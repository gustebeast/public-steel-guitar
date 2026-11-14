"""Output board -- the direct-drive instrument's audio, optical processing and USB-C power. x1.

    py -3.12 elec/output_board.py       # -> elec/out/output_board.{net,board.json}

⚠ NOT A BOARD TO ORDER ANY MORE (2026-11-13, the split). As one 68 x 100 board it did not
route (ob10: 30 nets open after the full finish, 0.54 fill). It is now TWO boards stacked
face to face in the same box -- output_power.py and output_signal.py -- and THIS FILE IS
STILL THEIR CIRCUIT: output_split.py builds output_board() and keeps one half of it, with
a board-to-board connector on the nets that cross (harness.OUTPUT_LINK). Change the
circuit here; change which half a part is on in output_split.py. Running this file alone
still writes the whole netlist, which is useful for checks and nothing else.

A NEW BOARD for branner's direct_bench instrument (user, 2026-11-12). output_panel.py is
the old instrument's board, is shipped, and is NOT touched by anything here; the audio
chain below is COPIED from its R2 (by tools in the bronner scratchpad, 2026-11-12), so a
fix to one does not reach the other. What is new, and why:

  * IT STANDS ON ITS EDGE. The board lies in the instrument's X-Z plane in the +X -Y
    corner (a box ~68 x 37 x 113), and its ports run VERTICALLY along the +X edge, out
    through the new thin +X endplate. The deck underside (z -3.2) is its top limit.
  * THE OPTICAL PROCESSING MOVED HERE (user), AND THE OPTICAL BOARD'S CONVERTERS TALK TO IT
    DIRECTLY (user, 2026-11-13: no forwarder MCU -- cost, and the STM32U5A5's stock -- "ribbon
    cable is fine"). The optical board is sensors, emitters, TIAs, its five TLV320ADC3140s and
    a quiet LDO; a 16-way 1.27 mm ribbon (J4) carries their TDM lanes, their I2C, the emitter
    gate and 5 V. This board's MCU is the old optical board's STM32H743IIT6 on the SAME SAI
    map it used there (SAI1 A/B + SAI2 A/B + SAI3 A, all on SAI1's clocks), so the lock-in
    firmware carries over; no USB3300, no ULPI. It is a FULL-SPEED DEVICE to the brain board's
    CM5 (J9, OTG_FS on PA11/PA12). It also REPLACES THE CH32V307: it clocks both audio
    converters (SAI4, PF6-PF9 + PB2), drives the relay, the jack mode and the gain pot. The hub (CH334F) and the CH340
    flash path are gone: the H743's ROM DFU loader lives on OTG_FS, so the CM5 flashes
    it over J9 (USB-only firmware rule); BOOT0 has a pad for recovery.
  * DUAL USB-C POWER + DATA (work item R2-6). J1 and J2 each sink USB PD (5-20 V; EPR is
    not enabled) through an AP33772S, and LM74700 ideal diodes OR the two onto VIN_BUS,
    so a second charger can be plugged or pulled while playing. The OR-ed 5-20 V goes to
    the brain board on J10 + J12, two 4-way XH leads in parallel sized for the two-charger
    worst case (10 A, 22 AWG), measured by U16, with the logic on J11
    (harness.BRAIN_POWER / BRAIN_SIGNAL); the 24 V boost is THERE,
    beside the motors it feeds and away from this board's pickup preamp (see J10). Each
    port's USB 2.0 data reaches the CM5's gadget port through a TS3USB221 (U17 -> J3). No
    barrel jack, no brick.
  * THE MCU AND THE AUDIO START BEFORE THE 24 V, AND THAT ORDER IS THE POINT. VSTBY is
    either port's VBUS through a Schottky (D14/D16) -- vSafe5V is there the moment a
    charger is attached, before any PD contract -- and feeds U5 -> +5V -> U21 -> +3V3D.
    So the H743 is running before anything big is: it reads BOTH chargers' offers over
    I2C, picks the contract and the power mode (R2-6: full / reduced / minimal), and only
    then raises BRAIN_EN (low at rest) and, for a weak charger, LOW_PWR. "Never cut a
    running Pi" becomes "never START one on a contract that cannot hold it."
  * THE MAGNETIC PICKUP (J8, slotted screw terminals, user: "accessible if possible") and
    the TRS jack (J5) keep R2's analog chain exactly. Its notes are copied with it and
    still read true -- except that "U1" in them was the CH32V307 and is the H743 here.

OPEN ITEMS (in BOARD_NOTES["open_items"] too, so they print with the board):
  - (closed 2026-11-13) AP33772S EP: DS46176 Rev. 10-2 Table 1 has "EPAD GND" and p.17
    asks it on GND -- KiCad's pad 25, PWR_GND. NCEP4090GU read from NCE's own sheet V4.0
    p.1 (1-3 S, 4 G, 5-8 D = the tab). Citations in PD_PINOUTS below.
  - The brain board takes the boost (LM5122, SNVS954H 8.2 values; inrush behind BRAIN_EN)
    and the power button: it is designed to harness.BRAIN_POWER / BRAIN_SIGNAL.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# OUTPUT_BOARD_OUT points a trial layout/route at a COPY (never mid-run over elec/out)
OUT_DIR = (os.environ.get("OUTPUT_BOARD_OUT")
           or os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import json  # noqa: E402

from skidl import ERC, Net, Part, Pin, generate_netlist  # noqa: E402

import harness                                      # noqa: E402
import netcheck                                     # noqa: E402
import buck_cell as BC                              # noqa: E402

# The analog chain below is output_panel's R2, copied with its REV switches in place; this
# board is R2's chain and only that, so REV is a constant here, not an environment knob.
REV = 2

P = Pin.types.PASSIVE

USBC_FP = "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"
# ⚠ NMJ6HCD2, NOT NMJ4HCD2: the 4 is the TS part and the 6 is its TRS sibling.
# Same body, same bushing, same panel cut-out, same mounting -- the TRS simply adds the
# RING and RING_N lands, and its pad set is a strict SUPERSET of the TS one (checked pad
# by pad, 2026-09-30). So the mechanical work already done against the TS part -- the
# 3.0 mm panel clamp, TS_SHOULDER_DEPTH, the endplate counterbore, _FRONT["J5"] -- all
# still holds, and the change costs a footprint name.
TRS_FP = "Connector_Audio:Jack_6.35mm_Neutrik_NMJ6HCD2_Horizontal"
# Kycon KPJX-4S-S, the 4-pin snap-and-lock power jack (user, 2026-10-01). The supply is
# a Mean Well GST160A24-R7B desktop adapter, 6.67 A, and its lead ends in a Kycon KPPX-4P;
# the PJ-102AH barrel jack that stood here is rated 5 A and does not take that plug.
# 7.5 A per pin, two pins per rail. Footprint drawn from Kycon's own land pattern:
# elec/footprints/Steel.pretty.
DC_FP = "Steel:Kycon_KPJX-4S-S"
XH_FP = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
# SIDE ENTRY since the split (2026-11-13): the two output boards face each other ~15 mm
# apart, so a vertical plug would point into the other board. Every internal lead now
# enters from the -X edge, as the brain board's do (its S6B-XH-SM4-TB, the same part).
XH6_FP = "Connector_JST:JST_XH_S6B-XH-SM4-TB_1x06-1MP_P2.50mm_Horizontal"
PH6_FP = "Connector_JST:JST_PH_S6B-PH-SM4-TB_1x06-1MP_P2.00mm_Horizontal"
TERM_FP = "TerminalBlock:TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm"
TERM_FP_R2 = "Steel:MaiXu_MX128-5.0-02P_1x02_P5.00mm"     # slotted: no second tool (R2-3)
TERM_FP_35 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-2-3.5-H_1x02_P3.50mm_Horizontal"
MCU_FP = "Package_DFN_QFN:QFN-68-1EP_8x8mm_P0.4mm_EP5.2x5.2mm"
ADC_FP = "Package_SO:TSSOP-14_4.4x5mm_P0.65mm"     # PCM1808PWR is a 14-pin TSSOP
DAC_FP = "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm"
HUB_FP = "Package_DFN_QFN:HVQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm"
# DPDT signal relay, 5 V coil. Only ONE pole switches audio (the tip); an
# unbalanced output has nothing for the second pole to do, and a DPDT in this
# package is what is stocked.
RELAY_FP = "Relay_SMD:Relay_DPDT_Omron_G6K-2F-Y"


# ⚠ THE REF IS PINNED FROM THE TAG. Every call passes a tag that spells the intended
# ref, and without ref= that agreement is a COINCIDENCE of CREATION ORDER, not a
# mechanism. On lever_sensor, adding a single resistor in the middle of the file consumed
# R5 and pushed every later resistor up one -- and BOARD_NOTES["placements"] is keyed by
# ref, so parts silently referred to refs that no longer existed while a new one with no
# placement would have landed on the board ORIGIN. ERC passed and the netlist was valid.
# This board had the same latent fault; pinning the ref makes creation order irrelevant.
def _r(tag, value, desc, fp="Resistor_SMD:R_0402_1005Metric"):
    return Part(name="R", ref_prefix="R", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, fp="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


# ⚠ AND _d WAS THE ONE THAT NEVER GOT THE FIX. The note above says a ref that agrees
# with its tag "without ref= ... is a COINCIDENCE of CREATION ORDER" -- and _r and _c were
# both pinned while the diode helper was left as it was, so the fault the note describes
# was still live in this file. Adding D7 for the ring's phantom guard BEFORE D6 in the
# source proved it: the netlist came out with "D7" carrying +24V and PWR_GND, which are
# D6's nets, because skidl had numbered them by creation order and the placement dict --
# keyed by ref -- then put each part at the other one's coordinates. DRC found it as a
# solder-mask bridge between parts that should not have been near each other.
# Caught in one route. It would have been much harder to see in a year.
def _bind(part, ways, nets):
    """Join each of `part`'s ways to the net its harness NAME maps to, and hold the order
    to the standard (harness.py). By name, never by way number."""
    harness.check_ways(ways, ("V24", "V5"), ("GND", harness.NC), where=part.ref)
    for i, n in enumerate(ways):
        if n in nets:
            nets[n] += part[i + 1]


def _d(tag, value, desc, fp="Diode_SMD:D_SOD-523"):
    return Part(name="D", ref_prefix="D", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _usbc(tag, desc, value="TYPE-C-31-M-12"):
    pins = ([Pin(num=n, func=P) for n in
             ("A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12",
              "B1", "B4", "B5", "B6", "B7", "B8", "B9", "B12")]
            + [Pin(num="SH", func=P)])
    return Part(name="USB_C_Receptacle", ref_prefix="J", ref=tag, tag=tag, dest="NETLIST",
                tool="skidl", value=value, description=desc,
                footprint=USBC_FP, pins=pins)


def _fix(tag, value, desc, fp, pins):
    """A part whose pins are numbers only; the ref is pinned from the tag (see _r)."""
    return Part(name=value, ref_prefix=tag.rstrip("0123456789"), ref=tag, tag=tag,
                dest="NETLIST", tool="skidl", value=value, description=desc, footprint=fp,
                pins=[Pin(num=i, func=P) for i in pins])


def _cap(tag, value, desc, a, b, fp="Capacitor_SMD:C_0402_1005Metric"):
    c = _c(tag, value, desc, fp)
    a += c[1]
    b += c[2]
    return c


def _res(tag, value, desc, a, b, fp="Resistor_SMD:R_0402_1005Metric"):
    r = _r(tag, value, desc, fp)
    a += r[1]
    b += r[2]
    return r


C0402, C0805 = "Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0805_2012Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
# Pinout citations for the PD parts, read 2026-11-13 against the maker's sheets AND the KiCad
# footprints' pad numbering (output_split's power half and the brain cite them from here).
PD_PINOUTS = {
    "NCEP4090GU": "NCE NCEP4090GU datasheet V4.0 (LCSC C502976) p.1 'DFN 5X6' top/bottom view + "
                  "schematic: 1-3 S, 4 G, 5-8 D, drain tab = 5-8 (bottom view); p.5 DFN5X6-8L(G) "
                  "outline. KiCad TDSON-8-1: pads 1-4 the leads, pad 5 the tab spanning 5-8",
    "AP33772SDKZ-13": "Diodes DS46176 Rev. 10-2 p.3 Table 1 (W-QFN4040-24 Type A1): 1 ISENP, 2 NC, "
                      "3 GND, 4 SDA, 5 SCL, 6 FLIP, 7 GPIO, 8 LED, 9 INT, 10 NC, 11 VSEL, 12 V18, "
                      "13 OTP, 14 NC, 15 IFB, 16 CC2, 17 CC1, 18 DN, 19 DP, 20 V5V, 21 NC, 22 VOUT, "
                      "23 PWR_EN, 24 VCC, EPAD GND (KiCad pad 25); p.17 EP to GND",
    "PTCFW-H22A-005": "YUWENFA PTCFW-H22A-005 drawing P-TCF-003 rev A0 (LCSC C54829820) sheet 2/3, "
                      "PIN ASSIGNMENTS: A1/A12/B1/B12 GND, A4/A9/B4/B9 VBUS, A5 CC1, B5 CC2, A6/B6 D+, "
                      "A7/B7 D-, A8/B8 SBU; its recommended layout (component side) puts A1/B12 at the "
                      "left end and A12/B1 at the right, 8.64 slot span, 4.18 / 5.79, two 0.65 pegs -- "
                      "TYPE-C-31-M-12's land, which KiCad's USB_C_Receptacle_HRO_TYPE-C-31-M-12 numbers "
                      "by the same names (read 2026-11-13)",
    "LM74700QDBVRQ1": "TI SNOSD17G p.3 Figure 5-1 / Table 5-1, DBV (SOT-23-6): 1 VCAP, 2 GND, 3 EN, "
                      "4 CATHODE, 5 GATE, 6 ANODE (the DDF table 5-2 differs); FET source on ANODE, "
                      "drain on CATHODE. KiCad SOT-23-6 pads 1-6 as numbered",
}
C1206, C1210 = "Capacitor_SMD:C_1206_3216Metric", "Capacitor_SMD:C_1210_3225Metric"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
# NCEP4090GU, DFN5x6-8L, 40 V 2.2 mR at 10 V / 3.3 mR at 4.5 V (LCSC C502976). The usual
# PowerPAK SO-8 land: pads 1-3 source, 4 gate, 5 the drain tab -- confirmed against NCE's
# sheet V4.0 p.1 on 2026-11-13 (PD_PINOUTS).
FET_FP = "Package_TO_SOT_SMD:TDSON-8-1"


def _nfet(tag, desc, value="NCEP4090GU"):
    return Part(name="Q_NMOS", ref_prefix="Q", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=FET_FP,
                pins=[Pin(num=1, name="S1", func=P), Pin(num=2, name="S2", func=P),
                      Pin(num=3, name="S3", func=P), Pin(num=4, name="G", func=P),
                      Pin(num=5, name="D", func=P)])


def _small_nfet(tag, desc):
    # 2N7002 SOT-23: 1 G  2 S  3 D (CJ 2N7002 datasheet p.1, LCSC C8545) -- as Q3
    return Part(name="Q_NMOS", ref_prefix="Q", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value="2N7002", description=desc + " (LCSC C8545)", footprint=SOT23,
                pins=[Pin(num=1, name="G", func=P), Pin(num=2, name="S", func=P),
                      Pin(num=3, name="D", func=P)])


# ── THE MCU: STM32H743IIT6, LQFP-176 -- the optical board's part and pin map ─────────────
# The optical board's map (optical.PIN, derived from KiCad's STM32H743IITx symbol and checked
# by re-deriving the LQFP144 map from its own symbol) plus the pins this board adds, read the
# same way from MCU_ST_STM32H7.kicad_sym (KiCad 10, 2026-11-12). PA4 = 50 and PB4 = 162 agree
# between the two reads.
MCU_VDD = (15, 23, 36, 49, 62, 72, 82, 91, 103, 127, 136, 149, 159, 172)
MCU_VSS = (14, 22, 48, 61, 71, 90, 102, 113, 126, 135, 148, 158)
PIN = {
    "PA0": 40, "PA1": 41, "PA2": 42, "PA3": 47, "PA4": 50, "PA5": 51,
    "PA6": 52, "PA7": 53, "PA13": 124, "PA14": 137,
    "PB0": 56, "PB1": 57, "PB3": 161, "PB4": 162, "PB5": 163,
    "PB10": 79, "PB11": 80, "PB12": 92, "PB13": 93, "PB14": 94, "PB15": 95,
    "PC0": 32, "PI11": 13, "PH4": 45, "PH0": 29, "PH1": 30,
    "PE2": 1, "PE3": 2, "PE4": 3, "PE5": 4, "PE6": 5,
    "PF0": 16, "PF1": 17,
    "NRST": 31, "BOOT0": 166, "PDR_ON": 171,
    "VBAT": 6, "VDDA": 39, "VSSA": 37, "VREF+": 38, "VDD33_USB": 114,
    "VCAP1": 81, "VCAP2": 125,
    # new on this board
    "PA11": 122, "PA12": 123, "PB6": 164, "PB7": 165, "PH7": 84, "PH8": 85,
    "PD8": 96, "PD9": 97, "PD10": 98, "PD11": 99, "PD12": 100, "PD13": 101, "PD3": 145, "PD4": 146,
    "PG2": 106, "PG3": 107, "PG6": 110, "PG7": 111, "PG8": 112,
    "PE7": 68, "PE8": 69, "PE11": 74, "PE12": 75, "PE14": 77,
    # the optical lanes' and SAI4's (KiCad 10 MCU_ST_STM32H7.kicad_sym, STM32H743IITx, its
    # pins' alternate-function lists, read 2026-11-13)
    "PF6": 24, "PF7": 25, "PF8": 26, "PF9": 27, "PB2": 58, "PI6": 175, "PD1": 143,
}
# Everything else this board asks of the MCU: net name -> port. AF in the comment.
MCU_IO = {
    # THE OPTICAL LANES, exactly the optical board's map (optical.py SAI_CLK / SAI_SD): 192 kHz,
    # BCLK 12.288 MHz, one lane per converter, SAI2 and SAI3 synchronous slaves of SAI1
    "SAI_SCK": "PE5",       # SAI1_SCK_A
    "SAI_FS": "PE4",        # SAI1_FS_A
    "SAI_SD1": "PE6",       # SAI1_SD_A   <- optical U15
    "SAI_SD2": "PE3",       # SAI1_SD_B   <- U16
    "SAI_SD3": "PA0",       # SAI2_SD_B   <- U17
    "SAI_SD4": "PI6",       # SAI2_SD_A   <- U18
    "SAI_SD5": "PD1",       # SAI3_SD_A   <- U19
    "OPT_EMIT": "PB3",      # TIM2_CH2: the emitter gate, frequency-locked to FSYNC (optical.py)
    # SAI4 for the 48 kHz audio converters, its own clock domain: block B master-transmit to
    # the DAC, block A synchronous to block B receiving the ADC (SAI4's A clock pins are
    # PE4/PE5 only, which the optical lanes hold)
    "I2S_CK": "PF8",        # SAI4_SCK_B
    "I2S_WS": "PF9",        # SAI4_FS_B
    "I2S_SDO": "PF6",       # SAI4_SD_B   -> PCM5102A DIN
    "I2S_SDI": "PB2",       # SAI4_SD_A   <- PCM1808 DOUT
    "I2S_MCK": "PF7",       # SAI4_MCLK_B
    "MCU_DM": "PA11",       # OTG_FS_DM -> J9, the brain board's CM5
    "MCU_DP": "PA12",       # OTG_FS_DP
    # three I2C buses: the two AP33772S share the fixed address 0x52, so each has its own
    "PDA_SCL": "PB6", "PDA_SDA": "PB7",          # I2C1 AF4 -> U13, port J1
    "PDB_SCL": "PH7", "PDB_SDA": "PH8",          # I2C3 AF4 -> U14, port J2
    "I2C2_SDA": "PF0", "I2C2_SCL": "PF1",        # I2C2 AF4 -> U16 INA226 (as optical)
    # the gain pot on SPI4 (or bit-banged: three plain outputs)
    "POT_CS": "PE11", "POT_SCK": "PE12", "POT_SDI": "PE14",
    "RELAY": "PD8", "JACK_MODE": "PD9",
    "PDA_INT": "PD10", "PDB_INT": "PD11",        # AP33772S INT: push-pull, HIGH = event; FT pins
    "INA_ALERT_N": "PD12",
    "OPT_VBUS_EN": "PD13", "OPT_FAULT_N": "PG2",
    "DATA_SEL": "PG3",      # U17: low = J1's pair to the CM5, high = J2's
    "STATUS_LED": "PG6",    # the warning that does not need the screen (R2-6 (c))
    # the brain-board signal lead, J11 (harness.BRAIN_SIGNAL)
    "BRAIN_EN": "PE7",      # high = the brain board may start its boost and 24 V
    "LOW_PWR": "PG7",       # high = MINIMAL mode: the brain board leaves the CM5 off
    "PWR_BTN": "PE8",       # the power button, from the brain board (open drain)
    "BRAIN_PG": "PG8",      # the brain board's 24 V is good (open drain)
    "PWR_LEAD1_N": "PD3",   # J10 power lead present (LOW); its way 3 is GND at the brain
    "PWR_LEAD2_N": "PD4",   # J12 power lead present (LOW)
}



# THE OUTPUT BOARD IS THE BRAIN (user, 2026-11-13): brain.py's circuit is built onto this one
# (its field connectors replaced by the connector-board ribbon). False = the two-board design.
MERGED = True


# THE H743 TAKES THE CH32's JOB (user, 2026-11-13: "unify more work onto a single processor").
# The CH32V307's signals, onto free H743 ports -- every one read from KiCad 10's
# MCU_ST_STM32H7.kicad_sym (STM32H743IITx, pin numbers + alternate functions, 2026-11-13) and
# checked unused by the merged netlist. FDCAN2 RX/TX on PB12/PB13 is the H743's own pair; FDCAN1
# on PH13/PH14 (PA11/PA12 is OTG_FS). USART1 on PA9/PA10 is one of the H74x ROM loader's ports
# (ST AN2606); PA9's OTG_FS VBUS-sense alternate stays off (firmware). The CH32's BTN_IN /
# LOW_PWR_IN / BRAIN_PG_N copies go: this MCU drives LOW_PWR and reads PWR_BTN already, and
# reads +24V itself on SENSE_24V.
FOLD = MERGED
FOLD_IO = {
    "CAN1_TX": "PH13", "CAN1_RX": "PH14",       # FDCAN1 -> U202 TCAN3413, bus A (motors)
    "CAN2_TX": "PB13", "CAN2_RX": "PB12",       # FDCAN2 -> U203 SN65HVD230, bus B (arms)
    "MCU_TX": "PA9", "MCU_RX": "PA10",          # USART1 <-> CM5 UART4 (R230 / R231), ROM loader
    "SENSE_24V": "PA4", "SENSE_5V": "PA5",      # ADC1_INP18 / ADC1_INP19, the brain's dividers
    "PG_5V": "PG0",                             # U205's power-good
    "BUSB_FAULT_N": "PG1",                      # the arm 5 V switches' fault (open drain)
    "EN_PED": "PE13", "EN_LEV": "PE15",         # the arm 5 V switches
    "PWR_HOLD": "PG4",                          # holds Q202 on through the CM5's shutdown
    "CM5_ON": "PG5",                            # CM5_3V3 is up
    "CM5_PWRBTN": "PG9",                        # -> Q214 -> the CM5's PWR_Button
}
FOLD_PINS = {"PH13": 128, "PH14": 129, "PB12": 92, "PB13": 93, "PA9": 120, "PA10": 121,
             "PA4": 50, "PA5": 51, "PG0": 66, "PG1": 67, "PE13": 76, "PE15": 78, "PG4": 108,
             "PG5": 109, "PG9": 152}
if FOLD:
    for _k, _v in FOLD_PINS.items():
        assert PIN.get(_k, _v) == _v, _k
    PIN.update(FOLD_PINS)
    MCU_IO.update(FOLD_IO)
    del MCU_IO["BRAIN_PG"]                      # nobody reports +24V good to itself


def _circuit_parts():
    from builtins import default_circuit         # skidl 2.x keeps it there
    return list(default_circuit.parts)


def _renumber(parts, offset):
    """REF n -> REF n+offset for the parts another file built (brain.py's, +200): one board,
    one set of refs. A ref with no trailing number is refused rather than guessed."""
    import re as _re
    for pt in parts:
        m = _re.match(r"^([A-Z]+)(\d+)(?:_\d+)?$", pt.tag or pt.ref)
        assert m, "cannot renumber %r" % (pt.tag or pt.ref)
        old = pt.tag or pt.ref
        pt.ref = pt.tag = "%s%d" % (m.group(1), int(m.group(2)) + offset)
        for pin in pt.pins:                  # its "<ref>_NC_<n>" nets follow the ref
            for net in pin.nets:
                nm = _re.match(r"^%s_NC_(\d+)(?:_\d+)?$" % _re.escape(old), net.name)
                if nm:
                    net.name = "%s_NC_%s" % (pt.ref, nm.group(1))


# the signals that cross the audio isolation barrier (U32-U34): MCU -> audio unless noted
XING = ("I2S_MCK", "I2S_CK", "I2S_WS", "I2S_SDO", "I2S_SDI", "POT_CS", "POT_SCK", "POT_SDI",
        "JACK_MODE")
# the audio section, grown from these over every net but the barrier's (_audio_parts)
AUDIO_SEEDS = ("U2", "U3", "U6", "U7", "U8", "U9", "U10", "U11", "U12", "J5", "J8")
BARRIER = ("U30", "U32", "U33", "U34")        # one side each: wired explicitly
QSOP16 = "Package_SO:QSOP-16_3.9x4.9mm_P0.635mm"


def _isolation(gnd, agnd, v5_pre, v3d, v3v3, v5, iso9_raw, iso9, io, iso):
    """The barrier: U30 (power) and U32-U34 (logic). Pinouts READ, not remembered, except
    where an open item says otherwise:
      ISO7741 / ISO7740, DBQ (QSOP-16): TI SLLSEP4K Table 4-1 -- 1 VCC1 2 GND1 3 INA 4 INB
        5 INC 6 OUTD (7741) / IND (7740) 7 EN1 (7741) / NC (7740) 8 GND1 9 GND2 10 EN2
        11 IND (7741) / OUTD (7740) 12 OUTC 13 OUTB 14 OUTA 15 GND2 16 VCC2. Non-F parts
        output HIGH on an open input or an unpowered side 1 (Table 7-2): POT_CS idles high
        (deselected), as R39 / R40 wanted.
      ISO7710F, D (SOIC-8): TI SLLSER9E -- 1 VCC1 2 IN 3 VCC1 4 GND1 5 GND2 6 OUT 7 NC 8 VCC2;
        F = LOW on an open input: JACK_MODE reads balanced through the MCU's reset.
      LP2985-50, DBV: TI SLVS522S Table 4-1 -- 1 VIN 2 GND 3 ON/OFF 4 BYPASS 5 VOUT; 16 V max
        in (legacy die), 2.2 uF ceramic out, 10 nF bypass (7.1.3).
      B0509S-1WR3 (Mornsun, SIP-4): 1 -Vin 2 +Vin 3 0V 4 +Vo AS THE MURATA MEE1 / NME FAMILY
        IT CLONES -- NOT YET READ OFF MORNSUN'S SHEET (open item)."""
    p = Pin.types.PASSIVE
    u30 = Part(name="DCDC_ISO", ref_prefix="U", ref="U30", tag="U30", dest="NETLIST", tool="skidl",
               value="B0509S-1WR3", description="1 W isolated DC-DC, 5 -> 9 V unregulated, "
               "1.5 kV: the audio section's power, across the barrier (Mornsun)",
               footprint="Converter_DCDC:Converter_DCDC_Murata_MEE1SxxxxSC_THT",
               pins=[Pin(num=i, func=p) for i in range(1, 5)])
    gnd += u30[1]
    v5_pre += u30[2]
    agnd += u30[3]
    iso9_raw += u30[4]
    # 9 V, not 5: the module is unregulated (its output climbs at light load), so it feeds
    # a low-noise LDO with headroom rather than the converters directly -- and the LDO's
    # PSRR is the module's ripple filter, after FB1
    u31 = Part(name="LDO_5V", ref_prefix="U", ref="U31", tag="U31", dest="NETLIST", tool="skidl",
               value="LP2985-50DBVR", description="the audio's +5V: low-noise LDO, 150 mA, "
               "16 V in, from the isolated 9 V (TI SLVS522S)",
               footprint="Package_TO_SOT_SMD:SOT-23-5",
               pins=[Pin(num=i, func=p) for i in range(1, 6)])
    byp = Net("ISO_LDO_BYP")
    iso9 += u31[1], u31[3]
    agnd += u31[2]
    byp += u31[4]
    v5 += u31[5]
    for tag, val, a, b, why, fp in (
            ("C160", "4.7uF/10V", v5_pre, gnd, "U30 input", C0805),
            ("C161", "4.7uF/25V", iso9_raw, agnd, "U30 output, before FB1", C0805),
            ("C162", "1uF/25V", iso9, agnd, "U31 input, after FB1", C0603),
            ("C163", "10nF", byp, agnd, "U31 noise bypass (SLVS522S 7.1.3)", C0402),
            ("C164", "4.7uF/10V", v5, agnd, "U31 output: 2.2 uF minimum effective", C0805)):
        _cap(tag, val, "isolated supply: " + why, a, b, fp)

    def iso_chip(tag, value, fp, side1, side2, desc):
        """side1 / side2: {pin: net}; the supplies and grounds added here."""
        u = Part(name="ISO", ref_prefix="U", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                 value=value, description=desc, footprint=fp,
                 pins=[Pin(num=n, func=p) for n in sorted(set(side1) | set(side2))])
        for k, net in list(side1.items()) + list(side2.items()):
            net += u[k]
        return u

    # U32: the converters' clocks out, the ADC's data back
    iso_chip("U32", "ISO7741DBQR", QSOP16,
             {1: v3d, 2: gnd, 3: io["I2S_MCK"], 4: io["I2S_CK"], 5: io["I2S_WS"], 6: io["I2S_SDI"],
              7: v3d, 8: gnd},
             {9: agnd, 10: v3v3, 11: iso["I2S_SDI"], 12: iso["I2S_WS"], 13: iso["I2S_CK"],
              14: iso["I2S_MCK"], 15: agnd, 16: v3v3},
             "4-ch digital isolator 3F/1R, 100 Mbps: MCLK, BCK, LRCK out, the ADC's data back (TI)")
    # U33: the DAC's data and the pot's SPI
    iso_chip("U33", "ISO7740DBQR", QSOP16,
             {1: v3d, 2: gnd, 3: io["I2S_SDO"], 4: io["POT_CS"], 5: io["POT_SCK"], 6: io["POT_SDI"],
              8: gnd},
             {7: Net("U33_NC_7"), 9: agnd, 10: v3v3, 11: iso["POT_SDI"], 12: iso["POT_SCK"],
              13: iso["POT_CS"], 14: iso["I2S_SDO"], 15: agnd, 16: v3v3},
             "4-ch digital isolator 4F: the DAC's data, the gain pot's SPI (TI)")
    # U34: the jack mode bit, default LOW (balanced)
    iso_chip("U34", "ISO7710FDR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
             {1: v3d, 2: io["JACK_MODE"], 3: v3d, 4: gnd},
             {5: agnd, 6: iso["JACK_MODE"], 7: Net("U34_NC_7"), 8: v3v3},
             "1-ch digital isolator, F = low on an open input: JACK_MODE (TI)")
    for tag, a, b, why in (("C165", v3d, gnd, "U32 VCC1"), ("C166", v3v3, agnd, "U32 VCC2"),
                           ("C167", v3d, gnd, "U33 VCC1"), ("C168", v3v3, agnd, "U33 VCC2"),
                           ("C169", v3d, gnd, "U34 VCC1"), ("C170", v3v3, agnd, "U34 VCC2")):
        _cap(tag, "100nF", "isolator bypass, " + why, a, b, C0402)


def _audio_parts():
    """Every part of the audio section: grown from AUDIO_SEEDS over every net except GND,
    the barrier's other side and the relay coil -- so a part added to the chain later is
    in it without a list to keep."""
    from builtins import default_circuit         # skidl 2.x keeps it there
    stop = {"GND", "AGND", "PWR_GND", "V5_PRE", "+3V3D", "RELAY_COIL"} | set(XING)
    seen, todo = set(AUDIO_SEEDS), list(AUDIO_SEEDS)
    parts = {pt.ref: pt for pt in default_circuit.parts}
    while todo:
        for pin in parts[todo.pop()].pins:
            for net in pin.nets:
                if net.name in stop:
                    continue
                for q in net.pins:
                    r = q.part.ref
                    if r not in seen and r not in BARRIER:
                        seen.add(r)
                        todo.append(r)
    return seen


def _move_audio_grounds(gnd, agnd):
    """The chain was written on one ground (output_panel's R2); every GND pin of an audio
    part goes to AGND here, in one place, and nothing of the audio may be left on GND."""
    audio = _audio_parts()
    moved = 0
    for pin in list(gnd.pins):
        if pin.part.ref in audio:
            pin.disconnect()
            agnd += pin
            moved += 1
    left = sorted({q.part.ref for q in gnd.pins} & audio)
    assert not left, "audio parts still on GND: %s" % left
    # and the other way: NOTHING outside the audio section and the barrier touches AGND (R60
    # did, 2026-11-13 -- written against `agnd` when that was GND's alias, it tied PWR_GND
    # straight onto the isolated ground and no check saw it)
    stray = sorted({q.part.ref for q in agnd.pins} - audio - set(BARRIER) - {"U31"})
    assert not stray, "parts outside the audio section on AGND: %s" % stray
    return audio, moved


def output_board():
    # ⚠ ONE SIGNAL GROUND, PWR_GND SEPARATE, R60 THE STAR -- output_panel's rule, kept. The
    # power path (both USB-C inlets, the ideal diodes, VIN_BUS and J10) is PWR_GND: the
    # brain board's motor current returns through it to the chargers and never crosses GND. The buck U5 stands on GND as on R2, so its input current (<= ~1.3 A
    # on a 5 V contract) is what R60 carries -- an 0603 then, 1206 here.
    gnd = Net("GND")
    # ⚠ THE AUDIO IS ISOLATED (user, 2026-11-13: "I like all three as a bulletproof
    # solution" -- the hum fix). AGND is the audio section's own ground: the pickup (J8),
    # the jack (J5), both converters, the buffers, the pot, the mode switch and +5V / +3V3
    # (which feed nothing else). It has NO copper path to GND: power crosses in U30 (an
    # isolated DC-DC), the converters' and the pot's logic in U32-U34 (digital isolators),
    # and the relay's coil-to-contact gap is the barrier at K1. A two-prong charger's Y-cap
    # leakage, or a computer on the USB data, then has no path to the jack's sleeve -- the
    # hum it makes through an earthed amp is designed out, not filtered.
    agnd = Net("AGND")
    # the AUDIO rails, isolated (U30 / U31 / U6) and named so: +5V / +3V3 are the brain's
    v5, v3v3 = Net("+5V_A"), Net("+3V3_A")     # +3V3_A: U6, the converters' rail, as on R2
    v3d = Net("+3V3D")                         # U21: the MCU, the PHY, the logic
    # ONE GROUND ON THE MERGED BOARD (2026-11-13): PWR_GND was kept apart, joined at R60, so the
    # chargers' and the brain's return current never crossed the AUDIO's reference. The audio is
    # galvanically isolated now (AGND), so that reason is gone -- and on one board a split between
    # the CM5 / CH32 / boost and the H743 would cost more than it saves. Placement keeps the big
    # currents apart instead: chargers and the boost along the bottom and the far end, the boost's
    # hot loop on its own local pours.
    pgnd = gnd if MERGED else Net("PWR_GND")
    vstby, vin = Net("VSTBY"), Net("VIN_BUS")
    for n in (gnd, agnd, v5, v3v3, v3d, pgnd, vstby, vin):
        n.drive = Pin.drives.POWER
    io = {k: Net(k) for k in MCU_IO}           # every MCU signal net, by name
    relay = io["RELAY"]                        # the relay COIL stays on GND (see K1)
    # the audio parts below connect to the ISOLATED side of each crossing; U32-U34 join
    # them to the MCU's io nets
    iso = {k: Net(k + "_ISO") for k in XING}
    jack_mode = iso["JACK_MODE"]
    pot_cs, pot_sck, pot_sdi = iso["POT_CS"], iso["POT_SCK"], iso["POT_SDI"]
    i2s_ck, i2s_ws = iso["I2S_CK"], iso["I2S_WS"]
    i2s_sdo, i2s_sdi, mclk = iso["I2S_SDO"], iso["I2S_SDI"], iso["I2S_MCK"]
    osc_in, osc_out, nrst, boot0 = Net("OSC_IN"), Net("OSC_OUT"), Net("NRST"), Net("MCU_BOOT0")

    # ── J1/J2: THE PANEL USB-C PORTS -- each one power IN and data, either one alone runs it ──
    # Per port, DS46176 figure 1 with one change: ONE switch FET, not the back-to-back pair,
    # because the LM74700 behind it already blocks reverse current -- the figure itself says
    # the pair "could be simplified to a simple N-MOS switch" when nothing can back-feed, and
    # the ideal diode is what makes that true. So, per port:
    #   J VBUS --R(5 mR, ISENP..VCC)-- VCC node --Q(switch, PWR_EN via 6k2)-- VOUT node
    #          --Q(ideal diode, LM74700)-- VIN_BUS --> U16's shunt --> J10, the brain board
    # and, off the VCC node, a Schottky to VSTBY for the logic (see the module note).
    # The pair's D+/D- go to U17, not to the AP33772S: its DP/DN are only moisture sensing,
    # which this instrument does not use, and they would hang on the data lines.
    # Each AP33772S has a bus to itself: the address is fixed at 0x52.
    usb_pair = {}
    for side, j_ref, u_ref, qs, qd, ui, rs, rt, refs_r, refs_c, d_tvs, d_stb, d_esd, clamp_refs, fl_p, fl_d in (
            ("A", "J1", "U13", "Q4", "Q6", "U18", "R70", "RT1",
             ("R71", "R72", "R73", "R74"), ("C80", "C81", "C82", "C83", "C84", "C85"),
             "D11", "D14", None, ("D20", "D21"), "FL1", "FL3"),
            ("B", "J2", "U14", "Q5", "Q7", "U19", "R75", "RT2",
             ("R76", "R77", "R78", "R79"), ("C86", "C87", "C88", "C89", "C90", "C91"),
             "D15", "D16", ("D12", "D13"), ("D22", "D23"), "FL2", "FL4")):
        # ⚠ A 48 V (EPR-class) RECEPTACLE, not the HRO TYPE-C-31-M-12 (lead ruling 2026-11-13):
        # HRO's drawing rates that one 20 V, under the PD contract's 21 V; YUWENFA's
        # PTCFW-H22A-005 is rated 48 V / 5 A on its own drawing (p.1/3) on the same land
        # (p.2/3: 8.64 slots, 4.18 / 5.79, two 0.65 pegs), at the same price
        j = _usbc(j_ref, "panel USB-C %s: USB PD power in (5-20 V) + USB 2.0 data to the "
                  "CM5's gadget port; 48 V receptacle (LCSC C54829820)" % side, "PTCFW-H22A-005")
        vbus, vcc, vout = Net("P%s_VBUS" % side), Net("P%s_VCC" % side), Net("P%s_VOUT" % side)
        dp, dm = Net("USB%s_DP" % side), Net("USB%s_DM" % side)
        # COMMON-MODE CHOKES AT THE PORT (user, 2026-11-13, the hum fix part 2): a charger's
        # switching hash rides VBUS, GND and the shield together. The power pair (VBUS, GND)
        # goes through one choke and the data pair through another, so the cable's
        # common-mode current meets the choke on EVERY conductor that reaches the board --
        # a choke on the power alone would let it return round the data lines' ground.
        # The shield lands on the CONNECTOR side, with the TVS.
        vbus_j, gnd_j = Net("P%s_VBUS_J" % side), Net("P%s_GND_J" % side)
        dp_j, dm_j = Net("USB%s_DP_J" % side), Net("USB%s_DM_J" % side)
        gnd_j += j["A1"], j["A12"], j["B1"], j["B12"], j["SH"]
        vbus_j += j["A4"], j["B4"], j["A9"], j["B9"]
        dp_j += j["A6"], j["B6"]
        dm_j += j["A7"], j["B7"]
        for tag, value, fp, (a1, a2), (b1, b2), why in (
                (fl_p, "744273102", "Inductor_SMD:L_CommonModeChoke_Wuerth_WE-SL5-HC",
                 (vbus_j, vbus), (gnd_j, pgnd), "power pair: WE-SL5 HC, >= 5 A (part number "
                 "an open item)"),
                (fl_d, "ACM2012-900-2P-T002", "Inductor_SMD:L_CommonModeChoke_Coilank_ACM2012",
                 (dp_j, dp), (dm_j, dm), "USB 2.0 data pair: 90 ohm common mode, passes HS")):
            fl = Part(name="CMC", ref_prefix="FL", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                      value=value, description="port %s common-mode choke, %s; windings 1-4 and "
                      "2-3 (open item: read off the maker's sheet)" % (side, why), footprint=fp,
                      pins=[Pin(num=i, func=P) for i in range(1, 5)])
            a1 += fl[1]
            a2 += fl[4]
            b1 += fl[2]
            b2 += fl[3]
        usb_pair[side] = (dp, dm)
        cc1, cc2 = Net("P%s_CC1" % side), Net("P%s_CC2" % side)
        cc1 += j["A5"]
        cc2 += j["B5"]
        # W-QFN4040-24 (DS46176 Rev. 10-2, Table 1). See the module's open items for the pad.
        u = _fix(u_ref, "AP33772SDKZ-13", "USB PD3.1 sink controller, port %s, I2C 0x52 "
                 "(LCSC C50341643)" % side,
                 "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm", range(1, 26))
        pgnd += u[3], u[25]                    # GND, and the land's pad
        vcc += u[24]                           # VCC: behind the sense resistor
        vbus += u[1]                           # ISENP: the connector side of it
        cc1 += u[17]
        cc2 += u[16]
        io["PD%s_SDA" % side] += u[4]
        io["PD%s_SCL" % side] += u[5]
        io["PD%s_INT" % side] += u[9]
        pwr_en, vsense = Net("P%s_PWR_EN" % side), Net("P%s_VOUT_SNS" % side)
        v18, v5v, ifb, otp = (Net("P%s_V18" % side), Net("P%s_V5V" % side),
                              Net("P%s_IFB" % side), Net("P%s_OTP" % side))
        pwr_en += u[23]
        vsense += u[22]
        v18 += u[12]
        v5v += u[20]
        ifb += u[15]
        otp += u[13]
        # FLIP, GPIO (FA02 only), LED, VSEL (FA02 only), DP, DN, and the four NC pins
        for k in (6, 7, 8, 11, 18, 19, 2, 10, 14, 21):
            Net("%s_NC_%d" % (u_ref, k)).connect(u[k])
        _res(rs, "5mR 1W", "port %s sense resistor, ISENP to VCC -- the 5 mR the AP33772S's "
             "OCP and CURRENT register are scaled for" % side, vbus, vcc,
             "Resistor_SMD:R_0805_2012Metric")
        q = _nfet(qs, "port %s VBUS switch, driven by %s PWR_EN" % (side, u_ref))
        vcc += q["D"]
        vout += q["S1"], q["S2"], q["S3"]
        gate = Net("P%s_GATE" % side)
        gate += q["G"]
        _res(refs_r[0], "6k2", "port %s switch gate resistor (DS46176 fig. 1)" % side,
             pwr_en, gate)
        # ⚠ THE SINGLE SWITCH FET'S GATE NEEDS A CLAMP BOTH WAYS (voltage_check, 2026-11-13).
        # OFF, PWR_EN pulls the gate to ground while VOUT stays charged -- C84 holds it and the
        # ideal diode behind stops it draining -- so VGS = -VOUT, the whole 21 V contract, over
        # the NCEP4090GU's +-20 V. Fig. 1's back-to-back pair has a floating common source and
        # never sees it; this simplification does. A single zener cannot fix it: ON, the gate
        # sits ~4 V above the source and would forward-bias it. Two BZT52C12T anti-series
        # (common anode) clamp at +-(12.7 + 0.7) V and stay off below 11.4 V either way; the
        # clamp current is R71's, (21 - 13.4) / 6k2 = 1.2 mA, and it drains VOUT as it goes.
        gclamp = Net("P%s_GCLAMP" % side)
        for dz, k, why in ((clamp_refs[0], gate, "gate side"), (clamp_refs[1], vout, "source side")):
            z = _fix(dz, "BZT52C12T-7", "port %s switch gate-source clamp, %s: two 12 V zeners "
                     "anti-series (LCSC C507911)" % (side, why), "Diode_SMD:D_SOD-523", (1, 2))
            k += z[1]                          # KiCad diode land: pad 1 = K
            gclamp += z[2]
        _res(refs_r[1], "200R", "port %s VOUT sense series (DS46176 fig. 1)" % side,
             vout, vsense)
        _res(refs_r[2], "5k1", "port %s CC1 Rd -- external on this part" % side, cc1, pgnd)
        _res(refs_r[3], "5k1", "port %s CC2 Rd" % side, cc2, pgnd)
        ntc = Part(name="Thermistor_NTC", ref_prefix="RT", ref=rt, tag=rt, dest="NETLIST",
                   tool="skidl", value="NCP15XH103F03RC",
                   description="port %s hot-spot NTC, 10k at 25 C, B 3380 -- the AP33772S's "
                   "OTP and de-rating input; sits at the switch FET (LCSC C77131)" % side,
                   footprint="Resistor_SMD:R_0402_1005Metric",
                   pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
        otp += ntc[1]
        pgnd += ntc[2]
        for tag, val, a, why, fp in (
                (refs_c[0], "10uF/35V", vbus, "VBUS bulk -- USB-C's 10 uF limit for a sink", C1206),
                (refs_c[1], "100nF", v18, "V18 LDO output", C0402),
                (refs_c[2], "1uF/10V", v5v, "V5V LDO output", C0402),
                (refs_c[3], "100nF", ifb, "IFB, the current-measurement filter", C0402),
                (refs_c[4], "10uF/35V", vout, "switched VOUT bulk", C1206)):
            _cap(tag, val, "port %s %s" % (side, why), a, pgnd, fp)
        # the ideal diode: ANODE = this port's VOUT, CATHODE = the shared bus
        ui_p = _fix(ui, "LM74700QDBVRQ1", "port %s ideal-diode controller, SOT-23-6 "
                    "(LCSC C2941042)" % side, "Package_TO_SOT_SMD:SOT-23-6", range(1, 7))
        vcap, dgate = Net("P%s_VCAP" % side), Net("P%s_ORGATE" % side)
        vcap += ui_p[1]
        pgnd += ui_p[2]
        vout += ui_p[3], ui_p[6]               # EN tied to ANODE: always on
        vin += ui_p[4]
        dgate += ui_p[5]
        _cap(refs_c[5], "100nF/25V", "port %s LM74700 charge-pump cap, VCAP to ANODE" % side,
             vcap, vout)
        qo = _nfet(qd, "port %s OR-ing FET: source to the port, drain to VIN_BUS" % side)
        vout += qo["S1"], qo["S2"], qo["S3"]
        vin += qo["D"]
        dgate += qo["G"]
        # ⚠ SMB, NOT THE SOD-123FL SMF24A (voltage_check, 2026-11-13). The SMF24A clamps a
        # live plug at 37.4 V, over the AP33772S's 31 V on ISENP / VOUT and 34 V on VCC
        # (DS46176 Rev. 10-2 p.5); an SMF22A still reaches 33.5 V. The SMBJ22A's 16.9 A IPP
        # puts it at 29.1 V for the same surge (Littelfuse SMBJ datasheet p.2). Diodes' own EVB
        # (user guide Rev. 2.0 p.6-7) fits no VBUS TVS at all, so there is nothing to copy.
        # A series R on the sense pins is no answer: VCC sits 5 mohm from ISENP and is the
        # chip's supply (p.18 wants the sense traces straight off the shunt's pads).
        d = _d(d_tvs, "SMBJ22A", "port %s VBUS clamp, 600 W, 22 V standoff over the 21 V "
               "contract, 29.1 V at a live plug (LCSC C224015)" % side, "Diode_SMD:D_SMB")
        vbus_j += d[1]                         # at the connector, ahead of the choke
        gnd_j += d[2]
        d = _d(d_stb, "SS34", "port %s -> VSTBY Schottky, 40 V 3 A: the logic runs from "
               "vSafe5V before any contract (LCSC C8678)" % side, "Diode_SMD:D_SMA")
        vstby += d[1]                          # pad 1 = K
        vcc += d[2]
        if d_esd:
            for tag, net in zip(d_esd, (dp, dm)):
                d = _d(tag, "LESD5L5.0CT1G", "port %s data-line clamp, 0.5 pF -- D2/D3's "
                       "twins (LCSC C5274293)" % side)
                net += d[1]
                gnd += d[2]
    # D2/D3 (copied below) clamp J1's pair under their old names
    thru_dp, thru_dm = usb_pair["A"]
    for bus, refs in (("PDA", ("R80", "R81")), ("PDB", ("R82", "R83"))):
        for net, ref in zip((io[bus + "_SCL"], io[bus + "_SDA"]), refs):
            _res(ref, "10k", "%s pull-up to +3V3D -- 10k, not 4k7: an unplugged port's "
                 "AP33772S is UNPOWERED and this is what it is back-fed through" % net.name,
                 net, v3d)

    # ── J3: the panel data to the CM5's gadget port; J9: this MCU to a CM5 host port ──
    gad_dp, gad_dm = Net("GADGET_DP"), Net("GADGET_DM")
    if not MERGED:
        j3 = _usbc("J3", "to the brain board's CM5 USB OTG (gadget) port, stock C-to-C lead")
        gnd += j3["SH"], j3["A1"], j3["A12"], j3["B1"], j3["B12"]
        Net("J3_VBUS_NC").connect(j3["A4"], j3["B4"], j3["A9"], j3["B9"])   # dead, as R2's J2
        gad_dp += j3["A6"], j3["B6"]
        gad_dm += j3["A7"], j3["B7"]
        for tag, pin in (("R3", "A5"), ("R4", "B5")):
            _res(tag, "5k1", "J3 CC Rd: this end is the device side", j3[pin], gnd)
    u17 = _fix("U17", "TS3USB221RSER", "which panel port's data reaches the CM5 "
               "(LCSC C130085)", "Package_DFN_QFN:Texas_UQFN-10_1.5x2mm_P0.5mm", range(1, 11))
    (a_dp, a_dm), (b_dp, b_dm) = usb_pair["A"], usb_pair["B"]
    a_dm += u17[1]                             # 1D- / 1D+: J1, S low (at rest)
    a_dp += u17[2]
    b_dm += u17[3]                             # 2D- / 2D+: J2
    b_dp += u17[4]
    gnd += u17[5], u17[6]                      # OE# low: always on
    gad_dp += u17[7]
    gad_dm += u17[8]
    io["DATA_SEL"] += u17[9]
    v3d += u17[10]
    _res("R92", "100k", "DATA_SEL down: J1 is the data port until the MCU says", io["DATA_SEL"], gnd)
    _cap("C117", "100nF", "U17 VCC bypass", v3d, gnd)

    if not MERGED:
        j9 = _usbc("J9", "to a brain-board CM5 host port: this MCU's OTG_FS device, stock "
                   "C-to-C lead")
        gnd += j9["SH"], j9["A1"], j9["A12"], j9["B1"], j9["B12"]
        Net("J9_VBUS_NC").connect(j9["A4"], j9["B4"], j9["A9"], j9["B9"])   # powered here
        io["MCU_DP"] += j9["A6"], j9["B6"]
        io["MCU_DM"] += j9["A7"], j9["B7"]
        for tag, pin in (("R1", "A5"), ("R2", "B5")):
            _res(tag, "5k1", "J9 CC Rd: a device", j9[pin], gnd)

    # ── J4: the RIBBON to the optical board -- this board powers and clocks it ───────────
    # 20 ways, 1.27 mm, vertical SMD (a THT 2 x 10 at 1.27 traps its inner row: 0.27 mm between
    # pads, oneB_j0 left all eight lanes open), an IDC ribbon (wire n = pin n): eleven signals, 5 V on two
    # wires, and SEVEN grounds so that every 12.288 MHz line has a ground beside it and the
    # bit clock has one on each side. Sixteen ways left I2C SDA no wire.
    opt_5v = Net("+5V_OPT")
    j4 = Part(name="Conn_02x10", ref_prefix="J", ref="J4", tag="J4", dest="NETLIST",
              tool="skidl", value="PZ1.27-2x10P ZZ",
              description="ribbon to the optical board: five TDM lanes + clocks, I2C, emitter "
              "gate, 5 V (1.27 mm 2x10 vertical, HX PZ1.27 family as J5 on the brain)",
              footprint="Connector_PinHeader_1.27mm:PinHeader_2x10_P1.27mm_Vertical_SMD",
              pins=[Pin(num=n, func=P) for n in range(1, 21)])
    for pin, net in ((1, opt_5v), (2, opt_5v), (3, gnd), (4, io["SAI_SCK"]), (5, gnd),
                     (6, io["SAI_FS"]), (7, gnd), (8, io["SAI_SD1"]), (9, io["SAI_SD2"]),
                     (10, gnd), (11, io["SAI_SD3"]), (12, io["SAI_SD4"]), (13, gnd),
                     (14, io["SAI_SD5"]), (15, gnd), (16, io["OPT_EMIT"]), (17, gnd),
                     (18, io["I2C2_SDA"]), (19, io["I2C2_SCL"]), (20, gnd)):
        net += j4[pin]
    # the ribbon's 5 V at the HEADER as well as at the switch (C119): quality A9 found the
    # nearest capacitor to J4's 5 V ways 40 mm off (oneG_j6, 2026-11-13); the optical board's
    # 1.8 A of converter and emitter current steps through this pair of wires
    _cap("C153", "10uF/16V", "J4 ribbon 5 V, at the header", opt_5v, gnd, C0805)
    # ── J5: the 1/4 in jack. PCB-MOUNT, so no hand-soldered lug. ─────────────
    # BOM.md already specifies this Neutrik; it is a PCB part with a panel bushing,
    # and mounting it as a free-floating panel jack was what implied hand-soldered
    # lugs. Its nut clamps the endplate, so the PANEL takes the cable-yank load
    # rather than the PCB.
    # ⚠ THREE MODES OUT OF ONE JACK, AND THE PLUG PICKS BETWEEN TWO OF THEM MECHANICALLY.
    #   1. TS mono, "DIRECT"  -- a TS plug SHORTS RING TO SLEEVE. Nothing switches, nothing
    #      is told, and nothing has to detect the plug: the ring driver simply finds itself
    #      driving ground through its 220R series resistor, which is what that resistor is
    #      for. The tip carries the pickup through the relay's de-energised contact, so the
    #      instrument plays with no Pi, no firmware and no DAC.
    #   2. TRS stereo         -- tip = DAC left, ring = DAC RIGHT.
    #   3. TRS balanced mono  -- tip = +signal, ring = -signal.
    # ⚠⚠ THE JACK MODE AND THE SOURCE ARE INDEPENDENT AXES, AND AN EARLIER VERSION OF
    # THIS BLOCK CONFLATED THEM (corrected by the user, 2026-09-30). It read "balanced is a
    # processed mode", because it was cheaper: if balanced only ever happens when the Pi is
    # in the path, the Pi can emit -L on the right channel and the board needs no inverter.
    # That is true and it is the wrong shape. The two settings are:
    #
    #     jack     unbalanced mono | balanced mono | unbalanced stereo
    #     source   magnetic pickup (DIRECT) | optical pickup | MIDI
    #
    # and every combination is meant to work -- including BALANCED + DIRECT, which no amount
    # of Pi-side arithmetic can reach, because the direct path exists precisely so the Pi is
    # not in it. So the balancing lives HERE, in analog, and is source-agnostic by
    # construction. One code path instead of two, and the cold leg is correct even with the
    # firmware stopped.
    #
    # ⚠ THE SOURCE AXIS NEEDS NO NEW HARDWARE AT ALL, which is worth saying because it
    # looks like it should. "Optical pickup" and "MIDI" are both THE Pi VIA THE DAC -- they
    # differ in what the Pi computes, not in what arrives on this board -- so K1's existing
    # direct/processed throw already covers all three sources, and the Pi chooses between
    # the latter two internally.
    #
    # ⚠ AND STEREO + DIRECT COSTS NOTHING EITHER, BECAUSE K1 HAS A SPARE POLE. Pole B was
    # unused (it showed up in ERC as K1_NC_6 / K1_NC_7). Wiring its NC contact to the SAME
    # `direct` net as pole A, and its NO contact to the attenuated DAC right, makes pole B's
    # common mean "the right-hand signal, whatever the source": the pickup when direct, DAC
    # right when processed. Duplicating the mono pickup across both channels therefore falls
    # out of the relay that already selects the source, with no part and no second control.
    # The DAC's right channel already existed and was being thrown away -- it was literally
    # Net("DAC_OUT_R_NC").
    outp, ringp = Net("JACK_TIP"), Net("JACK_RING")
    j5 = Part(name="NMJ6HCD2", ref_prefix="J", ref="J5", tag="J5", dest="NETLIST", tool="skidl",
              value="NMJ6HCD2", description="1/4 in TRS output, PCB mount, panel bushing",
              footprint=TRS_FP,
              pins=[Pin(num="T", name="TIP", func=P), Pin(num="TN", name="TIP_N", func=P),
                    Pin(num="R", name="RING", func=P), Pin(num="RN", name="RING_N", func=P),
                    Pin(num="S", name="SLEEVE", func=P), Pin(num="SN", name="SLEEVE_N", func=P)])
    outp += j5["T"]
    ringp += j5["R"]
    # The switched contacts go to ground rather than floating: an open switch lug
    # beside an audio contact is an antenna, and nothing here needs to sense a plug.
    agnd += j5["S"], j5["TN"], j5["SN"], j5["RN"]

    # ── J8: the magnetic pickup, on SCREW TERMINALS (user) ───────────────────
    # It is the most likely thing anyone ever rewires -- swapping a pickup is a
    # normal thing to do to a guitar -- so it is the one field connection that is
    # neither soldered nor crimped. A pickup arrives as two bare tinned leads; a
    # screw terminal takes them as they are.
    pk_hot = Net("PICKUP_HOT")
    j8 = Part(name="SCREW_2", ref_prefix="J", ref="J8", tag="J8", dest="NETLIST", tool="skidl",
              # ONE BLADE FOR EVERY SCREW (user, 2026-11-13: "the motors use a small flat head so
              # for the screw terminals we should use a flathead as well so a single tool can do
              # both"): the SERVO42D's terminals take a 2.0 mm blade; the MX128's M2.5 slot wants
              # a wider one. So J8 is the connector board's 3.5 mm M2-slotted block, 2-way.
              value="KF350-3.5-2P",
              description="magnetic pickup in, 3.5 mm screw terminal, M2 slotted (2.0 mm blade, "
                          "as the motors' and the connector board's)",
              footprint=TERM_FP_35,
              pins=[Pin(num=1, name="HOT", func=P), Pin(num=2, name="RET", func=P)])
    # R2 TURNS J8 180 DEGREES (lead, 2026-10-29): on the dropped board its +Y entry sat in
    # string 10's clamp sweep, so the wires come in from -Y, over the board. Turned about
    # its pad row, pin 1 lands in pin 2's hole and pin 2 in pin 1's, so the two NETS swap
    # pins and every track stays where it was routed. Either screw takes either core.
    if REV == 1:
        pk_hot += j8[1]
        agnd += j8[2]         # the coil's return IS the analog reference
    else:
        pk_hot += j8[2]
        agnd += j8[1]

    # ── U1: STM32H743IIT6 -- the optical board's processor, moved here (user) ──────────
    # Everything the optical board proved about this part carries: the LQFP-176, the 25 MHz
    # HSE crystal, the 2.2 uF VCAPs, the SAI map to the five converters. What is new: the
    # converters are at the far end of a ribbon, and USB is full speed only (to the CM5).
    mcu_pins = range(1, 177)
    u1 = Part(name="STM32H743IIT6", ref_prefix="U", ref="U1", tag="U1", dest="NETLIST",
              tool="skidl", value="STM32H743IIT6",
              description="MCU, LQFP-176: SAI1-3 TDM from the optical board's five converters, "
              "OTG_FS device to the CM5, SAI4 to the audio converters (LCSC C89597)",
              footprint="Package_QFP:LQFP-176_24x24mm_P0.5mm",
              pins=[Pin(num=n, func=P) for n in mcu_pins])
    for n in MCU_VDD:
        v3d += u1[n]
    for n in MCU_VSS:
        gnd += u1[n]
    gnd += u1[PIN["VSSA"]]
    v3d += (u1[PIN["VDDA"]], u1[PIN["VREF+"]], u1[PIN["VBAT"]], u1[PIN["VDD33_USB"]],
            u1[PIN["PDR_ON"]])
    osc_in += u1[PIN["PH0"]]
    osc_out += u1[PIN["PH1"]]
    nrst += u1[PIN["NRST"]]
    boot0 += u1[PIN["BOOT0"]]
    swdio, swclk = Net("SWDIO"), Net("SWCLK")
    swdio += u1[PIN["PA13"]]
    swclk += u1[PIN["PA14"]]
    vcap1, vcap2 = Net("VCAP1"), Net("VCAP2")
    vcap1 += u1[PIN["VCAP1"]]
    vcap2 += u1[PIN["VCAP2"]]
    # ⚠ THE AP33772S INT IS A 5 V PUSH-PULL OUTPUT (from its V5V) and PD10 / PD11 are FT pins,
    # whose limit is VDD + 4 V: 4.0 V with the H743 unpowered, which the charger side can
    # outlive at start-up (voltage_check FAIL, 2026-11-13). Each INT reaches its pin through a
    # 4k7 / 10k divider: 5.33 V worst case -> 3.63 V, a 5.0 V high -> 3.40 V (over 0.7 VDD).
    int_div = {"PDA_INT": ("R123", "R124"), "PDB_INT": ("R125", "R126")}
    for name, port in MCU_IO.items():
        if name in int_div:
            at_pin = Net(name + "_MCU")
            at_pin += u1[PIN[port]]
            top, bot = int_div[name]
            _res(top, "4k7", "%s divider, top: the AP33772S's 5 V INT into an FT pin" % name, io[name], at_pin)
            _res(bot, "10k", "%s divider, bottom: 3.63 V worst case at %s" % (name, port), at_pin, gnd)
            continue
        io[name] += u1[PIN[port]]
    used = (set(MCU_VDD) | set(MCU_VSS)
            | {PIN[k] for k in ("VSSA", "VDDA", "VREF+", "VBAT", "VDD33_USB", "PDR_ON", "PH0",
                                "PH1", "NRST", "BOOT0", "PA13", "PA14", "VCAP1", "VCAP2")}
            | {PIN[p] for p in MCU_IO.values()})
    for n in mcu_pins:
        if n not in used:
            Net("U1_NC_%d" % n).connect(u1[n])
    for ref, net, what in (("TP1", swdio, "SWDIO"), ("TP2", swclk, "SWCLK"),
                           ("TP3", nrst, "NRST"), ("TP4", gnd, "GND"),
                           ("TP5", v3d, "+3V3D"),
                           ("TP6", boot0, "BOOT0 -- hold HIGH at reset for the ROM loader")):
        tp = Part(name="TestPoint", ref_prefix="TP", ref=ref, dest="NETLIST", tool="skidl",
                  value="SWD", description="SWD pad -- %s; bare copper, no component" % what,
                  footprint="TestPoint:TestPoint_Pad_D1.5mm", pins=[Pin(num=1, func=P)])
        net += tp[1]
    for k in range(14):                        # one per VDD pin, as the optical board
        _cap("C%d" % (120 + k), "100nF", "MCU VDD decoupling", v3d, gnd)
    _cap("C134", "2.2uF", "H7 core regulator cap VCAP1 -- REQUIRED, not optional",
         vcap1, gnd, C0805)
    _cap("C135", "2.2uF", "H7 core regulator cap VCAP2", vcap2, gnd, C0805)
    _cap("C136", "1uF", "VDDA / VREF+ bulk", v3d, gnd)
    _cap("C137", "100nF", "VDD33_USB bypass -- OTG_FS's transceiver", v3d, gnd)
    _cap("C138", "10uF", "+3V3D bulk at the MCU", v3d, gnd, C0805)
    _res("R7", "10k", "BOOT0 pull-down -- run from flash unless deliberately held", boot0, gnd)
    _res("R6", "10k", "NRST pull-up", nrst, v3d)
    _cap("C54", "100nF", "NRST filter -- ST's recommended reset-pin capacitor", nrst, gnd)

    # 25 MHz HSE -- the optical board's crystal, CL 10 pF, 12 pF C0G each side
    y1 = Part(name="Crystal", ref_prefix="Y", ref="Y1", tag="Y1", dest="NETLIST", tool="skidl",
              value="TAXM25M4RDBCCT2T",
              description="MCU HSE 25 MHz, CL 10 pF, ESR <= 30 ohm (LCSC C403946)",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=n, func=P) for n in range(1, 5)])
    osc_in += y1[1]
    osc_out += y1[3]
    gnd += y1[2], y1[4]
    _cap("C15", "12pF", "HSE crystal load -- C0G", osc_in, gnd)
    _cap("C16", "12pF", "HSE crystal load -- C0G", osc_out, gnd)

    # ── U15: the optical board's 5 V, switched and limited (R2's J1 switch, re-used) ──────
    # The optical board is powered from here over the ribbon and in MINIMAL mode it is OFF
    # (R2-6), so its 5 V is a switch the MCU owns: off through reset (R88), 1.6-1.8 A (R86).
    u15 = _fix("U15", "TPS2553DBVR", "optical-board 5 V switch, 1.6-1.8 A, reverse-"
               "blocking (LCSC C55266)", "Package_TO_SOT_SMD:SOT-23-6", range(1, 7))
    v5_pre = Net("V5_PRE")
    v5_pre += u15[1]
    gnd += u15[2]
    io["OPT_VBUS_EN"] += u15[3]
    io["OPT_FAULT_N"] += u15[4]
    ilim = Net("U15_ILIM")
    ilim += u15[5]
    opt_5v += u15[6]
    _res("R86", "15k 1%", "U15 ILIM: 1.61 to 1.80 A", ilim, gnd)
    _res("R87", "4k7", "U15 FAULT# up", io["OPT_FAULT_N"], v3d)
    _res("R88", "100k", "OPT_VBUS_EN down: the optical board is off until the MCU says",
         io["OPT_VBUS_EN"], gnd)
    _cap("C118", "100nF", "U15 IN bypass", v5_pre, gnd)
    _cap("C119", "10uF/16V", "J4 ribbon 5 V output, at the switch", opt_5v, gnd, C0805)

    # ── U21: +3V3D, the logic's own LDO -- the optical board's U8 and its input resistor ──
    # From V5_PRE (the buck side of FB1), as on the optical board, so the MCU's current never
    # crosses the audio side of the bead.
    u21 = Part(name="AP2114H-3.3", ref_prefix="U", ref="U21", tag="U21", dest="NETLIST",
               tool="skidl", value="AP2114H-3.3TRG1",
               description="3V3 DIGITAL LDO, SOT-223 tab, ceramic-stable (LCSC C150716)",
               footprint="Package_TO_SOT_SMD:SOT-223-3_TabPin2",
               pins=[Pin(num=1, name="GND", func=P), Pin(num=2, name="VO/TAB", func=P),
                     Pin(num=3, name="VI", func=P)])
    u21_in = Net("U21_VIN")
    gnd += u21[1]
    v3d += u21[2]
    u21_in += u21[3]
    _res("R98", "FRC2512F1R20TS", "U21 input series resistor, 1.2 R 1 % 1 W -- takes ~0.4 W "
         "off the LDO, as optical's R54 (LCSC C2960682)", v5_pre, u21_in,
         "Resistor_SMD:R_2512_6332Metric")
    _cap("C151", "10uF/16V", "U21 input bulk", u21_in, gnd, C0805)
    _cap("C152", "10uF", "U21 output -- AP2114H asks 4.7 uF ceramic", v3d, gnd, C0805)

    # STATUS LED: the warning that needs no screen (R2-6 (c)) -- the screen is the CM5's.
    led_a = Net("STATUS_LED_A")
    _res("R97", "1k", "status LED series, ~1 mA from 3.3 V", io["STATUS_LED"], led_a)
    d18 = _d("D18", "KT-0603R", "status LED, red: 'low power -- use a larger charger' "
             "(LCSC C2286)", "LED_SMD:LED_0603_1608Metric")
    gnd += d18[1]                              # pad 1 = K
    led_a += d18[2]
    # ── U2: PCM1808PWR, TSSOP-14 -- the magnetic channel's ADC ──────────────
    #   1 VREF 2 AGND 3 VCC(5 V) 4 VDD(3V3) 5 DGND 6 SCKI 7 LRCK 8 BCK 9 DOUT
    #   10 MD0 11 MD1 12 FMT 13 VINL 14 VINR
    # MD1 = MD0 = low: SLAVE mode, SCKI auto-detected at 256/384/512 fS, so the MCU owns BCK
    # and LRCK and the ADC and DAC share one clock. FMT low = I2S.
    # SCKI is the MCU's I2S2_MCK (PC6) -- a real 256 fS master clock. It was tied to BCK
    # (64 fS), which the part cannot run from.
    pk_buf, adc_in, vref = Net("PICKUP_BUF"), Net("ADC_IN"), Net("ADC_VREF")
    u2 = Part(name="PCM1808PWR", ref_prefix="U", ref="U2", tag="U2", dest="NETLIST", tool="skidl",
              value="PCM1808PWR", description="24-bit 99 dB 96 kHz stereo ADC",
              footprint=ADC_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(
                  ("VREF", "AGND", "VCC", "VDD", "DGND", "SCKI", "LRCK", "BCK", "DOUT",
                   "MD0", "MD1", "FMT", "VINL", "VINR"))])
    vref += u2["VREF"]
    agnd += u2["AGND"]
    v5 += u2["VCC"]
    v3v3 += u2["VDD"]
    gnd += u2["DGND"], u2["MD0"], u2["MD1"], u2["FMT"]
    mclk += u2["SCKI"]
    i2s_ws += u2["LRCK"]
    i2s_ck += u2["BCK"]
    i2s_sdi += u2["DOUT"]
    # BOTH inputs take the one buffered pickup (one coil), through ONE coupling cap: the ADC
    # biases its own inputs at VREF (0.5 VCC), 60k each, so the cap is the input HPF --
    # TI's 1 uF gives 2.7 Hz into one input; into the two in parallel, 5.3 Hz.
    adc_in += u2["VINL"], u2["VINR"]

    # ── U3: PCM5102APWR, TSSOP-20 -- the Pi's processed audio, made analog again ──
    #   1 CPVDD 2 CAPP 3 CPGND 4 CAPM 5 VNEG 6 OUTL 7 OUTR 8 AVDD 9 AGND 10 DEMP
    #   11 FLT 12 SCK 13 BCK 14 DIN 15 LRCK 16 FMT 17 XSMT 18 LDOO 19 DGND 20 DVDD
    # EVERY SUPPLY IS 3.3 V (AVDD/CPVDD/DVDD abs max 3.9 V). FLT, DEMP, FMT low: normal
    # latency, no de-emphasis, I2S. SCK takes the same 256 fS MCLK as the ADC (4-wire), so
    # the DAC's clock does not depend on its PLL locking to BCK. XSMT high = un-muted.
    proc = Net("AUDIO_PROC")
    capp, capm = Net("DAC_CAPP"), Net("DAC_CAPM")
    vneg, ldoo = Net("DAC_VNEG"), Net("DAC_LDOO")
    u3 = Part(name="PCM5102APWR", ref_prefix="U", ref="U3", tag="U3", dest="NETLIST", tool="skidl",
              value="PCM5102APWR", description="112 dB stereo DAC, 2.1 Vrms ground-centred out",
              footprint=DAC_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(
                  ("CPVDD", "CAPP", "CPGND", "CAPM", "VNEG", "OUTL", "OUTR", "AVDD", "AGND",
                   "DEMP", "FLT", "SCK", "BCK", "DIN", "LRCK", "FMT", "XSMT", "LDOO", "DGND",
                   "DVDD"))])
    v3v3 += u3["CPVDD"], u3["AVDD"], u3["DVDD"], u3["XSMT"]
    gnd += u3["CPGND"], u3["AGND"], u3["DGND"], u3["DEMP"], u3["FLT"], u3["FMT"]
    capp += u3["CAPP"]
    capm += u3["CAPM"]
    vneg += u3["VNEG"]
    ldoo += u3["LDOO"]
    mclk += u3["SCK"]
    i2s_ck += u3["BCK"]
    i2s_sdo += u3["DIN"]
    i2s_ws += u3["LRCK"]
    proc += u3["OUTL"]
    # ⚠ OUTR IS UNCONNECTED ON PURPOSE AND THAT IS NOW A DECISION, NOT AN OMISSION.
    # The user's call: the PI DOES THE STEREO->MONO SUM IN SOFTWARE. It already
    # chooses what to send here, so it can fold down for the jack while the
    # computer gets full stereo over the gadget port -- two different mixes from
    # one stream.
    # ⚠ THIS USED TO BE Net("DAC_OUT_R_NC") -- the right channel existed and was
    # discarded, because the Pi summed to mono for a TS jack. With a TRS jack the ring
    # IS that channel, so the whole of modes 2 and 3 is already sitting on this pin.
    proc_r = Net("DAC_OUT_R")
    proc_r += u3["OUTR"]


    # ── U5: VSTBY -> 5 V. R2's buck cell, fed from the chargers' raw 5-20 V, NOT from 24 V ──
    # Same LMR33630 cell as R2 (3.8-36 V in). Moving its input off the 24 V does two things:
    # the logic and the audio run before the boost does (see the module note), and the 5 V
    # no longer shares a rail with ten stepper drivers. At a bare 5 V contract it runs near
    # dropout (~4.8 V out) -- only until the MCU has asked for 9 V or more.
    sw, boot, fb = Net("SW"), Net("BOOT"), Net("FB")
    bgnd = gnd
    u5 = Part(name="LMR33630", ref_prefix="U", ref="U5", tag="U5", dest="NETLIST",
              tool="skidl",
              # MERGED: the ONE logic 5 V (the brain's +5V_AUX folded in, user 2026-11-13): optical
              # 1.8 A + the H743 0.58 + the isolated audio 0.3 + the CH32 side and both arms ~0.45
              # = ~3.1 A, past the 3 A part -- the 4 A sibling (open item: orderable + inductor)
              value="LMR33640 (RNX, open item)" if MERGED else BC.U_VALUE,
              description="VSTBY (5-20 V) -> 5 V synchronous buck, 1.4 MHz, %s" % (
                  "4 A: every logic 5 V on the board" if MERGED else "3 A (LCSC %s)" % BC.U_LCSC),
              footprint=BC.U_FP,
              pins=[Pin(num=n, func=P) for n in range(1, 13)])
    bgnd += u5[1], u5[11], u5[6]
    vstby += u5[2], u5[10], u5[9]
    sw += u5[3], u5[12]
    boot += u5[4]
    buck_vcc = Net("BUCK_VCC")
    buck_vcc += u5[5]
    fb += u5[7]
    Net("BUCK_PG_NC").connect(u5[8])
    # ── U6: 5 -> 3.3 V for the MCU, the hub and the converters' digital side ─
    u6 = Part(name="LDO_3V3", ref_prefix="U", ref="U6", tag="U6", dest="NETLIST", tool="skidl",
              value="AP2112K-3.3TRG1", description="5 V -> 3V3, AFTER the bead",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=i, func=P) for i in range(1, 6)])
    v5 += u6[1], u6[3]        # IN and EN; EN tied on
    gnd += u6[2]
    Net("LDO_NC").connect(u6[4])
    v3v3 += u6[5]

    # ── U7/U8: the two analog buffers ────────────────────────────────────────
    # ⚠ BOTH BUFFERS RUN AT MID-RAIL NOW (2026-09-21). They sit on 0..5 V, and neither
    # signal they carry is: the pickup is AC about 0 V and the DAC's OUTL is GROUND-CENTRED
    # (its charge pump makes the negative rail). Each op-amp input is AC-coupled and biased
    # at VMID = 2.5 V, so the whole waveform fits the rail instead of the bottom half
    # clipping at ground.
    sel, buf = Net("AUDIO_SEL"), Net("BUF_OUT")
    # The ring side's nets, declared together and BEFORE anything reaches for them.
    # They are used across three blocks that do not appear in signal order -- K1 wires
    # pole B, U12 selects, U10 attenuates -- and a net created where it is first
    # mentioned makes that order load-bearing for no reason.
    ring_in = Net("RING_BUF_IN")
    ring_buf = Net("RING_BUF_OUT")
    ring_blocked = Net("RING_BLOCKED")
    ring_gain = Net("RING_GAIN")
    ring_att = Net("RING_ATT")
    dac_r_filt = Net("DAC_R_FILT")
    u7_in, pk_in, vmid = Net("OUT_BUF_IN"), Net("PICKUP_IN"), Net("VMID")
    # TLV9061IDBVR x4 (U7, U8, U9, U11). Pins off TI SBOS839N Table 5-1, SOT-23 column,
    # read 2026-09-30: 1 OUT  2 V-  3 IN+  4 IN-  5 V+. (The SC70 and X2SON columns differ.)
    u7 = Part(name="OPAMP", ref_prefix="U", ref="U7", tag="U7", dest="NETLIST", tool="skidl",
              value="TLV9061IDBVR", description="output buffer -- drives the TS jack",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                    Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                    Pin(num=5, name="V+", func=P)])
    buf += u7[1], u7[4]       # unity-gain follower
    agnd += u7[2]
    tip_gain = Net("TIP_GAIN")
    tip_gain += u7[3]         # the pot's W1 wiper -- see U10
    v5 += u7[5]
    # ⚠ U8 IS NEW WITH THE PICKUP, AND IT IS WHAT MAKES ONE COIL FEED TWO THINGS.
    # The ADC and the relay's direct contact both want the pickup, and a magnetic
    # pickup's tone IS its loading -- hang two inputs straight on the coil and you
    # have changed the instrument's sound. One buffer, two taps off its output, so
    # the coil sees a single high impedance whichever mode is selected.
    u8 = Part(name="OPAMP", ref_prefix="U", ref="U8", tag="U8", dest="NETLIST", tool="skidl",
              value="TLV9061IDBVR", description="pickup buffer -- feeds BOTH the "
              "relay's direct contact and the ADC, so the coil sees one load",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                    Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                    Pin(num=5, name="V+", func=P)])
    pk_buf += u8[1], u8[4]
    agnd += u8[2]
    pk_in += u8[3]            # the coil through C37, biased at VMID through R8 (1M)
    v5 += u8[5]

    # ── U9: the RING buffer. Third instance of a part already on this board. ─────
    # TLV9061 again rather than a dual: U7 and U8 are already this SKU, so the ring leg
    # adds a line to the reel count and not a new part to buy, place and stock. A dual
    # would have saved one package and cost a SKU, and on a board that already carries
    # two singles that is the wrong way round.
    # ⚠ AND IT MUST BE THE SAME PART FOR AN ELECTRICAL REASON TOO, not just a purchasing
    # one. In balanced mode the tip and ring are a differential pair, and the receiver
    # rejects common-mode noise only as well as the two legs MATCH. Identical amplifier,
    # identical topology, identical 220R series and identical 2.2 uF block is what makes
    # the two legs the same impedance; a different op-amp on the cold leg would be a
    # CMRR fault that measures fine on a bench and hums in a room.
    u9 = Part(name="OPAMP", ref_prefix="U", ref="U9", tag="U9", dest="NETLIST",
              tool="skidl", value="TLV9061IDBVR",
              description="ring buffer -- the TRS cold leg, matched to U7",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                    Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                    Pin(num=5, name="V+", func=P)])
    ring_buf += u9[1], u9[4]      # unity-gain follower, exactly as U7
    agnd += u9[2]
    u9_in = Net("RING_BUF_SEL")
    u9_in += u9[3]            # U12 picks what this is: the inverted tip, or the right channel
    v5 += u9[5]

    # ── U11: THE INVERTER. This is what "balanced" actually costs. ─────────────
    # A fourth TLV9061 -- the same SKU as U7, U8 and U9, so the balancing capability adds a
    # line to the reel count and no new part to buy or stock.
    # ⚠ ITS INPUT IS U7's OUTPUT, NOT THE POT WIPER, AND THAT IS THE WHOLE POINT. The two
    # legs of a balanced pair have to carry the same magnitude at EVERY volume setting. A
    # pot wiper's source impedance varies with position -- up to a quarter of the track,
    # 2.5k on a 10k part -- and that impedance sits in series with R26, so an inverter fed
    # from the wiper would have a gain that CHANGES AS THE VOLUME MOVES. Taking `buf`
    # instead puts an op-amp output (milliohms) in front of R26, so the gain is R27/R26 and
    # nothing else, and the cold leg tracks the hot one exactly.
    # ⚠ AND R26/R27 ARE 0.1%, NOT 1%. The receiver's common-mode rejection is set by how
    # well the two legs match: a 1% pair allows 2% of gain error, which is about 34 dB of
    # CMRR, and 0.1% buys roughly 54 dB. That is the difference between a balanced output
    # that measures balanced and one that merely has three contacts. The parts cost cents.
    inv_n, inv_out = Net("INV_IN_N"), Net("INV_OUT")
    u11 = Part(name="OPAMP", ref_prefix="U", ref="U11", tag="U11", dest="NETLIST",
               tool="skidl", value="TLV9061IDBVR",
               description="unity INVERTER -- makes the balanced cold leg in analog, so "
               "balanced works with the DIRECT source too",
               footprint="Package_TO_SOT_SMD:SOT-23-5",
               pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                     Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                     Pin(num=5, name="V+", func=P)])
    inv_out += u11[1]
    agnd += u11[2]
    vmid += u11[3]            # it inverts ABOUT VMID, which is this board's signal zero
    inv_n += u11[4]
    v5 += u11[5]

    # ── U12: which of the two the ring carries. ONE BIT, and mode 1 needs none. ────
    # ⚠ UNBALANCED MONO IS NOT A SETTING HERE. A TS plug shorts ring to sleeve, so mode 1
    # is selected by the CABLE and this switch can be in either position. That is why three
    # jack modes need one control line and not two.
    # ⚠ THE SWITCH IS ON THE BUFFER'S INPUT, NOT ITS OUTPUT, and that is deliberate: an
    # analog switch's on-resistance varies with signal voltage, so passing CURRENT through
    # one is what turns it into distortion. U9's input draws picoamps, so Ron modulation has
    # nothing to act on.
    # ⚠ TS5A3159, NOT THE SN74LVC1G3157 THAT STOOD HERE (2026-10-04, the level review).
    # The switch runs on 5 V because the audio swings 0..5 V through it, and its control
    # pin is driven by a 3.3 V MCU output. The LVC part's control threshold is 0.7 x VCC
    # (SCES424 p.6): 3.48 V at this rail, ABOVE anything a 3.3 V pin can reach -- it would
    # have worked on most parts on most days. The TS5A3159 is the same SC-70-6 with the
    # same pin for pin function (TI SCDS174 p.3: 1 NO, 2 GND, 3 NC, 4 COM, 5 V+, 6 IN;
    # IN high joins COM to NO) and reads 2.4 V as high at 4.5-5.5 V (p.4). 1 ohm instead
    # of 6, same rail-to-rail signal range. Pin NAMES below are still the LVC part's:
    # B2 = NO, B1 = NC, A = COM, S = IN.
    u12 = Part(name="TS5A3159", ref_prefix="U", ref="U12", tag="U12", dest="NETLIST",
               tool="skidl", value="TS5A3159DCKR",
               description="SPDT analog switch, 2.4 V logic at a 5 V supply (LCSC C46388) "
               "-- ring = inverted tip (balanced) or the right-hand channel (stereo)",
               footprint="Package_TO_SOT_SMD:SOT-363_SC-70-6",
               # ⚠ READ OFF TI'S OWN TABLE 4-1 (SCES424O, rev June 2025), NOT REMEMBERED.
               # It was remembered first, as 1 B1 / 3 A / 4 B2, and ALL THREE SIGNAL PINS
               # WERE WRONG: the real order is 1 B2, 2 GND, 3 B1, 4 A, 5 VCC, 6 S. A route
               # was already running against the wrong netlist when the datasheet arrived.
               # This is the second time in one sitting that this file's rule -- "it is
               # checked here or it is not checked at all" -- has earned its keep, and the
               # first was the MCU pin four lines of comment away.
               pins=[Pin(num=1, name="B2", func=P), Pin(num=2, name="GND", func=P),
                     Pin(num=3, name="B1", func=P), Pin(num=4, name="A", func=P),
                     Pin(num=5, name="VCC", func=P), Pin(num=6, name="S", func=P)])
    # B1 conducts with S LOW and B2 with S HIGH (Table 4-1), which fixes the polarity of
    # JACK_MODE rather than leaving it to firmware to discover: 0 = balanced, 1 = stereo.
    inv_out += u12[3]         # B1, S low  -- balanced: the inverted tip
    agnd += u12[2]
    ring_gain += u12[1]       # B2, S high -- stereo: pole B's signal, after P1
    u9_in += u12[4]           # A: the common, into U9
    v5 += u12[5]
    jack_mode += u12[6]
    # ✅ AND THE PART IS RIGHT FOR THE JOB, from the same datasheet: "Audio signal
    # routing" is a listed application, Ron is ~6 ohm, and it is rail-to-rail on signals up
    # to VCC -- which matters because this board's audio is VMID-centred and swings most of
    # 0..5 V, so a switch that only passed a logic-level window would clip the loud half.

    # ── U10: THE GAIN, AND IT IS AN ATTENUATOR IN FRONT OF THE BUFFERS ─────────
    # AD8402ARZ10: dual 10k digital pot, SPI, 256 steps, SOIC-14, 2.7 to 5.5 V. Pinout off
    # Analog Devices AD8400/AD8402/AD8403 Rev. C (the order review read the current Rev. E
    # and found the pinout and logic levels the same), the pin configuration drawing and the pin
    # function table, which agree (read 2026-10-08):
    #   1 AGND  2 B2  3 A2  4 W2  5 DGND  6 SHDN  7 CS
    #   8 SDI   9 CLK 10 RS 11 VDD 12 W1  13 A1  14 B1
    # ⚠ WHY A POT AND NOT A GAIN THE Pi APPLIES IN SOFTWARE: BECAUSE OF MODE 1.
    # The user asked for gain control in the DIRECT mode -- the one whose whole point is
    # that the pickup reaches the jack without the Pi in the path. A software gain is by
    # definition unavailable there. This is an ANALOG attenuator, so it works in every
    # mode including the one with no firmware running, and it adds ZERO samples of
    # latency because there is no sample: it is a resistor divider that a wiper moves.
    # ⚠ AND IT SITS BEFORE THE BUFFER, WHICH IS THE WHOLE TRICK. Signal -> wiper ->
    # buffer -> jack. Put the pot AFTER the buffer and the jack sees 10k of source
    # impedance that varies with the setting; in front of a unity follower the jack
    # always sees the op-amp. The low end of each track goes to VMID rather than ground
    # because VMID IS the AC ground here (C40 is 10 uF across it) -- and because both
    # ends of the track then sit at the same DC as the wiper, so moving the wiper moves
    # no charge and the volume change does not click.
    # ⚠ 3.3 V LOGIC INTO A 5 V PART, CHECKED RATHER THAN ASSUMED: input-high is 2.4 V at
    # VDD = 5 V, and the MCU drives 3.3 V. It runs off V5 and not V3V3 because
    # the AUDIO has to fit between its rails -- the signal is VMID-centred and swings the
    # full 0..5 V, which a 3.3 V-powered pot would clip against its own substrate diodes.
    # ⚠⚠ WHY THIS PART, AND WHAT IT ASKS OF THE BOARD (user, 2026-10-08). It was chosen on
    # stock: 2,460 at the fab (C578716) where the EEPROM pots of the MCP42x1 family stood
    # under 100. Three things about it are on this board:
    #   1. NO MEMORY. Its latches are
    #      volatile. FIRMWARE: keep the gain in the MCU's flash and write BOTH channels at
    #      boot (and save a moment after the last change, not on every step).
    #   2. NO POWER-ON PRESET OF ITS OWN. The sheet promises midscale only through RS
    #      ("resets to midscale by asserting the RS pin, simplifying initial conditions at
    #      power up"), and Rev. E says outright that without it the wiper "can be at any
    #      random position at power-up" (p. 20, as the order review read it). So RS has a
    #      power-on network, R38 100k to +5V and C62 100 nF to ground: a 10 ms time
    #      constant, RS crossing 0.8 V at 1.7 ms and 2.4 V at 6.5 ms, released at about
    #      5 ms (tRS is 50 ns). With no firmware at all both wipers stand at midscale,
    #      80H, about -6 dB -- which is what the direct mode plays at until the MCU writes.
    #      ⚠ THE NETWORK FIRES ONCE PER CLEAN POWER-UP. A rail that stalls near 3 V (a
    #      bench supply in current limit) lets RS release while CS, at 0.6 x VDD, sits on
    #      its threshold: a stray CS edge then latches zeros into the tip channel, and
    #      raising the limit afterwards does not reset it. A debugger or NRST reset does
    #      not return the pot to midscale either. Only a power cycle does (off 2 s).
    #      FIRMWARE: PA5 high in the output register BEFORE it is made an output; never
    #      a CS pulse without a full word; POT_SCK / POT_SDI driven low early (floating
    #      mid-rail the part draws up to about 5 mA); both channels written 30 ms or more
    #      after +5V; and 00H around a relay release, 100 ms, then the level back
    #      (DIRECT_AC floats while the relay is energised: up to 2.4 V of step).
    #   ⚠ THE TERMINALS LEAVE 0..VDD BY A JUNCTION DROP, BRIEFLY, AND THAT IS ACCEPTED
    #      (order review, 2026-10-08): for milliseconds at switch-on with strings ringing,
    #      at every switch-off (C40 holds VMID while +5V collapses, 1 to 3 mA) and on
    #      clipping. Peaks 6 mA or less against 20 mA pulsed; continuous ratings are 5 mA
    #      at the wiper and 2.1 mA A to B for the 10k part, the board runs 0.31 mA. The
    #      same topology stood with the earlier pot.
    #   3. NO PULL-UPS ON ITS INPUTS. With the MCU erased or in
    #      reset CS would float, and a floating CS with a floating clock loads noise
    #      into the latches. R39 / R40 hold it high: 100k to +5V over 150k to ground is
    #      3.0 V (2.85 to 3.15 over the rail's 5 %), above the part's 2.4 V input-high
    #      and inside the MCU pin's 3.6 V -- PA5 is not a 5 V-tolerant pin, which is why
    #      it is a divider and not a plain pull-up to the pot's own rail. CLK and SDI are
    #      left to float in reset: with CS high the part ignores them.
    # THE WORD, on three MCU pins (it is 10 bits, two address then
    # eight data, MSB first, clocked on the rising edge and latched when CS rises: a
    # bit-banged write either way), 3.3 V logic into a 5 V part (VIH 2.4 V at 5 V), the
    # terminals' range (0 to VDD) and the sense of the wiper (FFH is the A end, full
    # level). THD 0.003 % at 1 V rms, 1 kHz.
    u10 = Part(name="AD8402ARZ10", ref_prefix="U", ref="U10", tag="U10",
               dest="NETLIST", tool="skidl", value="AD8402ARZ10",
               description="dual 10k SPI digital pot -- the OUTPUT GAIN, analog so it "
               "works in the direct mode too (LCSC C578716)",
               footprint="Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
               pins=[Pin(num=n, func=P) for n in range(1, 15)])
    agnd += u10[1], u10[5]    # AGND and DGND: one ground on this board
    v5 += u10[11]
    # SHDN is tied INACTIVE rather than left to float: SHDN low opens the A terminal and
    # puts the wiper on B, which mutes the instrument -- the one failure nobody would
    # debug quickly.
    v5 += u10[6]
    pot_cs += u10[7]
    pot_sdi += u10[8]
    pot_sck += u10[9]
    pot_rs = Net("POT_RS")
    pot_rs += u10[10]
    r38 = _r("R38", "100k", "U10 RS power-on reset to midscale, with C62 (10 ms)")
    v5 += r38[1]
    pot_rs += r38[2]
    r39 = _r("R39", "100k", "POT_CS held high in reset: top of the 3.0 V divider")
    pot_cs += r39[1]
    v5 += r39[2]
    r40 = _r("R40", "150k", "POT_CS held high in reset: bottom of the 3.0 V divider")
    pot_cs += r40[1]
    agnd += r40[2]
    # RDAC 1 = the TIP path, which is BOTH modes' hot leg and therefore the direct path too
    u7_in += u10[13]          # A1: the relay common, AC-coupled and VMID-biased
    tip_gain += u10[12]       # W1 -> U7
    vmid += u10[14]           # B1: AC ground
    # RDAC 2 = the RING path. Same 10k, same code written to both, so the two legs track
    # and a balanced pair stays balanced at every volume setting (channel match 1 %).
    ring_in += u10[3]         # A2: pole B, attenuated, AC-coupled, VMID-biased
    ring_gain += u10[4]       # W2 -> U9
    vmid += u10[2]            # B2

    # ── K1/Q1: direct vs processed. DE-ENERGISED IS DIRECT. ──────────────────
    # With no power, no Pi and no firmware the magnetic pickup reaches the jack
    # through a mechanical contact, so the instrument is still a guitar when
    # everything clever about it is off.
    # ⚠ AND IT IS NOT LATCHING, WHICH CORRECTS ME: I wrote on the optical board
    # that latching was required because "a held coil hums at the audio it is
    # switching". Wrong -- the coil is driven with DC and a static field does not
    # hum. The real cost of holding it is ~30 mA, which this rail has.
    # OMRON G6K-2F-Y-DC5 (LCSC C47190, the tape-and-reel listing fab.py orders; the tube
    # listing C326376 ran down to 44), off Omron's own terminal arrangement (TOP VIEW,
    # datasheet p.6): coil 1 (+) / 8 (-); pole A COM 3, NC 2, NO 4; pole B COM 6, NC 7, NO 5.
    # It replaces an "FRT5-class" part numbered 1..10 with no datasheet behind it -- the
    # FRT5's own maker publishes no pin diagram that could be found, and its SMD variant is
    # not stocked where this board is built. Pole B is spare.
    # BOTH THROWS ARE AC-COUPLED (C38 on the direct side, the DAC is ground-centred already),
    # and the common is held at 0 V by R15 -- so switching between them moves no DC and
    # makes no click.
    coil, direct, dac_att = Net("RELAY_COIL"), Net("DIRECT_AC"), Net("DAC_ATT")
    ring_sel = Net("RING_SEL")   # pole B common: the right-hand signal, whichever source
    k1 = Part(name="G6K-2F-Y", ref_prefix="K", tag="K1", dest="NETLIST", tool="skidl",
              value="G6K-2F-Y-DC5", description="true-bypass select; DE-ENERGISED = DIRECT "
              "(LCSC C47190)", footprint=RELAY_FP, pins=[Pin(num=i, func=P) for i in range(1, 9)])
    v5_pre += k1[1]            # the COIL is on the charger side (V5_PRE / GND, Q1); the
    coil += k1[8]              # contacts are in the audio: G6K coil-contact 1.5 kV
    sel += k1[3]
    direct += k1[2]
    dac_att += k1[4]
    # ── POLE B: the right-hand signal, and it costs NOTHING because the pole existed ──
    # Pole A answers "what does the TIP carry"; pole B answers the same question for the
    # RING, off the same coil and therefore always in agreement with it. NC is direct and
    # NO is processed on both poles, so:
    #     direct   -> pole B carries the PICKUP, the same signal as the tip. That IS
    #                 "stereo + direct duplicates the mono pickup across both channels",
    #                 and it needs no control of its own.
    #     processed-> pole B carries the DAC's RIGHT channel, which the Pi is free to make
    #                 genuinely different from the left.
    # ⚠ BOTH NC CONTACTS SHARE ONE NET AND ONE COUPLING CAP. k1[7] joins `direct`, which
    # C38 already feeds from the pickup buffer -- the two poles want the identical signal,
    # so a second cap would only add a second high-pass corner to mismatch against the
    # first. U8 buffers the coil precisely so it can be tapped more than once.
    direct += k1[7]
    ring_att += k1[5]
    ring_sel += k1[6]
    # AO3400A SOT-23: 1 G  2 S  3 D -- AOS datasheet rev 3 p.1 package drawing (D alone on
    # its side, G at the pin-1 dot), read 2026-09-30. K1 re-read the same day off Omron's
    # G6K-2F-Y terminal diagram (p. B-83): matches the list above, contact for contact.
    q1 = Part(name="Q_NMOS", ref_prefix="Q", ref="Q1", tag="Q1", dest="NETLIST", tool="skidl",
              value="AO3400A", description="relay coil driver (LCSC C20917)",
              footprint="Package_TO_SOT_SMD:SOT-23",
              pins=[Pin(num=1, name="G", func=P), Pin(num=2, name="S", func=P),
                    Pin(num=3, name="D", func=P)])
    gnd += q1[2]
    coil += q1[3]

    # ── L1 / FB1: the buck's output, and the ONE place the rails join ────────
    l1 = Part(name="L", ref_prefix="L", ref="L1", tag="L1", dest="NETLIST", tool="skidl",
              # ⚠ A PART, CHOSEN FOR SATURATION AT THE IC'S LIMIT (2026-10-05). TI SNVSA24
              # 9.2.2.2: "Using a rating near 1.6 A will enable the LMR16006 to current
              # limit without saturating the inductor. This is preferable to the LMR16006
              # going into thermal shutdown mode and the possibility of damaging the
              # inductor if the output is shorted". The limit is 1.2 A typical, 1.7 max.
              # APV PNR3015 (its sheet, 2023-12; guaranteed / typical, 30 % drop):
              #   47 uH  0.65 / 0.88 A saturation, 0.45 / 0.58 A rms   <- what was here
              #   22 uH  1.15 / 1.40,  0.75 / 0.90
              #   15 uH  1.40 / 1.80,  1.00 / 1.20                     <- this
              #   10 uH  1.50 / 2.00,  1.50 / 2.00 (10,880 in stock: the alternate)
              # 15 uH is the largest value whose GUARANTEED saturation clears the typical
              # limit, and its typical clears the maximum. Same series, same land.
              # Ripple 5 x (1 - 5 / 24) / (15 uH x 700 kHz) = 0.38 A, so the 0.257 A worst
              # load peaks at 0.45 A. LCSC C19634062, 3 x 3 x 1.5.
              # MERGED: L1 carries every logic 5 V (~3.1 A, voltage_check FAIL on the 3 A
              # SWPA5040). Changjiang FXL0630-4R7-M, 4.7 uH (TI's value at 1.4 MHz, as the
              # cell), 6 A rated / 9 A saturation, 33 mohm, 6.45 x 6.6 x 2.8 (JLC listing
              # C167220, 149k stock; read which figure is Isat on cjiang's sheet). The 5.4 x
              # 5.2 FXL0530 saturates at 5 A -- not above the LMR33640's low-side limit, which
              # TI's rule (SNVSAN3F 9.2.2.4, the cell's) asks the inductor to clear.
              value="PNR3015-150M" if REV == 1 else ("FXL0630-4R7-M" if MERGED else BC.L1_VALUE),
              description=("15 uH buck output inductor, Isat 1.4 A, SHIELDED -- it sits on "
                           "the same board as a magnetic pickup's preamp"
                           if REV == 1 else (
                               "buck output inductor, 4.7 uH +-20 % shielded molded, 6 A / 9 A, "
                               "33 mohm, 6.45 x 6.6 x 2.8 (LCSC C167220)" if MERGED else BC.L1_DESC)),
              # APV's own land (its sheet's a 1.0, b 1.1, c 2.7): pads 1.1 x 2.7 with 1.0
              # between them. The Taiyo Yuden NR-30xx land this used is 0.8 x 2.7 with 1.4,
              # which left the part's 0.9 mm terminals 0.25 mm short of pad on each inner side
              footprint="Steel:L_APV_PNR3015" if REV == 1 else (
                  "Inductor_SMD:L_Changjiang_FXL0630" if MERGED else BC.L1_FP),
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw += l1[1]
    v5_pre += l1[2]
    # ⚠ V5_PRE BECOMES +5V THROUGH A BEAD, NOT A WIRE. The buck's return stays on
    # PWR_GND and the board's 5 V rides the signal ground; the bead is where the two
    # domains meet, deliberately and in one identifiable place. Route it as the
    # single crossing it is -- if copper joins the rails anywhere else, this part
    # is decoration.
    fb1 = Part(name="FerriteBead", ref_prefix="FB", ref="FB1", tag="FB1", dest="NETLIST",
               tool="skidl", value="BLM18KG601SN1D",
               description="5 V rail split: buck side to board side. 600 ohm at "
               "100 MHz, 1.3 A, 150 mohm (LCSC C85833) -- the 200 mA bead this replaces "
               "sat under the board's 257 mA worst case",
               footprint="Inductor_SMD:L_0603_1608Metric",
               pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    # NOW THE ISOLATED SUPPLY'S FILTER: U30's raw 9 V -> FB1 -> U31 (the audio's 5 V LDO)
    iso9_raw, iso9 = Net("ISO9_RAW"), Net("ISO9")
    iso9_raw += fb1[1]
    iso9 += fb1[2]
    _isolation(gnd, agnd, v5_pre, v3d, v3v3, v5, iso9_raw, iso9, io, iso)

    # ── diodes ───────────────────────────────────────────────────────────────
    # 60 V, not 40: its cathode is the switch node, which stands at VIN, and the rail
    # clamp's catalogue point is 38.9 V -- 1.1 V under a 40 V part before any ring.
    if REV == 1:
        d1 = _d("D1", "DSS16", "buck catch diode, 60 V 1 A -- the LMR16006 is ASYNCHRONOUS, so "
                "this is required, not optional", "Diode_SMD:D_SOD-123")
        sw += d1[1]
        pgnd += d1[2]
    for tag, net in (("D2", thru_dp), ("D3", thru_dm)):
        d = _d(tag, "LESD5L5.0CT1G", "panel USB data-line clamp, 0.5 pF, bidirectional "
               "(LCSC C5274293) -- J1 is the port a stranger plugs into")
        net += d[1]
        gnd += d[2]
    # ⚠ PAD 1 IS THE CATHODE AND IT GOES TO +5V (2026-10-04). It was drawn the other way
    # round -- cathode on the FET's drain, anode on the rail -- which is a diode forward
    # across the supply every time the relay is switched on: 5 V through a 150 mA diode
    # into a FET that is fully enhanced. Nothing in the build could see it (two nets, two
    # pads, either way round routes clean); the manual polarity review did.
    d4 = _d("D4", "1N4148WT", "coil flyback, cathode to V5_PRE (LCSC C917006) -- the coil is "
            "an inductor and the FET is not")
    v5_pre += d4[1]
    coil += d4[2]
    # D5 IS THE PHANTOM GUARD'S CLAMP and it sits INSIDE the DC block: a blocking
    # capacitor stops the 48 V but passes the insertion edge straight through.
    blocked = Net("OUT_BLOCKED")
    d5 = _d("D5", "ESD5B5.0ST1G", "bidirectional 5 V TVS (LCSC C93623): catches the "
            "insertion edge C1 passes through. The node it sits on idles at VMID and swings "
            "0..5 V, inside its 5.0 V working voltage")
    blocked += d5[1]
    agnd += d5[2]
    # ⚠ D7 IS NOT OPTIONAL, AND FINDING THAT OUT IS THE REASON THE RING TOOK MORE THAN
    # A BUFFER. On a TRS-to-XLR cable the RING IS PIN 3, and a desk with phantom power on
    # puts +48 V down pin 3 through 6.81k exactly as it does down pin 2. The tip has been
    # guarded since this board was drawn -- R9, C1 and D5 -- and a ring added without the
    # same three parts would be a brand-new 48 V path onto a brand-new op-amp. So the cold
    # leg is a part-for-part mirror of the hot one, which the matching argument at U9 wants
    # anyway: R20 for R9, D7 for D5, C41 for C1, R21 for R10.
    d7 = _d("D7", "ESD5B5.0ST1G", "RING phantom-guard clamp -- the mirror of D5. A TRS "
            "plug's ring lands on XLR pin 3, which carries +48 V through 6.81k just like "
            "pin 2, and C41 blocks the DC but passes the insertion edge")
    ring_blocked += d7[1]
    agnd += d7[2]
    # ⚠ A 24 V CLAMP, AND THE 1.5 kW ONE (motor_ctrl.py's D8 has the table). It breaks
    # down at 26.7 to 29.5 V and its voltage then rises with the current it is handed, to
    # 38.9 V at its rated pulse -- and that pulse is 10.3 A for an SMAJ, 38.6 A for this
    # SMCJ. Behind it are the optical board's LMR33630 (36 V operating, 38 V absolute),
    # which has no clamp of its own, and both bucks' switch nodes; the SMCJ reaches 36 V at
    # 26.7 A of surge and 38 V at 34.9 A, where the SMAJ did at 7.1 and 9.3 A -- under what
    # a brick limiting at 150 % can hand it. The brick is 24 V +-3 % (24.72 V), two volts
    # under the lowest breakdown. If the brick ever sat at its over-voltage threshold
    # (105 to 135 %: 25.2 to 32.4 V) instead of tripping, this part would conduct
    # continuously and fail SHORT, which hiccups the supply: a brick fault ends as a dead
    # rail, not as 32 V on everything.


    # ── R2's relay, jack-mode, input and buck passives (output_panel's resistor list) ─────
    _res("R5", "100R", "relay gate series", relay, q1[1])
    _res("R36", "100k", "relay gate pull-down -- off through reset", q1[1], gnd)
    _res("R37", "100k", "JACK_MODE pull-down -- balanced through reset: on the MCU side, "
         "where the pin floats; U34 is the F part, LOW on an open input", io["JACK_MODE"], gnd)
    _res("R8", "1M", "pickup input bias to VMID -- and the LOAD the pickup sees, which "
         "sets its tone: 1M is a typical amplifier input", pk_in, vmid)
    _res("R9", "220R", "output series -- bounds a phantom-power fault and C1's inrush",
         buf, blocked)
    _res("R10", "100k", "output bleed -- stops the DC block thumping on unplug", outp, agnd)
    # LMR33630: VFB 1.0 V, so 100k / 24k9 is 5.02 V, as R2 and the optical board's U13
    _res("R11", "100k", "buck feedback divider, top", v5_pre, fb)
    _res("R12", "24k9 1%", "buck feedback divider, bottom", fb, bgnd)
    _cap("C1", "2.2uF/100V", "OUTPUT DC BLOCK -- the phantom guard, see above", blocked, outp,
         C1210)
    _cap("C2", "10uF/50V", "buck input bulk (VSTBY, 5-20 V) -- 1206 for the DC-bias "
         "derating", vstby, bgnd, C1206)
    _cap("C3", "100nF/50V", "buck input HF bypass", vstby, bgnd)
    _cap("C17", "10uF/50V", "buck input bulk, the buck cell's second", vstby, bgnd, C1206)
    _cap("C18", "100nF/50V", "buck input HF bypass, pins 10 and 11", vstby, bgnd)
    _cap("C63", "1uF/25V", "buck VCC bypass", buck_vcc, bgnd)
    _cap("C4", "100nF/50V", "buck bootstrap", boot, sw)
    for tag in ("C5", "C6", "C64"):
        _cap(tag, "22uF/16V", "5 V bulk, BUCK SIDE of the bead", v5_pre, bgnd, C0805)
    _cap("C65", "100nF/50V", "buck output HF bypass", v5_pre, bgnd)
    if not MERGED:                     # merged: one ground, no star tie
        _res("R60", "0R", "ground tie, PWR_GND to GND -- the instrument's star point. 1206: it "
             "carries the buck's input current home (<= ~1.3 A on a 5 V contract)",
             pgnd, gnd, "Resistor_SMD:R_1206_3216Metric")   # GND: AGND is isolated
    for tag, val, net, ref, desc in (
            ("C7", "10uF", v5, agnd, "5 V bulk, board side of the bead"),
            ("C8", "100nF", v5, agnd, "5 V HF bypass"),
            ("C9", "10uF", v3v3, gnd, "3V3 (converters) bulk"),
            ("C58", "1uF", v5, gnd, "LDO input -- AP2112 asks for 1 uF at IN"),
            ("C59", "100nF", v5, agnd, "U8 bypass"),
            ("C60", "100nF", v5, agnd, "U7 bypass"),
            ("C13", "100nF", v5, agnd, "ADC analog bypass"),
            ("C14", "100nF", v3v3, agnd, "DAC AVDD bypass -- 3V3, never 5 V (abs max 3.9)")):
        _cap(tag, val, desc, net, ref, C0805 if val == "10uF" else C0402)

    # ── J10: THE BRAIN BOARD'S POWER -- AND THE BOOST IS THERE, NOT HERE (2026-11-12) ───────
    # The first draft carried R2-6's LM5122 boost on this board, and the board came out at
    # 0.70 courtyard fill against 0.41-0.47 for the dense boards that route at the bar
    # (output_panel 0.47, motor_ctrl 0.41): it would not have routed. The boost was ~1000 mm2
    # of it -- a 17 mm inductor, two 10 mm polymers, twelve 1210s, the controller, two power
    # FETs -- and EVERY watt it makes is spent on the brain board (ten motors, the CM5, the
    # lights). It is also a 15 A-peak, 250 kHz switcher, and this is the board with the
    # magnetic pickup's preamp on it. So it moved to the brain board with the 24 V switch,
    # and this board hands over the chargers' OR-ed 5-20 V, measured, plus four logic ways
    # (harness.BRAIN_SIGNAL): BRAIN_EN and LOW_PWR out, PWR_BTN and BRAIN_PG back.
    #   BRAIN_EN low (reset, R94) -> the brain board's boost and 24 V stay off, so nothing
    #     big starts until this MCU has read both chargers and accepted a contract.
    #   LOW_PWR high              -> MINIMAL mode: the brain board leaves the CM5 off
    #     (R2-6). A wire, so it works with the CM5 down -- which USB could not.
    #   PWR_BTN                   -> the power button, read on the brain board (the UI
    #     station hangs beside it now) and passed here, so "off" can quiet this board too.
    #   BRAIN_PG                  -> the brain board's 24 V is good.
    # ⚠ THE POWER IS ON TWO 6-WAY XH LEADS IN PARALLEL, J10 + J12, SIZED FROM THE WORST CASE
    # (lead, 2026-11-13). PD caps CURRENT, not power (3 A below 20 V; 5 A only at 20 V on a
    # 5 A cable), so a lower voltage never means more amps; but two ports at the SAME voltage
    # share through the ideal diodes: 6.5 A from two 65 W chargers, up to 10 A from two 5 A
    # contracts. At <= 2.5 A a way that is 4 VIN + 4 GND ways: two VIN and two GND on each
    # of two 6-way XH leads (harness.BRAIN_POWER; the first cut had ONE VIN way a lead), 22 AWG -- the two-gauge rule (user, 11-01) allows no other wire, so a
    # VH 2-way on 18 AWG tried first was reverted. Firmware also keeps ONE port carrying (the
    # other asked for a lower voltage, so its diode blocks): one charger is <= 5 A, 1.25 A a
    # way. A missing lead is SENSED on way 3 (below), so the double fault -- one lead out,
    # two 5 A chargers sharing, 5 A a way -- is caught by firmware, not an install note.
    # ⚠ AND THE COPPER: J1/J2 -> Q4..Q7 -> R112 -> J10/J12 is a 10 A path, pour it, do not trace it.
    # ⚠ INRUSH IS THE BRAIN BOARD'S TO LIMIT: VIN reaches its input the moment a port's
    # switch closes, so its boost input sits behind a soft-start switch gated by BRAIN_EN.
    vin_brain = Net("VIN_BRAIN")
    vin_brain.drive = Pin.drives.POWER
    link = {"GND": gnd}
    for k in ("BRAIN_EN", "LOW_PWR", "PWR_BTN", "BRAIN_PG"):
        link[k] = Net("LINK_" + k)
    if MERGED:
        # THE BRAIN, BUILT ON THIS BOARD (user, 2026-11-13: "the output board becomes the brain
        # board"). On PWR_GND -- the ground its leads landed on (J10/J12 ways 2/5), so the 24 V
        # boost's and the motors' return currents reach the chargers without crossing GND, and
        # the R60 star stays the one place the two meet. Its parts are renumbered +200 (U1 ->
        # U201) so the two circuits' refs never meet.
        import brain as BR
        from builtins import default_circuit
        before = {id(pt) for pt in _circuit_parts()}
        ours = {n.name for n in default_circuit.nets}
        nets0 = {id(n) for n in default_circuit.nets}
        mg = {"gnd": pgnd, "vin": vin_brain, "v5a": v5_pre}
        if FOLD:
            mg["v33"] = v3d
            mg["mcu"] = dict({k: io[k] for k in FOLD_IO}, NRST=nrst, BOOT0=boot0)
        bn = BR.brain(mg)
        # the brain's own nets that share a name with this board's (its CH32's NRST, OSC_IN,
        # SWDIO ... beside the H743's) get a B_ prefix: two nets, two names
        # a trailing number is skidl's collision suffix (NRST1) UNLESS brain.py itself wrote
        # that name (SW5, FB5: its U5 buck's) -- read from its Net("...") literals
        import re as _re2
        declared = set(_re2.findall(r'Net\("([^"%]+)"\)', open(BR.__file__, encoding="utf-8").read()))
        for n in list(default_circuit.nets):
            if id(n) in nets0 or (n.name in declared and n.name not in ours):
                continue
            if n.name.rstrip("0123456789") in ours | {x + "_" for x in ours}:
                base = n.name
                while base and base[-1].isdigit() and base[:-1] in ours:
                    base = base[:-1]
                if base in ours:
                    n.name = "B_" + base
        _renumber([pt for pt in _circuit_parts() if id(pt) not in before], 200)
        for k in ("BRAIN_EN", "LOW_PWR", "PWR_BTN", "BRAIN_PG"):
            link[k] += bn["link"][k]
        gad_dp += bn["gadget"][0]
        gad_dm += bn["gadget"][1]
        io["MCU_DP"] += bn["oblink"][0]
        io["MCU_DM"] += bn["oblink"][1]
        for k, pu in (("PWR_LEAD1_N", "R120"), ("PWR_LEAD2_N", "R122")):
            _res(pu, "10k", "%s: no lead any more (merged) -- held HIGH, firmware ignores it" % k,
                 io[k], v3d)
    else:
        j10 = Part(name="S6B-XH-SM4-TB", ref_prefix="J", ref="J10", tag="J10", dest="NETLIST",
                   tool="skidl", value="S6B-XH-SM4-TB",
                   description="to the brain board: the chargers' 5-20 V, lead 1 of 2 in parallel "
                               "(harness.BRAIN_POWER)",
                   footprint=XH6_FP,
                   pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(harness.BRAIN_POWER)]
                   + [Pin(num="MP", name="MP", func=P)])
        j12 = Part(name="S6B-XH-SM4-TB", ref_prefix="J", ref="J12", tag="J12", dest="NETLIST",
                   tool="skidl", value="S6B-XH-SM4-TB",
                   description="to the brain board: the chargers' 5-20 V, lead 2 of 2 in parallel "
                               "(harness.BRAIN_POWER)",
                   footprint=XH6_FP,
                   pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(harness.BRAIN_POWER)]
                   + [Pin(num="MP", name="MP", func=P)])
        harness.check_ways(harness.BRAIN_POWER, ("VIN",), ("GND", harness.NC), where="J10/J12")
        # WAY 3 IS A PRESENCE LOOP (lead, 2026-11-13): the brain board straps it to GND, so a lead
        # that is in reads LOW. Either one HIGH and firmware caps the input at ONE charger's
        # contract (the other asked for a lower voltage, its diode blocks) or holds BRAIN_EN off --
        # the unplugged-lead double fault, sensed instead of written in INSTALL_NOTES.
        for j, k, ser, pu in ((j10, "PWR_LEAD1_N", "R119", "R120"),
                              (j12, "PWR_LEAD2_N", "R121", "R122")):
            vin_brain += j[1], j[6]
            pgnd += j[2], j[5]
            loop = Net("%s_LOOP" % j.ref)
            loop += j[3]
            Net("%s_NC_4" % j.ref).connect(j[4])
            _res(ser, "1k", "%s presence loop in from the cable" % j.ref, loop, io[k])
            _res(pu, "10k", "%s presence pull-up: HIGH = lead missing" % j.ref, io[k], v3d)
        j11 = Part(name="S6B-PH-SM4-TB", ref_prefix="J", ref="J11", tag="J11", dest="NETLIST",
                   tool="skidl", value="S6B-PH-SM4-TB",
                   description="to the brain board: enable, low-power mode out; button, "
                               "power-good in (harness.BRAIN_SIGNAL)",
                   footprint=PH6_FP,
                   pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(harness.BRAIN_SIGNAL)]
                   + [Pin(num="MP", name="MP", func=P)])
        for i, w in enumerate(harness.BRAIN_SIGNAL):
            link[w] += j11[i + 1]
    if FOLD:
        # one board, one MCU: no cable to bound, so the link lines are the MCU's own nets; the
        # brain section's R252 / R261 are the pull-downs, R117 the button's pull-up
        for k in ("BRAIN_EN", "LOW_PWR", "PWR_BTN"):
            io[k] += link[k]
        _res("R117", "10k", "PWR_BTN pull-up: Q212 drives it open-drain", io["PWR_BTN"], v3d)
    else:
        for k, ref in (("BRAIN_EN", "R113"), ("LOW_PWR", "R114")):
            _res(ref, "1k", "%s out to the cable -- bounds a short on 300 mm of wire" % k,
                 io[k], link[k])
        for k, ref, pu in (("PWR_BTN", "R115", "R117"), ("BRAIN_PG", "R116", "R118")):
            _res(ref, "1k", "%s in from the cable" % k, link[k], io[k])
            _res(pu, "10k", "%s pull-up: the brain board drives it open-drain" % k, io[k], v3d)
        _res("R94", "100k", "BRAIN_EN down: the brain board stays off through reset",
             io["BRAIN_EN"], gnd)
        _res("R93", "100k", "LOW_PWR down: full mode unless firmware says otherwise",
             io["LOW_PWR"], gnd)
    if not MERGED:                     # merged: the brain's own inlet clamp (D201) is it
        d = _d("D19", "SMF24A", "VIN_BRAIN clamp at the cable, 200 W (LCSC C169430)",
               "Diode_SMD:D_SOD-123F")
        vin_brain += d[1]
        pgnd += d[2]
    for k in range(2):
        _cap("C%d" % (92 + k), "22uF/35V", "VIN_BUS bulk -- the brain board's boost carries "
             "its own input caps", vin, pgnd, C1210)
    _cap("C96", "100nF/50V", "VIN_BUS HF bypass", vin, pgnd)
    _cap("C97", "100nF/50V", "VIN_BRAIN HF bypass at J10", vin_brain, pgnd)

    # ── U16: INA226 on VIN_BRAIN -- everything the brain board draws (R2-4 / R2-6) ───────
    # The chargers' totals come from each AP33772S's CURRENT register; this is the brain
    # board's share, at the cable, and its ALERT is wired (R2-6: a sag acted on in
    # microseconds, not at the next poll).
    u16 = _fix("U16", "INA226AIDGSR", "brain-board volts and amps, I2C2 at 0x40 (LCSC C49851)",
               "Steel:MSOP-10_3x3mm_P0.5mm_Tight", range(1, 11))
    gnd += u16[1], u16[2], u16[7]              # A1, A0 low: 0x40; GND
    io["INA_ALERT_N"] += u16[3]
    io["I2C2_SDA"] += u16[4]
    io["I2C2_SCL"] += u16[5]
    v3d += u16[6]
    vin_brain += u16[8], u16[9]                # VBUS, IN-: the load side
    vin += u16[10]                             # IN+: the supply side
    # ⚠ 2512, NOT 0805 (output_power finish, 2026-11-13): VIN_BUS and VIN_BRAIN are In2 pours
    # carrying up to 10 A, and an 0805's 1.0 x 1.4 mm lands cannot take the via array that joins
    # a land to them -- the router's single via was the path's choke point (quality A1). The
    # brain's own 4 mohm 2512 (R109) lands take one; 10 A is 40 mV of the INA226's 81.9 and
    # 0.4 W of its 2 W. FIRMWARE: the INA226 calibration is for 4 mohm, not 5.
    _res("R112", "4mR 1W", "brain-board shunt, 4 mohm 2512 (C326588, as brain R109): 10 A is 40 mV "
         "of the INA226's 81.9, 0.4 W", vin, vin_brain, "Resistor_SMD:R_2512_6332Metric")
    _cap("C116", "100nF", "U16 VS bypass", v3d, gnd)
    for net, ref in ((io["I2C2_SCL"], "R84"), (io["I2C2_SDA"], "R85"),
                     (io["INA_ALERT_N"], "R91")):
        _res(ref, "4k7", "%s pull-up" % net.name, net, v3d)
    # ── the analog rewrite's parts (2026-09-21) ────────────────────────────────
    dac_filt = Net("DAC_FILT")
    for tag, val, a, b, desc, fp in (
            # U2, PCM1808: VREF, VCC and VDD each 0.1 uF + 10 uF (TI 10.1.4 / 8.2 C3-C5);
            # C13 is VCC's 0.1 uF
            ("C19", "100nF", vref, agnd, "ADC VREF", None),
            ("C20", "10uF", vref, agnd, "ADC VREF bulk", C0805),
            ("C21", "10uF", v5, agnd, "ADC VCC bulk", C0805),
            ("C22", "100nF", v3v3, gnd, "ADC VDD", None),
            ("C23", "10uF", v3v3, gnd, "ADC VDD bulk", C0805),
            ("C24", "1uF", pk_buf, adc_in, "ADC input coupling (TI's 1 uF)", C0805),
            # U3, PCM5102A, Figure 33: AVDD / CPVDD / DVDD / LDOO each 0.1 + 10 uF, the charge
            # pump's flying cap and VNEG 2.2 uF each; C14 is AVDD's 0.1 uF
            ("C25", "10uF", v3v3, agnd, "DAC AVDD bulk", C0805),
            ("C26", "100nF", v3v3, gnd, "DAC CPVDD", None),
            ("C27", "10uF", v3v3, gnd, "DAC CPVDD bulk", C0805),
            ("C28", "100nF", v3v3, gnd, "DAC DVDD", None),
            ("C29", "10uF", v3v3, gnd, "DAC DVDD bulk", C0805),
            ("C30", "100nF", ldoo, gnd, "DAC LDOO", None),
            # C31 is the 0402 (6.3 V, on a 1.8 V pin): the 0805 stood in the mouth of the
            # channel the inlet's full current leaves by, and no other site clears both the
            # DAC's pins and the inlet's body
            ("C31", "10uF", ldoo, gnd, "DAC LDOO bulk", None),
            ("C32", "2.2uF", capp, capm, "DAC charge-pump flying cap", C0805),
            ("C33", "2.2uF", vneg, gnd, "DAC VNEG", C0805),
            ("C34", "2.2nF C0G", dac_filt, agnd, "DAC output filter, with R13 "
             "(TI's recommended 470R + 2.2 nF)", None),
            # U4, CH334F: V5 >= 1 uF, VDD33 0.1 + 10 uF (C12 is the 0.1)
            # the buffers
            ("C37", "100nF C0G", pk_hot, pk_in, "pickup input coupling -- 1.6 Hz into R8's "
             "1M. C0G: a coupling cap in the coil's own path must not have a voltage "
             "coefficient", "Capacitor_SMD:C_1206_3216Metric"),
            # 10 uF, not 1 (pre-order review, 2026-10-06): 1 uF into 10 k is 16 Hz, which
            # is 0.26 dB down and 14 degrees of lead at the low C (65 Hz) on THIS throw only
            # -- the relay's other throw is the DAC, flat to DC, so switching sources moved
            # the bass. 1.6 Hz moves nothing audible, and a class-II part with almost no
            # signal across it has no voltage coefficient to distort with.
            ("C38", "10uF", pk_buf, direct, "direct-path coupling to the relay -- 1.6 Hz into "
             "R15's 10k, flat through the lowest string (C2, 65 Hz)", C0805),
            ("C39", "1uF", sel, u7_in, "output buffer input coupling (1.6 Hz into R16)", C0805),
            ("C40", "10uF", vmid, agnd, "VMID reservoir", C0805),
            # ── the RING leg ─────────────────────────────────────────
            ("C41", "2.2uF/100V", ring_blocked, ringp, "RING DC BLOCK -- C1's mirror, and a "
             "safety part for the same reason: 100 V is the RATING, because it sits charged "
             "to 48 V for the duration of a phantom fault",
             "Capacitor_SMD:C_1210_3225Metric"),
            ("C42", "1uF", ring_sel, ring_in, "ring path coupling, off K1 POLE B -- "
             "C39's mirror on the other pole", C0805),
            ("C43", "100nF", v5, agnd, "U9 bypass", None),
            ("C44", "100nF", v5, agnd, "U10 bypass -- the pot's supply is also the reference "
             "its wiper divides, so it gets its own", None),
            ("C62", "100nF", pot_rs, agnd, "U10 RS power-on reset, with R38: holds RS low "
             "for about 5 ms after the rail stands (10 ms time constant), so both wipers start at midscale", None),
            ("C45", "2.2nF C0G", dac_r_filt, agnd, "DAC right output filter, with R23 -- "
             "C34's mirror", None),
            ("C46", "100nF", v5, agnd, "U11 bypass", None),
            ("C47", "100nF", v5, agnd, "U12 bypass", None)):
        c = _c(tag, val, desc, fp) if fp else _c(tag, val, desc)
        a += c[1]
        b += c[2]
    for tag, val, a, b, desc in (
            ("R13", "470R", proc, dac_filt, "DAC output filter, with C34"),
            ("R14", "10k", dac_filt, dac_att, "DAC -6 dB with R15: 2.1 Vrms (5.9 Vpp) is "
             "more than a 5 V rail carries; ~3 Vpp after this"),
            ("R15", "10k", sel, agnd, "relay common to 0 V -- no DC step when it switches"),
            ("R16", "100k", u7_in, vmid, "output buffer bias to VMID"),
            ("R17", "100k", v5, vmid, "VMID divider, top"),
            ("R18", "100k", vmid, agnd, "VMID divider, bottom"),
            # ── the RING leg: every one of these is the mirror of a TIP part ─────────
            ("R20", "220R", ring_buf, ring_blocked, "ring output series -- R9's mirror, and "
             "the part that makes a TS PLUG SAFE: it shorts ring to sleeve, so this resistor "
             "is what the ring buffer drives in mode 1"),
            ("R21", "100k", ringp, agnd, "ring output bleed -- R10's mirror"),
            ("R22", "100k", ring_in, vmid, "ring buffer bias to VMID -- R16's mirror"),
            ("R23", "470R", proc_r, dac_r_filt, "DAC right output filter, with C45 -- R13's "
             "mirror. The right channel needs TI's filter for the same reason the left does"),
            ("R24", "10k", dac_r_filt, ring_att, "DAC right -6 dB with R25 -- R14's mirror. "
             "2.1 Vrms is more than a 5 V rail carries on EITHER channel"),
            ("R25", "10k", ring_att, agnd, "ring attenuator bottom -- R15's mirror, and it "
             "holds the node at 0 V so nothing steps when the DAC starts"),
            ("R26", "10k 0.1%", buf, inv_n, "inverter input -- 0.1% because this pair IS "
             "the balanced output's CMRR (1% would be ~34 dB, 0.1% ~54 dB)"),
            ("R27", "10k 0.1%", inv_n, inv_out, "inverter feedback -- the other half of "
             "that pair, and it must be the SAME tolerance and ideally the same reel"),
            ("R28", "10k", ring_sel, agnd, "pole B common to 0 V -- R15's mirror, so the "
             "ring throw makes no DC step either")):
        r = _r(tag, val, desc)
        a += r[1]
        b += r[2]
    if MERGED:
        # nets joined across the two circuits keep ONE stable name (skidl picks either side's,
        # and the A16 / quality declarations key on it)
        # (skidl's merge_names honours fixed_name)
        for net in (gad_dp, gad_dm, io["MCU_DP"], io["MCU_DM"]) + (
                tuple(io[k] for k in ("BRAIN_EN", "LOW_PWR", "PWR_BTN")) if FOLD else ()):
            net.fixed_name = True
    audio, moved = _move_audio_grounds(gnd, agnd)
    print("audio isolated: %d parts, %d ground pins moved to AGND" % (len(audio), moved))




