"""Electro-mechanical pedal steel guitar — main build script (vertical layout).

  py -3.12 -m src.build              # build all printed parts + assembly + push
  py -3.12 -m src.build --part NAME  # build one printed part (fast iteration)
  py -3.12 -m src.build --list       # list part names
  py -3.12 -m src.build --geom       # print the belt geometry report & exit

Vertical-screw, under-string layout: each string turns 90° over its bridge
bearing and runs down to a vertical leadscrew; motors lie flat under the speaking
length in a staircase, twisted belts connecting them.
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
from .components import MOTOR_PULLEY_STANDOFF
from .carriage import carriage, THICK as CARRIAGE_THICK
from .screw_rail import screw_rail
from .bridge_mount import bridge_mount
from .belt_clamp import belt_clamp
from . import motor_bank as MB

PARTS = {
    "carriage":        (heal(carriage),      "carriage.step",        "PA6-GF, load-critical — ×10 identical"),
    "screw_rail":      (heal(screw_rail),    "screw_rail.step",      "PA6-GF — shared bottom screw-support rail"),
    "bridge_support":  (heal(bridge_mount),  "bridge_support.step",  "PCTG — bridge-bearing axle support"),
    "motor_bank":      (heal(MB.motor_bank), "motor_bank.step",      "PCTG — under-string staircase motor mounts"),
    "belt_clamp":      (heal(belt_clamp),    "belt_clamp.step",      "PETG — GT2 belt splice clamp (print 2 per splice ×10)"),
}


def _export(name):
    obj, path, note = PARTS[name]
    cq.exporters.export(obj, path)
    print(f"Wrote {path}" + (f"  ({note})" if note else ""))


def _rod(p0, p1, r):
    v = p1.sub(p0)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, pnt=p0, dir=v))


# ─────────────────────────────────────────────────────────────────────────
# Belt geometry report
# ─────────────────────────────────────────────────────────────────────────
SPLICE_LAP = 25.0   # extra open-belt length to lap inside the splice clamp


def geometry_report() -> str:
    lines = ["", "=== Belt geometry (under-string vertical layout) ===",
             f"  strings={D.N_STRINGS}  string pitch={D.STRING_PITCH} mm  "
             f"screw len={D.SCREW_LEN:.0f} mm (vertical, no whip)",
             "  toothed GT2 (6 mm); twisted 90° (motor pulley axis Y -> screw "
             "pulley axis Z), run along X.",
             "  cut = open-belt length to cut per string (loop + splice lap), mm:",
             f"    {'str':>4} {'run':>7} {'twist':>9} {'cut len':>9}"]
    total = 0.0
    for i in range(D.N_STRINGS):
        mx, my, mz = D.motor_pos(i)
        run = abs(mx - D.SCREW_X)
        loop = 2 * run + math.pi * D.PULLEY_OD
        cut = loop + SPLICE_LAP
        total += cut
        lines.append(f"    {i:>4} {run:>6.0f} {90.0 / run:>6.2f}°/mm {cut:>8.0f}")
    lines.append(f"  total open GT2 to buy: ~{total/1000:.2f} m "
                 f"(+ {D.N_STRINGS} printed splice clamps)")
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
                .translate((-150, 0, D.STRING_Z + 40)))
    except Exception:
        return None


def _string_components(i):
    sy = D.string_y(i)
    mx, my, mz = D.motor_pos(i)
    out = []
    # vertical leadscrew
    out.append((f"leadscrew_{i}", C.screw().translate((D.SCREW_X, sy, D.SCREW_BOT_Z))))
    # carriage (origin = screw axis) at the nominal travel position
    out.append((f"carriage_{i}", carriage.translate((D.SCREW_X, sy, D.CARRIAGE_NOM_Z))))
    # round nut pressed up into the carriage from below
    out.append((f"nut_{i}", C.nut().translate(
        (D.SCREW_X, sy, D.CARRIAGE_NOM_Z - CARRIAGE_THICK / 2))))
    # guide rod (anti-rotation), offset −X, spanning the carriage travel
    glen = D.CARRIAGE_TRAVEL + CARRIAGE_THICK + 6.0
    out.append((f"guide_rod_{i}", C.guide_rod(glen).translate(
        (D.SCREW_X - D.GUIDE_ROD_DX, sy, D.CARRIAGE_NOM_Z - glen / 2))))
    # screw drive pulley, support bearing (in the shared rail), locknut below
    out.append((f"screw_pulley_{i}", C.screw_pulley().translate((D.SCREW_X, sy, D.SCREW_PULLEY_Z))))
    out.append((f"screw_bearing_{i}", C.support_bearing().translate((D.SCREW_X, sy, D.SUPPORT_BRG_Z))))
    out.append((f"locknut_{i}", C.locknut().translate(
        (D.SCREW_X, sy, D.SUPPORT_BRG_Z - D.SUPPORT_BRG_W / 2 - D.LOCKNUT_W / 2))))
    # motor (shaft +Y, body −Y toward player) + its pulley + twisted belt
    out.append((f"motor_{i}", C.motor().translate((mx, my, mz))))
    out.append((f"motor_pulley_{i}", C.motor_pulley().translate((mx, my, mz))))
    out.append((f"belt_{i}", C.belt((mx, my, mz), (D.SCREW_X, sy, D.SCREW_PULLEY_Z))))
    # splice clamp at the run midpoint (free span, clears the lower motors' bodies)
    out.append((f"belt_clamp_{i}", belt_clamp.translate(
        ((mx + D.SCREW_X) / 2, sy, D.SCREW_PULLEY_Z))))
    # string: rises from the anchor tangent to the bearing's +X extent, wraps 90°
    # over the top, then runs the speaking length to the tuner at the nut.
    out.append((f"string_{i}", _string_path(i, sy)))
    out.append((f"tuner_{i}", C.tuner().translate((-D.MOUNTING_SPAN, D.nut_y(i), D.STRING_Z))))
    return out


def _string_path(i, sy):
    """Vertical rise → 90° wrap around the bridge bearing → speaking length."""
    r = D.BRIDGE_BEARING_OD / 2
    cx, cz = D.BRIDGE_AXLE_X, D.BRIDGE_BEARING_Z      # bearing centre
    az = D.CARRIAGE_NOM_Z + CARRIAGE_THICK / 2        # anchor (carriage top)
    rad = 0.55
    # vertical rise to the +X tangent point (cx+r, cz)
    p0 = cq.Vector(cx + r, sy, az)
    prev = cq.Vector(cx + r, sy, cz)
    out = _rod(p0, prev, rad)
    # 90° arc, +X extent → top, approximated by short rods
    N = 10
    for k in range(1, N + 1):
        ang = (k / N) * (math.pi / 2)
        p = cq.Vector(cx + r * math.cos(ang), sy, cz + r * math.sin(ang))
        out = out.union(_rod(prev, p, rad))
        prev = p
    # speaking length from the top tangent to the tuner (fans in Y to nut pitch)
    out = out.union(_rod(prev, cq.Vector(-D.MOUNTING_SPAN, D.nut_y(i), D.STRING_Z), rad))
    return out


def collect_components():
    comps = [
        ("bridge_support", bridge_mount),
        ("bridge_bearings", C.bridge_bearings()),
        ("screw_rail", screw_rail),
        ("motor_bank", MB.motor_bank),
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
    p.add_argument("--geom", action="store_true", help="Print belt geometry report and exit.")
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
