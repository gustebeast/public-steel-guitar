"""Nut block geometry (×1) — keyhead string termination. PETG-GF (clamps bear on it).

THE WRAP CAPSTAN (user). The string does not go straight from the break edge to a
clamp any more. It winds turns around a shared rod first, and the clamp behind it
only has to hold what the capstan leaves:

    bridge  ->  BREAK DOWEL  ->  UNDER THE WRAP ROD, up and round (n turns)  ->  CLAMP  ->  tail

THE WRAP IS TURNED OVER (user, 2026-10-31). The string used to land on the rod's top and go down the
-X side, and a stiff tip could not be got round under the rod: bench tests of every ramp and curve
failed, and the top panel closes the +X side whatever the endplate does. So the rod stands higher and
further -X, the string lands on its UNDERSIDE and wraps up the -X side, and the tip is fed by hand,
straight along X, through the gap between the rod and the panel, and grabbed on both sides. The
lanes run out through the -X face; the fingers hang on the floor alone (Z), with no wall or bar.

Capstan (Euler-Eytelwein), T = T0.e^-mu.theta, mu = 0.15 steel on steel:

    no wrap    147 N at the clamp  ->  490 N of clamp force  ->  39 MPa on plastic
    1.5 turns   36 N               ->  119 N
    3.5 turns    5 N               ->   18 N

That is the whole point of the scheme: the clamp was never the wrong mechanism, it
was being asked for 490 N. What is left at the tail is clamped by the string's SLIDING
INSERT, which presses the coil up against the rod (see THE SLIDING INSERT below).

NO ANVIL (user). A second Ø2 dowel used to sit under the tail so the screw pinched it
against STEEL rather than against the plastic floor. It existed for load that no longer
happens: at 46 N of clamp force the floor sees a fraction of what made the plain clamp
untenable, and the pocket it needed was the last real overhang in the part — a vertical
+X wall the -X -> +X build had to bridge, with no +X face to open toward the way the
break dowel's pocket has. Deleting it takes ten overhangs, ten pockets and a BOM line
with it, and leaves the part simpler rather than more complicated.

THE ROD IS THE BRIDGE AXLE'S OWN PART (user). The Ø8 x 100 precision shaft the +X
endplate carries its 688ZZ bearings on -- D.BRIDGE_AXLE_D and D.BRIDGE_AXLE_L, read
here rather than copied -- so both ends of the instrument buy ONE shaft SKU. Ø8 bends
the .070 at 18.2% outer-fibre strain (d/(D+d)), gentler than the Ø5 it replaced
(26.2%) and than a guitar tuner post. The move from Ø5 was paid for in X (ROD_X) and in
the block's -Y reach (Y_LO).

ONE ROD, NOT TEN POSTS (user). Ten vertical posts would let each wrap climb in Z,
where height is free. A shared rod along Y makes the wrap climb ACROSS THE STRINGS
instead, and there the budget is D.NUT_PITCH — 6.5 mm — which is what sets the turn
count. See _turns: it is not a taste parameter, it is the largest number of turns
whose coil still leaves a printable web to the next string.

WHICH WAY THE WRAPS MARCH IS THE DESIGN (user-driven, and it is worth the sentence).
Every wrap marches -Y, toward the THICKER neighbour. Marching the other way puts the
two fattest strings' coils into each other and string 10 ends up with 1.12 mm of web,
under the two-bead floor. Marching -Y instead lands the fattest coil — the .070's,
which needs 6.53 mm of rod — in the OPEN AIR outboard of the field where there is no
neighbour at all, and every web in the comb clears 1.6:

    WRAPS (3) wraps on every string (~2.93 turns from first touch) -> ~9.3 N left at
    the tail out of 147. Strings 1-7 keep a printed finger between their bays; 8-10
    share one open bay, where the rod's longest unsupported run is ~23.9 mm -- ~26 MPa
    in the Ø8. See bays().

Local frame: X=0 at the break edge, +X toward the bridge (speaking length); Z=0 at
the string-top plane (= STRING_Z global); body hangs -Z to the deck plane.

PRINTS -X -> +X. The -X end face is the bed. Every bore here runs PERPENDICULAR to
that axis — the rod along Y, the screws and inserts along Z — so each is a
"horizontal" hole in the print sense and takes cadkit's 45° teardrop; without it they
print as sagging round ceilings and come out oval.

This is FUSED into the keyhead endplate (one printed piece — keyhead_endplate.py
unions it in); it stays its own module for the per-string layout.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_y
from cadkit.fitted_joint import LAYER
from cadkit.holes import teardrop_hole

PRINT_UP = (1.0, 0.0, 0.0)                      # build axis: the -X face is the bed

# ── hardware ───────────────────────────────────────────────────────────────
PIN_D    = D.NUT_PIN_D                          # Ø4 break dowel (one per string)
PIN_L    = D.NUT_PIN_L

ROD_D = D.BRIDGE_AXLE_D                         # Ø8 -- the bridge axle's own shaft (user)
ROD_FIT = 0.4                                   # the rod is LOCATED, not gripped: the wraps
                                                # load it -X and the comb takes that; it only
                                                # has to slide in through 10 fingers at once
ROD_BORE = ROD_D + ROD_FIT

# ── X layout (local frame) ─────────────────────────────────────────────────
# The prism runs from X_FRONT, flush with the endplate's +X face, back to X_BACK, the -X
# bed face. X_BACK and KEYHEAD_W are defined further down. The chassis reads them.
#
# The growth is all -X, AWAY FROM THE STRINGS: X_FRONT and the break edge at X=0 do not
# move, so the scale length is untouched and the bridge stays exactly where it is.
X_FRONT = D.KEYHEAD_PX_BUF                      # +2.4: +X lip, reclaimed from 4.0 -- see
                                                # dimensions.KEYHEAD_PX_BUF for the walk
# THE DOWELS SIT AS FAR +X AS 1.6 OF MATERIAL ALLOWS (user). Derived, not chosen: the
# bore's +X wall stands DOWEL_KEEP back from the block's front face, so if the front
# moves or the clearance changes the dowels follow instead of silently thinning that
# wall. At the old DOWEL_X = 0 there was only 1.25 of material there -- the 2.4 front
# buffer was sized against the OLD Ø2.8 seat, and the Ø2.30 bore left less behind it
# than intended.
# THE DOWEL IS SET BY THE INSERT THAT CARRIES IT, not by block material +X of it.
# DOWEL_KEEP used to reserve BLOCK behind the bore; there is no block there any more
# (see dimensions.KEYHEAD_PX_BUF), so what stands +X of the dowel is the INSERT's own
# wall, and the dowel sits that far back from the face.
DOWEL_KEEP = D.MIN_WALL                         # 0.8 of INSERT wall +X of the cradle
DOWEL_X = X_FRONT - DOWEL_KEEP - (PIN_D + 0.3) / 2
# THE ROD STANDS AS HIGH AND AS FAR -X AS THREE THINGS AGREE (user: under the string line, wrapping
# up). HIGHER opens the gap over the panel the tip is fed through but flattens the break over the
# dowel; further -X eases the break and clears a bar at fret 0, whose circle the rod's three-bead
# lid has to stay outside, and costs nothing now the -X wall has gone. At x -8 the lid stands in the
# bar. Here: 20.4-20.6 deg, 4.8 of gap, 1.0 of air to the bar.
ROD_X   = -16 * D.BEAD                          # -12.8 rod centre
ROD_Z   = -1 * D.BEAD                           # -0.8
_G_MAX  = max(D.STRING_GAUGE)
# THE INSERT'S TRAVEL IS SIZED FOR THE ENVELOPE, not the demo set: a heavier string must still
# thread and clamp without a reprint (D.STRING_GAUGE_MAX).
G_ENVELOPE = max(_G_MAX, D.STRING_GAUGE_MAX)


def _break_at(rod_z: float, g: float) -> float:
    """True tangent angle, in degrees, down off the dowel to the UNDERSIDE of a rod at rod_z."""
    hr = ROD_D / 2 + g / 2
    dx, dz = DOWEL_X - ROD_X, -g / 2 - rod_z
    return math.degrees(math.atan2(dz, dx)) + math.degrees(math.asin(hr / math.hypot(dx, dz)))


# THE BAR HAS TO CLEAR IT. A round bar resting on the strings at fret 0 is a circle of
# BAR_R centred BAR_R above the string plane over the dowel; the rod must stay a margin
# outside it. Tested circle-to-circle. BLOCK_TOP's outline is held to the same circle below.
BAR_R   = 19.0 / 2                              # a typical steel bar
BAR_CLR_MIN = 0.8
_BAR_CLR = math.hypot(DOWEL_X - ROD_X, BAR_R - ROD_Z) - BAR_R - ROD_D / 2
assert _BAR_CLR >= BAR_CLR_MIN, (
    f"the rod (O{ROD_D} at x {ROD_X:+.2f}, z {ROD_Z:+.2f}) comes within {_BAR_CLR:.2f} of a "
    f"bar resting at fret 0 -- the first centimetre could not be barred")

# ── Z extent ───────────────────────────────────────────────────────────────
# NUT_TOP covers the rod with a three-bead lid. +X of the rod the top falls to FRONT_TOP, the old
# block's height, under the bar (see BLOCK_TOP, once X_BACK exists): the +X opening stays as it was
# (user).
NUT_TOP  = ROD_Z + ROD_BORE / 2 + 3 * D.BEAD     # a three-bead lid over the rod (user: two printed badly)
FRONT_TOP = -1.72                                # the block's +X end, as it stood
NUT_BASE = D.DECK_TOP_Z - D.STRING_Z             # prism base sits on the deck plane


def _touch_angle_g(g: float) -> float:
    """Angle about the rod axis (in the XZ plane, from +X) at which string i first
    TOUCHES the wrap circle, coming down off its dowel. The LOWER of the two tangents,
    because the string comes in under the rod.

    THE ONE PLACE THIS IS COMPUTED. The turn count, the drawn string path and the coil's
    start phase all read it; when build.py owned a second copy the straight run and the
    coil disagreed and left a visible gap in the wrap."""
    hr = ROD_D / 2 + g / 2                       # the string's centre-path radius
    dx, dz = DOWEL_X - ROD_X, -g / 2 - ROD_Z     # rod axis -> dowel (the rod sits BELOW)
    return math.atan2(dz, dx) - math.acos(hr / math.hypot(dx, dz))


def touch_angle(i: int) -> float:
    """_touch_angle_g at string i's own gauge. The core takes ANY gauge so the outermost
    insert can be sized for a string heavier than the demo set (SKU C)."""
    return _touch_angle_g(D.STRING_GAUGE[i])


WRAP_F   = 1.05                                 # axial rise per turn, as a multiple of the
                                                # string's own diameter: the turns lie all but
                                                # touching. They must NOT cross -- under tension
                                                # a string crossing itself can cut itself in two
LANE_CLR = 0.5                                  # air each side of a coil, before its comb web
# ── HOW MANY TURNS: set by a Y BUDGET, and TWO INSERT SKUS (user) ──────────
# The wrap count used to be one number for all ten -- three string widths of clamp,
# everywhere. That is gauge-free in the RATIO but not in the millimetres: at 2.94 turns
# string 1 spent 1.16 mm of its 6.5 pitch and string 10 spent 5.43. The thin strings were
# leaving most of their lane unused while the thick ones were overrunning theirs, and it
# was the overrun at the bass that merged the bays and orphaned the walls between the
# insert pockets.
#
# So the budget is stated in Y and the turns follow from it: EVERY STRING TAKES AS MANY
# WHOLE WRAPS AS FIT ITS LANE, never fewer than _K_MIN. That is what collapses the insert
# from ten designs to two, because the clamp lobe is then sized to the LANE (a fixed
# window) rather than to the coil, and a fixed window is the same shape on every string.
#
# TWO ZONES, THREE SKUS (SKU C is string 10 on its own -- see SKU_C):
#
#   SKU A, strings 1..N_FINGERED -- each keeps a printed FINGER of MIN_WALL_2P to its
#       neighbour, so the rod is held at every one of those stations. The lane is the
#       pitch less that finger, and the coil has to fit inside it.
#
#   SKU B, the rest -- they give the fingers up and share ONE open bay. Their coils then
#       only have to clear each OTHER (COIL_CLR of air, not a wall), which is what lets
#       the bass keep three wraps instead of being forced down to two. Their inserts are
#       a pitch wide, ABUT one another, and are located by the stack rather than by walls
#       that could not be supported anyway.
#
# WHY THE ZONES FALL WHERE THEY DO: a finger costs 1.6 mm of the 6.5 pitch, and at the
# bass a three-wrap coil needs more than the 4.9 that leaves. Strings 8-10 are the ones
# that cannot pay it. The cost is the rod's longest unsupported run, ~23.9 mm: ~26 MPa in
# the Ø8 shaft, against the 250 MPa this module asserts.
N_FINGERED = 7                                  # s1..s7 keep their fingers
CLAMP_WIDTHS = 3.0                              # the GUARANTEE, not the target: no string
                                                # gets less clamp than this many string
                                                # widths (see _K_MIN, which delivers it)
COIL_CLR = 0.2                                  # coil-to-coil air where there is NO wall
                                                # between them (SKU B's shared bay). A
                                                # coil beside a PRINTED finger still gets
                                                # LANE_CLR: it has to clear a wall whose
                                                # position carries print tolerance, not
                                                # just another wire.
# SKU A's lane, as a window either side of the string's own Y. Its +Y edge clears the
# fattest coil in the zone; its -Y edge is then whatever leaves the finger exactly.
LANE_HI = max(D.STRING_GAUGE[:N_FINGERED]) / 2 + LANE_CLR
LANE_LO = -(D.NUT_PITCH - D.MIN_WALL_2P - LANE_HI)
# WHERE THE TAIL LEAVES: at the bottom of the rod, heading -X (-90 deg), level along the insert's
# flat and out through the lane. It lies where the clamp is, and the wrap's whole turns land it there
# from the touch, about 20 deg round, on every string.
EXIT_DEG = -90.0

# THE TAIL HAS TO LEAVE ON THE EXIT TANGENT, which quantises the turns: the coil enters at
# touch_angle (set by the break geometry and the gauge) and must sweep, ANGLE FALLING (-X side up,
# over, +X side down), to EXIT_DEG less a whole number of turns.
def _sweep0_g(g: float) -> float:
    """Turns from where a string of gauge g touches the rod round to the exit tangent."""
    return ((_touch_angle_g(g) - math.radians(EXIT_DEG)) % (2 * math.pi)) / (2 * math.pi)


def _sweep0(i: int) -> float:
    """Turns from where the string touches the rod round to the exit tangent."""
    return _sweep0_g(D.STRING_GAUGE[i])


def _adv_at(i: int, k: int) -> float:
    """How far string i's coil would march with k whole turns above the entry sweep."""
    return (_sweep0(i) + k) * WRAP_F * D.STRING_GAUGE[i]


