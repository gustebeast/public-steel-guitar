"""Negotiated routing (PathFinder): every open net is routed with every other in view, and
space two nets both want is priced up round by round until nobody shares it.

Not "try orders until one works": the order is fixed (shortest first) and only matters in
round one; from then on each net pays for what it takes from the others, and what it took
last round is remembered (history), so a net that keeps fighting for a pin's only exit
learns to leave it to the net that has no other way."""
from __future__ import annotations

import math
import time

import numpy as np

from . import search as S

W_REF = 0.2          # the narrowest track: a wide net's necked width at its lands


class Net:
    def __init__(self, name, nid, width):
        self.name, self.id, self.width = name, nid, width
        self.pieces = []        # [np.array of flat cell indices (full-board, k*ny*nx + i*nx + j)]
        self.paths = []         # [np.array of flat cell indices] laid this round
        self.rec_t = None
        self.n_t = 0
        self.rec_v = None
        self.n_v = 0
        self.bbox = None
        self.failed = False
        self.plane = False
        self.via_mult = 1.0     # a matched pair's vias cost more (its via budget)
        self.partner = None     # the other net of a pair, routed right after it
        self.layers_only = None # a same_layer pair's allowed routing layers (indices)
        self.same_layer = False # in a same_layer match group
        self.merge = None       # (x, y, r): a pad-merge connector's circle (match merge_at)
        self.run_layers = None  # a same_layer pair's layers OUTSIDE its merge circle
        self.relaxed = False    # run_layers given up: it shared space round after round
        self.fixed = []         # copper drawn before negotiation (the merge crossing)
        self.stuck = 0          # consecutive rounds this net has shared space
        self.necks = []         # per path: bool per cell, True where it runs necked down
        self.legs = []          # diff-pair chain hops, in order: (from cells, to cells, label)
        self.mate = None        # the other net of a matched pair (both directions)


