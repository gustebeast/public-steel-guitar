"""PLANK BENCH -- one string's whole drive, screwed to a wooden plank (user, 2026-11-07).

String 1 (index 0) at its own scale length, with every piece of its hardware exactly where and
how the instrument has it: the SERVO42D with its shaft +Y, the 14T pulleys, the open GT2 belt
with its 90 deg twist and its clamp, the Tr8x2 screw on its 688 thrust bearing under the
pulley-collar, the brass H-nut carriage on its guide rod, the ball end under the nut's +X ear,
and the 688 bridge bearing the string turns over. ALL OF IT IS DRAWN AT THE INSTRUMENT'S WORLD
COORDINATES, so nothing here re-derives a position: the two printed parts below are only what
holds those parts up off a plank.

    HEAD      the instrument's own motor bay (motor_bank's coupon, on string 1's motor) + the crown
              tower. The motor is held down by its tee board's M4, as in the body. The crown is a Ø4 x 4 steel dowel (the stand-ins'
              91595A119) at the keyhead's break edge, NUT_BLOCK_X, string top at STRING_Z.
              The string goes over it and down to a bought guitar tuner, mounted in the plank
              itself well -X of the head (user) -- so the head fixes the crown-to-motor spacing,
              and the plank fixes nothing that matters.
    STATION   the screw station: bridge-bearing pocket and axle bore, changer room, screw rail
              (688 seat, lip, boss passage -- screw_rail's diameters), guide-rod socket, and
              the open pulley bay the belt leaves by. Base flanges both sides in Y take the
              string's pull (147 N at STRING_Z, 72 mm over the plank) down to four wood screws.
              NO CAP (user, 2026-11-07): the 688 drops into its pocket from +Z and the Ø8 axle
              slides through it along Y. Nothing over the guide rod: its press fit in the slab
              bore holds it, as it does the instrument's (whose plug is only a backstop).

ONE STRING, STRAIGHT. The instrument's string 1 fans 13.5 in Y over its length; here the crown
is on the string's bridge Y instead, so the string runs straight down the plank. That changes
its speaking length by 0.15 mm (607.15 -> 607.00), well under how well a plank is marked out.

THE PLANK: its top is Z_PLANK (the motor's floor less the bases' thickness), and the +Y faces of
both bases are one plane, Y_EDGE -- lay them flush with the plank's +Y edge and they are in line.
Crown dowel to bridge-bearing axle is SCALE_SPAN along X: that is the only measurement to make.
PRINT POSES: the head BASE DOWN (+Z up), the bay's own overhangs being the coupon's. The STATION
builds -X off its +X face, as the instrument's bridge endplate does (user, 2026-11-07): base down
left its room ceiling cantilevered round the holes through it, which print_check's inscribed-circle
span read as a 7.4 bridge. Built -X the room, the lane and the rail run along the build and every
Z bore is a teardrop, exactly screw_rail's. PETG-GF. No tee dummy: the real tee board holds the motor down.

    py -3.12 -m src.plank_bench      -> coupons/plank_head.step, plank_station.step, ...
"""

from __future__ import annotations

import math
import pathlib

import cadquery as cq

from . import dimensions as D
from . import components as C
from . import screw_rail as SR
from . import belt_tensioner as BTn
from .helpers import box_at, cyl, cyl_x, cyl_y
from cadkit.supports import printable_bore
from cadkit.fasteners import M4

I = 0                                            # string 1
SX, SY = D.screw_x(I), D.string_y(I)             # -12.0, 42.75: the screw's axis
RX = D.guide_rod_x(I)                            # -20.0: the guide rod
UP = (0.0, 0.0, 1.0)                             # the head builds +Z
ST_UP = (-1.0, 0.0, 0.0)                         # the station builds -X, as bridge_endplate

# ── THE PLANK AND THE BASES ──────────────────────────────────────────────────────────────
BASE_T = 6 * D.BEAD                              # 4.8 under everything, and over the countersinks
# AS LOW ON THE WOOD AS IT GOES (user, 2026-11-07): the screw pulley's bed flange FLOOR_GAP over
# the station's floor. The motor stands on the plank too, so it sits higher against the screw pulley
# than the instrument's motor bank holds it -- see MZ.
FLOOR_GAP = 1.0
_PULLEY_BOT = D.screw_pulley_z(0) - (D.PULLEY_GAP / 2 + D.PULLEY_FLANGE_T + (D.PULLEY_FLANGE_OD - D.PULLEY_OD) / 2)
Z_PLANK = _PULLEY_BOT - FLOOR_GAP - BASE_T
# The wood screw is the watering-backpack's (user): #8 flat head, Ø4.0 shank, Ø9.3 MEASURED head,
# 82 deg. A 45 deg countersink is steeper than the head, so it lands at the mouth and sits flush.
WOOD_CLR_D, WOOD_CSK_D = 4.5, 9.3 + 0.3
WOOD_CSK_DEPTH = (WOOD_CSK_D - WOOD_CLR_D) / 2.0  # 2.55
assert WOOD_CSK_DEPTH < BASE_T - D.MIN_WALL_2P, "the countersink eats the base"

# ── THE STATION ──────────────────────────────────────────────────────────────────────────
WALL = 6 * D.BEAD                                # 4.8: the room's side walls
LANE = 8 * D.BEAD                                # 6.4: the room's half-width, the nut's 10.5 AF + 1.0 a side
# THE BAY, under the rail: one lane the whole length, open -X for the belt, its walls standing full
# height either side -- so the rail and the room over it are BRIDGES between two walls, base down,
# and nothing hangs off -X (user, 2026-11-07: a bay cut wide below z -40 left them cantilevered).
# Its +Y side is the clamp's: near the top of travel the clamp's half A reaches y 50.12 inside the
# station's X span (and z -40.1); the belt itself spans y 37.9..47.6 there.
# Its -Y side is the thrust 688's: the bearing slides in along the bay from -X and up into the
# rail's seat, so the bay is a bearing wide (user, 2026-11-08).
LANE_HI = 11 * D.BEAD                            # 8.8: the bay's +Y half-width (1.43 past the clamp)
LANE_LO = 21 * D.BEAD / 2                        # 8.4: the bay's -Y half-width, the 688's 8.0 + 0.4
assert min(LANE_LO, LANE_HI) >= D.BRG688_OD / 2 + 0.4 - 1e-9, "the thrust 688 cannot slide in along the bay"
WALL_HI = 4 * D.BEAD                             # 3.2: the bay's walls outside it
Y0, Y1 = SY - LANE_LO - WALL_HI, SY + LANE_HI + WALL_HI   # 31.15 .. 54.75, the station's Y faces
FLANGE = 11.6                                    # the station's base past its walls, both sides in Y
Y_EDGE = Y1 + FLANGE                             # every base's +Y face: the plank's edge
X0 = RX - 7.2                                    # -27.2: the station's -X face, past the rod's socket
X1 = D.BRIDGE_X + 4.0                            # 4.0: the back wall's inner face
X1B = X1 + WALL                                  # 8.8
SLAB_TOP = 12.2 + 2 * D.BEAD                     # 13.8: two beads over the axle bore's crown

# the screw rail, at screw_rail's own numbers -- round bores, since this one builds +Z
# THE BENCH STAYS AS PRINTED (user, 2026-11-08: reprint the yoke only). Both stations were
# printed with the drawing's 15.0 nut, before the measured 13.5 brought the instrument's thrust
# stack up 1.5 (dimensions.NUT_BOT_MIN). Their stack features sit PRINTED_DROP under the
# instrument's: the bench nut just has 1.5 more fall onto its 688, which tuning never uses.
PRINTED_DROP = 15.0 - D.NUT_H                    # 1.5
RAIL_BOT, RAIL_TOP = SR.BOT - PRINTED_DROP, SR.TOP - PRINTED_DROP   # -31.85 .. -22.55
LEDGE_TOP = SR.LEDGE_TOP - PRINTED_DROP
BRG_TOP_Z = D.SUPPORT_BRG_Z - PRINTED_DROP       # the 688's top face
BRG_BOT_Z = D.SUPPORT_BRG_BOT - PRINTED_DROP
SOCKET_Z = LEDGE_TOP + 2 * D.BEAD                # -23.35: the rod's bottom, 1.6 over the lip band
ROD_TOP = SOCKET_Z + D.GUIDE_ROD_L               # 6.45
ROD_BORE = D.GUIDE_ROD_D + D.GUIDE_ROD_FIT       # 3.65, round

# the bridge bearing: a 688 on an Ø8 shaft, as in the instrument, dropped into a pocket open on
# top, the shaft then slid through it along Y (user, 2026-11-07)
BX, BZ = D.BRIDGE_AXLE_X, D.BRIDGE_BEARING_Z     # (-8, 8)
BRG_POCKET = (BX - D.BRIDGE_BEARING_OD / 2 - 0.5, D.BRIDGE_X + 1.6, 2.9, -0.5)   # x0, x1, half-Y, z0
AXLE_BORE = D.BRIDGE_AXLE_D + 0.4                # 8.4, a teardrop through both Y faces: any Ø8
                                                 # shaft over the station's width, the bought 100 too
assert BZ + AXLE_BORE / 2 <= SLAB_TOP - 2 * D.BEAD + 1e-9, "under two beads over the axle bore"
SCREW_HOLE_D = 12.7                              # 1/2 in: the pulley's Ø11 flange and the drill
assert D.CHANGER_CEIL_Z < BRG_POCKET[3], "no floor between the room and the bearing"

# ── THE HEAD ─────────────────────────────────────────────────────────────────────────────
MX, MY, _MZ = D.motor_pos(I)
MZ = Z_PLANK + BASE_T + 42.3 / 2                 # the motor pulley's centre: the can stands on the head's floor.
MOTOR_RISE = MZ - _MZ                            # ~15 over the instrument's: the belt runs ~1.5 deg off level
# THE MOTOR BAY IS THE INSTRUMENT'S (user, 2026-11-07): motor_bank's own coupon bay, built for
# string 1's motor, lifted MOTOR_RISE onto the plank. The motor drops in and its CAN tee board (or the
# coupon's printed dummy) holds it down with the one M4 into the bay's post, exactly as in the body.
# the crown: the keyhead's break edge, the string's TOP on STRING_Z
CROWN_X = D.NUT_BLOCK_X                          # -615
CROWN_Z = D.STRING_Z - D.STRING_GAUGE[I] - D.NUT_PIN_D / 2.0
MX_Y0 = 35.25 - D.MOTOR_BODY_L                  # the motor's back (faceplate y 35.25)
TOWER_X0 = CROWN_X - 5.0                         # -620; it runs +X to the bay's -X wall
TOWER_Y0, TOWER_Y1 = SY - 7.2, SY + 7.2
TAB = 16 * D.BEAD                                # 12.8: a wood-screw tab, the screw in its middle
SCALE_SPAN = BX - CROWN_X                        # 607.0, crown dowel to bearing axle

