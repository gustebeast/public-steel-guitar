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
    THE TENON, axis to its apex    16.17     <- the only solid section in the joint

So the mechanism goes in the tenon, which is exactly where the load is not, and
the joint's two hollow parts each give it something instead of housing it:

    THE ADAPTER gives the RETENTION POCKET. Its wall over the mortise is 5.81 and
      the hook needs only a 2.40 bite out of it.
    THE SLEEVE gives the NOTCH the button shows through, and doubles as the COVER
      -- the sleeve wall is what stands over the slider. That deletes latch.py's
      separate cover part outright.

BUTTON ON THE LEG (user: you pull it off with one hand). The pad sits flush in the
sleeve's -Y face, just below the butt plane, on the piece you are holding. The
adapter gets no hole and no button -- the same rule src.latch keeps.

ASSEMBLY -- and an earlier version of this paragraph was WRONG. It said to build
the leg first and drop the slider in through the notch afterwards. That cannot
work: the slider's body is 12.8 wide, the notch's neck slot is 8.5, and the
tenon's pocket is closed at both ends. The order that does work (user's
sequence, and swept -- see the fit tests):

  1. LATCH INTO THE TENON while it is separate: spring into the divot, slider
     over it into the pocket.
  2. SLIDE THE TENON DOWN into the fixed sleeve from its top (BUTT) end, pad held
     flush. Everything but the neck and pad lies inside the bore's own profile,
     so it passes straight through; the neck and pad ride into the notch, which is
     open at that end, over the last 20 mm.
  3. SCREW THE TENON TO THE FIXED SLEEVE (leg_stack.Z_FIX_SCREW; its twin,
     Z_ADJ_SCREW, pins the adjust sleeve when that goes on). The slider's body
     shoulders now sit under the sleeve's bore, which holds it in against the
     spring -- the SLEEVE IS THE COVER -- and the screw stops the tenon backing out
     of the sleeve, so the latch cannot fall out.
  4. offer the leg up to the body: push to connect, no button.

WHY THE HOOK NEEDS NO LONG RUN-IN CHANNEL. It sits just above the butt plane, so
it is outside the adapter for all but the last HOOK_Z + RUN (8.0) of a 40 mm
insertion: it meets the adapter's MOUTH EDGE, cams in on its lead-in, rides the
bore retracted for RUN, and springs out into a pocket that is CLOSED on its mouth
side. (An earlier version left the pocket open to the mouth. That retains nothing
-- there is no face for the hook to catch on.) That closed side is a flat 90
ledge, so pulling the leg down loads it in shear with no cam-out.

FRAME: world, like leg_stack -- every z is a real height. Radii are measured from
the leg's axis TOWARD THE BUTTON, and BUTTON_SIDE is the one place that says which
way that is.
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
BUTTON_SIDE = -1.0                 # the button faces -Y: inboard of the +Y rail,
                                   # toward the player


# -- the radii (from the leg's axis toward the button) -----------------------
def _apex_r(w: float, cham: float = LS.CHAM) -> float:
    """How far the leg's 45-degree section of `w` across flats reaches toward the
    button. The apex is a CHAMFER, not a point, so this is w/sqrt2 minus half the
    chamfer -- not the virtual apex, which is 0.8 further and would put every
    clearance here out by that much, in the unsafe direction."""
    return w / math.sqrt(2.0) - cham / 2.0


TEN_R = _apex_r(LS.TEN_W)                              # 16.171 the tenon's apex
BORE_R = _apex_r(LS.TEN_W + 2 * LS.FIT)                # 16.595 the mortise's
FACE_R = LS.LEG_W / 2.0                                # 22.400 the outer face
WALL = FACE_R - BORE_R                                 #  5.805 all there is

CH_FLOOR = BORE_R + 0.5            # pocket floor, stood off the bore so the hook
                                   # never rubs the tenon it rides beside
HOOK_R = CH_FLOOR + LT.HOOK_ENGAGE                     # 19.49 engaged
STROKE = LT.STROKE                 # 3.2 -- MUST exceed HOOK_ENGAGE, or pressing
                                   # the button cannot clear the bore
assert HOOK_R - STROKE < BORE_R, (
    "pressed, the hook still stands %.2f into the bore -- the leg cannot come off"
    % (HOOK_R - STROKE - BORE_R))
# BRIDGE SAG over the hook. The adapter prints button-face UP, so the retention
# pocket's outer skin is its ROOF: a 13.3 x 5.3 opening walled on all four sides,
# i.e. a 5.3 mm bridge -- routine, but a bridge droops, and the hook tip sat only
# CLR (0.25) under it. This is room for the droop, not material.
BRIDGE_SAG = 0.3
POCKET_R = HOOK_R + CLR + BRIDGE_SAG                   # 20.04
assert FACE_R - POCKET_R >= D.MIN_WALL_2P, (
    "only %.2f of adapter skin over the retention pocket" % (FACE_R - POCKET_R))

