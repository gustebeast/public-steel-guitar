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

THE ROD IS THE BRIDGE AXLE'S OWN PART (user). The Ø8 x 100 precision shaft the +X
endplate carries its 688ZZ bearings on -- D.BRIDGE_AXLE_D and D.BRIDGE_AXLE_L, read
here rather than copied -- so both ends of the instrument buy ONE shaft SKU. Ø8 bends
the .070 at 18.2% outer-fibre strain (d/(D+d)), gentler than the Ø5 it replaced
(26.2%) and than a guitar tuner post. The move from Ø5 was paid for in X (ROD_X) and in
the block's -Y reach (Y_LO), not in the break angle, which re-solves itself.

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

ROD_D = D.BRIDGE_AXLE_D                         # Ø8 -- the bridge axle's own shaft (user)
ROD_FIT = 0.4                                   # the rod is LOCATED, not gripped: the wraps
                                                # load it -X and the comb takes that; it only
                                                # has to slide in through 10 fingers at once
ROD_BORE = ROD_D + ROD_FIT

# ── X layout (local frame) ─────────────────────────────────────────────────
# The prism runs from X_FRONT, flush with the endplate's +X face, back to X_BACK, the -X
# bed face. X_BACK is DERIVED (user): two beads behind the stow bores, the -X-most thing
# in the part -- see KEYHEAD_W, defined once STOW_X exists. The chassis reads it.
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
# THE ROD'S +X FACE MUST STAY -X OF THE INSERT TAPER (asserted in _plan). The taper starts
# where the DOWEL puts it (string 1: -3.57), whatever the rod does. At Ø5 the centre sat at
# -6.4 with its face at -3.9; Ø8 adds 1.5 of radius, so the centre steps two beads -X to
# hold the face at -4.0. INS_X0 and the stow bores follow it -X by derivation.
ROD_X   = -10 * D.BEAD                          # -8.0 rod centre
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
# THE INSERT'S TRAVEL IS SIZED FOR THE ENVELOPE, not the demo set: a heavier string must still
# thread and clamp without a reprint (D.STRING_GAUGE_MAX). The ROD stays solved for the set
# above -- its break angle is a target, and a heavier string only breaks a little shallower
# (asserted against BREAK_ANGLE below).
G_ENVELOPE = max(_G_MAX, D.STRING_GAUGE_MAX)


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
# THE BAR HAS TO CLEAR IT. A round bar resting on the strings at fret 0 is a circle of
# BAR_R centred BAR_R above the string plane over the dowel; the rod must stay a margin
# outside it. Tested circle-to-circle, not as the bar's height above the rod's AXIS: that
# closed form, R - sqrt(R^2 - d^2), only exists while the rod sits less than one bar
# radius behind the nut, and the Ø8 rod's step -X (ROD_X) put it past that -- the old
# test did not fail, it stopped being computable.
BAR_R   = 19.0 / 2                              # a typical steel bar
_BAR_CLR = math.hypot(DOWEL_X - ROD_X, BAR_R - ROD_Z) - BAR_R - ROD_D / 2
assert _BAR_CLR >= 0.8, (
    f"the rod (O{ROD_D} at x {ROD_X:+.2f}, z {ROD_Z:+.2f}) comes within {_BAR_CLR:.2f} of a "
    f"bar resting at fret 0 -- the first centimetre could not be barred")

# ── Z extent ───────────────────────────────────────────────────────────────
# ONE PRISM, AND A SHORT ONE. NUT_TOP used to be INSERT_GAP + INSERT_POCKET -- whatever
# height the M4 clamp inserts needed to drop in from +Z. Those screws are gone (the
# sliding insert IS the clamp) and with them the only reason this block stood above the
# strings. What is left to cover is the ROD BORE, so that sets it.
NUT_TOP  = ROD_Z + ROD_BORE / 2 + D.MIN_WALL_2P  # a two-bead lid over the rod
NUT_BASE = D.DECK_TOP_Z - D.STRING_Z             # prism base sits on the deck plane

# THE TWO CLAMP ROWS ARE GONE with the screws that needed them. They sat at -15.2 and
# -20.8 and were staggered so O6 heat-set inserts could clear each other at a 6.5 pitch;
# the sliding insert clamps the string against the rod instead, so none of that layout --
# nor the wall behind it that _NX_WALL policed -- has anything left to protect.
TAIL_X  = None                                  # set below, once INS_X0 exists


