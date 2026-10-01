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
import re
import sys
import time
from functools import partial

import cadquery as cq

# Shared CAD utilities, vendored at <project>/cadkit (git subtree). show() makes the
# build's output viewable — opens/refreshes its tab in the FreeCAD hub. Never raises.
from cadkit.freecad import show
from cadkit.step_export import export_step
try:                                    # optional on-every-build face-count regression gate
    from tools.build_profile import (record_part, report_build_regressions,
                                     write_part_volumes)
except Exception:                       # a profiling hook must NEVER break a build
    def record_part(*a, **k): pass
    def report_build_regressions(): return 0
    def write_part_volumes(*a, **k): return 0

from . import dimensions as D
from elec import harness as _EH           # the PCB's pin order, single-sourced
from .helpers import heal
from . import components as C
from . import chassis as CH
from .components import MOTOR_PULLEY_STANDOFF
from .bridge_endplate import bridge_endplate
from . import bridge_endplate as BE
from . import belt_tensioner as BTn
from .chassis import segments as chassis_segments
from .chassis import segments_light as chassis_light
from . import nut_block as NB
from . import ui_panel as UI
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


def _PB_bar(attr):
    """A pedal-bar piece with its pedal HOUSINGS fused in (user: the housing is
    not a separate part — see foot_pedal.fuse_into_bar). Fused here, not in
    pedal_bar, because foot_pedal reads pedal_bar for the bar's faces and the
    import has to stay one-way.

    The piece's X span comes from pedal_bar.PIECE_SPAN, not from the caller: the
    assembly needs the same fusion and passing the range in twice is what let the
    two disagree (the assembly kept the unfused bar for the pedals' whole life)."""
    FP = __import__("src.foot_pedal", fromlist=["e"])
    PB = __import__("src.pedal_bar", fromlist=["e"])
    span = PB.PIECE_SPAN[attr]
    # heal BEFORE the threads and not after: thread rules (cut last and alone,
    # never heal a threaded part). That is also why the heal lives here rather
    # than in the PARTS lambda, which used to wrap this call.
    piece = FP.cut_feel_access(heal(FP.fuse_into_bar(_PB(attr), *span)), *span)
    return FP.cut_wire_ways(piece, *span)


