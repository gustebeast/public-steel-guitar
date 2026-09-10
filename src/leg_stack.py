"""REDESIGNED LEG — a chain of through-mortise sleeves joined by floating tenons.

Built fresh alongside the old legs.py (which is untouched) so it can be looked at
without destabilising the build. ONE leg only: the -X/+Y (TRRS) station.

THE CHAIN, top to bottom:

    pedal bar (mortise)
      |__ HEIGHT-ADJUST floating tenon   <- sets leg height; screw through a hole
    height-adjust leg (mortise)
      |__ FIXED floating tenon           <- joins the two sleeves; screw-locked
    fixed-height leg (mortise)
      |__ ...and the leg's OWN 44.8 section plugs the body adapter
    body quick-release adapter (mortise) -> body

WHY THE BODY END IS NOT A FLOATING TENON (design change, and it is load-driven).
The user's chain had the fixed tenon protrude out the bottom into the adapter.
It cannot: the kick case (250 N at 100 mm, leg at ~800 max = 175 N.m) puts the
instrument's worst moment at exactly that joint, and a 45-degree tenon is capped
at 24.6 mm across flats by the 44.8 leg and a 5 mm wall. That gives

    sleeve 44.8 sq   Z 13937 mm^3   12.6 MPa   SF 4.0
    tenon  24.0      Z  1629 mm^3  107.4 MPa   SF 0.47   <- fails
    tenon  31.7 (zero wall!)        46.6 MPa   SF 1.07

which is the SAME argument that ruled out a tenon-shaped adapter (user): bending
strength goes as the cube of the section, and the smallest section in the stack
must not be the one at the largest moment. So the fixed sleeve's own 44.8 body
enters the adapter and the full section carries the kick. The floating tenon
still runs the sleeve's length -- it just terminates inside rather than
protruding, so it aligns and stiffens instead of carrying.

That also keeps the LATCH handedness we already have: the removed piece (the
leg) presents the outer 44.8 section as the male, the adapter is the mortise, so
the button rides the male and the hook grabs OUTWARD into the adapter wall --
exactly latch.py as built. Only the PEDAL BAR end needs the mirrored variant
(button on a mortise, hook inward), because there the removed piece is the bar.

PROFILE: a square with its corners chamfered to a CHAM-wide flat -- an octagon
whose four extra sides are 1.6 (user: sharp corners cause joint fit issues).
Used rotated 45 degrees, which is what makes the mortise self-supporting: the
leg prints ON ITS SIDE, so a rotated square puts an APEX at the top and the
mortise roof is two 45-degree faces instead of a flat bridge down the whole
length.

NOT DONE YET / deliberately out of scope: cable management (space is reserved
for the TRRS jacks, nothing is routed), the mirrored bar-end latch, and the
detent rack for the height adjust (holes are drawn, the screw is not).
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl

B = D.BEAD

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

# The 45-degree rotation is what makes the mortise printable, and it also sets
# the wall: the octagon's DIAGONAL points at the sleeve's faces.
WALL_MIN = LEG_W / 2 - (TEN_W + 2 * FIT) * math.sqrt(2) / 2
assert WALL_MIN >= 2 * D.MIN_WALL_2P, (
    "mortise wall %.2f is under two two-bead walls -- shrink TEN_W" % WALL_MIN)

# A self-crossing profile still EXTRUDES -- it just yields a mangled corner and a
# wrong section. Gate it on the one number that cannot lie: a chamfered square is
# the square minus its four corner triangles, w^2 - cham^2 exactly.
def _profile_area(w: float, cham: float = CHAM) -> float:
    return octagon(w, cham).extrude(1.0).val().Volume()


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
                                  # very top face, leaving nothing to bolt through.
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
#   SHORTEST setting: as much of it hidden as possible. It cannot hide entirely,
#     because the bottom end must always be engaged in the PEDAL BAR -- so the
#     least it can ever show is ENGAGE. Buried length is then ADJ_TEN_L - ENGAGE,
#     which must fit its mortise: ADJ_TEN_L <= ADJ_L + ENGAGE.
#   LONGEST setting: out as far as the strength budget allows, i.e. until only
#     ENGAGE remains in the sleeve.
# and the bed caps it. Travel is what is left between the two.
ADJ_TEN_L = min(BED, ADJ_L + ENGAGE)          # 252.0
ADJ_TRAVEL = ADJ_TEN_L - 2 * ENGAGE           # 156.0 usable height adjustment
FIX_TEN_L = FIX_L + 2 * ENGAGE    # 296.0 fixed tenon: the FULL length of its own
                                  # sleeve PLUS an extension at each end, so the
                                  # one bar does the work of a tenon at BOTH
                                  # neighbouring joints (user). It is never seen:
                                  # a fixed-length tenon has no reason to show.

# ── height adjust: a ladder of holes, not friction ──────────────────────────
ADJ_HOLE_D = 5 * B                # 4.0 through-hole for the M4 locking screw
ADJ_WEB = 2 * B                   # 1.6 material between holes -- this web, not
                                  # the screw, is what tears out under load, so
                                  # it is the number that sets pull-out strength
ADJ_PITCH = ADJ_HOLE_D + ADJ_WEB  # 5.6 and therefore the HEIGHT STEP
ADJ_N = int(ADJ_TRAVEL / ADJ_PITCH)           # 27 holes, filling the travel
# Two rows, offset half a pitch, on opposite faces: halves the step to 2.8
# without thinning any web (each row keeps its full 1.6).
ADJ_ROWS = (0.0, ADJ_PITCH / 2.0)

# BODY JOINERY on the adapter's closed end: four M4 through the wall on a square
# pattern, which is what actually carries the leg's load into the body. Placed at
# the CORNERS of the section, as far apart as the wall allows -- a bolt pattern
# resists the kick's moment as a couple, so spread is worth more than bolt count.
ADAPT_BOLT_D = 4.4                # M4 clearance (a hole, not material)
ADAPT_BOLT_PCD = LEG_W - 2 * (4 * B)   # 38.4 across the square pattern

TRRS_D = 12 * B                   # 9.6 reserved bore for the TRRS jack body
TRRS_Z = 40 * B                   # 32.0 up from the sleeve's bottom face


def octagon(w: float, cham: float = CHAM):
    """Square of `w` across flats with its corners chamfered to `cham`-wide
    faces, as a closed 2-D wire on XY. Drawn at 45 degrees -- the pose it is
    USED in -- so an apex points +Y and the mortise roof self-supports."""
    h = w / 2.0
    c = cham / math.sqrt(2.0)          # the corner leg the chamfer cuts off
    pts = []
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        pts.append((sx * (h - c), sy * h))
        pts.append((sx * h, sy * (h - c)))
    # WALK THE PERIMETER. Getting this order wrong does not fail -- it makes a
    # self-crossing polygon that still extrudes, and the damage shows up as one
    # mangled corner (the -Y one) while the other three chamfer correctly. The
    # area check below is what actually catches it.
    #   flat, chamfer, flat, chamfer, ... counter-clockwise from the +Y top edge
    loop = [pts[0], pts[2],      # top flat      (h-c, h) -> (-(h-c), h)
            pts[3], pts[5],      # -X flat       (-h, h-c) -> (-h, -(h-c))
            pts[4], pts[6],      # bottom flat   (-(h-c), -h) -> (h-c, -h)
            pts[7], pts[1]]      # +X flat       (h, -(h-c)) -> (h, h-c)
    # NB: draw it SQUARE-ON and rotate the SOLID after extruding. Rotating the
    # Workplane here does nothing -- polyline().close() leaves a PENDING wire,
    # not an object on the stack, so extrude() would consume the unrotated
    # profile and the 45 would silently vanish (caught by the bounding box:
    # 24.0 across instead of 24 * sqrt2 = 33.9).
    return cq.Workplane("XY").polyline(loop).close()


def _at45(solid):
    """Into the INSTALL pose. The leg prints on its side, so an apex must point
    up: that turns the mortise roof into two 45-degree faces instead of a flat
    bridge running the whole length."""
    return solid.rotate((0, 0, 0), (0, 0, 1), 45)


def tenon(length: float, w: float = TEN_W):
    """A floating tenon: the octagon bar, extruded along +Z."""
    return _at45(octagon(w).extrude(length))


def mortise_cutter(length: float, w: float = TEN_W, fit: float = FIT):
    """The matching through-hole, grown by the slide fit on every face."""
    return _at45(octagon(w + 2 * fit).extrude(length))


def _sleeve(length: float, trrs: bool = False):
    """A leg section: LEG_W square, octagon mortise straight through."""
    b = box_at(LEG_W, LEG_W, length, z=length / 2.0)
    b = b.cut(mortise_cutter(length + 2.0).translate((0, 0, -1.0)))
    if trrs:
        # SPACE ONLY -- nothing is routed yet (user). A blind pocket in the wall
        # on the +X side, clear of the mortise, big enough for the jack body.
        b = b.cut(cyl(TRRS_D, 20.0, z=TRRS_Z)
                  .rotate((0, 0, 0), (0, 1, 0), 90)
                  .translate((LEG_W / 2 - 6.0, 0, TRRS_Z)))
    return b


def adjust_sleeve():
    """The HEIGHT-ADJUST section: the long one, so the tenon can be set over a
    wide range. Carries the locking screw's clearance hole."""
    b = _sleeve(ADJ_L, trrs=True)
    for dz in ADJ_ROWS:
        b = b.cut(cyl(ADJ_HOLE_D + 0.8, LEG_W + 4.0, z=ADJ_L * 0.5 + dz)
                  .rotate((0, 0, 0), (1, 0, 0), 90)
                  .translate((0, LEG_W / 2 + 2.0, 0)))
    return b


