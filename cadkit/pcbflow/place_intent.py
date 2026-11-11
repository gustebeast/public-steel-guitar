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
  hole      xy d keepout           a mounting hole and its head's clearance: no courtyard
  keepout   poly [side]            no courtyard inside (deck wall, standoff, rib, cable run)
  height    poly max_mm            no part taller than max_mm inside (lid, deck, strings)
  panel     ref edge at face [overhang] [anchor]
                                   a connector whose MOUTH the panel fixes: the body front
                                   (F.Fab extent toward `edge`) at face + overhang, its
                                   centre `at` along the edge
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
  region    name poly              a floorplan band; in_region refs region keeps parts in it
  apart     a b min_mm             two groups' courtyards at least min_mm apart (noise)
  thermal   ref others apart_mm    a heat source off the sensors and off each other
  decap     cap pin max_mm         the capacitor's land on the pin's net within max_mm of it
  near      ref target max_mm      target = a part (courtyard) or a pin "U4.8"
  chain     refs [max_ratio]       a pair's path order: sum of hops <= max_ratio x straight
  rot       ref allowed            rotation in the allowed set
  side      ref F|B
  array     refs axis pitch [tol]  one rule for a repeat: same off-axis, equal pitch along
  current   net amps [dT]          the current a net carries: widths() turns it into the track
                                   width (IPC-2221), so power is drawn as power
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
import json
import math
import os
import re
import sys

import numpy as np

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


def check(rule, P, notes, H=None):
    """[(slack mm, subject, detail)] for one rule against placement P."""
    k = rule["kind"]
    out = []
    parts = P.parts
    if k == "outline":
        poly = notes.get("outline_poly") or _rect(notes["outline_mm"])
        skip = set(rule.get("except", ())) | {r["ref"] for r in notes.get("_panel", ())}
        for ref in parts:
            if ref in skip:
                continue
            s = float(_edge_dist_inside(poly, P.crtyd(ref)).min())
            out.append((s, ref, "courtyard to Edge.Cuts"))
    elif k == "hole":
        c, keep = np.asarray(rule["xy"], float), rule["d"] / 2.0 + rule.get("keepout", 0.0)
        for ref in parts:
            cy = P.crtyd(ref)
            s = _poly_dist(cy, _circle(c, keep))
            if s < 3.0:
                out.append((s, ref, "to the hole's keep-out at %.2f,%.2f" % tuple(c)))
    elif k == "keepout":
        poly = rule["poly"]
        for ref in parts:
            if rule.get("side") and parts[ref]["side"] != rule["side"]:
                continue
            s = _poly_dist(P.crtyd(ref), poly)
            if s < 3.0:
                out.append((s, ref, "to keep-out %s" % rule.get("name", "")))
    elif k == "height":
        H = H if H is not None else heights()
        for ref in parts:
            h = H.get(parts[ref]["fpid"])
            if h is None:
                continue
            if _poly_dist(P.crtyd(ref), rule["poly"]) < 0:
                out.append((rule["max_mm"] - float(h), ref, "%.2f tall under a %.2f limit" % (h, rule["max_mm"])))
    elif k == "panel":
        ref, e = rule["ref"], rule["edge"]
        ux, uy = DIRS[e]
        b = P.body(ref)
        front = float((b @ (ux, uy)).max())
        want = rule["face"] + rule.get("overhang", 0.0)
        out.append((-abs(front - want) + rule.get("tol", 0.05), ref,
                    "body front %.3f, the panel wants %.3f" % (front, want)))
        if "at" in rule:
            along = (0.0, 1.0) if ux else (1.0, 0.0)      # `at` is the board's own y (or x)
            mid = float(((b @ along).max() + (b @ along).min()) / 2.0)
            out.append((-abs(mid - rule["at"]) + rule.get("tol", 0.05), ref,
                        "centre along the edge %.3f, wanted %.3f" % (mid, rule["at"])))
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
            d = min(math.hypot(*(c - pp)) for c in cp)
            out.append((rule.get("max_mm", 1.5) - d, cap, "%.2f from %s (%s)" % (d, pin, net)))
    elif k == "near":
        ref, t, m = rule["ref"], rule["target"], rule["max_mm"]
        d = _poly_dist(P.crtyd(ref), P.target(t)) if "." not in t else \
            float(_edge_dist_inside(P.crtyd(ref), P.target(t)).max() * -1)
        d = max(d, 0.0)
        out.append((m - d, ref, "%.2f from %s" % (d, t)))
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
        out.append((0.0 if parts[ref]["side"] == rule["side"] else -1.0, ref, "on %s" % parts[ref]["side"]))
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
    elif k == "array":
        refs = _refs(rule["refs"], parts)
        ax = 0 if rule["axis"] in ("x", "X") else 1
        pts = sorted(((np.asarray(P.at(r)[:2]), r) for r in refs), key=lambda t: t[0][ax])
        tol = rule.get("tol", 0.02)
        off = [p[1 - ax] for p, _ in pts]
        for (p, r), (q, s) in zip(pts, pts[1:]):
            out.append((tol - abs((q[ax] - p[ax]) - rule["pitch"]), s, "pitch %.3f after %s" % (q[ax] - p[ax], r)))
        for (p, r) in pts:
            out.append((tol - abs(p[1 - ax] - off[0]), r, "off the row by %.3f" % (p[1 - ax] - off[0])))
    elif k == "region":
        pass
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