# ── THE AXIAL RIG (user, 2026-11-08) ─────────────────────────────────────────────────────
# On the rig above the string pulls the nut's +X ear, 8 off the screw's axis: 147 N x 8 mm tips
# the nut on its thread, and a tipped Tr8 nut grabs (the user, by hand, on a loose nut). So a
# SECOND STATION with the string's pull ON THE SCREW'S AXIS: a printed YOKE bolted to the nut
# through BOTH its ears, carrying the ball end over the screw's tip and its own guide-rod hole,
# and the bridge bearing moved -X so the string drops off its tangent straight down the axis.
# The screw, its pulley, the belt and the motor stay exactly where they are; only the crown-
# to-bearing span changes (SCALE_SPAN_AX). Not for the instrument: it spends Y and Z freely.
YK_H = 20 * D.BEAD                               # 16.0: the yoke over the nut's flange top
YK_R0 = 15 * D.BEAD                              # 12.0: the underside of its roof, the ball end's seat
YK_HX, YK_HY = 15 * D.BEAD, 15 * D.BEAD / 2      # 12.0 x 6.0 half-sizes: the flange's 22 x 10.5 and a wall
YK_CAV = D.SCREW_OD + 0.8                        # 8.8: the screw's tip rises into it
# THE NUT'S LIP (user, 2026-11-08): a Ø10.2 x 1.5 lip stands on the flange's top face, so the
# yoke's -Z face takes a ROUND recess for just the lip (user, 2026-11-08), which also registers the
# yoke concentric with the screw. It leaves 1.1 to each M3 tap hole
# and 0.7 to the Y faces, over its 1.8 depth only. The yoke keeps its
# 12 x 6 so it is the ONLY part to reprint: the axial station is unchanged.
YK_LIP_D = D.NUT_LIP_D + 0.5                     # 10.7: a sliding register on the Ø10.2 lip (10.6
                                                 # printed a bit too tight: user, 2026-11-09)
YK_LIP_HY = 5.4                                  # the plain station's relief half-width
YK_LIP_L = D.NUT_LIP_L + 0.3                     # 1.8
STN_LIP_D = 2 * YK_LIP_HY                        # the plain station's ceiling relief over the lip
STN_LIP_L = D.NUT_LIP_L + 0.3                    # 1.8: leaves 0.9 under the bearing's pocket
YK_PROTRUDE = D.SCREW_TOP_Z - (D.NUT_TOP_Z - D.CARRIAGE_TRAVEL)   # 6.75: tip over the flange, bottom of travel
assert YK_R0 - D.STRING_NUT_D >= YK_PROTRUDE + 1.0 - 1e-9, "the screw's tip reaches the ball end"
# THE M3s SELF-TAP (user, 2026-11-08: a prototype is not worth inserts). Straight Ø3.2 holes
# (cadkit's M3 self-tap) up from the -Z face; the thinner wall to the lip's recess is then 1.1,
# so it needs no relief slot either.
YK_TAP_D = BTn.M3.selftap_d                      # 3.2: drawn for an UPRIGHT hole (round, nozzle-made: it
                                                 # prints ~0.6 under, ~2.6, and the M3 taps it)
YK_TAP_SIDE_D = YK_TAP_D - 0.4                   # 2.8: a SIDEWAYS one (a teardrop) prints BIGGER than a
                                                 # round one: 3.2 printed a clearance hole in the counter
                                                 # yoke (user, 2026-11-10). cadkit f862c04's rule,
                                                 # holes.as_printed_d (TEARDROP_OVERSIZE 0.4) -- use it
                                                 # once that is propagated
YK_SCREW_L = BTn.SCREW_L                         # M3 x 12 socket head (the belt clamp's): ear 3.5, 8.5 bites
YK_TIP = YK_SCREW_L - D.NUT_FLANGE_T + 0.6       # 9.1: the hole's depth, the tip's 8.5 and air
assert D.NUT_HOLE_DX - YK_TAP_D / 2 - YK_LIP_D / 2 >= D.MIN_WALL - 1e-9, "tap hole into the lip's recess"
assert D.NUT_HOLE_DX - YK_TAP_D / 2 - YK_CAV / 2 >= 1.2 - 1e-9, "tap hole into the screw's cavity"
ROD_DY = -15 * D.BEAD                            # -12.0: the guide rod, out -Y past the flange and the rail's seat
# THE ROD'S HOLE: 4.0 printed needing "a fair bit of force" (user, 2026-11-08) -- a small hole
# along the build prints under, and 16 of it binds on any tilt. Now 4.3, bearing only on a LAND
# at each end; between them a Ø5.0 relief, entered and left by 45 deg cones (the -Z one is a
# ceiling in the +Z -> -Z print). 0.8 of diametral play over the arm's 12 is ±1 deg of yaw.
YK_ROD_D = D.GUIDE_ROD_D + 0.8                   # 4.3: a sliding fit; it only takes the screw's torque
YK_ROD_RELIEF_D = 5.0
YK_ROD_LAND = 4.0                                # each end's bearing length
ARM_R = (D.GUIDE_ROD_D + 0.5) / 2 + 3 * D.BEAD   # 4.4: the rod's boss, unchanged (station room)
# The boss runs the yoke's full height: the yoke prints roof-down, and a short arm would hang
# off the body in that print (print_check, 2026-11-08). The rod spans the whole channel and is
# held at both ends: a shallow socket in the floor and the bore into the slab over the room.
ARM_H = YK_H
CLR = 0.6                                        # the room round the yoke
ROOM_HY = YK_HY + CLR                            # 6.6
ARM_Z0 = D.NUT_TOP_Z - D.CARRIAGE_TRAVEL - CLR  # -12.15: the arm's channel floor
ARM_Y0 = SY + ROD_DY - ARM_R - CLR              # the channel's -Y side
ROD_SOCK = 3 * D.BEAD                            # 2.4: just a pocket to locate its -Z end (user, 2026-11-08)
ROD_BOT = ARM_Z0 - ROD_SOCK                      # -14.55
ROD_TOP2 = ROD_BOT + D.GUIDE_ROD_L               # 15.25: 2.45 into the slab over the room
CEIL_AX = D.NUT_TOP_Z + YK_H                     # 12.8: the room's ceiling = the yoke's top stop
G0 = D.STRING_GAUGE[I]
BX_AX = SX - D.BRIDGE_BEARING_OD / 2 - G0 / 2    # the bearing's +X tangent drops the string ON the axis
POCKET_Z0 = CEIL_AX + 3 * D.BEAD                 # 15.2: a slab between the room and the bearing
BZ_AX = POCKET_Z0 + 0.5 + D.BRIDGE_BEARING_OD / 2   # 23.7
SLAB_TOP_AX = BZ_AX + AXLE_BORE / 2 + 2 * D.BEAD    # 29.5
BRG_HY = D.BRIDGE_BEARING_W / 2 + 0.4            # 2.9
STR_HOLE_D = 2.0                                 # the string's hole up the slab: room for a .070 and a fumble
X0_AX = BX_AX - D.BRIDGE_BEARING_OD / 2 - 0.5 - BRG_HY - 3 * D.BEAD   # the gable's ridge, then 2.4
Y0_AX = ARM_Y0 - WALL_HI
# ITS +X FACE IS THE SCREW'S SEAT AND THREE BEADS (user, 2026-11-08: "rigidity isn't too big a deal
# now"): nothing +X of the axis needs it -- the yoke slides in from +X and may stand 1.5 proud of it,
# the bay and the room run out through it, and the string goes up the axis, not out a slit.
X1_AX = SX + (D.SUPPORT_BRG_OD + 0.2) / 2 + 3 * D.BEAD   # -1.5
SCALE_SPAN_AX = BX_AX - CROWN_X                  # 594.8

OUT = pathlib.Path(__file__).resolve().parents[1] / "coupons"
_MAIN_COUPONS = pathlib.Path(__file__).resolve().parents[2] / "public-steel-guitar" / "coupons"


def _box(x0, x1, y0, y1, z0, z1):
    return box_at(x1 - x0, y1 - y0, z1 - z0, x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(z0 + z1) / 2)


def _zbore(d, x, y, z0, z1, up=UP):
    return printable_bore(d, z1 - z0, axis_point=(x, y, z0), axis_dir=(0.0, 0.0, 1.0), print_up=up)


def _wood_screw(x, y, up=UP, zp=None):
    """Clearance through the base and the 45 deg countersink from its top face (a 45 deg cone
    lying sideways is AT the overhang rule, so it needs no teardrop of its own). zp: the plank's
    top (Z_PLANK; the X rig's is Z_PLANK_X)."""
    zp = Z_PLANK if zp is None else zp
    zt = zp + BASE_T
    clr = _zbore(WOOD_CLR_D, x, y, zp - 1.0, zt + 1.0, up)
    csk = cq.Workplane("XY").add(cq.Solid.makeCone(WOOD_CLR_D / 2.0, WOOD_CSK_D / 2.0, WOOD_CSK_DEPTH,
                                                   pnt=cq.Vector(x, y, zt - WOOD_CSK_DEPTH)))
    return clr.union(csk).union(_zbore(WOOD_CSK_D, x, y, zt - 0.01, zt + 60.0, up))


