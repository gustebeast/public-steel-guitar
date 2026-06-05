"""Purchased-component DUMMIES — schematic solids for the assembly only.

These are NOT exported as printable STEPs; they exist so the assembly shows
where the bought parts sit relative to the printed parts. Each is built in a
canonical local frame (documented per function); build.py translates copies
into each string's global position.

Canonical orientation convention: rotating parts have their axis along +Y
(the screw/motor/string-pull direction), to match the global layout.
"""

from __future__ import annotations

import math
import cadquery as cq

from . import dimensions as D
from .helpers import cyl_y, box_at


# ── Leadscrew (T8) ───────────────────────────────────────────────────────
def screw(length: float = D.LEADSCREW_LEN) -> cq.Workplane:
    """T8 leadscrew, axis +Y, base face at y=0. (Threads not modelled.)"""
    return cyl_y(D.SCREW_OD, length, y0=0.0)


# ── Leadscrew nut (brass flanged) ────────────────────────────────────────
def nut() -> cq.Workplane:
    """Round brass nut, axis +Y. Seat lip (−Y face) at y=0; body extends +Y."""
    lip = cyl_y(D.NUT_FLANGE_OD, D.NUT_FLANGE_T, y0=0.0)
    body = cyl_y(D.NUT_OD, D.NUT_BODY_LEN, y0=D.NUT_FLANGE_T)
    bore = cyl_y(D.SCREW_OD + 0.4, D.NUT_FLANGE_T + D.NUT_BODY_LEN + 2, y0=-1.0)
    return lip.union(body).cut(bore)


# ── GT2 pulley ───────────────────────────────────────────────────────────
def pulley(bore: float) -> cq.Workplane:
    """GT2 20T pulley, axis +Y, centred at y=0 (y = ±PULLEY_W/2)."""
    body = cyl_y(D.PULLEY_OD, D.PULLEY_W, y0=-D.PULLEY_W / 2)
    b = cyl_y(bore, D.PULLEY_W + 2, y0=-D.PULLEY_W / 2 - 1)
    return body.cut(b)


# ── Screw support bearing + locknut ──────────────────────────────────────
def support_bearing() -> cq.Workplane:
    """Single deep-groove ball bearing (radial + axial), axis +Y, centred y=0."""
    o = cyl_y(D.SUPPORT_BRG_OD, D.SUPPORT_BRG_W, y0=-D.SUPPORT_BRG_W / 2)
    i = cyl_y(D.SUPPORT_BRG_ID, D.SUPPORT_BRG_W + 2, y0=-D.SUPPORT_BRG_W / 2 - 1)
    return o.cut(i)


def locknut() -> cq.Workplane:
    """Hex-ish locknut threaded on the screw end, snug against the bearing
    inner race — the axial retainer. Axis +Y, centred at y=0."""
    o = cyl_y(D.LOCKNUT_OD, D.LOCKNUT_W, y0=-D.LOCKNUT_W / 2)
    bore = cyl_y(D.SCREW_OD - 0.3, D.LOCKNUT_W + 2, y0=-D.LOCKNUT_W / 2 - 1)  # threads on
    return o.cut(bore)


# ── Motor: MKS SERVO42D on a 48 mm NEMA17 ────────────────────────────────
def motor() -> cq.Workplane:
    """SERVO42D, shaft along −Y. Faceplate at y=0, motor body extends +Y,
    driver PCB stacks beyond it; the 5 mm shaft + Ø22 pilot boss poke −Y
    (toward the screw/pulley). Centred on X=Z=0."""
    s = D.MOTOR_SQ / 2
    body = box_at(D.MOTOR_SQ, D.MOTOR_BODY_LEN, D.MOTOR_SQ,
                  x=0, y=D.MOTOR_BODY_LEN / 2, z=0)
    pcb = box_at(D.MOTOR_SQ - 6, D.MOTOR_PCB_LEN, D.MOTOR_SQ - 6,
                 x=0, y=D.MOTOR_BODY_LEN + D.MOTOR_PCB_LEN / 2, z=0)
    pilot = cyl_y(D.NEMA17_PILOT_D, 2.0, y0=-2.0)               # boss toward screw
    shaft = cyl_y(D.MOTOR_SHAFT_D, D.MOTOR_SHAFT_LEN, y0=-D.MOTOR_SHAFT_LEN)
    return body.union(pcb).union(pilot).union(shaft)


# ── Guide rod (anti-rotation) ────────────────────────────────────────────
def guide_rod(length: float) -> cq.Workplane:
    """Hardened steel rod, axis +Y, base face at y=0."""
    return cyl_y(D.GUIDE_ROD_D, length, y0=0.0)


# ── Roller bridge (purchased, schematic) ─────────────────────────────────
def roller_bridge() -> cq.Workplane:
    """A bar spanning the string field along X at the bridge (Y=0), with a
    row of rollers. Canonical: built in global position (bar top at
    BRIDGE_TOP_Z). String anchors BEHIND it (toward +Y) on the carriages."""
    bar = box_at(D.BRIDGE_BAR_W, D.BRIDGE_BAR_DEPTH, D.BRIDGE_BAR_H,
                 x=0, y=0, z=D.BRIDGE_TOP_Z - D.BRIDGE_BAR_H / 2)
    out = bar
    for i in range(D.N_STRINGS):
        roller = cq.Workplane("XY").add(cq.Solid.makeCylinder(
            D.BRIDGE_ROLLER_D / 2, D.STRING_PITCH * 0.7,
            pnt=cq.Vector(D.string_x(i) - D.STRING_PITCH * 0.35, 0, D.BRIDGE_TOP_Z),
            dir=cq.Vector(1, 0, 0)))
        out = out.union(roller)
    return out


# ── Locking tuner (purchased, schematic) ─────────────────────────────────
def tuner() -> cq.Workplane:
    """Schematic locking-tuner block, centred at origin (place at far end)."""
    return box_at(D.TUNER_W, D.TUNER_D, D.TUNER_H)


# ── GT2 belt loop (viz) ──────────────────────────────────────────────────
def belt(a: tuple[float, float], b: tuple[float, float], y_center: float) -> cq.Workplane:
    """A timing-belt loop wrapping two pulleys whose centres are a=(x,z) and
    b=(x,z) in the X–Z plane at y_center. Modelled as the band between the
    outer and inner stadium (racetrack) envelopes of the two pulley circles."""
    r_in = D.PULLEY_OD / 2
    r_out = r_in + D.BELT_T
    ax, az = a
    bx, bz = b
    dx, dz = bx - ax, bz - az
    L = math.hypot(dx, dz)
    y0 = y_center - D.BELT_W / 2

    def stadium(r):
        c0 = cyl_y(2 * r, D.BELT_W, y0=y0, x=ax, z=az)
        c1 = cyl_y(2 * r, D.BELT_W, y0=y0, x=bx, z=bz)
        if L < 1e-6:
            return c0.union(c1)
        # connecting bar: box length L (along local X) × BELT_W (Y) × 2r (Z),
        # rotated about +Y to align local +X with the a→b direction.
        alpha = math.degrees(math.atan2(-dz, dx))   # see helpers note on Y-rotation
        bar = (box_at(L, D.BELT_W, 2 * r, x=0, y=0, z=0)
               .rotate((0, 0, 0), (0, 1, 0), alpha)
               .translate(((ax + bx) / 2, y_center, (az + bz) / 2)))
        return c0.union(c1).union(bar)

    return stadium(r_out).cut(stadium(r_in))
