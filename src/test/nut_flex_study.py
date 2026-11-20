r"""NUT FLEX-CLAMP STUDY (user, 2026-11-20) -- a long, light, gauge-reading clamp, to scale.

The idea (user's sketch): ONE screw per string both clamps the string and sets its height, for
ANY gauge, so a C6 set can come off and an E9 set go on and still play flat.

    bridge ----------------.  crown (top of GREEN)
                            \   break 15-20 deg
     ====== DATUM bar ======.\=================   <- ground underside, common to all ten strings
            (rolled/ground)  '---- string -----     <- straight run along X, pinched 30 mm
     ##### GREEN jaw arm (rigid, deep) ########     <- jaw = up-facing cut edge of GREEN
     ===== flexure blade (slot above) =====|        <- root at +X, under the tower
                               (foot)               <- crowned 12.5 deg facet, under the jaw centre
                        /// SHOE (wedge) ///        <- pulled -X by an M3 from the -X face
     ======================= FLOOR bar ========

  * The screw pulls the SHOE -X; its ramp lifts GREEN's foot; the BLADE bends and pushes GREEN's
    jaw up, pinning the string against the DATUM's underside. The jaw then sits at datum - gauge,
    and the crown, a fixed height above the jaw on the same rigid body, puts every string's top
    at the same Z whatever its gauge.
  * The blade is the flexure: it makes each string's clamp soft (force ~ turns past contact), so
    one string's tightening barely unloads its neighbours and creep in the print barely matters.
  * GREEN rocks on its crowned foot (a line contact on the shoe), so the jaw lies flat on the
    string over the full 30 mm.
  * DATUM and FLOOR are full-Y steel bars tied only past string 1 and string 10: two steel standoffs an end along Z (TIES="z"), M3 12.9 both ends.
  * Clamp loop: datum -> string -> green -> foot -> shoe -> floor -> standoffs -> datum, all steel.
    The print only holds the screw's axial pull (lowers the clamp by tan(alpha) of its creep).

Frame: nut_block_v2's local frame (X = 0 at the old break edge, +X toward the bridge, Z = 0 the
string-top plane, Y across the strings). Run:
    PYTHONPATH=. py -3.12 src/test/nut_flex_study.py      (checks, PNG, STEP)
"""
from __future__ import annotations

import math
import os

import cadquery as cq

from src import dimensions as D
from src import nut_block_v2 as N

# ── loads and materials ─────────────────────────────────────────────────────────────────────
T = N.STRING_T                       # 147 N per string (v2's pessimistic figure)
MU = N.MU                            # 0.15 steel on steel, dry, pessimistic
SF = 2.0                             # clamp margin on slip
P_CRUSH = 30.0                       # N per mm of string: ~5 um of crush on a wound string (estimate,
                                     #   to be replaced by the bench test)
E = 193000.0                         # 304 / 301
YIELD = {"304 annealed": 205.0, "301 full hard": 965.0}
BLADE_MAT = "301 full hard"          # the crown plate's material: the flexure needs spring temper
SIGMA_FRAC = 0.8                     # blade stress allowed at the top of the window, x yield
G_LO, G_HI = 0.010 * 25.4, D.STRING_GAUGE_MAX          # envelope .010 .. .080
GAUGES = sorted(set([G_LO] + list(D.STRING_GAUGE) + [G_HI]))
THREAD_CLR = D.MIN_WALL              # opened: room to thread the heaviest string past the jaw

# ── fixed by today's keyhead ────────────────────────────────────────────────────────────────
XC, RC = N.DOWEL_X, 2.0              # crown centre X (scale length unchanged) and laser-cut radius
X_FRONT = N.PLATE_X1                 # GREEN's +X face, as v2's plate
BAR_R, BAR_CLR = N.BAR_R, N.BAR_CLR_MIN
PITCH = D.NUT_PITCH                  # 6.5
T_PL = 4.0                           # GREEN and SHOE: 4 mm sheet, profile in XZ
POCKET_CLR_Y = N.PLATE_CLR_Y

# ── the knobs ───────────────────────────────────────────────────────────────────────────────
JAW_L = 30.0                         # pinch length (user: 30 for a 2x slip-to-crush window)
RD = 1.5                             # datum's +X lower edge, ground round: the second bend
DATUM_H, FLOOR_W, FLOOR_H = 18.0, 20.0, 16.0           # bars, X x Z (datum X = jaw + RD + margin)
JAW_D = 20.0                         # GREEN's rigid jaw arm depth: carries the blade's root moment
ROOT_W = 2.0                         # blade root block, at GREEN's +X face
ALPHA = 12.5                         # the shoe's ramp
RF = 100.0                           # the foot's crown radius (line contact, rocks)
FOOT_W, FOOT_H = 8.0, 2.0
SHOE_H0_MIN = 9.0                    # shoe's thin (-X) end: screw slot + square-nut window (grown to fit a stock standoff)
SCREW_D, HEAD_D, HEAD_H = 3.0, 5.5, 3.0                # ISO 4762 M3 (2.5 key)
NUT_S, NUT_M = 5.5, 1.8                                # DIN 562 M3 square nut
SLOT_W = 3.3
END_T = 6.0                          # end plates, 304
WIN_CLR = 0.1                        # end-plate windows around the bars, a side (laser +-0.1)
BAR_RECESS = 0.3                     # bar ends stop short of the end plate's outer face
KEEP_T = 2.0                         # retainer plate over the windows, laser-cut
TIE_L = 10                           # M3x10 SHCS into each tapped bar end (end-plate ties only)
TIES = "z"                           # "z": datum and floor tied along Z by standoffs; "plates": end plates
STANDOFFS = (40, 45, 50, 55, 60)     # M3 F-F steel hex standoffs, stock lengths
SO_HEX, SO_THREAD = 5.5, 3.0         # across flats; the screws' thread engagement is the standoff's
SO_DX = 10.0                         # two standoffs an end, this far apart in X, centred on the push point
Z_SCREW_L = 25                       # M3x25 12.9 SHCS, one into each standoff end


