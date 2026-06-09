"""Carriage (×10) — PA6-GF, load-critical (§8 item 1).

The moving element, riding a VERTICAL leadscrew (axis Z) — it travels in Z. It
presses the round nut into its pocket, rides the guide rod (anti-rotation), and
anchors the string ball-end directly under the bridge bearing, reaching +X over
the screw to do so. Tension path: string → carriage → nut → screw → support brg.

Local frame: origin on the SCREW axis (axis Z). The nut presses in from below;
the string ball-end anchor is at X=+ANCHOR_DX (under the bridge bearing),
opening +Z so the string runs up to it. The guide bore lives in a low FOOT
(column + leg hanging below the plate at the +X end): the rod sits below the
stringing window, so the window stays clear, and the foot's top/bottom faces
are the hard-stop contacts against the endplate's two guide ledges.

Print orientation: the string-tension axis is Z; lay the part so that runs along
the layer lines.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, cyl_y, box_at

THICK   = 12.0                              # Z height
WIDTH   = D.NUT_OD + 2 * 1.0               # across (Y), ≤ string pitch
NUT_POCKET_D = D.NUT_OD + 0.2
X_LO    = -(NUT_POCKET_D / 2 + 2.0)        # wall past the nut pocket (−X)
X_HI    = D.ANCHOR_DX + 0.5                # plate stops at +0.5 global: the upper
                                           # guide ledge (X ≥ +1) sweeps past it
BODY_X  = X_HI - X_LO
BODY_XC = (X_HI + X_LO) / 2

# Guide foot: column down from the plate's +X end, then a leg reaching +X under
# the upper ledge to the rod line. Foot top = D.GUIDE_FOOT_DZ (the top-stop face).
COL_X0, COL_X1   = 4.5, X_HI               # column: clear of the screw bore / ledge
FOOT_X0, FOOT_X1 = 6.5, 13.5               # leg: −X face clears the belt wrap, +X
                                           # face stops 0.5 shy of the cap face
SCREW_CLR_D  = D.SCREW_OD + 1.0
GUIDE_CLR_D  = D.GUIDE_ROD_D + D.FIT_CLR
NUT_SEAT_D    = D.STRING_NUT_D + 0.4       # transverse (Y) seat for the string-end cylinder nut
# +Z hole the string exits through — must clear the heaviest string (C6 .070 ≈ 1.8 mm)
# and leave room to bend it in. Still < the Ø3.5 nut, so the nut is captured.
STRING_SLOT_W = 2.6
ANCHOR_POST_H = 7.0                        # post above the body — roofs over the nut seat
SEAT_Z        = THICK / 2 + D.STRING_NUT_D / 2 + 0.6   # nut-seat centre, above the body top


def _build() -> cq.Workplane:
    body = box_at(BODY_X, WIDTH, THICK, x=BODY_XC, y=0, z=0)

    # Screw clearance through (axis Z) at the origin.
    body = body.cut(cyl(SCREW_CLR_D, THICK + 2, z=-THICK / 2 - 1))
    # Nut press-pocket from the bottom face (seat lip bears on the bottom).
    body = body.cut(cyl(NUT_POCKET_D, D.NUT_BODY_LEN, z=-THICK / 2 - 0.01))

    # Guide FOOT: column + leg below the plate, guide bore through the leg.
    col_h = -D.GUIDE_FOOT_DZ - THICK / 2                   # plate bottom → foot top
    body = body.union(box_at(COL_X1 - COL_X0, WIDTH, col_h,
                             x=(COL_X0 + COL_X1) / 2, y=0,
                             z=-THICK / 2 - col_h / 2))
    body = body.union(box_at(FOOT_X1 - FOOT_X0, WIDTH, D.GUIDE_FOOT_H,
                             x=(FOOT_X0 + FOOT_X1) / 2, y=0,
                             z=D.GUIDE_FOOT_DZ - D.GUIDE_FOOT_H / 2))
    body = body.cut(cyl(GUIDE_CLR_D, D.GUIDE_FOOT_H + 2,
                        z=D.GUIDE_FOOT_DZ - D.GUIDE_FOOT_H - 1)
                    .translate((D.GUIDE_ROD_DX, 0, 0)))

    # Anchor POST rising from the body top toward the bridge bearing. The
    # string-end cylinder NUT (axis Y) slots into a transverse seat in it; the
    # string runs +Z out through a slot too narrow for the nut, so the string
    # pull seats the nut UP against the roof (mechanical capture, no clamp). The
    # nut loads from the +X (open-endplate) side.
    body = body.union(box_at(8.0, WIDTH, ANCHOR_POST_H,
                             x=D.ANCHOR_DX, y=0, z=THICK / 2 + ANCHOR_POST_H / 2))
    # transverse seat for the cylinder nut
    body = body.cut(cyl_y(NUT_SEAT_D, WIDTH + 2, y0=-(WIDTH / 2 + 1),
                          x=D.ANCHOR_DX, z=SEAT_Z))
    # +X loading mouth — opens the seat to the +X face so the nut slides in
    body = body.cut(box_at(5.0, D.STRING_NUT_L + 0.6, NUT_SEAT_D,
                           x=D.ANCHOR_DX + 3.0, y=0, z=SEAT_Z))
    # +Z string slot up through the roof (narrower than the nut → captures it)
    body = body.cut(box_at(STRING_SLOT_W, STRING_SLOT_W + 0.6, ANCHOR_POST_H,
                           x=D.ANCHOR_DX, y=0, z=SEAT_Z + ANCHOR_POST_H / 2))
    # funnel lead-in at the top of the hole so the string threads/bends in cleanly
    post_top = THICK / 2 + ANCHOR_POST_H
    funnel = cq.Workplane("XY").add(cq.Solid.makeCone(
        STRING_SLOT_W / 2, STRING_SLOT_W, 2.5,
        cq.Vector(D.ANCHOR_DX, 0, post_top - 2.5), cq.Vector(0, 0, 1)))
    body = body.cut(funnel)
    return body


carriage = _build()
