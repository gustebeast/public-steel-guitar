"""Brain board -- the direct-drive instrument's motor controller, CM5 carrier and power. x1.

    py -3.12 elec/brain.py       # -> elec/out/brain.{net,board.json}

A NEW BOARD for branner's direct_bench instrument (user, 2026-11-12). It merges three of the
old instrument's boards and the cables between them:
  * motor_ctrl  -- the CH32V307 that reads the levers and pedals off bus B and commands the
                   ten SERVO42Ds on bus A, both transceivers, the lever-flash arm switches;
  * pi_cap + the Pi -- now a Compute Module 5 on two DF40 mezzanines (J1/J2): the UI
                   ribbon (J5), the two LED drops (J3 frets, J4 feet), the Pi's 5 V buck;
  * the CAN tees -- GONE. The ten motors plug in DIRECTLY (J21-J30) and the two lever /
                   pedal arms too (J15/J16): twelve JSTs, all SIDE-ENTRY ON THE TOP EDGE with
                   their mouths up, so a motor can be swapped with the board in place (user).
                   Bus A is a linear bus on the board, terminated at both ends of the row
                   (R5, R6); each drop is the motor lead, 0.1-0.3 m.
And it takes the 24 V BOOST from the output board (fill and noise -- output_board.py J10):
the chargers' OR-ed 5-20 V arrives on J10 + J12 (harness.BRAIN_POWER, two 6-way XH in
parallel, way 3 of each strapped to GND as the presence loop) and the logic on J11
(harness.BRAIN_SIGNAL).

MOUNTING (user): on its side in the X-Z plane against the -Y wall, -Y of the motors, if --
and only if -- every motor JST faces up. EVERY JST does (lead, 2026-11-13): all seventeen are
side-entry headers on the +Z edge, mouths up -- the ten motors, each over its own station
(src.direct_bench STATION, within ~1 mm of the motor's X span: short CAN drops), the two
bus-B arms, the two LED drops and the three output-board leads in the gaps. That is 292 mm of
courtyard, so the board is 320 long (instrument X -520..-200) and 70 tall (Z -107.2..-37.2): the
top edge sits 21 mm under the UI station's underside (z -16.1), room for a mated XH plug and
its wire's bend under the UI board. The UI ribbon (J5) is a pin header, not a JST: a VERTICAL
2x8 off the board face under the UI station.
The CM5 and the bucks sit on the station-3 stretch (66 mm free in Y); only low parts beside
station 2 (19 mm above z -54). Longer leads so it can be lifted out are acceptable.

POWER, IN THE ORDER IT HAPPENS:
  1. A charger is attached. The output board's MCU reads it and raises BRAIN_EN (J11).
  2. Q2 -- the old output panel's P-FET switch, now on 5-20 V with a 12 V gate clamp --
     closes only when the BUTTON says on (or the CH32 holds it, see 5) AND BRAIN_EN is high.
     Its Miller cap is the soft start: the VIN inrush limit the output board asks for.
  3. The LM5122 boost (U20, TI's SNVS954H 8.2 design) makes +24V for the motors and lights.
  4. Two 5 V bucks: U7 (+5V_AUX, always on with the 24 V) for the CH32, the transceivers and
     bus B's 5 V; U5 (+5V_CM5) for the CM5 only, held off by LOW_PWR (minimal mode, R2-6).
  5. THE CM5 SHUTS DOWN BEFORE ITS POWER GOES. When the button goes off, the CH32 holds Q2 on
     (PWR_HOLD through D13), presses the CM5's PWR_Button (Q14), waits for CM5_3.3V to fall
     (CM5_ON) and only then lets go. "Never cut a running Pi" is hardware here.
  6. PWR_BTN and BRAIN_PG go back to the output board, open drain, ACTIVE LOW (pulled up
     there): the button reads LOW when ON; the 24 V reads LOW when GOOD.

LINKS (no CH340 any more -- the CM5 is on the board):
  * CH32 USART1 (PA9/PA10, also WCH's ROM loader) <-> CM5 UART4 (GPIO12/13), 1k series each
    way so neither back-powers the other in minimal mode. CM5 GPIO25 -> CH32 NRST, GPIO19 ->
    CH32 BOOT0: the CM5 flashes the CH32 with no tool (USB-only firmware rule).
  * J13 (USB-C) <- output board J3: the panel ports' data to the CM5's USB 2.0 OTG (gadget,
    and rpiboot for the eMMC with nRPIBOOT held -- TP7).
  * J14 (USB-C) <- output board J9: the H743's OTG_FS device on the CM5's USB3-0 USB2 pair.
  * The CM5's USB3-1 USB2 pair is the LEVER-FLASH LANE (docs/lever-usb-flash.md): U9/U10
    hand an arm's pair from CAN to it for one flash. It replaces motor_ctrl's U7/U8 path.

OPEN ITEMS (BOARD_NOTES["open_items"]):
  - DF40 pad numbering vs CM5 pin numbering: pad n = pin n (J1) and pin n+100 (J2), as on
    the CM4/CM5 IO board -- check against the CM5 IO board's KiCad files before layout.
  - CM5 5 V: U5 is the 3 A LMR33630 motor_ctrl fed the Pi 4B from; the CM5 asks 5 A with
    USB loads. This board hangs nothing on the CM5's USB but two data links, so 3 A should
    hold -- measure; the LMR33640 (4 A) takes the same land.
  - LM5122 OPT tied to AGND (single-phase master) -- confirm in SNVS954H.
  - L4 and C113/C114: placeholder lands (R2-6: XR181810VC / CDEP15D90; C46550430).
  - NCEP4090GU pinout taken as the PowerPAK-SO8 family's -- check at order.
  - CM5 variant: an eMMC one (no SD socket on this board), e.g. CM5104032.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = (os.environ.get("BRAIN_OUT")
           or os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import json  # noqa: E402

from skidl import ERC, Net, Part, Pin, generate_netlist  # noqa: E402

import harness                                      # noqa: E402
import netcheck                                     # noqa: E402
import buck_cell as BC                              # noqa: E402

P = Pin.types.PASSIVE
C0402, C0603 = "Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0603_1608Metric"
C0805, C1206 = "Capacitor_SMD:C_0805_2012Metric", "Capacitor_SMD:C_1206_3216Metric"
C1210 = "Capacitor_SMD:C_1210_3225Metric"
R0402 = "Resistor_SMD:R_0402_1005Metric"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
# side entry, mouth off the board edge: on the +Z edge, the plug goes in from above
XH4_SIDE = "Connector_JST:JST_XH_S4B-XH-SM4-TB_1x04-1MP_P2.50mm_Horizontal"
XH6_SIDE = "Connector_JST:JST_XH_S6B-XH-SM4-TB_1x06-1MP_P2.50mm_Horizontal"
PH6_SIDE = "Connector_JST:JST_PH_S6B-PH-SM4-TB_1x06-1MP_P2.00mm_Horizontal"
PH4_SIDE = "Connector_JST:JST_PH_S4B-PH-SM4-TB_1x04-1MP_P2.00mm_Horizontal"
USBC_FP = "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"
DF40_FP = "Connector_Hirose_DF40:Hirose_DF40C-100DS-0.4V_2x50_P0.4mm"
FET_FP = "Package_TO_SOT_SMD:TDSON-8-1"


# ⚠ EVERY REF IS PINNED FROM ITS TAG (the lever_sensor / output_panel lesson: creation order
# is not a mechanism, and BOARD_NOTES placements are keyed by ref).
def _part(tag, name, value, desc, fp, pins):
    return Part(name=name, ref_prefix=tag.rstrip("0123456789"), ref=tag, tag=tag,
                dest="NETLIST", tool="skidl", value=value, description=desc, footprint=fp,
                pins=pins)


def _fix(tag, value, desc, fp, pins):
    return _part(tag, value, value, desc, fp, [Pin(num=i, func=P) for i in pins])


def _two(tag, prefix_name, value, desc, fp, a, b):
    x = _part(tag, prefix_name, value, desc, fp, [Pin(num=1, func=P), Pin(num=2, func=P)])
    a += x[1]
    b += x[2]
    return x


def _res(tag, value, desc, a, b, fp=R0402):
    return _two(tag, "R", value, desc, fp, a, b)


def _cap(tag, value, desc, a, b, fp=C0402):
    return _two(tag, "C", value, desc, fp, a, b)


def _diode(tag, value, desc, k, a, fp="Diode_SMD:D_SOD-523"):
    """KiCad diode lands: pad 1 = K."""
    return _two(tag, "D", value, desc, fp, k, a)


def _nfet(tag, desc, d, g, s, value="NCEP4090GU"):
    """NCEP4090GU DFN5x6: 1-3 S, 4 G, 5 the drain tab (see the open items)."""
    q = _part(tag, "Q_NMOS", value, desc, FET_FP,
              [Pin(num=n, func=P) for n in range(1, 6)])
    s += q[1], q[2], q[3]
    g += q[4]
    d += q[5]
    return q


def _small(tag, desc, d, g, s):
    """2N7002 SOT-23: 1 G, 2 S, 3 D (CJ datasheet p.1, LCSC C8545)."""
    q = _part(tag, "Q_NMOS", "2N7002", desc + " (LCSC C8545)", SOT23,
              [Pin(num=1, func=P), Pin(num=2, func=P), Pin(num=3, func=P)])
    g += q[1]
    s += q[2]
    d += q[3]
    return q


def _usbc(tag, desc):
    pins = ([Pin(num=n, func=P) for n in
             ("A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12",
              "B1", "B4", "B5", "B6", "B7", "B8", "B9", "B12")] + [Pin(num="SH", func=P)])
    return _part(tag, "USB_C_Receptacle", "TYPE-C-31-M-12", desc + " (LCSC C165948)",
                 USBC_FP, pins)


def _jst(tag, value, desc, fp, ways, nets, power=("V24", "V5", "VIN")):
    """A JST in the harness standard: join each way to the net its NAME maps to."""
    harness.check_ways(ways, power, ("GND", harness.NC), where=tag)
    j = _part(tag, value, value, desc, fp,
              [Pin(num=i + 1, name=n, func=P) for i, n in enumerate(ways)])
    for i, n in enumerate(ways):
        if n in nets:
            nets[n] += j[i + 1]
        else:
            Net("%s_NC_%d" % (tag, i + 1)).connect(j[i + 1])
    return j


def _tps2553(tag, desc, vin, en, out, fault, ilim_r, ilim_val, gnd):
    """TPS2553DBVR SOT-23-6: 1 IN, 2 GND, 3 EN, 4 FAULT#, 5 ILIM, 6 OUT (LCSC C55266)."""
    u = _fix(tag, "TPS2553DBVR", desc + " (LCSC C55266)", "Package_TO_SOT_SMD:SOT-23-6",
             range(1, 7))
    vin += u[1]
    gnd += u[2]
    en += u[3]
    fault += u[4]
    ilim = Net("%s_ILIM" % tag)
    ilim += u[5]
    out += u[6]
    _res(ilim_r, ilim_val, "%s current limit (TPS2553 p.7)" % tag, ilim, gnd)
    return u


