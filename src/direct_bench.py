"""DIRECT BENCH -- every string's screw driven straight off its own NEMA17, no belt (user, 2026-11-09).

A fit study like src.changer_bench: bought parts as they are, printed frames as plain blocks, the
instrument's limits (pickup, deck, side walls, keyhead) as GHOSTS the overlap gate measures. Held
from the instrument: the crown at NUT_BLOCK_X, the bridge bearings (STRING_Z), the strings fanning
from nut_y to string_y (9.5), Tr8x2 screws and the brass H-nut, CARRIAGE_TRAVEL, SERVO42D motors.

THE LAYOUT
 1. TWO BENDS. Every string leaves the bridge bearing straight DOWN on one line (x = 0), and turns
    -X under a SECOND 688 at its row's depth. The rows' axles all sit on x = -8 under the bridge
    axle: a string dropping to a lower row passes 4 mm outside every upper axle (its surface is at
    x = -4) and 7 mm beside the upper rows' bearings (they sit only at their own strings' Y).
 2. THREE ROWS, string i on row i % 3, DZ apart. A screw passes other strings' motors on its way
    to its own, so a neighbour closer than the motor's half-width + the screw in Y (9.5 and 19
    both are) has to be DZ >= 21.15 + 4 + clearance away in Z. Strings three apart (28.5) clear
    in Y, so three rows are the fewest.
 3. THE SCREW LIES ALONG -X and the nut rides it: the string pulls the nut +X, the screw is in
    TENSION into its two 688s at the motor end. A yoke on the nut's +X face holds the ball end on
    the screw axis (no couple, the X rig's yoke), a Ø3.5 rod through the nut's other ear keeps it
    from turning.
 4. THE SPRING WRAPS THE SCREW. An extension spring from a collar on the nut's boss back to one
    common ANCHOR WALL pulls the nut -X, on the axis. A fixed sleeve over the screw keeps the coils
    off the turning threads. It stops at the wall rather than running back to the motor: a Ø16
    spring passing the other motors would need ~30 of row pitch where the Ø8 screw needs 26.
 5. MOTORS COAXIAL, staggered along X in STATIONS. Two motors need different stations if their
    bodies overlap in YZ (closer than 44.7 in both Y and Z): rows 0 and 2 are 2 DZ apart, so they
    share; strings 57 apart on a row share. Four stations.
 6. EVERYTHING ON AXIS (user, 2026-11-09): every screw and motor runs straight along X under its
    own string, no yaw. String 1's motor then stands past today's +Y rail (42.75 + 21.15 > 54.75),
    and the rail MOVES OUT to clear it (RAIL_HI, "I don't mind the width change at the +y side").

    py -3.12 -m src.direct_bench          -> the layout report;   --gate -> the overlap gate
    view: scope src.direct_bench --attr assembly, `agent_sync.py view --solo`
"""

from __future__ import annotations

import math
import re as _re
from functools import lru_cache as _lru_cache

from cadkit.kept import kept

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_x, cyl_y, ball_bearing


def cyl_z(d: float, length: float, z0: float, *, x: float = 0.0, y: float = 0.0) -> cq.Workplane:
    """Solid cylinder along +Z from z0, centred on (x, y) (helpers has X and Y only)."""
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        d / 2, length, pnt=cq.Vector(x, y, z0), dir=cq.Vector(0, 0, 1)))

N = D.N_STRINGS
# THE TRAVEL (user, 2026-11-12): from the slack end (keyhole plate on the endplate, the screw just
# threading the nut) to where the nut may pull. Restringing leaves an unknown slack the motor
# takes up, so the travel covers slack -> open -> +3 st on the stretchiest string with hand slack
# to spare (E9's G#4: ~0.0-5 + 6.3 + 2.6 = ~14). It stops 1 mm short of the tightest spring's
# coils closing (string 10, 16.6 from the slack end); the screw tip would only reach the ball
# at ~23.9.
T_TRAVEL = 15.6
T_OPEN = D.DL_OPEN / T_TRAVEL                       # open pitch, from the slack end

# ── rows ────────────────────────────────────────────────────────────────────────────────────
R = D.BRG688_OD / 2                                 # 8, every bend
BR_C = (D.BRIDGE_AXLE_X, D.BRIDGE_BEARING_Z)        # (-8, 8)
X_DROP = BR_C[0] + R                                # 0: every string's drop line
X_BEND = X_DROP - R                                 # -8: the bend axles, and the exit point
Z_TOP = -32.0                                       # row 0: the nut's ears (22) under the pickup (-20)
DZ = 26.4                                           # 21.15 + 4 + 0.5 + the gauges' half-diameters
LEVELS = 3


def level(i: int) -> int:
    return i % LEVELS


def z_level(k: int) -> float:
    """The string's exit height under row k's bend = the screw axis (less half the gauge)."""
    return Z_TOP - k * DZ


def za(i: int) -> float:
    """String i's screw axis: the string's centre leaving its bend."""
    return z_level(level(i)) - D.STRING_GAUGE[i] / 2


def y_of(i: int) -> float:
    return D.string_y(i)


# ── along the screw (x, before the yaw) ─────────────────────────────────────────────────────
# THE YOKE'S M3s (user, 2026-11-12): from behind the collar, through the flange and the printed
# spacer, tapped into the keyhole plate, the tip 0.5 under its +X face. So the screw's length sets
# the yoke, and the yoke sets the gap from the nut to the ball -- the one lever on travel (the
# screw tip may come up to the ball). M3 x 30 (McMaster 91292A022; user 2026-11-12: travel to
# spare), a different SKU from the bar clamp's (two SKUs, user 2026-11-12).
KEY_M3_L = 30.0
YK_H = KEY_M3_L - 6.0                               # 24: flange face -> plate's +X face (the head
                                                    # 3, collar 3, flange 3.5 behind; tip 0.5 short)
# THE KEYHOLE PLATE (user, 2026-11-12: a ball end on a 2.4 printed roof is ~8 mm^2 of plastic
# under the whole string, and the yoke's M3s threaded into plastic -- neither holds for years).
# The roof is now a LASER-CUT 304 PLATE, 4 mm, the nut plates' sheet (one JLCCNC order): the
# keyhole is cut in it and the yoke's two M3s are TAPPED into it, so the string goes ball ->
# steel plate -> steel screws -> collar -> nut, with no thread in plastic. The printed yoke
# behind it only spaces it and shapes the ball's pocket. YK_H (flange face -> plate's +X face)
# is unchanged; the plate is its last YK_ROOF.
YK_ROOF = 4.0                                       # the keyhole plate's thickness
YK_D = D.NUT_FLANGE_L                               # 22: round, as the nut's flange
BRG_CLR = 1.0                                       # the endplate's face off the bend bearings' rim
# the rods' plate (and the balls' windows), the endplate's -X wall: its +X face BRG_CLR off the
# bend bearings' rim (user, 2026-11-12), its thickness whole beads, chosen for the load by the
# FEA (tools: the endplate under the strings' open-pitch pull, sustained). Its -X face is x_j,
# where the body's walls and floor end.
EP_PLATE_N = 4                                      # beads: FEA 2026-11-12, with the axles in their
                                                    # bores, 3.2 / 4.8 / 7.2 thick read 8.9 / 8.8 / 8.6
                                                    # MPa peak at open pitch: the axles tie the fingers,
                                                    # the plate barely matters; 3.2 clears the pickup
ROD_PLATE = (X_BEND - R - BRG_CLR - EP_PLATE_N * D.BEAD, X_BEND - R - BRG_CLR)
# THE DRIVE'S PLACE ALONG X (user, 2026-11-12: "tons of space at -X: move the motors, anchor, etc
# -X to make room for the 30 mm screw"). At the slack end the yoke's +X face stands YK_CLR off the
# endplate's plate; the nut, collar, springs, plugs, anchor plate and motors all sit DRIVE_DX
# further -X than the 2026-11-11 layout (nut flange at -42, anchor at -190), so the springs and
# the leadscrews keep their lengths; only the guide rods grow by DRIVE_DX.
# THE SLACK END IS CONTACT (user, 2026-11-12): to restring, the motor drives the keyhole plate
# all the way onto the endplate's plate, its hard stop
YK_CLR = 0.0
X_FT0 = ROD_PLATE[0] - YK_CLR - YK_H                # the nut flange's +X face at the slack end
X_YT0 = X_FT0 + YK_H                                # the yoke's +X face there
DRIVE_DX = -42.0 - X_FT0
# THE ROUND NUT (user, 2026-11-09): the common Tr8x2 brass flange nut, Ø22 x 3.5 flange with FOUR
# Ø3.5 holes on a Ø16 circle at 45 deg -- no flats needed here (a row's nuts are 28.5 apart, the
# next row's 28.1). Its holes do everything:
#   45 / 225 deg  two M3 x 12 SHCS from behind, through the collar's plate and the flange, into the
#                 yoke: they hold the yoke ON (the string pulls it +X, off the flange) and clamp the
#                 spring's collar, and a diagonal pair pulls on the axis.
#   135 deg       (was the guide rod's, through the nut; now empty -- see THE GUIDE ROD)
NUT_PCD = 16.0
HOLE_ANG = {"m3": (45.0, 225.0), "rod": 135.0, "web": (0.0, 180.0)}


# THE GUIDE ROD (user, 2026-11-11/12: one held at one end is no reliable rotation lock; hold it at
# BOTH ends). A 3/16 in 304 stainless rod (McMaster 89535K84, $7.45 a 6 ft length = 10 rods),
# outside the nut at GUIDE_R, GUIDE_ANG (the one direction free on all ten strings in the space
# scan; 30/210 sit on the plug's insert ears). One length for every string: its -X end in a blind
# seat in a boss on the ANCHOR PLUG (the plug's neck length varies, the seat's depth takes it),
# its +X end in the ROD PLATE. The NUT never touches it: the COLLAR (clamped to the nut by the
# M3s) carries a TAB with a RADIAL SLOT -- a close fit across (the rotation lock), GUIDE_FLOAT free
# along the radius, so the nut is never pushed off the screw's axis by a rod a little out of line.
GUIDE_D = 25.4 * 3 / 16                             # 4.76
# 15.35: 1.6 from its own string's spring-end sleeve; 325: as far as it goes from the NEIGHBOURS'
# collars and sleeves (user, 2026-11-12: rotate it, do not push it out; the scan put the worst
# neighbour gap at 4.5 there against 3.4 at 300, and the collar's tab 7 over the floor; 290 put
# the plug's boss into the next plug)
GUIDE_R, GUIDE_ANG = 15.35, 325.0                   # off the screw axis; deg from +Y toward +Z
GUIDE_ANG_1 = 325.0                                 # string 1: as the rest


def guide_ang(i: int) -> float:
    return GUIDE_ANG_1 if i == 0 else GUIDE_ANG
GUIDE_SEAT = GUIDE_D + 0.2                          # its two seats, a slip fit (it is trapped)
GUIDE_SLOT = GUIDE_D + 0.2                          # the slot across, the rotation lock
GUIDE_FLOAT = 1.0                                   # the slot's play along the radius, each way
GUIDE_WALL = 3 * 0.8                                # round the slot and the seat: three beads
TAB_L = 8.0                                         # the tab along x: the slot's bearing length


def at_ang(a: float, r: float = NUT_PCD / 2):
    """(dy, dz) of angle a (deg, from +Y toward +Z) at radius r."""
    return r * math.cos(math.radians(a)), r * math.sin(math.radians(a))


