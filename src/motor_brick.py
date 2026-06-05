"""Motor brick (§5) — PCTG. THE key spatial problem.

Holds all 10 SERVO42D motors in the zero-skew, 2-layer arrangement. Because
each belt has its own Y belt-plane (BANK_DY between even/odd + BELT_PLANE_DY
between the two planes within a layer), the 10 motors sit at FOUR distinct
faceplate Y levels, two per Z-layer:

  • lower layer (−Z, even strings): planes at FACE Y_even,0 and Y_even,1
  • upper layer (+Z, odd strings):  planes at FACE Y_odd,0  and Y_odd,1

The brick is one mounting plate per (layer, plane) group — each carrying its
motors' NEMA17 patterns (centre pilot + 4 bolt holes slotted along Z for belt
tensioning) — all tied together by two side rails and a floor. Built in global
position; motors mount on the +Y side, pulleys poking −Y to the screw pulleys.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, nema17_face_cutter

PLATE_T      = 6.0
STANDOFF     = 20.0         # motor faceplate set back from its pulley plane
TENSION_SLOT = 4.0          # bolt-slot length along Z for belt tensioning
RAIL_W       = 8.0


def _motor_face_y(i):
    return D.screw_pulley_y(i) + STANDOFF


def _groups():
    """Map face_y (rounded) -> list of string indices that mount there."""
    g = {}
    for i in range(D.N_STRINGS):
        key = round(_motor_face_y(i), 3)
        g.setdefault(key, []).append(i)
    return g


_GROUPS = _groups()
_XMARGIN = D.MOTOR_SQ / 2 + 5.0          # plate edge clearance in X
_ZPAD    = D.MOTOR_SQ / 2 + 1.0          # plate just covers the motor square in Z
                                         # (a big Z margin would clip the screw pulleys)

# Envelope (for reports / build counter placement).
_all_x, _all_z, _all_y = [], [], []
for i in range(D.N_STRINGS):
    mx, mz, _ = D.motor_target_for_string(i)
    _all_x.append(mx)
    _all_z.append(mz)
    _all_y.append(_motor_face_y(i))
X_LO, X_HI = min(_all_x) - _XMARGIN, max(_all_x) + _XMARGIN
Z_LO, Z_HI = min(_all_z) - _ZPAD, max(_all_z) + _ZPAD
Y_LO = min(_all_y) - PLATE_T / 2
Y_HI = max(_all_y) + PLATE_T / 2
PLATE_W = X_HI - X_LO
PLATE_H = Z_HI - Z_LO
FACE_Y = max(_all_y)        # rearmost faceplate — used by reports


def _build() -> cq.Workplane:
    body = None

    def add(p):
        nonlocal body
        body = p if body is None else body.union(p)

    # One mounting plate per (layer, belt-plane) group.
    for face_y, members in _GROUPS.items():
        xs = [D.motor_target_for_string(i)[0] for i in members]
        zs = [D.motor_target_for_string(i)[1] for i in members]
        x0, x1 = min(xs) - _XMARGIN, max(xs) + _XMARGIN
        z0, z1 = min(zs) - _ZPAD, max(zs) + _ZPAD
        plate = box_at(x1 - x0, PLATE_T, z1 - z0,
                       x=(x0 + x1) / 2, y=face_y, z=(z0 + z1) / 2)
        for i in members:
            mx, mz, _ = D.motor_target_for_string(i)
            plate = plate.cut(nema17_face_cutter(
                face_y + PLATE_T / 2, PLATE_T + 1.0, x=mx, z=mz, slot=TENSION_SLOT))
        add(plate)

    # Side rails tying every plate together (X extremes), full Y and Z.
    for sx in (X_LO + RAIL_W / 2, X_HI - RAIL_W / 2):
        add(box_at(RAIL_W, Y_HI - Y_LO, Z_HI - Z_LO,
                   x=sx, y=(Y_LO + Y_HI) / 2, z=(Z_LO + Z_HI) / 2))
    # Floor panel under the lower layer.
    add(box_at(X_HI - X_LO, Y_HI - Y_LO, RAIL_W,
               x=(X_LO + X_HI) / 2, y=(Y_LO + Y_HI) / 2, z=Z_LO + RAIL_W / 2))
    return body


motor_brick = _build()