def _k_min(i: int) -> int:
    """Fewest whole turns that still deliver the CLAMP_WIDTHS guarantee.

    DERIVED, NOT A LITERAL, and that matters more than it looks: the count needed depends
    on the ENTRY SWEEP, which moved when the exit angle did. Carrying the tail on to 135
    deg left only 0.08 of a turn between touch and exit instead of 0.94, so a hard-coded
    floor of 2 quietly started delivering 2.13 widths instead of 3.04. Deriving it from
    CLAMP_WIDTHS means the guarantee survives anyone moving EXIT_DEG again."""
    return _k_min_g(D.STRING_GAUGE[i])


def _k_min_g(g: float) -> int:
    """_k_min for any gauge g -- see outer_coil_lo."""
    need = 1.0 + (CLAMP_WIDTHS - 1.0) / WRAP_F
    return max(1, math.ceil(need - _sweep0_g(g) - 1e-9))


def outer_coil_lo(g: float) -> float:
    """-Y edge of the OUTERMOST string's coil if it carried gauge g. That string is held at
    _K_MIN (see _adv_cap), so its coil marches (entry sweep + _K_MIN) * WRAP_F * g from its
    own Y, and its last turn reaches half a gauge past that. What SKU C is sized from."""
    i = D.N_STRINGS - 1
    return D.nut_y(i) - (_sweep0_g(g) + _k_min_g(g)) * WRAP_F * g - g / 2


def _adv_cap(i: int) -> float:
    """The most Y string i's coil may take.

    SKU A: whatever fits the lane, which already has the finger subtracted.
    SKU B: the pitch, less both half-gauges and the air between two bare coils -- there is
    no wall to keep, so the only thing the coil must clear is its neighbour's coil.
    THE OUTERMOST STRING is capped at _K_MIN even though nothing is outboard of it: it
    could take more, but every extra turn there pushes HW out and widens the instrument,
    which is a poor trade for a string that already has its three widths."""
    g = D.STRING_GAUGE[i]
    if i == D.N_STRINGS - 1:
        return _adv_at(i, _k_min(i))
    if i < N_FINGERED:
        return -LANE_LO - g / 2 - LANE_CLR
    return D.NUT_PITCH - g / 2 - D.STRING_GAUGE[i + 1] / 2 - 2 * COIL_CLR


def turns(i: int) -> float:
    """THE LANE'S CAPACITY for string i: the most WHOLE wraps it will take, never under _K_MIN,
    landing the tail on the exit tangent by construction. It SIZES THE PRINTED PARTS (the SKU A
    clamp lobe, the SKU B bay, the rod span), so an insert accepts anything from the recommended
    WRAPS up to this. What a player is told to wind -- and what the assembly draws -- is wraps().

    THE WHOLE COUNT IS NOT NEGOTIABLE, because the tail has to leave pointing at its
    channel. Sweeping forward the tangent at phi is (-sin phi, cos phi), so only one
    angle sends the tail where the channel is; everything else exits into the trough
    wall. The entry angle is set by the break geometry, so the turns are that sweep plus
    an integer -- and the integer is the only thing the Y budget gets to choose."""
    k = _k_min(i)
    while _adv_at(i, k + 1) <= _adv_cap(i) + 1e-9:
        k += 1
    return _sweep0(i) + k


_K_SHORT = [i for i in range(D.N_STRINGS)
            if _adv_at(i, _k_min(i)) > _adv_cap(i) + 1e-9]
assert not _K_SHORT, (
    "strings %s cannot fit even _k_min wraps in their lane, so the %.1f-string-width "
    "clamp guarantee is not met -- widen the lane or move them into SKU B"
    % ([i + 1 for i in _K_SHORT], CLAMP_WIDTHS))


# ── WHAT A PLAYER WINDS: 3 WRAPS ON EVERY STRING (user) ────────────────────────
# The capacity above fills each lane, which drew ~8 wraps on the thinnest strings. That was
# never the recommendation. The capstan divides the clamp's load by e^(2*pi*MU) = 2.57 per
# wrap: ~9.3 N at 3 (every string the same, well under the 60 N _WORST_RES allows), ~3.6 at 4,
# ~0.5 at 6 -- so past the first extra wrap the clamp barely notices, while each wrap costs
# ~27 mm of string and more winding at every restring. And strings 6, 7, 9 and 10 cannot fit a
# fourth, so 3 is the one count every slot takes. Still the entry sweep plus a WHOLE number of
# turns, so the tail leaves on its exit tangent; ~3.06 here, which is also each string's _K_MIN.
WRAPS = 3


def wraps(i: int) -> float:
    """Turns string i is wound with, as recommended and as drawn: the entry sweep plus the whole
    number of turns nearest WRAPS. Never under the clamp guarantee, never over the lane."""
    return _sweep0(i) + max(_k_min(i), round(WRAPS - _sweep0(i)))


_WRAPS_BAD = [i + 1 for i in range(D.N_STRINGS) if wraps(i) > turns(i) + 1e-9]
assert not _WRAPS_BAD, (
    f"strings {_WRAPS_BAD} cannot fit the recommended {WRAPS} wraps in their lane")


def exit_angle(i: int) -> float:
    """Where string i's tail leaves the rod -- EXIT_DEG, by construction, since turns()
    is built as the entry sweep plus a whole number of revolutions."""
    return touch_angle(i) - wraps(i) * 2 * math.pi


def exit_point(i: int):
    """(x, z) where string i's tail leaves the rod, in the block's local frame. THE ONE
    PLACE THIS IS COMPUTED -- build.py used to derive it from its own wrap radius, which
    differed from this one by 0.05 and left every tail starting inside its own coil."""
    a = exit_angle(i)
    hr = wrap_radius(i)
    return ROD_X + hr * math.cos(a), ROD_Z + hr * math.sin(a)


def tail_route(i: int):
    """The tail's route from the rod, as (x, z) points: level along the flat to its -X end, where it
    is cut. Where a tail finally goes is open (INSTALL_NOTES); it is drawn cut there."""
    x0, z0 = exit_point(i)
    return [(x0, z0), (INS_X0, z0)]


def exit_dir(i: int):
    """Unit (x, z) the tail is travelling as it leaves. The angle falls, so the tangent at
    phi is (sin phi, -cos phi) -- at EXIT_DEG -90 that is dead -X."""
    a = exit_angle(i)
    return math.sin(a), -math.cos(a)


_EXIT_ERR = max(abs((math.degrees(exit_angle(i)) - EXIT_DEG + 180.0) % 360.0 - 180.0)
                for i in range(D.N_STRINGS))
assert _EXIT_ERR <= 0.01, (
    f"a tail leaves {_EXIT_ERR:.2f} deg off the {EXIT_DEG:.0f} deg exit tangent -- "
    f"turns() is meant to make that exact, so the derivation has drifted")


MU = 0.15                                       # steel on steel, dry, deliberately pessimistic
STRING_T = 147.0                                # per-string tension the capstan is dividing


