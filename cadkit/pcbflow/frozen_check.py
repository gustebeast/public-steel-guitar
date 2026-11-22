"""Frozen-band integrity after every stage that writes copper (lead 2026-11-21).

    KiCad-python cadkit/pcbflow/frozen_check.py STEM STAGE

STAGE "layout" records the baseline: every frozen band (a pour zone NAMED "frozen") refilled on
its own, its filled pieces and area, into STEM.frozen_base.json -- the same fill the pregate
judges. Any other STAGE (the router, unwick, repair_planes, close_last, prune_closures,
spent_vias, power_vias, return_vias, eco) refills the bands on the board as that stage left it
and compares. One line a band goes to the log:

    frozen_check <stage>: +5V_SW F.Cu pieces 1 -> 2, area 42.2 -> 26.7 mm2 (-36.7 %) LOST

A band LOST (more pieces than the baseline -- pieces that hold the baseline's copper -- or more than LOSS_PCT / LOSS_MM2 of its area gone)
exits 3 naming the band, the stage, and every foreign track or via inside the band's GROWN
outline -- half its width (a via's radius) plus the zone's clearance, the reach at which the
refill knocks copper out of the band (router.model frozen_d) -- that the baseline did not have.
finish.py stops the flow on it: the next copper writer that cuts a band is a stop with a name,
not a thin power-gate reading two hours later.

⚠ WHY (brain_board, 2026-11-21): two different copper writers cut frozen bands -- the router
(a +24V_RIB via ON +5V_SW's edge, rPS_e3: 42.2 -> 20.0 + 6.7 mm2) and layout's plane reconnect
(an 11.8 mm +24V stub across VIN_SW, rPS_e2). Both read PASS/WARN on the unrouted board and
OPEN at the power gate after the route. Two writers, two holes: there will be a third.

THE LOST LINE NAMES THE CUT, NOT THE CROWD (lead 2026-11-22). Everything inside the grown outline
is not the cut: on rPS_11a4 the line listed +24V_RIB tracks and five vias beside the three GND repair
tracks that alone split +24V_LED, and the vias read as the router's fault. A lost band is re-judged on
fresh loads of the board with intruders taken out (_blame): an item is a CUT when, left alone among
the intruders, the band is still lost, or when taking it alone out restores the band; if none does
alone but all together do, they are named as one joint cut. The rest go on an "also inside" line.
Only a lost band pays for this (a load and one band refill per intruder, at most MAX_BLAME).

PCBFLOW_FROZEN_CHECK=warn reports a lost band and goes on (replaying an old board as it was);
=0 skips the check. A board with no frozen bands is never touched.
"""
from __future__ import annotations

import json
import os
import sys

import pcbnew

LOSS_PCT = 2.0         # a band that keeps its piece count may lose this much of its area ...
LOSS_MM2 = 0.3         # ... and at least this much, before it is LOST (refill noise is below both
                       # on brain_board: k1/e3 pregate-vs-pregate refills agree to 0.0 mm2)
ZONE_CLR_DEFAULT = 0.5
MAX_NAMED = 10         # intruders named per lost band (the rest counted)
MAX_BLAME = 24         # intruders re-judged one by one (beyond it, the cut is not bisected)
_KEEP = []             # Removed items' proxies outlive their boards (finish._REMOVED says why)


def _mm2(v):
    return v / 1e12


def _zclr(z):
    c = z.GetLocalClearance()
    c = c.value() if hasattr(c, "value") else c
    return c if c else pcbnew.FromMM(ZONE_CLR_DEFAULT)


def _bands(board):
    out = []
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetZoneName() != "frozen":
            continue
        bb = z.GetBoundingBox()
        key = "%s|%s|%.1f,%.1f,%.1f,%.1f" % (z.GetNetname(), board.GetLayerName(z.GetFirstLayer()),
                                             pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                                             pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))
        out.append((key, z))
    return out


def _fill(board, zones):
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    try:
        import stable_fill
        stable_fill.fill(board, zones)
    except ImportError:
        pcbnew.ZONE_FILLER(board).Fill(zones)


PIECE_MM2 = 0.05       # a filled piece smaller than this is not counted