def _touch_angle_g(g: float) -> float:
    """Angle about the rod axis (in the XZ plane, from +X) at which string i first
    TOUCHES the wrap circle, coming down off its dowel. The LOWER of the two tangents,
    because the string wraps the underside.

    THE ONE PLACE THIS IS COMPUTED. The turn count, the drawn string path and the coil's
    start phase all read it; when build.py owned a second copy the straight run and the
    coil disagreed and left a visible gap in the wrap."""
    hr = ROD_D / 2 + g / 2                       # the string's centre-path radius
    dx, dz = DOWEL_X - ROD_X, -g / 2 - ROD_Z     # rod axis -> dowel (the rod sits BELOW)
    # the UPPER of the two tangents: the string now comes down onto the rod's top
    return math.atan2(dz, dx) + math.acos(hr / math.hypot(dx, dz))


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
def _sweep0_g(g: float) -> float:
    """Turns from where a string of gauge g touches the rod round to the exit tangent."""
    return ((math.radians(EXIT_DEG) - _touch_angle_g(g)) % (2 * math.pi)) / (2 * math.pi)


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
# turns, so the tail leaves on its exit tangent; ~2.93 here, which is also each string's _K_MIN.
WRAPS = 3


def wraps(i: int) -> float:
    """Turns string i is wound with, as recommended and as drawn: the entry sweep plus the whole
    number of turns nearest WRAPS. Never under the clamp guarantee, never over the lane."""
    return _sweep0(i) + max(_k_min(i), round(WRAPS - _sweep0(i)))


_WRAPS_BAD = [i + 1 for i in range(D.N_STRINGS) if wraps(i) > turns(i) + 1e-9]
assert not _WRAPS_BAD, (
    f"strings {_WRAPS_BAD} cannot fit the recommended {WRAPS} wraps in their lane")


def clamp_widths(i: int) -> float:
    """Contact at the clamp, in string widths -- what CLAMP_WIDTHS asked for."""
    return (wraps(i) - 1.0) * WRAP_F + 1.0


