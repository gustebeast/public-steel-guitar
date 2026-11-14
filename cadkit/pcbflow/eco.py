"""Move parts on a finished board without routing it again, and measure how well that works.

    KiCad-python cadkit/pcbflow/eco.py move elec/out/board moves.json
    KiCad-python cadkit/pcbflow/eco.py check elec/out/board
    KiCad-python cadkit/pcbflow/eco.py trials elec/out/board 18

`move` edits the board in place. moves.json is {"R12": [x_mm, y_mm], ...} in KiCad's frame. It
takes up the moved parts' own local copper (out from each pad as far as a via or another pad)
within RIP mm of where they stood or now stand, and any
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

import _nowindow  # noqa: F401  (no console windows on Windows: _nowindow.py)
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys

import pcbnew

RIP = 3.0                   # mm, of the moved parts' own local copper (see _tree)
CLEAR = 0.75                # mm from a new pad centre to any track's edge
EDGE = 0.2                  # mm from a new pad's OUTLINE to another net's track edge
HOLE = 0.25                 # mm hole to hole, a carried via against the net's own (JLC 0.2 + margin)
REFUSED = 3                 # exit code: the move would disturb matched copper, or re-closed a detour
FINE = 0.6                  # mm: a part with pad centres closer than this is fine-pitch


def _seg(p, a, c):
    dx, dy = c[0] - a[0], c[1] - a[1]
    n = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n)) if n else 0.0
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _seg_seg(a, c, p, q):
    """Distance between segments a-c and p-q; 0 if they cross."""
    def side(u, v, w):
        return (v[0] - u[0]) * (w[1] - u[1]) - (v[1] - u[1]) * (w[0] - u[0])
    if side(a, c, p) * side(a, c, q) < 0 and side(p, q, a) * side(p, q, c) < 0:
        return 0.0
    return min(_seg(p, a, c), _seg(q, a, c), _seg(a, p, q), _seg(c, p, q))


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
    # a stub ending on a pad's EDGE (optical U7.9 to its exposed pad, 0.05 mm short of the
    # outline, 2026-11-07) ends on that pad: tested with a tenth of a millimetre's reach
    pinned = lambda e, net: any(p.GetNetname() == net and p.HitTest(at(e), pcbnew.FromMM(0.1))
                                for p in fine)
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


def _own_escapes(fp, tracks):
    """(stub, via) pairs that are one pad's private way down: a single track from a pad of
    `fp` to a via of the same net that no other track touches (the via's other side is a
    pour). Other copper may meet the pad; it is the part's ordinary routing and goes the
    ordinary way."""
    near = lambda u, v: abs(u[0] - v[0]) < 0.005 and abs(u[1] - v[1]) < 0.005
    vias = [t for t in tracks if t.GetClass() == "PCB_VIA"]
    segs = [t for t in tracks if t.GetClass() != "PCB_VIA"]
    out = []
    for p in fp.Pads():
        net = p.GetNetname()
        for t in segs:
            if t.GetNetname() != net:
                continue
            for e, o in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
                if not p.HitTest(e) or p.HitTest(o):
                    continue
                v = [u for u in vias if u.GetNetname() == net and near(_xy(u.GetPosition()), _xy(o))]
                if len(v) != 1:
                    continue
                others = [u for u in segs if u is not t and u.GetNetname() == net and any(
                    near(_xy(x), _xy(o)) for x in (u.GetStart(), u.GetEnd()))]
                if not others:
                    out.append((t, v[0]))
    return out


def _tree(fp, tracks):
    """uuids of the track pieces a part's pads reach through track joints alone: out from
    each pad, along shared ends, stopping at a via and at any other part's pad. The part's
    own local copper, which goes with it when it moves; what lies beyond a via stays."""
    near = lambda u, v: abs(u[0] - v[0]) < 0.005 and abs(u[1] - v[1]) < 0.005
    vias = [t for t in tracks if t.GetClass() == "PCB_VIA"]
    segs = [t for t in tracks if t.GetClass() != "PCB_VIA"]
    others = [q for f in fp.GetBoard().GetFootprints() if f is not fp for q in f.Pads()]
    seen, front = set(), []
    for p in fp.Pads():
        for t in segs:
            if t.GetNetname() == p.GetNetname() and t.m_Uuid.AsString() not in seen \
                    and (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd())):
                seen.add(t.m_Uuid.AsString())
                front.append(t)
    while front:
        t = front.pop()
        net = t.GetNetname()
        for e in (t.GetStart(), t.GetEnd()):
            x = _xy(e)
            if any(v.GetNetname() == net and near(_xy(v.GetPosition()), x) for v in vias):
                continue
            if any(q.GetNetname() == net and q.HitTest(e) for q in others):
                continue
            for u in segs:
                if u.m_Uuid.AsString() not in seen and u.GetNetname() == net and (
                        near(_xy(u.GetStart()), x) or near(_xy(u.GetEnd()), x)):
                    seen.add(u.m_Uuid.AsString())
                    front.append(u)
    return seen


def _detour(board, net, layer, keep, p, q, step=0.05, margin=3.0):
    """A short path p -> q on `layer` keeping `keep` mm (half width + clearance) from every
    other net's copper, or None: A* on a grid over the gap's box plus `margin`, then pulled
    straight wherever a segment clears. None too if it is not A23-short."""
    mm = pcbnew.ToMM
    x0, y0 = min(p[0], q[0]) - margin, min(p[1], q[1]) - margin
    x1, y1 = max(p[0], q[0]) + margin, max(p[1], q[1]) + margin
    win = lambda a, c, r: (max(a[0], c[0]) + r > x0 and min(a[0], c[0]) - r < x1
                           and max(a[1], c[1]) + r > y0 and min(a[1], c[1]) - r < y1)
    segs, boxes = [], []
    for t in board.GetTracks():
        if t.GetNetname() == net:
            continue
        if t.GetClass() == "PCB_VIA":
            o, r = _xy(t.GetPosition()), mm(t.GetWidth(pcbnew.F_Cu)) / 2.0
            if win(o, o, r + keep):
                segs.append((o, o, r))
        elif t.GetLayer() == layer:
            a, c, r = _xy(t.GetStart()), _xy(t.GetEnd()), mm(t.GetWidth()) / 2.0
            if win(a, c, r + keep):
                segs.append((a, c, r))
    for f in board.GetFootprints():
        for d in f.Pads():
            if d.GetNetname() != net and d.IsOnLayer(layer):
                bb = d.GetBoundingBox()
                b = (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))
                if win((b[0], b[1]), (b[2], b[3]), keep):
                    boxes.append(b)

    def clear(a, c):
        return (all(_seg_seg(a, c, u, v) >= r + keep for u, v, r in segs)
                and all(_seg_box(a, c, b) >= keep for b in boxes))

    if clear(p, q):
        return [p, q]
    nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    cell = lambda i, j: (x0 + i * step, y0 + j * step)
    ok = {}

    def free(i, j):
        if (i, j) not in ok:
            e = cell(i, j)
            ok[(i, j)] = 0 <= i < nx and 0 <= j < ny and clear(e, e)
        return ok[(i, j)]

    s = (round((p[0] - x0) / step), round((p[1] - y0) / step))
    g = (round((q[0] - x0) / step), round((q[1] - y0) / step))
    ok[s] = ok[g] = True
    import heapq
    h = lambda n: math.dist(n, g)
    todo, came, cost = [(h(s), s)], {s: None}, {s: 0.0}
    while todo:
        _, n = heapq.heappop(todo)
        if n == g:
            break
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                m = (n[0] + di, n[1] + dj)
                if (di or dj) and free(*m):
                    c = cost[n] + math.hypot(di, dj)
                    if c < cost.get(m, 1e18):
                        cost[m], came[m] = c, n
                        heapq.heappush(todo, (c + h(m), m))
    if g not in came:
        return None
    pts, n = [], g
    while n is not None:
        pts.append(cell(*n))
        n = came[n]
    pts = [q] + pts[1:-1] + [p]
    pts.reverse()
    out, k = [p], 0
    while k < len(pts) - 1:
        j = next(j for j in range(len(pts) - 1, k, -1) if j == k + 1 or clear(pts[k], pts[j]))
        out.append(pts[j])
        k = j
    if any(not clear(a, c) for a, c in zip(out, out[1:])):
        return None
    ln, gap = sum(math.dist(a, c) for a, c in zip(out, out[1:])), math.dist(p, q)
    return out if ln <= max(1.5 * gap, gap + 10.0) else None


def move(stem, moves):
    """Apply {ref: (x, y)} to stem.kicad_pcb; returns how many track pieces were taken up."""
    path = stem + ".kicad_pcb"
    with open(stem + ".board.json", encoding="utf-8") as fh:
        notes = json.load(fh)
    matched = _matched(notes)
    board = pcbnew.LoadBoard(path)
    stood, stands, nets, boxes = [], [], set(), []
    onl = []                     # the copper layers of each pad in `stands`
    stn = []                     # ...and its net
    local = set()                # uuids of the moved parts' local copper (see _tree)
    pairs = []                   # (net, old centre, new centre) of every moved pad
    tracks = list(board.GetTracks())
    drags = []                   # (stub, via, dx, dy, ref): a pad's own escape, carried with it
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref not in moves:
            continue
        stood += [_xy(p.GetPosition()) for p in fp.Pads()]
        nets |= {p.GetNetname() for p in fp.Pads()}
        was = _xy(fp.GetPosition())
        drags += [(t, v, moves[ref][0] - was[0], moves[ref][1] - was[1], ref)
                  for t, v in _own_escapes(fp, tracks)]
        local |= _tree(fp, tracks)
        olds = [(p.GetNetname(), _xy(p.GetPosition())) for p in fp.Pads()]
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(moves[ref][0]), pcbnew.FromMM(moves[ref][1])))
        pairs += [(n, o, _xy(p.GetPosition())) for (n, o), p in zip(olds, fp.Pads())]
        for p in fp.Pads():
            cu = {board.GetLayerName(l) for l in p.GetLayerSet().CuStack()}
            stands.append(_xy(p.GetPosition()))
            onl.append(cu)
            stn.append(p.GetNetname())
            bb = p.GetBoundingBox()
            boxes.append(((pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                           pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())),
                          p.GetNetname(), cu))
    if not stands:
        raise SystemExit("none of %s on %s" % (sorted(moves), path))

    # ⚠ A PART'S OWN VIA GOES WITH IT (optical +3V3D, 2026-11-06). Every decap on the rail
    # has a stub to a via of its own into the rail's pour; ripped with the part's other copper,
    # close_last had to invent the via again and instead joined the pad 19 mm round by track
    # (quality A23). A stub and via that serve that one pad and nothing else are moved by the
    # part's own offset instead -- unless they would land on another net's pad or via, which
    # nothing could clear, and then they are taken up like the rest.
    carried = set()
    fixed = [(p, p.GetBoundingBox()) for f in board.GetFootprints() for p in f.Pads()]
    # the vias that travel are tested where they will stand, not where they stood: a part's two
    # escapes (its rail and its ground) move together and never come closer than they were
    going = {id(v): (dx, dy) for _t, v, dx, dy, _r in drags}
    at = lambda u: (_xy(u.GetPosition())[0] + going.get(id(u), (0.0, 0.0))[0],
                    _xy(u.GetPosition())[1] + going.get(id(u), (0.0, 0.0))[1])
    box = lambda bb: (pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                      pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))
    for t, v, dx, dy, ref in drags:
        net, (a0, c0) = t.GetNetname(), [_xy(e) for e in (t.GetStart(), t.GetEnd())]
        a0, c0 = (a0[0] + dx, a0[1] + dy), (c0[0] + dx, c0[1] + dy)
        vx0, vy0 = _xy(v.GetPosition())
        vx0, vy0, vr = vx0 + dx, vy0 + dy, pcbnew.ToMM(v.GetWidth(pcbnew.F_Cu)) / 2.0
        pin = c0 if math.dist(a0, (vx0, vy0)) < 0.005 else a0     # the stub's end on the pad

        def _fits(a, c, vx, vy, rigid):
            # the part's own other pads travel too: stub and land keep the spacing they were
            # laid at (optical C121, 2026-11-07: its GND stub runs 0.2 mm off its +3V3D land,
            # under EDGE plus the box test's corner, and the via was refused and taken up).
            # Only when carried straight: swung round, the stub meets its own lands anew.
            if any(p.GetNetname() != net and not (rigid and p.GetParentFootprint().GetReference() == ref)
                   and (_seg_box((vx, vy), (vx, vy), box(bb)) < vr + EDGE
                        or _seg_box(a, c, box(bb)) < pcbnew.ToMM(t.GetWidth()) / 2.0 + EDGE)
                   for p, bb in fixed):
                return False
            # never into an SMD land, its own net's included: solder wicks down the barrel (A14)
            if any(p.GetDrillSize().x == 0 and _seg_box((vx, vy), (vx, vy), box(bb)) < vr
                   for p, bb in fixed):
                return False
            # another net's via at copper clearance; the net's own at the drill's hole-to-hole
            # rule (quality A12), since two holes too close is a drill fault whatever the nets.
            # Holding the net's own to the copper rule refused a cap's ground via 0.7 mm from
            # its rail via and left the ground land an island (optical C106, 2026-11-07)
            def _near(u):
                d = math.dist(at(u), (vx, vy))
                if u.GetNetname() == net:
                    return d < (pcbnew.ToMM(u.GetDrillValue()) + pcbnew.ToMM(v.GetDrillValue())) / 2.0 + HOLE
                return d < vr + pcbnew.ToMM(u.GetWidth(pcbnew.F_Cu)) / 2.0 + EDGE
            if any(u.GetClass() == "PCB_VIA" and u is not v and _near(u) for u in tracks):
                return False
            # nor across another net's track: the via is on every layer and would take that
            # track up, and a signal laid back round costs more than the cap's via found again
            # (optical C118, 2026-11-07: its +3V3D via landed on I2C2_SCL's B.Cu run, which
            # came back 92 mm). The moved parts' own nets are theirs to lose (C121's +3V3D
            # stub refused its own GND via's drag, and U7.1 lost its ground, 2026-11-07)
            def _cuts(u):
                if u.GetClass() == "PCB_VIA" or u.GetNetname() == net or u.GetNetname() in nets:
                    return False
                e = (_xy(u.GetStart()), _xy(u.GetEnd()))
                w = pcbnew.ToMM(u.GetWidth()) / 2.0
                return (_seg((vx, vy), *e) < vr + w + EDGE
                        or (u.GetLayer() == t.GetLayer()
                            and _seg_seg(a, c, *e) < pcbnew.ToMM(t.GetWidth()) / 2.0 + w + EDGE))
            return not any(_cuts(u) for u in tracks)

        # ⚠ STRAIGHT ACROSS FIRST, THEN SWUNG ROUND THE PIN (optical C117, 2026-11-07): carried
        # straight, its GND via came 0.71 mm from a +3V3A via (0.8 wanted), was taken up, and
        # close_last found no room for another, leaving the land an island. The same stub
        # turned 45 or 90 degrees about its pad end usually clears.
        for deg in (0, 45, -45, 90, -90, 135, -135, 180):
            co, si = math.cos(math.radians(deg)), math.sin(math.radians(deg))
            rx, ry = vx0 - pin[0], vy0 - pin[1]
            vx, vy = pin[0] + co * rx - si * ry, pin[1] + si * rx + co * ry
            a, c = (pin, (vx, vy)) if pin == a0 else ((vx, vy), pin)
            if _fits(a, c, vx, vy, deg == 0):
                break
        else:
            continue
        t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
        t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(c[0]), pcbnew.FromMM(c[1])))
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(vx), pcbnew.FromMM(vy)))
        going[id(v)] = (0.0, 0.0)        # it stands where it is now; `at` adds nothing
        carried |= {t.m_Uuid.AsString(), v.m_Uuid.AsString()}
        boxes.append(((vx - vr, vy - vr, vx + vr, vy + vr), net, None))
        boxes.append(((min(a[0], c[0]), min(a[1], c[1]), max(a[0], c[0]), max(a[1], c[1])), net,
                      {t.GetLayerName()}))

    def _in_way(t, a, c, half):
        # near a new pad's centre, or near its OUTLINE for another net: a centre-only test
        # missed a +5V via 1.08 from a 1.0 x 1.45 pad's centre, over its edge (seed 29 C130)
        # ...and only on a layer the track is on: a 0402 moved over a B.Cu track took 5.5 mm of
        # I2C2_SCL up with it and close_last laid it back 92 mm round (optical C118, 2026-11-07).
        # A via is on every layer; so is a dragged via (None).
        on = None if t.GetClass() == "PCB_VIA" else {t.GetLayerName()}
        meet = lambda cu: on is None or cu is None or bool(on & cu)
        # A track of the pad's own net is a connection, not in the way (seed 71 C108: the +3V3D
        # trunk beside its new +3V3D pad went, and close_last re-laid it 19.3 mm round 1.6);
        # a via of its own net still is, since under the land it would be a via in the pad.
        return (any(_seg(p, a, c) < half + CLEAR for p, cu, n in zip(stands, onl, stn)
                    if meet(cu) and (on is None or n != t.GetNetname()))
                or any(_seg_box(a, c, b) < half + EDGE for b, n, cu in boxes
                       if n != t.GetNetname() and meet(cu)))
    cut = {}
    def _spans(t):
        # the pieces of a track that stay clear of the moved pads (by 0.3 mm more), and
        # whether its start is the end cut away
        uid = t.m_Uuid.AsString()
        if uid not in cut:
            a, c, half = _xy(t.GetStart()), _xy(t.GetEnd()), pcbnew.ToMM(t.GetWidth()) / 2.0
            n = max(2, int(math.dist(a, c) / 0.05))
            pts = [(a[0] + (c[0] - a[0]) * k / n, a[1] + (c[1] - a[1]) * k / n) for k in range(n + 1)]
            bad = [_in_way(t, e, e, half + 0.3) for e in pts]
            spans, k = [], 0
            while k <= n:
                if bad[k]:
                    k += 1
                    continue
                j = k
                while j < n and not bad[j + 1]:
                    j += 1
                if math.dist(pts[k], pts[j]) > 0.3:
                    spans.append((pts[k], pts[j]))
                k = j + 1
            cut[uid] = (spans, bad[0])
        return cut[uid]
    def _stretch_clear(t, seg, half):
        net, layer = t.GetNetname(), t.GetLayer()
        for u in board.GetTracks():
            if u is t or u.GetNetname() == net:
                continue
            if u.GetClass() == "PCB_VIA":
                if _seg(_xy(u.GetPosition()), *seg) < half + pcbnew.ToMM(u.GetWidth(pcbnew.F_Cu)) / 2.0 + EDGE:
                    return False
            elif u.GetLayer() == layer:
                # another net's run the move cuts is judged by what of it stays (C132: +3V3A's
                # stretch to the cap was refused by the +3V3D trunk the cap cuts through)
                ua, uc, uh = _xy(u.GetStart()), _xy(u.GetEnd()), pcbnew.ToMM(u.GetWidth()) / 2.0
                segs = [(ua, uc)]
                if u.GetNetname() not in nets and math.dist(ua, uc) > 1.0 and _in_way(u, ua, uc, uh):
                    segs = _spans(u)[0]
                if any(_seg_seg(*seg, p, q) < half + uh + EDGE for p, q in segs):
                    return False
        return not any(q.GetNetname() != net and q.IsOnLayer(layer) and _seg_box(*seg, box(bb)) < half + EDGE
                       for q, bb in fixed)

    gone = []
    stretch = {}                 # uuid -> (which end, new point): tracks that follow their pad
    trim = {}                    # uuid -> (keep the end, new start): runs cut at RIP
    split = {}                   # uuid -> [(start, end)]: another net's run, less what is in the way
    blocked = set()              # id: taken up because it is in the way, not only because it is near
    lone = []                    # (track, spans, clipped end): split at one end only, pending
    for t in board.GetTracks():
        if t.m_Uuid.AsString() in carried:
            continue
        via = t.GetClass() == "PCB_VIA"
        a, c = _xy(t.GetStart()), _xy(t.GetEnd())
        half = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu) if via else t.GetWidth()) / 2.0
        # ⚠ THE PART'S OWN COPPER, NOT ITS NETS' (optical R50, 2026-11-07). Everything of the
        # moved parts' nets within RIP went, so a pull-up's via went with the In2 run beyond it
        # and close_last laid I2C2_SCL back 20 mm round a 4 mm gap. Now: the copper its pads
        # reach without passing a via or another pad (_tree) within RIP of the part, and any of
        # its nets' vias it now sits on. The via and what lies beyond it stay, for close_last
        # to join to.
        mine = t.GetNetname() in nets and (
            (t.m_Uuid.AsString() in local and min(_seg(p, a, c) for p in stood + stands) < RIP)
            or (via and min(_seg(p, a, c) for p in stands) < half + CLEAR))
        way = _in_way(t, a, c, half)
        # ⚠ A TRACK FROM A MOVED PAD'S CENTRE FOLLOWS THE PAD (optical R42, 2026-11-07): cut at
        # RIP, its MID trunk left a 3 mm gap that close_last closed 19 mm round by B.Cu. The end
        # on the pad's old centre goes to its new one, if the stretched track clears every other
        # net; the connection is never broken, and close_last has nothing to do there.
        if mine and not via:
            hit = [(i, new) for i, e in enumerate((a, c)) for n, old, new in pairs
                   if n == t.GetNetname() and math.dist(e, old) < 0.01]
            if len(hit) == 1:
                # straight to the far end if that clears; else a dogleg: the track is cut at the
                # nearest point P (0.3 to 3 mm out) that a new piece from the pad's new centre
                # reaches clear, and that piece is added (R42's straight stretch passed PD10B.2)
                i, new = hit[0]
                o, f = (a, c) if i == 0 else (c, a)
                ln = math.dist(o, f)
                cuts = [ln] + [d for d in (0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1, 2.4, 2.7, 3.0) if d < ln - 0.1]
                for d in cuts:
                    p = (o[0] + (f[0] - o[0]) * d / ln, o[1] + (f[1] - o[1]) * d / ln)
                    if _stretch_clear(t, (new, p), half):
                        stretch[t.m_Uuid.AsString()] = (i, new, p)
                        break
                else:
                    p = None
                if p is not None:
                    continue
        # ⚠ A LONG RUN IS CUT AT RIP, NOT TAKEN WHOLE (optical R42, 2026-11-07): its MID pad's
        # trunk is one 18 mm segment, so all of it went and close_last laid 13.2 mm round a
        # 1.3 mm gap. The part beyond RIP stays and close_last joins the pad to its cut end.
        far = max(a, c, key=lambda e: min(math.dist(e, p) for p in stood + stands))
        if mine and not via and min(math.dist(far, p) for p in stood + stands) > RIP:
            near = c if far == a else a
            for k in range(1, 400):
                f = k / 400.0
                e = (near[0] + (far[0] - near[0]) * f, near[1] + (far[1] - near[1]) * f)
                if min(math.dist(e, p) for p in stood + stands) >= RIP:
                    break
            if math.dist(e, far) > 0.3 and not _in_way(t, e, far, half):
                trim[t.m_Uuid.AsString()] = (far is c, e)
                continue
        # ⚠ ANOTHER NET'S RUN IS CUT ONLY WHERE IT IS IN THE WAY (optical C132, 2026-11-07).
        # The cap came down across the +3V3D trunk; its 5.5 mm segment went whole with the next,
        # a 7.3 mm gap that close_last closed 20.7 mm round. The pieces clear of the moved pads
        # (by 0.3 mm more) stay, and close_last joins a gap the width of the part.
        if way and not mine and not via and math.dist(a, c) > 1.0:
            spans, bad0 = _spans(t)
            # only a cut with copper kept on BOTH sides: a clipped end is a stub with nothing to
            # rejoin (C118's GND run to a via that went; close_last's +3V3D closure then hit it).
            # A run clipped at one end counts if the next piece of it is clipped too (C132's
            # trunk: two segments meeting under the cap) -- settled after this loop.
            if len(spans) >= 2:
                split[t.m_Uuid.AsString()] = spans
                continue
            if spans:
                lone.append((t, spans, a if bad0 else c))
                continue
        if mine or way:
            gone.append(t)
            if way:
                blocked.add(id(t))
    for t, spans, e in lone:
        if any(u is not t and u.GetNetname() == t.GetNetname() and u.GetLayer() == t.GetLayer()
               and math.dist(e, f) < 0.005 for u, _, f in lone):
            split[t.m_Uuid.AsString()] = spans
        else:
            gone.append(t)
            blocked.add(id(t))
    # ⚠ WHAT A STRETCHED TRACK LEADS TO STAYS (optical C106, 2026-11-07). The +3V3D rail ran
    # through C106's pad; the piece on the pad followed it, but the 0.15 mm piece beyond was
    # local and inside RIP and went, so the stretched leg joined nothing and the trunk was cut
    # (U8.2 to U6.6 open). Copper chained to a stretched track, not in the way, is kept.
    ends = lambda t: (_xy(t.GetStart()), _xy(t.GetEnd()))
    reach = [e for t in board.GetTracks() if t.m_Uuid.AsString() in stretch
             for k, e in enumerate(ends(t)) if k != stretch[t.m_Uuid.AsString()][0]]
    grew = True
    while grew:
        grew = False
        for t in list(gone):
            if id(t) in blocked or t.GetClass() == "PCB_VIA":
                continue
            if any(math.dist(e, r) < 0.005 for e in ends(t) for r in reach):
                gone.remove(t)
                reach += ends(t)
                grew = True
    clash = {id(t) for t in gone if _in_way(t, *_reach(t)[0], _reach(t)[1])}
    spare = _escapes(board, moves, gone, clash)
    # ⚠ A NEIGHBOUR'S OWN VIA STAYS (optical C140, 2026-11-07). RIP took U9.2's GND stub and
    # via 2.8 mm from the moved cap; the F.Cu GND there is an island, so the pin went open.
    # A pad's private stub+via (see _own_escapes) on a part not moved stays unless it clashes.
    mine = [q for fp in board.GetFootprints() if fp.GetReference() in moves for q in fp.Pads()]
    every = list(board.GetTracks())
    byuuid = {t.m_Uuid.AsString(): t for t in gone}
    for fp in board.GetFootprints():
        if fp.GetReference() in moves:
            continue
        for t, v in _own_escapes(fp, every):
            t, v = byuuid.get(t.m_Uuid.AsString()), byuuid.get(v.m_Uuid.AsString())
            if t is None or v is None or id(t) in clash or id(v) in clash:
                continue
            if any(m.HitTest(t.GetStart()) or m.HitTest(t.GetEnd()) for m in mine):
                continue
            spare |= {id(t), id(v)}
    # a spared escape of ANOTHER net that a moved pad now sits on is a clash nothing will
    # fix: close_last refuses a board that starts with a violation (optical seed 29, C130's
    # VBUS pad on a +5V via: 5 unconnected, 25 FAIL). Refused, like matched copper.
    sat = sorted({t.GetNetname() for t in gone
                  if id(t) in spare and id(t) in clash and t.GetNetname() not in nets})
    if sat:
        print("REFUSED: a moved pad would sit on spared copper of %s" % ", ".join(sat))
        raise SystemExit(REFUSED)
    gone = [t for t in gone if id(t) not in spare]
    # ⚠ A VIA A MOVED PAD LANDS ON SLIDES ASIDE, ITS TRACKS' ENDS WITH IT (optical R42,
    # 2026-11-07). Its MID_BUF pad came down on the MID via beside it; the via went, the In2
    # run beyond it was left an island, and close_last re-joined both pieces 16.7 and 20.3 mm
    # round. A via in the way with copper that stays on its other layers is moved to the
    # nearest clear spot within 1.6 mm, and the ends of that copper are moved to meet it.
    # ⚠ BY UUID: GetTracks() hands back new proxies every call, so id() of a piece in `gone`
    # never matched one from `allt` and every taken-up piece counted as held (seed 71 R33)
    taken = {t.m_Uuid.AsString() for t in gone}
    near = lambda u, w: abs(u[0] - w[0]) < 0.005 and abs(u[1] - w[1]) < 0.005
    allt = list(board.GetTracks())
    for v in [t for t in gone if t.GetClass() == "PCB_VIA" and id(t) in clash]:
        o, vr, net = _xy(v.GetPosition()), pcbnew.ToMM(v.GetWidth(pcbnew.F_Cu)) / 2.0, v.GetNetname()
        held = [t for t in allt if t.GetClass() != "PCB_VIA" and t.m_Uuid.AsString() not in taken
                and t.GetNetname() == net and (near(_xy(t.GetStart()), o) or near(_xy(t.GetEnd()), o))]
        if not held:
            continue
        others = [t for t in allt if t.m_Uuid.AsString() not in taken and t.GetNetname() != net]

        def _clear(p):
            if _in_way(v, p, p, vr):
                return False
            for u in others:
                if u.GetClass() == "PCB_VIA":
                    if math.dist(_xy(u.GetPosition()), p) < vr + pcbnew.ToMM(u.GetWidth(pcbnew.F_Cu)) / 2.0 + EDGE:
                        return False
                elif _seg(p, _xy(u.GetStart()), _xy(u.GetEnd())) < vr + pcbnew.ToMM(u.GetWidth()) / 2.0 + EDGE:
                    return False
            if any(u.GetClass() == "PCB_VIA" and u.m_Uuid.AsString() != v.m_Uuid.AsString()
                   and u.m_Uuid.AsString() not in taken and u.GetNetname() == net
                   and math.dist(_xy(u.GetPosition()), p) < pcbnew.ToMM(u.GetDrillValue()) + HOLE
                   for u in allt):
                return False
            if any(q.GetNetname() != net and _seg_box(p, p, box(bb)) < vr + EDGE for q, bb in fixed):
                return False
            # nor into an SMD land of its own net (optical seed 71 C124: C110's and C111's GND
            # vias slid onto their own GND pads, quality A14 -- solder wicks down the barrel)
            if any(q.GetDrillSize().x == 0 and _seg_box(p, p, box(bb)) < vr for q, bb in fixed):
                return False
            for t in held:
                far = _xy(t.GetEnd()) if near(_xy(t.GetStart()), o) else _xy(t.GetStart())
                if t.m_Uuid.AsString() in stretch:
                    # it follows its pad: judged from where it will start, not the old centre
                    # (seed 71 R33: USB_CC2's stub, from the old centre, met the new GND land)
                    _, new_, p_ = stretch[t.m_Uuid.AsString()]
                    far = new_ if near(p_, o) else p_
                hw = pcbnew.ToMM(t.GetWidth()) / 2.0
                for u in others:
                    if u.GetClass() == "PCB_VIA":
                        if _seg(_xy(u.GetPosition()), far, p) < hw + pcbnew.ToMM(u.GetWidth(pcbnew.F_Cu)) / 2.0 + EDGE:
                            return False
                    elif u.GetLayer() == t.GetLayer() and _seg_seg(far, p, _xy(u.GetStart()), _xy(u.GetEnd())) \
                            < hw + pcbnew.ToMM(u.GetWidth()) / 2.0 + EDGE:
                        return False
                if any(q.GetNetname() != net and q.IsOnLayer(t.GetLayer()) and _seg_box(far, p, box(bb)) < hw + EDGE
                       for q, bb in fixed):
                    return False
            return True
        ring = [(o[0] + r * math.cos(k * math.pi / 8), o[1] + r * math.sin(k * math.pi / 8))
                for r in (0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6) for k in range(16)]
        # ⚠ A SLID VIA THAT WAS THE MOVED PAD'S OWN GETS A LEG BACK TO IT (optical R42,
        # 2026-11-07). The MID via slid clear of the MID_BUF pad, but its stub to R42.2 had
        # gone, so the In2 run beyond it joined nothing and close_last re-laid MID 19 mm round
        # a 2.3 mm gap. A spot from which a straight leg reaches the pad's new centre clear,
        # on the stub's layer, wins over a nearer one; the leg is laid with the via.
        stub = next((t for t in gone if t.GetClass() != "PCB_VIA" and t.GetNetname() == net
                     and (near(_xy(t.GetStart()), o) or near(_xy(t.GetEnd()), o))), None)
        tos = [new for n, old, new in pairs if n == net] if stub is not None else []
        if stub is not None:
            # ...or back to the pad its stub came from, when that pad stayed put (seed 71 C124:
            # C111's GND via slid clear and its stub to C111.2 had gone with the rip)
            far = _xy(stub.GetEnd()) if near(_xy(stub.GetStart()), o) else _xy(stub.GetStart())
            fv = pcbnew.VECTOR2I(pcbnew.FromMM(far[0]), pcbnew.FromMM(far[1]))
            if any(q.GetNetname() == net and q.HitTest(fv) for q, bb in fixed):
                tos.append(far)
        spot, leg_to = None, None
        for p in ring:
            if not _clear(p):
                continue
            to = next((w for w in sorted(tos, key=lambda w: math.dist(w, p))
                       if _stretch_clear(stub, (w, p), pcbnew.ToMM(stub.GetWidth()) / 2.0)), None)
            if to is not None:
                spot, leg_to = p, to
                break
            if spot is None:
                spot = p
            if not tos:
                break
        if spot is None:
            continue
        at_spot = pcbnew.VECTOR2I(pcbnew.FromMM(spot[0]), pcbnew.FromMM(spot[1]))
        if leg_to is not None:
            leg = pcbnew.PCB_TRACK(board)
            leg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(leg_to[0]), pcbnew.FromMM(leg_to[1])))
            leg.SetEnd(at_spot)
            leg.SetWidth(stub.GetWidth())
            leg.SetLayer(stub.GetLayer())
            leg.SetNet(stub.GetNet())
            board.Add(leg)
        for t in held:
            (t.SetStart if near(_xy(t.GetStart()), o) else t.SetEnd)(at_spot)
        v.SetPosition(at_spot)
        gone = [t for t in gone if t is not v]
    hit = sorted({t.GetNetname() for t in gone} & matched)
    if hit:
        print("REFUSED: would take up matched copper on %s" % ", ".join(hit))
        raise SystemExit(REFUSED)
    # Another net's run of short pieces that went whole because it was in the way (optical
    # C129: four SAI_SD4 pieces under the cap, none long enough to split) is a gap too, when
    # its two free ends still meet copper of its own that stays; laid round below.
    chain_gaps = []
    eq = lambda u, w: abs(u[0] - w[0]) < 0.005 and abs(u[1] - w[1]) < 0.005
    went = {t.m_Uuid.AsString() for t in gone}
    pool = [t for t in gone if id(t) in blocked and t.GetClass() != "PCB_VIA"
            and t.GetNetname() not in nets and not t.GetNetname().upper().endswith("GND")]
    while pool:
        comp, grow = [pool.pop()], True
        while grow:
            grow = False
            for u in list(pool):
                if any(eq(e, f) for t in comp for e in (_xy(t.GetStart()), _xy(t.GetEnd()))
                       for f in (_xy(u.GetStart()), _xy(u.GetEnd()))) and u.GetNetname() == comp[0].GetNetname():
                    comp.append(u)
                    pool.remove(u)
                    grow = True
        net, layer = comp[0].GetNetname(), comp[0].GetLayer()
        if any(t.GetLayer() != layer for t in comp):
            continue
        ends = [e for t in comp for e in (_xy(t.GetStart()), _xy(t.GetEnd()))]
        free = [e for e in ends if sum(eq(e, f) for f in ends) == 1]
        if any(v.GetClass() == "PCB_VIA" and v.GetNetname() == net
               and any(eq(_xy(v.GetPosition()), e) for e in ends) for v in gone):
            continue
        def held(e):
            pe = pcbnew.VECTOR2I(pcbnew.FromMM(e[0]), pcbnew.FromMM(e[1]))
            return (any(u.GetNetname() == net and u.m_Uuid.AsString() not in went
                        and (eq(_xy(u.GetStart()), e) or eq(_xy(u.GetEnd()), e)
                             or (u.GetClass() == "PCB_VIA" and eq(_xy(u.GetPosition()), e)))
                        for u in allt)
                    or any(d.GetNetname() == net and d.IsOnLayer(layer) and d.HitTest(pe)
                           for f in board.GetFootprints() for d in f.Pads()))
        tied = [e for e in free if held(e)]
        if len(tied) == 2:
            chain_gaps.append((comp[0].GetNet(), layer, comp[0].GetWidth(), tied[0], tied[1]))
    # a pour's width is the pour's: a 2.6 mm GND strap closed wide only clashes with its neighbours
    poured ={(z["net"] if isinstance(z, dict) else z[0]) for z in notes.get("zones", ())}
    widths = notes.setdefault("close_widths", {})
    for t in gone:
        if t.GetClass() != "PCB_VIA" and t.GetNetname() not in poured:
            widths[t.GetNetname()] = max(widths.get(t.GetNetname(), 0.0), pcbnew.ToMM(t.GetWidth()))
        board.Remove(t)
    legs = []
    gaps = list(chain_gaps)      # (net, layer, width, end, end): a run cut under a moved part
    ones = [(t, sp[0], e) for t, sp, e in lone if t.m_Uuid.AsString() in split]
    for k, (t, (s0, e0), e) in enumerate(ones):
        for u, (s1, e1), f in ones[k + 1:]:
            if u.GetNetname() == t.GetNetname() and math.dist(e, f) < 0.005:
                p = min((s0, e0), key=lambda w: math.dist(w, e))
                q = min((s1, e1), key=lambda w: math.dist(w, f))
                gaps.append((t.GetNet(), t.GetLayer(), t.GetWidth(), p, q))
    for t in board.GetTracks():
        if t.m_Uuid.AsString() in stretch:
            i, new, p = stretch[t.m_Uuid.AsString()]
            vp = pcbnew.VECTOR2I(pcbnew.FromMM(p[0]), pcbnew.FromMM(p[1]))
            vn = pcbnew.VECTOR2I(pcbnew.FromMM(new[0]), pcbnew.FromMM(new[1]))
            if math.dist(p, _xy(t.GetEnd() if i == 0 else t.GetStart())) < 0.005:
                (t.SetStart if i == 0 else t.SetEnd)(vn)          # straight: the whole track
            else:
                (t.SetStart if i == 0 else t.SetEnd)(vp)          # dogleg: cut at P...
                leg = pcbnew.PCB_TRACK(board)                     # ...and a piece from the pad
                leg.SetStart(vn)
                leg.SetEnd(vp)
                leg.SetWidth(t.GetWidth())
                leg.SetLayer(t.GetLayer())
                leg.SetNet(t.GetNet())
                legs.append(leg)
        if t.m_Uuid.AsString() in trim:
            keep_end, e = trim[t.m_Uuid.AsString()]
            (t.SetStart if keep_end else t.SetEnd)(pcbnew.VECTOR2I(pcbnew.FromMM(e[0]), pcbnew.FromMM(e[1])))
        if t.m_Uuid.AsString() in split:
            sp = split[t.m_Uuid.AsString()]
            gaps += [(t.GetNet(), t.GetLayer(), t.GetWidth(), sp[k][1], sp[k + 1][0]) for k in range(len(sp) - 1)]
            (s0, e0), *rest = sp
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(s0[0]), pcbnew.FromMM(s0[1])))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(e0[0]), pcbnew.FromMM(e0[1])))
            for s1, e1 in rest:
                piece = pcbnew.PCB_TRACK(board)
                piece.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(s1[0]), pcbnew.FromMM(s1[1])))
                piece.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(e1[0]), pcbnew.FromMM(e1[1])))
                piece.SetWidth(t.GetWidth())
                piece.SetLayer(t.GetLayer())
                piece.SetNet(t.GetNet())
                legs.append(piece)
    for leg in legs:
        board.Add(leg)
    # ⚠ A RUN CUT UNDER A MOVED PART IS LAID ROUND IT HERE, NOT LEFT TO close_last (optical
    # C132, 2026-11-07). The cap came down across the +3V3D trunk and the NRST run; south of
    # it is room for one track, close_last gave it to NRST, and +3V3D went 15 mm round by
    # In2 and B.Cu for a 4.4 mm gap. Widest first (then longest), each gap gets a short path found on a
    # 0.05 mm grid through the copper as it now stands, if one is A23-short (1.5x the gap, or
    # 10 mm over); a signal left over closes with a via hop inside its own allowance.
    clr = pcbnew.ToMM(board.GetDesignSettings().m_MinClearance) + 0.02
    for net, layer, w, p, q in sorted(gaps, key=lambda g: (-g[2], -math.dist(g[3], g[4]))):
        way = _detour(board, net.GetNetname(), layer, pcbnew.ToMM(w) / 2.0 + clr, p, q)
        if way is None:
            continue
        for a, c in zip(way, way[1:]):
            piece = pcbnew.PCB_TRACK(board)
            piece.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
            piece.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(c[0]), pcbnew.FromMM(c[1])))
            piece.SetWidth(w)
            piece.SetLayer(layer)
            piece.SetNet(net)
            board.Add(piece)
        print("laid %s round a moved part: %.1f mm for a %.1f mm gap"
              % (net.GetNetname(), sum(math.dist(a, c) for a, c in zip(way, way[1:])), math.dist(p, q)))
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
