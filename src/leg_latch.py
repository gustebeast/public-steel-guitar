"""LEG -> BODY latch: press-to-release, and the mechanism lives IN THE TENON.

THE JOINT. The fixed tenon runs up out of the fixed sleeve and into the body
adapter's blind mortise; the sleeve's 44.8 face BUTTS the adapter's. The tenon is
what holds the leg on the body (user) -- the butt carries the kick as compression,
the tenon carries the tension -- and this latch is what stops it sliding back out.

WHY NOT src.latch, WHICH ALREADY EXISTS. Its mechanism is 24.80 deep radially,
MEASURED (FACE_Y - BACK_Y): slider 20.8, the spring reacting 2.4 behind it, a 3.2
cover. It fits at the old joints because the male there is a SOLID 44.8 section
and the mechanism buries itself in it. Nothing here is solid:

    sleeve wall over the mortise   5.81      <- the obvious place. Not close.
    adapter wall over the mortise  5.81      <- and it is the wrong part anyway
    THE TENON, axis to its roof    16.17     <- the only solid section in the joint

So the mechanism goes in the tenon, which is exactly where the load is not, and
the joint's two hollow parts each give it something instead of housing it:

    THE ADAPTER gives the RETENTION POCKET. Its wall over the mortise is 5.81 and
      the hook needs only a 2.40 bite out of it, leaving 2.91 of skin.
    THE SLEEVE gives the NOTCH the button shows through, and doubles as the COVER
      -- the sleeve wall is what stands over the slider. That deletes latch.py's
      separate cover part outright.

BUTTON ON THE LEG (user: you pull it off with one hand). The pad sits flush in the
sleeve's outer face, below the butt plane, on the piece you are holding. The
adapter gets no hole and no button -- the same rule src.latch keeps.

ASSEMBLY -- and an earlier version of this paragraph was WRONG. It said to build
the leg first and drop the slider in through the notch afterwards. That cannot
work: the slider's body is 12.8 wide, the notch's neck slot is 8.5, and the
tenon's pocket is closed at both ends. The order that does work (user's sequence, and swept -- see the fit tests):

  1. LATCH INTO THE TENON while it is separate: spring into the divot, slider
     down over it into the pocket.
  2. SLIDE THE TENON DOWN (+Z to -Z in the world) into the fixed sleeve from its
     BUTT end, pad held flush. Everything but the neck and pad lies inside the
     bore's own profile, so it passes straight through; the neck and pad ride into
     the notch, which is open at that end, over the last 20 mm.
  3. SCREW THE TENON TO THE FIXED SLEEVE (leg_stack.FIX_SCREW_Z; its twin,
     ADJ_SCREW_Z, pins the adjust sleeve when that goes on). The slider's body
     shoulders now sit under the sleeve's bore, which holds it in against the
     spring -- the SLEEVE IS THE COVER -- and the screw stops the tenon backing out
     of the sleeve, so the latch cannot fall out.
  4. offer the leg up to the body: push to connect, no button.

WHY THE HOOK NEEDS NO LONG RUN-IN CHANNEL. It sits just inside the butt plane, so
it is outside the adapter for all but the last HOOK_Z + RUN (8.0) of a 40 mm
insertion: it meets the adapter's MOUTH EDGE, cams in on its 45 lead, rides the
bore retracted for RUN, and springs out into a pocket ENCLOSED on its +Z side. (An
earlier version put the pocket open to the mouth. That retains nothing -- there is
no +Z face for the hook to catch on.) The pocket's far face is a flat 90 ledge, so
pulling on the leg loads it in shear with no cam-out.

FRAME: leg-local -- the same one leg_stack assembles in. +Z runs AWAY from the
instrument, so the ADAPTER is at low z and the SLEEVE at high, and BUTT is the
plane between them. +Y is the button face.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import latch as LT
from . import leg_stack as LS
from .helpers import box_at

B = D.BEAD
CLR = 0.25                         # sliding clearance (a CLEARANCE: sub-bead by
                                   # necessity, like every gap in src.latch)


# -- the radii, all measured off leg_stack's own section ---------------------
def _top_flat(w: float, cham: float = LS.CHAM) -> float:
    """+Y extent of a 45-rotated chamfered square of `w` across flats. The apex is
    a CHAMFER, not a point, so this is w/sqrt2 minus half the chamfer -- not the
    virtual apex, which is 0.8 higher and would put every clearance here out by
    that much, in the unsafe direction."""
    return w / math.sqrt(2.0) - cham / 2.0


TEN_TOP = _top_flat(LS.TEN_W)                          # 16.171 the tenon's roof
BORE_TOP = _top_flat(LS.TEN_W + 2 * LS.FIT)            # 16.595 the mortise's
FACE_Y = LS.LEG_W / 2.0                                # 22.400 outer face
WALL = FACE_Y - BORE_TOP                               #  5.805 all there is

CH_FLOOR = BORE_TOP + 0.5          # pocket floor, stood off the bore so the hook
                                   # never rubs the tenon it rides beside
HOOK_TIP = CH_FLOOR + LT.HOOK_ENGAGE                   # 19.49 engaged
STROKE = LT.STROKE                 # 3.2 -- MUST exceed HOOK_ENGAGE, or pressing
                                   # the button cannot clear the bore
assert HOOK_TIP - STROKE < BORE_TOP, (
    "pressed, the hook still stands %.2f into the bore -- the leg cannot come off"
    % (HOOK_TIP - STROKE - BORE_TOP))
# BRIDGE SAG over the hook. The adapter prints button-face UP, so the retention
# pocket's outer skin is its ROOF: a 13.3 x 5.3 opening walled on all four sides,
# i.e. a 5.3 mm bridge -- routine, but a bridge droops, and the hook tip sat only
# CLR (0.25) under it. This is room for the droop, not material.
BRIDGE_SAG = 0.3
POCKET_TOP = HOOK_TIP + CLR + BRIDGE_SAG                # 20.04
assert FACE_Y - POCKET_TOP >= D.MIN_WALL_2P, (
    "only %.2f of adapter skin over the retention pocket" % (FACE_Y - POCKET_TOP))

# -- the band ---------------------------------------------------------------
BUTT = LS.ADAPT_L                  # 52.8 the butt plane, in leg-local z
BAND_W = 16 * B                    # 12.8 across X. Centred on x=0, where the
                                   # tenon is TALLEST: its roof falls away at 45
                                   # degrees either side, so an off-centre band
                                   # would have less material under it, not more.
HOOK_Z = 6 * B                     # 4.8 the hook's own length along the leg
RUN = 4 * B                        # 3.2 how far INSIDE the mouth the pocket sits.
                                   # It cannot sit AT the mouth: a pocket open to
                                   # the mouth has no +Z face, so the hook would
                                   # simply slide back out of it and the latch
                                   # would retain nothing. This is the run the hook
                                   # rides RETRACTED against the bore before it
                                   # springs out -- and RUN is what turns the
                                   # pocket's far side into a real 90 ledge.
HOOK_Z1 = BUTT - RUN               # 49.6 the retention face, looking back up +Z
HOOK_Z0 = HOOK_Z1 - HOOK_Z         # 44.8 the leading end, where the lead-in is
# THE PAD IS A THUMB TARGET, 20 x 20 (user: 8 x 12 was too small to press). It is
# a PLATE on a narrow NECK rather than a 20-wide slider, because the neck is what
# has to pass through the sleeve wall at the joint's highest-moment station, and
# only the plate has to be big. The plate sits in a RECESS in the sleeve face,
# flush at rest; the recess floor is the hard stop at full stroke.
PAD_W = 25 * B                     # 20.0 across X
PAD_L = 25 * B                     # 20.0 down the sleeve from the butt plane
PAD_T = 3 * B                      # 2.4 plate thickness: a thumb load at a corner
                                   # cantilevers it 6 past the neck, and 1.6 bent
                                   # at ~14 MPa there against ~6 at 2.4
NECK_W = LT.PAD_W                  # 8.0 what actually crosses the sleeve wall
SPR_Z = BUTT + PAD_L / 2.0         # the spring sits under the middle of the pad
                                   # so the notch keeps a lip either side

# The slider's back face at rest, and the spring behind it. Same coil SKU as
# src.latch -- one spring for the whole instrument (user) -- so these are its
# numbers, not new ones.
SPR_GAP = LT.SPR_GAP               # 4.0 back face -> tunnel back at rest
TUNNEL_BACK = 4 * B                # 3.2 how deep the pocket goes. NOT a free
                                   # choice in either direction: shallower and the
                                   # slider has no room for the spring's 6.4 seat
                                   # plus a wall behind it; deeper and it eats the
                                   # tenon. 3.2 is the shallowest that houses the
                                   # seat, and it is what sets SECTION_LOSS below.
SLIDER_BACK = TUNNEL_BACK + SPR_GAP                    # 7.2
# THE SPRING IS SEATED AT BOTH ENDS (user). It used to sit in a blind bore in the
# slider and just stand on the pocket's flat floor, so its far end could walk
# about under a side load. Now the tenon has a DIVOT for it too.
#
# The seat depth is SPLIT, not added to. Deepening the tenon end on top of the
# slider's existing 6.4 would lengthen the spring's installed length by the same
# amount and throw away its preload -- at a 1.6 divot the coil sits at exactly its
# 12.0 free length at rest, and the hook would be held out by nothing. So the
# total stays LT.SPR_SEAT and the preload is untouched.
DIVOT = 2 * B                      # 1.6 in the tenon's pocket floor
SLIDER_SEAT = LT.SPR_SEAT - DIVOT  # 4.8 in the slider
SPR_REST_L = SLIDER_BACK + SLIDER_SEAT - (TUNNEL_BACK - DIVOT)   # 10.4 installed
SPR_PRESS_L = SPR_REST_L - STROKE                                 # 7.2 pressed
assert SPR_REST_L < LT.SPR_FREE, "the spring is not preloaded at rest"
assert SPR_PRESS_L >= LT.SPR_SOLID, "the spring goes solid before full stroke"
PRELOAD_N = (LT.SPR_FREE - SPR_REST_L) * LT.SPR_RATE             # ~4.0
PRESS_N = (LT.SPR_FREE - SPR_PRESS_L) * LT.SPR_RATE              # ~12.0
assert SLIDER_BACK - STROKE > TUNNEL_BACK, (
    "the slider bottoms on the tunnel back before the stroke is done")


def _band(y0: float, y1: float, z0: float, z1: float, w: float = BAND_W):
    """A block across the band: X is width, Y radial depth, Z along the leg."""
    return box_at(w, y1 - y0, z1 - z0, y=(y0 + y1) / 2.0, z=(z0 + z1) / 2.0)


# The slider body must house the spring's seat and still have a back wall.
assert TEN_TOP - CLR - SLIDER_BACK >= SLIDER_SEAT + D.MIN_WALL_2P, (
    "the slider is %.2f deep; its spring seat needs %.2f plus a wall"
    % (TEN_TOP - CLR - SLIDER_BACK, SLIDER_SEAT))

# WHAT THE POCKET COSTS THE TENON, which is the real price of putting the
# mechanism here and is therefore measured, not estimated. It is a notch in the
# TENSION member at the joint's highest-moment station.
#
# MEASURE THE SECTION, DO NOT MULTIPLY THE BAND. Band x depth calls it 29%, which
# is wrong by a fifth: the tenon's roof falls away at 45 degrees either side of
# centre, so the top of that rectangle is mostly outside the section already.
_full = LS.tenon(1.0).val().Volume()
_left = LS.tenon(1.0).cut(
    _band(TUNNEL_BACK, TEN_TOP + 2.0, -1.0, 2.0)).val().Volume()
SECTION_LOSS = 1.0 - _left / _full                     # 0.235
assert SECTION_LOSS < 0.25, (
    "the slider pocket takes %.0f%% of the tenon's section" % (100 * SECTION_LOSS))
# Tension at the joint was ~10 MPa over the full section, SF ~5 (leg_stack). Over
# what is left it is ~13 MPa, SF ~3.8 -- still the cheap direction, but no longer
# free, and this is the number to revisit if the kick case gets worse.


# -- the moving part --------------------------------------------------------
# The recess floor sits over the bore. Directly over the apex the neck slot cuts
# through anyway, so the thinnest wall that SURVIVES is at the slot's edge, where
# the bore's roof has already fallen away at 45 degrees.
RECESS_FLOOR = FACE_Y - PAD_T - STROKE                 # 16.80
_SLOT_EDGE = NECK_W / 2.0 + CLR
_ROOF_AT_EDGE = (LS.TEN_W + 2 * LS.FIT) / math.sqrt(2.0) - _SLOT_EDGE
assert RECESS_FLOOR - _ROOF_AT_EDGE >= D.MIN_WALL_2P, (
    "only %.2f of sleeve wall under the pad recess at the neck slot's edge"
    % (RECESS_FLOOR - _ROOF_AT_EDGE))
assert PAD_W + 2 * CLR <= LS.LEG_W - 4 * D.MIN_WALL_2P, (
    "the pad recess leaves too little of the sleeve face either side")


# -- HOLDING FORCE (user: reliable when lifting/moving the instrument) ------
# MEASURED off the solids by closing each gap and pushing 0.2 further, not read
# off the constants. Load path when the leg hangs: adapter ledge -> hook -> slider
# -> the tenon pocket's end wall -> tenon -> screw -> sleeve.
#
#   ledge bearing (hook on adapter)     25.2 mm2 x 30 MPa  ~  760 N  <- weakest
#   adapter ledge shear-out             63.5 mm2 x 12 MPa  ~  760 N  <- weakest
#   hook root shear (off the slider)    74.8 mm2 x 12 MPa  ~  900 N
#   tenon pocket end wall bearing       81.7 mm2 x 30 MPa  ~ 2450 N
#
# Allowables are deliberately conservative for printed PETG-GF/PCTG: 12 MPa is an
# INTERLAYER shear figure, used for every shear plane because the slider's print
# orientation is not fixed yet. Against that, the heaviest thing it holds is the
# whole leg below the adapter -- 1.19 kg printed SOLID (an upper bound) = 11.7 N,
# 58 N at a x5 handling jolt. ~13x margin; strength is not what limits this latch.
# What does is ACCIDENTAL RELEASE: see the pad.


def _bore_prism(z0: float, z1: float, dy: float = 0.0, shrink: float = CLR):
    """The mortise's own octagon, as a prism over z0..z1, optionally lifted in Y.

    THE SLIDER IS SHAPED BY THIS, and that is the whole trick of the hook. The
    bore's roof is a 45 degree V, not a flat -- only 1.6 of it is level -- so a
    RECTANGULAR slider does not fit inside it: its top corners sit in solid
    adapter (measured: 197 mm3 at rest, plus 222 into the sleeve). Worse, a
    rectangular hook cannot RETRACT into the bore either, so the leg could not go
    on. Both faults vanish once the slider is clipped to this profile.

    Lift it by HOOK_ENGAGE and it becomes the hook: a V-topped tab standing
    exactly that far proud of the bore all the way across, which retracts clear
    with STROKE - HOOK_ENGAGE = 0.8 to spare.
    """
    prism = LS._at45(LS.octagon(LS.TEN_W + 2 * LS.FIT - 2 * shrink)
                     .extrude(z1 - z0))
    return prism.translate((0, dy, z0))


def slider() -> cq.Workplane:
    """One rigid piece reaching across the butt plane: HOOK deep on the adapter
    side, PAD out on the sleeve side, body and spring bore between them, all of it
    lying in the tenon's pocket.

    The only moving part in the joint. There is no cover: the sleeve is it.
    """
    e = CLR
    env = _band(SLIDER_BACK, HOOK_TIP + 1.0, HOOK_Z0 + e, BUTT + PAD_L - e,
                BAND_W - 2 * e)
    # body: everything that must stay inside the bore
    keep = _bore_prism(HOOK_Z1, BUTT + PAD_L + 1.0)
    # hook: the same profile, lifted, over its own stretch only
    keep = keep.union(_bore_prism(HOOK_Z0, HOOK_Z1, dy=LT.HOOK_ENGAGE))
    s = env.intersect(keep)
    # 45 LEAD-IN on the leading end, so the joint closes with no button pressed
    # (user: push to connect). The hook meets the adapter's mouth on this face.
    lead = (cq.Workplane("YZ")
            .polyline([(HOOK_TIP + 2.0, HOOK_Z0 - 1.0),
                       (HOOK_TIP + 2.0, HOOK_Z0 + LT.HOOK_ENGAGE),
                       (BORE_TOP - LT.HOOK_ENGAGE, HOOK_Z0 - 1.0)])
            .close().extrude(BAND_W))
    s = s.cut(cq.Workplane("XY").add(lead.val()).translate((-BAND_W / 2.0, 0, 0)))
    # neck, out through the sleeve wall...
    # ROOTED DOWN IN THE BODY, not started at the bore's crown (user). The body is
    # clipped to the bore's 45 roof, which at the neck's edges sits ~2.3 below
    # the crown -- so a neck starting near the crown joined the body only across
    # its middle, with an open triangle either side: a notch right at the root of
    # the part that takes the thumb load. Everything this fills is void in every
    # host (the tenon's pocket, the sleeve's slot, which runs down to the bore).
    s = s.union(_band(SLIDER_BACK, FACE_Y - PAD_T, BUTT + e, BUTT + PAD_L - e,
                      NECK_W - 2 * e))
    # ...and the 20 x 20 thumb plate on its end, flush with the outer face at rest
    s = s.union(_band(FACE_Y - PAD_T, FACE_Y, BUTT + e, BUTT + PAD_L - e,
                      PAD_W - 2 * e))
    # the spring's blind bore, opening at the back face
    s = s.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        LT.SPR_BORE_D / 2.0, SLIDER_SEAT + 0.01,     # +0.01: the bore starts
        cq.Vector(0, SLIDER_BACK - 0.01, SPR_Z), cq.Vector(0, 1, 0))))
    return s


def spring() -> cq.Workplane:
    """The steel coil, drawn at REST. HARDWARE, so its numbers are the part's and
    not on the bead grid."""
    # drawn at its true INSTALLED length, floor of the divot to floor of the seat
    # (it used to be drawn 8.0 long, which was neither its rest nor its free length)
    return (cq.Workplane("XY").add(cq.Solid.makeCylinder(
        LT.SPR_OD / 2.0, SPR_REST_L,
        cq.Vector(0, TUNNEL_BACK - DIVOT, SPR_Z), cq.Vector(0, 1, 0))))


# -- what each host part gives up -------------------------------------------
def tenon_pocket() -> cq.Workplane:
    """Cut in the TENON: the slider's seat, open to +Y through the tenon's roof."""
    # Ends at CLR, not 1.0. The pocket's -Z END WALL is where the whole pull-off
    # load lands (hook -> slider -> this wall -> tenon), so every mm of slop here
    # is a mm the leg drops before the latch takes the weight.
    pocket = _band(TUNNEL_BACK, TEN_TOP + 2.0,
                   HOOK_Z0 - CLR, BUTT + PAD_L + CLR, BAND_W)
    divot = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        LT.SPR_BORE_D / 2.0, DIVOT + 0.01,
        cq.Vector(0, TUNNEL_BACK - DIVOT, SPR_Z), cq.Vector(0, 1, 0)))
    return pocket.union(divot)


def sleeve_notch() -> cq.Workplane:
    """Cut in the FIXED SLEEVE: how the pad reaches the outside. OPEN AT THE BUTT
    FACE, which is what lets the slider drop in last and be captured by the
    adapter -- and the reason this latch needs no cover part."""
    # Only as wide as the NECK. The slider's body is clipped to the bore, so it
    # needs no relief here at all -- widening this was the wrong fix for a slider
    # that was the wrong shape.
    # From y=0, not from just under BORE_TOP: the bore's roof falls away at 45
    # degrees, so at the slot's EDGE it is ~3 mm lower than at its centre, and a
    # slot floored near BORE_TOP left a sliver of wall there that the PRESSED neck
    # ground into (17.6 mm3). Below the roof is the mortise, so this removes
    # nothing more than the sliver.
    slot = _band(0.0, FACE_Y + 1.0, BUTT - 1.0, BUTT + PAD_L,
                 NECK_W + 2 * CLR)
    # the plate's recess: exactly PAD_T + STROKE deep, so the floor stops the
    # press at full stroke -- the hook is clear by then, and the spring never
    # sees more than it was sized for. Open at the TOP of the print (the sleeve
    # lies +Y up), so it is a plain pocket with no overhang.
    recess = _band(RECESS_FLOOR, FACE_Y + 1.0, BUTT - 1.0, BUTT + PAD_L,
                   PAD_W + 2 * CLR)
    return slot.union(recess)


def adapter_pocket() -> cq.Workplane:
    """Cut in the BODY ADAPTER: the retention pocket, RUN inside the mouth so it
    has a +Z face. That face is the flat 90 ledge the leg hangs on -- pure shear,
    no cam-out, so a hard lift cannot pop the latch.

    Open to the BORE (not to the mouth): the hook enters by riding the bore
    retracted for RUN, then springing out into this."""
    # Reaches down past the bore on purpose: below the bore's roof there is
    # nothing to remove (that is the mortise), so this cuts only the sliver of
    # wall the hook actually stands in.
    return _band(0.0, POCKET_TOP, HOOK_Z0 - CLR, HOOK_Z1 + CLR,
                 BAND_W + 2 * CLR)
