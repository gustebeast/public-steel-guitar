"""Bottom screw-support rail (×1, shared) — PA6-GF (§8 item 2).

The 10 vertical screws' bottom supports live in ONE rail spanning the field at
the screw line (X=SCREW_X). Each station is a Ø8 bushing/MR85 seat (radial) with
a top ledge that backs the thrust washer against the screw's UPWARD pull (the
string pulls each carriage toward its bridge bearing, +Z). A single rail avoids
the overlapping per-screw cradles that 10 separate holders would create at
9.5 mm pitch. Built in global position.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, box_at

ACROSS  = 2 * D.BRIDGE_AXLE_Y              # ends reach the bridge uprights + chassis rail
DEPTH   = 14.0                             # along X
HEIGHT  = D.SUPPORT_BRG_W + 5.0            # Z
SEAT_LEDGE_D = D.SUPPORT_BRG_OD - 2.5      # top-ledge bore (< OD, backs the washer)


def _build() -> cq.Workplane:
    body = box_at(DEPTH, ACROSS, HEIGHT, x=D.SCREW_X, y=0, z=D.SUPPORT_BRG_Z)
    for i in range(D.N_STRINGS):
        y = D.string_y(i)
        # bushing seat: counterbore from the bottom (−Z) up by the bushing width
        body = body.cut(cyl(D.SUPPORT_BRG_OD + 0.2, D.SUPPORT_BRG_W + 0.3,
                            z=D.SUPPORT_BRG_Z - HEIGHT / 2 - 0.01)
                        .translate((D.SCREW_X, y, 0)))
        # screw/washer clearance through the top ledge
        body = body.cut(cyl(SEAT_LEDGE_D, HEIGHT + 2, z=D.SUPPORT_BRG_Z - HEIGHT / 2 - 1)
                        .translate((D.SCREW_X, y, 0)))
    return body


screw_rail = _build()
