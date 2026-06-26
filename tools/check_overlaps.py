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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "freecad"))
from overlap_check import run                     # noqa: E402  (shared engine)

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
    # nut-block hardware (per string): break pin sets the scale, set screw clamps the string
    frozenset({"break_dowel", "string"}), frozenset({"set_screw", "string"}),
    frozenset({"nut", "screw_pulley"}), frozenset({"screw_bearing", "screw_pulley"}),
    frozenset({"locknut", "leadscrew"}), frozenset({"locknut", "screw_bearing"}),
    # a belt connects its OWN motor and screw, so it touches both there
    frozenset({"belt", "motor"}), frozenset({"belt", "leadscrew"}),
    frozenset({"belt", "belt_clamp"}),   # splice clamp grips its own belt
}
# The bridge endplate hosts the whole drive top end (screw rail fused in, axle
# comb, guide ledges), so most per-string hardware legitimately touches it.
GLOBAL_OK = {
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
    # pickup carrier: the pickup rests on the printed Z-plate (lifted by the 3
    # height screws) and is pinned by the clamp shim (driven by the side clamp
    # screw). Each part's contact with the piece is the top_plate rule below.
    frozenset({"pickup", "pickup_zplate"}), frozenset({"pickup", "pickup_xclamp"}),
    frozenset({"pickup_zplate", "height_screw"}),
    frozenset({"pickup_xclamp", "clamp_screw"}),
    # legs: socket bolts to the rail; threaded junctions + washers + slider
    frozenset({"leg_socket", "chassis"}), frozenset({"leg_socket", "leg_segment"}),
    frozenset({"leg_segment", "leg_segment"}), frozenset({"leg_segment", "leg_sleeve"}),
    frozenset({"leg_sleeve", "leg_shaft"}), frozenset({"leg_shaft", "leg_foot"}),
    frozenset({"leg_washer", "leg_socket"}), frozenset({"leg_washer", "leg_segment"}),
    frozenset({"leg_washer", "leg_sleeve"}),
}


def intended(na, nb) -> bool:
    if "build_counter" in (na, nb):
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
    # top deck plates ride the rail grooves, abut each other (mortise/tenon),
    # carry the OLED + joystick, and the pickup pokes through the open slot
    tp = {base(na), base(nb)}
    if "top_plate" in tp and tp & {"chassis", "top_plate", "oled", "joystick",
                                   "pickup", "pickup_zplate", "pickup_xclamp",
                                   "height_screw", "clamp_screw",
                                   "bridge_endplate", "keyhead_endplate"}:
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
