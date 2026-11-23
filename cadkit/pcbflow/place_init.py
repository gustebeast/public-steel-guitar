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
IC_EDGE_HALO = os.environ.get("PCBFLOW_IC_EDGE_HALO", "1") == "1"   # see _drop
# ⚠ A FINE-PITCH SIGNAL PIN'S ONLY WAY OUT IS STRAIGHT ON (brain_board mV40, 2026-11-18):
# U221 (WSON-8, 0.5 mm) -- C327, its VBIAS decap, seated 1 mm in front of pin 4 and across
# pin 3: EN5 boxed in by +5V_RAW, +3V3D, the GND pad and the cap, no via allowed in a pasted
# land. With PCBFLOW_DECAP_SLIDE=1 the decap's SEAT slides along the pin row, off the exit
# of any neighbouring fine-pitch signal pin (other-net neighbour closer than LANE_PITCH, net
# under LANE_RAIL_PINS pins, anchor up to LANE_MAX_PADS). Holding those lanes as grid masks
# instead (PIN_LANES, mV41r) moved 21 parts for one net, overflow 7.71 -> 10.53, and seating a
# `near` satellite on its `between` line (BETWEEN_SEAT, mV45q) 10.34: both deleted 11-18.
LANE_PITCH, LANE_LEN, LANE_CLR, LANE_RAIL_PINS, LANE_MAX_PADS = 0.8, 1.2, 0.3, 12, 16
DECAP_SLIDE = os.environ.get("PCBFLOW_DECAP_SLIDE", "0") == "1"


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
        self.out = ~inside                          # the outline alone (IC_EDGE_HALO in _drop)
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


def cu_grids(G, items, clr=None):
    """G.cu: {(layer, net, own): bool grid} -- each declared net's copper per layer ("F" / "B" /
    "I" inner / "A" a via, every layer), grown by the net clearance and half a cell. Set on G."""
    clr = pi.PAD_CU_CLEAR if clr is None else clr
    out = {}
    pts = np.stack([G.X.ravel(), G.Y.ravel()], axis=1)
    grow = clr + G.g * 0.71
    for net, lay, kind, g, own in items:
        L = "A" if lay == pi.ALL_CU else ("F" if lay == "F.Cu" else ("B" if lay == "B.Cu" else "I"))
        if kind == "seg":
            a, b, hw = g
            lo, hi = np.minimum(a, b) - hw - grow, np.maximum(a, b) + hw + grow
            r = hw + grow
        else:
            a, r0 = g
            b = a
            lo, hi = a - r0 - grow, a + r0 + grow
            r = r0 + grow
        sel = ((pts[:, 0] >= lo[0]) & (pts[:, 0] <= hi[0]) & (pts[:, 1] >= lo[1]) & (pts[:, 1] <= hi[1]))
        if not sel.any():
            continue
        hit = np.zeros(len(pts), bool)
        hit[sel] = pi._seg_dist(pts[sel], a, b) <= r
        key = (L, net, own)
        cur = out.get(key)
        hv = hit.reshape(G.H, G.W)
        out[key] = hv if cur is None else (cur | hv)
    G.cu = out
    G.cu_any = None
    if out:
        G.cu_any = np.zeros((G.H, G.W), bool)
        for v in out.values():
            G.cu_any |= v
    return out


def pad_mask(part, rot, m_shape, ai, aj, keep, g=GRID):
    """The part's pads that `keep(q)` selects, rasterised in mask()'s frame (shape m_shape, anchor
    ai, aj), half a cell grown: None if none is selected."""
    qs = [q for q in part["pads"] if q.get("size") and keep(q)]
    if not qs:
        return None
    X, Y = np.meshgrid((np.arange(m_shape[1]) - aj) * g, (np.arange(m_shape[0]) - ai) * g)
    pts = np.stack([X.ravel(), Y.ravel()], axis=1)
    out = np.zeros(len(pts), bool)
    for q in qs:
        w, h = q["size"][:2]
        c = pi._rot([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]], q.get("rot", 0.0)) + np.asarray(q["xy"], float)
        out |= pi._inside(pi._rot(c, rot), pts)
    return binary_dilation(out.reshape(m_shape), iterations=1)


def _cu_free(G, part, ref, a, m, ai, aj, i0, i1, j0, j1):
    """bool (window): where the part's other-net pads keep off declared copper (all True if none)."""
    if not getattr(G, "cu", None):
        return None
    if not G.cu_any[i0:i1, j0:j1].any():
        return None
    side = "B" if part.get("side", "F") == "B" else "F"
    ok = None
    for (L, net, own), grid in G.cu.items():
        if ref in own:
            continue
        sub = grid[i0:i1, j0:j1]
        if not sub.any():
            continue
        on = ((lambda q: True) if L == "A" else (lambda q: bool(q.get("tht"))) if L == "I" else
              (lambda q: bool(q.get("tht")) or L == side))
        pm = pad_mask(part, a, m.shape, ai, aj, lambda q: on(q) and q.get("net") != net)
        if pm is None:
            continue
        f = _collide(sub.astype(np.float32), pm, ai, aj) < 0.5
        ok = f if ok is None else (ok & f)
    return ok


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


def _pin_cap(rule, parts):
    """⚠ A CAP `near` ITS IC's SUPPLY PIN MAY STAND IN THAT IC's RING, AS A `decap` MAY
    (output_board mN, 2026-11-14). The project ruled the H743's 13 VDD caps as `near`
    U1.<pin>, 3.0 mm (quality A2), so auto_decaps left them as the author's -- and only a
    `decap` rule was let into its IC's escape ring (_drop_sat). U1's ring is 2.5 mm (176 pins)
    and its pads sit 1.00 inside its courtyard, so every cap seated at 1.00 + 2.67 = 3.67 mm:
    all 13 broken by the placer's own ring, not by the footprints (against the courtyard they
    reach 1.0). Only the drop changes: re-typing the rules as `decap` moved them into the
    decap stage and reshuffled the board (196 of 377 parts moved, a decap stranded 34 mm
    off U212) -- the rule kind, and so the seating order, stay as written."""
    if rule is None or rule["kind"] != "near":
        return False
    c, t = rule.get("ref", ""), rule.get("target", "")
    if not (c[:1] == "C" and c[1:2].isdigit() and "." in t and c in parts):
        return False
    ic, num = t.split(".", 1)
    if ic not in parts or len(parts[ic]["pads"]) <= IC_PADS:
        return False
    net = next((q["net"] for q in parts[ic]["pads"] if q["num"] == num), None)
    return bool(net) and net in {q["net"] for q in parts[c]["pads"]}


def place(parts, notes, rules, keep=()):
    """Free-anchor `group` cells are placed whole: each becomes one composite part (its
    anchor's ref) for every stage, its members expanded from the anchor's pose at the end.

    ⚠ WHY (lead, 2026-11-11, for the re-layout): a designed cell -- a buck laid out round
    its pins, a PHY with its decap column -- is the design; only WHERE it goes is a
    placement choice. A group needed a fixed anchor before, so a cell had to be pinned or
    dissolved into free parts that the legaliser then scattered."""
    back = pi.back_refs(rules)
    if back:
        return _place_two_sided(parts, notes, rules, keep, back)
    fixed0 ={r["ref"] for r in rules if r["kind"] in ("fixed", "pin", "panel")} | set(keep)
    cells = {r["anchor"]: r["members"] for r in rules if r["kind"] == "group" and r["anchor"] not in fixed0}
    if not cells:
        return _place_bus(parts, notes, rules, keep)
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
    pl, log, why = _place_bus(P2, notes, R2, keep)
    for a, ms in cells.items():
        if a not in pl:
            # the composite found NO ROOM (its diagnosis is already in the log): its members
            # stay unplaced with it, so the flow reports the one stop, not a KeyError (c1,
            # 2026-11-22: the LM5122 cell's U220 was crowded out by L204 and C201)
            log.append("NO ROOM: cell %s (+%d members) unplaced with its anchor" % (a, len(ms)))
            continue
        ax, ay, ar = pl[a]
        for m, (dx, dy, dr) in ms.items():
            o = pi._rot([[dx, dy]], ar)[0]
            pl[m] = [round(ax + float(o[0]), 4), round(ay + float(o[1]), 4), (ar + dr) % 360.0]
            why[m] = "group: %s's cell, placed whole (free anchor)" % a
    log.append("free-anchor cells placed whole: %s" % " ".join("%s(+%d)" % (a, len(ms)) for a, ms in cells.items()))
    return pl, log, why


BACK_ONLY = ("outline", "hole", "current")       # kinds that bind the back pass as they are
GHOST = 0.02                                       # mm: a front SMD part's mark on the back grid
THT_GROW = 0.3                                     # mm round a through pad, both sides


def _rule_refs(r):
    """Every ref a rule names (ref / cap / the lists / pin and target strings)."""
    out = set()
    for f in ("ref", "cap"):
        if isinstance(r.get(f), str):
            out.add(r[f])
    for f in ("pin", "target"):
        if isinstance(r.get(f), str):
            out.add(r[f].split(".", 1)[0])
    for f in ("refs", "others", "a", "b"):
        if isinstance(r.get(f), list):
            out |= set(r[f])
        elif isinstance(r.get(f), str) and f in ("a", "b"):
            out.add(r[f].split(".", 1)[0])
    if r.get("kind") == "group":
        out.add(r["anchor"])
        out |= set(r["members"])
    return out


def _ghost(part):
    """A front part as the BACK grid sees it: its pads (the nets' springs) and, for a through-
    hole part, its through pads as the obstacle -- they pierce the board. An SMD front part
    leaves only a GHOST-sized mark: the back face under it is free."""
    tht = [q for q in part["pads"] if q.get("tht")]
    if not tht and len(part["pads"]) > IC_PADS:
        # ⚠ A FRONT IC'S ESCAPE BAND IS NOT FREE ON THE BACK (ob3, 2026-11-13): its decaps,
        # seated "at their pins" on the back, sat under U1's pad ring -- where its escape vias
        # go, and the router bans a via near ANY pad on any layer (52 open, from 50). Each pad
        # blocks its own size plus the IC's halo; the middle under the body stays free.
        g = halo(part)
        sq = []
        for q in part["pads"]:
            r = max(q["size"]) / 2.0 + g
            x, y = q["xy"]
            sq.append([[x - r, y - r], [x + r, y - r], [x + r, y + r], [x - r, y + r]])
        return dict(part, crtyd=sq[0], crtyd_multi=sq, n_own=0)
    if tht:
        xs = [q["xy"][0] for q in tht]
        ys = [q["xy"][1] for q in tht]
        r = max(max(q["size"]) for q in tht) / 2.0 + THT_GROW
        cy = [[min(xs) - r, min(ys) - r], [max(xs) + r, min(ys) - r],
              [max(xs) + r, max(ys) + r], [min(xs) - r, max(ys) + r]]
    else:
        cy = [[-GHOST, -GHOST], [GHOST, -GHOST], [GHOST, GHOST], [-GHOST, GHOST]]
    return dict(part, crtyd=cy, crtyd_multi=None, n_own=0)


def _place_two_sided(parts, notes, rules, keep, back):
    """Front first, exactly as a one-sided board but without the back parts; then the back
    parts on a grid of their own, every front part FIXED where the front pass put it.

    ⚠ OPT-IN, PER INTENT (lead, 2026-11-13): only a `side` rule with side "B" sends a part
    here (pi.back_refs). The output board's courtyards filled 0.55 of 68 x 100 against the
    0.41-0.47 a dense board routes at; its LQFP-176 and jack cannot shrink, its box cannot
    grow, and layout.py already turns back_refs over. The back pass:
      * sees the outline, holes and cutouts (both faces) and only the keep-outs and height
        zones marked side "B" -- a front keep-out (a module's stack) is the front's;
      * sees a front part as _ghost: through pads block, SMD bodies do not;
      * keeps every rule that names a back part (near / decap / apart / chain / rot) and
        every `tight` loop, so a back decap still goes under its pin.
    The parts are mirrored first (pi.mirror_back), so the back pass and every later check see
    the geometry layout will build."""
    parts = pi.mirror_back(parts, back)
    bset = set(back)
    front = {r: p for r, p in parts.items() if r not in bset}
    rf = []
    for r in rules:
        if r["kind"] == "side" and r.get("ref") in bset:
            continue
        if _rule_refs(r) & bset:
            if r["kind"] in ("near", "decap", "apart", "chain", "rot", "group", "in_region"):
                continue
            r = dict(r)
            for f in ("refs", "others", "a", "b"):
                if isinstance(r.get(f), list):
                    r[f] = [x for x in r[f] if x not in bset]
        if r["kind"] in ("keepout", "height") and r.get("side") == "B":
            continue
        rf.append(r)
    plF, logF, whyF = place(front, notes, rf, keep)

    P2 = {r: _ghost(p) for r, p in front.items()}
    P2.update({r: parts[r] for r in back})
    rb = [dict(kind="fixed", ref=r, xy=[plF[r][0], plF[r][1]], rot=plF[r][2], hold="snapshot", why="front pass",
               src="place_init two-sided") for r in sorted(front)]
    for r in rules:
        k = r["kind"]
        if k in BACK_ONLY or k == "tight":
            rb.append(r)
        elif k in ("keepout", "height"):
            if r.get("side") == "B":
                rb.append(r)
        elif k == "side":
            continue
        elif k == "apart":
            # only a separation BETWEEN two back parts: one judged against a front ghost
            # measures the ghost, not the part (ob3: "U5 7.29 from U8", both front)
            a_ = set(pi._refs(r.get("a") or [r["ref"]], parts))
            b_ = set(pi._refs(r.get("b") or r["others"], parts))
            if a_ & bset and b_ & bset:
                rb.append(dict(r, a=sorted(a_ & bset), b=sorted(b_ & bset), others=None, ref=None))
        elif _rule_refs(r) & bset and k in ("near", "decap", "chain", "rot"):
            rb.append(r)
    plB, logB, whyB = place(P2, notes, rb, ())
    pl = dict(plF)
    why = dict(whyF)
    for r in back:
        pl[r] = plB[r]
        why[r] = "BACK side: " + whyB.get(r, "")
    log = list(logF) + ["two-sided: %d part(s) on the back, placed after the front: %s"
                        % (len(back), " ".join(back))] + ["back: " + x for x in logB if not x.startswith("fixed ")]
    return pl, log, why


