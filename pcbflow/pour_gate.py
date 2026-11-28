"""Pre-route pour gate: every declared pour leg's pins sit in one connected copper body.

    "C:/Program Files/KiCad/10.0/bin/python.exe" pour_gate.py BOARD.kicad_pcb NOTES_OR_INTENT.json

⚠ A POUR CUT BEFORE THE ROUTER IS A RAIL HANGING ON ROUTED BRIDGES (brain_board fold15 / fold16,
2026-11-28). V5_PRE's In3 north leg (U211.1-U36.5-R98.1) was cut from the L1 body by +24V's
higher-priority In3 band, and its B.Cu west leg (L1.2-U206.1-U42.1) by a frozen +5V_RAW B.Cu
track just north of L1 -- B.Cu carries no parts, so island removal kept a 12 mm2 stub. Both cuts
were in the pre-route fill of BOTH folds. fold15's router happened to bridge them; fold16_s2's
ripped the bridges ("3 of its 26 joins still share space") and all six L1.2 branches came back
OPEN, four hours later. A one-second check on the filled, unrouted board says so at place time.

THE BODY is the net's own copper after the pre-route fill: every filled piece of every zone of the
net, its declared tracks and vias, and its pads, joined where they touch on a shared copper layer
(a through via or a PTH pad is on every layer). A PIN of a leg is in a body when its pad is, or --
an SMD pin on another layer than its inner pour, which the router reaches with one via -- when a
filled piece of the leg's own layer lies under the pad or within PIN_REACH of its centre.

A leg passes when all its pins are in one body. Otherwise the line names the net, the leg, the pin
that is off the first pin's body, and what stands on the leg's own layer at the first point of the
pin-to-pin line where the first body's copper ends: another net's fill, track, via or pad (frozen
when declared) -- the thing to move, give way, or bridge with declared copper.

legs(notes): zones (dicts) carry "legs" (place_flow._pours: one along-list per pour rule merged into
the zone); an intent rules list works too (kind "pour" with "along").
"""
import json
import os
import sys

import pcbnew

PIN_REACH = 2.0             # mm: an SMD pin's pour may be this far off its centre (one via away)
STEP = 0.1                  # mm: sampling step along the pin-to-pin line, for the "split by" probe
CUT_LOOK = 3.0              # mm past the body's edge to look for the other net's copper that cut it
SHEET_ORIGIN = (100.0, 100.0)


def _mm(v):
    return pcbnew.ToMM(v)


