"""Do the CAD's connector anchors still agree with the boards' placements?

⚠ THE SAME DRIFT mpn_check CATCHES FOR PARTS, BUT FOR GEOMETRY. src/electronics.py
carries connector anchors and board outlines "straight out of" elec/*.py -- copied by
hand, on a different day, for a different reason. When they drift the BOARD is right and
the CAD is wrong, and the CAD is what the chassis is cut around.

Found on 2026-09-18, by writing this:

  J9      The output panel's SECOND 24 V outlet was added to the netlist and never added
          to OP_J. The CAD had been modelling a board with one power outlet where the
          netlist has two. A missing connector is invisible in the way that matters --
          the solid looks right, and the clearance it does not take is the clearance
          nobody checks.

Neither DRC nor the netlist checks nor the overlap gate can see this: each file is
internally consistent, and only the comparison sees it.

Usage:  py -3.12 elec/cad_geom_check.py
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from src import electronics as cad              # noqa: E402

# ⚠ TWO BOARDS IS THE WHOLE LIST, AND THAT IS NOT A COVERAGE GAP. Checked 2026-09-18,
# because "the priority board is not in here" looks exactly like one:
#   * optical and lever_sensor need no comparison. Their CAD is GENERATED from the board
#     -- src/optical_pickup.PARTS is the single source elec/optical.py imports (and
#     asserts both ways, refs and footprints, plus the VCAP pins and the sourcing table);
#     src/knee_lever.py reads elec/out/lever_sensor.board.json. One source cannot drift
#     from itself. Adding them here would compare a file to itself and always pass.
#   * can_tee DOES keep two copies -- six numbers in elec/can_tee.py and six in
#     src/dimensions.py -- but it cannot be checked HERE, because the CAD has no
#     connector anchor table for it (electronics.tee_pcb places the headers by
#     construction). Its check therefore lives in elec/can_tee.py itself, as an import-
#     time assert against src.dimensions. Do not re-add it here; it is not missing.
# That leaves output_panel and motor_ctrl: the only two boards whose CAD states the
# geometry INDEPENDENTLY, which is the only situation this file is for.
#
# (board module, the CAD's anchor dict, the CAD's outline pair, tolerance in mm)
BOARDS = (("output_panel", "OP_J", ("OP_BOARD_X", "OP_BOARD_Y"), 0.01),
          ("motor_ctrl", "MCTRL_J", ("MCTRL_BOARD_X", "MCTRL_BOARD_Y"), 0.01))

# Connectors deliberately outside the CAD's box table, and why. Each one is a claim that
# the part IS modelled, somewhere else and better -- not that it may be ignored.
EXEMPT = {
    ("output_panel", "J5"):
        "the 1/4 in jack is built as a real cylinder, because its BORE is what the "
        "endplate hole lines up with and a box would hide that -- see OP_TS_* ",
}


def main():
    bad = []
    for mod_name, anchors_name, outline_names, tol in BOARDS:
        mod = importlib.import_module(mod_name)
        notes = mod.BOARD_NOTES
        places = notes["placements"]
        anchors = getattr(cad, anchors_name)
        w, h = notes["outline_mm"]
        cw, ch = (getattr(cad, n) for n in outline_names)
        if abs(cw - w) > tol or abs(ch - h) > tol:
            bad.append("%s outline: board %.2f x %.2f, CAD %.2f x %.2f"
                       % (mod_name, w, h, cw, ch))
        # ⚠ "STARTS WITH J" IS NOT "IS A CONNECTOR", and the first run of this reported
        # three disagreements that were all the heuristic's fault. JP1/JP2 are
        # SolderJumper_2_Open CAN-termination jumpers -- flat copper with no 3D envelope,
        # correctly absent from a table of boxes. So JP* is excluded by rule, and the one
        # real connector that belongs outside the table is named below with its reason.
        # Anything else missing is a finding.
        board_conns = {r for r in places
                       if r.startswith("J") and not r.startswith("JP")
                       and (mod_name, r) not in EXEMPT}
        for ref in sorted(board_conns - set(anchors)):
            bad.append("%s %s is placed on the board and missing from cad.%s"
                       % (mod_name, ref, anchors_name))
        for ref in sorted(set(anchors) - board_conns):
            bad.append("%s cad.%s has %s, which the board does not place"
                       % (mod_name, anchors_name, ref))
        for ref in sorted(board_conns & set(anchors)):
            bx, by, brot = places[ref]
            cx, cy, crot = anchors[ref]
            if abs(bx - cx) > tol or abs(by - cy) > tol or abs(brot - crot) > tol:
                bad.append("%s %s: board (%.2f, %.2f, %.0f) vs CAD (%.2f, %.2f, %.0f)"
                           % (mod_name, ref, bx, by, brot, cx, cy, crot))
        print("%-13s %2d connector(s) compared, outline %.1f x %.1f"
              % (mod_name, len(board_conns), w, h))
    if bad:
        print("\n*** %d DISAGREEMENT(S) BETWEEN THE CAD AND THE BOARDS ***" % len(bad))
        for line in bad:
            print("   " + line)
        return 1
    print("\nthe CAD's connector anchors and outlines match the boards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
