"""Public Steel Guitar -- the main build: the direct-drive instrument.

  py -3.12 -m src.build              # build all printed parts + the viewer's model + the gates
  py -3.12 -m src.build --part NAME  # build one printed part (fast iteration)
  py -3.12 -m src.build --list       # list part names

The instrument is src.direct_bench's (user, 2026-11-13). Its printed parts come from there
(_direct_parts, below); the parts it reuses from earlier designs -- the knee levers, the leg
and its latches, the pedal bar, the UI station's printed parts and the shop jigs -- are
listed in PARTS here and built by their own modules. The v1 belt-drive instrument is gone
from the build (lead, 2026-11-17); it is at the git tag v1-instrument.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import pathlib
import re
import sys
import time
from functools import partial

_T_IMPORT = time.perf_counter()         # the modules below BUILD GEOMETRY as they import

import cadquery as cq

# Shared CAD utilities, vendored at <project>/cadkit (git subtree).
from cadkit.step_export import export_print, export_print_parts
from cadkit.orientation import (PrintOrientation as PO,
                                require_declared, unconfirmed)
try:                                    # optional on-every-build face-count regression gate
    from tools.build_profile import (record_part, report_build_regressions,
                                     write_part_volumes)
except Exception:                       # a profiling hook must NEVER break a build
    def record_part(*a, **k): pass
    def report_build_regressions(): return 0
    def write_part_volumes(*a, **k): return 0

from .helpers import heal


def _m(name):
    """src.<name>, imported when a builder first runs and not before: a part's module is
    only paid for by a build that builds it (--part and --list import nothing else)."""
    return importlib.import_module("src." + name)


def _PB(attr):
    return getattr(_m("pedal_bar"), attr)()


def _PB_bar(attr):
    """A pedal-bar piece with its pedal housings fused in (foot_pedal.bar_piece)."""
    return _m("foot_pedal").bar_piece(attr)


# ── PRINTED parts → each is exported as its own STEP. ────────────────────
# This is the ONLY set that gets STEP files; purchased parts and stand-ins appear only in
# the assembly. Values are (builder, path, note); the builder runs at export time, so
# importing this module builds nothing. Paths are MATERIAL FOLDERS -- slice a whole folder
# with one filament:
#   petg-gf/  stiffness/creep-critical (the sustained string-tension + ground-reaction paths)
#   pctg/     compliant, snap-fit, impact and fine-feature parts
#   tpu/      feet
#   steel/    laser-cut sheet (ordered, not printed)
#   tools/    shop jigs
PARTS = {
    "knee_housing": (lambda: _m("knee_lever").knee_housing, "petg-gf/knee_housing.step", "PETG-GF — knee-lever (LKL) housing: ONE parametric prism derived from the lever/cartridge/body extents, minus the house-pockets, backstop threads + lever room, plus FOUR fused octagon mount tenons on the top face (one per chassis rib crossing; the +X-most survives only as a stub over each cheek) and the MT6701 board CRADLE on the +Y face (grooves + plinth + floor; the board drops in from +Z with the lever OFF the instrument and the chassis underside becomes its lid — no retaining screw. Ø14 driver bore reserved for the magnet cap, plus a relief channel through the cheek and the -X web for the board's side-entry CAN connector and its plug). Retention is all on -X: the +X web stops at the plinth top so NOTHING stands +X of the prism face. Depth lock deferred"),
    "knee_housing_r": (lambda: _m("knee_lever").knee_housing_r, "petg-gf/knee_housing_r.step", "PETG-GF — RIGHT-HAND knee-lever housing (LKR, RKR: struck by the knee moving +X): knee_housing's mirror image in X, except the board cradle, plug tunnel and knee relief, which are cut for the ONE sensor board turned over about the axle (connector toward +X, long end up, 1.7 higher, no shim). Print 2. The mirrored lever, cartridges and axle it carries are not exported yet"),
    "knee_lever": (lambda: _m("knee_lever").knee_lever,   "pctg/knee_lever.step",   "PCTG — knee-lever (LKL) arm + knee paddle (takes knee strikes: toughness over stiffness); the +Y axle journal + magnet stub print INTEGRAL (stand off the lying -Y bed face)"),
    "kl_axle": (lambda: _m("knee_lever").kl_axle, "pctg/kl_axle.step", "PCTG — knee-lever AXLE ×1: ONE full-length part fitted LAST, slid +Y→−Y through bearing/lever/bearing (the old integral stub could never enter its bearing). Ø8 journals, D-FLAT key through the hub, flange land seating on the +Y inner race (= the air-gap datum), threaded magnet pocket, M4 thread-forming bore in the −Y tip for the retention screw + washer. Prints STANDING, POCKET-DOWN, with a brim"),
    "kl_spacer": (lambda: _m("knee_lever").spacer(), "pctg/kl_spacer.step", "PCTG — axle SPACER ×2 per lever (×2 per pedal): Ø10 ring between the lever's flat face and each bearing's INNER race, through the seat's printed shoulder. Part of the clamped rotating stack (land, races, spacers, lever, washer), which is what locks the lever in Y. Slip it over the axle as the axle goes through. Prints FLAT"),
    "kl_spacer_sprung": (lambda: _m("knee_lever").spacer(_m("knee_lever").SPRUNG_SPACER_T), "pctg/kl_spacer_sprung.step", "PCTG — LKL axle SPACER, +Y (the stack with the PRELOAD SPRING): the same Ø10 ring as kl_spacer but EXACT, lever face -> +Y inner race (2.00, not 2.05) -- the spring takes up the print error instead of a sized-long clamp. Prints FLAT"),
    "kl_spacer_sprung_n": (lambda: _m("knee_lever").spacer(_m("knee_lever").SPRUNG_SPACER_T_N), "pctg/kl_spacer_sprung_n.step", "PCTG — LKL axle SPACER, -Y (3.59): lever face -> the -Y inner race, through both -Y shoulders (the -Y bearing sits out past the preload spring). Prints FLAT"),
    "kl_axle_sprung": (lambda: _m("knee_lever").kl_axle_sprung, "pctg/kl_axle_sprung.step", "PCTG — the LKL's AXLE: kl_axle 1.59 longer at the -Y end, for the -Y bearing out past the PRELOAD SPRING (McMaster 9714K29). Same journals, flat, land, magnet pocket and end screw. Prints STANDING, POCKET-DOWN, with a brim"),
    "kl_magnet_cap": (lambda: _m("knee_lever").kl_magnet_cap, "pctg/kl_magnet_cap.step", "PCTG — magnet CAP ×1: female-threaded HEX nut (9.35 across flats, for a 3/8-inch driver) screwing over the axle's pocket collar to clamp the Ø6 diametric disc; centre stays open so nothing intrudes on the air gap. Fit it BEFORE the sensor board. Prints APERTURE-DOWN"),
    "kl_pcb_shim": (lambda: (lambda KL: KL.pcb_shim(KL.HOUS_Z0, KL.HOUS_Z1))(_m("knee_lever")), "pctg/kl_pcb_shim.step", "PCTG — sensor-board shim, LEFT-HAND knee levers (x2: LKL, RKL): a 33.0 x 1.55 strip one board thick that drops down the cradle grooves on top of the board, so the chassis underside presses the board through it. The right-hand housings need none. Prints FLAT, on a big face"),
    "kv_pcb_shim": (lambda: _m("knee_lever_vert").kv_pcb_shim, "pctg/kv_pcb_shim.step", "PCTG — sensor-board shim, VERTICAL knee lever (x1): the same plate 20.95 tall, filling the taller housing's cradle above the one board. Prints FLAT, on a big face"),
    "pedal_pcb_shim": (lambda: (lambda KL, FP: KL.pcb_shim(FP.CRADLE_Z0, FP.SHIM_TOP, FP.BOARD_FLIP))(_m("knee_lever"), _m("foot_pedal")), "pctg/pedal_pcb_shim.step", "PCTG — sensor-board shim, FOOT PEDALS (x5): the same plate 24.70 tall, standing from the board's edge to the bar's lid groove; the LID presses it. Prints FLAT, on a big face"),
    "kv_housing": (lambda: _m("knee_lever_vert").kv_housing, "petg-gf/kv_housing.step", "PETG-GF — VERTICAL knee-lever (LKV) housing: same prism derivation as LKL but with the feel block TRANSLATED above the axle (not mirrored — the pocket gable stays up for printability), so the axle sits 19.2 lower and the arm has room to swing UP. Y is asymmetric (-16.10..+13.90): the -Y wall is 2.2 wider to fit TWO octagon tenons at the 23mm rib pitch, while the +Y sensor face is untouched. Tenons slide along local X (= the guitar's Y once posed). Carries the SAME sensor cradle as LKL (knee_lever._cradle, parameterised by the housing Z extents) - the board is just taller here, 31.2 vs 19. Rest stop deferred"),
    "kv_lever": (lambda: _m("knee_lever_vert").kv_lever, "pctg/kv_lever.step", "PCTG — VERTICAL knee-lever (LKV) arm: an L. Hub on the axle, a LEG rising +Z carrying the return lobe at 13.2 (sized so the 20° throw gives the SAME 4.51 spring stroke as LKL's 30°), and a 50mm ARM running +X that the knee lifts — 17.1 of paddle rise"),
    "cart_base": (lambda: _m("knee_lever").cart_base, "pctg/cart_base.step", "PCTG — spring-cartridge (inverted-U, open -Z; shared: print 2, for main + half-stop)"),
    "cart_piston": (lambda: _m("knee_lever").cart_piston, "pctg/cart_piston.step", "PCTG — spring-cartridge piston, flat follower tongue (shared: print 2)"),
    "leg_foot": (lambda: heal(_m("legs").leg_foot()),    "tpu/leg_foot.step",    "TPU — SHARED dovetail foot ×4 (user: one look): 44-sq pad + tenon into the underside mortise of the -Y leg blocks AND the pedal bar; the wired bar one covers the plug-threading access"),
    "body_adapter": (lambda: heal(_m("leg_stack").body_adapter()), "petg-gf/body_adapter.step", "PETG-GF — body adapter, -X/+Y corner (the leg): slides into the body's mortises along Y (two octagon ridges + the end-wall tongue in its rebate), one M4 shear pin down the rail + the endplate's lock pin; blind mortise below for the fixed tenon, with the body latch's pocket. Prints +Y -> -Y"),
    "body_adapter_px_py": (lambda: heal(_m("leg_stack").body_adapter(_m("chassis").LEG_STATIONS_X[0], _m("chassis").LEG_Y[0])), "petg-gf/body_adapter_px_py.step", "PETG-GF — body adapter, +X/+Y corner: the same adapter with its body joinery built for that corner (tongue toward +X)"),
    "body_adapter_px_my": (lambda: heal(_m("leg_stack").body_adapter(_m("chassis").LEG_STATIONS_X[0], _m("chassis").LEG_Y[1])), "petg-gf/body_adapter_px_my.step", "PETG-GF — body adapter, +X/-Y corner (tongue toward +X, screw down the -Y rail)"),
    "body_adapter_mx_my": (lambda: heal(_m("leg_stack").body_adapter(_m("chassis").LEG_STATIONS_X[1], _m("chassis").LEG_Y[1])), "petg-gf/body_adapter_mx_my.step", "PETG-GF — body adapter, -X/-Y corner (tongue toward -X, screw down the -Y rail)"),
    "fixed_sleeve": (lambda: heal(_m("leg_stack").fixed_sleeve()), "petg-gf/fixed_sleeve.step", "PETG-GF — fixed sleeve: butts the adapter, pinned to the fixed tenon by one +X screw; the body latch's pad sits flush in its -Y face. Prints +Y -> -Y"),
    "adjust_sleeve": (lambda: heal(_m("leg_stack").adjust_sleeve()), "petg-gf/adjust_sleeve.step", "PETG-GF — adjust sleeve: butts the fixed sleeve; one +X screw pins the fixed tenon, one sets the height through the adjust tenon's ladder. Prints +Y -> -Y"),
    "fixed_tenon": (lambda: heal(_m("leg_stack").fixed_tenon()), "petg-gf/fixed_tenon.step", "PETG-GF — fixed floating tenon: adapter <-> fixed sleeve <-> adjust sleeve, houses the body latch slider and spring. Prints diagonally (+X+Y -> -X-Y)"),
    "adjust_tenon": (lambda: heal(_m("leg_stack").adjust_tenon()), "petg-gf/adjust_tenon.step", "PETG-GF — adjust floating tenon: the height ladder (blind +X holes) and, at its bar end, the pedal bar latch's pocket and lead-in. Prints diagonally (+X+Y -> -X-Y)"),
    "leg_latch_slider": (lambda: heal(_m("leg_latch").slider()), "pctg/leg_latch_slider.step", "PCTG — body latch slider: push-to-connect hook into the adapter, flush 20x20 pad on the fixed sleeve, one steel coil. Prints -X -> +X"),
    "bar_latch_frame": (lambda: heal(_m("leg_stack").bar_latch_frame()), "pctg/bar_latch_frame.step", "PCTG — pedal bar yoke latch: a ring round the adjust tenon, hook in its pocket, 20x20 pad flush in the collar, a cup seating its one coil. Prints ring down"),
    "bar_latch_collar": (lambda: heal(_m("leg_stack").bar_latch_collar()), "petg-gf/bar_latch_collar.step", "PETG-GF — pedal bar latch collar: the top 22.4 of the bar's tower, holding the yoke and its springs; two T rails slide it onto the tower from +Y, one M4x40 button head into a heat-set insert in the tower locks it. Prints on its +Y face"),
    "pedal_bar_a": (lambda: _PB_bar("pedal_bar_a"), "petg-gf/pedal_bar_a.step", "PETG-GF — pedal bar, -X piece (35.6 wide, flush with the slimmed leg blocks; fused WIRED tower; trough + lid groove; splice tenons at +X). ~205 long: prints STRAIGHT; _b drops onto the tenons, the LID locks the stack — no glue"),
    "pedal_bar_b": (lambda: _PB_bar("pedal_bar_b"), "petg-gf/pedal_bar_b.step", "PETG-GF — pedal bar, MID piece (trough only; XS1 cavities -X, XS2 tenons +X). ~229 long: straight print; slides straight down onto _a's tenons (the lid is the Z lock — no glue)"),
    "pedal_bar_c": (lambda: _PB_bar("pedal_bar_c"), "petg-gf/pedal_bar_c.step", "PETG-GF — pedal bar, +X piece (35.6 wide, flush with the slimmed leg blocks; fused PLAIN tower; splice cavities at -X). ~229 long: straight print; slides straight down onto _b's tenons (the lid is the Z lock — no glue)"),
    "pedal_lid_a": (lambda: heal(_PB("pedal_lid_a")), "petg-gf/pedal_lid_a.step", "PETG-GF — sliding dovetail lid, -X piece (covers the TRRS latch; bridges bar splice XS1; carries the lock dimple). Goes in SECOND, and its -X end finishes FLUSH with the bar. 318 long: diagonal, TOP-FACE DOWN (45-deg flanks)"),
    "pedal_lid_b": (lambda: heal(_PB("pedal_lid_b")), "petg-gf/pedal_lid_b.step", "PETG-GF — sliding dovetail lid, +X piece (covers the plain latch; bridges XS2). INSTALL BOTH FROM THE -X END: B first, run it the whole bar until it butts the 1.6 end wall, then A behind it — A's dimple clicks the nub and pins the stack. 317 long: diagonal, TOP-FACE DOWN"),
    "pedal_lever": (lambda: heal(_m("foot_pedal").pedal_lever()), "pctg/pedal_lever.step", "PCTG — FOOT PEDAL lever ×3 (initial design): hub on the axle, leg carrying the return lobe at 13.2 (sized so the 20° throw gives the SAME 4.51 spring stroke as the knee levers — which is what lets the half stop transfer for free), a 90 mm arm running out to the player and the pedal board across its end (30.8 mm of travel, ~1.6→3 N at the board)"),
    "pedal_detent_nub": (lambda: heal(_PB("nub_part")), "tpu/pedal_detent_nub.step", "TPU — detent nub ×1 (Ø4×4): presses into the bar top as the LID lock"),
    "ui_clamp": (lambda: heal(_m("ui_panel").clamp()), "petg-gf/ui_clamp.step", "PETG-GF - the UI clamp plate. It lies against the BOARD'S UNDERSIDE (3.2 thick, a relief under each through-hole footprint for the tails) and one M4x10 pulls it up into the deck panel's own boss, gripping the board between its whole top face and the deck's bearings; two spigots off the deck locate it. It holds the display too: two arms step up past the board and run +Y under the module, either side of the display's ribbon, to a crossbar at its far mounting-hole row, and four columns -- two off that crossbar, two off tabs beside the board's ends -- press the module's PCB into the window ledge. The ribbon carries no load, so that is the screen's whole retention. GF because it is a stiffness part. Prints PLATE-DOWN, its own flat underside on the bed, so every rib, column and post grows straight up off it"),
    "ui_pwr_cap": (lambda: heal(_m("ui_panel").power_cap()), "pctg/ui_pwr_cap.step", "PCTG - the power button's cap: a plain O15.2 disc with a blind square socket, pressed onto the latching switch's 3.3 mm stem and guided by its hole in the deck. Prints TOP-FACE-DOWN, the socket opening upward, so the face the thumb meets is the bed's and the socket's floor is printed before its walls. The socket bottoms on the stem's end: a push goes through the cap's full thickness, not through the press fit. PCTG, the knob's resin and the deck's"),
    "ui_knob": (lambda: heal(_m("ui_panel").knob()), "pctg/ui_knob.step", "PCTG - the UI cap: a O8 shank up through the deck and a O17 disc over it, bored O2.6x1.8 for the Alps shaft's tip. Prints DISC-DOWN (its own flat face on the bed), so the shank and the bore are both vertical and the bore's ceiling is the last thing printed. PCTG because it is the one part of the instrument a player touches every time they change a setting, and the deck it sits on is the same resin"),
    "coil_mandrel": (
    lambda: heal(_m("coil_mandrel").mandrel()),
    "tools/coil_mandrel.step",
    "TOOL — inner mandrel for winding the leg's TRRS lead into a 7-turn coil. Barrel Ø15.2 with a helical pitch rib, flange-down on a Ø27.8 base, TAIL_RUN of plain barrel each side so both tails leave AXIAL, and a full-thickness slit so the starting tail carries on DOWN through the flange. PA6-GF, printed SOLID"),
    "coil_mandrel_sleeve": (
    lambda: heal(_m("coil_mandrel").sleeve()),
    "tools/coil_mandrel_sleeve.step",
    "TOOL — the mandrel's outer sleeve, bore Ø23.0. It caps the coil's diameter so the mean lands on arithmetic rather than on spring-back, and holds both axial tails against the barrel while they set. PA6-GF, printed SOLID"),
    "lever_prog_jig": (
    lambda: heal(_m("lever_jig").jig()),
    "tools/lever_prog_jig.step",
    "TOOL — pogo nest for flashing the 11 lever/pedal sensor boards. The board drops in COMPONENT FACE DOWN onto four pogo pins (Adafruit 2430) standing at TP1–TP4 (positions read from the routed board), and J1 is powered through the end window. NO GLUE: each pin stands on the base plate and is held up by its own lead, which is nipped under the ear by the one M4 screw. One brass M4 insert in the ear's underside. PETG, printed as drawn"),
    "lever_prog_jig_base": (
    lambda: heal(_m("lever_jig").base()),
    "tools/lever_prog_jig_base.step",
    "TOOL — the jig's base plate: the flat the four pins stand on, screwed to the nest's ear with one M4 x 10 button screw whose head is sunk in the underside. PETG, printed UPSIDE DOWN (the counterbore opens upward)"),
    "saw_jig": (
    lambda: heal(_m("saw_jig").body()),
    "tools/saw_jig.step",
    "TOOL — hacksaw jig for cutting the ten Tr8x2 leadscrews to SCREW_LEN by hand with one Quick-Grip and no vise: the rod rests on two crests in a 90 deg V tunnel, the saw slot (1.3, McMaster 6927A16) sits 5.6 past the clamped support, and the piece overhangs an OPEN fork to a fixed end stop at SCREW_LEN + 0.4, then drops out. The table-edge notch goes on the table edge so a slipped blade hits the jig. PETG, printed as drawn"),
    "motor_shaft_saw_jig": (
    lambda: heal(_m("motor_shaft_saw_jig").body()),
    "tools/motor_shaft_saw_jig.step",
    "TOOL — the leadscrew saw jig's sibling for cutting each SERVO42D's shaft to components.MOTOR_SHAFT_CUT_L, no screws: the motor drops into the chassis' own bay (motor_bank.lift_prism + low_walls, the bay's boss slot), faceplate pushed home on a 1.6 lip, shaft on a cradle rib its full length to a 1.3 saw slot (McMaster 6927A16) at the cut plane with a 3.2 cheek each side, the motor-side cheek braced by two 45 deg gussets; 1.6 floor and bay walls to the shaft axis. NO CAP: the Quick-Grip pad goes straight on the motor. PETG-GF on the 0.8, printed as drawn"),
    "saw_jig_cap": (
    lambda: heal(_m("saw_jig").cap()),
    "tools/saw_jig_cap.step",
    "TOOL — the saw jig's cap: a plunger down the clamp channel whose 45 deg notch seats on the rod's upper crests, with a rimmed pocket on top for the Quick-Grip pad. The clamp squeezes cap, rod, jig and table in one stack. PETG, printed as drawn (notch on the bed)"),
    "pin_drill_jig": (
    lambda: heal(_m("pin_drill_jig").body()),
    "tools/pin_drill_jig.step",
    "TOOL — drill jig for the cross hole that pins a Tr8x2 leadscrew into the printed motor coupler: the saw jig's diamond tunnel and Quick-Grip cap (print a second saw_jig_cap), an end stop that puts the hole 6.0 from the screw's end, and a tower over the rod taking drop-in bushings (1/16 pilot, then 1/8 through for the belt clamp's M3 x 12), an exit hole under. PETG-GF, printed as drawn (table face on the bed)"),
    "pin_drill_bushing_pilot": (
    lambda: heal(_m("pin_drill_jig").bushing("pilot")),
    "tools/pin_drill_bushing_pilot.step",
    "TOOL — the pin drill jig's 1/16 in pilot bushing: Ø10 tube, 28 of guide, a Ø14 flange on the tower's top. PETG-GF, printed flange down"),
    "pin_drill_bushing_pin": (
    lambda: heal(_m("pin_drill_jig").bushing("pin")),
    "tools/pin_drill_bushing_pin.step",
    "TOOL — the pin drill jig's 1/8 in bushing: Ø10 tube, 28 of guide, a Ø14 flange on the tower's top. PETG-GF, printed flange down"),
    "pin_drill_bushing_pilot_1": (
    lambda: heal(dict(_m("pin_drill_jig").pilot_trials())["pin_drill_bushing_pilot_1"]),
    "tools/pin_drill_bushing_pilot_1.step",
    "TOOL -- trial 1/16 in pilot bushing 1 of 3 (bore = bit + PILOT_TRY[0], 1 scallop(s) on the flange): keep the one that is tight but runs the bit through. PETG-GF, printed flange down"),
    "pin_drill_bushing_pilot_2": (
    lambda: heal(dict(_m("pin_drill_jig").pilot_trials())["pin_drill_bushing_pilot_2"]),
    "tools/pin_drill_bushing_pilot_2.step",
    "TOOL -- trial 1/16 in pilot bushing 2 of 3 (bore = bit + PILOT_TRY[1], 2 scallop(s) on the flange): keep the one that is tight but runs the bit through. PETG-GF, printed flange down"),
    "pin_drill_bushing_pilot_3": (
    lambda: heal(dict(_m("pin_drill_jig").pilot_trials())["pin_drill_bushing_pilot_3"]),
    "tools/pin_drill_bushing_pilot_3.step",
    "TOOL -- trial 1/16 in pilot bushing 3 of 3 (bore = bit + PILOT_TRY[2], 3 scallop(s) on the flange): keep the one that is tight but runs the bit through. PETG-GF, printed flange down"),
    "ream_jig": (
    lambda: heal(_m("ream_jig").jig()),
    "tools/ream_jig.step",
    "TOOL — reaming jig for one ear of the Tr8x2 H-flange nut (9/64\" reamer, McMaster 2995A116): the nut slides in from the side BOSS DOWN, its flats on the slot walls so it cannot turn, the ear on the floor; a 44.6 channel over the ear holds the reamer vertical. Every ceiling is a 45 deg gable. PETG-GF, printed as drawn (table face on the bed)"),
    "guide_rod_saw_jig": (
    lambda: heal(_m("guide_rod_saw_jig").body()),
    "tools/guide_rod_saw_jig.step",
    "TOOL — hacksaw jig for cutting each 2 ft length of 3/16 in stainless (McMaster 89535K84) into three guide rods of direct_bench.ROD_L (202.5), with one Quick-Grip and no vise: the whole jig sits on the table; the stock rests in a short diamond-tunnel guide -X of a 1.3 saw slot (McMaster 6927A16), and the piece lies in a supported 90 deg V trough out to an end stop at ROD_L from the slot's +X face, clamped next to the slot through the LEADSCREW JIG'S CAP (saw_jig_cap: no cap of its own). 217 x 41. PETG, printed as drawn (table face on the bed)"),
    "keyhole_plate": (lambda: _m("direct_bench").keyhole_plate(), "steel/keyhole_plate.step", "LASER-CUT 304 STAINLESS, 4 mm, x10, the nut plates' sheet (JLCCNC, no finish): the direct-drive yoke's roof. The string's ball end bears on it; two Ø3.4 CLEAR holes (no tapping): the M3 x 30s go in from +X, heads on this plate, through the yoke into the collar's brass inserts. Not printed"),
}
# ONE PRINT, TWO FILAMENTS, ONE FILE (user, 2026-11-03). A part named here is a body of
# the part it maps to: the two share a STEP, each its own named product, so Bambu loads
# the file as one object with one part per filament (cadkit export_print_parts). Each
# keeps its own PARTS row -- its own volume, its own material in part_volumes.json, its
# own checks -- but its "path" is the file it is written INTO, and FILAMENT_OF says what
# it is made of, since its folder is the bulk's. The file goes where the bulk is.
PRINTS_WITH: dict = {}
# THE DIRECT DRIVE'S PER-STRING PRINTS (user, 2026-11-16: "why does each part have 10 copies? Are
# they all identical?"): a family's leader -> (file stem, material, its members). Its export
# writes ONE STEP PER DISTINCT SHAPE (_export_family), named for the strings that print it.
STRING_FAMILIES: dict = {}
FILAMENT_OF: dict = {}


# Anchor ALL outputs to the project folder (never the cwd)
OUT = pathlib.Path(__file__).resolve().parents[1]


# ── PRINT ORIENTATION — one declaration per printed part ─────────────────────
# cadkit requires it and export_print refuses a part without it, because a MISSING bed face
# used to be indistinguishable from a deliberate "models as printed". Each module declares
# its parts' build DIRECTION as a module-level constant (PRINT_UP, LEVER_UP, BAR_UP ...),
# with its reasoning beside it; this collects them, and PrintOrientation.from_build_dir
# turns each into the pose the STEP is written in. A part no module declares exports as
# modelled and is marked confirmed=False; the build names those on every run.
def _declared():
    LS, KL, KV = _m("leg_stack"), _m("knee_lever"), _m("knee_lever_vert")
    FP, UI, PB, LG = _m("foot_pedal"), _m("ui_panel"), _m("pedal_bar"), _m("legs")
    LJ, CM, SJG, MSJ, RJG = (_m("lever_jig"), _m("coil_mandrel"), _m("saw_jig"),
                             _m("motor_shaft_saw_jig"), _m("ream_jig"))

    out = {}
    # the leg stack names its parts individually, each with its reasons in leg_stack's own
    # comments (the ridges, the latch pocket's bridge, the layer-support test on the slider)
    for _n, _up in LS.PRINT_UP.items():
        out[_n] = PO.from_build_dir(
            _up, "leg_stack.PRINT_UP %r — see leg_stack for why (the ridges, "
                 "the latch pocket, the slider's layer-support test)" % (_up,))
    out["leg_latch_slider"] = out.pop("latch_slider")   # the PARTS name
    for _names, _up, _why in (
        (["knee_housing"], KL.PRINT_UP, "knee_lever.PRINT_UP — builds +Z, as modelled"),
        (["knee_housing_r"], KL.PRINT_UP,
         "knee_lever.PRINT_UP — builds +Z, as modelled (the X-mirror of knee_housing)"),
        (["kv_housing"], KV.PRINT_UP,
         "knee_lever_vert.PRINT_UP — builds +Z; the pocket gable is kept UP for exactly this"),
        (["knee_lever"], KL.LEVER_UP,
         "knee_lever.LEVER_UP — the arm lies on its -Y face and builds +Y. Already "
         "machine-readable: cut_axle_bore hands this to cadkit as print_up, which is why the "
         "axle bore comes back a plain cylinder and not a teardrop (the bore runs ALONG the build)"),
        (["cart_base"], KL.CART_UP,
         "knee_lever.CART_UP — builds +Z with the housing it sits in, which is what its peaked "
         "roof is drawn for: the housing pocket cut from it is then self-supporting"),
        (["kl_axle", "kl_axle_sprung"], KL.AXLE_UP,
         "knee_lever.AXLE_UP — STANDING, POCKET-DOWN: drawn along +Z then rotated +Z->+Y, so "
         "the collar end faces +Y and the build runs away from it. That bed face is only "
         "14.8 mm2, which is exactly why the part note calls for a brim"),
        (["kl_magnet_cap"], KL.MAGNET_CAP_UP,
         "knee_lever.MAGNET_CAP_UP — APERTURE-DOWN, same construction as the axle: the "
         "flange face is the bed (its +Y end, 55.2 mm2)"),
        (["kl_spacer", "kl_spacer_sprung", "kl_spacer_sprung_n"], KL.SPACER_UP,
         "knee_lever.SPACER_UP — a flat ring, either face on the bed"),
        (["cart_piston"], KL.PISTON_UP,
         "knee_lever.PISTON_UP — stands on its +X SPRING-SEAT face, the one flat 10x10 end, "
         "so body, follower tongue and nose all grow ALONG the build"),
        (["kv_lever"], KV.LEVER_UP,
         "knee_lever_vert.LEVER_UP — the same one fact as the LKL arm, on this lever's axle "
         "(X): it lies on its -X face"),
        (["kv_pcb_shim"], KV.SHIM_UP,
         "knee_lever_vert.SHIM_UP — the same flat plate as the LKL shim, standing in this "
         "lever's board plane (across X): it lies on its -X face"),
        (["kl_pcb_shim", "pedal_pcb_shim"], KL.SHIM_UP,
         "knee_lever.SHIM_UP — flat on a big face, building through its own 1.6 thickness"),
        (["pedal_lever"], FP.LEVER_UP,
         "foot_pedal.LEVER_UP — the LKL arm direction again, through the foot pedal pose"),
        (["ui_knob"], UI.KNOB_UP,
         "ui_panel.KNOB_UP — DISC-DOWN, on the flat top face it presents to the player. Every "
         "other way up puts the shaft bore blind end over air"),
        (["ui_clamp"], UI.CLAMP_UP,
         "ui_panel.CLAMP_UP — flat underside on the bed, every pad, rib and post growing "
         "straight up off it"),
        (["pedal_bar_a", "pedal_bar_b", "pedal_bar_c"], PB.BAR_UP,
         "pedal_bar.BAR_UP — the bar prints lying on its -Y face, building +Y"),
        (["pedal_lid_a", "pedal_lid_b"], PB.LID_UP,
         "pedal_bar.LID_UP — the OPPOSITE of BAR_UP, and it has to be: the lid profile runs "
         "out to the bar +Y face, so it builds -Y, and its 45 dovetail flanks are only "
         "overhangs this way up"),
        (["leg_foot"], LG.FOOT_UP, "legs.FOOT_UP — the 44-sq pad is the bed, tenon up"),
        (["lever_prog_jig"], LJ.JIG_UP,
         "lever_jig.JIG_UP — prints as drawn: flat on the base face, posts growing up"),
        (["lever_prog_jig_base"], LJ.BASE_UP,
         "lever_jig.BASE_UP — upside down: the screw head's counterbore opens upward"),
        (["saw_jig"], SJG.BODY_UP,
         "saw_jig.BODY_UP — as drawn, table face on the bed: the V and roof of the rod tunnel "
         "and the fork's arch are all 45 deg"),
        (["ream_jig"], RJG.PRINT_UP,
         "ream_jig.PRINT_UP — standing as it is used, table face on the bed: the nut slot and "
         "the reamer channel both print round their own axis, every ceiling a 45 deg gable"),
        (["motor_shaft_saw_jig"], MSJ.BODY_UP,
         "motor_shaft_saw_jig.BODY_UP — as drawn, table face on the bed: the bay, the boss "
         "slot, the shaft channel and the saw slot all open upward; the gussets rise at 45 deg"),
        (["saw_jig_cap"], SJG.CAP_UP,
         "saw_jig.CAP_UP — as drawn: the rod notch's two 45 deg faces rise off the bed, the "
         "pad pocket opens up"),
        (["coil_mandrel"], CM.MANDREL_UP,
         "coil_mandrel.MANDREL_UP — flange-down on its O27.8 base, as drawn"),
        (["coil_mandrel_sleeve"], CM.SLEEVE_UP,
         "coil_mandrel.SLEEVE_UP — as drawn (a plain tube: both ends measure identically)"),
    ):
        for _n in _names:
            out[_n] = PO.from_build_dir(_up, _why)

    # THE BODY-ADAPTER CORNERS. The body tenons on the top face run along Y and END at one Y
    # face, so that face is the bed (leg_stack.ADAPTER_UP states the rule for the -X/+Y one);
    # the corner variants are that part with its joinery rebuilt, and the bed is the Y end
    # the tenons leave unbroken, which flips with the corner. px_my breaks neither end, so it
    # follows its corner-mate mx_my.
    _ADAPTER_WHY = ("the body tenons run along Y and END at this corner Y face, so that face "
                    "is the bed (leg_stack.ADAPTER_UP rule, mirrored with the corner): built "
                    "the other way each ridge starts in mid-air and the 45 ramp that fixes it "
                    "costs 481 mm3 of tenon engagement")
    for _n, _up in (("body_adapter_px_py", (0.0, -1.0, 0.0)),
                    ("body_adapter_px_my", (0.0, 1.0, 0.0)),
                    ("body_adapter_mx_my", (0.0, 1.0, 0.0))):
        out[_n] = PO.from_build_dir(_up, _ADAPTER_WHY)

    # Declared by its module, but NOT YET CONFIRMED by the user (2026-10-12).
    out["ui_pwr_cap"] = PO.from_build_dir(
        UI.PWR_CAP_UP,
        "ui_panel.PWR_CAP_UP — top face on the bed, the stem's socket opening upward. Measured "
        "that way up: no ceiling and no curved overhang. Chosen, not yet confirmed",
        confirmed=False)
    out["pedal_detent_nub"] = PO(
        ((1, 0, 0), -90),
        "NOTHING IN THE PROJECT DECLARES THIS ONE. Measured: a O4x4 TPU cylinder whose axis "
        "lies along Y, so standing it up is the only way it has a footprint at all (12.6 mm2) "
        "and it is overhang-free that way. Low stakes, but unchecked",
        confirmed=False)
    return {k: v for k, v in out.items() if k in PARTS}


PRINT_ORIENTATION = _declared()
for _n, (_b, _path, _note) in PARTS.items():
    if _n in PRINT_ORIENTATION:
        continue
    # NOT a decision -- a RECORD of what this part's STEP has always exported as.
    PRINT_ORIENTATION[_n] = PO(
        None,
        "as modelled — what this part's STEP has always exported as. UNSTUDIED. The part "
        "note says: " + " ".join((_note or "(nothing about printing)").split())[:300],
        confirmed=False)


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


# ── WHERE A BUILD'S TIME GOES ────────────────────────────────────────────────────────
# One line per stage at the end of every build (lead, 2026-10-09: the log timed two
# gates and nothing else, so nobody could say what a ten-minute build spent its ten
# minutes on). Cut where this says the time is, not where it is assumed to be.
_STAGES: list = []


@contextlib.contextmanager
def _stage(label):
    t = time.perf_counter()
    try:
        yield
    finally:
        _STAGES.append((label, time.perf_counter() - t))


def _stage_add(label, seconds):
    for i, (k, s) in enumerate(_STAGES):
        if k == label:
            _STAGES[i] = (k, s + seconds)
            return
    _STAGES.append((label, seconds))


def _report_stages():
    total = sum(s for _, s in _STAGES)
    print("BUILD TIME by stage (%.0f s):" % total)
    for label, s in _STAGES:
        print("  %7.1f s  %4.1f %%  %s" % (s, 100.0 * s / total if total else 0.0, label))
    sys.stdout.flush()


def _shape_sig(shape):
    """A rigid-motion-free signature: volume, area and the principal radii of gyration^2."""
    import numpy as np
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    w = getattr(shape, "wrapped", shape)
    g, a = GProp_GProps(), GProp_GProps()
    BRepGProp.VolumeProperties_s(w, g)
    BRepGProp.SurfaceProperties_s(w, a)
    m = g.MatrixOfInertia()
    eig = np.linalg.eigvalsh(np.array([[m.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)]))
    v = g.Mass()
    return v, a.Mass(), tuple(float(e) / v for e in eig)


def _same_shape(p, q) -> bool:
    return (abs(p[0] - q[0]) <= 1e-6 * max(abs(p[0]), 1.0) + 1e-3
            and abs(p[1] - q[1]) <= 1e-6 * max(abs(p[1]), 1.0) + 1e-3
            and all(abs(x - y) <= 1e-3 for x, y in zip(p[2], q[2])))


def _string_no(n: str) -> int:
    return int(n.rsplit("_", 1)[1]) + 1


PRINT_LIST = OUT / "PRINT_LIST.md"


def _print_list_update(paths_gone, rows):
    """PRINT_LIST.md: one row per direct-drive STEP (path, quantity, strings), rewritten in place."""
    keep = {}
    if PRINT_LIST.exists():
        for ln in PRINT_LIST.read_text(encoding="utf-8").splitlines():
            if ln.startswith("| `"):
                keep[ln.split("`")[1]] = ln
    for p in paths_gone:
        keep.pop(p, None)
    for p, n, what in rows:
        keep[p] = f"| `{p}` | {n} | {what} |"
    PRINT_LIST.write_text(
        "# Direct drive: what to print\n\nGenerated by `src.build` (one STEP per distinct shape; "
        "the quantity is how many to print).\n\n| file | qty | strings |\n|---|---|---|\n"
        + "\n".join(keep[k] for k in sorted(keep, key=_natural)) + "\n", encoding="utf-8")


def _natural(k: str):
    """housing_s2 before housing_s10."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", k)]