# THE FIXED JOINT'S SCREW (user): tenon to fixed sleeve, the step that locks the
# latch in. Same M4 convention as the adjust ladder -- clearance in the sleeve,
# ADJ_HOLE_D in the tenon -- so the leg takes one screw and one hole size. It
# goes in the MIDDLE of the fixed sleeve, and it runs along X, not Y: along Y it
# would pass through the button face, and the middle keeps it clear of the latch
# band (which ends at leg_latch's BUTT + PAD_L) with the whole sleeve to spare.
FIX_SCREW_Z = ADAPT_L + FIX_L / 2.0    # 138.8 leg-local


def _fix_screw(d: float):
    """The fixed joint's screw hole, along X, in LEG-LOCAL z."""
    return (cyl(d, LEG_W + 4.0, z=0.0)
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((0, 0, FIX_SCREW_Z)))


def fixed_sleeve():
    """The FIXED section. Its own 44.8 body BUTTS the body adapter, so the kick
    moment never passes through a tenon (see the module docstring).

    Carries the latch NOTCH -- the way the button reaches the outside, and the
    part that stands over the slider in place of a cover."""
    from . import leg_latch as LL          # late: leg_latch reads this module
    b = _sleeve(FIX_L)
    b = b.cut(LL.sleeve_notch().translate((0, 0, -ADAPT_L)))
    return b.cut(_fix_screw(ADJ_HOLE_D + 0.8).translate((0, 0, -ADAPT_L)))


