"""Where should ONE part go? Every legal site on the board, scored.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/sitesearch.py elec/out/lever_sensor U2

⚠ WRITTEN BECAUSE THIS BOARD KEEPS BEING PLACED BY EYE AND KEEPS BEING WRONG. orient.py
already makes the same argument for ROTATION -- "a part at the wrong angle does not look
wrong ... and one number would have said so" -- and position is the other half of it. The
note beside lever_sensor's SWD pads says they went where "the only four 2.0 mm sites this
board has left" were, which was true of a 21.4 mm outline and is not true of the 34 mm
one; nothing re-derived it when the board grew. This does the deriving.

⚠ IT RANKS SITES, IT DOES NOT PROVE ONE ROUTES. Same caution pinsearch.py carries: the
score is straight-line distance from this part's pads to the other pads on its nets, and
straight-line metrics have been refuted on these boards before. What it CAN do honestly
is rule sites out -- a position whose courtyard overlaps another part or leaves the board
is not a candidate at all -- and rank what is left so the routing runs are spent on the
few that are plausible instead of on guesses.

Distance is measured to the NEAREST pad on each net rather than to all of them, because a
net is a tree and a part only has to reach it once.
"""
import math
import os
import sys

import pcbnew

MARGIN_MM = 1.0          # part-to-board-edge, the figure can_tee's outline note uses
STEP_MM = 0.5


def _rects(board, skip):
    out = []
    for fp in board.GetFootprints():
        if fp.GetReference() == skip:
            continue
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        out.append((bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
    return out


def _pad_offsets(fp):
    """Pad positions relative to the footprint origin, UNROTATED, with their nets."""
    o, rot = fp.GetPosition(), math.radians(fp.GetOrientationDegrees())
    out = []
    for pad in fp.Pads():
        p = pad.GetPosition()
        dx, dy = p.x - o.x, p.y - o.y
        # undo the footprint's own rotation so a candidate angle can be applied cleanly
        c, s = math.cos(-rot), math.sin(-rot)
        out.append((dx * c + dy * s, -dx * s + dy * c, pad.GetNetname()))
    return out


def _targets(board, ref):
    """For every net this part is on: the other pads on it, as (x, y)."""
    out = {}
    for fp in board.GetFootprints():
        if fp.GetReference() == ref:
            continue
        for pad in fp.Pads():
            n = pad.GetNetname()
            if not n:
                continue
            p = pad.GetPosition()
            out.setdefault(n, []).append((p.x, p.y))
    return out


def search(stem, ref, top=12, skip_nets=("GND", "+3V3", "+24V", "PWR_GND")):
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    fp = {f.GetReference(): f for f in board.GetFootprints()}[ref]
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    hw, hh = bb.GetWidth() / 2.0, bb.GetHeight() / 2.0
    others = _rects(board, ref)
    offs = _pad_offsets(fp)
    tgt = _targets(board, ref)
    # ⚠ THE POWER NETS ARE EXCLUDED FROM THE SCORE ON PURPOSE. They are poured planes
    # with pads everywhere, so every site scores about the same on them and they only
    # add noise to the comparison the signals are trying to make.
    live = [(dx, dy, n) for dx, dy, n in offs if n and n not in skip_nets and n in tgt]

    ebb = board.GetBoardEdgesBoundingBox()
    m = pcbnew.FromMM(MARGIN_MM)
    x0, x1 = ebb.GetLeft() + m, ebb.GetRight() - m
    y0, y1 = ebb.GetTop() + m, ebb.GetBottom() - m
    step = pcbnew.FromMM(STEP_MM)

    best = []
    for rot in (0.0, 90.0, 180.0, 270.0):
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        rw, rh = (hw, hh) if rot in (0.0, 180.0) else (hh, hw)
        x = x0 + rw
        while x <= x1 - rw:
            y = y0 + rh
            while y <= y1 - rh:
                l, t, r, b = x - rw, y - rh, x + rw, y + rh
                if not any(l < orr and ol < r and t < ob and ot < b
                           for ol, ot, orr, ob in others):
                    d = 0.0
                    for dx, dy, n in live:
                        px = x + dx * c - dy * s
                        py = y + dx * s + dy * c
                        d += min(math.hypot(px - tx, py - ty) for tx, ty in tgt[n])
                    best.append((d, pcbnew.ToMM(x) - 100.0, 100.0 - pcbnew.ToMM(y), rot))
                y += step
            x += step
    best.sort()
    return best, len(live)


def main(argv):
    if len(argv) < 3:
        raise SystemExit("usage: sitesearch.py <stem> <REF>")
    stem, ref = os.path.abspath(argv[1]), argv[2]
    best, nlive = search(stem, ref)
    print("%s: %d legal site(s), scored on %d signal pad(s)" % (ref, len(best), nlive))
    if not best:
        return 1
    for d, x, y, rot in best[:12]:
        print("   %8.2f mm   (%7.2f, %7.2f) rot %3.0f" % (pcbnew.ToMM(int(d)), x, y, rot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
