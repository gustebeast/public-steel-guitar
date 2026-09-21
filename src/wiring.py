"""Wire harness: gauge-colored round cables, modeled as cylinder chains.

STRATEGY (July 2026, BOM 'Connectors' section): solder only on PCBs, every
field connection a connector, never inline-splice. Both CAN buses are
TRUNK-AND-DROP over TEE PCBs (electronics.tee_pcb, flat on the floor):
crimped XH jumper SEGMENTS run tee-to-tee (each drawn as its own component,
suffix _N — a segment IS a separate physical cable), and each device hangs
by ONE drop, so unplugging a device never breaks a bus. 120 Ω termination
lives on the boards (motor_ctrl + each bus's LAST tee, jumper closed).

  bus A (motors): motor_ctrl -> tee 9..0 (one per motor; LAST = tee 0,
        easternmost — its jumper is closed). Drop = the SERVO42D's own
        6-pin XH pigtail (motor_pigtail_N, grey). The 24 V pair rides the
        same tees (2 contacts per rail on the 6-pos trunk headers): head
        = DC inlet -> the AFE tee (10) -> tee 0; tail = tee 9 -> buck.
  bus B (inputs): motor_ctrl -> the lever/pedal boards, WITH NO TEES AT ALL
        (user, 2026-09-14). Tees 11 and 12 are deleted: 11 existed to tap
        the trunk at the knee station, which the lever board's own 8-way
        pass-through (in 1-4, out 5-8) now does on the board, and 12
        existed to land the chassis TRRS jack's factory cable, which the
        TRRS ADAPTER BOARD now does with the jack soldered on. Both were
        junctions that only existed because the thing either side of them
        could not terminate itself; both ends can now.

One component per physical CABLE. Discrete wires (the 24 V pair) are drawn
individually; jacketed/bundled runs at the bundle OD. Colors (build.py):
HUE = gauge bucket, SHADE = the specific wire within the bucket:

  CAN BUS COLOURS (user override): the CAN + power trunk is shown as its four
  colour-coded conductors, NOT the gauge/shade rule below:
      BLACK  = wire_pwr_gnd  (CAN ground / 0 V return)
      RED    = wire_pwr_hot  (CAN 24 V)
      YELLOW = wire_can*h    (CAN-H, both buses + the transceiver jumper)
      GREEN  = wire_can*l    (CAN-L)
  Each CAN bus is drawn as its CAN-H/CAN-L pair (split ±CAN_OFF): bus A
  (wire_canh/l, motors) and bus B (wire_canbh/l, inputs), both leaving the motor
  controller's own connectors. There is no transceiver jumper any more -- the
  transceivers sit on the MCU's board, so that harness became copper.

  The gauge/shade rule still governs the NON-CAN nets:
  BLUE = power pair       (superseded for the CAN power rails above)
  AMBER = 28 AWG logic    (light -> dark) wire_link (motor controller <-> Pi),
                          wire_oled, wire_joy
  VIOLET = shielded USB-2 wire_usb: USB-C panel -> Pi 5
  GREY = factory jackets  motor_pigtail_N

Analog architecture: NONE OF IT IS HERE. The AFE board is deleted and no audio
crosses this harness -- the optical pickup board carries the magnetic pickup's
buffer, its bypass relay and the jack output, and reaches the Pi over USB. What
runs through the bay is DC bus, CAN, and logic.

Routing: a 6-lane floor trunk at z -69.7 (under the motors) passes every
cross-rib through SHALLOW gable raceways (chassis._raceway) whose floor stays
0.4 clear of the knee-lever rib-mortise tip (-71.42) -- the harness never
blocks a floating tenon sliding to ANY knee depth. Trunk segments still ride
those lanes rib-to-rib; they dip to z -72.6 (between ribs, clear of the
mortise plane) to land on their tee headers. Wire ends clip ~1-2 mm into
their declared source/destination bodies to show the connection
(whitelisted); everywhere else the gate enforces clearance.

The SERVO42D driver is ON the motor, so there are NO stepper phase leads --
the harness is DC bus, CAN and logic only. Insulation is not
an EMI defence: noise immunity comes from SHIELDING (audio), TWISTING
(power, CAN) and buffering at the source (the AFE at the bridge).
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import electronics as EL
from .helpers import oct_cable

# modeled cable OD per net (mm): jacketed bundles (shielded/USB) drawn as ONE
# round conductor at the jacket OD; the 24 V pair AND the CAN pairs as discrete
# conductors (user override: the CAN bus is shown as its four colour-coded
# wires -- black gnd, red 24 V, yellow CAN-H, green CAN-L). Nothing exceeds 2.6.
WIRE_OD = {
    "wire_usb": 2.6,
    "wire_pickup": 2.0,   # DORMANT, kept: the magnetic pickup's screw-terminal
                          # run returns when the optical pickup board is designed
                          # (see the AFE note in build_wires). The other four AFE
                          # cables are gone for good.
    # CAN signal pairs, split into CAN-H / CAN-L discrete conductors
    "wire_canh": 1.3, "wire_canl": 1.3,       # bus A (motors)
    "wire_canbh": 1.3, "wire_canbl": 1.3,     # bus B (inputs)

    "wire_pwr_hot": 1.8, "wire_pwr_gnd": 1.8,
    # 5 V to the Pi's GPIO header. 20 AWG PAIR, not signal wire: the Pi's
    # undervoltage trip is 4.63 V against a 5.00 nominal, so the whole budget is
    # 0.37 V and the cable may not eat it. Over this run 20 AWG spends 0.03.
    "wire_5v": 1.8,
    "wire_link": 1.4,
    "wire_oled": 1.4, "wire_joy": 1.4,
    "motor_pigtail": 3.4,
}
# Where bus B lands at the knee station: as close to the LKL lever board's XH as the
# chassis CAD lets the trunk reach today, clear of the packed -X corner. The last few
# millimetres onto the board are a chassis follow-up.
_KNEE_B = (-508.0, -110.0, -60.0)
CAN_OFF = 0.7         # CAN-H / CAN-L conductor separation (both x and y, same
                      # scheme as PWR_OFF): the split pair stays inside the old
                      # single-jacket envelope (0.7 + 0.65 = 1.35 < the 2.4/2 it
                      # replaces) so the trunk footprint is unchanged.
# ⚠ THE TEE-TO-TEE TRUNK IS ONE 4-WAY CABLE, AND ITS FOUR CONDUCTORS WERE ON ONE LINE 0.3 mm
# APART. The hops drew CAN at +-CAN_OFF (0.7) and 24 V at +-PWR_OFF (1.0), both along the same
# diagonal, so CAN-H ran through 24 V hot and CAN-L through ground on every hop -- 18 pairs,
# ~80 mm3 each over 45.8 mm, never reported (the gate allow-lists wire against wire). Spread
# as a flat set at 1.8, which clears the fattest neighbours (O1.8 beside O1.3 needs 1.55):
TRUNK_OFF = {"hot": -2.7, "canh": -0.9, "canl": 0.9, "gnd": 2.7}
PWR_OFF = 1.0         # 24 V hot/gnd separation. In X on the bank hops (see _seg) and in Z
                      # along the -Y corridor, where the pair rides one lane each. 2.0 apart
                      # leaves 0.2 of air between two O1.8 conductors, which is right for a
                      # pair that is BIFILAR on purpose -- they are meant to stay together.
                      # (Was 1.2 in both x and y. The y half is what had to go: 2.4 across a
                      # corridor only 3.2 deep behind the channel's straps put one conductor
                      # in a strap.)
WIRE_D = 2.0          # default (shielded-pair size)

# ── -Y RAIL harness corridor ──────────────────────────────────────────────
# The ribs are STRUCTURE + lever mounts ONLY: a knee/pedal lever slides along its rib
# mortise to ANY depth in ANY bay, so a cable sitting in a rib would block a lever from
# being installed there. So NO wire crosses a rib. The whole X-running trunk instead
# hugs the -Y rail's INNER FACE, ABOVE the rib tops (z > FLOOR_TOP -65.15) where no rib
# reaches and -- except the +X-most motor (m9) -- no motor body reaches either. The tees
# mount on the rail (each on a pcb_cradle); every motor's drop pigtail reaches from its
# -Y-facing PCB out to its tee. Past m9 the rail is notched (chassis motor-9 cable cut).
from .chassis import Y_LO as _Y_LO, Y_HI as CH_Y_HI, T as _RAIL_T
from .chassis import SPLIT_X as CH_SPLIT_X
from .chassis import WT_LANE_Y as CH_WT_LANE_Y, WT_ZF as CH_WT_ZF, WT_H as CH_WT_H
from .chassis import WT_X1 as CH_WT_X1, WT_RUNS as CH_WT_RUNS
from . import motor_bank as MB                          # back_y: where each motor's pigtail leaves
from .motor_bank import FLOOR_TOP as _RIB_TOP           # -65.15 (rib tops = above = rib-free)
RAIL_INNER_Y = _Y_LO + _RAIL_T / 2                       # -128.75: -Y rail inner face
RAIL_Y = RAIL_INNER_Y + 4.5                              # the old floor-level corridor, which
                                                         # only bus B still uses at the keyhead
TEE_Y  = RAIL_INNER_Y + 8.0                              # tee-board centre (14mm-deep board clears wall)
# ── THE -Y CORRIDOR IS THE WIRING TROUGH NOW (chassis.WT_*), ABOVE THE MOTORS ──────────
# It used to be a pocket cut into the rail below the motor tops; the user moved it OUT of
# the wall and UP (the wall is the body's side beam). Everything that runs the length of
# the instrument rides it, stacked in Z inside a 4.8 mm-wide space, at one y (CHAN_Y):
# ⚠ THE STACK STARTS 1.5 OFF THE FLOOR, NOT ON IT. Where the trough is left out -- over
# string 10's motor -- the cables carry on at the same height, and two chassis walls either
# side of that motor stand to -25.45: a lane on the floor (-26.4) clipped both. From there
# up the stack is packed flat-to-flat (the octagons are rolled so their flats face up and
# down), and still finishes under the lip's top at -13.6.
LANE_PWR2  = CH_WT_ZF + 3.5      # -22.9: the 24 V bypass feed (J10 -> motor_ctrl),
                                 #        hot -23.9 / gnd -21.9, 0.65 over those walls
LANE_USB   = CH_WT_ZF + 7.1      # -19.3: output board J2 -> the Pi (O2.6)
LANE_PWR   = CH_WT_ZF + 10.8     # -15.6: the 24 V head (J7 -> the east tee), hot -16.6 /
                                 #        gnd -14.6 -- first trough piece only, it leaves
                                 #        at string 10's motor for that motor's tee
LANE_CTRL  = -42.0               # CAN bus B: keyhead-local, on the old floor corridor
LANE_CAN   = -48.0               # CAN bus A: bank hops only (never on the corridor)
TEE_Z = _RIB_TOP + 4 * D.BEAD                            # 3.2 of printed cradle on the rib tops
_TRUNK_OD = max(od for nm, od in WIRE_OD.items() if nm != 'motor_pigtail')
# the trough's own guarantees, asserted where the lanes are chosen:
_TOP_OF_MOTORS = D.MOTOR_BELT_Z + D.MOTOR_SQ / 2          # -29.05
assert CH_WT_ZF > _TOP_OF_MOTORS, "the trough's floor has come down to the motor tops"
assert LANE_PWR2 - PWR_OFF - 1.8 / 2 > CH_WT_ZF, "feed 2 is in the trough's floor"
assert LANE_PWR + PWR_OFF + 1.8 / 2 < CH_WT_ZF + CH_WT_H, "the head stands over the lip"
assert CH_WT_LANE_Y + _TRUNK_OD / 2 <= MB.HARNESS_Y1, (
    "the trough's lane reaches y %.2f, past motor_bank's HARNESS_Y1 %.2f"
    % (CH_WT_LANE_Y + _TRUNK_OD / 2, MB.HARNESS_Y1))
HDR_Z = -54.0                                            # lifted tee header top (wire entry z)

_M9X = D.motor_pos(9)[0]
M9_X0, M9_X1 = _M9X - D.MOTOR_SQ / 2 - 2.0, _M9X + D.MOTOR_SQ / 2 + 2.0
CHAN_Y = CH_WT_LANE_Y                    # -126.35: inside the trough
CUTOUT_Y = RAIL_INNER_Y - 1.25           # motor 9's pigtail lies in the rail notch itself


def _rail_pts(x0, x1, z):
    """Points riding the -Y corridor -- the trough -- from x0 to x1 at height z.

    ONE straight line now. The pocket this replaced broke at every split plane (it could not
    cut through the seam joint) and the cables stepped out and back each time; a trough
    standing off the wall has nothing to dodge, and where it is left out -- over string 10's
    motor, and a hair at each seam -- the cables carry on at the same line, above the motor."""
    return [(x0, CHAN_Y, z), (x1, CHAN_Y, z)]


def _wire(pts, d=WIRE_D):
    """Polyline cable, OCTAGONAL section, across-flats d -- see helpers.oct_cable.

    It was cylinders with sphere elbows, fused first as a chain of pairwise unions (which
    silently dropped cable: 1100 mm3 of one feed gone, no exception), then as one
    multi-fuse checked by volume, then with a sphere-free fallback when the spheres broke
    every tolerance. The user's call (2026-09-21) was to stop fighting round geometry: flat
    faces fuse reliably and check fast, and across-flats = the cable's diameter keeps the
    real cable inside the model."""
    return oct_cable(pts, d)


def _floor_pts(x0, x1, z):
    """The old floor-level corridor at RAIL_Y, which bus B still uses at the keyhead: it runs
    motor controller -> lever boards low down, where the lever boards are, and has no reason
    to climb over the motors and back."""
    return [(x0, RAIL_Y, z), (x1, RAIL_Y, z)]


# ── tee stations (all on the -Y rail corridor) ────────────────────────────
def _motor_back(i):
    return MB.back_y(i)                      # -Y-most face of motor i (PCB back)


def tee_stations():
    """[(x, y, drop_sign)] tee-PCB anchors, all on the -Y rail (TEE_Y) so the CAN trunk
    stays on the rail and never crosses a rib. 0..9 bus A, ONE PER MOTOR AND NOTHING
    ELSE -- a tee board exists to give a motor power and CAN, so a tee that serves no
    motor has no reason to be a board (user, 2026-09-18). Tee 10 used to sit here as the
    optical pickup board's 24 V drop; that board is fed from the output panel's J9 and
    has no CAN at all, so the drop was feeding a board fed from somewhere else.
    THERE ARE NO BUS-B TEES either -- 11 (knee) and 12 (leg-socket) are deleted; see the
    module docstring. The two +X-most motors (8,9) reach the rail, so a tee
    dead-behind them would sit inside the motor -- their tees shift into the clear corridor
    (m8 -X toward m7, m9 +X past the motor bank) and reach back with a longer pigtail."""
    out = []
    for i in range(10):
        mx = D.motor_pos(i)[0]
        # m9's body sits AT the rail (its tee would be buried in it) -> park m9's tee just past the
        # motor bank in the clear corridor; every other motor's tee rides the rail at its own X (m8's
        # tee corner just grazes m8's PCB, a whitelisted mount contact).
        out.append((mx, TEE_Y, +1))
    return out


_TEE_LIFT = TEE_Z - EL.FLOOR_Z          # lift a RAIL tee dummy onto its cradle, above the rib tops

# ── TEES ON THE MOTORS (user, 2026-09-14) ───────────────────────────────────
# Bus-A tees 0..9 no longer ride the rail: each sits on its own motor's pocket, resting on the
# faceplate wall's top and LAPPING the motor, so the one M4 that holds the board down also stops
# the motor lifting out -- board and motor share a screw. The drop pigtail becomes a hand's
# breadth instead of a reach to the rail, and the trunk flies tee to tee over the bank.
# ALL TEN, including string 10: side entry (7.0 tall, not the 9.8 of a mated top-entry pair)
# clears the magnetic pickup's neck-most position over that motor by 1.4, so the exception that
# kept its tee on the rail is gone.
N_MOTOR_TEES = D.N_STRINGS


def on_motor(i):
    return i < N_MOTOR_TEES


def tee_center(i, x, y):
    """(cx, cy) of tee i's board."""
    if on_motor(i):
        # the bay itself is cut for the board (motor_bank.tee_board_box): the seat is the same
        # prism as the pocket, so the board's placement comes from there rather than from here
        bx0, bx1, by0, by1, _ = MB.tee_board_box(i)
        return (bx0 + bx1) / 2, (by0 + by1) / 2
    return x, EL.tee_board_cy(y)


