"""REDESIGNED LEG — a chain of through-mortise sleeves joined by floating tenons.

Built fresh alongside the old legs.py (which is untouched) so it can be looked at
without destabilising the build. ONE leg only: the -X/+Y (TRRS) station.

EVERY PART IS AUTHORED WHERE IT ACTUALLY IS: world X/Y on the leg's station, world
Z hanging down from the chassis underside. Nothing is built in a private frame
and moved into place, so a direction in this file means what it means in the
viewer -- +Y is +Y, up is up -- and every height is a named plane (Z_TOP, Z_BUTT,
Z_JOINT, ...) you can find on the model.

THE CHAIN, top to bottom:

    instrument body -- chassis underside                      Z_TOP
    body adapter (blind mortise)                    Z_TOP   .. Z_BUTT
      |__ the fixed sleeve BUTTS it; the fixed tenon runs up into it
    fixed sleeve (through mortise)                  Z_BUTT  .. Z_JOINT
      |__ FIXED floating tenon      joins the sleeves; screwed to each
    adjust sleeve (through mortise)                 Z_JOINT .. Z_ADJ_BOT
      |__ HEIGHT-ADJUST floating tenon   sets the height: a screw through a hole
    pedal bar (blind mortise)

WHY THE SLEEVE BUTTS THE ADAPTER instead of plugging into it (load-driven). The
kick case (250 N at 100 mm, leg at ~800 max = 175 N.m) puts the instrument's worst
moment at exactly the body joint. A tenon BRIDGING that joint takes the moment as
bending, and a 45-degree tenon is capped at 24.6 mm across flats by the 44.8 leg:

    sleeve 44.8 sq   Z 13937 mm^3   12.6 MPa   SF 4.0
    tenon  24.0      Z  1629 mm^3  107.4 MPa   SF 0.47   <- fails in bending

With the faces BUTTED the moment resolves instead into a couple -- compression
through the 44.8 faces, tension in the tenon -- and tension is the cheap
direction (~10 MPa, SF ~5). See body_adapter.

PROFILE: a square with its corners chamfered to a CHAM-wide flat -- an octagon
whose four extra sides are 1.6 (user: sharp corners cause joint fit issues). Used
turned 45 degrees about the leg's axis, which is what makes the mortise
self-supporting: the leg prints ON ITS SIDE, so the turned square puts an APEX at
the top of the print and the mortise roof is two 45-degree faces instead of a flat
bridge down the whole length.

NOT DONE YET: cable management and the TRRS jacks (no space is modelled -- the
pocket once "reserved" for them never cut anything, and a straight fix would bore
into the fixed tenon's overlap zone, so where they go is still open), and the
bar-end latch.
"""

from __future__ import annotations

import math

import cadquery as cq

from cadkit.holes import teardrop_hole
from . import chassis as CH
from . import dimensions as D
from . import legs as LG
from .helpers import box_at

B = D.BEAD

# ── where the leg is ────────────────────────────────────────────────────────
LEG_X = CH.LEG_STATIONS_X[1]      # the -X station: the TRRS leg
LEG_Y = CH.LEG_Y[0]               # on the +Y rail
Z_TOP = CH.Z_BOT                  # the adapter's top face, against the chassis underside

# ── the section ─────────────────────────────────────────────────────────────
LEG_W = 56 * B                    # 44.8 outer square of every sleeve (unchanged
                                  # from the old leg, so chassis interfaces hold)
TEN_W = 30 * B                    # 24.0 floating-tenon across flats
CHAM = 2 * B                      # 1.6 chamfer face width -- the octagon's four
                                  # extra sides. A true square's sharp corner is
                                  # where a printed joint binds: the outside
                                  # corner rounds to the nozzle radius while the
                                  # inside stays sharp, so the fit fights itself.
FIT = 0.30                        # slide fit, tenon in mortise (a CLEARANCE: it
                                  # is a gap, so the bead grid does not apply)

# The 45-degree turn is what makes the mortise printable, and it also sets the
# wall: the octagon's DIAGONAL points at the sleeve's faces.
WALL_MIN = LEG_W / 2 - (TEN_W + 2 * FIT) * math.sqrt(2) / 2
assert WALL_MIN >= 2 * D.MIN_WALL_2P, (
    "mortise wall %.2f is under two two-bead walls -- shrink TEN_W" % WALL_MIN)


# ── lengths (a single leg; the height range lives in the adjust section) ─────
# STRENGTH BUDGET: least engagement of a tenon in its mortise. Two tenon widths
# is the joinery rule of thumb, and it is what stops the joint hinging open --
# the moment at a slide joint resolves into a couple over the engagement, so the
# bearing force is M/L and shortening L raises it hyperbolically. At 2 x TEN_W
# the adjust joint's ~26 N.m gives ~540 N on the walls; halve the engagement and
# it doubles.
ENGAGE = 50 * B                   # 40.0 = 1.67 x TEN_W, down from the 2.00 rule of
                                  # thumb. SPENT DELIBERATELY ON REACH (user): the
                                  # tenon is bed-capped, so every mm off the
                                  # engagement buys TWO mm of fixed sleeve, and the
                                  # whole leg reaches 804 - 3 * ENGAGE. 48 tops out
                                  # at 660 and the 95th-percentile player needs
                                  # 674.9; 40 reaches 684. It also lengthens the
                                  # travel, since ADJ_TRAVEL = ADJ_TEN_L - 2*ENGAGE
                                  # -- 156 -> 172. Two wins from one number, which
                                  # is why it is worth spending carefully: the wall
                                  # force at a slide joint is M/L, so this raises it
                                  # 20% (the adjust joint's ~26 N.m over 40 rather
                                  # than 48 mm: ~650 N instead of ~540).