# ── string path ─────────────────────────────────────────────────────────────────────────────
def tangent(g, xd1, zd):
    """Crossing tangent from the top of the crown to the underside of the datum's round edge.
    Returns (break angle deg, crown tangent point, datum tangent point) of the string's centreline."""
    c1 = (XC, -g - RC)
    c2 = (xd1 - RD, zd + RD)
    r1, r2 = RC + g / 2, RD + g / 2
    dx, dz = c2[0] - c1[0], c2[1] - c1[1]
    d = math.hypot(dx, dz)
    phi = math.atan2(dz, dx)
    best = None
    for s in (1, -1):
        beta = phi + s * math.acos((r1 + r2) / d)
        n = (math.cos(beta), math.sin(beta))
        if n[1] <= 0:
            continue
        p1 = (c1[0] + r1 * n[0], c1[1] + r1 * n[1])
        p2 = (c2[0] - r2 * n[0], c2[1] - r2 * n[1])
        if p2[0] < p1[0]:
            best = (math.degrees(math.atan2(p1[1] - p2[1], p1[0] - p2[0])), p1, p2)
    return best


def solve_layout():
    L = {}
    # the datum's +X face: a Ø25 bar resting at fret 0 must clear it (its top is above the bar centre)
    L["XD1"] = XC - BAR_R - BAR_CLR
    # its underside: the middle gauge breaks 17.5 deg over the crown
    g_mid = 0.5 * (G_LO + G_HI)
    lo, hi = -20.0, -0.5
    for _ in range(60):
        zd = 0.5 * (lo + hi)
        if tangent(g_mid, L["XD1"], zd)[0] > 17.5:
            lo = zd
        else:
            hi = zd
    L["ZD"] = round(zd, 2)
    L["XJ1"] = L["XD1"] - RD                       # flat of the datum starts here
    L["XJ0"] = L["XJ1"] - JAW_L
    L["XJC"] = 0.5 * (L["XJ0"] + L["XJ1"])
    L["DATUM_X"] = (L["XJ0"] - 0.5, L["XD1"])
    return L


LAY = solve_layout()


def loads(g=None):
    """Window, operating point and the lift GREEN needs, for the mid break."""
    th = math.radians(tangent(0.5 * (G_LO + G_HI) if g is None else g, LAY["XD1"], LAY["ZD"])[0])
    t_c = T * math.exp(-MU * 2 * th)               # crown bend + datum bend
    n_slip = t_c / (2 * MU)                        # just holds
    n_min = SF * n_slip
    n_max = P_CRUSH * JAW_L
    n_op = math.sqrt(n_slip * n_max)               # equal margin to slip and to crush
    v = T * math.sin(th)                           # the crown's down load
    return dict(theta=math.degrees(th), t_c=t_c, n_slip=n_slip, n_min=n_min, n_max=n_max,
                n_op=n_op, v=v, lift_op=n_op + v, lift_max=n_max + v)


LD = loads()
# push point: under the jaw centre, nudged +X so the crown's load leaves the jaw pressure even
X_L = LAY["XJC"] + LD["v"] * (XC - LAY["XJC"]) / LD["lift_op"]
X_ROOT = X_FRONT - ROOT_W
LF = X_ROOT - X_L
SIG = SIGMA_FRAC * YIELD[BLADE_MAT]
TB = math.sqrt(6 * LD["lift_max"] * LF / (T_PL * SIG))          # blade depth (Z)
K_BLADE = E * T_PL * TB ** 3 / (4 * LF ** 3)
DELTA_MAX = LD["lift_max"] / K_BLADE
SLOT = round(DELTA_MAX + 0.3, 1)                                 # closes = overload stop

# GREEN's nominal frame (gauge 0, blade unloaded): crown top z 0, jaw top z ZD
Z_BODY_BOT = LAY["ZD"] - JAW_D
Z_BLADE_TOP = Z_BODY_BOT - SLOT
Z_BLADE_BOT = Z_BLADE_TOP - TB
Z_FOOT = Z_BLADE_BOT - FOOT_H                                     # contact point, nominal
TAN = math.tan(math.radians(ALPHA))


