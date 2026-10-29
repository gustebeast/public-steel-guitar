# -*- coding: utf-8 -*-
"""THE MOTOR CONTROLLER'S RETENTION: edge guides it slides down, + to - Z, and nothing else.

It replaces the old tray `_frame` (electronics.keyhead_cradles), which was shaped for the
endplate the board used to hang on: a ring and a locating wall round the whole outline, with a
45 deg lean over the board's face, because the endplate printed along world +X and anything
reaching over a board was a ceiling. In the chassis, which prints +Z, a board standing in YZ
needs no lean at all -- every face a guide can touch is a WALL in the print. The user
(2026-10-29): "They use 45 angles but don't need to with the print orientation... The goal is
to allow the board to slide in from + to - z but not move on any other axis... the hardware
needs to clear the support material along that range of motion."

WHAT HOLDS EACH AXIS, read off the board as it stands (electronics.motor_ctrl(), mated):
  -Y     the -Y EDGE CHANNEL's back wall, MCTRL_FIT off the laminate's -Y edge.
  +Y     string 1's motor: the board sits flush on its back face, MOTOR_CLR off (the bay's back
         wall was dropped for it, motor_bank.back_wall_x0).
  X      the channel's two cheeks over the -Y edge, the +Y GUIDE's two cheeks over the +Y edge,
         and the floor port along the bottom edge. Three lines round the board, so it cannot
         swing about the channel (a lone edge slot is a hinge) or rock about its bottom edge.
  +Z     the top panel's capture rib, MCTRL_CAP_GAP over the top edge (top_plate._mctrl_capture).
  -Z     ⚠ NOT IN THE CHASSIS -- see below.

⚠ THE -Z STOP IS THE -X/-Y BODY ADAPTER, AND ONLY WITH THE LEG ON. The laminate's bottom edge
stands 0.34 above the body's underside (its Z is the user's: the bus-B plugs must be squeezable
from outside), so there is no room for a printed ledge under it. The adapter's top face already
lies under the laminate's -Y end; build.py asserts it does. It cannot grow +Y to take more of
the edge: it prints +Y face on the bed (leg_stack.ADAPTER_UP, user). Legs off, nothing but the
cables and the plugs resting on a table stop the board dropping -- INSTALL_NOTES says so.
R2 (lead, 2026-10-29): bronner adds a laminate shoulder on a bare edge at mid-height; the
channel's cheeks are where a ledge goes then -- a block across the channel under the shoulder.

EVERY GUIDE IS CLEAR OF THE WHOLE STROKE, not just the final pose. The board drops in from
above, so a part on its face sweeps everything ABOVE its seated position; a guide may stand in
a part's Y band only BELOW that part. Each cheek's top is read off the board's own parts (the
mated plugs included), and `swept_clear` checks the result with each guide swept the length of
the stroke.
"""
from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from . import electronics as EL
from . import motor_bank as MB
from .helpers import box_at

B = D.BEAD
FIT = D.MCTRL_FIT                 # 0.3: board to printed guide, every guide face
CHEEK_T = 2 * B                   # each cheek across the board (X)
BACK_T = 3 * B                    # the channel's back wall (Y), the -Y stop
EDGE_E = 2 * B                    # how far the -Y cheeks lap the laminate's face
GUIDE_E_NEG = 7 * B               # the +Y guide's -X cheek: that face is bare 6.3 in
GUIDE_E_POS = 2 * B               # its +X cheek: a part stands 2.2 in from the edge
GUIDE_H = 10 * B                  # the +Y guide's cheeks: low posts off the floor
SWEEP_CLR = 0.4                   # guide to any part that slides past it


def _laminate():
    x0, x1, y0, y1, ztop = EL.mctrl_capture_target()
    return x0, x1, y0, y1, ztop - EL.MCTRL_BOARD_X, ztop


