"""Belt-tension lock forks — a graded set of tiny printed plugs (§ motors).

The motor mounts are friction clamps in slotted holes; the slots point at the
screw pulley, so long-term clamp creep could let a motor walk +X and slacken
its belt. A direct tensioner (set screw / U-channel) doesn't fit: the staircase
packs motors 1.7 mm apart in X. Instead, the slots stay (continuous tension),
and after torquing a motor, a FORK of the matching size slips into each slot's
open +X remainder, between the M3 shank and the slot's end wall. Belt tension
then bears screw → fork → solid wall: a positive mechanical stop, no friction
reliance. To re-tension: loosen, pull the forks, slide, re-fork.

The tensioned gap is always 2.2..4.2 mm (slot half-length 3.7, shank +X edge at
travel −2..0 → +1.5..+3.5), so the set runs L = 2.0..4.0 in 0.2 steps: pick the
longest that drops in; residual play ≤ 0.2 mm. Body height 3.25 slips the
3.4 slot; depth stops 0.3 shy of the motor face; a 1.2 head flange stays proud
on the +Y wall face for fingernail removal. One STEP = the whole 11-size set
(separate bodies; print the plate flat, 4 forks of the chosen size per motor).
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import motor_bank as MB
from .helpers import box_at

BODY_H   = D.M3_CLR_D - 0.15     # slips the slot height
BODY_D   = MB.PLATE_T - 0.3      # wall thickness minus motor-face clearance
HEAD_T   = 1.2                   # flange proud of the wall's +Y face
HEAD_H   = 5.0
SIZES    = [round(2.0 + 0.2 * i, 1) for i in range(11)]   # 2.0 .. 4.0


def _fork(L: float) -> cq.Workplane:
    body = box_at(L, BODY_D, BODY_H, x=L / 2, y=BODY_D / 2, z=BODY_H / 2)
    head = box_at(L, HEAD_T, HEAD_H, x=L / 2, y=-HEAD_T / 2, z=HEAD_H / 2)
    return body.union(head)


def _build() -> cq.Workplane:
    out = cq.Workplane("XY")
    for i, L in enumerate(SIZES):
        out = out.add(_fork(L).translate((i * 7.0, 0, 0)))
    return out


tension_forks = _build()
