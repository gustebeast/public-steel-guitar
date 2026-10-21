"""Motor bank (§5) — PCTG. The under-string staircase.

The 10 motors lie flat under the speaking length, shaft +Y (bodies extend −Y
toward the player). They step along −X by MOTOR_X_STEP so they don't overlap,
each on its string's Y line. Each mounts to a faceplate wall (an X–Z plane at
its faceplate Y) (its pilot boss drops into a slot in it); motors and walls rest on the
chassis's solid bottom prism (the walls are fused into the chassis). Built in
global position.

DROP-IN POCKETS (user, 2026-09-11). The motors do not bolt to anything any more:
each drops STRAIGHT DOWN into a pocket that stops it in every other direction,
and its own CAN TEE stops it coming back out: the board sits on the pocket's
faceplate wall, laps the motor, and the single M4 that holds the board down is
what holds the motor in (user, 2026-09-14). Install: slip the belt over the
pulley, lower the motor in, drop the tee on and drive its one screw. Remove:
back that screw out, lift the board off, lift the motor out.

What makes a pocket possible between motors only D.MOTOR_GAP apart is the STAGGER. Neighbours sit
one string pitch (9.5) apart in Y, so the −X neighbour ENDS 9.5 short of this
motor's back face and the +X neighbour STARTS 9.5 behind its front face. In those
two bands the side post stands alone and can be as thick as it likes, so the bank
has no 42 mm tall, 1.6 mm thin fin in it anywhere (the user's warping worry).
"""

from __future__ import annotations

import cadquery as cq


from . import dimensions as D
from .helpers import box_at, cyl_y
from .components import MOTOR_PULLEY_STANDOFF

PLATE_T      = 8 * D.BEAD        # 6.4 faceplate wall

BOARD_AIR  = D.MIN_WALL          # 0.8: the tee board's underside over the motor's top face --
                                 # the lap that retains it, and the motor's lift before it bites
SEAT_HALF_W = 21.9               # the faceplate wall's -X reach: the tee's -X locating wall needs
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
POST_T     = 12 * D.BEAD         # 9.6 side post (X). Capped by the NEIGHBOUR's boss slot,
                                 # which the post has to keep a wall off -- asserted below
NEIGH_CLR  = D.MIN_WALL          # 0.8 air to the diagonal neighbour's body, at the band end
BACK_T     = 4 * D.BEAD          # 3.2 back wall: nothing pushes the motor -Y, so it is a stop,
BUMP_H     = 14 * D.BEAD         # 11.2 tall: the ONE low-wall height (user, 2026-10-20) -- the
                                 # back wall and both side walls beside the green terminals stop
                                 # here, under the 6-way's measured bottom less TERM_RELIEF_CLR.
                                 # Staggered bays share walls, so one height means no steps.
STAGGER    = D.STRING_PITCH      # 9.5, one string pitch: the band's depth
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
HARNESS_Y1 = -122.4               # +Y edge of the corridor: the trunk lanes' own edge
HARNESS_Z1 = -40.0                # ...and its top: just over the highest trunk lane

# Per-motor faceplate wall CENTRE Y. The motor faceplate (component) is at
# string_y(i) − STANDOFF; the wall's −Y face must sit there so the faceplate
# ABUTS the wall (motor body −Y of it), hence +PLATE_T/2.
def _face_y(i):
    return D.string_y(i) - MOTOR_PULLEY_STANDOFF + PLATE_T / 2

_zc = D.MOTOR_BELT_Z
FLOOR_TOP = _zc - D.MOTOR_SQ / 2            # motors rest here (= wall bottom / chassis rib top)
BED_Z = FLOOR_TOP - D.BOTTOM_T                  # print bed = the chassis bottom prism's
                                                # underside; FLOOR_TOP is that prism's top
Z_HI = _zc + D.MOTOR_SQ / 2 + BOARD_AIR            # the TEE SEAT PLANE: the board rests here and
                                                   # laps the motor by BOARD_AIR of air
