"""place_intent.py: placement INTENT -- the rules a board's parts are placed by -- and its checker.

PLACEMENT.md step (a). A board states what has to be where, and why; this module says, for
any placement (the hand one, or one place_init / place_refine produced), how much room
each rule has: SLACK in mm, >= 0 met, < 0 broken. Nothing here moves a part.

    py -3.12 place_intent.py <stem> <intent.json>     report every rule's slack, worst first

<stem> needs <stem>.parts.json (place_geom.py, the parts' local geometry) and
<stem>.board.json (the notes: placements, outline, cutouts). The intent is a list of
rules, plain JSON (a generator builds it with the helpers below, or writes it by hand):

    {"kind": "...", ...args..., "hard": true|false, "weight": 1.0,
     "why": "the reason", "src": "where the reason comes from"}

`src` is where the rule comes from -- a datasheet section, a user ruling or memory, a CAD
part (src/electronics.py OP_PANEL), or "hand" for a choice with no outside source -- so a
re-layout can tell which rules still hold when the thing they came from changes.

MECHANICAL (from the CAD -- a fresh board is mostly these)
  outline                          every courtyard inside Edge.Cuts (panel parts excepted)
  hole      xy d keepout           a mounting hole and its head's clearance: no courtyard.
                                   A notes cutout with `keepout_d` (the CAD's boss / post /
                                   head) makes this rule itself and overrides a typed one
  keepout   poly [side] [except]   no courtyard inside (deck wall, standoff, rib, cable run);
                                   `except` names parts the CAD puts there on purpose
  height    poly max_mm            no part taller than max_mm inside (lid, deck, strings)
  panel     ref edge at face|face_at [overhang] [anchor]
                                   a connector whose MOUTH the panel fixes: the body front
                                   (F.Fab extent toward `edge`) at face + overhang, its
                                   centre `at` along the edge. `face` is a DISTANCE out from
                                   the board centre along `edge` (>= 0: the -X face of a 45 mm
                                   board is 22.5, not -22.5); `face_at` is the same face as a
                                   board coordinate. Unless a `rot` rule says otherwise the
                                   part is turned so its mouth -- the body's far side from its
                                   pads -- points at the edge
  mate      ref dir length [clear]
                                   the plug / cable insertion stroke as a swept keep-out:
                                   from the part's body along dir (+X, -X, +Y, -Y; L+X ... in
                                   the part's own frame, turning with it; up) for
                                   length mm; no other courtyard within clear of it. "up"
                                   (a top-entry plug) sweeps the part's own body upward:
                                   no neighbour within clear of it
  access    ref|xy side tool_d     something reached after assembly (test pad, button, the
                                   hex key to a screw): no other courtyard within tool_d/2
  fixed     ref xy rot [tol]       pinned by the CAD or by hand ("pin" = fixed at the hand xy)
  group     anchor members [tol]   a rigid CELL: members {ref: [dx, dy, drot]} in the anchor's
                                   own frame (offset turns with the anchor, rot = anchor rot +
                                   drot). One rule per instance of a repeated cell (optical's
                                   ten string cells, five converter cells): the cell is designed
                                   once, around its pins, and placed whole -- its hand-laid
                                   geometry (a TIA's summing nodes, a converter's input fan)
                                   is the design, not a placement choice

ELECTRICAL / FLOORPLAN
  region    name poly [exclusive]  a floorplan band; in_region refs region keeps parts in it;
                                   exclusive: closed to every other part but its members'
                                   satellites (near / decap on a member)
  apart     a b min_mm             two groups' courtyards at least min_mm apart (noise)
  thermal   ref others apart_mm    a heat source off the sensors and off each other
  decap     cap pin max_mm [also]  the capacitor's land on the pin's net within max_mm of it (and of every pin
                                   in `also`: one cap serving neighbouring supply pins, seated between them)
  near      ref target max_mm      target = a part (courtyard) or a pin "U4.8"
  chain     refs [max_ratio]       a pair's path order: sum of hops <= max_ratio x straight
  rot       ref allowed            rotation in the allowed set
  side      ref F|B
  array     refs axis pitch [tol]  one rule for a repeat: same off-axis, equal pitch along
  current   net amps [dT]          the current a net carries: widths() turns it into the track
                                   width (IPC-2221), so power is drawn as power
  pour      net layer region|along [width_mm] [priority]
                                   a current no track can carry: a copper zone on `layer`, over
                                   the named region or round the pins `along` ("Q2.2", "J7.1":
                                   the hull of width_mm circles at each, default twice the
                                   IPC width of the net's largest power path, >= 2 mm).
                                   place_flow writes it into notes["zones"]; the report counts
                                   other nets' pads inside on that layer (room: a pour goes
                                   only where its layer has it -- +3V3 on In2, output_panel)
  (auto_floorplan(parts) proposes the noise `apart` rules: switch nodes and USB / relay
   edges off references, ADC / amplifier inputs, photodiodes and crystals)
  tight     nets max_mm [weight]   a loop the datasheet wants small (a buck's SW node, its FB,
                                   a crystal's legs): each net's pads within max_mm (half
                                   perimeter); place_init pulls these nets x weight

`auto_decaps(parts, notes)` proposes a decap rule for every capacitor that sits across an
IC's supply and ground, at its nearest supply pin -- the rule a fresh board gets for free.
"""
from __future__ import annotations

import ast
import collections
import json
import math
import os
import re
import sys

import numpy as np

from nettie import is_net_tie  # noqa: E402  (NT<n>: one answer for every reader)

_HERE = os.path.dirname(os.path.abspath(__file__))

HERE = os.path.dirname(os.path.abspath(__file__))
DIRS = {"+X": (1.0, 0.0), "-X": (-1.0, 0.0), "+Y": (0.0, 1.0), "-Y": (0.0, -1.0)}


# ----------------------------------------------------------------------------- geometry
def _rot(xy, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    xy = np.asarray(xy, float).reshape(-1, 2)
    return np.stack([xy[:, 0] * c - xy[:, 1] * s, xy[:, 0] * s + xy[:, 1] * c], axis=1)


def _seg_dist(p, a, b):
    """Distance from points p (n,2) to segment ab."""
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0)
    return np.hypot(*(p - (a + t[:, None] * ab)).T)


def _inside(poly, pts):
    """Even-odd point in polygon, vectorised: pts (n,2) -> bool (n,)."""
    poly = np.asarray(poly, float)
    x, y = pts[:, 0][:, None], pts[:, 1][:, None]
    x1, y1 = poly[:, 0][None], poly[:, 1][None]
    x2, y2 = np.roll(poly[:, 0], -1)[None], np.roll(poly[:, 1], -1)[None]
    cross = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / np.where(y2 != y1, y2 - y1, 1e-12) + x1)
    return cross.sum(axis=1) % 2 == 1


def _poly_dist(pa, pb):
    """Signed distance between two polygons: > 0 apart (gap), < 0 overlapping (depth, approx)."""
    pa, pb = np.asarray(pa, float), np.asarray(pb, float)
    d = min(min(_seg_dist(pa, pb[i], pb[(i + 1) % len(pb)]).min() for i in range(len(pb))),
            min(_seg_dist(pb, pa[i], pa[(i + 1) % len(pa)]).min() for i in range(len(pa))))
    # vertices AND edge midpoints: two boxes sharing an edge line (a courtyard flush with a
    # keep-out) overlap with no vertex strictly inside the other
    ma, mb = (pa + np.roll(pa, -1, axis=0)) / 2.0, (pb + np.roll(pb, -1, axis=0)) / 2.0
    xa, xb = np.concatenate([pa, ma]), np.concatenate([pb, mb])
    ia, ib = _inside(pb, xa), _inside(pa, xb)
    if ia.any() or ib.any():
        # depth: how far the deepest sampled point of each lies inside the other
        dep = 0.0
        if ia.any():
            dep = max(dep, float(_edge_dist_inside(pb, xa[ia]).max()))
        if ib.any():
            dep = max(dep, float(_edge_dist_inside(pa, xb[ib]).max()))
        return -max(dep, 1e-3)
    return d


def _edge_dist_inside(poly, pts):
    """Signed distance of each point to the polygon's boundary: + inside, - outside."""
    poly = np.asarray(poly, float)
    d = np.min([_seg_dist(pts, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))], axis=0)
    return np.where(_inside(poly, pts), d, -d)


def heights():
    """cadkit board_geom's HEIGHT table (mm above the face, by footprint), read as a literal
    so the CadQuery module is not imported."""
    src = open(os.path.join(os.path.dirname(HERE), "board_geom.py"), encoding="utf-8").read()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "HEIGHT" for t in node.targets):
            try:
                return ast.literal_eval(node.value)
            except ValueError:
                return {}
    return {}


def part_height(ref, parts, H, notes=None):
    """A part's height above the face: the board notes' `part_heights` {ref: mm} first, else
    board_geom's HEIGHT by footprint, else None.

    ⚠ A FOOTPRINT IS NOT A HEIGHT (brain, 2026-11-13): C113/C114 went to a 13 mm polymer on
    the 10 mm CP_Elec_10x10.5 land, and HEIGHT has no CP_Elec entry at all -- a height zone
    skips a part it cannot measure, so a 13 mm can would have been free to sit in the
    station-2 band. The board that knows the part says so in its notes (which the CAD reads
    too); the footprint table stays the default."""
    ph = (notes or {}).get("part_heights") or {}
    if ref in ph:
        return float(ph[ref])
    return H.get(parts[ref]["fpid"])


# ── declared copper is an obstacle to other nets' pads (lead 2026-11-22) ─────────────────────
# ⚠ A RELEASED PART CAN LAND ON DECLARED COPPER AND ONLY LAYOUT SAYS SO (brain_board sqp, 2026-11-22):
# D213 / TP2, released by a pair corridor, sat on +5V_CM5's declared F.Cu column; placement treated
# declared tracks and vias as nothing, the route was never started, and layout refused the board
# ("declared copper crowds another net"). Each other net's PAD, grown by the fab's mask expansion,
# keeps the net clearance from every declared track and via on the pad's own side (a through-hole
# pad on every layer; a via is on every layer). Courtyards are not blocked: a body may sit over
# copper, its pads may not.
PAD_CU_CLEAR = 0.127        # layout._declared_copper_clear's rule (JLC 5 mil)
PAD_MASK_EXP = 0.05         # solder-mask opening round a pad at the fab
VIA_D = 0.6                 # layout._add_via's default diameter
ALL_CU = "*"


def declared_items(rules=(), notes=None):
    """[(net, layer or ALL_CU, kind, geom, own)]: every declared track segment ("seg", (a, b, half
    width)) and via ("via", (centre, radius)) -- `copper` rules and the notes' own tracks / vias.
    own: the parts a rule's copper lands `on` -- drawn against those exact pins, their clearance is
    layout's exact check (_declared_copper_clear), not a pad rectangle's."""
    out, seen = [], set()
    own = frozenset()

    def seg(net, layer, w, pts):
        for a, b in zip(pts[:-1], pts[1:]):
            key = (net, layer, round(float(w), 4), tuple(map(float, a)), tuple(map(float, b)))
            if key not in seen:
                seen.add(key)
                out.append((net, layer, "seg", (np.asarray(a, float), np.asarray(b, float), float(w) / 2.0), own))

    def via(net, x, y, d):
        key = (net, round(float(x), 4), round(float(y), 4))
        if key not in seen:
            seen.add(key)
            out.append((net, ALL_CU, "via", (np.asarray([x, y], float), float(d) / 2.0), own))
    for r in rules:
        if r.get("kind") != "copper":
            continue
        own = frozenset(x.split(".", 1)[0] for x in r.get("on", ()))
        for tr in r.get("tracks", ()):
            seg(r["net"], tr["layer"], tr["width"], tr["pts"])
        for v in r.get("vias", ()):
            via(r["net"], v[0], v[1], v[3] if len(v) > 3 else r.get("via_d", VIA_D))
    own = frozenset()
    for tr in (notes or {}).get("tracks", ()) or ():
        seg(tr[0], tr[1], tr[2], tr[3])
    for v in (notes or {}).get("vias", ()) or ():
        via(v[0], v[1], v[2], v[4] if len(v) > 4 else VIA_D)
    return out


def _seg_poly_gap(poly, a, b):
    """Distance from segment ab to a convex polygon; 0 where they touch, cross or one holds the other."""
    poly = np.asarray(poly, float)
    if _inside(poly, np.stack([a, b])).any():
        return 0.0
    n = len(poly)
    d = float(_seg_dist(poly, a, b).min())
    for i in range(n):
        e0, e1 = poly[i], poly[(i + 1) % n]
        d = min(d, float(_seg_dist(np.stack([a, b]), e0, e1).min()))
        # proper crossing: the two segments straddle each other
        c1 = np.cross(b - a, e0 - a) * np.cross(b - a, e1 - a)
        c2 = np.cross(e1 - e0, a - e0) * np.cross(e1 - e0, b - e0)
        if c1 < 0 and c2 < 0:
            return 0.0
    return d


def pad_layers(part, q):
    """The copper layers a pad is on: ALL_CU for a through-hole pad, else its part's outer side."""
    return ALL_CU if q.get("tht") else ("B.Cu" if part.get("side", "F") == "B" else "F.Cu")


def pad_copper(P, items, refs=None, clr=PAD_CU_CLEAR, exp=0.0, near=0.5):
    """[(slack, "REF.PIN", det)]: other nets' pads against declared copper, slack = gap - clr - exp
    (< 0: the pad is inside the net clearance, or its mask opening is with exp=PAD_MASK_EXP). Only
    pads within `near` of slack 0; a rule's own parts (`on`) are skipped.

    ⚠ THE MASK BAND IS A WARNING, NOT A STOP (brain_board so_ovlo / sqahA, 2026-11-22): every declared
    escape between U205's 0.5-pitch pins is drawn at the 0.127 rule, 0.13 from the next pin -- 34 pads
    inside clearance + mask on boards layout accepts. place_flow stops at the net clearance (layout's
    own rule, which catches sqp's D213 / TP2 on +5V_CM5) and says the mask band."""
    if not items:
        return []
    need = clr + exp
    boxes = []
    for net, lay, kind, g, _own in items:
        if kind == "seg":
            a, b, hw = g
            lo, hi = np.minimum(a, b) - hw, np.maximum(a, b) + hw
        else:
            c, rr = g
            lo, hi = c - rr, c + rr
        boxes.append((lo - need - near, hi + need + near))
    out = []
    for ref, part in P.parts.items():
        if ref not in P.pl or (refs is not None and ref not in refs):
            continue
        # ⚠ A NET TIE'S PADS ARE ONE CONDUCTOR (brain_board fold4, 2026-11-25): NT206 joins +5V_RAW
        # to ISN5, and the declared +5V_RAW track ran 0.088 from its ISN5 pad -- the q6c board it was
        # lifted from is DRC clean there, because KiCad waives clearance between a tie's own nets.
        # Copper on any net the tie joins is not foreign to any of its pads.
        tied = {x.get("net") for x in part["pads"]} if is_net_tie(ref) else ()
        for q in part["pads"]:
            if not q.get("num") or not q.get("size"):
                continue
            pl_ = pad_layers(part, q)
            poly = None
            for (net, lay, kind, g, own), (lo, hi) in zip(items, boxes):
                if net == q.get("net") or net in tied or ref in own or not (pl_ == ALL_CU or lay == ALL_CU or lay == pl_):
                    continue
                c = P.pad(ref, q["num"])
                rr = max(q["size"][:2]) * 0.75
                if (c[0] + rr < lo[0] or c[0] - rr > hi[0] or c[1] + rr < lo[1] or c[1] - rr > hi[1]):
                    continue
                poly = poly if poly is not None else P.pad_poly(ref, q["num"])
                if kind == "seg":
                    a, b, hw = g
                    gap = _seg_poly_gap(poly, a, b) - hw
                    what = "declared %s track (%s, %.2f wide)" % (net, lay, 2 * hw)
                else:
                    cc, rv = g
                    gap = (0.0 if _inside(poly, cc[None])[0] else float(min(
                        _seg_dist(cc[None], poly[i], poly[(i + 1) % len(poly)])[0] for i in range(len(poly))))) - rv
                    what = "declared %s via (%.2f, %.2f)" % (net, cc[0], cc[1])
                s = gap - need
                if s < near:
                    out.append((s, "%s.%s" % (ref, q["num"]),
                                "%s pad [%s] %.3f mm from %s, wants %.3f (clearance %.3f + mask %.3f)"
                                % (pad_layers(part, q).replace(ALL_CU, "THT"), q.get("net") or "no net",
                                   max(gap, 0.0), what, need, clr, exp)))
    return out


class Placed:
    """Parts at a placement: world courtyards, pads, bodies (board frame, mm)."""

    def __init__(self, parts, placements):
        self.parts, self.pl = parts, placements
        self._c = {}

    def at(self, ref):
        x, y, r = self.pl[ref][:3]
        return float(x), float(y), float(r)

    def world(self, ref, local):
        x, y, r = self.at(ref)
        return _rot(local, r) + (x, y)

    def crtyd(self, ref):
        if ref not in self._c:
            p = self.parts[ref]
            loc = p["crtyd"]
            if p.get("crtyd_multi"):              # a placed-whole cell (place_init): its hull
                loc = _hull([q for c in p["crtyd_multi"] for q in c]).tolist()
            if not loc:
                fx = p["fab"] or [-0.5, 0.5, -0.5, 0.5]
                loc = [[fx[0], fx[2]], [fx[1], fx[2]], [fx[1], fx[3]], [fx[0], fx[3]]]
            self._c[ref] = self.world(ref, loc)
        return self._c[ref]

    def body(self, ref):
        p = self.parts[ref]
        fx = p["fab"]
        if not fx:
            return self.crtyd(ref)
        return self.world(ref, [[fx[0], fx[2]], [fx[1], fx[2]], [fx[1], fx[3]], [fx[0], fx[3]]])

    def pad(self, ref, num):
        for q in self.parts[ref]["pads"]:
            if q["num"] == str(num):
                return self.world(ref, [q["xy"]])[0]
        raise KeyError("%s has no pad %s" % (ref, num))

    def pad_poly(self, ref, num):
        """That pad's rectangle (4 corners, board frame): its size turned by its own rotation."""
        for q in self.parts[ref]["pads"]:
            if q["num"] == str(num):
                w, h = (q.get("size") or (0.0, 0.0))[:2]
                c = _rot([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]], q.get("rot", 0.0))
                return self.world(ref, c + np.asarray(q["xy"], float))
        raise KeyError("%s has no pad %s" % (ref, num))

    def pads_on(self, ref, net):
        return [self.world(ref, [q["xy"]])[0] for q in self.parts[ref]["pads"] if q["net"] == net]

    def target(self, t):
        """'U4.8' -> that pad's point; 'U4' -> its courtyard."""
        if "." in t:
            ref, num = t.split(".", 1)
            return np.asarray([self.pad(ref, num)])
        return self.crtyd(t)


# ----------------------------------------------------------------------------- the rules
def _refs(arg, parts):
    """A list of refs, or a regex string ('^C1[0-9]$') matched against every part."""
    if isinstance(arg, str):
        rx = re.compile(arg)
        return sorted(r for r in parts if rx.search(r))
    return list(arg)


def back_refs(rules):
    """The parts the intent puts on the board's UNDERSIDE: every `side` rule with side "B".

    ⚠ TWO-SIDED PLACEMENT IS OPT-IN (lead, 2026-11-13). With no such rule nothing anywhere in
    the flow changes: place_init takes its one-sided path and every board places
    byte-identically. A back-side part is still checked by the `side` rule itself."""
    return sorted({r["ref"] for r in rules if r.get("kind") == "side" and r.get("side") == "B"})


def mirror_back(parts, refs):
    """parts with each ref in refs turned over: side "B", local geometry mirrored y -> -y.

    WHY y AND NOT x: layout.py flips a back_refs part with Flip(pos, False) and THEN sets its
    rotation. Measured on KiCad 10 (S4B-XH-SM4, 2026-11-13): the flip is a left-right mirror
    at orientation 180, and SetOrientationDegrees(rot) turns that by rot - 180. In this
    frame (+Y up) that is R(rot) applied to the footprint mirrored y -> -y -- so a mirrored
    part placed like any other lands where layout puts it. Idempotent: a part already on
    "B" is left alone."""
    out = dict(parts)
    for ref in refs:
        p = parts[ref]
        if p.get("side") == "B":
            continue
        q = dict(p, side="B")
        q["pads"] = [dict(d, xy=[d["xy"][0], -d["xy"][1]], rot=(-d.get("rot", 0.0)) % 360.0)
                     for d in p["pads"]]
        if p.get("crtyd"):
            q["crtyd"] = [[x, -y] for x, y in p["crtyd"]][::-1]
        if p.get("fab"):
            f = p["fab"]
            q["fab"] = [f[0], f[1], -f[3], -f[2]]
        if p.get("at"):
            q["at"] = [p["at"][0], -p["at"][1], p["at"][2]]
        out[ref] = q
    return out


def _hull2(pts):
    """Convex hull (monotone chain) of 2-D points, counter-clockwise, as [[x, y]]."""
    pts = sorted(set((round(x, 4), round(y, 4)) for x, y in pts))
    if len(pts) < 3:
        return [list(q) for q in pts]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for q in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    for q in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], q) <= 0:
            hi.pop()
        hi.append(q)
    return [list(q) for q in lo[:-1] + hi[:-1]]


