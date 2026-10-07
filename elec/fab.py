"""Fab outputs -- gerbers, drill, BOM and CPL, one zip per board.

    py -3.12 elec/fab.py                # every board
    py -3.12 elec/fab.py lever_sensor   # just one

The machinery is cadkit's (`cadkit/pcbflow/fab_package.py`: what a package contains, every check
it runs before it will write one, and why rotation cannot be solved here are documented
there). THIS file is what is ours: which boards the instrument has, which LCSC part each
value is ordered as, the order-form settings, and the check that holds BOM.md against the
packages just built.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from cadkit.pcbflow import fab_package as _fab  # noqa: E402

# SIX boards: the power board merged into motor_ctrl, and the optical pickup landed
# (both 2026-09-15). This is now the whole instrument.
# ...plus the two FRET LIGHTING boards (2026-09-29), which are one design in
# elec/fret_led.py cut to two panels -- see that module. `foot_led` is the OTHER
# lighting job, the one that fires down at the player's feet. (The single side-mount
# `led_strip` both replaced is gone, 2026-10-01.)
BOARDS = ("can_tee", "lever_sensor", "motor_ctrl", "output_panel",
          "pi_cap", "optical", "ui_board", "fret_led_mid", "fret_led_key",
          "foot_led_a", "foot_led_b",
          # the leg's blind-mate boards (elec/leg_pogo.py, 2026-10-01): two joints, and each
          # joint's pair is the MIRROR of the other's, so four designs
          "leg_pogo_male_bottom", "leg_pogo_male_top",
          "leg_pogo_female_bottom", "leg_pogo_female_top")

# ── SOURCING ─────────────────────────────────────────────────────────────────
# ONLY codes the repo already recorded, keyed by the part VALUE as the netlist
# carries it. Nothing is inferred: an entry here means a human wrote that number
# down somewhere in elec/ or BOM.md, and a blank means the decision has not been
# made. See the module docstring on why blank beats a guess.
LCSC = {
    "S8B-XH-A": "C157914",          # 8-way side-entry XH, motor tee trunk
    "DSHP01TSGER": "C3293141",      # 1-position slide DIP switch, the tee's terminator; 21,200 stock
    "2.54-2*20P": "C5124634",       # 2x20 female header, the pi_cap's Pi socket
    "B6B-PH-K-S": "C131342",        # B6B-PH-K-S(LF)(SN) -- motor_ctrl J5, the Pi's 5 V out
    "B4B-PH-K-S": "C131334",        # B4B-PH-K-S(LF)(SN) -- motor_ctrl J4, the USB lead; 110k stock
    "S6B-PH-SM4-TB": "C265405",     # S6B-PH-SM4-TB(LF)(SN) -- pi_cap J2, the Pi's 5 V in; 5,510 stock
    "S4B-XH-A": "C157925",          # S4B-XH-A(LF)(SN), through-hole side entry -- pi_cap J6 (foot drop)
    "S8B-PH-SM4-TB": "C265121",     # 8-way side-entry PH, the 11 lever/pedal J1
    "S4B-PH-SM4-TB": "C265102",     # 4-way side-entry PH: motor_ctrl J2/J6 (bus B,
                                    # split so each half unplugs from under the
                                    # instrument). Same family as the 8-way above.
                                    # Verified 2026-09-25: 28,934 in stock.
    "SN65HVD230DR": "C12084",       # CAN transceiver: bus B on motor_ctrl, the lever boards
    "TCAN3413DR": "C22433320",      # TI, SOIC-8, +-58 V bus fault: bus A on motor_ctrl; 13,888 (2026-10-06)
    "NUP2105LT1G": "C14486",        # onsemi dual CAN-line TVS, 24 V stand-off, SOT-23; 273,420
    "LMR16006XDDCR": "C87080",      # 60 V 0.6 A buck, lever + motor controller
    "TYPE-C-31-M-12": "C165948",    # USB-C receptacle, motor controller + panel
    "CH32V203G6U6": "C5142280",     # lever board MCU
    "CH32V307WCU6": "C5142795",     # motor controller MCU
    "MT6701QT-STD": "C2913974",     # the angle sensor
    "AO3400A": "C20917",            # logic-level N-ch FET; the optical board's Q1 too
    # ── the optical board, every line checked against the manufacturer's datasheet on
    # 2026-09-17 (pinout verified pin by pin, not just the package) ──────────────────
    "STM32H743IIT6": "C89597",      # LQFP176; pins re-derived from ST's CubeMX symbol
    "USB3300-EZK-TR": "C108383",    # ULPI PHY, QFN-32 5x5; 17,431 in stock 2026-10-05
    "USBLC6-2SC6": "C7519",         # ESD array, SOT23-6L: 1 IO1 2 GND 3 IO2 4 IO2 5 VBUS 6 IO1
    "TLV9062IDGKR": "C398356",      # dual TIA, VSSOP-8 -- same die as the TLV9064 it
                                    # replaced (TI SBOS839); 34k stock vs the quad's 107
    "TLV9061IDBVR": "C398358",      # mid-rail buffer -- DBV, NOT the DCK part once ordered
    "AP2114H-3.3TRG1": "C150716",   # 3V3 digital LDO, ceramic-stable: 1 GND 2 VOUT/tab 3 VIN;
                                    # 11,540 in stock 2026-10-04 (optical U8)
    "TPS7A2033PDBVR": "C2862740",   # 3V3 analog LDO, ceramic-stable: 1 IN 2 GND 3 EN 4 N/C 5 OUT;
                                    # 203,032 in stock 2026-10-04 (optical U9)
    "LTE-C9901": "C2683614",        # 940 nm emitter, 0603, Lite-On DS50-2017-0074:
                                    # 8 mW/sr typ @20 mA, 65 deg FULL, 0.98 tall, 60 mA DC
    "PD15-22B/TR8": "C161211",      # Everlight PIN photodiode, 940 nm peak, 11k stock (2026-09-21)
    "TLV320ADC3140IRTWT": "C1852021",  # TI 4-ch audio ADC, WQFN-24 RTW, 306 stock (2026-09-21)
    "S4B-XH-SM4-TB": "C161861",     # the (LF)(SN) form, 20,992; the bare listing is 0
    # Crystals are specified by PART, not by frequency -- see the note beside Y1.
    # Inductors are specified by PART too -- see the note beside L1. Isat 1.35 A
    # worst case against the TPS560430's 1.4 A maximum current limit, which is the
    # number TI tells you to size against.
    "WPN4020H4R7MT": "C98363",       # 4.7 uH, 4x4x2.0 closed-circuit, Isat 4.0 A (optical L1)
    "SWPA5040S4R7MT": "C48496",      # 4.7 uH, 5x5x4.0 shielded, Isat 3.50 A min (the LED bucks)
    "LMR33630BRNXR": "C2071384",     # the 1.4 MHz RNX part (the LED bucks, elec/buck_cell.py; optical U13)
    # -- motor_ctrl's parts that were values and not parts until the 2026-10-04 review --
    "PNR3015-150M": "C19634062",     # APV 15 uH 3015, Isat 1.4 A guaranteed; 906 (LMR16006 L1).
                                     # Fits: ANR3015T470M C7427088 (0.43 A, 14.9k)
    "VLS6045EX-6R8M": "C415364",     # TDK 6.8 uH 6045, Isat 4.7 A, 36 mOhm; 4,123 (5 V buck
                                     # L2). Nearest: Sunlord SWPA6045S6R8MT C57254 (4.3 A)
    "JFC1206-1100FS": "C136343",     # JDT 1206 fuse 1 A 63 V; 96,232
    "JFC1206-1200FS": "C136345",     # JDT 1206 fuse 2 A 63 V; 11,363 on 2026-10-05 (foot_led_a F1)
    "JFC1206-1300FS": "C136347",     # JDT 1206 fuse 3 A 63 V; 37,944
    "JFC1206-1400FS": "C136349",     # JDT 1206 fuse 4 A 63 V; 45,541
    "B5819W": "C8598",               # CJ B5819W SL, SOD-123 1 A 40 V Schottky, JLC basic
    "SMAJ24A": "C148222",            # Littelfuse, SMA, unidirectional: 26.7-29.5 V, 38.9 V at 10.3 A; 19,311
    "SMBJ5.0A": "C83333",            # Littelfuse, SMB, unidirectional; 26,310
    "LESD5L5.0CT1G": "C5274293",     # LRC 0.5 pF bidirectional 5 V clamp, SOD-523; 12,023
    "TAXM12M4RFBCCT2T": "C133337",   # Yajingxin 12 MHz 3225, CL 12 pF, ESR 80 ohm max
    "TS5A3159DCKR": "C46388",        # SPDT analog switch, VIH 2.4 V at 5 V
    "RK73B3ATTE2R0J": "C5139521",    # 2 ohm 2512, KOA: optical R44, the 24 V input damper,
                                     # chosen for its one-pulse curve; 3,354 in stock 2026-10-05
    "BLM18KG601SN1D": "C85833",      # 0603 bead, 600R@100MHz, 1.3 A, DCR 150 mohm
    "1N4148WT": "C917006",           # SOD-523 switching diode, 75 V 150 mA
    "TAXM8M4RFDCET2T": "C403948",    # Yajingxin 8 MHz 3225, CL 12 pF, ESR 250 ohm max;
                                     # 75,154 in stock 2026-10-04 (motor_ctrl HSE)
    "TAXM25M4RDBCCT2T": "C403946",   # Yajingxin 25 MHz 3225, CL 10 pF, ESR 30 ohm max;
                                     # 7,232 in stock 2026-10-04 (optical MCU HSE)
    "CJO05-240003320B30": "C712738",   # JSCJ 24 MHz 3.3 V CMOS oscillator, 3225; PHY reference
    # ── sourced 2026-09-17 from JLCPCB's own parts API, not from memory ──────────
    # Each line names the listing's exact model and the stock it showed, because a code
    # with no source is the thing this file exists to refuse. Picked by EXACT model and
    # genuine manufacturer; where a listing was the bare MPN at 0 stock and its (LF)(SN)
    # tin-plated form was stocked, the stocked form is the same part as ordered from JST.
    "B4B-XH-A": "C144395",          # JST B4B-XH-A(LF)(SN), stock 60,424
    "TLC5971RGER": "C543004",       # 12-ch 16-bit constant-current LED driver, VQFN-24 (fret_led, foot_led)
    "XL-5050RGBW": "C7371891",      # XINGLIGHT RGBW 5050, separate anodes/cathodes (fret_led, foot_led)
    "S6B-PH-SM4-TB": "C265405",     # 6-way side-entry PH, the LED strip's chain connector
                                    # and pi_cap J3, 5 V + SPI out to the strip
    "S4B-XH-SM4-TB": "C161861",     # S4B-XH-SM4-TB(LF)(SN), 20,777 -- pi_cap J2/J4,
                                    # side entry so they fit UNDER the cap (see there)
    # the leg blind-mate (elec/leg_pogo.py), read off JLCPCB's parts API 2026-10-01:
    "YZ165615055F-04025-02": "C54799748",   # right-angle 1x4 spring-pin header, stock 1,467
                                            # (its -01 sibling C5296819, 902, is the same drawing)
    "YZ185115035T-04025-01": "C54930022",   # vertical 1x4 gold target, stock 210 -- THIN
    "S4B-ZR-SM4A-TF": "C485354",            # JST S4B-ZR-SM4A-TF(LF)(SN), stock 26,844
    "YZF0002-38080-02": "C5203987", # side-mount SMD pogo, 24 V / 12 A: the fret seam, x6 a side
    "B2B-XH-A": "C158012",          # JST B2B-XH-A(LF)(SN), stock 381,008 -- sourced
                                    # 2026-09-19 by asking the catalogue, and it is the
                                    # (LF)(SN) trap again and not a preference: the BARE
                                    # "B2B-XH-A" listing is C19272845 with ONE piece in
                                    # stock. Same shape as S4B-XH-SM4-TB and B4B-XH-A.
    "S4B-XH-A": "C157925",          # JST S4B-XH-A(LF)(SN), stock 88,547
    "LMR33630ADDAR": "C841384",     # TI, ESOP-8 (= HSOIC-8 PowerPAD), stock 6,730
    "KPJX-4S-S": "C2875467",        # Kycon KPJX-4S-S, 4-pin power jack; stock 44 on
                                    # 2026-10-01 -- THIN: check before a build of 10
    "MX126-5.0-02P": "C5188434",    # MAX MX126-5.0-02P-GN01-Cu-S-A, stock 48,416
    # The two CLASS lines whose pinout the netlist actually writes out, so a part can be
    # checked against it pin for pin rather than chosen by name:
    "NMJ6HCD2": "C368502",          # Neutrik 1/4 in TRS jack, THT. 1350 in stock 2026-10-02
                                    # (it was at ZERO on 2026-09-17 and sat in OPEN_VALUES)
    "SQD50P06-15L": "C3281500",     # Vishay SQD50P06-15L_GE3, P-ch 60 V 15.5 mOhm TO-252;
                                    # 6,668 in stock 2026-10-04 -- the output panel's power
                                    # switch. Same pinout: NCE60P50K (28 mOhm), AOD409 (40)
    "2N7002": "C8545",              # CJ 2N7002 SOT-23, JLC basic part, 1.6 M in stock
    "BZT52C10T-7": "C248313",       # Diodes Inc 10 V zener, SOD-523; 3,376 in stock
                                    # 2026-10-04. Alternates in the footprint: BZX584C10,
                                    # MM5Z10VT1G
    "B6B-XH-A": "C144397",          # JST B6B-XH-A(LF)(SN), 38,933 in stock 2026-10-04 --
                                    # the motor board / output panel power + switch cable
    "TPS2553DBVR": "C55266",        # TI current-limited switch, SOT-23-6 (motor_ctrl U6, pi_cap U1); 58,077 in stock
                                    # 2026-10-04 -- motor_ctrl U6, bus B's 5 V
    "PZ1.27-2x8P": "C22438114",     # the same family's 2x8, for the UI board's 16-way
                                    # ribbon; 2050 in stock 2026-10-04
    "PB-22E85-S-5.7C-C-W": "C22462024",   # Legion self-locking push switch, 2P2T, THT,
                                    # 12 V 0.3 A; 2535 in stock 2026-10-04. The power button.
    "MCP4261-103E/ST": "C185580",   # dual 10k digital pot, TSSOP-14 -- ⚠ 96 in stock on
                                    # 2026-10-01; re-check before ordering
    "TLV9061IDBVR": "C398358",      # TI, SOT-23-5: 1 OUT 2 V- 3 IN+ 4 IN- 5 V+ -- exact
                                    # match to U7/U8. Stock 301,906. Same family as the
                                    # optical board's TIAs. RRIO, 5.5 V max on a 5 V rail.
    "AP2112K-3.3TRG1": "C51118",    # Diodes Inc, SOT-23-5: 1 IN 2 GND 3 EN 4 NC 5 OUT --
                                    # exact match to U6. 600 mA against a 300 mA class.
                                    # Stock 55,831.
    # ── the output board's analog rewrite, 2026-09-21: every one of these is wired pin by
    # pin from the maker's own table (see output_panel.py), which is what the three
    # placeholder OPENs below were waiting for ─────────────────────────────────────────
    "PCM1808PWR": "C55513",         # TI ADC, TSSOP-14 (SLES177B Pin Functions)
    "PCM5102APWR": "C107671",       # TI DAC, TSSOP-20 (SLAS859C Pin Functions, Figure 33)
    "CH334F": "C5187527",           # WCH HS hub, QFN-24 4x4 (DS V2.5 Table 1-3, "4F")
    "G6K-2F-Y-DC5": "C326376",      # Omron DPDT, 5 V coil (terminal arrangement p.6), ~2.5k
    "ESD5B5.0ST1G": "C93623",       # onsemi bidirectional 5 V TVS, SOD-523, ~166k
    # -- the UI board, 2026-09-25, every line read off the LCSC listing itself ------
    "RKJXT1F42001": "C160841",      # Alps 4-way stick + encoder + push, 7,354 in stock.
                                    # DigiKey's listing for the same part is 0 in stock
                                    # at $9.22 and describes it as "non-continuous",
                                    # which is wrong -- see the note in BOM.md.
    "KH-2.54PH180-1X20P-L11.5": "C2905493",   # 1x20 male, insulation 2.5 / mating pin
                                    # 6.0 / tail 3.0, all three read from the listing
                                    # because src/ui_panel.py's Z stack is built on
                                    # them. 1,131 in stock.
}
# ── EVERY PASSIVE, BY (VALUE, FOOTPRINT) ──────────────────────────────────────────────
# These rows used to go to the fab with no part number -- "a generic passive, chosen at
# order time". On 2026-10-06 a dry run of a real order showed who does the choosing:
# JLCPCB's matcher read `C_0402_1005Metric` as 01005 and put a 01005 6.3 V capacitor on the
# 100 nF row and a 01005 resistor on the 10 k row. Economic assembly does not place 01005,
# so both came up unselected at quantity 0 and the order would have built the board without
# them. So each row names its part, and cadkit's builder refuses a package with a blank.
#
# KEYED ON THE PAIR because the value alone is not a part: "100nF" is an 0402 on six boards
# and an 0805 on the optical board; "4.7uF/50V" is an 0805 on the lighting boards and a
# 1206 on the motor board. Two spellings of one part ("100nF", "100nF/50V") are two keys
# to one code: the higher rating covers the bare value, and every bare-value capacitor was
# checked to sit on 5 V or less (2026-10-06, from the netlists).
#
# Every code was read on JLCPCB's parts catalogue on 2026-10-06: package, value, voltage,
# dielectric, tolerance. `elec/lcsc_check.py` re-reads them all and compares. Basic parts
# wherever one exists (no extended-part fee, placed by Economic assembly).
PASSIVES = {
    ("100nF", "C_0402_1005Metric"):          "C307331",   # Samsung CL05B104KB54PNC, 50 V X7R 10 %; basic
    ("100nF/16V", "C_0402_1005Metric"):      "C307331",
    ("100nF/50V", "C_0402_1005Metric"):      "C307331",
    ("10nF C0G", "C_0402_1005Metric"):       "C22400107",   # Murata GRM1555C1H103JE01D, 50 V C0G 5 %; 66,861 in stock
    ("10uF", "C_0402_1005Metric"):           "C15525",   # Samsung CL05A106MQ5NUNC, 6.3 V X5R 20 %; basic. Every one sits on 3.3 V or a 1.8 V regulator pin
    ("12pF", "C_0402_1005Metric"):           "C1547",   # FH 0402CG120J500NT, 50 V C0G 5 %; basic
    ("15pF", "C_0402_1005Metric"):           "C1548",   # FH 0402CG150J500NT, 50 V C0G 5 %; basic
    ("1uF", "C_0402_1005Metric"):            "C52923",   # Samsung CL05A105KA5NQNC, 25 V X5R 10 %; basic
    ("1uF/16V", "C_0402_1005Metric"):        "C52923",
    ("1uF/25V", "C_0402_1005Metric"):        "C52923",
    ("2.2nF C0G", "C_0402_1005Metric"):      "C2987940",   # Murata GRM1555C1H222GA01D, 50 V C0G 2 %; 103,502 in stock
    ("2.2pF", "C_0402_1005Metric"):          "C325452",   # Yageo CC0402BRNPO9BN2R2, 50 V NP0 +-0.1 pF: the TIA's Cf, tighter than the +-10 % its stability sum assumes
    ("22nF/50V", "C_0402_1005Metric"):       "C1532",   # FH 0402B223K500NT, 50 V X7R 10 %; basic
    ("4.7uF", "C_0402_1005Metric"):          "C23733",   # Samsung CL05A475MP5NRNC, 10 V X5R 20 %; basic. On 3.3 V
    ("10uF", "C_0805_2012Metric"):           "C15850",   # Samsung CL21A106KAYNNNE, 25 V X5R 10 %; basic
    ("10uF/16V", "C_0805_2012Metric"):       "C15850",
    ("10uF/25V", "C_0805_2012Metric"):       "C15850",
    ("1uF", "C_0805_2012Metric"):            "C28323",   # Samsung CL21B105KBFNNNE, 50 V X7R 10 %; basic
    ("2.2uF", "C_0805_2012Metric"):          "C377773",   # Samsung CL21A225KBQNNNE, 50 V X5R 10 %; basic
    ("22uF/16V", "C_0805_2012Metric"):       "C45783",   # Samsung CL21A226MAQNNNE, 25 V X5R 20 %; basic (25 V where 16 is asked)
    ("4.7uF", "C_0805_2012Metric"):          "C1779",   # Samsung CL21A475KAQNNNE, 25 V X5R 10 %; basic
    ("4.7uF/25V", "C_0805_2012Metric"):      "C1779",
    ("4.7uF/50V", "C_0805_2012Metric"):      "C98192",   # Samsung CL21A475KBQNNNE, 50 V X5R 10 %; extended, 340,236 in stock
    ("100nF C0G", "C_1206_3216Metric"):      "C170182",   # FH 1206N104J500CT, 50 V NP0 5 %; 175,852 in stock
    ("10uF/50V", "C_1206_3216Metric"):       "C13585",   # Samsung CL31A106KBHNNNE, 50 V X5R 10 %; basic
    ("22uF/25V", "C_1206_3216Metric"):       "C12891",   # Samsung CL31A226KAHNNNE, 25 V X5R 10 %; basic
    ("4.7uF/50V", "C_1206_3216Metric"):      "C29823",   # FH 1206B475K500NT, 50 V X7R 10 %; basic
    ("2.2uF/100V", "C_1210_3225Metric"):     "C92775",   # Taiyo Yuden HMK325B7225KN-T, 100 V X7R 10 %; 81,275 in stock
    ("220nF/50V", "C_0603_1608Metric"):      "C64705",   # Samsung CL10B224KB8NNNC, 50 V X7R 10 %; 365,491 in stock
    ("0R", "R_0402_1005Metric"):             "C17168",   # UniOhm 0402WGF0000TCE; basic
    ("100R", "R_0402_1005Metric"):           "C25076",   # UniOhm 0402WGF1000TCE, 1 %; basic
    ("100k", "R_0402_1005Metric"):           "C25741",   # UniOhm 0402WGF1003TCE, 1 %; basic
    ("100k 1%", "R_0402_1005Metric"):        "C25741",
    ("10k", "R_0402_1005Metric"):            "C25744",   # UniOhm 0402WGF1002TCE, 1 %; basic
    ("10k 1%", "R_0402_1005Metric"):         "C25744",
    ("10k 0.1%", "R_0402_1005Metric"):       "C190095",   # Yageo RT0402BRD0710KL, thin film 0.1 % 25 ppm; 729,784 in stock
    ("12k 1%", "R_0402_1005Metric"):         "C25752",   # UniOhm 0402WGF1202TCE, 1 %; basic
    ("137k 1%", "R_0402_1005Metric"):        "C138058",   # Yageo RC0402FR-07137KL, 1 %; 27,854 in stock
    ("150k", "R_0402_1005Metric"):           "C25755",   # UniOhm 0402WGF1503TCE, 1 %; preferred extended
    ("0R22", "R_1206_3216Metric"):           "C25336",   # UniOhm 1206W4F220LT5E, 1 %, 250 mW, 200 V; 39,275 in stock (2026-10-06)
    ("120R 100mW", "R_0402_1005Metric"):     "C413065",   # Panasonic ERJ2RKF1200X, 1 %, 100 mW; 43,451 in stock (2026-10-06)
    ("180R 100mW", "R_0402_1005Metric"):     "C413069",   # Panasonic ERJ2RKF1800X, 1 %, 100 mW (the UniOhm / Yageo 0402 is 62.5); 29,615 in stock
    ("18k2 1%", "R_0402_1005Metric"):        "C2076827",   # Panasonic ERJ2RKF1822X, 1 %; 37,043 in stock
    ("1M", "R_0402_1005Metric"):             "C26083",   # UniOhm 0402WGF1004TCE, 1 %; basic
    ("1R", "R_0402_1005Metric"):             "C25086",   # UniOhm 0402WGF100KTCE, 1 %; preferred extended
    ("1k 1%", "R_0402_1005Metric"):          "C11702",   # UniOhm 0402WGF1001TCE, 1 %; basic
    ("200k 1%", "R_0402_1005Metric"):        "C25764",   # UniOhm 0402WGF2003TCE, 1 %; basic
    ("220R", "R_0402_1005Metric"):           "C25091",   # UniOhm 0402WGF2200TCE, 1 %; basic
    ("24k9 1%", "R_0402_1005Metric"):        "C138027",   # Yageo RC0402FR-0724K9L, 1 %; 356,026 in stock
    ("249k 1%", "R_0402_1005Metric"):        "C2076822",   # Panasonic ERJ2RKF2493X, 1 %; 30,031 in stock
    ("2R2", "R_0402_1005Metric"):            "C327251",   # Yageo RC0402FR-072R2L, 1 %; 758,197 in stock
    ("30k1", "R_0402_1005Metric"):           "C2076806",   # Panasonic ERJ2RKF3012X, 1 %; 29,132 in stock
    ("330k", "R_0402_1005Metric"):           "C25778",   # UniOhm 0402WGF3303TCE, 1 %; preferred extended
    ("3k3", "R_0402_1005Metric"):            "C25890",   # UniOhm 0402WGF3301TCE, 1 %; basic
    ("470R", "R_0402_1005Metric"):           "C25117",   # UniOhm 0402WGF4700TCE, 1 %; basic
    ("49k9 1%", "R_0402_1005Metric"):        "C25897",   # UniOhm 0402WGF4992TCE, 1 %; preferred extended, 31,254 in stock
    ("4k7", "R_0402_1005Metric"):            "C25900",   # UniOhm 0402WGF4701TCE, 1 %; basic
    ("56k", "R_0402_1005Metric"):            "C25796",   # UniOhm 0402WGF5602TCE, 1 %; preferred extended
    ("5k1", "R_0402_1005Metric"):            "C25905",   # UniOhm 0402WGF5101TCE, 1 %; basic
    ("68R", "R_0402_1005Metric"):            "C163455",   # Yageo RC0402FR-0768RL, 1 %; 396,451 in stock
    ("7k68 1%", "R_0402_1005Metric"):        "C25919",   # UniOhm 0402WGF7681TCE, 1 %; 106,451 in stock
    ("9k09 1%", "R_0402_1005Metric"):        "C274897",   # Yageo RC0402FR-079K09L, 1 %; 47,319 in stock
    ("0R", "R_0603_1608Metric"):             "C21189",   # UniOhm 0603WAF0000T5E; basic
    ("120R", "R_0603_1608Metric"):           "C22787",   # UniOhm 0603WAF1200T5E, 1 %, 100 mW; basic
}

# ⚠ EVERY VALUE STRING MUST BE ACCOUNTED FOR -- IN LCSC, GENERIC, OR HERE.
# branner's catch, and it is the right shape for the bug that happened: usb_panel's
# J2 kept its OLD part number in `value` after its footprint moved to a different
# connector, and the BOM reads `value`. NOTHING ELSE IN THE PIPELINE DOES -- not
# the netlist, not the layout, not DRC -- so a stale part number is invisible
# right up until a box of nine-contact USB 3.0 shells arrives for a four-pad
# footprint. Only running fab.py caught it, and only because I happened to read
# the output.
#
# Reporting unknowns was not enough: a changed value simply joined the OPEN pile
# and looked like every other undecided part. So unknowns are now DECLARED. A
# value that is neither sourced nor generic nor listed below FAILS THE BUILD,
# which means changing a part number forces you to come here and say so.
OPEN_VALUES = frozenset({
    # (The placeholders that stood here -- "FRT5-class 5V", "PCM5102A-class", "CH334-class HS
    #  hub" -- and PCM1808PWR's hold are gone with the 2026-09-21 rewrite: real parts, real
    #  pinouts, sourced above. What still wants a second pair of eyes is the ANALOG DESIGN
    #  -- bias, coupling, the pickup's 1M load -- not a part number.)
})

# ORDER-FORM CHOICES THAT APPLY TO EVERY BOARD (2026-10-02 review). None is in a gerber.
ORDER_EVERY_BOARD = (
    ("mark", "Remove Mark (the fab's order number). Left on, it is printed wherever the "
             "fab finds room -- on the optical board that can be beside the sensors."),
    ("rails", "Edge rails and fiducials: Added by JLCPCB. No board carries its own "
              "fiducials, and the small ones are assembled in a panel the fab makes."),
    ("placement", "Confirm Parts Placement: Yes. An engineer checks polarity and rotation "
                  "before the run; ROTATION-CHECK.txt is the list to compare against."),
    ("prod file", "Confirm Production File: Yes. The last look at the panel before it is cut."),
    ("carry-over", "THE FORM REMEMBERS THE PREVIOUS BOARD'S OPTIONS. After a board ordered "
                   "with 0.25 mm vias the next one opens with 0.25 mm vias, Tg155 and the "
                   "4-wire Kelvin test still selected (Advanced Options), about 40 USD it "
                   "does not need. Unless this file says otherwise above, set: via "
                   "0.3 mm / (0.4/0.45 mm), FR4 TG135, Kelvin test No. Check the build time "
                   "too: it can jump to the paid 2-3 day option."),
    ("upload", "Upload THIS package's -bom.csv and -cpl.csv as they are: every row has "
               "its part number, and each placement that could be measured is "
               "already in the fab's footprint frame. ROTATION-CHECK.txt lists the ones "
               "that were corrected and the ones still to check in the preview."),
    ("tier", "PCBA Type should read Economic. Two boards are Standard and the page "
             "says so itself: optical (a "
             "black solder mask) and output_panel (the relay is 'Standard only': the "
             "page offers 'Switch to Standard PCBA', take it). Standard is a 25 USD "
             "setup, a stencil charge and a loading fee per part type. On any other "
             "board Standard is left over from the previous one: set it back."),
    ("align", "Entering the placement preview the page may ask 'component may be offset "
              "from the PCB, automatically align it?' -- Cancel. The placement file is "
              "already in the fab's frames."),
)

# WHAT THE ORDER PAGE NEEDS DONE BY HAND FOR ONE PART (written into ORDER.txt of each
# board that carries it).
PART_NOTES = {
    "C326376": "the relay is 'Standard only': under Economic it arrives unticked and Next "
               "offers 'Switch to Standard PCBA' or 'Do not place this part'. Switch.",
    "C5139521": "the fab has no footprint or model for it yet: the preview shows a "
                "placeholder and the build takes one more day.",
    "C54799748": "the fab has no footprint or model for it yet: the preview shows a "
                 "placeholder and the build takes one more day.",
    "C2875467": "the 24 V inlet jack stands on flat tabs in plated SLOTS: six of 0.6 x 2.7 mm "
                "and one of 2.2 x 1.0 mm in the drill file, the sizes on Kycon's drawing. If "
                "the fab's engineer proposes round holes or a narrower slot, decline: the "
                "tabs do not enter anything smaller.",
    "C161211": "polarity, to look at in the placement preview and again on the finished "
               "board: each photodiode's STRIPED end (its cathode; Everlight's lands 1 and 4) "
               "lies on the silk bar, which is the end toward its op-amp. Twenty of them, "
               "every one the same way round relative to its own op-amp.",
    "C5203987": "the seam pogo pin arrives UNSELECTED (a 'difficult' part, about 0.08 USD "
                "each extra). Tick its row -- it can take two clicks -- or Next stops "
                "with 'Project has unselected parts'.",
}


def _check_bom_md(names):
    """Hold BOM.md against the packages just built, and say so here.

    ⚠ A CHECK NOTHING CALLS IS A CHECK THAT DOES NOT RUN. verify.py sat unrun for
    weeks behind a docstring insisting it existed to remove the human, because no step
    invoked it. bom_check.py and part_totals.py were written today and were in exactly
    that position. This is the step that turns boards into something orderable and
    BOM.md is what a person orders from, so this is where the two belong.

    ⚠ IT REPORTS, IT DOES NOT REFUSE, and the line is drawn at the artefact. A wrong
    part number in BOM.md does not corrupt the fab package -- JLC assembles from the CPL
    and BOM inside the zip, which are generated. Refusing to build the package over a
    documentation error would block the thing that is correct because the thing beside it
    is not. It fails where it actually bites: somebody hand-ordering, or reading the file
    to understand what the instrument is made of.

    Only runs on a FULL build. Against a partial one it would report parts as unnamed
    that are simply not in this run's packages.
    """
    if set(names) != set(BOARDS):
        return
    # The other direction (2026-10-06): does anything still name a part NO board carries?
    # bom_audit.py, which also holds docs/order-parts.md against the netlists.
    try:
        import bom_audit
        print()
        bom_audit.main([])
    except Exception as exc:
        print("  !! bom_audit did not run: %r" % (exc,))
    try:
        import bom_check
        import part_totals
        bad = bom_check.check()[0]
        per = part_totals.totals()[0]
        bom_txt = open(os.path.join(os.path.dirname(HERE), "BOM.md"),
                       encoding="utf-8").read()
        unlisted = [v for v in per if v in LCSC and v not in bom_txt]
    except Exception as exc:                # a check that breaks must not break the run
        print()
        print("  !! BOM.md checks did not run: %r" % (exc,))
        return
    if not bad and not unlisted:
        print()
        print("BOM.md agrees with the packages: every designator row names the part its "
              "board places,")
        print("  and every sourced part is named.")
        return
    print()
    print("!! BOM.md DISAGREES WITH THE BOARDS -- the packages are fine, the document "
          "is not:")
    for board, des, part, code, val, line in bad:
        print("   BOM.md:%-5d %-6s says %-20s %-10s but %s places %s"
              % (line, des, part, code, board, val))
    for val in sorted(unlisted):
        print("   %-20s is placed and SOURCED (%s) but named nowhere in BOM.md"
              % (val, LCSC[val]))


_fab.configure(HERE, BOARDS, {**LCSC, **PASSIVES}, OPEN_VALUES, ORDER_EVERY_BOARD,
               after=_check_bom_md, part_notes=PART_NOTES)
fab = _fab.fab
main = _fab.main

if __name__ == "__main__":
    _args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--frames" in sys.argv:          # measure the fab's footprint frames (network)
        _fab.frames(_args or list(BOARDS), refresh="--refresh" in sys.argv)
    else:
        main(_args or list(BOARDS))
