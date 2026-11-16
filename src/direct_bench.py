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
    TENSION into its 688 at the motor end. A yoke on the nut's +X face holds the ball end on
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
import functools as _functools
from functools import lru_cache as _lru_cache

from cadkit.kept import kept
try:                    # BOUGHT HARDWARE DRAWN AS IT IS (cadkit.mesh_parts, 2026-11-16): threads, knurls
    from cadkit.mesh_parts import placed, fused, insert_mesh, swap_bore, with_mesh, affine_of
except ImportError:     # a cadkit before them: the plain proxies, placed and joined as ever
    insert_mesh = swap_bore = None

    def placed(part, place):
        return place(part)

    def fused(parts):
        out = None
        for p in parts:
            out = p if out is None else out.union(p)
        return out
from cadkit.board_geom import mask_rgb as _mask_rgb   # a board is a solder-mask colour (cadkit f715f57)

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
# THE YOKE'S M3s (user, 2026-11-12): HEADS ON THE KEYHOLE PLATE'S +X FACE, each shank -X
# through the plate, the printed spacer and the nut flange into a brass INSERT in the collar (the
# collar then needs no way in for a head, and prints with no bridge: the old heads behind it
# needed a bayonet and pockets nothing could print). The insert's +X end is flush on the flange's
# back face, so the string's pull runs plate -> screws -> insert -> brass flange with no plastic
# in it; the inserts only hold the collar on against the spring. So the screw's length sets the
# yoke, and the yoke sets the gap from the nut to the ball -- the one lever on travel (the screw
# tip may come up to the ball). M3 x 30 (McMaster 91292A022; user 2026-11-12: travel to spare),
# a different SKU from the bar clamp's (two SKUs, user 2026-11-12); the spacer is shortened so
# it bites KEY_M3_ENGAGE into the insert (user, 2026-11-12: shorten the yoke slightly).
KEY_M3_L = 30.0
COL_INS = (4.7, 4.3)                                # the insert: McMaster 94459A130 brass M3,
                                                    # OD over the knurl, installed length (as
                                                    # belt_tensioner's: measure one first)
COL_INS_HOLE = 4.0                                  # its heat-set pilot (the 3.9 pilot end drops
                                                    # in; 4.8 drop-in left 0.3 to the nut's bore)
KEY_M3_ENGAGE = COL_INS[1] - 0.3                    # 4.0 of thread in the insert
YK_H = KEY_M3_L - D.NUT_FLANGE_T - KEY_M3_ENGAGE    # 22.5: flange face -> plate's +X face
# THE KEYHOLE PLATE (user, 2026-11-12: a ball end on a 2.4 printed roof is ~8 mm^2 of plastic
# under the whole string, and the yoke's M3s threaded into plastic -- neither holds for years).
# The roof is now a LASER-CUT 304 PLATE, 4 mm, the nut plates' sheet (one JLCCNC order): the
# keyhole is cut in it and the yoke's two M3s pass through it (Ø3.4, heads on its +X face), so
# the string goes ball -> steel plate -> steel screws -> brass inserts -> nut, no thread in plastic. The printed yoke
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
# BOTH ends). A 3/16 in 304 stainless rod (McMaster 89535K84, 2 ft lengths cut in three: ROD_L),
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
# the plug's boss into the next plug). 2026-11-16 (the anchor collars to Ø24.7 for two beads
# round their clamp): the rod passes collar B, so it stands SPIN_GAP outside that swept circle
# (15.65). (335 was tried with the ties and put the rod into the next string's nut collar along
# the travel: 325 stays, the ties take the room instead.)
GUIDE_R, GUIDE_ANG = 15.65, 325.0                   # off the screw axis; deg from +Y toward +Z
GUIDE_ANG_1 = GUIDE_ANG                             # string 1: as the rest


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
# ...and its reach under / over the axis: its FLOOR level with the bottom of the keyhole's ball
# hole (user, 2026-11-12: a ball slid in along the floor drops straight into the pocket; a floor
# a ball's width lower ran it into the plate's steel under the hole)
WIN_Z = (-(KEY_DROP + KEY_D / 2), 3.2)
# THE SPRING (user, 2026-11-13: stainless, it lives inside the instrument for years): McMaster
# 9665K36 -- CUT-TO-LENGTH 302 STAINLESS, 0.75 in OD, 0.091 in wire, 20 in close-wound, straight
# cut ends; cut into SPRING_COILS whole-coil pieces (~5 a length, ~$6.40 each). 7.54 lbf (33.5 N)
# initial tension; 1.37 lbf/in for the 20 in length (~220 coils), so ~1.55 N/mm for 34 working
# coils -- ~10 % softer than the spring-steel 9654K335 it replaces (31.3 N, 1.72 N/mm at 35). Peak pull ~75 N: ~310 MPa
# in the wire (Wahl-corrected, C 7.2), well inside 302 spring wire's extension-spring allowable.
# A production spring is to be wound to a force-at-length drawing.
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
SPRING_ACTIVE = 34                                  # working coils between the grips (whole turns):
                                                    # 34, not 35, with the softer stainless -- at 35
                                                    # string 1's stretched spring overran its plug by 0.7
SPRING_IT = 7.54 * 4.448222                         # 33.5 N initial tension (9665K36)
SPRING_K = (1.37 * 4.448222 / 25.4) * (20.0 / (SPRING_WIRE / 25.4)) / SPRING_ACTIVE   # 1.55 N/mm
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
SPRING_COILS = SPRING_ACTIVE + 2 * GRIP_TURNS       # 42: the cut piece, ~97 free
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
# yield 205; a flat sheet: I ~360, ~215 MPa and 1.4 mm of sag -- the folds stay). The END FOLDS
# lie flat on the side walls and BEAR ON SCREW SHANKS (user, 2026-11-12, replacing the pins):
# ANCHOR_SCREW_N M4 button heads a side, put in from inside the EMPTY body before anything else
# (so no key has to reach past the springs, and nothing shows outside), each through the rail's
# inner skin and tapped into the A-36 bar, its head down on a SPACER BOSS printed with the body,
# as long as the fold is thick. The tray drops in from above between a printed REFERENCE RIB on each wall
# (at the web's -X face) and the screws (at the end folds' +X edges); the strings and springs pull
# it +X (~2 kN), the folds' edges onto the bare shanks beside each boss (its WINDOW), steel on
# steel into the bars. The heads keep the folds on the walls; the UI and the deck over it keep it
# from lifting when the strings are off.
ANCHOR_T = 4.0
ANCHOR = (-190.0 - DRIVE_DX - ANCHOR_T, -190.0 - DRIVE_DX)   # the plate's web, x
ANCHOR_Z = (None, -8.0)                             # its top at most (DECK_UNDER -3.2); _anchor_z
ANCHOR_FL = 16.0                                    # the top and bottom folds' depth, toward +X
ANCHOR_CLR = 0.5                                    # off the body's walls and floor, and under the UI
M4_HEAD = (7.6, 2.2)                                # ISO 7380 button head (the housing's bolts)
# THE SCREWS: ~2 kN over 2 x ANCHOR_SCREW_N = 250 N each, bending the shank over ~4.3 (the fold's
# middle off the bar's face, through the skin): ~350 MPa in the M4's core (Ø3.14), under the 18-8
# (A2-70) button heads' ~450 yield; three a side was ~470, at yield. M4 x 10, the stock length the
# instrument already buys 80 of: the spacer and the skin take 6.6, 3.4 (~5 turns) in the bar.
# The end folds' +X edge is the face that bears: a bent flange's length holds to ~+-0.3, so the web
# may sit that far off the rib -- the rib only squares it up as it goes in.
ANCHOR_SCREW_N, ANCHOR_SCREW_L = 4, 10.0
ANCHOR_SPACER_L = ANCHOR_CLR + ANCHOR_T + 0.3       # the fold's gap, thickness, and its slide
ANCHOR_SCREW_DX = ANCHOR_FL + 2.0                   # the shank's axis off the web's +X face
CB_BOSS = (-572.175, -28.5, -102.2)                 # the connector board's M4 boss: x, y, top (lead)
ANCHOR_RIB = (3 * D.BEAD, 10.0, 0.2)                # the reference rib: across x, out from the wall
                                                    # (past the bend's radius), its gap to the web
# THE COLLAR (user, 2026-11-12): SOLID from the nut flange back to its stop flange, as round as
# the flange (STOP_D), PRINTED +X -> -X, its +X face (on the flange) on the bed: two insert pockets
# up from that face, each under a 45 deg CONE ROOF, the stop flange's face and its detent teeth on
# top. Nothing overhangs. COLLAR_L is the length the plate and the old heads' room took, kept so
# the springs keep their lengths.
COLLAR_L = 3.0 + M3_HEAD[1] + 0.5                   # 6.5: flange's back face -> the stop flange

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
    """The collar along x: its +X face (on the nut flange's back), the stop flange (from, to),
    the seat (from, to) -- the seat runs -X from the flange, the spring's end on the flange."""
    pb = x_ft(t) - D.NUT_FLANGE_T                   # the nut flange's back face
    f1 = pb - COLLAR_L
    f0 = f1 - STOP_T
    return pb, (f0, f1), (f0 - SEAT_L, f0)


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
    free = x_collar(T_OPEN)[1][0] - SPRING_WIRE / 2 - (f0 + STOP_T + SPRING_WIRE / 2)
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
    return x_plug(i)[1][1] + SPRING_WIRE / 2, x_collar(t)[1][0] - SPRING_WIRE / 2


def spring_force(t: float, i: int) -> float:
    span = spring_span(t, i)
    return SPRING_IT + SPRING_K * (span[1] - span[0] - 2 * SEAT_GRIP - SPRING_ACTIVE * SPRING_WIRE)


# INSTALLING THE RODS (user, 2026-11-12: "we need a way to install the guide rods"). Each goes in
# LAST, from -X: through a hole in the anchor plate, the plug's boss (a through hole), the
# collar's slot, and home into its blind seat in the endplate, where three CRUSH RIBS grip its
# tip (ROD_GRIP: the only axial load is the tab's ~2 N of friction). So the endplate is on and
# screwed down first, and no rod has to find a hidden hole. Its -X end stands out of the plate's
# -X face into the housing's CAP (a blind pocket on a boss), for pliers to pull it.
# its +X end, deep in the endplate (user, 2026-11-13: "deepen the guide rod holes", 1.6 of
# plastic kept round them): with the endplate printed +X -> -X the axle bores peak -X and are
# round in z, so every rod passes 2.5+ over or under them; what stops the seat is the strings'
# slots (X_DROP - EP_STR_CLR, open the full height), which the rods of strings 4, 7 and 10 cross.
# The seat's floor ROD_SEAT_WALL short of them: ~24 of grip
ROD_SEAT_WALL = 1.6
EP_STR_CLR = 1.5                                    # the endplate's fill stands this far -X of the
                                                    # string's vertical drop (user: inset for clearance)
ROD_TIP = X_DROP - EP_STR_CLR - ROD_SEAT_WALL - 0.3
# THE SLOT'S ROOF (user, 2026-11-13): the slot's -X end is a 45 deg gable peaked -X (the build
# direction), SLOT_ROOF_CLR square off every gauge the instrument takes (the string's centre drops
# at X_DROP + g/2, round the bearing's OD). The rods beside it keep ROD_SEAT_WALL (asserted below,
# where rod_yz exists).
SLOT_ROOF_CLR = 1.0
SLOT_APEX_X = min(X_DROP + g / 2 - math.sqrt(2) * (g / 2 + SLOT_ROOF_CLR)
                  for g in tuple(D.STRING_GAUGE) + (D.STRING_GAUGE_MAX,))
# ITS LENGTH: a 2 ft stock length (McMaster 89535K84) cut in THREE EQUAL pieces, no offcut (user,
# 2026-11-13: "use the entire thing ... saves another cut"; the rod may be -5/+10 of 193.3).
# 609.6 / 3, less the two cuts' kerf (~1 each); the stock is cut long (+ tolerance), so a piece
# lands ROD_L .. a third (rod_l_max). Pushed home in its seat, the rest is -X: the housing's cap
ROD_STOCK, ROD_PIECES, ROD_KERF = 609.6, 3, 1.0
ROD_L = round((ROD_STOCK - (ROD_PIECES - 1) * ROD_KERF) / ROD_PIECES, 1)   # 202.5
ROD_END = ROD_TIP - ROD_L                           # every string the same
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

