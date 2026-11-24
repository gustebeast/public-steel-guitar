"""Bottleneck report: the global plan read the way an engineer reads a ratsnest.

    py -3.12 -m router.bottleneck <stem> [--top 6] [--json out.json]

<stem> is a laid-out, UNROUTED board (layout.py's output; a trial's *.unrouted.kicad_pcb
copied to <stem>.kicad_pcb). Reports only -- changes nothing.

For each crowded strip (a cluster of squares where the global plan wants more tracks than
fit, globalroute.SCORE_UTIL), the question an engineer asks: "these nets all want through
here -- which of them MUST, and which can go round, at what cost?"

  1. the nets whose plan crosses the strip, each classed: pair (a matched/diff pair -- keeps
     its channel), power (wider than the board's signal width), signal;
  2. each net re-planned with the strip blocked (every layer, its own lands excepted), on the
     negotiated congestion prices: the DETOUR in mm, or MUST CROSS when it has no way round
     (a land in the strip, or the strip walls it off);
  3. the engineer's order: must-cross and pairs keep the strip, power next, signals give way
     cheapest detour first -- moved out one at a time until the strip fits; the report names
     the ones that go round and what it costs.

The plan's numbers are coarse (1 mm squares, track counts at SCORE_UTIL): read it as where
and who, not as exact millimetres.
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np

from . import globalroute as GR
from . import search as S


def _cls(net, sig_w):
    if getattr(net, "partner", None) is not None or getattr(net, "mate", None) is not None:
        return "pair"
    if net.width and net.width > sig_w + 1e-6:
        return "power"
    return "signal"


def _plan_len(g, paths):
    gg = g.gh * g.gw
    n = 0
    for p in paths:
        k = p // gg
        n += int(p.size) - int(np.count_nonzero(k[1:] != k[:-1])) + int(np.count_nonzero(k[1:] != k[:-1])) * GR.VIA_GC
    return n * g.gc_mm


def _replan(g, net, cost, block2d):
    """The net's plan on `cost` with the 2-D mask `block2d` closed on every layer (its own
    land squares stay open). None when a piece cannot reach the tree."""
    c = cost.copy()
    c[:, block2d] = np.inf
    old = S.astar_s
    miss = []

    def wrapped(*a):
        p = old(*a)
        if p.size == 0:
            miss.append(1)
        return p
    S.astar_s = wrapped
    try:
        paths = g._route(net, c)
    finally:
        S.astar_s = old
    return None if miss else paths


def report(stem, top=6, log=print):
    from .model import Model
    from .negotiate import Router
    from scipy import ndimage
    m = Model(stem)
    r = Router(m)
    r.log = lambda s: None
    r.build_nets(pours=m.fills)
    g = GR.GlobalRouter(r, log=lambda *a: None, util=GR.SCORE_UTIL, width_weight=True).run()
    L, gh, gw, gg = g.L, g.gh, g.gw, g.gh * g.gw
    over = np.maximum(g.use - g.cap, 0.0)
    hot = over.sum(axis=0) > 0
    lab, nlab = ndimage.label(ndimage.binary_dilation(hot, iterations=1), structure=np.ones((3, 3)))
    lab = np.where(hot, lab, 0)
    clusters = sorted(range(1, nlab + 1), key=lambda c: -float(over[:, lab == c].sum()))[:top]
    nets = {n.name: n for n in g._nets()}
    sig_w = float(m.notes.get("signal_width", 0) or 0) or min(n.width for n in nets.values() if n.width)
    pf = 0.5 * 1.5 ** (g.rounds - 1)
    cost = g._cost(min(pf, 50.0))
    from .congestion import _refs
    refs = _refs(m.txt)
    out = []
    log("bottleneck: %s -- %d crowded strip(s); global plan overflow %.1f over %d square(s)"
        % (stem, nlab, float(over.sum()), int(hot.sum())))
    for ci, c in enumerate(clusters, 1):
        sq = lab == c
        ii, jj = np.nonzero(sq)
        x = m.x0 + (jj.mean() + 0.5) * g.gc_mm
        y = m.y0 + (ii.mean() + 0.5) * g.gc_mm
        near = [q[0] for q in sorted(refs, key=lambda q: math.hypot(q[1] - x, q[2] - y))[:4]]
        ov = float(over[:, sq].sum())
        layers = [m.route_layers[k] for k in range(L) if over[k, sq].sum() > 0.2 * ov]
        rows = []
        for name, net in nets.items():
            paths = g.plans.get(name) or []
            if not paths:
                continue
            cells = np.unique(np.concatenate(paths))
            own = set(g.terms.get(name, np.zeros(0, np.int64)).tolist())
            cross = [q for q in cells.tolist() if sq[(q % gg) // gw, q % gw] and q not in own]
            if not cross:
                continue
            lands_here = any(sq[(q % gg) // gw, q % gw] for q in own)
            g._mark(name, -1.0)
            base = g._route(net, cost)
            alt = None if lands_here else _replan(g, net, cost, sq)
            g.plans[name] = paths
            g._mark(name, +1.0)
            d = None if alt is None else _plan_len(g, alt) - _plan_len(g, base)
            rows.append(dict(net=name, cls=_cls(net, sig_w), tracks=round(g._wt.get(name, 1.0), 1), squares=len(cross), lands_here=lands_here,
                             detour_mm=None if d is None else round(max(d, 0.0), 1), cross=cross))
        # the engineer's order: signals give way cheapest first, then power; pairs and
        # must-cross keep the strip
        give = sorted([q for q in rows if q["detour_mm"] is not None and q["cls"] != "pair"],
                      key=lambda q: ({"signal": 0, "power": 1}[q["cls"]], q["detour_mm"]))
        use = g.use.copy()
        moved, cost_mm = [], 0.0
        for q in give:
            if float(np.maximum(use - g.cap, 0.0)[:, sq].sum()) <= 0:
                break
            np.add.at(use.reshape(-1), np.array(q["cross"], np.int64), -g._wt.get(q["net"], 1.0))
            moved.append(q["net"])
            cost_mm += q["detour_mm"]
        left = float(np.maximum(use - g.cap, 0.0)[:, sq].sum())
        must = [q["net"] for q in rows if q["detour_mm"] is None]
        keep_pairs = [q["net"] for q in rows if q["cls"] == "pair" and q["detour_mm"] is not None]
        log("")
        log("STRIP %d at (%.1f, %.1f), %d mm2, beside %s, on %s: %d net(s) want through, %.1f track(s) too many"
            % (ci, x, y, int(sq.sum() * g.gc_mm ** 2), ", ".join(near), "/".join(layers) or "-", len(rows), ov))
        if must:
            log("  must cross (a land here, or no way round): " + ", ".join(sorted(must)))
        if keep_pairs:
            log("  pairs keep their channel: " + ", ".join(sorted(keep_pairs)))
        if moved:
            log("  go round, cheapest first: " + ", ".join("%s +%.0f" % (n, next(q["detour_mm"] for q in rows
                                                                              if q["net"] == n)) for n in moved)
                + "  (mm; %.0f mm in all)" % cost_mm)
        log("  " + ("then the strip fits" if left <= 0 else
                    "still %.1f too many after every net that can go round -- this needs ROOM (move a part, "
                    "or another layer), not a better route" % left))
        for q in rows:
            q.pop("cross")
        out.append(dict(strip=ci, x=round(x, 1), y=round(y, 1), area_mm2=int(sq.sum() * g.gc_mm ** 2), beside=near,
                        layers=layers, overflow=round(ov, 1), nets=sorted(rows, key=lambda q: (q["detour_mm"] is not None,
                                                                                               q["detour_mm"] or 0)),
                        must_cross=sorted(must), go_round=moved, go_round_mm=round(cost_mm, 1),
                        left_after=round(left, 1)))
    return dict(stem=stem, overflow=round(float(over.sum()), 1), squares_over=int(hot.sum()), strips=out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stem")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--json")
    a = ap.parse_args()
    res = report(a.stem, a.top)
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)
