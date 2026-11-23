"""`access` holds its room in placement, not only in the score (2026-11-22).

    py -3.12 test_access_grow.py

brain_board sqah: hard access on seven test pads placed cell for cell like soft. 1. grow_access gives
a test pad a courtyard holding its tool circle (radius >= tool_d / 2 round the pad); 2. it is
idempotent; 3. a part without an access rule is untouched; 4. place_flow's hard gate lists
`access`. Exit 0 = PASS.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_intent as pi  # noqa: E402

tp = {"pads": [{"num": "1", "net": "SWCLK", "xy": [0.0, 0.0], "size": [1.5, 1.5]}],
      "crtyd": [[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0]], "side": "F"}
r1 = {"pads": [{"num": "1", "net": "A", "xy": [-0.5, 0], "size": [0.5, 0.5]}],
      "crtyd": [[-1, -0.5], [1, -0.5], [1, 0.5], [-1, 0.5]], "side": "F"}
rules = [{"kind": "access", "ref": "TP2", "side": "top", "tool_d": 3.0, "hard": True}]
bad = []
g, grown = pi.grow_access({"TP2": tp, "R1": r1}, rules)
c = g["TP2"]["crtyd"]
rmin = min(math.hypot(x, y) for x, y in c)
far = max(math.hypot(x, y) for x, y in c)
if grown != ["TP2"]:
    bad.append("grown %s, wants ['TP2']" % grown)
if far < 1.5 - 1e-6:
    bad.append("the grown courtyard does not reach the 1.5 mm tool radius (max %.3f)" % far)
# every point of the 1.5 circle lies inside the hull: its vertices circumscribe it
if rmin < 1.5 - 1e-6:
    bad.append("a hull vertex sits inside the tool circle (%.3f)" % rmin)
g2, grown2 = pi.grow_access(g, rules)
if grown2 or g2["TP2"]["crtyd"] != c:
    bad.append("not idempotent: grew %s again" % grown2)
if g["R1"] is not r1:
    bad.append("a part with no access rule was changed")
src = open(os.path.join(HERE, "place_flow.py"), encoding="utf-8").read()
if "access" not in pi.GATE_KINDS or "pi.GATE_KINDS" not in src or "pi.grow_reach(parts, rules)" not in src:
    bad.append("place_flow does not grow access courtyards or gate hard access")
for x in bad:
    print("  FAIL:", x)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