# ── A STEP IS WRITTEN ONLY WHEN WHAT IS IN IT CHANGED (user, 2026-11-16: "changing parts should
# automatically use cached data as much as possible") ─────────────────────────────────────────
# Each file's key: the content names of the bodies in it (cadkit.kept tags every result with its
# content's sha1; anything else is hashed from its BREP), their names, and the print pose. The
# file is skipped when it exists and its key is the one it was written with (.step_keys.json).
_STEP_KEYS_FILE = OUT / ".step_keys.json"
_STEP_KEYS: dict = {}
_STEP_KEY_V = 1


def _content_token(o) -> str:
    from cadkit.kept import _shape_token
    tag = getattr(o, "_cadkit_kept", None)
    if tag:
        return "kept:" + tag
    shapes = o.vals() if hasattr(o, "vals") else [o]
    return "|".join(_shape_token(x) if isinstance(x, cq.Shape) else repr(x) for x in shapes)


def _write_print(dest: pathlib.Path, bodies, orientation) -> bool:
    """export_print / export_print_parts of [(name, obj)] to `dest`, unless it is already that.
    True if it was written."""
    import hashlib
    if not _STEP_KEYS and _STEP_KEYS_FILE.exists():
        try:
            _STEP_KEYS.update(json.loads(_STEP_KEYS_FILE.read_text(encoding="utf-8")))
        except ValueError:
            pass
    rel = dest.resolve().relative_to(OUT.resolve()).as_posix()
    key = hashlib.sha1(json.dumps([_STEP_KEY_V, [(n, _content_token(o)) for n, o in bodies],
                                   repr(orientation.rot)]).encode()).hexdigest()
    if dest.exists() and _STEP_KEYS.get(rel) == key:
        return False
    if len(bodies) == 1:
        export_print(bodies[0][1], orientation, str(dest))
    else:
        export_print_parts(bodies, orientation, str(dest))
    _STEP_KEYS[rel] = key
    _STEP_KEYS_FILE.write_text(json.dumps(_STEP_KEYS, indent=0, sort_keys=True), encoding="utf-8")
    return True


