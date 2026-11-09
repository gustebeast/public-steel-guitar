"""DIRECT BENCH -- every string's screw driven straight off its own NEMA17, no belt (user, 2026-11-09).

A fit study like src.changer_bench: bought parts as they are, printed frames as plain blocks, the
instrument's limits (pickup, deck, side walls, keyhead) as GHOSTS the overlap gate measures. Held
from the instrument: the crown at NUT_BLOCK_X, the bridge bearings (STRING_Z), the strings fanning
from nut_y to string_y (9.5), Tr8x2 screws and the brass H-nut, CARRIAGE_TRAVEL, SERVO42D motors.

THE LAYOUT
 1. TWO BENDS. Every string leaves the bridge bearing straight DOWN on one line (x = 0), and turns
    -X under a SECOND 688 at its row's depth. The rows' axles all sit on x = -8 under the bridge
    axle: a string dropping to a lower row passes 4 mm outside every upper axle (its surface is at
    x = -4) and 7 mm beside the upper rows' bearings (they sit only at their own strings' Y).
 2. THREE ROWS, string i on row i % 3, DZ apart. A screw passes other strings' motors on its way
    to its own, so a neighbour closer than the motor's half-width + the screw in Y (9.5 and 19
    both are) has to be DZ >= 21.15 + 4 + clearance away in Z. Strings three apart (28.5) clear
    in Y, so three rows are the fewest.
 3. THE SCREW LIES ALONG -X and the nut rides it: the string pulls the nut +X, the screw is in
    TENSION into its two 688s at the motor end. A yoke on the nut's +X face holds the ball end on
    the screw axis (no couple, the X rig's yoke), a Ø3.5 rod through the nut's other ear keeps it
    from turning.
 4. THE SPRING WRAPS THE SCREW. An extension spring from a collar on the nut's boss back to one
    common ANCHOR WALL pulls the nut -X, on the axis. A fixed sleeve over the screw keeps the coils
    off the turning threads. It stops at the wall rather than running back to the motor: a Ø16
    spring passing the other motors would need ~30 of row pitch where the Ø8 screw needs 26.
 5. MOTORS COAXIAL, staggered along X in STATIONS. Two motors need different stations if their
    bodies overlap in YZ (closer than 44.7 in both Y and Z): rows 0 and 2 are 2 DZ apart, so they
    share; strings 57 apart on a row share. Four stations.
 6. EVERYTHING ON AXIS (user, 2026-11-09): every screw and motor runs straight along X under its
    own string, no yaw. String 1's motor then stands past today's +Y rail (42.75 + 21.15 > 54.75),
    and the rail MOVES OUT to clear it (RAIL_HI, "I don't mind the width change at the +y side").

    py -3.12 -m src.direct_bench          -> the layout report;   --gate -> the overlap gate
    view: scope src.direct_bench --attr assembly, `agent_sync.py view --solo`
"""

from __future__ import annotations

import math
import re as _re

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_x, cyl_y, ball_bearing

N = D.N_STRINGS
T_TRAVEL = D.CARRIAGE_TRAVEL                        # 8.35
T_OPEN = D.DL_OPEN / T_TRAVEL                       # open pitch, from the slack end

# ── rows ────────────────────────────────────────────────────────────────────────────────────
R = D.BRG688_OD / 2                                 # 8, every bend
BR_C = (D.BRIDGE_AXLE_X, D.BRIDGE_BEARING_Z)        # (-8, 8)
X_DROP = BR_C[0] + R                                # 0: every string's drop line
X_BEND = X_DROP - R                                 # -8: the bend axles, and the exit point
Z_TOP = -32.0                                       # row 0: the nut's ears (22) under the pickup (-20)
DZ = 26.4                                           # 21.15 + 4 + 0.5 + the gauges' half-diameters
LEVELS = 3


def level(i: int) -> int:
    return i % LEVELS


def z_level(k: int) -> float:
    """The string's exit height under row k's bend = the screw axis (less half the gauge)."""
    return Z_TOP - k * DZ


def za(i: int) -> float:
    """String i's screw axis: the string's centre leaving its bend."""
    return z_level(level(i)) - D.STRING_GAUGE[i] / 2


def y_of(i: int) -> float:
    return D.string_y(i)


# ── along the screw (x, before the yaw) ─────────────────────────────────────────────────────
YK_H = 20 * D.BEAD                                  # 16: yoke, flange face -> roof
YK_ROOF = 3 * D.BEAD                                # 2.4
YK_D = D.NUT_FLANGE_L                               # 22: round, as the nut's flange
X_YT0 = -26.0                                       # yoke roof at the slack end of travel
ROD_PLATE = (-24.0, -20.0)                          # the rods' plate (and the strings' holes)
# THE ROUND NUT (user, 2026-11-09): the common Tr8x2 brass flange nut, Ø22 x 3.5 flange with FOUR
# Ø3.5 holes on a Ø16 circle at 45 deg -- no flats needed here (a row's nuts are 28.5 apart, the
# next row's 28.1). Its holes do everything:
#   45 / 225 deg  two M3 x 12 SHCS from behind, through the collar's plate and the flange, into the
#                 yoke: they hold the yoke ON (the string pulls it +X, off the flange) and clamp the
#                 spring's collar, and a diagonal pair pulls on the axis.
#   135 deg       THE GUIDE ROD, through the yoke, the flange and the collar: the nut itself is the
#                 anti-rotation bearing, no arm. (135, not 315: the rod plate keeps 1.3 of web
#                 between the rod and the ball's window.)
NUT_PCD = 16.0
HOLE_ANG = {"m3": (45.0, 225.0), "rod": 135.0, "web": (0.0, 180.0)}


