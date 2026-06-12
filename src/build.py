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
import os
import pathlib
import sys
from functools import partial

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
from . import tension_fork as TF
from . import pickup_mount as PM
from . import legs as LG

# ── PRINTED parts → each is exported as its own STEP. ────────────────────
# This is the ONLY set that gets STEP files. DEMONSTRATION parts (purchased /
# swaged dummies — leadscrew, brass nuts, bearings, motor, belt, string,
# string-end nut, dowels …) live in components.py and appear ONLY in
# assembly.step; they are never added here, so they are never exported.
# Values are (builder, path, note): the builder runs heal() LAZILY at export
# time, so importing this module (the overlap gate, assembly-only builds)
# doesn't pay for healing parts it never exports.
PARTS = {
    "carriage":        (partial(heal, carriage),      "carriage.step",        "PA6-GF, load-critical — ×10 identical"),
    "bridge_endplate": (partial(heal, bridge_endplate), "bridge_endplate.step", "PCTG — fused bridge end (screw support + bearing support + axle comb + box closure)"),
    "nut_block":       (partial(heal, NB.nut_block),   "nut_block.step",       "PA6-GF — removable keyhead nut block (gauged break-edge + 2-row clamps; reprint per string set)"),
    "belt_clamp":      (partial(heal, belt_clamp),    "belt_clamp.step",      "PETG — GT2 belt splice clamp (print 2 per splice ×10)"),
    "screw_pulley":    (lambda: heal(C.screw_pulley()),  "screw_pulley.step",  "flanged 14T GT2 pulley, 45° top flange — ×10"),
    "motor_pulley":    (lambda: heal(C.motor_pulley()),  "motor_pulley.step",  "flanged 14T GT2 pulley, 45° outer flange — ×10"),
    "tension_fork":    (lambda: TF.tension_forks,    "tension_fork.step",    "PCTG — belt-tension lock forks, graded 3.0–6.0 set (4 of the fitting size per motor; positive stop in the slot, no friction reliance)"),
    "pickup_bar":      (partial(heal, PM.pickup_bar),  "pickup_bar.step",    "PCTG — pickup bridge bar: end tongues ride the rail grooves (slide in from +X before the endplate); the body-mounted knob screw locks X"),
    "pickup_jaw":      (partial(heal, PM.pickup_jaw),  "pickup_jaw.step",    "PCTG — pickup width jaw ×2 (rotate 180° for the opposing side); M4 set-screw lock"),
    "pickup_shim":     (partial(heal, PM.pickup_shim), "pickup_shim.step",   "PCTG — pickup height shim (thickness = 25 - pickup height; reprint to tune the string gap)"),
    "pickup_knob":     (partial(heal, PM.pickup_knob), "pickup_knob.step",   "PCTG — hand knob for the X-lock M4 set screw (self-threads on, dab of CA)"),
    "leg_socket":      (lambda: heal(LG.leg_socket()),  "leg_socket.step",  "PCTG — leg corner socket ×4 (bolts to a rail's outer face; 2-turn coarse thread, quick on/off)"),
    "leg_segment":     (lambda: heal(LG.leg_segment()), "leg_segment.step", "PCTG — stackable leg tube (male up / female down; the COUNT per leg is the coarse height adjust, 142 mm per segment; default 2 -> x8)"),
    "leg_sleeve":      (lambda: heal(LG.leg_sleeve()),  "leg_sleeve.step",  "PCTG — leg slider sleeve ×4 (clamp collar: M4 set screw + insert)"),
    "leg_shaft":       (lambda: heal(LG.leg_shaft()),   "leg_shaft.step",   "PCTG — leg sliding shaft ×4 (0–150 fine height adjust)"),
    "leg_foot":        (lambda: heal(LG.leg_foot()),    "leg_foot.step",    "TPU — foot cap ×4"),
    "leg_washer":      (lambda: heal(LG.leg_washer()),  "leg_washer.step",  "TPU — anti-unscrew shoulder washer, 1/junction = segments+1 per leg (compresses on the last quarter turn)"),
}
for _i, _seg in enumerate(chassis_segments):     # chassis split into dovetailed segments
    PARTS[f"chassis_{_i}"] = (partial(heal, _seg), f"chassis_{_i}.step",
                              "PCTG — chassis segment (slide-down dovetail, glued)")


