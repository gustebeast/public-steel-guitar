"""Negotiated routing (PathFinder): every open net is routed with every other in view, and
space two nets both want is priced up round by round until nobody shares it.

Not "try orders until one works": the order is fixed (shortest first) and only matters in
round one; from then on each net pays for what it takes from the others, and what it took
last round is remembered (history), so a net that keeps fighting for a pin's only exit
learns to leave it to the net that has no other way."""
from __future__ import annotations

import math
import os
import time

import numpy as np

from . import search as S
from .model import GROUND_RE

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
        self.group = None       # its match group (board.json "match" entry), if any
        self.force_layers = None  # the pair finish's layer set for this attempt (outside the merge circle)
        self.main_xy = None     # a pour net's island re-join: the fill its main body reaches (bool[H, W])
        self.keep_paths = None  # ...and the joins of its good pieces, kept as laid {piece: (path, necks)}


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
            for x in names:
                by[x].group = g
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
            # ⚠ A same_layer PAIR WITHOUT A MERGE CONNECTOR RUNS ON ITS LANDS' LAYER TOO
            # (optical HUB_PHY, 2026-11-09): nothing held it, the leading rail dived to B.Cu
            # wherever its lane was busy, its mate followed the layers it was handed, and the
            # negotiation ended with the pair split -- which no finish attempt could undo on
            # a board settled round it. An engineer lays a hub-to-PHY pair on the layer both
            # chips sit on. Same strict-then-relaxed rule as the merge case.
            if g.get("same_layer") and not g.get("merge_at") and names:
                lid_ = {n_: k for k, n_ in enumerate(m.route_layers)}
                run = set(range(len(m.route_layers)))
                for p in m.pads:
                    if p["net"] in names and p["cu"] is not None:
                        run &= {lid_[c] for c in p["cu"] if c in lid_}
                if run and len(run) < len(m.route_layers):
                    for x in names:
                        by[x].run_layers = run
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
                net.legs = [(cells[k], cells[k + 1], "%s->%s" % (chain[k], chain[k + 1]),
                             chain[k] in keep, chain[k + 1] in keep)
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
    WIDEN_AFTER = 3                  # rounds a net may share before its search window widens...
    STALL_ROUNDS = 2                 # ...once the whole negotiation is this many rounds without gain
    RELAX_AFTER = 10                 # rounds a layer-held pair may share before it is relaxed (4 relaxed USB mid-negotiation, 11-08)
    FILL_MARGIN = 0.15               # a plane-join via's pad this far inside the fill's edge
    PLANE_JOIN_MM = (2.0, 6.0)       # a plane join looks this near its piece first (then everywhere)
    RING_COST = 4.0                  # inside another net's poured land's thermal room (model.ring_net)
    VOID_COST = 3.0                  # over a void in the track's return plane (model.ref_void)
    NECK_W = W_REF                   # a net's width where it necks down at its own lands
    NECK_MM = 1.2                    # ...within this distance of its own copper
    TURN_STATES_MAX = 40_000_000     # heading-aware search up to this many states (x9 cells)
    PAIR_PUSH = 0.01                 # the finish's last attempts price others' copper this low (_finish_pairs)
    PAIR_WALL = True                 # in a pair attempt the mate's copper is a wall (_pair_try)
    PLANE_MAIN = True                # plane joins aim at the main body's fill as it stands (_rounds)
    PLANE_KEEP = True                # a sharing plane net re-joins only its sharing pieces (_rounds)

    # ⚠ HEURISTIC WEIGHT 1.2 (optical S53o0, 2026-11-09): negotiation 123 -> 90 s, same
    # nets, same pair faults (none), +0.4 % track, vias 192 -> 191. Congestion pricing
    # leaves the straight-line heuristic weak; a small weight buys most of the speed back.
    ASTAR_EPS = 1.2
    # ⚠ HEURISTIC TO THE NEAREST TARGET CELL, NOT ITS BOX (optical BOOT0, 2026-11-09: lands
    # spread over a 9 x 15 mm box left the search unguided inside it -- 7.7 M states, 5.6 s,
    # for one 46 mm net). See search.astar_s_h.
    HMAP = True

    # ⚠ "NO PATH" IS PROVEN BY LABELLING, NOT BY FLOODING (optical USB_DM, 2026-11-09): a
    # hop with no way through a 12 mm window popped 8.1 M states to say so, and the pair
    # finish asked that question twice an attempt -- 71 of its 85 s. Connected components
    # of the passable cells, joined across layers wherever a via may stand, are a superset
    # of what the search can reach (it moves 8-way, changes layer only at a via cell), so
    # "not connected" is exactly "no path" and the search is skipped. Asked only where
    # "no path" is common (a pair's hops, tried in small windows first): before every
    # search it cost output_panel 48 -> 81 s.
    REACH_MIN = 300_000              # cells (L x h x w) from which a search is checked first

    def _reachable(self, cellf, vcellf, src_idx, tgt, L, h, w):
        from scipy.ndimage import label
        fin = np.isfinite(cellf).reshape(L, h, w)
        s_ok = src_idx[fin.ravel()[src_idx]]
        if s_ok.size == 0:
            return False
        if tgt[s_ok].any():
            return True
        labs = np.zeros((L, h, w), np.int32)
        base = 0
        st8 = np.ones((3, 3), bool)
        for k in range(L):
            if fin[k].any():
                lk, nk = label(fin[k], structure=st8)
                labs[k] = np.where(lk > 0, lk + base, 0)
                base += nk
        up = np.arange(base + 1)

        def find(a):
            while up[a] != a:
                up[a] = up[up[a]]
                a = up[a]
            return a
        vf = np.isfinite(vcellf).reshape(h, w)
        for k1 in range(L):
            for k2 in range(k1 + 1, L):
                mm = vf & fin[k1] & fin[k2]
                if mm.any():
                    key = np.unique(labs[k1][mm].astype(np.int64) * (base + 1) + labs[k2][mm])
                    for a_, b_ in zip((key // (base + 1)).tolist(), (key % (base + 1)).tolist()):
                        ra, rb = find(a_), find(b_)
                        if ra != rb:
                            up[ra] = rb
        lf = labs.ravel()
        sr = {find(int(x)) for x in np.unique(lf[s_ok])}
        tl = np.unique(lf[np.flatnonzero(tgt)])
        return any(find(int(x)) in sr for x in tl if x > 0)

    def _astar(self, cellf, vcellf, src, tgt, L, h, w, tb, dir_cost, vmult=1.0, check=False):
        vc = np.float32(self.via_cost * vmult)
        bufs = self.__dict__.setdefault("_bufs", S.Buffers())
        src_idx = np.flatnonzero(src).astype(np.int64)
        eps = np.float32(self.ASTAR_EPS)
        if check and L * h * w >= self.REACH_MIN and not self._reachable(cellf, vcellf, src_idx, tgt, L, h, w):
            return np.empty(0, np.int64)
        turn = L * h * w * 9 <= self.TURN_STATES_MAX and self.turn45 + self.turn90 > 0
        if self.HMAP:
            # straight-line distance to the nearest target cell, in cells (search.py)
            from scipy.ndimage import distance_transform_edt
            t2 = tgt.reshape(L, h * w).any(axis=0).reshape(h, w)
            hmap = distance_transform_edt(~t2).astype(np.float32).ravel()
            if turn:
                g, par, st, base = bufs.take(L * h * w * 9)
                return S.astar_turn_s_h(cellf, vcellf, src_idx, tgt, L, h, w, vc, tb, hmap,
                                        dir_cost, self.turn45, self.turn90, eps, g, par, st, base)
            g, par, st, base = bufs.take(L * h * w)
            return S.astar_s_h(cellf, vcellf, src_idx, tgt, L, h, w, vc, tb, hmap, dir_cost, eps,
                               g, par, st, base)
        if turn:
            g, par, st, base = bufs.take(L * h * w * 9)
            return S.astar_turn_s(cellf, vcellf, src_idx, tgt, L, h, w, vc, tb, dir_cost,
                                  self.turn45, self.turn90, eps, g, par, st, base)
        g, par, st, base = bufs.take(L * h * w)
        return S.astar_s(cellf, vcellf, src_idx, tgt, L, h, w, vc, tb, dir_cost, eps,
                         g, par, st, base)

    USE_GLOBAL = True                # plan every net on a coarse grid first (globalroute.py): placement feedback
    # ⚠ CORRIDORS DID NOT PAY (optical S53o0, 2026-11-09): holding the detailed search to
    # the plan halved round 1 but nets shared longer, 123 s either way (131 s releasing a
    # net at its first share). Kept, off, for a better plan to try again.
    CORRIDORS = False
    CORR_WIDEN = 2                   # corridor = the plan's squares widened this many squares
    CORR_RELAX = 3                   # rounds a net may share space inside its corridor before it leaves it

    def _corridor(self, net):
        """⚠ PLAN FIRST, THEN DRAW (2026-11-09): with congestion priced in, a long net's
        true cost runs far over the straight-line heuristic and A* explored millions of
        states (optical BOOT0, 3.4 s a search). The global plan gives each net a corridor;
        the detailed search keeps to it, and leaves it only if no path fits there or the
        net keeps sharing space (CORR_RELAX rounds): a plan is a guide, not a cage."""
        gr = getattr(self, "_gr", None)
        if (not self.CORRIDORS or gr is None or net.plane or net.stuck >= self.CORR_RELAX
                or net.fixed):
            return None
        c = gr.corridor(net.name, widen=self.CORR_WIDEN)
        if not c.any():
            return None
        # every land of the net must sit in it, or the search cannot even start there
        for p in net.pieces:
            r = p % (self.H * self.W)
            if not c[(r // self.W) // gr.b, (r % self.W) // gr.b].any():
                return None
        return c

    # ⚠ A FINE-PITCH PIN LEAVES STRAIGHT OUT (optical U7, C112 moved 0.6 mm, 2026-11-09):
    # eight ULPI pins at 0.5 mm pitch all leave north on F.Cu; straight-out escapes fit (a
    # track and its clearance is 0.357), but the router laid them as it pleased, a neighbour
    # jogged into the next pin's exit, and whichever of D3 / D4 went second could not get
    # out -- both ripped out, on a placement whose neighbours route. An engineer plans the
    # fan-out first: each pin's first ESC_MM is its own. Other nets crossing that stub pay
    # ESC_COST (a price, not a wall: a board that needs it can still cross).
    ESC_COST = 4.0
    ESC_MM = 0.8
    ESC_PITCH = 0.8                  # a part is fine-pitch below this pad pitch...
    ESC_PINS = 8                     # ...with at least this many pads

    def _escape_map(self):
        es = getattr(self, "_esc", None)
        if es is not None:
            return es
        m = self.m
        L, H, W = self.L, self.H, self.W
        es = np.zeros((L, H, W), np.int32)
        lid = {n_: k for k, n_ in enumerate(m.route_layers)}
        plane = set(m.pours)
        by = {}
        for p in m.pads:
            ref = (p.get("name") or "").rsplit(".", 1)[0]
            if ref:
                by.setdefault(ref, []).append(p)
        need = self.wref / 2.0 + m.clear + m.margin - m.pitch
        for ref, pads in by.items():
            if len(pads) < self.ESC_PINS:
                continue
            xy = np.array([(p["gx"], p["gy"]) for p in pads])
            d = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
            np.fill_diagonal(d, np.inf)
            if np.median(d.min(axis=1)) >= self.ESC_PITCH:
                continue
            cx, cy = xy.mean(axis=0)
            for p in pads:
                if not p["net"] or p["net"] in plane or p["net"] not in m.net_id or not p.get("cu"):
                    continue
                ks = [lid[c] for c in p["cu"] if c in lid]
                if len(ks) != 1:
                    continue                # a through land escapes by any layer
                ax, ay = p["x2"] - p["x1"], p["y2"] - p["y1"]
                la = math.hypot(ax, ay)
                if la < 1e-6:
                    continue
                ux, uy = ax / la, ay / la
                if (p["gx"] - cx) * ux + (p["gy"] - cy) * uy < 0:
                    ux, uy = -ux, -uy
                tx, ty = p["gx"] + ux * (la / 2.0 + p["r"]), p["gy"] + uy * (la / 2.0 + p["r"])
                ex, ey = tx + ux * self.ESC_MM, ty + uy * self.ESC_MM
                x0, x1 = min(tx, ex) - need, max(tx, ex) + need
                y0, y1 = min(ty, ey) - need, max(ty, ey) + need
                j0, j1 = max(0, int((x0 - m.x0) / m.pitch)), min(W, int((x1 - m.x0) / m.pitch) + 2)
                i0, i1 = max(0, int((y0 - m.y0) / m.pitch)), min(H, int((y1 - m.y0) / m.pitch) + 2)
                if i0 >= i1 or j0 >= j1:
                    continue
                X, Y = np.meshgrid(m.cx[j0:j1], m.cy[i0:i1])
                t = np.clip((X - tx) * ux + (Y - ty) * uy, 0.0, self.ESC_MM)
                dd = np.hypot(X - (tx + t * ux), Y - (ty + t * uy))
                sub = es[ks[0], i0:i1, j0:j1]
                sub[(dd < need) & (sub == 0)] = m.net_id[p["net"]]
        self._esc = es
        return es

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
        # the global plan's corridor first (globalroute.py), then the net's own windows
        corr = self._corridor(net)
        for strict in ((True, False) if net.run_layers and not net.relaxed else (False,)):
            self._strict = strict
            # ⚠ A NET THAT KEEPS SHARING LOOKS WIDER (pi_cap, 2026-11-09): the window grew
            # only when it held NO path, and a shared one always exists, so SCK_FOOT_PI and
            # UI_SW_C fought over one gap in the socket row for eight rounds at pf 576 while
            # room lay just outside both windows, and both were ripped out. An engineer
            # stuck like that steps back: once the negotiation has STALLED (no better for
            # STALL_ROUNDS rounds), a net that has shared WIDEN_AFTER rounds starts at
            # 12 mm, after twice that over the whole board. Only when stalled: widening
            # while the negotiation still improved moved optical's nets round its USB pair
            # and left the pair unfinishable; and never a matched pair, which has its own
            # way out (RELAX_AFTER, then its finish).
            margins = (4.0, 12.0, 1e4)
            if net.mate is not None or not getattr(self, "_stalled", False):
                pass
            elif net.stuck >= 2 * self.WIDEN_AFTER:
                margins = (1e4,)
            elif net.stuck >= self.WIDEN_AFTER:
                margins = (12.0, 1e4)
            for margin in ((("corr", corr),) if corr is not None else ()) + margins:
                if isinstance(margin, tuple):
                    self._corr = margin[1]
                    win = self._window(net, 4.0)
                else:
                    self._corr = None
                    win = self._window(net, margin)
                self._necks = []
                paths = self._route_in(net, pf, win)
                self._corr = None
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
        if net.run_layers and net.merge is None and getattr(self, "_strict", False):
            for k in range(L):
                if k not in net.run_layers:
                    legal[k] = False
        if net.force_layers is not None:
            for k in range(L):
                if k not in net.force_layers:
                    legal[k] = (legal[k] & circle) if circle is not None else False
        corr = getattr(self, "_corr", None)
        if corr is not None:
            gb = self._gr.b
            legal &= corr[np.ix_(np.arange(i0, i1) // gb, np.arange(j0, j1) // gb)][None]
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
        if self.ESC_COST > 1.0:
            es = self._escape_map()[sl]
            cell = np.where((es != 0) & (es != nid), cell * self.ESC_COST, cell)
        rg = m.ring_net[sl]
        cell = np.where((rg != 0) & (rg != nid), cell * self.RING_COST, cell)
        # over a slot in its return plane a signal pays VOID_COST a cell, so it crosses
        # square and short, never along (model._ref_voids)
        if not GROUND_RE.match(net.name):
            cell = np.where(m.ref_void[sl], cell * self.VOID_COST, cell)
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
            bc_ = int(math.ceil(sp / m.pitch + 2.5)) + 1
            for k in range(L):
                if mine[k].any():
                    # only round the partner's copper (the band is within sp of it)
                    ti, tj = np.nonzero(mine[k])
                    a0, a1 = max(0, ti.min() - bc_), min(h, ti.max() + bc_ + 1)
                    b0, b1 = max(0, tj.min() - bc_), min(w, tj.max() + bc_ + 1)
                    dd = distance_transform_edt(~mine[k][a0:a1, b0:b1]) * m.pitch
                    band = (dd >= sp - 1e-6) & (dd <= sp + 2.5 * m.pitch)
                    cell[k][a0:a1, b0:b1][band] *= 0.6
        occv = self.occ_v.reshape(H, W)[i0:i1, j0:j1].astype(np.float32)
        hv = self.hist_v.reshape(H, W)[i0:i1, j0:j1]
        vcell = np.where(vlegal, (1.0 + hv) * (1.0 + pf * occv), np.inf).astype(np.float32)
        # ⚠ IN A PAIR ATTEMPT THE MATE IS A WALL, NOT A PRICE (optical HUB_PHY, 2026-11-09):
        # _pair_try refuses any attempt whose rails overlap, and at the finish's price the
        # cheapest way past other nets' copper was straight over the mate -- every attempt
        # refused, none ever offered to _displace, the pair left split across layers. An
        # engineer lays the second rail beside the first and moves what is in the way: here
        # it may not touch the mate, so it takes the lane through others' space, and that
        # attempt goes to _displace like any other laid to the rules.
        mt = net.mate if net.mate is not None else net.partner
        if getattr(self, "_pair_wall", False) and mt is not None and mt.paths:
            from scipy.ndimage import distance_transform_edt
            theirs = np.zeros((L, h, w), bool)
            mine_ = np.zeros((L, h, w), bool)
            for src_, dst_ in ((mt.paths, theirs), (net.pieces, mine_)):
                for pth in src_:
                    kk = pth // (H * W)
                    rr_ = pth % (H * W)
                    ii, jj = rr_ // W - i0, rr_ % W - j0
                    ok = (ii >= 0) & (ii < h) & (jj >= 0) & (jj < w)
                    dst_[kk[ok], ii[ok], jj[ok]] = True
            gap = (net.width + mt.width) / 2.0 + m.clear + m.margin
            gc_ = int(math.ceil(gap / m.pitch)) + 1
            for k in range(L):
                if theirs[k].any():
                    # only round the mate's own copper: the transform of the whole window
                    # cost more than the searches it shapes
                    ti, tj = np.nonzero(theirs[k])
                    a0, a1 = max(0, ti.min() - gc_), min(h, ti.max() + gc_ + 1)
                    b0, b1 = max(0, tj.min() - gc_), min(w, tj.max() + gc_ + 1)
                    wall = ((distance_transform_edt(~theirs[k][a0:a1, b0:b1]) * m.pitch < gap - 1e-6)
                            & ~mine_[k][a0:a1, b0:b1])
                    cell[k][a0:a1, b0:b1][wall] = np.inf
                    vcell[a0:a1, b0:b1][wall] = np.inf
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
            for li, (a_c, b_c, _lbl, a_dec, b_dec) in enumerate(net.legs):
                a_l, b_l = local(a_c), local(b_c)
                if a_l.size == 0 or b_l.size == 0:
                    legs_ok = False
                    break
                amask = np.zeros(n, np.bool_)
                amask[a_l] = True
                bmask = np.zeros(n, np.bool_)
                bmask[b_l] = True
                ends = amask | bmask
                # a part is one node: the whole piece its pads sit in is an end...
                # ⚠ ...UNLESS ITS LANDING PADS ARE DECLARED (optical USB_HS, 2026-11-09).
                # diff_pairs pads {J1: [A6, A7]} is the pair's chirality at the socket, and
                # the merge piece joins A6 to B6: grown to the piece, USB_DP landed on B6
                # (nearest U10), the pair arrived DM-west-of-DP, crossed again outside the
                # merge circle, and broke the 2-via budget on 4 of 11 placements. A declared
                # end is its pads; the rest of its piece is out of bounds like other copper.
                for p_ in pieces:
                    if amask[p_].any() and not a_dec:
                        ends[p_] = True
                        a_l = np.union1d(a_l, p_)
                    elif bmask[p_].any() and not b_dec:
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
                    path = self._astar(cl, vl.ravel(), s_, t_, L, h, w, tb, self.dir_cost, net.via_mult,
                                       check=True)
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

    def pair_measure(self, net):
        """{name: (length mm, {layer index: mm}, vias)} for a pair net and its mate, as
        verify.py measures them: copper whose midpoint is within the group's merge_r of
        the merge connector is not counted. None if the net is not in a pair."""
        mate = getattr(net, "mate", None)
        if mate is None or net.group is None:
            return None
        H, W = self.H, self.W
        cx, cy, p = self.m.cx, self.m.cy, self.m.pitch
        ctr = None
        if net.merge is not None:
            ctr = (net.merge[0], net.merge[1], float(net.group.get("merge_r", 4.0)))
        out = {}
        for x in (net, mate):
            tot, per, nv = 0.0, {}, 0
            for pth in x.paths:
                if pth.size < 2:
                    continue
                k = pth // (H * W)
                r_ = pth % (H * W)
                X, Y = cx[r_ % W], cy[r_ // W]
                mx, my = (X[1:] + X[:-1]) / 2.0, (Y[1:] + Y[:-1]) / 2.0
                keep = np.ones(mx.size, bool) if ctr is None else                     np.hypot(mx - ctr[0], my - ctr[1]) >= ctr[2]
                via = (k[1:] != k[:-1]) & keep
                nv += int(via.sum())
                st = np.hypot(X[1:] - X[:-1], Y[1:] - Y[:-1]) * ~via * keep
                for lay in np.unique(k[:-1][st > 0]).tolist():
                    mm = float(st[k[:-1] == lay].sum())
                    per[lay] = per.get(lay, 0.0) + mm
                    tot += mm
            out[x.name] = (tot, per, nv)
        return out

    def pair_faults(self, net):
        """verify.py's pair rules on the pair as laid: a list of (fault, net names)."""
        ms = self.pair_measure(net)
        if not ms or net.failed or net.mate.failed:
            return []
        g = net.group
        bad = []
        if g.get("same_layer") and len({frozenset(v[1]) for v in ms.values()}) != 1:
            bad.append(("layers", tuple(ms)))
        mv = g.get("max_vias")
        if mv is not None:
            over = tuple(n for n, v in ms.items() if v[2] > mv)
            if over:
                bad.append(("vias", over))
        sk = g.get("max_skew_mm")
        ls = [v[0] for v in ms.values()]
        if sk is not None and max(ls) - min(ls) > sk:
            bad.append(("skew", tuple(ms)))
        return bad

    # ⚠ A PAIR IS FINISHED AS A PAIR, AFTER THE NEGOTIATION (optical USB_HS, 2026-11-09):
    # the negotiation relaxed USB_DP / USB_DM to any layer on every placement of an
    # 18-nudge series, and whether the relaxed pair came out legal was luck -- 4 of 11
    # valid placements split the layer set, 4 broke the via budget, 1 the skew. The
    # negotiation's test is "nobody shares a cell", which a split pair passes. So once the
    # board has settled, each pair that breaks verify's rules is ripped up and laid again
    # the way an engineer lays it, everything else held: both on the home layers; else one
    # rail dives on ONE named layer and the other follows through the same spot (each
    # order, plain and with dives priced harder). The first attempt that meets the rules
    # and shares nothing is kept; if none does, the fewest faults win, the original first.
    def _finish_pairs(self):
        pf = getattr(self, "_pf_last", 1.0)
        for a in list(self.nets):
            b = a.mate
            if b is None or a.partner is not None or a.group is None or a.failed or b.failed:
                continue
            f0 = self.pair_faults(a)
            if not f0:
                continue
            home = set(a.run_layers or a.layers_only or range(self.L))
            others = sorted((k for k in range(self.L) if k not in home),
                            key=lambda k: (float(self.layer_cost[k]), k))
            keep = {x: (x.paths, x.necks, x.failed, x.relaxed, x.force_layers) for x in (a, b)}
            cands = [(a, b, False, None, 1.0, False, 1.0), (b, a, False, None, 1.0, False, 1.0)]
            # ⚠ A SAME-LAYER PAIR WITH NO HOME LAYERS IS ALSO TRIED ONE LAYER AT A TIME
            # (optical HUB_PHY, 2026-11-09): free to use every layer, the second rail dived
            # wherever the first had taken its lane, and the only attempts were the two
            # orders -- both broke same_layer. An engineer picks the layer for the pair and
            # lays both on it; each layer is offered, cheapest first, both orders.
            if a.same_layer and not (a.run_layers or a.layers_only):
                for k in sorted(range(self.L), key=lambda k: (float(self.layer_cost[k]), k)):
                    for f_, s_ in ((a, b), (b, a)):
                        cands.append((f_, s_, True, {k}, 1.0, True, 1.0))
            # a second dive is what breaks a via budget: the last attempts price vias x5
            for vm in (1.0, 5.0):
                for d in others:
                    for f_, s_ in ((a, b), (b, a)):
                        for om in (1.0, 4.0):
                            cands.append((f_, s_, True, home | {d}, om, True, vm))
            # ⚠ LAY IT WHERE IT SHOULD GO, THEN MOVE THE REST (optical USB_HS, 2026-11-09):
            # at the finish's congestion price every home-layer attempt went the long way
            # round other nets (skew 52-77 mm) or dived to cross them (via budget), and
            # neither is "to the rules", so _displace never saw one. These last attempts
            # price other nets' copper at PAIR_PUSH x the finish's price -- the short way, on
            # the pair's own layers -- and an attempt to the rules goes to _displace.
            for f_, s_ in ((a, b), (b, a)):
                cands.append((f_, s_, False, None, 1.0, True, 1.0, self.PAIR_PUSH))
            ms0 = self.pair_measure(a)
            l0 = [v[0] for v in ms0.values()]
            best, best_key = None, (0, len(f0), max(l0) - min(l0))
            ruled = None                   # (shared cells, skew, state): to the rules, but in others' space
            for c in cands:
                got = self._pair_try(pf * (c[7] if len(c) > 7 else 1.0), *c[:7])
                if os.environ.get("PAIR_DEBUG"):
                    self.log("    try %s first relax=%s layers=%s off x%g via x%g: %s" % (
                        c[0].name, c[2], c[3], c[4], c[6],
                        "no path" if got is None else (got, round(max(
                            v[0] for v in self.pair_measure(a).values()) - min(
                            v[0] for v in self.pair_measure(a).values()), 2))))
                if got is None:
                    continue
                sh, fl = got
                ms = self.pair_measure(a)
                ls = [v[0] for v in ms.values()]
                key = (sh, len(fl), max(ls) - min(ls))
                if sh == 0 and not fl:
                    best = None
                    self.log("  pair %s/%s: %s -- refinished (%s first, %s)" % (
                        a.name, b.name, ", ".join(x[0] for x in f0), c[0].name,
                        "home layers" if c[3] is None else "+" + "/".join(
                            self.m.route_layers[k] for k in sorted(c[3] - home))))
                    break
                if not fl and (ruled is None or (sh, key[2]) < ruled[:2]):
                    ruled = (sh, key[2], {x: (x.paths, x.necks, x.failed, x.relaxed, x.force_layers)
                                          for x in (a, b)})
                if key < best_key:
                    best_key = key
                    best = {x: (x.paths, x.necks, x.failed, x.relaxed, x.force_layers) for x in (a, b)}
            else:
                if ruled is not None and self._displace(a, b, ruled[2], pf):
                    self.log("  pair %s/%s: %s -- laid to the rules through %d cell(s) of other "
                             "nets' space, which re-negotiated round it" % (
                                 a.name, b.name, ", ".join(x[0] for x in f0), ruled[0]))
                    for x in (a, b):
                        x.force_layers = None
                    continue
                st = best or keep
                for x in (a, b):
                    self._unmark(x)
                for x in (a, b):
                    x.paths, x.necks, x.failed, x.relaxed, x.force_layers = st[x]
                    self._mark(x)
                self.log("  pair %s/%s: %s -- no attempt met the rules%s" % (
                    a.name, b.name, ", ".join(x[0] for x in f0),
                    "; kept the one with fewest faults %s" % (best_key,) if best else "; kept as negotiated"))
            for x in (a, b):
                x.force_layers = None

    # ⚠ THE PAIR FIRST, THEN WHAT IT DISPLACED (optical ONX3, 2026-11-09): eight of eighteen
    # attempts laid USB_HS to every rule, each through 14-90 cells the board had settled
    # round the old pair, so all were refused and the FAIL stayed. An engineer lays the
    # pair and moves the traces in its way. The best such attempt is held and the nets it
    # crosses negotiate round it; kept only if no more nets end open than before.
    def _displace(self, a, b, state, pf):
        saved = {n: (n.paths, n.necks, n.failed) for n in self.nets}
        lock = {a, b}
        # ⚠ THE PAIR'S OWN FLAGS ARE NOT COUNTED (optical, 2026-11-09): the last attempt
        # tried may have found no path and left a rail marked failed, so "open before"
        # counted 1, and a displacement that left LED_ROW open passed as no worse.
        fail0 = sum(n.failed for n in self.nets if n not in lock)
        for x in (a, b):
            self._unmark(x)
        for x in (a, b):
            x.paths, x.necks, x.failed, x.relaxed, x.force_layers = state[x]
            self._mark(x)
        todo = [n for n in self.nets if n not in lock and not n.failed and self._conflicts(n)]
        left, _ = self._rounds(todo, pf, 12, 600, locked=lock)
        fail1 = (sum(n.failed for n in self.nets if n not in lock)
                 + sum(not n.failed for n in left if n not in lock))
        if fail1 <= fail0 and not self.pair_faults(a):
            self._rip(left)
            return True
        self.log("  pair %s/%s: re-negotiating round it left %d net(s) open (was %d) -- put back"
                 % (a.name, b.name, fail1, fail0))
        for n in self.nets:
            self._unmark(n)
        for n in self.nets:
            n.paths, n.necks, n.failed = saved[n]
            self._mark(n)
        return False

    # ----------------------------------------------------------------- pour islands
    FILL_MIN_W = 0.2                 # the refill's thinnest copper: narrower necks are cut

    def _islands(self, net):
        """Where a regional-pour net's pieces stand after the negotiation, judged as the
        refill will lay the pour: its region minus every other net's keep-out, opened by
        the fill's minimum width, then joined to the net's own pads and tracks.

        Returns (pieces that do not reach the main body, main body's fill as bool[H, W]),
        or None when the net has no regional pour on a routed layer to judge."""
        m = self.m
        L, H, W = self.L, self.H, self.W
        lid = {n_: k for k, n_ in enumerate(m.route_layers)}
        pl = m.pours.get(net.name) or []
        if not pl or any(L_ not in lid for L_, _ in pl):
            return None                 # a plane layer the router does not route: not judged
        reg = m.region_net == net.id     # [L, H, W]
        if not reg.any():
            return None
        ks, ii, jj = np.nonzero(reg)
        i0, i1 = max(int(ii.min()) - 2, 0), min(int(ii.max()) + 3, H)
        j0, j1 = max(int(jj.min()) - 2, 0), min(int(jj.max()) + 3, W)
        sl = (slice(None), slice(i0, i1), slice(j0, j1))
        from scipy.ndimage import binary_opening, label
        fd = np.where(m.n1[sl] == net.id, m.d2[sl], m.d1[sl])
        self._unmark(net)
        other = self.occ_t.reshape(L, H, W)[sl] > 0
        self._mark(net)
        # the zone's own clearance and width (model._zone_rules), never less than the rules
        zc, zt = getattr(m, "zone_rule", {}).get(net.name, (0.0, 0.0))
        zc, zt = max(zc, m.clear), max(zt, self.FILL_MIN_W)
        # other nets' keep-out was stamped for a track beside them; the fill stands off
        # further, by the difference
        extra = zc - (self.wref / 2.0 + m.clear + m.margin)
        if extra > m.pitch / 2.0:
            from scipy.ndimage import distance_transform_edt
            other = np.stack([distance_transform_edt(~other[k]) * m.pitch < extra
                              if other[k].any() else other[k] for k in range(L)])
        fill = reg[sl] & (fd >= zc) & ~other
        fill &= (m.edge[i0:i1, j0:j1] >= m.edge_clear)[None]
        rr = max(1, int(round(zt / 2.0 / m.pitch)))
        yy, xx = np.mgrid[-rr:rr + 1, -rr:rr + 1]
        disk = (yy * yy + xx * xx) <= rr * rr
        h, w = i1 - i0, j1 - j0
        labs, base = np.zeros((L, h, w), np.int64), 0
        for k in range(L):
            if fill[k].any():
                f_ = binary_opening(fill[k], structure=disk)
                lk, nk = label(f_, structure=np.ones((3, 3), bool))
                labs[k] = np.where(lk > 0, lk + base, 0)
                base += nk
        # union-find over: fill components 1..base, pieces, paths
        items = [p for p in net.pieces] + [p for p in net.paths]
        npc = len(net.pieces)
        up = list(range(base + 1 + len(items)))

        def find(a):
            while up[a] != a:
                up[a] = up[up[a]]
                a = up[a]
            return a

        def union(a, b):
            up[find(a)] = find(b)

        def comps(cells, via_all):
            k = cells // (H * W)
            r = cells % (H * W)
            ci, cj = r // W - i0, r % W - j0
            ok = (ci >= 0) & (ci < h) & (cj >= 0) & (cj < w)
            k, ci, cj = k[ok], ci[ok], cj[ok]
            got = set(labs[k, ci, cj].tolist())
            if via_all is not None:              # a via pierces every pour layer
                vi = via_all[ok]
                if vi.any():
                    for kk in range(L):
                        got |= set(labs[kk, ci[vi], cj[vi]].tolist())
            got.discard(0)
            return got

        for q, cells in enumerate(items):
            node = base + 1 + q
            if q < npc:
                # a land touches the fill only where it is copper on that layer; pieces[0]
                # is everything the planes reach, so it is judged per fill component only
                if q == 0:
                    continue
                for c in comps(cells, None):
                    union(node, c)
            else:
                k = cells // (H * W)
                via = np.zeros(cells.size, bool)
                ch = np.nonzero(k[1:] != k[:-1])[0]
                via[ch] = True
                via[ch + 1] = True
                for c in comps(cells, via):
                    union(node, c)
        # tracks join the pieces and each other where they share cells
        cs = [set(c.tolist()) for c in items]
        # a track ending in pieces[0] (a via or land the planes reach) is joined to the
        # fill there, on whatever layer that copper meets it
        if npc and net.pieces[0].size:
            for q in range(npc, len(items)):
                sh = np.array(sorted(cs[q] & cs[0]), np.int64)
                if sh.size:
                    for c in comps(sh, np.ones(sh.size, bool)):
                        union(base + 1 + q, c)
        for a in range(1, len(items)):
            for b in range(a + 1, len(items)):
                if a < npc and b < npc:
                    continue
                if not cs[a].isdisjoint(cs[b]):
                    union(base + 1 + a, base + 1 + b)
        # pieces[0]: each fill component it stands on is planed (that is what it is)
        p0c = comps(net.pieces[0], None) if npc and net.pieces[0].size else set()
        roots = {}
        for q in range(1, npc):
            roots.setdefault(find(base + 1 + q), []).append(q)
        for c in p0c:
            roots.setdefault(find(c), [])
        if not roots:
            return [], None
        score = {r_: len(qs) + 10 * sum(find(c) == r_ for c in p0c) for r_, qs in roots.items()}
        main = max(score, key=score.get)
        bad = [q for r_, qs in roots.items() if r_ != main for q in qs]
        mlab = [c for c in range(1, base + 1) if find(c) == main]
        mx = np.zeros((H, W), bool)
        if mlab:
            mx[i0:i1, j0:j1] = np.isin(labs, mlab).any(axis=0)
        return bad, mx

    def _pour_islands(self):
        """⚠ A VIA INTO A REGIONAL POUR IS ONLY A JOIN IF THE REFILL REACHES IT (optical
        +3V3D under U6, 2026-11-09: other nets may cross the region -- priced, not banned --
        and on 16 of 19 nudged placements one piece's join via landed on a fill island the
        crossings had cut off, so close_last closed it the long way round, 13.5 mm across
        a 1.7 mm gap, quality A23). After the negotiation each such net is judged as the
        refill will lay it; a piece off the main body is re-joined to the main body only,
        everything else re-negotiating round it, and kept only if no more nets end open."""
        lock = {n for n in self.nets if n.group is not None}
        for net in self.nets:
            if not net.plane or net.failed:
                continue
            # ⚠ ONE PIECE AT A TIME (optical +3V3D, 2026-11-09: three pieces were cut off;
            # the one at 118.8,150.3 could only re-join through ULPI_CK/STP, a locked group,
            # and re-joining all three together put all three back). Each cut-off piece is
            # re-joined on its own, the others held, and each success kept.
            tried = set()

            def _at(q):
                r_ = net.pieces[q] % (self.H * self.W)
                return "(%.1f, %.1f)" % (float(self.m.cx[int(np.median(r_ % self.W))]),
                                         float(self.m.cy[int(np.median(r_ // self.W))]))
            for attempt in range(12):
                got = self._islands(net)
                if got is None:
                    break
                bad, mx = got
                if not bad or mx is None or not mx.any():
                    break
                if not tried:
                    self.log("  %s: %d piece(s) join the pour on an island the crossings cut off,"
                             " at %s -- re-joining each to the main body"
                             % (net.name, len(bad), ", ".join(_at(q) for q in bad[:4])))
                todo_q = [q for q in bad if q not in tried]
                if not todo_q:
                    break
                q1 = todo_q[0]
                tried.add(q1)
                saved = {n: (n.paths, n.necks, n.failed) for n in self.nets}
                fail0 = sum(n.failed for n in self.nets)
                net.main_xy = mx
                # ⚠ ONLY THE CUT-OFF PIECES ARE RE-JOINED (optical +3V3D, 2026-11-09: the
                # piece at 77.5,163.9 re-joined cleanly, but re-routing the whole net moved a
                # good join under U6 onto ULPI_D5/D6 -- a locked matched group -- and the
                # re-join was put back on every run). The good pieces keep their joins.
                if len(net.paths) == len(net.pieces) - 1:
                    net.keep_paths = {q: (net.paths[q - 1], net.necks[q - 1] if q - 1 < len(net.necks) else None)
                                      for q in range(1, len(net.pieces)) if q != q1}
                try:
                    left, _ = self._rounds([net], getattr(self, "_pf_last", 1.0), 12, 600, locked=lock)
                finally:
                    net.main_xy = None
                    net.keep_paths = None
                fail1 = sum(n.failed for n in self.nets) + sum(not n.failed for n in left)
                again = self._islands(net) if not net.failed else None
                nbad = len(again[0]) if again else len(bad) + 1
                if fail1 <= fail0 and not net.failed and nbad < len(bad):
                    self._rip(left)
                    self.log("  %s: piece at %s re-joined" % (net.name, _at(q1)))
                    continue
                self.log("  %s: re-joining the piece at %s left %d net(s) open (was %d), %d island"
                         " piece(s) -- put back" % (net.name, _at(q1), fail1, fail0, nbad))
                for n in self.nets:
                    self._unmark(n)
                for n in self.nets:
                    n.paths, n.necks, n.failed = saved[n]
                    self._mark(n)

    def _pair_try(self, pf, first, second, relax, layers, offrun_mult, refine, via_mult=1.0):
        """Lay a pair afresh (everything else held): first, then second, then (refine)
        first again against second. (shared cells, pair faults), or None if a rail fails."""
        for x in (first, second):
            self._unmark(x)
            x.paths, x.necks, x.failed = [], [], False
            x.relaxed, x.force_layers = relax, layers
        old = self.OFFRUN_COST
        self.OFFRUN_COST = old * offrun_mult
        vold = {x: x.via_mult for x in (first, second)}
        for x in (first, second):
            x.via_mult = vold[x] * via_mult
        self._pair_wall = self.PAIR_WALL
        try:
            for x in (first, second) + ((first,) if refine else ()):
                self._unmark(x)
                x.relaxed = relax
                p = self._route_net(x, pf)
                if p is None:
                    x.paths, x.necks, x.failed = [], [], True
                    return None
                x.paths, x.failed = p, False
                self._mark(x)
        finally:
            self._pair_wall = False
            self.OFFRUN_COST = old
            for x in (first, second):
                x.via_mult = vold[x]
        sh = sum(int(c.size) for x in (first, second) for c in self._conflicts(x))
        # ⚠ THE RAILS' OWN OVERLAP IS COUNTED APART (optical, 2026-11-09): "fewest shared
        # cells" lumped the rails sharing with EACH OTHER in with sharing other nets', and
        # _displace -- which holds the pair and moves the rest -- can never undo the first:
        # USB_DP and USB_DM were written 0.33 mm into each other, a post-route pass took
        # DP up, close_last closed it the long way and the skew failed. An attempt whose
        # rails overlap is no attempt at all.
        self._unmark(second)
        alone = sum(int(c.size) for c in self._conflicts(first))
        self._mark(second)
        mutual = sum(int(c.size) for c in self._conflicts(first)) - alone
        if mutual > 0:
            return None
        return sh, self.pair_faults(first)

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
        # (the fill does not move between rounds: computed once per net and window)
        ck = (net.name, win)
        cache = self.__dict__.setdefault("_under_cache", {})
        if ck not in cache:
            under = np.zeros(site.shape, bool)
            for pts in getattr(net, "pour_polys", ()):
                under |= _in_poly(X, Y, pts)
            # ...and only where the WHOLE via pad sits in that copper: a site at a fill's
            # edge or across one of its slivers is no join at all
            from scipy.ndimage import distance_transform_edt
            under &= distance_transform_edt(under) * self.m.pitch >= self.m.via_d / 2.0 + self.FILL_MARGIN
            cache[ck] = under
        under = cache[ck].copy()
        # after an island check (_pour_islands): only the fill the net's other copper
        # really reaches is a join; an island is a via into nothing
        mx = getattr(net, "main_xy", None)
        if mx is not None:
            under &= mx[i0:i1, j0:j1]
        site = (site & under).ravel()
        tgt0 = np.zeros(n, np.bool_)
        p0 = pieces[0]
        if mx is not None and p0.size:
            r0_ = p0 % (h * w)
            p0 = p0[mx[i0:i1, j0:j1].ravel()[r0_]]
        tgt0[p0] = True
        vs = np.tile(site, L) & np.isfinite(cellf)
        paths = []
        cell3 = cellf.reshape(L, h, w)
        vs3 = vs.reshape(L, h, w)
        tg3 = tgt0.reshape(L, h, w)
        pitch = self.m.pitch
        kp = getattr(net, "keep_paths", None) or {}
        for q in range(1, len(pieces)):
            if q in kp:                                 # a good piece's join, kept (_pour_islands)
                fp_, nk_ = kp[q]
                k_, r_ = fp_ // (H * W), fp_ % (H * W)
                ii_, jj_ = r_ // W - i0, r_ % W - j0
                if ((ii_ >= 0) & (ii_ < h) & (jj_ >= 0) & (jj_ < w)).all():
                    lp_ = (k_ * h + ii_) * w + jj_
                    self._claim_vias(lp_, vcell, h, w)   # its vias keep the re-join's off
                    tgt0[lp_] = True
                    self._necks.append(nk_ if nk_ is not None else np.zeros(fp_.size, bool))
                    paths.append(fp_)
                    continue
            pk = pieces[q] % (h * w)
            pkk = pieces[q] // (h * w)
            pi_, pj_ = pk // w, pk % w
            # ⚠ LOOK BESIDE THE PAD FIRST, as an engineer drops a plane via (optical
            # +3V3D, 2026-11-09): the heuristic aims at the piece itself, so a join searched
            # in the whole-board window with no site near flooded it like Dijkstra -- 5-6 M
            # states for a 6 mm join, the dearest searches of a round. Small boxes round the
            # piece first, the whole window only if they hold no way in.
            path = None
            for marg in self.PLANE_JOIN_MM + (None,):
                if marg is None:
                    a0, a1, b0, b1 = 0, h, 0, w
                else:
                    mc = int(math.ceil(marg / pitch))
                    a0, a1 = max(0, int(pi_.min()) - mc), min(h, int(pi_.max()) + mc + 1)
                    b0, b1 = max(0, int(pj_.min()) - mc), min(w, int(pj_.max()) + mc + 1)
                    if (a0, a1, b0, b1) == (0, h, 0, w):
                        continue
                hs, ws = a1 - a0, b1 - b0
                # ⚠ a via site an earlier piece's via has claimed is no target (optical
                # +3V3D, 2026-11-09: the sites were fixed before the loop, _claim_vias
                # closed them in vcell only, and two joins dropped vias 0.25 mm apart --
                # drills overlapping by 0.05 mm)
                free = np.isfinite(vcell.reshape(h, w)[a0:a1, b0:b1])[None]
                tg = np.ascontiguousarray(tg3[:, a0:a1, b0:b1] | (vs3[:, a0:a1, b0:b1] & free))
                sidx = (pkk * hs + (pi_ - a0)) * ws + (pj_ - b0)
                tg = tg.ravel()
                tg[sidx] = False
                if not tg.any():
                    if marg is None:
                        return None
                    continue
                src = np.zeros(L * hs * ws, np.bool_)
                src[sidx] = True
                cs = np.ascontiguousarray(cell3[:, a0:a1, b0:b1]).ravel()
                vcs = np.ascontiguousarray(vcell.reshape(h, w)[a0:a1, b0:b1]).ravel()
                tb = np.array([int(pi_.min()) - a0, int(pi_.max()) - a0,
                               int(pj_.min()) - b0, int(pj_.max()) - b0], np.int64)
                p = self._astar(cs, vcs, src, tg, L, hs, ws, tb, self.dir_cost)
                if p.size:
                    kk = p // (hs * ws)
                    rr = p % (hs * ws)
                    path = (kk * h + (rr // ws + a0)) * w + (rr % ws + b0)
                    break
            if path is None:
                return None
            # ⚠ A JOIN THAT ARRIVES ON THE POUR'S OWN LAYER NEEDS NO VIA (optical +3V3D,
            # 2026-11-09: the regional pour is on B.Cu, a join's track came in on B.Cu, and
            # the layer change always added here dropped a via touching B.Cu only -- the
            # tidy pass removed two such "dangling" vias every run). The track ends in the
            # pour and the refill takes it; only a join on another layer changes layer.
            pour_k = {k_ for k_, n_ in enumerate(self.m.route_layers)
                      if any(L_ == n_ for L_, _ in self.m.pours.get(net.name, ()))}
            if not tgt0[path[0]] and (path[0] // (h * w)) not in pour_k:
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
        self._premerge()
        self._neg = (pf_mul, hf)
        if self.USE_GLOBAL and os.environ.get("OWNROUTE_GLOBAL", "1") != "0":
            from .globalroute import GlobalRouter
            self._gr = GlobalRouter(self, log=self.log).run()
            self._gr.report()
        todo, pf = self._rounds(list(self.nets), pf0, iters, budget_s)
        self._pf_last = pf
        todo = self._priority_repair(todo, pf)
        self._rip(todo)
        if os.environ.get("OWNROUTE_SNAPSHOT"):        # pair-finish development: replay from here
            import pickle
            with open(os.environ["OWNROUTE_SNAPSHOT"], "wb") as fh:
                pickle.dump({"pf": pf, "nets": {n.name: (n.paths, n.necks, n.failed, n.relaxed)
                                                for n in self.nets}}, fh)
        self._finish_pairs()
        self._pour_islands()
        return [n for n in self.nets if n.failed]

    PRIORITY_REPAIR = True
    PRIO_MAX = 8                     # stuck nets a repair takes on; more is a placement problem

    def _sharers(self, grp):
        """The other nets whose keep-out covers a cell of grp's paths."""
        bad = [c for n in grp for c in self._conflicts(n)]
        if not bad:
            return []
        bad = np.unique(np.concatenate(bad))
        out = []
        for o in self.nets:
            if o in grp or not o.n_t:
                continue
            if np.isin(bad, o.rec_t[:o.n_t], assume_unique=False).any():
                out.append(o)
        return out

    def _nbad(self):
        return sum(1 for n in self.nets if n.failed or any(c.size for c in self._conflicts(n)))

    def _priority_repair(self, todo, pf):
        """⚠ A STUCK NET IS ROUTED FIRST, THEN WHAT IT SHARED WITH (optical USB_DP/DM,
        2026-11-09). Ten resistors moved 20 mm away from the USB pair and the negotiation
        ended with D+/D- sharing space with ULPI_D0 and VBUS for good: ripped out, the pair
        open on a placement every neighbour of which routes. PathFinder prices everyone at
        once; an engineer routes the critical net first and pushes the rest aside. So: for
        each net still sharing when negotiation stops, lift it (with its pair partner) and
        the nets it shares with, route it first, then route them round it. Kept only if the
        board has fewer nets sharing or open than before; otherwise put back."""
        stuck = [n for n in todo if not n.failed]
        if not self.PRIORITY_REPAIR or not stuck or len(stuck) > self.PRIO_MAX:
            return todo
        seen = set()
        for net in stuck:
            if net in seen or net.failed or not any(c.size for c in self._conflicts(net)):
                continue
            grp = [net] + [o for o in (net.partner,) + tuple(x for x in self.nets if x.partner is net)
                           if o is not None and o is not net]
            seen.update(grp)
            nb = [o for o in self._sharers(grp) if o not in grp]
            lift = grp + nb
            before = self._nbad()
            save = {n: (n.paths, n.necks, n.failed) for n in lift}
            # ⚠ ORDER IS THE DECISION (v109: D+ and D- each wanted the one via site beside
            # J1's lands; whichever went first got it, the other had nowhere to go). Each
            # order is tried -- the stuck net first, its partner first, the others first --
            # and the best kept.
            orders = [grp + nb, grp[::-1] + nb, nb + grp, nb + grp[::-1]]
            best, best_state = before, None
            for order in orders:
                if len(set(map(id, order))) != len(order):
                    continue
                for n in lift:
                    self._unmark(n)
                for n in order:
                    paths = self._route_net(n, pf)
                    n.failed = paths is None
                    n.paths = paths or []
                    if not paths:
                        n.necks = []
                    self._mark(n)
                after = self._nbad()
                if after < best:
                    best, best_state = after, ([n.name for n in order],
                                               {n: (n.paths, n.necks, n.failed) for n in lift})
                if after == 0:
                    break
            for n in lift:
                self._unmark(n)
            keep = best_state[1] if best_state else save
            for n, (p, k, f) in keep.items():
                n.paths, n.necks, n.failed = p, k, f
                self._mark(n)
            if best_state:
                self.log("  priority repair, order %s: %d net(s) sharing or open, was %d"
                         % (" > ".join(best_state[0]), best, before))
        return [n for n in self.nets if n.failed or any(c.size for c in self._conflicts(n))]

    def _rip(self, todo):
        """anything still sharing comes out: a legal board with a net open beats a short"""
        for net in todo:
            if not net.failed:
                self.log("  %s still shares space%s: ripped out" % (net.name, self._where(net)))
            self._unmark(net)
            net.paths = []
            net.necks = []
            net.failed = True

    def _rounds(self, todo, pf, iters, budget_s, locked=()):
        """PathFinder rounds over `todo` until nobody shares; `locked` nets hold their copper
        (never re-routed). Returns (nets still sharing or failed, final pf)."""
        pf_mul, hf = getattr(self, "_neg", (1.6, 0.4))
        t0 = time.time()
        best, since = None, 0
        self._stalled = False
        kept0 = {n: n.keep_paths for n in self.nets if n.plane}
        for it in range(1, iters + 1):
            for net in todo:
                if net in locked:
                    continue
                # ⚠ A PLANE JOIN AIMS WHERE THE POUR WILL BE, EVERY ROUND (optical +3V3D by
                # U6, 2026-11-09): join targets were the pour's polygon, so a join ended in the
                # region's corner where a B.Cu track along its edge had cut the fill off; the
                # refill drops that sliver, and the island pass could not re-join the piece
                # past the locked ULPI group (close_last closed it the long way). The main
                # body's fill is judged against the copper as it stands, and joins aim at it.
                mx0 = getattr(net, "main_xy", None)
                if self.PLANE_MAIN and net.plane and mx0 is None:
                    got = self._islands(net)
                    if got is not None and got[1] is not None and got[1].any():
                        net.main_xy = got[1]
                self._unmark(net)
                paths = self._route_net(net, pf)
                net.main_xy = mx0
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
                if net in locked:
                    continue
                if net.failed:
                    todo.append(net)
                    continue
                shared = False
                bad_q = set()
                for q, path in enumerate(net.paths):
                    c = path[self.occ_t[path] >= 2]
                    if c.size:
                        self.hist[c] += hf
                        shared = True
                        bad_q.add(q)
                    k = path // (H * W)
                    via = np.nonzero(k[1:] != k[:-1])[0]
                    if via.size:
                        r = path[via] % (H * W)
                        rv = r[self.occ_v[r] >= 2]
                        if rv.size:
                            self.hist_v[rv] += hf
                            shared = True
                            bad_q.add(q)
                # ⚠ A PIECE CUT OFF THE POUR IS AS UNFINISHED AS ONE SHARING SPACE (optical
                # +3V3D by U6, 2026-11-09): PLANE_MAIN aims a join at the main body when the net
                # is routed, but a net routed later in the round can still cut its target off;
                # the plane net was not sharing, so never re-routed, and the island showed only
                # at the end, where the island pass could not undo it past the locked ULPI
                # group. Cut-off pieces count as shared and are re-joined next round.
                if self.PLANE_MAIN and net.plane and not net.fixed and len(net.paths) == len(net.pieces) - 1:
                    got = self._islands(net)
                    if got is not None and got[0]:
                        shared = True
                        bad_q.update(q - 1 for q in got[0])
                # ⚠ A PLANE NET RE-JOINS ONLY THE PIECES THAT SHARE (optical +3V3D,
                # 2026-11-09: ~55 pieces, each its own join to the pour, and one or two
                # sharing space re-searched all of them every round -- 220 searches, a third
                # of the negotiation). An engineer moves the via that is in the way, not
                # every via on the rail; the others keep their joins as laid.
                if (shared and self.PLANE_KEEP and net.plane and not net.fixed
                        and len(net.paths) == len(net.pieces) - 1):
                    net.keep_paths = {q + 1: (net.paths[q], net.necks[q] if q < len(net.necks) else None)
                                      for q in range(len(net.paths)) if q not in bad_q}
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
            self._stalled = since >= self.STALL_ROUNDS
            if time.time() - t0 > budget_s:
                self.log("  out of time")
                break
            pf *= pf_mul
        self._stalled = False
        for n, kp in kept0.items():
            n.keep_paths = kp
        return todo, pf