BUS_MIN = 4       # two-pin nets between the same two ICs that make a parallel bus


def _buses(parts):
    """[(anchor, partner, nets)]: BUS_MIN or more two-pin nets joining the same two ICs (each
    over IC_PADS pads) -- ULPI, SAI, a parallel bus. The anchor is the one with more pads."""
    nets = {}
    for ref, p in parts.items():
        for q in p["pads"]:
            if q["net"] and q["num"]:
                nets.setdefault(q["net"], []).append((ref, q["num"]))
    by = {}
    for nm, pins in nets.items():
        rs = sorted({r for r, _ in pins})
        if len(pins) == 2 and len(rs) == 2 and all(len(parts[r]["pads"]) > IC_PADS for r in rs):
            by.setdefault(tuple(rs), []).append(nm)
    out = []
    for (a, b), ns in sorted(by.items()):
        if len(ns) >= BUS_MIN:
            if len(parts[b]["pads"]) > len(parts[a]["pads"]):
                a, b = b, a
            out.append((a, b, sorted(ns)))
    return out


def _bus_len(parts, pl, nets):
    P = pi.Placed(parts, pl)
    tot = 0.0
    for nm in nets:
        pts = [pt for r in parts if r in pl for pt in P.pads_on(r, nm)]
        if len(pts) == 2:
            tot += float(np.hypot(*(pts[0] - pts[1])))
    return tot


def _place_bus(parts, notes, rules, keep=()):
    """_place_grow, then ONE retry per parallel bus whose anchor faces the wrong way.

    ⚠ A FAST BUS TURNS ITS ANCHOR -- AFTER THE PARTNER HAS A SEAT (output_board, 2026-11-13).
    U1's twelve ULPI pins sat on the side facing the power band; the PHY was legalised 19 mm
    off to the side and CK / DIR / NXT / STP went open (ob8). Turning U1 by hand so that side
    faced the PHY's seat left only CK open (ob10). Weighting the bus in the TURN stage did not
    do it (ob11): the turn judges against the quadratic targets, which pull the partner into
    the anchor's bus side even where its region forbids it. So the turn is judged where the
    partner actually LANDED: the anchor's rotation that brings its bus pins' centroid nearest
    the partner is tried, and kept only if the bus gets shorter and no part loses its seat.
    A board whose buses already face their partners never retries: identical."""
    pl, log, why = _place_grow(parts, notes, rules, keep)
    fixed = {r["ref"] for r in rules if r["kind"] in ("fixed", "pin", "panel", "rot")} | set(keep)
    for a, b, ns in _buses(parts):
        if a in fixed or a not in pl or b not in pl:
            continue
        x, y, r0 = pl[a]
        sel = [q for q in parts[a]["pads"] if q["net"] in ns]

        def face(rot):
            c = (_pad_off(dict(parts[a], pads=sel), rot)).mean(axis=0) + (x, y)
            return float(np.hypot(*(c - np.asarray(pl[b][:2]))))
        best = min((0.0, 90.0, 180.0, 270.0), key=face)
        if abs((best - r0 + 180.0) % 360.0 - 180.0) < 0.5:
            continue
        before = _bus_len(parts, pl, ns)
        rules2 = list(rules) + [{"kind": "rot", "ref": a, "allowed": [best], "hard": True,
                                 "src": "place_init bus turn", "why": "%s's bus to %s" % (a, b)}]
        pl2, log2, why2 = _place_grow(parts, notes, rules2, keep)
        after = _bus_len(parts, pl2, ns) if a in pl2 and b in pl2 else float("inf")
        if len(pl2) >= len(pl) and after < before:
            log2.append("BUS TURN: %s %g -> %g, its %d-net bus to %s %.0f -> %.0f mm"
                        % (a, r0, best, len(ns), b, before, after))
            pl, log, why = pl2, log2, why2
            why[a] = "bus turn: its %d-net bus faces %s (%s)" % (len(ns), b, why.get(a, ""))
        else:
            log.append("BUS TURN TRIED: %s %g -> %g -- bus %.0f -> %.0f mm, %d -> %d seated; kept %g"
                       % (a, r0, best, before, after, len(pl), len(pl2), r0))
    return pl, log, why


GROWN = {}        # region name -> grown poly, from the last place() (main writes it beside --out)


def _place_grow(parts, notes, rules, keep=()):
    """_place, and once more with a region edge grown when a TANGLE HINT says the region's
    edge is what keeps a fine-pitch IC in its tangled turn.

    ⚠ A REGION IS THE AUTHOR'S FLOORPLAN (lead, 2026-11-12): the grow may not undo it.
    * Only the edge nearest the stranded satellite's pin, and only by its shortfall +
      GROW_PAD.
    * Never into another region, and never within any `apart` / `thermal` distance (forbid
      zones included) of the other side's placed parts.
    * The grown run is kept only if the anchor took the untangled turn and the satellite
      is no longer stranded; else the floorplan stands and it stays a hint.
    * Every grow, blocked grow and kept-as-written is a log line (GROW ...), which
      place_flow copies into report.md.
    motor_ctrl from footprints, `logic` band back at x = 6: U4 turns 270 -> 0 on its own."""
    hint_out = []
    pl, log, why = _place(parts, notes, rules, keep, hint_out)
    if not hint_out:
        return pl, log, why
    regions = {r["name"]: r for r in rules if r["kind"] == "region"}
    P = pi.Placed(parts, pl)
    grows = []
    for h in hint_out:
        for c, short, at in h["stranded"]:
            names = sorted({r["region"] for r in rules if r["kind"] == "in_region"
                            and c in r.get("refs", ()) and r["region"] in regions}) or \
                sorted({r["region"] for r in rules if r["kind"] == "in_region"
                        and h["anchor"] in r.get("refs", ()) and r["region"] in regions})
            if not names:
                log.append("GROW BLOCKED: %s/%s is in no region -- a region is not what strands it; "
                           "stays a hint" % (h["anchor"], c))
                continue
            name = names[0]
            poly = np.asarray(regions[name]["poly"], float)
            # the room the satellite needs, not its shortfall: Y1 (4.2 x 3.5) was 1.7 mm past its
            # `near`, but seating it off U4.5 at all takes its narrow side + a seat gap past the pin
            # (a 2.2 mm grow turned U4 and left Y1 where it was)
            cy_ = np.asarray(parts[c]["crtyd"] or [[0, 0], [1, 1]], float)
            depth = float(np.min(np.ptp(cy_, axis=0)))
            ok, msg, new = _grow_edge(poly, np.asarray(at, float), short + GROW_PAD, name, regions, rules,
                                      parts, pl, P, reach=SEAT_GAP + depth + GROW_PAD)
            if not ok:
                log.append("GROW BLOCKED: region %s, %s (for %s/%s); stays a hint" % (name, msg, h["anchor"], c))
                continue
            regions[name] = dict(regions[name], poly=new)
            grows.append((h, c, name, msg, new))
    if not grows:
        return pl, log, why
    rules2 = [dict(r) for r in rules]
    for _, _, name, _, new in grows:
        for r in rules2:
            if r["kind"] == "region" and r["name"] == name:
                r["poly"] = new
    # ⚠ THE ROOM IS THE SATELLITE'S, NOT THE ANCHOR'S (motor_ctrl, 2026-11-12): with the band
    # grown 4.3 mm west for Y1, the quadratic stage pulled U4 itself 1.9 mm west into it (its
    # nets pull that way), and Y1 stranded again at turn 0. The anchor is held where the first
    # run put it -- a square of its courtyard's long side + HOLD_PAD, so every turn fits.
    held_at = []
    for h in {g[0]["anchor"]: g[0] for g in grows}.values():
        a_ = h["anchor"]
        cy_ = np.asarray(parts[a_]["crtyd"] or [[0, 0], [1, 1]], float)
        half = float(np.max(np.ptp(cy_, axis=0))) / 2.0 + HOLD_PAD
        x_, y_ = pl[a_][:2]
        nm_ = "_hold_" + a_
        bx0, by0, bx1, by1 = x_ - half, y_ - half, x_ + half, y_ + half
        for r in rules2:
            if r["kind"] == "in_region" and a_ in r.get("refs", ()):
                # ...and still inside its own region (f24: U4 turned and sat 0.19 mm past `logic`)
                rp = np.asarray([q for q in rules2 if q["kind"] == "region" and q["name"] == r["region"]][0]["poly"], float)
                bx0, by0 = max(bx0, rp[:, 0].min()), max(by0, rp[:, 1].min())
                bx1, by1 = min(bx1, rp[:, 0].max()), min(by1, rp[:, 1].max())
                r["refs"] = [x for x in r["refs"] if x != a_]
        rules2.append({"kind": "region", "name": nm_, "hard": True,
                       "poly": [[bx0, by0], [bx1, by0], [bx1, by1], [bx0, by1]]})
        rules2.append({"kind": "in_region", "refs": [a_], "region": nm_, "hard": True})
        held_at.append("%s held at (%.1f, %.1f)" % (a_, x_, y_))
    pl2, log2, why2 = _place(parts, notes, rules2, keep, [])
    P2 = pi.Placed(parts, pl2)
    good = True
    for h, c, name, msg, _ in grows:
        # ⚠ THE RETRY CAN LOSE THE ANCHOR (output_board ob9, 2026-11-13): held in its square,
        # U14 found no room and was not in pl2 -- a KeyError killed the flow. No seat is
        # "did not turn": the grow failed and the floorplan stands, as for any other miss.
        if h["anchor"] not in pl2:
            good = False
            log.append("GROW TRIED: region %s, %s -- %s found no room in the retry; the floorplan "
                       "stands as written" % (name, msg, h["anchor"]))
            continue
        turned = abs((pl2[h["anchor"]][2] - h["to"] + 180.0) % 360.0 - 180.0) < 0.5
        r_ = [r for r in rules if (r.get("ref") == c or r.get("cap") == c) and r["kind"] in ("near", "decap")]
        try:
            held = all(min(x[0] for x in pi.check(r, P2, notes)) >= -0.05 for r in r_)
        except (KeyError, ValueError):
            held = False
        if not (turned and held):
            good = False
            log.append("GROW TRIED: region %s, %s -- %s %s, %s %s; the floorplan stands as written" % (
                name, msg, h["anchor"], "turned" if turned else "did not turn to %g" % h["to"],
                c, "held" if held else "still stranded"))
    if not good:
        return pl, log, why
    GROWN.clear()
    GROWN.update({name: new for _, _, name, _, new in grows})
    for h, c, name, msg, _ in grows:
        log2.append("GROW: region %s, %s -- for %s (%s %g -> %g, %d -> %d crossing escapes; %s)" % (
            name, msg, c, h["anchor"], h["rot"], h["to"], h["cross"][0], h["cross"][1], "; ".join(held_at)))
    return pl2, log2, why2