# ── the board ────────────────────────────────────────────────────────────────────────────
# ONE BOARD (user, 2026-11-13: "I want a single output board"), 120.3 x 100, DROPPED IN AND
# SLID HOME (user, 2026-11-13: "slide in down -z and then over +x"). The board stands in the
# instrument's X-Z plane, its back at y -87.5 (component face -85.9: branner moved it +1.7 so
# UNCLIPPED 3.4 mm THT tails clear the -Y wall's inner face at -91.7 by 0.8) and its parts
# facing +Y. It drops down -Z with the deck off, then slides +X 19 into a pocket fitted to it
# in the +X endplate (branner). USB INSET 1.6 (user, 2026-11-13: "keeping the USB fully on
# the PCB and then having 1.6mm of plastic, so the plug is 1.6mm inset and there is 1.6mm of
# plastic holding the PCB in place"): the board's panel edge stops against a 1.6 wall, the
# USB-C bodies end AT that edge (no overhang, mouths 1.6 behind the outer face), and the jack
# J5 sits 2.4 back on the board so its shoulder meets the inside of its own 4.0 clamp wall
# (its nut clamps it: src/board_geom.py PANEL; the board edge runs on under it in a slot).
#   +X  FINAL instrument x 0.43 = 2.03 - 1.6 wall
#   -X  final -150.4; during the drop -169.4 = 1.0 clear of the anchor screws' M4 heads
#       (src/direct_bench.py _anchor_screw_at: x -174.2, heads to -170.4, standing off the
#       -Y wall to y -84.7, into the board's band). The UI station is IGNORED for now (user,
#       2026-11-13): its clamp (to x -147) is in the drop path and moves later
#   z   -108.24 .. -8.24 (the bottom edge in a floor groove, the top under the deck)
# SEEN FROM ITS COMPONENT SIDE (+Y, looking -Y) the instrument's +X is on the LEFT, so:
#   board x = -(instrument x + 74.985), board y = instrument z + 58.24
# The PANEL is the board's -X edge: J1, J2 (power + data in), J5 (the jack); J8 (the pickup's
# screws) is on the TOP edge under the open deck; the internal leads (J3, J9 to the CM5,
# J4 the optical ribbon, J10-J12 to the brain) come off the +X end. The parts inside the
# endplate pocket: elec/output_board.pocket.json (what branner cuts the pocket from).
# The mount (an M4, branner's pick at x > -124) is ON HOLD until he places it.
BOARD_W, BOARD_L = 150.83, 100.0
XC, ZC = -74.985, -58.24
XL = BOARD_W / 2 - 35.0         # the brain-lead band: the last 35 mm (the placement intent)
# PWR_GND under the power section: the chargers at the panel end (-X), the buck and the brain
# leads along the bottom
POWER_POLY = [[-BOARD_W / 2, -50], [BOARD_W / 2, -50], [BOARD_W / 2, 0], [XL, 0], [XL, -10],
              [-20, -10], [-20, 0], [-BOARD_W / 2, 0]]
