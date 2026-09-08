"""Nut block geometry (×1) — keyhead string termination. PETG-GF (clamps bear on it).

THE WRAP CAPSTAN (user). The string does not go straight from the break edge to a
clamp any more. It winds turns around a shared rod first, and the clamp behind it
only has to hold what the capstan leaves:

    bridge  ->  BREAK DOWEL  ->  WRAP ROD (n turns)  ->  GATE/CLAMP  ->  tail

Capstan (Euler-Eytelwein), T = T0.e^-mu.theta, mu = 0.15 steel on steel:

    no wrap    147 N at the clamp  ->  490 N of clamp force  ->  39 MPa on plastic
    1.5 turns   36 N               ->  119 N
    3.5 turns    5 N               ->   18 N

That is the whole point of the scheme: the clamp was never the wrong mechanism, it
was being asked for 490 N. Every string still terminates on the SAME clamp hardware
it did before (M4 cup-tip set screw in a brass heat-set insert) — it is only the
load that changed.

NO ANVIL (user). A second Ø2 dowel used to sit under the tail so the screw pinched it
against STEEL rather than against the plastic floor. It existed for load that no longer
happens: at 46 N of clamp force the floor sees a fraction of what made the plain clamp
untenable, and the pocket it needed was the last real overhang in the part — a vertical
+X wall the -X -> +X build had to bridge, with no +X face to open toward the way the
break dowel's pocket has. Deleting it takes ten overhangs, ten pockets and a BOM line
with it, and leaves the part simpler rather than more complicated.

THE ROD IS THE BRIDGE AXLE'S OWN PART. Ø5 g6 precision shaft, D.BRIDGE_AXLE_D, the
same stock the changer end already buys — one shaft diameter now serves the bridge
axle and this rod, so a wrap post is not a new line in the BOM. Ø5 also bends the
.070 at 26.2% outer-fibre strain against Ø3's 37.2% (Ø6 would be 22.9%), i.e. it
sits where a guitar tuner post sits, which is the thing this is imitating.

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

    ~2.94 turns on every string, set so the CLAMP AREA is three string widths wide
    (CLAMP_WIDTHS) -> 9.0-9.2 N left at the tail out of 147.
    The webs that survive are gaps 1-8; only s9->s10 merges, where the two coils'
    lanes overlap outright, and the rod spans 16.69 mm there -- 75 MPa. See bays().

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
from .helpers import cyl, box_at, cyl_y
from cadkit.holes import teardrop_hole

PRINT_UP = (1.0, 0.0, 0.0)                      # build axis: the -X face is the bed

# ── hardware (the clamp is unchanged; only its load changed) ────────────────
INSERT_D = D.NUT_INSERT_D
INSERT_L = D.NUT_INSERT_L
SCREW_D  = D.NUT_SCREW_D
PIN_D    = D.NUT_PIN_D                          # Ø2 break dowel (one per string)
PIN_L    = D.NUT_PIN_L
PIN_CLR  = D.NUT_PIN_CLR
PIN_SEAT_D = PIN_D + 2 * PIN_CLR
PIN_SEAT_L = PIN_L + 2 * PIN_CLR

ROD_D = D.BRIDGE_AXLE_D                         # Ø5 — the bridge axle's own shaft
ROD_FIT = 0.4                                   # the rod is LOCATED, not gripped: the wraps
                                                # load it -X and the comb takes that; it only
                                                # has to slide in through 10 fingers at once
ROD_BORE = ROD_D + ROD_FIT

# ── X layout (local frame) ─────────────────────────────────────────────────
# The prism is the KEYHEAD's footprint, D.KEYHEAD_W -- which is 4.2 thicker than the
# bridge's D.ENDPLATE_W, and this module is the reason why (user: extend the thickness
# along X to fit). The capstan spends X the old scheme did not: the rod, and the
# threading bay a hand needs around it. Behind that the clamp inserts STILL need two
# staggered rows, because O6 pockets on a 6.5 string pitch cannot share one row at all
# -- perfectly spaced they leave 0.5 mm of wall, and the turn counts differ so the
# worst pair closes to 5.78 and interferes outright.
#
# The growth is all -X, AWAY FROM THE STRINGS: X_FRONT and the break edge at X=0 do not
# move, so the scale length is untouched and the bridge stays exactly where it is.
X_FRONT = D.KEYHEAD_PX_BUF                      # +2.4: +X lip, reclaimed from 4.0 -- see
                                                # dimensions.KEYHEAD_PX_BUF for the walk
X_BACK  = X_FRONT - D.KEYHEAD_W                 # -25.6: -X outer face (the bed face)
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
ROD_X   = -8 * D.BEAD                           # -6.4 rod centre
# ROD_Z IS SET BY THE BREAK ANGLE, not by taste. The dowel -- not the rod -- has to
# terminate the speaking length, which means the string must leave the dowel at a real
# down-angle rather than drifting off it. The angle is worst for the THICKEST string
# (its centre starts lowest, so it has the least drop to play with over the same run),
# so one rod height for all ten is set by the .070 and every thinner string simply gets
# a steeper break. At -0.8 the .070 broke at 5.5 deg, half the floor -- three beads down
# fixes every string at once. See _break_deg, which is asserted below.
# THE STRING ENTERS AND LEAVES ON THE ROD'S -Z SIDE (user), so ROD_Z is DERIVED from
# the break angle rather than chosen. Wrapping the underside is what removes the two
# sharp reversals the old path had -- the string used to run DOWN off the dowel, hit the
# rod's mid-height and turn back UP, then reverse again to reach the exit. Now it leaves
# the dowel already heading down, meets the rod underneath, wraps, and leaves on the same
# side pointing straight at the clamp.
#
# The rod ends up ABOVE the string plane, which is the trade: -z is the accessible side
# for restringing, and it is the only option that leaves room to grow a 45 from the
# trough up to the dowels without widening the block in X (user's reasoning, and it
# matches what the +X ramp measured twice: there is no X to spare).
#
# GAUGE-INDEPENDENT, which the +z arrangement was not. The string sits on the dowel crown
# at -g and meets the wrap circle at ROD_Z - (ROD_D/2 + g/2); the g/2 appears on both
# sides and cancels, so the drop is ROD_D/2 - ROD_Z for every string. One rod height, one
# break angle, all ten -- against 26-31 deg of spread before.
# THE TARGET IS NOT THE FLOOR, and keeping them separate is the point. BREAK_ANGLE
# (below) is the inherited MINIMUM -- down-bearing T*sin(a) must beat the string's
# vibrational lift, which bounds the angle from below and says nothing about where to
# aim. Solving ROD_Z for the floor itself left ~0.4 deg of margin, which is no margin.
#
# 15 deg is the builders' consensus target for a nut break: production tilted headstocks
# run 10-14, ~15 is the commonly stated aim, and the practical minimum is 5-7. The
# recurring caveat is the one that stops us going higher -- once downforce is adequate,
# more angle buys nothing, and what does the damage is the RADIUS being bent over. Ours
# is a O2 dowel, a 1 mm radius, far sharper than a nut, and the .070 is the least
# tolerant string of a tight bend. So: adequate and no more.
#
# (Our case is easier than a guitar's in one way -- the forum worry about strings jumping
# out of the slot does not apply, since ours is clamped and the capstan holds it. The
# requirement here is only that the DOWEL, not the clamp, terminates the speaking length.)
BREAK_TARGET_DEG = 15.0                             # deg, what ROD_Z is solved for
# THE STRING WRAPS OVER THE TOP, WHICH IS WHAT PUTS THE ROD BELOW THE STRINGS (user).
#
# The underside wrap read better on paper -- it gave a gauge-free break angle and put the
# clamp and the dowel at similar heights. But it forced the rod ABOVE the string plane,
# and that is unplayable: the bar rides ON the strings, so at fret 0 a O19 bar's underside
# is only 2.18 above the plane where the rod sits 6.05 behind the dowel -- and the rod's
# top stood at 3.38. It fouled the bar by 1.20, which costs the first ~centimetre of every
# string. A tuning mechanism that cannot be barred at the first fret is not a mechanism.
#
# Wrapping the other way lets the rod drop to -4.477, top at -1.977, clearing the bar by
# 4.16. What it costs is listed honestly:
#   * THE BREAK ANGLE IS NO LONGER GAUGE-FREE. Underneath, the -g/2 at the dowel and the
#     +g/2 in the wrap radius cancelled. Over the top they ADD, so the drop carries a -g
#     and thick strings break steeper than thin. ROD_Z is therefore solved for the
#     THINNEST string, the shallowest case: every other string then exceeds the target
#     rather than falling short of it.
#   * THE INSERT GROWS A NECK. Its flat now bears on the wrap far below the dowel, so it
#     has to reach back up -- DIVOT_OFF goes from 0.62 to 5.98. That is the trade the user
#     named, and it is the right way round: a taller printed part is cheap, an unplayable
#     first fret is not.
# THE THICKEST STRING SETS THE ROD, not the thinnest. Over the top the wrap radius grows
# with gauge faster than the drop does, so a FAT string breaks SHALLOWER -- the reverse of
# the underside wrap, where the thick one was steepest. Solving for the thin string left
# the .070 at 2.7 deg against a 10 deg floor.
_G_MAX  = max(D.STRING_GAUGE)                   # the shallowest break: sets the rod


def _break_at(rod_z: float, g: float) -> float:
    """True tangent angle, in degrees, for a rod at rod_z under string gauge g."""
    hr = ROD_D / 2 + g / 2
    dx, dz = DOWEL_X - ROD_X, -g / 2 - rod_z
    return math.degrees(math.atan2(dz, dx)) - math.degrees(math.asin(hr / math.hypot(dx, dz)))


def _solve_rod_z(g: float, target: float) -> float:
    """ROD_Z that gives string g the target break angle, by bisection.

    SOLVED, NOT WRITTEN IN CLOSED FORM. The obvious algebra -- drop to the wrap's top over
    the run -- is a CHORD, and over the top the chord and the tangent diverge badly: it
    put the rod where the real angle was 1.9 deg while claiming 15. The tangent is what
    the string follows, and it is transcendental in rod_z, so it gets solved."""
    lo, hi = -80.0, -ROD_D / 2 - g - 0.001      # the rod must clear the string
    for _ in range(200):                        # angle falls monotonically as rod_z rises
        mid = (lo + hi) / 2.0
        if _break_at(mid, g) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


ROD_Z   = _solve_rod_z(_G_MAX, BREAK_TARGET_DEG)
# THE BAR HAS TO CLEAR IT. A round bar resting on the strings at fret 0 rises
# R - sqrt(R^2 - d^2) above the string plane d behind its contact point; nothing may
# stand higher than that anywhere behind the nut.
BAR_R   = 19.0 / 2                              # a typical steel bar
_BAR_UNDER = BAR_R - math.sqrt(BAR_R ** 2 - (DOWEL_X - ROD_X) ** 2)
assert ROD_Z + ROD_D / 2 <= _BAR_UNDER - 0.8, (
    f"the rod's top ({ROD_Z + ROD_D / 2:+.2f}) reaches the bar's underside "
    f"({_BAR_UNDER:+.2f}) at fret 0 -- the first centimetre could not be barred")

# ── Z extent ───────────────────────────────────────────────────────────────
# ONE PRISM, AND A SHORT ONE. NUT_TOP used to be INSERT_GAP + INSERT_POCKET -- whatever
# height the M4 clamp inserts needed to drop in from +Z. Those screws are gone (the
# sliding insert IS the clamp) and with them the only reason this block stood above the
# strings. What is left to cover is the ROD BORE, so that sets it.
NUT_TOP  = ROD_Z + ROD_BORE / 2 + D.MIN_WALL_2P  # a two-bead lid over the rod
NUT_BASE = D.DECK_TOP_Z - D.STRING_Z             # prism base sits on the deck plane

BAY_R   = ROD_D / 2 + 2.5                       # 5.0 threading annulus around the rod --
                                                # the room a hand needs to pass the tail
                                                # around it, not a clearance
# THE TWO CLAMP ROWS ARE GONE with the screws that needed them. They sat at -15.2 and
# -20.8 and were staggered so O6 heat-set inserts could clear each other at a 6.5 pitch;
# the sliding insert clamps the string against the rod instead, so none of that layout --
# nor the wall behind it that _NX_WALL policed -- has anything left to protect.
TAIL_X  = None                                  # set below, once INS_X0 exists


def touch_angle(i: int) -> float:
    """Angle about the rod axis (in the XZ plane, from +X) at which string i first
    TOUCHES the wrap circle, coming down off its dowel. The LOWER of the two tangents,
    because the string wraps the underside.

    THE ONE PLACE THIS IS COMPUTED. The turn count, the drawn string path and the coil's
    start phase all read it; when build.py owned a second copy the straight run and the
    coil disagreed and left a visible gap in the wrap."""
    g = D.STRING_GAUGE[i]
    hr = ROD_D / 2 + g / 2                       # the string's centre-path radius
    dx, dz = DOWEL_X - ROD_X, -g / 2 - ROD_Z     # rod axis -> dowel (the rod sits BELOW)
    # the UPPER of the two tangents: the string now comes down onto the rod's top
    return math.atan2(dz, dx) + math.acos(hr / math.hypot(dx, dz))


WRAP_F   = 1.05                                 # axial rise per turn, as a multiple of the
                                                # string's own diameter: the turns lie all but
                                                # touching. They must NOT cross -- under tension
                                                # a string crossing itself can cut itself in two
LANE_CLR = 0.5                                  # air each side of a coil, before its comb web
# ── HOW MANY TURNS: set by the CLAMP AREA, then snapped to a clean exit (user) ──
# The insert presses up against the WOUND string on the rod's underside, so the clamp
# area is however much coil crosses the bottom tangent. Three string widths of it (user):
#
#     clamp width, in string widths = (TURNS - 1) * WRAP_F + 1
#
# GAUGE-INDEPENDENT, and pleasingly so: the coil's axial pitch and the string's own width
# both scale with g, so the ratio does not. One turn count serves all ten.
CLAMP_WIDTHS = 3.0                              # string widths of contact at the clamp
_N_WANT = 1.0 + (CLAMP_WIDTHS - 1.0) / WRAP_F   # 2.905 turns, if turns were free

# ...but they are NOT free, because the TAIL HAS TO LEAVE POINTING AT THE CLAMP. It
# exits wherever the winding stops, and the exit passage, the clamp screw and the
# insert's own flat all sit on the bottom tangent running -X. So the wrap must stop AT
# THE BOTTOM (-90 deg), which quantises TURNS: the coil enters at touch_angle (~-74 deg,
# set by the break geometry) and must sweep to -90 plus a whole number of turns.
#
# That is the same constraint the old half-turn rule was groping at, but stated properly.
# The old rule ("half turns only, or the tail exits +X") was a rule of thumb for the
# over-the-top wrap; underneath, what matters is landing on the bottom, and the fraction
# that achieves it is set by where the string first touches -- not by halves.
# TURNS IS PER STRING NOW, and it has to be. Over the top, touch_angle carries the
# gauge (the wrap radius does), so the entry spreads 12.38 deg across the set against
# 0.29 underneath -- and a single count would leave the worst tail 9 deg off the bottom,
# exiting into the trough wall instead of running -X to the clamp.
#
# It costs almost nothing: the counts differ by hundredths of a turn, so the clamp area
# barely moves, and the inserts are already per-string in plan. What it buys is every
# tail leaving exactly on the bottom tangent.
def turns(i: int) -> float:
    """Turns for string i: sweep from where it touches, round to the bottom tangent, plus
    whichever whole count lands the clamp area nearest CLAMP_WIDTHS."""
    # THE WRAP CONTINUES THE WAY THE STRING IS ALREADY TRAVELLING -- phi INCREASING.
    # It arrives heading -X and downward and touches the rod's top, so it carries on over
    # and down the FAR side. Sweeping phi the other way makes it reverse at the touch
    # point: a sharp 180 and then a coil wound backwards.
    # ...AND IT LEAVES AT THE TOP, not the bottom (user). Sweeping forward, the tangent
    # at phi is (-sin phi, cos phi): at the TOP that points -X, straight at the clamp; at
    # the BOTTOM it points +X, back toward the bridge. So the wrap must stop at +90 deg.
    sweep0 = (math.pi / 2 - touch_angle(i)) % (2 * math.pi)       # entry -> the TOP
    k = max(1, round((_N_WANT * 2 * math.pi - sweep0) / (2 * math.pi)))
    return (sweep0 + k * 2 * math.pi) / (2 * math.pi)


def clamp_widths(i: int) -> float:
    """Contact at the clamp, in string widths -- what CLAMP_WIDTHS asked for."""
    return (turns(i) - 1.0) * WRAP_F + 1.0


def exit_angle(i: int) -> float:
    """Where string i's tail leaves the rod -- the TOP tangent, by construction, since
    that is the only place a forward-swept wrap points -X at the clamp."""
    return touch_angle(i) + turns(i) * 2 * math.pi


_EXIT_ERR = max(abs(math.degrees(exit_angle(i)) % 360.0 - 90.0)
                for i in range(D.N_STRINGS))
assert _EXIT_ERR <= 0.01, (
    f"a tail leaves {_EXIT_ERR:.2f} deg off the top tangent -- turns() is meant to "
    f"make that exact, so the derivation has drifted")


MU = 0.15                                       # steel on steel, dry, deliberately pessimistic
STRING_T = 147.0                                # per-string tension the capstan is dividing


def _adv(i: int) -> float:
    """How far string i's coil marches along the rod (always -Y)."""
    return turns(i) * WRAP_F * D.STRING_GAUGE[i]


