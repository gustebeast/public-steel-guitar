"""Electro-mechanical pedal steel guitar — main build script (vertical layout).

  py -3.12 -m src.build              # build all printed parts + assembly + push
  py -3.12 -m src.build --part NAME  # build one printed part (fast iteration)
  py -3.12 -m src.build --list       # list part names
  py -3.12 -m src.build --geom       # print the belt geometry report & exit

Vertical-screw, under-string layout: each string turns 90° over its roller and
runs down to a vertical leadscrew; motors lie flat under the speaking length in a
staircase, twisted belts connecting them.
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
from .bearing_block import bearing_rail
from .bridge_mount import bridge_mount
from . import motor_brick as MB

PARTS = {
    "carriage":     (heal(carriage),     "carriage.step",     "PA6-GF, load-critical — ×10 identical"),
    "bearing_rail": (heal(bearing_rail), "bearing_rail.step", "PA6-GF — shared bottom bushing rail"),
    "bridge_mount": (heal(bridge_mount), "bridge_mount.step", "PCTG — roller bridge support"),
    "motor_bank":   (heal(MB.motor_bank),"motor_bank.step",   "PCTG — under-string staircase motor mounts"),
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
def geometry_report() -> str:
    lines = ["", "=== Belt geometry (under-string vertical layout) ===",
             f"  strings={D.N_STRINGS}  string pitch={D.STRING_PITCH} mm  "
             f"screw len={D.SCREW_LEN:.0f} mm (vertical, no whip)",
             "  per-string belt: motor pulley (axis Y) -> screw pulley (axis Z), "
             "twisted, run along X:"]
    runs = []
    for i in range(D.N_STRINGS):
        mx, my, mz = D.motor_pos(i)
        run = abs(mx - D.SCREW_X)
        runs.append(run)
        lines.append(f"    string {i}: belt run {run:5.0f} mm along X "
                     f"(motor at X={mx:.0f}, Y={my:+.1f})")
    lines.append(f"  belt run range: {min(runs):.0f}-{max(runs):.0f} mm "
                 f"(long is fine — self-lock holds the load, not the belt)")
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
    out.append((f"screw_{i}", C.screw().translate((D.SCREW_X, sy, D.SCREW_BOT_Z))))
    # carriage (origin = screw axis) at the nominal travel position
    out.append((f"carriage_{i}", carriage.translate((D.SCREW_X, sy, D.CARRIAGE_NOM_Z))))
    # round nut pressed up into the carriage from below
    out.append((f"nut_{i}", C.nut().translate(
        (D.SCREW_X, sy, D.CARRIAGE_NOM_Z - CARRIAGE_THICK / 2))))
    # guide rod (anti-rotation), offset −X, spanning the carriage travel
    glen = D.CARRIAGE_TRAVEL + CARRIAGE_THICK + 6.0
    out.append((f"guiderod_{i}", C.guide_rod(glen).translate(
        (D.SCREW_X - D.GUIDE_ROD_DX, sy, D.CARRIAGE_NOM_Z - glen / 2))))
    # screw drive pulley, bushing (in the shared rail), locknut below
    out.append((f"spulley_{i}", C.screw_pulley().translate((D.SCREW_X, sy, D.SCREW_PULLEY_Z))))
    out.append((f"bearing_{i}", C.support_bearing().translate((D.SCREW_X, sy, D.SUPPORT_BRG_Z))))
    out.append((f"locknut_{i}", C.locknut().translate(
        (D.SCREW_X, sy, D.SUPPORT_BRG_Z - D.SUPPORT_BRG_W / 2 - D.LOCKNUT_W / 2))))
    # motor (shaft +Y, body −Y toward player) + its pulley + twisted belt
    out.append((f"motor_{i}", C.motor().translate((mx, my, mz))))
    out.append((f"mpulley_{i}", C.motor_pulley().translate((mx, my, mz))))
    out.append((f"belt_{i}", C.belt((mx, my, mz), (D.SCREW_X, sy, D.SCREW_PULLEY_Z))))
    # schematic string: carriage anchor -> roller (90° turn) -> tuner at the nut
    az = D.CARRIAGE_NOM_Z + CARRIAGE_THICK / 2
    anchor = cq.Vector(D.ROLLER_X, sy, az)
    roller = cq.Vector(D.ROLLER_X, sy, D.STRING_Z)
    tuner = cq.Vector(-D.MOUNTING_SPAN, D.nut_y(i), D.STRING_Z)
    out.append((f"string_{i}", _rod(anchor, roller, 0.6).union(_rod(roller, tuner, 0.6))))
    out.append((f"tuner_{i}", C.tuner().translate((-D.MOUNTING_SPAN, D.nut_y(i), D.STRING_Z))))
    return out


def collect_components():
    comps = [
        ("bridge_mount", bridge_mount),
        ("roller_bridge", C.roller_bridge()),
        ("bearing_rail", bearing_rail),
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
