"""Wire harness: gauge-colored round cables, modeled as cylinder chains.

One component per physical CABLE. Discrete wires (the 24 V pair) are drawn
individually; jacketed cables (CAN pair, shielded audio, USB) are drawn as one
conductor at the jacket OD. Colors (build.py): HUE = gauge bucket, SHADE = the
specific wire within the bucket:

  BLUE = 20 AWG power     wire_pwr_hot (dark) / wire_pwr_gnd (light):
                          DC inlet -> servo chain -> buck, + AFE LDO branch
  RED = 26 AWG CAN pair   wire_can: transceiver -> servo daisy chain
  GREEN = 28 AWG SHIELDED (light -> dark)
                          wire_pickup: pickup -> AFE (raw, short)
                          wire_audio:  AFE buffer -> Teensy ADC
                          wire_dac:    Teensy DAC -> AFE relay NO
                          wire_out:    AFE relay common -> TS jack
  AMBER = 28 AWG logic    (light -> dark) wire_relayctrl, wire_link,
                          wire_canjmp, wire_tdm, wire_oled, wire_joy
  VIOLET = shielded USB-2 wire_usb: USB-C panel -> Pi 5

Analog architecture: the pickup is buffered AT the bridge (AFE), so the long
run to the keyhead ADC is low-impedance and noise-tolerant. A true-bypass
relay on the AFE sends the raw buffered signal straight to the jack by default
and swaps to the DAC (Q-processed) output when the Teensy energizes it.

Routing: a 6-lane floor trunk at z -69.7 (under the motors) passes every
cross-rib through SHALLOW gable raceways (chassis._raceway) whose floor stays
0.4 clear of the knee-lever rib-mortise tip (-71.42) -- the harness never
blocks a floating tenon sliding to ANY knee depth. Per-motor stubs (CAN,
power) dive to z -72.6 under the lanes (between ribs, clear of the mortise
plane) and rise into each body. Wire ends clip ~1-2 mm into their declared
source/destination bodies to show the connection (whitelisted); everywhere
else the gate enforces clearance.

CABLE SPEC (per net; OD drives the model + raceway size). The SERVO42D driver
is ON the motor, so there are NO stepper phase leads -- the harness is DC bus,
CAN, buffered audio and logic only. Insulation is not an EMI defence: noise
immunity comes from SHIELDING (audio), TWISTING (power, CAN) and buffering at
the source (the AFE at the bridge). Gauges:
  power      20 AWG pair, twisted/flat (10-motor worst-case slew ~6-10 A at
             24 V is staggered by firmware to <5 A; drop over ~1.2 m ~0.3 V)
  can        26 AWG twisted pair (120R terminated)
  pickup/audio/dac/out  28 AWG SHIELDED pair (mA signals -- the shield is the
             spec, not the copper)
  usb        slim shielded USB-2 (28 AWG cores)
  logic (relayctrl/link/canjmp/tdm/oled/joy)  28 AWG
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
    "wire_relayctrl": 1.4, "wire_can": 2.2, "wire_usb": 2.6,
    "wire_pwr_hot": 1.8, "wire_pwr_gnd": 1.8,
    "wire_link": 1.4, "wire_canjmp": 1.4, "wire_tdm": 1.4,
    "wire_oled": 1.4, "wire_joy": 1.4,
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


def _chain(lane_y, x_off, x_from, x_to):
    """Trunk run along lane_y with a dive-under stub into each motor."""
    pts = [(x_from, lane_y, LANE_Z)]
    motors = sorted(((D.motor_pos(i)[0], D.motor_pos(i)[1]) for i in range(10)),
                    key=lambda m: m[0], reverse=(x_from > x_to))
    for mx, sy in motors:
        sx = mx + x_off
        if not (min(x_from, x_to) < sx < max(x_from, x_to)):
            continue
        ry = _riser_y(sy)
        pts += [(sx, lane_y, LANE_Z), (sx, lane_y, STUB_Z),
                (sx, ry, STUB_Z), (sx, ry, -63.0),          # ~2 into the body
                (sx, ry, STUB_Z), (sx, lane_y, STUB_Z),
                (sx, lane_y, LANE_Z)]
    pts.append((x_to, lane_y, LANE_Z))
    return pts


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
    #    off-axis in the jack's body wall, clear of the new socket bore)
    out.append(("wire_out", _wire([
        afe_relay_c, (0.0, -78.0, -52.0), (-4.5, -72.0, -54.0),
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

    # -- CAN bus (green): transceiver -> corridor -> floor lane -> every motor
    head = [(-598.0, -46.0, -57.0), (-598.0, -46.0, BAYFLY),
            (RISE_X, -46.0, BAYFLY), (RISE_X, -46.0, STUB_Z),
            (RISE_X, LANE_CAN, STUB_Z), (RISE_X, LANE_CAN, LANE_Z)]
    out.append(("wire_can",
                _wire(head + _chain(LANE_CAN, 14.0, RISE_X, -94.0)[1:],
                      WIRE_OD["wire_can"])))

    # -- power (red): DC inlet -> floor lane + stub to every motor -> buck
    head = [(-5.5, EL.DC_Y, EL.JACK_Z), (-5.5, EL.DC_Y, -49.0),
            (-26.0, EL.DC_Y, -49.0), (-26.0, EL.DC_Y, STUB_Z),
            (-26.0, LANE_PWR, STUB_Z), (-26.0, LANE_PWR, LANE_Z)]
    tail = [(RISE_X, LANE_PWR, LANE_Z), (RISE_X, LANE_PWR, BAYFLY),
            (RISE_X, -106.0, BAYFLY), (-567.0, -106.0, BAYFLY),
            (-567.0, -106.0, -50.0)]                      # over the tray, into buck
    afe_branch = [(-5.5, EL.DC_Y, EL.JACK_Z), (-1.0, -92.0, -53.0), afe_pwr]
    # hot + ground drawn as the two discrete 20 AWG wires they are, offset
    # +-PWR_OFF in x AND y so the pair runs side-by-side on every leg — lanes
    # (x-runs), motor stubs (y-runs) and verticals alike (wire-on-wire contact
    # is fine; both stay inside the raceway)
    ppts = head + _chain(LANE_PWR, 18.0, -26.0, RISE_X)[1:] + tail
    for _nm, _do in (("wire_pwr_hot", -PWR_OFF), ("wire_pwr_gnd", PWR_OFF)):
        out.append((_nm, _wire([(px + _do, py + _do, pz) for px, py, pz in ppts],
                               WIRE_OD[_nm])
                    .union(_wire([(px + _do, py + _do, pz) for px, py, pz in afe_branch],
                                 WIRE_OD[_nm]))))

    # -- USB (blue): USB-C panel -> floor lane -> corridor -> right-angle to Pi
    out.append(("wire_usb", _wire([
        (-2.5, EL.USB_Y, EL.JACK_Z), (-12.0, EL.USB_Y, -45.0),
        (-12.0, LANE_USB, -45.0), (-30.0, LANE_USB, -45.0),    # clear the -X jack body
        (-30.0, LANE_USB, LANE_Z), (RISE_X, LANE_USB, LANE_Z),
        (RISE_X, LANE_USB, BAYFLY), (-560.0, LANE_USB, BAYFLY),
        (-560.0, 40.0, BAYFLY), (-575.0, 40.0, BAYFLY),
        (-575.0, 40.0, -44.0)],
        WIRE_OD["wire_usb"])))                         # west of motor 9, then +Y to Pi

    # -- Teensy <-> Pi link (purple): over the bay
    out.append(("wire_link", _wire([
        (-600.0, -60.0, out_z), (-600.0, -60.0, BAYFLY),
        (-560.0, 5.0, BAYFLY), (-560.0, 5.0, -57.0)], WIRE_OD["wire_link"])))

    # -- Teensy <-> CAN transceiver (orange): both at the -X corner
    out.append(("wire_canjmp", _wire([
        (-603.0, -57.0, out_z), (-603.0, -52.0, BAYFLY),
        (-598.0, -48.0, BAYFLY), (-598.0, -48.0, -57.0)], WIRE_OD["wire_canjmp"])))

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
    "wire_can":       {"can_xcvr", "motor"},
    "wire_pwr_hot":   {"dc_jack", "motor", "buck", "analog_frontend"},
    "wire_pwr_gnd":   {"dc_jack", "motor", "buck", "analog_frontend"},
    "wire_usb":       {"usbc_jack", "pi5"},
    "wire_link":      {"teensy_stack", "pi5"},
    "wire_canjmp":    {"teensy_stack", "can_xcvr"},
    "wire_tdm":       {"cs_stack", "pi5"},
    "wire_oled":      {"oled", "teensy_stack"},
    "wire_joy":       {"joystick", "teensy_stack"},
}