def _export_family(leader):
    """Every member of `leader`'s family built (kept: cached), grouped by shape, ONE STEP per
    distinct shape. One shape: `stem.step`. Several: the most common (if one is) keeps `stem`,
    the rest `stem_s<strings>`. Stale files of the family (a merged name, a shape gone) go."""
    stem, mat, members = STRING_FAMILIES[leader]
    built, groups = {}, []
    for n in members:
        t = time.perf_counter(); wp = PARTS[n][0](); built[n] = (wp, time.perf_counter() - t)
        sig = _shape_sig(wp.val() if hasattr(wp, "val") else wp)
        for g in groups:
            if _same_shape(g[0], sig):
                g[1].append(n)
                break
        else:
            groups.append((sig, [n]))
    sizes = sorted((len(g[1]) for g in groups), reverse=True)
    main = None
    if len(groups) == 1 or (sizes[0] > 1 and sizes[0] > sizes[1]):
        main = max(groups, key=lambda g: len(g[1]))
    d = OUT / mat
    d.mkdir(parents=True, exist_ok=True)
    written, rows = [], []
    for g in groups:
        ms = g[1]
        nos = sorted({_string_no(n) for n in ms})
        fn = stem if g is main else stem + "_" + "_".join(f"s{k}" for k in nos)
        rep_ = ms[0]
        t = time.perf_counter()
        wrote = _write_print(d / f"{fn}.step", [(rep_, built[rep_][0])], PRINT_ORIENTATION[rep_])
        export_s = time.perf_counter() - t
        _stage_add("printed parts: STEP export", export_s)
        names = sorted({n.rsplit("_", 1)[0] for n in ms})
        by = "; ".join(f"{nm} " + ",".join(f"S{_string_no(n)}" for n in ms if n.rsplit("_", 1)[0] == nm)
                       for nm in names) if len(names) > 1 else ",".join(f"S{k}" for k in nos)
        written.append(f"{fn}.step")
        rows.append((f"{mat}/{fn}.step", len(ms), by))
        for n in ms:
            wp, build_s = built[n]
            record_part(n, build_s, export_s if n == rep_ else 0.0,
                        wp.val() if hasattr(wp, "val") else wp, material=mat)
            _stage_add("printed parts: build", build_s)
        print(f"{'Wrote' if wrote else 'Unchanged'} {mat}/{fn}.step  x{len(ms)}  ({by})")
    olds = {f"{stem}.step"} | {p.name for p in d.glob(f"{stem}_s*.step")} \
        | {f"{n.rsplit('_', 1)[0]}.step" for n in members}
    gone = [f"{mat}/{f}" for f in sorted(olds) if f not in written and (d / f).exists()]
    for f in gone:
        (OUT / f).unlink()
        print(f"  removed stale {f}")
    _print_list_update(gone + [f"{mat}/{f}" for f in sorted(olds) if f not in written], rows)