def residual(i: int) -> float:
    """Tension still left at the clamp after the wrap — what the clamp actually holds."""
    return STRING_T * math.exp(-MU * turns(i) * 2 * math.pi)


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
#     difference  = ROD_D/2 - PIN_D/2 - ROD_Z = 0.621, with no g in it
INS_CLR   = 0.3                                 # Y clearance in its pocket, each side
INS_W     = D.NUT_PITCH - 2 * INS_CLR           # 5.9 wide -- the pitch, less its slip fit
INS_DROP  = 4 * D.BEAD                          # 3.2: how far below its bearing height an
                                                # insert must be able to sit. At the
                                                # NOMINAL height its flat IS the wrap's
                                                # underside, so with the insert there a
                                                # string cannot be wound at all -- it has
                                                # to drop clear of the whole coil first,
                                                # which is a fat string's diameter plus
                                                # room to pass. 3.2 covers the .070 (1.78)
                                                # with margin.
INS_H     = 5 * D.BEAD                          # 4.0 of body below the flat
DIVOT_OFF = ROD_D / 2 - PIN_D / 2 - ROD_Z       # 0.621, cradle centre ABOVE the flat
DIVOT_D   = PIN_D + 0.3                         # 2.3, the dowel's cradle
# The insert reaches from just past the dowel back under the rod, so the flat spans both
# the cradle and the clamp area. It stops short of the trough's -X wall.
INS_X1    = X_FRONT                             # FLUSH with the block's +X face: the
                                                # insert is the last thing at this end, so
                                                # it bears on the deck panel butting it and
                                                # no block prints out over its slot