def _measure(board, z, base_polys=None):
    """Pieces, area, the biggest pieces, and the fill's outlines (for the next stage's baseline).

    ⚠ A NEW PIECE OF COPPER IS NOT A CUT (brain_board rPS_fg1/fg2, 2026-11-21): VIN_CM5 read
    1 -> 2 pieces on both seeds with nothing foreign near. The route widened the band's own
    declared stub over U205.7 (0.25 -> 0.45), an island inside the package between pins 6 and 7
    then touched it and survived island removal: 0.52 mm2 of copper the baseline never had. Judged
    against the baseline, a piece counts only where it holds at least PIECE_MM2 of the BASELINE's
    copper -- a band carved in two still reads two; copper gained reads as area, not a split."""
    L = z.GetFirstLayer()
    f = z.GetFilledPolysList(L)
    areas = [_mm2(f.Outline(i).Area()) for i in range(f.OutlineCount())]
    if base_polys is None:
        pieces = sum(1 for a in areas if a >= PIECE_MM2)
    else:
        bp = pcbnew.SHAPE_POLY_SET()
        for pts in base_polys:
            bp.NewOutline()
            for x, y in pts:
                bp.Append(int(x), int(y))
        pieces = 0
        for i in range(f.OutlineCount()):
            if areas[i] < PIECE_MM2:
                continue
            one = pcbnew.SHAPE_POLY_SET(); one.AddOutline(f.Outline(i))
            one.BooleanIntersection(bp)
            if _mm2(one.Area()) >= PIECE_MM2:
                pieces += 1
    polys = [[[f.Outline(i).CPoint(j).x, f.Outline(i).CPoint(j).y] for j in range(f.Outline(i).PointCount())]
             for i in range(f.OutlineCount()) if areas[i] >= PIECE_MM2]
    srt = sorted(areas, reverse=True)
    return {"pieces": pieces, "area": round(sum(areas), 2), "biggest": [round(a, 1) for a in srt[:4]],
            "polys": polys}


def _intruders(board, z):
    """Foreign tracks (on the band's layer) and vias (any layer) inside the band's grown outline."""
    o, L, net, clr = z.Outline(), z.GetFirstLayer(), z.GetNetname(), _zclr(z)
    hit = {}
    for t in board.GetTracks():
        if t.GetNetname() == net:
            continue
        if t.GetClass() == "PCB_VIA":
            r = t.GetWidth(L) // 2 if t.GetWidth(L) else t.GetWidth() // 2
            seg = pcbnew.SEG(t.GetPosition(), t.GetPosition())
            what = "via %s at (%.2f, %.2f)" % (t.GetNetname(), pcbnew.ToMM(t.GetPosition().x),
                                               pcbnew.ToMM(t.GetPosition().y))
        elif t.GetLayer() == L:
            r = t.GetWidth() // 2
            seg = pcbnew.SEG(t.GetStart(), t.GetEnd())
            what = "track %s w %.2f (%.2f, %.2f)->(%.2f, %.2f)" % (
                t.GetNetname(), pcbnew.ToMM(t.GetWidth()), pcbnew.ToMM(t.GetStart().x),
                pcbnew.ToMM(t.GetStart().y), pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))
        else:
            continue
        if o.Collide(seg, int(r + clr)):
            hit[t.m_Uuid.AsString()] = what
    # a pour of another net that OUTRANKS the band over its outline (layout lifts frozen bands
    # above every other pour; a board laid before that, or a pour added after, still can)
    for o2 in board.Zones():
        if o2.GetIsRuleArea() or o2.GetNetname() == net or not o2.IsOnLayer(L):
            continue
        if o2.GetAssignedPriority() <= z.GetAssignedPriority():
            continue
        f2 = o2.GetFilledPolysList(L).CloneDropTriangulation()
        f2.Inflate(int(clr), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, pcbnew.FromMM(0.01))
        f2.BooleanIntersection(o)
        if _mm2(f2.Area()) >= PIECE_MM2:
            hit["zone:%s:%d" % (o2.GetNetname(), o2.GetAssignedPriority())] = (
                "pour %s %r priority %d over band priority %d (%.1f mm2 of the outline)" % (
                    o2.GetNetname(), o2.GetZoneName(), o2.GetAssignedPriority(), z.GetAssignedPriority(),
                    _mm2(f2.Area())))
    return hit


def _bad(b, m):
    d = m["area"] - b["area"]
    pct = 100.0 * d / b["area"] if b["area"] else 0.0
    return m["pieces"] > b["pieces"] or (-d > LOSS_MM2 and -pct > LOSS_PCT)