# THE THRUST HOUSING (user, 2026-11-09: "put the thrust bearings on the anchor"; one 688 since
# 2026-11-14; both collars clamped, 2026-11-15). Along -X from the anchor plate's -X face:
#   COLLAR B   threaded on the Tr8 and pinched by its M3, its boss on the inner race's +X face
#   HOUSING    over collar B from the plate WITHOUT TOUCHING IT (posts only round it), then its
#              LIP on the outer race's +X face, then the bearing's POCKET (open -X)
#   BEARING    the one 688
#   LID        on the outer race's -X face, shutting the bearing in
#   COLLAR A   the same part as B, turned end for end, its boss on the inner race's -X face
# Two M3 x 30 (the yoke's SKU) through the lid, the housing's posts and the plate into heat-set
# inserts in the plug clamp lid, housing, plate and plug together. The inner race is pinched
# between the collars' bosses, the outer race between the lip and the lid: with the spring and
# the motor off the screw cannot move along X at all.
#   strings on:  the screw pulls +X: collar A -> inner race -> outer race -> the lip -> the
#                housing's posts -> THE PLATE (compression). The plug's spring pull meets it in
#                the ties.
#   strings off: the spring pushes the screw -X: collar B -> inner race -> outer race -> the lid
#                -> the ties -> the plug, whose spring pull it is: the plate sees nothing.
# Either way the motor only turns the screw.
HOUSE_D = D.BRG688_OD + 3.2                         # 19.2: the pocket's 1.6 wall
# ONE 688 PER SCREW (user, 2026-11-14; it was a pair): the rated EZO part carries the 147 N a string
# pulls at 2.0x on its own (elec/prices.json bearing_688zz_screw, which always counted ten), and the
# motor's own bearings hold the screw's other end, so a second one only over-constrained it.
HOUSE_POCKET = D.BRG688_W                           # the one 688, pressed in from -X
# TURNING NEVER TOUCHES FIXED (user, 2026-11-14: "ideally the bearings handle all the contact"):
# every collar face stands SPIN_GAP off the plate, the lip and the lid, and every fixed thing
# SPIN_GAP outside the collars' swept circle -- the bearing's own axial play (~0.1) and a collar
# printed a little long both come out of it
SPIN_GAP = 0.8
# THE COLLARS ARE ONE PART (user, 2026-11-15: "both collars threaded and clamped with a screw";
# collar B was a jam nut in the plate's hole). The coupler's formed thread in the bore, split
# through on one side and pinched across the split by an M3 whose HEAD SITS INSIDE THE BODY,
# into a BRASS INSERT on the split's far side (user, 2026-11-16: no screws threaded into plastic,
# and two beads everywhere). Two 0.8 beads cannot be had at any size: its boss on the inner race
# is 0.9 at best (the race's land Ø10.4 round the thread's Ø8.6). It PRINTS ON THE 0.8 NOZZLE all
# the same (user, 2026-11-16: "spots between 1.6 and 0.8 thickness ... will likely print fine"),
# its walls 0.8 at least -- COLLAR_WALL round every hole sets the size: the clearance hole at the split, the head's pocket and the
# insert's keep 0.8 off the thread's crests and 0.8 inside the body, and the pockets leave through
# FLATS square to them (top and bottom), so no pocket runs out through the round at a slant and
# leaves a feathered edge -- Ø24.8 is the least that does (scratch: the clamp's 2-D layout).
COLLAR_WALL = 0.8                                   # the least wall (one 0.8 bead; the user's floor)
COLLAR_D, CLAMP_L = 24.8, 11.0                      # Ø, body length: the head's teardrop pocket
                                                    # (r 3, its peak r*sqrt2 along +X) two beads
                                                    # off both faces
COLLAR_SCREW = (6.78, 3.43)                         # the clamp M3's axis off the bore, its head's
                                                    # underside off the split's middle
COLLAR_INS_Z = 2.85                                 # the insert's top (its floor) under the split's
                                                    # middle; slid in from the bottom flat, it
                                                    # pulls up against that floor
# THE INSERT IS A NUT, NOT HEAT-SET (user, 2026-11-16: "a wider slot ... use them as a nut"): it slides
# into its pocket by hand and the clamp screw pulls it up against the pocket's floor, so it comes back
# out and goes in again as often as the collar does. Its pocket is a SNUG SLIDE sized as a round hole
# (the knurl's 4.7 + 0.8: the fit print's PETG-GF slide was +0.85 on 1/4", small holes shrink more),
# drawn as the sideways teardrop it is (cadkit holes fit=True: 0.4 smaller)
COL_INS_NUT = COL_INS[0] + 0.8                      # 5.5 round -> 5.1 drawn
COLLAR_SPLIT = 1.0                                  # the split's width
COLLAR_M3_L = 10.0                                  # M3 x 10: 4.0 of the insert's 4.3 of thread,
                                                    # its tip inside the insert
LIP_T = 4.0                                         # 5 beads: the lip spans its three posts under
                                                    # the strings' pull
LID_T = LIP_T                                       # the same, so both collars' bosses match
RACE_OUT_D = 13.6                                   # lip and lid holes: on the outer race only
RACE_IN_D = 10.4                                    # collar bosses: on the inner race only
# THE TIES (2-D packing of every string against its neighbours, 2026-11-15): the ties pass collar
# B, so they stand outside its swept circle, between the neighbours' collars. An M4 fits nowhere
# (best -1.8 mm, every pair of angles); an M3 with one bead round its shank fits at 23 / 300 deg,
# r 14.55: 1.05 to the nearest neighbour's collar, rod or ear (scratch ear_fast.py). 2026-11-16,
# the collars to Ø24.7: searched again with the rod's angle (scratch ear_pack2.py; the ties at
# least 90 apart so the lip is held on two sides; then inside the anchor tray's folds): 152 / 310 -- SPIN_GAP + 0.3 off its own
# collar B, 1.09+ clear of the neighbours, 1.6 + 0.35 of the plug between a tie's insert and the
# rod's seat.
# PER STRING (user, 2026-11-16: "the outer rim of drive trains would use slots on the outside
# perimeter"): one pattern for all ten left the inner strings boxed in, so each string has its own
# pair, the edge ones turned out to the free side. Searched together (scratch ear_per_string3.py,
# coordinate ascent + joint moves): every head SPIN_GAP outside every collar A, every spacer outside
# every collar B, the ears inside the anchor tray's folds, and the ears' rings (EAR_WALL) off every
# neighbour's ears, rods, housings and plugs, and inside the body's ribs behind the plate (the
# spacers: y -81.7..56.0) and its walls. The worst is strings 4, 7 and 8's plug: 1.07 between a
# tie's insert and the rod's seat (scratch ear_per_string5.py). (a1, a2, r)
TIES = {0: (152.0, 282.0, 16.15), 1: (152.0, 350.0, 16.45), 2: (32.0, 302.0, 16.35),
        3: (304.0, 150.0, 16.45), 4: (152.0, 282.0, 16.45), 5: (152.0, 302.0, 16.45),
        6: (304.0, 150.0, 16.45), 7: (304.0, 138.0, 16.45), 8: (104.0, 194.0, 16.45),
        9: (152.0, 242.0, 16.45)}
# the ears' walls round a tie's hole or insert: 1.2 (user, 2026-11-16: "spots between 1.6 and 0.8
# will likely print fine"), which is what lets the rings pass their neighbours
EAR_WALL = 1.2


def ear_ang(i: int) -> tuple:
    return TIES[i][:2]


def ear_r(i: int) -> float:
    return TIES[i][2]


def tie_offsets(i: int) -> list:
    """String i's two ties, (dy, dz) off its axis."""
    return [at_ang(a, ear_r(i)) for a in ear_ang(i)]
TIE_L = 35.0                                        # M3 x 35 (2026-11-16: heads on the lid's face,
                                                    # the 13 spacers): the insert's whole 4.3
TIE_BOSS = 3.4 / 2 + EAR_WALL                       # the lip's and lid's bosses round the ties
# THE TIES' SPACERS (user, 2026-11-16): past collar B the housing has no room for a two-bead
# wall round a tie (one bead left 1.05 to the next string's collar), so each tie runs through a
# ALUMINIUM ROUND SPACER, OD 4.5 / ID 3.2, 13 long (for M3; McMaster 94669A107, $0.65; 11 and 12
# are $1.77, 18-8 $1.80+), standing from the lip to the plate --
# the strings' pull goes lip -> spacers -> plate. Its stock length sets the room collar B
# turns in.
TIE_SPACER = (4.5, 3.2, 13.0)                       # OD, ID, length
PLATE_HOLE_D = 10.0                                 # the plate's hole: the screw only
NEMA17_HOLES = 31.0                                 # the faceplate's M3 square
SLOT_STATIONS = (0,)                                # the +X-most motors: oversized (slotted) holes


def x_brg():
    """The bearing, x from..to."""
    x1 = ANCHOR[0] - TIE_SPACER[2] - LIP_T
    return x1 - D.BRG688_W, x1


def x_lip():
    b1 = x_brg()[1]
    return b1, b1 + LIP_T


def x_lid():
    b0 = x_brg()[0]
    return b0 - LID_T, b0


def x_house():
    """The housing, x from..to: the pocket's mouth (the bearing's -X face) to the lip's +X face
    (the spacers stand from there to the plate)."""
    return x_brg()[0], x_lip()[1]


def x_collar_b():
    """Collar B: (body from, body to), and its boss's end (the bearing's +X face). SPIN_GAP off
    the lip (so its boss is collar A's: one part); the spacers' spare length is off the plate."""
    c0 = x_lip()[1] + SPIN_GAP
    return (c0, c0 + CLAMP_L), x_brg()[1]


def x_collar_a():
    """Collar A: (body from, body to), and its boss's end (the bearing's -X face)."""
    body1 = x_lid()[0] - SPIN_GAP
    return (body1 - CLAMP_L, body1), x_brg()[0]


PLATE_T = 4.0
STATION_GAP = 1.3
STATION_P = M_BACK + CPL_X[1] + STATION_GAP         # 77.0: no bearing block any more
# THE NEAREST STATION'S COUPLER IS ITS COLLAR A (user, 2026-11-15): the coupler already grips the
# screw as collar A does (the formed thread, pinched by its C clamp) and takes a boss on a 688's
# inner race (motor_coupler.coupler's boss_l, as the plank bench's X rig). On station 0 its +X face
# stands where collar A's would, its boss through the lid onto the race; so its X is set by the
# bearing, not the motor -- the shaft sits CPL_SLACK short of the D's stop and the screw's end
# CPL_SLACK further in, so the motor plate's place along X is free that much either way. With
# the motor pulled, the coupler stays pinched on the screw: still locked in X.
CPL_SLACK = 1.0
X_REF0 = x_collar_a()[0][1] - CPL_X[1] - CPL_SLACK  # station 0's pulley plane


def coupler_is_collar(i: int) -> bool:
    return STATION[i] == 0

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


YOKE_UP = (1.0, 0.0, 0.0)                           # prints -X -> +X: the face on the nut's flange on
                                                    # the bed, the plate's face last (user, 2026-11-14)


def _yoke(i: int, t: float) -> cq.Workplane:
    """Printed YOKE_UP. The lip register steps in to the bore on a 45 deg cone, not a flat ring."""
    y, z = y_of(i), za(i)
    ft, yt = x_ft(t), x_yt(t)
    out = cyl_x(YK_D, YK_H - YK_ROOF, ft, y=y, z=z)                                 # the spacer
    out = out.cut(cyl_x(D.SCREW_OD + 0.8, yt - YK_ROOF - ft + 1, ft - 1, y=y, z=z))   # tip + ball
    out = out.cut(cyl_x(D.NUT_LIP_D + 0.4, D.NUT_LIP_L + 1.3, ft - 1, y=y, z=z))      # lip register
    rl, rb = (D.NUT_LIP_D + 0.4) / 2, (D.SCREW_OD + 0.8) / 2                          # ... its roof
    xl = ft + D.NUT_LIP_L + 0.3
    out = out.cut(_cone_x(rl, rb - 0.01, xl - 0.01, xl + rl - rb, y, z))
    ry, rz = rod_yz(i)
    out = out.cut(cyl_x(GUIDE_D + 2.0, YK_H + 2, ft - 1, y=ry, z=rz))                 # rod: clear
    for a in HOLE_ANG["m3"]:                                                          # the M3s bite
        dy, dz = at_ang(a)
        out = out.cut(cyl_x(3.4, YK_H + 2, ft - 1, y=y + dy, z=z + dz))           # clear
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
    end on the axis, and the yoke's two M3 clearance holes (Ø3.4: the heads sit on its +X face)."""
    w = cyl_x(YK_D, YK_ROOF, -YK_ROOF, y=0, z=0)
    w = w.cut(cyl_x(KEY_D, YK_ROOF + 2, -YK_ROOF - 1, y=0, z=-KEY_DROP))
    w = w.cut(box_at(YK_ROOF + 2, SLIT_W, KEY_DROP, x=-YK_ROOF / 2, y=0, z=-KEY_DROP / 2))
    w = w.cut(cyl_x(SLIT_W, YK_ROOF + 2, -YK_ROOF - 1, y=0, z=0))
    for a in HOLE_ANG["m3"]:
        dy, dz = at_ang(a)
        w = w.cut(cyl_x(3.4, YK_ROOF + 2, -YK_ROOF - 1, y=dy, z=dz))
    return w


def rod_yz(i: int):
    dy, dz = at_ang(guide_ang(i), GUIDE_R)
    return y_of(i) + dy, za(i) + dz


def _radial_box(i: int, x0: float, x1: float, r0: float, r1: float, w: float) -> cq.Workplane:
    """A box x0..x1, from radius r0 to r1 off string i's axis toward its guide rod, w wide."""
    return _radial_box_at(i, x0, x1, r0, r1, w, guide_ang(i))


def _radial_box_at(i: int, x0: float, x1: float, r0: float, r1: float, w: float,
                   a: float) -> cq.Workplane:
    """A box x0..x1, from radius r0 to r1 off string i's axis toward angle a, w wide."""
    b = box_at(x1 - x0, w, r1 - r0, x=(x0 + x1) / 2, y=0, z=(r0 + r1) / 2)        # along +Z ...
    return b.rotate((0, 0, 0), (1, 0, 0), a - 90).translate((0, y_of(i), za(i)))


