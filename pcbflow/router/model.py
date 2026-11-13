"""The board as the router sees it: a grid per copper layer, the fixed copper reduced to
distance fields, and the nets still to route with their connected pieces.

See ../ROUTER.md for why the fields are (d1, n1, d2): one pass over the fixed copper answers
"how far is the nearest copper that is NOT mine" for every net at once."""
from __future__ import annotations

import json
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import repair_search as RS  # noqa: E402  (the battle-tested parsers: pads, tracks, edges)

FAR = np.float32(1e3)
SIGNAL_W = 0.2           # a signal's track width (wide nets neck to it at their lands)
POWER_W_MAX = 1.0        # the widest a power path is drawn (wider: pour it)
DROP_SHARE = 0.6         # of a path's drop budget the track may spend (detours, vias, joints)
DETOUR = 1.6             # routed length over Manhattan, for the drop estimate (optical V24_IN ran 2.0x)
RING_PADS = 3            # parts with this many pads or fewer get a thermal ring
RING_MM = 0.9            # a poured land's thermal room, from its copper edge
HOLE_PAD = 0.45          # a pad's hole to any other hole, edge to edge (quality.FAB hole_hole_pad)
SUPPLY = ("+", "GND", "VCC", "VDD")
GROUND_RE = re.compile(r"^(GND|VSS|[A-Z0-9]+_GND|[AD]GND|GND[A-Z0-9_]*)$")   # as quality.GROUND


def _copper_layers(txt):
    blk = re.search(r"\n\t\(layers\n(.*?)\n\t\)", txt, re.S)
    names = re.findall(r'\(\d+ "([^"]+\.Cu)" (?:signal|power|mixed|jumper)', blk.group(1)) if blk else []
    order = {"F.Cu": -1, "B.Cu": 99}
    return sorted(names, key=lambda n: order.get(n, int(re.sub(r"\D", "", n) or 50)))


