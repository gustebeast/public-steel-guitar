"""place_init.py: a legal first placement from intent + netlist (PLACEMENT.md step (b)).

    py -3.12 place_init.py <stem> <intent.json> [--out placements.json] [--keep REF,...]

<stem>.parts.json (place_geom) gives each part's local pads / courtyard; <stem>.board.json
the outline and cutouts; the intent (place_intent) the rules. Writes {ref: [x, y, rot]} in
the board frame -- the `placements` layout.py takes -- and prints what it did.

Constructive, seconds, no router:
  1. FIXED: `fixed` / `pin` parts where they are told, `panel` parts where the panel puts
     their body front (rot from their `rot` rule, else as in the parts file).
  2. GLOBAL: quadratic placement on the net graph -- every free part a point, each net a
     clique of springs between its pads (weight 1 / (pins - 1)); nets wider than WIDE pins
     (ground, rails: the planes carry them) left out; `chain` hops and diff pairs pulled
     hard; `in_region` parts sprung to their region; fixed parts' pads as anchors.
  3. TURN: each multi-pin part turned (within its `rot` rule) so its pads face their nets.
  4. LEGAL: parts dropped in, biggest first, each at the free spot nearest its target on a
     GRID mm occupancy grid (courtyards, outline, holes, keep-outs; FFT collision maps over
     a window). An IC's decaps go in straight after it, at their pins.
layout.py stays the legality gate; this only has to hand it something it will take.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
from scipy.ndimage import binary_dilation
from scipy.signal import fftconvolve

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_intent as pi  # noqa: E402

GRID = 0.1          # mm, the legaliser's occupancy grid
WIDE = 12           # nets with more pins than this are left to the planes
GAP = 0.05          # courtyards are already the keep-out: just no overlap
WINDOW = 18.0       # mm searched round a part's target before widening
# ROOM TO ESCAPE (output_panel, 2026-11-10). Courtyards butted 0.15 mm all round U1 left no
# spot for a GND stitching via beside two of its pads (layout refused the board) and no lane
# for its escapes. A placed part keeps a halo no later part may enter: an IC the width of a
# via and its clearance on every side, anything else a sliver for a stitch between ends.
# A fine-pitch IC needs more: its escapes fan out from pad pitch to track pitch, so the ring
# grows with the pins on a side (HALO_PER_PIN a pin, HALO_IC to HALO_MAX). 0.15 over 0.10 on
# output_panel: 1 open against 3, one pair fault against 2.
HALO_IC, HALO_SMALL, IC_PADS, HALO_MAX = 1.0, 0.25, 8, 2.5
HALO_PER_PIN = float(os.environ.get("PLACE_HALO_K", "0.15"))


def halo(part):
    n = len(part["pads"])
    if n <= IC_PADS:
        return HALO_SMALL
    return min(HALO_MAX, max(HALO_IC, HALO_PER_PIN * n / 4.0))


class Grid:
    def __init__(self, poly, cutouts, keepouts, g=GRID):
        poly = np.asarray(poly, float)
        self.g = g
        self.x0, self.y0 = poly[:, 0].min(), poly[:, 1].min()
        self.W = int(math.ceil((poly[:, 0].max() - self.x0) / g)) + 1
        self.H = int(math.ceil((poly[:, 1].max() - self.y0) / g)) + 1
        X, Y = np.meshgrid(self.x0 + np.arange(self.W) * g, self.y0 + np.arange(self.H) * g)
        pts = np.stack([X.ravel(), Y.ravel()], axis=1)
        inside = pi._inside(poly, pts).reshape(self.H, self.W)
        # a courtyard may meet the edge, not cross it: one cell of margin from the boundary
        self.occ = ~inside
        self.occ = binary_dilation(self.occ, iterations=1)
        for c in cutouts:
            r = c["d"] / 2.0 + c.get("keepout", 0.0)
            self.occ |= (np.hypot(X - c["xy"][0], Y - c["xy"][1]) <= r)
        for k in keepouts:
            self.occ |= pi._inside(k, pts).reshape(self.H, self.W)
        self.occ_p = np.zeros_like(self.occ)        # placed courtyards alone, no halo
        self.X, self.Y = X, Y

    def ij(self, x, y):
        return int(round((y - self.y0) / self.g)), int(round((x - self.x0) / self.g))

    def xy(self, i, j):
        return self.x0 + j * self.g, self.y0 + i * self.g


def mask(part, rot, g=GRID):
    """Rasterised courtyard of a part at rot about its anchor: (bool array, anchor i, anchor j)."""
    loc = part["crtyd"]
    if not loc:
        f = part["fab"] or [-0.5, 0.5, -0.5, 0.5]
        loc = [[f[0], f[2]], [f[1], f[2]], [f[1], f[3]], [f[0], f[3]]]
    w = pi._rot(loc, rot)
    xa, xb, ya, yb = w[:, 0].min() - GAP, w[:, 0].max() + GAP, w[:, 1].min() - GAP, w[:, 1].max() + GAP
    j0, j1 = int(math.floor(xa / g)), int(math.ceil(xb / g))
    i0, i1 = int(math.floor(ya / g)), int(math.ceil(yb / g))
    X, Y = np.meshgrid(np.arange(j0, j1 + 1) * g, np.arange(i0, i1 + 1) * g)
    m = pi._inside(w, np.stack([X.ravel(), Y.ravel()], axis=1)).reshape(X.shape)
    m = binary_dilation(m, iterations=1)          # half a cell each side: conservative
    return m, -i0, -j0


def _pad_off(part, rot):
    return pi._rot([q["xy"] for q in part["pads"]], rot) if part["pads"] else np.zeros((0, 2))


def place(parts, notes, rules, keep=()):
    pl = {}
    log = []
    why = {}                     # provenance: which rule (or stage) set each coordinate
    rot_of = {}
    for r in rules:
        if r["kind"] == "rot":
            rot_of[r["ref"]] = list(r["allowed"])

    def rot0(ref):
        return rot_of.get(ref, [parts[ref]["at"][2]])[0]

    # ---- 1. fixed
    for ref in keep:
        pl[ref] = list(notes["placements"][ref])
        why[ref] = "keep (hand)"
    for i_r, r in enumerate(rules):
        if r["kind"] in ("fixed", "pin"):
            pl[r["ref"]] = [r["xy"][0], r["xy"][1], r.get("rot", rot0(r["ref"]))]
            why[r["ref"]] = "rule %d %s [%s]" % (i_r, r["kind"], r.get("src", ""))
        elif r["kind"] == "panel":
            ref = r["ref"]
            rot = rot0(ref)
            ux, uy = pi.DIRS[r["edge"]]
            P = pi.Placed(parts, {ref: [0.0, 0.0, rot]})
            b = P.body(ref)
            front = float((b @ (ux, uy)).max())
            want = r["face"] + r.get("overhang", 0.0)
            along = (0.0, 1.0) if ux else (1.0, 0.0)
            mid = float(((b @ along).max() + (b @ along).min()) / 2.0)
            s = want - front
            a = r.get("at", 0.0) - mid
            pl[ref] = [ux * s + along[0] * a, uy * s + along[1] * a, rot]
            why[ref] = "rule %d panel %s [%s]" % (i_r, r["edge"], r.get("src", ""))
    fixed = set(pl)
    log.append("fixed %d: %s" % (len(fixed), " ".join(sorted(fixed))))

    # ---- 2. global (quadratic)
    free = [r for r in sorted(parts) if r not in fixed]
    idx = {r: i for i, r in enumerate(free)}
    n = len(free)
    nets = {}
    for ref, p in parts.items():
        off = _pad_off(p, pl[ref][2] if ref in pl else rot0(ref))
        for q, o in zip(p["pads"], off):
            if q["net"]:
                nets.setdefault(q["net"], []).append((ref, o))
    wnet = {}
    for spec in notes.get("diff_pairs", ()):
        for nm in spec.get("nets", ()):
            wnet[nm] = 4.0
    A = np.zeros((n, n))
    bx, by = np.zeros(n), np.zeros(n)

    def spring(a, oa, b, ob, w):
        # (xa + oa) - (xb + ob) ; a, b refs (free or fixed)
        fa, fb = a in idx, b in idx
        pa = None if fa else np.asarray(pl[a][:2]) + oa
        pb = None if fb else np.asarray(pl[b][:2]) + ob
        if fa and fb:
            i, j = idx[a], idx[b]
            A[i, i] += w
            A[j, j] += w
            A[i, j] -= w
            A[j, i] -= w
            d = ob - oa
            bx[i] += w * d[0]
            by[i] += w * d[1]
            bx[j] -= w * d[0]
            by[j] -= w * d[1]
        elif fa:
            i = idx[a]
            A[i, i] += w
            t = pb - oa
            bx[i] += w * t[0]
            by[i] += w * t[1]
        elif fb:
            spring(b, ob, a, oa, w)

    for nm, pins in nets.items():
        k = len(pins)
        if k < 2 or k > WIDE:
            continue
        w = wnet.get(nm, 1.0) / (k - 1)
        for u in range(k):
            for v in range(u + 1, k):
                if pins[u][0] != pins[v][0]:
                    spring(pins[u][0], pins[u][1], pins[v][0], pins[v][1], w)
    regions = {r["name"]: np.asarray(r["poly"], float) for r in rules if r["kind"] == "region"}
    for r in rules:
        if r["kind"] == "in_region":
            c = regions[r["region"]].mean(axis=0)
            for ref in pi._refs(r["refs"], parts):
                if ref in idx:
                    i = idx[ref]
                    A[i, i] += 2.0
                    bx[i] += 2.0 * c[0]
                    by[i] += 2.0 * c[1]
        elif r["kind"] == "chain":
            rs = r["refs"]
            for a_, b_ in zip(rs, rs[1:]):
                spring(a_, np.zeros(2), b_, np.zeros(2), 2.0)
    poly = np.asarray(notes.get("outline_poly") or pi._rect(notes["outline_mm"]), float)
    cen = poly.mean(axis=0)
    A[np.diag_indices(n)] += 1e-3                    # an unconnected part drifts to the middle
    bx += 1e-3 * cen[0]
    by += 1e-3 * cen[1]
    gx, gy = np.linalg.solve(A, bx), np.linalg.solve(A, by)
    target = {r: np.array([gx[idx[r]], gy[idx[r]]]) for r in free}

    # ---- 3. turn
    where = {}
    for ref in parts:
        where[ref] = np.asarray(pl[ref][:2]) if ref in pl else target[ref]
    netc = {nm: np.mean([where[r_] for r_, _ in pins], axis=0) for nm, pins in nets.items() if 2 <= len(pins) <= WIDE}
    def rots(ref, first):
        if ref in rot_of:
            return [first] + [a for a in rot_of[ref] if a != first]
        return [first, (first + 90) % 360, (first + 180) % 360, (first + 270) % 360]

    rot = {}
    for ref in free:
        p = parts[ref]
        opts = rot_of.get(ref, [0.0, 90.0, 180.0, 270.0] if len(p["pads"]) > 2 else [rot0(ref), (rot0(ref) + 90) % 360])
        best = None
        for a in opts:
            off = _pad_off(p, a)
            c = sum(float(np.hypot(*(netc[q["net"]] - (where[ref] + o))))
                    for q, o in zip(p["pads"], off) if q["net"] in netc)
            if best is None or c < best[0] - 1e-6:
                best = (c, a)
        rot[ref] = best[1]

    # ---- 4. legal
    G = Grid(poly, [dict(c) for c in notes.get("cutouts", ())] +
             [{"xy": r["xy"], "d": r["d"], "keepout": r.get("keepout", 0.0)} for r in rules if r["kind"] == "hole"],
             [r["poly"] for r in rules if r["kind"] == "keepout"])
    inreg = {}
    for r in rules:
        if r["kind"] == "in_region":
            out = ~pi._inside(regions[r["region"]], np.stack([G.X.ravel(), G.Y.ravel()], axis=1)).reshape(G.H, G.W)
            for ref in pi._refs(r["refs"], parts):
                inreg[ref] = out
    for ref in fixed:
        m, ai, aj = mask(parts[ref], pl[ref][2])
        _stamp(G, m, ai, aj, *G.ij(*pl[ref][:2]), force=True, grow=halo(parts[ref]))
    decaps = {}
    for r in rules:
        if r["kind"] == "decap":
            decaps.setdefault(r["pin"].split(".")[0], []).append(r)
        elif r["kind"] == "near" and r.get("ref") in idx:
            decaps.setdefault(r["target"].split(".")[0], []).append(r)
    area = {ref: float(np.prod(np.ptp(np.asarray(parts[ref]["crtyd"] or [[0, 0], [1, 1]]), axis=0))) for ref in free}
    sat = {r_.get("cap") or r_.get("ref") for v in decaps.values() for r_ in v}
    order = sorted((r for r in free if r not in sat), key=lambda r: -area[r])
    placed_sat = set()
    miss = []
    for ref in sorted(fixed) + order:
        if ref not in fixed:
            if not _drop(G, parts, ref, target[ref], rots(ref, rot[ref]), pl, inreg.get(ref)):
                miss.append(ref)
                continue
            why[ref] = "net graph (quadratic), nearest free spot" + (" in its region" if ref in inreg else "")
        for r in sorted(decaps.get(ref, ()), key=lambda r: r.get("max_mm", 9)):
            c = r.get("cap") or r.get("ref")
            if c in placed_sat or c in fixed or c not in idx:
                continue
            P = pi.Placed(parts, pl)
            if r["kind"] == "decap":
                pin = P.pad(*r["pin"].split(".", 1))
                ctr = np.asarray(pl[ref][:2])
                v = pin - ctr
                t = pin + v / (np.hypot(*v) or 1.0) * 1.0          # just outside the pin
            elif "." in r["target"]:
                t = P.pad(*r["target"].split(".", 1))
            else:
                t = np.asarray(pl[ref][:2])
            if _drop(G, parts, c, t, rots(c, rot[c]), pl, inreg.get(c)):
                placed_sat.add(c)
                why[c] = "%s at %s [%s]" % (r["kind"], r.get("pin") or r.get("target"), r.get("src", ""))
    for c in sorted(sat - placed_sat - fixed):
        if c in idx:
            if _drop(G, parts, c, target[c], rots(c, rot[c]), pl, inreg.get(c)):
                why[c] = "net graph (its anchor part had no room near it)"
            else:
                miss.append(c)
    log.append("placed %d free parts (%d satellites at their pins), %d with no room: %s"
               % (len(free) - len(miss), len(placed_sat), len(miss), " ".join(miss)))
    return pl, log, why


def _grow(m, ai, aj, grow, g=GRID):
    k = int(round(grow / g))
    if not k:
        return m, ai, aj
    return binary_dilation(np.pad(m, k), iterations=k), ai + k, aj + k


def _put(arr, m, ai, aj, i, j):
    i0, j0 = i - ai, j - aj
    h, w = m.shape
    a0, b0 = max(0, i0), max(0, j0)
    a1, b1 = min(arr.shape[0], i0 + h), min(arr.shape[1], j0 + w)
    if a1 > a0 and b1 > b0:
        arr[a0:a1, b0:b1] |= m[a0 - i0:a1 - i0, b0 - j0:b1 - j0]


def _stamp(G, m, ai, aj, i, j, force=False, grow=0.0):
    """A placed part: its courtyard grown by its halo into G.occ (what later parts' plain
    courtyards must miss), its plain courtyard into G.occ_p (what a later part's own halo
    must miss)."""
    _put(G.occ_p, m, ai, aj, i, j)
    _put(G.occ, *_grow(m, ai, aj, grow, G.g), i, j)


def _collide(sub, m, ai, aj):
    """1.0 where a mask anchored at that cell meets an occupied cell (or leaves the window)."""
    hit = fftconvolve(sub, m[::-1, ::-1].astype(np.float32), mode="full")
    h, w = m.shape
    # full-conv index (u, v) <-> mask top-left at (u - h + 1, v - w + 1) in sub
    ii = np.arange(sub.shape[0])[:, None]
    jj = np.arange(sub.shape[1])[None, :]
    u = ii - ai + h - 1
    v = jj - aj + w - 1
    okr = (ii - ai >= 0) & (ii - ai + h <= sub.shape[0]) & (jj - aj >= 0) & (jj - aj + w <= sub.shape[1])
    uu, vv = np.clip(u, 0, hit.shape[0] - 1), np.clip(v, 0, hit.shape[1] - 1)
    return np.where(okr, hit[uu, vv], 1.0)


def _drop(G, parts, ref, t, rots, pl, forbid=None):
    """Put ref at the free grid spot nearest t (first rot that fits, nearer wins)."""
    best = None
    for rad in (WINDOW, WINDOW * 3, 1e9):
        for a in rots:
            m, ai, aj = mask(parts[ref], a)
            ti, tj = G.ij(*t)
            R = int(rad / G.g)
            i0, i1 = max(0, ti - R), min(G.H, ti + R + 1)
            j0, j1 = max(0, tj - R), min(G.W, tj + R + 1)
            sub = G.occ[i0:i1, j0:j1]
            if forbid is not None:
                sub = sub | forbid[i0:i1, j0:j1]
            # ⚠ A HALO HOLDS BOTH WAYS (output_panel, 2026-11-11). Placed biggest first,
            # K1 (the relay, 0.25 mm halo) went in before U1, and U1 was dropped against
            # K1's own small halo: K1.4 sat 1.5 mm off U1's courtyard, inside U1's 2.5 mm
            # escape ring, where U1.49's GND stitch had to go -- the stitch then crossed
            # SWDIO's exit and SWDIO could not route on an empty board. The gap between two
            # parts is the larger of their halos whichever is placed first: the plain mask
            # misses everyone's grown courtyard, and the mask grown by its own halo misses
            # everyone's plain courtyard.
            col = _collide(sub.astype(np.float32), m, ai, aj)
            mg, gi, gj = _grow(m, ai, aj, halo(parts[ref]), G.g)
            col2 = _collide(G.occ_p[i0:i1, j0:j1].astype(np.float32), mg, gi, gj)
            free = (col < 0.5) & (col2 < 0.5)
            if not free.any():
                continue
            fi, fj = np.nonzero(free)
            d = np.hypot(fi + i0 - ti, fj + j0 - tj)
            k = int(np.argmin(d))
            if best is None or d[k] < best[0]:
                best = (float(d[k]), a, fi[k] + i0, fj[k] + j0, m, ai, aj)
        if best is not None:
            break
    if best is None:
        return False
    _, a, i, j, m, ai, aj = best
    _stamp(G, m, ai, aj, i, j, grow=halo(parts[ref]))
    x, y = G.xy(i, j)
    pl[ref] = [round(x, 3), round(y, 3), a]
    return True


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("stem")
    ap.add_argument("intent")
    ap.add_argument("--out")
    ap.add_argument("--keep", default="")
    a = ap.parse_args(argv)
    stem = os.path.abspath(a.stem)
    parts = json.load(open(stem + ".parts.json", encoding="utf-8"))["parts"]
    notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    rules = json.load(open(a.intent, encoding="utf-8"))
    import time
    t0 = time.time()
    pl, log, why = place(parts, notes, rules, [k for k in a.keep.split(",") if k])
    for line in log:
        print("place_init: " + line)
    out = a.out or stem + ".init.json"
    json.dump(pl, open(out, "w"), indent=0)
    json.dump(why, open(out[:-5] + ".why.json" if out.endswith(".json") else out + ".why", "w"), indent=0)
    print("place_init: %d placements -> %s (%.1f s)" % (len(pl), out, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
