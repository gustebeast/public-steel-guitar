"""Take up only the closures that broke a rule, and keep the rest.

    "C:/Program Files/KiCad/10.0/bin/python.exe" cadkit/pcbflow/prune_closures.py elec/out/optical

Reads <stem>.preclose.kicad_pcb (the board before close_last ran), <stem>.kicad_pcb (after
it) and <stem>.finish.drc.json (DRC of the after board). Every track or via that is new
since the before board and is named in a violation is taken up, together with the new
copper joined to it end to end on the same net: that whole run is one closure, and half
of one is a dangling stub. Everything else close_last laid stays. Prints how many pieces
it took up; finish.py runs DRC again and keeps the result only if it reads better.

WHY (optical, 2026-11-05). A decoupling cap beside U6 moved a millimetre and left three
+3V3D gaps. close_last closed all three, one of them with a 12 mm detour that broke
clearance, and finish judged the attempt as one lot: all three were put back and the board
stayed at three open. finish's retry then left the blamed NET alone, but the three gaps
were all on +3V3D, so the retry closed nothing either. The unit that broke the rule is the
closure, not the net.

Measured on the kept optical R2 board, the three decap moves that missed: C109 4 open -> 2
(25 of 32 new pieces kept); C129 still 3; C128 unchanged at 2 (no violation to prune: its
misses were GND finding no path, fixed in close_last since). It can only help: finish keeps
the pruned board only if DRC reads strictly better.

⚠ C129 IS NOT A SHARED VIA (corrected 2026-11-05; an earlier note here and commit 64fd20a's
message said it was). Its violating closures are the SHORT ones, into U6.171 (0.5 mm pitch):
DRC finds them too close to pads 170 and 173, which have no net. Those pads are in the
search's obstacle list, so the gap is in how close_last's closure meets a fine-pitch pin
(margin, end snapping or the final approach); not yet found. Taking those closures up is
right, and leaves the pin open.
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
    # grow each bad piece into its whole closure: new copper, same net, sharing an end that
    # is not on a pad. A closure ends at a pad, and the closures of one supply often start
    # at the same one (the moved cap's): joined through it, all three went as one.
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    def ends(t):
        if t.GetClass() == "PCB_VIA":
            return [t.GetPosition()]
        return [t.GetStart(), t.GetEnd()]
    def free(q, net):
        return not any(p.GetNetname() == net and p.HitTest(q) for p in pads)
    gone, front = {id(t): t for t in bad}, list(bad)
    while front:
        u = front.pop()
        joints = [q for q in ends(u) if free(q, u.GetNetname())]
        for v in new:
            if id(v) in gone or v.GetNetname() != u.GetNetname():
                continue
            if any((q - e).EuclideanNorm() < pcbnew.FromMM(0.01) or
                   (v.GetClass() != "PCB_VIA" and v.HitTest(q))
                   for q in joints for e in ends(v)):
                gone[id(v)] = v
                front.append(v)
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