def _adv(i: int) -> float:
    """How far string i's coil marches along the rod (always -Y)."""
    return turns(i) * WRAP_F * D.STRING_GAUGE[i]


def residual(i: int) -> float:
    """Tension still left at the clamp after the wrap — what the clamp actually holds."""
    return STRING_T * math.exp(-MU * wraps(i) * 2 * math.pi)       # as WOUND: fewest wraps = worst


# ── THE SLIDING INSERT (user) ─────────────────────────────────────────────
# One per string, entering from BELOW. Its flat top presses the wound string up against
# the rod, which does two jobs at once: it clamps the string (no separate cup-tip screw)
# and it makes the STRING ITSELF the gauge block.
#
# WHY THAT MATTERS. The dowels are gauged so every string TOP lands on one plane, which
# in the old scheme meant ten different printed pocket depths -- and the smallest step
# between neighbours is 0.025 mm, unrepresentable at any layer height we print. The
# insert converts that per-string difference into a COMMON dimension: it rises until the
# string stops it, so its own position encodes the gauge, and the cradle is a fixed
# offset from there. Printer error is then the same on all ten -- a systematic offset the
# setup absorbs -- instead of per-string scatter. It also drops STRING_GAUGE out of the
# endplate's geometry entirely, so a different string set no longer needs a new endplate.
#
# THE OFFSET IS GAUGE-FREE, which is the whole trick:
#     flat        = ROD_Z - ROD_D/2 - g      the wrap's lowest surface, where it bears
#     dowel centre= -g - PIN_D/2             gauged, so string tops stay coplanar
#     difference  = ROD_D/2 - PIN_D/2 - ROD_Z = 11.59, with no g in it
INS_CLR   = 0.2                                 # Y clearance in its pocket, each side
                                                # (0.3 before: see TAPER_TAN, where every
                                                # 0.1 of it comes straight off the wall
                                                # between neighbouring pockets)
# HOW FAR THE INSERT HAS TO DROP TO BE "UNINSTALLED" (user), which is the position the
# pocket depth is measured from -- not the working one.
#
# At its NOMINAL height the flat IS the wrap's underside, so with the insert there a
# string cannot be threaded at all. Uninstalled means dropped far enough that a THICK
# GAUGE string can be passed between the flat and the coil already on the rod: the gap
# has to admit the string's own diameter, plus room for it to be worked round rather
# than forced. Both terms are the thickest string in the set, since one pocket depth
# serves all ten.
#
# SET BY THE HEIGHT SCREW NOW, as far as it can take the insert (user, 2026-10-30: "1.6mm of
# material +z of the inserts and then the PCTG starts"), which is what lets a hand reach in and
# grab the string. The screw's whole length less the heat-set and that cap is its travel, and
# of the travel the gauge envelope and the overlap into the rod are spoken for: what is left
# is the drop. See THE STACK. It is well past what threading needs, and asserted to stay so.
from cadkit.fasteners import M4, M4_BUTTON_HEAD_D, M4_BUTTON_HEAD_H
THREAD_CLR = D.MIN_WALL                         # room to work the string round, not force it
_DROP_NEED = G_ENVELOPE + THREAD_CLR            # 2.832 for a .080
HS_SCREW_L     = 16.0                           # M4 x 16 button: McMaster stocks 16 and 20 (not 18).
                                                # 20's travel would hang its head 4 below the bed
HS_CAP         = D.MIN_WALL_2P                  # printed floor over the heat-set, and the screw's
                                                # bore through it, under the insert's foot
HS_ROD_OVERLAP = 2 * D.BEAD
INS_DROP  = HS_SCREW_L - (M4.insert_depth + HS_CAP) - (G_ENVELOPE + HS_ROD_OVERLAP)     # 5.77
assert INS_DROP >= _DROP_NEED, f"a {INS_DROP:.2f} drop will not thread a {G_ENVELOPE:.2f} string"
INS_H     = 5 * D.BEAD                          # 4.0 of body below the flat
DIVOT_OFF = ROD_D / 2 - PIN_D / 2 - ROD_Z       # 11.59, cradle centre ABOVE the flat
DIVOT_D   = PIN_D + 0.3                         # 4.3, the dowel's cradle
# THE CRADLE'S +X LIP (user): A SQUARE SHELF, TWO LAYERS ON THE BED. Everything off the dowel's
# crown is the same for every gauge: the crown is the string's underside, and the flat, so the
# insert, moves with the gauge. LIP_STRING_CLR is the air left under the string with the dowel
# seated, which is DIVOT_D/2 - PIN_D/2 below the centre of the cut.
#
# The first lip ran the arc on round to +45 and failed: past a point its layers were a strip
# thinner than a bead. A shelf's last layer is what sets it, its width being LIP_H less the
# arc's height at that layer, and at three layers (x 1.75) the arc has climbed to 1.25, leaving
# 0.30: that same failure. Two layers end at the cradle's +X extreme, where the arc is at
# height 0 and the whole of LIP_H is the layer's width. So the arc stops at 0 deg and the shelf
# carries the wall straight up from there, tangent, for LIP_H. The seat is 135 deg of arc plus
# that wall, the dowel held on +X above and below its centre. The 90 deg corner is fine: only
# a bead's own radius limits it (user).
LIP_STRING_CLR = 0.3
_CROWN_SEATED = PIN_D / 2 - (DIVOT_D / 2 - PIN_D / 2)   # 1.85 over the centre of the cut
LIP_H = _CROWN_SEATED - LIP_STRING_CLR                  # 1.55, the shelf's width in the print
LIP_LAYERS = 2
assert abs(X_FRONT - (DOWEL_X + DIVOT_D / 2) - LIP_LAYERS * LAYER) < 1e-9, (
    "the lip is not whole layers tall: it stands off the bed from the cradle's +X extreme")
assert LIP_H >= D.BEAD, "the shelf's layers are under a bead wide"
# The insert reaches from just past the dowel back under the rod, so the flat spans both
# the cradle and the clamp area. It stops short of the trough's -X wall.
INS_X1    = X_FRONT                             # FLUSH with the block's +X face: the
                                                # insert is the last thing at this end, so
                                                # it bears on the deck panel butting it and
                                                # no block prints out over its slot
# -X END: far enough back to clear the fattest winding, on the grid, rounded the safe
# way (DOWN, i.e. -X: rounding the other way would pinch the coil).
INS_X0    = math.floor((ROD_X - ROD_D / 2 - G_ENVELOPE - D.MIN_WALL)
                       / D.BEAD) * D.BEAD


def insert_flat_z(i: int) -> float:
    """Z of string i's insert top face -- set by the STRING, not by the printer: it rises
    until the wound string stops it against the rod."""
    return ROD_Z - ROD_D / 2 - D.STRING_GAUGE[i]


def clamp_span(i: int) -> float:
    """Y width of the coil's contact with the insert -- CLAMP_WIDTHS string widths of it,
    measured as the spread of the turns that cross the bottom tangent."""
    g = D.STRING_GAUGE[i]
    return (turns(i) - 1.0) * WRAP_F * g + g


def clamp_y(i: int) -> float:
    """Y centre of that contact. It sits -Y of the string's own lane because the coil
    marches that way, by half the advance."""
    return D.nut_y(i) - _adv(i) / 2.0


# ── WHY THE INSERT IS STEPPED IN PLAN, not a rectangle ─────────────────────
# One insert has to cover TWO things at different Y: the dowel, which must sit on the
# string's own lane, and the clamp area, which sits -Y of it by half the coil's advance.
# On the .070 that is 2.84 apart, and the two together need 7.64 mm of Y -- inside a
# 6.5 mm pitch. A rectangle spanning both cannot fit, and shrinking it drops one job.
#
# THEY ARE AT DIFFERENT X, though, so the part can step: a narrow DOWEL LOBE at the +X
# end on the string's lane, and a wider CLAMP LOBE at the -X end offset -Y. Neighbouring
# inserts then overlap in Y while never sharing an X, so they interleave instead of
# colliding -- s9's clamp lobe and s10's dowel lobe overlap 0.45 in Y at X stations that
# do not touch.
#
# The cost is that the inserts are PER STRING in plan (the advance differs with gauge),
# so there are ten variants rather than one. That is the right trade and worth naming:
# what used to be per-string was a POCKET DEPTH differing by 0.025 mm, which no printer
# here can hold. What is per-string now is a Y layout differing by millimetres, which any
# printer holds trivially. The precision moved off the machine and onto the string.
# Both lobes are the FEATURE plus a hair, not a round number -- the padding is wall
# taken from the neighbour, and at the bass end there is none to spare.
# THE Ø4 DOWEL (user, 2026-10-29: "I got the new dowels from mcmaster"; McMaster 91595A119,
# trialled 2026-10-28 as a scratch build). SKU A's two lobes are both PIN_L wide -- "a
# consistent 4mm thickness for A with parallel angles" -- so the taper's two edges are
# parallel and the wall rule below derives its angle at 36.9 deg. The bass inserts follow the
# same rule (insert_lobes): every edge of every insert steps the same S, so every taper in the
# block runs at A's angle.
INS_LOBE_W  = PIN_L                             # 4.0, the dowel lobe = the dowel
CRADLE_L  = PIN_L + 0.3                         # the trough: the dowel and a float, centred
                                                # on the string (slide_insert)


# SKU B's insert is a PITCH WIDE and butts its neighbours. That is what replaces the
# walls it no longer has: the three are located by the s7 finger on one side, the end
# wall on the other, and each other in between. STACK_CLR is deliberately far tighter
# than INS_CLR -- it is a flat sliding on a flat in Z only, the easiest fit there is, and
# every 0.1 of it lands as string-spacing error at the dowel. At 0.1 the worst a single
# dowel can sit off its lane is 0.3 mm even if the whole stack piles one way.
#
# STACK_CLR IS THE SLOT'S GEOMETRY; BASS_FIT IS THE PARTS' (see below). Changing STACK_CLR
# moves the slot's walls as well as the inserts, which is the wrong lever for a fit: the
# slot prints true (below), the stack does not.
# BOTH ITS LOBES ARE FULL WIDTH, which is the part that stops the debris coming back. A
# narrow dowel lobe would leave 2.2 mm of block standing between each pair of bass
# inserts, and in a shared bay that material has a trough under it, a sky over it and a
# pocket either side -- exactly the floating fragment this whole change is removing. Full
# width, they abut, and there is nothing left between them to come loose.
STACK_CLR = 0.1                                 # total Y slip in the shared slot
BASS_CLR  = STACK_CLR / 2 + 0.01                # per side; the +0.01 makes neighbouring
                                                # pockets OVERLAP rather than share a
                                                # face, so their union is one clean
                                                # opening instead of a coincident-face
                                                # boolean