def _grow_edge(poly, at, d, name, regions, rules, parts, pl, P, reach=0.0):
    """Move the polygon edge nearest `at` outward by d mm -- or further, until the edge is
    `reach` mm beyond `at` -- if that keeps to the floorplan. -> (ok, what, new_poly)."""
    n = len(poly)
    best = None
    for k in range(n):
        a, b = poly[k], poly[(k + 1) % n]
        v = b - a
        L = float(np.hypot(*v))
        if L < 1e-9:
            continue
        t = float(np.clip(np.dot(at - a, v) / (L * L), 0.0, 1.0))
        dist = float(np.hypot(*(at - (a + t * v))))
        if best is None or dist < best[0]:
            best = (dist, k, v / L)
    _, k, u = best
    nrm = np.array([u[1], -u[0]])
    a, b = poly[k], poly[(k + 1) % n]
    if pi._inside(poly, ((a + b) / 2.0 + nrm * 0.01)[None])[0]:
        nrm = -nrm                                     # outward
    d = max(d, float(np.dot(at, nrm)) + reach - float(np.dot(a, nrm)))
    if abs(nrm[0]) > 0.99:
        side, axis = ("+X" if nrm[0] > 0 else "-X"), 0
    elif abs(nrm[1]) > 0.99:
        side, axis = ("+Y" if nrm[1] > 0 else "-Y"), 1
    else:
        side, axis = "edge %d" % k, None
    what = ("edge %s %.2f -> %.2f (%.1f mm)" % (side, a[axis], a[axis] + nrm[axis] * d, d)
            if axis is not None else "%s by %.1f mm" % (side, d))
    g = np.linspace(0.02, 0.98, 25)
    S = np.array([a + (b - a) * s_ + nrm * d * t_ for s_ in g for t_ in g])
    for nm, r in regions.items():
        if nm != name and pi._inside(np.asarray(r["poly"], float), S).any():
            return False, "%s would run into region %s" % (what, nm), None
    members = {x for r in rules if r["kind"] == "in_region" and r["region"] == name for x in r.get("refs", ())}
    for r in rules:
        if r["kind"] not in ("apart", "thermal"):
            continue
        A = set(pi._refs(r.get("a") or [r["ref"]], parts))
        B = set(pi._refs(r.get("b") or r.get("others") or [], parts))
        dmin = float(r.get("min_mm", r.get("apart_mm", 0.0)))
        for mine, other in ((A, B), (B, A)):
            if not (mine & members):
                continue
            for o in other - members:
                if o not in pl:
                    continue
                cy = np.asarray(P.crtyd(o), float)
                if len(cy) < 3:
                    continue
                dd = min(float(np.min(np.hypot(*(S - q).T))) for q in cy)
                if pi._inside(cy, S).any() or dd < dmin:
                    return False, "%s would come %.1f mm from %s, inside a %g mm apart rule" % (
                        what, dd, o, dmin), None
    new = poly.copy()
    new[k] = a + nrm * d
    new[(k + 1) % n] = b + nrm * d
    return True, what, [[round(float(x), 3), round(float(y), 3)] for x, y in new]


def _near_reach(parts, rules, pl):
    """⚠ A HARD `near` ITS SUBJECT'S REGION CANNOT REACH FAILS HERE, BY NAME (output_board
    mN, 2026-11-14): U17 was held in one region and its rule's target sat in another; the
    placer met what it could by dragging the target and reported nothing. The rule is
    checked against the regions before anything is placed: a subject held in a region (its
    in_region rules) whose nearest point is further from the target -- a placed part, or
    the region the target is held in -- than the rule allows cannot meet it anywhere."""
    # the AUTHOR's regions only: a grown re-run holds an anchor in its own `_hold_<ref>` square
    # where the first run put it (_place_grow), and a rule the first run left broken there is
    # the report's NEAR BROKEN, not a refusal (output_board mN replay: U14 held 22.9 off J2)
    regions = {r["name"]: np.asarray(r["poly"], float) for r in rules
               if r["kind"] == "region" and not r["name"].startswith("_")}
    held = {}
    for r in rules:
        if r["kind"] == "in_region" and r["region"] in regions:
            for x in pi._refs(r["refs"], parts):
                held.setdefault(x, []).append(r["region"])
    bad = []
    for r in rules:
        if r["kind"] != "near" or not r.get("hard", True) or r.get("ref") not in held:
            continue
        tr = r["target"].split(".", 1)[0]
        # ⚠ A WHOLE-PART TARGET IS ITS COURTYARD, NOT ITS CENTRE (brain_board W48, 2026-11-19):
        # `near U1` is measured to U1's courtyard (place_intent P.target), but this check measured
        # to U1's centre and refused C123 in a window that holds U1's own west pads -- "11.4 mm
        # from U1" across a 24 mm LQFP. Reach is now the centre distance less the target's own
        # radius -- its courtyard's, or for a pad target ("U1.50", a decap's) that pad's offset
        # from the anchor: never refuses a rule that can be met, may pass one only the placer
        # can judge.
        reach = 0.0
        if "." in r["target"]:
            num = r["target"].split(".", 1)[1]
            xy = [q["xy"] for q in parts.get(tr, {}).get("pads", ()) if str(q.get("num")) == num]
            reach = max((float(np.hypot(*v)) for v in xy), default=0.0)
        elif parts.get(tr, {}).get("crtyd"):
            reach = float(np.hypot(*np.asarray(parts[tr]["crtyd"], float).T).max())
        if tr in pl:
            where, what = np.asarray([pl[tr][:2]], float), "%s (placed)" % tr
        elif tr in held:
            where, what = None, "%s (held in %s)" % (tr, "/".join(held[tr]))
        else:
            continue
        for reg in held[r["ref"]]:
            if where is not None:
                d = float(min(pi._seg_dist(where, regions[reg][i], regions[reg][(i + 1) % len(regions[reg])]).min()
                              for i in range(len(regions[reg]))))
                d = 0.0 if pi._inside(regions[reg], where).any() else d
            else:
                d = max(0.0, min(pi._poly_dist(regions[reg], regions[t_]) for t_ in held[tr]))
            if where is not None:
                d = max(0.0, d - reach)
            if d > float(r["max_mm"]):
                bad.append("%s is held in region %s, which comes no nearer than %.1f mm to %s; the rule "
                           "wants %g [%s]" % (r["ref"], reg, d, what, r["max_mm"], r.get("src", "")))
    if bad:
        raise SystemExit("place_init: a hard near rule no placement can meet -- re-region the part "
                         "or relax the rule:\n  " + "\n  ".join(bad))


