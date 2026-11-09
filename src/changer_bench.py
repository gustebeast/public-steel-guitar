"""CHANGER BENCH -- all ten strings' drives in the space the instrument actually has (user, 2026-11-09).

A fit study first and a bench second: every bought part is drawn where it would sit, the printed
frames are plain blocks that only hold them, and the instrument's own limits are drawn as GHOSTS
(the pickup, the deck, the side walls, the keyhead, today's bottom) so a fit is something the
overlap gate measures, not something claimed. What is held from the instrument, unchanged:

    scale       the crown at NUT_BLOCK_X, the bridge bearings' tops at STRING_Z, the strings fanning
                from nut_y (6.5) to string_y (9.5)
    hardware    Tr8x2 screws, the brass H-nuts, 688ZZ thrust bearings, open GT2 5 mm belts with the
                in-line clamp, SERVO42D motors with 14T pulleys, CARRIAGE_TRAVEL of nut travel

THE FOUR CONCEPTS (user):
 1. THE STRING PULLS ON THE SCREW'S AXIS. Each nut carries a YOKE (the plank bench's counter yoke):
    the ball end sits under its roof ON the screw axis, the string runs on up the axis to whatever
    turns it. So the screw sees only axial load -- no ear couple. Coaxial means each screw axis IS
    its string's dead length, which is what lays out the changer:
      NEAR row (strings 1,3,5,7,9) -- the axis is the string leaving the bridge bearing's tangent.
      FAR row  (strings 2,4,6,8,10) -- the string goes on over the bridge to an IDLER (a 688 on a
               second axle) and leaves ITS tangent, X_FAR further +X. Two rows because the nut's
               10.5 flats cannot share a 9.5 lane.
 2. BIG SCREW PULLEYS. 40T on the A planes, 47T on the B planes (vs 14T): the pulley ratio divides
    the motor's torque. What caps them is (a) the neighbour's column passing through the plane at
    the 19.0 in-row pitch (A), the cable legs and the 38.0 in-plane pitch (B), and (b) THE BELT
    CLAMP'S TRAVEL: N teeth circulate N mm of belt per mm of nut, so the run has to carry
    N x CARRIAGE_TRAVEL plus the clamp. That is why the motors live at the far -X end.
 3. MOTORS SHAFT +Z, three abreast, one RANK per belt plane. With shafts parallel to the screws every
    belt is FLAT -- no twist at all -- so the pulleys can be any size and the planes pack tight.
    A belt to a far rank passes OVER the nearer ranks' pulleys, so the ranks stair up: the lowest
    plane drives the nearest rank. To keep a 61 mm motor out of the knees, THE WHOLE DRIVE IS
    TILTED ALPHA about Y (screws, pulleys, belts, motors, all parallel in one frame): the belts
    climb toward the motors and the farthest motor's pulley sits just under the deck.
 4. COUNTER SPRINGS, ALSO ON THE AXIS. The yoke carries an ARM out +-L_ARM along x', and a cable
    leg drops from each tip, point-symmetric about the axis (the tips are +-ARM_DY off the string's
    lane), so the pull is on the axis. The legs turn -X' under everything on floor sheaves, meet in
    a THIMBLE (the two legs share one spring and pull equally), and the spring -- the stainless
    9665K61, a 4 in piece -- lies along the floor with an M4 x 40 adjuster at its far end.
    The legs are where they are because those are the only vertical lanes through the stack: inside
    every belt loop, between its two runs.

FRAMES. World as the instrument (X along the strings, +X the bridge end; Y across; Z up). The
DRIVE FRAME (x', y, z') is the world turned ALPHA about Y with its origin at P_NEAR, the point a
near string leaves the bridge bearing: x' along the belts (+ toward the changer), z' along the
screws (+ toward the bridge). Everything in the drive is drawn in that frame and moved by `dw`.

    py -3.12 -m src.changer_bench          -> the layout report
    view: scope src.changer_bench --attr assembly, `agent_sync.py view --solo`
"""

from __future__ import annotations

import math
import re

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl, cyl_x, cyl_y, ball_bearing

# ─────────────────────────────────────────────────────────────────────────────────────────────
# STRINGS, ROWS AND PLANES
# ─────────────────────────────────────────────────────────────────────────────────────────────
N = D.N_STRINGS
T_TRAVEL = D.CARRIAGE_TRAVEL                        # 8.35 of nut travel, as the instrument
T_OPEN = D.DL_OPEN / T_TRAVEL                       # where open pitch sits in it (from the top)


def far(i: int) -> bool:
    """The instrument's own parity: string 10 (last index) on the far row."""
    return D.screw_far(i)


NEAR_IDX = [i for i in range(N) if not far(i)]      # 0 2 4 6 8: strings 1 3 5 7 9
FAR_IDX = [i for i in range(N) if far(i)]           # 1 3 5 7 9: strings 2 4 6 8 10


def plane_of(i: int) -> str:
    """Alternate strings WITHIN a row take alternate planes, so in-plane neighbours are 38 apart."""
    row = NEAR_IDX if not far(i) else FAR_IDX
    return ("n" if not far(i) else "f") + ("A" if row.index(i) % 2 == 0 else "B")


PLANES = ("nA", "nB", "fA", "fB")                   # top to bottom

X_FAR = 34.0                                        # the far row's axis, x': its -X' legs (17.5)
                                                    # clear the near B belts (reach 15.6)
# Teeth. A: a B column (Ø9.6) passes 19.0 away through the plane -> flange R <= 19 - 4.8 - 0.6.
# B: the cable legs stand L_ARM off the axis inside the loop -> flange R <= L_ARM - 0.5 - 0.5.
TEETH = {"nA": 40, "nB": 47, "fA": 40, "fB": 47}
# STRING 1 IS CAPPED BY THE +Y WALL: its pulley sits 12.0 inside the rail's inner face (54.75), so
# its flange may reach 11.7 -> 34T. (String 10's side has the whole -Y half of the body.)
TEETH_CAP = {0: 34}
MOTOR_TEETH = D.PULLEY_TEETH                        # 14, the instrument's motor pulley


def teeth(i: int) -> int:
    return TEETH_CAP.get(i, TEETH[plane_of(i)])


def pd(n: int) -> float:
    return n * D.BELT_PITCH / math.pi


