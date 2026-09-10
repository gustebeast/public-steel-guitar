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

ROD_D = D.NUT_WRAP_ROD_D                        # Ø5 (was the bridge axle's stock until that went Ø8)
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
# TWO ZONES, TWO SKUS:
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
# that cannot pay it. The cost is the rod's longest unsupported run, 16.7 -> 24.8 mm:
# 111 MPa and 0.014 mm of sag in a hardened Ø5 shaft, against the 250 MPa this module
# asserts. Three strings over 25 mm is not much load for that section.
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
# WHERE THE TAIL LEAVES, AND IT IS NO LONGER THE TOP (user). Sweeping forward the
# tangent at phi is (-sin phi, cos phi): at 90 that is straight -X, which is what the old
# -X exit channel wanted. Carrying on to 135 points the tail -X AND DOWN at 45, which is
# what the new channel wants -- it leaves the rod already descending, so the passage can
# start as a 45 cut and bend to vertical without the string ever having to turn a corner
# it is not already turning.
# WHERE THE TAIL LEAVES, AND IT IS QUANTISED BY THE CLAMP. The wrap is the entry sweep
# plus a WHOLE number of turns, so the exit angle picks the fraction -- and the fraction
# decides whether the whole turn count that meets CLAMP_WIDTHS is 2 or 3.
#
# It must ALSO leave heading -X and NOT DOWNWARD, because the tail's route to its stow
# bore is up out of the socket, over the wall and down the hole (see stow_route). That
# rules out the old 135, which left the rod descending because the passage used to start
# there and bend; with a straight vertical bore there is nothing to descend into.
#
# Those two together are a narrow window, and the numbers are worth keeping:
#
#     exit    turns          widths       climbs?
#      45     3.81..3.83     3.95..3.98   yes  -- a whole extra wrap on every string
#      75     2.91..3.90     3.00..4.05   yes  -- k splits across the set
#      85     2.92..2.94     3.02..3.04   yes  <- here
#      90     2.94..2.96     3.03..3.06   NO   -- leaves dead horizontal
#     135     3.06..3.08     3.16..3.19   NO   -- leaves descending
#
# Anything under about 75 costs a full extra turn, which the bass lanes cannot pay for;
# anything from 90 on stops climbing.
EXIT_DEG = 85.0                                 # -X, and just above horizontal

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
def _sweep0(i: int) -> float:
    """Turns from where the string touches the rod round to the exit tangent."""
    return ((math.radians(EXIT_DEG) - touch_angle(i)) % (2 * math.pi)) / (2 * math.pi)


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
    need = 1.0 + (CLAMP_WIDTHS - 1.0) / WRAP_F
    return max(1, math.ceil(need - _sweep0(i) - 1e-9))


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
    """Turns for string i: the most WHOLE wraps its lane will take, never under _K_MIN,
    landing the tail on the exit tangent by construction.

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


def clamp_widths(i: int) -> float:
    """Contact at the clamp, in string widths -- what CLAMP_WIDTHS asked for."""
    return (turns(i) - 1.0) * WRAP_F + 1.0


def exit_angle(i: int) -> float:
    """Where string i's tail leaves the rod -- EXIT_DEG, by construction, since turns()
    is built as the entry sweep plus a whole number of revolutions."""
    return touch_angle(i) + turns(i) * 2 * math.pi


def exit_point(i: int):
    """(x, z) where string i's tail leaves the rod, in the block's local frame. THE ONE
    PLACE THIS IS COMPUTED -- build.py used to derive it from its own wrap radius, which
    differed from this one by 0.05 and left every tail starting inside its own coil."""
    a = exit_angle(i)
    hr = wrap_radius(i)
    return ROD_X + hr * math.cos(a), ROD_Z + hr * math.sin(a)


def stow_route(i: int, z_end: float):
    """The tail's route from the rod to the bottom of its stow bore, as (x, z) points.

    UP, OVER, DOWN -- and the 'over' is the point of it. The socket and the bore both open
    at the block's upper face and the wall between them stops at NUT_TOP, so the wound end
    leaves the rod climbing, clears that wall, and drops into the hole. There is no
    passage joining the two below the top face and there does not need to be one: the tail
    is cut to length and fed in by hand."""
    x0, z0 = exit_point(i)
    ex, ez = exit_dir(i)
    assert ez > 1e-6, (
        f"the tail leaves string {i + 1} descending (EXIT_DEG {EXIT_DEG:.0f}), so it "
        f"cannot climb over the wall into its stow bore")
    z_over = NUT_TOP + D.MIN_WALL_2P             # clear of the block's upper face
    stub = 3.0                                   # a little of the tangent before it bends
    return [(x0, z0),
            (x0 + ex * stub, z0 + ez * stub),    # off the rod on its own tangent...
            (STOW_X, z_over),                    # ...then bent up over the wall by hand
            (STOW_X, z_end)]                     # and down the bore


def exit_dir(i: int):
    """Unit (x, z) the tail is travelling as it leaves. Forward sweep, so the tangent at
    phi is (-sin phi, cos phi) -- at EXIT_DEG 135 that is -X and 45 deg down."""
    a = exit_angle(i)
    return -math.sin(a), math.cos(a)


_EXIT_ERR = max(abs(math.degrees(exit_angle(i)) % 360.0 - EXIT_DEG)
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
INS_CLR   = 0.2                                 # Y clearance in its pocket, each side
                                                # (0.3 before: see TAPER_TAN, where every
                                                # 0.1 of it comes straight off the wall
                                                # between neighbouring pockets)
INS_W     = D.NUT_PITCH - 2 * INS_CLR           # 5.9 wide -- the pitch, less its slip fit
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
# DERIVED, and it lands on the 3.2 it was already set to -- but as a number that moves if
# the string set does, instead of a round one justified after the fact.
THREAD_CLR = D.MIN_WALL                         # room to work the string round, not force it
# ...and the 45 deg lead-ins that get it there: a full thickest-gauge diameter, so a fat
# string meets the chamfer before it can reach the square corner behind it.
THREAD_LEAD = math.ceil(max(D.STRING_GAUGE) / D.BEAD) * D.BEAD    # 2.4
_DROP_NEED = max(D.STRING_GAUGE) + THREAD_CLR   # 2.578 for the .070
INS_DROP  = math.ceil(_DROP_NEED / D.BEAD) * D.BEAD          # 3.2, on the grid
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
# -X END: far enough back to clear the fattest winding, on the grid, rounded the safe
# way (DOWN, i.e. -X: rounding the other way would pinch the coil).
INS_X0    = math.floor((ROD_X - ROD_D / 2 - max(D.STRING_GAUGE) - D.MIN_WALL)
                       / D.BEAD) * D.BEAD
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
INS_STEP_X  = (DOWEL_X + ROD_X) / 2.0           # (unused: the step is derived in _plan)
# Both lobes are the FEATURE plus a hair, not a round number -- the padding is wall
# taken from the neighbour, and at the bass end there is none to spare. 4.3 puts the
# dowel-lobe wall on the 1.6 two-bead target exactly.
INS_LOBE_W  = PIN_L + 0.3                       # 4.3, the dowel lobe
CRADLE_L  = INS_LOBE_W                          # the trough is the DOWEL LOBE's width,
                                                # anchored on that lobe's +Y edge -- see
                                                # slide_insert. Cutting it to PIN_L + a
                                                # float instead leaves a 0.05 rind of
                                                # insert standing at the lobe's edge,
                                                # which is a sliver on both SKUs.



# SKU B's insert is a PITCH WIDE and butts its neighbours. That is what replaces the
# walls it no longer has: the three are located by the s7 finger on one side, the end
# wall on the other, and each other in between. STACK_CLR is deliberately far tighter
# than INS_CLR -- it is a flat sliding on a flat in Z only, the easiest fit there is, and
# every 0.1 of it lands as string-spacing error at the dowel. At 0.1 the worst a single
# dowel can sit off its lane is 0.3 mm even if the whole stack piles one way.
#
# BOTH ITS LOBES ARE FULL WIDTH, which is the part that stops the debris coming back. A
# narrow dowel lobe would leave 2.2 mm of block standing between each pair of bass
# inserts, and in a shared bay that material has a trough under it, a sky over it and a
# pocket either side -- exactly the floating fragment this whole change is removing. Full
# width, they abut, and there is nothing left between them to come loose.
STACK_CLR = 0.1                                 # total Y slip in the shared slot
BASS_W    = D.NUT_PITCH - STACK_CLR             # 6.4: they touch
BASS_CLR  = STACK_CLR / 2 + 0.01                # per side; the +0.01 makes neighbouring
                                                # pockets OVERLAP rather than share a
                                                # face, so their union is one clean
                                                # opening instead of a coincident-face
                                                # boolean
BASS_OFF  = 0.4                                 # the clamp lobe's +Y edge above nut_y:
                                                # low enough to cover the deepest bass
                                                # coil, high enough to abut the neighbour


def _clr(i: int) -> float:
    """Pocket clearance for string i -- the two SKUs are fitted differently."""
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


def insert_lobes(i: int):
    """(dowel lobe, clamp lobe) as (y_centre, width) pairs -- the insert's plan.

    SKU A's clamp lobe is THE LANE, less its pocket clearance -- not the coil. Sizing it
    to the coil is what made every insert a different part; sizing it to the window makes
    them all the same one, and the window is guaranteed to contain the coil because
    turns() is what fits the coil into it."""
    if i < N_FINGERED:
        return ((D.nut_y(i), INS_LOBE_W), (D.nut_y(i) + CLAMP_C, CLAMP_W))
    # SKU B's dowel lobe is OFFSET -Y, not centred. Centred, a 6.4 lobe reaches 3.2 past
    # the string and left string 7 a 0.79 wall (user). It only has to CONTAIN the dowel,
    # so it is hung from just clear of the dowel's own end and runs -Y from there: the
    # bass three still abut each other, and s7 gets its 1.6 back.
    return ((D.nut_y(i) + INS_LOBE_W / 2 - BASS_W / 2, BASS_W),
            (D.nut_y(i) + BASS_OFF - BASS_W / 2, BASS_W))


def _plan(i: int):
    """The insert's PLAN: clamp lobe, a 45 deg taper, then the dowel lobe.

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


