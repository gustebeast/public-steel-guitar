"""Grid paths to KiCad copper: runs of one direction become one segment, a layer change a via.

⚠ EVERY JOINT IS A NODE (first own-router finish, 2026-11-08). A path that stops on a
land's rounded corner, or meets another track in the middle of its length, is connected as
far as KiCad's DRC cares -- the copper overlaps -- but quality's copper graph (A1) joins
track ENDS to lands they lie in and to other track ends, and read +5V as eleven open paths
from a track that began on FB1.2's corner. So every path end is finished the way an
engineer finishes it: into the middle of the land, onto the centreline of the track it
meets (which is then split there), and our own segments are split wherever another of the
net's ends lands on them."""
from __future__ import annotations

import math
import re
import uuid

import numpy as np

from .model import pad_dist, _d_pts_seg

EPS = 1e-4
NECK_W = 0.2         # negotiate.Router.NECK_W: a wide net's width where it necks down


def _grid_items(m, path, neck, w, wn, pinned=None):
    """[("seg", layer, x1, y1, x2, y2, width) | ("via", x, y, layer_a, layer_b)] for one
    path, corners kept; cells flagged in `neck` are drawn at wn, the rest at w."""
    H, W = m.ny, m.nx
    k = path // (H * W)
    r = path % (H * W)
    ii, jj = r // W, r % W
    if neck is None or len(neck) != k.size:
        neck = np.zeros(k.size, bool)
    out = []
    n = k.size
    a = 0
    while a < n:
        b = a
        while b + 1 < n and k[b + 1] == k[a]:
            b += 1
        verts = [a]
        for q in range(a + 1, b):
            turn = (ii[q] - ii[q - 1], jj[q] - jj[q - 1]) != (ii[q + 1] - ii[q], jj[q + 1] - jj[q])
            if turn or neck[q] != neck[q - 1] or neck[q] != neck[q + 1]:
                verts.append(q)
        if b > a:
            verts.append(b)
        # another path of the net ends on this run: that cell stays a vertex, so the
        # junction split below lands exactly on it
        pin = np.zeros(k.size, bool)
        if pinned:
            pin = np.fromiter((int(c) in pinned for c in path), bool, k.size)
            verts = sorted(set(verts) | {q for q in range(a + 1, b) if pin[q]})
        verts = _straighten(m, ii, jj, neck, verts, pin)
        L = m.route_layers[int(k[a])]
        for p, q in zip(verts, verts[1:]):
            x1, y1 = m.xy(int(ii[p]), int(jj[p]))
            x2, y2 = m.xy(int(ii[q]), int(jj[q]))
            out.append(("seg", L, x1, y1, x2, y2, wn if (neck[p] or neck[q]) else w))
        if b + 1 < n:
            x, y = m.xy(int(ii[b]), int(jj[b]))
            out.append(("via", x, y, L, m.route_layers[int(k[b + 1])]))
        a = b + 1
    ends = []
    for e in (0, n - 1):
        x, y = m.xy(int(ii[e]), int(jj[e]))
        ends.append((m.route_layers[int(k[e])], x, y, wn if neck[e] else w))
    return out, ends


# ⚠ A STAIRCASE IS ONE STRAIGHT TRACK (output_board mK, 2026-11-13): a V5_PRE run at a
# 1:2 slope came out as ~360 segments of 0.05-0.1 mm, alternating 45-degree and straight
# grid steps; drop_degenerate then took the whole chain for fragments and cut the net.
# From each vertex the run is drawn straight to the farthest later vertex whose path
# cells all lie within STRAIGHT_TOL of that line (and no neck change between). The
# copper then sits at most STRAIGHT_TOL from the centreline cells the router proved
# legal -- under the model's clearance margin (0.03 mm), so clearance holds by
# construction. None of the router's own cells move; only how they are drawn.
STRAIGHT_TOL = 0.025