def _ts3usb221a(tag, what):
    """TI TS3USB221A, SCDS277C table 4-1 (RSE): 1 1D+ 2 1D- 3 2D+ 4 2D- 5 GND 6 OE 7 D- 8 D+
    9 S 10 VCC; OE low enables, S low D = 1D (motor_ctrl's helper, the same part)."""
    return _part(tag, "TS3USB221A", "TS3USB221ARSER", what + ", LCSC C128396",
                 "Package_DFN_QFN:Texas_UQFN-10_1.5x2mm_P0.5mm",
                 [Pin(num=1, name="1D+", func=P), Pin(num=2, name="1D-", func=P),
                  Pin(num=3, name="2D+", func=P), Pin(num=4, name="2D-", func=P),
                  Pin(num=5, name="GND", func=P), Pin(num=6, name="OE", func=P),
                  Pin(num=7, name="D-", func=P), Pin(num=8, name="D+", func=P),
                  Pin(num=9, name="S", func=P), Pin(num=10, name="VCC", func=P)])


# ── THE CM5: two Hirose DF40C-100DS-0.4V. Raspberry Pi CM5 datasheet (RP-008180-DS-7) table 4 ──
CM5_GND = (1, 2, 7, 8, 13, 14, 22, 23, 32, 33, 42, 43, 52, 53, 59, 60, 65, 66, 71, 74, 98,
           107, 108, 113, 114, 119, 120, 125, 126, 131, 132, 137, 138, 144, 150, 155, 156,
           161, 162, 167, 168, 173, 174, 179, 180, 185, 186, 191, 192, 197, 198)
CM5_5V_IN = (77, 79, 81, 83, 85, 87)        # 4.75-5.25 V main input
CM5_3V3_OUT = (84, 86)                      # 300 mA a pin, 600 mA total; off in power-off
CM5_PIN = {"GPIO_VREF": 78, "PWR_Button": 92, "nRPIBOOT": 93, "LED_nACT": 21,
           "USB_N": 103, "USB_P": 105,                    # USB 2.0 OTG
           "USB3_0_DP": 134, "USB3_0_DM": 136,            # USB 2.0 pair of USB3 port 0
           "USB3_1_DP": 163, "USB3_1_DM": 165}            # ... and of USB3 port 1
GPIO = {2: 58, 3: 56, 4: 54, 5: 34, 6: 30, 7: 37, 8: 39, 9: 40, 10: 44, 11: 38, 12: 31,
        13: 28, 14: 55, 15: 51, 16: 29, 17: 50, 18: 49, 19: 26, 20: 27, 21: 25, 22: 46,
        23: 47, 24: 45, 25: 41, 26: 24, 27: 48}
# The CM5's GPIO jobs: pi_cap's, by BCM number (pi_cap.UI_WAYS / PI_* read through the 40-way
# header map), plus the CH32 link this board adds.
CM5_IO = {
    "UI_SW_A": 17, "UI_SW_B": 27, "UI_SW_C": 22, "UI_SW_D": 23, "UI_SW_PUSH": 24,
    "UI_ENC_A": 5, "UI_ENC_B": 6, "UI_SCLK": 21, "UI_SDIN": 20, "UI_DC": 26,
    "UI_CS_N": 18, "UI_RES_N": 16,
    "SCK_PI": 11, "SDI_PI": 10,                 # SPI0 -> the fret chain (J3)
    "SCK_FOOT_PI": 15, "SDT_FOOT_PI": 14,       # SPI5 -> the foot strip (J4)
    "CM5_TX": 12, "CM5_RX": 13,                 # UART4 <-> CH32 USART1
    "CM5_MCU_RST": 25, "CM5_MCU_BOOT": 19,      # -> CH32 NRST / BOOT0
    "MCU_IRQ_CM5": 4,                           # <- CH32: "read me"
}

# ── THE CH32V307WCU6, QFN-68: motor_ctrl's pins (WCH datasheet V3.9 table 3-1) + this board's ──
CH32_PWR = {"VSS": (69, 18, 49, 12), "VDD": (32, 50, 68, 13, 17, 31, 51, 67, 1)}
CH32_IO = {
    "OSC_IN": 5, "OSC_OUT": 6, "NRST": 7, "BOOT0": 63, "BOOT1_PB2": 28,
    "CAN1_RX": 46, "CAN1_TX": 47,               # PA11 / PA12, bus A
    "CAN2_RX": 35, "CAN2_TX": 36,               # PB12 / PB13, bus B
    "MCU_TX": 44, "MCU_RX": 45,                 # PA9 / PA10, USART1 + the ROM loader
    "SWDIO": 48, "SWCLK": 52,                   # PA13 / PA14
    "SENSE_24V": 20, "SENSE_5V": 21,            # PA4 / PA5
    "PG_5V": 66,                                # PE0, U5's power-good
    "BUSB_FAULT_N": 39,                         # PC6
    "EN_PED": 56, "EN_LEV": 57,                 # PC12 / PD2
    "SEL_PED": 34, "SEL_LEV": 33,               # PD9 / PD8
    "PWR_HOLD": 19,                             # PA3: holds Q2 on through a CM5 shutdown
    "CM5_ON": 22,                               # PA6: CM5_3.3V is up
    "CM5_PWRBTN": 64,                           # PB8: -> Q14 -> the CM5's PWR_Button
    "BRAIN_PG_N": 65,                           # PB9: open drain -> J11, LOW = 24 V good
    "BTN_IN": 24,                               # PC4: the button, as J11 carries it
    "LOW_PWR_IN": 29,                           # PB10: minimal mode, as J11 carries it
    "MCU_IRQ": 43,                              # PA8: -> CM5 GPIO4
}


