# -*- coding: utf-8 -*-
"""THE LEG'S BLIND-MATE, ON THE JOINT'S OWN AXIS: a spring-floated jack inside the
fixed TENON, meeting a plug fixed in the body adapter's roof, right down the middle
of the octagon joint the leg already hangs on.

WHY THE MIDDLE (user). The first pass put this in the -X/+Y corner, because the
connector stack was sized against the ADAPTER's depth and only a corner has 52.8 of
it -- on the axis the adapter has 12.8, the mortise being 40 of the 52.8. That was
the wrong part to measure. Put the bulk in the TENON, which is 252 long and solid,
and the axis is not merely possible but better:

  * the octagon joint's OWN 0.3 fit centres the pair. In the corner, two bores 20 off
    the axis had to agree across two parts and two print directions.
  * nothing stands proud. The plug's barrel protrudes, but into the MORTISE, which is
    a pocket 40 deep -- there is no exposed pin to knock.
  * the lead then runs the leg's CORE, which is the path the ADJUST tenon needs
    anyway (user): its ladder holes run along X at y 0, so a few mm of Y clears every
    one of them -- measured O9.2 clear the full 252.

WHERE, EXACTLY. Not the geometric axis: the latch's pocket owns the tenon's middle
(it takes everything y < -3 across x +-6), so the spine steps +Y off it. At
(-1.6, +4.8) the fixed tenon takes O14.8 for its top 46 and O12.8 for its whole
length, with the latch's pocket clear -- measured on the built solid, not derived.

WHAT IT COSTS, and the user chose it: the plug's way IN is a O6.6 hole in the
adapter's top face at that spine, and the MIDDLE RIDGE's root is there. Boring
through a ridge would leave 1.6 slivers, so the ridge is CUT BACK instead -- it
already gives up its inboard end to the service slide, and it now starts at
legs.SIGNAL_RIDGE_IN rather than at the slide. A shortening, not a hole.

HOW IT GOES TOGETHER. The plug drops in from the adapter's top face and PRESSES into
8.0 of O6.0 bore, its back at the channel's floor so the lead folds straight into the
channel and runs out the -Y face, inboard, under the instrument. The jack is dropped
down the tenon's bore onto its coil and is stopped by the THROAT at the tenon's tip --
a O6.6 lip the plug's overmould passes and the jack's O9.7 barrel cannot. At rest the
jack's mouth stands THROAT_L below the tip; the plug's shoulder bottoms it FLOAT
lower, and that FLOAT is how much the latch is allowed to be short.

THE COIL IS NOT THE LATCHES' COIL, and that is the user's call after this joint
turned out to be unbuildable with it. The coil has to end up ON THE LEAD, between the
jack's back and its seat -- and a lead has two ends, the moulded jack (O9.7) and the
moulded far plug (O6.1). A 3.8 ID coil passes neither, so NO assembly order puts it
there; widening every bore to PASS_D was necessary and nowhere near sufficient. (The
install sweep missed it because a swept envelope treats each piece as a free rigid
body and has no notion of one part being THREADED ONTO another.) So this joint gets
its own coil, whose only new requirement is an ID that clears the far plug -- it is
slid onto the lead over that plug before anything goes in the tenon. Everything else
about it is the latch coil's numbers, deliberately: same free length, same rate, so
the force at rest and at seat are unchanged.

It pays for itself twice over: at O8.0 the coil seats DIRECTLY on the tenon's own
O9.9 -> PASS_D step, because a step that stops a O8.0 coil still passes the O6.1 head.
The printed seat washer the O5.0 coil needed is gone.
"""

from __future__ import annotations

import math

import cadquery as cq

from cadkit.holes import teardrop_hole
from . import dimensions as D
from . import latch as LT
from . import leg_stack as LS
from . import legs as LG

B = D.BEAD

# ── the bought parts (BOM.md: the M->F extension cable, and its plug end) ─────
JACK_D = 9.7            # the moulded inline jack's barrel (BOM: 9.1..9.7, pick high)
JACK_L = 40.0           # ...and its length (BOM: <= 40)
# The plug is a REAL PART, off its drawing (user asked for one rather than a
# "confirm at purchase"): Tensility 10-02155, a 3.5 mm 4C plug-to-plug assembly,
# 1830 mm, 28 AWG, $3.73 at DigiKey. The drawing gives the overmould as 6.1 x 14,
# the barrel 3.5 x 14 and the cable 3.8 -- all four numbers below.
PLUG_D = 6.1            # the moulded overmould (10-02155 drawing)
PLUG_L = 14.0           # ...and its length
BARREL_L = 14.0         # the plug's barrel: what actually crosses the joint
BARREL_D = 3.5
CABLE_D = 3.8           # the lead, either side (10-02155's is 3.8). The leg's coil is
                        # slid on over the far PLUG, not the cable, so the cable's own
                        # diameter is no longer a sourcing constraint -- the O6.6 coil
                        # ID clears the O6.1 overmould and everything thinner with it

# ── the float ────────────────────────────────────────────────────────────────
FLOAT = 3.0             # how far the jack is pushed back when the leg latches -- and
                        # so how much SLOP THE LATCH IS ALLOWED: the pair bottoms this
                        # far before the leg is home, so anything from a perfect latch
                        # to this much short of one still seats the connector
SPR_WIRE = 0.7          # THIS JOINT'S OWN COIL (see the docstring), and the number
SPR_OD = 8.0            # that makes it its own SKU is the ID: it is slid onto the lead
SPR_ID = SPR_OD - 2 * SPR_WIRE          # 6.6 -- clears the far plug's O6.1 overmould by
                                        # 0.5, which is the assert's floor plus a tenth.
                                        # uxcell B0C33C21K9, 304 SS, $6.29 for 5
