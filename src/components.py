"""Purchased-component DUMMIES — schematic solids for the assembly only.

These are NOT exported as printable STEPs; they exist so the assembly shows where
the bought parts sit relative to the printed parts. Each is built in a canonical
local frame; build.py translates copies into each string's position.
"""

from __future__ import annotations

import functools
import math

import cadquery as cq

from . import dimensions as D
from .helpers import ball_bearing, ball_bearing_y, box_at, cyl, cyl_y

from cadkit.threads import threaded_rod
from cadkit.fasteners import set_screw, m4_insert                # the ONE dummies now live in cadkit/fasteners.py;
# re-exported here so C.set_screw() / C.m4_insert() keep working across the project

# PER-PART NOZZLE. The two GT2 pulleys are the only PRINTED parts in this module of
# dummies, and they need a finer nozzle than the project's 0.8 for their 2 mm tooth pitch.
# 0.4 (user, 2026-10-28; the belt clamp's GT2 ridges proved PCTG at 0.4): both print axis-up,
# so the teeth are drawn in plane -- ~0.9 lands, two 0.4 lines -- and the screw pulley's
# pilot thread is LAYER-made, its 45 deg flanks stacked by layers, 0.45 deep radially at
# Tr8 (Ø7.1 ridge, Ø8.0 groove). It was 0.2 for the Tr5 thread's 0.3 groove, now gone.
NOZZLE_D = 0.4

MOTOR_PULLEY_STANDOFF = 14.0 + D.MOTOR_SETBACK   # 17.2: pulley this far +Y of the motor faceplate


# ── Vertical leadscrew (axis Z) ──────────────────────────────────────────
# Tr8x2 to ISO 2904 / DIN 103 (the basic profile, no tolerance position): 30 deg
# included flanks, thread thickness = groove width = P/2 on the pitch diameter
# d2 = d - P/2, root d3 = d - 2*(P/2 + ac) with the standard's crest clearance ac = 0.25
# for P 2..5 -- which is the Ø5.5 root dimensions.FORM_MINOR is already sized against.
_TR_AC      = 0.25
_TR_PITCH_D = D.SCREW_OD - D.SCREW_PITCH / 2                    # 7.0
_TR_ROOT_D  = D.SCREW_OD - 2 * (D.SCREW_PITCH / 2 + _TR_AC)     # 5.5
_TR_FLANK   = math.tan(math.radians(15.0))
_TR_CHAMFER = (D.SCREW_OD - _TR_ROOT_D) / 2    # 1.25 x 45 deg, crest to root, both ends.
                                               # ⚠ GUESSED: the rod is sawn from stock and
                                               # nothing in the repo says how its ends are
                                               # dressed; this is the usual deburr.
_SCREWS = {}                                   # length -> the solid, built once


def _tr_groove_w(r: float) -> float:
    """Axial width of the thread GROOVE at radius r."""
    return D.SCREW_PITCH / 2 + 2 * (r - _TR_PITCH_D / 2) * _TR_FLANK


