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
  * SPRING = "head" (user 2026-11-20, the default): GREEN is rigid 304 (no blade, no slot). The
    force is set at the screw head by a disc-spring stack: 2 groups of 3 nested McMaster
    96445K101 (3.2 x 6 x 0.3, 151 N flat each), back to back. Tighten until the stack is flat and
    the torque climbs. The head bears on a lip machined on the FLOOR bar, so the screw's reaction
    stays in steel. SPRING = "blade" keeps the 301 full-hard flexure version below.
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
DATUM_H, FLOOR_W, FLOOR_H = 12.0, 20.0, 14.0           # bars, X x Z (datum X = jaw + RD + margin)
# DATUM_H 12 (user 2026-11-22, was 19): sized by the bar, not by a bow figure -- the extra force a bar at
# fret 1 needs to press every string level (bar_level_force) stays under a bar's own ~2 N weight
JAW_D = 20.0                         # GREEN's rigid jaw arm depth: carries the blade's root moment
ROOT_W = 2.0                         # blade root block, at GREEN's +X face
ALPHA = 14.0                         # the shoe's ramp: the steepest that keeps the weakest clamp >= 1.2 x slip
                                     #   with 3 nested discs AND the wall's friction on GREEN (16 without it)
RF = 100.0                           # the foot's crown radius (line contact, rocks)
FOOT_W, FOOT_H = 8.0, 2.0
SPRING = "head"                      # "head": disc stack under the screw head, rigid GREEN; "blade": 301 flexure
DISC = dict(sku="McMaster 96445K101", d=3.2, D=6.0, t=0.3, h=0.45, f=151.0)   # 34 lbf flat, chrome-vanadium
DISC_PAR, DISC_SER = 3, 2            # nested per group, groups back to back
DISC_TOL = (-0.075, 0.25)            # DIN 2093 load tolerance at this size
MU_RAMP = (0.10, 0.20)               # the shoe ramp's friction, unmeasured: the clamp window spans it
K_LIFT_LOOP = 15000.0                # N/mm, the steel clamp loop seen at the foot (assumed; bench it)
N_CEIL = 1300.0                      # clamp ceiling, OPEN: crown rise <= 0.03 at this, per the bench test
LIP_T = 6.0                          # head plate: 304 laser-cut, stands on the floor bar's -X end face;
                                     #   it is also GREEN's X stop (a nub on GREEN's -X face bears on it)
NUB_DZ, NUB_H = 7.0, 3.0             # GREEN's stop nub: centre this far above the screw axis, this tall
WALL_MU = 0.15                       # nub on plate, steel on steel dry (PTFE film ~0.08)
PAD_RELIEF = 0.3                     # GREEN's incline sits this far off the shoe ramp, except at the pad
SO_CBORE_D = 6.6                     # standoff counterbore in the floor top (hex 5.5 F-F, 6.35 corners)
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
DATUM_CBORE = (6.5, 3.4)              # ISO 4762 M3 counterbore in the datum top: tie heads flush
SO_DX = 10.0                         # two standoffs an end, this far apart in X, centred on the push point
Z_SCREW_L = 20                       # tie screw length, one into each standoff end (one stock SKU)
# tie size: M4 (user 2026-11-20, JLCCNC cuts the holes) -- 7 hex standoffs are 1.6x the M3's area, and
# M4 BUTTON heads take the same 2.5 key as the M3 SHCS
TIE_SPECS = {
    "M3": dict(d=3.0, clr=3.4, tap=2.5, hex=5.5, head_d=5.5, head_h=3.0, cbore=(6.5, 3.4),
               kind="ISO 4762 12.9 SHCS", proof=4900.0),
    "M4": dict(d=4.0, clr=4.5, tap=3.3, hex=7.0, head_d=7.6, head_h=2.2, cbore=(8.2, 2.4),
               kind="ISO 7380 10.9 button", proof=7300.0),
}
TIE_SIZE = "M4"
TS = TIE_SPECS[TIE_SIZE]
SO_HEX = TS["hex"]
DATUM_CBORE = TS["cbore"]
SO_CBORE_D = SO_HEX / math.cos(math.pi / 6) + 0.3      # hex corners + clearance


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
# Z only (independent of X_L): GREEN's pad and the screw axis, for the wall couple; checked after layout
Z_FOOT_EST = None
Z_NUB_EST = None
# push point: under the jaw centre, nudged +X so the crown's load leaves the jaw pressure even
X_L = LAY["XJC"] + LD["v"] * (XC - LAY["XJC"]) / LD["lift_op"]