def _judge(stem, key, b, drop):
    """Is the band `key` still lost on a fresh load of the board with the `drop` uuids taken out?"""
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    _KEEP.append(board)
    for t in list(board.GetTracks()):
        if t.m_Uuid.AsString() in drop:
            _KEEP.append(t)
            board.Remove(t)
    z = dict(_bands(board)).get(key)
    if z is None:
        return None
    _fill(board, [z])
    return _bad(b, _measure(board, z, b.get("polys")))


def _blame(stem, key, b, uuids):
    """(cuts, joint): the intruders that cut the band (see the module note), and whether the cut is
    only the set together. ([], False) when taking them ALL out does not restore it."""
    allu = set(uuids)
    if _judge(stem, key, b, allu):
        return [], False
    cuts = []
    for u in uuids:
        if _judge(stem, key, b, allu - {u}) or not _judge(stem, key, b, {u}):
            cuts.append(u)
    return (cuts, False) if cuts else (list(uuids), True)


def main(stem, stage):
    mode = os.environ.get("PCBFLOW_FROZEN_CHECK", "1")
    if mode == "0":
        return 0
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    bands = _bands(board)
    if not bands:
        return 0
    _fill(board, [z for _, z in bands])
    base_path = stem + ".frozen_base.json"
    if stage == "layout":
        now = {k: dict(_measure(board, z), intruders=_intruders(board, z)) for k, z in bands}
        json.dump(now, open(base_path, "w"))
        for k, m in now.items():
            n, ly, _ = k.split("|")
            print("frozen_check layout: %s %s pieces %d, area %.1f mm2 (baseline)" % (n, ly, m["pieces"], m["area"]))
        return 0
    if not os.path.isfile(base_path):
        print("frozen_check %s: no baseline (%s) -- layout did not record one; not judged" % (stage, base_path))
        return 0
    base = json.load(open(base_path))
    now = {k: dict(_measure(board, z, (base.get(k) or {}).get("polys")), intruders=_intruders(board, z))
           for k, z in bands}
    lost = []
    for k, m in now.items():
        n, ly, _ = k.split("|")
        b = base.get(k)
        if b is None:
            print("frozen_check %s: %s %s is not in the baseline (a new band?) -- not judged" % (stage, n, ly))
            continue
        d = m["area"] - b["area"]
        pct = 100.0 * d / b["area"] if b["area"] else 0.0
        bad = _bad(b, m)
        print("frozen_check %s: %s %s pieces %d -> %d, area %.1f -> %.1f mm2 (%+.1f %%)%s"
              % (stage, n, ly, b["pieces"], m["pieces"], b["area"], m["area"], pct, "  LOST" if bad else ""))
        if bad:
            newu = [u for u in m["intruders"] if u not in b.get("intruders", {})]
            order = lambda w: (not w.startswith(("via", "pour")), w)   # vias, pours first: one is a whole cut
            tracks = [u for u in newu if not u.startswith("zone:")]
            cuts, joint, blamed = [], False, False
            if tracks and len(tracks) <= MAX_BLAME:
                cuts, joint = _blame(stem, k, b, tracks)
                blamed = True
            named = sorted((m["intruders"][u] for u in cuts), key=order)
            rest = sorted((m["intruders"][u] for u in newu if u not in cuts), key=order)
            lost.append((n, ly, b, m, named, rest, joint, blamed))
    if not lost:
        return 0
    def _list(xs):
        return "; ".join(xs[:MAX_NAMED]) + (" ... and %d more" % (len(xs) - MAX_NAMED) if len(xs) > MAX_NAMED else "")
    for n, ly, b, m, named, rest, joint, blamed in lost:
        if named:
            what = ("cut by %s%s" % ("these together (no one alone): " if joint else "", _list(named)))
        elif blamed:
            what = "no foreign track or via cuts it (all taken out, still lost) -- a pad or an outranking pour"
        else:
            what = "not bisected (%d intruders); inside its grown outline" % len(rest)
        print("  ⚠ FROZEN BAND LOST at %s: %s on %s, %d piece(s) %.1f mm2 -> %d piece(s) %s mm2; %s"
              % (stage, n, ly, b["pieces"], b["area"], m["pieces"], " + ".join(str(a) for a in m["biggest"]), what))
        if rest:
            print("      also inside its grown outline (not the cut): %s" % _list(rest))
    if mode == "warn":
        print("frozen_check %s: PCBFLOW_FROZEN_CHECK=warn -- going on" % stage)
        return 0
    return 3


if __name__ == "__main__":
    rc = main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(rc)