def reach_envelope(part, rule, n=24):
    """The local-frame points an `access` or `mate` rule reserves round its part, or None when the
    reach cannot be stated in the part's own frame (a mate along a BOARD direction: it turns with
    the part's rotation, which placement chooses -- the gate still checks it).
      access: a tool_d circle round the part's pads (its courtyard centre when padless);
      mate:   the body (fab box), swept `length` along an L-direction (or just the body for
              "up"), grown by `clear` on every side."""
    loc = part.get("crtyd") or []
    if rule["kind"] == "access":
        if "tool_d" not in rule:
            return None
        pads = [q["xy"] for q in part.get("pads", ()) if q.get("xy") is not None] or loc or [[0.0, 0.0]]
        cx, cy = sum(q[0] for q in pads) / len(pads), sum(q[1] for q in pads) / len(pads)
        rad = float(rule["tool_d"]) / 2.0 / math.cos(math.pi / n)     # the polygon circumscribes the circle
        return [(cx + rad * math.cos(2 * math.pi * k / n), cy + rad * math.sin(2 * math.pi * k / n)) for k in range(n)]
    if rule["kind"] == "mate":
        d = rule.get("dir", "up")
        if d != "up" and not d.startswith("L"):
            return None
        f = part.get("fab")
        if f:
            box = [(f[0], f[2]), (f[1], f[2]), (f[1], f[3]), (f[0], f[3])]
        elif loc:
            box = [tuple(q) for q in loc]
        else:
            return None
        if d != "up":
            ux, uy = DIRS[d[1:]]
            L_ = float(rule.get("length", 0.0))
            box = box + [(x + ux * L_, y + uy * L_) for x, y in box]
        c = float(rule.get("clear", 0.0))
        return [(x + sx * c, y + sy * c) for x, y in _hull2(box) for sx in (-1, 1) for sy in (-1, 1)]
    return None


# ── which stage honours each intent kind, and what stops a flow when a hard one breaks ─────
# ⚠ THREE RULES THAT SILENTLY DID NOTHING IN ONE DAY (brain_board 2026-11-22): `tight` named only pin
# satellites its stage cannot move; declared copper was no obstacle to a released part; `access`
# (and `mate`) were only score terms, and the hard BROKEN gate listed neither. test_intent_kinds.py
# holds this table against the code: every kind check() knows has an entry, every entry names a
# stage that reads it, and every kind that can be hard has a gate.
#   place:  the placement stages that honour it -- "init" (place_init seating / its quadratic and
#           local stages, SOFT_KINDS), "cells" (place_cells), "grow" (grow_reach: the courtyard holds
#           it), "flow" (place_flow itself), "layout" (the router model: router/model.py),
#           "expand" (place_intent turns it into other rules or widths: auto_pour -> `pour`, current -> widths), "check" (no stage seats it: check() alone, so a hard one only refuses -- array)
#   gate:   "broken" (place_flow's BROKEN hard rules), "near" (_near_broken), "region" (the region
#           leak stop), "pad_copper" (place_flow's PAD ON DECLARED COPPER stop), None (not gated)
#   hard:   the default when a rule says nothing (the soft optimiser kinds are soft unless asked)
KINDS = {
    "outline":   dict(place=("init",), gate="broken", hard=True),
    "keepout":   dict(place=("init", "cells"), gate="broken", hard=True),
    "hole":      dict(place=("init", "cells"), gate="broken", hard=True),
    "height":    dict(place=("init",), gate="broken", hard=True),
    "fixed":     dict(place=("init", "cells"), gate="broken", hard=True),
    "pin":       dict(place=("init", "cells"), gate="broken", hard=True),
    "panel":     dict(place=("init", "cells", "flow"), gate="broken", hard=True),
    "group":     dict(place=("init", "cells"), gate="broken", hard=True),
    "rot":       dict(place=("init",), gate="broken", hard=True),
    "side":      dict(place=("init",), gate="broken", hard=True),
    "access":    dict(place=("init", "grow"), gate="broken", hard=True),
    "mate":      dict(place=("grow",), gate="broken", hard=True),
    "array":     dict(place=("check",), gate=None, hard=False),       # hard is refused: check() raises
    "near":      dict(place=("init",), gate="near", hard=True),
    "decap":     dict(place=("init",), gate="broken", hard=True),
    "between":   dict(place=("init",), gate="broken", hard=False),
    "thermal":   dict(place=("init", "cells"), gate="broken", hard=False),
    "apart":     dict(place=("init", "cells"), gate="broken", hard=False),
    "chain":     dict(place=("init",), gate="broken", hard=False),
    "tight":     dict(place=("init",), gate="broken", hard=False),
    "in_region": dict(place=("init", "cells"), gate="region", hard=True),
    "region":    dict(place=("init",), gate=None, hard=False),
    "current":   dict(place=("expand",), gate=None, hard=False),
    "pour":      dict(place=("flow",), gate=None, hard=False),
    "auto_pour": dict(place=("expand",), gate=None, hard=False),
    "copper":    dict(place=("flow", "init"), gate="pad_copper", hard=True),   # other nets' pads keep off it
}
GATE_KINDS = tuple(k for k, v in KINDS.items() if v["gate"] == "broken")


# ⚠ EVERY HOLD SAYS WHY IT HOLDS (user 2026-11-22: "it feels like an oversight having previous
# decisions limit us now without a clear reason"). 365 of the brain board's 393 `fixed` rules
# were where an earlier layout or window round happened to leave a part, written as hard
# holds with no reason and no expiry; they stacked up until no placer could act on overflow.
# A `fixed` rule carries "hold": one of HOLD_CLASSES, and a `why` naming the specific need:
#   mate        a connector / plug's partner sets where it is (a ribbon's IDC, a module socket)
#   mechanical  the enclosure, a panel, a screw, a bearing or the string fan sets it
#   user        the user ruled it (cite the ruling in src)
#   physical    the circuit needs it there (an isolation barrier straddle, a kelvin tie, an
#               optical sensing column)
#   snapshot    a REMEMBERED POSITION: where an earlier layout left it -- not a constraint
# place_flow stops on a `fixed` rule with no class or no why (check_holds), and prints the
# HOLDS line by class on every run.
HOLD_CLASSES = ("mate", "mechanical", "user", "physical", "snapshot")


def hold_class(rule):
    """A `fixed` rule's hold class ("snapshot": true is the older spelling of hold "snapshot"),
    or None when it has none."""
    if rule.get("kind") != "fixed":
        return None
    if rule.get("snapshot"):
        return "snapshot"
    return rule.get("hold")


def is_snapshot(rule):
    """A `fixed` hold of class "snapshot" is a REMEMBERED POSITION (where an earlier layout or a
    window round left the part), not a constraint (lead 2026-11-22). place_init still seats the
    part there, but a re-placement may move it under every hard-rule gate. Mate, mechanical,
    user and physical holds (HOLD_CLASSES) are constraints."""
    return hold_class(rule) == "snapshot"


def check_holds(rules):
    """(counts, problems) over every `fixed` rule: counts by hold class (+ "transient" for
    window scaffolding -- transient region / in_region / keepout / fixed rules), and one line
    per hold with no class, an unknown class, a snapshot flag contradicting its class, or no
    `why`. A problem stops place_flow."""
    counts, bad = {}, []
    for i, r in enumerate(rules):
        if r.get("transient") and r.get("kind") in ("region", "in_region", "keepout", "fixed"):
            counts["transient"] = counts.get("transient", 0) + 1
        if r.get("kind") != "fixed":
            continue
        c = hold_class(r)
        if r.get("snapshot") and r.get("hold") not in (None, "snapshot"):
            bad.append("rule %d: %s is snapshot=true but hold %r" % (i, r.get("ref"), r.get("hold")))
        elif c not in HOLD_CLASSES:
            bad.append("rule %d: %s fixed with %s" % (i, r.get("ref"), "no hold class" if c is None
                                                       else "unknown hold class %r" % c))
        elif not str(r.get("why", "")).strip():
            bad.append("rule %d: %s fixed (%s) with no why" % (i, r.get("ref"), c))
        counts[c] = counts.get(c, 0) + 1
    return counts, bad


def is_hard(rule):
    """A rule's hardness: its own `hard`, else its kind's default (KINDS)."""
    if "hard" in rule:
        return bool(rule["hard"])
    return KINDS.get(rule.get("kind"), {}).get("hard", True)

def grow_reach(parts, rules):
    """parts with each `access` / `mate` part's courtyard grown to hold what the rule reserves (the
    hull of the courtyard and reach_envelope), so every placer and check keeps neighbours out of
    a probe's or a plug's reach -- a reach rule that is only a score term is not one. Returns
    (parts, [refs grown]); idempotent.

    ⚠ `access` AND `mate` WERE ONLY SCORE TERMS (brain_board sqah, 2026-11-22): hard access on seven
    test pads placed cell for cell like soft (sqak), 5 of 7 pads still short of quality A33; the
    three hard IDC `mate` strokes (J4, J240, J205) had no placement consumer either."""
    out, grown = dict(parts), []
    for r in rules:
        ref = r.get("ref") if r.get("kind") in ("access", "mate") else None
        if ref not in out:
            continue
        p = out[ref]
        env = reach_envelope(p, r)
        if env is None:
            continue
        loc = p.get("crtyd") or []
        hull = _hull2(list(env) + [tuple(q) for q in loc])
        if sorted(tuple(round(v, 4) for v in q) for q in loc) != sorted(tuple(q) for q in hull):
            out[ref] = dict(p, crtyd=hull)
            if ref not in grown:
                grown.append(ref)
    return out, grown


grow_access = grow_reach        # b702a19's name


def panel_face(rule):
    """A panel rule's face as a distance along its edge's outward direction.

    ⚠ `face` IS A DISTANCE, NOT A COORDINATE (lever_sensor holdout 1, 2026-11-12): written cold
    as the -X face's x, -19.46, it put J1 / J2 off the +X edge on top of the sensor, and no
    check said so -- the outline skipped panel parts and the panel check shared the sign. A
    negative `face` is refused; `face_at` takes the coordinate."""
    ux, uy = DIRS[rule["edge"]]
    if "face_at" in rule:
        return float(rule["face_at"]) * (ux + uy)
    f = float(rule["face"])
    if f < 0:
        raise ValueError("panel %s: face %.3f is negative -- `face` is a DISTANCE out from the board centre "
                         "along %s; give the coordinate as face_at" % (rule["ref"], f, rule["edge"]))
    return f


def panel_rot(parts, ref, edge, prefer=None):
    """The turn (0/90/180/270) that points ref's mouth at `edge`. The mouth is where the body
    stands past the SIGNAL pads (numbered: 1, A5 -- mounting and shield pads, MP / SH / blank,
    sit anywhere): the vector from their centroid to the body's centre, turned,
    must point most nearly along the edge's outward direction; `prefer` on a tie. (Reach
    toward the edge was tried first: a 12 mm-wide side-entry PH reads farther across than
    deep and kept its mouth sideways.)"""
    ux, uy = DIRS[edge]
    best = None
    for rr in (0.0, 90.0, 180.0, 270.0):
        P_ = Placed(parts, {ref: [0.0, 0.0, rr]})
        b_ = np.asarray(P_.body(ref), float)
        sig = [q["num"] for q in parts[ref]["pads"] if re.match(r"^[A-Z]?\d+$", q["num"] or "")]
        sig = sig or [q["num"] for q in parts[ref]["pads"]]
        pads_ = np.array([P_.pad(ref, n_) for n_ in sig] or [[0.0, 0.0]], float)
        v = (b_.max(axis=0) + b_.min(axis=0)) / 2.0 - pads_.mean(axis=0)
        key = (-round(float(v @ (ux, uy)), 3), 0 if prefer is not None and abs(rr - prefer) < 1e-6 else 1)
        if best is None or key < best[0]:
            best = (key, rr)
    return best[1]


def _is_decap_rule(P, ref, target):
    """A near rule from a capacitor (ref C<n>) to a pin whose net one of its lands is on."""
    if not re.match(r"C[0-9]", ref) or "." not in target:
        return False
    ic, num = target.split(".", 1)
    net = next((q.get("net") for q in P.parts.get(ic, {}).get("pads", ()) if q["num"] == num), None)
    return bool(net) and any(q.get("net") == net for q in P.parts.get(ref, {}).get("pads", ()))


def check(rule, P, notes, H=None):
    """[(slack mm, subject, detail)] for one rule against placement P."""
    k = rule["kind"]
    out = []
    parts = P.parts
    if k == "outline":
        poly = notes.get("outline_poly") or _rect(notes["outline_mm"])
        panel = {r["ref"] for r in notes.get("_panel", ())}
        skip = set(rule.get("except", ())) | panel
        for ref in parts:
            if ref in skip:
                continue
            s = float(_edge_dist_inside(poly, P.crtyd(ref)).min())
            out.append((s, ref, "courtyard to Edge.Cuts"))
        # a panel part's BODY may stand past its edge, but its pads may not leave the board
        # (holdout 1: J1 / J2 wholly off the board passed every intent check)
        pp = np.asarray(poly, float)
        for ref in sorted(panel - set(rule.get("except", ()))):
            if ref not in parts or ref not in P.pl:
                continue
            pts = np.array([P.pad(ref, q["num"]) for q in parts[ref]["pads"]], float)
            if not len(pts):
                continue
            ins = _inside(pp, pts)
            d = np.min([_seg_dist(pts, pp[i], pp[(i + 1) % len(pp)]) for i in range(len(pp))], axis=0)
            out.append((float(np.where(ins, d, -d).min()), ref, "panel part's pads to Edge.Cuts"))
    elif k == "hole":
        c, keep = np.asarray(rule["xy"], float), rule["d"] / 2.0 + rule.get("keepout", 0.0)
        for ref in parts:
            cy = P.crtyd(ref)
            s = _poly_dist(cy, _circle(c, keep))
            if s < 3.0:
                out.append((s, ref, "to the hole's keep-out at %.2f,%.2f" % tuple(c)))
    elif k == "keepout":
        poly = rule["poly"]
        exc = set(rule.get("except", ()))
        for ref in parts:
            if ref in exc or (rule.get("side") and parts[ref]["side"] != rule["side"]):
                continue
            s = _poly_dist(P.crtyd(ref), poly)
            if s < 3.0:
                out.append((s, ref, "to keep-out %s" % rule.get("name", "")))
    elif k == "height":
        H = H if H is not None else heights()
        for ref in parts:
            h = part_height(ref, parts, H, notes)
            if h is None:
                continue
            if _poly_dist(P.crtyd(ref), rule["poly"]) < 0:
                out.append((rule["max_mm"] - float(h), ref, "%.2f tall under a %.2f limit" % (h, rule["max_mm"])))
    elif k == "panel":
        ref, e = rule["ref"], rule["edge"]
        ux, uy = DIRS[e]
        b = P.body(ref)
        front = float((b @ (ux, uy)).max())
        want = panel_face(rule) + rule.get("overhang", 0.0)
        out.append((-abs(front - want) + rule.get("tol", 0.05), ref,
                    "body front %.3f, the panel wants %.3f" % (front, want)))
        if "at" in rule:
            along = (0.0, 1.0) if ux else (1.0, 0.0)      # `at` is the board's own y (or x)
            mid = float(((b @ along).max() + (b @ along).min()) / 2.0)
            out.append((-abs(mid - rule["at"]) + rule.get("tol", 0.05), ref,
                        "centre along the edge %.3f, wanted %.3f" % (mid, rule["at"])))
        # ⚠ THE BODY FRONT IS NOT THE COPPER (motor_ctrl trial v1, gap 6, 2026-11-11): J2/J6's
        # side-entry bodies sat on the floor edge as asked, and their mounting pads lay inside
        # the 0.3 mm copper-to-edge clearance -- four DRC copper_edge_clearance. Every pad's
        # far side must stay edge_clear (layout's m_CopperEdgeClearance) inside the outline's
        # edge on that side.
        poly = np.asarray((notes or {}).get("outline_poly") or _rect((notes or {}).get("outline_mm", (1e3, 1e3))), float)
        edge = float((poly @ (ux, uy)).max())
        ec = float(rule.get("edge_clear", 0.3))
        x0, y0, a0 = P.at(ref)
        worst = None
        for q in P.parts[ref]["pads"]:
            w, h = q["size"]
            c = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
            loc = _rot(c, q.get("rot", 0.0)) + q["xy"]
            far = float((P.world(ref, loc) @ (ux, uy)).max())
            if worst is None or far > worst[0]:
                worst = (far, q["num"])
        if worst is not None:
            out.append((edge - ec - worst[0], ref, "pad %s %.3f from the %s edge, copper wants %.2f"
                        % (worst[1], edge - worst[0], e, ec)))
    elif k == "mate":
        ref, d, L_ = rule["ref"], rule["dir"], rule["length"]
        clear = rule.get("clear", 0.0)
        b = P.body(ref)
        if d == "up":
            env = b
        else:
            ux, uy = _dir(d, P.at(ref)[2])
            env = np.concatenate([b, b + (ux * L_, uy * L_)])
            env = _hull(env)
        for o in parts:
            if o == ref:
                continue
            s = _poly_dist(P.crtyd(o), env) - clear
            if s < 3.0:
                out.append((s, o, "to %s's %s insertion stroke" % (ref, d)))
    elif k == "access":
        t = rule.get("ref")
        pt = np.asarray(rule["xy"], float) if "xy" in rule else P.target(t).mean(axis=0)
        rad = rule["tool_d"] / 2.0
        for o in parts:
            if o == t:
                continue
            s = _poly_dist(P.crtyd(o), _circle(pt, rad))
            if s < 3.0:
                out.append((s, o, "to the %s access (%.1f tool) at %s" % (rule.get("side", "top"),
                                                                          rule["tool_d"], t or tuple(pt))))
    elif k in ("fixed", "pin"):
        ref = rule["ref"]
        x, y, r = P.at(ref)
        wx, wy = rule["xy"]
        dr = abs((r - rule.get("rot", r) + 180.0) % 360.0 - 180.0)
        out.append((rule.get("tol", 0.01) - math.hypot(x - wx, y - wy) - (1e3 if dr > 0.5 else 0.0),
                    ref, "at %.3f,%.3f r%g, fixed %.3f,%.3f r%g" % (x, y, r, wx, wy, rule.get("rot", r))))
    elif k == "group":
        ax, ay, ar = P.at(rule["anchor"])
        for ref, (dx, dy, dr) in rule["members"].items():
            wx, wy = np.asarray([ax, ay]) + _rot([[dx, dy]], ar)[0]
            x, y, r = P.at(ref)
            bad = abs((r - (ar + dr) + 180.0) % 360.0 - 180.0) > 0.5
            out.append((rule.get("tol", 0.01) - math.hypot(x - wx, y - wy) - (1e3 if bad else 0.0),
                        ref, "in %s's cell: off by %.3f%s" % (rule["anchor"], math.hypot(x - wx, y - wy),
                                                            ", turned" if bad else "")))
    elif k == "in_region":
        poly = notes["_regions"][rule["region"]]
        for ref in _refs(rule["refs"], parts):
            s = float(_edge_dist_inside(poly, P.crtyd(ref)).min())
            out.append((s, ref, "inside region %s" % rule["region"]))
    elif k in ("apart", "thermal"):
        a = _refs(rule.get("a") or [rule["ref"]], parts)
        b = _refs(rule.get("b") or rule["others"], parts)
        m = rule.get("min_mm", rule.get("apart_mm"))
        fx = set(rule.get("fixed", ()))          # a pair of fixed parts is the CAD's, not a breach
        for x in a:
            ds = [(_poly_dist(P.crtyd(x), P.crtyd(y)), y) for y in b if y != x and not (x in fx and y in fx)]
            if not ds:
                continue
            best = min(ds)
            out.append((best[0] - m, x, "%.2f from %s, wants %.2f" % (best[0], best[1], m)))
    elif k == "decap":
        cap, pin = rule["cap"], rule["pin"]
        ic, num = pin.split(".", 1)
        net = next(q["net"] for q in parts[ic]["pads"] if q["num"] == num)
        pp = P.pad(ic, num)
        cp = P.pads_on(cap, net)
        if not cp:
            out.append((-99.0, cap, "has no land on %s (%s's net)" % (net, pin)))
        else:
            # `also`: further pins of the same IC and net this one cap serves -- judged by the
            # farthest (auto_decaps, when an IC has fewer caps than supply pins)
            d, at = max((min(math.hypot(*(c - P.pad(ic, n_))) for c in cp), "%s.%s" % (ic, n_))
                        for n_ in [num] + [x.split(".", 1)[1] for x in rule.get("also", ())])
            out.append((rule.get("max_mm", 1.5) - d, cap, "%.2f from %s (%s)" % (d, at, net)))
    elif k == "near":
        ref, t, m = rule["ref"], rule["target"], rule["max_mm"]
        # ⚠ A DECAP IS MEASURED TO ITS PIN'S NEAREST POINT (lead 2026-11-21): a decap at a 3.4 mm
        # inner bar (U205.11) can never be within 1.5 of the bar's centre, and the near end is
        # where its current enters -- C230 read 2.20 (broken) to the centre, 0.49 to the pad.
        # A decap rule = a capacitor (ref C<n>) with a land on the target pin's net; it is
        # measured to the nearest point of that pin's pad rectangle. Every other pin target
        # keeps the CENTRE measure. Flipped no verdict on brain_board (14 of 18 decap rules read
        # 1.37 -> 0.62, all kept), thresholds unchanged.
        if "." not in t:
            d = _poly_dist(P.crtyd(ref), P.target(t))
        elif _is_decap_rule(P, ref, t):
            d = _poly_dist(P.crtyd(ref), P.pad_poly(*t.split(".", 1)))
        else:
            d = float(_edge_dist_inside(P.crtyd(ref), P.target(t)).max() * -1)
        d = max(d, 0.0)
        out.append((m - d, ref, "%.2f from %s" % (d, t)))
    elif k == "between":
        # a part ON the path between two others (a series resistor between driver and load,
        # a transceiver between its connector and the MCU, motor_ctrl trial gap 9): its centre
        # within max_mm of the segment joining the targets (a pad, or a part's centre),
        # projected between the ends -- `near` both cannot say "not off to one side"
        ref = rule["ref"]
        ends = [P.target(t).mean(axis=0) if "." in t else np.asarray(P.at(t)[:2], float)
                for t in (rule["a"], rule["b"])]
        c = np.asarray(P.at(ref)[:2], float)
        v = ends[1] - ends[0]
        u = float(np.clip(np.dot(c - ends[0], v) / (np.dot(v, v) or 1e-9), 0.0, 1.0))
        d = float(np.hypot(*(c - ends[0] - u * v)))
        out.append((rule.get("max_mm", 2.0) - d, ref, "%.2f off the %s-%s line (at %.0f%%)"
                    % (d, rule["a"], rule["b"], 100 * u)))
    elif k == "chain":
        refs = rule["refs"]
        pts = [np.asarray(P.at(r)[:2]) for r in refs]
        hops = sum(math.hypot(*(b - a)) for a, b in zip(pts, pts[1:]))
        straight = math.hypot(*(pts[-1] - pts[0])) or 1e-9
        mr = rule.get("max_ratio", 1.3)
        out.append(((mr - hops / straight) * straight, "->".join(refs),
                    "path %.1f mm against %.1f straight (x%.2f)" % (hops, straight, hops / straight)))
    elif k == "rot":
        ref = rule["ref"]
        r = P.at(ref)[2]
        ok = any(abs((r - a + 180) % 360 - 180) < 0.5 for a in rule["allowed"])
        out.append((0.0 if ok else -1.0, ref, "rot %g, allowed %s" % (r, rule["allowed"])))
    elif k == "side":
        ref = rule["ref"]
        side = "B" if (parts[ref].get("side") == "B" or ref in notes.get("back_refs", ())) else "F"
        out.append((0.0 if side == rule["side"] else -1.0, ref, "on %s" % side))
    elif k == "tight":
        for nm in rule["nets"]:
            pts = [P.pad(ref, q["num"]) for ref, p in P.parts.items() if ref in P.pl
                   for q in p["pads"] if q["net"] == nm]
            if len(pts) >= 2:
                a = np.asarray(pts)
                hp = float(np.ptp(a[:, 0]) + np.ptp(a[:, 1]))
                out.append((rule["max_mm"] - hp, nm, "%.1f mm across, wants %.1f" % (hp, rule["max_mm"])))
    elif k == "current":
        pass                                # a width, not a placement: see widths()
    elif k == "pour":
        poly = pour_poly(rule, P, notes)
        if poly is None:
            out.append((-99.0, rule["net"], "pour: no region %r and no pins along" % rule.get("region")))
        else:
            n = len(pour_foreign(rule, P, poly))
            out.append((-float(n), rule["net"], "pour on %s: %d other net pad(s) inside" % (rule["layer"], n)))
    elif k == "array":
        if rule.get("hard"):
            raise ValueError("array %s is hard, but array has no seating stage: use soft, or seat the parts as a "
                             "`group` (place_intent.KINDS)" % (rule.get("refs"),))
        refs = _refs(rule["refs"], parts)
        ax = 0 if rule["axis"] in ("x", "X") else 1
        pts = sorted(((np.asarray(P.at(r)[:2]), r) for r in refs), key=lambda t: t[0][ax])
        tol = rule.get("tol", 0.02)
        off = [p[1 - ax] for p, _ in pts]
        for (p, r), (q, s) in zip(pts, pts[1:]):
            out.append((tol - abs((q[ax] - p[ax]) - rule["pitch"]), s, "pitch %.3f after %s" % (q[ax] - p[ax], r)))
        for (p, r) in pts:
            out.append((tol - abs(p[1 - ax] - off[0]), r, "off the row by %.3f" % (p[1 - ax] - off[0])))
    elif k in ("region", "auto_pour"):
        pass
    elif k == "copper":
        # declared copper (place_flow._copper): each pin it names must hold one of its track ends
        for lnd in rule.get("on", ()):
            ref, num = lnd.split(".", 1)
            if ref not in P.pl:
                continue
            from matplotlib.path import Path as _Pth
            pp = _Pth(np.asarray(P.pad_poly(ref, num), float))
            ends = [e for t in rule.get("tracks", ()) for e in (t["pts"][0], t["pts"][-1])]
            hit = any(pp.contains_point(e, radius=0.02) or pp.contains_point(e, radius=-0.02) for e in ends)
            out.append((0.0 if hit else -1.0, rule["net"], "copper lands on %s%s" % (lnd, "" if hit else ": NO track end on the pad")))
    else:
        raise ValueError("unknown rule kind %r" % k)
    return out


