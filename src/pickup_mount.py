"""Pickup hardware: the DEMO pickup body (Lace Alumitone 4.0 bar) and its dimensions.

The mount itself -- the Z-plate the pickup rests on, the three M4 leadscrew jacks at the
plate corners, and the pickup's retention -- is built in top_plate.py, which reads the
PK_* dimensions here. Frame: pickup centred X/Y, top at z=0 (build.py lifts it to PK_TOP).
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl

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
# THE ADJUST RANGE (user, 2026-10-29): pickup top -> heaviest string bottom, at the two ends of
# the plate's travel. The DEEPEST pickup (PK_H) must reach down to GAP_MAX; the shallowest
# (PK_H_MIN) must still reach up to GAP_MIN. The plate is drawn at the BOTTOM of its travel --
# the deepest pickup at GAP_MAX -- so the gate sees the lowest it ever goes.
GAP_MAX = 6.0
# GAP_MIN is 3.0, today's top of travel, and NOT 1.5: the -Y retention boss rides 9.45 over the
# plate top and the deck's relief over it stops one bead under the deck top (top_plate
# RET_RELIEF_Z1), so the plate top can rise no further than -3.85 -- the 15 mm pickup's 2.82 gap.
# 3.0 keeps the swept half-millimetre steps clear of it; a 16 mm pickup still reaches 2.0.
GAP_MIN = 3.0
PK_TOP  = D.STRING_Z - D.STRING_GAUGE_MAX - GAP_MAX   # clear the heaviest string that fits, not the demo set's
PLATE_TRAVEL = (PK_H - PK_H_MIN) + (GAP_MAX - GAP_MIN)   # 10.0: what the jacks lift the plate
PK_BOT  = PK_TOP - PK_H

# mounting-ear holes: the pickup's own 4 corner holes, modelled on the demo body only (the
# mount does not use them -- the jacks are on the plate corners). Positions are relative to
# the pickup centre (X/Y).
EAR_HOLE_D = D.NUT_SCREW_D                       # M4 clearance (cadkit's M4)
EAR_HOLE_X = 30.6 / 2                            # +/-15.3 (the 30.6 pattern, along neck)
EAR_HOLE_Y = 84.0 / 2                            # +/-42.0 (the 84 pattern, across strings)
EAR_HOLES  = [(sx * EAR_HOLE_X, sy * EAR_HOLE_Y)
              for sy in (1, -1) for sx in (1, -1)]


def pickup_demo() -> cq.Workplane:
    """Lace Alumitone 4.0 bar per the datasheet: a 22mm-deep coil core (PK_COIL_W
    wide in X) under a thin full-width top mounting flange with rounded corner ears
    and four Ø4.4 mounting holes (84 x 30.6 pattern). Centred X/Y, top at z=0."""
    coil = box_at(PK_COIL_W, PK_L, PK_H, z=-PK_H / 2)           # thick sensing core
    flange = (box_at(PK_W, PK_L, PK_FLG_T, z=-PK_FLG_T / 2)     # thin ear plate on top
              .edges("|Z").fillet(6.0))                          # rounded corner ears
    body = coil.union(flange)
    for hx, hy in EAR_HOLES:                                     # the pickup's own 4 mounting holes
        body = body.cut(cyl(EAR_HOLE_D, PK_H + 2, z=-PK_H - 1)
                        .translate((hx, hy, 0)))
    return body