PARTS = {
    "bridge_endplate": (partial(heal, bridge_endplate), "petg-gf/bridge_endplate.step", "PETG-GF — fused bridge end (screw support + bearing support + axle comb + box closure)"),
    "keyhead_endplate": (lambda: heal(__import__("src.keyhead_endplate", fromlist=["e"]).keyhead_endplate), "petg-gf/keyhead_endplate.step", "PETG-GF — merged keyhead (-X) endplate + nut block (25 mm, one piece): closes the box, caps the deck grooves, gauged break-edge + 2-row clamps; drops in last, held by 1 screw"),
    "knee_housing":    (lambda: __import__("src.knee_lever", fromlist=["e"]).knee_housing, "petg-gf/knee_housing.step", "PETG-GF — knee-lever (LKL) housing: ONE parametric prism derived from the lever/cartridge/body extents, minus the house-pockets, backstop threads + lever room, plus FOUR fused octagon mount tenons on the top face (one per chassis rib crossing; the +X-most survives only as a stub over each cheek) and the MT6701 board CRADLE on the +Y face (grooves + plinth + floor; the board drops in from +Z with the lever OFF the instrument and the chassis underside becomes its lid — no retaining screw. Ø14 driver bore reserved for the magnet cap, plus a relief channel through the cheek and the -X web for the board's side-entry CAN connector and its plug). Retention is all on -X: the +X web stops at the plinth top so NOTHING stands +X of the prism face. Depth lock deferred"),
    "knee_lever":      (lambda: __import__("src.knee_lever", fromlist=["e"]).knee_lever,   "pctg/knee_lever.step",   "PCTG — knee-lever (LKL) arm + knee paddle (takes knee strikes: toughness over stiffness); the +Y axle journal + magnet stub print INTEGRAL (stand off the lying -Y bed face)"),
    "kl_axle": (lambda: __import__("src.knee_lever", fromlist=["e"]).kl_axle, "pctg/kl_axle.step", "PCTG — knee-lever AXLE ×1: ONE full-length part fitted LAST, slid +Y→−Y through bearing/lever/bearing (the old integral stub could never enter its bearing). Ø8 journals, D-FLAT key through the hub, flange land seating on the +Y inner race (= the air-gap datum), threaded magnet pocket, M4 thread-forming bore in the −Y tip for the retention screw + washer. Prints STANDING, POCKET-DOWN, with a brim"),
    "kl_magnet_cap": (lambda: __import__("src.knee_lever", fromlist=["e"]).kl_magnet_cap, "pctg/kl_magnet_cap.step", "PCTG — magnet CAP ×1: female-threaded HEX nut (9.35 across flats, for a 3/8-inch driver) screwing over the axle's pocket collar to clamp the Ø6 diametric disc; centre stays open so nothing intrudes on the air gap. Fit it BEFORE the sensor board. Prints APERTURE-DOWN"),
    "kv_housing":      (lambda: __import__("src.knee_lever_vert", fromlist=["e"]).kv_housing, "petg-gf/kv_housing.step", "PETG-GF — VERTICAL knee-lever (LKV) housing: same prism derivation as LKL but with the feel block TRANSLATED above the axle (not mirrored — the pocket gable stays up for printability), so the axle sits 19.2 lower and the arm has room to swing UP. Y is asymmetric (-16.10..+13.90): the -Y wall is 2.2 wider to fit TWO octagon tenons at the 23mm rib pitch, while the +Y sensor face is untouched. Tenons slide along local X (= the guitar's Y once posed). Carries the SAME sensor cradle as LKL (knee_lever._cradle, parameterised by the housing Z extents) - the board is just taller here, 31.2 vs 19. Rest stop deferred"),
    "kv_lever":        (lambda: __import__("src.knee_lever_vert", fromlist=["e"]).kv_lever, "pctg/kv_lever.step", "PCTG — VERTICAL knee-lever (LKV) arm: an L. Hub on the axle, a LEG rising +Z carrying the return lobe at 13.2 (sized so the 20° throw gives the SAME 4.51 spring stroke as LKL's 30°), and a 50mm ARM running +X that the knee lifts — 17.1 of paddle rise"),
    "cart_base": (lambda: __import__("src.knee_lever", fromlist=["e"]).cart_base, "pctg/cart_base.step", "PCTG — spring-cartridge (inverted-U, open -Z; shared: print 2, for main + half-stop)"),
    "cart_piston": (lambda: __import__("src.knee_lever", fromlist=["e"]).cart_piston, "pctg/cart_piston.step", "PCTG — spring-cartridge piston, flat follower tongue (shared: print 2)"),
    # NOT healed: cadkit.threads is explicit that heal()'s unify chokes on a threaded
    # solid. Both of these carry a pilot thread and both export fine unhealed.
    "screw_pulley_hi": (lambda: C.screw_pulley(high=True), "pctg/screw_pulley_hi.step",  "PCTG at a 0.2 NOZZLE — HIGH-plane screw pulley ×5. Prints FLANGE-DOWN — the full Ø11 bottom flange is the bed face and everything above it steps inward except the top flange, which is a 45° cone. No brim, no support. (A single part that FLIPPED to serve both planes was tried and dropped: it could only stand on a Ø5.6 boss, and a solid bed surface is worth more than the engagement it levelled — this SKU's 8.3 mm of formed thread is 2.5 MPa under the 147 N, ~10% of interlayer.) IT IS ALSO THE RETAINING COLLAR: its pilot-thread bore grips the rod and the string's 147 N jams it UP into the thrust bearings stacked straight on its pilot boss, so it needs no set screw, no clamp and no separate collar. Fine teeth AND a 0.3 mm thread groove both need the small nozzle and unfilled material"),
    "screw_pulley_lo": (lambda: C.screw_pulley(high=False), "pctg/screw_pulley_lo.step", "PCTG at a 0.2 NOZZLE — LOW-plane screw pulley ×5. The high-plane SKU plus an 11.2 mm column, which is what puts both SKUs' bosses on the ONE thrust plane while their bands sit BELT_PLANE_DZ apart. Prints FLANGE-DOWN like its twin"),
    "motor_pulley":    (lambda: heal(C.motor_pulley()),  "pctg/motor_pulley.step",  "PCTG — flanged 14T GT2 pulley, 45° outer flange — ×10"),
    "tension_fork":    (lambda: TF.tension_forks,    "pctg/tension_fork.step",    "PCTG — belt-tension lock forks, graded 3.0–6.0 set (4 of the fitting size per motor; positive stop in the slot, no friction reliance)"),
    # pickup carrier: the deck pickup-piece (a top_plate panel) holds the pickup on a
    # height plate lifted by 3 M4×20 button-head leadscrew jacks; a -Y M4 cup-tip grub
    # locks the pickup +Y against the plate's +Y wall. All hardware is stocked M4, all +Z.
    "ui_clamp":        (lambda: heal(__import__("src.ui_panel", fromlist=["e"]).clamp()), "petg-gf/ui_clamp.step", "PETG-GF - the UI clamp plate. It lies against the BOARD'S UNDERSIDE (3.2 thick, a relief under every footprint for the through-hole tails) and two M4x16 pull it up into the deck panel's own bosses, gripping the board between its whole top face and four bearings on the deck. An arm steps up past the board and runs +Y under the display to its far mounting-hole row, where two posts press the module's back into the window ledge - the screen's only positive retention. GF because it is a stiffness part. Prints PLATE-DOWN, its own flat underside on the bed, so every rib and post grows straight up off it"),
    "ui_knob":         (lambda: heal(__import__("src.ui_panel", fromlist=["e"]).knob()), "pctg/ui_knob.step", "PCTG - the UI cap: a O8 shank up through the deck and a O17 disc over it, bored O2.6x1.8 for the Alps shaft's tip. Prints DISC-DOWN (its own flat face on the bed), so the shank and the bore are both vertical and the bore's ceiling is the last thing printed. PCTG because it is the one part of the instrument a player touches every time they change a setting, and the deck it sits on is the same resin"),
    "pickup_zplate":   (lambda: heal(__import__("src.top_plate", fromlist=["e"]).pickup_zplate), "petg-gf/pickup_zplate.step", "PETG-GF — pickup height plate (green pickup area + nubs; 3 M4×20 button-head leadscrew jacks lift/tilt it via heat-set nuts on top, pickup rests on it and slides in X for tone; +Y retention wall + -Y cup-tip grub lock the pickup to the plate; GF keeps it flat on the point loads)"),
    # (the whole round-tube leg family — sockets, segments, thread couplers and
    #  washers — was DELETED 2026-08-01: 214 lines + 26 constants of unreachable
    #  code, kept through the square-leg swap and then never removed.
    # redesign — generators remain in legs.py until the refinement pass
    # deletes them)
    "leg_foot":        (lambda: heal(LG.leg_foot()),    "tpu/leg_foot.step",    "TPU — SHARED dovetail foot ×4 (user: one look): 44-sq pad + tenon into the underside mortise of the -Y leg blocks AND the pedal bar; the wired bar one covers the plug-threading access"),
    # (round leg_socket_trrs export retired — see leg_socket_sq_trrs)
    # ── SQUARE-LEG redesign, STAGE 1 (generators + eval prints; the round
    # legs still populate the assembly until the stack swap lands) ──
    # ("leg_coupler_m" export retired — ROUND 3: threadless, gasketless square legs)
    # ("leg_coupler_f" export retired — ROUND 3: threadless, gasketless square legs)
    # ("leg_lid" export retired — the wired cable runs up the column CENTER
    # through the flush-octagon joints' Ø7 bores; no face channel to cover)
    # ("leg_washer_sq" export retired — ROUND 3: threadless, gasketless square legs)
    # ("leg_washer" export retired — ROUND 3: threadless, gasketless square legs)
    # -- ONE LEG (user): the redesigned leg (src.leg_stack) at the -X/+Y corner, with its
    # body latch and the pedal bar's latch. The other three corners carry only a body
    # adapter. (The old square-leg family is retired from the assembly and from here;
    # its generators remain in legs.py, which still owns the body joinery.)
    "body_adapter":    (lambda: heal(LS.body_adapter()), "petg-gf/body_adapter.step", "PETG-GF — body adapter, -X/+Y corner (the leg): slides into the body's mortises along Y (two octagon ridges + the end-wall tongue in its rebate), one M4 shear pin down the rail + the endplate's lock pin; blind mortise below for the fixed tenon, with the body latch's pocket. Prints -Y -> +Y"),
    "body_adapter_px_py": (lambda: heal(LS.body_adapter(CH.LEG_STATIONS_X[0], CH.LEG_Y[0])), "petg-gf/body_adapter_px_py.step", "PETG-GF — body adapter, +X/+Y corner: the same adapter with its body joinery built for that corner (tongue toward +X)"),
    "body_adapter_px_my": (lambda: heal(LS.body_adapter(CH.LEG_STATIONS_X[0], CH.LEG_Y[1])), "petg-gf/body_adapter_px_my.step", "PETG-GF — body adapter, +X/-Y corner (tongue toward +X, screw down the -Y rail)"),
    "body_adapter_mx_my": (lambda: heal(LS.body_adapter(CH.LEG_STATIONS_X[1], CH.LEG_Y[1])), "petg-gf/body_adapter_mx_my.step", "PETG-GF — body adapter, -X/-Y corner (tongue toward -X, screw down the -Y rail)"),
    "fixed_sleeve":    (lambda: heal(LS.fixed_sleeve()), "petg-gf/fixed_sleeve.step", "PETG-GF — fixed sleeve: butts the adapter, pinned to the fixed tenon by one +X screw; the body latch's pad sits flush in its -Y face. Prints -Y -> +Y"),
    "adjust_sleeve":   (lambda: heal(LS.adjust_sleeve()), "petg-gf/adjust_sleeve.step", "PETG-GF — adjust sleeve: butts the fixed sleeve; one +X screw pins the fixed tenon, one sets the height through the adjust tenon's ladder. Prints -Y -> +Y"),
    "fixed_tenon":     (lambda: heal(LS.fixed_tenon()), "petg-gf/fixed_tenon.step", "PETG-GF — fixed floating tenon: adapter <-> fixed sleeve <-> adjust sleeve, houses the body latch slider and spring. Prints diagonally (+X+Y -> -X-Y)"),
    "adjust_tenon":    (lambda: heal(LS.adjust_tenon()), "petg-gf/adjust_tenon.step", "PETG-GF — adjust floating tenon: the height ladder (blind +X holes) and, at its bar end, the pedal bar latch's pocket and lead-in. Prints diagonally (+X+Y -> -X-Y)"),
    "leg_latch_slider": (lambda: heal(__import__("src.leg_latch", fromlist=["e"]).slider()), "pctg/leg_latch_slider.step", "PCTG — body latch slider: push-to-connect hook into the adapter, flush 20x20 pad on the fixed sleeve, one steel coil. Prints -X -> +X"),
    "bar_latch_frame": (lambda: heal(LS.bar_latch_frame()), "pctg/bar_latch_frame.step", "PCTG — pedal bar yoke latch: a ring round the adjust tenon, hook in its pocket, 20x20 pad flush in the collar, a cup seating its one coil. Prints ring down"),
    "bar_latch_collar": (lambda: heal(LS.bar_latch_collar()), "petg-gf/bar_latch_collar.step", "PETG-GF — pedal bar latch collar: the top 22.4 of the bar's tower, holding the yoke and its springs; two T rails slide it onto the tower from +Y, one M4x30 button head into a heat-set insert in the tower locks it. Prints on its +Y face"),
    # pedal bar (the per-foot latches are gone — the towers are passive
    # is validated). The bar itself is a DEMO prism (longer than the bed —
    # it gets segmented for printing once the pedals land on it).
    "pedal_bar_a":     (lambda: _PB_bar("pedal_bar_a"), "petg-gf/pedal_bar_a.step", "PETG-GF — pedal bar, -X piece (35.6 wide, flush with the slimmed leg blocks; fused WIRED tower; trough + lid groove; splice tenons at +X). ~219 long: prints STRAIGHT; _b drops onto the tenons, the LID locks the stack — no glue"),
    "pedal_bar_b":     (lambda: _PB_bar("pedal_bar_b"), "petg-gf/pedal_bar_b.step", "PETG-GF — pedal bar, MID piece (trough only; XS1 cavities -X, XS2 tenons +X). ~219 long: straight print; slides straight down onto _a's tenons (the lid is the Z lock — no glue)"),
    "pedal_bar_c":     (lambda: _PB_bar("pedal_bar_c"), "petg-gf/pedal_bar_c.step", "PETG-GF — pedal bar, +X piece (35.6 wide, flush with the slimmed leg blocks; fused PLAIN tower; splice cavities at -X). ~215 long: straight print; slides straight down onto _b's tenons (the lid is the Z lock — no glue)"),
    "pedal_lid_a":     (lambda: heal(_PB("pedal_lid_a")), "petg-gf/pedal_lid_a.step", "PETG-GF — sliding dovetail lid, -X piece (covers the TRRS latch; bridges bar splice XS1; carries the lock dimple). Goes in SECOND, and its -X end finishes FLUSH with the bar. 318 long: diagonal, TOP-FACE DOWN (45-deg flanks)"),
    "pedal_lid_b":     (lambda: heal(_PB("pedal_lid_b")), "petg-gf/pedal_lid_b.step", "PETG-GF — sliding dovetail lid, +X piece (covers the plain latch; bridges XS2). INSTALL BOTH FROM THE -X END: B first, run it the whole bar until it butts the 1.6 end wall, then A behind it — A's dimple clicks the nub and pins the stack. 317 long: diagonal, TOP-FACE DOWN"),
    # (pedal_bolt / pedal_bolt_trrs / pedal_latch_finger exports RETIRED by
    # ROUND 4 — the sliding latches are gone; the bar carries stub towers)
    "pedal_lever":     (lambda: heal(__import__("src.foot_pedal", fromlist=["e"]).pedal_lever()), "pctg/pedal_lever.step", "PCTG — FOOT PEDAL lever ×3 (initial design): hub on the axle, leg carrying the return lobe at 13.2 (sized so the 20° throw gives the SAME 4.51 spring stroke as the knee levers — which is what lets the half stop transfer for free), a 90 mm arm running out to the player and the pedal board across its end (30.8 mm of travel, ~1.6→3 N at the board)"),
    "pedal_detent_nub": (lambda: heal(_PB("nub_part")), "tpu/pedal_detent_nub.step", "TPU — detent nub ×1 (Ø4×4): presses into the bar top as the LID lock"),
    # (pedal_bar_foot merged into the shared leg_foot SKU — one look ×4)
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
# fuse each tee's drop-in PCB cradle (cadkit.pcb.pcb_cradle) into the chassis segment
# whose X-band owns that tee, so the cradle PRINTS AS PART of that segment. Each cradle's
# -Y wall merges into the -Y-rail inner face (a light cantilever bracket over the rib-top
# plane); the inboard bus-B tees (11,12) land on the nearest rib/bay structure. Verified:
# every cradle makes solid contact and each segment stays ONE connected solid. Done here
# (not in chassis.py) because chassis can't import wiring at module load (wiring imports
# chassis) -- build.py sits above both, so the fuse is clean.
from . import wiring as _WR_FUSE
_seg_edges = [CH._SHELL_PX + CH.KH_DT_DEPTH + 2.0] + sorted(CH.SPLIT_X, reverse=True) + [CH.X_NUT]
chassis_segments = list(chassis_segments)
# ⚠ THE MOTOR CONTROLLER'S FLOOR PORTS ARE CUT HERE, NOT IN chassis.py. chassis builds its
# segments at import and electronics imports chassis, so the chassis cannot ask where that
# board is without a circular import. The assembly knows both, so it does it (see
# electronics.mctrl_floor_ports).
from . import electronics as _EL_ports
# ⚠⚠ THE PI'S AND THE MOTOR BOARD'S CRADLES BELONG TO THE CHASSIS NOW, NOT TO THE ENDPLATE
# (user, 2026-09-28: "we need to be able to remove the endplate while leaving the pi and
# motor board in place"). Fused here for the same reason the floor ports are cut here -- the
# chassis cannot ask electronics where those boards are without a circular import -- and by
# the same route as wiring.tee_cradles below.
#
# ⚠ AND IT IS A DEFECT FIX AS WELL AS A FEATURE. Fused to the ENDPLATE, the motor frame's
# side walls ran down inside the chassis floor: 2717 mm3 of two printed parts occupying the
# same space, which check_overlaps never reported because {keyhead_endplate, chassis} is
# allow-listed wholesale for the endplate's own seating and hold-down screw. Fused to the
# CHASSIS the same walls are a root instead of an interference, and they are a better root
# than the endplate ever was: the motor board passes through the floor, so the slab grips it
# either side of its own port.
#
# BEFORE the port cuts, deliberately: the frames' walls sit outside the ports (walls at
# y -114.9 and -49.1 against a port spanning -113..-51), so cutting afterwards cannot take
# anything load-bearing away, and it guarantees the ports stay open whatever the frames do.
_kh_cr = _EL_ports.keyhead_cradles()
_kh_bb = _kh_cr.val().BoundingBox()
# ⚠ THE CRADLES REFILLED THE LEVER MORTISES, and the knee housing's tenons live in them.
# chassis.py cuts a mortise into every rib, then this union laid the cradles' feet back over
# the same band: 1986.6 mm3 of chassis_2 inside knee_housing, a 68 x 17 x 4.2 slab at
# z -77.5..-73.3. It is the endplate's cut-before-union fault in a new place (a union after a
# cut silently refills it), and it sat in the gate as the largest pair for weeks because the
# count was read as a baseline. The SAME cutters go through the cradles before they fuse.
from .chassis import _mort_cutters as _kh_mort_cutters
_kh_mc = _kh_mort_cutters(_kh_bb.xmin - 1.0, _kh_bb.xmax + 1.0)
if _kh_mc is not None:
    _kh_cr = _kh_cr.cut(_kh_mc)
_kh_hit = 0
for _csi, _cs in enumerate(chassis_segments):
    _sb = _cs.val().BoundingBox()
    if _sb.xmin <= _kh_bb.xmin and _kh_bb.xmax <= _sb.xmax + 1e-6:
        chassis_segments[_csi] = _cs.union(_kh_cr)
        _kh_hit += 1
        break
assert _kh_hit == 1, (
    "the board cradles (x %.1f..%.1f) did not fall inside exactly one chassis segment -- "
    "they landed in %d. A cradle that straddles a print split is two halves of a mount."
    % (_kh_bb.xmin, _kh_bb.xmax, _kh_hit))
# ⚠ AND ASK WHETHER THEY ATTACHED, because nothing else will. chassis._largest() bins the
# non-largest solids in a segment, but it runs at IMPORT -- before this union -- so a cradle
# that touches nothing survives here as a second solid and prints as a loose part. That is the
# exact failure keyhead_endplate's own assert was written for when it carried them: "the motor
# controller's came out a free-floating 18,121 mm3 lump, which the overlap gate cannot see --
# two solids that never touch do not interpenetrate". The question moves with the cradles.
_kh_n = len(chassis_segments[_csi].val().Solids())
assert _kh_n == 1, (
    "the chassis segment came out as %d disconnected solids after fusing the board cradles. "
    "One of them is not touching: the motor frame's side walls should run INTO the floor slab "
    "(board bottom edge z -80.85 against a floor top of -71.35) and the Pi's two legs should "
    "reach it with one bead of overlap. Check electronics.keyhead_cradles's root_d/foot "
    "against motor_bank.FLOOR_TOP." % _kh_n)
for _mp in _EL_ports.mctrl_floor_ports():
    for _csi in range(len(chassis_segments)):
        chassis_segments[_csi] = chassis_segments[_csi].cut(_mp)
# ⚠ AND THE FLAT PI'S ANCHOR, WHICH MUST BE CUT HERE AND NOT IN THE CRADLE. pcb_cradle bores
# its own boss, but that boss is EMBEDDED in the floor slab -- the M4 needs anchor_min_wall
# below the board's underside, which is deeper than the standoff -- so the floor's own
# material refills the bore the moment the cradle is unioned above. The gate caught exactly
# that: 43.9 mm3 of board_screw_2 and 37.5 of board_insert_2 inside chassis_2.
# Every segment, not `_csi`: that name was rebound by the loop just above, so it no longer
# points at the segment the cradle went into -- and the other cutters here sweep all segments
# for the same reason. A bore outside its own segment removes nothing.
if not os.environ.get("PI_NO_CRADLE"):          # see keyhead_cradles; debug sweeps only
    _pi_bore = _EL_ports.pi_hold_bore()
    for _csi in range(len(chassis_segments)):
        chassis_segments[_csi] = chassis_segments[_csi].cut(_pi_bore)
# (pi_cap_relief is GONE, and nothing replaces it. It pocketed 5.8 mm out of the bay's
#  -Y wall to admit the Pi cap's overhang; the Pi now sits +3.82 with the cap's face FLUSH
#  on that wall, so there is nothing to admit. The user's point was that the pocket cost
#  wall strength -- the answer is to not need it, not to make it smaller. See PI_FP.)
# ...and the LED strip's connector tails, for the same reason and by the same route.
for _lr in _EL_ports.led_wall_reliefs():
    for _csi in range(len(chassis_segments)):
        chassis_segments[_csi] = chassis_segments[_csi].cut(_lr)
_fused_segs = set()
for _cnm, _cr, (_ctx, _cty, _ctd) in _WR_FUSE.tee_cradles():
    for _csi in range(len(_seg_edges) - 1):
        if _seg_edges[_csi + 1] < _ctx < _seg_edges[_csi]:
            chassis_segments[_csi] = chassis_segments[_csi].union(_cr)
            _fused_segs.add(_csi)
            break
# ...then RE-CUT the knee/pedal lever rib mortises in whatever segment just gained a
# cradle. chassis._build_full() already cut them, but the fuse above puts material back
# INTO the segment and cradle 1 lands squarely in rib -478's mortise (24.9 mm^3 of it).
# That was latent until the cadkit fiber-clearance work grew the octagon 2.33 mm: the old
# tenon stopped short of the refill, the new one reaches it. A mortise has to survive
# everything fused in after it, so the cut belongs at the END of the segment pipeline.
from . import knee_lever as _KL_FUSE
for _csi in sorted(_fused_segs):
    _seg = chassis_segments[_csi]
    for _rx in CH._MORT_X:
        if _seg_edges[_csi + 1] < _rx < _seg_edges[_csi]:
            # THROUGH chassis.mort_segments, not the whole run: the three stations at each end
            # are two short runs over the feet with the floor between them solid, and re-cutting
            # them full length here carved that floor straight back out again.
            for _my0, _my1 in CH.mort_segments(_rx):
                _seg = _seg.cut(_KL_FUSE.rib_mortise(_rx, _my0, _my1))
    chassis_segments[_csi] = _seg
# STRING ACCESS through the chassis floor, under each string's endplate channel (see
# dimensions.string_access_x). LAST in the segment pipeline, like the mortise re-cut, so no
# later fuse refills it. The chassis prints Z-up (Z_BOT is the bed), so a vertical hole needs
# no roof of its own; it takes the endplate's house outline so the passage lines up.
for _i in range(D.N_STRINGS):
    if BE.access_blocked(_i):          # a leg is under it -- no floor hole (see access_blocked)
        continue
    _ax = D.string_access_x(_i)
    for _csi in range(len(_seg_edges) - 1):
        if _seg_edges[_csi + 1] < _ax < _seg_edges[_csi]:
            chassis_segments[_csi] = chassis_segments[_csi].cut(
                BE.access_cutter(_i, CH.Z_BOT - 1.0, CH.Z_BOT + 2 * D.XBAR + 1.0))

# ...and RE-BORE each M4-held tee's hold-down. pcb_cradle bores the anchor and head notch in
# the CRADLE, but the fuse above unions it into the segment, and the segment's own rib and
# rail material fills the hole straight back in -- the same refill trap as the mortises. The
# gate found it the moment the screws had dummies: a uniform 27.0 mm3 of screw and 23.3 of
# insert buried in chassis on nearly every tee. The M4's 8.5 anchor puts the cradle base 5.3
# into that material. Cut at the END of the pipeline, where nothing unions over it again.
for _ctx, _cutters in _WR_FUSE.tee_hold_negatives():
    for _csi in range(len(_seg_edges) - 1):
        if _seg_edges[_csi + 1] < _ctx < _seg_edges[_csi]:
            for _cut in _cutters:
                chassis_segments[_csi] = chassis_segments[_csi].cut(_cut)
            break
chassis_light = list(chassis_light)
for _i, _lt in enumerate(chassis_light):        # the transparent under-rail band
    PARTS[f"chassis_{_i}_light"] = (
        partial(heal, _lt), f"pctg/chassis_{_i}_light.step",
        "PCTG (WHITE, translucent) — DOWNWARD LIGHT WINDOW: 8 mm across Y by the bottom "
        f"prism's full XBAR, one XBAR inboard of the +Y rail (print AS ONE OBJECT with chassis_{_i}, "
        "the deck panels' base/colour pattern). The bottom is sealed now, which is what keeps the "
        "motor noise in; this is the one deliberate leak, and the rail stands outboard of it so "
        "nothing shows from the front -- it only aims DOWN, at the pedals. White to match the deck "
        "panels, and it diffuses rather than glares. "
        "⚠ PCTG, NOT PETG (user, 2026-09-30). These three were the ONLY parts in the instrument "
        "asking for a fourth spool, and nothing else in the project is plain PETG -- the body is "
        "PETG-GF, the deck and fine-feature parts are PCTG, the feet TPU. The deck panels are "
        "already translucent/white PCTG, so the window is now the material it sits next to rather "
        "than one bought for it. PCTG is the same glycol-modified polyester family as PETG-GF, so "
        "the two still weld and purge cleanly in a one-object print. If a test print shows that "
        "weld is worse than PETG's, that is a reason to revisit -- a spool is cheaper than a "
        "delamination")
# THE TRRS ADAPTER'S STATION over the -X/+Y leg (wiring.trrs_*): the same three-step
# dance the tees do, and for the same reason -- fuse the cradle into the segment that
# owns its X, THEN cut the things that live inside it, because the fuse fills them in.
# The PORT is the extra one here: a bore through the +Y rail that the leg's plug
# reaches in along, so it has to be cut after the cradle's base merges into that rail.
_trrs_x = _WR_FUSE.TRRS_X
# THE CHASSIS-SIDE TRRS BOARD IS PARKED (user, 2026-09-16): dropped off the
# instrument's underside, with the leg's lead left hanging in free air. The user has a
# wiring plan for it to be implemented later, and until then a board mounted here is a
# guess that collides with real parts -- it was behind 6 of the model's 14 unintended
# overlaps (keyhead_endplate, electronics_tray, pi4 and three nut_height screws).
#
# NOTHING IS DELETED. wiring.trrs_cradle / trrs_port / trrs_hold_negatives /
# trrs_components are all still there and still correct for the station as laid out;
# only these call sites are commented out, so putting the board back is uncommenting
# them.
# for _csi in range(len(_seg_edges) - 1):
#     if _seg_edges[_csi + 1] < _trrs_x < _seg_edges[_csi]:
#         chassis_segments[_csi] = chassis_segments[_csi].union(_WR_FUSE.trrs_cradle())
#         chassis_segments[_csi] = chassis_segments[_csi].cut(_WR_FUSE.trrs_port())
#         for _cut in _WR_FUSE.trrs_hold_negatives():
#             chassis_segments[_csi] = chassis_segments[_csi].cut(_cut)
#         break
for _i, _seg in enumerate(chassis_segments):     # chassis split into dovetailed segments
    PARTS[f"chassis_{_i}"] = (partial(heal, _seg), f"petg-gf/chassis_{_i}.step",
                              "PETG-GF — chassis segment (cadkit slide-down T joint per rail; NO glue "
                              "and NO seam fastener — the deck, endplates and finally the 4 leg screws "
                              "close the seam's Z axis. + tee cradles)")
# Section-joint coupon (the LEG stack's octagon at the real 28 mm width — legs.SEC_W)
# COIL MANDREL -- a SHOP TOOL, registered for EXPORT but never in the assembly.
# Re-registered 2026-09-18: it was pulled while the 22.8 published bend radius was
# unresolved, and the user's duty-cycle answer resolved it -- the lead is SET ONCE,
# so the coil is a static form and leg_trrs.CABLE_BEND_STATIC records the deviation
# and its licence. coil_mandrel still asserts against that floor.
PARTS["coil_mandrel"] = (
    lambda: heal(__import__("src.coil_mandrel", fromlist=["e"]).mandrel()),
    "tools/coil_mandrel.step",
    "TOOL — inner mandrel for winding the leg's TRRS lead into a 7-turn coil. Barrel Ø15.2 with a helical pitch rib, flange-down on a Ø27.8 base, TAIL_RUN of plain barrel each side so both tails leave AXIAL, and a full-thickness slit so the starting tail carries on DOWN through the flange. PA6-GF, printed SOLID")
PARTS["coil_mandrel_sleeve"] = (
    lambda: heal(__import__("src.coil_mandrel", fromlist=["e"]).sleeve()),
    "tools/coil_mandrel_sleeve.step",
    "TOOL — the mandrel's outer sleeve, bore Ø23.0. It caps the coil's diameter so the mean lands on arithmetic rather than on spring-back, and holds both axial tails against the barrel while they set. PA6-GF, printed SOLID")
# LEVER PROGRAMMING JIG -- a SHOP TOOL like the mandrel: exported, never in the assembly.
PARTS["lever_prog_jig"] = (
    lambda: heal(__import__("src.lever_jig", fromlist=["e"]).jig()),
    "tools/lever_prog_jig.step",
    "TOOL — pogo nest for flashing the 11 lever/pedal sensor boards. The board drops in COMPONENT FACE DOWN onto four P75 pins standing at TP1–TP4 (positions read from the routed board), J1 is powered through the end window, and the pins seat themselves at height against the bench. PETG, printed as drawn")

PARTS["test_section_tenon"] = (
    lambda: heal(__import__("src.joint_coupon", fromlist=["e"]).section_tenon_coupon()),
    "test_section_tenon.step",
    "TEST COUPON — LEG section joint (28 mm octagon) TENON on a base plate; prints "
    "-Z→+Z. Slide into test_section_mortise to check the leg stack's slide fit")
PARTS["test_section_mortise"] = (
    lambda: heal(__import__("src.joint_coupon", fromlist=["e"]).section_mortise_coupon()),
    "test_section_mortise.step",
    "TEST COUPON — LEG section joint (28 mm octagon) MORTISE block (through-slot); "
    "prints -Z→+Z; validates the one-bead roof bridge at the real section size")
# Sleeve-cover rail coupon (the W5 rail octagons + 44-wide plate, real geometry)
PARTS["test_cover_seat"] = (
    lambda: heal(__import__("src.joint_coupon", fromlist=["e"]).cover_seat_coupon()),
    "test_cover_seat.step",
    "TEST COUPON — 40-long slice of the thinned sleeve face with both W5 cover-rail "
    "slots; print lying like the sleeve, slide test_cover_plate on to check the fit")
PARTS["test_cover_plate"] = (
    lambda: heal(__import__("src.joint_coupon", fromlist=["e"]).cover_plate_coupon()),
    "test_cover_plate.step",
    "TEST COUPON — 40-long slice of the leg sleeve cover (44-wide plate + both W5 "
    "octagon rails); prints lying on its outer face")

# Belt-tensioner mechanism coupon — TWO identical clamp_halves + two identical lifter bars, real
# geometry, print orientation. Step 1 of the fixed-motor rework: prove the belt drops in
# free with the screw out, LOCKS on a positive tooth mesh when the M4 lifts the bars, and
# the tension winds in smoothly and holds without creep.
PARTS["test_belt_tensioner"] = (
    lambda: heal(__import__("src.belt_tensioner", fromlist=["e"]).tensioner_coupon()),
    "test_belt_tensioner.step",
    "TEST COUPON — belt-tension clamp: 2 identical clamp_half (one turned 180°) + 2 identical "
    "lifter bars. Drop a GT2 scrap through with the M4×35 out (bars low = free), seat the screw "
    "(bars ride the crest up → teeth mesh), and wind it against the external insert-nut to check "
    "the grip holds and tension sets fine without creep")


# Anchor ALL outputs to the project folder (never the cwd — see Archive/3D/CLAUDE.md)
OUT = pathlib.Path(__file__).resolve().parents[1]


# The instrument's materials, and there are THREE (user, 2026-09-30): PETG-GF for the
# body, PCTG for the deck and fine-feature parts, TPU for the feet. Plain PETG was here
# for exactly three parts -- the chassis light windows -- and buying a fourth spool for
# three translucent strips is the opposite of what this instrument is for.
MATERIALS = ("petg-gf", "pctg", "tpu")


def _material_of(path):
    """The material folder a part exports into, or None.

    ⚠ NOT path.split("/")[0]. Test coupons are written at the root and coil_mandrel into
    tools/, so that returned "test_cover_plate.step" and "tools" as materials and
    tools/cost.py then had no filament price for either (lead, 2026-09-30). A part
    outside the material folders has no filament cost to attribute, and saying None is
    how cost.py knows to leave it out rather than guess."""
    head = path.split("/")[0]
    return head if head in MATERIALS else None


def _export(name):
    builder, path, note = PARTS[name]
    dest = OUT / path
    dest.parent.mkdir(parents=True, exist_ok=True)   # material folder (petg-gf/pctg/tpu)
    t = time.perf_counter(); wp = builder(); build_s = time.perf_counter() - t
    t = time.perf_counter(); export_step(wp, str(dest)); export_s = time.perf_counter() - t
    record_part(name, build_s, export_s, wp.val() if hasattr(wp, "val") else wp,
                material=_material_of(path))          # ~free profiling + volume hook
    print(f"Wrote {path}" + (f"  ({note})" if note else ""))


def _bead(p, r):
    """A ball at a joint in the string path.

    WHY A BALL AND NOT AN OVERLAP. Where the tail leaves the coil the two are TANGENT --
    the chord sets off in the direction the helix is already going -- and a tangential
    overlap between a swept helix and a cylinder is the case OCC handles worst. Running
    the chord back into the coil (a string diameter of lap) fused seven of the ten and
    quietly dropped the coil on strings 4, 7 and 8: the union came back smaller than the
    tail alone. A ball centred ON the joint overlaps both solids in three dimensions
    instead of along a line, and all ten fuse."""
    return cq.Workplane("XY").add(cq.Solid.makeSphere(r, pnt=p, angleDegrees1=-90))


def _rod(p0, p1, r):
    v = p1.sub(p0)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, pnt=p0, dir=v))