def auto_decaps(parts, notes, values=None, max_mm=3.0, bulk_mm=8.0, bulk_f=1.5e-6, ground=("GND",), more_mm=2.0):
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
    P = Placed(parts, notes.get("placements", {}))
    rules = []
    ics = [r for r in parts if re.match(r"^(U|FB|L)\d", r)]
    for c in sorted(r for r in parts if re.match(r"^C\d", r)):
        nets = {q["net"] for q in parts[c]["pads"]}
        if not (nets & set(ground)) or len(nets) != 2:
            continue
        sup = (nets - set(ground)).pop()
        if not SUPPLY.search(sup):
            continue
        cands = []
        for u in ics:
            for q in parts[u]["pads"]:
                if q["net"] == sup and q["num"]:
                    try:
                        d = min(math.hypot(*(x - P.pad(u, q["num"]))) for x in P.pads_on(c, sup))
                    except (KeyError, ValueError):
                        d = 0.0
                    cands.append((d, "%s.%s" % (u, q["num"])))
        if not cands:
            continue
        d, pin = min(cands)
        f = _farads((values or {}).get(c))
        if f is not None and f >= bulk_f:
            rules.append({"kind": "near", "ref": c, "target": pin.split(".")[0], "max_mm": bulk_mm, "hard": False,
                          "why": "%s, bulk on %s: beside the IC it feeds" % (c, sup), "src": "auto_decaps (netlist)"})
        else:
            rules.append({"kind": "decap", "cap": c, "pin": pin, "max_mm": max_mm, "hard": False, "weight": 1.0,
                          "why": "%s across %s and ground: at its supply pin" % (c, sup), "src": "auto_decaps (netlist)",
                          "_f": f if f is not None else 0.0})
    by = {}
    for r in rules:
        if r["kind"] == "decap":
            by.setdefault(r["pin"].split(".")[0], []).append(r)
    for rs in by.values():
        for k, r in enumerate(sorted(rs, key=lambda r: (r["_f"], r["cap"]))):
            if k:
                r["max_mm"], r["weight"] = max_mm + more_mm, 0.5
                r["why"] += " (a further cap on this IC: within reach, not packed)"
    for r in rules:
        r.pop("_f", None)
    return rules


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
    rules = []
    for L in sorted(r for r in parts if re.match(r"^L\d", r) and r not in skip):
        for n in sorted(rnets[L]):
            members = nets.get(n, set())
            if SUPPLY.search(n) or n in ground or len(members) > 4 or not any(ic(m) for m in members if m != L):
                continue
            grp = sorted(members - set(skip))
            b = sorted((sens | crystals) - set(grp))
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
        b = sorted(sens - set(loud))
        if b:
            rules.append({"kind": "apart", "a": loud, "b": b, "min_mm": edge_mm, "hard": False, "weight": 0.5, "forbid": False,
                          "why": "USB / relay edges (%s) off the analog parts" % " ".join(loud),
                          "src": "auto_floorplan (netlist)"})
    return rules


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


def width_for(amps, dT=10.0, oz=1.0, inner=False, min_mm=0.2):
    """IPC-2221 track width (mm) for a current: I = k dT^0.44 A^0.725, A in mil^2, k 0.048
    outer / 0.024 inner, 1 oz = 1.378 mil. Rounded up to 0.05 mm, never under min_mm."""
    k = 0.024 if inner else 0.048
    area = (amps / (k * dT ** 0.44)) ** (1.0 / 0.725)          # mil^2
    w = area / (1.378 * oz) * 0.0254                            # mm
    return round(max(min_mm, math.ceil(w / 0.05 - 1e-9) * 0.05), 2)


def widths(rules, inner=False, **kw):
    """{net: width mm} from the intent's `current` rules -- what a generator writes into
    notes["net_widths"]. The OUTER curve by default: IPC-2221's inner k (half the outer)
    is the chart IPC-2152 found far too conservative -- an inner track in a board with
    planes runs about as cool as an outer one -- and at 3 A it asks 3.6 mm against 1.4.

    ⚠ WHY (output_panel, 2026-11-11): +3V3 as a signal tree took 27 vias and 189 mm; as a
    pour on In2 (the only inner signal layer) 51 vias, one per pin, and it pushed 450 mm of
    escapes off In2 (pair faults 1 -> 3); as a 0.4 mm tree 30 vias and 0 faults. Power is a
    width, from the current it carries; a pour only where a region has a layer to spare."""
    out = {}
    for r in rules:
        if r["kind"] == "current":
            out[r["net"]] = width_for(float(r["amps"]), r.get("dT", 10.0), inner=inner, **kw)
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
