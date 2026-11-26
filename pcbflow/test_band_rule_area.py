"""A keep-out rule area is a wall for a pour band (brain_board fold10 pre-check, 2026-11-26:
+5V_OPT's and VIN_BUS's B.Cu bands cut the corner of the audio moat, and the fill split there).

    py -3.12 test_band_rule_area.py

Two lands 20 mm apart with a 1 mm moat (notes rule_areas, fills not allowed, all layers) across
the straight line between them, open at one end: the band goes round the moat's end, no band
point inside it. A rule area that allows fills is not a wall. Exit 0 = PASS.
"""
import os
import sys

import numpy as np
from matplotlib.path import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_intent as pi  # noqa: E402

land = lambda: {"side": "F", "pads": [{"num": "1", "xy": [0.0, 0.0], "size": [1.0, 1.0], "net": "P", "rot": 0.0}],
                "crtyd": None, "fab": None}
P = pi.Placed({"A1": land(), "A2": land()}, {"A1": [0.0, 0.0, 0.0], "A2": [20.0, 0.0, 0.0]})
moat = [[9.5, -4.0], [10.5, -4.0], [10.5, 8.0], [9.5, 8.0]]          # open below y = -4
rule = {"kind": "pour", "net": "P", "layer": "B.Cu", "along": ["A1.1", "A2.1"], "width_mm": 1.0, "around": True,
        "search_mm": 8.0}
bad = []
for fills, want_wall in ((False, True), (True, False)):
    notes = {"zone_clearance": 0.5, "rule_areas": [{"poly": moat, "layers": "all", "fills": fills}]}
    poly = pi.pour_around(rule, P, notes, 1.0)
    if poly is None:
        bad.append("fills=%s: no band" % fills)
        continue
    g = np.mgrid[9.5:10.5:0.05, -4.0:8.0:0.05].reshape(2, -1).T
    hit = Path(poly).contains_points(g).any()
    print("  fills allowed %s: band crosses the moat: %s" % (fills, hit))
    if want_wall and hit:
        bad.append("a no-fill rule area did not wall the band")
    if not want_wall and not hit:
        bad.append("a fill-allowed rule area walled the band (it should run straight)")
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
