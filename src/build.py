"""Electro-Mechanical Pedal Steel Guitar — main build script.

  py -3.12 -m src.build              # build all printed parts + assembly + push
  py -3.12 -m src.build --part NAME  # build one printed part (fast iteration)
  py -3.12 -m src.build --list       # list part names
  py -3.12 -m src.build --geom       # print the §5 belt geometry report & exit

Writes each printed part's STEP (one representative for the ×10 parts) plus a
full assembly.step that places all 10 actuator axes and the motor brick in
their relative positions, then pushes assembly.step to Onshape.
"""

from __future__ import annotations

import argparse
import math
import os
import pathlib
import subprocess
import sys

import cadquery as cq

from . import dimensions as D
from .helpers import heal
from . import components as C
from .carriage import carriage
from .bearing_block import bearing_block, BLK_Y
from .bridge_mount import bridge_mount
from .base_rail import base_rail
from . import motor_brick as MB

# ─────────────────────────────────────────────────────────────────────────
# Printed parts → STEP files (canonical local frames for the repeated parts).
# ─────────────────────────────────────────────────────────────────────────
PARTS = {
    "carriage":      (heal(carriage),      "carriage.step",      "PA6-GF, load-critical — ×10 identical"),
    "bearing_block": (heal(bearing_block), "bearing_block.step", "PA6-GF — driven-end radial+thrust support, ×10"),
    "bridge_mount":  (heal(bridge_mount),  "bridge_mount.step",  "PCTG — roller-bridge cradle"),
    "base_rail":     (heal(base_rail),     "base_rail.step",     "PCTG — screw-field base + far support (split for print)"),
    "motor_brick":   (heal(MB.motor_brick),"motor_brick.step",   "PCTG — §5 2-layer fanned motor holder"),
}


def _export(name):
    obj, path, note = PARTS[name]
    cq.exporters.export(obj, path)
    print(f"Wrote {path}" + (f"  ({note})" if note else ""))


# ─────────────────────────────────────────────────────────────────────────
# Per-string placement geometry
# ─────────────────────────────────────────────────────────────────────────
def _screw_near_y(i):
    return D.SCREW_NEAR_Y + D.string_bank_dy(i)

def _screw_len(i):
    return D.screw_pulley_y(i) + D.PULLEY_W / 2 + 2.0 - _screw_near_y(i)

def _bearing_y(i):
    # outboard→inboard at the driven end: pulley | locknut | bearing (cradle)
    return D.screw_pulley_y(i) - D.PULLEY_W / 2 - D.LOCKNUT_W - D.SUPPORT_BRG_W / 2

def _guide_len(i):
    """Uniform length for ALL guide rods — just long enough to span the
    carriage's full travel. (The old per-bearing length made some rods long
    enough to collide with the belts.) The placement adds the bank offset, so
    the same length works in both variants."""
    carriage_max_y = D.CARRIAGE_NOM_Y + D.CARRIAGE_TRAVEL / 2 + 4.5 + 3.0
    return carriage_max_y - D.SCREW_NEAR_Y


# ─────────────────────────────────────────────────────────────────────────
# §5 belt-geometry report
# ─────────────────────────────────────────────────────────────────────────
def geometry_report() -> str:
    lines = ["", "=== Section 5 belt-offset motor-brick geometry ===",
             f"  strings={D.N_STRINGS}  string pitch={D.STRING_PITCH} mm  "
             f"field width={D.STRING_FIELD_W:.0f} mm",
             f"  motor pitch={D.MOTOR_PITCH} mm  layers=2 (+/-{D.MOTOR_LAYER_Z} mm Z)  "
             f"belt skew = 0 deg by construction (each belt in an X-Z plane)",
             "  per-string belt center distance (screw pulley -> motor pulley):"]
    cds = []
    for i in range(D.N_STRINGS):
        sx = D.string_x(i)
        mx, mz, py = D.motor_target_for_string(i)
        cd = math.hypot(mx - sx, mz - 0.0)
        cds.append(cd)
        belt_len = 2 * cd + math.pi * D.PULLEY_OD / 2
        lines.append(f"    string {i}: dX={mx-sx:+6.1f}  dZ={mz:+6.1f}  "
                     f"center dist={cd:5.1f} mm  ~belt loop {belt_len:5.0f} mm  "
                     f"({'upper' if i%2 else 'lower'} layer)")
    lines.append(f"  belt center distance range: {min(cds):.1f}-{max(cds):.1f} mm "
                 f"(GT2 fine in this range)")
    lines.append("  motor-brick envelope (X x Z front plate): "
                 f"{MB.PLATE_W:.0f} x {MB.PLATE_H:.0f} mm; "
                 f"front face at Y={MB.FACE_Y:.0f} mm")
    depth = (MB.FACE_Y + MB.PLATE_T + D.MOTOR_TOTAL_LEN) - 0.0
    lines.append(f"  end-box depth behind the bridge (Y): ~{depth:.0f} mm "
                 f"(motor body+PCB {D.MOTOR_TOTAL_LEN:.0f} mm beyond the plate)")
    lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────
# Assembly
# ─────────────────────────────────────────────────────────────────────────
_BUILD_COUNTER_FILE = pathlib.Path(__file__).resolve().parent.parent / "tools" / "build_counter.txt"


def _bump_build_counter() -> int:
    try:
        n = int(_BUILD_COUNTER_FILE.read_text().strip()) + 1
    except (OSError, ValueError):
        n = 1
    try:
        _BUILD_COUNTER_FILE.write_text(f"{n}\n")
    except OSError:
        pass
    return n


def _build_counter_model(n: int):
    try:
        return (cq.Workplane("XZ").center(0, 0).text(str(n), 28, 6)
                .translate((0, MB.FACE_Y, MB.Z_HI + 26)))
    except Exception:
        return None


