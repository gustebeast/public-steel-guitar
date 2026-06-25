"""Motor bank (§5) — PCTG. The under-string staircase.

The 10 motors lie flat under the speaking length, shaft +Y (bodies extend −Y
toward the player). They step along −X by MOTOR_X_STEP so they don't overlap,
each on its string's Y line. Each mounts to a faceplate wall (an X–Z plane at
its faceplate Y) carrying a NEMA17 pattern; motors and walls rest on the
chassis's per-motor cross-ribs (no floor plate — the walls are fused into the
chassis). Built in global position.

INDIVIDUAL SWAP: any motor comes out without touching the other motors — slip
its belt off (slot travel gives the slack), unhook the few strings directly
overhead (ball ends lift out of their cages tool-free), slide the pickup mount
aside if parked there, unbolt, back the motor −Y 2–3 mm (the Ø22 boss
disengages; motor 0 has exactly the 2 mm it needs), then LIFT it out through the
string field: a shaft-width channel runs from each pilot bore UP through the
wall's top edge so the shaft rises free. (Down/sideways are blocked: its own
cross-rib is underneath, neighbours 1.7 mm away.) Walls are 43 wide (legal
X-overlap — neighbours sit on different Y planes) so the ±3 tension slots keep
real outer walls.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, nema17_face_cutter_y
from .components import MOTOR_PULLEY_STANDOFF

PLATE_T      = 6.0
TENSION_SLOT = 3.0                          # ±1.5: belt slip-on slack + tension + the
                                            # 1-tooth (1 mm motor travel) cut quantum.
                                            # Small enough that neighbours never collide
                                            # at the 46 mm pitch (see MOTOR_X_STEP).
_BOLT_EDGE   = 6.0                          # material around the NEMA17 bolt square

WALL_W = D.NEMA17_BOLT_SQ + 2 * _BOLT_EDGE  # 43: 0.5 to the chassis split planes,
                                            # 1.35 to the neighbouring motor body

# Per-motor faceplate wall CENTRE Y. The motor faceplate (component) is at
# string_y(i) − STANDOFF; the wall's −Y face must sit there so the faceplate
# ABUTS the wall (motor body −Y of it), hence +PLATE_T/2.
def _face_y(i):
    return D.string_y(i) - MOTOR_PULLEY_STANDOFF + PLATE_T / 2

_zc = D.MOTOR_BELT_Z
FLOOR_TOP = _zc - D.MOTOR_SQ / 2            # motors rest here (= wall bottom / chassis rib top)
BED_Z = FLOOR_TOP - D.XBAR                  # print bed = chassis rib/rail bottom; the
                                            # FLOOR_TOP->bed gap = rib height = XBAR, so the
                                            # cross-ribs are a square XBAR x XBAR section
Z_HI = _zc + D.NEMA17_BOLT_SQ / 2 + _BOLT_EDGE     # wall top, just above the top bolts


def _build() -> cq.Workplane:
    # Just the faceplate walls (motor mounts). The motors rest on, and the walls
    # sit on, the chassis's per-motor cross-ribs — there is no solid floor (a thin
    # plate would be heavy printed skin; chunky ribs carry the load far lighter).
    # Each plate runs all the way to the print bed (BED_Z), with its bottom edges
    # tapered 45° — printable (no overhang) using less material than straight-down.
    body = None
    for i in range(D.N_STRINGS):
        mx, my, mz = D.motor_pos(i)
        fy = _face_y(i)
        wall = box_at(WALL_W, PLATE_T, Z_HI - BED_Z,
                      x=mx, y=fy, z=(Z_HI + BED_Z) / 2)
        wall = wall.edges("|Y and <Z").chamfer(14.0)   # big 45° buttress → bed (gusset)
        wall = wall.edges("|Y and >Z").chamfer(3.0)     # trim the top corners
        wall = wall.cut(nema17_face_cutter_y(
            fy - PLATE_T / 2, PLATE_T + 1.0, x=mx, z=mz, slot=TENSION_SLOT))
        # shaft exit channel: pilot bore → wall TOP edge, so an unbolted motor
        # (backed off ~3 mm) lifts out through the string field
        wall = wall.cut(box_at(6.0, PLATE_T + 2.0, Z_HI - mz + 1,
                               x=mx, y=fy, z=(mz + Z_HI + 1) / 2))
        body = wall if body is None else body.union(wall)
    return body


motor_bank = _build()
