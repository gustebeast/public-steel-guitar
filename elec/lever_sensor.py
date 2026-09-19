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
import re  # noqa: E402

from skidl import ERC, Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

import netcheck                                     # noqa: E402

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

# ⚠ THE BOARD GREW FOR THE XH (user freed the plastic, 2026-09-19). J1 stands on end
# -- rotated 90, so its LENGTH runs along BOARD_L -- and the XH is 25.0 mm against PH's
# 19.9, which 21.4 could not hold. 28.0 in Y gives 25.0 plus 1.5 of margin at each end.
#
# AND 6 mm WIDER IN X, measured rather than assumed. The XH's courtyard is 12.5 x 23.4
# against the PH's much slimmer one, so at 28 wide it overlapped U2, U3, Y1 and TP4 --
# four courtyard violations, every one of them this single part. The circuit occupies
# local x -3..+11 and cannot shift right, because the MT6701 sits on the axle at
# x 11.0 and that position is not negotiable. So the room comes off the -X edge: 34
# wide puts J1 at x -10.75, spanning -17..-4.5, clear of U3's -1.6 by 2.9 mm.
#
# The extra area is also what the CAN_RX corner has been short of. That net has been
# unroutable since it was measured -- U3 pad 19 showed ZERO clear escape bearings, at
# any distance and in any direction -- and what it lacked was room.
BOARD_W, BOARD_L = 34.0, 28.0
CHIP_XY = (11.0, -0.3)        # the axle axis, in board-local mm (see board_json)

# Anything TALLER than 1.5 mm must keep its whole footprint outside the magnet
# cap's swept circle, because the board installs by dropping straight down past
# the cap. Only the connector, the transceiver and the inductor qualify; every
# passive here is under 1.5.
CAP_SWEEP_R = 5.66
TALL_PARTS = ("J1", "U2", "L1")


