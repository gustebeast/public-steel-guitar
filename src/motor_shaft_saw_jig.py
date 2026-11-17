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
  BAY     the chassis' own motor bay (lift_prism, and low_walls' relief beside the
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

import math

import cadquery as cq

from . import dimensions as D
from . import components as C
from .components import MOTOR_PULLEY_STANDOFF
from . import saw_jig as SJ
from . import servo42d as SV
from .helpers import box_at

B = D.BEAD

# ── THE BAY: the v1 chassis' motor bay, which this jig reproduces ────────────────────────
# Lifted out of src/motor_bank.py when the v1 body went (lead, 2026-11-17, v1 removal round 3,
# git tag v1-instrument): the motor's pose (D.motor_pos), its body box, the lift prism and the
# low-wall relief, exactly as the bank cut them. The jig reads them for COUPON_MOTOR only.
BOARD_AIR  = 0.0                 # the tee board's underside ON the CAN's real top (user, coupon
                                 # board/2 + wall + fit outside the board, and the neighbour's body
                                 # is at MOTOR_SQ/2 + MOTOR_GAP (wiring asserts the board still fits)
MOTOR_CLR  = D.MOTOR_CLR         # slip fit round a PURCHASED body (the gap is sized from it)
BOSS_CLR   = 0.4                 # round the O22 pilot boss in its drop-in slot
# THE SIDE FIT, PER SECTION (coupon round 2, user 2026-10-20). MOTOR_CLR round the 42.3
# nominal is 0.3 a side round the real 42.5 driver cover -- "good" -- and 0.55 round the 42.0
# can -- "loose ... it can wobble". The can gets the cover's 0.3 too, from CAN_NARROW_LEAD in
# front of the cover/can transition forward (lift_prism).
SIDE_FIT   = (D.MOTOR_SQ + 2 * D.MOTOR_CLR - D.MOTOR_DRIVER_SQ_MEASURED) / 2      # 0.3
CAN_NARROW_LEAD = 3 * D.BEAD     # 2.4: the narrowing starts this far in front of the cover
BACK_STEP_H = 16 * D.BEAD        # 12.8: the low back stop's height in the pocket (over BUMP_H)
BACK_T     = 4 * D.BEAD          # 3.2 back wall: nothing pushes the motor -Y, so it is a stop,
BUMP_H     = 14 * D.BEAD         # 11.2 tall: the ONE low-wall height (user, 2026-10-20) -- the
# THE POCKET'S -Y LIMIT. The bank is staggered, so the -Y-most motors' backs run right down to
# the -Y rail -- and that strip is the HARNESS CORRIDOR: the tee boards on their cradles and the
# six stacked trunk lanes. Nothing of a pocket may enter it (the first cut of this design put
# 15 clashes there, including motor 9's tee screw buried in chassis). So the back features stop
# here, and where that leaves no room they are simply dropped: what stops those motors going -Y
# is the rail itself, 2.0 behind string 10's back (user: merge the back wall into the chassis
# wall on the high strings). wiring.py asserts this against where the tees and lanes really are.
# It was -108.75, the TEE BOARDS' +Y edge -- but the bus-A tees sit on their motors now, and no
# rail-mounted board lies within the bank's X span (wiring asserts it), so what remains along
# here is the trunk WIRES: RAIL_Y -124.25 plus the fattest trunk conductor's radius, -122.95.
# Pulling the keep-out back to -122.4 hands 14 mm of Y to the bays, which is what lets the
# -Y-most ones have a back wall like everyone else instead of being a special case (user).
# THE CORRIDOR IS GONE (user, 2026-10-29: the body narrowed to D.MOTOR_INSTALL_CLR behind
# string 10's motor). The trunk rides the trough over the motor tops, and nothing runs at floor
# level along the bank's -Y edge any more, so the keep-out is the rail's own inner face: the
# bays reach the rail (string 10's back wall merges into it) and the corridor cut is empty.
M10_BACK_Y = D.string_y(D.N_STRINGS - 1) - MOTOR_PULLEY_STANDOFF - D.MOTOR_BODY_L   # -113.15
# THE -Y RAIL'S INNER FACE, off string 10's motor back by the LARGER of the two needs (lead,
# 2026-10-29), each in whole beads: the motor's install room (D.MOTOR_INSTALL_CLR) and the
# Pi's USB-C plug, PI_PLUG_CLR off its -Y extent (rounded OUT to a bead, never a pocket).
_PI_PLUG_NEED = math.ceil((M10_BACK_Y - (D.PI_PLUG_Y0 - D.PI_PLUG_CLR)) / D.BEAD - 1e-9) * D.BEAD
_OP_W = 56.0  # FROZEN, v1: motor_bank._OP_W = _BG.load("output_panel")["outline_mm"][1] (tag v1-instrument)
_OP_EDGE_LIM = D.string_y(D.N_STRINGS - 1) - D.PULLEY_FLANGE_OD / 2 - D.OP_PULLEY_CLR
_OP_NEED = math.ceil((M10_BACK_Y - (_OP_EDGE_LIM - _OP_W - D.OP_PANEL_CLR)) / D.BEAD - 1e-9) * D.BEAD
RAIL_BACK_CLR = max(D.MOTOR_INSTALL_CLR, _PI_PLUG_NEED, _OP_NEED)
RAIL_INNER_Y = M10_BACK_Y - RAIL_BACK_CLR
_zc = D.MOTOR_BELT_Z
FLOOR_TOP = _zc - D.MOTOR_SQ / 2            # motors rest here (= wall bottom / chassis rib top)
                                                # underside; FLOOR_TOP is that prism's top