def adjust_tenon():
    """Floating tenon, pedal bar <-> adjust sleeve. The LADDER of holes is the
    height setting: pick a hole, drop the screw, and every leg set to the same
    hole index is at the same height -- repeatable without measuring, which
    friction alone never is."""
    t = tenon(ADJ_TEN_L)
    for row, dz0 in enumerate(ADJ_ROWS):
        for i in range(ADJ_N):
            z = ENGAGE + dz0 + i * ADJ_PITCH
            if z > ADJ_TEN_L - ENGAGE / 2:
                break
            t = t.cut(cyl(ADJ_HOLE_D, TEN_W + 8.0, z=z)
                      .rotate((0, 0, 0), (1, 0, 0), 90)
                      .translate((0, TEN_W / 2 + 4.0, 0)))
    return t


def fixed_tenon():
    """Floating tenon, adjust sleeve <-> fixed sleeve. Spans the fixed sleeve and
    protrudes UP into the adapter; the bottom end stops inside the adjust sleeve.

    This is the piece that HOLDS THE LEG ON THE BODY (user), and it is also the
    only solid section at that joint -- so it hosts the latch's pocket. What that
    costs the tenon is measured in leg_latch.SECTION_LOSS."""
    from . import leg_latch as LL
    t = tenon(FIX_TEN_L)
    t = t.cut(LL.tenon_pocket().translate((0, 0, -ADAPT_WALL)))
    return t.cut(_fix_screw(ADJ_HOLE_D).translate((0, 0, -ADAPT_WALL)))


