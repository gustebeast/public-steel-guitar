# -*- coding: utf-8 -*-
"""A PRINTED HACKSAW JIG for cutting each SERVO42D's shaft to components.MOTOR_SHAFT_CUT_L.

SHOP TOOL, not a part of the instrument. The leadscrew saw jig's sibling (src/saw_jig.py):
"the same design but using the shape we have in the chassis that holds the motor in place"
(user, 2026-10-29). Nothing screws into the motor -- "the screws are cumbersome when you
want to cut 10 motors in a row".

ONE PRINTED PART, NO CAP (user, 2026-10-29: "we don't need the cap at all, I can just clamp
the motor directly since the clamp has a soft pad on it"). The leadscrew needed its cap
because it is round; the motor is a 42 mm square in a bay of its own shape, so the Quick-Grip
goes straight onto the driver's cover and squeezes motor -> jig -> table. Undo it, lift the
motor out, drop the next one in, re-clamp.

LEAN (user, 2026-10-29). Shaft along +Y, the motor's faceplate at y = 0, the table at z = 0.
  FLOOR   MIN_WALL_2P under everything.
  BAY     the chassis' own motor bay (motor_bank.lift_prism, and low_walls' relief beside the
          green terminals) in MIN_WALL_2P walls, standing only to the SHAFT'S AXIS: enough to
          seat the can and to give the shaft a solid bed, no higher.
  LIP     a MIN_WALL_2P stop the faceplate is pushed home on, with the bay's boss slot
          through it. It replaces the solid block that ran from the faceplate to the cut.
  CRADLE  a solid rib under the WHOLE shaft, faceplate to past its tip, a half-round trough
          to the axis.
  CHEEKS  the saw slot (SLOT_W, the leadscrew jig's blade) with a CHEEK_T wall each side,
          full height -- they take the blade's side load.
  GUSSETS the motor-side cheek lost the block behind it, so two 45 deg gussets (CHEEK_T
          thick, on CHEEK_T side rails at the bay's outer faces) tie it back to the lip.

THE CUT. The slot's motor-side face is at CUT_L, so the blade cannot cut the stub short. It
comes out between CUT_L and CUT_L + (SLOT_W - kerf), and the file takes it to CUT_L.
THE SHAFT IS FREE TO TURN (the cap's tongue on the D flat went with the cap); the motor's
detent holds it, or a finger on the stub past the saw.
"""
from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import components as C
from . import motor_bank as MB
from . import saw_jig as SJ
from . import servo42d as SV
from .helpers import box_at

B = D.BEAD

# ── the motor, in the jig frame (faceplate y = 0, shaft +Y, table z = 0) ────
FLOOR_T = D.MIN_WALL_2P                            # 1.6 under the cover
AXIS_Z = FLOOR_T + SV.DRV_HALF                     # 22.85: the motor on its 42.5 cover
COVER_TOP = AXIS_Z + SV.DRV_HALF                   # 45.7: what the cap bears on
SHAFT_R = D.MOTOR_SHAFT_D / 2.0                    # 2.5
BOSS_W = D.NEMA17_PILOT_D + 2 * MB.BOSS_CLR        # 22.8: the bay's boss slot
BOSS_D = SV.PILOT_H + B / 2.0                      # 2.4 deep off the face
CUT_L = C.MOTOR_SHAFT_CUT_L                        # 20.8 at the held 17.2 standoff (15.6 at 12.0)

# ── the saw: the leadscrew jig's blade and slot ─────────────────────────────
SLOT_W = SJ.SLOT_W                                 # 1.3, McMaster 6927A16
SLOT_UNDER = SJ.SLOT_UNDER                         # 2.4 under the shaft
SLOT_FLOOR_Z = AXIS_Z - SHAFT_R - SLOT_UNDER
CHEEK_T = SJ.CHEEK_T                               # 3.2, the +Y cheek
CH_CLR = 0.1                                       # the shaft channel round the shaft
CH_HW = SHAFT_R + CH_CLR

# ── the body ────────────────────────────────────────────────────────────────
WALL = D.MIN_WALL_2P                               # 1.6: bay walls and lip
LIP_T = D.MIN_WALL_2P                              # the faceplate's stop, along Y
RIB_W = 2 * (CH_HW + D.MIN_WALL_2P)                # the shaft's cradle rib, across
BED_Z = AXIS_Z                                     # bay, lip and cradle stop at the shaft's axis
LID_ENGAGE = 6 * B                                 # the cheeks' reach over the cover (as before)
Z_TOP = COVER_TOP + LID_ENGAGE                     # the cheeks' top
SHAFT_TIP_Y = SV.SHAFT_L                           # the uncut shaft's tip off the faceplate
Y1 = max(CUT_L + SLOT_W + CHEEK_T, SHAFT_TIP_Y + D.MIN_WALL_2P)   # the +Y cheek's outer face
BODY_UP = (0.0, 0.0, 1.0)                          # as drawn, table face on the bed


def _local_to_jig(wp):
    """The motor's own frame (components.motor_parts: faceplate at -MOTOR_PULLEY_STANDOFF, axis
    on z = 0) into this one."""
    return wp.translate((0.0, C.MOTOR_PULLEY_STANDOFF, AXIS_Z))


