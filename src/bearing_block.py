"""Leadscrew bearing cradle (×10) — PA6-GF (§8 item 2).

OPEN holder, not an enclosing bore. With no belt the bearing load is almost
purely AXIAL (the string pulls the screw −Y), so the bearing only needs a −Y
backstop face (compression — strong even thin) plus light radial cradling.

To let ALL screws share one Z plane, the holder grips the bearing from BELOW
the screw plane: a saddle under the bearing (bulk at Z < −screw_r) plus a thin
−Y backstop ring. At the screw plane (Z≈0) the only thing in the field is the
bearing's own OD, so a neighbour screw 9.5 mm away clears it by ~1.5 mm.

Local frame: screw axis +Y through the origin; the bearing nests centred at the
ORIGIN (Y=0, Z=0). The backstop is just −Y of it. build.py places the holder at
the bearing's centre.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl_y, box_at

RB          = D.SUPPORT_BRG_OD / 2
BACKSTOP_T  = 2.0                          # −Y backstop thickness (Y)
BACKSTOP_LIP = 1.5                         # radial overlap onto the outer race
BLK_Y       = D.SUPPORT_BRG_W + BACKSTOP_T   # holder Y depth
SADDLE_W    = 2 * (RB + 1.5)                 # cups the bearing (below the screws)
BLK_X       = SADDLE_W                       # (exported for reference)
SADDLE_TOP_Z = -(D.SCREW_OD / 2 + 1.0)       # holder stays below the screw plane
Z_BOT       = -(RB + 3.0)

# Y spans (bearing centred at Y=0):
_BRG_Y0     = -D.SUPPORT_BRG_W / 2            # bearing −Y face
_BACK_Y0    = _BRG_Y0 - BACKSTOP_T           # backstop −Y face


def _build() -> cq.Workplane:
    # Saddle: a block beneath the bearing, spanning the backstop+bearing Y, with
    # a trough scooped out so the bearing's lower arc nests in it.
    saddle = box_at(SADDLE_W, BLK_Y, SADDLE_TOP_Z - Z_BOT,
                    x=0, y=(_BACK_Y0 + D.SUPPORT_BRG_W / 2) / 2,
                    z=(SADDLE_TOP_Z + Z_BOT) / 2)
    saddle = saddle.cut(cyl_y(D.SUPPORT_BRG_OD + 0.4, D.SUPPORT_BRG_W + 2,
                              y0=_BRG_Y0 - 1.0, x=0, z=0))

    # −Y backstop ring (Ø_OD outer, Ø(OD−2·lip) bore): backs the outer race,
    # sits at the bearing OD so it clears the neighbour screw at Z=0.
    ring = cyl_y(D.SUPPORT_BRG_OD, BACKSTOP_T, y0=_BACK_Y0, x=0, z=0)
    ring = ring.cut(cyl_y(D.SUPPORT_BRG_OD - 2 * BACKSTOP_LIP, BACKSTOP_T + 2,
                          y0=_BACK_Y0 - 1, x=0, z=0))
    return saddle.union(ring)


bearing_block = _build()
