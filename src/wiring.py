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

  BLUE = power pair       wire_pwr_hot (dark) / wire_pwr_gnd (light):
                          2 × 22 AWG PER RAIL in the crimped trunk jumpers
                          (XH contacts take 22 AWG max; <5 A staggered slew
                          = 2.5 A/contact), drawn as one rod per rail
  RED = CAN               wire_can (bus A) / wire_canb (bus B): 22 AWG
                          pairs inside the crimped trunk jumpers
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

# modeled cable OD per net (mm): jacketed bundles (CAN/shielded/USB) drawn as
# ONE round conductor at the jacket OD; the 24 V pair as TWO discrete 20 AWG
# silicone wires. Nothing exceeds 2.6.
WIRE_OD = {
    "wire_pickup": 2.0, "wire_out": 2.0, "wire_audio": 2.0, "wire_dac": 2.0,
    "wire_relayctrl": 1.4, "wire_can": 2.2, "wire_canb": 2.4, "wire_usb": 2.6,
    "wire_pwr_hot": 1.8, "wire_pwr_gnd": 1.8,
    "wire_link": 1.4, "wire_canjmp": 1.4, "wire_tdm": 1.4,
    "wire_oled": 1.4, "wire_joy": 1.4,
    "motor_pigtail": 3.4, "wire_knee_drop": 2.4,
}
PWR_OFF = 1.2         # 24 V hot/gnd separation, applied in BOTH x and y (+off /
                      # -off): a single-axis offset leaves the pair COLLINEAR on
                      # runs along that axis (the y-offset pair coincided on the
                      # y-running motor stubs). x-runs separate by the y part,
                      # y-runs by the x part, verticals by both. Lane edges at
                      # 1.2 + 0.9 = 2.1 < RACE_HW 2.4.
WIRE_D = 2.0          # default (shielded-pair size)

# floor-trunk lane y's (rib raceway diamonds are cut at these, z -70.65).
# All sit +Y of the AFE pedestal (y <= -104); spacing 8 keeps riser gaps >= 4.
LANE_AUDIO = -59.5       # buffered pickup -> ADC (motor 0's wall foot reaches
                         # y -56.8, so 2.7 clear)
LANE_CAN   = -67.5       # CAN bus (motor stubs)
LANE_PWR   = -75.5       # 24 V (motor stubs)
LANE_USB   = -83.5       # USB-C -> Pi
LANE_DAC   = -91.5       # DAC -> AFE
LANE_CTRL  = -99.5       # relay control -> AFE
LANE_Z = -69.6           # trunk centre: the max-OD (2.6) wire bottoms out 0.1
                         # above the raceway floor (-71.02); every OD stays
                         # inside the gable
STUB_Z = -72.6           # under-lane crossing level (between ribs; bottom of a
                         # 2.4 stub = -73.8, still 1.35 above the bed)
RIB_RACE_Y = (LANE_AUDIO, LANE_CAN, LANE_PWR, LANE_USB, LANE_DAC, LANE_CTRL)


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


def _riser_y(sy):
    """Stub riser y inside a motor body footprint (body y = sy-84..sy+4), kept
    >= 4 mm from every trunk lane. The lanes (pitch 8) and motors (pitch 9.5)
    beat, so a fixed offset hits a lane for most motors; instead pick from
    ABSOLUTE clear zones - below the whole band (open floor, for -Y motors),
    the lane-gap centres, or +Y of the band - first that lands in the body."""
    cands = [-103.5, -95.5, -87.5, -79.5, -71.5, -63.5, -55.5,
             sy - 30, sy - 20, sy - 10, sy]
    for y in cands:
        if sy - 84 <= y <= sy + 4 and all(abs(y - L) >= 4.0 for L in RIB_RACE_Y):
            return y
    return sy - 30


# ── tee stations (trunk-and-drop; see the header) ────────────────────────
TEE_Y_A = -71.5          # bus A tees sit between the CAN and PWR lanes
HDR_Z = EL.FLOOR_Z + 8.1  # tee header top (wire entry z)


