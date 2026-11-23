"""route.widen_necks never widens a track into another net's frozen band (2026-11-22).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_widen_band.py <dir holding rPS_sqe1's
        UNROUTED board as b.kicad_pcb / b.kicad_pro / b.board.json>

rPS_sqe1 (brain_board, sqahe placement): layout laid the declared +5V_CM5 B.Cu run
(117, 125.6)->(119.5, 123.9) at 1.4 mm beside +24V's B.Cu frozen band. post_route's
widen_necks took it to the net's `current` width, 2.05: its edge crossed the band's outline +
zone clearance, the refill lost 14.7 -> 13.7 mm2, and finish stopped on "FROZEN BAND LOST at
ownroute.py". Pads and tracks were obstacles to widening; the band (a zone) was not.

1. widen_necks runs on the unrouted board (the declared copper alone -- the crossing needs no
   route), and that run must leave every widened track out of every foreign band:
   FrozenWall.seg_ok at the track's new half width, on its layer.
2. The run itself must still widen something (a wall that refuses every widening passes 1).
Exit 0 = PASS. Nothing is saved.
"""
from __future__ import annotations
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main(d):
    try:
        import wx as _wx
        _wx.DisableAsserts()
    except Exception:
        pass
    import pcbnew
    import frozen_wall
    import layout
    import route
    F, M = pcbnew.FromMM, pcbnew.ToMM
    b = pcbnew.LoadBoard(os.path.join(d, "b.kicad_pcb"))
    notes = json.load(open(os.path.join(d, "b.board.json"), encoding="utf-8"))
    cut = next((t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() == "+5V_CM5"
                and abs(M(t.GetStart().x) - 117.0) < 0.01 and abs(M(t.GetStart().y) - 125.6) < 0.01
                and abs(M(t.GetEnd().x) - 119.5) < 0.01), None)
    if cut is None:
        return ["the +5V_CM5 run (117, 125.6)->(119.5, 123.9) is not on this board -- wrong board?"]
    wall = frozen_wall.FrozenWall(b, keepouts=False)
    if wall.seg_ok((cut.GetStart().x, cut.GetStart().y), (cut.GetEnd().x, cut.GetEnd().y),
                   "+5V_CM5", F(2.05) // 2, cut.GetLayer()):
        return ["a 2.05 mm +5V_CM5 run there clears +24V's band -- the case no longer bites"]
    w0 = {t.m_Uuid.AsString(): t.GetWidth() for t in b.GetTracks()}
    layout.NECKED.clear()
    route.widen_necks(b, notes)
    bad, grew = [], 0
    for t in b.GetTracks():
        if t.GetClass() != "PCB_TRACK" or t.GetWidth() <= w0.get(t.m_Uuid.AsString(), t.GetWidth()):
            continue
        grew += 1
        if not wall.seg_ok((t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y),
                           t.GetNetname(), t.GetWidth() // 2, t.GetLayer()):
            s_, e_ = t.GetStart(), t.GetEnd()
            hit = next((h["net"] for k in range(11)
                        for h in [wall.band_at(s_.x + (e_.x - s_.x) * k / 10, s_.y + (e_.y - s_.y) * k / 10,
                                               t.GetNetname(), t.GetWidth() // 2, t.GetLayer())] if h), "?")
            bad.append("%s %s (%.2f, %.2f)->(%.2f, %.2f) widened %.2f -> %.2f into %s's frozen band"
                       % (t.GetNetname(), b.GetLayerName(t.GetLayer()), M(t.GetStart().x), M(t.GetStart().y),
                          M(t.GetEnd().x), M(t.GetEnd().y), M(w0[t.m_Uuid.AsString()]), M(t.GetWidth()), hit))
    print("  widen_necks widened %d track(s); the +5V_CM5 run is %.2f mm" % (grew, M(cut.GetWidth())), flush=True)
    if not grew:
        bad.append("widen_necks widened nothing -- the wall refuses everything?")
    return bad


if __name__ == "__main__":
    bad = main(sys.argv[1])
    print("\n".join(bad) if bad else "PASS", flush=True)
    os._exit(1 if bad else 0)
