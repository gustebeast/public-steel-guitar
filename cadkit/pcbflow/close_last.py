"""Close the nets a finished route left open, by maze search on the ROUTED board.

    KiCad-python cadkit/pcbflow/close_last.py elec/out/output_panel

finish.py runs this itself, after the last routing round, on a board with nothing wrong
but unconnected items; it keeps the result only if DRC then reads strictly better.

WHY IT EXISTS (output_panel, 2026-10-02). With the USB-C sockets the board sat exactly at
the router's limit: seven consecutive routes each left ONE or TWO nets open, and never the
same ones -- POT_SDI, then HUB_DN2_DP, then NRST and PWR_GND, then OSC_IN and POT_CS, then
NRST again. Every per-net medicine (a pin escape, more passes, another round) closed the
net it was aimed at and opened a neighbour. That is not a placement fault to find; it is
the last half-percent of a search the router does not finish.

⚠ AND THE ANSWER CANNOT BE WRITTEN DOWN. repair_search.py says why at the top: a repair is
pinned to the routing it was searched against, and BOARD_NOTES["repair_tracks"] has gone
stale that way more than once. So this does not emit coordinates for anyone to paste. It
searches AGAIN, every run, against whatever the router just produced, and nothing it finds
outlives the board it was found on.

It reuses repair_search's obstacle model and maze3d rather than growing a fourth.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys

import pcbnew
import wx                                       # noqa: E402  (KiCad's python ships it)
wx.DisableAsserts()                             # NO MODAL DIALOGS IN A BUILD STEP -- see route.py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import repair_search as RS   # noqa: E402

LAYERS = ("F.Cu", "In2.Cu", "B.Cu")
WIDTH = 0.2                   # the board's own signal width: a QFN pad row is on 0.4
REACH = 6.0                   # mm of margin round the two ends' bounding box


def _ends(item):
    m = re.search(r"\[([^\]]+)\]", item["description"])
    lay = re.search(r"on ((?:F|B|In\d)\.Cu)", item["description"])
    return (m.group(1) if m else None, lay.group(1) if lay else "F.Cu",
            (item["pos"]["x"], item["pos"]["y"]), item["description"].startswith("Track"))


def _free_end(board, net, layer, pos, target):
    """The end of the dangling copper at `pos` that is NEAREST `target`, as (layer, point).

    ⚠ DRC REPORTS A TRACK BY ITS START POINT, NOT BY ITS LOOSE END (pi_cap, 2026-10-04).
    An unconnected "Track [UI_RES_N] on F.Cu" came back positioned at the END OF THE
    HEADER'S EDGE LANE -- the far end of a 4.7 mm escape stub whose free end stood in open
    board -- so the search started in a lane with 0.15 mm to its neighbour, left it with a
    0.05 mm jog at this file's 0.2 mm width, and the one clearance error that made was
    enough for finish.py to throw away a board with nothing else wrong.
    So: walk the copper joined to that point (same net, joined end to end on one layer) and
    start from whichever of its ends is closest to where the net has to go.
    """
    eps = pcbnew.FromMM(0.005)
    lid = board.GetLayerID(layer)
    segs = [t for t in board.GetTracks()
            if t.GetClass() != "PCB_VIA" and t.GetNetname() == net and t.GetLayer() == lid]
    key = lambda p: (round(p.x / eps), round(p.y / eps))
    here = (round(pcbnew.FromMM(pos[0]) / eps), round(pcbnew.FromMM(pos[1]) / eps))
    seen, edge, used = {here}, [here], set()
    while edge:
        k = edge.pop()
        for i, t in enumerate(segs):
            if i in used:
                continue
            a, b = key(t.GetStart()), key(t.GetEnd())
            if k in (a, b):
                used.add(i)
                for q in (a, b):
                    if q not in seen:
                        seen.add(q)
                        edge.append(q)
    if not used:
        return layer, pos
    count = {}
    for i in used:
        for q in (key(segs[i].GetStart()), key(segs[i].GetEnd())):
            count[q] = count.get(q, 0) + 1
    tips = [q for q, n in count.items() if n == 1] or list(count)
    best = min(tips, key=lambda q: (pcbnew.ToMM(int(q[0] * eps)) - target[0]) ** 2
               + (pcbnew.ToMM(int(q[1] * eps)) - target[1]) ** 2)
    return layer, (pcbnew.ToMM(int(best[0] * eps)), pcbnew.ToMM(int(best[1] * eps)))


def _via_starts(board, net, pos, layers):
    """Every (layer, point) the net's copper joined to `pos` offers through a via of its own.

    ⚠ AN END THAT ALREADY HAS ITS ESCAPE VIA WAS SEARCHED FROM THE WRONG LAYER
    (motor_ctrl PG_5V, 2026-10-04). Both ends of that net were declared escapes: a QFN pin
    with a 0.15 mm track to a via 1 mm away, and a regulator pin walled in on the front by
    its own thermal pad and the input copper, with a via beside it. The search started on
    F.Cu at each -- the one layer with no way out, which is why the vias were drawn -- and
    said "no path" for two vias with open board between them on both other layers.
    So: walk the net's copper from `pos` across layers, and offer each via it reaches as a
    start on every routable layer.
    """
    eps = pcbnew.FromMM(0.005)
    key = lambda p: (round(p.x / eps), round(p.y / eps))
    segs = [t for t in board.GetTracks()
            if t.GetClass() != "PCB_VIA" and t.GetNetname() == net]
    vias = {key(t.GetPosition()): t for t in board.GetTracks()
            if t.GetClass() == "PCB_VIA" and t.GetNetname() == net}
    here = (round(pcbnew.FromMM(pos[0]) / eps), round(pcbnew.FromMM(pos[1]) / eps))
    seen, edge, used = {here}, [here], set()
    while edge:
        k = edge.pop()
        for i, t in enumerate(segs):
            if i in used:
                continue
            a, b = key(t.GetStart()), key(t.GetEnd())
            if k in (a, b):
                used.add(i)
                for q in (a, b):
                    if q not in seen:
                        seen.add(q)
                        edge.append(q)
    out = []
    for k in seen:
        if k in vias:
            c = vias[k].GetPosition()
            out += [(L, (pcbnew.ToMM(c.x), pcbnew.ToMM(c.y))) for L in layers]
    return out


def _zone_point(board, net, layer, toward, inset=0.35):
    """The point of the net's poured copper on `layer` nearest `toward`, pulled `inset` mm into
    the copper (None if the net has no pour there).

    ⚠ DRC NAMES A ZONE BY ITS OUTLINE'S FIRST CORNER (optical, 2026-11-05). A decap moved
    beside U6 and left "Pad 158 [GND] of U6" unconnected to "Zone [GND] on F.Cu", the zone at
    (71.69, 189.53): the board's own bottom-left corner, 60 mm from the pad. The search went
    looking for a path to that corner and found none, with GND pour all round the pad.
    So a zone end is the zone's copper nearest the other end, not the point DRC printed."""
    lid = board.GetLayerID(layer)
    tx, ty = pcbnew.FromMM(toward[0]), pcbnew.FromMM(toward[1])
    d = pcbnew.FromMM(inset)
    best = None
    for z in board.Zones():
        if z.GetNetname() != net or not z.IsOnLayer(lid):
            continue
        fill = z.GetFilledPolysList(lid)
        for k in range(fill.OutlineCount()):
            o = fill.Outline(k)
            for i in range(o.PointCount()):
                v = o.CPoint(i)
                r = (v.x - tx) ** 2 + (v.y - ty) ** 2
                if best is not None and r >= best[0]:
                    continue
                # a vertex is ON the copper's edge, where the clearance shuts the start cell
                for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d), (d, d), (-d, -d), (d, -d), (-d, d)):
                    q = pcbnew.VECTOR2I(v.x + dx, v.y + dy)
                    if all(fill.Contains(pcbnew.VECTOR2I(q.x + ex, q.y + ey))
                           for ex, ey in ((0, 0), (d // 2, 0), (-d // 2, 0), (0, d // 2), (0, -d // 2))):
                        best = (r, (pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)))
                        break
    return best[1] if best else None


def _stitch_islands(board, net, plane, clr=0.2, step=0.25):
    """A via in every island of the net's pour that nothing goes through, where the plane's
    pour is too (or, with no plane, a joined piece of the net's pour on another layer):
    [(x, y), ...] laid.

    ⚠ ZONE TO ZONE IS AN ISLAND, NOT A PATH (pi_cap, 2026-11-05). Two of ten nudged reroutes
    came back with "Zone [GND] on B.Cu" open to "Zone [GND] on In2.Cu" -- both named by the
    board's corner, which says nothing. The real fault was a 33 mm2 strip of the B.Cu pour
    along the south edge, cut off from the rest of it by a track, with no via or through-hole
    pad in it; the In2 plane lay under the whole strip. A maze search has nothing to aim at
    there, and needs nothing: one via down to the plane joins it. An island that has a via
    or a through-hole pad of the net in it is already joined through that and is left alone.
    Clear of every other net's copper on every layer by `clr` past the via's ring, of every
    pad, and hole to hole."""
    r = RS.VIA_D / 2.0
    code = board.GetNetcodeFromNetname(net)
    cu = [L for L in board.GetEnabledLayers().CuStack()]
    at = lambda x, y: pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
    thru = [t.GetPosition() for t in board.GetTracks()
            if t.GetClass() == "PCB_VIA" and t.GetNetname() == net]
    thru += [q.GetPosition() for f in board.GetFootprints() for q in f.Pads()
             if q.GetNetname() == net and q.GetDrillSize().x > 0]
    holes = [(t.GetPosition(), pcbnew.ToMM(t.GetDrillValue()) / 2.0) for t in board.GetTracks()
             if t.GetClass() == "PCB_VIA"]
    holes += [(q.GetPosition(), pcbnew.ToMM(max(q.GetDrillSize().x, q.GetDrillSize().y)) / 2.0)
              for f in board.GetFootprints() for q in f.Pads() if q.GetDrillSize().x > 0]
    pads = [q for f in board.GetFootprints() for q in f.Pads()]
    others = [t for t in board.GetTracks() if t.GetNetname() != net]
    ozones = [z for z in board.Zones() if z.GetNetname() != net and not z.GetIsRuleArea()]
    # what an island may be stitched to: the plane's pour, or on a board without one, a piece
    # of the net's pour on another layer that something already goes through
    targets = []
    for z in board.Zones():
        if z.GetNetname() == net:
            for L in z.GetLayerSet().Seq():
                fill = z.GetFilledPolysList(L)
                for k in range(fill.OutlineCount()):
                    o = fill.Outline(k)
                    if board.GetLayerName(L) in plane or any(o.PointInside(t) for t in thru):
                        ps = pcbnew.SHAPE_POLY_SET()
                        ps.AddOutline(o)
                        targets.append((L, ps))

    def ring(ps, x, y, rr):
        return all(ps.Contains(at(x + dx * rr, y + dy * rr)) for dx, dy in
                   ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (.7, .7), (-.7, -.7), (.7, -.7), (-.7, .7)))

    def legal(x, y):
        p = at(x, y)
        reach = pcbnew.FromMM(r + clr)
        for h, hr in holes:
            if (pcbnew.ToMM(h.x) - x) ** 2 + (pcbnew.ToMM(h.y) - y) ** 2 < (hr + RS.VIA_DRILL / 2 + 0.3) ** 2:
                return False
        for L in cu:
            if any(t.IsOnLayer(L) and t.GetEffectiveShape(L).Collide(p, reach) for t in others):
                return False
            if any(q.IsOnLayer(L) and q.GetEffectiveShape(L).Collide(p, reach) for q in pads):
                return False
            if any(z.IsOnLayer(L) and z.GetFilledPolysList(L).Collide(p, reach) for z in ozones):
                return False
        return True

    laid = []
    for z in board.Zones():
        if z.GetNetname() != net:
            continue
        for L in z.GetLayerSet().Seq():
            if board.GetLayerName(L) in plane:
                continue
            fill = z.GetFilledPolysList(L)
            for k in range(fill.OutlineCount()):
                o = fill.Outline(k)
                if any(o.PointInside(t) for t in thru):
                    continue
                isl = pcbnew.SHAPE_POLY_SET()
                isl.AddOutline(o)
                bb = o.BBox()
                x0, y0 = pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY())
                x1, y1 = pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
                cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
                pts = [(x0 + i * step, y0 + j * step) for i in range(int((x1 - x0) / step) + 1)
                       for j in range(int((y1 - y0) / step) + 1)]
                pts.sort(key=lambda q: (q[0] - cx) ** 2 + (q[1] - cy) ** 2)
                for x, y in pts:
                    if ring(isl, x, y, r + 0.05) and any(TL != L and ring(ps, x, y, r + 0.05)
                                                          for TL, ps in targets) \
                            and legal(x, y):
                        v = pcbnew.PCB_VIA(board)
                        v.SetPosition(at(x, y))
                        v.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(RS.VIA_D))
                        v.SetDrill(pcbnew.FromMM(RS.VIA_DRILL))
                        v.SetNetCode(code)
                        board.Add(v)
                        thru.append(at(x, y))
                        holes.append((at(x, y), RS.VIA_DRILL / 2.0))
                        laid.append((round(x, 2), round(y, 2)))
                        break
    return laid