def _tangent_angle(cx, cz, px, pz, R, side):
    """Angle (XZ plane) of the point where a line from (px, pz) touches the circle of radius
    R about (cx, cz). side +1 = the touch point counter-clockwise of the centre line, -1 =
    clockwise."""
    dx, dz = px - cx, pz - cz
    return math.atan2(dz, dx) + side * math.acos(R / math.hypot(dx, dz))


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
        run = abs(mx - D.screw_x(i))
        rise = D.screw_pulley_z(i) - mz          # odd pulleys sit one belt-plane up
        span = math.hypot(run, rise)
        loop = 2 * span + math.pi * D.PULLEY_OD
        cut = loop + SPLICE_LAP
        total += cut
        lines.append(f"    {i:>4} {span:>6.0f} {90.0 / span:>6.2f}°/mm {cut:>8.0f}")
    lines.append(f"  total open GT2 to buy: ~{total/1000:.2f} m "
                 f"(+ {2 * D.N_STRINGS} printed clamp_half + {2 * D.N_STRINGS} lifter bars, "
                 f"{D.N_STRINGS}× M4×35 + insert-nut)")
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
# default). Strings 1, 2, 9 and 10 — both edge pairs; string N = index + 1
# (string 1 = index 0 = thinnest/highest, the far edge; string 10 = index 9 =
# thickest/lowest, nearest the player) — are kept PERMANENTLY at full
# down-travel, feet on the bottom stop: the maximum stretch/tension the
# mechanism can pull, so the travel extremes are always visible from either
# side. Everything riding the carriage (string nut, brass nut, string anchor)
# follows; the guide rod, screw and stops are fixed.
DEMO_POSE_DZ = {i: -D.CARRIAGE_TRAVEL for i in (0, 1, 8, 9)}

# BELT CLAMP TRAVEL. Each belt's tension clamp rides the belt, so it has to stay on the
# straight run between the two pulleys' flanges over the carriage's whole travel. The travel
# is DERIVED from that (dimensions.CARRIAGE_TRAVEL) using the clamp's length as a number;
# this is where that number is held to the solids.
_CLAMP_XS = [v for _n, _s in BTn.clamp_components(with_lifters=True)
             for v in (_s.val().BoundingBox().xmin, _s.val().BoundingBox().xmax)]
_CLAMP_L = max(_CLAMP_XS) - min(_CLAMP_XS)
assert abs(_CLAMP_L - D.BELT_CLAMP_L) < 0.05, (
    f"the belt clamp measures {_CLAMP_L:.2f} along the belt but dimensions.BELT_CLAMP_L is "
    f"{D.BELT_CLAMP_L}: the carriage travel and the nut's floor are sized from that number")


def _string_components(i):
    sy = D.string_y(i)
    mx, my, mz = D.motor_pos(i)
    cz = D.NUT_TOP_Z + DEMO_POSE_DZ.get(i, 0.0)      # the NUT's flange top
    out = []
    # vertical leadscrew
    out.append((f"leadscrew_{i}", C.screw().translate((D.screw_x(i), sy, D.SCREW_BOT_Z))))
    # THE NUT IS THE CARRIAGE. Nothing else moves: its +X ear anchors the string and
    # its -X ear rides the guide rod. Origin = the flange's top face.
    out.append((f"nut_{i}", C.nut().translate((D.screw_x(i), sy, cz))))
    # string BALL END, hanging UNDER the +X ear — tension pulls it up against the
    # ear's underside, and that IS the retention (a guitar bridge plate, exactly)
    out.append((f"string_nut_{i}", C.string_nut().translate(
        (D.string_anchor_x(i), sy, cz - D.NUT_FLANGE_T - D.STRING_NUT_D / 2))))
    # guide rod: dropped in from +Z through the slab, through the -X ear, into a blind
    # socket in the screw rail — SUPPORTED AT BOTH ENDS, so it is a beam and not a
    # cantilever. Gravity seats it; the string overhead keeps it there.
    rod_top = BE.GUIDE_ROD_TOP          # just under the optical board
    rod_bot = BE.GUIDE_SOCKET_Z
    out.append((f"guide_rod_{i}", C.guide_rod(rod_top - rod_bot).translate(
        (D.guide_rod_x(i), sy, rod_bot))))
    # screw drive pulley (odd ones raised one belt-plane), then the thrust stack:
    spz = D.screw_pulley_z(i)
    # TWO SKUs: the low-plane stations carry the column that lifts their boss to the
    # same thrust plane the high-plane ones already reach.
    out.append((f"screw_pulley_{i}",
                C.screw_pulley(high=spz > D.SCREW_PULLEY_Z).translate((D.screw_x(i), sy, spz))))
    # THRUST STACK, seated straight on the pulley's pilot boss. The string's pull jams
    # the pulley up into it, and that one jam does BOTH jobs: it retains the screw and
    # it holds the pulley on the rod. No collar, no set screw.
    for k in range(D.SUPPORT_BRG_N):
        bz = D.SUPPORT_BRG_BOT + (k + 0.5) * D.BRG688_W
        out.append((f"screw_bearing_{i}_{k}", C.support_bearing().translate((D.screw_x(i), sy, bz))))
    # NO TOP RADIAL BEARING — deleted 2026-09-09 (user), and Tr8 is what allows it.
    # It existed to react the string's off-axis couple: the pull lands NUT_HOLE_DX from
    # the screw axis, and a Ø5 screw cantilevering from the thrust bearing was too limp
    # to take that alone. At Ø8 the screw is 6.55x stiffer in bending (d^4) and deflects
    # 0.006 mm over the 21 mm from the thrust bearing to the nut — so the second bearing
    # is now reacting nothing the screw was not already handling.
    # It also could not have stayed: at Ø8 bore the smallest bearing available is Ø16
    # OD, whose radius reaches EXACTLY the guide rod at NUT_HOLE_DX 8.0 (the bought
    # nut's own hole pitch), so the seat and the rod occupied the same space. The
    # overlap gate caught it. Deleting the bearing is what resolves that, not a fit.
    # motor (shaft +Y, body −Y toward player) + its pulley + twisted belt
    out.append((f"motor_{i}", C.motor().translate((mx, my, mz))))
    out.append((f"motor_pulley_{i}", C.motor_pulley().translate((mx, my, mz))))
    # The body length the pockets are built from is checked here, where the motor is built
    # anyway. (No retaining screw: each motor is held by its own CAN tee -- wiring.on_motor.)
    if i == 0:
        _mb = C.motor().val().BoundingBox()
        assert abs(-_mb.ymin - MOTOR_PULLEY_STANDOFF - D.MOTOR_BODY_L) < 1e-6, (
            f"the motor body is {-_mb.ymin - MOTOR_PULLEY_STANDOFF:.2f} deep, not "
            f"dimensions.MOTOR_BODY_L {D.MOTOR_BODY_L} -- the pockets are built from that")
    out.append((f"belt_{i}", C.belt((mx, my, mz), (D.screw_x(i), sy, spz))))   # all belts modelled smooth
    # belt-tension clamp (unified clamp_half ×2 + screw + external nut), oriented to the belt's flat
    # zone. Lifter bars only on the last string (build-time saver — same geometry, hidden elsewhere).
    # THE CLAMP IS DRAWN AT ITS REFERENCE SPOT, NOT WHERE THE NUT HAS CARRIED IT -- and that is
    # a known gap, not a choice. Posing it by travel (splice_frame's from_screw: spliced on
    # CLAMP_END_CLR off the screw pulley with the nut at the top, then BELT_PER_MM toward the
    # motor per mm of nut) was tried on 2026-10-01 and showed real trouble the reference pose
    # hides: near the screw end the belt is turned 90 deg, so the clamp lies across its
    # neighbours' lanes (clamp<->next belt up to 26 mm3, clamps 9<->10 31 mm3), and string 9's
    # clamp grazes string 10's motor pulley in its last millimetre of travel. Where on each
    # belt the clamp may live, over the whole travel, is an open study; until it is settled
    # the pose stays here so the gate is not red on a question it cannot answer.
    so, sxd, sn = C.splice_frame((mx, my, mz), (D.screw_x(i), sy, spz))
    cloc = cq.Location(cq.Plane(origin=so, xDir=sxd, normal=sn))
    for _nm, _shp in BTn.clamp_components(with_lifters=(i == D.N_STRINGS - 1)):
        out.append((f"{_nm}_{i}", cq.Workplane("XY").add(_shp.val().moved(cloc))))
    # string: rises from the anchor tangent to the bearing's +X extent, wraps 90°
    # over the top, then runs the speaking length to the nut block.
    out.append((f"string_{i}", _string_path(i, sy)))
    # nut-block hardware (DEMO): gauged break pin, then the WRAP's clamp -- which sits
    # at the far end of the coil, not on the string's own lane (see nut_block.wrap_y)
    g = D.STRING_GAUGE[i]
    ny, wy = NB.wrap_y(i)
    tail_z = D.STRING_Z + NB.ROD_Z                                     # the tail runs at rod height
    out.append((f"break_dowel_{i}", C.dowel().translate(               # gauged: pin top at Z-g, so
        (D.NUT_BLOCK_X + NB.DOWEL_X, ny,                               # every string top lands on
         D.STRING_Z - g - D.NUT_PIN_D / 2))))                          # one plane. DOWEL_X, not 0:
                                                                       # the dowels sit 1.6 back from
                                                                       # the block's front face now
    # THE SLIDING INSERT IS THE CLAMP (no set screw, no heat-set insert): the tail is pinched
    # against the wrap on the rod rather than against the floor. It was only ever drawn by
    # keyhead_endplate.assembly() -- the scratch view -- so the full assembly, and everyone
    # viewing it, never saw one. Same placement as there, from the same module.
    out.append((f"nut_slide_insert_{i}",
                NB.slide_insert(i).translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z))))
    # ...and the M4 x 20 that pushes it up, threading its heat-set in the endplate slab
    out.append((f"nut_height_screw_{i}",
                NB.height_screw(i).translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z))))
    out.append((f"nut_height_insert_{i}",
                NB.height_insert(i).translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z))))
    return out


def _wrap_rod_component():
    """The nut's WRAP ROD -- one part for all ten strings, and the SAME Ø8 x 100 shaft the
    bridge axle is (nut_block.ROD_D / ROD_L read D.BRIDGE_AXLE_D / _L): one SKU at both
    ends. It is what the capstan turns around, so it is what lets a light clamp hold."""
    return [("nut_wrap_rod",
             NB.rod().translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z)))]


def _string_path(i, sy):
    """Vertical rise → 90° wrap around the bridge bearing → speaking length."""
    r = D.BRIDGE_BEARING_OD / 2
    cx, cz = D.BRIDGE_AXLE_X, D.BRIDGE_BEARING_Z      # bearing centre
    # anchor = the ball end hanging under the nut's +X ear
    az = (D.NUT_TOP_Z + DEMO_POSE_DZ.get(i, 0.0)
          - D.NUT_FLANGE_T - D.STRING_NUT_D / 2)
    g = D.STRING_GAUGE[i]
    rad = g / 2.0                                     # actual string gauge
    # THE STRING RIDES ON THE OD. A 688ZZ has a plain outer ring, no groove, so the string's
    # CENTRELINE wraps at the OD radius plus half its gauge, and both straight runs leave that
    # circle TANGENTIALLY. The path used to centre the string ON the OD and aim the rise at the
    # fixed +X extent, which buried half the gauge in every bearing and more wherever the rise
    # leans (user saw strings clipping). The rise is still NOT vertical: the ear sits ANCHOR_DX
    # either side of the tangent, near row one way and far row the other (~10°) -- that split
    # is the point, see dimensions.
    p0 = cq.Vector(D.string_anchor_x(i), sy, az)
    # speaking length to the break edge: string sits on the gauged pin, TOP at STRING_Z
    brk = cq.Vector(D.NUT_BLOCK_X, D.nut_y(i), D.STRING_Z - g / 2.0)
    R0 = r + rad
    th0 = _tangent_angle(cx, cz, p0.x, p0.z, R0, +1)       # rise touches on the +X side
    th1 = _tangent_angle(cx, cz, brk.x, brk.z, R0, -1)     # speaking length leaves over the top
    N = max(8, math.ceil((th1 - th0) / math.radians(10.0)))
    # Chords cut inside an arc. Vertices on R0/cos(half-step) put every chord's MIDPOINT on R0,
    # so the polygon touches the race and never dips into it; the tangents are re-taken on that
    # radius so the straight runs still meet the first and last vertex exactly.
    R = R0 / math.cos((th1 - th0) / N / 2)
    th0 = _tangent_angle(cx, cz, p0.x, p0.z, R, +1)
    th1 = _tangent_angle(cx, cz, brk.x, brk.z, R, -1)
    pts = [cq.Vector(cx + R * math.cos(th0 + (th1 - th0) * k / N), sy,
                     cz + R * math.sin(th0 + (th1 - th0) * k / N)) for k in range(N + 1)]
    # a bead at every vertex: a tangent join between two cylinders shares no volume, and OCC
    # hands back a compound with the pieces floating free (see the wrap below)
    # THE RISE LEAVES THROUGH THE EAR'S HOLE, AND A HEAVY STRING DOES NOT FIT THROUGH IT
    # STRAIGHT. The ball end seats centred under a Ø3.5 hole and the string leans ~9-13 deg
    # toward the bearing, so by the flange's top face its centreline has walked up to 1.4
    # off the hole's axis -- more the higher the nut sits, since the same ANCHOR_DX is spent
    # over a shorter rise. Past (hole radius - string radius) it is ON THE BRASS. Drawn
    # straight, the string simply passed through the nut: 0.96 mm3 on string 9 at the top of
    # travel, and 0.22 where the old top of travel was -- which the demo pose hid by parking
    # that string at the bottom. So the string is drawn the way it runs: up the hole to the
    # rim, over the rim, then away to the bearing. That rim is a real break point on the
    # heavy strings; see INSTALL_NOTES (deburr the ear holes).
    z_ear = az + D.STRING_NUT_D / 2 + D.NUT_FLANGE_T + 0.1         # just over the flange's top face
    reach = D.NUT_HOLE_D / 2.0 - rad - 0.05                        # centreline's room in the hole
    lean = (pts[0].x - p0.x) * (z_ear - p0.z) / (pts[0].z - p0.z)  # ...and what it would take
    if abs(lean) > reach:
        rim = cq.Vector(p0.x + math.copysign(reach, lean), sy, z_ear)
        th0 = _tangent_angle(cx, cz, rim.x, rim.z, R, +1)
        pts = [cq.Vector(cx + R * math.cos(th0 + (th1 - th0) * k / N), sy,
                         cz + R * math.sin(th0 + (th1 - th0) * k / N)) for k in range(N + 1)]
        out = _rod(p0, rim, rad).union(_bead(rim, rad)).union(_rod(rim, pts[0], rad))
    else:
        out = _rod(p0, pts[0], rad)
    out = out.union(_bead(pts[0], rad))
    for pa, pb in zip(pts, pts[1:]):
        out = out.union(_rod(pa, pb, rad)).union(_bead(pb, rad))
    out = out.union(_rod(pts[-1], brk, rad))
    # dead end: break edge -> down to the wrap rod -> N turns around it -> out to the clamp
    ny, wy = NB.wrap_y_drawn(i)                          # the coil AS WOUND (nut_block.WRAPS)
    rx, rz = D.NUT_BLOCK_X + NB.ROD_X, D.STRING_Z + NB.ROD_Z
    hr = NB.wrap_radius(i)                                 # helix radius: nut_block owns it
    # THE WRAP IS ON THE ROD'S UNDERSIDE (-Z), so the path has no reversal left in it:
    # the string leaves the dowel already descending, becomes TANGENT to the wrap circle
    # on the way down, goes round underneath, and leaves at the bottom running straight
    # -X to the clamp. TANGENCY is the part that has to be right -- aiming at the
    # circle's lowest point instead would draw the string cutting through the rod on the
    # way in. The touch point sits BREAK_ANGLE round from the bottom, +X side.
    phi = NB.touch_angle(i)          # nut_block owns this -- see its docstring on why
    tang = cq.Vector(rx + hr * math.cos(phi), ny, rz + hr * math.sin(phi))
    tail_z = rz + hr                                       # the TOP: where it leaves
    # RUN THE STRAIGHT RUNS PAST THE TANGENT POINT, or they do not touch the coil.
    # A tangent meets its circle at ONE POINT: the lead rod ends exactly where the helix
    # begins, so the union of the two has literally nothing to fuse and OCC hands back a
    # two-solid compound with the coil floating free. It came out as strings 8 and 10
    # rendering with no winding at all -- and the giveaway was that the union's volume was
    # the EXACT SUM of its parts, i.e. zero overlap, not a boolean that had gone wrong.
    # The other eight only survived on the odd micron of floating-point slop.
    #
    # Carrying each straight run ONE STRING DIAMETER past the touch point gives a real
    # overlap without moving anything that matters: the tangent line separates from the
    # circle as d^2/2r, so at d = 2*rad the centrelines are 2*rad^2/hr apart -- 0.02 mm on
    # the .015 and 0.46 on the .070, well inside the string's own radius either way. The
    # wrap itself is untouched; this is the DEMO path's joinery, not the capstan geometry.
    _LAP = 2.0 * rad                                       # one string diameter of overlap
    t_in = cq.Vector(-math.sin(phi), 0.0, math.cos(phi))   # the coil's heading at the touch
    out = out.union(_rod(brk, tang + t_in.multiply(_LAP), rad))
    out = out.union(_wrap_coil(i, rad, hr))
    # THE TAIL FOLLOWS THE CHANNEL'S OWN CENTRELINE, from nut_block, so the string and the
    # passage it lives in cannot drift apart -- the same one-description rule the pocket
    # and the insert follow. It leaves at EXIT_DEG already descending, so there is no
    # corner here at all: the -X run and the separate stow bore are both gone.
    pts = NB.stow_route(i, (CH.Z_BOT + 8.4) - D.STRING_Z)   # stop above the tongue top
    # The tail leaves the rod at the COIL's Y, but its bore sits behind the INSERT (nut_block.
    # stow_y), so it crosses to the bore's Y as it rises in the socket: the exit and its stub
    # stay on the coil, every point from the rise on follows the bore's axis -- which leans -Y
    # as it descends (nut_block.STOW_TILT), so the descent is read off stow_y_at, not stow_y.
    ys = [wy, wy] + [NB.stow_y_at(i, z) for _x, z in pts[2:]]
    x0, z0 = pts[0]
    prev = cq.Vector(D.NUT_BLOCK_X + x0, wy, D.STRING_Z + z0)
    out = out.union(_bead(prev, rad * 1.05))                # see _bead: the tail leaves
    for (x, z), y in zip(pts[1:], ys[1:]):                  # TANGENT to the coil
        cur = cq.Vector(D.NUT_BLOCK_X + x, y, D.STRING_Z + z)
        out = out.union(_rod(prev, cur, rad))
        prev = cur
    return out