# THE COIL IS A BOUGHT PART AND THESE ARE ITS NUMBERS, not the latch coil's.
# uxcell B0GCZKKCFP-family: 304 SS, O8.0 OD x 0.7 wire x 20.0 FREE (BOM). The first
# pass borrowed latch.SPR_FREE (12.0) and a 2.5 N/mm rate, which described a coil
# nobody sells in this ID -- the whole reason this joint has its own SKU is that the
# ID has to clear the lead's O6.1 moulded plug, and at O8.0/0.7 that means 6.6.
SPR_FREE = 20.0
SPR_TURNS_MAX = 14      # WHAT WE DO NOT KNOW is the coil count, and it is the coil
                        # count -- not the rate -- that can make this joint
                        # unbuildable, because solid height is what the mate has to
                        # clear. uxcell publishes neither turns nor rate, so this is a
                        # BOUND rather than a count: 20.0 of free length on 0.7 wire is
                        # 10 turns at a 2.0 pitch and 14 at 1.4, and past that the coil
                        # would be nearly closed at rest. The chain hangs off the worst
                        # case, not off a guess at the real one
SPR_SOLID = SPR_TURNS_MAX * SPR_WIRE                            # 9.8
SPR_RATE = 0.75         # N/mm, ESTIMATED and bracketed 0.6-0.9: McMaster publishes
                        # 1.91 for a O8.8 x 0.8 x 14.5 and 0.76 for a O8.63 x 0.63 x 16,
                        # and this one is longer than either at a smaller OD, so more
                        # coils and softer. MEASURE ON ARRIVAL -- PRELOAD_TARGET below
                        # turns it straight into the installed length

# THE INSTALLED LENGTH TARGETS THE PRELOAD, now that the rate is a published number
# rather than a bracket. 5.0 N is what this joint was designed around: it is what holds
# the jack up against its keeper with the leg off, and the keeper's TPU lugs carry it.
# The old hardcoded 10.0 is gone either way -- against a real catalogue coil it would
# have sat wherever the arithmetic left it.
PRELOAD_TARGET = 5.0
_SOLID_FLOOR = SPR_SOLID + 1.0 + FLOAT          # the coil must STILL be clear of solid
                                                # once the leg latches and the jack has
                                                # given up FLOAT. This is a floor, not a
                                                # preference, and on a soft coil it wins
SPR_REST_L = max(SPR_FREE - PRELOAD_TARGET / SPR_RATE, _SOLID_FLOOR)    # 13.8
                                                # -- the floor, here: at 0.75 N/mm the
                                                # target would want 13.33 and go solid
SPR_MATE_L = SPR_REST_L - FLOAT
PRELOAD_N = (SPR_FREE - SPR_REST_L) * SPR_RATE                  # ~4.7 N standing still
MATE_N = (SPR_FREE - SPR_MATE_L) * SPR_RATE                     # ~6.9 N seated
assert PRELOAD_N >= 3.0, (
    "only %.1f N holds the jack against its keeper with the leg off -- the coil's rate "
    "or its free length is not carrying the preload any more" % PRELOAD_N)
assert SPR_ID >= PLUG_D + 0.4, (
    "a %.1f ID coil will not slide over the lead's %.1f far plug -- this joint is "
    "unbuildable, which is the whole reason it has its own SKU" % (SPR_ID, PLUG_D))
assert SPR_MATE_L >= SPR_SOLID + 1.0, (
    "the coil is %.2f from solid when the leg latches -- no room for the latch's own "
    "slop" % (SPR_MATE_L - SPR_SOLID))

# ── the spine: off the axis by just enough to clear the latch's pocket ───────
AX_X = -2 * B           # -1.6
AX_Y = 7 * B            # +5.6 -- the latch's pocket takes the tenon's -Y middle
THROAT_D = PLUG_D + 0.5         # 6.6: the plug's overmould passes, the jack does not.
                                # This lip is the jack's up-stop with the leg off -- and
                                # it is a separate PRESSED PART, not a step in the bore,
                                # for the same reason the coil's seat is: the jack is
                                # O9.7 and goes in from the tip, so a 6.6 step above it
                                # is a lid on a box with the box already shut. The first
                                # pass cut it as a bore and the cavity had O6.6 at BOTH
                                # ends, which the user spotted in the tab
# ── THE PLUG IS HELD BY A TPU SLEEVE ON A BAYONET (user), not by a press ─────
# The press it replaces was the joint's one un-numbered assumption. What loads it is
# not the plug's weight (2 g) but the TRRS pair's own EXTRACTION FORCE, applied every
# time the leg comes off: the jack follows the plug for FLOAT on its coil, hits the
# keeper, and the remaining BARREL_L has to be dragged out -- reacted straight into
# whatever holds the plug. A O6.1 overmould in a O6.0 printed bore gives 6-48 N
# depending on the overmould's modulus, against a 3.5 mm plug's 5-20 N of detent; and
# PLUG_D is the HIGH end of the drawing's range, so a plug that measures 5.95 has no
# press at all. The user found this by asking what stops the plug falling -Z, and the
# honest answer was "friction we never sized".
#
# So: a TPU cup grips the overmould, and the cup is locked into the adapter by a
# quarter-turn bayonet. The grip is still friction, but it is friction we CONTROL --
# an elastomer at SLV_SQUEEZE does not care whether the plug came in at 5.9 or 6.2,
# where a rigid press goes to zero. The bayonet is positive: the sleeve cannot come
# -Z without rotating, and it cannot rotate once the instrument is assembled, because
# the leads it carries are folded into CHAN_W of rectangular channel that the chassis
# closes over. Rotation is free exactly when you need it -- with the adapter off the
# instrument and the far end of the lead still bare (user).
#
# It also ends the plug's COCK. A preloaded elastomer has no slop, where the press
# had 0.15 and 1.79 degrees with it.
SLV_SQUEEZE = 0.4               # the sleeve's interference on the overmould. 0.4 and
                                # not 0.1: TPU is the compliant half, so this can
                                # swallow the bought part's whole tolerance band
