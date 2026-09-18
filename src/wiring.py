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

import cadquery as cq

from . import dimensions as D
from . import electronics as EL

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
PWR_OFF = 1.2         # 24 V hot/gnd separation, applied in BOTH x and y (+off /
                      # -off): a single-axis offset leaves the pair COLLINEAR on
                      # runs along that axis (the y-offset pair coincided on the
                      # y-running motor stubs). x-runs separate by the y part,
                      # y-runs by the x part, verticals by both. Lane edges at
                      # 1.2 + 0.9 = 2.1 < RACE_HW 2.4.
WIRE_D = 2.0          # default (shielded-pair size)

# ── -Y RAIL harness corridor ──────────────────────────────────────────────
# The ribs are STRUCTURE + lever mounts ONLY: a knee/pedal lever slides along its rib
# mortise to ANY depth in ANY bay, so a cable sitting in a rib would block a lever from
# being installed there. So NO wire crosses a rib. The whole X-running trunk instead
# hugs the -Y rail's INNER FACE, ABOVE the rib tops (z > FLOOR_TOP -65.15) where no rib
# reaches and -- except the +X-most motor (m9) -- no motor body reaches either. The tees
# mount on the rail (each on a pcb_cradle); every motor's drop pigtail reaches from its
# -Y-facing PCB out to its tee. Past m9 the rail is notched (chassis motor-9 cable cut).
from .chassis import Y_LO as _Y_LO, T as _RAIL_T
from .chassis import SPLIT_X as CH_SPLIT_X
from . import motor_bank as MB                          # back_y: where each motor's pigtail leaves
from .motor_bank import FLOOR_TOP as _RIB_TOP           # -65.15 (rib tops = above = rib-free)
RAIL_INNER_Y = _Y_LO + _RAIL_T / 2                       # -128.75: -Y rail inner face
RAIL_Y = RAIL_INNER_Y + 4.5                              # trunk corridor centre, hugging the rail
TEE_Y  = RAIL_INNER_Y + 8.0                              # tee-board centre (14mm-deep board clears wall)
# six trunk lanes, STACKED in Z (was spread in Y), all ABOVE the tee headers (-54) so the
# long-haul nets (audio/dac/relayctrl/usb, which do NOT land on a tee) clear every tee; the
# CAN/pwr/canb nets dip DOWN to the tee headers to land (whitelisted tee contacts). 2mm pitch.
LANE_AUDIO = -52.0       # buffered pickup -> ADC
LANE_CAN   = -50.0       # CAN bus A (motors)
LANE_PWR   = -48.0       # 24 V
LANE_USB   = -46.0       # USB-C -> Pi
LANE_DAC   = -44.0       # DAC -> AFE
LANE_CTRL  = -42.0       # relay control / CAN bus B
# NOTE: LANE_* are now Z heights along the RAIL_Y corridor (not lane y's).
TEE_Z = _RIB_TOP + 4 * D.BEAD                            # 3.2 of printed cradle on the rib tops
# the motor pockets stop short of this corridor (motor_bank.HARNESS_Y1) -- keep the two in step,
# or a pocket lands on a tee board or in a trunk lane (it did, once)
# the TRUNK wires set the corridor top -- the motor pigtails are fat (3.4) but ride down at
# -52 with the tee headers, not up in the lanes
_TRUNK_OD = max(od for nm, od in WIRE_OD.items() if nm != 'motor_pigtail')
_CORR_Y1 = RAIL_Y + _TRUNK_OD / 2
_CORR_Z1 = max(LANE_AUDIO, LANE_CAN, LANE_PWR, LANE_USB, LANE_DAC, LANE_CTRL) + _TRUNK_OD / 2
assert _CORR_Y1 <= MB.HARNESS_Y1 and _CORR_Z1 <= MB.HARNESS_Z1, (
    "the harness corridor now reaches y %.2f / z %.2f, past motor_bank's HARNESS_Y1 %.2f / "
    "HARNESS_Z1 %.2f -- the motor pockets stop at those" % (_CORR_Y1, _CORR_Z1,
                                                            MB.HARNESS_Y1, MB.HARNESS_Z1))
HDR_Z = -54.0                                            # lifted tee header top (wire entry z)