# THE TEE SEAT PLANE: the board rests here and laps the motor by BOARD_AIR of air -- off the
# REAL can: the motor stands on its driver's cover (the lowest flat), so the can's top is
# FLOOR_TOP + cover/2 + can/2, not FLOOR_TOP + the 42.3 nominal
Z_HI = (FLOOR_TOP + (D.MOTOR_DRIVER_SQ_MEASURED + D.MOTOR_SQ_MEASURED) / 2 + BOARD_AIR)
SEAT_TOP = Z_HI + D.TEE_BOARD_T + D.TEE_WALL_OVER  # ...and the bay runs this far over it, so the


def lift_prism(i):
    """Motor i's way out: its footprint swept +Z from ITS OWN UNDERSIDE. Cut it from
    anything built over a motor.

    STOPS AT THE MOTOR'S BOTTOM (user, 2026-09-15). It used to reach 100 below, from when this
    was cut only from the tee CRADLE -- a separate part with a base hanging below the seat plane,
    which had to come out of the motor's fit gap. The cradle is gone (the bay IS the seat) and
    the CHASSIS now cuts this from the fused segments, so those 100 mm were hollowing every
    motor's footprint down through the ribs the motor rests on: FLOOR_TOP is the rib tops.
    A motor slides in from +Z, so its swept volume starts at its own underside and nothing
    below that line is in its way."""
    from . import servo42d as SV
    bx0, bx1, by0, by1, bz0, bz1 = body_box(i)
    mx = (bx0 + bx1) / 2
    z0, z1 = bz0, bz1 + 300.0
    # TWO WIDTHS (coupon round 2, user 2026-10-20): the driver's cover is 42.5 and the can
    # 42.0, and one fit round both left the can loose ("it can wobble a bit") while the cover's
    # 0.3 a side was good. So the can gets the cover's fit: the pocket narrows by their
    # difference CAN_NARROW_LEAD in front of the transition (user: "a little after").
    ym = by1 + SV.DRV_Y0 + CAN_NARROW_LEAD
    rear = box_at(bx1 - bx0 + 2 * MOTOR_CLR, ym - (by0 - MOTOR_CLR), z1 - z0,
                  x=mx, y=(ym + by0 - MOTOR_CLR) / 2, z=(z0 + z1) / 2)
    # ...AND TWO LENGTHS (coupon round 2, user: "slides 2mm forward/back"). The driver's ribs
    # reach 53.2 back, but only above SV.BAND_Z1; under them the back is the two lower screw
    # heads at 51.6, and that is all the BUMP_H back wall ever meets. So up to BACK_STEP_Z the
    # pocket stops LOWER_L + MOTOR_CLR behind the faceplate. A motor drops in from +Z, so its
    # ribs never come lower than they sit, and the step cannot catch them.
    zs = bz0 + BACK_STEP_H
    rib_z = D.motor_pos(i)[2] + SV.BAND_Z1                 # the ribs' lowest line, seated
    assert zs < rib_z - SV.RIB_T, "the back step reaches the ribs' height"
    rear = rear.cut(box_at(bx1 - bx0 + 4.0, SV.TOTAL_L - SV.LOWER_L, zs - z0 + 1.0,
                           x=mx, y=by1 - (SV.TOTAL_L + SV.LOWER_L) / 2 - MOTOR_CLR,
                           z=(z0 - 1.0 + zs) / 2))
    yf = by1 + MOTOR_CLR
    front = box_at(SV.SQ + 2 * SIDE_FIT, yf - ym + 0.01, z1 - z0,
                   x=mx, y=(yf + ym - 0.01) / 2, z=(z0 + z1) / 2)
    return rear.union(front)