def _plan_wire(i: int):
    return cq.Workplane("XY").polyline(_plan(i)).close()


NECK_CLR_X = 0.4                                # air +X of the coil, before the neck


def _neck_x0(i: int) -> float:
    """Where string i's neck starts. The wrap reaches ROD_X + ROD_D/2 + g on its +X side
    and anything -X of that drives through the winding, so the neck starts from the COIL's
    own extent and moves with the gauge. THE ONE PLACE THIS IS COMPUTED."""
    return ROD_X + ROD_D / 2.0 + D.STRING_GAUGE[i] + NECK_CLR_X


# ── HOW BIG THE THREADING RAMPS MAY BE ─────────────────────────────────────
# They are added material sitting right where the coil does, so their size is not a taste
# question: each is the largest 45 deg ramp that still clears EVERY string's wound
# envelope by RAMP_CLR. Both limits fall out of string 10, whose coil is fattest and whose
# flat therefore sits lowest.
RAMP_CLR = 0.4                                  # air between a ramp and a wound string


def _ramp_fits(L: float, x0: float, sgn: float, i: int) -> bool:
    """Does a 45 deg ramp of rise L, running sgn from x0, clear string i's coil?"""
    g = D.STRING_GAUGE[i]
    r = ROD_D / 2.0 + g                          # the wound coil's outer envelope
    fz = insert_flat_z(i)
    for k in range(41):
        t = k / 40.0
        dx = (x0 + sgn * L * t) - ROD_X
        if abs(dx) >= r:
            continue
        if fz + L * (1.0 - t) > ROD_Z - math.sqrt(r * r - dx * dx) - RAMP_CLR:
            return False
    return True


