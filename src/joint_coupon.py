"""Print coupon for the cadkit octagon ("stop-sign") slide joint — the joint the
knee levers use to key into the body.

Two small blocks, both printed -Z→+Z (the real lever/body orientation): one
grows the octagon TENON standing up, the other carries the MORTISE slot. Print
both, slide them together along X, and check the fit + that the mortise roof
bridged cleanly. It goes through the SAME `slide_joint` front door the levers
use — both halves face 'up' → the octagon family — so the coupon can't drift
from the real geometry.
"""

import cadquery as cq

from cadkit.joinery import PrintSpec, joint

NOZZLE = 0.8          # pedal-steel nozzle
WIDTH  = 6.0          # flat-to-flat room (well above the ~1.93 mm floor)
LENGTH = 14.0         # slide / engagement depth along X (the real load path)
CLR    = 0.1          # mortise↔tenon fit clearance (tenon is shrunk by this)
PLATE  = 4.0          # coupon base-plate / floor thickness
CEIL   = 3 * 0.8   # 2.4 (was 2.0)          # mortise ceiling over the roof = the printed bridge
MARGIN = 6.0          # material each side of the joint in Y

# both halves print -Z→+Z (facing 'up') → slide_joint picks the octagon family
_UP = PrintSpec(nozzle=NOZZLE, material="PETG-GF", facing="up")
_J = joint(WIDTH, LENGTH, tenon=_UP, mortise=_UP, clearance=CLR)
_H = _J.height                       # mortise depth above the mating plane


def tenon_coupon():
    """Base plate with the octagon tenon standing up (+z). Prints -Z→+Z: plate,
    then stem, then the 45° flare, narrowing to the roof."""
    plate = (cq.Workplane("XY")
             .box(LENGTH, WIDTH + 2 * MARGIN, PLATE, centered=(True, True, False))
             .translate((0, 0, -PLATE)))                       # z -PLATE..0
    ten = _J.tenon(root=1.0).translate((-LENGTH / 2.0, 0, 0))
    return plate.union(ten)


def mortise_coupon():
    """Block with the octagon mortise as a through-slot along X. Prints -Z→+Z; the
    thin ceiling over the slot is the one-nozzle bridge the shape is designed for."""
    block = (cq.Workplane("XY")
             .box(LENGTH, WIDTH + 2 * MARGIN, _H + PLATE + CEIL, centered=(True, True, False))
             .translate((0, 0, -PLATE)))                        # z -PLATE.._H+CEIL (ceiling = bridge)
    cut = (joint(WIDTH, LENGTH + 2, tenon=_UP, mortise=_UP, clearance=CLR)
           .mortise(drop=PLATE)
           .translate((-(LENGTH + 2) / 2.0, 0, 0)))             # slot open both X ends
    return block.cut(cut)


# ── SECTION-JOINT coupon (the LEG stack's octagon, width 28 — legs.SEC_W). The
# 6 mm knee coupon above does NOT validate the 28 mm section fit, so print this
# pair to check the leg stack's slide fit + one-bead roof bridge at the real size.
SEC_WIDTH, SEC_LEN, SEC_HEIGHT = 28.0, 28.0, 36.0   # keep = legs.SEC_W/_TEN_L/_H
_SJ = joint(SEC_WIDTH, SEC_LEN, tenon=_UP, mortise=_UP, clearance=CLR,
                  depth=SEC_HEIGHT)
_SH = _SJ.height


def section_tenon_coupon():
    """Base plate with the 28 mm section octagon tenon standing up (+z)."""
    plate = (cq.Workplane("XY")
             .box(SEC_LEN, SEC_WIDTH + 2 * MARGIN, PLATE, centered=(True, True, False))
             .translate((0, 0, -PLATE)))
    return plate.union(_SJ.tenon(root=1.0).translate((-SEC_LEN / 2.0, 0, 0)))


def section_mortise_coupon():
    """Block with the 28 mm section octagon mortise as a through-slot along X."""
    block = (cq.Workplane("XY")
             .box(SEC_LEN, SEC_WIDTH + 2 * MARGIN, _SH + PLATE + CEIL, centered=(True, True, False))
             .translate((0, 0, -PLATE)))
    cut = (joint(SEC_WIDTH, SEC_LEN + 2, tenon=_UP, mortise=_UP, clearance=CLR,
                       depth=SEC_HEIGHT)
           .mortise(drop=PLATE)
           .translate((-(SEC_LEN + 2) / 2.0, 0, 0)))
    return block.cut(cut)


# ── SLEEVE-COVER rail coupon: the leg sleeve cover's W5 octagon rails at the
# REAL geometry — built from legs.py's own helpers so the coupon can't drift.
def cover_seat_coupon():
    """40-long slice of the sleeve's thinned +Y face carrying both W5 rail
    slots. Print LYING like the real sleeve (slots open at the bed; the 0.8
    roof bridges at depth 5); slide cover_plate_coupon on along Z."""
    from .legs import _rail_groove, CVR_RAIL_X, SLV_FACE_Y, SQ_W
    blk = (cq.Workplane("XY")
           .box(SQ_W, 12.0, 40.0, centered=(True, True, False))
           .translate((0, SLV_FACE_Y - 6.0, 0)))
    for gx in (CVR_RAIL_X, -CVR_RAIL_X):
        blk = blk.cut(_rail_groove(42.0).translate((gx, 0, -1.0)))
    return blk


def cover_plate_coupon():
    """40-long slice of the cover: the 44-wide × COVER_T plate + both rails
    (no tongue). Prints lying on its outer face, rails up."""
    from .legs import _rail_tenon, CVR_RAIL_X, COVER_T, SQ_W
    b = (cq.Workplane("XY")
         .box(SQ_W, COVER_T, 40.0, centered=(True, True, False))
         .translate((0, SQ_W / 2 - COVER_T / 2, 0)))
    for gx in (CVR_RAIL_X, -CVR_RAIL_X):
        b = b.union(_rail_tenon(40.0).translate((gx, 0, 0)))
    return b