def tee_z(i):
    """Board-underside Z for tee i."""
    return MB.tee_board_box(i)[4] if on_motor(i) else TEE_Z


def tee_hdr_z(i):
    """Where a wire lands on tee i: mid-mouth on a motor tee, the header top on a rail one."""
    from cadkit.pcb import XH_SIDE_H
    return (tee_z(i) + _PCB_T + XH_SIDE_H / 2) if on_motor(i) else HDR_Z


def tee_point(i, x, y, which="trunk"):
    """The 3D point a wire lands on: tee i's trunk (8-way) or drop (4-way) connector."""
    from cadkit.pcb import xh_side_length
    cx, cy = tee_center(i, x, y)
    if not on_motor(i):
        return cx, cy + EL.TEE_CONN_CY, tee_hdr_z(i)
    l8 = xh_side_length(EL.TEE_TRUNK_N, smt=False)
    l4 = xh_side_length(EL.TEE_CONN_N, smt=False)
    run = l8 + l4
    dx = (-run / 2 + l8 / 2) if which == "trunk" else (run / 2 - l4 / 2)
    # the cable arrives at the MOUTH, which faces -Y: it runs out over the motor, not upward
    return cx + dx, cy + EL.TEE_CONN_CY - EL.TEE_MOUTH_DY - 2.0, tee_hdr_z(i)


