"""The motor connectors on the connector board (J11-J20), drawn as the screw-terminal PLUG.

MAX (Cixi Maixu) MX15EDGRC-3.5-04P header (LCSC C5188297) + its MX15EDGK-3.5-04P plug
(C5188251): the wires go into the plug and are clamped by M2 slotted screws (2.0 mm blade,
the instrument's one flat tool). KiCad's model for the land is Phoenix's MC 1,5/4-G-3.5 --
the HEADER only, a shrouded socket that reads as a JST in the render (user, 2026-11-14:
"they look like JSTs"). The plug is what a player sees and works on, so it is drawn here,
seated in each header, the way src/screw_terminal.py draws output_board's J8.

FROM THE MAKER'S DRAWINGS (as elec/connector_board.py and src/board_geom.py read them):
  * pitch 3.50; the plug 15.90 long, 5.30 of it inside the header; the header's open face
    5.9 from the pin row, so the plug's wire face is 16.5 from the pins
  * the mated pair 11.10 tall off the board
  * the plug's width: the header body's (the footprint's F.Fab), 15.0 for four ways
ESTIMATED (no plug drawing read for these -- check one pair):
  * the plug's underside 1.0 off the board outside the header
  * wire holes square 2.4, centre 4.0 above the plug's underside, 6.0 deep
  * screw wells O3.2, 3.0 deep, centred 4.5 behind the wire face; the M2 slotted head
    O3.0 x 1.0 in each well's bottom, slot 0.5 wide x 0.5 deep

THE WIRE FACE is the side of the pin row the header's body runs to (its F.Fab), read per
part, so it follows the placement (every J11-J20 faces -Y, the user's two rows).
"""
from __future__ import annotations

import cadquery as cq

from . import board_geom as BG

PREFIX = "MAX_MX15EDGRC-3.5-"
PITCH = 3.50
PLUG_L, PLUG_IN = 15.90, 5.30          # long; of which inside the header
FACE_FROM_PINS = 16.5                  # the plug's wire face from the pin row
MATED_H = 11.10
LIFT = 1.0                              # estimated: underside off the board outside the header
HOLE, HOLE_Z, HOLE_DEPTH = 2.4, 4.0, 6.0               # estimated
WELL_D, WELL_DEPTH, WELL_BACK = 3.2, 3.0, 4.5           # estimated
HEAD_D, HEAD_H, SLOT_W, SLOT_D = 3.0, 1.0, 0.5, 0.5     # estimated, M2 slotted


def _box(w, l, h, x, y, z):
    return cq.Workplane("XY").box(w, l, h).translate((x, y, z))


def refs(board):
    """The board's MX15EDGRC headers."""
    return [f["ref"] for f in BG.load(board)["footprints"] if f["fpid"].startswith(PREFIX)]


def _one(board, ref):
    """The plug in `ref`'s header, any quarter turn: the pads give the row's axis, the F.Fab
    (the header body) which side of the row the plug comes out on."""
    f = BG.footprint(board, ref)
    rot = float(f.get("rot") or 0.0) % 90.0
    assert min(rot, 90.0 - rot) < 1e-6, "%s %s is turned %s: quarter turns only" % (board, ref, f.get("rot"))
    t = BG.load(board)["thickness_mm"]
    P = list(f["pads"].values())
    xs, ys = [p[0] for p in P], [p[1] for p in P]
    along_x = (max(xs) - min(xs)) >= (max(ys) - min(ys))           # the pad row's axis
    fx0, fx1, fy0, fy1 = f["fab"]
    if along_x:
        row, a0, a1, c0, c1 = ys[0], fy0, fy1, fx0, fx1
    else:
        row, a0, a1, c0, c1 = xs[0], fx0, fx1, fy0, fy1
    s = -1.0 if (row - a0) > (a1 - row) else 1.0                     # the side the body runs to
    face = row + s * FACE_FROM_PINS
    mid = face - s * PLUG_L / 2.0
    cw = c1 - c0
    h = MATED_H - LIFT

    def at(u, v, z):                    # (across-row, along-row) -> board x, y
        return (v, u, z) if along_x else (u, v, z)

    def box(du, dv, dz, u, v, z):
        w_, l_ = (dv, du) if along_x else (du, dv)
        return _box(w_, l_, dz, *at(u, v, z))

    body = box(PLUG_L, cw, h, mid, (c0 + c1) / 2.0, t + LIFT + h / 2.0)
    metal = None
    for q in (xs if along_x else ys):
        body = body.cut(box(HOLE_DEPTH * 2.0, HOLE, HOLE, face, q, t + LIFT + HOLE_Z))
        wu = face - s * WELL_BACK
        z0 = t + MATED_H - WELL_DEPTH
        x_, y_, _ = at(wu, q, 0.0)
        body = body.cut(cq.Workplane("XY").circle(WELL_D / 2.0).extrude(WELL_DEPTH).translate((x_, y_, z0)))
        head = cq.Workplane("XY").circle(HEAD_D / 2.0).extrude(HEAD_H).translate((x_, y_, z0))
        head = head.cut(box(HEAD_D + 0.2, SLOT_W, SLOT_D * 2.0, wu, q, z0 + HEAD_H))
        metal = head if metal is None else metal.union(head)
    return body, metal


def parts(board="connector_board"):
    """{"housing": every plug's body, "metal": every screw head} in the board's own frame."""
    housing = metal = None
    for ref in refs(board):
        b, m = _one(board, ref)
        housing = b if housing is None else housing.union(b)
        metal = m if metal is None else metal.union(m)
    return {"housing": housing, "metal": metal}