def _place(parts, notes, rules, keep=(), hint_out=None):
    pl = {}
    log = []
    why = {}                     # provenance: which rule (or stage) set each coordinate
    rot_of = {}
    for r in rules:
        if r["kind"] == "rot":
            rot_of[r["ref"]] = list(r["allowed"])
    # every hard distance rule, by each ref it names: _drop takes no seat that breaks one
    _HARD.clear()
    for r in rules:
        if r["kind"] in HARD_DIST_KINDS and pi.is_hard(r):
            for x in _rule_refs(r):
                if x in parts:
                    _HARD.setdefault(x, []).append(r)

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
            if ref not in rot_of:
                # no `rot` rule: turn the mouth to the edge (holdout 1: rot came from parts.json's
                # zeroed `at`, and the PH plug faced +Y on a -X panel)
                rot = pi.panel_rot(parts, ref, r["edge"], prefer=rot)
                if abs(rot - rot0(ref)) > 1e-6:
                    log.append("panel %s turned to %g: its mouth faces %s" % (ref, rot, r["edge"]))
            ux, uy = pi.DIRS[r["edge"]]
            P = pi.Placed(parts, {ref: [0.0, 0.0, rot]})
            b = P.body(ref)
            front = float((b @ (ux, uy)).max())
            want = pi.panel_face(r) + r.get("overhang", 0.0)
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

    # ⚠ A CONSTRAINED SATELLITE IS NOT A SATELLITE (lever_sensor holdout 1b, 2026-11-12): SW1
    # (the 8.9 mm DIP terminator: `access`, an `apart` from the sensor, `near` R4) was seated
    # as R4's satellite after every other satellite had filled the board -- "no room", dropped
    # on the crystal corner, six overlaps. A small part that carries its own mechanical
    # constraint (access / apart, or too tall for a height zone) is placed as a part in its
    # own right, in area order with the other parts, so no satellite seated after its
    # anchor can take its room; its `near` is a spring. (Placing these FIRST of all was
    # tried -- holdout 2b: U2, promoted only for being 1.75 tall, took the board's middle
    # and the LQFP-48 had no room.)
    H_ = None
    con = set()
    for r in rules:
        if r["kind"] == "access" and r.get("ref") in parts:
            con.add(r["ref"])
        elif r["kind"] == "apart":
            con |= set(pi._refs(r["a"], parts)) | set(pi._refs(r["b"], parts))
        elif r["kind"] == "height":
            H_ = pi.heights() if H_ is None else H_
            con |= {x for x in parts if (pi.part_height(x, parts, H_, notes) or 0.0) > float(r["max_mm"])}
    # ...but only a BIG one, and never a tight loop's member: a test pad's `access`, a crystal's or an
    # ESD clamp's noise `apart` (auto_floorplan) leave those satellites (optical, output_panel)
    tnets = {nm for r in rules if r["kind"] == "tight" for nm in r["nets"]}

    def _big(x):
        c_ = np.asarray(parts[x]["crtyd"] or [[0, 0], [0, 0]], float)
        return float(np.prod(np.ptp(c_, axis=0))) >= SAT_BIG_MM2
    promoted = {r["ref"] for r in rules if r["kind"] == "near" and r.get("ref") in con
                and len(parts[r["ref"]]["pads"]) <= IC_PADS and _big(r["ref"])
                and not (tnets & {q["net"] for q in parts[r["ref"]]["pads"] if q["net"]})}

    _near_reach(parts, rules, pl)

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

    # ⚠ A `near` PULLS ITS SUBJECT, NEVER ITS TARGET (output_board mN, 2026-11-14). As a
    # two-way spring the rule "U17 within 30 of FL3" pulled FL3 -- the USB pair's choke,
    # tied by its nets to the J1 connector -- as hard as it pulled U17; U17's region held
    # it, so the solve met the rule halfway by dragging FL3 43 mm off J1, and the rule was
    # still broken (39.6 mm). The target is where the rule is measured FROM: a one-way
    # spring moves only the subject, and the target answers to its own nets.
    def spring1(a, oa, b, ob, w):
        if a not in idx:
            return
        i = idx[a]
        A[i, i] += w
        if b in idx:
            j = idx[b]
            A[i, j] -= w
            d = ob - oa
            bx[i] += w * d[0]
            by[i] += w * d[1]
        else:
            t_ = np.asarray(pl[b][:2]) + ob - oa
            bx[i] += w * t_[0]
            by[i] += w * t_[1]

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
        elif r["kind"] == "near" and r.get("ref") in idx and (len(parts[r["ref"]]["pads"]) > IC_PADS
                                                               or r["ref"] in promoted):
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
            spring1(ref_, np.zeros(2), tr, ot, w)
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
             [r["poly"] for r in rules if r["kind"] == "keepout" and not r.get("except")])
    cu_grids(G, pi.declared_items(rules, notes))   # kind "copper" + the notes' tracks / vias: other nets' pads keep off
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
    # ⚠ A KEEP-OUT'S "except" LIST WAS IGNORED HERE (output_board mG, 2026-11-13): every
    # keep-out went into the grid as solid, so the 80 audio parts its except list names --
    # the isolated corner's own -- found NO ROOM in the corner they were drawn for. (The CM5
    # keep-out never showed it: its two excepted parts are fixed.) A keep-out with an except
    # list is closed, like an exclusive region, to every free part NOT on it.
    for r in rules:
        if r["kind"] != "keepout" or not r.get("except"):
            continue
        exc = set(r["except"])
        inside = pi._inside(np.asarray(r["poly"], float), XY).reshape(G.H, G.W)
        for ref in parts:
            if ref in exc or ref in fixed:
                continue
            inreg[ref] = inside if ref not in inreg else (inreg[ref] | inside)
    # ⚠ A HEIGHT ZONE IS CLOSED TO A TALLER PART (lever_sensor holdout 2c, 2026-11-12): only the
    # checker knew the rule, so U2 (SOIC-8, 1.75) dropped inside the magnet cap's 1.5 mm sweep
    # and the flow stopped before layout. The zone is forbidden to every free part over its
    # limit, the way an exclusive region is to outsiders.
    H_z = None
    for r in rules:
        if r["kind"] != "height":
            continue
        H_z = pi.heights() if H_z is None else H_z
        inside = pi._inside(np.asarray(r["poly"], float), XY).reshape(G.H, G.W)
        # ⚠ A PART WITH NO HEIGHT IS NOT A LOW PART (lead, 2026-11-13): the zone used to let
        # every part it could not measure in without a word -- the brain's 13 mm polymer caps
        # among them. Say which, so the board adds part_heights (or board_geom a HEIGHT row).
        # Only prints; nothing placed differs.
        _unk = sorted("%s (%s)" % (x, parts[x]["fpid"]) for x in parts
                      if x not in fixed and pi.part_height(x, parts, H_z, notes) is None)
        if _unk:
            print("place_init: WARNING: height zone %r (max %.1f mm) cannot measure %d part(s), which "
                  "it lets in unchecked -- give them part_heights in the board notes: %s"
                  % (r.get("why", r.get("name", "")), float(r["max_mm"]), len(_unk), ", ".join(_unk)))
        for ref in parts:
            if ref in fixed or (pi.part_height(ref, parts, H_z, notes) or 0.0) <= float(r["max_mm"]):
                continue
            inreg[ref] = inside if ref not in inreg else (inreg[ref] | inside)
    _fsrc = {r_.get("ref"): "%s %s" % (r_["kind"], r_.get("src", "")) for r_ in rules
             if r_["kind"] in ("fixed", "panel") and r_.get("ref")}
    _fov = []
    if ROOM_DIAG:
        try:
            for line_ in _fixed_overlaps(parts, pl, fixed, _fsrc):
                _fov.append(line_)
                log.append(line_)
                print("place_init: " + line_)
        except Exception as e_:                 # noqa: BLE001  (a diagnosis never stops a run)
            log.append("FIXED OVERLAP check failed: %r" % (e_,))
    # ⚠ NAMED IN THE FIRST SECOND, REFUSED 12 MINUTES LATER (brain_board mV23, 2026-11-17):
    # U5's land grew (RNX -> DDA) under five holds frozen round the old one; this said so,
    # the placement ran on for 720 s, and layout refused the courtyard overlaps. With
    # PCBFLOW_FIXED_OVERLAP_STOP=1 the run stops here. (Off by default: layout accepts the
    # overlaps a project declares in its pcb_declared.py, which this stage does not read.)
    if _fov and os.environ.get("PCBFLOW_FIXED_OVERLAP_STOP", "0") == "1":
        raise SystemExit("place_init: %d FIXED OVERLAP(s) -- release one hold of each pair "
                         "(see above); stopped before placement" % len(_fov))
    for ref in fixed:
        m, ai, aj = mask(parts[ref], pl[ref][2])
        _stamp(G, m, ai, aj, *G.ij(*pl[ref][:2]), force=True, grow=halo(parts[ref]))
    decaps = {}
    for r in rules:
        if r["kind"] == "decap":
            decaps.setdefault(r["pin"].split(".")[0], []).append(r)
        elif (r["kind"] == "near" and r.get("ref") in idx and len(parts[r["ref"]]["pads"]) <= IC_PADS
              and r["ref"] not in promoted):
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
    # ⚠ A TIGHT LOOP'S PATH IS RESERVED BEFORE THE DECAPS TAKE IT (motor_ctrl from
    # footprints, 2026-11-11): satellites seated by radius, so U4's decaps (1.5 mm) went
    # first and C8 took the spot on the line from U4.5/6 to where Y1 then seated -- OSC_IN /
    # OSC_OUT did not route. A satellite sharing a `tight` net with its anchor seats FIRST,
    # and the strip (CHANNEL_W) from each anchor pin to its pin on that net is stamped into
    # the grid, so no later drop -- seat or local pass -- lands on it. (Charging crossings in
    # the local pass was tried first: a satellite is placed by its seat, not by that cost,
    # so C8 never moved, and the members' charge cascaded into 8 broken rules.)
    tight_nets = {nm for r in rules if r["kind"] == "tight" for nm in r["nets"]}
    pnets = {r_: {q["net"] for q in parts[r_]["pads"] if q["net"]} for r_ in parts}
    for anc_, rs_ in decaps.items():
        for r_ in rs_:
            c_ = r_.get("cap") or r_.get("ref")
            if anc_ in pnets and tight_nets & pnets.get(c_, set()) & pnets[anc_]:
                r_["_tight"] = sorted(tight_nets & pnets.get(c_, set()) & pnets[anc_])

    def strips(ref, c):
        """The strips (CHANNEL_W) from each of ref's pins on a tight net shared with c to c's
        nearest pin on it, from just outside one pad to just short of the other."""
        P = pi.Placed(parts, pl)
        out_ = []
        for nm in sorted(tight_nets & pnets[ref] & pnets[c]):
            A_ = [P.pad(ref, q["num"]) for q in parts[ref]["pads"] if q["net"] == nm]
            B_ = [P.pad(c, q["num"]) for q in parts[c]["pads"] if q["net"] == nm]
            for a_ in A_:
                b_ = min(B_, key=lambda b: float(np.hypot(*(b - a_))))
                v_ = b_ - a_
                L_ = float(np.hypot(*v_))
                if L_ < 1.3:
                    continue
                u_ = v_ / L_
                nn = np.array([-u_[1], u_[0]]) * CHANNEL_W / 2.0
                a2, b2 = a_ + u_ * 0.6, b_ - u_ * 0.6
                out_.append((nm, np.array([a2 + nn, b2 + nn, b2 - nn, a2 - nn])))
        return out_

    # ⚠ A SATELLITE THAT CANNOT SEAT AT ITS PIN TAKES ROOM, OR SAYS SO (output_board mN replay,
    # 2026-11-14): U212 landed with D219 1.3 mm and R244 1.4 mm off its supply pin, and its
    # decap C246 (rule 5 mm) took "the nearest free spot" 20.5 mm away -- the unbounded drop,
    # with nothing in the log. Now: within the rule first; then a non-satellite neighbour
    # holding the pin's patch is lifted (nearest first, EVICT_TRIES of them), the satellite
    # seated within its rule, and the neighbour re-dropped at the nearest free spot to where
    # it was -- kept only if both seat; else the unbounded drop, logged DECAP STRANDED.
    # ...but only a SMALL, LOW-CURRENT neighbour (output_board replay init4, 2026-11-14): the
    # first cut lifted L204 -- the boost's hot-loop inductor -- and C314 (+24V bulk) to seat
    # U220's control satellites; BST_SW's pour went from 10 to 25 foreign pads, BST_LMID 1 to
    # 15. A part on a pour's net or path (the high-current stage), or more than EVICT_AREA x
    # the satellite's courtyard, holds its seat.
    def _area(x):
        return float(np.prod(np.ptp(np.asarray(parts[x]["crtyd"] or [[0, 0], [1, 1]], float), axis=0)))

    def evict(c, t, ref, r, f0):
        P = pi.Placed(parts, pl)
        mm = float(r["max_mm"])
        tp = np.asarray(t, float)[None]
        cand = sorted((pi._poly_dist(P.crtyd(x), tp), x) for x in pl
                      if x in idx and x not in sat and x != ref and x not in fixed and x not in power_held
                      and _area(x) <= EVICT_AREA * _area(c))
        for d, x in [q for q in cand if q[0] < mm][:EVICT_TRIES]:
            pose = _lift(G, parts, pl, x)
            if _drop_sat(G, parts, c, t, rots(c, rot[c]), pl, f0, ref, r, near_mm=mm):
                if _drop(G, parts, x, pose[:2], rots(x, pose[2]), pl, inreg.get(x)):
                    log.append("DECAP ROOM: %s lifted off %s's pin patch (%s) and re-seated %.1f mm away; %s seated"
                               % (x, ref, r.get("pin") or r.get("target"), math.dist(pose[:2], pl[x][:2]), c))
                    why[x] = (why.get(x, "") + "; lifted for %s's %s" % (ref, c)).lstrip("; ")
                    return True
                _lift(G, parts, pl, c)
            _put_back(G, parts, pl, x, pose)
        return False

    pour_nets = {r_["net"] for r_ in rules if r_["kind"] == "pour"}
    power_held = ({a_.split(".", 1)[0] for r_ in rules if r_["kind"] == "pour" for a_ in r_.get("along", ())}
                  | {x for x in parts if {q["net"] for q in parts[x]["pads"]} & pour_nets})

    def stranded(c, t, ref, r, f0):
        if not _drop_sat(G, parts, c, t, rots(c, rot[c]), pl, f0, ref, r):
            return False
        mm = r.get("max_mm")
        if mm is not None:
            d = math.dist(pl[c][:2], np.asarray(t, float))
            if d > float(mm):
                P = pi.Placed(parts, pl)
                tp = np.asarray(t, float)[None]
                hold = sorted((pi._poly_dist(P.crtyd(x), tp), x) for x in pl if x not in (c, ref))[:3]
                log.append("DECAP STRANDED: %s seated %.1f mm from %s (rule %g): the pin's patch is held by %s"
                           % (c, d, r.get("pin") or r.get("target"), mm,
                              ", ".join("%s %.1f" % (x, dd) for dd, x in hold)))
        return True

    def seat(ref):
        """Seat ref's satellites at their pins; then each satellite's own (recursive)."""
        # ⚠ A HARD SATELLITE SEATS BEFORE A SOFT ONE (brain_board sw1, 2026-11-22): U205's
        # datasheet-hard VIN cap C218 found NO ROOM -- its own soft siblings had taken the pin's
        # patch first, and the LM5122's soft control parts filled Q209's side before its hard
        # loop ceramic C306. An engineer places the hot-loop / VCC / BOOT caps first and fits
        # the control parts round them: tight nets, then hard rules, then tightest max_mm.
        for r in sorted(decaps.get(ref, ()), key=lambda r: (0 if tight_nets & pnets.get(r.get("cap") or r.get("ref"), set())
                                                                & pnets[ref] else 1, 0 if pi.is_hard(r) else 1,
                                                                r.get("max_mm", 9))):
            c = r.get("cap") or r.get("ref")
            if c in placed_sat or c in fixed or c not in idx:
                continue
            P = pi.Placed(parts, pl)
            t = _seat(r, P, pl, ref)        # just outside the pin (a shared decap: off the package)
            # a satellite keeps clear of its noise zones too, when there is room (output_panel
            # 2026-11-11: Y1, the MCU crystal, seated 0.67 mm from the buck inductor)
            fb, f0 = _apart_forbid(G, parts, pl, c, rules), inreg.get(c)
            nm_ = r.get("max_mm")
            if ((fb is not None and _drop_sat(G, parts, c, t, rots(c, rot[c]), pl,
                                              fb if f0 is None else (fb | f0), ref, r, near_mm=nm_))
                    or (nm_ is not None and _drop_sat(G, parts, c, t, rots(c, rot[c]), pl, f0, ref, r, near_mm=nm_))
                    or (nm_ is not None and evict(c, t, ref, r, f0))
                    or stranded(c, t, ref, r, f0)):
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
                if ROOM_DIAG:
                    try:
                        line_ = _why_no_room(G, parts, pl, ref, target[ref], rots(ref, rot[ref]), f0, fixed, _fsrc)
                    except Exception as e_:     # noqa: BLE001
                        line_ = "NO ROOM WHY: %s -- the diagnosis failed: %r" % (ref, e_)
                    log.append(line_)
                    print("place_init: " + line_)
                continue
            elif fb is not None:
                tail = ", NO room clear of its apart/thermal rules"
            why[ref] = "net graph (quadratic), nearest free spot" + (" in its region" if ref in inreg else "") + tail
            if ref in promoted:
                why[ref] += " (constrained: placed before the satellites)"
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
    hints = {}
    moved, gain = _local(G, parts, pl, [r for r in free if r not in miss], rots, inreg, wnet, rules, notes_c, sats,
                         hints=hints)
    # ⚠ A TURN THE FLOORPLAN FORBIDS IS SAID, NOT TAKEN (motor_ctrl from footprints,
    # 2026-11-12): CAN1_TX/RX stayed open f10-f19 under every placement fix tried. U4 sat at
    # 270, with CAN1 (pins 46/47, bound for U2 at -X) east of CAN2 (35/36, bound for U3 at
    # +X) on one 0.4 mm row: 177 crossing escape chords, and CAN2 ran along the pin tips.
    # At 0 it is 72 -- but U4.5 then faced the `logic` band's edge, which the trial
    # floorplan drew flush with U4's courtyard, and Y1 seated 1.7 mm past its 4 mm `near`,
    # so stranding (lexicographic, lead ruling) kept 270. Widening the band 2 mm: U4 turned
    # to 0 on net cost alone, 0 open, 0 unconnected (f21). A tangle COST (3 mm/crossing) and
    # a fan-out band clear of loose parts were tried and dropped: neither was decisive, and
    # the band cost output_panel 0.5 -> 1.3 mm uncoupled. What the author needs is the line.
    for ref_, rec in sorted(hints.items()):
        if ref_ not in pl:
            continue
        cur = [x for x in rec if abs((x[0] - pl[ref_][2] + 180.0) % 360.0 - 180.0) < 0.5]
        alt = min(rec, key=lambda x: x[2])
        if not cur or not alt[1] or alt[2] * TANGLE_RATIO > cur[0][2] or cur[0][2] - alt[2] < TANGLE_MIN:
            continue
        regs = sorted({r["region"] for r in rules if r["kind"] == "in_region" and ref_ in r.get("refs", ())})
        log.append("TANGLE HINT: %s at %g has %d crossing escapes, at %g only %d -- but there %s%s. "
                   "Give it room (a wider band, or loosen that rule) and it will turn." % (
                       ref_, pl[ref_][2], cur[0][2], alt[0], alt[2],
                       ", ".join("%s lands %.1f mm past its rule" % (c, d_) for c, d_, _ in alt[1]),
                       " (in region %s)" % "/".join(regs) if regs else ""))
        if hint_out is not None:
            hint_out.append({"anchor": ref_, "rot": pl[ref_][2], "to": alt[0], "stranded": alt[1],
                             "cross": (cur[0][2], alt[2])})
    # ---- 5b. tight paths: reserved once the turns are settled, intruders re-dropped
    # ⚠ A TIGHT LOOP'S PATH IS RESERVED (motor_ctrl from footprints, 2026-11-11): Y1 seated
    # at U4.5 and U4's decap C8 sat on the line from U4.5/6 to Y1 -- OSC_IN/OSC_OUT did not
    # route. After the local pass each anchor -> tight-net satellite strip is stamped into
    # the grid and every other part crossing it is lifted and dropped again at the nearest
    # free spot. (Two earlier forms were reverted: charging crossings in the local pass --
    # a satellite is placed by its seat, so C8 never moved and the members' charge cascaded
    # into 8 broken rules; stamping the strip at seat time -- it froze U4's first turn, the
    # pass could not re-seat Y1, and U4 went back to 0.)
    tpairs = []
    for anc, rs in decaps.items():
        for r in rs:
            c = r.get("cap") or r.get("ref")
            if anc in pl and c in pl and tight_nets & pnets[anc] & pnets[c]:
                tpairs.append((anc, c))
    XY_ = np.stack([G.X.ravel(), G.Y.ravel()], axis=1)
    for anc in sorted({a_ for a_, _ in tpairs}):
        tight_sats = {c for a_, c in tpairs if a_ == anc}
        sts = [(nm, st, c) for c in sorted(tight_sats) for nm, st in strips(anc, c)]
        if not sts:
            continue
        P = pi.Placed(parts, pl)

        def crosses(o, P=P):
            cy = np.asarray(P.crtyd(o), float)
            return len(cy) and any(pi._inside(st, cy).any() or pi._inside(cy, st).any() for _, st, _ in sts)
        # the anchor's other satellites are re-seated TOGETHER round the reserved paths (one at
        # a time could not repack a crowded edge: C8 left U4.1's corner for the far side of U4,
        # into the U4 -> U7 channel -- BOOT0, LINK_TX, SWDIO, SENSE_24V went open, f7); other
        # parts on a path are dropped again at the nearest free spot
        lift = [(c, r) for r in sorted(decaps.get(anc, ()), key=lambda r: r.get("max_mm", 9))
                for c in [r.get("cap") or r.get("ref")]
                if c in pl and c in idx and c not in fixed and c not in tight_sats]
        lifted = {c for c, _ in lift}
        others = [o for o in pl if o in parts and o != anc and o not in tight_sats and o not in lifted
                  and o in idx and o not in fixed and crosses(o)]
        if not others and not any(crosses(c) for c in lifted):
            for nm, st, c in sts:
                G.occ += pi._inside(st, XY_).reshape(G.H, G.W).astype(G.occ.dtype)
            continue
        olds = {o: list(pl[o]) for o in list(lifted) + others}
        for o in olds:
            mo, ao, bo = mask(parts[o], pl[o][2])
            _unstamp(G, mo, ao, bo, *G.ij(*pl[o][:2]), grow=halo(parts[o]))
            del pl[o]
        for nm, st, c in sts:
            G.occ += pi._inside(st, XY_).reshape(G.H, G.W).astype(G.occ.dtype)
        for c, r in lift:
            if c in pl:
                continue                                # a cap with two rules: seated once
            P = pi.Placed(parts, pl)
            t_ = _seat(r, P, pl, anc)
            if not (_drop_sat(G, parts, c, t_, rots(c, olds[c][2]), pl, inreg.get(c), anc, r, near_mm=r.get("max_mm"))
                    or _drop_sat(G, parts, c, t_, rots(c, olds[c][2]), pl, inreg.get(c), anc, r)):
                pl[c] = olds[c]
                mo, ao, bo = mask(parts[c], pl[c][2])
                _stamp(G, mo, ao, bo, *G.ij(*pl[c][:2]), force=True, grow=halo(parts[c]))
                log.append("tight paths of %s: %s found no seat clear of them -- left" % (anc, c))
        for o in others:
            if not _drop(G, parts, o, np.asarray(olds[o][:2]), rots(o, olds[o][2]), pl, inreg.get(o)):
                pl[o] = olds[o]
                mo, ao, bo = mask(parts[o], pl[o][2])
                _stamp(G, mo, ao, bo, *G.ij(*pl[o][:2]), force=True, grow=halo(parts[o]))
        mv_ = {o: float(np.hypot(pl[o][0] - olds[o][0], pl[o][1] - olds[o][1])) for o in olds}
        for o, d_ in mv_.items():
            if d_ > 0.05:
                why[o] = why.get(o, "") + "; re-seated round %s's tight paths" % anc
        log.append("tight paths of %s (%s) reserved; re-seated %s" % (
            anc, " ".join(sorted({nm for nm, _, _ in sts})),
            " ".join("%s %.1f" % (o, d_) for o, d_ in sorted(mv_.items()) if d_ > 0.05) or "nothing moved"))
    # ---- 6. forbid zones: repair, else say so
    unmet = _forbid_repair(G, parts, pl, rules, notes_c, inreg, target, rots, rot, sats, set(idx) - set(miss), why, log)
    for x, det, w in unmet:
        log.append("FORBID NOT MET: %s %s -- %s (the floorplan does not fit: move a fixed part, "
                   "shrink the zone, or give the cell room)" % (x, det, w))
        why[x] = why.get(x, "") + "; FORBID NOT MET: " + det
    # what the later stages (local pass, repairs) leave a satellite with: said by name
    for v in decaps.values():
        for r in v:
            c = r.get("cap") or r.get("ref")
            if c in pl and r.get("max_mm") is not None:
                s_ = _slack(r, parts, pl)
                if s_ < -STRANDED_MM:
                    log.append("SATELLITE OFF ITS PIN: %s %.1f mm past its rule (%s %s, %g)"
                               % (c, -s_, r["kind"], r.get("pin") or r.get("target"), r["max_mm"]))
    log.append("local pass: %d parts moved, small-net wirelength %.0f -> %.0f mm" % (moved, gain[0], gain[1]))
    log.append("placed %d free parts (%d satellites at their pins), %d with no room: %s"
               % (len(free) - len(miss), len(placed_sat), len(miss), " ".join(miss)))
    # the grid is counts: a part lifted twice leaves a negative cell that reads as free
    if G.occ.min() < 0 or G.occ_p.min() < 0:
        raise SystemExit("place_init: occupancy grid went negative (a part was unstamped twice) -- "
                         "the placement may overlap; this is a place_init bug")
    return pl, log, why


