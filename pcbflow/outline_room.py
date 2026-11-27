"""The board outline as a legality test for POST-ROUTE copper: a via or a stub laid after the
router keeps the board's copper-to-edge clearance (m_CopperEdgeClearance) inside the outline
and off every cut-out.

⚠ THE ROUTER KNEW THE EDGE AND THE REPAIRS DID NOT (brain_board fold11, 2026-11-26). The router
model holds the outline (router/model.py _edge_field, edge_clear 0.3) and refused the cell, yet
a GND via landed 0.311 mm from J7's notch wall at x 109.5 -- its copper 0.011 mm off the edge --
with its tracks: DRC copper_edge_clearance x3. The via placers that run after the route
(layout's strand repair, plane-join mover, missing-via and stray-stitch passes, unwick) tested
pads, tracks, holes and frozen bands, never the outline. Every one of them asks this.

    room = OutlineRoom(board)
    room.via_ok(x, y, r)            # nm: a disc of radius r at (x, y)
    room.seg_ok((x1, y1), (x2, y2), half)   # nm: a track of half-width `half`
"""
import math

import pcbnew


def _seg_seg(ax, ay, bx, by, cx, cy, dx, dy):
    """Distance between segments AB and CD (any units)."""
    def pt_seg(px, py, x1, y1, x2, y2):
        ux, uy = x2 - x1, y2 - y1
        L2 = ux * ux + uy * uy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x1) * ux + (py - y1) * uy) / L2))
        return math.hypot(px - (x1 + t * ux), py - (y1 + t * uy))

    def cross(ox, oy, px, py, qx, qy):
        return (px - ox) * (qy - oy) - (py - oy) * (qx - ox)

    d1, d2 = cross(cx, cy, dx, dy, ax, ay), cross(cx, cy, dx, dy, bx, by)
    d3, d4 = cross(ax, ay, bx, by, cx, cy), cross(ax, ay, bx, by, dx, dy)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 and d2 and d3 and d4:
        return 0.0
    return min(pt_seg(ax, ay, cx, cy, dx, dy), pt_seg(bx, by, cx, cy, dx, dy),
               pt_seg(cx, cy, ax, ay, bx, by), pt_seg(dx, dy, ax, ay, bx, by))


class OutlineRoom:
    def __init__(self, board):
        self.ps = pcbnew.SHAPE_POLY_SET()
        self.ok = bool(board.GetBoardPolygonOutlines(self.ps, False)) and self.ps.OutlineCount() > 0
        self.ec = board.GetDesignSettings().m_CopperEdgeClearance
        self.segs = []
        if not self.ok:
            return
        for i in range(self.ps.OutlineCount()):
            chains = [self.ps.COutline(i)] + [self.ps.CHole(i, h) for h in range(self.ps.HoleCount(i))]
            for c in chains:
                for k in range(c.SegmentCount()):
                    s = c.CSegment(k)
                    self.segs.append((float(s.A.x), float(s.A.y), float(s.B.x), float(s.B.y)))

    def _inside(self, x, y):
        return self.ps.Contains(pcbnew.VECTOR2I(int(x), int(y)))

    def via_ok(self, x, y, r):
        """A disc of radius r (nm) at (x, y) sits inside the outline, m_CopperEdgeClearance off
        every edge and cut-out. With no closed outline the board cannot be judged: True."""
        if not self.ok:
            return True
        if not self._inside(x, y):
            return False
        need = r + self.ec
        bx0, by0, bx1, by1 = x - need, y - need, x + need, y + need
        for x1, y1, x2, y2 in self.segs:
            if max(x1, x2) < bx0 or min(x1, x2) > bx1 or max(y1, y2) < by0 or min(y1, y2) > by1:
                continue
            if _seg_seg(x, y, x, y, x1, y1, x2, y2) < need:
                return False
        return True

    def seg_ok(self, a, b, half):
        """A track from a to b (nm points) of half-width `half` keeps the edge clearance."""
        if not self.ok:
            return True
        ax, ay = float(a[0]), float(a[1])
        bx, by = float(b[0]), float(b[1])
        if not (self._inside(ax, ay) and self._inside(bx, by)):
            return False
        need = half + self.ec
        bx0, by0 = min(ax, bx) - need, min(ay, by) - need
        bx1, by1 = max(ax, bx) + need, max(ay, by) + need
        for x1, y1, x2, y2 in self.segs:
            if max(x1, x2) < bx0 or min(x1, x2) > bx1 or max(y1, y2) < by0 or min(y1, y2) > by1:
                continue
            if _seg_seg(ax, ay, bx, by, x1, y1, x2, y2) < need:
                return False
        return True


_CACHE = {}


def for_board(board):
    """One OutlineRoom per board while its Edge.Cuts stay the same: callers in tight loops
    (layout._path_clear, sampled once per candidate stub) do not rebuild the outline."""
    n_edge = sum(1 for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts)
    key = (id(board), n_edge, board.GetDesignSettings().m_CopperEdgeClearance)
    r = _CACHE.get(key)
    if r is None:
        _CACHE.clear()
        r = _CACHE[key] = OutlineRoom(board)
    return r
