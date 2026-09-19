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
BARREL_D = 19 * B               # 15.2. With the cable captured against SLEEVE_ID the
                                # coil's mean is BARREL_D + CABLE_D and nothing about
                                # spring-back enters it
MEAN_SET = BARREL_D + LT.CABLE_D                        # 19.8, as heat-set
SLEEVE_CLR = 0.2                # ...and the annulus is the cable plus this, so the
                                # sleeve slides rather than shaves
SLEEVE_ID = BARREL_D + 2 * LT.CABLE_D + SLEEVE_CLR      # 23.8
SLEEVE_WALL = 3 * B                                     # 2.4
SLEEVE_OD = SLEEVE_ID + 2 * SLEEVE_WALL                 # 28.6

SOLID_SPAN = TURNS * LT.CABLE_D                         # 26.6, turns touching
FREE_SPAN = 80.0                # ...AND THE COIL IS NOT SET THERE. Turns-touching is
                                # the obvious thing to wind and it is wrong here: the
                                # service span is 90.8..253.2, so a coil set at 26.6
                                # would live held at 3.4x to 9.5x its own free length.
                                # A phone handset cord lives at 3-6x and those lose
                                # their curl; ours would too, and a relaxed coil is not
                                # a cosmetic problem -- 342 mm of uncoiled slack does
                                # not fit a O24.7 bore, so losing the curl is losing
                                # the function.
                                #
                                # Set just UNDER the shortest gap instead. 80 against a
                                # 90.8 minimum leaves the coil always in slight tension
                                # (1.1x) and never compressed below free, where it would
                                # buckle and jam in the bore, and takes the worst case
                                # down to 3.2x -- ordinary curly-cord duty
PITCH = FREE_SPAN / TURNS       # 11.43 between turns, which is why the barrel carries
                                # a rib: at this spacing the turns do not locate
                                # themselves the way touching turns do
COIL_LEN = TURNS * math.hypot(math.pi * MEAN_SET, PITCH)        # cable the coil holds

assert FREE_SPAN < GAP_MIN, (
    "set free at %.1f in a gap that closes to %.1f, the coil would be COMPRESSED at "
    "the leg's low stop and buckle" % (FREE_SPAN, GAP_MIN))
assert PITCH > LT.CABLE_D, "the turns overlap at the set pitch"

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
assert _STRAIGHT_IN_GAP >= 0.0, (
    "the coil wants %.1f of cable and the gap frees %.1f" % (COIL_LEN, COIL_CABLE))
MEAN_LONG = math.sqrt(max((COIL_LEN / TURNS) ** 2 - _P_LONG ** 2, 0.0)) / math.pi
# ⚠⚠ THIS TOOL IS BLOCKED ON A VENDOR NUMBER, AND THE ASSERT BELOW SAYS SO. ⚠⚠
#
# Tensility publish a MINIMUM BEND RADIUS of 22.8 for 10-02135 -- 6x the jacket,
# because the shield is spiral + FOIL and foil cracks long before PVC complains.
# (leg_trrs.CABLE_BEND_R, checked against their page by tools/check_part_specs.py.)
#
# A coil at that radius needs a mean diameter of 45.6. The cavity it has to live in --
# the adjust sleeve above the tenon -- measures O24.7, which caps the mean at 20.9.
# There is no turn count that reconciles those: the coil is impossible in the leg at
# the published radius, not merely tight. Everything below sizes a coil at mean 19.0,
# which is r 9.5 against a required 22.8.
#
# I found this AFTER building the tool, by reading the vendor's page (user asked).
# Every earlier bend-radius figure in this module and in docs/leg-trrs-routing.md was
# measured against a 3xOD rule of thumb I brought with me, not against the number the
# manufacturer publishes -- so "2.1xOD, tight but acceptable" was the wrong yardstick
# throughout. The options are the user's: accept exceeding the published radius on a
# static install, move the slack store out of the leg where nothing caps the diameter
# (docs/leg-trrs-routing.md option 2), or source a lead with a smaller bend radius.
assert MEAN_LONG / 2.0 >= LT.CABLE_BEND_R, (
    "the coil bends to r %.1f at full leg extension and %s publishes %.1f as its "
    "minimum -- see the block above; this is a DESIGN DECISION, not a number to relax"
    % (MEAN_LONG / 2.0, "10-02135", LT.CABLE_BEND_R))
assert MEAN_LONG >= 15.0, (
    "stretched over the %.1f gap the coil narrows to mean O%.1f, under the 15 floor"
    % (GAP_MAX, MEAN_LONG))

FLANGE_D = SLEEVE_OD            # the sleeve seats on it, so they match
FLANGE_T = 8 * B                # 6.4, thick enough that the starting tail sits BELOW
                                # its top face in a top-entry notch. That is what lets
                                # the sleeve seat flat on the flange without a notch of
                                # its own, and it is why the flange is not thinner
RIB_H = 2 * B                   # 1.6 of helical rib between turns. Its lower flank
                                # rises 1.6 over 2*RIB_H of axial run -- 26.6 degrees
                                # off vertical, not the 45 a symmetric rib would give.
                                # The extra is for the LEAD: a helical flank's true
                                # slope swings by about the lead angle (13.5 here) as
                                # it goes round, so a nominal 45 would droop past the
                                # limit on one side of every turn. 26.6 + 13.5 still
                                # clears it. The upper flank stays steep -- nothing
                                # prints on top of it. Shorter than the cable's
                                # radius, so the cable still rests on the barrel and
                                # MEAN_SET stays barrel + cable; the rib only spaces
                                # the turns, which at PITCH they will not do themselves
SCRIBE_W, SCRIBE_DEEP = 0.6, 0.4        # the line you wind TO
CLEAT_W = LT.CABLE_D - 0.4      # 3.4: a light pinch on the O3.8 jacket, pressed in
                                # SIDEWAYS -- it cannot be threaded