SLV_ID = PLUG_D - SLV_SQUEEZE   # 5.7
SLV_OD = 12 * B                 # 9.6, leaving the cup a 1.95 wall at the grip
SLV_CLR = 0.4                   # ...and a running clearance, because it has to TURN
CB_D = SLV_OD + SLV_CLR         # 10.0: the counterbore it turns in
CB_ROOF = 2 * B                 # 1.6 of adapter left over the counterbore, which the
                                # sleeve's flange bears up against and the leads pass
                                # through on their way into the channel
LUG_PROUD = 1.8                 # how far the bayonet lugs stand off the barrel, and
                                # it is the LUG'S OWN THICKNESS that sets it, not the
                                # ledge's. These lugs are TPU, and the recorded print
                                # finding is that sub-1.6 TPU rails TEAR
                                # (cadkit/JOINERY_README) -- at 1.2 the keeper's came
                                # out 0.86 (tools/check_thin). Pushed out to where the
                                # TENON stops it: the keeper's slot sweeps to 104
                                # degrees, where the octagon runs out at r 8.45, so a
                                # slot at 6.8 keeps MIN_WALL_2P and not a thou more
LUG_D = CB_D + 2 * LUG_PROUD    # 12.4 over the lugs
LUG_SLOT_H = 3 * B              # 2.4: the slot the lug turns in...
LUG_H = LUG_SLOT_H + 0.2        # ...and the lug is 0.2 TALLER. That 0.2 is the joint's
                                # preload: a rigid bayonet needs a spring behind it or
                                # it rattles, and in TPU the lug IS the spring.
                                # THREE BEADS AND NOT TWO because the lug's free face is
                                # chamfered 45 for printability, and a 45 chamfer eats
                                # LUG_PROUD of height: at 1.6 the lug tapered to a 0.15
                                # knife at its outer edge, which is under a bead and
                                # which tools/check_thin cannot see (it rejects knife
                                # edges by design). At 2.4 the tip is 0.95
LUG_LEDGE = 2 * B               # 1.6 of adapter under the slot -- the ledge the lug
                                # actually sits on, and the only thing in the -Z load
                                # path once the quarter turn is made
LUG_DEG = 30.0                  # each lug's arc; two of them, opposed
LUG_TURN = 46.0                 # ...and how far it turns. The run is cut LUG_CLR_DEG
LUG_CLR_DEG = 4.0               # wider at each end, and the far end is the hard stop.
                                # NEITHER NUMBER IS FREE, and both were set by measuring
                                # the hosts rather than by choosing a round fraction:
                                #  * the SLOT sweeps LUG_DEG + LUG_TURN + 8 = 108, and
                                #    in the TENON it has to miss the thin arc: the wall
                                #    round the keeper's counterbore falls to 1.65 over
                                #    110-170 degrees, so a slot reaching past ~115 puts
                                #    the octagon under the floor. 60+90 would sweep 158
                                #    and go straight through it.
                                #  * the TURN has to carry the lugs past each bore's
                                #    TEARDROP APEX, which is a void in the very ledge
                                #    they land on. At 45 degrees of turn the keeper's
                                #    second lug landed on the apex and kept just 15 of
                                #    its 30 degrees of ledge.
                                #  * and every slot END WALL has to be PRINTABLE. An end
                                #    wall is a plane through the bore's axis, so its
                                #    normal lies in the plane that contains the build
                                #    direction, and it overhangs by |sin(U - theta)| --
                                #    U the build azimuth, theta the wall's. That is
                                #    within 45 degrees only when the wall sits near the
                                #    build axis or square across it. Six walls, two
                                #    parts, two different build directions: solved by
                                #    SEARCH over (turn, clocking), and 46 is the largest
                                #    turn for which a clocking exists on BOTH parts
SLV_A = (52.0, 232.0)           # where each joint's slots START. Different numbers
KEEP_A = (6.0, 186.0)           # because the two apexes point different ways: the
                                # adapter prints +Y and the tenon -X-Y, and each part's
                                # bores peak toward its own print_up
JACK_BORE_D = JACK_D + 0.2      # 9.9: the jack runs free in the tenon
PASS_D = PLUG_D + 0.5           # 6.6: every bore below the throat is at least this,
                                # because the lead's FAR PLUG has to travel the whole
                                # length of the tenon and out the bottom. A O4.8 cable
                                # bore looks right and cannot be assembled (user).
THROAT_BORE_D = 10.3                    # the keeper sits in a COUNTERBORE at the
                                        # tip, not in the jack's own bore, so its wall
                                        # is not taken out of the O6.6 the plug has to
                                        # pass. The octagon takes O14.00 here
                                        # (measured), so this leaves the tenon 1.85 --
                                        # and the last tenth came off it so the LUG
                                        # could have 1.60: the lug is the span between
                                        # this circle and LUG_D, and both ends of that
                                        # span are pinned by walls