# ⚠ THE REF IS PINNED FROM THE TAG, AND IT HAS TO BE. Every call already passes a tag
# that spells the intended ref ("R5", "C11"), and until 2026-09-18 that was a COINCIDENCE:
# skidl numbered these parts in CREATION order and the order happened to agree. Adding one
# resistor in the MCU block broke it -- R5 vanished, the two I2C pull-ups became R7 and R9,
# and BOARD_NOTES["placements"] is keyed by ref, so three placed parts silently referred to
# refs that no longer existed while a new R9 had no placement and would have landed on the
# origin. The board still generated, ERC still passed, and the netlist was still valid.
# Passing ref= makes the tag authoritative, so where a part is CREATED stops mattering.
def _r(ref, tag, value, desc, pkg="Resistor_SMD:R_0402_1005Metric"):
    return Part(name="R", ref_prefix=ref, ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=pkg,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, pkg="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
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
    # ⚠ XH NOW, THE SAME PART THE POWER AND TEE BOARDS USE (user, 2026-09-19). PH was
    # chosen because an 8-way XH in SIDE-ENTRY SMT is not stocked -- see the header note
    # -- and that was the whole objection. S8B-XH-A is side-entry THT, 8-way, 25.0 mm,
    # LCSC C157914, and can_tee has been using it all along. What kept it off THIS board
    # was its THT posts sweeping the magnet cap on install, which is a PLASTIC problem,
    # and the plastic is being redesigned (user), so the constraint moved.
    #
    # What it buys: ONE connector family across both buses instead of two, the same
    # crimps and the same 8-way housing as the trunk, and 3 A contacts where PH gave 2.
    # What it costs: 5.1 mm more length (25.0 against 19.9), which is why the board grew
    # -- see BOARD_L.
    j1 = Part(name="S8B-XH-A", ref_prefix="J", ref="J1", tag="J1", dest="NETLIST",
              tool="skidl", value="S8B-XH-A",
              description="CAN trunk in (1-4) and out (5-8), LCSC C157914",
              footprint="Connector_JST:JST_XH_S8B-XH-A_1x08_P2.50mm_Horizontal",
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
    # ⚠ PIN 1 IS BOOT0/PB8, AND NOTHING ON THIS BOARD CONNECTS TO IT. This note used to
    # say pin 1 was unidentified and had to be resolved against the package drawing
    # before fabrication. A second source now answers it: KiCad's own MCU_WCH_RiscV
    # library gives CH32V203GxUx pin 1 as BOOT0/PB8, and its pin list agrees with this
    # board's other twelve declarations exactly. That is a library rather than WCH's
    # drawing, so it is corroboration and not proof -- but the question is no longer open,
    # it is answerable, and the answer has a consequence.
    #
    # ⚠ A FLOATING BOOT STRAP IS NOT A NEUTRAL STATE. BOOT0 selects where the part starts;
    # left unconnected it is whatever the die's internal pull does, which is a thing to
    # confirm rather than assume -- and if there is no internal pull-down, an assembled
    # board's boot mode is set by leakage. motor_ctrl ties its BOOT0 to a pull-down and a
    # test pad for exactly this reason. Resolve it before fabrication: either confirm the
    # internal pull from WCH's manual, or spend one 0402 on a pull-down.
    #
    # ⚠ AND THE BIGGER BOARD DID NOT FIX IT -- MEASURED AGAIN 2026-09-19, after the
    # board went to 34 x 28 for the XH. The open net swapped from CAN_RX to CAN_TX,
    # exactly the clean swap predicted below, and the shape is identical: the
    # TRANSCEIVER end has 14 of 24 clear bearings and 566 reachable via sites, the MCU
    # end (U3 pad 20) has ZERO and ZERO.
    #
    # That locates the constraint precisely, and it is not board area: the blockage is
    # inside the QFN's own escape fan, where the neighbouring pins' escapes take the
    # lane, so adding 6 mm of board in another direction cannot reach it. Two nets need
    # to leave adjacent pins of a 0.4 mm-pitch package through the same gap and only one
    # can. Re-assigning the pins is not available either -- see the remap note below;
    # this package brings out no PB9.
    #
    # What is left is moving the MCU or the transceiver relative to each other, which is
    # a placement question for the next revision rather than a routing one.

    # ⚠ CAN_RX MEASURED, 2026-09-18: THE MCU PIN CANNOT ESCAPE AT ALL. Probed at 24
    # directions and five distances from 0.3 to 1.5 mm, U3 pad 19 has ZERO clear exits --
    # not one bearing, not at any length. Reachable via sites: 885 from the transceiver's
    # pad, NONE from this one. No 2-segment or 3-segment F.Cu path exists between the two
    # pads, and no In2.Cu link between any of the 60 nearest reachable via sites.
    #
    # The blockers name the cause: CAN_TX's own track and pads take four of the eight
    # bearings, +3V3 one, GND pads the rest. CAN_TX and CAN_RX are adjacent MCU pins, and
    # whichever routes first takes the other's escape -- which is exactly what the note
    # below already predicted ("pre-lay CAN_RX and it connects, and CAN_TX becomes the
    # unconnected net instead, a clean swap"). The measurement corroborates it rather
    # than adding anything new.
    #
    # So this is NOT repairable the way optical's MID was. That pin had one clear bearing
    # and needed only a detour around two pads; this one has none, so there is no
    # geometry to find and no post-route track can help. The recorded conclusion stands
    # and is now measured rather than argued: only MOVING PARTS fixes this corner.
    # ⚠ AND THE SAME PIN LIST CLOSES OFF THE CAN REMAP. This package brings out PB8 (on
    # pin 1) but NO PB9 at all, so CAN1's PB8/PB9 remap -- the one motor_ctrl uses to get
    # CAN off PA11/PA12 -- does not exist here, and remap 3 is PD0/PD1, which the crystal
    # occupies. CAN_RX and CAN_TX are therefore stuck on PA11/PA12, immediately beside
    # SWDIO on PA13, which is the crowded corner described below. That corner cannot be
    # fixed by moving signals; only by moving parts.
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
                    Pin(num=28, name="PB7", func=P),
                    Pin(num=1, name="PB8", func=I)])   # BOOT0 -- see the note above
    gnd += u2["VSS"], u2["VSS_PAD"]
    v33 += u2["VDD"], u2["VDDA"]
    nrst += u2["NRST"]
    osc1 += u2["OSC_IN"]; osc2 += u2["OSC_OUT"]
    can_rx += u2["PA11"]; can_tx += u2["PA12"]
    swdio += u2["PA13"]; swclk += u2["PA14"]
    scl += u2["PB6"]; sda += u2["PB7"]
    # ⚠ BOOT0 RESOLVED: IT GETS THE 0402. The note above left two ways out -- confirm the
    # die's internal pull from WCH's manual, or spend a resistor -- and the resistor is
    # right even if the manual turns out to say there is a pull-down. An explicit strap is
    # immune to a datasheet revision and to a part substitution, motor_ctrl already does
    # exactly this on the same vendor's silicon (its R7, "BOOT0 pull-down"), and the cost
    # is one 0402 of a value this board already stocks -- no new SKU and no new feeder,
    # across all eleven boards. Confirming the internal pull would have cost more reading
    # than the part costs and still left the board leaning on an undocumented default.
    #
    # NO TEST PAD BESIDE IT, unlike motor_ctrl. A BOOT0 pad exists to force the ROM
    # bootloader, and that only helps if the bootloader can be REACHED -- this board has
    # no USB and brings out no USART, so the entry path does not exist. That absence is
    # the whole reason the SWD pads were added; SWD is the recovery route here.
    # ⚠ TIED HARD TO GND, NOT PULLED DOWN -- AND THE BOARD DECIDED THAT, NOT ME. The
    # 0402 pull-down went in first, matching motor_ctrl. It could not be placed: this
    # board is FULL (its own note: six free 2.0 mm sites, four already spent on the SWD
    # pads), and three sitings gave three different failures -- inside two courtyards
    # (3 unconnected, 3 violations), clearing pads but not courtyards (2 and 2), and
    # clearing both but displacing the router badly (4 and 1). The part was costing more
    # than it bought every time.
    #
    # A pull-down exists so BOOT0 can be forced HIGH externally to reach the ROM
    # bootloader. THIS BOARD HAS NO BOOTLOADER PATH -- no USB, no USART brought out --
    # which is the whole reason the SWD pads were added. So the resistor buys an entry
    # to a door that does not exist here, and a hard tie is the honest wiring of "this
    # part always boots from flash". motor_ctrl keeps ITS pull-down because it has USB
    # on a connector and the door is real.
    #
    # What a hard tie costs: forcing the bootloader later would mean cutting copper
    # rather than lifting a resistor. Against a board with no way to use the bootloader
    # and a working SWD route, that is not a cost worth one 0402 and three re-routes.
    gnd += u2["PB8"]


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

    # ⚠ WITHOUT THESE FOUR PADS THIS BOARD CANNOT BE PROGRAMMED AT ALL, and there are
    # eight to ten of them in the instrument. Audited 2026-09-17, after the same fault
    # was found on the optical board: SWDIO and SWCLK reached the MCU and stopped --
    # single-node nets, which layout drops as unplaceable and DRC cannot complain about.
    #
    # AND UNLIKE THE OTHER BOARDS THERE IS NO SECOND WAY IN. Listed from the netlist,
    # the only externally reachable nets were +24V, CAN_H, CAN_L and GND. The CH32V203
    # has no CAN bootloader -- WCH's ISP is USB or USART -- and this board brings out
    # neither, nor a BOOT0 pin. motor_ctrl and output_panel at least have USB on a
    # connector, so their ROM bootloader is reachable in principle; this one had nothing.
    # An assembled lever board would have been a brick, ten times over.
    #
    # Four pads, not five: the board is FULL. A scan of its courtyards found six free
    # 2.0 mm sites and no contiguous strip at all, so there is no room for the +3V3
    # target-sense pad the optical board carries. SWDIO, SWCLK and GND are clustered
    # within 2.5 mm for a probe; NRST is the outlier, which is the right one to strand
    # because it is only needed for connect-under-reset recovery.
    for _ref, _net, _what in (("TP1", swdio, "SWDIO"), ("TP2", swclk, "SWCLK"),
                              ("TP3", gnd, "GND"), ("TP4", nrst, "NRST")):
        _tp = Part(name="TestPoint", ref_prefix="TP", ref=_ref, dest="NETLIST",
                   tool="skidl", value="SWD",
                   description="SWD pad -- %s; bare copper, no component" % _what,
                   footprint="TestPoint:TestPoint_Pad_D1.0mm",
                   pins=[Pin(num=1, func=P)])
        _net += _tp[1]
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


