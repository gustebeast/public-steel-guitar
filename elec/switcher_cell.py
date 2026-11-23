"""What every designed switcher cell shares (lm5122_cell, tps552892_cell, ...).

A cell module defines ANCHOR, SRC, CELL ({member: (dx, dy, rot)} in the anchor's rot-0 pad
frame), RULES (hard rules among the members), OUTER (hard rules tying outside parts to the
cell), REACH ({outside part: (dx, dy, rot)}, one proven legal seat each) and GAP_MM. This
module turns those into intent rules and checks them against the geometry alone.

A part with no courtyard (a NetTie) is left out of the overlap check: it is drawn to sit on
another part's pad (TPS552892's NT205 / NT206 on R313's pads, the Kelvin taps).
"""
from __future__ import annotations

import itertools
import os
import json
import sys


def intent_rules(cell):
    """The intent rules a cell adds: the group (placed whole) and its hard rules."""
    name = os.path.splitext(os.path.basename(cell.__file__))[0]
    out = [dict(kind="group", anchor=cell.ANCHOR, members={k: list(v) for k, v in cell.CELL.items()}, hard=True,
                src=cell.SRC, why="the %s as one designed cell (elec/%s.py)" % (cell.WHAT, name))]
    out += [dict(r, hard=True, src=cell.SRC) for r in cell.RULES + cell.OUTER]
    return out


def check(cell, parts, pi):
    """[problem] for the cell alone at the origin, plus REACH: courtyard overlaps, broken hard rules."""
    pl = {cell.ANCHOR: [0.0, 0.0, 0.0]}
    pl.update({k: list(v) for k, v in cell.CELL.items()})
    pl.update({k: list(v) for k, v in cell.REACH.items()})
    P = pi.Placed(parts, pl)
    bad = []
    solid = [r for r in pl if parts[r].get("crtyd")]
    for a, b in itertools.combinations(solid, 2):
        d = pi._poly_dist(P.crtyd(a), P.crtyd(b))
        if d < cell.GAP_MM:
            bad.append("courtyards %s / %s %.2f mm apart (< %.2f)" % (a, b, d, cell.GAP_MM))
    for r in cell.RULES + cell.OUTER:
        for s, ref, det in pi.check(dict(r, hard=True), P, {}):
            if s < -0.05:
                bad.append("%s breaks its %s %s <= %g by %.2f (%s)" % (ref, r["kind"], r.get("pin") or r.get("target"),
                                                                     r["max_mm"], -s, det))
    return bad


def main(cell, argv):
    """py -3.12 elec/<cell>.py <output_board.parts.json> <cadkit/pcbflow dir>"""
    sys.path.insert(0, argv[1])
    import place_intent as _pi
    name = os.path.splitext(os.path.basename(cell.__file__))[0]
    problems = check(cell, json.load(open(argv[0]))["parts"], _pi)
    print("\n".join(problems) if problems else "%s: PASS (%d members, %d hard rules, %d outside parts seated)"
          % (name, len(cell.CELL), len(cell.RULES) + len(cell.OUTER), len(cell.REACH)))
    return 1 if problems else 0