def _record(stem, closure):
    """Append one laid closure to <stem>.closures.json, for quality A23 to judge.

    ⚠ A CLOSURE IS NOT CLEAN BECAUSE IT CONNECTS (optical, 2026-11-05). After a decap moved,
    the board came back 0 open, 0 FAIL with +3V3D joined by 38.2 mm of track across a 2.4 mm
    gap, and FLASH_RX by 33.2 mm across 7.8 on another move: DRC and every check passed, so the
    robustness count read both as good boards.
    Each closure is written down with the straight distance between the two ends it joins,
    and A23 sets the length against it. A record whose copper is no longer on the board (a
    put-back attempt, prune_closures, an eco move) is ignored there, so this only appends."""
    path = stem + ".closures.json"
    try:
        with open(path, encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        got = []
    got.append(closure)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(got, fh, indent=1)


def _pad_layer(board, net, layer, pos):
    """The layer an SMD pad at `pos` is really on (a through-hole pad keeps `layer`).

    ⚠ A DRC ITEM FOR A PAD NAMES NO LAYER, and the default here was F.Cu -- so a search
    for a capacitor on the BACK ended on the front, over the pad, and reached it with a
    via drilled into a 0.56 mm land (quality A12, pi_cap 2026-10-04).
    """
    at = pcbnew.VECTOR2I(pcbnew.FromMM(pos[0]), pcbnew.FromMM(pos[1]))
    for f in board.GetFootprints():
        for q in f.Pads():
            if q.GetNetname() == net and q.GetDrillSize().x == 0 and q.HitTest(at):
                return "B.Cu" if q.IsOnLayer(pcbnew.B_Cu) else "F.Cu"
    return layer


def _lay(board, stem, net, res, width, layer_id, named, gap):
    """Lay one search result `res` = (runs, vias) for `net` at `width`, and record it as a
    closure of `gap` between the two ends `named`. Returns the track length laid."""
    runs, vias = res
    code = board.GetNetcodeFromNetname(net)
    # ⚠ TWO VIAS A TENTH OF A MILLIMETRE APART ARE ONE VIA. The maze can
    # return a layer change that immediately reverses -- F.Cu down to B.Cu
    # and back up, with a B.Cu run between them shorter than the drill. On
    # the watering-backpack board that put two LEVEL vias 0.067 mm apart and
    # two GATE_A vias 0.242 mm apart, against a 0.25 mm hole-to-hole
    # minimum. DRC reports it as hole_to_hole at "actual 0.0000 mm" -- the
    # holes do not merely crowd, they OVERLAP -- and grades it a WARNING, so
    # the error count stays at zero and nobody looks. A fab either rejects
    # the drill file or drills one ragged hole.
    #
    # So the via list is merged first and the track ends are snapped onto
    # whatever they merged into: one via still joins F.Cu to B.Cu at that
    # point, which is all the pair ever did, and the short run between them
    # collapses to nothing and is dropped. Snapping can only move a point by
    # less than the merge radius, and finish.py keeps this whole pass only
    # if DRC comes out strictly better, so a snap that hurt would be thrown
    # away rather than shipped.
    merge_r = RS.VIA_DRILL + 0.25
    # Seeded with the vias ALREADY on this net, because the hole the new one
    # crowds need not be another new one. The first version of this merged
    # only within close_last's own list and left a LEVEL via 0.0673 mm from
    # one the ROUTER had put down -- same violation, different neighbour.
    # Snapping onto an existing via is better than merging two new ones: the
    # layer transition is already there and already in the zones' pour.
    keep_v, snap = [], {}
    for _t in board.GetTracks():
        if isinstance(_t, pcbnew.PCB_VIA) and _t.GetNetname() == net:
            _p = _t.GetPosition()
            keep_v.append((pcbnew.ToMM(_p.x), pcbnew.ToMM(_p.y)))
    n_existing = len(keep_v)

    def _snap(q):
        for k in keep_v:
            if (q[0] - k[0]) ** 2 + (q[1] - k[1]) ** 2 < merge_r ** 2:
                return k
        return None

    for q in vias:
        k = _snap(q)
        if k is None:
            keep_v.append(q)
        else:
            snap[(round(q[0], 6), round(q[1], 6))] = k
    vias = keep_v[n_existing:]
    if len(vias) != len(res[1]):
        print("close_last: %s -- merged %d via(s) that would have overlapped "
              "a neighbouring hole (min %.2f mm)"
              % (net, len(res[1]) - len(vias), merge_r))

    def _pt(q):
        return snap.get((round(q[0], 6), round(q[1], 6)), q)

    length, laid = 0.0, []
    for L, pts in runs:
        pts = [_pt(q) for q in pts]
        for q0, q1 in zip(pts, pts[1:]):
            if q0 == q1:
                continue
            laid.append((L, round(q0[0], 4), round(q0[1], 4), round(q1[0], 4), round(q1[1], 4)))
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(q0[0]), pcbnew.FromMM(q0[1])))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(q1[0]), pcbnew.FromMM(q1[1])))
            t.SetWidth(pcbnew.FromMM(width))
            t.SetLayer(layer_id[L])
            t.SetNetCode(code)
            board.Add(t)
            length += ((q1[0] - q0[0]) ** 2 + (q1[1] - q0[1]) ** 2) ** 0.5
    # ⚠ FINISH AT THE VIA'S CENTRE, NOT AT ITS RIM (optical +3V3A, 2026-10-04). Own-net
    # copper is free ground to the search, so a path aimed at a via stops at the first
    # cell that touches its ring: the track ended 0.30 mm from the centre of a 0.60 mm
    # via, joined by the 0.1 mm its round end overlaps the ring. DRC calls that
    # connected; it is a sliver, and the quality pass's own walk (which joins a track
    # to a via at the via's centre) read the rail as cut in two.
    _own_vias = [(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y),
                  pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2.0)
                 for t in board.GetTracks()
                 if t.GetClass() == "PCB_VIA" and t.GetNetname() == net]
    _flat = [(L, q) for L, pts in runs for q in pts]
    for L, q in (_flat[0], _flat[-1]) if _flat else ():
        for vx, vy, vr in _own_vias:
            d = ((q[0] - vx) ** 2 + (q[1] - vy) ** 2) ** 0.5
            if 0.005 < d <= vr + width / 2.0:
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(q[0]), pcbnew.FromMM(q[1])))
                t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(vx), pcbnew.FromMM(vy)))
                t.SetWidth(pcbnew.FromMM(width))
                t.SetLayer(layer_id[L])
                t.SetNetCode(code)
                board.Add(t)
                break
    # ⚠ NO VIA IN A THROUGH-HOLE PAD OF THE SAME NET (pi_cap, 2026-10-04). The search
    # is told which layer each end is on, and a DRC "PTH pad" item names F.Cu whatever
    # layer the route arrives on -- so a path that came in on B.Cu changed layer AT the
    # pin, and the via it dropped there was a second hole drilled through the pin's own
    # (quality A12: hole to hole -0.65 mm). The plated barrel is already the layer
    # change; the two runs meet at its centre without one.
    barrels = [(pcbnew.ToMM(q.GetPosition().x), pcbnew.ToMM(q.GetPosition().y),
                pcbnew.ToMM(min(q.GetSize().x, q.GetSize().y)) / 2.0)
               for f in board.GetFootprints() for q in f.Pads()
               if q.GetNetname() == net and q.GetDrillSize().x > 0]
    # ...and the same for a via the net already has (motor_ctrl PG_5V, 2026-10-04): a
    # search started FROM an escape via on one layer and changing to another beside it
    # dropped its own via 0.02 mm from the first -- two holes 0.28 mm into each other.
    barrels += [(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y),
                 RS.VIA_D) for t in board.GetTracks()
                if t.GetClass() == "PCB_VIA" and t.GetNetname() == net]
    # ⚠ ...AND A LAYER CHANGE THAT BORROWS A BARREL HAS TO REACH IT ON BOTH LAYERS
    # (optical +3V3A, 2026-10-04). The path left an escape via on In2, stepped 0.30 mm
    # and changed to B.Cu; its own via was dropped as above, which left the B.Cu run
    # starting 0.30 mm from the barrel that was now carrying it -- joined by overlap
    # with the ring, a sliver DRC accepts. Each run that turned at a dropped via gets
    # a stub to the centre of the barrel that replaced it.
    kept = []
    for vx, vy in vias:
        hit = [(bx, by) for bx, by, br in barrels
               if (vx - bx) ** 2 + (vy - by) ** 2 <= br * br]
        if not hit:
            kept.append((vx, vy))
            continue
        bx, by = min(hit, key=lambda c: (vx - c[0]) ** 2 + (vy - c[1]) ** 2)
        for L, pts in runs:
            near = lambda q, x, y: abs(q[0] - x) < 0.003 and abs(q[1] - y) < 0.003
            if (any(near(q, vx, vy) for q in pts)
                    and not any(near(q, bx, by) for q in pts)
                    and (vx - bx) ** 2 + (vy - by) ** 2 > 1e-6):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(vx), pcbnew.FromMM(vy)))
                t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(bx), pcbnew.FromMM(by)))
                t.SetWidth(pcbnew.FromMM(width))
                t.SetLayer(layer_id[L])
                t.SetNetCode(code)
                board.Add(t)
    vias = kept
    for vx, vy in vias:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(vx), pcbnew.FromMM(vy)))
        v.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(RS.VIA_D))
        v.SetDrill(pcbnew.FromMM(RS.VIA_DRILL))
        v.SetNetCode(code)
        board.Add(v)
    print("close_last: %s closed with %.2f mm over %s and %d via(s)"
          % (net, length, "/".join(L for L, _p in runs), len(vias)))
    _record(stem, {"net": net, "a": [round(c, 3) for c in named[0][1]],
                   "b": [round(c, 3) for c in named[1][1]], "gap": round(gap, 3),
                   "length": round(length, 3), "tracks": laid})
    return length