# THE BASS INSERTS ARE PRINTED SMALLER THAN THEIR PLAN, BY BASS_FIT ALL ROUND (user,
# 2026-10-28). On the full-height coupon (bench_joinery insert_slots_full) at STACK_CLR 0.1
# every insert went in ALONE, A "fits perfectly", and all three bass together went in only
# with "a lot of friction since they are pushed tight together". The PETG-GF slot printed
# TRUE -- 21.56 across against 21.52 drawn -- and the stack read 20.89 on calipers against
# 21.2 drawn, so the bind is where three printed parts meet (their steps and faces), not
# their width or the slot's. So the fix is on the PCTG parts only: the pocket is still cut
# from the unshrunk plan, and only the part shrinks. 0.10 a face is the stack finder's pick
# (fit_finder.StackFinder, round 1, 2026-10-13: slot fixed, tokens shrunk all round,
# "0.20 tight / 0.30 good / 0.40 slightly loose" -- its step 0.30 = STACK_CLR + 2 x 0.10).
# SKU A is untouched: it fits.
BASS_FIT = (0.30 - STACK_CLR) / 2.0             # 0.10, off every face of a bass insert


# ── SKU C: STRING 10 ON ITS OWN, AS WIDE AS IT LIKES (user) ─────────────────────
# The longstanding string-10 clip was SKU B's clamp lobe. It hung a full pitch from just above
# its string, which covers strings 8 and 9 with 1.1 to spare but not the outermost: that coil
# marches -Y furthest, and at the .070 its last turn ran 0.33 past the lobe into the end wall
# for the whole insert run (2.6 mm3, invisible to the gate, which lets keyhead_endplate touch
# any string). At a .080 it would have been 1.24.
#
# String 10 has nothing -Y of it, so its insert can simply be wider. SKU C keeps SKU B's +Y
# edges -- it still abuts string 9 -- and runs its CLAMP lobe out to SKU_C_LO, with the dowel lobe
# stepping back in by SKU_C_STEP (user: that shoulder keeps the insert from walking +X, and the
# taper up to it prints like every other insert's). That edge covers the coil for every gauge
# up to D.STRING_GAUGE_MAX with LANE_CLR of air (it is a printed wall, like a finger), on the
# bead grid from the string's own Y. SAMPLED, not just the two ends: the whole-turn count
# (_k_min_g) can step between them, and a step is where the coil jumps.
SKU_C = D.N_STRINGS - 1
_SKU_C_GAUGES = [D.STRING_GAUGE[SKU_C] + (D.STRING_GAUGE_MAX - D.STRING_GAUGE[SKU_C]) * t / 40.0
                 for t in range(41)]
SKU_C_COIL_LO = min(outer_coil_lo(g) for g in _SKU_C_GAUGES)
SKU_C_LO = D.nut_y(SKU_C) - math.ceil((D.nut_y(SKU_C) - (SKU_C_COIL_LO - LANE_CLR)) / D.BEAD
                                      - 1e-9) * D.BEAD
assert all(outer_coil_lo(g) - (SKU_C_LO - BASS_CLR) >= LANE_CLR - 1e-9 for g in _SKU_C_GAUGES), (
    f"string 10's coil reaches past its insert's -Y edge for some gauge up to "
    f"{D.GAUGE_MAX_IN:.3f} in -- the old end-wall clip is back")


def sku_gauge_max(i: int) -> float:
    """The heaviest gauge string i's insert SKU is built for. EVERY INSERT OF A SKU IS ONE PART
    (user: three SKUs, each covering a range of gauges), so anything gauge-shaped on an insert
    is shaped by its SKU's heaviest -- never by whichever string happens to sit in that slot, or
    two inserts of one SKU would come out different. SKU A and SKU B take the heaviest demo
    string in their zone; SKU C takes the envelope, D.STRING_GAUGE_MAX."""
    if i == SKU_C:
        return max(D.STRING_GAUGE[SKU_C], D.STRING_GAUGE_MAX)
    zone = range(N_FINGERED) if i < N_FINGERED else range(N_FINGERED, SKU_C)
    return max(D.STRING_GAUGE[k] for k in zone)


def _clr(i: int) -> float:
    """Pocket clearance for string i. SKU A sits between fingers; SKUs B and C abut in the
    shared slot, so they take the stack fit."""
    return INS_CLR if i < N_FINGERED else BASS_CLR


# ── HOW WIDE THE CLAMP LOBE HAS TO BE: the CONTACT, not the lane ───────────
# It was the lane less its pocket clearance, which made the pocket exactly as wide as the
# lane and the wall between neighbours exactly MIN_WALL_2P -- on the STRAIGHT sections.
# With nothing spare there, the taper had nowhere to take its cosine from and the finger
# came out at 0.96 (user).
#
# The lane is what the COIL needs; the lobe only has to cover where the flat actually
# TOUCHES that coil, which is a good deal narrower -- 3.21 against the lane's 4.9,
# because the contact is the turns that cross the bottom tangent, not the whole winding.
# Sizing it to the contact hands the difference back as wall, and it is measured over
# every string in the zone so a gauge change re-derives it rather than silently eating
# the margin.
_CT = [(clamp_y(i) + clamp_span(i) / 2 - D.nut_y(i),
        clamp_y(i) - clamp_span(i) / 2 - D.nut_y(i)) for i in range(N_FINGERED)]
CLAMP_PAD = 0.2                                 # each side of the contact
CLAMP_HI = max(h for h, _ in _CT) + CLAMP_PAD
CLAMP_LO = min(l for _, l in _CT) - CLAMP_PAD
CLAMP_W = CLAMP_HI - CLAMP_LO
CLAMP_C = (CLAMP_HI + CLAMP_LO) / 2.0
assert CLAMP_HI <= LANE_HI and CLAMP_LO >= LANE_LO, (
    "the clamp lobe has grown outside the lane the coil was fitted into")

# ── HOW SHALLOW THE PLAN'S TAPER HAS TO BE ─────────────────────────────────
# The taper used to be 45 deg because that is the steepest a -X -> +X print will carry.
# But steepest is not free: two neighbouring plans put two PARALLEL diagonals either side
# of the finger between them, and the perpendicular distance between parallel diagonals is
# only cos(theta) of their Y gap. At 45 the 2.2 gap became 1.556, and the two pocket
# clearances took it to 0.96 -- a one-bead finger where the design calls for two.
#
# So the angle is derived from the WALL instead, and 45 becomes the limit it never
# reaches rather than the value it takes:
#
#     wall = gap * cos(theta) - 2 * INS_CLR  >=  MIN_WALL_2P
#
# A shallower taper is strictly better for printing as well -- material arrives more
# gradually, not less -- so the only thing it costs is X, and the run is short enough to
# finish before the dowel's cradle needs full lobe width.
#
# INS_CLR pulls its weight here twice over: it comes off the wall directly AND it raises
# the cosine the taper has to beat. At 0.3 there is no solution at all (the budget is
# 6.5 = 4.3 + 0.6 + 1.6 with nothing spare, so cos(theta) would have to exceed 1); at
# 0.2 the taper comes out around 25 deg.
TAPER_GAP = D.NUT_PITCH - max(INS_LOBE_W, CLAMP_W)   # the Y gap on the straights
_TAPER_COS = (D.MIN_WALL_2P + 2 * INS_CLR) / TAPER_GAP
assert _TAPER_COS < 1.0, (
    f"no taper angle can hold a {D.MIN_WALL_2P} wall: the Y gap is {TAPER_GAP:.2f} and "
    f"the two clearances alone take {2 * INS_CLR:.2f} of it")
TAPER_TAN = math.sqrt(1.0 - _TAPER_COS ** 2) / _TAPER_COS

# SKU C'S -Y STEP. Every other edge steps S = -CLAMP_C, but SKU C's -Y taper runs over string
# 10's coil (see _sku_c_taper_gap): the coil's +X extreme, at rod-axis height, reaches into the
# run from x_s to x_e, and at a full S the pocket edge there stands 0.33 over a .080 winding
# (the trial had to switch its assert off for it). So that one edge steps only as far as every
# gauge SKU C takes allows with INS_CLR of air (a pocket fit), floored to whole beads -- still a
# shoulder, so the insert still cannot walk +X (user), and at a shallower angle than A's, which
# prints the same. The +Y edge steps S.
def _sku_c_step_max() -> float:
    s = -CLAMP_C
    x_e = DOWEL_X - DIVOT_D / 2
    x_s = x_e - s / TAPER_TAN
    lim = s
    for g in _SKU_C_GAUGES:
        x1 = min(ROD_X + ROD_D / 2.0 + g, x_e)
        if x1 > x_s:
            lim = min(lim, (outer_coil_lo(g) - INS_CLR - SKU_C_LO + _clr(SKU_C))
                      * (x_e - x_s) / (x1 - x_s))
    return lim


SKU_C_STEP = math.floor(_sku_c_step_max() / D.BEAD + 1e-9) * D.BEAD
assert SKU_C_STEP >= D.MIN_WALL / 2, (
    f"SKU C's -Y step is down to {SKU_C_STEP:.2f}: string 10's coil leaves no shoulder")


def insert_lobes(i: int):
    """(dowel lobe, clamp lobe) as (y_centre, width) pairs -- the insert's plan.

    SKU A's clamp lobe covers the coil's CONTACT with the flat (CLAMP_LO..CLAMP_HI about
    the string): one fixed window for every SKU A string, so they are all one part. Sizing
    it to each coil is what made every insert a different part."""
    if i < N_FINGERED:
        return ((D.nut_y(i), INS_LOBE_W), (D.nut_y(i) + CLAMP_C, INS_LOBE_W))
    # THE BASS STACK, SHARED BY NEED (user, 2026-10-28: "only extend the inserts as far as
    # needed ... then give the extra space to the next string's insert"; strings 8-10 have no
    # finger wall, so the slot's width is theirs to share out). EVERY INSERT PARALLEL, ONE
    # WIDTH ("do they all keep the parallel angle and consistent width properties that we had
    # for A"): each edge steps SKU A's own offset S between its clamp lobe and its dowel lobe,
    # so a boundary between two bass neighbours is one number b (its clamp-lobe Y; its
    # dowel-lobe Y is b + S), placed in the middle of the range that leaves both strings their
    # needs (_bass_need), less STACK_CLR/2 each side. The stack's outer edges stay put: string
    # 8's against the s7 finger, string 10's clamp lobe at SKU_C_LO.
    S = -CLAMP_C

    def bnd(k):                     # between bass strings k and k + 1, at the clamp lobe
        (dlo, _), (clo, _) = _bass_need(k)
        (_, dhi), (_, chi) = _bass_need(k + 1)
        return (min(clo, dlo - S) + max(chi, dhi - S)) / 2.0

    hi = (D.nut_y(i) + INS_LOBE_W / 2 - S if i == N_FINGERED
          else bnd(i - 1) - STACK_CLR / 2.0)
    if i == SKU_C:
        # ...but SKU C's -Y edge steps only SKU_C_STEP: a full S would run its taper over
        # string 10's coil (see SKU_C_STEP). Its +Y edge still steps S, against string 9.
        lo = SKU_C_LO
        return (((hi + S + lo + SKU_C_STEP) / 2.0, hi + S - lo - SKU_C_STEP),
                ((hi + lo) / 2.0, hi - lo))
    lo = bnd(i) + STACK_CLR / 2.0
    w = hi - lo
    return ((lo + S + w / 2.0, w), (lo + w / 2.0, w))


