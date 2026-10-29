# -*- coding: utf-8 -*-
"""A PRINTED HACKSAW GUIDE for cutting each SERVO42D's shaft to components.MOTOR_SHAFT_CUT_L.

SHOP TOOL, not a part of the instrument (lead, 2026-10-29; user: "a jig very similar to the one
we use for cutting the leadscrew except this one will hold the motor in place"). The shaft is
bought 21.5 long off the faceplate; the pulley only needs it to its own outer face, and the
rest is what kept the motors 3.2 further from their belts than they had to be. Cutting it is a
process step on every motor, done once, before its pulley goes on.

ONE PRINTED PART, FOUR SCREWS THE INSTRUMENT ALREADY BUYS. Shaft axis along +X, the motor's
faceplate at x = 0, the table at z = 0 -- the motor lies on its side on the table, as it is
used:

  PLATE  a square the size of the faceplate, 12 beads thick, bolted FLAT to it by four M3 x 12
         socket heads (the belt clamps' draw screws, BOM m3_shcs_12, 2.5 mm key) in the NEMA17
         holes at 31 square. Its back carries a pocket that takes the pilot boss on BOSS_CLR, so
         the guide is concentric with the shaft without measuring, and the pocket's roof closes
         on the shaft in a 45 deg cone: the whole face of the motor -- boss, bearing seal, the
         magnet gap behind it -- is under printed plastic.
  TOWER  a block on the plate around the shaft, inside the four screw heads (so the key reaches
         every one straight down X), with a snug D bore the shaft's own flat keys into. Its +X
         face IS the cut plane: the blade's flat lies on it and saws down past the shaft.

WHY ONE CHEEK, not the leadscrew jig's two. The jig prints FACEPLATE-FACE DOWN, so every hole
in it -- the D bore, the four screw holes -- is drawn round about its own axis (no teardrop
apex for filings to ride in along the shaft), and the boss pocket's roof is that 45 deg cone. A
+X cheek would stand over the saw gap as a flat ceiling the full size of the cheek. A hacksaw
held flat on one guide face only ever drifts +X -- AWAY from the motor -- so the error makes the
shaft longer, never shorter, and the file takes it back to the face.

CHIPS. The plate covers the faceplate; the one way in from the saw is the D bore, a close fit
CUT_BORE_L long, flat to flat. The tower overhangs the table edge (EDGE MARK), so filings fall
to the floor, not onto the table under the motor. Then the steps in INSTALL_NOTES: deburr,
chamfer, and pick the filings off the stub and the tower with a magnet BEFORE the jig comes
off -- the motor's own magnet is under the plate, and this is the moment it is covered.

THE SCREWS ENGAGE ONLY SCREW_ENGAGE (2.4, five M3 threads). Nothing else on the instrument
screws into a motor -- the bays drop them in and the tee board holds them -- so there is no
proven hole depth to lean on, and the SERVO42D's drawing does not give one (searched
2026-10-29). Five threads hold a hand-saw guide, and every NEMA17 faceplate seen is tapped
deeper (3.5-4.5), so the plate is sized to the shallowest plausible hole instead of to a
guess at this one.
"""
from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import components as C
from . import motor_bank as MB
from . import servo42d as SV

B = D.BEAD

# ── the motor ───────────────────────────────────────────────────────────────
SHAFT_R = D.MOTOR_SHAFT_D / 2.0                      # 2.5
FLAT_Z = D.MOTOR_SHAFT_FLAT - SHAFT_R                # 2.0: the D's flat over the axis
AXIS_Z = D.MOTOR_DRIVER_SQ_MEASURED / 2.0            # 21.25: lying on its 42.5 driver cover
FACE_HW = D.MOTOR_SQ / 2.0                           # 21.15: the faceplate's half-width
BOLT_H = D.NEMA17_BOLT_SQ / 2.0                      # 15.5
PILOT_R = SV.PILOT_D / 2.0 + MB.BOSS_CLR / 2.0       # the boss pocket: BOSS_CLR across
POCKET_D = SV.PILOT_H + B / 2.0                      # 2.4: the plate stands on the face, not the boss

# ── the screws: the belt clamps' M3 x 12 (one SKU, the one key) ─────────────
SCREW_L = 12.0
PLATE_T = 12 * B                                     # 9.6: the heads seat on its +X face
SCREW_ENGAGE = SCREW_L - PLATE_T                     # 2.4 in the motor: five threads (see docstring)
assert abs(PLATE_T / B - round(PLATE_T / B)) < 1e-9, "the plate is off the bead grid"
CLEAR_R = 3.4 / 2.0                                  # M3 clearance
HEAD_R = 5.5 / 2.0                                   # ISO 4762 M3 head