# ── TEE RETENTION: ONE M4 THROUGH THE BOARD'S EAR (user: one driver, one insert SKU) ──
# It was one M2 down through a board hole. cadkit's pcb_cradle now takes the screw BESIDE
# the board (hold_edge): the walls capture every direction but +Z, and the button head laps
# the board edge to close +Z, so the board needs no hole at all. tee_hold() is the ONE
# table of per-tee choices, and it feeds the cradle, the dummy screw AND the post-fuse
# re-bore -- so the part that is bored and the screw the overlap gate checks cannot disagree.
MOTOR_SEAT_SO = 0.8         # a motor-seat cradle's pads under the board (the rail's is 3.2):
                            # every mm here is a mm the board sits further off the motor it laps
TEE_SCREW_L   = 10.0        # M4x10 button: head on the board top, tip inside the anchor
TEE_CLR       = 0.3         # board fit gap in the cradle; also sets where the hold screw sits
TEE_WALL_OVER = 1.2         # cradle walls stand this far above the board top
# (_BUS_B_M2_XY is NOT carried over from main: it located the M2 through the bus-B
#  PLACEHOLDER tees, and 11/12 are deleted on this branch (user). With them went the
#  last M2 in the tee family -- one screw diameter, one driver.)
_EAR_XY       = (D.TEE_BOARD_X / 2,         # the accurate board's M4 THROUGH-hole, board-local
                 (D.TEE_BOARD_Y - D.TEE_EAR_Y) / 2)   # (centred in the bare ear off its +X end)
from cadkit.fasteners import M4 as _M4
from cadkit.pcb import PCB_T as _PCB_T
assert TEE_SCREW_L - _PCB_T <= _M4.anchor_min_wall + 1e-9, (
    f"tee hold-down M4x{TEE_SCREW_L:g} reaches {TEE_SCREW_L - _PCB_T:.2f} below the board's "
    f"underside, past the {_M4.anchor_min_wall} anchor the cradle bores -- it would bottom out")


def tee_hold(i, x, y, d):
    """(board_w, board_l, centre_x, centre_y, open_edge, hold_edge, hold_at) for tee i.

    EVERY TEE IS NOW THE SAME BOARD ON THE SAME M4 THROUGH ITS EAR. Main still carried
    an `i >= 11` branch for the bus-B PLACEHOLDERS and their M2 through the board; those
    tees are deleted (user), so the branch is gone and with it THE LAST M2 IN THE TEE
    FAMILY -- one screw diameter, one driver."""
    if on_motor(i):
        # ON A MOTOR: the board's -Y half laps the motor, so that edge can have no wall (a wall
        # there would overhang the motor and trap it) -- and a screw BESIDE the board only laps
        # its edge, which friction alone then has to hold against a -Y tug (user, 2026-09-15:
        # every unplug is one, since the mouths face -Y). So the screw goes THROUGH the board,
        # down the bare ear off its +X end into the post: positive in X and Y, not frictional.
        cx, cy = tee_center(i, x, y)
        return (D.TEE_OUTLINE_X, EL.TEE_BOARD_Y, cx, cy, "-x", "through", None)
    # ⚠ UNREACHABLE SINCE TEE 10 WENT: every tee is on a motor now, so on_motor() above
    # always takes it. Kept as the rail-mounted form -- a cradle on the rib tops with all
    # four walls closed -- because it is the shape any future rail tee would want, and
    # raising here instead would lose that. If nothing rail-mounted returns by the time
    # this file is next touched, delete it rather than letting it rot.
    return D.TEE_OUTLINE_X, EL.TEE_BOARD_Y, x, EL.tee_board_cy(y), None, "through", None



def tee_components():
    """The tee-PCB dummies for the assembly, lifted onto their -Y-rail cradles (above the
    rib tops so no tee sits in a rib), each M4-held tee with its screw and insert placed
    from the same tee_hold() the cradle is bored from. See tee_cradles()."""
    from cadkit.fasteners import M4_BUTTON_HEAD_H, m4_button_screw, seated_insert
    from cadkit.pcb import pcb_hold_xy
    out = []
    for i, (x, y, d) in enumerate(tee_stations()):
        # main's placement wins: the tee now sits at its own tee_z (on a motor, or the
        # rail for tee 10), not at one shared lift. `accurate` is vestigial with the
        # placeholders gone, so every tee is the real board.
        bw, bl, cx, cy, _open, hold_edge, hold_at = tee_hold(i, x, y, d)
        z0 = tee_z(i)
        out.append((f"tee_pcb_{i}", EL.tee_pcb(cx, cy - EL.TEE_YSHIFT, d)
                    .translate((0, 0, z0 - EL.FLOOR_Z))))
        if hold_edge is None:
            continue
        hx, hy = _EAR_XY if hold_edge == "through" else pcb_hold_xy(
            bw, bl, hold_edge, hold_at=hold_at, clr=TEE_CLR)
        out.append((f"tee_insert_{i}", seated_insert(_M4, (cx + hx, cy + hy, z0), (0, 0, -1))))
        out.append((f"tee_screw_{i}", m4_button_screw(TEE_SCREW_L).translate(
            (cx + hx, cy + hy, z0 + _PCB_T + M4_BUTTON_HEAD_H))))          # head seated on the board top
    return out


