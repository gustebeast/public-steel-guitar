"""Leadscrew bearing cradle (×10) — PA6-GF (§8 item 2).

OPEN holder, not an enclosing bore. With no belt the bearing load is almost
purely AXIAL (the string pulls the screw −X), so the bearing only needs a −X
backstop face (compression — strong even thin) plus light radial cradling.

To let ALL screws share one Z plane, the holder grips the bearing from BELOW
the screw plane: a saddle under the bearing (bulk at Z < −screw_r) plus a thin
−X backstop ring. At the screw plane (Z≈0) the only thing in the field is the
bearing's own OD, so a neighbour screw 9.5 mm away clears it.

Local frame: screw axis +X through the origin; the bearing nests centred at the
ORIGIN (X=0, Z=0). The backstop is just −X of it. build.py places the holder at
the bearing's centre.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl_x, box_at

RB           = D.SUPPORT_BRG_OD / 2
BACKSTOP_T   = 2.0                          # −X backstop thickness (X)
BACKSTOP_LIP = 1.5                          # radial overlap onto the outer race
BLK_X        = D.SUPPORT_BRG_W + BACKSTOP_T   # holder depth along the screw (X)
BLK_ACROSS   = 2 * (RB + 1.5)               # across width (Y); cups the bearing
SADDLE_TOP_Z = -(D.SCREW_OD / 2 + 1.0)      # holder stays below the screw plane
Z_BOT        = -(RB + 3.0)

# X spans (bearing centred at X=0):
_BRG_X0  = -D.SUPPORT_BRG_W / 2             # bearing −X face
_BACK_X0 = _BRG_X0 - BACKSTOP_T            # backstop −X face


def _build() -> cq.Workplane:
    # Saddle: a block beneath the bearing, spanning the backstop+bearing X, with
    # a trough scooped out so the bearing's lower arc nests in it.
    saddle = box_at(BLK_X, BLK_ACROSS, SADDLE_TOP_Z - Z_BOT,
                    x=(_BACK_X0 + D.SUPPORT_BRG_W / 2) / 2, y=0,
                    z=(SADDLE_TOP_Z + Z_BOT) / 2)
    saddle = saddle.cut(cyl_x(D.SUPPORT_BRG_OD + 0.4, D.SUPPORT_BRG_W + 2,
                              x0=_BRG_X0 - 1.0, y=0, z=0))

    # −X backstop ring (Ø_OD outer, Ø(OD−2·lip) bore): backs the outer race, sits
    # at the bearing OD so it clears the neighbour screw at Z=0.
    ring = cyl_x(D.SUPPORT_BRG_OD, BACKSTOP_T, x0=_BACK_X0, y=0, z=0)
    ring = ring.cut(cyl_x(D.SUPPORT_BRG_OD - 2 * BACKSTOP_LIP, BACKSTOP_T + 2,
                          x0=_BACK_X0 - 1, y=0, z=0))
    return saddle.union(ring)


bearing_block = _build()
