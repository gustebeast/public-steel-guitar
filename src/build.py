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
from step_export import export_step

from . import dimensions as D
from .helpers import heal
from . import components as C
from . import chassis as CH
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
#
# Paths are MATERIAL FOLDERS — slice a whole folder with one filament:
#   petg-gf/  stiffness/creep-critical (the sustained string-tension +
#             ground-reaction paths, and the deck colour layers)
#   pctg/     compliant, snap-fit, impact and fine-feature parts
#   tpu/      feet + preload washers


def _PB(attr):
    return getattr(__import__("src.pedal_bar", fromlist=["e"]), attr)()


PARTS = {
    "carriage":        (partial(heal, carriage),      "petg-gf/carriage.step",        "PETG-GF, load-critical — ×10 identical"),
    "bridge_endplate": (partial(heal, bridge_endplate), "petg-gf/bridge_endplate.step", "PETG-GF — fused bridge end (screw support + bearing support + axle comb + box closure)"),
    "keyhead_endplate": (lambda: heal(__import__("src.keyhead_endplate", fromlist=["e"]).keyhead_endplate), "petg-gf/keyhead_endplate.step", "PETG-GF — merged keyhead (-X) endplate + nut block (25 mm, one piece): closes the box, caps the deck grooves, gauged break-edge + 2-row clamps; drops in last, held by 1 screw"),
    "belt_clamp":      (partial(heal, belt_clamp),    "pctg/belt_clamp.step",      "PCTG — GT2 belt splice clamp (print 2 per splice ×10)"),
    "knee_housing":    (lambda: __import__("src.knee_lever", fromlist=["e"]).knee_housing, "petg-gf/knee_housing.step", "PETG-GF — knee-lever (LKL) housing: MR85 pivot bearings + MT6701 sensor mount (rigid = stable air gap)"),
    "knee_lever":      (lambda: __import__("src.knee_lever", fromlist=["e"]).knee_lever,   "pctg/knee_lever.step",   "PCTG — knee-lever (LKL) arm + knee paddle (takes knee strikes: toughness over stiffness)"),
    "floating_tenon":  (lambda: __import__("src.knee_lever", fromlist=["e"]).floating_tenon, "petg-gf/floating_tenon.step", "PETG-GF — floating christmas-tree tenon: glue into the lever yoke, slide into the rib (2 per lever)"),
    "cart_base": (lambda: __import__("src.knee_lever", fromlist=["e"]).cart_base, "pctg/cart_base.step", "PCTG — spring-cartridge (inverted-U, open -Z; shared: print 2, for main + half-stop)"),
    "cart_piston": (lambda: __import__("src.knee_lever", fromlist=["e"]).cart_piston, "pctg/cart_piston.step", "PCTG — spring-cartridge piston, flat follower tongue (shared: print 2)"),
    "guide_post": (lambda: __import__("src.knee_lever", fromlist=["e"]).guide_post, "pctg/guide_post.step", "PCTG — coil-back guide post, screw pushes it (shared: print 2)"),
    "cart_backstop": (lambda: __import__("src.knee_lever", fromlist=["e"]).cart_backstop, "pctg/cart_backstop.step", "PCTG — hollow X-position back-stop screw: threads the housing boss, tension screw runs through the Ø5.5 bore (shared: print 2)"),
    "cart_drag": (lambda: __import__("src.knee_lever", fromlist=["e"]).cart_drag, "tpu/cart_drag.step", "TPU — passive drag pad: seats in the pocket outboard-wall recess, bulges onto the cartridge for transport-drift friction (print 2, MAIN mirrored)"),
    "screw_pulley":    (lambda: heal(C.screw_pulley()),  "pctg/screw_pulley.step",  "PCTG — flanged 14T GT2 pulley, 45° top flange — ×10 (fine teeth need unfilled resolution)"),
    "motor_pulley":    (lambda: heal(C.motor_pulley()),  "pctg/motor_pulley.step",  "PCTG — flanged 14T GT2 pulley, 45° outer flange — ×10"),
    "tension_fork":    (lambda: TF.tension_forks,    "pctg/tension_fork.step",    "PCTG — belt-tension lock forks, graded 3.0–6.0 set (4 of the fitting size per motor; positive stop in the slot, no friction reliance)"),
    # pickup carrier: the deck pickup-piece (a top_plate panel) holds the pickup
    # via a full-width height plate + a clamp shim (both printed); the screws are
    # stocked M4
    "pickup_zplate":   (lambda: heal(__import__("src.top_plate", fromlist=["e"]).pickup_zplate), "petg-gf/pickup_zplate.step", "PETG-GF — pickup height plate (full-width; the 3 M4 height screws lift it from below, pickup rests on top so it can sit anywhere in X; GF keeps it flat on the point loads)"),
    "pickup_xclamp":   (lambda: heal(__import__("src.top_plate", fromlist=["e"]).pickup_xclamp), "pctg/pickup_xclamp.step", "PCTG — pickup clamp shim (the side M4 screw drives it against the pickup so no metal digs the pickup; compliance is the function)"),
    "leg_socket":      (lambda: heal(LG.leg_socket()),  "petg-gf/leg_socket.step",  "PETG-GF — leg corner socket ×4 (dovetail tenon slides up into the rail slot, glued; 2-turn coarse thread, quick on/off)"),
    "leg_segment":     (lambda: heal(LG.leg_segment()), "pctg/leg_segment.step", "PCTG — stackable leg tube ×8 (male up / female down; COUNT per leg = coarse height adjust, 142/segment). PCTG not GF: standing prints bend across layer lines and a kick is energy-limited — PCTG interlayer is ~85-90% of bulk + ductile (~8 J to yield vs ~2 J to snap for GF). Print bell-down, LOW fan"),
    "leg_sleeve":      (lambda: heal(LG.leg_sleeve()),  "pctg/leg_sleeve.step",  "PCTG — leg slider sleeve ×4 (pinch collar: M4 button screw + insert pulls the slit closed; the slit MUST flex — never glass-filled)"),
    "leg_shaft":       (lambda: heal(LG.leg_shaft()),   "pctg/leg_shaft.step",   "PCTG — leg sliding shaft ×3 (fine height adjust; single-D key flat = pure Z travel + one unique orientation; chord notch mounts the pedal bar on the +Y legs). Print LYING ON THE FLAT: layer lines run along the shaft (kick bending loads bulk material), 43-deg junction self-supporting, notch faces up"),
    "leg_shaft_trrs":  (lambda: heal(LG.leg_shaft_trrs()), "pctg/leg_shaft_trrs.step", "PCTG — the -X/+Y leg's shaft ×1: leg_shaft + inboard corner fill + the X-facing TRRS jack pocket (LCSC SMT jack on the leg CARRIER PCB, mouth flush in the fill's flat face) + carrier seat + bottom-entry XH cavity (under the foot) + Ø5 off-axis cable bore. Same lying-flat print (pocket opens sideways, no bridges)"),
    "leg_foot":        (lambda: heal(LG.leg_foot()),    "tpu/leg_foot.step",    "TPU — foot cap ×4"),
    "leg_socket_trrs": (lambda: heal(LG.leg_socket_trrs()), "petg-gf/leg_socket_trrs.step", "PETG-GF — the -X/+Y leg's socket ×1: leg_socket + the vertical chassis-jack way (Tensility 10-03404, coaxial with the thread — the column-top plug BLIND-MATES on the final turn) + mouth-seat boss + tenon cable channel. Jack drops in before glue-up"),
    "leg_plug_retainer": (lambda: heal(LG.leg_plug_retainer()), "pctg/leg_plug_retainer.step", "PCTG — press sleeve ×1: up the wired leg's top-segment bore under the CA-354S handle (insertion backstop; the spigot tip lip takes withdrawal)"),
    "socket_jack_slug": (lambda: heal(LG.socket_jack_slug()), "tpu/socket_jack_slug.step", "TPU — saddle slug ×1: tops the chassis jack in the socket way (insertion backstop after glue-up; side slot clears the cable exit)"),
    # ── SQUARE-LEG redesign, STAGE 1 (generators + eval prints; the round
    # legs still populate the assembly until the stack swap lands) ──
    "leg_seg_body":    (lambda: heal(LG.leg_seg_body()), "petg-gf/leg_seg_body.step", "PETG-GF — square 44 segment BODY ×8 (redesign): prints LYING on the -Y face (layer lines along the leg — kick loads bulk GF); square-32 core takes the glued thread couplers; +Y face = lidded cable channel"),
    "leg_coupler_m":   (lambda: heal(LG.leg_coupler_m()), "pctg/leg_coupler_m.step", "PCTG — male thread coupler ×8 (redesign): prints STANDING (thread quality); glues into a body core end; Ø40 collar hard stop + Ø36/30 single-start spigot unchanged"),
    "leg_coupler_f":   (lambda: heal(LG.leg_coupler_f()), "pctg/leg_coupler_f.step", "PCTG — female thread coupler ×8 (redesign): prints STANDING mouth-down; gland + rim hard-stop ring in its face; internal thread through the glue plug"),
    "leg_lid":         (lambda: heal(LG.leg_lid()), "petg-gf/leg_lid.step", "PETG-GF — leg channel LID ×8 (redesign): 45° dovetail strip, slides over the body's cable channel (bar-lid pattern; TPU nub SKU locks it)"),
    "leg_washer":      (lambda: heal(LG.leg_washer()),  "tpu/leg_washer.step",  "TPU — gland washer, 1/junction = segments+1 per leg (sits in the female-rim recess; the hard-stop collar squeezes it a fixed 2.5->2.0 every assembly)"),
    # pedal bar + latch (one latched foot for now; mirror to -X once the feel
    # is validated). The bar itself is a DEMO prism (longer than the bed —
    # it gets segmented for printing once the pedals land on it).
    "pedal_bar_a":     (lambda: heal(_PB("pedal_bar_a")), "petg-gf/pedal_bar_a.step", "PETG-GF — pedal bar, -X piece (TRRS foot + wiring trough + dovetail lid groove; splice tenons at its +X end). 322 long: place DIAGONALLY on the 255^2 bed; glue to pedal_bar_b"),
    "pedal_bar_b":     (lambda: heal(_PB("pedal_bar_b")), "petg-gf/pedal_bar_b.step", "PETG-GF — pedal bar, +X piece (plain snap foot; splice slots at its -X end). 292 long: diagonal print; slide down onto _a's tenons + glue"),
    "pedal_lid_a":     (lambda: heal(_PB("pedal_lid_a")), "petg-gf/pedal_lid_a.step", "PETG-GF — sliding dovetail lid, -X piece (covers the TRRS latch; bridges the bar splice). 241 long; print TOP-FACE DOWN (45-deg flanks)"),
    "pedal_lid_b":     (lambda: heal(_PB("pedal_lid_b")), "petg-gf/pedal_lid_b.step", "PETG-GF — sliding dovetail lid, +X piece (covers the plain latch; lock dimple clicks onto the bar-top nub, pinning both lid pieces — no screws). 322 long: diagonal, TOP-FACE DOWN"),
    "pedal_bolt":      (lambda: heal(_PB("pedal_bolt")), "petg-gf/pedal_bolt.step", "PETG-GF — latch slider + thumb pad, +X foot (IDENTICAL latch design at both feet: retract 15, slide the bar, release + thumb-press to the detent click; flat head bears on the shaft's key flat)"),
    "pedal_bolt_trrs": (lambda: heal(_PB("pedal_bolt_trrs")), "petg-gf/pedal_bolt_trrs.step", "PETG-GF — latch slider, -X foot: the SAME latch design with the TRRS MOUNT grown on (cradle carrying the male plug — that latch is also the connector actuator)"),
    "pedal_latch_finger": (lambda: heal(_PB("finger_part")), "tpu/pedal_latch_finger.step", "TPU — latch finger x2 (same print): +X foot = bolt return spring; -X foot = far-end KICK spring, engaged only over the last ~4.5 of opening (holding retracted is nearly free)"),
    "pedal_detent_nub": (lambda: heal(_PB("nub_part")), "tpu/pedal_detent_nub.step", "TPU — detent nub x3 (Ø4x4): two press into the lid over the posts (hold-closed clicks, TRRS-independent per user rule); one presses into the bar top as the LID lock"),
    "electronics_tray": (lambda: heal(__import__("src.electronics", fromlist=["e"]).electronics_tray()), "pctg/electronics_tray.step", "PCTG — compute-bay tray (drops into rail channels from above; tool-free SNAP mounts for Teensy+shield, Pi 5, 2x CS42448, buck, CAN transceiver — snap fingers need PCTG's ductility)"),
}
# Deck panels: each is a (base, colour) PAIR — same origin, print as ONE object
# with two filaments (the ha-keypad keycaps/keycaps_text pattern). The base is
# the transparent body + embossed fret lines; the _color part is the 1.6 mm top
# layer between the lines.
_TP = __import__("src.top_plate", fromlist=["e"])
for _i in range(len(_TP.segments)):              # placed deck panels (piece + fillers + UI/keyhead)
    PARTS[f"top_plate_{_i}"] = (
        (lambda i: lambda: heal(__import__("src.top_plate", fromlist=["e"]).segments[i]))(_i),
        f"pctg/top_plate_{_i}.step",
        "PCTG (transparent) — deck panel BASE: body + embossed fret lines/dots "
        f"(print AS ONE OBJECT with top_plate_{_i}_color; rides rail grooves, "
        "slides out -X; piece carries the pickup, mid panel the OLED + joystick)")
    PARTS[f"top_plate_{_i}_color"] = (
        (lambda i: lambda: heal(__import__("src.top_plate", fromlist=["e"]).segments_color[i]))(_i),
        f"pctg/top_plate_{_i}_color.step",
        f"PCTG (colour) — deck COLOUR layer (1.6 mm top band between the fret lines; "
        f"print AS ONE OBJECT with top_plate_{_i}). PCTG, not PETG-GF: the deck is the "
        "forearm rest — no glass fiber on skin-contact surfaces, and same-resin pairs "
        "weld/purge cleanest")
