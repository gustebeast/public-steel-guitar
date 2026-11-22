"""check_declare_guard.py -- voltage_check.declare_diff flags a lowered declared max (2026-11-22).

    py -3.12 elec/check_declare_guard.py

The 33.088 -> 4.0 V fall on U13.23 is LOWER; a rise is a change, not LOWER; a numeric max that
becomes "none" or vanishes is LOWER; a new pin and an unchanged one are not. Exit 0 = PASS."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from voltage_check import declare_diff  # noqa: E402

old = {"U13.23": {"max": 33.088}, "R1.1": {"max": 50.0}, "R2.1": {"max": 50.0}, "R3.1": {"max": 50.0},
       "R4.1": {"max": "none"}, "R5.1": {"max": 6.5}}
new = {"U13.23": {"max": 4.0}, "R1.1": {"max": 75.0}, "R2.1": {"max": "none"}, "R4.1": {"max": "none"},
       "R5.1": {"max": 6.5}, "R6.1": {"max": 6.5}}
got = {k: low for k, _line, low in declare_diff(old, new)}
want = {"U13.23": True, "R1.1": False, "R2.1": True, "R3.1": True, "R6.1": False}
bad = ["%s: %s, wants %s" % (k, got.get(k, "no line"), w) for k, w in want.items() if got.get(k) != w]
bad += ["%s: a line for an unchanged pin" % k for k in got if k not in want]
for x in bad:
    print("  FAIL:", x)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