class Model:
    def __init__(self, stem, pitch=0.05, margin=0.03, default_w=None):
        self.stem = stem
        txt = open(stem + ".kicad_pcb", encoding="utf-8").read()
        self.txt = txt
        notes = json.load(open(stem + ".board.json", encoding="utf-8"))
        self.notes = notes
        pro = json.load(open(stem + ".kicad_pro", encoding="utf-8"))
        cls = {c["name"]: c for c in pro["net_settings"]["classes"]}
        self.clear = float(cls.get("Default", {}).get("clearance", RS.RULE_CLEAR))
        self.via_d = float(cls.get("Default", {}).get("via_diameter", RS.VIA_D))
        self.via_drill = float(cls.get("Default", {}).get("via_drill", RS.VIA_DRILL))
        self.edge_clear = RS._edge_clearance(stem)
        rules = pro.get("board", {}).get("design_settings", {}).get("rules", {})
        self.hole_clear = max(float(rules.get("min_hole_clearance", 0.25)), self.clear)
        self.hole_to_hole = float(rules.get("min_hole_to_hole", 0.25))
        self.margin = margin
        self.pitch = pitch
        self.layers = _copper_layers(txt)
        plane = set(notes.get("plane_layers", ()))
        self.route_layers = [L for L in self.layers if L not in plane]
        self.L = len(self.route_layers)

        self.pads = RS._pads(txt)
        _attach_custom(txt, self.pads)
        _attach_drills(txt, self.pads)
        self.segs = RS._segments(txt)
        self.vias = RS._vias(txt)
        self.edges = RS._edges(txt)
        self.keepouts = _keepouts(txt)
        self.pours = _pours(txt)
        self.whole = _pours(txt, named="whole")
        self.zone_rule = _zone_rules(txt)
        # where each pour's copper actually IS (its fill), net by net; the outline where
        # a pour has no fill yet. Plane joins aim here (negotiate build_nets/_to_plane).
        fills = _fills(txt)
        self.fills = {n: fills.get(n) or pl for n, pl in self.pours.items()}

        # ---- nets
        names = sorted({p["net"] for p in self.pads if p["net"]} |
                       {s["net"] for s in self.segs if s["net"]})
        self.net_id = {n: i + 1 for i, n in enumerate(names)}
        self.net_name = {i: n for n, i in self.net_id.items()}
        # ⚠ WIDTH AS AN ENGINEER SETS IT: signals thin, current wide. A signal carries no
        # current worth the room, so it runs at SIGNAL_W; the class's 0.25 everywhere
        # (freerouting's habit) left optical 4 nets open and output_panel's crystal pair
        # open (2026-11-08). A net on a declared power path is sized the way quality judges
        # it (power_width): its IPC-2221 heating width, and the width that keeps the path's
        # drop inside its budget over the distance it has to go (optical V24_IN at 0.2
        # dropped 58 mV against 50). A flat amps formula widened 0.1 A rails to 0.3 and
        # cost output_panel DAC_OUT_R. net_widths, where the board states one, wins.
        if default_w is None:
            default_w = SIGNAL_W
        self.default_w = default_w
        q = notes.get("quality", {}) or {}
        at = {p["name"]: (p["gx"], p["gy"]) for p in self.pads if p.get("name")}
        need = {}
        for pp in q.get("power_paths", ()) or ():
            w = power_width(pp, q, at)
            need[pp["net"]] = max(need.get(pp["net"], 0.0), w)
        widths = notes.get("net_widths", {}) or {}
        self.width = {}
        for n in names:
            w = max(default_w, min(POWER_W_MAX, need.get(n, 0.0)))
            self.width[n] = float(widths.get(n, w))

        # ---- grid over the outline
        xs = [e[0] for e in self.edges] + [e[2] for e in self.edges]
        ys = [e[1] for e in self.edges] + [e[3] for e in self.edges]
        self.x0, self.y0 = min(xs), min(ys)
        self.nx = int(math.ceil((max(xs) - self.x0) / pitch)) + 1
        self.ny = int(math.ceil((max(ys) - self.y0) / pitch)) + 1
        self.cx = (self.x0 + np.arange(self.nx) * pitch).astype(np.float64)
        self.cy = (self.y0 + np.arange(self.ny) * pitch).astype(np.float64)

        self._fields()
        self._edge_field()
        self._ref_voids()

    # ------------------------------------------------------------------ geometry helpers
    def xy(self, i, j):
        return self.x0 + j * self.pitch, self.y0 + i * self.pitch

    def ij(self, x, y):
        return int(round((y - self.y0) / self.pitch)), int(round((x - self.x0) / self.pitch))

    def _window(self, x0, y0, x1, y1, reach):
        j0 = max(0, int(math.floor((x0 - reach - self.x0) / self.pitch)))
        j1 = min(self.nx, int(math.ceil((x1 + reach - self.x0) / self.pitch)) + 1)
        i0 = max(0, int(math.floor((y0 - reach - self.y0) / self.pitch)))
        i1 = min(self.ny, int(math.ceil((y1 + reach - self.y0) / self.pitch)) + 1)
        return i0, i1, j0, j1

    # ------------------------------------------------------------------ fixed copper
    def _fields(self):
        """Per routing layer: d1 = distance to the nearest fixed copper, n1 = its net,
        d2 = distance to the nearest fixed copper of a net other than n1. Copper with no
        net gets id -1, foreign to everything."""
        L, ny, nx = self.L, self.ny, self.nx
        self.d1 = np.full((L, ny, nx), FAR, np.float32)
        self.n1 = np.zeros((L, ny, nx), np.int32)
        self.d2 = np.full((L, ny, nx), FAR, np.float32)
        reach = 0.5 + max(self.width.values(), default=0.2) / 2 + self.clear + self.margin + self.via_d
        self.reach = reach
        lid = {n: k for k, n in enumerate(self.route_layers)}

        def put(k, win, d, net):
            i0, i1, j0, j1 = win
            D1 = self.d1[k, i0:i1, j0:j1]
            N1 = self.n1[k, i0:i1, j0:j1]
            D2 = self.d2[k, i0:i1, j0:j1]
            same = N1 == net
            closer = (~same) & (d < D1)
            farther = (~same) & ~closer
            # nearest is mine already: just get nearer
            np.minimum(D1, np.where(same, d, FAR), out=D1)
            # a new nearest of another net: the old nearest becomes the second
            D2[closer] = D1[closer]
            D1[closer] = d[closer]
            N1[closer] = net
            # not nearer: may still be the nearest foreign one
            np.minimum(D2, np.where(farther, d, FAR), out=D2)

        def grid(win):
            i0, i1, j0, j1 = win
            return np.meshgrid(self.cx[j0:j1], self.cy[i0:i1])

        # ⚠ NO VIA IN ANY LAND, THE NET'S OWN INCLUDED (first own-router finish, 2026-11-08).
        # The router changed layer right inside small SMD lands; post_route then took up 67
        # such vias as paste-wicking via-in-pad (PCB_QUALITY M29 / A14) and left 67 nets open.
        # An engineer drops the via beside the land, so this is a distance to every land.
        pad_near = np.full((ny, nx), FAR, np.float32)
        hole_extra = self.hole_clear - self.clear
        for p in self.pads:
            net = self.net_id.get(p["net"], -1)
            r = pad_reach(p)
            win = self._window(p["gx"] - r, p["gy"] - r, p["gx"] + r, p["gy"] + r, reach)
            X, Y = grid(win)
            d = pad_dist(p, X, Y).astype(np.float32)
            i0, i1, j0, j1 = win
            np.minimum(pad_near[i0:i1, j0:j1], d, out=pad_near[i0:i1, j0:j1])
            for L_ in self.route_layers:
                if p["cu"] is None or L_ in p["cu"]:
                    put(lid[L_], win, d, net)
            # ⚠ A DRILL HAS ITS OWN, LARGER RULE (min_hole_clearance 0.25 against 0.127):
            # J1_VBUS on In2.Cu ran inside it at J1's unplated holes. The hole goes in as
            # copper pulled in by the difference, so the one clearance test covers both; an
            # unplated hole belongs to no net and keeps everything off.
            if p.get("drill"):
                hx, hy, hr = p["drill"]
                d = (_d_pts_seg(X, Y, p["gx"] - hx, p["gy"] - hy, p["gx"] + hx, p["gy"] + hy)
                     - hr - hole_extra).astype(np.float32)
                for k in range(L):
                    put(k, win, d, -1 if p.get("npth") else net)
        for s in self.segs:
            if s["layer"] not in lid:
                continue
            net = self.net_id.get(s["net"], -1)
            win = self._window(min(s["x1"], s["x2"]), min(s["y1"], s["y2"]),
                               max(s["x1"], s["x2"]), max(s["y1"], s["y2"]), reach + s["half"])
            X, Y = grid(win)
            d = (_d_pts_seg(X, Y, s["x1"], s["y1"], s["x2"], s["y2"]) - s["half"]).astype(np.float32)
            put(lid[s["layer"]], win, d, net)
        for v in self.vias:
            net = self.net_id.get(v["net"], -1)
            win = self._window(v["x"], v["y"], v["x"], v["y"], reach + v["r"])
            X, Y = grid(win)
            d = (np.hypot(X - v["x"], Y - v["y"]) - v["r"]).astype(np.float32)
            for k in range(L):
                put(k, win, d, net)
        # ⚠ A REGIONAL POUR IS RESERVED ROOM, PRICED NOT BANNED (optical +3V3D under U6,
        # 2026-11-08). Crossed freely, the refill came back in islands and nine +3V3D joints
        # were open; banned outright, the area under U6 was walled off and seventeen nets
        # could not finish. So other nets may cross a pour that covers a region (not a
        # whole layer) on its layer, at REGION_COST times the price -- only where they must.
        # region_net[k] = the net a regional pour reserves each cell for (0 = none).
        self.region_net = np.zeros((L, ny, nx), np.int32)
        board_area = _area(_loops(self.edges)[0]) if self.edges else 0.0
        for net_name, polys in self.pours.items():
            nid = self.net_id.get(net_name, -1)
            for L_, pts in polys:
                if L_ not in lid or _area(pts) > 0.8 * board_area:
                    continue
                win = self._window(min(q[0] for q in pts), min(q[1] for q in pts),
                                   max(q[0] for q in pts), max(q[1] for q in pts), 0.0)
                X, Y = grid(win)
                i0, i1, j0, j1 = win
                sub = self.region_net[lid[L_], i0:i1, j0:j1]
                sub[_in_poly(X, Y, pts)] = nid
        # ⚠ A BAND IS CUT BY ONE CROSSING (output_board, 2026-11-13): VIN_BUS at 10 A as a
        # 7.2 mm In2 band 78 mm long, chargers to shunt, crossed by GND tracks at
        # REGION_COST, refilled in five islands and finished 78 mm open. A blob survives a
        # crossing; a band does not. A pour zone NAMED "whole" (opt-in: auto_pour `whole`)
        # costs other nets WHOLE_COST on its layer -- priced, not banned (a ban walled U6
        # off on optical), so a net crosses it only where no other layer will do.
        # whole_net[k] = the net a whole pour keeps each cell for (0 = none).
        self.whole_net = np.zeros((L, ny, nx), np.int32)
        for net_name, polys in self.whole.items():
            nid = self.net_id.get(net_name, -1)
            for L_, pts in polys:
                if L_ not in lid:
                    continue
                win = self._window(min(q[0] for q in pts), min(q[1] for q in pts),
                                   max(q[0] for q in pts), max(q[1] for q in pts), 0.0)
                X, Y = grid(win)
                i0, i1, j0, j1 = win
                sub = self.whole_net[lid[L_], i0:i1, j0:j1]
                sub[_in_poly(X, Y, pts)] = nid
        self.whole_any = bool(self.whole_net.any())
        # ⚠ A POURED LAND NEEDS ROOM TO BREATHE (optical R33.2 GND, 2026-11-08: a foreign
        # track hugging the land left the F.Cu GND pour too few thermal spokes, DRC
        # starved_thermal, and close_last would not run past it). Round every land whose net
        # pours its layer there, other nets pay RING_COST (negotiate) to pass within
        # RING_MM of the land's edge -- room the pour's spokes need -- so they go round
        # where they can and squeeze by only where they must.
        # ring_net[k] = the pour net whose land the cell rings (0 = none).
        # ⚠ SMALL PARTS ONLY (output_panel, 2026-11-08): ringing every GND pin of U3 priced
        # each neighbouring signal pin's escape 4x and left DAC_OUT_R open. An IC's pin
        # takes spokes from outside the package; a passive's land is the one a hugging
        # track starves (and the one that tombstones).
        npads = {}
        for p in self.pads:
            npads[p.get("fp")] = npads.get(p.get("fp"), 0) + 1
        self.ring_net = np.zeros((L, ny, nx), np.int32)
        for net_name, polys in self.pours.items():
            nid = self.net_id.get(net_name, -1)
            for p in self.pads:
                if p["net"] != net_name or npads.get(p.get("fp"), 99) > RING_PADS:
                    continue
                r = pad_reach(p) + RING_MM
                win = None
                for L_, pts in polys:
                    if L_ not in lid or not (p["cu"] is None or L_ in p["cu"]):
                        continue
                    if not _in_poly(np.array([p["gx"]]), np.array([p["gy"]]), pts)[0]:
                        continue
                    if win is None:
                        win = self._window(p["gx"] - r, p["gy"] - r, p["gx"] + r, p["gy"] + r, 0.0)
                        X, Y = grid(win)
                        d = pad_dist(p, X, Y)
                        ring = (d > 0) & (d < RING_MM)
                    i0, i1, j0, j1 = win
                    sub = self.ring_net[lid[L_], i0:i1, j0:j1]
                    sub[ring & (sub == 0)] = nid
        # keep-outs. A track ban is distance 0 to "copper" of no net inside the area, on its
        # layers. A via ban -- or a track ban on ANY copper layer, plane layers included,
        # since a via pierces them all -- is a 2-D mask of forbidden via centres.
        self.via_ban = np.zeros((ny, nx), bool)
        for z in self.keepouts:
            pts = z["pts"]
            # ⚠ THE AREA BANS THE COPPER'S EDGE, NOT ITS CENTRE: a via centred 0.28 mm off
            # a keep-out's corner still put its 0.6 mm pad inside it (RING_BUF_SEL at U1,
            # nudge RO_1, 2026-11-08). The track field is the true distance to the area
            # (0 inside), and the via ban grows by the via's radius.
            rv = self.via_d / 2.0 + self.margin
            win = self._window(min(q[0] for q in pts), min(q[1] for q in pts),
                               max(q[0] for q in pts), max(q[1] for q in pts), rv + 1.0)
            X, Y = grid(win)
            inside = _in_poly(X, Y, pts)
            edge = np.full(X.shape, FAR)
            for k in range(len(pts)):
                (xa, ya), (xb, yb) = pts[k], pts[(k + 1) % len(pts)]
                np.minimum(edge, _d_pts_seg(X, Y, xa, ya, xb, yb), out=edge)
            dist = np.where(inside, 0.0, edge)
            names = set()
            for L_ in z["layers"]:
                names |= set(self.layers) if L_ in ("*.Cu", "F&B.Cu") else {L_}
            if z["tracks"]:
                d = dist.astype(np.float32)
                for name in names:
                    if name in lid:
                        put(lid[name], win, d, -1)
            if z["vias"] or (z["tracks"] and names & set(self.layers)):
                i0, i1, j0, j1 = win
                self.via_ban[i0:i1, j0:j1] |= dist < rv
        self.via_ban |= pad_near < self.via_d / 2.0 + self.clear + self.margin
        # ⚠ AND NO NEW DRILL INSIDE AN OLD ONE'S HOLE-TO-HOLE, OF ANY NET: a layer change
        # beside a declared via of the SAME net drilled a second hole 0.0 mm from it
        # (HUB_DN4_DM at R52, 2026-11-08). At the net's own via the router changes layer
        # THROUGH that via instead (negotiate._route_in), and emit writes no new one.
        # ⚠ ...AND NONE NEAR A PAD'S HOLE, at the fab's pad-hole rule (quality.FAB
        # hole_hole_pad 0.45, a pad hole to ANY other hole): a via 0.183 mm from J1's shield
        # hole failed quality A12 (optical, 2026-11-08) -- the rules file's hole-to-hole
        # (0.25) is the via-to-via figure and the pad drills were never in this ban at all.
        for p in self.pads:
            if not p.get("drill"):
                continue
            hx, hy, hr = p["drill"]
            reach_h = hr + self.via_drill / 2.0 + HOLE_PAD + self.margin
            win = self._window(p["gx"] - abs(hx), p["gy"] - abs(hy),
                               p["gx"] + abs(hx), p["gy"] + abs(hy), reach_h + 0.1)
            X, Y = grid(win)
            i0, i1, j0, j1 = win
            self.via_ban[i0:i1, j0:j1] |= (_d_pts_seg(X, Y, p["gx"] - hx, p["gy"] - hy,
                                                      p["gx"] + hx, p["gy"] + hy) < reach_h)
        for v in self.vias:
            win = self._window(v["x"], v["y"], v["x"], v["y"], self.via_drill + self.hole_to_hole + 0.1)
            X, Y = grid(win)
            i0, i1, j0, j1 = win
            self.via_ban[i0:i1, j0:j1] |= (np.hypot(X - v["x"], Y - v["y"])
                                           < self.via_drill + self.hole_to_hole + self.margin)

    VOID_MIN_MM = 2.0      # a reference-plane void this wide or more is priced (a via's antipad is not)

    def _ref_voids(self):
        """ref_void[k, i, j]: on routing layer k, the ground plane a track there returns in
        is MISSING at (i, j) -- inside that plane's outline, outside its fill.

        ⚠ A SIGNAL OVER A SLOT RETURNS ROUND IT (pi_cap UI_ENC_A, 2026-11-09): the 40-pin
        socket's two rows of holes cut the In2 ground plane, and the router, knowing nothing
        of it, ran UI_ENC_A ALONG the cut for 11.77 mm where one crossing is 6; quality A15
        failed it against the 9.3 the row is signed for. The reference plane is read as A15
        reads it -- the nearest ground copper in the stack-up, other than the track's own
        layer -- from the fill layout left, and only voids VOID_MIN_MM across or wider
        count: an antipad never fails a 5 mm rule, and pricing every one would push
        tracks off every pin."""
        L, ny, nx = self.L, self.ny, self.nx
        self.ref_void = np.zeros((L, ny, nx), bool)
        order = {n: k for k, n in enumerate(self.layers)}
        gfill, gout = {}, {}
        for net, pl in self.fills.items():
            if GROUND_RE.match(net):
                for L_, pts in pl:
                    gfill.setdefault(L_, []).append(pts)
        for net, pl in self.pours.items():
            if GROUND_RE.match(net):
                for L_, pts in pl:
                    gout.setdefault(L_, []).append(pts)

        def raster(polys):
            m = np.zeros((ny, nx), bool)
            for pts in polys:
                P = np.asarray(pts, np.float64)
                win = self._window(P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max(), 0.0)
                i0, i1, j0, j1 = win
                if i1 <= i0 or j1 <= j0:
                    continue
                X, Y = np.meshgrid(self.cx[j0:j1], self.cy[i0:i1])
                m[i0:i1, j0:j1] ^= _in_poly(X, Y, pts)
            return m

        cov = {l: raster(p) for l, p in gfill.items() if l in order}
        out = {l: raster(p) for l, p in gout.items() if l in order}
        from scipy.ndimage import label, find_objects
        mn = int(round(self.VOID_MIN_MM / self.pitch))
        for k, name in enumerate(self.route_layers):
            dist = {l: abs(order[l] - order[name]) for l in cov if l != name}
            if not dist:
                continue
            near = min(dist.values())
            refs = [l for l in dist if dist[l] == near]
            covered = np.zeros((ny, nx), bool)
            within = np.zeros((ny, nx), bool)
            for l in refs:
                covered |= cov[l]
                within |= out.get(l, cov[l])
            void = within & ~covered
            lab, n = label(void)
            keep = np.zeros(n + 1, bool)
            for q, sl in enumerate(find_objects(lab), start=1):
                if sl is not None and max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) >= mn:
                    keep[q] = True
            self.ref_void[k] = keep[lab]

    EDGE_REACH = 10.0                # mm: the edge field is exact this far in, FAR beyond

    def _edge_field(self):
        """Distance to the outline, signed so that outside the board is negative."""
        X, Y = np.meshgrid(self.cx, self.cy)
        d = np.full((self.ny, self.nx), FAR, np.float64)
        # ⚠ EACH SEGMENT OVER ITS OWN WINDOW (optical, 2026-11-10): 2294 outline segments
        # (the slots and round cut-outs are drawn as many) each measured over the whole
        # grid was 9.5 s of an 82 s route. Every reader compares the field with a track's
        # or via's half width plus edge clearance -- a millimetre or two -- so beyond
        # EDGE_REACH it stays FAR (signed below), and within it each cell is exact: the
        # segment nearest it is within reach, so its window holds the cell.
        R = self.EDGE_REACH
        for e in self.edges:
            x1, y1, x2, y2 = e
            j0 = max(0, int(np.floor((min(x1, x2) - R - self.x0) / self.pitch)))
            j1 = min(self.nx, int(np.ceil((max(x1, x2) + R - self.x0) / self.pitch)) + 1)
            i0 = max(0, int(np.floor((min(y1, y2) - R - self.y0) / self.pitch)))
            i1 = min(self.ny, int(np.ceil((max(y1, y2) + R - self.y0) / self.pitch)) + 1)
            if i1 <= i0 or j1 <= j0:
                continue
            sub = d[i0:i1, j0:j1]
            np.minimum(sub, _d_pts_seg(X[i0:i1, j0:j1], Y[i0:i1, j0:j1], *e), out=sub)
        loops = _loops(self.edges)
        inside = _in_poly(X, Y, loops[0]) if loops else np.ones_like(d, bool)
        # every other closed loop (a round cut-out drawn on Edge.Cuts) is a hole in the board
        for hole in loops[1:]:
            inside &= ~_in_poly(X, Y, hole)
        self.edge = np.where(inside, d, -d).astype(np.float32)

    # ------------------------------------------------------------------ legality
    def free(self, net, w):
        """bool[L, ny, nx]: where net's centreline (width w) may stand on the fixed copper."""
        nid = self.net_id[net]
        need = w / 2.0 + self.clear + self.margin
        fd = np.where(self.n1 == nid, self.d2, self.d1)
        ok = fd >= need
        ok &= (self.edge >= w / 2.0 + self.edge_clear + self.margin)[None]
        return ok

    def via_free(self, net):
        """bool[ny, nx]: where a via of net may stand (clear on every routing layer)."""
        nid = self.net_id[net]
        need = self.via_d / 2.0 + self.clear + self.margin
        fd = np.where(self.n1 == nid, self.d2, self.d1)
        ok = np.all(fd >= need, axis=0)
        ok &= self.edge >= self.via_d / 2.0 + self.edge_clear + self.margin
        ok &= ~self.via_ban
        return ok



