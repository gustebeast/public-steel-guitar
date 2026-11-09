"""The global route: every net's corridor planned on a coarse grid before a track is drawn.

What an engineer does with the ratsnest before routing: sees which channels every net
needs, where the channels are too narrow for the nets that want them, and plans a corridor
per net so the drawing is methodical rather than a search. Two uses, one computation:

  * **placement score** -- `score()`: tracks wanted through each square against the tracks
    the square can carry, summed as overflow, with the parts beside the worst squares
    named. Seconds, not the minutes a detailed route takes, so placement can be searched
    against it (ROUTER.md M4).
  * **detailed-route corridors** -- `corridor(net)`: the coarse cells a net's plan crosses,
    widened a cell, which the detailed search keeps to first (negotiate._route_in), so a
    long net no longer explores the whole board when congestion pricing makes the
    straight-line heuristic weak.

Model, per G-cell (GC_MM square) and routing layer:
  capacity = tracks that can cross the square: the free fine rows (for an east-west track)
             or columns (north-south), whichever is more, over the track pitch. Free = a
             standard signal's centreline may stand there against the FIXED copper and the
             edge; the other nets' routed copper is what the usage counts.
  usage    = nets whose plan crosses the square on that layer, not counting the squares
             the net's own lands stand in (pin access is local work, priced by the
             detailed router -- counting it would read every fine-pitch IC as overflow).
Nets are planned with PathFinder on the coarse grid: squares over capacity get dearer
round by round until the plan fits or stops improving. Plane nets join their pours
locally and are left out; their stubs are short and the detailed router places them.
"""
from __future__ import annotations

import math
import time

import numpy as np

from . import search as S

GC_MM = 1.0                # G-cell size
VIA_GC = 1.0               # a via, in G-cell steps (the detailed via_cost of 15 fine cells is 0.75 mm)
ROUNDS = 30