def _bass_need(i: int):
    """(dowel, clamp) Y spans a bass insert has to cover: its dowel, and its coil's contact
    with the flat plus CLAMP_PAD."""
    dowel = (D.nut_y(i) - PIN_L / 2.0, D.nut_y(i) + PIN_L / 2.0)
    clamp = (clamp_y(i) - clamp_span(i) / 2.0 - CLAMP_PAD,
             clamp_y(i) + clamp_span(i) / 2.0 + CLAMP_PAD)
    return dowel, clamp


def _plan(i: int):
    """The insert's PLAN: clamp lobe, a taper (TAPER_TAN, ~25 deg), then the dowel lobe.

    ONLY THE -Y EDGE IS TAPERED, and that is not a shortcut -- it is what buys the wall
    back (user: the fingers between the inserts were 0.96 where they had to be 1.6).

    THE TAPER IS ONLY NEEDED WHERE MATERIAL APPEARS. Printing -X -> +X, both lobes step
    +Y going forward, so on the plan's -Y side the pocket RETREATS and block material
    arrives with nothing behind it -- an overhang, and the one the user photographed. On
    the +Y side the pocket GROWS and block material leaves, which no printer has ever had
    trouble with. Tapering that side too was symmetry, not physics.

    AND SYMMETRY WAS EXPENSIVE. Two neighbouring plans put two PARALLEL 45 deg edges
    either side of a finger, and the perpendicular distance between parallel diagonals is
    only cos 45 of their Y gap: 2.2 becomes 1.556, and the two pocket clearances take it
    to 0.956. No taper angle fixes that -- the Y budget is 6.5 = 4.3 lobe + 0.6 clearance
    + 1.6 wall with nothing spare, so any slope at all eats into the wall, and even a
    zero-clearance 45 leaves 1.556.

    With one edge square the finger is bounded by a diagonal on one side and a HORIZONTAL
    on the other, and the closest approach between those is the plain Y gap again. The
    square edge sits at x_e, the far end of the taper, so the neighbour's diagonal has
    already finished travelling before this edge jumps."""
    (dy, dw), (cy, cw) = insert_lobes(i)
    yhd, yld = dy + dw / 2, dy - dw / 2
    yhc, ylc = cy + cw / 2, cy - cw / 2
    # THE TAPER IS SHALLOWER THAN 45, and it has to be (user: the fingers between the
    # inserts were 0.96 where they had to be 1.6). See TAPER_TAN -- 45 was the STEEPEST
    # slope printability allows, and taking it was throwing the wall away for nothing.
    x_e = DOWEL_X - DIVOT_D / 2                        # the cradle's -X edge: the lobe is
    x_s = x_e - max(abs(yhd - yhc), abs(yld - ylc)) / TAPER_TAN
    # The taper must finish narrowing +X of the ROD, because the flat bears on the coil's
    # UNDERSIDE -- a line along Y at about the rod's axis. The coil's +X flank reaches
    # further than this, but nothing touches the insert there: it is at mid-height, well
    # above the flat.
    assert x_s >= ROD_X + ROD_D / 2, (
        f"string {i + 1}'s taper starts at {x_s:.2f}, -X of the rod's own face "
        f"({ROD_X + ROD_D / 2:.2f}) -- the clamp lobe would narrow over the contact")
    assert x_s > INS_X0, f"string {i + 1}'s taper starts -X of the insert itself"
    return [(INS_X0, ylc), (x_s, ylc), (x_e, yld), (INS_X1, yld),
            (INS_X1, yhd), (x_e, yhd), (x_s, yhc), (INS_X0, yhc)]


# SKU C'S -Y TAPER RUNS OVER STRING 10'S COIL. The step (SKU_C_STEP) tapers in from x_s to x_e,
# and the coil's +X extreme (at rod-axis height) reaches into that run -- so the tapered pocket edge
# has to clear the coil there, for every gauge SKU C takes. The edge only moves +Y going +X, so the
# tightest point is the furthest +X the coil gets. Guarded because the margin is thin at a .080.
def _sku_c_taper_gap(g: float) -> float:
    (x_s, y_s), (x_e, y_e) = _plan(SKU_C)[1], _plan(SKU_C)[2]
    x1 = min(ROD_X + ROD_D / 2.0 + g, x_e)
    if x1 <= x_s:
        return float("inf")                     # the coil stops short of the taper
    edge = y_s + (y_e - y_s) * (x1 - x_s) / (x_e - x_s) - _clr(SKU_C)
    return outer_coil_lo(g) - edge


_SKU_C_TAPER_GAP = min(_sku_c_taper_gap(g) for g in _SKU_C_GAUGES)
assert _SKU_C_TAPER_GAP >= INS_CLR - 1e-9, (
    f"string 10's coil reaches {-_SKU_C_TAPER_GAP:.2f} past SKU C's tapered pocket edge for some gauge "
    f"up to {D.GAUGE_MAX_IN:.3f} in -- the -Y step has been drawn over the winding")


def _plan_wire(i: int):
    return cq.Workplane("XY").polyline(_plan(i)).close()


def _part_wire(i: int):
    """The plan the INSERT is made from: _plan_wire, less BASS_FIT all round on the bass
    stack. The pocket is cut from _plan_wire itself."""
    if i < N_FINGERED:
        return _plan_wire(i)
    return _plan_wire(i).offset2D(-BASS_FIT, kind="arc")


NECK_LIP = D.BEAD                               # the neck's top face, -X of the cradle


def _neck_x0(i: int) -> float:
    """Where string i's neck starts: a bead -X of the dowel's cradle and no further, because the
    string comes down from the dowel over it and runs lower with every mm -X. Asserted clear of the
    string, for the heaviest gauge, below. THE ONE PLACE THIS IS COMPUTED."""
    return DOWEL_X - DIVOT_D / 2.0 - NECK_LIP


def slide_insert(i: int) -> cq.Workplane:
    """String i's insert, placed where the string will hold it. The POCKET is this part's
    plan offset by its fit (insert_pocket), so the two cannot drift."""
    fz = insert_flat_z(i)
    (dy, dw), (cy, cw) = insert_lobes(i)
    # the dowel lobe, plus a NECK rising from the flat to the cradle. The flat bears on
    # the wrap far below the dowel now, so the insert has to carry the dowel back up; the
    # neck stops AT the cradle centre, which is a dowel-radius under the crown and so
    # still below the string plane -- nothing of the insert can foul the bar either. Only
    # the +X lip (LIP_H) rises above that, and it stops short of the string.
    body = _part_wire(i).extrude(INS_H).translate((0, 0, fz - INS_H))
    # THE HEIGHT-ADJUST EXTENSION (user): a tall foot down to the screw that pushes the insert up --
    # the insert's OWN PLAN carried all the way down (user), so the -Y shoulder that stops it walking
    # +X runs the whole height, and there is no transition to fit. Its +X face is the dowel lobe's:
    # one flat plane, which is what the part prints on.
    body = body.union(_part_wire(i).extrude(INS_EXT_H + 0.01)
                      .translate((0, 0, fz - INS_H - INS_EXT_H)))
    # THE NECK STARTS CLEAR OF THE STRING (_neck_x0).
    nx0 = _neck_x0(i)
    # THE NECK FILLS THE WHOLE PLAN, not just the dowel lobe's width (user). It used to be
    # a box the width of the dowel lobe, clipped to the plan -- so everywhere the plan is
    # WIDER than that box (the taper, and the clamp lobe on the bass strings, which is the
    # wider of the two there) the insert stepped down to the flat and left a notch.
    #
    # There was never a reason for it: the pocket is the plan extruded, so that notch was
    # empty slot, not clearance for anything. Filling it is free material exactly where the
    # part is weakest -- the neck is DIVOT_OFF (11.59) tall on an INS_H (4.00) body -- and it puts the
    # insert's own profile alongside the block's ramp instead of a step floating over it.
    #
    neck = (_part_wire(i).extrude(DIVOT_OFF).translate((0, 0, fz))
            .intersect(box_at((INS_X1 + 1.0) - nx0, 4000.0, DIVOT_OFF + 2.0,
                              x=(nx0 + INS_X1 + 1.0) / 2, y=0.0, z=fz + DIVOT_OFF / 2)))
    body = body.union(neck)
    # THE CRADLE IS THE DOWEL'S LENGTH, NOT THE LOBE'S (user). It used to run the full
    # width of the dowel lobe and a millimetre past each end -- which on SKU A is nearly
    # the same thing, since that lobe is only PIN_L + 0.3 wide, but on SKU B's 6.4 lobe it
    # left an 8.4 trough for a 4.0 dowel. A dowel can then be dropped anywhere along it,
    # and where it lands is the string's BREAK POINT: put it 2 mm off and that string's
    # speaking length starts in the wrong place.
    #
    # ANCHORED ON THE DOWEL LOBE'S +Y EDGE and run -Y from there. That edge is the same
    # place on both SKUs -- nut_y + INS_LOBE_W/2, since SKU B's lobe is hung from it --
    # so one rule serves both: on SKU A the trough spans its lobe exactly and is open at
    # both ends, and on SKU B it stops 2.1 short of the far side, which is the wall the
    # dowel seats against. Either way the dowel has INS_LOBE_W - PIN_L of float, and no
    # rind of insert is left standing anywhere.
    #
    # THE DOWEL COMES IN ON THE DIAGONAL, -X +Z TO +X -Z (user). The cradle centre IS the
    # neck's top face, so a plain round cut left a half-round whose -X extreme is a flat
    # ceiling with the part printing -X up, and at Ø4.3 that stopped being a corner a
    # slicer gets away with. So the seat is turned 45 deg about the dowel, which does not
    # move: -X it stops at -135, which is where the teardrop's flank (the same cut as the
    # axle's, apex print-up) leaves the circle, and the lip below holds the +X side.
    # That flank is also the -X side of the dowel's way in.
    #
    # nozzle=0, A SHARP APEX: the apex lands exactly on the neck's top face, so the part
    # keeps only the half of it below that face. Dulled, that half would be the flat
    # ceiling this is here to remove.
    #
    # THE LIP IS ADDED BEFORE THE CUT, which it only touches on the tangent, and SKU B's wall
    # at the end of the trough stays the height it was.
    zc = fz + DIVOT_OFF
    lip_x0 = DOWEL_X + DIVOT_D / 2
    body = body.union(_part_wire(i).extrude(LIP_H + 1.0).translate((0, 0, zc - 1.0))
                      .intersect(box_at(INS_X1 + 1.0 - lip_x0, 4000.0, LIP_H + 1.0,
                                        x=(lip_x0 + INS_X1 + 1.0) / 2, y=0.0,
                                        z=zc + (LIP_H - 1.0) / 2)))
    body = body.cut(teardrop_hole(DIVOT_D, CRADLE_L, (DOWEL_X, D.nut_y(i) - CRADLE_L / 2.0,
                                                      fz + DIVOT_OFF),
                                  (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), nozzle=0.0))
    return body