def _bay_to_jig(wp, i=MB.COUPON_MOTOR):
    """A cutter of motor i's bay in WORLD into this frame. The bay's front fit (MOTOR_CLR past
    the faceplate) becomes the wall the faceplate is pushed home on, and its floor the motor's
    true rest on its 42.5 cover (the bay's is the 42.3 nominal's)."""
    mx, my, mz = D.motor_pos(i)
    face_w = MB.body_box(i)[3] + MB.MOTOR_CLR          # the bay's wall face, world
    floor_w = MB.body_box(i)[4]                        # the bay's floor, world
    return wp.translate((-mx, -face_w, FLOOR_T - floor_w))


def _u(hw, y0, y1, z_bot_axis, x=0.0):
    """A U channel down to a round bottom of radius `hw` about the axis, open to the top."""
    r = cq.Workplane("XZ").center(x, z_bot_axis).circle(hw).extrude(-(y1 - y0)).translate((0, y0, 0))
    return r.union(box_at(2 * hw, y1 - y0, Z_TOP + 50.0 - z_bot_axis,
                          x=x, y=(y0 + y1) / 2.0, z=(z_bot_axis + Z_TOP + 50.0) / 2.0))


def _bay_hw():
    return (D.MOTOR_SQ + 2 * MB.MOTOR_CLR) / 2.0


def _back_y():
    return -(D.MOTOR_BODY_L + 2 * MB.MOTOR_CLR)       # the bay's rear fit, from the wall face


def _gusset(x0, x1, y0, y1, z0):
    """A 45 deg gusset in YZ, x0..x1 thick: rises from (y0, z0) to (y1, z0 + y1 - y0)."""
    h = y1 - y0
    return (cq.Workplane("YZ").polyline([(y0, z0), (y1, z0), (y1, z0 + h)]).close()
            .extrude(x1 - x0).translate((x0, 0, 0)))


def body() -> cq.Workplane:
    hw = _bay_hw() + WALL
    y0 = _back_y() - WALL
    cy0 = CUT_L - CHEEK_T                             # the motor-side cheek's back face
    assert cy0 - LIP_T >= 2 * B, "no room between the lip and the motor-side cheek"
    # the bay: floor + walls to the axis, the motor's prism cut out
    blk = box_at(2 * hw, -y0, BED_Z, y=y0 / 2.0, z=BED_Z / 2.0)
    blk = blk.cut(_bay_to_jig(MB.lift_prism(MB.COUPON_MOTOR)))
    lw = _bay_to_jig(MB.low_walls(MB.COUPON_MOTOR)).val().BoundingBox()
    blk = blk.cut(box_at(lw.xlen, lw.ylen, Z_TOP + 1.0 - lw.zmin, x=(lw.xmin + lw.xmax) / 2.0,
                         y=(lw.ymin + lw.ymax) / 2.0, z=(lw.zmin + Z_TOP + 1.0) / 2.0))
    # forward of the faceplate: floor, lip, cradle rib, the two cheeks
    blk = blk.union(box_at(2 * hw, Y1, FLOOR_T, y=Y1 / 2.0, z=FLOOR_T / 2.0))
    blk = blk.union(box_at(2 * hw, LIP_T, BED_Z, y=LIP_T / 2.0, z=BED_Z / 2.0))
    blk = blk.union(box_at(RIB_W, Y1, BED_Z, y=Y1 / 2.0, z=BED_Z / 2.0))
    # the cheeks are ONE block, motor-side cheek to +Y cheek; the saw slot is cut into it from
    # SLOT_UNDER under the shaft upward, so below that it is solid wall to wall (user, 2026-10-29:
    # "the slit only needs to run as low as the shaft ... the saw blade never goes there")
    yc1 = CUT_L + SLOT_W + CHEEK_T                   # the +Y cheek's outer face; past it, only the
    blk = blk.union(box_at(2 * hw, yc1 - cy0, Z_TOP, y=(cy0 + yc1) / 2.0, z=Z_TOP / 2.0))  # cradle
    # the struts: a side rail at each outer face, lip to cheek, then a 45 deg gusset off its
    # top up the cheek's back -- as high as the run allows, never past the cheek's top
    rise = min(cy0, Z_TOP - BED_Z)
    for sx in (-1.0, 1.0):
        x0, x1 = (hw - CHEEK_T, hw) if sx > 0 else (-hw, -hw + CHEEK_T)
        blk = blk.union(box_at(CHEEK_T, cy0, BED_Z, x=(x0 + x1) / 2.0, y=cy0 / 2.0,
                               z=BED_Z / 2.0))
        blk = blk.union(_gusset(x0, x1, cy0 - rise, cy0 + 0.01, BED_Z - 0.01))
    blk = blk.cut(_u(BOSS_W / 2.0, -1.0, BOSS_D, AXIS_Z))           # the boss slot
    blk = blk.cut(_u(CH_HW, BOSS_D - 0.5, Y1 + 1.0, AXIS_Z))        # the shaft channel
    blk = blk.cut(box_at(2 * hw + 2.0, SLOT_W, Z_TOP - SLOT_FLOOR_Z + 1.0,
                         y=CUT_L + SLOT_W / 2.0, z=(SLOT_FLOOR_Z + Z_TOP + 1.0) / 2.0))
    vals = blk.solids().vals()
    assert len(vals) == 1, f"the jig fell apart into {len(vals)} solids"
    return blk


def motor() -> cq.Workplane:
    """The SERVO42D, shaft cut, seated -- for checking only."""
    parts = None
    for _k, wp, _rgb, _fin in C.motor_parts():
        parts = wp if parts is None else parts.union(wp)
    return _local_to_jig(parts)
