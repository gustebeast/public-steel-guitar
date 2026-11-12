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
from scipy.ndimage import binary_dilation, distance_transform_edt
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
    n = part.get("n_own", len(part["pads"]))
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
        # counts, so a part can be lifted again (the local pass): mechanical blockage is 1
        self.occ = self.occ.astype(np.int16)
        self.occ_p = np.zeros_like(self.occ)        # placed courtyards alone, no halo
        self.X, self.Y = X, Y

    def ij(self, x, y):
        return int(round((y - self.y0) / self.g)), int(round((x - self.x0) / self.g))

    def xy(self, i, j):
        return self.x0 + j * self.g, self.y0 + i * self.g


def mask(part, rot, g=GRID):
    """Rasterised courtyard of a part at rot about its anchor: (bool array, anchor i, anchor j).
    A free-anchor cell (composite) is the union of its members' courtyards."""
    if part.get("crtyd_multi"):
        ms = [mask(dict(part, crtyd=c, crtyd_multi=None), rot, g) for c in part["crtyd_multi"]]
        i0 = min(-ai for _, ai, _ in ms)
        j0 = min(-aj for _, _, aj in ms)
        i1 = max(-ai + m.shape[0] for m, ai, _ in ms)
        j1 = max(-aj + m.shape[1] for m, _, aj in ms)
        out = np.zeros((i1 - i0, j1 - j0), bool)
        for m, ai, aj in ms:
            out[-ai - i0:-ai - i0 + m.shape[0], -aj - j0:-aj - j0 + m.shape[1]] |= m
        return out, -i0, -j0
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


def _composite(parts, anchor, members):
    """A free-anchor cell as one part in the anchor's frame (rot 0): the anchor's pads and
    each member's (num "M/num"), every courtyard kept (crtyd_multi), halo from the anchor."""
    a = parts[anchor]
    pads = [dict(q) for q in a["pads"]]
    cy = [a["crtyd"]] if a["crtyd"] else []
    for m, (dx, dy, dr) in members.items():
        pm = parts[m]
        off = np.array([dx, dy])
        for q in pm["pads"]:
            xy = off + pi._rot([q["xy"]], dr)[0]
            pads.append(dict(q, num="%s/%s" % (m, q["num"]), xy=[float(xy[0]), float(xy[1])],
                             rot=(q.get("rot", 0.0) + dr) % 360.0))
        loc = pm["crtyd"] or [[pm["fab"][0], pm["fab"][2]], [pm["fab"][1], pm["fab"][2]],
                              [pm["fab"][1], pm["fab"][3]], [pm["fab"][0], pm["fab"][3]]]
        cy.append((off + pi._rot(loc, dr)).tolist())
    return dict(a, pads=pads, crtyd=a["crtyd"], crtyd_multi=cy, n_own=len(a["pads"]))


def place(parts, notes, rules, keep=()):
    """Free-anchor `group` cells are placed whole: each becomes one composite part (its
    anchor's ref) for every stage, its members expanded from the anchor's pose at the end.

    ⚠ WHY (lead, 2026-11-11, for the re-layout): a designed cell -- a buck laid out round
    its pins, a PHY with its decap column -- is the design; only WHERE it goes is a
    placement choice. A group needed a fixed anchor before, so a cell had to be pinned or
    dissolved into free parts that the legaliser then scattered."""
    fixed0 = {r["ref"] for r in rules if r["kind"] in ("fixed", "pin", "panel")} | set(keep)
    cells = {r["anchor"]: r["members"] for r in rules if r["kind"] == "group" and r["anchor"] not in fixed0}
    if not cells:
        return _place(parts, notes, rules, keep)
    owner = {m: a for a, ms in cells.items() for m in ms}
    P2 = {r: p for r, p in parts.items() if r not in owner}
    for a, ms in cells.items():
        P2[a] = _composite(parts, a, ms)

    def pin(t):
        ref, _, num = t.partition(".")
        if ref in owner:
            return "%s.%s/%s" % (owner[ref], ref, num) if num else owner[ref]
        return t

    R2 = []
    for r in rules:
        if r["kind"] == "group" and r["anchor"] in cells:
            continue
        r = dict(r)
        for f in ("pin", "target"):
            if isinstance(r.get(f), str):
                r[f] = pin(r[f])
        for f in ("ref", "cap"):
            if r.get(f) in owner:
                r = None
                break
        if r is None:
            continue
        for f in ("refs", "others", "a", "b"):
            if isinstance(r.get(f), list):
                r[f] = list(dict.fromkeys(owner.get(x, x) for x in r[f]))
        R2.append(r)
    pl, log, why = _place(P2, notes, R2, keep)
    for a, ms in cells.items():
        ax, ay, ar = pl[a]
        for m, (dx, dy, dr) in ms.items():
            o = pi._rot([[dx, dy]], ar)[0]
            pl[m] = [round(ax + float(o[0]), 4), round(ay + float(o[1]), 4), (ar + dr) % 360.0]
            why[m] = "group: %s's cell, placed whole (free anchor)" % a
    log.append("free-anchor cells placed whole: %s" % " ".join("%s(+%d)" % (a, len(ms)) for a, ms in cells.items()))
    return pl, log, why