def jaw_resultant(x_l, n, mu=0.2):
    """Where the string's reaction on the jaw lands: GREEN balances lift at x_l, crown v at XC, jaw n,
    and (head) the couple of the ramp's -X thrust at the pad against the wall's +X push at the nub."""
    x = x_l + LD["v"] * (x_l - XC) / n
    if SPRING == "head":
        x += (n + LD["v"]) * (math.tan(math.radians(ALPHA)) + mu) * (Z_FOOT_EST - Z_NUB_EST) / n
    return x


if SPRING == "head":
    # rigid GREEN: push as far +X as keeps the jaw's reaction in its middle third (full-length contact,
    # pressure never reaching zero at the -X end), 1 mm in from the third, at the strongest clamp
    _rf = lambda mu: math.tan(math.radians(ALPHA) + math.atan(mu)) + mu
    _n_hi = DISC_PAR * DISC["f"] * (1 + DISC_TOL[1]) / _rf(MU_RAMP[0]) - LD["v"]
    _x_lim = LAY["XJC"] + JAW_L / 6 - 1.0
    X_L = (_x_lim + LD["v"] * XC / _n_hi) / (1 + LD["v"] / _n_hi)
X_ROOT = X_FRONT - ROOT_W
LF = X_ROOT - X_L
SIG = SIGMA_FRAC * YIELD[BLADE_MAT]
TB = math.sqrt(6 * LD["lift_max"] * LF / (T_PL * SIG))          # blade depth (Z)
K_BLADE = E * T_PL * TB ** 3 / (4 * LF ** 3)
DELTA_MAX = LD["lift_max"] / K_BLADE
SLOT = round(DELTA_MAX + 0.3, 1)                                 # closes = overload stop
if SPRING == "head":                                             # rigid GREEN: no blade, no slot
    TB, SLOT, K_BLADE, DELTA_MAX = 0.0, 0.0, math.inf, 0.0
STACK_FLAT = DISC_SER * DISC_PAR * DISC["t"] if SPRING == "head" else 0.0
STACK_FREE = DISC_SER * (DISC_PAR * DISC["t"] + DISC["h"] - DISC["t"]) if SPRING == "head" else 0.0

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
SHOE_L = math.ceil(TRAVEL + FOOT_W + (6 if SPRING == "head" else 10))
U_HIGH = SHOE_L - 5.0                                             # contact, shoe coords, at Z_HIGH
_ZF0 = Z_HIGH - U_HIGH * TAN                                      # floor top + SHOE_H0
# the gap datum-underside to floor-top is a stock standoff: grow the shoe's thin end to match it
SO_L = min(l for l in STANDOFFS if l >= LAY["ZD"] - (_ZF0 - SHOE_H0_MIN))
SHOE_H0 = SO_L - (LAY["ZD"] - _ZF0)
SO_CBORE = 0.0
if SPRING == "head":       # keep the shoe at its minimum (screw low, short lever on the head plate):
    SHOE_H0 = SHOE_H0_MIN  # the standoff sinks into a counterbore in the floor top instead
    SO_CBORE = SO_L - (LAY["ZD"] - (_ZF0 - SHOE_H0))
ZF = _ZF0 - SHOE_H0                                               # floor top
Z_SCREW = ZF + SHOE_H0 / 2
NUT_U = 3.0                                                       # nut window, from the shoe's -X end


def shoe_x(zc):
    """The shoe's -X end for a given contact Z."""
    return X_L - (zc - ZF - SHOE_H0) / TAN


if SPRING == "head":       # now that Z is laid out: the wall couple moves the push point back -X
    Z_FOOT_EST, Z_NUB_EST = Z_FOOT, Z_SCREW + NUB_DZ
    X_L -= (_n_hi + LD["v"]) * (math.tan(math.radians(ALPHA)) + MU_RAMP[1]) * (Z_FOOT_EST - Z_NUB_EST) / _n_hi
S_MIN, S_MAX = shoe_x(Z_HIGH), shoe_x(Z_LOW)
X_WALL_IN = S_MIN - 1.0                                           # printed wall's +X face
X_HEAD_BEAR = X_WALL_IN - (LIP_T if SPRING == "head" else 4.0)   # bearing face: floor lip / printed wall
X_HEAD = X_HEAD_BEAR - STACK_FLAT                                 # the head's seat, stack flat
# the -X face: FLUSH WITH THE HEADS FULLY INSTALLED, the stack flat (user, 2026-11-22: "It's fine if loose
# hardware extends beyond the face, we just need it to be flush when fully installed"; the old 2.0 lip
# and key hole held the heads in the blade-spring design, and 0.4 kept loose heads in)
X_BACK_NEW = X_HEAD - HEAD_H
_SCREW_NEED = (S_MAX + NUT_U + NUT_M + 0.6) - X_HEAD
SCREW_L = min(l for l in (10, 12, 16, 20, 25, 30, 35, 40) if l >= _SCREW_NEED)
SLOT_END_U = (X_HEAD + SCREW_L) - S_MIN + 0.5                     # the screw tip, deepest, in the shoe
Z_LIP_TOP = (Z_SCREW + NUB_DZ + NUB_H / 2 + 1.5 if SPRING == "head"   # covers GREEN's nub at every gauge
             else Z_SCREW + 4.5)