def _collar(i: int, t: float) -> cq.Workplane:
    y, z = y_of(i), za(i)
    pb, (f0, f1), (s0, s1) = x_collar(t)
    out = cyl_x(STOP_D, pb - f0, f0, y=y, z=z)                                      # solid
    x0, x1 = spring_span(t, i)                                                      # the post:
    out = out.union(_post(i, x0, x1 - x0 - SEAT_GRIP, D.NUT_BOSS_D + 0.4))          # threaded
    out = out.cut(cyl_x(D.NUT_BOSS_D + 0.4, 60, s0 - 1, y=y, z=z))                  # boss, screw
    out = out.union(_tube_x(13.0, SCREW_CLR, s0, s0 + 3.0, y, z))                   # post's floor
    # the detent's teeth (sunk 0.02 into the flange and 0.02 inside its rim: fused flush with
    # both, the solid came back invalid)
    zf = x1 - x0 + SPRING_WIRE / 2
    teeth = (_teeth(zf, -1, 1).translate((0, 0, 0.02))
             .intersect(_ring(DET_R0, SLEEVE_OD / 2 - 0.02, zf - DET_H - 1, zf + 1)))
    out = out.union(_in_spring(teeth, i, x0))
    # THE INSERTS' POCKETS: up from the +X face (the bed), the insert's length and 0.3, under a
    # 45 deg cone roof -- a hole printed along the build, so round, and no ceiling
    d, h = COL_INS_HOLE, COL_INS[1] + 0.3
    for a in HOLE_ANG["m3"]:
        dy, dz = at_ang(a)
        out = out.cut(cyl_x(d, h + 1, pb - h, y=y + dy, z=z + dz))
        out = out.cut(cq.Workplane("XY").add(cq.Solid.makeCone(
            d / 2, 0.0, d / 2, cq.Vector(pb - h + 0.01, y + dy, z + dz), cq.Vector(-1, 0, 0))))
    # the TAB: from the +X face out past the rod, TAB_L along x, and its RADIAL SLOT. Its outer
    # end is ROUND, concentric with the slot's (user, 2026-11-12: the square corners came close to
    # the next string's spring): GUIDE_WALL all round the slot
    w = GUIDE_SLOT + 2 * GUIDE_WALL
    lo, hi = GUIDE_R - GUIDE_FLOAT, GUIDE_R + GUIDE_FLOAT
    out = out.union(_radial_box(i, pb - TAB_L, pb, D.NUT_FLANGE_L / 2 - 2.0, hi, w))
    dy, dz = at_ang(guide_ang(i), hi)
    out = out.union(cyl_x(w, TAB_L, pb - TAB_L, y=y + dy, z=z + dz))
    out = out.cut(_radial_box(i, pb - TAB_L - 1, pb + 1, lo, hi, GUIDE_SLOT))
    for r in (lo, hi):                                                              # round ends
        dy, dz = at_ang(guide_ang(i), r)
        out = out.cut(cyl_x(GUIDE_SLOT, TAB_L + 2, pb - TAB_L - 1, y=y + dy, z=z + dz))
    return out


def _collar_inserts(i: int, t: float) -> cq.Workplane:
    """The two brass inserts, their +X ends flush with the collar's face (on the nut flange)."""
    y, z = y_of(i), za(i)
    pb = x_collar(t)[0]
    return fused([_insert_x(pb, -1, y + dy, z + dz) for dy, dz in (at_ang(a) for a in HOLE_ANG["m3"])])


def _insert_x(mouth: float, sense: int, y: float, z: float, axis: str = "x") -> cq.Workplane:
    """An M3 heat-set insert (COL_INS) along X, its mouth at x = `mouth`, running `sense` (+1/-1)
    into the part; axis="z": upright, the mouth at z = `mouth` and the insert below it. The proxy
    is the tube the gate always checked; the look the knurl and the thread (cadkit.mesh_parts)."""
    od, l = COL_INS
    if axis == "z":
        x0, x1 = mouth - l, mouth
        proxy = cq.Workplane("XY").add(cq.Solid.makeCylinder(od / 2, l, cq.Vector(y[0], y[1], x0)))
        proxy = proxy.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(1.25, l + 2, cq.Vector(y[0], y[1], x0 - 1))))
        place = lambda w: w.translate((y[0], y[1], mouth))                   # noqa: E731
    else:
        x0, x1 = (mouth - l, mouth) if sense < 0 else (mouth, mouth + l)
        proxy = _tube_x(od, 2.5, x0, x1, y, z)
        # the insert's own frame: top at z = 0, down -Z -> the mouth, running `sense` along X
        place = lambda w: w.rotate((0, 0, 0), (0, 1, 0), 90 if sense < 0 else -90).translate((mouth, y, z))  # noqa: E731
    if insert_mesh is None:
        return proxy
    return with_mesh(proxy, insert_mesh(3.0, 0.5, od, l), affine_of(place))


def _m3s(i: int, t: float) -> cq.Workplane:
    y, z = y_of(i), za(i)
    # heads on the keyhole plate's +X face, into the collar's inserts (KEY_M3_ENGAGE)
    return fused([_cap("m3", KEY_M3_L, (x_yt(t) + M3_HEAD[1], y + dy, z + dz), (-1, 0, 0))
                  for dy, dz in (at_ang(a) for a in HOLE_ANG["m3"])])


def _cap(kind: str, length: float, top, shank_dir) -> cq.Workplane:
    from .motor_coupler import cap_screw
    return cap_screw(kind, length, top, shank_dir)


COILS = True                                        # (unused since the screw and spring are mesh-only parts, 2026-11-15)


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
    """The leadscrew from x0 to x1 along +X: the instrument's Tr8x2 rod, a MESH-ONLY PART
    (cadkit.mesh_parts, 2026-11-15): its solid is the plain Ø8 cylinder its crests ride on -- what
    the gate, the bounding boxes and the STEP see -- and its look the thread drawn in closed form
    (milliseconds, any length). It was OCCT's helix cut: minutes a screw, and empty or ringed at
    some lengths (187 mm, 2026-11-15)."""
    from . import components as C
    y, z = y_of(i), za(i)
    proxy = cyl_x(D.SCREW_OD, x1 - x0, x0, y=y, z=z)
    try:
        from cadkit.mesh_parts import threaded_rod_mesh, with_mesh, affine_of
    except ImportError:                             # vendored cadkit before 4e2a993: the plain rod
        return proxy
    m = threaded_rod_mesh(x1 - x0, D.SCREW_OD, C._TR_ROOT_D, D.SCREW_PITCH, hand=D.SCREW_HAND)
    return with_mesh(proxy, m, affine_of(lambda w: w.rotate((0, 0, 0), (0, 1, 0), 90)
                                         .translate((x0, y, z))))


def _spring(i: int, t: float) -> cq.Workplane:
    """A MESH-ONLY PART (cadkit.mesh_parts, 2026-11-15): its solid is the tube OD..ID the gate
    always checked; its look the wire on its helix -- grip coils, the stretched working coils,
    grip coils -- drawn in closed form instead of three OCCT sweeps."""
    x0, x1 = spring_span(t, i)
    proxy = _tube_x(SPRING_OD, SPRING_ID, x0, x1, y_of(i), za(i))
    try:
        from cadkit.mesh_parts import coil_mesh, with_mesh, affine_of
    except ImportError:                             # vendored cadkit before 4e2a993: the tube
        return proxy
    L = x1 - x0
    act = L - 2 * SEAT_GRIP
    k = SPRING_ACTIVE                               # whole turns: every piece starts at angle 0
    assert act > k * SPRING_WIRE, "the working coils solid"
    m = coil_mesh([(0.0, GRIP_PITCH, SEAT_GRIP), (SEAT_GRIP, act / k, act),
                   (SEAT_GRIP + act, GRIP_PITCH, SEAT_GRIP)], R_COIL, SPRING_WIRE)
    return with_mesh(proxy, m, affine_of(lambda w: _in_spring(w, i, x0)))


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


def _sleeve_local(zf: float, s: int, z_far: float, z0: float, tighten: int,
                  up=None) -> cq.Workplane:
    """The grip sleeve in the spring's frame: from the flange face zf (its end on the teeth)
    toward s to z_far, bore SLEEVE_CLR off the post, the grip coils' groove (helix from z0, as
    the post's), the teeth's complement on its end, and the key's cross-hole."""
    ri, ro = R_COIL + SLEEVE_CLR, SLEEVE_OD / 2
    body = _ring(ri, ro, zf + s * DET_H, z_far)
    band = _ring(DET_R0, ro, zf, zf + s * DET_H).cut(_teeth(zf, s, tighten))
    body = body.union(band)
    body = body.cut(_helix(z0, GRIP_PITCH, SEAT_L, GROOVE_D))
    zk = (zf + z_far) / 2                                    # the key's cross-hole, through
    if up is not None:                                       # (a teardrop, peaked up the print)
        from cadkit.holes import teardrop_hole
        key = teardrop_hole(SLEEVE_KEY, 2 * ro + 2, axis_point=(0, -ro - 1, zk), axis_dir=(0, 1, 0),
                            print_up=up)
    else:
        key = cq.Workplane("XY").add(cq.Solid.makeCylinder(SLEEVE_KEY / 2, 2 * ro + 2,
                                                           cq.Vector(0, -ro - 1, zk), cq.Vector(0, 1, 0)))
    return body.cut(key)


SLEEVE_P_UP = (-1.0, 0.0, 0.0)                      # world: +X -> -X
SLEEVE_P_UP_LOCAL = (0.0, 0.0, -1.0)                # the same, in the spring's frame
SLEEVE_C_UP = (1.0, 0.0, 0.0)                       # world: -X -> +X
SLEEVE_C_UP_LOCAL = (0.0, 0.0, 1.0)


def _sleeve_plug(i: int) -> cq.Workplane:
    """The plug end's sleeve: flange face at local -wire/2, over the post to its end. Tightening
    runs it toward -z: with a right-hand helix that is -angle."""
    zf = -SPRING_WIRE / 2
    # PRINTS +X -> -X (user, 2026-11-14): its far end on the bed, the teeth last. Local +z is world
    # +X here (_in_spring), so up the print is local -z
    return _in_spring(_sleeve_local(zf, 1, SEAT_L - GRIP_PITCH / 2, 0.0, -1, up=SLEEVE_P_UP_LOCAL), i,
                      spring_span(0.0, i)[0])


def _sleeve_collar(i: int, t: float) -> cq.Workplane:
    """The collar end's: flange face at local L + wire/2, back over the post. It tightens +z."""
    x0, x1 = spring_span(t, i)
    L = x1 - x0
    zf = L + SPRING_WIRE / 2
    # PRINTS -X -> +X (user, 2026-11-14): its far end on the bed, the teeth last; up = local +z
    return _in_spring(_sleeve_local(zf, -1, L - SEAT_L + GRIP_PITCH / 2, L - SEAT_GRIP, 1,
                                    up=SLEEVE_C_UP_LOCAL), i, x0)


PLUG_UP = (1.0, 0.0, 0.0)                           # prints -X -> +X: the neck's end on the bed,
                                                    # the teeth last (user, 2026-11-14)


def _cone_x(r0: float, r1: float, x0: float, x1: float, y: float, z: float) -> cq.Workplane:
    """A frustum along +X from radius r0 at x0 to r1 at x1."""
    return cq.Workplane("XY").add(cq.Solid.makeCone(r0, r1, x1 - x0, pnt=cq.Vector(x0, y, z),
                                                    dir=cq.Vector(1, 0, 0)))


def _anchor_plug(i: int) -> cq.Workplane:
    """Printed -X -> +X (PLUG_UP). Every step out in radius going +X is a 45 deg cone (user,
    2026-11-14): under the stop flange, and from each insert's pocket down to its screw's hole; and
    the screws' holes run right out through the teeth, which would otherwise hang over them."""
    y, z = y_of(i), za(i)
    (a0, a1), (f0, f1), (s0, s1) = x_plug(i)
    out = cyl_x(SPRING_ID, f0 - a0, a0, y=y, z=z)                                   # neck
    out = out.union(cyl_x(STOP_D, f1 - f0, f0, y=y, z=z))                           # stop flange
    rise = (STOP_D - SPRING_ID) / 2                                                 # ... on a cone
    out = out.union(_cone_x(SPRING_ID / 2, STOP_D / 2, f0 - rise, f0 + 0.01, y, z))
    out = out.union(_ears(i, a0, f1, COL_INS_HOLE / 2 + EAR_WALL))                    # the inserts'
    out = out.cut(cyl_x(SCREW_CLR, s1 - a0 + 2, a0 - 1, y=y, z=z))                 # the screw's way
    ins_d, ins_l, tip_d = COL_INS_HOLE, COL_INS[1] + 0.3, 3.4     # the ties' M3 inserts
    for dy, dz in tie_offsets(i):
        out = out.cut(cyl_x(ins_d, ins_l + 1.0, a0 - 1, y=y + dy, z=z + dz))           # insert
        out = out.cut(_cone_x(ins_d / 2, tip_d / 2 - 0.01, a0 + ins_l - 0.01,
                              a0 + ins_l + (ins_d - tip_d) / 2, y + dy, z + dz))    # ... its floor
    out = out.union(_post(i, spring_span(0.0, i)[0], 0.0, SCREW_CLR))               # threaded post
    # the guide rod's -X SEAT: a boss at GUIDE_R on the plate, its web back to the neck, and a
    # hole right through it: the rod slides in from -X through the plate (ROD_END)
    dy, dz = at_ang(guide_ang(i), GUIDE_R)
    out = out.union(cyl_x(GUIDE_SEAT + 2 * GUIDE_WALL, f1 - a0, a0, y=y + dy, z=z + dz))
    out = out.union(_radial_box(i, a0, f1, SPRING_ID / 2 - 1.0, GUIDE_R, GUIDE_SEAT + 2 * GUIDE_WALL))
    out = out.cut(cyl_x(GUIDE_SEAT, f1 - a0 + 2, a0 - 1, y=y + dy, z=z + dz))
    out = out.union(_in_spring(_teeth(-SPRING_WIRE / 2, 1, -1), i, spring_span(0.0, i)[0]))
    x_end = out.val().BoundingBox().xmax
    for dy, dz in tie_offsets(i):  # the tips' way, out through all
        out = out.cut(cyl_x(tip_d, x_end + 1 - (a0 + ins_l), a0 + ins_l, y=y + dy, z=z + dz))
    return out


def _ears(i: int, x0: float, x1: float, hw: float) -> cq.Workplane:
    """String i's two ears (ear_ang): a web from the axis out to a boss round ear_r, x0..x1."""
    y, z = y_of(i), za(i)
    out = None
    er = ear_r(i)
    for a in ear_ang(i):
        e = box_at(x1 - x0, 2 * hw, er, x=(x0 + x1) / 2, y=0, z=er / 2)         # along +Z ...
        e = e.union(cyl_x(2 * hw, x1 - x0, x0, y=0, z=er))
        e = e.rotate((0, 0, 0), (1, 0, 0), a - 90).translate((0, y, z))        # ... turned to a
        out = e if out is None else out.union(e)
    return out


def rod_cap_x() -> tuple:
    """The rod's cap: the LIP'S +X FACE (2026-11-16: the 13 long spacers put the lip past the
    rod's end, so no pocket -- the rod's -X end floats over collar B and stops on the lip).
    (floor, floor)"""
    xp = x_lip()[1]
    assert xp < ROD_END, "the rod's end runs into the lip"
    assert ROD_END - xp <= 3.0, "the rod floats too far before the lip stops it"
    return xp, xp