M3_HEAD = (5.5, 3.0)                                # SHCS head diameter, height
M3_L = 12.0
# RESTRINGING (user, 2026-11-09): a KEYHOLE in the yoke's roof. The ball end goes in through a
# hole KEY_DROP under the axis, then slides UP a slit only the string fits through, to sit on the
# axis behind the roof; the string's pull holds it there. The rod plate has a WINDOW in front of
# each keyhole the ball passes through (it was a Ø2 hole: the ball could never get past it).
KEY_D = D.STRING_NUT_D + 0.8                        # 4.8: the ball's way in
KEY_DROP = 5.0                                      # its centre under the axis: the slit's length
SLIT_W = 2.2                                        # string 10's 1.78 and room
WIN_HY = KEY_D / 2 + 1.4                            # 3.8: the plate window's half-width in Y
# ...and its reach under / over the axis: down a whole ball's width past the ball's hole, room to
# bring the ball in to the keyhole's bottom when restringing (user, 2026-11-12); that still
# leaves 1.9 over the next row's axle bore
WIN_Z = (-(KEY_DROP + KEY_D / 2 + KEY_D), 3.2)
# THE SPRING (2026-11-11): McMaster 9654K335 -- 0.75 in OD, 0.091 in tempered spring steel, 6.5 in,
# loop ends -- its LOOPS CUT OFF and the body cut to SPRING_COILS whole coils (one spring a piece,
# ~$2.71). Close-wound, 7.03 lbf (31.3 N) initial tension, ~1.72 N/mm with 35 working coils
# (McMaster's 1.70 at 35.5). A production spring is to be wound to a force-at-length drawing.
# Each end SCREWS
# ONTO A SEAT, its last coils wound over a plug of the spring's own inside diameter -- the way
# cut-to-length springs are meant to be ended -- so nothing is hooked off the axis.
#   NUT END: the COLLAR -- a plate clamped under the two M3 heads on the flange's back, two webs at
#            +-Y past the heads, and the seat on the far side of them, round the screw.
#   WALL END: the ANCHOR PLUG -- a seat on the plate's +X face, bolted through the plate to the
#            thrust HOUSING behind it (THE THRUST HOUSING).
#   NO SLEEVE (user, 2026-11-12): the plug and the collar never turn and the screw does, so a sleeve
#   round it rubbed wherever a bent screw whipped. The spring cannot reach the screw anyway: it is
#   always in tension (31 N before it stretches), so it stays straight post to post, Ø14.4 inside
#   round a Ø8 screw. Both parts are just SCREW_CLR round the screw.
SPRING_OD, SPRING_WIRE = 19.05, 2.31             # 0.75 / 0.091 in
SPRING_ID = SPRING_OD - 2 * SPRING_WIRE             # 14.43: the seats' diameter
SPRING_ACTIVE = 35                                  # working coils between the grips (whole turns)
SPRING_IT, SPRING_K = 31.3, 1.72                    # N initial tension, N/mm for SPRING_ACTIVE
# THE FORCE PER STRING (user, 2026-11-11: per-position lengths). Each string's spring is set at
# OPEN pitch to 95 % of its lightest string at -3 st (any C6/E9 gauge players use), less 1 N of
# drift over the +-3 st travel and less 5 N for the stock spring's tolerance (McMaster's
# +-0.3 lbf / +-10 % rate on a sibling: ~+-4..6 N); a strong spring then still stays under the
# string at -3 st, so the nut never crosses its backlash. Typical setups get 37..46 % help at
# their top raise. Index = string - 1. The ONLY per-string difference is the plug's neck: the
# same cut spring, stretched to its length (spring_len_open).
SPRING_F = (67.0, 68.0, 61.0, 66.0, 55.0, 61.0, 61.0, 63.0, 54.0, 53.0)
# HOW AN END HOLDS (user, 2026-11-09: "wrap the wire at the end around something"). Each seat is a
# THREADED POST: a helical groove the spring's last GRIP_TURNS coils are screwed into (the wire
# wraps the post, the load spread round the whole thread; its crests show between the coils).
# THE GRIP SLEEVE (user, 2026-11-12: no bent end): over each end's grip coils, a printed SLEEVE
# carrying the OTHER HALF of the thread (the post's groove holds the wire's inner half, the
# sleeve's its outer), screwed on over the coils and JAMMED against the stop flange by hand, a
# 2.5 key through its cross-hole for a tommy bar. Between its end face and the flange a ring of
# sawtooth DETENT TEETH: they click past as it goes on, and the steep side stands against it
# coming back off as the plastic relaxes -- steep enough to hold, not so steep a firm twist
# cannot undo it. So the spring is just cut to SPRING_COILS: no bending, no heating, no tang.
GRIP_TURNS, GRIP_PITCH = 4, 2.6                     # the end coils in the post's thread: the
                                                    # close-wound 2.31 opened a little as they go on
SPRING_COILS = SPRING_ACTIVE + 2 * GRIP_TURNS       # 43: the cut piece, ~100 free
SEAT_GRIP = GRIP_TURNS * GRIP_PITCH                 # 10.4 of post under them
SEAT_L = SEAT_GRIP                                   # no more: the open coils cross past it
SLEEVE_WALL = 2 * D.BEAD                            # the grip sleeve's wall past the spring
SLEEVE_OD = SPRING_OD + 0.2 + 2 * SLEEVE_WALL        # 22.45
SLEEVE_CLR = 0.1                                     # its bore off the post's crests
STOP_D, STOP_T = SLEEVE_OD, 2.0                      # the STOP FLANGE each spring end butts against:
                                                     # as wide as the sleeve, for the teeth's ring
DET_N, DET_H, DET_BACK = 24, 0.6, 60.0               # the detent: teeth, height, the steep side's
DET_R0 = SPRING_OD / 2 + 0.25                        # slope (deg); its ring from just past the wire
SLEEVE_KEY = 2.7                                     # the 2.5 key's cross-hole
R_COIL = (SPRING_OD - SPRING_WIRE) / 2              # 8.37: the wire's centre
SEAT_D = 2 * R_COIL                                 # the post: its thread's crests at the wire's centre
GROOVE_D = SPRING_WIRE + 0.1                         # under GRIP_PITCH: turns stay apart
PLUG_GAP = 4.5                                      # the plug's flange off the plate: with the
                                                    # flange the ears' 6.5 (an M4 insert's 5 and
                                                    # the bolt's tip past it)
SCREW_CLR = 10.0                                    # the plug's and collar's holes round the Ø8 screw
# THE ANCHOR PLATE (user, 2026-11-09): every spring's pull, about 73 N each and ~730 N in all,
# held ALL THE TIME. A printed wall fails under it (4.8 PETG-GF across 97 between the cheeks,
# holed to ~30 of section: ~77 MPa, ~7 mm of sag, then creep). It is LASER-CUT 304 STAINLESS,
# 4 mm, the nut plates' stock and order (JLCCNC sheet metal), BENT INTO A TRAY: its top, bottom
# and both ends folded ANCHOR_FL toward +X. The top and bottom folds make it a channel ~16 deep
# (I ~5800 mm^4 through the worst hole row: ~50 MPa at the middle of the rail-to-rail span,
# yield 205), and the end folds HANG ON PINS in the wall bars (user, 2026-11-12: no screws to
# reach it; a 2.5 key along Y had no way in past the springs, and none through the outer walls):
# two Ø5 hardened dowels a side, each in a hole drilled through the A-36 bar (no tap), pushed in
# from inside the empty body through a Ø5 hole in the rail's inner skin that grips it. Each end
# fold has an open-topped SLOT the pins drop into, so the tray goes in from above before anything
# else: the strings and springs pull it +X (~2 kN), the slot's -X edge onto the pins, steel on
# steel into the bars; the UI and the deck over it keep it from lifting when the strings are off.
ANCHOR_T = 4.0
ANCHOR = (-190.0 - DRIVE_DX - ANCHOR_T, -190.0 - DRIVE_DX)   # the plate's web, x
ANCHOR_Z = (None, -8.0)                             # its top at most (DECK_UNDER -3.2); _anchor_z
ANCHOR_FL = 16.0                                    # each fold's depth, toward +X
ANCHOR_CLR = 0.5                                    # off the body's walls and floor, and under the UI
M4_HEAD = (7.6, 2.2)                                # ISO 7380 button head (the housing's bolts)
# the pins: 0.5 kN each over ~4.5 of lever (bar face to the fold's middle): ~180 MPa bending in
# a Ø5 -- a hardened dowel (yield ~1 GPa), not 18-8. 12 long: 1 proud of the fold, 4.5 in the bar
ANCHOR_PIN_D, ANCHOR_PIN_L, ANCHOR_PIN_PROUD = 5.0, 12.0, 1.0
ANCHOR_SLOT_W = ANCHOR_PIN_D + 0.4                  # laser-cut: a drop-in fit across x
COLLAR_T = 3.0                                      # the collar's plate
# the collar's turn onto the M3 heads: only as far as takes the head (5.5) wholly over the plate
# past its way in (head + 0.6) and 0.3 more (user, 2026-11-12: just enough to get the screw in):
# each channel is then ~12 of arc, about two head diameters
BRIDGE_SAG = 1.0                                    # room under a printed bridge for its sag
BAYONET_TURN = math.degrees(2 * math.asin((M3_HEAD[0] / 2 + (M3_HEAD[0] + 0.6) / 2 + 0.3)
                                          / NUT_PCD))   # 44.8


def x_yt(t: float) -> float:
    return X_YT0 - t * T_TRAVEL


def x_ft(t: float) -> float:
    """Nut flange's +X face."""
    return x_yt(t) - YK_H


# THE SCREW'S CUT END (user, 2026-11-12): at the slack end it only JUST threads the nut, so the
# rest of the nut's length is travel before the tip can reach the ball. NUT_ENGAGE_SLACK: three
# turns of the Tr8x2 (the string is slack there; only the spring pulls, < 100 N on ~40 mm^2 of
# brass thread)
NUT_ENGAGE_SLACK = 3 * 2.0
SCREW_TIP = x_ft(0.0) - D.NUT_H + NUT_ENGAGE_SLACK


def x_collar(t: float):
    """The collar along x: plate (from, to), the heads' far face, the stop flange (from, to),
    the seat (from, to) -- the seat runs -X from the flange, the spring's end on the flange."""
    pb = x_ft(t) - D.NUT_FLANGE_T                   # the nut flange's back face
    heads = pb - COLLAR_T - M3_HEAD[1]
    f1 = heads - 0.5
    f0 = f1 - STOP_T
    return (pb - COLLAR_T, pb), heads, (f0, f1), (f0 - SEAT_L, f0)


def spring_len_open(i: int) -> float:
    """String i's spring, end coil centre to end coil centre, at open pitch: the grips plus the
    working coils close-wound and stretched to SPRING_F[i]."""
    return 2 * SEAT_GRIP + SPRING_ACTIVE * SPRING_WIRE + (SPRING_F[i] - SPRING_IT) / SPRING_K


def _plug_x0(i=None) -> float:
    """The plug's flange face off the plate: PLUG_GAP, and string i's neck longer by however much
    shorter its spring sits than the plain plug would leave it (None: the plain plug)."""
    f0 = ANCHOR[1] + PLUG_GAP
    if i is None:
        return f0
    free = x_collar(T_OPEN)[2][0] - SPRING_WIRE / 2 - (f0 + STOP_T + SPRING_WIRE / 2)
    d = free - spring_len_open(i)
    assert d >= 0, f"string {i + 1}: its spring wants {-d:.1f} more than the plain plug leaves"
    return f0 + d


def x_plug(i=None):
    """The anchor plug along x: the neck off the plate's +X face, the stop flange, the seat."""
    a1 = ANCHOR[1]
    f0 = _plug_x0(i)
    return (a1, f0), (f0, f0 + STOP_T), (f0 + STOP_T, f0 + STOP_T + SEAT_L)


def spring_span(t: float, i=None):
    """The spring, x from..to: its end coils' centres a wire's radius off each flange face."""
    return x_plug(i)[1][1] + SPRING_WIRE / 2, x_collar(t)[2][0] - SPRING_WIRE / 2


def spring_force(t: float, i: int) -> float:
    span = spring_span(t, i)
    return SPRING_IT + SPRING_K * (span[1] - span[0] - 2 * SEAT_GRIP - SPRING_ACTIVE * SPRING_WIRE)


# INSTALLING THE RODS (user, 2026-11-12: "we need a way to install the guide rods"). Each goes in
# LAST, from -X: through a hole in the anchor plate, the plug's boss (a through hole), the
# collar's slot, and home into its blind seat in the endplate, where three CRUSH RIBS grip its
# tip (ROD_GRIP: the only axial load is the tab's ~2 N of friction). So the endplate is on and
# screwed down first, and no rod has to find a hidden hole. Its -X end stands ROD_PROUD out of the
# plate's -X face, clear of the housing (r 9.6) and its ears (155/275), for pliers to pull it.
ROD_PROUD = 2.0
ROD_END = ANCHOR[0] - ROD_PROUD
# its +X end, deep in the endplate: the seat runs on past the plate until 1.0 of plastic is left
# before the NEXT ROW's axle bore (rows 0 and 1 have one just under their rods): ~11 of grip
ROD_TIP = X_BEND - (D.BRIDGE_AXLE_D + 0.2) / 2 - 1.0 - 0.3
ROD_L = round(ROD_TIP - ROD_END, 1)                 # every string the same
ROD_GRIP, ROD_RIB = 4.0, 0.15                       # the ribs: length at the seat's bottom, bite

# ── motors and stations ─────────────────────────────────────────────────────────────────────
M_HALF = D.MOTOR_SQ / 2                             # 21.15
M_BACK = 60.7                                       # pulley plane -> the driver's back
M_FACE = 7.5                                        # pulley plane -> the faceplate
PLUG = (21.15, 29.9, 6.2, 44.5, 38.5)               # coil plug + leads: off the axis from..to,
                                                    # half-width, and its x range (back of ref)
# THE COUPLER IS ONE PRINTED PIECE (user, 2026-11-09), x from the pulley plane:
#   MOTOR END  the motor pulley's own open D bore (components.MOTOR_BORE_CLR) over the shaft's
#              flat, -4 .. +4: its -X face on the D key's stop, the shaft cut flush at +4 as
#              for the pulley (MOTOR_SHAFT_CUT_L). A friction fit: it TURNS the screw, nothing
#              more -- the string pulls the screw +X, away from the motor, so no thrust reaches
#              the shaft.
#   SCREW END  a plain Ø8.4 socket the screw slides into (no thread), 0.5 past the shaft's end,
#              and ONE M3 x 12 SHCS sideways through the coupler and a Ø3.2 hole DRILLED through
#              the screw, self-tapping the far wall (as the yoke's M3s): a pin for the torque.
#   THRUST     none: the coupler only TURNS the screw (~0.09 N m). The thrust bearings are on the
#              anchor plate (THE THRUST HOUSING below), so the motor carries no axial load.
from .motor_coupler import CPL_D, CPL_X, CPL_GRIP, SCREW_X0   # src.motor_coupler
M3_PILOT = 2.5