def _place(parts, notes, rules, keep=()):
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
            # the copper, not the body, decides how far out it may go (gap 6): a pad's far side
            # stays edge_clear inside the outline -- the body is pulled in by the shortfall
            sl = [x for x in pi.check(r, pi.Placed(parts, pl), notes) if x[2].startswith("pad ")]
            if sl and sl[0][0] < 0:
                pl[ref] = [pl[ref][0] + ux * sl[0][0], pl[ref][1] + uy * sl[0][0], rot]
                log.append("panel %s pulled in %.2f mm: %s" % (ref, -sl[0][0], sl[0][2]))
                why[ref] += " -- pulled in %.2f for pad-to-edge copper clearance" % -sl[0][0]
    # a rigid cell follows its anchor (the anchor fixed above; a free-anchor cell -- moved
    # whole by the legaliser -- is not built yet: say so rather than scatter the cell)
    for i_r, r in enumerate(rules):
        if r["kind"] != "group":
            continue
        if r["anchor"] not in pl:
            raise SystemExit("place_init: group rule %d: anchor %s unplaced (place() makes a free "
                             "anchor's cell a composite before this stage -- internal error)" % (i_r, r["anchor"]))
        ax, ay, ar = pl[r["anchor"]]
        for ref, (dx, dy, dr) in r["members"].items():
            o = pi._rot([[dx, dy]], ar)[0]
            pl[ref] = [ax + float(o[0]), ay + float(o[1]), (ar + dr) % 360.0]
            why[ref] = "rule %d group: %s's cell [%s]" % (i_r, r["anchor"], r.get("src", ""))
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
    # a loop the datasheet wants small: pulled x its weight in both stages (a plain
    # half-perimeter scores the buck's SW node like its DC output, and the output's far
    # loads won: L1 sat 33 mm from U5)
    for r in rules:
        if r["kind"] == "tight":
            for nm in r["nets"]:
                wnet[nm] = max(wnet.get(nm, 1.0), float(r.get("weight", 10.0)))
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
    near_springs = []
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
        elif r["kind"] == "between" and r.get("ref") in idx:
            # equal springs to both ends: the optimum is the midpoint, on the line
            for t in (r["a"], r["b"]):
                if "." in t:
                    tr, num = t.split(".", 1)
                    k = [q["num"] for q in parts[tr]["pads"]].index(num)
                    ot = _pad_off(parts[tr], pl[tr][2] if tr in pl else rot0(tr))[k]
                else:
                    tr, ot = t, np.zeros(2)
                spring(r["ref"], np.zeros(2), tr, ot, 2.0 * float(r.get("weight", 1.0)))
        elif r["kind"] == "near" and r.get("ref") in idx and len(parts[r["ref"]]["pads"]) > IC_PADS:
            # an IC near a part (optical's PHY near the socket): a spring here, not a
            # satellite drop -- see the satellite note below
            t = r["target"]
            if "." in t:
                tr, num = t.split(".", 1)
                k = [q["num"] for q in parts[tr]["pads"]].index(num)
                ot = _pad_off(parts[tr], pl[tr][2] if tr in pl else rot0(tr))[k]
            else:
                tr, ot = t, np.zeros(2)
            near_springs.append([r["ref"], tr, ot, 2.0 * float(r.get("weight", 1.0)), float(r["max_mm"])])
    poly = np.asarray(notes.get("outline_poly") or pi._rect(notes["outline_mm"]), float)
    cen = poly.mean(axis=0)
    A[np.diag_indices(n)] += 1e-3                    # an unconnected part drifts to the middle
    bx += 1e-3 * cen[0]
    by += 1e-3 * cen[1]
    # ⚠ A BROKEN `near` SPRING IS STIFFENED AND THE SYSTEM RE-SOLVED (optical, 2026-11-11):
    # the PHY's spring to the USB socket (weight 2) lost to twelve ULPI springs to the MCU
    # and U7 landed 20 mm from J1 against a 15 mm rule, the USB pair 4.4 mm uncoupled. A
    # fixed weight is a guess per board; tripling only the springs whose rule is still
    # broken (centre distance less both half-sizes, up to 3 rounds) asks the rule itself.
    A0, bx0, by0 = A.copy(), bx.copy(), by.copy()
    half = lambda r_: 0.5 * float(np.ptp(np.asarray(parts[r_]["crtyd"] or [[0, 0], [0, 0]]), axis=0).min())
    for _round in range(4):
        A[:], bx[:], by[:] = A0, bx0, by0
        for ref_, tr, ot, w, _m in near_springs:
            spring(ref_, np.zeros(2), tr, ot, w)
        gx, gy = np.linalg.solve(A, bx), np.linalg.solve(A, by)
        hard = False
        for sp in near_springs:
            ref_, tr, ot, w, m_ = sp
            pa = np.array([gx[idx[ref_]], gy[idx[ref_]]])
            pb = (np.array([gx[idx[tr]], gy[idx[tr]]]) if tr in idx else np.asarray(pl[tr][:2])) + ot
            if np.hypot(*(pa - pb)) - half(ref_) - (0.0 if np.any(ot) else half(tr)) > m_:
                sp[3] = w * 3.0
                hard = True
        if not hard:
            break
    if near_springs:
        log.append("near springs: %s" % " ".join("%s->%s x%g" % (a_, b_, w_) for a_, b_, _, w_, _ in near_springs))
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

    # ---- 3b. a declared pair's chain parts face each other
    got = _pair_turns(parts, list(notes.get("diff_pairs", ())), pl, target, rot, rot_of)
    for ref_, a_ in got.items():
        rot[ref_] = a_
        rot_of[ref_] = [a_]
    if got:
        log.append("pairs: chain parts turned %s" % " ".join("%s:%g" % kv for kv in got.items()))

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
    # ⚠ AN EXCLUSIVE REGION KEEPS OTHERS OUT (motor_ctrl trial, 2026-11-11): in_region holds
    # its members in, but nothing held the rest out -- the Pi band filled with parts that
    # had no business there and J4, the USB-C the band exists for, had "no room". A region
    # with exclusive: true is closed to every free part that is neither a member nor a
    # satellite (near / decap) of one: J4's ESD clamps and CC resistors still sit by it.
    XY = np.stack([G.X.ravel(), G.Y.ravel()], axis=1)
    for r in rules:
        if r["kind"] != "region" or not r.get("exclusive"):
            continue
        members = {x for q in rules if q["kind"] == "in_region" and q["region"] == r["name"]
                   for x in pi._refs(q["refs"], parts)}
        sats = {q.get("cap") or q.get("ref") for q in rules if q["kind"] in ("near", "decap")
                and ((q.get("target") or q.get("pin") or "").split(".")[0] in members)}
        inside = pi._inside(regions[r["name"]], XY).reshape(G.H, G.W)
        for ref in parts:
            if ref in members or ref in sats or ref in fixed:
                continue
            inreg[ref] = inside if ref not in inreg else (inreg[ref] | inside)
    for ref in fixed:
        m, ai, aj = mask(parts[ref], pl[ref][2])
        _stamp(G, m, ai, aj, *G.ij(*pl[ref][:2]), force=True, grow=halo(parts[ref]))
    decaps = {}
    for r in rules:
        if r["kind"] == "decap":
            decaps.setdefault(r["pin"].split(".")[0], []).append(r)
        elif r["kind"] == "near" and r.get("ref") in idx and len(parts[r["ref"]]["pads"]) <= IC_PADS:
            # ⚠ ONLY SMALL PARTS ARE SATELLITES (optical, 2026-11-11). U7 (the PHY, `near`
            # J1) was a satellite: dropped at J1's centre after J1, and -- not being in the
            # drop order -- its own ten decaps were never seated at its pins (C121 26 mm off
            # U7.6). An IC's `near` is a spring in the quadratic stage instead, and seating
            # below recurses, so a satellite's own satellites follow it.
            decaps.setdefault(r["target"].split(".")[0], []).append(r)
    area = {ref: float(np.prod(np.ptp(np.asarray(parts[ref]["crtyd"] or [[0, 0], [1, 1]]), axis=0))) for ref in free}
    sat = {r_.get("cap") or r_.get("ref") for v in decaps.values() for r_ in v}
    order = sorted((r for r in free if r not in sat), key=lambda r: -area[r])
    placed_sat = set()
    miss = []
    def seat(ref):
        """Seat ref's satellites at their pins; then each satellite's own (recursive)."""
        for r in sorted(decaps.get(ref, ()), key=lambda r: r.get("max_mm", 9)):
            c = r.get("cap") or r.get("ref")
            if c in placed_sat or c in fixed or c not in idx:
                continue
            P = pi.Placed(parts, pl)
            if r["kind"] == "decap":
                pin = _pin_at(P, r)
                ctr = np.asarray(pl[ref][:2])
                v = pin - ctr
                t = pin + v / (np.hypot(*v) or 1.0) * 1.0          # just outside the pin
            elif "." in r["target"]:
                t = P.pad(*r["target"].split(".", 1))
            else:
                t = np.asarray(pl[ref][:2])
            # a satellite keeps clear of its noise zones too, when there is room (output_panel
            # 2026-11-11: Y1, the MCU crystal, seated 0.67 mm from the buck inductor)
            fb, f0 = _apart_forbid(G, parts, pl, c, rules), inreg.get(c)
            if (fb is not None and _drop_sat(G, parts, c, t, rots(c, rot[c]), pl,
                                             fb if f0 is None else (fb | f0), ref, r, near_mm=r.get("max_mm")))                     or _drop_sat(G, parts, c, t, rots(c, rot[c]), pl, f0, ref, r):
                placed_sat.add(c)
                why[c] = "%s at %s [%s]" % (r["kind"], r.get("pin") or r.get("target"), r.get("src", ""))
                seat(c)

    for ref in sorted(fixed) + order:
        if ref not in fixed:
            fb = _apart_forbid(G, parts, pl, ref, rules)
            f0 = inreg.get(ref)
            tail = ""
            if fb is not None and _drop(G, parts, ref, target[ref], rots(ref, rot[ref]), pl,
                                        fb if f0 is None else (fb | f0)):
                tail = ", clear of its apart/thermal rules"
            elif not _drop(G, parts, ref, target[ref], rots(ref, rot[ref]), pl, f0):
                miss.append(ref)
                continue
            elif fb is not None:
                tail = ", NO room clear of its apart/thermal rules"
            why[ref] = "net graph (quadratic), nearest free spot" + (" in its region" if ref in inreg else "") + tail
        seat(ref)
    for c in sorted(sat - placed_sat - fixed):
        if c in idx:
            if _drop(G, parts, c, target[c], rots(c, rot[c]), pl, inreg.get(c)):
                why[c] = "net graph (its anchor part had no room near it)"
            else:
                miss.append(c)
    # ---- 4b. pair turns again, on the parts' real positions
    # ⚠ THE QUADRATIC TARGET IS NOT WHERE A SATELLITE LANDS (optical, 2026-11-11): U10 (the
    # ESD clamp, `near` J1) was turned on its quadratic target -- by U7, not J1 -- and the
    # turn that faced the pair there (0) was the worst one where it was dropped (cost 70
    # against 21 at 90). Decided again here, each changed part re-dropped at its spot.
    ch = list(dict.fromkeys(c for sp in notes.get("diff_pairs", ()) for c in sp.get("chain", ())
                            if c in idx and c in pl))
    if ch:
        pl_x = {k: v for k, v in pl.items() if k not in ch}
        cur = {c: np.asarray(pl[c][:2]) for c in ch}
        got = _pair_turns(parts, list(notes.get("diff_pairs", ())), pl_x, cur, {c: pl[c][2] for c in ch},
                          {c: [0.0, 90.0, 180.0, 270.0] for c in ch})
        for c, a_ in got.items():
            if abs((a_ - pl[c][2] + 180.0) % 360.0 - 180.0) < 0.5:
                rot_of[c] = [pl[c][2]]
                continue
            old = list(pl[c])
            _lift(G, parts, pl, c)
            if _drop(G, parts, c, cur[c], [a_], pl, inreg.get(c), near_mm=3.0):
                rot_of[c] = [a_]
                rot[c] = a_
                log.append("pairs: %s re-turned %g -> %g where it landed" % (c, old[2], a_))
                # its satellites stay where they were seated; the local pass moves the group
            else:
                _put_back(G, parts, pl, c, old)
                rot_of[c] = [old[2]]

    # ---- 5. local: lift each part and put it back nearer its nets, if that is shorter
    notes_c = dict(notes, _regions={r["name"]: r["poly"] for r in rules if r["kind"] == "region"},
                   _panel=[r for r in rules if r["kind"] == "panel"])
    sats = {}
    for anc, rs in decaps.items():
        for r in rs:
            c = r.get("cap") or r.get("ref")
            if c in placed_sat and c != anc:
                sats.setdefault(anc, []).append((c, r))
    moved, gain = _local(G, parts, pl, [r for r in free if r not in miss], rots, inreg, wnet, rules, notes_c, sats)
    # ---- 6. forbid zones: repair, else say so
    unmet = _forbid_repair(G, parts, pl, rules, notes_c, inreg, target, rots, rot, sats, set(idx) - set(miss), why, log)
    for x, det, w in unmet:
        log.append("FORBID NOT MET: %s %s -- %s (the floorplan does not fit: move a fixed part, "
                   "shrink the zone, or give the cell room)" % (x, det, w))
        why[x] = why.get(x, "") + "; FORBID NOT MET: " + det
    log.append("local pass: %d parts moved, small-net wirelength %.0f -> %.0f mm" % (moved, gain[0], gain[1]))
    log.append("placed %d free parts (%d satellites at their pins), %d with no room: %s"
               % (len(free) - len(miss), len(placed_sat), len(miss), " ".join(miss)))
    # the grid is counts: a part lifted twice leaves a negative cell that reads as free
    if G.occ.min() < 0 or G.occ_p.min() < 0:
        raise SystemExit("place_init: occupancy grid went negative (a part was unstamped twice) -- "
                         "the placement may overlap; this is a place_init bug")
    return pl, log, why