# ON THE GRID, and rounded the safe way. The derivation is still the trough's own wall,
# so this tracks BAY_R, but ROD_D/2 drags 2.5 into it and the result landed on 13.25
# beads. Rounding UP (toward +X) can only thicken that wall, never thin it.
INS_X0    = math.ceil((ROD_X - BAY_R + D.MIN_WALL) / D.BEAD) * D.BEAD
TAIL_X    = INS_X0                              # where the tail leaves the insert and
                                                # runs on -X to its stow bore


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
INS_STEP_X  = (DOWEL_X + ROD_X) / 2.0           # -3.4, where the plan steps
# Both lobes are the FEATURE plus a hair, not a round number -- the padding is wall
# taken from the neighbour, and at the bass end there is none to spare. 4.3 puts the
# dowel-lobe wall on the 1.6 two-bead target exactly.
INS_LOBE_W  = PIN_L + 0.3                       # 4.3, the dowel lobe


def insert_lobes(i: int):
    """(dowel lobe, clamp lobe) as (y_centre, width) pairs -- the insert's plan."""
    return ((D.nut_y(i), INS_LOBE_W),
            (clamp_y(i), clamp_span(i) + 0.2))


def _plan(i: int):
    """The insert's PLAN: clamp lobe, a 45 deg taper, then the dowel lobe.

    THE SQUARE STEP HAD TO GO (user). Jumping straight from one lobe's Y band to the
    other left a finger face standing in mid-air -- printing -X -> +X the block reaches
    the step and must lay that face with nothing behind it. A 45 deg transition carries
    each layer on the one before, the same rule the comb braces at the bridge end follow.
    The taper runs over whichever side moves further, so the steeper side is exactly 45
    and the other is shallower -- which is the safe direction to err."""
    (dy, dw), (cy, cw) = insert_lobes(i)
    yhd, yld = dy + dw / 2, dy - dw / 2
    yhc, ylc = cy + cw / 2, cy - cw / 2
    run = max(abs(yhd - yhc), abs(yld - ylc))          # 45 deg: Y travel == X run
    x_s = INS_STEP_X
    x_e = min(x_s + run, INS_X1 - 0.01)
    return [(INS_X0, ylc), (x_s, ylc), (x_e, yld), (INS_X1, yld),
            (INS_X1, yhd), (x_e, yhd), (x_s, yhc), (INS_X0, yhc)]