def contact_z(g, state):
    """World Z of the foot's contact point. state: 'open' (dropped to thread), 'touch', 'op', 'max'."""
    if state == "open":
        return Z_FOOT - g - THREAD_CLR
    f = {"touch": 0.0, "op": LD["lift_op"], "max": LD["lift_max"]}[state]
    return Z_FOOT - g + f / K_BLADE


Z_HIGH = contact_z(G_LO, "max")
Z_LOW = contact_z(G_HI, "open")
TRAVEL = (Z_HIGH - Z_LOW) / TAN
SHOE_L = math.ceil(TRAVEL + FOOT_W + 10)
U_HIGH = SHOE_L - 5.0                                             # contact, shoe coords, at Z_HIGH
_ZF0 = Z_HIGH - U_HIGH * TAN                                      # floor top + SHOE_H0
# the gap datum-underside to floor-top is a stock standoff: grow the shoe's thin end to match it
SO_L = min(l for l in STANDOFFS if l >= LAY["ZD"] - (_ZF0 - SHOE_H0_MIN))
SHOE_H0 = SO_L - (LAY["ZD"] - _ZF0)
ZF = _ZF0 - SHOE_H0                                               # floor top
Z_SCREW = ZF + SHOE_H0 / 2
NUT_U = 3.0                                                       # nut window, from the shoe's -X end


def shoe_x(zc):
    """The shoe's -X end for a given contact Z."""
    return X_L - (zc - ZF - SHOE_H0) / TAN


S_MIN, S_MAX = shoe_x(Z_HIGH), shoe_x(Z_LOW)
X_WALL_IN = S_MIN - 1.0                                           # printed wall's +X face
X_HEAD_BEAR = X_WALL_IN - 4.0                                     # head bears here (wall 4 thick)
X_BACK_NEW = X_HEAD_BEAR - HEAD_H - 0.4 - 2.0                     # retaining lip, key hole
_SCREW_NEED = (S_MAX + NUT_U + NUT_M + 0.6) - X_HEAD_BEAR
SCREW_L = min(l for l in (10, 12, 16, 20, 25, 30, 35, 40) if l >= _SCREW_NEED)
SLOT_END_U = (X_HEAD_BEAR + SCREW_L) - S_MIN + 0.5                # the screw tip, deepest, in the shoe

# ── bars ────────────────────────────────────────────────────────────────────────────────────
Y_OUT = 4.5 * PITCH + T_PL / 2 + 2.0                              # end plates' inner faces
# Z ties: standoff centres clear the outer shoes' square nuts (they stick out of the plate)
Y_TIE = 4.5 * PITCH + NUT_S / 2 + 1.0 + SO_HEX / math.sqrt(3)
X_TIES = (X_L - SO_DX / 2, X_L + SO_DX / 2)
SPAN = 2 * Y_TIE if TIES == "z" else 2 * Y_OUT + END_T


def bar_bow(W, b, h):
    I = b * h ** 3 / 12
    return 5 * W * SPAN ** 3 / (384 * E * I), W * SPAN / 8 * (h / 2) / I, I