# ═════════════════════════════════════════════════════════════════════════════════════════
def station() -> cq.Workplane:
    """Built -X (ST_UP) off its +X face, X1B: every Z bore below is a teardrop pointing -X."""
    zb = Z_PLANK + BASE_T
    s = _box(X0, X1B, Y0 - FLANGE, Y_EDGE, Z_PLANK, zb)                                  # base
    s = s.union(_box(X0, X1B, Y0, Y1, zb - 0.01, SLAB_TOP))                          # the block
    # the bay: the lane under the rail, open -X for the belt
    s = s.cut(_box(X0 - 1.0, X1, SY - LANE_LO, SY + LANE_HI, zb, RAIL_BOT))
    # the changer room: over the rail, under the slab, open -X for the hand that spins the nut on
    s = s.cut(_box(X0 - 1.0, X1, SY - LANE, SY + LANE, RAIL_TOP, D.CHANGER_CEIL_Z))
    # ...and open +X through the back wall: the ear the string is threaded up through is 8 mm in
    # from there (user, 2026-11-07)
    s = s.cut(_box(X1 - 1.0, X1B + 1.0, SY - LANE, SY + LANE, RAIL_TOP, D.CHANGER_CEIL_Z))
    # the nut's Ø10.2 x 1.5 LIP (user, 2026-11-08) rises past the flange top into the ceiling at
    # the top of travel: a relief over it, so the flange still stops on the ceiling as before
    s = s.cut(_zbore(STN_LIP_D, SX, SY, D.CHANGER_CEIL_Z - 0.01, D.CHANGER_CEIL_Z + STN_LIP_L, ST_UP))
    # THE SCREW GOES IN FROM BELOW with its pulley on, as in the instrument: a 1/2 in hole through
    # the floor, which is also the guide to drill the plank through
    s = s.cut(_zbore(SCREW_HOLE_D, SX, SY, Z_PLANK - 1.0, zb + 1.0, ST_UP))
    # the rail's seat, lip and boss passage: screw_rail.seat_cutter's diameters and its teardrops
    s = s.cut(_zbore(D.SUPPORT_BRG_OD + 0.2, SX, SY, RAIL_BOT - 1.0, BRG_TOP_Z + 1e-3, ST_UP))
    s = s.cut(_zbore(SR.SEAT_LEDGE_D, SX, SY, RAIL_BOT - 1.0, LEDGE_TOP, ST_UP))
    s = s.cut(_zbore(SR.NUT_PASS_D, SX, SY, LEDGE_TOP - 0.01, RAIL_TOP + 1.0, ST_UP))
    # the guide rod: blind socket in the rail, bore up through the slab
    s = s.cut(_zbore(ROD_BORE, RX, SY, SOCKET_Z, RAIL_TOP + 1.0, ST_UP))
    s = s.cut(_zbore(ROD_BORE, RX, SY, D.CHANGER_CEIL_Z - 1.0, SLAB_TOP + 1.0, ST_UP))
    # the bridge bearing's pocket, open on top, and the string's slot down to the ear
    bx0, bx1, bh, bz0 = BRG_POCKET
    # its -X end is the ROOF in the print (ST_UP): gabled to a ridge like the instrument's slot
    # (bridge_endplate's house pentagon), not a flat 5.8 bridge whose sag drags on the race
    s = s.cut(cq.Workplane("XY", origin=(0.0, 0.0, bz0))
              .polyline([(bx1, SY - bh), (bx1, SY + bh), (bx0, SY + bh), (bx0 - bh, SY), (bx0, SY - bh)])
              .close().extrude(SLAB_TOP + 1.0 - bz0))
    s = s.cut(_box(D.string_anchor_x(I) - 1.6, D.BRIDGE_X + 1.6, SY - 1.6, SY + 1.6,
                   D.CHANGER_CEIL_Z - 1.0, bz0 + 0.5))
    # the axle's bore, out through both faces, cut last
    s = s.cut(printable_bore(AXLE_BORE, Y1 - Y0 + 2.0, axis_point=(BX, Y0 - 1.0, BZ),
                             axis_dir=(0.0, 1.0, 0.0), print_up=ST_UP))
    # wood screws, two down each flange, clear of the belt
    for x in (X0 + 6.4, X1B - 6.4):
        for y in (Y0 - FLANGE / 2, Y1 + FLANGE / 2):
            s = s.cut(_wood_screw(x, y, ST_UP))
    return s


def station_axial() -> cq.Workplane:
    """The axial rig's station. Built -X (ST_UP) like station(): the room and the rod's
    channel run straight through in X, so in the print they are shafts, not roofs."""
    zb = Z_PLANK + BASE_T
    s = _box(X0_AX, X1_AX, Y0_AX - FLANGE, Y_EDGE, Z_PLANK, zb)
    s = s.union(_box(X0_AX, X1_AX, Y0_AX, Y1, zb - 0.01, SLAB_TOP_AX))
    s = s.cut(_box(X0_AX - 1.0, X1_AX + 1.0, SY - LANE_LO, SY + LANE_HI, zb, RAIL_BOT))          # the bay
    # the room: the nut and yoke slide in from +X; it runs out -X too
    s = s.cut(_box(X0_AX - 1.0, X1_AX + 1.0, SY - ROOM_HY, SY + ROOM_HY, RAIL_TOP, CEIL_AX))
    # the rod arm's channel, -Y of the room: its floor is the arm's bottom of travel
    s = s.cut(_box(X0_AX - 1.0, X1_AX + 1.0, ARM_Y0, SY - ROOM_HY + 0.01, ARM_Z0, CEIL_AX))
    s = s.cut(_zbore(SCREW_HOLE_D, SX, SY, Z_PLANK - 1.0, zb + 1.0, ST_UP))
    s = s.cut(_zbore(D.SUPPORT_BRG_OD + 0.2, SX, SY, RAIL_BOT - 1.0, BRG_TOP_Z + 1e-3, ST_UP))
    s = s.cut(_zbore(SR.SEAT_LEDGE_D, SX, SY, RAIL_BOT - 1.0, LEDGE_TOP, ST_UP))
    s = s.cut(_zbore(SR.NUT_PASS_D, SX, SY, LEDGE_TOP - 0.01, RAIL_TOP + 1.0, ST_UP))
    # the guide rod: a shallow pocket in the channel floor, its press bore into the slab over
    # the room, and a clear passage on up to the top to drop it in and push it home
    ry = SY + ROD_DY
    s = s.cut(_zbore(ROD_BORE, SX, ry, ROD_BOT, ARM_Z0 + 0.01, ST_UP))
    s = s.cut(_zbore(ROD_BORE, SX, ry, CEIL_AX - 0.01, ROD_TOP2 + 0.5, ST_UP))
    s = s.cut(_zbore(ROD_BORE + 0.6, SX, ry, ROD_TOP2 + 0.4, SLAB_TOP_AX + 1.0, ST_UP))
    # the bridge bearing's pocket, gabled at -X (the print's roof), open on top
    bx0, bx1 = BX_AX - D.BRIDGE_BEARING_OD / 2 - 0.5, SX + 1.0
    s = s.cut(cq.Workplane("XY", origin=(0.0, 0.0, POCKET_Z0))
              .polyline([(bx1, SY - BRG_HY), (bx1, SY + BRG_HY), (bx0, SY + BRG_HY), (bx0 - BRG_HY, SY),
                         (bx0, SY - BRG_HY)]).close().extrude(SLAB_TOP_AX + 1.0 - POCKET_Z0))
    # the string's hole, ON the axis from the room up into the bearing's pocket: no slit out +X
    # (user, 2026-11-08) -- the string is threaded up it, -Z to +Z, from the yoke
    s = s.cut(_zbore(STR_HOLE_D, SX, SY, CEIL_AX - 1.0, POCKET_Z0 + 0.5, ST_UP))
    s = s.cut(printable_bore(AXLE_BORE, Y1 - Y0_AX + 2.0, axis_point=(BX_AX, Y0_AX - 1.0, BZ_AX),
                             axis_dir=(0.0, 1.0, 0.0), print_up=ST_UP))
    for x in (X0_AX + 6.4, X1_AX - 6.4):
        for y in (Y0_AX - FLANGE / 2, Y1 + FLANGE / 2):
            s = s.cut(_wood_screw(x, y, ST_UP))
    return s


# ═════════════════════════════════════════════════════════════════════════════════════════
# THE X RIG (user, 2026-11-08): the screw LYING ALONG X, pointing at the head, the string straight
# off the yoke's roof to the crown. Nothing but the screw, the nut and the thrust 688 -- no bridge
# bearing, no guide rod -- so whatever friction is left is the nut on the screw.
#
# The stack is the axial rig's, AS PRINTED (PRINTED_DROP: the user's pulley is the printed one),
# turned local +Z -> world -X: world x = XR_OFF - z_local, the axis at y SY, z XR_ZA.
#   XR_ZA   the string's centre on the crown, so the string runs DEAD LEVEL from the yoke's roof to
#           the crown: any slope is a side load on the roof, a tilt on the nut, what this rig removes.
#   XR_OFF  crown to the yoke's roof at MID-travel = the scale span, so the string tunes to pitch at
#           the instrument's tension.
# The frame is an open-topped box on the axial station's four plank holes: the RAIL WALL (the 688's
# seat, screw_rail's bores turned along X), the END WALL (-X; the yoke's top stop, the string's slot
# open on top), and two side walls. The +Y wall is what stops the yoke turning (its corner, 12 off
# the axis, meets it after ~3 deg); the yoke's arm runs in a slot in the -Y wall, rod-less.
XR_ZA = D.STRING_Z - D.STRING_GAUGE[I] / 2.0     # 15.81
# THE X RIG'S PLANK IS ITS OWN, 51 HIGHER (user, 2026-11-10: "lower everything such that the motor
# sits level with the wood"). Z_PLANK was the vertical screw's (the pulley over the station's
# floor); lying along X nothing needs that height, and the counter post tore on a layer line at
# its base with the springs' pull 67 over it. Now the in-line motor rests on its block's base pad
# (MOTOR_SEAT_CLR for the driver housing's 0.1 below the can) and that sets the axis' height over
# the wood: 26.25, was 72.2. The head and crown tower are gone too (user): a bought axle bar on
# the plank is the string's break, its top at the axis' height.
MOTOR_SEAT_CLR = 0.3
Z_PLANK_X = XR_ZA - D.MOTOR_SQ / 2 - MOTOR_SEAT_CLR - BASE_T
XR_ROOF_MID = D.NUT_TOP_Z + YK_H - D.CARRIAGE_TRAVEL / 2.0   # the yoke's roof, local z, mid-travel
XR_OFF = CROWN_X + SCALE_SPAN + XR_ROOF_MID      # world x of local z 0
XR_WALL = 6 * D.BEAD                             # 4.8: each buttress
XR_TOP = XR_ZA + YK_HX + 2 * D.BEAD              # 29.41: the walls' top, past the yoke's corners


def _xr_x(z):
    """World x of a local (axial-rig) z."""
    return XR_OFF - z


def _xbore(d, z0, z1):
    """A local Z bore z0..z1 about the screw's axis, turned along X: a teardrop for the +Z build."""
    return printable_bore(d, z1 - z0, axis_point=(_xr_x(z1), SY, XR_ZA), axis_dir=(1.0, 0.0, 0.0),
                          print_up=UP)