# THE THRUST HOUSING (user, 2026-11-09: "put the thrust bearings on the anchor ... it would
# ideally hit that metal plate"). Each screw's two 688s sit in a printed HOUSING on the anchor
# plate's -X face, and the anchor plug on its +X face; two M4 x 20 button heads through the
# housing's ears and the plate into heat-set inserts in the plug's ears clamp the three together
# (the plug's quarter-turn lugs are gone). The screw is held in the pair by two printed collars
# threaded on its Tr8: COLLAR B (+X, in the plate's hole) run down first, COLLAR A (-X) run up
# against the pair to take the play out, then pinched by an M3 x 12.
#   strings on:  the screw pulls +X: collar A -> both inner races -> outer races -> THE PLATE's
#                face round its hole. Metal, straight. The plug's spring pull reaches the plate
#                through the bolts and the housing. The plate carries the string tension.
#   strings off: the spring pulls the plug +X and pushes the screw -X (collar B -> the pair ->
#                the housing's -X shoulder): the two meet in the bolts, the plate sees nothing.
# Either way the motor only turns the screw. Ears at 155 / 275 deg (2026-11-12, with the rod at
# 325 and the tangs gone): a 2-D scan of every string's flange, ears and rod boss puts the worst
# gap at 2.1 there; 35/215 put the rod's boss 3 mm into the next string's ear.
HOUSE_D = D.BRG688_OD + 3.2                         # 19.2: the pocket's 1.6 wall
HOUSE_POCKET = 2 * D.BRG688_W                       # the pair, pressed in from +X
HOUSE_SHOULDER = 2.5
RACE_OUT_D = 13.6                                   # shoulder holes: on the outer race only
RACE_IN_D = 10.4                                    # collar bosses: on the inner race only
EAR_ANG, EAR_R = (155.0, 275.0), 12.0
PLATE_HOLE_D = 14.4                                 # the plate's hole: collar B inside, the outer
                                                    # race's face (to Ø16) bears on the rim
HB_L = 20.0                                         # the M4 button heads: housing, plate, insert
COLLAR_A = (20.0, 8.0)                              # Ø, body length
COLLAR_B_D = 13.0
NEMA17_HOLES = 31.0                                 # the faceplate's M3 square
SLOT_STATIONS = (0,)                                # the +X-most motors: oversized (slotted) holes


def x_house():
    """The housing, x from..to: shoulder at -X, the pocket to the plate's -X face."""
    a0 = ANCHOR[0]
    return a0 - HOUSE_POCKET - HOUSE_SHOULDER, a0


def x_collar_a():
    """Collar A: (body from, body to), and its boss's end (the -X bearing's face)."""
    h0 = x_house()[0]
    b1 = ANCHOR[0] - HOUSE_POCKET
    body1 = h0 - 0.5
    return (body1 - COLLAR_A[1], body1), b1
PLATE_T = 4.0
STATION_GAP = 1.3
STATION_P = M_BACK + CPL_X[1] + STATION_GAP         # 77.0: no bearing block any more
X_REF0 = x_collar_a()[0][0] - 1.0 - CPL_X[1]        # the nearest station: past collar A

# station of each string (nearest 0): rows 0 and 2 share; 57 apart on a row share. The ORDER is
# the one (of the 24) where every motor's coil plug finds a side no passing screw, station-mate,
# rail or deck takes (searched; the middle row's lone string 5 has to be the farthest).
STATION = {1: 0, 7: 0, 0: 1, 6: 1, 2: 1, 8: 1, 3: 2, 9: 2, 5: 2, 4: 3}


def x_ref(i: int) -> float:
    return X_REF0 - STATION[i] * STATION_P


# ── the rails ───────────────────────────────────────────────────────────────────────────────
Y_LO, Y_HI = -116.35, 54.75                         # today's rails' inner faces
KEYHEAD_X = D.KEYHEAD_INBOARD_X                     # -607.8
DECK_UNDER = -3.2
WALL_CLR = 0.4


THETA = 0.0                                         # no yaw: everything on its string's axis


def yaw(wp: cq.Workplane, i: int) -> cq.Workplane:
    """Swing a string's drive part by THETA about its exit point (0: as drawn)."""
    if THETA == 0.0:
        return wp
    return wp.rotate((X_BEND, y_of(i), 0), (X_BEND, y_of(i), 1), math.degrees(THETA))


def yaw_pt(p, i: int):
    x, y, z = p
    dx, dy = x - X_BEND, y - y_of(i)
    c, s = math.cos(THETA), math.sin(THETA)
    return (X_BEND + dx * c - dy * s, y_of(i) + dx * s + dy * c, z)


# ── plug directions: searched so no passing screw, no station-mate, no deck or floor meets it ─
DIRS = {0: (0.0, 1.0), 270: (1.0, 0.0), 90: (-1.0, 0.0), 180: (0.0, -1.0)}   # phi -> (dy, dz)


def _plug_box(i: int, phi: int):
    dy, dz = DIRS[phi]
    a, b, hw = PLUG[0], PLUG[1], PLUG[2]
    y, z = y_of(i), za(i)
    if dy:
        ys = sorted((y + dy * a, y + dy * b))
        return (ys[0], ys[1], z - hw, z + hw)
    zs = sorted((z + dz * a, z + dz * b))
    return (y - hw, y + hw, zs[0], zs[1])


def _hits(b, c):
    return b[0] < c[1] and c[0] < b[1] and b[2] < c[3] and c[2] < b[3]


def _body(j: int):
    return (y_of(j) - M_HALF, y_of(j) + M_HALF, za(j) - M_HALF, za(j) + M_HALF)


def _plug_dirs() -> dict:
    floor = min(za(i) for i in range(N)) - M_HALF
    out = {}
    for i in sorted(range(N), key=lambda k: STATION[k]):
        # a +Y plug past today's rail would widen it further: try it last there
        order = (90, 0, 180, 270) if y_of(i) + PLUG[1] > Y_HI else (90, 270, 0, 180)
        for phi in order:
            b = _plug_box(i, phi)
            if b[3] > DECK_UNDER - 0.5 or b[2] < floor:
                continue
            if b[0] < Y_LO + WALL_CLR:               # the -Y rail stays; the +Y one moves out
                continue
            bad = False
            for j in range(N):
                if j == i:
                    continue
                if STATION[j] > STATION[i]:           # j's screw passes i's motor
                    r = D.SCREW_OD / 2 + 0.3
                    if _hits(b, (y_of(j) - r, y_of(j) + r, za(j) - r, za(j) + r)):
                        bad = True
                elif STATION[j] == STATION[i]:
                    if _hits(b, _body(j)) or (j in out and _hits(b, _plug_box(j, out[j]))):
                        bad = True
            if not bad:
                out[i] = phi
                break
        else:
            raise ValueError(f"no plug direction for string {i + 1}")
    return out


PLUG_DIR = _plug_dirs()


def _rail_hi() -> float:
    """Where the +Y rail's inner face has to be: past every motor and plug, and never in."""
    far = max(max(y_of(i) + M_HALF, _plug_box(i, PLUG_DIR[i])[1]) for i in range(N))
    return max(Y_HI, far + WALL_CLR)


RAIL_HI = _rail_hi()


# ── report ──────────────────────────────────────────────────────────────────────────────────
def report() -> str:
    out = [f"rows z (axis): " + "  ".join(f"{k}: {z_level(k):.1f}" for k in range(LEVELS)) +
           f"   DZ {DZ}",
           f"+Y rail inner face {RAIL_HI:.2f} (today {Y_HI}): {RAIL_HI - Y_HI:+.2f} wider, all on axis",
           f"stations x (pulley plane): " + "  ".join(f"{X_REF0 - s * STATION_P:.1f}"
                                                      for s in range(4)) + f"  pitch {STATION_P}",
           "string row station  motor (x, y, z)            plug  screw length  spring at slack/full"
           "   N at slack/open/full"]
    for i in range(N):
        m = yaw_pt((x_ref(i), y_of(i), za(i)), i)
        sl = SCREW_TIP - (x_ref(i) + 11.0)
        s0 = spring_span(0, i)[1] - spring_span(0, i)[0]
        s1 = spring_span(1, i)[1] - spring_span(1, i)[0]
        dirn = {0: "+Z", 90: "-Y", 180: "-Z", 270: "+Y"}[PLUG_DIR[i]]
        out.append(f"  {i + 1:2d}   {level(i)}     {STATION[i]}     ({m[0]:7.1f}, {m[1]:6.1f}, {m[2]:6.1f})"
                   f"   {dirn}   {sl:6.1f}        {s0:5.1f} / {s1:5.1f}"
                   f"   {spring_force(0, i):4.1f} / {spring_force(T_OPEN, i):4.1f} / {spring_force(1, i):4.1f}")
    low = min(za(i) for i in range(N)) - M_HALF
    far = min(x_ref(i) for i in range(N)) - M_BACK
    out.append(f"deepest: the lowest motor's bottom z {low:.1f}  (today's bottom -81.8)")
    out.append(f"farthest motor back x {far:.1f}  (keyhead {KEYHEAD_X})")
    return "\n".join(out)


# ── geometry ────────────────────────────────────────────────────────────────────────────────
def _seg(a, b, d):
    va, vb = cq.Vector(*a), cq.Vector(*b)
    v = vb - va
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(d / 2, v.Length, va, v.normalized()))


def _tube_x(od, idd, x0, x1, y, z):
    return cyl_x(od, x1 - x0, x0, y=y, z=z).cut(cyl_x(idd, x1 - x0 + 2, x0 - 1, y=y, z=z))


def _yoke(i: int, t: float) -> cq.Workplane:
    y, z = y_of(i), za(i)
    ft, yt = x_ft(t), x_yt(t)
    out = cyl_x(YK_D, YK_H - YK_ROOF, ft, y=y, z=z)                                 # the spacer
    out = out.cut(cyl_x(D.SCREW_OD + 0.8, yt - YK_ROOF - ft + 1, ft - 1, y=y, z=z))   # tip + ball
    out = out.cut(cyl_x(D.NUT_LIP_D + 0.4, D.NUT_LIP_L + 1.3, ft - 1, y=y, z=z))      # lip register
    ry, rz = rod_yz(i)
    out = out.cut(cyl_x(GUIDE_D + 2.0, YK_H + 2, ft - 1, y=ry, z=rz))                 # rod: clear
    for a in HOLE_ANG["m3"]:                                                          # the M3s bite
        dy, dz = at_ang(a)
        out = out.cut(cyl_x(3.4, YK_H + 2, ft - 1, y=y + dy, z=z + dz))           # clear: they
                                                                                  # tap the plate
    # behind the plate, a pocket the ball slides up in (its 3 along the axis, Ø4 across)
    rx0 = yt - YK_ROOF
    pk = D.STRING_NUT_L + 0.6
    # ...its bottom ROUND, the plate's ball hole (user, 2026-11-12: a square pocket left two
    # ledges of steel under the hole a ball could catch on when the string is pulled down)
    out = out.cut(box_at(pk, KEY_D, KEY_DROP, x=rx0 - pk / 2, y=y, z=z - KEY_DROP / 2))
    out = out.cut(cyl_x(KEY_D, pk, rx0 - pk, y=y, z=z - KEY_DROP))
    return out




def keyhole_plate() -> cq.Workplane:
    """The keyhole plate in its own frame (+X face at x = 0, axis on y = z = 0), as cut from the
    4 mm sheet: a Ø YK_D disc, the ball's hole KEY_DROP under the axis, the slit up to a round
    end on the axis, and the yoke's two M3 tapped holes (drawn as the Ø2.5 tap drill)."""
    w = cyl_x(YK_D, YK_ROOF, -YK_ROOF, y=0, z=0)
    w = w.cut(cyl_x(KEY_D, YK_ROOF + 2, -YK_ROOF - 1, y=0, z=-KEY_DROP))
    w = w.cut(box_at(YK_ROOF + 2, SLIT_W, KEY_DROP, x=-YK_ROOF / 2, y=0, z=-KEY_DROP / 2))
    w = w.cut(cyl_x(SLIT_W, YK_ROOF + 2, -YK_ROOF - 1, y=0, z=0))
    for a in HOLE_ANG["m3"]:
        dy, dz = at_ang(a)
        w = w.cut(cyl_x(2.5, YK_ROOF + 2, -YK_ROOF - 1, y=dy, z=dz))
    return w


def rod_yz(i: int):
    dy, dz = at_ang(guide_ang(i), GUIDE_R)
    return y_of(i) + dy, za(i) + dz


def _radial_box(i: int, x0: float, x1: float, r0: float, r1: float, w: float) -> cq.Workplane:
    """A box x0..x1, from radius r0 to r1 off string i's axis toward its guide rod, w wide."""
    return _radial_box_at(i, x0, x1, r0, r1, w, guide_ang(i))


