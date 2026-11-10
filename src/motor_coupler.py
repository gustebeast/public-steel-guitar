# -*- coding: utf-8 -*-
"""THE PRINTED MOTOR COUPLER (user, 2026-11-09): one piece from a SERVO42D's shaft to a Tr8x2
leadscrew, shared by the direct bench and the plank bench's in-line motor.

Drawn in the MOTOR'S OWN FRAME (components.motor_parts): shaft +Y from the pulley plane y = 0,
the D's flat facing +Z. y from the pulley plane:
  MOTOR END  the motor pulley's own open D bore (components.MOTOR_BORE_CLR) over the shaft's flat,
             -4 .. +4: its -Y face on the D key's stop, the shaft cut flush at +4 as for the
             pulley (MOTOR_SHAFT_CUT_L). The D key turns it.
  SCREW END  the SCREW PULLEY'S OWN GRIP (user, 2026-11-10: the screw was too tough to drill for
             the old M3 cross pin; "the screw pulley we already designed grips quite well on
             the screw ... keep that and add a C clamp"): a FORMED-THREAD socket, the pulley's
             cutter (D.FORM_MINOR/FORM_MAJOR), the screw threaded in to SCREW_X0 (0.5 past the
             shaft's end). Then a C CLAMP over it: the body SLIT along its whole length on +Z,
             and an EAR over the socket carrying ONE M4 x 10 BUTTON HEAD (stock, the 2.5 key)
             across the slit, head on +x, into an M4 insert FITTED as a NUT, no heat (user,
             2026-11-10): the insert slides into the -x jaw from its -x face and the screw pulls
             it onto a lip (CLAMP_LIP) toward the slit, as the plank slider's captive nut.
  BOSS       optional, on the screw end: a Ø10.4 boss that bears on a 688's INNER race only, when
             the coupler is also the screw's thrust shoulder (the plank bench's X rig). The
             string's pull jams the formed thread just as it does the pulley's.
PRINTS standing on its motor end (+Y up): the slit is vertical, the M4's hole and the insert's
pocket teardrops peaked +Y, the ear's underside a 45 deg cone off the body.
PRINTS IN PCTG ON THE 0.4 NOZZLE (PRINT_SETUP), like the pulleys: its D bore is the motor pulley's
(MOTOR_BORE_CLR) and its socket the screw pulley's formed thread, both tuned on that setup. A
PETG-GF / 0.8 print's D bore came out too small (user, 2026-11-10).
"""
from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_y

CPL_D = 18.0
CPL_X = (-4.0, 15.0)                                # y from..to past the pulley plane
CPL_GRIP = 4.0                                      # the D bore's end: the shaft's cut
SCREW_X0 = CPL_GRIP + 0.5                           # the screw's end
SOCKET_D = D.FORM_MAJOR                             # the formed thread's groove Ø (its envelope)
M3_HEAD = (5.5, 3.0)                                # the benches' M3 SHCS (motor face screws)
M3_L = 12.0
RACE_IN_D = 10.4                                    # a boss on a 688's inner race only
PRINT_SETUP = ("PCTG", 0.4)                         # the pulleys' (components.PULLEY_NOZZLE_D)

# ── the C clamp: an M4 x 10 button head into a fitted M4 insert ────────────
from cadkit.fasteners import M4                     # noqa: E402
SLIT_W = 1.2                                        # the slit, on +Z: 1.5 beads, prints open
CLAMP_L = 10.0                                      # M4 button stock (D.M4_BUTTON_STOCK_L)
CLAMP_HEAD = (7.6, 2.2)
INSERT_POCKET_D = 5.9                               # teardrop: the plank slider's (SL_POCKET_D),
                                                    # a fitted, unheated insert
CLAMP_LIP = 3 * D.BEAD                              # 2.4: the -x jaw from the slit to the insert
INS_X0 = -(SLIT_W / 2 + CLAMP_LIP)                  # -3.0: the insert's +x end, on the lip
EAR_X = (INS_X0 - M4.insert_l, INS_X0 - M4.min_bite + CLAMP_L)   # -8.0 .. 3.5: the insert flush
                                                    # with -x; the head seats on +x, 3.5 into it
CLAMP_Z = SOCKET_D / 2 + 1.0 + INSERT_POCKET_D / 2  # 7.95: 1.0 of wall over the socket
EAR_TOP = CLAMP_Z + INSERT_POCKET_D / 2 + 2 * D.BEAD   # 12.5: two beads over the pocket
EAR_Y0 = 1.3                                        # the ear's foot: 0.8 clear of the plank motor
                                                    # block's face wall (its pilot hole, r 11.3)
_APEX = EAR_Y0 - (CPL_D / 2 - 0.5)                  # the ear's 45 deg underside: full at r 8.5
assert EAR_X[1] - SLIT_W / 2 >= 2 * D.BEAD, "the +x jaw under the head is too thin"
assert CLAMP_Z - INSERT_POCKET_D / 2 >= SOCKET_D / 2 + 0.8 - 1e-9, "the pocket breaks into the socket"


def clamp_y(c1: float = CPL_X[1]) -> float:
    """The clamp's y: as high as the head allows under the body's end, so the insert's pocket
    clears the ear's 45 deg underside by a bead."""
    y = c1 - CLAMP_HEAD[0] / 2 - 0.2
    rho = math.hypot(EAR_X[0], CLAMP_Z)            # the pocket's outer, lowest corner
    assert y - INSERT_POCKET_D / 2 >= _APEX + rho + D.BEAD - 1e-9, (
        f"the insert's pocket at y {y:.2f} breaks out of the ear's underside: lengthen the coupler")
    return y


