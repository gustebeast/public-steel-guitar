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
from .helpers import box_at, cyl, cyl_y
from cadkit.supports import printable_bore

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
RAIL_BOT, RAIL_TOP = SR.BOT, SR.TOP              # -31.85 .. -22.55
SOCKET_Z = SR.LEDGE_TOP + 2 * D.BEAD             # -23.35: the rod's bottom, 1.6 over the lip band
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
YK_PROTRUDE = D.SCREW_TOP_Z - (D.NUT_TOP_Z - D.CARRIAGE_TRAVEL)   # 6.75: tip over the flange, bottom of travel
assert YK_R0 - D.STRING_NUT_D >= YK_PROTRUDE + 1.0 - 1e-9, "the screw's tip reaches the ball end"
# THE M3 INSERTS ARE HEAT-SET FROM THE -Z FACE, the one on the flange (user, 2026-11-08): dropped in
# from the top onto a shoulder, that shoulder was a ring hanging over the clearance hole in the
# +Z -> -Z print. Mouth at the flange, the hole only narrows going +Z, i.e. DOWN the print. The
# screw clamps the ear to the mouth: the string pulls the insert toward its mouth, as an insert should.
YK_INS_D = BTn.INS_D + 0.1                       # 4.8: the Pi's heat-set pocket for the same insert (PI_M3)
YK_CLR_D = BTn.SCR_CLR                           # 3.4: the screw's tip, past the insert
YK_SCREW_L = BTn.SCREW_L                         # M3 x 12 socket head (the belt clamp's): ear 4 + 2.4 + 5.6 in the insert
assert YK_SCREW_L - D.NUT_FLANGE_T >= BTn.INS_L, "the M3 does not reach through its insert"
YK_TIP = YK_SCREW_L - D.NUT_FLANGE_T + 0.6       # 8.6: the hole's depth, the tip's 8.0 and air
assert D.NUT_HOLE_DX - YK_INS_D / 2 - YK_CAV / 2 >= 1.2 - 1e-9, "insert pocket into the screw's cavity"
ROD_DY = -15 * D.BEAD                            # -12.0: the guide rod, out -Y past the flange and the rail's seat
YK_ROD_D = D.GUIDE_ROD_D + 0.5                   # 4.0: printed, sliding; it only takes the screw's torque
ARM_R = YK_ROD_D / 2 + 3 * D.BEAD                # 4.4: the rod's boss
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
SCALE_SPAN_AX = BX_AX - CROWN_X                  # 594.8

OUT = pathlib.Path(__file__).resolve().parents[1] / "coupons"
_MAIN_COUPONS = pathlib.Path(__file__).resolve().parents[2] / "public-steel-guitar" / "coupons"


def _box(x0, x1, y0, y1, z0, z1):
    return box_at(x1 - x0, y1 - y0, z1 - z0, x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(z0 + z1) / 2)


def _zbore(d, x, y, z0, z1, up=UP):
    return printable_bore(d, z1 - z0, axis_point=(x, y, z0), axis_dir=(0.0, 0.0, 1.0), print_up=up)


def _wood_screw(x, y, up=UP):
    """Clearance through the base and the 45 deg countersink from its top face (a 45 deg cone
    lying sideways is AT the overhang rule, so it needs no teardrop of its own)."""
    zt = Z_PLANK + BASE_T
    clr = _zbore(WOOD_CLR_D, x, y, Z_PLANK - 1.0, zt + 1.0, up)
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
    # THE SCREW GOES IN FROM BELOW with its pulley on, as in the instrument: a 1/2 in hole through
    # the floor, which is also the guide to drill the plank through
    s = s.cut(_zbore(SCREW_HOLE_D, SX, SY, Z_PLANK - 1.0, zb + 1.0, ST_UP))
    # the rail's seat, lip and boss passage: screw_rail.seat_cutter's diameters and its teardrops
    s = s.cut(_zbore(D.SUPPORT_BRG_OD + 0.2, SX, SY, RAIL_BOT - 1.0, D.SUPPORT_BRG_Z + 1e-3, ST_UP))
    s = s.cut(_zbore(SR.SEAT_LEDGE_D, SX, SY, RAIL_BOT - 1.0, SR.LEDGE_TOP, ST_UP))
    s = s.cut(_zbore(SR.NUT_PASS_D, SX, SY, SR.LEDGE_TOP - 0.01, RAIL_TOP + 1.0, ST_UP))
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
    s = _box(X0_AX, X1B, Y0_AX - FLANGE, Y_EDGE, Z_PLANK, zb)
    s = s.union(_box(X0_AX, X1B, Y0_AX, Y1, zb - 0.01, SLAB_TOP_AX))
    s = s.cut(_box(X0_AX - 1.0, X1, SY - LANE_LO, SY + LANE_HI, zb, RAIL_BOT))          # the bay
    # the room: the nut and yoke slide in from +X; it runs out -X too
    s = s.cut(_box(X0_AX - 1.0, X1B + 1.0, SY - ROOM_HY, SY + ROOM_HY, RAIL_TOP, CEIL_AX))
    # the rod arm's channel, -Y of the room: its floor is the arm's bottom of travel
    s = s.cut(_box(X0_AX - 1.0, X1B + 1.0, ARM_Y0, SY - ROOM_HY + 0.01, ARM_Z0, CEIL_AX))
    s = s.cut(_zbore(SCREW_HOLE_D, SX, SY, Z_PLANK - 1.0, zb + 1.0, ST_UP))
    s = s.cut(_zbore(D.SUPPORT_BRG_OD + 0.2, SX, SY, RAIL_BOT - 1.0, D.SUPPORT_BRG_Z + 1e-3, ST_UP))
    s = s.cut(_zbore(SR.SEAT_LEDGE_D, SX, SY, RAIL_BOT - 1.0, SR.LEDGE_TOP, ST_UP))
    s = s.cut(_zbore(SR.NUT_PASS_D, SX, SY, SR.LEDGE_TOP - 0.01, RAIL_TOP + 1.0, ST_UP))
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
    for x in (X0_AX + 6.4, X1B - 6.4):
        for y in (Y0_AX - FLANGE / 2, Y1 + FLANGE / 2):
            s = s.cut(_wood_screw(x, y, ST_UP))
    return s


