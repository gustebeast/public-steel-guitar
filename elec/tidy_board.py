"""Re-apply route.py's deterministic post-route clean-up to an ALREADY ROUTED board.

    cd elec/out && "C:/Program Files/KiCad/10.0/bin/python.exe" ../tidy_board.py fret_led_key

WHY THIS EXISTS AS ITS OWN STEP. Everything route.py does after freerouting hands back a
session file -- snapping hairline gaps, dropping degenerate fragments, re-pouring -- is
DETERMINISTIC. The routing itself is not: "freerouting is non-deterministic and two runs
differ" (elec/README.md), so re-running a whole route to pick up an improvement in the
clean-up throws away a board that is already good and gambles on getting another one.

That is not hypothetical. The keyhead fret LED board routed to zero errors and kept one
8.3 micron dangling stub, which `drop_degenerate` missed because its floor was a flat 5
microns rather than a fraction of the track's own width -- the very ratio its docstring
argues from. Fixing the floor fixes every FUTURE route; this applies the same fixed
function to the board already on disk, and changes nothing else about it.

⚠ IT IS NOT A REPAIR TOOL AND MUST NOT BECOME ONE. It runs the same clean-up functions
route.py runs, with the same arguments, and nothing else. Anything that needs judgement
about where copper should go belongs in route.py's repair block, where it is recorded.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json  # noqa: E402

import pcbnew  # noqa: E402
import wx  # noqa: E402

wx.DisableAsserts()

import layout  # noqa: E402


def tidy(stem):
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    # ⚠ EVERY READ AND EVERY POUR HAPPENS BEFORE THE FIRST DELETE, AND THE SAVE IS THE
    # NEXT STATEMENT AFTER IT. board.Remove() leaves the track container in a state
    # where touching it again is undefined -- route.py records this as a SWIG ownership
    # hazard and takes its measurements first; the first draft of this file poured AFTER
    # drop_degenerate, exactly as route.py does in a flow where the board is freshly
    # built, and segfaulted KiCad's Python on a board loaded from disk.
    board.BuildConnectivity()
    n_snap = layout.snap_hairline_gaps(board)
    if n_snap:
        print("  snapped %d hairline gap(s) shut" % n_snap)
        board.BuildConnectivity()
    if board.Zones():
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    n_junk = layout.drop_degenerate(board)
    board.Save(stem + ".kicad_pcb")
    print("%s: tidied -- %d snapped, %d degenerate fragment(s) dropped"
          % (os.path.basename(stem), n_snap, n_junk))


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        tidy(arg[:-len(".kicad_pcb")] if arg.endswith(".kicad_pcb") else arg)