# ── TRRS ADAPTER STATION -- the -X/+Y leg's cable into the instrument ─────
# THE LEG UNPLUGS BEFORE IT SLIDES OUT, so this station is chosen by where a HAND
# can reach a plug, not by where a board fits tidily. The plug is on the
# instrument's -Z UNDERSIDE (user, with the spot circled): it looks straight DOWN
# through a bore in the chassis floor, a hand's reach inboard of the leg, and the
# lead from the body adapter never comes round to a face you can see. An earlier
# pass had it mouthing +Y through the back rail, which is exactly the face the
# player looks at.
#
# THE BOARD IS A REQUEST TO BRONNER, and this is the second one -- it REPLACES the
# earlier "put the jack on the long edge". What the station needs now is a
# BOARD-PERPENDICULAR (vertical-entry) 3.5 mm 4-pole jack: barrel along the board's
# normal, mouth through the board. Everything else about the board is unchanged and
# every size below still comes from electronics.py. The reason is room, and it is
# not close: a board-PARALLEL jack can only look -Z if the board stands on edge, and
# a board on edge is 26 tall in a cavity whose only solid floor is under the
# electronics tray, with 9.5 between that floor and the tray's underside.
# _trrs_board_as_asked is what gets deleted when the respin lands.
#
# WHAT SETS THE POCKET, all of it measured on the BUILT chassis rather than reasoned
# about:
#   * THE FLOOR is a 10.3 slab, -81.8 (the instrument's underside, and this
#     segment's print bed) to -71.5. Over the leg and just outboard of here the slab
#     is a RIB LATTICE with open cells; it goes fully solid from x -608 inboard. The
#     port and the screw's anchor both want solid slab, so the station sits at
#     x -604, in that band and as far out toward the leg as the band reaches.
#   * ABOVE is the electronics tray, whose plate starts at z -62. The cradle's top
#     is -66.6, so it passes under it -- which is only possible because the screw's
#     anchor goes down into the SLAB instead of into a 6.0 base plate of its own.
#   * The plug hangs ~17 below the underside. That is the price of a plug you can
#     reach without taking the instrument apart.
TRRS_FLOOR_TOP = -71.5      # the chassis floor's upper face at this station
TRRS_FLOOR_BOT = -81.8      # ...and the instrument's underside: this segment's bed
TRRS_X = -755 * D.BEAD      # -604.0: in the solid band, and as far outboard (toward
TRRS_Y = 0.0                # the leg) as that band reaches
TRRS_CLR = TEE_CLR          # the tees' own board fit, wall stand-off and screw: one
TRRS_WALL_OVER = TEE_WALL_OVER      # cradle idiom on this instrument, not two
TRRS_SCREW_L = TEE_SCREW_L          # M4x10 button, 2.5 hex -- the one lock (user)
# THE ADAPTER BOARD IS GONE (user, 2026-09-16): the leg column became an off-the-shelf
# TRRS extension lead, so electronics no longer carries TRRS_BOARD_* / TRRS_PLUG_* /
# TRRS_JACK_*. This station is PARKED, not deleted, and it still reasons in the board's
# dimensions -- so they live here now as plain numbers rather than as imports of a thing
# that does not exist. Values are the board as it last stood (20.0 x 31.0, a mated plug
# needing 30.0 of run at O10.0, the jack 15.18 across x 10.09 tall).
TRRS_ACROSS = 20.0                          # across X
TRRS_ALONG = 31.0                           # along Y
TRRS_PLUG_D = 10.0                          # the plug handle's diameter
TRRS_PLUG_RUN = 30.0                        # what a MATED plug needs clear of the mouth
TRRS_JACK_W = 15.18                         # the jack body, across
TRRS_JACK_L = 10.09                         # ...and tall
TRRS_PORT_D = TRRS_PLUG_D + 0.8             # 10.8: the plug's handle passes THROUGH the
                                            # floor slab to reach the mouth -- a socket
                                            # has to be met by the plug's shoulder, and
                                            # the slab is 10.3 of that reach
_TRRS_STANDOFF = 2.5
_TRRS_BASE_T = 1.6          # NOT pcb_cradle's default 6.0. That default exists so the
                            # M4's anchor fits above the mounting surface; here the
                            # mounting surface IS the floor slab and the anchor bores
                            # 8.5 down into 10.3 of it, so the plate is just a plate.
                            # Paying the 6.0 would put the cradle's top through the
                            # electronics tray.


def trrs_station():
    """(centre x, centre y, mounting surface z) -- the board's outline in the world."""
    return TRRS_X, TRRS_Y, TRRS_FLOOR_TOP


def trrs_board_z():
    """The board's underside. pcb_cradle measures its standoff from the MOUNTING
    SURFACE (its base plate hangs BELOW that), so this is not base + plate + standoff
    -- getting that wrong floats the board 6.0 clear of the pads that hold it."""
    return TRRS_FLOOR_TOP + _TRRS_STANDOFF


def trrs_mouth_z():
    """The jack's mouth: through the board, looking -Z."""
    return trrs_board_z()


def trrs_cradle():
    """The drop-in cradle, standing on the floor slab. Walls on ALL FOUR edges -- no
    rail to borrow here -- so the only way the board can leave is the way it went in
    (+Z), and the one M4 beside its -Y edge closes that."""
    from cadkit.fasteners import M4_BUTTON_HEAD_D
    from cadkit.pcb import pcb_cradle
    cx, cy, z0 = trrs_station()
    cr = pcb_cradle(TRRS_ACROSS, TRRS_ALONG, open_edge=None, hold_edge="-y",
                    standoff=_TRRS_STANDOFF, wall_over=TRRS_WALL_OVER, clr=TRRS_CLR,
                    base_t=_TRRS_BASE_T, hold_spec=_M4, head_d=M4_BUTTON_HEAD_D)
    cr = cr.translate((cx, cy, z0))
    return cr.union(_trrs_footing(cr.val().BoundingBox()))


def _trrs_footing(bb):
    """WHAT THE CRADLE STANDS ON. The floor slab here is not a plate but a RIB
    LATTICE with open cells, and a base plate laid across it is a bridge, not a
    foundation (measured: 79 mm2 of the plate had nothing under it). So the cells
    under the cradle's own footprint are FILLED, slab bottom to slab top -- and the
    slab's bottom is this segment's print bed, which makes the fill the first layer
    rather than an island. The footprint comes from the cradle's OWN bounding box:
    the M4's boss stands proud of the base plate on the -Y side, and sizing this by
    hand is how that boss ends up hanging."""
    from .helpers import oct_cable, box_at
    return box_at(bb.xlen, bb.ylen, TRRS_FLOOR_TOP - TRRS_FLOOR_BOT,
                  x=bb.center.x, y=bb.center.y,
                  z=(TRRS_FLOOR_BOT + TRRS_FLOOR_TOP) / 2.0)


def trrs_port():
    """The bore the plug reaches up along, straight down through the floor slab and
    out the instrument's underside. It runs along the chassis's own build direction,
    so it needs no teardrop: a +Z bore prints round."""
    import cadquery as cq
    cx, cy, _ = trrs_station()
    z0 = TRRS_FLOOR_BOT - 1.0
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        TRRS_PORT_D / 2.0, (trrs_mouth_z() + 0.5) - z0,
        cq.Vector(cx, cy, z0), cq.Vector(0, 0, 1)))


def trrs_hold_negatives():
    """The cradle's own anchor and head notch, in the world -- build.py re-cuts them
    after the fuse, the same refill trap the tees have. The anchor lands in the floor
    slab, which is why the base plate can be 1.6."""
    import cadquery as cq
    from cadkit.fasteners import M4_BUTTON_HEAD_D, anchor_cutter
    from cadkit.pcb import pcb_hold_xy
    cx, cy, _ = trrs_station()
    hx, hy = pcb_hold_xy(TRRS_ACROSS, TRRS_ALONG, "-y", clr=TRRS_CLR, spec=_M4)
    wx, wy = cx + hx, cy + hy
    bz = trrs_board_z()
    out = [anchor_cutter(_M4, (wx, wy, bz), (0, 0, -1), _M4.anchor_min_wall,
                         overshoot=1.0, print_up=(0.0, 0.0, 1.0))]
    out.append(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        (M4_BUTTON_HEAD_D + 2 * TRRS_CLR) / 2.0, _PCB_T + TRRS_WALL_OVER + 1.0,
        cq.Vector(wx, wy, bz), cq.Vector(0, 0, 1))))
    return out


def trrs_components():
    """The assembly's dummies: the board on its cradle, the screw and its insert, and
    the MATED PLUG -- the plug is the point of the station, so it is drawn."""
    import cadquery as cq
    from cadkit.fasteners import M4_BUTTON_HEAD_H, m4_button_screw, seated_insert
    from cadkit.pcb import pcb_hold_xy
    cx, cy, _ = trrs_station()
    bz, mz = trrs_board_z(), trrs_mouth_z()
    board = _trrs_board_as_asked().translate((cx, cy, bz))
    hx, hy = pcb_hold_xy(TRRS_ACROSS, TRRS_ALONG, "-y", clr=TRRS_CLR, spec=_M4)
    wx, wy = cx + hx, cy + hy
    plug = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        TRRS_PLUG_D / 2.0, TRRS_PLUG_RUN,
        cq.Vector(cx, cy, mz - TRRS_PLUG_RUN), cq.Vector(0, 0, 1)))
    return [("trrs_adapter_pcb", board),
            ("trrs_adapter_plug", plug),
            ("trrs_adapter_insert", seated_insert(_M4, (wx, wy, bz), (0, 0, -1))),
            ("trrs_adapter_screw", m4_button_screw(TRRS_SCREW_L).translate(
                (wx, wy, bz + _PCB_T + M4_BUTTON_HEAD_H)))]