SEAT_TOP = Z_HI + D.TEE_BOARD_T + D.TEE_WALL_OVER  # ...and the bay runs this far over it, so the
                                                   # seat's walls are just the bay, cut for the board


def tee_board_box(i):
    """The tee board's own box on motor i: (x0, x1, y0, y1, z_underside).

    ITS +X EDGE SITS ON THE MOTOR'S FIT LINE. The board is 40 across a 42.3 motor, so centred it
    would leave the seat's +X wall inside the motor's lift path, where the cut that frees the
    motor slices it to a sliver (the user found that on both sides). Pushed out to the fit line,
    everything beyond it is outside the motor and survives whole. What hangs PAST it is the
    bare EAR the retaining M4 goes through, which lands on the +X post."""
    _, bx1, _, by1, _, _ = body_box(i)
    x1 = bx1 + MOTOR_CLR + D.TEE_EAR_X              # the layout region's +X edge is the fit line
    y1 = by1 + PLATE_T                              # +Y edge flush with the faceplate wall's face
    return x1 - D.TEE_OUTLINE_X, x1, y1 - D.TEE_BOARD_Y, y1, Z_HI


assert D.TEE_EAR_Y <= STAGGER - NEIGH_CLR + 1e-9, (
    "the tee board's ear (%.1f deep) reaches past the band the +X neighbour's board vacates "
    "(%.1f): the ten boards would clash" % (D.TEE_EAR_Y, STAGGER - NEIGH_CLR))


def tee_ear_box(i):
    """The bare TAB off the +X end of motor i's board: (x0, x1, y0, y1). Only the +Y
    D.TEE_EAR_Y of the board's depth, because the +X neighbour's board is one stagger further
    -Y and a full-depth ear would sit on top of it."""
    _, sx1, _, sy1, _ = tee_board_box(i)
    return sx1 - D.TEE_EAR_X, sx1, sy1 - D.TEE_EAR_Y, sy1


# THE FAR-END LIP (coupon round 2, user 2026-10-20: the board "is lifting away from the motor
# at the far end away from the screw ... add a 45 lip to the far side so when installing the
# tee you slide it under that lip"). The board's -X edge stands TEE_FIT off the seat's -X
# locating wall (the faceplate wall's strip beside it); a 45 deg lip off that wall laps the
# board's top edge. Its underside meets the board's top corner TEE_LIP_AIR over it, and it runs
# up to the seat top, TEE_LIP_REACH in over the board. The tee goes in -X edge first, tilted,
# under the lip; then the ear drops onto the post and the M4 closes it.
TEE_LIP_AIR = 0.1


def tee_lip(i):
    """The lip's wedge over tee i's -X edge: kept OUT of tee_pocket so the seat keeps it."""
    sx0, sx1, sy0, sy1, sz = tee_board_box(i)
    top = sz + D.TEE_BOARD_T
    xw = sx0 - D.TEE_FIT - 1.0                       # into the locating wall
    z_hi = SEAT_TOP + 1.0
    z_lo = top + TEE_LIP_AIR + (xw - sx0)            # the 45 deg underside, through the corner
    x_hi = sx0 + (z_hi - top - TEE_LIP_AIR)
    prof = (cq.Workplane("XZ").polyline([(xw, z_lo), (x_hi, z_hi), (xw, z_hi)]).close()
            .extrude(-(sy1 - sy0 + 2 * D.TEE_FIT)))
    return prof.translate((0, sy0 - D.TEE_FIT, 0))


TEE_LIP_REACH = SEAT_TOP - (Z_HI + D.TEE_BOARD_T) - TEE_LIP_AIR   # 1.1 over the board at the top