def _plan_wire(i: int):
    return cq.Workplane("XY").polyline(_plan(i)).close()


def slide_insert(i: int) -> cq.Workplane:
    """String i's insert, placed where the string will hold it. `clr` grows it all round,
    which is how the POCKET is cut -- so the pocket is the part's own shape by
    construction and the two cannot drift."""
    fz = insert_flat_z(i)
    (dy, dw), (cy, cw) = insert_lobes(i)
    # the dowel lobe, plus a NECK rising from the flat to the cradle. The flat bears on
    # the wrap far below the dowel now, so the insert has to carry the dowel back up; the
    # neck stops AT the cradle centre, which is a dowel-radius under the crown and so
    # still below the string plane -- nothing of the insert can foul the bar either.
    body = _plan_wire(i).extrude(INS_H).translate((0, 0, fz - INS_H))
    # THE NECK STARTS CLEAR OF THE COIL, not at the lobe's step. The wrap reaches
    # ROD_X + ROD_D/2 + g on its +X side, and a neck beginning further -X than that drives
    # straight through the winding -- 10 mm^3 of it on the .070. So it is set from the
    # coil's own extent, per string, which is also why it moves with the gauge.
    nx0 = ROD_X + ROD_D / 2 + D.STRING_GAUGE[i] + 0.4
    # CLIPPED TO THE PLAN. nx0 sits -X of the taper, where the profile has already
    # narrowed to the clamp lobe -- a neck drawn at the dowel lobe's full width there
    # juts sideways out of its own slot and into the block (10 mm^3 on string 1).
    # Intersecting with the plan means the neck can never exceed the part's footprint,
    # whatever nx0 does as the gauge changes.
    neck = box_at(INS_X1 - nx0, dw, DIVOT_OFF,
                  x=(nx0 + INS_X1) / 2, y=dy, z=fz + DIVOT_OFF / 2)
    body = body.union(neck.intersect(
        _plan_wire(i).extrude(DIVOT_OFF + 2).translate((0, 0, fz - 1))))
    body = body.cut(cyl_y(DIVOT_D, dw + 2, y0=dy - dw / 2 - 1,
                          x=DOWEL_X, z=fz + DIVOT_OFF))
    return body


def insert_pocket(i: int) -> cq.Workplane:
    """The slot string i's insert rises through: its own PLAN, cut clean through the block
    from underside to top face.

    IT HAS TO REACH THE TOP (user). The insert is fitted from below and then rises until
    the string stops it, so anything left capping it does two bad things at once -- it
    limits the travel that makes the whole scheme self-referencing, and it is a ceiling
    over a slot, i.e. an overhang in a part that prints -X -> +X. Running the slot right
    through removes both, and costs nothing: the material over an insert was doing no
    work, since what holds the string down is the ROD, not the block.

    The plan is the part's own, grown by INS_CLR, so pocket and insert cannot drift."""
    # THE POCKET IS THE PART'S OWN PLAN, OFFSET (user). It used to be built from two
    # boxes -- one per lobe -- which squared off the transition the part tapers through,
    # so the block kept a step where the insert has a 45 and printed that face over thin
    # air. Two descriptions of one shape is the bug we keep re-making here; there is only
    # one now, and offsetting it means the slot tracks any future change to the profile
    # for free.
    #
    # offset2D IS A TRUE OFFSET, which matters on the diagonal: padding the Y bounds by
    # INS_CLR moves a 45 deg edge only INS_CLR/sqrt(2) away from itself, so the old
    # rectangles were UNDER-cleared exactly where the taper runs. kind="intersection"
    # extends the edges to meet rather than rounding the corners, so the pocket is the
    # profile grown, not the profile blurred.
    (dy, dw), (cy, cw) = insert_lobes(i)
    fz  = insert_flat_z(i)
    lo  = fz - INS_DROP                     # the flat at its lowest adjustment
    z0  = lo - INS_H - 1.0                  # ...and the body hanging under it
    z1  = NUT_TOP + 1.0
    # a FUNCTION, not a value: extruding a Workplane consumes its pending wires, and
    # this profile is extruded twice.
    grown = lambda: _plan_wire(i).offset2D(INS_CLR, kind="intersection")

    # THE POCKET IS THE PART SWEPT THROUGH ITS TRAVEL, NOT THE PLAN EXTRUDED. Extruding
    # the whole plan the block's full height cut a slot the width of the CLAMP LOBE all
    # the way to the top -- and nothing of the insert is up there. Only the neck is: the
    # body's top face IS the flat, which sits at the block's base plane, so above that the
    # part is a single narrow finger reaching up to the cradle.
    #
    # The cost of the old version was structural, not cosmetic. The clamp lobes are wide
    # and the walls between them are all that is left of the block in a merged bay -- so
    # taking those walls to full height, with the trough having already taken the floor
    # and the sky the roof, left them attached to nothing. Two of them came out as loose
    # 23 mm^3 fragments at the bass end. Cutting only where the part actually goes leaves
    # a band of solid block above the flat that ties every wall back to the end walls.
    body = grown().extrude(fz - z0).translate((0, 0, z0))
    # ...and the neck, from the flat's LOWEST travel right through the top face. Built the
    # same way the part's neck is -- same nx0, clipped to the same profile -- so the two
    # move together; only the clearance differs.
    nx0 = ROD_X + ROD_D / 2 + D.STRING_GAUGE[i] + 0.4 - INS_CLR
    x1 = INS_X1 + INS_CLR
    neck = box_at(x1 - nx0, dw + 2 * INS_CLR, z1 - lo,
                  x=(nx0 + x1) / 2, y=dy, z=(lo + z1) / 2)
    return body.union(neck.intersect(grown().extrude(z1 - lo).translate((0, 0, lo))))


