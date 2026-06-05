"""Roller-bridge mount (§8 item 5) — PCTG (schematic, v1).

Carries the shared bridge-bearing axle. Two uprights (just outside the string
field, so they don't block the strings) hold the axle ends; a tie bar above the
strings links them. The uprights run down to chassis level. The carriage/string
path comes up between them, untouched. Built in global position.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import motor_brick as MB
from .helpers import cyl_y, box_at

POST_Y   = D.BRIDGE_AXLE_Y                  # uprights at the axle ends
POST_W   = 5.0                              # upright thickness (Y)
TIE_Z    = D.STRING_Z + 6.0                 # tie bar clear above the strings' −X exit
BOT_Z    = MB.Z_LO + 2.0
AXLE_BORE = D.BRIDGE_AXLE_D + 0.4


def _build() -> cq.Workplane:
    body = None
    for sy in (-POST_Y, POST_Y):
        post = box_at(D.BRIDGE_BAR_DEPTH, POST_W, TIE_Z - BOT_Z,
                      x=D.BRIDGE_AXLE_X, y=sy, z=(TIE_Z + BOT_Z) / 2)
        # axle bore through the upright
        post = post.cut(cyl_y(AXLE_BORE, POST_W + 2, y0=sy - POST_W / 2 - 1,
                              x=D.BRIDGE_AXLE_X, z=D.BRIDGE_BEARING_Z))
        body = post if body is None else body.union(post)
    # tie bar linking the upright tops (above the strings)
    body = body.union(box_at(D.BRIDGE_BAR_DEPTH, 2 * POST_Y + POST_W, 5.0,
                             x=D.BRIDGE_AXLE_X, y=0, z=TIE_Z - 2.5))
    return body


bridge_mount = _build()
