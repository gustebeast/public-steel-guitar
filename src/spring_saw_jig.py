# -*- coding: utf-8 -*-
"""A PRINTED HACKSAW JIG for cutting the nut springs (direct_bench.SPRING_COILS close-wound coils
of McMaster 9665K36, 3/4 in OD x 0.091 in 302 stainless, 20 in lengths) into pieces.

SHOP TOOL, not a part of the instrument (user, 2026-11-17: no cutters strong enough for the wire,
and no new tool on the tool list for one cut). The guide rod jig's sibling (src/guide_rod_saw_jig.py):
the same blade (McMaster 6927A16), the same Quick-Grip and no vise, the same CAP (the leadscrew
jig's saw_jig_cap: no cap of its own; user, 2026-11-17: "could we use a C clamp like the rest of
the cutting jigs"), the whole jig on the table, the piece in a supported 90 deg V trough out to
an END STOP, clamped next to the slot.

ONE STRAIGHT CUT, SQUARE TO THE AXIS (user, 2026-11-17: "why can't it just be one angled cut that
splits the spring into two pieces?"). The spring is close-wound, its coils filling the length with
no gaps, so a plane square to the axis runs through the wire along ONE turn, lengthwise, and
nowhere else: two pieces, no loose bits, each end a FLAT face whose last turn tapers to a knife
edge over one turn (a ground spring end). The flat end butts the stop, so every piece is the
stop-to-slot length with no coil counting. The spring is NOT stretched for the cut: only its
initial tension (SPRING_IT, ~33 N) presses the coils together, and the clamp holds the piece so
the kerf cannot close on the blade.

Spring axis along +X, the saw line at x = 0, the piece +X of it:

  GUIDE   -X of the slot: a short block with the diamond tunnel the stock rests in (hold its
          free end by hand).
  SLOT    SLOT_W, open across the whole width from the top down to SLOT_UNDER under the spring.
  CLAMP   +X of the slot past SUPPORT_GAP: the channel the cap drops into. Its 90 deg notch,
          sized for the Tr8 rod, is narrower than the spring, so the cap rides on the spring on
          the notch's two lower edges (CAP_BEAR over the axis). Clamp: cap -> spring -> V -> jig
          -> table.
  TROUGH  a rib with a 90 deg V on top to the spring's axis, out to the END STOP.
  STOP    at PIECE_L from the slot's +X face.

THE CUT. A piece comes out PIECE_L .. PIECE_L + (SLOT_W - kerf), 97.0 .. ~97.4: the working
coils' length is set by the printed neck, not by the piece, so that is fine. Five pieces from one
20 in length (508): 5 x ~98.5 with the kerfs, the first cut squaring the factory end.
"""
from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import direct_bench as DB
from . import saw_jig as SJ

B = D.BEAD
SQ2 = math.sqrt(2.0)

# ── the spring ──────────────────────────────────────────────────────────────
SPR_R = DB.SPRING_OD / 2.0                   # 9.525
PIECE_L = DB.SPRING_COILS * DB.SPRING_WIRE   # 97.02: 42 close-wound coils
SLOT_UNDER = SJ.SLOT_UNDER                   # 2.4: slot floor under the spring's bottom
FLOOR_T = 3 * B                              # 2.4: under the V's apex and the slot floor
AXIS_Z = 20 * B                              # 16.0: spring axis over the table
V_APEX_Z = AXIS_Z - SPR_R * SQ2              # 2.53: the 90 deg V's apex
SLOT_FLOOR_Z = AXIS_Z - SPR_R - SLOT_UNDER   # 4.08
assert V_APEX_Z >= FLOOR_T and SLOT_FLOOR_Z >= FLOOR_T, "the floor is too thin over the table"
ROOF_CLR = SJ.ROOF_CLR                       # 0.5: air over the spring in the guide's tunnel
ROOF_Z = AXIS_Z + (SPR_R + ROOF_CLR) * SQ2

# ── the saw ─────────────────────────────────────────────────────────────────
SLOT_W = SJ.SLOT_W                           # 1.3, McMaster 6927A16
SLOT_X0, SLOT_X1 = -SLOT_W / 2.0, SLOT_W / 2.0
STOP_X = SLOT_X1 + PIECE_L                   # the stop's face

# ── the cap: THE LEADSCREW JIG'S OWN, riding on the spring ──────────────────
CAP_L = CAP_W = SJ.CAP_L                     # 33.6
CAP_CLR = SJ.CAP_CLR                         # 0.3
NOTCH_HW = SJ.ROD_R * SQ2 - SJ.CAP_LIFT      # 4.46: the notch's half-width at the cap's underside
assert NOTCH_HW < SPR_R / SQ2, "the notch's faces, not its edges, would bear on the spring"
CAP_BEAR = math.sqrt(SPR_R ** 2 - NOTCH_HW ** 2)   # 8.42: the underside over the axis, edges on it
CAP_DZ = AXIS_Z + CAP_BEAR - (SJ.ROD_Z + SJ.CAP_LIFT)   # the cap moved up by this here
CAP_TOP = SJ.Z_TOP + SJ.CAP_PROUD + CAP_DZ   # its pocket's rim
CH_FLOOR = AXIS_Z                            # the channel's floor: the V runs on below it
assert AXIS_Z + CAP_BEAR - CH_FLOOR >= SJ.CAP_LIFT, "the cap would bottom before it clamps"
Z_TOP = math.floor((CAP_TOP - SJ.CAP_PROUD) / B + 1e-9) * B   # the cap ~CAP_PROUD proud
assert Z_TOP - (AXIS_Z + SPR_R) >= 12.0, "the cheeks guide the blade too little over the spring"