def _lane(i: int):
    """(+Y edge, -Y edge) of string i's coil plus its air. It marches -Y, so the +Y edge
    is where the string arrives and the -Y edge is where its last turn ends."""
    y0, y1 = wrap_y(i)
    g = D.STRING_GAUGE[i]
    return y0 + g / 2 + LANE_CLR, y1 - g / 2 - LANE_CLR


# WHAT A WEB HAS TO BEAT BEFORE IT IS MERGED AWAY. This was MIN_WALL_2P, the two-bead
# quality target, and dropping it to the one-bead FLOOR is a deliberate demotion.
#
# The reason is that merging is not free, which is what the 1.6 rule missed. A web is not
# only a fin standing in a trough -- it is the ONLY thing holding up the wall between two
# insert pockets. The trough clears the whole block height in a merged bay and the two
# pockets take everything either side, so with the web gone that wall is attached to
# nothing at all: it came out as a loose 49 mm^3 fragment between strings 8 and 9, which
# the slicer would have printed as debris rattling around inside the part.
#
# So the trade at s8-s9 is a 0.98 web against no wall. 0.98 is a printable bead, and
# MIN_WALL_2P is the target to PREFER, not a floor to delete material under. Below the
# one-bead floor the fin really is unprintable and the merge is still right: s9-s10's
# lanes actually OVERLAP by 0.33, so that one still merges -- and its wall survives
# anyway, carried round by the web at s8-s9 that this threshold puts back.
#
# It buys back stiffness too, which was not the point but is worth recording: the
# unsupported rod span drops from 22.74 to 16.69 mm and the bending stress with it,
# 102 -> 75 MPa.
WEB_MIN = D.MIN_WALL                            # see bays()


def bays():
    """(-Y, +Y) of each string's threading bay, WITH THIN WEBS MERGED AWAY (user).

    Every coil clears its neighbour with air to spare. What gets tight down at the bass
    end is the material LEFT BETWEEN two lanes: 0.98 mm at s8->s9, and at s9->s10 the
    lanes overlap outright.
    Where a web falls under WEB_MIN the two bays MERGE into one open pocket and the rod
    simply spans it -- but see WEB_MIN for why that threshold is the one-bead floor and
    not the two-bead target: a merged bay costs the WALL BETWEEN THE INSERT POCKETS its
    only support, so merging one web too eagerly leaves loose material behind.

    IT CAN AFFORD TO. The longest run the rod is left to span is 16.69 mm, with the bass
    strings pulling on it: 75 MPa in a hardened 5 mm shaft, a comfortable margin.
    _SPAN_MPA asserts it, so a heavier string set has to re-earn it rather than quietly
    bend the rod."""
    hi = [_lane(i)[0] for i in range(D.N_STRINGS)]
    lo = [_lane(i)[1] for i in range(D.N_STRINGS)]
    for i in range(D.N_STRINGS - 1):
        if lo[i] - hi[i + 1] < WEB_MIN - 1e-9:              # web too thin to print...
            mid = (lo[i] + hi[i + 1]) / 2.0
            lo[i] = hi[i + 1] = mid                         # ...so there is no web at all
    return [(lo[i], hi[i]) for i in range(D.N_STRINGS)]


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


def rod_span() -> tuple[float, float]:
    """(y0, y1) the rod has to cover: every bay plus a bearing length in the end walls."""
    lo = min(_lane(i)[1] for i in range(D.N_STRINGS))
    return lo - 2 * D.BEAD, D.nut_y(0) + 2 * D.BEAD


ROD_Y0, ROD_Y1 = rod_span()
ROD_END_W = D.MIN_WALL_2P                       # the +Y bore is BLIND; that wall is the stop
# THE BLOCK IS NOW AS WIDE AS THE WRAP FIELD, not as wide as the clamp field. The .070
# marches 6.53 mm OUTWARD past the last string -- that free air is exactly what buys it
# 3.5 turns -- so the -Y end of the rod lands 0.12 outside the old half-width. Take the
# wider of the two requirements and put the surplus on the bead grid, so the block grows
# by whole beads rather than by whatever the gauge table happens to ask for.
# The block reaches the OUTERMOST INSERT plus a wall. It used to be sized from the
# clamp inserts' O6 pockets, which no longer exist.
Y_WALL    = 8.0                                 # outer wall past the last insert
_HW_CLAMP = D.nut_y(0) + INS_LOBE_W / 2 + Y_WALL
_HW_NEED = max(_HW_CLAMP, ROD_END_W - ROD_Y0)
HW = D.nut_y(0) + math.ceil((_HW_NEED - D.nut_y(0)) / D.BEAD - 1e-9) * D.BEAD
assert ROD_Y0 - ROD_END_W >= -HW, "the rod's -Y end has run out of block to sit in"

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