def _dir(d, rot):
    """'+X' / '-Y' (board) or 'L+X' / 'L-Y' (the part's own frame, turned with it)."""
    if d.startswith("L"):
        v = _rot([DIRS[d[1:]]], rot)[0]
        return float(v[0]), float(v[1])
    return DIRS[d]


def _rect(wh):
    w, h = wh
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


def _circle(c, r, n=24):
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([c[0] + r * np.cos(a), c[1] + r * np.sin(a)], axis=1)


def _hull(pts):
    pts = sorted(map(tuple, np.asarray(pts, float)))

    def half(ps):
        h = []
        for p in ps:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) -
                                   (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, hi = half(pts), half(pts[::-1])
    return np.asarray(lo[:-1] + hi[:-1])


# ----------------------------------------------------------------------------- derived rules
SUPPLY = re.compile(r"^\+|VCC|VDD|VBUS|VREF|LDO|VNEG|VPRE|V5|V3|VMID|VIN|VOUT", re.I)


def _farads(v):
    m = re.match(r"^\s*([0-9.]+)\s*([pnuµm]?)", str(v or ""))
    if not m:
        return None
    return float(m.group(1)) * {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "": 1.0}[m.group(2)]


def _pin_key(p):
    """'U4.13' sorts after 'U4.2': numbers as numbers."""
    r_, n_ = p.split(".", 1)
    return (r_, int(n_) if n_.isdigit() else 1 << 30, n_)


A2_REACH = 5.0       # mm: quality A2's reach from a supply pin to its nearest cap


LEAK_RAIL = 12      # a net on more parts than this is a rail: it says nothing about where a part belongs


def region_leaks(parts, rules):
    """[(region, [refs])]: parts a `fixed` rule holds INSIDE a region they belong to by the
    netlist, that no in_region rule binds there -- held in place, they leak the day the hold
    is released.

    ⚠ WHY (brain_board mV31, 2026-11-18): the analog in_region named its 11 ICs; ~70 audio
    passives stayed in the isolated corner only by their mP0 holds. Released, C1 C41 D7 R10
    were placed across the moat and their copper met it. The same audit found 51 more held
    parts in pd / power / compute / boost with no binding. A part belongs to the region whose
    bound members most of its signal-net neighbours are (rails, nets on > LEAK_RAIL parts,
    ignored). A region rule may list `free` refs that sit in it unbound on purpose (a part
    that straddles the region's edge by design)."""
    bound, owner, free = {}, {}, set()
    for r in rules:
        if r.get("kind") == "in_region":
            for x in r.get("refs") or ():
                bound.setdefault(r["region"], set()).add(x)
                owner.setdefault(x, set()).add(r["region"])
        if r.get("kind") == "region":
            free |= set(r.get("free") or ())
    if not bound:
        return []
    polys = {r["name"]: np.asarray(r["poly"], float) for r in rules if r.get("kind") == "region"}
    members = {}
    for ref, p in parts.items():
        for q in p["pads"]:
            if q.get("net"):
                members.setdefault(q["net"], set()).add(ref)
    out = {}
    for r in rules:
        ref = r.get("ref")
        if r.get("kind") != "fixed" or ref not in parts or ref in owner or ref in free or not r.get("xy"):
            continue
        # ⚠ A TRANSIENT HOLD IS NOT A HOLD THAT GETS RELEASED (brain_board W47, 2026-11-19): a
        # window run holds every part outside the window at the source placement for that run
        # only -- scaffolding, never committed -- so the leak this guards against (a durable
        # hold released later) cannot happen to it. Mark such holds `"transient": true`.
        if r.get("transient"):
            continue
        votes = {}
        for q in parts[ref]["pads"]:
            nm = q.get("net")
            if not nm or len(members.get(nm, ())) > LEAK_RAIL:
                continue
            for o in members[nm] - {ref}:
                for g in owner.get(o, ()):
                    votes[g] = votes.get(g, 0) + 1
        if not votes:
            continue
        g, k = max(votes.items(), key=lambda kv: kv[1])
        if 2 * k < sum(votes.values()) or g not in polys:
            continue
        if _inside(polys[g], np.asarray([r["xy"][:2]], float))[0]:
            out.setdefault(g, []).append(ref)
    return sorted((g, sorted(v)) for g, v in out.items())


STRAY_MIN_VOTES = 2


def region_strays(parts, rules, pl):
    """[(region, ref, where, why_ok)]: parts the netlist says belong to a region (the same vote
    as region_leaks: most of a part's signal-net neighbours bound there) that the placement put
    OUTSIDE it. `where` is the region the part sits in instead ('' for none). A region rule may
    list `away: {ref: why}` for parts that sit outside on purpose; those come back with the why.

    ⚠ THE SIBLING region_leaks DOES NOT SEE (brain_board W47 audit, 2026-11-19): leaks are held
    parts INSIDE their region with no binding; a part already OUTSIDE its region -- Q210 voted
    boost, sitting in compute; U41/R88/R80 voted pd, in compute -- passed both checks."""
    owner, free, away = {}, set(), {}
    for r in rules:
        if r.get("kind") == "in_region":
            for x in r.get("refs") or ():
                owner.setdefault(x, set()).add(r["region"])
        if r.get("kind") == "region":
            free |= set(r.get("free") or ())
            for x, w in (r.get("away") or {}).items():
                away[(r["name"], x)] = w
    if not owner:
        return []
    polys = {r["name"]: np.asarray(r["poly"], float) for r in rules
             if r.get("kind") == "region" and not r["name"].startswith("_")}
    members = {}
    for ref, p in parts.items():
        for q in p["pads"]:
            if q.get("net"):
                members.setdefault(q["net"], set()).add(ref)
    out = []
    for ref in sorted(pl):
        if ref not in parts or ref in owner or ref in free:
            continue
        votes = {}
        for q in parts[ref]["pads"]:
            nm = q.get("net")
            if not nm or len(members.get(nm, ())) > LEAK_RAIL:
                continue
            for o in members[nm] - {ref}:
                for g in owner.get(o, ()):
                    votes[g] = votes.get(g, 0) + 1
        if not votes:
            continue
        g, k = max(votes.items(), key=lambda kv: kv[1])
        # a CLEAR owner only: two or more neighbours and two thirds of the votes. One neighbour,
        # or a part split between two regions (glue at the seam), says nothing about where it
        # belongs -- W47 listed 55 such parts and a real stray would have drowned in them
        if k < STRAY_MIN_VOTES or 3 * k < 2 * sum(votes.values()) or g not in polys:
            continue
        xy = np.asarray([pl[ref][:2]], float)
        if _inside(polys[g], xy)[0]:
            continue
        where = next((n for n, P in polys.items() if _inside(P, xy)[0]), "")
        out.append((g, ref, where, away.get((g, ref), "")))
    return out


def region_fill(rules, parts, pl):
    """[(region, area mm2, courtyards mm2, fill)] -- each placed part counted in the first
    region holding its courtyard's centre. Courtyards only (no halo): the number layout and
    the router see. ⚠ WHY (output_board ob12, 2026-11-13): a floorplan's regions are drawn by
    hand, and one sat at 0.70 beside another at 0.18 with no report saying so."""
    regs = [(r["name"], np.asarray(r["poly"], float)) for r in rules
            if r.get("kind") == "region" and not r["name"].startswith("_")]
    if not regs:
        return []
    P = Placed(parts, pl)

    def area(c):
        c = np.asarray(c, float)
        return abs(float(np.dot(c[:, 0], np.roll(c[:, 1], 1)) - np.dot(c[:, 1], np.roll(c[:, 0], 1)))) / 2.0
    used = {n: 0.0 for n, _ in regs}
    for ref in pl:
        if ref not in parts:
            continue
        c = P.crtyd(ref)
        cen = np.asarray(c).mean(axis=0)[None, :]
        for n, poly in regs:
            if _inside(poly, cen)[0]:
                used[n] += area(c)
                break
    return [(n, area(poly), used[n], used[n] / max(area(poly), 1e-9)) for n, poly in regs]


def auto_switcher(parts, cells=(), gate_mm=8.0, ctrl_mm=5.0, small=5, sw_refs=6):
    """`near` rules for a switching regulator's own loops, read off the netlist's STRUCTURE.

    ⚠ WHY (brain board, 2026-11-13): the LM5122 boost sat in its region with its loads loose.
    The gate drives, FB and VCC came out open in br3 / br4 (1, then 4 open). Pinning each load
    to the controller's pin -- FETs to HO / LO, the FB divider at FB, the VCC cap at VCC, as
    SNVS954H 10.1 asks -- routed every boost net in br5 (2 open, neither the boost's).

    STRUCTURE, NOT PIN NAMES. Our netlists carry none (SKiDL parts built from numbered pins),
    so a rule keyed on "HO" would never fire:
    * SWITCHER: an IC (U*) on a net with an inductor (L*) and at most sw_refs parts -- its SW
      node -- that drives a FET of its own (a gate-drive net, below). A ferrite (FB*) is not an
      inductor here; an integrated converter (FETs inside) gets nothing.
    * GATE DRIVE: a net of exactly two pads, one the switcher's pin and one a FET's (Q*). The
      FET goes within gate_mm of that pin.
    * CONTROL PIN: a net of at most `small` pads joining ONE pin of the switcher and only
      passives (R / C) -- FB, COMP, VCC, RT, SS, UVLO, SLOPE. Each passive goes within ctrl_mm.
    The bootstrap cap (across two of its pins) is auto_decaps' pin-pair rule already. A part
    the author already ties (near / decap / fixed / pin / a group member) is left alone."""
    # ⚠ A SNAPSHOT IS NOT THE AUTHOR'S TIE (brain_board, 2026-11-22): every LM5122 control part
    # was a snapshot hold, so none got its rule, and nothing pulled the cell together when the
    # snapshot was released (the FETs 12-19 mm off their gate pins). A remembered position
    # (is_snapshot) leaves the part to these rules; a mate / mechanical / user / physical hold
    # still does not.
    ruled = {r.get("cap") or r.get("ref") for r in cells
             if r.get("kind") in ("near", "decap", "fixed", "pin") and not is_snapshot(r)}
    ruled |= {m for r in cells if r.get("kind") == "group" for m in r["members"]}
    on = {}                                   # net -> [(ref, num)]
    for ref, p in parts.items():
        for q in p["pads"]:
            if q["net"] and q["num"]:
                on.setdefault(q["net"], []).append((ref, q["num"]))
    # the SW node, not the output rail: a rail touches every IC it feeds (a TPS2553 on the
    # buck's +5V read as a switcher, op / ob / brain), the node only the switcher and its loop
    sw = sorted({u for n, pads in on.items() if any(re.match(r"^L\d", r) for r, _ in pads)
                 and len({r for r, _ in pads}) <= sw_refs
                 for u, _ in pads if re.match(r"^U\d", u)})
    # ⚠ ONLY A CONTROLLER THAT DRIVES ITS OWN FETS (output_panel, 2026-11-13): an integrated
    # buck's loop is inside the package. The LMR33630's two FB rules on output_panel cost a
    # pair fault and 0.5 mm uncoupled (opA 0 / 1 / 1.03 against opB 0 / 0 / 0.52), and that
    # board routed without them. The rules earn their keep on the LM5122 (brain br4 -> br5),
    # which has gate drives: a switcher counts only with one.
    sw = [u for u in sw if any(len(pads) == 2 and sum(1 for r, _ in pads if r == u) == 1
                                and any(re.match(r"^Q\d", r) for r, _ in pads) for pads in on.values())]
    out, seen = [], set()
    for u in sw:
        for n, pads in sorted(on.items()):
            mine = [num for r, num in pads if r == u]
            if len(mine) != 1:
                continue
            others = [(r, num) for r, num in pads if r != u]
            pin = "%s.%s" % (u, mine[0])
            if len(pads) == 2 and re.match(r"^Q\d", others[0][0]):
                cand, mm, what = [others[0][0]], gate_mm, "gate drive"
            elif len(pads) <= small and others and all(re.match(r"^[RC]\d", r) for r, _ in others):
                cand, mm, what = sorted({r for r, _ in others}), ctrl_mm, "control pin"
            else:
                continue
            for ref in cand:
                if ref in ruled or ref in seen:
                    continue
                seen.add(ref)
                out.append({"kind": "near", "ref": ref, "target": pin, "max_mm": mm, "hard": False,
                            "src": "auto_switcher (netlist)",
                            "why": "%s's %s on %s: at the pin (switching regulator layout)" % (u, what, n)})
    return out


GROUND_NET = re.compile(r"^(?:[ADPS]?GND|GND_\w+|\w+_GND)$")


def auto_decaps(parts, notes, values=None, max_mm=3.0, bulk_mm=8.0, bulk_f=1.5e-6, ground=("GND",), more_mm=2.0,
                cells=(), descriptions=None, loose_mm=8.0):
    """Rules for every capacitor across a SUPPLY net (SUPPLY: '+...', VCC, VDD, VBUS, VREF, ...)
    and ground: a small one (< bulk_f) gets `decap` at the nearest IC pin on that net, a bulk
    one `near` that part. The sources considered are ICs, ferrites and inductors (a buck's
    output caps belong to its inductor, a filtered rail's to its bead). values = {ref: '100n'} (read_values); without it every cap is small.
    Signal-net capacitors (crystal loads, RC filters, resets) get no rule: they are the
    circuit's, not the supply's.

    ⚠ ONLY THE FIRST CAP AN IC GETS IS A 3 mm RULE (output_panel R2, 2026-11-10). The routed,
    known-good hand board broke a flat 3 mm on 14 caps at 3-7 mm, and with no trend in the
    package (U1's QFN68 caps at 2.6-3.5, U11's SOT-23 at 4.5): what it kept was ONE cap per
    IC close -- the smallest, the high-frequency loop -- and the rest within ~5. So per IC,
    smallest value first, the first cap gets max_mm at weight 1, every further one
    max_mm + more_mm at weight 0.5: a rule refinement can trade, never one that packs caps
    round a fine-pitch part at the cost of its escapes."""
    # ⚠ A SPLIT GROUND IS GROUND (output_board mN replay, 2026-11-14): the audio section's caps
    # sit across +3V3_A / +5V_A and AGND, and with only "GND" counted as ground every one of
    # them fell into the two-pins-of-one-IC branch -- which takes the FIRST IC holding both
    # nets: all nine +3V3_A caps ruled "within 3 mm of U2.4", seven +5V_A caps of U10.6, none
    # placeable, and the converters they serve got none. AGND / DGND / PGND / SGND (and any
    # *_GND) are grounds, so those caps take the supply branch: each at the IC pin it serves.
    split = {q["net"] for p_ in parts.values() for q in p_["pads"]
             if q["net"] and GROUND_NET.match(q["net"])} - set(ground)
    ground = tuple(sorted(set(ground) | {q["net"] for p_ in parts.values() for q in p_["pads"]
                                          if q["net"] and GROUND_NET.match(q["net"])}))
    P = Placed(parts, notes.get("placements", {}))
    placed = bool(notes.get("placements"))
    # ⚠ A STRAP IS NOT A SUPPLY PIN (output_board mP0, 2026-11-15): every netlist pin reads
    # PASSIVE, so the nearest pin on the rail won -- C26 ("DAC CPVDD") went to U3.17, the
    # PCM5102A's XSMT mute strap, and C168 to U33.10, the ISO7740's EN2. A board names its
    # ICs' supply pins once, from the datasheets: notes["supply_pins"] = {"U3": [1, 8, 20]}.
    # A listed IC is decoupled at those pins only (and quality A2 judges only those); an IC
    # not listed keeps the old guess, every pin on the rail.
    # The value is a list of pin numbers, or {number: datasheet name} -- with names, a cap whose
    # description names the pin ("DAC CPVDD", "isolator bypass, U32 VCC2") goes to THAT pin.
    sp_raw = notes.get("supply_pins") or {}
    sp = {u: {str(n) for n in v} for u, v in sp_raw.items()}
    sp_name = {u: {str(n): str(nm).upper() for n, nm in v.items()} for u, v in sp_raw.items() if isinstance(v, dict)}
    is_sup = lambda u, num: u not in sp or str(num) in sp[u]
    # ⚠ A DECLARED SUPPLY PIN MAKES ITS NET A SUPPLY, WHATEVER ITS NAME (brain_board p11,
    # 2026-11-26): VSTBY, U5's input, matched no SUPPLY pattern, so its four caps got no rule
    # at all, and snapshot holds kept them 15-19 mm off U5.2 with nothing said until quality A2.
    declared_sup = {q["net"] for u, pins in sp.items() if u in parts
                    for q in parts[u]["pads"] if q["net"] and str(q["num"]) in pins}
    rules = []
    pinpair = []                 # caps across two pins of one IC: kept out of the supply passes
    ics = [r for r in parts if re.match(r"^(U|FB|L)\d", r)]
    # a cap the intent already places (near / decap / a cell member) is the author's
    # ⚠ A HOLD PLACES A CAP, IT DOES NOT DECOUPLE IT (brain_board mV5, 2026-11-16): `fixed` /
    # `pin` counted as the author's rule, so 111 caps frozen by a placement hold got no decap
    # rule at all -- U21's output cap C152 sat 5.8 mm off VOUT and nothing said so until
    # quality A2 failed the routed board. A held cap still gets its rule: the hold places it,
    # the rule judges it (place_init does not move a fixed part; the intent report shows
    # the breach).
    ruled = {r.get("cap") or r.get("ref") for r in cells if r.get("kind") in ("near", "decap")}
    ruled |= {m for r in cells if r.get("kind") == "group" for m in r["members"]}
    for c in sorted(r for r in parts if re.match(r"^C\d", r)):
        if c in ruled:
            continue
        nets = {q["net"] for q in parts[c]["pads"]}
        # ...but a cap from a split ground to a net that is NOT a supply (ISO9_RAW, POT_RS:
        # an isolated converter's output, a reference) is still a two-pins-of-one-IC cap, as
        # it was when only GND was ground -- the supply branch would drop it
        odd = len(nets) == 2 and bool(nets & split) and not any(SUPPLY.search(n_) for n_ in nets - set(ground))
        if len(nets) == 2 and (odd or not (nets & set(ground))):
            # ⚠ A CAP ACROSS TWO PINS OF ONE IC BELONGS AT THEM (output_panel C4, 2026-11-11):
            # a bootstrap cap (BOOT to SW), a VCC-to-VIN bypass. Not across a supply and
            # ground, so it got no rule, landed 7.8 mm off U5.4 on the net graph, and BOOT
            # went open the moment a pour took some of the corridor. At the pin of the net
            # with fewer pads (BOOT, not SW).
            on = {}
            for u in ics:
                if not re.match(r"^U\d", u):
                    continue
                for q in parts[u]["pads"]:
                    if q["net"] in nets and q["num"]:
                        on.setdefault(u, {}).setdefault(q["net"], q["num"])
            both = sorted(u for u, m in on.items() if len(m) == 2)
            if both:
                u = both[0]
                npads = {n_: sum(1 for p_ in parts.values() for q in p_["pads"] if q["net"] == n_) for n_ in nets}
                n_ = min(sorted(nets), key=lambda x: npads[x])
                pinpair.append({"kind": "decap", "cap": c, "pin": "%s.%s" % (u, on[u][n_]), "max_mm": max_mm,
                              "hard": False, "weight": 1.0, "src": "auto_decaps (netlist)",
                              "assigned": "across two pins of %s" % u,
                              "why": "%s across %s and %s, both pins of %s: at them" % ((c,) + tuple(sorted(nets)) + (u,))})
            continue
        if not (nets & set(ground)) or len(nets) != 2:
            continue
        sup = (nets - set(ground)).pop()
        if not (SUPPLY.search(sup) or sup in declared_sup):
            continue
        cands = []
        for u in ics:
            for q in parts[u]["pads"]:
                if q["net"] == sup and q["num"] and is_sup(u, q["num"]):
                    try:
                        d = min(math.hypot(*(x - P.pad(u, q["num"]))) for x in P.pads_on(c, sup))
                    except (KeyError, ValueError):
                        d = 0.0
                    cands.append((d, "%s.%s" % (u, q["num"])))
        # ⚠ A NAMED PLACE WINS, A CONNECTOR TOO (brain_board mV5, 2026-11-16): brain.py's C59
        # is "+3V3_UI at the UI header J5" (J205 merged). Only ICs, beads and inductors were
        # candidates, so the description named nothing on the list and the nearest IC pin on
        # the rail -- U212.6, the load switch's output 52 mm away -- took it; A2 then failed
        # J205 at 52.8 mm. A description naming ANY part that has a pin on this rail decides
        # it: that part's rail pins are the candidates.
        desc_c = (descriptions or {}).get(c, "")
        named_parts = [x for x in re.findall(r"(?<![A-Za-z0-9])([A-Z]{1,3}[0-9]+)(?![0-9])", desc_c)
                       if x in parts and x != c]
        named_c = []
        for x in named_parts:
            for q in parts[x]["pads"]:
                if q["net"] == sup and q["num"]:
                    try:
                        d = min(math.hypot(*(x_ - P.pad(x, q["num"]))) for x_ in P.pads_on(c, sup))
                    except (KeyError, ValueError):
                        d = 0.0
                    named_c.append((d, "%s.%s" % (x, q["num"])))
        how = None
        if named_c and not any(t[1].split(".")[0] in named_parts for t in cands):
            cands = named_c
            how = "named %s" % ",".join(sorted({t[1].split(".")[0] for t in named_c}))
        # ...and a named part that IS a candidate decides it, whatever its prefix (brain_board C65
        # "U5 buck output HF bypass, at L1": L1 is a source on V5_PRE, but only U-names counted
        # below, so the nearest pin -- U211.1, 26.8 mm off -- took it)
        named_in = [t for t in cands if t[1].split(".")[0] in named_parts]
        if how is None and named_in:
            cands = named_in
            how = "named %s" % ",".join(sorted({t[1].split(".")[0] for t in named_in}))
        if not cands:
            continue
        # ⚠ THE SCHEMATIC SAYS WHOSE IT IS (motor_ctrl trial, 2026-11-11): "U8 switch
        # decoupling", "U7 VCC bypass". Unplaced, the deal gave C35/C37/C38 to the MCU and
        # U8-U10 went without. A description naming an IC on this rail decides it.
        said = [u for u in re.findall(r"(?<![A-Za-z0-9])(U[0-9]+)(?![0-9])", (descriptions or {}).get(c, ""))
                if any(t[1].split(".")[0] == u for t in cands)]
        if not said:
            # ...or a role the IC's own description carries: "MCU supply decoupling" and
            # U4 "RISC-V MCU" (all-caps words of three letters or more: MCU, PHY, ADC, LDO)
            words = set(re.findall(r"(?<![A-Za-z])([A-Z]{3,})(?![A-Za-z])", (descriptions or {}).get(c, "")))
            said = sorted({t[1].split(".")[0] for t in cands
                           if words & set(re.findall(r"(?<![A-Za-z])([A-Z]{3,})(?![A-Za-z])",
                                                     (descriptions or {}).get(t[1].split(".")[0], "")))})
            said = said if len(said) == 1 else []
        if said:
            cands = [t for t in cands if t[1].split(".")[0] == said[0]]
            how = how or "said %s" % said[0]
        if sp_name:
            # the description names the pin: "DAC CPVDD" -> the declared CPVDD pin (of the IC
            # it names, if it names one), whatever is nearest today
            words = set(re.findall(r"[A-Z0-9_+]+", (descriptions or {}).get(c, "").upper()))
            named = [t for t in cands if sp_name.get(t[1].split(".")[0], {}).get(t[1].split(".", 1)[1]) in words]
            if named:
                cands = named
                how = how or "pin named"
        if not placed:
            # ⚠ A FRESH BOARD HAS NO DISTANCES (motor_ctrl trial, 2026-11-11): every pin read
            # 0 mm and the "nearest" was the first in sort order -- all eleven +3V3 caps to
            # L1.2, the buck inductor. Unplaced, caps are dealt out: an IC (U) before a
            # source (L, FB), the one holding fewest caps on this rail first.
            # caps per supply pin: a QFN-68 with eight VDD pins takes eight before a SOT-23
            # takes its second
            load = collections.Counter(r_["pin"].split(".")[0] for r_ in rules if r_.get("_rail") == sup)
            npin = collections.Counter(t[1].split(".")[0] for t in cands)
            f_ = _farads((values or {}).get(c))
            if f_ is not None and f_ >= bulk_f:
                # bulk: at the rail's source (inductor, ferrite), else its biggest load
                d, pin = min(cands, key=lambda t: (0 if not t[1].startswith("U") else 1,
                                                   -npin[t[1].split(".")[0]], t[1]))
            else:
                # ...and within the IC, the supply pin holding fewest caps (unplaced, every pin
                # tied and all six of U4's +3V3 caps went to U4.1, the first in sort order)
                pload = collections.Counter(r_["pin"] for r_ in rules if r_.get("_rail") == sup)
                d, pin = min(cands, key=lambda t: (0 if t[1].startswith("U") else 1,
                                                   load[t[1].split(".")[0]] / float(npin[t[1].split(".")[0]]),
                                                   pload[t[1]], _pin_key(t[1])))
        else:
            d, pin = min(cands)
        # ⚠ SAY WHEN THE PART WAS A GUESS (lead 2026-11-26, brain_board C65 / C119): a cap whose
        # description names no part on its rail goes to the nearest supply pin (placed) or is dealt
        # out (unplaced). C65 "buck output HF bypass" went to U211.1 on V5_PRE and sat 26.8 mm off
        # it under a snapshot before anyone saw. `assigned` says how each cap's part was chosen;
        # "fallback ..." is printed by place_flow on the first run, with the part it picked.
        how = how or ("fallback: nearest of %d %s pin(s)" % (len(cands), sup) if placed
                      else "fallback: dealt out among %d %s pin(s), unplaced" % (len(cands), sup))
        f = _farads((values or {}).get(c))
        if f is not None and f >= bulk_f:
            rules.append({"kind": "near", "ref": c, "target": pin.split(".")[0], "max_mm": bulk_mm, "hard": False,
                          "why": "%s, bulk on %s: beside the IC it feeds" % (c, sup), "src": "auto_decaps (netlist)",
                          "assigned": how})
        else:
            rules.append({"kind": "decap", "cap": c, "pin": pin, "max_mm": max_mm, "hard": False, "weight": 1.0,
                          "why": "%s across %s and ground: at its supply pin" % (c, sup), "src": "auto_decaps (netlist)",
                          "_f": f if f is not None else 0.0, "_rail": sup, "assigned": how})
    # ⚠ EVERY IC ON A RAIL GETS ONE (optical fold, 2026-11-11). Nearest-pin assignment let
    # U6's eight +3V3D pins take every +3V3D cap, and the LDO U8 whose OUTPUT is +3V3D got
    # none: quality A2 failed U8.2 (nearest cap 5.4 mm). And on a fresh board, with no
    # placements, every distance is 0 and the nearest pin is just the first in sort order.
    # So: an IC with a pin on a supply rail and no cap of its own there takes a cap from the
    # IC holding the most on that rail -- that IC's largest, last-sorted -- never its last one.
    # cells: the intent's `group` rules -- an IC in a designed cell has its caps in the cell
    # (optical's converters U14-U18: their Cs/Ci/Cm), so it is never given one here.
    by = {}
    for r in rules:
        if r["kind"] == "decap":
            by.setdefault(r["pin"].split(".")[0], []).append(r)
    rail = lambda r: (set(q["net"] for q in parts[r["cap"]]["pads"]) - set(ground)).pop()
    have = {(r.get("target") or r["pin"].split(".")[0], rail(r) if r["kind"] == "decap" else
             (set(q["net"] for q in parts[r["ref"]]["pads"]) - set(ground)).pop()) for r in rules}
    incell = {r["anchor"] for r in cells if r.get("kind") == "group"} | {
        m for r in cells if r.get("kind") == "group" for m in r["members"]}
    for u in sorted(x for x in ics if re.match(r"^U\d", x) and x not in incell):
        for net in sorted({q["net"] for q in parts[u]["pads"] if q["net"] and SUPPLY.search(q["net"])
                           and is_sup(u, q["num"])}):
            # declared supply pins (notes supply_pins): EVERY one gets a cap within A2's reach,
            # not one per IC and rail -- U3's CPVDD / AVDD / DVDD sit on three sides of the TSSOP
            if u in sp:
                uxy = {q["num"]: q["xy"] for q in parts[u]["pads"]}
                todo = sorted({q["num"] for q in parts[u]["pads"] if q["net"] == net and is_sup(u, q["num"])},
                              key=lambda n_: _pin_key("%s.%s" % (u, n_)))
            else:
                if (u, net) in have:
                    continue
                todo = [None]
            for wp in todo:
                if wp is not None:
                    mine_u = [r for r in by.get(u, []) if rail(r) == net]
                    if any(r["pin"].split(".", 1)[1] in uxy and wp in uxy and math.hypot(
                            uxy[wp][0] - uxy[r["pin"].split(".", 1)[1]][0],
                            uxy[wp][1] - uxy[r["pin"].split(".", 1)[1]][1]) <= A2_REACH - max_mm
                           for r in mine_u):
                        continue
                # a donor keeps a cap for each of ITS declared supply pins on the rail (one, if
                # it declares none): only a surplus is given
                need_ = lambda d_: max(1, len({q["num"] for q in parts[d_]["pads"] if q["net"] == net
                                                and q["num"] and is_sup(d_, q["num"])})) if d_ in sp else 1
                donors = sorted(((len([r for r in rs if rail(r) == net]) - need_(d), d) for d, rs in by.items()
                                 if d != u and d in parts), reverse=True)
                if not donors or donors[0][0] < 1:
                    continue
                d = donors[0][1]
                # the cap whose pin has ANOTHER capped pin nearest it in the IC's own frame
                # (placement-independent): that neighbour's cap is tightened to max_mm and serves
                # both. (Taking the largest instead left U6.171/172 at 5.7/6.1 mm: A2 judges pins.)
                xy = {q["num"]: q["xy"] for q in parts[d]["pads"]}
                mine = [r for r in by[d] if rail(r) == net]

                def gap(r):
                    a_ = xy.get(r["pin"].split(".", 1)[1])
                    o_ = [math.hypot(a_[0] - xy[x["pin"].split(".", 1)[1]][0], a_[1] - xy[x["pin"].split(".", 1)[1]][1])
                          for x in mine if x is not r and a_ is not None and x["pin"].split(".", 1)[1] in xy]
                    return (min(o_) if o_ else 1e9, -r.get("_f", 0.0), r["cap"])
                give = min(mine, key=gap)
                g_ = gap(give)[0]
                if 1e-6 < g_ < 1e9:
                    a_ = xy[give["pin"].split(".", 1)[1]]
                    keep_ = min((x for x in mine if x is not give),
                                key=lambda x: math.hypot(a_[0] - xy[x["pin"].split(".", 1)[1]][0],
                                                         a_[1] - xy[x["pin"].split(".", 1)[1]][1]))
                    keep_["_tight"] = True
                    keep_["also"] = keep_.get("also", []) + [give["pin"]]
                    keep_["why"] += " (also serves %s, %.1f mm along the package: its cap went to %s)" % (
                        give["pin"], g_, u)
                by[d].remove(give)
                give.pop("also", None)                     # it serves its new IC, nothing of the old
                give.pop("_tight", None)
                num = wp if wp is not None else next(q["num"] for q in parts[u]["pads"] if q["net"] == net and q["num"])
                give["pin"] = "%s.%s" % (u, num)
                give["why"] = "%s across %s and ground: %s's own (it had none; given by %s)" % (give["cap"], net, u, d)
                give["assigned"] = "given to %s by %s (every IC on a rail gets one)" % (u, d)
                by.setdefault(u, []).append(give)
                have.add((u, net))
    # ⚠ ONE TIGHT CAP PER SUPPLY PIN; EXTRA CAPS GO LOOSE (lead ruling, motor_ctrl from
    # footprints, 2026-11-11). U4.1 and U4.68 (+3V3, 1 mm apart round the corner) each got a
    # cap seated at the pin; with the crystal's paths reserved on that edge, C8 had no seat
    # within 5 mm and was re-seated round the IC into U4's other escapes -- four nets open.
    # A2 judges a PIN by the nearest cap within A2_REACH: a tight cap (<= max_mm off its pin)
    # covers every pin within A2_REACH - max_mm of it along the package. A cap whose pin is
    # already so covered becomes a loose `near` the IC (loose_mm, weight 0.5): it stays on the
    # rail beside the part without taking a seat from the pins' escape room.
    cover = A2_REACH - max_mm
    for d, rs in by.items():
        if not re.match(r"^U\d", d):
            continue
        xy = {q["num"]: q["xy"] for q in parts[d]["pads"]}
        tight = {}                  # per RAIL: a +3V3D cap does not cover a +3V3A pin (optical U6.38)
        for r in sorted(rs, key=lambda r: (r["_f"], r["cap"])):
            pins = [r["pin"]] + list(r.get("also", ()))
            pts = [xy[x.split(".", 1)[1]] for x in pins if x.split(".", 1)[1] in xy]
            tr = tight.setdefault(rail(r), [])
            if pts and tr and all(min(math.hypot(a_[0] - b_[0], a_[1] - b_[1]) for b_ in tr) <= cover
                                  for a_ in pts):
                r["kind"], r["ref"], r["target"] = "near", r.pop("cap"), d
                r["max_mm"], r["weight"] = loose_mm, 0.5
                r["why"] += " -- %s is covered by a tight cap within %.1f mm along the package: loose, beside %s" % (
                    r.pop("pin"), cover, d)
                r.pop("also", None)
                r["_loose"] = True
                continue
            tr += pts
    for d in list(by):
        by[d] = [r for r in by[d] if not r.get("_loose")]
    for rs in by.values():
        for k, r in enumerate(sorted(rs, key=lambda r: (r["_f"], r["cap"]))):
            if r.get("also"):
                r["max_mm"], r["weight"] = max_mm + more_mm, 1.0     # between its pins, at the reach A2 judges
            elif k:
                r["max_mm"], r["weight"] = max_mm + more_mm, 0.5
                r["why"] += " (a further cap on this IC: within reach, not packed)"
    # ...and a TRUE pin pair's further caps at the same pin get within reach, not packed, as
    # the supply branch's do (lead, 2026-11-14): the first max_mm at weight 1, every further
    # one max_mm + more_mm at 0.5 -- never a rule no placement can meet
    seen = {}
    for r in pinpair:
        k = seen.get(r["pin"], 0)
        seen[r["pin"]] = k + 1
        if k:
            r["max_mm"], r["weight"] = max_mm + more_mm, 0.5
            r["why"] += " (a further cap at this pin: within reach, not packed)"
    for r in rules:
        r.pop("_f", None)
        r.pop("_tight", None)
        r.pop("_rail", None)
        r.pop("_loose", None)
    return rules + pinpair


def auto_singles(parts, ground=("GND",), max_mm=8.0, skip=(), weight=0.5, two_pad=False):
    """A `near` rule for every part with ONE signal net (test pads, a lone jumper or probe
    point): at that net's driver pin -- an IC's pin on the net (most pads first), else the
    pin of the part with most pads. Placement-independent, so a fresh board gets it too.

    ⚠ WHY (output_panel intent board, 2026-11-11): TP1 (SWDIO's probe pad) was free, landed
    12 mm from U1.48 on the net graph's average, and SWDIO stayed open through a round of
    refinement that never got to it. A single-net part belongs at its pin; said once here,
    place_init puts it there as a satellite.

    ⚠ TEST PADS ONLY BY DEFAULT, LOOSE (lead ruling 2026-11-11). Applied to every two-pad
    part whose other end is ground as well (pull-downs, filter caps), a 5 mm rule put 26
    satellites against U1's pins and routed 4 open against 1: where a pull-up goes is a
    judgement about escapes. two_pad=True opts those in."""
    rules = []
    for ref in sorted(parts):
        if ref in skip:
            continue
        pads = parts[ref]["pads"]
        nets = {q["net"] for q in pads if q["net"]} - set(ground)
        if len(nets) != 1 or SUPPLY.search(next(iter(nets))) or "GND" in next(iter(nets)):
            continue
        # a test pad, or a two-pad part whose other end is ground (pull-down, filter cap,
        # clamp); never a connector, whose place is the mechanical design's
        if not (re.match(r"^TP\d", ref) or (two_pad and len(pads) == 2 and re.match(r"^[RCD]\d", ref))):
            continue
        net = nets.pop()
        cands = []
        for o, p in parts.items():
            if o == ref:
                continue
            for q in p["pads"]:
                if q["net"] == net and q["num"]:
                    cands.append((0 if re.match(r"^U\d", o) else 1, -len(p["pads"]), o, q["num"]))
        if not cands:
            continue
        _, _, o, num = min(cands)
        rules.append({"kind": "near", "ref": ref, "target": "%s.%s" % (o, num), "max_mm": max_mm, "hard": False,
                      "weight": weight,
                      "why": "%s carries only %s: at its driver pin" % (ref, net), "src": "auto_singles (netlist)"})
    return rules


SENSITIVE = re.compile(r"(^|_)(V?REF\w*|VMID|MID(_RAW|_BUF)?|AREG|AVDD|AIN\w*|ADC\w*_IN\w*|ADC_IN|\w*_IN_\d\w*|"
                       r"TIA\w*|PICKUP\w*|SENSE\w*)$", re.I)
XTAL_NET = re.compile(r"(^|_)(OSC_(IN|OUT)|\w*_X[IO]|X[IO]|XTAL\w*)$", re.I)
NOISY_EDGE = re.compile(r"(^|_)(USB\w*|VBUS|\w*_D[PM]|RELAY\w*)$", re.I)


def auto_floorplan(parts, sensitive=SENSITIVE, noisy=NOISY_EDGE, xtal=XTAL_NET, switch_mm=10.0, edge_mm=6.0, skip=(),
                   ground=("GND",)):
    """Default noise floorplan from the netlist: `apart` rules between what radiates and
    what listens. A fresh board gets them for free, like auto_decaps.

      switchers   an inductor on a small non-supply net shared with an IC pin (a buck's SW
                  node): the inductor, the IC and every part on that node. Apart from
                  EVERY sensitive part by switch_mm, weight 1.
      noisy edges relays (K*) and the parts carrying USB (an IC or connector with a pin on
                  a net matching `noisy`). Apart from the ANALOG sensitive parts (not the
                  crystals -- a PHY's crystal belongs at the PHY) by edge_mm, weight 0.5.
                  Switch nodes also stay 1.5 x edge_mm off the USB parts: a high-speed
                  pair's path is not where a switcher goes.
      sensitive   crystals (Y*), photodiodes (PD*), every IC with a pin on a net matching
                  `sensitive` (references, MID, ADC/amplifier inputs, the pickup, oscillator
                  legs), and every two-pin part whose non-ground nets are all sensitive (a
                  reference divider's resistors).

    Only the switch-node-to-sensitive rule carries "forbid": true (place_init keeps the
    zone clear when it first drops a part); the edge rules are checked and penalised in the
    local pass, never forbidden.

    ⚠ WHY (output_panel, 2026-11-11): with every rule a forbid zone, the 98 x 56 board
    routed 8 open (vN 0): the USB-edge zones round the hub pushed its own connectors' parts
    away. A dense board cannot honour every 6 mm edge rule; the hand board breaks 10.

    Overridable: pass your own regexes, distances or `skip` refs; a part in both a noisy
    group and the sensitive set is dropped from that rule's sensitive side (a USB codec's
    ADC). Soft rules: the router never sees them, so score.py --intent prints their
    breaches beside the route.

    ⚠ WHY (optical, 2026-11-11): place_init, with the floorplan unsaid, put the buck (U13,
    L1) beside the PHY and 6 mm from the MID divider that feeds all twenty TIAs -- and the
    board routed BETTER than the hand one (210 vias vs 223). A score that only routes
    passes a placement that is electrically wrong; this is the rule that says so."""
    nets = {}
    for r, v in parts.items():
        for q in v["pads"]:
            if q["net"]:
                nets.setdefault(q["net"], set()).add(r)
    rnets = {r: {q["net"] for q in v["pads"] if q["net"]} for r, v in parts.items()}
    ic = lambda r: re.match(r"^U\d", r) is not None
    sens, crystals = set(), set()
    for r in parts:
        if r in skip:
            continue
        sig = rnets[r] - set(ground)
        # a crystal and its load caps listen; the MCU / hub / PHY driving it does not
        # (output_panel's U1 and U4 had read as sensitive through OSC_IN / HUB_XI)
        if re.match(r"^Y\d", r) or (len(parts[r]["pads"]) == 2 and any(xtal.search(n) for n in sig)):
            crystals.add(r)
        elif re.match(r"^PD\d", r):
            sens.add(r)
        elif ic(r) and any(sensitive.search(n) for n in sig):
            sens.add(r)
        elif len(parts[r]["pads"]) == 2 and sig and all(sensitive.search(n) for n in sig):
            sens.add(r)
    # ⚠ A SENSITIVE NAME IS NOT ENOUGH FOR A TWO-PIN PART (output_board mJ, 2026-11-13): the
    # power button's SW_SENSE -- 10 V, a zener clamp, a 1 ms RC into a FET gate -- matched
    # SENSE\w*, so its zener D208 and pull-up R254 joined the analog parts and the trial
    # reported the H743 2.26 mm from D208 as a floorplan miss. A two-pin part listens only
    # if a sensitive net of its own reaches something that listens: a sensitive IC, a
    # photodiode, or another such net's part (a divider chain). Ones reaching none leave.
    def _hears(r, seen):
        for n in rnets[r] - set(ground):
            if not sensitive.search(n):
                continue
            for o in nets.get(n, set()) - {r}:
                if o in seen:
                    continue
                if re.match(r"^PD\d", o) or (ic(o) and o in sens):
                    return True
                if o in sens and len(parts[o]["pads"]) == 2 and _hears(o, seen | {r, o}):
                    return True
        return False
    sens -= {r for r in list(sens) if len(parts[r]["pads"]) == 2 and not _hears(r, {r})}
    # ⚠ A PART'S OWN INPUT IS NOT ITS VICTIM (output_board mJ, same day): SENSE_5V /
    # SENSE_24V's divider resistors read as sensitive by name, and the MCU they feed
    # carries USB -- so the rule asked U1 to stand 6 mm off its own ADC dividers. A two-pin
    # sensitive part whose sensitive net lands on a pin of the loud group is that group's
    # input: it belongs AT the group, and leaves that rule's sensitive side.
    def _own(group):
        g = set(group)
        return {r for r in sens if len(parts[r]["pads"]) == 2
                and any(nets.get(n, set()) & g for n in rnets[r] - set(ground) if sensitive.search(n))}
    # the ICs driving a crystal (a pin on an oscillator net): listeners to a switch node only
    xdrivers = {r for r in parts if r not in skip and ic(r) and r not in crystals
                and any(xtal.search(n) for n in rnets[r] - set(ground))}
    rules = []
    for L in sorted(r for r in parts if re.match(r"^L\d", r) and r not in skip):
        for n in sorted(rnets[L]):
            members = nets.get(n, set())
            # ⚠ AN EXTERNAL-FET SW NODE HAS FIVE PARTS (brain_board c5, 2026-11-22): the LM5122's
            # BST_SW joins U220, L204, Q208, Q209 and the bootstrap cap C299. The old limit of 4
            # fitted only integrated converters, so the boost's SW node had no `apart` at all,
            # and the USB hub's crystal Y2 was crowded against L204. Same bound as
            # auto_switcher's sw_refs (6).
            if SUPPLY.search(n) or n in ground or len(members) > 6 or not any(ic(m) for m in members if m != L):
                continue
            grp = sorted(members - set(skip))
            # ⚠ A CRYSTAL'S DRIVER LISTENS TO A SWITCH NODE (brain_board c6, 2026-11-22): the
            # hub U37 seated 1.2 mm off the boost's L204, and its crystal Y2 (hard: <= 4 mm of
            # U37) could not also stand 10 mm off the SW node -- NO ROOM. The driver's XI / XO
            # pins carry the same oscillator as the crystal. It stays out of the USB-edge
            # rules (a PHY's crystal belongs at the PHY), but not out of this one.
            b = sorted((sens | crystals | xdrivers) - set(grp) - _own(grp))
            if b:
                rules.append({"kind": "apart", "a": grp, "b": b, "min_mm": switch_mm, "hard": False, "weight": 1.0,
                              "forbid": True,
                              "why": "switch node %s (%s): off every sensitive part" % (n, " ".join(grp)),
                              "src": "auto_floorplan (netlist)"})
    loud = sorted(r for r in parts if r not in skip and (re.match(r"^K\d", r) or
                  (re.match(r"^[UJ]\d", r) and any(noisy.search(n) for n in rnets[r]))))
    usb = [r for r in loud if not re.match(r"^K\d", r)]
    for r0 in [x for x in rules if x["src"] == "auto_floorplan (netlist)"]:
        b = sorted(set(usb) - set(r0["a"]))
        if b:
            rules.append({"kind": "apart", "a": r0["a"], "b": b, "min_mm": edge_mm * 1.5, "hard": False, "weight": 0.5, "forbid": False,
                          "why": "switch node %s off the USB path (%s)" % (r0["a"], " ".join(b)),
                          "src": "auto_floorplan (netlist)"})
    if loud:
        b = sorted(sens - set(loud) - _own(loud))
        if b:
            rules.append({"kind": "apart", "a": loud, "b": b, "min_mm": edge_mm, "hard": False, "weight": 0.5, "forbid": False,
                          "why": "USB / relay edges (%s) off the analog parts" % " ".join(loud),
                          "src": "auto_floorplan (netlist)"})
    return rules


# ⚠ A PAIR'S PIN ORDER CAN TWIST IT (output_board rob_d1, 2026-11-14). Two rails running side by
# side keep which one is on the left, seen along the run; at each land that order is fixed by the
# pins: the part side they sit on (outward normal n) and which rail is which (d = P - N). Leaving
# end A, s = sign(n_A x d_A); arriving at B, s = sign(-n_B x d_B). Unequal = a TWISTED hop: the
# pair cannot run coupled on one layer, so it either changes layer or one rail detours round a
# land, paying uncoupled mm (USBA / MCU on rob_d1 met the rules that way; USBB / FLASH did not).
# Placement feedback, not a routing rule: NO rotation changes it (a turn keeps orientation, so
# n and d turn together at both ends of any part); a mirror does (one end on the other side),
# and so does re-binding which rail goes to which pin -- free on a pass-through part whose
# channels are identical (a CMC's windings, a clamp's or a USB mux's channels: optical's
# "turn U10 by 180" fixed it because turning a symmetric clamp IS a channel swap), or a
# polarity swap where the IC has one.
def pair_twists(parts, pl, groups):
    """[(group name, ref A, ref B, "twisted" | "straight" | "unknown: why")] for every same-layer
    two-net pair hop: a hop runs between two placed parts that carry both rails."""
    P = Placed(parts, pl)
    out = []

    def normal(ref, q, c):
        sx, sy = q["size"]
        if abs(sx - sy) < 0.1 * max(sx, sy):
            return None                              # a square pad: no long axis
        ax = np.asarray([1.0, 0.0] if sx > sy else [0.0, 1.0])
        if q.get("rot"):
            ax = _rot([ax], float(q["rot"]))[0]
        o = P.world(ref, [[0.0, 0.0]])[0]
        u = P.world(ref, [ax])[0] - o
        u = u / max(np.hypot(*u), 1e-9)
        xy = P.pad(ref, q["num"])
        return u if np.dot(u, xy - c) >= 0 else -u

    def end(ref, qp, qn):
        cy = np.asarray(P.crtyd(ref), float)
        c = (cy.min(axis=0) + cy.max(axis=0)) / 2.0
        a_, b_ = normal(ref, qp, c), normal(ref, qn, c)
        if a_ is None or b_ is None:
            return None, "a square pad on %s" % ref
        if np.dot(a_, b_) < 0.9:
            return None, "%s's two pins face different ways" % ref
        return (a_ + b_) / 2.0, ""

    seen = set()
    for g in groups:
        nets = g.get("nets") or []
        if len(nets) != 2 or not g.get("same_layer", True) or frozenset(nets) in seen:
            continue
        seen.add(frozenset(nets))
        pn, nn = nets
        on = {}
        for ref, v in parts.items():
            if ref not in pl:
                continue
            qp = [q for q in v["pads"] if q.get("net") == pn]
            qn = [q for q in v["pads"] if q.get("net") == nn]
            if qp and qn:
                on[ref] = [(a, b) for a in qp for b in qn]
        refs = sorted(on)
        mid = {r: np.mean([(P.pad(r, a["num"]) + P.pad(r, b["num"])) / 2.0 for a, b in on[r]], axis=0) for r in refs}
        # the hops: the minimum spanning tree over the parts (a chain through a pass-through
        # part, not every pair of parts on the net)
        hops, inn = [], refs[:1]
        while refs and len(inn) < len(refs):
            ra, rb = min(((a, b) for a in inn for b in refs if b not in inn),
                         key=lambda ab: float(np.hypot(*(mid[ab[0]] - mid[ab[1]]))))
            hops.append((ra, rb))
            inn.append(rb)
        def lands(r, other):
            """Every pin pair the pair can leave r from towards `other`: the closest-spaced
            pairs (within 25 %) of the land nearest the other end (within 1 mm).
            ⚠ A LAND CAN OFFER BOTH PIN ORDERS (brain_board fold13, 2026-11-27): a USB-C
            receptacle carries D+ / D- as A6 / A7 and again as B6 / B7, mirrored, so A6-A7,
            A6-B7 and B6-A7 are all 0.5 mm pairs of opposite order. Judging one of them read
            J2 (USBB_J FL4 -> J2) twisted and the identical J1 straight, by which pair a
            0.1 mm rounding put first. The router can leave on either; judge them all."""
            def far(ab):
                return float(np.hypot(*((P.pad(r, ab[0]["num"]) + P.pad(r, ab[1]["num"])) / 2.0 - mid[other])))

            def gap(ab):
                return float(np.hypot(*(P.pad(r, ab[0]["num"]) - P.pad(r, ab[1]["num"]))))
            f0 = min(far(ab) for ab in on[r])
            near = [ab for ab in on[r] if far(ab) <= f0 + 1.0]
            g0 = min(gap(ab) for ab in near)
            return [ab for ab in near if gap(ab) <= 1.25 * g0 + 1e-6]

        for ra, rb in hops:
            verdicts, why = set(), ""
            for qa, qa2 in lands(ra, rb):
                for qb, qb2 in lands(rb, ra):
                    na, wa = end(ra, qa, qa2)
                    nb, wb = end(rb, qb, qb2)
                    if na is None or nb is None:
                        why = why or wa or wb
                        continue
                    da = P.pad(ra, qa["num"]) - P.pad(ra, qa2["num"])
                    db = P.pad(rb, qb["num"]) - P.pad(rb, qb2["num"])
                    sa = np.sign(na[0] * da[1] - na[1] * da[0])
                    sb = np.sign(-nb[0] * db[1] + nb[1] * db[0])
                    verdicts.add("twisted" if sa != sb else "straight")
            out.append((g.get("name") or pn, ra, rb,
                        "straight" if "straight" in verdicts else "twisted" if verdicts else "unknown: " + why))
    return out


def _swap_pairs(part, groups, flip=False):
    """[(pin, pin)] that swap a pass-through part's rails between its identical channels, or None
    when the part is not one: <= 10 pads, only the pins of one or two declared pairs besides
    ground / supply, and every pair's two rails on it equally often (a CMC's windings: FL4 pins
    1/2 and 3/4; a flow-through clamp's channels). Each rail's pin swaps with the other rail's
    nearest pin.
    flip=True: a part the board DECLARES (notes "pair_flip": {ref: datasheet citation}) whose
    rails may all trade paths at once -- a 1:2 USB mux (TS3USB221: the D+ and D- switches are
    one spec, SCDS220M Table 7-1 p.12 selects both alike), any number of pairs plus control
    pins. Every held pair flips together, so polarity end to end is kept (brain_board U17,
    2026-11-19: GADGET/USBA/USBB twisted at U17, all straight flipped)."""
    pads = part.get("pads", ())
    if len(pads) > 10:
        return None
    nets = {q.get("net") for q in pads if q.get("net")}
    # a pair declared twice (in "match" AND "diff_pairs") is ONE pair: listed twice, its swap
    # ran twice and undid itself (brain_board U17/U44, 2026-11-19: every plan came back empty)
    held = sorted({g for g in groups if len(g) == 2 and g <= nets}, key=sorted)
    rest = nets - set().union(*held) if held else nets
    if not held:
        return None
    if not flip and (len(held) > 2 or any(not (GROUND_NET.search(n) or SUPPLY.search(n)) for n in rest)):
        return None
    out = []
    for g in held:
        pn, nn = sorted(g)
        qp = [q for q in pads if q.get("net") == pn]
        qn = [q for q in pads if q.get("net") == nn]
        if len(qp) != len(qn):
            return None
        free = list(qn)
        for q in qp:
            m = min(free, key=lambda r: math.hypot(r["xy"][0] - q["xy"][0], r["xy"][1] - q["xy"][1]))
            free.remove(m)
            out.append((q["num"], m["num"]))
    return out


def swap_plan(parts, pl, groups, max_parts=10, flip=(), rejected=()):
    """The channel swaps on pass-through parts that leave the fewest twisted pair hops
    (pair_twists), fewest swaps on a tie. Each swap is free in the netlist (identical channels)
    but must be carried into the netlist's generator. Returns (twisted before, twisted after,
    [(ref, [(pin, pin)])]).
    ⚠ THE TWISTED-HOP COUNT IS A HINT, NOT A SCORE (brain_board W48k, 2026-11-19): the plan's
    FL3/FL4 winding swaps took the count 7 -> 3 and the paired seed-1 route came out worse
    (2/0/98/32 vs 2/0/90/24; GADGET 6/9 vias, skew 30.7, new USBA / USBB_J fails). Route a
    proposed swap against its control before carrying it into the netlist.
    ⚠ ...AND A REJECTED ONE IS NOT PROPOSED AGAIN (brain_board esc13, 2026-11-22): the same FL3 / FL4
    swap was proposed in 24 runs after W48k; its 2-seed route A/B (rPS_13s1/s2 vs 13c1/c2) lost on the
    USB pairs both times (USBA / USBB_J hard FAILs 2 vs 0 and 2 vs 1). `rejected` (the board notes'
    swap_rejected refs) leaves those parts out of the plan."""
    import copy
    gsets = [frozenset(g.get("nets") or ()) for g in groups if len(g.get("nets") or ()) == 2]
    cand = {}
    for ref, v in parts.items():
        if ref in pl and ref not in rejected:
            sp = _swap_pairs(v, gsets, flip=ref in flip)
            if sp:
                cand[ref] = sp
    names = sorted(cand)[:max_parts]

    def count(sel):
        pp = parts
        if sel:
            pp = dict(parts)
            for ref in sel:
                v = copy.deepcopy(parts[ref])
                by = {q["num"]: q for q in v["pads"]}
                for a_, b_ in cand[ref]:
                    by[a_]["net"], by[b_]["net"] = by[b_]["net"], by[a_]["net"]
                pp[ref] = v
        return sum(1 for t in pair_twists(pp, pl, groups) if t[3] == "twisted")

    n0 = count(())
    best = (n0, 0, ())
    for k in range(1, len(names) + 1):
        for sel in __import__("itertools").combinations(names, k):
            n_ = count(sel)
            if (n_, k) < best[:2]:
                best = (n_, k, sel)
    return n0, best[0], [(r, cand[r]) for r in best[2]]


def apply_swaps(parts, net_text, swaps):
    """Apply swap_plan's swaps to a parts dict (in place) and a KiCad netlist's text (returned):
    each swapped pin's node moves to the other rail's net."""
    for ref, prs in swaps:
        by = {q["num"]: q for q in parts[ref]["pads"]}
        for a_, b_ in prs:
            by[a_]["net"], by[b_]["net"] = by[b_]["net"], by[a_]["net"]
    # the netlist: find each (net ...) block's span and each (node (ref R) (pin P) ...) in it
    def spans(text, head):
        out, i = [], 0
        while True:
            i = text.find(head, i)
            if i < 0:
                return out
            depth, j = 0, i
            while True:
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            out.append((i, j + 1))
            i = j + 1
    moves = {}
    for ref, prs in swaps:
        for a_, b_ in prs:
            moves[(ref, a_)] = (ref, b_)
            moves[(ref, b_)] = (ref, a_)
    # where each moved pin's net is now, from the swapped parts (its new net)
    target = {(ref, q["num"]): q["net"] for ref, _ in swaps for q in parts[ref]["pads"]}
    nodes = {}                            # (ref, pin) -> node text, removed from its old net
    text = net_text
    for (i, j) in reversed(spans(text, "(net")):
        blk = text[i:j]
        new = blk
        for (ni, nj) in reversed(spans(blk, "(node")):
            nd = blk[ni:nj]
            m = re.search(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', nd)
            if m and (m.group(1), m.group(2)) in moves:
                nodes[(m.group(1), m.group(2))] = nd
                new = new[:ni] + new[nj:]
        text = text[:i] + new + text[j:]
    for (ref, pin), nd in nodes.items():
        net = target[(ref, pin)]
        m = re.search(r'\(name "%s"\)' % re.escape(net), text)
        if not m:
            raise ValueError("apply_swaps: net %s not in the netlist" % net)
        k = m.end()
        text = text[:k] + "\n      " + nd + text[k:]
    return text


def unregioned_sensitive(parts, rules):
    """Report lines: a sensitive IC or crystal left out of every region while a switcher
    feeding it is held in one (motor_ctrl trial gap 8, 2026-11-11).

    A WARNING, not automation: v2 regioned the 5 V buck and left the MCU unsaid, and
    place_init put U4 beside the buck with its crystal 15 mm off. auto_floorplan's `apart`
    still applies, but a regioned switcher is a floorplan that has been half written --
    the author decided where the noise goes and not where the listener goes."""
    held = set()
    for r in rules:
        if r["kind"] == "in_region":
            held |= set(_refs(r["refs"], parts))
        elif r["kind"] in ("fixed", "pin", "panel"):
            held.add(r["ref"])
    held |= fixed_refs(rules)
    out = []
    for r in auto_floorplan(parts):
        if not r.get("forbid"):
            continue
        sw = [x for x in r["a"] if x in held and re.match(r"^[UL]\d", x)]
        if not sw:
            continue
        loose = [x for x in r["b"] if x not in held and re.match(r"^[UY]\d", x)]
        if loose:
            out.append("%s unregioned while switcher %s is (%s)" % (" ".join(loose), " ".join(sw), r["why"]))
    return out


FLOOR_KINDS = ("apart", "thermal", "in_region", "region")


def fixed_refs(rules):
    """Refs the intent pins (fixed, pin, panel, and the members of a group on a fixed anchor)."""
    fx = {r["ref"] for r in rules if r["kind"] in ("fixed", "pin", "panel")}
    for r in rules:
        if r["kind"] == "group" and r["anchor"] in fx:
            fx |= set(r["members"])
    return fx


def floor_breaches(stem, rules, placements=None, parts_path=None):
    """[(slack, subject, detail, why)] for the broken floorplan rules (apart, thermal,
    in_region): what score.py --intent prints beside the route."""
    fx = fixed_refs(rules)
    fl = [dict(r, fixed=sorted(fx)) if r["kind"] in ("apart", "thermal") else r
          for r in rules if r["kind"] in FLOOR_KINDS]
    return [(s, subj, det, r.get("why", "")) for s, _, r, subj, det in report(stem, fl, H={}, placements=placements, parts_path=parts_path)
            if s < 0 and r["kind"] != "region"]


def pour_poly(rule, P, notes, amps=None):
    """A `pour` rule's outline in board mm (the notes' frame, as zones take it): the named
    region's polygon, or the convex hull of width_mm circles round each pin `along`."""
    if rule.get("region"):
        return (notes.get("_regions") or {}).get(rule["region"])
    pins = [P.pad(*x.split(".", 1)) for x in rule.get("along", ())]
    if len(pins) < 1:
        return None
    w = rule.get("width_mm")
    if w is None:
        w = max(2.0, 1.5 * width_for(amps, design_dt(notes), q=(notes or {}).get("quality"),
                                     layer=rule["layer"])) if amps else 2.0
    r = float(w) / 2.0
    pts = np.array([(float(p[0]) + r * math.cos(a), float(p[1]) + r * math.sin(a))
                    for p in pins for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)])
    from scipy.spatial import ConvexHull
    h = ConvexHull(pts)
    return [[round(float(x), 3), round(float(y), 3)] for x, y in pts[h.vertices]]


def pour_amps(rule, notes):
    """The current a `pour` carries: the declared power path between its own `along` pins,
    else the net's largest (a 3.8 A J10 path sized the 2.9 A Q2-J7 pour at 3.8 mm)."""
    # a pour may state its current (esc11_pre8, 2026-11-22): +24V's Q209.5 feeds F203 3 A AND F204 2 A,
    # but the largest single path (3 A) sized its land vias -- 2 of 0.3 mm for 5 A
    if rule.get("amps"):
        return float(rule["amps"])
    paths = (notes.get("quality", {}) or {}).get("power_paths", ()) or ()
    al = set(rule.get("along", ()))
    hit = [float(p_["amps"]) for p_ in paths if p_["net"] == rule["net"] and p_["from"] in al
           and al & set(p_["to"] if isinstance(p_["to"], (list, tuple)) else [p_["to"]])]
    return max(hit) if hit else max([float(p_["amps"]) for p_ in paths if p_["net"] == rule["net"]] or [0.0]) or None


PAIR_CLEAR = 0.5    # mm each side of a coupled pair its corridor keeps free (a via's clearance)


def pair_corridors(spec, P):
    """A declared diff pair's hops as corridors: [(polygon, {the hop's two parts}, side,
    length mm)] -- the straight line between the two parts' pin-pair midpoints, as wide as
    the coupled pair (2 x width + gap) plus PAIR_CLEAR each side. A hop with a part not
    placed, or a part carrying neither rail, is skipped."""
    nets = set(spec.get("nets") or ())
    w = float(spec.get("width", 0.2))
    hw = (2.0 * w + float(spec.get("gap", 0.2))) / 2.0 + PAIR_CLEAR
    chain = list(spec.get("chain") or ())

    def mid(step):
        pts = []
        for ref in step.split("|"):
            if ref not in P.pl or ref not in P.parts:
                continue
            pts += [P.pad(ref, q["num"]) for q in P.parts[ref]["pads"] if q.get("net") in nets and q["num"]]
        return np.mean(pts, axis=0) if pts else None

    out = []
    for sa, sb in zip(chain, chain[1:]):
        a, b = mid(sa), mid(sb)
        if a is None or b is None:
            continue
        d = b - a
        ln = float(np.hypot(*d))
        if ln < 1e-6:
            continue
        n = np.array([-d[1], d[0]]) / ln * hw
        poly = [a + n, b + n, b - n, a - n]
        side = "F"
        r0 = sa.split("|")[0]
        if r0 in P.parts:
            side = P.parts[r0].get("side", "F")
        out.append((poly, set(sa.split("|")) | set(sb.split("|")), side, ln))
    return out


def pair_foreign(spec, P, poly, side, skip=(), refs=None):
    """[(pad name, mm2 inside)] of the pads of OTHER nets inside a pair corridor on its side
    (through-hole pads on either), its own hop's parts (`skip`) left out: their escapes are
    the router's. The pad's area by a 5 x 5 sample grid, as pour_foreign(areas=True)."""
    from matplotlib.path import Path as _Path
    nets = set(spec.get("nets") or ())
    path = _Path(np.asarray(poly, float))
    pa = np.asarray(poly, float)
    lo, hi = pa.min(axis=0), pa.max(axis=0)
    grid = np.array([(a, b) for a in np.linspace(-0.5, 0.5, 5) for b in np.linspace(-0.5, 0.5, 5)])
    out = []
    for ref, p in P.parts.items():
        if ref not in P.pl or ref in skip or (refs is not None and ref not in refs):
            continue
        x, y, _ = P.at(ref)
        rr = float(np.max(np.abs(np.asarray([q["xy"] for q in p["pads"]], float)))) + 3.0 if p["pads"] else 0.0
        if x < lo[0] - rr or x > hi[0] + rr or y < lo[1] - rr or y > hi[1] + rr:
            continue
        for q in p["pads"]:
            if q.get("net") in nets or not q["num"]:
                continue
            if not (q.get("tht") or p.get("side", "F") == side):
                continue
            loc = _rot(grid * np.asarray(q["size"], float), float(q.get("rot") or 0.0)) + q["xy"]
            frac = float(path.contains_points(P.world(ref, loc)).mean())
            if frac > 0:
                out.append(("%s.%s" % (ref, q["num"]), frac * float(q["size"][0]) * float(q["size"][1])))
    return out


def pour_foreign(rule, P, poly, refs=None, areas=False):
    """Other nets' pads inside a pour's outline on its layer: ["U4.3", ...].

    ⚠ A PAD IS ITS AREA, NOT ITS CENTRE (brain_board mT4, 2026-11-16) -- PCBFLOW_POUR_AREA=1
    while it is measured, then the default. A MOSFET's drain tab is 4.5 mm across: Q5's sat
    with its centre outside the PB_VOUT band and 8.8 mm2 of it inside, the fill went round it
    and A1 read the pour's cut as 0.00 mm -- while this said "no foreign pads", so the turn
    stage (place_init pour_pen) never saw a reason to face the source pins at the next stage.
    Q4/Q6's tabs did the same to PA_VOUT (5.6 mm2 each). With the flag a pad counts when any
    of a 5 x 5 sample grid over it lies inside. areas=True: [(name, mm2 inside)] -- the
    sampled fraction of the pad times its size (a rectangle's area; a round pad reads high)."""
    from matplotlib.path import Path as _Path
    import os
    path = _Path(np.asarray(poly, float))
    side = "B" if rule["layer"].startswith("B.") else "F"
    inner = rule["layer"].startswith("In")
    area = os.environ.get("PCBFLOW_POUR_AREA") == "1"
    grid = np.array([(a, b) for a in np.linspace(-0.5, 0.5, 5) for b in np.linspace(-0.5, 0.5, 5)])
    out = []
    for ref, p in P.parts.items():
        if ref not in P.pl or (refs is not None and ref not in refs):
            continue
        for q in p["pads"]:
            if q["net"] == rule["net"] or not q["num"]:
                continue
            on = q.get("tht") or (not inner and p.get("side", "F") == side)
            if not on:
                continue
            if area:
                loc = _rot(grid * np.asarray(q["size"], float), float(q.get("rot") or 0.0)) + q["xy"]
                frac = float(path.contains_points(P.world(ref, loc)).mean())
                hit = frac > 0
            else:
                hit = path.contains_point(tuple(P.pad(ref, q["num"])))
                frac = 1.0
            if hit:
                nm_ = "%s.%s" % (ref, q["num"])
                out.append((nm_, frac * float(q["size"][0]) * float(q["size"][1])) if areas else nm_)
    return out


AROUND_GRID = 0.1        # pour_around's grid (mm)
AROUND_NECK = 0.6        # ...the narrowest copper it leaves past another net's pad (mm)
AROUND_CLEAR = 0.25      # ...a pad's keep-out besides the neck (the fill's clearance, mm)


def pour_around(rule, P, notes=None, amps=None):
    """A pour band along its `along` pins that goes ROUND other nets' pads on its layer,
    not through them: the band's centreline is a shortest path over a 0.1 mm grid (a
    spanning tree over the pins, Prim on path length) on which every foreign pad's
    circumscribed circle, grown by AROUND_CLEAR + AROUND_NECK / 2, is a wall; the band is
    that centreline grown by width_mm / 2 -- the fill then clears the foreign pads it
    still covers, and the centreline's corridor stays copper. None if no tree reaches
    every pin (the caller keeps the hull and says so).

    ⚠ WHY (output_board mL2, 2026-11-14): pour_poly's hull drew +24V's band straight
    through J240 and PB_VBUS's through R76 / Q5; the fill cleared those pads and the band
    came back in two parts, R75.1 alone on a 3.9 mm2 fragment. The router now joins a
    split fill (negotiate.build_nets, 19b4915), but a band cut before routing is a pour
    drawn badly."""
    from scipy.ndimage import binary_dilation, distance_transform_edt
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    pins = [np.asarray(P.pad(*x.split(".", 1)), float) for x in rule.get("along", ())]
    if len(pins) < 2:
        return None
    w = rule.get("width_mm")
    if w is None:
        w = max(2.0, 1.5 * width_for(amps, design_dt(notes), q=(notes or {}).get("quality"),
                                     layer=rule["layer"])) if amps else 2.0
    w = float(w)
    g = AROUND_GRID
    pa = np.array(pins)
    mg = w + float(rule.get("search_mm", 6.0))     # how far past the pins the band may detour
    x0, y0 = pa.min(axis=0) - mg
    x1, y1 = pa.max(axis=0) + mg
    nx, ny = int(math.ceil((x1 - x0) / g)) + 1, int(math.ceil((y1 - y0) / g)) + 1
    X = x0 + np.arange(nx) * g
    Y = y0 + np.arange(ny) * g
    side = "B" if rule["layer"].startswith("B.") else "F"
    inner = rule["layer"].startswith("In")
    # the width the band must hold where the current flows: the net's IPC width at the design
    # rise (what the power gate wants), never under AROUND_NECK
    # ⚠ ON ITS OWN LAYER (brain_board fold10 pre-check, 2026-11-26): an In3 +24V band at 3 A drew
    # "neck 0.95 of 0.95 wanted" -- the outer width -- where the gate, scaling inner copper by its
    # foil, wants 2.15 drawn: the band would have passed here and FAILed at the gate
    need = (max(AROUND_NECK, width_for(amps, design_dt(notes), q=(notes or {}).get("quality"),
                                       layer=rule["layer"])) if amps else AROUND_NECK)
    # ⚠ THE WALLS KEEP THE BOARD'S ZONE CLEARANCE, NOT 0.25 (brain_board esc_pre5, 2026-11-21): the
    # centreline ran need/2 + 0.25 off other nets' pads, the fill then kept its 0.5 off them, and
    # +5V_SW's band came out 0.34 mm (wants 0.51) near F202 -- the fill ate what the walls left
    clr_ = max(AROUND_CLEAR, float((notes or {}).get("zone_clearance") or 0.5))
    m_max = clr_ + need / 2.0
    m_own = clr_ + AROUND_NECK / 2.0        # an own pin's ring must beat its neighbours' walls
    dfor = np.full((ny, nx), np.inf)    # distance to the nearest foreign pad (its rectangle)
    fid = np.full((ny, nx), -1, int)    # ...and which pad that is (index into flab)
    flab = []
    own = np.zeros((ny, nx), bool)
    pads_ = np.zeros((ny, nx), bool)    # foreign pads + AROUND_CLEAR: never inside the band
    lobes = {}                          # ref -> [(cx, cy, hx, hy, ca, sa)] own pads on the rule's net
    for ref, p in P.parts.items():
        if ref not in P.pl:
            continue
        for q in p["pads"]:
            if not q["num"]:
                continue
            on = q.get("tht") or (not inner and p.get("side", "F") == side)
            if not on:
                continue
            # ⚠ THE PAD'S RECTANGLE, NOT ITS CIRCUMSCRIBED CIRCLE (brain_board rPS_p1, 2026-11-20):
            # a 0.25 x 3.40 QFN power pin's circle is 1.7 mm across, grown by the clearance it
            # swallowed every neighbour's gap -- U205.11, U205.7, U221.7/.8 sat in 0.6-9 mm2 islands,
            # no band reached them, and 5 of 6 F.Cu power pours fell back to a hull the fill shredded.
            cx, cy = P.world(ref, [q["xy"]])[0]
            hx, hy = q["size"][0] / 2.0, q["size"][1] / 2.0
            mine = q["net"] == rule["net"]
            r_ = math.hypot(hx, hy) + (m_own if mine else m_max)
            j0, j1 = max(int((cx - r_ - x0) / g), 0), min(int((cx + r_ - x0) / g) + 2, nx)
            i0, i1 = max(int((cy - r_ - y0) / g), 0), min(int((cy + r_ - y0) / g) + 2, ny)
            if j0 >= j1 or i0 >= i1:
                continue
            ang = math.radians(P.at(ref)[2] + float(q.get("rot") or 0.0))
            ca, sa = math.cos(ang), math.sin(ang)
            ux, uy = X[None, j0:j1] - cx, Y[i0:i1, None] - cy
            lx, ly = np.abs(ux * ca + uy * sa), np.abs(-ux * sa + uy * ca)
            dq = np.hypot(np.maximum(lx - hx, 0.0), np.maximum(ly - hy, 0.0))
            if mine:
                # an own pin's clearance ring beats the walls: a fine-pitch pin (U205.11 at 0.5 mm
                # pitch) is fenced by its neighbours' rings, and its escape is pin-wide whatever
                # the band does -- the gate measures the neck from the pad edge, the part's
                # rating covers its own pins
                own[i0:i1, j0:j1] |= dq <= m_own + 1e-9
                lobes.setdefault(ref, []).append((cx, cy, hx, hy, ang))
            else:
                closer = dq < dfor[i0:i1, j0:j1]
                fid[i0:i1, j0:j1][closer] = len(flab)
                flab.append("%s.%s" % (ref, q["num"]))
                dfor[i0:i1, j0:j1] = np.minimum(dfor[i0:i1, j0:j1], dq)
                pads_[i0:i1, j0:j1] |= dq <= AROUND_CLEAR + 1e-9
    # the other bands on this layer: their end pins (pads on any side) and their drawn outlines
    # are walls like a foreign pad (place_flow passes them)
    # the band's own end pins get their ring whatever side they are on: a B.Cu trunk's ends are
    # F.Cu lands, which the side filter above skips
    for key in rule.get("along", ()):
        ref, num = key.split(".", 1)
        p = P.parts.get(ref)
        if p is None or ref not in P.pl:
            continue
        for q in p["pads"]:
            if q["num"] != num:
                continue
            cx, cy = P.world(ref, [q["xy"]])[0]
            hx, hy = q["size"][0] / 2.0, q["size"][1] / 2.0
            ang = math.radians(P.at(ref)[2] + float(q.get("rot") or 0.0))
            ca, sa = math.cos(ang), math.sin(ang)
            ux, uy = X[None, :] - cx, Y[:, None] - cy
            lx, ly = np.abs(ux * ca + uy * sa), np.abs(-ux * sa + uy * ca)
            own |= np.hypot(np.maximum(lx - hx, 0.0), np.maximum(ly - hy, 0.0)) <= m_own + 1e-9
    # ⚠ THE NECK WAS REPORTED INSIDE THE PAD (brain_board sa_away, 2026-11-22): +5V_RAW's band read
    # "neck 0.68 of 1.35 -- pinched by U221.1" while the gate measured 1.37. The pinch lay on the
    # IN bar's escape stub (pin_escapes: pin-wide through the neighbours' fence, 0.95 past the pad),
    # which the gate counts as pad by rule (lead, 2026-11-21) -- the band takes over at the stub's
    # tip, so the centreline may run the stub's corridor at any neck (test_stub_own.py).
    for e_ in pin_escapes(rule, P, notes):
        if e_.get("layer", rule.get("layer")) != rule.get("layer"):
            continue
        (ax_, ay_), (bx_, by_) = e_["pts"][0], e_["pts"][-1]
        dx_, dy_ = bx_ - ax_, by_ - ay_
        L2 = dx_ * dx_ + dy_ * dy_
        if L2 <= 0:
            continue
        ux, uy = X[None, :] - ax_, Y[:, None] - ay_
        t_ = np.clip((ux * dx_ + uy * dy_) / L2, 0.0, 1.0)
        own |= np.hypot(ux - t_ * dx_, uy - t_ * dy_) <= e_["width"] / 2.0 + 1e-9
    for key in rule.get("_avoid_pins", ()):
        ref, num = key.split(".", 1)
        p = P.parts.get(ref)
        if p is None or ref not in P.pl:
            continue
        for q in p["pads"]:
            if q["num"] != num:
                continue
            cx, cy = P.world(ref, [q["xy"]])[0]
            hx, hy = q["size"][0] / 2.0, q["size"][1] / 2.0
            ang = math.radians(P.at(ref)[2] + float(q.get("rot") or 0.0))
            ca, sa = math.cos(ang), math.sin(ang)
            ux, uy = X[None, :] - cx, Y[:, None] - cy
            lx, ly = np.abs(ux * ca + uy * sa), np.abs(-ux * sa + uy * ca)
            dq = np.hypot(np.maximum(lx - hx, 0.0), np.maximum(ly - hy, 0.0))
            closer = dq < dfor
            fid[closer] = len(flab)
            flab.append(key)
            dfor = np.minimum(dfor, dq)
            pads_ |= dq <= AROUND_CLEAR + 1e-9
    # ⚠ DECLARED COPPER IS A WALL TOO (brain_board esc11_pre2, 2026-11-22): U205's FSW5 / GND
    # escapes were declared (intent kind "copper") before the bands, but the band only walled pads,
    # so VIN_CM5's outline ran over the FSW5 via and its stub, the fill cleared them by the zone
    # clearance, and the band necked to 0.42 mm (wants 0.70; 0.53 without the escapes). Another
    # net's declared track on this layer, and its via on any layer, fence the band like a pad.
    segs_ = [(t[2] / 2.0, t[3]) for t in (notes or {}).get("tracks", ())
             if t[0] != rule["net"] and t[1] == rule.get("layer", "F.Cu")]
    vias_ = [(x_, y_) for n_, x_, y_ in ((v[0], v[1], v[2]) for v in (notes or {}).get("vias", ()))
             if n_ != rule["net"]]
    for hw_, pts_d in segs_:
        for (ax_, ay_), (bx_, by_) in zip(pts_d[:-1], pts_d[1:]):
            r_ = hw_ + m_max
            j0, j1 = max(int((min(ax_, bx_) - r_ - x0) / g), 0), min(int((max(ax_, bx_) + r_ - x0) / g) + 2, nx)
            i0, i1 = max(int((min(ay_, by_) - r_ - y0) / g), 0), min(int((max(ay_, by_) + r_ - y0) / g) + 2, ny)
            if j0 >= j1 or i0 >= i1:
                continue
            ux, uy = X[None, j0:j1] - ax_, Y[i0:i1, None] - ay_
            dx_, dy_ = bx_ - ax_, by_ - ay_
            L2 = dx_ * dx_ + dy_ * dy_
            t_ = np.clip((ux * dx_ + uy * dy_) / L2, 0.0, 1.0) if L2 > 0 else np.zeros_like(ux * uy)
            dq = np.maximum(np.hypot(ux - t_ * dx_, uy - t_ * dy_) - hw_, 0.0)
            closer = dq < dfor[i0:i1, j0:j1]
            fid[i0:i1, j0:j1][closer] = len(flab)
            flab.append("declared track")
            dfor[i0:i1, j0:j1] = np.minimum(dfor[i0:i1, j0:j1], dq)
            pads_[i0:i1, j0:j1] |= dq <= AROUND_CLEAR + 1e-9
    VIA_R_ = 0.3
    for vx_, vy_ in vias_:
        r_ = VIA_R_ + m_max
        j0, j1 = max(int((vx_ - r_ - x0) / g), 0), min(int((vx_ + r_ - x0) / g) + 2, nx)
        i0, i1 = max(int((vy_ - r_ - y0) / g), 0), min(int((vy_ + r_ - y0) / g) + 2, ny)
        if j0 >= j1 or i0 >= i1:
            continue
        dq = np.maximum(np.hypot(X[None, j0:j1] - vx_, Y[i0:i1, None] - vy_) - VIA_R_, 0.0)
        closer = dq < dfor[i0:i1, j0:j1]
        fid[i0:i1, j0:j1][closer] = len(flab)
        flab.append("declared via")
        dfor[i0:i1, j0:j1] = np.minimum(dfor[i0:i1, j0:j1], dq)
        pads_[i0:i1, j0:j1] |= dq <= AROUND_CLEAR + 1e-9
    if rule.get("_avoid_polys"):
        from matplotlib.path import Path as _Path
        gx_, gy_ = np.meshgrid(X, Y)
        pts_ = np.column_stack([gx_.ravel(), gy_.ravel()])
        for pg in rule["_avoid_polys"]:
            m_ = _Path(pg).contains_points(pts_).reshape(ny, nx)
            if not m_.any():
                continue
            dq = distance_transform_edt(~m_) * g
            closer = dq < dfor
            fid[closer] = len(flab)
            flab.append("band")
            dfor = np.minimum(dfor, dq)
            pads_ |= dq <= AROUND_CLEAR + 1e-9
    # ⚠ A KEEP-OUT RULE AREA IS A WALL (brain_board fold10 pre-check, 2026-11-26): +5V_OPT's and
    # VIN_BUS's B.Cu bands cut the corner of the audio corner's 1 mm moat (notes rule_areas, no
    # fills on any layer) at (-13, 5); the fill split there into two pieces and the gate read both
    # OPEN on frozen copper. A rule area that keeps fills off this layer fences the band like a pad.
    ras_ = [ra_["poly"] for ra_ in (notes or {}).get("rule_areas", ()) or ()
            if not ra_.get("fills", False)
            and (ra_.get("layers", "all") == "all" or rule.get("layer", "F.Cu") in ra_.get("layers", ()))]
    if ras_:
        from matplotlib.path import Path as _Path
        gx_, gy_ = np.meshgrid(X, Y)
        pts_ = np.column_stack([gx_.ravel(), gy_.ravel()])
        for pg in ras_:
            m_ = _Path(pg).contains_points(pts_).reshape(ny, nx)
            if not m_.any():
                continue
            dq = distance_transform_edt(~m_) * g
            closer = dq < dfor
            fid[closer] = len(flab)
            flab.append("rule area")
            dfor = np.minimum(dfor, dq)
            pads_ |= dq <= AROUND_CLEAR + 1e-9
    # ⚠ THE BAND WAS 0.6 mm WHERE IT MATTERED (brain_board rPS_g1, 2026-11-21): the walls left the
    # centreline any gap AROUND_NECK wide, so VIN_BRAIN's frozen band ran 1.15 mm (wants 2.61) past
    # C326 and wandered 84 mm (306 mm2 of frozen copper, 55 router opens). The centreline now keeps
    # `need` / 2 + the clearance off every foreign pad; only if no such tree exists does it accept
    # a narrower neck (3/4, 1/2 of need, then AROUND_NECK), and it says which.
    cost = None
    idx = np.arange(nx * ny).reshape(ny, nx)
    pc = [int(idx[min(max(int(round((py - y0) / g)), 0), ny - 1),
                  min(max(int(round((px - x0) / g)), 0), nx - 1)]) for px, py in pins]
    # ⚠ THE BARE NEED IS A RUNG (brain_board sa_away, 2026-11-26): `need` is the DRAWN width
    # (copper.drawn_width_mm, the need + one raster step), and the ladder went straight from it to
    # 3/4 of it -- +5V_RAW's corridor holds 1.37 (the gate's reading), short of the drawn 1.40, so
    # the band fell to 1.05 where the need (1.33) fitted: asking for the margin cost the width.
    # The bare need comes before the fractions (close_last's guard ladder stops there too).
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from copper import required_width_mm
    bare = max(AROUND_NECK, min(need, required_width_mm(amps, "F.Cu", {"temp_rise_c": design_dt(notes)})))         if amps else need
    for neck in sorted({need, bare, max(AROUND_NECK, 0.75 * need), max(AROUND_NECK, 0.5 * need), AROUND_NECK},
                       reverse=True):
        wall = dfor <= clr_ + neck / 2.0 + 1e-9
        free = ~wall | own
        # a cell costs 1, up to 3 near a wall: a wide corridor before a narrow one
        dw = distance_transform_edt(~wall) * g
        cost = 1.0 + 2.0 * np.clip(1.0 - dw / max(w / 2.0, g), 0.0, 1.0)
        rows, cols, vals = [], [], []
        for di, dj in ((0, 1), (1, 0), (1, 1), (1, -1)):
            ln = math.hypot(di, dj)
            ia, ib = slice(0, ny - di), slice(di, ny)
            if dj >= 0:
                ja, jb = slice(0, nx - dj), slice(dj, nx)
            else:
                ja, jb = slice(-dj, nx), slice(0, nx + dj)
            ok = free[ia, ja] & free[ib, jb]
            c_ = ln * g * (cost[ia, ja] + cost[ib, jb]) / 2.0
            rows.append(idx[ia, ja][ok])
            cols.append(idx[ib, jb][ok])
            vals.append(c_[ok])
        G = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                       shape=(nx * ny, nx * ny)).tocsr()
        line = np.zeros(nx * ny, bool)
        line[pc[0]] = True
        left = {c for c in pc[1:] if not line[c]}
        while left:
            dist, pred = dijkstra(G, directed=False, indices=np.nonzero(line)[0],
                                  return_predecessors=True, min_only=True)[:2]
            best = min(left, key=lambda c: dist[c])
            if not np.isfinite(dist[best]):
                break
            c = best
            while c >= 0 and not line[c]:
                line[c] = True
                c = pred[c]
            left = {c for c in left if not line[c]}
        if not left:
            break
    else:
        # say WHY (esc11_pre5: +24V on B.Cu fell back to a hull with nothing in the log): the pins
        # the narrowest neck still could not reach, and the walls that ring them
        from scipy.ndimage import label as _label
        lab_, _n = _label(free)
        home = lab_.ravel()[pc[0]]
        names = rule.get("along", ())
        miss = [names[k] for k, c in enumerate(pc) if lab_.ravel()[c] != home]
        reg = (lab_ == home) if home else np.zeros_like(free)
        rim = binary_dilation(reg, iterations=2) & wall
        fence = sorted({flab[i] for i in np.unique(fid[rim]) if 0 <= i < len(flab)})
        pour_around.last = dict(net=rule["net"], need=round(need, 3), neck=0.0, length=0.0, failed=True,
                                unreached=miss, fence=fence[:40], pinch=[], pinch_xy=[])
        return None
    # where the centreline runs closer than the full width allows, and whose pads pinch it --
    # the parts a placement corridor would have to move
    lm = line.reshape(ny, nx)
    pin_ = lm & (dfor <= clr_ + need / 2.0 + 1e-9) & ~own
    ii, jj = np.nonzero(pin_)
    pinch = sorted({flab[k] for k in fid[ii, jj] if k >= 0})
    pour_around.last = dict(net=rule["net"], need=round(need, 3), neck=round(neck, 3),
                            length=round(float(lm.sum()) * g, 1), pinch=pinch,
                            pinch_xy=[[round(float(X[j]), 2), round(float(Y[i]), 2)] for i, j in zip(ii[::5], jj[::5])])
    rr = int(round(w / 2.0 / g))
    yy, xx = np.mgrid[-rr:rr + 1, -rr:rr + 1]
    band = binary_dilation(line.reshape(ny, nx), structure=(yy * yy + xx * xx) <= rr * rr)
    # parallel pins of one part on the net (U221.7/.8, 0.5 pitch) join in one lobe at the pad
    # edge -- the box over the group, less any foreign pad -- then the band widens from there
    for ref, pp in lobes.items():
        grp = []
        for a in pp:
            if any(math.hypot(a[0] - b[0], a[1] - b[1]) <= 2 * max(a[2], a[3], b[2], b[3]) + 1.0
                   for b in pp if b is not a):
                grp.append(a)
        if len(grp) < 2:
            continue
        ang = grp[0][4]
        ca, sa = math.cos(ang), math.sin(ang)
        cx, cy = np.mean([a[0] for a in grp]), np.mean([a[1] for a in grp])
        lo, hi = [np.inf, np.inf], [-np.inf, -np.inf]
        for ax, ay, hx, hy, _ in grp:
            u, v = (ax - cx) * ca + (ay - cy) * sa, -(ax - cx) * sa + (ay - cy) * ca
            lo = [min(lo[0], u - hx), min(lo[1], v - hy)]
            hi = [max(hi[0], u + hx), max(hi[1], v + hy)]
        ux, uy = X[None, :] - cx, Y[:, None] - cy
        u, v = ux * ca + uy * sa, -ux * sa + uy * ca
        band |= (u >= lo[0]) & (u <= hi[0]) & (v >= lo[1]) & (v <= hi[1])
    # a band never covers another net's pad or its clearance: a frozen band (a router wall)
    # over a fine-pitch neighbour would wall in its escape
    band &= ~pads_
    import contourpy
    z = np.zeros((ny + 2, nx + 2))
    z[1:-1, 1:-1] = band
    lines = contourpy.contour_generator(z=z).lines(0.5)
    if not lines:
        return None
    ring = max(lines, key=len)
    pts = [(x0 + (c - 1) * g, y0 + (r - 1) * g) for c, r in ring]
    pts = _simplify(pts, g / 2.0)
    return [[round(float(x), 3), round(float(y), 3)] for x, y in pts]