# ── checks ──────────────────────────────────────────────────────────────────────────────────
def checks():
    out = []
    ths = [tangent(g, LAY["XD1"], LAY["ZD"])[0] for g in GAUGES]
    out.append(("break 15..20 deg, every gauge", 15 <= min(ths) and max(ths) <= 20,
                f"{min(ths):.1f} (.080) .. {max(ths):.1f} (.010)"))
    top = LAY["ZD"] + DATUM_H
    out.append(("datum clears a Ø25 bar at fret 0", XC - LAY["XD1"] >= BAR_R + BAR_CLR - 1e-6,
                f"{XC - LAY['XD1'] - BAR_R:.2f} mm; datum top z {top:+.1f} (above the string plane)"))
    out.append(("pinch window: crush / slip >= 2", LD["n_max"] / LD["n_slip"] >= 2,
                f"slip {LD['n_slip']:.0f} N, SF2 {LD['n_min']:.0f}, crush {LD['n_max']:.0f} "
                f"(x{LD['n_max'] / LD['n_slip']:.1f}); aim {LD['n_op']:.0f} N = {LD['n_op'] / JAW_L:.0f} N/mm"))
    out.append(("push point under the jaw", LAY["XJ0"] < X_L < LAY["XJ1"],
                f"x {X_L:.1f} (jaw {LAY['XJ0']:.1f}..{LAY['XJ1']:.1f}, centre {LAY['XJC']:.1f})"))
    # flexure, both materials
    for mat, y in YIELD.items():
        tb = math.sqrt(6 * LD["lift_max"] * LF / (T_PL * SIGMA_FRAC * y))
        k = E * T_PL * tb ** 3 / (4 * LF ** 3)
        out.append((f"blade in {mat}", mat == BLADE_MAT or k < 5000,
                    f"depth {tb:.1f}, k {k / 1000:.1f} kN/mm"
                    + ("  <- chosen" if mat == BLADE_MAT else "  (no softer than the plain loop: no gain)")))
    k_loop = 1 / (1 / K_BLADE + 1 / 15000.0)
    out.append(("blade", True, f"{LF:.1f} long x {TB:.2f} deep, k {K_BLADE / 1000:.2f} kN/mm "
                f"(loop {k_loop / 1000:.2f}); {DELTA_MAX:.2f} mm at {LD['lift_max']:.0f} N; slot {SLOT} = stop"))
    # jaw arm stiffness: the blade's root moment crosses it to reach the jaw
    I_arm = T_PL * JAW_D ** 3 / 12
    m_root = LD["n_op"] * (X_ROOT - LAY["XJC"])
    rot = 0.5 * (m_root + LD["n_op"] * (LAY["XJ1"] - LAY["XJC"])) * (X_ROOT - LAY["XJ1"]) / (E * I_arm)
    crown_shift = rot * (XC - LAY["XJ1"]) * 1000
    # the shift is the same for every string at the same force; only the force SCATTER shows as
    # unlevel strings (hand tightening by turns: ~ +-30 %)
    out.append(("crown level spread < 5 um", crown_shift * 0.3 < 5.0,
                f"{crown_shift:.1f} um common drop at the aim force, +-{crown_shift * 0.3:.1f} um for +-30 % force "
                f"(jaw arm {JAW_D:.0f} deep; root moment {m_root / 1000:.1f} N.m)"))
    # foot on shoe: line contact, crowned
    Es = E / (2 * (1 - 0.29 ** 2))
    b = math.sqrt(4 * LD["lift_max"] * RF / (math.pi * T_PL * Es))
    p = 2 * LD["lift_max"] / (math.pi * b * T_PL)
    out.append(("foot contact <= 1.67 x 304 yield", p <= 1.67 * YIELD["304 annealed"],
                f"{p:.0f} MPa (shoe 304); rocks {RF * 0.0017:.2f} mm for a 0.1 deg jaw tilt"))
    # screw and wedge
    phi = math.atan(MU)
    f_ax = LD["lift_max"] * (math.tan(math.radians(ALPHA) + phi) + MU)
    out.append(("M3 axial at the top of the window", f_ax < 0.5 * 2260,
                f"{f_ax:.0f} N (A2-70 proof 2260), ~{0.2 * f_ax * 0.003:.2f} N.m"))
    per_turn = 0.5 * TAN * K_BLADE * k_loop / K_BLADE
    out.append(("force per turn past contact", True,
                f"{0.5 * TAN:.3f} mm lift, ~{per_turn:.0f} N/turn -> aim {LD['n_op'] / per_turn:.1f} turns past touch"))
    out.append(("shoe travel", True, f"{TRAVEL:.1f} mm = {TRAVEL / 0.5:.0f} turns open -> clamped "
                f"(.010 tight to .080 threaded); shoe {SHOE_L} long"))
    out.append(("screw length is stock", SLOT_END_U < SHOE_L - 2,
                f"M3x{SCREW_L} (needs {_SCREW_NEED:.1f}); tip {SLOT_END_U:.1f} into a {SHOE_L} shoe"))
    gap = PITCH - T_PL - 2 * POCKET_CLR_Y
    out.append(("heads fit one row", HEAD_D + 0.6 <= PITCH, f"Ø{HEAD_D} at {PITCH} pitch"))
    out.append(("nuts in the finger gap", (NUT_S - T_PL) <= gap - 0.4,
                f"{(NUT_S - T_PL) / 2:.2f} a side into a {gap:.1f} finger (finger relieved there)"))
    # bars
    w = 10 * LD["n_max"]
    d_b, d_s, d_i = bar_bow(w, LAY["DATUM_X"][1] - LAY["DATUM_X"][0], DATUM_H)
    f_b, f_s, f_i = bar_bow(w + 10 * LD["v"], FLOOR_W, FLOOR_H)
    out.append(("datum bow (height error) <= 0.02", d_b <= 0.02,
                f"{d_b * 1000:.0f} um mid, {d_s:.0f} MPa, at all ten = {w / 1000:.1f} kN"))
    out.append(("floor stress <= 0.8 yield", f_s <= 0.8 * 205, f"{f_s:.0f} MPa, bow {f_b * 1000:.0f} um"))
    c = SPAN ** 3 / (48 * E) * (1 / d_i + 1 / f_i)
    r = c * k_loop
    out.append(("neighbour unloads < 5% / string", r < 0.05,
                f"{r * 100:.1f}% each; worst after one pass ~{6 * r * 100:.0f}%, after two ~{(6 * r) ** 2 * 100:.0f}%"))
    end_load = (w + 10 * LD["v"]) / 2
    if TIES == "z":
        a_so = math.sqrt(3) / 2 * SO_HEX ** 2 - math.pi * 1.25 ** 2
        k_end = 2 * E * a_so / SO_L
        per = end_load / 2
        out.append(("Z ties: standoff stretch (common to every string) <= 0.03", end_load / k_end <= 0.03,
                    f"{end_load / 1000:.1f} kN an end on 2 standoffs M3 F-F {SO_HEX} hex x {SO_L}: "
                    f"{end_load / k_end * 1000:.0f} um"))
        out.append(("Z tie screw: preload >= its load, <= 0.6 proof (12.9: 4.9 kN)", per <= 0.6 * 4900,
                    f"{per / 1000:.2f} kN each -> preload ~{per * 1.15 / 1000:.1f} kN, "
                    f"~{0.2 * per * 1.15 * 0.003:.1f} N.m; M3x{Z_SCREW_L} 12.9, thread top "
                    f"{Z_SCREW_L - DATUM_H:.0f} / bottom {Z_SCREW_L - FLOOR_H:.0f} into the standoff"))
        out.append(("shoe thin end grown to the standoff", SHOE_H0 >= SHOE_H0_MIN,
                    f"SHOE_H0 {SHOE_H0:.2f} (min {SHOE_H0_MIN}) for a {SO_L} standoff"))
    else:
        out.append(("end ties", True, f"{end_load / 1000:.1f} kN a end: bars bear in laser-cut windows; 1x M3x{TIE_L} SHCS per bar end clamps a {KEEP_T:.0f} mm keeper"))
    # envelope vs today
    z_bot = ZF - FLOOR_H
    out.append(("depth from the crown", -z_bot <= 75.0, f"{-z_bot:.1f} (study floor 75; ordered plate today 52.35)"))
    out.append(("-X growth", True, f"-X face {X_BACK_NEW:.1f} vs today {N.X_BACK} -> {N.X_BACK - X_BACK_NEW:+.1f} mm longer"))
    return out


