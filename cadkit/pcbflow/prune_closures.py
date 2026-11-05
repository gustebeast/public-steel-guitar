"""Take up only the closures that broke a rule, and keep the rest.

    "C:/Program Files/KiCad/10.0/bin/python.exe" cadkit/pcbflow/prune_closures.py elec/out/optical

Reads <stem>.preclose.kicad_pcb (the board before close_last ran), <stem>.kicad_pcb (after
it) and <stem>.finish.drc.json (DRC of the after board). Every track or via that is new
since the before board and is named in a violation is taken up. Then the leftovers are
trimmed: a new piece goes if one of its ends touches nothing of its net (no pad, no other
piece), and a new via goes if fewer than two pieces reach it; repeat until nothing moves.
Growing the take along "joined" copper instead took too much (closures meet at pads and at
each other), so the rule is take the bad, then trim what dangles. Everything else close_last
laid stays. Prints how many pieces it took up; finish.py runs DRC again and keeps the
result only if it reads better.

WHY (optical, 2026-11-05). A decoupling cap beside U6 moved a millimetre and left three
+3V3D gaps. close_last closed all three, one of them with a 12 mm detour that broke
clearance, and finish judged the attempt as one lot: all three were put back and the board
stayed at three open. finish's retry then left the blamed NET alone, but the three gaps
were all on +3V3D, so the retry closed nothing either. The unit that broke the rule is the
closure, not the net.

Measured on the kept optical R2 board, the three decap moves that missed (with close_last's
zone-point fix): C109 4 open -> 0 open, 0 violations (took up 1 of 34 new pieces; quality
1 soft A1 width FAIL); C129 3 -> 0 open, 0 violations (took up 2 of 17); C128 0/0/0 FAIL. It
can only help: finish keeps the pruned board only if DRC reads strictly better.

⚠ C129 still reads 5 hard A1 FAILs ("no copper joins U8.2 to U6.6/15/23/36/172"). Not this
step: eco.py rips U6's own 171-172 pin-to-pin bridge (it meets C129's feed at a junction),
and the replacement's only joint to pad 172 is a 0.5 mm track overlapping the pad, which DRC
counts as connected and A1 does not. Fix belongs in eco's escape keep (a fine-pitch part's
pin-to-pin bridge stays), not here.
"""
from __future__ import annotations

import json
import re
import sys

import pcbnew


_SEG = re.compile(r'\(segment\s+\(start ([-\d.]+) ([-\d.]+)\)\s+\(end ([-\d.]+) ([-\d.]+)\)'
                  r'\s+\(width [-\d.]+\)\s+\(layer "([^"]+)"\)\s+\(net "([^"]*)"\)')
_VIA = re.compile(r'\(via\s+\(at ([-\d.]+) ([-\d.]+)\)[^()]*(?:\([^()]*\)\s*)*?\(net "([^"]*)"\)')


def _key(net, layer, *xy):
    return (net, layer) + tuple(round(float(v), 3) for v in xy)


def _old(path):
    """Every track and via of the before board, by net, layer and ends, read as text: a
    second LoadBoard in one process hands back a bare swig pointer, and uuids do not
    survive the steps between (unwick and repair_planes write the board again)."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    keys = set()
    for sx, sy, ex, ey, layer, net in _SEG.findall(text):
        keys.add(_key(net, layer, sx, sy, ex, ey))
        keys.add(_key(net, layer, ex, ey, sx, sy))
    for x, y, net in _VIA.findall(text):
        keys.add(_key(net, "via", x, y))
    return keys


def _key_of(t):
    mm = lambda v: (pcbnew.ToMM(v.x), pcbnew.ToMM(v.y))
    if t.GetClass() == "PCB_VIA":
        return _key(t.GetNetname(), "via", *mm(t.GetPosition()))
    return _key(t.GetNetname(), t.GetLayerName(), *(mm(t.GetStart()) + mm(t.GetEnd())))


def main(stem):
    old = _old(stem + ".preclose.kicad_pcb")
    with open(stem + ".finish.drc.json", encoding="utf-8") as fh:
        drc = json.load(fh)
    named = {i.get("uuid") for v in drc.get("violations", []) for i in v.get("items", [])}
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    new = [t for t in board.GetTracks() if _key_of(t) not in old]
    bad = [t for t in new if t.m_Uuid.AsString() in named]
    if not bad:
        print("prune_closures: no violation is on new copper")
        return 0
    # ⚠ TAKE UP THE BAD PIECES, THEN WHAT THEY LEAVE DANGLING -- not the whole closure
    # (optical C129, 2026-11-05). The three +3V3D closures there met track to track, not at
    # a pad, so a closure grown end to end was all three: 16 of 17 new pieces went for two
    # short ones that broke clearance. Now a new piece goes if DRC names it, or if one of its
    # ends then touches nothing of its net (no pad, no other piece); a new via goes if fewer
    # than two pieces still reach it. Repeated until nothing more comes loose.
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    tracks = list(board.GetTracks())
    tol = pcbnew.FromMM(0.01)
    def ends(t):
        if t.GetClass() == "PCB_VIA":
            return [t.GetPosition()]
        return [t.GetStart(), t.GetEnd()]
    def held(q, t, gone):
        net = t.GetNetname()
        if any(p.GetNetname() == net and p.HitTest(q) for p in pads):
            return True
        for v in tracks:
            if v is t or id(v) in gone or v.GetNetname() != net:
                continue
            if v.GetClass() == "PCB_VIA":
                if (v.GetPosition() - q).EuclideanNorm() < tol:
                    return True
            elif any((e - q).EuclideanNorm() < tol for e in ends(v)) or v.HitTest(q):
                return True
        return False
    gone = {id(t): t for t in bad}
    loose = True
    while loose:
        loose = False
        for t in new:
            if id(t) in gone:
                continue
            if t.GetClass() == "PCB_VIA":
                q = t.GetPosition()
                n = sum(1 for v in tracks if id(v) not in gone and v is not t
                        and v.GetClass() != "PCB_VIA" and v.GetNetname() == t.GetNetname()
                        and any((e - q).EuclideanNorm() < tol for e in ends(v)))
                drop = n < 2 and not any(p.GetNetname() == t.GetNetname() and p.HitTest(q)
                                         for p in pads)
            else:
                drop = not all(held(q, t, gone) for q in ends(t))
            if drop:
                gone[id(t)] = t
                loose = True
    nets = sorted({t.GetNetname() for t in gone.values()})
    for t in gone.values():
        board.Remove(t)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(stem + ".kicad_pcb", board)
    print("prune_closures: took up %d of %d new piece(s), on %s; kept %d"
          % (len(gone), len(new), ", ".join(nets), len(new) - len(gone)))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1]))
