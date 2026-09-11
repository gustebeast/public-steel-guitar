"""Motor bank (§5) — PCTG. The under-string staircase.

The 10 motors lie flat under the speaking length, shaft +Y (bodies extend −Y
toward the player). They step along −X by MOTOR_X_STEP so they don't overlap,
each on its string's Y line. Each mounts to a faceplate wall (an X–Z plane at
its faceplate Y) carrying a NEMA17 pattern; motors and walls rest on the
chassis's per-motor cross-ribs (no floor plate — the walls are fused into the
chassis). Built in global position.

DROP-IN POCKETS (user, 2026-09-11). The motors do not bolt to anything any more:
each drops STRAIGHT DOWN into a pocket that stops it in every other direction,
and ONE screw stops it coming back out. Install: slip the belt over the pulley,
lower the motor in, drive its screw. Remove: back the screw out and lift.

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
from cadkit.fasteners import M4 as _M4, M4_BUTTON_HEAD_D, M4_BUTTON_HEAD_H, selftap_cutter

PLATE_T      = 8 * D.NOZZLE_D    # 6.4 (was 6.0 = 7.5 beads)
_BOLT_EDGE   = 7 * D.BEAD                   # 5.6 material around the NEMA17 bolt square
                                            # (was 6.0 = 7.5 beads; snapped DOWN — the
                                            # gaps to the chassis split planes and the
                                            # neighbouring motor GROW)

WALL_W = D.NEMA17_BOLT_SQ + 2 * _BOLT_EDGE  # 42.2: 0.9 to the chassis split planes,
                                            # 1.75 to the neighbouring motor body

MOTOR_CLR  = 0.4                 # slip fit round a PURCHASED body (42.3 nominal, +-0.2)
BOSS_CLR   = 0.4                 # round the O22 pilot boss in its drop-in slot
POST_T     = 12 * D.BEAD         # 9.6 side post (X). Capped by the NEIGHBOUR's boss slot,
                                 # which the post has to keep a wall off -- asserted below
POST_RISE  = 10 * D.BEAD         # 8.0: how far the screw post stands over the motor top
NEIGH_CLR  = D.MIN_WALL          # 0.8 air to the diagonal neighbour's body, at the band end
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

# THE RETAINING SCREW (user, 2026-09-11): one M4 button at 45 deg in the X-Z plane. Its head
# lands on the +X post's chamfered top -- reachable straight down at 45 deg on every string,
# which neither a +Y-facing head (string 1 is jammed against the +Y rail) nor a -Y one
# (strings 9-10 sit on the rail) manages -- and its shank crosses the motor's top +X corner,
# so the motor cannot rise. SELF-TAPPING, not an insert: a 45 deg insert pocket spans 8.5 in
# X and the post cannot be that thick, while the 4.2 self-tap leaves 1.8 of wall either side.
# It carries almost nothing: the belt pulls the motor into this same post, and gravity holds
# it down; the screw only has to stop it lifting out.
# The axis is AIMED at the motor's top face, SCREW_CROSS inboard of the +X corner, and the
# screw stops short of it: the shank passes about a millimetre over the top face, so the motor
# is free at rest and jams into the shank the moment it rises. (Aimed AT the corner instead,
# a screw long enough to bite would have driven its tip into the motor body -- everything
# past that corner IS the motor.)
SCREW_CROSS  = 2.5                          # where the axis meets the top face, off the corner
SCREW_RECESS = 3 * D.BEAD                   # 2.4 head recess in the chamfer
SCREW_L      = 6.0                          # M4x6 button
SCREW_FACE   = 12 * D.BEAD                  # 9.6: the chamfer face, out along the diagonal --
                                            # what buys the self-tap its bite in the post

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
Z_HI = _zc + D.NEMA17_BOLT_SQ / 2 + _BOLT_EDGE     # wall top, just above the top bolts


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


def screw_axis(i):
    """(entry, direction) of motor i's retaining screw: 45 deg in the X-Z plane, head on the
    +X post's chamfer, shank passing over the motor's top face just inboard of its +X corner."""
    _, bx1, by0, by1, _, bz1 = body_box(i)
    k = 1.0 / math.sqrt(2.0)
    n = (k, 0.0, k)                                             # outboard, up the diagonal
    aim = (bx1 + MOTOR_CLR - SCREW_CROSS, bz1 + MOTOR_CLR)      # where it crosses the top face
    entry = (aim[0] + n[0] * SCREW_FACE,
             (by1 + (by1 - STAGGER + NEIGH_CLR)) / 2,
             aim[1] + n[2] * SCREW_FACE)
    return entry, (-n[0], 0.0, -n[2])


def screw_cutter(i) -> cq.Workplane:
    """The screw's hole. CUT AFTER THE CHASSIS UNIONS THE POCKET (chassis does it): the
    neighbour's faceplate wall fuses into this post's band, and a hole cut here first would
    be silently refilled by it -- the same trap the endplates' cut order documents."""
    entry, d = screw_axis(i)
    cut = selftap_cutter(_M4, entry, d, SCREW_RECESS + SCREW_L + 1.0,
                         overshoot=1.0, print_up=(0.0, 0.0, 1.0))
    head = cq.Solid.makeCylinder((M4_BUTTON_HEAD_D + 0.8) / 2, SCREW_RECESS + 1.0,
                                 cq.Vector(entry[0] - d[0], entry[1], entry[2] - d[2]),
                                 cq.Vector(*d))
    return cut.union(cq.Workplane(obj=head))


