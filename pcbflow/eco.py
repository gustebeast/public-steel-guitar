"""Move parts on a finished board without routing it again, and measure how well that works.

    KiCad-python cadkit/pcbflow/eco.py move elec/out/board moves.json
    KiCad-python cadkit/pcbflow/eco.py trials elec/out/board 18

`move` edits the board in place. moves.json is {"R12": [x_mm, y_mm], ...} in KiCad's frame. It
takes up the moved parts' own copper within RIP mm of where they stood or now stand, and any
copper in the way of where they now stand; `finish.py --keep-route` then closes what is open
and runs every check. About a minute, against half an hour for a route.

`trials` does that to scratch copies, one random legal move of a small part each (0.5 to 1.5 mm,
courtyards clear), and counts how many come back clean. The board named is not touched. It is
the number to read for "does this board survive a small change".

WHY IT EXISTS (output_panel R2, 2026-11-02). A full route of that board left 1 to 4 nets open,
different ones each run, whatever was held. Keeping g1's whole copper and routing again did not
work either: Freerouting spent 58 minutes optimising fixed copper and wrote nothing. Local
repair closed 11 of 18 random moves with no route at all, 7 of them clean.

⚠ WHAT IT CANNOT DO. close_last lays signal-width track and knows nothing of pairs, so a move
that touches a matched pair fails skew or the via budget, and one on a supply net fails the
current check. Those need a person, and the checks say so; read them, not just the
unconnected count. The moved position is on the board only: copy it into the generator's
placements, or the next regenerate puts the part back.

⚠ THE BOARD HAS TO START AT 0 UNEXPECTED VIOLATIONS: close_last refuses a board with any. A
trial's copy lies outside the project, so PCBFLOW_PROJECT has to name it or the project's
pcb_declared.py is not found and declared overlaps count against it. `trials` sets that for a
board in the usual <project>/out; a board anywhere else needs it set by hand.
"""
from __future__ import annotations

import json
import math
import os
import random
import shutil
import subprocess
import sys

import pcbnew

RIP = 3.0                   # mm, of the moved parts' own nets
CLEAR = 0.75                # mm from a new pad centre to any track's edge


def _seg(p, a, c):
    dx, dy = c[0] - a[0], c[1] - a[1]
    n = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n)) if n else 0.0
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _xy(v):
    return pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)


def move(stem, moves):
    """Apply {ref: (x, y)} to stem.kicad_pcb; returns how many track pieces were taken up."""
    path = stem + ".kicad_pcb"
    board = pcbnew.LoadBoard(path)
    stood, stands, nets = [], [], set()
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref not in moves:
            continue
        stood += [_xy(p.GetPosition()) for p in fp.Pads()]
        nets |= {p.GetNetname() for p in fp.Pads()}
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(moves[ref][0]), pcbnew.FromMM(moves[ref][1])))
        stands += [_xy(p.GetPosition()) for p in fp.Pads()]
    if not stands:
        raise SystemExit("none of %s on %s" % (sorted(moves), path))
    gone = []
    for t in board.GetTracks():
        via = t.GetClass() == "PCB_VIA"
        a, c = _xy(t.GetStart()), _xy(t.GetEnd())
        half = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu) if via else t.GetWidth()) / 2.0
        if (t.GetNetname() in nets and min(_seg(p, a, c) for p in stood + stands) < RIP) \
                or any(_seg(p, a, c) < half + CLEAR for p in stands):
            gone.append(t)
    for t in gone:
        board.Remove(t)
    # a stale pour against a moved pad is a violation, and close_last will not start on one
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    return len(gone)


def legal_moves(stem, count, seed=11):
    """`count` random single moves of small parts that keep courtyards and the edge clear."""
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    rng = random.Random(seed)
    edge = board.GetBoardEdgesBoundingBox()
    x_lo, y_lo = _xy(edge.GetOrigin())
    x_hi, y_hi = x_lo + pcbnew.ToMM(edge.GetWidth()), y_lo + pcbnew.ToMM(edge.GetHeight())
    yards = {}
    for fp in board.GetFootprints():
        box = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if box.GetWidth():
            x, y = _xy(box.GetOrigin())
            yards[fp.GetReference()] = (x, x + pcbnew.ToMM(box.GetWidth()),
                                        y, y + pcbnew.ToMM(box.GetHeight()), fp)
    small = sorted(r for r, b in yards.items()
                   if r[0] in "CRDL" and r[1:].isdigit() and b[1] - b[0] < 3.5)
    out = []
    while len(out) < count:
        ref = rng.choice(small)
        x0, x1, y0, y1, fp = yards[ref]
        turn, far = rng.uniform(0.0, 2 * math.pi), rng.uniform(0.5, 1.5)
        dx, dy = far * math.cos(turn), far * math.sin(turn)
        q = (x0 + dx - 0.1, x1 + dx + 0.1, y0 + dy - 0.1, y1 + dy + 0.1)
        if q[0] < x_lo + 0.5 or q[1] > x_hi - 0.5 or q[2] < y_lo + 0.5 or q[3] > y_hi - 0.5:
            continue
        if any(k != ref and q[0] < b[1] and q[1] > b[0] and q[2] < b[3] and q[3] > b[2]
               for k, b in yards.items()):
            continue
        x, y = _xy(fp.GetPosition())
        out.append((ref, far, x + dx, y + dy))
    return out


def trials(stem, count):
    here = os.path.dirname(os.path.abspath(__file__))
    src, name = os.path.split(os.path.abspath(stem))
    base = src + "_eco"
    env = dict(os.environ)
    env.setdefault("PCBFLOW_PROJECT", os.path.dirname(src))
    clean = connected = 0
    for n, (ref, far, x, y) in enumerate(legal_moves(stem, count), 1):
        dst = os.path.join(base, "t%d" % n)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst)
        copy = os.path.join(dst, name)
        with open(os.path.join(dst, "moves.json"), "w", encoding="utf-8") as fh:
            json.dump({ref: (x, y)}, fh)
        # its own process: a second LoadBoard in this one hands back a bare swig pointer
        t = subprocess.run([sys.executable, os.path.abspath(__file__), "move", copy,
                            os.path.join(dst, "moves.json")], capture_output=True, text=True)
        taken = next((ln for ln in t.stdout.splitlines() if ln.startswith("took up")), "?")
        r = subprocess.run([sys.executable, os.path.join(here, "finish.py"), "--keep-route", copy],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=env)
        last = [ln for ln in r.stdout.splitlines() if ln.startswith(name + ": ")]
        last = last[-1] if last else "finish wrote no result (exit %d)" % r.returncode
        link = " 0 unconnected, 0 violation" in last
        ok = link and "verify" not in last and "quality: 0 FAIL" in last
        connected += link
        clean += ok
        print("%2d %-6s %.2f mm, %s: %s" % (n, ref, far, taken, last[len(name) + 2:]), flush=True)
        shutil.rmtree(dst, ignore_errors=True)
    print("%s: %d of %d moves connected, %d of those clean of every check"
          % (name, connected, count, clean))


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ("move", "trials"):
        raise SystemExit(__doc__)
    if sys.argv[1] == "move":
        with open(sys.argv[3], encoding="utf-8") as fh:
            print("took up", move(sys.argv[2], json.load(fh)))
    else:
        trials(sys.argv[2], int(sys.argv[3]))


if __name__ == "__main__":
    main()