def _rail_volts(net):
    """quality._rail_volts (that module needs pcbnew): "+24V" 24, "+3V3A" 3.3, "VBUS" 5."""
    m = re.match(r"^\+?(\d+)V(\d*)", net)
    if m:
        return float("%s.%s" % (m.group(1), m.group(2) or "0"))
    return 5.0 if net.upper().startswith("VBUS") else None


def power_width(pp, q, at):
    """The track width one power_paths entry needs, judged as quality judges it.

    The larger of IPC-2221's heating width (outer layer, quality.temp_rise_c, copper_oz)
    and the width whose resistance over the path keeps the drop to DROP_SHARE of its
    budget (max_drop_mv on the path or board, else max_drop_pct of the rail's named
    volts, else 50 mV -- quality's rule). Length is Manhattan from the source to each
    load, times DETOUR. Outer copper is assumed: a power net the router puts inside runs
    on half the copper, and quality says so if that costs the budget."""
    amps = float(pp.get("amps", 0.0))
    if amps <= 0:
        return 0.0
    oz = float(q.get("copper_oz", 1.0))
    dt = float(q.get("temp_rise_c", 10.0))
    area_mil2 = (amps / (0.048 * dt ** 0.44)) ** (1.0 / 0.725)
    w = area_mil2 / (oz * 1.378) * 0.0254
    limit = pp.get("max_drop_mv", q.get("max_drop_mv"))
    if limit is None:
        volts = _rail_volts(pp["net"])
        limit = volts * 10.0 * float(q.get("max_drop_pct", 2.0)) if volts else 50.0
    src = at.get(pp.get("from"))
    dsts = pp["to"] if isinstance(pp["to"], (list, tuple)) else [pp["to"]]
    for d in dsts:
        if src is None or d not in at:
            continue
        L = (abs(at[d][0] - src[0]) + abs(at[d][1] - src[1])) * DETOUR
        r_max = DROP_SHARE * float(limit) / 1000.0 / amps            # ohm
        w = max(w, 1.72e-5 * L / (r_max * oz * 0.035))               # mm, as quality's
    return round(w, 2)