def at_ang(a: float, r: float = NUT_PCD / 2):
    """(dy, dz) of angle a (deg, from +Y toward +Z) at radius r."""
    return r * math.cos(math.radians(a)), r * math.sin(math.radians(a))


M3_HEAD = (5.5, 3.0)                                # SHCS head diameter, height
M3_L = 12.0
# RESTRINGING (user, 2026-11-09): a KEYHOLE in the yoke's roof. The ball end goes in through a
# hole KEY_DROP under the axis, then slides UP a slit only the string fits through, to sit on the
# axis behind the roof; the string's pull holds it there. The rod plate has a WINDOW in front of
# each keyhole the ball passes through (it was a Ø2 hole: the ball could never get past it).
KEY_D = D.STRING_NUT_D + 0.8                        # 4.8: the ball's way in
KEY_DROP = 5.0                                      # its centre under the axis: the slit's length
SLIT_W = 2.2                                        # string 10's 1.78 and room
WIN_HY = KEY_D / 2 + 1.4                            # 3.8: the plate window's half-width in Y
WIN_Z = (-(KEY_DROP + KEY_D / 2 + 1.2), 3.2)        # ...and its reach under / over the axis
# THE SPRING: 3/4 in OD stainless extension spring stock, cut to length (SKU TBD). Each end SCREWS
# ONTO A SEAT, its last coils wound over a plug of the spring's own inside diameter -- the way
# cut-to-length springs are meant to be ended -- so nothing is hooked off the axis.
#   NUT END: the COLLAR -- a plate clamped under the two M3 heads on the flange's back, two webs at
#            +-Y past the heads, and the seat on the far side of them, round the screw.
#   WALL END: the ANCHOR PLUG -- a seat on the wall's +X face, a neck through it, and a lug bar
#            behind it: put through with the lugs along Y (the wall's slot), turned a quarter to Z,
#            and the spring's own pull holds it there. The plug carries the SLEEVE over the screw.
SPRING_OD, SPRING_WIRE = 19.05, 2.0
SPRING_ID = SPRING_OD - 2 * SPRING_WIRE             # 15.05: the seats' diameter
ACTIVE_PITCH = 2.5                                  # the open coils between the grips, about
# HOW AN END HOLDS (user, 2026-11-09: "wrap the wire at the end around something"). Each seat is a
# THREADED POST: a helical groove the spring's last GRIP_TURNS coils are screwed into (the wire
# wraps the post, the load spread round the whole thread; its crests show between the coils).
# Then the wire's END is a TANG: bent straight back along the axis through a hole in the stop
# flange, and hooked over behind it -- so the spring cannot unscrew itself off the post.
GRIP_TURNS, GRIP_PITCH = 4, 3.0                     # the end coils in the post's thread
SEAT_GRIP = GRIP_TURNS * GRIP_PITCH                 # 12 of post under them
SEAT_L = SEAT_GRIP                                   # no more: the open coils cross past it
STOP_D, STOP_T = SPRING_OD + 2.0, 2.0               # the STOP FLANGE each spring end butts against
R_COIL = (SPRING_OD - SPRING_WIRE) / 2              # 8.525: the wire's centre
SEAT_D = 2 * R_COIL                                 # the post: its thread's crests at the wire's centre
GROOVE_D = SPRING_WIRE + 0.2
TANG_BACK, TANG_HOOK = SPRING_WIRE / 2 + STOP_T + 1.2, 2.6   # the tang: through, then over
PLUG_GAP = 3.0                                      # the plug's flange off the wall: the hook's room
SLEEVE_OD, SLEEVE_ID = 11.0, 9.0                    # over the screw, part of the anchor plug
ANCHOR = (-194.8, -190.0)                           # the anchor wall, x
LUG = (3.0, 22.0, 6.0)                              # the plug's lug bar: thick, long, wide
COLLAR_T = 3.0                                      # the collar's plate
PILLAR_D = 5.2                                      # the collar's two pillars past the M3 heads


def x_yt(t: float) -> float:
    return X_YT0 - t * T_TRAVEL


def x_ft(t: float) -> float:
    """Nut flange's +X face."""
    return x_yt(t) - YK_H


SCREW_TIP = x_ft(0.0) - D.SCREW_END_GAP             # under the flange face at the slack end


def x_collar(t: float):
    """The collar along x: plate (from, to), the heads' far face, the stop flange (from, to),
    the seat (from, to) -- the seat runs -X from the flange, the spring's end on the flange."""
    pb = x_ft(t) - D.NUT_FLANGE_T                   # the nut flange's back face
    heads = pb - COLLAR_T - M3_HEAD[1]
    f1 = heads - 0.5
    f0 = f1 - STOP_T
    return (pb - COLLAR_T, pb), heads, (f0, f1), (f0 - SEAT_L, f0)


def x_plug():
    """The anchor plug along x: the neck in the wall, the stop flange, the seat."""
    a0, a1 = ANCHOR
    f0 = a1 + PLUG_GAP
    return (a0, f0), (f0, f0 + STOP_T), (f0 + STOP_T, f0 + STOP_T + SEAT_L)


