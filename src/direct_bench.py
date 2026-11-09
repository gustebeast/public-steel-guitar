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
 6. THE DRIVE YAWS THETA in plan (every screw the same angle, -Y going -X). String 1's motor at
    its own Y would sit through the +Y rail (42.75 + 21.15 > 54.75); a common angle keeps every
    relative position, so the rules above still hold, and the bend bearings take a ~1 deg fleet.

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
YK_W = 14 * D.BEAD                                  # 11.2 across Y (the nut's 10.5 flats)
YK_TALL = D.NUT_FLANGE_L                            # 22 in Z, as the flange
X_YT0 = -26.0                                       # yoke roof at the slack end of travel
ROD_PLATE = (-24.0, -20.0)                          # the rods' plate (and the strings' holes)
ROD_DZ = -D.NUT_HOLE_DX                             # the rod rides the ear at -Z
COLLAR_L = 2.0                                      # the spring's collar, on the boss's end
SPRING_OD, SPRING_ID = 15.9, 12.7                   # 5/8 in stainless extension spring (SKU TBD)
SLEEVE_OD, SLEEVE_ID = 11.0, 9.0                    # fixed sleeve over the screw
ANCHOR = (-194.8, -190.0)                           # the anchor wall, x


def x_yt(t: float) -> float:
    return X_YT0 - t * T_TRAVEL


def x_ft(t: float) -> float:
    """Nut flange's +X face."""
    return x_yt(t) - YK_H


SCREW_TIP = x_ft(0.0) - D.SCREW_END_GAP             # under the flange face at the slack end
ROD_END = x_ft(1.0) - D.NUT_FLANGE_T                # the ear's back face at full travel
SLEEVE_END = x_ft(1.0) - D.NUT_H - COLLAR_L - 1.0   # clear of the collar at full travel

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
X_REF0 = ANCHOR[0] - 1.0 - BLOCK[2]                 # the nearest station's pulley plane

# station of each string (nearest 0): rows 0 and 2 share; 57 apart on a row share. The ORDER is
# the one (of the 24) where every motor's coil plug finds a side no passing screw, station-mate,
# rail or deck takes (searched; the middle row's lone string 5 has to be the farthest).
STATION = {1: 0, 7: 0, 0: 1, 6: 1, 2: 1, 8: 1, 3: 2, 9: 2, 5: 2, 4: 3}


def x_ref(i: int) -> float:
    return X_REF0 - STATION[i] * STATION_P


# ── the yaw ─────────────────────────────────────────────────────────────────────────────────
Y_LO, Y_HI = -116.35, 54.75
KEYHEAD_X = D.KEYHEAD_INBOARD_X                     # -607.8
DECK_UNDER = -3.2
WALL_CLR = 0.4


def _theta() -> float:
    """The least common yaw that keeps every motor's +Y face inside the rail."""
    need = 0.0
    for i in range(N):
        near = X_BEND - (x_ref(i) - M_FACE)          # the motor's nearest end, distance from the bend
        over = y_of(i) + M_HALF + WALL_CLR - Y_HI
        if over > 0:
            need = max(need, over / near)
    return math.atan(need) + math.radians(0.15)


THETA = _theta()                                    # raised below until every plug fits


def yaw(wp: cq.Workplane, i: int) -> cq.Workplane:
    """Swing a string's drive part (drawn along -X at y_of(i)) by THETA about its exit point."""
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
        for phi in (90, 270, 0, 180):
            b = _plug_box(i, phi)
            if b[3] > DECK_UNDER - 0.5 or b[2] < floor:
                continue
            dy = math.tan(THETA) * (X_BEND - (x_ref(i) - PLUG[4]))     # the yaw's shift there
            if b[1] - dy > Y_HI - WALL_CLR or b[0] - dy < Y_LO + WALL_CLR:
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


def _settle():
    global THETA
    for _ in range(40):
        try:
            return _plug_dirs()
        except ValueError:
            THETA += math.radians(0.25)
    raise ValueError("no yaw up to 10 deg places every coil plug")