ADAPT_WALL = 16 * B               # 12.8 the adapter's CLOSED END: a solid wall that
                                  # hugs the body and carries the joinery attaching
                                  # the leg to it (user). The mortise is BLIND, not
                                  # through -- the tenon used to run to the adapter's
                                  # very top face, leaving nothing to fix it by.
ADAPT_L = ADAPT_WALL + ENGAGE     # 52.8 wall + the tenon's engagement, no more
BED = 315 * B                     # 252.0 longest printed part. The bed is 255 sq,
                                  # but sizing to the DIAGONAL would mean one part
                                  # per plate (user), so this is the square limit.
ADJ_L = BED                       # 252.0 adjust sleeve -- AS LONG AS THE BED
                                  # ALLOWS, because its length is what buys height
                                  # adjustment; the fixed section takes the rest
FIX_L = BED - 2 * ENGAGE          # 172.0 fixed sleeve: as long as the bed lets its
                                  # own tenon be (FIX_L + 2*ENGAGE = BED exactly)
# ADJUST TENON -- DERIVED, not chosen (user). Two constraints set it:
#   SHORTEST leg: the tenon pushed up as far as it goes. It cannot hide entirely,
#     because its bottom end must always be engaged in the PEDAL BAR -- so the
#     least it can ever show is ENGAGE. Buried length is then ADJ_TEN_L - ENGAGE,
#     which must fit its mortise: ADJ_TEN_L <= ADJ_L + ENGAGE.
#   LONGEST leg: out as far as the strength budget allows, i.e. until only
#     ENGAGE remains in the sleeve.
# and the bed caps it. Travel is what is left between the two.
ADJ_TEN_L = min(BED, ADJ_L + ENGAGE)          # 252.0
ADJ_TRAVEL = ADJ_TEN_L - 2 * ENGAGE           # 172.0 usable height adjustment
FIX_TEN_L = FIX_L + 2 * ENGAGE    # 252.0 fixed tenon: the FULL length of its own
                                  # sleeve PLUS an extension at each end, so the
                                  # one bar does the work of a tenon at BOTH
                                  # neighbouring joints (user). It is never seen:
                                  # a fixed-length tenon has no reason to show.

# ── the planes, top to bottom (world Z) ─────────────────────────────────────
Z_MORTISE_ROOF = Z_TOP - ADAPT_WALL        # the adapter's closed end stops here --
                                           # and the fixed tenon's top end sits on it
Z_BUTT = Z_TOP - ADAPT_L                   # adapter <-> fixed sleeve, face to face
Z_JOINT = Z_BUTT - FIX_L                   # fixed sleeve <-> adjust sleeve
Z_ADJ_BOT = Z_JOINT - ADJ_L                # the adjust sleeve's bottom face
Z_FIX_TEN_BOT = Z_MORTISE_ROOF - FIX_TEN_L # the fixed tenon's bottom end, ENGAGE
                                           # down inside the adjust sleeve
# The adjust tenon's TOP END is the height setting. Its range:
Z_ADJ_TEN_TOP_LONG = Z_ADJ_BOT + ENGAGE              # longest leg: only ENGAGE
                                                     # left inside the sleeve
Z_ADJ_TEN_TOP_SHORT = Z_ADJ_BOT - ENGAGE + ADJ_TEN_L # shortest: only ENGAGE left
                                                     # showing, for the bar
Z_ADJ_TEN_TOP = Z_ADJ_TEN_TOP_LONG         # AS DRAWN: the longest setting
Z_ADJ_TEN_BOT = Z_ADJ_TEN_TOP - ADJ_TEN_L
# WHERE THE PEDAL BAR GOES. It does not get to choose: it hangs off the adjust
# tenon's bottom end, which is wherever the height setting put it. The tenon
# buries ENGAGE into the bar's tower, the same rule as every other joint, so the
# tower's mouth sits ENGAGE above the tenon's end. ONE expression, read by the bar.
Z_BAR_MOUTH = Z_ADJ_TEN_BOT + ENGAGE

# ── height adjust: a ladder of holes, not friction ──────────────────────────
ADJ_HOLE_D = 5 * B                # 4.0 through-hole for the M4 locking screw
ADJ_WEB = 2 * B                   # 1.6 material between holes -- this web, not
                                  # the screw, is what tears out under load, so
                                  # it is the number that sets pull-out strength
