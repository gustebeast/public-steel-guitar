"""A pour pin named in the rule's `no_escape` gets no escape stub (brain_board fold8, 2026-11-26).

    py -3.12 test_no_escape.py

U1 has two 0.30 x 2.40 pins on 0.5 pitch (U221.5 / .6 of a TPS259470A) and R1 a 1 x 1.4 land 10 mm
off: pin_escapes gives U1.6 a stub by default (its neighbour is 0.2 mm away, under twice the zone
clearance) and none when the rule lists U1.6 in no_escape. Exit 0 = PASS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_intent as pi  # noqa: E402

pin = lambda n, y, net: {"num": n, "xy": [0.0, y], "size": [2.4, 0.3], "net": net, "rot": 0.0}
parts = {"U1": {"side": "F", "pads": [pin("5", -0.25, "IN"), pin("6", 0.25, "OUT")], "crtyd": None, "fab": None},
         "R1": {"side": "F", "pads": [{"num": "1", "xy": [0.0, 0.0], "size": [1.0, 1.4], "net": "OUT", "rot": 0.0}],
                "crtyd": None, "fab": None}}
P = pi.Placed(parts, {"U1": [0.0, 0.0, 0.0], "R1": [10.0, 0.25, 0.0]})
rule = {"kind": "pour", "net": "OUT", "layer": "B.Cu", "along": ["U1.6", "R1.1"], "width_mm": 1.45}
bad = []
got = pi.pin_escapes(rule, P, {"zone_clearance": 0.5})
if not any(e["key"].startswith("U1.6") or "U1.6" in e["key"] for e in got):
    bad.append("no stub for U1.6 by default (the test's premise): %s" % got)
got2 = pi.pin_escapes(dict(rule, no_escape=["U1.6"]), P, {"zone_clearance": 0.5})
if got2:
    bad.append("U1.6 named in no_escape still got a stub: %s" % got2)
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
