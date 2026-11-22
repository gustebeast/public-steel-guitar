"""place_flow warns on a tight rule that cannot act, and on an unmet one (2026-11-22).

    py -3.12 test_tight_warns.py

brain_board so_ovw8: U21_OVLO's tight named only U221 and two pin satellites (R319 / R320, small
parts with a `near` to U221.2); weight 2 and 8 placed identically, 5.7 mm against 3. 1. that shape
says TIGHT CANNOT ACT and TIGHT UNMET with the achieved value; 2. a tight with a free member says
no CANNOT ACT; 3. a met tight says nothing. Exit 0 = PASS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_flow as pf  # noqa: E402
import place_intent as pi  # noqa: E402


def res(n1, n2):
    return {"pads": [{"num": "1", "net": n1, "xy": [-0.5, 0], "size": [0.5, 0.5]},
                     {"num": "2", "net": n2, "xy": [0.5, 0], "size": [0.5, 0.5]}],
            "crtyd": [[-1, -0.5], [1, -0.5], [1, 0.5], [-1, 0.5]]}


ic = {"pads": [{"num": str(k), "net": ("OV" if k == 2 else "N%d" % k), "xy": [k * 0.5, 0], "size": [0.3, 0.3]}
               for k in range(1, 11)], "crtyd": [[-1, -1], [6, -1], [6, 1], [-1, 1]]}
parts = {"U1": ic, "R1": res("V", "OV"), "R2": res("OV", "G"), "R3": res("OV", "G")}
tight = {"kind": "tight", "nets": ["OV"], "max_mm": 3.0}
near = [{"kind": "near", "ref": "R1", "target": "U1.2", "max_mm": 6}, {"kind": "near", "ref": "R2", "target": "U1.2", "max_mm": 6}]
far = {"U1": [0, 0, 0], "R1": [4.5, 1.5, 0], "R2": [0.5, 3.0, 0], "R3": [30, 30, 0]}
P = pi.Placed({k: v for k, v in parts.items() if k != "R3"}, {k: v for k, v in far.items() if k != "R3"})
bad = []
w = pf._tight_warns(near + [tight], {k: v for k, v in parts.items() if k != "R3"}, P, {})
if not any(x.startswith("TIGHT CANNOT ACT") and "R1 R2" in x for x in w):
    bad.append("satellite-only tight: no CANNOT ACT (%s)" % w)
if not any(x.startswith("TIGHT UNMET") and "wants 3.0" in x for x in w):
    bad.append("unmet tight: no achieved-vs-asked line (%s)" % w)
P3 = pi.Placed(parts, far)
w3 = pf._tight_warns(near + [tight], parts, P3, {})
if any(x.startswith("TIGHT CANNOT ACT") for x in w3):
    bad.append("a tight with a free member (R3) still said CANNOT ACT")
close = {"U1": [0, 0, 0], "R1": [1.0, 0.8, 0], "R2": [1.0, -0.8, 0]}
P2 = pi.Placed({k: v for k, v in parts.items() if k != "R3"}, close)
w2 = pf._tight_warns([tight], {k: v for k, v in parts.items() if k != "R3"}, P2, {})
if w2:
    bad.append("a met tight with free members said %s" % w2)
for x in bad:
    print("  FAIL:", x)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