# THE ISOLATED AUDIO CORNER: the panel end's top (J5, J8 above it), AGND's own pour; GND and
# PWR_GND stop MOAT short of it all round, so the barrier is a 1 mm copper-free gap that only
# U30, U32-U34 and K1 straddle. The placement intent's "analog" region is this rectangle.
AUDIO_X1, AUDIO_Y0, MOAT = -14.0, 6.0, 1.0
AUDIO_POLY = [[-BOARD_W / 2, AUDIO_Y0], [AUDIO_X1, AUDIO_Y0], [AUDIO_X1, BOARD_L / 2],
              [-BOARD_W / 2, BOARD_L / 2]]
GND_POLY = [[-BOARD_W / 2, -BOARD_L / 2], [BOARD_W / 2, -BOARD_L / 2], [BOARD_W / 2, BOARD_L / 2],
            [AUDIO_X1 + MOAT, BOARD_L / 2], [AUDIO_X1 + MOAT, AUDIO_Y0 - MOAT],
            [-BOARD_W / 2, AUDIO_Y0 - MOAT]]
MOAT_POLY = [[-BOARD_W / 2, AUDIO_Y0 - MOAT], [AUDIO_X1 + MOAT, AUDIO_Y0 - MOAT],
             [AUDIO_X1 + MOAT, BOARD_L / 2], [AUDIO_X1, BOARD_L / 2], [AUDIO_X1, AUDIO_Y0],
             [-BOARD_W / 2, AUDIO_Y0]]
