"""Exact clearance of the copper the router writes (ROUTER.md M2), before KiCad sees it.

The negotiation works on a 0.05 mm grid with a margin, so its paths are clear by
construction -- but emit.py finishes every path with copper the grid never saw: a stub into
the middle of a land, a stub onto the centre of a declared via, a stub onto a fixed track's
centreline. Those were never measured, and a post-route pass later found them by DRC and
took up the router track instead (optical USB_DP crowding USB_DM between J1 and U10,
2026-11-09: the track went, close_last closed the rail the long way, the pair's skew
failed). This measures every emitted segment and via against every other net's copper --
fixed pads by their exact shape, fixed tracks and vias, and the other nets' new copper --
and names each shortfall with what drew it.
"""
from __future__ import annotations

import math

import numpy as np

from .model import pad_dist
from . import emit

TOL = 0.002          # mm: rounding the board file allows


def _seg_seg(a, b):
    """Distance between segments a = (x1, y1, x2, y2) and b."""
    def ps(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
        return math.hypot(px - x1 - t * dx, py - y1 - t * dy)

    def side(ux, uy, vx, vy, wx, wy):
        return (vx - ux) * (wy - uy) - (vy - uy) * (wx - ux)
    (a1, a2, a3, a4), (b1, b2, b3, b4) = a, b
    if (side(a1, a2, a3, a4, b1, b2) * side(a1, a2, a3, a4, b3, b4) < 0
            and side(b1, b2, b3, b4, a1, a2) * side(b1, b2, b3, b4, a3, a4) < 0):
        return 0.0
    return min(ps(b1, b2, a1, a2, a3, a4), ps(b3, b4, a1, a2, a3, a4),
               ps(a1, a2, b1, b2, b3, b4), ps(a3, a4, b1, b2, b3, b4))


def _kind(it, ends):
    """What drew this item: a grid run, or a finishing stub (one end at a land/via/track)."""
    if it[0] == "via":
        return "via"
    return "stub" if ((round(it[4], 4), round(it[5], 4)) in ends) else "run"


def check(m, nets, limit=40):
    """[(gap_short_mm, net, layer, x, y, kind, against)] for every new item closer to another
    net's copper than the clearance, worst first."""
    clr = m.clear
    shapes = []                                 # (net, layer|None, (x1,y1,x2,y2), half, kind)
    for net in nets:
        items, _ = emit.net_items(m, net)
        land = {(round(p["gx"], 4), round(p["gy"], 4)) for p in m.pads if p["net"] == net.name}
        land |= {(round(v["x"], 4), round(v["y"], 4)) for v in m.vias if v["net"] == net.name}
        for it in items:
            if it[0] == "seg":
                k = "stub" if (round(it[4], 4), round(it[5], 4)) in land else "run"
                shapes.append((net.name, it[1], (it[2], it[3], it[4], it[5]), it[6] / 2.0, k))
            else:
                shapes.append((net.name, None, (it[1], it[2], it[1], it[2]), m.via_d / 2.0, "via"))
    fixed = [(s["net"], s["layer"], (s["x1"], s["y1"], s["x2"], s["y2"]), s["half"], "track")
             for s in m.segs]
    fixed += [(v["net"], None, (v["x"], v["y"], v["x"], v["y"]), v["r"], "via") for v in m.vias]
    out = []
    # pads: sample each new item finely against nearby pads of other nets
    for net, L, (x1, y1, x2, y2), h, k in shapes:
        n = max(2, int(math.hypot(x2 - x1, y2 - y1) / 0.01) + 1)
        X = np.linspace(x1, x2, n)[None]
        Y = np.linspace(y1, y2, n)[None]
        bx0, bx1 = min(x1, x2) - h - 2, max(x1, x2) + h + 2
        by0, by1 = min(y1, y2) - h - 2, max(y1, y2) + h + 2
        for p in m.pads:
            if p["net"] == net or not (bx0 <= p["gx"] <= bx1 and by0 <= p["gy"] <= by1):
                continue
            if L is not None and p["cu"] is not None and L not in p["cu"]:
                continue
            d = float(pad_dist(p, X, Y).min()) - h
            if d < clr - TOL:
                out.append((round(clr - d, 3), net, L or "via", round(x1, 3), round(y1, 3), k,
                            "pad %s" % (p.get("name") or p["net"] or "<no net>")))
    # tracks and vias: new against fixed and against other nets' new copper
    allc = shapes + fixed
    idx = sorted(range(len(allc)), key=lambda i: min(allc[i][2][0], allc[i][2][2]))
    reach = 2.0
    for ai in range(len(idx)):
        a = allc[idx[ai]]
        ax1 = max(a[2][0], a[2][2])
        for bi in range(ai + 1, len(idx)):
            b = allc[idx[bi]]
            if min(b[2][0], b[2][2]) > ax1 + reach:
                break
            if a[0] == b[0] or (idx[ai] >= len(shapes) and idx[bi] >= len(shapes)):
                continue
            if a[1] is not None and b[1] is not None and a[1] != b[1]:
                continue
            d = _seg_seg(a[2], b[2]) - a[3] - b[3]
            if d < clr - TOL:
                new, oth = (a, b) if idx[ai] < len(shapes) else (b, a)
                out.append((round(clr - d, 3), new[0], new[1] or "via", round(new[2][0], 3),
                            round(new[2][1], 3), new[4], "%s %s" % (oth[0] or "<no net>", oth[4])))
    out.sort(key=lambda r: -r[0])
    return out[:limit]