class Router:
    def __init__(self, model, via_cost=15.0, layer_cost=None, log=print, turn45=4.0, turn90=12.0):
        self.m = model
        self.turn45, self.turn90 = np.float32(turn45), np.float32(turn90)
        # the width a dynamic keep-out assumes of the OTHER net: the widest an un-widened
        # net runs (wider nets dilate their own test, necked cells mark narrower)
        self.wref = max(model.default_w, W_REF)
        self.log = log
        m = model
        self.L, self.H, self.W = m.L, m.ny, m.nx
        n = self.L * self.H * self.W
        self.occ_t = np.zeros(n, np.int32)
        self.gen_t = np.zeros(n, np.int64)
        self.occ_v = np.zeros(self.H * self.W, np.int32)
        self.gen_v = np.zeros(self.H * self.W, np.int64)
        self.hist = np.zeros(n, np.float32)
        self.hist_v = np.zeros(self.H * self.W, np.float32)
        self.gval = 0
        self.via_cost = via_cost
        lc = layer_cost or {}
        self.layer_cost = np.array([lc.get(L, 1.0) for L in m.route_layers], np.float32)
        # an inner layer gets a direction, as an engineer would give it one: alternate
        # horizontal/vertical preference on inner layers, outer layers free
        self.dir_cost = np.zeros((self.L, 2), np.float32)
        self.nets = []
        self.wp_used = set()      # nets that took a symmetric-swap dive

    # ----------------------------------------------------------------- pieces
    def build_nets(self, skip=(), pours=None):
        """pours: {net: set of layers it is poured on}. Such a net is joined to its planes,
        not pad to pad (see _to_plane)."""
        pours = pours or {}
        m = self.m
        L, H, W = self.L, self.H, self.W
        lid = {n: k for k, n in enumerate(m.route_layers)}
        by_net = {}
        for p in m.pads:
            if p["net"]:
                by_net.setdefault(p["net"], []).append(("p", p))
        for s in m.segs:
            if s["net"] and s["layer"] in lid:
                by_net.setdefault(s["net"], []).append(("s", s))
        for v in m.vias:
            if v["net"]:
                by_net.setdefault(v["net"], []).append(("v", v))
        for name in sorted(by_net):
            if name in skip:
                continue
            items = by_net[name]
            if sum(1 for k, _ in items if k == "p") < 2 and not any(k != "p" for k, _ in items):
                continue
            cells = [self._cells(k, it, lid) for k, it in items]
            # union items that share a cell
            up = list(range(len(items)))

            def find(a):
                while up[a] != a:
                    up[a] = up[up[a]]
                    a = up[a]
                return a
            owner = {}
            for a, cs in enumerate(cells):
                for c in cs.tolist():
                    b = owner.setdefault(c, a)
                    if b != a:
                        up[find(a)] = find(b)
            groups = {}
            for a in range(len(items)):
                groups.setdefault(find(a), []).append(a)
            if name in pours:
                from .model import _in_poly
                pl = pours[name]               # [(layer, outline pts)]

                def inside(x, y, layers):
                    return any(L_ in layers and bool(_in_poly(np.array([[x]]), np.array([[y]]), pts)[0, 0])
                               for L_, pts in pl)

                def planed(a):
                    # reached by one of the net's pours: copper on the pour's layer, inside
                    # its outline (a via or through-hole land is on every layer)
                    k, it = items[a]
                    if k == "v":
                        return inside(it["x"], it["y"], set(m.layers))
                    if k == "p":
                        return inside(it["gx"], it["gy"], set(m.layers) if it["cu"] is None else it["cu"])
                    return (inside(it["x1"], it["y1"], {it["layer"]})
                            or inside(it["x2"], it["y2"], {it["layer"]}))
                reach = [a for g in groups.values() if any(planed(a) for a in g) for a in g]
                loose = [g for g in groups.values() if not any(planed(a) for a in g)]
                if not loose:
                    continue
                net = Net(name, m.net_id[name], m.width[name])
                net.plane = True
                net.pour_polys = [pts for _, pts in pl]
                net.pieces = ([np.unique(np.concatenate([cells[a] for a in reach]))]
                              if reach else [np.empty(0, np.int64)])
                net.pieces += [np.unique(np.concatenate([cells[a] for a in g])) for g in loose]
                allc = np.concatenate(net.pieces[1:])
                r = allc % (H * W)
                ii, jj = r // W, r % W
                net.bbox = (int(ii.min()), int(ii.max()), int(jj.min()), int(jj.max()))
                self.nets.append(net)
                continue
            pieces = [np.unique(np.concatenate([cells[a] for a in g])) for g in groups.values()]
            pieces = [p for p in pieces if p.size]
            if len(pieces) < 2:
                continue
            net = Net(name, m.net_id[name], m.width[name])
            net.pieces = sorted(pieces, key=lambda p: -p.size)
            allc = np.concatenate(net.pieces)
            r = allc % (H * W)
            ii, jj = r // W, r % W
            net.bbox = (int(ii.min()), int(ii.max()), int(jj.min()), int(jj.max()))
            self.nets.append(net)
        # shortest first: the only place order matters is round one
        self.nets.sort(key=lambda n: ((n.bbox[1] - n.bbox[0]) + (n.bbox[3] - n.bbox[2]), n.name))
        # matched groups (USB pairs): vias priced to their budget, the two routed back to back
        by = {n.name: n for n in self.nets}
        for g in m.notes.get('match', ()) or ():
            names = [x for x in g.get('nets', ()) if x in by]
            # ⚠ ONLY A GROUP WITH A VIA BUDGET PRICES ITS VIAS UP (optical ULPI, 2026-11-08):
            # ULPI declares max_vias null -- 60 MHz, the budget is skew -- yet its twelve
            # nets paid x20 a via, could not escape U7's pin row, and ULPI_D3 / D4 were
            # ripped out run after run
            if g.get("max_vias") is not None:
                for x in names:
                    by[x].via_mult = 20.0
            # ⚠ A same_layer PAIR STAYS ON ITS LAYERS (optical USB_HS, 2026-11-08): the router
            # bridged J1's B-side DP on In2 and DM on F.Cu, and the pair split its layer set
            # (quality A3). Both nets may use only the layers ALL of the group's own fixed
            # copper already shares (else any layer that copper uses).
            if g.get("same_layer") and names:
                for x in names:
                    by[x].same_layer = True
            # ⚠ A PAD-MERGE CONNECTOR IS JOINED FIRST, INSIDE ITS CIRCLE, and the pair RUNS
            # on its lands' layer (optical USB_HS, 2026-11-08). A USB-C carries D+ on A6
            # and B6 either side of D-'s A7, so one rail must hop a layer to join its two
            # lands -- the standard crossing. verify excludes copper within merge_r of the
            # connector for exactly that; the router spread the hop 6 mm along B.Cu, past
            # the circle, and the pair read as split and 11 mm skewed. Join each net's
            # lands at the connector first, inside the circle (all layers), then keep the
            # run outside it on the lands' common layer (falls back if that cannot route).
            if g.get("merge_at") and names:
                at = next(((p["fpx"], p["fpy"]) for p in m.pads
                           if p.get("name", "").startswith(g["merge_at"] + ".")), None)
                if at is not None:
                    r = float(g.get("merge_r", 4.0)) - 0.5
                    for x in names:
                        by[x].merge = (at[0], at[1], r)
                    if g.get("same_layer"):
                        lid = {n_: k for k, n_ in enumerate(m.route_layers)}
                        run = set(range(len(m.route_layers)))
                        for p in m.pads:
                            if p["net"] in names and p["cu"] is not None:
                                run &= {lid[c] for c in p["cu"] if c in lid}
                        if run:
                            for x in names:
                                by[x].run_layers = run
                lid = {n_: k for k, n_ in enumerate(m.route_layers)}
                per = [{lid[s["layer"]] for s in m.segs if s["net"] == x and s["layer"] in lid}
                       for x in g.get("nets", ())]
                per = [s for s in per if s]
                keep = set.intersection(*per) if per else set()
                keep = keep or (set.union(*per) if per else set())
                if keep:
                    for x in names:
                        by[x].layers_only = keep
            if len(names) == 2:
                a_, b_ = by[names[0]], by[names[1]]
                b_.partner = a_
                a_.mate, b_.mate = b_, a_
                self.nets.remove(b_)
                self.nets.insert(self.nets.index(a_) + 1, b_)
        self._chain_legs(by, lid)
        return self.nets

    def _chain_legs(self, by, lid):
        """⚠ A diff pair's CHAIN IS AN ORDER, NOT A SET (optical USB_HS, 2026-11-08). The
        pair runs U31 -> U10 (ESD clamp: D+ on pins 1 and 6, linked under its body) -> J1.
        Routed as a tree, U31's leg joined whatever copper of the net was cheapest -- even
        J1's merge, straight past the clamp. Each hop is now drawn part to part, in order,
        and every hop must end on the next part.

        A PART IS ONE NODE: a hop may land on any of its pads of the net, and the next hop
        may leave from any of them (or the copper already joining them). Requiring the
        clamp's far pin for the outgoing hop -- true flow-through -- was tried first: on
        optical R2 that pin faces a wall (VCAP1, the PHY's 1V8 cap, the oscillator), the
        hop wrapped round the package and fenced in the other pin, and the pair came out
        13 mm skewed. Landing on the near pin keeps the clamp ON the line, its own link a
        2 mm stub, which at 480 Mbps is nothing. spec["pads"] limits a part's candidates
        as layout does."""
        m = self.m
        by_name = {}
        for p in m.pads:
            if p.get("name") and p["net"]:
                by_name.setdefault(p["name"].split(".")[0], []).append(p)
        for spec in self.m.notes.get("diff_pairs", ()) or ():
            chain = spec.get("chain") or []
            keep = spec.get("pads", {}) or {}
            for name in spec.get("nets", ()):
                net = by.get(name)
                if net is None or net.plane or len(chain) < 2:
                    continue
                cand = []
                for ref in chain:
                    ps = [p for p in by_name.get(ref, ()) if p["net"] == name
                          and (ref not in keep or p["name"].split(".", 1)[1] in keep[ref])]
                    cand.append(ps)
                if not all(cand):
                    continue
                cells = [np.unique(np.concatenate([self._cells("p", q, lid) for q in ps])) for ps in cand]
                net.legs = [(cells[k], cells[k + 1], "%s->%s" % (chain[k], chain[k + 1]))
                            for k in range(len(chain) - 1)]

    def _cells(self, kind, it, lid):
        """Flat indices of the grid cells inside an item's copper, on its layers."""
        m = self.m
        H, W = self.H, self.W
        p = m.pitch
        if kind == "p":
            from .model import pad_dist, pad_reach
            r = pad_reach(it)
            i0, i1, j0, j1 = m._window(it["gx"] - r, it["gy"] - r, it["gx"] + r, it["gy"] + r, 0.0)
            X, Y = np.meshgrid(m.cx[j0:j1], m.cy[i0:i1])
            inside = pad_dist(it, X, Y) <= 1e-9
            if not inside.any():          # a land smaller than a cell: its nearest cell
                ci, cj = m.ij(it["gx"], it["gy"])
                inside = np.zeros_like(inside)
                inside[min(max(ci - i0, 0), inside.shape[0] - 1), min(max(cj - j0, 0), inside.shape[1] - 1)] = True
            layers = [k for L_, k in lid.items() if it["cu"] is None or L_ in it["cu"]]
        elif kind == "s":
            h = it["half"]
            i0, i1, j0, j1 = m._window(min(it["x1"], it["x2"]), min(it["y1"], it["y2"]),
                                       max(it["x1"], it["x2"]), max(it["y1"], it["y2"]), h)
            X, Y = np.meshgrid(m.cx[j0:j1], m.cy[i0:i1])
            from .model import _d_pts_seg
            inside = _d_pts_seg(X, Y, it["x1"], it["y1"], it["x2"], it["y2"]) <= h + 1e-9
            layers = [lid[it["layer"]]]
        else:
            i0, i1, j0, j1 = m._window(it["x"], it["y"], it["x"], it["y"], it["r"])
            X, Y = np.meshgrid(m.cx[j0:j1], m.cy[i0:i1])
            inside = np.hypot(X - it["x"], Y - it["y"]) <= it["r"] + 1e-9
            layers = list(range(self.L))
        ii, jj = np.nonzero(inside)
        ii, jj = ii + i0, jj + j0
        out = [(k * H + ii) * W + jj for k in layers]
        return np.concatenate(out).astype(np.int64) if out else np.empty(0, np.int64)

    # ----------------------------------------------------------------- one net
    REGION_COST = 6.0                # crossing another net's regional pour (model.region_net)
    DEBUG_MERGE = False
    DIVE_STUB = 1.0                  # a diving rail keeps to the surface this near its lands
    OFFRUN_COST = 4.0                # a relaxed pair's cell price off its home layers
    RELAX_AFTER = 10                 # rounds a layer-held pair may share before it is relaxed (4 relaxed USB mid-negotiation, 11-08)
    FILL_MARGIN = 0.15               # a plane-join via's pad this far inside the fill's edge
    RING_COST = 4.0                  # inside another net's poured land's thermal room (model.ring_net)
    NECK_W = W_REF                   # a net's width where it necks down at its own lands
    NECK_MM = 1.2                    # ...within this distance of its own copper
    TURN_STATES_MAX = 40_000_000     # heading-aware search up to this many states (x9 cells)

    def _astar(self, cellf, vcellf, src, tgt, L, h, w, tb, dir_cost, vmult=1.0):
        vc = np.float32(self.via_cost * vmult)
        if L * h * w * 9 <= self.TURN_STATES_MAX and self.turn45 + self.turn90 > 0:
            return S.astar_turn(cellf, vcellf, src, tgt, L, h, w, vc, tb, dir_cost,
                                self.turn45, self.turn90)
        return S.astar(cellf, vcellf, src, tgt, L, h, w, vc, tb, dir_cost)

    def _window(self, net, margin_mm):
        mc = int(math.ceil(margin_mm / self.m.pitch))
        i0, i1, j0, j1 = net.bbox
        return (max(0, i0 - mc), min(self.H, i1 + mc + 1), max(0, j0 - mc), min(self.W, j1 + mc + 1))

    def _route_net(self, net, pf):
        m = self.m
        L, H, W = self.L, self.H, self.W
        self._wp_off = self._mate_dive(net)
        if self._wp_off is not None:
            net.relaxed = True             # its mate dived: it must be free to follow
        for strict in ((True, False) if net.run_layers and not net.relaxed else (False,)):
            self._strict = strict
            for margin in (4.0, 12.0, 1e4):
                win = self._window(net, margin)
                self._necks = []
                paths = self._route_in(net, pf, win)
                if paths is not None:
                    net.necks = [np.zeros(p.size, bool) for p in net.fixed] + self._necks
                    return list(net.fixed) + paths
                if win == (0, H, 0, W):
                    break
        return None

    def _route_in(self, net, pf, win):
        m = self.m
        L, H, W = self.L, self.H, self.W
        i0, i1, j0, j1 = win
        h, w = i1 - i0, j1 - j0
        # fixed-copper legality for this net in the window
        nid = net.id
        sl = (slice(None), slice(i0, i1), slice(j0, j1))
        fd = np.where(m.n1[sl] == nid, m.d2[sl], m.d1[sl])
        legal = fd >= net.width / 2.0 + m.clear + m.margin
        legal &= (m.edge[i0:i1, j0:j1] >= net.width / 2.0 + m.edge_clear + m.margin)[None]
        allowed = None if net.relaxed else net.layers_only
        # ⚠ WITH NO COPPER OF ITS OWN, A same_layer PAIR'S SECOND NET FOLLOWS THE FIRST
        # (optical USB_HS, 2026-11-08: layout could not lay the pair on this placement, so
        # there was nothing to key off, and DP took B.Cu while DM stayed on F.Cu).
        if (allowed is None and net.same_layer and not net.relaxed and net.partner is not None
                and net.partner.paths):
            allowed = {int(k) for pth in net.partner.paths for k in np.unique(pth // (H * W))}
        if allowed is not None:
            for k in range(L):
                if k not in allowed:
                    legal[k] = False
        circle = None
        if net.merge is not None:
            X, Y = np.meshgrid(m.cx[j0:j1], m.cy[i0:i1])
            circle = np.hypot(X - net.merge[0], Y - net.merge[1]) < net.merge[2]
            if net.run_layers and getattr(self, "_strict", False):
                for k in range(L):
                    if k not in net.run_layers:
                        legal[k] &= circle
        vlegal = np.all(fd >= m.via_d / 2.0 + m.clear + m.margin, axis=0)
        vlegal &= m.edge[i0:i1, j0:j1] >= m.via_d / 2.0 + m.edge_clear + m.margin
        vlegal &= ~m.via_ban[i0:i1, j0:j1]
        occ =self.occ_t.reshape(L, H, W)[sl].astype(np.float32)
        if net.width > self.wref + 1e-6:
            from scipy.ndimage import maximum_filter
            rr = int(math.ceil((net.width - self.wref) / 2.0 / m.pitch))
            yy, xx = np.mgrid[-rr:rr + 1, -rr:rr + 1]
            fp = (yy * yy + xx * xx) <= rr * rr
            occ = np.stack([maximum_filter(occ[k], footprint=fp) for k in range(L)])
        hist = self.hist.reshape(L, H, W)[sl]
        cell = (1.0 + hist) * (1.0 + pf * occ) * self.layer_cost[:, None, None]
        # ⚠ A RELAXED PAIR DIVES TO CROSS, THEN COMES BACK UP (optical USB_DP, 2026-11-08:
        # relaxed, it dived to swap sides with USB_DM and stayed down 13 mm, through the
        # room ULPI needed). Off its home layers it pays OFFRUN_COST a cell, so a dive is
        # as short as the crossing that needs it.
        home = net.run_layers or net.layers_only
        if net.relaxed and home:
            for k in range(L):
                if k not in home:
                    cell[k] = cell[k] * self.OFFRUN_COST
        rn = m.region_net[sl]
        cell = np.where((rn != 0) & (rn != nid), cell * self.REGION_COST, cell)
        rg = m.ring_net[sl]
        cell = np.where((rg != 0) & (rg != nid), cell * self.RING_COST, cell)
        # ⚠ A WIDE NET NECKS DOWN AT ITS OWN LANDS, as an engineer necks it: J1_VBUS at
        # 1.0 mm could not reach a USB-C pin between its neighbours and was left open. Within
        # NECK_MM of the net's own copper it may run at NECK_W where full width will not fit
        # (at a price, so it widens again as soon as it can); emit draws those cells narrow.
        neck_ok = np.zeros_like(legal)
        if net.width > self.NECK_W + 1e-6:
            from scipy.ndimage import distance_transform_edt
            own = np.zeros((L, h, w), bool)
            for p_ in net.pieces:
                kk = p_ // (H * W)
                rr = p_ % (H * W)
                ii, jj = rr // W - i0, rr % W - j0
                ok = (ii >= 0) & (ii < h) & (jj >= 0) & (jj < w)
                own[kk[ok], ii[ok], jj[ok]] = True
            narrow = fd >= self.NECK_W / 2.0 + m.clear + m.margin
            narrow &= (m.edge[i0:i1, j0:j1] >= self.NECK_W / 2.0 + m.edge_clear + m.margin)[None]
            for k in range(L):
                if own[k].any():
                    near = distance_transform_edt(~own[k]) * m.pitch <= self.NECK_MM
                    neck_ok[k] = near & narrow[k] & ~legal[k]
            cell = np.where(neck_ok, cell * 2.0, cell)
        cell = np.where(legal | neck_ok, cell, np.inf).astype(np.float32)
        self._neck_win = (neck_ok, h, w, i0, j0)
        # ⚠ A PAIR RUNS TOGETHER: the second net of a matched pair is drawn to the band one
        # pitch off its partner's centreline -- what an engineer does by routing the two as
        # one (coupled pair routing proper is ROUTER.md milestone 3; this is its first step)
        if net.partner is not None and net.partner.paths:
            from scipy.ndimage import distance_transform_edt
            mine = np.zeros((L, h, w), bool)
            for pth in net.partner.paths:
                kk = pth // (H * W)
                rr = pth % (H * W)
                ii, jj = rr // W - i0, rr % W - j0
                ok = (ii >= 0) & (ii < h) & (jj >= 0) & (jj < w)
                mine[kk[ok], ii[ok], jj[ok]] = True
            sp = net.width / 2.0 + net.partner.width / 2.0 + m.clear + m.margin + self.wref / 2.0
            for k in range(L):
                if mine[k].any():
                    dd = distance_transform_edt(~mine[k]) * m.pitch
                    band = (dd >= sp - 1e-6) & (dd <= sp + 2.5 * m.pitch)
                    cell[k][band] *= 0.6
        occv = self.occ_v.reshape(H, W)[i0:i1, j0:j1].astype(np.float32)
        hv = self.hist_v.reshape(H, W)[i0:i1, j0:j1]
        vcell = np.where(vlegal, (1.0 + hv) * (1.0 + pf * occv), np.inf).astype(np.float32)
        # the net's own fixed vias: a layer change there is free, through the via itself
        for v in m.vias:
            if v["net"] == net.name:
                ci, cj = m.ij(v["x"], v["y"])
                if i0 <= ci < i1 and j0 <= cj < j1:
                    vcell[ci - i0, cj - j0] = 0.0

        # pieces as window-local flat indices (cells inside the window only)
        def local(cells):
            k = cells // (H * W)
            r = cells % (H * W)
            ii, jj = r // W, r % W
            ok = (ii >= i0) & (ii < i1) & (jj >= j0) & (jj < j1)
            return (k[ok] * h + (ii[ok] - i0)) * w + (jj[ok] - j0)

        pieces = [local(p) for p in net.pieces]
        if any(p.size == 0 for p in pieces[(1 if net.plane else 0):]):
            return None
        cellf = cell.ravel()
        # ⚠ A LAND WITH NO LEGAL CELL (a solder jumper's lands sit closer than track + rule)
        # starts from its DEEPEST cells only -- those furthest from foreign copper -- never
        # from all of it: the first version opened the whole land and the track left from
        # the edge facing the other land (JP1, 0.077 mm against 0.127).
        fdf = fd.ravel()
        for p in pieces:
            if not np.isfinite(cellf[p]).any():
                best = p[fdf[p] >= fdf[p].max() - 1e-6]
                cellf[best] = 1.0
        n = L * h * w
        if net.plane:
            return self._to_plane(net, pieces, cellf, vcell, L, h, w, win)
        paths = []
        if circle is not None and not net.fixed:
            inside = np.tile(circle.ravel(), L)
            at = [q for q, p in enumerate(pieces) if inside[p].any()]
            if len(at) >= 2:
                cf = np.where(inside, cellf, np.inf).astype(np.float32)
                vc = np.where(circle, vcell, np.inf).astype(np.float32)
                msrc = np.zeros(n, np.bool_)
                msrc[pieces[at[0]]] = True
                todo = at[1:]
                while todo:
                    tgt = np.zeros(n, np.bool_)
                    for q in todo:
                        tgt[pieces[q]] = True
                    tk = np.nonzero(tgt)[0] % (h * w)
                    tb = np.array([(tk // w).min(), (tk // w).max(), (tk % w).min(), (tk % w).max()], np.int64)
                    # vias inside the merge circle are the crossing itself, not the run's:
                    # verify does not count them, so they cost what any via costs (at the
                    # pair's x20 budget price the two merges wrapped round each other's
                    # lands and shared space forever rather than one of them diving)
                    path = self._astar(cf, vc.ravel(), msrc, tgt, L, h, w, tb, self.dir_cost, 1.0)
                    if path.size == 0:
                        break                   # leave the rest to the open search
                    hit = next(q for q in todo if np.isin(path[0], pieces[q]))
                    todo.remove(hit)
                    self._claim_vias(path, vcell, h, w)
                    msrc[path] = True
                    msrc[pieces[hit]] = True
                    self._necks.append(self._neck_win[0].ravel()[path])
                    k_ = path // (h * w)
                    r_ = path % (h * w)
                    paths.append((k_ * H + (r_ // w + i0)) * W + (r_ % w + j0))
                joined = [q for q in at if q not in todo]
                merged = np.nonzero(msrc)[0]
                pieces = [merged] + [p for q, p in enumerate(pieces) if q not in joined]
        if net.legs:
            # the chain's hops, pad to pad and in order (_chain_legs); every piece a hop
            # touches is then one piece, and the open search joins whatever is left
            # ⚠ A HOP KEEPS CLEAR OF ITS OWN NET'S OTHER COPPER (optical USB_DM, 2026-11-08):
            # own copper is legal ground, so U31 -> U10.3 walked in through U10.4 and the
            # link under the clamp -- the stub again, by another door. Every other piece of
            # the net, and every hop already drawn, is out of bounds to a hop (grown by a
            # track and a clearance), except the two lands it joins.
            from scipy.ndimage import binary_dilation
            rr = int(math.ceil((net.width + m.clear) / m.pitch))
            yy, xx = np.mgrid[-rr:rr + 1, -rr:rr + 1]
            disk = (yy * yy + xx * xx) <= rr * rr
            done = np.zeros(n, np.bool_)
            np0, nk0, legs_ok = len(paths), len(self._necks), True
            wp = self._wp_mask(net, win, legal) if getattr(self, "_wp_off", None) is not None else None
            wleg = None
            if wp is not None:
                # the hop nearest the mate's dive carries this net's matching dive
                wk = np.nonzero(wp)[0] % (h * w)
                wy, wx = (wk // w).mean(), (wk % w).mean()

                def _cen(c):
                    q = local(c) % (h * w)
                    return ((q // w).mean(), (q % w).mean()) if q.size else (1e9, 1e9)

                def _dseg(a, b):
                    (ay, ax), (by_, bx) = a, b
                    vy, vx = by_ - ay, bx - ax
                    vv = vy * vy + vx * vx
                    t = 0.0 if vv == 0 else max(0.0, min(1.0, ((wy - ay) * vy + (wx - ax) * vx) / vv))
                    return math.hypot(wy - ay - t * vy, wx - ax - t * vx)
                wleg = min(range(len(net.legs)),
                           key=lambda q: _dseg(_cen(net.legs[q][0]), _cen(net.legs[q][1])))
            for li, (a_c, b_c, _lbl) in enumerate(net.legs):
                a_l, b_l = local(a_c), local(b_c)
                if a_l.size == 0 or b_l.size == 0:
                    legs_ok = False
                    break
                amask = np.zeros(n, np.bool_)
                amask[a_l] = True
                bmask = np.zeros(n, np.bool_)
                bmask[b_l] = True
                ends = amask | bmask
                # a part is one node: the whole piece its pads sit in is an end
                for p_ in pieces:
                    if amask[p_].any():
                        ends[p_] = True
                        a_l = np.union1d(a_l, p_)
                    elif bmask[p_].any():
                        ends[p_] = True
                        b_l = np.union1d(b_l, p_)
                other = np.zeros(n, np.bool_)
                for p_ in pieces:
                    other[p_] = True
                other |= done
                other &= ~ends
                o3 = other.reshape(L, h, w)
                ban = np.stack([binary_dilation(o3[k], disk) if o3[k].any() else o3[k]
                                for k in range(L)]).ravel() & ~ends
                cl = np.where(ban, np.inf, cellf).astype(np.float32)
                vl = np.where(ban.reshape(L, h, w).any(axis=0), np.inf, vcell).astype(np.float32)
                for p_ in (a_l, b_l):
                    if not np.isfinite(cl[p_]).any():
                        cl[p_[fdf[p_] >= fdf[p_].max() - 1e-6]] = 1.0
                s_ = np.zeros(n, np.bool_)
                s_[a_l] = True
                t_ = np.zeros(n, np.bool_)
                t_[b_l] = True
                tk = b_l % (h * w)
                tb = np.array([(tk // w).min(), (tk // w).max(), (tk % w).min(), (tk % w).max()], np.int64)
                legp = None
                if li == wleg:
                    legp = self._through(cl, vl, s_, t_, wp & np.isfinite(cl), L, h, w, tb, net.via_mult)
                    if legp is not None:
                        self.wp_used.add(net.name)
                if legp is None:
                    path = self._astar(cl, vl.ravel(), s_, t_, L, h, w, tb, self.dir_cost, net.via_mult)
                    if path.size == 0:
                        legs_ok = False
                        break
                    legp = [path]
                for path in legp:
                    self._claim_vias(path, vcell, h, w)
                    done[path] = True
                    self._necks.append(self._neck_win[0].ravel()[path])
                    k_ = path // (h * w)
                    r_ = path % (h * w)
                    paths.append((k_ * H + (r_ // w + i0)) * W + (r_ % w + j0))
                done[a_l] = True
                done[b_l] = True
            if not legs_ok:
                # no ordered hop fits in this window: the plain tree, rather than nothing
                # (a wider window retries the hops first; the last one falls through here)
                if win != (0, H, 0, W):
                    return None
                del paths[np0:]
                del self._necks[nk0:]
            else:
                hit = [q for q, p in enumerate(pieces) if done[p].any()]
                pieces = ([np.unique(np.concatenate([np.nonzero(done)[0]] + [pieces[q] for q in hit]))]
                          + [p for q, p in enumerate(pieces) if q not in hit])
                if len(pieces) == 1:
                    return paths
        src = np.zeros(n, np.bool_)
        src[pieces[0]] = True
        rest = list(range(1, len(pieces)))
        label = np.full(n, -1, np.int64)
        for q in rest:
            label[pieces[q]] = q
        while rest:
            tgt = np.zeros(n, np.bool_)
            for q in rest:
                tgt[pieces[q]] = True
            tk = np.nonzero(tgt)[0] % (h * w)
            tb = np.array([(tk // w).min(), (tk // w).max(), (tk % w).min(), (tk % w).max()], np.int64)
            path = self._astar(cellf, vcell.ravel(), src, tgt, L, h, w,
                           tb, self.dir_cost, net.via_mult)
            if path.size == 0:
                return None
            q = int(label[path[0]])
            rest.remove(q)
            self._claim_vias(path, vcell, h, w)
            src[path] = True
            src[pieces[q]] = True
            label[pieces[q]] = -1
            # back to full-board flat indices
            self._necks.append(self._neck_win[0].ravel()[path])
            k = path // (h * w)
            r = path % (h * w)
            paths.append((k * H + (r // w + i0)) * W + (r % w + j0))
        return paths

    # A FORCED PAIR SWAP IS DONE SYMMETRICALLY (optical USB_HS, 2026-11-08). When a
    # same_layer pair's rails must cross -- the clamp, the socket and the hub pin out in
    # opposite senses and the board has no room to turn a part -- one rail dives under the
    # other. Alone, that splits the pair's layer set (quality A3) and gives one rail
    # discontinuities the other lacks. An engineer swaps P and N with vias on BOTH: so the
    # mate of a rail that dives passes through the same layer within WP_MM of the dive,
    # inside a through hop (never a stub).
    WP_MM = 1.5

    def _mate_dive(self, net):
        """Full-board cells where this net's pair mate runs off its home layers outside
        the merge circle (its last laid paths), or None."""
        mate = getattr(net, "mate", None)
        home = net.run_layers or net.layers_only
        if mate is None or not mate.paths or not home or not net.legs:
            return None
        H, W = self.H, self.W
        cells = np.concatenate(mate.paths)
        k = cells // (H * W)
        off = cells[~np.isin(k, list(home))]
        if off.size and net.merge is not None:
            r_ = off % (H * W)
            d = np.hypot(self.m.cx[r_ % W] - net.merge[0], self.m.cy[r_ // W] - net.merge[1])
            off = off[d >= net.merge[2]]
        return off if off.size else None

    def _wp_mask(self, net, win, legal):
        """Window-local cells on the mate's dive layers within WP_MM of its dive."""
        from scipy.ndimage import distance_transform_edt
        H, W, L = self.H, self.W, self.L
        i0, i1, j0, j1 = win
        h, w = i1 - i0, j1 - j0
        off = self._wp_off
        k = off // (H * W)
        r_ = off % (H * W)
        ii, jj = r_ // W - i0, r_ % W - j0
        ok = (ii >= 0) & (ii < h) & (jj >= 0) & (jj < w)
        if not ok.any():
            return None
        out = np.zeros((L, h, w), bool)
        for lay in np.unique(k[ok]).tolist():
            src = np.ones((h, w), bool)
            sel = ok & (k == lay)
            src[ii[sel], jj[sel]] = False
            near = distance_transform_edt(src) * self.m.pitch <= self.WP_MM
            out[lay] = near & legal[lay]
        return out.ravel() if out.any() else None

    def _through(self, cl, vl, s_, t_, wp, L, h, w, tb, vmult):
        """A hop s_ -> t_ through a waypoint cell (wp): two searches joined at the cell, the
        second barred from the first's via spot and cells, so the dive has length. None if
        either half fails."""
        if not wp.any():
            return None
        wk = np.nonzero(wp)[0] % (h * w)
        tbw = np.array([(wk // w).min(), (wk // w).max(), (wk % w).min(), (wk % w).max()], np.int64)
        p1 = self._astar(cl, vl.ravel(), s_, wp, L, h, w, tbw, self.dir_cost, vmult)
        if p1.size == 0:
            return None
        at = int(p1[0])
        v2 = vl.copy()
        self._claim_vias(p1, v2, h, w)
        v2[(at % (h * w)) // w, (at % (h * w)) % w] = np.inf
        c2 = cl.copy()
        c2[p1[1:]] = np.inf
        s2 = np.zeros_like(s_)
        s2[at] = True
        p2 = self._astar(c2, v2.ravel(), s2, t_, L, h, w, tb, self.dir_cost, vmult)
        if p2.size == 0:
            return None
        return [p1, p2]

    def _where(self, x):
        """ " (first at x,y on layer, beside nets)" for a net's first shared cell."""
        H, W = self.H, self.W
        for pth in x.paths:
            c = pth[self.occ_t[pth] >= 2]
            if c.size:
                r_ = c[0] % (H * W)
                cxx, cyy = float(self.m.cx[r_ % W]), float(self.m.cy[r_ // W])
                near = sorted({o.name for o in self.nets if o is not x and any(
                    (np.hypot(self.m.cx[(op % (H * W)) % W] - cxx,
                              self.m.cy[(op % (H * W)) // W] - cyy) < 0.6).any()
                    for op in o.paths)})
                return " (first at %.2f,%.2f on %s, beside %s)" % (
                    cxx, cyy, self.m.route_layers[c[0] // (H * W)], ", ".join(near[:4]) or "?")
        return ""

    def _premerge(self):
        """⚠ THE PAD-MERGE CROSSING IS DRAWN ONCE, BEFORE NEGOTIATION, as an engineer draws
        it (optical USB_HS, 2026-11-08). On a USB-C, D+ lands A6 and B6 either side of D-'s
        A7 and D- lands B7 and A7 either side of D+'s A6: each rail's join wraps round the
        other's land, and negotiated freely the two wrapped round each other for twenty
        rounds and were ripped out. The fix is a decision, not a price: ONE rail dives --
        leaves each of its lands on the surface only within DIVE_STUB of it, links them on
        an inner layer -- and the OTHER wraps on the surface round that copper. Both role
        orders are tried; the shorter that works is kept. The result is each net's fixed
        copper: its lands at the connector are one piece from then on."""
        from scipy.ndimage import distance_transform_edt
        m = self.m
        L, H, W = self.L, self.H, self.W
        groups = {}
        for net in self.nets:
            if net.merge is not None:
                groups.setdefault(net.merge, []).append(net)
        for (x, y, rad), nets in groups.items():
            if len(nets) != 2:
                continue
            ci, cj = m.ij(x, y)
            R = int(math.ceil((rad + 1.0) / m.pitch))
            i0, i1, j0, j1 = (max(0, ci - R), min(H, ci + R + 1), max(0, cj - R), min(W, cj + R + 1))
            h, w = i1 - i0, j1 - j0
            n = L * h * w
            X, Y = np.meshgrid(m.cx[j0:j1], m.cy[i0:i1])
            circle = np.hypot(X - x, Y - y) < rad

            def local(cells):
                k = cells // (H * W)
                r = cells % (H * W)
                ii, jj = r // W, r % W
                ok = (ii >= i0) & (ii < i1) & (jj >= j0) & (jj < j1)
                return (k[ok] * h + (ii[ok] - i0)) * w + (jj[ok] - j0)

            def lands(net):
                inside = np.tile(circle.ravel(), L)
                return [q for q, p in enumerate(net.pieces) if inside[local(p)].any()]

            def base(net):
                sl = (slice(None), slice(i0, i1), slice(j0, j1))
                fd = np.where(m.n1[sl] == net.id, m.d2[sl], m.d1[sl])
                legal = fd >= net.width / 2.0 + m.clear + m.margin
                legal &= (m.edge[i0:i1, j0:j1] >= net.width / 2.0 + m.edge_clear + m.margin)[None]
                legal &= circle[None]
                vl = np.all(fd >= m.via_d / 2.0 + m.clear + m.margin, axis=0)
                vl &= m.edge[i0:i1, j0:j1] >= m.via_d / 2.0 + m.edge_clear + m.margin
                vl &= ~m.via_ban[i0:i1, j0:j1] & circle
                return fd, legal, vl

            def route(net, legal, vl, fd):
                qs = lands(net)
                if len(qs) != 2:
                    return None
                a, b = (local(net.pieces[q]) for q in qs)
                cell = np.where(legal, 1.0, np.inf).astype(np.float32) * self.layer_cost[:, None, None]
                cf = cell.ravel()
                fdf = fd.ravel()
                for p_ in (a, b):           # walled lands start from their deepest cells
                    if not np.isfinite(cf[p_]).any():
                        cf[p_[fdf[p_] >= fdf[p_].max() - 1e-6]] = 1.0
                vc = np.where(vl, 1.0, np.inf).astype(np.float32)
                src = np.zeros(n, np.bool_)
                src[a] = True
                tgt = np.zeros(n, np.bool_)
                tgt[b] = True
                tk = np.nonzero(tgt)[0] % (h * w)
                tb = np.array([(tk // w).min(), (tk // w).max(), (tk % w).min(), (tk % w).max()], np.int64)
                path = self._astar(cf, vc.ravel(), src, tgt, L, h, w, tb, self.dir_cost, 1.0)
                return path if path.size else None

            def keepout(path, other, legal, vl):
                """Clear `other` of this copper: tracks per layer, vias on every layer."""
                k = path // (h * w)
                r = path % (h * w)
                legal = legal.copy()
                vl = vl.copy()
                vias = np.zeros((h, w), bool)
                at = np.nonzero(k[1:] != k[:-1])[0]
                vias.ravel()[r[at]] = True
                dv = distance_transform_edt(~vias) * m.pitch if vias.any() else None
                for kk in range(L):
                    mask = np.zeros((h, w), bool)
                    mask.ravel()[r[k == kk]] = True
                    if mask.any():
                        d = distance_transform_edt(~mask) * m.pitch
                        legal[kk] &= d >= (other.width + self.wref) / 2.0 + m.clear + m.margin
                        vl &= d >= (m.via_d + self.wref) / 2.0 + m.clear + m.margin
                    if dv is not None:
                        legal[kk] &= dv >= (m.via_d + other.width) / 2.0 + m.clear + m.margin
                if dv is not None:
                    vl &= dv >= m.via_d + m.hole_to_hole
                return legal, vl

            if any(len(lands(n_)) != 2 for n_ in nets):
                continue                    # already joined (layout's flip merge laid it)
            best = None
            for diver, wrapper in ((nets[0], nets[1]), (nets[1], nets[0])):
                fd_d, lg_d, vl_d = base(diver)
                # the diver keeps to the surface only beside its own lands
                own = np.zeros((h, w), bool)
                for q in lands(diver):
                    own.ravel()[local(diver.pieces[q]) % (h * w)] = True
                theirs = np.zeros((h, w), bool)
                for q in lands(wrapper):
                    theirs.ravel()[local(wrapper.pieces[q]) % (h * w)] = True
                d_own = distance_transform_edt(~own) * m.pitch
                d_theirs = distance_transform_edt(~theirs) * m.pitch
                # nearer its own lands than the wrapper's: "within 1 mm of its lands" alone
                # still let it run under the wrapper's land tip and wrap on the surface
                near = (d_own <= self.DIVE_STUB) & (d_own < d_theirs)
                lg_d = lg_d.copy()
                lg_d[0] &= near
                # ...and drops its vias a lane clear of the wrapper's lands, or the two dive
                # vias either side of a wrapper land (1.0 mm apart on a USB-C) leave 0.4 mm
                # for a track that needs 0.5 and the wrapper cannot get back in
                lane = (m.via_d / 2.0 + wrapper.width + 2.0 * (m.clear + m.margin))
                vl_d = vl_d & (d_theirs >= lane)
                pd = route(diver, lg_d, vl_d, fd_d)
                if pd is None:
                    self.log("    (%s cannot dive: %d land(s) in the circle, %d via site(s) near them)"
                             % (diver.name, len(lands(diver)), int((vl_d & near).sum())))
                    continue
                fd_w, lg_w0, vl_w0 = base(wrapper)
                lg_w, vl_w = keepout(pd, wrapper, lg_w0, vl_w0)
                pw = route(wrapper, lg_w, vl_w, fd_w)
                if pw is None:
                    # the dive's vias closed the wrapper's way out (two vias either side of
                    # its land, side by side): route the wrapper past the dive's SURFACE
                    # stubs only, then re-drop the dive's vias clear of the wrapper --
                    # staggered, as an engineer staggers them
                    stubs = pd[(pd // (h * w)) == 0]
                    lg_s, vl_s = keepout(stubs, wrapper, lg_w0, vl_w0)
                    pw = route(wrapper, lg_s, vl_s, fd_w)
                    if pw is not None:
                        lg_d2, vl_d2 = keepout(pw, diver, lg_d, vl_d)
                        pd = route(diver, lg_d2, vl_d2, fd_d)
                        if pd is None:
                            self.log("    (%s wraps past the stubs, but %s cannot then re-dive clear of it)"
                                     % (wrapper.name, diver.name))
                            if self.DEBUG_MERGE:
                                kk = pw // (h * w); rr = pw % (h * w)
                                self.log("      wrapper path: %s" % [(round(float(m.cx[j0 + c % w]), 2), round(float(m.cy[i0 + c // w]), 2), int(k_)) for c, k_ in zip(rr.tolist(), kk.tolist())][::4])
                            pw = None
                if pw is None:
                    self.log("    (%s dives, but %s cannot wrap round it)" % (diver.name, wrapper.name))
                    if self.DEBUG_MERGE and pd is not None:
                        fd0, lg0, vl0 = base(wrapper)
                        alone = route(wrapper, lg0, vl0, fd0)
                        kk = pd // (h * w); rr = pd % (h * w)
                        pts = [(round(float(m.cx[j0 + c % w]), 2), round(float(m.cy[i0 + c // w]), 2), int(k_))
                               for c, k_ in zip(rr.tolist(), kk.tolist())]
                        self.log("      diver path (every 6th): %s" % pts[::6])
                        self.log("      wrapper alone: %s" % ("no path" if alone is None else "%d cells, layers %s"
                                 % (alone.size, sorted(set((alone // (h * w)).tolist())))))
                    continue
                tot = pd.size + pw.size
                if best is None or tot < best[0]:
                    best = (tot, diver, pd, wrapper, pw)
            if best is None:
                self.log("  %s / %s: no clean crossing at the merge connector -- left to the "
                         "negotiation" % (nets[0].name, nets[1].name))
                continue
            _, diver, pd, wrapper, pw = best
            for net, path in ((diver, pd), (wrapper, pw)):
                k = path // (h * w)
                r = path % (h * w)
                full = (k * H + (r // w + i0)) * W + (r % w + j0)
                qs = lands(net)
                joined = np.unique(np.concatenate([full] + [net.pieces[q] for q in qs]))
                net.pieces = [joined] + [p for q, p in enumerate(net.pieces) if q not in qs]
                net.fixed = [full]
            self.log("  %s dives, %s wraps: the crossing at the merge connector is drawn"
                     % (diver.name, wrapper.name))

    def _claim_vias(self, path, vcell, h, w):
        """⚠ ONE NET, ONE VIA PER SPOT (optical I2C2_SCL, 2026-11-08): two branches of a
        net each dropped a via, 0.10 mm apart wall to wall; the tidy merged them and the
        net came back open. After each branch its vias are claimed: no new via of this
        net within hole-to-hole of one, and the via itself is free to reuse -- a later
        branch changes layer THROUGH it, as an engineer would."""
        hw = h * w
        r = path % hw
        k = path // hw
        at = np.nonzero((r[1:] == r[:-1]) & (k[1:] != k[:-1]))[0]
        if at.size == 0:
            return
        m = self.m
        rad = (m.via_drill + m.hole_to_hole) / m.pitch
        R = int(math.ceil(rad))
        for c in np.unique(r[at]).tolist():
            ci, cj = c // w, c % w
            a0, a1 = max(0, ci - R), min(h, ci + R + 1)
            b0, b1 = max(0, cj - R), min(w, cj + R + 1)
            yy, xx = np.mgrid[a0:a1, b0:b1]
            near = (yy - ci) ** 2 + (xx - cj) ** 2 < rad * rad
            sub = vcell[a0:a1, b0:b1]
            sub[near & (sub > 0)] = np.inf
            vcell[ci, cj] = 0.0

    def _to_plane(self, net, pieces, cellf, vcell, L, h, w, win):
        """A pour net: pieces[0] is everything the planes already reach (vias, through-hole
        lands, copper on the net's own pour layers); every other piece is joined to it OR
        to the nearest legal via site, where a via drops into the plane -- what an engineer
        does with a ground pad the stitcher could not via."""
        H, W = self.H, self.W
        i0, i1, j0, j1 = win
        n = L * h * w
        site = np.isfinite(vcell)                       # [h, w]
        # a via joins the plane only where one of the net's pours is (a regional pour,
        # optical's +3V3D under U6, covers a corner of the board, not all of it)
        from .model import _in_poly
        X, Y = np.meshgrid(self.m.cx[j0:j1], self.m.cy[i0:i1])
        under = np.zeros(site.shape, bool)
        for pts in getattr(net, "pour_polys", ()):
            under |= _in_poly(X, Y, pts)
        # ...and only where the WHOLE via pad sits in that copper: a site at a fill's
        # edge or across one of its slivers is no join at all
        from scipy.ndimage import distance_transform_edt
        under &= distance_transform_edt(under) * self.m.pitch >= self.m.via_d / 2.0 + self.FILL_MARGIN
        site = (site & under).ravel()
        tgt0 = np.zeros(n, np.bool_)
        tgt0[pieces[0]] = True
        vs = np.tile(site, L) & np.isfinite(cellf)
        paths = []
        for q in range(1, len(pieces)):
            src = np.zeros(n, np.bool_)
            src[pieces[q]] = True
            tgt = tgt0 | vs
            tgt[pieces[q]] = False
            tk = np.nonzero(tgt)[0] % (h * w)
            if tk.size == 0:
                return None
            # heuristic box: the piece itself, since a via site is usually right beside it
            pk = pieces[q] % (h * w)
            tb = np.array([(pk // w).min(), (pk // w).max(), (pk % w).min(), (pk % w).max()], np.int64)
            path = self._astar(cellf, vcell.ravel(), src, tgt, L, h, w,
                           tb, self.dir_cost)
            if path.size == 0:
                return None
            if not tgt0[path[0]]:
                # ended on a via site: the via is a layer change at the same cell
                k0 = path[0] // (h * w)
                r0 = path[0] % (h * w)
                path = np.concatenate([[((k0 + 1) % L) * h * w + r0], path])
            self._claim_vias(path, vcell, h, w)
            tgt0[path] = True
            self._necks.append(self._neck_win[0].ravel()[path])
            k = path // (h * w)
            r = path % (h * w)
            paths.append((k * H + (r // w + i0)) * W + (r % w + j0))
        return paths

    # ----------------------------------------------------------------- occupancy
    def _mark(self, net):
        m = self.m
        L, H, W = self.L, self.H, self.W
        self.gval += 1
        rt = (net.width / 2.0 + self.wref / 2.0 + m.clear + m.margin) / m.pitch
        rvt = (m.via_d / 2.0 + self.wref / 2.0 + m.clear + m.margin) / m.pitch
        rtv = (net.width / 2.0 + m.via_d / 2.0 + m.clear + m.margin) / m.pitch
        rvv = (m.via_d + m.clear + m.margin) / m.pitch
        ks, iis, jjs, al, rads = [], [], [], [], []
        vk, vi, vj, vr = [], [], [], []
        rtn = (self.NECK_W / 2.0 + self.wref / 2.0 + m.clear + m.margin) / m.pitch
        rtvn = (self.NECK_W / 2.0 + m.via_d / 2.0 + m.clear + m.margin) / m.pitch
        for q_, path in enumerate(net.paths):
            k = path // (H * W)
            r = path % (H * W)
            ii, jj = r // W, r % W
            nk = net.necks[q_] if q_ < len(net.necks) else np.zeros(k.size, bool)
            ks.append(k); iis.append(ii); jjs.append(jj)
            al.append(np.zeros(k.size, np.bool_)); rads.append(np.where(nk, rtn, rt))
            vk.append(np.zeros(k.size, np.int64)); vi.append(ii); vj.append(jj)
            vr.append(np.where(nk, rtvn, rtv))
            via = np.nonzero(k[1:] != k[:-1])[0]
            if via.size:
                ks.append(k[via]); iis.append(ii[via]); jjs.append(jj[via])
                al.append(np.ones(via.size, np.bool_)); rads.append(np.full(via.size, rvt))
                vk.append(np.zeros(via.size, np.int64)); vi.append(ii[via]); vj.append(jj[via])
                vr.append(np.full(via.size, rvv))
        if not ks:
            net.n_t = net.n_v = 0
            return
        K, I, J = np.concatenate(ks), np.concatenate(iis), np.concatenate(jjs)
        AL, R = np.concatenate(al), np.concatenate(rads)
        cap = int(K.size * (2 * R.max() + 2) ** 2 * 1.1) + 16
        net.rec_t = np.empty(cap, np.int64)
        net.n_t = S.stamp(self.occ_t, self.gen_t, self.gval, L, H, W, K, I, J, R, AL, net.rec_t)
        VK, VI, VJ, VR = np.concatenate(vk), np.concatenate(vi), np.concatenate(vj), np.concatenate(vr)
        cap = int(VK.size * (2 * VR.max() + 2) ** 2 * 1.1) + 16
        net.rec_v = np.empty(cap, np.int64)
        net.n_v = S.stamp(self.occ_v, self.gen_v, self.gval, 1, H, W, VK, VI, VJ, VR,
                          np.zeros(VK.size, np.bool_), net.rec_v)

    def _unmark(self, net):
        if net.n_t:
            S.unstamp(self.occ_t, net.rec_t, net.n_t)
        if net.n_v:
            S.unstamp(self.occ_v, net.rec_v, net.n_v)
        net.n_t = net.n_v = 0

    def _conflicts(self, net):
        """Path cells another net's keep-out covers (own stamp counts 1 there)."""
        H, W = self.H, self.W
        bad = []
        for path in net.paths:
            c = path[self.occ_t[path] >= 2]
            if c.size:
                bad.append(c)
            k = path // (H * W)
            via = np.nonzero(k[1:] != k[:-1])[0]
            if via.size:
                r = path[via] % (H * W)
                rv = r[self.occ_v[r] >= 2]
                if rv.size:
                    bad.append(rv)       # 2-D index: handled by caller via hist_v
        return bad

    # ----------------------------------------------------------------- the loop
    def run(self, iters=40, pf0=0.5, pf_mul=1.6, hf=0.4, budget_s=1800):
        t0 = time.time()
        pf = pf0
        self._premerge()
        todo = list(self.nets)
        best, since = None, 0
        for it in range(1, iters + 1):
            for net in todo:
                self._unmark(net)
                paths = self._route_net(net, pf)
                net.failed = paths is None
                net.paths = paths or []
                if not paths:
                    net.necks = []
                self._mark(net)
            # who still shares space
            H, W = self.H, self.W
            todo = []
            nbad = 0
            for net in self.nets:
                if net.failed:
                    todo.append(net)
                    continue
                shared = False
                for path in net.paths:
                    c = path[self.occ_t[path] >= 2]
                    if c.size:
                        self.hist[c] += hf
                        shared = True
                    k = path // (H * W)
                    via = np.nonzero(k[1:] != k[:-1])[0]
                    if via.size:
                        r = path[via] % (H * W)
                        rv = r[self.occ_v[r] >= 2]
                        if rv.size:
                            self.hist_v[rv] += hf
                            shared = True
                if shared:
                    todo.append(net)
                    nbad += 1
                    net.stuck += 1
                    # ⚠ A RULE THAT CANNOT BE MET IS DROPPED, NOT ENFORCED INTO AN OPEN NET
                    # (optical USB_HS, 2026-11-08: held to F.Cu, the pair shared space to
                    # the end and was ripped out -- A* always finds a path, so "no path"
                    # never came to relax it). A pair still sharing after RELAX_AFTER
                    # rounds is routed on any layer from then on, partner included.
                    if ((net.run_layers or net.layers_only or net.same_layer) and not net.relaxed
                            and net.stuck >= self.RELAX_AFTER):
                        for x in (net, net.partner) + tuple(o for o in self.nets if o.partner is net):
                            if x is not None and not x.relaxed:
                                x.relaxed = True
                                where = self._where(x)
                                self.log("  %s: kept to its layers it still shares space "
                                         "after %d rounds%s -- routing it on any layer"
                                         % (x.name, net.stuck, where))
                else:
                    net.stuck = 0
            nfail = sum(n.failed for n in self.nets)
            self.log("  round %2d: %3d net(s) sharing, %d with no path, pf %.2f, %.0f s"
                     % (it, nbad, nfail, pf, time.time() - t0))
            if not todo:
                break
            # a negotiation that has stopped improving will not start again by pricing harder
            score = nbad + nfail
            if best is None or score < best:
                best, since = score, 0
            else:
                since += 1
                if since >= 8:
                    self.log("  no better in 8 rounds: stopping")
                    break
            if time.time() - t0 > budget_s:
                self.log("  out of time")
                break
            pf *= pf_mul
        # anything still sharing comes out: a legal board with a net open beats a short
        for net in todo:
            if not net.failed:
                self.log("  %s still shares space%s: ripped out" % (net.name, self._where(net)))
            self._unmark(net)
            net.paths = []
            net.necks = []
            net.failed = True
        return [n for n in self.nets if n.failed]