# FIRMWARE RULES the fold makes (one H743: optical SAI1-3, audio SAI4, FDCAN1/2, the motor loop)
FIRMWARE_NOTES = [
    "Interrupt handlers stay SHORT -- the SAI DMA half/complete ISRs only flag a block, the FDCAN "
    "ISR only moves frames between the message-RAM FIFOs and a queue. The DSP (lock-in, audio "
    "mix) and the lever -> motor mapping run outside interrupt context, the DSP lowest. Then no "
    "order of the two ISRs can underrun audio (DMA moves the samples without the CPU; a block "
    "is ~167 us at 32 samples / 192 kHz) or overflow CAN (FDCAN RX FIFOs hold up to 64 frames). "
    "Priority, highest first: SAI DMA, FDCAN, USB, then the deferred work (lead 2026-11-13 asked "
    "SAI DMA above CAN; with short ISRs that order costs CAN a few microseconds).",
    "DMA buffers in non-cacheable RAM (MPU) or with explicit cache maintenance: the H7's "
    "classic stale-data fault.",
    "No interrupts-off critical sections around the motor weight table: swap a pointer.",
    "Measure the lock-in loop's cycles (DWT) at bring-up; the 10-17 % CPU estimate is paper.",
]


BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "audio_poly": AUDIO_POLY,
    "outline_poly": [[-BOARD_W / 2, -50], [BOARD_W / 2, -50], [BOARD_W / 2, 50], [-BOARD_W / 2, 50]],
    "frame": {"instrument_x": "-(board x) - 74.985", "instrument_z": "board y - 58.24",
              "component_face_y": -85.9, "faces": "+Y", "by": "branner 2026-11-13",
              "install": "drop -Z at x - 19, slide +X 19 into the endplate pocket"},
    "layers": 4,
    "zones": [*([] if MERGED else [{"net": "PWR_GND", "layer": "In1.Cu", "inset": 0.3, "poly": POWER_POLY, "priority": 1}]),
              {"net": "GND", "layer": "In1.Cu", "inset": 0.3, "poly": GND_POLY},
              {"net": "GND", "layer": "B.Cu", "inset": 0.3, "poly": GND_POLY},
              {"net": "AGND", "layer": "In1.Cu", "inset": 0.3, "poly": AUDIO_POLY},
              {"net": "AGND", "layer": "B.Cu", "inset": 0.3, "poly": AUDIO_POLY}],
    "stitch_nets": ("GND", "AGND") if MERGED else ("PWR_GND", "GND", "AGND"),
    # exposed pads only before routing; the router takes the rest (cadkit 72d70a5: brain 14 -> 1 open)
    "stitch_scope": "exposed",
    "qty_per_instrument": 1,
    "panel_edge": "-X",
    # A17: twenty unnamed 1.27 mm ways -- the labeller prints a pinout block beside J4
    "silk_pinout": ["J4"],
    "edge_parts": {"-X": ["J1", "J2", "J5"], "+Y": ["J8"], "+X": ["J3", "J9"]},
    "placements": {},
    "firmware_notes": FIRMWARE_NOTES,
    # THE MOAT, sealed on every layer: no track, via or fill crosses between the audio corner
    # and the rest -- only the barrier parts' pads straddle it (cadkit A25 checks the result)
    "rule_areas": [{"poly": MOAT_POLY, "layers": "all",
                    "why": "the isolated audio corner's 1 mm moat (lead 2026-11-13)"}] if MERGED else [],
    "open_items": [
        "brain board: the 24 V boost and the power button move there (harness.BRAIN_POWER / BRAIN_SIGNAL); its VIN input soft-starts behind BRAIN_EN",
        "AP33772SDKZ-13 vs -FA02: VSEL/GPIO only on FA02; this board uses neither",
        "J4 ribbon header PZ1.27-2x10P ZZ: find its LCSC code and stock (the 2x8 is C22438123); the optical board's end mirrors this pinout",
        "J4 ribbon: 12.288 MHz BCLK + five lanes over the ribbon -- keep it short (optical top panel to this board) and series-terminate the clock at its source (SAI1 SCK pin)",
        "the +X endplate pocket (branner) is cut from elec/output_board.pocket.json: regenerate it whenever the parts within 19 mm of the panel edge move",
        "the mount: one M4 (branner) at x > -124, not yet placed -- reserve its keepout when it is",
        "A16 voltage declarations: voltage_check has output_power / output_signal seeds; merge them into one output_board entry",
        "audio isolation: B0509S-1WR3 pinout (1 -Vin 2 +Vin 3 0V 4 +Vo assumed from the Murata MEE1 family) -- read it off Mornsun's sheet; LCSC codes for B0509S-1WR3, ISO7741DBQR, ISO7740DBQR, ISO7710FDR, LP2985-50DBVR",
        "U5 as the ONE logic 5 V (merged): LMR33640 in the RNX footprint (confirm the orderable and LCSC code), an inductor with Isat >= 5 A in the 5x5 land, D14 / D16 (SS34, 3 A) feed it on a 5 V contract -- 5 A parts if full load is allowed there",
        "USB-C common-mode chokes FL1-FL4: winding pins (1-4 / 2-3 assumed) and the WE-SL5 HC part number with >= 5 A, both off the makers' sheets; LCSC codes",
        "audio isolation: the board is meant to be measured (pickup into an amp: no charger / phone charger / laptop charger / two chargers / a computer on the data) against R1",
        "the UI station's clamp (to x -147) is in this board's drop path (to x -169.4): ignored for now (user 2026-11-13), it moves -X later",
    ],
}