def spring_span(t: float):
    """The spring, x from..to: its end coils' centres a wire's radius off each flange face."""
    return x_plug()[1][1] + SPRING_WIRE / 2, x_collar(t)[2][0] - SPRING_WIRE / 2


# THE SLEEVE IS SPLIT 50/50 (user, 2026-11-09): half fixed on the anchor plug, half riding the
# collar, meeting 1.0 apart at full travel. The bare screw between them is the travel either way;
# this just keeps both 1-wall tubes stubby (no ~98 long one) and the gap mid-span.
SLEEVE_HALF = (x_collar(1.0)[3][0] - 1.0 - x_plug()[2][1]) / 2
SLEEVE_END = x_plug()[2][1] + SLEEVE_HALF            # the plug's half, from its post
# the rod's -X end: 0.5 short of the stop flange's back at the slack end (the spring starts
# there), so at full travel it is still 3.15 into the 3.5 flange
ROD_END = x_collar(0.0)[2][0] + 0.5
ROD_L = round(ROD_PLATE[1] - 0.3 - ROD_END, 1)     # ...and 0.3 inside the plate's +X face: a Ø3.5
                                                    # ground rod, ~33 long (length still to source)

# ── motors and stations ─────────────────────────────────────────────────────────────────────
M_HALF = D.MOTOR_SQ / 2                             # 21.15
M_BACK = 60.7                                       # pulley plane -> the driver's back
M_FACE = 7.5                                        # pulley plane -> the faceplate
PLUG = (21.15, 29.9, 6.2, 44.5, 38.5)               # coil plug + leads: off the axis from..to,
                                                    # half-width, and its x range (back of ref)
COUPLER = (19.0, -2.0, 21.0)                        # Ø, x from..to past the pulley plane
BLOCK = (24.0, 22.0, 36.0)                          # square, x from..to: two 688s
PLATE_T = 4.0
STATION_GAP = 1.3
STATION_P = M_BACK + BLOCK[2] + STATION_GAP         # 98.0
X_REF0 = ANCHOR[0] - LUG[0] - 1.0 - BLOCK[2]        # the nearest station: past the plug's lugs

# station of each string (nearest 0): rows 0 and 2 share; 57 apart on a row share. The ORDER is
# the one (of the 24) where every motor's coil plug finds a side no passing screw, station-mate,
# rail or deck takes (searched; the middle row's lone string 5 has to be the farthest).
STATION = {1: 0, 7: 0, 0: 1, 6: 1, 2: 1, 8: 1, 3: 2, 9: 2, 5: 2, 4: 3}


def x_ref(i: int) -> float:
    return X_REF0 - STATION[i] * STATION_P


# ── the rails ───────────────────────────────────────────────────────────────────────────────
Y_LO, Y_HI = -116.35, 54.75                         # today's rails' inner faces
KEYHEAD_X = D.KEYHEAD_INBOARD_X                     # -607.8
DECK_UNDER = -3.2
WALL_CLR = 0.4


THETA = 0.0                                         # no yaw: everything on its string's axis


def yaw(wp: cq.Workplane, i: int) -> cq.Workplane:
    """Swing a string's drive part by THETA about its exit point (0: as drawn)."""
    if THETA == 0.0:
        return wp
    return wp.rotate((X_BEND, y_of(i), 0), (X_BEND, y_of(i), 1), math.degrees(THETA))


def yaw_pt(p, i: int):
    x, y, z = p
    dx, dy = x - X_BEND, y - y_of(i)
    c, s = math.cos(THETA), math.sin(THETA)
    return (X_BEND + dx * c - dy * s, y_of(i) + dx * s + dy * c, z)


# ── plug directions: searched so no passing screw, no station-mate, no deck or floor meets it ─
DIRS = {0: (0.0, 1.0), 270: (1.0, 0.0), 90: (-1.0, 0.0), 180: (0.0, -1.0)}   # phi -> (dy, dz)


def _plug_box(i: int, phi: int):
    dy, dz = DIRS[phi]
    a, b, hw = PLUG[0], PLUG[1], PLUG[2]
    y, z = y_of(i), za(i)
    if dy:
        ys = sorted((y + dy * a, y + dy * b))
        return (ys[0], ys[1], z - hw, z + hw)
    zs = sorted((z + dz * a, z + dz * b))
    return (y - hw, y + hw, zs[0], zs[1])


def _hits(b, c):
    return b[0] < c[1] and c[0] < b[1] and b[2] < c[3] and c[2] < b[3]


def _body(j: int):
    return (y_of(j) - M_HALF, y_of(j) + M_HALF, za(j) - M_HALF, za(j) + M_HALF)


def _plug_dirs() -> dict:
    floor = min(za(i) for i in range(N)) - M_HALF
    out = {}
    for i in sorted(range(N), key=lambda k: STATION[k]):
        # a +Y plug past today's rail would widen it further: try it last there
        order = (90, 0, 180, 270) if y_of(i) + PLUG[1] > Y_HI else (90, 270, 0, 180)
        for phi in order:
            b = _plug_box(i, phi)
            if b[3] > DECK_UNDER - 0.5 or b[2] < floor:
                continue
            if b[0] < Y_LO + WALL_CLR:               # the -Y rail stays; the +Y one moves out
                continue
            bad = False
            for j in range(N):
                if j == i:
                    continue
                if STATION[j] > STATION[i]:           # j's screw passes i's motor
                    r = D.SCREW_OD / 2 + 0.3
                    if _hits(b, (y_of(j) - r, y_of(j) + r, za(j) - r, za(j) + r)):
                        bad = True
                elif STATION[j] == STATION[i]:
                    if _hits(b, _body(j)) or (j in out and _hits(b, _plug_box(j, out[j]))):
                        bad = True
            if not bad:
                out[i] = phi
                break
        else:
            raise ValueError(f"no plug direction for string {i + 1}")
    return out


