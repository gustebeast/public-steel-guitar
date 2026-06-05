"""Roller-bridge mount (§8 item 5) — PCTG.

Holds the roller bridge at the correct height (BRIDGE_TOP_Z), defines the
speaking length, and provides the behind-the-bridge string-anchor geometry
(the strings pass over the rollers and run on to the carriages at +Y).

Built in global position: a cradle spanning the string field at Y=0, sitting
on the base top and raising the bridge bar to its seat.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at

CRADLE_X    = D.BRIDGE_BAR_W + 8.0
CRADLE_Y    = D.BRIDGE_BAR_DEPTH + 8.0
SEAT_BOT_Z  = D.BRIDGE_TOP_Z - D.BRIDGE_BAR_H        # underside of bridge bar
BOT_Z       = D.BASE_TOP_Z


def _build() -> cq.Workplane:
    h = SEAT_BOT_Z - BOT_Z
    body = box_at(CRADLE_X, CRADLE_Y, h, x=0, y=0, z=(SEAT_BOT_Z + BOT_Z) / 2)

    # Seat pocket for the bridge bar on top.
    body = body.cut(box_at(D.BRIDGE_BAR_W + D.FIT_CLR, D.BRIDGE_BAR_DEPTH + D.FIT_CLR,
                           D.BRIDGE_BAR_H, x=0, y=0,
                           z=SEAT_BOT_Z + D.BRIDGE_BAR_H / 2 - 0.01))

    # String clearance notches behind the bridge so each string can run from
    # the roller down to its carriage anchor without fouling the cradle top.
    for i in range(D.N_STRINGS):
        body = body.cut(box_at(2.5, CRADLE_Y, 4.0,
                               x=D.string_x(i), y=2.0, z=SEAT_BOT_Z - 1.0))
    return body


bridge_mount = _build()
