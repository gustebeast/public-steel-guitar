"""Nut block geometry (×1) — keyhead string termination. PETG-GF, fused into the keyhead endplate.

THE STEEL NUT PLATE (user, 2026-11-03). Each string ends on its own laser-cut 304 plate, 4 mm
thick, one part for all ten (JLCCNC, quoted $80.15 for 100 delivered). Its profile, in XZ:

        crown (the break)                    the ROUNDED ARM's top is the break edge: the
          _                                  string comes over it from the bridge
         | |                                 and drops -X to the rod
         | |
    _____| |      <- shelf: pinches the one  the SHELF sits under the rod and pinches the
   |       |         strand under the rod    single strand crossing there, steel on steel
   |       |
   |       |      <- -X face: the tail is    the tail drops off the rod's -X side onto this
   |_______|         screwed against it      face, and a side screw pins it there

    bridge -> CROWN -> over the rod, down the -X side, under (shelf pinch), up the +X side,
    over again -> down the -X side -> tail, pinched on the plate's -X face by the side screw

WHY STEEL (user). Two reasons, both about the printer. A printed insert sets string HEIGHT from
a printed crown-to-shelf distance, and the thinnest strings differ by 0.025 mm -- below anything
FDM holds -- and a glued dowel adds its own seating error. The plate's crown and shelf are both
UP-FACING CUT EDGES, so kerf and taper move them together and cancel in the one distance that
sets height. And both pinches are now metal on metal, so nothing creeps under a wire.

ONE WRAP, NOT THREE (user). Three wraps could lie over one another under the insert, which then
stops on two diameters and sets the string 1 g low. With ONE turn past the entry, exactly one
strand crosses the bottom of the rod (asserted below), so the shelf can only ever meet one. The
string touches past the rod's top (~110-115 deg), so the capstan to the shelf is ~158 deg, x1.51
(~97 N left there); the side screw's grip counts x2.03 there (the 270 deg from the shelf round to the
exit). See residual().

A POCKET PER STRING, STRAIGHT (user). One wrap marches ~2 mm on the .070, so every string keeps
its own pocket and a finger to each neighbour (strings 8-10 no longer share a bay), and the
pocket is a plain rectangle in plan -- no stepped lobes, no tapers, one plate for all ten.

THE BENCH STAND-IN (user). Until the plates arrive, a PRINTED PCTG copy of the plate's outline
carries a Ø4 dowel where the crown is (standin()). It fits the same pocket, rides the same height
screw and takes the same side screw, so the endplate never needs reprinting for the swap.

THE ROD IS THE BRIDGE AXLE'S OWN PART (user). The Ø8 x 100 precision shaft the +X endplate carries
its 688ZZ bearings on -- D.BRIDGE_AXLE_D and D.BRIDGE_AXLE_L, read here rather than copied -- so
both ends of the instrument buy ONE shaft SKU. Kept, with the winding direction (user): over the
top, down the -X side. Every wrap marches -Y, toward the thicker neighbour.

Local frame: X=0 at the break edge, +X toward the bridge (speaking length); Z=0 at
the string-top plane (= STRING_Z global); body hangs -Z to the deck plane.

PRINTS -X -> +X. The -X end face is the bed. The rod bore runs along Y, so it takes cadkit's
teardrop; the side screws run along X, the build direction, and print round.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_y
from cadkit.holes import teardrop_hole

PRINT_UP = (1.0, 0.0, 0.0)                      # build axis: the -X face is the bed

# ── hardware ───────────────────────────────────────────────────────────────
PIN_D    = D.NUT_PIN_D                          # Ø4: the crown's diameter, and the stand-in's dowel
PIN_L    = D.NUT_PIN_L

ROD_D = D.BRIDGE_AXLE_D                         # Ø8 -- the bridge axle's own shaft (user)
ROD_FIT = 0.4                                   # the rod is LOCATED, not gripped: it slides in
                                                # through every finger at once
ROD_BORE = ROD_D + ROD_FIT

# ── X layout (local frame) ─────────────────────────────────────────────────
# X_FRONT is the endplate's +X face; X_BACK, the -X bed face, is defined further down (the side
# screws set it). The growth is all -X, AWAY FROM THE STRINGS: the break at X=0 does not move.
X_FRONT = D.KEYHEAD_PX_BUF                      # +3.8
# THE CROWN'S CENTRE: the old dowel's, so the scale, the break angles and the bar clearance below
# are all unchanged. It is a bead of wall plus the old 0.3 dowel fit back from the face.
DOWEL_X = X_FRONT - D.MIN_WALL - (PIN_D + 0.3) / 2
# THE ROD STANDS LOW, IN THE PLATE, CLEAR OF THE BAR (user). HEIGHT sets the break: higher flattens it.
# Thin to thick the break spreads ~6 deg, so no X puts all ten inside the 15-20 that is enough for the
# crown to end the speaking length and no steeper.
# X MOVED +3.2 FOR THE SIDE SCREWS (2026-11-03). The tail now drops off the rod's -X side, and behind it
# go the tail channel and the side screw's heat-set; at -14.4 that stack pushed the bed face 2.9 -X, and
# KEYHEAD_W moves the -X legs, the bottom's mortise grid (and so every foot's tenons and lock pin) and the
# boards laid out from them. At -11.2 the stack fits behind the old bed face, so nothing else moves. The
# price is a steeper break, 18.7-25.0 deg where it was 15.3-20.7: past the band, but steeper only adds
# load on the crown (~62 N down where it was ~52), and the crown is steel.
ROD_X   = -14 * D.BEAD                          # -11.2 rod centre
ROD_Z   = -13 * D.BEAD                          # -10.4
_G_MAX  = max(D.STRING_GAUGE)
# THE TRAVEL IS SIZED FOR THE ENVELOPE, not the demo set: a heavier string must still thread and
# clamp without a reprint (D.STRING_GAUGE_MAX).
G_ENVELOPE = max(_G_MAX, D.STRING_GAUGE_MAX)


def _break_at(rod_z: float, g: float) -> float:
    """True tangent angle, in degrees, down off the crown to the TOP of a rod at rod_z."""
    hr = ROD_D / 2 + g / 2
    dx, dz = DOWEL_X - ROD_X, -g / 2 - rod_z
    return math.degrees(math.atan2(dz, dx)) - math.degrees(math.asin(hr / math.hypot(dx, dz)))


# THE BAR HAS TO CLEAR IT. A round bar resting on the strings at fret 0 is a circle of
# BAR_R centred BAR_R above the string plane over the crown; the rod must stay a margin
# outside it. A Ø25 bar sitting on the crowns touches no plastic (user).
BAR_R   = 25.0 / 2                              # the biggest bar the player may rest at fret 0
BAR_CLR_MIN = 0.8
_BAR_CLR = math.hypot(DOWEL_X - ROD_X, BAR_R - ROD_Z) - BAR_R - ROD_D / 2
assert _BAR_CLR >= BAR_CLR_MIN, (
    f"the rod (O{ROD_D} at x {ROD_X:+.2f}, z {ROD_Z:+.2f}) comes within {_BAR_CLR:.2f} of a "
    f"bar resting at fret 0 -- the first centimetre could not be barred")

# ── Z extent ───────────────────────────────────────────────────────────────
NUT_TOP  = ROD_Z + ROD_BORE / 2 + 3 * D.BEAD     # a three-bead lid over the rod (user: two printed badly)
NUT_BASE = D.DECK_TOP_Z - D.STRING_Z             # prism base sits on the deck plane

BREAK_ANGLE = 15.0                              # MIN break over the crown, so the CROWN (not the
                                                # rod) terminates the speaking length
assert _break_at(ROD_Z, D.STRING_GAUGE_MAX) >= BREAK_ANGLE, (
    f"a {D.GAUGE_MAX_IN:.3f} in string breaks only {_break_at(ROD_Z, D.STRING_GAUGE_MAX):.2f} deg over "
    f"its crown -- under the {BREAK_ANGLE} floor, so the rod would end the speaking length")


def _break_deg(i: int) -> float:
    return _break_at(ROD_Z, D.STRING_GAUGE[i])


# ── THE WRAP: ONE TURN (user) ────────────────────────────────────────────────
def _touch_angle_g(g: float) -> float:
    """Angle about the rod axis (in the XZ plane, from +X) at which a string of gauge g first
    TOUCHES the wrap circle, coming down off its crown. The UPPER of the two tangents, because
    the string comes in over the rod. THE ONE PLACE THIS IS COMPUTED."""
    hr = ROD_D / 2 + g / 2                       # the string's centre-path radius
    dx, dz = DOWEL_X - ROD_X, -g / 2 - ROD_Z     # rod axis -> crown (the rod sits BELOW)
    return math.atan2(dz, dx) + math.acos(hr / math.hypot(dx, dz))


def touch_angle(i: int) -> float:
    return _touch_angle_g(D.STRING_GAUGE[i])


WRAP_F   = 1.05                                 # axial rise per turn, as a multiple of the gauge:
                                                # the strands lie all but touching, never crossing
# THE TAIL LEAVES DOWN THE -X SIDE (180 deg), heading straight down -- onto the plate's -X face,
# which stands at the rod's own -X tangent, and on down the tail channel to the side screw.
EXIT_DEG = 180.0
WRAPS = 1                                       # whole turns past the entry sweep (user)


def _sweep0_g(g: float) -> float:
    """Turns from where a string of gauge g touches the rod round to the exit tangent, ANGLE
    RISING (-X side down, under, +X side up)."""
    return ((math.radians(EXIT_DEG) - _touch_angle_g(g)) % (2 * math.pi)) / (2 * math.pi)


def wraps_g(g: float) -> float:
    """Turns from first touch to the exit: the entry sweep plus WRAPS whole turns, so the tail
    always leaves on its exit tangent."""
    return _sweep0_g(g) + WRAPS


def wraps(i: int) -> float:
    return wraps_g(D.STRING_GAUGE[i])


def _adv_g(g: float) -> float:
    """How far the coil marches along the rod (always -Y), touch to exit."""
    return wraps_g(g) * WRAP_F * g


def _bottom_crossings(g: float) -> int:
    """How many times the coil passes the rod's underside (270 deg) between touch and exit --
    i.e. how many strands the shelf can meet."""
    a0 = _touch_angle_g(g)
    a1 = a0 + wraps_g(g) * 2 * math.pi
    k0 = math.ceil((a0 - 1.5 * math.pi) / (2 * math.pi))
    return sum(1 for k in range(k0, k0 + 3) if a0 < 1.5 * math.pi + 2 * math.pi * k <= a1)


_STACKED = [g for g in list(D.STRING_GAUGE) + [G_ENVELOPE] if _bottom_crossings(g) != 1]
assert not _STACKED, (
    f"gauges {_STACKED} cross the rod's underside other than once -- the shelf would meet two "
    f"strands (or none) and set the height wrong, which is what one wrap exists to rule out")


def _bottom_y_g(g: float) -> float:
    """Y offset (from the string's own Y) of the one strand under the rod, where the shelf pinches."""
    t = ((1.5 * math.pi - _touch_angle_g(g)) % (2 * math.pi)) / (2 * math.pi)
    return -t * WRAP_F * g


def exit_angle(i: int) -> float:
    return touch_angle(i) + wraps(i) * 2 * math.pi


WRAP_EPS = 0.05                                 # the coil is drawn a hair off the rod


def wrap_radius(i: int) -> float:
    """Radius of string i's coil centreline about the rod axis. THE ONE PLACE THIS IS COMPUTED."""
    return ROD_D / 2.0 + D.STRING_GAUGE[i] / 2.0 + WRAP_EPS


def exit_point(i: int):
    """(x, z) where string i's tail leaves the rod, in the block's local frame."""
    a = exit_angle(i)
    hr = wrap_radius(i)
    return ROD_X + hr * math.cos(a), ROD_Z + hr * math.sin(a)


def exit_dir(i: int):
    """Unit (x, z) the tail is travelling as it leaves: at EXIT_DEG 180, straight down."""
    a = exit_angle(i)
    return -math.sin(a), math.cos(a)


def wrap_y(i: int) -> tuple[float, float]:
    """(start, end) Y of string i's coil. It arrives on its own lane and leaves -Y of it."""
    y0 = D.nut_y(i)
    return y0, y0 - _adv_g(D.STRING_GAUGE[i])


wrap_y_drawn = wrap_y                           # one wrap: what is wound is what the parts are sized for

MU = 0.15                                       # steel on steel, dry, deliberately pessimistic
STRING_T = 147.0                                # per-string tension


def residual(i: int) -> float:
    """Tension the shelf pinch sees: what the capstan leaves between the touch and the strand
    under the rod. The side screw's grip adds to it from behind, x e^(mu.theta) for the 270 deg
    from the shelf round to the exit."""
    t = ((1.5 * math.pi - touch_angle(i)) % (2 * math.pi))
    return STRING_T * math.exp(-MU * t)


# ── THE STEEL PLATE ─────────────────────────────────────────────────────────
# THE HEIGHT IS GAUGE-FREE, which is the whole trick, and it carries over from the printed insert:
#     shelf        = ROD_Z - ROD_D/2 - g      the one strand's underside, where it bears
#     crown centre = -g - PIN_D/2             so every string TOP lands on z = 0
#     difference   = ROD_D/2 - PIN_D/2 - ROD_Z = 12.40, with no g in it
# so one plate serves every gauge: the plate rises until the string stops it.
PLATE_T = 4.0                                   # stock 4 mm 304 (JLCCNC); covers the .070's coil footprint
CROWN_R = PIN_D / 2.0
CROWN_OFF = ROD_D / 2 - CROWN_R - ROD_Z         # 12.40, crown centre above the shelf
PLATE_X0 = ROD_X - ROD_D / 2.0                  # -15.2: the -X face, on the rod's own -X tangent,
                                                # so the tail drops off the rod straight onto it
PLATE_X1 = DOWEL_X + CROWN_R                    # the arm's +X face, tangent to the crown
ARM_X0 = DOWEL_X - CROWN_R                      # the arm's -X face
# THE RAMP (user): the shelf/arm inside corner is a quarter circle, tangent to the shelf right under the
# rod and to the arm's -X face. Threading, a string pushed under the rod slides round it and comes up the
# +X side on its own -- so restringing only drops the plate the threading gap, not the whole way. Its
# centre is straight over the rod's, so it meets the wound strand only where the shelf pinches it, and
# opens away from it from there (asserted below, for the heaviest gauge).
RAMP_R = ARM_X0 - ROD_X                         # 10.05


def _ramp_gap(phi: float, g: float, arm_x0: float = ARM_X0) -> float:
    """Clearance from a clamped strand of gauge g (round the rod) to the ramp, phi from its bottom."""
    r = arm_x0 - ROD_X
    rs = ROD_D / 2.0 + g                        # the strand's outside, about the rod's centre
    d = r - rs                                  # ramp centre above the rod's
    return math.sqrt(r * r + d * d - 2 * r * d * math.cos(phi)) - rs


assert RAMP_R < CROWN_OFF, "the ramp runs past the arm into the crown"
assert all(_ramp_gap(math.radians(a), G_ENVELOPE) > 0.0 for a in range(5, 91, 5)), "the ramp meets the wind"
PLATE_CLR = 0.2                                 # Y slip fit, each side, in the pocket
COIL_AIR = 0.2                                  # the coil to the pocket wall, either side: the aim
COIL_AIR_MIN = 0.15                             # ... and the least accepted
PLATE_CLR_X = 0.15                              # +X: the wall in front of the arm is what is left
                                                # of X_FRONT, and it has to stay a bead (asserted)
POCKET_X1 = PLATE_X1 + PLATE_CLR_X
assert X_FRONT - POCKET_X1 >= D.MIN_WALL - 1e-9, (
    f"{X_FRONT - POCKET_X1:.2f} of wall in front of the plates' arms -- under a bead")


def shelf_z(i: int) -> float:
    """Z of string i's shelf, clamped -- set by the STRING, not by the part: the plate rises until
    the one strand under the rod stops it."""
    return ROD_Z - ROD_D / 2 - D.STRING_GAUGE[i]


# WHERE THE PLATE SITS IN Y, about the string's own Y (user: the string on the plate's middle, every
# pocket and finger the same). The crown is under the string's centre only if the wrap allows: it walks
# -Y, so the -X face has to stand behind the tail (-_adv_g), the side screw (on the plate's middle) has
# to reach it, and the coil's -Y edge has to clear the pocket wall by COIL_AIR. Strings 1-9 share the
# one offset their heaviest needs. String 10's coil is as wide as the pocket allows, so it is centred
# in it (the pocket matches the others, user: no cut-out; a .080 does NOT fit there now).
def _yc_bound(g: float) -> float:
    return min(0.0,
               -_adv_g(g) + PLATE_T / 2.0,                                  # the tail on the -X face
               -_adv_g(g) + D.MIN_WALL_2P,                                  # the screw's tip on the tail
               -_adv_g(g) - g / 2.0 + PLATE_T / 2.0 + PLATE_CLR - COIL_AIR)  # the coil clear of the wall


def _gauges_of(i: int):
    """The gauges string i's slot takes."""
    return (D.STRING_GAUGE[i],)


_YC_SHARED = min(_yc_bound(g) for i in range(D.N_STRINGS - 1) for g in _gauges_of(i))
PLATE_YC = (_YC_SHARED,) * (D.N_STRINGS - 1) + (-_adv_g(D.STRING_GAUGE[-1]) / 2.0,)


def plate_y(i: int) -> float:
    """Y centre of string i's plate (and of its pocket and screws)."""
    return D.nut_y(i) + PLATE_YC[i]


# ── HOW FAR THE PLATE HAS TO DROP TO THREAD, AND THE HEIGHT SCREW UNDER IT ──────────
# Unchanged from the printed insert (user): an M4 x 40 button head, heat-set in the endplate slab
# mouth DOWN, pushes the plate's foot up from below on the instrument's one 2.5 mm key.
from cadkit.fasteners import M4, M4_BUTTON_HEAD_D, M4_BUTTON_HEAD_H
# BOTH SCREWS HERE TAKE THE EXTRA-STRONG POCKET (user, 2026-11-05: overtightened, a height screw
# pulled its insert out of the plastic): each is driven hard against something -- the height screw
# the plate up onto the rod, the side screw the string onto its plate -- so the insert grips 0.1 tighter
# and is started square with the iron rather than dropped in.
M4S = M4.strong()
THREAD_CLR = D.MIN_WALL                         # room to work the string round, not force it
_DROP_NEED = G_ENVELOPE + THREAD_CLR            # 2.832 for a .080
assert _ramp_gap(math.radians(45), G_ENVELOPE) >= THREAD_CLR, "the ramp crowds the wind"
HS_SCREW_L     = 40.0                           # M4 x 40 button, the longest in the shop
HS_CAP         = D.MIN_WALL_2P                  # printed floor over the heat-set
HS_ROD_OVERLAP = 2 * D.BEAD

# THE STACK, from the chassis up (local frame -- Z relative to STRING_Z):
#   motor_bank.FLOOR_TOP  top of the wide corner rib the keyhead sits over (chassis)
#   HS_PRISM_BOT          the heat-sets' mouths, flush in it: a bead over the rib (user: no air gap)
#   HS_FLOOR              the slot's printed floor, over the heat-set
#   HS_TIP_LOW            where a DROPPED plate's foot rests: the tip, screw fully undone
# TIGHTENED ALL THE WAY the shelf stands HS_ROD_OVERLAP up INTO the rod, so you always tighten against
# the string, never against the endplate; clamping any string the head stays over the bed.
# THE RAMP PAYS FOR THE LONG PLATE (user, 2026-11-03): threading only needs the plate down the threading
# gap now, not the crown under the rod, so the screw's travel is just what the room under the mouth gives
# -- and with the heat-sets down on the rib, the same M4 x 40 reaches 10.4 lower, which the plate's body
# takes: more of it held in its pocket.
from . import motor_bank as _MB                  # motor_bank imports only dimensions/helpers/components
HS_HEAD_CLR    = 0.4                             # radial air round a head in its chassis cavity (and over the bed)
HS_HEAD_CAV_D  = M4_BUTTON_HEAD_D + 2 * HS_HEAD_CLR
HS_PRISM_BOT = _MB.FLOOR_TOP + D.BEAD - D.STRING_Z
# ONLY PLAYING HAS TO STAY INSIDE (user, 2026-11-04): clamping the heaviest string, a head hangs no lower
# than HS_HEAD_CLR over the bed; dropped to thread, it may hang out under the instrument.
_HS_HANG     = HS_PRISM_BOT - (_MB.BED_Z - D.STRING_Z) - HS_HEAD_CLR   # a head's room, heaviest string clamped
INS_DROP     = _DROP_NEED                          # under the heaviest string's clamp: just enough to thread
HS_REACH_MAX = _HS_HANG - M4_BUTTON_HEAD_H + INS_DROP   # the tip's whole travel, undone to tightened
assert _HS_HANG - M4_BUTTON_HEAD_H >= G_ENVELOPE + HS_ROD_OVERLAP, "tightened, the shelf never reaches the rod"
HS_TIP_RISE  = HS_SCREW_L - (M4.insert_depth + HS_CAP) - HS_REACH_MAX    # the tip over the floor, undone
_FZ_LOW      = ROD_Z - ROD_D / 2.0 - G_ENVELOPE - INS_DROP
_FZ_TIGHT    = ROD_Z - ROD_D / 2.0 + HS_ROD_OVERLAP
HS_FLOOR     = HS_PRISM_BOT + HS_SCREW_L - HS_TIP_RISE - HS_REACH_MAX
HS_TIP_LOW   = HS_FLOOR + HS_TIP_RISE              # the tip, screw fully undone: a dropped foot rests here
assert abs(HS_FLOOR - (HS_PRISM_BOT + M4.insert_depth + HS_CAP)) < 1e-9, (
    f"the floor over the heat-set is {HS_FLOOR - HS_PRISM_BOT - M4.insert_depth:.2f}, not {HS_CAP}")
HS_HEAD_LOW = HS_PRISM_BOT - _HS_HANG - INS_DROP  # a head's bottom, fully undone (service: under the bed)
# THE PLATE'S BODY reaches from the shelf down to where a DROPPED plate's foot meets the undone tip.
PLATE_BODY_H = _FZ_LOW - HS_TIP_LOW               # 38.16 (33.75 with the head kept in when undone)


def plate_profile(cradle: bool = False) -> cq.Workplane:
    """The plate's outline in XZ, shelf at z = 0, extruded PLATE_T along -Y from y = 0.

    cradle=True is the PRINTED STAND-IN's: the crown is replaced by a Ø4 dowel lying in a cradle
    whose seated dowel puts its top exactly where the crown's is, and the arm grows a bead of
    wall -X of the cradle to hold it. The +X face is the plate's, so it fits the same pocket."""
    zc = CROWN_OFF
    zb = -PLATE_BODY_H

    def ramp(w, ax0):
        r = ax0 - ROD_X
        return (w.lineTo(ax0, r).threePointArc((ax0 - r + r / math.sqrt(2), r - r / math.sqrt(2)), (ROD_X, 0.0))
                .lineTo(PLATE_X0, 0.0).close())
    if not cradle:
        w = (cq.Workplane("XY").moveTo(PLATE_X0, zb).lineTo(PLATE_X1, zb).lineTo(PLATE_X1, zc)
             .threePointArc((DOWEL_X, zc + CROWN_R), (ARM_X0, zc)))
        solid = ramp(w, ARM_X0).extrude(PLATE_T)
    else:
        ax0 = STANDIN_ARM_X0
        solid = ramp(cq.Workplane("XY").moveTo(PLATE_X0, zb).lineTo(PLATE_X1, zb)
                     .lineTo(PLATE_X1, STANDIN_TOP).lineTo(ax0, STANDIN_TOP), ax0).extrude(PLATE_T)
        solid = solid.cut(cq.Workplane("XY").center(DOWEL_X, STANDIN_CRADLE_Z)
                          .circle(STANDIN_CRADLE_D / 2.0).extrude(PLATE_T))
        # NO FIN (print_check): the cradle breaks out through the +X face, leaving a wedge between the
        # two. The +X side stops where that wall is a bead wide, a flat; the seat still wraps past the
        # bottom far enough to hold the dowel against the string's small +X pull.
        solid = solid.cut(box_at(10.0, 20.0, 10.0, x=DOWEL_X + 5.0, y=STANDIN_LIP_Z + 10.0, z=PLATE_T / 2))
    # (x, z) drawn in XY, thickness along +Z: turn it so z lands on Z and the thickness runs -Y
    return solid.rotate((0, 0, 0), (1, 0, 0), 90.0)


# THE STAND-IN (user): printed PCTG, flat on a Y face, so its outline is the printer's XY -- its most
# accurate axes -- and the cradle prints round. The dowel's fit is the old cradle's 0.3; its centre is
# raised by half of it, so a SEATED dowel's top lands where the crown's does.
STANDIN_FIT = 0.1                               # off the Y faces and the +X face (printed part, steel pocket)
STANDIN_CRADLE_D = PIN_D + 0.3
STANDIN_CRADLE_Z = CROWN_OFF + (STANDIN_CRADLE_D - PIN_D) / 2.0
STANDIN_TOP = STANDIN_CRADLE_Z                  # the arm stops at the cradle's centre: the dowel lifts in
STANDIN_ARM_X0 = DOWEL_X - STANDIN_CRADLE_D / 2.0 - D.MIN_WALL     # one bead: the string runs low over it
_LIP_DX = (PLATE_X1 - STANDIN_FIT - D.MIN_WALL) - DOWEL_X       # cradle centre to a bead in from the face
STANDIN_LIP_Z = STANDIN_CRADLE_Z - math.sqrt((STANDIN_CRADLE_D / 2.0) ** 2 - _LIP_DX ** 2)
INSERT_UP = (0.0, 1.0, 0.0)                     # the stand-in's build axis: flat on its -Y face


def _place(solid: cq.Workplane, i: int, t: float) -> cq.Workplane:
    """Put a profile solid (shelf at z 0, thickness -Y from 0) on string i, thickness t centred."""
    return solid.translate((0.0, plate_y(i) + t / 2.0, shelf_z(i)))


def plate(i: int) -> cq.Workplane:
    """String i's steel plate, clamped on its string (local frame)."""
    return _place(plate_profile(), i, PLATE_T)


def standin(i: int) -> cq.Workplane:
    """String i's printed stand-in, clamped (local frame): the plate's outline with a dowel cradle,
    thinned and set back by STANDIN_FIT on the faces that slide."""
    s = (plate_profile(cradle=True)
         .intersect(box_at(PLATE_X1 - STANDIN_FIT - (PLATE_X0 - 1.0), PLATE_T - 2 * STANDIN_FIT, 200.0,
                           x=(PLATE_X1 - STANDIN_FIT + PLATE_X0 - 1.0) / 2, y=-PLATE_T / 2, z=0.0)))
    return _place(s, i, PLATE_T)


def standin_dowel(i: int) -> cq.Workplane:
    """The Ø4 x 4 dowel in string i's stand-in, seated (its top on the string's underside)."""
    from . import components as C
    g = D.STRING_GAUGE[i]
    return C.dowel().translate((DOWEL_X, plate_y(i), -g - PIN_D / 2))


# The string must pass over the stand-in's arm, which stands -X of the crown: for every gauge.
_NECK_AIR = min(-g - (DOWEL_X - STANDIN_ARM_X0) * math.tan(math.radians(_break_at(ROD_Z, g)))
                - (-g - PIN_D / 2 - CROWN_OFF + STANDIN_TOP) for g in (D.STRING_GAUGE[0], G_ENVELOPE))
assert _NECK_AIR > 0.0, f"the string runs {-_NECK_AIR:.2f} into its stand-in's arm"


# ── THE PLATE MEETS EVERY STRAND IT HAS TO (asserted, every gauge the endplate takes) ──────
def _plate_lo(i: int) -> float:
    return PLATE_YC[i] - PLATE_T / 2.0


def _plate_hi(i: int) -> float:
    return PLATE_YC[i] + PLATE_T / 2.0


for _i in range(D.N_STRINGS):
    for _g in _gauges_of(_i):
        assert _plate_lo(_i) + _g / 2 <= _bottom_y_g(_g) <= _plate_hi(_i) - _g / 2, (
            f"a {_g / 25.4:.3f} in string's strand under the rod is not wholly over the shelf")
        assert _plate_lo(_i) <= -_adv_g(_g) <= _plate_hi(_i), (
            f"a {_g / 25.4:.3f} in string's tail drops off the rod past the plate's -X face")

# ── THE POCKET: one per string, a rectangle, open to the sky ─────────────────────────
# Its Y span is the plate plus its fit. The coil has to fit it too -- the string arrives on its own Y,
# its +Y edge g/2 over -- with COIL_AIR to the finger for the demo set; the tail channel below it is the
# same width, except string 10's, which has no neighbour -Y and opens out for the heaviest tail.
POCKET_HI = tuple(_plate_hi(i) + PLATE_CLR for i in range(D.N_STRINGS))
POCKET_LO = tuple(_plate_lo(i) - PLATE_CLR for i in range(D.N_STRINGS))
for _i in range(D.N_STRINGS):
    for _g in _gauges_of(_i):
        assert POCKET_HI[_i] - _g / 2 >= COIL_AIR_MIN - 1e-9, (
            f"a {_g / 25.4:.3f} in string arrives {POCKET_HI[_i] - _g / 2:.2f} off its finger")
        _lo = -_adv_g(_g) - _g / 2
        assert _lo >= POCKET_LO[_i] + COIL_AIR_MIN - 1e-9, (
            f"a {_g / 25.4:.3f} in string's last strand reaches {POCKET_LO[_i] - _lo:.2f} into the finger")
# the finger between string i and string i + 1 (-Y of it)
FINGER_W = min(D.NUT_PITCH + POCKET_LO[i] - POCKET_HI[i + 1] for i in range(D.N_STRINGS - 1))
assert FINGER_W >= D.MIN_WALL_2P - 1e-9, f"{FINGER_W:.2f} fingers between the pockets"

# THE TAIL CHANNEL: the string drops off the rod's -X side, so the channel is the strip -X of the
# plate's face, wide enough for the heaviest tail and the screw to back off past it.

# ── THE SIDE SCREWS (user): one per string, from the -X face, pinning the tail to the plate ──────
# An M4 x 10 button head on the one 2.5 mm key, in an M4 heat-set. It prints round: its axis is the
# build direction. THE HEADS SIT INSIDE THE PLASTIC (user, 2026-11-03): each in its own recess, and the
# whole endplate grows -X, legs and all (user), until the heaviest string's head -- the one that stands
# furthest out -- is in.
# From the plate's -X face outward: the tail channel; a clearance bore; the heat-set, its mouth on the
# recess floor; the recess, open in the bed face.
SS_SCREW_L = 10.0
assert SS_SCREW_L in D.M4_BUTTON_STOCK_L and HS_SCREW_L in D.M4_BUTTON_STOCK_L, "a screw we cannot buy"
SS_HEAD_D = M4_BUTTON_HEAD_D + D.BEAD            # 8.4: the head's recess
SS_HEAD_GAP = 0.5                                # the lightest string's head stands this clear of the floor


def _ss_tip_x(g: float) -> float:
    """X of the screw's tip, clamped on a tail of gauge g."""
    return PLATE_X0 - WRAP_EPS - g


TAIL_W = math.ceil((G_ENVELOPE + THREAD_CLR) / D.BEAD) * D.BEAD
POCKET_X0 = PLATE_X0 - TAIL_W                    # the tail channel's -X wall
SS_MOUTH_X = _ss_tip_x(min(D.STRING_GAUGE)) - SS_SCREW_L + SS_HEAD_GAP    # the recess floor
assert SS_MOUTH_X + M4.insert_depth <= POCKET_X0 - D.MIN_WALL, "the side heat-set runs into the channel"
_SS_HEAD_BACK = _ss_tip_x(G_ENVELOPE) - SS_SCREW_L - M4_BUTTON_HEAD_H
# IT GROWS BY WHOLE LEVER PITCHES. The floor's mortise grid is centred end to end, so a keyhead grown
# by anything else shifts every station (and the legs' lock pins miss their tenons); grown by a pitch,
# the grid gains one station at -X and the +X chassis segments stay exactly as they were. The motor
# board and the height screws stay put (user); the -X legs move out with the face.
_KH_W_HELD = X_FRONT + 22.862741699796957        # the stow-bore keyhead's thickness, the grid's phase
KEYHEAD_W = _KH_W_HELD + math.ceil((X_FRONT - _SS_HEAD_BACK - _KH_W_HELD) / D.LEVER_PITCH - 1e-9) * D.LEVER_PITCH
X_BACK = X_FRONT - KEYHEAD_W                     # the bed face
# THE LANES (user: hand threading): the pocket carried out through the -X face, above LANE_FLOOR, so a
# finger can reach under the rod either side. The recesses sit below them with a two-bead wall.
LANE_FLOOR = ROD_Z - ROD_D / 2.0 - _DROP_NEED
SS_Z_A = math.floor((LANE_FLOOR - D.MIN_WALL_2P - SS_HEAD_D / 2.0) / D.BEAD) * D.BEAD


def _solve_ss_dz() -> float:
    """The least whole-bead Z between the two screw rows that leaves two beads of web between
    neighbouring head recesses (they alternate rows, string to string)."""
    for n in range(1, 41):
        dz = n * D.BEAD
        if math.hypot(D.NUT_PITCH, dz) - SS_HEAD_D >= D.MIN_WALL_2P - 1e-9:
            return dz
    raise AssertionError("no row spread leaves a two-bead web between the side screws")


SS_DZ = _solve_ss_dz()
SS_ROWS = (SS_Z_A, SS_Z_A - SS_DZ)
# THE SCREW'S Y: the plate's middle -- its clearance bore is the channel's width
SS_YC = PLATE_YC
assert all(abs(-_adv_g(g) - SS_YC[i]) <= D.MIN_WALL_2P
           for i in range(D.N_STRINGS) for g in _gauges_of(i)), "the side screw's tip misses a tail"
# THE TAIL CANNOT SNEAK PAST THE SCREW (user, 2026-11-05: the 4.4 channel let a string run by the
# screw's side). Below the lanes the channel is TAIL_W wide on the screw's axis, so even the thinnest
# string's centre stays inside the tip's flat face (the thread's minor diameter, ~3.14), and the
# heaviest still drops through. The plate's 0.2 of -X clearance is too thin to hide a string in.
# The screw's own clearance bore runs on across the channel to the plate's face (the M4 is wider than
# the channel), so at the screw the channel is a 4.4 round hole only 4.4 tall, and the narrow channel
# above and below it holds the string in line under the tip.
_SS_TIP_R = (M4.screw_d - 1.227 * 0.7) / 2.0    # the M4 coarse thread's minor radius, the flat tip
assert TAIL_W / 2.0 - min(D.STRING_GAUGE) / 2.0 <= _SS_TIP_R, "a thin tail can sit off the screw's tip"
assert TAIL_W >= G_ENVELOPE + D.BEAD / 2.0, "the narrowed tail channel pinches the heaviest string"
assert PLATE_CLR < min(D.STRING_GAUGE), "a thin string fits in the plate's clearance beside the channel"
# THE PLIER WINDOW (user): one slot across every string, below the side screws and open in the bed
# face, with no fingers in it -- the tails hang across it, and pliers pull each one down tight before
# its screw goes in. Its roof is a plain bridge in the -X -> +X build (user: its depth does not matter).
# IT SITS AT THE BOTTOM (user): its floor is the tail channels' blind floor, two beads over the height
# prism's bottom, so everything from its roof up to the plates and side screws stays solid.
TAIL_Z_END = HS_PRISM_BOT + D.MIN_WALL_2P       # the channels' floor, and the window's: as deep as the
                                                # endplate goes (user) -- the rib is the chassis's floor
WIN_H = 25 * D.BEAD                             # 20.0 (user)
WIN_LO = TAIL_Z_END
WIN_HI = WIN_LO + WIN_H
assert WIN_HI <= SS_ROWS[1] - SS_HEAD_D / 2.0 - D.MIN_WALL_2P, "the window runs up into the side screws"
# TRIMMING: the tail is pushed to the floor, marked level with the window's top edge, and cut
# TAIL_CUT below the mark. Put back, it ends half way down the window: the top half to grip, the bottom
# half to pull it down into.
TAIL_CUT = WIN_H / 2.0
TAIL_END = WIN_HI - TAIL_CUT                    # where a tail ends, trimmed
assert TAIL_END - WIN_LO >= 8.0, "a trimmed tail has no room to be pulled down"
# THE RAMP (user, 2026-11-04): a 45 degree fill in the window's floor/+X corner, so the +X face -- a
# ceiling in the -X -> +X build -- bridges WIN_H - WIN_RAMP instead of the whole window. It stays under
# a trimmed tail's end, and the tail channels are cut through it, so a tail still drops to the floor.
WIN_RAMP = 12 * D.BEAD                          # 9.6
assert WIN_RAMP <= TAIL_CUT, "the ramp climbs past a trimmed tail's end"
# the plate's -X face has to stand behind both rows wherever a string clamps it
for _g in (D.STRING_GAUGE[0], G_ENVELOPE):
    _bot = ROD_Z - ROD_D / 2 - _g - PLATE_BODY_H
    assert SS_ROWS[1] - M4.screw_d / 2.0 >= _bot + D.MIN_WALL_2P, "a side screw lands below its plate"


def ss_row(i: int) -> int:
    return i % 2


def side_screw_yz(i: int):
    return D.nut_y(i) + SS_YC[i], SS_ROWS[ss_row(i)]


def side_screw_negatives(i: int):
    """Head recess (open in the bed face), heat-set pocket (mouth on its floor) and clearance on
    across the tail channel to the plate's face. Along the build direction, so plain round bores -- and each step down
    in diameter is a ceiling over the wider bore, so stepped_bore_cutter cones it at 45 degrees."""
    from cadkit.fasteners import stepped_bore_cutter
    y, z = side_screw_yz(i)
    pilot = M4S.pilot_d((1.0, 0.0, 0.0), PRINT_UP)
    return [stepped_bore_cutter([(SS_HEAD_D, SS_MOUTH_X - X_BACK + 1.0),
                                 (pilot, M4.insert_depth),
                                 (M4.shaft_clr_d, PLATE_X0 - SS_MOUTH_X - M4.insert_depth)],
                                (X_BACK - 1.0, y, z), (1.0, 0.0, 0.0), print_up=PRINT_UP)]


def side_screw(i: int) -> cq.Workplane:
    """Dummy M4 x 10 button head, tip on string i's tail (local frame)."""
    from cadkit.fasteners import m4_button_screw
    y, z = side_screw_yz(i)
    tip = _ss_tip_x(D.STRING_GAUGE[i])
    s = m4_button_screw(SS_SCREW_L).rotate((0, 0, 0), (0, 1, 0), -90)   # head x 0..h, shank on to h + L
    return s.translate((tip - (M4_BUTTON_HEAD_H + SS_SCREW_L), y, z))


def side_insert(i: int) -> cq.Workplane:
    from cadkit.fasteners import seated_insert
    y, z = side_screw_yz(i)
    return seated_insert(M4S, (SS_MOUTH_X, y, z), (1.0, 0.0, 0.0))


def tail_route(i: int):
    """The tail's route from the rod, as (x, z) points: straight down the plate's -X face to the
    channel's floor."""
    x0, z0 = exit_point(i)
    return [(x0, z0), (x0, TAIL_END)]


# ── THE HEIGHT SCREWS: two X rows under the plates' feet ─────────────────────────────
# The heads hang side by side in the chassis rib, each in its own HS_HEAD_CAV_D cavity, and on the
# string pitch those would run together -- so the strings alternate between two X rows, as before,
# both under the plate's foot and centred on it.
SKU_C = D.N_STRINGS - 1


def _row_of(i: int) -> int:
    return (SKU_C - i + 1) % 2


def _solve_row_dx() -> float:
    """The smallest whole-bead row spread whose neighbouring head cavities keep MIN_WALL_2P of web."""
    for n in range(1, 41):
        dx = n * D.BEAD
        if math.hypot(dx, D.NUT_PITCH) - HS_HEAD_CAV_D >= D.MIN_WALL_2P - 1e-9:
            return dx
    raise AssertionError("no row spread leaves a two-bead web between the head cavities")


HS_ROW_DX = _solve_row_dx()
# as far +X as the plate's foot allows: the heads hang into the chassis rib, and -X of these the
# keyhead's own foot-box walls stand
_HS_ROW_B = PLATE_X1 - D.MIN_WALL - M4.shaft_clr_d / 2.0
HS_ROWS = (_HS_ROW_B - HS_ROW_DX, _HS_ROW_B)
assert (HS_ROWS[0] - M4.shaft_clr_d / 2 >= PLATE_X0 + D.MIN_WALL
        and HS_ROWS[1] + M4.shaft_clr_d / 2 <= PLATE_X1 - D.MIN_WALL), "a height screw misses its plate's foot"


def height_screw_xy(i: int):
    """(x, y) of string i's height screw, local frame: its row, under the plate's middle."""
    return HS_ROWS[_row_of(i)], plate_y(i)


def plate_foot_z(i: int) -> float:
    return shelf_z(i) - PLATE_BODY_H


def screw_reach(i: int) -> float:
    """How far above the floor string i's screw tip stands when that plate is clamped."""
    return plate_foot_z(i) - HS_TIP_LOW


def height_screw_negatives(i: int):
    """Heat-set pocket (mouth in the bottom face) and shank/tip bore for string i, TEARDROPS along Z
    (sideways to the -X -> +X build), apex +X. The head hangs below the part, in the chassis."""
    x, y = height_screw_xy(i)

    def bore(d, z0, z1):
        return teardrop_hole(d, z1 - z0, axis_point=(x, y, z0), axis_dir=(0.0, 0.0, 1.0),
                             print_up=PRINT_UP)
    return [bore(M4S.pilot_d((0.0, 0.0, 1.0), PRINT_UP), HS_PRISM_BOT - 1.0,
                 HS_PRISM_BOT + M4.insert_depth),
            bore(M4.shaft_clr_d, HS_PRISM_BOT + M4.insert_depth - 0.01, HS_FLOOR + 1.0)]


def height_screw(i: int) -> cq.Workplane:
    """Dummy M4 x 40 button head, head DOWN, tip on string i's clamped plate foot (local frame)."""
    from cadkit.fasteners import m4_button_screw
    x, y = height_screw_xy(i)
    tip = HS_TIP_LOW + screw_reach(i)
    s = m4_button_screw(HS_SCREW_L).rotate((0, 0, 0), (1, 0, 0), 180)   # head z 0..h, shank up to h + L
    return s.translate((x, y, tip - (M4_BUTTON_HEAD_H + HS_SCREW_L)))


def height_insert(i: int) -> cq.Workplane:
    """Dummy M4 heat-set under string i, mouth flush in the prism's bottom face (local frame)."""
    from cadkit.fasteners import seated_insert
    x, y = height_screw_xy(i)
    return seated_insert(M4S, (x, y, HS_PRISM_BOT), (0.0, 0.0, 1.0))


for _i in range(D.N_STRINGS):
    assert 0.0 <= screw_reach(_i) <= HS_REACH_MAX + 1e-9, f"string {_i + 1}'s screw reach is out of range"
    assert HS_HEAD_LOW + screw_reach(_i) >= _MB.BED_Z - D.STRING_Z + HS_HEAD_CLR - 1e-9, (
        f"playing, string {_i + 1}'s height-screw head hangs below the bed")


# ── THE CUTS ───────────────────────────────────────────────────────────────────
Z_SKY = NUT_TOP + 1.0


def _y_span(i: int):
    return D.nut_y(i) + POCKET_LO[i], D.nut_y(i) + POCKET_HI[i]


def insert_pocket(i: int) -> cq.Workplane:
    """String i's pocket: the plate's slot from the height screws' floor to the sky, and the tail
    channel -X of it down to its floor. A PRISM IN Z -- the plate does not sit in it, it TRAVELS.
    Below the lanes the channel narrows to TAIL_W on the side screw's axis, through a 45 degree funnel."""
    y0, y1 = _y_span(i)
    slot = box_at(POCKET_X1 - (PLATE_X0 - PLATE_CLR), y1 - y0, Z_SKY - HS_FLOOR,
                  x=(POCKET_X1 + PLATE_X0 - PLATE_CLR) / 2, y=(y0 + y1) / 2, z=(Z_SKY + HS_FLOOR) / 2)
    xc, xl = (PLATE_X0 + 0.5 + POCKET_X0) / 2, PLATE_X0 + 0.5 - POCKET_X0
    chan = box_at(xl, y1 - y0, Z_SKY - LANE_FLOOR, x=xc, y=(y0 + y1) / 2, z=(Z_SKY + LANE_FLOOR) / 2)
    ys = D.nut_y(i) + SS_YC[i]
    narrow = box_at(xl, TAIL_W, LANE_FLOOR - TAIL_Z_END + 0.01, x=xc, y=ys,
                    z=(LANE_FLOOR + TAIL_Z_END) / 2)
    # the funnel: each side wall leans in at 45 degrees from the full width down to TAIL_W
    fz = max(y1 - ys, ys - y0) - TAIL_W / 2
    funnel = (cq.Workplane("YZ").polyline([(y0, LANE_FLOOR + 0.01), (y1, LANE_FLOOR + 0.01),
                                           (ys + TAIL_W / 2, LANE_FLOOR - fz),
                                           (ys - TAIL_W / 2, LANE_FLOOR - fz)]).close()
              .extrude(xl).translate((POCKET_X0, 0.0, 0.0)))
    return slot.union(chan).union(narrow).union(funnel)


def all_pockets() -> cq.Workplane:
    """Every pocket, FUSED and subtracted once (ten short booleans against a busy body left cores)."""
    out = None
    for i in range(D.N_STRINGS):
        k = insert_pocket(i)
        out = k if out is None else out.union(k)
    return out


def lanes() -> cq.Workplane:
    """Every lane's way out -X, LANE_FLOOR to sky: the pocket carried past the bed face."""
    out = None
    for i in range(D.N_STRINGS):
        y0, y1 = _y_span(i)
        k = box_at(POCKET_X0 + 0.5 - (X_BACK - 1.0), y1 - y0, Z_SKY - LANE_FLOOR,
                   x=(POCKET_X0 + 0.5 + X_BACK - 1.0) / 2, y=(y0 + y1) / 2, z=(Z_SKY + LANE_FLOOR) / 2)
        out = k if out is None else out.union(k)
    return out


def plier_window() -> cq.Workplane:
    """The window across every string's tail, from past the bed face in to the plates' slots."""
    y0, y1 = D.nut_y(SKU_C) + POCKET_LO[SKU_C], D.nut_y(0) + POCKET_HI[0]
    x0, x1 = X_BACK - 1.0, PLATE_X0 - PLATE_CLR
    win = box_at(x1 - x0, y1 - y0, WIN_H, x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(WIN_LO + WIN_HI) / 2)
    ramp = (cq.Workplane("XZ").polyline([(x1 + 0.01, WIN_LO - 0.01), (x1 - WIN_RAMP - 0.01, WIN_LO - 0.01),
                                         (x1 + 0.01, WIN_LO + WIN_RAMP + 0.01)]).close()
            .extrude(y1 - y0 + 2.0, both=True).translate((0.0, (y0 + y1) / 2, 0.0)))
    return win.cut(ramp)


def all_side_screw_negatives() -> cq.Workplane:
    out = None
    for i in range(D.N_STRINGS):
        for k in side_screw_negatives(i):
            out = k if out is None else out.union(k)
    return out


# ── THE ROD AND THE BLOCK'S Y EXTENT ──────────────────────────────────────────────
# The rod is whole in the block, flush with its -Y face, to ROD_END_W of wall at +Y, its stop. The
# wall has a hole on its axis for the 2.5 key, pushed in from +Y to send the rod back out.
ROD_L  = D.BRIDGE_AXLE_L
ROD_END_W = D.MIN_WALL_2P
ROD_PUSH_D = 4 * D.BEAD
# THE END BLOCKS MATCH on the +X face (keyhead_endplate checks it on the finished solid), so they are
# sized off the POCKETS there; string 10's wider tail channel is -X of the plate and eats into its own.
_INS_HI = D.nut_y(0) + POCKET_HI[0]              # string 1's pocket, +Y
_FACE_LO = D.nut_y(SKU_C) + POCKET_LO[SKU_C]     # string 10's pocket, -Y
_INS_LO = _FACE_LO                               # the cuts' -Y extreme
END_BLOCK_W = (ROD_L + ROD_END_W - (_INS_HI - _FACE_LO)) / 2.0
HW   = _INS_HI + END_BLOCK_W                     # the +Y face
Y_LO = _FACE_LO - END_BLOCK_W                    # the -Y face
ROD_Y0, ROD_Y1 = Y_LO, Y_LO + ROD_L
assert _INS_LO - Y_LO >= D.MIN_WALL_2P, f"{_INS_LO - Y_LO:.2f} of end block -Y of string 10's channel"
# THE HEIGHT PRISM'S +X FACE STAYS WHERE THE MOTOR BANK WAS LAID OUT FROM (dimensions.KEYHEAD_INBOARD_X):
# keyhead_endplate stands it a two-bead wall past this. The plates' pockets end well short of it, so below
# the deck the wall in front of them -- which takes the side screws' push -- is thick.
HS_POCKET_X1 = D.KEYHEAD_INBOARD_X - D.NUT_BLOCK_X - D.MIN_WALL_2P
assert HS_POCKET_X1 >= POCKET_X1 + D.MIN_WALL_2P, "the height prism stops short of walling the pockets"
# Bending in the rod over its worst span: every finger holds it now, so a span is one pocket.
_I = math.pi * ROD_D ** 4 / 64.0
_SPAN = PLATE_T + 2 * PLATE_CLR
_SPAN_MPA = ((STRING_T / _SPAN) * _SPAN ** 2 / 8.0) / (_I / (ROD_D / 2))
assert _SPAN_MPA <= 250.0, f"the rod carries {_SPAN_MPA:.0f} MPa over a {_SPAN:.1f} mm pocket"


_TOP_BAR = min(math.hypot(x - DOWEL_X, NUT_TOP - BAR_R) - BAR_R
               for x in [X_BACK + (X_FRONT - X_BACK) * k / 50.0 for k in range(51)])
assert _TOP_BAR >= BAR_CLR_MIN, f"the block's top stands {_TOP_BAR:.2f} from the bar at fret 0"


def _build() -> cq.Workplane:
    # ONE solid prism under a level top, and every feature is CUT from it.
    pts = [(X_BACK, NUT_TOP), (X_FRONT, NUT_TOP), (X_FRONT, NUT_BASE), (X_BACK, NUT_BASE)]
    body = cq.Workplane("XZ", origin=(0.0, HW, 0.0)).polyline(pts).close().extrude(HW - Y_LO)
    body = body.cut(all_pockets())
    body = body.cut(lanes())
    # THE ROD BORE. BLIND at +Y: that wall is the rod's +Y stop. It slides in from -Y through every
    # finger at once, so it must be a precision shaft and not a dowel.
    body = body.cut(rod_bore())
    return body


def rod() -> cq.Workplane:
    """The wrap rod itself, in the nut block's local frame — the bridge axle's shaft."""
    return cyl_y(ROD_D, ROD_Y1 - ROD_Y0, y0=ROD_Y0, x=ROD_X, z=ROD_Z)


def rod_bore() -> cq.Workplane:
    """The rod's bore, in the local frame: open at -Y (the rod slides in there), stopped at +Y but
    for the key's hole. It runs the rod's whole length past its seat, so the rod can start from
    outside the -Y face."""
    return teardrop_hole(ROD_BORE, (ROD_Y1 - ROD_Y0) + ROD_L,
                         axis_point=(ROD_X, ROD_Y0 - ROD_L, ROD_Z),
                         axis_dir=(0.0, 1.0, 0.0), print_up=PRINT_UP).union(
        teardrop_hole(ROD_PUSH_D, ROD_END_W + 2.0, axis_point=(ROD_X, ROD_Y1 - 1.0, ROD_Z),
                      axis_dir=(0.0, 1.0, 0.0), print_up=PRINT_UP))


nut_block = _build()
