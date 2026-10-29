# -*- coding: utf-8 -*-
"""A PRINTED HACKSAW JIG for cutting each SERVO42D's shaft to components.MOTOR_SHAFT_CUT_L.

SHOP TOOL, not a part of the instrument. The leadscrew saw jig's sibling (src/saw_jig.py),
and it works the same way (user, 2026-10-29): "the same design but using the shape we have
in the chassis that holds the motor in place. Like the lead screw I'd expect a lid that you
clamp down on to lock the motor onto a table. Also expecting a channel for the saw so it
cuts evenly." And: "The screws are cumbersome when you want to cut 10 motors in a row." So
nothing screws into the motor: undo the clamp, lift the lid, swap the motor, re-clamp.

TWO PRINTED PARTS, NOTHING BOUGHT. Shaft along +Y, the motor's faceplate at y = 0, the table
at z = 0. The motor lies as it does in the instrument, on its driver's cover.

  BODY   the chassis' own motor bay, as a block: motor_bank.lift_prism (the bay's two widths,
         its fits and its back step) and motor_bank.low_walls (the bay's relief beside the
         green terminals, so a wired motor goes in too) cut out of it, and the bay's faceplate
         wall with its boss slot (motor_bank.BOSS_CLR) -- none of it redrawn here. The motor is
         pushed home on that wall, which the cut is measured from.
         The wall runs on CUT_L to the SAW SLOT (SLOT_W, the leadscrew jig's blade), open
         across the whole width, and a +Y CHEEK past it: the blade has a wall on both sides.
         The shaft lies in a U channel through both, open at the top for the drop-in.
  CAP    a plunger down the bay's opening onto the driver's cover, the way saw_jig's cap goes
         down its channel. The Quick-Grip's pad goes on its flat top (see CAP_UP for why no
         rimmed pocket), so the clamp squeezes cap -> motor -> base -> table in one stack. An ARM over the faceplate wall
         carries a TONGUE down the shaft channel to just over the shaft's D FLAT: the shaft
         cannot turn under the blade, and the channel is closed between the saw and the
         motor. Its relief over the coil plug and its leads is read off the motor's model.

CHIPS. The cap closes the boss slot and the shaft channel from the faceplate to the slot's
face, so the only way from the saw to the bearing seal and the magnet gap is along the shaft
inside a closed channel. INSTALL_NOTES: magnet the filings off before the cap comes up.

THE CUT. The slot's motor-side face is at CUT_L, so the blade cannot cut the stub short. It
comes out between CUT_L and CUT_L + (SLOT_W - kerf), and the file takes it to CUT_L.
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
FLOOR_T = 4 * B                                    # 3.2 under the cover
AXIS_Z = FLOOR_T + SV.DRV_HALF                     # 24.45: the motor on its 42.5 cover
COVER_TOP = AXIS_Z + SV.DRV_HALF                   # 45.7: what the cap bears on
SHAFT_R = D.MOTOR_SHAFT_D / 2.0                    # 2.5
FLAT_Z = D.MOTOR_SHAFT_FLAT - SHAFT_R              # 2.0: the D's flat over the axis
FLAT_Y0 = SV.SHAFT_L - D.MOTOR_SHAFT_FLAT_L        # 3.5: where the flat starts off the face
BOSS_W = D.NEMA17_PILOT_D + 2 * MB.BOSS_CLR        # 22.8: the bay's boss slot
BOSS_D = SV.PILOT_H + B / 2.0                      # 2.4 deep off the face
CUT_L = C.MOTOR_SHAFT_CUT_L                        # 15.6

# ── the saw: the leadscrew jig's blade and slot ─────────────────────────────
SLOT_W = SJ.SLOT_W                                 # 1.3, McMaster 6927A16
SLOT_UNDER = SJ.SLOT_UNDER                         # 2.4 under the shaft
SLOT_FLOOR_Z = AXIS_Z - SHAFT_R - SLOT_UNDER
CHEEK_T = SJ.CHEEK_T                               # 3.2, the +Y cheek
CH_CLR = 0.1                                       # the shaft channel round the shaft
CH_HW = SHAFT_R + CH_CLR

# ── the body ────────────────────────────────────────────────────────────────
WALL = 4 * B                                       # 3.2 round the bay
LID_ENGAGE = 6 * B                                 # 4.8: the bay's walls over the cover
Z_TOP = COVER_TOP + LID_ENGAGE
Y1 = CUT_L + SLOT_W + CHEEK_T                      # the +Y cheek's outer face
BODY_UP = (0.0, 0.0, 1.0)                          # as drawn, table face on the bed

# ── the cap ─────────────────────────────────────────────────────────────────
CAP_CLR = SJ.CAP_CLR                               # 0.3, its slide in the bay
TONGUE_CLR = 0.1                                   # the tongue over the flat
ARM_GAP = SJ.CAP_CLR                               # the arm's underside over the wall's top
ARM_T = 12 * B                                     # 9.6
CAP_TOP = Z_TOP + ARM_GAP + ARM_T
RELIEF_CLR = 2 * B                                 # round the coil plug and its leads
# PRINT ORIENTATION: upside down, its flat top on the bed -- the plunger, the arm, the boss plug
# and the tongue all stand up off it and every face is a wall or a floor. That is why the top
# is FLAT, with no rimmed pad pocket like saw_jig's cap: upside down the pocket's floor would be
# a 27 x 20 bridge, and standing on an end instead makes the tongue's and the plug's ends 10 mm
# ceilings. The Quick-Grip's pad goes anywhere on the 42 x 53 top; all of it is over the cover.
CAP_UP = (0.0, 0.0, -1.0)


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


def body() -> cq.Workplane:
    hw = _bay_hw() + WALL
    y0 = _back_y() - MB.BACK_T
    blk = box_at(2 * hw, Y1 - y0, Z_TOP, y=(Y1 + y0) / 2.0, z=Z_TOP / 2.0)
    blk = blk.cut(_bay_to_jig(MB.lift_prism(MB.COUPON_MOTOR)))
    # the terminal relief: the bay's own box, run on up through the jig's top (in the chassis
    # it stops at the tee seat, which here would leave a 1.25 shelf hanging over it)
    lw = _bay_to_jig(MB.low_walls(MB.COUPON_MOTOR)).val().BoundingBox()
    blk = blk.cut(box_at(lw.xlen, lw.ylen, Z_TOP + 1.0 - lw.zmin, x=(lw.xmin + lw.xmax) / 2.0,
                         y=(lw.ymin + lw.ymax) / 2.0, z=(lw.zmin + Z_TOP + 1.0) / 2.0))
    blk = blk.cut(_u(BOSS_W / 2.0, -1.0, BOSS_D, AXIS_Z))           # the boss slot
    blk = blk.cut(_u(CH_HW, BOSS_D - 0.5, Y1 + 1.0, AXIS_Z))        # the shaft channel
    blk = blk.cut(box_at(2 * hw + 2.0, SLOT_W, Z_TOP - SLOT_FLOOR_Z + 1.0,
                         y=CUT_L + SLOT_W / 2.0, z=(SLOT_FLOOR_Z + Z_TOP + 1.0) / 2.0))
    return blk


def _relief():
    """What of the motor stands over its cover (coil socket, plug, lead loop), grown by
    RELIEF_CLR, as a box -- read off the model, not typed."""
    parts = None
    for _k, wp, _rgb, _fin in C.motor_parts():
        parts = wp if parts is None else parts.union(wp)
    over = _local_to_jig(parts).intersect(box_at(200, 200, 100, z=COVER_TOP + 0.01 + 50.0))
    b = over.val().BoundingBox()
    return (b.xmin - RELIEF_CLR, b.xmax + RELIEF_CLR, b.ymin - RELIEF_CLR, b.ymax + RELIEF_CLR,
            b.zmax + RELIEF_CLR)


def cap() -> cq.Workplane:
    # the plunger: the bay's NARROW section (the can's), less CAP_CLR a side, so one width
    # slides the whole bay; from the back fit to the faceplate wall
    pw = SV.SQ + 2 * MB.SIDE_FIT - 2 * CAP_CLR
    py0, py1 = _back_y() + CAP_CLR, -CAP_CLR
    c = box_at(pw, py1 - py0, CAP_TOP - COVER_TOP, y=(py0 + py1) / 2.0,
               z=(COVER_TOP + CAP_TOP) / 2.0)
    # the arm over the faceplate wall, to the slot's face
    za = Z_TOP + ARM_GAP
    c = c.union(box_at(pw, CUT_L - py1, CAP_TOP - za, y=(py1 + CUT_L) / 2.0,
                       z=(za + CAP_TOP) / 2.0))
    # the boss slot's plug, down to over the boss -- CAP_CLR off the wall's face, where the
    # motor's faceplate stands
    zb = AXIS_Z + D.NEMA17_PILOT_D / 2.0 + TONGUE_CLR
    by0, by1 = CAP_CLR, BOSS_D - CAP_CLR
    c = c.union(box_at(BOSS_W - 2 * CAP_CLR, by1 - by0, za - zb + 0.01,
                       y=(by0 + by1) / 2.0, z=(zb + za) / 2.0))
    # the TONGUE down the shaft channel, TONGUE_CLR over the shaft's round part and then over
    # its D FLAT, so the shaft cannot turn under the blade
    tw = 2 * (CH_HW - TONGUE_CLR)
    zf = AXIS_Z + FLAT_Z + TONGUE_CLR
    zr = AXIS_Z + SHAFT_R + TONGUE_CLR
    yf = FLAT_Y0 + 2 * B                               # on the flat past its runout
    assert CUT_L - yf >= 4 * B, "under four beads of tongue on the flat"
    c = c.union(box_at(tw, CUT_L - by1, za - zr + 0.01, y=(by1 + CUT_L) / 2.0, z=(zr + za) / 2.0))
    c = c.union(box_at(tw, CUT_L - yf, zr - zf + 0.01, y=(yf + CUT_L) / 2.0, z=(zf + zr) / 2.0))
    # the relief over the coil plug and its leads
    rx0, rx1, ry0, ry1, rz1 = _relief()
    assert rz1 + 4 * B <= CAP_TOP, "the cap is too thin over the coil lead's loop"
    c = c.cut(box_at(rx1 - rx0, ry1 - ry0, rz1 - COVER_TOP + 1.0,
                     x=(rx0 + rx1) / 2.0, y=(ry0 + ry1) / 2.0, z=(COVER_TOP - 1.0 + rz1) / 2.0))
    return c


def motor() -> cq.Workplane:
    """The SERVO42D, shaft cut, seated -- for checking only."""
    parts = None
    for _k, wp, _rgb, _fin in C.motor_parts():
        parts = wp if parts is None else parts.union(wp)
    return _local_to_jig(parts)
