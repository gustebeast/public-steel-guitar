"""Electro-mechanical pedal steel guitar — main build script (vertical layout).

  py -3.12 -m src.build              # build all printed parts + assembly.step
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
import pathlib
import sys

import cadquery as cq

# Shared FreeCAD viewer helper (Archive/3D/freecad). show() makes the build's
# output viewable — opens or refreshes its tab in the FreeCAD hub. Never raises.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "freecad"))
from freecad_view import show

from . import dimensions as D
from .helpers import heal
from . import components as C
from .carriage import carriage, THICK as CARRIAGE_THICK, SEAT_Z as CARRIAGE_SEAT_Z
from .bridge_endplate import bridge_endplate
from .belt_clamp import belt_clamp
from .chassis import segments as chassis_segments
from . import nut_block as NB

# ── PRINTED parts → each is exported as its own STEP. ────────────────────
# This is the ONLY set that gets STEP files. DEMONSTRATION parts (purchased /
# swaged dummies — leadscrew, brass nuts, bearings, motor, belt, string,
# string-end nut, tuner …) live in components.py and appear ONLY in
# assembly.step; they are never added here, so they are never exported.
PARTS = {
    "carriage":        (heal(carriage),      "carriage.step",        "PA6-GF, load-critical — ×10 identical"),
    "bridge_endplate": (heal(bridge_endplate), "bridge_endplate.step", "PA6-GF, load-critical — fused bridge end (screw support + bearing support + box closure)"),
    "nut_block":       (heal(NB.nut_block),   "nut_block.step",       "PCTG — removable keyhead nut block (gauged break-edge + 2-row clamps; reprint per string set)"),
    "belt_clamp":      (heal(belt_clamp),    "belt_clamp.step",      "PETG — GT2 belt splice clamp (print 2 per splice ×10)"),
    "screw_pulley":    (heal(C.screw_pulley()),  "screw_pulley.step",  "flanged 14T GT2 pulley, 45° top flange — ×10"),
    "motor_pulley":    (heal(C.motor_pulley()),  "motor_pulley.step",  "flanged 14T GT2 pulley, 45° outer flange — ×10"),
}
for _i, _seg in enumerate(chassis_segments):     # chassis split into dovetailed segments
    PARTS[f"chassis_{_i}"] = (heal(_seg), f"chassis_{_i}.step",
                              "PCTG — chassis segment (slide-down dovetail, glued)")


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
    # string-end cylinder nut, seated in the carriage anchor (DEMO — purchased)
    out.append((f"string_nut_{i}", C.string_nut().translate(
        (D.BRIDGE_X, sy, D.CARRIAGE_NOM_Z + CARRIAGE_SEAT_Z))))
    # round nut pressed up into the carriage from below — flange seats flush
    # against the carriage bottom face, body up into the pocket
    out.append((f"nut_{i}", C.nut().translate(
        (D.SCREW_X, sy, D.CARRIAGE_NOM_Z - CARRIAGE_THICK / 2 - D.NUT_FLANGE_T))))
    # guide rod (anti-rotation), offset −X, spanning the carriage travel
    glen = D.CARRIAGE_TRAVEL + CARRIAGE_THICK + 6.0
    out.append((f"guide_rod_{i}", C.guide_rod(glen).translate(
        (D.SCREW_X - D.GUIDE_ROD_DX, sy, D.CARRIAGE_NOM_Z - glen / 2))))
    # screw drive pulley (odd ones raised one belt-plane), support bearing
    # (in the shared rail), locknut below
    spz = D.screw_pulley_z(i)
    out.append((f"screw_pulley_{i}", C.screw_pulley().translate((D.SCREW_X, sy, spz))))
    out.append((f"screw_bearing_{i}", C.support_bearing().translate((D.SCREW_X, sy, D.SUPPORT_BRG_Z))))
    out.append((f"locknut_{i}", C.locknut().translate(
        (D.SCREW_X, sy, D.SUPPORT_BRG_Z - D.SUPPORT_BRG_W / 2 - D.LOCKNUT_W / 2))))
    # motor (shaft +Y, body −Y toward player) + its pulley + twisted belt
    out.append((f"motor_{i}", C.motor().translate((mx, my, mz))))
    out.append((f"motor_pulley_{i}", C.motor_pulley().translate((mx, my, mz))))
    out.append((f"belt_{i}", C.belt((mx, my, mz), (D.SCREW_X, sy, spz), teeth=(i == 0))))
    # splice clamp, oriented to the belt's flat zone (no twist within the clamp)
    so, sxd, sn = C.splice_frame((mx, my, mz), (D.SCREW_X, sy, spz))
    cloc = cq.Location(cq.Plane(origin=so, xDir=sxd, normal=sn))
    out.append((f"belt_clamp_{i}", cq.Workplane("XY").add(belt_clamp.val().moved(cloc))))
    # string: rises from the anchor tangent to the bearing's +X extent, wraps 90°
    # over the top, then runs the speaking length to the tuner at the nut.
    out.append((f"string_{i}", _string_path(i, sy)))
    # nut-block hardware (DEMO): gauged break pin, clamp anvil, clamp set screw
    g = D.STRING_GAUGE[i]
    row_x = NB.ROW1_X if i % 2 == 0 else NB.ROW2_X
    out.append((f"break_dowel_{i}", C.dowel().translate(
        (D.NUT_BLOCK_X, D.nut_y(i), D.STRING_Z - g - 1.05))))
    out.append((f"anvil_dowel_{i}", C.dowel().translate(
        (D.NUT_BLOCK_X + row_x, D.nut_y(i), D.STRING_Z + NB.GROOVE_FLOOR))))
    out.append((f"set_screw_{i}", C.set_screw().translate(
        (D.NUT_BLOCK_X + row_x, D.nut_y(i), D.STRING_Z + NB.BOSS_TOP))))
    return out


def _string_path(i, sy):
    """Vertical rise → 90° wrap around the bridge bearing → speaking length."""
    r = D.BRIDGE_BEARING_OD / 2
    cx, cz = D.BRIDGE_AXLE_X, D.BRIDGE_BEARING_Z      # bearing centre
    az = D.CARRIAGE_NOM_Z + CARRIAGE_SEAT_Z           # anchor (string-end nut in the carriage)
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
    # speaking length from the top tangent to the break edge (fans in Y to nut pitch)
    brk = cq.Vector(D.NUT_BLOCK_X, D.nut_y(i), D.STRING_Z)
    out = out.union(_rod(prev, brk, rad))
    # dead end: break edge → clamp row (dips into the groove)
    row_x = NB.ROW1_X if i % 2 == 0 else NB.ROW2_X
    out = out.union(_rod(brk, cq.Vector(D.NUT_BLOCK_X + row_x, D.nut_y(i),
                                        D.STRING_Z + NB.GROOVE_FLOOR), rad))
    return out


def collect_components():
    comps = [
        ("bridge_endplate", bridge_endplate),
        ("bridge_bearings", C.bridge_bearings()),
        ("nut_block", NB.nut_block.translate((D.NUT_BLOCK_X, 0, D.STRING_Z))),
    ]
    comps += [(f"chassis_{i}", seg) for i, seg in enumerate(chassis_segments)]
    for i in range(D.N_STRINGS):
        comps.extend(_string_components(i))
    return comps


# Per-part colours, baked into the assembly STEP (single source of truth — they
# show in the shared FreeCAD live viewer and any STEP viewer). RGB floats 0..1.
_COLORS = {
    "carriage":        (0.27, 0.51, 0.71),   # PA6-GF — load-critical
    "bridge_endplate": (0.39, 0.58, 0.93),   # PA6-GF — load-critical
    "belt_clamp":      (0.95, 0.55, 0.15),   # PETG
    "screw_pulley":    (0.00, 0.55, 0.55),
    "motor_pulley":    (0.00, 0.55, 0.55),
    "leadscrew":       (0.75, 0.75, 0.78),   # steel
    "screw_bearing":   (0.69, 0.77, 0.87),
    "bridge_bearings": (0.69, 0.77, 0.87),
    "nut":             (0.82, 0.60, 0.20),   # brass
    "string_nut":      (0.82, 0.60, 0.20),   # brass string-end fitting (demo)
    "locknut":         (0.82, 0.60, 0.20),
    "guide_rod":       (0.35, 0.35, 0.38),
    "motor":           (0.22, 0.25, 0.27),   # charcoal
    "belt":            (0.13, 0.13, 0.13),   # GT2 black
    "string":          (0.85, 0.85, 0.85),
    "tuner":           (0.50, 0.50, 0.50),
    "nut_block":       (0.46, 0.52, 0.55),   # PCTG — removable keyhead nut block
    "break_dowel":     (0.75, 0.75, 0.78),   # steel dowel (gauged break pin)
    "anvil_dowel":     (0.75, 0.75, 0.78),   # steel dowel (clamp anvil)
    "set_screw":       (0.55, 0.55, 0.58),   # alloy set screw
    "chassis":         (0.46, 0.52, 0.55),   # PCTG frame
    "build_counter":   (0.86, 0.08, 0.24),
}
_DEFAULT_COLOR = (0.80, 0.80, 0.80)


def _color_for(name):
    head, _, tail = name.rpartition("_")
    base = head if (head and tail.isdigit()) else name
    return cq.Color(*_COLORS.get(base, _DEFAULT_COLOR))


def _export_assembly():
    build_n = _bump_build_counter()
    asm = cq.Assembly(name="servo_steel")
    for name, wp in collect_components():
        asm.add(wp, name=name, color=_color_for(name))
    counter = _build_counter_model(build_n)
    if counter is not None:
        asm.add(counter, name="build_counter", color=_color_for("build_counter"))
    asm.save("assembly.step")
    print(f"Wrote assembly.step  [build #{build_n}]", flush=True)
    print(geometry_report())
    show("assembly.step")   # open/refresh it in the shared FreeCAD hub


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
