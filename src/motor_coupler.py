# -*- coding: utf-8 -*-
"""THE PRINTED MOTOR COUPLER (user, 2026-11-09): one piece from a SERVO42D's shaft to a Tr8x2
leadscrew, shared by the direct bench and the plank bench's in-line motor.

Drawn in the MOTOR'S OWN FRAME (components.motor_parts): shaft +Y from the pulley plane y = 0,
the D's flat facing +Z. y from the pulley plane:
  MOTOR END  a D bore over the shaft's flat, -4 .. +4: its -Y face on the D key's stop, the shaft
             cut flush at +4 as for the pulley (MOTOR_SHAFT_CUT_L). The D key turns it.
  SCREW END  the SCREW PULLEY'S KIND OF GRIP (user, 2026-11-10: the screw was too tough to drill
             for the old M3 cross pin; "the screw pulley we already designed grips quite well on
             the screw ... keep that and add a C clamp"): a FORMED-THREAD socket, the screw
             threaded in to SCREW_X0 (0.5 past the shaft's end). Then a C CLAMP over it: the body
             SLIT along its whole length on -Z (away from the D's flat, so the key keeps its
             whole flat), and an EAR over the socket carrying ONE M3 x 12 SHCS across the slit,
             head on +x, into an M3 insert FITTED as a NUT, no heat (user, 2026-11-10) -- the
             BELT CLAMP'S screw and insert (belt_tensioner.M3 / INS_POCKET, the pocket that takes
             the knurled insert by hand): the insert slides into the -x jaw from its -x face and
             the screw pulls it onto a lip (CLAMP_LIP) toward the slit.
  BOSS       optional, on the screw end: a Ø10.4 boss that bears on a 688's INNER race only, when
             the coupler is also the screw's thrust shoulder (the plank bench's X rig). The
             string's pull jams the formed thread just as it does the pulley's.

PRINTS IN PETG-GF ON THE 0.8 NOZZLE (user, 2026-11-10: "more dimensionally stable"), standing
on its motor end (+Y up): the slit vertical, the M3's hole and the insert's pocket teardrops
peaked +Y, the ear's underside a 45 deg cone off the body. Drawn AS THAT SETUP PRINTS IT:
  CORNERS    every corner made INSIDE A LAYER (an edge along the build, +Y) is drawn at the
             nozzle's measured turning radius, cadkit.print_corners.DRAW_MIN["nozzle"] (2.0,
             convex and concave): the slit's edges, the ear's, the ear's joins to the body and
             the D bore's corners (user, 2026-11-10: "model the path it can realistically take").
             Corners made across layers stay square.
  BORES      a hole on this setup prints HOLE_SHRINK small on its radius (the 1/8 in drill
             bushing drawn 0.3 a side over the bit: tight, the bit runs through; the D bore at the
             pulley's 0.05 a side: too small). The D bore is the shaft + HOLE_SHRINK a side.
  THREAD     the socket is the pulley's formed thread re-drawn for 0.8 (user, 2026-11-10: "the
             threads don't need to fit the screw perfectly, just ... maximize contact area"):
               its groove Ø the screw's crest + HOLE_SHRINK a side, so it PRINTS at the crest as
               the pulley's does (line to line);
               its ridge RIDGE_H deep, 45 deg flanks both sides (self-supporting standing up):
               as deep as a 90 deg ridge can go into Tr8x2's 30 deg groove before its flanks
               meet the screw's crest corners (RIDGE_MAX, 0.63), vs the pulley's 0.45. A deeper
               ridge cannot add flank contact without a steeper flank, and the load flank is the
               ridge's underside, an overhang in this print.
             The slit lets it open if it prints tight; the clamp closes it if it prints loose.
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
M3_HEAD = (5.5, 3.0)                                # the benches' M3 SHCS (motor face screws)
M3_L = 12.0
RACE_IN_D = 10.4                                    # a boss on a 688's inner race only
PRINT_SETUP = ("PETG-GF", 0.8)

# ── drawn as PETG-GF on 0.8 prints it ───────────────────────────────────────────────────────
from cadkit.print_corners import DRAW_MIN           # noqa: E402
CORNER_R = max(DRAW_MIN["nozzle"])                  # 2.0: in-layer corners, convex and concave
HOLE_SHRINK = 0.3                                   # a round hole's radius prints this much small
D_BORE_R = D.MOTOR_SHAFT_D / 2 + HOLE_SHRINK        # 2.8
D_FLAT_Z = D.MOTOR_SHAFT_FLAT - D.MOTOR_SHAFT_D / 2 + HOLE_SHRINK   # 2.3: the flat, off the axis
# Tr8x2 (ISO 2904): crest flat 0.732 at Ø8, flanks 15 deg off radial -> groove 1.268 wide at the crest
_GROOVE_AT_CREST = D.SCREW_PITCH - (D.SCREW_PITCH / 2 - 2 * 0.25 * D.SCREW_PITCH * math.tan(math.radians(15)))
RIDGE_MAX = _GROOVE_AT_CREST / 2                    # 0.634: a 90 deg ridge's depth at that width
RIDGE_H = 0.6
assert RIDGE_H <= RIDGE_MAX, "the ridge's flanks run into the screw's crest corners"
FORM_MAJOR_C = D.SCREW_OD + 2 * HOLE_SHRINK         # 8.6: prints at the crest, 8.0
FORM_MINOR_C = FORM_MAJOR_C - 2 * RIDGE_H           # 7.4
SOCKET_D = FORM_MAJOR_C                             # the formed thread's groove Ø (its envelope)

# ── the C clamp: the belt clamp's M3 x 12 into its M3 insert, fitted as a nut. On -Z ────────
from . import belt_tensioner as _BT                 # noqa: E402
SLIT_W = 1.2                                        # the slit, on -Z: 1.5 beads, prints open
CLAMP_SPEC = _BT.M3                                 # insert_l 4.3, OD 4.7
CLAMP_L = _BT.SCREW_L                               # 12
CLAMP_HEAD = (_BT.HEAD_D, _BT.HEAD_H)               # 5.5 x 3
INSERT_POCKET_D = _BT.INS_POCKET                    # 4.8: takes the knurled insert by hand
CLAMP_LIP = 3 * D.BEAD                              # 2.4: the -x jaw from the slit to the insert
INS_X0 = -(SLIT_W / 2 + CLAMP_LIP)                  # -3.0: the insert's +x end, on the lip
EAR_X = (INS_X0 - CLAMP_SPEC.insert_l, INS_X0 - CLAMP_SPEC.insert_l + CLAMP_L)   # -7.3 .. 4.7:
                                                    # the insert flush with -x, the 12's tip at its
                                                    # far end (all 4.3 of it bitten), the head on +x
CLAMP_Z = SOCKET_D / 2 + 1.0 + INSERT_POCKET_D / 2  # 7.7 under the axis: 1.0 of wall to the socket
EAR_TOP = max(CLAMP_Z + INSERT_POCKET_D / 2 + 2 * D.BEAD,       # two beads past the pocket, and
              CLAMP_Z + CLAMP_HEAD[0] / 2 + CORNER_R)           # the head's face flat to its rim
EAR_Y0 = 1.3                                        # the ear's foot: 0.8 clear of the plank motor
                                                    # block's face wall (its pilot hole, r 11.3)
SPOT_Z = CLAMP_Z - CLAMP_HEAD[0] / 2 - CORNER_R    # the head's SPOT FACE (x = EAR_X[1]) runs up
                                                    # to z -SPOT_Z, flat past the head's rim
_GROW_R = CPL_D / 2 - CORNER_R - 0.1                # 6.9: the eared section GROWS at 45 deg from this
                                                    # radius over what the plain one under it holds
_APEX = EAR_Y0 - _GROW_R
assert EAR_X[1] - SLIT_W / 2 >= 2 * CORNER_R, "the +x jaw is too thin for its rounded corners"
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
    """The formed-thread cutter (FORM_*_C), along +Y from y0 to past y1. No lead-in at the mouth:
    it would leave the boss's ring under a bead (the screw's own end is chamfered)."""
    from cadkit.threads import threaded_rod
    turns = math.ceil((y1 - y0 + 2.0) / D.SCREW_PITCH)
    t = threaded_rod(FORM_MINOR_C, FORM_MAJOR_C, D.SCREW_PITCH, turns * D.SCREW_PITCH,
                     z=y0, overshoot=0.05, bevel_ends=False)
    return t.rotate((0, 0, 0), (1, 0, 0), -90)        # Z -> +Y


def _round_y_edges(w: cq.Workplane, pts, r: float = CORNER_R) -> cq.Workplane:
    """Fillet the straight edges running along Y whose (x, z) is at one of `pts`."""
    sel = []
    for e in w.val().Edges():
        if e.geomType() != "LINE":
            continue
        a, b = e.startPoint(), e.endPoint()
        if abs(a.x - b.x) > 1e-6 or abs(a.z - b.z) > 1e-6:
            continue
        if any(abs(a.x - px) < 0.02 and abs(a.z - pz) < 0.02 for px, pz in pts):
            sel.append(e)
    assert len(sel) == len(pts), f"rounding {len(pts)} corners, found {len(sel)} edges"
    return cq.Workplane("XY").add(w.val().fillet(r, sel))


def _section(y0: float, y1: float, ear: bool, bore: str) -> cq.Workplane:
    """The body from y0 to y1, its in-layer corners rounded: the Ø18 (+ the ear on -Z), the slit,
    and the bore ("d": the motor's D, "socket": the thread's envelope)."""
    wp = cq.Workplane("XZ", origin=(0, y1, 0))     # local (x, z); extrudes -Y, y1 -> y0
    L = y1 - y0
    R = CPL_D / 2
    s = wp.circle(R).extrude(L)
    pts = []
    if ear:
        s = s.union(wp.center(sum(EAR_X) / 2, -EAR_TOP / 2).rect(EAR_X[1] - EAR_X[0], EAR_TOP).extrude(L))
        s = s.cut(box_at(R, L + 2, EAR_TOP + 1.0, x=EAR_X[1] + R / 2, y=(y0 + y1) / 2,
                         z=-SPOT_Z - (EAR_TOP + 1.0) / 2))                       # the spot face
        pts += [(EAR_X[0], -EAR_TOP), (EAR_X[1], -EAR_TOP)]                      # convex
        pts += [(EAR_X[0], -math.sqrt(R * R - EAR_X[0] ** 2))]                   # concave join
        pts += [(EAR_X[1], -SPOT_Z), (math.sqrt(R * R - SPOT_Z ** 2), -SPOT_Z)]  # the spot face's
        s = _round_y_edges(s, pts)
        pts = []
    rb = D_BORE_R if bore == "d" else SOCKET_D / 2
    hole = wp.circle(rb).extrude(L)
    if bore == "d":
        hole = hole.cut(box_at(2 * rb + 2, L + 2, rb, y=(y0 + y1) / 2, z=D_FLAT_Z + rb / 2))
        xf = math.sqrt(rb * rb - D_FLAT_Z ** 2)
        pts += [(-xf, D_FLAT_Z), (xf, D_FLAT_Z)]                                # the D's corners
    s = s.cut(hole)
    zo = EAR_TOP if ear else R
    s = s.cut(box_at(SLIT_W, L + 2, zo + 1.0, y=(y0 + y1) / 2, z=-(zo + 1.0) / 2))
    zi = math.sqrt(rb * rb - (SLIT_W / 2) ** 2)
    pts += [(-SLIT_W / 2, -zi), (SLIT_W / 2, -zi)]                              # slit at the bore
    if ear:
        pts += [(-SLIT_W / 2, -EAR_TOP), (SLIT_W / 2, -EAR_TOP)]                # ...at the ear's face
    else:
        zs = math.sqrt(R * R - (SLIT_W / 2) ** 2)
        pts += [(-SLIT_W / 2, -zs), (SLIT_W / 2, -zs)]                          # ...at the skin
    return _round_y_edges(s, pts)


def coupler(c1: float = CPL_X[1], boss_l: float = 0.0) -> cq.Workplane:
    """The coupler in the motor's frame, to y = c1 (+ a boss_l long inner-race boss)."""
    from cadkit.holes import teardrop_hole
    c0 = CPL_X[0]
    end = c1 + boss_l
    out = _section(c0, EAR_Y0, False, "d")
    # the eared sections keep what stands on the plain one (its profile carried up) and grow out
    # of it at 45 deg (the cone): no ceiling over the plain one's rounded slit corners or the ear
    held = _section(EAR_Y0 - 0.01, c1, False, "d")
    cone = cq.Workplane("XY").add(cq.Solid.makeCone(0.0, 40.0, 40.0, cq.Vector(0, _APEX, 0),
                                                    cq.Vector(0, 1, 0)))
    eared = _section(EAR_Y0, CPL_GRIP, True, "d").union(_section(CPL_GRIP, c1, True, "socket"))
    out = out.union(eared.intersect(cone.union(held)))
    if boss_l:
        boss = cyl_y(RACE_IN_D, boss_l + 0.01, y0=c1 - 0.01)
        out = out.union(boss.cut(box_at(SLIT_W, boss_l + 2, RACE_IN_D, y=c1 + boss_l / 2,
                                        z=-RACE_IN_D / 2)))
    out = out.cut(_thread_socket(CPL_GRIP, end))                      # the formed thread
    # the clamp: the M3's clearance through the +x jaw and the lip, the insert's pocket in from -x
    yc = clamp_y(c1)
    up = (0.0, 1.0, 0.0)
    out = out.cut(teardrop_hole(CLAMP_SPEC.shaft_clr_d, EAR_X[1] - INS_X0 + 2.0,
                                axis_point=(INS_X0 - 1.0, yc, -CLAMP_Z),
                                axis_dir=(1, 0, 0), print_up=up))
    out = out.cut(teardrop_hole(CLAMP_HEAD[0] + 0.8, 10.0, axis_point=(EAR_X[1], yc, -CLAMP_Z),
                                axis_dir=(1, 0, 0), print_up=up))       # the head's seat
    return out.cut(teardrop_hole(INSERT_POCKET_D, INS_X0 - EAR_X[0] + 1.0,
                                 axis_point=(EAR_X[0] - 1.0, yc, -CLAMP_Z),
                                 axis_dir=(1, 0, 0), print_up=up))


def clamp_parts(c1: float = CPL_X[1]):
    """The clamp's M3 x 12 (on the ear's +x face) and its fitted insert (on the lip), in the
    motor's frame: [("m3", ...), ("insert", ...)]."""
    from cadkit.fasteners import seated_insert
    yc = clamp_y(c1)
    return [("m3", cap_screw("m3", CLAMP_L, (EAR_X[1] + CLAMP_HEAD[1], yc, -CLAMP_Z), (-1, 0, 0))),
            ("insert", seated_insert(CLAMP_SPEC, (INS_X0, yc, -CLAMP_Z), (-1.0, 0.0, 0.0)))]



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