def screw(length: float = D.SCREW_LEN) -> cq.Workplane:
    """Leadscrew, axis +Z, base face at z=0: a cut length of Tr8x2 rod, threaded end to
    end (it is sawn from threaded stock, so there are no journals -- the bearing, the nut
    and the pulley's socket all ride the crests), single start, D.SCREW_HAND.

    ONE TRUE HELIX, cut the way cadkit.threads cuts: the groove's section swept along a
    helix and subtracted from a chamfered Ø8 blank, so the crests ARE the old plain
    cylinder's surface and nothing stands outside it. (Not cadkit.threads itself: that
    is the printable 45 deg form, and this is the bought rod's 30 deg one.) The sweep
    runs whole turns and overshoots both ends; the section rides the helix's own frame,
    which leans it by the lead angle (6.6 deg at the root, 0.7% on the groove's width).

    Built ONCE per length and handed out as the same solid: place it with .moved(), which
    shares the geometry, not .translate(), which copies it."""
    if length not in _SCREWS:
        p, rc, rr, ch = D.SCREW_PITCH, D.SCREW_OD / 2, _TR_ROOT_D / 2, _TR_CHAMFER
        blank = (cq.Workplane("XZ")
                 .polyline([(0, 0), (rc - ch, 0), (rc, ch), (rc, length - ch),
                            (rc - ch, length), (0, length)]).close()
                 .revolve(360, (0, 0, 0), (0, 1, 0)))
        turns = math.ceil(length / p) + 2
        ro = rc + 0.3                                               # cutter past the crest
        groove = (cq.Workplane("XZ")
                  .polyline([(rr, -_tr_groove_w(rr) / 2), (ro, -_tr_groove_w(ro) / 2),
                             (ro, _tr_groove_w(ro) / 2), (rr, _tr_groove_w(rr) / 2)]).close()
                  .sweep(cq.Workplane("XY").add(cq.Wire.makeHelix(
                      pitch=p, height=turns * p, radius=rr,
                      lefthand=D.SCREW_HAND == "LH")), isFrenet=True)
                  .translate((0, 0, -(turns * p - length) / 2)))
        out = blank.cut(groove, clean=False)
        # OCCT can hand back a smooth rod, or half of one, without a word
        # (cadkit/THREADS_README.md): hold the result to the thread's own arithmetic.
        _fill = 1 - ((rc ** 2 - rr ** 2) * (_tr_groove_w(rr) + _tr_groove_w(rc)) / 2 / p
                     - (rc - rr) ** 2 * (_tr_groove_w(rc) - _tr_groove_w(rr)) / (3 * p)) / rc ** 2
        _vol = out.val().Volume() / (math.pi * rc ** 2 * length)
        assert out.val().isValid() and len(out.val().Solids()) == 1             and abs(_vol - _fill) < 0.03, (
                f"the leadscrew's thread did not cut: {_vol:.3f} of its cylinder, "
                f"want {_fill:.3f}")
        _SCREWS[length] = out
    return _SCREWS[length]


# ── Leadscrew nut (H-type brass flange nut, axis Z) ──────────────────────
def nut() -> cq.Workplane:
    """H-type brass leadscrew nut, axis Z, mounted FLANGE UP / BOSS DOWN.

    THIS PART IS THE CARRIAGE. One ear anchors the string (ball end underneath),
    the other rides the guide rod; nothing else moves. WHICH ear does which is
    per-ROW, not per-part: the two screw rows are mirrored, so the near row takes
    its +X ear and the far row its -X ear. This solid is SYMMETRIC about x=0, so
    that mirroring needs no second SKU and no rotation — it is entirely carried by
    dimensions.string_anchor_x() / guide_rod_x() picking opposite ears.

    Origin = the flange's TOP face, so the flange hangs the first NUT_FLANGE_T
    below it and the boss the rest — see dimensions' MOUNTING note for why
    flange-up. The flange is the round Ø22 disc with two flats cut to NUT_AF (that
    IS the "H"), modelled as disc ∩ slab, which is what puts the long ends'
    ROUNDED profile in the assembly and decides how far the ears sweep.

    Tr8x2 H-flange, DEMO/purchased. Dimensions are now READ OFF THE SELLER'S
    DRAWING rather than guessed, but the listing states its own error as 0.5-1 mm
    and none has been measured yet — see dimensions.NUT_AF and the BOM's
    buy-one-and-measure gate.
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


# GT2 14-tooth pulley grooves: 14 valleys at 2 mm pitch on the pitch circle (PD = 14·2/π =
# 8.91 mm), cut into the toothed band between the flanges. Each is the GT2 groove's shape: a
# round bottom the belt tooth's R0.555 tip sits in, and straight flanks tangent to it that open
# to GROOVE_MOUTH at the OD.
# THE MOUTH IS WHAT SEATS THE TOOTH (user, 2026-10-28: the belt skipped by hand, "the valleys
# may not be deep enough to fit the whole teeth"). The grooves used to be a bare R0.55 circle
# centred 0.2 inside the OD -- 0.75 deep, but only 1.02 across at the rim, narrower than the
# 1.11 tooth tip itself, so the tooth rode on the rim's edges and never reached the bottom.
# Every size below carries GROOVE_CLR: a concave feature drawn by a 0.4 nozzle prints small.
_N_TEETH = 14
GROOVE_CLR = 0.05                                    # radial, all round the groove
GROOVE_DEPTH = D.BELT_TOOTH_H + GROOVE_CLR           # 0.80 below the OD
GROOVE_MOUTH = 1.40 + 2 * GROOVE_CLR                 # 1.50 across at the OD (the tooth's
                                                     # base, R0.15 fillets and all, ~1.4)
_GROOVE_R = 0.555 + GROOVE_CLR                       # the bottom's radius
_GROOVE_RC = D.PULLEY_OD / 2 - GROOVE_DEPTH + _GROOVE_R   # its centre's radius


def _groove(lo: float, length: float) -> cq.Workplane:
    """One groove cutter on +X, axis Z from z=lo for `length`, its far (+Z) end closed by a
    45° cone so the groove's end is no ceiling in a flange-down print."""
    ro, over = D.PULLEY_OD / 2, 0.3
    # flank: tangent from the mouth's corner (ro, GROOVE_MOUTH/2) to the bottom circle
    px, py = ro - _GROOVE_RC, GROOVE_MOUTH / 2
    d = math.hypot(px, py)
    ang = math.atan2(py, px) + math.acos(_GROOVE_R / d)
    tx, ty = _GROOVE_RC + _GROOVE_R * math.cos(ang), _GROOVE_R * math.sin(ang)
    qx = ro + over
    qy = ty + (qx - tx) * (GROOVE_MOUTH / 2 - ty) / (ro - tx)        # the flank, run on out
    prof = (cq.Workplane("XY").moveTo(tx, -ty)
            .threePointArc((_GROOVE_RC - _GROOVE_R, 0.0), (tx, ty))
            .lineTo(qx, qy).lineTo(qx, -qy).close())
    cap = math.hypot(qx - _GROOVE_RC, qy)                            # the cone's base radius
    g = prof.extrude(length + cap + 0.1).translate((0, 0, lo))
    roof = _cone(cap, 0.0, cap, cq.Vector(_GROOVE_RC, 0, lo + length), cq.Vector(0, 0, 1))
    keep = box_at(qx + 1.0, 4 * cap, length, x=(qx + 1.0) / 2, y=0.0, z=lo + length / 2)
    return g.intersect(keep.union(roof))


