"""Base / chassis frame (§8 items 3,4,7 — simplified) — PCTG.

A thin frame that stays in ONE Z-plane under the screw field. It is two side
rails outside the string field (running along X) tied together by:
  • per-bank transverse near-support walls that radially locate the non-driven
    screw ends AND the coaxial-below guide rods, and
  • a cross-bar at the driven (+X) end.
The bearing cradles bolt to the rails/cross-ribs (mounting shown schematically).

Built in global position. In reality the length exceeds the 255 mm build volume
and would be split + glued with alignment keys.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl_x, box_at

RAIL_Y      = D.STRING_FIELD_W / 2 + 17.0     # side rails clear of the outer belts
RAIL_W      = 8.0
RAIL_Z0     = -4.0
RAIL_Z1     = 4.0
RAIL_ZC     = (RAIL_Z0 + RAIL_Z1) / 2
RAIL_H      = RAIL_Z1 - RAIL_Z0

X0          = -4.0
# End the frame just past the front-most (cascaded) driven pulley so the cross-
# bar doesn't clip any pulley or belt.
X1          = max(D.screw_pulley_x(i) for i in range(D.N_STRINGS)) \
              + D.PULLEY_W / 2 + RAIL_W + 4.0

WALL_T      = 6.0
SCREW_SEAT_D = D.SCREW_OD + 0.6

def _wall_z(parity):
    """Z span of a bank's near-support wall — only its own layer's range, so the
    strings clear over the wall top."""
    lz = -D.ACT_LAYER_Z if parity == 0 else D.ACT_LAYER_Z
    return (lz + D.GUIDE_ROD_DZ - D.GUIDE_ROD_D / 2 - 2.0,
            lz + D.SCREW_OD / 2 + 2.0)


def _build() -> cq.Workplane:
    body = None

    def add(part):
        nonlocal body
        body = part if body is None else body.union(part)

    # Two side rails (outside the field), running along X.
    for sy in (-RAIL_Y, RAIL_Y):
        add(box_at(X1 - X0, RAIL_W, RAIL_H, x=(X0 + X1) / 2, y=sy, z=RAIL_ZC))

    # Cross-bar tying the rails together at the driven end.
    add(box_at(RAIL_W, 2 * RAIL_Y + RAIL_W, RAIL_H,
               x=X1 - RAIL_W / 2, y=0, z=RAIL_ZC))

    # Per-bank transverse near-support walls with screw + guide-rod seats.
    for parity in (0, 1):
        wall_x = D.SCREW_NEAR_X + (0.0 if parity == 0 else D.BANK_DX)
        wz0, wz1 = _wall_z(parity)
        wall = box_at(WALL_T, 2 * RAIL_Y + RAIL_W, wz1 - wz0,
                      x=wall_x, y=0, z=(wz0 + wz1) / 2)
        for i in range(D.N_STRINGS):
            if i % 2 == parity:
                sy = D.string_y(i)
                lz = D.string_layer_z(i)
                wall = wall.cut(cyl_x(SCREW_SEAT_D, WALL_T + 2,
                                      x0=wall_x - WALL_T / 2 - 1, y=sy, z=lz))
                wall = wall.cut(cyl_x(D.GUIDE_ROD_D + 0.2, WALL_T + 2,
                                      x0=wall_x - WALL_T / 2 - 1, y=sy,
                                      z=lz + D.GUIDE_ROD_DZ))
        # String clearance windows: every string crosses this wall on its way
        # from the carriage anchor to the bridge; notch the wall where it does.
        for i in range(D.N_STRINGS):
            sy = D.string_y(i)
            az = D.string_layer_z(i) + D.BRIDGE_TOP_Z
            ax = D.CARRIAGE_NOM_X + D.string_bank_dx(i) - 9.0
            sz = az + (D.BRIDGE_TOP_Z - az) * (ax - wall_x) / ax   # string Z at wall
            if wz0 - 1 < sz < wz1 + 1:
                wall = wall.cut(box_at(WALL_T + 2, 2.6, 5.0, x=wall_x, y=sy, z=sz))
        add(wall)
    return body


base_rail = _build()
