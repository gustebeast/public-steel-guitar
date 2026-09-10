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

PUSH TO CONNECT, NO BUTTON (user). The hook sits just above the butt plane, so it
is outside the adapter for all but the last HOOK_Z + RUN of a 40 mm insertion: it
meets the adapter's MOUTH EDGE, cams in up its lead-in RAMP, rides the bore
retracted for RUN, and springs out into a pocket that is CLOSED on its mouth
side. The ramp has to follow the bore's 45-degree V -- see LEAD_DEG for the jam a
flat ramp produced. (An earlier version left the pocket open to the mouth. That retains nothing
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
from cadkit.holes import teardrop_hole
from .helpers import box_at

B = D.BEAD
CLR = 0.25                         # sliding clearance (a CLEARANCE: sub-bead by
                                   # necessity, like every gap in src.latch)
SLIDE_CLR = 0.40                   # the slider's clearance to the ADAPTER's bore at
                                   # rest -- larger than CLR on purpose (user: prints
                                   # are not exact). Two parts each printed 0.15
                                   # oversize still leave ~0.1, so the slider's body
                                   # never rubs the adapter's bore going in.
# WHERE THE SLIDER ACTUALLY RESTS. Nothing holds it at a drawn "zero": the spring
# pushes it out until its body's 45-degree flanks sit on the SLEEVE's bore. That
# contact IS the rest position, so the slider is drawn there -- and the pad's flush
# face, the hook's real reach and the insertion simulation all start from it.
# Drawn at the bare clearance instead, all three were out by CLR * sqrt2 toward
# the button; the pop-out check found it when a wider clearance opened the gap.
REST_OUT = CLR * math.sqrt(2.0)    # 0.354 the body's outward lift at rest
# Inside the SLEEVE the body keeps CLR -- that is what makes the rest position
# definite. Where it enters the ADAPTER it is shrunk further, so that even pushed
# out to rest it clears the adapter's bore by SLIDE_CLR at the tightest point (the
# apex flat, whose gap along Y is shrink - REST_OUT).
SHRINK_ADAPTER = SLIDE_CLR + REST_OUT   # 0.754
# The step between the two zones must print, so it is a 45-degree TRANSITION -- and
# its length is sqrt2 x the shrink change, not 1x: shrinking the octagon moves its
# flanks by the shrink but its APEX FLAT by sqrt2 x the shrink, and a 1x transition
# leaned that apex face out to 35 degrees (the overhang probe caught it).
TRANSITION_Z = math.sqrt(2.0) * (SHRINK_ADAPTER - CLR)   # 0.713
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
# ...and the hook as actually drawn, at rest: the adapter-zone body lifted to rest,
# plus its engagement. It must clear the bore when pressed and stay inside the pocket.
HOOK_REACH = BORE_R - SHRINK_ADAPTER + REST_OUT + LT.HOOK_ENGAGE   # 18.60
assert HOOK_REACH - STROKE <= BORE_R - D.MIN_WALL_2P / 2, (
    "pressed, the hook clears the bore by only %.2f" % (BORE_R - (HOOK_REACH - STROKE)))
assert HOOK_REACH + CLR <= HOOK_R + CLR, "the hook reaches past its pocket"
# The adapter prints BUTTON FACE DOWN (leg_stack.ADAPTER_UP), so the retention
# pocket's outer skin is a FLOOR in the print, not a roof: nothing is bridged, so
# nothing droops onto the hook. (Printed the other way up it was a 5.3 mm bridge
# and needed 0.3 of sag room.)
POCKET_R = HOOK_R + CLR                                # 19.74
assert FACE_R - POCKET_R >= D.MIN_WALL_2P, (
    "only %.2f of adapter skin over the retention pocket" % (FACE_R - POCKET_R))

# -- the band -----------------------------------------------------------------
BAND_W = 16 * B                    # 12.8 across X. Centred on the axis, where the
                                   # tenon reaches FURTHEST toward the button: its
                                   # apex falls away at 45 degrees either side, so
                                   # an off-centre band would have less under it.
HOOK_Z = 8 * B                     # 6.4 the hook's own length along the leg: the
                                   # lead-in ramp (LEAD_L) plus a real LAND of full
                                   # engagement before the ledge
# THE LEAD-IN, and why it cannot be a flat cut. The hook is the bore's own 45-degree
# V lifted HOOK_ENGAGE toward the button, so across the band its top sits lower
# and lower away from the centreline. The first lead-in was ONE PLANE across the
# band: at the band's edges the whole hook sat below where that plane started, so
# there its leading end was a flat square face. Simulated insertion with no hand on
# the button (scratch latch_insert_sim): the needed retraction jumped 2.05 mm in
# 0.1 mm of travel at first contact -- 87 degrees from the push axis, a WALL, and
# the joint self-locked at any real friction. Push-to-connect did not exist.
#
# So the ramp is a LOFT of the bore profile, ruled between its two ends, and every
# point across the band rises at the same LEAD_DEG from the push axis.
#
# BUILT TO SURVIVE THE PRINTER (user: a printed slope is only an approximation of
# the one drawn). Three allowances, each aimed at a specific way a print mangles
# this contact, all exercised by the worst-case insertion simulation (both parts
# 0.15 oversize, the ramp built as 0.2 mm stairs taken at their worst, a sharp
# adapter edge, friction to 0.5):
#   TIP_RELIEF  the ramp's leading end starts one bead INSIDE the bore, not at it,
#               so an oversize tip, a first-layer elephant's foot (the slider stands
#               on this end) or a blob still enters the mouth instead of stubbing
#   MOUTH_CH    a 45-degree chamfer on the adapter's mouth, so the ramp's printed
#               stair steps slide on a flat face instead of catching a square edge
#   SLIDE_CLR   the body's clearance to the bore (above)
LEAD_DEG = 30.0
TIP_RELIEF = 1 * B                 # 0.8 the leading end, recessed inside the bore
LEAD_L_MAX = HOOK_Z - B            # leave at least one bead of full-height land
MOUTH_CH = 3 * B                   # 2.4 the adapter mouth's chamfer, radially
RUN = 7 * B                        # 5.6 how far ABOVE the mouth the pocket sits.
                                   # It cannot sit AT the mouth: a pocket open to
                                   # the mouth has no face on that side, so the
                                   # hook would simply slide back out and the latch
                                   # would retain nothing. It is what makes the
                                   # pocket's mouth side a real 90 ledge -- and it
                                   # grew with MOUTH_CH, so the chamfer does not eat
                                   # the ledge the leg hangs on.
# THE PAD IS A THUMB TARGET, 20 x 20 (user: 8 x 12 was too small to press). It is
# a PLATE on a narrow NECK rather than a 20-wide slider, because the neck is what
# has to pass through the sleeve wall at the joint's highest-moment station, and
# only the plate has to be big. The plate sits in a RECESS in the sleeve face,
# flush at rest; the recess floor is the hard stop at full stroke.
PAD_W = 25 * B                     # 20.0 across X
PAD_FLAT = 25 * B                  # 20.0 of FLAT thumb face down the sleeve
# The slider prints STANDING ON ITS HOOK END (leg_stack.PRINT_UP), so the pad is at
# the top of the print -- and the plate reaches well outside the body it grows
# from, which would leave its upper end hanging over air. So that end is
# CORBELLED: a 45-degree draft out from the body's own outline (_corbel_draft).
# That draft takes CORBEL off the top of the plate, so the pad is longer by that
# much and the flat 20 x 20 face survives whole below it.
CORBEL = 14 * B                    # 11.2 the draft's depth: enough to reach the
                                   # plate's far corners (asserted)
PAD_SPAN = CORBEL + PAD_FLAT       # 31.2 the whole pad, from the butt plane down
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
Z_PAD_BOT = Z_BUTT - PAD_SPAN      # the pad runs from the butt plane down to here
SPR_Z = Z_PAD_BOT + PAD_FLAT / 2.0  # the spring sits behind the middle of the FLAT
                                   # face, where the thumb actually pushes

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


def lead_l() -> float:
    """The ramp's length along the leg, from LEAD_DEG (read at call time): it rises
    from TIP_RELIEF inside the bore to HOOK_ENGAGE outside it."""
    return (LT.HOOK_ENGAGE + TIP_RELIEF) / math.tan(math.radians(LEAD_DEG))


def hook_lift(z: float) -> float:
    """How far the slider's profile stands out past the bore at height z: 0 on
    the body, HOOK_ENGAGE on the hook's land, falling along the ramp to
    -TIP_RELIEF at the leading end. The insertion simulation reads this."""
    if z < Z_HOOK_LEDGE:
        return 0.0
    z_ramp = Z_HOOK_LEAD - lead_l()
    if z <= z_ramp:
        return LT.HOOK_ENGAGE
    t = min(1.0, (z - z_ramp) / lead_l())
    return LT.HOOK_ENGAGE - t * (LT.HOOK_ENGAGE + TIP_RELIEF)


def profile_at(z: float):
    """(lift toward the button, shrink) of the slider's section at height z, AT
    REST. Below the butt plane (in the sleeve) the body is lifted to rest and keeps
    CLR; across a 45-degree transition just above it, it shrinks to SHRINK_ADAPTER
    for the adapter; the hook's lift (hook_lift) rides on top of that. The slider
    and the insertion simulation both read this, so they cannot disagree."""
    t = TRANSITION_Z
    if z < Z_BUTT:
        shrink = CLR
    elif z < Z_BUTT + t:
        shrink = CLR + (z - Z_BUTT) / math.sqrt(2.0)
    else:
        shrink = SHRINK_ADAPTER
    return REST_OUT + hook_lift(z), shrink


def _bore_wire(z: float, lift: float, shrink: float = SHRINK_ADAPTER):
    """The mortise's 45-degree octagon at height z, lifted toward the button, as a
    closed world-space wire -- the two ends of the lead-in loft."""
    w = LS.TEN_W + 2 * LS.FIT - 2 * shrink
    h, c = w / 2.0, LS.CHAM / math.sqrt(2.0)
    # the same perimeter walk as leg_stack.octagon, square-on...
    sq = [(h - c, h), (-(h - c), h), (-h, h - c), (-h, -(h - c)),
          (-(h - c), -h), (h - c, -h), (h, -(h - c)), (h, h - c)]
    k = math.sqrt(0.5)
    # ...turned 45 degrees and placed on the leg's axis
    pts = [cq.Vector(LS.LEG_X + k * (x - y),
                     LS.LEG_Y + k * (x + y) + BUTTON_SIDE * lift, z) for x, y in sq]
    return cq.Wire.makePolygon(pts + [pts[0]])


def _lead_ramp(z_lo: float, z_hi: float):
    """Fully lifted at z_lo, recessed TIP_RELIEF inside the bore at z_hi (the
    leading end), ruled between: the lead-in, rising at LEAD_DEG across the V."""
    return cq.Workplane("XY").add(cq.Solid.makeLoft(
        [_bore_wire(z_lo, REST_OUT + LT.HOOK_ENGAGE),
         _bore_wire(z_hi, REST_OUT - TIP_RELIEF)], True))


def _corbel_draft():
    """The room the PAD may fill. Below the corbel, anything. Within it, only what
    a 45-degree draft out from the body's outline reaches -- so no layer of the pad
    overhangs the layer printed before it (the slider prints hook end down)."""
    # the body's outline where the pad meets it: the sleeve-zone profile, at rest
    a = (LS.TEN_W + 2 * LS.FIT - 2 * CLR) / math.sqrt(2.0) + REST_OUT
    z_top = Z_BUTT - CLR                     # the pad's own top face
    hx = BAND_W / 2.0 - CLR
    xa = LS.CHAM / 2.0                       # half the apex chamfer
    outline = [(-hx, SLIDER_BACK), (hx, SLIDER_BACK), (hx, a - hx),
               (xa, a - xa), (-xa, a - xa), (-hx, a - hx)]
    # The draft's zero plane is the pad's TOP FACE, not the butt plane: set at the
    # butt plane, the pad (which stops CLR short of it) was already allowed CLR of
    # growth on its first layer -- a 0.25 lip, flat, overhanging. The probe found it.
    pts = [cq.Vector(LS.LEG_X + x, LS.LEG_Y + BUTTON_SIDE * r, z_top)
           for x, r in outline]
    top = cq.Wire.makePolygon(pts + [pts[0]])
    # grow it OUTWARD. Which sign OCC's offset takes depends on the wire's winding,
    # and the inward one simply collapses on an outline this small (it returns no
    # wire at all), so keep whichever result exists and is bigger than the outline.
    grown = None
    for d in (CORBEL, -CORBEL):
        res = top.offset2D(d, "intersection")
        if res and res[0].BoundingBox().xlen > top.BoundingBox().xlen:
            grown = res[0]
            break
    assert grown is not None, "could not grow the body outline for the pad's corbel"
    low = grown.translate(cq.Vector(0, 0, -CORBEL))
    draft = cq.Workplane("XY").add(cq.Solid.makeLoft([low, top], True))
    z_lo = Z_PAD_BOT - 2.0
    below = box_at(4 * LS.LEG_W, 4 * LS.LEG_W, (z_top - CORBEL) - z_lo,
                   x=LS.LEG_X, y=LS.LEG_Y, z=(z_top - CORBEL + z_lo) / 2.0)
    return draft.union(below)


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
# The corbel must reach the plate's far corners, or they would still hang.
_A_BODY = (LS.TEN_W + 2 * LS.FIT - 2 * CLR) / math.sqrt(2.0) + REST_OUT
_CORNER_REACH = ((PAD_W / 2.0 - CLR) + FACE_R - _A_BODY) / math.sqrt(2.0)
assert _CORNER_REACH <= CORBEL, (
    "the pad's corners sit %.2f from the body outline; the corbel reaches %.2f"
    % (_CORNER_REACH, CORBEL))


# -- HOLDING FORCE (user: reliable when lifting/moving the instrument) ------
# MEASURED off the solids by closing each gap and pushing 0.2 further, not read
# off the constants. Load path when the leg hangs: adapter ledge -> hook -> slider
# -> the tenon pocket's upper end wall -> tenon -> screw -> sleeve.
#
#   hook root shear (off the slider)    32.0 mm2 x 12 MPa  ~  380 N  <- weakest
#   ledge bearing (hook on adapter)     20.8 mm2 x 30 MPa  ~  620 N
#   adapter ledge shear-out            ~89   mm2 x 12 MPa  ~ 1070 N  (estimate: the
#                                        21.5 hook outline x the ledge's ~4.15 run
#                                        left past the mouth chamfer)
#   tenon pocket end wall bearing       81.7 mm2 x 30 MPa  ~ 2450 N
#
# WHAT PRINT-FORGIVENESS COSTS THE HOOK. The 30-degree ramp now rises from TIP_RELIEF
# inside the bore, so it takes 5.54 of the 6.4 hook, and SLIDE_CLR trims the hook's
# section: protrusion beyond the bore 48.1 mm3 against 112.5 for a full-height hook,
# and the root shear (74.8 mm2, measured on that full-height hook) is scaled by the
# ratio. What it buys, simulated with no hand on the button from the slider's TRUE
# rest: as drawn, no jam and 9-13 N to seat (mu 0.3-0.5); as a worst-case print
# (both parts 0.15 oversize, the ramp as 0.2 mm stairs taken at their worst, a
# sharp adapter edge), still no jam at mu 0.5, 17-28 N, retraction 2.11 of the 3.2
# stroke. Guide friction is not included, so real pushes run somewhat higher.
#
# Allowables are deliberately conservative for printed PETG-GF/PCTG: 12 MPa is an
# INTERLAYER shear figure. The slider prints hook end down, which puts its root
# shear plane ACROSS the layers rather than along one, so that is conservative
# there. Against it, the heaviest thing the latch holds is the whole leg below the
# adapter -- 1.19 kg printed SOLID (an upper bound) = 11.7 N, 58 N at a x5 handling
# jolt. ~6.5x margin; strength is still not what limits this latch.
# What does is ACCIDENTAL RELEASE: see the pad.


def _bore_prism(z0: float, z1: float, lift: float = 0.0,
                shrink: float = SHRINK_ADAPTER):
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
    STROKE - HOOK_ENGAGE (plus SLIDE_CLR) to spare.
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
    L = lead_l()
    assert L <= LEAD_L_MAX + 1e-9, (
        "a %.0f-degree lead-in needs %.2f of hook but only %.2f is spare -- "
        "lengthen HOOK_Z or steepen LEAD_DEG" % (LEAD_DEG, L, LEAD_L_MAX))
    # body, AT REST (see profile_at): in the sleeve, lifted to rest and keeping CLR...
    keep = _bore_prism(Z_PAD_BOT - 1.0, Z_BUTT, lift=REST_OUT, shrink=CLR)
    # ...a 45-degree transition into the adapter zone...
    t = TRANSITION_Z
    keep = keep.union(cq.Workplane("XY").add(cq.Solid.makeLoft(
        [_bore_wire(Z_BUTT, REST_OUT, CLR),
         _bore_wire(Z_BUTT + t, REST_OUT, SHRINK_ADAPTER)], True)))
    # ...then shrunk to clear the adapter's bore by SLIDE_CLR
    keep = keep.union(_bore_prism(Z_BUTT + t, Z_HOOK_LEDGE, lift=REST_OUT))
    # the hook's LAND: the same profile, fully lifted, from the ledge up...
    keep = keep.union(_bore_prism(Z_HOOK_LEDGE, Z_HOOK_LEAD - L,
                                  lift=REST_OUT + LT.HOOK_ENGAGE))
    # ...then the LEAD-IN RAMP to the leading end, where it is not lifted at all,
    # so the adapter's mouth edge meets a slope, never a face (user: push to
    # connect with no button pressed)
    keep = keep.union(_lead_ramp(Z_HOOK_LEAD - L, Z_HOOK_LEAD))
    s = env.intersect(keep)
    # neck, out through the sleeve wall. ROOTED DOWN IN THE BODY, not started at
    # the bore's apex (user): the body is clipped to the bore's 45 V, which at the
    # neck's edges sits ~2.3 further in than at the apex -- so a neck starting near
    # the apex joined the body only across its middle, with an open triangle
    # either side: a notch right at the root of the part that takes the thumb
    # load. Everything this fills is void in every host (the tenon's pocket, the
    # sleeve's slot, which runs in to the axis).
    pad = _band(SLIDER_BACK, FACE_R - PAD_T, Z_PAD_BOT + e, Z_BUTT - e,
                NECK_W - 2 * e)
    # ...and the thumb plate on its end, flush with the outer face at rest
    pad = pad.union(_band(FACE_R - PAD_T, FACE_R, Z_PAD_BOT + e, Z_BUTT - e,
                          PAD_W - 2 * e))
    # both corbelled into the body at 45 degrees, so the pad prints on the body
    s = s.union(pad.intersect(_corbel_draft()))
    # the spring's blind bore, opening at the back face (starts 0.01 inside it, so
    # it runs 0.01 longer to keep its full depth). Sideways to the slider's print,
    # so via cadkit: a teardrop.
    return s.cut(teardrop_hole(
        LT.SPR_BORE_D, SLIDER_SEAT + 0.01,
        (LS.LEG_X, LS.LEG_Y + BUTTON_SIDE * (SLIDER_BACK - 0.01), SPR_Z),
        (0.0, BUTTON_SIDE, 0.0), LS.PRINT_UP["latch_slider"]))


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
    # the divot runs 45 degrees to the tenon's build, so cadkit returns it round
    divot = teardrop_hole(
        LT.SPR_BORE_D, DIVOT + 0.01,
        (LS.LEG_X, LS.LEG_Y + BUTTON_SIDE * (TUNNEL_BACK - DIVOT), SPR_Z),
        (0.0, BUTTON_SIDE, 0.0), LS.PRINT_UP["fixed_tenon"])
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


def mouth_chamfer() -> cq.Workplane:
    """Cut in the BODY ADAPTER: a 45-degree chamfer round the mouth, across the latch
    band only (see MOUTH_CH). The ramp's printed stairs then meet a flat slope, not
    a square corner. Its faces look into the bore and down, and the adapter prints
    button face DOWN, so in the print they face up: no overhang."""
    lo = _bore_wire(Z_BUTT - 1.0, MOUTH_CH + 1.0, shrink=0.0)
    hi = _bore_wire(Z_BUTT + MOUTH_CH, 0.0, shrink=0.0)
    cone = cq.Workplane("XY").add(cq.Solid.makeLoft([lo, hi], True))
    return cone.intersect(_band(0.0, FACE_R, Z_BUTT - 1.0, Z_BUTT + MOUTH_CH + 0.01,
                                BAND_W + 2 * CLR))