def _tooth_cutter(axis: str, lo: float = None, length: float = None):
    """Union of the 14 groove cutters, axis 'Z' (screw) or 'Y' (motor), spanning the
    toothed band between the two flanges; each closes at 45° at its +axis end."""
    if lo is None:
        lo = -D.PULLEY_W / 2 + D.PULLEY_FLANGE_T
    if length is None:
        length = D.PULLEY_W - D.PULLEY_FLANGE_T - _CHAMFER
    g = _groove(lo, length)
    tool = None
    for k in range(_N_TEETH):
        t = g.rotate((0, 0, 0), (0, 0, 1), 360.0 * k / _N_TEETH)
        tool = t if tool is None else tool.union(t)
    return tool if axis == "Z" else tool.rotate((0, 0, 0), (1, 0, 0), -90.0)   # Z -> +Y


# ── Screw drive pulley (axis Z) ──────────────────────────────────────────
# PRINT ORIENTATION (the record, declared once per part) -- both pulleys print FLANGE
# DOWN, which the builders below already say in prose and draw: a full disc as the bed
# face, narrowing going up, and _tooth_cutter caps the groove ends at 45 because a flat
# one would be "unsupported in a flange-down print". The screw pulley's flange is its -Z
# face and the motor pulley's is its -Y face (its +Y flange is the chamfered, printable
# cone), so they build +Z and +Y respectively. Neither is posed into the assembly.
SCREW_PULLEY_UP = (0.0, 0.0, 1.0)
MOTOR_PULLEY_UP = (0.0, 1.0, 0.0)