def rod_l_max() -> float:
    """The longest rod the cap takes, pushed home in its seat: a stock third has to fit."""
    m = ROD_TIP - rod_cap_x()[1] - 0.3
    assert m >= ROD_STOCK / ROD_PIECES - 0.01, (m, "a third of the stock no longer fits the cap")
    return m


HOUSE_UP = (1.0, 0.0, 0.0)                          # prints -X -> +X: the pocket's mouth on the bed,
                                                    # the lip a 1.2 ledge over it, the rod's
                                                    # pocket open on top
LID_UP = (-1.0, 0.0, 0.0)                           # prints +X -> -X: the heads' pockets open on top


def _sweep_cut(x0: float, x1: float, i: int) -> cq.Workplane:
    """Everything fixed stands SPIN_GAP outside a collar's swept circle over x0..x1."""
    return cyl_x(COLLAR_D + 2 * SPIN_GAP, x1 - x0, x0, y=y_of(i), z=za(i))


def _housing(i: int) -> cq.Workplane:
    """The bearing's pocket and the lip: a Ø19.2 with webs out to the ties and to the guide rod,
    whose cap the lip's +X face is (2026-11-16: no pocket; the rod floats up to it, rod_cap_x). NOTHING past the lip (user,
    2026-11-16): the ties' steel spacers carry the lip to the plate, and the rod runs bare past
    collar B (~2 clear; the plug and the plate hold it -- a post round it there left 0.87 of wall
    on the collar's side, and the spacer at 300 deg cut into it)."""
    y, z = y_of(i), za(i)
    h0, _ = x_house()
    l0, l1 = x_lip()
    rb = GUIDE_SEAT / 2 + GUIDE_WALL
    out = cyl_x(HOUSE_D, l1 - h0, h0, y=y, z=z).union(_ears(i, h0, l1, TIE_BOSS))
    out = out.union(_radial_box(i, h0, l1, 0.0, GUIDE_R, 2 * rb))
    dy, dz = at_ang(guide_ang(i), GUIDE_R)
    out = out.union(cyl_x(2 * rb, l1 - h0, h0, y=y + dy, z=z + dz))
    out = out.cut(cyl_x(D.BRG688_OD, l0 + 0.01 - (h0 - 1), h0 - 1, y=y, z=z))  # the pocket, open -X
    out = out.cut(cyl_x(RACE_OUT_D, l1 - l0 + 2, l0 - 1, y=y, z=z))            # the lip's hole
    rod_l_max()                                                                 # a third still fits
    for dy, dz in tie_offsets(i):
        out = out.cut(cyl_x(3.4, l1 - h0 + 2, h0 - 1, y=y + dy, z=z + dz))
    return _housing_label(out, i, h0, l1, rb)


LABEL_PROUD = 0.5                                   # the string's number, raised (version_mark)
LABEL_INSET = 0.4                                   # off the face's ends


def _housing_label(out: cq.Workplane, i: int, h0: float, l1: float, rb: float) -> cq.Workplane:
    """"S<n>" raised on a SIDE of the web out to the guide rod (user, 2026-11-16: the housings
    are per string now, so each carries its string; the Rennie Mackintosh face of the boards
    and the display). The -X face is the bed and the +X face the rod's cap and collar B's
    face, so a side: the one turned away from the nearer tie, flat from where it leaves the
    Ø19.2 to where it meets the rod's boss, figures as tall as that run allows reading along X
    (the housing's 9), raised, not cut -- its strokes are under a bead. No wall is touched."""
    from .version_mark import raise_mark, emboss_mark
    g = math.radians(guide_ang(i))
    u = (math.cos(g), math.sin(g))                                  # out along the web, (y, z)
    n = (-math.sin(g), math.cos(g))                                 # across it
    a = min(ear_ang(i), key=lambda a: abs((a - guide_ang(i) + 180) % 360 - 180))
    s = -1.0 if math.sin(math.radians(a) - g) > 0 else 1.0          # away from the nearer tie
    r0 = math.sqrt((HOUSE_D / 2) ** 2 - rb ** 2) + LABEL_INSET      # the flat run along u
    r1 = GUIDE_R - LABEL_INSET
    length = l1 - h0 - 2 * LABEL_INSET
    text = f"S{i + 1}"
    m = emboss_mark(text, 1.0, LABEL_PROUD)                         # its size per unit figure
    if m is None:
        return out
    bb = m.val().BoundingBox()
    h = min((r1 - r0) / bb.ylen, length / bb.xlen)                  # as tall as the face allows
    rc = (r0 + r1) / 2
    at = ((h0 + l1) / 2, y_of(i) + rc * u[0] + s * rb * n[0], za(i) + rc * u[1] + s * rb * n[1])
    return raise_mark(out, text, at, (0.0, s * n[0], s * n[1]), (1.0, 0.0, 0.0), h, LABEL_PROUD)


def _tie_spacers(i: int) -> cq.Workplane:
    """The two aluminium spacers, lip to plate, round the ties."""
    od, idd, L = TIE_SPACER
    x1 = ANCHOR[0]
    assert abs(x1 - L - x_lip()[1]) < 1e-6
    return fused([_tube_x(od, idd, x1 - L, x1, y_of(i) + dy, za(i) + dz) for dy, dz in tie_offsets(i)])


def _lid(i: int) -> cq.Workplane:
    """On the outer race's -X face: the ties' heads sunk in it, collar A's boss through its hole."""
    y, z = y_of(i), za(i)
    d0, d1 = x_lid()
    out = cyl_x(HOUSE_D, d1 - d0, d0, y=y, z=z).union(_ears(i, d0, d1, TIE_BOSS))
    out = out.cut(cyl_x(RACE_OUT_D, d1 - d0 + 2, d0 - 1, y=y, z=z))
    for dy, dz in tie_offsets(i):  # the ties' heads on its -X face (not sunk)
        out = out.cut(cyl_x(3.4, d1 - d0 + 2, d0 - 1, y=y + dy, z=z + dz))
    return out


def _housing_bolts(i: int) -> cq.Workplane:
    """The two ties: M3 x 30, heads sunk in the lid, through the housing's posts and the plate
    into the plug's inserts."""
    y, z = y_of(i), za(i)
    hu = x_lid()[0]                                 # the heads' underside: on the lid's -X face
    return fused([_cap("m3", TIE_L, (hu - M3_HEAD[1], y + dy, z + dz), (1, 0, 0))
                  for dy, dz in tie_offsets(i)])


def _inserts(i: int) -> cq.Workplane:
    """The plug's two M3 heat-set inserts (the collar's: COL_INS), flush in its -X face."""
    y, z = y_of(i), za(i)
    return fused([_insert_x(ANCHOR[1], +1, y + dy, z + dz) for dy, dz in tie_offsets(i)])


COLLAR_A_UP = (1.0, 0.0, 0.0)                       # prints -X -> +X: its -X face on the bed, the
                                                    # boss last (user, 2026-11-14)
COLLAR_B_UP = (-1.0, 0.0, 0.0)                      # the same part turned end for end: the same print


def collar_screw_x() -> float:
    """The clamp screw's axis along the collar, from its body's -X face (collar A's frame): the
    head's teardrop pocket (r, peaked r*sqrt2 along +X) centred, so both faces keep their wall."""
    hp = (M3_HEAD[0] + 0.5) / 2
    return (CLAMP_L + hp - hp * math.sqrt(2)) / 2


def _collar_screw_xw(which: str) -> float:
    """The same, in the world: collar B is A turned end for end, so it measures from its +X end."""
    (c0, c1), _ = x_collar_a() if which == "a" else x_collar_b()
    return c0 + collar_screw_x() if which == "a" else c1 - collar_screw_x()


def _collar_local(boss_l: float = SPIN_GAP + LID_T, shaft: float = 0.0, body_l: float = CLAMP_L,
                  screw_x: float = None, grip: float = 0.0) -> cq.Workplane:
    """THE COLLAR, along +X from 0: the body 0..CLAMP_L, the boss (`boss_l`) on to the race; split
    on +Y from the bore right out (body AND boss: a boss left whole is a closed ring round the
    thread and the screw could not pinch it), pinched by an M3 from +Z whose head sits inside the
    body. THE BORE IS THE COUPLER'S FORMED THREAD (user, 2026-11-14: "so it grips better").
    `shaft` > 0: THE COUPLER (user, 2026-11-16: "the same design as the collar except with an extra
    section for the motor shaft"): a Ø CPL_D section `shaft` long on -X, the body `body_l` long with
    its screw at `screw_x`, the motor's D bore from the coupler's end to `grip` and the thread on
    from there; the split and the flats run on through it all."""
    from cadkit.holes import teardrop_hole
    from .motor_coupler import _thread_socket
    from .motor_coupler import FORM_MAJOR_C
    L, Lb = body_l, boss_l
    out = cyl_x(COLLAR_D, L, 0.0)
    if Lb > 0:
        out = out.union(cyl_x(RACE_IN_D, Lb, L))
    if shaft > 0:
        out = out.union(cyl_x(CPL_D, shaft, -shaft))
        # the step out to the clamp body a 45 deg cone, not a shelf: the coupler prints standing on
        # its motor end, and a flat step there is a 3.4 ceiling over air
        ch = (COLLAR_D - CPL_D) / 2
        assert ch <= shaft + 1e-9, "the cone runs past the shaft section"
        out = out.union(cq.Workplane("XY").add(cq.Solid.makeCone(
            CPL_D / 2, COLLAR_D / 2, ch, cq.Vector(-ch, 0, 0), cq.Vector(1, 0, 0))))
    out = out.cut(box_at(L + Lb + shaft + 2, COLLAR_D / 2 + 1.0, COLLAR_SPLIT,
                         x=(L + Lb - shaft) / 2, y=(COLLAR_D / 2 + 1.0) / 2, z=0.0))
    sy, sz = COLLAR_SCREW
    zi, (ins_od, ins_l) = COLLAR_INS_Z, COL_INS
    # COLLAR_WALL ROUND EVERY HOLE: the cross-section's corners nearest the thread's
    # crests, and round the head's pocket and the insert out to the round, up to the flats
    w, R = COLLAR_WALL, COLLAR_D / 2
    wall = FORM_MAJOR_C / 2 + w
    hp = (M3_HEAD[0] + 0.5) / 2
    hs = COLLAR_SPLIT / 2
    from cadkit.holes import as_printed_d
    ri = as_printed_d(COL_INS_NUT, (0, 0, 1), COLLAR_A_UP) / 2     # the insert's pocket, as drawn
    z_top, z_bot = sz + M3_HEAD[1], -(zi + ins_l)                 # the flats: the head's top and
                                                                  # the insert's end flush
    assert math.hypot(sy - 1.7, hs) >= wall - 1e-6, "the clearance hole at the split"
    assert math.hypot(sy - hp, sz) >= wall - 1e-6, "the head's pocket"
    assert math.hypot(sy - ri, zi) >= wall - 1e-6, "the insert's pocket"
    assert sz - hs >= w and zi - hs >= w, "over and under the split"
    assert z_top - FORM_MAJOR_C / 2 >= w and -z_bot - FORM_MAJOR_C / 2 >= w, "the flats off the bore"
    assert math.hypot(sy + hp + w, z_top) <= R + 1e-6, "round the head's pocket, to its flat"
    assert math.hypot(sy + ri + w, -z_bot) <= R + 1e-6, "round the insert, to its flat"
    eng = COLLAR_M3_L - (sz + zi)
    assert 3.5 <= eng <= ins_l, (eng, "the screw's thread in the insert, its tip inside it")
    for zc, up in ((z_top, 1), (z_bot, -1)):                      # the flats, the body's whole length
        out = out.cut(box_at(L + shaft + 2, COLLAR_D + 2, R, x=(L - shaft) / 2, y=0.0,
                             z=zc + up * R / 2))
    # the head's pocket is a teardrop peaked +X (the print's up): it reaches r on -X and r*sqrt2
    # on +X, so centre THAT envelope, and both faces keep two beads
    xm = collar_screw_x() if screw_x is None else screw_x
    assert min(xm - hp, L - xm - hp * math.sqrt(2)) >= w - 1e-9, "the head's pocket walls"
    assert min(xm - ri, L - xm - ri * math.sqrt(2)) >= w - 1e-9, "the insert's pocket walls"
    # the insert's slide-in pocket (from the bottom flat), the clearance hole across the split, the
    # head's pocket (out through the top flat)
    for d, z0, h, fit in ((COL_INS_NUT, z_bot - 1.0, ins_l + 1.0, True),
                          (3.4, -zi - 0.01, zi + sz + 0.02, False), (M3_HEAD[0] + 0.5, sz, R, False)):
        out = out.cut(teardrop_hole(d, h, axis_point=(xm, sy, z0), axis_dir=(0, 0, 1),
                                    print_up=COLLAR_A_UP, fit=fit))
    # the thread last, UNCLEANED (as the coupler: a cleaned cut drops the ridges). The coupler's
    # cutter runs along +Y in its own frame; turned onto +X here.
    if shaft > 0:                                                 # the motor's D, before the thread
        out = out.cut(_d_bore_local(shaft, grip))
    th = _thread_socket(grip if shaft > 0 else -1.0, L + Lb + 1.0).rotate((0, 0, 0), (0, 0, 1), -90)
    return out.cut(th, clean=False, tol=1e-3)   # fuzzy: no zero-area sliver where a crest meets an end face (Bambu read it as 5 open edges)


# THE COUPLER'S CLAMP (user, 2026-11-16: "as close to centered as possible while leaving sufficient
# clearance from the mount plate"): its screw at the coupler's middle, which pinches the D AND the
# screw's socket (1.5 past the joint), and the Ø COLLAR_D body run down toward the motor as far as the
# plate allows -- its 45 deg cone to Ø CPL_D at the coupler's end, so everything outside the plate's
# pilot hole (less SPIN_GAP) stands SPIN_GAP off the plate's face. Motor frame (y along the shaft).
_PILOT_R = (D.NEMA17_PILOT_D + 0.6) / 2                              # the mount's pilot hole
CPL_CONE = (COLLAR_D - CPL_D) / 2                                    # 3.4: the cone's length
PLATE_FACE_Y = -M_FACE + PLATE_T                                     # -3.5: the motor plate's back face


