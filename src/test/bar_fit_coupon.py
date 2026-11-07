"""STEEL BAR FIT COUPON (2026-11-06): the wall bar's channel and pocket, short, at three clearances.

Steel in a printed channel is a new pair for this instrument, so the fit is proved on a coupon and
the real bar before any full-length part (the print-forgiving-fits rule). Cut the bar to length
first (26-1/2 in pre-cut -> dimensions.BAR_L, 26 in): the 12.7 offcut is the test piece, and the
whole bar can be tried in the same blocks.

Each STEP (row) is one clearance per side, BAR_CLR -0.05 / 0 / +0.05 over the bar as dimensioned
(5/8 x 2 in), numbered 1, 2, 3 from the TOP (+Y) of the plate down, every family alike: one V-notch
per step in the -X edge of the row's flange. Per row, two blocks, each printed the way its real part is:

  * RAIL (left): a 30 mm slice of the side rail, the channel along X, built +Z as the chassis is --
    the channel's 1.6 roof bridges the bar's thickness, as it does down the whole rail.
  * POCKET (right): an endplate's bar pocket, its axis up, built along it as both endplates build --
    the mouth is the last layer, as the endplates' inboard faces are.

WHAT TO REPORT: in each, does the bar (and the offcut) go in by hand, how much it rocks across Y
and in Z, and whether the roof sagged onto it. Zinc the offcut first if the bars will be zinced
(user: cold-galvanizing spray), so the coating is in the fit.

    py -3.12 -m src.test.bar_fit_coupon      # -> coupons/bar_fit.step in the main checkout
"""
from __future__ import annotations

import pathlib

import cadquery as cq

from src import dimensions as D
from src.helpers import box_at
from cadkit.orientation import PrintOrientation as PO
from cadkit.step_export import export_print

STEPS = (D.BAR_CLR - 0.05, D.BAR_CLR, D.BAR_CLR + 0.05)   # step 1 (top) .. 3
SKIN = (D.RAIL_T - D.BAR_CHAN_T) / 2.0                     # the rail's skin each side (1.86)
FLOOR = D.MIN_WALL_2P                                      # under the channel / pocket, and its roof
RAIL_L = 30.0                                              # the rail slice along X
POCKET_D = 16.0                                            # the pocket's depth: the offcut goes all in
ROW_P = D.RAIL_T + 6.0                                     # row pitch in Y
GAP = 6.0


def _tab(n, y, w):
    """The row's step tab: a two-bead flange off the rail block's -X end, with n V-notches in
    its -X edge (seen from above). The notches stay out of the blocks' thin roof and rims."""
    t = box_at(10.0, w, FLOOR, x=-5.0, y=y, z=FLOOR / 2)
    for k in range(n):
        yk = y + (k - (n - 1) / 2.0) * 4.0
        v = (cq.Workplane("XY").polyline([(-10.0, yk - 1.4), (-8.0, yk), (-10.0, yk + 1.4)])
             .close().extrude(FLOOR + 2.0).translate((0, 0, -1.0)))
        t = t.cut(v)
    return t


def coupon():
    plate = None
    for i, c in enumerate(STEPS):
        y = (len(STEPS) - 1 - i) * ROW_P                  # step 1 at the top (+Y)
        ct, cw = D.BAR_T + 2 * c, D.BAR_W + 2 * c
        # RAIL: channel along X, Z up
        h = cw + 2 * FLOOR
        w = ct + 2 * SKIN
        rail = box_at(RAIL_L, w, h, x=RAIL_L / 2, y=y, z=h / 2).cut(
            box_at(RAIL_L + 2.0, ct, cw, x=RAIL_L / 2, y=y, z=FLOOR + cw / 2))
        rail = rail.union(_tab(i + 1, y, w))
        # POCKET: axis up, 51.2 along X, mouth at the top
        x0 = RAIL_L + GAP
        px = cw + 2 * FLOOR
        ph = POCKET_D + FLOOR
        pk = box_at(px, w, ph, x=x0 + px / 2, y=y, z=ph / 2).cut(
            box_at(cw, ct, POCKET_D + 1.0, x=x0 + px / 2, y=y, z=FLOOR + (POCKET_D + 1.0) / 2))
        pk = pk.union(box_at(GAP + 1.0, w, FLOOR, x=x0 - GAP / 2, y=y, z=FLOOR / 2))   # one piece per row
        for b in (rail, pk):
            plate = b if plate is None else plate.union(b)
    return plate


if __name__ == "__main__":
    main = pathlib.Path(__file__).resolve().parents[2]
    if main.name.startswith("public-steel-guitar-"):          # a worktree: the main checkout's coupons/
        main = main.parent / "public-steel-guitar"
    out = main / "coupons" / "bar_fit.step"
    out.parent.mkdir(exist_ok=True)
    export_print(coupon(), PO(None, "models as printed: every block on its bed face"), str(out))
    bb = coupon().val().BoundingBox()
    print(out, "%.1f x %.1f x %.1f" % (bb.xlen, bb.ylen, bb.zlen), "steps", STEPS)
