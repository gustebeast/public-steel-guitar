"""Carriage (×10) — PA6-GF, load-critical (§8 item 1).

The moving element, riding a VERTICAL leadscrew (axis Z) — it travels in Z. It
presses the round nut into its pocket, rides the guide rod (anti-rotation), and
anchors the string ball-end directly under the roller, reaching +X over the
screw to do so. Tension path: string → carriage → nut → screw → support bearing.

Local frame: origin on the SCREW axis (axis Z). The nut presses in from below;
the guide bore is at X=−GUIDE_ROD_DX; the string ball-end anchor is at
X=+ANCHOR_DX (under the roller), opening +Z so the string runs up to the roller.

Print orientation: the string-tension axis is Z; lay the part so that runs along
the layer lines.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, box_at

THICK   = 12.0                              # Z height
WIDTH   = D.NUT_OD + 2 * 1.0               # across (Y), ≤ string pitch
X_LO    = -D.GUIDE_ROD_DX - 3.0            # past the guide rod (−X)
X_HI    = D.ANCHOR_DX + 3.0                # past the anchor (+X)
BODY_X  = X_HI - X_LO
BODY_XC = (X_HI + X_LO) / 2

NUT_POCKET_D = D.NUT_OD + 0.2
SCREW_CLR_D  = D.SCREW_OD + 1.0
GUIDE_CLR_D  = D.GUIDE_ROD_D + D.FIT_CLR
BALL_D       = 3.8
STRING_SLOT_W = 1.2
ANCHOR_POST_H = 6.0                        # thin post above the body to the roller


def _build() -> cq.Workplane:
    body = box_at(BODY_X, WIDTH, THICK, x=BODY_XC, y=0, z=0)

    # Screw clearance through (axis Z) at the origin.
    body = body.cut(cyl(SCREW_CLR_D, THICK + 2, z=-THICK / 2 - 1))
    # Nut press-pocket from the bottom face (seat lip bears on the bottom).
    body = body.cut(cyl(NUT_POCKET_D, D.NUT_BODY_LEN, z=-THICK / 2 - 0.01))
    # Guide-rod bore (anti-rotation), axis Z, offset −X.
    body = body.cut(cyl(GUIDE_CLR_D, THICK + 2, z=-THICK / 2 - 1)
                    .translate((-D.GUIDE_ROD_DX, 0, 0)))

    # Thin anchor POST rising from the body top to near the roller (so only the
    # slim post nears the roller, not the full body). String ball-end anchors in
    # its top, opening +Z (the string runs up to the roller).
    post_top = THICK / 2 + ANCHOR_POST_H
    body = body.union(box_at(6.0, WIDTH, ANCHOR_POST_H,
                             x=D.ANCHOR_DX, y=0, z=THICK / 2 + ANCHOR_POST_H / 2))
    body = body.cut(cyl(BALL_D, 5.0, z=post_top - 5.0).translate((D.ANCHOR_DX, 0, 0)))
    body = body.cut(box_at(STRING_SLOT_W, STRING_SLOT_W + 1.0, 6.0,
                           x=D.ANCHOR_DX, y=0, z=post_top - 1.0))
    return body


carriage = _build()