# ── bars ────────────────────────────────────────────────────────────────────────────────────
Y_OUT = 4.5 * PITCH + T_PL / 2 + 2.0                              # end plates' inner faces
# Z ties: standoff centres clear the outer shoes' square nuts (they stick out of the plate)
Y_TIE = 4.5 * PITCH + NUT_S / 2 + 1.0 + SO_HEX / math.sqrt(3)
if SPRING == "head":       # the printed endplate (nut_endplate_study): a 1.6 wall between the square nuts'
    # travel band and the standoffs' hex pockets, 0.15 a side clear. A FLAT FACES +X (user, 2026-11-23:
    # the string load bears on a face, not on two corner lines that creep in), so corners are on +-Y
    Y_TIE = 4.5 * PITCH + NUT_S / 2 + 0.15 + D.MIN_WALL_2P + (SO_HEX / 2 + 0.15) / math.cos(math.pi / 6)
if SPRING == "head":       # spread the pair as wide as datum and floor allow, still centred on the push
    _m = (SO_HEX / 2 if SPRING == "head" else SO_HEX / math.sqrt(3)) + 1.5   # hex half-extent in X + a margin
    _lo = max(LAY["DATUM_X"][0], X_WALL_IN) + _m
    _hi = min(LAY["DATUM_X"][1], max(X_L + FLOOR_W / 2, S_MAX + SHOE_L + 1.0)) - _m
    SO_DX = 2 * min(X_L - _lo, _hi - X_L)
X_TIES = (X_L - SO_DX / 2, X_L + SO_DX / 2)
SPAN = 2 * Y_TIE if TIES == "z" else 2 * Y_OUT + END_T


def bar_bow(W, b, h):
    I = b * h ** 3 / 12
    return 5 * W * SPAN ** 3 / (384 * E * I), W * SPAN / 8 * (h / 2) / I, I


TIGHTEN_PASSES = 4                   # passes over all ten, 1 -> 10, each to flat: 12 datum 462 N after 3, 516 after 4


def tighten_passes(k_loop, hd=None, hf=None, passes=None, order=tuple(range(10))):
    """Weakest clamp after `passes` passes, simulated: tightening string i to flat (its stack at the stop)
    raises its force to the window top; both bars' bow at string j (point-load influence, simply supported
    on the ties) opens j's loop, which loses k_loop x that. The victim is taken at the window's floor
    with every aggressor at its top. Returns (weakest N, worst loss N)."""
    from src import dimensions as D
    hd = DATUM_H if hd is None else hd
    hf = FLOOR_H if hf is None else hf
    passes = TIGHTEN_PASSES if passes is None else passes
    pull = DISC_PAR * DISC["f"]
    hi = pull * (1 + DISC_TOL[1]) / ramp_factor(MU_RAMP[0]) - LD["v"]
    lo = pull * (1 + DISC_TOL[0]) / ramp_factor(MU_RAMP[1]) - LD["v"]
    lo -= WALL_MU * (lo + LD["v"]) * (math.tan(math.radians(ALPHA)) + MU_RAMP[1])
    bd = LAY["DATUM_X"][1] - LAY["DATUM_X"][0]
    EId, EIf = E * bd * hd ** 3 / 12, E * floor_b() * hf ** 3 / 12
    ys = [D.nut_y(i) + Y_TIE for i in range(10)]

    def infl(x, a, EI):
        b = SPAN - a
        if x > a:
            x, a, b = SPAN - x, b, a
        return b * x * (SPAN ** 2 - b ** 2 - x ** 2) / (6 * SPAN * EI)
    A = [[infl(ys[i], ys[j], EId) + infl(ys[i], ys[j], EIf) for j in range(10)] for i in range(10)]
    n = [0.0] * 10
    for _ in range(passes):
        for i in order:
            d = hi - n[i]
            for j in range(10):
                if j != i:
                    n[j] -= k_loop * A[j][i] * d
            n[i] = hi
    loss = max(hi - x for x in n)
    return lo - loss, loss


BAR_LEVEL_MAX = 1.5                  # N: extra bar force to level the strings at fret 1 (a bar weighs ~2 N)


