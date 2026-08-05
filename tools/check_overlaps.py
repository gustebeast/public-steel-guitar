"""Overlap checker for the pedal-steel assembly.

Project glue over the shared engine in ``freecad/overlap_check.py``: this file
supplies the placed parts (``src.build.collect_components``) and the project's
``intended()`` whitelist of designed contacts (screw-in-nut, bushing-in-rail,
motor-on-bank, …); the engine runs the parallel boolean scan and reports the
UNINTENDED interpenetrations.

  py -3.12 -m tools.check_overlaps            # fast scan (skips belts -- see below)
  py -3.12 -m tools.check_overlaps --full     # check EVERY part (belts too) -- pre-commit
  py -3.12 -m tools.check_overlaps --all      # also list intended contacts
  py -3.12 -m tools.check_overlaps --only chassis,keyhead_endplate   # just these bases
  py -3.12 -m tools.check_overlaps --exclude string,wire            # skip more bases
  py -3.12 -m tools.check_overlaps -j 14      # set worker count (default: cores/2)
  py -3.12 -m tools.check_overlaps --serial   # single-process (baseline/debug)

The belts are slow to boolean (swept compounds dominate the runtime) and rarely
move, so the DEFAULT scan skips them for a quick inner-loop check; pass --full for
the complete gate (e.g. before committing). Every run prints what it skipped.

Exit code is the number of unintended overlapping pairs (0 = clean).

The heavy project build is imported only inside main(), so spawned workers (which
re-import this module) don't rebuild it — they just load the serialized shapes.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

from cadkit.overlap_check import run              # shared engine

WIRE_OK = None      # set in main() (src.wiring needs src.build imported first)


def base(name: str) -> str:
    return re.sub(r"_\d+$", "", name)


def idx(name: str):
    m = re.search(r"_(\d+)$", name)
    return int(m.group(1)) if m else None


# Designed contacts that SHOULD interpenetrate / touch — not problems.
PER_STRING_OK = {
    frozenset({"leadscrew", "nut"}), frozenset({"leadscrew", "carriage"}),
    frozenset({"nut", "carriage"}), frozenset({"guide_rod", "carriage"}),
    frozenset({"leadscrew", "screw_bearing"}), frozenset({"leadscrew", "screw_pulley"}),
    frozenset({"belt", "screw_pulley"}), frozenset({"belt", "motor_pulley"}),
    frozenset({"motor", "motor_pulley"}),
    frozenset({"string", "carriage"}),
    frozenset({"string_nut", "carriage"}), frozenset({"string_nut", "string"}),
    # nut-block hardware (per string): break pin sets the scale, set screw clamps the
    # string, threading through its own heat-set insert
    frozenset({"break_dowel", "string"}), frozenset({"set_screw", "string"}),
    frozenset({"set_screw", "nut_insert"}),
    frozenset({"nut", "screw_pulley"}), frozenset({"screw_bearing", "screw_pulley"}),
    frozenset({"locknut", "leadscrew"}), frozenset({"locknut", "screw_bearing"}),
    # a belt connects its OWN motor and screw, so it touches both there
    frozenset({"belt", "motor"}), frozenset({"belt", "leadscrew"}),
    frozenset({"belt", "belt_clamp"}),   # splice clamp grips its own belt
}
# The bridge endplate hosts the whole drive top end (screw rail fused in, axle
# comb, guide ledges), so most per-string hardware legitimately touches it.
GLOBAL_OK = {
    # optical strip: two M4 grips locate the board -- each screw threads through its own
    # heat-set insert, which is seated in the endplate's wrap plinth. Both are designed
    # thread engagement, not interference.
    frozenset({"optical_screw", "optical_insert"}),
    # belt-tensioner coupon: the M4 brass insert seats INSIDE the anchor's bore (designed)
    frozenset({"belt_tensioner_anchor_coupon", "belt_tensioner_insert_coupon"}),
    frozenset({"optical_screw", "bridge_endplate"}),
    frozenset({"screw_bearing", "bridge_endplate"}), frozenset({"leadscrew", "bridge_endplate"}),
    frozenset({"locknut", "bridge_endplate"}), frozenset({"screw_pulley", "bridge_endplate"}),
    frozenset({"nut", "bridge_endplate"}), frozenset({"carriage", "bridge_endplate"}),
    frozenset({"bridge_endplate", "bridge_bearings"}),
    frozenset({"string", "bridge_bearings"}), frozenset({"string", "bridge_endplate"}),
    # guide rods drop through the endplate's stop bar into its blind sockets
    frozenset({"guide_rod", "bridge_endplate"}),
    # chassis ties everything into one frame; the motor faceplate walls are fused
    # into it, so motors mount to it
    frozenset({"chassis", "bridge_endplate"}), frozenset({"chassis", "motor"}),
    frozenset({"chassis", "string"}),
    # merged keyhead endplate + nut block: seats on / caps the chassis, caps the
    # deck-panel grooves, and holds the strings + their gauged dowels + set screws;
    # one +Z hold-down screw ties it to the chassis floor
    frozenset({"keyhead_endplate", "chassis"}), frozenset({"keyhead_endplate", "string"}),
    frozenset({"keyhead_endplate", "top_plate"}),
    frozenset({"keyhead_endplate", "break_dowel"}), frozenset({"keyhead_endplate", "set_screw"}),
    # pickup carrier: the pickup rests on the printed Z-plate, which the three LEADSCREW
    # jacks raise/tilt -- each screw head captured in a piece bearing housing at the top,
    # its thread running through a heat-set-insert NUT in the plate. (Y hold-down clamp
    # removed for now -- height adjustment only.)
    frozenset({"pickup", "pickup_zplate"}),
    frozenset({"pickup_zplate", "pickup_jack_insert"}),
    frozenset({"pickup_zplate", "pickup_jack_screw"}),
    frozenset({"pickup_jack_insert", "pickup_jack_screw"}),
    frozenset({"pickup_jack_screw", "top_plate"}),
    # retention: -Y cup-tip grub threads a heat-set insert in the plate boss and pushes the
    # pickup +Y against the plate's +Y wall
    frozenset({"pickup_retention_screw", "pickup"}),
    frozenset({"pickup_retention_screw", "pickup_zplate"}),
    frozenset({"pickup_retention_insert", "pickup_zplate"}),
    frozenset({"pickup_retention_insert", "pickup_retention_screw"}),
    # FLUSH-X: the body stubs' outboard wall tenons mortise the ENDPLATE
    # side walls (the inboard ones mortise the rail/chassis)
    frozenset({"leg_body_stub", "keyhead_endplate"}),
    frozenset({"leg_body_stub", "bridge_endplate"}),
    # the electronics tray's snap nubs/fingers bite their boards by design
    frozenset({"electronics_tray", "pi5"}),
    frozenset({"electronics_tray", "teensy_ifc"}),
    # a motor's CAN tee mounts right at that motor's -Y PCB (the drop pigtail is short);
    # the tee-board corner grazing the motor body there is that mount contact
    frozenset({"tee_pcb", "motor"}),
    # legs (FLUSH round): the BODY STUB's octagon wall tenons mortise the
    # rail band (0.1 fit) and its top face butts the body bottom; the
    # latch head engages its socket; the stack below is designed contact
    frozenset({"leg_body_stub", "chassis"}),
    frozenset({"leg_body_stub", "leg_latch_head"}),
    frozenset({"leg_latch_bolt", "leg_body_stub"}),
    frozenset({"chassis_trrs_jack", "leg_body_stub"}),
    frozenset({"jack_seat_ring", "leg_body_stub"}),
    frozenset({"leg_column_plug", "leg_body_stub"}),
    frozenset({"leg_sleeve", "leg_shaft"}), frozenset({"leg_shaft", "leg_foot"}),
    frozenset({"leg_washer", "leg_sleeve"}),
    frozenset({"leg_seg_body", "leg_seg_body"}),
    frozenset({"leg_seg_body", "leg_latch_head"}),
    frozenset({"leg_seg_body", "leg_sleeve"}),
    frozenset({"leg_latch_bolt", "leg_latch_head"}),
    frozenset({"leg_latch_btn", "leg_latch_head"}),
    frozenset({"leg_column_plug", "leg_latch_head"}),
    frozenset({"leg_plug_retainer", "leg_latch_head"}),
    frozenset({"leg_lid", "leg_seg_body"}),
    # pedal bar: the C-slots wrap the shaft waists (0.2 clr, touch at the
    # shoulder plane), the plate rests on the foot caps, and the closed
    # bolts (one latch per foot) block the waists
    frozenset({"pedal_bar_a", "leg_shaft"}),
    frozenset({"pedal_bar_c", "leg_shaft"}),
    frozenset({"pedal_bolt", "leg_shaft"}), frozenset({"pedal_bolt_trrs", "leg_shaft"}),
    # TRRS: the female jack embeds in the -X/+Y shaft (leg_shaft_2 is the
    # leg_shaft_trrs variant); the slider-carried plug reaches into it
    frozenset({"pedal_trrs_jack", "leg_shaft"}),
    frozenset({"pedal_trrs_plug", "leg_shaft"}),
    frozenset({"pedal_leg_carrier", "leg_shaft"}),
    # the leg-column TRRS cable up the shaft's Ø6 hollow centre
    frozenset({"pedal_trrs_cable_leg", "leg_shaft"}),
    # leg↔body TRRS blind-mate: jack in the stub chimney (ring pressed
    # atop = the 0.05 crush), plug in the head (retainer pressed beneath)
    frozenset({"leg_column_plug", "leg_segment"}),
    frozenset({"leg_column_plug", "chassis_trrs_jack"}),
    frozenset({"jack_seat_ring", "chassis_trrs_jack"}),
    frozenset({"leg_column_plug", "leg_plug_retainer"}),
    frozenset({"leg_plug_retainer", "leg_segment"}),
    # the leg-column cable and the shaft-side cable model the SAME physical
    # CA-354S in two modeling domains; they abut/overlap inside the bore
    frozenset({"leg_column_cable", "pedal_trrs_cable_leg"}),
    # ROUND 4: the bar carries the +Y legs' stub towers — the short
    # shaft's block seats the stub plate, the latch bolt bears its ledge,
    # the second TRRS pair mates inside, the stub takes a leg foot
    frozenset({"leg_foot", "pedal_bar_a"}),
    frozenset({"leg_foot", "pedal_bar_c"}),
    frozenset({"leg_latch_bolt", "pedal_bar_a"}),
    frozenset({"leg_latch_bolt", "pedal_bar_c"}),
    frozenset({"leg_latch_btn", "pedal_bar_a"}),
    frozenset({"leg_latch_btn", "pedal_bar_c"}),
    frozenset({"leg_column_plug", "pedal_bar_a"}),
    frozenset({"leg_plug_retainer", "pedal_bar_a"}),
    frozenset({"leg_latch_bolt", "leg_shaft"}),
    frozenset({"shaft_trrs_jack", "leg_shaft"}),
    frozenset({"shaft_trrs_jack", "leg_column_plug"}),
    frozenset({"shaft_trrs_jack", "jack_seat_ring"}),
    frozenset({"jack_seat_ring", "leg_shaft"}),
}

# The pedal-bar latches are a self-contained subassembly (bolt in its
# channel, TPU finger potted in the lid, lid recessed into the bar; one
# mirrored latch per foot): whitelist any pair WITHIN the family — a pedal
# part clashing with a leg/chassis part (other than the GLOBAL_OK contacts
# above) stays a reportable bug.
PEDAL_FAMILY = {"pedal_bar_a", "pedal_bar_b", "pedal_bar_c",
                "pedal_lid_a", "pedal_lid_b", "pedal_detent_nub",
                "pedal_trrs_cable_bar"}


# The knee-lever control core is a self-contained subassembly: the axle, bearings,
# magnet, sensor board, springs, set screws, housing and lever are ALL designed to
# touch/run on each other. Whitelist any pair WITHIN the family (this never masks a
# housing<->chassis / housing<->motor clash, since those involve a non-family part).
KNEE_FAMILY = {"knee_housing", "knee_lever", "kv_housing", "kv_lever", "kv_bearing",
               "kv_magnet", "kv_pcb", "kv_chip", "kv_can_header" "kv_pcb_shim", "kv_main_cart_base", "kv_main_cart_piston", "kv_main_guide_post",
               "kv_half_stop_cart_base", "kv_half_stop_cart_piston", "kv_half_stop_guide_post", "kl_axle", "kl_magnet_cap", "kl_chip",
               "kl_bearing", "kl_magnet", "kl_pcb", "kl_can_header",
               "main_spring", "half_stop_spring", "floating_tenon", "retention_setscrew",
               "main_cart_base", "main_cart_piston", "main_guide_post", "main_cart_backstop", "main_cart_drag",
               "half_stop_cart_base", "half_stop_cart_piston", "half_stop_guide_post", "half_stop_cart_backstop", "half_stop_cart_drag",
               "main_spring_tension_setscrew", "half_stop_spring_tension_setscrew"}


def intended(na, nb) -> bool:
    if "build_counter" in (na, nb):
        return True
    if base(na) in KNEE_FAMILY and base(nb) in KNEE_FAMILY:
        return True
    if base(na) in PEDAL_FAMILY and base(nb) in PEDAL_FAMILY:
        return True
    # the knee-lever -Y retention screw is a thread-forming screw that bites the chassis -Y rail;
    # the floating tenon slides up into the rib mortise (its designed seat)
    if frozenset({base(na), base(nb)}) in (frozenset({"retention_setscrew", "chassis"}),
                                           frozenset({"floating_tenon", "chassis"})):
        return True
    # wires are insulated cables: crossing/touching ANOTHER wire is physically
    # fine (and not worth fighting in the model). A wire may otherwise only clip
    # its declared source/destination bodies; clipping any OTHER solid (a motor,
    # a board, the chassis) is a real routing bug.
    a_wire, b_wire = base(na) in WIRE_OK, base(nb) in WIRE_OK
    if a_wire and b_wire:
        return True
    for w, o in ((na, nb), (nb, na)):
        if base(w) in WIRE_OK:
            return base(o) in WIRE_OK[base(w)]
    # the electronics tray's tabs rest on their channel floors
    if frozenset({base(na), base(nb)}) == frozenset({"electronics_tray", "chassis"}):
        return True
    # bus tee PCBs mount flat on the chassis floor (christmas-tree boss TBD)
    if frozenset({base(na), base(nb)}) == frozenset({"tee_pcb", "chassis"}):
        return True
    # top deck plates ride the rail grooves, abut each other (mortise/tenon),
    # carry the OLED + joystick, and the pickup pokes through the open slot.
    # Each panel is a base + colour-layer PAIR (top_plate_N / top_plate_color_N)
    # printed as one object — designed full-face contact.
    tp = {base(na), base(nb)}
    TP_FAMILY = {"top_plate", "top_plate_color"}
    if tp & TP_FAMILY and tp <= (TP_FAMILY | {"chassis", "oled", "joystick",
                                              "pickup", "pickup_zplate", "pickup_jack_screw",
                                              "pickup_jack_insert",
                                              "bridge_endplate", "keyhead_endplate"}):
        return True
    # adjacent chassis segments meet at their sliding-dovetail joints (one frame)
    if base(na) == base(nb) == "chassis":
        return True
    # A belt is allowed to touch its OWN two pulleys (it wraps them); any other
    # belt contact (neighbour belt/pulley/rod) is a real clash to be reported.
    if {base(na), base(nb)} <= {"belt", "screw_pulley", "motor_pulley"} \
            and idx(na) == idx(nb):
        return True
    pair = frozenset({base(na), base(nb)})
    if pair in GLOBAL_OK:
        return True
    if idx(na) is not None and idx(na) == idx(nb) and pair in PER_STRING_OK:
        return True
    return False


# Base names skipped by default: the belts are swept compounds whose booleans
# dominate the runtime, and they rarely move. --full overrides this.
DEFAULT_SKIP = {"belt", "belt_clamp"}


def main():
    ap = argparse.ArgumentParser(description="Pedal-steel assembly overlap checker.")
    ap.add_argument("--all", action="store_true", help="also list intended contacts")
    ap.add_argument("--full", action="store_true",
                    help=f"check ALL parts (default skips {sorted(DEFAULT_SKIP)})")
    ap.add_argument("--exclude", default="", metavar="A,B",
                    help="comma-separated base names to also skip")
    ap.add_argument("--only", default="", metavar="A,B",
                    help="check ONLY these comma-separated base names")
    ap.add_argument("--serial", action="store_true", help="single-process (baseline/debug)")
    ap.add_argument("-j", "--jobs", type=int, default=None,
                    help="worker processes (default: cores/2)")
    args = ap.parse_args()

    global WIRE_OK
    from src.build import collect_components       # heavy: deferred so workers skip it
    import src.wiring                              # safe now (src.build imported first)
    WIRE_OK = src.wiring.WIRE_OK

    comps = [(n, wp.val()) for n, wp in collect_components()]
    only = {s for s in args.only.split(",") if s}
    if only:
        comps = [(n, s) for n, s in comps if base(n) in only]
        print(f"checking ONLY base names: {sorted(only)}")
    else:
        skip = set() if args.full else set(DEFAULT_SKIP)
        skip |= {s for s in args.exclude.split(",") if s}
        if skip:
            comps = [(n, s) for n, s in comps if base(n) not in skip]
            print(f"skipping base names (pass --full to include): {sorted(skip)}")

    jobs = 1 if args.serial else args.jobs
    sys.exit(run(comps, intended, jobs=jobs, show_all=args.all))


if __name__ == "__main__":
    main()
