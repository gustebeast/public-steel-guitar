"""Purchased-component DUMMIES — schematic solids for the assembly only.

These are NOT exported as printable STEPs; they exist so the assembly shows where
the bought parts sit relative to the printed parts. Each is built in a canonical
local frame; build.py translates copies into each string's position.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, cyl_y, box_at

from cadkit.fasteners import M2, cut_selftap
from cadkit.threads import threaded_rod
from cadkit.fasteners import set_screw, m4_insert                # the ONE dummies now live in cadkit/fasteners.py;
# re-exported here so C.set_screw() / C.m4_insert() keep working across the project

# PER-PART NOZZLE. The two GT2 pulleys are the only PRINTED parts in this module of
# dummies, and they need the fine nozzle twice over: 2 mm tooth pitch, and a 0.3 mm
# pilot-thread groove that 0.8 would smear into a smooth bore. (screw_collar used to
# carry this declaration for the pair of them; it is gone, so it lives here now.)
NOZZLE_D = 0.2

MOTOR_PULLEY_STANDOFF = 14.0   # pulley sits this far +Y of the motor faceplate


# ── Vertical leadscrew (axis Z) ──────────────────────────────────────────
def screw(length: float = D.SCREW_LEN) -> cq.Workplane:
    """Leadscrew, axis +Z, base face at z=0. (Threads not modelled.)"""
    return cyl(D.SCREW_OD, length, z=0.0)


# ── Leadscrew nut (H-type brass flange nut, axis Z) ──────────────────────
def nut() -> cq.Workplane:
    """H-type brass leadscrew nut, axis Z, mounted FLANGE UP / BOSS DOWN.

    THIS PART IS THE CARRIAGE. Its +X ear anchors the string (ball end
    underneath) and its -X ear rides the guide rod; nothing else moves. Origin =
    the flange's TOP face, so the flange hangs the first NUT_FLANGE_T below it and
    the boss the rest — see dimensions' MOUNTING note for why flange-up. The flange is the round
    Ø20 disc with two flats milled tangent to the boss (that IS the "H"), so it
    is modelled as the intersection of the disc and an AF-wide slab — which is
    what puts the long ends' ROUNDED profile in the assembly, the thing that
    decides how far the ears sweep. Two Ø3 ears carry the M2 mounting screws.
    DEMO/purchased — and every dimension is a guess until the part arrives
    (see dimensions.NUT_AF).
    """
    z0 = -D.NUT_FLANGE_T
    disc = cyl(D.NUT_FLANGE_L, D.NUT_FLANGE_T, z=z0)            # ends stay round
    slab = box_at(D.NUT_FLANGE_L + 2, D.NUT_AF, D.NUT_FLANGE_T,
                  x=0, y=0, z=z0 + D.NUT_FLANGE_T / 2)
    out = disc.intersect(slab)
    out = out.union(cyl(D.NUT_BOSS_D, D.NUT_BOSS_L,               # boss hangs -Z
                        z=z0 - D.NUT_BOSS_L))
    out = out.cut(cyl(D.SCREW_OD, D.NUT_H + 2, z=z0 - D.NUT_BOSS_L - 1))   # thread bore
    for sx in (-1, 1):                                           # the two ears
        out = out.cut(cyl(D.NUT_HOLE_D, D.NUT_FLANGE_T + 2, z=z0 - 1)
                      .translate((sx * D.NUT_HOLE_DX, 0, 0)))
    return out


# ── String-end nut (swaged cylinder on the string's bridge end) ──────────
# A cylinder crimped on the string end (axis Y, crosswise). It slots into the
# carriage anchor; the string runs +Z out of it to the bridge bearing, and the
# +Z string pull seats it up under the anchor roof. DEMO ONLY (purchased/swaged).
def string_nut() -> cq.Workplane:
    """String-end cylinder fitting, axis Y, centred at the origin."""
    return cyl_y(D.STRING_NUT_D, D.STRING_NUT_L, y0=-D.STRING_NUT_L / 2, x=0.0, z=0.0)


# ── Nut-block hardware (Ø2 steel dowel + M4 cup-tip set screw) — DEMO ─────
def dowel() -> cq.Workplane:
    """Ø2×4 steel dowel (axis Y) — the gauged break pin. Short so it drops into
    its top-open slot from above (the string then traps it)."""
    return cyl_y(2.0, 4.0, y0=-2.0, x=0.0, z=0.0)


# (set_screw() and m4_insert() moved to freecad/fasteners.py -- imported above so every project shares
#  the SAME dummy geometry, not just the dimensions.)


_CHAMFER = (D.PULLEY_FLANGE_OD - D.PULLEY_OD) / 2     # 45° flange chamfer height


def _cone(r1, r2, h, pnt, d):
    return cq.Workplane("XY").add(cq.Solid.makeCone(r1, r2, h, pnt, d))


# GT2 14-tooth pulley grooves: 14 rounded valleys at 2 mm pitch on the pitch circle
# (PD = 14·2/π = 8.91 mm), BELT_TOOTH_H deep, cut into the toothed band between the
# flanges. The cutter cylinders sit on a radius that puts the valley floor at
# OD/2 − tooth height with a GT2-ish rounded bottom (radius _GROOVE_R).
_N_TEETH  = 14
_GROOVE_R = 0.55
_GROOVE_RC = D.PULLEY_OD / 2 - D.BELT_TOOTH_H + _GROOVE_R


def _tooth_cutter(axis: str, lo: float = None, length: float = None):
    """Union of the 14 groove-cutting cylinders, axis 'Z' (screw) or 'Y' (motor),
    spanning the toothed band between the two flanges."""
    if lo is None:
        lo = -D.PULLEY_W / 2 + D.PULLEY_FLANGE_T
    if length is None:
        length = D.PULLEY_W - D.PULLEY_FLANGE_T - _CHAMFER
    tool = None
    for k in range(_N_TEETH):
        a = 2 * math.pi * k / _N_TEETH
        u, v = _GROOVE_RC * math.cos(a), _GROOVE_RC * math.sin(a)
        g = (cyl(2 * _GROOVE_R, length, z=lo).translate((u, v, 0)) if axis == "Z"
             else cyl_y(2 * _GROOVE_R, length, y0=lo, x=u, z=v))
        # CAP THE FAR END AT 45°. A plain cylinder leaves the groove ending in a flat
        # ceiling — 14 little 0.68 mm² lids per pulley, unsupported in a flange-down
        # print. Tapering the cutter to a point closes each groove at 45° instead, and
        # costs nothing: the belt only ever engages the parallel part below.
        if axis == "Z":
            g = g.union(_cone(_GROOVE_R, 0.0, _GROOVE_R,
                              cq.Vector(u, v, lo + length), cq.Vector(0, 0, 1)))
        tool = g if tool is None else tool.union(g)
    return tool


# ── Screw drive pulley (axis Z) ──────────────────────────────────────────
def screw_pulley(col_h: float = 0.0) -> cq.Workplane:
    """Screw drive pulley, origin at the TOOTHED BAND'S CENTRE. TWO SKUs, told apart
    by `col_h` alone: 0 for the high plane, BELT_PLANE_DZ for the low one.

    It is also the retaining collar. Its pilot-thread bore grips the rod and the
    string's 147 N jams the boss on top up into the thrust bearings, so it needs no
    set screw, no clamp and no separate collar. Both SKUs' bosses land on the SAME
    thrust plane while their bands sit BELT_PLANE_DZ apart — which is the whole job
    of the column, and why it is exactly that and not a tuned number.

    PRINTS FLANGE-DOWN, no brim, no support: the full Ø11 bottom flange is the bed
    face, and everything above it steps INWARD except the top flange, which is a 45°
    cone. (A single part that flipped to serve both planes was tried and dropped —
    it could only stand on a Ø5.6 boss, and a solid bed surface is worth more than
    the thread engagement it levelled. The short SKU's 8.3 mm is 2.5 MPa under load,
    ~10% of interlayer, so the engagement was never the constraint.)
    """
    g, cn = D.PULLEY_GAP, D.PULLEY_CONE
    out = cyl(D.PULLEY_FLANGE_OD, D.PULLEY_FLANGE_T,             # BED FACE: full flange
              z=-g / 2 - D.PULLEY_FLANGE_T)
    out = out.union(cyl(D.PULLEY_OD, g, z=-g / 2))               # toothed band
    out = out.union(_cone(D.PULLEY_OD / 2, D.PULLEY_FLANGE_OD / 2, cn,
                          cq.Vector(0, 0, g / 2), cq.Vector(0, 0, 1)))   # 45° top flange
    top = g / 2 + cn
    if col_h > 0.0:                                              # the low SKU's column
        out = out.union(cyl(D.PULLEY_SPACER_D, col_h, z=top))
        top += col_h
    out = out.union(cyl(D.PULLEY_BOSS_D, D.PULLEY_BOSS_H, z=top))
    top += D.PULLEY_BOSS_H

    out = out.cut(_tooth_cutter("Z", lo=-g / 2, length=g))       # 14 GT2 grooves
    # PILOT THREAD, full height: the bore prints as a shallow female helix and the
    # Tr5×1 rod swages the last 0.1 going in. It is the torque path AND the retention.
    bot = -g / 2 - D.PULLEY_FLANGE_T
    _h = int(top - bot) + 4                                      # whole turns, past both
    out = out.cut(threaded_rod(D.FORM_MINOR, D.FORM_MAJOR, D.SCREW_PITCH, _h,
                               z=bot - 2, overshoot=0.05, bevel_ends=False), clean=False)
    _li = 0.4                                                    # lead-in, both ends
    for zc, d0, d1 in ((bot - 0.01, D.FORM_MAJOR + 2 * _li, D.FORM_MAJOR),
                       (top - _li, D.FORM_MAJOR, D.FORM_MAJOR + 2 * _li)):
        out = out.cut(_cone(d0 / 2, d1 / 2, _li + 0.01,
                            cq.Vector(0, 0, zc), cq.Vector(0, 0, 1)), clean=False)
    return out


# ── Motor pulley (axis Y) ────────────────────────────────────────────────
def motor_pulley() -> cq.Workplane:
    """Flanged GT2 pulley on the motor shaft, axis Y, centred at y=0. Full flange
    on the −Y (motor) side, 45°-chamfered flange on +Y (printable cone)."""
    w, ft = D.PULLEY_W, D.PULLEY_FLANGE_T
    out = (cyl_y(D.PULLEY_OD, w, y0=-w / 2)
           .union(cyl_y(D.PULLEY_FLANGE_OD, ft, y0=-w / 2))             # full −Y flange
           .union(_cone(D.PULLEY_OD / 2, D.PULLEY_FLANGE_OD / 2, _CHAMFER,
                        cq.Vector(0, w / 2 - _CHAMFER, 0), cq.Vector(0, 1, 0))))   # 45° +Y
    out = out.cut(_tooth_cutter("Y"))                                # 14 GT2 grooves
    return out.cut(cyl_y(D.PULLEY_BORE_MOTOR, w + 2, y0=-w / 2 - 1))


# ── Screw thrust bearing (axis Z) ────────────────────────────────────────
def support_bearing() -> cq.Workplane:
    """ONE MR85ZZ deep-groove ball bearing, axis Z, centred z=0. Two of these go
    on each screw in TANDEM — build.py stacks them; see dimensions.SUPPORT_BRG_N
    for why two and why not preloaded. (The purchased LOCKNUT that used to sit
    under them is gone: the printed screw_collar retains the screw now.)"""
    o = cyl(D.MR85_OD, D.MR85_W, z=-D.MR85_W / 2)
    return o.cut(cyl(D.MR85_ID, D.MR85_W + 2, z=-D.MR85_W / 2 - 1))


# ── Motor: MKS SERVO42D, lies flat, shaft +Y ─────────────────────────────
def motor() -> cq.Workplane:
    """SERVO42D, shaft along +Y. Reference = the pulley plane (y=0): faceplate at
    y=−STANDOFF, motor body + PCB extend −Y (toward the player); the 5 mm shaft +
    Ø22 pilot poke +Y. Centred on X=Z=0."""
    s = MOTOR_PULLEY_STANDOFF
    body = box_at(D.MOTOR_SQ, D.MOTOR_BODY_LEN, D.MOTOR_SQ,
                  x=0, y=-s - D.MOTOR_BODY_LEN / 2, z=0)
    pcb = box_at(D.MOTOR_SQ - 6, D.MOTOR_PCB_LEN, D.MOTOR_SQ - 6,
                 x=0, y=-s - D.MOTOR_BODY_LEN - D.MOTOR_PCB_LEN / 2, z=0)
    pilot = cyl_y(D.NEMA17_PILOT_D, 2.0, y0=-s)                 # boss at faceplate
    shaft = cyl_y(D.MOTOR_SHAFT_D, s + 4.0, y0=-s)             # shaft to past pulley
    return body.union(pcb).union(pilot).union(shaft)


# ── Guide rod (axis Z) ───────────────────────────────────────────────────
def guide_rod(length: float) -> cq.Workplane:
    """Hardened steel rod, axis +Z, base face at z=0."""
    return cyl(D.GUIDE_ROD_D, length, z=0.0)


# ── Bridge bearings — one ball bearing per string on a shared axle ───────
def bridge_bearings() -> cq.Workplane:
    """A shared axle (axis Y) at (BRIDGE_AXLE_X, BRIDGE_BEARING_Z) carrying one
    freely-spinning ball bearing per string; each string rises tangent to the
    bearing's +X extent and wraps 90° over the top. A spinning bearing keeps the
    bend near-frictionless so the two sides' tensions equalize. Built in global
    position; bearing tops at STRING_Z."""
    x, z = D.BRIDGE_AXLE_X, D.BRIDGE_BEARING_Z
    out = cyl_y(D.BRIDGE_AXLE_D, 2 * D.BRIDGE_AXLE_Y, y0=-D.BRIDGE_AXLE_Y, x=x, z=z)
    for i in range(D.N_STRINGS):
        y0 = D.string_y(i) - D.BRIDGE_BEARING_W / 2
        brg = cyl_y(D.BRIDGE_BEARING_OD, D.BRIDGE_BEARING_W, y0=y0, x=x, z=z)
        brg = brg.cut(cyl_y(D.BRIDGE_AXLE_D + 0.3, D.BRIDGE_BEARING_W + 2,
                            y0=y0 - 1, x=x, z=z))
        out = out.union(brg)
    return out


_FLAT_LEN = 42.0            # flat (untwisting) belt zone near the motor end of run B
_CLAMP_DIST = 24.0         # clamp centre distance from the motor (clears the pulley)
_AUX_OFF = 3.0             # auxiliary-spine offset that drives the sweep twist
_SAMPLE_DIV = 12.0         # run sample spacing (smaller = denser)


def _belt_samples(motor_xyz, screw_xyz):
    """Loop centreline as a list of (point, inward-normal n). n tracks the toothed
    face and returns to itself (orientable). Run B carries a FLAT zone near the
    motor (n held = +Z) so the splice clamp grips a non-twisting section."""
    V = cq.Vector
    M, S = V(*motor_xyz), V(*screw_xyz)
    r = D.PULLEY_OD / 2 + D.BELT_T / 2
    m_top, m_bot = V(M.x, M.y, M.z + r), V(M.x, M.y, M.z - r)
    s_py, s_my = V(S.x, S.y + r, S.z), V(S.x, S.y - r, S.z)

    def lerp(a, b, t):
        return a.add(b.sub(a).multiply(t))

    samples, NW = [], 12
    NA = max(8, int(s_py.sub(m_top).Length / _SAMPLE_DIV))
    for k in range(NA):                               # run A: n −Z → −Y
        a = (k / NA) * math.pi / 2
        samples.append((lerp(m_top, s_py, k / NA), V(0, -math.sin(a), -math.cos(a))))
    for k in range(NW):                               # screw wrap (+X side)
        phi = math.radians(90 - 180 * k / NW)
        samples.append((V(S.x + r * math.cos(phi), S.y + r * math.sin(phi), S.z),
                        V(-math.cos(phi), -math.sin(phi), 0)))
    L_B = m_bot.sub(s_my).Length                      # run B: +Y → +Z, flat near motor
    flat = min(0.45, _FLAT_LEN / L_B)
    NB = max(8, int(L_B / _SAMPLE_DIV))
    for k in range(NB):
        t = k / NB
        if t < 1 - flat:
            a = (t / (1 - flat)) * math.pi / 2
            samples.append((lerp(s_my, m_bot, t), V(0, math.cos(a), math.sin(a))))
        else:
            samples.append((lerp(s_my, m_bot, t), V(0, 0, 1)))   # flat splice zone
    for k in range(NW):                               # motor wrap (−X side)
        th = math.radians(270 - 180 * k / NW)
        samples.append((V(M.x + r * math.cos(th), M.y, M.z + r * math.sin(th)),
                        V(-math.cos(th), 0, -math.sin(th))))
    return samples


def splice_frame(motor_xyz, screw_xyz):
    """Placement for the splice clamp: a point in run B's flat zone with the belt's
    tangent and (flat) normal. Returns (origin, xDir=tangent, normal=n) tuples."""
    V = cq.Vector
    M, S = V(*motor_xyz), V(*screw_xyz)
    r = D.PULLEY_OD / 2 + D.BELT_T / 2
    m_bot, s_my = V(M.x, M.y, M.z - r), V(S.x, S.y - r, S.z)
    L_B = m_bot.sub(s_my).Length
    t = 1 - _CLAMP_DIST / L_B                          # clamp centre, clear of the pulley
    p = s_my.add(m_bot.sub(s_my).multiply(t))
    tan = m_bot.sub(s_my).normalized()
    n = V(0, 0, 1)
    n = n.sub(tan.multiply(n.dot(tan))).normalized()
    return (p.x, p.y, p.z), (tan.x, tan.y, tan.z), (n.x, n.y, n.z)


def _belt_smooth(samples):
    """Single smooth sweep of the strip profile along the loop centreline, the
    twist driven by an auxiliary spine (offset along the inward normal). One solid,
    no seams. (FreeCAD/OCC reads these fine; tight short loops can trip stricter
    STEP importers, so the single-sweep approach avoids them.)"""
    pts = [(p.x, p.y, p.z) for p, _ in samples]
    aux = [(p.x + n.x * _AUX_OFF, p.y + n.y * _AUX_OFF, p.z + n.z * _AUX_OFF)
           for p, n in samples]
    path = cq.Workplane("XY").spline(pts, periodic=True).wire()
    auxw = cq.Workplane("XY").spline(aux, periodic=True).wire()
    p0, n0 = samples[0]
    tan = samples[1][0].sub(p0).normalized()
    wd = n0.cross(tan).normalized()
    prof = cq.Workplane(cq.Plane(origin=(p0.x, p0.y, p0.z), xDir=(wd.x, wd.y, wd.z),
                                 normal=(tan.x, tan.y, tan.z))).rect(D.BELT_W, D.BELT_T)
    return prof.sweep(path, auxSpine=auxw, isFrenet=False).val()


def _belt_teeth_ridges(samples):
    """Rounded GT2 teeth: half-round ridges (cylinders along the width) every
    BELT_PITCH of arc on the inner face (+n)."""
    def lerp(a, b, t):
        return a.add(b.sub(a).multiply(t))
    ridges, n_pts, acc = [], len(samples), 0.0
    for k in range(n_pts):
        q0, m0 = samples[k]
        q1, m1 = samples[(k + 1) % n_pts]
        seg = q1.sub(q0)
        L = seg.Length
        if L < 1e-6:
            continue
        t_dir = seg.multiply(1.0 / L)
        d = 0.0
        while acc <= L - d + 1e-9:
            d += acc
            t = min(d / L, 1.0)
            pt = lerp(q0, q1, t)
            nn = lerp(m0, m1, t)
            nn = nn.sub(t_dir.multiply(nn.dot(t_dir)))
            acc = D.BELT_PITCH
            if nn.Length < 1e-6:
                continue
            nn = nn.normalized()
            ww = nn.cross(t_dir).normalized()
            base = pt.add(nn.multiply(D.BELT_T / 2 - 0.25))   # deep overlap → robust fuse
            c = base.sub(ww.multiply(D.BELT_W / 2))
            ridges.append(cq.Solid.makeCylinder(
                D.BELT_TOOTH_H, D.BELT_W, cq.Vector(c.x, c.y, c.z),
                cq.Vector(ww.x, ww.y, ww.z)))
        acc -= (L - d)
    return ridges


# ── GT2 belt — smooth twisted loop (both runs + 90° twist + pulley wraps) ─────
def belt(motor_xyz, screw_xyz, teeth: bool = False) -> cq.Workplane:
    """The belt loop wraps the motor pulley (axis Y) and screw pulley (axis Z), so
    its flat face twists 90° per run. A single smooth sweep (no seams), one solid.
    `teeth=True` fuses rounded GT2 teeth onto the inner face."""
    samples = _belt_samples(motor_xyz, screw_xyz)
    body = _belt_smooth(samples)
    if teeth:
        body = body.fuse(*_belt_teeth_ridges(samples))
    body = body.clean()
    solids = body.Solids()
    return cq.Workplane("XY").add(solids[0] if len(solids) == 1 else body)