def _trrs_board_as_asked():
    """Bronner's adapter WITH A BOARD-PERPENDICULAR JACK (the request above), in the
    world's axes: origin at the board's centre on its underside, the mouth looking
    -Z through the board. Every size is electronics'; only the jack's axis differs,
    and this function is what gets deleted when the respin lands."""
    from .helpers import box_at
    from cadkit.pcb import jst_xh_header
    b = box_at(TRRS_ACROSS, TRRS_ALONG, _PCB_T, x=0.0, y=0.0, z=_PCB_T / 2)
    b = b.union(box_at(TRRS_JACK_W, TRRS_JACK_W, TRRS_JACK_L, x=0.0, y=0.0,
                       z=_PCB_T + TRRS_JACK_L / 2))
    b = b.union(jst_xh_header(4, mated=False)
                .translate((0.0, TRRS_ALONG / 2 - 7.5, _PCB_T)))
    return b


def tee_cradles():
    """A drop-in pcb_cradle under each tee, on the -Y-rail corridor. The cradle base sits on the
    rib tops; the tee drops in from +Z and ONE M4 beside it retains it (tee_hold). The tee
    connectors are TOP-entry (cables up), so a relief WINDOW is cut in the base under them for
    the THT post tails (3.4 below the board vs the 3.2 standoff). The M4 anchor is 8.5 deep
    against the M2's 5.5, so an M4-held cradle's base reaches 5.3 below the rib tops, not 2.3
    -- which is why build.py re-bores it after the fuse (tee_hold_negatives)."""
    from cadkit.pcb import pcb_cradle
    from .helpers import box_at
    rw, rl = EL.TEE_RELIEF
    out = []
    for i, (x, y, d) in enumerate(tee_stations()):
        if on_motor(i):
            continue          # ITS SEAT IS THE BAY: motor_bank cuts the board's profile out of
                              # the same prism it cuts the motor from, so there is no part here
        bw, bl, cx, cy, open_edge, hold_edge, hold_at = tee_hold(i, x, y, d)
        # ON A MOTOR the cradle stands on the pocket's faceplate wall, so its base is only
        # MOTOR_SEAT_SO under the board; on the rail it stands on the rib tops as before.
        so = MOTOR_SEAT_SO if on_motor(i) else TEE_Z - _RIB_TOP
        base_z = tee_z(i) - so
        # (main's `hold_edge is None` arm went with the bus-B placeholders and their M2.
        #  Every surviving tee is held THROUGH its ear, so the M4 arm is the only one left
        #  that can fire -- the else is kept for a tee that ever wants an edge hold again.)
        if hold_edge == "through":
            cr = pcb_cradle(bw, bl, screw_xy=_EAR_XY, spec=_M4, open_edge=open_edge, standoff=so,
                            wall_over=TEE_WALL_OVER, clr=TEE_CLR)
        else:
            cr = pcb_cradle(bw, bl, open_edge=open_edge, hold_edge=hold_edge, hold_at=hold_at,
                            standoff=so, wall_over=TEE_WALL_OVER, clr=TEE_CLR)
        cr = cr.cut(box_at(rw, rl, 12.0, x=0.0, y=EL.TEE_CONN_CY, z=-5.5))   # THT-tail relief
        cr = cr.translate((cx, cy, base_z))
        # EACH CRADLE CARRIES ITS OWN STATION. It used to be zipped against tee_stations() by
        # position in build.py, which silently broke the moment this loop started SKIPPING the
        # ten bank tees: every surviving cradle got paired with another tee's x and fused into
        # the segment that x falls in -- all three into the keyhead segment, 350 mm from where
        # their geometry sits, floating free of it and burying rib -70.8's lever mortise.
        out.append((f"tee_cradle_{i}", cr, (x, y, d)))
    return out


def tee_hold_negatives():
    """[(station_x, [world-space cutters])] for every M4-held tee: the SAME anchor and head
    notch pcb_cradle bores, placed in the world. build.py cuts them AFTER fusing the cradles
    into the chassis segments, because that fuse fills them straight back in with the
    segment's own rib and rail material (a feature cut before a union does not survive it)."""
    import cadquery as cq
    from cadkit.fasteners import M4_BUTTON_HEAD_D, anchor_cutter
    from cadkit.pcb import pcb_hold_xy
    notch_h = _PCB_T + TEE_WALL_OVER + 1.0
    out = []
    for i, (x, y, d) in enumerate(tee_stations()):
        bw, bl, cx, cy, _open, hold_edge, hold_at = tee_hold(i, x, y, d)
        if hold_edge is None:
            continue
        hx, hy = _EAR_XY if hold_edge == "through" else pcb_hold_xy(
            bw, bl, hold_edge, hold_at=hold_at, clr=TEE_CLR)
        px, py, pz = cx + hx, cy + hy, tee_z(i)
        anchor = anchor_cutter(_M4, (px, py, pz), (0, 0, -1), _M4.anchor_min_wall)
        notch = cq.Workplane("XY").add(cq.Solid.makeCylinder(
            (M4_BUTTON_HEAD_D + 2 * TEE_CLR) / 2, notch_h, cq.Vector(px, py, pz)))
        out.append((x, [anchor, notch]))
    return out


def _on_bank(p):
    return p[2] > HDR_Z + 20.0          # a tee on a motor sits far above the rail lanes


def _seg(a, b, lane_z, d=WIRE_D, off=0.0):
    """One crimped trunk SEGMENT between two tee headers, each a 3D point (tee_point).

    Two tees ON THE BANK fly to each other at TOP_Z, over the motors. A segment with a RAIL
    tee at one end rises there and flies across at the same lane. Rail to rail is the old
    route: the rail corridor at lane_z, dodging m9. off shifts x AND y (the 24 V pair)."""
    if _on_bank(a) and _on_bank(b):
        # out of each mouth, along the -Y side of the boards at mouth height, into the next --
        # low enough to pass under the magnetic pickup's neck-most position at every X
        lane = min(a[1], b[1]) - 4.0
        # EACH HOP LEAVES ITS CONNECTOR LEANING TOWARD THE HOP IT IS GOING TO. Straight out of
        # the mouth, the stub of the hop ARRIVING at a tee and the stub of the hop LEAVING it
        # were the same line -- same x, same z, same direction out of the same point -- so two
        # Ø1.3 conductors ran COINCIDENT for 4.65 mm, ~6.0 mm3 of each inside the other. OCCT
        # cannot boolean coincident cylinders, which is what put wire_canh_8/9 and wire_canl_8/9
        # in the gate's "could not be checked" list for as long as it has had one: they were not
        # suspect, they were a modelling artefact. Leaning them apart is also the truer picture --
        # the trunk in and the trunk out are different contacts on the same 6-way, and two crimps
        # leaving a connector lie side by side, not through each other.
        _lean = 2.0 if b[0] >= a[0] else -2.0
        pts = [a, (a[0] + _lean, lane, a[2]), (b[0] - _lean, lane, b[2]), b]
    elif _on_bank(a) or _on_bank(b):
        t, r = (a, b) if _on_bank(a) else (b, a)          # t on the bank, r on the rail
        pts = [t, (t[0], t[1] - 4.0, t[2]), (r[0], t[1] - 4.0, t[2]), (r[0], r[1], t[2]),
               (r[0], r[1], r[2])]
        if not _on_bank(a):
            pts.reverse()
    else:
        pts = [a] + _rail_pts(a[0], b[0], lane_z) + [b]
    return _wire([(px + off, py + off, pz) for px, py, pz in pts], d)


