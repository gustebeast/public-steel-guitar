"""Motor bank (§5) — PCTG. The under-string staircase.

The 10 motors lie flat under the speaking length, shaft +Y (bodies extend −Y
toward the player). They step along −X by MOTOR_X_STEP so they don't overlap,
each on its string's Y line. Each mounts to a faceplate wall (an X–Z plane at
its faceplate Y) carrying a NEMA17 pattern; the walls sit on a shared floor that
runs under the speaking length. Built in global position.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, nema17_face_cutter_y
from .components import MOTOR_PULLEY_STANDOFF

PLATE_T      = 6.0
TENSION_SLOT = 4.0
FLOOR_T      = 6.0
_PAD         = 4.0

# Per-motor faceplate Y (the wall the motor bolts to; −Y of the pulley line).
def _face_y(i):
    return D.string_y(i) - MOTOR_PULLEY_STANDOFF

# Envelope (for reports / counter).
_xs = [D.motor_pos(i)[0] for i in range(D.N_STRINGS)]
_zc = D.MOTOR_BELT_Z
X_LO, X_HI = min(_xs) - D.MOTOR_SQ / 2 - _PAD, max(_xs) + D.MOTOR_SQ / 2 + _PAD
Z_LO = _zc - D.MOTOR_SQ / 2 - _PAD
Z_HI = _zc + D.MOTOR_SQ / 2 + _PAD
# Motors' bodies run −Y from the faceplates; floor spans that.
Y_LO = min(_face_y(i) for i in range(D.N_STRINGS)) - D.MOTOR_BODY_LEN - 4.0
Y_HI = max(_face_y(i) for i in range(D.N_STRINGS)) + PLATE_T


def _build() -> cq.Workplane:
    # Shared floor under the motors.
    floor = box_at(X_HI - X_LO, Y_HI - Y_LO, FLOOR_T,
                   x=(X_LO + X_HI) / 2, y=(Y_LO + Y_HI) / 2, z=Z_LO + FLOOR_T / 2)
    body = floor
    for i in range(D.N_STRINGS):
        mx, my, mz = D.motor_pos(i)
        fy = _face_y(i)
        # faceplate wall (X–Z) at the motor faceplate, down to the floor
        wall = box_at(D.MOTOR_SQ + 2 * _PAD, PLATE_T, mz - (Z_LO) + D.MOTOR_SQ / 2 + _PAD,
                      x=mx, y=fy, z=(mz + D.MOTOR_SQ / 2 + _PAD + Z_LO) / 2)
        wall = wall.cut(nema17_face_cutter_y(
            fy - PLATE_T / 2, PLATE_T + 1.0, x=mx, z=mz, slot=TENSION_SLOT))
        body = body.union(wall)
    return body


motor_bank = _build()