PLUG_DIR = _plug_dirs()


def _rail_hi() -> float:
    """Where the +Y rail's inner face has to be: past every motor and plug, and never in."""
    far = max(max(y_of(i) + M_HALF, _plug_box(i, PLUG_DIR[i])[1]) for i in range(N))
    return max(Y_HI, far + WALL_CLR)


RAIL_HI = _rail_hi()


# ── report ──────────────────────────────────────────────────────────────────────────────────
def report() -> str:
    out = [f"rows z (axis): " + "  ".join(f"{k}: {z_level(k):.1f}" for k in range(LEVELS)) +
           f"   DZ {DZ}",
           f"+Y rail inner face {RAIL_HI:.2f} (today {Y_HI}): {RAIL_HI - Y_HI:+.2f} wider, all on axis",
           f"stations x (pulley plane): " + "  ".join(f"{X_REF0 - s * STATION_P:.1f}"
                                                      for s in range(4)) + f"  pitch {STATION_P}",
           "string row station  motor (x, y, z)            plug  screw length  spring at slack/full"]
    for i in range(N):
        m = yaw_pt((x_ref(i), y_of(i), za(i)), i)
        sl = SCREW_TIP - (x_ref(i) + 11.0)
        s0 = spring_span(0)[1] - spring_span(0)[0]
        s1 = spring_span(1)[1] - spring_span(1)[0]
        dirn = {0: "+Z", 90: "-Y", 180: "-Z", 270: "+Y"}[PLUG_DIR[i]]
        out.append(f"  {i + 1:2d}   {level(i)}     {STATION[i]}     ({m[0]:7.1f}, {m[1]:6.1f}, {m[2]:6.1f})"
                   f"   {dirn}   {sl:6.1f}        {s0:5.1f} / {s1:5.1f}")
    low = min(za(i) for i in range(N)) - M_HALF
    far = min(x_ref(i) for i in range(N)) - M_BACK
    out.append(f"deepest: the lowest motor's bottom z {low:.1f}  (today's bottom -81.8)")
    out.append(f"farthest motor back x {far:.1f}  (keyhead {KEYHEAD_X})")
    return "\n".join(out)


# ── geometry ────────────────────────────────────────────────────────────────────────────────
def _seg(a, b, d):
    va, vb = cq.Vector(*a), cq.Vector(*b)
    v = vb - va
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(d / 2, v.Length, va, v.normalized()))


def _tube_x(od, idd, x0, x1, y, z):
    return cyl_x(od, x1 - x0, x0, y=y, z=z).cut(cyl_x(idd, x1 - x0 + 2, x0 - 1, y=y, z=z))


def _yoke(i: int, t: float) -> cq.Workplane:
    y, z = y_of(i), za(i)
    ft, yt = x_ft(t), x_yt(t)
    out = cyl_x(YK_D, YK_H, ft, y=y, z=z)
    out = out.cut(cyl_x(D.SCREW_OD + 0.8, yt - YK_ROOF - ft + 1, ft - 1, y=y, z=z))   # tip + ball
    out = out.cut(cyl_x(D.NUT_LIP_D + 0.4, D.NUT_LIP_L + 1.3, ft - 1, y=y, z=z))      # lip register
    ry, rz = rod_yz(i)
    out = out.cut(cyl_x(D.GUIDE_ROD_D + 0.4, YK_H + 2, ft - 1, y=ry, z=rz))           # the rod
    for a in HOLE_ANG["m3"]:                                                          # the M3s bite
        dy, dz = at_ang(a)
        out = out.cut(cyl_x(2.5, M3_L - COLLAR_T - D.NUT_FLANGE_T + 1.0, ft - 1, y=y + dy, z=z + dz))
    # the keyhole: the ball's hole KEY_DROP down, the slit up to the axis, and behind the roof
    # a pocket the ball slides up in (its 3 along the axis, Ø4 across)
    rx0 = yt - YK_ROOF
    out = out.cut(cyl_x(KEY_D, YK_ROOF + 2, rx0 - 1, y=y, z=z - KEY_DROP))
    out = out.cut(box_at(YK_ROOF + 2, SLIT_W, KEY_DROP, x=rx0 + YK_ROOF / 2, y=y, z=z - KEY_DROP / 2))
    out = out.cut(cyl_x(SLIT_W, YK_ROOF + 2, rx0 - 1, y=y, z=z))
    pk = D.STRING_NUT_L + 0.6
    out = out.cut(box_at(pk, KEY_D, KEY_DROP + KEY_D / 2, x=rx0 - pk / 2, y=y,
                         z=z - (KEY_DROP + KEY_D / 2) / 2))
    return out


def rod_yz(i: int):
    dy, dz = at_ang(HOLE_ANG["rod"])
    return y_of(i) + dy, za(i) + dz