# -- the band -----------------------------------------------------------------
BAND_W = 16 * B                    # 12.8 across X. Centred on the axis, where the
                                   # tenon reaches FURTHEST toward the button: its
                                   # apex falls away at 45 degrees either side, so
                                   # an off-centre band would have less under it.
HOOK_Z = 6 * B                     # 4.8 the hook's own length along the leg
RUN = 4 * B                        # 3.2 how far ABOVE the mouth the pocket sits.
                                   # It cannot sit AT the mouth: a pocket open to
                                   # the mouth has no face on that side, so the
                                   # hook would simply slide back out and the latch
                                   # would retain nothing. This is the run the hook
                                   # rides RETRACTED against the bore before it
                                   # springs out -- and it is what turns the
                                   # pocket's mouth side into a real 90 ledge.
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

# -- the heights (world Z) ----------------------------------------------------
Z_BUTT = LS.Z_BUTT                 # adapter <-> fixed sleeve
Z_HOOK_LEDGE = Z_BUTT + RUN        # the hook's LOWER face: it hangs on the adapter's
                                   # ledge here
Z_HOOK_LEAD = Z_HOOK_LEDGE + HOOK_Z  # the hook's upper, LEADING end -- first into the
                                   # adapter, so the lead-in is on it
Z_PAD_BOT = Z_BUTT - PAD_L         # the pad runs from the butt plane down to here
SPR_Z = Z_BUTT - PAD_L / 2.0       # the spring sits behind the middle of the pad

# The slider's back face at rest, and the spring behind it. Same coil SKU as
# src.latch -- one spring for the whole instrument (user) -- so these are its
# numbers, not new ones.
SPR_GAP = LT.SPR_GAP               # 4.0 back face -> tunnel back at rest
TUNNEL_BACK = 4 * B                # 3.2 how deep the pocket goes. NOT a free
                                   # choice in either direction: shallower and the
                                   # slider has no room for the spring's seat plus
                                   # a wall behind it; deeper and it eats the
                                   # tenon. 3.2 is the shallowest that houses the
                                   # seat, and it is what sets SECTION_LOSS below.
SLIDER_BACK = TUNNEL_BACK + SPR_GAP                    # 7.2
# THE SPRING IS SEATED AT BOTH ENDS (user): a blind bore in the slider AND a
# divot in the tenon, so its far end cannot walk about under a side load.
#
# The seat depth is SPLIT, not added to. Deepening the tenon end on top of the
# slider's 6.4 would lengthen the spring's installed length by the same amount
# and throw away its preload -- at a 1.6 divot the coil would sit at exactly its
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


def _band(r0: float, r1: float, z0: float, z1: float, w: float = BAND_W):
    """A block across the band: `w` wide in X, from radius r0 out to r1 toward the
    button, from world z0 up to z1."""
    return box_at(w, r1 - r0, z1 - z0, x=LS.LEG_X,
                  y=LS.LEG_Y + BUTTON_SIDE * (r0 + r1) / 2.0, z=(z0 + z1) / 2.0)


def _radial_cyl(d: float, r0: float, length: float, z: float):
    """A cylinder on the band's centreline pointing at the button: starting at
    radius r0 and running `length` further out, at height z."""
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        d / 2.0, length, cq.Vector(LS.LEG_X, LS.LEG_Y + BUTTON_SIDE * r0, z),
        cq.Vector(0, BUTTON_SIDE, 0)))


def _radial_prism(pts, w: float = BAND_W):
    """A prism across the band from a profile of (radius, world z) points."""
    prof = (cq.Workplane("YZ")
            .polyline([(LS.LEG_Y + BUTTON_SIDE * r, z) for r, z in pts])
            .close().extrude(w))
    return cq.Workplane("XY").add(prof.val()).translate((LS.LEG_X - w / 2.0, 0, 0))


# The slider body must house the spring's seat and still have a back wall.
assert TEN_R - CLR - SLIDER_BACK >= SLIDER_SEAT + D.MIN_WALL_2P, (
    "the slider is %.2f deep; its spring seat needs %.2f plus a wall"
    % (TEN_R - CLR - SLIDER_BACK, SLIDER_SEAT))