def _wrap_coil(i, rad, hr):
    """The capstan itself: NB turns of string around the shared rod, marching -Y. Same
    sweep recipe cadkit/threads.py uses for a real thread. The march is what makes the
    turn count a geometry question -- each turn eats NUT_PITCH, see nut_block._turns."""
    ny, wy = NB.wrap_y_drawn(i)                          # the coil AS WOUND (nut_block.WRAPS)
    p = NB.WRAP_F * D.STRING_GAUGE[i]
    h = abs(wy - ny)
    # RIGHT-HAND. Rotated +90 about X the helix axis lies along -Y (the march), and a
    # right-handed helix then turns +X toward +Z -- phi INCREASING, which is the way the
    # string is already going when it meets the rod's top. Left-hand reverses that and
    # draws the coil winding back into its own entry.
    helix = cq.Wire.makeHelix(pitch=p, height=h, radius=hr, lefthand=False)
    coil = (cq.Workplane("XZ").center(hr, 0).circle(rad)
            .sweep(cq.Workplane("XY").add(helix), isFrenet=True))
    # +90 about X (not -90): that lays the helix axis along -Y, so the coil marches
    # toward the THICKER neighbour and the fattest one runs out into free air.
    # ...then -90 about its OWN axis, which is what puts the start of the wrap on the
    # ROD'S UNDERSIDE. makeHelix begins at angle 0 -- the +X side -- and leaving it there
    # would draw the string entering at the rod's mid-height, which is the reversal this
    # whole change exists to remove.
    coil = coil.rotate((0, 0, 0), (1, 0, 0), 90.0)
    # START THE WRAP WHERE THE STRING LANDS. makeHelix begins at angle 0 (+X); spinning it
    # to the touch angle is what closes the gap between the straight run and the coil.
    coil = coil.rotate((0, 0, 0), (0, 1, 0), -math.degrees(NB.touch_angle(i)))
    return coil.translate((D.NUT_BLOCK_X + NB.ROD_X, ny, D.STRING_Z + NB.ROD_Z))


def _pickup_mount_components():
    from . import top_plate as TP
    from cadkit.fasteners import (M2, M4, screw as f_screw, insert as f_insert,
                                  headed_screw, seated_insert)
    PICKUP_X = TP.PICKUP_X_NOM     # pickup centre in the shown pose (pocket centre)
    # pickup rests on the Z-plate, centred on the field (Y = PK_CTR_Y) for magnetic cover
    out = [("pickup", PM.pickup_demo().translate((PICKUP_X, TP.PK_CTR_Y, PM.PK_TOP))),
           ("pickup_zplate", TP.pickup_zplate)]
    # OPTICAL per-string strip: lies UNDER the strings on a carrier that is part of the
    # bridge endplate and rides on top of the deck, firing UP (see optical_pickup.py).
    # Board is fab/purchased -> assembly only, no standalone STEP. The light COVER is
    # now part of the ENDPLATE (unioned there), not a part of its own.
    from . import optical_pickup as OP
    out.append(("optical_pcb", OP.opt_pcb()))
    # MALE connectors + cable at true diameter. Not a printed part -- it exists so the
    # route can be PLANNED rather than assumed, and so the overlap gate has something to
    # complain about if the conduit or the plinth ever moves into the cable's path.
    # ⚠ TWO CABLES, TWO NAMES, TWO COLOURS. These were one "optical_cables" solid in a
    # single near-black grey, so the USB lead and the 24 V lead were indistinguishable in
    # the viewer and neither could be hidden without hiding the other. Split so each says
    # what it is, and coloured off the loose-wire scheme already in this table: violet for
    # USB, red for 24 V.
    out.append(("optical_cable_usb", OP.opt_cables("usb")))
    out.append(("optical_cable_pwr", OP.opt_cables("pwr")))
    # The two M4 grips that locate the board: heat-set insert seated in the endplate's
    # wrap plinth, button screw down through the board's clearance hole into it. Same
    # fastener family as the pickup height jacks, so no new BOM line.
    from . import bridge_endplate as _BE
    _ohh = TP.JACK_HEAD_H                             # the jacks' ISO 7380 button head
    # headed_screw draws head-top-at-0 with the shank running -Z, which is ALREADY the
    # orientation for a screw entering downward -- no flip. (The old optical M2 went up
    # from below and did need one; copying that was what put this one through the board.)
    _oscr = headed_screw(M4, 12.0, head_d=TP.JACK_HEAD_D, head_h=_ohh, socket_af=2.5)
    for _i, (_mx, _my) in enumerate(OP.mount_points()):
        out.append((f"optical_insert_{_i}",
                    seated_insert(M4, (_mx, _my, _BE.PCB_PAD_TOP), (0, 0, -1))))
        out.append((f"optical_screw_{_i}",
                    _oscr.translate((_mx, _my, OP.PCB_TOP + _ohh))))
    # TOP-ACCESS height (user): THREE M4×20 BUTTON-HEAD LEADSCREW jacks (real headed cap screw,
    # cadkit headed_screw -> hex-socket drive visible in the head top). Each head is captured in a
    # counterbore in the solid deck (JACK_HEAD_Z shoulder); the shank threads down through a HEAT-
    # SET-INSERT NUT standing on the plate. Turning the head from +Z walks the plate up/down.
    # Equalise the two +Y = X level, -Y = across-string tilt.
    for _i, (_jx, _jy) in enumerate(TP.JACK_POS):
        out.append((f"pickup_jack_insert_{_i}",
                    f_insert(M4).translate((_jx, _jy, TP.JACK_MOUTH_Z))))   # nut, mouth at the boss top
        _screw = headed_screw(M4, TP.JACK_SCREW_L, head_d=TP.JACK_HEAD_D,   # M4×20 button head, hex socket
                              head_h=TP.JACK_HEAD_H, socket_af=2.5)
        out.append((f"pickup_jack_screw_{_i}",
                    _screw.translate((_jx, _jy, TP.JACK_HEAD_Z + TP.JACK_HEAD_H))))  # head top over the shoulder
    # PICKUP RETENTION (user): a -Y horizontal M4 x 12 BUTTON HEAD (2.5 mm key; it was a cup-tip
    # set screw until the one-key rule, 2026-09-30) threads a heat-set insert and pushes the pickup +Y against the
    # +Y wall, locking it to the PLATE only. Threading it in/out meets any pickup in the ~5.5 mm
    # length window; shown here at the DEMO Alumitone (longest, so nearly backed out): tip at PK_YM.
    _ret_face_y = TP.PK_MAX_YM - TP.RET_BOSS_L                        # boss/insert mouth (-Y, at the room edge)
    from cadkit.fasteners import m4_button_screw, M4_BUTTON_HEAD_H
    _ret_grub = m4_button_screw(TP.RET_SCREW_L).rotate((0, 0, 0), (1, 0, 0), 90)   # head -Y, tip +Y
    _ret_bb = _ret_grub.val().BoundingBox()
    out.append(("pickup_retention_screw",
                _ret_grub.translate((TP.RET_SCREW_X, TP.PK_YM - _ret_bb.ymax, TP.RET_SCREW_Z))))  # tip at the pickup
    out.append(("pickup_retention_insert",
                seated_insert(M4, (TP.RET_SCREW_X, _ret_face_y, TP.RET_SCREW_Z), (0, 1, 0))))
    return out


# The pedal bar and the pedals on it are both drawn in the bar's own frame (z0 = plate
# bottom) and lifted into the guitar by the same amount. Named once so the bar, the
# pedals and the viewer's animation rig (tools/export_rig.py, which needs the axle
# centre in guitar coordinates) can't drift apart. The bar hangs off the redesigned
# leg's adjust tenon (user: one leg), so the lift is where that leg puts the bar's
# tower mouth -- the same pose leg_stack.pedal_bar_context uses.
from . import leg_stack as LS                      # noqa: E402
from . import pedal_bar as _PBM                    # noqa: E402
PEDAL_LIFT_DZ = LS.Z_BAR_MOUTH - _PBM.TOWER_TOP


def _leg_components():
    """ONE LEG (user): the redesigned leg (src.leg_stack) at its -X/+Y corner, with its
    body latch and the pedal bar's latch, every part authored where it goes. The other
    three corners carry only a BODY ADAPTER, slid into the body's mortises, so the
    body joinery is still in the assembly at every corner."""
    from . import chassis as CH
    out = list(LS.leg_parts())
    k = 1
    for sx in CH.LEG_STATIONS_X:
        for ly in CH.LEG_Y:
            if (sx, ly) == (LS.LEG_X, LS.LEG_Y):
                continue
            egx = -1.0 if sum(CH.LEG_STATIONS_X) / 2 > sx else 1.0
            syg = 1.0 if ly > sum(CH.LEG_Y) / 2 else -1.0
            out.append(("body_adapter_%d" % k, LS.body_adapter(sx, ly)))
            out += LG.lock_pin_dummies(sx, ly, egx, syg, CH.Z_BOT, k)   # its one screw
            k += 1
    return out


def _pedal_bar_components():
    """Pedal bar + latch, modelled in absolute X/Y with z0 = plate bottom =
    the shaft waist's lower shoulder (foot top): lift by ground + FOOT_H."""
    from . import pedal_bar as PB
    from . import foot_pedal as FP
    dz = PEDAL_LIFT_DZ
    # The pedal HOUSINGS are fused into the bar pieces (foot_pedal.fuse_into_bar),
    # and that fusion has to happen HERE as well as in the export registry
    # (_PB_bar). It did not, so every assembly and every overlap-gate run since the
    # pedals landed saw the PLAIN bar: all three housings — 205,061 mm3, 61% of
    # pedal_bar_b — were absent from the assembly while present in the STEP the
    # printer gets. That is why the pedal read as non-working on screen (a lever and
    # springs in front of nothing) and why the gate never checked a single pedal
    # part against the structure it mounts to.
    out = []
    for n, wp in PB.assembly_parts():
        if n in PB.PIECE_SPAN:
            wp = _PB_bar(n)      # the SAME finished piece the printer gets
        out.append((n, wp.translate((0, 0, dz))))
    return out


def _foot_pedal_components():
    """Foot pedals, drawn in the pedal bar's frame (z0 = plate bottom) and lifted
    the same way it is. Three stations, all at REST."""
    from . import foot_pedal as FP
    return [(n, wp.translate((0, 0, PEDAL_LIFT_DZ))) for n, wp in FP.demo_parts()]


def _electronics_components():
    """The compute bay + panel jacks + the wire harness.

    (The old "PRO population shown; a basic build leaves the Pi / CS stack / buck
    sockets empty" is retired with the basic/pro split itself -- there is ONE model,
    fully populated, and BOM.md's cost summary says so. The CS stack and the buck
    sockets it named are both gone besides.)"""
    from . import electronics as EL
    from . import wiring as WR
    from . import top_plate as TP
    # electronics_tray is gone: the Pi's and the motor controller's mounts are cradles
    # fused into the CHASSIS SEGMENT now (see electronics.keyhead_cradles and the union at
    # the top of this file) -- NOT the endplate, which is what this said until 2026-09-29.
    # The endplate has to come off with the boards left in place (user), which is the whole
    # reason they moved. One less printed part, and the boards gained retention they never
    # had on the tray's bare posts.
    # pi_spacer is the flat Pi's RETENTION -- a printed piece, not a dummy. It replaces the
    # button head that used to clamp the laminate directly: no position beside the board had
    # room for that screw's anchor below the floor (electronics.PI_SPACER_XY).
    out = [("pi4", EL.pi4()), ("pi_cap", EL.pi_cap()), ("pi_spacer", EL.pi_spacer()),
           *EL.led_sections(),
           ("motor_ctrl", EL.motor_ctrl()),
           ("output_panel", EL.output_panel()),
           ]
    out += UI.parts()
    # the fret-light boards and their LEDs. The CELLS are not here -- they are deck
    # geometry, built into top_plate's mid/keyhead panels (src/fret_light.py).
    from . import fret_light as FL
    for panel in ("mid", "key"):
        out.append(("fret_pcb_%s" % panel, FL.pcb(panel)))
        out.append(("fret_led_%s" % panel, FL.leds(panel)))
    # the FOOT strip: one board placed twice, firing down through the chassis window.
    # The channel it slides into is chassis geometry (src/foot_light.py).
    from . import foot_light as FOOT
    out += FL.strips()
    out += FL.pogo_pins()
    out += FL.m4_screws()      # the one M4 per board, head on the board's underside
    out += FOOT.parts()
    out += EL.board_screws()
    out += [(f"top_plate_{i}", seg) for i, seg in enumerate(TP.segments)]
    out += [(f"top_plate_color_{i}", seg) for i, seg in enumerate(TP.segments_color)]
    # (NO SPARE FILLERS to explode off to the side any more: the fillers are fret-free,
    #  so one design fits any slot and the two installed ARE the whole set. See top_plate.)
    out += WR.tee_components()
    # out += WR.trrs_components()      # PARKED with the station above
    out += WR.build_wires()
    return out


# ── THE FIVE KNEE LEVERS ─────────────────────────────────────────────────────
# FIVE since 2026-09-11 (user): ILKL, the inner lever, is removed. Its forward plane
# (_ILKL_Y) stays as the datum the shared contact plane is measured from, and its
# station X stays as LKL's (_LKL_X), so the other five did not move.
# The copedent needs six (user): ILKL, LKL, VKL, LKR, RKL, RKR. Only LKL and VKL
# were ever modelled, each hardcoded at its own MOUNT_POSE; this table makes the
# station the variable and reuses those two designs for all six.
#
# TWO Y PLANES, which is all the user asked for: ILKL is the INNER lever, closest
# to the player, its paddle's -Y face FLUSH with the body edge; everything else
# sits one paddle-depth behind it, sharing one contact plane.
#
# X: THE MIRROR IS WHAT MAKES CLUSTERS POSSIBLE. The KL housing is 82.36 wide in X
# and almost all of it lies -X of its axle (-77.36..+5), because the two feel
# cartridges sit beside the lever. Two levers of the SAME hand therefore cannot come
# closer than 92 (4 rib pitches) — but an "…R" lever is the design REFLECTED, so it
# occupies +X of its axle instead, and an L/R pair NESTS at 23 (one rib). That is
# also what they physically are: LKL and LKR are one knee pushing left or right, so
# their axles belong next to each other. The pairs below sit a rib apart and the two
# knees land ~250 apart, which is a seated player's stance.
#
# VKL cannot join the nesting — it is a different housing and has to clear the pair
# outright, so it sits +X of them rather than between.
#
# Every station is a RIB X (23 pitch), because both designs' tenons are generated on
# a plain rib walk from the axle — and the rib mortises chassis.py cuts run from the
# player face all the way to MID_Y, so the Y placement below is a slide along slots
# that already exist. Nothing in the chassis changes for any of this.
_LEVER_PADDLE_D = 20.0                       # KL paddle depth in Y
_ILKL_Y = CH.Y_LO + _LEVER_PADDLE_D / 2      # -123.95: paddle -Y face on the body edge


