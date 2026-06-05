"""Belt splice clamp (×10) — PETG.

Closes each cut-to-length open GT2 belt into a loop. The two cut ends lap inside
the clamp teeth-to-teeth; toothed inner faces mesh the belt teeth so the joint
can't slip under the (small) move tension, and 2× M2 screws squeeze them. Printed
as a two-plate clamp (print this piece twice per splice); modelled here as the
assembled envelope. It sits in a free span of the belt — never on a pulley.

Local frame: the belt runs along X through the centre; +Z up. build.py places one
at the midpoint of each belt's run.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, box_at

LEN   = 22.0                       # along the belt (X) — laps several teeth each side
WIDTH = D.BELT_W + 2.0             # across (Y), < string pitch
HEIGHT = 8.0                       # Z
SLOT_H = 2 * D.BELT_T + 0.6        # captures the two lapped belt layers
SCREW_DX = 6.0                     # M2 squeeze screws
M2_CLR_D = 2.2


def _build() -> cq.Workplane:
    body = box_at(LEN, WIDTH, HEIGHT)
    # belt pass-through slot (lapped ends) along X
    body = body.cut(box_at(LEN + 2, D.BELT_W + 0.4, SLOT_H, x=0, y=0, z=0))
    # 2× M2 squeeze screws (through Z)
    for sx in (-SCREW_DX, SCREW_DX):
        body = body.cut(cyl(M2_CLR_D, HEIGHT + 2, z=-HEIGHT / 2 - 1).translate((sx, 0, 0)))
    return body


belt_clamp = _build()