def _thread_socket(y0: float, y1: float) -> cq.Workplane:
    """The screw pulley's formed-thread cutter, along +Y from y0 to past y1, + its mouth's
    lead-in (components.screw_pulley)."""
    from cadkit.threads import threaded_rod
    turns = math.ceil((y1 - y0 + 2.0) / D.SCREW_PITCH)
    t = threaded_rod(D.FORM_MINOR, D.FORM_MAJOR, D.SCREW_PITCH, turns * D.SCREW_PITCH,
                     z=y0, overshoot=0.05, bevel_ends=False)
    li = 0.4
    t = t.union(cq.Workplane("XY").circle(D.FORM_MAJOR / 2).workplane(offset=li + 0.01)
                .circle(D.FORM_MAJOR / 2 + li + 0.01).loft().translate((0, 0, y1 - li)))
    return t.rotate((0, 0, 0), (1, 0, 0), -90)        # Z -> +Y


def coupler(c1: float = CPL_X[1], boss_l: float = 0.0) -> cq.Workplane:
    """The coupler in the motor's frame, to y = c1 (+ a boss_l long inner-race boss)."""
    from . import components as C
    from cadkit.holes import teardrop_hole
    c0 = CPL_X[0]
    end = c1 + boss_l
    out = cyl_y(CPL_D, c1 - c0, y0=c0)
    if boss_l:
        out = out.union(cyl_y(RACE_IN_D, boss_l + 0.01, y0=c1 - 0.01))
    # THE EAR over the socket, its underside a 45 deg cone out of the body (no ceiling)
    e0 = EAR_Y0
    ear = box_at(EAR_X[1] - EAR_X[0], c1 - e0, EAR_TOP, x=sum(EAR_X) / 2, y=(e0 + c1) / 2,
                 z=EAR_TOP / 2)
    cone = cq.Workplane("XZ").add(cq.Solid.makeCone(0.0, 40.0, 40.0, cq.Vector(0, _APEX, 0),
                                                    cq.Vector(0, 1, 0)))
    out = out.union(ear.intersect(cone))
    # the motor's D bore
    r = D.MOTOR_SHAFT_D / 2.0 + C.MOTOR_BORE_CLR
    zf = D.MOTOR_SHAFT_FLAT - D.MOTOR_SHAFT_D / 2.0 + C.MOTOR_BORE_CLR
    bore = cyl_y(2 * r, CPL_GRIP - c0 + 1.0, y0=c0 - 1.0).cut(
        box_at(2 * r + 1.0, 20.0, r + 1.0 - zf, y=0.0, z=(zf + r + 1.0) / 2.0))
    out = out.cut(bore)
    out = out.cut(_thread_socket(CPL_GRIP, end))                      # the formed thread
    # THE SLIT, the whole length, +Z: the body is a C
    out = out.cut(box_at(SLIT_W, end - c0 + 2.0, EAR_TOP + 2.0, x=0.0, y=(c0 + end) / 2,
                         z=(EAR_TOP + 2.0) / 2))
    # the clamp: the M4's clearance through the +x jaw and the lip, the insert's pocket in from -x
    yc = clamp_y(c1)
    up = (0.0, 1.0, 0.0)
    out = out.cut(teardrop_hole(M4.shaft_clr_d, EAR_X[1] - INS_X0 + 2.0,
                                axis_point=(INS_X0 - 1.0, yc, CLAMP_Z),
                                axis_dir=(1, 0, 0), print_up=up))
    out = out.cut(teardrop_hole(CLAMP_HEAD[0] + 0.8, 10.0, axis_point=(EAR_X[1], yc, CLAMP_Z),
                                axis_dir=(1, 0, 0), print_up=up))       # the head's seat: the body's
                                                                         # round runs past x 3.5 there
    return out.cut(teardrop_hole(INSERT_POCKET_D, INS_X0 - EAR_X[0] + 1.0,
                                 axis_point=(EAR_X[0] - 1.0, yc, CLAMP_Z),
                                 axis_dir=(1, 0, 0), print_up=up))


def clamp_parts(c1: float = CPL_X[1]):
    """The clamp's M4 x 10 button head (on the ear's +x face) and its fitted insert (on the
    lip), in the motor's frame: [("m4", ...), ("insert", ...)]."""
    from cadkit.fasteners import seated_insert
    yc = clamp_y(c1)
    return [("m4", cap_screw("m4", CLAMP_L, (EAR_X[1] + CLAMP_HEAD[1], yc, CLAMP_Z), (-1, 0, 0))),
            ("insert", seated_insert(M4, (INS_X0, yc, CLAMP_Z), (-1.0, 0.0, 0.0)))]


def cap_screw(kind: str, length: float, top, shank_dir) -> cq.Workplane:
    """cadkit's headed screw (head and its hex socket drawn), head TOP at `top`, the shank
    running `shank_dir` from it. "m3": the M3 SHCS the benches use (belt_tensioner's spec,
    as plank_bench's yoke screws); "m4": the M4 button head. Both turn with the 2.5 key."""
    from cadkit.fasteners import M4, headed_screw, _rot_z_onto
    if kind == "m3":
        from . import belt_tensioner as BTn
        s = headed_screw(BTn.M3, length, BTn.HEAD_D, BTn.HEAD_H, 2.5)
    else:
        s = headed_screw(M4, length, 7.6, 2.2, 2.5)
    d = tuple(-c for c in shank_dir)                # headed_screw's shank runs -Z
    return _rot_z_onto(s, d).translate(tuple(top))
