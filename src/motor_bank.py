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
MOTOR_CLR  = 0.4                 # slip fit round a PURCHASED body (42.3 nominal, +-0.2)
BOSS_CLR   = 0.4                 # round the O22 pilot boss in its drop-in slot
POST_T     = 12 * D.BEAD         # 9.6 side post (X). Capped by the NEIGHBOUR's boss slot,
                                 # which the post has to keep a wall off -- asserted below
NEIGH_CLR  = D.MIN_WALL          # 0.8 air to the diagonal neighbour's body, at the band end
WIRE_LANE_W = 6.0                # a back stop leaves this much clear on the motor's centreline
                                 # for its CAN pigtail to climb
FIN_H      = 16 * D.BEAD         # 12.8: the one-bead -X fin's height (short, and wall-braced)
BUMP_T     = 4 * D.BEAD          # 3.2 back bumper: nothing pushes the motor -Y, so it is a
BUMP_H     = 16 * D.BEAD         # 12.8 tall stop, not a wall -- the CAN pigtail leaves over it
STAGGER    = abs(D.string_y(0) - D.string_y(1))    # 9.5, one string pitch: the band's depth
# THE POCKET'S -Y LIMIT. The bank is staggered, so the -Y-most motors' backs run right down to
# the -Y rail -- and that strip is the HARNESS CORRIDOR: the tee boards on their cradles and the
# six stacked trunk lanes. Nothing of a pocket may enter it (the first cut of this design put
# 15 clashes there, including motor 9's tee screw buried in chassis). So the back features stop
# here, and where that leaves no room they are simply dropped: what stops those motors going -Y
# is the rail itself, 2.0 behind string 10's back (user: merge the back wall into the chassis
# wall on the high strings). wiring.py asserts this against where the tees and lanes really are.
HARNESS_Y1 = -108.75              # +Y edge of the corridor: the tee boards' own +Y edge
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


def lift_prism(i):
    """Motor i's way out: its footprint swept +Z. Cut it from anything built over a motor."""
    bx0, bx1, by0, by1, _, bz1 = body_box(i)
    return box_at(bx1 - bx0 + 2 * MOTOR_CLR, by1 - by0 + 2 * MOTOR_CLR, 400.0,
                  x=(bx0 + bx1) / 2, y=(by0 + by1) / 2, z=bz1 + 200.0)


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
    slot_w = D.NEMA17_PILOT_D + 2 * BOSS_CLR
    wall = wall.cut(box_at(slot_w, PLATE_T + 2.0, Z_HI - mz + 1.0,
                           x=mx, y=fy, z=(mz + Z_HI + 1.0) / 2))
    wall = wall.cut(cq.Workplane(obj=cq.Solid.makeCylinder(
        slot_w / 2, PLATE_T + 2.0, cq.Vector(mx, fy - PLATE_T / 2 - 1.0, mz),
        cq.Vector(0, 1, 0))))
    return wall


def pocket(i) -> cq.Workplane:
    """ONE motor's housing: faceplate wall + the two stagger-band side posts + the back
    bumper. The motor drops in from +Z and its screw (cut by the chassis) stops it lifting.

    Exposed PER MOTOR so the chassis can fuse each housing WHOLE into the print segment that
    owns its motor -- a housing straddling a segment boundary is never sliced; it just
    overhangs the cut plane and the neighbour is relieved. That frees the segment splits to
    fall between ribs instead of dodging the 43-wide walls."""
    bx0, bx1, by0, by1, bz0, bz1 = body_box(i)
    body = _wall(i)
    # +X post: in the band the +X neighbour does not reach (it starts STAGGER further -Y).
    # Tall enough to host the screw, and fused to the wall, which braces it.
    px0 = bx1 + MOTOR_CLR
    _pl = (STAGGER - NEIGH_CLR) + PLATE_T          # ...and on into the wall, which braces it
    _pr = Z_HI - bz1                               # post top = the tee seat plane it helps carry
    body = body.union(box_at(POST_T, _pl, (bz1 + _pr) - bz0,
                             x=px0 + POST_T / 2,
                             y=by1 + PLATE_T - _pl / 2,
                             z=(bz0 + bz1 + _pr) / 2))
    # -X post: the mirror band, at the BACK (the -X neighbour ends STAGGER short of it),
    # running -Y into the bumper so the housing prints as one piece -- but never past
    # HARNESS_Y1. On the -Y-most strings that clips it to nothing and it is dropped: the boss
    # in its slot already fixes X, and the belt pulls the motor onto the +X post, not this one.
    # ...and where the corridor took that post away (strings 9-10), a one-bead FIN on the -X
    # side of the FRONT band instead, opposite the +X post. The boss in the wall's slot already
    # holds the motor's front to +-0.4 either way, but with no -X post its BACK can yaw about
    # that boss until it touches the neighbour (1.6 over 70, ~1.3 deg). The front band is the
    # only -X room left: the neighbour's body is there, so 0.8 is what fits between two 0.4
    # fits -- but it fuses to the faceplate wall along its front edge, so it is braced, not a
    # free-standing fin.
    if _post_y(i) is None:
        _fl = STAGGER - NEIGH_CLR
        body = body.union(box_at(D.MIN_WALL, _fl, FIN_H,
                                 x=bx0 - MOTOR_CLR - D.MIN_WALL / 2,
                                 y=by1 - _fl / 2,
                                 z=bz0 + FIN_H / 2))
    _band = _post_y(i)
    if _band is not None:
        body = body.union(box_at(POST_T, _band[1] - _band[0], bz1 - bz0,
                                 x=bx0 - MOTOR_CLR - POST_T / 2,
                                 y=(_band[0] + _band[1]) / 2,
                                 z=(bz0 + bz1) / 2))
    # back bumper: low, so the pigtail leaves over it. On the -Y-most strings its back face
    # lands inside the chassis rail and simply fuses with it -- no new thickness anywhere.
    # Its width is the MOTOR's, not the pocket's: the bank is staggered, so a bumper as wide
    # as the housing reaches into the -X neighbour's BODY (it lies 9.5 further -Y, right across
    # this Y band) -- 344 mm3 of it, which also blocked that motor's way in. 43.1 keeps 1.2 off
    # both neighbours; the -X post reaches back to meet it, and the rib under both fuses them.
    if back_stop_kind(i) == "bumper":
        body = body.union(box_at(D.MOTOR_SQ + 2 * MOTOR_CLR, BUMP_T, BUMP_H,
                                 x=(bx0 + bx1) / 2, y=by0 - MOTOR_CLR - BUMP_T / 2,
                                 z=bz0 + BUMP_H / 2))
    elif back_stop_kind(i) == "tab":
        # no room for a bumper beside the corridor, but this motor still has its -X post:
        # a 45 deg wedge grows out of the post's side ABOVE the corridor and laps the
        # motor's back. Self-supporting (the hypotenuse is its underside) and it leaves the
        # pigtail its run underneath.
        _x0 = bx0 - MOTOR_CLR
        _prof = [(_x0, HARNESS_Z1), (_x0 + (bz1 - HARNESS_Z1), bz1), (_x0, bz1)]
        _y = by0 - MOTOR_CLR - BUMP_T
        body = body.union(cq.Workplane("XZ").workplane(offset=-(_y + BUMP_T))
                          .polyline(_prof).close().extrude(BUMP_T))
    return body


