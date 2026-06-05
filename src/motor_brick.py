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

WALL_W = D.MOTOR_SQ + 1.0                   # wall X-width (< MOTOR_X_STEP, clears neighbour)

# Per-motor faceplate wall CENTRE Y. The motor faceplate (component) is at
# string_y(i) − STANDOFF; the wall's −Y face must sit there so the faceplate
# ABUTS the wall (motor body −Y of it), hence +PLATE_T/2.
def _face_y(i):
    return D.string_y(i) - MOTOR_PULLEY_STANDOFF + PLATE_T / 2

# Envelope (for reports / counter).
_xs = [D.motor_pos(i)[0] for i in range(D.N_STRINGS)]
_zc = D.MOTOR_BELT_Z
FLOOR_TOP = _zc - D.MOTOR_SQ / 2            # motors rest ON the floor (no sink-in)
X_LO, X_HI = min(_xs) - WALL_W / 2, max(_xs) + WALL_W / 2
Z_LO = FLOOR_TOP - FLOOR_T
Z_HI = _zc + D.MOTOR_SQ / 2 + _PAD
# Motors' bodies run −Y from the faceplates; floor spans that.
Y_LO = min(D.string_y(i) - MOTOR_PULLEY_STANDOFF for i in range(D.N_STRINGS)) - D.MOTOR_BODY_LEN - 4.0
Y_HI = max(_face_y(i) for i in range(D.N_STRINGS)) + PLATE_T / 2


def _build() -> cq.Workplane:
    # Shared floor under the motors (top flush with the motor bodies' bottom).
    floor = box_at(X_HI - X_LO, Y_HI - Y_LO, FLOOR_T,
                   x=(X_LO + X_HI) / 2, y=(Y_LO + Y_HI) / 2, z=FLOOR_TOP - FLOOR_T / 2)
    body = floor
    for i in range(D.N_STRINGS):
        mx, my, mz = D.motor_pos(i)
        fy = _face_y(i)
        # faceplate wall (X–Z) just +Y of the motor faceplate, rising from the floor
        wall = box_at(WALL_W, PLATE_T, Z_HI - FLOOR_TOP,
                      x=mx, y=fy, z=(Z_HI + FLOOR_TOP) / 2)
        wall = wall.cut(nema17_face_cutter_y(
            fy - PLATE_T / 2, PLATE_T + 1.0, x=mx, z=mz, slot=TENSION_SLOT))
        body = body.union(wall)
    return body


motor_bank = _build()