RULE_W = 10.0       # mm of wirelength a millimetre of broken soft rule is worth (local pass)
SOFT_KINDS = ("decap", "near", "between", "thermal", "apart", "chain", "tight")


def _pin_at(P, r):
    """A decap's pin -- or, when it serves several (`also`), the mean of them."""
    ps = [P.pad(*x.split(".", 1)) for x in [r["pin"]] + list(r.get("also", ()))]
    return np.mean(ps, axis=0)


def _seat(r, P, pl, anc):
    """Where a satellite goes for its rule: just outside its pin, or at its target."""
    if r["kind"] == "decap":
        pin = _pin_at(P, r)
        v = pin - np.asarray(pl[anc][:2])
        return pin + v / (np.hypot(*v) or 1.0) * 1.0
    if "." in r.get("target", ""):
        return P.pad(*r["target"].split(".", 1))
    return np.asarray(pl[anc][:2])


def _local(G, parts, pl, refs, rots, inreg, wnet, rules=(), notes=None, sats=None, passes=3):
    """Detailed placement: a part the legaliser dropped far from its nets (the greedy
    biggest-first drop puts it at the nearest FREE spot, which can be across the board) is
    lifted and dropped again at the free spot nearest its nets' optimum, kept there only if
    its nets get shorter. Nets of 2..WIDE pins, half-perimeter, pair nets x4.

    ⚠ WHY (output_panel intent board, 2026-11-11): the board closed, but small nets the hand
    board keeps within millimetres ran across it -- the buck's SW node 44 mm (hand 9), its
    FB 34 (hand 3.4), DAC_R_FILT 52 (hand 3.6) -- and cost ~90 vias over the hand board's
    count. Same total wirelength; a few parts in the wrong place."""
    pads = {}
    for ref in parts:
        pads[ref] = [(q["net"], q["xy"]) for q in parts[ref]["pads"] if q["net"]]
    members = {}
    for ref, ps in pads.items():
        for nm, _ in ps:
            members.setdefault(nm, set()).add(ref)
    scope = {nm for nm, m in members.items() if 2 <= sum(1 for r in m for n2, _ in pads[r] if n2 == nm) <= WIDE}

    def world(ref):
        x, y, a = pl[ref]
        off = pi._rot([xy for _, xy in pads[ref]], a) if pads[ref] else np.zeros((0, 2))
        return [(nm, np.array([x, y]) + o) for (nm, _), o in zip(pads[ref], off)]

    def cost(nets):
        c = 0.0
        for nm in nets:
            pts = [p for r in members[nm] if r in pl for n2, p in world(r) if n2 == nm]
            if len(pts) >= 2:
                a = np.array(pts)
                c += wnet.get(nm, 1.0) * float(np.ptp(a[:, 0]) + np.ptp(a[:, 1]))
        return c

    # the soft rules each part takes part in: a move that strands a cap off its pin, or a
    # pull-up off its part, costs RULE_W x the millimetres it breaks the rule by
    # (first version without this: caps dragged 30 mm after their nets, 7 -> 19 rules broken)
    rel = {}
    for r in rules:
        if r["kind"] not in SOFT_KINDS:
            continue
        names = {r.get(f) for f in ("ref", "cap") if r.get(f)}
        for f in ("pin", "target"):
            if r.get(f):
                names.add(r[f].split(".")[0])
        for f in ("others", "refs", "a", "b"):
            if isinstance(r.get(f), list):
                names |= set(r[f])
            elif f in ("a", "b") and isinstance(r.get(f), str):
                names.add(r[f].split(".")[0])           # between: a pad or a part
        for nm in r.get("nets") or ():                 # tight: every part on those nets
            names |= members.get(nm, set())
        for n in names:
            rel.setdefault(n, []).append(r)

    def penalty(ref):
        if not rel.get(ref):
            return 0.0
        P = pi.Placed(parts, pl)
        v = 0.0
        for r in rel[ref]:
            try:
                for sl, _, _ in pi.check(r, P, notes or {}):
                    v += r.get("weight", 1.0) * max(0.0, -sl)
            except (KeyError, ValueError):
                pass
        return RULE_W * v

    def total():
        return cost(scope)

    t0 = total()
    moved = set()
    fixed_local = set(pl) - set(refs)
    for _ in range(passes):
        order = sorted(refs, key=lambda r: -cost({nm for nm, _ in pads[r]} & scope))
        changed = False
        for ref in order:
            mine = {nm for nm, _ in pads[ref]} & scope
            if not mine:
                continue
            x, y, a = pl[ref]
            # the anchor that puts each pad nearest the rest of its net
            tg = []
            for nm, p in world(ref):
                if nm not in mine:
                    continue
                # an anchor's own satellites move with it: they are not where it should go
                # (L1's V5_PRE target was its own caps, so it never left them for U5)
                own = {c for c, _ in (sats or {}).get(ref, ())}
                oth = [q for r in members[nm] if r != ref and r not in own and r in pl
                       for n2, q in world(r) if n2 == nm]
                if oth:
                    tg.append(np.mean(oth, axis=0) - (p - np.array([x, y])))
            if not tg:
                continue
            t = np.mean(tg, axis=0)
            if np.hypot(t[0] - x, t[1] - y) < 0.5 and len(pads[ref]) > 2:
                continue
            # ⚠ AN ANCHOR MOVES WITH ITS SATELLITES (output_panel, 2026-11-11): the buck's
            # SW node stayed 42 mm because U5 and L1 each carry caps whose rules a lone move
            # would break; lifted as a group -- the part, then each cap re-seated at its pin
            # -- the move is judged on the whole group's nets and rules.
            # ⚠ ONCE EACH (optical, 2026-11-11): C130 had two rules on U10 (auto_decaps' and the
            # intent's own), the group listed it twice, it was unstamped twice, and the grid's
            # negative count left a hole R33 was dropped into -- inside U10's courtyard.
            group = list(dict.fromkeys([ref] + [c for c, _ in (sats or {}).get(ref, ())
                                                if c in pl and c not in fixed_local]))
            gnets = set()
            for g in group:
                gnets |= {nm for nm, _ in pads[g]} & scope
            c0 = cost(gnets) + sum(penalty(g) for g in group)
            olds = {g: list(pl[g]) for g in group}
            old_xy = pl[ref][:2]
            for g in group:
                mg_, gi_, gj_ = mask(parts[g], pl[g][2])
                _unstamp(G, mg_, gi_, gj_, *G.ij(*pl[g][:2]), grow=halo(parts[g]))
            # ⚠ EACH TURN TRIED ON ITS OWN, THE CHEAPEST KEPT (output_panel, 2026-11-11): the
            # first turn that fitted was taken, and two-pin nets the hand board routes with
            # no via (BOOT, FB, DAC_FILT, SW_GATE) took two -- a part facing the wrong way.
            best_t = None
            # ⚠ A ZONE IS NOT FOR TRADING (output_panel, 2026-11-11): the pass moved L1 28 mm
            # and paid a 9.3 mm breach of the crystal's zone (93 in the penalty) for 2100 of
            # other soft-rule gains -- L1 ended 0.67 mm from Y1. Moves keep forbid zones.
            fz = _apart_forbid(G, parts, pl, ref, rules)
            fr = inreg.get(ref) if fz is None else (fz if inreg.get(ref) is None else fz | inreg.get(ref))
            for rr in rots(ref, a):
                ok = _drop(G, parts, ref, t, [rr], pl, fr)
                placed_g = [ref] if ok else []
                if ok:
                    for c, r in (sats or {}).get(ref, ()):
                        if c not in group or c in placed_g:
                            continue
                        P = pi.Placed(parts, pl)
                        fc = _apart_forbid(G, parts, pl, c, rules)
                        fc = inreg.get(c) if fc is None else (fc if inreg.get(c) is None else fc | inreg.get(c))
                        if _drop_sat(G, parts, c, _seat(r, P, pl, ref), rots(c, olds[c][2]), pl, fc, ref, r):
                            placed_g.append(c)
                        else:
                            ok = False
                            break
                cc = cost(gnets) + sum(penalty(g) for g in group) if ok else None
                if ok and (best_t is None or cc < best_t[0]):
                    best_t = (cc, {g: list(pl[g]) for g in group})
                for g in placed_g:
                    mg_, gi_, gj_ = mask(parts[g], pl[g][2])
                    _unstamp(G, mg_, gi_, gj_, *G.ij(*pl[g][:2]), grow=halo(parts[g]))
                for g in group:
                    pl[g] = list(olds[g])
            ok = best_t is not None
            placed_g = []
            if ok:
                for g in group:
                    pl[g] = best_t[1][g]
                    mg_, gi_, gj_ = mask(parts[g], pl[g][2])
                    _stamp(G, mg_, gi_, gj_, *G.ij(*pl[g][:2]), grow=halo(parts[g]))
                    placed_g.append(g)
            if os.environ.get("PLACE_DEBUG") == ref:
                print("  PLACE_DEBUG %s at %s target %s group %s ok=%s cost %.1f -> %.1f (nets %.1f pen %.1f)" % (
                    ref, old_xy, np.round(t, 1), group, ok, c0, cost(gnets) + sum(penalty(g) for g in group),
                    cost(gnets), sum(penalty(g) for g in group)))
            if ok and cost(gnets) + sum(penalty(g) for g in group) < c0 - 0.5:
                moved.update(group)
                changed = True
                continue
            for g in placed_g:                       # undo: lift what was dropped, put all back
                mg_, gi_, gj_ = mask(parts[g], pl[g][2])
                _unstamp(G, mg_, gi_, gj_, *G.ij(*pl[g][:2]), grow=halo(parts[g]))
            for g in group:
                pl[g] = olds[g]
                mg_, gi_, gj_ = mask(parts[g], pl[g][2])
                _stamp(G, mg_, gi_, gj_, *G.ij(*pl[g][:2]), grow=halo(parts[g]))
        if not changed:
            break
    return len(moved), (t0, total())