def tee_pocket(i):
    """The tee board's space: its profile plus a fit, open upward so it drops in, together with
    the relief the THT tails need under its +Y band. ONE cutter, because the board is 40 across
    a 42.3 motor and so reaches 1.5 into the NEIGHBOUR's bay -- the chassis subtracts every bay's
    from the fused result, exactly as it does every motor's lift path. Less tee_lip(i)."""
    return _tee_pocket(i).cut(tee_lip(i))


def _tee_pocket(i):
    sx0, sx1, sy0, sy1, sz = tee_board_box(i)
    _h = (SEAT_TOP - sz) + 2.0
    # (its +X face is the motor's fit line: the board's edge stands D.TEE_EDGE_BACK inside it,
    # so the fit takes nothing from the wall between this motor and the next)
    pocket = box_at(D.TEE_BOARD_X - D.TEE_EDGE_BACK + 2 * D.TEE_FIT,
                    D.TEE_BOARD_Y + 2 * D.TEE_FIT, _h,
                    x=(sx0 + sx1) / 2 - D.TEE_EAR_X / 2 - D.TEE_EDGE_BACK / 2,
                    y=(sy0 + sy1) / 2, z=sz + _h / 2)
    # ...plus the ear's tab (an L, not a box). The CUT runs deeper than the tab: down to where
    # the -X neighbour's own board sits, one STAGGER away. The ear laps that neighbour's bay, so
    # two independent pockets bite the same post from opposite sides, and stopping each at its own
    # board's edge left the strip between them standing as a 0.2 rib (found on nine strings).
    # Reaching the neighbour's seat line means the two cuts meet, with their fits overlapping.
    ex0, ex1, _, ey1 = tee_ear_box(i)
    ey0 = ey1 - max(D.TEE_EAR_Y, STAGGER)
    pocket = pocket.union(box_at(D.TEE_EAR_X + 2 * D.TEE_FIT, (ey1 - ey0) + 2 * D.TEE_FIT, _h,
                                 x=(ex0 + ex1) / 2, y=(ey0 + ey1) / 2, z=sz + _h / 2))
    # the tail relief runs under the LAYOUT REGION only -- the ear has no tails, and leaving it
    # solid is what the hole's boss is bored from
    return pocket.union(box_at(D.TEE_BOARD_X - 2.0, 5.0, D.TEE_TAIL_DROP + 2.0,
                               x=(sx0 + sx1) / 2 - D.TEE_EAR_X / 2,
                               y=(sy0 + sy1) / 2 + D.TEE_TAIL_CY,
                               z=sz - (D.TEE_TAIL_DROP + 2.0) / 2 + 0.01))


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
    """-Y face of motor i's back wall: string 1's is the two-bead stop off the motor board."""
    by0 = body_box(i)[2]
    return by0 - (D.MIN_WALL_2P + MOTOR_CLR if i == 0 else BACK_T)


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
    yb = back_wall_y0(i) - 1.0
    x0, x1 = bx0 - side_room(i, -1) - 1.0, bx1 + side_room(i, 1) + 1.0
    z0, z1 = bz0 + term_wall_h(), SEAT_TOP + 1.0
    return box_at(x1 - x0, ya - yb, z1 - z0, x=(x0 + x1) / 2, y=(ya + yb) / 2, z=(z0 + z1) / 2)


def back_y(i):
    """Y of motor i's back face -- where its CAN pigtail leaves it (wiring reads this)."""
    return body_box(i)[2]


