# -*- coding: utf-8 -*-
"""A PRINTED HACKSAW JIG for cutting the ten Tr8x2 leadscrews to D.SCREW_LEN.

SHOP TOOL, not a part of the instrument (lead, 2026-10-21). The screws are cut by hand from
long rods with a hacksaw, and the shop has NO VISE -- one Irwin Quick-Grip and a wood table.
The jig makes that one clamp do everything, and makes every piece the same length without
measuring.

TWO PRINTED PARTS, NOTHING BOUGHT. Rod axis along +X, the saw line at x = 0:

  BODY   a block the rod runs through in a DIAMOND tunnel -- a 90 deg V below that it rests
         in on two thread crests (so it cannot roll, and the V's apex stands ROD_R*(sqrt2 - 1)
         clear of the rod: the thread ROOTS never touch anything), a 45 deg roof above.
         -X of the saw line, over the table: the CLAMP CHANNEL the cap drops into. At the saw
         line: the SAW SLOT (SLOT_W, open across the whole width for the stroke), its two
         cheeks guiding the blade from Z_TOP down to the slot floor SLOT_UNDER under the rod.
         +X of it, past the table edge: an OPEN FORK -- nothing under the piece, so the cut
         piece drops straight out -- carrying the fixed END STOP.
  CAP    a plunger that slides down the clamp channel onto the rod: a 45 deg notch in its
         underside seats on the rod's two upper crests, and its top stands CAP_PROUD above
         the body with a raised rim round a pocket for the clamp's pad, so the pad cannot
         skate off. The clamp squeezes cap -> rod -> V -> body -> table in one stack: it holds
         the rod AND the jig.

HOW IT IS USED
  1. Thread the spare nut onto the rod (it stays on the long side, -X of the jig: the rod
     axis stands ROD_Z, over the flange nut's half-length, so it clears the table).
  2. Feed the rod in from the -X end until its end touches the END STOP.
  3. Set the jig on the table with the EDGE MARK (the notch down both sides) on the table's
     edge: the saw slot and the whole fork are then past the edge, so a blade that slips
     cuts the jig's slot floor, never the table.
  4. Drop the cap in, put the Quick-Grip's pad in the cap's pocket and its other jaw under
     the table, and squeeze.
  5. Saw down the slot. The piece falls out through the fork.
  6. File the fresh end of the LONG rod (the next piece's first end), then run the spare
     nut off over it to reform the thread. Repeat from 2.

THE STOP is at SCREW_LEN + FILE_ALLOW from the slot's +X face. The blade cannot cut +X of
that face, so every piece comes out at least SCREW_LEN + FILE_ALLOW long (and at most
SLOT_W - kerf longer), and filing takes it to length.

⚠ PAD_L x PAD_W is the clamp pad as the user measured it, "27mm x 20xx", read as 27 x 20.
The pocket is square and PAD_L + 3.4 across, so either way round fits -- confirm the second
figure only if the real pad is bigger than ~30 mm.
⚠ SLOT_W suits McMaster 6927A16 (12" bi-metal, 0.025" body; the tooth SET is wider): ~1.3.
"""
from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D

B = D.BEAD
SQ2 = math.sqrt(2.0)

# ── the rod and what rides on it ────────────────────────────────────────────
ROD_R = D.SCREW_OD / 2.0                     # 4.0: Tr8 crest
ROOT_R = 5.5 / 2.0                           # Tr8x2 root (see D.FORM_MINOR's note)
NUT_R = D.NUT_FLANGE_L / 2.0                 # 11.0: the spare nut's reach from the axis
ROD_Z = 15 * B                               # 12.0: rod axis over the table
assert ROD_Z >= NUT_R + B, "the spare nut would drag on the table (axis %.1f)" % ROD_Z
V_APEX_Z = ROD_Z - ROD_R * SQ2               # the V's apex, ROD_R*(sqrt2-1) under the rod
assert ROD_R * SQ2 - ROD_R > 0.0 and ROD_R * SQ2 > ROOT_R  # crests touch, roots never
ROOF_CLR = 0.5                               # air between the rod's crest and the 45 roof
ROOF_Z = ROD_Z + (ROD_R + ROOF_CLR) * SQ2    # the roof's ridge over the axis

# ── the saw ─────────────────────────────────────────────────────────────────
SLOT_W = 1.3                                 # 6927A16's tooth set, plus a little
SLOT_UNDER = 3 * B                           # 2.4: slot floor under the rod's bottom
SLOT_FLOOR_Z = ROD_Z - ROD_R - SLOT_UNDER    # 5.6
SLOT_X0, SLOT_X1 = -SLOT_W / 2.0, SLOT_W / 2.0
Z_TOP = 38 * B                               # 30.4: the cheeks guide the blade 14 over the rod
FILE_ALLOW = 0.4                             # filed off each piece's cut end
STOP_X = SLOT_X1 + D.SCREW_LEN + FILE_ALLOW  # the stop's face: SCREW_LEN + 0.4 from the slot

# ── the body ────────────────────────────────────────────────────────────────
WALL = 4 * B                                 # 3.2
CHEEK_T = 4 * B                              # 3.2: the +X cheek (piece side of the slot)
SUPPORT_GAP = 7 * B                          # 5.6: slot face -> clamped support (lead: 5-10)
DROP_HW = ROD_R + 1.2                        # 5.2: the fork's open half-width the piece falls through
LEG_T = 4 * B                                # 3.2
LEG_TOP = ROD_Z + ROD_R + 3 * B              # 18.4: the fork legs and the stop stand over the rod
STOP_T = 4 * B                               # 3.2
EDGE_W, EDGE_D = 2 * B, B                    # the table-edge mark: a 1.6 x 0.8 notch