def _lever_plane_y() -> float:
    """The shared contact plane, set by CLEARING ILKL'S HOUSING — not by the paddle.

    First cut put this one paddle-depth behind ILKL, which reads right but is not
    what governs: the housing is 38.1 deep in Y against a 20 paddle, so at that
    spacing the two housings still overlapped and the only way to keep them apart
    was to push LKL far away in X. The user's call, and it is the right one — move
    the plane +Y until the housings clear, and X is free again.

    Derived from the housing solid so it tracks the design.
    """
    from . import knee_lever as KL
    b = KL.knee_housing.translate(KL.MOUNT_POSE).val().BoundingBox()
    return _ILKL_Y + (b.ymax - b.ymin) + 0.4     # housing depth + a print clearance


_LEVER_Y = _lever_plane_y()                  # -85.45

# ONE SLOT for the levers, quantised to the rib comb. A lever's tenons only land in
# rib mortises if its station IS a rib X, so any lever spacing is a whole rib count.
# DERIVED from the motor pitch (the comb is its half-pitch — chassis._rib_positions)
# so a MOTOR_X_STEP change moves the stations WITH the comb instead of out from
# under it (that walk-off already happened once — see the layout exemptions).
_RIB = D.MOTOR_X_STEP / 2                    # 23.0 rib-comb pitch
_RIB0 = D.motor_pos(0)[0] - 2 * D.MOTOR_X_STEP   # -616: comb origin (2 pitches past m0)

# THE KNEE GAP. The player's knee sits BETWEEN a pair (LKL/LKR, RKL/RKR) and pushes
# one or the other; the vertical lever goes in the same gap, above the knee (user).
# The user's own steel measures ~120 here and asked for the closest step — but the
# step is NOT what binds. Each horizontal lever carries 82.36 of housing, almost all
# of it on the far side of its axle from the knee (an "…L" lever's cartridges run -X,
# an "…R" lever's +X), so a pair occupies gap + 154.72. Two pairs must fit between
# the left leg block (-592.4) and the right one (-35.3):
#
#     2 * (gap + 154.72) + clearance  <=  522.7   ->  gap <= ~106
#
# so 5 ribs (115) does not fit and 4 ribs (92) is the closest reachable step. Getting
# to 120 needs a NARROWER HOUSING, not a different station — the same 82.36 that
# already dictated the cluster spacing. Flagged rather than silently rounded.
# TWO GAPS NOW, and the LEFT one is ODD ON PURPOSE (user: the vertical lever is not
# centred between LKL and LKR). KV's two tenons are one rib apart, so a legal KV
# station is always rib - TEN_Y[1] = 11.9 off a rib — never ON one. An EVEN rib gap
# puts the pair's midpoint ON a rib, so the vertical lever could never be closer
# than ~11.9 to it, which is exactly what the user was looking at. An ODD gap puts
# the midpoint BETWEEN ribs, which is where a legal station already lives: 5 ribs
# lands it 0.4 off centre instead of 11.9.
#
# 115 is also nearer the user's original 120 knee-width target than 92 was. The right
# knee keeps 92 because the two pairs plus their housings have to fit between the leg
# blocks, and 115/115 does not — that is also why LKL sits at ILKL's own station
# rather than one slot +X of it. The ILKL offset is what pays for the wider left gap
# AND the centred vertical lever; the two levers simply stack front-to-back on one X,
# which is what an INNER lever is anyway.
_KNEE_GAP_L = 5 * _RIB                       # 115.0 — odd, so VKL can centre
_KNEE_GAP_R = 4 * _RIB                       # 92.0
_LEVER_SLOT = 1 * _RIB                       # 23.0 — ILKL -> LKL, all the leg leaves
#   ILKL lives in the FORWARD plane, which is exactly the band the -Y leg blocks
#   occupy (y -139.15..-95.15), so its housing must clear -592.4 in X: it cannot go
#   -X of -501. That pins the pair, and one rib is all the offset left over. The
#   originally-requested slot (69) is only affordable at a 69 knee gap, which is
#   worse where it matters — the knee has to fit.

# VKL sits at the SHARED PLANE like everything else, now that the mortise runs to the
# inside edge of the instrument (knee_lever.MORT_Y_END). It could not before: the
# slots stopped at mid-Y, the KV housing is 77.4 deep in +Y, and its tail ran 10.4
# into solid rib — so it had to sit that much further -Y, which put its arm in FRONT
# of the knee. The player would have had to pull back to reach it, defeating the one
# thing a vertical lever is for: lift without moving (user). Lengthening the slot
# bought the whole 10.4 back and then some. Still derived, still clamped, so the day
# the housing gets deeper this reports instead of burying itself in a rib.
def _vkl_mount_y() -> float:
    """VKL's mount Y: put the ARM'S CENTRE on the shared contact plane.

    Not the axle. The axle was on the plane and the user still read the lever as too
    far forward — because a KV arm runs 50 -Y of its axle and only 5 +Y, so an axle
    on the plane leaves the arm's centre 22.5 in FRONT of it, out where the knee has
    to be pulled back to meet it. What the knee actually touches is the arm, so the
    arm is what gets centred. Measured off the solid, and still clamped to the
    mortise so it cannot bury itself in a rib.
    """
    from . import knee_lever as KL
    from . import knee_lever_vert as KV
    b = KV.place(KV.kv_lever).val().BoundingBox()
    arm_off = (b.ymin + b.ymax) / 2.0 - KV.MOUNT_Y          # -22.5
    tail = KV.place(KV.kv_housing).val().BoundingBox().ymax - KV.MOUNT_Y
    return min(_LEVER_Y - arm_off, KL.MORT_Y_END - tail)


#   name    kind   station x        mount y     mirrored?
# `mirror` is the throw DIRECTION: a "…R" lever is struck by the knee moving +X, so
# it is the LKL design reflected. Reflection keeps the tenons on ribs (their offsets
# are rib multiples either way), but it does make a separate printed SKU — flagged,
# not exported yet.
# ILKL still needs X clearance from LKL even though their PADDLES are in different
# planes: the housings are deeper in Y than the paddles and their bands overlap. And
# its -X limit is the left leg, whose block ends at -596.6 — the first station that
# clears it is -501. Both bounds together pin ILKL and push the left group +X:
# ILKL -501, LKL -409 is exactly the 92 one-slot step the user described.
def _vkl_station() -> float:
    """VKL's mount X: the LEGAL station nearest the LKL/LKR midpoint.

    Legal means both its tenons land on ribs, which pins the station to
    rib - TEN_Y[1]. Rather than hardcode one (the last constant here silently put
    both tenons 0.7 off their ribs when the housing widened), walk the ribs and take
    whichever legal station sits closest to the midpoint the user wants it centred
    on. With the odd left gap that comes out 0.4 off.
    """
    from . import knee_lever_vert as KV
    mid = _LKL_X + _KNEE_GAP_L / 2.0
    # its tenons sit at KV.TEN_Y in the guitar's X once posed; _lever_station returns the MOUNT
    # that puts them all on real stations, so there is nothing left to subtract here (there used
    # to be, when it returned a station and this had to undo the offset by hand).
    #
    # ...THEN ONE MORTISE -X (user, 2026-09-18, reading the render). THE GRID CANNOT CENTRE THIS
    # LEVER: the two legal mounts either side of the knee gap's midpoint sit 5.20 off it each
    # way, so which one it takes is a preference, not an optimum, and the user wants the -X one.
    # Stepped by a whole PITCH, so the three tenons stay in slots that exist -- re-checked below
    # rather than assumed, because a lever over solid floor is 1-2.5 cm3 of interference and the
    # gate is the only other thing that would notice.
    m = _lever_station(mid, KV.TEN_Y) - D.LEVER_PITCH
    from . import chassis as CH_V
    _have = set(round(x, 3) for x in CH_V._MORT_X)
    _off = [round(m + t, 3) for t in KV.TEN_Y if round(m + t, 3) not in _have]
    assert not _off, ("the -X step puts VKL's tenons at %s, which are not mortise stations -- "
                      "the station one pitch -X of %.2f is dropped" % (_off, m + D.LEVER_PITCH))
    return m


def _lever_station(x_target, offsets, mirrored=False):
    """The lever's MOUNT X, closest to x_target, at which EVERY one of its tenons lands in a
    slot that exists.

    IT RETURNS A MOUNT, NOT A STATION (user, 2026-09-18), and the difference is real now: a
    lever's tenon set is anchored on its own housing edge, so it carries a phase and the mount
    sits off-station by exactly that. Candidate mounts are therefore station - offset[0], not
    the stations themselves.

    And not just the nearest grid X either. The bottom grid (D.LEVER_PITCH) drops stations where
    the leg feet and the segment seams need solid material, so a station can be on-pitch and
    still have no slot -- and a tenon over solid slab is 1-2.5 cm3 of interference, which is
    exactly what the gate reported when the knee gaps were still multiples of the old 22.35 rib
    pitch."""
    from . import chassis as CH_G
    have = set(round(s, 3) for s in CH_G._MORT_X)
    def _at(m, t):
        return round(m + (-t if mirrored else t), 3)
    first = (-offsets[0] if mirrored else offsets[0])
    ok = [s - first for s in CH_G._MORT_X
          if all(_at(s - first, t) in have for t in offsets)]
    assert ok, ("no mount on the bottom grid fits a lever with tenons at %s -- the set's own "
                "spacing has to be a multiple of the grid pitch" % (offsets,))
    return min(ok, key=lambda m: abs(m - x_target))


from . import knee_lever as _KL_ST
_LKL_X = _lever_station(-501.0, _KL_ST.TEN_X)   # hard -X bound: the left leg block (ILKL's old
                                                # station; LKL shared it — see _KNEE_GAP_L)
_RKL_X = _lever_station(-225.0, _KL_ST.TEN_X)   # right knee

LEVER_STATIONS = (
    # LEFT KNEE: the knee sits in the gap between LKL and LKR, and VKL sits in that
    # same gap so the vertical arm is directly above it (user). VKL's station is
    # rib-DERIVED (MOUNT_X = rib - 10.4) so its own two tenons land on ribs.
    ("lkl",  "kl", _LKL_X,               _LEVER_Y, False),
    ("vkl",  "kv", _vkl_station(),       None,     False),   # mid-gap, grid-derived
    #                                                          None -> _vkl_mount_y()
    # the GAPS are the ergonomic numbers; the station is the nearest one the grid can
    # actually host, which is within half a pitch (4.4) of it
    ("lkr",  "kl", _lever_station(_LKL_X + _KNEE_GAP_L, _KL_ST.TEN_X, True), _LEVER_Y, True),
    # RIGHT KNEE: same gap, no vertical lever in this copedent
    ("rkl",  "kl", _RKL_X,               _LEVER_Y, False),
    ("rkr",  "kl", _lever_station(_RKL_X + _KNEE_GAP_R, _KL_ST.TEN_X, True), _LEVER_Y, True),
)


def _knee_vert_components():
    """LKV, posed by its own 90°-about-Z mount (see knee_lever_vert.place). Drawn at
    REST; the throw would lift the arm. The rib mortises chassis.py already cuts take
    these tenons unchanged — same joint, same width, same mating plane, same slide
    direction once posed — so nothing in the chassis had to move for it."""
    from . import knee_lever_vert as KV
    out = [("kv_housing", KV.kv_housing), ("kv_lever", KV.kv_lever)]
    out += KV.demo_parts()
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
    out = [("knee_housing", KL.knee_housing), ("knee_lever", swing(KL.knee_lever)),
           ("kl_axle", swing(KL.kl_axle)),                  # keyed on its D-flat -> turns with the lever
           ("kl_magnet_cap", swing(KL.kl_magnet_cap))]      # screwed to the axle
    for nm, off, s in (("main", KL.CART_MAIN_OFFSET, s_main), ("half_stop", KL.CART_HALFSTOP_OFFSET, s_hs)):
        out.append((f"{nm}_cart_base", KL.feel_place(KL.cart_base.translate(off))))
        out.append((f"{nm}_cart_piston", KL.feel_place(KL.cart_piston.translate(off)).translate((-s, 0, 0))))
    for n, s in KL.demo_parts():                         # magnet spins with the lever; the rest are stationary
        out.append((n, swing(s) if n == "kl_magnet" else s))
    # (the octagon mount tenons are FUSED onto knee_housing now -- no separate floating_tenon parts)
    return out


def assert_storage_angle(tol=0.5):
    """KL.STORAGE is MEASURED, not derived, so check it against the real poses.

    The fold's limit is the VERTICAL lever's arm, and knee_lever cannot see either that
    or this module's station table -- KV imports KL, so the arrow only points one way.
    The number therefore lives where the sweep needs it and is verified here, where both
    ends of the question are visible. A station that moves fails loudly.
    """
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from . import knee_lever as KL
    from . import knee_lever_vert as KV

    vk = [st for st in LEVER_STATIONS if st[1] != "kl"][0]
    vy = _vkl_mount_y() if vk[3] is None else vk[3]
    arm = (KV.kv_lever.rotate((0, 0, 0), (0, 0, 1), -90)
           .translate((vk[2], vy, KV.MOUNT_Z)).val())
    worst = None
    for name, kind, sx, sy, mirrored in LEVER_STATIONS:
        if kind != "kl":
            continue
        s = KL.knee_lever.rotate((0, 0, 0), (0, 1, 0), -KL.STORAGE)
        if mirrored:
            s = s.mirror("YZ")
        g = BRepExtrema_DistShapeShape(
            s.translate((sx, sy if sy is not None else _vkl_mount_y(),
                         KL.MOUNT_Z)).val().wrapped, arm.wrapped).Value()
        worst = g if worst is None else min(worst, g)
    assert worst <= tol, (
        "KL.STORAGE is %.0f deg but the nearest knee lever still has %.2f mm to the "
        "vertical lever's arm there -- the fold could go further, or a station moved"
        % (KL.STORAGE, worst))
    return worst


def _lever_stations_components():
    """FIVE of the six knee levers, each design posed at its station (LEVER_STATIONS).

    ⚠ THIS SAID "ALL SIX" AND THE TABLE HAS FIVE. The instrument has 6 knee levers
    and 5 pedals (user, 2026-09-18; now D.N_LEVERS / D.N_PEDALS). LEVER_STATIONS lists
    lkl, vkl, lkr, rkl, rkr -- the right knee has no vertical lever "in this copedent",
    per the comment in the table, so the sixth control is not modelled here. The gap is
    real and not a typo; what was wrong was the docstring claiming coverage the table
    does not have. elec/lever_sensor.py orders against D.N_SENSED (11) and not against
    this table, so the sensor panel is unaffected -- but anything that sizes hardware
    from LEVER_STATIONS is sizing for five.

    Both source modules build their parts in a LOCAL frame and hand them to a
    module-level pose, so a station is just that pose with x/y replaced — the Z
    (housing top flush with the chassis underside) is the design's and stays put.

    NAMING: the LKL station keeps the bare part names the colour map, the export
    registry and the overlap gate's KNEE_FAMILY already know. The five new stations
    take a prefix, and _color_for's existing sibling rule gives them LKL's colours
    for free rather than needing 60 near-duplicate entries.
    """
    from . import knee_lever as KL
    from . import knee_lever_vert as KV

    kl_parts, kv_parts = _knee_lever_components(), _knee_vert_components()
    assert_storage_angle()
    out = []
    for name, kind, sx, sy, mirrored in LEVER_STATIONS:
        if sy is None:
            sy = _vkl_mount_y()
        if kind == "kl":
            parts, mz = kl_parts, KL.MOUNT_Z
        else:                                   # KV carries its own -90° about Z
            parts = [(n, s.rotate((0, 0, 0), (0, 0, 1), -90)) for n, s in kv_parts]
            mz = KV.MOUNT_Z
        for n, s in parts:
            if mirrored:
                s = s.mirror("YZ")              # local +X -> -X: the opposite throw
            out.append((n if name == "lkl" else f"{name}_{n}",
                        s.translate((sx, sy, mz))))
    return out


SCREW_ROW_PARTS = ("leadscrew", "nut_", "string_", "guide_rod",
                   "screw_pulley", "screw_bearing")


def travel_work_components():
    """EVERYTHING THE NUT'S TRAVEL MOVES OR MEETS, as one live set: all ten strings' whole
    drivetrains (screw, nut, guide rod, string, belt, clamp, motor) and the bridge endplate
    whose ceiling and rail are the two stops. The screw rows alone leave the belts and their
    clamps in grey cache, and the clamps reaching the pulleys is what the travel is about."""
    out = [(n, w) for i in range(D.N_STRINGS) for n, w in _string_components(i)]
    out.append(("bridge_endplate", PARTS["bridge_endplate"][0]()))
    out.append(("bridge_bearings", C.bridge_bearings()))
    return out


def screw_rows_components():
    """The +X drivetrain as ONE named set: both Tr8x2 screw rows and the endplate that
    hosts them.

    The build does not need this — collect_components already composes the same parts per
    string. It exists so the per-agent scratch view can make the whole two-row assembly
    LIVE, because that is the unit the work actually changes. A `part:` scope resolves to
    exactly one part, which left the rows sitting in grey cache next to the endplate they
    determine."""
    out = [(n, w) for i in range(D.N_STRINGS) for n, w in _string_components(i)
           if n.startswith(SCREW_ROW_PARTS)]
    out.append(("bridge_endplate", PARTS["bridge_endplate"][0]()))
    # the bridge bearings + axle, and the strings over them (string_ above): the 688ZZ swap
    # and the string path from ear to bearing are part of the same unit
    out.append(("bridge_bearings", C.bridge_bearings()))
    return out


BODY_WORK_PARTS = SCREW_ROW_PARTS + (
    "bridge_endplate", "bridge_bearings", "motor", "chassis_",
    # BOTH SIDES OF THE MERGE ARE RIGHT HERE: main added the deck/pickup/optical
    # parts while this branch deleted teensy_/adc_stack/buck/analog_frontend and the
    # three free-standing panel jacks (they are PCB parts on the output+panel board
    # now). Keep main's additions, keep the deletions.
        "pi4", "pi_cap", "pi_spacer", "led_strip_", "motor_ctrl", "tee_", "wire_",
        "output_panel", "ui_",
    "body_adapter", "lock_pin_", "adjust_", "fixed_", "bar_latch_", "leg_latch_",
    "top_plate", "pickup", "optical")   # the deck piece too: its skirt sets the bay's headroom


