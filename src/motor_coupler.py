# -*- coding: utf-8 -*-
"""THE PRINTED MOTOR COUPLER (user, 2026-11-09): one piece from a SERVO42D's shaft to a Tr8x2
leadscrew, shared by the direct bench and the plank bench's in-line motor.

Drawn in the MOTOR'S OWN FRAME (components.motor_parts): shaft +Y from the pulley plane y = 0,
the D's flat facing +Z. y from the pulley plane:
  MOTOR END  the motor pulley's own open D bore (components.MOTOR_BORE_CLR) over the shaft's flat,
             -4 .. +4: its -Y face on the D key's stop, the shaft cut flush at +4 as for the
             pulley (MOTOR_SHAFT_CUT_L). A friction fit: it TURNS the screw, nothing more.
  SCREW END  a plain Ø8.4 socket the screw slides into (no thread), its end 0.5 past the shaft's,
             and ONE M3 x 12 SHCS (the belt clamps', belt_tensioner.SCREW_L) sideways through the
             coupler and a 1/8 in hole drilled through the screw (src.pin_drill_jig), threading
             the far wall: a pin for the torque.
  BOSS       optional, on the screw end: a Ø10.4 boss that bears on a 688's INNER race only, when
             the coupler is also the screw's thrust shoulder (the plank bench's X rig).
"""
from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_x, cyl_y

CPL_D = 18.0
CPL_X = (-4.0, 15.0)                                # y from..to past the pulley plane
CPL_GRIP = 4.0                                      # the D bore's end: the shaft's cut
SCREW_X0 = CPL_GRIP + 0.5                           # the screw's end
SOCKET_D = D.SCREW_OD + 0.4
PIN_FROM_END = 5.0                                  # the M3's axis from the screw's end: 3.4 of
                                                    # steel past a 1/8 hole (the plank's screw has
                                                    # only 9.5 out past its 688 to hold a coupler)
PIN_X = SCREW_X0 + PIN_FROM_END
M3_PILOT = 2.5
M3_HEAD = (5.5, 3.0)
M3_L = 12.0
RACE_IN_D = 10.4                                    # a boss on a 688's inner race only


def coupler(c1: float = CPL_X[1], boss_l: float = 0.0) -> cq.Workplane:
    """The coupler in the motor's frame, to y = c1 (+ a boss_l long inner-race boss)."""
    from . import components as C
    c0 = CPL_X[0]
    out = cyl_y(CPL_D, c1 - c0, y0=c0)
    if boss_l:
        out = out.union(cyl_y(RACE_IN_D, boss_l + 0.01, y0=c1 - 0.01))
    r = D.MOTOR_SHAFT_D / 2.0 + C.MOTOR_BORE_CLR                    # the pulley's D bore
    zf = D.MOTOR_SHAFT_FLAT - D.MOTOR_SHAFT_D / 2.0 + C.MOTOR_BORE_CLR
    bore = cyl_y(2 * r, CPL_GRIP - c0 + 1.0, y0=c0 - 1.0).cut(
        box_at(2 * r + 1.0, 20.0, r + 1.0 - zf, y=0.0, z=(zf + r + 1.0) / 2.0))
    out = out.cut(bore)
    out = out.cut(cyl_y(SOCKET_D, c1 + boss_l - CPL_GRIP + 1.0, y0=CPL_GRIP))   # the socket
    rs = SOCKET_D / 2
    # PRINTS standing on its motor end (+Y up): the pin's holes are teardrops peaked +Y, and the
    # head's pocket is a SLOT open out through the screw end, so nothing is roofed over it
    from cadkit.holes import teardrop_hole
    up = (0.0, 1.0, 0.0)
    tip = SOCKET_D / 2 + 1.0 - M3_L                 # the M3's tip (its head's underside less 12)
    p0 = tip - 0.2                                  # BLIND: 2.0 of skin left outside it
    out = out.cut(teardrop_hole(M3_PILOT, -p0 + 1.0, axis_point=(p0, PIN_X, 0),
                                axis_dir=(1, 0, 0), print_up=up))          # far wall: threads
    out = out.cut(teardrop_hole(3.4, CPL_D, axis_point=(0.0, PIN_X, 0),
                                axis_dir=(1, 0, 0), print_up=up))          # near wall: clear
    hd = M3_HEAD[0] + 0.7
    top = c1 + boss_l + 1.0                         # the head's pocket: a square-bottomed slot,
    y0 = PIN_X - hd / 2                             # open out through the screw end (a round one
    out = out.cut(box_at(CPL_D, top - y0, hd, x=rs + 1.0 + CPL_D / 2,    # left a knife edge
                         y=(y0 + top) / 2, z=0))                          # where it met the skin)
    # ...and a FLAT across that side, so the slot's walls meet the skin square, not in a wedge
    fx = CPL_D / 2 - 1.2
    return out.cut(box_at(CPL_D, top - y0, CPL_D + 2, x=fx + CPL_D / 2, y=(y0 + top) / 2, z=0))


def coupler_m3() -> cq.Workplane:
    """The pin, in the motor's frame: head in the pocket on +x, through to the far wall."""
    h0 = SOCKET_D / 2 + 1.0                         # the head's underside: 1.0 of wall
    return cap_screw("m3", M3_L, (h0 + M3_HEAD[1], PIN_X, 0), (-1, 0, 0))


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