def screw_pulley(high: bool = False) -> cq.Workplane:
    """Screw drive pulley, origin at the TOOTHED BAND'S CENTRE. An ENDCAP, in TWO SKUs.

    The rod ends in a BLIND pilot-thread socket in the column above the band; the band's
    core is solid. A through-bore is impossible at Tr8 — the Ø8.0 pilot groove is wider
    than a 14T band's tooth root — and the endcap is what lets the pulley stay 14T.

    This part is still the retaining collar: the socket's formed thread grips the rod and
    the string's 147 N jams the boss on top up into the thrust bearing's inner ring.

    The SKUs differ only in COLUMN LENGTH (PULLEY_COL_HI vs PULLEY_COL_H, BELT_PLANE_DZ
    apart). That is what puts their bands on the two belt planes while their tops — and so
    their sockets — sit at the same Z. Both print FLANGE-DOWN.
    """
    g, cn = D.PULLEY_GAP, D.PULLEY_CONE
    ro, rf = D.PULLEY_OD / 2, D.PULLEY_FLANGE_OD / 2
    col = D.PULLEY_COL_HI if high else D.PULLEY_COL_H
    out = cyl(D.PULLEY_OD, g, z=-g / 2)                              # toothed band, solid
    out = out.union(_cone(ro, rf, cn, cq.Vector(0, 0, g / 2),        # 45° top flange
                          cq.Vector(0, 0, 1)))
    top = g / 2 + cn
    out = out.union(cyl(D.PULLEY_COL_D, col, z=top))                 # column, above the band
    top += col
    out = out.union(cyl(D.PULLEY_BOSS_D, D.PULLEY_BOSS_H, z=top))    # pilot onto inner ring
    top += D.PULLEY_BOSS_H

    # LOWER FLANGE: a 45° face toward the belt so it self-centres, then a full disc as the
    # bed face. It narrows going up, so it prints.
    bot = -g / 2 - cn
    out = out.union(_cone(rf, ro, cn, cq.Vector(0, 0, bot), cq.Vector(0, 0, 1)))
    out = out.union(cyl(D.PULLEY_FLANGE_OD, D.PULLEY_FLANGE_T, z=bot - D.PULLEY_FLANGE_T))

    out = out.cut(_tooth_cutter("Z", lo=-g / 2, length=g))           # 14 GT2 grooves
    # BLIND PILOT-THREAD SOCKET from the top. The cutter runs whole turns and overshoots
    # the mouth; only its floor is placed.
    floor = top - D.PULLEY_SOCKET_L
    turns = math.ceil((D.PULLEY_SOCKET_L + 2.0) / D.SCREW_PITCH)
    out = out.cut(threaded_rod(D.FORM_MINOR, D.FORM_MAJOR, D.SCREW_PITCH,
                               turns * D.SCREW_PITCH, z=floor, overshoot=0.05,
                               bevel_ends=False), clean=False)
    _li = 0.4                                                        # lead-in at the mouth
    out = out.cut(_cone(D.FORM_MAJOR / 2, D.FORM_MAJOR / 2 + _li, _li + 0.01,
                        cq.Vector(0, 0, top - _li), cq.Vector(0, 0, 1)), clean=False)
    return out


# ── Motor pulley (axis Y) ────────────────────────────────────────────────
# THE MOTOR PULLEY GRIPS THE SHAFT'S FLAT, ALL OF IT, AND NOTHING PAST ITS OWN FLANGE (user,
# 2026-10-28: "a round bore ... how will it grip to the motor shaft?"; "use the full length for
# grip"; then "open sounds good so it doesn't take up more space than needed" and the D should
# run "all the way" so it shows which way it goes on). The bore is the shaft's D end to end,
# open at both ends. Its -Y face is where the shaft's flat begins: the D key stops on the
# round shaft there, and THAT sets the pulley's place -- so the flat's length (dimensions.
# MOTOR_SHAFT_FLAT_L, assumed) sets it, and must be measured. Its +Y end is the +Y flange (the
# shaft stands 0.3 past it): the hub no longer runs on past the tip, toward the next belt.
# Drawn at the shaft's own sizes: a nozzle-drawn round hole prints under (cadkit's M4 pocket
# needed +0.1 to let a 6.0 insert drop in). At 0.0 it went on but would not come off without
# breaking it (user, 2026-10-28: "a touch too tight"), so 0.05 a side: still a grip, now a
# removable one. Open it another 0.05 if it is still too tight; close it if the pulley slips.
MOTOR_BORE_CLR = 0.05           # on the bore's radius and its flat