def bar_level_force(n_each, h, T=147.0):
    """Extra force a flat bar at fret 1 needs to bring all ten strings level. The jaws push the datum up
    (n_each a string, point loads at the strings, simply supported on the ties: the worst case), so each
    string's crown rises by the datum's local bow; at fret 1 that is (1 - x1/L) of it. The bar lands on
    the highest strings and pushes each down to the lowest, T (1/x1 + 1/(L - x1)) per mm.
    Returns (force N, worst step at fret 1 mm, bow mm)."""
    from src import dimensions as D
    b = LAY["DATUM_X"][1] - LAY["DATUM_X"][0]
    EI = E * b * h ** 3 / 12
    L = D.MOUNTING_SPAN
    x1 = L * (1 - 2 ** (-1 / 12))
    ys = [D.nut_y(i) + Y_TIE for i in range(10)]

    def ss(x, a):
        bb = SPAN - a
        if x > a:
            x, a, bb = SPAN - x, bb, a
        return n_each * bb * x * (SPAN ** 2 - bb ** 2 - x ** 2) / (6 * SPAN * EI)
    d = [sum(ss(y, a) for a in ys) for y in ys]
    ex = [(di - min(d)) * (1 - x1 / L) for di in d]
    return T * (1 / x1 + 1 / (L - x1)) * sum(ex), max(ex), max(d)


def ramp_factor(mu):
    """Screw pull per newton of lift at the foot: wedge at ALPHA with friction mu on both faces."""
    return math.tan(math.radians(ALPHA) + math.atan(mu)) + mu