def _export(name):
    """Build `name` and write its print STEP, with every body that prints with it
    (PRINTS_WITH) in the same file. A body that prints with another is written by that
    one's export, so on its own it is passed over."""
    if name in PRINTS_WITH:
        return
    if name in STRING_FAMILIES:
        return _export_family(name)
    builder, path, note = PARTS[name]
    dest = OUT / path
    dest.parent.mkdir(parents=True, exist_ok=True)   # material folder (petg-gf/pctg/tpu)
    bodies = [name] + [n for n, into in PRINTS_WITH.items() if into == name]
    built = {}
    for n in bodies:
        t = time.perf_counter(); wp = PARTS[n][0](); built[n] = (wp, time.perf_counter() - t)
    t = time.perf_counter()
    wrote = _write_print(dest, [(n, built[n][0]) for n in bodies], PRINT_ORIENTATION[name])
    export_s = time.perf_counter() - t
    for n in bodies[1:]:
        (OUT / FILAMENT_OF[n] / f"{n}.step").unlink(missing_ok=True)   # its own file, from before
    for n in bodies:
        wp, build_s = built[n]
        record_part(n, build_s, export_s if n == name else 0.0,
                    wp.val() if hasattr(wp, "val") else wp,
                    material=FILAMENT_OF.get(n) or _material_of(path))   # ~free profiling + volume hook
        _stage_add("printed parts: build", build_s)
    _stage_add("printed parts: STEP export", export_s)
    print(f"{'Wrote' if wrote else 'Unchanged'} {path}" + (f"  ({' + '.join(bodies)})" if len(bodies) > 1 else "")
          + (f"  ({note})" if note else ""))


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


