"""Move parts on a finished board without routing it again, and measure how well that works.

    KiCad-python cadkit/pcbflow/eco.py move elec/out/board moves.json
    KiCad-python cadkit/pcbflow/eco.py check elec/out/board
    KiCad-python cadkit/pcbflow/eco.py trials elec/out/board 18

`move` edits the board in place. moves.json is {"R12": [x_mm, y_mm], ...} in KiCad's frame. It
takes up the moved parts' own copper within RIP mm of where they stood or now stand, and any
copper in the way of where they now stand; `finish.py --keep-route` then closes what is open
and runs every check. About a minute, against half an hour for a route. Then `check`: it exits
REFUSED if close_last could only re-close a net the long way (quality A23), and that move is put
back -- restore the board from before `move`.

`trials` does that to scratch copies, one random legal move of a small part each (0.5 to 1.5 mm,
courtyards clear), and counts how many come back clean, meaning no quality FAIL beyond what the
unmoved board shows. A move whose re-closure fails A23 is refused like one on matched copper,
and logged with the net and the lengths. The board named is not touched. It is the number to read for "does this
board survive a small change".

WHY IT EXISTS (output_panel R2, 2026-11-02). A full route of that board left 1 to 4 nets open,
different ones each run, whatever was held. Keeping g1's whole copper and routing again did not
work either: Freerouting spent 58 minutes optimising fixed copper and wrote nothing. Local
repair closed 11 of 18 random moves with no route at all, 7 of them clean.

⚠ WHAT IT WILL NOT DO. close_last knows nothing of pairs, so a move that takes up matched copper
fails skew or the via budget, whether the part is on that net or only landed on its track
(R47, C52 and C36 on output_panel were bystanders). `move` refuses those and exits REFUSED; they
need a person. So does a move whose re-closure is a detour (A23, `check`): optical's decaps
feed their supply through the pad in series (lead, 2026-11-05: that is good decoupling, keep it),
so moving one takes up the rail's link, and close_last found 38 mm round a 2.4 mm gap at every
width down its ladder -- the straight way is blocked by the moved part, not by the width. A supply keeps the widest width taken up from it, through close_widths, down
close_last's own ladder, so read the checks and not just the unconnected count. The moved position is on the board only: copy it into the generator's
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
import re
import shutil
import subprocess
import sys

import pcbnew

RIP = 3.0                   # mm, of the moved parts' own nets
CLEAR = 0.75                # mm from a new pad centre to any track's edge
EDGE = 0.2                  # mm from a new pad's OUTLINE to another net's track edge
REFUSED = 3                 # exit code: the move would disturb matched copper, or re-closed a detour
FINE = 0.6                  # mm: a part with pad centres closer than this is fine-pitch


def _seg(p, a, c):
    dx, dy = c[0] - a[0], c[1] - a[1]
    n = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n)) if n else 0.0
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _seg_box(a, c, box):
    """Distance from segment a-c to the axis-aligned box (x0, y0, x1, y1); 0 if they meet."""
    x0, y0, x1, y1 = box
    t0, t1, dx, dy = 0.0, 1.0, c[0] - a[0], c[1] - a[1]
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                break
        else:
            r = q / p
            if p < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
    else:
        if t0 <= t1:
            return 0.0                      # the segment crosses the box (Liang-Barsky)
    def pt(p):
        return math.hypot(max(x0 - p[0], 0.0, p[0] - x1), max(y0 - p[1], 0.0, p[1] - y1))
    return min(pt(a), pt(c), *(_seg(k, a, c) for k in ((x0, y0), (x0, y1), (x1, y0), (x1, y1))))


def _xy(v):
    return pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)


def _reach(t):
    """((start, end), half width) of a track or via, in mm."""
    via = t.GetClass() == "PCB_VIA"
    return ((_xy(t.GetStart()), _xy(t.GetEnd())),
            pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu) if via else t.GetWidth()) / 2.0)


def _matched(notes):
    """The nets a person has to re-lay: declared pairs and matched-length groups."""
    return {n for k in ("diff_pairs", "match") for g in notes.get(k, ()) for n in g.get("nets", ())}


def _escapes(board, moved, gone, clash):
    """The pieces of `gone` a fine-pitch part's pins escape by: from a pad of a part not moved
    whose pads stand closer than FINE, along the same net through shared ends, to a via, to
    copper that stays or to another fine pin of the net, touching no moved pad on the way
    and losing no piece to a clash with one: the shortest such path, nothing off it.

    ⚠ THESE WERE HALF OF OPTICAL'S MISSES (2026-11-03). A decoupling cap beside U6 (LQFP-176,
    0.5 mm) moved a millimetre; RIP took up every GND piece near it, U6's pin-to-via stubs
    with them, and close_last may not drop a via in a 0.5 mm pad field, so the pins went
    looking for a 74 mm path to a pour fragment and stayed open. The stub never needed to
    move: it does not touch the cap."""
    ends = lambda t: (_xy(t.GetStart()), _xy(t.GetEnd()))
    near = lambda u, v: abs(u[0] - v[0]) < 0.02 and abs(u[1] - v[1]) < 0.02
    fine = []
    for fp in board.GetFootprints():
        if fp.GetReference() in moved:
            continue
        xy = [_xy(q.GetPosition()) for q in fp.Pads()]
        if any(math.dist(a, c) < FINE for i, a in enumerate(xy) for c in xy[i + 1:]):
            fine += list(fp.Pads())
    mine = [q for fp in board.GetFootprints() if fp.GetReference() in moved for q in fp.Pads()]
    took = {t.m_Uuid.AsString() for t in gone}          # proxies are new on every GetTracks()
    stays = [_xy(e) for t in board.GetTracks() if t.m_Uuid.AsString() not in took
             for e in (t.GetStart(), t.GetEnd())]
    keep = set()
    # THE PATH, NOT THE PIECE. Breadth first from the pin, through pieces that touch no moved
    # pad and do not clash, to the nearest anchor -- a via, copper that stays, or ANOTHER fine
    # pin of the net -- and only that path is kept. Taking the whole connected piece lost
    # every escape that had a branch to the moved part on it (optical C129, 2026-11-05: U6's
    # 171-172 bridge meets the cap's old feed at a T between the pins; the feed clashed, the
    # bridge went with it, and the closure only overlapped pad 172 -- DRC read it joined,
    # quality's A1 did not). The walk does not pass through a pin: a pad is not a joint.
    at = lambda e: pcbnew.VECTOR2I(pcbnew.FromMM(e[0]), pcbnew.FromMM(e[1]))
    pinned = lambda e, net: any(p.GetNetname() == net and p.HitTest(at(e)) for p in fine)
    usable = [u for u in gone if id(u) not in clash and not any(
        m.HitTest(u.GetStart()) or m.HitTest(u.GetEnd()) for m in mine)]
    for q in fine:
        for t in usable:
            if t.GetClass() == "PCB_VIA" or t.GetNetname() != q.GetNetname()                     or not (q.HitTest(t.GetStart()) or q.HitTest(t.GetEnd())):
                continue
            net, back, front = t.GetNetname(), {id(t): None}, [t]
            while front:
                u = front.pop(0)
                path = [u]
                while back[id(path[-1])] is not None:
                    path.append(back[id(path[-1])])
                if len(path) > 8:
                    continue
                if u.GetClass() == "PCB_VIA" or any(near(e, f) for e in ends(u) for f in stays)                         or any(pinned(e, net) and not q.HitTest(at(e)) for e in ends(u)):
                    keep |= {id(c) for c in path}
                    break
                for v in usable:
                    if id(v) not in back and v.GetNetname() == net and any(
                            near(e, f) for e in ends(u) if not pinned(e, net) for f in ends(v)):
                        back[id(v)] = u
                        front.append(v)
    return keep


def move(stem, moves):
    """Apply {ref: (x, y)} to stem.kicad_pcb; returns how many track pieces were taken up."""
    path = stem + ".kicad_pcb"
    with open(stem + ".board.json", encoding="utf-8") as fh:
        notes = json.load(fh)
    matched = _matched(notes)
    board = pcbnew.LoadBoard(path)
    stood, stands, nets, boxes = [], [], set(), []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref not in moves:
            continue
        stood += [_xy(p.GetPosition()) for p in fp.Pads()]
        nets |= {p.GetNetname() for p in fp.Pads()}
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(moves[ref][0]), pcbnew.FromMM(moves[ref][1])))
        stands += [_xy(p.GetPosition()) for p in fp.Pads()]
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            boxes.append(((pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                           pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())),
                          p.GetNetname()))
    if not stands:
        raise SystemExit("none of %s on %s" % (sorted(moves), path))

    def _in_way(t, a, c, half):
        # near a new pad's centre, or near its OUTLINE for another net: a centre-only test
        # missed a +5V via 1.08 from a 1.0 x 1.45 pad's centre, over its edge (seed 29 C130)
        return (any(_seg(p, a, c) < half + CLEAR for p in stands)
                or any(_seg_box(a, c, b) < half + EDGE for b, n in boxes
                       if n != t.GetNetname()))
    gone = []
    for t in board.GetTracks():
        via = t.GetClass() == "PCB_VIA"
        a, c = _xy(t.GetStart()), _xy(t.GetEnd())
        half = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu) if via else t.GetWidth()) / 2.0
        if (t.GetNetname() in nets and min(_seg(p, a, c) for p in stood + stands) < RIP) \
                or _in_way(t, a, c, half):
            gone.append(t)
    clash = {id(t) for t in gone if _in_way(t, *_reach(t)[0], _reach(t)[1])}
    spare = _escapes(board, moves, gone, clash)
    # a spared escape of ANOTHER net that a moved pad now sits on is a clash nothing will
    # fix: close_last refuses a board that starts with a violation (optical seed 29, C130's
    # VBUS pad on a +5V via: 5 unconnected, 25 FAIL). Refused, like matched copper.
    sat = sorted({t.GetNetname() for t in gone
                  if id(t) in spare and id(t) in clash and t.GetNetname() not in nets})
    if sat:
        print("REFUSED: a moved pad would sit on spared copper of %s" % ", ".join(sat))
        raise SystemExit(REFUSED)
    gone = [t for t in gone if id(t) not in spare]
    hit = sorted({t.GetNetname() for t in gone} & matched)
    if hit:
        print("REFUSED: would take up matched copper on %s" % ", ".join(hit))
        raise SystemExit(REFUSED)
    # a pour's width is the pour's: a 2.6 mm GND strap closed wide only clashes with its neighbours
    poured = {(z["net"] if isinstance(z, dict) else z[0]) for z in notes.get("zones", ())}
    widths = notes.setdefault("close_widths", {})
    for t in gone:
        if t.GetClass() != "PCB_VIA" and t.GetNetname() not in poured:
            widths[t.GetNetname()] = max(widths.get(t.GetNetname(), 0.0), pcbnew.ToMM(t.GetWidth()))
        board.Remove(t)
    # a stale pour against a moved pad is a violation, and close_last will not start on one
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    with open(stem + ".board.json", "w", encoding="utf-8") as fh:
        json.dump(notes, fh, indent=1)
    return len(gone)


def detours(stem, floor=()):
    """A23's failures on the finished board at stem, as texts, less any net in `floor`."""
    try:
        with open(stem + ".quality.json", encoding="utf-8") as fh:
            res = json.load(fh).get("results", ())
    except (OSError, ValueError):
        return ["no %s.quality.json: run finish first" % os.path.basename(stem)]
    return [r["text"] for r in res
            if r.get("rule") == "A23" and r.get("status") == "FAIL" and r.get("subject") not in floor]


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