def cpl_layout(face_y: float = PLATE_FACE_Y) -> tuple:
    """(the body's start, the screw) along the shaft for a mount whose back face is at `face_y`
    (motor frame): the body as near the motor as that face allows, the screw at the coupler's
    middle unless the body starts too late for it (its head's pocket keeps COLLAR_WALL off the
    body's end). The instrument's plate: (-0.6, 5.5)."""
    body = max(CPL_X[0] + CPL_CONE,
               face_y + SPIN_GAP + (COLLAR_D / 2 - (_PILOT_R - SPIN_GAP)))
    hp = (M3_HEAD[0] + 0.5) / 2
    return body, max((CPL_X[0] + CPL_X[1]) / 2, body + hp + COLLAR_WALL)


def _cpl_loc(body_y: float) -> cq.Location:
    """The coupler's own frame (the collar's: axis +X from the body's start, split +Y, screw head
    +Z) -> the motor's (axis +Y from the pulley plane, the D's flat +Z): the split comes out on -Z,
    away from the flat, the head on -X."""
    return cq.Plane(origin=(0, body_y, 0), xDir=(0, 1, 0), normal=(-1, 0, 0)).location


def _to_motor(w: cq.Workplane, body_y: float) -> cq.Workplane:
    loc = _cpl_loc(body_y)
    return cq.Workplane("XY").add([v.moved(loc) for v in w.vals()])


def _d_bore_local(shaft: float, grip: float) -> cq.Workplane:
    body_y = CPL_GRIP - grip
    """src.motor_coupler's D bore (D_CLR, its corners at the nozzle's radius), from 1 past the
    coupler's end to the shaft's end (CPL_GRIP), in the coupler's own frame."""
    from . import motor_coupler as MC
    wp = cq.Workplane("XZ", origin=(0, CPL_GRIP, 0))
    dh, pts = MC._d_bore(wp, CPL_GRIP - CPL_X[0] + 1.0, CPL_X[0] - 1.0, CPL_GRIP, MC.D_CLR)
    loc = _cpl_loc(body_y).inverse
    return cq.Workplane("XY").add([v.moved(loc) for v in MC._round_y_edges(dh, pts).vals()])


def _coupler_body(boss_l: float, face_y: float = PLATE_FACE_Y) -> cq.Workplane:
    """The coupler in the motor frame, from CPL_X[0] to CPL_X[1] (+ boss_l), laid out for a mount
    whose back face is at face_y (cpl_layout)."""
    body_y, screw_y = cpl_layout(face_y)
    return _to_motor(_collar_local(boss_l=boss_l, shaft=body_y - CPL_X[0],
                                   body_l=CPL_X[1] - body_y, screw_x=screw_y - body_y,
                                   grip=CPL_GRIP - body_y), body_y)


def _collar_a(i: int) -> cq.Workplane:
    """BUILT ONCE (kept with no arguments: its key is its own code and dimensions, not where it
    stands) and placed: twenty collars, one formed-thread cut."""
    (c0, _), _ = x_collar_a()
    return kept(_collar_local).translate((c0, y_of(i), za(i)))


def _collar_b(i: int) -> cq.Workplane:
    """Collar A turned end for end about Z: its boss -X onto the race's +X face, split on -Y."""
    (_, c1), _ = x_collar_b()
    return kept(_collar_local).rotate((0, 0, 0), (0, 0, 1), 180).translate((c1, y_of(i), za(i)))


def _collar_m3(i: int, which: str) -> cq.Workplane:
    (c0, c1), _ = x_collar_a() if which == "a" else x_collar_b()
    sy, sz = COLLAR_SCREW
    sg = 1 if which == "a" else -1
    return _cap("m3", COLLAR_M3_L, (_collar_screw_xw(which), y_of(i) + sg * sy, za(i) + sz + M3_HEAD[1]),
                (0, 0, -1))


def _collar_ins(i: int, which: str) -> cq.Workplane:
    """The clamp's brass insert, under the split (both collars: collar B is A turned about Z, so
    only y changes side), its top on the pocket's floor."""
    (c0, c1), _ = x_collar_a() if which == "a" else x_collar_b()
    sy, _ = COLLAR_SCREW
    sg = 1 if which == "a" else -1
    return _insert_x(za(i) - COLLAR_INS_Z, -1, (_collar_screw_xw(which), y_of(i) + sg * sy), None, axis="z")


def _collar_a_ins(i: int) -> cq.Workplane:
    return _collar_ins(i, "a")


def _collar_b_ins(i: int) -> cq.Workplane:
    return _collar_ins(i, "b")


def _collar_a_m3(i: int) -> cq.Workplane:
    return _collar_m3(i, "a")


def _collar_b_m3(i: int) -> cq.Workplane:
    return _collar_m3(i, "b")


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
    if swap_bore is None:
        return out
    # its look: the Tr8x2 thread through it (crests on the screw's root + clearance), the rest as built
    return with_mesh(out, swap_bore(out, D.SCREW_OD, D.SCREW_PITCH, (ft, y, z), (1, 0, 0),
                                    flank_deg=15.0, minor=D.SCREW_OD - D.SCREW_PITCH,
                                    hand=D.SCREW_HAND))


def _ball_x(t: float) -> float:
    return x_yt(t) - YK_ROOF - D.STRING_NUT_L / 2


MOTOR_FINISH = {}                                   # motor part -> its finish (motor_parts)


def _motor_frame(wp: cq.Workplane, i: int) -> cq.Workplane:
    """The motor's own frame (shaft +Y from the pulley plane, the D's flat +Z) -> string i's."""
    return (wp.rotate((0, 0, 0), (0, 1, 0), PLUG_DIR[i]).rotate((0, 0, 0), (0, 0, 1), -90)
            .translate((x_ref(i), y_of(i), za(i))))


def _cpl_shift(i: int) -> float:
    return CPL_SLACK if coupler_is_collar(i) else 0.0


def _coupler(i: int, face_y: float = PLATE_FACE_Y) -> cq.Workplane:
    """THE COLLAR WITH A SHAFT SECTION (_collar_local), in string i's motor frame (its D bore on the
    shaft's flat). On station 0 it is collar A as well: a boss through the lid onto the inner race,
    CPL_SLACK up the shaft."""
    boss = SPIN_GAP + LID_T if coupler_is_collar(i) else 0.0
    # built once per kind (kept on its own dimensions), then placed
    return _motor_frame(kept(_coupler_body, boss, face_y).translate((0, _cpl_shift(i), 0)), i)


def _coupler_clamp(i: int, k: str, face_y: float = PLATE_FACE_Y) -> cq.Workplane:
    """The coupler's clamp part `k` ("m3" or "insert"): the collar's M3 x 10 and slide-in insert, in
    the coupler's own frame, carried into string i's motor frame."""
    sy, sz = COLLAR_SCREW
    body_y, screw_y = cpl_layout(face_y)
    xm = screw_y - body_y
    if k == "m3":
        w = _cap("m3", COLLAR_M3_L, (xm, sy, sz + M3_HEAD[1]), (0, 0, -1))
    else:
        w = _insert_x(-COLLAR_INS_Z, -1, (xm, sy), None, axis="z")
    return placed(w, lambda p: _motor_frame(_to_motor(p, body_y).translate((0, _cpl_shift(i), 0)), i))


def _motor(i: int) -> list:
    from . import components as C
    out = []
    # NO WRITE TO MOTOR_FINISH here (material_of fills it): a global this changed in place made
    # its own kept key move mid-build, so every motor rebuilt on every run
    for k, wp, _, _fin in C.motor_parts():
        w = (wp.rotate((0, 0, 0), (0, 1, 0), PLUG_DIR[i]).rotate((0, 0, 0), (0, 0, 1), -90)
             .translate((x_ref(i), y_of(i), za(i))))
        out.append((f"motor_{k}_{i}" if k else f"motor_{i}", w))
    return out


def _bend_parts() -> list:
    """Each string's two 688s: the bridge bearing and the bend bearing at its row. Their AXLES
    are the endplate's (endplate_axles): they run wall to wall, so they are sized by the body."""
    out = []
    for i in range(N):
        out.append((f"bend_brg_{i}", kept(_bend_brg, i)))
        out.append((f"bridge_brg_{i}", kept(_bridge_brg, i)))
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


def _anchor_screw_z():
    """The ANCHOR_SCREW_N screws a side, evenly from under the top fold (a head's radius and 0.5
    off it) down to the bar's bottom less a tapped hole's margin."""
    z0, z1 = _anchor_z()
    hi = min(z1 - ANCHOR_T - M4_HEAD[0] / 2 - 0.5, BAR_Z[1] - 3.5)
    lo = max(z0 + ANCHOR_T + M4_HEAD[0] / 2 + 0.5, BAR_Z[0] + 3.5)
    n = ANCHOR_SCREW_N
    return tuple(round(hi - k * (hi - lo) / (n - 1), 2) for k in range(n))


def _anchor() -> cq.Workplane:
    x0, x1 = ANCHOR
    (y0, y1), (z0, z1), T, F = _anchor_y(), _anchor_z(), ANCHOR_T, ANCHOR_FL
    w = box_at(T, y1 - y0, z1 - z0, x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(z0 + z1) / 2)
    xf = x1 + F / 2                                  # the folds' middle, x
    for zc in (z1 - T / 2, z0 + T / 2):              # top and bottom: the channel (flaps of
        w = w.union(box_at(F, y1 - y0 - 2 * T, T, x=xf, y=(y0 + y1) / 2, z=zc))   # their own,
                                                     # between the end folds)
    for yc in (y1 - T / 2, y0 + T / 2):              # both ends: their +X edges on the screws
        w = w.union(box_at(F, T, z1 - z0, x=xf, y=yc, z=(z0 + z1) / 2))
    for i in range(N):                               # the screw's hole, the two ties, and
        y, z = y_of(i), za(i)                        # the rod's way in
        w = w.cut(cyl_x(PLATE_HOLE_D, 20, x0 - 10, y=y, z=z))
        ry, rz = rod_yz(i)
        w = w.cut(cyl_x(GUIDE_SEAT + 0.4, 20, x0 - 10, y=ry, z=rz))
        for dy, dz in tie_offsets(i):
            w = w.cut(cyl_x(3.5, 20, x0 - 10, y=y + dy, z=z + dz))   # the ties (M3)
    return w


def _anchor_screw_at():
    """[(y of the wall's inner face, sign toward the inside, x, z)] for every anchor screw."""
    b0, b1 = body_box()["inner"][1]
    x = ANCHOR[1] + ANCHOR_SCREW_DX
    return [(yw, sg, x, z) for yw, sg in ((b0, 1), (b1, -1)) for z in _anchor_screw_z()]


def _anchor_screws() -> cq.Workplane:
    """The M4 x 10 button heads: head on its spacer, into the wall and the bar."""
    return fused([_cap("m4", ANCHOR_SCREW_L, (x, yw + sg * (ANCHOR_SPACER_L + M4_HEAD[1]), z), (0, -sg, 0))
                  for yw, sg, x, z in _anchor_screw_at()])


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
    return _screw(i, x_ref(i) + SCREW_X0 + _cpl_shift(i), SCREW_TIP)


def _brg(i: int) -> cq.Workplane:
    return (ball_bearing(D.BRG688_OD, D.BRG688_ID, D.BRG688_W)
            .rotate((0, 0, 0), (0, 1, 0), 90).translate((x_brg()[0], y_of(i), za(i))))


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
    ("yoke", _yoke, True), ("keyplate", _keyplate_at, True), ("ball", _ball, True),
    ("nut", _nut, True), ("collar", _collar, True), ("m3", _m3s, True),
    ("col_ins", _collar_inserts, True),
    ("spring", _spring, True), ("sleeve_p", _sleeve_plug, False),
    ("sleeve_c", _sleeve_collar, True), ("plug", _anchor_plug, False),
    ("rod", _rod, False), ("screw", _screw_at, False), ("coupler", _coupler, False),
    ("cpl_m3", _cpl_m3, False), ("cpl_insert", _cpl_insert, False),
    ("housing", _housing, False), ("hb", _housing_bolts, False),
    ("insert", _inserts, False), ("collar_a", _collar_a, False),
    ("ca_m3", _collar_a_m3, False), ("collar_b", _collar_b, False),
    ("cb_m3", _collar_b_m3, False), ("ca_ins", _collar_a_ins, False),
    ("cb_ins", _collar_b_ins, False), ("lid", _lid, False), ("tie_spacer", _tie_spacers, False),
    ("brg", _brg, False), ("mplate", _mplate, False),
)


# MESH-ONLY parts (cadkit.mesh_parts): made in milliseconds, so never kept (a kept round trip
# would drop the mesh hung on them)
_MESH_ONLY = {"screw", "spring"}
# the parts that ride the nut AS ONE RIGID BODY: built once, at t = 0, and moved along x to t
# (2026-11-15: the gate's three t's, and every view at another t, read one build of each)
_RIGID = {"yoke", "keyplate", "ball", "nut", "collar", "m3", "col_ins"}


def string_parts(i: int, t: float) -> list:
    """String i's drive, drawn along -X at (y_of(i), za(i)), yawed into place: each part kept."""
    out = []
    for nm, make, moves in _STRING_PARTS:
        if nm in ("collar_a", "ca_m3", "ca_ins") and coupler_is_collar(i):
            continue                                # the coupler is its collar A
        if nm in _MESH_ONLY:
            w = make(i, t) if moves else make(i)
        elif moves and nm in _RIGID:
            dx = x_ft(t) - x_ft(0.0)
            w = kept(make, i, 0.0)
            w = placed(w, lambda p: p.translate((dx, 0.0, 0.0))) if dx else w
        else:
            w = kept(make, i, *((t,) if moves else ()))
        out.append((f"{nm}_{i}", yaw(w, i)))
    out += [(nm, yaw(w, i)) for nm, w in kept(_motor, i)]
    out.append((f"string_{i}", kept(_string, i, t)))
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
# The -X end is the V2 KEYHEAD ENDPLATE (src.keyhead_v2, 2026-11-13): its bed face is the nut
# block's (nut_block_v2.X_BACK), read live.
from . import nut_block_v2 as _NB2
NUT_BLOCK_X0 = D.NUT_BLOCK_X + _NB2.X_BACK
BODY_CLR = 2.0                                      # inside the walls and ends
FLOOR_CLR = 0.5                                     # the floor under the lowest motor (user, 2026-11-12:
                                                    # the motors hang on their plates; the floor never
                                                    # touches them, but no more gap than print tolerance)