def optical_work_components():
    """The optical board and the two parts that SHAPE it -- for the O-band work.

    ⚠ body_work_components WAS THE WRONG UNIT FOR THIS AND THE VIEW SHOWED IT. That set is
    293 parts, essentially the whole instrument, and ScratchView only skips caching for
    names matching `replaced` prefixes -- so with none declared every live part was ALSO
    cached and rendered twice. The user saw the old C-shaped board sitting inside the new
    O-shaped one. A live set that big also saves nothing: the cache exists to skip the
    build, and there was almost nothing left to skip.

    This is the actual unit of the work: the board, the endplate whose block it cuts into,
    and the chassis it sits above. Scope it with
        scope --set src.build --attr optical_work_components --crop bridge               --replaced optical_,bridge_endplate,chassis_
    so the cache leaves those to the live build instead of duplicating them.

    ⚠ BOTH ENDPLATE BOARDS, NOT JUST THE OPTICAL ONE (user, 2026-09-25). The instrument
    carries a PCB at each end -- the optical strip in the bridge endplate and the motor
    controller in the keyhead endplate's cradle -- and the work has crossed between them all
    day (the bus-B connectors moved to the motor board's downward edge while the optical
    board was routing). A scope holding one of them makes the other invisible exactly when
    a change to the chassis has to suit both.
    """
    from . import optical_pickup as OP
    from . import electronics as EL
    _KE = __import__("src.keyhead_endplate", fromlist=["e"])
    # ⚠ AND THE FLAT PI WITH ITS SPACER, FOR THE SAME REASON THE MOTOR BOARD IS HERE. The
    # retention work crossed into the Pi's bay (its hold-down had to leave the board's edge
    # entirely -- electronics.PI_SPACER_XY), and a scope that hides the part being designed is
    # how the user came to report "the pi disappeared from your tab". The spacer is the point of
    # the change, so it has to be visible in the view that reviews it.
    out = [("optical_pcb", OP.opt_pcb()),
           ("optical_cable_usb", OP.opt_cables("usb")),
           ("optical_cable_pwr", OP.opt_cables("pwr")),
           ("bridge_endplate", PARTS["bridge_endplate"][0]()),
           ("motor_ctrl", EL.motor_ctrl()),
           ("pi4", EL.pi4()), ("pi_spacer", EL.pi_spacer()),
           ("keyhead_endplate", _KE.keyhead_endplate)]
    # ⚠ AND THE FASTENERS, BECAUSE THEY MOVE WITH THE RETENTION AND THE CACHE DOES NOT KNOW.
    # Left to the cache, board_screw_2/board_insert_2 stay at the hold position they had when
    # it was built -- and a scoped gate then reports the OLD screw against the NEW chassis:
    # 61.1 mm3 into chassis_2, 47.1 of insert, 36.5 into knee_housing and 112.8 through
    # pi_spacer, every one of them an artefact of an 83-minute-old cache rather than a fault in
    # the design. Live, they are checked where they actually are.
    out += EL.board_screws()
    out += [(f"chassis_{i}", seg) for i, seg in enumerate(chassis_segments)]
    return out


def body_work_components():
    """The motor bank, the standing electronics and their harness, the chassis, the legs and
    the +X screw rows as ONE live set -- for work that runs the length of the body (the bank
    packed against the electronics, the rib comb, the legs' service slide over the string
    access channels). The DECK PIECE is live too: its -Y skirt is the floor over the motor
    bank, so a change there lands on the tees."""
    out = screw_rows_components()
    out += [(n, w) for i in range(D.N_STRINGS) for n, w in _string_components(i)
            if n.startswith("motor")]
    out += _electronics_components()          # includes the deck pieces
    out += [(f"chassis_{i}", seg) for i, seg in enumerate(chassis_segments)]
    out += [(f"chassis_light_{i}", lt) for i, lt in enumerate(chassis_light)]
    out += _leg_components()
    out += _pickup_mount_components()
    return out


def lever_components():
    """Every lever as ONE named set: the five modelled knee-lever stations (of six --
    see _knee_components) and the foot pedals.

    Like screw_rows_components, the build does not need it; it exists so the per-agent
    scratch view can make the whole lever family LIVE. All of them share knee_lever's
    bearing, axle, hub and seat helpers, so a change there is one unit of work."""
    return _lever_stations_components() + _foot_pedal_components()


_LKL_VKL_STATIONS = ("lkl", "vkl")   # the focused stations (user: LKL + LKV)


def lkl_vkl_box():
    """(w, d, h, x, y, z) round the focused lever stations (_LKL_VKL_STATIONS): the levers
    whole, plus the chassis bottom they hang from. X/Z come from the stations' posed parts; Y spans
    the whole chassis (the rib mortises run its depth); +Z stops under the deck so the
    view looks up into the ribs rather than at the top plate."""
    from . import chassis as CH, top_plate as TP
    bbs = [w.val().BoundingBox() for n, w in _lkl_vkl_levers()]
    x0, x1 = min(b.xmin for b in bbs) - 30.0, max(b.xmax for b in bbs) + 30.0
    y0, y1 = CH.Y_LO - 10.0, CH.Y_HI + 10.0
    z0, z1 = min(b.zmin for b in bbs) - 10.0, TP.BZ
    return (x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)


def _lkl_vkl_levers():
    # LKL keeps the bare names; the other stations are prefixed (see _lever_stations_components)
    others = tuple(f"{st[0]}_" for st in LEVER_STATIONS if st[0] not in _LKL_VKL_STATIONS)
    return [(n, w) for n, w in _lever_stations_components() if not n.startswith(others)]


def lkl_vkl_components():
    """The focused lever stations and the chassis bottom they mount to, as ONE live set -- for the lever
    joinery work. The chassis is CLIPPED to lkl_vkl_box(): the rest of its length is
    context the levers cannot reach, and it is most of the solids."""
    w, d, h, x, y, z = lkl_vkl_box()
    box = cq.Workplane("XY").box(w, d, h).translate((x, y, z))
    out = _lkl_vkl_levers()
    for n, seg in ([(f"chassis_{i}", s) for i, s in enumerate(chassis_segments)]
                   + [(f"chassis_light_{i}", s) for i, s in enumerate(chassis_light)]):
        clip = seg.intersect(box)
        if clip.solids().vals():
            out.append((n, clip))
    return out


LEG_CONTEXT_Z = 250.0    # how far UP the legs the pedal-bar crop reaches


def pedal_bar_box():
    """(w, d, h, x, y, z) round the PEDAL BAR: the bar end to end, its towers, the
    pedals standing on it, the feet under it -- and LEG_CONTEXT_Z of the leg columns
    above it.

    The legs are the reason for that last term. A box drawn to the bar's own bounds
    is only ~175 tall, and everything the bar hangs off is outside it, so the view
    came out as a bar floating in space with no instrument attached to it (user). The
    box stops well short of the body all the same: the legs are ~700 long and all of
    that is somebody else's work."""
    bbs = [w.val().BoundingBox() for _, w in _pedal_bar_components() + _foot_pedal_components()]
    x0, x1 = min(b.xmin for b in bbs) - 20.0, max(b.xmax for b in bbs) + 20.0
    y0, y1 = min(b.ymin for b in bbs) - 30.0, max(b.ymax for b in bbs) + 30.0
    z0 = min(b.zmin for b in bbs) - 30.0
    z1 = max(b.zmax for b in bbs) + LEG_CONTEXT_Z
    return (x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)


def pedal_bar_work_components():
    """The bar, its lid and latch, and the five pedals on it, as ONE live set -- for
    work on the bar itself (the wiring trough, the splices, the fused housings). Like
    lever_components, the build does not need it: it exists so the scratch view can
    make the whole bar live at once, which is the unit a trough change touches."""
    return _pedal_bar_components() + _foot_pedal_components()


def lever_bus_nodes():
    """[(name, plug, lace, out_dir)] in GUITAR coordinates, in CHAIN ORDER -- what
    src.wiring.lever_bus needs to draw the knee levers' bus-B harness and cut list.

    It lives here because a station's POSE lives here (LEVER_STATIONS, and the rotate /
    mirror / translate in _lever_stations_components), and wiring is imported BY this
    module -- the same one-way dodge the pedal housings use. The two attachment points
    themselves are the LEVERS' (knee_lever.plug_point / lace_point), read off the
    connector and the lace loop, so nothing here is a transcribed coordinate.

    CHAIN ORDER IS -X -> +X: bus B arrives from the motor controller at the keyhead and
    the far end of the chain terminates at the +X-most lever (elec/motor_ctrl: the
    controller is a MID-BUS node now, and the ends close their own JP1).

    Each node is (name, plug, keeper, plug_dir, keeper_axis, pin_axis, pins, standoff,
    cheek_axis, cheek_bypass, guide),
    where `pins` is {way: point} for all CONN_N ways of that lever's J1 -- so the model
    shows which conductor belongs in which slot (user).

    """
    from . import knee_lever as KL
    from . import knee_lever_vert as KV

    def _pose(kind, sx, sy, mirrored, p, vector=False):
        x, y, z = p
        if kind != "kl":
            x, y = y, -x                    # the -90 about Z that KV parts carry
        if mirrored:
            x = -x                          # mirror YZ: local +X -> -X
        if vector:
            return (x, y, z)
        return (x + sx, y + sy, z + (KL.MOUNT_Z if kind == "kl" else KV.MOUNT_Z))

    out = []
    for name, kind, sx, sy, mirrored in sorted(LEVER_STATIONS, key=lambda st: st[2]):
        if sy is None:
            sy = _vkl_mount_y()
        if kind == "kl":
            pin = KL.plug_pin
            lace = KL.keeper_point()
        else:
            def pin(w, _K=KV):
                return KL.plug_pin(w, _K.HOUS_Z0, _K.HOUS_Z1)
            # ...WITH ITS OWN HOUSING TOP. Left off, keeper_point fell back to the
            # HORIZONTAL lever's, and since the winding is measured DOWN from the top,
            # LKV's coil hung 19.6 below its own column (user).
            lace = KL.keeper_point(KV.HOUS_Z0, KV.HOUS_X0, KV.HOUS_HW_P, KV.HOUS_Z1)
        plug = pin((KL.CONN_N + 1) / 2.0)
        # the plug's wires leave along local -X (the mouth faces -X), posed the same way
        p = _pose(kind, sx, sy, mirrored, plug)
        l = _pose(kind, sx, sy, mirrored, lace)
        d = _pose(kind, sx, sy, mirrored, (-1.0, 0.0, 0.0), vector=True)
        ka = _pose(kind, sx, sy, mirrored, KL.keeper_axis(), vector=True)
        pa = _pose(kind, sx, sy, mirrored, KL.pin_axis(), vector=True)
        ca = _pose(kind, sx, sy, mirrored, KL.cheek_axis(), vector=True)
        pins = {w: _pose(kind, sx, sy, mirrored, pin(w)) for w in range(1, KL.CONN_N + 1)}
        # WHERE THE ARRIVING CABLE TURNS, on the one lever whose plug the bus cannot
        # reach in a straight line: the vertical one, whose body lies along its plug's
        # axis, so the cable has to come round the +Y end before it can run back to the
        # connector.
        #
        # IT TURNS ON THE HOUSING'S OWN BACK CORNER -- no part at all (user: "you added
        # an extra winding post to the LKV but it's unnecessary"). A turn post was added
        # when the approach came round the FRONT, into the arm's sweep; round the back
        # there is already a corner to rest on, and a corner is a contact surface like
        # any other. Tried its own KEEPER column first: that sits on the connector
        # cheek, so turning there means arriving through the body (66 mm3).
        # ...AND AT THE COLUMN'S OWN HEIGHT, so the run reaches the corner level and
        # goes straight on. Off it, the cable drops in Z to round the corner and climbs
        # back for the connector, for no reason a part gives it (user).
        _off = KL.CANB_BUNDLE_OD / 2.0 + D.MIN_WALL
        guide = (_pose(kind, sx, sy, mirrored,
                       (KV.HOUS_X0 - _off, -KV.HOUS_HW_N - _off,
                        KL.keeper_point(KV.HOUS_Z0, KV.HOUS_X0, KV.HOUS_HW_P,
                                        KV.HOUS_Z1)[2]))
                 if kind != "kl" else None)
        out.append((name, p, l, d, ka, pa, pins, KL.plug_standoff(),
                    ca, KL.cheek_bypass(), guide))
    return out


def _ctrl_bus_components():
    """Bus B's two ARRIVALS at the motor controller, drawn. See wiring.ctrl_bus_b.

    Separate from _lever_bus_components because these are not lever-to-lever segments:
    they are the pedal bar's cable coming in off the instrument's underside and the head
    of the lever chain, and both cross the chassis floor through the one wiring port."""
    from . import wiring as WR
    return WR.ctrl_bus_b(lever_bus_nodes()[0])


def _lever_bus_components():
    """The knee levers' bus-B harness, drawn. See wiring.lever_bus."""
    from . import wiring as WR
    parts, _ = WR.lever_bus(lever_bus_nodes())
    return parts


def cable_cut_list():
    """The modelled harness as a CUT LIST -- what to cut before crimping."""
    from . import wiring as WR
    return WR.lever_bus_cut_list(lever_bus_nodes())


def lever_harness_box():
    """(w, d, h, x, y, z) round the KNEE LEVERS and their harness -- the unit of work,
    and nothing else. The pedal bar is 600 mm away down the legs and shares only the
    board design, so carrying it live cost minutes a gate for geometry the levers
    cannot reach (user)."""
    from . import top_plate as TP
    bbs = [w.val().BoundingBox()
           for _, w in (_lever_stations_components() + _lever_bus_components()
                       + _ctrl_bus_components())]
    x0, x1 = min(b.xmin for b in bbs) - 25.0, max(b.xmax for b in bbs) + 25.0
    y0, y1 = min(b.ymin for b in bbs) - 25.0, max(b.ymax for b in bbs) + 25.0
    z0, z1 = min(b.zmin for b in bbs) - 15.0, TP.BZ
    return (x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)


def lever_harness_components():
    """The knee levers and the bus-B harness between them, as ONE live set. The pedals
    and the bar are OUT: they are a separate subassembly that this work does not move,
    and leaving them in made every gate rebuild 500 solids to check 200."""
    return (_lever_stations_components() + _lever_bus_components()
            + _ctrl_bus_components())


def bus_b_components():
    """EVERYTHING ON BUS B as ONE live set: the five modelled knee-lever stations, the
    five foot pedals, and the pedal bar they are fused into.

    The bus is the unit of work for the harness -- a lever chains to the next lever and
    the chain carries on down the leg to the bar -- and it is the one view that shows
    both ends of it. Like lever_components, the build does not need this; it exists for
    the scratch view. No crop goes with it: the chain spans the whole instrument, and
    cropping to the levers is what left the pedal bar looking like a bar in empty
    space."""
    return (lever_components() + _pedal_bar_components()
            + _lever_bus_components() + _ctrl_bus_components())


def ctrl_bus_work_components():
    """BUS B'S CROSSING OF THE CHASSIS FLOOR as one live set: the two cables that arrive
    at the motor controller, and everything they have to get past to do it.

    It is body_work plus the bus, and it needs to be both. The pedal cable starts inside
    the -X/+Y LEG, comes out of the body adapter onto the instrument's UNDERSIDE, crosses
    it, passes through a port in the CHASSIS floor slab, and lands on a connector on the
    standing ELECTRONICS tray; the lever half comes up from the knee-lever bay below. A
    live set holding only the harness would gate a cable against nothing it can hit, and
    one holding only the body would not gate the cable at all."""
    out = body_work_components()
    have = {n for n, _ in out}
    for n, w in lever_components() + _lever_bus_components() + _ctrl_bus_components():
        if n not in have:
            out.append((n, w))
    return out


def ui_work_components():
    """THE UI STATION as one live set: the deck panel it is cut into, the board, the
    display, the knob, and everything under that part of the deck.

    It has to be the whole body, not just the station. The UI board hangs 13 mm below a
    deck panel that SLIDES OUT -X for service, so every part of its cradle sweeps the
    length of the bay on the way out; and the -Y band it sits over is the band the motor
    bank and its tee boards live under. A live set holding only the UI would gate it
    against nothing it can reach."""
    out = body_work_components()
    have = {n for n, _ in out}
    for n, w in _ctrl_bus_components():
        if n not in have:
            out.append((n, w))
    return out


def _tensioner_coupon_components():
    """The unified belt clamp shown ASSEMBLED, parked off the +X end for a clear look (the real
    clamps ride each string's belt). ONE SKU per half (`clamp_half`; half-B is it turned 180° about
    Z), the M4 head on half-A's −X face, the insert used as a plain EXTERNAL nut on half-B's +X face.
    Reuses the pre-built clamp parts (no extra geometry) so it can't drift from the real placements."""
    o = cq.Vector(150.0, 90.0, 40.0)
    return [(f"{nm}_coupon", cq.Workplane("XY").add(shp.val().translate((o.x, o.y, o.z))))
            for nm, shp in BTn.clamp_components(with_lifters=True)]


