"""Post-route copper keeps the board's copper-to-edge clearance (brain_board fold11, 2026-11-26).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_outline_room.py

A GND via landed 0.311 mm from J7's notch wall (x 109.5), its copper 0.011 mm off the edge, with
its tracks (DRC copper_edge_clearance x3). The router knew the edge; the via placers that run
after it never asked. A board built here, no files: outline x 24.585..191.01, y 50..150, with
fold11's notch x 109.5..124.5, y 50..61, and m_CopperEdgeClearance 0.3.
1. OutlineRoom.via_ok refuses fold11's via (109.1886, 59.1536, r 0.3) and one inside the notch,
   and passes one 1 mm off the wall (108.5, 59.15); a via over a round cut-out's edge is refused.
2. seg_ok refuses the F.Cu GND stub (108.835, 58.25) -> (109.1886, 59.1536) at 0.2 mm and passes
   a stub that stays 0.6 mm off the wall.
3. Every post-route via placer asks it: layout's add_missing_vias, _path_clear, _via_on_piece,
   _vias_on_piece, _move_plane_joins, rescue_stray_stitches, and unwick.
Exit 0 = PASS.
"""
import os
import re
import sys

import wx  # noqa: F401  (KiCad's python ships it)
wx.DisableAsserts()
import pcbnew  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import outline_room  # noqa: E402

F = pcbnew.FromMM
bad = []
b = pcbnew.BOARD()
pts = [(24.585, 50.0), (109.5, 50.0), (109.5, 61.0), (124.5, 61.0), (124.5, 50.0), (191.01, 50.0),
       (191.01, 150.0), (24.585, 150.0)]
for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(F(x1), F(y1)))
    s.SetEnd(pcbnew.VECTOR2I(F(x2), F(y2)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(F(0.1))
    b.Add(s)
c = pcbnew.PCB_SHAPE(b)                       # a round cut-out, r 1.6 at (60, 100)
c.SetShape(pcbnew.SHAPE_T_CIRCLE)
c.SetCenter(pcbnew.VECTOR2I(F(60.0), F(100.0)))
c.SetEnd(pcbnew.VECTOR2I(F(61.6), F(100.0)))
c.SetLayer(pcbnew.Edge_Cuts)
c.SetWidth(F(0.1))
b.Add(c)
b.GetDesignSettings().m_CopperEdgeClearance = F(0.3)
room = outline_room.OutlineRoom(b)
if not room.ok:
    bad.append("no closed outline read off the board")
for x, y, want, what in ((109.1886, 59.1536, False, "fold11's via 0.311 off the notch wall"),
                         (115.0, 55.0, False, "a via inside the notch"),
                         (108.5, 59.15, True, "a via 1.0 mm off the wall"),
                         (61.7, 100.0, False, "a via over the round cut-out's edge"),
                         (63.0, 100.0, True, "a via 1.4 mm off the cut-out")):
    got = room.via_ok(F(x), F(y), F(0.3))
    print("via (%.4f, %.4f) r 0.3: %s  -- %s" % (x, y, "ok" if got else "refused", what))
    if got != want:
        bad.append("%s: via_ok %s" % (what, got))
for a, z, want, what in (((108.835, 58.25), (109.1886, 59.1536), False, "fold11's F.Cu GND stub"),
                         ((108.0, 58.25), (108.4, 59.15), True, "a stub 0.6 mm off the wall")):
    got = room.seg_ok((F(a[0]), F(a[1])), (F(z[0]), F(z[1])), F(0.1))
    print("stub %s -> %s w 0.2: %s  -- %s" % (a, z, "ok" if got else "refused", what))
    if got != want:
        bad.append("%s: seg_ok %s" % (what, got))

rd = lambda f: open(os.path.join(HERE, f), encoding="utf-8").read().replace("\r\n", "\n")
lay, unw = rd("layout.py"), rd("unwick.py")


def body(src, name):
    m = re.search(r"\ndef %s\(.*?(?=\ndef |\Z)" % re.escape(name), src, re.S)
    return m.group(0) if m else ""


for name in ("add_missing_vias", "_path_clear", "_via_on_piece", "_vias_on_piece",
             "_move_plane_joins", "rescue_stray_stitches"):
    bd = body(lay, name)
    if (not bd or not re.search(r"outline_room\.(OutlineRoom|for_board)\(board\)", bd)
            and "room = outline_room" not in bd) or not re.search(r"\.(via|seg)_ok\(", bd):
        bad.append("layout.%s does not ask the outline" % name)
if "outline_room.OutlineRoom(board)" not in unw or "room.via_ok(" not in unw:
    bad.append("unwick does not ask the outline")
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.stdout.flush()
os._exit(1 if bad else 0)