ADJ_PITCH = ADJ_HOLE_D + ADJ_WEB  # 5.6 and therefore the HEIGHT STEP
ADJ_N = int(ADJ_TRAVEL / ADJ_PITCH)           # 30 steps -> ADJ_N + 1 holes
# ONE ROW. There used to be two, half a pitch apart, meant to halve the step
# "without thinning any web". They could not: both ran along the same axis, so
# Ø4.0 holes at 2.8 spacing OVERLAP and the row becomes a slot with no web at all.
# Two rows on crossing axes do not rescue it either: through-holes both pass the
# tenon's centre, so they still meet there. A finer step needs a different
# mechanism, not a second row.
#
# WHERE THE SCREW GOES. It must pass through BURIED tenon at every setting, and
# the tenon is only guaranteed buried over the sleeve's bottom ENGAGE (at the
# LONGEST setting that is all that is left inside). So the sleeve's hole sits in
# the middle of that zone, and the ladder is exactly the tenon positions that one
# hole sees across the travel.
Z_LADDER = Z_ADJ_BOT + ENGAGE / 2.0           # the adjust sleeve's screw hole
LADDER_OFF = ENGAGE / 2.0                     # 20.0 first tenon hole, down from
                                              # the tenon's top end


def ladder_top(i: int) -> float:
    """The adjust tenon's top end at ladder setting i (0 = longest leg): the
    height at which tenon hole i sits on the sleeve's hole."""
    return Z_LADDER + LADDER_OFF + i * ADJ_PITCH


assert LADDER_OFF + ADJ_N * ADJ_PITCH + ADJ_HOLE_D / 2 <= ADJ_TEN_L - ENGAGE, (
    "the ladder's last hole reaches into the bar-engaged end of the tenon")
assert (ladder_top(0) >= Z_ADJ_TEN_TOP_LONG - 1e-9
        and ladder_top(ADJ_N) <= Z_ADJ_TEN_TOP_SHORT + 1e-9), (
    "the ladder asks for settings outside the travel")

# ── the sleeve-joint screws (user) ──────────────────────────────────────────
# TWO, one each side of the fixed/adjust sleeve joint and equidistant from it,
# each pinning ONE sleeve to the fixed tenon. That tenon is what holds the two
# sleeves together; with only one sleeve pinned, the adjust sleeve, its tenon and
# the pedal bar rode on a bare slide fit and would slide off the moment the
# instrument was lifted.
#
# Both land in the tenon's ENGAGE-long overlap zone, the one stretch of the leg
# where tenon and both sleeves coexist. Same M4 convention as the ladder
# (clearance in the sleeve, ADJ_HOLE_D in the tenon), and along X, not Y: along Y
# they would line up with the button face.
SCREW_OFF = 16 * B                               # 12.8 either side of the joint
Z_FIX_SCREW = Z_JOINT + SCREW_OFF                # in the FIXED sleeve, above
Z_ADJ_SCREW = Z_JOINT - SCREW_OFF                # in the ADJUST sleeve, below
_CLR_D = ADJ_HOLE_D + 0.8                        # 4.8 clearance in a sleeve
# Edge distance: each hole sits near an END -- the sleeve joint face on one side,
# the fixed tenon's bottom end for the adjust one -- and that end is the direction
# a hanging load tears it out. Two hole diameters of material is the floor.
assert SCREW_OFF - _CLR_D / 2 >= 2 * _CLR_D, (
    "only %.1f from each screw to the sleeve joint face" % (SCREW_OFF - _CLR_D / 2))
assert Z_ADJ_SCREW - Z_FIX_TEN_BOT - ADJ_HOLE_D / 2 >= 2 * _CLR_D, (
    "the adjust-side screw is too close to the fixed tenon's bottom end")

# EVERY SCREW GOES IN FROM +X, AND THE -X FACE STAYS WHOLE (user). The two kinds of
# screw carry very different loads, so they stop in different places:
#
#   SLEEVE-JOINT screws only see load when the leg HANGS (lifting the instrument):
#     the lower leg's weight, ~20 N, ~100 N with a jolt. They go JOIN_SEAT into the
#     tenon from its +X apex and stop -- 4 x 12 = 48 mm2 of bearing at 30 MPa is
#     ~1.4 kN against that.
#
#   The LADDER screw carries the WHOLE LEG LOAD whenever the instrument stands:
#     body -> butts -> adjust sleeve -> ladder screw -> adjust tenon -> bar ->
#     floor. It goes in from +X and stops BLIND IN THE TENON, LADDER_SKIN short of
#     the tenon's -X faces. It used to run through the tenon into a seat in the
#     sleeve's -X wall, for support both sides -- but the adjust tenon is the one
#     part of the leg that is EXPOSED, and that left every ladder hole open on its
#     -X side (user: keep the exposed -X face clean).
#     What that costs, stated: with ~29 mm of engagement the screw's only bending
#     arm is the 0.3 fit gap at the +X wall, so the M4 is still in near-pure shear
#     (~53 MPa at a hard 400 N lean). What drops is BEARING -- only the +X sleeve
#     wall carries it now: 4 x 5.8 = 23 mm2, ~700 N at 30 MPa, SF ~1.75 on 400 N.
JOIN_SEAT = 15 * B                 # 12.0 sleeve-joint screw depth into the tenon, 3 x d
LADDER_SKIN = D.MIN_WALL_2P        # 1.6 of tenon left over the ladder hole's blind end,
                                   # measured SQUARE to the tenon's 45-degree -X flanks