def pin_escapes(rule, P, notes=None):
    """Declared escape stubs for a band's fine-pitch end pins: [{key, net, layer, width, pts, pitch}].

    ⚠ A POUR CANNOT TOUCH A 0.5 mm PITCH PIN (brain_board tr_pre1..4, 2026-11-21): +5V_BB at
    U205.11 and VIN_CM5 at U205.7 read OPEN on frozen copper. The fill keeps the zone clearance
    (0.5) off the neighbour pins, 0.25 away, so it stops ~0.43 short of the pin and only a router
    stub reached it -- 0.29 mm across a 6.4 mm neck. A pin whose same-part neighbour is closer than
    twice the zone clearance gets a stub: pin-wide, straight out along the pin's axis (from the
    end nearest the band's next pin; none if that end crosses a foreign pad) until it is past the
    neighbours' clearance, capped at 2 x pitch -- the band takes
    over there at full width. The gate counts the stub as part of the pad (the datasheet pin rating
    covers it, lead 2026-11-21); beyond it the full width applies. A local zone clearance under 0.5
    at 0.5 pitch was rejected: fab DRC and slivers between the pins."""
    zc = float((notes or {}).get("zone_clearance") or 0.5)
    out = []
    # ⚠ A PIN THAT HAS ITS OWN DECLARED EXIT TAKES NO STUB (brain_board fold8, 2026-11-26): U221.6's
    # stub went out of the pin's WEST end, into U221.5's declared +5V_RAW foot, while +5V_CM5's own
    # stepped foot leaves its east end -- layout refused the placement. A rule names such pins in
    # `no_escape`; the declared copper on them is the joint, and the band takes over from it.
    skip_ = set(rule.get("no_escape") or ())
    for key in rule.get("along", ()):
        if key in skip_:
            continue
        ref, num = key.split(".", 1)
        p = P.parts.get(ref)
        if p is None or ref not in P.pl:
            continue
        # the stub goes on the PIN's layer: a B.Cu trunk ends on F.Cu pins (+5V_BB at U205.11)
        pin_layer = "B.Cu" if p.get("side", "F") == "B" else "F.Cu"
        mine = [q for q in p["pads"] if q["num"] == num]
        if not mine:
            continue
        q = mine[0]
        cx, cy = P.world(ref, [q["xy"]])[0]
        hx, hy = q["size"][0] / 2.0, q["size"][1] / 2.0
        ang = math.radians(P.at(ref)[2] + float(q.get("rot") or 0.0))
        ux, uy = (math.cos(ang), math.sin(ang)) if hx >= hy else (-math.sin(ang), math.cos(ang))
        half_len, half_w = max(hx, hy), min(hx, hy)
        if half_len < 1.5 * half_w:
            continue                             # a land, not a pin: no axis to escape along
        # ⚠ THE STUB LEAVES FROM THE END NEAREST THE BAND'S NEXT PIN, OR NOT AT ALL (brain_board
        # fold8, 2026-11-26): U221.6's target-facing (east) end was fenced by U221.10's corner pad,
        # so the stub fell back to the WEST end and ran into U221.5's +5V_RAW foot -- a stub out of
        # the far end leads away from the band's other pins on every board. The end is the one
        # whose tip is nearer the band's next pin (the following `along` pin of another part, else
        # the one before); "away from the part's centre" picked the wrong end of a 3.4 mm power pin
        # that runs through its package (U205.7/.11, esc_pre2). If that end would cross a foreign
        # pad, the pin gets no stub: the band (or the router) meets the pin itself.
        al_ = list(rule.get("along", ()))
        i_ = al_.index(key)
        nxt = ([k_ for k_ in al_[i_ + 1:] if k_.split(".", 1)[0] != ref]
               + [k_ for k_ in reversed(al_[:i_]) if k_.split(".", 1)[0] != ref])
        if nxt:
            tx, ty = P.pad(*nxt[0].split(".", 1))
        else:
            tx, ty = 2 * cx - P.at(ref)[0], 2 * cy - P.at(ref)[1]
        if (tx - cx) * ux + (ty - cy) * uy < 0:
            ux, uy = -ux, -uy
        # the nearest other-net pad of the same part: its lateral gap and the pitch
        gap, pitch = None, None
        for o in p["pads"]:
            if o is q or not o["num"] or o["net"] == q["net"]:
                continue
            ox, oy = P.world(ref, [o["xy"]])[0]
            d = math.hypot(ox - cx, oy - cy)
            # a neighbour BESIDE the pin fences it; one in line with its axis (a resistor's other
            # land) does not -- the escape runs away from it
            if abs((ox - cx) * ux + (oy - cy) * uy) > abs(-(ox - cx) * uy + (oy - cy) * ux):
                continue
            ohw = min(o["size"]) / 2.0
            g_ = d - half_w - ohw
            if gap is None or g_ < gap:
                gap, pitch = g_, d
        if gap is None or gap >= 2 * zc:
            continue
        # the full 2 x pitch the gate exempts (less 0.05): at +0.3 past the neighbours' clearance the
        # fill still met U221.7/.8's stubs in a 0.34 mm funnel between the row's end pins (esc_pre4)
        beyond = max(min(math.sqrt(max(zc * zc - max(gap, 0.0) ** 2, 0.0)) + 0.3, 2.0 * pitch),
                     2.0 * pitch - 0.05)

        # the stub's run beyond the pad must clear every other-net pad of the part (0.2): the
        # target-facing end of U221.7 ran across U221.9, its exposed GND pad (esc_pre3)
        def _clear(sx, sy):
            for o in p["pads"]:
                if not o["num"] or o["net"] == q["net"]:
                    continue
                ox, oy = P.world(ref, [o["xy"]])[0]
                oa = math.radians(P.at(ref)[2] + float(o.get("rot") or 0.0))
                oc, os_ = math.cos(oa), math.sin(oa)
                for s_ in np.linspace(half_len, half_len + beyond, 8):
                    qx, qy = cx + sx * s_ - ox, cy + sy * s_ - oy
                    lx, ly = abs(qx * oc + qy * os_), abs(-qx * os_ + qy * oc)
                    if math.hypot(max(lx - o["size"][0] / 2.0, 0.0),
                                  max(ly - o["size"][1] / 2.0, 0.0)) < half_w + 0.2:
                        return False
            return True
        if not _clear(ux, uy):
            continue
        x1, y1 = cx + ux * (half_len + beyond), cy + uy * (half_len + beyond)
        out.append(dict(key=key, net=rule["net"], layer=pin_layer, width=round(2 * half_w, 3),
                        pts=[[round(cx, 3), round(cy, 3)], [round(x1, 3), round(y1, 3)]],
                        pitch=round(pitch, 3), beyond=round(beyond, 3)))
    return out


