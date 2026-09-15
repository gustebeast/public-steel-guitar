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
    return D.motor_pos(i)[1] - 84.0          # -Y-most face of motor i (PCB back)


def tee_stations():
    """[(x, y, drop_sign)] tee-PCB anchors, all on the -Y rail (TEE_Y) so the CAN trunk
    stays on the rail and never crosses a rib. 0..9 bus A (one per motor); 10 is the
    24 V drop the optical pickup board takes. THERE ARE NO BUS-B TEES -- 11 (knee) and
    12 (leg-socket) are deleted; see the module docstring. The two +X-most motors (8,9) reach the rail, so a tee
    dead-behind them would sit inside the motor -- their tees shift into the clear corridor
    (m8 -X toward m7, m9 +X past the motor bank) and reach back with a longer pigtail."""
    out = []
    for i in range(10):
        mx = D.motor_pos(i)[0]
        # m9's body sits AT the rail (its tee would be buried in it) -> park m9's tee just past the
        # motor bank in the clear corridor; every other motor's tee rides the rail at its own X (m8's
        # tee corner just grazes m8's PCB, a whitelisted mount contact).
        if i == 9:
            mx = _M9X + 30.0
        out.append((mx, TEE_Y, +1))
    out.append((-48.0, TEE_Y, -1))            # 10: the optical pickup board's 24 V drop
                                              # (rail; -X of the +X leg stub at -13.4)
    return out


_TEE_LIFT = TEE_Z - EL.FLOOR_Z          # lift the tee dummy onto its cradle, above the rib tops


# ── TEE RETENTION: ONE M4 BESIDE THE BOARD (user: one driver, one insert SKU) ──────
# It was one M2 down through a board hole. cadkit's pcb_cradle now takes the screw BESIDE
# the board (hold_edge): the walls capture every direction but +Z, and the button head laps
# the board edge to close +Z, so the board needs no hole at all. tee_hold() is the ONE
# table of per-tee choices, and it feeds the cradle, the dummy screw AND the post-fuse
# re-bore -- so the part that is bored and the screw the overlap gate checks cannot disagree.
TEE_SCREW_L   = 10.0        # M4x10 button: head on the board top, tip inside the anchor
TEE_CLR       = 0.3         # board fit gap in the cradle; also sets where the hold screw sits
TEE_WALL_OVER = 1.2         # cradle walls stand this far above the board top
from cadkit.fasteners import M4 as _M4
from cadkit.pcb import PCB_T as _PCB_T
assert TEE_SCREW_L - _PCB_T <= _M4.anchor_min_wall + 1e-9, (
    f"tee hold-down M4x{TEE_SCREW_L:g} reaches {TEE_SCREW_L - _PCB_T:.2f} below the board's "
    f"underside, past the {_M4.anchor_min_wall} anchor the cradle bores -- it would bottom out")


def tee_hold(i, x, y, d):
    """(board_w, board_l, centre_x, centre_y, open_edge, hold_edge, hold_at) for tee i.

    Every tee is now the SAME board on the SAME M4-beside-the-edge hold. The bus-B
    placeholders that kept an M2 through a board hole are deleted with tees 11/12, so
    THE LAST M2 IN THE TEE FAMILY IS GONE -- one screw diameter, one driver."""
    # bus-A (22 x 24): hold on the +X edge, toward the -Y rail end (hold_at -8).
    #   +Y (the obvious spot) lands under the -Y ends of motors 6-8: 115 mm3 of screw into
    #      motor_7 and motor_8 -- the board grows +Y into the corridor the motors reach into.
    #   -X clips the connectors (0.7-3.2 mm3): the rotated XH body reaches x -10.25.
    #   +X clears the mated connectors and the 120R at every hold_at tried (-9..0); -8 keeps
    #      the head 12 back from the motor ends and inside the board's own Y span, so it
    #      stays off the rail. All four walls close -- the connectors are top-entry now.
    return EL.TEE_BOARD_X, EL.TEE_BOARD_Y, x, EL.tee_board_cy(y), None, "+x", -8.0