for _i in range(len(_TP.spare_fillers)):         # fillers for the other pickup-piece slots
    PARTS[f"top_plate_spare_{_i}"] = (
        (lambda i: lambda: heal(__import__("src.top_plate", fromlist=["e"]).spare_fillers[i]))(_i),
        f"pctg/top_plate_spare_{_i}.step",
        "PCTG (transparent) — filler-band BASE for an alternate pickup-piece "
        f"position (print AS ONE OBJECT with top_plate_spare_{_i}_color; install "
        "the ones the piece doesn't cover)")
    PARTS[f"top_plate_spare_{_i}_color"] = (
        (lambda i: lambda: heal(__import__("src.top_plate", fromlist=["e"]).spare_fillers_color[i]))(_i),
        f"pctg/top_plate_spare_{_i}_color.step",
        f"PCTG (colour) — filler-band COLOUR layer (print AS ONE OBJECT with "
        f"top_plate_spare_{_i}; skin-contact surface — no glass fiber)")
for _i, _seg in enumerate(chassis_segments):     # chassis split into dovetailed segments
    PARTS[f"chassis_{_i}"] = (partial(heal, _seg), f"petg-gf/chassis_{_i}.step",
                              "PETG-GF — chassis segment (slide-down dovetail, glued)")


# Anchor ALL outputs to the project folder (never the cwd — see Archive/3D/CLAUDE.md)
OUT = pathlib.Path(__file__).resolve().parents[1]