def _arc_x(i: int, x0: float, x1: float, r: float, w: float, a0: float, a1: float,
           open_out: bool = False) -> cq.Workplane:
    """A slot x0..x1 along the arc of radius r round string i's axis, from angle a0 to a1, w wide
    with round ends; open_out runs it on out past the outside (a pocket open to the side)."""
    ro = (STOP_D / 2 + 2.0) if open_out else r + w / 2
    ring = cyl_x(2 * ro, x1 - x0, x0, y=y_of(i), z=za(i)).cut(
        cyl_x(2 * (r - w / 2), x1 - x0 + 2, x0 - 1, y=y_of(i), z=za(i)))
    R = 2 * ro + 5                                   # the wedge a0..a1, as a fan of triangles
    n = max(2, int(abs(a1 - a0) / 10) + 1)
    pts = [(0.0, 0.0)] + [at_ang(a0 + (a1 - a0) * k / n, R) for k in range(n + 1)]
    wedge = (cq.Workplane("YZ", origin=(x0 - 1, y_of(i), za(i))).polyline(pts).close()
             .extrude(x1 - x0 + 2))
    out = ring.intersect(wedge)
    for a in (a0, a1):                                # the round ends
        dy, dz = at_ang(a, r)
        out = out.union(cyl_x(w, x1 - x0, x0, y=y_of(i) + dy, z=za(i) + dz))
        if open_out:
            out = out.union(_radial_box_at(i, x0, x1, r, ro, w, a))
    return out


def _radial_box_at(i: int, x0: float, x1: float, r0: float, r1: float, w: float,
                   a: float) -> cq.Workplane:
    """A box x0..x1, from radius r0 to r1 off string i's axis toward angle a, w wide."""
    b = box_at(x1 - x0, w, r1 - r0, x=(x0 + x1) / 2, y=0, z=(r0 + r1) / 2)        # along +Z ...
    return b.rotate((0, 0, 0), (1, 0, 0), a - 90).translate((0, y_of(i), za(i)))


def _collar(i: int, t: float) -> cq.Workplane:
    y, z = y_of(i), za(i)
    (p0, p1), heads, (f0, f1), (s0, s1) = x_collar(t)
    out = cyl_x(D.NUT_FLANGE_L, p1 - p0, p0, y=y, z=z)                             # the plate
    # SOLID from the plate back to the flange (user, 2026-11-12: no air gap), the flange's own
    # diameter: only a POCKET for each M3 head (0.3 a side round it) and the nut boss's bore below
    out = out.union(cyl_x(STOP_D, p0 - f0 + 0.01, f0, y=y, z=z))                   # + stop flange
    hw = M3_HEAD[0] / 2 + 0.3                        # the head pockets: below, with the bayonet
    x0, x1 = spring_span(t, i)                                                      # the post:
    out = out.union(_post(i, x0, x1 - x0 - SEAT_GRIP, D.NUT_BOSS_D + 0.4))          # threaded
    out = out.cut(cyl_x(D.NUT_BOSS_D + 0.4, 60, s0 - 1, y=y, z=z))                  # boss, screw
    out = out.union(_tube_x(13.0, SCREW_CLR, s0, s0 + 3.0, y, z))                   # post's floor
    x0, x1 = spring_span(t, i)                       # the detent's teeth on the flange
    out = out.union(_in_spring(_teeth(x1 - x0 + SPRING_WIRE / 2, -1, 1), i, x0))
    # A BAYONET ON THE M3 HEADS (user, 2026-11-12: a 30 mm screw cannot come in along X past the
    # post and the flange; put the screws in the nut first, then the collar onto them). The M3s go
    # through the nut flange and yoke into the keyhole plate first, heads left COLLAR_T proud.
    # The collar slides along the leadscrew onto the nut, the heads through two head-sized holes
    # in its plate BAYONET_TURN past their places into the pockets behind, then TURNS back: the
    # plate's arc slots carry it under the heads. The 2.5 key reaches each head from -X down a
    # Ø3.4 hole through the post, its floor and the flange -- tighten both before the spring goes
    # on (its wire crosses that line). Nothing on the nut is cut.
    for a in HOLE_ANG["m3"]:
        dy, dz = at_ang(a)
        out = out.cut(cyl_x(3.4, p1 - s0 + 2, s0 - 1, y=y + dy, z=z + dz))
        a0 = a + BAYONET_TURN                       # (+: the way in clear of the rod tab at 325)
        out = out.cut(_arc_x(i, p0 - 0.01, p1 + 0.01, NUT_PCD / 2, 3.4, a0, a))      # the slot
        dy, dz = at_ang(a0)                                                        # the way in
        out = out.cut(cyl_x(2 * hw, p1 - p0 + 0.02, p0 - 0.01, y=y + dy, z=z + dz))
        out = out.cut(_arc_x(i, f1, p0 + 0.01, NUT_PCD / 2, 2 * hw, a0, a, open_out=True))
        # PRINTED +X -> -X, the plate on the bed (user, 2026-11-12): nothing of the flange or its
        # teeth over the channels, so they print open to the sky. The post's wall (r 5.3..8.37)
        # still runs over their inner half: a ~12 bridge along each arc, anchored both ends on
        # the post's unbroken ring. A bridge comes out uneven (user, 2026-11-12: do not rely on
        # its floor), and nothing bears on it -- the heads clamp the plate -- so the channel
        # runs BRIDGE_SAG further in under it: the head turns past whatever sags.
        out = out.cut(_arc_x(i, f1 - BRIDGE_SAG, f1 + 0.02, NUT_PCD / 2, 2 * hw, a0, a, open_out=True))
        out = out.cut(_arc_x(i, f0, f1 + 0.02, NUT_PCD / 2, 2 * hw, a0, a, open_out=True)
                      .cut(cyl_x(SEAT_D + 0.01, f1 - f0 + 1, f0 - 0.5, y=y, z=z)))
        out = out.cut(_arc_x(i, f0 - DET_H - 0.01, f0 + 0.01, NUT_PCD / 2, 2 * hw, a0, a,
                             open_out=True).cut(cyl_x(2 * DET_R0 - 0.2, DET_H + 1, f0 - DET_H - 0.5,
                                                      y=y, z=z)))
    # the TAB: from the plate out past the rod, TAB_L along x from the plate's +X face back,
    # and its RADIAL SLOT. Its outer end is ROUND, concentric with the slot's (user, 2026-11-12:
    # the square corners came close to the next string's spring): GUIDE_WALL all round the slot
    w = GUIDE_SLOT + 2 * GUIDE_WALL
    lo, hi = GUIDE_R - GUIDE_FLOAT, GUIDE_R + GUIDE_FLOAT
    out = out.union(_radial_box(i, p1 - TAB_L, p1, D.NUT_FLANGE_L / 2 - 2.0, hi, w))
    dy, dz = at_ang(guide_ang(i), hi)
    out = out.union(cyl_x(w, TAB_L, p1 - TAB_L, y=y + dy, z=z + dz))
    out = out.cut(_radial_box(i, p1 - TAB_L - 1, p1 + 1, lo, hi, GUIDE_SLOT))
    for r in (lo, hi):                                                              # round ends
        dy, dz = at_ang(guide_ang(i), r)
        out = out.cut(cyl_x(GUIDE_SLOT, TAB_L + 2, p1 - TAB_L - 1, y=y + dy, z=z + dz))
    return out


def _m3s(i: int, t: float) -> cq.Workplane:
    y, z = y_of(i), za(i)
    (p0, _), heads, _, _ = x_collar(t)
    out = None
    for a in HOLE_ANG["m3"]:
        dy, dz = at_ang(a)
        sc = _cap("m3", KEY_M3_L, (heads, y + dy, z + dz), (1, 0, 0))
        out = sc if out is None else out.union(sc)
    return out


def _cap(kind: str, length: float, top, shank_dir) -> cq.Workplane:
    from .motor_coupler import cap_screw
    return cap_screw(kind, length, top, shank_dir)


COILS = True                                        # False: the spring as its tube (the gate)


def _helix(z0: float, pitch: float, h: float, d: float) -> cq.Workplane:
    """A wire of diameter d round R_COIL from local z0 for h, starting at angle 0 (local +x), in
    the SPRING'S FRAME: local z along the screw (-> world +X), placed by _in_spring."""
    hx = cq.Wire.makeHelix(pitch=pitch, height=h, radius=R_COIL)
    return (cq.Workplane("XZ").center(R_COIL, 0).circle(d / 2)
            .sweep(cq.Workplane("XY").add(hx), isFrenet=True).translate((0, 0, z0)))


def _in_spring(wp: cq.Workplane, i: int, x0: float) -> cq.Workplane:
    """Local spring frame -> the string's (local +x, angle 0, lands on world -Z)."""
    return wp.rotate((0, 0, 0), (0, 1, 0), 90).translate((x0, y_of(i), za(i)))


def _screw(i: int, x0: float, x1: float) -> cq.Workplane:
    """The leadscrew from x0 to x1 along +X: the instrument's own threaded Tr8x2 rod
    (components.screw, cached per length). Its crests are the plain cylinder's surface, so the
    gate (COILS False) checks that cylinder instead of cutting the helix."""
    y, z = y_of(i), za(i)
    if not COILS:
        return cyl_x(D.SCREW_OD, x1 - x0, x0, y=y, z=z)
    from . import components as C
    # OCCT's helix cut holds at some lengths and not others (components.screw checks it and
    # raises): cut the rod a little shorter at the free tip until it holds -- whole mm first,
    # it is sawn from stock anyway, and SCREW_END_GAP keeps the tip clear by more than this.
    L = math.floor(x1 - x0)
    for dl in (0.0, 0.5, 1.0, 1.5, 2.0):
        try:
            rod = C.screw(L - dl, whole_mesh=True)
            break
        except Exception:                           # the check's AssertionError, or the
            continue                                # groove's sweep failing outright (StdFail)
    else:
        raise AssertionError(f"no leadscrew of {L} to {L - 2.0} mm cut cleanly")
    return rod.rotate((0, 0, 0), (0, 1, 0), 90).translate((x0, y, z))


def _spring(i: int, t: float) -> cq.Workplane:
    x0, x1 = spring_span(t, i)
    if not COILS:
        return _tube_x(SPRING_OD, SPRING_ID, x0, x1, y_of(i), za(i))
    L = x1 - x0
    act = L - 2 * SEAT_GRIP
    k = SPRING_ACTIVE                               # whole turns: every piece starts at angle 0
    assert act > k * SPRING_WIRE, "the working coils solid" 
    pieces = [_helix(0.0, GRIP_PITCH, SEAT_GRIP, SPRING_WIRE),
              _helix(SEAT_GRIP, act / k, act, SPRING_WIRE),
              _helix(SEAT_GRIP + act, GRIP_PITCH, SEAT_GRIP, SPRING_WIRE)]
    # ONE compound: the view and the export take a part's first solid only
    one = cq.Workplane("XY").add(cq.Compound.makeCompound([v for p_ in pieces for v in p_.vals()]))
    return _in_spring(one, i, x0)


def _post(i: int, x0: float, z0: float, bore: float) -> cq.Workplane:
    """A threaded post SEAT_L long from local z0 (spring frame at x0), its groove matching the
    grip coils (angle 0 at z0, whole turns), bored for what passes through it."""
    # the post reaches its flange at one end, and stops half a pitch short of the open coils at
    # the other (where the pitch changes, the next turn would ride over its last crest)
    lo = -SPRING_WIRE / 2 if z0 <= 0 else GRIP_PITCH / 2
    hi = SPRING_WIRE / 2 if z0 > 0 else -GRIP_PITCH / 2
    post = cq.Workplane("XY").add(cq.Solid.makeCylinder(SEAT_D / 2, SEAT_L - lo + hi,
                                                        cq.Vector(0, 0, z0 + lo)))
    post = post.cut(_helix(z0, GRIP_PITCH, SEAT_L, GROOVE_D))
    post = post.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(bore / 2, SEAT_L - lo + hi + 2,
                                                                 cq.Vector(0, 0, z0 + lo - 1))))
    return _in_spring(post, i, x0)


def _ring(r0: float, r1: float, z0: float, z1: float) -> cq.Workplane:
    """An annulus r0..r1 about local z, z0..z1 (either order), in the spring's frame."""
    lo, hi = min(z0, z1), max(z0, z1)
    o = cq.Solid.makeCylinder(r1, hi - lo, cq.Vector(0, 0, lo))
    return cq.Workplane("XY").add(o.cut(cq.Solid.makeCylinder(r0, hi - lo, cq.Vector(0, 0, lo))))


def _teeth(zf: float, s: int, tighten: int) -> cq.Workplane:
    """The flange's DETENT TEETH in the spring's frame: on the face at local zf, standing DET_H
    toward s (+1/-1 along local z), on the ring DET_R0..SLEEVE_OD/2. Going round in the sleeve's
    TIGHTENING sense (tighten: +1 = +angle about local z) each tooth rises gently and drops
    steeply, so the sleeve rides up and over as it goes on and meets the steep side coming off."""
    r0, r1 = DET_R0, SLEEVE_OD / 2
    pitch = 2 * math.pi * (r0 + r1) / 2 / DET_N
    steep = DET_H / math.tan(math.radians(DET_BACK))
    up = (0.0, pitch - steep) if tighten > 0 else (0.0, steep)       # where the crest is
    pts = [(0.0, zf), (up[1], zf + s * DET_H), (pitch, zf)]
    one = (cq.Workplane("YZ", origin=(r0 - 0.5, 0, 0)).polyline(pts).close()
           .extrude(r1 - r0 + 1.0))
    out = None
    for k in range(DET_N):
        t = one.rotate((0, 0, 0), (0, 0, 1), k * 360.0 / DET_N)
        out = t if out is None else out.union(t)
    return out.intersect(_ring(r0, r1, zf, zf + s * DET_H))