# ── solids (each string at its own C6 gauge, clamped at the operating force) ─────────────────
def _xz(pts, y0=0.0, t=T_PL):
    return (cq.Workplane("XZ").polyline(pts).close().extrude(t / 2, both=True)
            .translate((0, y0, 0)))


def _box(x0, x1, z0, z1, y0=0.0, t=T_PL):
    return cq.Workplane("XY").box(x1 - x0, t, z1 - z0, centered=(False, True, False)).translate((x0, y0, z0))


def green(dz=0.0, y0=0.0):
    xj0 = LAY["XJ0"] - 0.5
    body = _box(xj0, X_FRONT, Z_BODY_BOT, LAY["ZD"])                       # jaw arm
    body = body.union(_box(XC - RC, X_FRONT, Z_BODY_BOT, -RC))             # tower
    body = body.union(cq.Workplane("XZ").center(XC, -RC).circle(RC).extrude(T_PL / 2, both=True))
    blade_x0 = X_L - FOOT_W / 2 - 1.0
    body = body.union(_box(blade_x0, X_FRONT, Z_BLADE_BOT, Z_BODY_BOT))   # blade + root, slot cut next
    body = body.cut(_box(blade_x0 - 1, X_ROOT, Z_BLADE_TOP, Z_BODY_BOT))
    # crowned foot: tangent at X_L with slope ALPHA (rising +X)
    n = (-math.sin(math.radians(ALPHA)), math.cos(math.radians(ALPHA)))
    cen = (X_L + RF * n[0], Z_FOOT + RF * n[1])
    foot = _box(X_L - FOOT_W / 2, X_L + FOOT_W / 2, Z_FOOT - 3, Z_BLADE_BOT + 0.01)
    foot = foot.intersect(cq.Workplane("XZ").center(*cen).circle(RF).extrude(T_PL, both=True))
    return body.union(foot).translate((0, y0, dz))


def shoe(s, y0=0.0):
    pts = [(s, ZF), (s + SHOE_L, ZF), (s + SHOE_L, ZF + SHOE_H0 + SHOE_L * TAN), (s, ZF + SHOE_H0)]
    p = _xz(pts, y0)
    p = p.cut(_box(s - 1, s + SLOT_END_U, Z_SCREW - SLOT_W / 2, Z_SCREW + SLOT_W / 2, y0, T_PL + 1))
    p = p.cut(_box(s + NUT_U, s + NUT_U + NUT_M + 0.1, Z_SCREW - (NUT_S + 0.1) / 2, Z_SCREW + (NUT_S + 0.1) / 2, y0, T_PL + 1))
    return p


def screw(y0):
    shank = cq.Workplane("YZ").circle(SCREW_D / 2).extrude(SCREW_L).translate((X_HEAD_BEAR, y0, Z_SCREW))
    head = cq.Workplane("YZ").circle(HEAD_D / 2).extrude(HEAD_H).translate((X_HEAD_BEAR - HEAD_H, y0, Z_SCREW))
    return shank.union(head)


def nut(s, y0):
    return _box(s + NUT_U + 0.05, s + NUT_U + 0.05 + NUT_M, Z_SCREW - NUT_S / 2, Z_SCREW + NUT_S / 2, y0, NUT_S)


def string(g, y0):
    th, p1, p2 = tangent(g, LAY["XD1"], LAY["ZD"])
    zc = LAY["ZD"] - g / 2
    segs = [((XC + 25, -g / 2), (XC, -g / 2)), (p1, p2), ((LAY["XJ1"], zc), (X_BACK_NEW - 5, zc))]
    s = None
    for a, b in segs:
        v = cq.Vector(b[0] - a[0], 0, b[1] - a[1])
        c = cq.Solid.makeCylinder(g / 2, v.Length, cq.Vector(a[0], y0, a[1]), v.normalized())
        s = c if s is None else s.fuse(c)
    return cq.Workplane().add(s)


def _bar_y():
    """Bars run through the end plates' windows, ends BAR_RECESS short of the outer faces."""
    if TIES == "z":
        return 2 * (Y_TIE + SO_HEX / 2 + 3.0)
    return 2 * (Y_OUT + END_T - BAR_RECESS)