def body_box(i):
    """The motor body's own envelope (x0, x1, y0, y1, z0, z1) -- what the pocket wraps.
    The boss and shaft stick out +Y of y1 and are NOT in here; they live in the wall's slot."""
    mx, my, mz = D.motor_pos(i)
    y1 = my - MOTOR_PULLEY_STANDOFF                      # faceplate = the wall's -Y face
    return (mx - D.MOTOR_SQ / 2, mx + D.MOTOR_SQ / 2,
            y1 - D.MOTOR_BODY_L, y1,
            mz - D.MOTOR_SQ / 2, mz + D.MOTOR_SQ / 2)


# THE SIDE TERMINALS' RELIEF (user, 2026-10-20). The SERVO42D takes 24 V and CAN on green
# screw terminals whose wires enter from the SIDES, 1.3 inside the can's flats -- and a bay wall
# standing the full height put a wall 0.35 off every wire end. Wired and bent flat it does
# fit inside the square, but too close (user), so beside each block the bay's side wall stops
# BELOW the block. The block heights were measured roughly (user: give it extra clearance), so
# the wall stops at least TERM_RELIEF_CLR under the LOWER block (the 6-way, bottom 13.1; the
# 5-way's is 16.7), and both sides and the back wall share that one height, BUMP_H 11.2: the
# staggered bays share walls, and three heights left steps and tabs where they met (user).
# It runs from a fit in front of the block to past the back. Cut from the FUSED chassis (like lift_prism): the wall between two
# motors is in both bays' prisms.
TERM_RELIEF_CLR = 2 * D.BEAD      # 1.6 at least, wall top to the block's measured bottom
TERM_RELIEF_FIT = 2 * D.BEAD      # 1.6 of relief in front of the block's motor-side face


def term_wall_h():
    """The wall height left beside both green blocks: BUMP_H, checked under the lower block."""
    from . import servo42d as SV
    assert BUMP_H <= min(SV.TERM_BOTTOM.values()) - TERM_RELIEF_CLR + 1e-9, \
        "the low walls reach within TERM_RELIEF_CLR of a terminal block"
    return BUMP_H


def back_wall_y0(i):
    """-Y face of motor i's back wall."""
    return body_box(i)[2] - BACK_T


def low_walls(i):
    """ONE cut per motor: everything over BUMP_H from in front of its green terminals back past
    its back wall, across the whole bay. That is both side walls beside the blocks AND the back
    wall (the driver's connector and the motor's coil lead want the upper back open). Inside
    the motor's fit there is nothing left for it to take -- lift_prism has emptied it -- so one
    box does what three did. It reaches 1.0 past the bay each way, into air: the neighbours'
    fits, or (string 10) open air. Cut from the FUSED chassis, after lift_prism: the wall
    between two motors is in both bays' prisms and a per-bay cut would be refilled."""
    from . import servo42d as SV
    bx0, bx1, by0, by1, bz0, bz1 = body_box(i)
    ya = by1 + SV.TERM_Y0 + TERM_RELIEF_FIT          # by1 is the faceplate
    yb = max(back_wall_y0(i) - 1.0, RAIL_INNER_Y)   # never into the -Y rail (string 10's)
    x0, x1 = bx0 - side_room(i, -1) - 1.0, bx1 + side_room(i, 1) + 1.0
    z0, z1 = bz0 + term_wall_h(), SEAT_TOP + 1.0
    return box_at(x1 - x0, ya - yb, z1 - z0, x=(x0 + x1) / 2, y=(ya + yb) / 2, z=(z0 + z1) / 2)


