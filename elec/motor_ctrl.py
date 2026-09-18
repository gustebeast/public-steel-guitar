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

import netcheck                                     # noqa: E402

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
    # ⚠ J1 CARRIES BUS A'S WHOLE CURRENT ON ONE 3 A CONTACT, and BOM.md has the analysis
    # -- see "The bottleneck moves rather than disappears" in the 24 V bus section. In
    # short: J3 below was doubled because its ways were idle, and doing the same here is
    # not free because ways 3 and 4 carry CAN. The BOM's own conclusion is that the answer
    # is probably a firmware slew cap rather than a connector change, since Tr8x2 is
    # self-locking and the bus carries essentially nothing at rest.
    # This pointer exists because the netlist is where someone meets this connector, and
    # the analysis lives three files away.
    j1 = _xh("J1", "bus A out -- the ten motor tees")
    j2 = _xh("J2", "bus B out -- the eight lever/pedal boards")
    j3 = _xh("J3", "24 V in from the rail (2 contacts populated)")
    gnd += j1[1], j2[1], j3[1], j3[4]
    v24 += j1[2], j2[2], j3[2], j3[3]
    a_h += j1[3]; a_l += j1[4]
    b_h += j2[3]; b_l += j2[4]
    # ⚠ J3 NOW DOUBLES ITS CONTACTS, AND IT IS A RATING FIX RATHER THAN TIDINESS. This
    # is the sink end of the instrument's whole 24 V trunk. BOM.md sizes that bus at
    # under 5 A and XH is rated 3 A per contact, which is exactly why the SOURCE (the
    # output panel's J7) puts two contacts on each rail -- and this end was taking all
    # of it through one. A doubled source into a single-contact sink is not doubled.
    # The cavities were previously left empty on the reasoning that wiring the CAN pair
    # to a power-only connector would hang an unterminated stub; that reasoning was
    # right about CAN and does not apply to power, which is what they carry now. Pin
    # order is the instrument's standard: 1=GND 2=+24V 3=+24V 4=GND.
    #
    # ⚠ AND THE BOTTLENECK MOVES RATHER THAN DISAPPEARS -- FLAGGED, NOT FIXED. J1 and
    # J2 are the bus outputs, and on a four-wire CAN-plus-power bus (GND, +24V, H, L --
    # the user's colour scheme) the 24 V rides ONE conductor and one contact. Bus A
    # feeds ten SERVO42D drivers, so very nearly the whole <5 A passes through a single
    # 3 A contact at J1. Doubling here is free because J3's spare ways were idle; doing
    # the same at J1/J2 is not, because those ways carry CAN. Resolving it means a
    # wider shell, a separate power bus, or a measured slew budget showing the staggered
    # peak is genuinely under 3 A -- a motor-controller decision, recorded in BOM.md.

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
    #
    # ⚠ ALL TWENTY-FOUR CHECKED AGAINST THE QFN68 COLUMN, 2026-09-17, ZERO MISMATCHES --
    # numbers AND names, including every power pin, read with per-word coordinates so the
    # value taken is the one standing in the QFN68 column rather than whichever number
    # happens to be on the line. A wrong pin number here is invisible to everything
    # downstream: SKiDL connects a net to a pin NUMBER, layout places the pad it names,
    # and DRC agrees the copper matches the netlist. The board would simply not run.
    #
    # ⚠ AND THE DIRECTION OF THE CAN1 REMAP IS THE PART WORTH RE-READING. PB8 is RX and
    # PB9 is TX; an automated pass over the alternate-function table said PB8 = CAN1_TX_2,
    # which would have meant the bus-A transceiver wired backwards and a dead bus. It was
    # the extraction, not the datasheet: that table splits CAN1_RX_2 across two lines as
    # "CAN1_RX_" and "2", and the rows are close enough together that the tail of one
    # lands beside its neighbour. Read by eye off page 53, PB8 is RX. The remap exists at
    # all because CAN1's home pins are PA11/PA12, which USB is using.
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

    # ⚠ SWDIO AND SWCLK REACHED THE MCU AND STOPPED. Single-node nets: layout drops them
    # as unplaceable, so no copper is ever laid and DRC then compares a clean board
    # against a netlist that never asked for anything. Found 2026-09-17 by running the
    # orphan-pin check across the whole fleet after the optical board had the same fault.
    #
    # THIS BOARD IS NOT AS BAD AS THE LEVER BOARD, which had no way in at all. Here the
    # CH32V307's USB reaches a connector, so WCH's ROM bootloader is reachable in
    # principle -- but BOOT0 goes only to a pull-down and the MCU pin, so entering it
    # means tack-soldering onto a resistor pad, and SWD debugging would be unavailable
    # for the life of the board. Five pads cost nothing and remove both problems.
    for _ref, _net, _what in (("TP1", swdio, "SWDIO"), ("TP2", swclk, "SWCLK"),
                              ("TP3", nrst, "NRST"), ("TP4", gnd, "GND"),
                              ("TP5", v33, "target sense")):
        _tp = Part(name="TestPoint", ref_prefix="TP", ref=_ref, dest="NETLIST",
                   tool="skidl", value="SWD",
                   description="SWD pad -- %s; bare copper, no component" % _what,
                   footprint="TestPoint:TestPoint_Pad_D1.5mm",
                   pins=[Pin(num=1, func=P)])
        _net += _tp[1]

    r_b = _r("R7", "10k", "BOOT0 pull-down"); boot0 += r_b[1]; gnd += r_b[2]
    # Eight supply pins want their own decoupling; one bulk holds the rail up.
    for tag in ("C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14"):
        c = _c(tag, "100nF", "MCU supply decoupling"); v33 += c[1]; gnd += c[2]
    c_bulk = _c("C15", "10uF", "MCU bulk", "Capacitor_SMD:C_0805_2012Metric")
    v33 += c_bulk[1]; gnd += c_bulk[2]

    # ── USB-C to the Pi ──────────────────────────────────────────────────────
    # ⚠ USB_DP ROUTES HERE, AND AN EARLIER NOTE IN THIS PLACE SAID IT COULD NOT. Worth
    # keeping the correction, because the arithmetic was right and the conclusion drawn
    # from it was not. Escaping BETWEEN two adjacent USB-C pads does need 0.6 of via plus
    # 0.137 of clearance beside a 0.2 track -- 0.537 mm into a 0.500 mm pitch -- and that
    # remains impossible. But joining A6 to B6 does not have to pass between the pads: the
    # router took it AROUND THE ENDS. The pads span y 119.10..120.55 and the link runs
    # across at y = 120.85, clearing them by 0.305 mm, which is 0.18 mm edge to edge
    # against a 0.127 fab rule. Tight, legal, and DRC agrees at zero violations.
    #
    # ⚠ IT IS A SEARCH RESULT, NOT A CONSTRUCTION, WHICH IS THE PART TO WATCH. Nothing was
    # done to USB_DP: it appeared when +24V went from 0.25 to 0.5 mm and perturbed the
    # router's search, and a solution found that way can be lost the same way. The optical
    # board does not rely on luck here -- it declares the pair and _flip_merge builds the
    # A6/B6 link deliberately -- and if this link goes missing after some unrelated
    # change, that is the fix, not another routing run.
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
    # ── 24 V -> 5 V FOR THE Pi, AND THE CROWBAR THAT MATTERS MORE ────────────
    # THE POWER BOARD IS GONE AND THIS IS IT (user, 2026-09-15). It was its own
    # PCB in the tray; merging it here deletes a board, a connector and a cable --
    # but the real reason is that it deletes a JUNCTION. The 24 V trunk had to
    # feed both boards at the keyhead and the power board had only a 4-way INLET,
    # so that branch was a SPLICE, the only one in the instrument without a board
    # behind it. One board at the end of the chain needs no branch at all.
    #
    # THE MOTOR CURRENT NEVER COMES THROUGH HERE. The chain runs output panel ->
    # tees -> keyhead and every motor taps at its own tee, so what reaches this
    # board is its own draw plus the Pi's 5 V worth -- about 0.7 A at 24 V.
    #
    # ⚠ THE CROWBAR IS THE POINT, NOT THE BUCK. The Pi is fed through its GPIO
    # header, and on a Pi 4B the USB-C VBUS pin and the GPIO 5 V pins are the SAME
    # NODE with no polyfuse between them -- so that path skips every input
    # protection the Pi has. If U5 ever fails SHORT, 24 V lands on the 5 V rail and
    # takes the Pi, the OLED and the joystick with it. D9 conducts, F2 opens, and
    # the damage stops at a $0.30 part.
    v5, v5_raw = Net("+5V"), Net("+5V_RAW")
    # F1 fuses ONLY the buck's feed. The bus connectors keep their unfused 24 V --
    # fusing the trunk here would put this board in series with every motor.
    v24_buck = Net("+24V_BUCK")
    f1 = Part(name="Fuse", ref_prefix="F", tag="F1", dest="NETLIST", tool="skidl",
              value="1A", description="24 V fuse for the buck -- a shorted U5 must "
              "not feed the fault back out into the trunk",
              footprint="Fuse:Fuse_1206_3216Metric",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v24 += f1[1]
    v24_buck += f1[2]
    sw5, boot5, vcc5, fb5, en5 = (Net("SW5"), Net("BOOT5"), Net("VCC5"),
                                  Net("FB5"), Net("EN5"))
    for n in (v5, v5_raw):
        n.drive = Pin.drives.POWER
    # LMR33630: 3.8-36 V in, 3 A, SYNCHRONOUS (no catch diode), HSOIC-8 with a
    # thermal pad. 36 V of absolute maximum against a 24 V rail shared with ten
    # stepper drivers is the headroom that matters; the 24 V-max parts in this
    # class have none at all.
    u5 = Part(name="LMR33630ADDAR", ref_prefix="U", tag="U5", dest="NETLIST",
              tool="skidl", value="LMR33630ADDAR",
              description="36 V 3 A synchronous buck, 24 V -> 5 V for the Pi",
              footprint="Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm",
              pins=[Pin(num=1, name="VIN", func=PWR), Pin(num=2, name="EN", func=P),
                    Pin(num=3, name="NC", func=P), Pin(num=4, name="FB", func=P),
                    Pin(num=5, name="GND", func=PWR), Pin(num=6, name="SW", func=P),
                    Pin(num=7, name="BOOT", func=P), Pin(num=8, name="VCC", func=P),
                    Pin(num=9, name="EP", func=PWR)])
    v24_buck += u5[1]
    en5 += u5[2]
    fb5 += u5[4]
    # The exposed pad is the ground connection AND the only heat path off the die.
    gnd += u5[5], u5[9]
    sw5 += u5[6]
    boot5 += u5[7]
    vcc5 += u5[8]
    l2 = Part(name="L", ref_prefix="L", tag="L2", dest="NETLIST", tool="skidl",
              value="6.8uH", description="5 V buck output inductor, shielded 6x6",
              footprint="Inductor_SMD:L_Bourns-SRN6028",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw5 += l2[1]
    v5_raw += l2[2]
    # 1206 for the DC-BIAS derating, not merely the voltage rating: an 0805 50 V
    # part loses most of its capacitance at 24 V bias.
    for tag, val in (("C16", "10uF/50V"), ("C17", "10uF/50V")):
        c = _c(tag, val, "5 V buck input bulk", "Capacitor_SMD:C_1206_3216Metric")
        v24_buck += c[1]; gnd += c[2]
    c18 = _c("C18", "100nF", "5 V buck input HF bypass -- nearest VIN/GND")
    v24_buck += c18[1]; gnd += c18[2]
    c19 = _c("C19", "1uF", "5 V buck VCC bypass")
    vcc5 += c19[1]; gnd += c19[2]
    c20 = _c("C20", "100nF", "5 V buck bootstrap -- BOOT to SW")
    boot5 += c20[1]; sw5 += c20[2]
    for tag in ("C21", "C22"):
        c = _c(tag, "22uF/16V", "5 V output bulk", "Capacitor_SMD:C_0805_2012Metric")
        v5_raw += c[1]; gnd += c[2]
    # Feedback from the RAW node, BEFORE the fuse: regulating after F2 would put
    # the fuse's resistance inside the loop and let a warm fuse move the rail.
    r10 = _r("R10", "100k", "5 V feedback divider, top")
    # 24k9: VREF is 1.0 V (LMR33630 datasheet SNVSAN3), so RFBB = RFBT / (VOUT/VREF - 1)
    # = 100k / 4 = 25k, and TI's own 5 V example in that datasheet uses 100k / 24.9k.
    r11 = _r("R11", "24k9 1%", "5 V feedback divider, bottom -- 5.02 V with R10")
    v5_raw += r10[1]; fb5 += r10[2], r11[1]; gnd += r11[2]
    # EN divider: hold the converter off until the 24 V rail is up, so it does not
    # try to start into a sagging supply and chatter.
    # The EN pin has a PRECISION threshold -- 1.231 V typ, 1.2 to 1.26 over temperature
    # (LMR33630 datasheet, VEN-H) -- which is what makes an external divider a real UVLO
    # rather than a pull-up. For turn-on at 18 V the divider must be 18/1.231 = 14.6:1,
    # so 137k over 10k (147k total) trips at 18.1 V typical and 17.6 to 18.5 V across the
    # threshold's own spread. Enable leakage is 0.2 nA, so a 147k divider is not loaded.
    r12 = _r("R12", "137k 1%", "5 V EN/UVLO divider, top -- turn-on at 18.1 V")
    r13 = _r("R13", "10k 1%", "5 V EN/UVLO divider, bottom")
    v24 += r12[1]; en5 += r12[2], r13[1]; gnd += r13[2]

    f2 = Part(name="Fuse", ref_prefix="F", tag="F2", dest="NETLIST", tool="skidl",
              value="4A", description="5 V output fuse -- the element D9 blows when "
              "U5 fails short", footprint="Fuse:Fuse_1206_3216Metric",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v5_raw += f2[1]; v5 += f2[2]
    # 5 V out on TWO contacts and GND on two: XH is rated 3 A per contact and the
    # design draw IS 3 A, so a single contact would sit exactly on its rating.
    j5 = Part(name="B4B-XH-A", ref_prefix="J", tag="J5", dest="NETLIST", tool="skidl",
              value="B4B-XH-A", description="5 V to the Pi's GPIO pins 2/4 + 6/9",
              footprint=XH_FP,
              pins=[Pin(num=i + 1, name=n, func=P)
                    for i, n in enumerate(("GND", "+5V", "+5V", "GND"))])
    gnd += j5[1], j5[4]
    v5 += j5[2], j5[3]

    for tag, net in (("D6", dp), ("D7", dm)):
        d = Part(name="TVS", ref_prefix="D", tag=tag, dest="NETLIST", tool="skidl",
                 value="ESD", description="USB data-line ESD clamp",
                 footprint="Diode_SMD:D_SOD-523",
                 pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
        net += d[1]; gnd += d[2]

    # ⚠ THESE TWO ARE CREATED LAST ON PURPOSE. SKiDL numbers a ref_prefix group by
    # CREATION order and ignores the tag, so building them beside the buck -- where
    # they belong logically -- handed them D6/D7 and pushed the USB clamps to D8/D9.
    # The placement dict and the CAD table both key on the ref, so the names have to
    # follow the parts, not the narrative.
    d8 = Part(name="D_TVS", ref_prefix="D", tag="D8", dest="NETLIST", tool="skidl",
              value="SMAJ30A", description="24 V rail clamp -- the trunk is shared "
              "with ten stepper drivers", footprint="Diode_SMD:D_SMA",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v24 += d8[1]; gnd += d8[2]

    d9 = Part(name="D_TVS", ref_prefix="D", tag="D9", dest="NETLIST", tool="skidl",
              value="SMBJ5.0A", description="THE CROWBAR: clamps the 5 V rail and "
              "draws enough through F2 to open it", footprint="Diode_SMD:D_SMB",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v5 += d9[1]; gnd += d9[2]



# ── the board ────────────────────────────────────────────────────────────────
# 40 x 35, sized by its own contents like the TRRS adapter and NOT by a housing:
# it replaces teensy_ifc in the electronics tray, whose 18 x 13 footprint was for
# two transceivers and three headers. The tray has the room -- deleting the Teensy
# and its audio shield freed far more than this needs -- but the tray must be
# rebuilt around this outline rather than the other way round.
BOARD_W, BOARD_L = 46.0, 58.0

BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 4,
    "thickness_mm": 1.6,
    # SKiDL numbers refs by INSTANTIATION order, not by tag: U1 is the buck,
    # U2/U3 the transceivers, U4 the MCU. Named as they come out.
    # Three 13.49 mm XH courtyards are 40.47 in a row and the board is 40, so the
    # power connector turns 90 onto the +X edge instead of joining the other two.
    # THE BOARD GREW +Y, FROM 35 TO 58, AND THE ORIGINAL LAYOUT DID NOT MOVE.
    # Every pre-merge part keeps its position against the -Y edge (a flat -11.50 in
    # board-local Y, which is where the centre went), so the routing that was already
    # proven is disturbed as little as possible; the 5 V section lives entirely in
    # the strip the growth added.
    "placements": {
        "J1": (-10.00, 2.50, 0.0),
        "J2": (4.00, 2.50, 0.0),
        "J3": (15.50, -8.50, 90.0),
        # SWD pads -- nearest free 2.5 mm sites to U4; see the note in motor_ctrl()
        "TP1": (-10.10, -12.85, 0.0),
        "TP2": (2.40, -15.60, 0.0),
        "TP3": (-10.85, -3.10, 0.0),
        "TP4": (5.40, -15.60, 0.0),
        "TP5": (-6.85, -21.35, 0.0),
        "J4": (0.00, -20.50, 0.0),
        "U4": (-4.00, -9.50, 0.0),
        "U2": (6.30, -5.00, 0.0),
        "U3": (6.30, -11.50, 0.0),
        "U1": (-16.00, -3.50, 0.0),
        "L1": (-16.00, -8.00, 0.0),
        "D1": (-16.00, -11.50, 0.0),
        "C1": (-16.50, -15.00, 0.0),
        "C2": (-16.00, -18.00, 0.0),
        "C3": (-12.50, -15.00, 0.0),
        "R1": (-12.50, -17.50, 0.0),
        "R2": (-12.50, -19.00, 0.0),
        "C6": (-11.00, -9.50, 0.0),
        "R7": (-11.00, -11.00, 0.0),
        "C7": (-11.00, -6.50, 0.0),
        "C8": (-11.00, -5.00, 0.0),
        "C9": (-8.60, -3.00, 0.0),
        "C10": (-6.60, -3.00, 0.0),
        "C11": (-4.60, -3.00, 0.0),
        "C12": (-2.60, -3.00, 0.0),
        "C13": (-0.60, -3.00, 0.0),
        "C14": (1.40, -3.00, 0.0),
        "Y1": (-4.00, -16.50, 0.0),
        "C4": (-8.00, -16.50, 0.0),
        "C5": (0.00, -16.50, 0.0),
        "C15": (-8.00, -19.00, 0.0),
        "R3": (11.20, -5.00, 0.0),
        "R4": (11.20, -11.50, 0.0),
        "R5": (16.50, 3.50, 0.0),
        "JP1": (16.50, -17.50, 0.0),
        "R6": (16.50, -21.00, 0.0),
        "JP2": (16.50, -24.50, 0.0),
        "D2": (12.30, 1.00, 0.0),
        "D3": (15.30, 1.00, 0.0),
        "D4": (10.00, -17.00, 0.0),
        "D5": (13.00, -17.00, 0.0),
        "R8": (-7.00, -24.00, 0.0),
        "R9": (-10.00, -24.00, 0.0),
        "D6": (7.00, -24.00, 0.0),
        "D7": (10.00, -24.00, 0.0),
        "C19": (-17.00, 9.00, 0.0),
        "C20": (-13.00, 9.00, 0.0),
        "R10": (-9.00, 9.00, 0.0),
        "R11": (-5.00, 9.00, 0.0),
        "R12": (-1.00, 9.00, 0.0),
        "R13": (3.00, 9.00, 0.0),
        "F1": (-18.00, 13.00, 0.0),
        "C16": (-12.00, 13.00, 0.0),
        "C17": (-6.00, 13.00, 0.0),
        "C18": (-1.50, 13.00, 0.0),
        "D8": (5.00, 13.00, 0.0),
        "F2": (13.00, 13.00, 0.0),
        "U5": (-16.00, 18.50, 0.0),
        "L2": (-7.00, 18.50, 0.0),
        "D9": (2.00, 18.50, 0.0),
        "C21": (9.00, 18.50, 0.0),
        "C22": (13.50, 18.50, 0.0),
        "J5": (0.00, 26.00, 0.0),
    },
    "refs_on_fab": True,
    # THE GROUND PLANE is why this is four layers, same as the lever board: the
    # buck switches on a board carrying a 12 MHz USB pair and two CAN pairs.
    "zones": [("GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],
    # ⚠ +24V IS A PASS-THROUGH ON THIS BOARD, NOT A LOCAL SUPPLY. v24 reaches J1 and J2 as
    # well as the inlet J3, so the drivers' current crosses this PCB on its way to the
    # motors -- BOM.md's "very nearly the whole <5 A". At the board default of 0.25 mm
    # that is 0.88 A of 1 oz outer copper by IPC-2221 at a 10 C rise, about 5.7x short,
    # and it went unnoticed because until now no board could state a per-net width at all.
    # The audit that found it also cleared the other two: optical's inlet is ~324 mA
    # against 0.88 A, and lever_sensor's 0.15 mm pass-through is 0.60 A on the sensor bus.
    #
    # 0.5 mm takes it to 1.6 A. That is the ceiling for a blanket width here for the same
    # reason as on the panel -- this net lands on 0402 parts with 0.6 mm pads and
    # freerouting does not neck into a land -- so it is an improvement, not the answer.
    # The J3 -> J1/J2 path still wants deliberate copper; see the trunk note on
    # output_panel for why that is a pinout decision rather than a routing one.
    # GND needs nothing: it has plane copper on In1.Cu and a pour on B.Cu.
    "net_widths": {"+24V": 0.5},
    # ⚠ IN1 IS A PLANE, AND THE ROUTER HAS TO BE TOLD. A zone is just copper as far
    # as freerouting is concerned: pour GND on In1 and say nothing, and it will route
    # signals straight through the plane, which is exactly what it did here. The damage
    # is not cosmetic -- a signal in the reference plane splits the return path of every
    # trace that crosses it, and the nets carved through this one included the ones that
    # care most.
    #
    # This was found and fixed on the optical board and the fix never reached the other
    # three 4-layer boards, because it was made where the symptom appeared instead of
    # where the property belonged. A board that pours a plane declares it.
    "plane_layers": ("In1.Cu",),
    # ⚠ AND A PLANE NEEDS STITCHING TO IT. Declaring In1 a plane is only half the
    # job: it stops the router carrying ground THROUGH the plane, and then nothing
    # connects the ground pads TO it. Declared alone it stranded six GND pads on this
    # board -- the pour reaches them, but a pour is what routing can orphan, which is
    # the whole reason the plane is there. Every GND pad gets its own via down.
    "stitch_nets": ("GND",),
    "hold_edge": "+x",
    "no_mounting_holes": True,
    "single_sided": True,
    "qty_per_instrument": 1,
}


if __name__ == "__main__":
    motor_ctrl(tag="ctrl")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "motor_ctrl.net"))
    netcheck.grounds_meet(os.path.join(OUT_DIR, "motor_ctrl.net"))
    netcheck.no_orphan_pins(os.path.join(OUT_DIR, "motor_ctrl.net"))
    with open(os.path.join(OUT_DIR, "motor_ctrl.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"])))