def pad_reach(p):
    """Radius round the pad's centre that holds all of its copper."""
    r = math.hypot(p["ihx"], p["ihy"]) + p["cr"]
    for cx, cy, cr in p.get("circles", ()):
        r = max(r, math.hypot(cx - p["gx"], cy - p["gy"]) + cr)
    for pts in p.get("polys", ()):
        r = max(r, max(math.hypot(x - p["gx"], y - p["gy"]) for x, y in pts))
    return r


def pad_dist(p, X, Y):
    """Distance from grid points to a pad's copper (<= 0 inside): the inset rectangle plus
    corner radius, and for a custom pad every primitive too."""
    dx, dy = X - p["gx"], Y - p["gy"]
    u = np.abs(dx * p["ca"] + dy * p["sa"]) - p["ihx"]
    v = np.abs(-dx * p["sa"] + dy * p["ca"]) - p["ihy"]
    d = np.hypot(np.maximum(u, 0), np.maximum(v, 0)) - p["cr"]
    for cx, cy, cr in p.get("circles", ()):
        np.minimum(d, np.hypot(X - cx, Y - cy) - cr, out=d)
    for pts in p.get("polys", ()):
        e = np.full(X.shape, FAR, np.float64)
        for a, b in zip(pts, pts[1:] + pts[:1]):
            np.minimum(e, _d_pts_seg(X, Y, a[0], a[1], b[0], b[1]), out=e)
        np.minimum(d, np.where(_in_poly(X, Y, pts), -e, e), out=d)
    return d