BODY_WALL = D.WALL_THICKNESS                        # 10.4, every wall
BODY_FLOOR = 6 * D.BEAD                             # 4.8


def _compound(nm, w):
    # a part of several solids (a pair of bolts) goes as ONE compound: the view and the export
    # take a part's first solid only
    if len(w.solids().vals()) <= 1:
        return (nm, w)
    out = cq.Workplane("XY").add(cq.Compound.makeCompound(w.solids().vals()))
    look = getattr(w, "_cadkit_mesh", None)          # a hung look (cadkit.mesh_parts): same frame
    if look is not None:
        out._cadkit_mesh = look
    return (nm, out)


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
    drive = [w for nm, w in _drive(T_OPEN) if not nm.startswith("string")]
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


def kh_x() -> dict:
    """The keyhead (-X) endplate's clamp, mirrored from ep_x: from its bed face (x0) the head
    recesses (washer + head, flush), the BACK WALL the screws pull on, the gap, the bar's pocket,
    and the JOINT (x_kj) where the walls and floor end."""
    from . import belt_tensioner as BTn
    x0 = NUT_BLOCK_X0
    wall1 = x0 + EP_WASHER[1] + BTn.HEAD_H
    e = ep_x()                                       # the SAME back wall as the +X endplate's (user,
    wall0 = wall1 + (e["wall1"] - e["wall0"])        # 2026-11-13: symmetry), so the same thickness
    bar_x0 = wall0 + EP_GAP
    return dict(x0=x0, wall1=wall1, wall0=wall0, bar_x0=bar_x0, x_kj=bar_x0 + EP_POCKET)


# McMaster 18-8 M3 SHCS stock lengths (91292A: 20, 22, 25, 30 read 2026-11-12) and the thread in the
# bar: 1.5 d -- in steel that already outlasts the screw, and every mm more is drilling and
# tapping the bar end (user, 2026-11-12: only as deep as a firm, lasting grip needs); the tapped
# hole goes EP_TAP_EXTRA past the tip
M3_STOCK = (16.0, 20.0, 22.0, 25.0, 30.0)
EP_ENGAGE, EP_TAP_EXTRA = 1.5 * 3.0, 2.0


def bar_screw_len(end: int = 1) -> float:
    """The shortest stock M3 that, head flush with the end, reaches EP_ENGAGE into the bar
    (end 1: the +X endplate's; -1: the keyhead's)."""
    if end > 0:
        e = ep_x()
        need = e["wall1"] - e["bar_end"] + EP_ENGAGE
    else:
        k = kh_x()
        need = k["bar_x0"] - k["wall1"] + EP_ENGAGE
    return min(L for L in M3_STOCK if L >= need)


def _bar_box(yc: float, x0: float, x1: float, grow: float = 0.0) -> cq.Workplane:
    z0, z1 = BAR_Z[0] - grow, BAR_Z[1] + grow
    return box_at(x1 - x0, BAR_T + 2 * grow, z1 - z0, x=(x0 + x1) / 2, y=yc, z=(z0 + z1) / 2)


def _wall_bars() -> list:
    return [(f"wall_bar_{k}", kept(_wall_bar, k)) for k in range(2)]


def _wall_bar(k: int) -> cq.Workplane:
    """Bar k (0: -Y, 1: +Y), its two tapped M3 holes in the +X end (drawn as the tap drill)."""
    x0 = kh_x()["bar_x0"]                            # in the keyhead endplate's pocket
    x1 = ep_x()["bar_end"]
    yc = bar_y()[k]
    b = _bar_box(yc, x0, x1)
    for zc in EP_SCREW_Z:
        depth = bar_screw_len() - (ep_x()["wall1"] - x1) + EP_TAP_EXTRA
        b = b.cut(cyl_x(2.5, depth, x1 - depth, y=yc, z=zc))
        depth = bar_screw_len(-1) - (x0 - kh_x()["wall1"]) + EP_TAP_EXTRA
        b = b.cut(cyl_x(2.5, depth, x0, y=yc, z=zc))
    for zp in _anchor_screw_z():                     # the anchor's screws: tapped M4 through
        b = b.cut(cyl_y(3.3, BAR_T + 2, yc - BAR_T / 2 - 1, x=ANCHOR[1] + ANCHOR_SCREW_DX, z=zp))
    return b


def _bar_screws() -> list:
    """The four M3 SHCS (bar_screw_len) and their washers: through the back wall into the bar
    ends, the head on its washer flush with the +X end."""
    from . import belt_tensioner as BTn
    e = ep_x()
    out = []
    for yc in bar_y():
        for zc in EP_SCREW_Z:
            top = e["wall1"] + EP_WASHER[1] + BTn.HEAD_H
            out += [_cap("m3", bar_screw_len(), (top, yc, zc), (-1, 0, 0)),
                    cyl_x(EP_WASHER[0], EP_WASHER[1], e["wall1"], y=yc, z=zc)
                    .cut(cyl_x(3.2, EP_WASHER[1] + 1, e["wall1"] - 0.5, y=yc, z=zc))]
    return fused(out)


def _body() -> cq.Workplane:
    """The walls and floor up to the endplate, all ending at x_j: one print, so one flat face the
    endplate bears on. The floor carries the strings' pull across the middle (2026-11-12:
    no floor gap; the walls alone left the endplate a 168 mm beam at ~16 MPa through a lane).
    Each wall carries its bar's channel, open at +X."""
    from cadkit.holes import teardrop_hole
    (x0, _), (y0, y1), (z0, z1) = body_box()["outer"]
    (a0, _), (b0, b1), (c0, _) = body_box()["inner"]
    xj = ep_x()["x_j"]
    x0 = kh_x()["x_kj"]                              # the -X end is the keyhead endplate's
    w = box_at(xj - x0, y1 - y0, z1 - z0, x=(x0 + xj) / 2, y=(y0 + y1) / 2, z=(z0 + z1) / 2)
    w = w.cut(box_at(xj + 1 - a0, b1 - b0, z1 - c0 + 2.0, x=(a0 + xj + 1) / 2, y=(b0 + b1) / 2,
                     z=(c0 + z1 + 2.0) / 2))
    for yc, yin in zip(bar_y(), (b0, b1)):
        w = w.cut(_bar_box(yc, x0 - 1, xj + 1, BAR_CLR))
        for zp in _anchor_screw_z():                 # the anchor screws through the INNER skin
            lo, hi = min(yc, yin), max(yc, yin)      # only (the outer skin stays whole)
            w = w.cut(teardrop_hole(4.4, hi - lo + 0.5, axis_point=(ANCHOR[1] + ANCHOR_SCREW_DX,
                                    lo - (0.5 if lo == yin else 0), zp), axis_dir=(0, 1, 0)))
        # the anchor's REFERENCE RIB (user, 2026-11-12): at the web's -X face, floor to its top
        rw, ro, rg = ANCHOR_RIB
        sg = 1 if yin == b0 else -1
        za0, za1 = c0, _anchor_z()[1]
        w = w.union(box_at(rw, ro, za1 - za0, x=ANCHOR[0] - rg - rw / 2, y=yin + sg * ro / 2,
                           z=(za0 + za1) / 2))
        for i in range(N):                           # the guide rods' way past it, and their
            ry, rz = rod_yz(i)                       # caps on the housings (string 1's meets it)
            w = w.cut(cyl_x(2 * (GUIDE_SEAT / 2 + GUIDE_WALL) + 2.0, rw + 2, ANCHOR[0] - rg - rw - 1,
                            y=ry, z=rz))
        # THE SPACERS ARE THE BODY'S (user, 2026-11-12): a printed BOSS under each anchor screw's
        # head, ANCHOR_SPACER_L off the skin, the head tightened down onto it. Printed -Z -> +Z:
        # a 45 deg RAMP under it, and nothing over the screw -- a block below the shank, its top
        # at the axis, and a column on its +X side up to the head's top; the -X side stands 1
        # clear of the end fold's edge, the WINDOW the fold bears on the bare shank through
        for zs in _anchor_screw_z():
            xa = ANCHOR[1] + ANCHOR_SCREW_DX
            xl, xh = xa - 1.0, xa + M4_HEAD[0] / 2 + D.BEAD
            hz, L = M4_HEAD[0] / 2 + D.BEAD, ANCHOR_SPACER_L
            # (u: off the skin, inward; z) -- block, ramp under it, column beside the shank
            prof = [(0.0, zs - hz - L), (L, zs - hz), (L, zs), (0.0, zs)]
            pts = [(yin + sg * u, z_) for u, z_ in prof]
            blk = cq.Workplane("YZ", origin=(xl, 0, 0)).polyline(pts).close().extrude(xh - xl)
            col = box_at(xh - (xa + 2.2), L, 2 * hz, x=(xh + xa + 2.2) / 2, y=yin + sg * L / 2,
                         z=zs + hz / 2 - 0.01)
            w = w.union(blk).union(col)
            lo_y = min(yin, yin + sg * L)
            w = w.cut(teardrop_hole(4.4, L + 1.0, axis_point=(xa, lo_y - 0.5, zs), axis_dir=(0, 1, 0)))
    w = w.cut(_ob_groove())                      # the output board's bottom edge
    # THE CONNECTOR BOARD'S BOSS (lead / bronner, 2026-11-15): one M4 heat-set boss up off the
    # floor, its top the board's underside (lifted CB_BOSS_TOP - floor = 5.0 for the MX15 THT
    # tails: confirm the tails on a sample before printing), the insert's pocket in its top
    from cadkit.fasteners import M4, cut_pocket
    bx, by, bt = CB_BOSS
    w = w.union(cyl_z(M4.boss_od, bt - c0 + 0.01, c0 - 0.01, x=bx, y=by))
    w = cut_pocket(M4, w, (bx, by, bt), (0, 0, -1), overshoot=0.5, print_up=(0, 0, 1))
    from . import deck_v2 as _DK                    # the walls stop at the deck panels' underside,
    w = w.cut(_DK.wall_cutter())                     # a groove down each for the panels' tongues
    return w


# THE ENDPLATE (user, 2026-11-12): ONE printed PETG-GF part, the instrument's +X end from the
# JOINT (x_j, where the walls and floor end) to the end, the full height (the bed under it to the
# bridge axle's top), PRINTED +X -> -X (EP_UP). Just enough of it to:
#   - hold each GUIDE ROD (its seat from the plate's back, ~24 deep: ROD_TIP);
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
EP_BRG_CLR = 1.0                                     # a lane's roof / floor off a bearing's rim
# the slot's gable (SLOT_APEX_X) stays ROD_SEAT_WALL off every rod seat's tip it passes beside
for _i in range(N):
    _ry, _ = rod_yz(_i)
    for _j in range(N):
        _dy = abs(_ry - y_of(_j)) - GUIDE_SEAT / 2           # the seat's nearest edge off the lane's middle
        if _dy < LANE_HW:
            assert SLOT_APEX_X + max(_dy, 0.0) - (ROD_TIP + 0.3) >= ROD_SEAT_WALL - 1e-9, (
                f"the slot's roof in lane {_j + 1} leaves rod {_i + 1}'s seat "
                f"{SLOT_APEX_X + max(_dy, 0.0) - ROD_TIP - 0.3:.2f} of wall")
AXLE_STOP_T, PUSH_D = 3.0, 3.2                       # the +Y stop; the push-out hole (a 2.5 key)
# THE ENDPLATE PRINTS +X -> -X (user, 2026-11-13: "a clean look on the exterior"): its +X end on
# the bed, the joint face (x_j) last. Every hole along X (rods, M3 heads, bar screws, I/O) prints
# ROUND; the bores across it (the axles) peak toward -X. The one bridge is the rod plate's +X face
# over each lane (2 LANE_HW, 5.2 across): the lane reaches EP_DROOP into the plate there, so a
# sagging bridge still clears the bend bearing's rim by BRG_CLR.
EP_UP = (-1.0, 0.0, 0.0)
EP_DROOP = 0.5


def axle_zs() -> list:
    """(name, z) of the four axles, all at x X_BEND."""
    return [(f"bend_axle_r{'abc'[k]}", z_level(k) + R) for k in range(LEVELS)] + \
           [("bridge_axle", D.BRIDGE_BEARING_Z)]


AXLE_L = 100.0                                       # STOCK: McMaster 6459K118, O8 x 100 (user,
                                                     # 2026-11-13: no cutting; was 106.7 with an 8 grip)


def axle_span() -> tuple:
    """Each axle's y: one length for all four rows (one part to stock), the outermost lanes'
    width plus what AXLE_L leaves each side as its grip in plastic. It goes in from -Y down its bore and stops on the +Y wall."""
    ys = [y_of(i) for i in range(N)]
    grip = (AXLE_L - (max(ys) - min(ys)) - 2 * LANE_HW) / 2       # 4.65 at 100
    assert grip >= 0.5 * D.BRIDGE_AXLE_D, grip
    return min(ys) - LANE_HW - grip, max(ys) + LANE_HW + grip


def endplate_axles() -> list:
    return [(nm, kept(_axle, k)) for k, (nm, _) in enumerate(axle_zs())]


def _axle(k: int) -> cq.Workplane:
    a, b = axle_span()
    return cyl_y(D.BRIDGE_AXLE_D, b - a, a, x=X_BEND, z=axle_zs()[k][1])


