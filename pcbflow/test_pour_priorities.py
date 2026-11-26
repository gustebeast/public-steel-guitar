"""A declared pour priority is a fixed point: undeclared pours number BELOW it, never over it.

    py -3.12 test_pour_priorities.py

place_flow.pour_priorities on stub zone lists (no board): the brain_board fold6 case (BST_LMID
declared 11, then BST_SW and +24V undeclared -- they come out 1 and 2, below 11, in rule order,
where the old rule made them 12 and 13 and +24V filled over BST_LMID); the full fold6 F.Cu list
(12 undeclared nets do not fit under 11, so the declared block rises to 13 and +24V stays under
it); two declared pours keep their gap when lifted; no declared pour = 1, 2, ...; a second zone
of the same net shares its number; layers are numbered independently. Exit 0 = PASS.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from place_flow import pour_priorities  # noqa: E402

bad = []


def z(net, pr=None, layer="F.Cu"):
    return {"net": net, "layer": layer, "priority": pr}


def pr(zs):
    return {(q["net"], q["layer"]): q["priority"] for q in zs}


# 1. fold6: declared 11, two undeclared after it
zs = [z("BST_LMID", 11), z("BST_SW"), z("+24V")]
pour_priorities(zs)
p = pr(zs)
if not (p[("BST_SW", "F.Cu")] < p[("+24V", "F.Cu")] < p[("BST_LMID", "F.Cu")] == 11):
    bad.append("fold6 case: %s (want BST_SW < +24V < BST_LMID, BST_LMID kept at 11)" % p)
if p[("BST_SW", "F.Cu")] < 1:
    bad.append("undeclared pours must start at 1 (above a 0 plane): %s" % p)

# 2. the whole fold6 F.Cu list: 12 undeclared nets do not fit under 11 -> the declared block lifts
auto_a = ["PA_VBUS", "PA_VCC", "PA_VOUT", "PB_VBUS", "PB_VCC", "PB_VOUT", "VIN_SW"]
auto_b = ["BST_SW", "+24V", "+24V_RIB", "PA_VBUS_J", "PB_VBUS_J"]
zs = [z(n) for n in auto_a] + [z("BST_LMID", 11)] + [z(n) for n in auto_b]
rep = pour_priorities(zs)
p = pr(zs)
autos = [p[(n, "F.Cu")] for n in auto_a + auto_b]
if autos != list(range(1, 13)):
    bad.append("undeclared pours should keep rule order, 1..12: %s" % autos)
if p[("BST_LMID", "F.Cu")] != 13:
    bad.append("declared 11 under 12 undeclared should lift to 13, got %d" % p[("BST_LMID", "F.Cu")])
if rep != [("F.Cu", sorted(((n, v) for (n, _l), v in p.items()), key=lambda t: t[1]))]:
    bad.append("report order: %s" % rep)

# 3. two declared pours rise as a block, keeping their order and gap
zs = [z("A", 2), z("B", 5), z("X"), z("Y"), z("Z")]
pour_priorities(zs)
p = pr(zs)
if (p[("A", "F.Cu")], p[("B", "F.Cu")]) != (4, 7) or [p[(n, "F.Cu")] for n in "XYZ"] != [1, 2, 3]:
    bad.append("block lift: %s (want X1 Y2 Z3, A4 B7)" % p)

# 4. nothing declared: 1, 2, ... (motor_ctrl +5V_RAW / +5V never share a number)
zs = [z("+5V_RAW"), z("+5V")]
pour_priorities(zs)
if [q["priority"] for q in zs] != [1, 2]:
    bad.append("undeclared only: %s" % [q["priority"] for q in zs])

# 5. same net twice shares a number; other layers numbered on their own
zs = [z("+24V"), z("GNDX", 3), z("+24V"), z("VB", layer="B.Cu"), z("VC", 1, layer="B.Cu")]
pour_priorities(zs)
got = [q["priority"] for q in zs]
if got != [1, 3, 1, 1, 2]:
    bad.append("same net / per layer: %s (want [1, 3, 1, 1, 2])" % got)

for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