def _datum_sec():
    x0, x1 = LAY["DATUM_X"]
    return x0, x1, LAY["ZD"], LAY["ZD"] + DATUM_H


def _floor_sec():
    return X_L - FLOOR_W / 2, X_L + FLOOR_W / 2, ZF - FLOOR_H, ZF


def datum():
    x0, x1, z0, z1 = _datum_sec()
    b = cq.Workplane("XY").box(x1 - x0, _bar_y(), z1 - z0, centered=(False, True, False)).translate((x0, 0, z0))
    b = b.edges("|Y").edges(cq.selectors.NearestToPointSelector((x1, 0, z0))).fillet(RD)
    return b.cut(_tie_holes(_datum_sec())) if TIES != "z" else b.cut(_z_holes(z0, z1))


def floor_bar():
    x0, x1, z0, z1 = _floor_sec()
    b = cq.Workplane("XY").box(x1 - x0, _bar_y(), z1 - z0, centered=(False, True, False)).translate((x0, 0, z0))
    return b.cut(_tie_holes(_floor_sec())) if TIES != "z" else b.cut(_z_holes(z0, z1))


def _z_holes(z0, z1, d=3.4):
    """Plain M3 clearance holes, drilled through along Z (the threads are the standoffs')."""
    out = None
    for y in (-Y_TIE, Y_TIE):
        for x in X_TIES:
            h = cq.Workplane("XY").center(x, y).circle(d / 2).extrude(z1 - z0 + 2).translate((0, 0, z0 - 1))
            out = h if out is None else out.union(h)
    return out


def standoff(x, y):
    """M3 female-female steel hex standoff, SO_L long: datum underside to floor top."""
    return (cq.Workplane("XY").center(x, y).polygon(6, SO_HEX / math.cos(math.pi / 6)).extrude(SO_L)
            .cut(cq.Workplane("XY").center(x, y).circle(2.5 / 2).extrude(SO_L))
            .translate((0, 0, ZF)))


def z_screw(x, y, top):
    """ISO 4762 M3xZ_SCREW_L: from the datum top (top) or the floor bottom, into the standoff."""
    if top:
        z_face = LAY["ZD"] + DATUM_H
        shank = cq.Workplane("XY").center(x, y).circle(SCREW_D / 2).extrude(-Z_SCREW_L).translate((0, 0, z_face))
        head = cq.Workplane("XY").center(x, y).circle(HEAD_D / 2).extrude(HEAD_H).translate((0, 0, z_face))
    else:
        z_face = ZF - FLOOR_H
        shank = cq.Workplane("XY").center(x, y).circle(SCREW_D / 2).extrude(Z_SCREW_L).translate((0, 0, z_face))
        head = cq.Workplane("XY").center(x, y).circle(HEAD_D / 2).extrude(-HEAD_H).translate((0, 0, z_face))
    return shank.union(head)


def _tie_c(sec):
    return 0.5 * (sec[0] + sec[1]), 0.5 * (sec[2] + sec[3])


def _tie_holes(sec, depth=TIE_L - KEEP_T - BAR_RECESS + 1.0, d=2.5):
    """Tap-drill holes (2.5 for M3) in both bar ends, at the section's centre."""
    x, z = _tie_c(sec)
    out = None
    for side in (-1, 1):
        y_end = side * (_bar_y() / 2)
        h = cq.Workplane("XZ").center(x, z).circle(d / 2).extrude(depth / 2, both=True)             .translate((0, y_end - side * depth / 2, 0))
        out = h if out is None else out.union(h)
    return out


def _plate_xz():
    x0 = min(LAY["DATUM_X"][0], X_L - FLOOR_W / 2) - 3
    x1 = max(LAY["DATUM_X"][1], X_L + FLOOR_W / 2) + 3
    return x0, x1, ZF - FLOOR_H - 3, LAY["ZD"] + DATUM_H + 3


def end_plate(side):
    x0, x1, z0, z1 = _plate_xz()
    y = side * (Y_OUT + END_T / 2)
    p = _box(x0, x1, z0, z1, y, END_T)
    # the space between the bars, where the strings' clamps live, is open
    p = p.cut(_box(x0 - 1, x1 + 1, ZF + 4, LAY["ZD"] - 4, y, END_T + 1))
    # windows: the bars pass through and bear on the window edges (Z load in steel, not in the screws)
    for sec in (_datum_sec(), _floor_sec()):
        p = p.cut(_box(sec[0] - WIN_CLR, sec[1] + WIN_CLR, sec[2] - WIN_CLR, sec[3] + WIN_CLR, y, END_T + 1))
    return p


def keeper(side):
    """Retainer over both windows; the two M3s clamp it onto the end plate's outer face."""
    x0, x1, z0, z1 = _plate_xz()
    y = side * (Y_OUT + END_T + KEEP_T / 2)
    p = _box(x0, x1, z0, z1, y, KEEP_T)
    p = p.cut(_box(x0 - 1, x1 + 1, ZF + 4, LAY["ZD"] - 4, y, KEEP_T + 1))
    for sec in (_datum_sec(), _floor_sec()):
        x, z = _tie_c(sec)
        p = p.cut(cq.Workplane("XZ").center(x, z).circle(3.4 / 2).extrude(KEEP_T, both=True).translate((0, y, 0)))
    return p


