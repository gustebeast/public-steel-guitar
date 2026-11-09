"""Where the nets fought: the negotiation's history cost as placement feedback.

Every round a cell is shared, its history price rises, so after routing `Router.hist` is a
map of contested space. Clustered and named by the parts beside it, it is what an engineer
reads off a ratsnest before moving parts: "the strip west of U1 is over-subscribed"."""
from __future__ import annotations

import math
import re

import numpy as np


def _refs(txt):
    out = []
    for f in re.findall(r"\(footprint\b(.*?)\n\t\)", txt, re.S):
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", f)
        rf = re.search(r'\(property "Reference" "([^"]+)"', f)
        if at and rf:
            out.append((rf.group(1), float(at.group(1)), float(at.group(2))))
    return out


def hotspots(router, top=8, cell_mm=2.0):
    """[(score, x, y, layers, [nearest refs])] for the most contested `cell_mm` squares."""
    m = router.m
    L, H, W = router.L, router.H, router.W
    hist = router.hist.reshape(L, H, W)
    if not hist.any():
        return []
    b = max(1, int(round(cell_mm / m.pitch)))
    hh, ww = H // b, W // b
    blk = hist[:, :hh * b, :ww * b].reshape(L, hh, b, ww, b).sum(axis=(2, 4))
    tot = blk.sum(axis=0)
    order = np.argsort(tot.ravel())[::-1]
    refs = _refs(m.txt)
    out, taken = [], []
    for o in order:
        if tot.flat[o] <= 0 or len(out) >= top:
            break
        bi, bj = divmod(int(o), ww)
        if any(abs(bi - a) <= 1 and abs(bj - c) <= 1 for a, c in taken):
            continue
        taken.append((bi, bj))
        x, y = m.xy(int((bi + 0.5) * b), int((bj + 0.5) * b))
        layers = [m.route_layers[k] for k in range(L) if blk[k, bi, bj] > 0.25 * tot[bi, bj]]
        near = sorted(refs, key=lambda r: math.hypot(r[1] - x, r[2] - y))[:3]
        out.append((float(tot[bi, bj]), x, y, layers, [r[0] for r in near]))
    return out


def report(router, log=print, top=8):
    hs = hotspots(router, top=top)
    if not hs:
        log("ownroute: no contested space -- every net had room from round one")
        return
    log("ownroute: most contested space (where placement would buy routing room):")
    for s, x, y, layers, near in hs:
        log("    %6.1f  at (%.1f, %.1f) on %s, beside %s"
            % (s, x, y, "/".join(layers) or "-", ", ".join(near)))


def pair_dives(router, log=print):
    """Where a same_layer pair had to leave its layers: placement feedback, not routing.

    ⚠ A PAIR CAN BE TWISTED BY ITS PLACEMENT (optical USB_DP / USB_DM, 2026-11-08). U10, a
    pass-through clamp, keeps D+ north of D- on both faces; leaving its east face the pair
    has D+ on its left, and turning south into U31's top edge puts D+ on the east -- but
    U31 has D+ to the WEST. No route in one plane undoes that twist, so one rail must change
    layer, and quality A3 fails the pair whatever the router does. The fix is a part turned
    (U10 by 180 degrees) or a pin order, so this reports where the dive is and what is
    around it rather than the router pretending."""
    m = router.m
    H, W = router.H, router.W
    refs = _refs(m.txt)
    seen = set()
    for net in router.nets:
        home = net.run_layers or net.layers_only
        if not (net.same_layer and home) or net.name in seen:
            continue
        for pth in net.paths:
            k = pth // (H * W)
            r = pth % (H * W)
            at = [i for i in range(len(k) - 1) if k[i] != k[i + 1]]
            off = [i for i in range(len(k)) if int(k[i]) not in home]
            if not off:
                continue
            i = off[len(off) // 2]
            x, y = float(m.cx[r[i] % W]), float(m.cy[r[i] // W])
            if net.merge is not None and math.hypot(x - net.merge[0], y - net.merge[1]) < net.merge[2]:
                continue
            near = sorted(refs, key=lambda q: math.hypot(q[1] - x, q[2] - y))[:3]
            mate = net.partner.name if net.partner is not None else "its pair"
            log("ownroute: %s left its layers for %.1f mm at (%.1f, %.1f), beside %s: the pair "
                "with %s crosses itself there -- a placement twist (turn a part, or swap a pin "
                "order); routing cannot keep it on one layer"
                % (net.name, len(off) * m.pitch, x, y, ", ".join(q[0] for q in near), mate))
            seen.add(net.name)
            break