def _straighten(m, ii, jj, neck, verts, pin=None):
    tol = min(STRAIGHT_TOL, getattr(m, "margin", STRAIGHT_TOL) * 0.9)
    if len(verts) < 3:
        return verts
    out = [verts[0]]
    p = 0
    while p < len(verts) - 1:
        a = verts[p]
        best = p + 1
        for q in range(p + 2, len(verts)):
            b = verts[q]
            if neck[a:b + 1].any() != neck[a:b + 1].all():
                break
            if pin is not None and pin[a + 1:b].any():
                break
            y0, x0 = ii[a] * 1.0, jj[a] * 1.0
            dy, dx = ii[b] - y0, jj[b] - x0
            L = math.hypot(dx, dy)
            if L == 0:
                break
            d = np.abs((ii[a:b + 1] - y0) * dx - (jj[a:b + 1] - x0) * dy) / L * m.pitch
            if d.max() > tol:
                break
            best = q
        out.append(verts[best])
        p = best
    return out


def _on(pt, s):
    """Does point (x, y) lie on segment s's interior (not at either end)?"""
    x, y = pt
    if math.hypot(x - s[2], y - s[3]) < EPS or math.hypot(x - s[4], y - s[5]) < EPS:
        return False
    return float(_d_pts_seg(np.array(x), np.array(y), s[2], s[3], s[4], s[5])) < EPS


def _stub_rho(x, y, tx, ty, w, p, n=48):
    """Largest half-width (<= min(w, r)) of the stub (x,y)->(tx,ty) whose two sides stay
    inside pad p's core capsule (x1,y1-x2,y2, radius r) or the disk of radius w at (x,y).
    The round caps are inside those by rho <= min(w, r); the sides are sampled n+1 points
    each and the half-width bisected."""
    r = p["r"]
    L = math.hypot(tx - x, ty - y)
    nx, ny = -(ty - y) / L, (tx - x) / L

    def inside(px, py):
        if (px - x) ** 2 + (py - y) ** 2 <= w * w + 1e-12:
            return True
        qx, qy = _proj(px, py, p["x1"], p["y1"], p["x2"], p["y2"])
        return (px - qx) ** 2 + (py - qy) ** 2 <= r * r + 1e-12

    def ok(rho):
        for k in range(n + 1):
            cx, cy = x + (tx - x) * k / n, y + (ty - y) * k / n
            if not (inside(cx + rho * nx, cy + rho * ny) and inside(cx - rho * nx, cy - rho * ny)):
                return False
        return True

    hi = min(w, r)
    if ok(hi):
        return hi
    lo = 0.0
    for _ in range(16):
        mid = (lo + hi) / 2.0
        if ok(mid):
            lo = mid
        else:
            hi = mid
    return lo


def _proj(x, y, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L))
    return x1 + t * dx, y1 + t * dy


