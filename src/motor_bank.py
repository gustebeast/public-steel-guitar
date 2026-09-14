"""Motor bank (§5) — PCTG. The under-string staircase.

The 10 motors lie flat under the speaking length, shaft +Y (bodies extend −Y
toward the player). They step along −X by MOTOR_X_STEP so they don't overlap,
each on its string's Y line. Each mounts to a faceplate wall (an X–Z plane at
its faceplate Y) carrying a NEMA17 pattern; motors and walls rest on the
chassis's per-motor cross-ribs (no floor plate — the walls are fused into the
chassis). Built in global position.

DROP-IN POCKETS (user, 2026-09-11). The motors do not bolt to anything any more:
each drops STRAIGHT DOWN into a pocket that stops it in every other direction,
and its own CAN TEE stops it coming back out: the board sits on the pocket's
faceplate wall, laps the motor, and the single M4 that holds the board down is
what holds the motor in (user, 2026-09-14). Install: slip the belt over the
pulley, lower the motor in, drop the tee on and drive its one screw. Remove:
back that screw out, lift the board off, lift the motor out.

What makes a pocket possible at a 1.6 mm motor gap is the STAGGER. Neighbours sit
one string pitch (9.5) apart in Y, so the −X neighbour ENDS 9.5 short of this
motor's back face and the +X neighbour STARTS 9.5 behind its front face. In those
two bands the side post stands alone and can be as thick as it likes, so the bank
has no 42 mm tall, 1.6 mm thin fin in it anywhere (the user's warping worry).
"""

from __future__ import annotations

import cadquery as cq

import math

from . import dimensions as D
from .helpers import box_at
from .components import MOTOR_PULLEY_STANDOFF
from cadkit.fasteners import M4 as _M4

PLATE_T      = 8 * D.NOZZLE_D    # 6.4 (was 6.0 = 7.5 beads)
_BOLT_EDGE   = 7 * D.BEAD                   # 5.6 material around the NEMA17 bolt square
                                            # (was 6.0 = 7.5 beads; snapped DOWN — the
                                            # gaps to the chassis split planes and the
                                            # neighbouring motor GROW)

WALL_W = D.NEMA17_BOLT_SQ + 2 * _BOLT_EDGE  # 42.2: 0.9 to the chassis split planes,
                                            # 1.75 to the neighbouring motor body

BOARD_AIR  = D.MIN_WALL          # 0.8: the tee board's underside over the motor's top face --
                                 # the lap that retains it, and the motor's lift before it bites
SEAT_HALF_W = 21.9               # the faceplate wall's -X reach: the tee's -X locating wall needs
                                 # board/2 + wall + fit outside the board, and the neighbour's body
                                 # is at 22.75 (wiring asserts the board still fits this)
MOTOR_CLR  = D.MOTOR_CLR         # slip fit round a PURCHASED body (the gap is sized from it)
BOSS_CLR   = 0.4                 # round the O22 pilot boss in its drop-in slot
POST_T     = 12 * D.BEAD         # 9.6 side post (X). Capped by the NEIGHBOUR's boss slot,
                                 # which the post has to keep a wall off -- asserted below
NEIGH_CLR  = D.MIN_WALL          # 0.8 air to the diagonal neighbour's body, at the band end
WIRE_LANE_W = 6.0                # a back stop leaves this much clear on the motor's centreline
                                 # for its CAN pigtail to climb
FIN_H      = 16 * D.BEAD         # 12.8: the -X fin's height (short, and wall-braced)
BACK_T     = 4 * D.BEAD          # 3.2 back wall: nothing pushes the motor -Y, so it is a stop,
BUMP_H     = 16 * D.BEAD         # 12.8 tall -- above it the DRIVE's connector and cable want the
                                 # bay open, and the motor goes in with them attached
STAGGER    = abs(D.string_y(0) - D.string_y(1))    # 9.5, one string pitch: the band's depth
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
BED_Z = FLOOR_TOP - D.XBAR                  # print bed = chassis rib/rail bottom; the
                                            # FLOOR_TOP->bed gap = rib height = XBAR, so the
                                            # cross-ribs are a square XBAR x XBAR section
Z_HI = _zc + D.MOTOR_SQ / 2 + BOARD_AIR            # wall top = the TEE SEAT PLANE: the board rests
                                                   # here and laps the motor by BOARD_AIR of air


