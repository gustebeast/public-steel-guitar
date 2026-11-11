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
    elif k == "in_region":
        poly = notes["_regions"][rule["region"]]
        for ref in _refs(rule["refs"], parts):
            s = float(_edge_dist_inside(poly, P.crtyd(ref)).min())
            out.append((s, ref, "inside region %s" % rule["region"]))
    elif k in ("apart", "thermal"):
        a = _refs(rule.get("a") or [rule["ref"]], parts)
        b = _refs(rule.get("b") or rule["others"], parts)
        m = rule.get("min_mm", rule.get("apart_mm"))
        for x in a:
            best = min((_poly_dist(P.crtyd(x), P.crtyd(y)), y) for y in b if y != x)
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


def auto_decaps(parts, notes, values=None, max_mm=3.0, bulk_mm=8.0, bulk_f=1.5e-6, ground=("GND",)):
    """Rules for every capacitor across a SUPPLY net (SUPPLY: '+...', VCC, VDD, VBUS, VREF, ...)
    and ground: a small one (< bulk_f) gets `decap` at the nearest IC pin on that net, a bulk
    one `near` that part. The sources considered are ICs, ferrites and inductors (a buck's
    output caps belong to its inductor, a filtered rail's to its bead). values = {ref: '100n'} (read_values); without it every cap is small.
    Signal-net capacitors (crystal loads, RC filters, resets) get no rule: they are the
    circuit's, not the supply's."""
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
            rules.append({"kind": "decap", "cap": c, "pin": pin, "max_mm": max_mm, "hard": False,
                          "why": "%s across %s and ground: at its supply pin" % (c, sup), "src": "auto_decaps (netlist)"})
    return rules


def read_values(net_path):
    """{ref: value} from a KiCad .net (the components' (value ...))."""
    txt = open(net_path, encoding="utf-8").read()
    return {m.group(1): m.group(2) for m in re.finditer(r'\(comp\s*\(ref "?([^")\s]+)"?\)\s*\(value "?([^")]*)"?\)', txt)}


def report(stem, rules, H=None):
    parts = json.load(open(stem + ".parts.json", encoding="utf-8"))["parts"]
    notes = json.load(open(stem + ".board.json", encoding="utf-8"))
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
    rows = report(stem, rules)
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