def _max_ramp(x0_of, sgn: float) -> float:
    """The biggest such ramp that suits all ten, snapped DOWN to the bead grid."""
    worst = 99.0
    for i in range(D.N_STRINGS):
        lo, hi = 0.0, 8.0
        for _ in range(40):
            mid = (lo + hi) / 2.0
            lo, hi = (mid, hi) if _ramp_fits(mid, x0_of(i), sgn, i) else (lo, mid)
        worst = min(worst, lo)
    return math.floor(worst / D.BEAD) * D.BEAD


RAMP_END  = _max_ramp(lambda i: INS_X0, +1.0)   # at the flat's -X end
RAMP_NECK = _max_ramp(_neck_x0, -1.0)           # at the neck's foot


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
    nx0 = _neck_x0(i)
    # THE NECK FILLS THE WHOLE PLAN, not just the dowel lobe's width (user). It used to be
    # a box the width of the dowel lobe, clipped to the plan -- so everywhere the plan is
    # WIDER than that box (the taper, and the clamp lobe on the bass strings, which is the
    # wider of the two there) the insert stepped down to the flat and left a notch.
    #
    # There was never a reason for it: the pocket is the plan extruded, so that notch was
    # empty slot, not clearance for anything. Filling it is free material exactly where the
    # part is weakest -- the neck is 8.11 tall standing on a 4.00 body -- and it puts the
    # insert's own profile alongside the block's ramp instead of a step floating over it.
    #
    # ITS -X FACE IS STILL nx0, WHICH IS THE ONE THING HERE THAT IS NOT FREE. The wrap
    # reaches ROD_X + ROD_D/2 + g on its +X side, and anything -X of that drives through
    # the winding (10 mm^3 of it on the .070 when this was a plain box). So the neck starts
    # from the COIL's own extent, per string, and moves with the gauge.
    neck = (_plan_wire(i).extrude(DIVOT_OFF).translate((0, 0, fz))
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
    # It stays open at the TOP: the cradle centre IS the neck's top face, so the cut
    # leaves a half-round and the dowel drops straight in.
    y_hi = dy + dw / 2.0
    body = body.cut(cyl_y(DIVOT_D, CRADLE_L, y0=y_hi - CRADLE_L,
                          x=DOWEL_X, z=fz + DIVOT_OFF))

    # ── TWO 45 DEG LEAD-INS FOR THREADING (user) ──────────────────────────
    # The flat meets the insert's -X end face, and it meets the neck's -X face, at square
    # corners, and a string worked round the axle has to get past both. They are RAMPS
    # ADDED, not chamfers cut.
    #
    # I built them as cuts first and that was exactly backwards: a chamfer cut into a
    # corner does not remove the corner, it replaces it with a POCKET -- a notch the
    # string end drops into and will not come back out of (user). Filling the corner gives
    # the string a face to ride up; cutting it gives the string somewhere to hide.
    #
    # SIZED SO THEY CANNOT TOUCH A WOUND STRING, which is the constraint that matters once
    # they are material rather than air. See RAMP_END and RAMP_NECK.
    #
    # Clipped to the plan, so neither can escape the silhouette the socket is cut from.
    keep = (_plan_wire(i).extrude(DIVOT_OFF + INS_H + 2.0)
            .translate((0, 0, fz - INS_H - 1.0)))
    for x0, run in ((INS_X0, +RAMP_END), (nx0, -RAMP_NECK)):
        ramp = (cq.Workplane("XZ")
                .polyline([(x0, fz), (x0 + run, fz), (x0, fz + abs(run))]).close()
                .extrude(2 * HW).translate((0.0, HW, 0.0)))
        body = body.union(ramp.intersect(keep))
    return body


# ONE POCKET DEPTH FOR ALL TEN (user). It used to come off insert_flat_z, which carries
# the gauge -- the flat is ROD_Z - ROD_D/2 - g, so a thick string's insert rides lower and
# its pocket was cut deeper. Strings 8-10 came out visibly deeper than the rest.
#
# It is measured from the UNINSTALLED position (user): far enough down that a thick gauge
# string can be threaded between the flat and the coil already on the rod. See INS_DROP.
POCKET_Z0 = (ROD_Z - ROD_D / 2.0 - max(D.STRING_GAUGE)   # the lowest flat any string sets
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
    the part's full X/Y extent, and offsetting it is enough. offset2D is a TRUE offset,
    which matters on the diagonal: padding the Y bounds instead would move a 45 deg edge
    only INS_CLR/sqrt(2) away from itself and under-clear the taper exactly where the part
    is tightest. kind="intersection" extends the edges to meet rather than rounding the
    corners, so the slot is the profile grown, not the profile blurred."""
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
    lo = min(_lane(i)[1] for i in range(N_FINGERED, D.N_STRINGS))
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


# ── THE RAMP CARRIES ON (user) ─────────────────────────────────────────────
# The trough's teardrop puts a 45 deg flank under each lane, rising toward +X and ending
# at the apex. The sky cut used to flatten everything off at ROD_Z from there to the
# face, which threw away the one thing that ramp was good for: every millimetre of height
# it reaches +X of the trough is another millimetre of GUIDE around the insert sliding
# through it. So the ramp simply keeps going at the same 45, and the sky's floor follows
# it rather than cutting across it.
#
# IT FLATTENS OFF 0.8 SHORT OF THE FACE (user). Run at 45 right up to the +X face and the
# material arrives as a feather edge -- a corner thinner than the nozzle can lay, which
# prints as a ragged lip on the face the inserts bear against. One bead of flat gives that
# edge a thickness the slicer can actually build.
#
# Nothing is ADDED to do this: the block is still one prism and this is still only a cut,
# just a cut that stops where the ramp wants to be (user's rule -- grow the prism and cut
# away, never glue a wedge on afterwards).
RAMP_X0 = ROD_X + BAY_D / 2 * _APEX              # the teardrop's apex: where the flank ends
RAMP_X1 = X_FRONT - D.MIN_WALL                   # ...and where it flattens, a bead short
RAMP_Z1 = ROD_Z + (RAMP_X1 - RAMP_X0)            # 45 deg: the rise IS the run
assert RAMP_Z1 < SLOT_Z0, (
    f"the ramp's crest ({RAMP_Z1:+.2f}) reaches the string slot's floor ({SLOT_Z0:+.2f})")


def _all_skies() -> cq.Workplane:
    """Open every lane to the sky, from the ROD'S CENTRE-PLANE up. Fused, cut once.

    This is what removes the beams the trough left behind -- the wedges standing between
    each trough's crown and the cap -- and the rule is chosen so they cannot come back:

        ROD_Z IS THE TROUGH'S WIDEST POINT. An opening that starts at the widest point of
        the shape below it can never narrow going up, so nothing spans the lane and there
        is no overhang to argue about. Cut from any higher and the trough's own crown
        closes over the opening; cut from lower and material is spent for nothing.

    ...and +X OF THE TROUGH ITS FLOOR RIDES THE RAMP instead, climbing at the same 45 the
    teardrop's flank does and levelling off RAMP_X1. That is a floor that only ever gets
    HIGHER going +X, so the no-narrowing rule still holds and the lane is still open to
    the sky the whole way; it just stops throwing away the ramp. See the RAMP_ block.

    ITS -X EDGE IS THE TEARDROPS' CENTRE (user), i.e. the rod axis, not the trough's -X
    wall: the lane opens over the +X half only and the -X half keeps its roof.

    The FINGERS are untouched -- they sit between lanes, keep their full height, and are
    what still captures the rod, since their material stands above the bore's top up to
    the cap. So the rod cannot lift out even though its lane is open."""
    top = NUT_TOP + 1.0
    xe = X_FRONT + 1.0
    prof = [(ROD_X, ROD_Z), (RAMP_X0, ROD_Z), (RAMP_X1, RAMP_Z1),
            (xe, RAMP_Z1), (xe, top), (ROD_X, top)]
    out = None
    for i in range(D.N_STRINGS):
        y0, y1 = bays()[i]
        k = (cq.Workplane("XZ").polyline(prof).close()
             .extrude(y1 - y0).translate((0.0, y1, 0.0)))
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


# ── THE STOW CHANNEL: a teardrop SWEPT down a curve (user) ─────────────────
# The tail used to leave on the top tangent, run -X in a square channel to the block's
# back face, and drop into a separate vertical bore in the endplate -- three features,
# two of them with corners the string had to be persuaded round.
#
# Now it is ONE passage and the string never turns a corner it is not already turning:
# the wrap carries on to EXIT_DEG, so the tail leaves already heading -X and 45 deg DOWN,
# the channel starts as a 45 cut on that same line, and then bends smoothly to vertical
# and runs out the bottom.
#
# WHY IT IS SWEPT RATHER THAN BORED. A round hole on a curve is not a shape teardrop_hole
# can make -- and worse, teardrop_hole REFUSES an axis that is not perpendicular to the
# build direction, which this one is not (it has an X component the whole way). So the
# curve is walked in short chords and each chord gets its own teardrop section, exactly
# the way the string path itself approximates its arcs. Each section's apex points at the
# projection of PRINT_UP onto that section's own normal plane, so the roof is 45 deg
# supported all the way round the bend rather than only where the axis happens to be
# square to the bed.
STOW_D = 4 * D.BEAD                             # 3.2: the bore the cut tail is stowed
                                                # in. It was 6 beads, which is far more
                                                # than a .070 tail needs (user) -- and an
                                                # oversized bore here is not free: the
                                                # teardrop's apex reaches d/2*sqrt(2), so
                                                # every extra bead of diameter pushes the
                                                # whole channel another 0.57 -X to keep
                                                # its wall off the trough.


WRAP_EPS = 0.05                                 # the coil is drawn a hair off the rod


def wrap_radius(i: int) -> float:
    """Radius of string i's coil centreline about the rod axis. THE ONE PLACE THIS IS
    COMPUTED -- build.py drew the coil at this radius while stow_path put the exit point
    at a radius 0.05 smaller, so every tail started just inside its own coil's surface and
    the union of the two collapsed (string 10 came out at 166 mm^3 when its coil alone was
    165 and its tail 200). Same bug as the stow bores and the touch angle before it."""
    return ROD_D / 2.0 + D.STRING_GAUGE[i] / 2.0 + WRAP_EPS


# WHERE THE CHANNEL SITS, AND IT IS SET BY THE SOCKET (user). The bore's own TEARDROP
# TIP is what has to keep its distance, not its axis: the apex points +X (the build
# direction) and reaches STOW_D/2 * sqrt(2) off centre, so a bore placed by its axis would
# put 1.6 of wall on paper and 1.6 - 2.26 of it in the part.
# The block only spans down to NUT_BASE, but the bore carries on into the endplate this
# block is fused into, so the block's own cut is asked for the full depth and simply
# intersected with the prism.
STOW_Z_END = -40.0                              # well past the block's base
STOW_KEEP = D.MIN_WALL_2P                       # wall between the channel's tip and the socket
STOW_APEX = STOW_D / 2.0 * _APEX                # the teardrop's real +X reach
STOW_X = INS_X0 - STOW_KEEP - STOW_APEX
assert STOW_X - STOW_D / 2.0 > X_BACK, (
    f"the stow channel ({STOW_X:.2f}) has walked out through the block's -X face "
    f"({X_BACK:.2f}) -- the socket or the channel has grown")


def stow_channel(i: int, y: float, z_end: float) -> cq.Workplane:
    """String i's stow passage: ONE STRAIGHT TEARDROP BORE ALONG Z (user).

    This channel has had four constructions and this is the only simple one, so it is
    worth saying what the other three were paying for and why the bill is no longer worth
    it. They all tried to carry the string CONTINUOUSLY from the wrap into the passage --
    the tail left the rod already descending at 45, the passage started on that same line
    and bent smoothly to vertical, and the string never turned a corner it was not already
    turning. That is a nice property and it cost:

      * a swept cutter, which cadkit's teardrop_hole cannot make (it refuses an axis that
        is not square to the build direction, and a bending one never is);
      * chording it instead, which rolls the apex between chords and fills the roof with
        micron-thick sheets;
      * or sweeping a section in the XZ plane instead, which is clean but leaves the roof
        FLAT the full width of the bore;
      * or slabbing that in Y to get the roof back, at 105 s a rebuild.

    A straight bore needs none of it. The string is CUT TO LENGTH and pushed down the hole
    by hand at restring (user), so it does not need a fair curve to follow -- it needs a
    hole it can be fed into. teardrop_hole makes exactly that, its axis is square to the
    build direction so the helper is happy, and the apex points +X with no argument.

    The tail reaches it OVER THE TOP: the socket and this bore both open at the block's
    upper face, and the wall between them stops at NUT_TOP, so the wound end comes up out
    of the socket, over that wall and down the hole. That is why the wrap now leaves at
    EXIT_DEG 45, heading -X and UP, instead of down."""
    z1 = NUT_TOP + 1.0
    return teardrop_hole(STOW_D, z1 - z_end, axis_point=(STOW_X, y, z_end),
                         axis_dir=(0.0, 0.0, 1.0), print_up=PRINT_UP)


def all_stow_channels(z_end: float) -> cq.Workplane:
    """Every tail's passage, fused and cut once -- the lesson the troughs taught."""
    out = None
    for i in range(D.N_STRINGS):
        k = stow_channel(i, wrap_y(i)[1], z_end)
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

        # (the EXIT is no longer a straight -X channel per string: the tail leaves at
        #  EXIT_DEG already descending and the passages are swept and cut once below --
        #  see all_stow_channels)
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
    # SOCKETS FIRST -- the plan, swept, offset by the fit. Nothing else.
    # ...the slots the INSERTS rise through, cut from the parts' own profiles so the
    # pocket cannot drift from the thing it has to accept.
    body = body.cut(all_pockets())

    # ...and the stow passages, swept from each tail's exit tangent down and out the
    # bottom. Cut to just under the block's base: the endplate this block is fused into
    # carries the same passage the rest of the way to the bed.
    body = body.cut(all_stow_channels(STOW_Z_END))

    # THE STRING SLOT IS GONE (user), and it turns out it had been redundant for a while.
    # It cut the whole +X end, FULL WIDTH IN Y, from SLOT_Z0 up -- which beheaded every
    # finger between the dowel pockets, leaving them 1.07 shorter than the axle fingers
    # behind them. What it was for was clearing the strings, and it dates from when this
    # block stood to +7.1: NUT_TOP is -2.31 now, a good 2.3 BELOW the string plane, so
    # there is no longer any block material that could foul a string to begin with.
    #
    # Nothing replaces it. Each string's own lane is already opened by the two cuts that
    # have to be there regardless -- the sky over the bay and the insert's pocket -- and
    # what those two leave standing between the lanes is exactly the finger, now running
    # its full height to the cap like the ones at the axle do.
    assert SLOT_Z0 < NUT_TOP, (
        f"the block ({NUT_TOP:+.2f}) now reaches the strings' clearance line "
        f"({SLOT_Z0:+.2f}) -- it needs a string slot again")

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