def _wire(pts, d=WIRE_D):
    """Polyline cable: cylinders between points + sphere elbows."""
    r = d / 2
    out = cq.Workplane("XY")
    for a, b in zip(pts, pts[1:]):
        va, vb = cq.Vector(*a), cq.Vector(*b)
        ax = vb - va
        if ax.Length < 1e-6:
            continue
        out = out.union(cq.Workplane("XY").add(
            cq.Solid.makeCylinder(r, ax.Length, va, ax)))
    for p in pts[1:-1]:
        out = out.union(cq.Workplane("XY").add(
            cq.Solid.makeSphere(r, cq.Vector(*p), angleDegrees1=-90)))
    return out


# motor 9 (the +X-most motor) is the ONE whose body reaches the -Y rail, so the rail
# corridor at RAIL_Y is blocked by it; the trunk dips OUTBOARD into the rail there (the
# chassis motor-9 cable cut notches the rail + drops its diamonds). Every other motor
# leaves the corridor open.
_M9X = D.motor_pos(9)[0]
M9_X0, M9_X1 = _M9X - D.MOTOR_SQ / 2 - 2.0, _M9X + D.MOTOR_SQ / 2 + 2.0
CUTOUT_Y = RAIL_INNER_Y - 1.25           # trunk dip: just past m9's back into the notched rail,
                                         # shallow enough that even the Ø2.6 USB stays inside the cut


# a chassis split inside the notch would fill the dip back in with its joint
assert not any(M9_X0 - 4.0 < _s < M9_X1 + 4.0 for _s in CH_SPLIT_X), (
    "a chassis split plane (%s) lands in motor 9's rail notch %.1f..%.1f, where the trunk dips "
    "outboard -- its tenon will fill the dip" % ([round(_s, 2) for _s in CH_SPLIT_X],
                                                 M9_X0, M9_X1))


