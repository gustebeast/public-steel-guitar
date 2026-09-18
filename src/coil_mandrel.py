# -*- coding: utf-8 -*-
"""A PRINTED TWO-PART MANDREL for heat-setting the leg's TRRS lead into a coil.

SHOP TOOL, not a part of the instrument. It exists because the slack store in the leg
wants a COILED lead (docs/leg-trrs-routing.md, sub-problem B) and a curly TRRS cable
with a trustworthy datasheet may not be buyable. A straight lead forced into a coil is
stressed; one heat-set at the radius it will live at is not.

WHY TWO PARTS (user). A bare mandrel sets the coil's INSIDE diameter and leaves its
outside to spring-back -- a number nobody can quote for an unspecified jacket, and the
sleeve bore only gives 20.9 of mean to land in. Capturing the cable in an annulus
exactly its own width pins the mean diameter between two surfaces instead of guessing
it: wound on BARREL_D, capped at SLEEVE_ID, and the answer is arithmetic. The outer
also holds every turn put while the assembly is heated and cooled, which is the other
half of the job.

WHY THE TURN COUNT IS THE POINT. The coil lives BETWEEN THE TENON ENDS, in a gap that
runs 90.8 (leg short) to 253.2 (leg long) and holds a constant ~433 mm of cable. Two
bounds pull opposite ways: COMPRESSED the coil gets FATTER and can swell past the
sleeve's O24.7 bore; STRETCHED it gets THINNER and the bend radius tightens. The
threshold is TURNS_MIN -- about 6.6. Above it the coil's circumferential capacity
exceeds the whole cable length, so it CANNOT exceed the bore however far it is
compressed and only the turns touching is left. At 6.5 turns the coil binds at a 71.3
gap against a 90.8 minimum; at 7 it binds at 26.6, about eleven ladder steps of
headroom. Half a turn is the difference, which is why this is a tool and not an
instruction to wind it round something.

HOW IT IS USED
  1. Find the middle of the lead. The coil is a MIDDLE section -- both ends are moulded
     connectors and neither passes through anything, which is also why every anchor
     here takes the cable sideways rather than threading it.
  2. Press the cable into the base cleat, wind TURNS turns up the barrel, touching, to
     the scribe line, and press the far side into the top cleat.
  3. Slide the SLEEVE down over the coil until it seats on the flange (its notch passes
     the starting tail).
  4. HEAT-SET: 80 C for 30+ min, then cool to room temperature BEFORE opening
     anything. The set happens on cooling, not on heating.
  5. Slide the sleeve off, then unscrew the coil off the barrel's open top.

⚠ HEAT IS NOT OPTIONAL, and "let it sit" is not a substitute. Winding a jacket cold and
leaving it gives creep, not a set: it holds some curl for a while and relaxes, worst in
plain PVC. The commercial process for a curly cord is a heated mandrel.

PRINT IT IN PA6-GF AND USE AN OVEN (user has both). That changes which end of this is
the constraint. PA6-GF's HDT is far above anything the jacket wants, so THE TOOL IS NO
LONGER THE LIMIT -- the CABLE is. Most TRRS jackets are rated 80 C continuous, which is
where to start; a curly cord is commercially set hotter, so if 80 relaxes there is room
to climb, and the tool will not care. Two practical notes about dry heat: an oven moves
heat into a wound coil more slowly than water, so give it 30+ minutes AT temperature
rather than 15; and keep the lead's two moulded connectors out of the hot zone, since
they are the parts with no reason to be heated and the most to lose.

⚠ Heating PVC gives off plasticiser. Ventilate, and do not use a food oven.

(The project dropped PA6-GF for PETG-GF on cost for INSTRUMENT parts. A one-off shop
tool is the case where that trade does not apply -- see the Tools section of BOM.md.)
Nothing about the geometry depends on any of this: a metal tube of BARREL_D substitutes
for the inner, and the sleeve's job of capping the diameter is unaffected.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import leg_stack as LS
from . import leg_trrs as LT

B = D.BEAD

# ── what the leg actually asks for ──────────────────────────────────────────
# Derived from the joint, not typed in, so the tool cannot drift from the part.
CAVITY_D = 24.7                 # the adjust sleeve's clear bore, MEASURED off the solid
                                # (the octagon's chamfers set it, not its flats)
GAP_MID = LS.Z_FIX_TEN_BOT - LS.Z_ADJ_TEN_TOP           # 172.0 as modelled
GAP_RANGE = (LS.ADJ_N - 1) * LS.ADJ_PITCH               # 162.4
GAP_MIN = GAP_MID - GAP_RANGE / 2.0                     # 90.8, leg at its shortest
GAP_MAX = GAP_MID + GAP_RANGE / 2.0                     # 253.2, leg at its longest
COIL_CABLE = 432.7              # the jacket left once every straight run is accounted
                                # for -- docs/leg-trrs-routing.md. CONSTANT: the straight
                                # runs do not change with the adjustment

_MEAN_MAX = CAVITY_D - LT.CABLE_D                       # 20.9 widest mean coil that fits
TURNS_MIN = COIL_CABLE / (math.pi * _MEAN_MAX)          # 6.59 -- THE THRESHOLD
TURNS = 7                       # the first whole turn above it

assert TURNS > TURNS_MIN, (
    "%d turns is under the %.2f threshold -- the coil will swell past the sleeve's "
    "O%.1f bore before the leg reaches its low stop" % (TURNS, TURNS_MIN, CAVITY_D))

# ── the tool ────────────────────────────────────────────────────────────────
BARREL_D = 20 * B               # 16.0. With the cable captured against SLEEVE_ID the
                                # coil's mean is BARREL_D + CABLE_D and nothing about
                                # spring-back enters it
MEAN_SET = BARREL_D + LT.CABLE_D                        # 19.8, as heat-set
SLEEVE_CLR = 0.2                # ...and the annulus is the cable plus this, so the
                                # sleeve slides rather than shaves
SLEEVE_ID = BARREL_D + 2 * LT.CABLE_D + SLEEVE_CLR      # 23.8
SLEEVE_WALL = 3 * B                                     # 2.4
SLEEVE_OD = SLEEVE_ID + 2 * SLEEVE_WALL                 # 28.6

SOLID_SPAN = TURNS * LT.CABLE_D                         # 26.6, turns touching
COIL_LEN = TURNS * math.hypot(math.pi * MEAN_SET, LT.CABLE_D)   # cable the coil holds

assert MEAN_SET <= _MEAN_MAX, (
    "set at mean O%.1f, the coil will not enter the O%.1f bore" % (MEAN_SET, CAVITY_D))
assert COIL_LEN <= COIL_CABLE * 1.02, (
    "%d turns at mean O%.1f wants %.1f of cable and the gap only frees %.1f"
    % (TURNS, MEAN_SET, COIL_LEN, COIL_CABLE))
assert SOLID_SPAN < GAP_MIN, (
    "the coil goes solid at %.1f and the gap only closes to %.1f" % (SOLID_SPAN, GAP_MIN))

# stretched: the gap holds the coil PLUS whatever cable stays straight in it
_STRAIGHT_IN_GAP = COIL_CABLE - COIL_LEN
_P_LONG = (GAP_MAX - _STRAIGHT_IN_GAP) / TURNS
MEAN_LONG = math.sqrt(max((COIL_LEN / TURNS) ** 2 - _P_LONG ** 2, 0.0)) / math.pi
assert MEAN_LONG >= 15.0, (
    "stretched over the %.1f gap the coil narrows to mean O%.1f, under the 15 floor"
    % (GAP_MAX, MEAN_LONG))

FLANGE_D = SLEEVE_OD            # the sleeve seats on it, so they match
FLANGE_T = 4 * B                # 3.2
CLEAT_W = LT.CABLE_D - 0.4      # 3.4: a light pinch on the O3.8 jacket, pressed in
                                # SIDEWAYS -- it cannot be threaded
CLEAT_DEEP = 8.0
SCRIBE_W, SCRIBE_DEEP = 0.6, 0.4        # the line you wind TO
SHANK_D, SHANK_L = 10.0, 20.0           # chuck it, or hold it in a vice
SLEEVE_L = SOLID_SPAN + 2.0             # 28.6: covers every turn and no more
BARREL_L = SOLID_SPAN + CLEAT_DEEP + 4.0
                                        # 38.6, and it is the SLEEVE that sizes it: the
                                        # top cleat has to start above where the sleeve
                                        # ends, or the sleeve seats on the tail instead
                                        # of the flange (the assert below, which caught
                                        # exactly that on the first build)

assert CLEAT_W < LT.CABLE_D, "the cleat has to pinch, not clear"
assert SLEEVE_L < BARREL_L - CLEAT_DEEP + 1.0, "the sleeve buries the top cleat"


def mandrel() -> cq.Workplane:
    """THE INNER. Shank, base flange with a cleat, barrel, scribe line at the turn
    count, top cleat. The top is OPEN on purpose -- the finished coil comes off by
    UNSCREWING, which a second flange would prevent."""
    z = 0.0
    out = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        SHANK_D / 2.0, SHANK_L, cq.Vector(0, 0, z), cq.Vector(0, 0, 1)))
    z += SHANK_L
    out = out.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        FLANGE_D / 2.0, FLANGE_T, cq.Vector(0, 0, z), cq.Vector(0, 0, 1))))
    z_base = z + FLANGE_T
    out = out.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        BARREL_D / 2.0, BARREL_L, cq.Vector(0, 0, z_base), cq.Vector(0, 0, 1))))
    # the base cleat: a radial slot through the flange, so the tail leaves sideways
    out = out.cut(cq.Workplane("XY").box(
        FLANGE_D, CLEAT_W, FLANGE_T + 2.0, centered=(False, True, False))
        .translate((BARREL_D / 2.0 - CLEAT_DEEP, 0, z - 1.0)))
    # the scribe line: wind to here and you have TURNS turns, touching
    ring = cq.Solid.makeCylinder(BARREL_D / 2.0 + 1.0, SCRIBE_W,
                                 cq.Vector(0, 0, z_base + SOLID_SPAN), cq.Vector(0, 0, 1))
    core = cq.Solid.makeCylinder(BARREL_D / 2.0 - SCRIBE_DEEP, SCRIBE_W + 2.0,
                                 cq.Vector(0, 0, z_base + SOLID_SPAN - 1.0),
                                 cq.Vector(0, 0, 1))
    out = out.cut(cq.Workplane("XY").add(ring.cut(core)))
    # the top cleat: an axial notch the finishing tail tucks into and lifts out of
    out = out.cut(cq.Workplane("XY").box(
        BARREL_D + 2.0, CLEAT_W, CLEAT_DEEP + 1.0, centered=(True, True, False))
        .translate((0, 0, z_base + BARREL_L - CLEAT_DEEP)))
    assert len(out.val().Solids()) == 1, (
        "the mandrel came out as %d solids" % len(out.val().Solids()))
    return out


def sleeve() -> cq.Workplane:
    """THE OUTER: a plain tube that caps the coil's diameter while it sets, with a notch
    at its foot so it can seat on the flange without crushing the starting tail.

    Drawn where it sits when the assembly is closed, so the pair reads as a pair."""
    z0 = SHANK_L + FLANGE_T
    out = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        SLEEVE_OD / 2.0, SLEEVE_L, cq.Vector(0, 0, z0), cq.Vector(0, 0, 1)))
    out = out.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        SLEEVE_ID / 2.0, SLEEVE_L + 2.0, cq.Vector(0, 0, z0 - 1.0), cq.Vector(0, 0, 1))))
    # the foot notch, over the starting tail
    out = out.cut(cq.Workplane("XY").box(
        SLEEVE_OD + 2.0, CLEAT_W + 0.4, LT.CABLE_D + 0.4, centered=(True, True, False))
        .translate((0, 0, z0 - 0.2)))
    assert len(out.val().Solids()) == 1, (
        "the sleeve came out as %d solids" % len(out.val().Solids()))
    return out


def report() -> str:
    """What this tool produces, in the numbers the leg cares about."""
    return "\n".join([
        "coil: %d turns, wound O%.1f, capped O%.1f" % (TURNS, BARREL_D, SLEEVE_ID),
        "  as SET            mean O%.1f   (bore allows %.1f -- no spring-back to guess)"
        % (MEAN_SET, _MEAN_MAX),
        "  holds             %.1f of cable against the %.1f the gap frees -- the last "
        "turn lands %.1f short, so %.2f turns not %d" %
        (COIL_LEN, COIL_CABLE, COIL_LEN - COIL_CABLE,
         TURNS * COIL_CABLE / COIL_LEN, TURNS),
        "  leg at its lowest  gap %.1f, coil solid at %.1f -> %.1f of headroom"
        % (GAP_MIN, SOLID_SPAN, GAP_MIN - SOLID_SPAN),
        "  leg at its highest gap %.1f, mean O%.1f (bend R %.1f = %.1fxOD)"
        % (GAP_MAX, MEAN_LONG, MEAN_LONG / 2, MEAN_LONG / 2 / LT.CABLE_D),
    ])
