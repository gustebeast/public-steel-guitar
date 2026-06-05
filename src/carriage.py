"""Carriage (×10) — PA6-GF, load-critical (§8 item 1).

The moving element. Rides the guide rod (anti-rotation), presses the round
leadscrew nut into its pocket, and anchors the string ball-end. Tension path:
string → carriage → nut → screw → support bearing.

NARROW by design: at the tight string pitch the carriage must stay slim. It is
sized so it clears its neighbours, and the guide rod runs directly BELOW the
screw (same Y, Z = GUIDE_ROD_DZ) so it never lands on a neighbour's screw line.

Local frame (build.py adds each string's Y and bank X): origin on the SCREW
axis; screw axis along ±X. Guide bore at Z=GUIDE_ROD_DZ. The string exits the
−X face toward the bridge/nut; the ball-end anchor post rises to the string
height (BRIDGE_TOP_Z).

Print orientation: lay the part so the string-tension axis (X) runs ALONG the
layer lines (print on a side face), never pulling across layers.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl_x, box_at

# ── local geometry constants ─────────────────────────────────────────────
# Across-width is set by the nut + thin walls. Compact: ~9 mm so 10 carriages
# sit INLINE at the 9.5 mm changer pitch (no bank). Standard: wider, banked.
WALL            = 1.0 if D.COMPACT else 1.75
WIDTH           = D.NUT_OD + 2 * WALL       # across the strings (Y)
ALONG           = 9.0                       # along the screw axis (X)
Z_TOP           = 6.0                       # block top (above the screw)
Z_BOT           = D.GUIDE_ROD_DZ - D.GUIDE_ROD_D / 2 - 2.0   # below the guide rod
BODY_Z          = Z_TOP - Z_BOT
BODY_ZC         = (Z_TOP + Z_BOT) / 2

NUT_POCKET_D    = D.NUT_OD + 0.2          # press pocket for the round nut
SCREW_CLR_D     = D.SCREW_OD + 1.0
GUIDE_CLR_D     = D.GUIDE_ROD_D + D.FIT_CLR

BALL_D          = 3.8       # string ball-end pocket diameter
STRING_SLOT_W   = 1.2       # string exit slot width
ANCHOR_W        = min(7.0, WIDTH - 1.0)   # anchor post across-width (Y)
ANCHOR_DEPTH    = 6.0       # anchor post along-X depth (toward the nut)
ANCHOR_TOP_Z    = D.BRIDGE_TOP_Z   # post rises to string height


def _build() -> cq.Workplane:
    # Main body, centred on the screw axis in X/Y; spans screw→guide in Z.
    body = box_at(ALONG, WIDTH, BODY_Z, x=0, y=0, z=BODY_ZC)

    # Nut press-pocket on the +X face (round nut, seat lip bears on the face).
    body = body.cut(cyl_x(NUT_POCKET_D, D.NUT_BODY_LEN,
                          x0=ALONG / 2 - D.NUT_BODY_LEN + 0.01, y=0, z=0))
    # Screw clearance the rest of the way through (so the screw passes).
    body = body.cut(cyl_x(SCREW_CLR_D, ALONG + 2, x0=-ALONG / 2 - 1, y=0, z=0))

    # Guide-rod bore directly below the screw (anti-rotation), axis X.
    body = body.cut(cyl_x(GUIDE_CLR_D, ALONG + 2,
                          x0=-ALONG / 2 - 1, y=0, z=D.GUIDE_ROD_DZ))

    # String ball-end anchor post on the −X face, rising to string height.
    post_top_z = ANCHOR_TOP_Z + 3.0
    post_bot_z = BODY_ZC
    post = box_at(ANCHOR_DEPTH, ANCHOR_W, post_top_z - post_bot_z,
                  x=-ALONG / 2 - ANCHOR_DEPTH / 2, y=0, z=(post_top_z + post_bot_z) / 2)
    body = body.union(post)
    # ball pocket drilled +X into the post from the −X face at string height
    body = body.cut(cyl_x(BALL_D, 5.0,
                          x0=-ALONG / 2 - ANCHOR_DEPTH - 0.5, y=0, z=ANCHOR_TOP_Z))
    # thin string-exit slot continuing −X at string height
    body = body.cut(box_at(8.0, STRING_SLOT_W, STRING_SLOT_W + 1.0,
                           x=-ALONG / 2 - ANCHOR_DEPTH, y=0, z=ANCHOR_TOP_Z))
    # set-screw insert pocket: vertical hole from the post top down to the ball
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        D.M3_INSERT_D / 2, post_top_z - ANCHOR_TOP_Z + 0.5,
        pnt=cq.Vector(-ALONG / 2 - ANCHOR_DEPTH / 2, 0, ANCHOR_TOP_Z - 0.5),
        dir=cq.Vector(0, 0, 1))))
    return body


carriage = _build()
