"""Motor brick (§5) — PCTG. THE key spatial problem.

Holds all 10 SERVO42D motors in the zero-skew, 2-layer arrangement. Because each
belt has its own X belt-plane (BANK_DX between even/odd + BELT_PLANE_DX between
the two planes within a layer), the 10 motors sit at FOUR distinct faceplate X
levels, two per Z-layer (lower = even strings, upper = odd strings).

The brick is one mounting plate per (layer, plane) group — each carrying its
motors' NEMA17 patterns (centre pilot + 4 bolt holes slotted along Z for belt
tensioning) — tied together by side rails and a floor. Built in global position;
motors mount on the +X side, pulleys poking −X to the screw pulleys.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, nema17_face_cutter

PLATE_T      = 6.0
STANDOFF     = 20.0         # motor faceplate set back from its pulley plane (+X)
TENSION_SLOT = 4.0          # bolt-slot length along Z for belt tensioning
RAIL_W       = 8.0


def _motor_face_x(i):
    return D.screw_pulley_x(i) + STANDOFF


def _groups():
    """Map face_x (rounded) -> list of string indices that mount there."""
    g = {}
    for i in range(D.N_STRINGS):
        g.setdefault(round(_motor_face_x(i), 3), []).append(i)
    return g


_GROUPS = _groups()
_YMARGIN = D.MOTOR_SQ / 2 + 5.0          # plate edge clearance across (Y)
_ZPAD    = D.MOTOR_SQ / 2 + 1.0          # plate just covers the motor square in Z

# Envelope (for reports / build-counter placement).
_all_y, _all_z, _all_x = [], [], []
for i in range(D.N_STRINGS):
    my, mz, _ = D.motor_target_for_string(i)
    _all_y.append(my)
    _all_z.append(mz)
    _all_x.append(_motor_face_x(i))
Y_LO, Y_HI = min(_all_y) - _YMARGIN, max(_all_y) + _YMARGIN
Z_LO, Z_HI = min(_all_z) - _ZPAD, max(_all_z) + _ZPAD
X_LO = min(_all_x) - PLATE_T / 2
X_HI = max(_all_x) + PLATE_T / 2
PLATE_W = Y_HI - Y_LO       # across extent
PLATE_H = Z_HI - Z_LO
FACE_X = max(_all_x)        # front-most faceplate — used by reports


def _build() -> cq.Workplane:
    body = None

    def add(p):
        nonlocal body
        body = p if body is None else body.union(p)

    # One mounting plate (in a Y–Z plane) per (layer, belt-plane) group.
    for face_x, members in _GROUPS.items():
        ys = [D.motor_target_for_string(i)[0] for i in members]
        zs = [D.motor_target_for_string(i)[1] for i in members]
        y0, y1 = min(ys) - _YMARGIN, max(ys) + _YMARGIN
        z0, z1 = min(zs) - _ZPAD, max(zs) + _ZPAD
        plate = box_at(PLATE_T, y1 - y0, z1 - z0,
                       x=face_x, y=(y0 + y1) / 2, z=(z0 + z1) / 2)
        for i in members:
            my, mz, _ = D.motor_target_for_string(i)
            plate = plate.cut(nema17_face_cutter(
                face_x + PLATE_T / 2, PLATE_T + 1.0, y=my, z=mz, slot=TENSION_SLOT))
        add(plate)

    # Side rails tying every plate together (across extremes), full X and Z.
    for sy in (Y_LO + RAIL_W / 2, Y_HI - RAIL_W / 2):
        add(box_at(X_HI - X_LO, RAIL_W, Z_HI - Z_LO,
                   x=(X_LO + X_HI) / 2, y=sy, z=(Z_LO + Z_HI) / 2))
    # Floor panel under the lower layer.
    add(box_at(X_HI - X_LO, Y_HI - Y_LO, RAIL_W,
               x=(X_LO + X_HI) / 2, y=(Y_LO + Y_HI) / 2, z=Z_LO + RAIL_W / 2))
    return body


motor_brick = _build()