# SLIMMED (user, 2026-11-08: "save plastic ... make the support angled"). What is left:
#   the RAIL WALL, the main plate: 9.3 (screw_rail's) round the 688's seat, 4.8 under it, a 45 deg
#     step between them.
#   two BUTTRESSES, the side walls cut to a triangle from the rail wall's top down to the base at
#     XR_X0: the string pulls the wall -X, and they take that in compression. Their slope faces up
#     in the +Z print.
#   NOTHING STOPS THE YOKE TURNING (user, 2026-11-08: "I will hold it in place"): no rod, no band.
#   the BASE, a U under the walls and the four wood screws; nothing under the room.
# NO TOP STOP any more: at the old stop the nut still has ~12 of thread on the screw, so a hand
# raising past it can wind the nut off the screw's end.
XR_X1 = _xr_x(RAIL_BOT)                          # the rail wall's +X face: the 688's seat mouth
XR_XR = _xr_x(RAIL_TOP)                          # the rail wall's -X face
XR_RAIL_T2 = 6 * D.BEAD                          # 4.8: the rail wall under the seat
XR_SEAT_Z0 = XR_ZA - (D.SUPPORT_BRG_OD + 0.2) / 2 - 2 * D.BEAD   # the thick part's underside
XR_X0 = XR_XR - 37.8                             # the buttresses' foot
# CENTRED ON THE SCREW (user, 2026-11-08): the rail wall and both buttresses symmetric about SY, so
# the 688's seat is in the middle of the plate. The base too, its +Y face still the plank's edge.
# WIDENED (user, 2026-11-10): at 11.4 the buttresses stopped the nut, its M3s and the yoke held
# with the ears HORIZONTAL (Y) short of the screw's full travel. "As far as we can fit, the same
# width as the motor wall": the motor's 21.15 would leave the counter springs 0.55, so their 1.0
# (asserted at CS_DY) sets it.
XR_HW = 20.7                                     # the frame's half-width
assert XR_HW - XR_WALL >= D.NUT_FLANGE_L / 2 + CLR - 1e-9, "the nut's ears, horizontal, hit the buttresses"
XR_Y0, XR_Y1 = SY - XR_HW, SY + XR_HW            # 31.35 .. 54.15
# THE PLANK'S HOLES ARE THE SECOND PRINT'S (user, 2026-11-08: reuse the drill points): x -7.9 and
# 26.07, y 16.75 and 60.55. The base reaches them with a tab each off the strips under the walls.
XR_SCREWS_X = (X1_AX - 6.4, XR_X1 - 6.4)         # -7.9, 26.07
XR_SCREWS_Y = (Y0_AX - FLANGE / 2, Y1 + FLANGE / 2)   # 16.75, 60.55
XR_TAB = 6.4                                     # a tab's half-length in X round its screw
assert XR_SCREWS_Y[0] + WOOD_CSK_D / 2 <= XR_Y0 - 1e-9, "a -Y screw head under the buttress"
# THE +Y SIDE no longer has room outside the walls (a head there would be past the plank's edge):
#   foot end   the old hole (-7.9, 60.55), the +Y buttress's foot trimmed back off it so the key
#              goes straight down (_wood_screw's access bore).
#   rail end   a NEW hole (user, 2026-11-10: "widen + new hole") INSIDE the open room, just -X of
#              the rail wall, on a pad off the +Y wall's strip -- reached down through the open top.
XR_IN_HOLE = (XR_XR - WOOD_CSK_D / 2 - 1.0, SY + XR_HW - XR_WALL - WOOD_CSK_D / 2 - 1.6)
XR_HOLES = [(XR_SCREWS_X[0], XR_SCREWS_Y[0]), (XR_SCREWS_X[1], XR_SCREWS_Y[0]),
            (XR_SCREWS_X[0], XR_SCREWS_Y[1]), XR_IN_HOLE]
XR_FOOT_X = XR_SCREWS_X[0] + WOOD_CSK_D / 2       # the +Y buttress starts here, past the old hole
# the key goes down past the nut with its ears VERTICAL (its 10.5 flat across Y): a 2.5 key's
# ~3.5 of shank clear of that
assert XR_IN_HOLE[1] - 3.5 / 2 >= SY + 10.5 / 2 + 0.5 - 1e-9, "the key can't pass the nut to the room's screw"
assert XR_X0 <= XR_SCREWS_X[0] - WOOD_CSK_D / 2 - 1.6 + 1e-9, "under 1.6 of base past the -X screws' countersinks"


def _xz_prism(pts, y0, y1):
    """A polygon in XZ, extruded y0..y1."""
    return (cq.Workplane("XZ", origin=(0.0, y1, 0.0)).polyline(pts).close().extrude(y1 - y0))


def station_x() -> cq.Workplane:
    """The X rig's frame, built +Z (base down): every bore along X is a teardrop."""
    zb = Z_PLANK_X + BASE_T
    # base: the U -- the full footprint less the room's floor
    # base: strips under the walls, a pad under the rail wall, and a tab out to each screw
    s = _box(XR_X0, XR_X1, XR_Y0, XR_Y0 + XR_WALL, Z_PLANK_X, zb)
    s = s.union(_box(XR_X0, XR_X1, XR_Y1 - XR_WALL, XR_Y1, Z_PLANK_X, zb))
    s = s.union(_box(XR_XR, XR_X1, XR_Y0, XR_Y1, Z_PLANK_X, zb))
    for x in XR_SCREWS_X:
        s = s.union(_box(x - XR_TAB, x + XR_TAB, Y0_AX - FLANGE, XR_Y0 + 0.01, Z_PLANK_X, zb))
    fx, fy = XR_SCREWS_X[0], XR_SCREWS_Y[1]                                     # the foot's +Y hole's pad
    s = s.union(_box(fx - XR_TAB, fx + XR_TAB, fy - XR_TAB, Y_EDGE, Z_PLANK_X, zb))
    hx, hy = XR_IN_HOLE                                                         # the room's pad
    s = s.union(_box(hx - XR_TAB, XR_XR + 0.01, hy - XR_TAB, XR_Y1 - XR_WALL + 0.01, Z_PLANK_X, zb))
    # the rail wall: thick round the seat, thin under it, a 45 deg step
    s = s.union(_box(XR_X1 - XR_RAIL_T2, XR_X1, XR_Y0, XR_Y1, zb - 0.01, XR_TOP))
    dx = XR_X1 - XR_RAIL_T2 - XR_XR
    s = s.union(_xz_prism([(XR_XR, XR_TOP), (XR_X1 - XR_RAIL_T2 + 0.01, XR_TOP),
                           (XR_X1 - XR_RAIL_T2 + 0.01, XR_SEAT_Z0 - dx), (XR_XR, XR_SEAT_Z0)], XR_Y0, XR_Y1))
    # the -Y buttress
    tri = [(XR_X1 - XR_RAIL_T2 + 0.01, zb - 0.01), (XR_X1 - XR_RAIL_T2 + 0.01, XR_TOP), (XR_XR, XR_TOP),
           (XR_X0, zb - 0.01)]
    s = s.union(_xz_prism(tri, XR_Y0, XR_Y0 + XR_WALL))
    # the +Y buttress, the same triangle
    s = s.union(_xz_prism(tri, XR_Y1 - XR_WALL, XR_Y1).cut(
        _box(XR_X0 - 1.0, XR_FOOT_X, XR_Y1 - XR_WALL - 1.0, XR_Y1 + 1.0, zb, XR_TOP + 1.0)))
    # the rail wall's bores: screw_rail's seat, lip and boss passage, as printed
    s = s.cut(_xbore(D.SUPPORT_BRG_OD + 0.2, RAIL_BOT - 1.0, BRG_TOP_Z + 1e-3))
    s = s.cut(_xbore(SR.SEAT_LEDGE_D, RAIL_BOT - 1.0, LEDGE_TOP))
    s = s.cut(_xbore(SR.NUT_PASS_D, LEDGE_TOP - 0.01, RAIL_TOP + 1.0))
    for x, y in XR_HOLES:
        s = s.cut(_wood_screw(x, y, UP, Z_PLANK_X))
    return s


XR_PARTS = ("leadscrew_0", "nut_0", "yoke_0", "string_nut_0", "yoke_m3_lo_0", "yoke_m3_hi_0",
            "screw_pulley_0", "screw_bearing_0_0")


def assembly_x():
    """The X rig (scratch view scope): the axial stack turned along X, the nut mid-travel."""
    def turn(w):
        return w.rotate((0, 0, 0), (0, 1, 0), -90).translate((XR_OFF, 0.0, XR_ZA - SX))
    ax = dict(assembly(axial=True))
    dz = -D.CARRIAGE_TRAVEL / 2.0
    g = D.STRING_GAUGE[I]
    # NO HEAD (user, 2026-11-10): an Ø8 axle bar across the plank breaks the string, its top on the
    # string's underside -- the stand-in here; what holds it up is the user's
    out = [("plank_station_x", station_x()),
           ("crown_axle", cyl_y(8.0, 60.0, SY - 30.0, x=CROWN_X, z=XR_ZA - g / 2 - 4.0))]
    for nm in XR_PARTS:
        w = ax[nm]
        if nm in ("nut_0", "yoke_0", "string_nut_0", "yoke_m3_lo_0", "yoke_m3_hi_0"):
            w = w.translate((0, 0, dz))
        out.append(("x" + nm, turn(w)))
    g = D.STRING_GAUGE[I]
    a = (_xr_x(D.NUT_TOP_Z + dz + YK_R0 - D.STRING_NUT_D / 2), SY, XR_ZA)
    crown = (CROWN_X, SY, XR_ZA)
    st = _seg(a, crown, g / 2).union(_seg(crown, (CROWN_X - 40.0, SY, Z_PLANK_X + 2.0), g / 2))
    out.append(("string_0", st))
    return out


def yoke() -> cq.Workplane:
    """On the nut's flange, its axis at the origin, z 0 = the flange's top (the nut's own origin).
    Two M3 x 12 come up through the ears self-tapping into its -Z face; the ball end
    comes up the cavity and seats under the roof ON THE AXIS; the guide rod runs through the -Y boss."""
    y = _box(-YK_HX, YK_HX, -YK_HY, YK_HY, 0.0, YK_H)
    y = y.union(_box(-ARM_R, ARM_R, ROD_DY, -YK_HY + 0.01, 0.0, ARM_H))
    y = y.union(cyl(2 * ARM_R, ARM_H).translate((0.0, ROD_DY, 0.0)))
    y = y.cut(cyl(YK_ROD_D, ARM_H + 2.0, z=-1.0).translate((0.0, ROD_DY, 0.0)))
    dr = (YK_ROD_RELIEF_D - YK_ROD_D) / 2.0                                         # the cones' rise
    z0, z1 = YK_ROD_LAND, ARM_H - YK_ROD_LAND
    prof = [(0, z0), (YK_ROD_D / 2, z0), (YK_ROD_RELIEF_D / 2, z0 + dr),
            (YK_ROD_RELIEF_D / 2, z1 - dr), (YK_ROD_D / 2, z1), (0, z1)]
    y = y.cut(cq.Workplane("XZ").polyline(prof).close().revolve(360, (0, 0, 0), (0, 1, 0))
              .translate((0.0, ROD_DY, 0.0)))
    y = y.cut(cyl(YK_CAV, YK_R0 + 1.0, z=-1.0))                                     # the screw's tip
    y = y.cut(cyl(YK_LIP_D, YK_LIP_L + 1.0, z=-1.0))                                # the nut's lip
    # NO WINDOW, NO SLIT (user, 2026-11-08): the string goes in -Z to +Z, free end up through the
    # cavity from the -Z face (before the yoke goes on the nut) and out this hole on the axis,
    # until the ball end seats under the roof
    y = y.cut(cyl(STR_HOLE_D + 0.1, YK_H - YK_R0 + 2.0, z=YK_R0 - 1.0))   # 2.1 (user, 2026-11-08); the station's stays 2.0
    for sx in (-1, 1):
        x = sx * D.NUT_HOLE_DX
        y = y.cut(cyl(YK_TAP_D, YK_TIP + 1.0, z=-1.0).translate((x, 0.0, 0.0)))
    return y


