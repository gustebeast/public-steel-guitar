# -*- coding: utf-8 -*-
"""THE LEG <-> PEDAL BAR BLIND-MATE, on the joint's own spine -- the LEG HALF.

The top joint (src.leg_trrs) put the long half -- a O9.7 x 40 inline jack floating on a
coil -- inside the fixed tenon, because the tenon is 252 long and the body adapter had
12.8. Down here the same reasoning points the OTHER WAY, and the numbers are not close:

    bar, mortise floor to the bar's underside      31.1
    ...once the TPU foot's mortise is allowed for  25.1
    what the top joint's chain needs below its interface   60.0

So the bar cannot hold the long half. The tenon can: its lowest ladder hole is 64 above
its bottom end, and the bar latch's retention pocket clears this spine out to r 5.2 over
the whole engagement (both measured, not assumed). THE LEG TAKES THE LONG HALF AGAIN --
but this time it is the MALE plug that lives in the leg, floating, and the bar keeps a
short PCB-mount jack (user's call).

WHY THE MALE END IS THE ONE THAT FLOATS. The leg's lead is ONE bought M-F cable: its
female is the floating jack at the TOP joint, already built, so its bottom end is male
and that is not negotiable without redoing a finished joint. That settles the bar as
female -- and an inline female is O9.7 x 40, the very thing that does not fit -- so the
bar's female is a short PCB jack instead. Soldering stays on a board, which the project's
wiring rule allows.

AND THE COIL STILL THREADS ON. It has to end up ON the lead, above the plug, and a lead
has two ends: the O9.7 jack at the top and this O6.1 plug at the bottom. leg_trrs.SPR_ID
is 6.6 -- chosen to pass that same O6.1 -- so the SAME SPRING SKU threads on over the
plug and slides up. Nothing new to buy, and nothing that makes the joint unbuildable the
way a 3.8 ID coil once did.

NOTHING STANDS PROUD OF THE LEG. At rest the plug is at its lowest, and its barrel is
drawn to finish FLUSH with the tenon's bottom face -- so a detached leg has no pin
hanging off its foot to be knocked. The exposure moves to the BAR, where the jack's nose
stands up off the mortise floor into a pocket 40 deep, which is the same bargain the top
joint made with the adapter's plug.

WHAT THE BAR MUST PRESENT, and it is the only thing this module asks of it:
  * the socket face at JACK_MOUTH (world z), square to the axis and on the spine;
  * a nose that fits NOSE_WAY_D and is no taller than NOSE_H above the mortise floor;
  * a face flat out to at least PLUG_D, so the plug's shoulder -- not the sleeve's rim --
    is what sets the insertion depth.
Until the jack is sourced those are requirements, not measurements. The bar half waits on
its datasheet; this half does not depend on which jack it is.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import leg_stack as LS
from . import leg_trrs as LT

B = D.BEAD

# ── the interface, and the parts either side of it ───────────────────────────
TIP = LS.Z_ADJ_TEN_BOT          # -770.55: the tenon's bottom face IS the mortise floor
FLOAT = LT.FLOAT                # 3.0, and it means the same thing as at the top joint:
                                # how short the latch may stop and still make contact

SH_REST = TIP + LT.BARREL_L     # the plug's shoulder with the leg OFF. Putting it a
                                # whole BARREL_L up is what keeps the barrel's tip flush
                                # with the tenon's bottom face rather than hanging out
SH_MATE = SH_REST + FLOAT       # ...and seated, the plug having given up its float
JACK_MOUTH = SH_MATE            # THE BAR'S REQUIREMENT: its socket face, here
NOSE_H = JACK_MOUTH - TIP       # 17.0 of jack nose above the mortise floor
NOSE_WAY_D = LT.JACK_BORE_D     # 9.9 -- the nose rides the very bore the collar, the
                                # coil and the plug all travel, so the bar gets no new
                                # diameter to respect. It also gives the mate a second
                                # lead-in on top of the octagon's own fit

# ── the sleeve: a TPU collar that carries the plug, not a cup that caps it ───
SLV_GRIP = LT.PLUG_GRIP         # 4.8 of squeeze on the overmould, as at the top
SLV_ID = LT.SLV_ID              # 5.7 -- the same interference on the same bought plug
SLV_OD = LT.SLV_OD              # 9.6
SLV_SEAT_T = 2 * B              # 1.6: the collar's upper flange, which the coil sits on
SLV_SEAT_ID = LT.PLUG_D + 0.2   # 6.3 -- and it CLEARS the overmould rather than capping
                                # it. That is what lets the collar go on at all: it is
                                # threaded from the BARREL end, O3.5 first, and has to
                                # pass the O6.1 overmould to reach its grip. A capping
                                # flange like the top sleeve's O4.8 could never get past
                                # it, and the lead's other end is a O9.7 jack, so there
                                # is no second way on. Open both ends, no slit needed
SLV_H = SLV_GRIP + SLV_SEAT_T   # 6.4

# ── the bayonet: leg_trrs's, with a taller run so the plug can FLOAT in it ───
LUG_BOT = SH_REST + 0.4         # the lugs at rest, just above the collar's bottom rim
RUN_H = LT.LUG_H + FLOAT        # 5.6: lug plus travel. The run's FLOOR is the down-stop
                                # (what holds the plug in with the leg off) and its ROOF
                                # is the up-stop at full compression. At the top joint
                                # the run was the lug's own height and the joint did not
                                # float; here the run IS the float
LUG_A = LT.KEEP_A               # (6, 186) -- THE TOP JOINT'S OWN BAYONET, 30 degree
                                # lugs and a 46 degree turn, which is only possible
                                # because of where this spine sits. See AX_Y: at the top
                                # joint's +5.6 the tenon's thin arc (110-160) and the bar
                                # latch's pocket (65-130) between them left room for a
                                # single lug at 24/30, and the bore itself was 0.76 off
                                # the pocket. At +3.2 there is no thin arc at all and the
                                # pocket is 8.1 away, so nothing here needs its own
                                # numbers -- searched (offset, deg, turn, clocking) as a
                                # grid rather than tuned one knob at a time
LUG_CHAMFER = 1.0               # the lug's TOP is chamfered by 1.0, not by its whole
                                # 1.8 of radial height. Its underside is the bearing face
                                # -- that is what the leg-off stop bears on -- and the top
                                # only has to LIMIT over-insertion. Chamfered all the way,
                                # as the top joint's sleeve is, the top tapers to a knife
                                # at r 4.79, inside the O9.9 bore, and catches nothing:
                                # the verification measured 0.000 mm3 of stop. At 1.0 the
                                # top keeps a 0.8 flat outside the bore, which is one bead
                                # of eave to print and a real stop to hit
assert RUN_H >= LT.LUG_H + FLOAT - 1e-9

# ── the coil, above the collar, around the overmould and then the lead ───────
SPR_BOT = SH_REST + SLV_H       # it lands on the collar's flange...
SPR_TOP = SPR_BOT + LT.SPR_REST_L
SEAT_Z = SPR_TOP                # ...and reacts against the bore's own step, exactly as
                                # at the top joint: a step that stops a O8.0 coil still
                                # passes the O6.1 plug, so no printed washer is needed
BORE_D = LT.JACK_BORE_D         # 9.9: the coil's bore. Wider than the collar needs, and
                                # that is deliberate -- it is the one bore the coil, the
                                # collar and the plug all travel, so there is only one
PASS_D = LT.PASS_D              # 6.6 above the seat: the lead's far plug has to be able
                                # to travel this bore, the same rule that made the number
                                # at the top joint
PASS_TOP = LS.Z_ADJ_TEN_TOP - (LS.LADDER_OFF + LS.ADJ_N * LS.ADJ_PITCH) - D.MIN_WALL_2P
                                # ...AND IT STOPS SHORT OF THE LADDER, 1.6 under the
                                # lowest hole. Running it the tenon's whole length is
                                # what the top joint's note assumed, and it does not
                                # survive contact: the ladder sits on the tenon's centre
                                # line and this spine is only 5.6 off it, so a O6.6 bore
                                # leaves a 0.30 web against every one of the 31 holes
                                # (tools/check_thin, and the reason this line exists).
                                # Where the lead goes ABOVE here is the parked routing
                                # problem -- docs/leg-trrs-routing.md -- and it wants
                                # either the ladder moved off centre or a path outside
                                # the tenon. Not a decision this joint gets to make

assert SPR_TOP - TIP < 64.0, (
    "the chain reaches %.1f above the tenon's bottom and the lowest ladder hole is at "
    "64.0" % (SPR_TOP - TIP))
assert LT.SPR_ID >= LT.PLUG_D + 0.4, (
    "the coil cannot be threaded onto the lead over its O%.1f plug" % LT.PLUG_D)


AX_X = LT.AX_X                  # the bottom joint keeps the top's X...
AX_Y = 4 * B                    # ...and sits at +3.2 in Y where the top sits at +5.6.
                                # 2.4 is the whole difference and it buys three things at
                                # once. The top spine is +5.6 because the LEG latch owns
                                # the fixed tenon's -Y middle; down here it is the BAR
                                # latch, whose retention pocket owns +Y, and at +5.6 that
                                # pocket left the O9.9 bore a 0.76 wall (check_thin). The
                                # obvious fix, mirroring to -5.6, is worse: it swings the
                                # octagon's thin arc onto 190-260, straddling the -X-Y
                                # build direction, which is exactly where a printable slot
                                # end wall has to sit -- no clocking exists at all. At
                                # +3.2 the pocket is 8.1 clear, the octagon holds a lug
                                # slot in EVERY direction, and the top joint's own 30/46
                                # bayonet fits. The lead jogs 2.4 in Y somewhere up the
                                # leg, which is a cable's job


def _ax():
    return LS.LEG_X + AX_X, LS.LEG_Y + AX_Y


def tenon_negatives(up=None):
    """Cut in the ADJUST TENON: one straight bore from the bottom face up past the
    collar and the coil to their seat, the bayonet's slots, and the pass-through above.

    Nothing narrows on the way IN. Everything that has to get past -- the lead's far
    plug, the coil, the collar -- goes in from the bottom face, in that order."""
    x, y = _ax()
    up = up or LS.PRINT_UP["adjust_tenon"]
    out = LT._bore(BORE_D, TIP - 1.0, SEAT_Z, x, y, up)
    out = out.union(LT._bore(PASS_D, SEAT_Z - 0.01, PASS_TOP, x, y, up))
    out = out.union(LT._bayonet_slots(BORE_D / 2.0 - 0.01, LT.LUG_D / 2.0,
                                      LUG_BOT, LUG_BOT + RUN_H, True, x, y, LUG_A, up))
    # AND THE ENTRY SLOTS RUN THE WHOLE WAY DOWN TO THE FACE. leg_trrs._bayonet_slots
    # opens its entry one LUG_LEDGE below the run, which is right at the top joint --
    # there the run sits exactly that far from the part's open end. Here the run is
    # LUG_BOT - TIP = 14.4 up, because the plug's barrel has to fit under it, so that
    # entry stopped 11.8 above the tenon's face and the lugs could not get in at all
    # (scratchpad/verify_bar_trrs.py caught it).
    for a0 in LUG_A:
        out = out.union(LT._td_sector(
            BORE_D / 2.0 - 0.01, LT.LUG_D / 2.0, TIP - 1.0, LUG_BOT + 0.01,
            a0 - LT.LUG_CLR_DEG, LT.LUG_DEG + 2 * LT.LUG_CLR_DEG, x, y, up))
    return out


def sleeve():
    """THE PLUG'S CARRIER: a TPU collar, gripping the overmould and riding the bayonet.

    It is not the top joint's cup. There the sleeve CAPPED the plug and the counterbore's
    roof was the up-stop; here the plug has to FLOAT, so the collar carries it and the
    run's roof and floor are the two stops. The load path at mate is jack -> plug's
    shoulder -> (grip) -> collar -> coil, and the grip carries it: ~17-55 N of squeeze
    against the coil's ~10."""
    x, y = _ax()
    body = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        SLV_OD / 2.0, SLV_H, cq.Vector(x, y, SH_REST), cq.Vector(0, 0, 1)))
    body = body.union(LT._lugs(SLV_OD / 2.0 - 0.01, LT.LUG_D / 2.0 - LT.SLV_CLR / 2.0,
                               LUG_BOT, LUG_BOT + LT.LUG_H, x, y, LUG_A, False,
                               LUG_CHAMFER))
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        SLV_ID / 2.0, SLV_GRIP + 1.0, cq.Vector(x, y, SH_REST - 1.0), cq.Vector(0, 0, 1))))
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        SLV_SEAT_ID / 2.0, SLV_H + 2.0, cq.Vector(x, y, SH_REST + SLV_GRIP),
        cq.Vector(0, 0, 1))))
    assert len(body.val().Solids()) == 1, (
        "the collar came out as %d solids" % len(body.val().Solids()))
    return body


def dummies(k: int = 0, mated: bool = True):
    """The bought parts where they sit. `mated` is the latched state: the plug pushed
    FLOAT back up its run, its coil that much shorter."""
    x, y = _ax()
    rise = FLOAT if mated else 0.0
    sh = SH_REST + rise
    plug = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        LT.PLUG_D / 2.0, LT.PLUG_L, cq.Vector(x, y, sh), cq.Vector(0, 0, 1)))
    plug = plug.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        LT.BARREL_D / 2.0, LT.BARREL_L, cq.Vector(x, y, sh - LT.BARREL_L),
        cq.Vector(0, 0, 1))))
    coil_l = LT.SPR_REST_L - rise
    coil = LT.spring_coil(x, y, mated=False)
    coil = coil.translate((0, 0, (SPR_BOT + rise) - LT.SPR_SEAT))
    return [("bar_trrs_plug_%d" % k, plug),
            ("bar_trrs_sleeve_%d" % k, sleeve().translate((0, 0, rise))),
            ("bar_trrs_spring_%d" % k, coil)]