def flange_r(n: int) -> float:
    return (pd(n) - 0.5) / 2 + 1.1                  # OD + a 1.1 lip


# ─────────────────────────────────────────────────────────────────────────────────────────────
# THE STACK, along z' (each row: yoke, nut, travel, 688, pulley)
# ─────────────────────────────────────────────────────────────────────────────────────────────
YK_H = 20 * D.BEAD                                  # 16.0 yoke over the nut's flange (plank bench)
YK_ROOF = 3 * D.BEAD                                # 2.4 over the ball end
Z_YT_NEAR = -11.2                                   # near yoke top, top of travel: world -3.2 at
                                                    # ALPHA 0, the instrument's changer ceiling
SCREW_END_GAP = D.SCREW_END_GAP                     # the screw's top under the flange, top of travel
BRG_W = D.BRG688_W
LEDGE_T = 5 * D.BEAD                                # 4.0 of bearing plate over the 688s
COL_A = 2.7                                         # A pulley's column over its top flange: the
                                                    # socket (9.7) = col + flange + band + flange
FL_T = D.PULLEY_FLANGE_T                            # 0.8
BAND = D.PULLEY_GAP                                 # 5.4
P_HALF = BAND / 2 + FL_T                            # 3.5 band centre to a flange's outer face
SOCKET_L = COL_A + FL_T + BAND + FL_T               # 9.7
DZ_AB = 7.6                                         # A band -> B band (A's flange over B's: 0.6)
DZ_NF = 7.6                                         # near B band -> far A band (far belt under near B)
B_COL_D = 12 * D.BEAD                               # 9.6, the B column (and A's)


def bb_of(row: str) -> float:
    """The 688's bottom face = the pulley's top, z'."""
    if row == "n":
        z_ft = Z_YT_NEAR - YK_H                     # flange top, top of travel
        return z_ft - D.NUT_H - T_TRAVEL - BRG_W
    return band("fA") + COL_A + FL_T + BAND / 2


def band(p: str) -> float:
    """Band centre of plane p, z'."""
    a = bb_of("n") - COL_A - FL_T - BAND / 2
    return {"nA": a, "nB": a - DZ_AB, "fA": a - DZ_AB - DZ_NF,
            "fB": a - 2 * DZ_AB - DZ_NF}[p]


def col_len(p: str) -> float:
    return COL_A + (DZ_AB if p[1] == "B" else 0.0)


def z_yt(row: str) -> float:
    """Yoke top at the top of travel; the far row's stack hangs from its own (lower) 688s."""
    return Z_YT_NEAR - (bb_of("n") - bb_of(row))


def x_of(i: int) -> float:
    return X_FAR if far(i) else 0.0


def row_of(i: int) -> str:
    return "f" if far(i) else "n"


def stack(i: int, t: float = T_OPEN) -> dict:
    """z' of everything on string i's axis at travel fraction t (0 = top / slack, 1 = bottom)."""
    r = row_of(i)
    yt = z_yt(r) - t * T_TRAVEL
    ft = yt - YK_H                                  # nut flange top (the yoke sits on it)
    bb = bb_of(r)
    screw_top = z_yt(r) - YK_H - SCREW_END_GAP
    screw_bot = bb - SOCKET_L + 0.2
    return {"yoke_top": yt, "flange_top": ft, "nut_bot": ft - D.NUT_H,
            "brg_top": bb + BRG_W, "bb": bb, "band": band(plane_of(i)),
            "screw_top": screw_top, "screw_bot": screw_bot,
            "ball": yt - YK_ROOF - D.STRING_NUT_D / 2}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# THE DRIVE FRAME
# ─────────────────────────────────────────────────────────────────────────────────────────────
BR_R = D.BRIDGE_BEARING_OD / 2                      # 8
BR_C = (D.BRIDGE_AXLE_X, D.BRIDGE_BEARING_Z)        # (-8, 8) world
DECK_UNDER = -3.2                                   # world: nothing of the drive above this (x < -20)
Y_LO, Y_HI = -116.35, 54.75                         # the rails' inner faces (motor_bank, chassis)
KEYHEAD_X = D.KEYHEAD_INBOARD_X                     # -607.8
BODY_BOT_NOW = -81.8                                # today's bottom (the chassis bed, measured)

MOTOR_STEP = D.MOTOR_SQ + 1.2                       # 43.5 between ranks along x' (bought bodies)
RANK_D0 = 442.0                                     # the nearest rank's distance, x' (see RUN)
MOTOR_CLR = D.MOTOR_CLR
MOTOR_TOP_CLR = 1.6                                 # farthest motor pulley under the deck


def rank_x(p: str) -> float:
    """x' of plane p's motor rank: lowest plane nearest (the stair)."""
    k = {"fB": 0, "fA": 1, "nB": 2, "nA": 3}[p]
    return -(RANK_D0 + k * MOTOR_STEP)


def _alpha() -> float:
    """Tilt that puts the highest motor's pulley (nA, the farthest rank) MOTOR_TOP_CLR under the
    deck: world z of a drive point = P_z - x' sin a + z' cos a, with P on the bridge bearing."""
    x, z = rank_x("nA"), band("nA") + P_HALF
    lo, hi = 0.0, math.radians(20.0)
    for _ in range(60):
        a = (lo + hi) / 2
        px, pz = BR_C[0] + BR_R * math.cos(a), BR_C[1] - BR_R * math.sin(a)
        zw = pz - x * math.sin(a) + z * math.cos(a)
        lo, hi = (a, hi) if zw < DECK_UNDER - MOTOR_TOP_CLR else (lo, a)
    return lo


ALPHA = _alpha()
SA, CA = math.sin(ALPHA), math.cos(ALPHA)
P_NEAR = (BR_C[0] + BR_R * CA, BR_C[1] - BR_R * SA)     # world (x, z): the near string leaves here


def dw(p):
    """Drive point (x', y, z') -> world (x, y, z)."""
    x, y, z = p
    return (P_NEAR[0] + x * CA + z * SA, y, P_NEAR[1] - x * SA + z * CA)


def wd(p):
    """World -> drive."""
    x, y, z = p[0] - P_NEAR[0], p[1], p[2] - P_NEAR[1]
    return (x * CA - z * SA, y, x * SA + z * CA)


