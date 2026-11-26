"""One via need for the router and the gate (copper.via_drill_mm / via_barrel_mm).

    py -3.12 test_via_need.py

The drill the router sizes is the smallest 0.05 step whose barrel is at least the gate's need,
for every current: +24V's 3 A at 20 C (need 0.89760, a 0.40 barrel 0.89760 short by 6 um) gets
0.45; the gate (widepath, rasterpath), power_vias, quality A1 and the router read the barrel
and the need from copper.py alone. Exit 0 = PASS.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import copper  # noqa: E402
import widepath  # noqa: E402

bad = []
q20 = {"temp_rise_c": 20.0}
if copper.via_drill_mm(3.0, q20) != 0.45:
    bad.append("+24V 3 A at 20 C: drill %s, want 0.45 (0.40's barrel is under the need)" % copper.via_drill_mm(3.0, q20))
for q in ({"temp_rise_c": 10.0}, q20, {"temp_rise_c": 20.0, "copper_oz": 2.0}):
    for i in range(1, 400):
        a = i * 0.025
        d = copper.via_drill_mm(a, q)
        need = copper.required_width_mm(a, "F.Cu", q)
        if copper.via_barrel_mm(d) < need:
            bad.append("%.3f A %s: drill %.2f barrel %.5f < need %.5f" % (a, q, d, copper.via_barrel_mm(d), need))
        if d > 0.05 + 1e-9 and copper.via_barrel_mm(d - 0.05) >= need:
            bad.append("%.3f A %s: drill %.2f not the smallest" % (a, q, d))
if copper.via_drill_mm(20.0, q20, max_mm=0.8) != 0.8:
    bad.append("max_mm cap not applied")
if widepath.PLATING is not copper.PLATING and widepath.PLATING != copper.PLATING:
    bad.append("widepath's barrel derating is not copper.PLATING")
for f, want in (("router/model.py", "copper.via_drill_mm("), ("rasterpath.py", "via_barrel_mm(hd)"),
                ("power_vias.py", "return via_barrel_mm(drill_mm)"), ("quality.py", "via_barrel_mm(MM(")):
    src = open(os.path.join(HERE, f), encoding="utf-8").read()
    if want not in src:
        bad.append("%s does not take the via from copper.py (%s)" % (f, want))
    if "25.0 / 35.0" in src.replace("# ", "#"):
        lines = [l for l in src.splitlines() if "25.0 / 35.0" in l and not l.lstrip().startswith("#")]
        if lines:
            bad.append("%s still has its own barrel derating: %s" % (f, lines[0].strip()))
for b_ in bad[:20]:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