def _export(name):
    builder, path, note = PARTS[name]
    dest = OUT / path
    dest.parent.mkdir(parents=True, exist_ok=True)   # material folder (petg-gf/pctg/tpu)
    export_step(builder(), str(dest))
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
    row_x = NB.clamp_row_x(i)
    out.append((f"break_dowel_{i}", C.dowel().translate(               # centred in its seat (0.4 clr
        (D.NUT_BLOCK_X, D.nut_y(i), D.STRING_Z - g - D.NUT_PIN_D / 2))))  # all round); pin top at Z−g
    out.append((f"set_screw_{i}", C.set_screw().translate(             # cup tip on the CLAMPED string
        (D.NUT_BLOCK_X + row_x, D.nut_y(i),                            # (per-string floor); tail proud
         D.STRING_Z + NB.clamp_floor(i) + D.NUT_SCREW_L + g))))
    out.append((f"nut_insert_{i}", C.m4_insert().translate(           # Ø6×5 heat-set insert (the screw
        (D.NUT_BLOCK_X + row_x, D.nut_y(i),                            # threads into it), in its roof pocket
         D.STRING_Z + NB.INSERT_GAP + NB.INSERT_L))))                  # (pocket floor INSERT_GAP, up INSERT_L)
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
    # dead end: break edge → clamp, then on out the exit curve and down into the Z stow bore
    out = out.union(_rod(brk, cq.Vector(D.NUT_BLOCK_X + NB.clamp_row_x(i), D.nut_y(i),
                                        D.STRING_Z + NB.clamp_floor(i) + g / 2.0), rad))
    out = out.union(_stow_tail(i, rad))
    return out