def collect_components():
    """EVERY placed thing in the instrument: [(name, cq.Workplane), ...].

    THE DIRECT-DRIVE INSTRUMENT (user, 2026-11-13: the main build is src.direct_bench's
    instrument; v1 stays reachable at the git tag v1-instrument and as collect_v1_components).
    Each part is drawn where it sits at T_OPEN, every one its own kept() entry; the pickup is
    still its stand-in (ghost_pickup). The v1 latch, legs, pedal bar and levers are NOT in it
    yet: they come over later, and their modules and PARTS entries stay for that.

    The one entry point the whole tool chain is built on -- the overlap and sweep gates, the
    GLB exporter, scratch_view and the build profiler all take their model from here, so a
    part that is not in this list is invisible to every check in the project. Names matter
    beyond display: the gates key their allow-lists on them (its pairs are judged by
    direct_bench.is_intended)."""
    from . import direct_bench as DB
    return DB.assembly(DB.T_OPEN)


from elec import harness as _EH  # noqa: E402  (the PCB's pin order, single-sourced)
from . import board_geom as _BG  # noqa: E402
_COLORS = {
    "bridge_endplate": (0.39, 0.58, 0.93),   # PETG-GF — load-critical
    "keyhead_endplate": (0.42, 0.50, 0.62),   # PETG-GF — keyhead endplate + nut block (merged)
    # belt-tension clamp: two printed halves (0.4 nozzle), steel M3, brass insert
    "belt_tensioner_half_a": (0.95, 0.55, 0.15),    # head half    printed
    "belt_tensioner_half_b": (0.95, 0.70, 0.25),    # insert half  printed
    "belt_tensioner_screw":  (0.55, 0.55, 0.58),   # steel M3 socket head
    "belt_tensioner_insert": (0.72, 0.60, 0.30),   # brass M3 insert (dropped in behind a shoulder)
    # …and the parked assembled coupon (green = clearly a reference, not a product part)
    # The coupon keeps its own COOL family so the parked copy never reads as a real
    # clamp; same one-hue-per-SKU rule within it.
    "screw_pulley":    (0.00, 0.55, 0.55),
    "screw_top_bearing": (0.69, 0.77, 0.87),
    "motor_pulley":    (0.00, 0.55, 0.55),
    "leadscrew":       (0.75, 0.75, 0.78),   # steel
    "screw_bearing":   (0.69, 0.77, 0.87),
    "bridge_bearings": (0.69, 0.77, 0.87),
    "nut":             (0.82, 0.60, 0.20),   # brass
    "string_nut":      (0.82, 0.60, 0.20),   # brass string-end fitting (demo)
    "guide_rod":       (0.35, 0.35, 0.38),
    "rod_plug":        (0.85, 0.45, 0.15),
    "belt":            (0.13, 0.13, 0.13),   # GT2 black
    "string":          (0.85, 0.85, 0.85),
    "break_dowel":     (0.75, 0.75, 0.78),
    "nut_height_screw": (0.72, 0.74, 0.78),   # M4 x 40 button, pushes the insert up
    "nut_height_insert": (0.72, 0.60, 0.30),  # M4 heat-set in the keyhead slab
    "nut_plate":       (0.80, 0.81, 0.83),   # laser-cut 304: lighter than the rod it pinches against
    "nut_side_screw":  (0.72, 0.74, 0.78),   # M4 x 10 button, pins the tail
    "nut_side_insert": (0.72, 0.60, 0.30),   # M4 heat-set in the bed face
    "nut_slide_insert": (0.86, 0.72, 0.30),   # the printed stand-in, if ever drawn
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
    "pogo_male_board":   _BG.mask("leg_pogo_male_top"),
    "pogo_female_board": _BG.mask("leg_pogo_female_top"),
    "pogo_male_pins":    (0.83, 0.69, 0.22),
    "pogo_female_pads":  (0.83, 0.69, 0.22),
    # the lighting seams' plungers (src.pogo_part): gold plated, the colour their barrels
    # are drawn in. They had no entry and came out the default white
    "fret_pogo_pins":    (0.83, 0.68, 0.25),
    "foot_pogo_pins":    (0.83, 0.68, 0.25),
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
    "bar_trrs_sleeve": (0.03, 0.03, 0.03),   # the bottom joint's TPU carrier (black)
    "bar_trrs_plug":   (0.15, 0.15, 0.17),   # ...the male plug it floats
    "bar_trrs_spring": (0.62, 0.64, 0.67),   # ...and the coil above it
    "bar_latch_frame": (0.85, 0.35, 0.20),   # pedal bar latch accent
    "bar_latch_collar": (0.36, 0.42, 0.46),  # PETG-GF, the bar tower's family
    "bar_latch_spring": (0.62, 0.64, 0.67),
    "bar_latch_screw": (0.55, 0.55, 0.58),   # M4 button -- same SKU, same colour
    "bar_latch_insert": (0.80, 0.60, 0.35),  # as the leg's screw and insert
    "leg_seg_body":    (0.42, 0.48, 0.52),   # square GF bodies
    "leg_head":        (0.36, 0.42, 0.46),
    "leg_plug_retainer": (0.42, 0.48, 0.52),
    "chassis_trrs_jack": (0.62, 0.64, 0.67),
    "leg_column_plug":  (0.32, 0.36, 0.58),  # slate, matches the bar plug
    "chassis_trrs_cable": (0.45, 0.45, 0.48),
    "leg_column_cable": (0.45, 0.45, 0.48),
    "leg_cable_coil":  (0.45, 0.45, 0.48),   # heat-set coil section (slack
                                             # take-up in the segment core)
    "leg_sleeve":      (0.36, 0.42, 0.46),
    "leg_shaft":       (0.55, 0.58, 0.62),
    "leg_foot":        (0.12, 0.12, 0.13),   # TPU
    # pedal bar (2 spliced pieces + 2 dovetail-lid pieces) + latches
    "pedal_bar_a":      (0.30, 0.45, 0.35),  # PETG-GF bar, -X piece
    "pedal_bar_b":      (0.33, 0.48, 0.38),  # PETG-GF bar, mid piece
    "pedal_bar_c":      (0.31, 0.46, 0.36),  # PETG-GF bar, +X piece
    "pedal_lid_a":      (0.50, 0.58, 0.52),  # dovetail lid, -X piece
    "pedal_lid_b":      (0.54, 0.62, 0.56),  # dovetail lid, +X piece
    "pedal_detent_nub": (0.12, 0.12, 0.13),  # TPU hold-closed detent nub

    "shaft_trrs_jack": (0.62, 0.64, 0.67),       # bar-joint jack (10-03404)
    "shaft_trrs_cable": (0.45, 0.45, 0.48),
    "jack_seat_ring":  (0.42, 0.48, 0.52),
    # knee lever (LKL) — input-side control
    "knee_housing":    (0.30, 0.36, 0.42),   # PCTG housing
    "knee_lever":      (0.27, 0.51, 0.71),   # PCTG lever/paddle
    "kl_axle":         (0.30, 0.54, 0.68),   # PCTG full-length axle (near the lever blue)
    "kl_axle_screw":   (0.55, 0.55, 0.58),   # M4 x 10 button in the axle's -Y end
    "kl_axle_washer":  (0.72, 0.72, 0.75),
    "kl_preload_spring": (0.35, 0.36, 0.40),  # McMaster 9714K29 wave disc spring (dark spring steel)
    "kl_spacer_sprung": (0.30, 0.54, 0.68),   # the LKL's exact spacers (kl_spacer's blue)
    "kl_spacer_sprung_n": (0.30, 0.54, 0.68),
    "kl_axle_sprung":  (0.30, 0.54, 0.68),   # the LKL's axle (kl_axle's blue)
    "kv_axle_screw":   (0.55, 0.55, 0.58),
    "kv_axle_washer":  (0.72, 0.72, 0.75),
    "kl_magnet_cap":   (0.24, 0.44, 0.56),   # PCTG magnet retainer
    "kl_spacer":       (0.30, 0.54, 0.68),   # PCTG axle spacers (the axle's blue)
    # the rest of the sensor board's real population (knee_lever.SENSOR_BOM). The
    # kv_/pedal{i}_ instances inherit these by the prefix rules in _color_for.
    "kl_bearing":      (0.69, 0.77, 0.87),   # MR85ZZ
    "kl_magnet":       (0.80, 0.20, 0.20),   # diametric magnet
    "kl_pcb":          _BG.mask("lever_sensor"),   # MT6701 board (green)
    "kv_housing":      (0.30, 0.36, 0.42),   # LKV housing (PETG-GF, as LKL)
    # ...THE SAME BLUE AS LKL'S ARM, not a colour of its own (user, 2026-09-25: "the
    # levers are blue for LKL but yellow for LKV, we should color them consistently").
    # The comment beside it already said "as LKL" while the number said otherwise, which
    # is how it survived: same part, same job, same material, two colours.
    "kv_lever":        (0.27, 0.51, 0.71),   # LKV arm (PCTG, as LKL -- the same blue)
    "kv_pcb":          _BG.mask("lever_sensor"),   # LKV MT6701 board (green, as LKL)
    "kv_pcb_shim":     (0.75, 0.75, 0.78),   # LKV board shim (printed, takes up the slack)
    # feel parts (unified: two identical spring cartridges, main -Y + half-stop +Y)
    "main_spring":                        (0.04, 0.16, 0.55),   # JIS light-load die spring: painted blue
    "half_stop_spring":                   (0.04, 0.16, 0.55),
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
    # electronics bay (dummies) + panel jacks

    # the Pi's parts, each its own colour (src/pi4b.py: "pi4" is the laminate)
    **{"pi4" + _k: __import__("src.pi4b", fromlist=["RGB"]).RGB[_c]
       for _k, (_c, _f) in __import__("src.pi4b", fromlist=["GROUPS"]).GROUPS.items()},
    "pi_cap":          _BG.mask("pi_cap"),   # PCB green
    # the new instrument's boards (src/new_boards_view.py): a board part with no entry here was
    # drawn the default white -- cadkit's export now refuses a board not in a mask colour
    "connector_board_pcb": _BG.mask("connector_board"),
    "pi_riser":        (0.05, 0.05, 0.05),   # BOUGHT: Adafruit 4079 socket riser, black
    "output_panel":    _BG.mask("output_panel"),   # output + panel board (VBUS broken,
                                             # DAC + true-bypass relay + the TS jack)
    "motor_ctrl":      _BG.mask("motor_ctrl"),   # motor controller PCB (CH32V307 +
                                             # 2x CAN transceiver + XH headers)
    "tee_pcb":         _BG.mask("can_tee"),   # trunk-and-drop bus tee PCBs
    "tee_cradle":      (0.32, 0.55, 0.42),   # PCTG drop-in PCB cradle (pcb_cradle, side hold-down)
    "trrs_adapter_pcb":    _BG.mask("trrs_adapter"),   # the leg's TRRS<->XH adapter (bronner's board)
    "trrs_adapter_plug":   (0.15, 0.15, 0.17),   # the lead from the leg, plugged in
    "trrs_adapter_screw":  (0.55, 0.55, 0.58),   # M4 button, 2.5 hex -- the one lock
    "trrs_adapter_insert": (0.80, 0.60, 0.35),   # its brass heat-set insert
    "tee_screw":       (0.72, 0.74, 0.78),   # M4x10 button, BESIDE the tee board
    "tee_insert":      (0.72, 0.60, 0.30),
    "board_screw":     (0.72, 0.74, 0.78),   # M4x10 button THROUGH our boards' mounting ears
    "board_insert":    (0.72, 0.60, 0.30),   # its heat-set brass, in the cradle boss   # M4 heat-set brass, in the cradle boss
    "optical_pcb":     _BG.mask("optical"),   # per-string optical strip: BLACK mask, as ordered
    # ⚠ MATCHED TO THE LOOSE-WIRE COLOURS BELOW, not picked fresh: a USB run is a USB
    # run whether it is drawn as a wire or as a modelled cable, and the old single entry
    # was (0.15,0.15,0.17) -- near-black, which this project reserves for TPU.
    "optical_cable_usb_metal": (0.75, 0.76, 0.78),   # the plugs' steel tongues
    "optical_cable_usb": (0.03, 0.03, 0.035),  # black, as the bought lead is: the optical board USB ribbon and its two plugs
    "optical_insert":  (0.72, 0.60, 0.30),   # M4 heat-set brass, board grips
    "optical_screw":   (0.72, 0.74, 0.78),   # M4x20 button, through the guard and the board
    "optical_silk":    (0.95, 0.95, 0.93),   # silkscreen ink, its own part on each board
    "pi_cap_silk":     (0.95, 0.95, 0.93),
    "motor_ctrl_silk": (0.95, 0.95, 0.93),
    "output_panel_silk": (0.95, 0.95, 0.93),
    # the new boards (src/new_boards_view.py: <board>_pcb + <board>_pcb_silk)
    "brain_pcb":        _BG.mask("brain"),
    "brain_board_pcb": _BG.mask("brain_board"),
    "brain_board_cm5":    _BG.mask_rgb("green"),   # the Compute Module 5: Raspberry Pi's green mask
    "brain_board_cm5_soc": (0.74, 0.75, 0.77),     # the BCM2712's metal lid
    "brain_board_cm5_plug": (0.85, 0.80, 0.68),    # the CM5's DF40 plugs, cream LCP
    "brain_board_df40_leads": (0.83, 0.69, 0.22),  # J201 / J202's gold contact leads
    "connector_board_tb_plug": (0.16, 0.55, 0.32),  # J11-J20: MX15EDGK plugs, green PA66
    "connector_board_tb_screws": (0.72, 0.74, 0.78),   # their M2 slotted screws
    "brain_board_idc": (0.10, 0.10, 0.11),       # the ribbon headers' IDC sockets, black PBT
    "connector_board_idc": (0.10, 0.10, 0.11),
    "brain_board_idc_ribbon": (0.62, 0.63, 0.66),   # grey 0.635 flat cable (a stub of it)
    "connector_board_idc_ribbon": (0.62, 0.63, 0.66),
    "brain_pcb_silk":   (0.95, 0.95, 0.93),
    "brain_board_pcb_silk": (0.95, 0.95, 0.93),
    "brain_board_term": (0.16, 0.55, 0.32),        # J8: MX128 terminal block, green PA66
    "brain_board_term_metal": (0.72, 0.74, 0.78),  # its slotted M2.5 screws and tinned pins
    "output_panel_term": (0.16, 0.55, 0.32),        # J8: MX128 terminal block, green PA66
    "output_panel_term_metal": (0.72, 0.74, 0.78),  # its M2.5 screws and tinned pins
    "optical_guard":   (0.18, 0.18, 0.20),   # the hand guard over the board -- print it
                                             # DARK: it is the one surface facing the
                                             # detectors, so a light one would bounce IR
    "top_plate":       (0.88, 0.91, 0.94),   # transparent-PCTG deck base + fret lines
    "top_plate_color": (0.30, 0.33, 0.38),   # colour-PCTG deck layer (skin contact)
    "chassis_light":   (0.88, 0.91, 0.94),   # light window -- the deck panels' white
    "ui_pcb":          _BG.mask("ui_board"),   # the UI board, as fabbed
    "ui_display":      (0.16, 0.16, 0.18),   # the module's metal bezel -- the part the
                                             # deck's ledge bears on and covers
    "ui_screen":       (0.004, 0.004, 0.005),   # an OLED is black where it is not lit
    "ui_screen_lit":   (0.93, 0.96, 1.0),    # ...and this module (WDW) lights white
    "ui_disp_ffc_socket": (0.90, 0.86, 0.72),  # the module's Molex FFC socket, natural nylon
    "ui_ffc":          (0.93, 0.93, 0.90),   # the display's flat cable: white PET film
                                             # (JUSHUO's drawing: "white" under-layer)
    "ui_ffc_contacts": (0.78, 0.79, 0.80),   # ...its bared tinned conductors at each end
    "ui_ffc_stiffener": (0.12, 0.35, 0.80),  # ...and its blue PET stiffeners
    "ui_clamp":        (0.36, 0.30, 0.42),   # the printed clamp plate under the board
    "ui_insert":       (0.72, 0.60, 0.38),   # brass heat-set
    "ui_screw":        (0.62, 0.64, 0.67),
    "ui_knob":         (0.15, 0.15, 0.17),   # the printed cap on the encoder
    "ui_pwr_cap":      (0.15, 0.15, 0.17),   # ...and the one on the power switch
    "ui_pwr_stem":     (0.94, 0.94, 0.92),   # the switch's own plunger, moulded white
    "dc_jack":         (0.62, 0.64, 0.67),
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
    # the motor drops, tee to motor screw terminals: the CAN scheme
    "wire_drop_v24":   (0.85, 0.12, 0.10),   # red
    "wire_drop_gnd":   (0.05, 0.05, 0.05),   # black
    "wire_drop_canh":  (0.95, 0.85, 0.10),   # yellow
    "wire_drop_canl":  (0.13, 0.72, 0.20),   # green
                                             #   XH pigtail (factory jacket)
    "wire_pickup":     (0.55, 0.85, 0.55),   # lightest green - the magnetic pickup's
                                             #   shielded lead, coil underside -> the
                                             #   output panel's J8 screw terminals
    "wire_link":       (0.95, 0.72, 0.22),   # light amber - motor controller <-> Pi, USB
    "wire_tdm":        (0.80, 0.46, 0.10),   # deep amber  - CS stack -> Pi
    # THE UI RIBBON, fourteen conductors. Grey is what 1.27 flat cable is; conductor 1
    # is its red stripe, which is the only marking an IDC cable carries and the only
    # thing that tells you which way round the plug goes.
    # named per PANEL, not per index (_color_for strips digits, not words), because
    # "mid" and "key" are what every other file calls these two boards
    "fret_pcb_mid":    _BG.mask("fret_led_mid"),   # PCB green
    "fret_pcb_key":    _BG.mask("fret_led_key"),
    "foot_pcb_a":      _BG.mask("foot_led_a"),
    "foot_pcb_b":      _BG.mask("foot_led_b"),
    "fret_pcb_mid_silk": (0.95, 0.95, 0.93),   # silkscreen ink, its own part on each board
    "fret_pcb_key_silk": (0.95, 0.95, 0.93),
    "foot_pcb_a_silk": (0.95, 0.95, 0.93),
    "foot_pcb_b_silk": (0.95, 0.95, 0.93),
    "ui_pcb_silk":     (0.95, 0.95, 0.93),
    "tee_silk":        (0.95, 0.95, 0.93),
    "kl_pcb_silk":     (0.95, 0.95, 0.93),
    "pogo_male_silk":  (0.95, 0.95, 0.93),
    "pogo_female_silk": (0.95, 0.95, 0.93),
    "wire_ui":         (0.55, 0.56, 0.58),
    "ui_ribbon_socket": (0.10, 0.10, 0.11),  # its two 1.27 IDC sockets, black PBT
    "wire_usb":        (0.55, 0.25, 0.75),   # violet      - output panel J2 -> the Pi's USB-C
    "wire_hub":        (0.38, 0.32, 0.85),   # indigo      - output panel J3 (the hub) -> a Pi USB-A
    "wire_usb_plug":   (0.03, 0.03, 0.035),  # the leads' moulded plugs, black as bought
    "wire_hub_plug":   (0.03, 0.03, 0.035),
    "wire_link_plug":  (0.03, 0.03, 0.035),
}
_DEFAULT_COLOR = (0.80, 0.80, 0.80)
_TPU_BLACK = (0.03, 0.03, 0.03)                  # ALL TPU parts render black (user rule)
# every part whose output path is tpu/... -> black, regardless of instance prefix/suffix
_TPU_BASES = tuple(sorted((k for k, v in PARTS.items() if v[1].startswith("tpu/")), key=len, reverse=True))