def head_checks():
    """The disc stack under the head: the clamp window it gives and how sharp its stop is."""
    out = []
    pull = DISC_PAR * DISC["f"]
    lo = pull * (1 + DISC_TOL[0]) / ramp_factor(MU_RAMP[1]) - LD["v"]
    hi = pull * (1 + DISC_TOL[1]) / ramp_factor(MU_RAMP[0]) - LD["v"]
    th_lo = (lo + LD["v"]) * (math.tan(math.radians(ALPHA)) + MU_RAMP[1])
    lo_raw, lo = lo, lo - WALL_MU * th_lo          # the nub drags on the plate as GREEN rises
    out.append(("head stack: weakest clamp >= 1.2 x slip", lo >= 1.2 * LD["n_slip"],
                f"{DISC_SER} x {DISC_PAR} nested {DISC['sku']} ({DISC['D']:.0f} OD, {DISC['f']:.0f} N flat): "
                f"pull {pull:.0f} N -> clamp {lo:.0f}..{hi:.0f} N over disc tol "
                f"{DISC_TOL[0] * 100:+.1f}/{DISC_TOL[1] * 100:+.0f} % and ramp mu {MU_RAMP[0]}..{MU_RAMP[1]} "
                f"(slip {LD['n_slip']:.0f}, x{lo / LD['n_slip']:.2f}; {lo_raw:.0f} before the wall's friction mu {WALL_MU})"))
    out.append(("head stack: strongest clamp <= ceiling (OPEN: bench test)", hi <= N_CEIL,
                f"{hi:.0f} N vs N_CEIL {N_CEIL:.0f}"))
    # the stop: torque per degree jumps by (k_ax + k_disc) / k_disc when the stack goes flat
    k_disc = pull / (DISC_SER * (DISC["h"] - DISC["t"]))
    out.append(("head stack: stop jump (feel) >= 2x", True, ""))     # filled below
    rows = []
    for k_lift in (K_LIFT_LOOP, 2 * K_LIFT_LOOP, 4 * K_LIFT_LOOP):
        k_ax = k_lift * TAN * ramp_factor(sum(MU_RAMP) / 2)
        rows.append(f"loop {k_lift / 1000:.0f} kN/mm -> {1 + k_ax / k_disc:.1f}x")
    k_ax = K_LIFT_LOOP * TAN * ramp_factor(sum(MU_RAMP) / 2)
    out[-1] = ("head stack: stop jump (feel) >= 2x", 1 + k_ax / k_disc >= 2.0,
               f"stack {k_disc:.0f} N/mm vs the loop seen at the screw {k_ax:.0f} N/mm: "
               + "; ".join(rows) + f"; {DISC_SER * (DISC['h'] - DISC['t']) / 0.5 * 360:.0f} deg of key from touch to flat")
    xs = [jaw_resultant(X_L, n) for n in (lo, hi)]
    out.append(("jaw reaction in its middle third (full contact)",
                all(abs(x - LAY["XJC"]) <= JAW_L / 6 for x in xs),
                f"push x {X_L:.1f}; reaction x {xs[0]:.1f}..{xs[1]:.1f} for {lo:.0f}..{hi:.0f} N "
                f"(jaw centre {LAY['XJC']:.1f}, third +-{JAW_L / 6:.1f})"))
    th = (hi + LD["v"]) * (math.tan(math.radians(ALPHA)) + MU_RAMP[1])
    out.append(("GREEN's X stop: nub on the head plate", True,
                f"up to ~{th:.0f} N -X from the ramp at the strongest clamp, taken {NUB_DZ} above the screw "
                f"axis; couple vs the pad shifts the jaw reaction {th * (Z_FOOT - Z_SCREW - NUB_DZ) / hi:+.1f} mm"))
    sig_n = 6 * th / PITCH * NUB_DZ / LIP_T ** 2
    out.append(("head plate between screw and nub <= 0.6 x 304 yield", sig_n <= 0.6 * YIELD["304 annealed"],
                f"{sig_n:.0f} MPa ({th:.0f} N a string, {NUB_DZ} apart)"))
    out.append(("tie standoffs spread", SO_DX >= 10, f"{SO_DX:.1f} apart in X at x {X_TIES[0]:.1f} / {X_TIES[1]:.1f}"))
    out.append(("standoff counterbore in the floor", 0 <= SO_CBORE <= FLOOR_H - 6,
                f"{SO_CBORE:.2f} deep, D{SO_CBORE_D} ({SO_L} standoff, shoe at its {SHOE_H0_MIN} min)"))
    out.append(("head stack fits the pitch", DISC["D"] + 0.4 <= PITCH, f"Ø{DISC['D']} at {PITCH}"))
    # lip: a cantilever off the floor bar, the screw's pull at Z_SCREW - ZF above its root
    m = pull * (1 + DISC_TOL[1]) / PITCH * (Z_SCREW - ZF)
    sig = m / (LIP_T ** 2 / 6)
    out.append(("head plate bending <= 0.6 x 304 yield", sig <= 0.6 * YIELD["304 annealed"],
                f"{sig:.0f} MPa, {LIP_T} thick, {Z_LIP_TOP - ZF:.1f} above the floor's end face (stack, all ten at once: "
                f"{10 * pull * (1 + DISC_TOL[1]) / 1000:.1f} kN)"))
    return out


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
    k_loop = 1 / (1 / K_BLADE + 1 / K_LIFT_LOOP)
    if SPRING == "head":       # the stack, reflected through the wedge, is in series with the loop
        k_disc = DISC_PAR * DISC["f"] / (DISC_SER * (DISC["h"] - DISC["t"]))
        k_loop = 1 / (1 / K_LIFT_LOOP + TAN * ramp_factor(sum(MU_RAMP) / 2) / k_disc)
        out += head_checks()
    # flexure, both materials
    for mat, y in (YIELD.items() if SPRING == "blade" else ()):
        tb = math.sqrt(6 * LD["lift_max"] * LF / (T_PL * SIGMA_FRAC * y))
        k = E * T_PL * tb ** 3 / (4 * LF ** 3)
        out.append((f"blade in {mat}", mat == BLADE_MAT or k < 5000,
                    f"depth {tb:.1f}, k {k / 1000:.1f} kN/mm"
                    + ("  <- chosen" if mat == BLADE_MAT else "  (no softer than the plain loop: no gain)")))
    if SPRING == "blade":
        out.append(("blade", True, f"{LF:.1f} long x {TB:.2f} deep, k {K_BLADE / 1000:.2f} kN/mm "
                f"(loop {k_loop / 1000:.2f}); {DELTA_MAX:.2f} mm at {LD['lift_max']:.0f} N; slot {SLOT} = stop"))
    # jaw arm stiffness: the blade's root moment crosses it to reach the jaw (no blade: no moment)
    I_arm = T_PL * JAW_D ** 3 / 12 if SPRING == "blade" else math.inf
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
    if SPRING == "head":
        f_ax = DISC_PAR * DISC["f"] * (1 + DISC_TOL[1])
    out.append(("M3 axial at the top of the window", f_ax < 0.5 * 2260,
                f"{f_ax:.0f} N (A2-70 proof 2260), ~{0.2 * f_ax * 0.003:.2f} N.m"))
    if SPRING == "blade":
        per_turn = 0.5 * TAN * k_loop
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
    # bars: all ten at the strongest clamp (head: disc +tol and the slickest ramp, not the 900 crush figure)
    n_top = LD["n_max"]
    if SPRING == "head":
        n_top = DISC_PAR * DISC["f"] * (1 + DISC_TOL[1]) / ramp_factor(MU_RAMP[0]) - LD["v"]
    w = 10 * n_top
    d_b, d_s, d_i = bar_bow(w, LAY["DATUM_X"][1] - LAY["DATUM_X"][0], DATUM_H)
    f_b, f_s, f_i = bar_bow(w + 10 * LD["v"], floor_b(), FLOOR_H)      # the block as drawn, not FLOOR_W
    f_lv, st_lv, bw_lv = bar_level_force(n_top, DATUM_H)
    out.append((f"datum: extra bar force to level at fret 1 <= {BAR_LEVEL_MAX} N", f_lv <= BAR_LEVEL_MAX,
                f"{f_lv:.2f} N (worst step {st_lv * 1000:.0f} um at fret 1, bow {bw_lv * 1000:.0f} um) at all ten = "
                f"{w / 1000:.1f} kN"))
    out.append(("datum stress <= 0.8 yield", d_s <= 0.8 * 205, f"{d_s:.0f} MPa"))
    out.append(("floor stress <= 0.8 yield", f_s <= 0.8 * 205, f"{f_s:.0f} MPa, bow {f_b * 1000:.0f} um"))
    c = SPAN ** 3 / (48 * E) * (1 / d_i + 1 / f_i)
    r = c * k_loop
    if SPRING == "blade":
        out.append(("neighbour unloads < 5% / string", r < 0.05,
                    f"{r * 100:.1f}% each; worst after one pass ~{6 * r * 100:.0f}%, after two ~{(6 * r) ** 2 * 100:.0f}%"))
    else:                      # tighten-to-flat resets each string; the weakest clamp after pass two must hold
        lo = (DISC_PAR * DISC["f"] * (1 + DISC_TOL[0]) / ramp_factor(MU_RAMP[1]) - LD["v"])
        wk, ls = tighten_passes(k_loop)
        wk1, _ = tighten_passes(k_loop, passes=TIGHTEN_PASSES - 1)
        out.append((f"{TIGHTEN_PASSES} tightening passes: weakest clamp still >= slip", wk >= LD["n_slip"],
                    f"{wk:.0f} N after {TIGHTEN_PASSES} (worst loss {ls:.0f}; {wk1:.0f} after {TIGHTEN_PASSES - 1}); "
                    f"slip {LD['n_slip']:.0f}; simulated 1 -> 10, both bars' influence, loop {k_loop / 1000:.1f} kN/mm"))
    end_load = (w + 10 * LD["v"]) / 2
    if TIES == "z":
        a_so = math.sqrt(3) / 2 * SO_HEX ** 2 - math.pi * (TS["tap"] / 2) ** 2
        k_end = 2 * E * a_so / SO_L
        per = end_load / 2
        out.append(("Z ties: standoff stretch (common to every string) <= 0.03", end_load / k_end <= 0.03,
                    f"{end_load / 1000:.1f} kN an end on 2 standoffs {TIE_SIZE} F-F {SO_HEX} hex x {SO_L}: "
                    f"{end_load / k_end * 1000:.0f} um"))
        out.append((f"Z tie screw: preload 1.15 x its load <= 0.75 proof ({TS['proof'] / 1000:.1f} kN)",
                    1.15 * per <= 0.75 * TS["proof"],
                    f"{per / 1000:.2f} kN each -> preload ~{per * 1.15 / 1000:.1f} kN, "
                    f"~{0.2 * per * 1.15 * TS['d'] / 1000:.1f} N.m; {TIE_SIZE}x{Z_SCREW_L} {TS['kind']}, thread top "
                    f"{Z_SCREW_L - (DATUM_H - DATUM_CBORE[1]):.1f} / bottom {Z_SCREW_L - (FLOOR_H - SO_CBORE):.1f} into the standoff"))
        e_top, e_bot = Z_SCREW_L - (DATUM_H - DATUM_CBORE[1]), Z_SCREW_L - (FLOOR_H - SO_CBORE)
        out.append(("tie threads: >= 1.5 d in, ends meet nowhere in the standoff",
                    min(e_top, e_bot) >= 1.5 * TS["d"] and e_top + e_bot <= SO_L - 2,
                    f"{e_top:.1f} + {e_bot:.1f} of {SO_L}"))
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
    if SPRING == "blade":
        blade_x0 = X_L - FOOT_W / 2 - 1.0
        body = body.union(_box(blade_x0, X_FRONT, Z_BLADE_BOT, Z_BODY_BOT))   # blade + root, slot cut next
        body = body.cut(_box(blade_x0 - 1, X_ROOT, Z_BLADE_TOP, Z_BODY_BOT))
    if SPRING == "head":   # underside = the ramp's incline, PAD_RELIEF clear of it; only the pad touches
        zr = lambda x: Z_FOOT + (x - X_L) * TAN + PAD_RELIEF
        z_lo = zr(xj0) - 1
        body = body.union(_box(xj0, X_FRONT, z_lo, Z_BODY_BOT + 0.01))
        body = body.cut(_xz([(xj0 - 1, zr(xj0 - 1)), (X_FRONT + 1, zr(X_FRONT + 1)),
                             (X_FRONT + 1, z_lo - 5), (xj0 - 1, z_lo - 5)], 0.0, T_PL + 1))
        # -X end: the jaw arm overhangs the head plate; below it only a nub reaches the plate (X stop).
        # GREEN sits g lower for gauge g (and THREAD_CLR more when open): the overhang clears the plate
        # top at the lowest, the nub is centred for the mid gauge
        drop = G_HI + THREAD_CLR
        if X_WALL_IN + PAD_RELIEF > xj0 - 1:     # plate face inside GREEN's -X end: overhang the plate
            body = body.cut(_box(xj0 - 1, X_WALL_IN + PAD_RELIEF, z_lo - 5, Z_LIP_TOP + drop + 0.5, 0.0, T_PL + 1))
        zn = Z_SCREW + NUB_DZ + 0.5 * (G_LO + G_HI)
        body = body.union(_box(X_WALL_IN, max(xj0, X_WALL_IN + PAD_RELIEF) + 1.0, zn - NUB_H / 2, zn + NUB_H / 2))
    # crowned foot: tangent at X_L with slope ALPHA (rising +X)
    n = (-math.sin(math.radians(ALPHA)), math.cos(math.radians(ALPHA)))
    cen = (X_L + RF * n[0], Z_FOOT + RF * n[1])
    foot = _box(X_L - FOOT_W / 2, X_L + FOOT_W / 2, Z_FOOT - 3,
                (Z_FOOT + FOOT_W * TAN + PAD_RELIEF + 0.5) if SPRING == "head" else Z_BLADE_BOT + 0.01)
    foot = foot.intersect(cq.Workplane("XZ").center(*cen).circle(RF).extrude(T_PL, both=True))
    return body.union(foot).translate((0, y0, dz))