def _pt(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def _sheet(x, y):
    """board mm -> the intent frame layout's messages use (y up, origin at SHEET_ORIGIN)."""
    return x - SHEET_ORIGIN[0], SHEET_ORIGIN[1] - y


def legs(notes):
    """[(net, layer, [pins])] from a notes dict (zone "legs") or an intent rules list."""
    out = []
    if isinstance(notes, dict):
        for z in notes.get("zones", ()):
            if isinstance(z, dict):
                for lg in z.get("legs") or ([z["along"]] if z.get("along") else []):
                    if len(lg) >= 2:
                        out.append((z["net"], z["layer"], list(lg)))
    else:
        for r in notes:
            if r.get("kind") == "pour" and len(r.get("along") or ()) >= 2:
                out.append((r["net"], r["layer"], list(r["along"])))
    return out


class _Net:
    """One net's copper as nodes (filled pieces, tracks, vias, pads) and their touching graph."""

    def __init__(self, board, net):
        self.b, self.net = board, net
        self.nodes = []             # (kind, layers set, SHAPE_POLY_SET, item, label)
        cu = [l for l in board.GetEnabledLayers().CuStack()]
        self.cu = cu
        for z in board.Zones():
            if z.GetIsRuleArea() or z.GetNetname() != net:
                continue
            for L in z.GetLayerSet().CuStack():
                fp = z.GetFilledPolysList(L)
                for i in range(fp.OutlineCount()):
                    ps = pcbnew.SHAPE_POLY_SET()
                    ps.AddOutline(fp.Outline(i))
                    for h in range(fp.HoleCount(i)):
                        ps.AddHole(fp.Hole(i, h))
                    self.nodes.append(("fill", {L}, ps, z, "%s fill" % board.GetLayerName(L)))
        for t in board.GetTracks():
            if t.GetNetname() != net:
                continue
            Ls = set(cu) if t.GetClass() == "PCB_VIA" else {t.GetLayer()}
            self.nodes.append(("via" if t.GetClass() == "PCB_VIA" else "track", Ls, None, t, t.GetClass()))
        for fp in board.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == net:
                    Ls = {L for L in cu if p.IsOnLayer(L)}
                    self.nodes.append(("pad", Ls, None, p, "%s.%s" % (fp.GetReference(), p.GetNumber())))
        self._polys = {}
        self.comp = self._components()

    def poly(self, i, L):
        k, Ls, ps, it, _ = self.nodes[i]
        if ps is not None:
            return ps
        key = (i, L)
        if key not in self._polys:
            s = pcbnew.SHAPE_POLY_SET()
            it.TransformShapeToPolygon(s, L, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
            self._polys[key] = s
        return self._polys[key]

    def _components(self):
        n = len(self.nodes)
        par = list(range(n))

        def find(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a
        bbs = []
        for i in range(n):
            L = next(iter(self.nodes[i][1])) if self.nodes[i][1] else None
            bbs.append(self.poly(i, L).BBox() if L is not None else None)
        for i in range(n):
            for j in range(i + 1, n):
                common = self.nodes[i][1] & self.nodes[j][1]
                if not common or bbs[i] is None or bbs[j] is None:
                    continue
                if self.nodes[i][0] == "fill" and self.nodes[j][0] == "fill":
                    continue                            # two pieces of one fill never touch
                if not bbs[i].Intersects(bbs[j]):
                    continue
                if find(i) == find(j):
                    continue
                for L in common:
                    a = pcbnew.SHAPE_POLY_SET(self.poly(i, L))
                    a.BooleanIntersection(self.poly(j, L))
                    if a.OutlineCount():
                        par[find(i)] = find(j)
                        break
        return [find(i) for i in range(n)]

    def pin(self, ref, num, layer):
        """Component ids this pin belongs to (its pad, or the leg-layer fill under / near it)."""
        ids = set()
        pos = None
        for i, (k, Ls, ps, it, lab) in enumerate(self.nodes):
            if k == "pad" and lab == "%s.%s" % (ref, num):
                ids.add(self.comp[i])
                pos = it.GetPosition()
        if pos is None:
            return None, None
        for i, (k, Ls, ps, it, lab) in enumerate(self.nodes):
            if k == "fill" and layer in Ls and ps.Collide(pos, pcbnew.FromMM(PIN_REACH)):
                ids.add(self.comp[i])
        return ids, pos

    def covers(self, comp, L, p):
        """Does component `comp` hold copper on layer L at point p?"""
        for i, (k, Ls, ps, it, lab) in enumerate(self.nodes):
            if self.comp[i] == comp and L in Ls and self.poly(i, L).Contains(p):
                return True
        return False


def _what_at(board, net, L, p):
    """Other-net copper on layer L at p: the thing that cuts the leg."""
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetNetname() == net or not z.IsOnLayer(L):
            continue
        if z.GetFilledPolysList(L).Contains(p):
            return "%s pour (priority %d%s)" % (z.GetNetname() or "no-net", z.GetAssignedPriority(),
                                                ", frozen" if z.GetZoneName() == "frozen" else "")
    for t in board.GetTracks():
        if t.GetNetname() != net and t.IsOnLayer(L) and t.HitTest(p, pcbnew.FromMM(0.15)):
            return "%s %s" % (t.GetNetname(),
                              "via" if t.GetClass() == "PCB_VIA" else "track w%.2f" % _mm(t.GetWidth()))
    for fp in board.GetFootprints():
        for pd in fp.Pads():
            if pd.GetNetname() != net and pd.IsOnLayer(L) and pd.HitTest(p, pcbnew.FromMM(0.15)):
                return "pad %s.%s [%s]" % (fp.GetReference(), pd.GetNumber(), pd.GetNetname())
    return None


def check(board, leg_list):
    """'POUR CUT: ...' lines, one per leg whose pins are not in one body."""
    bad, nets = [], {}
    for li, (net, layer, pins) in enumerate(leg_list):
        L = board.GetLayerID(layer)
        if net not in nets:
            nets[net] = _Net(board, net)
        N = nets[net]
        reps = []
        for pn in pins:
            ref, num = pn.split(".", 1)
            ids, pos = N.pin(ref, num, L)
            if ids is None:
                continue                                # a pin not on this board: not ours to judge
            reps.append((pn, ids, pos))
        if len(reps) < 2:
            continue
        legn = sum(1 for x in leg_list[:li] if x[0] == net) + 1
        first = reps[0]
        for pn, ids, pos in reps[1:]:
            if ids & first[1]:
                continue
            # walk the pin-to-pin line on the leg's layer, from the last pin before it that IS in the
            # first body (a bridged stretch is not the cut); the cut is past the LAST point the first
            # body covers -- a thermal-relief gap at a pad is not it -- and the cutter is the other
            # net's copper a step or a few beyond (the fill stops at its clearance edge)
            k = reps.index((pn, ids, pos))
            j = max(i for i in range(k) if reps[i][1] & first[1])
            path = [r[2] for r in reps[j:k + 1]]
            pts = []
            for a, b in zip(path, path[1:]):
                ax, ay, bx, by_ = _mm(a.x), _mm(a.y), _mm(b.x), _mm(b.y)
                n = max(1, int(((bx - ax) ** 2 + (by_ - ay) ** 2) ** 0.5 / STEP))
                pts += [(ax + (bx - ax) * s / n, ay + (by_ - ay) * s / n) for s in range(n + 1)]
            last = None
            for i_, (x, y) in enumerate(pts):
                if any(N.covers(c, L, _pt(x, y)) for c in first[1]):
                    last = i_
            where, by = None, None
            if last is None:
                where = (_mm(pos.x), _mm(pos.y))
                by = "nothing of %s's on %s along the leg from %s" % (net, layer, reps[j][0])
            else:
                where = pts[min(last + 1, len(pts) - 1)]
                for (x2, y2) in pts[last + 1:last + 1 + int(CUT_LOOK / STEP)]:
                    w = _what_at(board, net, L, _pt(x2, y2))
                    if w:
                        where, by = (x2, y2), w
                        break
                by = by or ("no copper within %.1f mm (the fill stops here: clearance, min width "
                            "or island removal)" % CUT_LOOK)
            sx, sy = _sheet(*where)
            bad.append("POUR CUT: %s leg %d (%s on %s) split by %s at (%.2f, %.2f) [board %.2f, %.2f] -- "
                       "%s is not in %s's copper body" % (
                           net, legn, "-".join(pins), layer, by, sx, sy, where[0], where[1], pn, first[0]))
            break
    return bad


if __name__ == "__main__":
    b = pcbnew.LoadBoard(sys.argv[1])
    src = json.load(open(sys.argv[2]))
    if len(sys.argv) > 3 and sys.argv[3] == "--fill":
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    lines = check(b, legs(src))
    print("\n".join(lines) if lines else "pour_gate: every pour leg's pins are in one body")
    sys.stdout.flush()
    os._exit(1 if lines else 0)
