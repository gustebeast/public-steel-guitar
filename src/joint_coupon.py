"""Print coupons for the LEG stack's slide joints (cadkit octagon family).

The 28 mm section-joint pair checks the leg stack's slide fit and its one-bead roof
bridge at the real size; the sleeve-cover pair checks the W5 cover rails. (The small
knee-lever octagon coupon that used to live here was removed, user 2026-09-11.)
"""

import cadquery as cq

from cadkit.joinery import PrintSpec, joint

NOZZLE_D = 0.8            # pedal-steel nozzle; the coupon's bead grid
CLR    = 0.1              # mortise↔tenon fit clearance (tenon is shrunk by this)
PLATE  = 4.0              # coupon base-plate / floor thickness
CEIL   = 3 * NOZZLE_D     # 2.4 mortise ceiling over the roof = the printed bridge
MARGIN = 8 * NOZZLE_D     # 6.4 material each side of the joint in Y

# both halves print -Z→+Z (facing 'up') → slide_joint picks the octagon family
_UP = PrintSpec(nozzle=NOZZLE_D, material="PETG-GF", facing="up")


# ── SECTION-JOINT coupon (the LEG stack's octagon, width 28 — legs.SEC_W): print this
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