def _attach_custom(txt, pads):
    """⚠ A CUSTOM PAD IS ITS PRIMITIVES, NOT ITS ANCHOR (JP1 on output_panel, 2026-11-08). A
    solder jumper's outer lands are a 1.0 x 0.5 anchor plus two r 0.5 circles and a polygon;
    the parser saw the anchor only, and a track came 0.077 mm from copper it could not see.
    Each custom pad's gr_circle / gr_poly primitives are read here, in world coordinates,
    onto the matching pad dict (same footprint and pad transform as repair_search._pads)."""
    key = {}
    for p in pads:
        key[(round(p["gx"], 3), round(p["gy"], 3), p["net"])] = p
    for f in re.findall(r"\(footprint\b(.*?)\n\t\)", txt, re.S):
        if " custom" not in f:
            continue
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", f)
        fx, fy = float(at.group(1)), float(at.group(2))
        rot = -math.radians(float(at.group(3)) if at.group(3) else 0.0)
        for m in re.finditer(r'\(pad "([^"]*)" \w+ custom(.*?)\n\t\t\)', f, re.S):
            body = m.group(2)
            pa = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", body)
            px, py = float(pa.group(1)), float(pa.group(2))
            gx = fx + px * math.cos(rot) - py * math.sin(rot)
            gy = fy + px * math.sin(rot) + py * math.cos(rot)
            ang = -math.radians(float(pa.group(3))) if pa.group(3) else rot
            ca, sa = math.cos(ang), math.sin(ang)
            nt = re.search(r'\(net "([^"]*)"\)', body)
            p = key.get((round(gx, 3), round(gy, 3), nt.group(1) if nt else ""))
            if p is None:
                continue
            world = lambda u, v: (gx + u * ca - v * sa, gy + u * sa + v * ca)
            circles, polys = [], []
            for c in re.finditer(r"\(gr_circle\s*\(center ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)",
                                 body):
                u, v, eu, ev = map(float, c.groups())
                x, y = world(u, v)
                circles.append((x, y, math.hypot(eu - u, ev - v)))
            for g in re.finditer(r"\(gr_poly\s*\(pts((?:\s*\(xy [-\d.]+ [-\d.]+\))+)", body):
                pts = [world(float(a), float(b))
                       for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", g.group(1))]
                if len(pts) >= 3:
                    polys.append(pts)
            p["circles"], p["polys"] = circles, polys


def _attach_drills(txt, pads):
    """Each drilled pad's hole onto its pad dict: drill = (hx, hy, r), a capsule from
    (gx-hx, gy-hy) to (gx+hx, gy+hy) of radius r (a round hole has hx = hy = 0), and
    npth = True for an unplated one."""
    key = {}
    for p in pads:
        key.setdefault((round(p["gx"], 3), round(p["gy"], 3)), []).append(p)
    for f in re.findall(r"\(footprint\b(.*?)\n\t\)", txt, re.S):
        if "(drill" not in f:
            continue
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", f)
        fx, fy = float(at.group(1)), float(at.group(2))
        rot = -math.radians(float(at.group(3)) if at.group(3) else 0.0)
        for m in re.finditer(r'\(pad "([^"]*)" (np_thru_hole|thru_hole) \w+(.*?)\n\t\t\)', f, re.S):
            body = m.group(3)
            dr = re.search(r"\(drill (oval )?([-\d.]+)(?: ([-\d.]+))?", body)
            pa = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", body)
            if not (dr and pa):
                continue
            px, py = float(pa.group(1)), float(pa.group(2))
            gx = fx + px * math.cos(rot) - py * math.sin(rot)
            gy = fy + px * math.sin(rot) + py * math.cos(rot)
            a = float(dr.group(2))
            b = float(dr.group(3)) if dr.group(3) else a
            ang = -math.radians(float(pa.group(3))) if pa.group(3) else rot
            if a >= b:     # long axis along the pad's local x
                h, r, ux, uy = (a - b) / 2.0, b / 2.0, math.cos(ang), math.sin(ang)
            else:
                h, r, ux, uy = (b - a) / 2.0, a / 2.0, -math.sin(ang), math.cos(ang)
            for p in key.get((round(gx, 3), round(gy, 3)), ()):
                p["drill"] = (ux * h, uy * h, r)
                p["npth"] = m.group(2) == "np_thru_hole"


def _area(pts):
    return 0.5 * abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1]
                         for i in range(len(pts))))