def _stow_tail(i, rad):
    """DEMO: the clamped string's free end continuing past the clamp -- flat to the exit-curve
    start, angled down (EXIT_ANGLE) out the -X face, then looping into the keyhead Z stow bore
    (face mouth → inward arc → straight down to the bed). Shows where each cut end tucks away."""
    from . import keyhead_endplate as KE
    ny = D.nut_y(i)
    cz = D.STRING_Z + NB.clamp_floor(i) + D.STRING_GAUGE[i] / 2.0       # centreline on the clamp floor
    R_e = (NB.EXIT_X0 - NB.EXIT_X1) / math.sin(math.radians(NB.EXIT_ANGLE))
    drop = R_e * (1.0 - math.cos(math.radians(NB.EXIT_ANGLE)))          # exit-curve drop at the -X face
    pts = [cq.Vector(D.NUT_BLOCK_X + NB.clamp_row_x(i), ny, cz),        # clamp
           cq.Vector(D.NUT_BLOCK_X + NB.EXIT_X0,        ny, cz),        # flat run to the exit start
           cq.Vector(D.NUT_BLOCK_X + NB.EXIT_X1,        ny, cz - drop)] # down the exit to the face
    # the stow bore: -X-face mouth, a 45° inward arc to x=ZHOLE_X, then straight down to the bed
    R = (KE.ZHOLE_X - KE.XLO) / (1.0 - math.cos(math.radians(45.0)))
    zj, cx = KE.Z6 - R * math.sin(math.radians(45.0)), KE.ZHOLE_X - R
    pts.append(cq.Vector(KE.XLO, ny, KE.Z6))                            # bore mouth at the -X face
    M = 8
    for k in range(1, M + 1):
        th = math.radians(45.0 * (1.0 - k / M))                        # 45° → 0° around the arc
        pts.append(cq.Vector(cx + R * math.cos(th), ny, zj + R * math.sin(th)))
    pts.append(cq.Vector(KE.ZHOLE_X, ny, CH.Z_BOT))                    # down the bore to the bed
    out = None
    for a, b in zip(pts[:-1], pts[1:]):
        seg = _rod(a, b, rad)
        out = seg if out is None else out.union(seg)
    return out


PICKUP_X = -50.0     # pickup centre in the shown pose (the 50 mm spec). The clamp
                     # gives +/-10 fine X (= the 20 mm slot/2 -> continuous), and
                     # re-slotting the 3-band piece (5 positions) moves it coarsely
                     # bridge<->neck; full reach ~ -37.5..-127.5.


def _pickup_mount_components():
    from . import top_plate as TP
    # pickup rests on the Z-plate, +Y face seated against the plate's +Y flange
    py = (TP.HY_REF - 0.3 - TP.FLG_T) - PM.PK_L / 2
    out = [("pickup", PM.pickup_demo().translate((PICKUP_X, py, PM.PK_TOP))),
           ("pickup_zplate", TP.pickup_zplate),
           ("pickup_xclamp", TP.pickup_xclamp.translate((PICKUP_X - TP.PIECE_CTR, 0, 0)))]
    # ONE central height screw lifts the Z-plate from below (one knob sets height;
    # the plate's +Y flange rides the full-height carrier track to keep it flat)
    out.append(("height_screw",
                PM.height_screw().translate((TP.HEIGHT_HOLE, 0.0, TP.ZPL_BOT))))
    # clamp screw in whichever -Y skirt hole sits nearest the pickup; its tip drives
    # the shim +Y, pinning the pickup against the +Y flange (the shim spreads load)
    cx = min(TP.CLAMP_HOLES, key=lambda h: abs(h - PICKUP_X))
    sc = PM.clamp_screw().rotate((0, 0, 0), (0, 0, 1), 180)      # head -Y, tip +Y
    out.append(("clamp_screw", sc.translate((cx, -53.75, TP.CL_Z))))
    return out


LEG_HEIGHT = 655.0   # floor → body bottom (the user's reference at 6')
LEG_SEGMENTS = 2     # coarse height: each segment steps 142; the shaft's 160
                     # slide overlaps the step, so every height ≥ ~241 is
                     # reachable by picking the count (2 covers 525..685)