def tee_components():
    """The tee-PCB dummies for the assembly, lifted onto their -Y-rail cradles (above the
    rib tops so no tee sits in a rib), each M4-held tee with its screw and insert placed
    from the same tee_hold() the cradle is bored from. See tee_cradles()."""
    from cadkit.fasteners import M4_BUTTON_HEAD_H, m4_button_screw, seated_insert
    from cadkit.pcb import pcb_hold_xy
    out = []
    for i, (x, y, d) in enumerate(tee_stations()):
        out.append((f"tee_pcb_{i}", EL.tee_pcb(x, y, d).translate((0, 0, _TEE_LIFT))))
        w, l, cx, cy, _open, hold_edge, hold_at = tee_hold(i, x, y, d)
        if hold_edge is None:
            continue
        hx, hy = pcb_hold_xy(w, l, hold_edge, hold_at=hold_at, clr=TEE_CLR)
        out.append((f"tee_insert_{i}", seated_insert(_M4, (cx + hx, cy + hy, TEE_Z), (0, 0, -1))))
        out.append((f"tee_screw_{i}", m4_button_screw(TEE_SCREW_L).translate(
            (cx + hx, cy + hy, TEE_Z + _PCB_T + M4_BUTTON_HEAD_H))))       # head seated on the board top
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
    so = TEE_Z - _RIB_TOP                                        # pads meet the lifted tee board bottom (TEE_Z)
    out = []
    for i, (x, y, d) in enumerate(tee_stations()):
        w, l, cx, cy, open_edge, hold_edge, hold_at = tee_hold(i, x, y, d)
        cr = pcb_cradle(w, l, open_edge=open_edge, hold_edge=hold_edge, hold_at=hold_at,
                        standoff=so, wall_over=TEE_WALL_OVER, clr=TEE_CLR)
        cr = cr.cut(box_at(rw, rl, 4.0, x=0.0, y=EL.TEE_CONN_CY, z=-1.5))   # THT-tail relief
        out.append((f"tee_cradle_{i}", cr.translate((cx, cy, _RIB_TOP))))
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
        w, l, cx, cy, _open, hold_edge, hold_at = tee_hold(i, x, y, d)
        if hold_edge is None:
            continue
        hx, hy = pcb_hold_xy(w, l, hold_edge, hold_at=hold_at, clr=TEE_CLR)
        px, py = cx + hx, cy + hy
        anchor = anchor_cutter(_M4, (px, py, TEE_Z), (0, 0, -1), _M4.anchor_min_wall)
        notch = cq.Workplane("XY").add(cq.Solid.makeCylinder(
            (M4_BUTTON_HEAD_D + 2 * TEE_CLR) / 2, notch_h, cq.Vector(px, py, TEE_Z)))
        out.append((x, [anchor, notch]))
    return out