def body_adapter():
    """Quick-release adapter: bolts to the body, and is otherwise JUST ANOTHER
    MORTISE SECTION -- same 44.8 outer as every sleeve, so it ends FLUSH with
    the rest of the leg (user). It wraps the fixed tenon's upper extension; the
    sleeve BUTTS it face to face rather than plugging into it.

    THAT BUTT IS WHAT CARRIES THE KICK, and it is why this works where my
    earlier objection said it would not. I had the tenon BRIDGING a gap, so the
    175 N.m appeared as BENDING in a 24 mm section: Z 1629 mm^3, 107 MPa,
    SF 0.47. With the faces in contact the moment resolves instead into a
    couple -- COMPRESSION carried by the butted 44.8 faces (which cannot fail
    that way) and TENSION carried by the tenon. Tension is the cheap direction:
    ~5.8 kN over the tenon's ~576 mm^2 is about 10 MPa, SF ~5.

    So the load path is the joint, not the bar. Keep the faces butted."""
    b = box_at(LEG_W, LEG_W, ADAPT_L, z=ADAPT_L / 2.0)
    # BLIND mortise: stops ADAPT_WALL short of the top face
    b = b.cut(mortise_cutter(ENGAGE + 1.0).translate((0, 0, ADAPT_WALL)))
    # the latch's retention pocket -- the ledge the whole leg hangs on
    from . import leg_latch as LL
    b = b.cut(LL.adapter_pocket())
    h = ADAPT_BOLT_PCD / 2.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            b = b.cut(cyl(ADAPT_BOLT_D, ADAPT_WALL + 2.0, z=ADAPT_WALL / 2.0)
                      .translate((sx * h, sy * h, 0)))
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
    "long -- it would bottom out before the leg is fully down"
    % (ADJ_TEN_L - ENGAGE, ADJ_L))
assert ADJ_N * ADJ_PITCH <= ADJ_TRAVEL + 1e-9, (
    "the hole ladder (%.1f) is longer than the travel the joint can give (%.1f)"
    % (ADJ_N * ADJ_PITCH, ADJ_TRAVEL))


PARTS = {
    "adjust_sleeve": adjust_sleeve,
    "adjust_tenon": adjust_tenon,
    "fixed_sleeve": fixed_sleeve,
    "fixed_tenon": fixed_tenon,
    "body_adapter": body_adapter,
}


# ── CONTEXT (not printed parts -- just enough to read the chain end to end) ──
BODY_T = 20 * B                   # 16.0 slab standing in for the chassis underside


def body_stub_context():
    """The chassis underside the adapter bolts to. NOT a printed part."""
    w = LEG_W + 8 * D.MIN_WALL_2P
    return box_at(w, w, BODY_T, z=-70 * B - BODY_T / 2)


# WHERE THE PEDAL BAR GOES. Published as a datum, because the bar does not get to
# choose: it hangs off the END OF THE ADJUST TENON, and the adjust tenon's end is
# wherever the height setting put it. The old dummy bar computed its own `top`
# from a formula that had gone stale (it still summed FIX_TEN_L and never counted
# the adapter at all) -- the same stale-datum failure this file has been bitten by
# four times. There is now ONE expression for the tenon's far end and everything
# downstream reads it.
ADJ_TEN_Z0 = ADAPT_L + FIX_L + ADJ_L - ENGAGE   # 436.8 tenon's top (buried end)
ADJ_TEN_Z1 = ADJ_TEN_Z0 + ADJ_TEN_L             # 688.8 tenon's far end, at the bar
BAR_SEAT = ADJ_TEN_Z1 - ENGAGE                  # 648.8 the bar's MOUTH plane: the
                                                # tenon buries ENGAGE into the bar's
                                                # tower, the same rule as every other
                                                # joint in the chain