# ── THE OUTPUT BOARD (bronner's single board, 2026-11-13) ───────────────────────────────────
# INSTALL (user, 2026-11-13): deck off, the board drops -Z beside the -Y wall, its bottom edge
# into a groove in the body's floor, then slides OB_SLIDE +X into a POCKET in the endplate's
# inner face until J5's shoulder meets the outer wall. The pocket FOLLOWS THE BOARD (user: no
# more plastic away than it needs): a slot for the laminate, and for each part that ends up
# inside the endplate a channel its courtyard's outline and height, all along X (the slide).
# The outer face shows only the I/O: J5's round hole through its 4.0 clamp wall, the USB-Cs'
# overmold stadiums. The board's outline and its parts are bronner's export, final position
# (src/output_board_pocket.json, copied from his elec/output_board.pocket.json).
import json as _json
from pathlib import Path as _Path
OB = _json.loads(_Path(__file__).with_name("output_board_pocket.json").read_text(encoding="utf-8"))
OB_SLIDE = 19.0                                     # the +X slide after the drop
OB_CLR = 0.4                                        # round every channel: a sliding fit


def _ob_part(p: dict) -> tuple:
    """A part's (x0, x1, z0, z1, h) in instrument coordinates, its courtyard."""
    return p["x"][0], p["x"][1], p["z"][0], p["z"][1], p["h"]


def _ob_pocket() -> cq.Workplane:
    """The cutter: the laminate's slot, each part's channel, and the I/O through the wall."""
    xj, xe = ROD_PLATE[0], X_BEND + R + D.STRING_GAUGE_MAX
    face, (ly0, ly1), (bz0, bz1) = OB["component_face_y"], OB["laminate_y"], OB["z"]
    edge, c = OB["edge_x"], OB_CLR
    w = box_at(edge + c - (xj - 1), ly1 - ly0 + 2 * c, bz1 - bz0 + 2 * c,
               x=(xj - 1 + edge + c) / 2, y=(ly0 + ly1) / 2, z=(bz0 + bz1) / 2)
    for p in OB["parts_past_inner_face"]:
        x0, x1, z0, z1, h = _ob_part(p)
        if p["ref"] == "J5":                        # its shoulder bears on the wall: no gap
            x1 = edge + p["protrudes"]
        else:
            x1 += c
        w = w.union(box_at(x1 - (xj - 1), h + c + 0.01, z1 - z0 + 2 * c, x=(xj - 1 + x1) / 2,
                           y=face + (h + c - 0.01) / 2, z=(z0 + z1) / 2))
        tl = p.get("tail")                          # through-hole tails out of the back,
        if tl:                                      # UNCLIPPED (board_geom: untrimmed fits)
            (tx0, tx1), (tz0, tz1), ty0 = tl["x"], tl["z"], tl["y"][0]
            w = w.union(box_at(tx1 + c - (xj - 1), ly0 - ty0 + c + 0.01, tz1 - tz0 + 2 * c,
                               x=(xj - 1 + tx1 + c) / 2, y=(ty0 - c + ly0 + 0.01) / 2,
                               z=(tz0 + tz1) / 2))
        zc, ya = (z0 + z1) / 2, face + p.get("axis_off_face", 0.0)
        xm = edge + p.get("protrudes", 0.0) - 0.01
        op = p.get("opening", "")
        if op.startswith("round"):
            w = w.union(cyl_x(float(op.split()[1]), xe + 1 - xm, xm, y=ya, z=zc))
        elif op.startswith("stadium"):
            sw, sh = (float(v) for v in op.split()[1].split("x") if v) if "x" in op.split()[1] \
                else (float(op.split()[1]), float(op.split()[3]))
            w = w.union(cq.Workplane("YZ", origin=(xm, ya, zc)).slot2D(sw, sh, angle=90)
                        .extrude(xe + 1 - xm))
    return w


def _ob_groove() -> cq.Workplane:
    """The body floor's groove under the board's bottom edge, from where it drops to x_j."""
    (ly0, ly1), bz0, c = OB["laminate_y"], OB["z"][0], OB_CLR
    x0, x1 = OB["minus_x_edge"] - OB_SLIDE - c, ROD_PLATE[0] + 1
    return box_at(x1 - x0, ly1 - ly0 + 2 * c, 3.0, x=(x0 + x1) / 2, y=(ly0 + ly1) / 2,
                  z=bz0 - c + 1.5)


def _ob_board() -> cq.Workplane:
    """bronner's board as a stand-in for the gates: the laminate and its parts' courtyards
    (final position; only the parts that reach the endplate are listed)."""
    face, (ly0, ly1), (bz0, bz1) = OB["component_face_y"], OB["laminate_y"], OB["z"]
    x0, x1 = OB["minus_x_edge"], OB["edge_x"]
    w = box_at(x1 - x0, ly1 - ly0, bz1 - bz0, x=(x0 + x1) / 2, y=(ly0 + ly1) / 2, z=(bz0 + bz1) / 2)
    for p in OB["parts_past_inner_face"]:
        px0, px1, z0, z1, h = _ob_part(p)
        if p["ref"] == "J5":
            px1 = x1 + p["protrudes"]
        w = w.union(box_at(px1 - px0, h, z1 - z0, x=(px0 + px1) / 2, y=face + h / 2,
                           z=(z0 + z1) / 2))
        tl = p.get("tail")
        if tl:
            (tx0, tx1), (tz0, tz1), (ty0, ty1) = tl["x"], tl["z"], tl["y"]
            w = w.union(box_at(tx1 - tx0, ty1 - ty0, tz1 - tz0, x=(tx0 + tx1) / 2,
                               y=(ty0 + ty1) / 2, z=(tz0 + tz1) / 2))
    return w


def _endplate(rods: bool = True, only: int = None) -> cq.Workplane:
    """only: draw ONE string's lane, window, rod and reliefs (the wood bench's slice)."""
    strings = range(N) if only is None else (only,)
    from cadkit.holes import teardrop_hole
    (_, _), (y0, y1), (z0, _) = body_box()["outer"]
    e = ep_x()
    xj, xe = e["x_j"], e["x_end"]
    w = box_at(xe - xj, y1 - y0, EP_TOP - z0, x=(xj + xe) / 2, y=(y0 + y1) / 2, z=(z0 + EP_TOP) / 2)
    if PLATE_LOW_X > xj:                                         # low under the pickup
        w = w.cut(box_at(PLATE_LOW_X - xj + 1, PICK_Y[1] - PICK_Y[0], EP_TOP - PLATE_TOP + 1,
                         x=(xj - 1 + PLATE_LOW_X) / 2, y=sum(PICK_Y) / 2,
                         z=(PLATE_TOP + EP_TOP + 1) / 2))
    for i in strings:                                           # the lanes, and the windows
        za_i = za(i)
        # each lane runs out through the +X end and the top (user, 2026-11-12: open, only the
        # fingers between the bearings, so a string feeds in and out when restringing)
        # ...and down as deep as the window, so the keyhole's bottom shows from above and the
        # ball goes straight in (user, 2026-11-12), but LANE_WALL over the peak of the next
        # row's axle bore (peaked -X as printed, so round in z) where one runs under the lane
        lo = za_i + WIN_Z[0]
        under = [zc for _, zc in axle_zs() if zc < za_i]
        if under:
            lo = max(lo, max(under) + (D.BRIDGE_AXLE_D + 0.2) / 2 + LANE_WALL)
        # THE LANE IS FILLED OVER ITS BEND BEARING (user, 2026-11-12: no string goes in there):
        # open from the window's floor up to EP_BRG_CLR over the bend bearing (a flat roof: it
        # is a side wall as printed, +X -> -X); solid from there up to a pocket with a flat floor
        # EP_BRG_CLR under the bridge bearing, open through the top; and a SLOT at the +X face the
        # string drops through, EP_STR_CLR off it, the lane's whole height
        y_i, x0l, x1l = y_of(i), ROD_PLATE[1] - EP_DROOP, xe + 1
        zr = z_level(level(i)) + R + D.BRG688_OD / 2 + EP_BRG_CLR      # the roof's eaves
        w = w.cut(box_at(x1l - x0l, 2 * LANE_HW, zr - lo, x=(x0l + x1l) / 2, y=y_i,
                         z=(lo + zr) / 2))
        zb = BR_C[1] - D.BRG688_OD / 2 - EP_BRG_CLR                    # the bridge's pocket
        w = w.cut(box_at(x1l - x0l, 2 * LANE_HW, EP_TOP + 1 - zb, x=(x0l + x1l) / 2, y=y_i,
                         z=(zb + EP_TOP + 1) / 2))
        # THE STRING'S SLOT ENDS IN A ROOF (user, 2026-11-13): its -X end is a 45 deg gable
        # peaked -X, the build direction, so the fill over the bend bearing ends in a roof and
        # not a 5.2 bridge; the gable stands EP_STR_CLR off the heaviest string all round
        xa, xs = SLOT_APEX_X, SLOT_APEX_X + LANE_HW
        w = w.cut(box_at(x1l - xs, 2 * LANE_HW, EP_TOP + 1 - lo, x=(xs + x1l) / 2, y=y_i,
                         z=(lo + EP_TOP + 1) / 2))
        w = w.cut(cq.Workplane("XY", origin=(0, 0, lo))
                  .polyline([(xs + 0.01, y_i - LANE_HW), (xs + 0.01, y_i + LANE_HW), (xa, y_i)]).close()
                  .extrude(EP_TOP + 1 - lo))
        lo, hi = WIN_Z
        # the window as wide as the lane (user, 2026-11-12): the ball comes down the lane, so
        # anything wider only took plate away (and met the M3 heads' holes)
        w = w.cut(box_at(ROD_PLATE[1] - xj + 2, 2 * LANE_HW, hi - lo, x=(xj + ROD_PLATE[1]) / 2,
                         y=y_of(i), z=za_i + (lo + hi) / 2))
        # THE M3 HEADS' HOLES (user, 2026-11-12, trial: heads on the keyhole plate's +X face): the
        # plate still bottoms out on the rod plate, the heads (3 tall) sunk in it -- round
        # (along the print), 0.3 round the head, right through the plate
        for a in HOLE_ANG["m3"]:
            dy, dz = at_ang(a)
            w = w.cut(cyl_x(M3_HEAD[0] + 0.6, ROD_PLATE[1] - xj + 2, xj - 1, y=y_of(i) + dy,
                            z=za_i + dz))
            # where a hole stands beside the window, the sliver between them is OPENED (user,
            # 2026-11-12: too little plastic there to print): the hole's near half joins the
            # window, a slot the head's width
            yw = y_of(i) + math.copysign(LANE_HW, dy)
            if abs(dy) - (M3_HEAD[0] + 0.6) / 2 < LANE_HW + 2 * D.BEAD and za_i + dz < za_i + WIN_Z[1]:
                rh, yc, zc = (M3_HEAD[0] + 0.6) / 2, y_of(i) + dy, za_i + dz
                pts = [(yc, zc + rh), (yw, zc + rh), (yw, zc - rh), (yc, zc - rh)]
                w = w.cut(cq.Workplane("YZ", origin=(xj - 1, 0, 0)).polyline(pts).close()
                          .extrude(ROD_PLATE[1] - xj + 2))
    # the rods' BOSSES: GUIDE_WALL round each seat where it runs beside a lane (strings 4-5, 7-8
    # and 10 have ~0.9 without), to the seat's floor, then a 45 deg cone down to 0.8 of wall --
    # the boss's +X end faces the bed as printed (+X -> -X), so it may not end flat in a lane
    rb = GUIDE_SEAT / 2 + GUIDE_WALL
    rc = GUIDE_SEAT / 2 + D.BEAD
    for i in (strings if rods else ()):
        ry, rz = rod_yz(i)
        xb = ROD_TIP + 0.3
        w = w.union(cyl_x(2 * rb, xb - xj, xj, y=ry, z=rz))
        w = w.union(cq.Solid.makeCone(rb, rc, rb - rc, cq.Vector(xb - 0.01, ry, rz), cq.Vector(1, 0, 0)))
    for i in (strings if rods else ()):                            # ...but EP_BRG_CLR off every
        zc = z_level(level(i)) + R                               # bend bearing's rim, where a
        w = w.cut(cyl_y(D.BRG688_OD + 2 * EP_BRG_CLR, 2 * LANE_HW, y_of(i) - LANE_HW,   # boss runs
                        x=X_BEND, z=zc))                         # beside the next row's lane
    for i in (strings if rods else ()):
        ry, rz = rod_yz(i)
        w = w.cut(cyl_x(GUIDE_SEAT, ROD_TIP + 0.3 - (xj - 3), xj - 3, y=ry, z=rz))   # round
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
                                axis_dir=(0, 1, 0), print_up=EP_UP))
        w = w.cut(teardrop_hole(PUSH_D, y1 + 1 - (b - 0.5), axis_point=(X_BEND, b - 0.5, zc),
                                axis_dir=(0, 1, 0), print_up=EP_UP))   # and the push-out hole
    for i in strings:                                           # the fingers' reliefs: off the
        for zc in (z_level(level(i)) + R, D.BRIDGE_BEARING_Z):   # turning outer races, both sides
            yb = y_of(i)
            w = w.cut(_tube_y(SHIELD_D, RACE_D, yb - LANE_HW - COMB_RELIEF, yb - LANE_HW + 0.01, zc))
            w = w.cut(_tube_y(SHIELD_D, RACE_D, yb + LANE_HW - 0.01, yb + LANE_HW + COMB_RELIEF, zc))
    for yc in bar_y():                                           # the bars' ends
        w = w.cut(_bar_box(yc, xj - 1, e["wall0"], BAR_CLR))      # pocket + gap
        for zc in EP_SCREW_Z:
            w = w.cut(cyl_x(EP_M3_CLR, e["wall1"] - e["bar_end"] + 1, e["bar_end"], y=yc, z=zc))
            w = w.cut(cyl_x(EP_TUNNEL, xe + 1 - e["wall1"], e["wall1"], y=yc, z=zc))   # a short
            # bridge as printed (the back wall's +X face round the screw), 7.2 across
    # FLAT PAST THE STRINGS (user, 2026-11-14): outside the strings' band the endplate stands only to
    # the top panels' top, so the instrument is flat except where the strings need the height
    from . import deck_v2 as _DK
    ya, yb = ep_raised_y()
    for ys0, ys1 in ((y0 - 1.0, ya), (yb, y1 + 1.0)):
        w = w.cut(box_at(xe - xj + 2, ys1 - ys0, EP_TOP + 1 - _DK.TZ, x=(xj + xe) / 2,
                         y=(ys0 + ys1) / 2, z=(_DK.TZ + EP_TOP + 1) / 2))
    if only is None:
        w = w.cut(_ob_pocket())                                  # the output board
    return w


