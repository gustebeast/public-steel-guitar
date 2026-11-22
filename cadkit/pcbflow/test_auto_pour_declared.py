"""auto_pour skips a net with declared copper tracks, at any amps (2026-11-22).

    py -3.12 test_auto_pour_declared.py

brain_board esc13: +5V_CM5's declared path to J201 still drew a whole-net hull that took +5V_BB's
band room. 1. a 4 A net with declared copper gets no auto pour; 2. the same net without it does;
3. copper with no tracks (vias only) does not count. Exit 0 = PASS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_intent as pi  # noqa: E402

PARTS = {"R1": {"pads": [{"num": "1", "net": "N"}, {"num": "2", "net": "X"}]},
         "J1": {"pads": [{"num": "1", "net": "N"}]}}
AP = {"kind": "auto_pour", "amps": 4.0, "layer": "F.Cu"}
CUR = {"kind": "current", "net": "N", "amps": 4.0, "why": "t"}


def pours(rules):
    out, _ = pi.auto_pour(rules, PARTS)
    return [r for r in out if r["kind"] == "pour" and r["net"] == "N"]


bad = []
cop = {"kind": "copper", "net": "N", "tracks": [{"layer": "F.Cu", "width": 1.4, "pts": [[0, 0], [1, 0]]}]}
if pours([AP, CUR, cop]):
    bad.append("a net with declared copper tracks still got an auto pour")
if not pours([AP, CUR]):
    bad.append("a 4 A net with no declared copper got no auto pour")
if not pours([AP, CUR, dict(cop, tracks=[], vias=[[0, 0]])]):
    bad.append("vias-only copper suppressed the auto pour")
for x in bad:
    print("  FAIL:", x)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
