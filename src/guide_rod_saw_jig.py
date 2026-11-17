# -*- coding: utf-8 -*-
"""A PRINTED HACKSAW JIG for cutting the direct drive's GUIDE RODS to direct_bench.ROD_L.

SHOP TOOL, not a part of the instrument (user, 2026-11-16: "we need a jig for cutting the guide
rods"). The leadscrew saw jig's sibling (src/saw_jig.py): the same blade (McMaster 6927A16), the
same Quick-Grip and no vise, the same diamond tunnel and clamp cap. The rod is 3/16 in 304
stainless (McMaster 89535K84, 2 ft lengths), each length cut into THREE EQUAL pieces with no
offcut (direct_bench.ROD_STOCK / ROD_PIECES / ROD_KERF).

WHAT IS DIFFERENT FROM THE LEADSCREW JIG. Its piece is 36 long and drops out of an open fork past
the table edge. This piece is 202.5, so a fork would be a 200 mm cantilever with a thin rod lying
loose in it. Instead the WHOLE JIG SITS ON THE TABLE and the piece lies in a supported V trough
out to the end stop. And the clamp holds the PIECE side, not the stock side, so the clamp section
counts toward the piece's length: the jig is ~225 long, not ~250.

Rod axis along +X, the saw line at x = 0, the piece +X of it:

  GUIDE   -X of the slot: a short full-width block with the diamond tunnel. The long stock rests
          in it while it is cut; hold the free end by hand.
  SLOT    SLOT_W, open across the whole width from Z_TOP down to SLOT_UNDER under the rod. A
          cheek either side guides the blade. A blade that runs through cuts the jig's floor,
          never the table.
  CLAMP   +X of the slot, past SUPPORT_GAP: the channel the LEADSCREW JIG'S CAP (saw_jig_cap, the
          same part) drops into onto the rod. The clamp squeezes cap -> rod -> V -> jig -> table.
  TROUGH  a rib with a 90 deg V on top, from the clamp block to the END STOP. The rod lies with its
          axis at the rib's top, so a cut piece lifts straight out.
  STOP    at ROD_L from the slot's +X face.

THE CUT. The blade's +X edge lands anywhere from the slot's +X face to SLOT_W - kerf short of it,
so a piece comes out ROD_L .. ROD_L + (SLOT_W - kerf), ~202.5 .. 202.8. File the burr square and
it is ~202.5. Feed the stock in twice from the same end; what is left after the second cut is
the third piece, ~202.5 again: 609.6 less two pieces and two ~1.0 kerfs. Every piece that fits is
in the window direct_bench takes: no shorter than ~ROD_L - 1.5 (the -X end stands 2 proud of the
anchor plate for pliers), no longer than rod_l_max() (204.0, the housing's cap). If the stock came
long and the third piece is over rod_l_max, put it in the jig and trim it like the others.
"""
from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import direct_bench as DB
from . import saw_jig as SJ

B = D.BEAD
SQ2 = math.sqrt(2.0)

# ── the rod ─────────────────────────────────────────────────────────────────
ROD_R = DB.GUIDE_D / 2.0                     # 2.38: 3/16 in
SLOT_UNDER = SJ.SLOT_UNDER                   # 2.4: slot floor under the rod's bottom
FLOOR_T = 3 * B                              # 2.4: under the slot floor (a blade overshoot)
ROD_Z = 10 * B                               # 8.0: rod axis over the table
SLOT_FLOOR_Z = ROD_Z - ROD_R - SLOT_UNDER    # 3.2
assert SLOT_FLOOR_Z >= FLOOR_T - 1e-9, "the slot floor is too thin over the table"
V_APEX_Z = ROD_Z - ROD_R * SQ2               # the 90 deg V's apex, under the rod
ROOF_CLR = SJ.ROOF_CLR                       # 0.5: air between the rod and the tunnel's roof
ROOF_Z = ROD_Z + (ROD_R + ROOF_CLR) * SQ2

# ── the saw ─────────────────────────────────────────────────────────────────
SLOT_W = SJ.SLOT_W                           # 1.3, McMaster 6927A16
SLOT_X0, SLOT_X1 = -SLOT_W / 2.0, SLOT_W / 2.0
STOP_X = SLOT_X1 + DB.ROD_L                  # the stop's face: ROD_L from the slot's +X face
assert DB.ROD_L + SLOT_W <= DB.rod_l_max(), "the longest piece the slot allows would not fit the cap"

# ── the body ────────────────────────────────────────────────────────────────
WALL = SJ.WALL                               # 3.2
GUIDE_L = 12 * B                             # 9.6: the stock-side block, cheek included
SUPPORT_GAP = SJ.SUPPORT_GAP                 # 5.6: slot face -> clamped support
RIB_HW = ROD_R * SQ2 + 3 * B                 # 5.8: the trough's half-width (V's lip + three beads)
STOP_T = 4 * B                               # 3.2
STOP_TOP = ROD_Z + ROD_R + 3 * B             # 12.8: the stop stands over the rod