KEEP_CLR = 0.2                          # ...and the keeper TURNS in it with this much
                                        # clearance, because THE KEEPER IS TPU ON THE
                                        # SAME BAYONET (user). What it replaces was a
                                        # press plus a O2 TPU pin, and the pin could not
                                        # answer the obvious question: there was no way
                                        # to get it back OUT. A TPU pin normally stands
                                        # proud so you have something to pull, and this
                                        # one cannot -- its flank is the one that slides
                                        # into the mortise with 0.15 of clearance.
                                        # A bayonet has the extraction built in: turn it
                                        # an eighth and lift. And what stops it turning
                                        # on its own is what made the pin unnecessary to
                                        # begin with -- with the leg ON, the mortise roof
                                        # lies flat on the keeper's top face, so the
                                        # axial half of the release cannot happen at all
KEEP_DRIVE_W = 2 * B                    # two radial notches across the keeper's mouth,
KEEP_DRIVE_DP = 2 * B                   # deep enough to take a flat blade. That is the
                                        # whole tool: the bore is O6.6 and open to the
                                        # tip, so an ordinary screwdriver spans it
LEAD_BORE_D = 6 * B             # 4.8 -- the SLEEVE'S flange bore, and the plug does
                                # not come down through it.
                                # THE LEAD IS A PIGTAIL NOW (user): the far end is bare
                                # wire crimped to a JST-XH at the station, not a second
                                # moulded plug. That buys three things at once.
                                #  1. the plug goes in from BELOW, up from the mortise,
                                #     and this bore is a POSITIVE up-stop -- a step the
                                #     O6.1 overmould cannot pass. The printed cap that
                                #     used to do that job is gone.
                                #  2. the four leads thread up it easily, so nothing
                                #     wide has to reach the top face: the mouth drops
                                #     from O8.8 to O4.8 and the middle ridge gets 2.4 of
                                #     its length back (legs.SIGNAL_RIDGE_IN).
                                #  3. the 90 degree turn into the channel happens in
                                #     BARE 28 AWG leads, not in a O3.8 jacketed cable.
                                #     The bend was the whole problem -- 6.5 of radius on
                                #     a 3.8 cable is 1.7x OD, well under the 3x a static
                                #     install wants. Stripped, it is a non-question.
THROAT_LEAD_D = 9.0             # the keeper's MOUTH, opened 45 from its O6.6 bore.
                                # THE KEEPER IS THE LEG'S HIGHEST FEATURE, so its bore
                                # is the first thing the plug's barrel meets on the way
                                # in -- and a bare O6.6 against a O3.5 barrel is only
                                # 1.55 of radial capture. The plug is a cantilever off
                                # PLUG_GRIP of bore, and a slack-printed press lets it
                                # cock: 0.15 of slop is 3.6 degrees is 1.60 at the
                                # barrel's tip. That JAMS THE LEG (user). Opened to 9.0
                                # the capture is 2.75, which swallows it.
CHAN_W = CABLE_D + 1.0          # 4.8 wide and deep: the groove in the adapter's top
CHAN_D = CABLE_D + 1.0          # face the lead is folded into

# ── the z chain, all of it hung off the tenon's tip ───────────────────────────
TIP = LS.Z_MORTISE_ROOF         # -94.55: the tenon's tip, and the mortise's roof
PLUG_GRIP = 6 * B               # 4.8 -- and it is the PLUG'S WRAP, the one number
                                # that keeps the male end pointing straight with the leg
                                # off (user: "if the male end is pointing off axis it
                                # won't meet the female and the leg will jam").
                                # Shortening the tenon and the mortise does NOT buy this
                                # -- TIP cancels out of wrap = PLUG_L - FLOAT - THROAT_L,
                                # checked at roof shifts of 0, -5 and -10 (wrap 2.40 in
                                # all three). The only lever is what the keeper spends,
                                # and a O7.6 button head was spending 8.6 of the 11.0 on
                                # a screw that sits on the REMOVABLE LEG and does nothing
                                # for the plug at all (user). A O3 PIN needs 2.12 of
                                # radius, not 4.2, so the keeper drops to 6.2 and the
                                # wrap doubles
PLUG_TOP = TIP + PLUG_GRIP      # THE KEEPER GETS THE HEIGHT (user: make the throat
                                # taller so the screw can be straight). THROAT_L and
                                # PLUG_GRIP share a fixed 11.0 -- both come off this one
                                # number -- so every mm the keeper gains, the plug's
                                # press gives up. A STRAIGHT O7.6 button needs the
                                # keeper at 7.8 (see LOCK_Z), which leaves the press
                                # 3.2, and 3.2 cannot hold MATE_N. So the plug stops
                                # relying on its press at all: cap() gives it a POSITIVE
                                # up-stop and the press only has to keep it from
                                # dropping out while the leg is off
PLUG_SHOULDER = PLUG_TOP - PLUG_L               # -100.55, and the jack's mouth when
                                                # the leg is home
THROAT_L = TIP - (PLUG_SHOULDER + FLOAT)        # 3.0: how far below the tip the jack's
                                                # mouth rests. It falls out of the chain
                                                # -- it is not a free number
SLV_BOT = TIP                                   # the cup's mouth, flush with the
                                                # mortise roof: below this the
                                                # overmould has to pass the keeper's
                                                # THROAT_D, which leaves 0.25 of wall.
                                                # There is no sleeve down there
SLV_TOP = (LS.Z_TOP - CHAN_D) - CB_ROOF         # ...and its flange's top face
SLV_H = SLV_TOP - SLV_BOT                       # 6.4: PLUG_GRIP of cup plus CB_ROOF of
                                                # flange
LUG_BOT = SLV_BOT + LUG_LEDGE                   # where the lugs sit once turned home
assert SLV_TOP > PLUG_TOP, (
    "the sleeve's flange has nowhere to be: the plug's top is %.2f and the counterbore's"
    " roof starts at %.2f" % (PLUG_TOP, SLV_TOP))
