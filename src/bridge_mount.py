"""Roller-bridge mount (§8 item 5) — PCTG (schematic, v1).

Holds the roller bridge above the carriages at X=0 (the 90° turn). Modelled as a
top bar above the rollers carried by two end posts (outside the string field)
down to the chassis — so it doesn't block the carriage/string path that comes up
from below. (The vertical screws are supported at the bottom rail; a top support
can be added once the roller-axle detail is fixed.) Built in global position.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import motor_brick as MB
from .helpers import box_at

ACROSS  = D.BRIDGE_BAR_LEN + 10.0
POST_Y  = D.STRING_FIELD_W / 2 + 14.0      # outside the bottom bearing rail
TOP_Z   = D.STRING_Z + 4.0
BOT_Z   = MB.Z_LO + 2.0


def _build() -> cq.Workplane:
    # top bar above the rollers
    body = box_at(D.BRIDGE_BAR_DEPTH, ACROSS, 5.0, x=0, y=0, z=TOP_Z - 2.5)
    # end posts down to the chassis (outside the field)
    for sy in (-POST_Y, POST_Y):
        body = body.union(box_at(D.BRIDGE_BAR_DEPTH, 6.0, TOP_Z - BOT_Z,
                                 x=0, y=sy, z=(TOP_Z + BOT_Z) / 2))
    return body


bridge_mount = _build()