def back_stop_kind(i):
    """Which -Y stop motor i can have. The bank is staggered, so how much room a motor has
    behind it depends on its string: string 1's back is 87 clear of the -Y rail, string 10's
    is 2.0. And the strip along that rail is the HARNESS CORRIDOR, which nothing may enter.
      bumper  the full-width block at the back face (strings 1-7)
      tab     a wedge off this motor's own -X post, over the corridor (string 8)
      rail    a ramp off the RAIL itself, which is right there (strings 9-10) -- the user's
              "merge that back wall into the chassis wall"; chassis builds it, since the rail
              is its own. It is a 45 deg face, so pushing the motor -Y lifts it against its
              retaining screw rather than moving it."""
    _, _, by0, _, _, bz1 = body_box(i)
    if by0 - MOTOR_CLR - BUMP_T >= HARNESS_Y1:
        return "bumper"
    return "tab" if _post_y(i) is not None else "rail"


def back_stop_rail(i, rail_inner_y):
    """The 'rail' back stop, for the motors whose backs nearly touch the -Y rail: a 45 deg
    ramp off the rail's inner face, rising from over the harness corridor to the motor's top.
    Built by the chassis (it owns the rail) and only where back_stop_kind says so."""
    bx0, bx1, by0, _, _, bz1 = body_box(i)
    # 45 deg is the STEEPEST the underside may be shallower than, so the reach is capped by the
    # rise available over the corridor. String 10 needs 1.6 and gets it; string 9 needs 11.1 and
    # the rise affords 10.95, so its stop lands 0.15 shy -- that much -Y play, not an overhang.
    reach = min(by0 - MOTOR_CLR - rail_inner_y, bz1 - HARNESS_Z1)
    y1 = rail_inner_y + reach
    prof = [(rail_inner_y, HARNESS_Z1), (y1, bz1), (rail_inner_y, bz1)]
    ramp = (cq.Workplane("YZ").workplane(offset=bx0 - MOTOR_CLR)
            .polyline(prof).close().extrude(bx1 - bx0 + 2 * MOTOR_CLR))
    # ...with a lane for the motor's own CAN pigtail, which leaves the back face on the
    # centreline and has to climb PAST this stop to reach its tee
    lane = D.motor_pos(i)[0]
    return ramp.cut(box_at(WIRE_LANE_W, (y1 - rail_inner_y) + 2.0, (bz1 - HARNESS_Z1) + 2.0,
                           x=lane, y=(rail_inner_y + y1) / 2, z=(HARNESS_Z1 + bz1) / 2))


def _post_y(i):
    """(y0, y1) of motor i's -X post, or None where the corridor leaves no room for one."""
    _, _, by0, _, _, _ = body_box(i)
    y1 = by0 + (STAGGER - NEIGH_CLR)
    y0 = max(by0 - MOTOR_CLR - BUMP_T, HARNESS_Y1)
    return (y0, y1) if y1 - y0 >= 4 * D.BEAD else None


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