def _wall(i) -> cq.Workplane:
    """The faceplate wall: the pocket's +Y face and the one that carries the load. Unchanged
    in size (the motor's faceplate lies against it), but its Ø22 pilot bore now opens UPWARD
    in a slot the boss drops through, and the four NEMA17 bolt holes are gone with the bolts."""
    mx, my, mz = D.motor_pos(i)
    fy = _face_y(i)
    # It runs +X to meet the +X post's outer face: 42.2 alone stops 0.45 short of a post that
    # has to stand off the motor by MOTOR_CLR, and a post the wall does not touch is a post
    # nothing braces. Its own Y band is clear of every neighbour, so the reach is free.
    _x1 = mx + D.MOTOR_SQ / 2 + MOTOR_CLR + POST_T
    _x0 = mx - SEAT_HALF_W
    wall = box_at(_x1 - _x0, PLATE_T, Z_HI - BED_Z,
                  x=(_x0 + _x1) / 2, y=fy, z=(Z_HI + BED_Z) / 2)
    wall = wall.edges("|Y and <Z").chamfer(14.0)   # big 45° buttress → bed (gusset)
    wall = wall.edges("|Y and >Z").chamfer(3.0)     # trim the top corners
    return wall                      # its SLOT is cut in pocket(), after the bay prism unions
                                     # into this band -- cut here, the prism refills it


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


def pocket(i) -> cq.Workplane:
    """ONE motor's housing, PRISM-FIRST (user, 2026-09-14): fill the bay with a solid and cut
    the motor's own topology out of it, rather than adding a wall here and a post there. The
    accreted version left a sliver wherever a cut met a small prism edge-on; here every face is
    either the motor's surface plus its fit, or a cut with a reason.

    THE PRISM  the bay this motor owns: the whole gap to each neighbour less its fit
               (side_room), so ONE 1.6 wall separates two motors, from the bottom prism's top
               up past the tee seat plane.
    THE CUTS   the motor + MOTOR_CLR swept +Z, which is both the pocket and the way IN; the
               tee board's seat; and the boss's drop-in slot. (The low walls -- back and
               sides over BUMP_H -- are low_walls(), and the -Y rail's harness corridor,
               both cut from the fused chassis by chassis.py.)

    Exposed PER MOTOR so the chassis can fuse each housing WHOLE into the print segment that
    owns its motor -- a housing straddling a segment boundary is never sliced; it just overhangs
    the cut plane and the neighbour is relieved."""
    bx0, bx1, by0, by1, bz0, bz1 = body_box(i)
    body = _wall(i)                                     # the faceplate wall (runs on to the bed)

    x0, x1 = bx0 - side_room(i, -1), bx1 + side_room(i, 1)
    # STRING 1'S BACK STOP IS THE MOTOR BOARD'S +Y WALL (user, 2026-10-02): the board stands
    # directly behind this motor, a two-bead wall off its back face, so the stop is that wall
    # and no thicker -- 3.2 here would stand in the board.
    y0, y1 = back_wall_y0(i), by1 + PLATE_T
    # FROM THE BOTTOM PRISM'S TOP FACE UP (user, 2026-09-16). It reached the BED for a while,
    # because the cross-ribs it used to stand on were a comb and a bay wall bridged every gap
    # between them. The bottom is one solid XBAR-tall prism now, so there is nothing to bridge:
    # the bay starts where that prism ends and the motor rests on it.
    body = body.union(box_at(x1 - x0, y1 - y0, SEAT_TOP - FLOOR_TOP,
                             x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(FLOOR_TOP + SEAT_TOP) / 2))

    # (THE BACK WALL stands only BUMP_H: low_walls() takes it down, with the side walls, from
    #  the fused chassis. It once had a 6 mm lane on the centreline for the grey pigtail; the
    #  drops leave from the side terminals now -- wiring, wire_drop_* -- so it is whole.)

    # (the -Y rail's HARNESS CORRIDOR is cut from the fused chassis, not from here: whether a
    #  bay may reach the rail depends on where the trunk runs, and across the +X-most motor the
    #  trunk dips OUTBOARD into the rail's notch, so that bay CAN. chassis.py owns both.)

    # THE +X POST: the tee seat's hold boss needs more X than a 1.6 wall has, and the stagger
    # leaves room for it at the front (the +X neighbour starts one string pitch further -Y)
    _pl = (STAGGER - NEIGH_CLR) + PLATE_T
    body = body.union(box_at(POST_T, _pl, SEAT_TOP - FLOOR_TOP,   # from the bottom prism's top
                             x=bx1 + MOTOR_CLR + POST_T / 2,      # face, like the bay itself
                             y=by1 + PLATE_T - _pl / 2,
                             z=(FLOOR_TOP + SEAT_TOP) / 2))

    # THE SEAT is this same prism, cut for the board (user, 2026-09-14): the bay runs up past it
    # and the board's own profile comes out, so what stands around the pocket IS the cradle. No
    # separate part to place, and nothing left for the motor's lift cut to slice into a sliver.
    # Most of the board hangs over the motor, where the lift cut has already opened the bay; what
    # this takes is the strip over the faceplate wall, plus a relief under the THT tail line.
    body = body.cut(tee_pocket(i))

    # ...and ONLY NOW the cuts, every one of them after every union: the boss's drop-in slot in
    # the faceplate wall, and the motor's own volume swept +Z (its fit, and its way in). Cut
    # before the prism unions into those bands and the prism simply fills them back in.
    _slot_w = D.NEMA17_PILOT_D + 2 * BOSS_CLR
    _fy = _face_y(i)
    body = body.cut(box_at(_slot_w, PLATE_T + 2.0, Z_HI - (mz := D.motor_pos(i)[2]) + 1.0,
                           x=(bx0 + bx1) / 2, y=_fy, z=(mz + Z_HI + 1.0) / 2))
    body = body.cut(cyl_y(_slot_w, PLATE_T + 2.0, _fy - PLATE_T / 2 - 1.0,
                          x=(bx0 + bx1) / 2, z=mz))
    return body.cut(lift_prism(i))


