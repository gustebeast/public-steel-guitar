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
    from tools.build_profile import record_part, report_build_regressions
except Exception:                       # a profiling hook must NEVER break a build
    def record_part(*a, **k): pass
    def report_build_regressions(): return 0

from . import dimensions as D
from .helpers import heal, cyl, cyl_y
from . import components as C
from . import chassis as CH
from .bridge_endplate import bridge_endplate
from . import bridge_endplate as BE
from .belt_clamp import belt_clamp
from .screw_collar import screw_collar
from .chassis import segments as chassis_segments
from . import nut_block as NB
from . import tension_fork as TF
from . import pickup_mount as PM
from . import legs as LG
from . import latch as LT

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
    return FP.cut_backstop_threads(heal(FP.fuse_into_bar(_PB(attr), *span)), *span)


PARTS = {
    "bridge_endplate": (partial(heal, bridge_endplate), "petg-gf/bridge_endplate.step", "PETG-GF — fused bridge end (screw support + bearing support + axle comb + box closure)"),
    "keyhead_endplate": (lambda: heal(__import__("src.keyhead_endplate", fromlist=["e"]).keyhead_endplate), "petg-gf/keyhead_endplate.step", "PETG-GF — merged keyhead (-X) endplate + nut block (25 mm, one piece): closes the box, caps the deck grooves, gauged break-edge + 2-row clamps; drops in last, held by 1 screw"),
    "belt_clamp":      (partial(heal, belt_clamp),    "pctg/belt_clamp.step",      "PCTG — GT2 belt splice clamp (print 2 per splice ×10)"),
    "knee_housing":    (lambda: __import__("src.knee_lever", fromlist=["e"]).knee_housing, "petg-gf/knee_housing.step", "PETG-GF — knee-lever (LKL) housing: ONE parametric prism derived from the lever/cartridge/body extents, minus the house-pockets, backstop threads + lever room, plus FOUR fused octagon mount tenons on the top face (one per chassis rib crossing; the +X-most survives only as a stub over each cheek) and the MT6701 board CRADLE on the +Y face (grooves + plinth + floor; the board drops in from +Z with the lever OFF the instrument and the chassis underside becomes its lid — no retaining screw. Ø14 driver bore reserved for the magnet cap, plus a relief channel through the cheek and the -X web for the board's side-entry CAN connector and its plug). Retention is all on -X: the +X web stops at the plinth top so NOTHING stands +X of the prism face. Depth lock deferred"),
    "knee_lever":      (lambda: __import__("src.knee_lever", fromlist=["e"]).knee_lever,   "pctg/knee_lever.step",   "PCTG — knee-lever (LKL) arm + knee paddle (takes knee strikes: toughness over stiffness); the +Y axle journal + magnet stub print INTEGRAL (stand off the lying -Y bed face)"),
    "kl_axle": (lambda: __import__("src.knee_lever", fromlist=["e"]).kl_axle, "pctg/kl_axle.step", "PCTG — knee-lever AXLE ×1: ONE full-length part fitted LAST, slid +Y→−Y through bearing/lever/bearing (the old integral stub could never enter its bearing). Ø5 round journals, D-FLAT key through the hub, flange seating on the housing contact rib (= the air-gap datum), threaded magnet pocket. Prints STANDING, POCKET-DOWN, with a brim"),
    "kl_magnet_cap": (lambda: __import__("src.knee_lever", fromlist=["e"]).kl_magnet_cap, "pctg/kl_magnet_cap.step", "PCTG — magnet CAP ×1: female-threaded HEX nut (9.35 across flats, for a 3/8-inch driver) screwing over the axle's pocket collar to clamp the Ø6 diametric disc; centre stays open so nothing intrudes on the air gap. Fit it BEFORE the sensor board. Prints APERTURE-DOWN"),
    "kv_housing":      (lambda: __import__("src.knee_lever_vert", fromlist=["e"]).kv_housing, "petg-gf/kv_housing.step", "PETG-GF — VERTICAL knee-lever (LKV) housing: same prism derivation as LKL but with the feel block TRANSLATED above the axle (not mirrored — the pocket gable stays up for printability), so the axle sits 19.2 lower and the arm has room to swing UP. Y is asymmetric (-16.10..+13.90): the -Y wall is 2.2 wider to fit TWO octagon tenons at the 23mm rib pitch, while the +Y sensor face is untouched. Tenons slide along local X (= the guitar's Y once posed). Carries the SAME sensor cradle as LKL (knee_lever._cradle, parameterised by the housing Z extents) - the board is just taller here, 31.2 vs 19. Rest stop deferred"),
    "kv_lever":        (lambda: __import__("src.knee_lever_vert", fromlist=["e"]).kv_lever, "pctg/kv_lever.step", "PCTG — VERTICAL knee-lever (LKV) arm: an L. Hub on the axle, a LEG rising +Z carrying the return lobe at 13.2 (sized so the 20° throw gives the SAME 4.51 spring stroke as LKL's 30°), and a 50mm ARM running +X that the knee lifts — 17.1 of paddle rise"),
    "cart_base": (lambda: __import__("src.knee_lever", fromlist=["e"]).cart_base, "pctg/cart_base.step", "PCTG — spring-cartridge (inverted-U, open -Z; shared: print 2, for main + half-stop)"),
    "cart_piston": (lambda: __import__("src.knee_lever", fromlist=["e"]).cart_piston, "pctg/cart_piston.step", "PCTG — spring-cartridge piston, flat follower tongue (shared: print 2)"),
    "guide_post": (lambda: __import__("src.knee_lever", fromlist=["e"]).guide_post, "pctg/guide_post.step", "PCTG — coil-back guide post, screw pushes it (shared: print 2)"),
    "cart_backstop": (lambda: __import__("src.knee_lever", fromlist=["e"]).cart_backstop, "pctg/cart_backstop.step", "PCTG — hollow X-position back-stop screw: threads the housing boss, tension screw runs through the Ø5.5 bore (shared: print 2)"),
    # NOT healed: cadkit.threads is explicit that heal()'s unify chokes on a threaded
    # solid. Both of these carry a pilot thread and both export fine unhealed.
    "screw_pulley":    (lambda: C.screw_pulley(),        "pctg/screw_pulley.step",  "PCTG at a 0.2 NOZZLE — flanged 14T GT2 pulley, 45° top flange ×10. Bore is a PILOT THREAD the Tr5x1 rod swages to size (that is the torque path); one M2 grub in the hub above the belt is only a secondary lock against walking. Fine teeth AND a 0.3 mm thread groove both need the small nozzle and unfilled material"),
    "screw_collar":    (lambda: screw_collar,            "pctg/screw_collar.step", "PCTG at a 0.2 NOZZLE — leadscrew retaining collar ×10: the screw's axial anchor, driving both MR85 inner rings up against the rail ledge. Bore prints as a PILOT THREAD at the true 1 mm pitch and the Tr5×1 rod swages the last 0.1 going in — a Tr screw has blunt flanks and no cutting edges, so it forms rather than cuts and needs a helix to track; a plain bore gave it nothing, and a friction clamp would creep out under 147 N. The 0.3 mm groove is why this is a 0.2-nozzle, unfilled part. TURNED, not prismatic: it rotates with the screw, so Ø8.8 is the SWEPT envelope and the 8 mm wrench flats are milled into it. Prints bore-up, flat, no supports"),
    "motor_pulley":    (lambda: heal(C.motor_pulley()),  "pctg/motor_pulley.step",  "PCTG — flanged 14T GT2 pulley, 45° outer flange — ×10"),
    "tension_fork":    (lambda: TF.tension_forks,    "pctg/tension_fork.step",    "PCTG — belt-tension lock forks, graded 3.0–6.0 set (4 of the fitting size per motor; positive stop in the slot, no friction reliance)"),
    # pickup carrier: the deck pickup-piece (a top_plate panel) holds the pickup on a
    # height plate lifted by 3 M4×20 button-head leadscrew jacks; a -Y M4 cup-tip grub
    # locks the pickup +Y against the plate's +Y wall. All hardware is stocked M4, all +Z.
    "pickup_zplate":   (lambda: heal(__import__("src.top_plate", fromlist=["e"]).pickup_zplate), "petg-gf/pickup_zplate.step", "PETG-GF — pickup height plate (green pickup area + nubs; 3 M4×20 button-head leadscrew jacks lift/tilt it via heat-set nuts on top, pickup rests on it and slides in X for tone; +Y retention wall + -Y cup-tip grub lock the pickup to the plate; GF keeps it flat on the point loads)"),
    # (the whole round-tube leg family — sockets, segments, thread couplers and
    #  washers — was DELETED 2026-08-01: 214 lines + 26 constants of unreachable
    #  code, kept through the square-leg swap and then never removed.
    # redesign — generators remain in legs.py until the refinement pass
    # deletes them)
    "leg_sleeve":      (lambda: heal(LG.leg_sleeve()),  "petg-gf/leg_sleeve.step",  "PETG-GF — leg slider sleeve ×4 (44×40×200, +Y face thinned for the cover: truncated flush spigot up top — the cover tongue completes the joint — full-length dropped octagon GROOVE, two W5 cover-rail slots, EMBEDDED gib bay + ONE M4 grub flush in the +X face; prints LYING on the thinned +Y face)"),
    "leg_sleeve_cover": (lambda: heal(LG.leg_sleeve_cover()), "petg-gf/leg_sleeve_cover.step", "PETG-GF — sleeve COVER ×4: 44-wide × 4 plate sliding down two W5 octagon rails to close the sleeve's open C-channel into a box tube (anti-bow at long extension) + hide the slack coil; segment-mortise TONGUE up top + blind rail ends = captive, zero fasteners. Prints lying on the outer face"),
    "leg_pinch_gib":   (lambda: heal(LG.leg_pinch_gib()), "tpu/leg_pinch_gib.step", "TPU — pinch GIB PAD ×4: grippy pad in the sleeve's +X wall pocket; ONE central M4 grub presses it onto the shaft octagon's waist wall (TPU = preload spring + µ~0.7 friction; ~500-650 N hold vs ~350 N worst leg load). Prints flat"),
    "leg_shaft":       (lambda: heal(LG.leg_shaft()),   "petg-gf/leg_shaft.step",   "PETG-GF — -Y shaft ×2: W28 dropped-octagon tenon (197, rides under the sleeve cover) + SOLID 35.6-sq block (91, equal-height rule; 4.2 inset on ALL FOUR sides — symmetric reveal, +Y face = the stem plane so the bed is one plane) with the shared TPU foot's dovetail mortise. 288 long: print LYING on the stem face, laid diagonal in plan"),
    "leg_shaft_trrs":  (lambda: heal(LG.leg_shaft_trrs()), "petg-gf/leg_shaft_trrs.step", "PETG-GF — +Y WIRED shaft ×1 (245, lying print): W28 octagon tenon + 44-sq block with the bar-joint octagon socket + the 10-03404 jack seated mouth-down on the (-5,+13) TRRS axis (loads from the open tenon top; boss = withdrawal stop, pressed jack_seat_ring = insertion stop)"),
    "leg_foot":        (lambda: heal(LG.leg_foot()),    "tpu/leg_foot.step",    "TPU — SHARED dovetail foot ×4 (user: one look): 44-sq pad + tenon into the underside mortise of the -Y leg blocks AND the pedal bar; the wired bar one covers the plug-threading access"),
    # (round leg_socket_trrs export retired — see leg_socket_sq_trrs)
    "leg_plug_retainer": (lambda: heal(LG.leg_plug_retainer()), "pctg/leg_plug_retainer.step", "PCTG — press sleeve ×2: under the molded TRRS plug handles (the leg extension cable's at the head + the bar cradle CA-354S's in the tower) — insertion backstop; the seat lip takes withdrawal"),
    # ── SQUARE-LEG redesign, STAGE 1 (generators + eval prints; the round
    # legs still populate the assembly until the stack swap lands) ──
    "leg_seg_body":    (lambda: heal(LG.leg_seg_body()), "petg-gf/leg_seg_body.step", "PETG-GF — square 44 segment BODY ×6 (redesign, plain legs): prints LYING on a face (layer lines along the leg — kick loads bulk GF); stacks on the cadkit octagon section joint, ONE M4 per joint for extraction only — no threads, no glue"),
    "leg_seg_body_ch": (lambda: heal(LG.leg_seg_body_ch()), "petg-gf/leg_seg_body_ch.step", "PETG-GF — square segment BODY, CHANNELED ×2 (redesign, the wired -X/+Y leg only): + lidded face cable channel + core dive holes"),
    # ("leg_coupler_m" export retired — ROUND 3: threadless, gasketless square legs)
    # ("leg_coupler_f" export retired — ROUND 3: threadless, gasketless square legs)
    # ("leg_lid" export retired — the wired cable runs up the column CENTER
    # through the flush-octagon joints' Ø7 bores; no face channel to cover)
    # ("leg_washer_sq" export retired — ROUND 3: threadless, gasketless square legs)
    "leg_body_stub":   (lambda: heal(LG.leg_body_stub()), "petg-gf/leg_body_stub.step", "PETG-GF — BODY STUB ×2 (bridge/+Y + keyhead/-Y; prints LYING ON ITS +Y FACE - Y-INSTALL round: layer lines in x-z so both leg-bending directions load within layers; the ridges print as vertical fins, the house gable points up): the 44-sq semi-permanent corner piece SLIDES IN ALONG Y - two FULL-LENGTH Y-running octagon crossing ridges (roof up) at the THIRDS of the 34 side-panel overlap (station +0.667/-10.667, hosted continuously by the WIDE CORNER RIB) + the 44-long simple 5×8 TONGUE at -17 into the endplate's groove (even 5/2.5+2.5 material split of the 10 wall; blind groove end = the flush stop); ONE M4×35 down the rail web into the inboard ridge = the Y-retention shear pin + ONE M4×10 along x through the endplate's end face cross-pinning the tongue (double shear); below, the leg↔bar socket verbatim (passive octagon mortise now the quick-release ledge is gone). Hangs 48 below the body = the disassembled z cost"),
    "leg_body_stub_jk": (lambda: heal(LG.leg_body_stub_jk()), "petg-gf/leg_body_stub_jk.step", "PETG-GF — body stub ×1 (the +X/-Y jack corner): the mirror SKU - end-wall tongue on local +x (this corner faces its endplate the other way); otherwise identical"),
    "leg_body_stub_trrs": (lambda: heal(LG.leg_body_stub_trrs()), "petg-gf/leg_body_stub_trrs.step", "PETG-GF — body stub ×1 (the -X/+Y WIRED corner; end-wall tongue local +x): NOTHING above the top face (user killed the jack fin) - the mouth-seat boss, barrel way and Ø9.7 jack way open through the FLAT top; the naked 10-03404 DROPS IN through the wide rib's Ø10.5 well AFTER the slide, seats on the boss, and an M2 set screw from the stub's inboard-y face (reachable under the assembled body) clamps its barrel; the pigtail rides the over-rib raceway (y 50.5) east to the bus-B tee"),
    "leg_head":        (lambda: heal(LG.leg_head()), "pctg/leg_head.step", "PCTG — LEG HEAD ×4 (all-octagon; prints LYING on the +Y bed face): 44-sq, flush octagon spigot into the stub socket, octagon section socket below, captive TRRS plug seat on the (+5,+13) axis (one SKU for all legs). NO Z RETENTION — the seatbelt quick-release (bolt + button) is gone; the spigot is a plain sliding fit"),
    "latch_slider":    (lambda: heal(LT.slider()), "pctg/latch_slider.step", "PCTG — LATCH SLIDER ×6 (4 leg—body + 2 bar—leg; ONE SKU): the whole quick-release. Push-to-connect (45° hook lead cams it in against the coil, springs out at depth); press the pad and pull to release, one-handed. Steel coil seats in its blind bore. Prints flat on its back face — the hook lead and the pad both face up, nothing to support"),
    "latch_cover":     (lambda: heal(LT.cover()), "pctg/latch_cover.step", "PCTG — LATCH COVER ×6 (ONE SKU): closes the slider load window; its aperture lip is the slider outward stop AND its Z lock. Slides DOWN a 45° dovetail onto a hard stop and can only leave upward, which the mating half blocks once assembled — captive, zero fasteners. Prints flat"),
    # ("leg_washer" export retired — ROUND 3: threadless, gasketless square legs)
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
    "leg_shaft_short": (lambda: heal(LG.leg_shaft_short()), "petg-gf/leg_shaft_short.step", "PETG-GF — SHORT +Y shaft ×1 (the wired one prints from leg_shaft_trrs): W28 dropped-octagon tenon ending in the 35.6-sq terminal block (4.2 inset on all four sides, symmetric; +Y face = the stem plane) whose octagon socket + point-side ledge take the bar tower's shaved tenon"),
    "jack_seat_ring":  (lambda: heal(LG.jack_seat_ring()), "pctg/jack_seat_ring.step", "PCTG — press ring ×1: down the wired short shaft's way onto the leg extension cable's molded jack barrel (insertion backstop; the integral boss takes withdrawal)"),
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
_fused_segs = set()
for (_cnm, _cr), (_ctx, _cty, _ctd) in zip(_WR_FUSE.tee_cradles(), _WR_FUSE.tee_stations()):
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
    for _rx in CH._RIB_X:
        if _seg_edges[_csi + 1] < _rx < _seg_edges[_csi]:
            _seg = _seg.cut(_KL_FUSE.rib_mortise(_rx))
    chassis_segments[_csi] = _seg
for _i, _seg in enumerate(chassis_segments):     # chassis split into dovetailed segments
    PARTS[f"chassis_{_i}"] = (partial(heal, _seg), f"petg-gf/chassis_{_i}.step",
                              "PETG-GF — chassis segment (cadkit slide-down T joint per rail; NO glue "
                              "and NO seam fastener — the deck, endplates and finally the 4 leg screws "
                              "close the seam's Z axis. + tee cradles)")
# Print coupon for the cadkit octagon slide joint (the joint the knee levers key
# into the body with). test_*.step at the project root; also rendered off to the
# side in the assembly (see _joint_coupon_components) so it rebuilds every time.
PARTS["test_octagon_tenon"] = (
    lambda: heal(__import__("src.joint_coupon", fromlist=["e"]).tenon_coupon()),
    "test_octagon_tenon.step",
    "TEST COUPON — octagon (stop-sign) joint TENON on a base plate; prints -Z→+Z. "
    "Slide into test_octagon_mortise along X to check the fit")
PARTS["test_octagon_mortise"] = (
    lambda: heal(__import__("src.joint_coupon", fromlist=["e"]).mortise_coupon()),
    "test_octagon_mortise.step",
    "TEST COUPON — octagon joint MORTISE block (through-slot); prints -Z→+Z; the "
    "thin slot ceiling is the one-bead bridge the octagon roof is sized for")
# Section-joint coupon (the LEG stack's octagon at the real 28 mm width — legs.SEC_W)
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

# Belt-tensioner mechanism coupon — FOUR parts (anchor + slider + two lifter bars), real
# geometry, print orientation. Step 1 of the fixed-motor rework: prove the belt drops in
# free with the screw out, LOCKS on a positive tooth mesh when the M4 lifts the bars, and
# the tension winds in smoothly and holds without creep.
PARTS["test_belt_tensioner"] = (
    lambda: heal(__import__("src.belt_tensioner", fromlist=["e"]).tensioner_coupon()),
    "test_belt_tensioner.step",
    "TEST COUPON — belt-tension clamp, 4 parts (anchor, slider, 2 lifter bars). Drop a GT2 "
    "scrap through with the M4×30 out (bars low = free), seat the screw (bars ride the crest "
    "up → teeth mesh), and wind it to check the grip holds and tension sets fine without creep")


# Anchor ALL outputs to the project folder (never the cwd — see Archive/3D/CLAUDE.md)
OUT = pathlib.Path(__file__).resolve().parents[1]


def _export(name):
    builder, path, note = PARTS[name]
    dest = OUT / path
    dest.parent.mkdir(parents=True, exist_ok=True)   # material folder (petg-gf/pctg/tpu)
    t = time.perf_counter(); wp = builder(); build_s = time.perf_counter() - t
    t = time.perf_counter(); export_step(wp, str(dest)); export_s = time.perf_counter() - t
    record_part(name, build_s, export_s, wp.val() if hasattr(wp, "val") else wp)   # ~free profiling hook
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
# default). Strings 1, 2, 9 and 10 — both edge pairs; string N = index + 1
# (string 1 = index 0 = thinnest/highest, the far edge; string 10 = index 9 =
# thickest/lowest, nearest the player) — are kept PERMANENTLY at full
# down-travel, feet on the bottom stop: the maximum stretch/tension the
# mechanism can pull, so the travel extremes are always visible from either
# side. Everything riding the carriage (string nut, brass nut, string anchor)
# follows; the guide rod, screw and stops are fixed.
DEMO_POSE_DZ = {i: -D.CARRIAGE_TRAVEL for i in (0, 1, 8, 9)}


def _string_components(i):
    sy = D.string_y(i)
    mx, my, mz = D.motor_pos(i)
    cz = D.NUT_TOP_Z + DEMO_POSE_DZ.get(i, 0.0)      # the NUT's flange top
    out = []
    # vertical leadscrew
    out.append((f"leadscrew_{i}", C.screw().translate((D.SCREW_X, sy, D.SCREW_BOT_Z))))
    # THE NUT IS THE CARRIAGE. Nothing else moves: its +X ear anchors the string and
    # its -X ear rides the guide rod. Origin = the flange's top face.
    out.append((f"nut_{i}", C.nut().translate((D.SCREW_X, sy, cz))))
    # string BALL END, hanging UNDER the +X ear — tension pulls it up against the
    # ear's underside, and that IS the retention (a guitar bridge plate, exactly)
    out.append((f"string_nut_{i}", C.string_nut().translate(
        (D.STRING_ANCHOR_X, sy, cz - D.NUT_FLANGE_T - D.STRING_NUT_D / 2))))
    # guide rod: pressed into the endplate's slab above and CANTILEVERED down through
    # the -X ear. It reaches the ear's underside at full travel plus a lead-in; there
    # is no bottom socket, because the drive relief left nothing down there to bore.
    rod_top = BE.GUIDE_SOCKET_Z + BE.GUIDE_SOCKET_H
    rod_bot = D.NUT_TOP_Z - D.CARRIAGE_TRAVEL - D.NUT_FLANGE_T - 2.0
    out.append((f"guide_rod_{i}", C.guide_rod(rod_top - rod_bot).translate(
        (D.GUIDE_ROD_X, sy, rod_bot))))
    # screw drive pulley (odd ones raised one belt-plane), then the thrust stack:
    # TWO MR85s in TANDEM seated up against the rail's ledge, and under them the
    # printed collar that drives their inner rings up (see screw_collar.py)
    spz = D.screw_pulley_z(i)
    out.append((f"screw_pulley_{i}", C.screw_pulley().translate((D.SCREW_X, sy, spz))))
    for k in range(D.SUPPORT_BRG_N):
        bz = D.SUPPORT_BRG_BOT + (k + 0.5) * D.MR85_W
        out.append((f"screw_bearing_{i}_{k}", C.support_bearing().translate((D.SCREW_X, sy, bz))))
    out.append((f"screw_collar_{i}", screw_collar.translate((D.SCREW_X, sy, D.COLLAR_Z1))))
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
    # anchor = the ball end hanging under the nut's +X ear
    az = (D.NUT_TOP_Z + DEMO_POSE_DZ.get(i, 0.0)
          - D.NUT_FLANGE_T - D.STRING_NUT_D / 2)
    g = D.STRING_GAUGE[i]
    rad = g / 2.0                                     # actual string gauge
    # rise to the +X tangent point (cx+r, cz). NOT quite vertical any more: the ear
    # sits STRING_ANCHOR_X, a shade -X of the tangent line, so the dead run leans a
    # couple of degrees. Deliberate — see dimensions on why the string takes the +X
    # ear and SCREW_X therefore stays exactly where it is.
    p0 = cq.Vector(D.STRING_ANCHOR_X, sy, az)
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
    pts.append(cq.Vector(KE.ZHOLE_X, ny, CH.Z_BOT + 8.4))              # down the bore, stopping
    #                                    just above the corner stubs' end-wall TONGUE top
    #                                    (bed + 8.0): the two +Y-corner bores land on the
    #                                    keyhead stub's tongue
    out = None
    for a, b in zip(pts[:-1], pts[1:]):
        seg = _rod(a, b, rad)
        out = seg if out is None else out.union(seg)
    return out


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
    out.append(("optical_cables", OP.opt_cables()))
    # The two M4 grips that locate the board: heat-set insert seated in the endplate's
    # wrap plinth, button screw down through the board's clearance hole into it. Same
    # fastener family as the pickup height jacks, so no new BOM line.
    from . import bridge_endplate as _BE
    _ohh = 2.2                                        # M4 button head height
    # headed_screw draws head-top-at-0 with the shank running -Z, which is ALREADY the
    # orientation for a screw entering downward -- no flip. (The old optical M2 went up
    # from below and did need one; copying that was what put this one through the board.)
    _oscr = headed_screw(M4, 12.0, head_d=7.0, head_h=_ohh, socket_af=2.5)
    for _i, (_mx, _my) in enumerate(OP.mount_points()):
        out.append((f"optical_insert_{_i}",
                    seated_insert(M4, (_mx, _my, _BE.CARRIER_TOP), (0, 0, -1))))
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
    # PICKUP RETENTION (user): a -Y horizontal M4 cup-tip SET SCREW (existing BOM nut-block part;
    # cadkit screw dummy, hex socket) threads a heat-set insert and pushes the pickup +Y against the
    # +Y wall, locking it to the PLATE only. Threading it in/out meets any pickup in the ~5.5 mm
    # length window; shown here at the DEMO Alumitone (longest, so nearly backed out): tip at PK_YM.
    _ret_face_y = TP.PK_MAX_YM - TP.RET_BOSS_L                        # boss/insert mouth (-Y, at the room edge)
    _ret_grub = f_screw(M4).rotate((0, 0, 0), (1, 0, 0), 90)          # drive/hex end -Y, cup tip +Y
    out.append(("pickup_retention_screw",
                _ret_grub.translate((TP.RET_SCREW_X, TP.PK_YM - M4.screw_l, TP.RET_SCREW_Z))))  # tip at the pickup
    out.append(("pickup_retention_insert",
                seated_insert(M4, (TP.RET_SCREW_X, _ret_face_y, TP.RET_SCREW_Z), (0, 1, 0))))
    return out


LEG_HEIGHT = 655.0   # floor → body bottom (user reference). Fine-stage
                     # bands (E = engagement 50..192, travel 142): with
                     # EQUAL 103-tall wide bottoms (user: -Y block 91 =
                     # bar 19 + tower 24 + block 48) every tenon roots at
                     # floor+103, so BOTH sides share ONE band formula.
                     # FLUSH round: the head seat moved up to Z_BOT-48
                     # (the stub mouth) → H = 590+142k−E (k=1: 540..682).
                     # Drawn 655 = k=1, E=77, all four legs — same count
LEG_SEGMENTS = 2     # index stride / band count; the drawn chain places
                     # LEG_SEGMENTS−1 bodies per leg (k=1 at 655)

# The pedal bar and the pedals on it are both drawn in the bar's own frame
# (z0 = plate bottom = the shaft waist's lower shoulder) and lifted into the
# guitar by the same amount. Named once so the bar, the pedals and the viewer's
# animation rig (tools/export_rig.py, which needs the axle centre in guitar
# coordinates) can't drift apart.
PEDAL_LIFT_DZ = (CH.Z_BOT - LEG_HEIGHT) + LG.FOOT_H


def _leg_components():
    """FLUSH SQUARE-LEG stack (leg centres = CH.LEG_Y, 17 inboard of the
    rails so every outer face is flush with the body walls): BODY STUB
    (semi-permanent: octagon crossing ridges into the side walls + the
    end-wall tongue into the endplate, one M4 down the web + one M4
    along x through the end face; mouth at -48) -> leg head (the
    inserting half, bolt
    channel opening INBOARD; its female mouth at -90) -> segment chain
    (142 pitch) -> sleeve -> shaft -> TPU foot. The stub/head joint
    frames are authored FLIPPED 180 in legs.py, so the whole stack still
    places with the one per-side rotation."""
    from . import chassis as CH
    from . import wiring as WR
    from .pedal_bar import STUB_Z0 as PB_STUB_Z0
    from .helpers import box_at
    out = []
    seg_body, seg_body_ch = LG.leg_seg_body(), LG.leg_seg_body_ch()
    head, head_latch = LG.leg_head(), LG.leg_head(latch=True)
    stub_p, stub_jk = LG.leg_body_stub(), LG.leg_body_stub_jk()
    sleeve, cover = LG.leg_sleeve(), LG.leg_sleeve_cover()
    shaft, foot = LG.leg_shaft(), LG.leg_foot()
    ground = CH.Z_BOT - LEG_HEIGHT
    ZM = -LG.STUB_H                        # stub mouth / head seat (rel Z_BOT)
    k = 0
    for sx in CH.LEG_STATIONS_X:           # stations computed from the shared endplate model
        # EVERY leg is placed rot 180 (user): the octagon's groove side -- which is
        # also the print-bed face -- then points world -Y on BOTH rails, so all four
        # legs read the same way round. The -Y pair used to sit at rot 0, which put
        # their bed face and their apex on the opposite sides from the +Y pair.
        for ly, rot in ((CH.LEG_Y[0], 180), (CH.LEG_Y[1], 180)):   # flush centres
            wired = (sx, ly) == (CH.LEG_STATIONS_X[1], CH.LEG_Y[0])
            # The stub SKU is chosen by eps, the LOCAL tongue side, and rot 180 maps
            # local x to world -x -- so eps = -egx, where egx is the outboard x sign
            # the chassis cuts its grooves with. (At rot 0 it was eps = +egx, which
            # is why the two -Y corners swap SKU with this change.) Getting this
            # wrong points the end-wall tongue away from its endplate.
            egx = -1.0 if sum(CH.LEG_STATIONS_X) / 2 > sx else 1.0
            eps = -egx

            def R(wp, dz=0.0, dx=0.0, dy=0.0):
                return (wp.translate((dx, dy, dz))
                        .rotate((0, 0, 0), (0, 0, 1), rot)
                        .translate((sx, ly, CH.Z_BOT)))

            out.append((f"leg_body_stub_{k}",
                        R(LG.leg_body_stub_trrs() if wired
                          else (stub_jk if eps > 0 else stub_p), ZM)))
            out.append((f"leg_head_{k}", R(head_latch if wired else head, ZM)))
            # LEG-JOINT LATCH: slider + cover ride the HEAD (the leg is the piece
            # you pull off, so the button is on it). Drawn LATCHED. The bar-joint
            # pair, indices 4-5, travel with the bar — pedal_bar._latch_parts.
            if wired:                       # ONE joint pair while the latch is iterated
                out.append((f"latch_slider_{k}", R(LT.slider(), ZM)))
                out.append((f"latch_cover_{k}", R(LT.cover(), ZM)))
                out.append((f"latch_spring_{k}", R(LT.spring(), ZM)))
            # threadless chain: butt faces, integral plugs. Head bottom
            # face at ZM - 42 = -90; each body IS the 142 pitch.
            top = ZM - LG.HEAD_BODY_L
            # equal bottoms: identical silhouettes -> identical bands
            # both sides (H = 618 + 142k - E after the 228 sleeve)
            # (leg_lid retired: the wired cable runs up the column CENTER)
            nseg = LEG_SEGMENTS - 1
            for j in range(nseg):
                idx = LEG_SEGMENTS * k + j
                out.append((f"leg_seg_body_{idx}",
                            R(seg_body_ch if wired else seg_body,
                              top - LG.SEG_BODY_L)))
                top -= LG.SEG_BODY_L
            out.append((f"leg_sleeve_{k}", R(sleeve, top)))
            # cover rides the sleeve frame (rails at blind-end down-stop)
            out.append((f"leg_sleeve_cover_{k}", R(cover, top)))
            # gib pad drawn released (0.3 standoff) in the pocket near the mouth
            out.append((f"leg_pinch_gib_{k}",
                        R(LG.leg_pinch_gib(), top - 195.0)))
            # +Y legs end SHORT (the bar carries their last piece as stub
            # towers); only the -Y legs run to the floor with feet.
            # Key on the RAIL, not on rot: rot used to double as "which rail",
            # and now that every leg is placed 180 it no longer discriminates.
            # Left as rot == 180 this branch swallowed all four legs -- the -Y
            # pair lost their feet and got the short bar-tower shaft, i.e. they
            # stopped reaching the floor.
            if ly == CH.LEG_Y[0]:
                sh = LG.leg_shaft_trrs() if wired else LG.leg_shaft_short()
                # short-shaft seat plane on the bar tower — also the datum the
                # wired branch below hangs the second TRRS blind-mate off
                zst = ground + LG.FOOT_H + PB_STUB_Z0
                out.append((f"leg_shaft_{k}",
                            sh.rotate((0, 0, 0), (0, 0, 1), rot)
                            .translate((sx, ly, zst))))
                # (the bar tower carried the same bolt/button SKUs at
                # indices 4-5; gone with the quick-release)
            else:
                out.append((f"leg_shaft_{k}",
                            shaft.rotate((0, 0, 0), (0, 0, 1), rot)
                            .translate((sx, ly, ground + LG.FOOT_H))))
                out.append((f"leg_foot_{k}",
                            foot.rotate((0, 0, 0), (0, 0, 1), rot)
                            .translate((sx, ly, ground))))
            if wired:
                # leg<->body TRRS blind-mate on the (+5, +13) axis (local
                # -> global (sx-5, ly-13) on this 180-rotated stack — the
                # fat flare band of the flush octagon): 10-03404 in the
                # stub's way (mouth -9.3, same z as ever: ZM + 38.7),
                # captive plug in the head (tip +3.7), press retainer.
                out.append(("chassis_trrs_jack",
                            R(LG.chassis_trrs_jack(), 0.0, 5.0, LG.TRRS_DY)))
                out.append(("leg_column_plug_0",
                            R(LG.leg_column_plug(), 0.0, 5.0, LG.TRRS_DY)))
                # (no seat ring at the BODY joint any more — Y-INSTALL: a
                # ring can't ride through the fin's side-wall passage, so
                # an M2 set screw through the fin wall clamps the jack)
                out.append(("leg_plug_retainer_0",
                            R(LG.leg_plug_retainer(), -41.6, 5.0, LG.TRRS_DY)))
                # leg<->bar blind-mate: jack #2 (mouth DOWN) + seat ring
                # in the short shaft's block; plug + retainer ride the
                # bar tower (axis at station +5, world y ly-13)
                yj = ly - LG.TRRS_DY
                zj = zst + 38.7 - LG.CHJ_MOUTH_Z    # jack mouth at +38.7
                out.append(("shaft_trrs_jack",
                            LG.chassis_trrs_jack()
                            .rotate((0, 0, 0), (0, 0, 1), rot)
                            .translate((sx + 5.0, yj, zj))))
                out.append(("leg_column_plug_1",
                            LG.leg_column_plug()
                            .rotate((0, 0, 0), (0, 0, 1), rot)
                            .translate((sx + 5.0, yj, zst + 48.0))))
                out.append(("jack_seat_ring_1",
                            LG.jack_seat_ring()
                            .rotate((0, 0, 0), (0, 0, 1), rot)
                            .translate((sx + 5.0, yj, zst + 78.2))))
                out.append(("leg_plug_retainer_1",
                            LG.leg_plug_retainer()
                            .rotate((0, 0, 0), (0, 0, 1), rot)
                            .translate((sx + 5.0, yj, zst + 48.0 - 41.6))))
                # ONE OFF-THE-SHELF TRRS M->F EXTENSION cable is the
                # whole column (user: zero connections on the leg): its
                # molded PLUG sits captive in the head (blind-mates the
                # chassis jack), its molded FEMALE barrel seats in the
                # shaft block (receives the bar tower's plug) — no
                # solder, no crimps, no junction anywhere in the leg.
                # Path: head plug -> Ø7 joint bores + cores (y ly-13) ->
                # sleeve groove -> heat-set slack COIL (O8 mandrel/85C;
                # at the groove's inscribed centre, y yj) -> up the
                # shaft's Ø9.7 way to its jack barrel. Drawn as two
                # nets purely so the coil renders between them.
                out.append(("leg_column_cable", WR._wire([
                    (sx - 5.0, yj, CH.Z_BOT - 39.2),
                    (sx - 5.0, yj, CH.Z_BOT - 58.0),
                    (sx, ly - 13.0, CH.Z_BOT - 66.0),
                    (sx, ly - 13.0, CH.Z_BOT - 245.0),
                    (sx, yj, CH.Z_BOT - 262.0),
                    (sx, yj, CH.Z_BOT - 270.0)], 3.8)))
                out.append(("shaft_trrs_cable", WR._wire([
                    (sx + 5.0, yj, zst + 80.0),
                    (sx + 5.0, yj, CH.Z_BOT - 352.0),
                    (sx, yj, CH.Z_BOT - 348.0),
                    (sx, yj, CH.Z_BOT - 340.0)], 3.8)))
                # slack coil in the sleeve's groove free span: at SEC_H 36
                # the groove's largest inscribed circle centres at y -3.5
                # (= TRRS_DY), r ~12.7 — plenty for the O16 coil
                coil = cq.Workplane("XY").add(cq.Solid.makeCylinder(
                    8.0, 70.0, cq.Vector(sx, yj, CH.Z_BOT - 340.0),
                    cq.Vector(0, 0, 1))).cut(
                    cq.Workplane("XY").add(cq.Solid.makeCylinder(
                        4.5, 72.0, cq.Vector(sx, yj, CH.Z_BOT - 341.0),
                        cq.Vector(0, 0, 1))))
                out.append(("leg_cable_coil", coil))
                # body jack's factory cable (Y-INSTALL, finless): the
                # jack drops into the stub's way through the wide rib's
                # well AFTER the slide; its pigtail exits the jack top
                # (-44.95), jogs NORTH to y 50.5 (past the jack barrel,
                # north of the electronics tray) and drops into the
                # OVER-RIB raceway lane (floor -67.3, cut across the
                # wide rib + station rib), riding it east ABOVE the
                # full-length ridge roofs (-67.91), then diagonally down
                # to the bus-B tee. Unplug at the tee to extract.
                out.append(("chassis_trrs_cable", WR._wire([
                    (sx - 5.0, yj, CH.Z_BOT + 30.4),
                    (sx - 5.0, yj, -42.9),
                    (sx - 5.0, 50.5, -42.9),
                    (sx - 5.0, 50.5, -65.0),
                    (-586.5, 50.5, -65.0),
                    (-581.5, 35.5, WR.HDR_Z)], 3.8)))
                #   ^ the descent elbow sits 2.5 east of the station
                #     rib's face (-589) so the fat diagonal rod clears
                #     its corner south of the raceway band
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
    """The compute bay (PRO population shown; a basic build leaves the Pi /
    CS stack / buck sockets empty) + panel jacks + the wire harness."""
    from . import electronics as EL
    from . import wiring as WR
    from . import top_plate as TP
    out = [("electronics_tray", EL.electronics_tray()),
           ("pi5", EL.pi5()), ("teensy_stack", EL.teensy_stack()),
           ("adc_stack", EL.adc_stack()), ("buck", EL.buck()),
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


# ── THE SIX KNEE LEVERS ──────────────────────────────────────────────────────
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
    best = min((abs(rib - KV.TEN_Y[1] - mid), rib - KV.TEN_Y[1])
               for rib in (_RIB0 + _RIB * k for k in range(30)))
    return best[1]


_ILKL_X = -501.0                             # hard -X bound: the left leg block
_LKL_X = _ILKL_X                             # -501: see _KNEE_GAP_L
_RKL_X = -225.0                              # right knee

LEVER_STATIONS = (
    ("ilkl", "kl", _ILKL_X,              _ILKL_Y,  False),
    # LEFT KNEE: the knee sits in the gap between LKL and LKR, and VKL sits in that
    # same gap so the vertical arm is directly above it (user). VKL's station is
    # rib-DERIVED (MOUNT_X = rib - 10.4) so its own two tenons land on ribs.
    ("lkl",  "kl", _LKL_X,               _LEVER_Y, False),
    ("vkl",  "kv", _vkl_station(),       None,     False),   # mid-gap, rib-derived
    #                                                          None -> _vkl_mount_y()
    ("lkr",  "kl", _LKL_X + _KNEE_GAP_L, _LEVER_Y, True),    # -386
    # RIGHT KNEE: same gap, no vertical lever in this copedent
    ("rkl",  "kl", _RKL_X,               _LEVER_Y, False),
    ("rkr",  "kl", _RKL_X + _KNEE_GAP_R, _LEVER_Y, True),    # -133
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
           ("kl_axle", swing(KL.kl_axle)),                  # keyed + set screw -> turns with the lever
           ("kl_magnet_cap", swing(KL.kl_magnet_cap))]      # screwed to the axle
    for nm, off, s in (("main", KL.CART_MAIN_OFFSET, s_main), ("half_stop", KL.CART_HALFSTOP_OFFSET, s_hs)):
        out.append((f"{nm}_cart_base", KL.feel_place(KL.cart_base.translate(off))))
        out.append((f"{nm}_cart_piston", KL.feel_place(KL.cart_piston.translate(off)).translate((-s, 0, 0))))
        out.append((f"{nm}_guide_post", KL.feel_place(KL.guide_post.translate(off))))
    for n, s in KL.demo_parts():                         # magnet spins with the lever; the rest are stationary
        out.append((n, swing(s) if n == "kl_magnet" else s))
    # (the octagon mount tenons are FUSED onto knee_housing now -- no separate floating_tenon parts)
    return out


def _lever_stations_components():
    """All six knee levers, each design posed at its station (LEVER_STATIONS).

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


def _joint_coupon_components():
    """The octagon-joint print coupons, parked off the +X end of the guitar (clear
    of every real part) so they rebuild with the model and can't drift from the
    cadkit geometry. Shown side by side in Y, unmated."""
    from . import joint_coupon as JC
    dy = JC.WIDTH + 20.0
    ten = JC.tenon_coupon().translate((150.0, -dy, 40.0))
    mor = JC.mortise_coupon().translate((150.0, dy, 40.0))
    return [("test_octagon_tenon_coupon", ten), ("test_octagon_mortise_coupon", mor)]


def _nut_coupon_components():
    """The string-termination DEMO — the WRAP POST scheme — parked off the +X end
    beside the other coupons. Not a printed part and not the real nut block yet: it
    exists so the mechanism can be SEEN (user), and it is built from dimensions.py's
    own gauges so it cannot drift from the instrument it is proposing a change to."""
    from . import nut_coupon as NC
    out = [(n, s.translate((150.0, -90.0, 40.0))) for n, s in NC.demo_parts()]
    # VARIANT B beside it (user): one shared rod along Y instead of ten posts
    # along Z. Same three gauges, same clamp — only the winding changes, so the
    # two sit side by side and the difference is the only thing you see.
    out += [(n, s.translate((150.0, -150.0, 40.0))) for n, s in NC.demo_parts_rod()]
    return out


def _tensioner_coupon_components():
    """The belt-tension clamp, shown ASSEMBLED (working position) with its M4 screw +
    brass insert, parked off the +X end clear of every real part. Rebuilds with the
    model so it can't drift from belt_tensioner.py."""
    from . import belt_tensioner as BTn
    o = cq.Vector(150.0, 90.0, 40.0)
    def at(p): return p.translate((o.x, o.y, o.z))
    la = BTn.seated_lifter(BTn.lifter_a(), (BTn.GA0 + BTn.GA1) / 2, locked=True)
    lb = BTn.seated_lifter(BTn.lifter_b(), (BTn.GB0 + BTn.GB1) / 2, locked=True)
    return [
        ("belt_tensioner_anchor_coupon", at(BTn.anchor())),
        ("belt_tensioner_slider_coupon", at(BTn.slider())),
        ("belt_tensioner_lifter_a_coupon", at(la)),
        ("belt_tensioner_lifter_b_coupon", at(lb)),
        ("belt_tensioner_screw_coupon",  at(BTn.screw_dummy())),
        ("belt_tensioner_insert_coupon", at(BTn.insert_dummy())),
    ]


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
    comps += _foot_pedal_components()
    comps += _electronics_components()
    comps += _lever_stations_components()      # all six, LKL/VKL included
    comps += _joint_coupon_components()
    comps += _nut_coupon_components()
    comps += _tensioner_coupon_components()
    for i in range(D.N_STRINGS):
        comps.extend(_string_components(i))
    return comps


# Per-part colours, baked into the assembly STEP (single source of truth — they
# show in the shared FreeCAD live viewer and any STEP viewer). RGB floats 0..1.
_COLORS = {
    "bridge_endplate": (0.39, 0.58, 0.93),   # PETG-GF — load-critical
    "keyhead_endplate": (0.42, 0.50, 0.62),   # PETG-GF — keyhead endplate + nut block (merged)
    "belt_clamp":      (0.95, 0.55, 0.15),   # PETG
    "belt_tensioner_anchor_coupon": (0.20, 0.70, 0.45),   # coupon — green = test piece
    "belt_tensioner_slider_coupon": (0.30, 0.80, 0.55),
    "belt_tensioner_lifter_a_coupon": (0.40, 0.85, 0.65),  # lifter bars
    "belt_tensioner_lifter_b_coupon": (0.40, 0.85, 0.65),
    "belt_tensioner_screw_coupon":  (0.55, 0.55, 0.58),   # steel M4
    "belt_tensioner_insert_coupon": (0.72, 0.60, 0.30),   # brass insert
    "screw_pulley":    (0.00, 0.55, 0.55),
    "motor_pulley":    (0.00, 0.55, 0.55),
    "leadscrew":       (0.75, 0.75, 0.78),   # steel
    "screw_bearing":   (0.69, 0.77, 0.87),
    "bridge_bearings": (0.69, 0.77, 0.87),
    "nut":             (0.82, 0.60, 0.20),   # brass
    "string_nut":      (0.82, 0.60, 0.20),   # brass string-end fitting (demo)
    "screw_collar":    (0.30, 0.65, 0.80),
    "guide_rod":       (0.35, 0.35, 0.38),
    "motor":           (0.22, 0.25, 0.27),   # charcoal
    "belt":            (0.13, 0.13, 0.13),   # GT2 black
    "string":          (0.85, 0.85, 0.85),
    "break_dowel":     (0.75, 0.75, 0.78),   # steel dowel (gauged break pin)
    # nut-termination DEMO (nut_coupon.py) — parked off +X, not a printed part
    "nutdemo_block":       (0.30, 0.45, 0.35),   # PETG-GF, as the real nut block
    "nutdemo_break_dowel": (0.75, 0.75, 0.78),   # existing O2 dowel
    "nutdemo_anvil":       (0.75, 0.75, 0.78),   # the OPTIONAL second O2 dowel
    "nutdemo_post":        (0.62, 0.66, 0.72),   # THE NEW PART: O6 wrap post
    "nutdemo_screw":       (0.55, 0.55, 0.58),   # existing M4 cup-tip set screw
    "nutdemo_insert":      (0.80, 0.62, 0.28),   # existing brass heat-set insert
    "nutdemo_string":      (0.85, 0.85, 0.85),   # string
    # variant B — the shared Y rod
    "rodnut_block":        (0.30, 0.45, 0.35),
    "rodnut_break_dowel":  (0.75, 0.75, 0.78),
    "rodnut_anvil":        (0.75, 0.75, 0.78),
    "rodnut_rod":          (0.62, 0.66, 0.72),   # ONE part, not ten
    "rodnut_screw":        (0.55, 0.55, 0.58),
    "rodnut_insert":       (0.80, 0.62, 0.28),
    "rodnut_string":       (0.85, 0.85, 0.85),
    "set_screw":       (0.55, 0.55, 0.58),   # alloy set screw
    "pickup_jack_screw":  (0.55, 0.55, 0.58),  # M4 top-access height set-screw jack
    "pickup_jack_insert":  (0.80, 0.60, 0.35),  # brass heat-set insert (jack)
    "pickup_retention_screw": (0.55, 0.55, 0.58),  # M4 -Y retention cup-tip set screw
    "pickup_retention_insert": (0.80, 0.60, 0.35),  # brass heat-set insert (-Y retention grub)
    "chassis":         (0.46, 0.52, 0.55),   # PETG-GF frame
    "pickup":          (0.10, 0.10, 0.12),   # DEMO pickup body
    "pickup_zplate":   (0.85, 0.65, 0.30),   # PCTG height plate (under the pickup)
    "leg_body_stub":   (0.36, 0.42, 0.46),
    "leg_seg_body":    (0.42, 0.48, 0.52),   # square GF bodies
    "leg_coupler_m":   (0.36, 0.42, 0.46),
    "leg_coupler_f":   (0.36, 0.42, 0.46),
    "leg_head":        (0.36, 0.42, 0.46),
    "latch_slider":    (0.85, 0.35, 0.20),   # latch accent
    "latch_cover":     (0.55, 0.30, 0.22),
    "latch_spring":    (0.62, 0.64, 0.67),   # stainless coil (purchased)
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
    "kv_lever":        (0.92, 0.72, 0.20),   # LKV arm (PCTG, as LKL)
    "kv_pcb":          (0.05, 0.35, 0.15),   # LKV MT6701 board (green, as LKL)
    "kv_chip":         (0.12, 0.12, 0.14),   # LKV MT6701 package (black)
    "kv_can_header":   (0.95, 0.95, 0.90),   # LKV S4B-XH-SM4-TB + mated XHP-4
    "kv_pcb_shim":     (0.75, 0.75, 0.78),   # LKV board shim (printed, takes up the slack)
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
    # electronics bay (dummies) + panel jacks
    "electronics_tray": (0.30, 0.36, 0.32),  # printed tray
    "pi5":             (0.05, 0.35, 0.15),   # PCB green
    "teensy_stack":    (0.10, 0.45, 0.30),
    "adc_stack":       (0.15, 0.25, 0.50),
    "buck":            (0.35, 0.30, 0.50),
    "teensy_ifc":      (0.55, 0.25, 0.25),   # Teensy interface PCB (2x CAN
                                             # transceiver + XH headers)
    "tee_pcb":         (0.10, 0.42, 0.18),   # trunk-and-drop bus tee PCBs
    "tee_cradle":      (0.32, 0.55, 0.42),   # PCTG 3-wall drop-in PCB cradle (pcb_cradle)
    "analog_frontend": (0.20, 0.45, 0.40),   # bridge-end buffer + relay board
    "optical_pcb":     (0.12, 0.30, 0.55),   # per-string optical strip (blue solder mask,
                                             # so it reads apart from the green audio PCBs)
    "optical_cables":  (0.15, 0.15, 0.17),   # USB-C + XHP-6 plugs and their leads
    "optical_insert":  (0.72, 0.60, 0.30),   # M4 heat-set brass, board grips
    "optical_screw":   (0.72, 0.74, 0.78),   # M4x12 button, down into it
    "optical_cover":   (0.18, 0.18, 0.20),   # slotted lid over the sensor row -- print it
                                             # DARK: it is the one surface facing the
                                             # detectors, so a light one would bounce IR
    "top_plate":       (0.88, 0.91, 0.94),   # transparent-PCTG deck base + fret lines
    "top_plate_color": (0.30, 0.33, 0.38),   # colour-PCTG deck layer (skin contact)
    "oled":            (0.05, 0.05, 0.08),   # screen (perfect-black OLED)
    "joystick":        (0.15, 0.15, 0.17),   # UI control
    "ts_jack":         (0.62, 0.64, 0.67),
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
    "wire_canbh":      (0.95, 0.85, 0.10),   # yellow      - bus B CAN-H
    "wire_canbl":      (0.13, 0.72, 0.20),   # green       - bus B CAN-L
    "wire_canjmph":    (0.95, 0.85, 0.10),   # yellow      - jumper CAN-H
    "wire_canjmpl":    (0.13, 0.72, 0.20),   # green       - jumper CAN-L
    "motor_pigtail":   (0.45, 0.45, 0.48),   # grey        - SERVO42D's own 6-pin
                                             #   XH pigtail (factory jacket)
    "wire_knee_drop":  (0.45, 0.45, 0.48),   # grey        - LKL drop stub
    "wire_pickup":     (0.55, 0.85, 0.55),   # lightest green - shielded: pickup -> AFE
    "wire_audio":      (0.30, 0.72, 0.40),   # light green - shielded: AFE -> ADC
    "wire_dac":        (0.10, 0.52, 0.28),   # dark green  - shielded: DAC -> AFE
    "wire_out":        (0.04, 0.34, 0.18),   # darkest green - shielded: relay -> jack
    "wire_relayctrl":  (0.98, 0.88, 0.35),   # lightest amber - relay control
    "wire_link":       (0.95, 0.72, 0.22),   # light amber - Teensy <-> Pi
    "wire_tdm":        (0.80, 0.46, 0.10),   # deep amber  - CS stack -> Pi
    "wire_oled":       (0.68, 0.36, 0.08),   # brown-amber - OLED -> Teensy
    "wire_joy":        (0.54, 0.28, 0.08),   # darkest amber - joystick -> Teensy
    "wire_usb":        (0.55, 0.25, 0.75),   # violet      - shielded USB-2 -> Pi
    "test_octagon_tenon_coupon":   (0.20, 0.75, 0.85),   # cyan  - joint coupon (test piece)
    "test_octagon_mortise_coupon": (0.95, 0.55, 0.15),   # orange - joint coupon (test piece)
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
    if base in _COLORS:
        return cq.Color(*_COLORS[base])
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
    # The five non-LKL LEVER STATIONS prefix the same way (ilkl_knee_housing,
    # vkl_kv_lever, ...), so they ride this rule too — the alternative was six
    # copies of the same 29 entries, and any station left out would have gone grey
    # exactly the way the pedals did.
    _st = re.match(r"(?:pedal\d+|ilkl|lkr|vkl|rkl|rkr|kv|kl)_(.+)$", base)
    if _st:
        inner = _st.group(1)
        # a KV station is doubly prefixed (vkl_kv_housing): peel to kv_housing too
        for k in (f"kl_{inner}", inner, f"kv_{inner}"):
            if k in _COLORS:
                return cq.Color(*_COLORS[k])
    if base == "pedal_lever":
        return cq.Color(*_COLORS["knee_lever"])   # it IS the knee lever, posed
    return cq.Color(*_DEFAULT_COLOR)


def _export_assembly(publish=True, gate=True, gate_full=False):
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
    return _report_overlaps(comps, full=gate_full) | _report_sweep(comps)


# The overlap gate's ACCEPTED baseline: pairs that are real interpenetrations but
# predate the gate and are tracked separately (chassis_trrs_cable vs
# electronics_tray ~28 mm^3, vs pi5 ~1 mm^3). The build fails only on a count
# ABOVE this — i.e. on a NEW overlap. Drive it to 0 when those are fixed.
OVERLAP_BASELINE = 2


def _report_overlaps(comps, full=False) -> int:
    """Run the overlap gate on the model we JUST built, and return 1 on regression.

    This is the whole point of folding the gate into the build: the scan itself is
    ~13 s, but ``tools.check_overlaps`` run standalone spends ~5.5 MINUTES rebuilding
    the model first. Reusing ``comps`` makes a full-tree gate essentially free, so
    the lead never has to choose between gating and building.
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
    p.add_argument("--gate-full", action="store_true",
                   help="Gate EVERY part, belts included (slower; belts rarely move).")
    args = p.parse_args()

    if args.geom:
        print(geometry_report())
        return
    if args.list:
        print("assembly")
        for name in PARTS:
            print(name)
        return
    gate, gate_full = not args.no_gate, args.gate_full
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
    report_build_regressions()          # ~free: flags any part whose face count grew vs baseline
    sys.exit(_export_assembly(gate=gate, gate_full=gate_full))


if __name__ == "__main__":
    main()