def _export(name):
    builder, path, note = PARTS[name]
    cq.exporters.export(builder(), path)
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
             f"  toothed GT2 ({D.BELT_W:.0f} mm); twisted 90° (motor pulley axis Y -> "
             "screw pulley axis Z), run along X.",
             "  cut = open-belt length to cut per string (loop + splice lap), mm:",
             f"    {'str':>4} {'run':>7} {'twist':>9} {'cut len':>9}"]
    total = 0.0
    for i in range(D.N_STRINGS):
        mx, my, mz = D.motor_pos(i)
        run = abs(mx - D.SCREW_X)
        rise = D.screw_pulley_z(i) - mz          # odd pulleys sit one belt-plane up
        span = math.hypot(run, rise)
        loop = 2 * span + math.pi * D.PULLEY_OD
        cut = loop + SPLICE_LAP
        total += cut
        lines.append(f"    {i:>4} {span:>6.0f} {90.0 / span:>6.2f}°/mm {cut:>8.0f}")
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


# DEMO POSE: per-string carriage offset from nominal (0 = top of travel, the
# default). Strings 1, 2, 9 and 10 — both edge pairs; string N = index 10−N
# (index 9 is string 1, the thinnest) — are kept PERMANENTLY at full
# down-travel, feet on the bottom stop: the maximum stretch/tension the
# mechanism can pull, so the travel extremes are always visible from either
# side. Everything riding the carriage (string nut, brass nut, string anchor)
# follows; the guide rod, screw and stops are fixed.
DEMO_POSE_DZ = {i: -D.CARRIAGE_TRAVEL for i in (0, 1, 8, 9)}


def _string_components(i):
    sy = D.string_y(i)
    mx, my, mz = D.motor_pos(i)
    cz = D.CARRIAGE_NOM_Z + DEMO_POSE_DZ.get(i, 0.0)
    out = []
    # vertical leadscrew
    out.append((f"leadscrew_{i}", C.screw().translate((D.SCREW_X, sy, D.SCREW_BOT_Z))))
    # carriage (origin = screw axis) at its demo-pose travel position
    out.append((f"carriage_{i}", carriage.translate((D.SCREW_X, sy, cz))))
    # string-end cylinder nut, seated in the carriage anchor (DEMO — purchased)
    out.append((f"string_nut_{i}", C.string_nut().translate(
        (D.BRIDGE_X, sy, cz + CARRIAGE_SEAT_Z))))
    # round nut pressed up into the carriage from below — flange seats flush
    # against the carriage bottom face, body up into the pocket
    out.append((f"nut_{i}", C.nut().translate(
        (D.SCREW_X, sy, cz - CARRIAGE_THICK / 2 - D.NUT_FLANGE_T))))
    # guide rod (anti-rotation), +X of the screw below the stringing window:
    # dropped in from the top through the stop bar's snug hole + the carriage's
    # closed bore, landing in the lower ledge's blind socket (bottom = blind
    # floor, 2 above the ledge bottom). Friction-held both ends. Ø2.5×28 (DIN 6325).
    rod_bot = (D.CARRIAGE_NOM_Z + D.GUIDE_FOOT_DZ
               - D.CARRIAGE_TRAVEL - D.GUIDE_FOOT_H - 4.0)   # GR_LBOT + 2
    out.append((f"guide_rod_{i}", C.guide_rod(28.0).translate(
        (D.SCREW_X + D.GUIDE_ROD_DX, sy, rod_bot))))
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
    # over the top, then runs the speaking length to the nut block.
    out.append((f"string_{i}", _string_path(i, sy)))
    # nut-block hardware (DEMO): gauged break pin + clamp set screw
    g = D.STRING_GAUGE[i]
    row_x = NB.ROW1_X if i % 2 == 0 else NB.ROW2_X
    out.append((f"break_dowel_{i}", C.dowel().translate(
        (D.NUT_BLOCK_X, D.nut_y(i), D.STRING_Z - g - 1.0))))          # pin top at STRING_Z−g
    out.append((f"set_screw_{i}", C.set_screw().translate(             # cup tip rests on the string
        (D.NUT_BLOCK_X + row_x, D.nut_y(i), D.STRING_Z + 8.0 + g))))
    return out