plates = [pocket(i) for i in range(D.N_STRINGS)]

# the post stops short of the NEIGHBOUR's boss slot (both sides are the same by symmetry)
_slot_edge = D.MOTOR_X_STEP - (D.NEMA17_PILOT_D + 2 * BOSS_CLR) / 2
assert (D.MOTOR_SQ / 2 + MOTOR_CLR + POST_T) <= _slot_edge - D.MIN_WALL + 1e-9, (
    "the side post reaches within %.2f of the neighbour's boss slot"
    % (_slot_edge - (D.MOTOR_SQ / 2 + MOTOR_CLR + POST_T)))


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
COUPON_UP = (0.0, 0.0, 1.0)
COUPON_WALL = D.MIN_WALL_2P      # 1.6, the shared side walls' own thickness
COUPON_FLOOR_T = 2 * D.BEAD      # 1.6
COUPON_RIM = 10 * D.BEAD         # 8.0 of floor inside the fit, all round
COUPON_GAP = 6.0                 # bay to dummy board on the plate
# THE DUMMY BOARD has to BEND like the real one, because the clamp is the board lapping the
# motor's top. FR-4 flexes at ~20 GPa, printed PETG-GF at ~3.3 (Elegoo TDS, material-strategy);
# bending stiffness goes as E t^3, so the 1.6 board becomes 1.6 * (20/3.3)^(1/3) = 2.92 ->
# 3.0, whole 0.2 layers. Thickened UPWARD over the layout region only: its underside is the
# real board's (it sits on the real seat) and the ear stays 1.6 so the M4x10 clamps exactly
# what it clamps on the instrument.
E_FR4, E_PETG_GF = 20.0, 3.3
TEE_DUMMY_T = 3.0
TEE_DUMMY_LIP_W = 4 * D.BEAD     # 3.2 of 1.6-thick edge under the lip (it reaches 1.1 in)
EMU_D = 2 * D.BEAD               # 1.6 of the -X neighbour's ear kept, from its -Y edge in
assert abs(TEE_DUMMY_T - D.TEE_BOARD_T * (E_FR4 / E_PETG_GF) ** (1 / 3)) < 0.1