# The blind end sits where the hole's EDGE (not its centre) keeps LADDER_SKIN to the
# flank: the flank is |x| + |y| = TEN_W/sqrt2, the hole edge is at |y| = d/2, and a
# 45-degree face puts sqrt2 x the skin along X.
# THE TENON'S HOLES run exactly 45 degrees to its build, so a plain round bore sits
# exactly AT the self-support limit -- and at each +X mouth its crown runs downhill
# out through the flank and the last of it hangs (layer-support check: ~0.15 mm2 per
# hole; a face-angle probe could not see it). Cut with a STRICTER limit, the crown
# gets a peak and clears, mouth included (cadkit.holes). How strict is MEASURED, not
# picked: 50 still left 0.17 mm2 across three holes; 60 leaves 0.0 even with the
# check's noise threshold dropped to 0.02.
TEN_HOLE_LIMIT_DEG = 60.0
_TEN_HOLE_TILT_DEG = 45.0          # every tenon hole is 45 to the tenon's build
# ...and the peak reaches further than the round bore, toward the build direction
TEN_HOLE_REACH = (ADJ_HOLE_D / 2.0) / (math.cos(math.radians(TEN_HOLE_LIMIT_DEG))
                                       / math.sin(math.radians(_TEN_HOLE_TILT_DEG)))  # 2.83
LADDER_BOTTOM_X = -(TEN_W / math.sqrt(2.0) - TEN_HOLE_REACH
                    - LADDER_SKIN * math.sqrt(2.0))           # -11.88 from the axis
TEN_APEX = TEN_W / math.sqrt(2.0) - CHAM / 2.0   # 16.171 axis -> the tenon's apex,
                                                 # which faces +X as well as +Y
assert JOIN_SEAT < TEN_APEX, "a sleeve-joint screw would come out of the tenon's -X side"
assert LADDER_SKIN >= D.MIN_WALL_2P

# BODY JOINERY (user): TENONS on the adapter's top face, into mortises the body
# ALREADY HAS -- the ones the old body stub used. They are cut into the chassis
# and the keyhead endplate by legs.corner_groove_negatives, the one shared source
# both parts use, so the tenons here come from that same module (legs._stub_ridge,
# legs._cross_x, the STUB_TNG_* numbers) and line up BY CONSTRUCTION, not by
# copied numbers. (The first version bolted the adapter up with four M4s through
# the closed end -- joinery the body has no holes for.) Per corner:
#   * two Y-running octagon RIDGES at the thirds of the side-panel overlap; the
#     middle one's INBOARD end is cut back by legs.SERVICE_SLIDE (user: the endplates
#     use that space; the leg slides out that far to reach it)
#   * one rectangular END-WALL TONGUE into a rebate against the endplate wall's
#     inner face; its blind end is the flush hard stop
#   * ONE SCREW (user): an M4 set-screw LOCK PIN along X, threaded in a heat-set
#     insert in the endplate's end wall and crossing the tongue through a clearance
#     hole. It locks the leg in the body and the endplate to the chassis. With a
#     service slide set, a SECOND tongue hole SERVICE_SLIDE inboard takes the same
#     screw with the leg slid out to its service position.
# The ridges are undercut, so this joint SLIDES IN ALONG Y from outboard -- the
# adapter cannot go straight up. It is the semi-permanent half: fitted once.
assert abs(LG.SQ_W - LEG_W) < 1e-9, "the body's mortises were cut for a %.1f leg" % LG.SQ_W
SYG = 1.0 if LEG_Y > sum(CH.LEG_Y) / 2 else -1.0            # this corner's outboard Y sign
EGX = -1.0 if sum(CH.LEG_STATIONS_X) / 2 > LEG_X else 1.0   # this corner's outboard
                                                            # X sign, as the chassis
                                                            # computes it


# ── the section, as solids on the leg's axis ────────────────────────────────
def octagon(w: float, cham: float = CHAM):
    """Square of `w` across flats with its corners chamfered to `cham`-wide
    faces, as a closed 2-D wire on XY, centred on the origin and drawn
    square-on. `section` is what turns it 45 degrees and stands it on the leg."""
    h = w / 2.0
    c = cham / math.sqrt(2.0)          # the corner leg the chamfer cuts off
    pts = []
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        pts.append((sx * (h - c), sy * h))
        pts.append((sx * h, sy * (h - c)))
    # WALK THE PERIMETER. Getting this order wrong does not fail -- it makes a
    # self-crossing polygon that still extrudes, and the damage shows up as one
    # mangled corner while the other three chamfer correctly. The area assert
    # below is what actually catches it.
    #   flat, chamfer, flat, chamfer, ... counter-clockwise from the +Y edge
    loop = [pts[0], pts[2],      # +Y flat      (h-c, h) -> (-(h-c), h)
            pts[3], pts[5],      # -X flat      (-h, h-c) -> (-h, -(h-c))
            pts[4], pts[6],      # -Y flat      (-(h-c), -h) -> (h-c, -h)
            pts[7], pts[1]]      # +X flat      (h, -(h-c)) -> (h, h-c)
    # NB: rotate the SOLID after extruding, never the Workplane here --
    # polyline().close() leaves a PENDING wire, not an object on the stack, so
    # extrude() would consume the unrotated profile and the 45 would silently
    # vanish (caught by the bounding box: 24.0 across instead of 33.9).
    return cq.Workplane("XY").polyline(loop).close()


