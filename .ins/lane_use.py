"""How much of the strip widening does the routed optical board actually use?

Reads .ins/board_dump.json (board-local, from .ins/dump.py) and the CAD geometry, and
reports, for the -X lane (x < old -X edge) and the +X lane (x > old +X edge) of the
sensing strip: copper per layer, how deep it reaches, and how many DISTINCT tracks cross
each Y slice (the width a lane actually needs is set by the busiest slice)."""
import json
import math
import sys
from collections import defaultdict

sys.path.insert(0, '.')
import src.optical_pickup as OP

d = json.load(open('.ins/board_dump.json'))
xs = [v for s in OP._SECTIONS for v in (s[2], s[3])]
ys = [v for s in OP._SECTIONS for v in (s[0], s[1])]
CX, CY = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
OLD_MX = OP.PCB_X1S                          # the strip's -X edge before widening
OLD_PX = OP.PCB_X0 - OP.STRIP_GROW_PX        # its +X edge before widening
Y0, Y1 = OP.Y_TAIL, OP.HEAD_Y0               # the strip section
NEW_MX, NEW_PX = OP.STRIP_X1, OP.PCB_X0


def cad(p):
    return p[0] + CX, p[1] + CY


def clip_x(a, b, xlo, xhi):
    """Portion of segment a-b with x in [xlo, xhi]; None if empty."""
    (x0, y0), (x1, y1) = a, b
    if x0 == x1:
        return (a, b) if xlo <= x0 <= xhi else None
    t0, t1 = sorted(((xlo - x0) / (x1 - x0), (xhi - x0) / (x1 - x0)))
    t0, t1 = max(t0, 0.0), min(t1, 1.0)
    if t0 >= t1:
        return None
    return ((x0 + t0 * (x1 - x0), y0 + t0 * (y1 - y0)),
            (x0 + t1 * (x1 - x0), y0 + t1 * (y1 - y0)))


for name, xlo, xhi, deep in (("-X lane", NEW_MX, OLD_MX, min), ("+X lane", OLD_PX, NEW_PX, max)):
    length = defaultdict(float)
    reach = None
    nets = set()
    slices = defaultdict(set)                 # (layer, y-bin) -> nets crossing
    for (s, e, w, layer, net) in d['tracks']:
        a, b = cad(s), cad(e)
        if not (Y0 <= a[1] <= Y1 or Y0 <= b[1] <= Y1):
            continue
        seg = clip_x(a, b, xlo, xhi)
        if not seg:
            continue
        (p, q) = seg
        length[layer] += math.hypot(q[0] - p[0], q[1] - p[1])
        nets.add(net)
        edge = deep(p[0], q[0]) + (-w / 2 if deep is min else w / 2)
        reach = edge if reach is None else deep(reach, edge)
        ylo, yhi = sorted((p[1], q[1]))
        for k in range(int((ylo - Y0) / 0.5), int((yhi - Y0) / 0.5) + 1):
            yb = Y0 + k * 0.5
            if Y0 <= yb <= Y1:
                slices[(layer, k)].add(net)
    vias = [v for v in d['vias'] if xlo <= cad(v[:2])[0] <= xhi and Y0 <= cad(v[:2])[1] <= Y1]
    peak = defaultdict(int)
    for (layer, k), ns in slices.items():
        peak[layer] = max(peak[layer], len(ns))
    width = abs(xhi - xlo)
    used = (OLD_MX - reach) if deep is min and reach is not None else \
           ((reach - OLD_PX) if reach is not None else 0.0)
    print("== %s: %.2f mm added" % (name, width))
    print("   copper per layer (mm): %s" % {k: round(v, 1) for k, v in sorted(length.items())})
    print("   vias in the lane: %d   distinct nets: %d" % (len(vias), len(nets)))
    print("   deepest copper: %.2f mm into the lane (%.0f %% of it)" % (used, 100 * used / width))
    print("   busiest 0.5 mm slice, nets side by side per layer: %s" % dict(peak))
    print("   nets: %s" % sorted(nets)[:40])