def motor_pulley(flat_deg: float = 0.0) -> cq.Workplane:
    """Flanged GT2 pulley on the motor shaft, axis Y, centred at y=0 (the motor's faceplate at
    y = -MOTOR_PULLEY_STANDOFF). 45 deg flanges both sides, a hub down to where the shaft's
    flat begins, an open D-bore whose flat faces +Z -- turned by `flat_deg` about Y, so the
    build can keep it on the shaft's flat when it turns the pulley to mesh the belt."""
    from .servo42d import SHAFT_L
    w, ft = D.PULLEY_W, D.PULLEY_FLANGE_T
    y0 = -MOTOR_PULLEY_STANDOFF + SHAFT_L - D.MOTOR_SHAFT_FLAT_L     # the flat's start
    y1 = w / 2                                                       # the +Y flange's face
    out = (cyl_y(D.PULLEY_OD, y1 - y0, y0=y0)                        # hub + toothed band
           .union(cyl_y(D.PULLEY_FLANGE_OD, ft, y0=-w / 2))          # -Y flange, belt face flat
           .union(_cone(D.PULLEY_FLANGE_OD / 2, D.PULLEY_OD / 2, _CHAMFER,      # ...on a 45 deg
                        cq.Vector(0, -w / 2, 0), cq.Vector(0, -1, 0)))          # cone to the hub
           .union(_cone(D.PULLEY_OD / 2, D.PULLEY_FLANGE_OD / 2, _CHAMFER,
                        cq.Vector(0, w / 2 - _CHAMFER, 0), cq.Vector(0, 1, 0))))   # 45° +Y
    out = out.cut(_tooth_cutter("Y"))                                # 14 GT2 grooves
    r = D.MOTOR_SHAFT_D / 2.0 + MOTOR_BORE_CLR
    z_flat = D.MOTOR_SHAFT_FLAT - D.MOTOR_SHAFT_D / 2.0 + MOTOR_BORE_CLR
    bore = (cyl_y(2 * r, y1 - y0 + 2.0, y0=y0 - 1.0)
            .cut(box_at(2 * r + 1.0, y1 - y0 + 4.0, r + 1.0 - z_flat,
                        y=(y0 + y1) / 2, z=(z_flat + r + 1.0) / 2.0)))      # the D, end to end
    return out.cut(bore.rotate((0, 0, 0), (0, 1, 0), flat_deg))


# ── Screw thrust bearing (axis Z) ────────────────────────────────────────
def support_bearing() -> cq.Workplane:
    """ONE 688ZZ deep-groove ball bearing (Ø8x16x5), axis Z, centred z=0. Goes
    on each screw in TANDEM — build.py stacks them; see dimensions.SUPPORT_BRG_N
    for why two and why not preloaded. (The purchased LOCKNUT that used to sit
    under them is gone: the printed screw_collar retains the screw now.)"""
    return ball_bearing(D.BRG688_OD, D.BRG688_ID, D.BRG688_W).translate((0, 0, -D.BRG688_W / 2))


# ── Motor: MKS SERVO42D, lies flat, shaft +Y ─────────────────────────────
def motor_parts() -> list:
    """[(suffix, solid, rgb, finish)] of the MEASURED SERVO42D (src/servo42d.py), one solid
    per material, shaft along +Y. Reference = the pulley plane (y=0): faceplate at
    y=−STANDOFF, the can and its driver extend −Y (toward the player). Centred on X=Z=0.
    The build names them motor_<i> (suffix "") and motor_<suffix>_<i>."""
    return [(k, wp.translate((0, -MOTOR_PULLEY_STANDOFF, 0)), rgb, fin)
            for k, wp, rgb, fin in _servo42d_parts()]


@functools.lru_cache(maxsize=1)
def _servo42d_parts():
    """Built once per process: ten motors are ten moves of the same solids."""
    from . import servo42d as SV
    return SV.parts()


def motor() -> cq.Workplane:
    """The whole SERVO42D as one compound, placed as motor_parts()."""
    return cq.Workplane("XY").add(cq.Compound.makeCompound(
        [v for _, wp, _, _ in motor_parts() for v in wp.vals()]))


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
    # The shaft runs from the -Y arm's BLIND wall out to the +Y arm's outer face, where
    # the optical strip's head caps it — see dimensions.BRIDGE_AXLE_Y0/Y1. It used to
    # stop at the two arm CENTRELINES, i.e. half a bore short of being supported at all.
    out = cyl_y(D.BRIDGE_AXLE_D, D.BRIDGE_AXLE_Y1 - D.BRIDGE_AXLE_Y0,
                y0=D.BRIDGE_AXLE_Y0, x=x, z=z)
    for i in range(D.N_STRINGS):
        y0 = D.string_y(i) - D.BRIDGE_BEARING_W / 2
        out = out.union(ball_bearing_y(D.BRIDGE_BEARING_OD, D.BRIDGE_AXLE_D + 0.3,
                                       D.BRIDGE_BEARING_W, y0, x=x, z=z))
    return out


