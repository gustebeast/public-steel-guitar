"""Reconnect copper the zone fill stranded from its own plane. One stage, one process.

⚠ WHY THIS IS A SEPARATE SCRIPT AND NOT THREE LINES AT THE END OF route.py. It was three
lines at the end of route.py first, and it could not run there: by that point route.py has
called board.Remove() (drop_degenerate), and after a removal pcbnew hands back raw
SwigPyObjects -- first board.Zones() had no GetNetname, and then a FRESH pcbnew.LoadBoard()
in the same interpreter had no BuildConnectivity either. The damage is to the process, not
to the one board, so no amount of reloading inside route.py escapes it. finish.py already
runs every stage as its own subprocess for exactly this family of reason; this is one more.

It also must run AFTER route.py rather than inside layout.py's pour: that pour happens
during PLACEMENT, when the board has no tracks at all and nothing is stranded yet.
"""
import json
import os
import sys

import layout
import pcbnew


def main(stem):
    pcb = stem + ".kicad_pcb"
    if not os.path.isfile(pcb):
        return 0
    try:
        notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    except Exception:
        return 0
    if not notes.get("zones"):
        return 0
    board = pcbnew.LoadBoard(pcb)
    laid = layout.repair_plane_orphans(board, notes)
    if laid:
        board.Save(pcb)
        # the repair added copper after route.py canonicalised, so do it again --
        # otherwise the repaired tracks carry random UUIDs and every diff of a
        # routed board picks up noise route.py went to trouble to remove.
        layout._canonical_uuids(pcb)
    return laid


if __name__ == "__main__":
    sys.exit(0 if main(os.path.abspath(sys.argv[1])) >= 0 else 1)