def to_w(wp: cq.Workplane) -> cq.Workplane:
    """Move a solid drawn in the drive frame into the world."""
    return wp.rotate((0, 0, 0), (0, 1, 0), math.degrees(ALPHA)).translate((P_NEAR[0], 0, P_NEAR[1]))


# THE IDLER: same 688 as the bridge, its +X' tangent ON the far axis, its centre on the line from
# the bridge's centre at the far strings' BREAK angle (the common tangent of two equal circles
# runs parallel to the line of their centres).
BREAK_DEG = 12.0
_b = math.radians(BREAK_DEG)
_dc = wd((BR_C[0], 0, BR_C[1]))                     # bridge centre, drive (-8, 0, 0)
_cos_ba = math.cos(_b - ALPHA)
IDLER_D = (X_FAR - BR_R - _dc[0]) / _cos_ba         # centre-to-centre
IDLER_C = (X_FAR - BR_R, 0.0, _dc[2] + IDLER_D * math.sin(ALPHA - _b))   # drive


# ─────────────────────────────────────────────────────────────────────────────────────────────
# MOTORS
# ─────────────────────────────────────────────────────────────────────────────────────────────
MOTOR_HALF = D.MOTOR_SQ / 2                         # 21.15
MOTOR_DROP = D.MOTOR_PULLEY_STANDOFF + D.MOTOR_BODY_L   # 60.7 pulley plane -> the motor's back
MOTOR_PLUG = 29.9                                   # coil plug + leads off the axis, on its -Y side
MOTOR_Y_STEP = MOTOR_HALF + MOTOR_PLUG + 1.0       # 52.05 abreast: the plug clears its neighbour
Y_ROOM = (Y_LO + MOTOR_PLUG + MOTOR_CLR, Y_HI - MOTOR_HALF - MOTOR_CLR)


def strings_on(p: str) -> list:
    return sorted((i for i in range(N) if plane_of(i) == p), key=D.string_y, reverse=True)


def motor_y(i: int) -> float:
    """Three abreast at MOTOR_Y_STEP, in the same order as their strings (belts in a plane never
    cross), the group centred on its strings and slid inside the walls."""
    ss = strings_on(plane_of(i))
    n = len(ss)
    c = sum(D.string_y(s) for s in ss) / n
    ys = [c + (n - 1) / 2 * MOTOR_Y_STEP - k * MOTOR_Y_STEP for k in range(n)]
    shift = max(0.0, Y_ROOM[0] - ys[-1]) - max(0.0, ys[0] - Y_ROOM[1])
    return ys[ss.index(i)] + shift


def motor_d(i: int):
    """Motor pulley centre, drive frame."""
    p = plane_of(i)
    return (rank_x(p), motor_y(i), band(p))


# ─────────────────────────────────────────────────────────────────────────────────────────────
# BELT RUN -- what the clamp needs (dimensions.CARRIAGE_TRAVEL's own sum, per string)
# ─────────────────────────────────────────────────────────────────────────────────────────────
BELT_CLAMP_L = D.BELT_CLAMP_L
CLAMP_END_CLR = D.CLAMP_END_CLR
CLAMP_W, CLAMP_T = 8.55, 6.4                        # belt_tensioner's section: across the belt's
                                                    # width (z') and through it


def run_len(i: int) -> float:
    m = motor_d(i)
    return math.hypot(m[0] - x_of(i), m[1] - D.string_y(i))


def clamp_room(i: int) -> float:
    """Belt the clamp can travel on string i's straight run, mm -- needs TEETH x travel."""
    n = teeth(i)
    return (run_len(i) - BELT_CLAMP_L - flange_r(n) - flange_r(MOTOR_TEETH) - 2 * CLAMP_END_CLR)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# COUNTER SPRINGS
# ─────────────────────────────────────────────────────────────────────────────────────────────
L_ARM = 16.5                                        # arm tip off the axis, x'
ARM_DY = 1.6                                        # the tips' lane offset, point-symmetric
ARM_W = 8 * D.BEAD                                  # 6.4 across Y
ARM_H = 6 * D.BEAD                                  # 4.8 tall, at the yoke's top
CABLE_D = 0.8                                       # 1/32 in 7x7 stainless rope
SHEAVE_OD, SHEAVE_R, SHEAVE_W = 12.0, 5.0, 4.0      # 623VV: Ø12 V-groove, cable radius 5, 4 wide
SPRING_OD = 0.375 * 25.4                            # 9665K61
SPRING_F0 = 5.9 * 4.448222                          # 26.2 N initial tension
SPRING_L0 = 4.0 * 25.4                              # a 4 in piece
SPRING_K = 1.87 * 20.0 / 4.0 * 4.448222 / 25.4      # 1.64 N/mm at 4 in (1.87 lbf/in at 20 in)
SPRING_F = 0.5 * 147.0                              # half the heaviest string, at open pitch
PLUG_L = 8.0                                        # a screw-in end plug, each end
THIMBLE_X = {"n": -40.0, "f": -225.0}               # where each row's legs meet their spring
ADJ_L = 40.0                                        # the M4 x 40 adjuster's reach


def spring_stretch(f: float) -> float:
    return (f - SPRING_F0) / SPRING_K


ARM_FLIP = {8}                                      # string 9: its +X' leg would ride string 10's
                                                    # belt, which falls toward its motor


def legs(i: int):
    """The two arm tips, drive (x', y): point-symmetric about the axis."""
    x, y = x_of(i), D.string_y(i)
    dy = -ARM_DY if i in ARM_FLIP else ARM_DY
    return ((x + L_ARM, y + dy), (x - L_ARM, y - dy))


def floor_z() -> float:
    """The floor cable's z': under fB's clamp (thick side down), a sheave's diameter and groove."""
    return band("fB") - CLAMP_W + 3.5 - 0.5 - SHEAVE_OD / 2 - SHEAVE_R