def _pours(txt, named=None):
    """{net: [(layer, outline pts)]}: every copper zone's OUTLINE, in board coordinates
    (only the zones of that `name` when `named` is given).

    Read from the board, not from board.json's `zones`, because that list comes in two
    spellings (a whole-layer three-tuple, or a dict with a `poly` region in layout's own
    frame -- optical's +3V3D under U6) and the board already holds both as plain outlines."""
    out = {}
    for z in re.findall(r"\(zone\b(.*?)\n\t\)", txt, re.S):
        if "(keepout" in z:
            continue
        if named is not None and not re.search(r'\(name "%s"\)' % re.escape(named), z):
            continue
        nt = re.search(r'\(net "([^"]*)"', z)
        ly = re.search(r'\(layer "([^"]+)"\)', z)
        pg = re.search(r"\(polygon\s*\(pts((?:\s*\(xy [-\d.]+ [-\d.]+\))+)", z, re.S)
        if not (nt and ly and pg and nt.group(1)):
            continue
        pts = [(float(a), float(b)) for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", pg.group(1))]
        if len(pts) >= 3:
            out.setdefault(nt.group(1), []).append((ly.group(1), pts))
    return out



def _zone_rules(txt):
    """{net: (clearance, min_thickness)}: the zone's OWN rules, the largest over its zones.

    ⚠ A POUR KEEPS ITS OWN DISTANCE, NOT THE NETCLASS'S (optical +3V3D, 2026-11-09): the
    zone under U6 holds 0.5 mm off other copper and is at least 0.25 mm wide; the island
    judge assumed 0.127 and 0.2, saw fill where KiCad lays none, and called four join vias
    joined that the refill left on islands -- the tidy pass removed them as dangling and
    close_last closed six pads 5.7 mm round."""
    out = {}
    for z in re.findall(r"\(zone\b(.*?)\n\t\)", txt, re.S):
        if "(keepout" in z:
            continue
        nt = re.search(r'\(net "([^"]*)"', z)
        if not (nt and nt.group(1)):
            continue
        cl = re.search(r"\(connect_pads[^()]*\(clearance ([\d.]+)\)", z)
        mt = re.search(r"\(min_thickness ([\d.]+)\)", z)
        c0, t0 = out.get(nt.group(1), (0.0, 0.0))
        out[nt.group(1)] = (max(c0, float(cl.group(1)) if cl else 0.0),
                            max(t0, float(mt.group(1)) if mt else 0.0))
    return out


def _fills(txt):
    """{net: [(layer, filled pts)]}: every copper zone's FILL as layout left it.

    ⚠ THE OUTLINE IS NOT THE COPPER (optical +3V3D, 2026-11-08). A plane join aimed at
    the pour's outline dropped three vias into voids of the fill under U6 -- inside the
    outline, touching no copper -- and the tidy pass removed them as dangling: five A1
    "no copper joins" FAILs. KiCad stores a fill as fractured polygons (holes joined to
    the rim by zero-width slits), so an even-odd test reads each one directly."""
    out = {}
    for z in re.findall(r"\(zone\b(.*?)\n\t\)", txt, re.S):
        if "(keepout" in z:
            continue
        nt = re.search(r'\(net "([^"]*)"', z)
        if not (nt and nt.group(1)):
            continue
        for fp in re.finditer(r'\(filled_polygon\s*\(layer "([^"]+)"\)\s*\(pts((?:\s*\(xy [-\d.]+ [-\d.]+\))+)', z):
            pts = [(float(a), float(b)) for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", fp.group(2))]
            if len(pts) >= 3:
                out.setdefault(nt.group(1), []).append((fp.group(1), pts))
    return out

def _keepouts(txt):
    """Rule areas: [{layers, pts, tracks, vias}] -- tracks/vias True where not allowed.
    (repair_search's reader keeps track bans only; the router places vias too.)"""
    out = []
    for z in re.findall(r"\(zone\b(.*?)\n\t\)", txt, re.S):
        if "(keepout" not in z:
            continue
        tr = "(tracks not_allowed)" in z
        vi = "(vias not_allowed)" in z
        if not (tr or vi):
            continue
        ly = re.search(r'\(layers((?: "[^"]+")+)\)', z)
        one = re.search(r'\(layer "([^"]+)"\)', z)
        layers = set(re.findall(r'"([^"]+)"', ly.group(1))) if ly else (
            {one.group(1)} if one else set())
        # ⚠ THE LAZY "(pts(.*?)\)\s*\)" STOPPED INSIDE THE LAST POINT: its closing paren was
        # taken as the end of pts, so the last (xy ...) lost its ")" and was never read, and
        # every 4-point keep-out came back a TRIANGLE (U1's slug fence, 2026-11-08: half of
        # each fence bar missing, and a via landed in it). Match the run of points itself.
        pg = re.search(r"\(polygon\s*\(pts((?:\s*\(xy [-\d.]+ [-\d.]+\))+)", z, re.S)
        if not pg:
            continue
        pts = [(float(a), float(b))
               for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", pg.group(1))]
        if len(pts) >= 3:
            out.append(dict(layers=layers, pts=pts, tracks=tr, vias=vi))
    return out


def _d_pts_seg(X, Y, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    if L == 0:
        return np.hypot(X - x1, Y - y1)
    t = np.clip(((X - x1) * dx + (Y - y1) * dy) / L, 0.0, 1.0)
    return np.hypot(X - (x1 + t * dx), Y - (y1 + t * dy))


def _in_poly(X, Y, pts):
    """Even-odd point-in-polygon over arrays X, Y (same shape).

    ⚠ THIS WAS 57 % OF A ROUTE (optical, 2026-11-09): a pour's fill is a fractured polygon
    of thousands of points, and the edge loop below ran in Python over the whole window --
    35 s per call, every round, for +3V3D's plane joins alone. A grid (X constant down
    columns, Y along rows -- every meshgrid caller) is now one compiled scanline pass:
    per row the edge crossings, sorted, and each column's count of crossings to its right.
    Same rule exactly: an edge counts where (y1 > y) != (y2 > y) and x < its crossing."""
    X = np.asarray(X, np.float64)
    Y = np.asarray(Y, np.float64)
    P = np.asarray(pts, np.float64)
    if _nb is not None and len(P) >= 3 and X.size:
        if X.ndim == 2 and X.shape == Y.shape and (X == X[0:1]).all() and (Y == Y[:, 0:1]).all():
            return _grid_in(np.ascontiguousarray(X[0]), np.ascontiguousarray(Y[:, 0]), P)
        return _pts_in(X.ravel(), Y.ravel(), P).reshape(X.shape)
    return _in_poly_np(X, Y, pts)


try:
    import numba as _nb
except ImportError:          # KiCad's Python has no numba: the plain loop below serves
    _nb = None

if _nb is not None:
    @_nb.njit(cache=True)
    def _grid_in(xs, ys, P):
        n = P.shape[0]
        out = np.zeros((ys.size, xs.size), np.bool_)
        xc = np.empty(n, np.float64)
        for i in range(ys.size):
            y = ys[i]
            m = 0
            for e in range(n):
                x1, y1 = P[e, 0], P[e, 1]
                x2, y2 = P[(e + 1) % n, 0], P[(e + 1) % n, 1]
                if y1 == y2:
                    continue
                if (y1 > y) != (y2 > y):
                    xc[m] = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                    m += 1
            if m == 0:
                continue
            row = np.sort(xc[:m])
            for j in range(xs.size):
                # crossings strictly right of x: x < xc
                k = np.searchsorted(row, xs[j], side="right")
                if (m - k) % 2 == 1:
                    out[i, j] = True
        return out

    @_nb.njit(cache=True)
    def _pts_in(xs, ys, P):
        n = P.shape[0]
        out = np.zeros(xs.size, np.bool_)
        for q in range(xs.size):
            x, y = xs[q], ys[q]
            c = False
            for e in range(n):
                x1, y1 = P[e, 0], P[e, 1]
                x2, y2 = P[(e + 1) % n, 0], P[(e + 1) % n, 1]
                if y1 == y2:
                    continue
                if (y1 > y) != (y2 > y):
                    if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                        c = not c
            out[q] = c
        return out


def _in_poly_np(X, Y, pts):
    inside = np.zeros(X.shape, bool)
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if y1 == y2:
            continue
        cond = (y1 > Y) != (y2 > Y)
        xc = x1 + (Y - y1) * (x2 - x1) / (y2 - y1)
        inside ^= cond & (X < xc)
    return inside


def _loops(edges):
    """Chain the outline's segments into closed loops, largest (the outline) first."""
    key = lambda p: (round(p[0], 3), round(p[1], 3))
    adj = {}
    for x1, y1, x2, y2 in edges:
        a, b = key((x1, y1)), key((x2, y2))
        if a == b:
            continue
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    seen, loops = set(), []
    for start in adj:
        if start in seen:
            continue
        loop, prev, cur = [start], None, start
        seen.add(start)
        while True:
            nxt = [q for q in adj[cur] if q != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            if cur == start or cur in seen:
                break
            seen.add(cur)
            loop.append(cur)
        if len(loop) >= 3:
            loops.append(loop)
    area = lambda P: abs(sum(P[i][0] * P[i - 1][1] - P[i - 1][0] * P[i][1] for i in range(len(P))))
    return sorted(loops, key=area, reverse=True)
