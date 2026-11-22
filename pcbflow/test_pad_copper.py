"""Declared copper keeps other nets' pads off it (lead 2026-11-22).

    py -3.12 test_pad_copper.py

brain_board sqp: D213 / TP2, released by a pair corridor, landed on +5V_CM5's declared F.Cu column
and only layout said so. Cases: 1 a pad across a foreign track is short by its overlap; 2 the
same net is not an obstacle; 3 a part the copper lands `on` is skipped; 4 a B.Cu track misses an F
SMD pad but meets a through-hole one; a via meets both; 5 place_init._drop seats a part dropped on
the track off it, clear by the net clearance; 6 place_flow stops, with no switch to turn it off.
Exit 0 = PASS.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_intent as pi  # noqa: E402
import place_init as pin  # noqa: E402

bad = []
R = {"pads": [{"num": "1", "net": "A", "xy": [-0.5, 0.0], "size": [0.6, 0.6], "rot": 0, "tht": False},
              {"num": "2", "net": "B", "xy": [0.5, 0.0], "size": [0.6, 0.6], "rot": 0, "tht": False}],
     "crtyd": [[-1.0, -0.5], [1.0, -0.5], [1.0, 0.5], [-1.0, 0.5]], "fab": None, "side": "F"}
T = dict(R, pads=[dict(q, tht=True) for q in R["pads"]])
rule = {"kind": "copper", "net": "P", "on": ["U1.1"], "tracks": [{"layer": "F.Cu", "width": 1.0, "pts": [[0.0, -5.0], [0.0, 5.0]]}]}
items = pi.declared_items([rule])
P = pi.Placed({"R1": R}, {"R1": [0.0, 0.0, 0]})
res = pi.pad_copper(P, items)
if not any(s < -0.3 and n == "R1.1" for s, n, _d in res):
    bad.append("1: R1.1 across the P track not reported short: %s" % res)
same = pi.declared_items([dict(rule, net="A")])
if any(n == "R1.1" and s < 0 for s, n, _d in pi.pad_copper(P, same)):
    bad.append("2: a pad on the copper's own net was reported")
P2 = pi.Placed({"U1": R}, {"U1": [0.0, 0.0, 0]})
if pi.pad_copper(P2, items):
    bad.append("3: the part the copper lands on was not skipped")
bk = pi.declared_items([dict(rule, tracks=[dict(rule["tracks"][0], layer="B.Cu")])])
if any(s < 0 for s, _n, _d in pi.pad_copper(P, bk)):
    bad.append("4: a B.Cu track met an F.Cu SMD pad")
if not any(s < 0 for s, _n, _d in pi.pad_copper(pi.Placed({"J1": T}, {"J1": [0.0, 0.0, 0]}), bk)):
    bad.append("4: a B.Cu track missed a through-hole pad")
via = pi.declared_items([{"kind": "copper", "net": "P", "vias": [[0.5, 0.0]]}])
if not any(s < 0 for s, _n, _d in pi.pad_copper(P, via)):
    bad.append("4: a via under a pad not reported")
far = pi.Placed({"R1": R}, {"R1": [3.0, 0.0, 0]})
if any(s < 0 for s, _n, _d in pi.pad_copper(far, items)):
    bad.append("1: R1 3 mm off the track still reported")
# 5: _drop
poly = [[-10, -10], [10, -10], [10, 10], [-10, 10]]
G = pin.Grid(poly, [], [])
pin.cu_grids(G, items)
pl = {}
if not pin._drop(G, {"R1": R}, "R1", np.array([0.0, 0.0]), [0.0], pl):
    bad.append("5: _drop found no seat")
else:
    s = min(x[0] for x in pi.pad_copper(pi.Placed({"R1": R}, pl), items) or [(9.0, "", "")])
    if s < -0.005:
        bad.append("5: _drop seated R1 at %s, %.3f short of the track" % (pl["R1"], -s))
    elif abs(pl["R1"][0]) > 3.0:
        bad.append("5: _drop seated R1 at %s, further than it needs" % pl["R1"])
src = open(os.path.join(HERE, "place_flow.py"), encoding="utf-8").read()
try:
    compile(src, "place_flow.py", "exec")
except SyntaxError as e:
    bad.append("6: place_flow.py does not compile: %s" % e)
if "PAD ON DECLARED COPPER" not in src or "PCBFLOW_PAD_COPPER" in src:
    bad.append("6: place_flow does not stop on a pad on declared copper")
for x in bad:
    print("  FAIL:", x)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