class GlobalRouter:
    UTIL = 1.0                 # of a square's track count a real route can use (calibrated below)
    def __init__(self, router, gc_mm=GC_MM, log=print):
        self.r = router
        self.m = m = router.m
        self.log = log
        self.L, self.H, self.W = router.L, router.H, router.W
        self.b = b = max(2, int(round(gc_mm / m.pitch)))
        self.gc_mm = b * m.pitch
        self.gh = gh = -(-self.H // b)
        self.gw = gw = -(-self.W // b)
        L = self.L
        t0 = time.time()
        # fine cells where a standard signal's centreline clears the fixed copper and edge
        wref = router.wref
        free = m.d1 >= wref / 2.0 + m.clear + m.margin
        free &= (m.edge >= wref / 2.0 + m.edge_clear + m.margin)[None]
        pad = np.zeros((L, gh * b, gw * b), bool)
        pad[:, :self.H, :self.W] = free
        blk = pad.reshape(L, gh, b, gw, b)
        tp = (wref + m.clear) / m.pitch                  # track pitch, fine cells
        rows = blk.all(axis=4).sum(axis=2)               # rows free right across: E-W tracks
        cols = blk.all(axis=2).sum(axis=3)               # columns free right down: N-S tracks
        self.cap = np.maximum(rows, cols).astype(np.float32) / np.float32(tp) * np.float32(self.UTIL)
        self.inside = (np.pad(m.edge >= 0, ((0, gh * b - self.H), (0, gw * b - self.W)))
                       .reshape(gh, b, gw, b).any(axis=(1, 3)))
        # a via may drop in a square if some fine site there is via-legal for any net
        vok = np.all(m.d1 >= m.via_d / 2.0 + m.clear + m.margin, axis=0)
        vok &= m.edge >= m.via_d / 2.0 + m.edge_clear + m.margin
        vok &= ~m.via_ban
        vp = np.zeros((gh * b, gw * b), bool)
        vp[:self.H, :self.W] = vok
        self.via_ok = vp.reshape(gh, b, gw, b).any(axis=(1, 3))
        self.use = np.zeros((L, gh, gw), np.float32)
        self.hist = np.zeros((L, gh, gw), np.float32)
        self.plans = {}            # net name -> list of coarse flat-index paths
        self.terms = {}            # net name -> set of coarse flat indices its lands stand in
        self.t_setup = time.time() - t0

    # ------------------------------------------------------------------ helpers
    def _coarse(self, cells):
        """Fine flat indices (k*H*W + i*W + j) -> unique coarse flat indices (k*gh*gw + gi*gw + gj)."""
        H, W, b = self.H, self.W, self.b
        k = cells // (H * W)
        r = cells % (H * W)
        gi = (r // W) // b
        gj = (r % W) // b
        return np.unique((k * self.gh + gi) * self.gw + gj)

    def _nets(self):
        return [n for n in self.r.nets if not n.plane and len(n.pieces) >= 2]

    def _cost(self, pf):
        L, gh, gw = self.L, self.gh, self.gw
        over = np.maximum(self.use + 1.0 - self.cap, 0.0)
        c = (1.0 + self.hist) * (1.0 + pf * over) * self.r.layer_cost[:, None, None]
        c = np.where(self.inside[None], c, np.inf).astype(np.float32)
        return c

    COUNT_TERMS = False        # count a net's own land squares in its usage

    def _mark(self, name, sign):
        term = self.terms[name]
        for p in self.plans.get(name, ()):
            q = np.unique(p) if self.COUNT_TERMS else np.setdiff1d(np.unique(p), term)
            np.add.at(self.use.reshape(-1), q, sign)

    def _route(self, net, cost):
        """Plan one net: grow a tree from its biggest piece, joining each other piece to it
        by the cheapest coarse path (nearest piece first)."""
        L, gh, gw = self.L, self.gh, self.gw
        n = L * gh * gw
        pcs = [self._coarse(p) for p in net.pieces if p.size]
        if len(pcs) < 2:
            return []
        terms = set()
        for p in pcs:
            terms.update(p.tolist())
        self.terms[net.name] = np.array(sorted(terms), np.int64)
        cf = cost.reshape(-1).copy()
        cf[self.terms[net.name]] = np.minimum(cf[self.terms[net.name]], 1.0)  # own lands: always enterable
        vc = np.where(self.via_ok, 1.0, np.inf).astype(np.float32).reshape(-1)
        tree = np.zeros(n, np.bool_)
        order = sorted(range(len(pcs)), key=lambda q: -pcs[q].size)
        tree[pcs[order[0]]] = True
        left = order[1:]
        paths = []
        bufs = self.__dict__.setdefault("_bufs", S.Buffers())
        dir_cost = np.zeros((L, 2), np.float32)
        while left:
            # nearest remaining piece to the tree (centroid distance, coarse)
            tk = np.flatnonzero(tree) % (gh * gw)
            ti, tj = tk // gw, tk % gw
            best, bq = None, None
            for q in left:
                pk = pcs[q] % (gh * gw)
                d = np.min(np.abs(ti[:, None] - (pk // gw)[None]) + np.abs(tj[:, None] - (pk % gw)[None]))
                if best is None or d < best:
                    best, bq = d, q
            left.remove(bq)
            src = np.zeros(n, np.bool_)
            src[pcs[bq]] = True
            tgt = tree.copy()
            tgt[pcs[bq]] = False
            if not tgt.any():
                tree[pcs[bq]] = True
                continue
            tb = np.array([ti.min(), ti.max(), tj.min(), tj.max()], np.int64)
            g, par, st, base = bufs.take(n)
            path = S.astar_s(cf, vc, np.flatnonzero(src).astype(np.int64), tgt, L, gh, gw,
                             np.float32(VIA_GC), tb, dir_cost, np.float32(1.0), g, par, st, base)
            if path.size == 0:
                tree[pcs[bq]] = True          # unreachable at this scale: leave it to detail
                continue
            paths.append(path)
            tree[path] = True
            tree[pcs[bq]] = True
        return paths

    # ------------------------------------------------------------------ the loop
    def run(self, rounds=ROUNDS, pf0=0.5, pf_mul=1.5, hf=0.3):
        t0 = time.time()
        nets = self._nets()
        pf = pf0
        best, since = None, 0
        for it in range(1, rounds + 1):
            for net in nets:
                if net.name in self.plans:
                    self._mark(net.name, -1.0)
                cost = self._cost(pf)
                self.plans[net.name] = self._route(net, cost)
                self._mark(net.name, +1.0)
            over = np.maximum(self.use - self.cap, 0.0)
            tot = float(over.sum())
            self.hist += hf * (over > 0)
            if best is None or tot < best - 1e-6:
                best, since = tot, 0
            else:
                since += 1
            if tot <= 0 or since >= 6:
                break
            pf *= pf_mul
        self.rounds = it
        self.t_run = time.time() - t0
        return self

    # ------------------------------------------------------------------ outputs
    def score(self):
        """{overflow, squares_over, length_mm, vias, rounds, seconds}: lower overflow is a
        more routable placement; length and vias break ties."""
        over = np.maximum(self.use - self.cap, 0.0)
        L, gh, gw = self.L, self.gh, self.gw
        length = vias = 0
        for paths in self.plans.values():
            for p in paths:
                k = p // (gh * gw)
                vias += int(np.count_nonzero(k[1:] != k[:-1]))
                length += int(p.size) - int(np.count_nonzero(k[1:] != k[:-1]))
        return dict(overflow=round(float(over.sum()), 2),
                    squares_over=int(np.count_nonzero(over.sum(axis=0) > 0)),
                    length_mm=round(length * self.gc_mm, 1), vias=vias, rounds=self.rounds,
                    seconds=round(self.t_setup + self.t_run, 2))

    def hotspots(self, top=8, cell_mm=2.0):
        """[(overflow, x, y, layers, [nearest refs])]: where the plan wants more tracks than fit."""
        from .congestion import _refs
        over = np.maximum(self.use - self.cap, 0.0)
        a = max(1, int(round(cell_mm / self.gc_mm)))
        L, gh, gw = self.L, self.gh, self.gw
        hh, ww = gh // a, gw // a
        blk = over[:, :hh * a, :ww * a].reshape(L, hh, a, ww, a).sum(axis=(2, 4))
        tot = blk.sum(axis=0)
        refs = _refs(self.m.txt)
        out, taken = [], []
        for o in np.argsort(tot.ravel())[::-1]:
            if tot.flat[o] <= 0 or len(out) >= top:
                break
            bi, bj = divmod(int(o), ww)
            if any(abs(bi - p) <= 1 and abs(bj - q) <= 1 for p, q in taken):
                continue
            taken.append((bi, bj))
            x = self.m.x0 + (bj + 0.5) * a * self.gc_mm
            y = self.m.y0 + (bi + 0.5) * a * self.gc_mm
            layers = [self.m.route_layers[k] for k in range(L) if blk[k, bi, bj] > 0.25 * tot[bi, bj]]
            near = sorted(refs, key=lambda r: math.hypot(r[1] - x, r[2] - y))[:3]
            out.append((float(tot[bi, bj]), x, y, layers, [r[0] for r in near]))
        return out

    def report(self, log=None):
        log = log or self.log
        s = self.score()
        log("globalroute: %d net(s) planned on a %.1f mm grid in %.1f s (%d rounds): overflow %.1f "
            "track(s) over %d square(s), %.0f mm, %d via(s)"
            % (len(self.plans), self.gc_mm, s["seconds"], s["rounds"], s["overflow"],
               s["squares_over"], s["length_mm"], s["vias"]))
        for o, x, y, layers, near in self.hotspots():
            log("    %5.1f  over at (%.1f, %.1f) on %s, beside %s"
                % (o, x, y, "/".join(layers) or "-", ", ".join(near)))

    def corridor(self, name, widen=1):
        """bool[gh, gw]: the squares a net's plan crosses (any layer), widened `widen` squares."""
        mask = np.zeros((self.gh, self.gw), bool)
        for p in self.plans.get(name, ()):
            r = p % (self.gh * self.gw)
            mask[r // self.gw, r % self.gw] = True
        if widen and mask.any():
            from scipy.ndimage import binary_dilation
            mask = binary_dilation(mask, iterations=widen)
        return mask
