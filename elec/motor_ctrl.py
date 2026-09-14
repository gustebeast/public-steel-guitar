"""Motor controller — the head of both CAN buses, x1.

    py -3.12 elec/motor_ctrl.py         # -> elec/out/motor_ctrl.{net,board.json}

ONE JOB (user): read the lever and pedal angles off bus B, apply the saved travel
offsets, and command the SERVO42Ds on bus A. Audio, pitch detection, the OLED and
the joystick all live on the Raspberry Pi; the Pi computes what the offsets should
be during tuning and writes them down here, and this board then runs without it.

IT REPLACES THREE THINGS: the Teensy 4.1 ($31.50), its SGTL5000 audio shield
($9.80) and the teensy_ifc carrier. The Teensy's value was the Audio Library, USB
high-speed and the codec -- all irrelevant once no audio touches this board. What
could NOT be deleted is the pair of CAN TRANSCEIVERS: no general-purpose MCU
integrates one, because a transceiver has to survive +-58 V bus faults and cannot
share a die with 3.3 V logic. So the board was always going to exist; the only
question was whether an MCU sat on it too.

CAPACITY, checked rather than assumed. On a pedal steel one pedal changes several
strings, so "a few controls moving" IS the ten-motor case:
    bus A, 10 motors, 8-byte frames, command + drive reply
      500 kbps @ 100 Hz -> 52%       500 kbps @ 200 Hz -> 104%  (over)
      1 Mbps   @ 200 Hz -> 52%
    bus B, 8 sensor boards, 2-byte frames @ 500 Hz
      500 kbps -> 57.6%              1 Mbps -> 28.8%
52% is the target, not 90%: CAN arbitrates by priority, so high utilisation
delays low-priority frames unpredictably -- the headroom buys latency, not just
throughput. Worth confirming the SERVO42Ds will run 1 Mbps; it doubles the margin.
The MCU is nowhere near the limit -- ~6,000 frames/s across both buses is
single-digit percent of a 144 MHz core with two HARDWARE CAN controllers.

⚠ CAN1 IS REMAPPED, AND THAT IS A LAYOUT DECISION, NOT A FIRMWARE ONE. CAN1's
default pins are PA11/PA12 -- which are also OTG_FS_DM/DP. This board needs USB
to the Pi AND both buses, so bus A's transceiver goes on CAN1's REMAP, PB8/PB9
(pins 64/65). Wire it to PA11/PA12 and no firmware setting can rescue it.

EVERY PIN NUMBER IS OFF THE DATASHEET, parsed from WCH's own QFN-68 column
(CH32V303/305/307/317 datasheet V3.9, table 3-1), not trusted to a library symbol.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import json  # noqa: E402

from skidl import ERC, Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

P = Pin.types.PASSIVE
I, O, PWR = Pin.types.INPUT, Pin.types.OUTPUT, Pin.types.PWRIN

XH_PINOUT = ("GND", "V24", "CAN_H", "CAN_L")     # same order as every other board
MCU_FP = "Package_DFN_QFN:QFN-68-1EP_8x8mm_P0.4mm_EP5.2x5.2mm"
XH_FP = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
USB_FP = "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"


def _r(tag, value, desc, pkg="Resistor_SMD:R_0402_1005Metric"):
    return Part(name="R", ref_prefix="R", tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=pkg,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, pkg="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=pkg,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _xh(tag, desc):
    return Part(name="B4B-XH-A", ref_prefix="J", tag=tag, dest="NETLIST", tool="skidl",
                value="B4B-XH-A", description=desc, footprint=XH_FP,
                pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(XH_PINOUT)])


def _xcvr(tag, desc):
    """SN65HVD230DR, SOIC-8: 1 D, 2 GND, 3 VCC, 4 R, 5 Vref, 6 CANL, 7 CANH, 8 Rs."""
    return Part(name="SN65HVD230DR", ref_prefix="U", tag=tag, dest="NETLIST", tool="skidl",
                value="SN65HVD230DR", description=desc,
                footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                pins=[Pin(num=1, name="D", func=I), Pin(num=2, name="GND", func=PWR),
                      Pin(num=3, name="VCC", func=PWR), Pin(num=4, name="R", func=O),
                      Pin(num=5, name="Vref", func=O), Pin(num=6, name="CANL", func=P),
                      Pin(num=7, name="CANH", func=P), Pin(num=8, name="Rs", func=I)])


@subcircuit
def motor_ctrl():
    gnd, v24, v33 = Net("GND"), Net("+24V"), Net("+3V3")
    for n in (gnd, v24, v33):
        n.drive = Pin.drives.POWER

    # ── the two buses ────────────────────────────────────────────────────────
    # This board is the END of each bus, not a pass-through, so one 4-way each --
    # the 8-way in/out pattern belongs to the tees and lever boards in the middle.
    a_h, a_l = Net("CANA_H"), Net("CANA_L")
    b_h, b_l = Net("CANB_H"), Net("CANB_L")
    j1 = _xh("J1", "bus A out -- the ten motor tees")
    j2 = _xh("J2", "bus B out -- the eight lever/pedal boards")
    j3 = _xh("J3", "24 V in from the rail (2 contacts populated)")
    gnd += j1[1], j2[1], j3[1]
    v24 += j1[2], j2[2], j3[2]
    a_h += j1[3]; a_l += j1[4]
    b_h += j2[3]; b_l += j2[4]
    # J3's CAN cavities stay EMPTY: a 4-way shell for one crimp order across the
    # instrument, but wiring the pair to a power-only connector would hang an
    # unterminated stub off whichever bus the lead came from.

    # ── 24 V -> 3V3, LMR16006XDDCR (LCSC C87080), same part as the lever board ─
    # TI SNVSA24 section 6: 1 CB, 2 GND, 3 FB, 4 SHDN, 5 VIN, 6 SW. SHDN floats =
    # enabled. Asynchronous, so the catch diode is required, not optional.
    u4 = Part(name="LMR16006XDDCR", ref_prefix="U", tag="U4", dest="NETLIST", tool="skidl",
              value="LMR16006XDDCR", description="60 V 0.6 A buck, 24 V -> 3V3",
              footprint="Package_TO_SOT_SMD:SOT-23-6",
              pins=[Pin(num=1, name="CB", func=P), Pin(num=2, name="GND", func=PWR),
                    Pin(num=3, name="FB", func=I), Pin(num=4, name="SHDN", func=I),
                    Pin(num=5, name="VIN", func=PWR), Pin(num=6, name="SW", func=O)])
    sw, fb, cb = Net("SW"), Net("FB"), Net("CB")
    v24 += u4["VIN"]; gnd += u4["GND"]; sw += u4["SW"]; fb += u4["FB"]; cb += u4["CB"]
    l1 = Part(name="L", ref_prefix="L", tag="L1", dest="NETLIST", tool="skidl",
              value="47uH", description="buck inductor",
              footprint="Inductor_SMD:L_Taiyo-Yuden_NR-30xx",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw += l1[1]; v33 += l1[2]
    d1 = Part(name="B5819W", ref_prefix="D", tag="D1", dest="NETLIST", tool="skidl",
              value="B5819W", description="buck catch diode (Schottky, 40 V)",
              footprint="Diode_SMD:D_SOD-123",
              pins=[Pin(num=1, name="K", func=P), Pin(num=2, name="A", func=P)])
    sw += d1["K"]; gnd += d1["A"]
    cin = _c("C1", "4.7uF/50V", "buck input bulk -- 50 V part on a 24 V rail",
             "Capacitor_SMD:C_1206_3216Metric")
    v24 += cin[1]; gnd += cin[2]
    cout = _c("C2", "10uF/16V", "buck output bulk", "Capacitor_SMD:C_0805_2012Metric")
    v33 += cout[1]; gnd += cout[2]
    cboot = _c("C3", "100nF", "bootstrap, CB to SW")
    cb += cboot[1]; sw += cboot[2]
    r1 = _r("R1", "100k", "feedback divider, top")     # VOUT = 0.765 x (1 + R1/R2)
    r2 = _r("R2", "30k1", "feedback divider, bottom")
    v33 += r1[1]; fb += r1[2], r2[1]; gnd += r2[2]

    # ── the two transceivers ─────────────────────────────────────────────────
    a_tx, a_rx = Net("CAN1_TX"), Net("CAN1_RX")
    b_tx, b_rx = Net("CAN2_TX"), Net("CAN2_RX")
    u2 = _xcvr("U2", "bus A -- the motors")
    u3 = _xcvr("U3", "bus B -- the levers and pedals")
    for u, (tx, rx, ch, cl), rtag in ((u2, (a_tx, a_rx, a_h, a_l), "R3"),
                                      (u3, (b_tx, b_rx, b_h, b_l), "R4")):
        tx += u["D"]; rx += u["R"]
        gnd += u["GND"]; v33 += u["VCC"]
        ch += u["CANH"]; cl += u["CANL"]
        # Rs to GND through a resistor sets slope control. 10 k slews the edges,
        # which is right on a metre of cable in a box full of motors; neither bus
        # is anywhere near the part's 1 Mbps limit.
        rs = _r(rtag, "10k", "transceiver slope control")
        u["Rs"] += rs[1]; gnd += rs[2]

    # TERMINATION at THIS end of each bus. The far ends are the last motor tee
    # and the last lever board, which carry the same resistor behind the same
    # jumper -- populated everywhere, closed only at the two ends of each bus.
    for tag, (ch, cl), jtag in (("R5", (a_h, a_l), "JP1"), ("R6", (b_h, b_l), "JP2")):
        rt = _r(tag, "120R", "CAN termination, 1%", "Resistor_SMD:R_0603_1608Metric")
        jp = Part(name="SolderJumper_2_Open", ref_prefix="JP", tag=jtag, dest="NETLIST",
                  tool="skidl", value="TERM", description="close at the bus end",
                  footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm",
                  pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
        mid = Net("TERM_%s" % tag)
        ch += rt[1]; mid += rt[2], jp[1]; cl += jp[2]

    # BUS-PIN CLAMPS, two per pair. Separate BIDIRECTIONAL parts rather than a
    # 3-pin CAN array: a 2-pin bidirectional device is symmetric, so there is no
    # pinout to get wrong. The threat is the leg's TRRS -- a plug drags its bands
    # across every socket contact on insertion, and 24 V reaching a bus pin is
    # past this transceiver's -4..+16 V absolute maximum.
    for tag, net in (("D2", a_h), ("D3", a_l), ("D4", b_h), ("D5", b_l)):
        d = Part(name="TVS", ref_prefix="D", tag=tag, dest="NETLIST", tool="skidl",
                 value="SMF24CA", description="bidirectional TVS, bus pin to GND",
                 footprint="Diode_SMD:D_SOD-523",
                 pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
        net += d[1]; gnd += d[2]

    # ── MCU, CH32V307WCU6 QFN-68 (LCSC C5142795) ─────────────────────────────
    # Pins off WCH's CH32V303/305/307/317 datasheet V3.9, table 3-1, QFN68 column:
    #   69 VSS (exposed pad -- KiCad numbers that land 69)
    #   5 OSC_IN  6 OSC_OUT  7 NRST  12 VSSA  13 VDDA  63 BOOT0
    #   18/49 VSS   32/50/68 VDD   17/31/51/67 VIO   (this part has a SEPARATE
    #     I/O supply, which the CH32V203 on the lever board does not)
    #   64 PB8 = CAN1_RX_2 , 65 PB9 = CAN1_TX_2   <- bus A, THE REMAP
    #   35 PB12 = CAN2_RX  , 36 PB13 = CAN2_TX    <- bus B
    #   46 PA11 = OTG_FS_DM, 47 PA12 = OTG_FS_DP  <- the Pi link
    #   48 PA13 = SWDIO    , 52 PA14 = SWCLK
    dm, dp = Net("USB_DM"), Net("USB_DP")
    nrst, boot0 = Net("NRST"), Net("BOOT0")
    osc1, osc2 = Net("OSC_IN"), Net("OSC_OUT")
    swdio, swclk = Net("SWDIO"), Net("SWCLK")
    pins = [(69, "VSS_PAD", PWR), (5, "OSC_IN", I), (6, "OSC_OUT", O), (7, "NRST", I),
            (12, "VSSA", PWR), (13, "VDDA", PWR), (18, "VSS_1", PWR), (49, "VSS_2", PWR),
            (32, "VDD_1", PWR), (50, "VDD_2", PWR), (68, "VDD_3", PWR),
            (17, "VIO_4", PWR), (31, "VIO_1", PWR), (51, "VIO_2", PWR), (67, "VIO_3", PWR),
            (35, "PB12", I), (36, "PB13", O), (46, "PA11", P), (47, "PA12", P),
            (48, "PA13", P), (52, "PA14", P), (63, "BOOT0", I),
            (64, "PB8", I), (65, "PB9", O)]
    u1 = Part(name="CH32V307WCU6", ref_prefix="U", tag="U1", dest="NETLIST", tool="skidl",
              value="CH32V307WCU6", description="RISC-V MCU, 2x hardware CAN",
              footprint=MCU_FP,
              pins=[Pin(num=n, name=nm, func=f) for n, nm, f in pins])
    gnd += u1["VSS_PAD"], u1["VSS_1"], u1["VSS_2"], u1["VSSA"]
    v33 += (u1["VDD_1"], u1["VDD_2"], u1["VDD_3"], u1["VDDA"],
            u1["VIO_1"], u1["VIO_2"], u1["VIO_3"], u1["VIO_4"])
    nrst += u1["NRST"]; boot0 += u1["BOOT0"]
    osc1 += u1["OSC_IN"]; osc2 += u1["OSC_OUT"]
    a_rx += u1["PB8"]; a_tx += u1["PB9"]         # CAN1 REMAPPED -- see the header
    b_rx += u1["PB12"]; b_tx += u1["PB13"]
    dm += u1["PA11"]; dp += u1["PA12"]
    swdio += u1["PA13"]; swclk += u1["PA14"]

    y1 = Part(name="Crystal", ref_prefix="Y", tag="Y1", dest="NETLIST", tool="skidl",
              value="8MHz", description="HSE -- CAN bit timing wants a crystal",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=i + 1, func=P) for i in range(4)])
    osc1 += y1[1]; osc2 += y1[3]; gnd += y1[2], y1[4]
    for tag, net in (("C4", osc1), ("C5", osc2)):
        c = _c(tag, "12pF", "crystal load"); net += c[1]; gnd += c[2]
    c_n = _c("C6", "100nF", "NRST filter"); nrst += c_n[1]; gnd += c_n[2]
    r_b = _r("R7", "10k", "BOOT0 pull-down"); boot0 += r_b[1]; gnd += r_b[2]
    # Eight supply pins want their own decoupling; one bulk holds the rail up.
    for tag in ("C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14"):
        c = _c(tag, "100nF", "MCU supply decoupling"); v33 += c[1]; gnd += c[2]
    c_bulk = _c("C15", "10uF", "MCU bulk", "Capacitor_SMD:C_0805_2012Metric")
    v33 += c_bulk[1]; gnd += c_bulk[2]

    # ── USB-C to the Pi ──────────────────────────────────────────────────────
    # HRO TYPE-C-31-M-12 (LCSC C165948), the same receptacle the optical board
    # uses. Both halves of D+/D- are tied so the cable works either way up.
    # VBUS IS DELIBERATELY UNCONNECTED: the board runs off the 24 V rail, and
    # taking VBUS as well would leave the Pi's supply and the instrument's
    # fighting over which one holds the rail.
    usb = Part(name="USB_C_Receptacle", ref_prefix="J", tag="J4", dest="NETLIST",
               tool="skidl", value="TYPE-C-31-M-12", description="link to the Pi",
               footprint=USB_FP,
               pins=[Pin(num=n, func=P) for n in
                     ("A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12",
                      "B1", "B4", "B5", "B6", "B7", "B8", "B9", "B12", "SH")])
    gnd += usb["A1"], usb["A12"], usb["B1"], usb["B12"], usb["SH"]
    # VBUS's four pads are ONE pin on the real part, so they are commoned onto a
    # net that goes nowhere else. Left netless they read as four separate
    # unconnected pads and DRC reports them shorting each other -- which is the
    # tool being right about the model and wrong about the connector.
    # The net carries NO LOAD: this board runs off the 24 V rail, and drawing
    # VBUS as well would leave the Pi's supply and the instrument's arguing over
    # who holds the rail. It is a landing for a future VBUS-present sense.
    vbus = Net("VBUS_NC")
    vbus += usb["A4"], usb["B4"], usb["A9"], usb["B9"]
    dp += usb["A6"], usb["B6"]
    dm += usb["A7"], usb["B7"]
    for tag, pin in (("R8", "A5"), ("R9", "B5")):
        r = _r(tag, "5k1", "USB-C CC pull-down (upstream-facing port)")
        usb[pin] += r[1]; gnd += r[2]
    for tag, net in (("D6", dp), ("D7", dm)):
        d = Part(name="TVS", ref_prefix="D", tag=tag, dest="NETLIST", tool="skidl",
                 value="ESD", description="USB data-line ESD clamp",
                 footprint="Diode_SMD:D_SOD-523",
                 pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
        net += d[1]; gnd += d[2]


# ── the board ────────────────────────────────────────────────────────────────
# 40 x 35, sized by its own contents like the TRRS adapter and NOT by a housing:
# it replaces teensy_ifc in the electronics tray, whose 18 x 13 footprint was for
# two transceivers and three headers. The tray has the room -- deleting the Teensy
# and its audio shield freed far more than this needs -- but the tray must be
# rebuilt around this outline rather than the other way round.
BOARD_W, BOARD_L = 40.0, 35.0

BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 4,
    "thickness_mm": 1.6,
    # SKiDL numbers refs by INSTANTIATION order, not by tag: U1 is the buck,
    # U2/U3 the transceivers, U4 the MCU. Named as they come out.
    # Three 13.49 mm XH courtyards are 40.47 in a row and the board is 40, so the
    # power connector turns 90 onto the +X edge instead of joining the other two.
    "placements": {
        "J1": (-10.0, 14.0, 0.0),        # bus A out -- the ten motor tees
        "J2": (4.0, 14.0, 0.0),          # bus B out -- the eight lever boards
        "J3": (15.5, 3.0, 90.0),         # 24 V in, +X edge
        "J4": (0.0, -9.0, 0.0),          # USB-C to the Pi, -Y edge
        "U4": (-4.0, 2.0, 0.0),          # MCU
        "U2": (6.3, 6.5, 0.0),           # bus A transceiver
        "U3": (6.3, 0.0, 0.0),           # bus B transceiver
        # buck, hard -X: its switching node as far from the USB pair and both
        # CAN pairs as a 40 mm board allows
        "U1": (-16.0, 8.0, 0.0),
        "L1": (-16.0, 3.5, 0.0),
        "D1": (-16.0, 0.0, 0.0),
        "C1": (-16.5, -3.5, 0.0),
        "C2": (-16.0, -6.5, 0.0),
        "C3": (-12.5, -3.5, 0.0),
        "R1": (-12.5, -6.0, 0.0),
        "R2": (-12.5, -7.5, 0.0),
        # MCU furniture
        "C6": (-11.0, 2.0, 0.0),
        "R7": (-11.0, 0.5, 0.0),
        "C7": (-11.0, 5.0, 0.0),
        "C8": (-11.0, 6.5, 0.0),
        "C9": (-8.6, 8.5, 0.0),
        "C10": (-6.6, 8.5, 0.0),
        "C11": (-4.6, 8.5, 0.0),
        "C12": (-2.6, 8.5, 0.0),
        "C13": (-0.6, 8.5, 0.0),
        "C14": (1.4, 8.5, 0.0),
        "Y1": (-4.0, -5.0, 0.0),
        "C4": (-8.0, -5.0, 0.0),
        "C5": (0.0, -5.0, 0.0),
        "C15": (-8.0, -7.5, 0.0),
        # bus furniture, +X
        "R3": (11.2, 6.5, 0.0),
        "R4": (11.2, 0.0, 0.0),
        "R5": (16.5, 15.0, 0.0),
        "JP1": (16.5, -6.0, 0.0),
        "R6": (16.5, -9.5, 0.0),
        "JP2": (16.5, -13.0, 0.0),
        "D2": (12.3, 12.5, 0.0),
        "D3": (15.3, 12.5, 0.0),
        "D4": (10.0, -5.5, 0.0),
        "D5": (13.0, -5.5, 0.0),
        # USB furniture
        "R8": (-7.0, -12.5, 0.0),
        "R9": (-10.0, -12.5, 0.0),
        "D6": (7.0, -12.5, 0.0),
        "D7": (10.0, -12.5, 0.0),
    },
    "refs_on_fab": True,
    # THE GROUND PLANE is why this is four layers, same as the lever board: the
    # buck switches on a board carrying a 12 MHz USB pair and two CAN pairs.
    "zones": [("GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],
    "hold_edge": "+x",
    "no_mounting_holes": True,
    "single_sided": True,
    "qty_per_instrument": 1,
}


if __name__ == "__main__":
    motor_ctrl(tag="ctrl")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "motor_ctrl.net"))
    with open(os.path.join(OUT_DIR, "motor_ctrl.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"])))
