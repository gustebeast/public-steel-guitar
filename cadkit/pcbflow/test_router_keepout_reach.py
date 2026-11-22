"""The router's keep-out field reaches as far as its widest net (brain_board rPS_11a3, 2026-11-22).

    py -3.12 test_router_keepout_reach.py <dir holding rPS_11a3's placed board as b.kicad_pcb /
        b.kicad_pro / b.board.json (the .unrouted board: the moat rule area, no routing)>

The keep-out distance field was written only via_r + margin + 1.0 (~1.4 mm) round each rule
area and read FAR beyond, so a 3.79 mm VIN_BUS run centred 1.38 mm off the audio moat was legal
and its edge sat 0.5 mm inside (DRC items_not_allowed, quality A25 hard on 3 of 5 esc11 seeds).
1. For EVERY track-banning rule area: the field is exact (not FAR) out to the widest net's
   need (width/2 + clearance + margin) beyond its edge, sampled outward from the box's sides.
2. On 11a3: B.Cu at (88.39, 70.0) is illegal for VIN_BUS (3.79 mm) and legal for a 0.25 track.
Exit 0 = PASS.
"""
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from router.model import Model, FAR  # noqa: E402

m = Model(os.path.join(os.path.abspath(sys.argv[1]), "b"))
bad = []
wmax = max(m.width.values())
need = wmax / 2.0 + m.clear + m.margin


def cell(x, y):
    return int(round((y - m.y0) / m.pitch)), int(round((x - m.x0) / m.pitch))


for z in m.keepouts:
    if not z["tracks"]:
        continue
    names = set(m.route_layers) if "*.Cu" in z["layers"] else set(z["layers"])
    xs = [q[0] for q in z["pts"]]
    ys = [q[1] for q in z["pts"]]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    for k, ln in enumerate(m.route_layers):
        if ln not in names:
            continue
        for dx, dy, x0, y0 in ((1, 0, max(xs), cy), (-1, 0, min(xs), cy), (0, 1, cx, max(ys)), (0, -1, cx, min(ys))):
            x, y = x0 + dx * (need - m.pitch), y0 + dy * (need - m.pitch)
            i, j = cell(x, y)
            if not (0 <= i < m.ny and 0 <= j < m.nx) or m.edge[i, j] <= 0:
                continue
            if m.d1[k, i, j] >= FAR / 2:
                bad.append("rule area at %.1f,%.1f: %s field FAR %.2f mm out (needs %.2f)"
                           % (cx, cy, ln, need - m.pitch, need))
k = m.route_layers.index("B.Cu")
i, j = cell(88.39, 70.0)
fd = m.d1[k, i, j]
w = m.width.get("VIN_BUS", 0)
print("VIN_BUS width %.2f; field at (88.39, 70.0) B.Cu %.3f; needs %.3f" % (w, fd, w / 2 + m.clear + m.margin))
if not fd < w / 2 + m.clear + m.margin:
    bad.append("VIN_BUS 3.79 is still legal centred 1.38 mm off the moat")
if not fd >= 0.25 / 2 + m.clear + m.margin:
    bad.append("a 0.25 track is refused 1.38 mm off the moat")
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.stdout.flush()
os._exit(1 if bad else 0)