def _grow(m, ai, aj, grow, g=GRID):
    k = int(round(grow / g))
    if not k:
        return m, ai, aj
    return binary_dilation(np.pad(m, k), iterations=k), ai + k, aj + k


def _put(arr, m, ai, aj, i, j, sign=1):
    i0, j0 = i - ai, j - aj
    h, w = m.shape
    a0, b0 = max(0, i0), max(0, j0)
    a1, b1 = min(arr.shape[0], i0 + h), min(arr.shape[1], j0 + w)
    if a1 > a0 and b1 > b0:
        arr[a0:a1, b0:b1] += sign * m[a0 - i0:a1 - i0, b0 - j0:b1 - j0].astype(arr.dtype)


def _stamp(G, m, ai, aj, i, j, force=False, grow=0.0):
    """A placed part: its courtyard grown by its halo into G.occ (what later parts' plain
    courtyards must miss), its plain courtyard into G.occ_p (what a later part's own halo
    must miss)."""
    _put(G.occ_p, m, ai, aj, i, j)
    _put(G.occ, *_grow(m, ai, aj, grow, G.g), i, j)


def _unstamp(G, m, ai, aj, i, j, grow=0.0):
    _put(G.occ_p, m, ai, aj, i, j, -1)
    _put(G.occ, *_grow(m, ai, aj, grow, G.g), i, j, -1)


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