def net_items(m, net):
    """All new copper for one net, ends finished and junctions split, plus the fixed
    segments that must be split: (items, splits) with splits = [(fixed seg dict, (x, y))]."""
    items, ends = [], []
    wn = min(net.width, NECK_W)
    pinned = {int(p_[e]) for p_ in net.paths if len(p_) for e in (0, -1)}
    for q, path in enumerate(net.paths):
        if not len(path):  # a join ripped out and left open: nothing to emit
            continue
        nk = net.necks[q] if q < len(getattr(net, "necks", ())) else None
        it, en = _grid_items(m, path, nk, net.width, wn, pinned)
        items += it
        ends += en
    pads = [p for p in m.pads if p["net"] == net.name]
    fsegs = [s for s in m.segs if s["net"] == net.name]
    fvias = [v for v in m.vias if v["net"] == net.name]
    splits = []
    # a layer change on the net's own declared via goes THROUGH it: no second drill, a stub
    # to its centre on each layer instead
    kept = []
    for it in items:
        if it[0] == "via":
            v = next((v for v in fvias if math.hypot(it[1] - v["x"], it[2] - v["y"]) <= v["r"]), None)
            if v is not None:
                if math.hypot(it[1] - v["x"], it[2] - v["y"]) > EPS:
                    for L in (it[3], it[4]):
                        kept.append(("seg", L, it[1], it[2], v["x"], v["y"], wn))
                continue
        kept.append(it)
    items = kept
    for L, x, y, we in ends:
        done = False
        for p in pads:
            if p["cu"] is not None and L not in p["cu"]:
                continue
            if float(pad_dist(p, np.array([[x]]), np.array([[y]]))[0, 0]) <= 1e-6:
                # ⚠ THE STUB IS COPPER THE ROUTER NEVER SAW (output_board mK, 2026-11-13):
                # VIN_BRAIN's path ended in Q202.3's rounded corner and a 1.0 mm stub ran
                # from there to the land's centre; its edge swept outside the land and stood
                # 0.055 mm off FLASH_DM -- a signal on a 10 A rail, legal in the router's
                # model and a clearance fault on the board. The stub now goes to the nearest
                # point of the land's core axis (pad x1,y1-x2,y2, radius r: inside the land),
                # at a half-width that keeps it inside the end's own disk (w/2, which the
                # router cleared) and that core. d the hop from the axis: with d <= r the
                # stub's sides stay within r of the axis and its far cap is the end's own
                # disk, so rho = min(w/2, r); with d > r (the end in a rectangle's corner)
                # the band between the core's edge and the end must stay inside that disk:
                # rho <= sqrt(w^2/4 - (d - r)^2). Under 0.127 mm, no stub.
                # ⚠ NOT TIGHTER (mK 2026-11-14): (w/2 + r - d) / 2 halved the stub of an end
                # sitting ON the land's edge (d = r), 0.1 < 0.127 dropped it, and U6.5 lost
                # the node inside its land that A1's copper graph joins a pad by -- a hard
                # "no copper joins" on a net DRC calls connected.
                # ⚠ AND NOT A BAND FORMULA (mK 2026-11-14, U220 x3 at 0.18 mm): where the
                # end projects onto an END of the core axis the land there is the core's
                # round cap, not a band, and a diagonal stub's sides left it. The half-width
                # is now TESTED: every point of the stub's two sides inside the core capsule
                # or the end's own disk (_stub_rho).
                tx, ty = _proj(x, y, p["x1"], p["y1"], p["x2"], p["y2"])
                d = math.hypot(x - tx, y - ty)
                if d > EPS:
                    rho = _stub_rho(x, y, tx, ty, we / 2.0, p)
                    if 2.0 * rho >= 0.127:
                        items.append(("seg", L, x, y, tx, ty, round(2.0 * rho, 4)))
                done = True
                break
        if done:
            continue
        for v in fvias:
            if math.hypot(x - v["x"], y - v["y"]) <= v["r"] + 1e-6:
                if math.hypot(x - v["x"], y - v["y"]) > EPS:
                    items.append(("seg", L, x, y, v["x"], v["y"], min(we, 2 * v["r"])))
                done = True
                break
        if done:
            continue
        for s in fsegs:
            if s["layer"] != L:
                continue
            px, py = _proj(x, y, s["x1"], s["y1"], s["x2"], s["y2"])
            if math.hypot(x - px, y - py) <= s["half"] + 1e-6:
                if math.hypot(x - px, y - py) > EPS:
                    items.append(("seg", L, x, y, px, py, min(we, 2 * s["half"])))
                if (math.hypot(px - s["x1"], py - s["y1"]) > EPS
                        and math.hypot(px - s["x2"], py - s["y2"]) > EPS):
                    splits.append((s, (px, py)))
                break
    # split our own segments wherever another end or a via of the net lands mid-length
    for _ in range(4):
        pts = {}
        for it in items:
            if it[0] == "seg":
                pts.setdefault(it[1], []).extend([(it[2], it[3]), (it[4], it[5])])
            else:
                for L in m.route_layers:
                    pts.setdefault(L, []).append((it[1], it[2]))
        out, changed = [], False
        for it in items:
            if it[0] != "seg":
                out.append(it)
                continue
            cut = next((q for q in pts.get(it[1], ()) if _on(q, it)), None)
            if cut is None:
                out.append(it)
                continue
            out.append(("seg", it[1], it[2], it[3], cut[0], cut[1], it[6]))
            out.append(("seg", it[1], cut[0], cut[1], it[4], it[5], it[6]))
            changed = True
        items = out
        if not changed:
            break
    # one via per spot
    seen, out = set(), []
    for it in items:
        if it[0] == "via":
            key = (round(it[1], 4), round(it[2], 4))
            if key in seen:
                continue
            seen.add(key)
        elif math.hypot(it[4] - it[2], it[5] - it[3]) < EPS:
            continue
        out.append(it)
    return out, splits