STRANDED_MM = 1.0   # mm past its rule a satellite is reported (SATELLITE OFF ITS PIN)
EVICT_AREA = 4.0    # x the satellite's courtyard: a bigger neighbour is not lifted for it
EVICT_TRIES = 4     # neighbours a stranded satellite may lift off its pin's patch, nearest first
SAT_BIG_MM2 = 20.0  # mm2 of courtyard: a constrained satellite this big is placed as a part (SW1 ~39)
CHANNEL_W = 0.6     # mm: the strip a tight net's MST edge keeps clear
TANGLE_FANOUT = 8   # parts: a net on more is a rail, left out of the escape tangle
TANGLE_RATIO = 1.5  # a turn hint needs the other turn to cross this many times fewer
TANGLE_PINS = 24    # pads: a fine-pitch IC this big has a fan-out that can tangle
TANGLE_W = 3.0      # mm of net per crossing escape at a fine-pitch IC (tie-break after stranding)
TANGLE_MIN = 10     # ...and at least this many crossings fewer
HOLD_PAD = 0.3      # mm: room round a held anchor's courtyard in a grown re-run (turns fit)
SEAT_GAP = 1.0      # mm: pin to satellite courtyard when a grown region seats it
GROW_PAD = 0.5      # mm: a region edge grown for a stranded satellite goes this far past its shortfall
POUR_W = 25.0       # mm of broken soft rule a pad inside another net's pour corridor is worth (x RULE_W in the pass: 250 mm of net)
POUR_PAD_MM2 = 1.0  # mm2 of foreign pad inside a pour corridor priced as one pad (PCBFLOW_POUR_AREA)
PAIR_W = 1.0        # mm of broken soft rule per mm2 of foreign pad in a diff pair's corridor (PCBFLOW_PAIR_CORRIDOR): a step aside, never a rule trade -- at POUR_W, U13 left its hard near-J1 rule by 14.5 mm to clear 5 mm2 of USBA's corridor (mV11)
PAIR_DEMAND_W = 4.0  # mm of net per mm2 of wiring demand a pair's hop crosses (its corridor width x RUDY along it)
DEMAND_CELL = 1.0   # mm: the RUDY demand map's cell
SPREAD_STEPS = (2.0, 4.0)  # mm a crowded part is also tried downhill of the crowd map (PCBFLOW_SPREAD)
DEMAND_WIRE = 0.4   # mm of board a wire takes (track + clearance) in the demand map
JOINT_MAX = 4       # parts turned together at most (4^4 = 256 rotation combinations)
JOINT_NEAR = 3.0    # mm a jointly turned part may slide off its spot to fit its new turn
RULE_W = 10.0       # mm of wirelength a millimetre of broken soft rule is worth (local pass)
SOFT_KINDS = ("decap", "near", "between", "thermal", "apart", "chain", "tight")


def _fine_pitch(part, lim=0.65):
    """True if some two pads of the part sit closer than lim mm (a QFN/QFP row)."""
    xy = np.asarray([q["xy"] for q in part["pads"]], float)
    if len(xy) < 2:
        return False
    d = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1))
    np.fill_diagonal(d, 9e9)
    return bool(d.min() < lim)


def _tangle(parts, pl, ref, members, rails):
    """Escape crossings of a part: each signal pin's chord, from its angle round the part to
    the angle of its net's far pads; two chords cross iff their ends interleave (pairs bound
    for the same part skipped -- their order is the far part's business). Each crossing is
    a via, or a net walled in front of a fine-pitch row."""
    P = pi.Placed(parts, pl)
    ctr = np.asarray(pl[ref][:2], float)
    items = []
    for q in parts[ref]["pads"]:
        nm = q["net"]
        if not nm or nm in rails:
            continue
        far = [r for r in members.get(nm, ()) if r != ref and r in pl]
        if not far:
            continue
        a = P.pad(ref, q["num"])
        t = np.mean([P.pad(r, x["num"]) for r in far for x in parts[r]["pads"] if x["net"] == nm], axis=0)
        items.append((math.atan2(a[1] - ctr[1], a[0] - ctr[0]), math.atan2(t[1] - ctr[1], t[0] - ctr[0]),
                      frozenset(far)))
    tau = 2.0 * math.pi
    n = 0
    for i in range(len(items)):
        p1, t1, f1 = items[i]
        span = (t1 - p1) % tau
        for p2, t2, f2 in items[i + 1:]:
            if not (f1 & f2) and (((p2 - p1) % tau) < span) != (((t2 - p1) % tau) < span):
                n += 1
    return n


def _pin_at(P, r):
    """A decap's pin -- or, when it serves several (`also`), the mean of them."""
    ps = [P.pad(*x.split(".", 1)) for x in [r["pin"]] + list(r.get("also", ()))]
    return np.mean(ps, axis=0)


def _seat(r, P, pl, anc):
    """Where a satellite goes for its rule: just outside its pin, or at its target."""
    if r["kind"] == "decap":
        pin = _pin_at(P, r)
        v = pin - np.asarray(pl[anc][:2])
        u = v / (np.hypot(*v) or 1.0)
        if r.get("also") and anc in P.parts:
            # ⚠ A SHARED DECAP SEATS OUTSIDE THE PACKAGE (brain_board mV8, 2026-11-16): C233
            # serves U202.3 and U202.5, opposite sides of an SOIC-8. The mean of the two pins
            # is inside the body, "1 mm past it" still was, and the legaliser took the nearest
            # free spot -- beside pin 5, 5.2 mm from pin 3 (A2 asks 5). The seat is the edge
            # of the anchor's courtyard in that direction, plus a millimetre: between the pins,
            # just off the package.
            c = np.asarray(pl[anc][:2], float)
            ext = max(float(np.dot(q - c, u)) for q in P.crtyd(anc))
            return c + u * (ext + 1.0)
        t = pin + u * 1.0
        if DECAP_SLIDE and not r.get("also"):
            t = _slide_seat(r, P, anc, pin, u, t)
        return t
    if "." in r.get("target", ""):
        return P.pad(*r["target"].split(".", 1))
    return np.asarray(pl[anc][:2])


def _slide_seat(r, P, anc, pin, u, t):
    """DECAP_SLIDE: t moved along the pin row off its neighbours' exits (or t as it was)."""
    parts = P.parts
    c = r.get("cap") or r.get("ref")
    if c not in parts or anc not in parts or parts[anc].get("n_own", len(parts[anc]["pads"])) > LANE_MAX_PADS:
        return t
    cy = np.asarray(parts[c]["crtyd"] or [[-0.5, -0.5], [0.5, 0.5]], float)
    half = float(np.max(np.ptp(cy, axis=0))) / 2.0          # either rotation: its long half
    own = {q["net"] for q in parts[c]["pads"] if q["net"]}
    npins = {}
    for ref in parts:
        for q in parts[ref]["pads"]:
            if q["net"]:
                npins[q["net"]] = npins.get(q["net"], 0) + 1
    # along the pin's EDGE of the package, not across the centre -> pin line: U221.4 is a
    # corner pin, and that line ran diagonal (the first try slid C327 nowhere)
    # -- and from the PAD's long axis, not the nearest courtyard edge: WSON's courtyard bulges
    # on its pad sides, so U221.4's nearest edge was +X (0.49) and its exit is -Y (0.55)
    qa = next(q for q in parts[anc]["pads"] if q["num"] == r["pin"].split(".", 1)[1])
    ax = np.array([1.0, 0.0]) if qa["size"][0] >= qa["size"][1] else np.array([0.0, 1.0])
    u = pi._rot([ax], P.at(anc)[2])[0]
    u = u / (np.hypot(*u) or 1.0)
    if float(np.dot(pin - np.asarray(P.at(anc)[:2]), u)) < 0:
        u = -u
    w = np.array([-u[1], u[0]])                             # along the pin row
    pads = [(q, P.pad(anc, q["num"])) for q in parts[anc]["pads"] if q["num"] and q["net"]]
    lanes = []
    for q, pp in pads:
        if q["net"] in own or npins.get(q["net"], 0) >= LANE_RAIL_PINS:
            continue
        if float(np.dot(pp - pin, u)) < -0.3:                # not on this pin's side
            continue
        if not any(q2["net"] != q["net"] and np.hypot(*(p2 - pp)) < LANE_PITCH for q2, p2 in pads):
            continue
        lanes.append((float(np.dot(pp - t, w)), half + min(q["size"]) / 2.0 + LANE_CLR))
    if not lanes:
        return t
    for k in range(0, 31):                                  # the smallest slide, 0.05 mm steps
        for sg in ((1.0, -1.0) if k else (1.0,)):
            sl = sg * 0.05 * k
            if all(abs(off - sl) >= clr for off, clr in lanes):
                return t + w * sl
    return t