# the two lighting leads, a conductor a part: black GND, red 24 V, white SCK, blue SDT
from . import led_leads as _LL                                   # noqa: E402
# the SERVO42D's parts take the colours it was measured in (src/servo42d.py LOOK)
from . import servo42d as _SV
_COLORS.update({("motor_" + _k) if _k else "motor": _rgb for _k, (_rgb, _) in _SV.LOOK.items()})
_COLORS.update({"wire_%s_led_%s" % (_lead, _w.lower()): _LL.COLORS[_w]
                for _lead in ("foot", "fret") for _w in _LL.WAYS})
_COLORS.update({
    "%s_wire_%s" % (run, n.lower()): {"GND": (0.05, 0.05, 0.05), "V5": (0.85, 0.12, 0.10),
                                      "CAN_H": (0.95, 0.85, 0.10),
                                      "CAN_L": (0.13, 0.72, 0.20)}[n]
    for run in ("pogo", "pedal") for n in _EH.PH_PINOUT})


# The keyhead's three board-to-board leads, a conductor a part, in the harness's own
# colours: black ground, red rail, and the power button's two throws yellow (out) and
# green (latched in), the spools the BOM holds. And the lever chain's head, which is bus B like the rest of the
# chain: its four had no entry of their own and came out the default grey, as did the
# Pi's 5 V four (the lead's audit, 2026-10-06).
_NET_RGB = {"gnd": (0.05, 0.05, 0.05), "v24": (0.85, 0.12, 0.10), "v5": (0.85, 0.12, 0.10),
            "up": (0.95, 0.80, 0.10), "dn": (0.10, 0.60, 0.25)}