GROOVE_W = 1.8
ROOF_CLR = 0.8
BREAK_ANGLE = 10.0                              # MIN break angle over the dowel, so the DOWEL
                                                # (not the rod) terminates the speaking length


def _break_deg(i: int) -> float:
    """Down-angle string i takes as it leaves the break dowel, running to where it first
    TOUCHES the wrap circle on the rod's underside."""
    # TRUE TANGENCY, not the chord to the circle's lowest point. The chord is
    # gauge-independent (the -g/2 at the dowel and the +g/2 in the wrap radius cancel),
    # which is a pleasing result and the WRONG one -- the string follows the tangent, and
    # that depends on the wrap radius, so it does vary with gauge. Only slightly: ~0.1 deg
    # across the set. But sizing ROD_Z off the chord lands the real angle ~0.5 deg
    # steeper than intended, which matters when the target is chosen for margin.
    g = D.STRING_GAUGE[i]
    hr = ROD_D / 2 + g / 2                                # the string's centre-path radius
    dx = DOWEL_X - ROD_X                                  # dowel -> rod axis
    dz = -g / 2 - ROD_Z                                   # (negative: the rod sits above)
    d = math.hypot(dx, dz)
    # The rod axis sits ABOVE the dowel, so the line to it RISES; the tangent to the
    # underside lies asin(hr/d) BELOW that line. Subtract -- adding gives the upper
    # tangent, i.e. a string wrapping over the top, which is the arrangement we left.
    # UPPER tangent: the rod sits BELOW the dowel now, so the line to its axis DESCENDS
    # and the tangent lies asin(hr/d) shallower than that line. (This read the lower
    # tangent while the rod was above -- the same formula gives 56-59 deg here, which is
    # what a stale sign looks like rather than a real break.)
    return math.degrees(math.atan2(dz, dx)) - math.degrees(math.asin(hr / d))


_WORST_BREAK = min(_break_deg(i) for i in range(D.N_STRINGS))
assert _WORST_BREAK >= BREAK_ANGLE - 1e-9, (
    f"the worst string breaks over the dowel at only {_WORST_BREAK:.1f} deg (floor "
    f"{BREAK_ANGLE}) — at that angle the ROD, not the dowel, sets the scale length")


def _gw(i: int) -> float:
    """Gauged channel width — each string lays in and centres itself."""
    return max(D.STRING_GAUGE[i] + 0.8, 1.4)


def _dowel_pocket(seat_z, y):
    """The break dowel's seat, as a solid to CUT. A round cradle cups it from BELOW so
    gravity retains it, wrapping 90° up the -X side to a vertical wall but only 45° up
    the +X side -- a steeper +X wall would be a print overhang in the -X -> +X build --
    then opening at 45° out to the +X face, which is also how the dowel drops in."""
    R = PIN_SEAT_D / 2.0
    s = R * math.sin(math.radians(45.0))
    z_face = seat_z + X_FRONT - 2.0 * s
    prof = (cq.Workplane("XZ")
            .moveTo(-R, NUT_TOP)
            .lineTo(-R, seat_z)
            .threePointArc((0.0, seat_z - R), (s, seat_z - s))
            .lineTo(X_FRONT, z_face)
            .lineTo(X_FRONT, NUT_TOP)
            .close())
    return prof.extrude(PIN_SEAT_L / 2.0, both=True).translate((0.0, y, 0.0))


BAY_D = 2 * BAY_R                               # 10.0 — ONE trough diameter for all ten

# ── WORK IN PROGRESS: THE DOWEL ZONE IS BARE PRISM (user) ──────────────────
# False switches off every cut +X of the troughs -- the two entry channel runs, the
# dowel cradle, and the two seat-wall trims -- leaving that region as the solid prism it
# started as. It is the starting point the +Z half of this block is being rebuilt from,
# and the reason is that those four cuts were each derived from a DIFFERENT datum (the
# gauged pin height, the channel floor, the dowel crown, the bay ramp), which is what
# made them hard to reason about together.
#
# Everything -X of the troughs is untouched and still cut: the exit passages and the
# clamp bores (user).
#
# Switched off rather than deleted, so the derivations survive to be reused or
# consciously discarded -- _dowel_pocket, _seat_wall_top and _seat_wall_lead are all
# still below, unused.
#
# NO STRING CAN BE TERMINATED IN THIS STATE: nothing holds a break dowel and there is no
# path from the bridge into a trough. Do not read a clean gate as a working part.
_EXTRA_CUTS = False


# ── STRING SLOT: the whole +X end opens down to under the strings (user) ───
# Everything +X of the axle is cleared across the FULL width -- no per-string lanes and
# no fingers, one rectangular slot -- from just clear of the axle bore out to the +X face.
#
# ITS -X EDGE IS THE AXLE TEARDROP'S TIP, not the bore's centre or its Ø5.4 wall. The
# teardrop's apex points +X (the build direction), so the bore actually reaches
# ROD_BORE/2 * sqrt(2) = 3.82 from the axis, and cutting to anything less would have left
# a sliver of the tip standing in the slot.
#
# ITS FLOOR IS THE THICKEST STRING'S UNDERSIDE, less the same clearance. One slot serves
# ten strings, so the floor is set by the lowest of them: the .070 hangs to -1.78 and
# every thinner string clears by more.
_APEX      = math.sqrt(2.0)                          # cadkit teardrop apex, in radii
SLOT_KEEP  = D.MIN_WALL_2P                           # 1.6, clearance off the bore's tip
AXLE_APEX  = ROD_X + ROD_BORE / 2 * _APEX            # the bore's real +X reach
SLOT_X0    = AXLE_APEX + SLOT_KEEP                   # clear of the bore's tip
STRING_BOT = -max(D.STRING_GAUGE)                    # -1.78, the .070's underside
SLOT_Z0    = STRING_BOT - SLOT_KEEP                  # the slot floor
assert SLOT_X0 > AXLE_APEX, "the string slot would clip the axle bore's teardrop tip"
assert SLOT_Z0 < NUT_TOP, "the string slot is shallower than the block it cuts"