def _sleeve_local(zf: float, s: int, z_far: float, z0: float, tighten: int) -> cq.Workplane:
    """The grip sleeve in the spring's frame: from the flange face zf (its end on the teeth)
    toward s to z_far, bore SLEEVE_CLR off the post, the grip coils' groove (helix from z0, as
    the post's), the teeth's complement on its end, and the key's cross-hole."""
    ri, ro = R_COIL + SLEEVE_CLR, SLEEVE_OD / 2
    body = _ring(ri, ro, zf + s * DET_H, z_far)
    band = _ring(DET_R0, ro, zf, zf + s * DET_H).cut(_teeth(zf, s, tighten))
    body = body.union(band)
    body = body.cut(_helix(z0, GRIP_PITCH, SEAT_L, GROOVE_D))
    zk = (zf + z_far) / 2                                    # the key's cross-hole, through
    key = cq.Workplane("XY").add(cq.Solid.makeCylinder(SLEEVE_KEY / 2, 2 * ro + 2,
                                                       cq.Vector(0, -ro - 1, zk), cq.Vector(0, 1, 0)))
    return body.cut(key)


def _sleeve_plug(i: int) -> cq.Workplane:
    """The plug end's sleeve: flange face at local -wire/2, over the post to its end. Tightening
    runs it toward -z: with a right-hand helix that is -angle."""
    zf = -SPRING_WIRE / 2
    return _in_spring(_sleeve_local(zf, 1, SEAT_L - GRIP_PITCH / 2, 0.0, -1), i,
                      spring_span(0.0, i)[0])


def _sleeve_collar(i: int, t: float) -> cq.Workplane:
    """The collar end's: flange face at local L + wire/2, back over the post. It tightens +z."""
    x0, x1 = spring_span(t, i)
    L = x1 - x0
    zf = L + SPRING_WIRE / 2
    return _in_spring(_sleeve_local(zf, -1, L - SEAT_L + GRIP_PITCH / 2, L - SEAT_GRIP, 1), i, x0)


def _anchor_plug(i: int) -> cq.Workplane:
    y, z = y_of(i), za(i)
    (a0, a1), (f0, f1), (s0, s1) = x_plug(i)
    out = cyl_x(SPRING_ID, f0 - a0, a0, y=y, z=z)                                   # neck
    out = out.union(cyl_x(STOP_D, f1 - f0, f0, y=y, z=z))                           # stop flange
    out = out.union(_ears(i, a0, f1, 4.5))                                          # the inserts'
    out = out.cut(cyl_x(SCREW_CLR, s1 - a0 + 2, a0 - 1, y=y, z=z))                 # the screw's way
    for a in EAR_ANG:
        dy, dz = at_ang(a, EAR_R)
        out = out.cut(cyl_x(6.1, 5.0, a0 - 1, y=y + dy, z=z + dz).translate((1, 0, 0)))  # insert
        out = out.cut(cyl_x(4.4, f1 - a0 + 2, a0 - 1, y=y + dy, z=z + dz))              # tip's way
    out = out.union(_post(i, spring_span(0.0, i)[0], 0.0, SCREW_CLR))               # threaded post
    # the guide rod's -X SEAT: a boss at GUIDE_R on the plate, its web back to the neck, and a
    # hole right through it: the rod slides in from -X through the plate (ROD_END)
    dy, dz = at_ang(guide_ang(i), GUIDE_R)
    out = out.union(cyl_x(GUIDE_SEAT + 2 * GUIDE_WALL, f1 - a0, a0, y=y + dy, z=z + dz))
    out = out.union(_radial_box(i, a0, f1, SPRING_ID / 2 - 1.0, GUIDE_R, GUIDE_SEAT + 2 * GUIDE_WALL))
    out = out.cut(cyl_x(GUIDE_SEAT, f1 - a0 + 2, a0 - 1, y=y + dy, z=z + dz))
    return out.union(_in_spring(_teeth(-SPRING_WIRE / 2, 1, -1), i, spring_span(0.0, i)[0]))


def _ears(i: int, x0: float, x1: float, hw: float) -> cq.Workplane:
    """The two ears at EAR_ANG: a web from the axis out to a boss round EAR_R, x0..x1."""
    y, z = y_of(i), za(i)
    out = None
    for a in EAR_ANG:
        e = box_at(x1 - x0, 2 * hw, EAR_R, x=(x0 + x1) / 2, y=0, z=EAR_R / 2)   # along +Z ...
        e = e.union(cyl_x(2 * hw, x1 - x0, x0, y=0, z=EAR_R))
        e = e.rotate((0, 0, 0), (1, 0, 0), a - 90).translate((0, y, z))        # ... turned to a
        out = e if out is None else out.union(e)
    return out


def _housing(i: int) -> cq.Workplane:
    y, z = y_of(i), za(i)
    h0, h1 = x_house()
    out = cyl_x(HOUSE_D, h1 - h0, h0, y=y, z=z).union(_ears(i, h0, h1, 4.5))
    out = out.cut(cyl_x(D.BRG688_OD, HOUSE_POCKET + 1, h1 - HOUSE_POCKET, y=y, z=z))   # open +X
    out = out.cut(cyl_x(RACE_OUT_D, 10, h0 - 1, y=y, z=z))
    for a in EAR_ANG:
        dy, dz = at_ang(a, EAR_R)
        out = out.cut(cyl_x(4.4, h1 - h0 + 2, h0 - 1, y=y + dy, z=z + dz))
        out = out.cut(cyl_x(M4_HEAD[0] + 0.6, M4_HEAD[1] + 0.3 + 1, h0 - 1, y=y + dy, z=z + dz))
    return out


def _housing_bolts(i: int) -> cq.Workplane:
    """Two M4 x 20 button heads, heads sunk in the housing's -X face, into the plug's inserts."""
    y, z = y_of(i), za(i)
    hu = x_house()[0] + M4_HEAD[1] + 0.3            # the heads' underside
    out = None
    for a in EAR_ANG:
        dy, dz = at_ang(a, EAR_R)
        b = _cap("m4", HB_L, (hu - M4_HEAD[1], y + dy, z + dz), (1, 0, 0))
        out = b if out is None else out.union(b)
    return out


def _inserts(i: int) -> cq.Workplane:
    from cadkit.fasteners import M4, seated_insert
    y, z = y_of(i), za(i)
    out = None
    for a in EAR_ANG:
        dy, dz = at_ang(a, EAR_R)
        b = seated_insert(M4, (ANCHOR[1], y + dy, z + dz), (1, 0, 0))   # cadkit's dummy
        out = b if out is None else out.union(b)
    return out


def _collar_a(i: int) -> cq.Workplane:
    """Threaded on the Tr8, its boss through the housing's shoulder onto the -X inner race;
    split on +Y and pinched across the split by an M3 x 12 (a 2.5 key from +Z)."""
    y, z = y_of(i), za(i)
    (c0, c1), b1 = x_collar_a()
    out = cyl_x(COLLAR_A[0], c1 - c0, c0, y=y, z=z).union(cyl_x(RACE_IN_D, b1 - c1, c1, y=y, z=z))
    out = out.cut(cyl_x(D.SCREW_OD, b1 - c0 + 2, c0 - 1, y=y, z=z))      # the thread (drawn Ø8)
    out = out.cut(box_at(c1 - c0 + 2, COLLAR_A[0] / 2, 1.0, x=(c0 + c1) / 2,
                         y=y + COLLAR_A[0] / 4 + 2, z=z))                 # the split, +Y
    xm = (c0 + c1) / 2
    out = out.cut(cyl_z(M3_PILOT, 20, z - 10, x=xm, y=y + 6.5))
    out = out.cut(cyl_z(3.4, 10, z, x=xm, y=y + 6.5))
    return out.cut(cyl_z(M3_HEAD[0] + 0.5, 10, z + 4.6, x=xm, y=y + 6.5))


def _collar_a_m3(i: int) -> cq.Workplane:
    y, z = y_of(i), za(i)
    (c0, c1), _ = x_collar_a()
    xm = (c0 + c1) / 2
    return _cap("m3", M3_L, (xm, y + 6.5, z + 4.6 + M3_HEAD[1]), (0, 0, -1))


def _collar_b(i: int) -> cq.Workplane:
    """Threaded on the Tr8 inside the plate's hole, its boss on the +X inner race."""
    y, z = y_of(i), za(i)
    a0, a1 = ANCHOR
    out = cyl_x(RACE_IN_D, 0.5, a0, y=y, z=z).union(
        cyl_x(COLLAR_B_D, a1 - 0.2 - (a0 + 0.5), a0 + 0.5, y=y, z=z))
    return out.cut(cyl_x(D.SCREW_OD, 10, a0 - 1, y=y, z=z))


def _nut(i: int, t: float) -> cq.Workplane:
    """The round Tr8x2 flange nut, axis along -X: lip on the flange's +X face, boss behind."""
    y, z, ft = y_of(i), za(i), x_ft(t)
    out = cyl_x(D.NUT_FLANGE_L, D.NUT_FLANGE_T, ft - D.NUT_FLANGE_T, y=y, z=z)
    out = out.union(cyl_x(D.NUT_LIP_D, D.NUT_LIP_L, ft, y=y, z=z))
    out = out.union(cyl_x(D.NUT_BOSS_D, D.NUT_H - D.NUT_FLANGE_T, ft - D.NUT_H, y=y, z=z))
    out = out.cut(cyl_x(D.SCREW_OD, 30, ft - 20, y=y, z=z))
    for a in (45.0, 135.0, 225.0, 315.0):
        dy, dz = at_ang(a)
        out = out.cut(cyl_x(3.5, 10, ft - 5, y=y + dy, z=z + dz))
    return out


def _ball_x(t: float) -> float:
    return x_yt(t) - YK_ROOF - D.STRING_NUT_L / 2


MOTOR_FINISH = {}                                   # motor part -> its finish (motor_parts)


def _motor_frame(wp: cq.Workplane, i: int) -> cq.Workplane:
    """The motor's own frame (shaft +Y from the pulley plane, the D's flat +Z) -> string i's."""
    return (wp.rotate((0, 0, 0), (0, 1, 0), PLUG_DIR[i]).rotate((0, 0, 0), (0, 0, 1), -90)
            .translate((x_ref(i), y_of(i), za(i))))


def _coupler(i: int) -> cq.Workplane:
    """src.motor_coupler's, in string i's motor frame (its D bore on the shaft's flat)."""
    from . import motor_coupler as MC
    return _motor_frame(MC.coupler(), i)


def _coupler_clamp(i: int, k: str) -> cq.Workplane:
    """The coupler's clamp part `k` ("m3" or "insert"), in string i's motor frame."""
    from . import motor_coupler as MC
    return _motor_frame(dict(MC.clamp_parts())[k], i)


def _motor(i: int) -> list:
    from . import components as C
    out = []
    # NO WRITE TO MOTOR_FINISH here (material_of fills it): a global this changed in place made
    # its own kept key move mid-build, so every motor rebuilt on every run
    for k, wp, _, _fin in C.motor_parts():
        w = (wp.rotate((0, 0, 0), (0, 1, 0), PLUG_DIR[i]).rotate((0, 0, 0), (0, 0, 1), -90)
             .translate((x_ref(i), y_of(i), za(i))))
        out.append((f"db_motor_{k}_{i}" if k else f"db_motor_{i}", w))
    return out


def _bend_parts() -> list:
    """Each string's two 688s: the bridge bearing and the bend bearing at its row. Their AXLES
    are the endplate's (endplate_axles): they run wall to wall, so they are sized by the body."""
    out = []
    for i in range(N):
        out.append((f"db_bend_brg_{i}", kept(_bend_brg, i)))
        out.append((f"db_bridge_brg_{i}", kept(_bridge_brg, i)))
    return out


def _bend_brg(i: int) -> cq.Workplane:
    return (ball_bearing(D.BRG688_OD, D.BRG688_ID, D.BRG688_W).rotate((0, 0, 0), (1, 0, 0), -90)
            .translate((X_BEND, y_of(i) - D.BRG688_W / 2, z_level(level(i)) + R)))


def _bridge_brg(i: int) -> cq.Workplane:
    from .helpers import ball_bearing_y
    return ball_bearing_y(D.BRIDGE_BEARING_OD, D.BRIDGE_AXLE_D + 0.3, D.BRIDGE_BEARING_W,
                          y_of(i) - D.BRIDGE_BEARING_W / 2, x=D.BRIDGE_AXLE_X, z=D.BRIDGE_BEARING_Z)


# (the CHEEKS and the separate COMB are gone: the ENDPLATE holds the axles. Kept for the
# bearings' clearances:)
COMB_CLR, COMB_RELIEF = 0.1, 0.5
RACE_D, SHIELD_D = 10.6, 17.0                       # 688 inner race OD (finger contact), relief to


def _tube_y(od, idd, y0, y1, zc):
    return (cyl_y(od, y1 - y0, y0, x=X_BEND, z=zc)
            .cut(cyl_y(idd, y1 - y0 + 2, y0 - 1, x=X_BEND, z=zc)))


def _anchor_y():
    """SIZED TO THE BODY (user, 2026-11-11): ANCHOR_CLR off its walls' inner faces."""
    y0, y1 = body_box()["inner"][1]
    return y0 + ANCHOR_CLR, y1 - ANCHOR_CLR