def build_wires():
    """Returns [(name, workplane)] for every net."""
    out = []
    # THE AFE'S WIRES ARE GONE WITH THE AFE (2026-09-14). wire_pickup, wire_out,
    # wire_audio, wire_dac and wire_relayctrl all began or ended on that board;
    # the bypass relay and the magnetic buffer now live on the optical pickup
    # board, which is 10 mm from the jack and the audio connector they feed.
    # wire_pickup RETURNS when that board is designed -- the magnetic pickup
    # still has to reach it -- but as ~230 mm of shielded coax to the optical
    # board's own terminal, not 110 mm to a board at the wrong end of the run.
    # Keyhead routing (STANDING TRAY, user 2026-09-11): the boards stand against the keyhead
    # endplate and string 1's motor sits 1.6 mm off the Pi, so nothing inside that motor's
    # Y/Z band can be reached from +X. Every bay wire therefore uses ONE column, BAY_X, just
    # inside the motor's -X face: -Y of the motor it rises straight out of the rail corridor,
    # and across the motor's Y band it runs at BAYFLY, over the motor top. From the column
    # it turns -X onto its board. Board pins stay authored in the tray's FLAT frame and are
    # posed with EL.stand_pt, so they follow the tray. Wire-vs-wire crossings are fine
    # (insulated); only solids (motors/boards/chassis) are avoided.
    BAY_X = D.motor_pos(0)[0] - D.MOTOR_SQ / 2 + 1.0    # -585.0
    BAYFLY = -12.0                                      # over motor 0, under the deck
    assert BAYFLY - max(WIRE_OD.values()) / 2 > D.MOTOR_BELT_Z + D.MOTOR_SQ / 2 + 1.0, (
        "the bay fly lane has come down onto string 1's motor")
    # ⚠ THREE BAY WIRES WERE ONE. The Pi link, bus B and the board-to-Pi USB all crossed
    # string 1's motor along this one column at BAYFLY -- 234, 69 and 15.5 mm3 of each
    # inside another, on the committed model, never reported (the gate allow-lists wire
    # against wire). Bus B flies lower; the USB takes its own column (see _USB_COL).
    BAYFLY_CANB = BAYFLY - 3.0            # -15.0 (the USB takes its own column instead)
    SP = EL.stand_pt
    # (the AFE's long shielded runs and their _long() helper are gone with the
    #  board; the Teensy stack they climbed onto is gone with the motor controller)

    # ── the two CAN buses: TRUNK-AND-DROP over the rail tee PCBs ────────
    tees = tee_stations()
    hdrA = {i: tee_point(i, tees[i][0], tees[i][1])          # trunk connector (3D) per tee
            for i in range(len(tees))}
    dropA = {i: tee_point(i, tees[i][0], tees[i][1], "drop") for i in range(10)}
    west = sorted(range(10), key=lambda i: hdrA[i][0])       # bus A west→east
    _WEST0 = west[-1]                 # the trunk's landing: the EAST-most tee, nearest J7

    # bus A CAN head: motor_ctrl J1 -> bay corridor -> -Y rail -> westernmost motor tee;
    # then one crimped segment per hop east. Termination: the controller's JP1 + tee 0's
    # closed jumper -- one at each END of the trunk and nowhere else (ISO 11898).
    # Drawn as the CAN-H (yellow) + CAN-L (green) pair, offset +-CAN_OFF (user).
    _w0 = hdrA[west[0]]                                      # string 1's tee, on its motor
    # ⚠ MAIN'S PATH, THIS BRANCH'S ENDPOINT. Main is right about the SHAPE -- with the
    # tees up on the motors there is no rail ride left, so the run climbs the bay gap and
    # flies straight over the bank to the first tee. But it STARTS at a hardcoded point on
    # the teensy_ifc board, which this branch deleted. The merged motor controller is the
    # source now, and it says where its own bus-A connector is rather than being copied.
    _ia = SP(*EL.mctrl_pt("J1"))
    _canA_head = [_ia, (BAY_X - 5.0, _ia[1], _ia[2]), (BAY_X - 5.0, _ia[1], _w0[2]),
                  (_w0[0], _ia[1], _w0[2]), _w0]
    for _sfx, _co in (("h", -CAN_OFF), ("l", CAN_OFF)):
        _od = WIRE_OD[f"wire_can{_sfx}"]
        out.append((f"wire_can{_sfx}_0", _wire(
            [(px + _co, py + _co, pz) for px, py, pz in _canA_head], _od)))
        for k in range(9):
            out.append((f"wire_can{_sfx}_{k + 1}",
                        _seg(hdrA[west[k]], hdrA[west[k + 1]], LANE_CAN, _od,
                             off=TRUNK_OFF["can" + _sfx])))

    # bus A drops: each motor's factory 4-pin XH pigtail (grey), from its -Y-facing PCB to its
    # OWN tee. For the nine tees on motors that is a short climb up behind the motor and over
    # its top; string 10's tee is still on the rail, so that one keeps the old reach along the
    # corridor. The climb stands off the back bumper where there is one.
    for i in range(10):
        mx, sy, mz = D.motor_pos(i)
        back = _motor_back(i)
        if on_motor(i):
            dx, dy, dz = dropA[i]
            room = back - RAIL_INNER_Y                 # from the motor's back face to the rail
            if room < WIRE_OD["motor_pigtail"] + 2.0:
                # STRING 10's back is 2.0 off the rail -- no room to climb there. Its cable lies
                # in the rail NOTCH (which exists for exactly this), runs east until it is past
                # the motor, and only then climbs to the tee's mouth height and comes back over
                # the motor's top. Under the magnetic pickup the whole way.
                _ex = mx + D.MOTOR_SQ / 2 + 4.0
                _ly = dy - (MB.STAGGER + 4.0)      # clear of this motor's own +X post band
                out.append((f"motor_pigtail_{i}", _wire([
                    (mx, back, mz), (mx, back - 1.5, mz), (_ex, back - 1.5, mz),
                    (_ex, _ly, mz), (_ex, _ly, dz), (dx, _ly, dz), (dx, dy, dz)],
                    WIRE_OD["motor_pigtail"])))
                continue
            stand = MB.BACK_T + MB.MOTOR_CLR + 2.0     # clear of the bay's back wall
            out.append((f"motor_pigtail_{i}", _wire([
                (mx, back, mz), (mx, back - stand, mz), (mx, back - stand, dz),
                (dx, back - stand, dz), (dx, dy, dz)],
                WIRE_OD["motor_pigtail"])))
            continue
        tx = tees[i][0]
        cy = min(TEE_Y, back - 3.0)
        out.append((f"motor_pigtail_{i}", _wire([
            (mx, back, mz), (mx, back, -52.0), (mx, cy, -52.0),
            (tx, cy, -52.0), (tx, TEE_Y + 4.5, -52.0), (tx, TEE_Y + 4.5, HDR_Z)],
            WIRE_OD["motor_pigtail"])))

    # 24 V pair (2 × 22 AWG per rail): panel J7 -> tee 9 ... tee 0 -> motor controller.
    # hot/gnd offset ±PWR_OFF.
    # ⚠ IT USED TO LAND ON TEE 10 AND TEE 10 IS GONE. The run now goes straight from the
    # panel to the westmost motor tee. Nothing had to be re-sized for it: these cables are
    # crimped from spooled wire (user), so the head is simply made to whatever length the
    # new landing needs, and cable length was never the reason the junction existed.
    x10, y10 = hdrA[_WEST0][0], hdrA[_WEST0][1]
    # ── THE OUTPUT BOARD'S 24 V HARNESS: TO THE WALL, ONE LOOP, THEN DOWN THE INSTRUMENT ──
    # (user, 2026-09-21: "route the wires to the chassis wall fairly directly and then coil
    # them in a single large circle before sending them down the instrument. The snake
    # pattern you have designed seems hard to achieve.") It was also drawn THROUGH the
    # output board: the serpentine sat at a fixed spot and nothing re-checked it when the
    # board moved, so it ran through the PCB and out below it.
    #
    # Both pairs leave their top-entry headers UP, cross the endplate's recess along the
    # board's -Y edge -- over the J7/J9 plug tops (-35.3), under the recess roof (-23.2) --
    # and come out into the bay, where they turn for the wall.
    _j7, _j10 = EL.op_top("J7"), EL.op_top("J10")
    _REC_Y = -121.5                       # along the board's -Y edge, inside the recess
    _REC_Z7, _REC_Z10 = -27.0, -31.0      # each pair's centre height crossing it
    _BAY_X7, _BAY_X10 = -28.0, -31.0      # out of the endplate's -X face (-25.06)
    # THE LOOP: the J7 cable's 111 mm of balancing slack (see below) as ONE flat turn in the
    # bay above the output board. A full turn adds its whole circumference to the conductor
    # -- none of it is "the direct line" -- so its radius is 111 / 2 pi. It climbs 4 mm over
    # the turn so it can close without passing through itself, and its -Y point sits on the
    # wall line, where the cable arrives and leaves.
    _LOOP_R = 111.0 / (2.0 * math.pi)     # 17.67
    _LOOP_CX, _LOOP_CY = -52.5, CHAN_Y + _LOOP_R
    _LOOP_RISE = 4.0
    _RISE7 = _LOOP_CX - 4.5               # J7 climbs to its trough lane just past the loop
    _RISE10 = CH_WT_X1 + 2.5              # feed 2 climbs short of the trough's end -- at
                                          # +1.0 its hot conductor's offset put it in the
                                          # trough's end face
    _EXIT7 = CH_WT_RUNS[-1][0] - 2.0      # J7 leaves the trough where it stops, before
                                          # string 10's motor, and goes to that motor's tee

    def _loop(z0):
        """One clockwise turn (seen from +Z) from the loop's -Y point, climbing _LOOP_RISE."""
        return [(_LOOP_CX + _LOOP_R * math.cos(-math.pi / 2 - 2 * math.pi * k / 24),
                 _LOOP_CY + _LOOP_R * math.sin(-math.pi / 2 - 2 * math.pi * k / 24),
                 z0 + _LOOP_RISE * k / 24) for k in range(25)]

    # THE PAIR IS SPACED IN X *AND* Z, header to far end. Z alone keeps the two loops apart
    # (same radius, 2 mm apart in height, all the way round -- side by side they would
    # cross twice), but it does nothing where the path is VERTICAL: both conductors left
    # the same header point and rose through each other, 67 mm3 on J7's pair and 154 on
    # feed 2's -- invisible to the gate, which allow-lists wire against wire as insulated
    # crossings. X is the pin spacing on the connector; Z is the stack in the trough.
    def _pair(pts, dz):
        return [(x + dz, y, z) for x, y, z in pts]

    def _head(dz):
        """J7 -> the east-most tee's trunk connector (on string 10's motor)."""
        zr, zl = _REC_Z7 + dz, LANE_PWR + dz
        loop = _loop(zr)
        return _pair([_j7, (_j7[0], _j7[1], zr), (_j7[0], _REC_Y, zr), (_BAY_X7, _REC_Y, zr),
                      (_BAY_X7, CHAN_Y, zr)] + loop
                     + [(_RISE7, CHAN_Y, loop[-1][2]), (_RISE7, CHAN_Y, zl),
                        (_EXIT7, CHAN_Y, zl), (_EXIT7, y10, zl), (x10, y10, zl),
                        hdrA[_WEST0]], dz)

    # THE TRUNK ENDS AT THE MERGED BOARD, and main's path off _w0 is the right shape
    # for it. Main ran it to a free-standing BUCK; this branch merged the power board
    # into the motor controller, so there is no buck and no junction -- the chain simply
    # terminates at a connector on a board.
    # ⚠ POSED. The boards stand on end against the keyhead endplate (stand_pt); every other
    # lead to this board was posed and these two -- the tee chain's tail and feed 2 -- were
    # not, so both ended in mid-air where J3 would be if the board still lay flat (user:
    # "unterminated ground and 24V wires near the motor control board").
    _mc24 = SP(*EL.mctrl_pt("J3"))
    tail = [_w0, (BAY_X, _w0[1], _w0[2]), (BAY_X, _mc24[1], _w0[2]),
            (BAY_X, _mc24[1], _mc24[2]), _mc24]

    # ── the SECOND 24 V feed: panel J10 -> motor_ctrl J3, bypassing the tees ──
    # ITS OWN COLUMN at the keyhead, 3 mm +X of the bay column the bay wires climb: run
    # along the column it crossed bus B's and the Pi link's risers there. At this y there
    # is no motor at x -582 (string 1's sits far +Y), so the column is free.
    _FEED2_X = BAY_X + 3.0
    # AND IT LANDS TWO PIN PITCHES FROM THE TAIL on motor_ctrl J3, not on the tail's own
    # point: two cables drawn into one point is two cables through each other.
    _J3_PITCH2 = 2 * 2.5

    def _feed2(dz):
        zr, zl = _REC_Z10 + dz, LANE_PWR2 + dz
        return _pair([_j10, (_j10[0], _j10[1], zr), (_j10[0], _REC_Y, zr),
                      (_BAY_X10, _REC_Y, zr), (_BAY_X10, CHAN_Y, zr), (_RISE10, CHAN_Y, zr),
                      (_RISE10, CHAN_Y, zl)]
                     + _rail_pts(_RISE10, _FEED2_X, zl)
                     + [(_FEED2_X, _mc24[1] + _J3_PITCH2, zl),
                        (_FEED2_X, _mc24[1] + _J3_PITCH2, _mc24[2] + dz),
                        (_mc24[0], _mc24[1] + _J3_PITCH2, _mc24[2] + dz)], dz)

    for _nm, _do in (("wire_pwr_hot", -PWR_OFF), ("wire_pwr_gnd", PWR_OFF)):
        def _off(pts, _do=_do):
            return [(px + _do, py, pz) for px, py, pz in pts]
        out.append((f"{_nm}_0", _wire(_head(_do), WIRE_OD[_nm])))
        for k in range(9):
            out.append((f"{_nm}_{k + 2}",
                        _seg(hdrA[west[k + 1]], hdrA[west[k]], LANE_PWR, WIRE_OD[_nm],
                             off=TRUNK_OFF[_nm[9:]])))
        # _1 is vacant: it was the hop from tee 10 onto the rail, and tee 10 is gone.
        # the tail pair spaced like the others -- an X offset alone left its X-running leg
        # with both conductors on one line (98.5 mm3, on the committed model)
        out.append((f"{_nm}_11", _wire([(x + _do, y, z + _do) for x, y, z in tail],
                                       WIRE_OD[_nm])))

        # ⚠ THE SECOND FEED (option A, user 2026-09-18). The tee chain is fed from BOTH
        # ends now: J7 at the east, and this cable running the length of the instrument
        # to motor_ctrl's J3 at the west, from which J1 injects onto the chain. Current
        # enters at both ends and meets in the middle, so the worst-loaded segment
        # carries about half the fleet instead of all of it. It does NOT go through the
        # tees: it is a 4-way carrying ONLY power, so both +24V ways parallel and its
        # 582 mm behaves like 291.
        out.append((f"{_nm}_12", _wire(_feed2(_do), WIRE_OD[_nm])))

        # ⚠ AND THE LOOP ON _0 IS DELIBERATE RESISTANCE. The two feeds are wildly
        # asymmetric -- J7 reaches the chain far sooner than feed 2 -- so uncorrected the
        # east feed takes 5.6 of the 10 motors and the west 4.4. 111 mm of slack on the J7
        # cable brings it to 5.00/5.00, for 0.0059 ohm -- 0.07 % of 24 V at 3 A. Kept as a
        # PAIR through the turn: motor current is switched, and a pair that stays together
        # is bifilar, so its fields cancel instead of ringing against the drivers' input
        # capacitance.


    # ── bus B (inputs): motor_ctrl J2 -> the lever boards, NO TEES ────────
    # It used to hop ifc -> tee 11 -> tee 12. Both tees are deleted (user), because both
    # ends can now terminate themselves: the lever board passes the trunk THROUGH its own
    # 8-way (in 1-4, out 5-8) so it needs no tap beside it, and the TRRS adapter carries
    # the leg jack ON the board so it needs no landing. What is left is one run from the
    # controller to the first board on the chain.
    _ib = SP(*EL.mctrl_pt("J2"))
    _canB_head = ([_ib, (BAY_X - 5.0, _ib[1], _ib[2]), (BAY_X - 5.0, _ib[1], BAYFLY_CANB),
                   (BAY_X, _ib[1], BAYFLY_CANB), (BAY_X, RAIL_Y, BAYFLY_CANB)]
                  + _floor_pts(BAY_X, _KNEE_B[0], LANE_CTRL)
                  + [(_KNEE_B[0], RAIL_Y, LANE_CTRL), _KNEE_B])
    for _sfx, _co in (("h", -CAN_OFF), ("l", CAN_OFF)):
        _od = WIRE_OD[f"wire_canb{_sfx}"]
        out.append((f"wire_canb{_sfx}_0", _wire(
            [(px + _co, py + _co, pz) for px, py, pz in _canB_head], _od)))
    # (wire_knee_drop is gone with tee 11: the stub existed to get from that tee to the
    #  lever board, and bus B now arrives at the board directly. The last few mm onto the
    #  kl_pcb XH is still the chassis follow-up it always was.)

    # -- USB (blue): USB-C panel -> -Y rail corridor -> ride to the bay -> right-angle to Pi
    # It leaves the OUTPUT PANEL BOARD's own USB-A now, not a panel coupler: the
    # panel USB-C is a part ON that board and its VBUS stops there, so what crosses
    # the instrument is the board-to-Pi lead. Starting it at the old panel-jack
    # position ran it straight through the relocated DC inlet.
    # The lane drops -X of the OUTPUT PANEL BOARD's own -X edge rather than at x -12,
    # which is where it used to go. -12 sat inside the relocated DC inlet (x -13.3..4.7)
    # AND inside the board's footprint; clearing the board is what also clears the jack.
    # It leaves J2 out of the board's -X edge through a USB-A plug standing _UA_PLUG past
    # the mouth, climbs to the trough's USB lane out in the bay -X of the J7 loop, and rides
    # the trough to the keyhead bay. (It used to run a floor corridor inside the pocket cut
    # into the rail; the trough replaced both.)
    _usb = SP(-575.0, 20.0, -44.0)
    _ua = EL.op_pt("J2")
    _UA_PLUG = 25.0
    # ITS OWN COLUMN at the keyhead, 6 mm +X of the one the bay wires share: at a different
    # fly height in the shared column it met the OLED lead's drop instead (24.9 mm3). Here it
    # flies over string 1's motor, well above its top.
    _USB_COL = BAY_X + 6.0
    _USB_FLY = BAYFLY - 3.0               # under the Pi link's fly, which it crossed at the Pi
    _ua_x = EL.op_origin()[0] - EL.OP_BOARD_X / 2 - _UA_PLUG     # the plug's cable end
    _USB_X = _LOOP_CX - _LOOP_R - 9.5     # -X of the loop, +X of the trough's end
    out.append(("wire_usb", _wire(
        [(_ua_x, _ua[1], _ua[2]), (_USB_X, _ua[1], _ua[2]), (_USB_X, _ua[1], LANE_USB),
         (_USB_X, CHAN_Y, LANE_USB)]
        + _rail_pts(_USB_X, _USB_COL, LANE_USB)
        + [(_USB_COL, CHAN_Y, _USB_FLY), (_USB_COL, _usb[1], _USB_FLY),
           (_usb[0], _usb[1], _USB_FLY), _usb],
        WIRE_OD["wire_usb"])))                          # over motor 0, then down into the Pi

    # -- 5 V to the Pi's GPIO header, from the merged board's J5. It was never
    #    modelled while the power board existed -- that board fed the Pi and nothing
    #    drew the cable -- so the harness has been a connector short all along.
    # It rides ABOVE the board tops between the two connectors and only drops at the
    # Pi. Run level with the header it started from, it grazed the tray plate.
    _j5 = SP(*EL.mctrl_pt("J5"))
    _gpio = SP(-596.0, -38.0, -57.0)
    _over = SP(-596.0, -50.0, -46.4)
    out.append(("wire_5v", _wire([
        _j5, (_j5[0], _over[1], _j5[2]), (_over[0], _over[1], _over[2]),
        (_gpio[0], _gpio[1], _over[2]), _gpio], WIRE_OD["wire_5v"])))

    # -- motor controller <-> Pi (purple): the USB-C lead the Pi writes travel
    #    offsets over. It leaves the board's mouth sideways, not off a header.
    _lt, _lp = SP(*EL.mctrl_pt("J4")), SP(-585.0, 20.0, -58.0)
    # It crosses motor 0's Y band, so it takes the BAYFLY lane over the motor top
    # like every other bay wire -- running it across at the board's own height put
    # 62 mm3 of cable inside string 1's motor.
    out.append(("wire_link", _wire([
        _lt, (BAY_X, _lt[1], _lt[2]), (BAY_X, _lt[1], BAYFLY), (BAY_X, _lp[1], BAYFLY),
        (_lp[0] + 5.0, _lp[1], BAYFLY), (_lp[0] + 5.0, _lp[1], _lp[2]), _lp],
        WIRE_OD["wire_link"])))

    # (the Teensy <-> transceiver CAN jumper pair is GONE: the transceivers now sit
    #  on the same board as the MCU, so that harness is copper instead of wire.)

    # (wire_tdm is GONE with adc_stack: the ten-channel ADC carrier it fed is
    #  deleted, the optical pickup board having absorbed that conversion.)

    # -- UI: OLED + joystick (-Y deck band) -> the PI's GPIO header (user: the OLED
    #    and the joystick live on the Pi). Drop under the deck, run to the keyhead,
    #    down the bay column onto the Pi.
    UDZ = -2.0
    out.append(("wire_oled", _wire([
        (EL.UI_X, EL.OLED_Y, EL.DECK_TOP + 1.0), (EL.UI_X, EL.OLED_Y, UDZ),
        (BAY_X, EL.OLED_Y, UDZ), (BAY_X, -40.0, SP(-600.0, -40.0, -57.0)[2]),
        SP(-600.0, -40.0, -57.0)], WIRE_OD["wire_oled"])))
    out.append(("wire_joy", _wire([
        (EL.JOY_X, EL.JOY_Y, EL.DECK_TOP + 1.0), (EL.JOY_X, EL.JOY_Y, UDZ),
        (BAY_X + 4, EL.JOY_Y, UDZ), (BAY_X + 4, -30.0, SP(-595.0, -30.0, -57.0)[2]),
        SP(-595.0, -30.0, -57.0)], WIRE_OD["wire_joy"])))

    return out