RIP_MAX = 6                   # nets close_last may take up for one closure
RIP_TOTAL = 9                 # ...and in all, counting those that must move to rejoin them


def _pieces(board, B, rip, layers, layer_id):
    """What taking up the copper `rip` (uuids) leaves of net B: (anchors, stubs).

    anchors = [(piece, layer, point)]: where ripped copper met a piece of B that keeps a pad;
    stubs = uuids of kept copper left in a piece with no pad, which goes with the ripped."""
    mm = lambda p: (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))
    eps = 0.005
    same = lambda p, q: abs(p[0] - q[0]) < eps and abs(p[1] - q[1]) < eps
    items = [t for t in board.GetTracks() if t.GetNetname() == B]
    pads = [q for f in board.GetFootprints() for q in f.Pads() if q.GetNetname() == B]
    kept = [t for t in items if t.m_Uuid.AsString() not in rip]
    nodes = [("t", t) for t in kept] + [("p", q) for q in pads]
    up = list(range(len(nodes)))

    def find(i):
        while up[i] != i:
            up[i] = up[up[i]]
            i = up[i]
        return i

    def ends(nd):
        k, o = nd
        if k == "p":
            return []
        if o.GetClass() == "PCB_VIA":
            return [(None, mm(o.GetPosition()))]
        return [(o.GetLayerName(), mm(o.GetStart())), (o.GetLayerName(), mm(o.GetEnd()))]

    def on(nd, L, p):
        """Does node `nd` take copper at point p on layer L (None = any layer)?"""
        k, o = nd
        if k == "p":
            return o.HitTest(pcbnew.VECTOR2I(pcbnew.FromMM(p[0]), pcbnew.FromMM(p[1]))) and (
                L is None or o.GetDrillSize().x > 0 or o.IsOnLayer(layer_id.get(L, -1)))
        return any((L is None or L2 is None or L == L2) and same(p, q) for L2, q in ends(nd))
    for i, nd in enumerate(nodes):
        for L, p in ends(nd):
            for j in range(len(nodes)):
                if j != i and on(nodes[j], L, p):
                    up[find(i)] = find(j)
    padded = {find(i) for i, nd in enumerate(nodes) if nd[0] == "p"}
    stubs = {nd[1].m_Uuid.AsString() for i, nd in enumerate(nodes)
             if nd[0] == "t" and find(i) not in padded}
    anchors = []
    for t in items:
        if t.m_Uuid.AsString() not in rip:
            continue
        pts = ([(None, mm(t.GetPosition()))] if t.GetClass() == "PCB_VIA"
               else [(t.GetLayerName(), mm(t.GetStart())), (t.GetLayerName(), mm(t.GetEnd()))])
        for L, p in pts:
            for i, nd in enumerate(nodes):
                if find(i) in padded and on(nd, L, p):
                    if L is None:               # a ripped via: its kept neighbour's layer
                        if nd[0] == "p":
                            L = "F.Cu" if nd[1].IsOnLayer(pcbnew.F_Cu) else "B.Cu"
                        else:
                            Ls = [L2 for L2, q in ends(nd) if L2 and same(p, q)]
                            L = Ls[0] if Ls else None
                    if L in layers:
                        anchors.append((find(i), L, p))
                    break
    return anchors, stubs


