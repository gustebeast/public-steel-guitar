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
  * a face flat out to at least PLUG_D, so the plug's shoulder -- not the collar's rim --
    is what sets the insertion depth.

AND IT IS AN INLINE JACK, NOT A BOARD (user, once the part was measured rather than
envelope'd). The BOM's O9.7 x 40 was never a part: Tensility's own drawing for 10-02135
gives the jack as 3.5 x 7.8 x L25.8. Since NOSE_H of it is up inside this tenon, only 8.8
sits below the mortise floor, against 25.1 of bar -- so the PCB-mount jack and the 36.5
of tower raise that the envelope forced are both off the table, and with them a board, a
solder operation and 6.5 ladder holes of low-end height adjustment. The bar's female is
the CUT HALF of the same jack-to-plug cable whose other half is this joint's male pigtail
at the top of the instrument. See BOM.md.
"""

from __future__ import annotations

import math

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
BORE_D = SLV_OD + 0.3           # 9.9: ONE bore, and THE COLLAR is what sets it. It
                                # inherited leg_trrs.JACK_BORE_D until that followed the
                                # jack's real drawing down to 8.4 and left the O9.6 collar
                                # unable to enter (verify_bar_trrs caught it). Nothing
                                # about this bore was ever the jack's business: what
                                # travels it is the collar, the O6.1 plug, the O8.0 coil
                                # and -- only for its last NOSE_H -- the jack's O7.8 nose
NOSE_WAY_D = BORE_D             # 9.9 -- the nose rides the very bore the collar, the
                                # coil and the plug all travel, so the bar gets no new
                                # diameter to respect. It also gives the mate a second
                                # lead-in on top of the octagon's own fit
SPR_CH_D = LT.SPR_OD + 0.6      # 8.6 -- THE COIL GETS ITS OWN CHANNEL. BORE_D is 9.9
                                # because the TPU COLLAR travels it, which leaves an
                                # O8.0 coil 0.95 of radial slop: enough to lean over
                                # and buckle sideways instead of compressing (user saw
                                # it). But the collar only ever reaches SPR_BOT+FLOAT,
                                # and above that the bore carries nothing but the coil
                                # and the O6.1 lead. So it steps down there: 0.3 on the
                                # coil, which centres it without gripping it
SPR_CH_BOT = SPR_BOT + FLOAT + 0.4
                                # ...and the 0.4 is the collar's clearance to the step
                                # at FULL compression. The step is a diameter change,
                                # not a stop -- the coil still reacts against SEAT_Z --
                                # so the collar must never reach it
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

assert SPR_CH_BOT > SH_REST + SLV_H + FLOAT, (
    "the coil's channel starts at %.2f and the collar's flange reaches %.2f at mate"
    % (SPR_CH_BOT, SH_REST + SLV_H + FLOAT))
assert SPR_CH_D > LT.SPR_OD and SPR_CH_D < BORE_D, (
    "the coil channel O%.1f has to pass the O%.1f coil and be tighter than the O%.1f "
    "bore it steps out of" % (SPR_CH_D, LT.SPR_OD, BORE_D))
assert TIP + NOSE_H < SPR_CH_BOT, (
    "the jack's nose reaches %.2f and the bore narrows at %.2f"
    % (TIP + NOSE_H, SPR_CH_BOT))
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
    out = LT._bore(BORE_D, TIP - 1.0, SPR_CH_BOT, x, y, up)
    out = out.union(LT._bore(SPR_CH_D, SPR_CH_BOT - 0.01, SEAT_Z, x, y, up))
    out = out.union(LT._bore(PASS_D, SEAT_Z - 0.01, PASS_TOP, x, y, up))
    out = out.union(LT._bayonet_slots(BORE_D / 2.0 - 0.01, LT.LUG_D / 2.0,
                                      LUG_BOT, LUG_BOT + RUN_H, True, x, y, LUG_A, up))
    # AND THE ENTRY SLOTS RUN THE WHOLE WAY DOWN TO THE FACE. leg_trrs._bayonet_slots
    # opens its entry one LUG_LEDGE below the run, which is right at the top joint --
    # there the run sits exactly that far from the part's open end. Here the run is
    # LUG_BOT - TIP = 14.4 up, because the plug's barrel has to fit under it, so that
    # entry stopped 11.8 above the tenon's face and the lugs could not get in at all
    # (scratchpad/verify_bar_trrs.py caught it).
    # ...AND THEY SWEEP PAST THE BUILD AZIMUTH, for the same reason the bar half's do.
    # At the lug's own width this entry ran 182..220 while the O9.9 bore's apex sits at
    # 225 -- the tenon builds -X-Y -- so it took the apex flat's low flank and left
    # 11.52 mm2 of it cantilevered from the tenon's face up to the run. I fixed the
    # bar and never looked at the other part the same joint cuts; the user found this
    # one in the tab. scratchpad/probe_apex.py now walks BOTH parts, each with its own
    # build direction, which is what it should have done first.
    for a0 in LUG_A:
        out = out.union(LT._td_sector(
            BORE_D / 2.0 - 0.01, LT.LUG_D / 2.0, TIP - 1.0, LUG_BOT + 0.01,
            a0 - LT.LUG_CLR_DEG,
            _entry_sweep(up, a0, LT.LUG_D / 2.0), x, y, up))
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
    # AT THE LENGTH IT IS AT. Seated, the plug has given up its float and the coil has
    # taken all of it, so the coil is FLOAT shorter -- not the same coil moved up.
    coil_l = LT.SPR_REST_L - rise
    coil = LT.spring_coil(x, y, length=coil_l)
    coil = coil.translate((0, 0, (SPR_BOT + rise) - LT.SPR_SEAT))
    assert coil.val().BoundingBox().zmax <= SEAT_Z + 1e-6, (
        "the coil is drawn %.2f past SEAT_Z, which is where the bore steps down to "
        "O%.1f -- an O%.1f coil cannot be there"
        % (coil.val().BoundingBox().zmax - SEAT_Z, PASS_D, LT.SPR_OD))
    return [("bar_trrs_plug_%d" % k, plug),
            ("bar_trrs_sleeve_%d" % k, sleeve().translate((0, 0, rise))),
            ("bar_trrs_spring_%d" % k, coil)]


# ════════════════════════════════════════════════════════════════════════════
# THE BAR HALF. Everything above is the LEG's, authored in world Z; a pedal bar
# piece is authored in the BAR's own frame, so every number below is a DEPTH
# BELOW THE MORTISE FLOOR and the caller says where that floor is. The two
# frames never meet in this file, which is the point.
# ════════════════════════════════════════════════════════════════════════════

BAR_UP = (0.0, 1.0, 0.0)        # pedal_bar_a lies on its -Y face and builds +Y, so a
                                # bore down THIS joint's spine is a HORIZONTAL bore in
                                # the print. Every cut below is teardropped against it

JB_DEEP = LT.JACK_L - NOSE_H    # 8.8 -- all of the jack that is not nose. The whole bar
                                # half is this number: 8.8 against the 25.1 the bar has,
                                # where the envelope wanted 60 (see the module docstring)
JB_D = LT.JACK_D + 0.3          # 8.1 -- a running fit on the O7.8 body, not a press. The
                                # jack is HELD by the throat's grip; this bore only keeps
                                # it straight and gives its back a seat
CABLE_WAY_D = LT.CABLE_D + 0.8  # 4.6 for the O3.8 lead -- and the STEP from JB_D down to
                                # it is the jack's DOWN-stop, the one stop this joint
                                # gets for free. It carries the mate force (MATE_N, ~7 N)
                                # on a r2.3..r4.05 annulus: 0.2 MPa, which is nothing

# ── the throat: the same TPU grip + bayonet the top joint uses, one size up ──
TH_DEEP = 8 * B                 # 6.4 of the 8.8 is the throat's pocket, leaving 2.4 of
                                # hard bore under it for the jack's seat
TH_ID = LT.JACK_D - LT.SLV_SQUEEZE          # 7.4: 0.4 of squeeze on the O7.8 body, the
                                # same interference the top joint's sleeve takes on the
                                # plug. Over TH_DEEP that is 157 mm2 of grip
TH_OD = TH_ID + 2 * D.MIN_WALL_2P           # 10.6
TH_POCK_D = TH_OD + LT.SLV_CLR              # 11.0
TH_LUG_D = TH_OD + 2 * LT.LUG_PROUD         # 14.2
TH_A = LT.SLV_A                 # (52, 232) -- AND THE NUMBER IS NOT BORROWED, it is
                                # re-derived. A bayonet slot's end wall is a plane
                                # through the bore's axis, so against a build azimuth U
                                # it overhangs by |sin(U - theta)| and the 45 rule is
                                # |U - theta| <= 45. Here U is +Y, 90 degrees, and the
                                # RUN is the wide feature: LUG_DEG + LUG_TURN + 2 CLR =
                                # 84 degrees of it, from a0 - 4 to a0 + 80. Both ends
                                # inside 45..135 forces a0 into [49, 55] and nothing
                                # else -- a 6 degree window, which 52 sits in the middle
                                # of. That the top joint's sleeve landed on the same
                                # number is arithmetic, not inheritance: its adapter
                                # builds +Y too
TH_RUN_H = LT.LUG_SLOT_H        # 2.4 against a 2.6 lug: the TPU squashes 0.2 and stands
                                # preloaded in its own slot, exactly as at the top joint
TH_DETENT = 0.4                 # ...AND THEN A POSITIVE DETENT, which the top joint did
                                # not need. There the anti-rotation lock is the user's
                                # pre-twisted leads; here the lead leaves the throat and
                                # turns into the trough, which resists a back-turn but
                                # does not forbid one. So the run's OUTER wall carries a
                                # bump TH_DETENT proud, TH_DETENT_DEG before the stop:
                                # the lug squashes past it going in and has to squash
                                # back to come out. TPU is the only reason this is a
                                # feature and not a crack
TH_DETENT_DEG = 8.0             # ...AND IT IS MEASURED FROM THE LUG'S TRAILING EDGE,
                                # so it has to clear the pin's own half-angle or the
                                # detent lands under the lug's RESTING position and the
                                # throat can never seat (1.50 mm3 of it, which is how
                                # this number was found). The assert below is the real
                                # constraint; 8.0 keeps 1.9 degrees of daylight
TH_DETENT_R = B                 # the bump is a round PIN, not an annular step, and the
                                # radius is not cosmetic. As a sector it shared its
                                # inner face with the pocket bore, and the two cuts that
                                # took 0.1 s of geometry took over four minutes of
                                # coincident-surface boolean -- the whole reason
                                # pedal_bar_a stopped building. Standing it off the bore
                                # entirely costs nothing and gives the lug a radius to
                                # ride rather than a corner to catch on

assert TH_DEEP + D.MIN_WALL_2P <= JB_DEEP, (
    "the throat's pocket (%.1f) leaves only %.1f of seat bore under it" %
    (TH_DEEP, JB_DEEP - TH_DEEP))
_PIN_R = TH_LUG_D / 2.0 + TH_DETENT_R - TH_DETENT
_PIN_DEG = math.degrees(math.asin(TH_DETENT_R / _PIN_R))
assert TH_DETENT_DEG > _PIN_DEG, (
    "a %.1f pin at r %.1f spans %.1f degrees and the detent is only %.1f before the "
    "stop: it would sit under the seated lug" %
    (TH_DETENT_R, _PIN_R, 2 * _PIN_DEG, TH_DETENT_DEG))
assert 45.0 <= TH_A[0] - LT.LUG_CLR_DEG and \
    TH_A[0] + LT.LUG_DEG + LT.LUG_TURN + LT.LUG_CLR_DEG <= 135.0, (
    "the run spans %.0f..%.0f and the 45 rule wants 45..135 for a +Y build" %
    (TH_A[0] - LT.LUG_CLR_DEG,
     TH_A[0] + LT.LUG_DEG + LT.LUG_TURN + LT.LUG_CLR_DEG))


def _entry_sweep(up, a0, r_out, turn=None, margin=2.0):
    """How far a bayonet ENTRY has to sweep so it carries the teardrop apex with it.

    A teardrop apex is a one-nozzle flat bridging between the two 45 flanks that
    converge to it. An entry slot cut at the LUG radius reaches out past the apex of
    every narrower bore it crosses, so if the entry STOPS SHORT of the build azimuth
    it takes one flank and leaves the flat cantilevered over open air. Sweeping past
    the azimuth instead makes the entry's own apex the only apex there -- _td_sector's
    "the two apexes are now the same apex" -- and that one has flanks inside the
    sector.

    The pad is the flat's own half-angle plus `margin`, not a guess: the flat sits at
    r_out*sqrt(2) - nozzle/2 and is one nozzle wide, so it subtends
    asin((nozzle/2)/r_flat) either side of the azimuth.

    Returns the sweep from `a0 - LUG_CLR_DEG`. Asserts it has not eaten the ledge the
    lug comes to rest on, which is the one thing spending angle here can cost.
    """
    turn = LT.LUG_TURN if turn is None else turn
    start = a0 - LT.LUG_CLR_DEG
    # THE APEX AHEAD OF *THIS* ENTRY. A teardrop about an axis has an apex every 180
    # degrees, so fold the build azimuth into [0, 180) FIRST and then walk it up past
    # this entry's start. Walking the raw azimuth instead keeps whichever of the two
    # it happened to be written as: for the tenon's up (-X-Y, 225) the lug at a0=186
    # got 225, correctly, and the lug at a0=6 got 225 as well -- 180 too far round,
    # against a lug that comes to rest at 52.
    az = (math.degrees(math.atan2(up[1], up[0])) % 180.0)
    while az < start:
        az += 180.0
    r_flat = r_out * math.sqrt(2.0) - D.NOZZLE_D / 2.0
    half = math.degrees(math.asin((D.NOZZLE_D / 2.0) / r_flat))
    top = az + half + margin
    sweep = top - start
    assert sweep >= LT.LUG_DEG + 2 * LT.LUG_CLR_DEG, (
        "the entry sweeps %.1f and the lug needs %.1f to pass"
        % (sweep, LT.LUG_DEG + 2 * LT.LUG_CLR_DEG))
    assert top <= a0 + turn - margin, (
        "carrying the apex needs the entry out to %.1f, and the lug comes to rest at "
        "%.1f: it would eat the ledge the lug bears on" % (top, a0 + turn))
    return sweep


def _th_run(floor_z):
    """The bayonet run's z band, from the caller's mortise floor."""
    lo = floor_z - TH_DEEP
    return lo, lo + TH_RUN_H


def bar_negatives(floor_z, chamber_top_z, x=None, y=None, up=BAR_UP):
    """Cut in the BAR's mortise tower, in the BAR's frame.

    `floor_z` is the mortise floor -- the plane the leg's tenon lands on, and the plane
    the jack's nose stands up off. `chamber_top_z` is the wiring chamber's ceiling: the
    cable way stops there rather than this module guessing where the bar's trough is.

    Nothing here narrows on the way DOWN except at the very bottom, where it is meant
    to: jack and throat both go in from the mortise, which is open until the leg does."""
    if x is None:
        x, y = _ax()
    lo, hi = _th_run(floor_z)
    out = LT._bore(JB_D, floor_z - JB_DEEP, floor_z + 0.01, x, y, up)
    out = out.union(LT._bore(TH_POCK_D, floor_z - TH_DEEP, floor_z + 0.01, x, y, up))
    out = out.union(LT._bayonet_slots(TH_POCK_D / 2.0 - 0.01, TH_LUG_D / 2.0,
                                      lo, hi, False, x, y, TH_A, up))
    # AND THE ENTRY SLOTS REACH THE MORTISE FLOOR. leg_trrs._bayonet_slots opens its
    # entry one LUG_LEDGE past the run, which is exactly right where the run sits that
    # far from the part's open end. It does not here: the run is at the BOTTOM of a
    # TH_DEEP pocket, so the stock entry stopped 1.4 short of the floor and the lugs
    # could not get in. The leg half needed the same line for the same reason -- see
    # tenon_negatives, where the shortfall was 11.8 rather than 1.4.
    for a0 in TH_A:
        out = out.union(LT._td_sector(
            TH_POCK_D / 2.0 - 0.01, TH_LUG_D / 2.0, lo, floor_z + 0.01,
            a0 - LT.LUG_CLR_DEG,
            _entry_sweep(up, a0, TH_LUG_D / 2.0), x, y, up))
    # the detent, subtracted BACK OUT of the run: a pin standing TH_DETENT proud of the
    # slot's outer wall, TH_DETENT_DEG before the stop, that the lug squashes past
    r_pin = _PIN_R
    for a0 in TH_A:
        a = math.radians(a0 + LT.LUG_TURN - TH_DETENT_DEG)
        out = out.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            TH_DETENT_R, hi - lo + 1.0,
            cq.Vector(x + r_pin * math.cos(a), y + r_pin * math.sin(a), lo - 0.5),
            cq.Vector(0, 0, 1))))
    # ...and the lead's way out of the jack's back, down into the wiring chamber
    out = out.union(LT._bore(CABLE_WAY_D, chamber_top_z - 0.01,
                             floor_z - JB_DEEP + 0.01, x, y, up))
    return out


def throat(floor_z=TIP, x=None, y=None):
    """THE JACK'S KEEPER: TPU, gripping the jack's body, turned into the tower's bayonet.

    It is the top joint's argument run downwards. The jack is a flangeless O7.8 moulding
    -- there is no shoulder on it to catch -- so the only positive up-stop available is
    to grip it and capture the GRIP. The plug's detent lets go at 5..20 N on every leg
    removal; the grip answers with 157 mm2 of 0.4-squeeze TPU and the lugs put that into
    a ledge, so nothing about the retention is an unsized press fit.

    IT IS BENCH-ASSEMBLED. Slide it down the jack's nose onto the body, thread the lead
    down the bar's cable way into the trough, THEN drop the pair into the mortise and
    turn. The jack is the handle: the grip that holds it is what lets it turn the
    throat, so the 40-deep mortise needs no tool reaching down it."""
    if x is None:
        x, y = _ax()
    lo, _ = _th_run(floor_z)
    body = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        TH_OD / 2.0, TH_DEEP, cq.Vector(x, y, floor_z - TH_DEEP), cq.Vector(0, 0, 1)))
    body = body.union(LT._lugs(TH_OD / 2.0 - 0.01, TH_LUG_D / 2.0 - LT.SLV_CLR / 2.0,
                               lo, lo + LT.LUG_H, x, y, TH_A, True))
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        TH_ID / 2.0, TH_DEEP + 2.0, cq.Vector(x, y, floor_z - TH_DEEP - 1.0),
        cq.Vector(0, 0, 1))))
    assert len(body.val().Solids()) == 1, (
        "the throat came out as %d solids" % len(body.val().Solids()))
    return body


def bar_cable(floor_z, x=None, y=None, k: int = 0):
    """THE START OF THE LEAD'S JOURNEY: out of the jack's back and into the trough.

    Only the start. Where it goes once it is IN the channel is the bar's wiring problem
    and not this joint's, so the run stops a little past the trough's mouth rather than
    pretending to know the rest -- exactly as leg_trrs.cables stops short of the chassis
    end that is still parked.

    What it is here to show is the TURN, which is the one thing about this route that
    was a decision: the lead leaves the jack travelling -Z, and the trough is 20.4 +X
    and 3.2 +Y of the spine. It could not turn that corner inside a tunnel of any
    sensible diameter, so it turns in the open chamber instead -- CHAM_Z1 - CHAM_Z0 of
    room, 3.3x the cable's own O3.8, plus the whole depth of the chamber in Y to bow
    into. Drawn as cylinders with balls at the corners (leg_trrs._run), so the corners
    are SHARPER than the real cable's: read the chamber for the radius, not the
    polyline.

    `floor_z` is the mortise floor in whatever frame the caller is drawing, which is
    the same contract the rest of the bar half keeps. Everything else is read off
    pedal_bar and shifted by the difference, so the two cannot drift apart."""
    from . import pedal_bar as PB                    # late: PB imports this module
    if x is None:
        x, y = _ax()
    dz = floor_z - (PB.TOWER_TOP - LS.ENGAGE)        # bar frame -> the caller's
    z_cham = PB.CHAM_Z1 + dz
    z_run = (PB.CHAM_Z0 + PB.CHAM_Z1) / 2.0 - 1.2 + dz       # the lead lies low in it
    y_mid = (PB.LID_Y0 - PB.TROUGH_D + PB.LID_Y0) / 2.0      # the trough's own centre
    lead = LT._run([
        (x, y, floor_z - JB_DEEP),                   # the jack's back
        (x, y, z_cham - 1.5),                        # straight down the cable way...
        (x, y + 3.6, z_cham - 6.0),                  # ...and into the chamber, turning
        (x + 7.0, y_mid - 1.8, z_run),               # the corner, mid-chamber
        (x + 17.0, y_mid, z_run),                    # settled on the trough's centre
        (PB.TROUGH_X0 + 16.0, y_mid, z_run),         # ...and away down the channel
    ])
    return [("bar_trrs_lead_%d" % k, lead)]


def bar_dummies(floor_z, x=None, y=None, k: int = 0):
    """The bought jack where it sits in the bar, and the throat holding it."""
    if x is None:
        x, y = _ax()
    jack = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        LT.JACK_D / 2.0, LT.JACK_L, cq.Vector(x, y, floor_z - JB_DEEP),
        cq.Vector(0, 0, 1)))
    return ([("bar_trrs_jack_%d" % k, jack),
             ("bar_trrs_throat_%d" % k, throat(floor_z, x, y))]
            + bar_cable(floor_z, x, y, k))