def _rect_wire(x0, x1, y0, y1, z):
    pts = [cq.Vector(x0, y0, z), cq.Vector(x1, y0, z), cq.Vector(x1, y1, z),
           cq.Vector(x0, y1, z), cq.Vector(x0, y0, z)]
    return cq.Wire.makePolygon(pts)


def _tee_board_world(i, t_layout):
    """Tee i's bare substrate where tee_components puts the real board."""
    from . import wiring as W, electronics as EL
    x, y, d = W.tee_stations()[i]
    _bw, _bl, cx, cy, _o, _he, _ha = W.tee_hold(i, x, y, d)
    return EL.tee_substrate(cx, cy - EL.TEE_YSHIFT, t_layout).translate(
        (0, 0, W.tee_z(i) - EL.FLOOR_Z))


def _coupon_world():
    """(bay, dummy) in WORLD position on motor COUPON_MOTOR, the dummy seated."""
    from . import wiring as W, electronics as EL
    i = COUPON_MOTOR
    near = [j for j in (i - 1, i, i + 1) if 0 <= j < D.N_STRINGS]
    bay = plates[near[0]]
    for j in near[1:]:
        bay = bay.union(plates[j])
    for j in near:
        bay = bay.cut(lift_prism(j)).cut(low_walls(j)).cut(tee_pocket(j))
    holds = W.tee_hold_negatives()
    for j in near:
        for c in holds[j][1]:
            bay = bay.cut(c)

    bx0, bx1, by0, by1, bz0, bz1 = body_box(i)
    fit = lift_prism(i).val().BoundingBox()
    fx0, fx1, fy0, fy1 = fit.xmin, fit.xmax, fit.ymin, fit.ymax
    w = COUPON_WALL
    z_top = SEAT_TOP + 1.0
    keep = box_at(fx1 - fx0 + 2 * w, fy1 - fy0 + 2 * w, z_top - FLOOR_TOP,
                  x=(fx0 + fx1) / 2, y=(fy0 + fy1) / 2, z=(FLOOR_TOP + z_top) / 2)
    # the seat block: the faceplate wall's top and the post, down past the M4 anchor...
    from cadkit.fasteners import M4
    sx1 = bx1 + MOTOR_CLR + POST_T                      # the post's +X face
    sy0 = by1 + PLATE_T - ((STAGGER - NEIGH_CLR) + PLATE_T) - 1.0   # past the post's -Y end
    sy1 = by1 + PLATE_T                                 # the faceplate wall's +Y face
    zb = Z_HI - M4.anchor_min_wall - COUPON_WALL
    keep = keep.union(box_at(sx1 - (fx0 - w), sy1 - sy0, z_top - zb,
                             x=(sx1 + fx0 - w) / 2, y=(sy0 + sy1) / 2, z=(zb + z_top) / 2))
    # ...and its corbel down to the ring. Its +X and +Y faces step back by different amounts,
    # so the CORNER edge between them is the steepest line: its height is that diagonal's
    # run, which would hold the corner at exactly 45 deg; 1.2 of it keeps it under, margin.
    # It starts from the ring's INNER face, so the corner edge leaves through the ring wall's
    # solid rather than from its bare outside corner (the cavity is cut by the bay anyway)
    import math
    step = 1.2 * math.hypot(sx1 - fx1, sy1 - fy1)
    corbel = cq.Solid.makeLoft([_rect_wire(fx0 - w, fx1, sy0, fy1, zb - step),
                                _rect_wire(fx0 - w, sx1, sy0, sy1, zb)], True)
    keep = keep.union(cq.Workplane(obj=corbel))
    # THE -X NEIGHBOUR'S EAR, in front of this board's FAR end (user, 2026-10-20: "the
    # neighboring pcb serves as retention here ... the one on the far end"). String i-1's tee
    # ear stands NEIGH_CLR-ish in front of this board's +Y edge over its -X end, on its own
    # post just past this bay's faceplate wall -- on the instrument it is what stops that end
    # going +Y. The coupon keeps an EMU_D strip of that post, carried off the faceplate wall
    # on a 45 deg shelf (user: "grow the wall with a 45 near the top"), and the ear's real
    # outline, 1.6, on top -- fused into the bay print.
    if i > 0:
        from . import wiring as W
        ex0, ex1, ey0, ey1 = tee_ear_box(i - 1)
        x0_, x1_ = max(ex0, fx0 - w), ex1
        bore = W.tee_hold_negatives()[i - 1][1][0].val().BoundingBox().ymin   # the anchor (not the head notch)
        y1_ = min(ey0 + EMU_D, bore)                        # ...short of its own M4's bore
        d_ = y1_ - sy1
        shelf = (cq.Workplane("YZ").polyline([(sy1, Z_HI - 1.2 * d_), (y1_, Z_HI),
                                              (y1_, z_top), (sy1, z_top)]).close()
                 .extrude(x1_ - x0_).translate((x0_, 0, 0)))
        keep = keep.union(shelf)
        bay = bay.union(_tee_board_world(i - 1, D.TEE_BOARD_T).intersect(shelf))
    bay = bay.intersect(keep)
    # the floor: a rim the motor stands on, open in the middle
    zf = FLOOR_TOP - COUPON_FLOOR_T
    floor = box_at(fx1 - fx0 + 2 * w, fy1 - fy0 + 2 * w, COUPON_FLOOR_T,
                   x=(fx0 + fx1) / 2, y=(fy0 + fy1) / 2, z=zf + COUPON_FLOOR_T / 2)
    floor = floor.cut(box_at(fx1 - fx0 - 2 * COUPON_RIM, fy1 - fy0 - 2 * COUPON_RIM, 10.0,
                             x=(fx0 + fx1) / 2, y=(fy0 + fy1) / 2, z=zf))
    bay = bay.union(floor)

    # the dummy board, placed exactly as tee_components places the real one
    dummy = _tee_board_world(i, TEE_DUMMY_T)
    sx0_, sx1_, sy0_, sy1_, sz_ = tee_board_box(i)
    # ...back to the real 1.6 along its -X edge, where it goes under the lip
    dummy = dummy.cut(box_at(TEE_DUMMY_LIP_W + 1.0, sy1_ - sy0_ + 2.0, 10.0,
                             x=sx0_ + (TEE_DUMMY_LIP_W - 1.0) / 2, y=(sy0_ + sy1_) / 2,
                             z=sz_ + D.TEE_BOARD_T + 5.0))
    db = dummy.val().BoundingBox()
    assert abs(db.zmin - sz_) < 1e-6 and abs(db.xmax - sx1_) < 1e-6 and abs(db.ymax - sy1_) < 1e-6, \
        "the dummy board is not where the seat expects the tee"
    return bay, dummy


def bay_coupon() -> cq.Workplane:
    """The print plate: the bay on its floor, the dummy board flat beside it (+X)."""
    i = COUPON_MOTOR
    bay, dummy = _coupon_world()
    mx = D.motor_pos(i)[0]
    by0, by1 = body_box(i)[2:4]
    zf = FLOOR_TOP - COUPON_FLOOR_T
    bay = bay.translate((-mx, -(by0 + by1) / 2, -zf))
    bb, db = bay.val().BoundingBox(), dummy.val().BoundingBox()
    dummy = dummy.translate((bb.xmax + COUPON_GAP - db.xmin, -db.center.y, -db.zmin))
    # TWO PRINTS, TWO OBJECTS in the one STEP, so the slicer can drop either (user, 2026-10-20;
    # a re-imported STEP shows both -- a reload of the old one did not)
    out = cq.Workplane().add(bay.vals() + dummy.vals())
    assert len(out.solids().vals()) == 2, "the plate is not the bay and the dummy"
    assert abs(min(v.BoundingBox().zmin for v in out.vals())) < 1e-6, "not on the bed"
    return out
