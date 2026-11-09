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


def _grid_items(m, path, neck, w, wn):
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


def _on(pt, s):
    """Does point (x, y) lie on segment s's interior (not at either end)?"""
    x, y = pt
    if math.hypot(x - s[2], y - s[3]) < EPS or math.hypot(x - s[4], y - s[5]) < EPS:
        return False
    return float(_d_pts_seg(np.array(x), np.array(y), s[2], s[3], s[4], s[5])) < EPS


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
    for q, path in enumerate(net.paths):
        nk = net.necks[q] if q < len(getattr(net, "necks", ())) else None
        it, en = _grid_items(m, path, nk, net.width, wn)
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
                if math.hypot(x - p["gx"], y - p["gy"]) > EPS:
                    # never wider than the land it runs into (a 0.5 mm stub into a small
                    # land reached a neighbour: +24V_IN at U16, 2026-11-08)
                    short = 2.0 * (min(p["ihx"], p["ihy"]) + p["cr"])
                    items.append(("seg", L, x, y, p["gx"], p["gy"], max(min(we, short), 0.127)))
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