def _parts(face):
    """The board's own solids proud of one face (`+1` = +X, `-1` = -X), as bounding boxes."""
    x0, x1, *_ = _laminate()
    xa, xb = (x1 + 0.01, x1 + 40.0) if face > 0 else (x0 - 40.0, x0 - 0.01)
    side = EL.motor_ctrl().intersect(box_at(xb - xa, 200.0, 200.0, x=(xa + xb) / 2.0,
                                            y=-55.0, z=-50.0))
    return [s.BoundingBox() for s in side.val().Solids()]


def _top_under_parts(face, ya, yb, zmax):
    """The highest a guide in Y band ya..yb on `face` may stand: below every part in that band
    (each one sweeps everything above where it seats)."""
    z = zmax
    for p in _parts(face):
        if p.ymin < yb + SWEEP_CLR and p.ymax > ya - SWEEP_CLR:
            z = min(z, p.zmin - SWEEP_CLR)
    return z


def _boxes():
    """The guides as (x0, x1, y0, y1, z0, z1) -- boxes so the stroke sweep is exact."""
    x0, x1, y0, y1, zb, zt = _laminate()
    # ROOTED ON THE BED, not on the floor top: the floor port clears the laminate by
    # MCTRL_PORT_CLR (0.5) and a guide by FIT (0.3), so a guide standing on the floor top
    # overhangs the port by 0.2 -- four ledges in print_check. Down to the bed, each guide
    # fills its side of the port to FIT and is a wall from layer one.
    zf = CH.Z_BOT
    zg = MB.FLOOR_TOP                                # the +Y posts' height is off the floor
    nx0, nx1 = x0 - FIT - CHEEK_T, x0 - FIT          # the -X cheeks
    px0, px1 = x1 + FIT, x1 + FIT + CHEEK_T          # the +X cheeks
    out = []
    # ── the -Y EDGE CHANNEL: back wall + two cheeks, floor to the board's top edge ──
    cy0, cy1 = y0 - FIT, y0 + EDGE_E
    out.append((nx0, px1, cy0 - BACK_T, cy0, zf, zt))                       # back wall
    out.append((nx0, nx1, cy0, cy1, zf, _top_under_parts(-1, cy0, cy1, zt)))
    out.append((px0, px1, cy0, cy1, zf, _top_under_parts(+1, cy0, cy1, zt)))
    # ── the +Y GUIDE: two low cheeks off the floor, inside the board's +Y edge ──
    # Not past it: string 1's motor is MOTOR_CLR beyond that edge, the whole bottom of it.
    out.append((nx0, nx1, y1 - GUIDE_E_NEG, y1, zf,
                _top_under_parts(-1, y1 - GUIDE_E_NEG, y1, zg + GUIDE_H)))
    out.append((px0, px1, y1 - GUIDE_E_POS, y1, zf,
                _top_under_parts(+1, y1 - GUIDE_E_POS, y1, zg + GUIDE_H)))
    for bx in out:
        assert bx[5] - bx[4] >= 4 * B, (
            "a motor-controller guide (x %.2f..%.2f, y %.2f..%.2f) is only %.2f tall: a part "
            "on the board sweeps the rest of it" % (bx[0], bx[1], bx[2], bx[3], bx[5] - bx[4]))
    return out


def _box(b, dz0=0.0):
    x0, x1, y0, y1, z0, z1 = b
    return box_at(x1 - x0, y1 - y0, z1 - (z0 - dz0),
                  x=(x0 + x1) / 2.0, y=(y0 + y1) / 2.0, z=(z1 + z0 - dz0) / 2.0)


def retention() -> cq.Workplane:
    """The guides, in WORLD, ready to fuse into the chassis segment that holds them."""
    out = None
    for b in _boxes():
        out = _box(b) if out is None else out.union(_box(b))
    return out


def swept_clear() -> float:
    """mm3 of the board, at any point of its drop, inside a guide: each guide grown DOWN by the
    stroke is the set of points that meet it while the board slides up and out."""
    stroke = 200.0
    board = EL.motor_ctrl()
    v = 0.0
    for b in _boxes():
        try:
            v += board.intersect(_box(b, stroke)).val().Volume()
        except Exception:
            pass
    return v