def _leg_components():
    from . import chassis as CH
    out = []
    socket = LG.leg_socket()
    seg, sleeve = LG.leg_segment(), LG.leg_sleeve()
    shaft, foot, washer = LG.leg_shaft(), LG.leg_foot(), LG.leg_washer()
    ground = CH.Z_BOT - LEG_HEIGHT
    step = 2.0 + (LG.SEG_L - LG.TH_LEN)                  # collar gap + segment
    k = 0
    for sx in CH.LEG_STATIONS_X:           # stations computed from the shared endplate model
        for ry, rot in ((CH.Y_HI, 180), (CH.Y_LO, 0)):   # plate faces outward
            zb = CH.Z_BOT - LG.BARREL_L                  # barrel bottom
            wired = (sx, ry) == (CH.LEG_STATIONS_X[1], CH.Y_HI)
            sock = LG.leg_socket_trrs() if wired else socket
            out.append((f"leg_socket_{k}",
                        sock.rotate((0, 0, 0), (0, 0, 1), rot)
                        .translate((sx, ry, CH.Z_BOT))))
            # (thread phase is built into the female generators — all joints
            # share the same 3 mm offset, so parts place with no relative
            # rotation. The SINGLE-start thread is not 180°-symmetric, so the
            # rotated +Y-rail socket clocks its whole stack 180 with it —
            # exactly what the hard-stop junctions do physically. The shaft
            # flats/waist are 180°-symmetric, so the pedal bar doesn't care.)
            shoulder = zb                                # next male's collar seat
            for j in range(LEG_SEGMENTS):
                out.append((f"leg_washer_{(LEG_SEGMENTS + 1) * k + j}",
                            washer.translate((sx, ry, shoulder))))
                shoulder -= step
                out.append((f"leg_segment_{LEG_SEGMENTS * k + j}",
                            seg.rotate((0, 0, 0), (0, 0, 1), rot)
                            .translate((sx, ry, shoulder))))
            out.append((f"leg_washer_{(LEG_SEGMENTS + 1) * k + LEG_SEGMENTS}",
                        washer.translate((sx, ry, shoulder))))
            out.append((f"leg_sleeve_{k}",
                        sleeve.rotate((0, 0, 0), (0, 0, 1), rot)
                        .translate((sx, ry, shoulder - 2))))
            # the -X/+Y leg carries the TRRS-jack shaft variant (same base
            # name: the whitelist pairs and colours apply unchanged)
            sh = (LG.leg_shaft_trrs()
                  if (sx, ry) == (CH.LEG_STATIONS_X[1], CH.Y_HI) else shaft)
            out.append((f"leg_shaft_{k}",
                        sh.rotate((0, 0, 0), (0, 0, 1), rot)
                        .translate((sx, ry, ground + 3.0))))
            out.append((f"leg_foot_{k}", foot.translate((sx, ry, ground))))
            if wired:
                # leg↔body TRRS blind-mate hardware (socket-local builders,
                # rotated with the stack, lifted to the rail bottom)
                for nm, bldr in (("chassis_trrs_jack", LG.chassis_trrs_jack),
                                 ("leg_column_plug", LG.leg_column_plug),
                                 ("socket_jack_slug", LG.socket_jack_slug)):
                    zoff = 31.3 if nm == "socket_jack_slug" else 0.0
                    out.append((nm, bldr().rotate((0, 0, 0), (0, 0, 1), rot)
                                .translate((sx, ry, CH.Z_BOT + zoff))))
                out.append(("leg_plug_retainer",
                            LG.leg_plug_retainer()
                            .rotate((0, 0, 0), (0, 0, 1), rot)
                            .translate((sx, ry, CH.Z_BOT - 40.5))))
                # the column CA-354S cable: plug spring -> down the segment
                # cores/sleeve -> INTO the shaft's Ø6 bore, meeting the
                # shaft-side model (pedal_trrs_cable_leg) at the bar band
                from . import wiring as WR
                # column cable in two straight runs bracketing the COIL
                # (heat-set: wind the CA-354S mid-span on a Ø8 mandrel,
                # ~85 °C / 15 min — a one-time bench step). The coil parks
                # in the lower segment's Ø22 core and self-absorbs the
                # shaft's 160 of fine-height slack: raising stretches it,
                # lowering lets it retract — the musician only ever
                # touches the pinch screw. Drawn at the build's height;
                # bottom run jogs to the shaft channel's top.
                out.append(("leg_column_cable", WR._wire([
                    (sx, ry, CH.Z_BOT - 38.0),
                    (sx, ry, CH.Z_BOT - 190.0)], 3.7).union(WR._wire([
                        (sx, ry, CH.Z_BOT - 285.0),
                        (sx, ry, ground + 224.0),
                        (sx + 6.07, ry - 4.74, ground + 214.0)], 3.7))))
                coil = cq.Workplane("XY").add(cq.Solid.makeCylinder(
                    8.0, 95.0, cq.Vector(sx, ry, CH.Z_BOT - 285.0),
                    cq.Vector(0, 0, 1))).cut(
                    cq.Workplane("XY").add(cq.Solid.makeCylinder(
                        4.5, 97.0, cq.Vector(sx, ry, CH.Z_BOT - 286.0),
                        cq.Vector(0, 0, 1))))
                out.append(("leg_cable_coil", coil))
                # the chassis jack's factory cable: axial exit, 90° out the
                # tenon channel (inner face), down to the floor, landing on
                # the bus-B socket tee (12)
                iy = -1.0 if ry > 0 else 1.0             # inboard sign
                out.append(("chassis_trrs_cable", WR._wire([
                    (sx, ry, CH.Z_BOT + 31.8),
                    (sx, ry, CH.Z_BOT + 34.5),
                    (sx, ry + iy * 8.0, CH.Z_BOT + 35.5),
                    (-605.5, 46.0, -45.0),
                    (-605.5, 46.0, -72.5),      # through the tray's notch
                    (-592.0, 44.5, -72.5),
                    (-590.0, 44.5, WR.HDR_Z)], 3.8)))
            k += 1
    return out