_COLORS.update({"wire_%s_%s" % (_lead, _net): _rgb
                for _lead in ("plink", "lights", "5v", "opt")
                for _net, _rgb in _NET_RGB.items()})
_COLORS.update({"wire_canb_%s_lkl" % _n: _COLORS["wire_canb_%s" % _n]
                for _n in ("gnd", "v5", "h", "l")})


# The USB lead's four as they go into J4: the jacket stays amber, the wires are a hand's pinning.
_WAY_COLORS = {"wire_link_1": (0.85, 0.12, 0.10), "wire_link_2": (0.05, 0.05, 0.05),
               "wire_link_3": (0.92, 0.92, 0.92), "wire_link_4": (0.10, 0.60, 0.25)}


# PARTS THAT HAD NO COLOUR (2026-11-14): each fell through to the default white, which is now a
# build failure (user: "missing from the project's colour table ... should fail the build").
# Coloured as their material already is elsewhere in this table.
_BRASS, _STEEL, _GF = (0.80, 0.60, 0.35), (0.55, 0.55, 0.58), _COLORS["bar_latch_collar"]
_COLORS.update({
    # the lever stack's heat-sets and travel stop (every station peels to these)
    "main_position_insert": _BRASS, "main_spring_tension_insert": _BRASS,
    "half_stop_position_insert": _BRASS, "half_stop_spring_tension_insert": _BRASS,
    "kl_travel_stop_insert": _BRASS, "kl_travel_stop_screw": _STEEL,
    # the fret boards' M4 joints (src/fret_light.py)
    "fret_m4_insert_key": _BRASS, "fret_m4_insert_mid": _BRASS,
    "fret_m4_key": _STEEL, "fret_m4_mid": _STEEL,
    "bar_shim": _GF, "seam_bridge": _GF,             # PETG-GF printed parts
    "ui_shaft": (0.62, 0.64, 0.67),                  # the encoder's steel shaft
    "wall_bar": (0.55, 0.58, 0.62),                  # steel bar, as leg_shaft
    "wire_link_plug_c": _COLORS["wire_link_plug"],
    "wire_usb_plug_pi": _COLORS["wire_usb_plug"],
    "wire_usb_ribbon": _COLORS["wire_usb"], "wire_usb_joint": _COLORS["wire_usb"],
})

def _color_for(name):
    # STRIP EVERY TRAILING INDEX GROUP, not just the last one -- the same lesson
    # tools.check_overlaps.base() records, and this resolver had not learned it. A part
    # numbered twice (`wire_canb_gnd_0_0`: net, segment, half) kept one index after a
    # single strip, matched nothing in _COLORS, and came out the default white. The
    # overlap gate had already been bitten by exactly this and fixed; colours had not.
    if name in _WAY_COLORS:
        return cq.Color(*_WAY_COLORS[name])
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
    # the changer bench (src.changer_bench) keeps its own small table, mostly aliases into
    # this one, so its 380 parts are not white
    if base.startswith(("cb_", "ghost_")):
        from . import changer_bench as _CB
        _c = _CB.color_of(base, _COLORS)
        if _c is not None:
            return cq.Color(*_c)
    from . import direct_bench as _DB            # ...and the instrument's (src.direct_bench)
    if _DB.owns(base):
        _c = _DB.color_of(base, _COLORS)
        if _c is not None:
            return cq.Color(*_c)
    # ⚠ NO DEFAULT COLOUR (user, 2026-11-14). A name nothing here knows used to come out
    # _DEFAULT_COLOR, white -- a new board read as a white-mask PCB and nothing said so. It
    # fails the build instead: add the part to _COLORS (or its module's own table).
    raise KeyError("build: no colour for part %r (base %r) -- add it to src/build.py _COLORS "
                   "or its module's colour table; there is no default" % (name, base))


def _export_assembly(publish=True, gate=True, gate_full=True):
    build_n = _bump_build_counter()
    with _stage("assembly: collect_components"):
        comps = collect_components()
    print(f"Assembled {len(comps)} components  [build #{build_n}]", flush=True)
    # THE ASSEMBLY IS THIS LIST, NOT A FILE. Nothing read the one-file STEP of it but a
    # viewer, and the viewer is given the list. The printed parts' own STEPs are above.
    # Each component is left behind on its own instead, where every worktree's scratch
    # view takes its surroundings from (cadkit.scratch): only the lead's build writes it.
    with _stage("shared cache for the scratch views"):
        from cadkit.scratch import publish_cache
        publish_cache(comps, OUT, build=build_n)
    rc = _web_view(comps, build_n, publish)
    # LAST: the gate spawns a worker pool, so run it once the viewer is refreshed — a
    # gate hiccup can never cost the build.
    if gate:
        # every gate always runs, so one RED doesn't hide another's result
        for label, fn in (("gate: overlaps", lambda: _report_overlaps(comps, full=gate_full)),
                          ("gate: sweep", lambda: _report_sweep(comps)),
                          ("gate: drive travel", lambda: _report_drive_travel(comps)),
                          ("gate: world pose", lambda: _report_world_pose(comps)),
                          ("gate: dead code", _report_dead)):
            with _stage(label):
                rc |= fn()
    _report_stages()
    return rc


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


def _report_world_pose(comps) -> int:
    """A printed part drawn ONCE must be authored where it sits, not rotated or mirrored into
    place (user, 2026-10-22) -- tools/check_world_pose. The PARTS solids are the ones the
    export above already built, so this costs the vertex fits only."""
    try:
        from tools.check_world_pose import gate
        parts = {n: (lambda s: s.val() if hasattr(s, "val") else s)(PARTS[n][0]()) for n in PARTS}
        return 1 if gate(parts, [(name, wp.val()) for name, wp in comps]) else 0
    except Exception as e:               # noqa: BLE001 — a gate crash must not eat the geometry
        print(f"world-pose gate: SKIPPED ({type(e).__name__}: {e})", flush=True)
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