def _bay_trough(y0: float, y1: float) -> cq.Workplane:
    """The threading trough: ONE shape, cut the same way for every string (user).

    It is a cadkit TEARDROP BORE along Y -- the same profile, from the same helper, as the
    axle bore it surrounds. That is the point of doing it this way: the trough and the hole
    through it are the same construction, so they cannot drift apart, and the trough is
    printable by the same argument that makes any teardrop printable rather than by a
    hand-built 45 that has to be re-argued whenever a gauge moves.

    ONE DIAMETER, sized on the WORST case -- string 10's winding needs
    ROD_D/2 + g + g/2 = 4.28 of radius, so BAY_D's 5.0 clears it -- and then every string
    gets that same trough regardless of its own gauge. Uniform beats optimal here: it is
    the difference between one number to check and ten.

    WHERE IT IS APPLIED comes from bays(): one window spanning strings 8-10, where the
    coils have already merged into a single pocket, and a separate window per string for
    1 through 7. What is left between those windows is the material the axle fingers are
    cut from."""
    return teardrop_hole(BAY_D, y1 - y0,
                         axis_point=(ROD_X, y0, ROD_Z),
                         axis_dir=(0.0, 1.0, 0.0), print_up=PRINT_UP)


DOWEL_CLR = 0.15                                # all round the dowel (user)
DOWEL_BORE_D = PIN_D + 2 * DOWEL_CLR            # 2.30
DOWEL_BORE_L = PIN_L + 2 * DOWEL_CLR            # 4.30


def _all_dowels() -> cq.Workplane:
    """One cylinder per break dowel: the dowel's own geometry grown by DOWEL_CLR on every
    face (user), so 0.3 on both the diameter and the length.

    GAUGED, as the dowels always were: each sits at -g - PIN_D/2, which puts its crown at
    -g and therefore every string's TOP on one plane at z=0. That is the whole reason
    there are ten of them instead of one shared rod."""
    out = None
    for i in range(D.N_STRINGS):
        pin_z = -D.STRING_GAUGE[i] - PIN_D / 2
        c = cyl_y(DOWEL_BORE_D, DOWEL_BORE_L, y0=D.nut_y(i) - DOWEL_BORE_L / 2,
                  x=DOWEL_X, z=pin_z)
        out = c if out is None else out.union(c)
    return out


def _all_skies() -> cq.Workplane:
    """Open every lane to the sky, from the ROD'S CENTRE-PLANE up. Fused, cut once.

    This is what removes the beams the trough left behind -- the wedges standing between
    each trough's crown and the cap -- and the rule is chosen so they cannot come back:

        ROD_Z IS THE TROUGH'S WIDEST POINT. An opening that starts at the widest point of
        the shape below it can never narrow going up, so nothing spans the lane and there
        is no overhang to argue about. Cut from any higher and the trough's own crown
        closes over the opening; cut from lower and material is spent for nothing.

    ITS -X EDGE IS THE TEARDROPS' CENTRE (user), i.e. the rod axis, not the trough's -X
    wall: the lane opens over the +X half only and the -X half keeps its roof.

    The FINGERS are untouched -- they sit between lanes, keep their full height, and are
    what still captures the rod, since their material stands above the bore's top (0.30)
    up to the cap at 1.90. So the rod cannot lift out even though its lane is open."""
    out = None
    for i in range(D.N_STRINGS):
        y0, y1 = bays()[i]
        k = box_at(X_FRONT - ROD_X, y1 - y0, (NUT_TOP + 1.0) - ROD_Z,
                   x=(ROD_X + X_FRONT) / 2, y=(y0 + y1) / 2,
                   z=(ROD_Z + NUT_TOP + 1.0) / 2)
        out = k if out is None else out.union(k)
    return out


def all_pockets() -> cq.Workplane:
    """Every insert's slot, FUSED and subtracted once -- the same lesson the troughs
    taught: ten short booleans against a body this busy left cores behind, one fused
    cutter does not."""
    out = None
    for i in range(D.N_STRINGS):
        k = insert_pocket(i)
        out = k if out is None else out.union(k)
    return out


def _all_troughs() -> cq.Workplane:
    """Every string's trough, FUSED into one cutter. The merged 8-10 window comes out as
    one continuous solid because those lanes already share their boundaries."""
    out = None
    for i in range(D.N_STRINGS):
        t = _bay_trough(*bays()[i])
        out = t if out is None else out.union(t)
    return out


def _seat_wall_lead(i: int) -> cq.Workplane:
    """45 deg lead-in on the -X END of the wall between seats i and i+1.

    The bay ramp carries the print up to the channel floor, but the seat walls stand 2.4
    higher than that -- up to their dowel's crown -- and that last 2.4 would still start in
    mid-air at the bay wall. So the wall's -X end slopes up at 45 deg over the same 2.4,
    landing on the ramp rather than on nothing. It costs the wall its -X corner, where it
    was doing the least: the dowel it blocks sits at x=0, a millimetre further in."""
    z_r = ROD_Z - max(D.STRING_GAUGE[i], D.STRING_GAUGE[i + 1])     # meets the bay ramp
    crown = -max(D.STRING_GAUGE[i], D.STRING_GAUGE[i + 1])          # the wall's own top
    x_p = ROD_X + BAY_R
    x_e = x_p + (crown - z_r)                                        # 45 deg -> 2.4 of run
    y_hi = D.nut_y(i) - PIN_SEAT_L / 2
    y_lo = D.nut_y(i + 1) + PIN_SEAT_L / 2
    prof = (cq.Workplane("XZ")
            .polyline([(x_p, z_r), (x_e, crown),
                       (x_e, NUT_TOP + 1.0), (x_p, NUT_TOP + 1.0)])
            .close())
    return prof.extrude((y_hi - y_lo) / 2.0, both=True).translate(
        (0.0, (y_hi + y_lo) / 2.0, 0.0))


