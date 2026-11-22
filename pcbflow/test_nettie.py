"""nettie: one answer to "is this a net tie, and which nets does it join" (2026-11-22).

    py -3.12 test_nettie.py

quality A16 and elec/voltage_check.py both ask nettie.py; voltage_check once did not walk ties
and read PA_VCC_K at 0 V (U13.23 rated 4 V instead of 33). 1. NT11 / NT205 are ties, NTC1 / R1 /
JP1 are not; 2. a tie joins its nets, a chain of ties is one group, a non-tie joins nothing;
3. quality.py has no net-tie test of its own left (it imports is_net_tie). Exit 0 = PASS.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nettie import is_net_tie, tie_groups  # noqa: E402

bad = []
for ref, want in (("NT11", True), ("NT205", True), ("NTC1", False), ("R1", False), ("JP1", False), ("", False)):
    if is_net_tie(ref) != want:
        bad.append("is_net_tie(%r) = %s, wants %s" % (ref, not want, want))
g = tie_groups({"NT11": ["PA_ISENP", "PA_ISENP_K"], "NT12": ["PA_VCC", "PA_VCC_K"],
                "NT13": ["PA_VCC_K", "PA_VCC_K2"], "R70": ["PA_VBUS", "PA_VCC"]})
if g.get("PA_VCC_K") != frozenset({"PA_VCC", "PA_VCC_K", "PA_VCC_K2"}):
    bad.append("a chain of ties is not one group: %s" % g.get("PA_VCC_K"))
if g.get("PA_ISENP_K") != frozenset({"PA_ISENP", "PA_ISENP_K"}):
    bad.append("a tie does not join its two nets: %s" % g.get("PA_ISENP_K"))
if "PA_VBUS" in g:
    bad.append("a resistor (R70) joined nets as a tie")
src = open(os.path.join(HERE, "quality.py"), encoding="utf-8").read()
own = re.findall(r'(?:re\.match\(r"NT|startswith\("NT"\))', src)
if own or "from nettie import is_net_tie" not in src:
    bad.append("quality.py tests net ties itself (%d place(s)) instead of nettie.is_net_tie" % len(own))
for x in bad:
    print("  FAIL:", x)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