# A self-crossing profile still EXTRUDES -- it just yields a mangled corner and a
# wrong section. Gate it on the one number that cannot lie: a chamfered square is
# the square minus its four corner triangles, w^2 - cham^2 exactly.
assert abs(octagon(TEN_W).extrude(1.0).val().Volume() - (TEN_W ** 2 - CHAM ** 2)) < 1e-6, (
    "the octagon profile is self-crossing -- check the perimeter walk")


def section(w: float, z0: float, z1: float, cham: float = CHAM):
    """The leg's section, `w` across flats and turned 45 degrees, as a prism on the
    leg's axis from world z0 up to z1. The turn puts an APEX where the print's
    top will be, so the mortise roof is two 45-degree faces, not a bridge."""
    prism = octagon(w, cham).extrude(z1 - z0).rotate((0, 0, 0), (0, 0, 1), 45)
    return prism.translate((LEG_X, LEG_Y, z0))


def tenon(z0: float, z1: float, w: float = TEN_W):
    """A floating tenon running from world z0 up to z1."""
    return section(w, z0, z1)


def mortise_cutter(z0: float, z1: float, w: float = TEN_W, fit: float = FIT):
    """The matching hole from z0 up to z1, grown by the slide fit on every face."""
    return section(w + 2 * fit, z0, z1)


def _sleeve(z0: float, z1: float):
    """A leg section from z0 up to z1: LEG_W square, octagon mortise straight
    through."""
    b = box_at(LEG_W, LEG_W, z1 - z0, x=LEG_X, y=LEG_Y, z=(z0 + z1) / 2.0)
    return b.cut(mortise_cutter(z0 - 1.0, z1 + 1.0))


def _from_plus_x(d: float, z: float, x_end: float, print_up,
                 limit_deg: float = 45.0):
    """A hole along X, entering from outside the +X face and stopping at world
    x_end, at height z. Via cadkit, so it is shaped for the part it is cut into: a
    teardrop in a sleeve (sideways to its build), a plain round bore in a tenon
    (45 degrees to its build -- the round bore already self-supports there)."""
    x0 = LEG_X + LEG_W / 2.0 + 2.0
    return teardrop_hole(d, x0 - x_end, (x0, LEG_Y, z), (-1.0, 0.0, 0.0), print_up,
                         limit_deg=limit_deg)


# ── the printed parts ───────────────────────────────────────────────────────
def adjust_sleeve():
    """The HEIGHT-ADJUST section: the long one, so the tenon can be set over a
    wide range. Carries the ladder screw's clearance hole."""
    b = _sleeve(Z_ADJ_BOT, Z_JOINT)
    # pinned to the FIXED tenon near the joint -- what stops this sleeve, its tenon
    # and the pedal bar sliding off when the instrument is lifted
    # clearance through the +X wall only; the -X wall is untouched
    b = b.cut(_from_plus_x(_CLR_D, Z_ADJ_SCREW, LEG_X, SLEEVE_UP))
    # the LADDER screw: clearance through the +X wall only. Its tip ends blind in
    # the tenon, so the -X wall is untouched too.
    return b.cut(_from_plus_x(_CLR_D, Z_LADDER, LEG_X, SLEEVE_UP))


def fixed_sleeve():
    """The FIXED section. Its own 44.8 body BUTTS the body adapter, so the kick
    moment never passes through a tenon (see the module docstring).

    Carries the latch NOTCH -- the way the button reaches the outside, and the
    part that stands over the slider in place of a cover."""
    from . import leg_latch as LL          # late: leg_latch reads this module
    b = _sleeve(Z_JOINT, Z_BUTT)
    b = b.cut(LL.sleeve_notch())
    # clearance through the +X wall only; the -X wall is untouched
    return b.cut(_from_plus_x(_CLR_D, Z_FIX_SCREW, LEG_X, SLEEVE_UP))


def adjust_tenon(top: float = Z_ADJ_TEN_TOP):
    """Floating tenon, adjust sleeve <-> pedal bar, with its top end at `top`
    (default: as drawn, the longest leg; ladder_top(i) gives setting i).

    The LADDER of holes is the height setting: pick a hole, drop the screw, and
    every leg set to the same hole index is at the same height -- repeatable
    without measuring, which friction alone never is."""
    t = tenon(top - ADJ_TEN_L, top)
    for i in range(ADJ_N + 1):
        z = top - (LADDER_OFF + i * ADJ_PITCH)
        # in from +X, BLIND: stops LADDER_SKIN short of the -X flanks, so the
        # exposed tenon's -X side shows no holes (user). Via cadkit, which returns
        # a plain round bore at 45 to the tenon's diagonal build.
        t = t.cut(_from_plus_x(ADJ_HOLE_D, z, LEG_X + LADDER_BOTTOM_X, TENON_UP,
                               limit_deg=TEN_HOLE_LIMIT_DEG))
    # the PEDAL BAR's latch hooks this end: its retention pocket and lead-in chamfer,
    # placed from where this tenon seats in the bar (src.bar_latch)
    from . import bar_latch as BL
    return t.cut(BL.tenon_cut(top - ADJ_TEN_L + ENGAGE))