def _rip_one(board, stem, net, model, layers, layer_id, named, gap, tries, close_w, deadline,
             stay=frozenset(), first=(), sc=1.0):
    """No path for `net`: find the path that crosses the fewest other nets' copper, take up
    what it runs into, lay `net`, and join each net taken up again round it. Returns
    (board, 1) on success, or the board as it was and 0.

    ⚠ THE LAST OPEN NET IS WALLED IN, NOT UNROUTABLE (output_panel, 2026-11-08). Pin 34 for
    ROLE_INT_N took the board to 9 of 11 nudged reroutes, and the two failures were one net
    each -- POT_CS on one route, I2S_WS on another -- with "no path" round the MCU's north
    pins, where the router had already laid its neighbours. Every per-net cure tried (declared
    escapes) moved the failure to another net. What a router does about that is rip-up and
    reroute, and close_last had none. Taking up ONE net was tried first and opened nothing:
    POT_CS's shortest way through crossed seven. So the search is told the other signal nets'
    track is soft -- crossable at a cost -- and finds the way through the fewest; only the
    segments and vias that path runs into are taken up; each net they belonged to is joined
    again by the same maze (each joint a closure A23 judges, like any other); and if any will
    not join, or more than RIP_MAX nets would have to move, the board is put back as it was.
    Only narrow signal nets are soft: no pour net, no net with a width of its own
    (close_widths), no net with track over 0.3 mm anywhere."""
    import copy
    import shutil
    import time as _time
    mm = lambda p: (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))
    pour = {z.GetNetname() for z in board.Zones()}
    wide = {s["net"] for s in model.segs if s["half"] * 2.0 > 0.3 + 1e-6}
    # a matched or frozen net (a USB pair, a length group) is laid as a set: never taken up
    notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    fixed = set(notes.get("frozen_nets", ())) | set(notes.get("net_widths", {}) or {})
    # A supply on narrow track with no pour MAY move (output_panel RR_8, 2026-11-08: +3V3 at
    # 0.25 mm through the corridor inside U1's pin ring was the whole wall round I2S_WS). It is
    # joined again at the width it had, and every joint is held to the A23 detour limits below,
    # so it comes back no thinner and no longer than the closure rule allows any net.
    q = notes.get("quality", {}) or {}
    ratio, excess = float(q.get("closure_ratio", 1.5)), float(q.get("closure_excess", 10.0))
    per_net = q.get("closure_limits", {}) or {}

    def too_long(n, length, g):
        """Would A23 fail this joint? Then it is not a closure worth the move."""
        lim = per_net.get(n)
        if lim is not None:
            return length > float(lim["ratio"]) * g + 1e-9 or length > float(lim["max_mm"]) + 1e-9
        return length > ratio * g and length - g > excess
    for g in notes.get("match", ()) + notes.get("diff_pairs", ()):
        fixed |= set(g.get("nets", ()) if isinstance(g, dict) else g)
    moved = set()           # nets taken up so far: laid again, never taken up twice
    softnet = lambda n: (n and n != net and n not in pour and n not in close_w and n not in wide
                         and n not in fixed and n not in stay and n not in moved)

    def search(m, ends, w):
        """The way from one end to the other through the fewest soft nets' copper."""
        hard = copy.copy(m)
        hard.segs = [s for s in m.segs if not softnet(s["net"])]
        hard.vias = [v for v in m.vias if not softnet(v["net"])]
        hard._vn_key = None
        soft = copy.copy(m)
        soft.segs = [s for s in m.segs if softnet(s["net"])]
        soft.vias = [v for v in m.vias if softnet(v["net"])]
        soft.pads, soft.edges, soft.keepouts = [], [], []
        for (l1, p1), (l2, p2), step in ends:
            if _time.time() > deadline:
                return None
            r = RS.maze3d(hard, layers, p1, l1, p2, l2, w=w, step=step, reach=REACH,
                          soft=soft, soft_cost=sc)
            if r is not None:
                return r
        return None

    def hits(res, w):
        """uuids and nets of the soft copper the path `res` (laid at width w) runs into."""
        runs, pvias = res
        path = [(L, q0, q1) for L, pts in runs for q0, q1 in zip(pts, pts[1:])]
        clr = RS.RULE_CLEAR + 0.02
        hw, vr = w / 2.0, RS.VIA_D / 2.0

        def hit(t):
            if t.GetClass() == "PCB_VIA":
                c, r = mm(t.GetPosition()), pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2.0
                return (any(RS._d_pt_seg(c[0], c[1], q0[0], q0[1], q1[0], q1[1]) < r + hw + clr
                            for _L, q0, q1 in path)
                        or any(math.hypot(c[0] - v[0], c[1] - v[1]) < r + vr + clr for v in pvias))
            a, b = mm(t.GetStart()), mm(t.GetEnd())
            h, L = pcbnew.ToMM(t.GetWidth()) / 2.0, t.GetLayerName()
            return (any(L == L2 and RS._d_seg_seg(a[0], a[1], b[0], b[1], q0[0], q0[1], q1[0], q1[1])
                        < h + hw + clr for L2, q0, q1 in path)
                    or any(RS._d_pt_seg(v[0], v[1], a[0], a[1], b[0], b[1]) < h + vr + clr
                           for v in pvias))
        rip, nets = set(), {}
        for t in board.GetTracks():
            if softnet(t.GetNetname()) and hit(t):
                rip.add(t.m_Uuid.AsString())
                nets.setdefault(t.GetNetname(), []).append(t)
        return rip, nets

    def take_up(rip, nets):
        """Plan each net's rejoin, then cut `rip` (and the stubs it strands) from the file."""
        nonlocal board
        plan = []
        for B in sorted(nets):
            anchors, stubs = _pieces(board, B, rip, layers, layer_id)
            rip |= stubs
            widths = [pcbnew.ToMM(t.GetWidth()) for t in nets[B] if t.GetClass() != "PCB_VIA"]
            plan.append((B, anchors, max(WIDTH, min(widths)) if widths else WIDTH))
        moved.update(nets)
        # ⚠ TAKEN UP IN THE FILE, NOT THROUGH board.Remove: after removing seven items through
        # SWIG the board handed back raw proxies ('SwigPyObject' has no GetNetcodeFromNetname)
        # and the script died with the copper gone. The blocks are cut from the saved text by
        # uuid and the board is read back fresh.
        board.Save(stem + ".kicad_pcb")
        txt = open(stem + ".kicad_pcb", encoding="utf-8", newline="").read()
        txt = re.sub(r"\n\t\((?:segment|via|arc)\b.*?\n\t\)",
                     lambda m_: "" if any(u in m_.group(0) for u in rip) else m_.group(0), txt,
                     flags=re.S)
        open(stem + ".kicad_pcb", "w", encoding="utf-8", newline="").write(txt)
        board = pcbnew.LoadBoard(stem + ".kicad_pcb")
        return plan

    res = search(model, tries, WIDTH)
    if res is None:
        print("close_last: %s -- no path even through other nets' track" % net)
        return board, 0
    rip, nets = hits(res, WIDTH)
    if len(nets) > RIP_MAX:
        print("close_last: %s -- the way through crosses %d nets (%s), more than %d"
              % (net, len(nets), ", ".join(sorted(nets)), RIP_MAX))
        return board, 0
    print("close_last: %s -- taking up %s to get through" % (net, ", ".join(sorted(nets)) or "nothing"))
    shutil.copy(stem + ".kicad_pcb", stem + ".rip.kicad_pcb")
    rec = stem + ".closures.json"
    had_rec = os.path.isfile(rec)
    if had_rec:
        shutil.copy(rec, rec + ".rip")
    todo = take_up(rip, nets)
    ok, stuck = True, None
    if too_long(net, _lay(board, stem, net, res, WIDTH, layer_id, named, gap), gap):
        print("close_last: %s -- the way through is longer than A23 allows" % net)
        ok = False
    # ⚠ A NET TAKEN UP MAY ITSELF BE WALLED IN BY THE NEW ONE (output_panel RR_8, 2026-11-08):
    # I2S_WS went through, and I2S_SDI, then SWCLK, then RELAY found no way back round it on
    # three tries. Each net that will not join gets the same treatment as the first -- the
    # way through the fewest others, what it runs into taken up and queued -- until
    # RIP_TOTAL nets have moved; past that the board is put back.
    todo.sort(key=lambda p: (first.index(p[0]) if p[0] in first else len(first), len(p[1])))
    while todo and ok:
        B, anchors, wb = todo.pop(0)
        joined = {anchors[0][0]} if anchors else set()
        while any(a[0] not in joined for a in anchors):
            board.Save(stem + ".kicad_pcb")
            mb = RS.Board(stem, B)
            a, b = min(((a, b) for a in anchors if a[0] in joined for b in anchors
                        if b[0] not in joined),
                       key=lambda ab: math.hypot(ab[0][2][0] - ab[1][2][0], ab[0][2][1] - ab[1][2][1]))
            r2 = None
            for step in (RS.MAZE_STEP, 0.05):
                if _time.time() > deadline:
                    break
                r2 = RS.maze3d(mb, layers, a[2], a[1], b[2], b[1], w=wb, step=step, reach=REACH)
                if r2 is not None:
                    break
            if r2 is None:
                r2 = search(mb, [((a[1], a[2]), (b[1], b[2]), RS.MAZE_STEP),
                                 ((a[1], a[2]), (b[1], b[2]), 0.05)], wb)
                more = hits(r2, wb) if r2 is not None else None
                if more is None or len(moved) + len(more[1]) > RIP_TOTAL:
                    print("close_last: %s would not join again round %s%s" % (B, net, "" if more is None
                          else " (would move %s too)" % ", ".join(sorted(more[1]))))
                    stuck, ok = B, False
                    break
                print("close_last: %s -- taking up %s to join again"
                      % (B, ", ".join(sorted(more[1])) or "nothing"))
                todo += take_up(*more)
            g = math.hypot(a[2][0] - b[2][0], a[2][1] - b[2][1])
            if too_long(B, _lay(board, stem, B, r2, wb, layer_id, ((a[1], a[2]), (b[1], b[2])), g), g):
                print("close_last: %s joins again only longer than A23 allows" % B)
                stuck, ok = B, False
                break
            joined.add(b[0])
    if ok:
        board.Save(stem + ".kicad_pcb")
        os.remove(stem + ".rip.kicad_pcb")
        if had_rec:
            os.remove(rec + ".rip")
        print("close_last: %s closed by taking up %s and joining it again"
              % (net, ", ".join(sorted(moved)) or "nothing"))
        return board, 1
    print("close_last: %s -- putting the board back as it was" % net)
    shutil.copy(stem + ".rip.kicad_pcb", stem + ".kicad_pcb")
    os.remove(stem + ".rip.kicad_pcb")
    if had_rec:
        shutil.copy(rec + ".rip", rec)
        os.remove(rec + ".rip")
    elif os.path.isfile(rec):
        os.remove(rec)
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    # the net that would not join goes first next time, before the others take its room
    # (RR_8: SWCLK, joined last, found every way out filled by the three joined before it);
    # if it is already first it stays where it is and the way through is looked for again
    if stuck and stuck not in first and len(first) < 3 and _time.time() < deadline:
        return _rip_one(board, stem, net, model, layers, layer_id, named, gap, tries, close_w,
                        deadline, stay, first + (stuck,), sc)
    if stuck and len(stay) < 4 and _time.time() < deadline:
        return _rip_one(board, stem, net, model, layers, layer_id, named, gap, tries, close_w,
                        deadline, stay | {stuck}, first, sc)
    return board, 0