assert LUG_BOT + LUG_H <= PLUG_TOP, (
    "the bayonet lugs (%.2f..%.2f) reach above the plug's top %.2f, so they would be "
    "trying to squeeze the flange rather than the grip"
    % (LUG_BOT, LUG_BOT + LUG_H, PLUG_TOP))

JACK_REST = PLUG_SHOULDER + FLOAT               # -97.55, the jack's mouth at rest
JACK_BACK = PLUG_SHOULDER - JACK_L              # -140.55 seated, FLOAT higher at rest
SPR_SEAT = (JACK_BACK + FLOAT) - SPR_REST_L     # -147.55: the coil's floor, and the
                                                # tenon's own O9.9 -> PASS_D step

assert THROAT_L >= D.MIN_WALL_2P, (
    "the throat is %.2f -- too thin a lip to stop the jack" % THROAT_L)
# THE KEEPER'S BAYONET, measured down from the tenon's tip. The keeper drops in from
# the tip and turns, so the ledge that holds it is ABOVE its lugs -- the jack pushes it
# +Z, and LUG_LEDGE of octagon over the slot is what takes that.
KEEP_SLOT_HI = TIP - LUG_LEDGE
KEEP_SLOT_LO = KEEP_SLOT_HI - LUG_SLOT_H
assert KEEP_SLOT_LO - JACK_REST >= D.MIN_WALL_2P, (
    "the keeper's bayonet reaches down to %.2f and the jack's mouth is at %.2f -- less "
    "than MIN_WALL_2P of keeper below the lugs to actually stop it with"
    % (KEEP_SLOT_LO, JACK_REST))

assert PLUG_GRIP >= 3 * D.BEAD, (
    "only %.1f of press guides the plug in the adapter's roof. It no longer "
    "CARRIES the mate force -- cap() does -- but it is still what keeps a "
    "14-long overmould concentric and stops it dropping out with the leg off"
    % PLUG_GRIP)

# the plug's way in is a hole in the adapter's TOP FACE, and the middle ridge's root
# is there. legs cuts that ridge back for us; check it actually clears, apex included
_MOUTH_PEAK = AX_Y + (LEAD_BORE_D / 2.0) * 2 ** 0.5     # the teardrop's apex, toward +Y
assert LG.SIGNAL_RIDGE_IN >= _MOUTH_PEAK + D.MIN_WALL_2P, (
    "the middle ridge starts at %+.2f but the plug's mouth reaches %+.2f -- boring "
    "through a ridge leaves slivers; legs.SIGNAL_RIDGE_IN has to clear it"
    % (LG.SIGNAL_RIDGE_IN, _MOUTH_PEAK))


def _ax(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    return sx + AX_X, ly + AX_Y


def _bore(d, z0, z1, x, y, up):
    return teardrop_hole(d, z1 - z0, (x, y, z0), (0, 0, 1), up)


def chan_pts(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """The channel's centreline on the adapter's top face: straight out of the plug's
    mouth and down the part to the -Y face. It needs no dog-leg any more -- on the
    axis there is no tongue in the way."""
    x, y = _ax(sx, ly)
    return [(x, y), (x, ly - LS.LEG_W / 2.0 - 1.0)]


def channel(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """That path as a groove in the top face. It runs ALONG this part's build
    direction, so both its walls are vertical and it has no ceiling at all."""
    a, b = chan_pts(sx, ly)
    return (cq.Workplane("XY")
            .box(CHAN_W, a[1] - b[1], CHAN_D + 1.0, centered=(True, False, False))
            .translate((a[0], b[1], LS.Z_TOP - CHAN_D)))


def _sector(r_in, r_out, z0, z1, a0, sweep, x, y):
    """An annular WEDGE about the spine: r_in..r_out, z0..z1, sweeping `sweep` degrees
    from `a0`. Every bayonet feature in this module is one of these."""
    w = cq.Solid.makeCylinder(r_out, z1 - z0, cq.Vector(0, 0, z0), cq.Vector(0, 0, 1),
                              angleDegrees=sweep)
    if r_in > 0.0:
        w = w.cut(cq.Solid.makeCylinder(r_in, z1 - z0 + 2.0, cq.Vector(0, 0, z0 - 1.0),
                                        cq.Vector(0, 0, 1)))
    return cq.Workplane("XY").add(w.rotate((0, 0, 0), (0, 0, 1), a0)).translate((x, y, 0))


def _td_sector(r_in, r_out, z0, z1, a0, sweep, x, y, up):
    """An annular wedge whose OUTER boundary is a teardrop, not a circle.

    A plain annular slot is a groove round a bore that is HORIZONTAL in the print, and
    wherever the groove passes within 45 degrees of the build direction its outer wall
    becomes a roof over open air. Cutting it to a teardrop of the same radius replaces
    exactly that arc -- the cap spans +-45 of `up` and nowhere else -- with two 45
    degree faces, so the slot is self-supporting at every clocking (user: no overhangs
    past 45). It also swallows the SLIVER the plain slot used to leave where its end
    ran up against the counterbore's own teardrop apex, which the user spotted at 214
    degrees on the tenon: the two apexes are now the same apex."""
    wedge = cq.Solid.makeCylinder(r_out * 2.0, z1 - z0, cq.Vector(0, 0, z0),
                                  cq.Vector(0, 0, 1), angleDegrees=sweep)
    wedge = cq.Workplane("XY").add(
        wedge.rotate((0, 0, 0), (0, 0, 1), a0)).translate((x, y, 0))
    td = teardrop_hole(2.0 * r_out, z1 - z0, (x, y, z0), (0, 0, 1), up)
    out = td.intersect(wedge)
    if r_in > 0.0:
        out = out.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            r_in, z1 - z0 + 2.0, cq.Vector(x, y, z0 - 1.0), cq.Vector(0, 0, 1))))
    return out


