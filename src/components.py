"""Purchased-component DUMMIES — schematic solids for the assembly only.

These are NOT exported as printable STEPs; they exist so the assembly shows where
the bought parts sit relative to the printed parts. Each is built in a canonical
local frame; build.py translates copies into each string's position.
"""

from __future__ import annotations

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


# ── Screw drive pulley (axis Z) ──────────────────────────────────────────
def screw_pulley() -> cq.Workplane:
    """GT2 pulley on the vertical screw, axis Z, centred at z=0."""
    body = cyl(D.PULLEY_OD, D.PULLEY_W, z=-D.PULLEY_W / 2)
    return body.cut(cyl(D.PULLEY_BORE_SCREW, D.PULLEY_W + 2, z=-D.PULLEY_W / 2 - 1))


# ── Motor pulley (axis Y) ────────────────────────────────────────────────
def motor_pulley() -> cq.Workplane:
    """GT2 pulley on the motor shaft, axis Y, centred at y=0."""
    body = cyl_y(D.PULLEY_OD, D.PULLEY_W, y0=-D.PULLEY_W / 2)
    return body.cut(cyl_y(D.PULLEY_BORE_MOTOR, D.PULLEY_W + 2, y0=-D.PULLEY_W / 2 - 1))


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


# ── GT2 belt — full twisted loop (both runs + 90° twist + pulley wraps) ───
def belt(motor_xyz, screw_xyz, teeth: bool = False) -> cq.Workplane:
    """The real belt loop: it wraps the motor pulley (axis Y) and the screw pulley
    (axis Z), so its flat face twists 90° (along Y at the motor → along Z at the
    screw) on each run. Built by sweeping an oriented strip along the loop
    centreline, then FUSED into one solid (one Onshape part, one colour). The loop
    is orientable (the inward normal returns to itself), so `teeth=True` adds GT2
    teeth on the inner face. Motor is far −X, screw +X; both pulleys at the Y line."""
    import math
    V = cq.Vector
    M, S = V(*motor_xyz), V(*screw_xyz)
    r = D.PULLEY_OD / 2 + D.BELT_T / 2                # belt centreline radius
    m_top, m_bot = V(M.x, M.y, M.z + r), V(M.x, M.y, M.z - r)   # motor ±Z tangents
    s_py, s_my = V(S.x, S.y + r, S.z), V(S.x, S.y - r, S.z)     # screw ±Y tangents

    def lerp(a, b, t):
        return a.add(b.sub(a).multiply(t))

    # samples around the loop as (point, inward normal n). n tracks the toothed
    # face; it is continuous all the way round (verified orientable).
    samples = []
    NW = 10
    NA = max(6, int(s_py.sub(m_top).Length / 18))
    for k in range(NA + 1):                           # run A: n −Z → −Y
        a = (k / NA) * math.pi / 2
        samples.append((lerp(m_top, s_py, k / NA), V(0, -math.sin(a), -math.cos(a))))
    for k in range(1, NW):                            # screw wrap (+X side), n → −radial
        phi = math.radians(90 - 180 * k / NW)
        samples.append((V(S.x + r * math.cos(phi), S.y + r * math.sin(phi), S.z),
                        V(-math.cos(phi), -math.sin(phi), 0)))
    NB = max(6, int(m_bot.sub(s_my).Length / 18))
    for k in range(NB + 1):                           # run B: n +Y → +Z
        a = (k / NB) * math.pi / 2
        samples.append((lerp(s_my, m_bot, k / NB), V(0, math.cos(a), math.sin(a))))
    for k in range(1, NW):                            # motor wrap (−X side), n → −radial
        th = math.radians(270 - 180 * k / NW)
        samples.append((V(M.x + r * math.cos(th), M.y, M.z + r * math.sin(th)),
                        V(-math.cos(th), 0, -math.sin(th))))

    n_pts = len(samples)

    def frame(p0, p1, n0, n1):
        seg = p1.sub(p0)
        L = seg.Length
        tan = seg.multiply(1.0 / L)
        nn = n0.add(n1).multiply(0.5)
        nn = nn.sub(tan.multiply(nn.dot(tan)))        # n ⟂ tangent
        nn = nn.normalized()
        wd = nn.cross(tan).normalized()               # width ⟂ both
        return tan, nn, wd, L

    OV = 0.4
    parts = []
    # smooth strip (thickness BELT_T along n, width BELT_W along wd)
    for k in range(n_pts):
        p0, n0 = samples[k]
        p1, n1 = samples[(k + 1) % n_pts]
        if p1.sub(p0).Length < 1e-6:
            continue
        tan, nn, wd, L = frame(p0, p1, n0, n1)
        o = p0.sub(tan.multiply(OV / 2))
        pl = cq.Plane(origin=(o.x, o.y, o.z),
                      xDir=(wd.x, wd.y, wd.z), normal=(tan.x, tan.y, tan.z))
        parts.append(cq.Workplane(pl).rect(D.BELT_W, D.BELT_T).extrude(L + OV).val())

    # GT2 teeth on the inner face, every 2 mm of arc, protruding along +n
    if teeth:
        PITCH, TLEN, TH = 2.0, 1.1, 0.75
        acc = 0.0
        for k in range(n_pts):
            p0, n0 = samples[k]
            p1, n1 = samples[(k + 1) % n_pts]
            if p1.sub(p0).Length < 1e-6:
                continue
            tan, _, _, L = frame(p0, p1, n0, n1)
            d = 0.0
            while acc <= L - d + 1e-9:
                d += acc
                t = min(d / L, 1.0)
                pt = lerp(p0, p1, t)
                nn = lerp(n0, n1, t)
                nn = nn.sub(tan.multiply(nn.dot(tan)))
                acc = PITCH
                if nn.Length < 1e-6:
                    continue
                nn = nn.normalized()
                wd = nn.cross(tan).normalized()
                base = pt.add(nn.multiply(D.BELT_T / 2 - 0.2))
                pl = cq.Plane(origin=(base.x, base.y, base.z),
                              xDir=(wd.x, wd.y, wd.z), normal=(nn.x, nn.y, nn.z))
                parts.append(cq.Workplane(pl).rect(D.BELT_W, TLEN).extrude(TH + 0.2).val())
            acc -= (L - d)

    fused = parts[0].fuse(*parts[1:]) if len(parts) > 1 else parts[0]
    fused = fused.clean()
    solids = fused.Solids()
    return cq.Workplane("XY").add(solids[0] if len(solids) == 1 else fused)
