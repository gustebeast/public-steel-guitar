"""Overlapping legs of one rail become one pour (brain_board fold13, 2026-11-27).

    py -3.12 test_pour_union.py

fold13: V5_PRE's In3 legs L1.2-U211.1-U215.3 and U211.1-U36.5-R98.1 (width 1.8) met at U211.1,
both priority 3 -- DRC zones_intersect, and close_last left V5_PRE open. fold13's pin positions,
the hulls built as place_intent.pour_poly builds them; no files.
1. The two legs are one zone: its outline holds every pin and every corner of both legs, and its
   area is more than either leg's and less than their sum.
2. Two legs that do not meet stay two zones.
3. Legs that meet but declare different priorities are refused (POUR OVERLAP), not left to DRC.
4. A leg inside another is absorbed; another net's overlapping pour is left alone.
Exit 0 = PASS.
"""
import math
import os
import sys

import numpy as np
from scipy.spatial import ConvexHull

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_flow as pf  # noqa: E402

bad = []
PIN = {"L1.2": (110.89, 139.18), "U211.1": (123.83, 116.86), "U215.3": (145.53, 138.46),
       "U36.5": (124.73, 65.20), "R98.1": (126.69, 51.54), "U206.1": (97.62, 114.75)}


def hull(pins, w=1.8):
    r = w / 2.0
    pts = np.array([(PIN[p][0] + r * math.cos(a), PIN[p][1] + r * math.sin(a))
                    for p in pins for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)])
    h = ConvexHull(pts)
    return [[round(float(x), 3), round(float(y), 3)] for x, y in pts[h.vertices]]


def area(p):
    return abs(sum(p[i - 1][0] * p[i][1] - p[i][0] * p[i - 1][1] for i in range(len(p)))) / 2.0


def zone(pins, net="V5_PRE", pr=3, **kw):
    return dict(net=net, layer="In3.Cu", poly=hull(pins), priority=pr, **kw)


def near_or_in(pt, poly, tol=0.01):
    if pf._inside(pt, poly):
        return True
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        ux, uy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((pt[0] - x1) * ux + (pt[1] - y1) * uy) / max(ux * ux + uy * uy, 1e-12)))
        if math.hypot(pt[0] - x1 - t * ux, pt[1] - y1 - t * uy) < tol:
            return True
    return False


# 1. fold13's two In3 legs
a, b = zone(["L1.2", "U211.1", "U215.3"]), zone(["U211.1", "U36.5", "R98.1"])
got, lines = pf.merge_same_net_pours([a, b])
print("1:", len(got), "zone(s);", lines)
if len(got) != 1:
    bad.append("1: the two legs stayed %d zones" % len(got))
else:
    u = got[0]["poly"]
    print("   areas: legs %.1f + %.1f, joined %.1f mm2" % (area(a["poly"]), area(b["poly"]), area(u)))
    if not (max(area(a["poly"]), area(b["poly"])) < area(u) < area(a["poly"]) + area(b["poly"])):
        bad.append("1: joined area %.1f not between the larger leg and the sum" % area(u))
    for p in ("L1.2", "U211.1", "U215.3", "U36.5", "R98.1"):
        if not pf._inside(PIN[p], u):
            bad.append("1: %s is outside the joined pour" % p)
    miss = [c for c in a["poly"] + b["poly"] if not near_or_in(c, u)]
    if miss:
        bad.append("1: %d leg corner(s) outside the joined pour, e.g. %s" % (len(miss), miss[0]))

# 2. two legs that do not meet
c = zone(["U36.5", "R98.1"])
got, _ = pf.merge_same_net_pours([zone(["L1.2", "U215.3"]), c])
print("2:", len(got), "zone(s)")
if len(got) != 2:
    bad.append("2: legs that do not meet were joined")

# 3. different priorities: refused by name
try:
    pf.merge_same_net_pours([a, dict(b, priority=7)])
    bad.append("3: legs of different priority were not refused")
except SystemExit as e:
    print("3: refused --", str(e)[:90])
    if "POUR OVERLAP" not in str(e):
        bad.append("3: refused without the POUR OVERLAP name")

# 4. a leg inside another is absorbed; another net's pour is left alone
inner = zone(["U211.1"])
other = zone(["U211.1", "U36.5"], net="+24V", pr=1)
got, _ = pf.merge_same_net_pours([a, inner, other])
print("4:", [(z["net"], len(z["poly"])) for z in got])
if len(got) != 2 or abs(area(got[0]["poly"]) - area(a["poly"])) > 0.05 or got[1] is not other:
    bad.append("4: inner leg not absorbed or the other net's pour touched")

print("\n".join(bad) if bad else "PASS")
sys.exit(1 if bad else 0)