def side_room(i, sgn):
    """How much X this motor's bay claims on one side: the WHOLE gap less the neighbour's fit,
    which is 1.6 of wall either way.

    Not half each. Halves would meet and fuse into 1.6 only where both bays exist -- and the
    bank is STAGGERED, so over the last 9.5 of every bay the neighbour has ended and a half wall
    stands alone at 0.8 (the user's rule, broken in the stagger bands). Claiming the whole gap
    makes both bays describe the SAME 1.6 wall, which is the honest description of it: one wall
    between two motors, not two half walls. The chassis cuts every motor's lift path out of the
    fused result, so a bay reaching across the gap never fills its neighbour's fit."""
    other = D.MOTOR_END_CLR if (sgn < 0 and i == 0) else D.MOTOR_GAP
    if sgn > 0 and i == D.N_STRINGS - 1:
        return MOTOR_CLR + D.MIN_WALL_2P          # open air past the last motor
    return other - MOTOR_CLR

# ── THE BAY FIT COUPON (user, 2026-10-20) ─────────────────────────────────────────────────
# Proves the measured motor fits its bay AND that the tee board clamps it, before ten bays go
# into chassis prints. Round 1 was the low walls alone; round 2 (user: "the full contact area
# on the motor ... and a way to test the top clamp ... I do want a floor") is the WHOLE bay of
# one motor, up through the tee seat, plus a printed stand-in for the tee board.
#
# THE REAL GEOMETRY, BY THE CHASSIS' OWN RECIPE: string 5's plate fused with both neighbours'
# (the shared walls and the post are in two plates), then every one of the three motors' lift
# path, low walls and tee pocket out of the fused result, then the M4 hold-down re-bored --
# chassis.py and build.py in that order. Nothing here re-models a face the motor or the board
# touches.
#
# ...THEN TRIMMED FOR MATERIAL. Outside a COUPON_WALL ring round the motor's fit everything
# goes, except under the board's seat: there the faceplate wall's top (the board's +Y band
# rests on it) and the +X post (the ear and its M4 insert) stay whole down to the anchor's
# floor, and below that a 45 deg corbel steps them back to the ring, so nothing hangs. The
# floor is the motor's rest plane at COUPON_FLOOR_T, a RIM round the footprint with the middle
# open: the motor's height under the board is what it sets, and a rim sets it.
COUPON_MOTOR = 4

# ── the motor, in the jig frame (faceplate y = 0, shaft +Y, table z = 0) ────
FLOOR_T = D.MIN_WALL_2P                            # 1.6 under the cover
AXIS_Z = FLOOR_T + SV.DRV_HALF                     # 22.85: the motor on its 42.5 cover
COVER_TOP = AXIS_Z + SV.DRV_HALF                   # 45.7: what the cap bears on
SHAFT_R = D.MOTOR_SHAFT_D / 2.0                    # 2.5
BOSS_W = D.NEMA17_PILOT_D + 2 * BOSS_CLR        # 22.8: the bay's boss slot
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


def _bay_to_jig(wp, i=COUPON_MOTOR):
    """A cutter of motor i's bay in WORLD into this frame. The bay's front fit (MOTOR_CLR past
    the faceplate) becomes the wall the faceplate is pushed home on, and its floor the motor's
    true rest on its 42.5 cover (the bay's is the 42.3 nominal's)."""
    mx, my, mz = D.motor_pos(i)
    face_w = body_box(i)[3] + MOTOR_CLR          # the bay's wall face, world
    floor_w = body_box(i)[4]                        # the bay's floor, world
    return wp.translate((-mx, -face_w, FLOOR_T - floor_w))


def _u(hw, y0, y1, z_bot_axis, x=0.0):
    """A U channel down to a round bottom of radius `hw` about the axis, open to the top."""
    r = cq.Workplane("XZ").center(x, z_bot_axis).circle(hw).extrude(-(y1 - y0)).translate((0, y0, 0))
    return r.union(box_at(2 * hw, y1 - y0, Z_TOP + 50.0 - z_bot_axis,
                          x=x, y=(y0 + y1) / 2.0, z=(z_bot_axis + Z_TOP + 50.0) / 2.0))


def _bay_hw():
    return (D.MOTOR_SQ + 2 * MOTOR_CLR) / 2.0


def _back_y():
    return -(D.MOTOR_BODY_L + 2 * MOTOR_CLR)       # the bay's rear fit, from the wall face


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
    blk = blk.cut(_bay_to_jig(lift_prism(COUPON_MOTOR)))
    lw = _bay_to_jig(low_walls(COUPON_MOTOR)).val().BoundingBox()
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
