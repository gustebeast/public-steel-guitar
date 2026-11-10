"""Lever / pedal sensor board — MA730 angle sensor + CAN node, x8.

    py -3.12 elec/lever_sensor.py       # -> elec/out/lever_sensor.{net,board.json}

ONE BOARD FOR EVERY CONTROL: five knee levers and three foot pedals. It reads the
pivot angle off a diametric magnet on the axle and puts it on CAN bus B.

IT ABSORBS THE BUS-B TEE (user). Earlier rounds hung each lever off a trunk tee by
a single 4-way drop; the trunk now passes THROUGH the board, in on J1 and out on J2.
That deletes eight tee boards and eight cradles. THE COST, stated once because it is
real: a daisy chain means unplugging one lever breaks the bus for everything
downstream of it, which is exactly the property the trunk-and-drop topology was
chosen to have.

TWO 4-WAY PH, NOT ONE 8-WAY (user, 2026-10-19). With in and out in one PHR-8 housing,
every hop's cable was crimped into the next board's housing alongside the cable after
it, so moving or pulling one lever meant re-making the harness either side of it. Two
4-ways make each hop its own straight PHR-4 jumper (way n to way n, both connectors in
harness.PH_PINOUT order): a lever comes out by its two plugs, and a hop that changes
length is one new cable. THROUGH-HOLE, S4B-PH-K-S (LCSC C157926, ~40k stock), because
it is what fits: two SMT S4B-PH-SM4-TB stand 23.8 end to end against the 19.9 the
board's height leaves (the foot pedal caps it), and two S4B-PH-K-S stand 19.8 -- the
length of the S8B-PH-SM4-TB they replace, so the outline and every housing are
unchanged. The pins come through to the back face; the cradle has no back wall there.
(History: two S4B-XH-SM4-TB needed 31.0 of height; the 8-way XH was not stocked; PHD
2x4 was rejected on sourcing.)

THE CHIP'S POSITION IS NOT NEGOTIABLE. MA730 sensing point = package geometric
centre (datasheet rev 1.1 p.10 fig. 3: 1.50 +-0.05 in from the edge of the 3.00
package, 0.45 below its top), and it must sit on the axle axis. Everything else is
placed around it.

THE SENSOR IS AN MA730GQ-Z SINCE 2026-11-03 (user, via the lead): the MT6701 went to
0 stock at LCSC under both codes and MagnTek has no DigiKey listing. Same QFN-16 3x3
outline, same 14 bits, but NOT pin-compatible and read over SPI, not I2C -- so the I2C
pair, its pull-ups and the MODE strap are gone, and SPI1 + PB5 read it. SOURCING (user):
JLC's listing (C161798), no consignment. Order-time check: the listing still covers 11+;
if it is gone the fallback is AS5600-ASOM (C79815), which is a board change.

EVERY PIN NUMBER BELOW IS OFF THE DATASHEET, not a library symbol -- see the
per-part notes. Getting one wrong is the failure this file exists to prevent.

⚠ RE-SPUN 2026-09-21 TO branner's SPEC (docs/lever-sensor-respin.md), user decisions:
  * the lever bus runs at 5 V -- the 24 V buck (U1 LMR16006, L1, D1, C1-C3, R1/R2) is
    gone, and a 5 V -> 3V3 LDO (AP2112K) takes its place
  * J1 is PH again (2026-10-19: J1 + J2, two S4B-PH-K-S, see above), on the magnet face, on
    end with its mouth -X -- a different family from the 24 V XH tees, so no harness can
    put 24 V on a lever board
  * the outline is the spec's 31.0 x 21.9, trimmed at +X and at the top
The paragraph above on why PH is right again; the XH interlude it replaced is in git.
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

import harness                                      # noqa: E402
import netcheck                                     # noqa: E402

P = Pin.types.PASSIVE
I, O, PWR, PIN = Pin.types.INPUT, Pin.types.OUTPUT, Pin.types.PWRIN, Pin.types.PWRIN

# ── the board ────────────────────────────────────────────────────────────────
# ⚠ THE OUTLINE IS branner's RE-SPIN SPEC, NOT AN OUTPUT OF THIS FILE (docs/lever-sensor-
# respin.md, 2026-09-21). In the spec's frame -- origin on the sensor, +X toward the lever,
# +Z up -- the edges are +X 4.025, top 10.1, bottom -11.8, -X -29.0: 33.025 x 21.9. This file
# works in board-local mm with the origin at the board CENTRE, so the chip sits at
# (+12.49, +0.85): 4.025 from the +X edge and 10.1 below the top.
# J1's plug run and the tunnel in the -X web follow the -X edge (knee_lever.PCB_X0).
# ⚠ FOOTPRINTS: the MCU's QFN-28 pitch (0.4 vs 0.45) and exposed pad are still the nearest
# stock KiCad land, not read off the drawing -- resolve before ordering. The SENSOR'S IS READ
# OFF ITS DRAWING: MA730 rev 1.1 p.26 "recommended land pattern", pads 0.70 x 0.25 on 0.50
# pitch with their centres 2.90 apart, exposed pad 1.70 (elec/footprints/Steel.pretty).
MCU_FP = "Package_QFP:LQFP-48_7x7mm_P0.5mm"
SENSOR_FP = "Steel:MPS_QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm"
# THE SPEC'S FOUR EDGES, in the spec's own frame (origin on the sensor, +X toward the
# lever, +Z up). Everything else about the outline is derived from them, because it was
# not: BOARD_W and CHIP_XY were both typed, and both encode the edges, so the +X edge
# moving on 2026-09-29 left this file describing a board that no longer existed while
# every number in it stayed self-consistent (tools/check_board_match.py now says so).
# -X: GROWN 12.0 ON 2026-11-03 for the USB-over-the-bus circuit (LQFP-48 MCU, the pair
# switch, the BOOT0 detector and two supply switches; user: "we have a decent amount of
# room there to grow longer"). Everything connector-side moved with the edge (_X0).
SPEC_X0, SPEC_X1 = -41.0, 4.025
SPEC_Z0, SPEC_Z1 = -11.8, 10.1
BOARD_W, BOARD_L = SPEC_X1 - SPEC_X0, SPEC_Z1 - SPEC_Z0
# the axle axis in board-local mm -- half the board, less the chip's distance to the far
# edge. Grow the board on +X alone and the CENTRE moves, so this moves too.
CHIP_XY = (BOARD_W / 2 - SPEC_X1, BOARD_L / 2 - SPEC_Z1)

# Anything TALLER than 1.5 mm must keep its whole footprint outside the magnet
# cap's swept circle, because the board installs by dropping straight down past
# the cap. Only the connector and the transceiver (SOIC-8, 1.75) qualify now that the
# inductor went with the buck; every passive here is under 1.5, the LDO is 1.45.
CAP_SWEEP_R = 5.66
TALL_PARTS = ("J1", "J2", "U2", "SW1")
SW1_XY = (-2.5500, -7.3000)       # the terminator switch's centre, chip frame


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
    gnd, v5, v33 = Net("GND"), Net("+5V"), Net("+3V3")
    can_h, can_l = Net("CAN_H"), Net("CAN_L")
    for n in (gnd, v5, v33, can_h, can_l):
        n.drive = Pin.drives.POWER

    # ── the trunk, in on J1 and out on J2 ────────────────────────────────────
    # Two 4-way PH, each in the instrument's one order (harness.PH_PINOUT: 5 V, GND,
    # CAN_H, CAN_L), so the cable between two boards is a STRAIGHT jumper, way n to way n.
    # The two are the same four nets -- a pass-through, not a switch -- so in and out may
    # be swapped without effect. PH, THT side entry (user, 2026-10-19; see the header):
    # the power way is the 5 V LEVER bus, which is why the family differs from the 24 V
    # tees -- a lever harness physically cannot mate a motor tee.
    _trunk = harness.ph_trunk_pins()
    # J2's 5 V way is the SWITCHED downstream supply (+5V_OUT, Q1 below), so IN and OUT are
    # no longer interchangeable: the other three ways still pass straight through.
    v5_out = Net("+5V_OUT")
    v5_out.drive = Pin.drives.POWER
    for j, (ref, side) in enumerate((("J1", "in"), ("J2", "out"))):
        _rail = {"GND": gnd, "V5": (v5, v5_out)[j], "CAN_H": can_h, "CAN_L": can_l}
        names = _trunk[4 * j:4 * j + 4]
        jx = Part(name="S4B-PH-K-S", ref_prefix="J", ref=ref, tag=ref, dest="NETLIST",
                  tool="skidl", value="S4B-PH-K-S",
                  description="lever bus %s, 5 V, LCSC C157926" % side,
                  footprint="Connector_JST:JST_PH_S4B-PH-K_1x04_P2.00mm_Horizontal",
                  pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(names)])
        ways = tuple(n.rsplit("_", 1)[0] for n in names)
        harness.check_ways(ways, ("V5",), where=ref)
        for i, n in enumerate(ways):
            _rail[n] += jx[i + 1]

    # ── 5 V -> 3V3, AP2112K-3.3TRG1 (LCSC C51118) ─────────────────────────────
    # Replaces the 24 V buck. SOT-23-5 (Diodes Inc DS33549): 1 IN, 2 GND, 3 EN, 4 NC,
    # 5 OUT -- the same part and pin map the output panel uses. EN tied to IN: always on.
    # 1 uF ceramic on each side is the datasheet's stability requirement. Load is ~30 mA
    # (MCU + transceiver + sensor), so it drops (5 - 3.3) x 0.03 = 0.05 W -- nothing.
    # A LINEAR regulator is also the right call beside a magnetic angle sensor: the buck
    # was the one switching node on this board, 15 mm from the angle sensor.
    # Pins off Diodes DS39724 rev 2-2 "Pin Descriptions", SOT25 column, read 2026-09-30:
    #   1 VIN  2 GND  3 EN (high = on)  4 NC  5 VOUT
    u1 = Part(name="AP2112K-3.3", ref_prefix="U", ref="U1", tag="U1", dest="NETLIST",
              tool="skidl", value="AP2112K-3.3TRG1",
              description="600 mA LDO, 5 V -> 3V3 (LCSC C51118)",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="IN", func=PWR), Pin(num=2, name="GND", func=PWR),
                    Pin(num=3, name="EN", func=I), Pin(num=4, name="NC", func=P),
                    Pin(num=5, name="OUT", func=P)])
    # THE REGULATOR SITS BEHIND 2.2 OHM (2026-10-04). The pedal boards are reached through
    # the leg's spring pins, a joint a player can make with the instrument on. A live 5 V
    # bus, a metre of 26 AWG (about 1 uH and 0.3 ohm) and a bare 1 uF ceramic is a tank
    # with a damping ratio near 0.2: it rings to about 7.6 V, and the AP2112's input is
    # 6.5 V absolute maximum. With 2.2 ohm in the branch the ratio is about 0.9 and there
    # is no overshoot to speak of. It costs 0.18 V at 80 mA, against 1.2 V of headroom,
    # and it is in the branch only: the bus itself passes J1 -> J2 untouched.
    # The bus keeps a 100 nF of its own at the connector (the regulator's capacitor is on
    # the far side of the resistor now). It rings on a hot plug like any bare ceramic and
    # does not mind: nothing else is on this net but the connector and the resistor.
    c_bus = _c("C3", "100nF/16V", "bus HF bypass at J1 -- rated for the hot-plug ring")
    v5 += c_bus[1]; gnd += c_bus[2]
    v5_ldo = Net("+5V_LDO")
    r_in = _r("R", "R8", "2R2", "damps the input capacitor against a hot-plugged bus")
    v5 += r_in[1]; v5_ldo += r_in[2]
    v5_ldo += u1["IN"], u1["EN"]
    gnd += u1["GND"]
    v33 += u1["OUT"]
    Net("U1_NC").connect(u1["NC"])
    cin = _c("C1", "1uF", "LDO input")
    v5_ldo += cin[1]; gnd += cin[2]
    cout = _c("C2", "1uF", "LDO output")
    v33 += cout[1]; gnd += cout[2]

    # ── CAN transceiver, SN65HVD230DR (LCSC C12084) ──────────────────────────
    # SOIC-8: 1 D, 2 GND, 3 VCC, 4 R, 5 Vref, 6 CANL, 7 CANH, 8 Rs.
    # (TI SLOS346O section 7 "Pin Functions", read 2026-09-30. Rs hard to GND = high speed.)
    can_tx, can_rx = Net("CAN_TX"), Net("CAN_RX")
    # ⚠ ref= PINNED: this part has always been U2 on the board (skidl numbered it second,
    # after the buck), and with the buck gone creation order would make it U1.
    u3 = Part(name="SN65HVD230DR", ref_prefix="U", ref="U2", tag="U3", dest="NETLIST",
              tool="skidl", value="SN65HVD230DR", description="3.3 V CAN transceiver",
              footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
              pins=[Pin(num=1, name="D", func=I), Pin(num=2, name="GND", func=PWR),
                    Pin(num=3, name="VCC", func=PWR), Pin(num=4, name="R", func=O),
                    Pin(num=5, name="Vref", func=O), Pin(num=6, name="CANL", func=P),
                    Pin(num=7, name="CANH", func=P), Pin(num=8, name="Rs", func=I)])
    can_tx += u3["D"]; can_rx += u3["R"]
    v33_can = Net("+3V3_CAN")
    gnd += u3["GND"]; v33_can += u3["VCC"]
    can_l += u3["CANL"]; can_h += u3["CANH"]
    # Rs to GND through a resistor sets slope control; 0 R would be full speed.
    # 10 k slews the edges, which is the right default on a metre of cable in a
    # box full of motors -- bus B runs at 500 k-1 M, nowhere near the limit.
    rs = _r("R", "R3", "10k", "transceiver slope control")
    u3["Rs"] += rs[1]; gnd += rs[2]
    c_xcvr = _c("C4", "100nF", "transceiver decoupling")
    v33_can += c_xcvr[1]; gnd += c_xcvr[2]

    # BUS-B FAR-END TERMINATION, behind a slide switch placed by the fab: fitted on all
    # eleven, ON on the ONE board at each far end of the bus. A switch, not a solder
    # bridge, so that ending the bus needs no iron (user rule: no hand soldering).
    # R4 is 0402: a single 120R across the pair sees ~17 mA in normal traffic, 0.034 W.
    # ⚠ A 100 mW 0402 (Panasonic ERJ2RKF1200X, C413065), NOT THE HOUSE 62.5 mW ONE
    # (2026-10-06, found by elec/voltage_check.py when this board was added to it). The
    # 34 mW is a typical drive at a typical duty. A transceiver's dominant output may be
    # 3 V (SLOS346, VOD max), and the SN65HVD230 has no dominant time-out: firmware that
    # parks TXD low holds 3 V across this part for as long as it stays there, 75 mW, 120 %
    # of the house part. Same land, same value.
    rt = _r("R", "R4", "120R 100mW", "CAN termination, in circuit only with SW1 ON",
            "Resistor_SMD:R_0402_1005Metric")
    # DSHP01TSGER (LCSC C3293141), THE MOTOR TEE'S SWITCH: one part number ends both
    # buses. 1 position, SPST, recessed slide, gull wing, body 5.4 x 2.88 x 2.3, lands
    # 0.76 x 1.27 on 7.62 centres -- 8.89 over the lands, which is what sets this board's
    # -X edge (see SPEC_X0). ON is printed on the body.
    sw1 = Part(name="SW_DIP_x01", ref_prefix="SW", ref="SW1", tag="SW1", dest="NETLIST",
               tool="skidl", value="DSHP01TSGER",
               description="bus B terminator: ON on the LAST board only (LCSC C3293141)",
               footprint="Steel:Kangshen_DSHP01TSGER",
               pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    # R4 + SW1 hang off the switch's 2D port (U5 below), not off the pair: in USB mode the
    # switch lets go of them, so a terminated end board can still be flashed.
    term, term_h, term_l = Net("TERM_MID"), Net("TERM_H"), Net("TERM_L")
    term_h += rt[1]; term += rt[2], sw1[2]; term_l += sw1[1]

    # BUS-PIN CLAMPS. Two SEPARATE bidirectional TVS rather than one three-pin
    # CAN array, on purpose: a 2-pin bidirectional part is symmetric, so there is
    # no pinout to get wrong, and the 3-pin arrays' pin order is the one number I
    # could not verify. The threat is real -- a TRRS plug sweeps every contact on
    # insertion, so the leg's supply momentarily reaches CAN_H and CAN_L, and this
    # transceiver's bus pins are absolute-max -4..+16 V. (That supply is 5 V on the lever
    # bus now, inside the rating -- the clamps stay for ESD, which is what a plug on a
    # player-handled lever mostly sees.)
    for tag, net in (("D2", can_h), ("D3", can_l)):
        d = Part(name="TVS", ref_prefix="D", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                 value="LESD5L5.0CT1G", description="bidirectional 5 V TVS, bus pin to GND, "
                 "0.5 pF (LCSC C5274293, the USB clamp motor_ctrl and output_panel use) -- the "
                 "pair carries full-speed USB too",
                 # SOD-523, not SOD-123: these are signal-line ESD clamps, not power
                 # TVS, and the big package cost 18 mm2 the board no longer has once
                 # the foot pedal's Y budget capped its height at 22.55.
                 footprint="Diode_SMD:D_SOD-523",
                 pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
        net += d[1]; gnd += d[2]

    # ── MCU, CH32V203C8T6 LQFP-48 (LCSC C3001172) ────────────────────────────
    # CHANGED 2026-11-03 FROM THE G6U6 QFN-28 (user: flash every lever over its own bus
    # wires). The ROM loader serves USB on PA11/PA12 OR PB6/PB7 (WCH CH32V203 EVT doc,
    # "WCHISPTool"), and the QFN-28 has CAN on PA11/PA12 with no remap -- so it cannot
    # put USB on the pair. The C8 brings out USBFS on PB6/PB7 AND CAN1's remap 2 on
    # PB8/PB9, so USB and CAN get their own pins and PA11/PA12 stay unconnected (the
    # ROM may enable USBD there; with nothing attached that is harmless). The C8T6 has
    # 9,420 at JLC against the K8T6's 573 (2026-11-03); the C8U6 QFN-48 is the same
    # silicon in a 7x7 body (1,079) if the board ever needs the room.
    # Pins off WCH CH32V203 datasheet V3.0 table 3-1-1, the LQFP48 column, read 2026-11-03:
    #   1 VBAT  5 OSC_IN  6 OSC_OUT  7 NRST  8 VSSA  9 VDDA  23 VSS_1  24 VDD_IO_1
    #   35 VSS_2  36 VDD_2  47 VSS_3  48 VDD_IO_3  20 PB2 = BOOT1  44 BOOT0
    #   14 PA4 (sensor CS)  15 PA5 SPI1_SCK  16 PA6 SPI1_MISO  17 PA7 SPI1_MOSI
    #   34 PA13 SWDIO  37 PA14 SWCLK  39 PB3  40 PB4  41 PB5
    #   42 PB6 USBFS_DM  43 PB7 USBFS_DP  45 PB8 CAN1_RX_2  46 PB9 CAN1_TX_2
    # ⚠ FIRMWARE: CAN1 on remap 2 (PB8/PB9), not the default pins. PB2 is BOOT1 and is
    # tied to GND here (the ISP wants BOOT1 low): never drive it as an output.
    # (The QFN-28's escape history, BOOT0 tie and rotation table are in git.)
    sck, miso, mosi = Net("SENS_SCK"), Net("SENS_MISO"), Net("SENS_MOSI")
    swdio, swclk, nrst = Net("SWDIO"), Net("SWCLK"), Net("NRST")
    osc1, osc2 = Net("OSC_IN"), Net("OSC_OUT")
    usb_dp, usb_dm = Net("USB_DP"), Net("USB_DM")
    usb_sel, xcvr_en_n, ds_en, boot0 = Net("USB_SEL"), Net("XCVR_EN_N"), Net("DS_EN"), Net("BOOT0")
    _mcu_pins = (
        (1, "VBAT", PWR), (5, "OSC_IN", I), (6, "OSC_OUT", O), (7, "NRST", I),
        (8, "VSSA", PWR), (9, "VDDA", PWR), (23, "VSS_1", PWR), (24, "VDD_1", PWR),
        (35, "VSS_2", PWR), (36, "VDD_2", PWR), (47, "VSS_3", PWR), (48, "VDD_3", PWR),
        (20, "PB2", I), (44, "BOOT0", I),
        (14, "PA4", O), (15, "PA5", O), (16, "PA6", I), (17, "PA7", O),
        (34, "PA13", P), (37, "PA14", P), (39, "PB3", O), (40, "PB4", O), (41, "PB5", O),
        (42, "PB6", P), (43, "PB7", P), (45, "PB8", I), (46, "PB9", O))
    u2 = Part(name="CH32V203C8T6", ref_prefix="U", ref="U3", tag="U2", dest="NETLIST",
              tool="skidl", value="CH32V203C8T6",
              description="RISC-V MCU, CAN + USBFS; same toolchain as the controller board",
              footprint=MCU_FP,
              pins=[Pin(num=n, name=nm, func=f) for n, nm, f in _mcu_pins])
    gnd += u2["VSSA"], u2["VSS_1"], u2["VSS_2"], u2["VSS_3"], u2["PB2"]
    v33 += u2["VBAT"], u2["VDDA"], u2["VDD_1"], u2["VDD_2"], u2["VDD_3"]
    nrst += u2["NRST"]
    osc1 += u2["OSC_IN"]; osc2 += u2["OSC_OUT"]
    can_rx += u2["PB8"]; can_tx += u2["PB9"]
    swdio += u2["PA13"]; swclk += u2["PA14"]
    sck += u2["PA5"]; miso += u2["PA6"]; mosi += u2["PA7"]
    usb_dm += u2["PB6"]; usb_dp += u2["PB7"]
    usb_sel += u2["PB3"]; xcvr_en_n += u2["PB4"]; ds_en += u2["PB5"]
    boot0 += u2["BOOT0"]

    # ── THE PAIR IS USB OR CAN: TS3USB221ARSER (LCSC C128396) ──────────────────
    # TI SCDS277C table 4-1 (RSE): 1 1D+  2 1D-  3 2D+  4 2D-  5 GND  6 OE  7 D-  8 D+
    # 9 S  10 VCC; table 7-1: OE low enables, S low D = 1D, S high D = 2D. I/O 5.5 V
    # tolerant, Coff 3.5 pF, Ioff +-2 uA unpowered (sections 5.3, 5.5).
    # D = the bus pair (CAN_H = D+, CAN_L = D-), 1D = the MCU's USBFS pins, 2D = the
    # terminator. S IS PULLED LOW, so a board whose MCU is blank or in its ROM loader
    # presents USB; the application drives PB3 high to take the pair as CAN. The
    # transceiver is NOT behind the switch: it stays on plain copper and is isolated by
    # having its supply cut (Q3), so CAN never passes through 6 ohm of switch.
    u5 = Part(name="TS3USB221A", ref_prefix="U", ref="U5", tag="U5", dest="NETLIST",
              tool="skidl", value="TS3USB221ARSER",
              description="USB / CAN-termination select on the bus pair (LCSC C128396)",
              footprint="Package_DFN_QFN:Texas_UQFN-10_1.5x2mm_P0.5mm",
              pins=[Pin(num=1, name="1D+", func=P), Pin(num=2, name="1D-", func=P),
                    Pin(num=3, name="2D+", func=P), Pin(num=4, name="2D-", func=P),
                    Pin(num=5, name="GND", func=PWR), Pin(num=6, name="OE", func=I),
                    Pin(num=7, name="D-", func=P), Pin(num=8, name="D+", func=P),
                    Pin(num=9, name="S", func=I), Pin(num=10, name="VCC", func=PWR)])
    usb_dp += u5["1D+"]; usb_dm += u5["1D-"]
    term_h += u5["2D+"]; term_l += u5["2D-"]
    can_h += u5["D+"]; can_l += u5["D-"]
    gnd += u5["GND"], u5["OE"]
    v33 += u5["VCC"]; usb_sel += u5["S"]
    c = _c("C13", "100nF", "switch decoupling")
    v33 += c[1]; gnd += c[2]
    r = _r("R", "R12", "100k", "S pull-down: USB until firmware says CAN")
    usb_sel += r[1]; gnd += r[2]

    # ── WHICH ONE IS ON THE PAIR DECIDES BOOT0: LMV331IDBVR (LCSC C34731) ───────
    # TI SLCS136V table 4-1, DBV: 1 IN+  2 GND  3 IN-  4 OUT (open drain)  5 VCC.
    # IN- = 0.32 x CAN_H (R13 1M over R14 470k), IN+ = 0.30 V (R15 100k over R16 10k): the
    # pair reads CAN above about 0.94 V. A biased CAN bus holds CAN_H at 2.0-3.0 V recessive
    # (ISO 11898) and higher dominant: IN- >= 0.64 V, twice the threshold,
    # OUT low, BOOT0 low, the application runs. A USB host's 15k pull-downs (or a dead,
    # floating pair -- R14) hold it near 0: OUT lets go, R17 pulls BOOT0 high, and the
    # chip starts its ROM loader on PB6/PB7. BOOT0 is sampled only at reset, so the
    # device's own D+ pull-up appearing afterwards changes nothing.
    # ⚠ IN- is never above VCC+ (rev O absolute maximum): bus B's 7.8 V transient (its
    # clamps' breakdown) is 2.5 V there, and unpowered the 1M limits the clamp current to 8 uA.
    # That is why the divider is 1M / 470k and not 1M / 1M (3.9 V).
    u6 = Part(name="LMV331", ref_prefix="U", ref="U6", tag="U6", dest="NETLIST",
              tool="skidl", value="LMV331IDBVR",
              description="bus-is-USB detector -> BOOT0 (LCSC C34731)",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="IN+", func=I), Pin(num=2, name="GND", func=PWR),
                    Pin(num=3, name="IN-", func=I), Pin(num=4, name="OUT", func=O),
                    Pin(num=5, name="VCC", func=PWR)])
    sense, vth = Net("BUS_SENSE"), Net("BUS_VTH")
    vth += u6["IN+"]; sense += u6["IN-"]; boot0 += u6["OUT"]
    gnd += u6["GND"]; v33 += u6["VCC"]
    c = _c("C14", "100nF", "comparator decoupling")
    v33 += c[1]; gnd += c[2]
    for tag, val, a, b, what in (
            ("R13", "1M", can_h, sense, "CAN_H into the detector"),
            ("R14", "470k", sense, gnd, "divides CAN_H; reads a floating pair as USB"),
            ("R15", "100k", v33, vth, "threshold, 0.30 V"),
            ("R16", "10k", vth, gnd, "threshold, 0.30 V"),
            ("R17", "10k", v33, boot0, "BOOT0 pull-up: high unless the bus is CAN")):
        r = _r("R", tag, val, what)
        a += r[1]; b += r[2]

    # ── THE TRANSCEIVER'S SUPPLY, default off: AO3401A (LCSC C15127) ──────────
    # Unpowered, the SN65HVD230's bus pins are high impedance (SLOS346); powered, its
    # receiver bias would hold both lines near 2.3 V and wreck USB's single-ended states.
    # So it is off until the application turns it on (PB4 low). AO3401A SOT-23: 1 G, 2 S,
    # 3 D (AOS datasheet); Vgs -3.3 V gives about 60 mohm against 50 mA.
    def _pfet(tag, what):
        return Part(name="AO3401A", ref_prefix="Q", ref=tag, tag=tag, dest="NETLIST",
                    tool="skidl", value="AO3401A", description=what + " (LCSC C15127)",
                    footprint="Package_TO_SOT_SMD:SOT-23",
                    pins=[Pin(num=1, name="G", func=I), Pin(num=2, name="S", func=P),
                          Pin(num=3, name="D", func=P)])
    q3 = _pfet("Q3", "transceiver supply switch, off by default")
    v33 += q3["S"]; v33_can += q3["D"]; xcvr_en_n += q3["G"]
    r = _r("R", "R11", "100k", "holds the transceiver off until firmware")
    v33 += r[1]; xcvr_en_n += r[2]

    # ── THE NEXT BOARD'S POWER, default off: AO3401A + 2N7002 ───────────────────
    # Every board downstream is dark until this one's firmware (PB5 high) lets it up, so
    # the chain powers in order and a blank board is the ONLY ROM loader on the pair: the
    # boards upstream of it are running and have let go of the pair (PB3 high, PB4 high);
    # the ones downstream are unpowered. Q1's body diode points J2 -> J1, so it blocks
    # when off; a board plugged in backwards still powers, but no longer gates the next.
    # 2N7002 SOT-23: 1 G, 2 S, 3 D (LCSC C8545).
    q1 = _pfet("Q1", "downstream 5 V switch, off by default")
    ds_gate = Net("DS_GATE")
    v5 += q1["S"]; v5_out += q1["D"]; ds_gate += q1["G"]
    c = _c("C16", "100nF/16V", "the downstream supply's own bypass -- rated for the hot-plug ring")
    v5_out += c[1]; gnd += c[2]
    q2 = Part(name="2N7002", ref_prefix="Q", ref="Q2", tag="Q2", dest="NETLIST",
              tool="skidl", value="2N7002", description="level shift for Q1 (LCSC C8545)",
              footprint="Package_TO_SOT_SMD:SOT-23",
              pins=[Pin(num=1, name="G", func=I), Pin(num=2, name="S", func=P),
                    Pin(num=3, name="D", func=P)])
    ds_gate += q2["D"]; gnd += q2["S"]; ds_en += q2["G"]
    for tag, a, b, what in (("R9", v5, ds_gate, "holds Q1 off"),
                            ("R10", ds_en, gnd, "holds Q2 off while the MCU is in reset")):
        r = _r("R", tag, "100k", what)
        a += r[1]; b += r[2]


    y1 = Part(name="Crystal", ref_prefix="Y", ref="Y1", tag="Y1", dest="NETLIST", tool="skidl",
              value="TAXM8M4RFDCET2T", description="HSE 8 MHz, CL 12 pF (LCSC C403948, the "
              "crystal motor_ctrl and output_panel use) -- CAN bit timing wants a "
              "crystal, not the RC",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P),
                    Pin(num=3, func=P), Pin(num=4, func=P)])
    osc1 += y1[1]; osc2 += y1[3]
    gnd += y1[2], y1[4]
    for tag, net in (("C5", osc1), ("C6", osc2)):
        c = _c(tag, "15pF", "crystal load: 7.5 in series + ~4.5 of pin and track = CL 12")
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
    for tag in ("C8", "C9", "C12", "C15"):
        c = _c(tag, "100nF", "MCU decoupling, one per VDD pair and VDDA")
        v33 += c[1]; gnd += c[2]
    c_bulk = _c("C10", "4.7uF", "MCU bulk -- 0402 since the re-spin (6.3 V X5R)")
    v33 += c_bulk[1]; gnd += c_bulk[2]

    # ── the sensor, MA730GQ-Z QFN-16 (JLC C161798, the listing; see the header) ──
    # Pins off MPS MA730 datasheet rev 1.1 (8/8/2022) p.2 "package reference" and p.8 "pin
    # functions", read 2026-11-03:
    #   1 SSD  2 A  3 Z  4 MOSI  5 CS  6 B  7 MISO  8 GND
    #   9 PWM  10 TEST  11 MGL  12 SCLK  13 VDD  14 NC  15 SSCK  16 MGH ; 17 the pad
    # Only VDD (13) sits where the MT6701's did, so C11 stays at that corner.
    # Read over SPI (p.11-14): mode 0 or 3, detected by the part; 25 MHz at most; one 16-bit
    # frame with MOSI 0 returns the angle, MSB first, 14 bits used. A register read is the
    # command 010 + a 5-bit address, and its value comes back in the next frame's high byte.
    # THE FIELD DIAGNOSTIC THE MT6701 GAVE ONLY OVER SSI IS A REGISTER HERE: register 27 bit 7
    # MGH (field over MGHT), bit 6 MGL (under MGLT), thresholds in register 6 (p.18, p.21).
    # A missing, flipped or mis-gapped magnet is the likeliest MECHANICAL fault on a lever,
    # and this reads it without opening the housing -- over the same four wires, so the
    # MGL / MGH output pins (11, 16) are left open.
    # Pin handling (p.8): TEST "connect to ground"; NC "leave unconnected"; CS has an internal
    # pull-up, so the sensor stays deselected while the MCU is in reset and PB5 floats; MOSI,
    # SCLK and SSCK have internal pull-downs. SSD, A, B, Z, PWM, MGL, MGH are outputs: open.
    # The pad: "recommended ... connected to ground" (p.11).
    # VDD is 3.0-3.6 V (p.4), 11.7 mA typical, so 3V3 straight off the LDO, 100 nF at the pin
    # (p.11 asks 1 uF "close to the sensor": C10's 4.7 uF on the same rail is 3.6 mm from the
    # package centre, C11 the 100 nF at the pin itself).
    # Field (p.4): 40 mT minimum, 60 typical, no maximum given. MPS's reference magnet is
    # dia 5 x 3 N35 at a 1.5 gap (p.10); ours is dia 6 x 2.5 at AIR_GAP 1.5 (knee_lever.py),
    # the MT6701's reference. Bench check: MGL clear with MGLT raised to 001 (41 mT rising).
    # Nothing is burned into the part: zero and direction stay in the MCU, as with the MT6701.
    u4 = Part(name="MA730GQ-Z", ref_prefix="U", ref="U4", tag="U4", dest="NETLIST",
              tool="skidl", value="MA730GQ-Z",
              description="14-bit angle sensor, SPI; sensing point = package centre",
              footprint=SENSOR_FP,
              pins=[Pin(num=4, name="MOSI", func=I), Pin(num=5, name="CS", func=I),
                    Pin(num=7, name="MISO", func=O), Pin(num=8, name="GND", func=PWR),
                    Pin(num=10, name="TEST", func=I), Pin(num=12, name="SCLK", func=I),
                    Pin(num=13, name="VDD", func=PWR), Pin(num=17, name="EP", func=PWR)])
    v33 += u4["VDD"]; gnd += u4["GND"], u4["TEST"], u4["EP"]
    sck += u4["SCLK"]; miso += u4["MISO"]; mosi += u4["MOSI"]
    csn = Net("SENS_CSN")
    csn += u4["CS"], u2["PA4"]
    c_sens = _c("C11", "100nF", "sensor decoupling")
    v33 += c_sens[1]; gnd += c_sens[2]


def _sensor_qty():
    """One board per sensed player control: 6 knee levers + 5 pedals."""
    from src import dimensions as D
    return D.N_SENSED


_SENSOR_QTY = _sensor_qty()

# ── WHERE EVERY PART SITS, IN THE CHIP'S FRAME ───────────────────────────────
# Authored about the CHIP, not the board's centre, because the chip is the axle axis:
# it is the one datum the housing, the spec and this file all share, and it does not
# move when an edge does. Board-local comes out of it below, once, via CHIP_XY.
# (They were board-local until 2026-09-30. That is a frame whose origin moves whenever
# the outline changes, so widening the +X edge by 1.025 would have shifted all 28 of
# them 0.5125 mm sideways relative to the chip, silently, while every number here
# stayed the same.)
_X0 = SPEC_X0 + 29.0          # what the connector-side parts move by when the -X edge does
_PLACE_CHIP = {
        "U4": (0.0000, 0.0000, 0.0),
        # SWD: SWDIO / SWCLK / GND in a row for a clip (lever_jig reads them off the routed
        # board), NRST beside the crystal (recovery only)
        "TP1": (-4.8000, 7.1000, 0.0),     # SWDIO
        "TP2": (-2.4000, 7.1000, 0.0),     # SWCLK
        "TP3": (0.0000, 7.1000, 0.0),      # GND
        "TP4": (-7.3000, 5.6000, 0.0),     # NRST
        # J1 (in) and J2 (out) on end, END TO END, mouths -X, 3.05 in from the -X edge.
        # Placements anchor on the PAD CENTROID: S4B-PH-K's pins are its local y 0, its
        # mouth local +y 6.25, and rot 270 turns +y to -X. Way 1 of each at its top.
        "J1": (-19.7000 + _X0, 4.1500, 270.0),
        "J2": (-19.7000 + _X0, -5.8500, 270.0),
        # ── the connector column (J1 / J2's courtyards end at x -27.4): the LDO, the
        # downstream switch, the bus bypass and the transceiver ──
        "U1": (-24.8500, 8.0000, 0.0),
        "R8": (-26.1500, 5.4000, 0.0),
        "C1": (-24.0000, 5.4000, 0.0),
        "Q1": (-25.0000, 2.6000, 0.0),
        "R9": (-22.1000, 2.6000, 90.0),
        "Q2": (-25.0000, -1.2000, 0.0),
        "R10": (-22.1000, -1.2000, 90.0),
        "C3": (-20.0000, 7.0000, 0.0),
        "C16": (-20.0000, 8.5000, 0.0),
        "C12": (-21.5000, -3.4000, 90.0),
        "U2": (-23.4000, -7.5000, 180.0),
        "R3": (-23.4000, -11.0000, 0.0),
        # ── the MCU, turned so PB3..PB9 and BOOT0 face the bus parts below it, the
        # oscillator pins face the crystal east of it and SPI1 leaves its top toward the
        # sensor ──
        "U3": (-15.5000, 1.0000, 180.0),
        "C2": (-21.9000, 8.0000, 90.0),
        "C9": (-17.4000, 7.0000, 0.0),
        "C4": (-18.9000, -5.9000, 90.0),
        "R11": (-18.9000, -8.6000, 90.0),
        "Q3": (-15.8000, -9.7000, 0.0),
        "U5": (-16.0000, -6.2000, 270.0),
        "R12": (-11.6000, -8.6000, 90.0),
        "C13": (-13.0000, -6.4000, 90.0),
        "C8": (-10.2000, -5.6000, 0.0),
        "Y1": (-8.1000, 0.8000, 90.0),
        "C5": (-8.1000, 3.7000, 0.0),
        "C6": (-8.1000, -2.1000, 0.0),
        "C7": (-5.6000, 3.7500, 0.0),
        "C15": (-9.5000, 5.4000, 90.0),
        # ── the BOOT0 detector ──
        "U6": (-4.5000, -3.4000, 0.0),
        "R15": (-4.4500, 0.0000, 90.0),
        "R16": (-3.1500, 0.0000, 90.0),
        "R13": (-7.5000, -3.9000, 90.0),
        "R14": (-8.8000, -3.9000, 90.0),
        "R17": (-10.6000, -10.6000, 0.0),
        "C14": (-8.6000, -7.8000, 90.0),
        # the sensor's 100 nF at its supply pin, the 4.7 uF on the same rail
        "C11": (1.6000, 3.4000, 90.0),
        "C10": (-1.2000, -3.6000, 90.0),
        # THE TERMINATOR CORNER: SW1 along X, its lands 8.89 apart, 2.3 tall so its body keeps
        # outside the magnet cap's sweep; R4 above it; the two low-C clamps below it.
        "R4": (-8.3000, -10.6000, 0.0),
        "SW1": SW1_XY + (0.0,),
        "D2": (-1.6500, -10.2000, 180.0),
        "D3": (0.9500, -10.2000, 180.0),
    }


BOARD_NOTES = {
    # ⚠ THE ONLY BOARD THERE IS MORE THAN ONE OF, AND IT USED TO DECLARE NO COUNT AT ALL.
    # Every other board states it -- optical 1, output_panel 1, motor_ctrl 1, can_tee one
    # per motor -- and this one, the multi-unit board, stated nothing. The count existed
    # only as the BOM's angle-sensor quantity, 11, with no record of what the 11 WERE, so
    # it could not be checked and could not be traced if it moved.
    #
    # It is 6 knee levers and 5 pedals (user, 2026-09-18): one sensed axis each, one
    # angle sensor each, one of these boards each. That is D.N_SENSED, and it reproduces the
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
    # ⚠ RE-PLACED 2026-09-21 FOR THE RE-SPIN. The circuit is the routed board's, moved
    # as a block by (+1.5, +1.45) -- the frame shift that keeps the chip on the axle in the
    # new board-centred frame -- so every relationship the CAN-fan notes below were
    # measured on (MCU beside transceiver beside crystal) is preserved exactly. What
    # changed: the buck is gone from the top, the LDO and its two caps take that corner,
    # R6 steps 0.57 -X out of the +X groove band, and the four SWD pads come in off the
    # trimmed +X edge into the top strip (one column of three plus NRST, as before).
    # ⚠ NRST's HOP IS DECLARED, NOT LEFT TO THE ROUTER (2026-09-30). U3 pin 4 sits between
    # the crystal pins (2, 3) and its own cap and pad (C7, TP4) are on the far side of the
    # chip from the crystal -- so on F.Cu the reset line MUST cross both oscillator tracks at
    # a 0.4 mm-pitch escape. The router found that hop on some rolls and not others: one net
    # added (the sensor's CSN) left NRST open on five placements out of five. One via in the
    # pocket beside the pin, laid BEFORE routing so the crystal tracks go round it, and the
    # same netlist closes first pass. CHIP frame like the placements (it was board-local
    # (-0.90, 2.30) on the 31.0 board); 0.50/0.25 like the rest of the board.
    "vias": [],
    "placements": {_r: (_x + CHIP_XY[0], _y + CHIP_XY[1], _rot)
                    for _r, (_x, _y, _rot) in _PLACE_CHIP.items()},
    "cap_keepout": {"xy": list(CHIP_XY), "r": CAP_SWEEP_R, "tall": list(TALL_PARTS)},
    # FOUR LAYERS: an unbroken GND plane on In1 under a magnetic angle sensor, and the
    # layer set the 0.4 mm-pitch MCU's escape needs. (It was first argued against the 24 V
    # buck's switching loop; the buck is gone and the plane's other two jobs remain.)
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
    # 20 passes on the re-spun board: at the default 10 the J1 move alone swapped 0
    # unconnected for 1 (OSC_OUT) -- the router re-plans everything on any change.
    "router_passes": 20,
    # ⚠ AND A PLANE NEEDS STITCHING TO IT. Declaring In1 a plane is only half the
    # job: it stops the router carrying ground THROUGH the plane, and then nothing
    # connects the ground pads TO it. Declared alone it stranded six GND pads on this
    # board -- the pour reaches them, but a pour is what routing can orphan, which is
    # the whole reason the plane is there. Every GND pad gets its own via down.
    "stitch_nets": ("GND",),
    # ⚠ STITCH EXCEPTIONS: THE SENSOR'S BELLY PAD HAS NO VIA (quality A14, 2026-10-06).
    # The stitcher's 0.3 mm via in its centre is a barrel that drinks the paste (70 % of the
    # MT6701's joint), on the pad that also sets how flat the chip sits over the magnet. The
    # MA730's pad is 1.70 under four 0.69 windows, and the same reasoning holds: it carries
    # no heat (40 mW) and no current of its own, so it is joined to pin 8, the part's ground
    # pin 0.25 mm away, by copper on its own layer, and pin 8 keeps the via to the plane.
    # TEST (pin 10, "connect to ground") is joined to the pad the same way, 0.25 mm across,
    # rather than given a via of its own at the +X groove band.
    "stitch_exceptions": ("U4.17", "U4.10"),
    # ⚠ AND THE MCU'S PIN 1 (VSS, the corner pin) GOES STRAIGHT INTO ITS OWN BELLY LAND.
    # Left to the router it ran north along the package's west edge to a via, and with
    # SCL leaving pin 27 north-eastward that shut SDA -- pin 28, the corner pin between
    # them -- in a 1 mm pocket with no exit: 1 unconnected on every run since J1's
    # ways were re-ordered (2026-10-07). 0.7 mm of copper to the land frees the corner.
    # ⚠ AND THE PASS-THROUGH'S 5 V IS LAID, J1.1 -> J2.1, ON F.Cu (quality A1). Left to the
    # router it went down to In2.Cu at 0.40, and an inner layer needs 0.72 for 0.57 A at a
    # 10 C rise. The two pins share a column with J1's other three between them, so the
    # track steps 1.9 toward the mouth, under J1's own body (nothing else may stand there:
    # the connector zone), runs down, and steps back. 0.725 clear of every pad's edge.
    # The sensor's two links (stitch_exceptions), in the CHIP frame like the placements: the
    # board frame is y-up, so KiCad's pin 8 at (+0.75, +1.45) is chip (+0.75, -1.45) and pin 10
    # at (+1.45, +0.25) is chip (+1.45, -0.25). Each runs from inside its pad's heel (1.10 from
    # centre) to inside the 1.70 pad's edge (0.85), 0.30 clear of the pins either side.
    "tracks": [("GND", "F.Cu", 0.2, [(0.75 + CHIP_XY[0], -1.20 + CHIP_XY[1]),
                                     (0.75 + CHIP_XY[0], -0.70 + CHIP_XY[1])]),
               ("GND", "F.Cu", 0.15, [(1.20 + CHIP_XY[0], -0.25 + CHIP_XY[1]),
                                      (0.70 + CHIP_XY[0], -0.25 + CHIP_XY[1])])],
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
    #
    # ⚠ RE-MEASURED 2026-09-19 AS THAT NOTE ASKS, on the 34 x 28 board: "local_nets":
    # ("CAN_RX",) lays ZERO segments. The generator's reach is 6 mm single-linkage and
    # CAN_RX spans 12.5 mm end to end, so pre-laying it is not refused, it is out of
    # range. The conclusion stands for a new reason, which is worth more than the
    # conclusion: the generator is not an option for this net AT ALL, so "pre-lay
    # CAN_RX and CAN_TX fails instead" cannot be reproduced on this board and is not
    # the state to reason from any more.
    # ⚠ A SMALLER VIA, AND IT IS WHAT CLOSES THE CAN FAN -- see the note in
    # lever_sensor() for the measurement. Three signals leave three adjacent 0.4 mm-pitch
    # QFN pins and a 0.6 mm via leaves room for two; at 0.50 all three escape and this
    # board reaches 0 unconnected, 0 violations for the first time.
    #
    # THE PAD IS THE DIMENSION THAT MATTERS, NOT THE DRILL, which the sweep separates:
    #     0.60 / 0.30   1 unconnected (CAN_RX)     -- the fan has room for two
    #     0.55 / 0.30   2 unconnected (SCL, SWDIO) -- worse, not a gradient
    #     0.50 / 0.30   0 unconnected, 12 hole_clearance errors
    #     0.50 / 0.25   0 unconnected, 0 violations
    #     0.45 / 0.25   0 unconnected, 11 hole_clearance errors
    # The drill only shrinks to keep the annulus wide enough for KiCad's DEFAULT 0.25 mm
    # hole-clearance constraint, which the 0.30 drill misses by 0.011 mm.
    #
    # ⚠ (2026-10-06: THE ORDER PAGE DISAGREES WITH WHAT FOLLOWS. The reading of the
    # capability page below concluded "not surcharged"; a real order of a board with the
    # same 0.50/0.25 via was charged about 17 USD for it, plus a Kelvin test and Tg155 the
    # form adds with it. The geometry argument stands; the cost claim does not, and
    # order_options below says what the form actually does.)
    # ⚠ AND IT COSTS NOTHING, WHICH WAS WORTH CHECKING RATHER THAN ASSUMING. The via
    # note in layout.py chose 0.6/0.3 because it is JLCPCB's standard capability, so the
    # obvious reading is that this leaves it. Their published capabilities (2026-09-19)
    # say otherwise on both counts:
    #   * "Min. Via hole size/diameter ... Multilayer: 0.15 mm hole size / 0.25 mm via
    #     diameter", so 0.50/0.25 is inside standard capability, not beyond it.
    #   * The surcharge is specific: "0.2mm or 0.25mm hole size with via diameter LESS
    #     THAN 0.45mm will cost more". 0.50 is above that, so a 0.25 drill here is not
    #     surcharged. It also satisfies their "via diameter should be 0.1mm (0.15mm
    #     preferred) larger than via hole size" -- this is 0.25 larger.
    #   * Their real hole-to-copper rule is "Via hole to Track 0.2mm", LOOSER than the
    #     0.25 KiCad enforces. So the 0.50/0.30 board that failed 12 hole_clearance
    #     checks was failing a house default and not a fab limit -- it is manufacturable
    #     too. 0.50/0.25 is used because it needs no rule relaxed to prove it.
    "via_mm": (0.50, 0.25),
    # the lever bus passes THROUGH this board (J1 in, J2 out), so the first board of
    # a chain carries every later board supply: up to bus B limit, 0.57 A
    # +5V_OUT carries the rest of its arm: at most five boards at 80 mA peak (M33)
    "net_widths": {"+5V": 0.4, "+5V_OUT": 0.5},
    # the words the silkscreen uses. A legend is as wide as its longest line and this
    # board is 32 x 22: at the full net names the J1 legend and one SWD label only went
    # down at 0.8 mm, under the fab minimum of 1.0
    "silk_labels": {"TP1": "DIO", "TP2": "CLK", "TP4": "RST", "SW1": "TERM",
                    "CAN_H": "H", "CAN_L": "L", "+5V": "5V"},
    # ⚠ THE VIA SIZE IS AN ORDER-FORM FIELD, NOT JUST A GERBER FACT. JLCPCB's own
    # capability page says "please select corresponding via size option when placing
    # order" for 0.2/0.25 mm hole sizes. The gerbers carry the geometry; the process is
    # chosen on the form, and nothing in the drill file makes the operator pick it.
    "order_options": {
        "via size": "0.25 mm hole / 0.50 mm diameter -- SELECT THIS ON THE ORDER FORM. It is "
                    "CHARGED FOR, whatever the capability page suggests (order page, "
                    "2026-10-06): about +17 USD for the via size, and choosing it makes "
                    "the form add a 4-wire Kelvin test (+17) and Tg155 material (+3.5 "
                    "to 7.8) by itself. The board does not route at the 0.6/0.3 default -- see the CAN fan note.",
    },
    # ⚠ THE ONE DRC WARNING THIS BOARD KEEPS IS COSMETIC, AND IS KEPT ON PURPOSE.
    # silk_overlap x1: the segment of Y1's silkscreen OUTLINE against U2's outline
    # polygon, ~0.96 mm apart at 97.0,104.7. It is two part outlines touching on the ink
    # layer -- not a reference designator over a pad, which is the case that actually
    # costs something, and not anything the fab cannot handle (silk over copper is
    # clipped automatically). The parts either side of it are the crystal and the CAN
    # transceiver, both of which are where they are for routing reasons that took four
    # rounds to settle; moving one to tidy ink would risk the 0 unconnected this board
    # only just reached. Recorded rather than chased, so it is not mistaken later for a
    # warning nobody looked at.
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
    "groove_exempt": ["U4", "J1", "J2"],
    # J1 + J2's zone (spec rule 4): their bodies (7.6 deep) and the mated plugs' run past
    # the mouths, over the pair's 19.8 -- x ..-5.86 here, clipped to the board as before.
    "conn_keepout": {"box": [SPEC_X0 + 1.01 + CHIP_XY[0], -9.9, SPEC_X0 + 10.65 + CHIP_XY[0], 9.9],
                     "exempt": ["J1", "J2", "U4"]},
    # ── the quality pass (cadkit/PCB_QUALITY.md) ─────────────────────────────
    "quality": {
        # A17 (cadkit/PCB_QUALITY.md): a connector whose pinout block is on the OTHER face,
        # and why. Way 1 is marked on the connector's own side in every case.
        # A16, PCB_QUALITY.md 'Steady and transient': U5's pins declared here (so the generated
        # U5 entries step aside), the bus side with its transient judged on the part's ESD rating
        "pin_volts": {
            **{"U5.%d" % n: {"max": 7.0, "peak": "none", "src": 'TI TS3USB221A SCDS277C (2024) s5.1: switch I/O and control inputs -0.5..7 V, VCC -0.5..4.6 V; s5.2: 12 kV HBM on the I/O', "why": "bus B's transient figure (7.8 V) is its clamps' breakdown during an ESD discharge, nanoseconds long, the event s5.2 rates this I/O for (12 kV HBM); 7 V is a DC figure. Nothing holds the pair above 5 V, under the 5.5 V operating rating"}
               for n in (3, 4, 7, 8)},
            **{"U5.%d" % n: {"max": 7.0, "src": 'TI TS3USB221A SCDS277C (2024) s5.1: switch I/O and control inputs -0.5..7 V, VCC -0.5..4.6 V; s5.2: 12 kV HBM on the I/O'} for n in (1, 2, 6, 9)},
            "U5.10": {"max": 4.6, "src": 'TI TS3USB221A SCDS277C (2024) s5.1: switch I/O and control inputs -0.5..7 V, VCC -0.5..4.6 V; s5.2: 12 kV HBM on the I/O'},
        },
        "return_slot_ok": {
            "CAN_TX": {"mm": 6.5,
                       "why": "a 500 kbit/s logic line into the transceiver's D pin, driven at the "
                              "MCU's slowest pad speed (2 MHz, hw.c) so its edges are tens of "
                              "ns: a 6 mm detour in its return costs nothing at that rate"},
        },
        "unmatched_ok": {
            "USB_DP": "full speed, 12 Mbit/s, and only for WCH's ROM loader: a bit is 83 ns and "
                      "U5 -> MCU is under 15 mm, 0.1 ns end to end, so no skew it could have is "
                      "1 % of a bit. The pair's long run is the harness (fs_eye, docs)",
        },
        # A8 asks for a via in every exposed pad; the sensor's has none, deliberately (the
        # note at stitch_exceptions). A8's own exception: a part that needs no heat path,
        # with the pad still on its net by copper on its own layer.
        "waive": {
            "A8:U4": "MA730, about 40 mW (11.7 mA at 3.3 V): its 1.70 mm exposed pad needs no "
                     "heat path, and a via in it would take most of its paste (A14). The pad is "
                     "on GND through 0.25 mm of F.Cu to pin 8, whose own via reaches the plane",
        },
        "power_paths": [
            # the bus passes through: the first board of a chain carries the rest, up to
            # the 565 mA maximum of motor_ctrl's TPS2553 at 49.9 k
            {"net": "+5V", "from": "J1.1", "to": ["Q1.2"], "amps": 0.57},
            # the rest of its arm, five boards at most (the lever arm is six) at 80 mA peak
            {"net": "+5V_OUT", "from": "Q1.3", "to": ["J2.1"], "amps": 0.40},
            # this board: MCU ~10 mA at 48 MHz, sensor 10 mA, transceiver 17 mA dominant
            # plus ~35 mA into the bus while it drives -- 80 mA with margin
            {"net": "+5V", "from": "J1.1", "to": ["R8.1"], "amps": 0.08},
            {"net": "+5V_LDO", "from": "R8.2", "to": ["U1.1"], "amps": 0.08},
            {"net": "+3V3", "from": "U1.5", "to": ["U3.24", "U3.36", "U3.48", "U3.9", "Q3.2",
                                                  "U4.13", "U5.10", "U6.5"],
             "amps": 0.08},
            {"net": "+3V3_CAN", "from": "Q3.3", "to": ["U2.3"], "amps": 0.06},
        ],
        # A13 (cadkit/PCB_QUALITY.md): what the DESIGN leaves open, and how many nets each
        # repeated structure is on. The pass fails on any difference from the routed board.
        "unconnected": {
            "U1.4": "the maker's NC pin",
            "U2.5": "SN65HVD230 Vref output: nothing here uses the reference",
            "U3": {
                "pins": "2 3 4 10 11 12 13 18 19 21 22 25 26 27 28 29 30 31 32 33 38",
                "why": "GPIO this board gives no function: left open, firmware leaves it an input with pull-down"
            },
            "U4": {
                "pins": "1 2 3 6 9 11 14 15 16",
                "why": "MA730 (rev 1.1 p.8): SSD, A, Z, B, PWM and the MGL / MGH flag outputs, the SSI clock input (internal pull-down) and NC; the angle and the field flags are read over SPI only"
            }
        },
        "net_groups": [
            {
                "name": "bus B in and out share GND, CAN_H and CAN_L; 5 V is switched (Q1)",
                "pins": [
                    "J[12].[2-4]"
                ],
                "nets": 3,
                "each": 2
            },
            {
                "name": "one CAN transceiver: TX and RX each reach the MCU",
                "nets_like": "CAN_(TX|RX)",
                "count": 2,
                "pads": 2
            },
            {
                "name": "the transceiver's bus pins",
                "pins": [
                    "U2.[67]"
                ],
                "nets": 2,
                "each": 1
            },
            {
                "name": "one angle sensor: its four SPI pins",
                "pins": [
                    "U4.[457]",
                    "U4.12"
                ],
                "nets": 4,
                "each": 1
            }
        ],
        "pinouts": {
            "S4B-PH-K-S": "KiCad JST_PH_S4B-PH-K_1x04_P2.00mm_Horizontal (generated from "
                          "JST's ePH drawing, which refuses a scripted fetch): pins 1-4 on "
                          "local x 0..6, mouth +y 6.25. J1 and J2 are each "
                          "harness.PH_PINOUT (5 V, GND, CAN_H, CAN_L) on ways 1-4, no "
                          "mounting pegs or tabs. Read 2026-10-19",
            "AP2112K-3.3TRG1": "Diodes DS39724 p.1-2, Pin Descriptions, SOT25 column: 1 VIN, "
                               "2 GND, 3 EN (high = on), 4 NC, 5 VOUT. Board: 1 +5V_LDO, 2 GND, "
                               "3 +5V_LDO, 4 open, 5 +3V3. Read 2026-10-04",
            "SN65HVD230DR": "TI SLOS346 Pin Functions (SOIC-8): 1 D, 2 GND, 3 VCC, 4 R, "
                            "5 Vref, 6 CANL, 7 CANH, 8 RS. Board: 1 CAN_TX, 2 GND, 3 +3V3, "
                            "4 CAN_RX, 5 open, 6 CAN_L, 7 CAN_H, 8 slope resistor. Re-read "
                            "2026-10-04",
            "CH32V203C8T6": "WCH CH32V203 datasheet V3.0 table 3-1-1, the LQFP48 column, read "
                            "2026-11-03: 1 VBAT, 5 OSC_IN, 6 OSC_OUT, 7 NRST, 8 VSSA, 9 VDDA, "
                            "23 / 35 / 47 VSS, 24 / 36 / 48 VDD, 14 PA4, 15-17 PA5-PA7 = "
                            "SPI1 SCK / MISO / MOSI, 20 PB2 = BOOT1, 34 PA13 = SWDIO, 37 PA14 = "
                            "SWCLK, 39-41 PB3-PB5, 42 PB6 = USBFS_DM, 43 PB7 = USBFS_DP, 44 "
                            "BOOT0, 45 PB8 = CAN1_RX_2, 46 PB9 = CAN1_TX_2. Board: those; "
                            "PB2 and the VSS pins to GND, VBAT / VDDA / VDD to +3V3, PA4 the "
                            "sensor CS, PB3 the pair select, PB4 the transceiver supply, PB5 "
                            "the downstream supply",
            "TS3USB221ARSER": "TI SCDS277C table 4-1, RSE: 1 1D+, 2 1D-, 3 2D+, 4 2D-, 5 GND, "
                              "6 OE, 7 D-, 8 D+, 9 S, 10 VCC; table 7-1 truth table. KiCad "
                              "Texas_UQFN-10_1.5x2mm_P0.5mm (RSE0010A) numbers the same. "
                              "Board: 1 USB_DP, 2 USB_DM, 3 TERM_H, 4 TERM_L, 5 / 6 GND, "
                              "7 CAN_L, 8 CAN_H, 9 USB_SEL, 10 +3V3. Read 2026-11-03",
            "LMV331IDBVR": "TI SLCS136V table 4-1, DBV: 1 IN+, 2 GND, 3 IN-, 4 OUT, 5 VCC+. "
                           "Board: 1 BUS_VTH, 2 GND, 3 BUS_SENSE, 4 BOOT0, 5 +3V3. Read 2026-11-03",
            "AO3401A": "AOS AO3401A, SOT-23: 1 G, 2 S, 3 D. Q1: S +5V, D +5V_OUT, G DS_GATE; "
                       "Q3: S +3V3, D +3V3_CAN, G XCVR_EN_N",
            "2N7002": "SOT-23: 1 G, 2 S, 3 D. Q2: G DS_EN, S GND, D DS_GATE",
            "MA730GQ-Z": "MPS MA730 datasheet rev 1.1 (8/8/2022) p.2 package reference "
                         "(top view) and p.8 pin functions: 1 SSD, 2 A, 3 Z, 4 MOSI, 5 CS, "
                         "6 B, 7 MISO, 8 GND, 9 PWM, 10 TEST, 11 MGL, 12 SCLK, 13 VDD, 14 NC, "
                         "15 SSCK, 16 MGH, 17 the pad. Land off p.26 (Steel.pretty). Board: "
                         "4 SENS_MOSI, 5 SENS_CSN, 7 SENS_MISO, 12 SENS_SCK, 13 +3V3, 8 / 10 / "
                         "the pad GND, the rest open. Read 2026-11-03",
            "TAXM8M4RFDCET2T": "Yajingxin TAXM8M4RFDCET2T sheet (LCSC C403948), 'Connection' "
                               "drawing: lands 1 and 3 are the crystal, 2 and 4 the can "
                               "(GND). Board: 1 OSC_IN, 3 OSC_OUT, 2 / 4 GND. Read "
                               "2026-10-04",
        },
        # The manual review, 2026-10-04. Each entry is the evidence, not a tick. Left OPEN on
        # purpose: M11 (the CAD fit, after these placements reach the build), M35 (errata)
        # and the order-time items M12, M29, M30, M37, M42.
        "manual": {
            "M35": "read 2026-10-05. " + 'WCH publishes no errata sheet: its product page lists the datasheet and the reference manual (CH32FV2x_V3xRM) and nothing else, read 2026-10-05. ' + "(CH32V203: same "
                   "manual.) The other parts were not searched for errata sheets",
            "M1": "each hop is a straight PHR-4 jumper (INSTALL_NOTES, KL-6): J1 the bus "
                  "in and J2 the bus out, both in harness.PH_PINOUT order (5 V, GND, CAN_H, "
                  "CAN_L), the list motor_ctrl J2 / J6 and the leg boards are built from. "
                  "Ways 2-4 are the same nets on both; way 1 of J2 is the SWITCHED 5 V for the "
                  "next board (Q1), so IN and OUT are no longer interchangeable: J1 faces "
                  "motor_ctrl, silk says IN / OUT. Plugged reversed, Q1's body diode still "
                  "powers this board but the next one is no longer held dark. "
                  "The housing is polarised and a PH cannot enter an XH, so a lever lead "
                  "cannot reach a 24 V motor tee",
            "M19": "Q1 AO3401A (P, 5 V switch): on with Vgs -5 V (Q2 pulls its gate to GND), "
                   "Rds(on) 52 mohm max at -4.5 V (AOS Rev 3.1 p.2): 0.52 A drops 27 mV, 14 mW. "
                   "Off in reset: R9 100k holds the gate at its source. Q3 AO3401A (P, the "
                   "transceiver's 3V3): on with Vgs -3.3 V (PB4 low), 75 mohm max at -2.5 V: "
                   "60 mA drops 5 mV. Off in reset: R11 holds the gate at +3V3. Q2 2N7002 (N, "
                   "level shift): Vgs 3.3 V against Vgs(th) 2.5 V max, sinking 50 uA; R10 holds "
                   "it off in reset. No gate sees more than 5.5 V (ratings 12 / 20 V). No "
                   "series gate resistors: each gate is a DC level, switched once at start",
            "M23": "the bus pair is the USB pair (user, 2026-11-03: flash every lever over its "
                   "own bus wires). Clamps: D2 / D3 at 0.5 pF; they sit beyond SW1 rather than "
                   "at J1 (M10). Path: J1 -> U5 (D -> 1D, S low) -> PB7 (D+) / PB6 (D-), two "
                   "vias a line or fewer. D+ pull-up: internal to the CH32V203's USBFS, which "
                   "WCH's ROM loader enables. No series resistors: the USBFS cell drives at "
                   "full speed's impedance without them (WCH EVT boards fit none). Clock: the "
                   "8 MHz crystal, 50 ppm, inside the 0.25 % FS needs. VBUS: none -- the board "
                   "is powered from the bus's own 5 V way and presents no VBUS to the host",
            "M43": "EXCEPTION, the user's (2026-11-03): no USB receptacle -- the board is "
                   "loaded over its own bus wires, eleven boards inside levers and pedals. "
                   "(a) J1's CAN_H / CAN_L ARE the USB pair: J1 -> U5 (default D = 1D) -> "
                   "PB6 / PB7, USBFS. motor_ctrl hands an arm's pair to the Pi's USB (R2). (b) "
                   "WCH's ROM loader, which serves USB on PA11 / PA12 or PB6 / PB7 with BOOT0 "
                   "high (CH32V203 EVT board manual, 'WCHISPTool'). (c) BOOT0 is set by the "
                   "bus, not by a hand: U6 reads the pair, high whenever it is not a biased CAN "
                   "bus. A blank or broken board therefore comes up in the ROM loader as soon "
                   "as it is powered on a pair the Pi holds as USB, and the boards before it "
                   "power it in order (Q1, ALL 'U'): first flash, updates (also over CAN "
                   "through the board's own loader) and recovery all from the Pi, with no "
                   "hand on the board. The real-receptacle line is the part excepted: the "
                   "lead is the crimped PH harness (user, as above). OPEN until a bench "
                   "board proves the ROM loader enumerates over the pair",
            "M2": "no polarised two-pad part: D2 / D3 are bidirectional, every capacitor "
                  "is ceramic",
            "M3": "In1 is an unbroken GND plane under the whole board and B.Cu carries a "
                  "second GND pour. The pass-through's return (up to 0.57 A) goes J2.2 -> "
                  "plane -> J1.2, 10 mm, directly under its own +5V track. No slot, no "
                  "split; the regulator and every IC ground drop into the plane on their "
                  "own vias",
            "M4": "U1 (AP2112K, DS39724): asks 1 uF ceramic at IN and at OUT. C1 1 uF at "
                  "IN behind R8; C2 1 uF at OUT plus C10 4.7 uF and seven 100 nF on the same "
                  "rail. Nothing on this board steps current. No rating is written on a "
                  "value here because the highest rail is 5 V and the fab's 0402 parts at "
                  "these values are 6.3 V or more; C3 and C16, the capacitors that can see a "
                  "hot-plug ring (about 10 V), are called out as 16 V parts",
            "M5": "+5V bus: C3 (16 V), R8, Q1 (VDS 30 V) and R9 only; +5V_OUT: Q1, C16 (16 V) "
                  "and J2. +5V_LDO: U1, absolute maximum 6.5 V, behind R8 (M16). +3V3: MCU "
                  "3.6 V max operating, sensor 3.3-5 V, transceiver 3.6 V, U5 4.6 V, U6 5.5 V. "
                  "CAN pins: the SN65HVD230 stands -4..16 V and the bus supply is 5 V, so no "
                  "fault on this bus exceeds it; U5's I/O 7 V (5.5 V operating); U6's input "
                  "sees 0.32 of CAN_H through 1M (2.5 V for bus B's 7.8 V transient, against "
                  "its 3.3 V); PB6 / PB7 see the pair only in USB mode (elec/voltage_check.py); "
                  "D2 / D3 clamp ESD. R4 carries 17 mA: 34 mW, and 75 mW with the bus held "
                  "dominant at 3 V, in an 0402 rated 100 mW (ERJ2RKF1200X; the house 0402 is "
                  "62 mW and was not used). R8 carries 80 mA: 14 mW",
            "M6": "full-speed USB (12 Mbit/s) on the bus pair, in USB mode only: the harness "
                  "eye is simulated (docs/lever-usb-flash.md), on the board the pair is under "
                  "15 mm. CAN at 1 Mbit/s with slope control, SPI to the sensor at a few MHz "
                  "over about 20 mm (the part takes 25), an 8 MHz crystal beside its pins",
            "M7": "U1: EN tied to IN, fixed 3.3 V part. U2 (SLOS346): RS through 10 k to "
                  "GND = slope control; Vref left open, as the sheet allows. U4 (MA730 "
                  "rev 1.1 p.8, p.11): TEST and the pad to GND, NC open, 100 nF at VDD, "
                  "SPI mode detected by the part. U3: 8 MHz crystal on OSC_IN / OSC_OUT (M24), "
                  "100 nF on NRST, VDDA and each VDD pair with a capacitor, VBAT on +3V3, "
                  "BOOT1 to GND. U5 (SCDS277C): 100 nF at VCC, OE low, S pulled to its "
                  "default. U6 (SLCS136V): open-drain output with its pull-up (R17), 100 nF at "
                  "VCC, both inputs inside 0..VCC",
            "M8": "BOOT0 (pin 44): R17 10k up, U6's open drain down -- low (the application) "
                  "whenever the pair is a biased CAN bus, high (WCH's ROM loader) when it is "
                  "held low by a USB host or floats (R14). BOOT1 / PB2: tied to GND. NRST: the "
                  "MCU's internal pull-up and C7. U1 EN: tied to IN. U2 RS: R3 to GND. U5 S: "
                  "R12 down (USB) until PB3; OE tied low. Q1 off (R9 up, Q2 held off by R10), "
                  "Q3 off (R11 up) until firmware. U4 CS: the sensor's own pull-up holds it "
                  "high (deselected) until PA4 drives it",
            "M9": "SWD on bare 1 mm pads in a row on the magnet face, each with its name "
                  "beside it at 1.0 mm: DIO, CLK, GND, and RST beside the crystal. No 3V3 "
                  "pad: the rail is probed on C10 or C2, and the board reports itself "
                  "over CAN once it runs. The pads are the last resort (M43): firmware goes in "
                  "over the bus pair as USB",
            "M10": "CAN_H / CAN_L: D2 / D3 (LESD5L5.0CT1G, bidirectional, 0.5 pF so the pair "
                   "still carries full-speed USB) from each line to GND, beyond the terminator "
                   "switch, not at J1: the strip beside the connector tails holds the "
                   "connector-side parts. Accepted because the transceiver's bus pins are "
                   "themselves rated 16 kV HBM, U5's I/O 12 kV HBM, and no fault on this 5 V bus "
                   "reaches 24 V. Reverse polarity: one polarised housing. Over-current: the "
                   "bus is limited to 0.52 A by motor_ctrl's U6",
            "M15": "AP2112K is ceramic-stable from 1 uF. Effective output capacitance at "
                   "3.3 V of bias is about 0.6 uF (C2) + 2.5 uF (C10) + 0.7 uF (the seven "
                   "100 nF): over 3 uF. Headroom: 5 V less 0.3 V of harness less 0.18 V "
                   "in R8 is 4.5 V at the pin, against 3.3 V + 0.25 V of dropout. It "
                   "dissipates 1.2 V x 80 mA = 0.1 W at most",
            "M16": "a pedal board is reached through the leg's spring pins, a joint that "
                   "can be made with the bus live. R8, 2.2 ohm, is in series with the "
                   "regulator's input capacitor: a metre of 26 AWG (about 1 uH, 0.3 ohm) "
                   "into 1 uF has a damping ratio near 0.2 without it (a ring to about "
                   "7.6 V against 6.5 V absolute maximum) and about 0.9 with it. C3 on the "
                   "bus side rings freely and is a 16 V part with nothing else on its net",
            "M18": "the first board takes its 5 V from motor_ctrl's switch and each one after "
                   "from the board before it (Q1), so a board is never powered while its "
                   "neighbour drives its pins: an unpowered board's SN65HVD230 bus pins are "
                   "high-impedance (SLOS346), U5's I/O leak 2 uA (Ioff), U6's input arrives "
                   "through 1M. On a powered board the transceiver itself is unpowered until "
                   "firmware (Q3), and PB8 / PB9 are inputs while it is. An SWD probe is the one "
                   "outside driver and is connected with the board powered",
            "M20": "SPI to the sensor: push-pull both ways, no pull-ups; CS idles high on "
                   "the part's own pull-up. "
                   "CAN: R4 120 ohm behind SW1, reached through U5's 2D port (6 ohm), ON only "
                   "on the board at each far end of bus B (two in all; the controller sits "
                   "mid-bus and carries none). In USB mode U5 lets go of it, so an end board "
                   "can be flashed. USB: unterminated at full speed, as the standard has it; "
                   "the FS eye over the harness is simulated in docs/lever-usb-flash.md",
            "M21": "the sensor's ground pin drops into the In1 plane on its own via, its pad "
                   "and TEST reach that pin on F.Cu, C11 is 0.9 mm from its supply pin, and the only regulator is "
                   "linear -- chosen for that, in place of the buck that stood 15 mm "
                   "from the sensor",
            "M22": "no op-amp on this board",
            "M24": "Y1 TAXM8M4RFDCET2T, CL 12 pF. C5 = C6 = 15 pF: 7.5 pF in series plus "
                   "about 4.5 pF of pin and track = 12 pF. The same crystal and capacitors "
                   "as motor_ctrl and output_panel",
            "M25": "two exposed pads, both GND. The MCU's is on a via to the plane (A8) and "
                   "dissipates about 35 mW. The sensor's (U4, about 40 mW) has NO via, on "
                   "purpose: a 0.3 mm barrel would take most of that 1.70 mm pad's paste "
                   "(A14), so it is joined to pin 8 on its own layer and pin 8's via "
                   "carries its ground. Neither needs the pad for heat",
            "M26": "CAN_TX: MCU pin 46 (PB9, CAN1_TX remap 1) to U2 pin 1, D, the driver "
                   "input. CAN_RX: U2 pin 4, R, the receiver output, to MCU pin 45 (PB8, "
                   "CAN1_RX remap 1). SPI1: MCU pin 15 (PA5, SCK) to the sensor's 12 (SCLK), "
                   "16 (PA6, MISO) to its 7 (MISO, the sensor's output), 17 (PA7, MOSI) to its "
                   "4 (MOSI); PA4 (14) to its 5 (CS). USB: U5 1D+ to PB7 (USBFS_DP, 43), 1D- "
                   "to PB6 (USBFS_DM, 42); CAN_H is D+, CAN_L is D-",
            "M27": "BOOT0 (44): U6's output and R17, nothing else. BOOT1 (PB2, 20): GND only, "
                   "so firmware never drives PB2. SWDIO / SWCLK: a test pad each, nothing else. "
                   "NRST: C7 and a test pad. PA11 / PA12 (the USBD pins the ROM loader may also "
                   "open) are left unconnected, so it can enable them harmlessly",
            "M28": "CH32V203C8T6 is the LQFP48 column of table 3-1-1 (shared with QFN48X7), "
                   "not the LQFP32 or QFN32 ones beside it. TS3USB221ARSER is the RSE UQFN-10 "
                   "(table 4-1) and the A part (5.5 V tolerant I/O), not the TS3USB221. "
                   "LMV331IDBVR is the DBV SOT-23-5 column. MA730GQ-Z is the QFN-16 on tape "
                   "and reel (-Z), the only package it comes in. AP2112K-3.3TRG1 is the SOT-25 "
                   "part and SN65HVD230DR the SOIC-8. Each read against the footprint the "
                   "board places (quality.pinouts)",
            "M31": "no polarised two-pad part to mark. Each IC's pin-1 mark is the KiCad "
                   "footprint's own silk, outside the body; J1, J2 and the four SWD pads are "
                   "named in silk at 1.0 mm; the terminator switch says TERM; the pinout "
                   "legend and the board name are on the back",
            "M41": "SW1 is not read by anything: it puts R4 across the pair or does not, "
                   "and is set once, on the bench, before the board goes into its "
                   "housing. Nothing to debounce",
            "M32": "J1 and J2 are JST PH, 2.0 mm, the family the lever harness is crimped in "
                   "(harness.PH_PINOUT). PH contacts are rated 2 A; the most this bus can "
                   "deliver is 0.57 A",
            "M33": "5 V in: MCU about 15 mA, sensor 12 mA, transceiver 17 mA dominant "
                   "plus about 35 mA into the bus while it transmits, switch and comparator "
                   "under 0.1 mA: 30 mA idle, 80 mA peak, through a 600 mA regulator. Bus B: "
                   "eleven boards idle at 30 mA and one transmitting is about 0.38 A against "
                   "motor_ctrl U6's 0.475 A minimum limit",
            "M34": "CAN_TX / CAN_RX, SPI and SWD are all 3.3 V at both ends. The sensor "
                   "runs from 3.3 V, so its outputs cannot exceed the MCU's rail",
            "M36": "the downstream 5 V (J2.1) is the bus itself through Q1: limited "
                   "upstream to 0.52 A by motor_ctrl's U6, carried on 0.4 mm copper, 2 A "
                   "contacts and a 4 A FET. This board adds no source",
            "M38": "the board is held by printed grooves on its two long edges; every "
                   "part stands at least 1.85 mm in from them (groove_keepout_x). J1 "
                   "and J2 take plug force on their four through-hole joints each. Every "
                   "part is on the magnet face (single_sided); J1 / J2's pins come "
                   "through to the back, where the cradle has no wall",
            "M39": "MCU: unused GPIO are left open and set by firmware to pulled inputs; "
                   "PB8 is grounded with BOOT0. U4: SSD, A, B, Z, PWM, MGL, MGH are outputs, "
                   "left open; SSCK has its own pull-down; NC is open; TEST is grounded. U2 Vref: an output, open. U1 pin 4: NC",
            "M40": "the generator carries the record beside each value: the crystal and "
                   "its capacitors (M24), R8 (M16), the BOOT0 detector's divider and why "
                   "it is 1M / 470k (U6), the pair switch's default (USB), the 0.50 / 0.25 "
                   "via, the row of SWD pads, the capacitor at each supply pin, and the "
                   "MCU's turn (so its bus pins face the bus parts)",
        },
    },
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
    import volts_decl                   # A16: generated, see volts_decl.py
    volts_decl.into(BOARD_NOTES, "lever_sensor")
    import part_alternates
    part_alternates.stamp(BOARD_NOTES)    # cadkit M42: alternates + waivers, one table
    with open(os.path.join(OUT_DIR, "lever_sensor.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements, chip on the axle at (%.1f, %.1f)"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]), *CHIP_XY))