def _merged_quality(paths, q):
    """The merged board's declarations: the output side's, with what pointed at the brain leads
    (J10 / J12) re-aimed at the brain's own power switch and the audio rails under their new
    names, plus brain.py's own (refs +200) minus everything that now lives on the connector
    board (the motor / arm / LED headers) -- re-aimed at the ribbon header J240."""
    import re as _re
    import brain as BR
    out = []
    for x in paths:
        if any(str(t).startswith(("J10.", "J12.")) for t in x["to"]):
            continue
        x = dict(x)
        if x["net"] == "+5V" and x["from"] == "FB1.2":
            x["from"], x["net"] = "U31.5", "+5V_A"         # the isolated LDO, not the bead
        elif x["net"] == "+3V3":
            x["net"] = "+3V3_A"
        out.append(x)
    out.append({"net": "VIN_BRAIN", "from": "R112.2", "to": ["Q202.3"], "amps": 10.0})

    def rn(t):
        m = _re.match(r"^([A-Z]+)(\d+)(\..*)?$", t)
        return "%s%d%s" % (m.group(1), int(m.group(2)) + 200, m.group(3) or "") if m else t
    field = _re.compile(r"^J(1[0256]|2\d|30|3|4)\.")
    for x in BR.BOARD_NOTES["quality"]["power_paths"]:
        if field.match(str(x["from"])) or any(field.match(str(t)) for t in x["to"]):
            continue
        x = dict(x, **{"from": rn(x["from"]), "to": [rn(t) for t in x["to"]]})
        # the brain's +5V_AUX buck (U207 / L203) is gone: its loads hang on V5_PRE (U5 / L1)
        x["to"] = [t for t in x["to"] if not t.startswith("U207.")]
        if not x["to"]:
            continue
        if FOLD:
            # the CH32 (U201) and its LDO (U208) are gone: the transceivers / switches hang on
            # +3V3D from U21
            x["to"] = [t for t in x["to"] if not t.startswith(("U201.", "U208."))]
            if not x["to"]:
                continue
            if x["from"].startswith("U208."):
                x = dict(x, net="+3V3D", **{"from": "U21.2"})
        if x["net"] == "+5V_AUX":
            x = dict(x, net="V5_PRE", **{"from": "L1.2"})
        out.append(x)
    out += [
        # the ribbon (harness.CONN_RIBBON): the motors' fused 24 V on ways 1-4, the lights' on
        # 7-8, each arm's 5 V on one way
        {"net": "+24V", "from": "Q209.5", "to": ["F204.1"], "amps": 4.0},
        {"net": "+24V_RIB", "from": "F204.2", "to": ["J240.1", "J240.2", "J240.3", "J240.4"],
         "amps": 4.0, "split": True},
        {"net": "+24V_LED", "from": "F203.2", "to": ["J240.7", "J240.8"], "amps": 3.0, "split": True},
        {"net": "+5V_BUSB_PED", "from": "U206.6", "to": ["J240.19"], "amps": 0.5},
        {"net": "+5V_BUSB_LEV", "from": "U211.6", "to": ["J240.22"], "amps": 0.5},
    ]
    bq = BR.BOARD_NOTES["quality"]
    q = dict(q)
    q["not_power"] = dict(q["not_power"], **bq.get("not_power", {}))
    unc = dict(q["unconnected"])
    cm5_used = set()
    if FOLD:                           # the CM5 GPIOs the fold puts to work (SEL_PED / SEL_LEV)
        cm5_used = {str(BR.GPIO[4]), str(BR.GPIO[7])}
    for k, v in bq.get("unconnected", {}).items():
        m = _re.match(r"^([A-Z]+\d+)(\.\w+)?$", k)
        if not m or field.match(m.group(1) + "."):
            continue
        if rn(m.group(1)) == "U207" or (FOLD and rn(m.group(1)) in ("U201", "U208")):
            continue
        if m.group(1) == "J1" and isinstance(v, dict) and cm5_used:
            v = dict(v, pins=" ".join(x for x in v["pins"].split() if x not in cm5_used))
        unc[rn(m.group(1)) + (m.group(2) or "")] = v
    for k in [k for k in unc if k.startswith(("J1[02]", "J11"))]:
        del unc[k]                     # the brain leads (J10 / J12 / J11): on-board now
    # cadkit A25: the audio domain is reached from AGND only through the barrier (the DC-DC,
    # the three isolators, the relay's coil-to-contact gap) and keeps the moat on every layer.
    # No creepage figure is declared: the barrier breaks a hum loop at a few volts, it is not
    # a safety barrier (B0509S 1.5 kV test, ISO774x 5 kV, as bought, not relied on)
    q["isolation"] = {"ground": "AGND", "barrier": ["U30", "U32", "U33", "U34", "K1"],
                      "moat_mm": MOAT, "why": "the isolated audio domain (user 2026-11-13: the "
                      "hum fix, 'all three, bulletproof'); output_board._isolation"}
    # the USB-C grounds on the connector side of FL1 / FL2 (the CMCs): grounds, by another name
    q["ground_nets"] = sorted(set(q.get("ground_nets", ())) | {"PA_GND_J", "PB_GND_J"})
    unc["U33.7"] = "ISO7740 DBQ pin 7 is NC (TI SLLSEP4K Table 4-1; the ISO7741's EN1)"
    unc["U34.7"] = "ISO7710F D pin 7 is NC (TI SLLSER9E pin table)"
    q["unconnected"] = unc
    q["pinouts"] = dict(bq.get("pinouts", {}), **q["pinouts"])
    if FOLD:
        q["manual"] = dict(q.get("manual", {}), M43=(
            "ONE programmable part on this board apart from the CM5: U1, the STM32H743 (the CH32 "
            "folded into it, 2026-11-13). (a) The host is the CM5 ON THIS BOARD (J201/J202), "
            "reached over its own USB-C (gadget) or the network: its UART4 (GPIO12/13) -> R230 / "
            "R231 1k -> U1 USART1 PA10 RX / PA9 TX. (b) ST's ROM loader, AN2606 Rev 61 Table 113: "
            "STM32H74x USART1 on PA9/PA10 (the same table optical.py's M43 cites). (c) The CM5 "
            "drives GPIO19 -> R233 1k -> MCU_BOOT0 (R7 10k down at rest) and GPIO25 -> R232 1k "
            "-> NRST (R6 10k up, C54): BOOT0 high, pulse NRST, the loader answers -- no firmware "
            "of U1's and no hand on the board, so first flash, update and recovery are one path. "
            "The CM5 itself: nRPIBOOT / rpiboot over its USB-C, the Raspberry Pi way. "
            "R232/R233 are 1k so a CM5 GPIO left as an input never fights R6/R7 and an "
            "unpowered CM5 cannot be back-fed. TP1-TP6 (SWD, NRST, BOOT0) stay for dead hardware "
            "(M9). NOT YET PROVEN ON A BOARD."))
    return out, q