def yoke() -> cq.Workplane:
    """On the nut's flange, its axis at the origin, z 0 = the flange's top (the nut's own origin).
    Two M3 x 12 come up through the ears into inserts heat-set into its -Z face; the ball end
    goes in from +Y and seats under the roof ON THE AXIS; the guide rod runs through the -Y boss."""
    y = _box(-YK_HX, YK_HX, -YK_HY, YK_HY, 0.0, YK_H)
    y = y.union(_box(-ARM_R, ARM_R, ROD_DY, -YK_HY + 0.01, 0.0, ARM_H))
    y = y.union(cyl(2 * ARM_R, ARM_H).translate((0.0, ROD_DY, 0.0)))
    y = y.cut(cyl(YK_ROD_D, ARM_H + 2.0, z=-1.0).translate((0.0, ROD_DY, 0.0)))
    y = y.cut(cyl(YK_CAV, YK_R0 + 1.0, z=-1.0))                                     # the screw's tip
    w = D.STRING_NUT_L / 2 + 0.5                                                      # the ball end, axis X
    y = y.cut(_box(-w, w, 0.0, YK_HY + 1.0, YK_R0 - D.STRING_NUT_D - 0.4, YK_R0))   # its window, +Y
    y = y.cut(_box(-1.0, 1.0, -1.0, YK_HY + 1.0, YK_R0 - 0.01, YK_H + 1.0))           # the string's slot
    for sx in (-1, 1):
        x = sx * D.NUT_HOLE_DX
        y = y.cut(cyl(YK_INS_D, BTn.INS_L + 1.0, z=-1.0).translate((x, 0.0, 0.0)))
        y = y.cut(cyl(YK_CLR_D, YK_TIP + 1.0, z=-1.0).translate((x, 0.0, 0.0)))
    return y


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
        z0 = D.NUT_TOP_Z                                   # flush in the mouth
        for tag, sx in (("lo", -1), ("hi", 1)):
            x = SX + sx * D.NUT_HOLE_DX
            out.append((f"yoke_m3_{tag}_0", headed_screw(BTn.M3, YK_SCREW_L, BTn.HEAD_D, BTn.HEAD_H, 2.5)
                        .rotate((0, 0, 0), (1, 0, 0), 180).translate((x, SY, zf - BTn.HEAD_H))))
            out.append((f"yoke_insert_{tag}_0", cyl(BTn.INS_D, BTn.INS_L, z=z0)
                        .cut(cyl(BTn.M3.insert_bore_d, BTn.INS_L + 1, z=z0 - 0.5)).translate((x, SY, 0))))
    else:
        out.append(("string_nut_0", C.string_nut().translate(
            (D.string_anchor_x(I), SY, D.NUT_TOP_Z - D.NUT_FLANGE_T - D.STRING_NUT_D / 2))))
        out.append(("guide_rod_0", C.guide_rod(D.GUIDE_ROD_L).translate((RX, SY, SOCKET_Z))))
    out.append(("screw_pulley_0", C.screw_pulley(high=D.screw_pulley_z(I) > D.SCREW_PULLEY_Z)
                .rotate((0, 0, 0), (0, 0, 1), sp_deg).translate((SX, SY, D.screw_pulley_z(I)))))
    out.append(("screw_bearing_0_0", C.support_bearing().translate(
        (SX, SY, D.SUPPORT_BRG_BOT + 0.5 * D.BRG688_W))))
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
    for nm, w in (("plank_station", st), ("plank_head", head()),   # the real tee board holds the motor (user)
                  ("plank_station_axial", sa), ("plank_yoke", yk)):
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
