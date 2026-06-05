"""Electro-mechanical pedal steel guitar — main build script.

  py -3.12 -m src.build              # build all printed parts + assembly + push
  py -3.12 -m src.build --part NAME  # build one printed part (fast iteration)
  py -3.12 -m src.build --list       # list part names
  py -3.12 -m src.build --geom       # print the §5 belt geometry report & exit

Writes each printed part's STEP (one representative for the ×10 parts) plus a
full assembly.step that places all 10 actuator axes and the motor brick in their
relative positions, then pushes assembly.step to Onshape.
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
from .carriage import carriage, ALONG as CARRIAGE_ALONG
from .bearing_block import bearing_block
from .bridge_mount import bridge_mount
from .base_rail import base_rail
from . import motor_brick as MB

# ─────────────────────────────────────────────────────────────────────────
# Printed parts → STEP files (canonical local frames for the repeated parts).
# ─────────────────────────────────────────────────────────────────────────
PARTS = {
    "carriage":      (heal(carriage),      "carriage.step",      "PA6-GF, load-critical — ×10 identical"),
    "bearing_block": (heal(bearing_block), "bearing_block.step", "PA6-GF — driven-end bearing cradle, ×10"),
    "bridge_mount":  (heal(bridge_mount),  "bridge_mount.step",  "PCTG — roller-bridge cradle"),
    "base_rail":     (heal(base_rail),     "base_rail.step",     "PCTG — screw-field base + near supports (split for print)"),
    "motor_brick":   (heal(MB.motor_brick),"motor_brick.step",   "PCTG — §5 2-layer motor holder"),
}


def _export(name):
    obj, path, note = PARTS[name]
    cq.exporters.export(obj, path)
    print(f"Wrote {path}" + (f"  ({note})" if note else ""))


# ─────────────────────────────────────────────────────────────────────────
# Per-string placement geometry (screw axis = X; strings spaced along Y)
# ─────────────────────────────────────────────────────────────────────────
def _screw_near_x(i):
    return D.SCREW_NEAR_X + D.string_bank_dx(i)

def _screw_len(i):
    return D.screw_pulley_x(i) + D.PULLEY_W / 2 + 2.0 - _screw_near_x(i)

def _bearing_x(i):
    # changer-ward → bridge-ward at the driven end: pulley | locknut | bearing
    return D.screw_pulley_x(i) - D.PULLEY_W / 2 - D.LOCKNUT_W - D.SUPPORT_BRG_W / 2

def _guide_len(i):
    """Uniform length for ALL guide rods — just long enough to span the
    carriage's full travel (the placement adds the bank offset along X)."""
    carriage_max_x = D.CARRIAGE_NOM_X + D.CARRIAGE_TRAVEL / 2 + CARRIAGE_ALONG / 2 + 3.0
    return carriage_max_x - D.SCREW_NEAR_X


# ─────────────────────────────────────────────────────────────────────────
# §5 belt-geometry report
# ─────────────────────────────────────────────────────────────────────────
def geometry_report() -> str:
    lines = ["", "=== Section 5 belt-offset motor geometry ===",
             f"  strings={D.N_STRINGS}  string pitch={D.STRING_PITCH} mm  "
             f"field width={D.STRING_FIELD_W:.0f} mm",
             f"  motor pitch={D.MOTOR_PITCH} mm  layers=2 (+/-{D.MOTOR_LAYER_Z} mm Z)  "
             f"belt skew = 0 deg by construction (each belt in a Y-Z plane)",
             "  per-string belt center distance (screw pulley -> motor pulley):"]
    cds = []
    for i in range(D.N_STRINGS):
        sy = D.string_y(i)
        my, mz, px = D.motor_target_for_string(i)
        cd = math.hypot(my - sy, mz - 0.0)
        cds.append(cd)
        belt_len = 2 * cd + math.pi * D.PULLEY_OD / 2
        lines.append(f"    string {i}: dY={my-sy:+6.1f}  dZ={mz:+6.1f}  "
                     f"center dist={cd:5.1f} mm  ~belt loop {belt_len:5.0f} mm  "
                     f"({'upper' if i%2 else 'lower'} layer)")
    lines.append(f"  belt center distance range: {min(cds):.1f}-{max(cds):.1f} mm "
                 f"(GT2 fine in this range)")
    lines.append("  motor-brick envelope (Y x Z): "
                 f"{MB.PLATE_W:.0f} x {MB.PLATE_H:.0f} mm; front face at X={MB.FACE_X:.0f} mm")
    depth = MB.FACE_X + MB.PLATE_T + D.MOTOR_TOTAL_LEN
    lines.append(f"  changer depth from the bridge (X): ~{depth:.0f} mm "
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
        return (cq.Workplane("XZ").text(str(n), 28, 6)
                .translate((MB.FACE_X, 0, MB.Z_HI + 26)))
    except Exception:
        return None


def _rod(p0, p1, r):
    """Thin cylinder (string) from p0 to p1."""
    v = p1.sub(p0)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, pnt=p0, dir=v))