def collect_components():
    """EVERY placed thing in the instrument: [(name, cq.Workplane), ...].

    The one entry point the whole tool chain is built on -- the overlap and sweep
    gates, the GLB and rig exporters, scratch_view and the build profiler all take
    their model from here, so a part that is not in this list is invisible to every
    check in the project. It is the ASSEMBLY, not the print list: purchased-part
    dummies, PCBs and the wiring harness are all in it, each already posed in world
    coordinates (printed parts are exported separately, in their print poses).

    Names matter beyond display. The gates key their allow-lists on them, and a
    trailing index (``chassis_0``) is stripped to a base name before matching, so
    renaming a part silently changes which contacts are treated as designed.
    """
    _KE = __import__("src.keyhead_endplate", fromlist=["e"])
    # the standing electronics and the whole motor bank are packed against this face
    # (dimensions.KEYHEAD_INBOARD_X). Checked here, where the gate builds the keyhead anyway
    # -- importing it at module level costs ~4 s on every build.
    assert abs(_KE.HS_X1 - D.KEYHEAD_INBOARD_X) < 1e-6, (
        f"the keyhead's inboard face moved to {_KE.HS_X1:.2f}; dimensions.KEYHEAD_INBOARD_X is "
        f"{D.KEYHEAD_INBOARD_X:.2f} -- update it and the motor bank follows")
    comps = [
        ("bridge_endplate", bridge_endplate),
        ("bridge_bearings", C.bridge_bearings()),
        ("keyhead_endplate", _KE.keyhead_endplate),
    ]
    comps += [(f"chassis_{i}", seg) for i, seg in enumerate(chassis_segments)]
    comps += _pickup_mount_components()
    comps += _leg_components()
    comps += _pedal_bar_components()
    comps += _foot_pedal_components()
    comps += _electronics_components()
    comps += _lever_stations_components()      # all five, LKL/VKL included
    # ...AND THE HARNESS THAT RUNS BETWEEN THEM. Left out when the bus-B harness landed
    # (2026-09-23), so all 36 conductors were built by lever_harness_components() for the
    # agent's own scratch view and by NOTHING ELSE: absent from assembly.step, from the web
    # preview, and -- the part that matters -- from the overlap gate, which takes its model
    # from this function. The user spotted it as missing geometry in the viewer; the gate had
    # been reporting green on an instrument with no lever wiring in it.
    comps += _lever_bus_components() + _ctrl_bus_components()
    comps += _wrap_rod_component()
    comps += _tensioner_coupon_components()
    for i in range(D.N_STRINGS):
        comps.extend(_string_components(i))
    return comps


# Per-part colours, baked into the assembly STEP (single source of truth — they
# show in the shared FreeCAD live viewer and any STEP viewer). RGB floats 0..1.
_COLORS = {
    "bridge_endplate": (0.39, 0.58, 0.93),   # PETG-GF — load-critical
    "keyhead_endplate": (0.42, 0.50, 0.62),   # PETG-GF — keyhead endplate + nut block (merged)
    # belt-tension clamp — real per-string parts (PETG halves, PCTG 0.2 mm lifter, steel/brass fasteners)
    # ONE HUE PER SKU (user). The a/b pairs are deliberately EQUAL, not an oversight
    # to be "fixed": clamp_half is one printed part fitted twice (half-B is it turned
    # 180 about Z) and both lifter bars are one part, so colouring the pair members
    # differently would assert a distinction that does not exist in the BOM. What has
    # to be distinguishable is the four SKUs, which is what the old table got wrong --
    # the lifter tan sat next to the brass insert, and the two halves differed by 0.05
    # in a single channel while every one of them fell through to grey anyway.
    "belt_tensioner_half_a": (0.95, 0.55, 0.15),    # clamp_half  x2  printed
    "belt_tensioner_half_b": (0.95, 0.55, 0.15),    #   ""  same SKU, same colour
    "belt_tensioner_lifter_a": (0.30, 0.75, 0.40),  # lifter bar  x2  printed (0.2 nozzle)
    "belt_tensioner_lifter_b": (0.30, 0.75, 0.40),  #   ""  same SKU, same colour
    "belt_tensioner_screw":  (0.55, 0.55, 0.58),   # steel M4
    "belt_tensioner_insert": (0.72, 0.60, 0.30),   # brass insert (used as an external nut)
    # …and the parked assembled coupon (green = clearly a reference, not a product part)
    # The coupon keeps its own COOL family so the parked copy never reads as a real
    # clamp; same one-hue-per-SKU rule within it.
    "belt_tensioner_half_a_coupon": (0.20, 0.70, 0.45),
    "belt_tensioner_half_b_coupon": (0.20, 0.70, 0.45),
    "belt_tensioner_lifter_a_coupon": (0.15, 0.50, 0.75),
    "belt_tensioner_lifter_b_coupon": (0.15, 0.50, 0.75),
    "belt_tensioner_screw_coupon":  (0.55, 0.55, 0.58),
    "belt_tensioner_insert_coupon": (0.72, 0.60, 0.30),
    "screw_pulley":    (0.00, 0.55, 0.55),
    "screw_top_bearing": (0.69, 0.77, 0.87),
    "motor_pulley":    (0.00, 0.55, 0.55),
    "leadscrew":       (0.75, 0.75, 0.78),   # steel
    "screw_bearing":   (0.69, 0.77, 0.87),
    "bridge_bearings": (0.69, 0.77, 0.87),
    "nut":             (0.82, 0.60, 0.20),   # brass
    "string_nut":      (0.82, 0.60, 0.20),   # brass string-end fitting (demo)
    "guide_rod":       (0.35, 0.35, 0.38),
    "motor":           (0.22, 0.25, 0.27),   # charcoal
    "belt":            (0.13, 0.13, 0.13),   # GT2 black
    "string":          (0.85, 0.85, 0.85),
    "break_dowel":     (0.75, 0.75, 0.78),
    "nut_height_screw": (0.72, 0.74, 0.78),   # M4 x 20 button, pushes the insert up
    "nut_height_insert": (0.72, 0.60, 0.30),  # M4 heat-set in the keyhead slab
    "nut_slide_insert": (0.86, 0.72, 0.30),   # the sliding insert -- brass-ish, so it
                                              # reads apart from the steel it presses on
   # steel dowel (gauged break pin)
    "nut_wrap_rod":    (0.62, 0.66, 0.72),   # THE CAPSTAN -- one rod, and it is the bridge
                                             # axle's own O5 g6 shaft
    "set_screw":       (0.55, 0.55, 0.58),   # alloy set screw
    "pickup_jack_screw":  (0.55, 0.55, 0.58),  # M4 top-access height set-screw jack
    "pickup_jack_insert":  (0.80, 0.60, 0.35),  # brass heat-set insert (jack)
    "pickup_retention_screw": (0.55, 0.55, 0.58),  # M4 -Y retention cup-tip set screw
    "pickup_retention_insert": (0.80, 0.60, 0.35),  # brass heat-set insert (-Y retention grub)
    "chassis":         (0.46, 0.52, 0.55),   # PETG-GF frame
    "pickup":          (0.10, 0.10, 0.12),   # DEMO pickup body
    "pickup_zplate":   (0.85, 0.65, 0.30),   # PCTG height plate (under the pickup)
    "leg_body_stub":   (0.36, 0.42, 0.46),
    # redesigned leg (src.leg_stack): sleeves read as the GF structure they are,
    # tenons a shade warmer so the floating pieces are tellable at a glance
    "body_adapter":    (0.36, 0.42, 0.46),   # PETG-GF, same family as leg_head
    "fixed_sleeve":    (0.42, 0.48, 0.52),   # PETG-GF, as the old segment bodies
    "adjust_sleeve":   (0.42, 0.48, 0.52),
    "fixed_tenon":     (0.55, 0.52, 0.44),   # PETG-GF floating tenons
    "adjust_tenon":    (0.62, 0.56, 0.42),
    "leg_latch_slider": (0.85, 0.35, 0.20),  # body latch accent
    "leg_latch_spring": (0.62, 0.64, 0.67),  # stainless coil (purchased)
    "lock_pin_screw":  (0.55, 0.55, 0.58),   # M4x12 button head (purchased)
    "lock_pin_insert": (0.80, 0.60, 0.35),   # brass heat-set insert
    # the leg's blind-mates: pogo boards (src.leg_pogo). PCB green, gold pads/pins,
    # the JST PH mated envelope in harness white, screws steel
    "pogo_male_board":   (0.10, 0.35, 0.18),
    "pogo_female_board": (0.10, 0.35, 0.18),
    "pogo_male_pins":    (0.83, 0.69, 0.22),
    "pogo_female_pads":  (0.83, 0.69, 0.22),
    "pogo_male_ph":      (0.90, 0.90, 0.86),
    "pogo_female_ph":    (0.90, 0.90, 0.86),
    "pogo_male_screw":   (0.62, 0.64, 0.67),
    "pogo_female_screw": (0.62, 0.64, 0.67),
    "pogo_male_insert":  (0.72, 0.52, 0.20),   # the brass heat-set inserts
    "pogo_female_insert": (0.72, 0.52, 0.20),
    # the leg's harness: FOUR conductors, in the same colours src.wiring gives every
    # CAN run (black GND / red hot / yellow CAN-H / green CAN-L) -- INCLUDING through
    # the slack coil, which used to be one red body at the bundle's diameter and is now
    # four helices carrying their own places in the bundle (user)
    # ...keyed BY PIN NUMBER off elec.harness, in wiring's colour order (return black,
    # rail red, CAN-H yellow, CAN-L green), so the colours follow the pinout instead of
    # being a fifth place the circuit names are written out
    "leg_trrs_plug":   (0.15, 0.15, 0.17),   # the blind-mate: the FIXED plug, in the
    "leg_trrs_jack":   (0.20, 0.20, 0.22),   # adapter's roof...and the FLOATING jack
    "leg_trrs_spring": (0.62, 0.64, 0.67),   # ...the coil that holds them together
    "leg_trrs_throat": (0.34, 0.56, 0.44),   # ...and the ring that keeps the jack in
    "bar_trrs_sleeve": (0.03, 0.03, 0.03),   # the bottom joint's TPU carrier (black)
    "bar_trrs_throat": (0.05, 0.05, 0.06),   # ...and the TPU keeper for its jack
    "bar_trrs_jack":   (0.12, 0.12, 0.14),   # ...the bought jack it holds
    "bar_trrs_lead":   (0.45, 0.45, 0.48),   # ...and the lead out of its back, as far as the bar's wiring channel
    "bar_trrs_plug":   (0.15, 0.15, 0.17),   # ...the male plug it floats
    "bar_trrs_spring": (0.62, 0.64, 0.67),   # ...and the coil above it
    "leg_trrs_sleeve": (0.03, 0.03, 0.03),   # ...and the TPU cup that holds the plug (black)
    "leg_trrs_patch":  (0.12, 0.12, 0.14),   # ...the lead up to the chassis socket
    "leg_trrs_leg_lead": (0.12, 0.12, 0.14), # ...and the column's own, down the leg
    "bar_latch_frame": (0.85, 0.35, 0.20),   # pedal bar latch accent
    "bar_latch_collar": (0.36, 0.42, 0.46),  # PETG-GF, the bar tower's family
    "bar_latch_spring": (0.62, 0.64, 0.67),
    "bar_latch_screw": (0.55, 0.55, 0.58),   # M4 button -- same SKU, same colour
    "bar_latch_insert": (0.80, 0.60, 0.35),  # as the leg's screw and insert
    "leg_seg_body":    (0.42, 0.48, 0.52),   # square GF bodies
    "leg_coupler_m":   (0.36, 0.42, 0.46),
    "leg_coupler_f":   (0.36, 0.42, 0.46),
    "leg_head":        (0.36, 0.42, 0.46),
    "leg_pinch_gib":   (0.85, 0.35, 0.20),   # clamp accent (matches bolts)
    "leg_plug_retainer": (0.42, 0.48, 0.52),
    "chassis_trrs_jack": (0.62, 0.64, 0.67),
    "leg_column_plug":  (0.32, 0.36, 0.58),  # slate, matches the bar plug
    "chassis_trrs_cable": (0.45, 0.45, 0.48),
    "leg_column_cable": (0.45, 0.45, 0.48),
    "leg_cable_coil":  (0.45, 0.45, 0.48),   # heat-set coil section (slack
                                             # take-up in the segment core)
    "leg_sleeve":      (0.36, 0.42, 0.46),
    "leg_sleeve_cover": (0.30, 0.36, 0.40),
    "leg_shaft":       (0.55, 0.58, 0.62),
    "leg_foot":        (0.12, 0.12, 0.13),   # TPU
    # pedal bar (2 spliced pieces + 2 dovetail-lid pieces) + latches
    "pedal_bar_a":      (0.30, 0.45, 0.35),  # PETG-GF bar, -X piece
    "pedal_bar_b":      (0.33, 0.48, 0.38),  # PETG-GF bar, mid piece
    "pedal_bar_c":      (0.31, 0.46, 0.36),  # PETG-GF bar, +X piece
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
    "pedal_trrs_cable_bar": (0.45, 0.45, 0.48),  # trough → stub plug seat

    "shaft_trrs_jack": (0.62, 0.64, 0.67),       # bar-joint jack (10-03404)
    "shaft_trrs_cable": (0.45, 0.45, 0.48),
    "jack_seat_ring":  (0.42, 0.48, 0.52),
    "build_counter":   (0.86, 0.08, 0.24),
    # knee lever (LKL) — input-side control
    "knee_housing":    (0.30, 0.36, 0.42),   # PCTG housing
    "knee_lever":      (0.27, 0.51, 0.71),   # PCTG lever/paddle
    "kl_axle":         (0.30, 0.54, 0.68),   # PCTG full-length axle (near the lever blue)
    "kl_axle_screw":   (0.55, 0.55, 0.58),   # M4 x 10 button in the axle's -Y end
    "kl_axle_washer":  (0.72, 0.72, 0.75),
    "kv_axle_screw":   (0.55, 0.55, 0.58),
    "kv_axle_washer":  (0.72, 0.72, 0.75),
    "kl_magnet_cap":   (0.24, 0.44, 0.56),   # PCTG magnet retainer
    "kl_chip":         (0.12, 0.12, 0.14),   # MT6701 package (black)
    # the rest of the sensor board's real population (knee_lever.SENSOR_BOM). The
    # kv_/pedal{i}_ instances inherit these by the prefix rules in _color_for.
    "kl_mcu":          (0.16, 0.16, 0.19),   # CH32V203G6U6 QFN-28 (black, slightly lifted)
    "kl_transceiver":  (0.20, 0.20, 0.23),   # SN65HVD230DR SOIC-8 (black)
    "kl_buck":         (0.24, 0.24, 0.27),   # LMR16006XDDCR SOT-23-6 (black)
    "kl_inductor":     (0.35, 0.30, 0.28),   # shielded inductor (dark ferrite)
    "kl_crystal":      (0.72, 0.74, 0.78),   # 3225 crystal can (bright metal)
    "kl_bearing":      (0.69, 0.77, 0.87),   # MR85ZZ
    "kl_magnet":       (0.80, 0.20, 0.20),   # diametric magnet
    "kl_pcb":          (0.05, 0.35, 0.15),   # MT6701 board (green)
    "kl_can_header":   (0.95, 0.95, 0.90),   # JST S4B-XH-SM4-TB + mated XHP-4 (natural white)
    "kv_housing":      (0.30, 0.36, 0.42),   # LKV housing (PETG-GF, as LKL)
    # ...THE SAME BLUE AS LKL'S ARM, not a colour of its own (user, 2026-09-25: "the
    # levers are blue for LKL but yellow for LKV, we should color them consistently").
    # The comment beside it already said "as LKL" while the number said otherwise, which
    # is how it survived: same part, same job, same material, two colours.
    "kv_lever":        (0.27, 0.51, 0.71),   # LKV arm (PCTG, as LKL -- the same blue)
    "kv_pcb":          (0.05, 0.35, 0.15),   # LKV MT6701 board (green, as LKL)
    "kv_chip":         (0.12, 0.12, 0.14),   # LKV MT6701 package (black)
    "kv_can_header":   (0.95, 0.95, 0.90),   # LKV S4B-XH-SM4-TB + mated XHP-4
    "kv_pcb_shim":     (0.75, 0.75, 0.78),   # LKV board shim (printed, takes up the slack)
    # feel parts (unified: two identical spring cartridges, main -Y + half-stop +Y)
    "main_spring":                        (0.55, 0.20, 0.75),
    "half_stop_spring":                   (0.75, 0.45, 0.88),
    "main_spring_tension_screw":          (0.55, 0.55, 0.58),
    "half_stop_spring_tension_screw":     (0.62, 0.62, 0.66),
    "main_cart_base":                     (0.85, 0.65, 0.13),   # printed cartridge (shared part)
    "main_cart_piston":                   (0.95, 0.80, 0.30),
    "half_stop_cart_base":                (0.80, 0.60, 0.10),
    "half_stop_cart_piston":              (0.92, 0.76, 0.26),
    "main_spring_seat_washer":            (0.72, 0.72, 0.75),   # steel washers + position screws
    "half_stop_spring_seat_washer":       (0.72, 0.72, 0.75),
    "main_position_washer":               (0.72, 0.72, 0.75),
    "half_stop_position_washer":          (0.72, 0.72, 0.75),
    "main_position_screw":                (0.55, 0.55, 0.58),
    "half_stop_position_screw":           (0.62, 0.62, 0.66),
    "retention_setscrew":                 (0.40, 0.40, 0.43),   # -Y lock screw
    # electronics bay (dummies) + panel jacks

    "pi4":             (0.05, 0.35, 0.15),   # PCB green
    "pi_cap":          (0.05, 0.35, 0.15),   # PCB green
    "pi_spacer":       (0.85, 0.55, 0.20),   # PRINTED: the Pi's retention, not a board
    "led_strip_":      (0.05, 0.35, 0.15),   # PCB green
    "output_panel":    (0.45, 0.30, 0.45),   # output + panel board (VBUS broken,
                                             # DAC + true-bypass relay + the TS jack)
    "motor_ctrl":      (0.55, 0.25, 0.25),   # motor controller PCB (CH32V307 +
                                             # 2x CAN transceiver + XH headers)
    "tee_pcb":         (0.10, 0.42, 0.18),   # trunk-and-drop bus tee PCBs
    "tee_cradle":      (0.32, 0.55, 0.42),   # PCTG drop-in PCB cradle (pcb_cradle, side hold-down)
    "trrs_adapter_pcb":    (0.18, 0.42, 0.24),   # the leg's TRRS<->XH adapter (bronner's board)
    "trrs_adapter_plug":   (0.15, 0.15, 0.17),   # the lead from the leg, plugged in
    "trrs_adapter_screw":  (0.55, 0.55, 0.58),   # M4 button, 2.5 hex -- the one lock
    "trrs_adapter_insert": (0.80, 0.60, 0.35),   # its brass heat-set insert
    "tee_screw":       (0.72, 0.74, 0.78),   # M4x10 button, BESIDE the tee board
    "tee_insert":      (0.72, 0.60, 0.30),
    "board_screw":     (0.72, 0.74, 0.78),   # M4x10 button THROUGH our boards' mounting ears
    "board_insert":    (0.72, 0.60, 0.30),   # its heat-set brass, in the cradle boss   # M4 heat-set brass, in the cradle boss
    "optical_pcb":     (0.12, 0.30, 0.55),   # per-string optical strip (blue solder mask,
                                             # so it reads apart from the green audio PCBs)
    # ⚠ MATCHED TO THE LOOSE-WIRE COLOURS BELOW, not picked fresh: a USB run is a USB
    # run whether it is drawn as a wire or as a modelled cable, and the old single entry
    # was (0.15,0.15,0.17) -- near-black, which this project reserves for TPU.
    "optical_cable_usb": (0.55, 0.25, 0.75),  # violet, as wire_usb - USB-C plug + lead to the Pi
    "optical_cable_pwr": (0.85, 0.12, 0.10),  # red, as wire_pwr_hot - 24 V in at J2
    "optical_insert":  (0.72, 0.60, 0.30),   # M4 heat-set brass, board grips
    "optical_screw":   (0.72, 0.74, 0.78),   # M4x12 button, down into it
    "optical_cover":   (0.18, 0.18, 0.20),   # slotted lid over the sensor row -- print it
                                             # DARK: it is the one surface facing the
                                             # detectors, so a light one would bounce IR
    "top_plate":       (0.88, 0.91, 0.94),   # transparent-PCTG deck base + fret lines
    "top_plate_color": (0.30, 0.33, 0.38),   # colour-PCTG deck layer (skin contact)
    "chassis_light":   (0.88, 0.91, 0.94),   # light window -- the deck panels' white
    "ui_pcb":          (0.05, 0.35, 0.18),   # the UI board, as fabbed
    "ui_display":      (0.16, 0.16, 0.18),   # the module's metal bezel -- the part the
                                             # deck's ledge bears on and covers
    "ui_screen":       (0.64, 0.66, 0.68),   # the 128 x 64 of LIT AREA. Light enough to
                                             # read against the bezel, so the render
                                             # answers "how much of the screen does the
                                             # deck cover" by looking -- but GREY, not
                                             # white: at 0.92 it glared next to the
                                             # near-black module around it
    "ui_clamp":        (0.36, 0.30, 0.42),   # the printed clamp plate under the board
    "ui_insert":       (0.72, 0.60, 0.38),   # brass heat-set
    "ui_screw":        (0.62, 0.64, 0.67),
    "ui_knob":         (0.15, 0.15, 0.17),   # the printed cap on the encoder
    "dc_jack":         (0.62, 0.64, 0.67),
    "usbc_jack":       (0.62, 0.64, 0.67),
    # wire harness: HUE = gauge bucket, SHADE = the specific wire in the bucket
    #   green = 28 AWG shielded audio | amber = 28 AWG logic | violet = USB-2
    # CAN + power trunk = its 4 colour-coded conductors (user override):
    #   black = gnd | red = 24 V | yellow = CAN-H | green = CAN-L
    "wire_pwr_hot":    (0.85, 0.12, 0.10),   # red         - CAN 24 V
    "wire_pwr_gnd":    (0.05, 0.05, 0.05),   # black       - CAN ground/return
    "wire_canh":       (0.95, 0.85, 0.10),   # yellow      - bus A CAN-H
    "wire_canl":       (0.13, 0.72, 0.20),   # green       - bus A CAN-L
    "wire_canb_gnd":   (0.05, 0.05, 0.05),   # black       - bus B ground (levers)
    "wire_canb_v5":    (0.85, 0.12, 0.10),   # red         - bus B +5 V  (levers)
    "wire_canb_h":     (0.95, 0.85, 0.10),   # yellow      - bus B CAN-H (levers)
    "wire_canb_l":     (0.13, 0.72, 0.20),   # green       - bus B CAN-L (levers)
    "wire_canb_coil":  (0.45, 0.45, 0.48),   # grey        - the slack, drawn as a bundle
    "wire_canbh":      (0.95, 0.85, 0.10),   # yellow      - bus B CAN-H
    "wire_canbl":      (0.13, 0.72, 0.20),   # green       - bus B CAN-L
    "wire_canjmph":    (0.95, 0.85, 0.10),   # yellow      - jumper CAN-H
    "wire_canjmpl":    (0.13, 0.72, 0.20),   # green       - jumper CAN-L
    "motor_pigtail":   (0.45, 0.45, 0.48),   # grey        - SERVO42D's own 6-pin
                                             #   XH pigtail (factory jacket)
    "wire_knee_drop":  (0.45, 0.45, 0.48),   # grey        - LKL drop stub
    "wire_pickup":     (0.55, 0.85, 0.55),   # lightest green - the magnetic pickup's
                                             #   shielded lead, coil underside -> the
                                             #   output panel's J8 screw terminals
    "wire_link":       (0.95, 0.72, 0.22),   # light amber - Teensy <-> Pi
    "wire_tdm":        (0.80, 0.46, 0.10),   # deep amber  - CS stack -> Pi
    # THE UI RIBBON, fourteen conductors. Grey is what 1.27 flat cable is; conductor 1
    # is its red stripe, which is the only marking an IDC cable carries and the only
    # thing that tells you which way round the plug goes.
    # named per PANEL, not per index (_color_for strips digits, not words), because
    # "mid" and "key" are what every other file calls these two boards
    "fret_pcb_mid":    (0.05, 0.35, 0.15),   # PCB green
    "fret_pcb_key":    (0.05, 0.35, 0.15),
    "fret_led_mid":    (0.95, 0.95, 0.88),   # RGBW, lit
    "fret_led_key":    (0.95, 0.95, 0.88),
    "foot_pcb_a":      (0.05, 0.35, 0.15),
    "foot_pcb_b":      (0.05, 0.35, 0.15),
    "foot_led_a":      (0.95, 0.95, 0.88),
    "foot_led_b":      (0.95, 0.95, 0.88),
    "wire_ui":         (0.55, 0.56, 0.58),
    "wire_usb":        (0.55, 0.25, 0.75),   # violet      - shielded USB-2 -> Pi
}
_DEFAULT_COLOR = (0.80, 0.80, 0.80)
_TPU_BLACK = (0.03, 0.03, 0.03)                  # ALL TPU parts render black (user rule)
# every part whose output path is tpu/... -> black, regardless of instance prefix/suffix
_TPU_BASES = tuple(sorted((k for k, v in PARTS.items() if v[1].startswith("tpu/")), key=len, reverse=True))


