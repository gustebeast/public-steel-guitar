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
    """Locknut on the screw end (axial retainer), axis Z, centred z=0."""
    o = cyl(D.LOCKNUT_OD, D.LOCKNUT_W, z=-D.LOCKNUT_W / 2)
    return o.cut(cyl(D.SCREW_OD - 0.3, D.LOCKNUT_W + 2, z=-D.LOCKNUT_W / 2 - 1))


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


# ── GT2 belt (schematic) — twisted run from motor pulley to screw pulley ──
def belt(motor_xyz, screw_xyz) -> cq.Workplane:
    """Schematic belt: a flat band along X from the motor pulley to the screw
    pulley (both near the same Z), at the string's Y. The real belt twists 90°
    (motor axis Y → screw axis Z) over this span; modelled as a band for viz."""
    mx, my, mz = motor_xyz
    sx, sy, sz = screw_xyz
    x0, x1 = min(mx, sx), max(mx, sx)
    zc = (mz + sz) / 2
    # thin flat band along X at the pulley centreline (schematic run)
    return box_at(x1 - x0, D.BELT_W, 2 * D.BELT_T, x=(x0 + x1) / 2, y=my, z=zc)
