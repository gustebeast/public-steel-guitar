"""Belt splice clamp (×10) — PETG.

Closes each cut-to-length open GT2 belt into a loop. The belt lies flat in the
clamp (the clamp forces a non-twisting section) with its teeth up; the clamp's
gripping face has matching GT2 ridges that mesh the belt teeth so the joint can't
slip under the (small) move tension, and 2× M2 screws squeeze them. Printed as a
two-plate clamp (print this piece twice per splice). It sits in run B's flat zone
— never on a pulley; build.py orients it to the belt via components.splice_frame.

Local frame: the belt runs along X with its teeth facing +Z; +Z up.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, box_at

LEN    = 22.0                          # along the belt (X) — laps several teeth
WIDTH  = D.BELT_W + 4.0                # across (Y)
HEIGHT = 8.0                           # Z
SLOT_H = D.BELT_T + D.BELT_TOOTH_H + 0.5   # belt back + teeth + clearance
SCREW_DX = 7.0                         # M2 squeeze screws
M2_CLR_D = 2.2


def _build() -> cq.Workplane:
    body = box_at(LEN, WIDTH, HEIGHT)
    # belt pass-through slot along X (belt back rests on the floor, teeth up)
    body = body.cut(box_at(LEN + 2, D.BELT_W + 0.5, SLOT_H, x=0, y=0, z=0))
    # GT2 ridges on the slot's upper face, meshing the belt teeth (axis Y)
    n_teeth = int((LEN - 3) / D.BELT_PITCH)
    x0 = -(n_teeth - 1) * D.BELT_PITCH / 2
    for k in range(n_teeth):
        x = x0 + k * D.BELT_PITCH
        body = body.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            D.BELT_TOOTH_H, D.BELT_W, pnt=cq.Vector(x, -D.BELT_W / 2, SLOT_H / 2),
            dir=cq.Vector(0, 1, 0))))
    # 2× M2 squeeze screws (through Z)
    for sx in (-SCREW_DX, SCREW_DX):
        body = body.cut(cyl(M2_CLR_D, HEIGHT + 2, z=-HEIGHT / 2 - 1).translate((sx, 0, 0)))
    return body


belt_clamp = _build()