# ═════════════════════════════════════════════════════════════════════════════════════════
# THE COUNTER-SPRING RIG (user, 2026-11-09): the X rig AS IT WAS -- head, motor, string to the
# crown -- with a COUNTER spring on the pulley side pulling the yoke +X, against the string. The
# nut's thread then carries string - spring (the pasted idea 3: a spring pulling the nut down to
# take load off the thread), set from ~50 % to 100 % of string 1's 147 N by ONE BOM SCREW, an
# M4 x 40 button head (the longest stock length, D.M4_BUTTON_STOCK_L). The 688 still sees
# string - spring, so it stays seated as long as the spring is under the string.
#
# The board ends at the X station's +X end, so the STATION MOVES -X by CS_DX (it and its whole
# stack, yoke and string end) and the spring's POST takes the station's old four plank holes.
#
#   TWO SPRINGS, one each side of the station in Y (CS_DY off the axis), both at the axis' height:
#     their pull is on the axis in Z and cancels in Y, so the yoke is not tipped (the reason for the
#     X rig), and nothing has to reach round or through the station. Two in parallel also halve the
#     travel that 50 -> 100 % takes (26.6 mm), which is what lets a 40 mm screw set it.
#   YOKE       the COUNTER YOKE (counter_yoke): the yoke on the nut with a bar across Y on its
#              roof, a pin each end for a spring's loop; the string out of its roof on the axis.
#   SLIDER     the same bar at the post end; an M4 insert on the axis, as a CAPTIVE NUT (SL_LIP).
#   POST       a wall with the M4 x 40 through it, head in a counterbore on its +X face (the board's
#              end: a 2.5 key from +X). Turning it in draws the slider +X. A deck under the slider
#              stops it turning with the screw.
SPR_L0 = 127.0                                   # 9654K634: 5" inside loop to inside loop, unloaded
SPR_OD = 25.4
SPR_WIRE = 0.105 * 25.4                          # 2.67
SPR_K = 7.9 * 4.448222 / 25.4                    # 1.383 N/mm, each
SPR_F0 = 4.0 * 4.448222                          # 17.8 N each: the initial tension (its 4 lbf minimum load)
N_SPR = 2
T_FULL = 147.0                                   # string 1 at pitch


def spring_stretch(f):
    """mm of stretch past free length for a total pull of f N, the springs in parallel."""
    return (f - N_SPR * SPR_F0) / (N_SPR * SPR_K)


def spring_pull(stretch):
    return N_SPR * (SPR_F0 + SPR_K * stretch)


PIN_D = 10.0                                     # the loop's pin: 2.4 MPa in bending at 147 N
PIN_GAP = 3.2                                    # the loop's wire (2.67) sits in this, under the head
PIN_HEAD_D = 15.0
PIN_Z0 = XR_ZA - PIN_GAP / 2                     # the pin's root: the wire's centre at the axis' height
PIN_PAD = PIN_HEAD_D / 2 + 1.0                   # 8.5: the pin's platform, half-length and half-width
# the springs' Y offset: clear of the station's walls (11.4) and the yoke's guide-rod arm (16.35 out -Y)
# 34.4, was 30.5 (user, 2026-11-09: the IN-LINE MOTOR): the springs clear the motor's 42.3 can,
# which now stands on the screw's axis past the rail wall (assembly_inline).
CS_DY = 34.4
assert CS_DY - SPR_OD / 2 >= D.MOTOR_SQ / 2 + 0.5 - 1e-9, "a spring rubs the in-line motor"
assert CS_DY - SPR_OD / 2 >= XR_HW + 1.0 - 1e-9, "a spring rubs the station"
assert CS_DY - SPR_OD / 2 >= -ROD_DY + ARM_R + 0.5 - 1e-9, "the -Y spring rubs the yoke's arm"
BAR_L = 2 * PIN_PAD                              # 17: both bars' run along X
BAR_HW = CS_DY + PIN_PAD                         # 39: their half-length in Y
BAR_Z0 = PIN_Z0 - 15 * D.BEAD                    # 2.2: their underside (12 under the pins)
HUB_HW = 10.0                                    # the middle's half-width, up the yoke's roof

# the adjuster: an M4 x 40 button head, head counterbored into the post's +X face
CS_SCREW_L = 40.0
assert CS_SCREW_L in D.M4_BUTTON_STOCK_L
HEAD_D = 7.6 + 0.8                               # ISO 7380 M4 head Ø7.6
PW1 = 30.0                                       # the post's +X face (the board's end)
PW_T = 12 * D.BEAD                               # 9.6: the wall
PW_CB = 6 * D.BEAD                               # 4.8: the counterbore, so 4.8 of wall under the head
PW0 = PW1 - PW_T                                 # 20.4: the wall's -X face
X_HEAD = PW1 - PW_CB                             # the head's seat
X_TIP = X_HEAD - CS_SCREW_L                      # -14.8
BITE_MIN = 3 * M4.pitch                          # 2.1: three threads in the insert, the slider's farthest out
GAP_MIN = 0.5                                    # the slider's +X face at the wall, fully in
# THE SLIDER'S INSERT IS A NUT (user, 2026-11-09): it slides into a pocket from the slider's -X
# face and seats on a LIP at the +X face, the M4 through the lip. The springs pull the slider -X
# and the screw holds it +X, so the string's whole pull presses the insert ONTO the lip -- it
# cannot be torn out of its melt. The pocket is a snug teardrop: if the insert turns with the
# screw, touch it home with the iron.
SL_LIP = 4 * D.BEAD                              # 3.2: ~60 mm^2 in shear round the insert, 2.4 MPa at 147 N
SL_POCKET_D = 5.9                                # teardrop: between cadkit's heat-set 5.7 and drop-in 6.1
XS1_OUT, XS1_IN = X_TIP + BITE_MIN + SL_LIP, PW0 - GAP_MIN   # the slider's +X face, out .. in
CS_STROKE = XS1_IN - XS1_OUT                     # 32.6

# where the station goes: fully in = 100 % + CS_OVER with the yoke at mid travel
CS_OVER = 1.0
S_FULL = spring_stretch(T_FULL) + CS_OVER        # the stretch, fully in
PITCH_FULL = SPR_L0 + S_FULL - PIN_D             # pin to pin (the loops wrap the pins' far sides)
XP_IN = XS1_IN - PIN_PAD                         # the slider's pins, fully in
CS_ROOF0 = _xr_x(D.NUT_TOP_Z - D.CARRIAGE_TRAVEL / 2.0 + YK_H)   # -8.0: the yoke's roof, mid travel, unmoved
CS_DX = round(XP_IN - PITCH_FULL + PIN_PAD - CS_ROOF0, 1)        # the station's move, -X
CS_ROOF = CS_ROOF0 + CS_DX
XP_SPREAD = CS_ROOF - PIN_PAD                    # the counter yoke's pins
S_OUT = (XS1_OUT - PIN_PAD) - XP_SPREAD + PIN_D - SPR_L0         # the stretch, screw backed out
assert spring_pull(S_OUT) <= 0.5 * T_FULL, "the screw cannot back the springs off to 50 %"
CS_SCALE = CS_ROOF - CROWN_X                     # crown to the yoke's roof

# the post: the wall, a deck under the slider on two ribs, a base on the station's old four holes
DECK_TOP = BAR_Z0 - 0.4
POST_HW = 16 * D.BEAD                            # 12.8: the wall, deck and ribs' half-width
assert CS_DY - SPR_OD / 2 >= POST_HW + 1.0 - 1e-9
RIB_T = 6 * D.BEAD
DECK_X0 = XS1_OUT - BAR_L + 8.0                  # the deck still under the slider, backed out
POST_X0 = XR_SCREWS_X[0] - XR_TAB                # the base's -X end
POST_TOP = XR_ZA + 12 * D.BEAD
# FLUSH WITH THE SCREW TABS (user, 2026-11-10: the wall's +X root is where it split): its +X face
# out to the tabs' +X edge, the head's seat unmoved -- the counterbore just deeper
POST_XF = XR_SCREWS_X[1] + XR_TAB                # 32.47, was PW1 (30.0)
assert POST_XF >= PW1


def _pin(x, y):
    """The loop's pin, standing on PIN_Z0 at (x, y), a 45 deg head over it."""
    p = cyl(PIN_D, PIN_GAP + 0.01, z=PIN_Z0 - 0.01).translate((x, y, 0.0))
    rise = (PIN_HEAD_D - PIN_D) / 2
    cone = cq.Workplane("XY").add(cq.Solid.makeCone(PIN_D / 2, PIN_HEAD_D / 2, rise,
                                                    pnt=cq.Vector(x, y, PIN_Z0 + PIN_GAP)))
    top = PIN_Z0 + PIN_GAP + rise
    return p.union(cone).union(cyl(PIN_HEAD_D, 2 * D.BEAD, z=top - 0.01).translate((x, y, 0.0)))


def _xb(d, x0, x1):
    return printable_bore(d, x1 - x0, axis_point=(x0, SY, XR_ZA), axis_dir=(1.0, 0.0, 0.0),
                          print_up=UP)


def _bar(x1, hub_top):
    """A spring bar, its +X face at x1: the bar across Y, its middle up to hub_top, a pin each end."""
    x0 = x1 - BAR_L
    b = _box(x0, x1, SY - BAR_HW, SY + BAR_HW, BAR_Z0, PIN_Z0)
    b = b.union(_box(x0, x1, SY - HUB_HW, SY + HUB_HW, BAR_Z0, hub_top))
    for s in (-1, 1):
        b = b.union(_pin(x1 - PIN_PAD, SY + s * CS_DY))
    return b


def _xflat(d, x0, x1, z=XR_ZA):
    """A bore along X, x0..x1 on (SY, z), its ceiling FLAT at the crown: a d-wide bridge in the +Z
    print. A teardrop's peak would run into the M3 holes beside it."""
    r = d / 2.0
    return cyl_x(d, x1 - x0, x0, y=SY, z=z).union(_box(x0, x1, SY - r, SY + r, z, z + r))