PLUG_DIR = _settle()


# ── report ──────────────────────────────────────────────────────────────────────────────────
def report() -> str:
    out = [f"rows z (axis): " + "  ".join(f"{k}: {z_level(k):.1f}" for k in range(LEVELS)) +
           f"   DZ {DZ}",
           f"yaw THETA {math.degrees(THETA):.2f} deg (string 1's motor inside the +Y rail)",
           f"stations x (pulley plane): " + "  ".join(f"{X_REF0 - s * STATION_P:.1f}"
                                                      for s in range(4)) + f"  pitch {STATION_P}",
           "string row station  motor (x, y, z)            plug  screw length  spring at slack/full"]
    for i in range(N):
        m = yaw_pt((x_ref(i), y_of(i), za(i)), i)
        sl = SCREW_TIP - (x_ref(i) + 11.0)
        s0 = (x_ft(0) - D.NUT_H - COLLAR_L) - ANCHOR[1]
        s1 = (x_ft(1) - D.NUT_H - COLLAR_L) - ANCHOR[1]
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
    out = box_at(YK_H, YK_W, YK_TALL, x=(ft + yt) / 2, y=y, z=z)
    out = out.cut(cyl_x(D.SCREW_OD + 0.8, yt - YK_ROOF - ft + 1, ft - 1, y=y, z=z))   # tip + ball
    out = out.cut(cyl_x(D.NUT_LIP_D + 0.4, D.NUT_LIP_L + 1.3, ft - 1, y=y, z=z))      # lip register
    out = out.cut(cyl_x(D.GUIDE_ROD_D + 0.4, YK_H + 2, ft - 1, y=y, z=z + ROD_DZ))    # the rod
    out = out.cut(cyl_x(2.0, YK_ROOF + 2, yt - YK_ROOF - 1, y=y, z=z))                # the string
    return out


def _nut(i: int, t: float) -> cq.Workplane:
    from . import components as C
    return C.nut().rotate((0, 0, 0), (0, 1, 0), 90).translate((x_ft(t), y_of(i), za(i)))


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
        w = w.cut(yaw(cyl_x(2.0, 10, x0 - 3, y=y_of(i), z=za(i)), i))
        w = w.cut(yaw(cyl_x(D.GUIDE_ROD_D, 10, x0 - 3, y=y_of(i), z=za(i) + ROD_DZ), i))
    return w


def _anchor() -> cq.Workplane:
    x0, x1 = ANCHOR
    w = _plate_yz(x0, x1, CHEEK_Z[0], -20.5)
    for i in range(N):
        w = w.cut(yaw(cyl_x(SLEEVE_OD, 20, x0 - 10, y=y_of(i), z=za(i)), i))
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
        ("db_collar", _tube_x(SPRING_OD, D.NUT_BOSS_D,
                              ft - D.NUT_H - COLLAR_L, ft - D.NUT_H + 0.0, y, z)),
        ("db_spring", _tube_x(SPRING_OD, SPRING_ID, ANCHOR[1], ft - D.NUT_H - COLLAR_L, y, z)),
        ("db_sleeve", _tube_x(SLEEVE_OD, SLEEVE_ID, ANCHOR[0], SLEEVE_END, y, z)),
        ("db_rod", cyl_x(D.GUIDE_ROD_D, ROD_PLATE[1] - 1.0 - ROD_END, ROD_END, y=y, z=z + ROD_DZ)),
        ("db_screw", cyl_x(D.SCREW_OD, SCREW_TIP - (xr + 11.0), xr + 11.0, y=y, z=z)),
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
    from .changer_bench import ghosts
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
    "spring": "stainless", "sleeve": "nylon", "coupler": "aluminium",
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
    "spring": "leg_latch_spring", "sleeve": (0.88, 0.91, 0.94),
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
    ("db_nut", "db_yoke"), ("db_nut", "db_rod"), ("db_nut", "db_collar"), ("db_yoke", "db_rod"),
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
    if "db_anchor" in pair and pair & {"db_spring", "db_sleeve"}:
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