def _anchor_z():
    """Its bottom ANCHOR_CLR over the body's floor; its top ANCHOR_Z[1] (under the deck), or
    ANCHOR_CLR under the UI station where that hangs over the channel (its clamp, z -15.9)."""
    z0 = body_box()["inner"][2][0]
    top = min(ANCHOR_Z[1], body_box()["ui_bottom_at_anchor"] - ANCHOR_CLR)
    assert top - ANCHOR_T >= za(0) + SPRING_OD / 2 + 1.0, "the anchor's top fold onto row 0's springs"
    return z0 + ANCHOR_CLR, top


def _anchor_pin_z():
    """The two pins a side: under the top fold, and between rows 0 and 1."""
    gap = ((za(0) - SPRING_OD / 2) + (za(1) + SPRING_OD / 2)) / 2
    return (round(_anchor_z()[1] - ANCHOR_T - 4.0, 1), round(gap, 1))


def _anchor() -> cq.Workplane:
    x0, x1 = ANCHOR
    (y0, y1), (z0, z1), T, F = _anchor_y(), _anchor_z(), ANCHOR_T, ANCHOR_FL
    w = box_at(T, y1 - y0, z1 - z0, x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(z0 + z1) / 2)
    xf = x1 + F / 2                                  # the folds' middle, x
    for zc in (z1 - T / 2, z0 + T / 2):              # top and bottom: the channel (flaps of
        w = w.union(box_at(F, y1 - y0 - 2 * T, T, x=xf, y=(y0 + y1) / 2, z=zc))   # their own,
    zp = min(_anchor_pin_z())                        # between the end folds)
    for yc in (y1 - T / 2, y0 + T / 2):              # both ends: hung on the pins
        w = w.union(box_at(F, T, z1 - z0, x=xf, y=yc, z=(z0 + z1) / 2))
        w = w.cut(box_at(ANCHOR_SLOT_W, T + 2, z1 + 1 - zp, x=xf, y=yc, z=(zp + z1 + 1) / 2))
        w = w.cut(cyl_y(ANCHOR_SLOT_W, T + 2, yc - T / 2 - 1, x=xf, z=zp))     # its round end
    for i in range(N):                               # collar B's hole (the bearing's rim round
        y, z = y_of(i), za(i)                        # it), the two bolts, and the rod's way in
        w = w.cut(cyl_x(PLATE_HOLE_D, 20, x0 - 10, y=y, z=z))
        ry, rz = rod_yz(i)
        w = w.cut(cyl_x(GUIDE_SEAT + 0.4, 20, x0 - 10, y=ry, z=rz))
        for a in EAR_ANG:
            dy, dz = at_ang(a, EAR_R)
            w = w.cut(cyl_x(4.5, 20, x0 - 10, y=y + dy, z=z + dz))
    return w


def _anchor_pins() -> cq.Workplane:
    """The four Ø5 dowels: ANCHOR_PIN_PROUD inside each end fold, out through the skin into the bar."""
    (y0, y1), xf = _anchor_y(), ANCHOR[1] + ANCHOR_FL / 2
    out = None
    for yf, sg in ((y1 - ANCHOR_T, 1), (y0 + ANCHOR_T, -1)):   # each fold's inner face, outward
        y_in = yf - sg * ANCHOR_PIN_PROUD
        for zb in _anchor_pin_z():
            b = cyl_y(ANCHOR_PIN_D, ANCHOR_PIN_L, min(y_in, y_in + sg * ANCHOR_PIN_L), x=xf, z=zb)
            out = b if out is None else out.union(b)
    return out


def _string(i: int, t: float) -> cq.Workplane:
    g = D.STRING_GAUGE[i]
    y0, y1 = D.nut_y(i), y_of(i)
    zs = D.STRING_Z + g / 2
    rr = R + g / 2
    pts = [(D.NUT_BLOCK_X - 30.0, y0, zs - 3.0), (D.NUT_BLOCK_X, y0, zs), (BR_C[0], y1, zs)]
    for k in range(1, 7):                            # over the bridge, 90 -> 0 deg
        a = math.pi / 2 * (1 - k / 6)
        pts.append((BR_C[0] + rr * math.cos(a), y1, BR_C[1] + rr * math.sin(a)))
    zc = z_level(level(i)) + R
    for k in range(0, 7):                            # round the bend, 0 -> -90 deg
        a = -math.pi / 2 * k / 6
        pts.append((X_BEND + rr * math.cos(a), y1, zc + rr * math.sin(a)))
    pts.append(yaw_pt((_ball_x(t), y1, za(i)), i))
    out = None
    for a, b in zip(pts, pts[1:]):
        if math.dist(a, b) > 1e-3:
            s = _seg(a, b, g)
            out = s if out is None else out.union(s)
    return out


def _mplate(i: int) -> cq.Workplane:
    """The motor's plate: pilot and the four M3s. At the +X-most station (SLOT_STATIONS) every
    hole is 1.2 oversize -- slotted every way, +-0.6 -- so the motor lines up on its short screw
    (held at both ends: the anchor's 688s and the motor's own bearings) before it is tightened."""
    y, z, xr = y_of(i), za(i), x_ref(i)
    extra = 1.2 if STATION[i] in SLOT_STATIONS else 0.0
    x0 = xr - M_FACE
    out = box_at(PLATE_T, D.MOTOR_SQ, D.MOTOR_SQ, x=x0 + PLATE_T / 2, y=y, z=z)
    out = out.cut(cyl_x(D.NEMA17_PILOT_D + 0.6 + extra, 10, x0 - 1, y=y, z=z))
    for sy in (1, -1):
        for sz in (1, -1):
            out = out.cut(cyl_x(3.4 + extra, 10, x0 - 1, y=y + sy * NEMA17_HOLES / 2,
                                z=z + sz * NEMA17_HOLES / 2))
    return out


def _keyplate_at(i: int, t: float) -> cq.Workplane:
    return keyhole_plate().translate((x_yt(t), y_of(i), za(i)))


def _ball(i: int, t: float) -> cq.Workplane:
    return cyl_x(D.STRING_NUT_D, D.STRING_NUT_L, _ball_x(t) - D.STRING_NUT_L / 2, y=y_of(i), z=za(i))


def _rod(i: int) -> cq.Workplane:
    return cyl_x(GUIDE_D, ROD_L, ROD_END, y=rod_yz(i)[0], z=rod_yz(i)[1])


def _screw_at(i: int) -> cq.Workplane:
    return _screw(i, x_ref(i) + SCREW_X0, SCREW_TIP)


def _brg(i: int) -> cq.Workplane:
    return (ball_bearing(D.BRG688_OD, D.BRG688_ID, 2 * D.BRG688_W)
            .rotate((0, 0, 0), (0, 1, 0), 90).translate((ANCHOR[0] - HOUSE_POCKET, y_of(i), za(i))))


def _cpl_m3(i: int) -> cq.Workplane:
    return _coupler_clamp(i, "m3")


def _cpl_insert(i: int) -> cq.Workplane:
    return _coupler_clamp(i, "insert")


# String i's parts: (name, builder, whether it moves with travel t). EACH IS KEPT ON ITS OWN
# (user, 2026-11-12: "Why aren't we caching everything separately?"): an edit to one part's code
# rebuilds that part only -- the coil springs and the threaded screws (most of the build time)
# are not redone for a collar or a plug change, and parts that do not move with travel are built
# once for every t.
_STRING_PARTS = (
    ("db_yoke", _yoke, True), ("db_keyplate", _keyplate_at, True), ("db_ball", _ball, True),
    ("db_nut", _nut, True), ("db_collar", _collar, True), ("db_m3", _m3s, True),
    ("db_spring", _spring, True), ("db_sleeve_p", _sleeve_plug, False),
    ("db_sleeve_c", _sleeve_collar, True), ("db_plug", _anchor_plug, False),
    ("db_rod", _rod, False), ("db_screw", _screw_at, False), ("db_coupler", _coupler, False),
    ("db_cpl_m3", _cpl_m3, False), ("db_cpl_insert", _cpl_insert, False),
    ("db_housing", _housing, False), ("db_hb", _housing_bolts, False),
    ("db_insert", _inserts, False), ("db_collar_a", _collar_a, False),
    ("db_ca_m3", _collar_a_m3, False), ("db_collar_b", _collar_b, False),
    ("db_brg", _brg, False), ("db_mplate", _mplate, False),
)


def string_parts(i: int, t: float) -> list:
    """String i's drive, drawn along -X at (y_of(i), za(i)), yawed into place: each part kept."""
    out = []
    for nm, make, moves in _STRING_PARTS:
        args = (t,) if moves else ()
        out.append((f"{nm}_{i}", yaw(kept(make, i, *args), i)))
    out += [(nm, yaw(w, i)) for nm, w in kept(_motor, i)]
    out.append((f"db_string_{i}", kept(_string, i, t)))
    return out


# -- THE UI STATION (user, 2026-11-11) ---------------------------------------------------------
# The lead's station (src.ui_panel) as it is -- the display at the same X off the bridge bearings,
# the joystick and the power button either side as close as they go -- but moved +Y until the
# display module's +Y edge TOUCHES THE FRET BORDER (as far toward the centre as it can go), so
# the body grows -Y for it as little as possible. The whole station moves together, by ui_parts()[1].
def _ui_moved():
    from . import ui_panel as U
    parts = U.parts()
    ymax = dict(parts)["ui_display"].val().BoundingBox().ymax
    dy = U.fret_border_y() - ymax
    return [(nm, w.translate((0.0, dy, 0.0))) for nm, w in parts], dy


@_lru_cache(maxsize=None)
def ui_parts() -> tuple:
    parts, dy = kept(_ui_moved)
    return tuple((nm, w) for nm, w in parts), dy


# -- THE BODY (user, 2026-11-11): a hollow box, no roof, opaque PETG-GF like the lead's ----------------------------------------
# Its +X, +-Y and floor are the drive's and the UI's extents (the strings and the anchor plate
# left out: the plate is SIZED TO the body) plus BODY_CLR; its -X end is the nut block's, so the
# body holds the scale length and the current nut block. Its walls stand to the deck's top.
# TODO: the nut block's -X face is MEASURED ONCE (src.keyhead_endplate.assembly(), its
# keyhead_endplate part, 2026-11-11), not read live: re-measure it when the nut block changes.
NUT_BLOCK_X0 = -648.3
BODY_CLR = 2.0                                      # inside the walls and ends
FLOOR_CLR = 0.5                                     # the floor under the lowest motor (user, 2026-11-12:
                                                    # the motors hang on their plates; the floor never
                                                    # touches them, but no more gap than print tolerance)
BODY_WALL = D.WALL_THICKNESS                        # 10.4, every wall
BODY_FLOOR = 6 * D.BEAD                             # 4.8


def _compound(nm, w):
    # a part of several solids (a pair of bolts) goes as ONE compound: the view and the export
    # take a part's first solid only
    return (nm, cq.Workplane("XY").add(cq.Compound.makeCompound(w.solids().vals()))
            if len(w.solids().vals()) > 1 else w)


def _drive(t: float) -> list:
    """Every part but the anchor plate and its bolts, the UI, the ghosts and the body.
    KEPT PART BY PART (user, 2026-11-11: "changing the chassis shouldn't rebuild the items inside
    it"; 2026-11-12: every showable part its own entry): each part is read back from cadkit's
    store until something IT reads changes."""
    out = []
    for i in range(N):
        out += string_parts(i, t)                   # each part kept on its own (_STRING_PARTS)
    out += _bend_parts()
    return [_compound(nm, w) for nm, w in out]


def _extents(drive, ui, pick):
    """(lo, hi, ui_bottom_at_anchor): the drive's, the pickup's and the UI's extents, plain
    numbers -- KEPT, so a body change costs no re-measuring (406 optimal boxes, ~11 s). The
    parts come in as ARGUMENTS, kept results named by where they came from: the key is cheap."""
    lo, hi = [1e9] * 3, [-1e9] * 3
    for w in drive + pick + ui:
        bb = w.val().BoundingBox()
        for k, (a, b) in enumerate(((bb.xmin, bb.xmax), (bb.ymin, bb.ymax), (bb.zmin, bb.zmax))):
            lo[k], hi[k] = min(lo[k], a), max(hi[k], b)
    ax0, ax1 = ANCHOR[0], ANCHOR[1] + ANCHOR_FL
    zs = [bb.zmin for bb in (w.val().BoundingBox() for w in ui) if bb.xmax > ax0 and bb.xmin < ax1]
    return lo, hi, min(zs, default=ANCHOR_Z[1] + 1.0)


@_lru_cache(maxsize=None)
def body_box() -> dict:
    """{"inner"/"outer": ((x0, x1), (y0, y1), (z0, z1)), "ui_bottom_at_anchor": z}."""
    from .changer_bench import DECK_UNDER
    from .changer_bench import ghosts as _ghosts
    pick = [w for nm, w in _ghosts(y_hi=RAIL_HI) if nm == "ghost_pickup"]
    drive = [w for nm, w in _drive(T_OPEN) if not nm.startswith("db_string")]
    lo, hi, ui_bottom = kept(_extents, drive, [w for _, w in ui_parts()[0]], pick)
    top = DECK_UNDER + 9.6                          # the deck's top: the walls' top
    inner = ((NUT_BLOCK_X0 + BODY_WALL, hi[0] + BODY_CLR), (lo[1] - BODY_CLR, hi[1] + BODY_CLR),
             (lo[2] - FLOOR_CLR, top))
    outer = ((NUT_BLOCK_X0, inner[0][1] + BODY_WALL),
             (inner[1][0] - BODY_WALL, inner[1][1] + BODY_WALL), (inner[2][0] - BODY_FLOOR, top))
    return dict(inner=inner, outer=outer, ui_bottom_at_anchor=ui_bottom)