# ── GT2 open belt: where it runs ─────────────────────────────────────────
# The belt is SEATED IN THE PULLEYS' TEETH: its land (the flat between two teeth) lies on
# the pulley's Ø8.4 tooth crests and its teeth hang into the grooves, so its pitch line is
# on the 14-tooth pitch circle (0.256 outside the crests; GT2's own figure is 0.254).
# Everything that rides the belt reads the SAME radius -- the clamp frames below as well --
# because a straight run is the tangent to it.
# ⚠ MOVED 2026-10-12: this was PULLEY_OD/2 + BELT_T/2 (4.9), which stood the whole belt on
# top of the crests, D.BELT_TOOTH_H too far out. Each run, and the clamp on it, is that
# much nearer the inside of its loop now.
BELT_BACK_T  = D.BELT_T - D.BELT_TOOTH_H                    # 0.65 the land, under the teeth
BELT_PITCH_R = D.PULLEY_TEETH * D.BELT_PITCH / (2 * math.pi)        # 4.456
BELT_R       = D.PULLEY_OD / 2 + BELT_BACK_T - D.BELT_T / 2  # 4.15 mid-thickness, on a pulley
_CLAMP_DIST = 24.0         # clamp centre distance from the motor (clears the pulley)


def splice_frame(motor_xyz, screw_xyz, from_screw=None):
    """Placement for the splice clamp: a point in run B's flat zone with the belt's
    tangent and (flat) normal. Returns (origin, xDir=tangent, normal=n) tuples.

    `from_screw` puts the origin that far along the run from the SCREW pulley's tangent
    point, which is how the assembly poses the clamp where the nut's travel has carried
    it. Left out, it sits _CLAMP_DIST from the motor (the coupon's reference)."""
    V = cq.Vector
    M, S = V(*motor_xyz), V(*screw_xyz)
    r = BELT_R
    m_bot, s_my = V(M.x, M.y, M.z - r), V(S.x, S.y - r, S.z)
    L_B = m_bot.sub(s_my).Length
    t = (1 - _CLAMP_DIST / L_B) if from_screw is None else from_screw / L_B
    p = s_my.add(m_bot.sub(s_my).multiply(t))
    tan = m_bot.sub(s_my).normalized()
    n = V(0, 0, 1)
    n = n.sub(tan.multiply(n.dot(tan))).normalized()
    return (p.x, p.y, p.z), (tan.x, tan.y, tan.z), (n.x, n.y, n.z)


def _clamp_run(motor_xyz, screw_xyz, upper):
    """(screw-end tangent point, unit tangent toward the motor, run length, sign) of the
    belt run a clamp rides: the upper one leaves the motor pulley's top."""
    V = cq.Vector
    M, S = V(*motor_xyz), V(*screw_xyz)
    r = BELT_R
    sgn = 1.0 if upper else -1.0
    m_t, s_t = V(M.x, M.y, M.z + sgn * r), V(S.x, S.y + sgn * r, S.z)
    return s_t, m_t.sub(s_t).normalized(), m_t.sub(s_t).Length, sgn


def clamp_span(motor_xyz, screw_xyz, upper, x0, x1):
    """(p_min, p_max): the clamp origin's distance from the screw-end tangent point with
    the clamp D.CLAMP_END_CLR off each pulley's flange. x0, x1 are the clamp's own extent
    along the belt about its origin."""
    L = _clamp_run(motor_xyz, screw_xyz, upper)[2]
    off = D.PULLEY_FLANGE_OD / 2 + D.CLAMP_END_CLR
    return off - x0, L - off - x1


def clamp_p(motor_xyz, screw_xyz, upper, x0, x1, down=0.0):
    """Where the clamp is with the nut `down` mm below the ceiling. It is SPLICED with the
    nut on the ceiling, D.CLAMP_END_CLR off the pulley it has just been travelling toward
    (INSTALL_NOTES), and the nut's travel carries it D.BELT_PER_MM per mm away from there.

    WHICH PULLEY THAT IS depends on the thread's hand, D.SCREW_HAND. A right-hand screw
    raises its nut when it turns clockwise seen from above; the pulley's +y side then
    moves toward +x. The upper run leaves the screw pulley on its +y side, so a clamp on
    it is carried TOWARD THE SCREW as the nut rises, and one on the lower run toward the
    motor. A left-hand screw swaps the two. ⚠ Derived, not yet seen on a bench."""
    p0, p1 = clamp_span(motor_xyz, screw_xyz, upper, x0, x1)
    at_screw_end = upper == (D.SCREW_HAND == "RH")       # where it is with the nut on the ceiling
    return p0 + down * D.BELT_PER_MM if at_screw_end else p1 - down * D.BELT_PER_MM


