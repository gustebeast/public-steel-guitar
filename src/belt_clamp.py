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

BELT_SLOT_CLR = 0.5                    # belt drop-in clearance in the slot

# ── this part prints on a FINE nozzle ────────────────────────────────────────
# The grid is a property of the PART, not the project (user). Everything the
# gripping face does happens at the GT2 tooth pitch -- 2.0 mm, with a 0.75 mm
# tooth height -- and a 0.8 bead cannot resolve a 0.75 mm ridge at 2.0 pitch:
# one bead per tooth IS the tooth, so the ridges come out as a smear and the
# mesh that stops the splice slipping stops existing. 0.2 gives 10 beads per
# pitch and ~4 across the ridge height, so the profile survives slicing.
# Consequence for MATING: a 0.2 grid is FINER, and every 0.8 length is a whole
# number of 0.2 beads, so anything inherited from the 0.8 world (D.BELT_*) is
# automatically legal here. The reverse would not be.
NOZZLE_D = 0.2                         # GT2 ridges; see above
B        = NOZZLE_D

LEN    = 110 * B                       # 22.0 along the belt (X) — laps several teeth
WIDTH  = D.BELT_W + 20 * B             # 9.0 across (Y)
HEIGHT = 40 * B                        # 8.0 Z
SLOT_H = D.BELT_T + D.BELT_TOOTH_H + BELT_SLOT_CLR   # belt back + teeth + clearance
SCREW_DX = 35 * B                      # 7.0 M2 squeeze screws
M2_CLR_D = 2.2                         # M2 clearance hole (a gap, not material)


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