def _finish(copy, name, env):
    """Run finish --keep-route on `copy`; returns (result line, quality FAIL count)."""
    here = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run([sys.executable, os.path.join(here, "finish.py"), "--keep-route", copy],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    last = [ln for ln in r.stdout.splitlines() if ln.startswith(name + ": ")]
    if not last:
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [""]
        return "finish wrote no result (exit %d): %s" % (r.returncode, tail[0]), None
    fails = re.search(r"quality: (\d+) FAIL", last[-1])
    return last[-1][len(name) + 2:], int(fails.group(1)) if fails else None


def trials(stem, count):
    src, name = os.path.split(os.path.abspath(stem))
    base = src + "_eco"
    env = dict(os.environ)
    env.setdefault("PCBFLOW_PROJECT", os.path.dirname(src))
    clean = connected = refused = 0
    dst = os.path.join(base, "t0")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    line, floor = _finish(os.path.join(dst, name), name, env)
    long_way = {t.split()[1] for t in detours(os.path.join(dst, name))}
    shutil.rmtree(dst, ignore_errors=True)
    print(" 0 unmoved: %s" % line, flush=True)
    if floor is None:
        raise SystemExit("the unmoved board did not finish, so no trial can be read")
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
        if t.returncode == REFUSED:
            refused += 1
            print("%2d %-6s %.2f mm, %s" % (n, ref, far, t.stdout.strip()), flush=True)
            shutil.rmtree(dst, ignore_errors=True)
            continue
        taken = next((ln for ln in t.stdout.splitlines() if ln.startswith("took up")), "?")
        last, fails = _finish(copy, name, env)
        bad = detours(copy, long_way)
        if bad:
            refused += 1
            print("%2d %-6s %.2f mm, REFUSED: re-closed the long way: %s"
                  % (n, ref, far, "; ".join(bad)), flush=True)
            shutil.rmtree(dst, ignore_errors=True)
            continue
        link = " 0 unconnected, 0 violation" in " " + last
        ok = link and "verify" not in last and fails is not None and fails <= floor
        connected += link
        clean += ok
        print("%2d %-6s %.2f mm, %s: %s" % (n, ref, far, taken, last), flush=True)
        shutil.rmtree(dst, ignore_errors=True)
    print("%s: %d of %d moves refused; of the other %d, %d connected, %d of those clean of every "
          "check" % (name, refused, count, count - refused, connected, clean))


def main():
    if sys.argv[1:2] == ["check"] and len(sys.argv) == 3:
        bad = detours(sys.argv[2])
        for t in bad:
            print("REFUSED: re-closed the long way: %s" % t)
        raise SystemExit(REFUSED if bad else 0)
    if len(sys.argv) != 4 or sys.argv[1] not in ("move", "trials"):
        raise SystemExit(__doc__)
    if sys.argv[1] == "move":
        with open(sys.argv[3], encoding="utf-8") as fh:
            print("took up", move(sys.argv[2], json.load(fh)))
    else:
        trials(sys.argv[2], int(sys.argv[3]))


if __name__ == "__main__":
    main()