def _seg_block(L, x1, y1, x2, y2, w, net):
    return ('\t(segment\n\t\t(start %.4f %.4f)\n\t\t(end %.4f %.4f)\n\t\t(width %g)\n'
            '\t\t(layer "%s")\n\t\t(net "%s")\n\t\t(uuid "%s")\n\t)\n'
            % (x1, y1, x2, y2, w, L, net, uuid.uuid4()))


def _dedupe(txt):
    """⚠ IDENTICAL COPPER IS ONE PIECE OF COPPER. layout.py lays some declared copper twice
    (output_panel's HUB_DN4_DM: every segment and via doubled on the placed board).
    freerouting's session import replaced it wholesale, so the doubles never survived; this
    router keeps the board's copper, and quality read the doubled vias as a via budget
    blown and two drills 0.0 mm apart. Exact repeats are dropped here."""
    seen = set()

    def key(b):
        kind = "via" if b.lstrip().startswith("(via") else "segment"
        pts = re.findall(r"\((?:start|end|at) ([-\d.]+) ([-\d.]+)", b)
        nums = tuple(round(float(v), 4) for pair in pts for v in pair)
        nt = re.search(r'\(net "([^"]*)"', b)
        ly = re.search(r"\(layers? ([^)]*)\)", b)
        w = re.search(r"\((?:width|size) ([-\d.]+)", b)
        return (kind, nums, nt.group(1) if nt else "", ly.group(1) if ly else "",
                w.group(1) if w else "")

    def one(mt):
        k = key(mt.group(0))
        if k in seen:
            return ""
        seen.add(k)
        return mt.group(0)
    return re.sub(r"\n\t\((?:segment|via)\b.*?\n\t\)", one, txt, flags=re.S)


def write(model, nets, out_path):
    m = model
    blocks, splits = [], []
    for net in nets:
        items, sp = net_items(m, net)
        splits += sp
        for it in items:
            if it[0] == "seg":
                _, L, x1, y1, x2, y2, w = it
                blocks.append(_seg_block(L, x1, y1, x2, y2, w, net.name))
            else:
                x, y = it[1], it[2]
                blocks.append('\t(via\n\t\t(at %.4f %.4f)\n\t\t(size %g)\n\t\t(drill %g)\n'
                              '\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "%s")\n'
                              '\t\t(uuid "%s")\n\t)\n'
                              % (x, y, m.via_d, m.via_drill, net.name, uuid.uuid4()))
    txt = _dedupe(m.txt)
    # split the fixed segments new copper meets mid-length (all cuts on one segment at once)
    cuts = {}
    for s, pt in splits:
        cuts.setdefault(id(s), (s, []))[1].append(pt)

    def resplit(mt):
        b = mt.group(0)
        st = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", b)
        en = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", b)
        nt = re.search(r'\(net "([^"]*)"', b)
        ly = re.search(r'\(layer "([^"]+)"', b)
        if not (st and en and nt and ly):
            return b
        x1, y1, x2, y2 = map(float, (st.group(1), st.group(2), en.group(1), en.group(2)))
        for s, pts in cuts.values():
            if (s["net"] == nt.group(1) and s["layer"] == ly.group(1)
                    and abs(s["x1"] - x1) < EPS and abs(s["y1"] - y1) < EPS
                    and abs(s["x2"] - x2) < EPS and abs(s["y2"] - y2) < EPS):
                order = sorted(set((round(px, 4), round(py, 4)) for px, py in pts),
                               key=lambda q: math.hypot(q[0] - x1, q[1] - y1))
                chain = [(x1, y1)] + order + [(x2, y2)]
                w = float(re.search(r"\(width ([-\d.]+)\)", b).group(1))
                return "".join(_seg_block(ly.group(1), a[0], a[1], c[0], c[1], w, nt.group(1))
                               for a, c in zip(chain, chain[1:])).rstrip("\n").lstrip("\t")
        return b
    if cuts:
        txt = re.sub(r"\(segment\b.*?\n\t\)", resplit, txt, flags=re.S)
    txt = txt.rstrip()
    assert txt.endswith(")")
    txt = txt[:-1] + "".join(blocks) + ")\n"
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(txt)
    return len(blocks)
