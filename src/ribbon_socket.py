"""The ribbon cables' IDC sockets, seated on the new boards' 1.27 mm headers.

User, 2026-11-14: "I see a bunch of pin headers on the brain board but nothing plugged into
them". The output (brain) board's J240 (2 x 15, to the connector board), J4 (2 x 10, the
optical board) and J205 (2 x 8, the UI board), and the connector board's J1 (2 x 15, the
other end of J240's ribbon), are bare HX PZ1.27 headers in KiCad's models; every one of them
carries a ribbon. This draws each socket pressed onto its header and the first STUB mm of its
ribbon, so the render shows what is plugged in -- not where the cable then goes (src/wiring.py
routes leads; these are not routed yet).

THE SOCKET IS src/ui_panel.py's, off Samtec's own print (FFSD-XX-X-XX.XX-01, rev AW; F-226):
N x 1.27 + 4.19 along the rows, 3.05 across them, 5.08 from its mating face, the last 1.02 a
cover pressed over the cable. The header (HX PZ1.27-2xNP, 2022-04-24) stands 5.3 off the
board with 4.00 of pin past its plastic, and the socket bottoms on the pin tips with 3.00 of
pin inside it -- so its mating face is 2.3 off the board.
THE RIBBON: 0.635 mm pitch flat cable, as wide as its ways (2N x 0.635), RIBBON_T thick,
leaving across the rows from the slot between body and cover; which side is not decided by
anything yet, so it leaves on the side AWAY from the board's centre, and only STUB mm of it
is drawn.
"""
from __future__ import annotations

import math
import re

import cadquery as cq

from . import board_geom as BG
from . import ui_panel as UP

HDR_H = 5.3                                   # HX PZ1.27 header off the board (VIEW_HEIGHT)
MOUTH = HDR_H - UP.IDC_PIN_IN                 # the socket's mating face off the board: 2.3
STUB = 12.0                                   # ribbon drawn past the socket
_FP = re.compile(r"PinHeader_2x(\d+)_P1\.27mm_Vertical")


def refs(board):
    """[(ref, ways per row)] of the board's 2 x N 1.27 vertical headers."""
    out = []
    for f in BG.load(board)["footprints"]:
        m = _FP.search(f["fpid"])
        if m and f.get("side", "F") == "F":
            out.append((f["ref"], int(m.group(1))))
    return out


def _one(board, ref, n):
    f = BG.footprint(board, ref)
    t = BG.load(board)["thickness_mm"]
    xs = [p[0] for p in f["pads"].values()]
    ys = [p[1] for p in f["pads"].values()]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    along_x = (max(xs) - min(xs)) >= (max(ys) - min(ys))          # the rows' direction
    L = n * 1.27 + 4.19
    body_h = UP.IDC_BODY_M
    z0 = t + MOUTH
    if along_x:
        dims = (L, UP.IDC_BODY_R)
    else:
        dims = (UP.IDC_BODY_R, L)
    body = cq.Workplane("XY").box(dims[0], dims[1], body_h).translate((cx, cy, z0 + body_h / 2.0))
    zc = z0 + body_h + UP.IDC_GAP
    cover = cq.Workplane("XY").box(dims[0], dims[1], UP.IDC_COVER_M).translate(
        (cx, cy, zc + UP.IDC_COVER_M / 2.0))
    # the ribbon: across the rows, away from the board's centre
    w = 2 * n * 0.635
    zr = z0 + UP.IDC_CABLE_M
    if along_x:
        s = 1.0 if cy >= 0 else -1.0
        y0 = cy - s * UP.IDC_BODY_R / 2.0
        rib = cq.Workplane("XY").box(w, UP.IDC_BODY_R + STUB, UP.RIBBON_T).translate(
            (cx, y0 + s * (UP.IDC_BODY_R + STUB) / 2.0, zr))
    else:
        s = 1.0 if cx >= 0 else -1.0
        x0 = cx - s * UP.IDC_BODY_R / 2.0
        rib = cq.Workplane("XY").box(UP.IDC_BODY_R + STUB, w, UP.RIBBON_T).translate(
            (x0 + s * (UP.IDC_BODY_R + STUB) / 2.0, cy, zr))
    return body.union(cover), rib


def parts(board):
    """{"socket": every IDC socket, "ribbon": every ribbon stub} in the board's own frame, or
    {} when the board has no 1.27 header."""
    sock = rib = None
    for ref, n in refs(board):
        s_, r_ = _one(board, ref, n)
        sock = s_ if sock is None else sock.union(s_)
        rib = r_ if rib is None else rib.union(r_)
    return {} if sock is None else {"socket": sock, "ribbon": rib}