def _string_path(i, sy):
    """Vertical rise → 90° wrap around the bridge bearing → speaking length."""
    r = D.BRIDGE_BEARING_OD / 2
    cx, cz = D.BRIDGE_AXLE_X, D.BRIDGE_BEARING_Z      # bearing centre
    az = (D.CARRIAGE_NOM_Z + DEMO_POSE_DZ.get(i, 0.0)
          + CARRIAGE_SEAT_Z)                          # anchor (string-end nut in the carriage)
    g = D.STRING_GAUGE[i]
    rad = g / 2.0                                     # actual string gauge
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
    # speaking length to the break edge: string sits on the gauged pin, TOP at STRING_Z
    brk = cq.Vector(D.NUT_BLOCK_X, D.nut_y(i), D.STRING_Z - g / 2.0)
    out = out.union(_rod(prev, brk, rad))
    # dead end: break edge → clamp row, where it rests on the (plastic) groove floor
    row_x = NB.ROW1_X if i % 2 == 0 else NB.ROW2_X
    out = out.union(_rod(brk, cq.Vector(D.NUT_BLOCK_X + row_x, D.nut_y(i),
                                        D.STRING_Z + NB.GROOVE_FLOOR + g / 2.0), rad))
    return out


PICKUP_X = -58.0     # pickup-mount centre (default: near-bridge tone). The bar's
                     # tongues slide the rail grooves; hard stop at −128 (the
                     # fretboard-line zone starts beyond). Near end: verified
                     # clean at −50 (the spec minimum); the jaws meet carriage 9's
                     # travel zone from ~−47, so don't park closer than −50.


def _pickup_mount_components():
    from . import chassis as CH
    out = [("pickup", PM.pickup_demo().translate((PICKUP_X, 0, PM.PK_TOP))),
           ("pickup_bar", PM.pickup_bar.translate((PICKUP_X, 0, 0))),
           ("pickup_shim", PM.pickup_shim.translate((PICKUP_X, 0, PM.BAR_TOP)))]
    for k, s in enumerate((1, -1)):           # jaws pinching the pickup width
        out.append((f"pickup_jaw_{k}",
                    PM.pickup_jaw.rotate((0, 0, 0), (0, 0, 1), 0 if s > 0 else 180)
                    .translate((PICKUP_X + s * PM.PK_W / 2, 0, PM.BAR_TOP))))
    # X-lock: knobbed M4×12 button screws in the two fixed −Y boss stations
    # (use whichever covers the current position). Tips land on the tongue's
    # 45° wedge top at the screw line.
    ly = CH.Y_LO + CH.T / 2 + 2.5
    d_scr = (CH.PU_FACE_LO - ly) + 0.3            # screw-line depth from the body face
    tip_z = (CH.PU_TNG_Z1 + 0.15 + CH.PU_GROOVE_D) - d_scr   # wedge top there
    for k, lx in enumerate(CH.PU_LOCK_XS):
        out.append((f"pickup_screw_{k}", PM.pickup_lock_screw().translate((lx, ly, tip_z))))
        out.append((f"pickup_knob_{k}", PM.pickup_knob.translate((lx, ly, tip_z + 12.0 - 0.3))))
    return out


LEG_HEIGHT = 655.0   # floor → body bottom (the user's reference at 6')
LEG_SEGMENTS = 2     # coarse height: each segment steps 142; the shaft's 150
                     # slide overlaps the step, so every height ≥ ~241 is
                     # reachable by picking the count (2 covers 525..675)