# ─────────────────────────────────────────────────────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────────────────────────────────────────────────────
def report() -> str:
    out = [f"ALPHA {math.degrees(ALPHA):.2f} deg   P_NEAR world ({P_NEAR[0]:.2f}, {P_NEAR[1]:.2f})",
           f"idler centre drive ({IDLER_C[0]:.2f}, {IDLER_C[2]:.2f})  world "
           f"({dw(IDLER_C)[0]:.2f}, {dw(IDLER_C)[2]:.2f})  far break {BREAK_DEG} deg",
           "bands z': " + "  ".join(f"{p} {band(p):.2f}" for p in PLANES),
           f"688 bottoms: near {bb_of('n'):.2f}  far {bb_of('f'):.2f}   yoke tops: near "
           f"{z_yt('n'):.2f}  far {z_yt('f'):.2f}   floor cable {floor_z():.2f}"]
    out.append("string  plane  T   ratio  run    clamp room / need   motor (x', y)   motor back world z")
    for i in range(N):
        p = plane_of(i)
        m = motor_d(i)
        back = dw((m[0], m[1], m[2] - MOTOR_DROP))[2]
        need = teeth(i) * T_TRAVEL
        out.append(f"  {i + 1:2d}    {p}   {teeth(i)}  {teeth(i) / MOTOR_TEETH:4.2f}  {run_len(i):6.1f}  "
                   f"{clamp_room(i):6.1f} / {need:6.1f}  ({m[0]:7.1f}, {m[1]:6.1f})   {back:7.2f}")
    lows = []
    for i in range(N):
        m = motor_d(i)
        for dx in (-MOTOR_HALF, MOTOR_HALF):
            lows.append(dw((m[0] + dx, 0, m[2] - MOTOR_DROP))[2])
    for x in (x_of(0) - L_ARM - SHEAVE_R - SHEAVE_OD / 2, X_FAR + L_ARM):
        lows.append(dw((x, 0, floor_z() - SPRING_OD / 2))[2])
    out.append(f"deepest drive point world z {min(lows):.1f}  (today's bottom {BODY_BOT_NOW})")
    s = spring_stretch(SPRING_F)
    out.append(f"spring: {SPRING_L0:.1f} piece, stretch {s:.1f} at {SPRING_F:.1f} N, "
               f"swing over the travel +-{SPRING_K * T_TRAVEL / 2:.1f} N")
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# GEOMETRY. Bought parts as they are; printed frames as plain blocks that hold them (FIT STUDY).
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _zc(d, z0, z1, x=0.0, y=0.0):
    """Cylinder along z' from z0 to z1 at (x, y), drive frame."""
    return cyl(d, z1 - z0, z=z0).translate((x, y, 0))


def _seg(a, b, d):
    """A round rod from point a to point b (any frame)."""
    va, vb = cq.Vector(*a), cq.Vector(*b)
    v = vb - va
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(d / 2, v.Length, va, v.normalized()))


