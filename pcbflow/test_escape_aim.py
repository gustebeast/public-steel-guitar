"""A pour pin's escape stub leaves from the end nearest the band's next pin, or not at all
(brain_board fold8, 2026-11-26: U221.6's east end was fenced by U221.10's corner pad, so the
stub fell back to the WEST end and ran into U221.5's +5V_RAW foot).

    py -3.12 test_escape_aim.py

U1 has two 0.30 x 2.40 pins on 0.5 pitch (U221.5 / .6 of a TPS259470A).
  1. the band's next pin is west: the stub runs west from U1.6;
  2. the next pin is west but the band's later pins are east: the NEXT pin decides (west),
     not the centroid of the band's other pins (east);
  3. a foreign corner pad fences the end facing the next pin: no stub (never the far end).
Exit 0 = PASS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_intent as pi  # noqa: E402

pin = lambda n, x, y, net, sx=2.4, sy=0.3: {"num": n, "xy": [x, y], "size": [sx, sy], "net": net, "rot": 0.0}
land = lambda: {"side": "F", "pads": [pin("1", 0.0, 0.0, "OUT", 1.0, 1.4)], "crtyd": None, "fab": None}


def stubs(u1_pads, at, along):
    parts = dict({"U1": {"side": "F", "pads": u1_pads, "crtyd": None, "fab": None}},
                 **{k: land() for k in at})
    P = pi.Placed(parts, dict({"U1": [0.0, 0.0, 0.0]}, **{k: [x, 0.25, 0.0] for k, x in at.items()}))
    rule = {"kind": "pour", "net": "OUT", "layer": "B.Cu", "along": along, "width_mm": 1.45}
    return [e for e in pi.pin_escapes(rule, P, {"zone_clearance": 0.5}) if e["key"] == "U1.6"]


bad = []
row = [pin("5", 0.0, -0.25, "IN"), pin("6", 0.0, 0.25, "OUT")]
g = stubs(row, {"R1": -10.0}, ["U1.6", "R1.1"])
if len(g) != 1 or not g[0]["pts"][1][0] < -1.2:
    bad.append("next pin west: want one stub running west of the pin, got %s" % g)
g = stubs(row, {"R1": -10.0, "R2": 20.0, "R3": 20.0}, ["U1.6", "R1.1", "R2.1", "R3.1"])
if len(g) != 1 or not g[0]["pts"][1][0] < -1.2:
    bad.append("next pin west, later pins east: want the stub west (the next pin), got %s" % g)
fence = row + [pin("10", 1.45, 0.55, "X", 0.25, 0.25)]
g = stubs(fence, {"R1": 10.0}, ["U1.6", "R1.1"])
if g:
    bad.append("east end fenced by a foreign pad: want no stub, got %s" % g)
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