def tee_stations():
    """[(x, y, drop_sign)] — 0..9 bus A (one per motor), 10 AFE power tee,
    11 bus B knee (LKL), 12 bus B leg-socket landing (west of the bay rib,
    under the tray — reachable from the -X/+Y socket without crossing an
    un-racewayed rib)."""
    out = [(D.motor_pos(i)[0] + 16.0, TEE_Y_A, +1) for i in range(10)]
    out.append((-42.0, -108.0, -1))      # 10: AFE power tee — SOUTH of all
                                         #     six lanes (a tee inside the
                                         #     lane band collides with the
                                         #     passing runs) and west of the
                                         #     AFE (x ≥ -22)
    out.append((-545.0, -110.0, -1))     # 11: LKL knee station (bay edge —
                                         #     clear of the housing, y≤-122.7)
    out.append((-581.5, 40.0, +1))       # 12: leg-socket cable landing (in
                                         # the rib GAP -588..-575: the flush
                                         # round un-severed the station rib,
                                         # which now owns x -598..-588)
    return out


def tee_components():
    """The tee-PCB dummies for the assembly."""
    return [(f"tee_pcb_{i}", EL.tee_pcb(x, y, d))
            for i, (x, y, d) in enumerate(tee_stations())]


def _seg(a, b, lane_y, d=WIRE_D, off=0.0):
    """One crimped trunk SEGMENT between tee headers at a=(x,y) and
    b=(x,y): dip under, cross to the raceway lane, ride it rib-to-rib,
    dip back to the far header. off shifts x AND y (the 24 V pair)."""
    (xa, ya), (xb, yb) = a, b
    pts = [(xa, ya, HDR_Z), (xa, ya, STUB_Z), (xa, lane_y, STUB_Z),
           (xa, lane_y, LANE_Z), (xb, lane_y, LANE_Z),
           (xb, lane_y, STUB_Z), (xb, yb, STUB_Z), (xb, yb, HDR_Z)]
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

    # -- pickup -> AFE buffer (white, short; passes its own pickup mount)
    out.append(("wire_pickup", _wire([
        (-50.0, -45.0, -5.0), (-44.0, -60.0, -14.0),
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
    RISE_X = -538.0          # corridor between motor 9's rib and the tray
    BAYFLY = -34.0           # over the bay boards
    out_z = shield_top - 1.0

    def _long(pad, drop_x, lane_y, sh_x, sh_y, d=WIRE_D):
        return _wire([
            pad, (pad[0], pad[1], -52.0), (drop_x, pad[1], -52.0),
            (drop_x, pad[1], STUB_Z), (drop_x, lane_y, STUB_Z),
            (drop_x, lane_y, LANE_Z), (RISE_X, lane_y, LANE_Z),
            (RISE_X, lane_y, BAYFLY), (RISE_X, sh_y, BAYFLY),
            (sh_x, sh_y, BAYFLY), (sh_x, sh_y, out_z)], d)

    out.append(("wire_audio", _long(afe_buf_out, -46.0, LANE_AUDIO, -600.0, -62.0,
                                    WIRE_OD["wire_audio"])))
    out.append(("wire_dac", _long(afe_relay_no, -52.0, LANE_DAC, -600.0, -80.0,
                                  WIRE_OD["wire_dac"])))
    out.append(("wire_relayctrl", _long(afe_coil, -58.0, LANE_CTRL, -600.0, -98.0,
                                        WIRE_OD["wire_relayctrl"])))

    # ── the two CAN buses: TRUNK-AND-DROP over the tee PCBs ─────────────
    tees = tee_stations()
    hdrA = {i: (tees[i][0], tees[i][1] - tees[i][2] * 2.0)   # trunk-header
            for i in range(len(tees))}                       # (x, y) per tee
    west = sorted(range(10), key=lambda i: hdrA[i][0])       # bus A west→east

    # bus A CAN head: teensy_ifc busA header -> corridor -> CAN lane -> the
    # westernmost motor tee (tee 9); then one crimped segment per hop east.
    # Termination: teensy_ifc (this end) + tee 0's closed jumper (far end).
    xw, yw = hdrA[west[0]]
    out.append(("wire_can_0", _wire([
        (-565.0, 42.0, -50.5), (-565.0, 42.0, BAYFLY),
        (RISE_X, 42.0, BAYFLY), (RISE_X, 42.0, STUB_Z),
        (RISE_X, -51.0, STUB_Z),
        (RISE_X, LANE_CAN, STUB_Z), (RISE_X, LANE_CAN, LANE_Z),
        (xw, LANE_CAN, LANE_Z), (xw, LANE_CAN, STUB_Z),
        (xw, yw, STUB_Z), (xw, yw, HDR_Z)], WIRE_OD["wire_can"])))
    for k in range(9):
        out.append((f"wire_can_{k + 1}",
                    _seg(hdrA[west[k]], hdrA[west[k + 1]], LANE_CAN,
                         WIRE_OD["wire_can"])))

    # bus A drops: each motor's OWN factory 6-pin XH pigtail (grey), from
    # its tee's drop header up into the motor body (no splices anywhere)
    for i in range(10):
        tx, sy = tees[i][0], D.motor_pos(i)[1]
        ry = _riser_y(sy)
        out.append((f"motor_pigtail_{i}", _wire([
            (tx, TEE_Y_A + 4.5, HDR_Z), (tx, TEE_Y_A + 4.5, STUB_Z),
            (tx, ry, STUB_Z), (tx, ry, -63.0)], WIRE_OD["motor_pigtail"])))

    # 24 V pair (2 × 22 AWG per rail in the trunk jumpers): DC inlet ->
    # AFE tee (10) -> tee 0 ... tee 9 -> buck; the AFE's LDO feed is tee
    # 10's DROP (no splice at the inlet). hot/gnd offset ±PWR_OFF.
    x10, y10 = hdrA[10]
    # inlet drop: dodge the AFE pedestal (x -24..0, y -110..-76, top -61)
    # to its NORTH, fly WEST at -63.4 OVER the wide corner rib + the x -18
    # comb rib (tops -65.15) and clear of the -24.07/-12.73 leg ridges
    # (roofs -67.91), then drop straight onto tee 10's header WEST of the
    # rib (the old bay dive at (-26,-97)/(-31,-104) is rib body now)
    heads = [(-5.5, EL.DC_Y, EL.JACK_Z), (-5.5, EL.DC_Y, -52.0),
             (-5.5, -74.0, -56.0), (-12.0, -74.0, -63.4),
             (-26.0, -74.0, -63.4), (x10 + 5.5, y10, -63.4),
             (x10 + 5.5, y10, HDR_Z)]
    tail9 = [(hdrA[west[0]][0], hdrA[west[0]][1], HDR_Z),
             (hdrA[west[0]][0], hdrA[west[0]][1], STUB_Z),
             (hdrA[west[0]][0], LANE_PWR, STUB_Z),
             (hdrA[west[0]][0], LANE_PWR, LANE_Z),
             (RISE_X, LANE_PWR, LANE_Z), (RISE_X, LANE_PWR, BAYFLY),
             (RISE_X, -106.0, BAYFLY), (-567.0, -106.0, BAYFLY),
             (-567.0, -106.0, -50.0)]                    # over the tray, buck
    afe_drop = [(x10, tees[10][1] - 4.5, HDR_Z), (x10, tees[10][1] - 4.5, -66.0),
                (-24.0, -112.0, -56.0), (-5.0, -106.0, -53.0), afe_pwr]
    for _nm, _do in (("wire_pwr_hot", -PWR_OFF), ("wire_pwr_gnd", PWR_OFF)):
        def _off(pts):
            return [(px + _do, py + _do, pz) for px, py, pz in pts]
        out.append((f"{_nm}_0", _wire(_off(heads), WIRE_OD[_nm])))
        out.append((f"{_nm}_1", _seg(hdrA[10], hdrA[west[-1]], LANE_PWR,
                                     WIRE_OD[_nm], off=_do)))
        for k in range(9):
            out.append((f"{_nm}_{k + 2}",
                        _seg(hdrA[west[k + 1]], hdrA[west[k]], LANE_PWR,
                             WIRE_OD[_nm], off=_do)))
        out.append((f"{_nm}_11", _wire(_off(tail9), WIRE_OD[_nm])))
        out.append((f"{_nm}_12", _wire(_off(afe_drop), WIRE_OD[_nm])))

    # ── bus B (inputs): ifc -> LKL tee -> leg-socket landing tee ────────
    x11, y11 = hdrA[11]
    out.append(("wire_canb_0", _wire([
        (-557.0, 42.0, -50.5), (-557.0, 42.0, BAYFLY),
        (RISE_X, 42.0, BAYFLY), (RISE_X, 42.0, STUB_Z),
        (RISE_X, -49.0, STUB_Z),
        (RISE_X, LANE_CTRL, STUB_Z), (RISE_X, LANE_CTRL, LANE_Z),
        (x11, LANE_CTRL, LANE_Z), (x11, LANE_CTRL, STUB_Z),
        (x11, y11, STUB_Z), (x11, y11, HDR_Z)], WIRE_OD["wire_canb"])))
    out.append(("wire_canb_1", _seg(hdrA[11], hdrA[12], LANE_CTRL,
                                    WIRE_OD["wire_canb"])))
    # LKL drop stub: drawn to the STATION BOUNDARY (housing starts y -122.7;
    # its kl_pcb sits OUTBOARD at y≈-127 below the floor). The last ~15 mm
    # to the kl_pcb's XH needs a small rail/floor pass-through near the
    # knee station — flagged as a CHASSIS REQUEST; until then the stub ends
    # clear of housing, rib and rail.
    out.append(("wire_knee_drop", _wire([
        (-545.0, tees[11][1] - 4.5, HDR_Z), (-537.0, -118.0, -71.0),
        (-533.0, -119.5, -71.0)], WIRE_OD["wire_knee_drop"])))

    # -- USB (blue): USB-C panel -> floor lane -> corridor -> right-angle to Pi
    # (the floor-lane descent moved WEST of the +X wide corner rib)
    out.append(("wire_usb", _wire([
        (-2.5, EL.USB_Y, EL.JACK_Z), (-12.0, EL.USB_Y, -45.0),
        (-12.0, LANE_USB, -45.0), (-47.0, LANE_USB, -45.0),    # clear the -X jack body
        (-47.0, LANE_USB, LANE_Z), (RISE_X, LANE_USB, LANE_Z),    # descend WEST of the
        #                                    -41 comb rib (the wide corner rib owns -35.4..)
        (RISE_X, LANE_USB, BAYFLY), (-560.0, LANE_USB, BAYFLY),
        (-560.0, 20.0, BAYFLY), (-575.0, 20.0, BAYFLY),
        (-575.0, 20.0, -44.0)],
        WIRE_OD["wire_usb"])))                         # west of motor 9, then +Y to Pi

    # -- Teensy <-> Pi link (purple): over the bay
    out.append(("wire_link", _wire([
        (-600.0, -60.0, out_z), (-600.0, -60.0, BAYFLY),
        (-560.0, 5.0, BAYFLY), (-560.0, 5.0, -57.0)], WIRE_OD["wire_link"])))

    # -- Teensy <-> CAN transceiver (orange): both at the -X corner
    out.append(("wire_canjmp", _wire([
        (-603.0, -57.0, out_z), (-603.0, -52.0, BAYFLY),
        (-561.0, 49.0, BAYFLY), (-561.0, 49.0, -50.5)], WIRE_OD["wire_canjmp"])))

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
    "wire_can":       {"teensy_ifc", "tee_pcb"},
    "wire_canb":      {"teensy_ifc", "tee_pcb"},
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
    "wire_canjmp":    {"teensy_stack", "teensy_ifc"},
    "wire_tdm":       {"adc_stack", "pi5"},
    "wire_oled":      {"oled", "teensy_stack"},
    "wire_joy":       {"joystick", "teensy_stack"},
}