def _local(G, parts, pl, refs, rots, inreg, wnet, rules=(), notes=None, sats=None, passes=3, hints=None):
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

    # ⚠ A POUR IS PLACEMENT'S BUSINESS TOO (gap 7, motor_ctrl from footprints, 2026-11-11):
    # the +5V_RAW (L2-F2) and +5V (F2-J5) pours were cut to 0.00-0.07 mm by other nets' pads
    # placed in their corridors (F1.2; D6, C17, R21) -- quality A1 FAIL on 3 A paths. A pad
    # inside another net's pour corridor on its layer costs POUR_W; a pour's own endpoint
    # part pays for every foreign pad its corridor then holds (so it can turn or move).
    pours = [r for r in rules if r["kind"] == "pour" and r.get("along")]
    pamps = {id(r): pi.pour_amps(r, notes or {}) for r in pours}
    ends = {}
    for r in pours:
        for x in r["along"]:
            ends.setdefault(x.split(".")[0], []).append(r)

    def pour_pen(ref):
        if not pours:
            return 0.0
        P = pi.Placed(parts, pl)
        n = 0
        for r in pours:
            if any(x.split(".")[0] not in pl for x in r["along"]):
                continue
            poly = pi.pour_poly(r, P, notes or {}, pamps[id(r)])
            if poly is None:
                continue
            rs_ = None if r in ends.get(ref, ()) else {ref}
            if os.environ.get("PCBFLOW_POUR_AREA") == "1":
                # ⚠ PRICED BY THE AREA IT TAKES (brain_board mV, 2026-11-16): one price per pad
                # made Q5's 8.8 mm2 drain tab in PB_VOUT cost what a 0.1 mm2 graze does, and the
                # joint turn put it back there on 5 mm of net. A pad pays per POUR_PAD_MM2 inside.
                n += sum(a_ for _, a_ in pi.pour_foreign(r, P, poly, refs=rs_, areas=True)) / POUR_PAD_MM2
            else:
                n += len(pi.pour_foreign(r, P, poly, refs=rs_))
        return POUR_W * n

    # ⚠ A DIFF PAIR NEEDS A CORRIDOR (brain_board mV8 -> lead, 2026-11-17) --
    # PCBFLOW_PAIR_CORRIDOR=1 while measured. The router could not couple the USB pairs on
    # mV8's placement: MCU_DP / DM run 64 mm J202 -> U1 through the board's hottest middle,
    # every coupled lay overlapped 640+ cells of other nets, and making room re-opened 86-89
    # nets. Placement had priced only the pair's length (wnet x4), never the way it must go.
    # Each hop of a declared pair is a corridor -- the straight line between its pin pairs,
    # the coupled pair's width plus PAIR_CLEAR each side -- and another net's pad inside it
    # costs PAIR_W per mm2, the price of a foreign pad in a pour: a hop's own parts pay for
    # their whole corridor (they move or turn to clear or shorten it), any other part for
    # its pads inside one (it steps out of the pair's way).
    # a board opts in through its own notes ("pair_corridor": true), so it rebuilds from its own
    # files and no other board changes (lead, 2026-11-17); PCBFLOW_PAIR_CORRIDOR=1 / 0 overrides
    _pc = os.environ.get("PCBFLOW_PAIR_CORRIDOR")
    _on = (_pc == "1") if _pc in ("0", "1") else bool((notes or {}).get("pair_corridor"))
    pairs_c = list((notes or {}).get("diff_pairs") or ()) if _on else []
    pair_ends = {}
    for sp in pairs_c:
        for st in sp.get("chain") or ():
            for x in st.split("|"):
                pair_ends.setdefault(x, []).append(sp)

    # ...AND THE WIRING IT MUST CROSS, NOT ONLY PADS (brain_board mV8 probe, 2026-11-17): MCU's
    # straight corridor held 2.0 mm2 of other pads, yet the router's coupled lays overlapped
    # 640+ cells -- of other nets' TRACKS. A hop's own parts also pay PAIR_DEMAND_W x its
    # corridor width x the wiring demand along it: RUDY (each net in scope spreads
    # DEMAND_WIRE x its half-perimeter evenly over its bounding box), the pairs' own nets left
    # out, the map rebuilt at the start of every pass. A shorter hop, or one round the
    # crowd, costs less.
    pair_nets = {nm for sp in pairs_c for nm in sp.get("nets") or ()}
    dmap = {}

    def refresh_demand():
        if not pairs_c:
            return
        pts_all = np.array([p for r in pl for _, p in world(r)] or [[0.0, 0.0]])
        lo = pts_all.min(axis=0) - 2.0
        hi = pts_all.max(axis=0) + 2.0
        nx_, ny_ = int(np.ceil((hi[0] - lo[0]) / DEMAND_CELL)), int(np.ceil((hi[1] - lo[1]) / DEMAND_CELL))
        g = np.zeros((ny_, nx_))
        for nm in scope - pair_nets:
            pts = [p for r in members[nm] if r in pl for n2, p in world(r) if n2 == nm]
            if len(pts) < 2:
                continue
            a = np.array(pts)
            x0, y0 = a.min(axis=0) - 0.5
            x1, y1 = a.max(axis=0) + 0.5
            i0, i1 = int((y0 - lo[1]) // DEMAND_CELL), int((y1 - lo[1]) // DEMAND_CELL) + 1
            j0, j1 = int((x0 - lo[0]) // DEMAND_CELL), int((x1 - lo[0]) // DEMAND_CELL) + 1
            g[i0:i1, j0:j1] += DEMAND_WIRE * ((x1 - x0) + (y1 - y0)) / ((x1 - x0) * (y1 - y0))
        dmap["g"], dmap["lo"] = g, lo

    def hop_demand(poly):
        g, lo = dmap.get("g"), dmap.get("lo")
        if g is None:
            return 0.0
        pa = np.asarray(poly, float)
        a, b = (pa[0] + pa[3]) / 2.0, (pa[1] + pa[2]) / 2.0
        w_ = float(np.hypot(*(pa[0] - pa[3])))
        ln = float(np.hypot(*(b - a)))
        n = max(2, int(ln / 0.5))
        s_ = a + np.outer(np.linspace(0.0, 1.0, n), b - a)
        ii = np.clip(((s_[:, 1] - lo[1]) // DEMAND_CELL).astype(int), 0, g.shape[0] - 1)
        jj = np.clip(((s_[:, 0] - lo[0]) // DEMAND_CELL).astype(int), 0, g.shape[1] - 1)
        return w_ * float(g[ii, jj].mean()) * ln

    def pair_pen(ref):
        """(mm2 of foreign pad in the corridors ref is priced for, mm of net for the demand
        its own hops cross)."""
        if not pairs_c:
            return 0.0, 0.0
        P = pi.Placed(parts, pl)
        v, dm = 0.0, 0.0
        for sp in pairs_c:
            for poly, hop, side, _ln in pi.pair_corridors(sp, P):
                if ref in hop:
                    v += sum(a_ for _, a_ in pi.pair_foreign(sp, P, poly, side, skip=hop))
                    dm += PAIR_DEMAND_W * hop_demand(poly)
                else:
                    v += sum(a_ for _, a_ in pi.pair_foreign(sp, P, poly, side, skip=hop, refs={ref}))
        return PAIR_W * v, dm

    # ⚠ THE TANGLE BREAKS A TIE, IT DOES NOT TRADE (lead, 2026-11-12): a fine-pitch IC's
    # crossing escapes cost TANGLE_W each, inside the cost that ranks AFTER stranding -- so a
    # turn that untangles but strands a satellite still loses. motor_ctrl, power band at 0
    # and the grow allowed: Y1 held, but U4 stayed at 270 on net cost (80 crossings vs 40).
    def tangle_pen(ref):
        if ref not in tangled:
            return 0.0
        return TANGLE_W * _tangle(parts, pl, ref, members, rails_l)

    # ⚠ ONE PRICE FOR A PAD IN A FOREIGN POUR (lead, 2026-11-14): pour_pen was summed into the
    # rule breach and multiplied by RULE_W only when the part had a soft rule -- a ruled part
    # paid RULE_W x POUR_W = 250 per foreign pad, a rule-less one 25, so adding any soft rule
    # made a part 10x more pour-averse as a side effect. Every part now pays the ruled price
    # (the one C246 showed the pass already weighs rules against).
    # ⚠ NOTHING PUSHED PARTS OUT OF A CROWD (brain_board mV25, 2026-11-17) -- PCBFLOW_SPREAD=1
    # while measured. Every term above pulls a part toward its nets; the global plan then
    # overflowed F.Cu at J7, U38 and U6 / R17 / R18 while ~1100 mm2 along the bottom edge held
    # nothing (the user saw it on the render). The crowd map is RUDY over every net in scope
    # (each spreads DEMAND_WIRE x its half-perimeter over its box); a part pays CROWD_W x the
    # demand above the board's SPREAD_PCT percentile under its courtyard, and a crowded part
    # is also tried SPREAD_STEPS mm downhill on the map, not only at its nets' optimum.
    # ⚠ MEASURED AND NOT KEPT (brain_board mV31, --to-routability, global plan overflow):
    # off 8.49 over 25 squares; W 2 / 85th 9.57 over 23; W 1 / 92nd 14.69 over 33. RUDY is
    # wire density, and this board's overflow is F.Cu pin escape at a few parts (J7's ESD
    # clamps, U209, U38): the term moved each jam somewhere else. Leave it off; a spreading
    # term that works will have to price escape room at the pins, not box demand.
    spread = os.environ.get("PCBFLOW_SPREAD") == "1"
    crowd_w = float(os.environ.get("PCBFLOW_SPREAD_W", "2.0"))
    crowd_pct = float(os.environ.get("PCBFLOW_SPREAD_PCT", "85"))
    cmap = {}

    def refresh_crowd():
        if not spread:
            return
        pts_all = np.array([p for r in pl for _, p in world(r)] or [[0.0, 0.0]])
        lo = pts_all.min(axis=0) - 2.0
        hi = pts_all.max(axis=0) + 2.0
        nx_ = int(np.ceil((hi[0] - lo[0]) / DEMAND_CELL))
        ny_ = int(np.ceil((hi[1] - lo[1]) / DEMAND_CELL))
        g = np.zeros((ny_, nx_))
        for nm in scope:
            pts = [p for r in members[nm] if r in pl for n2, p in world(r) if n2 == nm]
            if len(pts) < 2:
                continue
            a_ = np.array(pts)
            x0, y0 = a_.min(axis=0) - 0.5
            x1, y1 = a_.max(axis=0) + 0.5
            i0, i1 = int((y0 - lo[1]) // DEMAND_CELL), int((y1 - lo[1]) // DEMAND_CELL) + 1
            j0, j1 = int((x0 - lo[0]) // DEMAND_CELL), int((x1 - lo[0]) // DEMAND_CELL) + 1
            g[i0:i1, j0:j1] += DEMAND_WIRE * ((x1 - x0) + (y1 - y0)) / ((x1 - x0) * (y1 - y0))
        nz = g[g > 0]
        thr = float(np.percentile(nz, crowd_pct)) if nz.size else 0.0
        gy, gx = np.gradient(g)
        cmap.update(g=g, lo=lo, thr=thr, gx=gx, gy=gy)

    def _cbox(ref):
        c = np.asarray(pi.Placed(parts, pl).crtyd(ref), float)
        g, lo = cmap["g"], cmap["lo"]
        i0 = int(np.clip((c[:, 1].min() - lo[1]) // DEMAND_CELL, 0, g.shape[0] - 1))
        i1 = int(np.clip((c[:, 1].max() - lo[1]) // DEMAND_CELL, 0, g.shape[0] - 1)) + 1
        j0 = int(np.clip((c[:, 0].min() - lo[0]) // DEMAND_CELL, 0, g.shape[1] - 1))
        j1 = int(np.clip((c[:, 0].max() - lo[0]) // DEMAND_CELL, 0, g.shape[1] - 1)) + 1
        return i0, i1, j0, j1

    def crowd_pen(ref):
        if not spread or "g" not in cmap:
            return 0.0
        i0, i1, j0, j1 = _cbox(ref)
        ex = cmap["g"][i0:i1, j0:j1] - cmap["thr"]
        return crowd_w * float(np.clip(ex, 0.0, None).sum()) * DEMAND_CELL * DEMAND_CELL

    def downhill(ref):
        """unit vector away from the crowd at ref's courtyard, or None"""
        i0, i1, j0, j1 = _cbox(ref)
        v = -np.array([cmap["gx"][i0:i1, j0:j1].mean(), cmap["gy"][i0:i1, j0:j1].mean()])
        n = float(np.hypot(*v))
        return v / n if n > 1e-9 else None

    def penalty(ref):
        pp_, pd_ = pair_pen(ref)
        if not rel.get(ref):
            return RULE_W * (pour_pen(ref) + pp_) + pd_ + tangle_pen(ref) + crowd_pen(ref)
        P = pi.Placed(parts, pl)
        v = pour_pen(ref) + pp_
        for r in rel[ref]:
            try:
                for sl, _, _ in pi.check(r, P, notes or {}):
                    v += r.get("weight", 1.0) * max(0.0, -sl)
            except (KeyError, ValueError):
                pass
        return RULE_W * v + pd_ + tangle_pen(ref) + crowd_pen(ref)

    def total():
        return cost(scope)

    # ...and a satellite's OWN rules count the same way (output_board mN replay, 2026-11-14):
    # C246, seated at U212.6, moved itself 15.5 mm off the pin -- a pad in another net's pour
    # corridor costs RULE_W x POUR_W = 250, its weight-0.5 rule only 10 x 0.5 x 15.5 = 78, and
    # nothing ranked the breach first for a satellite as it is for an anchor. A move may not
    # take a part out of its own rule any more than it may strand an anchor's satellite.
    mine_ = {}
    for anc_, rs_ in (sats or {}).items():
        for c_, r_ in rs_:
            mine_.setdefault(c_, []).append((c_, r_))

    def stranded(ref):
        """How many of ref's satellites -- and of ref's own satellite rules -- sit outside
        their rule's radius: a turn or move is judged on this FIRST, then on cost (see the
        satellite note in the pass)."""
        n = 0
        P = pi.Placed(parts, pl)
        for c, r in list((sats or {}).get(ref, ())) + mine_.get(ref, []):
            if c not in pl:
                continue
            try:
                if min(x[0] for x in pi.check(r, P, notes or {})) < -0.05:
                    n += 1
            except (KeyError, ValueError):
                pass
        return n

    # fine-pitch ICs whose turn is worth a hint (see the TANGLE note where _local is called)
    rails_l = {nm for nm, m in members.items() if len(m) > TANGLE_FANOUT}
    rails_l |= {q["net"] for r in rules if r["kind"] == "decap"
                for q in parts.get(r.get("cap") or r.get("ref"), {"pads": ()})["pads"] if q["net"]}
    # only a big package: a 10-pin MSOP's escapes walk round it in a millimetre (output_panel
    # U14/U16 turned 180 on 2-3 crossings each when every fine-pitch part counted)
    tangled = {r_ for r_ in refs if r_[:1] == "U" and len(parts[r_]["pads"]) >= TANGLE_PINS and _fine_pitch(parts[r_])}
    # ⚠ PARTS THAT SHARE POURS TURN TOGETHER (brain_board mT4 -> mV, 2026-11-16) --
    # PCBFLOW_POUR_JOINT=1 while measured. A USB-C port's back-to-back FETs are each the end
    # of two pours (drain tab -> its own, source pins -> the partner's), and two ports'
    # stages interleave: Q5 turned alone to clear its tab from PB_VOUT put the tab in port
    # A's PA_VOUT. Each part's best turn depends on the others' (the corridor runs pin to
    # pin), so the one-at-a-time pass above cannot find it: the rotation-only optimum needed
    # Q4 and Q6 turned at once (foreign pad area 12.2 -> 2 mm2). So: the multi-pin parts
    # linked by being ends of the same pours, in clusters of 2..JOINT_MAX, every rotation
    # combination tried in place (satellites re-seated), ranked by (stranded, cost + penalty).
    def _joint_turn():
        free = [r_ for r_ in refs if r_ in pl and r_ not in fixed_local and len(pads[r_]) > 2]
        link = {r_: set() for r_ in free}
        for r in pours:
            e = [x.split(".")[0] for x in r["along"]]
            e = [x for x in dict.fromkeys(e) if x in link]
            for a_ in e:
                link[a_] |= set(e) - {a_}
        seen_, out_ = set(), set()
        for s_ in free:
            if s_ in seen_ or not link[s_]:
                continue
            comp, st = [], [s_]
            while st:
                u = st.pop()
                if u in seen_:
                    continue
                seen_.add(u)
                comp.append(u)
                st += list(link[u] - seen_)
            if not 2 <= len(comp) <= JOINT_MAX:
                if len(comp) > JOINT_MAX:
                    print("place_init: JOINT TURN skipped %s: %d parts > %d" % (",".join(sorted(comp)), len(comp), JOINT_MAX))
                continue
            comp.sort()
            group = list(dict.fromkeys(comp + [c for g in comp for c, _ in (sats or {}).get(g, ())
                                              if c in pl and c not in fixed_local]))
            gnets = set()
            for g in group:
                gnets |= {nm for nm, _ in pads[g]} & scope

            def score_():
                return (sum(stranded(g) for g in comp), cost(gnets) + sum(penalty(g) for g in group))
            s0_ = score_()
            olds = {g: list(pl[g]) for g in group}
            for g in group:
                mg_, gi_, gj_ = mask(parts[g], pl[g][2])
                _unstamp(G, mg_, gi_, gj_, *G.ij(*pl[g][:2]), grow=halo(parts[g]))
            best_, fail_ = None, {}
            import itertools as _it
            for combo in _it.product(*[rots(g, olds[g][2]) for g in comp]):
                placed_g, ok = [], True
                _INFLIGHT.clear()
                _INFLIGHT.update(group)
                for g, rr in zip(comp, combo):
                    fz = _apart_forbid(G, parts, pl, g, rules)
                    fr = inreg.get(g) if fz is None else (fz if inreg.get(g) is None else fz | inreg.get(g))
                    _INFLIGHT.discard(g)
                    if _drop(G, parts, g, np.asarray(olds[g][:2], float), [rr], pl, fr):
                        placed_g.append(g)
                    else:
                        ok = False
                        fail_[g] = fail_.get(g, 0) + 1
                        break
                if ok:
                    for g in comp:
                        for c, r in (sats or {}).get(g, ()):
                            if c not in group or c in placed_g:
                                continue
                            P = pi.Placed(parts, pl)
                            fc = _apart_forbid(G, parts, pl, c, rules)
                            fc = inreg.get(c) if fc is None else (fc if inreg.get(c) is None else fc | inreg.get(c))
                            _INFLIGHT.discard(c)
                            if _drop_sat(G, parts, c, _seat(r, P, pl, g), rots(c, olds[c][2]), pl, fc, g, r):
                                placed_g.append(c)
                            else:
                                ok = False
                                fail_[c] = fail_.get(c, 0) + 1
                                break
                        if not ok:
                            break
                if ok:
                    sc = score_()
                    slide = max(math.hypot(pl[g][0] - olds[g][0], pl[g][1] - olds[g][1]) for g in comp)
                    if slide > JOINT_NEAR:
                        ok = False
                        fail_["slide"] = fail_.get("slide", 0) + 1
                if ok:
                    if best_ is None or sc < best_[0]:
                        best_ = (sc, {g: list(pl[g]) for g in group}, combo)
                for g in placed_g:
                    mg_, gi_, gj_ = mask(parts[g], pl[g][2])
                    _unstamp(G, mg_, gi_, gj_, *G.ij(*pl[g][:2]), grow=halo(parts[g]))
                for g in group:
                    pl[g] = list(olds[g])
            _INFLIGHT.clear()
            take = best_ is not None and (best_[0][0] < s0_[0] or (best_[0][0] == s0_[0] and best_[0][1] < s0_[1] - 0.5))
            for g in group:
                if take:
                    pl[g] = best_[1][g]
                mg_, gi_, gj_ = mask(parts[g], pl[g][2])
                _stamp(G, mg_, gi_, gj_, *G.ij(*pl[g][:2]), grow=halo(parts[g]))
            print("place_init: JOINT TURN %s: %s %s -> %s (stranded, cost) %s -> %s" % (
                ",".join(comp), "TAKEN" if take else "kept",
                [olds[g][2] for g in comp], list(best_[2]) if best_ else None,
                (s0_[0], round(s0_[1], 1)), (best_[0][0], round(best_[0][1], 1)) if best_ else fail_))
            if take:
                out_ |= set(group)
        return out_

    refresh_demand()
    t0 = total()
    moved = set()
    fixed_local = set(pl) - set(refs)
    for _ in range(passes):
        refresh_demand()
        refresh_crowd()
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
            # ⚠ A TURN IS JUDGED WITH ITS SATELLITES RE-SEATED, STRANDED ONES FIRST (motor_ctrl
            # from footprints, 2026-11-11): every `at` 0, U4 kept rot 0 with OSC_IN (U4.5)
            # facing its region's edge; Y1 (near U4.5, 4 mm) could only seat 5.7 mm off. The
            # pass skipped U4 (already at its net optimum) and, when it did try turns, a
            # 1.7 mm breach weighed 17 against tens of mm of net -- so rot 0 stayed. Now a part
            # with a stranded satellite is tried in place, and turns rank by (stranded, cost).
            s0 = stranded(ref)
            crowded = spread and crowd_pen(ref) > 0.0
            if np.hypot(t[0] - x, t[1] - y) < 0.5 and len(pads[ref]) > 2:
                if not s0 and not crowded:
                    continue
                t = np.array([x, y])
            targets = [t]
            if crowded:
                u_ = downhill(ref)
                if u_ is not None:
                    targets += [np.array([x, y]) + d_ * u_ for d_ in SPREAD_STEPS]
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
            rec_ = []
            # ⚠ A ZONE IS NOT FOR TRADING (output_panel, 2026-11-11): the pass moved L1 28 mm
            # and paid a 9.3 mm breach of the crystal's zone (93 in the penalty) for 2100 of
            # other soft-rule gains -- L1 ended 0.67 mm from Y1. Moves keep forbid zones.
            fz = _apart_forbid(G, parts, pl, ref, rules)
            fr = inreg.get(ref) if fz is None else (fz if inreg.get(ref) is None else fz | inreg.get(ref))
            for t, rr in [(t_, r_) for t_ in targets for r_ in rots(ref, a)]:
                _INFLIGHT.clear()
                _INFLIGHT.update(g for g in group if g != ref)
                ok = _drop(G, parts, ref, t, [rr], pl, fr)
                placed_g = [ref] if ok else []
                if ok:
                    for c, r in (sats or {}).get(ref, ()):
                        if c not in group or c in placed_g:
                            continue
                        P = pi.Placed(parts, pl)
                        fc = _apart_forbid(G, parts, pl, c, rules)
                        fc = inreg.get(c) if fc is None else (fc if inreg.get(c) is None else fc | inreg.get(c))
                        _INFLIGHT.discard(c)
                        if _drop_sat(G, parts, c, _seat(r, P, pl, ref), rots(c, olds[c][2]), pl, fc, ref, r):
                            placed_g.append(c)
                        else:
                            ok = False
                            break
                cc = (stranded(ref), cost(gnets) + sum(penalty(g) for g in group)) if ok else None
                if ok and hints is not None and ref in tangled:
                    P = pi.Placed(parts, pl)
                    short = []
                    for c, r in (sats or {}).get(ref, ()):
                        try:
                            m_ = min(x_[0] for x_ in pi.check(r, P, notes or {}))
                        except (KeyError, ValueError):
                            continue
                        if m_ < -0.05:
                            tg_ = r.get("pin") or r.get("target") or ""
                            at_ = P.pad(*tg_.split(".", 1)) if "." in tg_ else np.asarray(pl[ref][:2], float)
                            short.append((c, -m_, [float(at_[0]), float(at_[1])]))
                    rec_.append((rr, short, _tangle(parts, pl, ref, members, rails_l)))
                if ok and (best_t is None or cc < best_t[0]):
                    best_t = (cc, {g: list(pl[g]) for g in group})
                for g in placed_g:
                    mg_, gi_, gj_ = mask(parts[g], pl[g][2])
                    _unstamp(G, mg_, gi_, gj_, *G.ij(*pl[g][:2]), grow=halo(parts[g]))
                for g in group:
                    pl[g] = list(olds[g])
            _INFLIGHT.clear()
            if rec_:
                hints[ref] = rec_
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
            s1 = stranded(ref) if ok else s0
            if ok and (s1 < s0 or (s1 == s0 and cost(gnets) + sum(penalty(g) for g in group) < c0 - 0.5)):
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
    if os.environ.get("PCBFLOW_POUR_JOINT") == "1":
        moved |= _joint_turn()
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


ROOM_DIAG = os.environ.get("PCBFLOW_ROOM_DIAG", "1") == "1"  # 0 turns the diagnoses off
ROOM_DIAG_R = 40.0  # mm round the target: the placed parts a NO ROOM diagnosis may lift


def _fixed_overlaps(parts, pl, fixed, src):
    """Pairs of FIXED parts whose courtyards overlap, with the rule that pinned each.

    ⚠ WHY (brain_board mV19c-f, 2026-11-17): J7 (the service USB-C, a new panel rule) sat on
    U21, a hold frozen from an older placement (mP0). Fixed parts are stamped by force, so
    nothing said so: the flow ran on, J7's satellites were pushed into U1's strip, and U1
    had NO ROOM -- reported as the 30 rules that bind U1, none of them the cause. Four
    routes were lost before a trace found it."""
    P = pi.Placed(parts, pl)
    fx = sorted(r for r in fixed if r in pl and parts.get(r, {}).get("crtyd"))
    cy = {r: np.asarray(P.crtyd(r), float) for r in fx}
    box = {r: (c.min(axis=0), c.max(axis=0)) for r, c in cy.items()}
    out = []
    for i, a in enumerate(fx):
        for b in fx[i + 1:]:
            (al, ah), (bl, bh) = box[a], box[b]
            if (al > bh).any() or (bl > ah).any():
                continue
            d = pi._poly_dist(cy[a], cy[b])
            if d < -GAP:
                sa, sb = src.get(a, "?"), src.get(b, "?")
                hint = ("both from one hold -- a footprint grew since it was frozen" if sa == sb
                        else "one rule is newer than the other's hold")
                out.append("FIXED OVERLAP: %s x %s by %.2f mm -- %s [%s] on %s [%s]: %s; release one"
                           % (a, b, -d, a, sa, b, sb, hint))
    return out


def _why_no_room(G, parts, pl, ref, t, rots, forbid, fixed, src):
    """A part with NO ROOM: the fewest placed parts whose lifting lets it in, named.

    Counterfactual, on the grid as it was when the drop failed: every placed part within
    ROOM_DIAG_R of the target is lifted (free parts first; the fixed ones too only if that
    is not enough), the drop is tried, then the lifted parts go back one by one, farthest
    first, and each one whose return shuts the part out again is a blocker. The grid and
    pl are left exactly as they were."""
    near = sorted((float(np.hypot(*(np.asarray(pl[o][:2]) - np.asarray(t)))), o)
                  for o in pl if o != ref and o in parts)
    near = [(d, o) for d, o in near if d <= ROOM_DIAG_R]
    stages = [[o for _d, o in near if o not in fixed], [o for _d, o in near if o in fixed]]
    lifted = {}

    def fits():
        if _drop(G, parts, ref, t, rots, pl, forbid):
            _lift(G, parts, pl, ref)
            return True
        return False
    try:
        ok = False
        for st in stages:
            for o in st:
                lifted[o] = _lift(G, parts, pl, o)
            if fits():
                ok = True
                break
        if not ok:
            return "NO ROOM WHY: %s does not fit even with every part within %.0f mm lifted -- "                    "its region or the board is too small for it" % (ref, ROOM_DIAG_R)
        order = sorted(lifted, key=lambda o: -float(np.hypot(*(np.asarray(lifted[o][:2]) - np.asarray(t)))))
        block = []
        for o in order:
            _put_back(G, parts, pl, o, lifted.pop(o))
            if not fits():
                lifted[o] = _lift(G, parts, pl, o)
                block.append(o)
        def tag(o):
            return "%s (%s)" % (o, "fixed: " + src.get(o, "?") if o in fixed else "placed")
        return "NO ROOM WHY: %s fits with only these lifted: %s" % (ref, ", ".join(tag(o) for o in block))
    finally:
        for o, pose in lifted.items():
            _put_back(G, parts, pl, o, pose)


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
    # ...and so may a TIGHT-LOOP satellite, but only IN FRONT OF ITS OWN PINS (motor_ctrl from
    # footprints, 2026-11-12): Y1 (the crystal, `tight` OSC_IN/OSC_OUT) was held 2.5 mm off
    # U4, its centre 4.25 mm out -- past its 4 mm `near` on any straight side, so U4 kept
    # 270 (a corner fits it) with CAN1 and CAN2 crossing in front of the 0.4 mm row. Let into
    # the WHOLE ring, it sat on U4's north edge in front of BOOT0 / PG_5V and both went open.
    # The window is the outward side of the edge carrying its tight pins, along that edge
    # the pins' span +- half the satellite.
    pcap = _pin_cap(rule, parts) and rule["target"].split(".", 1)[0] == anchor
    tight = rule is not None and rule.get("_tight") and rule["kind"] != "decap" and not pcap
    # A FALLBACK, judged by the rule: the plain drop first, kept if the rule holds; only a
    # stranded tight satellite tries the window, and keeps whichever seat breaks it less.
    # (Always open, it moved 51 parts on output_panel, whose crystals already held.)
    plain = None
    if tight:
        if not _drop(G, parts, c, t, rots, pl, forbid, near_mm):
            plain = None
        else:
            s0 = _slack(rule, parts, pl)
            if s0 >= -0.05:
                return True
            plain = (list(pl[c]), s0)
            _lift(G, parts, pl, c)
    big = (rule is not None and (rule["kind"] == "decap" or pcap or tight)
           and anchor in pl and halo(parts[anchor]) > HALO_SMALL)
    delta = None
    if big:
        m, ai, aj = mask(parts[anchor], pl[anchor][2])
        ij = G.ij(*pl[anchor][:2])
        delta = np.zeros_like(G.occ)
        _put(delta, *_grow(m, ai, aj, halo(parts[anchor]), G.g), *ij, -1)
        _put(delta, *_grow(m, ai, aj, HALO_SMALL, G.g), *ij)
        if tight:
            P = pi.Placed(parts, pl)
            cy = np.asarray(P.crtyd(anchor), float)
            lo, hi = cy.min(axis=0), cy.max(axis=0)
            half = float(np.max(np.ptp(np.asarray(parts[c]["crtyd"] or [[0, 0], [1, 1]], float), axis=0))) / 2.0 + 0.5
            win = np.zeros(G.occ.shape, bool)
            for q in parts[anchor]["pads"]:
                if q["net"] not in rule["_tight"]:
                    continue
                pp = P.pad(anchor, q["num"])
                gaps = [pp[0] - lo[0], hi[0] - pp[0], pp[1] - lo[1], hi[1] - pp[1]]
                k = int(np.argmin(gaps))
                if k < 2:
                    out = (G.X < lo[0] + 0.05) if k == 0 else (G.X > hi[0] - 0.05)
                    along = np.abs(G.Y - pp[1]) <= half
                else:
                    out = (G.Y < lo[1] + 0.05) if k == 2 else (G.Y > hi[1] - 0.05)
                    along = np.abs(G.X - pp[0]) <= half
                win |= out & along
            delta[~win] = 0
        G.occ += delta
    try:
        ok = _drop(G, parts, c, t, rots, pl, forbid, near_mm)
    finally:
        if delta is not None:
            G.occ -= delta
    if tight and plain is not None:
        if ok and _slack(rule, parts, pl) > plain[1]:
            return True
        if ok:
            _lift(G, parts, pl, c)
        _put_back(G, parts, pl, c, plain[0])
        return True
    return ok


def _hard_pick(G, parts, pl, ref, a, hk, gi, gj, d):
    """The index of the nearest candidate seat (grid gi, gj; distance d) at rotation a where
    every one of ref's judged hard rules holds, or None."""
    rs, reach = hk
    xy = np.stack([G.x0 + gj * G.g, G.y0 + gi * G.g], axis=1)
    keep = np.ones(len(d), bool)
    for c, lim in reach:
        keep &= np.hypot(xy[:, 0] - c[0], xy[:, 1] - c[1]) <= lim
    cand = np.nonzero(keep)[0]
    cand = cand[np.argsort(d[cand], kind="stable")][:HARD_TRIES]
    old = pl.get(ref)
    try:
        for k in cand:
            pl[ref] = [float(xy[k, 0]), float(xy[k, 1]), a]
            if all(_slack(r, parts, pl) >= -0.05 for r in rs):
                return int(k)
    finally:
        if old is None:
            pl.pop(ref, None)
        else:
            pl[ref] = old
    return None


def _slack(rule, parts, pl):
    """A rule's worst slack at this placement (mm; < 0 is broken); -inf if it cannot be read."""
    try:
        return min(x[0] for x in pi.check(rule, pi.Placed(parts, pl), {}))
    except (KeyError, ValueError, TypeError):
        return float("-inf")


# ⚠ A LEGALISER NEVER BREAKS A HARD DISTANCE (lead 2026-11-22): the quadratic stage met
# U13's hard `near` J1 (14 mm, DS46176 fig. 1), legalisation dropped U13 at the nearest FREE
# spot, 16.44 mm out, and the flow stopped 20 minutes later at the intent check. A hard
# near / decap / tight / between rule is a constraint on the seat, not a check afterwards:
# every _drop (first seat, satellite, local pass, re-seat) of a part such a rule names takes
# only a spot where each of its rules whose parts are all placed holds (_slack >= -0.05),
# nearest first; none -> False, which the callers report as NO ROOM by name.
HARD_DIST_KINDS = ("near", "decap", "tight", "between")
HARD_TRIES = 6000     # candidate seats tested per rotation, nearest first (prefiltered by reach)
_HARD = {}            # ref -> its hard distance rules (_place fills it)
# ⚠ A GROUP MOVES TOGETHER (brain_board lg_hard, 2026-11-22): the local pass unstamps an IC and
# its satellites but leaves their old poses in pl while it tries the IC's new seats, so Y2's
# hard 4 mm `near` U37 was judged against Y2's OLD seat, every U37 move was refused, and 29
# parts landed differently. Parts in flight (_INFLIGHT) are skipped until they land; each is
# judged on its own drop.
_INFLIGHT = set()


def _hard_ok(parts, pl, ref):
    """ref's hard distance rules that can be judged now (every part they name is placed and
    not in flight), or None; and the farthest a seat's centre can stand from each rule's other
    parts' centres (max_mm + both half-diagonals; tight / between: no bound)."""
    rs = [r for r in _HARD.get(ref, ())
          if all(x == ref or (x in pl and x not in _INFLIGHT) for x in _rule_refs(r) if x in parts)]
    if not rs:
        return None
    hd = lambda x: 0.5 * float(np.hypot(*np.ptp(np.asarray(parts[x]["crtyd"] or [[0, 0], [1, 1]], float), axis=0)))
    reach = []
    for r in rs:
        if r["kind"] in ("near", "decap") and r.get("max_mm") is not None:
            for x in _rule_refs(r) - {ref}:
                if x in pl and x not in _INFLIGHT:
                    reach.append((np.asarray(pl[x][:2], float), float(r["max_mm"]) + hd(ref) + hd(x) + 0.2))
    return rs, reach


def _drop(G, parts, ref, t, rots, pl, forbid=None, near_mm=None):
    """Put ref at the free grid spot nearest t (first rot that fits, nearer wins). near_mm:
    give up (False) rather than go further than that -- a satellite that cannot keep its
    noise zone AND its rule takes its rule (the caller retries without the zone). A part a
    HARD distance rule names takes only a seat that keeps the rule (_hard_ok)."""
    hk = _hard_ok(parts, pl, ref)
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
            # ⚠ AN IC'S HALO HOLDS AGAINST THE OUTLINE TOO (brain_board mV22-24, 2026-11-17):
            # a courtyard may meet the edge, so U35 (TUSB321, 0.4 pitch) sat 0.7 mm off the
            # J7 notch's wall with GND on the pin facing it -- no way out past edge_clear,
            # and the router's plane join for that one pad failed all of GND. Its halo is
            # the escape ring it keeps from other parts; with PCBFLOW_IC_EDGE_HALO=1 it keeps
            # it from the board's edge as well -- on by default (=0 turns it off); panel and fixed parts are not dropped here.
            if (IC_EDGE_HALO and parts[ref].get("n_own", len(parts[ref]["pads"])) > IC_PADS
                    and getattr(G, "out", None) is not None):
                col3 = _collide(G.out[i0:i1, j0:j1].astype(np.float32), mg, gi, gj)
                free &= col3 < 0.5
            cf = _cu_free(G, parts[ref], ref, a, m, ai, aj, i0, i1, j0, j1)
            if cf is not None:
                free &= cf
            if not free.any():
                continue
            fi, fj = np.nonzero(free)
            d = np.hypot(fi + i0 - ti, fj + j0 - tj)
            if hk is None:
                k = int(np.argmin(d))
            else:
                k = _hard_pick(G, parts, pl, ref, a, hk, fi + i0, fj + j0, d)
                if k is None:
                    continue
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
    # the floorplan GROW changed, for the flow's later gates (score --intent judges regions)
    gp = out[:-5] + ".grow.json" if out.endswith(".json") else out + ".grow"
    if GROWN:
        json.dump(GROWN, open(gp, "w"), indent=0)
    elif os.path.exists(gp):
        os.remove(gp)
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