def _rail_pts(x0, x1, z):
    """Points riding the -Y rail corridor (RAIL_Y) from x0 to x1 at height z, dipping
    OUTBOARD to CUTOUT_Y across motor 9's X-span (its body reaches RAIL_Y; the rail is
    notched there so the trunk passes outboard of it)."""
    pts = [(x0, RAIL_Y, z)]
    if min(x0, x1) < M9_X1 and max(x0, x1) > M9_X0:      # ride spans m9 -> dip around it
        a, b = (M9_X1, M9_X0) if x0 > x1 else (M9_X0, M9_X1)
        pts += [(a, RAIL_Y, z), (a, CUTOUT_Y, z), (b, CUTOUT_Y, z), (b, RAIL_Y, z)]
    pts.append((x1, RAIL_Y, z))
    return pts


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
        pts = [a, (a[0], lane, a[2]), (b[0], lane, b[2]), b]
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
                        _seg(hdrA[west[k]], hdrA[west[k + 1]], LANE_CAN, _od, off=_co)))

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
    # the power heads drop just inboard of the bridge endplate's wall, and that wall
    # follows BRIDGE_AXLE_X -- so this lane does too. It was a constant -5.5, and when
    # the bearing grew O8 -> O13 the axle (and the wall) stepped 2.5 -X and clipped the
    # ground wire.
    _PWR_X = D.BRIDGE_AXLE_X - 1.5                              # -8.0
    # The trunk now leaves the OUTPUT+PANEL BOARD's own trunk connector, not a
    # free-standing panel jack: the 24 V inlet is a PCB part on that board and the
    # pair crosses it on an isolated island before it ever becomes a cable.
    # (It is J7 since the 2026-09-15 respin -- the board gained a screw-terminal
    #  pickup input, so the connectors renumbered along the signal path.)
    _j6 = EL.op_pt("J7")
    heads = [_j6, (_PWR_X, _j6[1], _j6[2]), (_PWR_X, TEE_Y, -52.0),
             (x10, TEE_Y, -52.0), (x10, TEE_Y, HDR_Z)]
    # THE TRUNK ENDS AT THE MERGED BOARD, and main's path off _w0 is the right shape
    # for it. Main ran it to a free-standing BUCK; this branch merged the power board
    # into the motor controller, so there is no buck and no junction -- the chain simply
    # terminates at a connector on a board. That removed the ONE splice in an instrument
    # where every other branch is a tee or a pass-through.
    _mc24 = EL.mctrl_pt("J3")
    tail = [_w0, (BAY_X, _w0[1], _w0[2]), (BAY_X, _mc24[1], _w0[2]),
            (BAY_X, _mc24[1], _mc24[2]), _mc24]
    # (main's afe_drop is dropped with the AFE board itself. Tee 10 survives -- the
    #  optical pickup board takes 24 V off it -- but its drop has no modelled endpoint
    #  until that board exists.)
    #
    # ⚠ THAT BOARD NOW EXISTS, AND IT IS NOT FED FROM HERE. elec/optical.py is a finished
    # design with exactly two connectors: J1, a USB-C to the panel, and J2, a 4-pin XH
    # carrying 24 V. It has NO CAN -- the board speaks USB to the Pi -- so a CAN-rail tee
    # is the wrong shape of source for it: a tee exists to split the four-wire
    # CAN-plus-power cable for a device ON the bus, and this device is not on it.
    #
    # Its 24 V comes from the output panel instead: elec/output_panel.py's J9 is
    # documented as "24 V out to the optical pickup board", and the two boards are about
    # 150 mm apart -- which is the whole reason the USB hub moved onto the panel, taking
    # that 480 Mbps link from ~800 mm to ~100 mm (BOM.md, the hub row). A panel outlet is
    # a short cable; a rail drop would be a long one to a board with no bus to join.
    #
    # ⚠ SO TEE 10 LOOKS STALE, AND IT IS THE ONLY TEE LEFT ON THE RAIL (see tee_outline
    # above), which makes this more than one part: the rail-mounted tee, its cradle, its
    # M4 side hold-down and the drop's two wires all exist to feed a board that is fed
    # from somewhere else. Flagged rather than deleted -- removing it changes the rail
    # geometry and the rib spacing around it, which is not this file's call alone.
    # What would settle it: confirm that nothing else on the rail needs a 24 V drop.
    for _nm, _do in (("wire_pwr_hot", -PWR_OFF), ("wire_pwr_gnd", PWR_OFF)):
        def _off(pts):
            return [(px + _do, py + _do, pz) for px, py, pz in pts]
        out.append((f"{_nm}_0", _wire(_off(heads), WIRE_OD[_nm])))
        for k in range(9):
            out.append((f"{_nm}_{k + 2}",
                        _seg(hdrA[west[k + 1]], hdrA[west[k]], LANE_PWR, WIRE_OD[_nm], off=_do)))
        # _1 is vacant: it was the hop from tee 10 onto the rail, and tee 10 is gone.
        # The tail keeps its own index rather than shifting up into the loop's _2.._10.
        out.append((f"{_nm}_11", _wire(_off(tail), WIRE_OD[_nm])))


    # ── bus B (inputs): motor_ctrl J2 -> the lever boards, NO TEES ────────
    # It used to hop ifc -> tee 11 -> tee 12. Both tees are deleted (user), because both
    # ends can now terminate themselves: the lever board passes the trunk THROUGH its own
    # 8-way (in 1-4, out 5-8) so it needs no tap beside it, and the TRRS adapter carries
    # the leg jack ON the board so it needs no landing. What is left is one run from the
    # controller to the first board on the chain.
    _ib = SP(*EL.mctrl_pt("J2"))
    _canB_head = ([_ib, (BAY_X - 5.0, _ib[1], _ib[2]), (BAY_X - 5.0, _ib[1], BAYFLY),
                   (BAY_X, _ib[1], BAYFLY), (BAY_X, RAIL_Y, BAYFLY)]
                  + _rail_pts(BAY_X, _KNEE_B[0], LANE_CTRL)
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
    _USB_LANE_X = -60.0
    _usb = SP(-575.0, 20.0, -44.0)
    _ua = EL.op_pt("J2")
    out.append(("wire_usb", _wire(
        [_ua, (_ua[0], _ua[1] + 6.0, _ua[2]), (_USB_LANE_X, _ua[1] + 6.0, -45.0),
         (_USB_LANE_X, RAIL_Y, -45.0)]
        + _rail_pts(_USB_LANE_X, BAY_X, LANE_USB)
        + [(BAY_X, RAIL_Y, BAYFLY), (BAY_X, _usb[1], BAYFLY), (_usb[0], _usb[1], BAYFLY), _usb],
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