# what each net is ALLOWED to touch (its source/destination bodies);
# everything else a wire grazes is a routing bug the gate reports
WIRE_OK = {
    "wire_canh":      {"motor_ctrl", "tee_pcb"},
    "wire_canl":      {"motor_ctrl", "tee_pcb"},
    "wire_canbh":     {"motor_ctrl", "tee_pcb"},
    "wire_canbl":     {"motor_ctrl", "tee_pcb"},
    "motor_pigtail":  {"tee_pcb", "motor"},
    # leg↔body TRRS: the chassis jack's factory cable (tenon channel ->
    # bus-B socket tee) and the column CA-354S inside the leg stack
    # (it used to land on tee 12; that tee is deleted and the TRRS ADAPTER BOARD
    #  carries the jack instead -- the adapter has no station in the CAD yet)
    "chassis_trrs_cable": {"leg_body_stub", "chassis_trrs_jack",
                           "jack_seat_ring"},
    "leg_column_cable": {"leg_body_stub", "leg_segment", "leg_sleeve",
                         "leg_shaft", "leg_column_plug",
                         "leg_plug_retainer", "leg_cable_coil",
                         "leg_head", "leg_junction_pcb",
                         "leg_seg_body", "leg_lid",
                         # the shaft-side model of the SAME physical
                         # CA-354S — they abut inside the shaft channel
                         "pedal_trrs_cable_leg"},
    "leg_cable_coil":   {"leg_segment", "leg_seg_body", "leg_sleeve",
                         "leg_column_cable", "shaft_trrs_cable"},
    "shaft_trrs_cable": {"leg_shaft", "leg_sleeve", "leg_seg_body",
                         "shaft_trrs_jack", "leg_cable_coil",
                         "leg_junction_pcb", "leg_head"},
    "wire_pwr_hot":   {"output_panel", "tee_pcb", "motor_ctrl"},
    "wire_pwr_gnd":   {"output_panel", "tee_pcb", "motor_ctrl"},
    "wire_5v":        {"motor_ctrl", "pi5"},
    "wire_usb":       {"output_panel", "pi5"},
    "wire_link":      {"motor_ctrl", "pi5"},
    "wire_oled":      {"oled", "pi5"},
    "wire_joy":       {"joystick", "pi5"},
}


