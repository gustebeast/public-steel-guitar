"""Base / chassis frame (simplified) — PCTG.

Two side rails (outside the string field, running along X) that tie the bridge
mount, the bottom bearing rail, and the motor-bank floor together into one body.
Built in global position. In reality it exceeds the 255 mm build volume and would
be split + glued with alignment keys.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import motor_brick as MB
from .helpers import box_at

RAIL_Y  = D.STRING_FIELD_W / 2 + 14.0      # outside the field (across)
RAIL_W  = 8.0
X_HI    = 6.0                              # +X edge at the bridge
X_LO    = MB.X_LO - 4.0                    # −X edge past the last motor
RAIL_Z  = MB.Z_LO + 2.0                    # along the bottom of the motor bank


def _build() -> cq.Workplane:
    body = None
    for sy in (-RAIL_Y, RAIL_Y):
        rail = box_at(X_HI - X_LO, RAIL_W, RAIL_W,
                      x=(X_LO + X_HI) / 2, y=sy, z=RAIL_Z)
        body = rail if body is None else body.union(rail)
    # end cross-bars (bridge end and far/nut end) tying the rails
    for x in (X_HI - RAIL_W / 2, X_LO + RAIL_W / 2):
        body = body.union(box_at(RAIL_W, 2 * RAIL_Y + RAIL_W, RAIL_W,
                                 x=x, y=0, z=RAIL_Z))
    return body


base_rail = _build()
