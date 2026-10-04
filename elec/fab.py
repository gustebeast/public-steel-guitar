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
          "foot_led",
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
    "2.54-2*20P": "C5124634",       # 2x20 female header, the pi_cap's Pi socket
    "B6B-PH-K-S": "C131342",        # B6B-PH-K-S(LF)(SN) -- pi_cap J3, 5 V + SPI to the strip
    "S8B-PH-SM4-TB": "C265121",     # 8-way side-entry PH, the 11 lever/pedal J1
    "S4B-PH-SM4-TB": "C265102",     # 4-way side-entry PH, motor_ctrl J2/J6 (bus B,
                                    # split so each half unplugs from under the
                                    # instrument). Same family as the 8-way above.
                                    # Verified 2026-09-25: 28,934 in stock.
    "B8B-PH-K-S": "C157974",        # B8B-PH-K-S(LF)(SN), stock 21,709 -- motor_ctrl J2,
                                    # the same bus-B trunk on the vertical variant
    "PJ-320D-4A": "C95562",         # TRRS 4-pole socket
    "SN65HVD230DR": "C12084",       # CAN transceiver, both boards
    "LMR16006XDDCR": "C87080",      # 60 V 0.6 A buck, lever + motor controller
    "TYPE-C-31-M-12": "C165948",    # USB-C receptacle, motor controller + panel
    "CH32V203G6U6": "C5142280",     # lever board MCU
    "CH32V307WCU6": "C5142795",     # motor controller MCU
    "MT6701QT-STD": "C2913974",     # the angle sensor
    "AO3400A": "C20917",            # logic-level N-ch FET; the optical board's Q1 too
    # ── the optical board, every line checked against the manufacturer's datasheet on
    # 2026-09-17 (pinout verified pin by pin, not just the package) ──────────────────
    "STM32H743IIT6": "C89597",      # LQFP176; pins re-derived from ST's CubeMX symbol
    "USB3343-CP": "C633347",        # ULPI PHY; pinout was INVENTED before this check
    "USBLC6-2SC6": "C7519",         # ESD array, SOT23-6L: 1 IO1 2 GND 3 IO2 4 IO2 5 VBUS 6 IO1
    "TLV9062IDGKR": "C398356",      # dual TIA, VSSOP-8 -- same die as the TLV9064 it
                                    # replaced (TI SBOS839); 34k stock vs the quad's 107
    "TLV9061IDBVR": "C398358",      # mid-rail buffer -- DBV, NOT the DCK part once ordered
    "AMS1117-3.3": "C6186",         # 3V3 digital LDO: 1 GND 2 VOUT/tab 3 VIN
    "SPX3819M5-L-3-3/TR": "C9055",  # 3V3 analog LDO: 1 IN 2 GND 3 EN 4 BYP 5 OUT
    "LMR33630CRNXR": "C2071783",    # 24->5 V sync buck, 2.1 MHz, 3 A, VQFN-HR RNX (optical U13)
    "LTE-C9901": "C2683614",        # 940 nm emitter, 0603, Lite-On DS50-2017-0074:
                                    # 8 mW/sr typ @20 mA, 65 deg FULL, 0.98 tall, 60 mA DC
    "PD15-22B/TR8": "C161211",      # Everlight PIN photodiode, 940 nm peak, 11k stock (2026-09-21)
    "TLV320ADC3140IRTWT": "C1852021",  # TI 4-ch audio ADC, WQFN-24 RTW, 306 stock (2026-09-21)
    "S4B-XH-SM4-TB": "C161861",     # the (LF)(SN) form, 20,992; the bare listing is 0
    # Crystals are specified by PART, not by frequency -- see the note beside Y1.
    # Inductors are specified by PART too -- see the note beside L1. Isat 1.35 A
    # worst case against the TPS560430's 1.4 A maximum current limit, which is the
    # number TI tells you to size against.
    "SWPA4030S4R7MT": "C57269",      # 4.7 uH, 4x4x3.0 shielded, Isat 3.2 A (optical L1)
    # ⚠ "600" IS 60 OHM in Murata/Sunlord bead numbering. 601 is the 600 ohm part.
    "GZ1608D601TF": "C1002",         # 0603 bead, 600R@100MHz, 200 mA, DCR 450 mohm
    "TX322525M4LBDD2T": "C5308007",  # 25 MHz, CL 20 pF, ESR 30 ohm (MCU HSE)
    "K3A260002010": "C2835957",      # 26 MHz, CL 20 pF, ESR 30 ohm (the PHY's limits)
    # ── sourced 2026-09-17 from JLCPCB's own parts API, not from memory ──────────
    # Each line names the listing's exact model and the stock it showed, because a code
    # with no source is the thing this file exists to refuse. Picked by EXACT model and
    # genuine manufacturer; where a listing was the bare MPN at 0 stock and its (LF)(SN)
    # tin-plated form was stocked, the stocked form is the same part as ordered from JST.
    "B4B-XH-A": "C144395",          # JST B4B-XH-A(LF)(SN), stock 60,424
    "TLC59711PWPR": "C116842",      # 12-ch 16-bit constant-current LED driver (fret_led, foot_led)
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
    # ⚠ THE FOOT STRIP'S, AND IT IS THERE FOR ITS HEIGHT. Everything on that board hangs
    # into a 3.40 mm trough; the PH above is 5.50 tall and does not fit. JST's own
    # drawing puts the side-entry SH at 2.95. 1.0 A / 50 V against 0.24 A at 24 V.
    "SM04B-SRSS-TB": "C160404",     # JST SM04B-SRSS-TB(LF)(SN), 4-way side-entry SH,
                                    # 3,495 in stock 2026-09-30
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
    "PZ1.27-2x7P": "C22438113",     # HX PZ1.27-2x7P WZ: 1.27 mm 2x7 RIGHT-ANGLE pin header,
                                    # THT, 2902 in stock 2026-10-02 -- the pi_cap's UI ribbon.
                                    # (C22438122, named in pi_cap.py, is the VERTICAL one and
                                    # does not match the Horizontal footprint.)
    "PZ1.27-2x8P": "C22438114",     # the same family's 2x8, for the UI board's 16-way
                                    # ribbon; 2050 in stock 2026-10-04
    "PB-22E85-S-5.7C-C-W": "C22462024",   # Legion self-locking push switch, 2P2T, THT,
                                    # 12 V 0.3 A; 2535 in stock 2026-10-04. The power button.
    "MCP4261-103E/ST": "C185580",   # dual 10k digital pot, TSSOP-14 -- ⚠ 96 in stock on
                                    # 2026-10-01; re-check before ordering
    "SN74LVC1G3157DCKR": "C38663",  # SPDT analog switch, SC-70-6
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
    # 154 IN STOCK, AND IT IS THE THINNEST LINE ON THIS BOARD. The right-angle 2x7 is
    # the only shrouded IDC that fits under the deck (see ui_board.py); if it is gone,
    # the fallback is the VERTICAL DC3-2.54-14PAS, which needs the board re-laid for a
    # different exit -- not a like-for-like swap. Check it before ordering.
    "DC3-2.54-14PAL": "C5156673",
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
)


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


_fab.configure(HERE, BOARDS, LCSC, OPEN_VALUES, ORDER_EVERY_BOARD, after=_check_bom_md)
fab = _fab.fab
main = _fab.main

if __name__ == "__main__":
    main(sys.argv[1:] or list(BOARDS))
