"""Wire harness: gauge-colored round cables, modeled as cylinder chains.

STRATEGY (July 2026, BOM 'Connectors' section): solder only on PCBs, every
field connection a connector, never inline-splice. Both CAN buses are
TRUNK-AND-DROP over TEE PCBs (electronics.tee_pcb, flat on the floor):
crimped XH jumper SEGMENTS run tee-to-tee (each drawn as its own component,
suffix _N — a segment IS a separate physical cable), and each device hangs
by ONE drop, so unplugging a device never breaks a bus. 120 Ω termination
lives on the boards (teensy_ifc + each bus's LAST tee, jumper closed).

  bus A (motors): teensy_ifc -> tee 9..0 (one per motor; LAST = tee 0,
        easternmost — its jumper is closed). Drop = the SERVO42D's own
        6-pin XH pigtail (motor_pigtail_N, grey). The 24 V pair rides the
        same tees (2 contacts per rail on the 6-pos trunk headers): head
        = DC inlet -> the AFE tee (10) -> tee 0; tail = tee 9 -> buck.
  bus B (inputs): teensy_ifc -> tee 11 (LKL knee station) -> tee 12
        (leg-socket landing, under the tray west of the bay rib; takes
        the chassis TRRS jack's factory cable -> the pedal bar).

One component per physical CABLE. Discrete wires (the 24 V pair) are drawn
individually; jacketed/bundled runs at the bundle OD. Colors (build.py):
HUE = gauge bucket, SHADE = the specific wire within the bucket:

  CAN BUS COLOURS (user override): the CAN + power trunk is shown as its four
  colour-coded conductors, NOT the gauge/shade rule below:
      BLACK  = wire_pwr_gnd  (CAN ground / 0 V return)
      RED    = wire_pwr_hot  (CAN 24 V)
      YELLOW = wire_can*h    (CAN-H, both buses + the transceiver jumper)
      GREEN  = wire_can*l    (CAN-L)
  Each CAN bus is drawn as its CAN-H/CAN-L pair (split ±CAN_OFF); bus A
  (wire_canh/l, motors), bus B (wire_canbh/l, inputs), jumper (wire_canjmph/l).

  The gauge/shade rule still governs the NON-CAN nets:
  BLUE = power pair       (superseded for the CAN power rails above)
  GREEN = 28 AWG SHIELDED (light -> dark)
                          wire_pickup: pickup -> AFE (raw, short)
                          wire_audio:  AFE buffer -> Teensy ADC
                          wire_dac:    Teensy DAC -> AFE relay NO
                          wire_out:    AFE relay common -> TS jack
  AMBER = 28 AWG logic    (light -> dark) wire_relayctrl, wire_link,
                          wire_canjmp (Teensy stack <-> teensy_ifc XH
                          jumper), wire_tdm, wire_oled, wire_joy
  VIOLET = shielded USB-2 wire_usb: USB-C panel -> Pi 5
  GREY = factory jackets  motor_pigtail_N, wire_knee_drop (stub to the
                          LKL station; lands on the kl_pcb XH when the
                          knee harness PCB rev lands)

Analog architecture: the pickup is buffered AT the bridge (AFE), so the long
run to the keyhead ADC is low-impedance and noise-tolerant. A true-bypass
relay on the AFE sends the raw buffered signal straight to the jack by default
and swaps to the DAC (Q-processed) output when the Teensy energizes it.

Routing: a 6-lane floor trunk at z -69.7 (under the motors) passes every
cross-rib through SHALLOW gable raceways (chassis._raceway) whose floor stays
0.4 clear of the knee-lever rib-mortise tip (-71.42) -- the harness never
blocks a floating tenon sliding to ANY knee depth. Trunk segments still ride
those lanes rib-to-rib; they dip to z -72.6 (between ribs, clear of the
mortise plane) to land on their tee headers. Wire ends clip ~1-2 mm into
their declared source/destination bodies to show the connection
(whitelisted); everywhere else the gate enforces clearance.

The SERVO42D driver is ON the motor, so there are NO stepper phase leads --
the harness is DC bus, CAN, buffered audio and logic only. Insulation is not
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
    "wire_pickup": 2.0, "wire_out": 2.0, "wire_audio": 2.0, "wire_dac": 2.0,
    "wire_relayctrl": 1.4, "wire_usb": 2.6,
    # CAN signal pairs, split into CAN-H / CAN-L discrete conductors
    "wire_canh": 1.3, "wire_canl": 1.3,       # bus A (motors)
    "wire_canbh": 1.3, "wire_canbl": 1.3,     # bus B (inputs)
    "wire_canjmph": 1.2, "wire_canjmpl": 1.2, # Teensy <-> transceiver jumper
    "wire_pwr_hot": 1.8, "wire_pwr_gnd": 1.8,
    "wire_link": 1.4, "wire_tdm": 1.4,
    "wire_oled": 1.4, "wire_joy": 1.4,
    "motor_pigtail": 3.4, "wire_knee_drop": 2.4,
}
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
TEE_Z = _RIB_TOP + 3.0                                   # tee board rides a cradle on the rib tops
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
    stays on the rail and never crosses a rib. 0..9 bus A (one per motor); 10 AFE power;
    11 knee (LKL); 12 leg-socket. The two +X-most motors (8,9) reach the rail, so a tee
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
    out.append((-48.0, TEE_Y, -1))            # 10 AFE power (rail; -X of the +X leg stub at -13.4)
    # bus B (knee + leg-socket): NOT on the crowded motor rail -- inboard of it, near the knee
    # station, clear of the bay tray/buck and the motor tees.
    out.append((-500.0, -100.0, -1))          # 11 knee (LKL): inboard, +X of the housing
    out.append((-538.0, -100.0, +1))          # 12 leg-socket landing: inboard, +X of the bay tray
    return out


_TEE_LIFT = TEE_Z - EL.FLOOR_Z          # lift the tee dummy onto its cradle, above the rib tops


def tee_components():
    """The tee-PCB dummies for the assembly, lifted onto their -Y-rail cradles (above the
    rib tops so no tee sits in a rib). See tee_cradles()."""
    return [(f"tee_pcb_{i}", EL.tee_pcb(x, y, d).translate((0, 0, _TEE_LIFT)))
            for i, (x, y, d) in enumerate(tee_stations())]


def tee_cradles():
    """A 3-wall drop-in pcb_cradle under each tee, on the -Y-rail corridor. The cradle base
    sits on the rib tops; the tee drops in and one M2 screw retains it. Open edge faces +Y
    (the motor side) so the drop pigtail + trunk headers exit toward the corridor."""
    from cadkit.pcb import pcb_cradle
    out = []
    for i, (x, y, d) in enumerate(tee_stations()):
        # bus-A (0..10) sit on the -Y rail: open +Y so the motor pigtail + trunk headers exit
        # toward the motors. bus-B (11 knee, 12 leg) sit inboard: their drop exits toward -Y
        # (down to the knee/leg station), so open -Y or the wall clips the drop cable.
        open_edge = "-y" if i >= 11 else "+y"
        cr = pcb_cradle(18.0, 14.0, screw_xy=(6.5, -4.0), open_edge=open_edge,
                        standoff=TEE_Z - _RIB_TOP, wall_over=1.2)   # pads meet the lifted tee board bottom (TEE_Z)
        out.append((f"tee_cradle_{i}", cr.translate((x, y, _RIB_TOP))))
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
    shield_top = EL.BOARD_Z + 1.0 + 11.0 + EL.BD_T      # Teensy shield top
    # AFE connection pads dip INTO the board top (z -57) to show the join;
    # routing then rises to z -52 (clear of the components). Spread across the
    # board, x -22..-2, y -108..-78.
    PZ = EL.AFE_Z + 0.8
    afe_buf_in   = (EL.AFE_X0 + 3, -80.0, PZ)    # pickup in    (west, +Y)
    afe_buf_out  = (EL.AFE_X0 + 3, -92.0, PZ)    # buffer out   (west, mid)
    afe_relay_no = (EL.AFE_X0 + 3, -100.0, PZ)   # DAC in       (west, -Y)
    afe_coil     = (EL.AFE_X0 + 3, -106.0, PZ)   # relay driver (west, -Y)
    afe_relay_c  = (EL.AFE_X1 - 3, -82.0, PZ)    # relay common (east, +Y -> TS)
    afe_pwr      = (EL.AFE_X1 - 3, -104.0, PZ)   # 24 V LDO     (east, -Y -> 24V)
    # the AFE's 24 V is the SAME net as the motor bus (a splice at the inlet),
    # so it is a branch of wire_power, not its own color

    # -- pickup -> AFE buffer (white, short; passes its own pickup mount). Drops
    # below the -Y height-jack tab (z -9.78..-12.6) while still INBOARD (y>-49)
    # before spreading toward -Y, so it clears the jack + its pad.
    out.append(("wire_pickup", _wire([
        (-50.0, -45.0, -5.0), (-47.0, -49.0, -14.0),
        (-40.0, -76.0, -40.0), (-24.0, -80.0, -50.0), afe_buf_in],
        WIRE_OD["wire_pickup"])))

    # -- AFE relay common -> TS jack (l.gray, short, over the boss top; ends
    #    off-axis in the jack's body wall, clear of the new socket bore).
    #    Sag waypoints stay INBOARD of the end-wall inner face (x <= -3, in
    #    the foot hollow): the panel-jack recess floor rose to -51 (EP-TENON
    #    round), so the old x-0 dip would cross solid wall below it.
    out.append(("wire_out", _wire([
        afe_relay_c, (-3.0, -78.0, -52.0), (-4.5, -72.0, -54.0),
        (-5.0, EL.TS_Y, EL.JACK_Z + 4.5)],
        WIRE_OD["wire_out"])))     # jack moved -X with the centred tip

    # Keyhead routing (24.2" bay): wires reach the bay via the clear corridor
    # between motor 9's rib (-529) and the tray (-547), then fly OVER the boards
    # (tops ~ -42) to drop into their target. Wire-vs-wire crossings are fine
    # (insulated); only solids (motors/boards/chassis) are avoided.
    RISE_X = -552.0          # bay corridor, -X of motor 0 (spans -545..-503) so the fly-up clears it
    BAYFLY = -34.0           # over the bay boards
    out_z = shield_top - 1.0

    def _long(pad, lane_z, sh_x, sh_y, d=WIRE_D):
        """AFE pad -> up over the board -> out to the -Y rail corridor -> ride to the bay
        (dodging m9) -> up into the shield. All above the rib tops (no rib crossing)."""
        px, py, _ = pad
        return _wire([pad, (px, py, -52.0), (px, RAIL_Y, -52.0)]
                     + _rail_pts(px, RISE_X, lane_z)
                     + [(RISE_X, RAIL_Y, BAYFLY), (RISE_X, sh_y, BAYFLY),
                        (sh_x, sh_y, BAYFLY), (sh_x, sh_y, out_z)], d)

    out.append(("wire_audio", _long(afe_buf_out, LANE_AUDIO, -600.0, -62.0, WIRE_OD["wire_audio"])))
    out.append(("wire_dac", _long(afe_relay_no, LANE_DAC, -600.0, -80.0, WIRE_OD["wire_dac"])))
    out.append(("wire_relayctrl", _long(afe_coil, LANE_CTRL, -600.0, -98.0, WIRE_OD["wire_relayctrl"])))

    # ── the two CAN buses: TRUNK-AND-DROP over the rail tee PCBs ────────
    tees = tee_stations()
    hdrA = {i: (tees[i][0], tees[i][1] - tees[i][2] * 2.0)   # trunk-header (x, y) per tee
            for i in range(len(tees))}
    west = sorted(range(10), key=lambda i: hdrA[i][0])       # bus A west→east

    # bus A CAN head: teensy_ifc -> bay corridor -> -Y rail -> westernmost motor tee; then
    # one crimped segment per hop east. Termination: teensy_ifc + tee 0's closed jumper.
    # Drawn as the CAN-H (yellow) + CAN-L (green) pair, offset +-CAN_OFF (user).
    xw, yw = hdrA[west[0]]
    _canA_head = [(-565.0, 42.0, -50.5), (-565.0, 42.0, BAYFLY), (RISE_X, 42.0, BAYFLY),
                  (RISE_X, RAIL_Y, BAYFLY)] + _rail_pts(RISE_X, xw, LANE_CAN) + [(xw, yw, HDR_Z)]
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
    heads = [(-5.5, EL.DC_Y, EL.JACK_Z), (-5.5, EL.DC_Y, -52.0), (-5.5, TEE_Y, -52.0),
             (x10, TEE_Y, -52.0), (x10, TEE_Y, HDR_Z)]
    tail = ([(hdrA[west[0]][0], hdrA[west[0]][1], HDR_Z)]
            + _rail_pts(hdrA[west[0]][0], RISE_X, LANE_PWR)
            + [(RISE_X, RAIL_Y, BAYFLY), (RISE_X, -106.0, BAYFLY),
               (-567.0, -106.0, BAYFLY), (-567.0, -106.0, -50.0)])   # over the tray, buck
    afe_drop = [(x10, TEE_Y + 4.5, HDR_Z), (x10, -104.0, -54.0),
                (-8.0, -104.0, -54.0), afe_pwr]
    for _nm, _do in (("wire_pwr_hot", -PWR_OFF), ("wire_pwr_gnd", PWR_OFF)):
        def _off(pts):
            return [(px + _do, py + _do, pz) for px, py, pz in pts]
        out.append((f"{_nm}_0", _wire(_off(heads), WIRE_OD[_nm])))
        out.append((f"{_nm}_1", _seg(hdrA[10], hdrA[west[-1]], LANE_PWR, WIRE_OD[_nm], off=_do)))
        for k in range(9):
            out.append((f"{_nm}_{k + 2}",
                        _seg(hdrA[west[k + 1]], hdrA[west[k]], LANE_PWR, WIRE_OD[_nm], off=_do)))
        out.append((f"{_nm}_11", _wire(_off(tail), WIRE_OD[_nm])))
        out.append((f"{_nm}_12", _wire(_off(afe_drop), WIRE_OD[_nm])))

    # ── bus B (inputs): ifc -> LKL tee -> leg-socket landing tee ────────
    x11, y11 = hdrA[11]
    _canB_head = [(-557.0, 42.0, -50.5), (-557.0, 42.0, BAYFLY), (RISE_X, 42.0, BAYFLY),
                  (RISE_X, RAIL_Y, BAYFLY)] + _rail_pts(RISE_X, x11, LANE_CTRL) + [(x11, y11, HDR_Z)]
    for _sfx, _co in (("h", -CAN_OFF), ("l", CAN_OFF)):
        _od = WIRE_OD[f"wire_canb{_sfx}"]
        out.append((f"wire_canb{_sfx}_0", _wire(
            [(px + _co, py + _co, pz) for px, py, pz in _canB_head], _od)))
        out.append((f"wire_canb{_sfx}_1",
                    _seg(hdrA[11], hdrA[12], LANE_CTRL, _od, off=_co)))
    # LKL drop stub: from tee 11 down toward the kl_pcb XH at the knee station (ends clear of
    # housing/rib/rail; the last pass-through to the board is a chassis follow-up).
    out.append(("wire_knee_drop", _wire([
        (tees[11][0], tees[11][1] - 4.5, HDR_Z),   # exit tee 11 toward -Y
        (-508.0, -110.0, -60.0)], WIRE_OD["wire_knee_drop"])))  # short stub, clear of the packed -X corner
    # (tee 0/11/12 + kl_pcb all share this station); the -Y/-Z drop onto the kl_pcb XH is the chassis follow-up.

    # -- USB (blue): USB-C panel -> -Y rail corridor -> ride to the bay -> right-angle to Pi
    out.append(("wire_usb", _wire(
        [(-2.5, EL.USB_Y, EL.JACK_Z), (-12.0, EL.USB_Y, -45.0), (-12.0, RAIL_Y, -45.0)]
        + _rail_pts(-12.0, RISE_X, LANE_USB)
        + [(RISE_X, RAIL_Y, BAYFLY), (-560.0, RAIL_Y, BAYFLY),
           (-560.0, 20.0, BAYFLY), (-575.0, 20.0, BAYFLY), (-575.0, 20.0, -44.0)],
        WIRE_OD["wire_usb"])))                          # west of motor 9, then +Y to Pi

    # -- Teensy <-> Pi link (purple): over the bay
    out.append(("wire_link", _wire([
        (-600.0, -60.0, out_z), (-600.0, -60.0, BAYFLY),
        (-560.0, 5.0, BAYFLY), (-560.0, 5.0, -57.0)], WIRE_OD["wire_link"])))

    # -- Teensy <-> CAN transceiver: the CAN-H (yellow) / CAN-L (green) jumper pair
    _canjmp = [(-603.0, -57.0, out_z), (-603.0, -52.0, BAYFLY),
               (-561.0, 49.0, BAYFLY), (-561.0, 49.0, -50.5)]
    for _sfx, _co in (("h", -CAN_OFF), ("l", CAN_OFF)):
        out.append((f"wire_canjmp{_sfx}", _wire(
            [(px + _co, py + _co, pz) for px, py, pz in _canjmp],
            WIRE_OD[f"wire_canjmp{_sfx}"])))

    # -- PCM1864 carrier TDM -> Pi (teal)
    out.append(("wire_tdm", _wire([
        (-566.0, -72.0, -57.0), (-566.0, -72.0, BAYFLY),
        (-580.0, -5.0, BAYFLY), (-580.0, -5.0, -57.0)], WIRE_OD["wire_tdm"])))

    # -- UI: OLED + joystick (-Y deck band) -> Teensy. Drop under the deck, run
    #    to the keyhead, fly over the bay into the shield.
    UDZ = -2.0
    out.append(("wire_oled", _wire([
        (EL.UI_X, EL.OLED_Y, EL.DECK_TOP + 1.0), (EL.UI_X, EL.OLED_Y, UDZ),
        (RISE_X, EL.OLED_Y, UDZ), (RISE_X, -110.0, BAYFLY),
        (-600.0, -110.0, BAYFLY), (-600.0, -110.0, out_z)], WIRE_OD["wire_oled"])))
    out.append(("wire_joy", _wire([
        (EL.JOY_X, EL.JOY_Y, EL.DECK_TOP + 1.0), (EL.JOY_X, EL.JOY_Y, UDZ),
        (RISE_X + 4, EL.JOY_Y, UDZ), (RISE_X + 4, -100.0, BAYFLY),
        (-595.0, -100.0, BAYFLY), (-595.0, -100.0, out_z)], WIRE_OD["wire_joy"])))

    return out


# what each net is ALLOWED to touch (its source/destination bodies);
# everything else a wire grazes is a routing bug the gate reports
WIRE_OK = {
    "wire_pickup":    {"pickup", "analog_frontend", "top_plate",
                       "pickup_zplate", "pickup_xclamp"},
    "wire_out":       {"analog_frontend", "ts_jack"},
    "wire_audio":     {"analog_frontend", "teensy_stack"},
    "wire_dac":       {"analog_frontend", "teensy_stack"},
    "wire_relayctrl": {"analog_frontend", "teensy_stack"},
    "wire_canh":      {"teensy_ifc", "tee_pcb"},
    "wire_canl":      {"teensy_ifc", "tee_pcb"},
    "wire_canbh":     {"teensy_ifc", "tee_pcb"},
    "wire_canbl":     {"teensy_ifc", "tee_pcb"},
    "motor_pigtail":  {"tee_pcb", "motor"},
    "wire_knee_drop": {"tee_pcb"},
    # leg↔body TRRS: the chassis jack's factory cable (tenon channel ->
    # bus-B socket tee) and the column CA-354S inside the leg stack
    "chassis_trrs_cable": {"tee_pcb", "leg_body_stub", "chassis_trrs_jack",
                           "jack_seat_ring"},
    "leg_column_cable": {"leg_body_stub", "leg_segment", "leg_sleeve",
                         "leg_shaft", "leg_column_plug",
                         "leg_plug_retainer", "leg_cable_coil",
                         "leg_latch_head", "leg_junction_pcb",
                         "leg_seg_body", "leg_lid",
                         # the shaft-side model of the SAME physical
                         # CA-354S — they abut inside the shaft channel
                         "pedal_trrs_cable_leg"},
    "leg_cable_coil":   {"leg_segment", "leg_seg_body", "leg_sleeve",
                         "leg_column_cable", "shaft_trrs_cable"},
    "shaft_trrs_cable": {"leg_shaft", "leg_sleeve", "leg_seg_body",
                         "shaft_trrs_jack", "leg_cable_coil",
                         "leg_junction_pcb", "leg_latch_head"},
    "wire_pwr_hot":   {"dc_jack", "buck", "tee_pcb", "analog_frontend"},
    "wire_pwr_gnd":   {"dc_jack", "buck", "tee_pcb", "analog_frontend"},
    "wire_usb":       {"usbc_jack", "pi5"},
    "wire_link":      {"teensy_stack", "pi5"},
    "wire_canjmph":   {"teensy_stack", "teensy_ifc"},
    "wire_canjmpl":   {"teensy_stack", "teensy_ifc"},
    "wire_tdm":       {"adc_stack", "pi5"},
    "wire_oled":      {"oled", "teensy_stack"},
    "wire_joy":       {"joystick", "teensy_stack"},
}