def fixed_tenon():
    """Floating tenon, fixed sleeve <-> adjust sleeve. Its top end sits on the
    adapter's mortise roof, its bottom end ENGAGE down inside the adjust sleeve.

    This is the piece that HOLDS THE LEG ON THE BODY (user), and it is also the
    only solid section at that joint -- so it hosts the latch's pocket. What that
    costs the tenon is measured in leg_latch.SECTION_LOSS."""
    from . import leg_latch as LL
    t = tenon(Z_FIX_TEN_BOT, Z_MORTISE_ROOF)
    t = t.cut(LL.tenon_pocket())
    # both sleeve-joint screws bite the tenon, one per sleeve: in from the +X
    # apex JOIN_SEAT deep, and no further
    for z in (Z_FIX_SCREW, Z_ADJ_SCREW):
        t = t.cut(_from_plus_x(ADJ_HOLE_D, z, LEG_X + TEN_APEX - JOIN_SEAT,
                               TENON_UP, limit_deg=TEN_HOLE_LIMIT_DEG))
    return t


def body_adapter(sx: float = LEG_X, ly: float = LEG_Y):
    """Quick-release adapter: bolts to the body, and is otherwise JUST ANOTHER
    MORTISE SECTION -- same 44.8 outer as every sleeve, so it ends FLUSH with the
    rest of the leg (user). It wraps the fixed tenon's upper end; the sleeve BUTTS
    it face to face rather than plugging into it.

    THAT BUTT IS WHAT CARRIES THE KICK. A tenon BRIDGING a gap here would take the
    175 N.m as BENDING in a 24 mm section: Z 1629 mm^3, 107 MPa, SF 0.47. With
    the faces in contact the moment resolves instead into a couple -- COMPRESSION
    carried by the butted 44.8 faces (which cannot fail that way) and TENSION
    carried by the tenon. Tension is the cheap direction: ~5.8 kN over the
    tenon's ~576 mm^2 is about 10 MPa, SF ~5.

    So the load path is the joint, not the bar. Keep the faces butted.

    ANY CORNER (user: one leg, adapters at the other three). The leg-facing half --
    the mortise, the latch pocket, the mouth chamfer -- is the same everywhere, so it
    is built on this leg's axis and moved to (sx, ly). The body joinery on top is
    built for the corner it slides into: its end (egx), its rail (syg) and its
    service slide."""
    from . import leg_latch as LL
    egx = -1.0 if sum(CH.LEG_STATIONS_X) / 2 > sx else 1.0   # the corner's outboard x
    syg = 1.0 if ly > sum(CH.LEG_Y) / 2 else -1.0            # ...and y signs
    b = box_at(LEG_W, LEG_W, ADAPT_L, x=LEG_X, y=LEG_Y, z=(Z_BUTT + Z_TOP) / 2.0)
    # BLIND mortise: open at the butt face, closed at the mortise roof
    b = b.cut(mortise_cutter(Z_BUTT - 1.0, Z_MORTISE_ROOF))
    # the latch's retention pocket -- the ledge the whole leg hangs on -- and the
    # chamfered mouth that lets a printed hook ride in without catching
    b = b.cut(LL.adapter_pocket())
    b = b.cut(LL.mouth_chamfer())
    b = b.translate((sx - LEG_X, ly - LEG_Y, 0.0))
    # BODY TENONS, on the top face (see BODY JOINERY). Both ridges and the tongue
    # run the full LEG_W along Y, the slide axis.
    mid_cut = LG.service_slide(egx, syg)
    for i, dx in enumerate(LG._cross_x(egx)):
        cut = mid_cut if i == 0 else 0.0        # the middle ridge gives up its inboard end
        if cut >= LEG_W - 1e-9:
            continue
        y0 = ly - LEG_W / 2.0 + (cut if syg > 0 else 0.0)
        ridge = LG._stub_ridge(LEG_W - cut).translate((sx + dx, y0, Z_TOP))
        b = b.union(ridge)
    b = b.union(box_at(LG.STUB_TNG_W, LEG_W, LG.STUB_TNG_H,
                       x=sx + egx * LG.STUB_RIDGE_EP, y=ly,
                       z=Z_TOP + LG.STUB_TNG_H / 2.0))
    # M4 LOCK PIN, the adapter's ONLY screw (user): the set screw from the endplate's
    # insert crosses the tongue along X, locking the leg in the body and the endplate to
    # the chassis. Its SECOND hole, SERVICE_SLIDE inboard along the tongue, is where that
    # screw lands with the leg slid out to its service position (legs.SERVICE_SLIDE).
    # The same legs helper the endplate's half comes from, shaped by cadkit.
    for dy in (0.0,) + ((-syg * mid_cut,) if mid_cut else ()):
        b = b.cut(LG.tongue_pin_cutter(sx, ly + dy, egx, Z_TOP, ADAPTER_UP, syg))
    return b