def _seg(a, b, lane_z, d=WIRE_D, off=0.0):
    """One crimped trunk SEGMENT between two rail tee headers a=(x,y), b=(x,y): rise to the
    rail corridor at lane_z (above the ribs) and ride it in X (dodging m9). off shifts x AND
    y (the 24 V pair)."""
    (xa, ya), (xb, yb) = a, b
    pts = [(xa, ya, HDR_Z)] + _rail_pts(xa, xb, lane_z) + [(xb, yb, HDR_Z)]
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
    hdrA = {i: (tees[i][0], tees[i][1] - tees[i][2] * 2.0)   # trunk-header (x, y) per tee
            for i in range(len(tees))}
    west = sorted(range(10), key=lambda i: hdrA[i][0])       # bus A west→east

    # bus A CAN head: motor_ctrl J1 -> bay corridor -> -Y rail -> westernmost motor tee;
    # then one crimped segment per hop east. Termination: the controller's JP1 + tee 0's
    # closed jumper -- one at each END of the trunk and nowhere else (ISO 11898).
    # Drawn as the CAN-H (yellow) + CAN-L (green) pair, offset +-CAN_OFF (user).
    xw, yw = hdrA[west[0]]
    # the controller sits in the tray's -X -Y corner with its bus connectors on the
    # WEST edge, so both heads climb the tray's west side before crossing the bay
    _ia = SP(*EL.mctrl_pt("J1"))
    _canA_head = ([_ia, (BAY_X - 5.0, _ia[1], _ia[2]), (BAY_X - 5.0, _ia[1], BAYFLY),
                   (BAY_X, _ia[1], BAYFLY), (BAY_X, RAIL_Y, BAYFLY)]
                  + _rail_pts(BAY_X, xw, LANE_CAN) + [(xw, yw, HDR_Z)])
    for _sfx, _co in (("h", -CAN_OFF), ("l", CAN_OFF)):
        _od = WIRE_OD[f"wire_can{_sfx}"]
        out.append((f"wire_can{_sfx}_0", _wire(
            [(px + _co, py + _co, pz) for px, py, pz in _canA_head], _od)))
        for k in range(9):
            out.append((f"wire_can{_sfx}_{k + 1}",
                        _seg(hdrA[west[k]], hdrA[west[k + 1]], LANE_CAN, _od, off=_co)))

    # bus A drops: each motor's factory 6-pin XH pigtail (grey), from its -Y-facing PCB out
    # to its rail tee. cy = outboard of THIS motor's back so the pigtail never re-enters it;
    # m9 runs through the motor-9 cutout to its tee past the bank.
    for i in range(10):
        tx = tees[i][0]
        mx, sy, mz = D.motor_pos(i)
        back = _motor_back(i)
        cy = min(TEE_Y, back - 3.0)
        out.append((f"motor_pigtail_{i}", _wire([
            (mx, back, mz), (mx, back, -52.0), (mx, cy, -52.0),
            (tx, cy, -52.0), (tx, TEE_Y + 4.5, -52.0), (tx, TEE_Y + 4.5, HDR_Z)],
            WIRE_OD["motor_pigtail"])))

    # 24 V pair (2 × 22 AWG per rail): DC inlet -> AFE tee (10) -> tee 0 ... tee 9 -> buck;
    # the AFE's LDO feed is tee 10's DROP. hot/gnd offset ±PWR_OFF.
    x10, y10 = hdrA[10]
    # the power heads drop just inboard of the bridge endplate's wall, and that wall
    # follows BRIDGE_AXLE_X -- so this lane does too. It was a constant -5.5, and when
    # the bearing grew O8 -> O13 the axle (and the wall) stepped 2.5 -X and clipped the
    # ground wire.
    _PWR_X = D.BRIDGE_AXLE_X - 1.5                              # -8.0
    heads = [(_PWR_X, EL.DC_Y, EL.JACK_Z), (_PWR_X, EL.DC_Y, -52.0), (_PWR_X, TEE_Y, -52.0),
             (x10, TEE_Y, -52.0), (x10, TEE_Y, HDR_Z)]
    _buck = SP(-558.5, -109.5, -50.0)          # BUCK_FP turned with the tray relayout
    tail = ([(hdrA[west[0]][0], hdrA[west[0]][1], HDR_Z)]
            + _rail_pts(hdrA[west[0]][0], BAY_X, LANE_PWR)
            + [(BAY_X, _buck[1], LANE_PWR), (BAY_X, _buck[1], _buck[2]), _buck])   # in to the buck
    # (tee 10's drop fed the AFE's 24 V LDO. The tee survives -- the optical
    #  pickup board takes 24 V off it instead -- but its drop has no modelled
    #  endpoint until that board exists.)
    for _nm, _do in (("wire_pwr_hot", -PWR_OFF), ("wire_pwr_gnd", PWR_OFF)):
        def _off(pts):
            return [(px + _do, py + _do, pz) for px, py, pz in pts]
        out.append((f"{_nm}_0", _wire(_off(heads), WIRE_OD[_nm])))
        out.append((f"{_nm}_1", _seg(hdrA[10], hdrA[west[-1]], LANE_PWR, WIRE_OD[_nm], off=_do)))
        for k in range(9):
            out.append((f"{_nm}_{k + 2}",
                        _seg(hdrA[west[k + 1]], hdrA[west[k]], LANE_PWR, WIRE_OD[_nm], off=_do)))
        out.append((f"{_nm}_11", _wire(_off(tail), WIRE_OD[_nm])))
        # and the controller's own 24 V inlet (J3), tapped at the buck's input: the
        # board's LMR16006 makes its own 3V3, so this is the only rail it takes.
        _j3 = SP(*EL.mctrl_pt("J3"))
        out.append((f"{_nm}_12", _wire(_off(
            [_buck, (_buck[0], _j3[1], _buck[2]), (_j3[0], _j3[1], _buck[2]), _j3]),
            WIRE_OD[_nm])))

    # ── bus B (inputs): motor_ctrl J2 -> the lever boards, NO TEES ────────
    # It used to hop motor_ctrl -> tee 11 -> tee 12. Both are deleted (user), because
    # both ends can now terminate themselves: the lever board passes the trunk THROUGH
    # its own 8-way (in 1-4, out 5-8) so it needs no tap beside it, and the TRRS adapter
    # board carries the leg jack on the board so it needs no landing. What is left is one
    # run from the controller to the first board on the chain.
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
    "wire_pwr_hot":   {"dc_jack", "power_pcb", "tee_pcb", "motor_ctrl"},
    "wire_pwr_gnd":   {"dc_jack", "power_pcb", "tee_pcb", "motor_ctrl"},
    "wire_usb":       {"output_panel", "pi5"},
    "wire_link":      {"motor_ctrl", "pi5"},
    "wire_oled":      {"oled", "pi5"},
    "wire_joy":       {"joystick", "pi5"},
}