def _apart_forbid(G, parts, pl, ref, rules):
    """Cells where ref's courtyard would come within an `apart` / `thermal` rule's distance
    of the other side's PLACED parts (bool grid), or None if no such rule names ref. The
    quadratic stage has no repulsion, so a noise rule acts here: the drop looks for the
    nearest spot clear of it, and falls back to the plain nearest spot when there is none.

    ⚠ WHY (optical, 2026-11-11): as a local-pass penalty alone, the buck stayed beside the
    PHY -- the pass moves one part at a time and every single move out of the clump made the
    nets longer. The rule has to hold when the part is first dropped."""
    out = None
    for r in rules:
        # a hand-written apart/thermal rule is a zone by default; auto_floorplan's edge
        # rules opt out ("forbid": false) -- see its note
        if r["kind"] not in ("apart", "thermal") or not r.get("forbid", True):
            continue
        a = set(pi._refs(r.get("a") or [r["ref"]], parts))
        b = set(pi._refs(r.get("b") or r["others"], parts))
        if ref in a:
            other = b - {ref}
        elif ref in b:
            other = a - {ref}
        else:
            continue
        occ = np.zeros((G.H, G.W), np.int16)
        for o in other:
            if o in pl:
                mk, ai, aj = mask(parts[o], pl[o][2])
                _put(occ, mk, ai, aj, *G.ij(*pl[o][:2]))
        if not occ.any():
            continue
        f = distance_transform_edt(occ == 0) * G.g < float(r.get("min_mm", r.get("apart_mm", 0.0)))
        out = f if out is None else (out | f)
    return out