def brain():
    gnd = Net("GND")
    v24, vin, vin_sw = Net("+24V"), Net("VIN_BRAIN"), Net("VIN_SW")
    v5a, v5c, v33 = Net("+5V_AUX"), Net("+5V_CM5"), Net("+3V3")
    cm5_3v3 = Net("CM5_3V3")
    for n in (gnd, v24, vin, vin_sw, v5a, v5c, v33, cm5_3v3):
        n.drive = Pin.drives.POWER
    io = {k: Net(k) for k in list(CM5_IO) + list(CH32_IO) if k != "BOOT1_PB2"}

    # ── J10 / J12 / J11: from the output board ─────────────────────────────────────────
    # Two 6-way XH power leads in parallel (10 A worst case at 2.5 A a way: two VIN and two GND
    # ways on each, 22 AWG: the two-gauge rule), way 3 of each STRAPPED TO GND here -- the output board reads it as
    # "this lead is in". Then the 6-way logic lead.
    for tag in ("J10", "J12"):
        _jst(tag, "S6B-XH-SM4-TB", "5-20 V in from the output board, lead %s of 2 in "
             "parallel; way 3 = the presence loop, strapped to GND" % tag[-1:],
             XH6_SIDE, harness.BRAIN_POWER, {"VIN": vin, "GND": gnd, "LEAD_SENSE": gnd},
             power=("VIN",))
    link = {k: Net("LINK_" + k) for k in ("BRAIN_EN", "LOW_PWR", "PWR_BTN", "BRAIN_PG")}
    _jst("J11", "S6B-PH-SM4-TB", "logic to / from the output board (harness.BRAIN_SIGNAL)",
         PH6_SIDE, harness.BRAIN_SIGNAL, dict(link, GND=gnd), power=())
    _cap("C1", "22uF/35V", "VIN bulk at the inlet, AHEAD of the switch", vin, gnd, C1210)
    _cap("C2", "100nF/50V", "VIN HF bypass at J10", vin, gnd)
    _diode("D1", "SMF24A", "VIN clamp, 200 W (LCSC C169430)", vin, gnd, "Diode_SMD:D_SOD-123F")

    # ── Q2: THE POWER SWITCH, on the 5-20 V input (the old output panel's, re-biased) ──────
    # output_panel's Q2 switched a fixed 24 V with a 330k / 150k gate divider: -7.5 V of drive.
    # On 5-20 V that divider gives -1.6 V at 5 V -- off. So: R51 100k gate-source, R50 22k down
    # to the drivers -> -4.1 V at 5 V in (SQD50P06 is specified at -4.5 V; ~3 A on a phone
    # charger is 0.2 W), and D12, a 12 V zener gate to source, holds 20 V in to -12 V against
    # the part's +-20. C49 (gate-drain) is the soft start: the brain board's VIN inrush.
    # The pull-down is Q3 AND Q10 in series: the button (or PWR_HOLD) AND BRAIN_EN.
    q2 = _part("Q2", "Q_PMOS", "SQD50P06-15L", "VIN power switch, P-channel 60 V 15.5 mOhm "
               "(LCSC C3281500); the tab is the switched VIN, electrically live",
               "Package_TO_SOT_SMD:TO-252-2",
               [Pin(num=1, name="G", func=P), Pin(num=2, name="D", func=P),
                Pin(num=3, name="S", func=P)])
    gate, pull, mid = Net("PWR_GATE"), Net("PWR_PULL"), Net("PWR_Q3_SRC")
    vin += q2["S"]
    vin_sw += q2["D"]
    gate += q2["G"]
    _res("R51", "100k", "Q2 gate to source: OFF unless pulled", vin, gate)
    _res("R50", "22k", "Q2 gate pull-down through Q3 + Q10: -4.1 V at 5 V in", gate, pull)
    _diode("D12", "BZT52C12T-7", "Q2 gate clamp, 12 V: 20 V in stays inside +-20 V "
           "(LCSC C507911)", vin, gate)
    _cap("C48", "1uF/25V", "Q2 gate-source: holds it off through a live plug-in", vin, gate)
    _cap("C49", "22nF/50V", "Q2 gate-drain: the soft-start slope", gate, vin_sw)
    sw_gate, sw_sense, sw_mid = Net("SW_GATE"), Net("SW_SENSE"), Net("SW_PU_MID")
    _small("Q3", "power-switch driver: the button (or PWR_HOLD)", pull, sw_gate, mid)
    _small("Q10", "power-switch driver: BRAIN_EN from the output board", mid,
           link["BRAIN_EN"], gnd)
    _res("R52", "100k", "BRAIN_EN down: off with the lead out", link["BRAIN_EN"], gnd)
    # Q3's gate-source: with Q3 AND Q10 off, the node between them is set by leakage alone and
    # can drift to VIN (21 V) -- past the 2N7002's +-20 V. 1M ties it to the gate instead, so
    # Q3's Vgs never exceeds SW_GATE's own 10.6 V clamp; 10 uA at most, beside R55's 10k.
    _res("R63", "1M", "Q3 gate-source: holds the Q3 / Q10 middle node to the gate (A16)", sw_gate, mid)
    # THE BUTTON (output_panel's circuit, moved: the UI station hangs beside this board now).
    # Its throws arrive on the UI ribbon (ways 15/16); a throw shorted to GND says OFF, so a
    # missing ribbon reads ON. Up to 10 V and 2.1 mA at the switch (12 V / 0.3 A part).
    sw_up, sw_dn = Net("PWR_SW_UP"), Net("PWR_SW_DN")
    _res("R53", "4k7", "button pull-up, top half", vin, sw_mid)
    _res("R54", "4k7", "button pull-up, bottom half", sw_mid, sw_sense)
    _res("R55", "10k", "Q3 gate filter, 1 ms with C50", sw_sense, sw_gate)
    _cap("C50", "100nF", "Q3 gate filter", sw_gate, gnd)
    _diode("D8", "BZT52C10T-7", "10 V zener: the button never sees more (LCSC C248313)",
           sw_sense, gnd)
    jp1 = _part("JP1", "SolderJumper_3_Bridged12", "THROW",
                "which throw of the power button means OFF: bridged 1-2 = UP (as made), "
                "cut and bridge 2-3 = DN",
                "Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm",
                [Pin(num=1, func=P), Pin(num=2, func=P), Pin(num=3, func=P)])
    sw_up += jp1[1]
    sw_sense += jp1[2]
    sw_dn += jp1[3]
    # PWR_HOLD: the CH32 keeps the switch on through the CM5's shutdown
    _diode("D13", "BAT54WS", "PWR_HOLD into Q3's gate: OR with the button (LCSC C124205)",
           sw_gate, io["PWR_HOLD"], "Diode_SMD:D_SOD-323")
    _res("R56", "100k", "PWR_HOLD down: no hold through reset", io["PWR_HOLD"], gnd)
    # the button, back out to the output board: open drain, LOW = ON
    btn_g = Net("BTN_OUT_G")
    _res("R57", "10k", "Q12 gate from the button sense", sw_sense, btn_g)
    _res("R58", "100k", "Q12 gate down", btn_g, gnd)
    _small("Q12", "PWR_BTN to the output board, open drain: LOW = the button says ON",
           link["PWR_BTN"], btn_g, gnd)
    _res("R59", "10k", "the button as J11 carries it, into the CH32 (pulled up at the "
         "output board)", link["PWR_BTN"], io["BTN_IN"])
    _res("R60", "10k", "LOW_PWR as J11 carries it, into the CH32", link["LOW_PWR"],
         io["LOW_PWR_IN"])
    _res("R61", "100k", "LOW_PWR down: full mode with the lead out", link["LOW_PWR"], gnd)
    _res("R62", "1k", "BRAIN_PG out, open drain from the CH32: LOW = +24V good",
         io["BRAIN_PG_N"], link["BRAIN_PG"])

    # ── U20: THE BOOST, VIN_SW (5-20 V) -> 24 V, ~100 W. LM5122, TI SNVS954H 8.2 ────────────
    # TI's worked example is this design almost exactly (9/12/20 V in, 24 V 4.5 A out, 250 kHz,
    # 10 uH); its values stand except UVLO 49k9 / 18k2 (on at 4.49 V, so a 5 V phone charger
    # still runs MINIMAL mode -- R2-6) and Rs 4 mR (75 mV / 4 mR = 18.75 A cycle-by-cycle; a
    # 5 A, 9 V input peaks ~12.6 A). Behind Q2, so off really is off: a boost that is merely
    # disabled passes VIN to its output through the high-side body diode.
    b = {k: Net("BST_" + k) for k in ("VIN", "UVLO", "SS", "RT", "FB", "COMP", "SLOPE", "RES",
                                      "LO", "VCC", "SW", "HO", "BST", "CSPF", "CSNF", "LMID",
                                      "COMPMID", "FBMID")}
    u20 = _fix("U20", "LM5122PWPR", "synchronous boost controller, HTSSOP-20 (LCSC C77241)",
               "Package_SO:Texas_PWP0020A", range(1, 22))
    Net("U20_SYNCOUT_NC").connect(u20[1])
    gnd += u20[2], u20[9], u20[15], u20[21]   # OPT (master), AGND, PGND, the pad
    b["CSNF"] += u20[3]
    b["CSPF"] += u20[4]
    b["VIN"] += u20[5]
    b["UVLO"] += u20[6]
    b["SS"] += u20[7]
    b["RT"] += u20[8]
    b["FB"] += u20[10]
    b["COMP"] += u20[11]
    b["SLOPE"] += u20[12]
    Net("U20_MODE_NC").connect(u20[13])        # internal divider: diode emulation, skip
    b["RES"] += u20[14]
    b["LO"] += u20[16]
    b["VCC"] += u20[17]
    b["SW"] += u20[18]
    b["HO"] += u20[19]
    b["BST"] += u20[20]
    _two("L4", "L", "10uH 15A", "boost inductor, 10 uH, Isat >= 15 A, SHIELDED -- placeholder "
         "land; SKU open (R2-6: XR181810VC C53307993 / CDEP15D90 C171580)",
         "Inductor_SMD:L_Bourns_SRP1770TA_16.9x16.9mm", b["LMID"], b["SW"])
    _res("R109", "4mR 1W", "boost current sense, VIN side of L4 (TI's 4 mR)", vin_sw,
         b["LMID"], "Resistor_SMD:R_2512_6332Metric")
    _res("R110", "100R", "CSP filter (TI's 100R / 100 pF)", vin_sw, b["CSPF"])
    _res("R111", "100R", "CSN filter", b["LMID"], b["CSNF"])
    _cap("C104", "100pF/50V", "current-sense filter cap", b["CSPF"], b["CSNF"])
    _nfet("Q8", "boost low-side switch", b["SW"], b["LO"], gnd)
    _nfet("Q9", "boost high-side (synchronous) switch, SW to +24V", v24, b["HO"], b["SW"])
    _diode("D17", "1N4148WT", "boost bootstrap VCC -> BST, 75 V (LCSC C917006)", b["BST"],
           b["VCC"])
    _cap("C99", "100nF/50V", "boost bootstrap, BST to SW", b["BST"], b["SW"])
    _cap("C98", "4.7uF/25V", "LM5122 VCC (7.6 V) bypass", b["VCC"], gnd, C0805)
    _res("R108", "3R", "LM5122 VIN filter (TI's 3R / 0.47 uF)", vin_sw, b["VIN"],
         "Resistor_SMD:R_0603_1608Metric")
    _cap("C97", "470nF/50V", "LM5122 VIN filter", b["VIN"], gnd, C0603)
    _res("R100", "36k5 1%", "LM5122 RT: 250 kHz (TI's)", b["RT"], gnd)
    _res("R101", "49k9 1%", "UVLO top -- also the 0.5 V hysteresis (10 uA)", vin_sw, b["UVLO"])
    _res("R102", "18k2 1%", "UVLO bottom: on at 4.49 V", b["UVLO"], gnd)
    _res("R103", "49k9 1%", "FB top, first half (TI's 49k9 + 825R)", v24, b["FBMID"])
    _res("R104", "825R 1%", "FB top, second half", b["FBMID"], b["FB"])
    _res("R105", "2k67 1%", "FB bottom: 1.2 x (1 + 50.725/2.67) = 24.0 V", b["FB"], gnd)
    _res("R106", "68k1 1%", "COMP series R (TI's: crossover ~5.3 kHz)", b["COMP"], b["COMPMID"])
    _cap("C102", "22nF/50V", "COMP series C", b["COMPMID"], b["FB"])
    _cap("C103", "330pF/50V", "COMP high-frequency C", b["COMP"], b["FB"])
    _res("R107", "100k", "SLOPE: K ~ 1 at the lowest input (TI's)", b["SLOPE"], gnd)
    _cap("C100", "100nF", "soft-start, ~12 ms", b["SS"], gnd)
    _cap("C101", "470nF/25V", "hiccup restart timer (TI's)", b["RES"], gnd)
    for k in range(4):
        _cap("C%d" % (92 + k), "22uF/35V", "boost input bulk, after Q2", vin_sw, gnd, C1210)
    _cap("C96", "100nF/50V", "VIN_SW HF bypass at the boost", vin_sw, gnd)
    for k in range(8):
        _cap("C%d" % (105 + k), "22uF/35V", "boost output ceramic, ahead of the polymers "
             "(TI: ceramics first)", v24, gnd, C1210)
    for tag in ("C113", "C114"):
        _cap(tag, "470uF/35V", "boost output bulk, polymer -- placeholder land, SKU open "
             "(R2-6: C46550430)", v24, gnd, "Capacitor_SMD:CP_Elec_10x10.5")
    _cap("C115", "100nF/50V", "+24V HF bypass", v24, gnd)
    _diode("D3", "SMCJ24A", "+24V clamp, 1.5 kW -- ten stepper drivers' kick lands here",
           v24, gnd, "Diode_SMD:D_SMC")

    # ── U7: +5V_AUX -- the buck cell (output_board's U5), always on with the 24 V ───────────
    # Feeds what must run in MINIMAL mode: the CH32 (via U8), the transceivers, bus B's 5 V.
    # motor_ctrl took bus B's 5 V off the Pi's rail; minimal mode turns that rail off.
    sw7, boot7, fb7, vcc7 = Net("SW7"), Net("BOOT7"), Net("FB7"), Net("VCC7")
    u7 = _part("U7", "LMR33630", BC.U_VALUE, "24 V -> +5V_AUX synchronous buck, 1.4 MHz, 3 A "
               "(LCSC %s)" % BC.U_LCSC, BC.U_FP, [Pin(num=n, func=P) for n in range(1, 13)])
    gnd += u7[1], u7[11], u7[6]
    v24 += u7[2], u7[10], u7[9]
    sw7 += u7[3], u7[12]
    boot7 += u7[4]
    vcc7 += u7[5]
    fb7 += u7[7]
    Net("U7_PG_NC").connect(u7[8])
    _two("L3", "L", BC.L1_VALUE, BC.L1_DESC, BC.L1_FP, sw7, v5a)
    _res("R14", "100k", "+5V_AUX feedback, top", v5a, fb7)
    _res("R15", "24k9 1%", "+5V_AUX feedback, bottom: 5.02 V", fb7, gnd)
    for tag, val, a, why, fp in (("C51", "10uF/50V", v24, "U7 input bulk", C1206),
                                 ("C52", "100nF/50V", v24, "U7 input HF, pins 10/11", C0402),
                                 ("C53", "1uF/25V", vcc7, "U7 VCC", C0402),
                                 ("C55", "22uF/16V", v5a, "+5V_AUX bulk", C0805),
                                 ("C56", "22uF/16V", v5a, "+5V_AUX bulk", C0805)):
        _cap(tag, val, why, a, gnd, fp)
    _cap("C54", "100nF/50V", "U7 bootstrap", boot7, sw7)
    u8 = _fix("U8", "AP2112K-3.3TRG1", "+5V_AUX -> +3V3 for the CH32, the transceivers, the "
              "switches (LCSC C51118)", "Package_TO_SOT_SMD:SOT-23-5", range(1, 6))
    v5a += u8[1], u8[3]
    gnd += u8[2]
    Net("U8_NC_4").connect(u8[4])
    v33 += u8[5]
    _cap("C57", "1uF", "U8 input", v5a, gnd)
    _cap("C58", "10uF", "+3V3 bulk", v33, gnd, C0805)

    # ── U5: +5V_CM5 -- motor_ctrl's Pi buck, its fuse and its crowbar (motor_ctrl.py U5) ─────
    # EN: motor_ctrl's 18.1 V UVLO divider, and Q15 holds it low while LOW_PWR is high
    # (MINIMAL mode: the output board decided from the contract before anything started).
    v24_f, v24_buck, v5_raw = Net("+24V_F"), Net("+24V_BUCK"), Net("+5V_RAW")
    v5_raw.drive = Pin.drives.POWER
    sw5, boot5, vcc5, fb5, en5 = Net("SW5"), Net("BOOT5"), Net("VCC5"), Net("FB5"), Net("EN5")
    _res("R23", "0R", "link in U5's input branch; a damper's land if one is wanted", v24_f,
         v24, "Resistor_SMD:R_1206_3216Metric")
    _two("F1", "Fuse", "JFC1206-1150FS", "1.5 A 63 V: a shorted U5 must not take the 24 V down",
         "Fuse:Fuse_1206_3216Metric", v24_f, v24_buck)
    u5 = _part("U5", "LMR33630ADDAR", "LMR33630ADDAR", "36 V 3 A synchronous buck, 24 V -> "
               "5 V for the CM5", "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm",
               [Pin(num=n, func=P) for n in range(1, 10)])
    gnd += u5[1], u5[9]                        # PGND, AGND (motor_ctrl._LMR33630_DDA_PINS)
    v24_buck += u5[2]
    en5 += u5[3]
    io["PG_5V"] += u5[4]
    fb5 += u5[5]
    vcc5 += u5[6]
    boot5 += u5[7]
    sw5 += u5[8]
    _two("L2", "L", "VLS6045EX-6R8M", "6.8 uH 5 V buck inductor, Isat 4.7 A, shielded 6x6x4.5",
         "Inductor_SMD:L_TDK_VLS6045EX_VLS6045AF", sw5, v5_raw)
    for tag in ("C16", "C17"):
        _cap(tag, "10uF/50V", "5 V buck input bulk", v24_buck, gnd, C1206)
    _cap("C18", "220nF/50V", "5 V buck input HF bypass, at VIN / PGND", v24_buck, gnd, C0603)
    _cap("C19", "1uF", "5 V buck VCC bypass", vcc5, gnd)
    _cap("C20", "100nF", "5 V buck bootstrap", boot5, sw5)
    for tag in ("C21", "C22", "C31", "C32"):
        _cap(tag, "22uF/25V", "5 V output bulk", v5_raw, gnd, C1206)
    _res("R10", "100k", "5 V feedback divider, top", v5_raw, fb5)
    _res("R11", "24k9 1%", "5 V feedback divider, bottom -- 5.02 V", fb5, gnd)
    _res("R12", "137k 1%", "5 V EN/UVLO divider, top -- turn-on at 18.1 V", v24, en5)
    _res("R13", "10k 1%", "5 V EN/UVLO divider, bottom", en5, gnd)
    lp_g = Net("LOWPWR_G")
    _res("R16", "10k", "Q15 gate from LOW_PWR", link["LOW_PWR"], lp_g)
    _res("R17", "100k", "Q15 gate down", lp_g, gnd)
    _small("Q15", "MINIMAL mode: holds U5's EN low, the CM5 stays off", en5, lp_g, gnd)
    _two("F2", "Fuse", "JFC1206-1400FS", "4 A 63 V: 5 V output fuse -- the element D9 blows "
         "when U5 fails short", "Fuse:Fuse_1206_3216Metric", v5_raw, v5c)
    _diode("D9", "SMBJ5.0A", "THE CROWBAR: clamps +5V_CM5 and draws enough through F2 to "
           "open it", v5c, gnd, "Diode_SMD:D_SMB")
    for k, tag in enumerate(("C23", "C24", "C25")):
        _cap(tag, "22uF/16V", "+5V_CM5 bulk at the module's input pins", v5c, gnd, C0805)
    _res("R18", "10k", "+5V_CM5 sense divider, top", v5c, io["SENSE_5V"])
    _res("R19", "10k", "+5V_CM5 sense divider, bottom", io["SENSE_5V"], gnd)
    _res("R20", "100k", "+24V sense divider, top", v24, io["SENSE_24V"])
    _res("R21", "10k", "+24V sense divider, bottom", io["SENSE_24V"], gnd)

    # ── J1 / J2: THE CM5 ────────────────────────────────────────────────────────────────
    cm5 = [_part(tag, "DF40C-100DS-0.4V", "DF40C-100DS-0.4V(51)",
                 "CM5 mezzanine, carrier side, pins %d-%d -- the CM5 datasheet names "
                 "Amphenol 10164227-1001A1RLF (1.5 mm stack, NOTHING under the module); "
                 "Hirose DF40C-100DS-0.4V is the same land" % (1 + 100 * k, 100 + 100 * k),
                 DF40_FP,
                 [Pin(num=n, func=P) for n in range(1, 101)])
           for k, tag in enumerate(("J1", "J2"))]

    def cpin(n):
        return cm5[(n - 1) // 100][(n - 1) % 100 + 1]
    used = set()

    def cnet(net, *ns):
        for n in ns:
            net += cpin(n)
            used.add(n)
    cnet(gnd, *CM5_GND)
    cnet(v5c, *CM5_5V_IN)
    cnet(cm5_3v3, *CM5_3V3_OUT)
    cnet(cm5_3v3, CM5_PIN["GPIO_VREF"])          # 3.3 V GPIO; may not float or be grounded
    for name, g in CM5_IO.items():
        cnet(io[name], GPIO[g])
    pwrbut, nrpiboot, led_act = Net("CM5_PWR_BUT"), Net("CM5_nRPIBOOT"), Net("CM5_LED_nACT")
    cnet(pwrbut, CM5_PIN["PWR_Button"])
    cnet(nrpiboot, CM5_PIN["nRPIBOOT"])
    cnet(led_act, CM5_PIN["LED_nACT"])
    otg_p, otg_n = Net("GADGET_DP"), Net("GADGET_DM")
    lnk_p, lnk_n = Net("OB_LINK_DP"), Net("OB_LINK_DM")
    fl_p, fl_n = Net("FLASH_DP"), Net("FLASH_DM")
    cnet(otg_p, CM5_PIN["USB_P"])
    cnet(otg_n, CM5_PIN["USB_N"])
    cnet(lnk_p, CM5_PIN["USB3_0_DP"])
    cnet(lnk_n, CM5_PIN["USB3_0_DM"])
    cnet(fl_p, CM5_PIN["USB3_1_DP"])
    cnet(fl_n, CM5_PIN["USB3_1_DM"])
    for n in range(1, 201):
        if n not in used:
            Net("CM5_NC_%d" % n).connect(cpin(n))
    for tag in ("C26", "C27", "C28"):
        _cap(tag, "100nF", "+5V_CM5 HF at the module", v5c, gnd)
    _cap("C29", "1uF", "CM5_3V3 bypass", cm5_3v3, gnd)
    _small("Q14", "the CH32 presses the CM5's PWR_Button (pulled up to 5 V on the module)",
           pwrbut, io["CM5_PWRBTN"], gnd)
    _res("R24", "100k", "CM5_PWRBTN down: no press through reset", io["CM5_PWRBTN"], gnd)
    _res("R25", "10k", "CM5_ON: CM5_3V3 into the CH32 -- the module is up", cm5_3v3,
         io["CM5_ON"])
    _res("R26", "100k", "CM5_ON down: reads off when the module is", io["CM5_ON"], gnd)
    led_a = Net("ACT_LED_A")
    _res("R27", "1k", "activity LED series, from +3V3", v33, led_a)
    _diode("D18", "KT-0603G", "CM5 activity LED, green (LCSC C12624)", led_act, led_a,
           "LED_SMD:LED_0603_1608Metric")
    tp7 = _part("TP7", "TestPoint", "nRPIBOOT", "nRPIBOOT pad -- hold to GND at power-up to "
                "flash the eMMC over J13 (rpiboot); bare copper", "TestPoint:TestPoint_Pad_D1.5mm",
                [Pin(num=1, func=P)])
    nrpiboot += tp7[1]

    # ── J13 / J14: the two USB links from the output board ───────────────────────────────
    for tag, (dp, dm), what in (("J13", (otg_p, otg_n), "the panel ports' data -> the CM5's "
                                 "USB 2.0 OTG (gadget; rpiboot) -- from output board J3"),
                                ("J14", (lnk_p, lnk_n), "the output board's H743 (OTG_FS "
                                 "device) -> the CM5's USB3-0 USB2 pair -- from output J9")):
        j = _usbc(tag, what)
        gnd += j["A1"], j["A12"], j["B1"], j["B12"], j["SH"]
        Net("%s_VBUS_NC" % tag).connect(j["A4"], j["B4"], j["A9"], j["B9"])
        # CC1 / CC2 left OPEN, each on its own: a data-only C-to-C link with no VBUS, so
        # nothing negotiates. Tying them (as before) is the A6 trap: an e-marked cable's Ra
        # would sit across both.
        dp += j["A6"], j["B6"]
        dm += j["A7"], j["B7"]

    # ── U1: THE CH32V307 -- motor_ctrl's MCU and wiring ──────────────────────────────────
    u1 = _fix("U1", "CH32V307WCU6", "RISC-V MCU, 2x hardware CAN (LCSC C5142795)",
              "Package_DFN_QFN:QFN-68-1EP_8x8mm_P0.4mm_EP5.2x5.2mm", range(1, 70))
    for n in CH32_PWR["VSS"]:
        gnd += u1[n]
    for n in CH32_PWR["VDD"]:
        v33 += u1[n]
    u1_used = set(CH32_PWR["VSS"]) | set(CH32_PWR["VDD"])
    for name, n in CH32_IO.items():
        if name == "BOOT1_PB2":
            gnd += u1[n]
        else:
            io[name] += u1[n]
        u1_used.add(n)
    for n in range(1, 70):
        if n not in u1_used:
            Net("U1_NC_%d" % n).connect(u1[n])
    y1 = _fix("Y1", "TAXM8M4RFDCET2T", "8 MHz HSE, CL 12 pF -- CAN bit timing wants a crystal",
              "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", range(1, 5))
    io["OSC_IN"] += y1[1]
    io["OSC_OUT"] += y1[3]
    gnd += y1[2], y1[4]
    _cap("C4", "15pF", "crystal load", io["OSC_IN"], gnd)
    _cap("C5", "15pF", "crystal load", io["OSC_OUT"], gnd)
    _cap("C6", "100nF", "NRST filter", io["NRST"], gnd)
    _res("R7", "10k", "BOOT0 pull-down", io["BOOT0"], gnd)
    _res("R8", "10k", "NRST pull-up", io["NRST"], v33)
    for k, tag in enumerate(("C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14")):
        _cap(tag, "100nF", "MCU supply decoupling", v33, gnd)
    _cap("C15", "10uF", "MCU bulk", v33, gnd, C0805)
    for ref, net, what in (("TP1", io["SWDIO"], "SWDIO"), ("TP2", io["SWCLK"], "SWCLK"),
                           ("TP3", io["NRST"], "NRST"), ("TP4", gnd, "GND"),
                           ("TP5", v33, "+3V3"), ("TP6", io["BOOT0"], "BOOT0")):
        tp = _part(ref, "TestPoint", "SWD", "SWD pad -- %s; bare copper" % what,
                   "TestPoint:TestPoint_Pad_D1.5mm", [Pin(num=1, func=P)])
        net += tp[1]
    # the CM5 link: 1k in every line, so a powered side never feeds an unpowered one
    for ref, a, b_, what in (("R30", "CM5_TX", "MCU_RX", "CM5 UART4 TX -> CH32 USART1 RX"),
                             ("R31", "MCU_TX", "CM5_RX", "CH32 USART1 TX -> CM5 UART4 RX"),
                             ("R32", "CM5_MCU_RST", "NRST", "CM5 GPIO25 -> CH32 NRST"),
                             ("R33", "CM5_MCU_BOOT", "BOOT0", "CM5 GPIO19 -> CH32 BOOT0"),
                             ("R34", "MCU_IRQ", "MCU_IRQ_CM5", "CH32 PA8 -> CM5 GPIO4")):
        _res(ref, "1k", what + " -- series: no back-powering in minimal mode", io[a], io[b_])

    # ── the two CAN transceivers (motor_ctrl's U2 / U3) ──────────────────────────────────
    a_h, a_l, b_h, b_l = Net("CANA_H"), Net("CANA_L"), Net("CANB_H"), Net("CANB_L")
    for tag, value, desc, tx, rx, ch, cl, pin5, rtag, rwhat in (
            ("U2", "TCAN3413DR", "bus A -- the motors; +-58 V bus fault (TI SLLSFP9)",
             "CAN1_TX", "CAN1_RX", a_h, a_l, v33, "R3", "bus A transceiver STB, low = normal"),
            ("U3", "SN65HVD230DR", "bus B -- the levers and pedals (TI SLOS346O)",
             "CAN2_TX", "CAN2_RX", b_h, b_l, None, "R4", "bus B slope control")):
        u = _fix(tag, value, desc, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", range(1, 9))
        io[tx] += u[1]
        gnd += u[2]
        v33 += u[3]
        io[rx] += u[4]
        if pin5 is not None:
            pin5 += u[5]                       # TCAN3413 VIO
        else:
            Net("U3_VREF_NC").connect(u[5])
        cl += u[6]
        ch += u[7]
        rs = Net("%s_RS" % tag)
        rs += u[8]
        _res(rtag, "10k", rwhat, rs, gnd)
        _cap("C3%d" % (3 if tag == "U2" else 4), "100nF", "%s supply bypass" % tag, v33, gnd)
    # bus A is a LINE on this board: the ten motor headers in a row, terminated at both ends
    _res("R5", "120R", "bus A termination at the row's U2 end, 1%", a_h, a_l,
         "Resistor_SMD:R_0603_1608Metric")
    _res("R6", "120R", "bus A termination at the row's far end, 1% -- place past J25 (motor 5, the -X end)", a_h,
         a_l, "Resistor_SMD:R_0603_1608Metric")
    d2 = _fix("D2", "NUP2105LT1G", "bus A clamp: CAN_H and CAN_L to GND, 24 V stand-off",
              SOT23, range(1, 4))
    a_h += d2[1]
    a_l += d2[2]
    gnd += d2[3]
    for k in range(10):
        _jst("J%d" % (21 + k), "S4B-XH-SM4-TB",
             "motor %d (string %d) -- SERVO42D: 24 V + bus A, side entry, mouth UP"
             % (k + 1, k + 1), XH4_SIDE, harness.XH_PINOUT,
             {"V24": v24, "GND": gnd, "CAN_H": a_h, "CAN_L": a_l})
    # A2: a 24 V bypass at the row, one per neighbouring pair of motor headers (within 25 mm of
    # each): a stepper driver's chopper edges come back down its lead, and the boost's output
    # caps sit up to 250 mm away at the +X end. The SERVO42D carries its own bulk; these are
    # the board-side HF return, not a reservoir.
    for tag, pair in (("C116", "J25"), ("C117", "J24 / J26"), ("C118", "J30 / J21"),
                      ("C119", "J23 / J27"), ("C120", "J29"), ("C121", "J22 / J28")):
        _cap(tag, "10uF/50V", "+24V bypass at motor header(s) %s" % pair, v24, gnd, C1206)

    # ── bus B: two arms, each CAN or the flash lane (motor_ctrl's _arm_switches) ────────────
    ped_h, ped_l, lev_h, lev_l = Net("PED_H"), Net("PED_L"), Net("LEV_H"), Net("LEV_L")
    v5_ped, v5_lev = Net("+5V_BUSB_PED"), Net("+5V_BUSB_LEV")
    for n in (v5_ped, v5_lev):
        n.drive = Pin.drives.POWER
    for tag, (ah, al), sel, ctag, rtag, what in (
            ("U9", (ped_h, ped_l), io["SEL_PED"], "C37", "R28", "pedal"),
            ("U10", (lev_h, lev_l), io["SEL_LEV"], "C38", "R29", "lever")):
        u = _ts3usb221a(tag, "%s arm: CAN (U3) or the CM5's flash lane (USB3-1)" % what)
        b_h += u["1D+"]
        b_l += u["1D-"]
        fl_p += u["2D+"]
        fl_n += u["2D-"]
        ah += u["D+"]
        al += u["D-"]
        gnd += u["GND"], u["OE"]
        v33 += u["VCC"]
        sel += u["S"]
        _cap(ctag, "100nF", "%s switch decoupling" % tag, v33, gnd)
        _res(rtag, "100k", "%s S pull-down: the %s arm is CAN until firmware says USB"
             % (tag, what), sel, gnd)
    for tag, net in (("D4", ped_h), ("D5", ped_l), ("D10", lev_h), ("D11", lev_l)):
        _diode(tag, "ESD5B5.0ST1G", "bus B ESD clamp, arm pin to GND (LCSC C93623)", net, gnd)
    _tps2553("U6", "pedal arm 5 V, 0.52 A", v5a, io["EN_PED"], v5_ped, io["BUSB_FAULT_N"],
             "R22", "49k9 1%", gnd)
    _tps2553("U11", "lever arm 5 V, 0.52 A", v5a, io["EN_LEV"], v5_lev, io["BUSB_FAULT_N"],
             "R35", "49k9 1%", gnd)
    for tag, net, what in (("R36", io["EN_PED"], "U6"), ("R37", io["EN_LEV"], "U11")):
        _res(tag, "100k", "%s EN pull-up: the arm is powered unless firmware says off" % what,
             v33, net)
    _res("R38", "10k", "BUSB_FAULT_N pull-up", io["BUSB_FAULT_N"], v33)
    for tag, net, val, why, fp in (("C39", v5_ped, "1uF/16V", "U6 OUT", C0402),
                                   ("C40", v5_lev, "1uF/16V", "U11 OUT", C0402),
                                   ("C41", v5a, "100nF", "U6 / U11 IN", C0402),
                                   ("C42", v5_ped, "10uF/16V", "pedal arm bulk at J15", C0805),
                                   ("C43", v5_lev, "10uF/16V", "lever arm bulk at J16", C0805)):
        _cap(tag, val, why, net, gnd, fp)
    _jst("J15", "S4B-PH-SM4-TB", "bus B, the PEDAL arm -- 5 V PH, side entry, mouth UP; "
         "its lead comes up through the instrument's floor", PH4_SIDE, harness.PH_PINOUT,
         {"V5": v5_ped, "GND": gnd, "CAN_H": ped_h, "CAN_L": ped_l})
    _jst("J16", "S4B-PH-SM4-TB", "bus B, the LEVER arm -- 5 V PH, side entry, mouth UP; "
         "its lead comes up through the instrument's floor", PH4_SIDE, harness.PH_PINOUT,
         {"V5": v5_lev, "GND": gnd, "CAN_H": lev_h, "CAN_L": lev_l})

    # ── the lights (motor_ctrl F3 + pi_cap J3 / J6): fused 24 V and the CM5's two SPIs ──────
    v24_led = Net("+24V_LED")
    v24_led.drive = Pin.drives.POWER
    _two("F3", "Fuse", "JFC1206-1300FS", "24 V fuse for the lighting bus -- a short on a 600 mm "
         "LED cable must not take the motors down", "Fuse:Fuse_1206_3216Metric", v24, v24_led)
    _cap("C44", "10uF/50V", "lighting-bus bulk after the fuse", v24_led, gnd, C1206)
    _cap("C45", "100nF/50V", "lighting-bus HF bypass", v24_led, gnd)
    sck, sdt, sck_ft, sdt_ft = Net("SCK"), Net("SDT"), Net("SCK_FOOT"), Net("SDT_FOOT")
    for ref, a, b_, what in (("R40", io["SCK_PI"], sck, "fret SCLK series source termination"),
                             ("R41", io["SDI_PI"], sdt, "fret MOSI series source termination"),
                             ("R42", io["SCK_FOOT_PI"], sck_ft, "foot SCLK series termination"),
                             ("R43", io["SDT_FOOT_PI"], sdt_ft, "foot MOSI series termination")):
        _res(ref, "68R", what + " (pi_cap's 68R)", a, b_)
    _jst("J3", "S4B-XH-SM4-TB", "to fret_led_key J1 -- 24 V and SPI0 (harness.LED_DROP)",
         XH4_SIDE, harness.LED_DROP, {"V24": v24_led, "GND": gnd, "SCK": sck, "SDT": sdt})
    _jst("J4", "S4B-XH-SM4-TB", "to foot_led_a J1 -- 24 V and SPI5 (harness.LED_DROP)",
         XH4_SIDE, harness.LED_DROP, {"V24": v24_led, "GND": gnd, "SCK": sck_ft, "SDT": sdt_ft})

    # ── J5: the UI ribbon (pi_cap's J5, same order, harness.UI_RIBBON) ────────────────────
    v33_ui = Net("+3V3_UI")
    ui_map = {"SW_A": "UI_SW_A", "SW_B": "UI_SW_B", "SW_C": "UI_SW_C", "SW_D": "UI_SW_D",
              "SW_PUSH": "UI_SW_PUSH", "ENC_A": "UI_ENC_A", "ENC_B": "UI_ENC_B",
              "SCLK": "UI_SCLK", "SDIN": "UI_SDIN", "DC": "UI_DC", "CS_N": "UI_CS_N",
              "RES_N": "UI_RES_N"}
    j5 = _part("J5", "PinHeader_2x08", "PZ1.27-2x8P", "UI board ribbon, 16-way 1.27 mm 2x8 "
               "VERTICAL, off the board face under the UI station: the top edge is all JSTs "
               "(LCSC part to pick -- open item)",
               "Connector_PinHeader_1.27mm:PinHeader_2x08_P1.27mm_Vertical",
               [Pin(num=i + 1, func=P) for i in range(16)])
    for way, sig in enumerate(harness.UI_RIBBON, start=1):
        if sig == "GND":
            gnd += j5[way]
        elif sig == "+3V3":
            v33_ui += j5[way]
        elif sig == "PWR_SW_UP":
            sw_up += j5[way]
        elif sig == "PWR_SW_DN":
            sw_dn += j5[way]
        else:
            io[ui_map[sig]] += j5[way]
    ui_flt = Net("UI_FAULT_NC")
    _tps2553("U12", "3V3 to the UI ribbon from CM5_3V3, 0.52 A", cm5_3v3, cm5_3v3, v33_ui,
             ui_flt, "R44", "49k9 1%", gnd)
    _cap("C46", "1uF/16V", "U12 OUT", v33_ui, gnd)
    _cap("C47", "100nF", "U12 IN", cm5_3v3, gnd)


# ── the board ──────────────────────────────────────────────────────────────────────────────
# NOT PLACED YET. The frame is the stretch the bench geometry leaves against the -Y wall
# (X -520..-200, Z -107.2..-37.2): 320 x 70, board X = instrument X + 360, board Y = instrument
# Z + 72.2 (the top edge 21 mm under the UI station's z -16.1: a mated XH and its wire's bend).
# The +Y edge (instrument +Z, up) carries the twelve side-entry headers, mouths up, and the
# power / logic leads from the output board; the CM5 and both bucks on the station-3 stretch.
BOARD_W, BOARD_L = 320.0, 70.0
BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 4,
    "zones": [("GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],
    "stitch_nets": ("GND",),   # exposed pads and GND pads straight to the plane
    "qty_per_instrument": 1,
    "edge_parts": {"+Y": ["J21", "J22", "J23", "J24", "J25", "J26", "J27", "J28", "J29",
                          "J30", "J15", "J16", "J10", "J12", "J11", "J3", "J4"]},
    # every JST on +Y, mouth up (lead, 2026-11-13); J5's vertical 2x8 LCSC part is open
    "placements": {},
    "open_items": [
        "DF40 pad n = CM5 pin n (J1) / n+100 (J2), pad 1 at the module's pin-1 end, J1-J2 "
        "34.4 apart (scaled off CM5 DS fig. 4): check all three against the CM5 design files",
        "CM5 5 V: U5 is 3 A (LMR33630); CM5 asks 5 A with USB loads -- measure; LMR33640 fits",
        "LM5122 OPT tied to AGND for a single-phase master -- confirm in SNVS954H",
        "L4 (10 uH / 15 A) and C113/C114 (470 uF / 35 V polymer) lands are placeholders",
        "J5: vertical 2x8 1.27 mm header (the top edge is all JSTs) -- pick the LCSC part",
        "320 x 70 at X -520..-200, Z -107.2..-37.2: branner to confirm the -Y wall stretch and "
        "the 21 mm under the UI station for the mated plugs",
        "NCEP4090GU pinout assumed PowerPAK-SO8 (1-3 S, 4 G, tab D)",
        "CM5 variant: an eMMC part (no SD socket here); four M2.5 mounting holes for it",
    ],
}


# ── quality (cadkit/PCB_QUALITY.md), first pass after br8's finish (2026-11-13) ─────────────
def _cited(values):
    """Pinout citations this board shares with the instrument's earlier boards, read from their
    own notes so the two never drift. Importing those modules builds no parts (checked: 0
    before and after). A part not found here stays UNCITED -- an A4 FAIL is the honest state
    for the DF40 land, the NCEP4090 and the LM5122 until someone reads them against the
    maker's drawing (open items)."""
    import importlib
    out = {}
    for mod in ("motor_ctrl", "output_panel", "pi_cap", "lever_sensor", "optical"):
        cited = importlib.import_module(mod).BOARD_NOTES.get("quality", {}).get("pinouts", {})
        for v in values:
            if v in cited and v not in out:
                out[v] = "as %s.py: %s" % (mod, cited[v])
    return out


_USB_HS = ("USB 2.0 high speed, 480 Mbps: 2,080 ps a bit, so skew has room; the pair stays a PAIR "
           "on one layer (differential impedance is the two conductors' geometry) and collects "
           "no more than two vias. The same budget as output_panel's hub pairs.")
BOARD_NOTES["match"] = [
    {"name": n, "max_skew_mm": 8.3, "same_layer": True, "max_vias": 2,
     "nets": ["%s_DP" % n, "%s_DM" % n], "why": w + " " + _USB_HS}
    for n, w in (("GADGET", "J13 -> the CM5's USB OTG port (the panel ports' data, via the output board)."),
                 ("OB_LINK", "J14 -> the CM5's USB3-0 2.0 lane: the output board's H743 link."),
                 ("FLASH", "the CM5's USB3-1 2.0 lane -> U9 / U10, the arm-flashing switches."))]
BOARD_NOTES["quality"] = {
    "pinouts": _cited(["NUP2105LT1G", "S4B-XH-SM4-TB", "S6B-XH-SM4-TB", "S6B-PH-SM4-TB",
                       "TYPE-C-31-M-12", "S4B-PH-SM4-TB", "PZ1.27-2x8P", "THROW", "2N7002",
                       "SQD50P06-15L", "CH32V307WCU6", "TS3USB221ARSER", "TPS2553DBVR",
                       "TCAN3413DR", "SN65HVD230DR", "LMR33630ADDAR", "LMR33630BRNXR",
                       "AP2112K-3.3TRG1", "TAXM8M4RFDCET2T"])
               | {"S6B-XH-SM4-TB": "JST eXH.pdf p.6, Header / SMT type: the same drawing as the "
                                   "4-way S4B-XH-SM4-TB (pi_cap.py's citation): No. 1 circuit is "
                                   "the right-hand post seen from above, mouth away; KiCad "
                                   "JST_XH_S6B-XH-SM4-TB keeps the 4-way's tails -Y, pad 1 -X. "
                                   "Read 2026-11-13"},
    # where each supply enters, where it goes, and the WORST-case amps (not the budget)
    "power_paths": (
        # the chargers' 5-20 V: four VIN ways (two a lead, harness.BRAIN_POWER), 2.5 A each at 10 A
        [{"net": "VIN_BRAIN", "from": "%s.%d" % (j, w), "to": ["Q2.3"], "amps": 2.5}
         for j in ("J10", "J12") for w in (1, 6)]
        + [{"net": "VIN_SW", "from": "Q2.2", "to": ["R109.1"], "amps": 10.0},     # the boost's input
           {"net": "VIN_SW", "from": "Q2.2", "to": ["R108.1"], "amps": 0.02},    # LM5122 VIN filter
           # 24 V out of the boost: 100 W, 4.5 A at the high side; ten motors, the lights, two bucks
           {"net": "+24V", "from": "Q9.5", "to": ["F3.1"], "amps": 3.0},         # the lighting bus
           {"net": "+24V", "from": "Q9.5", "to": ["R23.2"], "amps": 0.8},        # the CM5 buck's feed
           {"net": "+24V", "from": "Q9.5", "to": ["U7.2", "U7.9", "U7.10"], "amps": 0.3}]
        + [{"net": "+24V", "from": "Q9.5", "to": ["J%d.1" % k], "amps": 0.45} for k in range(21, 31)]
        + [{"net": "+24V_F", "from": "R23.1", "to": ["F1.1"], "amps": 0.8},
           {"net": "+24V_BUCK", "from": "F1.2", "to": ["U5.2"], "amps": 0.8},
           {"net": "+24V_LED", "from": "F3.2", "to": ["J3.1"], "amps": 1.5},
           {"net": "+24V_LED", "from": "F3.2", "to": ["J4.1"], "amps": 1.5},
           # the CM5's 5 V: U5's 3 A limit, through F2, onto its six 5 V pins
           {"net": "+5V_RAW", "from": "L2.2", "to": ["F2.1"], "amps": 3.0},
           {"net": "+5V_CM5", "from": "F2.2", "to": ["J1.77", "J1.79", "J1.81", "J1.83", "J1.85",
                                                    "J1.87"], "amps": 3.0},
           # +5V_AUX: the bus-B arms (TPS2553 limited) and the 3V3 LDO
           {"net": "+5V_AUX", "from": "L3.2", "to": ["U6.1"], "amps": 0.5},
           {"net": "+5V_AUX", "from": "L3.2", "to": ["U11.1"], "amps": 0.5},
           {"net": "+5V_AUX", "from": "L3.2", "to": ["U8.1", "U8.3"], "amps": 0.3},
           {"net": "+5V_BUSB_PED", "from": "U6.6", "to": ["J15.1"], "amps": 0.5},
           {"net": "+5V_BUSB_LEV", "from": "U11.6", "to": ["J16.1"], "amps": 0.5},
           {"net": "+3V3", "from": "U8.5", "to": ["U1.1", "U1.13", "U1.17", "U1.31", "U1.32",
                                                 "U1.50", "U1.51", "U1.67", "U1.68"], "amps": 0.1},
           {"net": "+3V3", "from": "U8.5", "to": ["U2.3", "U2.5", "U3.3", "U9.10", "U10.10"],
            "amps": 0.03},
           {"net": "+3V3_UI", "from": "U12.6", "to": ["J5.10"], "amps": 0.1}]),
    "not_power": {
        "PWR_GATE": "Q2's gate: R51 / R50 bias and the soft-start cap, microamps",
        "PWR_HOLD": "the CH32's hold line into Q3 through D13: a gate, microamps",
        "PWR_PULL": "Q3's drain onto the gate divider: the same microamps",
        "PWR_Q3_SRC": "Q3 in series with Q10 on the gate path: microamps",
        "PWR_SW_UP": "a throw of the power button (UI ribbon way 15): a logic level",
        "PWR_SW_DN": "the button's other throw (way 16): a logic level",
        "VCC5": "U5's internal VCC regulator pin, bypassed by C19 only: no load",
        "VCC7": "U7's internal VCC regulator pin, bypassed by C53 only: no load",
    },
    # A13: what the DESIGN leaves open
    "unconnected": {
        "J1": {"pins": "3 4 5 6 9 10 11 12 15 16 17 18 19 20 35 36 37 39 40 56 57 58 61 62 63 64 "
                       "67 68 69 70 72 73 75 76 80 82 88 89 90 91 94 95 96 97 99 100",
               "why": "CM5 pins 1-100 this carrier does not use (Ethernet, spare GPIO, SD, LEDs, "
                      "camera / display GPIO): open, as RP-008180-DS-7 allows for unused functions. "
                      "The DF40 pad = CM5 pin mapping is itself an open item"},
        "J2": {"pins": "1 2 4 6 9 10 11 12 15 16 17 18 21 22 23 24 27 28 29 30 33 35 39 40 41 42 43 "
                       "45 46 47 48 49 51 52 53 54 57 58 59 60 64 66 69 70 71 72 75 76 77 78 81 82 "
                       "83 84 87 88 89 90 93 94 95 96 99 100",
               "why": "CM5 pins 101-200 this carrier does not use (HDMI, MIPI CSI / DSI, PCIe, the "
                      "USB3 SuperSpeed lanes): open, as RP-008180-DS-7 allows"},
        "U1": {"pins": "2 3 4 8 9 10 11 14 15 16 23 25 26 27 30 37 38 40 41 42 53 54 55 58 59 60 61 62",
               "why": "GPIO this board gives no function: left open, firmware leaves it an input "
                      "with pull-down (as motor_ctrl)"},
        "J1[3-6].MP": "a side-entry JST's mounting tabs: solder only",
        "J1[0-2].MP": "a side-entry JST's mounting tabs: solder only",
        "J[34].MP": "a side-entry JST's mounting tabs: solder only",
        "J2[1-9].MP": "a side-entry JST's mounting tabs: solder only",
        "J30.MP": "a side-entry JST's mounting tabs: solder only",
        "J1[34].[AB]5": "USB-C CC1 / CC2: a data-only board-to-board link, no VBUS, nothing "
                        "negotiates -- each open on its own (A6)",
        "J1[34].[AB]8": "USB-C sideband (SBU): USB 2.0 does not use it",
        "J1[02].4": "BRAIN_POWER way 4: the lead's one empty way (harness)",
        "U3.5": "SN65HVD230 Vref output: nothing here uses the reference (as motor_ctrl)",
        "U7.8": "LMR33630 PG: open drain, not read (as optical U13.8)",
        "U8.4": "AP2112K pin 4 is the maker's NC",
        "U12.4": "TPS2553 FAULT#: open drain, the UI rail's fault is not read",
        "U20.1": "LM5122 SYNCOUT: a single-phase master syncs nothing",
        "U20.13": "LM5122 MODE: open selects the internal divider (diode emulation, skip)",
    },
    "waive": {
        "A22:J1": "the CM5's own pinout (RP-008180-DS-7): its 3V3 OUTPUT pins sit beside its 5 V "
                  "inputs on the module, and a carrier cannot reorder a DF40 it mates with",
    },
    "net_groups": [
        {"name": "ten motor drops on bus A: CAN_H and CAN_L ways on two nets, ten each",
         "pins": ["J2[1-9].[34]", "J30.[34]"], "nets": 2, "each": 10},
        {"name": "ten motor drops: the 24 V way on one net", "pins": ["J2[1-9].1", "J30.1"],
         "nets": 1, "each": 10},
        {"name": "bus B's two arms: each its own 5 V and pair", "pins": ["J1[56].[134]"],
         "nets": 6, "each": 1},
        {"name": "two LED drops: one 24 V net, each its own SPI", "pins": ["J[34].[134]"], "nets": 5},
        {"name": "three USB pairs", "nets_like": "(GADGET|OB_LINK|FLASH)_D[PM]", "count": 6},
    ],
}

if __name__ == "__main__":
    brain()
    ERC()
    net_path = os.path.join(OUT_DIR, "brain.net")
    generate_netlist(file_=net_path)
    netcheck.no_orphan_pins(net_path)
    import volts_decl                   # A16: generated by voltage_check.py --declare brain
    volts_decl.into(BOARD_NOTES, "brain")
    with open(os.path.join(OUT_DIR, "brain.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("brain netlist written; %d open items" % len(BOARD_NOTES["open_items"]))