def ep_raised_y() -> tuple:
    """The +X endplate's raised band in y (user, 2026-11-14): the outermost strings' lanes and one
    more FINGER past each (a finger is what stands between two lanes), and wide enough that the
    bridge axle (stock AXLE_L, its top at z 12) keeps its bore: its -Y end flush with the step, its
    +Y end on the AXLE_STOP_T stop wall with the push hole through it."""
    ys = sorted(y_of(i) for i in range(N))
    finger = min(b - a for a, b in zip(ys, ys[1:])) - 2 * LANE_HW
    a, b = axle_span()
    return min(ys[0] - LANE_HW - finger, a), max(ys[-1] + LANE_HW + finger, b + AXLE_STOP_T)


@_lru_cache(maxsize=None)
def endplate_full():
    return kept(_endplate)


def assembly(t: float = T_OPEN, all_ghosts: bool = False) -> list:
    from .changer_bench import ghosts as _ghosts
    out = _drive(t) + [("endplate", endplate_full())] + endplate_axles()
    # EVERY PART THE VIEW CAN SHOW OR HIDE IS KEPT ON ITS OWN (user, 2026-11-12): an edit
    # rebuilds the parts whose code or inputs it touched, and nothing else
    out += [_compound("anchor", kept(_anchor)), _compound("anchor_m4", kept(_anchor_screws))]
    out += _wall_bars() + [_compound("bar_m3", kept(_bar_screws))]
    from . import keyhead_v2 as _KH                  # the -X endplate, its plates, screws and rod
    out += _KH.parts()
    from . import deck_v2 as _DK                     # the top panels and the fret LED stand-in
    out += _DK.parts()
    out = [(nm, _made(nm, w)) for nm, w in out] + list(ui_parts()[0])
    out.append(("ob_board", _made("ob_board", kept(_ob_board))))   # bronner's, a stand-in
    out.append(("body", _made("body", kept(_body))))   # opaque PETG-GF, as the lead's chassis
    out += [g for g in _ghosts(y_hi=RAIL_HI)
            if g[0] not in ("ghost_bottom_now", "ghost_pickup") and all_ghosts]   # the pickup is drawn now
    return out


# What each part is made of, for the viewer's shine (cadkit.web.finishes.made_of): printed
# frames in the instrument's PETG-GF, the bought parts as they are.
MATERIAL = {
    "yoke": "petg-gf", "keyplate": "steel", "collar": "pctg", "block": "petg-gf", "mplate": "petg-gf",
    "endplate": "petg-gf", "bar_m3": "steel", "bridge_axle": "steel", "bridge_brg": "polished", "anchor": "stainless", "anchor_m4": "steel",
    "body": "petg-gf", "wall_bar": "steel", "ob_board": "board",
    "keyhead": "petg-gf", "kh_m3": "steel", "kh_plate": "stainless", "kh_side_screw": "steel",
    "kh_side_insert": "brass", "kh_height_screw": "steel", "kh_shoe": "petg-gf", "kh_height_insert": "brass", "kh_rod": "steel",
    "nut": "brass", "ball": "brass", "screw": "steel", "rod": "steel", "string": "polished",
    "brg": "polished", "bend_brg": "polished", "bridge_bearings": "polished",
    "bend_axle_ra": "steel", "bend_axle_rb": "steel", "bend_axle_rc": "steel",
    "spring": "stainless", "plug": "petg-gf", "sleeve_p": "petg-gf", "sleeve_c": "petg-gf", "m3": "steel", "col_ins": "brass", "coupler": "petg-gf",
    "cpl_m3": "steel", "cpl_insert": "brass", "housing": "petg-gf", "hb": "steel", "insert": "brass",
    "collar_a": "petg-gf", "collar_b": "petg-gf", "ca_m3": "steel", "cb_m3": "steel", "ca_ins": "brass", "cb_ins": "brass", "lid": "petg-gf", "tie_spacer": "aluminium",
    "deck": "pctg-black", "deck_white": "pctg-clear", "fret_board": "board",
    "fret_leds": "nylon",                        # bought 5050s: a moulded white package, its colour kept
    # the +X end (src/deck_v2_region.py): the optical panel, the pickup's piece and fillers, its mount
    "deck_optical": "pctg-black", "deck_pickup": "pctg-black", "deck_filler": "pctg-black",
    "optical_board": "board", "pickup": "aluminium", "pickup_plate": "petg-gf",
    "pickup_jack_screw": "steel", "pickup_jack_insert": "brass",
    "pickup_ret_screw": "steel", "pickup_ret_insert": "brass",
}


# THE PART NAMES ARE PLAIN (user, 2026-11-14): this is the instrument now, so its parts carry no
# bench prefix. owns() is how the shared tools (check_overlaps, check_sweep, web_materials, the
# build's colours) know a name is this instrument's and ask here.
def owns(name: str) -> bool:
    """Is `name` (indices off) one of this instrument's parts?"""
    b = _re.sub(r"(_\d+)+$", "", name.split("__")[0])
    return b in _OWN or b in _motor_names()


@_functools.lru_cache(maxsize=None)
def _motor_names() -> frozenset:
    """The motor's part names as _motor draws them (indices off): "motor" and "motor_<k>".
    Exact names, not a "motor" prefix: v1's motor_shaft_saw_jig is not ours."""
    from . import components as C
    return frozenset(f"motor_{k}" if k else "motor" for k, *_ in C.motor_parts())


def material_of(base: str):
    """The material of a direct-bench part (its name, indices off), or None."""
    inner = base
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


# ── colours (src.build._color_for asks here for  names) ──────────────────────────────────
# inner name ( and EVERY trailing index group off) -> a key of build._COLORS, or an RGB.
COLORS = {
    "nut": "nut", "ball": "string_nut", "screw": "leadscrew", "brg": "screw_bearing",
    "string": "string", "bridge_bearings": "bridge_bearings", "rod": "guide_rod",
    "bend_brg": "bridge_bearings", "bend_axle_ra": "leadscrew", "bend_axle_rb": "leadscrew",
    "bend_axle_rc": "leadscrew",
    "yoke": (0.39, 0.58, 0.93), "collar": (0.85, 0.45, 0.15),
    "spring": "leg_latch_spring", "plug": (0.85, 0.45, 0.15),
    "sleeve_p": (0.95, 0.75, 0.20), "sleeve_c": (0.95, 0.75, 0.20), "m3": "set_screw", "col_ins": "nut",
    "coupler": (0.85, 0.45, 0.15), "cpl_m3": "set_screw", "cpl_insert": "nut",
    "housing": (0.30, 0.36, 0.42), "hb": "set_screw", "insert": "nut",
    "collar_a": (0.85, 0.45, 0.15), "collar_b": (0.85, 0.45, 0.15), "ca_m3": "set_screw",
    "cb_m3": "set_screw", "ca_ins": "nut", "cb_ins": "nut", "lid": (0.30, 0.36, 0.42), "tie_spacer": (0.78, 0.79, 0.81), "block": (0.30, 0.36, 0.42), "mplate": (0.30, 0.33, 0.38),
    "endplate": (0.36, 0.30, 0.42), "bar_m3": "set_screw", "bridge_axle": "set_screw",
    "bridge_brg": "bridge_bearings", "anchor": "nut_plate", "anchor_m4": "set_screw",
    "keyhead": (0.36, 0.30, 0.42), "kh_m3": "set_screw", "kh_plate": "nut_plate", "kh_shoe": (0.85, 0.45, 0.15),
    "kh_side_screw": "set_screw", "kh_side_insert": "nut", "kh_height_screw": "set_screw",
    "kh_height_insert": "nut", "kh_rod": "guide_rod",
    "body": "chassis", "wall_bar": "nut_plate", "keyplate": "nut_plate", "ob_board": _mask_rgb("green"),
    "deck": (0.16, 0.16, 0.18), "deck_white": (0.95, 0.95, 0.92), "fret_board": _mask_rgb("green"),
    "optical_board": _mask_rgb("green"),        # the stand-in: no mask ordered yet, the fab default
    # the +X end (src/deck_v2_region.py): panels as the deck, the pickup's hardware as v1's
    "deck_optical": (0.16, 0.16, 0.18), "deck_pickup": (0.16, 0.16, 0.18), "deck_filler": (0.16, 0.16, 0.18),
    "pickup": (0.10, 0.10, 0.12), "pickup_plate": (0.85, 0.65, 0.30),
    "pickup_jack_screw": (0.55, 0.55, 0.58), "pickup_ret_screw": (0.55, 0.55, 0.58),
    "pickup_jack_insert": (0.80, 0.60, 0.35), "pickup_ret_insert": (0.80, 0.60, 0.35),
    "fret_leds": (1.0, 0.98, 0.85),
}


# every base name this instrument draws (owns() reads it): the tables above, the drive's parts, and
# the few drawn with no material or colour of their own
_OWN = (set(MATERIAL) | set(COLORS) | {nm for nm, _, _ in _STRING_PARTS}
        | {"string", "bend_axle_ra", "bend_axle_rb", "bend_axle_rc", "kh_rod"})


def color_of(base: str, table: dict):
    inner = base
    v = COLORS.get(inner, inner)
    return v if isinstance(v, tuple) else table.get(v)


# ── the gate ────────────────────────────────────────────────────────────────────────────────
import re as _re

_IDX = _re.compile(r"_(\d+)$")


def _base(nm: str):
    m = _IDX.search(nm)
    b, i = (nm[:m.start()], int(m.group(1))) if m else (nm, None)
    return ("motor" if b.startswith("motor") else b), i


_SAME = {frozenset(p) for p in (
    ("screw", "nut"), ("screw", "brg"), ("screw", "coupler"),
    ("nut", "yoke"), ("nut", "collar"),
    ("m3", "col_ins"), ("col_ins", "collar"),       # threaded; heat-set (melted in)
    ("m3", "collar"), ("m3", "nut"), ("m3", "yoke"), ("m3", "keyplate"),
    ("spring", "plug"),
    ("sleeve_p", "plug"), ("sleeve_p", "spring"),
    ("sleeve_c", "collar"), ("sleeve_c", "spring"),
    ("yoke", "ball"), ("string", "ball"), ("string", "yoke"),
    ("collar", "spring"), ("brg", "block"), ("coupler", "motor"),
    ("motor", "mplate"), ("motor",), ("coupler", "block"),
    ("cpl_m3", "cpl_insert"),
    ("housing", "brg"), ("collar_a", "brg"), ("collar_b", "brg"),
    ("collar_a", "screw"), ("collar_b", "screw"), ("ca_m3", "collar_a"), ("cb_m3", "collar_b"),
    ("ca_m3", "ca_ins"), ("cb_m3", "cb_ins"), ("ca_ins", "collar_a"), ("cb_ins", "collar_b"),
    ("lid", "brg"), ("lid", "housing"), ("hb", "lid"), ("hb", "tie_spacer"), ("tie_spacer", "housing"),
    ("hb", "housing"), ("hb", "plug"), ("hb", "insert"), ("insert", "plug"),
    ("housing", "plug"),
    ("kh_side_screw", "kh_side_insert"), ("kh_height_screw", "kh_height_insert"),
    ("kh_height_screw", "kh_shoe"))}            # its tip bears on the shoe's wedge


def is_intended(a: str, b: str) -> bool:
    (ba, ia), (bb_, ib) = _base(a), _base(b)
    if ia is not None and ia == ib and frozenset((ba, bb_)) in _SAME:
        return True
    pair = {ba, bb_}
    if all(n.startswith("ghost_") for n in pair):
        return True
    bends = {"bend_axle_ra", "bend_axle_rb", "bend_axle_rc", "bend_brg"}
    if "string" in pair and pair & (bends | {"bridge_brg", "bridge_axle", "ghost_keyhead"}):
        return True
    if "bridge_brg" in pair and "bridge_axle" in pair:       # each bridge 688 on its axle
        return True
    if pair & {"bar_m3", "kh_m3"} and "wall_bar" in pair:   # threaded into the bar ends
        return True
    if "keyhead" in pair and pair & {"kh_side_insert", "kh_height_insert"}:   # melted in
        return True
    if "string" in pair and pair & {"kh_rod", "kh_plate", "kh_side_screw"}:
        return True                                  # wound on the rod, pinched, pinned
    if "keyhead" in pair and "ghost_keyhead" in pair:
        return True
    # the lead's instrument's ghosts (deck, walls, keyhead) stand where this body's own walls,
    # bars and endplate now are: no clash to report against a ghost of the other design
    if any(n.startswith("ghost_") for n in pair) and pair & {
            "wall_bar", "endplate", "bar_m3", "body", "bridge_axle", "keyhead",
            "kh_m3", "kh_plate", "kh_shoe", "kh_side_screw", "kh_side_insert", "kh_height_screw",
            "kh_height_insert", "kh_rod",
            "bend_axle_ra", "bend_axle_rb", "bend_axle_rc"}:
        return True
    # the deck panels ARE the lead's deck ghost now, and cap the walls its wall ghosts stand in
    if pair & {"ghost_deck", "ghost_wall_hi", "ghost_wall_lo", "ghost_keyhead"} and pair & {
            "deck", "deck_white", "fret_board", "fret_leds"}:
        return True
    if pair == {"deck", "deck_white"}:      # one print, two filaments: they share faces
        return True
    if "bend_brg" in pair and pair & bends - {"bend_brg"}:      # each 688 on its axle
        return True
    if "rod" in pair and "endplate" in pair:
        return True
    if "anchor_m4" in pair and pair & {"ghost_wall_hi", "ghost_wall_lo", "wall_bar"}:
        return True                                  # (tapped into the bar)
    if "anchor" in pair and pair & {"ghost_wall_hi", "ghost_wall_lo"}:   # sized to THIS body
        return True
    if "anchor" in pair and pair & {"plug", "housing", "hb", "tie_spacer"}:
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