# WHAT THE POCKET COSTS THE TENON, which is the real price of putting the
# mechanism here and is therefore measured, not estimated. It is a notch in the
# TENSION member at the joint's highest-moment station.
#
# MEASURE THE SECTION, DO NOT MULTIPLY THE BAND. Band x depth calls it 29%, which
# is wrong by a fifth: the tenon's apex falls away at 45 degrees either side of
# centre, so most of that rectangle is outside the section already.
_full = LS.section(LS.TEN_W, 0.0, 1.0).val().Volume()
_left = LS.section(LS.TEN_W, 0.0, 1.0).cut(
    _band(TUNNEL_BACK, TEN_R + 2.0, -1.0, 2.0)).val().Volume()
SECTION_LOSS = 1.0 - _left / _full                     # 0.235
assert SECTION_LOSS < 0.25, (
    "the slider pocket takes %.0f%% of the tenon's section" % (100 * SECTION_LOSS))
# Tension at the joint was ~10 MPa over the full section, SF ~5 (leg_stack). Over
# what is left it is ~13 MPa, SF ~3.8 -- still the cheap direction, but no longer
# free, and this is the number to revisit if the kick case gets worse.

# The recess floor sits over the bore. Directly over the apex the neck slot cuts
# through anyway, so the thinnest wall that SURVIVES is at the slot's edge, where
# the bore has already fallen away at 45 degrees.
RECESS_FLOOR = FACE_R - PAD_T - STROKE                 # 16.80
_SLOT_EDGE = NECK_W / 2.0 + CLR
_BORE_AT_SLOT_EDGE = (LS.TEN_W + 2 * LS.FIT) / math.sqrt(2.0) - _SLOT_EDGE
assert RECESS_FLOOR - _BORE_AT_SLOT_EDGE >= D.MIN_WALL_2P, (
    "only %.2f of sleeve wall under the pad recess at the neck slot's edge"
    % (RECESS_FLOOR - _BORE_AT_SLOT_EDGE))
assert PAD_W + 2 * CLR <= LS.LEG_W - 4 * D.MIN_WALL_2P, (
    "the pad recess leaves too little of the sleeve face either side")


# -- HOLDING FORCE (user: reliable when lifting/moving the instrument) ------
# MEASURED off the solids by closing each gap and pushing 0.2 further, not read
# off the constants. Load path when the leg hangs: adapter ledge -> hook -> slider
# -> the tenon pocket's upper end wall -> tenon -> screw -> sleeve.
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


def _bore_prism(z0: float, z1: float, lift: float = 0.0, shrink: float = CLR):
    """The mortise's own octagon as a prism from z0 up to z1, optionally lifted
    `lift` toward the button.

    THE SLIDER IS SHAPED BY THIS, and that is the whole trick of the hook. The
    bore's apex is a 45 degree V, not a flat -- only 1.6 of it is level -- so a
    RECTANGULAR slider does not fit inside it: its corners sit in solid adapter
    (measured: 197 mm3 at rest, plus 222 into the sleeve). Worse, a rectangular
    hook cannot RETRACT into the bore either, so the leg could not go on. Both
    faults vanish once the slider is clipped to this profile.

    Lifted by HOOK_ENGAGE it becomes the hook: a V-topped tab standing exactly
    that far proud of the bore all the way across, which retracts clear with
    STROKE - HOOK_ENGAGE = 0.8 to spare.
    """
    prism = LS.section(LS.TEN_W + 2 * LS.FIT - 2 * shrink, z0, z1)
    return prism.translate((0, BUTTON_SIDE * lift, 0))


