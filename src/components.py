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

MOTOR_PULLEY_STANDOFF = 14.0   # pulley sits this far +Y of the motor faceplate


# ── Vertical leadscrew (axis Z) ──────────────────────────────────────────
def screw(length: float = D.SCREW_LEN) -> cq.Workplane:
    """Leadscrew, axis +Z, base face at z=0. (Threads not modelled.)"""
    return cyl(D.SCREW_OD, length, z=0.0)


# ── Leadscrew nut (round brass, axis Z) ──────────────────────────────────
def nut() -> cq.Workplane:
    """Round brass nut, axis Z. Seat lip (−Z face) at z=0; body extends +Z."""
    lip = cyl(D.NUT_FLANGE_OD, D.NUT_FLANGE_T, z=0.0)
    body = cyl(D.NUT_OD, D.NUT_BODY_LEN, z=D.NUT_FLANGE_T)
    bore = cyl(D.SCREW_OD + 0.4, D.NUT_FLANGE_T + D.NUT_BODY_LEN + 2, z=-1.0)
    return lip.union(body).cut(bore)


# ── String-end nut (swaged cylinder on the string's bridge end) ──────────
# A cylinder crimped on the string end (axis Y, crosswise). It slots into the
# carriage anchor; the string runs +Z out of it to the bridge bearing, and the
# +Z string pull seats it up under the anchor roof. DEMO ONLY (purchased/swaged).
def string_nut() -> cq.Workplane:
    """String-end cylinder fitting, axis Y, centred at the origin."""
    return cyl_y(D.STRING_NUT_D, D.STRING_NUT_L, y0=-D.STRING_NUT_L / 2, x=0.0, z=0.0)


# ── Nut-block hardware (Ø2 steel dowel + M4 cup-tip set screw) — DEMO ─────
def dowel() -> cq.Workplane:
    """Ø2 steel dowel (axis Y) — the gauged break pin AND the clamp anvil."""
    return cyl_y(2.0, 5.0, y0=-2.5, x=0.0, z=0.0)


def set_screw() -> cq.Workplane:
    """M4×10 cup-tip set screw, axis Z, head/top at z=0 (extends −Z)."""
    return cyl(4.0, 10.0, z=-10.0)


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


def _tooth_cutter(axis: str):
    """Union of the 14 groove-cutting cylinders, axis 'Z' (screw) or 'Y' (motor),
    spanning the toothed band between the two flanges."""
    lo = -D.PULLEY_W / 2 + D.PULLEY_FLANGE_T
    length = D.PULLEY_W - D.PULLEY_FLANGE_T - _CHAMFER
    tool = None
    for k in range(_N_TEETH):
        a = 2 * math.pi * k / _N_TEETH
        u, v = _GROOVE_RC * math.cos(a), _GROOVE_RC * math.sin(a)
        g = (cyl(2 * _GROOVE_R, length, z=lo).translate((u, v, 0)) if axis == "Z"
             else cyl_y(2 * _GROOVE_R, length, y0=lo, x=u, z=v))
        tool = g if tool is None else tool.union(g)
    return tool


# ── Screw drive pulley (axis Z) ──────────────────────────────────────────
def screw_pulley() -> cq.Workplane:
    """Flanged GT2 pulley on the vertical screw, axis Z, centred at z=0. Printed
    axis-up: full bottom flange (printable wall, where the belt is biased) and a
    45°-chamfered TOP flange (a cone — printable, no overhang) per the print plan."""
    w, ft = D.PULLEY_W, D.PULLEY_FLANGE_T
    out = (cyl(D.PULLEY_OD, w, z=-w / 2)
           .union(cyl(D.PULLEY_FLANGE_OD, ft, z=-w / 2))                 # full bottom flange
           .union(_cone(D.PULLEY_OD / 2, D.PULLEY_FLANGE_OD / 2, _CHAMFER,
                        cq.Vector(0, 0, w / 2 - _CHAMFER), cq.Vector(0, 0, 1))))  # 45° top
    out = out.cut(_tooth_cutter("Z"))                                # 14 GT2 grooves
    return out.cut(cyl(D.PULLEY_BORE_SCREW, w + 2, z=-w / 2 - 1))


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


# ── Screw support bearing + locknut (axis Z) ─────────────────────────────
def support_bearing() -> cq.Workplane:
    """Single deep-groove ball bearing (radial + axial), axis Z, centred z=0."""
    o = cyl(D.SUPPORT_BRG_OD, D.SUPPORT_BRG_W, z=-D.SUPPORT_BRG_W / 2)
    return o.cut(cyl(D.SUPPORT_BRG_ID, D.SUPPORT_BRG_W + 2, z=-D.SUPPORT_BRG_W / 2 - 1))


def locknut() -> cq.Workplane:
    """Locknut on the screw end (axial retainer), axis Z, centred z=0. Bore = screw
    OD so it sleeves the thread cleanly (the real thread interference isn't modelled)."""
    o = cyl(D.LOCKNUT_OD, D.LOCKNUT_W, z=-D.LOCKNUT_W / 2)
    return o.cut(cyl(D.SCREW_OD, D.LOCKNUT_W + 2, z=-D.LOCKNUT_W / 2 - 1))


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


# ── Locking tuner (schematic) ────────────────────────────────────────────
def tuner() -> cq.Workplane:
    """Schematic locking-tuner block, centred at origin (placed at the nut end)."""
    return box_at(D.TUNER_D, D.TUNER_W, D.TUNER_H)


_FLAT_LEN = 42.0            # flat (untwisting) belt zone near the motor end of run B
_CLAMP_DIST = 24.0         # clamp centre distance from the motor (clears the pulley)
_AUX_OFF = 3.0             # auxiliary-spine offset that drives the sweep twist
_SAMPLE_DIV = 12.0         # run sample spacing (smaller = denser)


def _belt_samples(motor_xyz, screw_xyz):
    """Loop centreline as a list of (point, inward-normal n). n tracks the toothed
    face and returns to itself (orientable). Run B carries a FLAT zone near the
    motor (n held = +Z) so the splice clamp grips a non-twisting section."""
    import math
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