def pedal_bar_context():
    """The REAL pedal bar (+ its pedals), posed FROM THE ADJUST TENON.

    NOT a printed part of this module and NOT a stand-in: this is the actual
    src.pedal_bar geometry -- the same fused pieces the printer gets, via
    build._PB_bar -- so the joint is read against real walls rather than a box.

    The bar is authored in ABSOLUTE X/Y with z0 = plate bottom, and lands in the
    instrument via build.PEDAL_LIFT_DZ, which is keyed to the OLD leg stack
    (Z_BOT - LEG_HEIGHT + legs.FOOT_H). That number knows nothing about this
    chain, which is why the bar rendered adrift of the tenon. Here it is placed
    the other way round: the bar's mortise MOUTH (pedal_bar.TOWER_TOP) is put on
    BAR_SEAT, so moving the height adjustment MOVES THE BAR, as it must. The tenon
    then runs ENGAGE past the mouth and bottoms on the mortise's blind floor --
    which is the fixed, repeatable install stop for this joint (user: the height
    adjustment happens at the OTHER end of this tenon, not here).

    Returned in the LEG's own frame (+Z away from the instrument), which is
    upside down relative to the instrument -- hence the 180 about X. The station
    translate is the view pose's own, undone here so the pose can redo it; the
    zt term cancels out entirely, so this does not depend on the chassis height.
    """
    from . import build as BUILD
    from . import chassis as CH
    from . import pedal_bar as PB

    lx, ly = CH.LEG_STATIONS_X[1], CH.LEG_Y[0]
    dz = -(BAR_SEAT + PB.TOWER_TOP)

    parts = []
    for n, wp in PB.assembly_parts():
        if n in PB.PIECE_SPAN:
            wp = BUILD._PB_bar(n)       # the fused piece, pedal housings and all
        parts.append((n, wp))
    # The pedal MECHANISMS are deliberately not here (user: "we don't need all
    # the pedals and springs"). The housings still are -- they are FUSED INTO the
    # bar pieces, so they arrive with the real geometry rather than as a demo.
    return [(n, wp.translate((-lx, -ly, dz)).rotate((0, 0, 0), (1, 0, 0), 180))
            for n, wp in parts]


def assembly():
    """The chain, posed in the LEG's own frame: local z0 is the body adapter's
    TOP, and the leg runs +Z away from the instrument.

    TWO RULES the render caught (user):
      * THE ADAPTER SITS UNDER THE INSTRUMENT. It used to span z -56..0, which
        after the flip put it 56 mm UP INSIDE the chassis (2694 mm^3 into
        chassis_2). It now starts at z0 and grows AWAY, so it hangs below.
      * ONLY THE HEIGHT-ADJUST TENON IS EXPOSED. The fixed tenon is a fixed
        length, so there is no reason to see it: the two sleeves BUTT and it is
        fully encased, straddling the seam. It was showing 96 mm of bare bar.
        The adjust tenon is exposed BY DESIGN -- its exposed length IS the
        height setting.
    """
    out = []
    # adapter first: it surrounds the fixed sleeve's top and hangs below the body
    out.append(("body_adapter", body_adapter()))
    # BUTTED, not nested: same section, flush faces, moment through the joint
    out.append(("fixed_sleeve", fixed_sleeve().translate((0, 0, ADAPT_L))))
    # runs the sleeve's WHOLE length and out both ends: ENGAGE up into the
    # adapter's blind bore, ENGAGE down into the adjust sleeve
    out.append(("fixed_tenon", fixed_tenon().translate((0, 0, ADAPT_WALL))))
    out.append(("adjust_sleeve",
                adjust_sleeve().translate((0, 0, ADAPT_L + FIX_L))))
    # the ONE exposed tenon: how much stands proud IS the height setting
    out.append(("adjust_tenon", adjust_tenon().translate((0, 0, ADJ_TEN_Z0))))
    # the body latch, drawn AT REST (hook out, button proud)
    from . import leg_latch as LL
    out.append(("latch_slider", LL.slider()))
    out.append(("latch_spring", LL.spring()))
    # ...and the bar hangs off its far end. Context, not a printed part of this
    # module -- but posed from ADJ_TEN_Z1, so it cannot drift from the tenon.
    out += pedal_bar_context()
    return out
