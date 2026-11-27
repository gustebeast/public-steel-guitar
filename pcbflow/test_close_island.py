"""A pour island's break carries the current that crosses it, and is joined across its own gap
(brain_board fold11/12, 2026-11-27).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_close_island.py [<fold12's output_board stem>]

BST_SW's pour broke into the switch node (L204, Q208/Q209, C299) and a 0.8 mm2 sliver on
U220.18, the LM5122's SW pin -- the high-side gate drive's return -- 0.2 mm below it. DRC named
both ends by one zone corner, so the break kept the net's 6.5 A (fold11: CAN'T CARRY at 2.70
mm), and the join started at the big piece's first pad, 15.1 mm off (fold12: ROUTER OPEN).
On the committed fixture (testdata/close_island, make.py: the same split in small, SW at 6.5 A
L1.2 > Q1.1, the sliver on U1.18), and on fold12's board when its stem is given:
1. _island_retarget joins across the real gap: start to target under 1.5 mm.
2. _cut_amps: no stated path crosses the cut -> 0 A.
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


def check(tag, stem, net, corner, drv, other):
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    paths = (json.load(open(stem + ".board.json", encoding="utf-8")).get("quality") or {}).get("power_paths") or ()
    rt = CL._island_retarget(board, net, "F.Cu", corner)
    if not rt:
        bad.append("%s: no island found for %s" % (tag, net))
        return
    (la, pa), (lb, pb), pads = rt
    g = ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2) ** 0.5
    print("%s: join %s %s -> %s %s, %.2f mm; island pads %s" % (tag, la, pa, lb, pb, g, pads))
    if g > 1.5:
        bad.append("%s: the join spans %.2f mm, not the 0.2 mm gap" % (tag, g))
    a = CL._cut_amps(board, net, pads, paths)
    if abs(a) > 1e-9:
        bad.append("%s: the %s cut carries %.2f A, wants 0 (gate-drive return only)" % (tag, net, a))
    fake = [dict(net=net, amps=2.0, **{"from": drv, "to": [other]})]
    a = CL._cut_amps(board, net, pads, fake)
    if abs(a - 2.0) > 1e-9:
        bad.append("%s: a path across the cut reads %.2f A, wants 2.00" % (tag, a))


check("fixture", os.path.join(HERE, "testdata", "close_island", "b"), "SW", (2.0, 2.0), "U1.18", "L1.2")
if len(sys.argv) > 1:
    check("fold12", sys.argv[1], "BST_SW", (152.6, 120.0), "U220.18", "L204.2")
else:
    print("(no fold12 stem given: the fixture only)")
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.stdout.flush()
os._exit(1 if bad else 0)