def screw_dummy(i) -> cq.Workplane:
    """The screw itself, seated -- head bottom on the chamfer's recess floor."""
    from cadkit.fasteners import m4_button_screw
    entry, d = screw_axis(i)
    off = SCREW_RECESS - M4_BUTTON_HEAD_H              # the head sits just under the face
    s = m4_button_screw(SCREW_L).rotate((0, 0, 0), (0, 1, 0), 45.0)   # shank -Z -> along d
    return s.translate((entry[0] + d[0] * off, entry[1], entry[2] + d[2] * off))


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
    _x0 = mx - WALL_W / 2
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
    body = body.union(box_at(POST_T, _pl, (bz1 + POST_RISE) - bz0,
                             x=px0 + POST_T / 2,
                             y=by1 + PLATE_T - _pl / 2,
                             z=(bz0 + bz1 + POST_RISE) / 2))
    # its top-outboard corner cut back to a 45 deg face, square to the screw
    entry, d = screw_axis(i)
    body = body.cut(cq.Workplane("XY").box(200.0, 200.0, 200.0)
                    .rotate((0, 0, 0), (0, 1, 0), -45.0)
                    .translate((entry[0] - d[0] * 100.0, entry[1], entry[2] - d[2] * 100.0)))
    # -X post: the mirror band, at the BACK (the -X neighbour ends STAGGER short of it),
    # running -Y into the bumper so the housing prints as one piece -- but never past
    # HARNESS_Y1. On the -Y-most strings that clips it to nothing and it is dropped: the boss
    # in its slot already fixes X, and the belt pulls the motor onto the +X post, not this one.
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
    return (cq.Workplane("YZ").workplane(offset=bx0 - MOTOR_CLR)
            .polyline(prof).close().extrude(bx1 - bx0 + 2 * MOTOR_CLR))


def _post_y(i):
    """(y0, y1) of motor i's -X post, or None where the corridor leaves no room for one."""
    _, _, by0, _, _, _ = body_box(i)
    y1 = by0 + (STAGGER - NEIGH_CLR)
    y0 = max(by0 - MOTOR_CLR - BUMP_T, HARNESS_Y1)
    return (y0, y1) if y1 - y0 >= 4 * D.BEAD else None


plates = [pocket(i) for i in range(D.N_STRINGS)]
screw_cutters = [screw_cutter(i) for i in range(D.N_STRINGS)]

# the post stops short of the NEIGHBOUR's boss slot (both sides are the same by symmetry)
_slot_edge = D.MOTOR_X_STEP - (D.NEMA17_PILOT_D + 2 * BOSS_CLR) / 2
assert (D.MOTOR_SQ / 2 + MOTOR_CLR + POST_T) <= _slot_edge - D.MIN_WALL + 1e-9, (
    "the side post reaches within %.2f of the neighbour's boss slot"
    % (_slot_edge - (D.MOTOR_SQ / 2 + MOTOR_CLR + POST_T)))
# ...the screw finds enough plastic to bite (the post's material runs from the chamfer in
# to where the axis leaves its inboard face, over the motor's corner)
_bite = SCREW_FACE - SCREW_CROSS * math.sqrt(2.0) - SCREW_RECESS
assert _bite >= _M4.min_bite - 1e-9, (
    "the retaining screw bites only %.2f of self-tap, under min_bite %.2f"
    % (_bite, _M4.min_bite))
# ...its tip stops SHORT of the motor's top face (past it is the motor itself)
assert SCREW_RECESS + SCREW_L + 0.5 <= SCREW_FACE + 1e-9, (
    "an M4x%.0f drives %.2f into the motor" % (SCREW_L, SCREW_RECESS + SCREW_L - SCREW_FACE))
# ...and the post stands high enough to carry the chamfer the head lands on
assert POST_RISE >= MOTOR_CLR + SCREW_FACE / math.sqrt(2.0) + D.MIN_WALL - 1e-9, (
    "the screw's entry is above the post top")


def _build() -> cq.Workplane:
    body = plates[0]
    for w in plates[1:]:
        body = body.union(w)
    return body


motor_bank = _build()
