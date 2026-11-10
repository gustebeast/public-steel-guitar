"""Coupled diff-pair routing (ROUTER.md milestone 3).

⚠ A PAIR IS ONE TRACE TWICE, NOT TWO TRACES (optical USB_HS / HUB_PHY, 2026-11-10). The
pair finish laid each rail on its own -- the second drawn to a band beside the first --
and both came out to verify's rules (layer set, vias, skew) while running apart for
much of their length: on the unmoved board USB_DP ran 13.6 mm on In2.Cu while USB_DM
stayed on F.Cu, and HUB_PHY's rails parted for 7 mm round Q1/Q2. Differential impedance
is the geometry of the two conductors together; apart, each is a single-ended line.

An engineer routes the pair as one: the two rails' centreline first, as a track as wide
as the pair (w + spacing), then each rail at half the spacing either side of it. Here
the centreline is a temporary net of that width searched like any other (so every cost
the board carries -- congestion, history, regions, escapes, voids -- shapes it), from
between the pair's lands at one end of each hop to between them at the other. Each rail
is then laid in a lane round its offset of that line, priced cheapest ON the offset,
with free fan-out room round its own lands and round each place the centreline changes
layer (where the two rails take their vias side by side). The second rail keeps the
first as a wall (PAIR_WALL), so they cannot cross inside a lane.
"""
import copy
import itertools
import math

import numpy as np
from scipy.ndimage import distance_transform_edt, label
from scipy.ndimage import maximum as ndmax
from scipy.ndimage import sum as ndsum