CY_FT = CS_ROOF + YK_H                           # the nut flange's top face, mid travel (world x)
CY_Z0, CY_Z1 = BAR_Z0, XR_ZA + YK_HX             # 2.2 .. 27.8: the yoke's underside and top
CY_HY = YK_LIP_D / 2 + D.MIN_WALL                # 6.1: one bead outside the lip's recess (the axial yoke had 0.7)
assert CY_HY <= XR_HW - XR_WALL - 0.4 + 1e-9, "the yoke rubs the station's buttresses"
# TWO BEADS ROUND THE LIP'S RECESS (user, 2026-11-10: the 0.8 side walls broke the 1.6 quality
# rule). The yoke can't be 2 x CY_HY_LIP wide all the way down: at the top of travel its +X end runs
# ~1.7 between the buttresses, whose tops are z <= 6.9 there. So only from CY_WIDE_Z up, under it a
# 45 deg step out from CY_HY (it faces down in the +Z print).
CY_HY_LIP = YK_LIP_D / 2 + D.MIN_WALL_2P         # 6.95
CY_WIDE_Z = XR_ZA - CY_HY_LIP                    # 8.86: full width from the recess's 1.6 wall down
assert CY_WIDE_Z - (CY_HY_LIP - CY_HY) >= 6.9 + 0.4, "the yoke's wide part reaches the buttresses' tops"
assert D.NUT_HOLE_DX - YK_TAP_D / 2 - YK_LIP_D / 2 >= D.MIN_WALL - 1e-9, "tap hole into the lip's recess"


def counter_yoke() -> cq.Workplane:
    """THE COUNTER YOKE (user, 2026-11-09): the yoke and the spreader in one, its only jobs the nut,
    the string and the springs -- no guide rod, no arm. In place (world) at mid travel, base down.
      the BODY on the nut's flange: 24 x 12.2 x 16, 13.9 wide from CY_WIDE_Z up (two beads round the lip's recess), two M3 x 12 up through the nut's
        ears self-tapping into its +X face, the screw tip's cavity, the lip's recess;
      the ROOF: the ball end seats under it on the axis, the string out a 2.1 hole down the axis;
      the BAR across Y on the roof's -X face, the springs' pins at its ends (the spreader's, so the
        station stays where it is), its middle up the roof's full height."""
    x1, xr = CY_FT, CS_ROOF
    y = _box(xr, x1, SY - CY_HY, SY + CY_HY, CY_Z0, CY_Z1)
    w, z0 = CY_HY_LIP - CY_HY, CY_WIDE_Z
    for sy in (-1, 1):                                                          # the 1.6 round the lip
        pts = [(SY + sy * CY_HY, z0 - w - 0.01), (SY + sy * CY_HY_LIP, z0), (SY + sy * CY_HY_LIP, CY_Z1),
               (SY + sy * (CY_HY - 0.01), CY_Z1), (SY + sy * (CY_HY - 0.01), z0 - w - 0.01)]
        y = y.union(cq.Workplane("YZ", origin=(xr, 0, 0)).polyline(pts).close().extrude(x1 - xr))
    y = y.union(_bar(xr + 0.01, CY_Z1).translate((-0.01, 0.0, 0.0)))
    y = y.cut(_xflat(YK_CAV, x1 - YK_R0, x1 + 1.0))                             # the screw's tip
    y = y.cut(_xflat(YK_LIP_D, x1 - YK_LIP_L, x1 + 1.0))                        # the nut's lip
    y = y.cut(_xb(STR_HOLE_D + 0.1, xr - BAR_L - 1.0, x1 - YK_R0 + 1.0))        # the string
    for sz in (-1, 1):
        y = y.cut(printable_bore(YK_TAP_SIDE_D, YK_TIP + 1.0, axis_point=(x1 - YK_TIP, SY, XR_ZA + sz * D.NUT_HOLE_DX),
                                 axis_dir=(1.0, 0.0, 0.0), print_up=UP))
    return y


def slider(xs1=XS1_IN) -> cq.Workplane:
    """The post end's bar, its +X face at xs1 (world): the M4 through the LIP, the insert's pocket
    from the -X face up to it (SL_LIP). Base down."""
    s = _bar(xs1, XR_ZA + 7.0)
    s = s.cut(_xb(M4.shaft_clr_d, xs1 - SL_LIP - 1.0, xs1 + 1.0))           # through the lip
    return s.cut(_xb(SL_POCKET_D, xs1 - BAR_L - 1.0, xs1 - SL_LIP))           # the insert's way in


def counter_post() -> cq.Workplane:
    """The wall with the M4 x 40, the deck the slider rides on, two ribs under it, and a base on the
    X station's old four plank holes. Base down."""
    zb = Z_PLANK_X + BASE_T
    s = _box(PW0, POST_XF, SY - POST_HW, SY + POST_HW, zb - 0.01, POST_TOP)
    s = s.union(_box(DECK_X0, PW0 + 0.01, SY - POST_HW, SY + POST_HW, DECK_TOP - 3 * D.BEAD, DECK_TOP))
    # the ribs: full height over the base, their -X ends a 45 deg underside out to the deck's end
    d45 = POST_X0 - DECK_X0
    rib = [(DECK_X0, DECK_TOP), (PW0 + 0.01, DECK_TOP), (PW0 + 0.01, zb - 0.01), (POST_X0, zb - 0.01),
           (POST_X0, DECK_TOP - 3 * D.BEAD - d45), (DECK_X0, DECK_TOP - 3 * D.BEAD)]
    # SOLID, full width (user, 2026-11-10: the post tore at its base): with the X rig's plank up
    # 51 the deck is only ~5 over the base, so the two ribs became one block -- no bridge under the
    # deck, and the wall's root is the whole post's footprint
    s = s.union(_xz_prism(rib, SY - POST_HW, SY + POST_HW))
    # base: a strip under the ribs and wall, a crossbar out to each pair of holes
    s = s.union(_box(POST_X0, POST_XF, SY - POST_HW, SY + POST_HW, Z_PLANK_X, zb))
    for x in XR_SCREWS_X:
        s = s.union(_box(x - XR_TAB, x + XR_TAB, XR_SCREWS_Y[0] - XR_TAB, Y_EDGE, Z_PLANK_X, zb))
    s = s.cut(_xb(M4.shaft_clr_d, PW0 - 1.0, POST_XF + 1.0))
    s = s.cut(_xb(HEAD_D, X_HEAD, POST_XF + 1.0))
    for x in XR_SCREWS_X:
        for y in XR_SCREWS_Y:
            s = s.cut(_wood_screw(x, y, UP, Z_PLANK_X))
    return s


def _spring(xa, xb, y):
    """A spring between pins at xa < xb, at y: a tube between its loops, the loops round the pins."""
    a, b = xa - PIN_D / 2, xb + PIN_D / 2                    # the loops' insides
    loop_r = SPR_OD / 2 - SPR_WIRE
    body0, body1 = a + 2 * loop_r + SPR_WIRE, b - 2 * loop_r - SPR_WIRE
    t = cyl_x(SPR_OD, body1 - body0, body0, y=y, z=XR_ZA).cut(
        cyl_x(SPR_OD - 2 * SPR_WIRE, body1 - body0 + 2, body0 - 1, y=y, z=XR_ZA))
    for cx in (a + loop_r, b - loop_r):
        t = t.union(cq.Workplane("XY").add(cq.Solid.makeTorus(
            loop_r + SPR_WIRE / 2, SPR_WIRE / 2, pnt=cq.Vector(cx, y, XR_ZA))))
    return t


def slider_for(level):
    """The slider's +X face for `level` of 147 N, the yoke at mid travel."""
    xp = XP_SPREAD + SPR_L0 + spring_stretch(level * T_FULL) - PIN_D
    return xp + PIN_PAD


def assembly_counter(level=1.0):
    """The counter-spring rig (scratch view scope): the X rig moved CS_DX, the springs at `level`."""
    moved = ("plank_station_x",) + tuple("x" + n for n in XR_PARTS)
    out = []
    for nm, w in assembly_x():
        if nm == "xyoke_0":                      # the counter yoke takes its place
            continue
        if nm in moved:
            w = w.translate((CS_DX, 0.0, 0.0))
        elif nm == "string_0":
            g = D.STRING_GAUGE[I]
            a = (_xr_x(D.NUT_TOP_Z - D.CARRIAGE_TRAVEL / 2.0 + YK_R0 - D.STRING_NUT_D / 2) + CS_DX, SY, XR_ZA)
            crown = (CROWN_X, SY, XR_ZA)
            w = _seg(a, crown, g / 2).union(_seg(crown, (CROWN_X - 40.0, SY, Z_PLANK_X + 2.0), g / 2))
        out.append((nm, w))
    xs1 = slider_for(level)
    out.append(("plank_counter_yoke", counter_yoke()))
    out.append(("plank_counter_slider", slider(xs1)))
    out.append(("plank_counter_post", counter_post()))
    for k, s in enumerate((-1, 1)):
        out.append((f"counter_spring_{k}", _spring(XP_SPREAD, xs1 - PIN_PAD, SY + s * CS_DY)))
    from .motor_coupler import cap_screw
    out.append(("counter_m4_0", cap_screw("m4", CS_SCREW_L, (X_HEAD + 2.2, SY, XR_ZA), (-1, 0, 0))))
    from cadkit.fasteners import seated_insert
    out.append(("counter_insert_0", seated_insert(M4, (xs1 - SL_LIP, SY, XR_ZA), (-1.0, 0.0, 0.0))))
    return out


# ═════════════════════════════════════════════════════════════════════════════════════════
# THE IN-LINE MOTOR (user, 2026-11-09): a SERVO42D on the screw's own axis, past the rail wall, in
# place of the screw pulley -- to find how much counter-spring pull the motor needs before it can
# tighten and loosen the string reliably with no reduction at all.
#   COUPLER   src.motor_coupler's printed one, with its inner-race BOSS: it takes the pulley's
#             place as the screw's THRUST SHOULDER on the rail wall's 688 (the string pulls the
#             screw -X; the springs keep that so, under the string). The screw sticks 9.5 past the
#             688, threaded into the coupler's formed-thread socket (the screw pulley's own grip)
#             and squeezed by its C clamp's M3 x 12 into a fitted insert (user, 2026-11-10: the
#             screw was too tough to drill for the old cross pin). No thrust reaches the motor.
#   BLOCK     on a new set of four plank holes, the station's pattern (XR_SCREWS' 33.97 x 43.80):
#             the FACE WALL the motor's faceplate is screwed to (its four M3 x 12, heads on the -X
#             face -- they stand outside the X station's walls in Y, so a 2.5 key reaches each along
#             X past it), two 45 deg RIBS bracing it, the base.
#   SPRINGS   CS_DY moved out to clear the can: reprint the counter yoke and the slider.
#   RANGE     the slider backs out only to the motor's back (INLINE_XS1_MIN): ~53 % to 100 %.
# ORDER: block to the plank (all four wood screws open); coupler threaded onto the screw to its
# end, the clamp's M3 snug; motor in from +Z between the block and the
# slider (slider fully in), slid -X onto the coupler's D, its four M3s; springs last.
from . import motor_coupler as MC

