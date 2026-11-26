"""close_last's power guard is always on: a net with stated current is never closed narrower
than its drawn width (brain_board fold7c, 2026-11-26: +24V "closed" with 0.20 mm on In2).

    py -3.12 test_close_power_guard.py

Source checks (the ladder is inline in close_last's main loop): no CLOSE_POWER_GUARD switch,
the ladder is cut at the drawn width for every net with amps, outer layers first and then
every layer at its own (wider, inner) need, and the CAN'T CARRY open stays.
Exit 0 = PASS.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "close_last.py"), encoding="utf-8").read()
bad = []
if "CLOSE_POWER_GUARD" in src or re.search(r"\bPOWER_GUARD\b", src):
    bad.append("the guard is behind a switch again (CLOSE_POWER_GUARD / POWER_GUARD)")
if "        if _amps:\n" not in src.replace("\r\n", "\n") or "brk_amps = _break_amps(" not in src:
    bad.append("the width ladder is not cut for every break with stated current")
if "w_ >= _need]" not in src:
    bad.append("the ladder no longer stops at the drawn width (_need)")
if "CAN'T CARRY" not in src:
    bad.append("a power net with no wide path is no longer left open as CAN'T CARRY")
if "nw=_need_all)" not in src:
    bad.append("the rip-up is not sized for the widest layer it may use (nw=_need_all)")
if '_out = [L_ for L_ in layers if L_ in ("F.Cu", "B.Cu")]' not in src or "_drawn_w(_amps, L_, _qn)" not in src:
    bad.append("a power closure is not searched outer-first, then at every layer's own need")
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