# ── the cap and the clamp ───────────────────────────────────────────────────
PAD_L, PAD_W = 27.0, 20.0                    # the Quick-Grip pad (user, "27mm x 20xx")
RIM_T, RIM_H = 2 * B, 2 * B                  # the pad's locator rim
CAP_L = CAP_W = 42 * B                       # 33.6: square, so the pad sits either way round
assert CAP_W - 2 * RIM_T >= max(PAD_L, PAD_W) + 2 * B, "the pad does not fit the cap's pocket"
CAP_CLR = 0.3                                # the cap's slide in its channel, each side
CAP_LIFT = 3 * 0.4                           # 1.2: cap underside over the channel floor
CAP_PROUD = RIM_H + 2 * B                    # pocket floor 1.6 over the body top
CAP_X1 = SLOT_X0 - SUPPORT_GAP               # the cap's +X face
CAP_X0 = CAP_X1 - CAP_L
CH_X0, CH_X1 = CAP_X0 - CAP_CLR, CAP_X1 + CAP_CLR          # the channel
CH_HW = CAP_W / 2.0 + CAP_CLR
HW = CH_HW + WALL                            # body half-width
X_MIN = CH_X0 - WALL                         # the -X end wall
EDGE_X = (CH_X1 + SLOT_X0) / 2.0             # the table edge goes here: between support and slot
BODY_UP = (0.0, 0.0, 1.0)                    # prints as drawn, table face down
CAP_UP = (0.0, 0.0, 1.0)                     # prints as drawn, notch on the bed


def _box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _yz_prism(pts, x0, x1):
    """A prism of the YZ outline `pts`, from x0 to x1."""
    return (cq.Workplane("YZ").polyline(pts).close().extrude(x1 - x0).translate((x0, 0, 0)))


def _tunnel(x0, x1):
    """The rod's DIAMOND: the 90 deg V it rests in, and the 45 deg roof ROOF_CLR over it."""
    h = (ROOF_Z - V_APEX_Z) / 2.0
    zm = (ROOF_Z + V_APEX_Z) / 2.0
    return _yz_prism([(0.0, V_APEX_Z), (h, zm), (0.0, ROOF_Z), (-h, zm)], x0, x1)


def body() -> cq.Workplane:
    blk = _box(X_MIN, SLOT_X0, -HW, HW, 0.0, Z_TOP)
    blk = blk.cut(_box(CH_X0, CH_X1, -CH_HW, CH_HW, ROD_Z, Z_TOP + 1.0))   # the clamp channel
    blk = blk.cut(_tunnel(X_MIN - 1.0, SLOT_X0 + 1.0))
    # the slot's floor: what joins the two sides under the saw line, full width
    bridge = _box(SLOT_X0, SLOT_X1, -HW, HW, 0.0, SLOT_FLOOR_Z).cut(_tunnel(SLOT_X0 - 1, SLOT_X1 + 1))
    # the +X cheek: full width for the blade, an ARCH over the rod open to the bed (the piece
    # falls through it), its roof the tunnel's 45 deg one
    arch = _yz_prism([(-DROP_HW, -1.0), (DROP_HW, -1.0), (DROP_HW, ROOF_Z - DROP_HW),
                      (0.0, ROOF_Z), (-DROP_HW, ROOF_Z - DROP_HW)], SLOT_X1 - 1.0, SLOT_X1 + CHEEK_T + 1.0)
    cheek = _box(SLOT_X1, SLOT_X1 + CHEEK_T, -HW, HW, 0.0, Z_TOP).cut(arch)
    legs = [_box(SLOT_X1, STOP_X + STOP_T, s * DROP_HW, s * (DROP_HW + LEG_T), 0.0, LEG_TOP)
            if s > 0 else _box(SLOT_X1, STOP_X + STOP_T, -(DROP_HW + LEG_T), -DROP_HW, 0.0, LEG_TOP)
            for s in (+1, -1)]
    stop = _box(STOP_X, STOP_X + STOP_T, -(DROP_HW + LEG_T), DROP_HW + LEG_T, 0.0, LEG_TOP)
    out = blk.union(bridge).union(cheek).union(stop)
    for leg in legs:
        out = out.union(leg)
    for s in (+1, -1):                       # the table-edge mark down both sides
        y0 = HW - EDGE_D if s > 0 else -HW - 1.0
        out = out.cut(_box(EDGE_X - EDGE_W / 2.0, EDGE_X + EDGE_W / 2.0, y0, y0 + EDGE_D + 1.0,
                           -1.0, Z_TOP + 1.0))
    return out


def cap() -> cq.Workplane:
    top = Z_TOP + CAP_PROUD
    c = _box(CAP_X0, CAP_X1, -CAP_W / 2.0, CAP_W / 2.0, ROD_Z + CAP_LIFT, top)
    c = c.cut(_box(CAP_X0 + RIM_T, CAP_X1 - RIM_T, -CAP_W / 2.0 + RIM_T, CAP_W / 2.0 - RIM_T,
                   top - RIM_H, top + 1.0))
    apex = ROD_Z + ROD_R * SQ2               # 45 deg faces tangent to the rod's crest
    w = apex - (ROD_Z + CAP_LIFT) + 1.0
    return c.cut(_yz_prism([(-w, ROD_Z + CAP_LIFT - 1.0), (w, ROD_Z + CAP_LIFT - 1.0), (0.0, apex)],
                           CAP_X0 - 1.0, CAP_X1 + 1.0))


def rod(length=120.0) -> cq.Workplane:
    """The Tr8 rod at its crest, fed in to the stop -- for checking only."""
    return (cq.Workplane("YZ").circle(ROD_R).extrude(length)
            .translate((STOP_X - length, 0.0, ROD_Z)))
