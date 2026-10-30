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
  -Z     the LEDGE: a post off the floor that J3's housing comes down on -- see below.

THE -Z STOP IS A LEDGE UNDER J3 (2026-10-29). The laminate's bottom edge stands 0.34 above the
body's underside (its Z is the user's: the bus-B plugs must be squeezable from outside), so no
printed ledge fits under the board itself, and the R1 outline has no hole or shoulder to hang
it by. It used to rest on the -X/-Y body adapter (legs on only), but the board sits flush on
string 1's motor (user: "the further +y the better") and the motors came 9.7 +Y with the 7.5
standoff while the -Y rail did not, so the adapter is no longer under it. J3 is the lowest
through-hole housing whose drop path is clear: a 6-way XH, so the load goes into six soldered
pins, not an SMD joint (J1 sits over J2, which drops through the room a post would need). The
post stands under the HOUSING only, LEDGE_IN short of its mated plug, whose wires leave +X.
It works with the legs off too. R2 (lead): a laminate shoulder on a bare edge replaces it.

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
LEDGE_REF = "J3"                  # the through-hole housing the board comes to rest on
LEDGE_IN = 0.5                    # the post stops this far inside the housing's mating face


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
    out.append(_ledge())
    for bx in out:
        assert bx[5] - bx[4] >= 4 * B, (
            "a motor-controller guide (x %.2f..%.2f, y %.2f..%.2f) is only %.2f tall: a part "
            "on the board sweeps the rest of it" % (bx[0], bx[1], bx[2], bx[3], bx[5] - bx[4]))
    return out


def ledge_target():
    """J3's housing in world, as (x0, x1, y0, y1, z0, z1): the header alone, off the board's
    own fab box and the footprint's height, not the mated plug past it."""
    from . import board_geom as BG
    g = BG.load("motor_ctrl")
    f = next(f for f in g["footprints"] if f["ref"] == LEDGE_REF)
    assert "THT" in f["fpid"] or "B6B-XH-A" in f["fpid"], (
        f"the motor controller's -Z ledge must bear on a through-hole part, not {f['fpid']}")
    h = BG.BOARDS.HEIGHT[BG.fp_name(f["fpid"])]
    o, ax = EL.board_frame("motor_ctrl")
    fx0, fx1, fy0, fy1 = f["fab"]
    pts = [tuple(o[k] + ax[0][k] * a + ax[1][k] * b + ax[2][k] * c for k in range(3))
           for a in (fx0, fx1) for b in (fy0, fy1) for c in (0.0, h)]
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    x1 = _laminate()[1]
    return x1, hi[0], lo[1], hi[1], lo[2], hi[2]


def _ledge():
    """The post J3 comes down on: off the floor top, up to the housing's underside, under the
    housing only, FIT off the laminate. Its Y run is the longest stretch under the housing
    that nothing seated BELOW J3 uses -- each such part slides down through that band on the
    way in (J6's plug overlaps the housing's -Y end)."""
    hx0, hx1, hy0, hy1, hz0, _hz1 = ledge_target()
    free = [(hy0 + FIT, hy1 - FIT)]
    for p in _parts(+1):
        if p.zmax > hz0 + 1e-6:
            continue
        a, b = p.ymin - SWEEP_CLR, p.ymax + SWEEP_CLR
        free = [seg for lo, hi in free
                for seg in ((lo, min(hi, a)), (max(lo, b), hi)) if seg[1] > seg[0]]
    assert free, f"every part of {LEDGE_REF}'s housing has a part under it"
    ya, yb = max(free, key=lambda r: r[1] - r[0])
    x0, x1 = hx0 + FIT, hx1 - LEDGE_IN
    assert yb - ya >= 4 * B and x1 - x0 >= 4 * B, (
        f"the motor controller's ledge under {LEDGE_REF} is only {x1 - x0:.2f} x {yb - ya:.2f}: "
        f"the parts under the housing take the rest")
    return (x0, x1, ya, yb, MB.FLOOR_TOP, hz0)


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