def _bayonet_slots(r_in, r_out, z_lo, z_hi, open_up, x, y, angles, up):
    """The L-slots a set of lugs turns in: an ENTRY run open to one end, and the
    circumferential RUN it turns along. `open_up` says which end the lugs come in
    from -- True for the adapter's sleeve (pushed UP from the mortise), False for the
    tenon's keeper (dropped DOWN onto the tip)."""
    out = None
    for a0 in angles:
        # the entry is open to the part's end; the run is buried LUG_LEDGE inside it
        e0, e1 = ((z_lo - LUG_LEDGE - 1.0, z_hi) if open_up
                  else (z_lo, z_hi + LUG_LEDGE + 1.0))
        cut = _td_sector(r_in, r_out, e0, e1,
                         a0 - LUG_CLR_DEG, LUG_DEG + 2 * LUG_CLR_DEG, x, y, up)
        cut = cut.union(_td_sector(r_in, r_out, z_lo, z_hi, a0 - LUG_CLR_DEG,
                                   LUG_DEG + LUG_TURN + 2 * LUG_CLR_DEG, x, y, up))
        out = cut if out is None else out.union(cut)
    return out


def _lugs(r_in, r_out, z_lo, z_hi, x, y, angles, bear_up):
    """The lugs themselves, drawn WHERE THEY END UP -- a turn along the run from the
    entry, hard against the stop.

    ONE FACE OF A LUG IS THE BEARING FACE and the other is dead weight, so the dead one
    is chamfered at 45 and the part is printed with the bearing face pointing AWAY from
    the bed. A lug is LUG_PROUD of unsupported eave otherwise, which in TPU droops.
    `bear_up` says which face carries: True for the keeper (the coil pushes it +Z into
    a ledge above), False for the sleeve (the plug's extraction pulls it -Z onto a
    ledge below)."""
    out = None
    h = r_out - r_in
    if bear_up:                      # keep the TOP square, chamfer underneath
        cone = cq.Solid.makeCone(r_in, r_in + h, h, cq.Vector(x, y, z_lo),
                                 cq.Vector(0, 0, 1))
        band = cq.Solid.makeCylinder(r_out + 1.0, h, cq.Vector(x, y, z_lo),
                                     cq.Vector(0, 0, 1))
    else:                            # keep the BOTTOM square, chamfer on top
        cone = cq.Solid.makeCone(r_in + h, r_in, h, cq.Vector(x, y, z_hi - h),
                                 cq.Vector(0, 0, 1))
        band = cq.Solid.makeCylinder(r_out + 1.0, h, cq.Vector(x, y, z_hi - h),
                                     cq.Vector(0, 0, 1))
    chamfer = cq.Workplane("XY").add(band.cut(cone))
    for a0 in angles:
        w = _sector(r_in, r_out, z_lo, z_hi, a0 + LUG_TURN, LUG_DEG, x, y)
        out = w if out is None else out.union(w)
    return out.cut(chamfer)


def adapter_negatives(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, up=None):
    """Cut in the BODY ADAPTER: the counterbore the TPU sleeve turns into, its bayonet
    slots, the lead bore through the counterbore's roof, and the channel above.

    There is no press here any more. What used to hold the plug was a O6.1 overmould in
    a O6.0 bore, and the user asked the question that has no good answer: with the leg
    off, what stops it falling -Z? Friction, sized at somewhere between 6 and 48 N
    depending on a modulus nobody published -- against a plug detent of 5-20 N that
    pulls on it every single time the leg comes off."""
    x, y = _ax(sx, ly)
    up = up or LS.PRINT_UP["body_adapter"]
    out = _bore(CB_D, SLV_BOT - 0.01, SLV_TOP, x, y, up)          # the sleeve's barrel
    out = out.union(_bayonet_slots(CB_D / 2.0 - 0.01, LUG_D / 2.0,
                                   LUG_BOT, LUG_BOT + LUG_SLOT_H, True, x, y, SLV_A, up))
    out = out.union(_bore(LEAD_BORE_D, SLV_TOP, LS.Z_TOP + 0.01, x, y, up))
    return out.union(channel(sx, ly))


def sleeve(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """THE MALE PLUG'S RETAINER: a TPU cup that grips the overmould and locks into the
    adapter on a bayonet (user's design).

    Two things it fixes at once. RETENTION is no longer a rigid press whose interference
    disappears if the bought plug measures at the low end of its drawing -- an elastomer
    at SLV_SQUEEZE does not care, and the bayonet means the last word is a mechanical
    ledge rather than friction at all. And the plug can no longer COCK: the press had
    0.15 of slop in it, which is 1.79 degrees at the barrel's tip, and a preloaded
    elastomer has none.

    It only wraps PLUG_GRIP of the plug, not all 14 -- below the mortise roof the
    overmould has to pass the keeper's THROAT_D, which leaves 0.25 of wall.

    You turn it by turning the PLUG: the cup grips the overmould far harder than the
    lugs need, so there is no driver feature and nothing to reach into the mortise with.
    What stops it turning back is the lead itself -- folded into CHAN_W of rectangular
    channel that the chassis closes over, it cannot rotate, and the only free length is
    the few mm of round bore above the flange."""
    x, y = _ax(sx, ly)
    body = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        SLV_OD / 2.0, SLV_H, cq.Vector(x, y, SLV_BOT), cq.Vector(0, 0, 1)))
    body = body.union(_lugs(SLV_OD / 2.0 - 0.01, LUG_D / 2.0 - SLV_CLR / 2.0,
                            LUG_BOT - (LUG_H - LUG_SLOT_H) / 2.0,
                            LUG_BOT + LUG_SLOT_H + (LUG_H - LUG_SLOT_H) / 2.0,
                            x, y, SLV_A, False))
    # the grip bore, then the flange the plug's top bottoms on
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        SLV_ID / 2.0, PLUG_GRIP + 1.0, cq.Vector(x, y, SLV_BOT - 1.0),
        cq.Vector(0, 0, 1))))
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        LEAD_BORE_D / 2.0, SLV_H + 2.0, cq.Vector(x, y, SLV_BOT - 1.0),
        cq.Vector(0, 0, 1))))
    assert len(body.val().Solids()) == 1, (
        "the sleeve came out as %d solids -- see throat()" % len(body.val().Solids()))
    return body


