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
    STATION   the screw station: bridge-bearing cradle, changer room, screw rail (688 seat,
              lip, boss passage -- screw_rail's diameters), guide-rod socket, and the open
              pulley bay the belt leaves by. A +X buttress takes the string's pull (147 N at
              STRING_Z, 92 mm over the plank) down to the plank.
    CAP       over the station's slab: keeps the bridge axle and the guide rod's plug in (the
              optical board's job in the instrument), two M4 x 10 buttons into heat-sets.

ONE STRING, STRAIGHT. The instrument's string 1 fans 13.5 in Y over its length; here the crown
is on the string's bridge Y instead, so the string runs straight down the plank. That changes
its speaking length by 0.15 mm (607.15 -> 607.00), well under how well a plank is marked out.

THE PLANK: its top is Z_PLANK (the motor's floor less the bases' thickness), and the +Y faces of
both bases are one plane, Y_EDGE -- lay them flush with the plank's +Y edge and they are in line.
Crown dowel to bridge-bearing axle is SCALE_SPAN along X: that is the only measurement to make.
PRINT POSES: the head and the station BASE DOWN (+Z up) -- the station's rail and room are
bridges between its two full-height side walls, the bay's own overhangs are the coupon's -- the cap
and the tee dummy flat. PETG-GF.

    py -3.12 -m src.plank_bench      -> coupons/plank_head.step, plank_station.step, plank_cap.step
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
from cadkit.fasteners import M4, m4_button_screw, seated_insert
from cadkit.supports import printable_bore

I = 0                                            # string 1
SX, SY = D.screw_x(I), D.string_y(I)             # -12.0, 42.75: the screw's axis
RX = D.guide_rod_x(I)                            # -20.0: the guide rod
UP = (0.0, 0.0, 1.0)                             # every printed part here builds +Z

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
LANE_HI = 11 * D.BEAD                            # 8.8: the bay's +Y half-width (1.43 past the clamp)
WALL_HI = 4 * D.BEAD                             # 3.2: the +Y wall outside it
Y0, Y1 = SY - LANE - WALL, SY + LANE_HI + WALL_HI   # 31.55 .. 54.75, the station's Y faces
Y_EDGE = Y1                                      # every base's +Y face: the plank's edge
X0 = RX - 7.2                                    # -27.2: the head's -X face, past the rod's socket
X1 = D.BRIDGE_X + 4.0                            # 4.0: the back wall's inner face
X1B = X1 + WALL                                  # 8.8
SLAB_TOP = 12.2                                  # the optical board's underside (OP.PCB_BOT): the cap is the board
CAP_T = 3 * D.BEAD                               # 2.4

# the screw rail, at screw_rail's own numbers -- round bores, since this one builds +Z
RAIL_BOT, RAIL_TOP = SR.BOT, SR.TOP              # -31.85 .. -22.55
SOCKET_Z = SR.LEDGE_TOP + 2 * D.BEAD             # -23.35: the rod's bottom, 1.6 over the lip band
ROD_TOP = SOCKET_Z + D.GUIDE_ROD_L               # 6.45
ROD_BORE = D.GUIDE_ROD_D + D.GUIDE_ROD_FIT       # 3.65, round
ROD_PLUG_D, ROD_PLUG_L = 4 * D.BEAD, (SLAB_TOP - 0.15) - ROD_TOP   # the instrument's rod_plug: 3.2 x 5.6

# the bridge bearing: a 688 on an Ø8 shaft, as in the instrument, in a pocket with 2.7 of floor
BX, BZ = D.BRIDGE_AXLE_X, D.BRIDGE_BEARING_Z     # (-8, 8)
BRG_POCKET = (BX - D.BRIDGE_BEARING_OD / 2 - 0.5, D.BRIDGE_X + 1.6, 2.9, -0.5)   # x0, x1, half-Y, z0
AXLE_SLOT_D = D.BRIDGE_AXLE_D + 0.4              # 8.4, open on top and through both Y faces: any Ø8
                                                 # shaft over the station's width, the bought 100 too
assert BZ + D.BRIDGE_AXLE_D / 2 <= SLAB_TOP - 0.2 + 1e-9, "the axle stands proud of the slab under the cap"
SCREW_HOLE_D = 12.7                              # 1/2 in: the pulley's Ø11 flange and the drill
SCREW_IN_D = D.SCREW_OD + 0.4                    # through the bearing pocket's floor: the screw goes in from +Z
assert D.CHANGER_CEIL_Z < BRG_POCKET[3], "no floor between the room and the bearing"
# the cap's two heat-sets, clear of the axle slot, the bearing pocket and the rod
CAP_SCREWS = ((RX - 2.4, Y0 + 4.8), (X1 + 0.4, Y1 - 4.8))   # 1.75 of wall to the faces

# the buttress: the string pulls the bearing -X at z 16, 92 over the plank
FIN_X = 60.0

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
SCALE_SPAN = BX - CROWN_X                        # 607.0, crown dowel to bearing axle

OUT = pathlib.Path(__file__).resolve().parents[1] / "coupons"
_MAIN_COUPONS = pathlib.Path(__file__).resolve().parents[2] / "public-steel-guitar" / "coupons"


def _box(x0, x1, y0, y1, z0, z1):
    return box_at(x1 - x0, y1 - y0, z1 - z0, x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(z0 + z1) / 2)


def _zbore(d, x, y, z0, z1):
    return printable_bore(d, z1 - z0, axis_point=(x, y, z0), axis_dir=UP, print_up=UP)


def _wood_screw(x, y):
    """Clearance through the base and the 45 deg countersink from its top face."""
    zt = Z_PLANK + BASE_T
    clr = _zbore(WOOD_CLR_D, x, y, Z_PLANK - 1.0, zt + 1.0)
    csk = cq.Workplane("XY").add(cq.Solid.makeCone(WOOD_CLR_D / 2.0, WOOD_CSK_D / 2.0, WOOD_CSK_DEPTH,
                                                   pnt=cq.Vector(x, y, zt - WOOD_CSK_DEPTH)))
    return clr.union(csk).union(_zbore(WOOD_CSK_D, x, y, zt - 0.01, zt + 60.0))


# ═════════════════════════════════════════════════════════════════════════════════════════
def station() -> cq.Workplane:
    zb = Z_PLANK + BASE_T
    s = _box(X0 - 12.8, FIN_X + 2.0, Y0 - 11.6, Y_EDGE, Z_PLANK, zb)               # base
    s = s.union(_box(X0, X1B, Y0, Y1, zb - 0.01, SLAB_TOP))                          # the block
    for y0, y1 in ((Y0, Y0 + WALL), (Y1 - WALL, Y1)):                                 # buttress fins
        fin = (cq.Workplane("XZ").polyline([(X1B - 0.01, zb - 0.01), (FIN_X, zb - 0.01),
                                            (X1B - 0.01, BZ)]).close()
               .extrude(-(y1 - y0)).translate((0, y0, 0)))
        s = s.union(fin)
    # the bay: the lane under the rail, open -X for the belt
    s = s.cut(_box(X0 - 1.0, X1, SY - LANE, SY + LANE_HI, zb, RAIL_BOT))
    # the changer room: over the rail, under the slab, open -X for the hand that spins the nut on
    s = s.cut(_box(X0 - 1.0, X1, SY - LANE, SY + LANE, RAIL_TOP, D.CHANGER_CEIL_Z))
    # ...and open +X through the back wall, between the fins: the ear the string is threaded up
    # through is 8 mm in from there (user, 2026-11-07)
    s = s.cut(_box(X1 - 1.0, X1B + 1.0, SY - LANE, SY + LANE, RAIL_TOP, D.CHANGER_CEIL_Z))
    # THE SCREW GOES IN FROM BELOW with its pulley on, as in the instrument: a 1/2 in hole through
    # the floor, which is also the guide to drill the plank through
    s = s.cut(_zbore(SCREW_HOLE_D, SX, SY, Z_PLANK - 1.0, zb + 1.0))
    # the rail's seat, lip and boss passage (screw_rail.seat_cutter's diameters, round)
    s = s.cut(_zbore(D.SUPPORT_BRG_OD + 0.2, SX, SY, RAIL_BOT - 1.0, D.SUPPORT_BRG_Z + 1e-3))
    s = s.cut(_zbore(SR.SEAT_LEDGE_D, SX, SY, RAIL_BOT - 1.0, SR.LEDGE_TOP))
    s = s.cut(_zbore(SR.NUT_PASS_D, SX, SY, SR.LEDGE_TOP - 0.01, RAIL_TOP + 1.0))
    # the guide rod: blind socket in the rail, bore up through the slab
    s = s.cut(_zbore(ROD_BORE, RX, SY, SOCKET_Z, RAIL_TOP + 1.0))
    s = s.cut(_zbore(ROD_BORE, RX, SY, D.CHANGER_CEIL_Z - 1.0, SLAB_TOP + 1.0))
    # the bridge bearing's pocket, the screw's way in under it, and the string's slot down to the ear
    bx0, bx1, bh, bz0 = BRG_POCKET
    s = s.cut(_box(bx0, bx1, SY - bh, SY + bh, bz0, SLAB_TOP + 1.0))
    s = s.cut(_zbore(SCREW_IN_D, SX, SY, D.CHANGER_CEIL_Z - 1.0, bz0 + 0.5))
    s = s.cut(_box(D.string_anchor_x(I) - 1.6, D.BRIDGE_X + 1.6, SY - 1.6, SY + 1.6,
                   D.CHANGER_CEIL_Z - 1.0, bz0 + 0.5))
    # the axle's slot, open on top and out through both faces
    slot = cyl_y(AXLE_SLOT_D, Y1 - Y0 + 2.0, Y0 - 1.0, x=BX, z=BZ).union(
        _box(BX - AXLE_SLOT_D / 2, BX + AXLE_SLOT_D / 2, Y0 - 1.0, Y1 + 1.0, BZ, SLAB_TOP + 1.0))
    s = s.cut(slot)
    # the cap's heat-sets
    for x, y in CAP_SCREWS:
        s = s.cut(_zbore(M4.pilot_d(UP, UP), x, y, SLAB_TOP - M4.insert_depth, SLAB_TOP + 1.0))
        s = s.cut(_zbore(M4.shaft_clr_d, x, y, SLAB_TOP - M4.insert_depth - 3.0, SLAB_TOP))
    # wood screws: -X of the head block (reached from above before the belt goes on), and down
    # the middle of the buttress
    for x, y in ((X0 - 6.4, Y0 - 4.6), (X0 - 6.4, Y1 - 5.6), (24.0, SY), (52.0, SY)):
        s = s.cut(_wood_screw(x, y))
    return s


def cap() -> cq.Workplane:
    c = _box(X0, X1B, Y0, Y1, SLAB_TOP, SLAB_TOP + CAP_T)
    bx0, bx1, bh, _ = BRG_POCKET
    c = c.cut(_box(bx0, bx1, SY - bh, SY + bh, SLAB_TOP - 1.0, SLAB_TOP + CAP_T + 1.0))
    for x, y in CAP_SCREWS:
        c = c.cut(_zbore(M4.shaft_clr_d, x, y, SLAB_TOP - 1.0, SLAB_TOP + CAP_T + 1.0))
    return c


def _bay():
    """(bay, dummy board) from motor_bank's coupon, built on string 1's motor, at the plank's height."""
    from . import motor_bank as MB
    keep = MB.COUPON_MOTOR
    MB.COUPON_MOTOR = I
    try:
        bay, dummy = MB._coupon_world()
    finally:
        MB.COUPON_MOTOR = keep
    return bay.translate((0, 0, MOTOR_RISE)), dummy.translate((0, 0, MOTOR_RISE))


_BAY = None


def bay():
    global _BAY
    if _BAY is None:
        _BAY = _bay()
    return _BAY


def head() -> cq.Workplane:
    zb = Z_PLANK + BASE_T
    b, _dummy = bay()
    bb = b.val().BoundingBox()
    x0, x1, y0 = TOWER_X0 - 13.0, bb.xmax + 13.0, bb.ymin - 13.0
    h = _box(x0, x1, y0, Y_EDGE, Z_PLANK, zb).union(b)
    # the coupon's floor is a rim: the base fills its middle, so relieve it under the driver housing,
    # which hangs 0.1 under the can's floor line (servo42d, measured)
    h = h.cut(_box(MX - 21.3, MX + 21.3, MX_Y0, MX_Y0 + 13.5, zb - 0.4, zb + 0.01))
    # the belt's upper run leaves the motor pulley 1.5 deg off level here, and grazes the bay's
    # post by 0.16 where the instrument's level belt clears it: a relief, not a change to the bay
    h = h.cut(_box(MX + 9.0, MX + 20.0, MY - 2.7, MY - 1.2, MZ + 3.0, MZ + 5.5))
    # the crown tower, against the bay's -X wall, the Ø4 x 4 dowel in a cradle on top
    tz1 = CROWN_Z
    h = h.union(_box(TOWER_X0, bb.xmin + 0.8, TOWER_Y0, TOWER_Y1, zb - 0.01, tz1))
    h = h.cut(cyl_y(D.NUT_PIN_D + 0.2, D.NUT_PIN_L + 0.4, SY - (D.NUT_PIN_L + 0.4) / 2,
                    x=CROWN_X, z=CROWN_Z))
    # the tail's side: 45 deg off the -X top corner, under the line to the tuner
    c = CROWN_X - 3.3
    h = h.cut(cq.Workplane("XZ").polyline([(TOWER_X0 - 1.0, tz1 + 1.0), (c, tz1 + 1.0), (c, tz1),
                                           (TOWER_X0, tz1 - (c - TOWER_X0)),
                                           (TOWER_X0 - 1.0, tz1 - (c - TOWER_X0))]).close()
              .extrude(-(TOWER_Y1 - TOWER_Y0 + 2.0)).translate((0, TOWER_Y0 - 1.0, 0)))
    for x, y in ((x0 + 6.5, y0 + 6.5), (x0 + 6.5, Y_EDGE - 6.5), (x1 - 6.5, y0 + 6.5), (x1 - 6.5, Y_EDGE - 6.5)):
        h = h.cut(_wood_screw(x, y))
    return h


def tee_dummy() -> cq.Workplane:
    return bay()[1]


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


def _string(tail_x=-770.0):
    """Ball end -> up past the ear -> over the bearing -> crown -> down to a tuner at tail_x."""
    g = D.STRING_GAUGE[I]
    r, R = g / 2.0, D.BRIDGE_BEARING_OD / 2 + g / 2.0
    az = D.NUT_TOP_Z - D.NUT_FLANGE_T - D.STRING_NUT_D / 2
    a0 = math.radians(5.0)                                 # the rise touches just +X of the top's right
    pts = [(BX + R * math.cos(a0 + (math.pi / 2 - a0) * k / 8), SY, BZ + R * math.sin(a0 + (math.pi / 2 - a0) * k / 8))
           for k in range(9)]
    crown = (CROWN_X, SY, D.STRING_Z - r)
    path = [(D.string_anchor_x(I), SY, az)] + pts + [crown, (tail_x, SY, Z_PLANK + 15.0)]
    out = None
    for a, b in zip(path, path[1:]):
        sgm = _seg(a, b, r)
        out = sgm if out is None else out.union(sgm)
    return out


def assembly():
    """Everything, placed: the two printed parts and the cap, and every bought part on them."""
    args, gap, cloc = _belt_bits()
    mp_deg, sp_deg = C.belt_mesh(*args, BTn.BELT_TOOTH_IN)
    out = [("plank_station", station()), ("plank_cap", cap()), ("plank_head", head())]
    out.append(("leadscrew_0", C.screw().translate((SX, SY, D.SCREW_BOT_Z))))
    out.append(("nut_0", C.nut().translate((SX, SY, D.NUT_TOP_Z))))
    out.append(("string_nut_0", C.string_nut().translate(
        (D.string_anchor_x(I), SY, D.NUT_TOP_Z - D.NUT_FLANGE_T - D.STRING_NUT_D / 2))))
    out.append(("guide_rod_0", C.guide_rod(D.GUIDE_ROD_L).translate((RX, SY, SOCKET_Z))))
    out.append(("rod_plug_0", cyl(ROD_PLUG_D, ROD_PLUG_L, ROD_TOP).translate((RX, SY, 0))))
    out.append(("screw_pulley_0", C.screw_pulley(high=D.screw_pulley_z(I) > D.SCREW_PULLEY_Z)
                .rotate((0, 0, 0), (0, 0, 1), sp_deg).translate((SX, SY, D.screw_pulley_z(I)))))
    out.append(("screw_bearing_0_0", C.support_bearing().translate(
        (SX, SY, D.SUPPORT_BRG_BOT + 0.5 * D.BRG688_W))))
    out.append(("bridge_bearing_0", C.support_bearing().rotate((0, 0, 0), (1, 0, 0), 90)
                .translate((BX, SY, BZ))))
    out.append(("bridge_axle_rod", cyl_y(D.BRIDGE_AXLE_D, D.BRIDGE_AXLE_L, SY - D.BRIDGE_AXLE_L / 2, x=BX, z=BZ)))
    out.append(("crown_dowel", C.dowel().translate((CROWN_X, SY, CROWN_Z))))
    for k, wp, _rgb, _fin in C.motor_parts():
        out.append((f"motor_{k}_0" if k else "motor_0", wp.translate((MX, MY, MZ))))
    out.append(("motor_pulley_0", C.motor_pulley(-mp_deg).rotate((0, 0, 0), (0, 1, 0), mp_deg)
                .translate((MX, MY, MZ))))
    out.append(("belt_0", C.belt(*args)))
    for nm, shp in BTn.clamp_components(gap):
        out.append((f"{nm}_0", cq.Workplane("XY").add(shp.val().moved(cloc))))
    from . import wiring as W
    for nm, shp in W.tee_components():
        if nm.endswith("_0") and nm.startswith(("tee_pcb", "tee_silk", "tee_insert", "tee_screw")):
            out.append((nm, shp.translate((0, 0, MOTOR_RISE))))
    for k, (x, y) in enumerate(CAP_SCREWS):
        out.append((f"cap_insert_{k}", seated_insert(M4, (x, y, SLAB_TOP), (0.0, 0.0, -1.0))))
        out.append((f"cap_screw_{k}", m4_button_screw(10.0).rotate((0, 0, 0), (1, 0, 0), 180)
                    .translate((x, y, SLAB_TOP + CAP_T))))
    out.append(("string_0", _string()))
    return out


def print_parts():
    """{name: solid in its print pose}: the two bases down on z 0, the cap flat."""
    out = {}
    for nm, w in (("plank_station", station()), ("plank_head", head()), ("plank_cap", cap()),
                  ("plank_tee_dummy", tee_dummy())):
        bb = w.val().BoundingBox()
        out[nm] = w.translate((-bb.xmin, -bb.ymin, -bb.zmin))
    return out


if __name__ == "__main__":
    from cadkit.step_export import export_step
    print(f"scale span {SCALE_SPAN:.2f}  plank top z {Z_PLANK:.2f}  edge y {Y_EDGE:.2f}")
    for nm, w in print_parts().items():
        bb = w.val().BoundingBox()
        print(f"{nm:14s} {bb.xlen:6.1f} x {bb.ylen:5.1f} x {bb.zlen:5.1f}  vol {w.val().Volume():8.0f} mm3"
              f"  solids {len(w.solids().vals())}")
        for d in (OUT, _MAIN_COUPONS):
            if d.is_dir():
                export_step(w, str(d / f"{nm}.step"))