# ONE POCKET DEPTH FOR ALL TEN (user). It used to come off insert_flat_z, which carries
# the gauge -- the flat is ROD_Z - ROD_D/2 - g, so a thick string's insert rides lower and
# its pocket was cut deeper. Strings 8-10 came out visibly deeper than the rest.
#
# It is measured from the UNINSTALLED position (user): far enough down that a thick gauge
# string can be threaded between the flat and the coil already on the rod. See INS_DROP.
POCKET_Z0 = (ROD_Z - ROD_D / 2.0 - G_ENVELOPE           # the lowest flat any string may set
             - INS_DROP - INS_H - 1.0)                   # ...its body, and its travel


def insert_pocket(i: int) -> cq.Workplane:
    """The slot string i's insert slides in: its PLAN SILHOUETTE, grown by INS_CLR and
    extruded straight through the block.

    A PRISMATIC SLOT, WITH NO Z VARIATION AT ALL (user), and that is the whole point of
    it. The insert is not seated in this pocket, it TRAVELS in it -- it is fitted from
    below and then rises until the wound string stops it, which is what makes the scheme
    self-referencing. So the pocket cannot be the part's shape at any one height: cut to
    where the part happens to sit and the part can no longer move, because the first thing
    it meets on the way up is the ceiling of its own pocket. Only the plan is shared
    between every position the insert can occupy, so only the plan may be cut.

    (I got this wrong in the obvious direction: the body's top face IS the flat, so
    nothing of the part is above it, and cutting only where material actually is looked
    like the tidy answer. It is the answer for a part that is placed. This one slides.)

    IT ALSO HAS TO REACH THE TOP. Anything left capping the slot limits the same travel,
    and it is a ceiling over a slot -- an overhang in a part that prints -X -> +X. The
    material over an insert was doing no work either way: what holds the string down is
    the ROD, not the block.

    THE SILHOUETTE IS _plan_wire's, not a bounding box and not a second description of
    it. The neck is already clipped to that same profile in slide_insert, so the plan IS
    the part's full X/Y extent, and offsetting it (a TRUE offset, kind="arc" -- see below)
    is enough."""
    z0 = POCKET_Z0                               # ONE depth for all ten -- see POCKET_Z0
    z1 = NUT_TOP + 1.0
    # THE INSERT'S OWN PLAN, SWEPT ALONG Z AND OFFSET BY ITS FIT (user). One profile,
    # one operation -- which is what keeps the cut clean. Everything that ever put a step
    # or an overhang in this socket came from it being TWO shapes: a plan plus a
    # rectangular winding relief whose square +X face landed mid-taper.
    #
    # kind="arc" IS THE TRUE OFFSET, and here that matters twice over. It is the Minkowski
    # sum with a disc, so the clearance is exactly _clr(i) EVERYWHERE, including along the
    # taper -- "intersection" instead extends each corner out to where its two offset
    # edges meet, which overshoots by clr/cos(half-angle) and spends wall that the taper
    # has none of to spare. It also leaves the block's internal corners filleted at the
    # clearance radius rather than sharp, which is free and better to print into.
    #
    # THE PLAN *IS* THE Z SILHOUETTE, which is what makes this exact rather than
    # approximate: the neck is already clipped to the plan in slide_insert, so no part of
    # the insert ever reaches outside that profile at any height. Sweeping the solid along
    # Z therefore sweeps exactly this outline, and extruding the outline is the same
    # solid. Sweeping is also the only modification the socket needs: the insert does not
    # sit in it, it TRAVELS in it.
    return (_plan_wire(i).offset2D(_clr(i), kind="arc")
            .extrude(z1 - z0).translate((0, 0, z0)))


def _lane(i: int):
    """(+Y edge, -Y edge) of string i's coil plus its air. It marches -Y, so the +Y edge
    is where the string arrives and the -Y edge is where its last turn ends. The air is
    LANE_CLR against a printed finger and COIL_CLR where the only neighbour is another
    coil -- see COIL_CLR."""
    y0, y1 = wrap_y(i)
    g = D.STRING_GAUGE[i]
    c = LANE_CLR if i < N_FINGERED else COIL_CLR
    return y0 + g / 2 + c, y1 - g / 2 - c


def bass_bay():
    """The ONE open bay strings N_FINGERED.. share (SKU B).

    Its +Y edge is set by the last finger, not by the coil: that finger is the last place
    the rod is held, so it is the thing worth pinning. Its -Y edge is the deepest bass
    coil plus its air."""
    hi = D.nut_y(N_FINGERED - 1) + LANE_LO - D.MIN_WALL_2P
    lo = min(min(_lane(i)[1] for i in range(N_FINGERED, D.N_STRINGS)),
             SKU_C_COIL_LO - COIL_CLR)          # string 10's coil at the heaviest gauge it may carry
    return lo, hi


def bays():
    """(-Y, +Y) of each string's threading bay.

    NOTHING IS MERGED ANY MORE. This used to take each coil's own lane and fuse any pair
    whose web fell under a threshold -- which is how the bass bays ended up open and the
    walls between their insert pockets ended up holding onto nothing. The zones now say
    up front which strings keep a finger and which share a bay, and turns() sizes every
    coil to fit the answer, so a web can no longer go thin by accident.

    SKU A gets a fixed window either side of its own string. SKU B's three all report the
    SAME span -- one bay, three strings -- which is what makes the fused trough cutter
    open it as a single pocket and leaves finger_gaps() with no gap to find there."""
    lo, hi = bass_bay()
    return [(D.nut_y(i) + LANE_LO, D.nut_y(i) + LANE_HI) if i < N_FINGERED else (lo, hi)
            for i in range(D.N_STRINGS)]


def finger_gaps():
    """Gaps that still carry a printed comb web -- the rod's intermediate supports."""
    b = bays()
    return [i for i in range(D.N_STRINGS - 1) if b[i][0] - b[i + 1][1] > 1e-9]


def _supports():
    """Every Y at which the rod is held: the two end walls and each surviving web."""
    b = bays()
    return ([b[0][1] + 2 * D.BEAD]
            + [(b[i][0] + b[i + 1][1]) / 2.0 for i in finger_gaps()]
            + [b[-1][0] - 2 * D.BEAD])


# (the span + residual checks live below, once wrap_y exists to feed them)


def wrap_y(i: int) -> tuple[float, float]:
    """(start, end) Y of string i's coil. It arrives on its own lane and leaves -Y of it."""
    y0 = D.nut_y(i)
    return y0, y0 - _adv(i)


def wrap_y_drawn(i: int) -> tuple[float, float]:
    """(start, end) Y of string i's coil AS WOUND (wraps), for the assembly. wrap_y is the lane's
    capacity and sizes the printed parts; this is what the strings actually take up."""
    y0 = D.nut_y(i)
    return y0, y0 - wraps(i) * WRAP_F * D.STRING_GAUGE[i]


def rod_span() -> tuple[float, float]:
    """(y0, y1) the rod has to cover: every bay plus a bearing length in the end walls."""
    lo = min(_lane(i)[1] for i in range(D.N_STRINGS))
    return lo - 2 * D.BEAD, D.nut_y(0) + 2 * D.BEAD


ROD_END_W = D.MIN_WALL_2P                       # the rod's +Y stop: the blind wall it butts
assert abs(outer_coil_lo(D.STRING_GAUGE[SKU_C])
           - (wrap_y(SKU_C)[1] - D.STRING_GAUGE[SKU_C] / 2)) < 1e-9, (
    "outer_coil_lo has drifted from wrap_y -- SKU C would be sized off a coil that is not the one drawn")

# ── THE TOP PRISM IN Y: SET BY THE INSERTS, NOT BY THE ROD (user) ─────────────────
# It used to grow -Y until it covered the whole 100 mm rod, which stretched it to -70.85 for no
# structural reason. Now both faces come from the inserts:
#   +Y FACE  string 1's pocket plus Y_WALL of solid for strength, on the bead grid.
#   -Y FACE  the SAME length of material copied past string 10's pocket, so the block is
#            symmetric about the insert field.
Y_WALL  = 10 * D.BEAD                           # 8.0 solid past the outermost insert, for strength
_INS_HI = max(y + w / 2.0 for (y, w) in insert_lobes(0)) + _clr(0)          # string 1's pocket, +Y
_INS_LO = min(y - w / 2.0 for (y, w) in insert_lobes(SKU_C)) - _clr(SKU_C)  # string 10's pocket, -Y
HW   = D.nut_y(0) + math.ceil((_INS_HI + Y_WALL - D.nut_y(0)) / D.BEAD - 1e-9) * D.BEAD   # the +Y face
Y_LO = _INS_LO - (HW - _INS_HI)                                                             # the -Y face

# THE ROD butts a ROD_END_W wall at the +Y face -- that wall IS its +Y stop -- and being a purchased
# 100 mm (the bridge axle's Ø8 x 100), it ends wherever that puts it: out past the -Y face, lying in
# the insertion run rod_bore cuts through the endplate below. The block no longer grows to hide it.
ROD_L  = D.BRIDGE_AXLE_L
ROD_Y1 = HW - ROD_END_W
ROD_Y0 = ROD_Y1 - ROD_L
_ROD_NEED_Y0, _ROD_NEED_Y1 = rod_span()
assert ROD_Y1 >= _ROD_NEED_Y1 - 1e-9 and ROD_Y0 <= _ROD_NEED_Y0 + 1e-9, (
    f"the {ROD_L:g} mm rod spans {ROD_Y0:.2f}..{ROD_Y1:.2f}, short of the "
    f"{_ROD_NEED_Y0:.2f}..{_ROD_NEED_Y1:.2f} its bays need")

# Checked at import, because both are functions of the GAUGE TABLE: a different string
# set has to re-earn them rather than quietly go out of spec.
_SUP = _supports()
_MAX_SPAN = max(abs(_SUP[k] - _SUP[k + 1]) for k in range(len(_SUP) - 1))
# Bending in the rod over its worst span, with every string crossing it pulling at once.
_I = math.pi * ROD_D ** 4 / 64.0
_SPAN_MPA = ((3 * STRING_T / _MAX_SPAN) * _MAX_SPAN ** 2 / 8.0) / (_I / (ROD_D / 2))
_WORST_RES = max(residual(i) for i in range(D.N_STRINGS))
assert _SPAN_MPA <= 250.0, (
    f"the rod carries {_SPAN_MPA:.0f} MPa over its {_MAX_SPAN:.1f} mm unsupported span — "
    f"too many comb webs have been merged away, or the string set got heavier")
