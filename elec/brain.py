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
And it takes the 24 V BOOST from the brain board (fill and noise -- brain_board.py J10):
the chargers' OR-ed 5-20 V arrives on J10 + J12 (harness.BRAIN_POWER, two 6-way XH in
parallel, way 3 of each strapped to GND as the presence loop) and the logic on J11
(harness.BRAIN_SIGNAL).

MOUNTING (user): on its side in the X-Z plane against the -Y wall, -Y of the motors, if --
and only if -- every motor JST faces up. EVERY JST does (lead, 2026-11-13): all seventeen are
side-entry headers on the +Z edge, mouths up -- the ten motors, each over its own station
(src.direct_bench STATION, within ~1 mm of the motor's X span: short CAN drops), the two
bus-B arms, the two LED drops and the three brain-board leads in the gaps. That is 292 mm of
courtyard, so the board is 320 long (instrument X -520..-200) and 70 tall (Z -107.2..-37.2): the
top edge sits 21 mm under the UI station's underside (z -16.1), room for a mated XH plug and
its wire's bend under the UI board. The UI ribbon (J5) is a pin header, not a JST: a VERTICAL
2x8 off the board face under the UI station.
The CM5 and the bucks sit on the station-3 stretch (66 mm free in Y); only low parts beside
station 2 (19 mm above z -54). Longer leads so it can be lifted out are acceptable.

POWER, IN THE ORDER IT HAPPENS:
  1. A charger is attached. The brain board's MCU reads it and raises BRAIN_EN (J11).
  2. Q2 -- the old output panel's P-FET switch, now on 5-20 V with a 12 V gate clamp --
     closes only when the BUTTON says on (or the CH32 holds it, see 5) AND BRAIN_EN is high.
     Its Miller cap is the soft start: the VIN inrush limit the brain board asks for.
  3. The LM5122 boost (U20, TI's SNVS954H 8.2 design) makes +24V for the motors and lights.
  4. Two 5 V bucks: U7 (+5V_AUX, always on with the 24 V) for the CH32, the transceivers and
     bus B's 5 V; U5 (+5V_CM5) for the CM5 only, held off by LOW_PWR (minimal mode, R2-6).
  5. THE CM5 SHUTS DOWN BEFORE ITS POWER GOES. When the button goes off, the CH32 holds Q2 on
     (PWR_HOLD through D13), presses the CM5's PWR_Button (Q14), waits for CM5_3.3V to fall
     (CM5_ON) and only then lets go. "Never cut a running Pi" is hardware here.
  6. PWR_BTN and BRAIN_PG go back to the brain board, open drain, ACTIVE LOW (pulled up
     there): the button reads LOW when ON; the 24 V reads LOW when GOOD.

LINKS (no CH340 any more -- the CM5 is on the board):
  * CH32 USART1 (PA9/PA10, also WCH's ROM loader) <-> CM5 UART4 (GPIO12/13), 1k series each
    way so neither back-powers the other in minimal mode. CM5 GPIO25 -> CH32 NRST, GPIO19 ->
    CH32 BOOT0: the CM5 flashes the CH32 with no tool (USB-only firmware rule).
  * J13 (USB-C) <- brain board J3: the panel ports' data to the CM5's USB 2.0 OTG (gadget,
    and rpiboot for the eMMC with nRPIBOOT held -- TP7).
  * J14 (USB-C) <- brain board J9: the H743's OTG_FS device on the CM5's USB3-0 USB2 pair.
  * The CM5's USB3-1 USB2 pair is the LEVER-FLASH LANE (docs/lever-usb-flash.md): U9/U10
    hand an arm's pair from CAN to it for one flash. It replaces motor_ctrl's U7/U8 path.

OPEN ITEMS (BOARD_NOTES["open_items"]):
  - DF40 pad numbering vs CM5 pin numbering: pad n = pin n (J1) and pin n+100 (J2) -- CLOSED
    2026-11-14 against CM5IO's KiCad files; placement and check in elec/cm5_mech.py.
  - CM5 5 V: U5 is the 3 A LMR33630 motor_ctrl fed the Pi 4B from; the CM5 asks 5 A with
    USB loads. This board hangs nothing on the CM5's USB but two data links, so 3 A should
    hold -- measure; the LMR33640 (4 A) takes the same land.
  - LM5122 OPT tied to AGND (single-phase master) -- confirm in SNVS954H.
  - L4: placeholder land (R2-6: XR181810VC / CDEP15D90).
  - (closed 2026-11-13) NCEP4090GU pinout read from NCE's sheet: brain_board.PD_PINOUTS.
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
# 22 uF at 50 V (lead, 2026-11-14): the 35 V 1210 sat at 75 % on +24 V and under the clamped 37 V
# VIN transient; no 22 uF / 50 V MLCC is stocked in 1210, so the 2220 (PSA FS55X226K500EHG, X7R)
C2220 = "Capacitor_SMD:C_2220_5750Metric"
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


def brain(merged=None):
    """The brain's circuit. merged=None: the standalone board (retired 2026-11-13, kept so
    its netlist still builds). merged={"gnd": net, "vin": net}: built ONTO THE BRAIN BOARD
    (user, 2026-11-13: "the brain board becomes the brain board"), sharing its GND and
    its VIN_BRAIN; the inter-board leads and USB links are left out (brain_board joins the
    nets this returns) and every field connector -- ten motors, both bus-B arms, both LED
    drops -- is replaced by ONE ribbon header to the connector board (harness.CONN_RIBBON),
    whose field-side parts (the far bus-A terminator, the clamps, the header bypasses) are
    connector_board.py's."""
    gnd = merged["gnd"] if merged else Net("GND")
    v24, vin_sw = Net("+24V"), Net("VIN_SW")
    vin = merged["vin"] if merged else Net("VIN_BRAIN")
    v5c = Net("+5V_CM5")
    # merged with the H743 folded in: the brain board's +3V3D (its U21) is the transceivers' and
    # switches' 3.3 V, and U8 goes -- one logic LDO for one board
    v33 = merged["v33"] if merged and "v33" in merged else Net("+3V3")
    # FOLD (user, 2026-11-13: "unify more work onto a single processor"): the brain board's
    # H743 takes the CH32's job. merged["mcu"] hands over the H743-side nets for the CH32's
    # signals (CAN1/2, the sense / power-sequencing lines, USART1 to the CM5) and its NRST /
    # BOOT0; U1, Y1, their passives and pads are left out, and the CM5 keeps R30-R33.
    fold = merged["mcu"] if merged and "mcu" in merged else None
    cm5_io = dict(CM5_IO)
    if fold:
        # the CM5 talks to the H743 over USB (OB_LINK), so the "read me" line goes; the arms'
        # CAN/USB switches move to the CM5, which runs the arm flashing (lever-usb-flash) and
        # must not depend on the H743's firmware to do it
        del cm5_io["MCU_IRQ_CM5"]
        cm5_io["SEL_PED"], cm5_io["SEL_LEV"] = 4, 7
        # SWD from the CM5 (PCB_QUALITY M43, 2026-11-17): the H743's ROM loader answers only
        # if its option bytes allow it, and a firmware that sets RDP or remaps the pins shuts
        # USART1 out. SWD connect-under-reset (NRST held by GPIO25) reaches the core whatever
        # the flash holds -- so the CM5's flasher image drives SWCLK / SWDIO on GPIO8 / GPIO9.
        if "SWDIO" in fold and "SWCLK" in fold:
            cm5_io["CM5_SWCLK"], cm5_io["CM5_SWDIO"] = 8, 9
    # merged: the brain board's own 5 V (V5_PRE, its U5 on the chargers' raw input) IS the
    # logic 5 V -- one buck for both boards' logic (user, 2026-11-13: "combining multiple 5V
    # bucks into one"), and the CH32 runs from a charger's attach, not from the boost's 24 V
    v5a = merged["v5a"] if merged and "v5a" in merged else Net("+5V_AUX")
    cm5_3v3 = Net("CM5_3V3")
    for n in (gnd, v24, vin, vin_sw, v5a, v5c, v33, cm5_3v3):
        n.drive = Pin.drives.POWER
    io = {k: Net(k) for k in dict.fromkeys(list(cm5_io) + list(CH32_IO)) if k != "BOOT1_PB2"}
    if fold:
        io.update(fold)

    # ── J10 / J12 / J11: from the brain board ─────────────────────────────────────────
    # Two 6-way XH power leads in parallel (10 A worst case at 2.5 A a way: two VIN and two GND
    # ways on each, 22 AWG: the two-gauge rule), way 3 of each STRAPPED TO GND here -- the brain board reads it as
    # "this lead is in". Then the 6-way logic lead.
    for tag in (() if merged else ("J10", "J12")):
        _jst(tag, "S6B-XH-SM4-TB", "5-20 V in from the brain board, lead %s of 2 in "
             "parallel; way 3 = the presence loop, strapped to GND" % tag[-1:],
             XH6_SIDE, harness.BRAIN_POWER, {"VIN": vin, "GND": gnd, "LEAD_SENSE": gnd},
             power=("VIN",))
    link = {k: Net("LINK_" + k) for k in ("BRAIN_EN", "LOW_PWR", "PWR_BTN", "BRAIN_PG")}
    if not merged:
        _jst("J11", "S6B-PH-SM4-TB", "logic to / from the brain board (harness.BRAIN_SIGNAL)",
             PH6_SIDE, harness.BRAIN_SIGNAL, dict(link, GND=gnd), power=())
    _cap("C1", "22uF/50V", "VIN bulk at the inlet, AHEAD of the switch", vin, gnd, C2220)
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
    _small("Q10", "power-switch driver: BRAIN_EN from the brain board", mid,
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
    # the button, back out to the brain board: open drain, LOW = ON
    btn_g = Net("BTN_OUT_G")
    _res("R57", "10k", "Q12 gate from the button sense", sw_sense, btn_g)
    _res("R58", "100k", "Q12 gate down", btn_g, gnd)
    _small("Q12", "PWR_BTN to the brain board, open drain: LOW = the button says ON",
           link["PWR_BTN"], btn_g, gnd)
    # folded, the H743 that drives LOW_PWR and reads PWR_BTN is the same MCU these fed, and it
    # reads +24V itself (SENSE_24V): the second copies of the button / LOW_PWR and the
    # BRAIN_PG report go
    if not fold:
        _res("R59", "10k", "the button as J11 carries it, into the CH32 (pulled up at the "
             "brain board)", link["PWR_BTN"], io["BTN_IN"])
        _res("R60", "10k", "LOW_PWR as J11 carries it, into the CH32", link["LOW_PWR"],
             io["LOW_PWR_IN"])
    _res("R61", "100k", "LOW_PWR down: full mode with the lead out", link["LOW_PWR"], gnd)
    if not fold:
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
    # Coilank APS1513M100F (LCSC C49261410, 186 in stock 2026-11-17; AAPS1513M100F C49261563 is
    # a second listing, 179): the Bourns SRP1513CA-100M's clone, 10 uH, Isat 30 A at a 30 % drop,
    # Irms 19 A at a 20 C rise, 7 mohm max (Bourns SRP1513CA p.1) against a 13.8 A worst-case
    # peak x 1.3 = 17.9 A (prices.json's derivation). It replaces the SRP1770TA-100M, which LCSC
    # had none of (global sourcing / consigned, 2026-11-13): the search then was held to 17 x 17;
    # this one is SMALLER (16.5 x 15.5 x 7.0), so it lands inside the old outline, pads on X.
    _two("L4", "L", "APS1513M100F", "boost inductor, Coilank APS1513M100F = Bourns SRP1513CA-100M "
         "(LCSC C49261410): 10 uH, Isat 30 A, Irms 19 A, shielded",
         "Steel:L_Bourns_SRP1513CA_15.5x16.5mm", b["LMID"], b["SW"])
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
    # CHECKED AT 5 V IN (lead, 2026-11-17: U20's UVLO is 4.49 V, so a 5 V-only source can run
    # the boost). D = 0.79; at a 5 V / 3 A source's 13.5 W out, Rload 43 R. Above the power
    # pole the loop is (1-D) R106 / (2 pi A Rs Cout Rtop), A = 10 (SNVS954H p.11), Cout ~715 uF
    # (5 x 22 uF at 50 % + 2 x 330 uF): fc ~1.5 kHz (3.7 kHz at 12 V in). RHPZ (1-D)^2 R /
    # (2 pi L) = 29 kHz, 19x above it. Phase at fc: integrator -90, zero R106/C102 at 106 Hz
    # +86, power pole (10 Hz) -90, C103's pole at 7.1 kHz -12, RHPZ -3, ESR zero (24 kHz) +4:
    # -105, so ~75 degrees of margin. Slope: eq. 6 with R107 gives K = 1.0 at 9 V and 1.3 at
    # 4.5 V (over the 0.5 floor, a little over-compensated -- a slower loop, not a less stable one).
    _res("R106", "68k1 1%", "COMP series R (TI's: crossover ~5.3 kHz)", b["COMP"], b["COMPMID"])
    _cap("C102", "22nF/50V", "COMP series C", b["COMPMID"], b["FB"])
    _cap("C103", "330pF/50V", "COMP high-frequency C", b["COMP"], b["FB"])
    _res("R107", "100k", "SLOPE: K ~ 1 at the lowest input (TI's)", b["SLOPE"], gnd)
    _cap("C100", "100nF", "soft-start, ~12 ms", b["SS"], gnd)
    _cap("C101", "470nF/25V", "hiccup restart timer (TI's)", b["RES"], gnd)
    # HOW MANY (lead, 2026-11-14: re-derived when the 22 uF went 50 V 2220). The 50 V X7R 2220
    # keeps far more of its 22 uF at these voltages than the 35 V X5R 1210 did; taken as 50 %
    # at 24 V and 70 % at 20 V (ASSUMED: PSA publishes no DC-bias curve -- measure one).
    # IN: a boost's input current is continuous, ripple dIL = 2.4 A worst (12 V in, D 0.5,
    # 10 uH, 250 kHz) -> 0.69 A RMS; for 50 mV, C >= dIL / (8 fsw dV) = 24 uF: two (30 uF at
    # 20 V). OUT: the pulsed current, Iout D / (fsw dV) = 4.5 x 0.625 / (250 k x 0.24 V) = 47 uF
    # for 1 % ripple from the ceramics ALONE (the polymers carry the RMS): five (55 uF).
    for k in range(2):
        _cap("C%d" % (92 + k), "22uF/50V", "boost input bulk, after Q2", vin_sw, gnd, C2220)
    _cap("C96", "100nF/50V", "VIN_SW HF bypass at the boost", vin_sw, gnd)
    for k in range(5):
        _cap("C%d" % (105 + k), "22uF/50V", "boost output ceramic, ahead of the polymers "
             "(TI: ceramics first)", v24, gnd, C2220)
    for tag in ("C113", "C114"):
        # 50 V (2026-11-14): the SMCJ26A rail reaches 37.6 V; two carry 7 A of ripple against
        # the ~5.8 A RMS at 9 V in (Iout sqrt(D / (1 - D)))
        _cap(tag, "330uF/50V", "boost output bulk, polymer, jieerrui MA50V330M10X12: 3.5 A ripple, "
             "20 mOhm; 10 mm base on the 10x10.5 land, 12.5 mm TALL (LCSC C53120968)", v24, gnd,
             "Capacitor_SMD:CP_Elec_10x10.5")
    _cap("C115", "100nF/50V", "+24V HF bypass", v24, gnd)
    # SMCJ26A (lead, 2026-11-14): the 24A's 24 V stand-off sat under the 26.4 V steady figure;
    # the 26A reaches 37.6 V at the 20 A surge bound (the 28A: 41.1 V, over the LMR33630s' 38 V)
    _diode("D3", "SMCJ26A", "+24V clamp, 1.5 kW -- ten stepper drivers' kick lands here",
           v24, gnd, "Diode_SMD:D_SMC")

    # ── U7: +5V_AUX -- the buck cell (brain_board's U5), always on with the 24 V ───────────
    # Feeds what must run in MINIMAL mode: the CH32 (via U8), the transceivers, bus B's 5 V.
    # motor_ctrl took bus B's 5 V off the Pi's rail; minimal mode turns that rail off.
    if not (merged and "v5a" in merged):
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
    if not (merged and "v33" in merged):
        u8 = _fix("U8", "AP2112K-3.3TRG1", "+5V_AUX -> +3V3 for the CH32, the transceivers, the "
                  "switches (LCSC C51118)", "Package_TO_SOT_SMD:SOT-23-5", range(1, 6))
        v5a += u8[1], u8[3]
        gnd += u8[2]
        Net("U8_NC_4").connect(u8[4])
        v33 += u8[5]
        _cap("C57", "1uF", "U8 input", v5a, gnd)
        _cap("C58", "10uF", "+3V3 bulk", v33, gnd, C0805)

    # ── U5: +5V_CM5 -- A BUCK-BOOST FROM THE CHARGERS' OWN INPUT (M43, lead 2026-11-17) ──────
    # ⚠ THE CM5 MUST COME UP FROM A PC's 5 V WITH EVERY FIRMWARE BLANK (cadkit PCB_QUALITY M43:
    # power and enables are part of the flashing path). The LMR33630 here was a buck off the
    # +24 V -- the boost's output, which runs only after U1's firmware raises BRAIN_EN -- so a
    # factory board had no path into the CM5 at all. And a buck cannot make the CM5's 4.75 V
    # floor (datasheet RP-008180-DS-7 s3.1) from a PC port's 4.75 V less a cable. So: a
    # 4-switch buck-boost on VIN_BRAIN (the chargers' OR-ed input, 4-20 V), enabled EITHER by
    # VIN_SW (the normal path: button AND BRAIN_EN closed Q2) OR by FLASH (the board's
    # hardware flash mode, brain_board.py: a PC on the bottom service port). It also lifts the CM5's
    # supply from 3 A to the 5 A it asks.
    # TPS552892-Q1, NOT the TPS55288 (same family): the TPS55288 resets with its output OFF
    # until an I2C write (OE bit, "Output disabled (Default)") -- nothing can write it on a
    # blank board. And not the TPS552882: its buck side drives two EXTERNAL FETs (DR1H/DR1L).
    # This one is fully integrated and set by resistors alone (TI SLVSGT7, Table 5-1).
    v5_bb, v5_raw, v5_sw = Net("+5V_BB"), Net("+5V_RAW"), Net("+5V_SW")
    for n in (v5_bb, v5_raw, v5_sw):
        n.drive = Pin.drives.POWER
    sw1, sw2, boot1, boot2 = Net("SW5_1"), Net("SW5_2"), Net("BOOT5_1"), Net("BOOT5_2")
    vcc5, fb5, en5, comp5, comp5_z, fsw5 = (Net("VCC5"), Net("FB5"), Net("EN5"), Net("COMP5"),
                                           Net("COMP5_Z"), Net("FSW5"))
    vin_f = Net("VIN_CM5")
    _two("F1", "Fuse", "JFC1206-1400FS", "4 A 63 V: a shorted U5 must not take VIN_BRAIN down "
         "(25 W at a 9 V contract is 3.1 A in)", "Fuse:Fuse_1206_3216Metric", vin, vin_f)
    u5 = _part("U5", "TPS552892-Q1", "TPS552892QWRYQRQ1",
               "36 V 8 A fully integrated buck-boost, VIN_BRAIN 4-20 V -> 5.19 V for the CM5; "
               "resistor-set, no I2C (LCSC C22375748; TI SLVSGT7)",
               "Steel:Texas_RYQ0021B_VQFN-HR-21_3x5mm_P0.5mm",
               [Pin(num=n, func=P) for n in range(1, 22)])
    en5 += u5[1]                               # EN/UVLO: 1.15 V logic high, 1.23 V UVLO
    gnd += u5[2]                               # MODE low: auto PFM at light load (not floating)
    io["PG_5V"] += u5[3]                       # PG: open drain, high at 95 % of 5.19 V
    Net("U5_NC_CC").connect(u5[4])             # CC: constant-current flag, unused
    gnd += u5[5]                               # DITH/SYNC to ground: no dithering
    fsw5 += u5[6]
    vin_f += u5[7]
    sw1 += u5[8]
    gnd += u5[9], u5[17]                       # PGND, AGND
    sw2 += u5[10]
    v5_bb += u5[11], u5[12]                    # VOUT and ISP: the sense resistor follows
    v5_raw += u5[13]                           # ISN
    fb5 += u5[14]
    comp5 += u5[15]
    Net("U5_NC_CDC").connect(u5[16])           # CDC floating: no cable-droop lift (SLVSGT7 6.5)
    vcc5 += u5[18], u5[21]                     # VCC, and EXTVCC high: the internal LDO
    boot2 += u5[19]
    boot1 += u5[20]
    _two("L2", "L", "FXL0630-4R7-M", "4.7 uH, Isat 9 A, 33 mOhm, 7 x 6.6 (LCSC C167220): worst "
         "peak 6.25 A (20 V in, 5 A out, L -20 %, 400 kHz)", "Inductor_SMD:L_Changjiang_FXL0630",
         sw1, sw2)
    for tag in ("C16", "C17"):
        _cap(tag, "10uF/50V", "buck-boost input bulk", vin_f, gnd, C1206)
    _cap("C18", "220nF/50V", "buck-boost input HF bypass, at VIN / PGND", vin_f, gnd, C0603)
    _cap("C19", "4u7/10V", "VCC: more than 4.7 uF required (pin table)", vcc5, gnd, C0603)
    _cap("C20", "100nF", "BOOT1 to SW1 (pin table: 0.1 uF)", boot1, sw1)
    _cap("C123", "100nF", "BOOT2 to SW2 (pin table: 0.1 uF)", boot2, sw2)
    for tag in ("C21", "C22", "C31", "C32"):
        _cap(tag, "22uF/25V", "5 V output bulk, ~66 uF effective at 5 V", v5_bb, gnd, C1206)
    _res("R113", "10mR 1%", "ISP-ISN output current sense: 50 mV limit / 10 mR = 5.0 A (SLVSGT7 "
         "8.2.2.6); keeps the inductor under Isat in a fault", v5_bb, v5_raw,
         "Resistor_SMD:R_1206_3216Metric")
    _res("R10", "100k 1%", "5 V feedback divider, top", v5_bb, fb5)
    _res("R11", "30k1 1%", "5 V feedback divider, bottom -- 1.2 x (1 + 100/30.1) = 5.19 V: "
         "~5.05 V at the module at 5 A after R113 and F2", fb5, gnd)
    _res("R112", "49k9 1%", "FSW: 400 kHz (SLVSGT7 8.2.2.1)", fsw5, gnd)
    # compensation, boost mode at 4.0 V in (the flash case), 1.2 A, 66 uF, fc 15 kHz (fRHPZ/5):
    # RC = 2pi Vout Rsense Cout fc / ((1-D) Vref Gea) = 10.1 k; CC = Rload Cout / (2 RC) = 14 nF;
    # CP = Resr Cout / RC = 20 pF (SLVSGT7 eq. 24-26, Gea 190 uA/V, Rsense 0.055)
    _res("R114", "10k", "COMP zero resistor (RC)", comp5, comp5_z)
    _cap("C124", "15nF", "COMP zero capacitor (CC)", comp5_z, gnd)
    _cap("C125", "22pF", "COMP high-frequency pole (CP)", comp5, gnd)
    # EN: the NORMAL path is a UVLO divider off VIN_SW -- 1.23 x (1 + 100/23.2) = 6.53 V -- so
    # the CM5 runs only when Q2 has closed (button AND BRAIN_EN); Q15 holds it off in MINIMAL.
    # C126 makes the turn-on ~100 ms after VIN_SW rises: the HANDOVER from flash mode drops
    # FLASH (EN falls at once) and U21's 225 R discharge empties the module's rail before EN
    # comes back -- so the CM5 sees a real power cycle and re-samples a released nRPIBOOT.
    _res("R12", "100k 1%", "EN/UVLO divider, top -- normal turn-on at 6.53 V on VIN_SW", vin_sw, en5)
    _res("R13", "23k2 1%", "EN/UVLO divider, bottom", en5, gnd)
    _cap("C126", "4u7/10V", "EN delay: tau 88 ms (18.8 k x 4.7 uF) -- the handover off-time",
         en5, gnd, C0603)
    flash = merged.get("flash") if merged else None
    nrpiboot_n = Net("CM5_nRPIBOOT")                 # the module's pin 93, wired below
    if flash is not None:
        # FLASH (brain_board's U39, push-pull 3.3 V) holds EN on through D21. R117 bounds the
        # current so Q16 can overrule it: (3.3 - 0.3) / 1k = 3 mA, and EN still sits at
        # 3.0 x 23.2 / 24.2 = 2.9 V over the 1.23 V UVLO with R13 below it.
        fl_d = Net("FLASH_EN_D")
        _res("R117", "1k", "FLASH -> D21: bounded so Q16's pulse wins", flash, fl_d)
        _diode("D21", "BAT54WS", "FLASH -> EN: flash mode turns the CM5's supply on whatever "
               "U1 drives (LCSC C124205)", en5, fl_d, "Diode_SMD:D_SOD-323")
        # ⚠ A REAL POWER CYCLE ON EVERY FLASH ENTRY. nRPIBOOT is sampled only at the CM5's
        # power-up (RP-008180-DS-7: low within 2 ms of 5 V), so a PC plugged in while the
        # module runs would find its OS, not the ROM's usbboot. FLASH's rising edge, through
        # C128 into Q16's gate, holds EN LOW for 470 k x 1 uF x ln(3.3 / Vth): 130 ms at the
        # 2.5 V worst Vth, ~340 typical -- U221's 225 R discharge empties the module's rail in
        # ~50 ms -- and EN then comes
        # up through D21 with nRPIBOOT already held (Q17). R118 drains the gate after.
        pulse = Net("FLASH_PULSE")
        _cap("C128", "1uF", "FLASH edge -> Q16 gate: the power-cycle pulse", flash, pulse)
        _res("R118", "470k", "Q16 gate down: the pulse's length, 130-340 ms", pulse, gnd)
        _small("Q16", "flash entry: holds U5's EN low >= 130 ms, so the CM5 power-cycles into "
               "usbboot", en5, pulse, gnd)
        _small("Q17", "flash mode: holds the CM5's nRPIBOOT low (its own 10k pull-up to "
               "CM5_3V3) -- the ROM boots from USB, whatever the eMMC holds", nrpiboot_n, flash, gnd)
    lp_g = Net("LOWPWR_G")
    _res("R16", "10k", "Q15 gate from LOW_PWR", link["LOW_PWR"], lp_g)
    _res("R17", "100k", "Q15 gate down", lp_g, gnd)
    _small("Q15", "MINIMAL mode: holds U5's EN low, the CM5 stays off (LOW_PWR is clamped low "
           "in flash mode, brain_board)", en5, lp_g, gnd)
    # U21: the module's rail behind a switch WITH AN OUTPUT DISCHARGE, on the same EN: the
    # handover's power cycle is the discharge's, sized not guessed -- 225 R x ~100 uF = 22 ms,
    # under 0.5 V in ~50 ms, inside C126's ~100 ms off-time.
    u21 = _part("U21", "TPS22965", "TPS22965DSGR", "+5V_CM5 load switch, 6 A, 16 mOhm, QOD "
                "225 R (TI TPS22965 datasheet; LCSC C122837)",
                "Package_SON:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",
                [Pin(num=n, func=P) for n in range(1, 10)])
    v5_raw += u21[1], u21[2]
    en5 += u21[3]                              # ON: VIH 1.1 V, VIL 0.5 V
    v33 += u21[4]                              # VBIAS from +3V3D: the QOD works with U5 off
    gnd += u21[5], u21[9]
    Net("U21_NC_CT").connect(u21[6])           # CT floating: fastest rise
    # VOUT is pins 7 AND 8 (SLVSBJ0F p.4 s6 DSG top view: 1/2 VIN, 7/8 VOUT). Pad 8 sat on GND
    # until 2026-11-18 -- a dead short from +5V_SW to ground the moment the switch closed.
    v5_sw += u21[7], u21[8]
    _cap("C127", "1uF", "U21 VBIAS bypass", v33, gnd)
    # +5V_RAW had no capacitor at all (quality A2, mV22): the bulks sit on +5V_BB, behind
    # R113. TI characterises the switch with CIN = 1 uF (SLVSBJ0F 6.6-6.7); at its VIN pins.
    _cap("C129", "1uF", "U21 VIN bypass, after the sense resistor", v5_raw, gnd)
    _two("F2", "Fuse", "JFC1206-1400FS", "4 A 63 V: 5 V output fuse -- the element D9 blows "
         "when U5 fails short", "Fuse:Fuse_1206_3216Metric", v5_sw, v5c)
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
    for name, g in cm5_io.items():
        cnet(io[name], GPIO[g])
    pwrbut, nrpiboot, led_act = Net("CM5_PWR_BUT"), nrpiboot_n, Net("CM5_LED_nACT")
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
    # merged with a hub (brain_board: the CH334P on this lane feeds the arms' flash switches
    # AND the bottom service port): the CM5's USB3-1 pair is the hub's upstream, and FLASH_D*
    # is one of its downstream ports
    hub = bool(merged and merged.get("hub"))
    hu_p, hu_n = (Net("HUBU_DP"), Net("HUBU_DM")) if hub else (fl_p, fl_n)
    cnet(hu_p, CM5_PIN["USB3_1_DP"])
    cnet(hu_n, CM5_PIN["USB3_1_DM"])
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

    # ── J13 / J14: the two USB links from the brain board ───────────────────────────────
    for tag, (dp, dm), what in (() if merged else (
            ("J13", (otg_p, otg_n), "the panel ports' data -> the CM5's "
             "USB 2.0 OTG (gadget; rpiboot) -- from brain board J3"),
            ("J14", (lnk_p, lnk_n), "the brain board's H743 (OTG_FS "
             "device) -> the CM5's USB3-0 USB2 pair -- from output J9"))):
        j = _usbc(tag, what)
        gnd += j["A1"], j["A12"], j["B1"], j["B12"], j["SH"]
        Net("%s_VBUS_NC" % tag).connect(j["A4"], j["B4"], j["A9"], j["B9"])
        # CC1 / CC2 left OPEN, each on its own: a data-only C-to-C link with no VBUS, so
        # nothing negotiates. Tying them (as before) is the A6 trap: an e-marked cable's Ra
        # would sit across both.
        dp += j["A6"], j["B6"]
        dm += j["A7"], j["B7"]

    # ── U1: THE CH32V307 -- motor_ctrl's MCU and wiring (gone when the H743 takes its job) ──────────────────────────────────
    if not fold:
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
    # the CM5 link: 1k in every line, so a powered side never feeds an unpowered one. Folded,
    # the same four land on the H743: USART1 PA9 / PA10 (a ROM-loader port, AN2606) and NRST /
    # BOOT0 -- the CM5 can always force the H743 into its ROM loader (PCB_QUALITY M43).
    tgt = "H743" if fold else "CH32"
    lk = [("R30", "CM5_TX", "MCU_RX", "CM5 UART4 TX -> %s USART1 RX" % tgt),
          ("R31", "MCU_TX", "CM5_RX", "%s USART1 TX -> CM5 UART4 RX" % tgt),
          ("R32", "CM5_MCU_RST", "NRST", "CM5 GPIO25 -> %s NRST" % tgt),
          ("R33", "CM5_MCU_BOOT", "BOOT0", "CM5 GPIO19 -> %s BOOT0" % tgt)]
    if not fold:
        lk.append(("R34", "MCU_IRQ", "MCU_IRQ_CM5", "CH32 PA8 -> CM5 GPIO4"))
    if "CM5_SWCLK" in cm5_io:
        lk += [("R115", "CM5_SWCLK", "SWCLK", "CM5 GPIO8 -> H743 SWCLK (PA14)"),
               ("R116", "CM5_SWDIO", "SWDIO", "CM5 GPIO9 <-> H743 SWDIO (PA13)")]
    for ref, a, b_, what in lk:
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
    if not merged:
        _res("R6", "120R", "bus A termination at the row's far end, 1% -- place past J25 (motor 5, the -X end)", a_h,
             a_l, "Resistor_SMD:R_0603_1608Metric")
        d2 = _fix("D2", "NUP2105LT1G", "bus A clamp: CAN_H and CAN_L to GND, 24 V stand-off",
                  SOT23, range(1, 4))
        a_h += d2[1]
        a_l += d2[2]
        gnd += d2[3]
    for k in (() if merged else range(10)):
        _jst("J%d" % (21 + k), "S4B-XH-SM4-TB",
             "motor %d (string %d) -- SERVO42D: 24 V + bus A, side entry, mouth UP"
             % (k + 1, k + 1), XH4_SIDE, harness.XH_PINOUT,
             {"V24": v24, "GND": gnd, "CAN_H": a_h, "CAN_L": a_l})
    # A2: a 24 V bypass at the row, one per neighbouring pair of motor headers (within 25 mm of
    # each): a stepper driver's chopper edges come back down its lead, and the boost's output
    # caps sit up to 250 mm away at the +X end. The SERVO42D carries its own bulk; these are
    # the board-side HF return, not a reservoir.
    for tag, pair in (() if merged else (("C116", "J25"), ("C117", "J24 / J26"), ("C118", "J30 / J21"),
                      ("C119", "J23 / J27"), ("C120", "J29"), ("C121", "J22 / J28"))):
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
    for tag, net in (() if merged else (("D4", ped_h), ("D5", ped_l), ("D10", lev_h), ("D11", lev_l))):
        _diode(tag, "ESD5B5.0ST1G", "bus B ESD clamp, arm pin to GND (LCSC C93623)", net, gnd)
    # AT THE SWITCHES (lead, 2026-11-14): the arms' own clamps (ESD5B5.0, on the connector board
    # when merged) break down as high as 7.8 V, over U9 / U10's 7 V I/O. A deep-snapback pair
    # right at each switch's arm pins holds an IEC 8 kV hit to 4.32 V by 30 ns and 3.3 V at
    # 8 A TLP (Nexperia PESD2USB5UX Fig. 10, Table 7), 0.47 pF -- nothing to a full-speed USB
    # or CAN pair. 1 K1, 2 K2, 3 common anode
    for tag, (h, l), what in (("D19", (ped_h, ped_l), "U9"), ("D20", (lev_h, lev_l), "U10")):
        d = _fix(tag, "PESD2USB5UX", "bus B clamp at %s's arm pins: 2-line, 5 V stand-off, "
                 "deep snapback, 0.47 pF (Nexperia, LCSC C3709087)" % what, SOT23, range(1, 4))
        h += d[1]
        l += d[2]
        gnd += d[3]
    _tps2553("U6", "pedal arm 5 V, 0.52 A", v5a, io["EN_PED"], v5_ped, io["BUSB_FAULT_N"],
             "R22", "49k9 1%", gnd)
    _tps2553("U11", "lever arm 5 V, 0.52 A", v5a, io["EN_LEV"], v5_lev, io["BUSB_FAULT_N"],
             "R35", "49k9 1%", gnd)
    for tag, net, what in (("R36", io["EN_PED"], "U6"), ("R37", io["EN_LEV"], "U11")):
        _res(tag, "100k", "%s EN pull-up: the arm is powered unless firmware says off" % what,
             v33, net)
    _res("R38", "10k", "BUSB_FAULT_N pull-up", io["BUSB_FAULT_N"], v33)
    _arm_caps = [("C39", v5_ped, "1uF/16V", "U6 OUT", C0402),
                 ("C40", v5_lev, "1uF/16V", "U11 OUT", C0402),
                 ("C41", v5a, "100nF", "U6 / U11 IN", C0402)]
    if not merged:                     # the arms' bulk sits at their headers: the connector board's
        _arm_caps += [("C42", v5_ped, "10uF/16V", "pedal arm bulk at J15", C0805),
                      ("C43", v5_lev, "10uF/16V", "lever arm bulk at J16", C0805)]
    for tag, net, val, why, fp in _arm_caps:
        _cap(tag, val, why, net, gnd, fp)
    if not merged:
        _jst("J15", "S4B-PH-SM4-TB", "bus B, the PEDAL arm -- 5 V PH, side entry, mouth UP; "
             "its lead comes up through the instrument's floor", PH4_SIDE, harness.PH_PINOUT,
             {"V5": v5_ped, "GND": gnd, "CAN_H": ped_h, "CAN_L": ped_l})
        _jst("J16", "S4B-PH-SM4-TB", "bus B, the LEVER arm -- 5 V PH, side entry, mouth UP; "
             "its lead comes up through the instrument's floor", PH4_SIDE, harness.PH_PINOUT,
             {"V5": v5_lev, "GND": gnd, "CAN_H": lev_h, "CAN_L": lev_l})

    # ── the lights (motor_ctrl F3 + pi_cap J3 / J6): fused 24 V and the CM5's two SPIs ──────
    v24_led = Net("+24V_LED")
    v24_led.drive = Pin.drives.POWER
    # 3 A: at or under the lights' FOUR ribbon ways x 1 A (harness.CONN_RIBBON; 0.8 A each
    # derated = 3.2 A) and over their 1.70 A full-white draw (docs/lighting-bus.md)
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
    if not merged:
        _jst("J3", "S4B-XH-SM4-TB", "to fret_led_key J1 -- 24 V and SPI0 (harness.LED_DROP)",
             XH4_SIDE, harness.LED_DROP, {"V24": v24_led, "GND": gnd, "SCK": sck, "SDT": sdt})
        _jst("J4", "S4B-XH-SM4-TB", "foot light out -- 24 V and SPI5 (harness.LED_DROP); its board is re-authored for the direct body when wanted (foot_led_a left with v1, main 246f34fe)",
             XH4_SIDE, harness.LED_DROP, {"V24": v24_led, "GND": gnd, "SCK": sck_ft, "SDT": sdt_ft})
    else:
        # ── THE CONNECTOR RIBBON: every field connector is on the connector board now ──
        # The motors' 24 V leaves through its own fuse: a crushed ribbon or a shorted motor
        # lead must open here, not in one 30 AWG wire (four in parallel carry ~4 A).
        v24_rib = Net("+24V_RIB")
        v24_rib.drive = Pin.drives.POWER
        # 2920L200/60: 2 A hold / 4 A trip at 60 V (2026-11-14). The rail clamp (SMCJ26A) reaches
        # 37.6 V and no 2920 PPTC holds 3 A above 36 V; 2 A is five times the ten motors' measured
        # draw moving (~0.9 W each) and the 4 A trip is the four 30 AWG ways' ~1 A each. Their
        # sub-second step peaks are NOT measured (open item) -- a PPTC rides those out
        _two("F4", "Fuse", "2920L200/60GR", "the motors' 24 V onto the connector ribbon: "
             "4 x 30 AWG at ~1 A each; PPTC 2 A hold / 4 A trip, 60 V", "Fuse:Fuse_2920_7451Metric",
             v24, v24_rib)
        _cap("C122", "10uF/50V", "ribbon 24 V bulk, after F4", v24_rib, gnd, C1206)
        _jst("J40", "A127M05-0B30P51-H10A40", "the CONNECTOR BOARD ribbon, 30-way 1.27 mm 2x15 IDC "
             "(harness.CONN_RIBBON): motors' 24 V, the lights' 24 V, bus A, both arms (CAN or "
             "the flash lane) with their 5 V, both LED SPIs (JXTCONN, LCSC C41427104: SMD, 1 A per contact)",
             "Connector_PinHeader_1.27mm:PinHeader_2x15_P1.27mm_Vertical_SMD", harness.CONN_RIBBON,
             {"V24": v24_rib, "V24L": v24_led, "GND": gnd, "CANA_H": a_h, "CANA_L": a_l,
              "PED_H": ped_h, "PED_L": ped_l, "LEV_H": lev_h, "LEV_L": lev_l,
              "V5_PED": v5_ped, "V5_LEV": v5_lev, "SCK": sck, "SDT": sdt,
              "SCK_FOOT": sck_ft, "SDT_FOOT": sdt_ft},
             power=("V24", "V24L", "V5_PED", "V5_LEV"))

    # ── J5: the UI ribbon (pi_cap's J5, same order, harness.UI_RIBBON) ────────────────────
    v33_ui = Net("+3V3_UI")
    ui_map = {"SW_A": "UI_SW_A", "SW_B": "UI_SW_B", "SW_C": "UI_SW_C", "SW_D": "UI_SW_D",
              "SW_PUSH": "UI_SW_PUSH", "ENC_A": "UI_ENC_A", "ENC_B": "UI_ENC_B",
              "SCLK": "UI_SCLK", "SDIN": "UI_SDIN", "DC": "UI_DC", "CS_N": "UI_CS_N",
              "RES_N": "UI_RES_N"}
    # ⚠ NOT "PZ1.27-2x8P" (2026-11-13): fab.py maps that value to C22438114, the family's
    # RIGHT-ANGLE header (ui_board / pi_cap) -- this footprint is the vertical one, so it
    # would have been ordered wrong. The straight part is the same family's ZZ.
    j5 = _part("J5", "PinHeader_2x08", "PZ1.27-2x8P ZZ", "UI board ribbon, 16-way 1.27 mm 2x8 "
               "VERTICAL THT, off the board face under the UI station: the top edge is all JSTs "
               "(HX PZ1.27-2x8P ZZ, LCSC C22438123)",
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
    # ⚠ THE UI RIBBON'S 3V3 HAS A CAP AT THE HEADER (brain_board mP0 quality A2: J205 +3V3_UI's
    # nearest cap was C246 at 54.4 mm, its switch's output, against 25 mm). The ribbon's far end
    # is the UI board; this end gets its own 100 nF so the header pin is not fed down a trace.
    _cap("C59", "100nF", "+3V3_UI at the UI header J5", v33_ui, gnd)
    return {"link": link, "gadget": (otg_p, otg_n), "oblink": (lnk_p, lnk_n),
            "hubu": (hu_p, hu_n), "flash_lane": (fl_p, fl_n)}


# ── the board ──────────────────────────────────────────────────────────────────────────────
# NOT PLACED YET. The frame is the stretch the bench geometry leaves against the -Y wall
# (X -520..-200, Z -107.2..-37.2): 320 x 70, board X = instrument X + 360, board Y = instrument
# Z + 72.2 (the top edge 21 mm under the UI station's z -16.1: a mated XH and its wire's bend).
# The +Y edge (instrument +Z, up) carries the twelve side-entry headers, mouths up, and the
# power / logic leads from the brain board; the CM5 and both bucks on the station-3 stretch.
BOARD_W, BOARD_L = 320.0, 70.0
BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 4,
    "zones": [("GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],
    "stitch_nets": ("GND",),   # exposed pads and GND pads straight to the plane
    # heights a footprint does not tell (cadkit place_intent.part_height reads these for the
    # station-2 height zone; branner's CAD reads them for the bodies): the boost's polymer
    # caps are jieerrui MA35V470M10X13 -- 13 mm on a 10 mm land (MA series datasheet p.4)
    # Max seated heights from each maker's drawing (read 2026-11-13), because board_geom's
    # HEIGHT has no row for these footprints and the zone must not let them in unmeasured.
    "part_heights": {
        "C113": 12.5, "C114": 12.5,   # jieerrui MA50V330M10X12: 12.5 mm seated max (JLCPCB attributes, C53120968)
        "D1": 1.10,      # SMF24A (Jingdao, C169430): SOD-123FL outline dim A 0.9-1.1, "SMF5.0A~SMF440A-200W" 2020.10 p.4
        "D13": 1.10,     # BAT54WS: SOD323 dim A2 1.00-1.10 (Diodes DS30098 Rev. 14-2, package outline)
        "L3": 4.0,       # SWPA5040S4R7MT: C max 4.0 (Sunlord SWPA catalogue p.2, Shape and Dimensions)
        "L4": 7.3,       # APS1513M100F / SRP1513CA: 7.0 +- 0.3 (Bourns SRP1513CA p.1, Product Dimensions)
        "Q8": 1.10, "Q9": 1.10,       # NCEP4090GU: DFN5X6-8L(G) dim A 0.90-1.10 (NCE V4.0 p.5)
        "R109": 0.88,    # PA2512FKF7W0R004E: H 0.63 +- 0.25 (Yageo PA_E 2512 spec V.10 p.4, Table 1)
        "J5": 5.3,       # HX PZ1.27-2x8P ZZ: 1.00 plastic + 3.90 pin, +-0.2 each (Hanxia drawing p.1, C22438123)
        "U20": 1.10,     # LM5122 PWP0020A: 1.1 MAX (TI SNVS954H, mechanical data PWP0020A)
    },
    "qty_per_instrument": 1,
    "edge_parts": {"+Y": ["J21", "J22", "J23", "J24", "J25", "J26", "J27", "J28", "J29",
                          "J30", "J15", "J16", "J10", "J12", "J11", "J3", "J4"]},
    # every JST on +Y, mouth up (lead, 2026-11-13); J5's vertical 2x8 LCSC part is open
    "placements": {},
    "open_items": [
        "DF40 placement: CLOSED 2026-11-14 on the merged brain board -- read off CM5IO "
        "(RP-008099-DD-1): 34.0 apart, pad 1 at the module's +Y end, odd column -X; "
        "elec/cm5_mech.py places it and checks the routed board",
        "CM5 5 V: U5 is 3 A (LMR33630); CM5 asks 5 A with USB loads -- measure; LMR33640 fits",
        "LM5122 OPT tied to AGND for a single-phase master -- confirm in SNVS954H",
        "L4 (10 uH / 15 A) land is a placeholder; the 2220 X7R DC-bias retention (50 % at 24 V) the boost cap counts assume is not measured",
        "320 x 70 at X -520..-200, Z -107.2..-37.2: branner to confirm the -Y wall stretch and "
        "the 21 mm under the UI station for the mated plugs",
        "CM5 variant: an eMMC part (no SD socket here); four M2.5 mounting holes for it",
    ],
}


# ── quality (cadkit/PCB_QUALITY.md), first pass after br8's finish (2026-11-13) ─────────────
def _cited(values):
    """Pinout citations this board shares with the instrument's earlier boards, read from their
    own notes so the two never drift. Importing those modules builds no parts (checked: 0
    before and after). A part not found here stays UNCITED -- an A4 FAIL is the honest state
    for the DF40 land and the LM5122 (the NCEP4090 is read: brain_board.PD_PINOUTS) until someone reads them against the
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
    for n, w in (("GADGET", "J13 -> the CM5's USB OTG port (the panel ports' data, via the brain board)."),
                 ("OB_LINK", "J14 -> the CM5's USB3-0 2.0 lane: the brain board's H743 link."),
                 ("FLASH", "the CM5's USB3-1 2.0 lane -> U9 / U10, the arm-flashing switches."))]
BOARD_NOTES["quality"] = {
    "pinouts": _cited(["NUP2105LT1G", "S4B-XH-SM4-TB", "S6B-XH-SM4-TB", "S6B-PH-SM4-TB",
                       "TYPE-C-31-M-12", "S4B-PH-SM4-TB", "THROW", "2N7002",
                       "SQD50P06-15L", "CH32V307WCU6", "TS3USB221ARSER", "TPS2553DBVR",
                       "TCAN3413DR", "SN65HVD230DR", "LMR33630ADDAR", "LMR33630BRNXR",
                       "AP2112K-3.3TRG1", "TAXM8M4RFDCET2T"])
               | {"PZ1.27-2x8P ZZ": "HX PZ1.27-2x8P ZZ drawing (LCSC C22438123) p.1: a plain "
                                     "straight two-row header, the maker numbers nothing -- the "
                                     "numbering is the footprint's (KiCad PinHeader_2x08_P1.27mm_"
                                     "Vertical: odd pads one row, even the other, 1 / 2 at one end) "
                                     "and the way order is harness.UI_RIBBON, as pi_cap.py's 2x8"}
               | {"NCEP4090GU": "as brain_board.py: "
                                + __import__("brain_board").PD_PINOUTS["NCEP4090GU"]}
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
           {"net": "+24V", "from": "Q9.5", "to": ["U7.2", "U7.9", "U7.10"], "amps": 0.3}]
        + [{"net": "+24V", "from": "Q9.5", "to": ["J%d.1" % k], "amps": 0.45} for k in range(21, 31)]
        + [{"net": "VIN_CM5", "from": "F1.2", "to": ["U5.7"], "amps": 3.1},    # the CM5 buck-boost's feed (25 W at 9 V)
           {"net": "+24V_LED", "from": "F3.2", "to": ["J3.1"], "amps": 1.5},
           {"net": "+24V_LED", "from": "F3.2", "to": ["J4.1"], "amps": 1.5},
           # the CM5's 5 V: U5's 5 A output limit (R113), through U21 and F2, onto its six 5 V pins
           {"net": "+5V_BB", "from": "U5.11", "to": ["R113.1"], "amps": 5.0},
           {"net": "+5V_RAW", "from": "R113.2", "to": ["U21.1", "U21.2"], "amps": 5.0, "split": True},
           {"net": "+5V_SW", "from": "U21.7", "to": ["F2.1"], "amps": 2.0},
           {"net": "+5V_SW", "from": "U21.8", "to": ["F2.1"], "amps": 2.0},   # VOUT is 7 AND 8
           {"net": "+5V_CM5", "from": "F2.2", "to": ["J1.77", "J1.79", "J1.81", "J1.83", "J1.85",
                                                    "J1.87"], "amps": 4.0, "split": True},
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