def clamp_frame(motor_xyz, screw_xyz, upper, p, x0, x1, da=0.0):
    """Placement for the in-line belt clamp on its run, its origin p from the screw-end
    tangent point, turned with the belt (plus `da` degrees of twist error). Returns
    (origin, xDir = toward the motor, normal = into the loop).

    THE ONE KINEMATIC MODEL: src.build draws the clamp with it, and tools/clamp_range.py
    and tools/check_carriage_travel.py step it. The belt turns 90 deg between the pulleys
    -- flat at the screw (normal across the instrument), on edge at the motor (normal
    vertical) -- and the clamp is rigid, so the turn is shared between the free belt
    either side of it in proportion to length."""
    V = cq.Vector
    s_t, tan, L, sgn = _clamp_run(motor_xyz, screw_xyz, upper)
    ls, lm = p + x0, L - (p + x1)
    a = (math.pi / 2) * ls / (ls + lm) + math.radians(da)
    n = V(0, math.cos(a), math.sin(a)).multiply(-sgn)
    n = n.sub(tan.multiply(n.dot(tan))).normalized()
    o = s_t.add(tan.multiply(p))
    return (o.x, o.y, o.z), (tan.x, tan.y, tan.z), (n.x, n.y, n.z)


# ── GT2 open belt: the solid ─────────────────────────────────────────────
def _clamp_twist(d, L, p, x0, x1):
    """The belt's turn (rad, 0 at the screw pulley, pi/2 at the motor's) at d along a run
    of length L from its screw end. With a clamp on the run (p not None) the stretch
    under it, p + x0 .. p + x1, is rigid and the turn is shared between the free belt
    either side in proportion to length: clamp_frame's rule, so the two agree."""
    if p is None:
        return (math.pi / 2) * d / L
    a, b = p + x0, p + x1
    free = d if d <= a else a if d <= b else d - (b - a)
    return (math.pi / 2) * free / (L - (b - a))


def _belt_path(motor_xyz, screw_xyz, upper, p, x0, x1, end_a, end_b):
    """The open belt as a path: (frame, length, wraps). frame(u) -> (centre, inward
    normal, direction of travel) at u along the pitch line from the cut end in the clamp's
    half A (end_a, in the clamp's frame; A is the half toward the screw), round the screw
    pulley, back along the other run, round the motor pulley and into half B (end_b).
    wraps = ((u at the start of the screw pulley's half turn, its end), (the motor's))."""
    V = cq.Vector
    M, S = V(*motor_xyz), V(*screw_xyz)
    s_c, tan_c, L_c, sgn = _clamp_run(motor_xyz, screw_xyz, upper)
    s_o, tan_o, L_o, _ = _clamp_run(motor_xyz, screw_xyz, not upper)
    d_a, d_b = p + end_a, p + end_b
    half = math.pi * BELT_PITCH_R                       # half a turn of either pulley: 7 teeth
    u1 = d_a
    u2 = u1 + half
    u3 = u2 + L_o
    u4 = u3 + half
    total = u4 + L_c - d_b

    def run(o, tan, d, a, side, travel):
        n = V(0.0, math.cos(a), math.sin(a)).multiply(side)
        n = n.sub(tan.multiply(n.dot(tan))).normalized()
        return o.add(tan.multiply(d)), n, tan.multiply(travel)

    def frame(u):
        if u <= u1 or u >= u4:                          # the clamp's own run
            d = d_a - u if u <= u1 else L_c - (u - u4)
            return run(s_c, tan_c, d, _clamp_twist(d, L_c, p, x0, x1), -sgn, -1.0)
        if u < u2:                                      # screw pulley, its far side (+X)
            f = sgn * (math.pi / 2 - (u - u1) / BELT_PITCH_R)
            rad = V(math.cos(f), math.sin(f), 0.0)
            return (S.add(rad.multiply(BELT_R)), rad.multiply(-1.0),
                    V(math.sin(f), -math.cos(f), 0.0).multiply(sgn))
        if u <= u3:                                     # the other run, toward the motor
            d = u - u2
            return run(s_o, tan_o, d, _clamp_twist(d, L_o, None, 0.0, 0.0), sgn, 1.0)
        t = -sgn * (math.pi / 2 + (u - u3) / BELT_PITCH_R)      # motor pulley, far side (-X)
        rad = V(math.cos(t), 0.0, math.sin(t))
        return (M.add(rad.multiply(BELT_R)), rad.multiply(-1.0),
                V(math.sin(t), 0.0, -math.cos(t)).multiply(sgn))

    return frame, total, ((u1, u2), (u3, u4))