# ── the cut ────────────────────────────────────────────────────────────────
CUT_X = C.MOTOR_SHAFT_CUT_L                          # the tower's +X face: the blade's guide
BORE_CLR = 0.1                                       # round the shaft and its flat
TOWER_HW = 14 * B                                    # 11.2: half the tower's square
assert TOWER_HW + B <= BOLT_H - HEAD_R, "the tower stands over a screw head: no key access"
# the cone closing the boss pocket onto the bore, at 45 deg, then the bore proper to the face
CONE_X1 = POCKET_D + (PILOT_R - SHAFT_R - BORE_CLR)
CUT_BORE_L = CUT_X - CONE_X1                         # the close-fit run the filings would face
assert CUT_BORE_L >= 4 * B, "under four beads of close bore between the saw and the motor"
assert CUT_X - PLATE_T >= 4 * B, "the tower is too short to guide the blade"
EDGE_X = PLATE_T / 2.0                               # the table edge goes under the plate
EDGE_D = B                                           # the edge mark: a 45 deg V, 0.8 deep
# PRINT ORIENTATION: faceplate face (x = 0) on the bed, building +X
PRINT_UP = (1.0, 0.0, 0.0)


def _xcyl(r, x0, x1, y=0.0, z=AXIS_Z):
    return cq.Workplane("YZ").workplane(offset=x0).center(y, z).circle(r).extrude(x1 - x0)


def _d_bore(x0, x1):
    """The shaft's D, BORE_CLR all round, flat facing +Z."""
    r = SHAFT_R + BORE_CLR
    zf = FLAT_Z + BORE_CLR
    bore = _xcyl(r, x0, x1)
    return bore.cut(cq.Workplane("XY").box(x1 - x0 + 2.0, 2 * r + 2.0, r + 1.0, centered=(False, True, False))
                    .translate((x0 - 1.0, 0.0, AXIS_Z + zf)))


def jig() -> cq.Workplane:
    plate = (cq.Workplane("XY").box(PLATE_T, 2 * FACE_HW, AXIS_Z + FACE_HW, centered=(False, True, False)))
    tower = (cq.Workplane("XY").box(CUT_X - PLATE_T, 2 * TOWER_HW, 2 * TOWER_HW,
                                    centered=(False, True, True))
             .translate((PLATE_T, 0.0, AXIS_Z)))
    out = plate.union(tower)
    # the boss pocket and its 45 deg cone onto the bore
    out = out.cut(_xcyl(PILOT_R, -1.0, POCKET_D))
    cone = cq.Solid.makeCone(PILOT_R, SHAFT_R + BORE_CLR, CONE_X1 - POCKET_D,
                             cq.Vector(POCKET_D, 0.0, AXIS_Z), cq.Vector(1, 0, 0))
    out = out.cut(cq.Workplane("XY").add(cone))
    # (where the cone's round end meets the D bore, the flat's chord leaves a 0.5-wide, 1 mm2
    #  ledge looking down the print -- print_check lists it; it is a ledge, not a bridge)
    out = out.cut(_d_bore(CONE_X1 - 0.5, CUT_X + 1.0))
    for sy in (-1, 1):                                # the four M3 clearance holes
        for sz in (-1, 1):
            out = out.cut(_xcyl(CLEAR_R, -1.0, PLATE_T + 1.0, y=sy * BOLT_H, z=AXIS_Z + sz * BOLT_H))
    for sy in (-1, 1):                                # the table-edge mark down both sides: a
        yo = sy * (FACE_HW + 1.0)                     # 45 deg V, so its faces print as walls
        yi = sy * (FACE_HW - EDGE_D)
        v = (cq.Workplane("XY").polyline([(EDGE_X - EDGE_D - 1.0, yo), (EDGE_X + EDGE_D + 1.0, yo),
                                          (EDGE_X, yi)]).close()
             .extrude(AXIS_Z + FACE_HW + 2.0).translate((0.0, 0.0, -1.0)))
        out = out.cut(v)
    return out


def screw_heads():
    """The four M3 heads, seated, for checking key access only."""
    out = None
    for sy in (-1, 1):
        for sz in (-1, 1):
            h = _xcyl(HEAD_R, PLATE_T, PLATE_T + 3.0, y=sy * BOLT_H, z=AXIS_Z + sz * BOLT_H)
            out = h if out is None else out.union(h)
    return out