def main(stem):
    d = json.load(open(stem + ".finish.drc.json", encoding="utf-8"))
    todo = []
    for u in d.get("unconnected_items", []):
        if len(u.get("items", [])) != 2:
            continue
        (na, la, pa, ta), (nb, lb, pb, tb) = _ends(u["items"][0]), _ends(u["items"][1])
        if na and na == nb:
            za, zb = (i["description"].startswith("Zone") for i in u["items"][:2])
            todo.append((na, la, pa, ta, lb, pb, tb, za, zb))
    # nets finish.py asks to leave alone on this attempt: a closure of theirs broke a rule
    # last time, and one bad closure must not cost the board the good ones (see finish.py)
    skip = {s for s in os.environ.get("CLOSE_LAST_SKIP", "").split(",") if s}
    if skip:
        print("close_last: leaving %s open on this attempt" % ", ".join(sorted(skip)))
        todo = [t for t in todo if t[0] not in skip]
    if not todo:
        print("close_last: nothing to close")
        return 0
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    layer_id = {L: board.GetLayerID(L) for L in LAYERS}
    have = {L for L in LAYERS if board.IsLayerEnabled(layer_id[L])}
    _notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    plane = set(_notes.get("plane_layers", ()))
    # ⚠ A RAIL IS NOT CLOSED AT SIGNAL WIDTH IF THE BOARD SAYS HOW WIDE IT WANTS IT
    # (optical +3V3A, 2026-10-04). The net left open was the only feed from an LDO to
    # fifteen analog parts, and this file joined it with 23 mm of 0.2 mm track: connected,
    # DRC-clean, and the whole rail through a hair. BOARD_NOTES["close_widths"] =
    # {net: mm} asks for a width; if no path exists at it the search falls back to WIDTH
    # and SAYS SO, because an open net is still worse than a thin one.
    close_w = _notes.get("close_widths", {}) or {}
    layers = [L for L in LAYERS if L in have and L not in plane]
    made, stitched = 0, set()
    # ⚠ THE SEARCH HAS A CLOCK (optical, 2026-10-05). Ten open nets on a 188 mm board took
    # this file past an hour, silently, on a route whose real fault was a placement that
    # left four of them open in the first place. A closing step that runs longer than the
    # router is not finishing a board, it is hiding one that needs another look: after
    # CLOSE_LAST_BUDGET_S (default 20 minutes) the nets not yet reached are left open
    # and named.
    import time as _time
    _t0 = _time.time()
    _budget = float(os.environ.get("CLOSE_LAST_BUDGET_S", "1200"))
    for _i, (net, la, pa, ta, lb, pb, tb, za, zb) in enumerate(todo):
        if _time.time() - _t0 > _budget:
            print("close_last: out of time after %.0f s -- left open: %s"
                  % (_time.time() - _t0, ", ".join(t[0] for t in todo[_i:])))
            break
        # zone to zone: an island nothing goes through, joined to the plane by a via
        if za and zb:
            if net in stitched:
                continue
            stitched.add(net)
            laid = _stitch_islands(board, net, plane)
            if laid:
                made += 1
                print("close_last: %s -- %d pour island(s) stitched to the plane at %s"
                      % (net, len(laid), laid))
                continue
        # a zone end goes to its copper nearest the other end
        if za and not zb:
            pa = _zone_point(board, net, la, pb) or pa
        if zb and not za:
            pb = _zone_point(board, net, lb, pa) or pb
        if ta:
            la, pa = _free_end(board, net, la, pa, pb)
        else:
            la = _pad_layer(board, net, la, pa)
        if tb:
            lb, pb = _free_end(board, net, lb, pb, pa)
        else:
            lb = _pad_layer(board, net, lb, pb)
        if la not in layers or lb not in layers:
            print("close_last: %s ends on a layer this does not route (%s / %s)"
                  % (net, la, lb))
            continue
        # a fresh model per net: the copper laid for the previous one is an obstacle now
        board.Save(stem + ".kicad_pcb")
        model = RS.Board(stem, net)
        # ⚠ NO VIA IN A SMALL SOLDERED PAD OF THE NET'S OWN (output_panel PWR_GND,
        # 2026-10-04). Same-net copper is free ground to the search, so it changed layer
        # in the middle of a SOD-523 land -- quality A12's hard finding, "solder wicks down
        # it". Lands under 4 mm2 that carry paste are closed to vias; bigger ones can
        # afford one, and a pad with no paste has nothing to lose.
        model.own_lands = []
        for f in board.GetFootprints():
            for q in f.Pads():
                if (q.GetNetname() != net or q.GetDrillSize().x > 0
                        or not (q.IsOnLayer(pcbnew.F_Paste) or q.IsOnLayer(pcbnew.B_Paste))):
                    continue
                bb = q.GetBoundingBox()
                w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
                if w * h < 4.0:
                    c = bb.GetCenter()
                    model.own_lands.append((pcbnew.ToMM(c.x), pcbnew.ToMM(c.y), w / 2, h / 2))
        # ⚠ TWO GRIDS, COARSE FIRST. maze3d pads its clearance by half a cell diagonal, and
        # at the default 0.15 mm cell that pad alone (0.106) walls in a QFN pin on 0.4 mm
        # pitch: 0.1 + 0.127 + 0.106 = 0.333 against the 0.3 to its neighbour's edge, so
        # the START cell is blocked and the answer is "no path" for a pin with a clear
        # run straight out. A 0.05 mm cell costs nine times the cells and 0.035 of pad.
        # From any via the end's copper already reaches, inner layers first, and from the
        # end as DRC named it last: a via was drawn because the pin's own layer is shut,
        # so the search from the pin is the one most likely to spend its time failing.
        # The fine grid is for a pin in a 0.4 mm row and is tried on that pairing alone --
        # sixteen pairings at nine times the cells was a quarter of an hour of "no path".
        pref = {L: i for i, L in enumerate(("In2.Cu", "B.Cu", "F.Cu"))}
        via_a = sorted(_via_starts(board, net, pa, layers), key=lambda c: pref.get(c[0], 9))
        via_b = sorted(_via_starts(board, net, pb, layers), key=lambda c: pref.get(c[0], 9))
        named = ((la, pa), (lb, pb))
        gap = ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2) ** 0.5
        # ⚠ NEAREST PAIRING FIRST, AND NOT EVERY PAIRING (optical +3V3D, 2026-10-05). The
        # first path found is the one laid, and a rail's copper reaches dozens of vias: in
        # arbitrary order the first success joined two islands 18 mm apart with 134 mm of
        # track -- the MCU's whole supply through it, 170 mV down -- and the failures
        # before it were long searches that ate the clock. Sorted by the straight line
        # between the two starts, the first success is near the shortest there is.
        def _gap(t):
            (_la, a), (_lb, b) = t[0], t[1]
            return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

        def _near(pairs, keep):
            pairs = sorted(pairs, key=lambda t: (round(_gap(t), 2),
                                                 pref.get(t[0][0], 9) + pref.get(t[1][0], 9)))
            return pairs[:keep]

        tries = (_near([(x, y, RS.MAZE_STEP) for x in via_a for y in via_b], 18)
                 + _near([(x, named[1], RS.MAZE_STEP) for x in via_a], 6)
                 + _near([(named[0], y, RS.MAZE_STEP) for y in via_b], 6)
                 + [(named[0], named[1], RS.MAZE_STEP), (named[0], named[1], 0.05)])
        res = None
        want_w = max(WIDTH, float(close_w.get(net, WIDTH)))
        # A STEP BETWEEN: a rail that will not go at its asked width is tried halfway down
        # before the minimum. On optical two links of the MCU's supply ring fell straight
        # from 0.5 to 0.2 mm and took the rail's drop over its limit.
        _ladder = [want_w]
        if want_w - WIDTH >= 0.2:
            _ladder.append(round((want_w + WIDTH) / 2.0, 2))
        if want_w > WIDTH:
            _ladder.append(WIDTH)
        for _i, width in enumerate(_ladder):
            for (la, pa), (lb, pb), step in tries:
                # the clock again: one net's pairings can outlast the whole budget
                if _time.time() - _t0 > _budget:
                    break
                res = RS.maze3d(model, layers, pa, la, pb, lb, w=width, step=step,
                                reach=REACH)
                if res is not None:
                    break
            if res is not None:
                break
            if width > WIDTH:
                print("close_last: %s -- no path at %.2f mm, trying %.2f"
                      % (net, width, _ladder[_i + 1]))
        if res is None:
            print("close_last: %s -- no path between (%.2f, %.2f) and (%.2f, %.2f)"
                  % (net, pa[0], pa[1], pb[0], pb[1]))
            if _time.time() - _t0 < _budget:
                # then a way that keeps clear of other nets' track wherever it can: a longer
                # one that takes up less leaves the nets taken up more room to join again
                for sc in (1.0, 4.0):
                    board, ok = _rip_one(board, stem, net, model, layers, layer_id, named, gap,
                                         tries[:4] + tries[-2:], close_w, _t0 + _budget, sc=sc)
                    if ok or _time.time() - _t0 > _budget:
                        break
                made += ok
            continue
        _lay(board, stem, net, res, width, layer_id, named, gap)
        made += 1
    board.Save(stem + ".kicad_pcb")
    return made


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