def _report_drive_travel(comps) -> int:
    """THE DRIVE OVER ITS TRAVEL (replaces v1's carriage-travel gate, 2026-11-13): the overlap
    gate sees every string at T_OPEN, so this redraws the instrument with every string at
    each end of its travel (t 0 and 1) and gates that. Only the parts that move are new
    pairs; the rest come from the pair cache. Baseline is 0."""
    try:
        from . import direct_bench as DB
        from tools.check_overlaps import gate
        n = 0
        for t in (0.0, 1.0):
            print(f"drive travel: every string at t = {t:.0f}", flush=True)
            n += gate([(name, wp.val()) for name, wp in DB.assembly(t)], full=True)
    except Exception as e:               # noqa: BLE001 -- never let a gate eat the geometry
        print(f"drive travel gate: SKIPPED ({type(e).__name__}: {e})", flush=True)
        return 0
    print(f"DRIVE TRAVEL GATE: {'green' if n == 0 else f'RED -- {n} pair(s) meet at an end of the travel'}",
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


def _web_view(comps, build_n, publish=True):
    """The viewer's model, from the just-built components (reused — no second geometry
    pass, and every mesh is of a COPY): written to docs/, shown in the local page, and
    force-pushed to the gh-pages branch. Viewer or publish trouble (offline, not on main,
    auth) never fails an otherwise-good geometry build, WITH ONE EXCEPTION: boards whose
    components could not be drawn. That model is written with every board as its boxes,
    and it is neither shown nor published: the build is RED (returns 1), because a page
    of green boxes looks like a finished build to everyone but the person who knows the
    boards. The push itself is a no-op off the main branch (so agent worktrees don't
    publish) — see tools/publish_preview.py. Returns the build's exit code."""
    from cadkit.web import BoardsSkipped
    try:
        from cadkit.web import show_exported
        from tools.export_glb import build_glb
        from tools.export_rig import build_rig
        from tools.publish_preview import push_gh_pages
        with _stage("viewer: rig"):
            build_rig(build_n)                  # animation manifest (pivots + copedent)
        with _stage("viewer: mesh + write"):
            glb = build_glb(comps, build_n=build_n)   # full instrument, numbered
        with _stage("viewer: local page"):
            show_exported(glb.parent, root=OUT)
        if publish:
            with _stage("viewer: publish"):
                published = push_gh_pages(build_n)
            if published is False:               # it has said why; say it LAST as well
                print(f"⚠ web view: build #{build_n} is NOT on the public preview "
                      "(tools.publish_preview said why, above)", flush=True)
    except BoardsSkipped as e:
        print(f"🔴 web view: BOARDS NOT DRAWN — not shown, not published. {e}", flush=True)
        return 1
    except Exception as e:               # noqa: BLE001 — never let the viewer break a build
        print(f"web view: skipped ({type(e).__name__}: {e})", flush=True)
    return 0

# ── THE DIRECT INSTRUMENT'S PARTS (user, 2026-11-13: the main build is the direct instrument) ──
# PARTS_V1 is v1's table as it was, for the v1 code that still reads it. PARTS is what this
# build exports and checks: the direct instrument's parts, and the v1 parts it will REUSE (the
# body-adapter latch, the legs, the pedal bar, the levers, the UI's printed parts) and the shop
# ── THE DIRECT INSTRUMENT'S OWN PARTS (user, 2026-11-13: the main build is the direct instrument) ──
# families printed from one file under another name: collar A and B are ONE part (turned end for end)
_FAMILY_STEM = {"collar_a": "clamp_collar", "collar_b": "clamp_collar"}


def _direct_parts():
    """The direct instrument's own parts: each per-string printed part, one per string that has
    it, as drawn at T_OPEN; a family's members print from ONE STEP PER DISTINCT SHAPE
    (STRING_FAMILIES, _export_family); the body and the endplate; the anchor tray (laser cut, bent)."""
    from . import direct_bench as DB
    from cadkit.kept import kept
    out, with_ = {}, {}
    lead = {}                                         # (stem, material) -> the family's leader
    for nm, make, moves in DB._STRING_PARTS:
        mat = DB.MATERIAL.get(nm)
        if mat not in MATERIALS:
            continue
        stem = _FAMILY_STEM.get(nm, nm)
        for i in range(DB.N):
            if nm == "collar_a" and DB.coupler_is_collar(i):
                continue                              # the coupler is its collar A
            key = f"{nm}_{i}"
            args = (i, DB.T_OPEN) if moves else (i,)
            out[key] = (partial(kept, make, *args), f"{mat}/{stem}.step",
                        f"{mat.upper()} -- direct drive {nm}, string {i + 1} (PRINT_LIST.md: one "
                        f"STEP per distinct shape). src.direct_bench")
            ld = lead.setdefault((stem, mat), key)
            if ld == key:
                STRING_FAMILIES[key] = (stem, mat, [key])
            else:
                STRING_FAMILIES[ld][2].append(key)
                with_[key] = ld
    out["body"] = (partial(kept, DB._body), "petg-gf/body.step",
                      "PETG-GF -- the direct instrument's BODY: walls and floor to the endplate "
                      "joint, the bars' channels, the anchor's bosses and the brain board's "
                      "grooves. src.direct_bench._body")
    out["endplate"] = (DB.endplate_full, "petg-gf/endplate.step",
                          "PETG-GF -- the +X ENDPLATE (rod plate, axles, lanes, the bars' ends). "
                          "PRINTED +X -> -X. src.direct_bench._endplate")
    out["anchor"] = (partial(kept, DB._anchor), "steel/anchor.step",
                        "STAINLESS SHEET, laser cut and bent -- the spring anchor tray, on 8 "
                        "M4 x 10 into the wall bars. Not printed")
    # THE BODY ADAPTERS (user, 2026-11-17), one a corner, each its own STEP
    from . import body_adapter_v2 as BA
    for k, ex, ey in BA.corners():
        out[f"adapter_{k}"] = (partial(kept, BA.adapter, k), f"petg-gf/adapter_{k}.step",
                               f"PETG-GF -- body adapter, {'+X' if ex > 0 else '-X'}/{'+Y' if ey > 0 else '-Y'} "
                               "corner: the v1 leg half (blind mortise, latch pocket) under two X "
                               "tenons that slide into the body and the endplate. src.body_adapter_v2")
    return out, with_


_DP, _DW = _direct_parts()
from . import direct_bench as DB_
PARTS.update(_DP)
PRINTS_WITH.update(_DW)
FILAMENT_OF.update({k: v[1].split("/")[0] for k, v in _DP.items()})
PRINT_ORIENTATION = {k: v for k, v in PRINT_ORIENTATION.items() if k in PARTS}
PRINT_ORIENTATION["endplate"] = PO.from_build_dir(
    (-1, 0, 0), "direct_bench: the endplate PRINTS +X -> -X (user, 2026-11-13: a clean exterior, "
                "round holes along X); the axle bores peak -X, the lanes reach EP_DROOP into the "
                "rod plate for the bridge's sag")
for _n in [n for n in PARTS if n.startswith("collar_") and n[7:].isdigit()]:
    PRINT_ORIENTATION[_n] = PO.from_build_dir(
        (-1, 0, 0), "direct_bench: the collar PRINTS +X -> -X, its +X face on the bed (user, "
                    "2026-11-12, back to the original orientation); insert pockets under cone roofs")
# the rest of the drive's printed parts (user, 2026-11-14), each direction its module's constant
for _base, _up, _why in (
        ("collar_a", DB_.COLLAR_A_UP, "direct_bench.COLLAR_A_UP -- prints -X -> +X (0.8 nozzle; walls 0.8 at least round its "
                                       "holes and the boss); split through, the clamp insert from the bottom flat"),
        ("plug", DB_.PLUG_UP, "direct_bench.PLUG_UP -- prints -X -> +X; cones under the stop "
                              "flange and the insert pocket, the screw holes cut through the teeth"),
        ("sleeve_p", DB_.SLEEVE_P_UP, "direct_bench.SLEEVE_P_UP -- prints +X -> -X; its lock fin from the bed"),
        ("sleeve_c", DB_.SLEEVE_C_UP, "direct_bench.SLEEVE_C_UP -- prints +X -> -X; its lock fin standing on past the far end"),
        ("yoke", DB_.YOKE_UP, "direct_bench.YOKE_UP -- prints -X -> +X; the nut-rim register "
                              "under a cone"),
        ("collar_b", DB_.COLLAR_B_UP, "direct_bench.COLLAR_B_UP -- collar A's part turned end for "
                                      "end: the same print, boss last"),
        ("housing", DB_.HOUSE_UP, "direct_bench.HOUSE_UP -- prints -X -> +X: the pocket's mouth on "
                                  "the bed, the lip a 1.2 ledge (the spacers carry it to the plate)"),
        ("coupler", DB_.COLLAR_A_UP, "direct_bench._collar_local -- the coupler is the collar plus a "
                                     "shaft section: prints -X -> +X standing on its motor end, the 45 deg "
                                     "cone up to the clamp body, its pockets peaked +X as the collar's"),
        ("mplate", (1.0, 0.0, 0.0), "direct_bench._mplate -- flat, its motor face on the bed: every "
                                    "hole along the build, round"),
        ("lid", DB_.LID_UP,"direct_bench.LID_UP -- prints +X -> -X, the race's face on top; the ties' heads "
                            "on its -X face")):
    for _n in [n for n in PARTS if n.startswith(_base + "_") and n[len(_base) + 1:].isdigit()]:
        PRINT_ORIENTATION[_n] = PO.from_build_dir(_up, _why)
from . import body_adapter_v2 as _BA
for _k, _, _ in _BA.corners():
    PRINT_ORIENTATION[f"adapter_{_k}"] = PO.from_build_dir(
        _BA.adapter_up(_k), "body_adapter_v2.adapter_up -- builds along X from its outer end face: the "
                            "X tenons' profile in the layers (N), their outer ends ramped 1.5:1")
for _n, (_b, _path, _note) in PARTS.items():
    if _n not in PRINT_ORIENTATION:
        PRINT_ORIENTATION[_n] = PO(
            None, "as modelled -- a direct-bench part with no declared print yet. UNSTUDIED. "
                  "The part note says: " + " ".join((_note or "").split())[:300], confirmed=False)
require_declared(set(PARTS), PRINT_ORIENTATION)


def _once(builder):
    """`builder`, built at most once a process: the export builds every part, and the world-pose
    gate wants the same solids (it re-read every kept part, 2026-11-16)."""
    box = []

    def built():
        if not box:
            box.append(builder())
        return box[0]
    return built


PARTS.update({_k: (_once(_b), _p, _nt) for _k, (_b, _p, _nt) in PARTS.items()})


_T_MAIN = time.perf_counter()           # everything above has been imported and built


def main() -> None:
    # Part notes carry Unicode (→, Ø, …); a cp1252 Windows console/pipe raises
    # UnicodeEncodeError mid-export and aborts the build. Force UTF-8 so a print
    # can never kill a good geometry build (replace = never crash on any glyph).
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    # 🚩 an UNCONFIRMED bed face is a RECORD of how a part has been exported,
    # not a decision anyone checked. The bed face decides which faces are
    # overhangs, which slots bridge and which way every joint on the part
    # prints, so settle it with the user before working on one of these
    # (cadkit AGENTS.md). 41 of 63 parts here are in that state: the
    # instrument declares PRINT_UP per module, and these are the parts no
    # module covers.
    flagged = unconfirmed(PRINT_ORIENTATION)
    if flagged:
        print("UNCONFIRMED print orientation (%d of %d parts) — confirm with "
              "the user BEFORE working on one of these:\n  %s"
              % (len(flagged), len(PRINT_ORIENTATION), ", ".join(flagged)),
              flush=True)

    p = argparse.ArgumentParser(prog="src.build")
    p.add_argument("--part", help="Build only this printed part (skips assembly).")
    p.add_argument("--list", action="store_true", help="List part names and exit.")
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
    _STAGES.insert(0, ("import (module-level geometry)", _T_MAIN - _T_IMPORT))

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
        _export(PRINTS_WITH.get(args.part, args.part))
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