def shoe(s, y0=0.0):
    pts = [(s, ZF), (s + SHOE_L, ZF), (s + SHOE_L, ZF + SHOE_H0 + SHOE_L * TAN), (s, ZF + SHOE_H0)]
    p = _xz(pts, y0)
    p = p.cut(_box(s - 1, s + SLOT_END_U, Z_SCREW - SLOT_W / 2, Z_SCREW + SLOT_W / 2, y0, T_PL + 1))
    p = p.cut(_box(s + NUT_U, s + NUT_U + NUT_M + 0.1, Z_SCREW - (NUT_S + 0.1) / 2, Z_SCREW + (NUT_S + 0.1) / 2, y0, T_PL + 1))
    return p


def screw(y0):
    """The clamp screw, ISO 4762 M3 x SCREW_L, head on the disc stack, through cadkit's headed screw
    (socket and thread drawn, the instrument's every screw alike)."""
    from src.motor_coupler import cap_screw
    assert (SCREW_D, HEAD_D, HEAD_H) == (3.0, 5.5, 3.0), "cap_screw('m3') is ISO 4762 M3"
    return cap_screw("m3", SCREW_L, (X_HEAD - HEAD_H, y0, Z_SCREW), (1.0, 0.0, 0.0))


def discs(y0):
    """The head stack, flat (the clamped state): DISC_SER x DISC_PAR separate discs, -X to +X."""
    out, t = [], DISC["t"]
    for k in range(DISC_SER * DISC_PAR):
        out.append(cq.Workplane("YZ").circle(DISC["D"] / 2).circle(DISC["d"] / 2).extrude(t)
                   .translate((X_HEAD + k * t, y0, Z_SCREW)))
    return out


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