class CoupledMixin:
    COUPLE = True              # the pair finish lays declared diff pairs coupled
    COUPLE_MIN_MM = 2.0        # a pair to the rules but this far apart is re-laid coupled
    COUPLE_GAIN_MM = 1.0       # ...and the coupled lay is kept only this much closer
    COUPLE_END_MM = 1.2        # within this of its own lands a rail fans out: not judged
    LANE_TOL = 0.15            # a rail's lane: its offset of the centreline, +- this
    LANE_FAN = 0.8             # free room round each land beyond the centreline's start
    LANE_VIA = 0.9             # free room round each centreline layer change
    BAND_COST = 0.5            # price of a cell on the exact offset
    COUPLE_ENDS = 3            # pin-pair choices a coupled lay tries, best first
    EXIT_SIDE = True                 # a land with no outward line is sided by where each rail leaves it
    MID_SLACKS = (0.1, 0.05, 0.0)   # mm each side of the centreline's pair width, tried in turn
    VIA_OFF = 0.42             # a rail's via at a layer change: this far off the line, its side

    # ----------------------------------------------------------------- measures
    def _pair_spec(self, a):
        for spec in self.m.notes.get("diff_pairs", ()) or ():
            if a.name in spec.get("nets", ()):
                return spec
        return None

    def _pair_sp(self, a):
        """Centre-to-centre spacing of a declared pair: width + gap, never inside the
        pair wall."""
        spec = self._pair_spec(a) or {}
        b = a.mate
        m = self.m
        gap = float(spec.get("gap", m.clear))
        wall = (a.width + b.width) / 2.0 + m.clear + m.margin
        return max((a.width + b.width) / 2.0 + gap, wall + m.pitch)

    def _box(self, cell_lists, pad_mm):
        H, W = self.H, self.W
        allc = np.concatenate([c for c in cell_lists if c.size])
        r = allc % (H * W)
        ii, jj = r // W, r % W
        pad = int(math.ceil(pad_mm / self.m.pitch))
        return (max(0, int(ii.min()) - pad), min(H, int(ii.max()) + pad + 1),
                max(0, int(jj.min()) - pad), min(W, int(jj.max()) + pad + 1))

    def _grid(self, cells, box):
        L, H, W = self.L, self.H, self.W
        i0, i1, j0, j1 = box
        g = np.zeros((L, i1 - i0, j1 - j0), bool)
        for p in cells:
            if not p.size:
                continue
            k = p // (H * W)
            r = p % (H * W)
            ii, jj = r // W - i0, r % W - j0
            ok = (ii >= 0) & (ii < i1 - i0) & (jj >= 0) & (jj < j1 - j0)
            g[k[ok], ii[ok], jj[ok]] = True
        return g

    def _uncoupled(self, a):
        """mm of a pair's rails NOT beside each other -- same layer, centre spacing within
        [sp - 0.1, sp + 0.15] -- leaving out each rail's fan-out (COUPLE_END_MM of its own
        lands) and the merge circle."""
        b = a.mate
        m = self.m
        L, H, W = self.L, self.H, self.W
        sp = self._pair_sp(a)
        paths = [p for x in (a, b) for p in x.paths if p.size]
        if not paths:
            return 0.0
        box = self._box(paths + [p for x in (a, b) for p in x.pieces], self.COUPLE_END_MM + 1.0)
        i0, i1, j0, j1 = box
        tot = 0.0
        for x, y in ((a, b), (b, a)):
            mate = self._grid(y.paths, box)
            own = self._grid(x.pieces, box).any(axis=0)
            dend = (distance_transform_edt(~own) * m.pitch if own.any()
                    else np.full(own.shape, 1e9))
            dm = [distance_transform_edt(~mate[k]) * m.pitch if mate[k].any() else None
                  for k in range(L)]
            for p in x.paths:
                if p.size < 2:
                    continue
                k = p // (H * W)
                r = p % (H * W)
                pi, pj = r // W - i0, r % W - j0
                X, Y = m.cx[r % W], m.cy[r // W]
                st = np.hypot(np.diff(X), np.diff(Y))
                judge = (k[1:] == k[:-1]) & (dend[pi[:-1], pj[:-1]] >= self.COUPLE_END_MM)
                if x.merge is not None:
                    judge &= np.hypot(X[:-1] - x.merge[0], Y[:-1] - x.merge[1]) >= x.merge[2]
                d = np.full(p.size - 1, 1e9)
                for kk in range(L):
                    if dm[kk] is not None:
                        sel = k[:-1] == kk
                        d[sel] = dm[kk][pi[:-1][sel], pj[:-1][sel]]
                ok = (d >= sp - 0.1) & (d <= sp + 0.15)
                tot += float(st[judge & ~ok].sum())
        return tot

    # ----------------------------------------------------------------- the centreline
    def _pair_ends(self, x):
        if x.legs:
            return [(lg[0], lg[1]) for lg in x.legs]
        if len(x.pieces) == 2:
            return [(x.pieces[0], x.pieces[1])]
        return None

    def _xy(self, cells):
        r = cells % (self.H * self.W)
        return float(self.m.cx[r % self.W].mean()), float(self.m.cy[r // self.W].mean())

    def _outward(self, ca, cb, a, b):
        """Unit vector straight out of the part from a pin pair -- each pad's long axis,
        pointed away from its footprint's centre, summed -- or None when the pads are on
        different parts, round, or point opposite ways (a clamp's two rows)."""
        us, fps = [], set()
        H, W = self.H, self.W
        for cells, x in ((ca, a), (cb, b)):
            cx, cy = self._xy(cells)
            pads = [p for p in self.m.pads if p["net"] == x.name]
            if not pads:
                return None
            # ⚠ A LAND OF SEVERAL PADS HAS NO ONE WAY OUT (optical U10, 2026-11-10): the
            # flow-through clamp offers D+ on pins 1 and 6, either side of the body, and the
            # first in the list made a twist out of a pair that reaches the clamp untwisted
            # from its other side. Which pad is the rail's to choose; the line says nothing.
            rc = set((cells % (H * W)).tolist())
            inside = [p for p in pads if (lambda ij: ij[0] * W + ij[1])(self.m.ij(p["gx"], p["gy"])) in rc]
            if len(inside) > 1:
                return None
            p = min(pads, key=lambda q: math.hypot(q["gx"] - cx, q["gy"] - cy))
            fps.add(p.get("fp"))
            ax, ay = p["x2"] - p["x1"], p["y2"] - p["y1"]
            ox, oy = p["gx"] - p.get("fpx", p["gx"]), p["gy"] - p.get("fpy", p["gy"])
            n = math.hypot(ax, ay)
            if n < 1e-6:
                ax, ay, n = ox, oy, math.hypot(ox, oy)
                if n < 0.4:
                    return None
            elif ax * ox + ay * oy < 0:
                ax, ay = -ax, -ay
            us.append((ax / n, ay / n))
        if len(fps) != 1:
            return None
        ux, uy = us[0][0] + us[1][0], us[0][1] + us[1][1]
        n = math.hypot(ux, uy)
        return None if n < 1.0 else (ux / n, uy / n)

    def _mid_end(self, ca, cb, wf, a, b):
        """Cells between two lands (one per rail) where a track wf wide is legal: the
        nearest ring round their midpoint that has any. (cells, radius mm) or None."""
        m = self.m
        L, H, W = self.L, self.H, self.W
        (xa, ya), (xb, yb) = self._xy(ca), self._xy(cb)
        mx, my = (xa + xb) / 2.0, (ya + yb) / 2.0
        lays = sorted(set((ca // (H * W)).tolist()) | set((cb // (H * W)).tolist()))
        ci, cj = m.ij(mx, my)
        R = int(math.ceil(2.0 / m.pitch))
        i0, i1, j0, j1 = max(0, ci - R), min(H, ci + R + 1), max(0, cj - R), min(W, cj + R + 1)
        X, Y = np.meshgrid(m.cx[j0:j1], m.cy[i0:i1])
        dist = np.hypot(X - mx, Y - my)
        sl = (slice(None), slice(i0, i1), slice(j0, j1))
        n1 = m.n1[sl]
        fd = np.where((n1 == a.id) | (n1 == b.id), m.d2[sl], m.d1[sl])
        ok = fd >= wf / 2.0 + m.clear + m.margin
        ok &= (m.edge[i0:i1, j0:j1] >= wf / 2.0 + m.edge_clear + m.margin)[None]
        occ = self.occ_t.reshape(L, H, W)[sl] == 0
        # ⚠ STRAIGHT OUT OF THE PACKAGE (optical HUB_PHY at U7, 2026-11-10): the nearest
        # legal ring round the lands' midpoint put the centreline's start beside the MATE's
        # pad, and the near rail had to cross the mate's way to reach its side. An engineer
        # leaves a pin pair straight out, away from the part, and joins them there: the
        # start is the first legal spot on that outward line. Lands with no outward line
        # (the clamp's rows either side of its middle) keep the ring.
        u = self._outward(ca, cb, a, b)
        if u is not None:
            for t in np.arange(0.0, 2.0, m.pitch):
                ex, ey = mx + u[0] * t, my + u[1] * t
                near = np.hypot(X - ex, Y - ey) <= 1.5 * m.pitch
                sel = np.zeros_like(ok)
                for k in lays:
                    sel[k] = ok[k] & near
                if sel.any():
                    kk, ii, jj = np.nonzero(sel)
                    return (kk * H + ii + i0) * W + jj + j0, float(t) + 0.1
        for rad in (0.3, 0.6, 1.0, 1.5, 2.0):
            for need_free in (True, False):
                sel = np.zeros_like(ok)
                for k in lays:
                    sel[k] = ok[k] & (dist <= rad) & (occ[k] if need_free else True)
                if sel.any():
                    kk, ii, jj = np.nonzero(sel)
                    return (kk * H + ii + i0) * W + jj + j0, rad
        return None

    def _midline(self, a, b, pf, choice=0):
        """The pair's centreline, hop by hop: [(paths, (a from, b from), (a to, b to),
        radius from, radius to)] with full-board paths, or None if a hop finds no room
        for the pair."""
        H, W = self.H, self.W
        ea, eb = self._pair_ends(a), self._pair_ends(b)
        if not ea or not eb or len(ea) != len(eb):
            return None
        sp = self._pair_sp(a)
        wf = sp + (a.width + b.width) / 2.0
        combos = self._choose_ends(a, b, ea, eb)
        if choice >= len(combos):
            self._ends_left = False
            return None
        self._ends_left = choice + 1 < len(combos)
        ends = combos[choice]
        hops = []
        for (sa, sb), (ta, tb) in ends:
            s_ = self._mid_end(sa, sb, wf, a, b)
            t_ = self._mid_end(ta, tb, wf, a, b)
            if s_ is None or t_ is None:
                return None
            f = copy.copy(a)
            f.name = a.name + "~pair"
            f.width = wf
            f.ids = (a.id, b.id)
            f.via_erode = (self.m.via_d + self.m.clear) / 2.0 + self.m.margin + 0.05
            f.pieces = [s_[0], t_[0]]
            f.paths, f.necks, f.legs, f.fixed = [], [], [], []
            f.mate = f.partner = f.merge = None
            f.plane = f.same_layer = False
            f.keep_paths = f.main_xy = None
            f.stuck = 10 ** 6             # no global-plan corridor: it has no plan
            f.relaxed = True              # home layers preferred (OFFRUN_COST), not forced
            f.force_layers = None
            f.via_mult = a.via_mult
            allc = np.concatenate(f.pieces)
            r = allc % (H * W)
            f.bbox = (int((r // W).min()), int((r // W).max()), int((r % W).min()), int((r % W).max()))
            # ⚠ A CENTRELINE WITH NO SLACK SEATS NO SECOND RAIL (optical USB_HS, C102
            # +0.27/+0.18, 2026-11-10): between C102's via and two GND stitching vias the
            # line took the gap at exactly the pair's width; on the grid the first rail
            # fitted and the second, walled by its mate, had no legal cell left. The line is
            # sought with slack each side first, at the bare width only if that fails; each
            # slack in MID_SLACKS is its own attempt (_finish_pairs), widest first -- 0.1 mm
            # laid c02's USB with its vias too close, 0.05 laid it to the rules.
            got = None
            slack = getattr(self, "_mid_slack", None)
            slack = self.MID_SLACKS[0] if slack is None else slack
            for wx in ((wf + 2 * slack, wf) if slack > 0 else (wf,)):
                f.width = wx
                saved = (self._necks if hasattr(self, "_necks") else None, getattr(self, "_neck_win", None))
                try:
                    got = self._route_net(f, pf)
                finally:
                    self._necks, self._neck_win = saved
                if got:
                    break
            if not got:
                return None
            # A* hands a path back from its target: each runs start -> end here, so the
            # centreline's direction is the pair's travel
            st = set(s_[0].tolist())
            hp = [p if p[0] in st or p[-1] not in st and self._dcell(p[0], s_[0]) <= self._dcell(p[-1], s_[0])
                  else p[::-1].copy() for p in got if p.size]
            hops.append((hp, (sa, sb), (ta, tb), s_[1], t_[1]))
        return hops

    def _pin_pairs(self, ca, cb, a, b):
        """The pin pairs a pair may use at one part: [(a cells, b cells)]. Lands of one pad
        each are one pair; a part offering a rail several pads (a flow-through clamp) gives
        each a-pad with the b-pad of the same footprint facing the same way, nearest it."""
        H, W = self.H, self.W
        m = self.m

        def pads_in(cells, x):
            rc = set((cells % (H * W)).tolist())
            return [p for p in m.pads if p["net"] == x.name and
                    (lambda ij: ij[0] * W + ij[1])(m.ij(p["gx"], p["gy"])) in rc]

        def cells_of(cells, p):
            r = cells % (H * W)
            X, Y = m.cx[r % W], m.cy[r // W]
            vx, vy = p["x2"] - p["x1"], p["y2"] - p["y1"]
            vv = vx * vx + vy * vy
            t = np.clip(((X - p["x1"]) * vx + (Y - p["y1"]) * vy) / vv, 0, 1) if vv > 0 else 0.0
            d = np.hypot(X - p["x1"] - t * vx, Y - p["y1"] - t * vy)
            return cells[d <= p["r"] + 1.5 * m.pitch]

        def out(p):
            ax, ay = p["x2"] - p["x1"], p["y2"] - p["y1"]
            ox, oy = p["gx"] - p.get("fpx", p["gx"]), p["gy"] - p.get("fpy", p["gy"])
            n = math.hypot(ax, ay)
            if n < 1e-6:
                ax, ay, n = ox, oy, math.hypot(ox, oy) or 1.0
            elif ax * ox + ay * oy < 0:
                ax, ay = -ax, -ay
            return ax / n, ay / n

        pa, pb = pads_in(ca, a), pads_in(cb, b)
        if len(pa) <= 1 and len(pb) <= 1:
            return [(ca, cb)]
        got = []
        for p in pa:
            ua = out(p)
            same = [q for q in pb if q.get("fp") == p.get("fp") and
                    ua[0] * out(q)[0] + ua[1] * out(q)[1] > 0.7]
            if same:
                q = min(same, key=lambda q: math.hypot(q["gx"] - p["gx"], q["gy"] - p["gy"]))
                if math.hypot(q["gx"] - p["gx"], q["gy"] - p["gy"]) < 3.0:
                    ca_, cb_ = cells_of(ca, p), cells_of(cb, q)
                    if ca_.size and cb_.size:
                        got.append((ca_, cb_))
        return got or [(ca, cb)]

    def _choose_ends(self, a, b, ea, eb):
        """Each hop's (from, to) pin pairs, chosen where a part offers several: fewest
        hops whose two ends put the rails on opposite sides (a twist), then shortest.

        ⚠ A CLAMP'S PINS HAVE SIDES TOO (optical U10, 2026-11-10): DP is the top row of
        both pin pairs, west (1/3) and east (6/4). Judged as one land the clamp said
        nothing, and with J1 on A7/B6 the twist it put in the hop to J1 went unseen. The
        pair may use either pin pair arriving and either leaving -- through the clamp, or
        in and back out as a stub -- and the choice is the one that needs no swap."""
        opts = []
        for (sa, ta), (sb, tb) in zip(ea, eb):
            opts.append((self._pin_pairs(sa, sb, a, b), self._pin_pairs(ta, tb, a, b)))
        # ⚠ IN AND STRAIGHT BACK OUT IS NO WAY THROUGH (optical U10, 2026-11-10): with
        # no twist to pay, the pair came in to the clamp's west pins and was to leave by
        # them again -- but a hop keeps clear of its own net's other copper, so the second
        # hop had nowhere to run. Reusing a pin pair costs more than a twist (which a
        # layer change takes for free).
        ranked = []
        for combo in itertools.product(*[itertools.product(o[0], o[1]) for o in opts]):
            tw, ln = 0.0, 0.0
            for (s_, t_) in combo:
                s1 = self._end_side(s_[0], s_[1], a, b, 1.0) or 0
                s2 = self._end_side(t_[0], t_[1], a, b, -1.0) or 0
                tw += float(bool(s1 and s2 and s1 != s2))
                (x1, y1), (x2, y2) = self._xy(np.concatenate(s_)), self._xy(np.concatenate(t_))
                ln += math.hypot(x2 - x1, y2 - y1)
            for (_, t_), (s_, _) in zip(combo, combo[1:]):
                if np.intersect1d(t_[0], s_[0]).size:
                    tw += 1.5
            ranked.append(((tw, ln), list(combo)))
        ranked.sort(key=lambda r_: r_[0])
        return [c for _, c in ranked]

    def _dcell(self, c, cells):
        """Grid distance from one cell to the nearest of a set (cells, any layer)."""
        H, W = self.H, self.W
        r, rr = int(c) % (H * W), cells % (H * W)
        return float(np.min(np.hypot(rr // W - r // W, rr % W - r % W)))

    # ----------------------------------------------------------------- the lanes
    def _end_side(self, ca, cb, a, b, sense):
        """Side of rail a at a pin pair, against the pair's travel there (sense * the
        outward line): +1 / -1, or None with no outward line."""
        u = self._outward(ca, cb, a, b)
        if u is None:
            return None
        tx, ty = u[0] * sense, u[1] * sense
        (xa, ya), (xb, yb) = self._xy(ca), self._xy(cb)
        dx, dy = (xa - xb) / 2.0, (ya - yb) / 2.0
        cr = ty * dx - tx * dy
        return None if abs(cr) < 1e-6 else (1 if cr > 0 else -1)

    def _multi(self, cells, x):
        """True when a land holds more than one pad of its net (a USB-C's merged rows)."""
        H, W = self.H, self.W
        rc = set((cells % (H * W)).tolist())
        n = 0
        for p in self.m.pads:
            if p["net"] == x.name:
                i, j = self.m.ij(p["gx"], p["gy"])
                n += (i * W + j) in rc
        return n > 1

    def _exit(self, mine, theirs, x, y, end):
        """Where rail x's land is first reached from a line end, going round the mate's
        land (never within a track's clearance of it): (x mm, y mm), or None."""
        m = self.m
        H, W = self.H, self.W
        ei, ej = divmod(int(end % (H * W)), W)
        R = int(math.ceil(3.0 / m.pitch))
        i0, i1, j0, j1 = max(0, ei - R), min(H, ei + R + 1), max(0, ej - R), min(W, ej + R + 1)
        h, w = i1 - i0, j1 - j0
        own = np.zeros((h, w), bool)
        mate = np.zeros((h, w), bool)
        for cells, g in ((mine, own), (theirs, mate)):
            r = cells % (H * W)
            ii, jj = r // W - i0, r % W - j0
            ok = (ii >= 0) & (ii < h) & (jj >= 0) & (jj < w)
            g[ii[ok], jj[ok]] = True
        if not own.any():
            return None
        gap = (x.width + y.width) / 2.0 + m.clear
        wall = (distance_transform_edt(~mate) * m.pitch < gap) if mate.any() else np.zeros_like(mate)
        wall &= ~own
        si, sj = ei - i0, ej - j0
        seen = np.zeros((h, w), bool)
        seen[si, sj] = True
        front = [(si, sj)]
        while front:
            nxt = []
            for ci, cj in front:
                if own[ci, cj]:
                    return float(m.cx[cj + j0]), float(m.cy[ci + i0])
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        ni, nj = ci + di, cj + dj
                        if 0 <= ni < h and 0 <= nj < w and not seen[ni, nj] and not wall[ni, nj]:
                            seen[ni, nj] = True
                            nxt.append((ni, nj))
            front = nxt
        return None

    def _exit_side(self, ca, cb, a, b, p, at):
        """Side of rail a at a line end, from where each rail's land is first reached going
        round its mate's (p: the run at that end, at: 0 start, -1 end), against the line's
        travel there. +1 / -1, or None when the exits are not beside the line."""
        n = p.size
        if n < 3:
            return None
        k = min(8, n - 1)
        e0, e1 = (p[0], p[k]) if at == 0 else (p[n - 1 - k], p[n - 1])
        end = p[0] if at == 0 else p[n - 1]
        (x0, y0), (x1, y1) = self._xy(np.array([e0])), self._xy(np.array([e1]))
        tx, ty = x1 - x0, y1 - y0
        tn = math.hypot(tx, ty)
        if tn == 0:
            return None
        tx, ty = tx / tn, ty / tn
        # the mate's whole land walls the way, its fixed merge copper included; a rail
        # exits only onto the cells its hop may land on
        def whole(cells, x):
            pc = [q for q in x.pieces if np.isin(q, cells).any()]
            return np.concatenate([cells] + pc) if pc else cells
        xa = self._exit(ca, whole(cb, b), a, b, end)
        xb = self._exit(cb, whole(ca, a), b, a, end)
        if xa is None or xb is None:
            return None
        dx, dy = (xa[0] - xb[0]) / 2.0, (xa[1] - xb[1]) / 2.0
        cr = ty * dx - tx * dy
        dn = math.hypot(dx, dy)
        if dn == 0 or abs(cr) / dn < 0.3:
            return None
        return 1 if cr > 0 else -1

    def _side(self, cells, hp, tang, box):
        """Which side of a hop's centreline a land lies: +1 / -1, or 0 when it lies
        ahead of or behind the line's end rather than beside it."""
        H, W = self.H, self.W
        i0, _, j0, _ = box
        r = cells % (H * W)
        ci, cj = (r // W).mean() - i0, (r % W).mean() - j0
        allc = np.concatenate(hp)
        rr = allc % (H * W)
        ii, jj, kk = rr // W - i0, rr % W - j0, allc // (H * W)
        q = int(np.argmin((ii - ci) ** 2 + (jj - cj) ** 2))
        ti, tj = float(tang[0][kk[q], ii[q], jj[q]]), float(tang[1][kk[q], ii[q], jj[q]])
        di, dj = ci - ii[q], cj - jj[q]
        n = math.hypot(ti, tj) * math.hypot(di, dj)
        if n == 0:
            return 0
        sn = (ti * dj - tj * di) / n
        return 0 if abs(sn) < 0.3 else (1 if sn > 0 else -1)

    def _stem(self, ca, cb, end):
        """Grid cells from the midpoint of two lands straight to a centreline end cell,
        on that cell's layer (full-board indices, midpoint first)."""
        H, W = self.H, self.W
        (xa, ya), (xb, yb) = self._xy(ca), self._xy(cb)
        mi, mj = self.m.ij((xa + xb) / 2.0, (ya + yb) / 2.0)
        k, r = int(end // (H * W)), int(end % (H * W))
        ei, ej = r // W, r % W
        n = max(abs(ei - mi), abs(ej - mj)) + 1
        ii = np.rint(np.linspace(mi, ei, n)).astype(np.int64)
        jj = np.rint(np.linspace(mj, ej, n)).astype(np.int64)
        return (k * H + ii) * W + jj

    def _run_sides(self, runs, obs):
        """Side of rail a on each run of the centreline, hop by hop. obs: [(run, side,
        hop)] from the pin pairs at each hop's ends. Between hops (at a part both touch)
        the side may change: the pair can turn round there.

        ⚠ A TWIST GOES WHERE THE PAIR CHANGES LAYER (optical USB_HS, unmoved, 2026-11-10):
        DP leaves U31 on the pair's left and must reach J1's A6 on its right -- the pair
        has to cross itself somewhere, and the old router did it with a 13 mm dive. Where
        the centreline changes layer anyway the swap is free: one rail goes down, the other
        crosses over it on the layer above, then follows it down. The swap is put at the
        hop's first layer change; with none, the hop is left unsided."""
        side = [0] * len(runs)
        for hop in sorted({r_[1] for r_ in runs}):
            idx = [j for j, r_ in enumerate(runs) if r_[1] == hop]
            ob = [(r_, s_) for r_, s_, h_ in obs if h_ == hop]
            if not ob:
                continue
            s1, s2 = ob[0][1], ob[-1][1]
            if s1 == s2:
                for j in idx:
                    side[j] = s1
                continue
            cut = next((j for j in idx[1:] if runs[j][0] == runs[j - 1][0]
                        and runs[j][4] != runs[j - 1][4]), None)
            if cut is None:
                continue
            for j in idx:
                side[j] = s1 if j < cut else s2
        return side

    def _set_lanes(self, a, b, hops):
        """Each rail's lane round its offset of the centreline (self._lanes)."""
        m = self.m
        L, H, W = self.L, self.H, self.W
        sp = self._pair_sp(a)
        paths = [p for hop in hops for p in hop[0]]
        fan = max(max(hop[3], hop[4]) for hop in hops) + self.LANE_FAN
        box = self._box(paths + [p for x in (a, b) for p in x.pieces], max(fan, self.LANE_VIA) + 0.5)
        i0, i1, j0, j1 = box
        h, w = i1 - i0, j1 - j0
        lane = {a.name: np.zeros((L, h, w), bool), b.name: np.zeros((L, h, w), bool)}
        vlane = {a.name: np.zeros((h, w), bool), b.name: np.zeros((h, w), bool)}
        band = np.zeros((L, h, w), bool)
        yy, xx = np.mgrid[0:h, 0:w]
        # ⚠ TWO STRIPS, NOT ONE BAND (optical, 2026-11-10): with the centreline itself in
        # the lane, the first rail ran down the middle and walled the second out. The core
        # (nearer the centreline than half the pair wall) is no rail's, and each rail keeps
        # to ITS side -- the side its land is on -- so the first cannot take the second's.
        core = ((a.width + b.width) / 2.0 + m.clear + m.margin) / 2.0

        def disk(ci, cj, rad):
            return (yy - ci) ** 2 + (xx - cj) ** 2 <= (rad / m.pitch) ** 2

        # ⚠ THE LINE RUNS BACK TO BETWEEN THE PINS (optical HUB_PHY at U7, 2026-11-10):
        # the centreline starts where a pair-wide track first fits, and when it turned at
        # once the near rail's strip began under the mate's pad; split by distance to the
        # pads, its fan never met its strip. A straight stem from between each pin pair to
        # the line's end makes "which side" one question, asked of one line, from the pins
        # all the way along.
        exts, runs, obs, lines = [], [], [], []
        for hi, (hp, (sa, sb), (ta, tb), _, _) in enumerate(hops):
            ls = self._outward(sa, sb, a, b) is not None
            lt = self._outward(ta, tb, a, b) is not None
            ext = [p.copy() for p in hp]
            if ls:
                ext[0] = np.concatenate([self._stem(sa, sb, ext[0][0])[:-1], ext[0]])
            if lt:
                ext[-1] = np.concatenate([ext[-1], self._stem(ta, tb, ext[-1][-1])[::-1][1:]])
            exts.append(ext)
            first = len(runs)
            for pi, p in enumerate(ext):
                k = p // (H * W)
                cut = np.nonzero(k[1:] != k[:-1])[0]
                bounds = [0] + (cut + 1).tolist() + [p.size]
                for s0, s1_ in zip(bounds, bounds[1:]):
                    runs.append((hi * 1000 + pi, hi, s0, s1_, int(k[s0])))
            # each end's side against the way the pair travels there -- straight out of
            # the part at the start, straight in at the end. ⚠ A PART WITH NO OUTWARD LINE
            # SAYS NOTHING (optical U10, 2026-11-10): the clamp's DP is its top row and DM
            # its bottom row, either side of the line's end; judged against the line it read
            # as a twist. Its side is its neighbours'.
            s1 = self._end_side(sa, sb, a, b, 1.0)
            s2 = self._end_side(ta, tb, a, b, -1.0)
            # ⚠ A MERGED LAND IS SIDED BY WHERE EACH RAIL CAN LEAVE IT (output_panel PI at
            # J2, 2026-11-10). A USB-C at 90 / 270 deg carries D+ / D- on both rows, joined
            # by fixed merge loops. By its A6 / A7 pads DP sat above DM -- but DM's loop
            # boxes A6 in, and DP can only leave from B6, below DM. Read by the pads, the
            # two ends disagreed with no layer change between, and the run went unsided.
            # On a land of several pads (or none with an outward line) each rail's exit is
            # where its land is first reached from the line's end going round its mate's.
            if self.EXIT_SIDE and (s1 is None or self._multi(sa, a) or self._multi(sb, b)):
                s1 = self._exit_side(sa, sb, a, b, hp[0], 0) or s1
                ls = ls or bool(s1)
            if self.EXIT_SIDE and (s2 is None or self._multi(ta, a) or self._multi(tb, b)):
                s2 = self._exit_side(ta, tb, a, b, hp[-1], -1) or s2
                lt = lt or bool(s2)
            s1, s2 = s1 or 0, s2 or 0
            if s1:
                obs.append((first, s1, hi))
            if s2:
                obs.append((len(runs) - 1, s2, hi))
            lines.append((first, len(runs) - 1, ls, lt))
        rside = self._run_sides(runs, obs)
        self._lane_sides = rside
        sk_all = []
        for hi, (hp, (sa, sb), (ta, tb), _, _) in enumerate(hops):
            ext = exts[hi]
            mk = self._grid(ext, box)
            tang = (np.zeros((L, h, w), np.float32), np.zeros((L, h, w), np.float32))
            endm = np.zeros((L, h, w), bool)
            rid = np.full((L, h, w), -1, np.int64)
            for pi, p in enumerate(ext):
                k = p // (H * W)
                rr = p % (H * W)
                ii, jj = rr // W - i0, rr % W - j0
                ok = (ii >= 0) & (ii < h) & (jj >= 0) & (jj < w)
                n = p.size
                lo = np.clip(np.arange(n) - 6, 0, n - 1)
                hi_ = np.clip(np.arange(n) + 6, 0, n - 1)
                tang[0][k[ok], ii[ok], jj[ok]] = (ii[hi_] - ii[lo])[ok]
                tang[1][k[ok], ii[ok], jj[ok]] = (jj[hi_] - jj[lo])[ok]
                for ri, run in enumerate(runs):
                    if run[0] == hi * 1000 + pi:
                        sel = np.zeros(n, bool)
                        sel[run[2]:run[3]] = True
                        sel &= ok
                        rid[k[sel], ii[sel], jj[sel]] = ri
                        for e in (run[2], run[3] - 1):     # round a run's ends the strips meet
                            if ok[e]:
                                endm[k[e], ii[e], jj[e]] = True
            sk = {}
            for k in range(L):
                if not mk[k].any():
                    continue
                d, (ni, nj) = distance_transform_edt(~mk[k], return_indices=True)
                d = d * m.pitch
                strip = (d >= core) & (d <= sp / 2.0 + self.LANE_TOL)
                band[k] |= np.abs(d - sp / 2.0) <= 0.75 * m.pitch
                cr = tang[0][k][ni, nj] * (xx - nj) - tang[1][k][ni, nj] * (yy - ni)
                near_run = rid[k][ni, nj]
                sk[k] = (np.sign(cr), d >= core, near_run, d)
                # ⚠ A SIDE IS A REGION, NOT A CELL'S SIGN (optical USB, 2026-11-10): at a
                # turn the nearest centreline cell's direction flips on the inside, and the
                # strip broke there. Cut the strips apart at each run's ends, then each
                # connected strip takes the side most of its cells are on.
                strip &= ~endm[k][ni, nj]
                lab, nl = label(strip, structure=np.ones((3, 3), bool))
                if not nl:
                    continue
                idx = np.arange(1, nl + 1)
                vote = np.asarray(ndsum(np.sign(cr), lab, index=idx))
                runof = np.asarray(ndmax(np.where(strip, near_run, -1), lab, index=idx)).astype(int)
                for c in range(nl):
                    s_ = rside[runof[c]] if runof[c] >= 0 else 0
                    reg = lab == c + 1
                    if s_ == 0:
                        lane[a.name][k] |= reg
                        lane[b.name][k] |= reg
                    elif vote[c] * s_ > 0:
                        lane[a.name][k] |= reg
                    elif vote[c] * s_ < 0:
                        lane[b.name][k] |= reg
            sk_all.append(sk)
            # where the centreline changes layer the rails take their vias: free on both
            # layers where the pair swaps sides there; elsewhere ⚠ EACH IN ITS OWN HALF
            # (optical USB_HS, 2026-11-10): free all round, the first rail's via landed
            # across the second's way into the disk and cut it off from its strip
            rs_ = np.array(rside + [0])
            for p in hp:
                k = p // (H * W)
                for t in np.nonzero(k[1:] != k[:-1])[0]:
                    r = int(p[t] % (H * W))
                    ci, cj = r // W - i0, r % W - j0
                    dk = disk(ci, cj, self.LANE_VIA)
                    k1, k2 = int(k[t]), int(k[t + 1])
                    inb = 0 <= ci < h and 0 <= cj < w
                    r1 = int(rid[k1][ci, cj]) if inb else -1
                    r2 = int(rid[k2][ci, cj]) if inb else -1
                    swap = r1 < 0 or r2 < 0 or rside[r1] != rside[r2] or rside[r1] == 0
                    for xi, x in enumerate((a, b)):
                        sgn = 1 if xi == 0 else -1
                        if swap or k1 not in sk or not inb:
                            vlane[x.name] |= dk
                        else:
                            # ⚠ A PAIR'S VIAS STAND SIDE BY SIDE (optical USB_HS, 2026-11-10):
                            # left to choose, the first rail put its via where the mate's
                            # strip met the disk, and its keep-out cut the mate off. An
                            # engineer sets the two at the pair's layer change, one each
                            # side, a via's spacing apart: each rail drops only at its own.
                            ti, tj = float(tang[0][k1][ci, cj]), float(tang[1][k1][ci, cj])
                            tn = math.hypot(ti, tj) or 1.0
                            sd = rside[r1] * sgn
                            off = self.VIA_OFF / m.pitch
                            si, sj = ci + sd * (-tj / tn) * off, cj + sd * (ti / tn) * off
                            vlane[x.name] |= disk(si, sj, 2.5 * m.pitch)
                        for kk in (k1, k2):
                            if swap or kk not in sk:
                                lane[x.name][kk] |= dk
                            else:
                                half = sk[kk][0] * rs_[sk[kk][2]] * sgn > 0
                                lane[x.name][kk] |= dk & half
        # round its own lands each rail is free: on its own side of the line where the
        # pins have one; all round at a part with none (the clamp, whose rows the rails
        # reach round); off the hops (a merge's copper) on the side nearer its own lands
        mkall = self._grid(paths, box)
        self._lanes = {}
        on = [np.concatenate([c for hp in hops for c in (hp[1][xi], hp[2][xi])]) for xi in (0, 1)]
        for xi, (x, y) in enumerate(((a, b), (b, a))):
            og = self._grid(x.pieces, box)
            sgn = 1 if xi == 0 else -1
            todo = []
            for hi, (hp, e1, e2, _, _) in enumerate(hops):
                f, l_, ls, lt = lines[hi]
                for cells, has_line, ri, endc in ((e1, ls, f, hp[0][0]), (e2, lt, l_, hp[-1][-1])):
                    s_ = rside[ri]
                    todo.append((cells[xi], cells[1 - xi], ("line" if s_ else "split") if has_line else "all",
                                 s_, sk_all[hi], endc))
            todo += [(p, np.concatenate(y.pieces), "split", 0, None, None) for p in x.pieces
                     if not np.isin(p, on[xi]).any()]
            for mine, theirs, how, side, sk, endc in todo:
                own = self._grid([mine], box).any(axis=0)
                if not own.any():
                    continue
                do = distance_transform_edt(~own) * m.pitch
                fz = do <= fan
                if how == "all":
                    # ⚠ ROUND THE PART, FROM WHERE THE LINE STOPS (optical U10, 2026-11-10):
                    # the line ends at the clamp's middle, beside DM's row; a disk round DP's
                    # own pads stopped 0.35 mm short of DP's strip. The free room is centred
                    # on the line's end and reaches the rail's farthest land.
                    r_ = int(endc % (H * W))
                    ci, cj = r_ // W - i0, r_ % W - j0
                    oi, oj = np.nonzero(own)
                    reach = float(np.max(np.hypot(oi - ci, oj - cj))) * m.pitch + self.LANE_FAN
                    fz |= disk(ci, cj, reach)
                vor = None
                if how == "split":
                    mate = self._grid([theirs], box).any(axis=0)
                    if mate.any():
                        vor = do <= distance_transform_edt(~mate) * m.pitch
                for k in range(L):
                    if not (og[k].any() or (mkall[k] & fz).any()):
                        continue
                    z = fz
                    if how == "line" and k in sk:
                        z = (fz & (sk[k][0] * side * sgn > 0) & sk[k][1]) | (own & fz)
                    elif vor is not None:
                        z = fz & vor
                    lane[x.name][k] |= z
                vlane[x.name] |= fz
            self._lanes[x.name] = (i0, j0, lane[x.name], band, vlane[x.name])

    def _lane_win(self, net, win):
        """(legal, band, via-legal) of a net's lane in a route window, or None."""
        lanes = getattr(self, "_lanes", None)
        if not lanes or net.name not in lanes:
            return None
        li0, lj0, lane, band, vlane = lanes[net.name]
        L = self.L
        i0, i1, j0, j1 = win
        lg = np.zeros((L, i1 - i0, j1 - j0), bool)
        bd = np.zeros_like(lg)
        vl = np.zeros((i1 - i0, j1 - j0), bool)
        a0, a1 = max(i0, li0), min(i1, li0 + lane.shape[1])
        b0, b1 = max(j0, lj0), min(j1, lj0 + lane.shape[2])
        if a1 > a0 and b1 > b0:
            lg[:, a0 - i0:a1 - i0, b0 - j0:b1 - j0] = lane[:, a0 - li0:a1 - li0, b0 - lj0:b1 - lj0]
            bd[:, a0 - i0:a1 - i0, b0 - j0:b1 - j0] = band[:, a0 - li0:a1 - li0, b0 - lj0:b1 - lj0]
            vl[a0 - i0:a1 - i0, b0 - j0:b1 - j0] = vlane[a0 - li0:a1 - li0, b0 - lj0:b1 - lj0]
        return lg, bd, vl