def tie_screw(sec, side):
    """ISO 4762 M3xTIE_L: head on the keeper's outer face, shank into the bar end."""
    x, z = _tie_c(sec)
    y_face = side * (Y_OUT + END_T + KEEP_T)
    shank = cq.Workplane("XZ").center(x, z).circle(SCREW_D / 2).extrude(TIE_L)       # XZ normal is -Y
    head = cq.Workplane("XZ").center(x, z).circle(HEAD_D / 2).extrude(-HEAD_H)
    s = shank.union(head)
    return s.translate((0, y_face, 0)) if side > 0 else s.mirror("XZ").translate((0, y_face, 0))


def assembly():
    parts = [("nf_datum", datum()), ("nf_floor", floor_bar())]
    if TIES == "z":
        for side, ab in ((-1, "a"), (1, "b")):
            for k, x in enumerate(X_TIES):
                y = side * Y_TIE
                parts += [(f"nf_standoff_{ab}{k}", standoff(x, y)),
                          (f"nf_tie_top_{ab}{k}", z_screw(x, y, True)),
                          (f"nf_tie_bot_{ab}{k}", z_screw(x, y, False))]
    else:
        parts += [("nf_end_a", end_plate(-1)), ("nf_end_b", end_plate(1)),
                  ("nf_keep_a", keeper(-1)), ("nf_keep_b", keeper(1))]
        for side, ab in ((-1, "a"), (1, "b")):
            parts += [(f"nf_tie_datum_{ab}", tie_screw(_datum_sec(), side)),
                      (f"nf_tie_floor_{ab}", tie_screw(_floor_sec(), side))]
    for i in range(D.N_STRINGS):
        y, g = D.nut_y(i), D.STRING_GAUGE[i]
        s = shoe_x(contact_z(g, "op"))
        parts += [(f"nf_green_{i}", green(-g + 0.0, y)), (f"nf_shoe_{i}", shoe(s, y)),
                  (f"nf_screw_{i}", screw(y)), (f"nf_nut_{i}", nut(s, y)), (f"nf_string_{i}", string(g, y))]
    return parts


