"""Lever / pedal sensor board — MT6701 angle sensor + CAN node, x8.

    py -3.12 elec/lever_sensor.py       # -> elec/out/lever_sensor.{net,board.json}

ONE BOARD FOR EVERY CONTROL: five knee levers and three foot pedals. It reads the
pivot angle off a diametric magnet on the axle and puts it on CAN bus B.

IT ABSORBS THE BUS-B TEE (user). Earlier rounds hung each lever off a trunk tee by
a single 4-way drop; the trunk now passes THROUGH the board, in on one half of an
8-way connector and out on the other. That deletes eight tee boards and eight
cradles. THE COST, stated once because it is real: a daisy chain means unplugging
one lever breaks the bus for everything downstream of it, which is exactly the
property the trunk-and-drop topology was chosen to have.

WHY AN 8-WAY PH AND NOT TWO 4-WAY XH. Two S4B-XH-SM4-TB need 31.0 mm of board
height stacked (the window is 26.10) or 27.2 of the 28 mm width laid in line,
which leaves nothing for the circuit. The 8-way XH fits on paper at 25.0 but LCSC
stocks only the 4-way. S8B-PH-SM4-TB is 19.9 long, 20,215 in stock, takes the
trunk's existing 26 AWG mid-range (30-24), and keeps a same-family fallback --
S8B-PH-K-S, the THT right-angle PH -- that would cost a footprint change and NO
harness change at all. PHD 2x4 is smaller still and was rejected on sourcing:
niche dual-row contacts against PH's commodity ones.

THE CHIP'S POSITION IS NOT NEGOTIABLE. MT6701 sensing centre = package geometric
centre, and it must sit on the axle axis. Everything else is placed around it.

EVERY PIN NUMBER BELOW IS OFF THE DATASHEET, not a library symbol -- see the
per-part notes. Getting one wrong is the failure this file exists to prevent.
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
I, O, PWR, PIN = Pin.types.INPUT, Pin.types.OUTPUT, Pin.types.PWRIN, Pin.types.PWRIN

# ── the board ────────────────────────────────────────────────────────────────
# 28 x 22. The 28 is the FOOT PEDAL's cap (it turns the board 90 deg). The 22 is
# new: 16 was derived from the old 15.0 connector, and the 19.9 PH needs 20.9
# with JLCPCB's 1.0 component-to-edge rule. The horizontal lever's Z window is
# 26.10, so 22 costs nothing -- and it takes coverage from ~62% to ~48%, which
# this board needs: it has never modelled a single passive.
# ⚠ FOOTPRINTS NOT YET VERIFIED AGAINST THE PACKAGE DRAWINGS. The PIN NUMBERS
# above are datasheet-confirmed; these two LAND PATTERNS are the nearest stock
# KiCad parts and carry two open questions each -- the MCU's pitch (0.4 vs 0.45
# on a 4x4 QFN28) and both parts' exposed-pad size. The MT6701's pin list runs
# 1..16 with no pin 0, so it may have NO thermal pad at all, in which case this
# footprint leaves unconnected copper under the die. Resolve both off the
# drawings before any board is ordered; nothing else in this file depends on it.
MCU_FP = "Package_DFN_QFN:QFN-28-1EP_4x4mm_P0.4mm_EP2.4x2.4mm"
SENSOR_FP = "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.45x1.45mm"

# 28 x 22. THE HEIGHT IS CAPPED BY THE FOOT PEDAL, not by the knee levers:
# its housing is clipped to the pedal bar's own width, so the board may not
# reach below z -10.95 from the axle, and the horizontal lever's ceiling is
# +11.60 -- 22.55 between them. 25 was drawn before that was checked and does
# not fit. foot_pedal.py asserts it; board_flip does NOT, because it polices
# the cradle's window and the pedal's budget is tighter than the window.
# (Earlier note, still true of the connector: J1's COURTYARD is 21.29 x 10.29, far bigger
# than the 19.9 body -- a side-entry connector reserves the plug's run-in too.
# At 22 the board was 60% covered and the parts could not be placed. The
# horizontal lever's window is 26.10, so 25 still clears the shell by 0.30 at
# the bottom and 0.80 at the top with the chip pinned to the axle.
BOARD_W, BOARD_L = 28.0, 21.4
CHIP_XY = (11.0, -0.3)        # the axle axis, in board-local mm (see board_json)

# Anything TALLER than 1.5 mm must keep its whole footprint outside the magnet
# cap's swept circle, because the board installs by dropping straight down past
# the cap. Only the connector, the transceiver and the inductor qualify; every
# passive here is under 1.5.
CAP_SWEEP_R = 5.66
TALL_PARTS = ("J1", "U2", "L1")


def _r(ref, tag, value, desc, pkg="Resistor_SMD:R_0402_1005Metric"):
    return Part(name="R", ref_prefix=ref, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=pkg,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, pkg="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=pkg,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


@subcircuit
def lever_sensor():
    gnd, v24, v33 = Net("GND"), Net("+24V"), Net("+3V3")
    can_h, can_l = Net("CAN_H"), Net("CAN_L")
    for n in (gnd, v24, v33, can_h, can_l):
        n.drive = Pin.drives.POWER

    # ── the trunk, in and out of one connector ───────────────────────────────
    # Pins 1-4 are the incoming cable and 5-8 the outgoing one, each in the SAME
    # order the motor tee uses (GND / +V / CAN_H / CAN_L) so one crimp order
    # serves every connector in the instrument. The two halves are the same four
    # nets -- a pass-through, not a switch.
    j1 = Part(name="S8B-PH-SM4-TB", ref_prefix="J", tag="J1", dest="NETLIST",
              tool="skidl", value="S8B-PH-SM4-TB",
              description="CAN trunk in (1-4) and out (5-8), LCSC C265121",
              footprint="Connector_JST:JST_PH_S8B-PH-SM4-TB_1x08-1MP_P2.00mm_Horizontal",
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(
                  ("GND_IN", "V24_IN", "CANH_IN", "CANL_IN",
                   "GND_OUT", "V24_OUT", "CANH_OUT", "CANL_OUT"))])
    gnd += j1[1], j1[5]
    v24 += j1[2], j1[6]
    can_h += j1[3], j1[7]
    can_l += j1[4], j1[8]

    # ── 24 V -> 3V3, LMR16006XDDCR (LCSC C87080) ─────────────────────────────
    # Pins off TI SNVSA24 section 6: 1 CB, 2 GND, 3 FB, 4 SHDN, 5 VIN, 6 SW.
    # SHDN is left FLOATING, which the datasheet defines as enabled (internal
    # pull-up current source) -- deliberate, not an omission.
    # ASYNCHRONOUS buck: the catch diode D1 is required, not optional.
    u1 = Part(name="LMR16006XDDCR", ref_prefix="U", tag="U1", dest="NETLIST",
              tool="skidl", value="LMR16006XDDCR",
              description="60 V 0.6 A buck, 24 V -> 3V3",
              footprint="Package_TO_SOT_SMD:SOT-23-6",
              pins=[Pin(num=1, name="CB", func=P), Pin(num=2, name="GND", func=PWR),
                    Pin(num=3, name="FB", func=I), Pin(num=4, name="SHDN", func=I),
                    Pin(num=5, name="VIN", func=PWR), Pin(num=6, name="SW", func=O)])
    sw, fb, cb = Net("SW"), Net("FB"), Net("CB")
    v24 += u1["VIN"]
    gnd += u1["GND"]
    sw += u1["SW"]
    fb += u1["FB"]
    cb += u1["CB"]

    l1 = Part(name="L", ref_prefix="L", tag="L1", dest="NETLIST", tool="skidl",
              value="47uH", description="buck inductor",
              footprint="Inductor_SMD:L_Taiyo-Yuden_NR-30xx",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw += l1[1]
    v33 += l1[2]

    d1 = Part(name="B5819W", ref_prefix="D", tag="D1", dest="NETLIST", tool="skidl",
              value="B5819W", description="buck catch diode (Schottky, 40 V)",
              footprint="Diode_SMD:D_SOD-123",
              pins=[Pin(num=1, name="K", func=P), Pin(num=2, name="A", func=P)])
    sw += d1["K"]
    gnd += d1["A"]

    cin = _c("C1", "4.7uF/50V", "buck input bulk -- 50 V part on a 24 V rail",
             "Capacitor_SMD:C_1206_3216Metric")
    v24 += cin[1]; gnd += cin[2]
    cout = _c("C2", "10uF/16V", "buck output bulk", "Capacitor_SMD:C_0805_2012Metric")
    v33 += cout[1]; gnd += cout[2]
    cboot = _c("C3", "100nF", "bootstrap, CB to SW")
    cb += cboot[1]; sw += cboot[2]
    # VOUT = VFB x (1 + R1/R2); VFB = 0.765 V typ -> R1/R2 = 3.31 for 3V3
    rfb1 = _r("R", "R1", "100k", "feedback divider, top")
    rfb2 = _r("R", "R2", "30k1", "feedback divider, bottom")
    v33 += rfb1[1]; fb += rfb1[2], rfb2[1]; gnd += rfb2[2]

    # ── CAN transceiver, SN65HVD230DR (LCSC C12084) ──────────────────────────
    # SOIC-8: 1 D, 2 GND, 3 VCC, 4 R, 5 Vref, 6 CANL, 7 CANH, 8 Rs.
    can_tx, can_rx = Net("CAN_TX"), Net("CAN_RX")
    u3 = Part(name="SN65HVD230DR", ref_prefix="U", tag="U3", dest="NETLIST",
              tool="skidl", value="SN65HVD230DR", description="3.3 V CAN transceiver",
              footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
              pins=[Pin(num=1, name="D", func=I), Pin(num=2, name="GND", func=PWR),
                    Pin(num=3, name="VCC", func=PWR), Pin(num=4, name="R", func=O),
                    Pin(num=5, name="Vref", func=O), Pin(num=6, name="CANL", func=P),
                    Pin(num=7, name="CANH", func=P), Pin(num=8, name="Rs", func=I)])
    can_tx += u3["D"]; can_rx += u3["R"]
    gnd += u3["GND"]; v33 += u3["VCC"]
    can_l += u3["CANL"]; can_h += u3["CANH"]
    # Rs to GND through a resistor sets slope control; 0 R would be full speed.
    # 10 k slews the edges, which is the right default on a metre of cable in a
    # box full of motors -- bus B runs at 500 k-1 M, nowhere near the limit.
    rs = _r("R", "R3", "10k", "transceiver slope control")
    u3["Rs"] += rs[1]; gnd += rs[2]
    c_xcvr = _c("C4", "100nF", "transceiver decoupling")
    v33 += c_xcvr[1]; gnd += c_xcvr[2]

    # BUS-B FAR-END TERMINATION, behind a solder jumper exactly as the motor tee
    # does it: populated on all eight, closed on the ONE board that ends the bus.
    # 0402, NOT the 0603 this was. When the board came down to 21.4 (the foot pedal
    # housing's floor, see knee_lever.PCB_WZ) R4 ended up in a 1.48 mm gap between JP1
    # and C10 needing 1.55, and every column on this board is full -- there is nowhere
    # else for it. 0402 fits with 0.45 to spare and is not a compromise: a single 120R
    # across the pair sees ~17 mA, i.e. 0.034 W against 0402's 0.063 W rating. It also
    # makes this board ALL-0402 for resistors, dropping a feeder.
    rt = _r("R", "R4", "120R", "CAN termination, closed only on the last board",
            "Resistor_SMD:R_0402_1005Metric")
    jp1 = Part(name="SolderJumper_2_Open", ref_prefix="JP", tag="JP1", dest="NETLIST",
               tool="skidl", value="TERM", description="close on the bus's LAST board only",
               footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm",
               pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    term = Net("TERM_MID")
    can_h += rt[1]; term += rt[2], jp1[1]; can_l += jp1[2]

    # BUS-PIN CLAMPS. Two SEPARATE bidirectional TVS rather than one three-pin
    # CAN array, on purpose: a 2-pin bidirectional part is symmetric, so there is
    # no pinout to get wrong, and the 3-pin arrays' pin order is the one number I
    # could not verify. The threat is real -- a TRRS plug sweeps every contact on
    # insertion, so the leg's 24 V momentarily reaches CAN_H and CAN_L, and this
    # transceiver's bus pins are absolute-max -4..+16 V.
    for tag, net in (("D2", can_h), ("D3", can_l)):
        d = Part(name="TVS", ref_prefix="D", tag=tag, dest="NETLIST", tool="skidl",
                 value="PESD1CAN-like", description="bidirectional TVS, bus pin to GND",
                 # SOD-523, not SOD-123: these are signal-line ESD clamps, not power
                 # TVS, and the big package cost 18 mm2 the board no longer has once
                 # the foot pedal's Y budget capped its height at 22.55.
                 footprint="Diode_SMD:D_SOD-523",
                 pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
        net += d[1]; gnd += d[2]

    # ── MCU, CH32V203G6U6 QFN-28 (LCSC C5142280) ─────────────────────────────
    # Pins off WCH CH32V203 datasheet V2.8 table 3-1-3, the QFN28 (G6) column:
    #   0 VSS (exposed pad -- KiCad numbers that land 29, which is what is used
#     below)             2 OSC_IN  3 OSC_OUT  4 NRST  5 VDDA  16 VSS  17 VDD
    #   19 PA11 = CAN1_RX    20 PA12 = CAN1_TX
    #   21 PA13 = SWDIO      22 PA14 = SWCLK
    #   27 PB6  = I2C1_SCL   28 PB7  = I2C1_SDA
    # ⚠ PIN 1 IS NOT IDENTIFIED. The datasheet's G6 table skips it in extraction,
    # and BOOT0 does not appear in that column at all (it is pin 4 on the QSOP28
    # G8 part, where NRST is elsewhere). Nothing here connects to pin 1, and the
    # boot strap must be resolved against the package drawing before fabrication.
    sda, scl = Net("SDA"), Net("SCL")
    swdio, swclk, nrst = Net("SWDIO"), Net("SWCLK"), Net("NRST")
    osc1, osc2 = Net("OSC_IN"), Net("OSC_OUT")
    u2 = Part(name="CH32V203G6U6", ref_prefix="U", tag="U2", dest="NETLIST",
              tool="skidl", value="CH32V203G6U6",
              description="RISC-V MCU, 2x CAN; same toolchain as the controller board",
              footprint=MCU_FP,
              pins=[Pin(num=29, name="VSS_PAD", func=PWR), Pin(num=2, name="OSC_IN", func=I),
                    Pin(num=3, name="OSC_OUT", func=O), Pin(num=4, name="NRST", func=I),
                    Pin(num=5, name="VDDA", func=PWR), Pin(num=16, name="VSS", func=PWR),
                    Pin(num=17, name="VDD", func=PWR), Pin(num=19, name="PA11", func=I),
                    Pin(num=20, name="PA12", func=O), Pin(num=21, name="PA13", func=P),
                    Pin(num=22, name="PA14", func=P), Pin(num=27, name="PB6", func=P),
                    Pin(num=28, name="PB7", func=P)])
    gnd += u2["VSS"], u2["VSS_PAD"]
    v33 += u2["VDD"], u2["VDDA"]
    nrst += u2["NRST"]
    osc1 += u2["OSC_IN"]; osc2 += u2["OSC_OUT"]
    can_rx += u2["PA11"]; can_tx += u2["PA12"]
    swdio += u2["PA13"]; swclk += u2["PA14"]
    scl += u2["PB6"]; sda += u2["PB7"]

    y1 = Part(name="Crystal", ref_prefix="Y", tag="Y1", dest="NETLIST", tool="skidl",
              value="8MHz", description="HSE -- CAN bit timing wants a crystal, not the RC",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P),
                    Pin(num=3, func=P), Pin(num=4, func=P)])
    osc1 += y1[1]; osc2 += y1[3]
    gnd += y1[2], y1[4]
    for tag, net in (("C5", osc1), ("C6", osc2)):
        c = _c(tag, "12pF", "crystal load")
        net += c[1]; gnd += c[2]
    c_nrst = _c("C7", "100nF", "NRST filter")
    nrst += c_nrst[1]; gnd += c_nrst[2]
    for tag in ("C8", "C9"):
        c = _c(tag, "100nF", "MCU decoupling")
        v33 += c[1]; gnd += c[2]
    c_bulk = _c("C10", "4.7uF", "MCU bulk", "Capacitor_SMD:C_0805_2012Metric")
    v33 += c_bulk[1]; gnd += c_bulk[2]

    # ── the sensor, MT6701QT-STD QFN-16 (LCSC C2913974) ──────────────────────
    # Pins off MagnTek MT6701 datasheet section 1.2 (QFN-16 pin list):
    #   5 PUSH  6 A(SDA)  7 B(SCL)  8 Z(CSN)  9 W  11 U  12 V
    #   13 VDD  14 MODE  15 OUT  16 GND ; 1-4 and 10 are NC
    # MODE selects ABZ against I2C/SSI. It is strapped through a resistor rather
    # than tied, because which level selects which is a datasheet detail to
    # confirm on the first board -- a resistor is a jumper you can move.
    u4 = Part(name="MT6701QT-STD", ref_prefix="U", tag="U4", dest="NETLIST",
              tool="skidl", value="MT6701QT-STD",
              description="14-bit Hall angle encoder, sensing centre = package centre",
              footprint=SENSOR_FP,
              pins=[Pin(num=5, name="PUSH", func=O), Pin(num=6, name="A_SDA", func=P),
                    Pin(num=7, name="B_SCL", func=P), Pin(num=8, name="Z_CSN", func=P),
                    Pin(num=13, name="VDD", func=PWR), Pin(num=14, name="MODE", func=I),
                    Pin(num=15, name="OUT", func=O), Pin(num=16, name="GND", func=PWR),
                    Pin(num=17, name="EP", func=PWR)])
    v33 += u4["VDD"]; gnd += u4["GND"], u4["EP"]
    sda += u4["A_SDA"]; scl += u4["B_SCL"]
    r_mode = _r("R", "R5", "0R", "MODE strap -- confirm polarity on the first board")
    u4["MODE"] += r_mode[1]; gnd += r_mode[2]
    c_sens = _c("C11", "100nF", "sensor decoupling")
    v33 += c_sens[1]; gnd += c_sens[2]
    for tag, net in (("R6", sda), ("R7", scl)):
        r = _r("R", tag, "4k7", "I2C pull-up")
        v33 += r[1]; net += r[2]


BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 4,
    "thickness_mm": 1.6,
    # Board-local mm, origin at the board centre. The housing frame is x -25..+3
    # and z -14.2..+7.8, so the axle axis (housing 0,0) lands at CHIP_XY.
    "chip_on_axle_xy": CHIP_XY,
    "placements": {
        "U4": (11.00, -0.60, 0.0),
        "J1": (-10.55, 0.00, 90.0),
        "U1": (-1.10, 8.75, 0.0),
        "L1": (3.00, 8.70, 0.0),
        "D1": (7.60, 9.25, 0.0),
        "R1": (11.10, 9.25, 0.0),
        "C1": (-0.90, 5.60, 0.0),
        "C2": (3.40, 5.70, 0.0),
        "C3": (6.50, 5.70, 0.0),
        "R2": (8.60, 5.70, 0.0),
        "R7": (10.90, 5.70, 0.0),
        # ⚠ 0, NOT 90, AND IT IS A ROUTING DECISION. At 90 the CAN pair sat on the MCU's
        # NORTH edge while the transceiver it talks to is south of it, and J1 walls off
        # the whole west side -- so both signals had to travel around the package to get
        # anywhere. CAN_TX made it and CAN_RX did not, through three rounds of trying to
        # fix it as a routing problem.
        # Measured across all four orientations by total pin-to-net distance: 58.7 mm at
        # 0 against 66.6 at 90. A square QFN's envelope does not change when it turns, so
        # this costs nothing but the decision to look.
        "U3": (1.00, 1.55, 0.0),
        "C9": (5.50, 3.20, 0.0),
        "C8": (7.50, 3.20, 0.0),
        "R5": (11.00, 2.90, 0.0),
        "C11": (7.00, -0.60, 0.0),
        "C10": (9.50, -3.90, 0.0),
        "Y1": (-0.90, -3.00, 0.0),
        "C5": (3.60, -2.50, 0.0),
        "C6": (3.60, -4.30, 0.0),
        "C7": (6.00, -2.50, 0.0),
        "R6": (6.00, -4.50, 0.0),
        "U2": (0.50, -7.60, 0.0),
        "C4": (6.00, -6.30, 0.0),
        "R3": (6.00, -7.80, 0.0),
        "R4": (9.50, -5.75, 0.0),
        "JP1": (9.50, -7.70, 0.0),
        "D2": (5.80, -9.80, 0.0),
        "D3": (8.60, -9.80, 0.0),
    },
    "cap_keepout": {"xy": list(CHIP_XY), "r": CAP_SWEEP_R, "tall": list(TALL_PARTS)},
    # THE GROUND PLANE IS WHY THIS BOARD IS FOUR LAYERS. BOM.md says so outright:
    # "4 LAYERS, and not for density: the buck switches ~10 mm from a magnetic
    # angle sensor whose entire job is reading a small field. A solid ground
    # plane between them is worth more than the couple of dollars it costs."
    # Without this pour the stackup buys nothing.
    "zones": [("GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],
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
    # ⚠ 0.15 mm TRACK, because the tightest part on this board is a 0.4 mm pitch QFN-28
    # and the default 0.25 does not leave its escape fan room to turn. Four nets -- NRST,
    # OSC_OUT, CAN_RX and a +3V3 pin -- were stranded at that package and neither the
    # router nor the generator could get them out.
    # 0.15 on 1 oz copper carries ~0.5 A at a 10 C rise, against this board's largest
    # load of roughly 100 mA; the constraint here is geometry, not current.
    "track_mm": 0.15,
    # ⚠ AND A PLANE NEEDS STITCHING TO IT. Declaring In1 a plane is only half the
    # job: it stops the router carrying ground THROUGH the plane, and then nothing
    # connects the ground pads TO it. Declared alone it stranded six GND pads on this
    # board -- the pour reaches them, but a pour is what routing can orphan, which is
    # the whole reason the plane is there. Every GND pad gets its own via down.
    "stitch_nets": ("GND",),
    # ⚠ NO local_nets ON THIS BOARD, AND THE MEASUREMENT SAYS SO. Pre-laying every
    # short net here took it from 4 unconnected to 7. The generator is not better than
    # the router in general -- it wins on the optical board because twenty identical
    # feedback clusters in a strip holding 107 parts is a pattern, and a pattern is a
    # thing a generator does better than a search. This board is 28 x 21 with 29 parts
    # and the router has slack; deterministic copper laid first only takes that slack
    # away, and the search it constrains could have done better.
    #
    # Worth keeping the number rather than the conclusion: if this board grows a
    # component row, re-measure rather than assuming either way.
    "refs_on_fab": True,
    "hold_edge": None,          # NO screw: the grooves hold five faces and the
                                # instrument's underside closes over the sixth
    "no_mounting_holes": True,
    "single_sided": True,       # every part on the magnet-facing face
    # MECHANICAL keepouts, mirrored from knee_lever.py so this side catches them
    # too. The cradle's grooves take 1.85 off each X edge (the sensor is the one
    # part allowed in, its position being fixed on the axle), and the connector's
    # mated plug forbids a strip -- board-local, converted from the chip frame.
    "groove_keepout_x": 1.85,
    "groove_exempt": ["U4", "J1"],
    "conn_keepout": {"box": [-14.0, -3.25, -11.0, 11.0], "exempt": ["J1", "U4"]},
}


if __name__ == "__main__":
    lever_sensor(tag="lever")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "lever_sensor.net"))
    with open(os.path.join(OUT_DIR, "lever_sensor.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements, chip on the axle at (%.1f, %.1f)"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]), *CHIP_XY))