# THE USER'S 38 mm SCREW (user, 2026-11-09: a piece cut earlier), not the instrument's 36.28. Its +X
# end stays where the instrument's is (the coupler, block and motor unmoved) and the extra goes on
# the -X TIP: MORE TRAVEL (user: "can we get more travel"). The nut's far end is the rail wall's
# ledge and cannot move; its string end is only how much thread it keeps, so the nut now runs
# INLINE_EXTRA further toward the string on the same ~12 of thread: 8.35 -> 10.07. At the ledge
# end the tip then reaches INLINE_TIP_IN into the yoke's YK_R0 cavity, short of the ball's seat.
INLINE_SCREW_LEN = 38.0
INLINE_EXTRA = INLINE_SCREW_LEN - D.SCREW_LEN     # 1.72
INLINE_TRAVEL = D.CARRIAGE_TRAVEL + INLINE_EXTRA
INLINE_TIP_IN = YK_PROTRUDE + INLINE_EXTRA        # 8.47 of the cavity's 12
assert INLINE_TIP_IN <= YK_R0 - 2.0, "the 38 mm screw's tip reaches the ball end's seat"
INLINE_SCREW_END = _xr_x(D.SCREW_BOT_Z) + CS_DX   # the screw's +X end
INLINE_BRG_FACE = _xr_x(BRG_BOT_Z) + CS_DX        # the 688's +X face (the pulley's shoulder)
INLINE_XP = INLINE_SCREW_END + MC.SCREW_X0        # the motor's pulley plane (world x)
INLINE_BOSS = 0.8                                 # the coupler's boss onto the 688's inner race
INLINE_C1 = INLINE_XP - INLINE_BRG_FACE - INLINE_BOSS   # the coupler's body end (motor frame y)
INLINE_FACE = INLINE_XP + 7.5                     # the motor's faceplate (components.MOTOR_PULLEY_STANDOFF)
INLINE_BACK = INLINE_XP + 60.7                    # its driver's back (direct_bench.M_BACK)
INLINE_WALL_T = 10 * D.BEAD                       # 8.0: the M3 x 12 has 4 into the faceplate
INLINE_HOLES = 31.0                               # NEMA17's M3 square
INLINE_XS1_MIN = INLINE_BACK + 0.5 + BAR_L        # the slider's +X face, backed out to the motor
INLINE_X_SCREWS = (INLINE_FACE - INLINE_WALL_T - 6.6, INLINE_FACE - INLINE_WALL_T - 6.6 + 33.97)
assert INLINE_X_SCREWS[0] - XR_TAB >= XR_X1 + CS_DX + 0.2 - 1e-9, "the block's tab on the station's"
assert INLINE_XS1_MIN <= XS1_IN, "the motor leaves the slider no room"
CRADLE_HW = 12.0                                  # the ribs' outer faces: inside the wood screws' heads
GAUGE_T = D.BEAD                                  # 0.8: the gauge arms to the counter post
M_HALF = D.MOTOR_SQ / 2


def motor_block() -> cq.Workplane:
    """The face wall, two ribs and the base on four new plank holes. Base down."""
    zb = Z_PLANK_X + BASE_T
    w0, w1 = INLINE_FACE - INLINE_WALL_T, INLINE_FACE
    s = _box(w0, w1, SY - M_HALF, SY + M_HALF, zb - 0.01, XR_ZA + M_HALF)       # the face wall
    # THE MOTOR'S PAD (user, 2026-11-10: the motor sits level with the wood): the base under the
    # whole can, the wall's +X foot -- an L, so the pad and the motor bolted to the wall brace it
    # (the 45 deg ribs that stood under the raised can are gone). Z_PLANK_X puts the can
    # MOTOR_SEAT_CLR over it: the faceplate's M3s align the motor, the pad only catches it.
    pad1 = INLINE_BACK
    s = s.union(_box(w0, pad1, SY - M_HALF, SY + M_HALF, Z_PLANK_X, zb))
    for y0 in (SY - CRADLE_HW, SY + CRADLE_HW - RIB_T):
        # a GAUGE ARM on from it (user, 2026-11-09): 0.8 tall on the plank, ending exactly at the
        # counter post's -X base edge. Butt the post against both and it is at its spacing, square
        s = s.union(_box(pad1 - 0.01, POST_X0, y0, y0 + RIB_T, Z_PLANK_X, Z_PLANK_X + GAUGE_T))
    for x in INLINE_X_SCREWS:
        s = s.union(_box(x - XR_TAB, x + XR_TAB, XR_SCREWS_Y[0] - XR_TAB, Y_EDGE, Z_PLANK_X, zb))
    s = s.union(_box(INLINE_X_SCREWS[0], w1, XR_SCREWS_Y[0] - XR_TAB, Y_EDGE, Z_PLANK_X, zb))
    s = s.cut(_xb(D.NEMA17_PILOT_D + 0.6, w0 - 1.0, w1 + 1.0))                  # the pilot
    for sy in (1, -1):
        for sz in (1, -1):
            s = s.cut(printable_bore(3.4, INLINE_WALL_T + 2.0,
                                     axis_point=(w0 - 1.0, SY + sy * INLINE_HOLES / 2,
                                                 XR_ZA + sz * INLINE_HOLES / 2),
                                     axis_dir=(1.0, 0.0, 0.0), print_up=UP))
    for x in INLINE_X_SCREWS:
        for y in XR_SCREWS_Y:
            s = s.cut(_wood_screw(x, y, UP, Z_PLANK_X))
    return s


def _inline_frame(w):
    """The motor's own frame (shaft +Y, flat +Z) -> its place: shaft -X on the screw's axis."""
    return w.rotate((0, 0, 0), (0, 0, 1), 90).translate((INLINE_XP, SY, XR_ZA))


def inline_coupler() -> cq.Workplane:
    return _inline_frame(MC.coupler(INLINE_C1, INLINE_BOSS))


def assembly_inline(level=1.0):
    """The counter-spring rig with the in-line motor (scratch view scope), springs at `level`."""
    xs1 = slider_for(level)
    assert xs1 >= INLINE_XS1_MIN - 1e-6, f"the slider at {level:.0%} runs into the motor"
    out = [(nm, w) for nm, w in assembly_counter(level) if nm not in ("xscrew_pulley_0", "xleadscrew_0")]
    scr = C.screw(INLINE_SCREW_LEN).translate((SX, SY, D.SCREW_BOT_Z))
    out.append(("xleadscrew_0", scr.rotate((0, 0, 0), (0, 1, 0), -90)
                .translate((XR_OFF + CS_DX, 0.0, XR_ZA - SX))))
    out.append(("plank_motor_block", motor_block()))
    out.append(("inline_coupler", inline_coupler()))
    for k, w in MC.clamp_parts(INLINE_C1):
        out.append((f"inline_coupler_{k}", _inline_frame(w)))
    for k, wp, _, _fin in C.motor_parts():
        out.append((f"inline_motor_{k}" if k else "inline_motor", _inline_frame(wp)))
    w0 = INLINE_FACE - INLINE_WALL_T
    for sy in (1, -1):
        for sz in (1, -1):
            out.append((f"inline_face_m3_{(sy + 1) // 2}{(sz + 1) // 2}",
                        MC.cap_screw("m3", MC.M3_L, (w0 - 3.0, SY + sy * INLINE_HOLES / 2,
                                                     XR_ZA + sz * INLINE_HOLES / 2), (1, 0, 0))))
    return out


# ── THE INSTRUMENT'S PIECES, FROZEN ──────────────────────────────────────────────────────────
# The bay and the tee board are carved from the instrument's motor bank and wiring, and importing
# those builds half the instrument (src.wiring alone is over 90 s) for a few parts that never move
# here. So they are BUILT ONCE into FROZEN (BREPs, committed, at the instrument's own world pose)
# and read back in well under a second (user, 2026-11-08: "grab the geometry once"). Nothing
# re-freezes them behind your back: after a change to the motor bay or the tee board, run
#     py -3.12 -m src.plank_bench --freeze
FROZEN = pathlib.Path(__file__).resolve().parent / "plank_bench_frozen"
_TEE_KEEP = ("tee_pcb", "tee_silk", "tee_insert", "tee_screw")


def freeze():
    """Build the bay, its dummy board and string 1's tee board from the instrument and write them."""
    import subprocess
    from . import motor_bank as MB, wiring as W
    keep = MB.COUPON_MOTOR
    MB.COUPON_MOTOR = I
    try:
        bay_, dummy = MB._coupon_world()
    finally:
        MB.COUPON_MOTOR = keep
    parts = [("bay", bay_), ("tee_dummy", dummy)]
    parts += [(nm, shp) for nm, shp in W.tee_components() if nm.endswith("_0") and nm.startswith(_TEE_KEEP)]
    FROZEN.mkdir(exist_ok=True)
    for nm, w in parts:
        (w.val() if hasattr(w, "val") else w).exportBrep(str(FROZEN / f"{nm}.brep"))
    head_ = subprocess.run(["git", "log", "-1", "--format=%h %cs"], cwd=FROZEN, capture_output=True,
                           text=True).stdout.strip()
    (FROZEN / "FROZEN.txt").write_text(
        "Built by `py -3.12 -m src.plank_bench --freeze` from the instrument at %s.\n%s\n"
        % (head_, "\n".join(nm for nm, _ in parts)), encoding="utf-8")
    return [nm for nm, _ in parts]


def _frozen(nm):
    f = FROZEN / f"{nm}.brep"
    if not f.exists():
        raise FileNotFoundError(f"{f} is missing: run `py -3.12 -m src.plank_bench --freeze`")
    return cq.Workplane("XY").add(cq.Shape.importBrep(str(f)))


def _frozen_tee():
    names = (FROZEN / "FROZEN.txt").read_text(encoding="utf-8").splitlines()[1:]
    return [(nm, _frozen(nm)) for nm in names if nm.startswith(_TEE_KEEP)]


_BAY = None


def bay():
    """(bay, dummy board): motor_bank's coupon on string 1's motor, lifted to the plank's height."""
    global _BAY
    if _BAY is None:
        _BAY = tuple(_frozen(nm).translate((0, 0, MOTOR_RISE)) for nm in ("bay", "tee_dummy"))
    return _BAY