def _collar(i: int, t: float) -> cq.Workplane:
    y, z = y_of(i), za(i)
    (p0, p1), heads, (f0, f1), (s0, s1) = x_collar(t)
    out = cyl_x(D.NUT_FLANGE_L, p1 - p0, p0, y=y, z=z)                             # the plate
    for a in HOLE_ANG["web"]:                        # pillars past the M3 heads to the flange
        dy, dz = at_ang(a)
        out = out.union(cyl_x(PILLAR_D, p0 - f1 + 0.5, f1 - 0.5, y=y + dy, z=z + dz))
    out = out.union(cyl_x(STOP_D, f1 - f0, f0, y=y, z=z))                          # stop flange
    x0, x1 = spring_span(t)                                                         # the post:
    out = out.union(_post(i, x0, x1 - x0 - SEAT_GRIP, D.NUT_BOSS_D + 0.4))          # threaded
    out = out.cut(cyl_x(D.NUT_BOSS_D + 0.4, 60, s0 - 1, y=y, z=z))                  # boss, screw
    out = out.union(_tube_x(13.0, SLEEVE_ID, s0, s0 + 3.0, y, z))                   # post's floor,
    out = out.union(_tube_x(SLEEVE_OD, SLEEVE_ID, s0 - SLEEVE_HALF, s0 + 1.0, y, z))  # sleeve half
    out = out.cut(_tang_hole(i, f0))
    for a in HOLE_ANG["m3"]:                         # the M3s, and the key's way to them (before
        dy, dz = at_ang(a)                           # the spring goes on)
        out = out.cut(cyl_x(3.4, 30, f0 - 1, y=y + dy, z=z + dz))
    ry, rz = rod_yz(i)
    return out.cut(cyl_x(D.GUIDE_ROD_D + 0.4, 30, f0 - 1, y=ry, z=rz))             # the rod


def _m3s(i: int, t: float) -> cq.Workplane:
    y, z = y_of(i), za(i)
    (p0, _), heads, _, _ = x_collar(t)
    out = None
    for a in HOLE_ANG["m3"]:
        dy, dz = at_ang(a)
        sc = (cyl_x(M3_HEAD[0], M3_HEAD[1], heads, y=y + dy, z=z + dz)
              .union(cyl_x(3.0, M3_L, p0, y=y + dy, z=z + dz)))
        out = sc if out is None else out.union(sc)
    return out


COILS = True                                        # False: the spring as its tube (the gate)


def _helix(z0: float, pitch: float, h: float, d: float) -> cq.Workplane:
    """A wire of diameter d round R_COIL from local z0 for h, starting at angle 0 (local +x), in
    the SPRING'S FRAME: local z along the screw (-> world +X), placed by _in_spring."""
    hx = cq.Wire.makeHelix(pitch=pitch, height=h, radius=R_COIL)
    return (cq.Workplane("XZ").center(R_COIL, 0).circle(d / 2)
            .sweep(cq.Workplane("XY").add(hx), isFrenet=True).translate((0, 0, z0)))


def _in_spring(wp: cq.Workplane, i: int, x0: float) -> cq.Workplane:
    """Local spring frame -> the string's (local +x, angle 0, lands on world -Z)."""
    return wp.rotate((0, 0, 0), (0, 1, 0), 90).translate((x0, y_of(i), za(i)))


def _screw(i: int, x0: float, x1: float) -> cq.Workplane:
    """The leadscrew from x0 to x1 along +X: the instrument's own threaded Tr8x2 rod
    (components.screw, cached per length). Its crests are the plain cylinder's surface, so the
    gate (COILS False) checks that cylinder instead of cutting the helix."""
    y, z = y_of(i), za(i)
    if not COILS:
        return cyl_x(D.SCREW_OD, x1 - x0, x0, y=y, z=z)
    from . import components as C
    return C.screw(round(x1 - x0, 3)).rotate((0, 0, 0), (0, 1, 0), 90).translate((x0, y, z))


def _spring(i: int, t: float) -> cq.Workplane:
    x0, x1 = spring_span(t)
    if not COILS:
        return _tube_x(SPRING_OD, SPRING_ID, x0, x1, y_of(i), za(i))
    L = x1 - x0
    act = L - 2 * SEAT_GRIP
    k = max(1, round(act / ACTIVE_PITCH))           # whole turns: every piece starts at angle 0
    pieces = [_helix(0.0, GRIP_PITCH, SEAT_GRIP, SPRING_WIRE),
              _helix(SEAT_GRIP, act / k, act, SPRING_WIRE),
              _helix(SEAT_GRIP + act, GRIP_PITCH, SEAT_GRIP, SPRING_WIRE)]
    # the tangs: from each end coil (angle 0) straight back through its flange, then hooked out
    w = SPRING_WIRE
    for zc, sgn in ((0.0, -1), (L, 1)):
        zb = zc + sgn * TANG_BACK
        pieces.append(_seg((R_COIL, 0, zc), (R_COIL, 0, zb), w)
                      .union(_seg((R_COIL, 0, zb), (R_COIL + TANG_HOOK, 0, zb), w))
                      .union(cq.Workplane("XY").add(cq.Solid.makeSphere(w / 2))
                             .translate((R_COIL, 0, zb))))
    # ONE compound: the view and the export take a part's first solid only
    one = cq.Workplane("XY").add(cq.Compound.makeCompound([v for p_ in pieces for v in p_.vals()]))
    return _in_spring(one, i, x0)