# ── the body ────────────────────────────────────────────────────────────────
WALL = SJ.WALL                               # 3.2
GUIDE_L = 12 * B                             # 9.6
SUPPORT_GAP = SJ.SUPPORT_GAP                 # 5.6
RIB_HW = SPR_R * SQ2 + 3 * B                 # 15.9: the trough's half-width (V's lip + 3 beads)
STOP_T = 4 * B
STOP_TOP = AXIS_Z + SPR_R + 3 * B
CAP_X0 = SLOT_X1 + SUPPORT_GAP
CAP_X1 = CAP_X0 + CAP_L
CH_X0, CH_X1 = CAP_X0 - CAP_CLR, CAP_X1 + CAP_CLR
CH_HW = CAP_W / 2.0 + CAP_CLR
assert CH_HW > SPR_R * SQ2 + B, "the V comes through the channel's walls"
HW = CH_HW + WALL
X_MIN = SLOT_X0 - GUIDE_L
CLAMP_X1 = CH_X1 + WALL
assert CLAMP_X1 < STOP_X - 10.0, "the clamp block reaches the stop"
BODY_UP = (0.0, 0.0, 1.0)                    # prints as drawn, table face down


def _box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _yz_prism(pts, x0, x1):
    return cq.Workplane("YZ").polyline(pts).close().extrude(x1 - x0).translate((x0, 0, 0))


def _tunnel(x0, x1):
    """The spring's DIAMOND: the 90 deg V it rests in and the 45 deg roof ROOF_CLR over it."""
    h = (ROOF_Z - V_APEX_Z) / 2.0
    zm = (ROOF_Z + V_APEX_Z) / 2.0
    return _yz_prism([(0.0, V_APEX_Z), (h, zm), (0.0, ROOF_Z), (-h, zm)], x0, x1)


def _vee(x0, x1, top):
    """The open 90 deg V, from its apex up to `top`."""
    h = top - V_APEX_Z
    return _yz_prism([(0.0, V_APEX_Z), (h, top), (-h, top)], x0, x1)


def body() -> cq.Workplane:
    out = _box(X_MIN, SLOT_X0, -HW, HW, 0.0, Z_TOP)                           # stock-side guide
    out = out.cut(_tunnel(X_MIN - 1.0, SLOT_X0 + 1.0))
    out = out.union(_box(SLOT_X0, SLOT_X1, -HW, HW, 0.0, SLOT_FLOOR_Z))       # the slot's floor
    out = out.union(_box(SLOT_X1, CLAMP_X1, -HW, HW, 0.0, Z_TOP))            # cheek + clamp block
    out = out.cut(_box(CH_X0, CH_X1, -CH_HW, CH_HW, CH_FLOOR, Z_TOP + 1.0))  # the clamp channel
    out = out.cut(_vee(SLOT_X1 - 1.0, CLAMP_X1 + 1.0, CH_FLOOR + 0.01))      # the V under the cap
    out = out.cut(_tunnel(SLOT_X1 - 1.0, CH_X0 + 0.01))                      # ... the cheek's tunnel
    out = out.cut(_tunnel(CH_X1 - 0.01, CLAMP_X1 + 1.0))                     # ... the end wall's
    rib = _box(CLAMP_X1 - 1.0, STOP_X, -RIB_HW, RIB_HW, 0.0, AXIS_Z)
    rib = rib.cut(_vee(CLAMP_X1 - 2.0, STOP_X + 1.0, AXIS_Z + 1.0))
    stop = _box(STOP_X, STOP_X + STOP_T, -RIB_HW, RIB_HW, 0.0, STOP_TOP)
    out = out.union(rib).union(stop)
    vals = out.solids().vals()
    assert len(vals) == 1, f"the jig fell apart into {len(vals)} solids"
    return out


def cap() -> cq.Workplane:
    """The leadscrew jig's cap (saw_jig.cap: print one only if you have none), where it sits here."""
    return SJ.cap().translate((CAP_X0 - SJ.CAP_X0, 0.0, CAP_DZ))


def stock_spring() -> cq.Workplane:
    """The 20 in stock, its end on the stop, running out past the guide (drawn 60 past it)."""
    x0, x1 = X_MIN - 60.0, STOP_X
    proxy = DB._tube_x(DB.SPRING_OD, DB.SPRING_ID, x0, x1, 0.0, AXIS_Z)
    try:
        from cadkit.mesh_parts import coil_mesh, with_mesh, affine_of
    except ImportError:
        return proxy
    m = coil_mesh([(0.0, DB.SPRING_WIRE, x1 - x0)], DB.R_COIL, DB.SPRING_WIRE)
    return with_mesh(proxy, m, affine_of(lambda w: w.rotate((0, 0, 0), (0, 1, 0), 90)
                                         .translate((x0, 0.0, AXIS_Z))))


def blade() -> cq.Workplane:
    """The hacksaw blade (12.7 x 0.64) down the slot, its teeth on the spring's top."""
    return _box(-0.32, 0.32, -80.0, 80.0, AXIS_Z + SPR_R, AXIS_Z + SPR_R + 12.7)


def assembly() -> list:
    """The tab's view (user, 2026-11-17: "show the jig in a new tab")."""
    from cadkit.web.finishes import made_of
    from cadkit.kept import kept
    return [("sj_body", made_of(kept(body), "petg-gf")), ("sj_cap", made_of(kept(cap), "petg-gf")),
            ("sj_stock_spring", made_of(stock_spring(), "stainless")),
            ("sj_blade", made_of(blade(), "steel"))]


MATERIAL = {"sj_body": "petg-gf", "sj_cap": "petg-gf", "sj_stock_spring": "stainless", "sj_blade": "steel"}


def material_of(base_nm: str):
    return MATERIAL.get(base_nm)