def floor_b():
    """The floor block's real width in X (head mode: head plate to past the shoes, ~37), its bending b."""
    x0, x1, _, _ = _floor_sec()
    return x1 - x0


def _floor_sec():
    if SPRING == "head":   # a plain block from the head plate to past the shoes' furthest +X end
        return X_WALL_IN, max(X_L + FLOOR_W / 2, S_MAX + SHOE_L + 1.0), ZF - FLOOR_H, ZF
    return X_L - FLOOR_W / 2, X_L + FLOOR_W / 2, ZF - FLOOR_H, ZF


def datum():
    x0, x1, z0, z1 = _datum_sec()
    b = cq.Workplane("XY").box(x1 - x0, _bar_y(), z1 - z0, centered=(False, True, False)).translate((x0, 0, z0))
    b = b.edges("|Y").edges(cq.selectors.NearestToPointSelector((x1, 0, z0))).fillet(RD)
    if TIES == "z" and DATUM_CBORE:
        for y in (-Y_TIE, Y_TIE):
            for x in X_TIES:
                b = b.cut(cq.Workplane("XY").center(x, y).circle(DATUM_CBORE[0] / 2).extrude(DATUM_CBORE[1] + 1)
                          .translate((0, 0, z1 - DATUM_CBORE[1])))
    return b.cut(_tie_holes(_datum_sec())) if TIES != "z" else b.cut(_z_holes(z0, z1))


def floor_bar():
    x0, x1, z0, z1 = _floor_sec()
    b = cq.Workplane("XY").box(x1 - x0, _bar_y(), z1 - z0, centered=(False, True, False)).translate((x0, 0, z0))
    if SPRING == "head":
        for y in (-Y_TIE, Y_TIE):                 # standoff counterbores
            for x in X_TIES:
                b = b.cut(cq.Workplane("XY").center(x, y).circle(SO_CBORE_D / 2).extrude(SO_CBORE + 1)
                          .translate((0, 0, z1 - SO_CBORE)))
    return b.cut(_tie_holes(_floor_sec())) if TIES != "z" else b.cut(_z_holes(z0, z1))


