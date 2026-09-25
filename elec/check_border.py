"""Count the ratlines that still reach north of the border.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/check_border.py elec/out/optical [y]

⚠ THIS IS THE GATE FOR THE NORTH HALF (user, 2026-09-24: "the goal for now is just to get
rid of the nets that extend above the border by connecting everything from the north to
the border"). The autorouter is to be given the SOUTH half only, so every net with pads in
the string array has to arrive at the border under its own steam. What the user reads in
KiCad is the ratsnest -- a thin line reaching up into the strings means that net is still
the router's problem up there -- so this counts the same thing, and a number here and the
picture there should agree.

Three kinds of ratline, and only one of them is work:

  NORTH   both ends north of the border: a net that is not joined up in the string array.
          THIS IS THE LIST TO EMPTY.
  CROSS   one end north, one south: the net's single handover to the router. Exactly one
          per crossing net is the FINISHED state, not a fault.
  SOUTH   both ends south: the router's half, not ours.

⚠ THE RATSNEST IS BETWEEN ISLANDS, NOT PADS. Two pads of one net with copper between them
draw no line however far apart they are, and that is the whole point of a spine: it does
not shorten anything, it removes the line. So islands are built first -- union-find over
pads, tracks and vias, by layer and by touch -- and the estimate is a minimum spanning
tree over THOSE, nearest pad to nearest pad, which is what KiCad draws.

⚠ GND IS EXCLUDED, AND NOT BECAUSE IT DOES NOT MATTER. It is poured on F.Cu, In1 and B.Cu,
and this reads tracks rather than zones, so every pad reaching the plane through the pour
counts as its own island -- 70 of them, all false. Anything that reads zones can put GND
back; until then a number for it would be worse than no number.
"""
from __future__ import annotations

import collections
import math
import sys

import wx

wx.DisableAsserts()
import pcbnew  # noqa: E402

# Just south of R10: the ballast resistors are the southernmost thing string 10 owns, so
# this is "as close to string 10 as we can fit" and no closer.
BORDER = -19.0
TOL = 1000          # nm of slop, the same the island report uses


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, c):
        a, c = self.find(a), self.find(c)
        if a != c:
            self.p[a] = c


def _seg_hit(g, pt):
    _, s, e, w = g
    dx, dy = e.x - s.x, e.y - s.y
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((pt.x - s.x) * dx + (pt.y - s.y) * dy) / l2))
    cx, cy = s.x + t * dx, s.y + t * dy
    return (cx - pt.x) ** 2 + (cy - pt.y) ** 2 <= (w / 2.0 + TOL) ** 2


def _ends(g):
    if g[0] == "seg":
        return [g[1], g[2]]
    if g[0] == "pt":
        return [g[1]]
    return [g[1].GetPosition()]


def _touch(gi, gj):
    for pt in _ends(gj):
        if gi[0] == "seg" and _seg_hit(gi, pt):
            return True
        if gi[0] == "pad" and gi[1].HitTest(pcbnew.VECTOR2I(int(pt.x), int(pt.y)), TOL):
            return True
        if gi[0] == "pt" and (gi[1].x - pt.x) ** 2 + (gi[1].y - pt.y) ** 2 <= TOL ** 2:
            return True
    for pt in _ends(gi):
        if gj[0] == "seg" and _seg_hit(gj, pt):
            return True
        if gj[0] == "pad" and gj[1].HitTest(pcbnew.VECTOR2I(int(pt.x), int(pt.y)), TOL):
            return True
    return False


def islands(board, cu):
    """net -> list of islands, each a list of (x, y, label) pads. Single-island nets are
    left out: they have no ratsnest at all, which is the state every net is aiming for."""
    lx = lambda p: p.x / 1e6 - 100.0
    ly = lambda p: 100.0 - p.y / 1e6
    items = collections.defaultdict(list)
    for fp in board.GetFootprints():
        for q in fp.Pads():
            n = q.GetNetname()
            if n:
                items[n].append(("pad", set(q.GetLayerSet().Seq()), ("pad", q),
                                 "%s.%s" % (fp.GetReference(), q.GetNumber())))
    for t in board.GetTracks():
        n = t.GetNetname()
        if not n:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            items[n].append(("via", set(cu), ("pt", t.GetStart()), ""))
        else:
            items[n].append(("trk", {t.GetLayer()},
                             ("seg", t.GetStart(), t.GetEnd(), t.GetWidth()), ""))

    out = {}
    for n, lst in items.items():
        uf = _UF()
        for i in range(len(lst)):
            uf.find(i)
        for i in range(len(lst)):
            _, li, gi, _ = lst[i]
            for j in range(i + 1, len(lst)):
                _, lj, gj, _ = lst[j]
                if (li & lj) and _touch(gi, gj):
                    uf.union(i, j)
        groups = collections.defaultdict(list)
        for i, (k, _l, g, lab) in enumerate(lst):
            if k == "pad":
                p = g[1].GetPosition()
                groups[uf.find(i)].append((lx(p), ly(p), lab))
        gs = [v for v in groups.values() if v]
        if len(gs) > 1:
            out[n] = gs
    return out


def ratlines(isls):
    """Prim's MST over islands, each edge the closest pad pair joining its two islands."""
    edges, reached, rest = [], [0], list(range(1, len(isls)))
    while rest:
        best = None
        for a in reached:
            for b in rest:
                for pa in isls[a]:
                    for pb in isls[b]:
                        d = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
                        if best is None or d < best[0]:
                            best = (d, a, b, pa, pb)
        edges.append(best)
        reached.append(best[2])
        rest.remove(best[2])
    return edges


def main(argv):
    path = argv[1] if len(argv) > 1 else "elec/out/optical"
    cut = float(argv[2]) if len(argv) > 2 else BORDER
    if not path.endswith(".kicad_pcb"):
        path += ".kicad_pcb"
    board = pcbnew.LoadBoard(path)
    cu = [l for l in board.GetEnabledLayers().Seq() if pcbnew.IsCopperLayer(l)]

    tally = collections.Counter()
    rows = []
    for net, isls in sorted(islands(board, cu).items()):
        if net == "GND":
            continue
        north, cross, worst = 0, 0, None
        for d, _a, _b, pa, pb in ratlines(isls):
            n_a, n_b = pa[1] > cut, pb[1] > cut
            kind = "NORTH" if (n_a and n_b) else ("SOUTH" if not (n_a or n_b) else "CROSS")
            tally[kind] += 1
            if kind == "NORTH":
                north += 1
                if worst is None or d > worst[0]:
                    worst = (d, pa, pb)
            elif kind == "CROSS":
                cross += 1
        if north:
            rows.append((north, net, cross, worst))

    print("border y = %.2f" % cut)
    for n, net, cross, w in sorted(rows, key=lambda r: (-r[0], r[1])):
        print("  %-14s %2d north  %d cross   longest %6.2f mm  %s -> %s"
              % (net, n, cross, w[0], w[1][2], w[2][2]))
    print("%d ratline(s) north of the border over %d net(s); %d crossing, %d south only"
          % (tally["NORTH"], len(rows), tally["CROSS"], tally["SOUTH"]))
    return 1 if tally["NORTH"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