# -- the moving part --------------------------------------------------------
def slider() -> cq.Workplane:
    """One rigid piece reaching across the butt plane: HOOK up in the adapter,
    PAD down on the sleeve, body and spring bore between them, all of it lying in
    the tenon's pocket.

    The only moving part in the joint. There is no cover: the sleeve is it.
    """
    e = CLR
    env = _band(SLIDER_BACK, HOOK_R + 1.0, Z_PAD_BOT + e, Z_HOOK_LEAD - e,
                BAND_W - 2 * e)
    # body: everything that must stay inside the bore
    keep = _bore_prism(Z_PAD_BOT - 1.0, Z_HOOK_LEDGE)
    # hook: the same profile, lifted, over its own stretch only
    keep = keep.union(_bore_prism(Z_HOOK_LEDGE, Z_HOOK_LEAD, lift=LT.HOOK_ENGAGE))
    s = env.intersect(keep)
    # LEAD-IN on the leading (upper) end, so the joint closes with no button
    # pressed (user: push to connect). The hook meets the adapter's mouth on it.
    s = s.cut(_radial_prism([(HOOK_R + 2.0, Z_HOOK_LEAD + 1.0),
                             (HOOK_R + 2.0, Z_HOOK_LEAD - LT.HOOK_ENGAGE),
                             (BORE_R - LT.HOOK_ENGAGE, Z_HOOK_LEAD + 1.0)]))
    # neck, out through the sleeve wall. ROOTED DOWN IN THE BODY, not started at
    # the bore's apex (user): the body is clipped to the bore's 45 V, which at the
    # neck's edges sits ~2.3 further in than at the apex -- so a neck starting near
    # the apex joined the body only across its middle, with an open triangle
    # either side: a notch right at the root of the part that takes the thumb
    # load. Everything this fills is void in every host (the tenon's pocket, the
    # sleeve's slot, which runs in to the axis).
    s = s.union(_band(SLIDER_BACK, FACE_R - PAD_T, Z_PAD_BOT + e, Z_BUTT - e,
                      NECK_W - 2 * e))
    # ...and the 20 x 20 thumb plate on its end, flush with the outer face at rest
    s = s.union(_band(FACE_R - PAD_T, FACE_R, Z_PAD_BOT + e, Z_BUTT - e,
                      PAD_W - 2 * e))
    # the spring's blind bore, opening at the back face (starts 0.01 inside it, so
    # it runs 0.01 longer to keep its full depth)
    return s.cut(_radial_cyl(LT.SPR_BORE_D, SLIDER_BACK - 0.01, SLIDER_SEAT + 0.01,
                             SPR_Z))


def spring() -> cq.Workplane:
    """The steel coil at REST, drawn at its true INSTALLED length: floor of the
    divot to floor of the seat. HARDWARE, so its numbers are the part's and not on
    the bead grid."""
    return _radial_cyl(LT.SPR_OD, TUNNEL_BACK - DIVOT, SPR_REST_L, SPR_Z)


# -- what each host part gives up -------------------------------------------
def tenon_pocket() -> cq.Workplane:
    """Cut in the TENON: the slider's seat, open toward the button through the
    tenon's apex, plus the spring's divot in its floor."""
    # Ends at CLR, not 1.0. The pocket's UPPER end wall is where the whole
    # pull-off load lands (the leg drops, the hook holds the slider, the slider
    # bears on this wall), so every mm of slop here is a mm the leg drops before
    # the latch takes the weight.
    pocket = _band(TUNNEL_BACK, TEN_R + 2.0,
                   Z_PAD_BOT - CLR, Z_HOOK_LEAD + CLR, BAND_W)
    divot = _radial_cyl(LT.SPR_BORE_D, TUNNEL_BACK - DIVOT, DIVOT + 0.01, SPR_Z)
    return pocket.union(divot)


def sleeve_notch() -> cq.Workplane:
    """Cut in the FIXED SLEEVE: how the pad reaches the outside. OPEN AT THE BUTT
    FACE, which is what lets the neck and pad ride in as the tenon goes down --
    and the sleeve stands over the slider, so this latch needs no cover part."""
    # Only as wide as the NECK. The slider's body is clipped to the bore, so it
    # needs no relief here at all.
    # From the axis, not from just inside the bore's apex: the bore falls away at
    # 45 degrees, so at the slot's EDGE it is ~3 mm further in than at its centre,
    # and a slot stopped near the apex left a sliver of wall there that the
    # PRESSED neck ground into (17.6 mm3). Inside the bore is the mortise, so this
    # removes nothing more than the sliver.
    slot = _band(0.0, FACE_R + 1.0, Z_PAD_BOT, Z_BUTT + 1.0, NECK_W + 2 * CLR)
    # the plate's recess: exactly PAD_T + STROKE deep, so the floor stops the
    # press at full stroke -- the hook is clear by then, and the spring never
    # sees more than it was sized for. The button face is the top of the print,
    # so it is a plain open pocket with no overhang.
    recess = _band(RECESS_FLOOR, FACE_R + 1.0, Z_PAD_BOT, Z_BUTT + 1.0,
                   PAD_W + 2 * CLR)
    return slot.union(recess)


def adapter_pocket() -> cq.Workplane:
    """Cut in the BODY ADAPTER: the retention pocket, RUN above the mouth so it is
    closed on the mouth side. That closed side is the flat 90 ledge the leg hangs
    on -- pure shear, no cam-out, so a hard lift cannot pop the latch.

    Open to the BORE (not to the mouth): the hook enters by riding the bore
    retracted for RUN, then springing out into this."""
    # Reaches in past the bore on purpose: inside the bore there is nothing to
    # remove (that is the mortise), so this cuts only the wall the hook stands in.
    return _band(0.0, POCKET_R, Z_HOOK_LEDGE - CLR, Z_HOOK_LEAD + CLR,
                 BAND_W + 2 * CLR)
