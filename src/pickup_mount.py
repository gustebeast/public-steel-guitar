"""Pickup carrier hardware — the DEMO pickup body + its mount screws.

The pickup is carried by the swappable PICKUP PIECE in the deck (top_plate.py):
a pocket that rides the SAME rail grooves as the other deck cover pieces. The
pickup rests on a full-width Z-PLATE that three M4 SET-SCREW JACKS lift/tilt
(3-point -> height + across-string tilt); it slides on the plate in X for tone
and is locked by two M4 TOE-CLAMP screws. EVERY screw is turned from +Z with the
instrument assembled:
  * the two +Y jacks are reached THROUGH the pickup's own +Y mounting-ear holes
    (tip string 1 aside); the -Y jack sits outboard at centre X, in the open bay;
  * the two toe-clamp screws thread ledges on the -Y skirt and press the pickup's
    -Y mounting frame down -> lock the pickup onto the plate AND the plate onto the
    jack pads (the ledge also caps up-travel, so you can't jack into the strings).

Service flow (all from +Z, NO plate removal):
  X (tone, bridge<->neck): loosen the toe-clamps -> pickup slides on the plate
    (+/-~17 continuous, bridges the 20 mm slot step) + which slots the piece sits
    in (coarse); retighten.
  Z (gap) / tilt: loosen the toe-clamps -> turn the three jacks (equalise the two
    +Y = X level; the -Y jack = across-string tilt); retighten.
  Y: centred on the field for magnetic coverage; the -Y guide flange + end walls
    set it; the +Y body edge floats in the open bay by the chassis rail.

All screws are stocked M4 set screws (zero new BOM lines). Frames: pickup centred
X/Y, top at z=0 (build.py lifts it to PK_TOP); jack/clamp screws vertical.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl, cyl_y

# ── the pickup itself (Lace Alumitone 4.0 bar, per the datasheet) ─────────────
# The RECOMMENDED pickup (user). A current-driven BLADE humbucker (no per-string
# poles). Datasheet dimensions: overall 101.6(Y, across strings) x 38.6(X, along
# neck) x 22(Z, deep); a thin top MOUNTING FLANGE with FOUR corner ears; mounting
# holes on an 84(Y) x 30.6(X) pattern; MAGNETIC RANGE (the part that actually
# senses the strings) = 88.9 -- NOT the full body: there is a ~6.35mm dead frame at
# each Y end. So coverage must be reckoned against the 88.9 magnetic range, not the
# 101.6 body edge. The strings FAN (9.5mm pitch at the changer -> 6.5mm at the nut)
# and cross the pickup at ~+/-42; the 88.9 magnetic range (+/-44.45) covers them
# with ~2.4mm margin when the body is placed by magnetic coverage (see top_plate).
# Depth 22 is deeper than the -14 ribs allow at the neck-slide positions -- a known
# TODO the user will review.
PK_W, PK_L, PK_H = 38.6, 101.6, 22.0           # X (along neck), Y (across strings), Z (deep)
PK_MAG_L = 88.9                                 # magnetic (sensing) range in Y -- covers strings
PK_FLG_T = 3.3                                   # top mounting-flange (ear plate) thickness
PK_COIL_W = 31.0                                 # coil-core X width (flange overhangs = the ears)
PK_H_MIN = 15.0                                 # carrier-wall cap datum: walls stay this far
                                               # above the plate so they never top the pickup
                                               # (< PK_H) even raised -- never foul bar/strings
GAP     = 3.0                                   # pickup top -> heaviest string bottom
PK_TOP  = D.STRING_Z - max(D.STRING_GAUGE) - GAP
PK_BOT  = PK_TOP - PK_H

# mounting-ear holes (the pickup's own 4 corner holes; the tripod jacks reach the
# two +Y ones from +Z THROUGH these holes -- see top_plate). Ø sized for M4 clear /
# hex-driver access. Positions are relative to the pickup centre (X/Y).
EAR_HOLE_D = D.NUT_SCREW_D                       # M4 clearance / driver access (cadkit's M4)
EAR_HOLE_X = 30.6 / 2                            # +/-15.3 (the 30.6 pattern, along neck)
EAR_HOLE_Y = 84.0 / 2                            # +/-42.0 (the 84 pattern, across strings)
EAR_HOLES  = [(sx * EAR_HOLE_X, sy * EAR_HOLE_Y)
              for sy in (1, -1) for sx in (1, -1)]

# ── mount screws (all stocked M4) ────────────────────────────────────────────
HSCREW_D = 4.0                                  # M4 height set-screw
CSCREW_D = 4.0                                  # M4 X/Y clamp screw


def pickup_demo() -> cq.Workplane:
    """Lace Alumitone 4.0 bar per the datasheet: a 22mm-deep coil core (PK_COIL_W
    wide in X) under a thin full-width top mounting flange with rounded corner ears
    and four Ø4.4 mounting holes (84 x 30.6 pattern). Centred X/Y, top at z=0."""
    coil = box_at(PK_COIL_W, PK_L, PK_H, z=-PK_H / 2)           # thick sensing core
    flange = (box_at(PK_W, PK_L, PK_FLG_T, z=-PK_FLG_T / 2)     # thin ear plate on top
              .edges("|Z").fillet(6.0))                          # rounded corner ears
    body = coil.union(flange)
    for hx, hy in EAR_HOLES:                                     # the pickup's own 4 mounting holes
        body = body.cut(cyl(EAR_HOLE_D, PK_H + 2, z=-PK_H - 1)   # (the mount doesn't use these --
                        .translate((hx, hy, 0)))                 # jacks are on the plate corners)
    return body


def height_screw() -> cq.Workplane:
    """DEMO M4 height set-screw, axis +Z, top at z=0 (the pickup rests here);
    short enough that its base stays above the chassis ribs at z -14."""
    return cyl(HSCREW_D, 4.0, z=-4.0)


def clamp_screw() -> cq.Workplane:
    """DEMO M4x12 button-head X/Y clamp screw, axis +Y: shank tip at y=0."""
    return cyl_y(CSCREW_D, 12.0, y0=0.0).union(cyl_y(7.5, 2.2, y0=12.0))
