"""Wire harness: net-colored round cables, modeled as cylinder chains.

One component per electrical NET (so splices share a color; every unique
source-dest pairing is its own component/color):

  wire_pickup    white     pickup -> analog front-end (raw, short, at the bridge)
  wire_out       l.gray    AFE relay common -> TS jack (the switched output)
  wire_audio     cyan      AFE buffer out -> Teensy ADC (always feeds Q)
  wire_dac       magenta   Teensy DAC -> AFE relay NO (the processed path)
  wire_relayctrl yellow    Teensy GPIO -> AFE relay driver (UI bypass toggle)
  wire_afepwr    brown     24 V DC inlet -> AFE local LDO (powers buffer/relay)
  wire_can       green     CAN bus: transceiver -> servo daisy chain
  wire_power     red       DC inlet -> servo power chain -> buck input
  wire_usb       blue      USB-C panel -> Pi 5
  wire_link      purple    Teensy <-> Pi data link
  wire_canjmp    orange    Teensy CAN TX/RX <-> transceiver logic side
  wire_tdm       teal      CS42448 stack TDM -> Pi

Analog architecture: the pickup is buffered AT the bridge (AFE), so the long
run to the keyhead ADC is low-impedance and noise-tolerant. A true-bypass
relay on the AFE sends the raw buffered signal straight to the jack by default
and swaps to the DAC (Q-processed) output when the Teensy energizes it.

Routing: a 6-lane floor trunk at z -70.6 (under the motors) passes every
cross-rib through diamond raceways. Per-motor stubs (CAN, power) dive to
z -74.65 under the lanes and rise into each body. Cross-trunk traverses also
duck to z -74.65 to pass under the lanes. Wire ends clip ~1-2 mm into their
declared source/destination bodies to show the connection (whitelisted);
everywhere else the gate enforces clearance.

NOTE: each net is drawn as ONE conductor for clarity; physically power and CAN
are pairs (V+/GND, CAN-H/L) and the audio runs are shielded - a schematic
simplification, not a wiring spec.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import electronics as EL

WIRE_D = 3.5

# floor-trunk lane y's (rib raceway diamonds are cut at these, z -70.65).
# All sit +Y of the AFE pedestal (y <= -104); spacing 8 keeps riser gaps >= 4.
LANE_AUDIO = -59.5       # buffered pickup -> ADC (motor 0's wall foot reaches
                         # y -56.8, so 2.7 clear)
LANE_CAN   = -67.5       # CAN bus (motor stubs)
LANE_PWR   = -75.5       # 24 V (motor stubs)
LANE_USB   = -83.5       # USB-C -> Pi
LANE_DAC   = -91.5       # DAC -> AFE
LANE_CTRL  = -99.5       # relay control -> AFE
LANE_Z = -70.6
STUB_Z = -74.65          # under-lane crossing level
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
        (-40.0, -76.0, -40.0), (-24.0, -80.0, -50.0), afe_buf_in])))

    # -- AFE relay common -> TS jack (l.gray, short, over the boss top; ends
    #    off-axis in the jack's body wall, clear of the new socket bore)
    out.append(("wire_out", _wire([
        afe_relay_c, (0.0, -78.0, -52.0), (3.0, -72.0, -54.0),
        (2.5, EL.TS_Y, EL.JACK_Z + 4.5)])))

    # The three long runs leave the AFE westward (above the boss top, z -52),
    # drop into the open floor WEST of the boss (x <= -46), traverse under the
    # lanes to their lane y, run to the keyhead, rise EAST of the tray AND east
    # of the USB riser (x -518), y-traverse east of the CS stack, fly west into
    # the shield. Staggered drop-x / lane / fly-z / shield-y so no two meet.
    def _long(pad, drop_x, lane_y, fly_z, sh_x, sh_y):
        return _wire([
            pad, (pad[0], pad[1], -52.0),                   # rise off the board
            (drop_x, pad[1], -52.0),                        # west over open floor
            (drop_x, pad[1], STUB_Z), (drop_x, lane_y, STUB_Z),
            (drop_x, lane_y, LANE_Z), (-536.0, lane_y, LANE_Z),
            (-536.0, lane_y, fly_z), (-536.0, sh_y, fly_z),  # y-traverse east of CS
            (sh_x, sh_y, fly_z), (sh_x, sh_y, shield_top - 1.0)])

    out.append(("wire_audio",
                _long(afe_buf_out, -46.0, LANE_AUDIO, -37.0, -596.0, -60.0)))
    out.append(("wire_dac",
                _long(afe_relay_no, -52.0, LANE_DAC, -40.0, -590.0, -71.0)))
    out.append(("wire_relayctrl",
                _long(afe_coil, -58.0, LANE_CTRL, -29.0, -584.0, -76.0)))

    # -- CAN bus (green): transceiver -> floor lane -> stub into every motor
    head = [(-608.0, -45.0, -57.0), (-608.0, -45.0, -38.0),
            (-543.0, -45.0, -38.0), (-543.0, -45.0, STUB_Z),
            (-543.0, LANE_CAN, STUB_Z), (-543.0, LANE_CAN, LANE_Z)]
    out.append(("wire_can",
                _wire(head + _chain(LANE_CAN, 14.0, -543.0, -94.0)[1:])))

    # -- power (red): DC inlet -> NORTH of the AFE/boss -> floor lane west +
    #    stub to every motor -> buck
    # cross from the inlet y (-86) up to the power lane (-75.5) EAST of where
    # the USB lane begins (x -30), so the two never share a y-crossing
    head = [(2.0, EL.DC_Y, EL.JACK_Z), (2.0, EL.DC_Y, -49.0),
            (-26.0, EL.DC_Y, -49.0), (-26.0, EL.DC_Y, STUB_Z),
            (-26.0, LANE_PWR, STUB_Z), (-26.0, LANE_PWR, LANE_Z)]
    tail = [(-541.0, LANE_PWR, -50.0), (-558.0, LANE_PWR, -50.0),
            (-558.0, -88.0, -50.0)]
    afe_branch = [(2.0, EL.DC_Y, EL.JACK_Z), (-1.0, -92.0, -53.0), afe_pwr]
    out.append(("wire_power", _wire(
        head + _chain(LANE_PWR, 18.0, -26.0, -541.0)[1:] + tail)
        .union(_wire(afe_branch))))

    # -- USB (blue): USB-C panel -> up OVER the AFE, shift to its lane y while
    #    still high (clear of the AFE's -Y exit corridors), drop west of the
    #    boss -> floor lane -> bay -> Pi
    out.append(("wire_usb", _wire([
        (5.0, EL.USB_Y, EL.JACK_Z), (-8.0, EL.USB_Y, -45.0),
        (-8.0, LANE_USB, -45.0), (-30.0, LANE_USB, -45.0),
        (-30.0, LANE_USB, LANE_Z), (-542.0, LANE_USB, LANE_Z),
        (-542.0, LANE_USB, -33.0), (-566.0, LANE_USB, -33.0),
        (-566.0, 10.0, -33.0), (-566.0, 10.0, -44.0)])))

    # -- Teensy <-> Pi link (purple)
    out.append(("wire_link", _wire([
        (-572.0, -67.0, shield_top - 0.6), (-572.0, -67.0, -42.5),
        (-572.0, 5.0, -42.5), (-572.0, 5.0, -45.0)])))

    # -- Teensy <-> CAN transceiver (orange)
    out.append(("wire_canjmp", _wire([
        (-616.0, -66.0, shield_top - 0.6), (-616.0, -66.0, -41.0),
        (-616.0, -44.0, -41.0), (-616.0, -44.0, -57.0)])))

    # -- UI: OLED + joystick (-Y deck band) -> Teensy. Drop just under the deck
    #    (z 7, above the motors / outboard of the strings + belts) and run to the
    #    keyhead, then down into the shield. No floor-trunk lane needed.
    UDZ = 7.0
    out.append(("wire_oled", _wire([
        (EL.UI_X, EL.OLED_Y, EL.DECK_TOP + 1.0), (EL.UI_X, EL.OLED_Y, UDZ),
        (-590.0, EL.OLED_Y, UDZ), (-590.0, -65.0, UDZ),
        (-590.0, -65.0, shield_top - 1.0)])))
    out.append(("wire_joy", _wire([
        (EL.JOY_X, EL.JOY_Y, EL.DECK_TOP + 1.0), (EL.JOY_X, EL.JOY_Y, UDZ),
        (-578.0, EL.JOY_Y, UDZ), (-578.0, -66.0, UDZ),
        (-578.0, -66.0, shield_top - 1.0)])))

    # -- CS42448 TDM -> Pi (teal)
    out.append(("wire_tdm", _wire([
        (-598.0, -100.0, -43.0), (-598.0, -100.0, -33.0),
        (-598.0, -5.0, -33.0), (-598.0, -5.0, -57.0)])))

    return out


# what each net is ALLOWED to touch (its source/destination bodies);
# everything else a wire grazes is a routing bug the gate reports
WIRE_OK = {
    "wire_pickup":    {"pickup", "analog_frontend", "pickup_bar"},
    "wire_out":       {"analog_frontend", "ts_jack"},
    "wire_audio":     {"analog_frontend", "teensy_stack"},
    "wire_dac":       {"analog_frontend", "teensy_stack"},
    "wire_relayctrl": {"analog_frontend", "teensy_stack"},
    "wire_can":       {"can_xcvr", "motor"},
    "wire_power":     {"dc_jack", "motor", "buck", "analog_frontend"},
    "wire_usb":       {"usbc_jack", "pi5"},
    "wire_link":      {"teensy_stack", "pi5"},
    "wire_canjmp":    {"teensy_stack", "can_xcvr"},
    "wire_tdm":       {"cs_stack", "pi5"},
    "wire_oled":      {"oled", "teensy_stack"},
    "wire_joy":       {"joystick", "teensy_stack"},
}