def head() -> cq.Workplane:
    zb = Z_PLANK + BASE_T
    b, _dummy = bay()
    bb = b.val().BoundingBox()
    # THE BAY AND FOUR SCREW TABS, no plate round them (user, 2026-11-08): a pad the bay's own
    # footprint under it -- the coupon's floor is a rim, and the can stands on this -- and a tab
    # out each side at each end for a wood screw, the +Y pair running out to Y_EDGE so the head
    # still lies flush with the plank's edge like the station
    # The bay's FLOOR footprint, not its bounding box: the hold-down post's corbel reaches 8 past
    # the floor in +X and 6.8 in +Y up top, over air (user, 2026-11-08: "move this strip over")
    fl = b.val().intersect(cq.Solid.makeBox(bb.xlen + 2, bb.ylen + 2, 0.1,
                                            cq.Vector(bb.xmin - 1, bb.ymin - 1, zb + 0.1))).BoundingBox()
    h = _box(fl.xmin, fl.xmax, fl.ymin, fl.ymax, Z_PLANK, zb).union(b)
    tx = (fl.xmin + TAB / 2, fl.xmax - TAB / 2)
    for x in tx:
        h = h.union(_box(x - TAB / 2, x + TAB / 2, fl.ymin - TAB, fl.ymin + 0.01, Z_PLANK, zb))
        h = h.union(_box(x - TAB / 2, x + TAB / 2, fl.ymax - 0.01, max(Y_EDGE, fl.ymax + TAB), Z_PLANK, zb))
    # the can's floor relieved under the driver housing,
    # which hangs 0.1 under the can's floor line (servo42d, measured)
    h = h.cut(_box(MX - 21.3, MX + 21.3, MX_Y0, MX_Y0 + 13.5, zb - 0.4, zb + 0.01))
    # the belt's upper run leaves the motor pulley 1.5 deg off level here, and grazes the bay's
    # post by 0.16 where the instrument's level belt clears it: a relief, not a change to the bay
    h = h.cut(_box(MX + 9.0, MX + 20.0, MY - 2.7, MY - 1.2, MZ + 3.0, MZ + 5.5))
    # the crown tower, against the bay's -X wall, the Ø4 x 4 dowel in a cradle on top
    tz1 = CROWN_Z
    h = h.union(_box(TOWER_X0, bb.xmin + 0.8, TOWER_Y0, TOWER_Y1, Z_PLANK, tz1))
    h = h.cut(cyl_y(D.NUT_PIN_D + 0.2, D.NUT_PIN_L + 0.4, SY - (D.NUT_PIN_L + 0.4) / 2,
                    x=CROWN_X, z=CROWN_Z))
    # the tail's side: 45 deg off the -X top corner, under the line to the tuner
    c = CROWN_X - 3.3
    h = h.cut(cq.Workplane("XZ").polyline([(TOWER_X0 - 1.0, tz1 + 1.0), (c, tz1 + 1.0), (c, tz1),
                                           (TOWER_X0, tz1 - (c - TOWER_X0)),
                                           (TOWER_X0 - 1.0, tz1 - (c - TOWER_X0))]).close()
              .extrude(-(TOWER_Y1 - TOWER_Y0 + 2.0)).translate((0, TOWER_Y0 - 1.0, 0)))
    for x in tx:
        for y in (fl.ymin - TAB / 2, max(Y_EDGE, fl.ymax + TAB) - TAB / 2):
            h = h.cut(_wood_screw(x, y))
    return h


# ── HARDWARE, AT THE INSTRUMENT'S OWN POSITIONS ──────────────────────────────────────────────
def _belt_bits():
    clamp = BTn.clamp_components()
    xs = [v for _n, _s in clamp for v in (_s.val().BoundingBox().xmin, _s.val().BoundingBox().xmax)]
    x0, x1 = min(xs), max(xs)
    m, s = (MX, MY, MZ), (SX, SY, D.screw_pulley_z(I))
    upper = not D.screw_far(I)
    gap = BTn.belt_fit(C.belt_loop(m, s))[1]
    p = C.clamp_p(m, s, upper, x0, x1, 0.0)
    args = (m, s, upper, p, x0, x1, *BTn.belt_ends(gap))
    o, xd, n = C.clamp_frame(m, s, upper, p, x0, x1, 0.0)
    loc = cq.Location(cq.Plane(origin=o, xDir=xd, normal=n))
    return args, gap, loc


def _seg(a, b, r):
    a, b = cq.Vector(*a), cq.Vector(*b)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, (b - a).Length, pnt=a, dir=b - a))


def _string(tail_x=-770.0, axial=False):
    """Ball end -> up past the ear (or the yoke's roof) -> over the bearing -> crown -> tuner."""
    g = D.STRING_GAUGE[I]
    r, R = g / 2.0, D.BRIDGE_BEARING_OD / 2 + g / 2.0
    if axial:
        bx, bz, a0 = BX_AX, BZ_AX, 0.0                     # straight down the axis off the tangent
        anchor = (SX, SY, D.NUT_TOP_Z + YK_R0 - D.STRING_NUT_D / 2)
    else:
        bx, bz, a0 = BX, BZ, math.radians(5.0)             # the rise touches just +X of the top's right
        anchor = (D.string_anchor_x(I), SY, D.NUT_TOP_Z - D.NUT_FLANGE_T - D.STRING_NUT_D / 2)
    pts = [(bx + R * math.cos(a0 + (math.pi / 2 - a0) * k / 8), SY, bz + R * math.sin(a0 + (math.pi / 2 - a0) * k / 8))
           for k in range(9)]
    crown = (CROWN_X, SY, D.STRING_Z - r)
    path = [anchor] + pts + [crown, (tail_x, SY, Z_PLANK + 15.0)]
    out = None
    for a, b in zip(path, path[1:]):
        sgm = _seg(a, b, r)
        out = sgm if out is None else out.union(sgm)
    return out


def assembly(axial=False):
    """Everything, placed: the printed parts and every bought part on them. axial: the axial
    rig's station and yoke, the nut at the top of its travel."""
    args, gap, cloc = _belt_bits()
    mp_deg, sp_deg = C.belt_mesh(*args, BTn.BELT_TOOTH_IN)
    out = [("plank_station_axial" if axial else "plank_station", station_axial() if axial else station()),
           ("plank_head", head())]
    out.append(("leadscrew_0", C.screw().translate((SX, SY, D.SCREW_BOT_Z))))
    out.append(("nut_0", C.nut().translate((SX, SY, D.NUT_TOP_Z))))
    if axial:
        from cadkit.fasteners import headed_screw
        out.append(("yoke_0", yoke().translate((SX, SY, D.NUT_TOP_Z))))
        out.append(("string_nut_0", C.string_nut().rotate((0, 0, 0), (0, 0, 1), 90).translate(
            (SX, SY, D.NUT_TOP_Z + YK_R0 - D.STRING_NUT_D / 2))))
        out.append(("guide_rod_0", C.guide_rod(D.GUIDE_ROD_L).translate((SX, SY + ROD_DY, ROD_BOT))))
        zf = D.NUT_TOP_Z - D.NUT_FLANGE_T                  # the ears' underside
        for tag, sx in (("lo", -1), ("hi", 1)):
            x = SX + sx * D.NUT_HOLE_DX
            out.append((f"yoke_m3_{tag}_0", headed_screw(BTn.M3, YK_SCREW_L, BTn.HEAD_D, BTn.HEAD_H, 2.5)
                        .rotate((0, 0, 0), (1, 0, 0), 180).translate((x, SY, zf - BTn.HEAD_H))))
    else:
        out.append(("string_nut_0", C.string_nut().translate(
            (D.string_anchor_x(I), SY, D.NUT_TOP_Z - D.NUT_FLANGE_T - D.STRING_NUT_D / 2))))
        out.append(("guide_rod_0", C.guide_rod(D.GUIDE_ROD_L).translate((RX, SY, SOCKET_Z))))
    out.append(("screw_pulley_0", C.screw_pulley(high=D.screw_pulley_z(I) > D.SCREW_PULLEY_Z)
                .rotate((0, 0, 0), (0, 0, 1), sp_deg).translate((SX, SY, D.screw_pulley_z(I)))))
    out.append(("screw_bearing_0_0", C.support_bearing().translate(
        (SX, SY, BRG_BOT_Z + 0.5 * D.BRG688_W))))
    bx, bz = (BX_AX, BZ_AX) if axial else (BX, BZ)
    out.append(("bridge_bearing_0", C.support_bearing().rotate((0, 0, 0), (1, 0, 0), 90)
                .translate((bx, SY, bz))))
    out.append(("bridge_axle_rod", cyl_y(D.BRIDGE_AXLE_D, D.BRIDGE_AXLE_L, SY - D.BRIDGE_AXLE_L / 2, x=bx, z=bz)))
    out.append(("crown_dowel", C.dowel().translate((CROWN_X, SY, CROWN_Z))))
    for k, wp, _rgb, _fin in C.motor_parts():
        out.append((f"motor_{k}_0" if k else "motor_0", wp.translate((MX, MY, MZ))))
    out.append(("motor_pulley_0", C.motor_pulley(-mp_deg).rotate((0, 0, 0), (0, 1, 0), mp_deg)
                .translate((MX, MY, MZ))))
    out.append(("belt_0", C.belt(*args)))
    for nm, shp in BTn.clamp_components(gap):
        out.append((f"{nm}_0", cq.Workplane("XY").add(shp.val().moved(cloc))))
    for nm, shp in _frozen_tee():
        out.append((nm, shp.translate((0, 0, MOTOR_RISE))))
    out.append(("string_0", _string(axial=axial)))
    return out



def assembly_axial():
    """The axial rig (scratch view scope)."""
    return assembly(axial=True)


def print_parts():
    """{name: solid in its print pose, +Z up, on z 0}: the station turned so its +X face is the bed."""
    out = {}
    st = station().rotate((0, 0, 0), (0, 1, 0), 90)             # -X -> +Z
    sa = station_axial().rotate((0, 0, 0), (0, 1, 0), 90)
    yk = yoke().rotate((0, 0, 0), (1, 0, 0), 180)               # roof on the bed: no bridge over the cavity
    out_x = station_x()                                          # base down, as drawn
    spring = (("plank_counter_post", counter_post()), ("plank_counter_yoke", counter_yoke()),
              ("plank_counter_slider", slider()), ("plank_motor_block", motor_block()),   # all base down
              # the coupler stands on its motor end (+Y -> +Z): the D bore round, boss up
              ("plank_inline_coupler", MC.coupler(INLINE_C1, INLINE_BOSS).rotate((0, 0, 0), (1, 0, 0), 90)))
    for nm, w in (("plank_station", st), ("plank_head", head()),   # the real tee board holds the motor (user)
                  ("plank_station_axial", sa), ("plank_yoke", yk), ("plank_station_x", out_x)) + spring:
        bb = w.val().BoundingBox()
        out[nm] = w.translate((-bb.xmin, -bb.ymin, -bb.zmin))
    return out


if __name__ == "__main__":
    import sys
    from cadkit.step_export import export_step
    if "--freeze" in sys.argv:
        print("froze", ", ".join(freeze()), "into", FROZEN)
    print(f"scale span {SCALE_SPAN:.2f} (axial rig {SCALE_SPAN_AX:.2f})  plank top z {Z_PLANK:.2f}  edge y {Y_EDGE:.2f}")
    for nm, w in print_parts().items():
        bb = w.val().BoundingBox()
        print(f"{nm:14s} {bb.xlen:6.1f} x {bb.ylen:5.1f} x {bb.zlen:5.1f}  vol {w.val().Volume():8.0f} mm3"
              f"  solids {len(w.solids().vals())}")
        for d in (OUT, _MAIN_COUPONS):
            if d.is_dir():
                export_step(w, str(d / f"{nm}.step"))