def _post(i: int, x0: float, z0: float, bore: float) -> cq.Workplane:
    """A threaded post SEAT_L long from local z0 (spring frame at x0), its groove matching the
    grip coils (angle 0 at z0, whole turns), bored for what passes through it."""
    # the post reaches its flange at one end, and stops half a pitch short of the open coils at
    # the other (where the pitch changes, the next turn would ride over its last crest)
    lo = -SPRING_WIRE / 2 if z0 <= 0 else GRIP_PITCH / 2
    hi = SPRING_WIRE / 2 if z0 > 0 else -GRIP_PITCH / 2
    post = cq.Workplane("XY").add(cq.Solid.makeCylinder(SEAT_D / 2, SEAT_L - lo + hi,
                                                        cq.Vector(0, 0, z0 + lo)))
    post = post.cut(_helix(z0, GRIP_PITCH, SEAT_L, GROOVE_D))
    post = post.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(bore / 2, SEAT_L + 2,
                                                                 cq.Vector(0, 0, z0 - 1))))
    return _in_spring(post, i, x0)


def _tang_hole(i: int, x_from: float) -> cq.Workplane:
    return cyl_x(SPRING_WIRE + 0.4, STOP_T + 2, x_from - 1, y=y_of(i), z=za(i) - R_COIL)


def _anchor_plug(i: int) -> cq.Workplane:
    y, z = y_of(i), za(i)
    (a0, a1), (f0, f1), (s0, s1) = x_plug()
    out = cyl_x(SPRING_ID, f0 - a0, a0, y=y, z=z)                                   # neck
    out = out.union(cyl_x(STOP_D, f1 - f0, f0, y=y, z=z))                           # stop flange
    out = out.union(box_at(LUG[0], LUG[2], LUG[1], x=a0 - LUG[0] / 2, y=y, z=z))      # locked: lugs in Z
    out = out.union(cyl_x(SLEEVE_OD, SLEEVE_END - s1, s1, y=y, z=z))
    out = out.cut(cyl_x(SLEEVE_ID, SLEEVE_END - a0 + 2 * LUG[0], a0 - LUG[0] - 1, y=y, z=z))
    out = out.union(_post(i, spring_span(0.0)[0], 0.0, SLEEVE_ID))                  # threaded post
    return out.cut(_tang_hole(i, f0))


def _nut(i: int, t: float) -> cq.Workplane:
    """The round Tr8x2 flange nut, axis along -X: lip on the flange's +X face, boss behind."""
    y, z, ft = y_of(i), za(i), x_ft(t)
    out = cyl_x(D.NUT_FLANGE_L, D.NUT_FLANGE_T, ft - D.NUT_FLANGE_T, y=y, z=z)
    out = out.union(cyl_x(D.NUT_LIP_D, D.NUT_LIP_L, ft, y=y, z=z))
    out = out.union(cyl_x(D.NUT_BOSS_D, D.NUT_H - D.NUT_FLANGE_T, ft - D.NUT_H, y=y, z=z))
    out = out.cut(cyl_x(D.SCREW_OD, 30, ft - 20, y=y, z=z))
    for a in (45.0, 135.0, 225.0, 315.0):
        dy, dz = at_ang(a)
        out = out.cut(cyl_x(3.5, 10, ft - 5, y=y + dy, z=z + dz))
    return out


def _ball_x(t: float) -> float:
    return x_yt(t) - YK_ROOF - D.STRING_NUT_L / 2


MOTOR_FINISH = {}                                   # motor part -> its finish (motor_parts)


def _motor(i: int) -> list:
    from . import components as C
    out = []
    for k, wp, _, fin in C.motor_parts():
        MOTOR_FINISH[k] = fin
        w = (wp.rotate((0, 0, 0), (0, 1, 0), PLUG_DIR[i]).rotate((0, 0, 0), (0, 0, 1), -90)
             .translate((x_ref(i), y_of(i), za(i))))
        out.append((f"db_motor_{k}_{i}" if k else f"db_motor_{i}", w))
    return out


def _bend_parts() -> list:
    """Each row's axle (cheek to cheek) and its strings' 688s, plus the bridge's own bearings."""
    from . import components as C
    out = [("db_bridge_bearings", C.bridge_bearings())]
    for k in range(LEVELS):
        zc = z_level(k) + R
        out.append((f"db_bend_axle_r{'abc'[k]}",
                    cyl_y(D.BRIDGE_AXLE_D, 2 * CHEEK_Y[1], -CHEEK_Y[1], x=X_BEND, z=zc)))
    for i in range(N):
        out.append((f"db_bend_brg_{i}", ball_bearing(D.BRG688_OD, D.BRG688_ID, D.BRG688_W)
                    .rotate((0, 0, 0), (1, 0, 0), -90)
                    .translate((X_BEND, y_of(i) - D.BRG688_W / 2, z_level(level(i)) + R))))
    return out


CHEEK_Y = (48.6, 54.6)                              # each cheek, |y| from..to
CHEEK_X = (-20.0, 2.0)
CHEEK_Z = (z_level(LEVELS - 1) - 12.0, -12.0)


def _cheeks() -> cq.Workplane:
    (x0, x1), (z0, z1), (a, b) = CHEEK_X, CHEEK_Z, CHEEK_Y
    out = None
    for s in (1, -1):
        c = box_at(x1 - x0, b - a, z1 - z0, x=(x0 + x1) / 2, y=s * (a + b) / 2, z=(z0 + z1) / 2)
        out = c if out is None else out.union(c)
    for k in range(LEVELS):
        out = out.cut(cyl_y(D.BRIDGE_AXLE_D + 0.2, 200, -100, x=X_BEND, z=z_level(k) + R))
    return out