TAIL_RUN = 12.0                 # PLAIN BARREL EITHER SIDE OF THE WINDING ZONE, so each
                                # tail leaves the helix, TURNS AXIAL, and is held that
                                # way while it sets (user). It matters because that is
                                # exactly what the leg asks of them: the coil sits on
                                # the leg axis with its cable path at r 9.5, and both
                                # tails run AXIALLY out of it -- down into the adjust
                                # tenon's channel at r 8.0, up into the fixed tenon's
                                # bore at r 5.8. Set the transition here and the coil
                                # drops in with its ends already pointing the right way
                                # instead of being bent to it afterwards. 7 WHOLE turns
                                # also leaves both tails at the same azimuth, which is
                                # what those two radii want
CLEAT_R = BARREL_D / 2.0 + LT.CABLE_D / 2.0     # 9.5, the cable's OWN radius: the slit
                                        # has to sit where the tail already is, or it
                                        # pulls the tail sideways to reach it
BARREL_L = 2 * TAIL_RUN + FREE_SPAN
SLEEVE_L = BARREL_L                     # covers both tail runs AND every turn: the
                                        # axial tails are only 'set' if something holds
                                        # them against the barrel while they cool
                                        # 92.0, and it is the SLEEVE that sizes it: the
                                        # top cleat has to start above where the sleeve
                                        # ends, or the sleeve seats on the tail instead
                                        # of the flange (the assert below, which caught
                                        # exactly that on the first build)

assert CLEAT_W < LT.CABLE_D, "the cleat has to pinch, not clear"
assert SLEEVE_L <= BARREL_L, "the sleeve stands proud of the barrel"


def mandrel() -> cq.Workplane:
    """THE INNER, printed FLANGE-DOWN. Flange, then barrel: TAIL_RUN of plain barrel,
    the ribbed winding zone, TAIL_RUN of plain barrel, top cleat.

    NO SHANK (user). A O10 x 20 stub under the flange made the first layer O10 with
    everything above it wider -- a 127 tall tower on a 78 mm2 footprint -- and the 45
    cone above it existed only to carry the flange over that stub. Standing on the
    flange the base is O%.1f, the cone is unnecessary, and winding seven turns by hand
    never needed a chuck.""" % FLANGE_D
    out = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        FLANGE_D / 2.0, FLANGE_T, cq.Vector(0, 0, 0), cq.Vector(0, 0, 1)))
    z_base = FLANGE_T
    out = out.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        BARREL_D / 2.0, BARREL_L, cq.Vector(0, 0, z_base), cq.Vector(0, 0, 1))))
    # THE PITCH RIB, over the winding zone only -- the tail runs stay plain so each
    # tail can lie straight against the barrel while the sleeve holds it there.
    helix = cq.Wire.makeHelix(pitch=PITCH, height=FREE_SPAN, radius=BARREL_D / 2.0)
    # the profile's base is SUNK 0.4 into the barrel. Sitting it exactly on the surface
    # makes the rib tangent to the cylinder it fuses to, and a tangent boolean is the
    # one OCC reliably fails -- it returned a null shape on the first build.
    prof = (cq.Workplane("XZ").center(BARREL_D / 2.0, 0)
            .polyline([(-0.4, -2 * RIB_H), (RIB_H, 0.0), (-0.4, RIB_H)]).close())
    rib = prof.sweep(cq.Workplane("XY").add(helix), isFrenet=True)
    out = out.union(rib.translate((0, 0, z_base + TAIL_RUN + 2 * RIB_H)))
    # THE BASE CLEAT IS A FULL-THICKNESS SLIT, not a notch in the top face, so the tail
    # CARRIES ON DOWN through the flange instead of being turned out +X (user). That
    # turn was the one bend the tool had no business setting: the leg wants this tail
    # axial, and a 90 at the bottom of the axial run undoes what TAIL_RUN is for.
    # Open to the rim, because the cable is pressed in sideways -- both ends of the
    # lead are moulded, so nothing threads. Its inner wall stands off the barrel, so
    # it does not undercut it either.
    out = out.cut(cq.Workplane("XY").box(
        FLANGE_D, CLEAT_W, FLANGE_T + 2.0, centered=(False, True, False))
        .translate((CLEAT_R - CLEAT_W / 2.0, 0, -1.0)))
    # NO TOP CLEAT. It was a notch across the barrel's top face, which bent the
    # finishing tail sideways for exactly the same reason -- and the top has to stay
    # clear anyway, because the set coil comes off by UNSCREWING. The SLEEVE is what
    # holds both tails against the barrel while they set; the last turn only has to be
    # held by hand for the moment it takes to slide the sleeve on.
    assert len(out.val().Solids()) == 1, (
        "the mandrel came out as %d solids" % len(out.val().Solids()))
    return out


def sleeve() -> cq.Workplane:
    """THE OUTER: a plain tube that caps the coil's diameter while it sets, with a notch
    at its foot so it can seat on the flange without crushing the starting tail.

    Drawn where it sits when the assembly is closed, so the pair reads as a pair."""
    z0 = FLANGE_T
    out = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        SLEEVE_OD / 2.0, SLEEVE_L, cq.Vector(0, 0, z0), cq.Vector(0, 0, 1)))
    out = out.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        SLEEVE_ID / 2.0, SLEEVE_L + 2.0, cq.Vector(0, 0, z0 - 1.0), cq.Vector(0, 0, 1))))
    # NO foot notch. The starting tail lives in the flange's top-entry cleat, BELOW the
    # face the sleeve seats on, so there is nothing for the sleeve to clear -- and the
    # notch that used to do it was the sleeve's only overhang.
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