def _pedal_bar_components():
    """Pedal bar + latch, modelled in absolute X/Y with z0 = plate bottom =
    the shaft waist's lower shoulder (foot top): lift by ground + FOOT_H."""
    from . import pedal_bar as PB
    dz = (CH.Z_BOT - LEG_HEIGHT) + LG.FOOT_H
    return [(n, wp.translate((0, 0, dz))) for n, wp in PB.assembly_parts()]


def _electronics_components():
    """The compute bay (PRO population shown; a basic build leaves the Pi /
    CS stack / buck sockets empty) + panel jacks + the wire harness."""
    from . import electronics as EL
    from . import wiring as WR
    from . import top_plate as TP
    out = [("electronics_tray", EL.electronics_tray()),
           ("pi5", EL.pi5()), ("teensy_stack", EL.teensy_stack()),
           ("cs_stack", EL.cs_stack()), ("buck", EL.buck()),
           ("teensy_ifc", EL.teensy_ifc()),
           ("analog_frontend", EL.analog_frontend()),
           ("ts_jack", EL.ts_jack()), ("dc_jack", EL.dc_jack()),
           ("usbc_jack", EL.usbc_jack()),
           ("oled", EL.oled()), ("joystick", EL.joystick())]
    out += [(f"top_plate_{i}", seg) for i, seg in enumerate(TP.segments)]
    out += [(f"top_plate_color_{i}", seg) for i, seg in enumerate(TP.segments_color)]
    # the fillers the pickup piece displaced: show them slid +Y clear of the
    # instrument (exploded), but at the true X/Z where they'd seat if the pickup
    # weren't there -- so it reads as "pull these, drop in the pickup piece".
    # Base + colour move by the SAME dy (from the base's bbox) so the pair stays
    # aligned as printed.
    from . import chassis as CH
    rail_outer = CH.Y_HI + CH.T / 2
    for i, (f, fc) in enumerate(zip(TP.spare_fillers, TP.spare_fillers_color)):
        dy = (rail_outer + 8.0) - f.val().BoundingBox().ymin
        out.append((f"top_plate_{len(TP.segments) + i}", f.translate((0, dy, 0))))
        out.append((f"top_plate_color_{len(TP.segments_color) + i}",
                    fc.translate((0, dy, 0))))
    out += WR.tee_components()
    out += WR.build_wires()
    return out


def _knee_lever_components():
    """Knee lever (LKL) — input-side control, mounted in its rib bay (centre x=-501): the
    christmas-tree tenons slide +Y into the two flanking ribs; chassis.py cuts the grooves.
    Set KNEE_THROW_DEG=<angle> to pose the lever at that throw (rotate about the Y axle + slide the
    followers to ride the lobe) instead of at rest -- demonstrates the swept position in the assembly."""
    from . import knee_lever as KL
    import os
    throw = float(os.environ.get("KNEE_THROW_DEG", "0") or "0")
    def swing(s):                                        # rotate a lever-attached solid about the Y axle
        return s.rotate((0, 0, 0), (0, 1, 0), throw) if throw else s
    thr, eng = math.radians(throw), math.radians(KL.HS_ENGAGE_DEG)
    s_main = KL.LOBE_RC * math.sin(thr) if throw else 0.0            # MAIN follower engaged from rest
    s_hs = (KL.LOBE_RC * (math.sin(thr) - math.sin(eng)) + 1.0) if throw > KL.HS_ENGAGE_DEG else 0.0  # engages @15°
    pose = KL.MOUNT_POSE
    out = [("knee_housing", KL.knee_housing), ("knee_lever", swing(KL.knee_lever))]
    for nm, off, s in (("main", KL.CART_MAIN_OFFSET, s_main), ("half_stop", KL.CART_HALFSTOP_OFFSET, s_hs)):
        out.append((f"{nm}_cart_base", KL.feel_place(KL.cart_base.translate(off))))
        out.append((f"{nm}_cart_piston", KL.feel_place(KL.cart_piston.translate(off)).translate((-s, 0, 0))))
        out.append((f"{nm}_guide_post", KL.feel_place(KL.guide_post.translate(off))))
    for n, s in KL.demo_parts():                         # magnet spins with the lever; the rest are stationary
        out.append((n, swing(s) if n == "kl_magnet" else s))
    for i, rx in enumerate(KL.RAIL_X):                    # one floating tenon per rail (both -X of the axle)
        out.append((f"floating_tenon_{i}", KL.floating_tenon.translate((rx, 0, 0))))
    return [(n, s.translate(pose)) for n, s in out]


def collect_components():
    comps = [
        ("bridge_endplate", bridge_endplate),
        ("bridge_bearings", C.bridge_bearings()),
        ("keyhead_endplate", __import__("src.keyhead_endplate", fromlist=["e"]).keyhead_endplate),
    ]
    comps += [(f"chassis_{i}", seg) for i, seg in enumerate(chassis_segments)]
    comps += _pickup_mount_components()
    comps += _leg_components()
    comps += _pedal_bar_components()
    comps += _electronics_components()
    comps += _knee_lever_components()
    for i in range(D.N_STRINGS):
        comps.extend(_string_components(i))
    return comps