# ── the cap: THE LEADSCREW JIG'S OWN (user, 2026-11-16: "Can I use my existing cap?") ──
# Its 90 deg notch sits on any round rod, a thinner one only higher up into it: on the 3/16 rod
# the notch's apex stands ROD_R*sqrt2 over the axis, so the cap's underside comes down to
# CAP_DROP over it -- below the axis. The clamp channel's floor goes CAP_LIFT under that, and a
# narrow V RIB is left down its middle, inside the notch's opening, so the rod is held from
# below the whole way under the cap.
CAP_L = CAP_W = SJ.CAP_L                     # 33.6: square, so the pad sits either way round
CAP_CLR = SJ.CAP_CLR                         # 0.3
CAP_LIFT = SJ.CAP_LIFT                       # 1.2: cap underside over the channel floor
CAP_APEX = SJ.ROD_Z + SJ.ROD_R * SQ2         # the notch's apex in the leadscrew jig's frame
CAP_DZ = ROD_Z + ROD_R * SQ2 - CAP_APEX      # the cap moved down by this here
CAP_BOT = SJ.ROD_Z + SJ.CAP_LIFT + CAP_DZ    # its underside
CAP_TOP = SJ.Z_TOP + SJ.CAP_PROUD + CAP_DZ   # its pocket's rim
CH_FLOOR = CAP_BOT - CAP_LIFT                # the channel's floor
Z_TOP = math.floor((CAP_TOP - SJ.CAP_PROUD) / B + 1e-9) * B   # the body's top: the cap ~CAP_PROUD proud
assert Z_TOP - (ROD_Z + ROD_R) >= 12.0, "the cheeks guide the blade too little over the rod"
NOTCH_HW = CAP_APEX - (SJ.ROD_Z + SJ.CAP_LIFT)   # the notch's half-width at the cap's underside
RIB_CLR = 0.5                                # the rib's top corners under the notch's faces
CH_RIB_TOP = ROD_Z - ROD_R / SQ2 + 1.0       # the rib: 1.0 over where the rod bears on its V
CH_RIB_HW = (CAP_APEX + CAP_DZ) - CH_RIB_TOP - RIB_CLR   # out to where the notch's face is over it
assert CH_RIB_HW - (CH_RIB_TOP - V_APEX_Z) >= B, "the rib's lips under the cap's notch are under a bead"
assert CH_FLOOR >= FLOOR_T, "the channel's floor is too thin over the table"
CAP_X0 = SLOT_X1 + SUPPORT_GAP               # the cap's -X face
CAP_X1 = CAP_X0 + CAP_L
CH_X0, CH_X1 = CAP_X0 - CAP_CLR, CAP_X1 + CAP_CLR
CH_HW = CAP_W / 2.0 + CAP_CLR
HW = CH_HW + WALL                            # body half-width
X_MIN = SLOT_X0 - GUIDE_L
CLAMP_X1 = CH_X1 + WALL                      # the clamp block's +X end; the trough runs on
assert CLAMP_X1 < STOP_X - 10.0, "the clamp block reaches the stop"
BODY_UP = (0.0, 0.0, 1.0)                    # prints as drawn, table face down
CAP_UP = (0.0, 0.0, 1.0)                     # prints as drawn, notch on the bed


def _box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _yz_prism(pts, x0, x1):
    return cq.Workplane("YZ").polyline(pts).close().extrude(x1 - x0).translate((x0, 0, 0))


def _tunnel(x0, x1):
    """The rod's DIAMOND: the 90 deg V it rests in, and the 45 deg roof ROOF_CLR over it."""
    h = (ROOF_Z - V_APEX_Z) / 2.0
    zm = (ROOF_Z + V_APEX_Z) / 2.0
    return _yz_prism([(0.0, V_APEX_Z), (h, zm), (0.0, ROOF_Z), (-h, zm)], x0, x1)


def _vee(x0, x1):
    """The trough's open 90 deg V, from its apex up past the rib's top."""
    h = ROD_Z + 1.0 - V_APEX_Z
    return _yz_prism([(0.0, V_APEX_Z), (h, V_APEX_Z + h), (-h, V_APEX_Z + h)], x0, x1)


def body() -> cq.Workplane:
    out = _box(X_MIN, SLOT_X0, -HW, HW, 0.0, Z_TOP)                           # stock-side guide
    out = out.union(_box(SLOT_X0, SLOT_X1, -HW, HW, 0.0, SLOT_FLOOR_Z))       # the slot's floor
    out = out.union(_box(SLOT_X1, CLAMP_X1, -HW, HW, 0.0, Z_TOP))            # cheek + clamp block
    out = out.cut(_box(CH_X0, CH_X1, -CH_HW, CH_HW, CH_FLOOR, Z_TOP + 1.0))  # the clamp channel
    out = out.union(_box(CH_X0 - 0.5, CH_X1 + 0.5, -CH_RIB_HW, CH_RIB_HW, CH_FLOOR - 0.5, CH_RIB_TOP))
    out = out.cut(_tunnel(X_MIN - 1.0, CLAMP_X1 + 1.0))
    # the trough: a rib to the rod's axis, its V open on top, out to the stop
    rib = _box(CLAMP_X1 - 1.0, STOP_X, -RIB_HW, RIB_HW, 0.0, ROD_Z).cut(_vee(CLAMP_X1 - 2.0, STOP_X + 1.0))
    stop = _box(STOP_X, STOP_X + STOP_T, -RIB_HW, RIB_HW, 0.0, STOP_TOP)
    out = out.union(rib).union(stop)
    vals = out.solids().vals()
    assert len(vals) == 1, f"the jig fell apart into {len(vals)} solids"
    return out


def cap() -> cq.Workplane:
    """The leadscrew jig's cap (saw_jig.cap, print one only if you have none), where it sits here."""
    return SJ.cap().translate((CAP_X0 - SJ.CAP_X0, 0.0, CAP_DZ))


def rod(length=None) -> cq.Workplane:
    """The 3/16 rod fed in to the stop, a whole 2 ft length -- for checking only."""
    length = DB.ROD_STOCK if length is None else length
    return cq.Workplane("YZ").circle(ROD_R).extrude(length).translate((STOP_X - length, 0.0, ROD_Z))