def tee_seat(i):
    """Where motor i's CAN tee sits: (x centre, the +Y face its board's +Y edge lines up with,
    seat plane z). The board rests on the faceplate wall's top and laps the motor -- so the ONE
    screw that holds the board down also stops the motor lifting out (user, 2026-09-14). wiring
    builds the cradle there and cuts it with lift_prism, since nothing FIXED may overhang a
    motor or it can never come out."""
    mx, my, _ = D.motor_pos(i)
    return mx, _face_y(i) + PLATE_T / 2, Z_HI


def gap_keepout(i):
    """Everything -X of this motor's pocket face: the MOTOR GAP, which belongs to the pocket's
    own wall. Anything built over a motor gets cut by this as well as by lift_prism, or it
    leaves a sliver in the gap."""
    bx0, _, by0, by1, bz0, bz1 = body_box(i)
    return box_at(200.0, (by1 - by0) + 400.0, (bz1 + 300.0) - (bz0 - 100.0),
                  x=(bx0 - MOTOR_CLR) - 100.0, y=(by0 + by1) / 2,
                  z=((bz0 - 100.0) + (bz1 + 300.0)) / 2)


def lift_prism(i):
    """Motor i's way out: its footprint swept +Z. Cut it from anything built over a motor."""
    bx0, bx1, by0, by1, bz0, bz1 = body_box(i)
    # It spans the pocket's FULL height, not just upward from the motor top: anything seated
    # over a motor also has a base hanging below that line, and a base that reaches into the
    # motor's own fit gap comes back as a sliver (0.4 of one, user-measured).
    z0, z1 = bz0 - 100.0, bz1 + 300.0
    return box_at(bx1 - bx0 + 2 * MOTOR_CLR, by1 - by0 + 2 * MOTOR_CLR, z1 - z0,
                  x=(bx0 + bx1) / 2, y=(by0 + by1) / 2, z=(z0 + z1) / 2)


def body_box(i):
    """The motor body's own envelope (x0, x1, y0, y1, z0, z1) -- what the pocket wraps.
    The boss and shaft stick out +Y of y1 and are NOT in here; they live in the wall's slot."""
    mx, my, mz = D.motor_pos(i)
    y1 = my - MOTOR_PULLEY_STANDOFF                      # faceplate = the wall's -Y face
    return (mx - D.MOTOR_SQ / 2, mx + D.MOTOR_SQ / 2,
            y1 - D.MOTOR_BODY_L, y1,
            mz - D.MOTOR_SQ / 2, mz + D.MOTOR_SQ / 2)


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
    other = D.MOTOR_ELEC_CLR if (sgn < 0 and i == 0) else D.MOTOR_GAP
    if sgn > 0 and i == D.N_STRINGS - 1:
        return MOTOR_CLR + D.MIN_WALL_2P          # open air past the last motor
    return other - MOTOR_CLR