def _plate_yz(x0, x1, z0, z1) -> cq.Workplane:
    return box_at(x1 - x0, 2 * CHEEK_Y[0], z1 - z0, x=(x0 + x1) / 2, y=0, z=(z0 + z1) / 2)


def _rod_plate() -> cq.Workplane:
    x0, x1 = ROD_PLATE
    w = _plate_yz(x0, x1, CHEEK_Z[0], -20.5)
    for i in range(N):
        lo, hi = WIN_Z                               # the window the ball passes through
        w = w.cut(yaw(box_at(10, 2 * WIN_HY, hi - lo, x=(x0 + x1) / 2, y=y_of(i),
                             z=za(i) + (lo + hi) / 2), i))
        ry, rz = rod_yz(i)
        w = w.cut(yaw(cyl_x(D.GUIDE_ROD_D, 10, x0 - 3, y=ry, z=rz), i))
    return w


def _anchor() -> cq.Workplane:
    x0, x1 = ANCHOR
    w = _plate_yz(x0, x1, CHEEK_Z[0], -20.5)
    for i in range(N):                               # the plug's way through: round, and the
        y, z = y_of(i), za(i)                        # lugs' slot along Y (turned to Z, they lock)
        w = w.cut(yaw(cyl_x(SPRING_ID + 0.4, 20, x0 - 10, y=y, z=z), i))
        w = w.cut(yaw(box_at(20, LUG[1] + 0.8, LUG[2] + 0.8, x=(x0 + x1) / 2, y=y, z=z), i))
    return w


def _string(i: int, t: float) -> cq.Workplane:
    g = D.STRING_GAUGE[i]
    y0, y1 = D.nut_y(i), y_of(i)
    zs = D.STRING_Z + g / 2
    rr = R + g / 2
    pts = [(D.NUT_BLOCK_X - 30.0, y0, zs - 3.0), (D.NUT_BLOCK_X, y0, zs), (BR_C[0], y1, zs)]
    for k in range(1, 7):                            # over the bridge, 90 -> 0 deg
        a = math.pi / 2 * (1 - k / 6)
        pts.append((BR_C[0] + rr * math.cos(a), y1, BR_C[1] + rr * math.sin(a)))
    zc = z_level(level(i)) + R
    for k in range(0, 7):                            # round the bend, 0 -> -90 deg
        a = -math.pi / 2 * k / 6
        pts.append((X_BEND + rr * math.cos(a), y1, zc + rr * math.sin(a)))
    pts.append(yaw_pt((_ball_x(t), y1, za(i)), i))
    out = None
    for a, b in zip(pts, pts[1:]):
        if math.dist(a, b) > 1e-3:
            s = _seg(a, b, g)
            out = s if out is None else out.union(s)
    return out


def string_parts(i: int, t: float) -> list:
    """String i's drive, drawn along -X at (y_of(i), za(i)), yawed into place."""
    y, z = y_of(i), za(i)
    xr = x_ref(i)
    ft = x_ft(t)
    parts = [
        ("db_yoke", _yoke(i, t)),
        ("db_ball", cyl_x(D.STRING_NUT_D, D.STRING_NUT_L, _ball_x(t) - D.STRING_NUT_L / 2, y=y, z=z)),
        ("db_nut", _nut(i, t)),
        ("db_collar", _collar(i, t)),
        ("db_m3", _m3s(i, t)),
        ("db_spring", _spring(i, t)),
        ("db_plug", _anchor_plug(i)),
        ("db_rod", cyl_x(D.GUIDE_ROD_D, ROD_L, ROD_END, y=rod_yz(i)[0], z=rod_yz(i)[1])),
        ("db_screw", _screw(i, xr + 11.0, SCREW_TIP)),
        ("db_coupler", cyl_x(COUPLER[0], COUPLER[2] - COUPLER[1], xr + COUPLER[1], y=y, z=z)),
        ("db_block", box_at(BLOCK[2] - BLOCK[1], BLOCK[0], BLOCK[0], x=xr + (BLOCK[1] + BLOCK[2]) / 2,
                            y=y, z=z).cut(cyl_x(D.BRG688_OD, 20, xr + BLOCK[1] + 2, y=y, z=z))
         .cut(cyl_x(D.SCREW_OD + 1.0, 30, xr + BLOCK[1] - 1, y=y, z=z))),
        ("db_brg", ball_bearing(D.BRG688_OD, D.BRG688_ID, 2 * D.BRG688_W)
         .rotate((0, 0, 0), (0, 1, 0), 90).translate((xr + BLOCK[1] + 3, y, z))),
        ("db_mplate", box_at(PLATE_T, D.MOTOR_SQ, D.MOTOR_SQ, x=xr - M_FACE + PLATE_T / 2, y=y, z=z)
         .cut(cyl_x(D.NEMA17_PILOT_D + 0.6, 10, xr - M_FACE - 1, y=y, z=z))),
    ]
    out = [(f"{nm}_{i}", yaw(w, i)) for nm, w in parts]
    out += [(nm, yaw(w, i)) for nm, w in _motor(i)]
    out.append((f"db_string_{i}", _string(i, t)))
    return out