def quality_notes(net_path):
    """The split's two declaration sets as ONE board's: J20 is gone, so every path, waiver and
    group that crossed it is restated end to end on this board."""
    import output_split as OS
    qp, qs = OS.quality("power", net_path), OS.quality("signal", net_path)
    q = {"pinouts": dict(qp["pinouts"], **qs["pinouts"])}
    q["pinouts"]["PZ1.27-2x10P ZZ"] = (
        "HX PZ1.27 family drawing (as the brain's PZ1.27-2x8P ZZ, LCSC C22438123, p.1): a plain "
        "straight two-row header, the maker numbers nothing -- the numbering is the footprint's "
        "(KiCad PinHeader_2x10_P1.27mm_Vertical_SMD: odd pads one row, even the other, 1 / 2 at "
        "one end) and the way order is this file's J4 block, which the optical board's end "
        "mirrors (IDC ribbon: wire n = pin n)")
    for k in [k for k in q["pinouts"] if "2x12_P1.27mm" in k]:
        del q["pinouts"][k]
    unc = dict(qp["unconnected"], **qs["unconnected"])
    for k in [k for k in unc if k.startswith("J[49]") or k.startswith("J[123]") or k == "U4"]:
        del unc[k]
    unc["J[1239].[AB]8"] = "USB-C sideband (SBU): USB 2.0 does not use it"
    q["unconnected"] = unc
    q["decoupling"] = qp["decoupling"]
    q["not_power"] = dict(qp["not_power"], **qs["not_power"])
    paths = [x for x in qp["power_paths"] if not str(x.get("from", "")).startswith("J20")
             and not any(str(t).startswith("J20") for t in x["to"])]
    paths += [x for x in qs["power_paths"] if not str(x.get("from", "")).startswith("J20")
              and x["net"] != "VBUS_OPT"]
    paths += [
        # the 5 V buck's output to its three loads, on this board now (the split sent it over J20)
        {"net": "V5_PRE", "from": "L1.2", "to": ["U15.1"], "amps": 1.8},
        {"net": "V5_PRE", "from": "L1.2", "to": ["R98.1"], "amps": 0.6},
        {"net": "V5_PRE", "from": "L1.2", "to": ["U30.2"], "amps": 0.3},
        {"net": "+5V_OPT", "from": "U15.6", "to": ["J4.1", "J4.2"], "amps": 1.8, "split": True},
        {"net": "+3V3D", "from": "U21.2", "to": ["U17.10", "U16.6"], "amps": 0.005},
    ]
    # the port chokes (FL1 / FL2) sit between the connector's VBUS pins and the sense resistor
    chk = {"PA_VBUS": ("PA_VBUS_J", "FL1"), "PB_VBUS": ("PB_VBUS_J", "FL2")}
    keep = []
    for x in paths:
        if x["net"] in chk and str(x["from"]).startswith(("J1.", "J2.")):
            jn, fl = chk[x["net"]]
            keep.append(dict(x, net=jn, to=[fl + ".1"]))
        else:
            keep.append(x)
    paths = keep + [{"net": n, "from": fl + ".4", "to": [r + ".1"], "amps": 5.0}
                    for n, fl, r in (("PA_VBUS", "FL1", "R70"), ("PB_VBUS", "FL2", "R75"))]
    if MERGED:
        paths, q = _merged_quality(paths, q)
    q["power_paths"] = paths
    q["net_groups"] = [g for g in qp["net_groups"]]
    match = [m for m in qp["match"] + qs["match"] if m["name"] != "OPT"]
    if MERGED:
        import brain as BR
        match += [m for m in BR.BOARD_NOTES["match"] if m["name"] == "FLASH"]
        # the USB-C pairs' connector side, J1 / J2 -> FL3 / FL4: the same pair, a few mm long
        base = {m["name"]: m for m in match}
        for n in ("USBA", "USBB"):
            if n in base:
                match.append(dict(base[n], name=n + "_J", nets=[n + "_DP_J", n + "_DM_J"],
                                  why="%s's connector side, before its common-mode choke" % n))
    return q, match


if __name__ == "__main__":
    output_board()
    ERC()
    net_path = os.path.join(OUT_DIR, "output_board.net")
    generate_netlist(file_=net_path)
    if not MERGED:
        netcheck.grounds_meet(net_path)        # R60 joins GND and PWR_GND
    netcheck.no_orphan_pins(net_path)
    notes = dict(BOARD_NOTES)
    q, match = quality_notes(net_path)
    notes["match"], notes["quality"] = match, q
    import volts_decl                   # A16: generated by voltage_check.py --declare output_board
    volts_decl.into(notes, "output_board")
    with open(os.path.join(OUT_DIR, "output_board.board.json"), "w") as f:
        json.dump(notes, f, indent=2)
    print("output_board netlist written; %d open items" % len(BOARD_NOTES["open_items"]))