def pocket(i) -> cq.Workplane:
    """ONE motor's housing, PRISM-FIRST (user, 2026-09-14): fill the bay with a solid and cut
    the motor's own topology out of it, rather than adding a wall here and a post there. The
    accreted version left a sliver wherever a cut met a small prism edge-on; here every face is
    either the motor's surface plus its fit, or a cut with a reason.

    THE PRISM  the bay this motor owns: half the gap to each neighbour (the halves meet and
               fuse, so ONE 1.6 wall separates two motors), rib tops up to the tee seat plane.
    THE CUTS   the motor + MOTOR_CLR swept +Z, which is both the pocket and the way IN; the
               DRIVE's room at the back (its connector and cable leave that face and the motor
               goes in with them attached, so the back wall stops at BUMP_H and keeps a lane on
               the centreline); the -Y rail's harness corridor; and the boss's drop-in slot,
               which _wall cuts.

    Exposed PER MOTOR so the chassis can fuse each housing WHOLE into the print segment that
    owns its motor -- a housing straddling a segment boundary is never sliced; it just overhangs
    the cut plane and the neighbour is relieved."""
    bx0, bx1, by0, by1, bz0, bz1 = body_box(i)
    body = _wall(i)                                     # the faceplate wall (runs on to the bed)

    x0, x1 = bx0 - side_room(i, -1), bx1 + side_room(i, 1)
    y0, y1 = by0 - BACK_T, by1 + PLATE_T
    body = body.union(box_at(x1 - x0, y1 - y0, Z_HI - bz0,
                             x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(bz0 + Z_HI) / 2))


    # THE DRIVE: the back wall stands BUMP_H and no further, so the driver's connector and its
    # cable have the whole upper back open
    _yb0, _yb1 = y0 - 1.0, by0 - MOTOR_CLR
    body = body.cut(box_at((x1 - x0) + 2.0, _yb1 - _yb0, (Z_HI + 1.0) - (bz0 + BUMP_H),
                           x=(x0 + x1) / 2, y=(_yb0 + _yb1) / 2,
                           z=((bz0 + BUMP_H) + (Z_HI + 1.0)) / 2))
    # ...and a lane through what is left of it, for the pigtail to climb
    body = body.cut(box_at(WIRE_LANE_W, _yb1 - _yb0, BUMP_H + 2.0,
                           x=(bx0 + bx1) / 2, y=(_yb0 + _yb1) / 2, z=bz0 + BUMP_H / 2))

    # (the -Y rail's HARNESS CORRIDOR is cut from the fused chassis, not from here: whether a
    #  bay may reach the rail depends on where the trunk runs, and across the +X-most motor the
    #  trunk dips OUTBOARD into the rail's notch, so that bay CAN. chassis.py owns both.)

    # THE +X POST: the tee seat's hold boss needs more X than a 1.6 wall has, and the stagger
    # leaves room for it at the front (the +X neighbour starts one string pitch further -Y)
    _pl = (STAGGER - NEIGH_CLR) + PLATE_T
    body = body.union(box_at(POST_T, _pl, Z_HI - bz0,
                             x=bx1 + MOTOR_CLR + POST_T / 2,
                             y=by1 + PLATE_T - _pl / 2,
                             z=(bz0 + Z_HI) / 2))

    # ...and ONLY NOW the cuts, every one of them after every union: the boss's drop-in slot in
    # the faceplate wall, and the motor's own volume swept +Z (its fit, and its way in). Cut
    # before the prism unions into those bands and the prism simply fills them back in.
    _slot_w = D.NEMA17_PILOT_D + 2 * BOSS_CLR
    _fy = _face_y(i)
    body = body.cut(box_at(_slot_w, PLATE_T + 2.0, Z_HI - bz1 + (bz1 - (mz := D.motor_pos(i)[2])) + 1.0,
                           x=(bx0 + bx1) / 2, y=_fy, z=(mz + Z_HI + 1.0) / 2))
    body = body.cut(cq.Workplane(obj=cq.Solid.makeCylinder(
        _slot_w / 2, PLATE_T + 2.0, cq.Vector((bx0 + bx1) / 2, _fy - PLATE_T / 2 - 1.0, mz),
        cq.Vector(0, 1, 0))))
    body = body.cut(lift_prism(i))
    # The corridor cut can strand a scrap of side wall above it on the -Y-most bays (their backs
    # reach the rail, so there is nothing left to join it to). Keep the housing proper: the
    # chassis would drop the scraps anyway, and a part that IS its own answer is easier to read.
    _solids = body.val().Solids()
    if len(_solids) > 1:
        body = cq.Workplane(obj=max(_solids, key=lambda s: s.Volume()))
    return body


plates = [pocket(i) for i in range(D.N_STRINGS)]

# the post stops short of the NEIGHBOUR's boss slot (both sides are the same by symmetry).
# The SCREWED motor's fatter post is exempt: it is the last in the bank, with no neighbour.
_slot_edge = D.MOTOR_X_STEP - (D.NEMA17_PILOT_D + 2 * BOSS_CLR) / 2
assert (D.MOTOR_SQ / 2 + MOTOR_CLR + POST_T) <= _slot_edge - D.MIN_WALL + 1e-9, (
    "the side post reaches within %.2f of the neighbour's boss slot"
    % (_slot_edge - (D.MOTOR_SQ / 2 + MOTOR_CLR + POST_T)))


def _build() -> cq.Workplane:
    body = plates[0]
    for w in plates[1:]:
        body = body.union(w)
    return body


motor_bank = _build()