_COLORS.update({
    "pogo_wire_%s" % n.lower(): c for n, c in zip(
        _EH.PH_PINOUT, ((0.05, 0.05, 0.05), (0.85, 0.12, 0.10),
                        (0.95, 0.85, 0.10), (0.13, 0.72, 0.20)))})


def _color_for(name):
    # STRIP EVERY TRAILING INDEX GROUP, not just the last one -- the same lesson
    # tools.check_overlaps.base() records, and this resolver had not learned it. A part
    # numbered twice (`wire_canb_gnd_0_0`: net, segment, half) kept one index after a
    # single strip, matched nothing in _COLORS, and came out the default white. The
    # overlap gate had already been bitten by exactly this and fixed; colours had not.
    base = re.sub(r"(_\d+)+$", "", name)
    if base in _TPU_BASES or any(base.endswith(k) for k in _TPU_BASES):
        return cq.Color(*_TPU_BLACK)             # TPU is always black
    if base in _COLORS:
        return cq.Color(*_COLORS[base])
    # the pogo boards are named per joint (pogo_male_board_top / _bottom)
    _pg = re.match(r"(pogo_[a-z]+_[a-z]+)_(?:top|bottom)$", base)
    if _pg and _pg.group(1) in _COLORS:
        return cq.Color(*_COLORS[_pg.group(1)])
    # The three foot pedals are the knee-lever core VERBATIM, only posed and named
    # pedal{i}_<knee part>. Strip that station prefix and inherit the sibling's
    # colour rather than adding 66 near-duplicate entries — otherwise every pedal
    # part falls through to default grey and the whole assembly reads as one blank
    # mass (user: "the pedals are all white rather than using the same colour
    # scheme as the levers").
    # The axle group is named kl_* on the knee lever and pedal{i}_* here, so try the
    # kl_ sibling too: pedal0_pcb -> kl_pcb, pedal0_bearing -> kl_bearing. The feel
    # lanes need no prefix (main_cart_base is already unqualified).
    # Every lever carries the SAME sensor stack, named kl_* / kv_* / pedal{i}_*. Strip
    # whichever station prefix this is and inherit the kl_ sibling's colour rather than
    # triplicating the table. kl_ FIRST, then the bare name: bare-name-first collided,
    # because the sensor board's "buck" is not the project's other "buck".
    # The four non-LKL LEVER STATIONS prefix the same way (lkr_knee_housing,
    # vkl_kv_lever, ...), so they ride this rule too — the alternative was six
    # copies of the same 29 entries, and any station left out would have gone grey
    # exactly the way the pedals did.
    # PEEL EVERY PREFIX, not one (user, 2026-09-25: "the cartridges/pistons are yellow
    # for the LKL but white for LKV, we should color them consistently"). A vertical
    # lever's cartridge is DOUBLY prefixed -- vkl_kv_main_cart_piston, station then
    # design -- so a single strip reached kv_main_cart_piston, which is in no table, and
    # the whole feel stack came out default white beside LKL's yellow one. Peeling until
    # something matches costs nothing and is what "the same part at another station"
    # actually means.
    inner = base
    for _ in range(3):
        _st = re.match(r"(?:pedal\d+|lkr|vkl|rkl|rkr|kv|kl)_(.+)$", inner)
        if not _st:
            break
        inner = _st.group(1)
        for k in (f"kl_{inner}", inner, f"kv_{inner}"):
            if k in _COLORS:
                return cq.Color(*_COLORS[k])
    if base == "pedal_lever":
        return cq.Color(*_COLORS["knee_lever"])   # it IS the knee lever, posed
    return cq.Color(*_DEFAULT_COLOR)


def _export_assembly(publish=True, gate=True, gate_full=True):
    build_n = _bump_build_counter()
    comps = collect_components()
    asm = cq.Assembly(name="public_steel_guitar")
    for name, wp in comps:
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
    if publish:
        _publish_web_preview(comps, build_n)
    # LAST: the gate spawns a worker pool, so run it once the STEP is safely on
    # disk and the viewer is refreshed — a gate hiccup can never cost the build.
    if not gate:
        return 0
    # both gates always run, so one RED doesn't hide the other's result
    return (_report_overlaps(comps, full=gate_full) | _report_sweep(comps)
            | _report_travel(comps) | _report_dead())


# The overlap gate's ACCEPTED baseline: the count of REAL defects tracked
# elsewhere. The build fails ABOVE it, so a NEW overlap still stops it, and it must
# always equal the count you can NAME -- a baseline kept above the real number is
# just a licence for the next fault to arrive unnoticed.
# NOTHING IS ACCEPTED ANY MORE. Build #657 (branner's prism-first bank rebuild, which
# rerouted the -Y harness corridor) came back with ZERO unintended pairs, so the last
# named defect -- chassis <-> wire_pwr_hot_10, ~0.6 mm^3, a wire clipping a solid,
# carried since August -- is gone. Was 2, then 1, now 0: every unintended pair from
# here is a regression and stops the build, which is what the rule above is for.
OVERLAP_BASELINE = 0


def _report_overlaps(comps, full=False) -> int:
    """Run the overlap gate on the model we JUST built, and return 1 on regression.

    This is the whole point of folding the gate into the build: the scan is seconds
    on a warm pair cache, but ``tools.check_overlaps`` run standalone spends MINUTES
    rebuilding the model first. Reusing ``comps`` makes a full-tree gate essentially
    free, so the lead never has to choose between gating and building.
    """
    try:
        from tools.check_overlaps import gate
        n = gate([(name, wp.val()) for name, wp in comps], full=full)
    except Exception as e:               # noqa: BLE001 — a gate crash must not eat the geometry
        print(f"overlap gate: SKIPPED ({type(e).__name__}: {e})", flush=True)
        return 0
    if n > OVERLAP_BASELINE:
        print(f"OVERLAP GATE: RED — {n} unintended pairs "
              f"({n - OVERLAP_BASELINE} NEW above the accepted {OVERLAP_BASELINE})",
              flush=True)
        return 1
    print(f"OVERLAP GATE: green — {n} unintended pair(s), "
          f"accepted baseline {OVERLAP_BASELINE}", flush=True)
    return 0


def _report_sweep(comps) -> int:
    """Swept-envelope gate on the model we JUST built (see _report_overlaps for why
    reusing ``comps`` matters). This catches the class ``check_overlaps`` is
    STRUCTURALLY blind to: a part that clears everything at rest and fouls once it
    turns. Baseline is 0 — unlike the overlap gate there is no inherited debt."""
    try:
        from tools.check_sweep import gate
        n = gate([(name, wp.val()) for name, wp in comps])
    except Exception as e:               # noqa: BLE001 — never let a gate eat the geometry
        print(f"sweep gate: SKIPPED ({type(e).__name__}: {e})", flush=True)
        return 0
    print(f"SWEEP GATE: {'green' if n == 0 else f'RED — {n} swept collision(s)'}", flush=True)
    return 1 if n else 0


def _report_travel(comps) -> int:
    """The pickup height plate's TRAVEL, on the model we just built. The same blindness as
    the sweep gate, for a part that slides instead of turning: the overlap gate sees the
    plate at its lowest and nothing above. Baseline is 0. See tools/check_pickup_travel."""
    try:
        from tools.check_pickup_travel import gate
        n = gate([(name, wp.val()) for name, wp in comps], quiet=True)
    except Exception as e:               # noqa: BLE001 -- never let a gate eat the geometry
        print(f"travel gate: SKIPPED ({type(e).__name__}: {e})", flush=True)
        return 0
    print(f"TRAVEL GATE: {'green' if n == 0 else f'RED -- {n} pair(s) meet in the pickup plate travel'}",
          flush=True)
    return 1 if n else 0


def _report_dead() -> int:
    """Source drift, not geometry: module-level definitions nothing in the repo names
    any more. REPORT ONLY -- it never fails the build. Retired parts leave their
    builders behind (the electronics tray left nine), and the cost of that is a reader
    believing dead code is live, which is worth a line of output and not worth blocking
    an agent's merge over. See tools/check_dead.py for what counts as a use."""
    try:
        from tools.check_dead import scan, KNOWN
        dead = [d for d in scan() if d[2] not in KNOWN]
    except Exception as e:               # noqa: BLE001 -- never let a report eat a build
        print(f"dead-code report: SKIPPED ({type(e).__name__}: {e})", flush=True)
        return 0
    if dead:
        print(f"dead code: {len(dead)} unreferenced definition(s) -- "
              f"py -3.12 -m tools.check_dead", flush=True)
        for path, lineno, name in dead:
            print(f"    {path}:{lineno}  {name}()", flush=True)
    return 0


def _publish_web_preview(comps, build_n):
    """Refresh the web-preview GLB from the just-built components (reused — no
    second geometry pass) and force-push it to the gh-pages branch. STRICTLY
    NON-FATAL: a publish failure (offline, not on main, auth) must never fail an
    otherwise-good geometry build. The push itself is a no-op off the main branch
    (so agent worktrees don't publish) — see tools/publish_preview.py."""
    try:
        from tools.export_glb import build_glb
        from tools.export_rig import build_rig
        from tools.publish_preview import push_gh_pages
        build_glb(comps, build_n=build_n)   # full instrument + the #build label
        build_rig(build_n)                  # animation manifest (pivots + copedent)
        push_gh_pages(build_n)
    except Exception as e:               # noqa: BLE001 — never let publishing break a build
        print(f"web preview: publish skipped ({type(e).__name__}: {e})", flush=True)


def main() -> None:
    # Part notes carry Unicode (→, Ø, …); a cp1252 Windows console/pipe raises
    # UnicodeEncodeError mid-export and aborts the build. Force UTF-8 so a print
    # can never kill a good geometry build (replace = never crash on any glyph).
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    p = argparse.ArgumentParser(prog="src.build")
    p.add_argument("--part", help="Build only this printed part (skips assembly).")
    p.add_argument("--list", action="store_true", help="List part names and exit.")
    p.add_argument("--geom", action="store_true", help="Print belt geometry report and exit.")
    p.add_argument("--no-gate", action="store_true",
                   help="Skip the overlap gate (normally ~13 s on the built model).")
    # Belts are gated BY DEFAULT on the lead's build. It is the one authoritative
    # whole-tree check, and skipping belts is how far-row belts clipping near-row
    # pulley flanges (up to 9.8 mm^3) went out under a green gate. It costs ~225 s of
    # pairwise scan against ~15 s -- the price of the check meaning what it says.
    # Agents iterate with `view --gate`, which is where speed belongs.
    p.add_argument("--gate-fast", action="store_true",
                   help="Skip belts in the gate (~15 s scan vs ~225 s). Inner-loop only.")
    p.add_argument("--gate-full", action="store_true",
                   help="(default now; accepted for compatibility)")
    args = p.parse_args()

    if args.geom:
        print(geometry_report())
        return
    if args.list:
        print("assembly")
        for name in PARTS:
            print(name)
        return
    gate, gate_full = not args.no_gate, not args.gate_fast
    if args.part:
        if args.part == "assembly":
            sys.exit(_export_assembly(gate=gate, gate_full=gate_full))
        if args.part not in PARTS:
            print(f"unknown part: {args.part!r}. Use --list.", file=sys.stderr)
            sys.exit(2)
        _export(args.part)
        return

    for name in PARTS:
        _export(name)
    # ⚠ VOLUMES FIRST. report_build_regressions() ends by CLEARING the record list, so
    # writing the volumes after it wrote an empty file (found by the file being 100
    # bytes, lead 2026-09-30). Order matters here and nothing else would have said so.
    _n = write_part_volumes()           # what the plastic costs, for tools/cost.py
    if _n:
        print(f"wrote tools/part_volumes.json  ({_n} parts)")
    report_build_regressions()          # ~free: flags any part whose face count grew vs baseline
    sys.exit(_export_assembly(gate=gate, gate_full=gate_full))


if __name__ == "__main__":
    main()