def _leg_components():
    from . import chassis as CH
    out = []
    socket = LG.leg_socket()
    seg, sleeve = LG.leg_segment(), LG.leg_sleeve()
    shaft, foot, washer = LG.leg_shaft(), LG.leg_foot(), LG.leg_washer()
    ground = CH.Z_BOT - LEG_HEIGHT
    step = 2.0 + (LG.SEG_L - LG.TH_LEN)                  # washer + segment
    k = 0
    for sx in LG.LEG_STATIONS_X:
        for ry, rot in ((CH.Y_HI, 180), (CH.Y_LO, 0)):   # plate faces outward
            zb = CH.Z_BOT - LG.BARREL_L                  # barrel bottom
            out.append((f"leg_socket_{k}",
                        socket.rotate((0, 0, 0), (0, 0, 1), rot)
                        .translate((sx, ry, CH.Z_BOT))))
            # (thread phase is built into the female generators — all joints
            # share the same 3 mm offset, so parts place with no rotation)
            shoulder = zb                                # next male's shoulder seat
            for j in range(LEG_SEGMENTS):
                out.append((f"leg_washer_{(LEG_SEGMENTS + 1) * k + j}",
                            washer.translate((sx, ry, shoulder - 2))))
                shoulder -= step
                out.append((f"leg_segment_{LEG_SEGMENTS * k + j}",
                            seg.translate((sx, ry, shoulder))))
            out.append((f"leg_washer_{(LEG_SEGMENTS + 1) * k + LEG_SEGMENTS}",
                        washer.translate((sx, ry, shoulder - 2))))
            out.append((f"leg_sleeve_{k}", sleeve.translate((sx, ry, shoulder - 2))))
            out.append((f"leg_shaft_{k}", shaft.translate((sx, ry, ground + 3.0))))
            out.append((f"leg_foot_{k}", foot.translate((sx, ry, ground))))
            k += 1
    return out


def collect_components():
    comps = [
        ("bridge_endplate", bridge_endplate),
        ("bridge_bearings", C.bridge_bearings()),
        ("nut_block", NB.nut_block.translate((D.NUT_BLOCK_X, 0, D.STRING_Z))),
    ]
    comps += [(f"chassis_{i}", seg) for i, seg in enumerate(chassis_segments)]
    comps += _pickup_mount_components()
    comps += _leg_components()
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
    "nut_block":       (0.46, 0.52, 0.55),   # removable keyhead nut block
    "break_dowel":     (0.75, 0.75, 0.78),   # steel dowel (gauged break pin)
    "set_screw":       (0.55, 0.55, 0.58),   # alloy set screw
    "chassis":         (0.46, 0.52, 0.55),   # PCTG frame
    "pickup":          (0.10, 0.10, 0.12),   # DEMO pickup body
    "pickup_bar":      (0.80, 0.45, 0.10),   # pickup mount (printed)
    "pickup_jaw":      (0.90, 0.60, 0.20),
    "pickup_shim":     (0.95, 0.75, 0.35),
    "pickup_knob":     (0.86, 0.30, 0.10),
    "pickup_screw":    (0.55, 0.55, 0.58),
    "leg_socket":      (0.36, 0.42, 0.46),
    "leg_segment":     (0.42, 0.48, 0.52),
    "leg_sleeve":      (0.36, 0.42, 0.46),
    "leg_shaft":       (0.55, 0.58, 0.62),
    "leg_foot":        (0.12, 0.12, 0.13),   # TPU
    "leg_washer":      (0.12, 0.12, 0.13),   # TPU
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
    # ATOMIC write: the 30+ MB STEP takes seconds to save, and the viewer's
    # file-watcher must never see (and import) a half-written file — save to a
    # temp name, then rename into place (one mtime event, complete file).
    asm.save("assembly.step.tmp", exportType="STEP")
    os.replace("assembly.step.tmp", "assembly.step")
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