def _pair_turns(parts, specs, pl, target, rot, rot_of):
    """Rotations for the FREE parts of declared pairs' chains, so each hop's facing pads line
    up. `specs` is a list of diff_pairs specs, decided TOGETHER: a part in several chains
    (output_panel's hub U4 in three) gets one turn that serves all of them, not the last
    spec's. Cost, summed over every hop of every chain: |DP_a - DP_b| + |DM_a - DM_b|
    between facing pads (a pass-through's in-hop and out-hop use different pads), 20 mm for
    crossed rails, and 3 mm x |cos| per hop end whose DP-DM baseline is not square to the
    hop. Exhaustive over the free parts' allowed turns (<= 256 combinations, else {}).

    ⚠ WHY (optical, 2026-11-11): the turn stage scores each pad against its net's centroid,
    and a pass-through clamp (U10, the same two nets on both ends) scores the same in
    every rotation -- it was left turned across the chain, layout's coupled-pair layer
    found "no clear path U7->U10" and handed the pair to the router: 3-5 mm uncoupled.
    Facing it: 1.15 mm."""
    import itertools
    specs = [sp for sp in specs if len(sp.get("nets", ())) == 2
             and len([c for c in sp.get("chain", ()) if c in parts]) >= 2]
    # ONLY PASS-THROUGH PARTS are turned here: a mid-chain part with two pads on each pair
    # net. A chain END (a PHY, a hub, a connector) is turned well by the turn stage's pad
    # pull already -- ⚠ output_panel, 2026-11-11: turning the hub U4 and U14 by this cost
    # took the board's uncoupled 0 -> 15.2 mm.
    def thru(sp, c):
        ch = [x for x in sp["chain"] if x in parts]
        return (c in ch[1:-1] and all(sum(q["net"] == n for q in parts[c]["pads"]) >= 2 for n in sp["nets"]))
    free = list(dict.fromkeys(c for sp in specs for c in sp["chain"]
                              if c in parts and c not in pl and thru(sp, c)))
    if not free:
        return {}
    opts = [rot_of.get(c, [0.0, 90.0, 180.0, 270.0]) for c in free]
    if np.prod([len(o) for o in opts]) > 256:
        return {}

    def pads(c, a, nets):
        xy = np.asarray(pl[c][:2]) if c in pl else target[c]
        off = _pad_off(parts[c], a)
        return {n: [(q["num"], xy + o) for q, o in zip(parts[c]["pads"], off) if q["net"] == n] for n in nets}

    def cross(p1, p2, q1, q2):
        d = lambda a, b, c: (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return (d(p1, p2, q1) * d(p1, p2, q2) < 0) and (d(q1, q2, p1) * d(q1, q2, p2) < 0)

    def chain_cost(sp, ang):
        nets = sp["nets"]
        chain = [c for c in sp["chain"] if c in parts]
        P = {c: pads(c, ang[c] if c in ang else (pl[c][2] if c in pl else rot.get(c, 0.0)), nets) for c in chain}
        cost = 0.0
        used = {c: set() for c in chain}      # a pass-through's in-hop and out-hop use different pads
        for a_, b_ in zip(chain, chain[1:]):
            ends = []
            for n in nets:
                ua = [(k, u) for k, u in P[a_][n] if k not in used[a_]] or P[a_][n]
                ub = [(k, v) for k, v in P[b_][n] if k not in used[b_]] or P[b_][n]
                if not ua or not ub:
                    break
                d, ka, kb, pa, pb = min((float(np.hypot(*(u - v))), k1, k2, tuple(u), tuple(v))
                                        for k1, u in ua for k2, v in ub)
                cost += d
                used[a_].add(ka)
                used[b_].add(kb)
                ends.append((np.asarray(pa), np.asarray(pb)))
            if len(ends) == 2 and cross(ends[0][0], ends[0][1], ends[1][0], ends[1][1]):
                cost += 20.0
            if len(ends) == 2:
                # FACING: each end's DP-DM baseline square to the hop. A pad pair stacked
                # along the hop (U10 at 0 deg under U7) leaves one rail behind the other, and
                # the router's pair ran 2.4 mm apart there converging (optical vI8).
                hop = (ends[0][1] + ends[1][1]) / 2.0 - (ends[0][0] + ends[1][0]) / 2.0
                hn = float(np.hypot(*hop)) or 1.0
                for side in (0, 1):
                    base = ends[0][side] - ends[1][side]
                    bn = float(np.hypot(*base)) or 1.0
                    cost += 3.0 * abs(float(base @ hop)) / (bn * hn)
        return cost

    best = None
    for combo in itertools.product(*opts):
        ang = dict(zip(free, combo))
        cost = sum(chain_cost(sp, ang) for sp in specs)
        if os.environ.get("PAIR_DEBUG"):
            print("  PAIR_DEBUG %s cost %.2f" % (ang, cost))
        if best is None or cost < best[0] - 1e-6:
            best = (cost, ang)
    return dict(best[1]) if best else {}


def _lift(G, parts, pl, r):
    m, ai, aj = mask(parts[r], pl[r][2])
    _unstamp(G, m, ai, aj, *G.ij(*pl[r][:2]), grow=halo(parts[r]))
    return pl.pop(r)


def _put_back(G, parts, pl, r, pose):
    pl[r] = list(pose)
    m, ai, aj = mask(parts[r], pl[r][2])
    _stamp(G, m, ai, aj, *G.ij(*pl[r][:2]), grow=halo(parts[r]))


def _forbid_repair(G, parts, pl, rules, notes, inreg, target, rots, rot, sats, free, why, log):
    """Every `forbid` apart/thermal rule checked on the finished placement. A breaking part
    (either side, free ones only) gets one repair: lifted with its satellites and dropped
    inside its zone near its target; failing that, the free parts nearest the target are
    lifted too (up to six) and the drop retried, then they are re-dropped. Anything that
    does not land reverts. Returns the breaches left: [(subject, detail, why)].

    ⚠ WHY (lead, 2026-11-11): optical's buck cell fell back to 7.3 mm from the PHY crystal
    against a 10 mm forbid, and that was only visible as a soft line in the score. A zone
    the legaliser could not honour is the intent author's to know about: the floorplan
    does not fit."""
    def breaches():
        P = pi.Placed(parts, pl)
        out = []
        for r in rules:
            if r["kind"] in ("apart", "thermal") and r.get("forbid", True):
                try:
                    for sl, subj, det in pi.check(r, P, notes):
                        if sl < -0.05:
                            out.append((sl, subj, det, r))
                except (KeyError, ValueError):
                    pass
        return sorted(out, key=lambda t: t[0])

    def zone(x):
        fz, f0 = _apart_forbid(G, parts, pl, x, rules), inreg.get(x)
        return f0 if fz is None else (fz if f0 is None else fz | f0)

    def attempt(x):
        if x not in free or x not in pl:
            return False
        own = [c for c, _ in (sats or {}).get(x, ()) if c in pl and c in free]
        own = list(dict.fromkeys(own))
        olds = {g: list(pl[g]) for g in [x] + own}
        for g in [x] + own:
            _lift(G, parts, pl, g)
        t = target.get(x, np.asarray(olds[x][:2]))
        freed = {}
        ok = _drop(G, parts, x, t, rots(x, rot.get(x, olds[x][2])), pl, zone(x), near_mm=WINDOW)
        if not ok:
            near = sorted((float(np.hypot(*(np.asarray(pl[p][:2]) - t))), p) for p in free
                          if p in pl and p not in olds and p not in sats)
            for _, p in near[:6]:
                freed[p] = list(pl[p])
                _lift(G, parts, pl, p)
            ok = _drop(G, parts, x, t, rots(x, rot.get(x, olds[x][2])), pl, zone(x), near_mm=WINDOW)
        placed = [x] if ok else []
        if ok:
            for c, r in (sats or {}).get(x, ()):
                if c in olds and c not in pl:
                    P = pi.Placed(parts, pl)
                    if _drop_sat(G, parts, c, _seat(r, P, pl, x), rots(c, olds[c][2]), pl, inreg.get(c), x, r):
                        placed.append(c)
                    else:
                        ok = False
                        break
        if ok:
            for p in freed:
                if _drop(G, parts, p, target.get(p, np.asarray(freed[p][:2])), rots(p, freed[p][2]), pl, zone(p))                         or _drop(G, parts, p, target.get(p, np.asarray(freed[p][:2])), rots(p, freed[p][2]), pl,
                                 inreg.get(p)):
                    placed.append(p)
                else:
                    ok = False
                    break
        if not ok:
            for g in placed:
                _lift(G, parts, pl, g)
            for g, pose in list(olds.items()) + list(freed.items()):
                _put_back(G, parts, pl, g, pose)
            return False
        why[x] = why.get(x, "") + "; re-dropped clear of its forbid zone" + (
            " (lifted %s)" % " ".join(freed) if freed else "")
        return True

    first = breaches()
    tried = set()
    for sl, subj, det, r in first:
        other = det.split(" from ")[-1].split(",")[0].strip() if " from " in det else None
        for x in (subj, other):
            if x and x not in tried:
                tried.add(x)
                if attempt(x):
                    break
    left = breaches()
    if first:
        log.append("forbid zones: %d breach(es) before repair, %d after" % (len(first), len(left)))
    seen, out = set(), []
    for sl, subj, det, r in left:
        if subj not in seen:
            seen.add(subj)
            out.append((subj, det, r.get("why", "")))
    return out


def _drop_sat(G, parts, c, t, rots, pl, forbid, anchor, rule, near_mm=None):
    """_drop for a satellite. A DECAP may stand inside its own anchor's escape halo (down to
    HALO_SMALL off the courtyard): the halo is room for the IC's signal pins to get out, and
    a supply pin's cap is what the hand board puts against the courtyard at that very pin.

    ⚠ WHY (optical, 2026-11-11): U6 (LQFP-176, halo 2.5) kept its whole ring out --
    C117 seated 24 mm from U6.136 because the 2.5 mm ring plus the cap did not fit between
    U6 and the compute region's edge, where the hand board has the cap 1 mm off the body."""
    big = rule is not None and rule["kind"] == "decap" and anchor in pl and halo(parts[anchor]) > HALO_SMALL
    if big:
        m, ai, aj = mask(parts[anchor], pl[anchor][2])
        ij = G.ij(*pl[anchor][:2])
        _put(G.occ, *_grow(m, ai, aj, halo(parts[anchor]), G.g), *ij, -1)
        _put(G.occ, *_grow(m, ai, aj, HALO_SMALL, G.g), *ij)
    try:
        return _drop(G, parts, c, t, rots, pl, forbid, near_mm)
    finally:
        if big:
            _put(G.occ, *_grow(m, ai, aj, HALO_SMALL, G.g), *ij, -1)
            _put(G.occ, *_grow(m, ai, aj, halo(parts[anchor]), G.g), *ij)


def _drop(G, parts, ref, t, rots, pl, forbid=None, near_mm=None):
    """Put ref at the free grid spot nearest t (first rot that fits, nearer wins). near_mm:
    give up (False) rather than go further than that -- a satellite that cannot keep its
    noise zone AND its rule takes its rule (the caller retries without the zone)."""
    best = None
    rads = (WINDOW, WINDOW * 3, 1e9) if near_mm is None else (min(WINDOW, near_mm + 1.0), near_mm + 1.0)
    for rad in rads:
        for a in rots:
            m, ai, aj = mask(parts[ref], a)
            ti, tj = G.ij(*t)
            R = int(rad / G.g)
            i0, i1 = max(0, ti - R), min(G.H, ti + R + 1)
            j0, j1 = max(0, tj - R), min(G.W, tj + R + 1)
            sub = G.occ[i0:i1, j0:j1] > 0
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
            col2 = _collide((G.occ_p[i0:i1, j0:j1] > 0).astype(np.float32), mg, gi, gj)
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
    ap.add_argument("--strict", action="store_true", help="exit 3 if a forbid zone is not met")
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
    unmet = [line for line in log if line.startswith("FORBID NOT MET")]
    if unmet:
        print("place_init: %d forbid zone(s) NOT MET -- the floorplan does not fit as written" % len(unmet),
              file=sys.stderr)
        if a.strict:
            return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