# ── drawing ────────────────────────────────────────────────────────────────────────────────
def draw(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    BG = "#36383d"
    COL = {"green": "#39ff14", "datum": "#00b4d8", "shoe": "#ff6b00", "floor": "#9a9a9a",
           "screw": "#c8c8c8", "end": "#555b66"}

    def outline(ax, wp, col, lw=1.8, y=0.0):
        sl = wp.val().intersect(cq.Solid.makeBox(400, 0.02, 400, cq.Vector(-200, y - 0.01, -200)))
        for e in sl.Edges():
            if abs(e.Center().y - y) > 0.02 or e.Length() < 1e-3:
                continue
            pts = [e.positionAt(t / 30) for t in range(31)]
            ax.plot([p.x for p in pts], [p.z for p in pts], color=col, lw=lw)

    fig, axs = plt.subplots(1, 2, figsize=(20, 11), gridspec_kw={"width_ratios": [3, 1.25]})
    fig.patch.set_facecolor(BG)
    for ax in axs:
        ax.set_facecolor(BG); ax.set_aspect("equal"); ax.tick_params(colors="#999")
        [s.set_color("#666") for s in ax.spines.values()]
    ax = axs[0]
    for g, state, ls in ((G_HI, "op", "-"), (G_LO, "op", "--")):
        s = shoe_x(contact_z(g, state))
        outline(ax, green(-g), COL["green"], 2.0 if ls == "-" else 0.9)
        if ls == "-":
            outline(ax, shoe(s), COL["shoe"])
            outline(ax, nut(s, 0), COL["screw"], 1.0)
    outline(ax, datum(), COL["datum"], 2.2)
    outline(ax, floor_bar(), COL["floor"], 2.2)
    outline(ax, screw(0), COL["screw"], 1.2)
    for g, col in ((G_HI, "#ffffff"), (G_LO, "#ffd166")):
        th, p1, p2 = tangent(g, LAY["XD1"], LAY["ZD"])
        zc = LAY["ZD"] - g / 2
        ax.plot([XC + 22, XC], [-g / 2] * 2, color=col, lw=1.2)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=col, lw=1.2)
        ax.plot([LAY["XJ1"], X_BACK_NEW - 4], [zc, zc], color=col, lw=1.2)
    ax.add_patch(Circle((XC, BAR_R), BAR_R, fc="none", ec="#888", ls=":", lw=1.2))
    ax.plot([N.X_BACK] * 2, [8, ZF - FLOOR_H - 4], color="#888", ls="--", lw=1)
    ax.text(N.X_BACK + 0.4, 6, "today's -X face", color="#888", fontsize=8)
    ax.plot([X_BACK_NEW] * 2, [8, ZF - FLOOR_H - 4], color="#ccc", ls="--", lw=1)
    ax.text(X_BACK_NEW + 0.4, 9, "new -X face", color="#ccc", fontsize=8)
    ax.axhline(0, color="#777", lw=0.6, ls=":")
    ax.text(XC + 6, 1.0, "string top z 0, every gauge", color="#ddd", fontsize=8)
    ax.text(LAY["XJ0"], LAY["ZD"] + DATUM_H + 1.2, f"DATUM bar {LAY['DATUM_X'][1] - LAY['DATUM_X'][0]:.0f} x {DATUM_H:.0f}, ground underside",
            color=COL["datum"], fontsize=9)
    ax.text(LAY["XJ0"] + 1, Z_BODY_BOT + 3, f"GREEN ({BLADE_MAT}, 4 mm): jaw {JAW_L:.0f} long, crown, blade", color=COL["green"], fontsize=9)
    ax.text(LAY["XJ0"] + 1, Z_BLADE_BOT - 1.6, f"blade {LF:.0f} x {TB:.1f}, slot {SLOT}", color=COL["green"], fontsize=8)
    ax.text(S_MIN - 2, ZF + SHOE_H0 + SHOE_L * TAN + 1.5, f"SHOE {ALPHA} deg", color=COL["shoe"], fontsize=9)
    ax.text(X_L - FLOOR_W / 2, ZF - FLOOR_H - 3, f"FLOOR bar {FLOOR_W:.0f} x {FLOOR_H:.0f}", color=COL["floor"], fontsize=9)
    ax.text(X_HEAD_BEAR - 12, Z_SCREW - 6, f"M3x{SCREW_L} SHCS,\nhead held in the print", color=COL["screw"], fontsize=8)
    ax.text(XC - 9, BAR_R + 4, "Ø25 bar at fret 0", color="#888", fontsize=8)
    ax.text(X_BACK_NEW, ZF - FLOOR_H - 9, ".080 at its operating clamp (solid), .010 green dashed",
            color="#ddd", fontsize=8)
    ax.set_xlim(X_BACK_NEW - 6, XC + 24); ax.set_ylim(ZF - FLOOR_H - 11, BAR_R * 2 + 2)
    ax.set_title("Nut flex-clamp, side section (XZ), to scale, mm", color="w")
    # right: the ten strings across Y, at the jaw centre section
    ax = axs[1]
    xs = LAY["XJC"]
    for i in range(D.N_STRINGS):
        y, g = D.nut_y(i), D.STRING_GAUGE[i]
        zc = LAY["ZD"] - g / 2
        ax.add_patch(Circle((y, zc), g / 2, fc="#ffffff", ec="none"))
        top = LAY["ZD"] - g
        ax.add_patch(plt.Rectangle((y - T_PL / 2, Z_BODY_BOT - g), T_PL, top - (Z_BODY_BOT - g), fc="none", ec=COL["green"], lw=1.2))
        ax.text(y, Z_BODY_BOT - g - 2.5, f"{g / 25.4 * 1000:.0f}", color="#ddd", fontsize=7, ha="center")
    ax.add_patch(plt.Rectangle((-Y_OUT, LAY["ZD"]), 2 * Y_OUT, DATUM_H, fc="none", ec=COL["datum"], lw=2))
    for sd in (-1, 1):
        ax.add_patch(plt.Rectangle((sd * Y_OUT if sd > 0 else -Y_OUT - END_T, LAY["ZD"] - 25), END_T, DATUM_H + 28,
                                   fc="none", ec=COL["end"], lw=1.5))
    ax.set_xlim(-Y_OUT - 9, Y_OUT + 9); ax.set_ylim(LAY["ZD"] - 26, LAY["ZD"] + DATUM_H + 4)
    ax.set_title(f"across Y at x {xs:.1f}: jaws drop by each gauge,\nstring tops all on the datum", color="w", fontsize=10)
    plt.savefig(path, dpi=110, facecolor=BG, bbox_inches="tight")


if __name__ == "__main__":
    print(f"layout: datum +X face {LAY['XD1']:.2f}, underside z {LAY['ZD']:.2f}; jaw {LAY['XJ0']:.1f}..{LAY['XJ1']:.1f}; "
          f"push x {X_L:.1f}; floor top z {ZF:.1f}; screw z {Z_SCREW:.1f}")
    print(f"loads: break {LD['theta']:.1f}, tension at the pinch {LD['t_c']:.0f} N, crown {LD['v']:.0f} N, "
          f"lift at aim {LD['lift_op']:.0f} N")
    bad = 0
    for name, ok, val in checks():
        bad += not ok
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {val}")
    out = "out/nut_flex_study"
    os.makedirs(out, exist_ok=True)
    draw(os.path.join(out, "nut_flex_study.png"))
    asm = cq.Assembly()
    for nm, wp in assembly():
        asm.add(wp, name=nm)
    asm.save(os.path.join(out, "nut_flex_study.step"))
    for nm, wp in (("green", green()), ("shoe", shoe(0.0))):
        cq.exporters.export(wp, os.path.join(out, f"nut_flex_{nm}.step"))
    print(f"  wrote {out}/nut_flex_study.png, nut_flex_study.step, nut_flex_green.step, nut_flex_shoe.step"
          f"  ({bad} FAIL)")
