"""Base / chassis frame (§8 items 3,4,7 — simplified for v1) — PCTG.

A thin frame that stays in ONE Z-plane under the screw field (the playing
portion is kept thin; bulk lives in the outboard motor end-box). It is two
side rails outside the string field tied together by:
  • two transverse near-support walls (one per Y bank) that radially locate the
    non-driven screw ends AND the coaxial-below guide rods, and
  • a rear cross-bar at the driven end.
The bearing blocks bolt to the rails/cross-ribs (mounting shown schematically).

Built in global position. In reality the length exceeds the 255 mm build volume
and would be split + glued with alignment keys; v1 models it whole.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl_y, box_at

RAIL_X      = D.STRING_FIELD_W / 2 + 17.0     # side rails clear of the outer belts
RAIL_W      = 8.0
# The frame threads through the central Z gap between the two motor plates,
# kept narrow enough to stay clear of the outer belts diving to the motors.
RAIL_Z0     = -4.0
RAIL_Z1     = 4.0
RAIL_ZC     = (RAIL_Z0 + RAIL_Z1) / 2
RAIL_H      = RAIL_Z1 - RAIL_Z0

Y0          = -4.0
# End the frame just behind the rearmost (cascaded) driven pulley so the rear
# cross-bar doesn't clip any pulley or belt.
Y1          = max(D.screw_pulley_y(i) for i in range(D.N_STRINGS)) \
              + D.PULLEY_W / 2 + RAIL_W + 4.0

WALL_T      = 6.0
SCREW_SEAT_D = D.SCREW_OD + 0.6

def _wall_z(parity):
    """Z span of a bank's near-support wall — only its own layer's range, so
    the strings clear over the wall top."""
    lz = -D.ACT_LAYER_Z if parity == 0 else D.ACT_LAYER_Z
    return (lz + D.GUIDE_ROD_DZ - D.GUIDE_ROD_D / 2 - 2.0,
            lz + D.SCREW_OD / 2 + 2.0)


def _build() -> cq.Workplane:
    body = None

    def add(part):
        nonlocal body
        body = part if body is None else body.union(part)

    # Two side rails (outside the field).
    for sx in (-RAIL_X, RAIL_X):
        add(box_at(RAIL_W, Y1 - Y0, RAIL_H, x=sx, y=(Y0 + Y1) / 2, z=RAIL_ZC))

    # Rear cross-bar tying the rails together at the driven end.
    add(box_at(2 * RAIL_X + RAIL_W, RAIL_W, RAIL_H,
               x=0, y=Y1 - RAIL_W / 2, z=RAIL_ZC))

    # Per-bank transverse near-support walls with screw + guide-rod seats.
    for parity in (0, 1):
        wall_y = D.SCREW_NEAR_Y + (0.0 if parity == 0 else D.BANK_DY)
        wz0, wz1 = _wall_z(parity)
        wall = box_at(2 * RAIL_X + RAIL_W, WALL_T, wz1 - wz0,
                      x=0, y=wall_y, z=(wz0 + wz1) / 2)
        for i in range(D.N_STRINGS):
            if i % 2 == parity:
                sx = D.string_x(i)
                lz = D.string_layer_z(i)
                wall = wall.cut(cyl_y(SCREW_SEAT_D, WALL_T + 2,
                                      y0=wall_y - WALL_T / 2 - 1, x=sx, z=lz))
                wall = wall.cut(cyl_y(D.GUIDE_ROD_D + 0.2, WALL_T + 2,
                                      y0=wall_y - WALL_T / 2 - 1, x=sx,
                                      z=lz + D.GUIDE_ROD_DZ))
        # String clearance windows: every string crosses this wall on its way
        # from the carriage anchor to the bridge; notch the wall where it does.
        for i in range(D.N_STRINGS):
            sx = D.string_x(i)
            az = D.string_layer_z(i) + D.BRIDGE_TOP_Z
            ay = D.CARRIAGE_NOM_Y + D.string_bank_dy(i) - 9.0
            sz = az + (D.BRIDGE_TOP_Z - az) * (ay - wall_y) / ay   # string Z at wall
            if wz0 - 1 < sz < wz1 + 1:
                wall = wall.cut(box_at(2.6, WALL_T + 2, 5.0, x=sx, y=wall_y, z=sz))
        add(wall)
    return body


base_rail = _build()