# Per-part colours, baked into the assembly STEP (single source of truth — they
# show in the shared FreeCAD live viewer and any STEP viewer). RGB floats 0..1.
_COLORS = {
    "carriage":        (0.27, 0.51, 0.71),   # PETG-GF — load-critical
    "bridge_endplate": (0.39, 0.58, 0.93),   # PETG-GF — load-critical
    "keyhead_endplate": (0.42, 0.50, 0.62),   # PETG-GF — keyhead endplate + nut block (merged)
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
    "break_dowel":     (0.75, 0.75, 0.78),   # steel dowel (gauged break pin)
    "set_screw":       (0.55, 0.55, 0.58),   # alloy set screw
    "chassis":         (0.46, 0.52, 0.55),   # PETG-GF frame
    "pickup":          (0.10, 0.10, 0.12),   # DEMO pickup body
    "pickup_zplate":   (0.85, 0.65, 0.30),   # PCTG height plate (under the pickup)
    "pickup_xclamp":   (0.90, 0.55, 0.20),   # PCTG clamp shim
    "height_screw":    (0.72, 0.72, 0.75),   # M4 height set-screw (lifts the plate)
    "clamp_screw":     (0.55, 0.55, 0.58),   # M4 side clamp screw
    "leg_socket":      (0.36, 0.42, 0.46),
    "leg_socket_trrs": (0.36, 0.42, 0.46),
    "leg_plug_retainer": (0.42, 0.48, 0.52),
    "socket_jack_slug": (0.12, 0.12, 0.13),  # TPU
    "chassis_trrs_jack": (0.62, 0.64, 0.67),
    "leg_column_plug":  (0.32, 0.36, 0.58),  # slate, matches the bar plug
    "chassis_trrs_cable": (0.45, 0.45, 0.48),
    "leg_column_cable": (0.45, 0.45, 0.48),
    "leg_cable_coil":  (0.45, 0.45, 0.48),   # heat-set coil section (slack
                                             # take-up in the segment core)
    "leg_segment":     (0.42, 0.48, 0.52),
    "leg_sleeve":      (0.36, 0.42, 0.46),
    "leg_shaft":       (0.55, 0.58, 0.62),
    "leg_foot":        (0.12, 0.12, 0.13),   # TPU
    "leg_washer":      (0.12, 0.12, 0.13),   # TPU
    # pedal bar (2 spliced pieces + 2 dovetail-lid pieces) + latches
    "pedal_bar_a":      (0.30, 0.45, 0.35),  # PETG-GF bar, -X piece
    "pedal_bar_b":      (0.33, 0.48, 0.38),  # PETG-GF bar, +X piece
    "pedal_lid_a":      (0.50, 0.58, 0.52),  # dovetail lid, -X piece
    "pedal_lid_b":      (0.54, 0.62, 0.56),  # dovetail lid, +X piece
    "pedal_bolt":       (0.85, 0.35, 0.20),  # snap latch slider, +X foot
    "pedal_bolt_trrs":  (0.85, 0.35, 0.20),  # TRRS latch slider, -X foot
    "pedal_latch_finger": (0.12, 0.12, 0.13),  # TPU return finger (the only spring)
    "pedal_detent_nub": (0.12, 0.12, 0.13),  # TPU hold-closed detent nub
    "pedal_trrs_jack":  (0.62, 0.64, 0.67),  # leg-side female TRRS (DEMO)
    "pedal_trrs_plug":  (0.32, 0.36, 0.58),  # bar-side male plug (DEMO; slate
                                             # — black is reserved for TPU)
    # pedal TRRS link: Tensility CA-354S factory cables (Ø3.7 shielded 4C
    # jackets). Grey — NOT black (TPU-reserved); the per-wire gauge/shade
    # colours reappear at the crimped XH pigtails, not inside a jacket.
    "pedal_trrs_cable_bar": (0.45, 0.45, 0.48),  # cradle plug → first bar tee
    "pedal_trrs_cable_leg": (0.45, 0.45, 0.48),  # leg carrier → column top
    "pedal_leg_carrier": (0.10, 0.42, 0.18),     # leg carrier PCB (jack on
                                                 # top, XH header below)
    "build_counter":   (0.86, 0.08, 0.24),
    # knee lever (LKL) — input-side control
    "knee_housing":    (0.30, 0.36, 0.42),   # PCTG housing
    "knee_lever":      (0.27, 0.51, 0.71),   # PCTG lever/paddle
    "kl_axle":         (0.55, 0.58, 0.62),   # steel pin
    "kl_bearing":      (0.69, 0.77, 0.87),   # MR85ZZ
    "kl_magnet":       (0.80, 0.20, 0.20),   # diametric magnet
    "kl_pcb":          (0.05, 0.35, 0.15),   # MT6701 board (green)
    # feel parts (unified: two identical spring cartridges, main -Y + half-stop +Y)
    "main_spring":                        (0.55, 0.20, 0.75),
    "half_stop_spring":                   (0.75, 0.45, 0.88),
    "main_spring_tension_setscrew":       (0.55, 0.55, 0.58),
    "half_stop_spring_tension_setscrew":  (0.62, 0.62, 0.66),
    "main_cart_base":                     (0.85, 0.65, 0.13),   # printed cartridge (shared part)
    "main_cart_piston":                   (0.95, 0.80, 0.30),
    "half_stop_cart_base":                (0.80, 0.60, 0.10),
    "half_stop_cart_piston":              (0.92, 0.76, 0.26),
    "main_guide_post":                    (0.70, 0.50, 0.10),
    "half_stop_guide_post":               (0.66, 0.46, 0.08),
    "retention_setscrew":                 (0.40, 0.40, 0.43),   # -Y lock screw
    "floating_tenon":  (0.90, 0.55, 0.10),   # glued christmas-tree tenon (printed)
    # electronics bay (dummies) + panel jacks
    "electronics_tray": (0.30, 0.36, 0.32),  # printed tray
    "pi5":             (0.05, 0.35, 0.15),   # PCB green
    "teensy_stack":    (0.10, 0.45, 0.30),
    "cs_stack":        (0.15, 0.25, 0.50),
    "buck":            (0.35, 0.30, 0.50),
    "teensy_ifc":      (0.55, 0.25, 0.25),   # Teensy interface PCB (2x CAN
                                             # transceiver + XH headers)
    "tee_pcb":         (0.10, 0.42, 0.18),   # trunk-and-drop bus tee PCBs
    "analog_frontend": (0.20, 0.45, 0.40),   # bridge-end buffer + relay board
    "top_plate":       (0.88, 0.91, 0.94),   # transparent-PCTG deck base + fret lines
    "top_plate_color": (0.30, 0.33, 0.38),   # colour-PCTG deck layer (skin contact)
    "oled":            (0.05, 0.05, 0.08),   # screen (perfect-black OLED)
    "joystick":        (0.15, 0.15, 0.17),   # UI control
    "ts_jack":         (0.62, 0.64, 0.67),
    "dc_jack":         (0.62, 0.64, 0.67),
    "usbc_jack":       (0.62, 0.64, 0.67),
    # wire harness: HUE = gauge bucket, SHADE = the specific wire in the bucket
    #   blue = 20 AWG power | red = 26 AWG CAN | green = 28 AWG shielded audio
    #   amber = 28 AWG logic | violet = shielded USB-2
    "wire_pwr_hot":    (0.08, 0.20, 0.60),   # dark blue   - 24 V hot
    "wire_pwr_gnd":    (0.45, 0.65, 0.95),   # light blue  - 24 V ground/return
    "wire_can":        (0.80, 0.10, 0.10),   # red         - bus A CAN (crimped
                                             #   XH trunk segments, tee to tee)
    "wire_canb":       (0.95, 0.35, 0.30),   # light red   - bus B CAN (inputs)
    "motor_pigtail":   (0.45, 0.45, 0.48),   # grey        - SERVO42D's own 6-pin
                                             #   XH pigtail (factory jacket)
    "wire_knee_drop":  (0.45, 0.45, 0.48),   # grey        - LKL drop stub
    "wire_pickup":     (0.55, 0.85, 0.55),   # lightest green - shielded: pickup -> AFE
    "wire_audio":      (0.30, 0.72, 0.40),   # light green - shielded: AFE -> ADC
    "wire_dac":        (0.10, 0.52, 0.28),   # dark green  - shielded: DAC -> AFE
    "wire_out":        (0.04, 0.34, 0.18),   # darkest green - shielded: relay -> jack
    "wire_relayctrl":  (0.98, 0.88, 0.35),   # lightest amber - relay control
    "wire_link":       (0.95, 0.72, 0.22),   # light amber - Teensy <-> Pi
    "wire_canjmp":     (0.90, 0.58, 0.14),   # amber       - Teensy <-> transceiver
    "wire_tdm":        (0.80, 0.46, 0.10),   # deep amber  - CS stack -> Pi
    "wire_oled":       (0.68, 0.36, 0.08),   # brown-amber - OLED -> Teensy
    "wire_joy":        (0.54, 0.28, 0.08),   # darkest amber - joystick -> Teensy
    "wire_usb":        (0.55, 0.25, 0.75),   # violet      - shielded USB-2 -> Pi
}
_DEFAULT_COLOR = (0.80, 0.80, 0.80)
_TPU_BLACK = (0.03, 0.03, 0.03)                  # ALL TPU parts render black (user rule)
# every part whose output path is tpu/... -> black, regardless of instance prefix/suffix
_TPU_BASES = tuple(sorted((k for k, v in PARTS.items() if v[1].startswith("tpu/")), key=len, reverse=True))