def _sensor_qty():
    """One board per sensed player control: 6 knee levers + 5 pedals."""
    from src import dimensions as D
    return D.N_SENSED


_SENSOR_QTY = _sensor_qty()

BOARD_NOTES = {
    # ⚠ THE ONLY BOARD THERE IS MORE THAN ONE OF, AND IT USED TO DECLARE NO COUNT AT ALL.
    # Every other board states it -- optical 1, output_panel 1, motor_ctrl 1, can_tee one
    # per motor -- and this one, the multi-unit board, stated nothing. The count existed
    # only as the BOM's angle-sensor quantity, 11, with no record of what the 11 WERE, so
    # it could not be checked and could not be traced if it moved.
    #
    # It is 6 knee levers and 5 pedals (user, 2026-09-18): one sensed axis each, one
    # MT6701 each, one of these boards each. That is D.N_SENSED, and it reproduces the
    # BOM's 11 independently -- the first time those two numbers have had a common source
    # rather than agreeing by coincidence. Derived, not typed, because a typed board count
    # is how can_tee came to ship a 9 against a ten-motor instrument (see the note there).
    "qty_per_instrument": _SENSOR_QTY,
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 4,
    "thickness_mm": 1.6,
    # Board-local mm, origin at the board centre. The housing frame is x -25..+3
    # and z -14.2..+7.8, so the axle axis (housing 0,0) lands at CHIP_XY.
    "chip_on_axle_xy": CHIP_XY,
    "placements": {
        "U4": (11.00, -0.60, 0.0),
        # SWD pads -- the only four 2.0 mm sites this board has left; see the note in
        # lever_sensor() for why they are not in a neat row.
        "TP1": (4.75, 1.45, 0.0),      # SWDIO
        "TP2": (4.75, -0.95, 0.0),     # SWCLK
        "TP3": (7.15, 1.05, 0.0),      # GND  -- the three above are within 2.5 mm
        # ⚠ TP4 MOVED FOR THE XH. J1's courtyard now reaches x 96.75 and TP4 sat at
        # 96.30..98.39 -- the one part the bigger connector still clipped. TP4 is the
        # right one to move: it is NRST, described above as stranded and for
        # connect-under-reset recovery only, so it is the least coupled pad on the
        # board. Sited from pcbnew's own courtyards rather than estimated, 32241 free
        # positions, this the nearest to the circuit's centre.
        "TP4": (-1.30, 11.70, 0.0),   # moved off J1's courtyard; see below
        "J1": (-13.00, 0.00, 90.0),
        # ⚠ READ THROUGH pcbnew, AFTER FOUR PLACEMENTS BY ESTIMATE. The XH's pins
        # run DOWNWARD from pin 1 -- pad 1 at abs y 100.30, pad 8 at 82.80 -- so the
        # field is 17.5 mm long and its centre is 8.45 BELOW the origin, not on it.
        # Guessing that offset put pins off the bottom edge, then off the top, then
        # over TP4. Loading the board and printing the pad coordinates settles it in
        # one step: centred, the origin sits at local y 0.00. This
        # footprint is anchored at PIN 1, not at its body centre, so placing it at
        # local y 0 put the pin field at abs y 107.8..127.2 against a board ending at
        # 114 -- thirteen millimetres of connector hanging off the edge, which DRC
        # reported as courtyard overlaps with whatever it landed near rather than as
        # "off the board". Measured: the pads centred at abs y 117.5 and the board
        # centre is 100, so the origin moves +17.5 in board-local y to bring them onto
        # it. Two placements before this one were estimates and both were wrong.
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
        #
        # ⚠ AND THE REAL CONSTRAINT IS NOT "CAN_RX IS HARD", IT IS THREE SIGNALS AND TWO
        # WAYS OUT. Pre-lay CAN_RX and it connects -- and CAN_TX becomes the unconnected
        # net instead, a clean swap. Pre-lay BOTH and the second is reported not placeable
        # by the generator too. They leave adjacent pins, 19 and 20, on the same QFN edge.
        # Probing the escape ring outward from each: CAN_TX's own via sits 0.7 to 1.4 mm
        # off pin 19, squarely in CAN_RX's path, and SWDIO runs through that corridor at
        # every radius from 0.7 to 2.2 mm.
        #
        # SWDIO is there because of TP1. Before the SWD pads existed this net was
        # single-node, so layout dropped it and it laid no copper at all -- the board was
        # unprogrammable, which is why the pads went in. Giving SWDIO a destination gave
        # it a route, and that route goes through the one corner CAN_RX needed. Both are
        # required, so this is a placement question and not a routing one: move what the
        # transceiver or TP1 asks of that edge, or accept one CAN direction unrouted.
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
    # ⚠ THE LAYER LOCAL/RETRIED NETS MAY DIVE TO. In1.Cu is the ground plane and B.Cu
    # carries a second GND pour, so In2.Cu is the one inner layer with no pads on it.
    # Without this the generator has no way off the component layer at all, which is
    # exactly why the nets stranded at the QFN stayed stranded: its only escape was
    # gated on a differential-pair setting this board has no reason to declare.
    "local_inner": "In2.Cu",
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
    # ⚠ J1.5 REACHES THE PLANE THROUGH ITS OWN BARREL. The XH is a THROUGH-HOLE part,
    # so its ground pin is plated through every layer and is already connected to the
    # In1 plane by existing -- a stitching via beside it would add copper that joins
    # nothing new. It arrived as "no room for a stitching via beside J1.5" only because
    # the connector now sits against the -X edge with the mounting boss on one side and
    # the board edge on the other, and layout stops rather than silently leave a SURFACE
    # pad on the pour alone. That stop is right in general and does not apply to a pad
    # with its own hole. Same reasoning as output_panel's USB shield tabs.
    "stitch_exceptions": ("J1.5",),
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
    netcheck.grounds_meet(os.path.join(OUT_DIR, "lever_sensor.net"))
    netcheck.no_orphan_pins(os.path.join(OUT_DIR, "lever_sensor.net"))
    # ⚠ EVERY PART PLACED, EVERY PLACEMENT REAL. placements is keyed by REF, and a ref
    # is assigned by skidl rather than written here, so the two can disagree without
    # anything downstream objecting: a part with no entry lands on the ORIGIN, and an
    # entry naming a ref that no longer exists is simply ignored. Both happened on
    # 2026-09-18 from adding one resistor -- see the note on _r. ERC passed, the netlist
    # was valid, and three parts were in the wrong place.
    _refs = set(re.findall(r'\(comp\s*\(ref "([^"]+)"\)',
                           open(os.path.join(OUT_DIR, "lever_sensor.net"),
                                encoding="utf-8").read()))
    _placed = set(BOARD_NOTES["placements"])
    assert not (_refs - _placed), (
        "no placement for %s -- it would be laid on the board origin"
        % sorted(_refs - _placed))
    assert not (_placed - _refs), (
        "placements name %s, which no part has -- a ref moved under it"
        % sorted(_placed - _refs))
    with open(os.path.join(OUT_DIR, "lever_sensor.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements, chip on the axle at (%.1f, %.1f)"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]), *CHIP_XY))