def belt_loop(motor_xyz, screw_xyz) -> float:
    """Pitch-line length of the belt's path as a CLOSED loop: both runs and half a turn
    of each pulley. The belt is this, less what its clamp spans between its cut ends."""
    return (_clamp_run(motor_xyz, screw_xyz, True)[2] + _clamp_run(motor_xyz, screw_xyz, False)[2]
            + 2 * math.pi * BELT_PITCH_R)


def belt_mesh(motor_xyz, screw_xyz, upper, p, x0, x1, end_a, end_b, tooth):
    """(motor pulley turn about +Y, screw pulley turn about +Z), in degrees, that put each
    pulley's grooves under this belt's teeth. The pulleys are modelled with a groove on
    +X; the belt's teeth are where its clamp holds them, so the pulleys turn to suit."""
    _f, _total, ((u1, _u2), (u3, _u4)) = _belt_path(motor_xyz, screw_xyz, upper, p, x0, x1,
                                                    end_a, end_b)
    sgn = 1.0 if upper else -1.0

    def first(u):                                       # first tooth centre at or after u
        return tooth + math.ceil((u - tooth) / D.BELT_PITCH - 1e-9) * D.BELT_PITCH
    f = sgn * (math.pi / 2 - (first(u1) - u1) / BELT_PITCH_R)
    t = -sgn * (math.pi / 2 + (first(u3) - u3) / BELT_PITCH_R)
    step = 360.0 / D.PULLEY_TEETH
    # about +Y a turn carries +X toward -Z, so the motor pulley's is the angle negated
    return (-math.degrees(t)) % step, math.degrees(f) % step


_TWIST_STEP = 2.0                # deg: the most a run's belt turns between two sections
_WRAP_STEP = 10.0                # deg: likewise round a pulley


def belt(motor_xyz, screw_xyz, upper, p, x0, x1, end_a, end_b) -> cq.Workplane:
    """One OPEN GT2 belt from its cut end in the clamp's half A round both pulleys to its
    cut end in half B -- nothing passes through the clamp.

    upper, p, x0, x1 are clamp_frame's (which run the clamp is on, where, and its extent),
    so the belt lies in the clamp's slots wherever the clamp is put; end_a, end_b are the
    two cut ends in the clamp's frame (belt_tensioner.belt_ends).

    DRAWN AS A PLAIN BAND, D.BELT_W by D.BELT_T: the envelope of the land and its teeth,
    with no tooth cut into it. So it stands D.BELT_TOOTH_H into each pulley's crests and
    the clamp's ribs, which is where the teeth are.

    ONE ruled loft through the band's own cross-sections, every _TWIST_STEP of a run's
    90 deg turn and every _WRAP_STEP round a pulley. The cut ends are simply the first and
    last section, and no boolean is involved: one solid, by construction."""
    frame, total, ((u1, u2), (u3, u4)) = _belt_path(motor_xyz, screw_xyz, upper, p, x0, x1,
                                                    end_a, end_b)
    L_c = _clamp_run(motor_xyz, screw_xyz, upper)[2] - (x1 - x0)
    us = []
    for a, b, deg, step in ((0.0, u1, 90.0 * u1 / L_c, _TWIST_STEP),
                            (u1, u2, 180.0, _WRAP_STEP),
                            (u2, u3, 90.0, _TWIST_STEP),
                            (u3, u4, 180.0, _WRAP_STEP),
                            (u4, total, 90.0 * (total - u4) / L_c, _TWIST_STEP)):
        n = max(1, math.ceil(deg / step))
        us += [a + (b - a) * k / n for k in range(n)]
    us.append(total)
    ht, hw = D.BELT_T / 2, D.BELT_W / 2
    wires = []
    for u in us:
        o, n, t = frame(u)
        w = n.cross(t).normalized().multiply(hw)
        lo, hi = o.sub(n.multiply(ht)), o.add(n.multiply(ht))
        wires.append(cq.Wire.makePolygon([lo.sub(w), lo.add(w), hi.add(w), hi.sub(w)],
                                         close=True))
    return cq.Workplane("XY").add(cq.Solid.makeLoft(wires, ruled=True))