def _string_components(i):
    """Return [(name, workplane)] for one string, fully placed (incl. bank Y)."""
    sx = D.string_x(i)
    dy = D.string_bank_dy(i)
    lz = D.string_layer_z(i)
    py = D.screw_pulley_y(i)
    mx, mz, _ = D.motor_target_for_string(i)
    slen = _screw_len(i)
    bcy = _bearing_y(i)         # holder is built about the bearing centre
    nlen = _screw_near_y(i)
    cnom = D.CARRIAGE_NOM_Y + dy
    face_y = py + MB.STANDOFF + MB.PLATE_T / 2     # this string's belt-plane motor face

    out = []
    out.append((f"screw_{i}", C.screw(slen).translate((sx, nlen, lz))))
    out.append((f"carriage_{i}", carriage.translate((sx, cnom, lz))))
    # round nut pressed into the carriage +Y face pocket (body inside the
    # carriage so it doesn't protrude into the back bank)
    nut_y = cnom + 9.0 / 2 - D.NUT_FLANGE_T - D.NUT_BODY_LEN   # carriage BODY_Y/2 = 4.5
    out.append((f"nut_{i}", C.nut().translate((sx, nut_y, lz))))
    # guide rod directly below the screw (same X, Z = lz + GUIDE_ROD_DZ)
    out.append((f"guiderod_{i}", C.guide_rod(_guide_len(i)).translate(
        (sx, nlen, lz + D.GUIDE_ROD_DZ))))
    out.append((f"bblock_{i}", bearing_block.translate((sx, bcy, lz))))
    # single deep-groove bearing nested in the open cradle (radial + axial)
    out.append((f"bearing_{i}", C.support_bearing().translate((sx, bcy, lz))))
    # locknut on the screw end, snug against the bearing inner race (axial retainer)
    out.append((f"locknut_{i}", C.locknut().translate(
        (sx, py - D.PULLEY_W / 2 - D.LOCKNUT_W / 2, lz))))
    out.append((f"spulley_{i}", C.pulley(D.PULLEY_BORE_SCREW).translate((sx, py, lz))))
    out.append((f"motor_{i}", C.motor().translate((mx, face_y, mz))))
    out.append((f"mpulley_{i}", C.pulley(D.PULLEY_BORE_MOTOR).translate((mx, py, mz))))
    out.append((f"belt_{i}", C.belt((sx, lz), (mx, mz), py)))
    # schematic string in two segments: from the carriage ball-end (one
    # MOUNTING end, at this bank's layer height) up over the bridge roller
    # (common string height), then fanning out from changer pitch to nut pitch
    # to the far tuner (the other MOUNTING end). The two mounting ends are
    # MOUNTING_SPAN apart in Y at the nominal carriage position.
    anchor_y = cnom - 9.0
    tuner_y = anchor_y - D.MOUNTING_SPAN
    anchor = cq.Vector(sx, anchor_y, lz + D.BRIDGE_TOP_Z)
    bridge = cq.Vector(sx, 0.0, D.BRIDGE_TOP_Z)
    tuner_pt = cq.Vector(D.nut_x(i), tuner_y, D.BRIDGE_TOP_Z)
    out.append((f"string_{i}", _rod(anchor, bridge, 0.6).union(_rod(bridge, tuner_pt, 0.6))))
    out.append((f"tuner_{i}", C.tuner().translate((D.nut_x(i), tuner_y, D.BRIDGE_TOP_Z))))
    return out


def _rod(p0, p1, r):
    """Thin cylinder (string) from p0 to p1."""
    v = p1.sub(p0)
    h = v.Length
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, pnt=p0, dir=v))


def collect_components():
    """All placed components as [(name, workplane)] — singletons + 10 strings.
    Shared by the assembly export and the overlap checker."""
    comps = [
        ("base_rail", base_rail),
        ("bridge_mount", bridge_mount),
        ("roller_bridge", C.roller_bridge()),
        ("motor_brick", MB.motor_brick),
    ]
    for i in range(D.N_STRINGS):
        comps.extend(_string_components(i))
    return comps


def _export_assembly():
    build_n = _bump_build_counter()
    asm = cq.Assembly(name="electromech_pedal_steel")
    for name, wp in collect_components():
        asm.add(wp, name=name)
    counter = _build_counter_model(build_n)
    if counter is not None:
        asm.add(counter, name="build_counter")
    asm.save("assembly.step")
    print(f"Wrote assembly.step  [build #{build_n}]", flush=True)
    print(geometry_report())
    _push_onshape()


def _push_onshape() -> None:
    script = pathlib.Path(__file__).resolve().parent.parent / "tools" / "onshape_push.py"
    if not script.exists() or not pathlib.Path("assembly.step").exists():
        return
    try:
        subprocess.run([sys.executable, str(script), "assembly.step"],
                       check=False, cwd=os.getcwd())
    except Exception as e:
        print(f"[onshape] push skipped: {e}", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(prog="src.build")
    p.add_argument("--part", help="Build only this printed part (skips assembly).")
    p.add_argument("--list", action="store_true", help="List part names and exit.")
    p.add_argument("--geom", action="store_true", help="Print §5 geometry report and exit.")
    args = p.parse_args()

    if args.geom:
        print(geometry_report())
        return
    if args.list:
        print("assembly")
        for name in PARTS:
            print(name)
        return
    if args.part:
        if args.part == "assembly":
            _export_assembly()
            return
        if args.part not in PARTS:
            print(f"unknown part: {args.part!r}. Use --list.", file=sys.stderr)
            sys.exit(2)
        _export(args.part)
        return

    for name in PARTS:
        _export(name)
    _export_assembly()


if __name__ == "__main__":
    main()