def tenon_negatives(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, up=None,
                    bot: float = None):
    """Cut in the FIXED TENON: one straight O9.9 bore from the tip down past the jack
    and the coil to the ledge their SEAT rests on, then a pass-through the rest of the
    way that is wide enough for the lead's far plug. Nothing narrows on the way in --
    everything that has to get past goes in from the tip, in order."""
    x, y = _ax(sx, ly)
    up = up or LS.PRINT_UP["fixed_tenon"]
    bot = LS.Z_FIX_TEN_BOT - 1.0 if bot is None else bot
    out = _bore(JACK_BORE_D, SPR_SEAT, TIP + 1.0, x, y, up)     # ONE bore, tip to step
    out = out.union(_bore(THROAT_BORE_D, JACK_REST, TIP + 1.0, x, y, up))  # the keeper's
    out = out.union(_bayonet_slots(THROAT_BORE_D / 2.0 - 0.01, LUG_D / 2.0,
                                   KEEP_SLOT_LO, KEEP_SLOT_HI, False, x, y, KEEP_A, up))
    return out.union(_bore(PASS_D, bot, SPR_SEAT + 0.01, x, y, up))


def throat(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """THE JACK'S UP-STOP at the tenon's tip: a TPU ring on a bayonet (user).

    It cannot be a step in the bore. The jack is O9.7 and can only go in from the tip,
    so anything narrower than 9.7 above it is a lid fitted before the box is filled --
    which is exactly what the first pass drew, a O9.8 cavity with O6.6 at both ends and
    no way to put a jack in it (user). So the lip arrives after the jack, as its own
    part, bored THROAT_D so the plug's overmould still passes.

    WHY IT TURNS IN rather than presses. It was a PCTG ring on a press, locked by a O2
    TPU pin through the tenon's flank -- and the pin had no way out. A TPU pin usually
    stands proud so there is something to pull on; this one could not, because the flank
    it sits in is the one that enters the mortise with 0.15 of clearance (user). A
    bayonet carries its own extraction: put a blade in the drive notches, turn an eighth,
    lift. Nothing is proud of anything.

    Nor can it turn itself loose. A bayonet releases by turning AND THEN lifting, and
    with the leg on, the adapter's mortise roof lies flat on this face -- the lift is
    blocked before the turn matters. With the leg off there is nothing pulling on it:
    the coil's 5 N is the whole load, and the lugs carry that against LUG_LEDGE of
    octagon.

    It is TPU for the same reason the sleeve is: an elastomer lug LUG_H tall in a
    LUG_SLOT_H slot is its own spring, so the joint is preloaded and cannot rattle,
    where a rigid bayonet this size would need a wave washer behind it."""
    x, y = _ax(sx, ly)
    r = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        (THROAT_BORE_D - KEEP_CLR) / 2.0, THROAT_L,
        cq.Vector(x, y, JACK_REST), cq.Vector(0, 0, 1)))
    r = r.union(_lugs((THROAT_BORE_D - KEEP_CLR) / 2.0 - 0.01,
                      LUG_D / 2.0 - KEEP_CLR / 2.0,
                      KEEP_SLOT_LO - (LUG_H - LUG_SLOT_H) / 2.0,
                      KEEP_SLOT_HI + (LUG_H - LUG_SLOT_H) / 2.0, x, y, KEEP_A,
                      True))
    r = r.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        THROAT_D / 2.0, THROAT_L + 2.0,
        cq.Vector(x, y, JACK_REST - 1.0), cq.Vector(0, 0, 1))))
    # the LEAD-IN: a 45 funnel at the top, catching a barrel that arrives off axis
    r = r.cut(cq.Workplane("XY").add(cq.Solid.makeCone(
        THROAT_D / 2.0, THROAT_LEAD_D / 2.0, (THROAT_LEAD_D - THROAT_D) / 2.0,
        cq.Vector(x, y, TIP - (THROAT_LEAD_D - THROAT_D) / 2.0), cq.Vector(0, 0, 1))))
    # ...and the DRIVE: two notches across the mouth, square to the lugs so the blade
    # is turning on the thickest part of the ring
    for a in (KEEP_A[0] + LUG_TURN + LUG_DEG / 2.0 + 90.0,):
        cut = (cq.Workplane("XY")
               .box(THROAT_BORE_D + 2.0, KEEP_DRIVE_W, KEEP_DRIVE_DP, centered=True)
               .translate((0, 0, TIP - KEEP_DRIVE_DP / 2.0))
               .rotate((0, 0, 0), (0, 0, 1), a).translate((x, y, 0)))
        r = r.cut(cut)
    assert len(r.val().Solids()) == 1, (
        "the keeper came out as %d solids -- its lugs are drawn off a radius the ring "
        "does not reach, so they float. KEEP_CLR shrinks the ring away from the bore "
        "the lugs are sized against, and the lugs have to start from the RING"
        % len(r.val().Solids()))
    return r