# THE WALL BARS (user, 2026-11-12): a 1/4 x 3-1/2 in A-36 flat bar in each side wall, its 3-1/2
# standing in Z. The usable height runs from the lowest motor's bottom to the strings' top less
# 20 (103.6): the bar sits at its top, under a two-bead skin and its clearance. Steel, not
# aluminium: the bars set the length the strings are stretched over, and steel expands with
# them (aluminium would drift ~3-4 cents/degC). 1/4 thick keeps the standard 10.4 wall.
# THE CLAMP (user, 2026-11-12): each endplate screws to the bars' ends, four M3s along X into
# holes drilled and tapped in the bar ends (+Z+Y, -Z+Y, +Z-Y, -Z-Y; a printed drill jig puts them
# dead centre), M3 x 16 through a Ø9 washer (DIN 9021 M3: ~9 MPa on the plastic at 0.5 kN, a
# level PETG-GF holds without creeping off), reached down a tunnel from the +X end. The bars STOP SHORT of the endplate's wall (EP_GAP), so the
# screws pull the endplate onto the walls' ends and squeeze the sections together; the bar end
# only locates in a shallow POCKET. Sizes from the load (memory endplate-bar-clamp): pocket 5
# (locating only), wall 8 (bending over the bar's width), the counterbore over it for the head
# and washer.
BAR_T, BAR_H = 25.4 / 4, 25.4 * 3.5                  # 6.35 across Y, 88.9 in Z
BAR_CLR, BAR_SKIN = 0.2, 2 * D.BEAD
STRING_TOP = D.STRING_Z + 1.9 / 2                    # the heaviest string's top
BAR_Z = (STRING_TOP - 20.0 - BAR_SKIN - BAR_CLR - BAR_H, STRING_TOP - 20.0 - BAR_SKIN - BAR_CLR)
EP_POCKET, EP_GAP, EP_WALL = 5.0, 1.0, 8.0
# ISO 7089 / DIN 125-A M3 washer (user, 2026-11-12: the Ø9 DIN 9021 left a razor edge; the head
# is 2.45 from the wall's outer face, so a washer may reach 0.85 past it and keep 1.6 of wall)
EP_WASHER = (7.0, 0.5)                               # OD, thickness
EP_TUNNEL = 7.2                                      # the screw's way in from the +X end (as printed,
                                                     # fit=True): 0.1 a side over the washer, 1.6 wall
EP_M3_CLR = 3.4
EP_SCREW_Z = (BAR_Z[1] - 8.0, BAR_Z[0] + 5.5)        # the two screws in each bar end (the low one
                                                     # 5.5 up: its tunnel then clears row c's axle)


def bar_y() -> tuple:
    """Each wall bar's centre y (the -Y wall's, the +Y wall's): the middle of its wall."""
    (_, _), (y0, y1), _ = body_box()["outer"]
    return y0 + BODY_WALL / 2, y1 - BODY_WALL / 2


def ep_x() -> dict:
    """Along X from the JOINT (x_j: the walls' and the rod plate's -X face) to the +X END: the
    bar's pocket, its end (the gap after it), the BACK WALL the screws pull on, and the end."""
    x_j = ROD_PLATE[0]
    bar_end = x_j + EP_POCKET
    wall0 = bar_end + EP_GAP
    # the +X end (the fingers' tips) flush with the outside of the heaviest gauge the instrument
    # takes where it drops off the bearings (user, 2026-11-12: no more than that)
    x_end = X_BEND + R + D.STRING_GAUGE_MAX
    # the screw heads FLUSH with the +X end (user, 2026-11-12): the back wall runs on to the
    # washer under the head, so it is EP_WALL at least (the 8 the load needs) and usually more
    from . import belt_tensioner as BTn
    wall1 = x_end - EP_WASHER[1] - BTn.HEAD_H
    assert wall1 - wall0 >= EP_WALL, "the back wall is thinner than the load needs"
    return dict(x_j=x_j, bar_end=bar_end, wall0=wall0, wall1=wall1, x_end=x_end)


# McMaster 18-8 M3 SHCS stock lengths (91292A: 20, 22, 25, 30 read 2026-11-12) and the thread in the
# bar: 1.5 d -- in steel that already outlasts the screw, and every mm more is drilling and
# tapping the bar end (user, 2026-11-12: only as deep as a firm, lasting grip needs); the tapped
# hole goes EP_TAP_EXTRA past the tip
M3_STOCK = (16.0, 20.0, 22.0, 25.0, 30.0)
EP_ENGAGE, EP_TAP_EXTRA = 1.5 * 3.0, 2.0


def bar_screw_len() -> float:
    """The shortest stock M3 that, head flush with the +X end, reaches EP_ENGAGE into the bar."""
    e = ep_x()
    need = e["wall1"] - e["bar_end"] + EP_ENGAGE
    return min(L for L in M3_STOCK if L >= need)


def _bar_box(yc: float, x0: float, x1: float, grow: float = 0.0) -> cq.Workplane:
    z0, z1 = BAR_Z[0] - grow, BAR_Z[1] + grow
    return box_at(x1 - x0, BAR_T + 2 * grow, z1 - z0, x=(x0 + x1) / 2, y=yc, z=(z0 + z1) / 2)


def _wall_bars() -> list:
    return [(f"db_wall_bar_{k}", kept(_wall_bar, k)) for k in range(2)]


def _wall_bar(k: int) -> cq.Workplane:
    """Bar k (0: -Y, 1: +Y), its two tapped M3 holes in the +X end (drawn as the tap drill)."""
    # TODO: the -X end stops short of the -X endplate (the keyhead's), which is not modelled here
    x0 = body_box()["outer"][0][0] + BODY_WALL + 1.0
    x1 = ep_x()["bar_end"]
    yc = bar_y()[k]
    b = _bar_box(yc, x0, x1)
    for zc in EP_SCREW_Z:
        depth = bar_screw_len() - (ep_x()["wall1"] - x1) + EP_TAP_EXTRA
        b = b.cut(cyl_x(2.5, depth, x1 - depth, y=yc, z=zc))
    for zp in _anchor_pin_z():                       # the anchor's pins: drilled through, Ø5
        b = b.cut(cyl_y(ANCHOR_PIN_D, BAR_T + 2, yc - BAR_T / 2 - 1,
                        x=ANCHOR[1] + ANCHOR_FL / 2, z=zp))
    return b


def _bar_screws() -> list:
    """The four M3 SHCS (bar_screw_len) and their washers: through the back wall into the bar
    ends, the head on its washer flush with the +X end."""
    from . import belt_tensioner as BTn
    e = ep_x()
    out = None
    for yc in bar_y():
        for zc in EP_SCREW_Z:
            top = e["wall1"] + EP_WASHER[1] + BTn.HEAD_H
            sc = _cap("m3", bar_screw_len(), (top, yc, zc), (-1, 0, 0))
            sc = sc.union(cyl_x(EP_WASHER[0], EP_WASHER[1], e["wall1"], y=yc, z=zc)
                          .cut(cyl_x(3.2, EP_WASHER[1] + 1, e["wall1"] - 0.5, y=yc, z=zc)))
            out = sc if out is None else out.union(sc)
    return out


def _body() -> cq.Workplane:
    """The walls and floor up to the endplate, all ending at x_j: one print, so one flat face the
    endplate bears on. The floor carries the strings' pull across the middle (2026-11-12:
    no floor gap; the walls alone left the endplate a 168 mm beam at ~16 MPa through a lane).
    Each wall carries its bar's channel, open at +X."""
    (x0, _), (y0, y1), (z0, z1) = body_box()["outer"]
    (a0, _), (b0, b1), (c0, _) = body_box()["inner"]
    xj = ep_x()["x_j"]
    w = box_at(xj - x0, y1 - y0, z1 - z0, x=(x0 + xj) / 2, y=(y0 + y1) / 2, z=(z0 + z1) / 2)
    w = w.cut(box_at(xj + 1 - a0, b1 - b0, z1 - c0 + 2.0, x=(a0 + xj + 1) / 2, y=(b0 + b1) / 2,
                     z=(c0 + z1 + 2.0) / 2))
    for yc, yin in zip(bar_y(), (b0, b1)):
        w = w.cut(_bar_box(yc, x0 + BODY_WALL, xj + 1, BAR_CLR))
        for zp in _anchor_pin_z():                   # the anchor pins through the INNER skin only
            lo, hi = min(yc, yin), max(yc, yin)      # (a grip as printed; the outer skin stays whole)
            w = w.cut(cyl_y(ANCHOR_PIN_D, hi - lo + 0.5, lo - (0.5 if lo == yin else 0),
                            x=ANCHOR[1] + ANCHOR_FL / 2, z=zp))
    return w


# THE ENDPLATE (user, 2026-11-12): ONE printed PETG-GF part, the instrument's +X end from the
# JOINT (x_j, where the walls and floor end) to the end, the full height (the bed under it to the
# bridge axle's top), PRINTED -Z -> +Z. Just enough of it to:
#   - hold each GUIDE ROD (its seat from the plate's back, ~11 deep: ROD_TIP);
#   - be the ROD PLATE (x_j .. ROD_PLATE[1]), with the balls' windows; it stays under the pickup
#     (PLATE_TOP) where the pickup reaches it;
#   - hold the 4 AXLES (the three bend rows and the bridge): each slides in from the -Y face to a
#     STOP AXLE_STOP_T short of the +Y face, where a PUSH hole lets a 2.5 key push it back out;
#   - put a FINGER in all 9 gaps between the strings (each lane LANE_HW each side of a string,
#     its bearings' clearance), the side zones solid past strings 1 and 10;
#   - take the BAR ENDS: a POCKET (locating), the GAP, the BACK WALL the M3s pull on, and a
#     tunnel from the +X end down to the screw heads.
EP_TOP = D.BRIDGE_BEARING_Z + (D.BRIDGE_AXLE_D + 0.2) / 2 + 3 * D.BEAD   # 14.5: over the bridge axle
PLATE_TOP = -20.5                                    # under the pickup ...
PLATE_LOW_X = -20.0                                  # ... where it reaches (x -21)
PICK_Y = (-52.9, 51.1)                               # the pickup's y, and 1 each side
LANE_HW = D.BRG688_W / 2 + COMB_CLR                  # 2.6: a string's lane, its bearings in it
LANE_WALL = 2 * D.BEAD                               # a lane's floor over the next row's axle bore
AXLE_STOP_T, PUSH_D = 3.0, 3.2                       # the +Y stop; the push-out hole (a 2.5 key)


def axle_zs() -> list:
    """(name, z) of the four axles, all at x X_BEND."""
    return [(f"db_bend_axle_r{'abc'[k]}", z_level(k) + R) for k in range(LEVELS)] + \
           [("db_bridge_axle", D.BRIDGE_BEARING_Z)]


AXLE_GRIP = D.BRIDGE_AXLE_D                          # each end's grip in plastic past the outer lane
                                                     # (user, 2026-11-12: axles only as long as a
                                                     # solid grip needs; the fingers between hold it too)


def axle_span() -> tuple:
    """Each axle's y: one length for all four rows (one part to stock), the outermost lanes'
    width plus AXLE_GRIP each side. It goes in from -Y down its bore and stops on the +Y wall."""
    ys = [y_of(i) for i in range(N)]
    return min(ys) - LANE_HW - AXLE_GRIP, max(ys) + LANE_HW + AXLE_GRIP


def endplate_axles() -> list:
    return [(nm, kept(_axle, k)) for k, (nm, _) in enumerate(axle_zs())]


def _axle(k: int) -> cq.Workplane:
    a, b = axle_span()
    return cyl_y(D.BRIDGE_AXLE_D, b - a, a, x=X_BEND, z=axle_zs()[k][1])