def _simplify(pts, tol):
    """Douglas-Peucker on a closed ring (iterative)."""
    if len(pts) > 1 and tuple(pts[0]) == tuple(pts[-1]):
        pts = pts[:-1]
    if len(pts) < 4:
        return pts
    a = np.asarray(pts, float)
    far = int(np.argmax(np.hypot(*(a - a[0]).T)))
    keep = {0, far, len(a) - 1}
    stack = [(0, far), (far, len(a) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        p, d = a[i], a[j] - a[i]
        n = math.hypot(*d)
        seg = a[i + 1:j]
        dist = (np.abs(d[0] * (seg[:, 1] - p[1]) - d[1] * (seg[:, 0] - p[0])) / n
                if n > 1e-12 else np.hypot(*(seg - p).T))
        k = int(np.argmax(dist))
        if dist[k] > tol:
            keep.add(i + 1 + k)
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return [tuple(a[k]) for k in sorted(keep)]


def design_dt(notes):
    """The board's design temperature rise for copper sizing: quality.temp_rise_c, else 10 C.

    ⚠ THE POURS SIZED AT 10 C WHATEVER THE BOARD SAID (brain_board rPS_t1, 2026-11-20): the
    brain moved to a 20 C design rise (BRAIN_POWER_SIZING), the router and the gate read it
    from quality.temp_rise_c, but width_for's 10 C default sized every pour band and every
    land's via array -- a 6.5 A land asked 4 barrels for 2.61 mm where 2.61 / 0.67 is 4 but
    3.97 / 0.67 is 6, and the bands drew wider than the layer had room for."""
    return float(((notes or {}).get("quality") or {}).get("temp_rise_c") or 10.0)


def width_for(amps, dT=10.0, min_mm=0.2, q=None, layer="F.Cu"):
    """Track width (mm) to DRAW on `layer` (outer by default) for a current at a dT C rise:
    copper.drawn_width_mm -- the need quality and the power gate judge with (q = the board's
    quality notes, for its foil), plus one raster step, rounded up to 0.05 mm, never under min_mm."""
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from copper import drawn_width_mm
    return drawn_width_mm(amps, layer, dict(q or {}, temp_rise_c=dT), min_mm)


def auto_pour(rules, parts, notes=None):
    """OPT-IN (an `auto_pour` rule; no rule, no change): every `current` rule at or above
    its `amps` becomes a `pour` on its `layer` along all the net's pads, instead of a width.

    ⚠ WHY (output_power, 2026-11-13): as `current` widths, two 10 A nets asked 7.2 mm and six
    5 A port nets 2.8 mm, through a field of QFN and FET pads: 17-27 nets stayed open at
    0.22-0.43 region fill, 49-110 vias -- the router had no lanes left. The same paths as
    pours (the 10 A on the free In2, the 5 A on F.Cu) routed 0 open, and the finish closed.
    A trace that wide is a pour drawn badly. `max_frac` (default 0.25) is the guard the
    widths() note asks for: a pour whose outline, once the parts are placed, covers more of
    the board than that is dropped and the net goes back to its width (_pours says so).

    auto_pour(amps, layer [, max_frac, width_mm, layers_by_net, whole, around, clear_margin]) -- around: each
    band goes round other nets' pads on its layer (pour_around), not through them. The pour runs along the net's
    declared power_paths terminals when it has any, else its non-IC pads. A net with its own
    `pour` rule, or declared `copper` tracks, is left alone. Returns (rules, lines)."""
    ap = [r for r in rules if r["kind"] == "auto_pour"]
    if not ap:
        return rules, []
    a = ap[-1]
    poured = {r["net"] for r in rules if r["kind"] == "pour"}
    # ⚠ A DECLARED PATH IS THE NET'S COPPER (brain_board esc13, lead 2026-11-22): +5V_CM5's declared
    # B.Cu / F.Cu route to J201 still drew a whole-net F.Cu hull over U205's cell (69 other pads inside),
    # which left +5V_BB's band no room. A net with declared copper tracks is skipped like a poured one --
    # by rule, not by setting its amps under the threshold.
    poured |= {r["net"] for r in rules if r["kind"] == "copper" and r.get("tracks")}
    out, lines = [], []
    for r in rules:
        if r["kind"] == "current" and float(r["amps"]) >= float(a["amps"]) - 1e-9                 and r["net"] not in poured:
            along = ["%s.%s" % (ref, q["num"]) for ref, p in sorted(parts.items())
                     for q in p["pads"] if q["net"] == r["net"] and q["num"]]
            # an IC's pins on a power net are TAPS (sense, supply), not the current's path:
            # a hull through them took in 8-26 other nets' pads round the PD controllers
            # (output_power, opa). The track reaches them; the pour spans the parts the
            # current flows through.
            path = [x for x in along if not re.match(r"^U\d", x)]
            along = path if len(path) >= 2 else along
            # ...and where the board DECLARES the current's path (quality.power_paths), the
            # pour runs along exactly its terminals: on an outer layer a hull through every
            # pad on the net takes in other nets' pads (opaf: PA_VCC and PB_VOUT open, the
            # hand pours along from -> to closed 0 / 0)
            pp = [x for p_ in ((notes or {}).get("quality", {}) or {}).get("power_paths", ()) or ()
                  if p_["net"] == r["net"]
                  for x in [p_["from"]] + list(p_["to"] if isinstance(p_["to"], (list, tuple)) else [p_["to"]])]
            if len(set(pp)) >= 2:
                along = sorted(set(pp))
            layer = (a.get("layers_by_net") or {}).get(r["net"], a["layer"])
            w = float(a.get("width_mm") or max(3.0, width_for(float(r["amps"]), design_dt(notes))))
            # ⚠ THE BAND LOSES ITS FILL CLEARANCE ON EACH SIDE (brain_board mV0, 2026-11-16):
            # 5 A bands drawn 3.0 mm (IPC 2.77) filled 1.1-2.4 mm wide where other nets'
            # escapes ran along them -- 0.5 mm of zone clearance off each side took the IPC
            # width away. clear_margin: the band is the IPC width plus twice the board's zone
            # clearance (notes["zone_clearance"], KiCad's 0.5 default), never under 3.0.
            if a.get("clear_margin") and not a.get("width_mm"):
                clr = float((notes or {}).get("zone_clearance") or 0.5)
                # outer-layer IPC as above, on every layer: inner IPC for 10 A is 18.8 mm, a
                # plane not a band (In2's 10 A bands closed at 7.2)
                w = max(w, round(math.ceil((width_for(float(r["amps"]), design_dt(notes)) + 2 * clr) / 0.05 - 1e-9) * 0.05, 2))
            out.append(dict(kind="pour", net=r["net"], layer=layer, along=along, width_mm=w,
                            why="auto_pour: %s at %.1f A -- %s" % (r["net"], float(r["amps"]), r["why"]),
                            src=r.get("src", ""), hard=False, auto_amps=float(r["amps"]),
                            max_frac=float(a.get("max_frac", 0.25)),
                            **({"whole": True} if a.get("whole") else {}),
                            **({"around": True} if a.get("around") else {})))
            lines.append("%s %.1f A -> pour on %s along %d pad(s), %.1f mm" % (
                r["net"], float(r["amps"]), layer, len(along), w))
        else:
            out.append(r)
    return out, lines


def widths(rules):
    """{net: width mm} from the intent's `current` rules -- what a generator writes into
    notes["net_widths"]: the outer-copper width (width_for; inner copper is judged by its
    thinner foil in copper.required_width_mm, IPC-2152, not by 2221's halved inner k).

    ⚠ WHY (output_panel, 2026-11-11): +3V3 as a signal tree took 27 vias and 189 mm; as a
    pour on In2 (the only inner signal layer) 51 vias, one per pin, and it pushed 450 mm of
    escapes off In2 (pair faults 1 -> 3); as a 0.4 mm tree 30 vias and 0 faults. Power is a
    width, from the current it carries; a pour only where a region has a layer to spare."""
    out = {}
    for r in rules:
        if r["kind"] == "current":
            out[r["net"]] = width_for(float(r["amps"]), r.get("dT", 10.0))
    return out


def read_descriptions(net_path):
    """{ref: description} from a KiCad .net (SKiDL writes each part's description there:
    "U7 VCC bypass", "MCU supply decoupling")."""
    txt = open(net_path, encoding="utf-8").read()
    out = {}
    for b in re.split(r"\(comp\s", txt)[1:]:
        m, d = re.search(r'\(ref "?([^")\s]+)', b), re.search(r'\(description "([^"]*)"', b)
        if m and d:
            out[m.group(1)] = d.group(1)
    return out


def read_values(net_path):
    """{ref: value} from a KiCad .net (the components' (value ...))."""
    txt = open(net_path, encoding="utf-8").read()
    return {m.group(1): m.group(2) for m in re.finditer(r'\(comp\s*\(ref "?([^")\s]+)"?\)\s*\(value "?([^")]*)"?\)', txt)}


def report(stem, rules, H=None, placements=None, parts_path=None):
    parts = json.load(open(parts_path or stem + ".parts.json", encoding="utf-8"))["parts"]
    notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    if placements is not None:
        notes["placements"] = placements
    notes["_regions"] = {r["name"]: r["poly"] for r in rules if r["kind"] == "region"}
    notes["_panel"] = [r for r in rules if r["kind"] == "panel"]
    P = Placed(parts, notes["placements"])
    H = H if H is not None else heights()
    rows = []
    for i, r in enumerate(rules):
        for s, subj, det in check(r, P, notes, H):
            rows.append((s, i, r, subj, det))
    return rows


def selftest():
    """Synthetic parts: each rule kind broken and met once."""
    sq = [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]]

    def part(nets=("A", "B")):
        return {"fpid": "X", "side": "F", "anchor": "pads", "at": [0, 0, 0], "crtyd": sq, "fab": [-0.5, 0.5, -0.5, 0.5],
                "pads": [{"num": str(i + 1), "net": n, "xy": [i - 0.5, 0.0], "size": [0.5, 0.5], "rot": 0, "tht": False}
                         for i, n in enumerate(nets)]}
    parts = {"D1": part(), "D2": part(), "D3": part(), "J1": part(), "U1": part(("VCC", "GND")), "C1": part(("VCC", "GND"))}
    pl = {"D1": [0, 0, 0], "D2": [2, 0, 0], "D3": [4.1, 0, 0], "J1": [10, 0, 90], "U1": [-5, 0, 0], "C1": [-5, 2, 0]}
    notes = {"placements": pl, "outline_mm": [30, 10]}
    P = Placed(parts, pl)
    t = lambda r: min((s for s, _, _ in check(r, P, notes)), default=9e9)     # noqa: E731
    assert t({"kind": "array", "refs": "^D", "axis": "x", "pitch": 2.0}) < 0      # D3 0.1 off pitch
    assert t({"kind": "array", "refs": ["D1", "D2"], "axis": "x", "pitch": 2.0}) >= 0
    # J1 at 90: its local +X points board +Y; a 3 mm stroke that way meets nothing, -Y local... none
    assert t({"kind": "mate", "ref": "J1", "dir": "L+X", "length": 3.0}) > 0
    assert t({"kind": "mate", "ref": "D2", "dir": "+X", "length": 2.0}) < 0       # into D3
    assert t({"kind": "thermal", "ref": "U1", "others": ["D1"], "apart_mm": 5.0}) < 0
    assert t({"kind": "decap", "cap": "C1", "pin": "U1.1", "max_mm": 2.5}) >= 0
    assert t({"kind": "decap", "cap": "C1", "pin": "U1.1", "max_mm": 1.5}) < 0
    assert t({"kind": "keepout", "poly": [[1.5, -1], [2.5, -1], [2.5, 1], [1.5, 1]]}) < 0
    assert t({"kind": "outline"}) >= 0
    print("place_intent selftest: ok")


def main(argv):
    if argv[:1] == ["--selftest"]:
        selftest()
        return 0
    stem = os.path.abspath(argv[0][:-len(".kicad_pcb")] if argv[0].endswith(".kicad_pcb") else argv[0])
    rules = json.load(open(argv[1], encoding="utf-8"))
    pl = json.load(open(argv[2], encoding="utf-8")) if len(argv) > 2 else None
    rows = report(stem, rules, placements=pl)
    worst = {}
    for s, i, r, subj, det in rows:
        if i not in worst or s < worst[i][0]:
            worst[i] = (s, subj, det)
    nh = ns = 0
    for i, r in sorted(enumerate(rules), key=lambda t: worst.get(t[0], (9e9,))[0]):
        if i not in worst:
            continue
        s, subj, det = worst[i]
        bad = s < 0
        nh += bad and r.get("hard", True)
        ns += bad and not r.get("hard", True)
        print("%s %7.2f  %-8s %-10s %-34s %s" % ("BROKEN" if bad else "ok    ", s, r["kind"], subj, det[:34],
                                                 ("[%s] " % r["src"] if r.get("src") else "") + r.get("why", "")[:70]))
    print("%d rules, %d hard broken, %d soft broken" % (len(rules), nh, ns))
    return 1 if nh else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


# ⚠ A HARD near / decap A REGION CANNOT MEET IS SAID BEFORE PLACEMENT (lead 2026-11-22): sw1 /
# sw2 bound C3 (U5's VIN cap, hard 2.0 mm at U5.2) to region pd while U5 sat in power, and
# the flow placed for 20 minutes to end in NO ROOM. feasibility() reads each hard near /
# decap rule against the subject's region and the target's (its pin's) region -- or the
# pin itself when the target is held -- before anything is placed:
#   INFEASIBLE     no point of the subject's region lies within reach of the target (the
#                  regions' gap > max_mm + both parts' half-diagonals): the flow stops
#   REGION SPLIT   a hard rule of <= 3 mm whose subject is BOUND to a different region than
#                  its target: feasible only along their border -- an intent error, it stops too
def _half_diag(part):
    c = np.asarray(part.get("crtyd") or [[0, 0], [0, 0]], float)
    return 0.5 * float(np.hypot(*np.ptp(c, axis=0)))


def feasibility(rules, parts, notes):
    """(infeasible lines, region-split lines) for every hard near / decap rule."""
    polys = {r["name"]: np.asarray(r["poly"], float) for r in rules if r["kind"] == "region"}
    board = np.asarray(notes.get("outline_poly") or _rect(notes["outline_mm"]), float)
    reg = {}
    for r in rules:
        if r["kind"] == "in_region" and r.get("region") in polys:
            for x in _refs(r["refs"], parts):
                reg.setdefault(x, r["region"])
    held = {r["ref"]: [r["xy"][0], r["xy"][1], r.get("rot", 0.0)] for r in rules
            if r["kind"] in ("fixed", "pin") and r.get("xy") is not None and r.get("ref") in parts}
    P = Placed(parts, held)
    bad, split = [], []
    for i, r in enumerate(rules):
        if r["kind"] not in ("near", "decap") or not is_hard(r):
            continue
        sub = r.get("cap") or r.get("ref")
        tgt = r.get("pin") or r.get("target") or ""
        anc = tgt.split(".", 1)[0]
        if sub not in parts or anc not in parts or sub in held:
            continue
        rs, ra = reg.get(sub), reg.get(anc)
        sp = polys.get(rs, board)
        reach = float(r["max_mm"]) + _half_diag(parts[sub])
        if anc in held:
            tp = P.pad_poly(*tgt.split(".", 1)) if "." in tgt else P.crtyd(anc)
            gap = max(0.0, _poly_dist(sp, tp)) if not _inside(sp, np.asarray(tp, float)).any() else 0.0
        else:
            tp = polys.get(ra, board)
            reach += _half_diag(parts[anc])
            gap = max(0.0, _poly_dist(sp, tp))
        if gap > reach:
            bad.append("INFEASIBLE rule %d: %s (region %s) can come no nearer than %.1f mm to %s (%s), "
                       "past its hard %s %g mm + sizes (%.1f) [%s]"
                       % (i, sub, rs or "board", gap, tgt, ("held" if anc in held else "region %s" % (ra or "board")),
                          r["kind"], r["max_mm"], reach, r.get("src", "")))
        elif float(r["max_mm"]) <= 3.0 and anc not in held and rs is not None and rs != ra:
            split.append("REGION SPLIT rule %d: %s is bound to region %s but its hard %s %g mm target %s is in %s -- "
                         "it can hold only along their border; bind it with its IC"
                         % (i, sub, rs or "board", r["kind"], r["max_mm"], tgt, ra or "board"))
    return bad, split


# ----------------------------------------------------------------------------- kelvin ties
# ⚠ A KELVIN TIE IS SEATED ON ITS SHUNT'S LAND, NOT BY THE NET GRAPH (brain_board fold12-14,
# 2026-11-27): NT11 / NT12 / NT21 / NT22 (PA/PB sense ties) have no courtyard, the net graph
# put each one at the quadratic optimum of its nets -- NT11 in the middle of the FL1.4 -> R70.1
# path, its PA_ISENP_K pad carving the PA_VBUS pour to 0.60 mm -- and quality A30 read all four
# NOT ON a shunt land for three folds. A tie with one pad on a shunt's net is now a member of a
# hard group on that shunt (kelvin_seats): its pad centred on the land's edge, the tie pointing
# away from the shunt square to the current axis, both ties of one shunt on the same side. A
# rule that already places the tie is kept and checked instead (refused off the land).
SHUNT_VALUE = re.compile(r"^\s*\d+(\.\d+)?\s*m(R|Ohm|Ω)", re.I)


def kelvin_ties(parts, values):
    """({tie: (shunt, land pad num, tie pad num on the land)}, [(tie, why)]) -- every two-pad net
    tie whose pad shares a net with a pad of a two-pad milliohm resistor; a tie that touches more
    than one shunt land is ambiguous and listed, not guessed."""
    shunt_pads = {}
    for r, p in parts.items():
        if re.match(r"R\d", r) and SHUNT_VALUE.match(values.get(r, "") or "") and len(p["pads"]) == 2:
            for q in p["pads"]:
                if q.get("net"):
                    shunt_pads.setdefault(q["net"], []).append((r, q["num"]))
    out, amb = {}, []
    for t, p in sorted(parts.items()):
        if not is_net_tie(t) or len(p["pads"]) != 2:
            continue
        hits = [(s, n, q["num"]) for q in p["pads"] for s, n in shunt_pads.get(q.get("net"), ())]
        if len(hits) == 1:
            out[t] = hits[0]
        elif len(hits) > 1:
            amb.append((t, "touches %s" % ", ".join("%s.%s" % (s, n) for s, n, _ in hits)))
    return out, amb


def _pad(part, num):
    return next(q for q in part["pads"] if q["num"] == num)


def kelvin_seat(parts, tie, shunt, land, tpad):
    """[dx, dy, rot] of the tie in the shunt's frame: the tie's land pad centred on the land's
    edge square to the shunt's axis (its pad 1 -> pad 2 turned +90 degrees), its other pad
    pointing outward."""
    S, T = parts[shunt], parts[tie]
    L = _pad(S, land)
    other = next(q for q in S["pads"] if q["num"] != land)
    p1, p2 = sorted((L, other), key=lambda q: _pin_key("R." + q["num"]))
    ax = np.subtract(p2["xy"], p1["xy"], dtype=float)
    ax /= max(float(np.hypot(*ax)), 1e-9)
    n = np.array([-ax[1], ax[0]])
    c = _rot([[L["size"][0] / 2.0, L["size"][1] / 2.0], [L["size"][0] / 2.0, -L["size"][1] / 2.0]],
             L.get("rot", 0.0))
    h = float(np.abs(c @ n).max())
    a = _pad(T, tpad)
    b = next(q for q in T["pads"] if q["num"] != tpad)
    d = np.subtract(b["xy"], a["xy"], dtype=float)
    dr = round(math.degrees(math.atan2(n[1], n[0]) - math.atan2(d[1], d[0])), 6) % 360.0
    off = np.asarray(L["xy"], float) + h * n - _rot([a["xy"]], dr)[0]
    return [round(float(off[0]), 4), round(float(off[1]), 4), dr]


def _group_of(rules, ref):
    """(rule, as_anchor) for the group that holds ref, or (None, None)."""
    for r in rules:
        if r.get("kind") == "group":
            if r["anchor"] == ref:
                return r, True
            if ref in r["members"]:
                return r, False
    return None, None


def _on_land(parts, shunt, spose, land, tie, tpose, tpad):
    """True when the tie's land pad centre lies on the shunt land (inside it or on its edge)."""
    L = _pad(parts[shunt], land)
    w, h = L["size"][0] / 2.0, L["size"][1] / 2.0
    box = _rot([[-w, -h], [w, -h], [w, h], [-w, h]], L.get("rot", 0.0)) + np.asarray(L["xy"], float)
    box = np.asarray(spose[:2], float) + _rot(box, spose[2])
    pt = (np.asarray(tpose[:2], float) + _rot([_pad(parts[tie], tpad)["xy"]], tpose[2])[0])[None]
    if _inside(box, pt)[0]:
        return True
    return min(float(_seg_dist(pt, box[i], box[(i + 1) % 4])[0]) for i in range(4)) < 2e-3


def kelvin_seats(rules, parts, values):
    """(rules, lines, refused): every kelvin tie no rule places joins a hard group on its shunt
    (the shunt's own group when it has one, as anchor or member). A tie a rule already places is
    checked instead: off its land -- or held while its shunt is placed apart, so its land cannot
    be known before placement -- it is refused."""
    ties, amb = kelvin_ties(parts, values)
    rules = [dict(r, members=dict(r["members"])) if r.get("kind") == "group" else r for r in rules]
    fixed = {r["ref"]: (r["xy"][0], r["xy"][1], float(r.get("rot", 0.0)))
             for r in rules if r.get("kind") == "fixed"}
    placed = {r["ref"] for r in rules if r.get("kind") in ("fixed", "pin", "panel")}
    lines, bad = [], ["%s %s -- name its shunt with a group rule" % a for a in amb]
    for t, (s, land, tpad) in sorted(ties.items()):
        if parts[t].get("side", "F") != parts[s].get("side", "F"):
            bad.append("%s is on %s, its shunt %s on %s" % (t, parts[t].get("side", "F"), s,
                                                          parts[s].get("side", "F")))
            continue
        g, g_anchor = _group_of(rules, t)
        if t in placed or g is not None:
            if g is not None and (g["anchor"] == s or s in g["members"]):
                spose = (0.0, 0.0, 0.0) if g["anchor"] == s else tuple(g["members"][s])
                tpose = (0.0, 0.0, 0.0) if g_anchor else tuple(g["members"][t])
            elif t in fixed and s in fixed:
                spose, tpose = fixed[s], fixed[t]
            else:
                bad.append("%s: held by a rule while its shunt %s is placed apart -- its land cannot be "
                           "checked; drop the tie's rule (it is seated on %s.%s automatically)" % (t, s, s, land))
                continue
            if _on_land(parts, s, spose, land, t, tpose, tpad):
                lines.append("%s on %s.%s (by its own rule)" % (t, s, land))
            else:
                bad.append("%s: pad %s is NOT ON %s.%s -- the sense would read the pour, not the shunt; drop "
                           "the tie's rule (it is seated automatically) or put the pad on the land"
                           % (t, tpad, s, land))
            continue
        off = kelvin_seat(parts, t, s, land, tpad)
        sg, s_anchor = _group_of(rules, s)
        if sg is None:
            sg = dict(kind="group", anchor=s, members={}, hard=True, src="kelvin_seats (netlist)",
                      why="kelvin ties on %s's lands (place_intent.kelvin_seats)" % s)
            rules.append(sg)
            s_anchor = True
        if s_anchor:
            sg["members"][t] = off
        else:
            mx, my, mr = sg["members"][s]
            o = _rot([off[:2]], mr)[0]
            sg["members"][t] = [round(mx + float(o[0]), 4), round(my + float(o[1]), 4), (mr + off[2]) % 360.0]
        lines.append("%s seated on %s.%s at [%.3f, %.3f, %.0f] in %s's frame" % (t, s, land, off[0], off[1], off[2], s))
    return rules, lines, bad


# ----------------------------------------------------------------------------- fixed-hold overlaps
# ⚠ TWO HOLDS ARE CHECKED AGAINST EACH OTHER HERE, OR BY NOBODY (brain_board fold15_s2,
# 2026-11-27): p22's NT21 / NT22 physical holds sat under D20's mP0 snapshot; place_init seats
# a fixed part where it is told, and the clash first showed as a 0.0015 mm DRC clearance on a
# routed board 5 hours later. Every pair of parts the intent pins (fixed, and the members of a
# group on a fixed anchor) is checked before placement: by courtyard, a part with none (a net
# tie) by its fab box, else by its pads. A kelvin tie against its own shunt, and two parts of
# one group, are drawn together and not checked.
def _shapes(part):
    if part.get("crtyd"):
        return [part["crtyd"]]
    f = part.get("fab")
    if f:
        return [[[f[0], f[2]], [f[1], f[2]], [f[1], f[3]], [f[0], f[3]]]]
    out = []
    for q in part["pads"]:
        w, h = q["size"][0] / 2.0, q["size"][1] / 2.0
        out.append((_rot([[-w, -h], [w, -h], [w, h], [-w, h]], q.get("rot", 0.0))
                    + np.asarray(q["xy"], float)).tolist())
    return out


def held_poses(rules):
    """{ref: (x, y, rot)} of every part the intent pins: fixed, and the members of a group on a
    fixed anchor."""
    pose = {r["ref"]: (r["xy"][0], r["xy"][1], float(r.get("rot", 0.0))) for r in rules if r.get("kind") == "fixed"}
    for r in rules:
        if r.get("kind") == "group" and r["anchor"] in pose:
            ax, ay, ar = pose[r["anchor"]]
            for m, (dx, dy, dr) in r["members"].items():
                o = _rot([[dx, dy]], ar)[0]
                pose.setdefault(m, (ax + float(o[0]), ay + float(o[1]), (ar + dr) % 360.0))
    return pose


def hold_overlaps(rules, parts, values=None, tol=0.01):
    """['A x B: ...'] for every two held parts on one side whose shapes overlap by more than tol mm."""
    pose = {r: p for r, p in held_poses(rules).items() if r in parts}
    same = set()
    for r in rules:
        if r.get("kind") == "group":
            g = [r["anchor"]] + list(r["members"])
            same |= {(a, b) for a in g for b in g}
    for t, (s, _l, _p) in kelvin_ties(parts, values or {})[0].items():
        same |= {(t, s), (s, t)}
    W = {r: [np.asarray([x, y]) + _rot(p, a) for p in _shapes(parts[r])] for r, (x, y, a) in pose.items()}
    W = {r: v for r, v in W.items() if v}
    refs = sorted(W)
    box = {r: (min(p[:, 0].min() for p in W[r]), max(p[:, 0].max() for p in W[r]),
               min(p[:, 1].min() for p in W[r]), max(p[:, 1].max() for p in W[r])) for r in refs}
    out = []
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            if (a, b) in same or parts[a].get("side", "F") != parts[b].get("side", "F"):
                continue
            A, B = box[a], box[b]
            if A[0] >= B[1] or B[0] >= A[1] or A[2] >= B[3] or B[2] >= A[3]:
                continue
            dep = max(-_poly_dist(pa, pb) for pa in W[a] for pb in W[b])
            if dep > tol:
                c = np.mean(np.concatenate(W[a] + W[b]), axis=0)
                out.append("%s x %s: held shapes overlap %.2f mm near (%.2f, %.2f)" % (a, b, dep, c[0], c[1]))
    return out