def assembly(t: float = T_OPEN, all_ghosts: bool = False) -> list:
    from .changer_bench import ghosts as _ghosts

    def ghosts():
        return _ghosts(y_hi=RAIL_HI)
    out = []
    for i in range(N):
        out += string_parts(i, t)
    out += _bend_parts()
    out += [("db_cheeks", _cheeks()), ("db_rod_plate", _rod_plate()), ("db_anchor", _anchor())]
    out = [(nm, _made(nm, w)) for nm, w in out]
    show = ("ghost_pickup", "ghost_bottom_now")
    out += [g for g in ghosts() if all_ghosts or g[0] in show]
    return out


# What each part is made of, for the viewer's shine (cadkit.web.finishes.made_of): printed
# frames in the instrument's PETG-GF, the bought parts as they are.
MATERIAL = {
    "yoke": "petg-gf", "collar": "petg-gf", "block": "petg-gf", "mplate": "petg-gf",
    "cheeks": "petg-gf", "rod_plate": "petg-gf", "anchor": "petg-gf",
    "nut": "brass", "ball": "brass", "screw": "steel", "rod": "steel", "string": "polished",
    "brg": "polished", "bend_brg": "polished", "bridge_bearings": "polished",
    "bend_axle_ra": "steel", "bend_axle_rb": "steel", "bend_axle_rc": "steel",
    "spring": "stainless", "plug": "petg-gf", "m3": "steel", "coupler": "aluminium",
}


def material_of(base: str):
    """The material of a direct-bench part (its name, indices off), or None."""
    inner = base[3:]
    if inner.startswith("motor"):
        if not MOTOR_FINISH:
            from . import components as C
            MOTOR_FINISH.update({k: fin for k, _, _, fin in C.motor_parts()})
        return MOTOR_FINISH.get(inner[6:] if inner != "motor" else "")
    return MATERIAL.get(inner)


def _made(nm: str, w):
    from cadkit.web.finishes import made_of
    m = material_of(_re.sub(r"(_\d+)+$", "", nm))
    return made_of(w, m) if m else w


# ── colours (src.build._color_for asks here for db_ names) ──────────────────────────────────
# inner name (db_ and EVERY trailing index group off) -> a key of build._COLORS, or an RGB.
COLORS = {
    "nut": "nut", "ball": "string_nut", "screw": "leadscrew", "brg": "screw_bearing",
    "string": "string", "bridge_bearings": "bridge_bearings", "rod": "guide_rod",
    "bend_brg": "bridge_bearings", "bend_axle_ra": "leadscrew", "bend_axle_rb": "leadscrew",
    "bend_axle_rc": "leadscrew",
    "yoke": (0.39, 0.58, 0.93), "collar": (0.85, 0.45, 0.15),
    "spring": "leg_latch_spring", "plug": (0.85, 0.45, 0.15), "m3": "set_screw",
    "coupler": (0.70, 0.72, 0.76), "block": (0.30, 0.36, 0.42), "mplate": (0.30, 0.33, 0.38),
    "cheeks": (0.42, 0.50, 0.62), "rod_plate": (0.42, 0.50, 0.62), "anchor": (0.36, 0.30, 0.42),
}


def color_of(base: str, table: dict):
    inner = base[3:] if base.startswith("db_") else base
    v = COLORS.get(inner, inner)
    return v if isinstance(v, tuple) else table.get(v)


# ── the gate ────────────────────────────────────────────────────────────────────────────────
import re as _re

_IDX = _re.compile(r"_(\d+)$")


def _base(nm: str):
    m = _IDX.search(nm)
    b, i = (nm[:m.start()], int(m.group(1))) if m else (nm, None)
    return ("db_motor" if b.startswith("db_motor") else b), i


_SAME = {frozenset(p) for p in (
    ("db_screw", "db_nut"), ("db_screw", "db_brg"), ("db_screw", "db_coupler"),
    ("db_nut", "db_yoke"), ("db_nut", "db_collar"), ("db_yoke", "db_rod"), ("db_nut", "db_rod"),
    ("db_m3", "db_collar"), ("db_m3", "db_nut"), ("db_m3", "db_yoke"), ("db_spring", "db_plug"),
    ("db_yoke", "db_ball"), ("db_string", "db_ball"), ("db_string", "db_yoke"),
    ("db_collar", "db_spring"), ("db_brg", "db_block"), ("db_coupler", "db_motor"),
    ("db_motor", "db_mplate"), ("db_motor",), ("db_coupler", "db_block"))}


def is_intended(a: str, b: str) -> bool:
    (ba, ia), (bb_, ib) = _base(a), _base(b)
    if ia is not None and ia == ib and frozenset((ba, bb_)) in _SAME:
        return True
    pair = {ba, bb_}
    if all(n.startswith("ghost_") for n in pair):
        return True
    bends = {"db_bend_axle_ra", "db_bend_axle_rb", "db_bend_axle_rc", "db_bend_brg"}
    if "db_string" in pair and pair & (bends | {"db_bridge_bearings", "ghost_keyhead"}):
        return True
    if "db_cheeks" in pair and pair & (bends | {"db_rod_plate", "db_anchor"}):
        return True
    if "db_bend_brg" in pair and pair & bends - {"db_bend_brg"}:      # each 688 on its axle
        return True
    if "db_rod" in pair and "db_rod_plate" in pair:
        return True
    if "db_anchor" in pair and "db_plug" in pair:
        return True
    return False


def gate(ts=(0.0, T_OPEN, 1.0)) -> int:
    """Each spring checked as its whole tube, OD to ID (stricter than the coils, and a helix
    against its neighbours costs minutes)."""
    global COILS
    from cadkit import overlap_check as OC
    COILS = False
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