# Nothing may need the bed's diagonal: that would mean one part per plate.
for _n, _l in (("adjust sleeve", ADJ_L), ("fixed sleeve", FIX_L),
               ("adjust tenon", ADJ_TEN_L), ("fixed tenon", FIX_TEN_L),
               ("adapter", ADAPT_L)):
    assert _l <= BED + 1e-9, (
        "%s is %.1f long -- over the %.1f square-bed limit, so it would need the "
        "diagonal and could not be plated with anything else" % (_n, _l, BED))

assert ADJ_TEN_L - ENGAGE <= ADJ_L + 1e-9, (
    "at its SHORTEST the adjust tenon buries %.1f but its mortise is only %.1f "
    "long -- it would bottom out before the leg is fully up"
    % (ADJ_TEN_L - ENGAGE, ADJ_L))
assert ADJ_N * ADJ_PITCH <= ADJ_TRAVEL + 1e-9, (
    "the hole ladder (%.1f) is longer than the travel the joint can give (%.1f)"
    % (ADJ_N * ADJ_PITCH, ADJ_TRAVEL))


# ── PRINT ORIENTATION (user) -- the record, declared once per part ─────────
# PRINT_UP is each part's build direction; the hole cutters read it, so a hole is
# shaped for the way its part actually prints. PRINT_ROT is the same fact as
# cadkit.step_export.print_pose wants it, for the per-part STEPs. The assert below
# makes the two unable to disagree.
_S2 = 1.0 / math.sqrt(2.0)
SLEEVE_UP = (0.0, -1.0, 0.0)       # both sleeves: the bed is the +Y face (at Y 65.95
                                   # on this station) and the part builds toward -Y,
                                   # so the BUTTON face is the top (user)
ADAPTER_UP = (0.0, 1.0, 0.0)       # the adapter the OTHER way up, -Y -> +Y (user):
                                   # button face down. Built like the sleeves, its
                                   # latch pocket's outer skin was a 5.3 mm flat
                                   # bridge over the hook; this way up it is a floor.
                                   # (The sleeve's pad recess is the mirror case --
                                   # it wants the button face UP -- which is why the
                                   # two differ.)
TENON_UP = (-_S2, -_S2, 0.0)       # both floating tenons: +X+Y -> -X-Y, lying on
                                   # the section's own 45 flat that faces +X+Y
SLIDER_UP = (1.0, 0.0, 0.0)        # the latch slider builds -X -> +X (user): its -X
                                   # side is the bed. Every Z- and Y-facing face then
                                   # stands vertical -- the retention ledge, the pad's
                                   # top edge, the flush thumb face -- and the body's and
                                   # hook's V flanks lean out as 45-degree eaves off it.
                                   # Two things make it rest on the bed properly: the
                                   # pad sits +X of centre so its -X edge lands there
                                   # with the body (leg_latch.PAD_X), and the neck has a
                                   # hidden notch so it grows off body and plate
                                   # (leg_latch._neck_support). Checked with a slicer-
                                   # style LAYER-SUPPORT test, not just face angles: a
                                   # face-angle probe passed an earlier diagonal build
                                   # whose pad wing hung from its tip in mid-air.
BAR_FRAME_UP = (0.0, 0.0, 1.0)     # the pedal bar's yoke: ring on the bed, pad and
                                   # spring lugs growing up off it (src.bar_latch)
BAR_COLLAR_UP = (0.0, 0.0, -1.0)   # its collar prints MOUTH FACE DOWN: every latch
                                   # cavity opens at its underside, the top of the print
PRINT_UP = {"adjust_sleeve": SLEEVE_UP, "fixed_sleeve": SLEEVE_UP,
            "body_adapter": ADAPTER_UP,
            "adjust_tenon": TENON_UP, "fixed_tenon": TENON_UP,
            "latch_slider": SLIDER_UP, "bar_latch_frame": BAR_FRAME_UP,
            "bar_latch_collar": BAR_COLLAR_UP}
PRINT_ROT = {"adjust_sleeve": ((1, 0, 0), -90), "fixed_sleeve": ((1, 0, 0), -90),
             "body_adapter": ((1, 0, 0), 90),
             "adjust_tenon": ((-1, 1, 0), 90), "fixed_tenon": ((-1, 1, 0), 90),
             "latch_slider": ((0, 1, 0), -90), "bar_latch_frame": ((1, 0, 0), 0),
             "bar_latch_collar": ((1, 0, 0), 180)}


def _rotated(v, axis, deg):
    """v rotated about `axis` by `deg` (Rodrigues) -- to check PRINT_ROT."""
    k = [c / math.sqrt(sum(q * q for q in axis)) for c in axis]
    th = math.radians(deg)
    kv = sum(k[i] * v[i] for i in range(3))
    kx = (k[1] * v[2] - k[2] * v[1], k[2] * v[0] - k[0] * v[2],
          k[0] * v[1] - k[1] * v[0])
    return tuple(v[i] * math.cos(th) + kx[i] * math.sin(th)
                 + k[i] * kv * (1 - math.cos(th)) for i in range(3))