def _seat_wall_top(i: int) -> cq.Workplane:
    """Takes the top off the wall between dowel seats i and i+1 (user).

    That wall is 1.7 thick -- 6.5 of pitch less the 4.8 the seats take -- and it used to
    run the block's full height, ~9 mm of it. Thickness was never the problem; the ASPECT
    RATIO was. Its whole job is to stop a loose Ø2 pin walking along Y, so it only has to
    reach the pin's crown, and everything above that was a tall thin fin holding nothing.

    HEIGHT IS PER WALL, because the dowels are GAUGED: each sits at -g - PIN_D/2 so that
    every string TOP lands on one plane, which puts each crown at -g. A wall touches two
    dowels at two different heights, so it is cut to the LOWER crown -- i.e. the THICKER
    string's, max(g). Cut to the higher one it would stand proud of its own neighbour for
    no reason; cut lower it would stop covering the pin it is meant to block.

    Only spans the DOWEL ZONE (the bay's +X edge out to the +X face). The comb webs at the
    rod are untouched -- those carry the rod and are the one thing in here that is
    structural."""
    # THE MIDPOINT, NOT THE CROWN (user). The wall used to run up to the dowel's top; it
    # only has to reach the dowel's CENTRELINE. A cylinder cradled to its own mid-height
    # cannot roll out sideways -- it can only lift -- and the string lies across it, plus
    # a dab of glue holds it during restringing before the string is on. That last 1.0 mm
    # was buying nothing and it is what made these read as thin triangles hugging each
    # string. Still the LOWER of the two dowels, for the reason below.
    z_top = -max(D.STRING_GAUGE[i], D.STRING_GAUGE[i + 1]) - PIN_D / 2
    y_hi = D.nut_y(i) - PIN_SEAT_L / 2                          # the seats' facing edges
    y_lo = D.nut_y(i + 1) + PIN_SEAT_L / 2
    x0 = ROD_X + BAY_R
    return box_at(X_FRONT - x0, y_hi - y_lo, (NUT_TOP + 1.0) - z_top,
                  x=(x0 + X_FRONT) / 2, y=(y_hi + y_lo) / 2,
                  z=(z_top + NUT_TOP + 1.0) / 2)


def _build() -> cq.Workplane:
    # ONE solid prism, the endplate footprint, and every feature is CUT from it.
    body = box_at(X_FRONT - X_BACK, 2 * HW, NUT_TOP - NUT_BASE,
                  x=(X_FRONT + X_BACK) / 2, y=0, z=(NUT_TOP + NUT_BASE) / 2)

    for i in range(D.N_STRINGS):
        y0, y1 = wrap_y(i)
        g = D.STRING_GAUGE[i]
        gw = _gw(i)
        pin_z = -g - PIN_D / 2                  # dowel centre: its top at -g, string top at 0
        seat_z = pin_z + PIN_CLR                # seat raised so its BOTTOM is flush with the
                                                # dowel's -- no Z slop under the gauge datum
        # ── STRIPPED BACK TO PRISM + TROUGHS (user, in progress) ──────────────────
        # See _EXTRA_CUTS. Everything except the prism, the ten teardrop troughs and the
        # rod bore is switched off: the entry channels, the dowel cradle, the seat-wall
        # trims, the exit passage and the clamp bores.
        if _EXTRA_CUTS:
            body = body.cut(box_at(X_FRONT - (-PIN_D / 2), gw, ROOF_CLR - pin_z,
                                   x=(X_FRONT + -PIN_D / 2) / 2, y=y0,
                                   z=(ROOF_CLR + pin_z) / 2))
            body = body.cut(box_at((-PIN_D / 2) - (ROD_X + BAY_R), gw, ROOF_CLR - (ROD_Z - g),
                                   x=((-PIN_D / 2) + (ROD_X + BAY_R)) / 2, y=y0,
                                   z=(ROOF_CLR + ROD_Z - g) / 2))
            body = body.cut(_dowel_pocket(seat_z, y0))
            if i + 1 < D.N_STRINGS:
                body = body.cut(_seat_wall_top(i))
                body = body.cut(_seat_wall_lead(i))

        # (the troughs are cut ONCE, after this loop -- see _all_troughs)

        # EXIT: the tail leaves the rod's -Z TANGENT at the coil's far end and runs
        # STRAIGHT out the back face at that same height -- no bend at all now the wrap
        # is on the underside. tail_z is where the string actually is, so the passage and
        # the clamp below both hang off it rather than off the rod's centre.
        tail_z = ROD_Z + (ROD_D / 2 + g / 2)      # the TOP tangent -- see exit_angle
        body = body.cut(box_at((ROD_X - BAY_R) - X_BACK, gw, gw,
                               x=(X_BACK + ROD_X - BAY_R) / 2, y=y1, z=tail_z))
        # ANVIL: a second Ø2 dowel under the tail at the clamp, so the pinch is
        # metal-on-metal and the plastic floor is not the thing being squeezed.
        # (no clamp bores: the sliding insert IS the clamp now)

    # THE TROUGHS, FUSED AND SUBTRACTED ONCE (user). Ten separate short booleans against
    # a body already carrying this many nearby features left a CORE behind in the two
    # narrowest lanes -- strings 1 and 2 came out with a ~135 mm^3 island sitting inside
    # their own trough, smaller than the cutter that should have removed it, which is the
    # signature of a tolerance artifact rather than a wrong shape (the cutters themselves
    # all probe as single valid solids scaling cleanly with lane length). One fused cutter
    # and one subtraction is both more robust numerically and closer to what this geometry
    # is meant to BE: the same trough everywhere, made once.
    body = body.cut(_all_troughs())

    # ...and the slots the INSERTS rise through, cut from the parts' own profiles so the
    # pocket cannot drift from the thing it has to accept.
    body = body.cut(all_pockets())

    body = body.cut(_all_dowels())

    # ...and open each lane to the sky above the rod's centre-plane, which is what stops
    # a beam being left between the trough's crown and the cap. Fused and cut once, for
    # the same reason the troughs are.
    body = body.cut(_all_skies())

    # STRING SLOT: full width, axle tip out to the +X face, down to under the strings.
    body = body.cut(box_at(X_FRONT - SLOT_X0, 2 * HW + 2.0, (NUT_TOP + 1.0) - SLOT_Z0,
                           x=(SLOT_X0 + X_FRONT) / 2, y=0.0,
                           z=(SLOT_Z0 + NUT_TOP + 1.0) / 2))

    # THE ROD BORE, cut LAST so none of the unions above can refill it (the bridge end
    # lost both its axle bores exactly that way). BLIND at +Y: that wall is the rod's +Y
    # stop, the same trick the bridge axle uses. It slides in from -Y through all ten
    # comb webs at once, so it must be a precision shaft and not a dowel.
    body = body.cut(teardrop_hole(ROD_BORE, (ROD_Y1 - ROD_Y0) + 20.0,
                                  axis_point=(ROD_X, ROD_Y0 - 20.0, ROD_Z),
                                  axis_dir=(0.0, 1.0, 0.0), print_up=PRINT_UP))
    return body


def rod() -> cq.Workplane:
    """The wrap rod itself, in the nut block's local frame — the bridge axle's shaft."""
    return cyl_y(ROD_D, ROD_Y1 - ROD_Y0, y0=ROD_Y0, x=ROD_X, z=ROD_Z)


nut_block = _build()
