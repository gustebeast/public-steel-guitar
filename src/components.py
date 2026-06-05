"""Purchased-component DUMMIES — schematic solids for the assembly only.

These are NOT exported as printable STEPs; they exist so the assembly shows
where the bought parts sit relative to the printed parts. Each is built in a
canonical local frame; build.py translates copies into each string's position.

Convention: rotating parts have their axis along +X (the screw/string axis).
"""

from __future__ import annotations

import math
import cadquery as cq

from . import dimensions as D
from .helpers import cyl_x, box_at


# ── Leadscrew ────────────────────────────────────────────────────────────
def screw(length: float = D.LEADSCREW_LEN) -> cq.Workplane:
    """Leadscrew, axis +X, base face at x=0. (Threads not modelled.)"""
    return cyl_x(D.SCREW_OD, length, x0=0.0)


# ── Leadscrew nut (round brass) ──────────────────────────────────────────
def nut() -> cq.Workplane:
    """Round brass nut, axis +X. Seat lip (−X face) at x=0; body extends +X."""
    lip = cyl_x(D.NUT_FLANGE_OD, D.NUT_FLANGE_T, x0=0.0)
    body = cyl_x(D.NUT_OD, D.NUT_BODY_LEN, x0=D.NUT_FLANGE_T)
    bore = cyl_x(D.SCREW_OD + 0.4, D.NUT_FLANGE_T + D.NUT_BODY_LEN + 2, x0=-1.0)
    return lip.union(body).cut(bore)


# ── GT2 pulley ───────────────────────────────────────────────────────────
def pulley(bore: float) -> cq.Workplane:
    """GT2 pulley, axis +X, centred at x=0 (x = ±PULLEY_W/2)."""
    body = cyl_x(D.PULLEY_OD, D.PULLEY_W, x0=-D.PULLEY_W / 2)
    b = cyl_x(bore, D.PULLEY_W + 2, x0=-D.PULLEY_W / 2 - 1)
    return body.cut(b)


# ── Screw support bearing + locknut ──────────────────────────────────────
def support_bearing() -> cq.Workplane:
    """Single deep-groove ball bearing (radial + axial), axis +X, centred x=0."""
    o = cyl_x(D.SUPPORT_BRG_OD, D.SUPPORT_BRG_W, x0=-D.SUPPORT_BRG_W / 2)
    i = cyl_x(D.SUPPORT_BRG_ID, D.SUPPORT_BRG_W + 2, x0=-D.SUPPORT_BRG_W / 2 - 1)
    return o.cut(i)


def locknut() -> cq.Workplane:
    """Locknut threaded on the screw end, snug against the bearing inner race —
    the axial retainer. Axis +X, centred at x=0."""
    o = cyl_x(D.LOCKNUT_OD, D.LOCKNUT_W, x0=-D.LOCKNUT_W / 2)
    bore = cyl_x(D.SCREW_OD - 0.3, D.LOCKNUT_W + 2, x0=-D.LOCKNUT_W / 2 - 1)
    return o.cut(bore)


# ── Motor: MKS SERVO42D on a 48 mm NEMA17 ────────────────────────────────
def motor() -> cq.Workplane:
    """SERVO42D, shaft along −X. Faceplate at x=0, motor body extends +X, driver
    PCB beyond it; the 5 mm shaft + Ø22 pilot boss poke −X (toward the screw
    pulley). Centred on Y=Z=0."""
    body = box_at(D.MOTOR_BODY_LEN, D.MOTOR_SQ, D.MOTOR_SQ,
                  x=D.MOTOR_BODY_LEN / 2, y=0, z=0)
    pcb = box_at(D.MOTOR_PCB_LEN, D.MOTOR_SQ - 6, D.MOTOR_SQ - 6,
                 x=D.MOTOR_BODY_LEN + D.MOTOR_PCB_LEN / 2, y=0, z=0)
    pilot = cyl_x(D.NEMA17_PILOT_D, 2.0, x0=-2.0)               # boss toward screw
    shaft = cyl_x(D.MOTOR_SHAFT_D, D.MOTOR_SHAFT_LEN, x0=-D.MOTOR_SHAFT_LEN)
    return body.union(pcb).union(pilot).union(shaft)


# ── Guide rod (anti-rotation) ────────────────────────────────────────────
def guide_rod(length: float) -> cq.Workplane:
    """Hardened steel rod, axis +X, base face at x=0."""
    return cyl_x(D.GUIDE_ROD_D, length, x0=0.0)


# ── Roller bridge (schematic) ────────────────────────────────────────────
def roller_bridge() -> cq.Workplane:
    """A bar spanning the string field along Y at the bridge (X=0), with a row of
    rollers. Built in global position (bar top at BRIDGE_TOP_Z). The string
    anchors toward the changer (+X) on the carriages; the speaking length runs
    −X over the rollers."""
    bar = box_at(D.BRIDGE_BAR_DEPTH, D.BRIDGE_BAR_LEN, D.BRIDGE_BAR_H,
                 x=0, y=0, z=D.BRIDGE_TOP_Z - D.BRIDGE_BAR_H / 2)
    out = bar
    for i in range(D.N_STRINGS):
        roller = cq.Workplane("XY").add(cq.Solid.makeCylinder(
            D.BRIDGE_ROLLER_D / 2, D.STRING_PITCH * 0.7,
            pnt=cq.Vector(0, D.string_y(i) - D.STRING_PITCH * 0.35, D.BRIDGE_TOP_Z),
            dir=cq.Vector(0, 1, 0)))
        out = out.union(roller)
    return out


# ── Locking tuner (schematic) ────────────────────────────────────────────
def tuner() -> cq.Workplane:
    """Schematic locking-tuner block, centred at origin (placed at the nut end)."""
    return box_at(D.TUNER_D, D.TUNER_W, D.TUNER_H)


# ── GT2 belt loop (viz) ──────────────────────────────────────────────────
def belt(a: tuple[float, float], b: tuple[float, float], x_center: float) -> cq.Workplane:
    """A timing-belt loop wrapping two pulleys whose centres are a=(y,z) and
    b=(y,z) in the Y–Z plane at x_center. Modelled as the band between the outer
    and inner stadium (racetrack) envelopes of the two pulley circles."""
    r_in = D.PULLEY_OD / 2
    r_out = r_in + D.BELT_T
    ay, az = a
    by, bz = b
    dy, dz = by - ay, bz - az
    L = math.hypot(dy, dz)
    x0 = x_center - D.BELT_W / 2

    def stadium(r):
        c0 = cyl_x(2 * r, D.BELT_W, x0=x0, y=ay, z=az)
        c1 = cyl_x(2 * r, D.BELT_W, x0=x0, y=by, z=bz)
        if L < 1e-6:
            return c0.union(c1)
        # connecting bar: box BELT_W (X) × L (Y) × 2r (Z), rotated about +X to
        # align local +Y with the a→b direction.
        alpha = math.degrees(math.atan2(dz, dy))
        bar = (box_at(D.BELT_W, L, 2 * r, x=0, y=0, z=0)
               .rotate((0, 0, 0), (1, 0, 0), alpha)
               .translate((x_center, (ay + by) / 2, (az + bz) / 2)))
        return c0.union(c1).union(bar)

    return stadium(r_out).cut(stadium(r_in))