def _endplate() -> cq.Workplane:
    from cadkit.holes import teardrop_hole
    (_, _), (y0, y1), (z0, _) = body_box()["outer"]
    e = ep_x()
    xj, xe = e["x_j"], e["x_end"]
    w = box_at(xe - xj, y1 - y0, EP_TOP - z0, x=(xj + xe) / 2, y=(y0 + y1) / 2, z=(z0 + EP_TOP) / 2)
    if PLATE_LOW_X > xj:                                         # low under the pickup
        w = w.cut(box_at(PLATE_LOW_X - xj + 1, PICK_Y[1] - PICK_Y[0], EP_TOP - PLATE_TOP + 1,
                         x=(xj - 1 + PLATE_LOW_X) / 2, y=sum(PICK_Y) / 2,
                         z=(PLATE_TOP + EP_TOP + 1) / 2))
    for i in range(N):                                           # the lanes, and the windows
        za_i = za(i)
        # each lane runs out through the +X end and the top (user, 2026-11-12: open, only the
        # fingers between the bearings, so a string feeds in and out when restringing)
        # ...and down as deep as the window, so the keyhole's bottom shows from above and the
        # ball goes straight in (user, 2026-11-12), but LANE_WALL over the peak of the next
        # row's axle bore (a teardrop, peaked +Z) where one runs under the lane
        lo = za_i + WIN_Z[0]
        under = [zc for _, zc in axle_zs() if zc < za_i]
        if under:
            lo = max(lo, max(under) + (D.BRIDGE_AXLE_D + 0.2) / 2 * math.sqrt(2) + LANE_WALL)
        w = w.cut(box_at(xe + 1 - ROD_PLATE[1], 2 * LANE_HW, EP_TOP + 1 - lo,
                         x=(ROD_PLATE[1] + xe + 1) / 2, y=y_of(i), z=(lo + EP_TOP + 1) / 2))
        lo, hi = WIN_Z
        w = w.cut(box_at(ROD_PLATE[1] - xj + 2, 2 * WIN_HY, hi - lo, x=(xj + ROD_PLATE[1]) / 2,
                         y=y_of(i), z=za_i + (lo + hi) / 2))
    rb = GUIDE_SEAT / 2 + GUIDE_WALL                             # the rods' bosses: a teardrop
    for i in range(N):                                           # peaked -Z, so where one stands
        ry, rz = rod_yz(i)                                       # in a lane it prints from the plate
        w = w.union(teardrop_hole(2 * rb, ROD_TIP + 0.3 + 1.0 - xj, axis_point=(xj, ry, rz),
                                  axis_dir=(1, 0, 0), print_up=(0, 0, -1)))
    for i in range(N):
        ry, rz = rod_yz(i)
        w = w.cut(teardrop_hole(GUIDE_SEAT, ROD_TIP + 0.3 - (xj - 3), axis_point=(xj - 3, ry, rz),
                                axis_dir=(1, 0, 0), fit=True))
        # the CRUSH RIBS at its bottom (ROD_GRIP): three, at the bottom and +-120, each reaching
        # ROD_RIB inside the rod's circle -- the rod, pushed home from -X, stays put
        rr = GUIDE_D / 2 - ROD_RIB
        for a in (270.0, 30.0, 150.0):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            rib = box_at(ROD_GRIP, 0.8, 1.0, x=ROD_TIP + 0.3 - ROD_GRIP / 2, y=0, z=rr + 0.5)
            w = w.union(rib.rotate((0, 0, 0), (1, 0, 0), a - 90).translate((0, ry, rz)))
    a, b = axle_span()
    for nm, zc in axle_zs():                                     # the axles: in from -Y, the stop,
        w = w.cut(teardrop_hole(D.BRIDGE_AXLE_D + 0.2, b - (y0 - 1), axis_point=(X_BEND, y0 - 1, zc),
                                axis_dir=(0, 1, 0)))
        w = w.cut(teardrop_hole(PUSH_D, y1 + 1 - (b - 0.5), axis_point=(X_BEND, b - 0.5, zc),
                                axis_dir=(0, 1, 0)))             # and the push-out hole
    for i in range(N):                                           # the fingers' reliefs: off the
        for zc in (z_level(level(i)) + R, D.BRIDGE_BEARING_Z):   # turning outer races, both sides
            yb = y_of(i)
            w = w.cut(_tube_y(SHIELD_D, RACE_D, yb - LANE_HW - COMB_RELIEF, yb - LANE_HW + 0.01, zc))
            w = w.cut(_tube_y(SHIELD_D, RACE_D, yb + LANE_HW - 0.01, yb + LANE_HW + COMB_RELIEF, zc))
    for yc in bar_y():                                           # the bars' ends
        w = w.cut(_bar_box(yc, xj - 1, e["wall0"], BAR_CLR))      # pocket + gap
        for zc in EP_SCREW_Z:
            w = w.cut(teardrop_hole(EP_M3_CLR, e["wall1"] - e["bar_end"] + 1,
                                    axis_point=(e["bar_end"], yc, zc), axis_dir=(1, 0, 0), fit=True))
            w = w.cut(teardrop_hole(EP_TUNNEL, xe + 1 - e["wall1"], axis_point=(e["wall1"], yc, zc),
                                    axis_dir=(1, 0, 0), fit=True))
    return w


@_lru_cache(maxsize=None)
def endplate_full():
    return kept(_endplate)


def assembly(t: float = T_OPEN, all_ghosts: bool = False) -> list:
    from .changer_bench import ghosts as _ghosts
    out = _drive(t) + [("db_endplate", endplate_full())] + endplate_axles()
    # EVERY PART THE VIEW CAN SHOW OR HIDE IS KEPT ON ITS OWN (user, 2026-11-12): an edit
    # rebuilds the parts whose code or inputs it touched, and nothing else
    out += [_compound("db_anchor", kept(_anchor)), _compound("db_anchor_pin", kept(_anchor_pins))]
    out += _wall_bars() + [_compound("db_bar_m3", kept(_bar_screws))]
    out = [(nm, _made(nm, w)) for nm, w in out] + list(ui_parts()[0])
    out.append(("db_body", _made("db_body", kept(_body))))   # opaque PETG-GF, as the lead's chassis
    out += [g for g in _ghosts(y_hi=RAIL_HI)
            if g[0] != "ghost_bottom_now" and (all_ghosts or g[0] == "ghost_pickup")]
    return out


# What each part is made of, for the viewer's shine (cadkit.web.finishes.made_of): printed
# frames in the instrument's PETG-GF, the bought parts as they are.
MATERIAL = {
    "yoke": "petg-gf", "keyplate": "steel", "collar": "pctg", "block": "petg-gf", "mplate": "petg-gf",
    "endplate": "petg-gf", "bar_m3": "steel", "bridge_axle": "steel", "bridge_brg": "polished", "anchor": "stainless", "anchor_pin": "steel",
    "body": "petg-gf", "wall_bar": "steel",
    "nut": "brass", "ball": "brass", "screw": "steel", "rod": "steel", "string": "polished",
    "brg": "polished", "bend_brg": "polished", "bridge_bearings": "polished",
    "bend_axle_ra": "steel", "bend_axle_rb": "steel", "bend_axle_rc": "steel",
    "spring": "stainless", "plug": "petg-gf", "sleeve_p": "petg-gf", "sleeve_c": "petg-gf", "m3": "steel", "coupler": "petg-gf",
    "cpl_m3": "steel", "cpl_insert": "brass", "housing": "petg-gf", "hb": "steel", "insert": "brass",
    "collar_a": "petg-gf", "collar_b": "petg-gf", "ca_m3": "steel",
}


def material_of(base: str):
    """The material of a direct-bench part (its name, indices off), or None."""
    inner = base[3:]
    if inner.startswith("motor"):
        if not MOTOR_FINISH:
            from . import components as C
            MOTOR_FINISH.update({k: fin for k, _, _, fin in C.motor_parts()})
        return MOTOR_FINISH.get(inner[6:] if inner != "motor" else "")
    return MATERIAL.get(inner)


def _made(nm: str, w):
    from cadkit.web.finishes import made_of
    m = material_of(_re.sub(r"(_\d+)+$", "", nm))
    return made_of(w, m) if m else w


# ── colours (src.build._color_for asks here for db_ names) ──────────────────────────────────
# inner name (db_ and EVERY trailing index group off) -> a key of build._COLORS, or an RGB.
COLORS = {
    "nut": "nut", "ball": "string_nut", "screw": "leadscrew", "brg": "screw_bearing",
    "string": "string", "bridge_bearings": "bridge_bearings", "rod": "guide_rod",
    "bend_brg": "bridge_bearings", "bend_axle_ra": "leadscrew", "bend_axle_rb": "leadscrew",
    "bend_axle_rc": "leadscrew",
    "yoke": (0.39, 0.58, 0.93), "collar": (0.85, 0.45, 0.15),
    "spring": "leg_latch_spring", "plug": (0.85, 0.45, 0.15),
    "sleeve_p": (0.95, 0.75, 0.20), "sleeve_c": (0.95, 0.75, 0.20), "m3": "set_screw",
    "coupler": (0.85, 0.45, 0.15), "cpl_m3": "set_screw",
    "housing": (0.30, 0.36, 0.42), "hb": "set_screw", "insert": "nut",
    "collar_a": (0.85, 0.45, 0.15), "collar_b": (0.85, 0.45, 0.15), "ca_m3": "set_screw", "block": (0.30, 0.36, 0.42), "mplate": (0.30, 0.33, 0.38),
    "endplate": (0.36, 0.30, 0.42), "bar_m3": "set_screw", "bridge_axle": "set_screw",
    "bridge_brg": "bridge_bearings", "anchor": "nut_plate", "anchor_pin": "set_screw",
    "body": "chassis", "wall_bar": "nut_plate", "keyplate": "nut_plate",
}


def color_of(base: str, table: dict):
    inner = base[3:] if base.startswith("db_") else base
    v = COLORS.get(inner, inner)
    return v if isinstance(v, tuple) else table.get(v)


# ── the gate ────────────────────────────────────────────────────────────────────────────────
import re as _re

_IDX = _re.compile(r"_(\d+)$")


def _base(nm: str):
    m = _IDX.search(nm)
    b, i = (nm[:m.start()], int(m.group(1))) if m else (nm, None)
    return ("db_motor" if b.startswith("db_motor") else b), i


_SAME = {frozenset(p) for p in (
    ("db_screw", "db_nut"), ("db_screw", "db_brg"), ("db_screw", "db_coupler"),
    ("db_nut", "db_yoke"), ("db_nut", "db_collar"),
    ("db_m3", "db_collar"), ("db_m3", "db_nut"), ("db_m3", "db_yoke"), ("db_m3", "db_keyplate"),
    ("db_spring", "db_plug"),
    ("db_sleeve_p", "db_plug"), ("db_sleeve_p", "db_spring"),
    ("db_sleeve_c", "db_collar"), ("db_sleeve_c", "db_spring"),
    ("db_yoke", "db_ball"), ("db_string", "db_ball"), ("db_string", "db_yoke"),
    ("db_collar", "db_spring"), ("db_brg", "db_block"), ("db_coupler", "db_motor"),
    ("db_motor", "db_mplate"), ("db_motor",), ("db_coupler", "db_block"),
    ("db_cpl_m3", "db_cpl_insert"),
    ("db_housing", "db_brg"), ("db_collar_a", "db_brg"), ("db_collar_b", "db_brg"),
    ("db_collar_a", "db_screw"), ("db_collar_b", "db_screw"), ("db_ca_m3", "db_collar_a"),
    ("db_hb", "db_housing"), ("db_hb", "db_plug"), ("db_hb", "db_insert"), ("db_insert", "db_plug"),
    ("db_housing", "db_plug"))}


def is_intended(a: str, b: str) -> bool:
    (ba, ia), (bb_, ib) = _base(a), _base(b)
    if ia is not None and ia == ib and frozenset((ba, bb_)) in _SAME:
        return True
    pair = {ba, bb_}
    if all(n.startswith("ghost_") for n in pair):
        return True
    bends = {"db_bend_axle_ra", "db_bend_axle_rb", "db_bend_axle_rc", "db_bend_brg"}
    if "db_string" in pair and pair & (bends | {"db_bridge_brg", "db_bridge_axle", "ghost_keyhead"}):
        return True
    if "db_bridge_brg" in pair and "db_bridge_axle" in pair:       # each bridge 688 on its axle
        return True
    if "db_bar_m3" in pair and "db_wall_bar" in pair:              # threaded into the bar ends
        return True
    # the tunnels and clearance holes are drawn 0.4 under (fit=True: sideways teardrops print that
    # much over), so the Ø7 washer and the shank touch the holes as drawn, not as printed
    if "db_bar_m3" in pair and "db_endplate" in pair:
        return True
    # the lead's instrument's ghosts (deck, walls, keyhead) stand where this body's own walls,
    # bars and endplate now are: no clash to report against a ghost of the other design
    if any(n.startswith("ghost_") for n in pair) and pair & {
            "db_wall_bar", "db_endplate", "db_bar_m3", "db_body", "db_bridge_axle",
            "db_bend_axle_ra", "db_bend_axle_rb", "db_bend_axle_rc"}:
        return True
    if "db_bend_brg" in pair and pair & bends - {"db_bend_brg"}:      # each 688 on its axle
        return True
    if "db_rod" in pair and "db_endplate" in pair:
        return True
    if "db_anchor_pin" in pair and pair & {"ghost_wall_hi", "ghost_wall_lo"}:
        return True
    if "db_anchor" in pair and pair & {"ghost_wall_hi", "ghost_wall_lo"}:   # sized to THIS body
        return True
    if "db_anchor" in pair and pair & {"db_plug", "db_brg", "db_housing", "db_hb", "db_collar_b"}:
        return True
    return False


def gate(ts=(0.0, T_OPEN, 1.0)) -> int:
    """Each spring checked as its whole tube, OD to ID (stricter than the coils, and a helix
    against its neighbours costs minutes)."""
    global COILS
    from cadkit import overlap_check as OC
    COILS = False
    bad = 0
    for t in ts:
        comps = [(nm, cq.Compound.makeCompound(w.vals()) if len(w.vals()) > 1 else w.val())
                 for nm, w in assembly(t, all_ghosts=True)]
        print(f"\n#### travel t = {t:.2f}")
        bad += OC.run(comps, is_intended)
    return bad


if __name__ == "__main__":
    import sys
    print(report())
    if "--gate" in sys.argv:
        sys.exit(gate())
