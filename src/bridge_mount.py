"""Roller-bridge mount (§8 item 5) — PCTG.

Holds the roller bridge at the correct height (BRIDGE_TOP_Z), defines the
speaking length, and provides the string-anchor geometry (the strings pass over
the rollers and run on to the carriages toward the changer, +X).

Built in global position: a cradle spanning the string field at X=0, sitting on
the base top and raising the bridge bar to its seat.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at

CRADLE_ALONG  = D.BRIDGE_BAR_DEPTH + 8.0    # along the strings (X)
CRADLE_ACROSS = D.BRIDGE_BAR_LEN + 8.0      # across the strings (Y)
SEAT_BOT_Z    = D.BRIDGE_TOP_Z - D.BRIDGE_BAR_H   # underside of bridge bar
BOT_Z         = D.BASE_TOP_Z


def _build() -> cq.Workplane:
    h = SEAT_BOT_Z - BOT_Z
    body = box_at(CRADLE_ALONG, CRADLE_ACROSS, h, x=0, y=0, z=(SEAT_BOT_Z + BOT_Z) / 2)

    # Seat pocket for the bridge bar on top.
    body = body.cut(box_at(D.BRIDGE_BAR_DEPTH + D.FIT_CLR, D.BRIDGE_BAR_LEN + D.FIT_CLR,
                           D.BRIDGE_BAR_H, x=0, y=0,
                           z=SEAT_BOT_Z + D.BRIDGE_BAR_H / 2 - 0.01))

    # String clearance notches toward the changer so each string can run from the
    # roller to its carriage anchor without fouling the cradle top.
    for i in range(D.N_STRINGS):
        body = body.cut(box_at(4.0, 2.5, 4.0,
                               x=2.0, y=D.string_y(i), z=SEAT_BOT_Z - 1.0))
    return body


bridge_mount = _build()