assert _WORST_RES <= 60.0, (
    f"the worst string still leaves {_WORST_RES:.1f} N at the clamp — the wrap is not "
    f"doing its job and the clamp is back to bearing on plastic")

BREAK_ANGLE = 10.0                              # MIN break angle over the dowel, so the DOWEL
                                                # (not the rod) terminates the speaking length
assert _break_at(ROD_Z, D.STRING_GAUGE_MAX) >= BREAK_ANGLE, (
    f"a {D.GAUGE_MAX_IN:.3f} in string breaks only {_break_at(ROD_Z, D.STRING_GAUGE_MAX):.2f} deg over its "
    f"dowel -- under the {BREAK_ANGLE} floor, so the rod would end the speaking length, not the dowel")


def _break_deg(i: int) -> float:
    """Down-angle string i takes as it leaves the break dowel, running to where it first
    TOUCHES the wrap circle on the rod's top (true tangency, not the chord)."""
    return _break_at(ROD_Z, D.STRING_GAUGE[i])


_WORST_BREAK = min(_break_deg(i) for i in range(D.N_STRINGS))
assert _WORST_BREAK >= BREAK_ANGLE - 1e-9, (
    f"the worst string breaks over the dowel at only {_WORST_BREAK:.1f} deg (floor "
    f"{BREAK_ANGLE}) — at that angle the ROD, not the dowel, sets the scale length")


# ── THE STRING CLEARANCE LINE ─────────────────────────────────────────────
# There is no string slot any more (see _build), but the line it used to be cut to still
# matters: nothing in this block may stand within SLOT_KEEP of the underside of the
# heaviest string that can be fitted. _build asserts NUT_TOP stays below it.
_APEX      = math.sqrt(2.0)                          # cadkit teardrop apex, in radii
SLOT_KEEP  = D.MIN_WALL_2P                           # 1.6 below the strings
STRING_BOT = -G_ENVELOPE                             # the heaviest supported string's underside
SLOT_Z0    = STRING_BOT - SLOT_KEEP                  # the clearance line


# NO DOWEL BORE IN THE BLOCK (user spotted the cuts). There used to be one per string --
# the dowel's own geometry grown by DOWEL_CLR -- from when the BLOCK carried the dowels.
# The insert carries them now, in its cradle, and the socket the insert travels in
# already clears the dowel completely: the block comes out byte-identical with the bores
# and without them (9638.6 mm^3 either way), and with them suppressed the dowel still
# touches 0.000 mm^3 of block material.
#
# It was invisible while it was redundant and only showed up with the sockets switched
# off for inspection, which is a fair argument for looking at parts with their cuts
# disabled now and then.


def all_pockets() -> cq.Workplane:
    """Every insert's slot, FUSED and subtracted once -- the same lesson the troughs
    taught: ten short booleans against a body this busy left cores behind, one fused
    cutter does not."""
    out = None
    for i in range(D.N_STRINGS):
        k = insert_pocket(i)
        out = k if out is None else out.union(k)
    return out


WRAP_EPS = 0.05                                 # the coil is drawn a hair off the rod


def wrap_radius(i: int) -> float:
    """Radius of string i's coil centreline about the rod axis. THE ONE PLACE THIS IS
    COMPUTED -- build.py drew the coil at this radius while the tail's path put the exit point
    at a radius 0.05 smaller, so every tail started just inside its own coil's surface and
    the union of the two collapsed (string 10 came out at 166 mm^3 when its coil alone was
    165 and its tail 200). Same bug as the touch angle before it."""
    return ROD_D / 2.0 + D.STRING_GAUGE[i] / 2.0 + WRAP_EPS


# THE BED FACE STAYS WHERE THE STOW BORES PUT IT. They have gone, and with them the reason for this
# number, but the -X legs and everything else in chassis.KH_EP_THK stand on it, and the lid over
# the rod and the tail's way out are happy here.
X_BACK = -22.062741699796955
KEYHEAD_W = X_FRONT - X_BACK                      # the keyhead endplate's thickness in X

# THE BLOCK'S TOP, (x, z) from the bed face: the lid over the rod, then down under the bar.
BLOCK_TOP = [(X_BACK, NUT_TOP), (-10.4, NUT_TOP), (-3.2, FRONT_TOP), (X_FRONT, FRONT_TOP)]
_TOP_BAR = min(math.hypot(x0 + (x1 - x0) * k / 50.0 - DOWEL_X, z0 + (z1 - z0) * k / 50.0 - BAR_R) - BAR_R
               for (x0, z0), (x1, z1) in zip(BLOCK_TOP, BLOCK_TOP[1:]) for k in range(51))
assert _TOP_BAR >= BAR_CLR_MIN, f"the block's top stands {_TOP_BAR:.2f} from a bar at fret 0"
_LID_MIN = (abs((-3.2 + 10.4) * (NUT_TOP - ROD_Z) - (-10.4 - ROD_X) * (FRONT_TOP - NUT_TOP))
            / math.hypot(-3.2 + 10.4, FRONT_TOP - NUT_TOP) - ROD_BORE / 2)
assert _LID_MIN >= D.MIN_WALL_2P, f"{_LID_MIN:.2f} of wall from the rod's bore to the sloped top"
# The string must pass over the neck, for every gauge any SKU takes
_NECK_AIR = min(-g - (DOWEL_X - _neck_x0(0)) * math.tan(math.radians(_break_at(ROD_Z, g)))
                - (-g - PIN_D / 2) for g in (D.STRING_GAUGE[0], G_ENVELOPE))
assert _NECK_AIR > 0.0, f"the string runs {-_NECK_AIR:.2f} into its insert's neck"


# ── HEIGHT ADJUST: ONE M4 SCREW UNDER EACH INSERT (user) ─────────────────────────────
# The sliding insert clamps its string by rising against the coil, and until now nothing pushed it
# up. Each insert now grows a tall EXTENSION down into a new prism in the keyhead endplate
# (keyhead_endplate.HS_*), and an M4 x 16 button head, on the
# instrument's one 2.5 mm key -- pushes its foot up from below.
#
# THE NUT IS IN THE ENDPLATE, NOT THE INSERT. An M4 heat-set wants ~8 of width (M4.boss_od); SKU A
# inserts are 3.6-4.3 wide and SKU B 6.4, so only SKU C could carry one. So the heat-set sits in a
# slab of the endplate, mouth DOWN, and the screw travels with adjustment (the user's fallback).
#
# THE STACK, from the chassis up (local frame -- Z relative to STRING_Z):
#   motor_bank.FLOOR_TOP  top of the wide corner rib the keyhead sits over (chassis)
#   HS_PRISM_BOT          2.0 above that rib -- and the heat-sets' mouths, flush in it (user: the lower,
#                         the easier to reach). The heads hang below, down into the rib, which
#                         chassis.py opens for them.
#   HS_FLOOR              where a DROPPED insert's foot rests: the tip, screw fully undone
#
# THE SCREW'S TWO ENDS (user) set the rest:
#   * TIGHTENED ALL THE WAY -- head seated on the bottom face, it can go no further -- the insert's flat
#     stands HS_ROD_OVERLAP up INTO the rod. So even a string of no gauge at all clamps against the rod
#     before the head bottoms out: you always tighten against the string, never against the endplate.
#   * FULLY UNDONE -- the insert dropped for threading, flat at _FZ_LOW -- the head still clears
#     chassis.Z_BOT, where the leg's body adapter begins.
from . import motor_bank as _MB                  # motor_bank imports only dimensions/helpers/components
HS_HEAD_CLR    = 0.4                             # radial air round a head in its chassis cavity
HS_HEAD_CAV_D  = M4_BUTTON_HEAD_D + 2 * HS_HEAD_CLR
HS_PRISM_BOT   = _MB.FLOOR_TOP + 2.0 - D.STRING_Z    # 2 beads up: the head, fully undone, needs it
# THE EXTENSION puts a DROPPED insert's foot on the floor: the lowest flat any string may set, less
# the threading drop, less the body -- the same datum POCKET_Z0 is cut from.
_FZ_LOW      = ROD_Z - ROD_D / 2.0 - G_ENVELOPE - INS_DROP
_FZ_TIGHT    = ROD_Z - ROD_D / 2.0 + HS_ROD_OVERLAP
HS_REACH_MAX = _FZ_TIGHT - _FZ_LOW                 # the tip's whole travel, undone to tightened
HS_FLOOR     = HS_PRISM_BOT + HS_SCREW_L - HS_REACH_MAX
INS_EXT_H    = (_FZ_LOW - INS_H) - HS_FLOOR
assert INS_EXT_H > 0.0, "the height-adjust floor is above the insert body"
assert abs(HS_FLOOR - (HS_PRISM_BOT + M4.insert_depth + HS_CAP)) < 1e-9, (
    f"the floor over the heat-set is {HS_FLOOR - HS_PRISM_BOT - M4.insert_depth:.2f}, not {HS_CAP}")
HS_HEAD_LOW = HS_PRISM_BOT - HS_REACH_MAX - M4_BUTTON_HEAD_H     # a head's bottom, fully undone
assert HS_HEAD_LOW >= _MB.BED_Z - D.STRING_Z - 1e-9, (
    f"fully undone, a height-screw head drops to z {HS_HEAD_LOW + D.STRING_Z:.2f}, below the bed "
    f"({_MB.BED_Z:.2f}) where the leg's body adapter is")

# THE INSERT PRINTS ON ITS +X FACE (user): lying on that flat face and growing -X, the reliable way to
# make a 60 mm part, rather than standing it up as a tower. That face cannot follow a roof, so the
# POCKET carries the roof instead -- a HOUSE whose 45 deg sides pass the insert's +X corners (a small
# locating contact each) and whose flat top stands HS_ROOF_T clear of the insert's face. That top is
# a BRIDGE in the keyhead's -X -> +X print; the gap is there so it may sag.
HS_ROOF_T = 2 * D.BEAD
INSERT_UP = (-1.0, 0.0, 0.0)                    # the insert's own build axis: its +X face is the bed
HS_POCKET_X1 = INS_X1 + HS_ROOF_T + max(_clr(i) for i in range(D.N_STRINGS))   # the roofs' +X reach


def insert_foot_z(i: int) -> float:
    """Local Z of string i's insert FOOT, clamped on its demo string (as drawn)."""
    return insert_flat_z(i) - INS_H - INS_EXT_H


def screw_reach(i: int) -> float:
    """How far above the floor string i's screw tip stands when that insert is clamped."""
    return insert_foot_z(i) - HS_FLOOR


# TWO ROWS. The heads hang side by side in the chassis rib, each in its own HS_HEAD_CAV_D cavity, and on
# the string pitch those would run together -- so the strings alternate between two X rows. Row A stands
# in the plan's wide -X part, over the CLAMP lobe; by row B the plan has narrowed to the DOWEL lobe, which
# sits ~1.6 +Y of the clamp one, so row B's screws are centred on THAT (user: keep the tip bearing).
# HS_ROW_DX is then the smallest whole-bead spread that still leaves a two-bead web between neighbouring
# cavities, and string 1 takes row A -- both, so the heads stay as far -Y as they can: the +Y-most of them
# is what the leg has to slide clear of (legs.SERVICE_SLIDE).
_HS_ROW_A = X_BACK + D.WALL_THICKNESS + HS_HEAD_CAV_D / 2.0