for _n, _up in PRINT_UP.items():
    _z = _rotated(_up, *PRINT_ROT[_n])
    assert abs(_z[2] - 1.0) < 1e-9, (
        "%s: PRINT_ROT does not stand the part on the bed PRINT_UP says it "
        "prints from (build axis lands on %s, not +Z)" % (_n, _z))


def latch_slider():
    """The body latch's slider -- built in leg_latch, printed with the leg."""
    from . import leg_latch as LL
    return LL.slider()


def bar_latch_frame():
    """The pedal bar's yoke latch -- built in bar_latch, living in the bar's tower."""
    from . import bar_latch as BL
    return BL.frame(Z_BAR_MOUTH)


def _bar_trrs_top():
    """The bar's TRRS jack way top in world z (the bar is posed from its mouth)."""
    from . import pedal_bar as PB
    return Z_BAR_MOUTH - (PB.TOWER_TOP - PB.TRRS_WAY_TOP)


def bar_latch_collar():
    """The pedal bar latch's COLLAR -- printed on its own, screwed onto the bar's tower."""
    from . import bar_latch as BL
    return BL.collar(Z_BAR_MOUTH, _bar_trrs_top())


PARTS = {
    "adjust_sleeve": adjust_sleeve,
    "adjust_tenon": adjust_tenon,
    "fixed_sleeve": fixed_sleeve,
    "fixed_tenon": fixed_tenon,
    "body_adapter": body_adapter,
    "latch_slider": latch_slider,
    "bar_latch_frame": bar_latch_frame,
    "bar_latch_collar": bar_latch_collar,
}


# ── CONTEXT (not printed parts of this module) ──────────────────────────────
def pedal_bar_context():
    """The REAL pedal bar, hanging off the adjust tenon.

    NOT a stand-in: this is the actual src.pedal_bar geometry -- the same fused
    pieces the printer gets, via build._PB_bar -- so the joint is read against
    real walls rather than a box.

    The bar is modelled with z0 at its plate bottom and normally lands in the
    instrument via build.PEDAL_LIFT_DZ, which is keyed to the OLD leg stack and
    knows nothing about this chain. Here it is placed the other way round: the
    bar's mortise MOUTH (pedal_bar.TOWER_TOP) goes on Z_BAR_MOUTH, so moving the
    height setting MOVES THE BAR, as it must. The tenon then runs ENGAGE past the
    mouth and bottoms on the mortise's blind floor -- the fixed, repeatable
    install stop for this joint (user: the height adjusts at the OTHER end of
    this tenon, not here).
    """
    from . import build as BUILD
    from . import pedal_bar as PB

    parts = []
    for n, wp in PB.assembly_parts():
        if n in PB.PIECE_SPAN:
            wp = BUILD._PB_bar(n)       # the fused piece, pedal housings and all
        parts.append((n, wp))
    # The pedal MECHANISMS are deliberately not here (user: "we don't need all
    # the pedals and springs"). The housings still are -- they are FUSED INTO the
    # bar pieces, so they arrive with the real geometry rather than as a demo.
    dz = Z_BAR_MOUTH - PB.TOWER_TOP
    return [(n, wp.translate((0, 0, dz))) for n, wp in parts]


def leg_parts():
    """The leg and its two latches, every part where it goes -- without the pedal bar.
    What build.py places (it places the bar itself, lifted to where this leg puts it).

    TWO RULES the render caught (user):
      * THE ADAPTER SITS UNDER THE INSTRUMENT: its top face is Z_TOP, the chassis
        underside, and it hangs down from there.
      * ONLY THE HEIGHT-ADJUST TENON IS EXPOSED. The fixed tenon is a fixed
        length, so there is no reason to see it: the two sleeves BUTT and it is
        fully encased, straddling the seam. The adjust tenon is exposed BY DESIGN
        -- its exposed length IS the height setting.
    """
    from . import leg_latch as LL
    from . import bar_latch as BL
    out = [("body_adapter_0", body_adapter()),      # corner 0; build adds 1..3
           ("fixed_sleeve", fixed_sleeve()),
           ("fixed_tenon", fixed_tenon()),
           ("adjust_sleeve", adjust_sleeve()),
           ("adjust_tenon", adjust_tenon()),
           # the body latch, drawn AT REST (hook out, button flush)
           ("leg_latch_slider", LL.slider()),
           ("leg_latch_spring", LL.spring()),
           # the pedal bar latch, AT REST (hook in, pad flush)
           ("bar_latch_frame", BL.frame(Z_BAR_MOUTH)),
           ("bar_latch_collar", BL.collar(Z_BAR_MOUTH, _bar_trrs_top()))]
    out += [("bar_latch_spring_%d" % i, s) for i, s in enumerate(BL.springs(Z_BAR_MOUTH))]
    out += LG.lock_pin_dummies(LEG_X, LEG_Y, EGX, SYG, Z_TOP, 0)   # the leg's one screw
    return out


def assembly():
    """The leg, its latches and the real pedal bar hanging off it (the scratch view)."""
    return leg_parts() + pedal_bar_context()