def exit_angle(i: int) -> float:
    """Where string i's tail leaves the rod -- EXIT_DEG, by construction, since turns()
    is built as the entry sweep plus a whole number of revolutions."""
    return touch_angle(i) + wraps(i) * 2 * math.pi


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
    # UP FIRST, INSIDE ITS OWN SOCKET. Going straight from the stub to the over-the-wall point
    # drew a diagonal that shaved the wall's top +X corner -- the last of string 10's clip
    # once SKU C had moved its end wall (0.14 mm3), and a sliver on 7-9 as well. The socket is
    # open to the top, so the tail rises in it to half a gauge short of its -X face, then
    # crosses the wall level. That is the 'UP' this docstring always described.
    x_rise = INS_X0 - _clr(i) + D.STRING_GAUGE[i] / 2.0
    return [(x0, z0),
            (x0 + ex * stub, z0 + ez * stub),    # off the rod on its own tangent...
            (x_rise, z_over),                    # ...up inside the socket...
            (STOW_X, z_over),                    # ...level over the wall by hand
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
THREAD_LEAD = math.ceil(G_ENVELOPE / D.BEAD) * D.BEAD             # 2.4
_DROP_NEED = G_ENVELOPE + THREAD_CLR            # 2.832 for a .080
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
INS_X0    = math.floor((ROD_X - ROD_D / 2 - G_ENVELOPE - D.MIN_WALL)
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


# SKU B's -Y STEP: how far its dowel lobe's -Y edge stands inward (+Y) of its clamp lobe's. The
# pocket's shoulder there is what stops an insert walking +X; SKU C copies it (user).
BASS_STEP_LO = INS_LOBE_W / 2 - BASS_OFF        # 1.75

# ── SKU C: STRING 10 ON ITS OWN, AS WIDE AS IT LIKES (user) ─────────────────────
# The longstanding string-10 clip was SKU B's clamp lobe. It hangs BASS_W from BASS_OFF above
# its string, which covers strings 8 and 9 with 1.1 to spare but not the outermost: that coil
# marches -Y furthest, and at the .070 its last turn ran 0.33 past the lobe into the end wall
# for the whole insert run (2.6 mm3, invisible to the gate, which lets keyhead_endplate touch
# any string). At a .080 it would have been 1.24.
#
# String 10 has nothing -Y of it, so its insert can simply be wider. SKU C keeps SKU B's +Y
# edges -- it still abuts string 9 -- and runs its CLAMP lobe out to SKU_C_LO, with the dowel lobe
# stepping back in by SKU B's own -Y step (user: that shoulder keeps the insert from walking +X,
# and the taper up to it prints like every other insert's). That edge covers the coil for every gauge
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


def insert_lobes(i: int):
    """(dowel lobe, clamp lobe) as (y_centre, width) pairs -- the insert's plan.

    SKU A's clamp lobe is THE LANE, less its pocket clearance -- not the coil. Sizing it
    to the coil is what made every insert a different part; sizing it to the window makes
    them all the same one, and the window is guaranteed to contain the coil because
    turns() is what fits the coil into it."""
    if i < N_FINGERED:
        return ((D.nut_y(i), INS_LOBE_W), (D.nut_y(i) + CLAMP_C, CLAMP_W))
    if i == SKU_C:
        # SKU C keeps SKU B's +Y edges (it abuts string 9). Its clamp lobe runs to SKU_C_LO; its DOWEL
        # lobe stops BASS_STEP_LO short of that, so the -Y edge steps inward exactly like every other
        # insert's -- the pocket shoulder that makes is what keeps it from walking +X (user).
        dhi, chi = D.nut_y(i) + INS_LOBE_W / 2, D.nut_y(i) + BASS_OFF
        dlo = SKU_C_LO + BASS_STEP_LO
        return (((dhi + dlo) / 2, dhi - dlo), ((chi + SKU_C_LO) / 2, chi - SKU_C_LO))
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


# SKU C'S -Y TAPER RUNS OVER STRING 10'S COIL. The step (BASS_STEP_LO) tapers in from x_s to x_e,
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
assert _SKU_C_TAPER_GAP >= 0.0, (
    f"string 10's coil reaches {-_SKU_C_TAPER_GAP:.2f} past SKU C's tapered pocket edge for some gauge "
    f"up to {D.GAUGE_MAX_IN:.3f} in -- the -Y step has been drawn over the winding")


def _plan_wire(i: int):
    return cq.Workplane("XY").polyline(_plan(i)).close()


NECK_CLR_X = 0.4                                # air +X of the coil, before the neck


def _neck_x0(i: int) -> float:
    """Where string i's neck starts. The wrap reaches ROD_X + ROD_D/2 + g on its +X side
    and anything -X of that drives through the winding, so the neck starts from the COIL's
    own extent -- the SKU's HEAVIEST coil (sku_gauge_max), so every insert of a SKU has the
    same neck. THE ONE PLACE THIS IS COMPUTED."""
    return ROD_X + ROD_D / 2.0 + sku_gauge_max(i) + NECK_CLR_X


# ── HOW BIG THE THREADING RAMPS MAY BE ─────────────────────────────────────
# They are added material sitting right where the coil does, so their size is not a taste
# question: each is the largest 45 deg ramp that still clears EVERY string's wound
# envelope by RAMP_CLR. Both limits fall out of string 10, whose coil is fattest and whose
# flat therefore sits lowest.
RAMP_CLR = 0.4                                  # air between a ramp and a wound string


def _ramp_fits(L: float, x0: float, sgn: float, g: float) -> bool:
    """Does a 45 deg ramp of rise L, running sgn from x0, clear the coil of a gauge-g string
    (with the insert risen to that string, which is where the ramp sits)?"""
    r = ROD_D / 2.0 + g                          # the wound coil's outer envelope
    fz = ROD_Z - ROD_D / 2 - g                   # insert_flat_z, for this gauge
    for k in range(41):
        t = k / 40.0
        dx = (x0 + sgn * L * t) - ROD_X
        if abs(dx) >= r:
            continue
        if fz + L * (1.0 - t) > ROD_Z - math.sqrt(r * r - dx * dx) - RAMP_CLR:
            return False
    return True


def _max_ramp(x0_of, sgn: float) -> float:
    """The biggest such ramp that suits every slot at BOTH the demo string and the heaviest its
    SKU is built for (sku_gauge_max), snapped DOWN to the bead grid -- the ramp is part of the
    insert, and an insert has to thread any string its SKU accepts."""
    worst = 99.0
    for i in range(D.N_STRINGS):
        for g in {D.STRING_GAUGE[i], sku_gauge_max(i)}:
            lo, hi = 0.0, 8.0
            for _ in range(40):
                mid = (lo + hi) / 2.0
                lo, hi = (mid, hi) if _ramp_fits(mid, x0_of(i), sgn, g) else (lo, mid)
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
    # THE HEIGHT-ADJUST EXTENSION (user): a tall foot down to the screw that pushes the insert up.
    # Gabled plan (lower_plan_wire), so its pocket closes at +X without an overhang -- CLIPPED to
    # the insert's own plan: where the clamp lobe steps to the dowel lobe the bare gable would stick
    # out of the main pocket once the screw lifts the insert above the lower pocket.
    ext = (lower_plan_wire(i).extrude(INS_EXT_H + 0.01)
           .intersect(_plan_wire(i).extrude(INS_EXT_H + 0.01)))
    body = body.union(ext.translate((0, 0, fz - INS_H - INS_EXT_H)))
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
Y_WALL  = 8.0                                   # solid past the outermost insert, for strength
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
# THE BORES LEAN -Y AS THEY DESCEND (user). Straight down, strings 1 and 2 came out inside the +Y
# leg's body stub at the keyhead corner (its -Y face ~y 21.1, its top ~9 above the endplate floor),
# so their tails could not be reached from under the instrument. ONE tilt for all ten keeps them
# parallel -- every web between neighbours is unchanged -- and it pivots where each bore meets the
# top of its socket, so the entries stay exactly where stow_y puts them. The lean is in Y only,
# square to the -X -> +X build, so the bore is still a cadkit teardrop with its apex +X.
# 6.4 deg is the least that clears that stub with two beads of air; 7 puts string 1 ~5.7 clear of
# its face where the bore reaches its height. A constant, not derived from the stub: that part
# belongs to the leg-stack rework, so it is measured against in the build, not imported here.
STOW_TILT_DEG = 7.0
STOW_TILT = math.radians(STOW_TILT_DEG)
STOW_PIVOT_Z = NUT_TOP + 1.0                      # where a bore meets the top of its socket
# THE BED FACE IS TWO BEADS BEHIND THE STOW BORES (user). The keyhead used to be a fixed 28.8
# (a literal sized for clamp inserts that no longer exist), which left 4.34 of solid behind
# the bores doing nothing. The stow bore is the -X-most feature now, so the face follows it
# and the thickness is whatever the string termination hardware actually needs. The bores
# lean in Y only (STOW_TILT), so their -X reach is STOW_D/2 at every height.
X_BACK = STOW_X - STOW_D / 2.0 - D.MIN_WALL_2P
KEYHEAD_W = X_FRONT - X_BACK                      # the keyhead endplate's thickness in X


def stow_y(i: int) -> float:
    """Y of string i's stow bore (at the top of its socket): its -Y EDGE FLUSH WITH THE INSERT'S
    -Y EDGE, i.e. the clamp lobe's, which the bore sits behind. From the INSERT, not the coil
    (user) -- a hole in a printed part must not move when the strings change -- but biased -Y,
    not centred: the coil always marches -Y, so whatever the gauge the tail leaves near that
    end of the insert, and a centred bore made every tail cut back across the socket. Flush
    lands within ~0.2 of where the bass tails actually leave."""
    (_dy, _dw), (cy, cw) = insert_lobes(i)
    return cy - cw / 2.0 + STOW_D / 2.0


def stow_y_at(i: int, z: float) -> float:
    """Y of string i's stow bore axis at height z (local frame): stow_y at and above the pivot,
    leaning -Y by STOW_TILT below it."""
    return stow_y(i) - max(0.0, STOW_PIVOT_Z - z) * math.tan(STOW_TILT)


_STOW_WEBS = [abs(stow_y(i) - stow_y(i + 1)) - STOW_D for i in range(D.N_STRINGS - 1)]
assert min(_STOW_WEBS) >= D.MIN_WALL_2P - 1e-9, (
    f"two neighbouring stow bores leave only {min(_STOW_WEBS):.2f} of web between them -- "
    f"under the {D.MIN_WALL_2P} two-bead floor")


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
    dz = STOW_PIVOT_Z - z_end
    y_end = y - dz * math.tan(STOW_TILT)          # leaning -Y on the way down (STOW_TILT)
    return teardrop_hole(STOW_D, dz / math.cos(STOW_TILT), axis_point=(STOW_X, y_end, z_end),
                         axis_dir=(0.0, math.sin(STOW_TILT), math.cos(STOW_TILT)),
                         print_up=PRINT_UP)


def all_stow_channels(z_end: float) -> cq.Workplane:
    """Every tail's passage, fused and cut once -- the lesson the troughs taught."""
    out = None
    for i in range(D.N_STRINGS):
        k = stow_channel(i, stow_y(i), z_end)            # from the insert, not the coil
        out = k if out is None else out.union(k)
    return out


# ── HEIGHT ADJUST: ONE M4 SCREW UNDER EACH INSERT (user) ─────────────────────────────
# The sliding insert clamps its string by rising against the coil, and until now nothing pushed it
# up. Each insert now grows a tall EXTENSION down into a new prism in the keyhead endplate
# (keyhead_endplate.HS_*), and an M4 x 18 button head -- the keyhead hold-down's own SKU, on the
# instrument's one 2.5 mm key -- pushes its foot up from below.
#
# THE NUT IS IN THE ENDPLATE, NOT THE INSERT. An M4 heat-set wants ~8 of width (M4.boss_od); SKU A
# inserts are 3.6-4.3 wide and SKU B 6.4, so only SKU C could carry one. So the heat-set sits in a
# slab of the endplate, mouth DOWN, and the screw travels with adjustment (the user's fallback).
#
# THE STACK, from the chassis up (local frame -- Z relative to STRING_Z):
#   motor_bank.FLOOR_TOP  top of the wide corner rib the keyhead sits over (chassis)
#   HS_PRISM_BOT          0.4 above that rib
#   head cavity           room for the button head to hang at full retract
#   HS_SLAB_BOT           the heat-set's mouth, facing down (fitted before the endplate goes on)
#   HS_FLOOR              the slab top = pocket floor = where a DROPPED insert's foot rests
from cadkit.fasteners import M4, M4_BUTTON_HEAD_D, M4_BUTTON_HEAD_H
from . import motor_bank as _MB                  # motor_bank imports only dimensions/helpers/components
HS_SCREW_L    = 18.0                             # M4 x 18 button: the keyhead hold-down's SKU
HS_HEAD_CLR   = 0.4                              # radial air round the head in its cavity
HS_HEAD_CAV_D = M4_BUTTON_HEAD_D + 2 * HS_HEAD_CLR
HS_SLAB_T     = M4.insert_depth + 4 * D.BEAD     # the heat-set plus a 3.2 floor over it
HS_PRISM_BOT  = _MB.FLOOR_TOP + 0.4 - D.STRING_Z
HS_SLAB_BOT   = HS_PRISM_BOT + 0.4 + (HS_SCREW_L - HS_SLAB_T) + M4_BUTTON_HEAD_H
HS_FLOOR      = HS_SLAB_BOT + HS_SLAB_T
# THE EXTENSION puts a DROPPED insert's foot on the floor: the lowest flat any string may set, less
# the threading drop, less the body -- the same datum POCKET_Z0 is cut from.
_FZ_LOW   = ROD_Z - ROD_D / 2.0 - G_ENVELOPE - INS_DROP
INS_EXT_H = (_FZ_LOW - INS_H) - HS_FLOOR
assert INS_EXT_H > 0.0, "the height-adjust floor is above the insert body"
# How far the screw tip has to rise: the whole drop plus the full gauge envelope (a string of zero
# gauge would sit highest). Gauge-free, like the rest of the printed part.
HS_REACH_MAX = INS_DROP + G_ENVELOPE
assert HS_REACH_MAX <= HS_SCREW_L - HS_SLAB_T - HS_HEAD_CLR, (
    f"a {HS_SCREW_L:g} mm screw cannot reach {HS_REACH_MAX:.2f} above the floor without its head "
    f"meeting the slab")


def insert_foot_z(i: int) -> float:
    """Local Z of string i's insert FOOT, clamped on its demo string (as drawn)."""
    return insert_flat_z(i) - INS_H - INS_EXT_H


def screw_reach(i: int) -> float:
    """How far above the floor string i's screw tip stands when that insert is clamped."""
    return insert_foot_z(i) - HS_FLOOR


# TWO ROWS. Ø6 heat-set pockets on the 6.5 string pitch would leave 0.5 of wall, and Ø7.6 heads would
# collide, so the strings alternate between two X rows. Row A is the more +X of two limits:
#   * its head cavity a two-bead wall clear of the stow bores' teardrop tip (their X never changes --
#     they lean in Y only);
#   * its KEY PATH clear of this part's own lower -X wall (endplate_base's CH.T rail, which hangs
#     down past the corner rib): the 2.5 mm key comes up from under the chassis through an M4-
#     clearance hole (chassis.py), so that hole's -X edge may not run into the wall's +X face.
# Row B is 4.8 +X of row A, which clears neighbouring heads and leaves the heat-set pockets > 1.6 apart.
_HS_KEY_X_MIN = X_BACK + D.WALL_THICKNESS + M4.shaft_clr_d / 2.0
_HS_ROW_A = max(STOW_X + STOW_APEX + D.MIN_WALL_2P + HS_HEAD_CAV_D / 2.0, _HS_KEY_X_MIN)
HS_ROWS = (_HS_ROW_A, _HS_ROW_A + 6 * D.BEAD)


def height_screw_xy(i: int):
    """(x, y) of string i's height screw, local frame: its row, centred on the insert's clamp lobe."""
    (_dy, _dw), (cy, _cw) = insert_lobes(i)
    return HS_ROWS[(SKU_C - i) % 2], cy


def lower_plan_wire(i: int):
    """The EXTENSION's plan: the clamp lobe's Y span from INS_X0, with a 45 deg gable closing at +X
    on the insert's own +X face. The keyhead prints -X -> +X, so a square +X end would be a ceiling
    over the pocket; a gable is a roof. The extension prints the same way (on its -X face)."""
    (_dy, _dw), (cy, cw) = insert_lobes(i)
    lo, hi = cy - cw / 2.0, cy + cw / 2.0
    xg = INS_X1 - cw / 2.0
    assert xg > INS_X0, f"string {i + 1}'s gable would run past the insert's -X face"
    return (cq.Workplane("XY")
            .polyline([(INS_X0, lo), (xg, lo), (INS_X1, cy), (xg, hi), (INS_X0, hi)]).close())


def insert_pocket_lower(i: int) -> cq.Workplane:
    """The extension's slot: its gabled plan grown by the fit, from the floor up into the main pocket."""
    z0, z1 = HS_FLOOR, POCKET_Z0 + 0.5
    gable = lower_plan_wire(i).offset2D(_clr(i), kind="arc").extrude(z1 - z0)
    plan = _plan_wire(i).offset2D(_clr(i), kind="arc").extrude(z1 - z0)   # the extension is clipped too
    return gable.intersect(plan).translate((0, 0, z0))


def pocket_x_slot(i: int, x_to: float, z_top: float) -> cq.Workplane:
    """Opens the MAIN pocket's +X end out through the prism, over the band the insert's full-profile
    body travels inside the prism (POCKET_Z0 up to z_top). There that end is the dowel lobe's flat,
    and material +X of it would be a ceiling in the -X -> +X print."""
    (dy, dw), _cl = insert_lobes(i)
    c = _clr(i)
    x0 = INS_X1 - 0.5
    z0 = POCKET_Z0 - 0.1
    return box_at(x_to - x0, dw + 2 * c, z_top - z0, x=(x0 + x_to) / 2, y=dy, z=(z0 + z_top) / 2)


def height_screw_negatives(i: int):
    """Head cavity, heat-set pocket and shank/tip bore for string i, all TEARDROPS along Z (sideways to
    the -X -> +X build), apex +X."""
    x, y = height_screw_xy(i)

    def bore(d, z0, z1):
        return teardrop_hole(d, z1 - z0, axis_point=(x, y, z0), axis_dir=(0.0, 0.0, 1.0),
                             print_up=PRINT_UP)
    return [bore(HS_HEAD_CAV_D, HS_PRISM_BOT - 1.0, HS_SLAB_BOT),
            bore(M4.insert_pilot_d, HS_SLAB_BOT - 0.01, HS_SLAB_BOT + M4.insert_depth),
            bore(M4.shaft_clr_d, HS_SLAB_BOT + M4.insert_depth - 0.01, HS_FLOOR + HS_REACH_MAX + 1.0)]


def height_screw(i: int) -> cq.Workplane:
    """Dummy M4 x 18 button head, head DOWN, tip on string i's clamped insert foot (local frame)."""
    from cadkit.fasteners import m4_button_screw
    x, y = height_screw_xy(i)
    tip = HS_FLOOR + screw_reach(i)
    s = m4_button_screw(HS_SCREW_L).rotate((0, 0, 0), (1, 0, 0), 180)   # head z 0..h, shank up to h + L
    return s.translate((x, y, tip - (M4_BUTTON_HEAD_H + HS_SCREW_L)))


def height_insert(i: int) -> cq.Workplane:
    """Dummy M4 heat-set in the slab under string i, mouth down (local frame)."""
    from cadkit.fasteners import seated_insert
    x, y = height_screw_xy(i)
    return seated_insert(M4, (x, y, HS_SLAB_BOT), (0.0, 0.0, 1.0))


# ── what the layout must keep true ─────────────────────────────────────────────
for _i in range(D.N_STRINGS - 1):
    (_xa, _ya), (_xb, _yb) = height_screw_xy(_i), height_screw_xy(_i + 1)
    _d = math.hypot(_xa - _xb, _ya - _yb)
    assert _d >= M4_BUTTON_HEAD_D + HS_HEAD_CLR - 1e-9, (
        f"strings {_i + 1} and {_i + 2}: height-screw heads {_d:.2f} apart -- they would collide")
    assert _d - M4.insert_pilot_d >= D.MIN_WALL_2P - 1e-9, (
        f"strings {_i + 1} and {_i + 2}: heat-set pockets leave {_d - M4.insert_pilot_d:.2f} of wall")
assert (_HS_ROW_A - HS_HEAD_CAV_D / 2.0) - (STOW_X + STOW_APEX) >= D.MIN_WALL_2P - 1e-9, (
    "row A's head cavity has walked into the stow bores")
for _i in range(D.N_STRINGS):
    _x, _y = height_screw_xy(_i)
    (_dy, _dw), (_cy, _cw) = insert_lobes(_i)
    assert _x + M4.shaft_clr_d / 2.0 <= INS_X1 - _cw / 2.0 + 1e-9, (
        f"string {_i + 1}'s screw tip bore reaches past its extension's gable")
    assert 0.0 <= screw_reach(_i) <= HS_REACH_MAX + 1e-9, f"string {_i + 1}'s screw reach is out of range"


def _build() -> cq.Workplane:
    # ONE solid prism, the endplate footprint, and every feature is CUT from it.
    body = box_at(X_FRONT - X_BACK, HW - Y_LO, NUT_TOP - NUT_BASE,
                  x=(X_FRONT + X_BACK) / 2, y=(HW + Y_LO) / 2, z=(NUT_TOP + NUT_BASE) / 2)

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
    body = body.cut(rod_bore())
    return body


def rod() -> cq.Workplane:
    """The wrap rod itself, in the nut block's local frame — the bridge axle's shaft."""
    return cyl_y(ROD_D, ROD_Y1 - ROD_Y0, y0=ROD_Y0, x=ROD_X, z=ROD_Z)


def rod_bore() -> cq.Workplane:
    """The rod's bore, in the local frame: open at -Y (the rod slides in there), BLIND at +Y.
    ONE definition, because it is cut twice. The Ø8 rod dips below the deck plane, where this
    block stops and the keyhead endplate's base prism begins -- and that prism, fused in
    afterwards, fills the bottom of the bore straight back in (905 mm3 of rod buried in the
    endplate, the refill trap). So keyhead_endplate re-cuts this after its unions."""
    # THE INSERTION RUN IS THE ROD'S WHOLE LENGTH (user). The rod goes in from -Y, so before it
    # is pushed home it lies entirely -Y of its seat -- and the Ø8 rod dips below the deck plane,
    # where the keyhead's base stands. A 20 mm lead-out left that base blocking the other 80
    # (the rod could not be slid into position). keyhead_endplate asserts this run clears its
    # -Y face.
    return teardrop_hole(ROD_BORE, (ROD_Y1 - ROD_Y0) + ROD_L,
                         axis_point=(ROD_X, ROD_Y0 - ROD_L, ROD_Z),
                         axis_dir=(0.0, 1.0, 0.0), print_up=PRINT_UP)


nut_block = _build()