def head_plate():
    """6 mm 304, laser-cut with every hole: the screw heads (on their disc stacks) push it +X flat
    onto the floor bar's -X end face, so the clamp load is bearing, steel on steel. No screws hold it
    (user 2026-11-20): the printed housing locates it, so the floor block keeps Z-only holes."""
    b = cq.Workplane("XY").box(LIP_T, _bar_y(), Z_LIP_TOP - (ZF - FLOOR_H), centered=(False, True, False)) \
        .translate((X_HEAD_BEAR, 0, ZF - FLOOR_H))
    for i in range(D.N_STRINGS):
        b = b.cut(cq.Workplane("YZ").center(D.nut_y(i), Z_SCREW).circle(3.4 / 2).extrude(LIP_T + 2)
                  .translate((X_HEAD_BEAR - 1, 0, 0)))
    return b


def _z_holes(z0, z1, d=TS["clr"]):
    """Plain clearance holes, drilled through along Z (the threads are the standoffs')."""
    out = None
    for y in (-Y_TIE, Y_TIE):
        for x in X_TIES:
            h = cq.Workplane("XY").center(x, y).circle(d / 2).extrude(z1 - z0 + 2).translate((0, 0, z0 - 1))
            out = h if out is None else out.union(h)
    return out


def standoff(x, y):
    """M3 female-female steel hex standoff, SO_L long: datum underside to the floor (its counterbore)."""
    rot = 30.0 if SPRING == "head" else 0.0              # head: a flat faces +X (its pocket's bearing face)
    return (cq.Workplane("XY").center(x, y).transformed(rotate=(0, 0, rot))
            .polygon(6, SO_HEX / math.cos(math.pi / 6)).extrude(SO_L)
            .cut(cq.Workplane("XY").center(x, y).circle(TS["tap"] / 2).extrude(SO_L))
            .translate((0, 0, ZF - SO_CBORE)))


def z_screw(x, y, top):
    """Tie screw (TIE_SIZE x Z_SCREW_L): from the datum top (top) or the floor bottom, into the standoff."""
    from src.motor_coupler import cap_screw              # cadkit's headed screw: head and thread drawn
    kind = {"M3": "m3", "M4": "m4"}[TIE_SIZE]               # m3: ISO 4762; m4: ISO 7380 button (TIE_SPECS)
    if top:
        z_face = LAY["ZD"] + DATUM_H - (DATUM_CBORE[1] if DATUM_CBORE else 0.0)
        return cap_screw(kind, Z_SCREW_L, (x, y, z_face + TS["head_h"]), (0.0, 0.0, -1.0))
    z_face = ZF - FLOOR_H
    return cap_screw(kind, Z_SCREW_L, (x, y, z_face - TS["head_h"]), (0.0, 0.0, 1.0))


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
    if SPRING == "head":
        parts += [("nf_plate", head_plate())]
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
        if SPRING == "head":
            parts += [(f"nf_disc_{i}_{k}", d) for k, d in enumerate(discs(y))]
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
    if SPRING == "blade":
        ax.text(LAY["XJ0"] + 1, Z_BODY_BOT + 3, f"GREEN ({BLADE_MAT}, 4 mm): jaw {JAW_L:.0f} long, crown, blade", color=COL["green"], fontsize=9)
        ax.text(LAY["XJ0"] + 1, Z_BLADE_BOT - 1.6, f"blade {LF:.0f} x {TB:.1f}, slot {SLOT}", color=COL["green"], fontsize=8)
    else:
        ax.text(LAY["XJ0"] + 1, Z_BODY_BOT + 3, f"GREEN (304, 4 mm, rigid): jaw {JAW_L:.0f} long, crown", color=COL["green"], fontsize=9)
        for d in discs(0):
            outline(ax, d, "#e0c060", 1.0)
    ax.text(S_MIN - 2, ZF + SHOE_H0 + SHOE_L * TAN + 1.5, f"SHOE {ALPHA} deg", color=COL["shoe"], fontsize=9)
    ax.text(X_L - FLOOR_W / 2, ZF - FLOOR_H - 3, f"FLOOR bar {FLOOR_W:.0f} x {FLOOR_H:.0f}", color=COL["floor"], fontsize=9)
    ax.text(X_HEAD_BEAR - 12, Z_SCREW - 6, f"M3x{SCREW_L} SHCS,\nhead held in the print" if SPRING == "blade" else f"M3x{SCREW_L} SHCS,\n{DISC_SER}x{DISC_PAR} discs on the floor lip", color=COL["screw"], fontsize=8)
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