def _color_for(name):
    head, _, tail = name.rpartition("_")
    base = head if (head and tail.isdigit()) else name
    if base in _TPU_BASES or any(base.endswith(k) for k in _TPU_BASES):
        return cq.Color(*_TPU_BLACK)             # TPU is always black
    return cq.Color(*_COLORS.get(base, _DEFAULT_COLOR))


def _export_assembly():
    build_n = _bump_build_counter()
    asm = cq.Assembly(name="public_steel_guitar")
    for name, wp in collect_components():
        asm.add(wp, name=name, color=_color_for(name))
    counter = _build_counter_model(build_n)
    if counter is not None:
        asm.add(counter, name="build_counter", color=_color_for("build_counter"))
    # ATOMIC write: the 30+ MB STEP takes seconds to save, and the viewer's
    # file-watcher must never see (and import) a half-written file — save to a
    # temp name, then rename into place (one mtime event, complete file).
    asm.save(str(OUT / "assembly.step.tmp"), exportType="STEP")
    os.replace(OUT / "assembly.step.tmp", OUT / "assembly.step")
    print(f"Wrote assembly.step  [build #{build_n}]", flush=True)
    print(geometry_report())
    show(str(OUT / "assembly.step"))   # open/refresh it in the shared FreeCAD hub


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
