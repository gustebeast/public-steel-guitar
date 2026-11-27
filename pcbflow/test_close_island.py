"""A pour island's break carries the current that crosses it, and is joined across its own gap
(brain_board fold11/12, 2026-11-27).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_close_island.py <fold12's output_board stem>

BST_SW's pour broke into the switch node (L204, Q208/Q209, C299) and a 0.8 mm2 sliver on
U220.18, the LM5122's SW pin -- the high-side gate drive's return -- 0.2 mm below it. DRC named
both ends by one zone corner, so the break kept the net's 6.5 A (fold11: CAN'T CARRY at 2.70
mm), and the join started at the big piece's first pad, 15.1 mm off (fold12: ROUTER OPEN).
1. _island_retarget joins across the real gap: start to target under 1.5 mm.
2. _cut_amps: no stated BST_SW path crosses the cut -> 0 A.
3. _cut_amps: a stated path with one end on each side -> its current.
Exit 0 = PASS.
"""
import json
import os
import sys

import wx  # noqa: F401  (KiCad's python ships it)
wx.DisableAsserts()
import pcbnew  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import close_last as CL  # noqa: E402

bad = []
if len(sys.argv) < 2:
    print("needs fold12's output_board stem")
    sys.stdout.flush()
    os._exit(2)
stem = sys.argv[1]
board = pcbnew.LoadBoard(stem + ".kicad_pcb")
paths = (json.load(open(stem + ".board.json", encoding="utf-8")).get("quality") or {}).get("power_paths") or ()
rt = CL._island_retarget(board, "BST_SW", "F.Cu", (152.6, 120.0))
if not rt:
    bad.append("no island found for BST_SW")
else:
    (la, pa), (lb, pb), pads = rt
    g = ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2) ** 0.5
    print("join %s %s -> %s %s, %.2f mm; island pads %s" % (la, pa, lb, pb, g, pads))
    if g > 1.5:
        bad.append("the join spans %.2f mm, not the 0.2 mm gap" % g)
    a = CL._cut_amps(board, "BST_SW", pads, paths)
    if abs(a) > 1e-9:
        bad.append("the BST_SW cut carries %.2f A, wants 0 (gate-drive return only)" % a)
    fake = [dict(net="BST_SW", amps=2.0, **{"from": "U220.18", "to": ["L204.2"]})]
    a = CL._cut_amps(board, "BST_SW", pads, fake)
    if abs(a - 2.0) > 1e-9:
        bad.append("a path across the cut reads %.2f A, wants 2.00" % a)
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.stdout.flush()
os._exit(1 if bad else 0)