# THE BAYS' BACK WALLS reach to MB.HARNESS_Y1 now, so a tee still ON THE RAIL must not fall
# inside a bay's footprint -- a housing would be built straight on top of it. Tested against the
# real bay box (both axes: tee 11 sits inside the bank in X but well +Y of any back wall).
for _i, (_tx, _ty, _td) in enumerate(tee_stations()):
    if on_motor(_i):
        continue
    _bw, _bl, _bcx, _bcy, _o, _he, _ha = tee_hold(_i, _tx, _ty, _td)
    for _m in range(D.N_STRINGS):
        _mx0, _mx1, _my0, _my1, _mz0, _mz1 = MB.body_box(_m)
        _bay = (_mx0 - MB.side_room(_m, -1), _mx1 + MB.side_room(_m, 1),
                _my0 - MB.BACK_T, _my1 + MB.PLATE_T)
        assert not (_bcx - _bw / 2 < _bay[1] and _bcx + _bw / 2 > _bay[0]
                    and _bcy - _bl / 2 < _bay[3] and _bcy + _bl / 2 > _bay[2]), (
            "tee %d lands inside string %d's bay (x %.1f..%.1f, y %.1f..%.1f)"
            % (_i, _m + 1, _bay[0], _bay[1], _bay[2], _bay[3]))