def _row_of(i: int) -> int:
    return (SKU_C - i + 1) % 2


def _screw_y(i: int) -> float:
    (dy, _dw), (cy, _cw) = insert_lobes(i)
    return dy if _row_of(i) else cy


def _solve_row_dx() -> float:
    """The smallest whole-bead row spread whose neighbouring head cavities keep MIN_WALL_2P of web."""
    for n in range(1, 41):
        dx = n * D.BEAD
        xs = [_HS_ROW_A + (dx if _row_of(i) else 0.0) for i in range(D.N_STRINGS)]
        if all(math.hypot(xs[i] - xs[i + 1], _screw_y(i) - _screw_y(i + 1)) - HS_HEAD_CAV_D
               >= D.MIN_WALL_2P - 1e-9 for i in range(D.N_STRINGS - 1)):
            return dx
    raise AssertionError("no row spread leaves a two-bead web between the head cavities")


HS_ROW_DX = _solve_row_dx()
HS_ROWS = (_HS_ROW_A, _HS_ROW_A + HS_ROW_DX)


def height_screw_xy(i: int):
    """(x, y) of string i's height screw, local frame: its row, centred on the lobe that row stands
    over -- the clamp lobe in row A, the dowel lobe in row B."""
    return HS_ROWS[_row_of(i)], _screw_y(i)


def _roof_groups():
    """The +X ROOF spans, as (y_lo, y_hi, clr) of the dowel lobes (the fit included in lo/hi, and kept so
    the roof can start exactly at the pockets' own +X face). Pockets whose lobes abut -- the bass SKUs,
    8-10 -- take ONE roof over the lot: give each its own and the roofs meet in a peak and a valley
    between the strings (user caught this), where the bridge has to stay flat."""
    out = []
    for i in range(D.N_STRINGS):                  # string 1 is +Y, so each next string is -Y of the last
        (dy, dw), _cl = insert_lobes(i)
        c = _clr(i)
        lo, hi = dy - dw / 2.0 - c, dy + dw / 2.0 + c
        if out and out[-1][0] - hi < D.MIN_WALL_2P:
            out[-1] = (min(out[-1][0], lo), max(out[-1][1], hi), max(out[-1][2], c))
        else:
            out.append((lo, hi, c))
    return out


def _roof_cutter(lo: float, hi: float, c: float, z_top: float) -> cq.Workplane:
    """One group's roof, floor to the prism's top: full width until the pockets' own +X face (INS_X1 + the
    fit), then a TRUE 45 deg ramp -- rise HS_ROOF_T over the same run -- to a flat HS_ROOF_T past that
    face. Starting the ramp anywhere -X of that face would leave the pocket at full width under part of
    it, and the material would then arrive in one step: a narrow flat ledge, which is neither a ramp the
    printer can climb nor a span it can bridge (user). It runs the FULL height of the prism because that
    is how far the prism stands +X of those faces: roofed, the -X -> +X print never meets a ceiling there
    and the prism's own +X wall stays whole."""
    t = HS_ROOF_T
    assert hi - lo > 2 * t, f"a {hi - lo:.2f} roof span has no room for its flat top"
    x0 = INS_X1 + c                                # the pockets' +X face: where the ramp starts
    pts = [(x0 - 0.5, lo), (x0, lo), (x0 + t, lo + t),
           (x0 + t, hi - t), (x0, hi), (x0 - 0.5, hi)]
    return (cq.Workplane("XY").polyline(pts).close()
            .extrude(z_top - HS_FLOOR).translate((0, 0, HS_FLOOR)))


def lower_pockets(z_top: float) -> cq.Workplane:
    """Every extension's slot, floor up into the main pockets: the insert's own plan grown by the fit,
    and ONE roof per group of abutting pockets (_roof_groups), carried up to the prism's top `z_top`."""
    out = None
    for i in range(D.N_STRINGS):
        k = (_plan_wire(i).offset2D(_clr(i), kind="arc")
             .extrude((POCKET_Z0 + 0.5) - HS_FLOOR).translate((0, 0, HS_FLOOR)))
        out = k if out is None else out.union(k)
    for lo, hi, c in _roof_groups():
        out = out.union(_roof_cutter(lo, hi, c, z_top))
    return out


def height_screw_negatives(i: int):
    """Heat-set pocket (mouth in the bottom face) and shank/tip bore for string i, TEARDROPS along Z
    (sideways to the -X -> +X build), apex +X. The head hangs below the part, in the chassis."""
    x, y = height_screw_xy(i)

    def bore(d, z0, z1):
        return teardrop_hole(d, z1 - z0, axis_point=(x, y, z0), axis_dir=(0.0, 0.0, 1.0),
                             print_up=PRINT_UP)
    # the pocket's Ø for a TEARDROP (cadkit: a sideways pocket prints loose at the round one's
    # 6.1 -- user, 2026-10-28: these inserts "go in too loose")
    return [bore(M4.pilot_d((0.0, 0.0, 1.0), PRINT_UP), HS_PRISM_BOT - 1.0,
                 HS_PRISM_BOT + M4.insert_depth),
            bore(M4.shaft_clr_d, HS_PRISM_BOT + M4.insert_depth - 0.01, HS_FLOOR + HS_REACH_MAX + 1.0)]


def height_screw(i: int) -> cq.Workplane:
    """Dummy M4 x 16 button head, head DOWN, tip on string i's clamped insert foot (local frame)."""
    from cadkit.fasteners import m4_button_screw
    x, y = height_screw_xy(i)
    tip = HS_FLOOR + screw_reach(i)
    s = m4_button_screw(HS_SCREW_L).rotate((0, 0, 0), (1, 0, 0), 180)   # head z 0..h, shank up to h + L
    return s.translate((x, y, tip - (M4_BUTTON_HEAD_H + HS_SCREW_L)))


def height_insert(i: int) -> cq.Workplane:
    """Dummy M4 heat-set under string i, mouth flush in the prism's bottom face (local frame)."""
    from cadkit.fasteners import seated_insert
    x, y = height_screw_xy(i)
    return seated_insert(M4, (x, y, HS_PRISM_BOT), (0.0, 0.0, 1.0))


# ── what the layout must keep true ─────────────────────────────────────────────
for _i in range(D.N_STRINGS - 1):
    (_xa, _ya), (_xb, _yb) = height_screw_xy(_i), height_screw_xy(_i + 1)
    _d = math.hypot(_xa - _xb, _ya - _yb)
    assert _d - HS_HEAD_CAV_D >= D.MIN_WALL_2P - 1e-9, (
        f"strings {_i + 1} and {_i + 2}: head cavities leave {_d - HS_HEAD_CAV_D:.2f} of web")
    assert _d - M4.insert_pilot_d >= D.MIN_WALL_2P - 1e-9, (
        f"strings {_i + 1} and {_i + 2}: heat-set pockets leave {_d - M4.insert_pilot_d:.2f} of wall")
for _i in range(D.N_STRINGS):
    _x, _y = height_screw_xy(_i)
    (_dy, _dw), (_cy, _cw) = insert_lobes(_i)
    assert INS_X0 <= _x - M4.shaft_clr_d / 2.0 and _x + M4.shaft_clr_d / 2.0 <= INS_X1 + 1e-9, (
        f"string {_i + 1}'s screw tip bore reaches past its extension's +X face")
    assert 0.0 <= screw_reach(_i) <= HS_REACH_MAX + 1e-9, f"string {_i + 1}'s screw reach is out of range"


def lanes() -> cq.Workplane:
    """Every lane's way out -X, floor to sky: the clamp lobe carried past the bed face. What stands
    between two lanes is a finger, held by the floor alone; the +X opening is the pockets' own."""
    out = None
    for i in range(D.N_STRINGS):
        (_dy, _dw), (cy, cw) = insert_lobes(i)
        c = _clr(i)
        k = box_at(INS_X0 + 0.5 - (X_BACK - 1.0), cw + 2 * c, NUT_TOP + 1.0 - NUT_BASE,
                   x=(INS_X0 + 0.5 + X_BACK - 1.0) / 2, y=cy, z=(NUT_TOP + 1.0 + NUT_BASE) / 2)
        out = k if out is None else out.union(k)
    # string 8 arrives past its clamp lobe's +Y edge, so that edge moves over for it as far +X as the
    # taper, where the pocket opens anyway: the finger it comes off is the one that carries the most
    y0, y1 = insert_lobes(N_FINGERED)[1][0] + insert_lobes(N_FINGERED)[1][1] / 2, _lane(N_FINGERED)[0]
    x1 = _plan(N_FINGERED)[2][0]
    out = out.union(box_at(x1 - (X_BACK - 1.0), y1 - y0, NUT_TOP + 1.0 - NUT_BASE, x=(x1 + X_BACK - 1.0) / 2,
                           y=(y0 + y1) / 2, z=(NUT_TOP + 1.0 + NUT_BASE) / 2))
    return out


def _build() -> cq.Workplane:
    # ONE solid prism under the top's outline, and every feature is CUT from it.
    pts = BLOCK_TOP + [(X_FRONT, NUT_BASE), (X_BACK, NUT_BASE)]
    body = cq.Workplane("XZ", origin=(0.0, HW, 0.0)).polyline(pts).close().extrude(HW - Y_LO)

    # SOCKETS FIRST -- the plan, swept, offset by the fit. Nothing else.
    # ...the slots the INSERTS rise through, cut from the parts' own profiles so the
    # pocket cannot drift from the thing it has to accept.
    body = body.cut(all_pockets())
    body = body.cut(lanes())

    # THE ROD BORE. BLIND at +Y: that wall is the rod's +Y stop, the same trick the bridge axle
    # uses. It slides in from -Y through all ten comb webs at once, so it must be a precision
    # shaft and not a dowel.
    body = body.cut(rod_bore())
    return body


def rod() -> cq.Workplane:
    """The wrap rod itself, in the nut block's local frame — the bridge axle's shaft."""
    return cyl_y(ROD_D, ROD_Y1 - ROD_Y0, y0=ROD_Y0, x=ROD_X, z=ROD_Z)


def rod_bore() -> cq.Workplane:
    """The rod's bore, in the local frame: open at -Y (the rod slides in there), BLIND at +Y.
    It runs the rod's whole length past its seat, so the rod can start from outside the -Y face."""
    return teardrop_hole(ROD_BORE, (ROD_Y1 - ROD_Y0) + ROD_L,
                         axis_point=(ROD_X, ROD_Y0 - ROD_L, ROD_Z),
                         axis_dir=(0.0, 1.0, 0.0), print_up=PRINT_UP)


nut_block = _build()