def _tangent(c1, r1, c2, r2, sg):
    """External tangent of two circles (x, y): the touch points and the unit normal, side sg."""
    dx, dy = c2[0] - c1[0], c2[1] - c1[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    k = (r1 - r2) / L
    s = math.sqrt(max(0.0, 1 - k * k))
    ex, ey = k * ux + sg * s * nx, k * uy + sg * s * ny
    return (c1[0] + r1 * ex, c1[1] + r1 * ey), (c2[0] + r2 * ex, c2[1] + r2 * ey), (ex, ey)


def _hull2(c1, r1, c2, r2, z0, h):
    """Planar convex hull of two circles (x, y), extruded z0..z0+h: a belt loop's outline."""
    a1, a2, _ = _tangent(c1, r1, c2, r2, 1)
    b1, b2, _ = _tangent(c1, r1, c2, r2, -1)
    L = math.hypot(c2[0] - c1[0], c2[1] - c1[1])
    ux, uy = (c2[0] - c1[0]) / L, (c2[1] - c1[1]) / L
    far1 = (c1[0] - r1 * ux, c1[1] - r1 * uy)
    far2 = (c2[0] + r2 * ux, c2[1] + r2 * uy)
    w = (cq.Workplane("XY").workplane(offset=z0).moveTo(*a1).lineTo(*a2)
         .threePointArc(far2, b2).lineTo(*b1).threePointArc(far1, a1).close())
    return w.extrude(h)


def _belt(i: int) -> cq.Workplane:
    p = plane_of(i)
    m = motor_d(i)
    rs, rm = pd(teeth(i)) / 2, pd(MOTOR_TEETH) / 2
    z0 = band(p) - D.BELT_W / 2
    c1, c2 = (x_of(i), D.string_y(i)), (m[0], m[1])
    t = D.BELT_T / 2
    return _hull2(c1, rs + t, c2, rm + t, z0, D.BELT_W).cut(
        _hull2(c1, rs - t, c2, rm - t, z0 - 1, D.BELT_W + 2))


# Which run each clamp rides: +1 the run on the string's +Y side, -1 the -Y side.
# (searched: every other choice has a B clamp meeting an A clamp of the next plane thick side on)
CLAMP_SIDE = {0: -1, 4: 1, 8: 1, 2: 1, 6: 1, 1: -1, 5: -1, 3: 1}


def clamp_side(i: int) -> int:
    return CLAMP_SIDE.get(i, -1 if D.string_y(i) > 0 else 1)


# The in-line clamp is 3.5 across the belt's width on its thin side and 5.05 on the other: the thin
# side goes toward whatever the run passes close by in z'.
# Planes are DZ_AB = 7.6 apart and the clamp is 8.55 tall: a pair's clamps face THIN SIDE TO THIN
# SIDE (3.5 + 3.5 = 7.0) so they can cross in plan. nB / fA face thick to thick and must not cross
# (the gate checks). fB's thick side goes down: the floor sheaves sit under it (floor_z).
CLAMP_THIN_UP = {"nA": False, "nB": False, "fA": False, "fB": True}
CLAMP_THICK = CLAMP_W - 3.5                         # 5.05


def clamp_run(i: int):
    """The clamp's run: its two touch points (drive x', y), screw end first."""
    m = motor_d(i)
    rs, rm = pd(teeth(i)) / 2, pd(MOTOR_TEETH) / 2
    c1, c2 = (x_of(i), D.string_y(i)), (m[0], m[1])
    # side +1 of _tangent is to the LEFT of c1->c2 (heading -X', left is -Y)
    a, b, _ = _tangent(c1, rs, c2, rm, -clamp_side(i))
    return a, b


# string -> window slid off the motor end, mm: nA has slack to spare (34T / 40T on the longest
# runs) and parks its clamps toward the changer, off the nB clamps that converge on its motors.
CLAMP_SHIFT = {0: 200.0, 4: 150.0, 8: 150.0}


def clamp_window(i: int):
    """The stretch of run (distance from the string pulley's touch point) the clamp's body sweeps
    over the travel: parked against the motor end, so it stays clear of the changer's legs."""
    a, b = clamp_run(i)
    s1 = (math.hypot(b[0] - a[0], b[1] - a[1]) - flange_r(MOTOR_TEETH) - CLAMP_END_CLR
          - CLAMP_SHIFT.get(i, 0.0))
    return s1 - teeth(i) * T_TRAVEL - BELT_CLAMP_L, s1


def clamp_envelope(i: int, pad: float = 0.0) -> cq.Workplane:
    """Everywhere the clamp's body goes over the travel (clamp_window), its full section."""
    p = plane_of(i)
    a, b = clamp_run(i)
    s0, s1 = clamp_window(i)
    lo, hi = (-CLAMP_THICK, 3.5) if CLAMP_THIN_UP[p] else (-3.5, CLAMP_THICK)
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    box = box_at(s1 - s0 + 2 * pad, CLAMP_T + 2 * pad, hi - lo + 2 * pad, x=(s0 + s1) / 2, y=0,
                 z=band(p) + (lo + hi) / 2)
    return box.rotate((0, 0, 0), (0, 0, 1), ang).translate((a[0], a[1], 0))


def _pulley(i: int) -> cq.Workplane:
    p, n = plane_of(i), teeth(i)
    z = band(p)
    fr, od = flange_r(n), pd(n) - 0.5
    out = (_zc(2 * fr, z - P_HALF, z - BAND / 2)
           .union(_zc(od, z - BAND / 2, z + BAND / 2))
           .union(_zc(2 * fr, z + BAND / 2, z + P_HALF))
           .union(_zc(B_COL_D, z + P_HALF, z + P_HALF + col_len(p))))
    return out.translate((x_of(i), D.string_y(i), 0))


YOKE_W = 14 * D.BEAD                                # 11.2 across Y: the nut's 10.5 flats + 0.35 a side


def _rod_xy(i: int):
    x = x_of(i)
    return (x - D.NUT_HOLE_DX if not far(i) else x + D.NUT_HOLE_DX, D.string_y(i))


def _yoke(i: int, t: float) -> cq.Workplane:
    st = stack(i, t)
    x, y = x_of(i), D.string_y(i)
    ft, yt = st["flange_top"], st["yoke_top"]
    body = box_at(D.NUT_FLANGE_L, YOKE_W, YK_H, x=x, y=y, z=(ft + yt) / 2)
    arm = box_at(2 * (L_ARM + 2.4), ARM_W, ARM_H, x=x, y=y, z=yt - ARM_H / 2)
    out = body.union(arm)
    out = out.cut(_zc(D.SCREW_OD + 0.8, ft - 1, ft + T_TRAVEL, x=x, y=y))       # the tip's cavity
    out = out.cut(_zc(D.NUT_LIP_D + 0.4, ft - 1, ft + D.NUT_LIP_L + 0.3, x=x, y=y))   # lip register
    rx, ry = _rod_xy(i)
    out = out.cut(_zc(D.GUIDE_ROD_D + 0.4, ft - 1, yt + 1, x=rx, y=ry))         # the rod rides here
    return out


def _plate_z(row: str):
    bb = bb_of(row)
    return bb, bb + BRG_W + LEDGE_T


PLATE_X = {"n": (-14.0, 12.5), "f": (22.0, 48.0)}
CHEEK_Y = ((Y_HI, Y_HI + 8.0), (-80.0, -72.0))  # -Y: outside string 10's belt     # the bench's side cheeks (the rails' places)


def _plate(row: str) -> cq.Workplane:
    z0, z1 = _plate_z(row)
    x0, x1 = PLATE_X[row]
    y0, y1 = CHEEK_Y[1][1], CHEEK_Y[0][0]
    out = box_at(x1 - x0, y1 - y0, z1 - z0, x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(z0 + z1) / 2)
    for i in range(N):
        if row_of(i) != row:
            continue
        x, y = x_of(i), D.string_y(i)
        out = out.cut(_zc(D.BRG688_OD + 0.2, z0 - 1, z0 + BRG_W, x=x, y=y))      # 688 seat, from below
        out = out.cut(_zc(D.NUT_BOSS_D + 0.8, z0, z1 + 1, x=x, y=y))             # the boss's way down
        rx, ry = _rod_xy(i)
        out = out.cut(_zc(D.GUIDE_ROD_D + 0.15, z1 - 2.4, z1 + 1, x=rx, y=ry))    # rod socket
    return out


def _cheeks() -> cq.Workplane:
    """Side cheeks: the bridge axle, the idler axle, both plates and the floor hang off them."""
    zb, zt = floor_z() - 12.0, 12.0
    x0, x1 = -18.0, 56.0                             # x0: under the deck's changer edge (x -21)
    out = None
    for (y0, y1) in CHEEK_Y:
        c = box_at(x1 - x0, y1 - y0, zt - zb, x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(zb + zt) / 2)
        out = c if out is None else out.union(c)
    out = out.cut(cyl_y(D.BRIDGE_AXLE_D + 0.2, 200, -100, x=_dc[0], z=_dc[2]))
    out = out.cut(cyl_y(D.BRIDGE_AXLE_D + 0.2, 200, -100, x=IDLER_C[0], z=IDLER_C[2]))
    return out


def _floor() -> cq.Workplane:
    """The sheave bed under the changer (the twenty floor sheaves stand on it)."""
    z1 = floor_z() - 1.5
    z0 = z1 - 6 * D.BEAD
    x0, x1 = -30.0, 56.0
    y0, y1 = CHEEK_Y[1][1], CHEEK_Y[0][0]
    return box_at(x1 - x0, y1 - y0, z1 - z0, x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(z0 + z1) / 2)


def _sheave_c(xl: float):
    return (xl - SHEAVE_R, floor_z() + SHEAVE_R)


def _spring_parts(i: int, t: float) -> list:
    """Legs, sheaves, floor runs, thimble, spring and adjuster for string i at travel t."""
    st = stack(i, t)
    za = st["yoke_top"] - ARM_H / 2
    zf = floor_z()
    y = D.string_y(i)
    xt = THIMBLE_X[row_of(i)]
    parts = []
    for k, (xl, yl) in enumerate(legs(i)):
        sx, sz = _sheave_c(xl)
        parts.append((f"cb_leg_{k}_{i}", _seg((xl, yl, za), (xl, yl, sz), CABLE_D)))
        parts.append((f"cb_sheave_{k}_{i}",
                      cyl_y(SHEAVE_OD, SHEAVE_W, yl - SHEAVE_W / 2, x=sx, z=sz)))
        parts.append((f"cb_run_{k}_{i}", _seg((sx, yl, zf), (xt, yl, zf), CABLE_D)))
    parts.append((f"cb_thimble_{i}", box_at(2.0, 2 * ARM_DY + 2.4, 2.4, x=xt - 1.0, y=y, z=zf)))
    stretch = spring_stretch(SPRING_F) + (t - T_OPEN) * T_TRAVEL
    xs1 = xt - 2.0                                   # the spring's +X' plug face
    xs0 = xs1 - PLUG_L
    xe0 = xs0 - (SPRING_L0 - 2 * PLUG_L + stretch)   # the coils between the plugs
    parts.append((f"cb_spring_{i}", cyl_x(SPRING_OD, xs0 - xe0, xe0, y=y, z=zf)))
    parts.append((f"cb_plug_a_{i}", cyl_x(SPRING_OD - 1.6, PLUG_L, xs0, y=y, z=zf)))
    parts.append((f"cb_plug_b_{i}", cyl_x(SPRING_OD - 1.6, PLUG_L, xe0 - PLUG_L, y=y, z=zf)))
    xa = xe0 - PLUG_L
    parts.append((f"cb_adjuster_{i}", cyl_x(4.0, ADJ_L, xa - ADJ_L, y=y, z=zf)))
    return parts


def anchor_x(row: str) -> float:
    """The anchor wall's +X' face: the adjuster half run out."""
    xt = THIMBLE_X[row]
    return (xt - 2.0 - PLUG_L - (SPRING_L0 - 2 * PLUG_L + spring_stretch(SPRING_F)) - PLUG_L
            - ADJ_L / 2)


def _anchor(row: str) -> cq.Workplane:
    x1 = anchor_x(row)
    zf = floor_z()
    ys = [D.string_y(i) for i in range(N) if row_of(i) == row]
    w = box_at(8 * D.BEAD, max(ys) - min(ys) + 20, 16, x=x1 - 3.2, y=(max(ys) + min(ys)) / 2, z=zf)
    for y in ys:
        w = w.cut(cyl_x(4.4, 20, x1 - 15, y=y, z=zf))
    if row == "n":                                   # the far row's floor cables pass through
        for i in FAR_IDX:
            for _, yl in legs(i):
                w = w.cut(cyl_x(2.4, 20, x1 - 15, y=yl, z=zf))
    return w


def _rank_plate(p: str) -> cq.Workplane:
    ss = strings_on(p)
    x = rank_x(p)
    ys = [motor_y(i) for i in ss]
    face = band(p) - D.MOTOR_PULLEY_STANDOFF
    y0, y1 = min(ys) - MOTOR_HALF, max(ys) + MOTOR_HALF
    w = box_at(2 * MOTOR_HALF, y1 - y0, 3.0, x=x, y=(y0 + y1) / 2, z=face + 1.5)
    for y in ys:
        w = w.cut(_zc(D.NEMA17_PILOT_D + 0.6, face - 1, face + 5, x=x, y=y))
    for i in ss:                                     # the clamp's lane over the face (no screw there)
        w = w.cut(clamp_envelope(i, 0.5))
    return w


def _motor(i: int) -> list:
    """The SERVO42D one solid per material, named as the build names them (cb_motor_<i> the can,
    cb_motor_<part>_<i> the rest) so each takes its motor_<part> colour."""
    from . import components as C
    return [(f"cb_motor_{k}_{i}" if k else f"cb_motor_{i}",
             wp.rotate((0, 0, 0), (1, 0, 0), 90.0).translate(motor_d(i)))
            for k, wp, _, _ in C.motor_parts()]


def _motor_pulley(i: int) -> cq.Workplane:
    m = motor_d(i)
    return _zc(D.PULLEY_FLANGE_OD, m[2] - D.PULLEY_W / 2, m[2] + D.PULLEY_W / 2, x=m[0], y=m[1])


# ── strings ──────────────────────────────────────────────────────────────────────────────────
CROWN_X = D.NUT_BLOCK_X                             # -615


def _wrap(c, r, a0, a1, y, g, n=6):
    """World points round a Y-axis circle (centre c=(x, z)) from angle a0 to a1 (rad, from +X)."""
    rr = r + g / 2
    return [(c[0] + rr * math.cos(a0 + (a1 - a0) * k / n), y,
             c[1] + rr * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]


def _string(i: int, t: float) -> cq.Workplane:
    g = D.STRING_GAUGE[i]
    y0, y1 = D.nut_y(i), D.string_y(i)
    zs = D.STRING_Z + g / 2
    st = stack(i, t)
    pts = [(CROWN_X - 30.0, y0, zs - 3.0), (CROWN_X, y0, zs), (BR_C[0], y1, zs)]
    if not far(i):
        pts += _wrap(BR_C, BR_R, math.pi / 2, -ALPHA, y1, g)[1:]
        a = dw((0.0, y1, st["ball"]))
    else:
        ic = dw(IDLER_C)
        b = math.radians(BREAK_DEG)
        pts += _wrap(BR_C, BR_R, math.pi / 2, math.pi / 2 - b, y1, g, 2)[1:]
        pts += _wrap((ic[0], ic[2]), BR_R, math.pi / 2 - b, -ALPHA, y1, g)
        a = dw((X_FAR, y1, st["ball"]))
    pts.append((a[0] + (g / 2) * CA, y1, a[2] - (g / 2) * SA))
    out = None
    for a, b in zip(pts, pts[1:]):
        if math.dist(a, b) < 1e-3:
            continue
        s = _seg(a, b, g)
        out = s if out is None else out.union(s)
    return out


def _axle_parts() -> list:
    from . import components as C
    ic = IDLER_C
    idl = cyl_y(D.BRIDGE_AXLE_D, CHEEK_Y[0][1] - CHEEK_Y[1][0], CHEEK_Y[1][0], x=ic[0], z=ic[2])
    for i in FAR_IDX:
        idl = idl.union(ball_bearing(D.BRG688_OD, D.BRG688_ID + 0.3, D.BRG688_W)
                        .rotate((0, 0, 0), (1, 0, 0), -90)
                        .translate((ic[0], D.string_y(i) - D.BRG688_W / 2, ic[2])))
    return [("cb_bridge_bearings", C.bridge_bearings()), ("cb_idler", to_w(idl))]


# ── ghosts: the instrument's limits ─────────────────────────────────────────────────────────
PICKUP_GHOST = ((-74.0, -21.0), (-51.9, 50.1), (-20.0, 7.97))   # top_plate OPEN_X, PK_MAX_YM..PK_YP,
                                                                # the Z-plate's foot..PK_TOP


def ghosts() -> list:
    (x0, x1), (y0, y1), (z0, z1) = PICKUP_GHOST
    g = [("ghost_pickup", box_at(x1 - x0, y1 - y0, z1 - z0, x=(x0 + x1) / 2, y=(y0 + y1) / 2,
                                 z=(z0 + z1) / 2))]
    dx0, dx1 = KEYHEAD_X, -21.0                      # the deck, keyhead to the changer
    g.append(("ghost_deck", box_at(dx1 - dx0, Y_HI - Y_LO, 9.6, x=(dx0 + dx1) / 2,
                                   y=(Y_HI + Y_LO) / 2, z=DECK_UNDER + 4.8)))
    for nm, (a, b) in (("ghost_wall_hi", (Y_HI, Y_HI + 20.0)), ("ghost_wall_lo", (Y_LO - 20.0, Y_LO))):
        g.append((nm, box_at(-KEYHEAD_X - 21.0, b - a, 9.6 - BODY_BOT_NOW, x=(KEYHEAD_X - 21.0) / 2,
                             y=(a + b) / 2, z=(9.6 + BODY_BOT_NOW) / 2)))
    g.append(("ghost_keyhead", box_at(40.0, Y_HI - Y_LO, 100.0, x=KEYHEAD_X - 20.0,
                                      y=(Y_HI + Y_LO) / 2, z=-40.0)))
    g.append(("ghost_bottom_now", box_at(-KEYHEAD_X + 60.0, Y_HI - Y_LO, 0.4, x=KEYHEAD_X / 2 + 30,
                                         y=(Y_HI + Y_LO) / 2, z=BODY_BOT_NOW - 0.2)))
    return g


# ── assembly ────────────────────────────────────────────────────────────────────────────────
def moving(t: float) -> list:
    """Everything that rides the nut, at travel fraction t, drive frame."""
    from . import components as C
    out = []
    for i in range(N):
        st = stack(i, t)
        x, y = x_of(i), D.string_y(i)
        out.append((f"cb_nut_{i}", C.nut().translate((x, y, st["flange_top"]))))
        out.append((f"cb_yoke_{i}", _yoke(i, t)))
        out.append((f"cb_ball_{i}", C.string_nut().translate((x, y, st["ball"]))))
        out += _spring_parts(i, t)
    return out


def static() -> list:
    """Everything that does not ride the nut, drive frame."""
    out = []
    for i in range(N):
        st = stack(i)
        x, y = x_of(i), D.string_y(i)
        out.append((f"cb_screw_{i}", _zc(D.SCREW_OD, st["screw_bot"], st["screw_top"], x=x, y=y)))
        out.append((f"cb_brg_{i}", ball_bearing(D.BRG688_OD, D.BRG688_ID, BRG_W)
                    .translate((x, y, st["bb"]))))
        out.append((f"cb_pulley_{i}", _pulley(i)))
        rx, ry = _rod_xy(i)
        z1 = _plate_z(row_of(i))[1]
        out.append((f"cb_rod_{i}", _zc(D.GUIDE_ROD_D, z1 - 2.4, z1 - 2.4 + D.GUIDE_ROD_L, x=rx, y=ry)))
        out.append((f"cb_belt_{i}", _belt(i)))
        out.append((f"cb_clampzone_{i}", clamp_envelope(i)))
        out += _motor(i)
        out.append((f"cb_mpulley_{i}", _motor_pulley(i)))
    for r in ("n", "f"):
        out.append((f"cb_plate_{r}", _plate(r)))
        out.append((f"cb_anchor_{r}", _anchor(r)))
    out.append(("cb_cheeks", _cheeks()))
    out.append(("cb_floor", _floor()))
    for p in PLANES:
        out.append((f"cb_rank_{p}", _rank_plate(p)))
    return out


SHOWN_GHOSTS = ("ghost_pickup", "ghost_bottom_now")   # the deck, walls and keyhead would hide it all


def assembly(t: float = T_OPEN, all_ghosts: bool = False) -> list:
    out = [(nm, to_w(w)) for nm, w in static() + moving(t)]
    out += _axle_parts()
    out += [(f"cb_string_{i}", _string(i, t)) for i in range(N)]
    out += [g for g in ghosts() if all_ghosts or g[0] in SHOWN_GHOSTS]
    return out


# ── colours (src.build._color_for asks here for every cb_ / ghost_ name) ───────────────────
# inner name (cb_ and EVERY trailing index group off, as _color_for strips them: cb_leg_0_3 ->
# leg; hence no part base may end in digits) -> a key of build._COLORS, or an RGB of its own.
# Motor parts (motor_<part>) and anything named as the instrument names it fall through to
# the table by their inner name.
_PRINTED = (0.39, 0.58, 0.93)                       # PETG-GF, as the bridge endplate
COLORS = {
    "nut": "nut", "ball": "string_nut", "screw": "leadscrew", "brg": "screw_bearing",
    "pulley": "screw_pulley", "mpulley": "motor_pulley", "rod": "guide_rod", "belt": "belt",
    "string": "string", "bridge_bearings": "bridge_bearings", "idler": "bridge_bearings",
    "yoke": _PRINTED,
    "clampzone": "belt_tensioner_half_a",            # where the clamp goes, not the clamp
    "plate_n": (0.30, 0.36, 0.42), "plate_f": (0.30, 0.36, 0.42),
    "cheeks": (0.42, 0.50, 0.62), "floor": (0.42, 0.50, 0.62),
    "rank_nA": (0.30, 0.33, 0.38), "rank_nB": (0.30, 0.33, 0.38),
    "rank_fA": (0.30, 0.33, 0.38), "rank_fB": (0.30, 0.33, 0.38),
    "anchor_n": (0.36, 0.30, 0.42), "anchor_f": (0.36, 0.30, 0.42),
    "leg": (0.45, 0.45, 0.48), "run": (0.45, 0.45, 0.48),   # 7x7 stainless rope
    "sheave": "screw_bearing",                       # 623VV
    "thimble": (0.75, 0.75, 0.78),
    "spring": "leg_latch_spring",                    # 9665K61 stainless
    "plug_a": (0.85, 0.45, 0.15), "plug_b": (0.85, 0.45, 0.15),
    "adjuster": "set_screw",                         # M4 x 40
    "ghost_pickup": "pickup", "ghost_bottom_now": (0.85, 0.20, 0.20),   # today's bottom: red
}


# What each part is made of, for the viewer (tools.web_materials asks here for cb_ names; a part
# with none is an error there, not plastic).
_MOTOR_FINISH = {}
MATERIAL = {
    "nut": "brass", "ball": "brass", "screw": "steel", "rod": "steel", "adjuster": "steel",
    "brg": "polished", "bridge_bearings": "polished", "idler": "polished", "sheave": "polished",
    "string": "polished", "pulley": "aluminium", "mpulley": "aluminium", "belt": "rubber",
    "leg": "stainless", "run": "stainless", "thimble": "stainless", "spring": "stainless",
    "clampzone": "pctg", "yoke": "petg-gf", "plug_a": "petg-gf", "plug_b": "petg-gf",
    "plate_n": "petg-gf", "plate_f": "petg-gf", "cheeks": "petg-gf", "floor": "petg-gf",
    "rank_nA": "petg-gf", "rank_nB": "petg-gf", "rank_fA": "petg-gf", "rank_fB": "petg-gf",
    "anchor_n": "petg-gf", "anchor_f": "petg-gf",
}


def material_of(base: str):
    inner = base[3:]
    if inner.startswith("motor"):
        if not _MOTOR_FINISH:
            from . import components as C
            _MOTOR_FINISH.update({k: fin for k, _, _, fin in C.motor_parts()})
        return _MOTOR_FINISH.get(inner[6:] if inner != "motor" else "")
    return MATERIAL.get(inner)


def color_of(base: str, table: dict):
    """RGB for a changer-bench part (its name with the trailing indices off), or None."""
    inner = base[3:] if base.startswith("cb_") else base
    v = COLORS.get(inner, inner)
    return v if isinstance(v, tuple) else table.get(v)


# ── the gate ────────────────────────────────────────────────────────────────────────────────
import re as _re

_IDX = _re.compile(r"_(\d+)$")


def _base(nm: str):
    m = _IDX.search(nm)
    return (nm[:m.start()], int(m.group(1))) if m else (nm, None)


# Designed contacts. Same-string pairs among these bases touch by design:
_SAME = {frozenset(p) for p in (
    ("cb_screw", "cb_nut"), ("cb_screw", "cb_pulley"), ("cb_screw", "cb_brg"), ("cb_screw", "cb_yoke"),
    ("cb_nut", "cb_yoke"), ("cb_nut", "cb_rod"), ("cb_nut", "cb_brg"), ("cb_ball", "cb_yoke"),
    ("cb_brg", "cb_pulley"), ("cb_pulley", "cb_belt"), ("cb_mpulley", "cb_belt"), ("cb_mpulley", "cb_motor"),
    ("cb_belt", "cb_clampzone"), ("cb_string", "cb_ball"), ("cb_string", "cb_yoke"),
    ("cb_leg_0", "cb_yoke"), ("cb_leg_1", "cb_yoke"), ("cb_leg_0", "cb_sheave_0"),
    ("cb_leg_1", "cb_sheave_1"), ("cb_run_0", "cb_sheave_0"), ("cb_run_1", "cb_sheave_1"),
    ("cb_run_0", "cb_thimble"), ("cb_run_1", "cb_thimble"), ("cb_thimble", "cb_plug_a"),
    ("cb_spring", "cb_plug_a"), ("cb_spring", "cb_plug_b"), ("cb_plug_b", "cb_adjuster"),
    ("cb_rod", "cb_yoke"), ("cb_motor",))}


def _gate_base(nm: str):
    b, i = _base(nm)
    return ("cb_motor" if b.startswith("cb_motor_") else b), i      # one motor, all its parts


def is_intended(a: str, b: str) -> bool:
    (ba, ia), (bb_, ib) = _gate_base(a), _gate_base(b)
    if ia is not None and ia == ib and frozenset((ba, bb_)) in _SAME:
        return True
    pair = {ba, bb_}
    if all(n.startswith("ghost_") for n in pair):
        return True
    if "cb_string" in pair and pair & {"cb_bridge_bearings", "cb_idler", "ghost_keyhead"}:
        return True
    plates = {"cb_plate_n", "cb_plate_f"}
    if "cb_cheeks" in pair and pair & (plates | {"cb_floor", "cb_bridge_bearings", "cb_idler",
                                                 "ghost_wall_hi"}):
        return True
    if pair & {"cb_brg", "cb_rod"} and pair & plates:
        return True
    if "cb_motor" in pair and pair & {f"cb_rank_{p}" for p in PLANES}:
        return True
    if "cb_adjuster" in pair and pair & {"cb_anchor_n", "cb_anchor_f"}:
        return True
    return False


def gate(ts=(0.0, T_OPEN, 1.0)) -> int:
    from cadkit import overlap_check as OC
    bad = 0
    for t in ts:
        comps = [(nm, cq.Compound.makeCompound(w.vals()) if len(w.vals()) > 1 else w.val())
                 for nm, w in assembly(t, all_ghosts=True) if nm != "ghost_bottom_now"]
        print(f"\n#### travel t = {t:.2f}")
        bad += OC.run(comps, is_intended)
    return bad


if __name__ == "__main__":
    import sys
    print(report())
    if "--gate" in sys.argv:
        sys.exit(gate())