def _run(pts, d=CABLE_D):
    """A cable through `pts`: cylinders with balls at the corners."""
    out = None
    for a, b in zip(pts, pts[1:]):
        v = cq.Vector(*b) - cq.Vector(*a)
        seg = cq.Solid.makeCylinder(d / 2.0, v.Length, cq.Vector(*a), v.normalized())
        out = seg if out is None else out.fuse(seg)
    for q in pts[1:-1]:
        out = out.fuse(cq.Solid.makeSphere(d / 2.0, cq.Vector(*q)))
    return cq.Workplane("XY").add(out)


def cables(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, k: int = 0):
    """THE RUN, drawn -- a hole in a face with nothing coming out of it reads as a
    mystery (user saw exactly that on the first pass).

    The patch lead leaves the plug's back AT the channel's floor, runs straight down
    the adapter's top face and out the -Y one -- inboard, under the instrument, where
    nothing shows from the front -- then along the underside to the jack in the
    chassis floor. Below the joint, the leg's own lead drops from the floating jack's
    back down the middle of the tenon, which is where the adjust tenon will want it."""
    x, y = _ax(sx, ly)
    _, b = chan_pts(sx, ly)
    fold = LS.Z_TOP - CHAN_D / 2.0
    from . import electronics as EL                      # late: sizes only
    from . import wiring as WR                           # late: wiring reads chassis
    tail = WR.trrs_mouth_z() - EL.TRRS_PLUG_RUN          # the station plug's free end
    patch = _run([(x, y, PLUG_TOP),                             # the plug's back
                  (x, y, fold),                                 # folded into the channel
                  (b[0], b[1] + 1.0, fold),                     # out the -Y face
                  (b[0], b[1] - 4.0, fold),                     # clear of it
                  (b[0], WR.TRRS_Y - 10.0, fold),               # -Y FIRST, then across:
                  (WR.TRRS_X, WR.TRRS_Y - 10.0, fold),          # the diagonal ran
                                    # through the station plug's O10 barrel, which hangs
                                    # 13 below this plane. 10 of Y offset clears it
                  (WR.TRRS_X, WR.TRRS_Y - 10.0, tail - CABLE_D / 2.0 - 0.3),
                  (WR.TRRS_X, WR.TRRS_Y, tail - CABLE_D / 2.0 - 0.3),
                  (WR.TRRS_X, WR.TRRS_Y, tail)])                # and UP into the jack.
                                    # It stops AT the plug's tail and comes at it FROM
                                    # BELOW. The first pass ran straight down the
                                    # station's axis from the channel, which is 16.75 of
                                    # cable drawn inside the plug's own body -- the
                                    # station's mouth faces -Z (user), so its plug hangs
                                    # BELOW the adapter's top face, not above it
    leg = _run([(x, y, JACK_BACK), (x, y, JACK_BACK - 40.0)])
    return [("leg_trrs_patch_%d" % k, patch), ("leg_trrs_leg_lead_%d" % k, leg)]


def spring_coil(x, y, mated: bool = True):
    """THE FLOAT COIL, drawn as a coil. It used to be an annular TUBE -- the coil's
    swept envelope, which is the right thing to hand the overlap gate and the wrong
    thing to put in front of a person: it reads as a solid ring, and it hides the one
    number the whole z-chain was just hung off, which is the turn count (user asked).

    Same construction as latch.spring_coil and the same documented simplification:
    uniform pitch, so the closed-and-ground end coils are drawn pitched rather than
    touching. Nothing downstream cares -- OD sets the bore fit, overall length sets the
    gap, and solid height is turns x wire either way.

    Drawn at SPR_TURNS_MAX, the WORST-case count the chain is designed against, not at
    a guess at the real one. When the spring arrives and the turns are counted, this
    picture corrects itself along with the geometry."""
    L = SPR_MATE_L if mated else SPR_REST_L
    r_mid = (SPR_OD - SPR_WIRE) / 2.0
    path_h = L - SPR_WIRE
    wire = cq.Wire.makeHelix(pitch=path_h / SPR_TURNS_MAX, height=path_h, radius=r_mid)
    coil = (cq.Workplane("XZ").center(r_mid, 0).circle(SPR_WIRE / 2.0)
            .sweep(cq.Workplane("XY").add(wire), isFrenet=True))
    return coil.translate((x, y, SPR_SEAT + SPR_WIRE / 2.0))


def dummies(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, k: int = 0, mated: bool = True):
    """The bought parts where they sit. `mated` is the latched state: the jack pushed
    back FLOAT off its throat, its coil that much shorter."""
    x, y = _ax(sx, ly)
    back = 0.0 if mated else FLOAT
    plug = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        PLUG_D / 2.0, PLUG_L, cq.Vector(x, y, PLUG_SHOULDER), cq.Vector(0, 0, 1)))
    plug = plug.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        BARREL_D / 2.0, BARREL_L, cq.Vector(x, y, PLUG_SHOULDER - BARREL_L),
        cq.Vector(0, 0, 1))))
    mouth = PLUG_SHOULDER + back                 # the jack's mouth: it is what moves
    jack = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        JACK_D / 2.0, JACK_L, cq.Vector(x, y, mouth - JACK_L), cq.Vector(0, 0, 1)))
    coil = spring_coil(x, y, mated)
    return ([("leg_trrs_plug_%d" % k, plug), ("leg_trrs_jack_%d" % k, jack),
            ("leg_trrs_spring_%d" % k, coil),
            ("leg_trrs_throat_%d" % k, throat(sx, ly)),
            ("leg_trrs_sleeve_%d" % k, sleeve(sx, ly)),
            ]
            + cables(sx, ly, k))