def _string_components(i):
    """Return [(name, workplane)] for one string, fully placed."""
    sy = D.string_y(i)
    dx = D.string_bank_dx(i)
    lz = D.string_layer_z(i)
    px = D.screw_pulley_x(i)
    my, mz, _ = D.motor_target_for_string(i)
    nlen = _screw_near_x(i)
    bcx = _bearing_x(i)
    cnom = D.CARRIAGE_NOM_X + dx
    face_x = px + MB.STANDOFF + MB.PLATE_T / 2     # this string's belt-plane motor face

    out = []
    out.append((f"screw_{i}", C.screw(_screw_len(i)).translate((nlen, sy, lz))))
    out.append((f"carriage_{i}", carriage.translate((cnom, sy, lz))))
    # round nut pressed into the carriage +X face pocket (body inside the carriage)
    nut_x = cnom + CARRIAGE_ALONG / 2 - D.NUT_FLANGE_T - D.NUT_BODY_LEN
    out.append((f"nut_{i}", C.nut().translate((nut_x, sy, lz))))
    # guide rod directly below the screw (same Y, Z = lz + GUIDE_ROD_DZ)
    out.append((f"guiderod_{i}", C.guide_rod(_guide_len(i)).translate(
        (nlen, sy, lz + D.GUIDE_ROD_DZ))))
    out.append((f"bblock_{i}", bearing_block.translate((bcx, sy, lz))))
    # single deep-groove bearing nested in the open cradle (radial + axial)
    out.append((f"bearing_{i}", C.support_bearing().translate((bcx, sy, lz))))
    # locknut on the screw end, snug against the bearing inner race (axial retainer)
    out.append((f"locknut_{i}", C.locknut().translate(
        (px - D.PULLEY_W / 2 - D.LOCKNUT_W / 2, sy, lz))))
    out.append((f"spulley_{i}", C.pulley(D.PULLEY_BORE_SCREW).translate((px, sy, lz))))
    out.append((f"motor_{i}", C.motor().translate((face_x, my, mz))))
    out.append((f"mpulley_{i}", C.pulley(D.PULLEY_BORE_MOTOR).translate((px, my, mz))))
    out.append((f"belt_{i}", C.belt((sy, lz), (my, mz), px)))
    # schematic string: carriage ball-end (one MOUNTING end) over the bridge,
    # fanning from changer pitch to nut pitch to the far tuner (the other end);
    # the two ends are MOUNTING_SPAN apart in X at the nominal carriage position.
    anchor_x = cnom - 9.0
    tuner_x = anchor_x - D.MOUNTING_SPAN
    anchor = cq.Vector(anchor_x, sy, lz + D.BRIDGE_TOP_Z)
    bridge = cq.Vector(0.0, sy, D.BRIDGE_TOP_Z)
    tuner_pt = cq.Vector(tuner_x, D.nut_y(i), D.BRIDGE_TOP_Z)
    out.append((f"string_{i}", _rod(anchor, bridge, 0.6).union(_rod(bridge, tuner_pt, 0.6))))
    out.append((f"tuner_{i}", C.tuner().translate((tuner_x, D.nut_y(i), D.BRIDGE_TOP_Z))))
    return out


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
    asm = cq.Assembly(name="servo_steel")
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
