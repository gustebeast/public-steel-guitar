"""Optical pickup board — 10 strings, 20 photodiodes, USB high speed. x1.

    py -3.12 elec/optical.py            # -> elec/out/optical.{net,board.json}

THE SIXTH AND LAST BOARD, and the only one whose GEOMETRY IS AN INPUT rather than
an output. The other five size themselves from their parts; this one is
shaped by the instrument -- a 14 mm band of deck between the magnetic pickup's
cavity and the endplate -- and `src/optical_pickup.py` has carried that geometry,
part by part, since long before there was a netlist.

⚠ SO THE PLACEMENTS ARE IMPORTED FROM THE CAD, NOT RETYPED HERE. Every other
board in elec/ is the source and the CAD follows it; this one is the reverse, and
copying 153 positions into a second file would have created exactly the drift the
rest of the pipeline is built to prevent. `src.optical_pickup.PARTS` is the single
source, and _placements() below translates it into board-local coordinates. If a
part moves in the CAD it moves here, and if a ref exists in one and not the other
the build fails rather than laying out a board that does not match the model.

⚠ AND THAT IS WHY EVERY PART HERE CARRIES AN EXPLICIT `ref=`. SKiDL normally
numbers a ref_prefix group by CREATION order and ignores the tag -- a hazard that
has bitten this project three times. It cannot produce the CAD's refs at all,
though: they are deliberately non-contiguous (R1-R10 are the per-string LED
ballasts, R30-R38 the pulls, R40-R41 the buck divider), because the CAD spells out
the ambiguous groups rather than pattern-matching them. Passing `ref=` explicitly
makes SKiDL honour the name instead of the order, which both matches the CAD and
removes the creation-order trap from this file entirely.

WHAT THIS BOARD IS, in one paragraph: ten IR emitters fire up at ten strings;
twenty photodiodes -- a symmetric pair per string -- catch the reflection; twenty
transimpedance amps turn tens of nanoamps into volts; five four-channel audio
converters (TLV320ADC3140) digitise them and hand the STM32H743 five TDM lanes;
firmware demodulates the 48 kHz emitter carrier, forms SUM (the audio) and DIFF (the lateral
axis, which is what stops a precessing string reading an octave high); and the
result leaves over USB HIGH SPEED. See src/optical_pickup.py for why optical
rather than magnetic, why the detectors sit across Y rather than along X, and why
SUM alone is not enough -- none of that reasoning is repeated here.

⚠ USB HIGH SPEED IS A REQUIREMENT, NOT A PREFERENCE, and it is what forces the
external PHY. 10 channels x 48 kHz x 16 bit = 960 kB/s, and full speed's
isochronous ceiling is 1023 B/frame = 1023 kB/s -- 94% of the bus, which is not a
margin. The STM32H7's OTG_HS core has no on-chip HS PHY, so it needs a ULPI one
(U7). That is the one architectural difference from the other two MCU boards here,
which are CH32V307s with the PHY built in.

⚠ THE LINK IS SHORT NOW. It used to run ~800 mm to the Pi at the keyhead; since
the output panel gained a high-speed hub it runs ~100 mm to that board's J4
instead, and the hub carries both devices upstream on one cable. Both are HS, so
neither sits behind a Transaction Translator.

⚠ ROUTING IS FINISHED: 0 unconnected, 0 violations, 0 warnings, reproduced across
runs, with a fab package whose BOM, CPL, drill file, gerber layer set and outline
have all been checked. This paragraph used to say the opposite -- "2 real violations
and 15 unconnected items" -- and it stayed wrong long after the board was clean,
which is worse than never having written it: a reader of this file would conclude
the board does not route.

WHAT ACTUALLY CLOSED IT, because the diagnosis is the reusable part:
  * The 13 DANGLING GND STUBS were a generator problem, not a routing one -- the
    router laid a track from a ground pad toward the plane and never placed the via
    at the end. add_missing_vias drops a via wherever a net changes layer with
    nothing to carry it, which is the mechanical cleanup this note predicted.
  * The 2 REAL ones, TIA_OUT_7A and TIA_IN_1B, did want a human and got one. They
    are closed by deliberate copper laid AFTER routing (see the repair block in
    route.py): geometry searched with repair_search.py, verified clear against every
    obstacle class, and applied where the router cannot plan around it. Laid BEFORE
    routing the same copper cost five analog nets.
  * Freerouting converging at 20 and 30 passes was the right read. More effort was
    never the missing ingredient; the missing ingredient was doing the last two nets
    somewhere other than in the router.

⚠ AND CLEAN IS NOT VERIFIED. This is the part that has not changed. DRC compares
copper to a netlist: it does not know that twenty summing nodes read tens of
nanoamps, or that a 60 MHz ULPI bus has timing. All three things this paragraph
used to list as unchecked now have numbers attached: verify.py holds ULPI skew
against the PHY datasheet's own numbers and the USB pair's coupled length,
the TIA inputs are shown not to NEED guarding, and the switcher's hot loop is
measured at 6.23 mm2 fifty millimetres from the nearest summing node -- all three
sit beside the MID divider and the regulator. What is still unconfirmed is
everything nobody has thought to ask. Treat the routed .kicad_pcb as a CANDIDATE
that passes every check we have, not as a board somebody has signed off.

The placement, which is the part this file is actually responsible for, is clean:
the only DRC violations on the placed board are the 20 declared sensor-triplet
courtyards -- verified, all twenty are a PDnA/PDnB photodiode against its own Dn.

"""


import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import optical_pickup as OP  # noqa: E402  (the geometry source -- see above)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import json  # noqa: E402

from skidl import ERC, Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

import netcheck                                     # noqa: E402

P = Pin.types.PASSIVE

# ── the CAD's package names -> real KiCad footprints ─────────────────────────
# ⚠ TWO OF THESE DELIBERATELY DISAGREE WITH THE CAD ENVELOPE, and the CAD says so
# itself: U10 is modelled as SOT-563 but the USBLC6-2SC6 is SOT-23-6, and U11 is
# modelled as SOT-23-5 but the TLV9061 is SC-70-5. In both cases the MODEL is the
# larger box, so the clearance checks stay conservative -- but the FOOTPRINT has to
# be the real part or the board is unbuildable. The model is wrong in the safe
# direction; the footprint cannot be wrong in either.
FP = {
    "0402":     "Resistor_SMD:R_0402_1005Metric",     # overridden per-part below
    "0603":     "Resistor_SMD:R_0603_1608Metric",
    "0805C":    "Capacitor_SMD:C_0805_2012Metric",
    "1206C":    "Capacitor_SMD:C_1206_3216Metric",
    "2512R":    "Resistor_SMD:R_2512_6332Metric",
    "0603OPT":  "LED_SMD:LED_0603_1608Metric",
    "0805OPT":  "LED_SMD:LED_0805_2012Metric",
    "PD15":     "Steel:Everlight_PD15-22B",           # elec/footprints/Steel.pretty
    "WQFN-24":  "Package_DFN_QFN:Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",
    "RNX12":    "Steel:Texas_RNX0012_VQFN-HR-12_2x3mm_P0.5mm",
    "SOIC-14":  "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    "VSSOP-8":  "Package_SO:VSSOP-8_3x3mm_P0.65mm",
    "LQFP144":  "Package_QFP:LQFP-144_20x20mm_P0.5mm",
    "LQFP176":  "Package_QFP:LQFP-176_24x24mm_P0.5mm",
    "QFN-24":   "Package_DFN_QFN:HVQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm",
    "QFN-32":   "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm",
    "SOT-223":  "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    "SOT-23":   "Package_TO_SOT_SMD:SOT-23",
    "SOT-23-5": "Package_TO_SOT_SMD:SOT-23-5",
    "SOT-23-6": "Package_TO_SOT_SMD:SOT-23-6",
    "SOT-563":  "Package_TO_SOT_SMD:SOT-23-6",        # ⚠ see the note above
    "3225":     "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    "OSC3225":  "Oscillator:Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm",
    # Sunlord's own recommended land (1.1 x 3.7 pads on a 3.0 mm pitch), not the
    # Bourns SRN4018 one that used to be here -- LCSC stocks no usable SRN4018 value.
    "IND-4040": "Inductor_SMD:L_Sunlord_SWPA4030S",  # the 4 x 4 land; WPN4020H shares it
    "TP": "TestPoint:TestPoint_Pad_D1.5mm",
    # ⚠ A SMALLER PAD IS NOT A COMPROMISE, IT IS WHERE THE ROOM IS. See TP6/TP7.
    "TP_SMALL": "TestPoint:TestPoint_Pad_D1.0mm",
    "USB-C":    "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
    "XH-SM-4Y": "Connector_JST:JST_XH_S4B-XH-SM4-TB_1x04-1MP_P2.50mm_Horizontal",
}
# The 0402s are a mix of R and C; the CAD's package name does not say which, so the
# REF prefix does. Same for 0603 (all resistors: the LED ballasts) and the 0805s.
_R_0402 = "Resistor_SMD:R_0402_1005Metric"
_C_0402 = "Capacitor_SMD:C_0402_1005Metric"


# (There is no _fp() helper. An earlier draft had one that mapped a CAD package name
#  to a footprint, but every Part below names its own footprint at the point of
#  creation -- which is where a reader looks for it -- so the helper was never called.
#  A dead function is bad enough; a dead function that a COMMENT points at as the
#  explanation is worse, because it sends the next reader somewhere that does not
#  decide anything. The two CLASS packages are resolved like this:
#    0402    -> R_0402 for Rf*/R*, C_0402 for Cf*/Cd*/C*      (by ref prefix)
#    0805OPT -> LED_0805 for the ten emitters D1-D10,
#               D_0805 for the twenty detectors PD<n>A/B      (same land, and the
#               silkscreen polarity marker differs -- these are the parts an
#               assembler is most likely to fit backwards)
#  Verified against the generated netlist: 10 LED_0805, 20 D_0805, 20 Rf and 11 R on
#  R_0402, 10 ballasts on R_0603, 30 Cf/Cd on C_0402.)


# ── STM32H743IIT6, LQFP176 ───────────────────────────────────────────────────
# ⚠ THE PART CHANGED FOR STOCK, NOT FOR DESIGN (user, 2026-09-17). The LQFP144
# STM32H743ZIT6 showed ZERO at JLCPCB; the LQFP176 STM32H743IIT6 had 548 (C89597,
# $10.01 @10 against $9.93). It is the same die -- same ADCs, same OTG_HS, same 2 MB
# flash -- so every PORT assignment below (the ADC pairs, ULPI) carries over unchanged,
# and only the pin NUMBERS move. The alternative was the H750ZBT6 in the same LQFP144,
# which would have kept the footprint but cost 1.9 MB of flash and an external QSPI part.
#
# ⚠ PIN NUMBERS READ OUT OF KiCad's OWN ST SYMBOL LIBRARY (MCU_ST_STM32H7.kicad_sym,
# symbol STM32H743IITx), not recalled. That library is generated from ST's CubeMX
# database. The method was checked before it was trusted: re-deriving the old LQFP144
# map from symbol STM32H743ZITx the same way reproduced all 49 entries exactly, and
# every port this board uses exists on the LQFP176.
MCU_VDD = (15, 23, 36, 49, 62, 72, 82, 91, 103, 127, 136, 149, 159, 172)
MCU_VSS = (14, 22, 48, 61, 71, 90, 102, 113, 126, 135, 148, 158)
PIN = {  # port name -> LQFP176 pin
    "PA0": 40, "PA1": 41, "PA2": 42, "PA3": 47, "PA4": 50, "PA5": 51,
    "PA6": 52, "PA7": 53, "PA13": 124, "PA14": 137,
    "PB0": 56, "PB1": 57, "PB3": 161, "PB4": 162, "PB5": 163,
    "PB10": 79, "PB11": 80, "PB12": 92, "PB13": 93,
    "PC0": 32, "PC1": 33, "PC2_C": 34, "PC3_C": 35, "PC4": 54, "PC5": 55,
    # ULPI_DIR and ULPI_NXT, moved off the analog-switch pads -- see the note above ULPI
    "PI11": 13, "PH4": 45,
    "PF3": 19, "PF4": 20, "PF5": 21, "PF6": 24, "PF7": 25, "PF8": 26,
    "PF9": 27, "PF10": 28, "PF11": 59, "PF12": 60, "PF13": 63, "PF14": 64,
    "PH0": 29, "PH1": 30,
    # the audio converters' buses -- see THE CONVERTERS below
    "PE3": 2, "PE4": 3, "PE5": 4, "PE6": 5, "PI6": 175, "PD1": 143,
    "PF0": 16, "PF1": 17, "PF2": 18, "PF15": 65,
    "NRST": 31, "BOOT0": 166, "PDR_ON": 171,
    "VBAT": 6, "VDDA": 39, "VSSA": 37, "VREF+": 38, "VDD33_USB": 114,
    "VCAP1": 81, "VCAP2": 125,
}

# ── ULPI, and it takes seven pins the ADC wanted ─────────────────────────────
# The OTG_HS ULPI mapping is essentially fixed on this part -- most of these signals
# have exactly one pin. The alternates for DIR and NXT (PI11, PH4) were not bonded
# out on the LQFP144 this map was written for; on the LQFP176 they ARE (pins 13 and
# 45), so moving DIR/NXT off the analog-switch pads below is now possible. It is NOT
# done here: the swap to LQFP176 was for stock, and changing two ULPI pins in the same
# step would mix a stock fix with a design change. Worth doing deliberately.
#
# ⚠ PC2_C AND PC3_C NOW CARRY TWO OF THE TWENTY ANALOG CHANNELS, AND THE FIRMWARE RULE
# HAS REVERSED. This block used to say ULPI lands here and the SYSCFG analog switch must
# be LEFT CLOSED; that has been wrong since ULPI moved to PI11/PH4, and the instruction
# is now the opposite. PC2SO/PC3SO in SYSCFG_PMCR must be SET, opening the switch, so
# that ADC3 reaches the _C pads by the direct low-impedance path these pins exist for.
# Left at their reset value the conversion still works, through the switch and whatever
# series resistance it has -- which is exactly the kind of fault that measures as a
# slightly slow settling channel and is never traced back to a register.
#
# ⚠ THE TRAP THAT USED TO BE HERE IS GONE, NOT MOVED. It was that an ADC-heavy design
# would open these switches for analog performance and silently kill USB. With ULPI
# elsewhere, opening them is simply correct, and the pins are doing the one job they were
# bonded out for: on the LQFP176 the ordinary PC2/PC3 pads are not bonded at all, so the
# _C pad IS the pin. PA0_C and PA1_C, the ADC1/ADC2 equivalents, are not bonded on this
# package either -- dashes in the LQFP176 column of DS12110's pin table, balls T1/T2 on
# the BGA only -- which is why the near-edge slack is these two pins and no more.
# ⚠ ULPI_DIR AND ULPI_NXT USED TO SIT ON PC2_C / PC3_C AND HAVE BEEN MOVED OFF THEM.
# What follows is why they were there, why it worked, and why "it works" was not good
# enough.
#
# On the STM32H743, PC2 and PC3 have TWO pads on the die: the ordinary digital pad and
# a "_C" pad wired straight to ADC3 for a low-impedance analog path. On the LQFP176
# ONLY THE _C PAD IS BONDED OUT -- ST's LQFP176 pinout (DS12110 Fig. 9) brings out
# PC2_C at pin 34 and PC3_C at pin 35, and PC2/PC3 appear on no LQFP176 pin at all.
# The pin table gives PC2_C and PC3_C an I/O structure of "ANA" with an EMPTY alternate
# function column, which reads like a hard fault: OTG_HS_ULPI_DIR is an alternate
# function of PC2, and PC2 is not on this package.
#
# Footnote 6 of that table is what rescues it: "There is a direct path between Pxy_C and
# Pxy pins/balls, through an analog switch. Pxy alternate functions are available on
# Pxy_C WHEN THE ANALOG SWITCH IS CLOSED." The switch is closed at reset (SYSCFG_PMCR
# PC2SO/PC3SO default to 0), so the board works out of the box and a bring-up would
# never surface this.
#
# ⚠ THE TRAP WAS SHAPED EXACTLY LIKE THIS BOARD, WHICH IS WHY IT IS NOT WORTH KEEPING.
# Those switches exist so ADC3 can reach the _C pads directly, and OPENING them is what
# an ADC-heavy design does for analog performance -- which is precisely what this board
# is. Anyone tuning the twenty-channel front end, reading "direct channels optimise ADC
# performance" and setting PC2SO/PC3SO, would disconnect ULPI_DIR and ULPI_NXT from the
# PHY. USB would stop enumerating and nothing in the schematic, the netlist or DRC would
# point at it. A constraint whose only enforcement is a comment, on the exact axis the
# board invites you to optimise, is a trap and not a design.
#
# ⚠ AND IT WAS FREE TO REMOVE, WHICH SETTLED IT. OTG_HS_ULPI_DIR is also on PI11 and
# OTG_HS_ULPI_NXT is also on PH4 (DS12110 pin table); on the LQFP176 those are pins 13
# and 45, and both were unused. The two arguments for staying both collapsed on
# measurement:
#   "it keeps the bus together"  -- the bus is ALREADY on all four package edges
#                                   (pins 32 47 51 56 57 79 80 92 93 163), and PH4
#                                   lands on the edge where six of the ten already are
#   "it costs routing"           -- measured to the PHY: PC2_C 37.2 mm and PC3_C
#                                   36.8 mm become PI11 45.9 mm and PH4 30.7 mm. Net
#                                   +2.6 mm across the pair, inside a bus that already
#                                   spans 22.4 to 49.7 mm. At ~6.6 ps/mm that is 53 ps
#                                   on a 16.7 ns ULPI clock.
#
# So the firmware constraint is gone rather than documented, and ADC3_INP0 / ADC3_INP1
# are available again if a twenty-first channel is ever wanted.
#
# The other ten assignments were checked the same way, against DS12110's pin table:
# all ten name their OTG_HS_ULPI_* function on the port this map uses.
ULPI = {"ULPI_D0": "PA3", "ULPI_D1": "PB0", "ULPI_D2": "PB1", "ULPI_D3": "PB10",
        "ULPI_D4": "PB11", "ULPI_D5": "PB12", "ULPI_D6": "PB13", "ULPI_D7": "PB5",
        "ULPI_CK": "PA5", "ULPI_STP": "PC0", "ULPI_DIR": "PI11",
        "ULPI_NXT": "PH4"}

# ── THE CONVERTERS: FIVE TLV320ADC3140s, NOT THE MCU'S OWN ADCs (2026-09-21) ──────
# This section used to be ~340 lines on mapping twenty channels onto the H743's three ADCs:
# which pins each unit could reach, the pair skew a sequenced scan could not avoid, which
# strings came out with DIFF sign-inverted, and three routing proxies that each predicted
# wrong. All of it went with the decision below (it is in git history, 2026-09-21).
#
# WHY THE MCU'S ADCs WENT. They were this board's noise floor. DS12110 rev V gives 77 dB SNR
# single-ended -- characterised on BGA, "values for LQFP packages might differ" -- which is
# ~165 uVrms, against the ~35-50 uVrms the front end makes once its own op-amp noise is
# band-limited. Oversampling could not rescue it: ADC3 carried ten conversions, six of
# them on SLOW channels (1 Msps at 16 bit, DS12110 Table 185 notes), so ~4x was the
# ceiling. A delta-sigma audio converter fixes all of it at once:
#   * ~13 uVrms (SBAS993B 7.5: 106 dB SNR A-wt at 2 Vrms differential full scale)
#   * its decimation filter removes everything above the band, so the op-amps' voltage
#     noise out to their GBW no longer folds into the audio
#   * all twenty channels convert on ONE edge (shared BCLK/FSYNC), so a string's A and B
#     are simultaneous by construction -- the old pair-skew budget and the
#     DIFF_SIGN_INVERTED bookkeeping have nothing left to describe
#   * the analog nets end at a converter beside the MCU instead of fanning into a 0.5 mm
#     pitch LQFP edge -- which was this board's routing problem, every time
# ONE CONVERTER PER QUAD: U14..U18 take U1..U5's four outputs, IN1..IN4 in the quad's own
# section order (see SEC below), single-ended AC-coupled (SBAS993B Fig. 31): INxP from the
# TIA output through 10 nF C0G, INxM to GND through its own 10 nF C0G. TI rates the
# DIFFERENTIAL connection a few dB better; at ~13 uVrms against a light-limited ~35 uVrms
# floor that is not what limits this board, and a differential INxM had no room to route.
#
# ⚠ THEY RUN AT fS = 192 kHz AND THE EMITTERS ARE MODULATED AT 48 kHz, LOCKED TO FSYNC.
# The old ambient scheme -- a LEDs-on and a LEDs-off sample inside each 48 kHz frame --
# needs a sampler; a delta-sigma converter's filter averages the two together. So ambient
# rejection becomes a LOCK-IN: the emitters square-wave at fS/4, the string's audio rides
# as sidebands at 28..68 kHz inside the 192 kHz filter's ~86 kHz passband, and firmware
# multiplies by the +-1 reference and decimates to 48 kHz. Ambient light and its flicker
# land at 28..68 kHz after demodulation and are filtered away. (A 10 nF coupling cap into
# the 20 k input setting is an ~800 Hz high-pass, far below the carrier's lowest sideband.)
# The TIAs must pass the carrier, so their pole moved from 15.4 kHz to ~160 kHz -- see Rf.
#
# 20 ch x 16 bit x 192 kHz is 61 Mbit/s, more than one TDM lane carries (BCLK <= 24.576
# MHz), so EACH CONVERTER GETS ITS OWN DATA LANE at BCLK 12.288 MHz (4 slots x 16 bit x
# 192 kHz), all five on one BCLK/FSYNC pair driven by SAI1 block A. Pins, read off KiCad's
# STM32H743IITx symbol alternates (which are generated from ST's database):
#   SAI1_SCK_A PE5 (4), SAI1_FS_A PE4 (3)                      -- the one clock pair
#   lane 1 SAI1_SD_A PE6 (5)   lane 2 SAI1_SD_B PE3 (2)   lane 3 SAI2_SD_B PA0 (40)
#   lane 4 SAI2_SD_A PI6 (175) lane 5 SAI3_SD_A PD1 (143)
# ⚠ SAI2 AND SAI3 RUN AS SYNCHRONOUS SLAVES OF SAI1 (SAI_GCR SYNCIN), taking its clocks
# internally -- which is why lanes 3-5 need no SCK/FS pins of their own. SAI4 would have
# kept lane 5 on the strip-facing edge (PC1, pin 33) but it sits in the D3 domain; confirm
# SAI4<-SAI1 synchronisation in RM0433 before moving it there.
# CONTROL IS ONE I2C BUS AT ONE ADDRESS, ALL FIVE PARTS WRITTEN AT ONCE (2026-09-22). The
# five are configured IDENTICALLY -- each already has its own data lane, so each uses slots
# 0-3 on it -- so every register write is the same write to all five, and they share
# address 1001100 (both straps to GND). Open-drain ACKs from five parts simply wire
# together. What it gives up is reading one part back on its own (a read returns the
# wired-AND of five); firmware only writes. What it bought: this used to be two buses
# (I2C2 for four parts at four addresses, I2C4 for the fifth), and the straps that pulled
# ADDR0/ADDR1 up to +3V3D were two of the last 14 nets the router could not close -- the
# address pins sit between the I2C pins on the part's routing side.
# I2C2: PF0 SDA (16), PF1 SCL (17).
# ⚠ SHDNZ IS TIED TO EACH PART'S OWN IOVDD, NOT DRIVEN BY THE MCU (2026-09-22). As one
# six-terminal net across the cells it failed in every routing -- three layouts, escape vias
# and all. Tied locally it is five private hops: pin 14 -> via -> In2 down the channel ->
# via -> the IOVDD cap's rail pad, all laid (see "tracks"/"vias"). What it costs: TI's
# power-up sequence holds SHDNZ low until AVDD and IOVDD settle (SBAS993B 9.2.1.2 step 1);
# tied high, the parts leave shutdown as IOVDD rises. FIRMWARE MUST THEREFORE ISSUE THE
# SOFTWARE RESET (P0_R1, SW_RESET) over the I2C broadcast once both rails are up, before
# configuring -- that is the documented recovery, and the only one this board keeps.
# Hardware shutdown (the < 1 uA state) is lost; nothing here needs it.
# ⚠ THE EMITTER GATE (PB3) IS TIM2_CH2, and firmware must run it from the same PLL as the
# SAI kernel clock so the carrier is frequency-locked to FSYNC; its phase is fixed at start.
SAI_CLK = {"SAI_SCK": "PE5", "SAI_FS": "PE4"}
SAI_SD = ("PE6", "PE3", "PA0", "PI6", "PD1")     # lane k -> converter U(14 + k)
I2C_BUS = (("PF0", "PF1"),)                       # (SDA, SCL): I2C2
ADC_I2C = (0, 0, 0, 0, 0)                          # converter k -> bus
ADC_ADDR = (0, 0, 0, 0, 0)                         # converter k -> ADDR1:ADDR0 strap


def _r(ref, value, desc, fp=_R_0402):
    return Part(name="R", ref_prefix="R", ref=ref, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(ref, value, desc, fp=_C_0402):
    return Part(name="C", ref_prefix="C", ref=ref, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


@subcircuit
def optical():
    # ⚠ THERE IS ONE GROUND, AND THERE USED TO BE TWO THAT NEVER MET.
    # PWR_GND was declared here beside GND, with no comment and no rationale, and
    # collected the buck's return (U13, C160-C162, R41), the 24 V inlet's return (J2.1)
    # and the emitter row's switch (Q1.2). GND collected everything else -- every IC,
    # every decoupling cap, the USB shield, the crystals.
    #
    # NOTHING JOINED THEM. Not a component, not a net tie, not a stitch, not a zone.
    # Checked pin by pin on 2026-09-17: no part in the netlist had a pin on both, so the
    # buck's return path to its own loads was OPEN and the board could not have worked.
    #
    # ⚠ AND NOTHING COULD HAVE FOUND IT. Each net is internally fully connected, so the
    # ratsnest is empty and DRC reports nothing; the router routes both happily; ERC
    # sees two power nets, each properly driven. It is invisible to every check this
    # pipeline runs, which is why there is now a check for exactly it (see
    # _assert_grounds_meet below).
    #
    # THE FIX IS ONE NET, NOT A TIE, and that is a real decision rather than the lazy
    # one. A single-point "star" return is the right technique when there is no ground
    # plane -- when every return shares routed copper and you are choosing who shares
    # with whom. This board has a SOLID GND PLANE on In1.Cu and GND pours on F.Cu and
    # B.Cu. With a plane, splitting the return is actively worse: the split forces
    # return current to detour around the gap to reach the tie point, which ENLARGES
    # the very loops the split was meant to contain.
    #
    # What actually keeps the switcher quiet here is placement, and that is already
    # done: U13, C160 and C162 sit in one row so the high-di/dt loop is short, and the
    # buck is at the -Y tail as far from the photodiodes as the board allows. Q1's
    # emitter return -- 211 mA square-waved at 48 kHz, the board's worst aggressor -- is
    # better off on the plane directly beneath its own V5_PRE feed than on a trace
    # running back to a tie point.
    #
    # If a split is ever wanted again it needs BOTH halves: the separation AND an
    # explicit single-point join, with the reason written here.
    gnd = Net("GND")
    pgnd = gnd
    v5, v3d, v3a = Net("+5V"), Net("+3V3D"), Net("+3V3A")
    # V5_PRE is the BUCK side of the ferrite bead. Declared up here with the other
    # rails because the emitter row is wired long before the buck section builds it,
    # and a rail that half the board hangs on is not a local of the buck block.
    v5_pre = Net("V5_PRE")
    for n in (gnd, v5, v3d, v3a):
        n.drive = Pin.drives.POWER
    # MID is the TIAs' reference: the photodiodes run in PHOTOCONDUCTIVE-free
    # (zero-bias) mode into a virtual earth held here, and every TIA's + input sits
    # on it. It is buffered (U11) rather than being a bare divider because 20 summing
    # nodes hanging off a resistive divider would couple to each other through it.
    mid = Net("MID")

    # ── the ten sensing channels ─────────────────────────────────────────────
    # Per string: one emitter D(i) with ballast R(i), two photodiodes PDA/PDB, two
    # TIAs (a quarter of a quad each) with Rf/Cf, and two converter channels.
    led_row = Net("LED_ROW")        # the switched low side, common to all ten
    pd_a, pd_b = {}, {}
    for i in range(1, 11):
        # THE BALLAST IS PER-STRING AND THAT IS LEVER 2 OF THE SIGNAL BUDGET. A .014
        # plain string returns ~14 dB less than a .070 wound one because the string IS
        # the reflective target, so values are set at bring-up, per string, not here.
        # ⚠ LEVER 1 IS NO LONGER GONE. This note used to say narrow-beam emitters were
        # unavailable and the beam-angle lever was unspendable. That was true of the parts
        # surveyed at the time; the LTE-C9901 is 65 deg FULL angle against the old part's
        # 120, and combined with its 8 mW/sr typ that is where the +10.9 dB came from.
        # 180R NOW GIVES EXACTLY 20 mA, the datasheet's own operating point: the LTE-C9901
        # drops 1.4 V typ, so (5.0 - 1.4) / 180 = 20.0 mA on the nose. The old 1.2 V part
        # made the same resistor 21 mA.
        # ⚠ THE BUCK IS NOT THE CONSTRAINT AND A NOTE HERE BRIEFLY CLAIMED IT WAS. This
        # part is rated 60 mA continuous against the old part's 65, and "ten emitters flat
        # out is 600 mA against a 600 mA buck" was written from the 600 mA figure in the
        # budget below -- which is the TPS560430's, kept there as HISTORY. U13 has been the
        # 3 A LMR33630 since 2026-09-22, and the budget says so two lines above the number
        # that got read. Ten emitters at 60 mA continuous is 600 mA, and the whole board's
        # worst case then is 1068 mA: 36 % of the buck. There is no current problem.
        # WHAT DOES BIND, if the drive is ever raised, is all local:
        #   * the emitter's own 100 mW Pd -- 60 mA x 1.4 V is 84 mW, 84 % of it, and an
        #     0603 has less copper to lose it into than the 0805 this replaced. This is
        #     the real reason the part is rated 60 and not more.
        #   * C162's droop over a pulse: 600 mA for a 10.4 us half-period at 48 kHz is
        #     284 mV on 22 uF, 133 on 47, 62 on 100.
        #   * Q1, one SOT-23 gating all ten.
        # And the lever is smaller than it looks: 20 -> 60 mA is 3x optical = +2.4 dB of
        # shot-limited SNR, against the +10.9 dB the emitter swap just banked. Spend it
        # only if bring-up says the thin string needs it.
        # A 100 mW 0402 (Panasonic ERJ2RKF1800X, C413069), NOT THE HOUSE 62.5 mW ONE
        # (pre-order review, 2026-10-06). At 50 % duty it carries 36 to 40 mW, but nothing
        # in hardware limits the on-time: LED_GATE is one MCU pin, and a test mode or a
        # halted debugger that parks it high puts 72 to 80 mW in each ballast for as long
        # as it stays there -- 115 to 128 % of the part that was ordered, while the note
        # that signed this off called it an 0603 rated 100 mW. Same land, same value.
        r = _r("R%d" % i, "180R 100mW", "LED ballast, string %d -- 20 mA, tune per string" % i)
        d = Part(name="LED_IR", ref_prefix="D", ref="D%d" % i, dest="NETLIST",
                 tool="skidl", value="LTE-C9901",
                 description="IR emitter 940 nm, string %d (LCSC C2683614)" % i,
                 footprint="LED_SMD:LED_0603_1608Metric",
                 pins=[Pin(num=1, name="K", func=P), Pin(num=2, name="A", func=P)])
        v5_pre += r[1]        # BUCK side of the bead -- see FB1
        # ⚠ NAMED, BECAUSE SKiDL'S AUTO-NAMES ARE POSITION-DEPENDENT. A two-pin local
        # link left unnamed becomes "N$8", and the number is assigned by order of
        # creation -- so adding a part anywhere earlier in this file RENUMBERS every one
        # of them. This project's whole method is comparing one run's DRC and router
        # report against the last one's; a net identifier that shifts underneath that
        # comparison is worse than useless. And "N$8" does not say which string it is.
        Net("LED_A%d" % i).connect(r[2], d[2])
        led_row += d[1]
        for tag, store in (("A", pd_a), ("B", pd_b)):
            # ⚠ PD<string><side>, NOT PD<side><string>. The CAD names them PD1A/PD1B
            # and the placements are keyed by ref, so the two orderings are not
            # interchangeable -- they quietly produce a board whose parts sit in the
            # right places under the wrong names.
            # Everlight PD15-22B/TR8, two lands a terminal -- elec/layout.py nets every pad
            # that shares a number. THE PAD NUMBERS ARE OURS, NOT EVERLIGHT'S: pad 1 is the
            # ANODE pair and pad 2 the CATHODE pair. Everlight (DPD-0000195 rev 4, p.2)
            # numbers the four lands 1..4 with 1 and 4 the cathode, the side that carries
            # the body's stripe, and 2 and 3 the anode; the fab's footprint follows
            # Everlight. So the stripe goes on OUR PAD 2, and the placement frame in
            # fab_frames.json turns the part to put it there (seen in the fab's preview,
            # 2026-10-06: by pin number alone all twenty went on backwards).
            pd = Part(name="PHOTODIODE", ref_prefix="PD", ref="PD%d%s" % (i, tag),
                      dest="NETLIST", tool="skidl", value="PD15-22B/TR8",
                      description="filtered Si PIN photodiode, string %d side %s "
                      "(LCSC C161211)" % (i, tag),
                      footprint="Steel:Everlight_PD15-22B",
                      pins=[Pin(num=1, name="A", func=P), Pin(num=2, name="K", func=P)])
            store[i] = pd

    # ── U21-U30: the transimpedance amps, ONE DUAL PER STRING ────────────────
    # TLV9062, VSSOP-8 (DGK). Same die as the TLV9064 this replaced -- one datasheet, one
    # electrical table -- so 500 fA input bias, 10 MHz GBW and 10 nV/rtHz are unchanged.
    # WHY NOT THE QUAD. Sourcing first: JLCPCB stocks 107 of the quad against 34,405 of
    # the dual, at a third the price. But the electrical reason is the one that would have
    # forced it anyway. A quad serves four detectors over 14.25 mm of y, so three of its
    # four summing nodes -- the only high-z nets on this board -- run past neighbouring
    # stations. Every station's emitter carries the SAME 192 kHz carrier, so charge
    # coupled into a summing node arrives IN PHASE with the demodulator and integrates up
    # as a fixed offset that is indistinguishable from string displacement. Measured on
    # the CAD placement: all twenty nodes are now 5.13 mm with zero spread, against three
    # of four at ~15 mm and four different lengths.
    # AND THE DIFFERENCED PAIR IS ON ONE DIE. Supply, substrate and temperature perturb
    # both halves of a dual together, so they are common mode and cancel in A-B. That is
    # the whole measurement.
    duals = {}
    for i in range(1, 11):
        duals[i] = Part(
            name="TLV9062", ref_prefix="U", ref="U%d" % (20 + i), dest="NETLIST",
            tool="skidl", value="TLV9062IDGKR",
            description="dual op-amp, 2x TIA for string %d (LCSC C398356)" % i,
            footprint="Package_SO:VSSOP-8_3x3mm_P0.65mm",
            pins=[Pin(num=n, func=P) for n in range(1, 9)])
    # VSSOP-8 dual pinout: 1 OUT_A, 2 IN-_A, 3 IN+_A, 4 V-, 5 IN+_B, 6 IN-_B, 7 OUT_B,
    # 8 V+.  Section A takes the +Y detector and B the -Y one, which is also how the part
    # is rotated in the CAD (OP_ROT 270 puts A's pins on the +Y side). No height mapping
    # needed any more -- that was a quad problem, where four sections had to be matched to
    # four detectors spread over two strings and a naive order crossed two of them.
    SEC = {"A": (1, 2, 3), "B": (7, 6, 5)}      # (out, in-, in+)

    tia_out = {}
    for ch in range(20):                       # 0..19 -> (string, side)
        i, side = ch // 2 + 1, "A" if ch % 2 == 0 else "B"
        q = duals[i]
        out_p, inn_p, inp_p = SEC[side]
        # Rf<string><side>, the CAD's scheme: Rf1A/Rf1B for string 1's dual.
        n = "%d%s" % (i, side)
        pd = (pd_a if side == "A" else pd_b)[i]
        summing = Net("TIA_IN_%d%s" % (i, side))
        out = Net("TIA_OUT_%d%s" % (i, side))
        tia_out[(i, side)] = out
        # ZERO BIAS: the photodiode's CATHODE sits on the virtual earth and its ANODE on
        # MID, so there is no reverse bias and next to no dark current.
        #
        # ⚠ IT WAS WIRED THE OTHER WAY ROUND UNTIL 2026-09-21, AND THE OUTPUT WENT THE WRONG
        # WAY. Photocurrent leaves a photodiode by its ANODE (it is the + terminal, which is
        # why Voc is forward polarity), so an anode on the summing node pushes current IN
        # and drives the output DOWN from MID -- and MID is 0.33 V, set there precisely
        # because the output was believed to swing UP (see R34). Every string but the
        # thinnest would have clipped at the rail. With the cathode on the virtual earth
        # the photocurrent is drawn out through Rf and the output rises, which is what the
        # rest of the board assumes.
        #
        # ⚠ THE NOISE FLOOR IS THE LIGHT NOW, NOT THE ELECTRONICS. The budget that used to
        # sit here left out photon shot noise, and every SNR it quoted (67, 75 dB) inherited
        # that. Input-referred, per string, in the demodulated band (28..68 kHz at the
        # converter, 20 kHz after the lock-in), thinnest string, no ambient:
        #   signal shot    sqrt(2q x 143 nA), on half the time      0.15 pA/rtHz
        #   Rf thermal     sqrt(4kT / 1M)                            0.13
        #   en x 2 pi f Cin at 60 kHz (10 nV, ~25 pF)                 0.09
        #   in             TLV9064                                   0.02
        #   converter      ~20 nV/rtHz at +12 dB PGA, / Rf           0.02
        # -> ~67 dB against the thin string's lock-in signal (I/2 at 50% duty). The 143 nA
        # is the old ~60 nA x the PD15's photocurrent (7 vs 2.2 uA per mW/cm2 at 940 nm)
        # x 0.75 for the wider triplet. AMBIENT IR adds its own shot noise on top: 1 uA
        # of it (~0.14 mW/cm2 in the 750-1100 nm band -- a halogen wash can do that) costs
        # ~9 dB. The daylight filter rejects visible light and nothing else: LED and
        # fluorescent stage lighting are gone, sun and incandescent are not. Their FLICKER
        # is removed by the lock-in; their shot noise and headroom are what the cover
        # (field of view) and Rf's headroom are for.
        # The lever left is LIGHT: shot-limited SNR grows as sqrt(emitter current), and the
        # emitters run at 21 mA of a 65 mA rating.
        mid += pd["A"]
        summing += pd["K"], q[inn_p]
        mid += q[inp_p]
        out += q[out_p]
        # ⚠ 1M / 1 pF SINCE 2026-09-21, FOR BANDWIDTH -- the TIA has to pass the 48 kHz
        # emitter carrier and its +-20 kHz sidebands, where the old 4M7 / 2.2 pF set a
        # 15.4 kHz pole that would have eaten them. The closed-loop limit is
        # sqrt(GBW / (2 pi Rf Cin)) = sqrt(10 MHz / (2 pi x 1M x ~25 pF)) = 250 kHz, and
        # 1 pF puts the feedback pole at 159 kHz; the least Cf that is stable is
        # sqrt(Cin / (2 pi Rf GBW)) = 0.63 pF, so 1 pF is 1.6x that. (Cin: the PD15's
        # zero-bias capacitance is NOT published -- 6 pF is at VR 5 V -- and ~17 pF is
        # assumed from the VEMD's own 0 V / 5 V ratio. Measure it: more makes the loop
        # quicker to ring and the en term larger.)
        # SIGNAL LEVEL: the thin string's ~143 nA gives 0.14 V at MID + ..., a wound
        # string ~0.7 V, leaving ~2 V of the 2.9 V swing for AMBIENT photocurrent (~2 uA)
        # before the output rails. The converter's PGA (0..42 dB) takes the small end up
        # to its full scale, so the gain split is Rf for headroom, PGA for level.
        # Still per string: the plain strings can take 2M if ambient allows.
        # ⚠ 250k / 2.2 pF SINCE 2026-09-23, AND THE REASON IS PHASE, NOT NOISE. At 1M the
        # least stable Cf is sqrt(Ct / (2 pi Rf GBW)) = 0.70 pF on a ~31 pF Ct (the PD15 at
        # ZERO bias, ~25 pF, plus the amp's 6). You cannot buy or hold 0.70 pF: the
        # smallest real 0402 C0G is 0.5 at +-0.25, and an 0402's own stray is a few tenths,
        # so the feedback capacitance would be set by layout parasitics and the pole would
        # land anywhere. That scatters the CARRIER PHASE by about +-5.8 deg part to part,
        # and a lock-in recovers amplitude from phase: two channels of one string that do
        # not match in phase put a spurious term straight into DIFF, which is the signal
        # pitch detection rides on. At 250k the part is 1.40 pF minimum, a real +-10% 2.2
        # pF holds it, and the spread is +-1.2 deg.
        # IT COSTS 0.31 dB, because this board is SHOT-NOISE limited -- the photodiode's
        # own shot noise is 0.80 pA/rtHz against Rf's 0.13 at 1M and 0.26 at 250k, so Rf
        # barely enters the total. Noise was never the axis this decision turned on.
        # 2.2 pF not 1.5: 1.5 sits 1.07x over the stability minimum, which is no margin at
        # all. 2.2 is 1.57x, puts the pole at 289 kHz -- still 4.3x the 68 kHz sideband
        # edge -- and leaves ~60 deg of phase margin.
        # AND THE NEW EMITTER FORCES IT ANYWAY: the LTE-C9901 is ~6x the incumbent's flux,
        # so 1M saturates the output outright against a 0.33 V MID.
        # THE PART IS 249k: 250k is not an E96 value and no catalogue stocks it (JLCPCB
        # lists one 250k 0402, at zero). 0.4 % under the figure every sum above uses.
        rf = _r("Rf%s" % n, "249k 1%", "TIA feedback, string %d%s -- tune per string" % (i, side))
        # ⚠ Cf IS C0G, NOT X7R: it sets the pole, and an X7R part's capacitance moves with
        # bias and temperature, so twenty channels would stop matching -- which is exactly
        # what DIFF cannot tolerate. 1 pF is at the edge of what a part sets rather than
        # the layout (an 0402's own stray is a few tenths): measure the pole at bring-up.
        cf = _c("Cf%s" % n, "2.2pF", "TIA feedback cap, string %d%s -- C0G, ~289 kHz pole"
                % (i, side))
        summing += rf[1], cf[1]
        out += rf[2], cf[2]
    # ⚠ THE QUADS RUN ON +3V3A, NOT +5V, AND THAT IS AN ABSOLUTE-MAXIMUM FIX.
    # (Written when every TIA output went straight to an MCU ADC pin; the converters'
    # inputs are AC-coupled now, but their abs max is AVDD + 0.3 all the same.)
    # Every TIA output went straight to an ADC pin, and ST's Table 21 (DS12110,
    # "Voltage characteristics") gives "input voltage on any other pins" an absolute
    # maximum of 4.0 V. On a 5 V rail a rail-to-rail output saturates at ~4.95 V, so
    # any channel driven into saturation -- an emitter reflecting off a bright surface,
    # a string removed, sunlight through the cover -- put ~1 V over the ADC's rating on
    # a pin that is not 5 V tolerant. That is device damage, not a bad reading.
    #
    # IT ALSO COSTS NOTHING TO FIX, which is what makes the old choice a plain mistake:
    # the ADC measures against VREF+ = +3V3A, so everything above 3.3 V was unreadable
    # anyway. The 5 V rail bought 1.7 V of swing that no conversion could see, at the
    # price of exceeding the ADC's limit. On +3V3A the TIA shares the ADC's own
    # reference -- ratiometric, so reference drift cancels instead of adding.
    # TLV9064: 1.8 V to 5.5 V supply, rail-to-rail in and out, so 3.3 V is in spec.
    # TLV9062: 1.8 to 5.5 V, RRIO, so 3.3 V is in spec -- same die as the TLV9064 the
    # note above was written for. ONE bypass per package now instead of two per quad: ten
    # packages each get their own 100 nF beside its own V+ pin, which is ten caps for
    # twenty channels against the quad's ten for twenty. Same count, half the distance.
    for i in range(1, 11):
        v3a += duals[i][8]
        gnd += duals[i][4]
        c = _c("Cd%d" % i, "100nF", "string %d dual supply bypass" % i)
        v3a += c[1]
        gnd += c[2]

    sai_sck, sai_fs = Net("SAI_SCK"), Net("SAI_FS")
    sai_sd = [Net("SAI_SD%d" % (k + 1)) for k in range(5)]
    i2c = [(Net("I2C%d_SDA" % b), Net("I2C%d_SCL" % b)) for b in (2,)]

    # ── U14-U18: the audio converters, one per quad ─────────────────────────
    # TLV320ADC3140IRTWT, WQFN-24 RTW. Pins (SBAS993B Pin Functions): 1 AVDD 2 AREG 3 VREF
    # 4 AVSS 5 MICBIAS 6/7 IN1P/IN1M 8/9 IN2P/M 10/11 IN3P/M 12/13 IN4P/M 14 SHDNZ
    # 15 ADDR1 16 ADDR0 17 SCL 18 SDA 19 IOVDD 20 GPIO1 21 SDOUT 22 BCLK 23 FSYNC 24 DREG,
    # 25 thermal pad (VSS). Support parts are TI's Figure 165, less MICBIAS's 1 uF: there
    # are no microphones and MICBIAS stays powered down, so the pin is left open.
    # AVDD on +3V3A (the quiet LDO -- it now carries these too, see the power budget),
    # IOVDD on +3V3D with the MCU it talks to.
    adcs = {}
    for k in range(5):
        u = Part(name="TLV320ADC3140", ref_prefix="U", ref="U%d" % (14 + k), dest="NETLIST",
                 tool="skidl", value="TLV320ADC3140IRTWT",
                 description="4-ch audio ADC, quad U%d's outputs (LCSC C1852021)" % (k + 1),
                 footprint="Package_DFN_QFN:Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",
                 pins=[Pin(num=n, func=P) for n in range(1, 26)])
        adcs[k] = u
        tag = k + 1
        areg, vref, dreg = (Net("ADC%d_AREG" % tag), Net("ADC%d_VREF" % tag),
                            Net("ADC%d_DREG" % tag))
        v3a += u[1]
        areg += u[2]
        vref += u[3]
        gnd += u[4], u[25]
        Net("ADC%d_MICBIAS_NC" % tag).connect(u[5])
        # ⚠ SHDNZ IS PULLED UP NOW, NOT TIED, AND THAT IS THE BOARD'S LAST DIAGNOSTIC GAP
        # CLOSED. Five converters answer at one address on one bus, so a part holding SDA
        # low killed the control bus with no way to say which part or to take it off --
        # item 6 of docs/optical-bringup-diagnostics.md, and the only failure the
        # per-device SDOUT lines do not already name. Ground this resistor's own SHDNZ
        # land and that converter alone drops off the bus; with SDOUT already per device,
        # that is complete localization.
        # WHAT IT COSTS: one 0402 per cell, in a clear site 2 mm from pin 14 that exists
        # at the SAME cell-frame offset in all five cells. NOT a shared SHDNZ spine -- that
        # wants ~86 mm of digital line and 8 new vias through In1, whose 0 cuts and
        # 0.266 mm thinnest web are a measured SI property of the analog reference.
        # ⚠ AND THE PULL-UP IS WHY THE FIRMWARE RULE BELOW STILL HOLDS: 10k to IOVDD leaves
        # the part out of shutdown as IOVDD rises, exactly as the hard tie did, so the
        # software reset is still mandatory. A pulled-up pin is not a driven pin; nothing
        # here changes the power-up sequence, it only gives a person a way to override it.
        shdnz = Net("SHDNZ%d" % tag)
        shdnz += u[14]
        rs = _r("Rs%d1" % tag, "10k",
                "U%d SHDNZ pull-up -- ground its pad 1 to drop this converter off the "
                "I2C bus" % (14 + k,))
        shdnz += rs[1]
        v3d += rs[2]
        # ⚠ NO SEPARATE PAD: THE PULL-UP'S OWN SHDNZ LAND IS THE ACCESS POINT, and that
        # is a deliberate trade rather than a saving. A 1.0 mm pad does fit in these cells
        # -- searched, (-3.810, +6.950) in cell frame, 0.348 mm of headroom -- but it lands
        # 4 mm from the resistor and would need its OWN stub to reach the net, which is
        # another ~4 mm of copper per cell inside the analog strip. Five pads would have
        # cost 20 mm of it, and the whole reason this variant was chosen over a shared
        # SHDNZ spine was to keep copper out of there.
        # SO THE THING YOU GROUND IS Rs<k>1 PAD 1, a 0.54 x 0.64 land. That is smaller
        # than the bring-up pads and the honest objection to it is the same one that
        # justified those: probing a 0402 among fine-pitch parts is awkward. It is
        # acceptable HERE and not there because this is a deliberate, one-off, last-resort
        # action -- tack a wire to it, or hold a fine probe -- not a reading taken during
        # normal bring-up. Stage 1 needed pads a meter could reach; this needs a way in
        # that exists at all.
        a1, a0 = divmod(ADC_ADDR[k], 2)
        (v3d if a1 else gnd).__iadd__(u[15])
        (v3d if a0 else gnd).__iadd__(u[16])
        sda, scl = i2c[ADC_I2C[k]]
        scl += u[17]
        sda += u[18]
        v3d += u[19]
        Net("ADC%d_GPIO1_NC" % tag).connect(u[20])
        sai_sd[k] += u[21]
        sai_sck += u[22]
        sai_fs += u[23]
        dreg += u[24]
        # SBAS993B Fig 165 less its four 100 nF: TI parallels 0.1 uF with each bulk part,
        # and here the bulk parts are 0402s already (10 uF 6.3 V X5R, 1 uF) -- the low-ESL
        # package the 100 nF is there to supply. Four fewer parts in each of five cells
        # that could not route with them. Refs keep TI's numbering (Cs2/4/7/9 are the gaps).
        for j, val, net in ((1, "1uF", v3a),            # AVDD
                            (3, "10uF", areg),          # AREG
                            (5, "1uF", vref),           # VREF
                            (6, "10uF", dreg),          # DREG
                            (8, "10uF", v3d)):          # IOVDD
            c = _c("Cs%d%d" % (tag, j), val, "U%d supply/reference bypass (SBAS993B Fig 165)"
                   % (14 + k))
            net += c[1]
            gnd += c[2]
    # ⚠ THE ANALOG BOTTLENECK IS THE Cs WALL, AND IT IS NOT THE MAPPING (2026-09-22).
    # Fifteen of the twenty TIA_OUT runs have no straight path, and which of them the
    # router drops changes every run -- 4 failures then 8, with nothing analog altered in
    # between. Measured with .ins/lane.py rather than argued about:
    #
    #   ch1  op-amp pin 1  @ x 74.81   3.15 mm  CLEAR
    #   ch2  pin 14 @ 79.76            9.28 mm  blocked by Ci<k>1
    #   ch3  pin 8  @ 79.76           13.20 mm  blocked by U<k> pad 4, its OWN op-amp
    #   ch4  pin 7  @ 74.81           10.48 mm  blocked by Cs<k>3
    #
    # The obvious suspect was this loop's assignment -- Ci marches west while the op-amp
    # outputs alternate between two x columns, so three runs in four cross each other. It
    # is not: ALL 24 permutations of (1A,1B,2A,2B) -> IN1..IN4 score 1 of 4 clear, and the
    # order built here is already the shortest of them at 36.12 mm. Scored in seconds off
    # the placed pads; do not spend a routing run on it again.
    #
    # What actually blocks them is a WALL of supply caps between the op-amp column and the
    # converter, and its gaps are the whole story. Per quad, by y:
    #
    #   Cs<k>5  ][  0.340   intra-cap, can never be a door
    #   Cs<k>5  ][  0.520   a 0.2 track needs 0.454 -- a door, barely
    #   Cs<k>3  ][  0.340
    #   Cs<k>3  ][  0.970   a door
    #   Cs<k>1  ][  0.340
    #   Cs<k>1
    #
    # Two doors, four runs, five quads. The wall's ENDS are open (nothing else sits in
    # x 71.9..74.6), so the rest go the long way round, which is what the router is doing
    # and why it is fragile rather than impossible.
    # THE LEVER IS THE CAPS' ORIENTATION. They stand tall: 1.58 mm in y, 0.62 in x. Turned
    # 90 they present 0.56 to the wall instead of 1.58 and give back ~3 mm of door across
    # the column -- at the cost of 1.58 mm in x, which has to come out of the 73.16..74.50
    # corridor. Not yet tried.
    # the couplings: quad q's section s -> converter q's input s+1
    for ch in range(20):
        i, side = ch // 2 + 1, "A" if ch % 2 == 0 else "B"
        # ⚠ REVERSED WITHIN THE CONVERTER (2026-09-24), and the permutation study above is
        # NOT the reason not to: that study is from the FIVE-QUAD era -- it cites op-amp
        # "pin 14", which a VSSOP-8 dual does not have -- and it scored each run for a CLEAR
        # STRAIGHT PATH past a wall of supply caps that no longer stands between the column
        # and the converter. The criterion now is different and it is ORDER, not length.
        #
        # The four runs of a converter group leave the op-amp column at four different y and
        # arrive at four caps on one row at four different x. They share the 4.00 mm lane
        # between their own two strings' slots, and a trace peeling north out of that lane
        # must be north of every trace still running east -- so a crossing-free assignment
        # needs the north-to-south source order to match the west-to-east sink order.
        # Sources run 1A,1B,2A,2B north to south; IN1..IN4's caps run EAST to west. The old
        # mapping therefore made all four cross, in the tightest region on the board.
        # One subtraction makes the two orders agree. Firmware channel order changes with it.
        k, s_in = ch // 4, 4 - ch % 4
        pos = Net("ADC%d_IN%dP" % (k + 1, s_in))
        ci = _c("Ci%d%d" % (k + 1, s_in), "10nF C0G", "string %d%s -> U%d IN%dP"
                % (i, side, 14 + k, s_in))
        tia_out[(i, side)] += ci[1]
        pos += ci[2], adcs[k][4 + 2 * s_in]
        # INxM: SINGLE-ENDED AC-COUPLED, TI's Figure 31 -- the pin grounded through its
        # own 10 nF. (A shared INxM node to MID was tried, 2026-09-21: the four INxM pins
        # alternate with the INxP pins at 0.5 mm pitch, so joining them needs a via per
        # pin inside a crowded cell, and it was the cells' worst net. MID's own noise is
        # a buffered reference's; rejecting it was never worth an unroutable cell.)
        neg = Net("ADC%d_IN%dM" % (k + 1, s_in))
        cm = _c("Cm%d%d" % (k + 1, s_in), "10nF C0G", "U%d IN%dM -> GND" % (14 + k, s_in))
        neg += cm[1], adcs[k][5 + 2 * s_in]
        gnd += cm[2]
    for ref, net, rail, what in (("R50", i2c[0][1], v3d, "I2C2 SCL"),
                                 ("R51", i2c[0][0], v3d, "I2C2 SDA")):
        r = _r(ref, "4k7" if rail is v3d else "100k", what)
        net += r[1]
        rail += r[2]

    # ── U6: the MCU ──────────────────────────────────────────────────────────
    mcu_pins = sorted(set(range(1, 177)))
    u6 = Part(name="STM32H743IIT6", ref_prefix="U", ref="U6", dest="NETLIST",
              tool="skidl", value="STM32H743IIT6",
              description="MCU, LQFP176, SAI TDM from 5 audio ADCs + OTG_HS ULPI (LCSC C89597)",
              footprint="Package_QFP:LQFP-176_24x24mm_P0.5mm",
              pins=[Pin(num=n, func=P) for n in mcu_pins])
    for n in MCU_VDD:
        v3d += u6[n]
    for n in MCU_VSS:
        gnd += u6[n]
    gnd += u6[PIN["VSSA"]]
    v3a += u6[PIN["VDDA"]], u6[PIN["VREF+"]]
    v3d += u6[PIN["VBAT"]], u6[PIN["VDD33_USB"]], u6[PIN["PDR_ON"]]

    # the converters' buses -- see THE CONVERTERS
    sai_sck += u6[PIN[SAI_CLK["SAI_SCK"]]]
    sai_fs += u6[PIN[SAI_CLK["SAI_FS"]]]
    for net, port in zip(sai_sd, SAI_SD):
        net += u6[PIN[port]]
    for (sda, scl), (p_sda, p_scl) in zip(i2c, I2C_BUS):
        sda += u6[PIN[p_sda]]
        scl += u6[PIN[p_scl]]

    # ULPI
    ulpi = {k: Net(k) for k in ULPI}
    for sig, port in ULPI.items():
        ulpi[sig] += u6[PIN[port]]

    # housekeeping
    osc_in, osc_out, nrst, boot0 = Net("OSC_IN"), Net("OSC_OUT"), Net("NRST"), Net("BOOT0")
    osc_in += u6[PIN["PH0"]]
    osc_out += u6[PIN["PH1"]]
    nrst += u6[PIN["NRST"]]
    boot0 += u6[PIN["BOOT0"]]
    # ⚠ THE BOARD HAD NO WAY TO RECEIVE ITS FIRST FIRMWARE. SWDIO and SWCLK were
    # connected to the MCU and to NOTHING ELSE -- single-node nets, so layout dropped
    # them as unplaceable and the DRC had nothing to complain about. BOM.md carried a
    # row reading "SWD programming pads (no component)", which is how the intent
    # survived while the implementation never existed.
    #
    # AND THERE WAS NO SECOND WAY IN. A blank STM32H743 cannot enumerate over this
    # board's USB, because the ULPI PHY needs firmware to bring it up and the ROM
    # bootloader's DFU lives on OTG_FS (PA11/PA12), which this board does not wire --
    # it uses OTG_HS through the PHY. AN2606's other bootloader interfaces (USART1/2/3,
    # I2C1/2/3, SPI1/2/4, FDCAN1) are not brought out either. With no SWD and no
    # bootloader pin, an assembled board is a brick: nothing about it is repairable in
    # firmware because no firmware can be put on it.
    #
    # Five pads fix it, and the set is chosen rather than default:
    #   SWDIO, SWCLK   the interface
    #   NRST           so a target can be attached UNDER RESET. This is the one that
    #                  looks optional and is not: PA13/PA14 are ordinary GPIO after
    #                  reset and firmware that reconfigures them takes SWD away, and
    #                  connect-under-reset is the only way back in.
    #   GND            the return the probe references
    #   +3V3D          target-voltage sense, so the programmer knows the board is
    #                  powered rather than driving a dead rail
    # BOOT0 is deliberately NOT brought out: it only helps if a ROM bootloader
    # interface exists, and none does. NRST is the recovery path here.
    #
    # Pads, not a connector: this is a factory operation, not a field one, so the
    # project's every-field-connection-is-a-connector rule does not apply. They carry
    # no paste and are excluded from the BOM and the pick-and-place by the footprint.
    swdio, swclk = Net("SWDIO"), Net("SWCLK")
    swdio += u6[PIN["PA13"]]
    swclk += u6[PIN["PA14"]]
    for tag, (ref, net) in enumerate((("TP1", swdio), ("TP2", swclk),
                                      ("TP3", nrst), ("TP4", gnd), ("TP5", v3d))):
        tp = Part(name="TestPoint", ref_prefix="TP", ref=ref, dest="NETLIST",
                  tool="skidl", value="SWD",
                  description="SWD pad -- %s; bare copper, no component"
                              % net.name,
                  footprint=FP["TP"], pins=[Pin(num=1, func=P)])
        net += tp[1]
    # ⚠ THE SECOND WAY IN WAS ALREADY ON THIS BOARD, AND FOR MONTHS NOBODY LOOKED IT UP.
    # The claim above -- "no USART/I2C/SPI/CAN bootloader pin is brought out" -- is FALSE,
    # and AN2606 Rev 61 Table 113 says so: on STM32H74xxx the ROM bootloader's I2C2
    # interface is SCL on PF1 and SDA on PF0, which is EXACTLY the pair this board already
    # runs to all five converters as its control bus. It is routed, it reaches every corner
    # of the digital half, and it has pull-ups.
    #   bootloader I2C2 slave address  0b1001110  (0x4E)
    #   TLV320ADC3140 x5               0b1001100  (0x4C)
    # Different addresses, so the converters cannot answer for the bootloader and the
    # bootloader cannot answer for them. Nothing has to be isolated, and the bus does not
    # have to be free: I2C is multi-slave by design and only one of them is addressed.
    #
    # WHAT THAT REPLACES. Two pads on USART1 (PA9/PA10) were designed, placed and searched
    # first, and they cannot be built: PA9/PA10 sit mid-row on the LQFP176's east face, the
    # maze router explores 65 cells out of the pad and finds every lane walled by the
    # escape fan, and the autorouter reached the same verdict four times in its own way.
    # I2C2 needs no escape at all, because the escape already happened.
    #
    # ⚠ AND THIS IS WHY BOOT0 IS BROUGHT OUT NOW (TP8). It was left off because it "only
    # helps if a ROM bootloader interface exists, and none does". A bootloader interface
    # does exist, so the premise is gone: BOOT0 held HIGH against R30's 10k at reset is
    # what selects the bootloader, and without it the I2C2 pads lead nowhere.
    led_gate = Net("LED_GATE")
    led_gate += u6[PIN["PB3"]]       # the emitter row's on/off, one GPIO for all ten
    # VCAP: the H7's internal core regulator needs its own capacitors, and leaving
    # them off is a part that boots intermittently rather than one that fails cleanly.
    vcap1, vcap2 = Net("VCAP1"), Net("VCAP2")
    vcap1 += u6[PIN["VCAP1"]]
    vcap2 += u6[PIN["VCAP2"]]
    # Every remaining pin is unconnected ON PURPOSE. The LQFP176 brings out far more
    # IO than this board uses; naming each one keeps ERC honest instead of silent.
    used = set(MCU_VDD) | set(MCU_VSS) | {
        PIN[k] for k in ("VSSA", "VDDA", "VREF+", "VBAT", "VDD33_USB", "PDR_ON",
                         "PH0", "PH1", "NRST", "BOOT0", "PA13", "PA14", "PB3",
                         "VCAP1", "VCAP2") + tuple(SAI_CLK.values()) + SAI_SD
        + tuple(p for bus in I2C_BUS for p in bus)}
    used |= {PIN[p] for p in ULPI.values()}
    for n in mcu_pins:
        if n not in used:
            Net("U6_NC_%d" % n).connect(u6[n])

    # ── U7: the ULPI PHY ─────────────────────────────────────────────
    # USB3300-EZK, QFN-32 5 x 5 (LCSC C108383; 17,431 in stock 2026-10-05). Chosen for
    # what it does NOT have: link power management. The USB334x family's high-speed chirp
    # erratum (Microchip DS80000645A, module 2) follows that feature -- behind the STM32's
    # USB core those parts enumerate at full speed only. ST's forum thread on the fault
    # lists the USB3300 and USB3320 as working and the USB3330 / 3340 / 3343 as failing,
    # and ST's own STM32H743I-EVAL (schematic MB1246 E03) carries the USB3320C. This one
    # over that one for the single supply and for stock (the USB3320C had 568).
    # Pins, Microchip DS00001783C figure 3-1 and table 3-1:
    #    1 GND      2 GND      3 CPEN     4 VBUS     5 ID       6 VDD3.3   7 DP    8 DM
    #    9 RESET   10 EXTVBUS 11 NXT     12 DIR     13 STP     14 CLKOUT  15 VDD1.8  16 VDD3.3
    #   17 DATA7   18 DATA6   19 DATA5   20 DATA4   21 DATA3   22 DATA2   23 DATA1   24 DATA0
    #   25 VDD3.3  26 VDD1.8  27 XO      28 XI      29 VDDA1.8 30 VDD3.3  31 REG_EN  32 RBIAS
    #   FLAG (exposed pad) GND -- "the main ground connection"
    # What the sheet asks for, and where it is done:
    #   * ONE 3.3 V supply (3.0 to 3.6 V) on pins 6, 16, 25 and 30, 0.1 uF at each.
    #   * REG_EN (31) high: the two 1.8 V regulators are the part's own. VDD1.8 is pins 15
    #     and 26 joined, 4.7 uF low-ESR at 26 and 0.1 uF at 15; VDDA1.8 (29) has its own
    #     4.7 uF beside 0.1 uF. The two 1.8 V rails must NOT be joined to each other while
    #     the regulators run (table 3-1), and neither may feed anything else (6.4.1).
    #   * RBIAS (32): 12.0 k 1 % to ground.
    #   * RESET (9) is ACTIVE HIGH with its own pull-down: grounded, as the sheet recommends.
    #   * VBUS (4) through a series resistor (figure 7-1). ID (5), CPEN (3) and EXTVBUS (10)
    #     are left open: a device needs none of them (table 3-1; EXTVBUS has a pull-down).
    #   * a 24 MHz reference: a crystal across XI / XO, or a clock into XI with XO open
    #     (6.3). This board clocks XI; the note at Y2 has why.
    u7 = Part(name="USB3300", ref_prefix="U", ref="U7", dest="NETLIST", tool="skidl",
              value="USB3300-EZK-TR",
              description="USB 2.0 HIGH-SPEED ULPI PHY, QFN-32 5x5 (LCSC C108383)",
              footprint="Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm",
              pins=[Pin(num=n, func=P) for n in range(1, 34)])
    usb_dp, usb_dm = Net("USB_DP"), Net("USB_DM")
    v1v8, v1v8a = Net("PHY_1V8"), Net("PHY_1V8A")
    rbias, phy_vbus = Net("PHY_RBIAS"), Net("PHY_VBUS")
    for pin, sig in ((11, "ULPI_NXT"), (12, "ULPI_DIR"), (13, "ULPI_STP"), (14, "ULPI_CK"),
                     (17, "ULPI_D7"), (18, "ULPI_D6"), (19, "ULPI_D5"), (20, "ULPI_D4"),
                     (21, "ULPI_D3"), (22, "ULPI_D2"), (23, "ULPI_D1"), (24, "ULPI_D0")):
        ulpi[sig] += u7[pin]
    gnd += u7[1], u7[2], u7[9], u7[33]    # GND, GND, RESET (active high), the flag
    phy_vbus += u7[4]
    usb_dp += u7[7]
    usb_dm += u7[8]
    v3d += u7[6], u7[16], u7[25], u7[30], u7[31]   # the four supply pins, and REG_EN
    v1v8 += u7[15], u7[26]
    v1v8a += u7[29]
    rbias += u7[32]
    phy_xi = Net("PHY_XI")
    phy_xi += u7[28]
    for _n in (3, 5, 10, 27):             # CPEN, ID, EXTVBUS, and XO (clocked on XI)
        Net("U7_NC_%d" % _n).connect(u7[_n])

    # ── U8/U9: the two 3V3 rails, and they are two on purpose ────────────────
    # U8 feeds the MCU and the PHY -- ~300 mA, which at 5 V in is 0.51 W and past
    # what a SOT-23-5 can shed, hence the SOT-223 tab. U9 feeds the ANALOG side and
    # is chosen for noise (40 uVrms) rather than current (~40 mA). Sharing one rail
    # would put the MCU's switching transients on the reference the TIAs measure
    # against, which is the one place on this board that cannot absorb them.
    # ⚠ AP2114H, NOT THE AMS1117 THAT STOOD HERE (2026-10-04, the regulator review). An
    # AMS1117's output capacitor is part of its compensation and its sheet asks for 22 uF
    # of solid TANTALUM: it wants the ESR. This board gives it 10 uF of ceramic and a
    # field of 100 nF ceramics, a few milliohms, which is outside every condition the part
    # is characterised under -- the classic way an 1117 ends up oscillating at a few
    # hundred kHz on a rail that looks fine on a meter. The AP2114H-3.3 is a CMOS 1 A
    # part in the same SOT-223 with the same three pins (1 GND, 2 VOUT and the tab,
    # 3 VIN: Diodes AP2114 "Pin Descriptions", column H), specified stable with 4.7 uF
    # CERAMIC, 6 V in, 450 mV dropout at 1 A against the 1.7 V available.
    u8 = Part(name="AP2114H-3.3", ref_prefix="U", ref="U8", dest="NETLIST",
              tool="skidl", value="AP2114H-3.3TRG1",
              description="3V3 DIGITAL LDO, SOT-223 tab, ceramic-stable (LCSC C150716)",
              footprint="Package_TO_SOT_SMD:SOT-223-3_TabPin2",
              # SOT-223-3_TabPin2: the TAB *is* pin 2, so there is no pad 4. That is
              # also the right electrical answer for this part -- its tab is VOUT, not
              # ground -- which is worth knowing before anyone pours a heatsink area
              # under it and assumes it is at 0 V. The 0.51 W this part burns is shed
              # into whatever copper that tab sits on, and that copper is at 3V3.
              pins=[Pin(num=1, name="GND", func=P), Pin(num=2, name="VO/TAB", func=P),
                    Pin(num=3, name="VI", func=P)])
    gnd += u8[1]
    v3d += u8[2]
    v5_pre += u8[3]           # BUCK side: this LDO feeds the MCU and PHY
    # ⚠ TPS7A2033, NOT THE SPX3819 THAT STOOD HERE (2026-10-04, quality M15). The SPX3819's
    # sheet gives no ceramic-capacitor stability at all: its application section asks for
    # "a high quality 2.2 uF aluminum electrolytic" or "a 1 uF tantalum" and says bench
    # testing is the way to choose. It is the MIC5205 class of PNP regulator, compensated
    # by its output capacitor's ESR -- and this rail is 18 uF of ceramic and nothing else.
    # Same fault as the AMS1117 that U8 replaced, found a day later.
    # TPS7A20 (TI SBVS338, DBV): stable with 1 to 200 uF of ceramic at up to 100 mohm,
    # 300 mA against this rail's 166 mA worst case, 6.7 uVrms 10 Hz - 100 kHz at 100 mA
    # (the SPX3819 managed 40 with its bypass capacitor), 6.0 V maximum input against the
    # 5 V it is fed. Same package, same pins: 1 IN, 2 GND, 3 EN, 4 N/C, 5 OUT.
    # 0.28 W at 166 mA and 187 C/W: 53 C of rise.
    u9 = Part(name="TPS7A20", ref_prefix="U", ref="U9", dest="NETLIST", tool="skidl",
              value="TPS7A2033PDBVR",
              description="3V3 ANALOG LDO, 7 uVrms, ceramic-stable (LCSC C2862740). Chosen "
                          "for stability on ceramic output capacitors and for noise: do "
                          "not substitute an ESR-compensated part (SPX3819, MIC5205, 1117)",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=n, func=P) for n in range(1, 6)])
    # TPS7A20 DBV: 1 IN, 2 GND, 3 EN, 4 N/C, 5 OUT
    v5 += u9[1], u9[3]
    gnd += u9[2]
    # Pin 4 has no internal connection on this part. (On the SPX3819 it was the noise
    # bypass, with C127 on it; C127 went with that part.)
    Net("U9_NC_4").connect(u9[4])
    v3a += u9[5]

    # ── U10: USB ESD, at the connector ───────────────────────────────────────
    u10 = Part(name="USBLC6-2SC6", ref_prefix="U", ref="U10", dest="NETLIST",
               tool="skidl", value="USBLC6-2SC6",
               description="USB data-line ESD array (LCSC C7519) -- ⚠ SOT-23-6, "
               "not the SOT-563 the CAD models",
               footprint="Package_TO_SOT_SMD:SOT-23-6",
               pins=[Pin(num=n, func=P) for n in range(1, 7)])
    # 1 IO1, 2 GND, 3 IO2, 4 IO2, 5 VBUS, 6 IO1
    usb_dp += u10[1], u10[6]
    gnd += u10[2]
    usb_dm += u10[3], u10[4]
    vbus = Net("VBUS")
    vbus += u10[5]

    # ── U11: the mid-rail buffer the twenty TIAs share ───────────────────────
    u11 = Part(name="TLV9061", ref_prefix="U", ref="U11", dest="NETLIST", tool="skidl",
               value="TLV9061IDBVR",
               # ⚠ DBV (SOT-23-5), NOT DCK (SC70). It was ordered as the DCK part on a
               # SOT-23-5 footprint wired with the SOT-23 pinout, and TI's datasheet
               # (SBOS839, Table 5-1) gives the two packages DIFFERENT pinouts: SC70
               # is 1 IN+, 3 IN-, 4 OUT, where SOT-23 is 1 OUT, 3 IN+, 4 IN-. The old
               # note called the mismatch "envelope is oversized, safe" -- true of the
               # envelope, not of the pins.
               description="single op-amp, TIA mid-rail reference buffer "
               "(LCSC C398358, SOT-23-5 / DBV)",
               footprint="Package_TO_SOT_SMD:SOT-23-5",
               pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                     Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                     Pin(num=5, name="V+", func=P)])
    mid_raw = Net("MID_RAW")
    # ⚠ THE FOLLOWER DOES NOT DRIVE C133 DIRECTLY (2026-10-04, quality M22). It did: output
    # and inverting input both on MID, and MID carries a 10 uF bypass. TI's sheet (SBOS839
    # p.1 and fig. 33) gives this amplifier 100 pF of capacitive load and an open-loop
    # output impedance of about 100 ohm, resistive. 100 ohm into 10 uF is a second pole at
    # 160 Hz under a 10 MHz gain-bandwidth: the loop crosses unity near 40 kHz with almost
    # no phase left -- a reference ringing or oscillating beside the 48 kHz carrier, on
    # the one node all twenty channels share.
    # R42 isolates it, and the feedback is taken BEFORE the resistor: above a few hundred
    # hertz the amplifier sees 100 ohm, not a capacitor, so its loop is the unloaded one
    # at half the gain. C133 still does the bypassing (0.33 ohm at 48 kHz); the buffer
    # sets the DC level through 100 ohm, and the only DC on MID is the photodiodes' return,
    # under 0.1 mA for all twenty: 8 mV on a reference the converters are AC-coupled from.
    mid_buf = Net("MID_BUF")
    mid_buf += u11[1], u11[4]   # unity-gain follower, closed at its own pin
    r42 = _r("R42", "100R", "MID buffer isolation -- between U11's output and the 10 uF "
             "on MID; the follower's feedback is taken on U11's side of it")
    mid_buf += r42[1]
    mid += r42[2]
    gnd += u11[2]
    mid_raw += u11[3]
    v3a += u11[5]              # same rail as the quads it references -- see above

    # ── U13 / L1: the board's ONLY switcher, at the far end on purpose ───────
    # 24 V arrives at J2, so one switching stage is unavoidable (24->3V3 linearly is
    # 6.2 W and no package here sheds that). It sits at the -Y tail, as far from the
    # photodiode array as this board has room for, with a ~10 mm input path.
    # ⚠ AND ITS SWITCHING FREQUENCY IS A REAL SPEC, not a detail: this board samples
    # at 48 kHz and a switcher near a sub-multiple of that aliases straight into the
    # audio band, where subtraction cannot remove it because it is synchronous.
    # ── THE POWER BUDGET, ITEMISED -- because nothing added it up until 2026-09-17 ──
    # The board had a 600 mA buck and three scattered assertions about its load (~85 mA
    # at 24 V here, "nearer 0.35 A" there, "the MCU draws 200-300 mA" in BOM.md), none
    # of them derived and none of them agreeing. A 600 mA part deserves a sum.
    #
    # Every figure below is from the part's own datasheet, at the operating point this
    # board actually uses.
    #
    #   +3V3A  (U9, TPS7A2033 since 2026-10-04, off the QUIET side of FB1)
    #     5x TLV9064 quad          538 uA/amp typ, 750 max  ->  10.8 / 15.0 mA
    #     U11 TLV9061 single                                ->   0.54 / 0.75
    #     R34/R35 mid-rail divider 3.3 V / 10.09 k          ->   0.33 / 0.33
    #     5x TLV320ADC3140 AVDD (2026-09-21)   21.3 mA each, 4 ch at 48 kHz, PLL on
    #       (SBAS993B 7.5; 19.7 at 16 kHz, so it scales weakly) -- NO figure at 192 kHz;
    #       ~26 each assumed                                 ->  ~130 / ~150
    #                                                   subtotal ~142 / ~166 mA
    #     ⚠ THE CONVERTERS MULTIPLY THIS RAIL TENFOLD. U9 (then an SPX3819, 500 mA; now a 300 mA TPS7A20) carries it,
    #       but it burns (5 - 3.3) x 0.14 = 0.24 W in a SOT-23-5 -- ~45 C of rise -- and
    #       the buck's worst case below grows by the same ~150 mA. MEASURE AVDD current
    #       at 192 kHz on first boards before trusting either margin.
    #
    #   +3V3D  (U8, AMS1117, off the BUCK side)
    #     STM32H743 400 MHz VOS1, all peripherals enabled (DS12110 T30)
    #                              165 typ / 220 max @25 C / 400 max @85 C
    #     USB3300, HS transmit (DS00001783C T5-1), 3.3 V and the 1.8 V it makes
    #                               62 typ /  73 max
    #     Y2, the 24 MHz oscillator (its sheet gives only 10 max)   5 / 10 / 10
    #     R31 / R37 RBIAS / R38                             ->   0.8
    #                                            subtotal  212 / 282 / 462 mA
    #
    #   +5V / V5_PRE  (U13, an LMR33630 since 2026-09-22 -- 3 A; this budget was the TPS560430's 600 mA)
    #     ten emitters at 21.1 mA, pulsed -- 105 mA average, 211 mA while on
    #       ⚠ THE 50% DUTY IS AN INFERENCE ABOUT FIRMWARE THAT DOES NOT EXIST YET, not
    #       a measurement: the emitters square-wave at 48 kHz, a quarter of the
    #       converters' 192 kHz, for the lock-in -- a square wave is 50% by nature.
    #       Firmware could choose a shorter pulse. IT DOES NOT CHANGE THE CONCLUSION --
    #       at 100% duty the emitters are 211 mA continuous and the typical total
    #       becomes 430 mA, still 72% of the buck -- so the budget holds whatever the
    #       firmware picks. Only the "324 mA typical" headline moves.
    #     U8 input ~= its output                             212 / 282 / 462
    #     U9 input ~= its output                              12 /  16 /  16
    #   + THE CONVERTERS' ~130 mA (2026-09-21, via U9 above): typical ~454 mA, worst ~629 mA
    #     -- 105 % of the 600 mA TPS560430 this budget was written against. RESOLVED
    #     2026-09-22 (user): U13 is now the 3 A LMR33630, so the same worst case is 21 %.
    #     The percentages below are the TPS560430's and are kept as history.
    #                              average          324 mA   54 % of the buck
    #                              emitters on      430 mA   72 %
    #                              + max parts @25  499 mA   83 %
    #                              + max parts @85  679 mA   ⚠ OVER 600
    #
    # ⚠ THE LAST ROW IS THE ONE TO ARGUE WITH, AND IT IS NOT A REASON TO CHANGE THE
    # PART. 400 mA is ST's characterisation MAXIMUM at TJ = 85 C with every peripheral
    # enabled -- not a typical part, and not this firmware, which runs an ADC, a timer
    # and a USB controller and leaves the LTDC, JPEG codec, Ethernet, FMC, SDMMC and the
    # rest of a 176-pin part's peripheral set switched off. The honest statement is that
    # the buck has comfortable margin at the real operating point and no margin against
    # a worst-case datasheet corner this board will not visit. What it DOES mean is that
    # enabling peripherals is a power decision on this board and not a free one.
    #
    # ⚠ AND IT KILLS THE SNR LEVER RECORDED AT THE BALLASTS. Raising emitter drive to
    # the IR17-21C's 65 mA rating is 650 mA of emitters ALONE against a 600 mA buck,
    # before the MCU. That lever needs a bigger buck, not a smaller resistor -- which is
    # exactly what the ballast note said to check, now checked.
    #
    # C162's droop over one emitter pulse, which the ballast note also asked for:
    # 211 mA x 5.2 us / 22 uF = 50 mV on a rail feeding two LDOs with volts of headroom.
    # Not a constraint.
    #
    # 24 V input: 324 mA x 5 V / 0.85 = 1.9 W -> 79 mA, which is where the "~85 mA,
    # ~2 W" recorded elsewhere came from. That one was right.
    sw, fb = Net("SW"), Net("FB")
    # ⚠ TI TPS560430XF (SLVSE22B). Chosen against the requirement recorded on the CAD's
    # MPN line: SYNCHRONOUS (it is), >=30 V absolute max (38 V), and a switching
    # frequency away from the sample rate and its low harmonics (1.1 MHz). The F suffix
    # is FORCED PWM and that is not a detail: the PFM variants skip pulses at light
    # load, which puts the switching energy at variable, low frequencies -- some of them
    # audio -- where a fixed 1.1 MHz stays put and filterable. 1.1 MHz rather than the
    # 2.1 MHz part because it is TI's own 5 V reference design and doubles the
    # minimum-on-time margin at 24 V in (189 ns against the 60 ns floor).
    # ⚠ NOW AN LMR33630 (user, 2026-09-22) -- the TPS560430's 600 mA was 105 % used in
    # the worst case once the five converters landed on this board. 3 A, 36 V abs max, the
    # motor controller's family. THE VARIANT IS THE POINT:
    #   * "B" = 1.4 MHz, CHOSEN FOR HEAT (2026-10-05). The loss is read off TI's 24 V
    #     curves for this package, 5 V out, and it is mostly switching loss, there at any
    #     load:
    #                        2.1 MHz (fig. 9-17)        1.4 MHz (fig. 9-15)
    #       0.46 A typical   69 %   1.03 W   107 C      75 %   0.77 W    91 C
    #       1.08 A worst     80.5 % 1.31 W   124 C      86 %   0.88 W    98 C
    #     Junction at 45 C in the endplate cavity beside the motors, through an ESTIMATED
    #     60 C/W: TI's figure 9-4 for this package is 50 to 63 C/W on a four-layer board
    #     with 2 oz outer and 1 oz inner copper, this board is 1 oz and 0.5 oz, and the
    #     package has no pad -- the heat leaves by its pins. The limit is 125 C. The
    #     2.1 MHz part that was here ("C") was at it; this one has 27 C in hand. (The
    #     curves include TI's inductor, so the IC's own share is a little less.)
    #   * NOT PULSE-SKIPPING IN SERVICE. No forced-PWM LMR33630 is stocked, and a
    #     pulse-skipping buck at light load puts its switching energy at variable, low --
    #     sometimes audio -- frequencies beside twenty TIAs; that is why the TPS560430 was
    #     the FPWM part. At 1.4 MHz with 4.7 uH the ripple is 0.60 A pk-pk, so the part
    #     holds its frequency above 0.30 A. Running, this board draws 0.46 A typical and
    #     0.35 A in the half-cycle the emitters are off: above it, by less than the 2.1 MHz
    #     part's margin. Below 0.30 A it is in reset or asleep and nobody is listening.
    #     6.8 uH would put the boundary back at 0.21 A, and the 4 x 4 part of that value
    #     saturates at 3.0 A, under the IC's limit (see L1): not taken. (TI's 5 V /
    #     1.4 MHz example uses 2.2 uH -- sized for 3 A; at this board's load its 1.3 A of
    #     ripple would drop the part into PFM.)
    #   * "RNX" = VQFN-HR 2 x 3 mm, NOT the motor controller's HSOIC-8: the buck row sits
    #     against the tail's 0.11 mm length margin and the SOIC grows it 0.86 mm.
    # Pinout, SNVSB08 Table 6-1 (VQFN column): 1 PGND, 2 VIN, 3 NC, 4 BOOT, 5 VCC, 6 AGND,
    # 7 FB, 8 PG, 9 EN, 10 VIN, 11 PGND, 12 SW. TI: "connect the SW pin to NC on the PCB"
    # (it simplifies the CBOOT loop), so pin 3 joins SW. PG is unused and left open.
    # Footprint: elec/footprints/Steel.pretty, drawn from TI's RNX0012B/C land (identical).
    # ⚠ 260 in stock 2026-10-05 (C2071384), SHARED with the three LED supplies: four an
    # instrument. The 2.1 MHz LMR33630CRNXR (C2071783, 3,453) drops onto the same land and
    # the same parts if this one runs out, at the temperatures in the table above.
    u13 = Part(name="LMR33630BRNX", ref_prefix="U", ref="U13", dest="NETLIST",
               tool="skidl", value="LMR33630BRNXR",
               description="24V -> 5V synchronous buck, 1.4 MHz, 3 A (LCSC C2071384)",
               footprint="Steel:Texas_RNX0012_VQFN-HR-12_2x3mm_P0.5mm",
               pins=[Pin(num=n, func=P) for n in range(1, 13)])
    v24 = Net("+24V")
    v24.drive = Pin.drives.POWER
    # the connector side of R44 -- see J2
    v24_in = Net("V24_IN")
    boot, vcc_buck = Net("BOOT"), Net("BUCK_VCC")
    pgnd += u13[1], u13[11], u13[6]
    v24 += u13[2], u13[10]
    sw += u13[3], u13[12]
    boot += u13[4]
    vcc_buck += u13[5]
    fb += u13[7]
    # ⚠ POWER-GOOD STAYS A NO-CONNECT, AND THIS TIME THE REASON IS MEASURED. A pad on it
    # was designed, sited and mazed: the site is fine (3.032 mm of headroom, 5.9 mm away),
    # and the PIN CANNOT BE ESCAPED. Pad 8 sits mid-row on the VQFN-HR with the buck's own
    # +24V pads 9 and 10 either side of the only way out, and C165's +24V land beyond them.
    # Mazed at 0.05 mm over the finished board, on every layer, with a via hop allowed:
    #   0.24, 0.20, 0.18 mm track   NO PATH AT ALL (326, 495, 669 cells explored)
    #   0.16 mm                     a path, whose centreline comes 0.159 mm from +24V
    #   0.14 mm                     a path, 0.135 mm
    # A centreline at 0.159 mm with a 0.16 mm track is 0.079 mm of copper-to-copper, and
    # DRC confirmed it: 0.0900 mm against the 0.127 rule, seven violations. For a
    # 0.127 mm track the centreline would have to clear by 0.191 mm and the widest corridor
    # out of that pin is 0.159. There is no width that fits, so this is a PLACEMENT or a
    # part-choice question, not a routing one -- and a debug pad does not get to move the
    # buck. (A via-in-pad is no better: a 0.6 mm annulus does not fit between 0.5 mm pitch
    # pads either.)
    Net("BUCK_PG_NC").connect(u13[8])
    # EN tied to VIN, which the datasheet allows ("Can be connected directly to VIN; Do
    # not float") -- the same choice the TPS560430 had.
    v24 += u13[9]
    # ⚠ THE VALUE IS THE PART NUMBER, for the same reason the crystals' are: "15uH"
    # does not specify an inductor. Saturation current, RMS current, DCR and whether the
    # thing is shielded at all vary by 3x across 4x4 parts that share an inductance, and
    # every one of those four decides whether this supply works.
    #
    # WHY 15 uH AND NOT THE 18 uH THAT USED TO BE HERE. The old note read "15.8 uH min
    # (eq. 9, KIND 0.4)" and then rounded UP to the next E-series value, which is
    # backwards: KIND is a CHOICE inside TI's own 20-60% band, not a constant. 15 uH is
    # KIND = 0.42 -- squarely inside it -- and buys the thing that was actually binding.
    #
    # WHAT WAS BINDING IS SATURATION, AND THE BAR IS THE IC'S CURRENT LIMIT, NOT THE
    # LOAD. SLVSE22B section 9.2.2.4 says it outright: "the inductor current rating
    # should be a bit higher than current limit". IHS_LIMIT is 0.8 / 1.1 / 1.4 A
    # (min/typ/max), so the part has to survive 1.4 A, not the 0.72 A peak this board
    # draws at full load. Across Sunlord's 4x4 range at 22 uH the best Isat available is
    # 1.05 A (SWPA4020S220MT) -- under the typical limit, never mind the maximum. Drop
    # to 15 uH in the same package and Isat is 1.35 A worst case, DCR falls from 0.455
    # to 0.299 ohm max, and Irms rises from 0.62 to 0.77 A. Lower inductance is the
    # cheaper axis here, and TI says as much two paragraphs later.
    #
    # Ripple at 24 V in: 5 x 19 / (24 x 15u x 1.1M) = 0.24 A pk-pk, peak 0.72 A at the
    # 600 mA the part can deliver -- and this board's measured draw is nearer 0.35 A.
    # At the -20% tolerance corner (12 uH) ripple is 0.30 A and peak 0.75 A. 1.35 A of
    # Isat covers all of it with the IC's limit still the first thing to act.
    #
    # SHIELDED is not optional: an unshielded inductor switching at 1.1 MHz sits on the
    # same board as twenty transimpedance amplifiers looking for nanoamps.
    # 8,816 in stock 2026-09-17. Footprint is Sunlord's own recommended land (1.1 x 3.7
    # pads on a 3.0 mm pitch); the SRN4018 land that used to be here was a Bourns part
    # that LCSC does not stock in any usable value.
    # (The TPS560430-era sizing above is history.) With the LMR33630B at 1.4 MHz the pick
    # is 4.7 uH -- see U13.
    # ⚠ THE PART IS CHOSEN FOR SATURATION AT THE IC'S LIMIT, NOT AT THE LOAD (2026-10-05).
    # TI SNVSAN3F 9.2.2.4: "the inductor saturation current must not be less than the
    # device low-side current limit", 3.5 A typical (2.9 to 4.1). The SWPA4030S4R7MT that
    # was here is 2.9 A guaranteed / 3.2 typical: fine at this board's 1.3 A peak and
    # under the limit in a short, where a ferrite part that has let go leaves the switch
    # with almost no inductance to limit against. Sunlord WPN4020H4R7MT (its sheet, rev
    # 2023/06): 4.00 A rated / 4.90 typical for a 30 % drop, a metal-composite core that
    # gives way gradually, closed magnetic circuit, 40 V, 108 mohm max, 4.0 x 4.0 x 2.0 on
    # the SAME recommended land (1.1 x 3.7 on a 3.0 pitch). That covers the typical limit
    # with 0.5 A in hand and is 0.1 A short only with the IC at its extreme and the part at
    # its floor. The 3.3 uH of the family (4.70 A) would cover that too and was not taken:
    # its 0.86 A of ripple at 1.4 MHz puts the fixed-frequency boundary at 0.43 A, on top of
    # this board's typical load, and a buck that skips pulses beside twenty TIAs is the
    # worse fault.
    l1 = Part(name="L", ref_prefix="L", ref="L1", dest="NETLIST", tool="skidl",
              value="WPN4020H4R7MT",
              description="buck output inductor, 4.7 uH closed-circuit metal composite, "
              "Isat 4.0 A, DCR 108 mohm, 4.0 x 4.0 x 2.0 (LCSC C98363)",
              footprint="Inductor_SMD:L_Sunlord_SWPA4030S",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw += l1[1]
    v5_pre += l1[2]
    # ⚠ THE VALUE IS THE PART NUMBER for the third time on this board, and here the
    # reason is a naming trap rather than a spec spread: "600" in a Murata or Sunlord
    # bead part number means 60 ohm, not 600 (two digits and a decade multiplier), so
    # "600R@100MHz" on a BOM line invites exactly the wrong part -- same package, same
    # footprint, a tenth of the filtering, and nothing downstream that could notice.
    fb1 = Part(name="FerriteBead", ref_prefix="FB", ref="FB1", dest="NETLIST",
               # ⚠ BLM18KG601SN1D, NOT THE GZ1608D601TF THAT STOOD HERE (2026-10-04). That
               # part is rated 200 mA and this bead carries the whole analog rail: 142 mA
               # typical, 166 at the worst case, and the converters' draw at 192 kHz is an
               # assumption. A bead's impedance collapses as its DC current nears the
               # rating, so at 83 % it was not doing the job it is drawn for. Same 0603,
               # 600 ohm at 100 MHz, 1.3 A, 150 mohm (25 mV dropped instead of 75).
               tool="skidl", value="BLM18KG601SN1D",
               # ⚠ WHAT IS ON WHICH SIDE WAS THE WHOLE POINT AND IT WAS WRONG. The bead
               # splits a noisy 5 V from a quiet one, and the TEN EMITTERS -- pulsed at
               # 48 kHz, synchronously with sampling, the one noise source ambient
               # subtraction cannot remove -- were hanging on the QUIET side, together
               # with the digital LDO that feeds the MCU and the PHY. The bead was
               # keeping the buck's ripple out of a node that the board's own worst
               # aggressor was already sitting on.
               # Buck side now: the emitter row, and the digital LDO. Quiet side: the
               # analog LDO alone, which is the only thing the analog front end is fed
               # from now that the quads run on +3V3A.
               description="5 V rail split: buck + emitters + digital LDO on one side, "
               "the analog LDO on the other",
               footprint="Inductor_SMD:L_0603_1608Metric",
               pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v5_pre += fb1[1]
    v5 += fb1[2]
    # ⚠ THE BEAD HAS A DAMPER (2026-10-04, quality M17). A bead into ceramics is a resonant
    # filter: about 1.5 uH (the BLM18KG601's low-frequency inductance) against the 1.3 uF
    # on +5V (C140 1 uF + C141-C143) peaks near 115 kHz, and with 0.15 ohm of bead and
    # milliohms of capacitor to lose it in, by a factor of five or more. U9's input is a
    # constant-current load and damps nothing. The emitter row pulls a 48 kHz square wave
    # from V5_PRE, whose third harmonic is 144 kHz: the filter that is there to keep the
    # row's current off the analog rail was amplifying its strongest harmonic.
    # R43 + C134, 1 ohm in series with 10 uF across the rail: the capacitor is several
    # times the 1.3 uF it damps and the resistor is the filter's characteristic
    # impedance, sqrt(1.5 uH / 1.3 uF) = 1.07 ohm, which flattens the peak to about 1.
    damp = Net("V5_DAMP")
    r43 = _r("R43", "1R", "FB1 damper -- in series with C134 across +5V; the value is "
             "the bead filter's characteristic impedance, do not fit 0 ohm")
    c134 = _c("C134", "10uF", "FB1 damper capacitor, behind R43",
              "Capacitor_SMD:C_0805_2012Metric")
    v5 += r43[1]
    damp += r43[2], c134[1]
    gnd += c134[2]
    # ⚠ THE BRING-UP PADS, AND THIS TIME THEY ARE PLACED AFTER ROUTING. Like TP1-5 they
    # carry no paste and are excluded from the BOM and the pick-and-place by the footprint.
    # WHY THEY ARE NEEDED. The diagnostic chain is strictly serial -- power, MCU, I2C,
    # framing, analog, emitters, USB -- and stage ONE had no observability at all: no rail
    # is reachable by a meter without probing a 0402 beside 0.5 mm-pitch parts, and with
    # the MCU's own ADCs dropped and all 20 converter inputs used by photodiodes, a RUNNING
    # MCU cannot read one of its own supplies. Three pads fix that, and BOOT0 is what
    # selects the ROM bootloader when SWD will not attach.
    # ⚠ WHY THE FIRST FOUR ATTEMPTS FAILED, AND WHAT CHANGED. Handed to the ROUTER these
    # same pads cost a net every time -- 2 unconnected, then 2, then 4, then 2, always at
    # the USB PHY, and +3V3A failed even in the run where its own pad had been REMOVED.
    # That is not a placement problem and no re-siting fixes it: the south is re-solved
    # from scratch every run and only just succeeds, so the cost is the PERTURBATION, not
    # the area. These pads are now listed in post_route_refs and placed by route.py's
    # repair block, after the router has finished, on copper their own net already has --
    # which is the same timing argument that closed SAI_FS and +3V3A before them.
    # ⚠ NO PAD ON MID. It is the reference all twenty TIAs sit on, so anything coupled into
    # it appears on EVERY channel at once and calibration cannot separate it from signal.
    # Firmware already reads it as the common rest level of all 20 channels.
    # ⚠ TP6/TP7 ARE 1.0 mm, NOT 1.5, and the reason is measured rather than tidy: at D1.5
    # the I2C2 pair has 26 legal sites on the whole board and the best one in the digital
    # half clears by 0.074 mm, while at D1.0 the same search returns sites at 1.696 and
    # 0.743 mm. A millimetre is still four times a 0402's pad and a probe tip does not
    # care; half a fab tolerance does.
    for _ref, _net, _why in (("TP6", i2c[0][0], "I2C2 SDA -- the ROM bootloader's bus"),
                             ("TP7", i2c[0][1], "I2C2 SCL -- the ROM bootloader's bus"),
                             ("TP8", boot0, "BOOT0 -- hold HIGH at reset for the bootloader"),
                             ("TP9", v24_in, "24 V as it arrives at J2, ahead of R44"),
                             ("TP10", v5, "+5V rail -- the buck's output"),
                             ("TP11", v3a, "+3V3A rail -- the quiet LDO")):
        _tp = Part(name="TestPoint", ref_prefix="TP", ref=_ref, dest="NETLIST",
                   tool="skidl", value="BRINGUP",
                   description="bring-up pad -- %s; bare copper, no component" % _why,
                   footprint=FP["TP_SMALL" if _ref in ("TP6", "TP7") else "TP"],
                   pins=[Pin(num=1, func=P)])
        _net += _tp[1]

    # ── Q1: the emitter row's low-side switch ────────────────────────────────
    # All ten emitters share one gate. They are pulsed, not held on: pulsing lets the
    # firmware take an AMBIENT-ONLY sample with the LEDs off and subtract it, which is
    # the whole answer to an up-firing detector looking at the sky. (Subtraction fixes
    # flicker and offset; it does not fix saturation, which is the cover's job.)
    q1 = Part(name="Q_NMOS", ref_prefix="Q", ref="Q1", dest="NETLIST", tool="skidl",
              value="AO3400A", description="LED row driver (LCSC C20917)",
              footprint="Package_TO_SOT_SMD:SOT-23",
              pins=[Pin(num=1, name="G", func=P), Pin(num=2, name="S", func=P),
                    Pin(num=3, name="D", func=P)])
    pgnd += q1[2]
    led_row += q1[3]

    # ── crystals ─────────────────────────────────────────────────────────────
    # ⚠ THE VALUE IS THE PART NUMBER, BECAUSE "25MHz" DOES NOT SPECIFY A CRYSTAL.
    # Load capacitance and ESR are what decide whether an oscillator starts and whether
    # it runs on frequency, and they vary across parts that share a frequency and a
    # package: the 3225 26 MHz parts at JLCPCB run from CL 7.5 pF to 20 pF and ESR 30 to
    # 80 ohm. A BOM line reading "25MHz" lets the fab pick any of them.
    y1 = Part(name="Crystal", ref_prefix="Y", ref="Y1", dest="NETLIST", tool="skidl",
              # ⚠ CL 10 pF, NOT THE 20 pF PART THAT WAS HERE (2026-10-04). The H7's HSE is
              # specified by the largest critical transconductance it will start:
              # Gm_crit_max 1.5 mA/V (DS12110, HSE oscillator characteristics), where
              # gm_crit = 4 x ESR x (2 pi f)^2 x (C0 + CL)^2. TX322525M4LBDD2T (20 pF,
              # 30 ohm, C0 up to 5 pF) is 1.37 mA/V at a typical C0 and 1.85 at its limits:
              # past the MCU's guarantee at worst case and inside it by 9 % otherwise.
              # TAXM25M4RDBCCT2T (10 pF, 30 ohm max, C0 3 pF max: its
              # own sheet) is 0.50 at its limits. ST's own H7 boards fit 8 pF parts for the
              # same reason.
              value="TAXM25M4RDBCCT2T",
              description="MCU HSE 25 MHz, CL 10 pF, ESR <= 30 ohm (LCSC C403946)",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=n, func=P) for n in range(1, 5)])
    osc_in += y1[1]
    osc_out += y1[3]
    gnd += y1[2], y1[4]
    # Y2 is a 24 MHz CLOCK OSCILLATOR, not a crystal. 24 MHz is the only reference the
    # USB3300 takes, and its sheet allows either: "the clock should be connected to the
    # XI input and the XO pin left floating ... XI is designed to be driven with a 0 to
    # 3.3 volt signal" (DS00001783C 6.3).
    # ⚠ WHY NOT A CRYSTAL: the PHY's table 5-8 asks for a crystal rated for a drive level
    # of 0.5 mW or more, and the 3225 crystals JLCPCB stocks at 24 MHz / 20 pF / 30 ohm
    # are specified at 0.1 mW (Yajingxin TAXM24M4RLBCDT2T, its own sheet). Whether this
    # PHY really puts more than that into the quartz cannot be read off either sheet, and
    # an over-driven crystal fails by ageing, months after the board passed bring-up. An
    # oscillator has no such number, and no load capacitors to trim on the first board.
    # JSCJ CJO05 (its sheet, rev 1.0): 3.3 V +-10 %, 10 mA max, +-20 ppm all-in against
    # the +-500 the PHY's note 5-1 allows, 1 ps rms phase jitter (12 kHz to 20 MHz), 8 ns
    # edges into 15 pF, up in 5 ms. Pin 1 is its enable: high or open runs, so it is tied
    # to the supply rather than left to float.
    y2 = Part(name="Oscillator", ref_prefix="Y", ref="Y2", dest="NETLIST", tool="skidl",
              value="CJO05-240003320B30",
              description="PHY reference, 24 MHz 3.3 V CMOS oscillator (LCSC C712738)",
              footprint="Oscillator:Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm",
              pins=[Pin(num=1, name="EN", func=P), Pin(num=2, name="GND", func=P),
                    Pin(num=3, name="OUT", func=P), Pin(num=4, name="VDD", func=P)])
    v3d += y2[4], y2[1]
    gnd += y2[2]
    phy_xi += y2[3]
    c125 = _c("C125", "100nF", "24 MHz oscillator supply bypass -- Y2 pin 4", _C_0402)
    v3d += c125[1]
    gnd += c125[2]

    # ── J1: USB-C, the one cable that carries everything out ─────────────────
    # 10 channels of audio, MIDI from the on-chip pitch detection, and DFU for
    # firmware, all on this. It goes to the OUTPUT PANEL's hub downstream port
    # ~100 mm away, not to the Pi at the keyhead -- see the header.
    j1 = Part(name="USB_C_Receptacle", ref_prefix="J", ref="J1", dest="NETLIST",
              tool="skidl", value="TYPE-C-31-M-12",
              description="USB-C: 10ch audio + MIDI + DFU (LCSC C165948)",
              footprint="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
              pins=[Pin(num=n, func=P) for n in
                    ("A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12",
                     "B1", "B4", "B5", "B6", "B7", "B8", "B9", "B12")]
                   + [Pin(num="SH", func=P)])
    gnd += j1["A1"], j1["A12"], j1["B1"], j1["B12"], j1["SH"]
    # ⚠ VBUS IS NOT USED AND NOT DEAD-ENDED. This board is SELF-POWERED off the 24 V
    # trunk, so it takes no current from the host -- but it is a DEVICE, and a device
    # that cannot see VBUS cannot tell whether the host is there. The pin goes to the
    # ESD array's VBUS reference and, through R39, the PHY's VBUS comparator:
    # sensed, not consumed.
    vbus += j1["A4"], j1["B4"], j1["A9"], j1["B9"]
    usb_dp += j1["A6"], j1["B6"]
    usb_dm += j1["A7"], j1["B7"]

    # ── J2: 24 V in, on the instrument's standard 4-way ──────────────────────
    # ⚠ TWO WAYS, NOT FOUR (user, 2026-09-18). The doubling recorded below was real
    # reasoning and it is now superseded: this board draws 79 mA typical and 120 mA worst
    # case against 3 A per XH contact, so two of the four conductors were carrying a
    # current that never needed them. Dropping to a 2-way does three things -- it matches
    # the panel's J9, which went 2-way in the same change and CLOSED that board's severed
    # 24 V bus by vacating 5 mm of its pad row; it takes two crimps out of every harness;
    # and it removes the mis-mate hazard on this link outright, because a 2-way XH cannot
    # be plugged into a 4-way CAN drop and put 24 V on CAN_H. See the two-pinouts note in
    # BOM.md -- this is the cheap version of the 5-way keying proposal, available here
    # only because the current never needed four contacts.
    #
    # The superseded argument, kept because it explains the pin order: the panel's outlet
    # was 1=GND 2=+24V 3=+24V 4=GND, and this connector used to be 2-way against it, so a
    # straight four-conductor cable landed a live 24 V wire and a return on two pins
    # connected to nothing. That asymmetry is what doubling fixed. Making BOTH ends 2-way
    # fixes it the other way and costs less.
    # ⚠ THE HOUSING STAYS 4-WAY BECAUSE JST DOES NOT MAKE A 2-WAY ONE. S2B-XH-SM4-TB
    # is not a part -- the SMT SIDE-ENTRY XH line STARTS AT 4-WAY, which this repo had
    # already established (see BOM.md, "J2 - refitted and done") and which I re-derived
    # the hard way by trying to order one. The board needs side entry (a top-entry plug
    # would insert from inside the housing) and SMT (no post tails through a face that
    # has to seat), and that combination has no 2-way member.
    #
    # So the link goes two-wire by POPULATION, not by housing: ways 3 and 4 are wired to
    # nothing. That still buys the whole point -- two crimps instead of four, and the
    # mis-mate hazard gone in BOTH directions on this cable, because a CAN drop plugged
    # in here lands CAN_H/CAN_L on dead cavities, and this cable plugged into a CAN
    # socket puts nothing on them either. The panel end IS a true 2-way (B2B-XH-A exists
    # in the through-hole line), so the cable is 2-way at one end and 4-way at the other,
    # which is free when the harness is crimped to length anyway.
    j2 = Part(name="S4B-XH-SM4-TB", ref_prefix="J", ref="J2", dest="NETLIST",
              tool="skidl", value="S4B-XH-SM4-TB",
              description="24 V in -- 1=PWR_GND 2=+24V, ways 3/4 unpopulated",
              footprint="Connector_JST:JST_XH_S4B-XH-SM4-TB_1x04-1MP_P2.50mm_Horizontal",
              pins=[Pin(num=i + 1, name=n, func=P)
                    for i, n in enumerate(("PWR_GND", "+24V", "NC3", "NC4"))])
    pgnd += j2[1]
    v24_in += j2[2]
    # ⚠ R44: THE INPUT IS DAMPED, BECAUSE A LIVE PLUG WOULD OTHERWISE KILL THE BUCK
    # (2026-10-05, quality M16). J2 fed 10 uF of ceramic and U13 directly. A live 24 V
    # lead plugged into ceramics rings toward twice the supply: 48 V, against U13's 36 V
    # operating and 38 V absolute maximum. In the instrument the rail arrives through the
    # output panel's switch at about 2 V/ms and nothing rings -- but the first thing this
    # board meets is a bench supply on a metre of lead, plugged live, which is the classic
    # way a ceramic-input buck dies (TI SNVA489).
    # 2 ohm in series, ahead of every capacitor. With about 5 uF left of C160 at 24 V of
    # bias, a metre of lead (1 uH) has a characteristic impedance of 0.45 ohm and the
    # 150 mm harness (0.15 uH) 0.17: 2 ohm is a damping ratio of 2.2 and 5.8. No
    # overshoot at all. It also keeps the buck's 1.4 MHz input ripple off the harness.
    # ⚠ THE PART IS CHOSEN FOR THE PULSE AND MUST NOT BE SHRUNK. A live plug puts the
    # whole 24 V across it for the first microseconds: 288 W peak, falling with a 10 to
    # 20 us time constant, 1.5 to 3 mJ in all. KOA's one-pulse limit (RK73B sheet, "One-
    # Pulse Limiting Electric Power") is 400 W for the 2512 (W3A) below 10 us, 200 W for
    # the 2010 and 40 W for the 1206 -- so it is a 2512, and of that maker, because the
    # curve is theirs. A 1206 would need 15 ohm to stand the same plug.
    # Cost in service: 0.52 V and 0.14 W at the 0.26 A worst case, 0.16 V at the typical
    # 79 mA; U13 regulates from 23.5 V as it does from 24. A dead short behind it draws
    # 12 A and opens the output panel's 1 A fuse (F1 there) in well under a millisecond.
    r44 = _r("R44", "RK73B3ATTE2R0J",
             "24 V input damping, 2 ohm 2512 (LCSC C5139521) -- sized for the plug-in "
             "pulse (288 W peak): do not substitute a smaller case or another maker "
             "without its single-pulse curve",
             "Resistor_SMD:R_2512_6332Metric")
    v24_in += r44[1]
    v24 += r44[2]
    Net("J2_NC_3").connect(j2[3])   # documented no-connects; netcheck
    Net("J2_NC_4").connect(j2[4])   # exempts <REF>_NC_<pin> by name

    # ── the passives the CAD places, wired to what they belong to ────────────
    # R30-R38 and R40-R41 keep the CAD's exact names: that table is spelled out
    # rather than pattern-matched precisely because "R3" (a ballast) and "R30" (a
    # pull) would otherwise collide, and the same hazard exists here.
    # ⚠ R30 IS BOOT0 AND R31 IS NRST, which is the opposite of the order I first
    # wrote. The CAD's table is the authority on which ref is which, and guessing it
    # from the usual ordering would have swapped a pull-up for a pull-down on two
    # pins that both look fine in a netlist and neither of which then works.
    r30 = _r("R30", "10k", "BOOT0 pull-down -- run from flash unless held")
    boot0 += r30[1]
    gnd += r30[2]
    r31 = _r("R31", "10k", "NRST pull-up")
    nrst += r31[1]
    v3d += r31[2]
    # C135: the reset pin's capacitor (2026-10-05, quality M7). ST draws 100 nF from NRST
    # to ground (DS12110, "Recommended NRST pin protection") and this board had none: the
    # pin was a 25 mm track, a pull-up and a probe pad, on a board with a 1.4 MHz buck and
    # 0.2 A of emitter current switching at 48 kHz. A reset pin that glitches does not
    # fail loudly -- the audio stream drops and comes back. Beside R31, on the same node.
    # A probe that connects under reset drives it through the capacitor, as every SWD
    # probe expects to.
    c135 = _c("C135", "100nF", "NRST filter -- ST's recommended reset-pin capacitor")
    nrst += c135[1]
    gnd += c135[2]
    # BOTH CC pins get their OWN 5k1 -- not one resistor on a joined pair. The pair is
    # what tells the host which way round the cable went in, and joining them makes the
    # port undetectable in one orientation.
    r32 = _r("R32", "5k1", "USB-C CC1 pull-down (upstream-facing port)")
    Net("USB_CC1").connect(j1["A5"], r32[1])
    gnd += r32[2]
    r33 = _r("R33", "5k1", "USB-C CC2 pull-down")
    Net("USB_CC2").connect(j1["B5"], r33[1])
    gnd += r33[2]
    # ⚠ MID SITS NEAR THE BOTTOM OF THE RANGE, NOT IN THE MIDDLE, because the signal
    # only goes ONE WAY. The photodiode's cathode is on the virtual earth and its anode
    # on MID, so photocurrent drives the TIA output UP from MID and never below it. A
    # mid-supply reference would throw away half the ADC's range on a swing that cannot
    # happen. 0.33 V leaves ~2.9 V of usable swing and keeps the op-amp's input common
    # mode inside spec (the TLV9064 includes both rails).
    # 9k09/1k from +3V3A: 0.330 V, 363 uA. Low impedance on purpose -- the divider's
    # thermal noise lands on the reference every channel shares, and U11 buffers it.
    # ⚠ AND THE SUMMING NODES DO NOT NEED A GUARD RING -- ARITHMETIC, 2026-09-19, because
    # the header used to list "are the TIA inputs guarded" as an open question and an open
    # question with no number attached stays open forever.
    #
    # There IS no guard: the only zones on this board are GND (F.Cu, In1.Cu, B.Cu), so
    # what sits beside a summing node is ground pour at 0 V, not a ring at the node's own
    # potential. The question is therefore not clearance -- DRC already guarantees every
    # foreign net is at least 0.127 mm away, and it reports zero violations -- but how
    # much current that 0.127 mm of board surface leaks at the voltage across it.
    #
    # MID is 0.327 V (3.3 x 1k/(9k09+1k)), so that voltage is 0.327 and not a supply rail:
    #     surface 1e14 ohm  (clean, conformal coated)   0.003 pA   0.000005 % of 60 nA
    #     surface 1e12 ohm  (typical clean board)       0.33  pA   0.0005   %
    #     surface 1e10 ohm  (flux residue left on)     32.7   pA   0.055    %
    #     surface 1e9  ohm  (visibly contaminated)    327     pA   0.55     %
    # Against the ~60 nA this board was designed around, even a dirty board loses half a
    # percent. A guard ring buys nothing measurable and would cost room in the one place
    # this board has none.
    #
    # ⚠ THE LOW MID IS DOING WORK IT WAS NOT CHOSEN FOR. 0.327 V was picked for OUTPUT
    # SWING -- it leaves 2.9 V of headroom above MID for the ADC. But leakage scales with
    # the voltage driving it, so a conventional mid-supply reference at 1.65 V would make
    # every figure above FIVE TIMES larger. Worth knowing before anyone "fixes" MID to a
    # more standard half-rail.
    # ⚠ THE SWITCHER'S HOT LOOP, MEASURED 2026-09-19 -- the last of the three things this
    # file's header listed as unchecked. U13 is a TPS560430 in SOT-23-6, whose VIN (4, 5)
    # and GND (2) sit on OPPOSITE sides of the package, so the input cap cannot straddle
    # them the way it can on a part with adjacent pins.
    #
    # Traced from the routed copper: C161's +24V pad reaches VIN by arcing over the NORTH
    # side of the package -- 7.08 mm of track -- while the GND return is 1.60 mm straight
    # back underneath. Enclosed area 6.23 mm2, with the cap 4.84 mm from the VIN pad it
    # feeds. That is inside the usual "keep the input loop under ~10 mm2" guidance and it
    # is NOT tight; on a board that is only a switcher it would be worth moving the cap.
    #
    # ⚠ IT IS FINE HERE FOR A REASON THAT IS ABOUT DISTANCE, NOT ABOUT THE LOOP. The
    # nearest photodiode is 52.90 mm away (PD10B) and the farthest is 140.37 mm, with the
    # In1.Cu plane unbroken underneath the whole span -- one poured region, checked in the
    # gerbers. Near-field magnetic coupling from a small loop falls off as 1/r^3, so a
    # 6 mm2 loop fifty millimetres from the first summing node is not what will limit this
    # board. The 188 mm outline that makes the strip awkward to route is the same thing
    # that puts the switcher this far from it.
    #
    # If the switcher ever moves toward the strip, this stops being true and the cap
    # placement becomes the first thing to fix.
    r34 = _r("R34", "9k09 1%", "MID divider, top -- sets the TIA virtual earth to 0.33 V")
    r35 = _r("R35", "1k 1%", "MID divider, bottom")
    v3a += r34[1]
    mid_raw += r34[2], r35[1]
    gnd += r35[2]
    # ⚠ THE DIVIDER HAD NO BYPASS, AND IT IS THE ONE PATH THAT PUTS SUPPLY NOISE ON THE
    # CARRIER, IN PHASE, ON ALL TWENTY CHANNELS AT ONCE.
    #
    # C133 bypasses MID -- U11's OUTPUT -- which is not the same thing and does not do this
    # job. Inside its feedback loop the buffer forces its output to follow its input, so a
    # capacitor there handles load transients and filters nothing that arrived at pin 3.
    # Everything on MID_RAW is reproduced onto the reference flat to the amp's bandwidth.
    #
    # And MID_RAW carries a very specific noise. The LED row switches at 48 kHz, which is
    # the carrier, drawing its current from V5_PRE; U9 feeds +3V3A from V5_PRE through FB1
    # with perhaps 40-50 dB of PSRR at that frequency; the divider passes what is left to
    # MID_RAW at 1k/10k09, so 20 dB. That lands on every channel's non-inverting input AT
    # THE LOCK-IN'S OWN REFERENCE FREQUENCY AND IN PHASE WITH IT -- the one error the
    # demodulator cannot reject, SUM cannot reject (both halves see it) and DIFF cannot
    # reject (both halves see it equally). It reads as signal.
    #
    # 1 uF against the divider's 901 ohm source (9k09 || 1k) puts the pole at 177 Hz, so
    # 48 kHz is down a further 48.6 dB -- about 69 dB total with the divider. It costs no
    # new BOM line: 1 uF 0402 is already on this board (C140, and the converters' AVDD and
    # VREF bulk). The 0.9 ms it adds to the reference's startup is nothing.
    c114 = _c("C114", "1uF", "MID divider bypass -- keeps the LED's 48 kHz off the "
              "reference all twenty channels share; see the note")
    mid_raw += c114[1]
    gnd += c114[2]
    r36 = _r("R36", "100R", "LED driver gate series")
    led_gate += r36[1]
    Net("LED_GATE_Q").connect(r36[2], q1[1])
    # R37/R38 and C112/C113 are the four parts this netlist ADDED to the CAD -- see the
    # note beside them in src/optical_pickup.py. They are here because turning a part
    # table into nets is what exposed them: a part no net needs looks exactly like a
    # part nobody noticed was missing.
    r37 = _r("R37", "12k 1%", "PHY RBIAS -- a PRECISION part: it sets the USB "
             "transmitter's drive current, so 1% is the spec, not a preference")
    rbias += r37[1]
    gnd += r37[2]
    # R39: the VBUS pin's series resistor. 10 k is the value Microchip's peripheral
    # diagram names (figure 7-1: "10K Ohms will protect against transients up to 10V").
    # Against the pin's 75 k to ground it leaves 4.4 V of a 5 V bus: far above the
    # session-valid threshold, which is the only comparator a device uses.
    r39 = _r("R39", "10k", "PHY VBUS series, DS00001783C figure 7-1")
    vbus += r39[1]
    phy_vbus += r39[2]
    r38 = _r("R38", "100k", "LED gate pull-down -- the emitters must be OFF while "
             "the MCU is in reset, not floating at whatever the gate charges to")
    led_gate += r38[1]
    gnd += r38[2]
    # VREF = 1.00 V (TPS560430 datasheet, electrical characteristics), so 5 V wants a
    # 4:1 divider. 40.2 k / 10.0 k gives 5.02 V -- 0.4% high, inside the reference's own
    # 1.5% -- from standard E96 values.
    # LMR33630: VREF is also 1.0 V; TI's own 5 V example uses 100k / 24.9k (5.02 V).
    r40 = _r("R40", "100k 1%", "buck feedback divider, top -- 5.02 V with R41")
    r41 = _r("R41", "24k9 1%", "buck feedback divider, bottom")
    v5_pre += r40[1]
    fb += r40[2], r41[1]
    pgnd += r41[2]

    # -- the CAD's capacitor groups, each wired to the rail its placement sits on --
    # C100-C111: twelve MCU rail decouplers. The last two sit on the ANALOG 3V3,
    # because VDDA and VREF+ are the pins the twenty channels are measured against.
    # C111 is 1 uF (2026-10-04): ST draws VDDA / VREF+ with 1 uF beside the 100 nF
    # (DS12110, "Power supply and reference decoupling"), and both were 100 nF.
    for k in range(12):
        c = _c("C1%02d" % k, "1uF" if k == 11 else "100nF", "MCU decoupling")
        rail = v3a if k >= 10 else v3d
        rail += c[1]
        gnd += c[2]
    # C115-C118, C128, C129: six more on +3V3D (2026-10-04), so every VDD pair on all
    # four sides of the package has a capacitor at it -- see the ring in the CAD.
    # C144: U11's own supply bypass.
    for tag, rail, why in ([(t, v3d, "MCU decoupling") for t in
                            ("C115", "C116", "C117", "C118", "C128", "C129")]
                           + [("C144", v3a, "U11 supply bypass")]):
        c = _c(tag, "100nF", why)
        rail += c[1]
        gnd += c[2]
    # C112/C113: the H7 core regulator's VCAP pair. ADDED with R37/R38 -- see above.
    for tag, net in (("C112", vcap1), ("C113", vcap2)):
        c = _c(tag, "2.2uF", "H7 core regulator cap -- REQUIRED, not optional",
               "Capacitor_SMD:C_0805_2012Metric")
        net += c[1]
        gnd += c[2]
    # The PHY's capacitors, each named for the pin it stands at (the note at U7). The two
    # 4.7 uF parts are its regulators' output capacitors: the sheet gives the value and
    # +-20 %, and an 0805 keeps most of it at 1.8 V of bias where an 0402 would not.
    for tag, net, val, why, fp in (
            ("C119", v3d, "100nF", "PHY VDD3.3 bypass -- pin 25", _C_0402),
            ("C121", v3d, "100nF", "PHY VDD3.3 bypass -- pin 6", _C_0402),
            ("C138", v3d, "100nF", "PHY VDD3.3 bypass -- pin 16", _C_0402),
            ("C139", v3d, "100nF", "PHY VDD3.3 bypass -- pin 30", _C_0402),
            ("C122", v1v8, "4.7uF", "PHY VDD1.8 regulator output -- pin 26",
             "Capacitor_SMD:C_0805_2012Metric"),
            ("C145", v1v8, "100nF", "PHY VDD1.8 bypass -- pin 26", _C_0402),
            ("C137", v1v8, "100nF", "PHY VDD1.8 bypass -- pin 15", _C_0402),
            ("C120", v1v8a, "4.7uF", "PHY VDDA1.8 regulator output -- pin 29",
             "Capacitor_SMD:C_0805_2012Metric"),
            ("C136", v1v8a, "100nF", "PHY VDDA1.8 bypass -- pin 29", _C_0402)):
        c = _c(tag, val, why, fp)
        net += c[1]
        gnd += c[2]
    # C123 / C124: Y1's load capacitors, and the VALUE FOLLOWS THE CRYSTAL'S CL. Each leg
    # carries its capacitor plus that leg's stray, and the crystal sees the two legs in
    # series: CL = (C + Cleg) / 2, so C = 2 x CL - Cleg. Cleg is the MCU pin's ~5 pF plus
    # ~2 pF of board (the track is 2 mm, so the low end): 2 x 10 - 7 = 13 pF -> 12 pF for
    # the 10 pF crystal (see Y1).
    # ⚠ THESE ARE THE STARTING VALUES, NOT THE FINAL ONES. Stray capacitance is a
    # property of the finished board, so the frequency is measured on the first article
    # and the caps trimmed -- that is normal for a crystal and it is not an admission
    # that the arithmetic is wrong. (The PHY's reference is an oscillator and has none.)
    for tag, net, val in (("C123", osc_in, "12pF"), ("C124", osc_out, "12pF")):
        c = _c(tag, val, "crystal load -- C0G")
        net += c[1]
        gnd += c[2]
    # C130-C133: the bulk caps and the reference bypass.
    # ⚠ C130 IS 1 uF: THE PHY'S OWN MINIMUM FOR A DEVICE (USB3300 DS00001783C table 7-2,
    # "Capacitance values at VBUS of USB connector": device 1 uF min, 10 uF max, drawn on
    # the connector side of RVBUS in its figure 7-1). It was 100 nF, on the argument that
    # VBUS is only sensed here and that bulk against R39's 10 k would slow the sense. That
    # argument put the capacitor on the wrong side of the resistor: C130 is on VBUS itself,
    # which the host drives directly, so R39 is not in its charging path. 1 uF, the bottom
    # of the range, because the board draws nothing from VBUS and the host pays the inrush.
    for tag, net, desc in (("C130", vbus, "VBUS capacitor, the PHY's 1 uF minimum -- see note"),
                           ("C131", v3d, "3V3 digital bulk"),
                           ("C132", v3a, "3V3 analog bulk"),
                           ("C133", mid, "MID reference bypass -- the twenty summing "
                            "nodes share this, so it is what keeps them from talking "
                            "to each other through their own reference")):
        c = _c(tag, "1uF" if tag == "C130" else "10uF", desc,
               "Capacitor_SMD:C_0805_2012Metric")
        net += c[1]
        gnd += c[2]
    # C140-C143: decoupling at the power inputs, ANALOG side of the bead.
    # C140, the one at U9's input pin, is 1 uF (2026-10-04): the bead isolates U9 from the
    # buck's bulk on purpose, which left its input with 0.4 uF; the TPS7A20 asks for 1 uF
    # at its input (as the SPX3819 before it did).
    for tag in ("C140", "C141", "C142", "C143"):
        c = _c(tag, "1uF" if tag == "C140" else "100nF", "power-input decoupling")
        v5 += c[1]
        gnd += c[2]
    # the buck's furniture, keeping the CAD's C16x names
    c160 = _c("C160", "10uF/50V", "24 V input bulk -- 1206 for the DC-bias derating",
              "Capacitor_SMD:C_1206_3216Metric")
    v24 += c160[1]
    pgnd += c160[2]
    # 50 V, SAID IN THE VALUE (2026-10-04): the fab picks a passive by its value text, and
    # a bare "100nF" 0402 is its 16 V basic part -- on a 24 V rail the panel clamps at 48.
    c161 = _c("C161", "100nF/50V", "24 V input HF bypass")
    v24 += c161[1]
    pgnd += c161[2]
    c162 = _c("C162", "22uF/16V", "buck 5 V output bulk",
              "Capacitor_SMD:C_0805_2012Metric")
    v5_pre += c162[1]
    pgnd += c162[2]
    # ⚠ C164: U8'S OWN INPUT CAPACITOR, AND V5_PRE HAD NONE ANYWHERE NEAR IT. This rail
    # runs from the buck at the -Y tail all the way to the digital block, feeding the
    # AMS1117 (207-272 mA) and the ten emitters' ballasts on the way, and its ONLY
    # capacitor was C162 at the buck -- measured 20.7 mm from U8. A linear regulator
    # with no local input capacitance sees that 20.7 mm as series inductance in front of
    # it, and the emitters pulsing at 48 kHz share the same rail. 10 uF beside U8 costs
    # one 0805 and one BOM line already in the build.
    c164 = _c("C164", "10uF/16V", "U8 input bulk -- the only local cap on V5_PRE",
              "Capacitor_SMD:C_0805_2012Metric")
    v5_pre += c164[1]
    gnd += c164[2]
    # 100 nF, not 10: the TPS560430 datasheet specifies "a high quality 100-nF capacitor"
    # from CB to SW. Too small a bootstrap cap droops over the on-time and under-drives
    # the high-side FET.
    c163 = _c("C163", "100nF", "buck bootstrap, BOOT to SW -- 100 nF per datasheet")
    boot += c163[1]
    sw += c163[2]
    # LMR33630 extras (SNVSB08 Table 6-1 / 9.2.2): VCC needs its own 1 uF; the two VIN
    # pins sit on OPPOSITE sides of the RNX package, so each gets its own 100 nF (TI's
    # layout puts one beside each VIN/PGND pair); and a second 22 uF at the output.
    c165 = _c("C165", "100nF/50V", "24 V HF bypass -- the second VIN/PGND pair (pins 10/11)")
    v24 += c165[1]
    pgnd += c165[2]
    c166 = _c("C166", "1uF", "buck VCC bypass (internal 5 V LDO)")
    vcc_buck += c166[1]
    pgnd += c166[2]
    c167 = _c("C167", "22uF/16V", "buck 5 V output bulk, second",
              "Capacitor_SMD:C_0805_2012Metric")
    v5_pre += c167[1]
    pgnd += c167[2]


# ── the board ────────────────────────────────────────────────────────────────
# ⚠ OUTLINE AND PLACEMENTS BOTH COME FROM THE CAD. See the header: this is the one
# board whose shape the instrument dictates. _SECTIONS is (y0, y1, x_minus, x_plus)
# per band, and the shape it makes is a bracket -- wide over the endplate at both Y
# ends, narrow through the middle where it has to fit the 14 mm deck band.
def _cell_pt(k, dx, dy):
    """A point given as an offset from converter k's centre in the frame of a part turned
    180 -- the frame every cell offset in this file and in src/optical_pickup.py is written
    in. The two converters at the +Y end are turned 0, so the offset mirrors through the
    centre."""
    ux, uy, rot = _placements(CX, CY)["U%d" % (14 + k)]
    sgn = 1.0 if abs(rot - 180.0) < 1e-6 else -1.0
    return (ux + sgn * dx, uy + sgn * dy)


def _mcu_feed():
    """+3V3D FROM THE REGULATOR TO THE MCU: one 0.8 mm trunk on B.Cu, laid before routing.

    ⚠ THE ROUTER DOES NOT MAKE THIS CONNECTION SHORT, AND IT IS THE MCU'S WHOLE SUPPLY.
    Three routes running (2026-10-05) it took +3V3D from U8 down to the PHY on a 0.25 mm
    inner track and left the MCU's ring on an island; the closing step then joined the two
    from the PHY, 50 mm away. Connected, DRC-clean, and 0.35 A through about 370 mohm:
    90 mV lost against the 66 mV this rail is allowed. The straight line from U8's output
    capacitor to the MCU's nearest supply pin is 15 mm and B.Cu between them is empty.
      from  a via between U8's tab and C131, the output capacitor, joined to both on F.Cu
      to    a via beside C100, pin 49's bypass capacitor at the MCU's south-west corner
    30 mm at 0.8 mm in 1 oz copper is 18 mohm, 6 mV at 0.35 A. The ring round the MCU is
    still the router's."""
    P = _placements(CX, CY)
    for ref, x, y in (("C131", -12.98, -62.08), ("C100", -2.87, -51.87)):
        px, py, _ = P[ref]
        assert abs(px - x) < 0.03 and abs(py - y) < 0.03, (
            "%s is not where _mcu_feed draws to: (%.3f, %.3f), drawn for (%.3f, %.3f)"
            % (ref, px, py, x, y))
    a, b = (-14.75, -62.08), (-3.95, -51.39)
    tracks = [("+3V3D", "F.Cu", 0.8, [(-16.17, -62.08), a, (-13.93, -62.08)]),
              ("+3V3D", "B.Cu", 0.8, [a, (-14.75, -58.50), (-7.64, -51.39), b]),
              ("+3V3D", "F.Cu", 0.5, [b, (-2.87, -51.39)])]
    return tracks, [("+3V3D",) + a, ("+3V3D",) + b]


def _phy_copper():
    """(tracks, vias): everything at the PHY that is not ULPI or the USB pair.

    These are hops of 1 to 8 mm on a part with 0.5 mm pins, and left to the stitcher and
    the router they came back open on three routes running (2026-10-05): a ground via in
    the clock's gap, +3V3D run between RBIAS and its resistor, 3.3 V capacitors the rail
    never reached because nothing had put a via beside them, then a ground stub across
    VBUS's 2 mm and a ground via in the only door to a regulator capacitor. Declared,
    the stitcher and the router both work round them.
    Offsets are from U7's centre with the part turned 90 (src/optical_pickup.py, section
    4b-i, has the same frame and the pin table):
      THE GAP in the -X column, top to bottom, 0.2 mm tracks at 0.15:
        VDD1.8   pin 26 to C145, and on through the gap to C122 (its 4.7 uF)
        XI       pin 28 through the gap to the oscillator's output, the near lower land
        VDDA1.8  pin 29 through the gap to C120 (its 4.7 uF), with a stub down to C136
      RBIAS  pin 32: down and out to R37's inner pad
      +3V3D  pin 25 to C119, pins 30 + 31 to C139, pin 16 to C138, pin 6 to C121, each
             through a via standing in the lane between the pin and its capacitor
      +3V3D  at the oscillator: its enable land to its supply land, and the supply land
             up to C125's rail pad (C125.1 has the via: pin_escapes)
      VBUS   pin 4: out under the socket-face row to R39
      GND    pins 1, 2 and 9 (RESET) straight into the flag, which has the via: stitched
             like ordinary ground pads, pins 1 and 2 threw stubs across VBUS's way out
      THE +X FACE'S FOUR ULPI CONTROL PINS, each out to its own via, staggered. They are
      0.5 mm apart and a 0.6 mm via beside one closes the lane of the next: with CLKOUT
      and DIR escaped side by side, STP between them had 0.4 mm to leave through and came
      back with no copper at all. CLKOUT keeps the near site (and stays under pin 15's
      way out to its capacitor), STP steps down and runs past it to a via 1.5 further
      out, DIR and NXT turn down and away. 0.15 or more between any two of them.
      1V8    also pin 15 to pin 26, under the package (at the end of this function)"""
    P = _placements(CX, CY)
    ux, uy, rot = P["U7"]
    assert abs(rot - 90.0) < 1e-6, "the offsets below are for U7 turned 90, not %s" % rot
    for ref, dx, dy in (("Y2", -10.275, 0.50), ("C119", -5.155, 2.54), ("C145", -5.155, 1.36),
                        ("C136", -5.155, -0.51), ("C139", -5.155, -1.69),
                        ("R37", -5.155, -2.87), ("C122", -7.30, 2.95), ("C120", -7.30, -1.94),
                        ("C138", 4.795, 2.335), ("C121", -0.45, -4.735),
                        ("R39", -2.55, -4.735), ("C125", -9.925, 3.31)):
        px, py, _ = P[ref]
        assert abs((px - ux) - dx) < 0.02 and abs((py - uy) - dy) < 0.02, (
            "%s is not where _phy_copper draws to: (%.3f, %.3f) from U7, drawn for "
            "(%.3f, %.3f)" % (ref, px - ux, py - uy, dx, dy))

    def pts(*offs):
        return [(round(ux + dx, 3), round(uy + dy, 3)) for dx, dy in offs]
    vias = [(-3.635, 2.15), (-3.635, -1.20), (3.70, 2.25), (0.40, -3.65)]
    tracks = [
        ("PHY_1V8", "F.Cu", 0.2, pts((-2.44, 1.25), (-4.00, 1.25), (-4.11, 1.36),
                                      (-4.675, 1.36), (-5.235, 0.80), (-7.30, 0.80),
                                      (-7.30, 2.00))),
        ("PHY_XI", "F.Cu", 0.2, pts((-2.44, 0.25), (-3.00, 0.25), (-3.20, 0.45),
                                     (-8.50, 0.45), (-8.95, 0.00), (-9.45, -0.30),
                                     (-9.45, -0.55))),
        ("PHY_1V8A", "F.Cu", 0.2, pts((-2.44, -0.25), (-3.05, -0.25), (-3.40, 0.10),
                                       (-6.20, 0.10), (-6.90, -0.60), (-7.30, -0.99))),
        ("PHY_1V8A", "F.Cu", 0.2, pts((-4.675, 0.10), (-4.675, -0.51))),
        ("PHY_RBIAS", "F.Cu", 0.2, pts((-2.44, -1.75), (-3.10, -1.75), (-4.22, -2.87),
                                        (-4.675, -2.87))),
        ("+3V3D", "F.Cu", 0.25, pts((-2.44, 1.75), (-3.235, 1.75), (-3.635, 2.15),
                                     (-4.025, 2.54), (-4.675, 2.54))),
        ("+3V3D", "F.Cu", 0.25, pts((-2.44, -0.75), (-3.185, -0.75), (-3.635, -1.20),
                                     (-4.125, -1.69), (-4.675, -1.69))),
        ("+3V3D", "F.Cu", 0.25, pts((-2.44, -1.25), (-3.585, -1.25), (-3.635, -1.20))),
        ("+3V3D", "F.Cu", 0.25, pts((2.44, 1.75), (3.20, 1.75), (3.70, 2.25), (4.40, 2.25),
                                     (4.795, 1.855))),
        ("+3V3D", "F.Cu", 0.25, pts((0.75, -2.44), (0.75, -3.30), (0.40, -3.65),
                                     (0.03, -4.02), (0.03, -4.735))),
        ("+3V3D", "F.Cu", 0.25, pts((-11.10, 1.55), (-9.45, 1.55), (-9.45, 3.31))),
        ("PHY_VBUS", "F.Cu", 0.2, pts((-0.25, -2.44), (-0.25, -3.10), (-1.10, -3.95),
                                       (-1.70, -3.95), (-2.04, -4.29), (-2.04, -4.735))),
        ("GND", "F.Cu", 0.2, pts((-1.25, -2.44), (-1.25, -1.50))),
        ("GND", "F.Cu", 0.2, pts((-1.75, -2.44), (-1.75, -2.05), (-1.40, -1.70))),
        ("GND", "F.Cu", 0.2, pts((2.44, -1.75), (1.50, -1.75))),
    ]
    fan = (("ULPI_CK", ((2.44, 0.75), (3.00, 0.75), (3.10, 0.65), (3.40, 0.65))),
           ("ULPI_STP", ((2.44, 0.25), (2.95, 0.25), (3.35, -0.15), (4.90, -0.15))),
           ("ULPI_DIR", ((2.44, -0.25), (2.95, -0.25), (4.20, -1.50))),
           ("ULPI_NXT", ((2.44, -0.75), (2.90, -0.75), (3.40, -1.25), (3.40, -1.90))))
    out_vias = [("+3V3D",) + p for p in pts(*vias)]
    for net, path in fan:
        tracks.append((net, "F.Cu", 0.2, pts(*path)))
        out_vias.append((net,) + pts(path[-1])[0])
    # PIN 15 TO PIN 26, the two VDD1.8 pins the pin table says to join, on opposite faces
    # with the flag between them: under the package on B.Cu, between the flag's via and
    # the two +3V3D vias. Left to the router it was the one net of this part still open.
    # (the far via stops short of C122's land: an open hole in a pad wicks its solder)
    link = ((4.50, 0.75), (4.10, 1.30), (-6.00, 1.30), (-6.45, 1.15))
    tracks += [("PHY_1V8", "F.Cu", 0.2, pts((2.44, 1.25), (4.00, 1.25), link[0])),
               ("PHY_1V8", "B.Cu", 0.2, pts(*link)),
               ("PHY_1V8", "F.Cu", 0.2, pts(link[-1], (-6.45, 0.80)))]
    out_vias += [("PHY_1V8",) + q for q in pts(link[0], link[-1])]
    return tracks, out_vias


def _cell_tracks():
    out = []
    for k in range(5):
        # ADDR1 / ADDR0 (pins 15/16) and AVSS (pin 4) straight into the EP
        for dy in (0.25, -0.25):
            out.append(("GND", "F.Cu", 0.2, [_cell_pt(k, -1.962, dy), _cell_pt(k, -0.9, dy)]))
        out.append(("GND", "F.Cu", 0.2, [_cell_pt(k, 1.962, 0.25), _cell_pt(k, 0.9, 0.25)]))
    return (out + _fan_tracks() + _shdn_tracks() + _v3_trunk() + _i2c_spine()
            + _v5_spine() + _led_row_spine() + _mid_spine()
            + _bus_spines() + _v3a_spine() + _sd_spines())


# ⚠ THE +3V3D CLUSTERS CANNOT BE JOINED BY LAYING EITHER (2026-09-22). _v3_trunk links
# each cluster internally and took that net from 5 failures to 2; the 2 that remain are the
# annulus-to-wrap hop. Searched for a single-layer path from (-28.75, -36.04) to
# (-22.06, 91.61), checking BOTH the pads and the outline: no straight lane exists, and no
# 3-segment dogleg over a 26 x 60 x 26 grid of candidates exists either. The sensing strip is
# genuinely full across its whole length. Crossing it needs In2 and therefore vias, and the
# router will not connect to a pre-laid via here -- so that hop stays the router's.
#
# ⚠ AND SWAPPING THE CELL'S ROWS WAS TRIED AND IS WRONG (2026-09-22). The reasoning below
# is sound as far as it goes -- Ci really does sit inboard of Cm, so a signal from the strip
# really does meet the GND-local cap before its own coupling cap -- but swapping them routed
# 14 unconnected and 28 VIOLATIONS against 9 and 0. The near/far split is not free to move:
# the fan threads INxP and INxM between each other at 0.5 pin pitch, and which row a cap sits
# in is what keeps those threads from crossing (the note above _fan_tracks says so, and says
# an earlier wider-flung arrangement left 12 of them open). So the corridor stays 0.4 mm and
# U15 needs a different answer -- more board, or a cell narrow enough to sit clear of the
# jack. Reverted; kept here so the next reader does not spend another route finding out.
# ORIGINAL REASONING, still true and still not actionable on its own:
# ⚠ AND THE NEXT LEVER FOR U15 IS THE CELL'S ROW ORDER, WHICH IS BACKWARDS FOR SIGNAL FLOW.
# In each cell the Ci coupling caps sit in the NEAR row (3.75 from the chip) and the Cm caps
# in the FAR row (5.85) -- so a signal arriving from the strip meets Cm FIRST and has to get
# past it to reach its own Ci. That is what closes the eastward corridor to 0.4 mm (Cm21
# starts at y 81.4). Swapping the two rows would put Ci outermost, facing the incoming run.
# It is not a one-line change: elec/optical.py's _fan_tracks lays the fan from these same
# CELL_NEAR/CELL_FAR offsets and assigns rows per pin, so both have to move together, and it
# touches all five cells including the three that route fine today.


# ⚠ _u15_haul IS DELETED, AND ITS LESSON IS WORTH MORE THAN THE CODE WAS (2026-09-22).
# It laid four F.Cu lanes from the strip to U15's coupling caps, through a corridor measured
# "completely clear of pads" at x -16.5..-5.5 over y 45..83. It routed 11 unconnected and 3
# violations, against 9 and 0 without it.
#
# ⚠ THE CORRIDOR WAS MOSTLY NOT BOARD. The scan asked the PADS and never asked the OUTLINE,
# and this board is not a rectangle: below y ~80.9 it is only the sensing strip, x -32.42 ..
# -13.14, and it is the HEAD above that which reaches x +32.42. Two of the four lanes (-13.8
# and -12.6) were off the board edge entirely -- which is exactly what DRC said,
# copper_edge_clearance 0.00 mm. The region scanned "clear" because it is AIR.
#
# What the CORRECTED scan says, for whoever picks this up:
#   * vertical lanes x -16.5 .. -14.1 are clear AND inside the strip (2.4 mm; four lanes fit)
#   * but only ONE horizontal lane runs east into the head -- y 80.9..81.3, about 0.4 mm,
#     because Cm21 starts at 81.4 -- and four nets cannot share it
#   * the last hop is fine: a vertical at each Ci's own x threads between the Cm caps with
#     0.6 mm either side, which is what _fan_tracks already does inside the cell
# So it needs either the eastward leg on another layer (which needs vias the router will not
# connect to, so the path would have to be laid pad to pad) or the Cm row moved +Y to open a
# second lane. MEASURE THE OUTLINE FIRST.

def _v3_trunk():
    """Join each CLUSTER of converter cells' +3V3D stubs into one piece of B.Cu copper.

    ⚠ +3V3D WAS A THIRD OF EVERY FAILURE (5 of 15 unconnected, 2026-09-22) and it is not
    a routing problem, it is a MISSING BUS. The rail reached the board as 131 separate
    F.Cu traces because nothing ever laid it down deliberately: each cell got its own
    little F/B/F jog off IOVDD (see _shdn_tracks) and the router was left to find the
    trunk joining them. It found most and missed five, in a different five every run.

    The stubs already end on B.Cu at the same y within a cluster, so the trunk is one
    straight track per cluster through points the cell code chose -- the islands MERGE
    into one net island, with NO via to connect to (the router never connects to a
    pre-laid via on this board -- measured on SHDNZ and again on SAI). The two clusters
    are still the router's to join; this removes the four intra-cluster hops it keeps
    dropping, and gives the digital supply a real low-impedance spine while it is there."""
    # ⚠ ONE TRUNK NOW, NOT TWO. The cells used to sit in two clusters -- a pair at the +Y
    # wrap and three in the annulus -- and the hop between them had no single-layer path at
    # all (searched: no straight lane, no dogleg). Since all five moved into the strip in one
    # column at a common x, their B.Cu stubs line up and ONE track joins the lot.
    end = lambda k: _cell_pt(k, _V3_CH_DX, -3.27)
    return [("+3V3D", "B.Cu", 0.3, [end(0), end(4)])]


# ⚠ THE +3V3D CHANNEL, hoisted from five copies of -2.85 (the trunk's own ends, the three
# stub legs that reach it, and the via pair). It is ONE number -- the x, in cell-relative
# terms, of the digital rail's vertical run -- and having it written out five times meant
# moving it was five edits and a chance to miss one.
#
# ⚠ AND IT MOVED 0.20 WEST, 2026-09-24, TO GIVE Cm<k>4 ITS GROUND VIA BACK. The Cm caps in
# the FAR row sit at cell x -2.30, so at -2.85 the trunk ran 0.55 mm from them. A 0.6 via
# beside that pad needs via/2 + trunk/2 + clearance = 0.30 + 0.15 + 0.15 = 0.60, so it
# missed by 0.05 mm -- and the stitcher, finding nothing legal to the west, put the via on
# the far side of the coupling cap's door and ran its connecting track straight through the
# door. That is what blocked the comb crossing in four of the five cells: not the channel
# width, not the door, but 0.05 mm on a rail 26 mm away. The gap to the I2C spine is 1.13,
# so the room was already there and nothing else has to move to use it.
_V3_CH_DX = -3.05

_I2C_SPINE_DX = -3.98           # x 65.60 on the placed board: see below
_I2C_SCL_DY = -0.75             # pin 17. ⚠ NOT +0.75 -- the cell frame's y is
                                # INVERTED in the board frame, so +0.75 is pin 14


def _i2c_spine():
    """Lay I2C2_SCL as ONE B.Cu spine down the converter column.

    ⚠ THE SAME MISSING-BUS SHAPE AS +3V3D, and it arrived with the column. Four of the
    twelve failures after the five converters moved into the strip were SCL, and every
    one of them was a hop between neighbouring cells -- U14->U15, U16->U15, U17->U16,
    U17->a stub. Left to the router a five-drop bus on a shared x came back as 133.5 mm
    of copper and 7 vias with the board TO ITSELF (.ins/solo.py); the direct run is 75 mm.
    That is not a router that needs more passes, it is a bus nobody drew.

    ⚠ IT CANNOT BE THE OBVIOUS STRAIGHT LINE, which is what makes it worth a function.
    All five pin 17s share x = 66.619 exactly, so a single track through them looks free
    -- and it would short pins 17 through 24, the whole side of each QFN, which sit on
    that same x at 0.5 mm pitch. Nor can the spine simply step outboard on F.Cu: pad 17
    ends at x 66.207, and Cm24/34/44/54 sit at 66.28, so the first clear F.Cu x is
    already inside the caps.

    ⚠ AND THE FIRST ATTEMPT PUT THE SPINE OFF THE BOARD, which is the SECOND time on this
    board that a lane was chosen by asking the pads and never the outline -- the first
    cost eleven unconnected and three violations on U15's haul, and the warning written
    then is forty lines above this one. x 62.0 .. 66.2 does carry no pad at all over the
    column's whole y range. It carries no pad because the board edge is at 64.5817, and a
    spine at 64.80 sits 0.22 mm from it against a 0.30 rule.
    ASK THE OUTLINE. It is one call: the Edge.Cuts crossings at a given y.

    ⚠ THE SECOND BUG WAS QUIETER AND WOULD HAVE SHIPPED. The stubs were written at cell
    offset +0.75, read off pcbnew as pin 17's y -- but _cell_pt returns CAD coordinates
    and the board frame INVERTS y, so +0.75 is pin 14, which is SHDNZ, which _shdn_tracks
    ties to +3V3D. The DRC did not report a short; it simply relabelled every piece of
    this copper [+3V3D], and the only reason it was caught is that two unrelated tracks
    happened to share a length of 74.9077 mm and the coincidence did not sit right.

    So: a stub out of each pin 17 to x 65.60, a via, and the spine on B.Cu, in a channel
    that had to be WIDENED to exist -- see ADC_BUS_CH in src/optical_pickup.py. At the old
    column x the gaps either side of the +3V3D via column were 0.55 and 0.18 mm and a
    0.6 mm via needs 1.2: there was no lane here at all, for this net or any other.

    ⚠ SDA IS NOT LEFT TO THE ROUTER ANY MORE, AND THIS SAID IT WAS. The reasoning was
    sound when written -- SDA had failed zero times, and pin 18 shares pin 17's x so a
    second spine beside this one would have to cross it. It failed later, _bus_spines grew
    an SDA spine that goes round the west face instead of crossing, and nobody came back
    here. A note that describes a decision the code no longer implements is worse than no
    note: it is the reason I spent a pass looking for a missing SDA spine that exists.
    """
    out, DX, DY = [], _I2C_SPINE_DX, _I2C_SCL_DY
    for k in range(5):
        out += [("I2C2_SCL", "F.Cu", 0.2,
                 [_cell_pt(k, -1.963, DY), _cell_pt(k, DX, DY)])]
    # ⚠ THE SPINE RUNS ON PAST THE LAST CONVERTER, down to the border. Stopping at cell 5
    # left the handover 5.36 mm up in the array, which is 5.36 mm of ratline the router
    # draws across the strings for no reason -- the lane is empty below the cell.
    out.append(("I2C2_SCL", "B.Cu", 0.25,
                [_cell_pt(0, DX, DY), (_cell_pt(4, DX, DY)[0], _SD_BORDER)]))
    return out


# The three broadcast nets I2C2_SCL forgot. Pin offsets read off the placed board, which
# has all five converters at rot 180 on an 18.727 pitch, so one set of offsets serves all.
_SDA_DY, _SDA_JOG, _SDA_DX = -1.250, -1.60, -4.91      # pin 18, west face
_SAI_ROW = -1.9628                                     # pins 19..24, south face
_FS_DX, _FS_JOG, _FS_SPINE = 0.750, -6.00, 10.60       # pin 23
_SD_DX, _SD_JOG = -0.250, -7.20                        # pin 21, one net per cell
_SD_SPINE = (9.80, 9.00, 8.20, 7.40)                   # cells 0..3, north cell outermost
_SD_BORDER = -19.00                                    # where the south half takes over
_SCK_DX, _SCK_JOG, _SCK_SPINE = 0.250, -6.60, 6.40     # pin 22


def _bus_spines(w=0.2, spine_w=0.25):
    """I2C2_SDA, SAI_FS and SAI_SCK: the three buses that should look like I2C2_SCL.

    ⚠ ALL FOUR ARE THE SAME NET SHAPE -- one MCU pin driving all five converters -- and
    only SCL had a spine. The other three were five separate islands each, so their
    ratsnest drew as one long line from the MCU to whichever pad happened to be nearest,
    which is what made them look like nets "reaching up to strings 1 and 2" (user,
    2026-09-24). They were not reaching anything; there was no copper to stop anywhere.

    ⚠ THEY CANNOT ALL USE SCL's LANE. SDA is SCL's neighbour on the west face and takes
    the west strip beside it, but SAI_SCK and SAI_FS are on the SOUTH face, and getting
    them west means crossing +3V3D's B.Cu spine at x 8.85 and SCL's at 7.92 on those
    spines' own layer. East is empty instead -- nothing at all between x 16.4 and the
    board edge at 28.6 over the whole north half -- so they go that way.

    ⚠ SDA's STUB DROPS 0.35 BEFORE IT RUNS WEST, and that jog is not cosmetic. Straight
    out at pin 18's own y it passes SCL's via at dy -0.75 with 0.50 of clearance where a
    via needs 0.55 (0.3 annulus, 0.1 track, 0.15 rule). Short by 0.05.

    ⚠ A FEED MUST STAY ON F.Cu UNTIL IT REACHES ITS OWN SPINE, and that one rule is what
    lets the strip carry more than one bus. A horizontal running east at constant y
    crosses every spine between the pin and its destination, so on ONE layer only the
    innermost spine can be fed from the west. But a feed that stays on F.Cu and vias down
    AT its spine never touches B.Cu at all -- which is why I2C2_SCL and +3V3D have sat in
    the same lane for months without fouling each other, and it generalises: B.Cu holds as
    many spines as fit, F.Cu holds one, and each feed stops west of every F.Cu spine
    outboard of it. So FS takes the outermost lane on F.Cu and SCK and +3V3A sit inboard
    of it on B.Cu, each fed by an F.Cu horizontal that stops at its own via.

    Laying SCK's jog on B.Cu instead was tried first and is wrong for exactly this reason:
    it put a B.Cu horizontal across the strip and nothing else could share the layer.

    Jog depths are set by the Cs row's own ground vias at dy -5.04: a horizontal wants
    0.55 off those, so -6.00 is the first clear lane and the two buses take -6.00 and
    -6.60. The deeper one turns east from the WESTERN pin, so neither vertical crosses the
    other's horizontal -- the same ordering rule the comb lanes needed.
    """
    out = []
    for k in range(5):
        # SDA: west face, out past SCL's lane on F.Cu the whole way
        out += [("I2C2_SDA", "F.Cu", w,
                 [_cell_pt(k, -1.963, _SDA_DY), _cell_pt(k, -2.40, _SDA_DY)]),
                ("I2C2_SDA", "F.Cu", w,
                 [_cell_pt(k, -2.40, _SDA_DY), _cell_pt(k, -2.40, _SDA_JOG)]),
                ("I2C2_SDA", "F.Cu", w,
                 [_cell_pt(k, -2.40, _SDA_JOG), _cell_pt(k, _SDA_DX, _SDA_JOG)])]
        # FS: south face, the INNER east spine, F.Cu throughout
        out += [("SAI_FS", "F.Cu", w,
                 [_cell_pt(k, _FS_DX, _SAI_ROW), _cell_pt(k, _FS_DX, _FS_JOG)]),
                ("SAI_FS", "F.Cu", w,
                 [_cell_pt(k, _FS_DX, _FS_JOG), _cell_pt(k, _FS_SPINE, _FS_JOG)])]
        # SCK: south face, the OUTER east spine, so it hops to B.Cu at its own x
        out += [("SAI_SCK", "F.Cu", w,
                 [_cell_pt(k, _SCK_DX, _SAI_ROW), _cell_pt(k, _SCK_DX, _SCK_JOG)]),
                ("SAI_SCK", "F.Cu", w,
                 [_cell_pt(k, _SCK_DX, _SCK_JOG), _cell_pt(k, _SCK_SPINE, _SCK_JOG)])]
    # ⚠ AND SDA RUNS ON TO THE BORDER, FOR THE REASON SCL'S SPINE ALREADY DOES. It used to
    # stop at cell 4's jog, at y -14.49 -- 4.5 mm INSIDE the string array, among the comb
    # slots and their keepouts. The router has to reach a fixed wire's open end to adopt
    # it, and reaching that one means coming up into the array: measured, it did not. It
    # laid SDA from R51 all the way to U6.16 on In2 and left U18.18 and the whole spine as
    # a separate island, which is the ONE unconnected item on this net.
    # Every other bus here already hands over AT the line (_SD_BORDER); SDA was the one
    # that did not, because its spine was added later than the rule.
    out += [("I2C2_SDA", "F.Cu", spine_w,
             [_cell_pt(0, _SDA_DX, _SDA_JOG),
              (_cell_pt(4, _SDA_DX, _SDA_JOG)[0], _SD_BORDER)]),
            ("SAI_FS", "F.Cu", spine_w,
             [_cell_pt(0, _FS_SPINE, _FS_JOG), _cell_pt(4, _FS_SPINE, _FS_JOG)]),
            ("SAI_SCK", "B.Cu", spine_w,
             [_cell_pt(0, _SCK_SPINE, _SCK_JOG), _cell_pt(4, _SCK_SPINE, _SCK_JOG)])]
    return out


def _pin_escapes():
    """Escape vias for the pins the router leaves stranded -- see _PIN_ESCAPES.

    The first was SAI_FS at the MCU, the only one of its three
    neighbours that never got one (user spotted it in the routed board, 2026-09-25:
    "this disconnected net SAI_FS doesn't have a via but seems like it needs one").

    U6 pads 2/3/4 are SAI_SD2 / SAI_FS / SAI_SCK on a 0.5 mm pitch. The router escaped
    SD2 at (-5.35, -26.81) and SD1 at (-5.36, -28.02) -- 1.21 mm apart, and two 0.6 vias
    need 0.8 mm from each other, so there is no room for a THIRD between them. SAI_FS was
    left on F.Cu and had to cross a pin field that is full on both sides (east is those
    two vias, west is +3V3D's and SAI_SCK's surface runs), so it failed in every routing
    this board has had -- five layouts, every corridor width, 10 passes and 50.

    ⚠ MEASURED INTO A VERIFIED-EMPTY SITE, as every declared via on this board must be:
    (-5.73, -27.09) is 0.85 mm from the pad and the nearest clear position to it, scanned
    against the UNROUTED board (pads and declared copper) at 0.05 mm steps. It is inside
    where SD2's escape landed, which is the point -- claiming the lane for the net that
    cannot route pushes the two that can onto their own, and they have the whole belly.

    The stub is laid WITH the via, not left for the router: an orphan via never gets
    adopted on this board, so the pad reaches the via on F.Cu here and the router only
    has to leave from the via on an inner layer. Same shape as _stitch_plane_pads.
    """
    return _escapes(_PIN_ESCAPES)


# ⚠ THE NETS THAT FAIL ARE THE NETS WITH NO ESCAPE VIA. The user read three routings and
# found the same thing each time (2026-09-25): "this disconnected net SAI_FS doesn't have
# a via but seems like it needs one", then "5 ULPI_D1 is also disconnected and has no via",
# then "ditto for 11 ULPI_D6". Every one of them is a pin whose neighbours took the escape
# positions first and left it stranded on F.Cu in a pin field that is full on both sides.
# It is not three coincidences; it is one mechanism, and the router does not go back and
# make room once a lane is spent.
# Each site was SCANNED against the unrouted board (pads + declared copper) at 0.05 mm
# steps out from the pad, so it is measured rather than chosen -- the discipline every
# declared via on this board needs, since none of them are clearance-checked when laid.
#   pad                     via                  what it unblocks
def _bus_vias():
    """SAI_SCK's hop to B.Cu, one per converter, AT the spine and not at the pin -- the
    feed has to stay on F.Cu the whole way across. See _bus_spines."""
    return [("SAI_SCK",) + _cell_pt(k, _SCK_SPINE, _SCK_JOG) for k in range(5)]


# +3V3A's lanes. The op-amp side goes 0.65 WEST of the Cd column and drops south of the
# package before it dives, into the 1.3 mm corridor between Cd's own stitching via at
# -19.28 and MID's pin-3 via at -20.58.
# ⚠ IT MUST NOT GO EAST. 1.38 east puts the drop at -17.901, which is 0.11 from the
# Rf*B.1 column -- and that is the one place TIA_IN_B's inner hop can put a via. The
# summing node reaches its feedback resistor only through that hop, the op-amp's own
# pin row being between them, so nine strings lost it. A power rail has the whole
# board and the summing node has 0.97 mm; the rail yields. The older note stands:
# of the B channel's escape vias at -18.54 rather than 0.06 from them -- 0.68 was the
# first try and DRC caught it shorting TIA_OUT_*B on all ten strings. A via needs 0.60
# (0.3 annulus, 0.15 spine, 0.15 rule) and the gap west of those vias is only 0.19.
# The rest of the note stands: there is no room on the
# 1.283 mm stub between pin 8 and Cd (0.163 mm of gap, against the 0.9 a 0.6 via needs), and
# nothing else in the tile is clear -- the B-channel's own escape vias sit at x -18.54.
_V3A_DX = -0.80
_V3A_SPINE = 5.30           # converter side, INBOARD of SAI_FS at 7.20: see _bus_spines
_V3A_CS_DY = -3.27          # the Cs*1 row, +3V3A's pad in each cell


def _v3a_spine(w=0.2, spine_w=0.3):
    """+3V3A: the analogue rail, ten op-amp stations and five converter stations.

    ⚠ THE LAST NET REACHING NORTH OF THE BORDER, and the largest: 15 islands, 13 ratlines.
    Every station is internally fine -- pin 8 to its own Cd, one 1.283 mm stub -- and
    nothing joins the stations to each other. This was mis-read once as unconnected bypass
    caps (the island report prints "Cd1.1,U21.8" as ONE island, a connected pair, and it
    was read as two); the caps were never the problem. The rail between them was missing.

    ⚠ IT HAS TO BE B.Cu, and that is measured rather than assumed. The op-amp column is
    the obvious lane and cannot be used: pin 8 shares its x with pin 1, TIA_OUT_A, on the
    other row, and the column between two stations is blocked by Cd's ground pad, Cd's
    stitching via and the next op-amp's pin 1. Every neighbouring F.Cu lane is crossed
    once per string by the A channel's own feedback:

        x -18.60   the B channel's escape vias at -18.54, 0.06 away
        x -18.90   0.131 to pin 8's pad edge, against the 0.25 a track needs
        Rf..Cf     four crossings per string, TIA_IN and TIA_OUT, both halves
        east of Cf the two TIA_OUT runs heading for the comb

    In2 is no better: the B channel's two diagonals cross the column at every string. So
    the rail goes under everything on B.Cu and pays a via per station, which is what a
    power rail costs when the signal layers are full. The local bypass is unaffected --
    each Cd still sits against its own pin 8 on F.Cu, which is the part that matters.
    """
    P = _placements(CX, CY)
    strings = [n for n in range(1, 11) if ("Cd%d" % n) in P]
    cds = sorted(((n, P["Cd%d" % n]) for n in strings), key=lambda kv: -kv[1][1])
    assert cds, "no op-amp decoupling caps placed -- did Cd get renamed?"

    # Cd's +3V3A land is its north pad; read the offset back rather than assuming it
    cd_y = lambda q: q[1] + 0.48
    x = cds[0][1][0] + _V3A_DX
    out = [("+3V3A", "B.Cu", spine_w,
            [(x, cd_y(cds[0][1]) - _V3A_DROP), (x, cd_y(cds[-1][1]) - _V3A_DROP)])]
    for _n, q in cds:
        out += [("+3V3A", "F.Cu", w, [(q[0], cd_y(q)), (x, cd_y(q))]),
                ("+3V3A", "F.Cu", w, [(x, cd_y(q)), (x, cd_y(q) - _V3A_DROP)])]

    # the converter stations, same shape one lane in from SAI_FS
    for k in range(5):
        out.append(("+3V3A", "F.Cu", w,
                    [_cell_pt(k, 3.10, _V3A_CS_DY), _cell_pt(k, _V3A_SPINE, _V3A_CS_DY)]))
    out.append(("+3V3A", "B.Cu", spine_w,
                [_cell_pt(0, _V3A_SPINE, _V3A_CS_DY), _cell_pt(4, _V3A_SPINE, _V3A_CS_DY)]))

    # ⚠ ONE LINK BETWEEN THE TWO GROUPS, at the SOUTH end where both already finish. The
    # op-amp column bottoms out at string 10's Cd and the converter column at cell 5's Cs,
    # 1.06 mm apart in y and both within 3 mm of the border, so the crossing is a single
    # B.Cu run under the bottom of the comb field rather than a second trip up the board.
    # ⚠ THE LINK DROPS 1.0 BELOW Cd10 BEFORE IT RUNS EAST. Straight across at Cd10's own y
    # it clips the BOTTOM EDGE OF SLOT 10 -- the comb slots are milled openings, not just
    # keepouts, so that is a copper-to-edge violation and not a clearance one. y -18.2 is
    # below every slot and still 0.8 north of the border.
    # ⚠ BELOW EVERY ESCAPE JOG, not between two of them. At -1.385 the east via sat
    # 0.289 from SAI_FS's jog, and the window between that jog and the Cs row's
    # ground vias is 0.96 where a via and a track need 1.15. There is no lane in
    # there; going under the lot costs nothing but 3.4 mm of B.Cu.
    y_lnk = cd_y(cds[-1][1]) - 3.385
    xe = _cell_pt(4, _V3A_SPINE, _V3A_CS_DY)[0]
    # ⚠ THE CROSSING IS ON In2, NOT B.Cu. B.Cu carries I2C2_SCL's and +3V3D's spines down
    # the west of the converter column and both now run to the border, so a B.Cu run east
    # from the op-amps hits them. In2 is empty along the bottom of the comb field -- the
    # comb's own lanes all sit north of -17.2 -- so the link vias through and crosses
    # there, and the two vias are the only ones the whole east-west journey costs.
    out += [("+3V3A", "B.Cu", spine_w,
             [(x, cd_y(cds[-1][1]) - _V3A_DROP), (x, y_lnk)]),
            ("+3V3A", "In2.Cu", spine_w, [(x, y_lnk), (xe, y_lnk)]),
            ("+3V3A", "B.Cu", spine_w, [(xe, y_lnk), _cell_pt(4, _V3A_SPINE, _V3A_CS_DY)])]
    return out


def _v3a_vias():
    """One via per +3V3A station: ten op-amps, five converters. See _v3a_spine."""
    P = _placements(CX, CY)
    out = [("+3V3A", P["Cd%d" % n][0] + _V3A_DX, P["Cd%d" % n][1] + 0.48 - _V3A_DROP)
           for n in range(1, 11) if ("Cd%d" % n) in P]
    out += [("+3V3A",) + _cell_pt(k, _V3A_SPINE, _V3A_CS_DY) for k in range(5)]
    # the two ends of the In2 crossing -- see the note in _v3a_spine
    cd = sorted((P["Cd%d" % n] for n in range(1, 11) if ("Cd%d" % n) in P),
                key=lambda q: q[1])[0]
    y_lnk = cd[1] + 0.48 - 3.385
    out += [("+3V3A", cd[0] + _V3A_DX, y_lnk),
            ("+3V3A", _cell_pt(4, _V3A_SPINE, _V3A_CS_DY)[0], y_lnk)]
    return out


def _sd_spines(w=0.2, spine_w=0.25):
    """SAI_SD1..4: the serial data lines, each from its own converter down to the border.

    ⚠ THESE WERE THE LONG DIAGONALS ACROSS THE ARRAY (user, 2026-09-24: "the rest stretch
    from the south, those should go to the border instead"). Each SDn is point to point --
    one converter's pin 21 to one MCU pin -- so it has exactly two pads and no reason to
    fail a connectivity check, and it had NO north copper at all. The ratsnest therefore
    drew it as a single line from the converter to the far south, straight over the string
    array. Counting ratlines told us nothing about it: the net has one connection and it
    crosses the border, which is the finished state for every OTHER crossing net. What
    matters is WHERE it hands over, and it was handing over 79 mm too far north.

    SD5 is left alone. Its converter is the southern one and its pad is already 4.15 mm
    from the border, which is the handover.

    ⚠ THE NORTHERN CELL TAKES THE OUTER LANE, which is the opposite of the intuition. Each
    spine runs from its own cell SOUTHWARD, so at cell k's y the spines of cells k+1.. do
    not exist yet -- only the ones from cells further north are in the way. Feeding the
    northern cell outermost means every feed reaches its lane without meeting a spine that
    has started. Reversed, cell 3's feed would cross all three of its neighbours.

    ⚠ AND ONLY ONE SPINE IN THE STRIP CAN LIVE ON F.Cu. A feed crosses every same-layer
    spine between the pin and its lane, so F.Cu holds exactly one and it has to be the
    OUTERMOST -- SAI_FS, moved out to 10.60 for this. Everything else sits inboard on B.Cu
    fed by an F.Cu horizontal that vias down at its own lane, which crosses nothing.
    """
    out = []
    for k, dx in enumerate(_SD_SPINE):
        net = "SAI_SD%d" % (k + 1)
        x, y0 = _cell_pt(k, dx, _SD_JOG)
        out += [(net, "F.Cu", w,
                 [_cell_pt(k, _SD_DX, _SAI_ROW), _cell_pt(k, _SD_DX, _SD_JOG)]),
                (net, "F.Cu", w, [_cell_pt(k, _SD_DX, _SD_JOG), (x, y0)]),
                (net, "B.Cu", spine_w, [(x, y0), (x, _SD_BORDER)])]
    return out


def _sd_vias():
    """One via per SAI_SD lane, at the lane and not at the pin. See _sd_spines."""
    return [("SAI_SD%d" % (k + 1),) + _cell_pt(k, dx, _SD_JOG)
            for k, dx in enumerate(_SD_SPINE)]


def _door_keepout(pad=0.55, lo=0.50, hi=1.80):
    """Fence the stitcher out of the coupling caps' DOORS.

    Every TIA output reaches its coupling cap through the gap between two Cm pads -- Ci
    sits on a 1.2 mm pitch and Cm on the same pitch offset 0.8, so each Ci pad has a
    0.64 mm window straight above it and that window is the only way in (Ci's south pad
    belongs to the converter, and its north pad has 0.52 mm to the Cm row).

    The stitcher does not know that. It places a ground via 0.9 off each pad it grounds
    and knows nothing about what the space is for, and in FOUR of the five cells it put
    one in a door: 0.23 mm off the centre line against the 0.55 a 0.2 track needs. That
    is the whole reason those four runs could not be laid -- 740 candidates each, all
    stopped on the same last leg, while the one cell whose door happened to stay clear
    laid first try.

    Narrow strips at the door x, NOT a band across the row: the Cm caps' own GND vias sit
    between the doors and are the thing being fenced off FROM, so a band would cost every
    one of them its ground. Read back from the placed parts by reference so the fence
    cannot drift off the door it is fencing.
    """
    P = _placements(CX, CY)
    out = []
    for k in range(1, 6):
        for i in range(1, 5):
            ci = P.get("Ci%d%d" % (k, i))
            cm = P.get("Cm%d%d" % (k, i))
            if ci is None or cm is None:
                continue
            out.append([round(ci[0] - pad, 4), round(min(ci[1], cm[1]) + lo, 4),
                        round(ci[0] + pad, 4), round(max(ci[1], cm[1]) + hi, 4)])
    assert len(out) == 20, "expected one door per channel, got %d" % len(out)
    return out


def _v5_spine(spine_w=0.8, tap_w=0.3, dx=-2.94):
    """V5_PRE's NORTH HALF, laid: one spine down the reserved lane, one tap per ballast.

    ⚠ THE NORTH SIDE SHOULD NOT BE THE ROUTER'S JOB AT ALL (user, 2026-09-24: "we should
    route V5_PRE up to the border point"). V5_PRE had ZERO pre-laid copper, so the router
    was drawing the whole thing -- ten ballast feeds scattered the length of a 90 mm array
    -- and its ratsnest sprawled across every string. It is a RAIL: nine pads in a straight
    column at one x, on the string pitch. A spine and nine taps is the whole net.

    WHERE IT RUNS: the lane west of the detector lands that the board's own edge was pinned
    to (see V5_LANE in src/optical_pickup.py). That lane exists precisely because this rail
    needs it, and until now nothing put the rail in it. 5.3 mm of clear board, and each
    ballast sits midway between two strings with 0.88 mm to the nearest detector land, so
    every tap crosses open board.

    ⚠ IT STOPS AT THE SOUTHERNMOST BALLAST, NOT AT AN IMAGINARY LINE. The border wanted
    here is a place the ROUTER can pick the net up from, and this file records twice that
    it will not: _sai_escape laid exactly this shape and every part came back open ("the
    router never connected to a pre-laid via on this board"), and the corridor generator
    failed three times the same way. Copper that reaches no pad is not adopted. Ending on
    R10's pad makes the whole north half one connected piece hanging off a real pad, and
    the router's remaining job is one hop from there to the buck.

    Widths: the spine carries all ten emitters (1068 mA worst case) and each tap carries
    one (107 mA).
    """
    P = _placements(CX, CY)
    rs = sorted(((r, P[r]) for r in ("R%d" % i for i in range(1, 11)) if r in P),
                key=lambda kv: -kv[1][1])
    if not rs:
        return []
    # pad 1 sits 0.51 west of the part's centre (0402 on its side); read back, not assumed
    pad = lambda q: (q[0] - 0.51, q[1])
    x = pad(rs[0][1])[0] + dx
    out = [("V5_PRE", "F.Cu", spine_w,
            [(x, pad(rs[0][1])[1]), (x, pad(rs[-1][1])[1])])]
    for _, q in rs:
        px, py = pad(q)
        out.append(("V5_PRE", "F.Cu", tap_w, [(x, py), (px, py)]))
    return out


_LED_VIA_DX = -0.913     # LED_ROW surfaces BETWEEN MID's anode link and D*.1


def _led_row_spine(spine_w=0.8, tap_w=0.3, dx=-1.36):
    """LED_ROW's north half: the emitters' switched low side, one spine and ten taps.

    Same shape as _v5_spine and the same reason -- it is a rail with ten pads in a column
    and the router was drawing all ten feeds. It carries the whole emitter string, so the
    spine is sized like V5_PRE's.

    ⚠ IT CANNOT RUN AT THE PADS' OWN x, which is the obvious thing to try since all ten are
    collinear at -25.24: that column passes straight through the detector lands, which span
    -27.31..-22.31. So the spine sits in its own lane WEST of the detectors, outboard of
    V5_PRE's, and taps east to each emitter.

    ⚠ AND IT RUNS ON In2 UNDER THE DETECTOR COLUMN, WHICH IS THE ONLY PLACE IT FITS.
    Two earlier attempts put it west of the detectors alongside V5_PRE, and BOTH were off
    the board: the lane between the outline and the detector lands is 1.296 mm -- exactly
    V5_LANE, sized for ONE 0.8 track -- and there was never room for a second rail there.
    The error came from reading the west edge off GetBoardEdgesBoundingBox(), which
    includes the jack-access notch hanging 1.8 mm past the outline, so the board looked
    4 mm wider than it is. The user caught it in the render by toggling In2. ASK THE
    OUTLINE SEGMENTS, not the bounding box -- the same lesson _i2c_spine records, one note
    above, about a spine that ended up 0.22 mm off the edge.

      board west edge (Edge.Cuts)      -28.606
      V5_PRE spine, in its own lane    -27.900
      detector lands                   -27.310 .. -22.310
      LED_ROW spine, UNDER them        -26.600   (In2, no tracks there at all)

    In2 is empty under the detectors -- every local link is F.Cu and the comb crossings all
    begin east of the feedback caps -- and the detectors are SMD, so they obstruct nothing
    on an inner layer. The rail surfaces on its own spine at each emitter's y and crosses
    the last 1.36 mm on F.Cu, through the 1.0 mm gap the string's two detectors leave.
    The taps cross the detector band at the STRING's own y, where the two detectors of that
    string (at string_y +-2.15, land half-height 1.65) leave a 1.0 mm gap -- 0.35 mm of
    clearance either side of a 0.3 track. Tight and real; if a detector land ever grows,
    this is the first thing that breaks.
    """
    P = _placements(CX, CY)
    ds = sorted(((r, P[r]) for r in ("D%d" % i for i in range(1, 11)) if r in P),
                key=lambda kv: -kv[1][1])
    if not ds:
        return []
    # pad 1 sits 0.79 west of the emitter's centre; read back from the placement, not assumed
    pad = lambda q: (q[0] - 0.79, q[1])
    x = pad(ds[0][1])[0] + dx
    # the spine carries on to the border rather than stopping at D10: same reason as
    # _i2c_spine's, and In2 is empty down there.
    out = [("LED_ROW", "In2.Cu", spine_w,
            [(x, pad(ds[0][1])[1]), (x, _SD_BORDER)])]
    for _, q in ds:
        px, py = pad(q)
        out.append(("LED_ROW", "In2.Cu", tap_w, [(x, py), (px + _LED_VIA_DX, py)]))
        out.append(("LED_ROW", "F.Cu", tap_w, [(px + _LED_VIA_DX, py), (px, py)]))
    return out


def _led_row_vias():
    """The via per emitter where LED_ROW surfaces, east of V5_PRE's spine."""
    P = _placements(CX, CY)
    return [("LED_ROW", P[r][0] - 0.79 + _LED_VIA_DX, P[r][1])
            for r in ("D%d" % i for i in range(1, 11)) if r in P]


# MID's lanes, all measured against things that are already on the board.
#   _MID_VIA_DX    east of the anode column, clear of LED_ROW's In2 spine at -26.60 and
#                  west of the emitter's land at -25.24
#   _MID_VIA_DROP  below the lowest anode land, into the 0.931 window above the V5_PRE tap
#   _MID_P5_DX     west of pin 5, clear of its land and of TIA_IN_B's run above it
#   _MID_P3_DY     north of pin 3, above pin 4's land rather than beside it
# ⚠ EVERY ONE OF THESE IS SET BY A VIA, not by a pad, and three of the four were wrong
# on the first pass. Two 0.6 vias need 0.75 between centres and a via to a 0.25 track
# needs 0.575, and the neighbourhood is dense with the stitcher's own ground vias:
#   _MID_VIA_DX    1.10 east of the anode column, clear of LED_ROW's surfacing via
#                  at -26.15 by 0.79 (0.756 put the B.Cu spine 0.287 from it)
#   _MID_VIA_DROP  below the lowest anode land, into the 0.931 window above V5_PRE
#   _MID_P5_DX     west of pin 5, under TIA_IN_B's run
#   _MID_P3_DY     2.40 north of pin 3, clear of PIN 4's stitching via, which sits
#                  1.313 north of pin 4 and left only 0.673 at the first value
_MID_VIA_DX, _MID_VIA_DROP = 1.100, 0.970
_MID_P5_DX = 1.744
# ⚠ PIN 3's VIA IS 0.9 OFF PIN 3's COLUMN, and that offset is the whole of TIA_IN_B.
# _hop_via_inner needs a STRAIGHT stub from pad to via, and pin 6 is boxed in by
# pins 5 and 7 on its own row -- so its only straight escape is due south, down its
# own column. Pin 3 shares that column (both are op_x - _OP_PIN_DX), so a via sitting
# 2.4 north of pin 3 lands 2.738 south of the NEXT string's pin 6 and corks it. Nine
# strings lost their summing node to it. There is 1.94 mm of room down there; the
# column was simply occupied.
#
# Inside the package was tried instead and is worse (9 unlaid -> 18): the interior is
# where TIA_IN_A's escape goes, so that just moves the cork to the A channel.
_MID_P3_DX, _MID_P3_DY, _MID_P3_MID = 0.900, 2.964, 2.014
# the anode link rides the WEST side of its own lands, to leave LED_ROW's via room
_MID_COL_DX = -0.394
# ⚠ +3V3A's op-amp via DROPS clear of the feedback band before it dives. Sitting
# at Cd's own y it lands 0.79 from where TIA_IN_B's inner hop needs ITS via, and
# that hop is the only way the B channel's summing node reaches its feedback
# resistor -- the pin row is between them. Nine strings lost it that way.
# ⚠ MEASURED FROM Cd, SO IT MOVES WHEN Cd DOES. Correcting VSSOP-8's courtyard took
# Cd 0.475 south and this drop went with it, straight onto the NEXT op-amp's A row:
# 2.55 became 2.075 to put the via back where it was. If Cd moves again, this
# follows it, and the thing it must stay clear of is the A row below, not Cd.
_V3A_DROP = 1.000

# TLV9062 land geometry, read off the placed board rather than the datasheet drawing:
# 0.65 pitch, the two pin rows 4.225 apart. MID is pins 3 and 5, which sit on OPPOSITE
# rows and at different x -- pin 3 shares its x with pin 6 (TIA_IN_B) and pin 5 shares its
# x with pin 4 (GND), so neither x is a free north-south lane THROUGH a package. The chain
# below runs at pin 3's x BETWEEN packages and jogs west before it reaches the next pin 6.
_OP_PIN_DX, _OP_ROW_DY = 0.325, 2.1125


def _mid_spine(spine_w=0.3, w=0.25):
    """MID: the bias reference, on B.Cu, three vias per string.

    ⚠ IT EXISTS TO GET MID OUT OF THE SUMMING NODE'S LANE. In local_nets the MST linked
    each string's anodes to its own op-amp, ten crossings of the only lane TIA_IN_*B has,
    clearing it by 0.167 where 0.3 is needed. A DC bias reference feeding picoamps had the
    short path and a 1 Mohm summing node did not. Putting MID back in local_nets was tried
    again (2026-09-24) after TIA_IN_B got a clean route and was laid first: the MST went
    straight back to the same crossing and dropped all ten B channels. The spine stays.

    ⚠ AND IT HAS TO BE B.Cu, WHICH THE FIRST VERSION OF THIS FUNCTION DENIED. That version
    ran an F.Cu spine down the anode column and chained the op-amps on F.Cu, and it was
    committed without a DRC run. It was wrong in three places, each of them a short:

      the anode column      crosses EVERY V5_PRE tap. The taps run from the rail at
                            -27.90 east to each ballast at -24.96, so they cross the
                            anode lands at -26.46 whatever x the spine takes. There is no
                            F.Cu lane down that column, only the illusion of one.
      pin 5 -> pin 3        crosses TIA_IN_B. The two MID pins are on OPPOSITE rows and
                            TIA_IN_B's run to pin 6 passes between them; going round is
                            worse, since pin 3 shares its row with pin 4 (GND) to the west
                            and pin 2 (TIA_IN_A) to the east.
      the inter-string run  lands 0.414 from the TIA_OUT_B escape vias, against 0.55.

    B.Cu has none of those problems because it has no pads: V5_PRE is F.Cu, LED_ROW is
    In2, and the op-amp's own pins obstruct nothing on the bottom layer. Only vias block,
    and the lanes here clear every one. Three vias per string is what that costs -- the
    anode group, pin 5 and pin 3 -- and on a DC reference it costs nothing electrically.
    Each op-amp still has its own Cd against pin 8 on F.Cu, which is the part that matters.

    ⚠ THE ANODE VIA GOES SOUTH OF THE DETECTOR, NOT BESIDE IT. The column looks like it
    has room and has none: between LED_ROW's In2 spine at -26.60 and D*.1's land at
    -25.24 the window is 0.523 and a 0.6 via needs 0.9, and the gaps between the detector
    lands themselves are 0.4 and 0.475. The one opening is between the lower detector's
    bottom land and the V5_PRE tap below it -- 0.931, which a via fits by 0.031.
    """
    P = _placements(CX, CY)
    strings = [n for n in range(1, 11)
               if ("PD%dA" % n) in P and ("PD%dB" % n) in P and ("U%d" % (20 + n)) in P]
    assert strings, "no detector/op-amp pairs placed -- did the refs change?"

    ax = P["PD%dA" % strings[0]][0] - 1.65          # the anode lands' own column
    vx = ax + _MID_VIA_DX
    ys = lambda n: sorted(P["PD%d%s" % (n, h)][1] + dy for h in "AB" for dy in (0.70, -0.70))
    via_y = lambda n: ys(n)[0] - _MID_VIA_DROP
    op = lambda n: P["U%d" % (20 + n)]
    pin5 = lambda n: (op(n)[0] - 3 * _OP_PIN_DX, op(n)[1] - _OP_ROW_DY)
    pin3 = lambda n: (op(n)[0] - _OP_PIN_DX, op(n)[1] + _OP_ROW_DY)
    v5 = lambda n: (op(n)[0] - _MID_P5_DX, pin5(n)[1])
    v3 = lambda n: (pin3(n)[0] - _MID_P3_DX, pin3(n)[1] + _MID_P3_DY)

    order = sorted(strings, key=lambda n: -op(n)[1])
    out = [("MID", "B.Cu", spine_w,
            [(vx, via_y(order[0])), (vx, via_y(order[-1]))])]
    for n in strings:
        col = ys(n)
        cx = ax + _MID_COL_DX
        out += [("MID", "F.Cu", w, [(cx, col[-1]), (cx, via_y(n))]),
                ("MID", "F.Cu", w, [(cx, via_y(n)), (vx, via_y(n))]),
                ("MID", "B.Cu", w, [(vx, via_y(n)), v5(n)]),
                ("MID", "F.Cu", w, [v5(n), pin5(n)]),
                # ⚠ AN L, NOT A DIAGONAL. Straight between the two vias the run passes
                # 0.408 from PIN 4's stitching via, against 0.575. North first in pin
                # 5's own lane, which clears it by 0.769, then east above it.
                ("MID", "B.Cu", w, [v5(n), (v5(n)[0], v3(n)[1])]),
                ("MID", "B.Cu", w, [(v5(n)[0], v3(n)[1]), v3(n)]),
                # down its own lane, east 0.354 clear of pin 4's land and 0.552 clear of
                # pin 4's stitching via, then south into pin 3
                ("MID", "F.Cu", w, [v3(n), (v3(n)[0], pin3(n)[1] + _MID_P3_MID)]),
                ("MID", "F.Cu", w, [(v3(n)[0], pin3(n)[1] + _MID_P3_MID),
                                    (pin3(n)[0], pin3(n)[1] + _MID_P3_MID)]),
                ("MID", "F.Cu", w, [(pin3(n)[0], pin3(n)[1] + _MID_P3_MID), pin3(n)])]
    return out


def _mid_vias():
    """Three per string: the anode group, pin 5 and pin 3. See _mid_spine for why none of
    the three can be reached on a signal layer."""
    P = _placements(CX, CY)
    out = []
    for n in range(1, 11):
        if ("PD%dA" % n) not in P or ("U%d" % (20 + n)) not in P:
            continue
        ax = P["PD%dA" % n][0] - 1.65
        lo = min(P["PD%d%s" % (n, h)][1] + dy for h in "AB" for dy in (0.70, -0.70))
        ux, uy = P["U%d" % (20 + n)][0], P["U%d" % (20 + n)][1]
        out += [("MID", ax + _MID_VIA_DX, lo - _MID_VIA_DROP),
                ("MID", ux - _MID_P5_DX, uy - _OP_ROW_DY),
                ("MID", ux - _OP_PIN_DX - _MID_P3_DX, uy + _OP_ROW_DY + _MID_P3_DY)]
    return out


def _spine_keepout(via_d=0.6, clr=0.127):
    """Fence the stitcher off the B.Cu spines, sized from where the spines actually are.

    The stitcher places a ground via 0.9 off its pad and knows nothing about pre-laid
    copper; left alone it dropped one onto the +3V3D trunk at 0.100 mm. Excluding the pad
    would cost that cap its ground, so the lane is fenced and the stitch kept."""
    # ⚠ ONE BOX PER SPINE, NOT ONE BOX OVER ALL OF THEM. The first version took the
    # bounding box of every B.Cu run at once, which was invisible while the only two
    # spines were 0.93 apart and became a 10 mm wall the moment SAI_SCK's spine went into
    # the empty strip east of the converters: 28 Cs caps lost their stitching via to a
    # fence around copper that is nowhere near them.
    runs = [t for t in _cell_tracks()
            if t[1] == "B.Cu" and abs(t[3][0][1] - t[3][1][1]) > 10.0]
    assert runs, "no B.Cu spine to fence -- did the trunks move layer?"
    pad = via_d / 2 + clr
    out = []
    for t in runs:
        x0, x1 = t[3][0][0] - t[2] / 2, t[3][0][0] + t[2] / 2
        ys = (t[3][0][1], t[3][1][1])
        out.append([x0 - pad, min(ys) - pad, x1 + pad, max(ys) + pad])
    return out


def _fan_tracks():
    out = []
    near, far = OP.CELL_NEAR - 0.48, OP.CELL_FAR - 0.48
    for k in range(5):
        for name, pin_x, row in (("IN4P", -1.25, near), ("IN3M", -0.75, far),
                                 ("IN3P", -0.25, near), ("IN2M", 0.25, far),
                                 ("IN2P", 0.75, near), ("IN1M", 1.25, far)):
            cx = OP.CELL_FAN[name]
            d = cx - pin_x
            pts = [(pin_x, 1.96), (pin_x, 2.60), (cx, 2.60 + abs(d)), (cx, row)]
            out.append(("ADC%d_%s" % (k + 1, name), "F.Cu", 0.15,
                        [_cell_pt(k, x, y) for x, y in pts]))
        for name, (px, py), row in (("IN1P", (1.96, 1.25), near),
                                    ("IN4M", (-1.96, 1.25), far)):   # IN4M's cap: far row
            cx = OP.CELL_FAN[name]
            out.append(("ADC%d_%s" % (k + 1, name), "F.Cu", 0.15,
                        [_cell_pt(k, px, py), _cell_pt(k, cx, py), _cell_pt(k, cx, row)]))
    return out


def _sai_escape(k):
    """(net, pin x, via x, via y) for converter k's three SAI pins, part turned 180: SDOUT
    (pin 21, x -0.25), BCLK (22, +0.25), FSYNC (23, +0.75) leave the bottom corridor between
    the IOVDD and DREG caps. With all three left to the router the middle one, BCLK, was
    walled in by the other two in every routing (and repair_search found no path): so
    SDOUT and FSYNC drop to vias side by side and BCLK threads down between them to a
    lower one. Clearances: 0.19 to the IOVDD cap, 0.34 to DREG's, 0.19 either side of BCLK.
    ⚠ TRIED AND REVERTED, 2026-09-22: laid, SCK and FS failed at EVERY part (17 open) --
    the router never connected to a pre-laid via on this board, SHDNZ's either. Kept for
    the record; nothing calls it."""
    return (("SAI_SD%d" % (k + 1), -0.25, -0.45, -3.40),
            ("SAI_SCK", 0.25, 0.25, -4.40),
            ("SAI_FS", 0.75, 0.95, -3.40))


def _shdn_tracks():
    """Each converter's SHDNZ to its own IOVDD: pin 14 (-1.96, +0.75) -> via at (_V3_CH_DX, +0.75)
    -> In2 down the channel -> via at (_V3_CH_DX, -3.27) -> the IOVDD cap Cs<k>8's rail pad at
    (-1.25, -3.27). Offsets from the part's centre, part turned 180."""
    out = []
    for k in range(5):
        P = lambda dx, dy, k=k: _cell_pt(k, dx, dy)
        # ⚠ THE STUB FROM PIN 14 IS GONE FROM HERE, and it is the one thing in this
        # routine that is no longer +3V3D. SHDNZ is pulled up per cell now (see THE
        # CONVERTERS), so pin 14 belongs to SHDNZ<k> and reaches +3V3D only THROUGH the
        # resistor. Both of its stubs -- pin 14 to the resistor, and the resistor to this
        # channel -- are laid AFTER routing in repair_tracks, for the same reason the
        # bring-up pads are placed then: the resistor is invisible to the router, so a
        # site verified clear on the finished board cannot be perturbed by it.
        # ⚠ AND THE CHANNEL ITSELF IS GONE WITH IT, WHICH THE FIRST ATTEMPT DID NOT DO.
        # This channel existed for ONE purpose -- carrying pin 14 to IOVDD -- so with the
        # pull-up in the way it feeds nothing. Left in place it did real damage twice:
        # its head via went DANGLING and tidy_router_vias removed it, which orphaned the
        # B.Cu run and read as ten unconnected +3V3D items; and when a repair track was
        # attached to keep the via alive, the via came back as an obstacle SITTING IN THE
        # ONLY ESCAPE FROM PIN 14 -- five shorts, SHDNZ against +3V3D, and no track width
        # clears a 0.6 mm via 0.383 mm off the centreline. The pull-up reaches IOVDD by
        # its own post-route hop instead (see _shdnz_stubs).
        # ⚠ WHAT STAYS IS THE FOOT, AND IT IS NOT OPTIONAL: _v3_trunk's B.Cu spine lands on
        # exactly this point in every cell, so the foot via and the F.Cu run to the cap pad
        # are how each converter's IOVDD reaches the digital rail at all. Only the HEAD via
        # and the B.Cu leg up to pin 14 are dead. Removing the foot with them would have
        # disconnected all five converters' supply -- it was written that way for one edit
        # and caught by reading _v3_trunk rather than by any check.
        out += [("+3V3D", "F.Cu", 0.15, [P(_V3_CH_DX, -3.27), P(-1.25, -3.27)]),
                # and IOVDD's own pin 19 straight down onto that same pad
                ("+3V3D", "F.Cu", 0.2, [P(-1.25, -1.96), P(-1.25, -3.27)])]
    return out


# ⚠ THE SHDNZ PULL-UPS' TWO STUBS PER CELL, LAID AFTER ROUTING. One cell-frame path,
# copied five times by _cell_pt, exactly as _shdn_tracks does for the channel it replaces.
# They are repairs rather than declared copper for the reason the bring-up pads are placed
# late: the resistor is invisible to the router, so a path verified clear on the FINISHED
# board cannot be perturbed by it -- and unlike declared copper, everything here is checked
# (audit_board re-walks every segment of every repair, and DRC sees all of it).
#   SHDNZ<k>  converter pin 14 -> the pull-up's pad 1
#   +3V3D     the pull-up's pad 2 -> the via at the head of the existing IOVDD channel,
#             which is why that via stops dangling and the rail closes again
# ⚠ MAZED AGAINST THE FINISHED BOARD AT 0.05 mm AND VERIFIED CONTINUOUSLY AT 0.02 mm.
# SHDNZ leaves pin 14 westward, under the part's own IN4M pad at 0.360 mm -- a DC-static
# line beside an AC-grounded analog input, which is why 0.36 is comfortable rather than
# marginal -- and climbs to the resistor's south pad. +3V3D leaves the north pad, goes
# AROUND the west side and back down to the head of the existing IOVDD channel at
# (_V3_CH_DX, +0.75), which is also what stops that via dangling now that pin 14 no longer
# feeds it. Worst gap on either path 0.360 mm against the 0.127 rule.
# ⚠ THE SECOND PATH HAD TO BE SEARCHED AGAINST THE FIRST. Mazed independently they cross:
# the router cannot see copper that has not been laid yet, so SHDNZ went down with lay.py
# and +3V3D was searched against a board carrying it. Its first path ran at x 9.1 and its
# second goes round at x 7.7.
_SHDNZ_STUB = [(-1.962, 0.750), (-2.510, 0.751), (-3.460, 1.701), (-3.462, 2.240)]
# ⚠ AND +3V3D TAKES ONE VIA AND THE BACK SIDE, because there is no surface path at all.
# Asked with a 500 mm penalty per layer change, the maze still needs a hop: the corridor
# south from the pull-up to the rail is the converter's own west pad row. B.Cu and NOT In2
# -- the note on the channel this replaces says why, and it is the same reason now: on In2
# a run down the cell fences the one free signal layer off between every pair of cells,
# while on B.Cu it costs a GND pour a slot.
# ⚠ ONE VIA, NOT TWO: the maze's second via landed 0.52 mm from the foot via and the
# laminate between them came out at -0.080 mm. A through via IS a B.Cu landing, so the run
# ends ON the foot via instead -- which is also what reconnects this cell to _v3_trunk.
# ⚠ AND +3V3D TAKES ONE VIA AND THE BACK SIDE, because there is no surface path at all:
# asked with a 500 mm penalty per layer change the maze still needs a hop, since the
# corridor south from the pull-up is the converter's own west pad row. B.Cu and NOT In2 --
# the same reason the channel this replaces gave: on In2 a run down the cell fences the one
# free signal layer off, while on B.Cu it costs a GND pour a slot.
# ⚠ ONE VIA, NOT TWO: the maze's second via sat 0.52 mm from the foot via, -0.080 mm of
# laminate between the drills. A through via IS a B.Cu landing, so the run ends ON the foot
# via -- which is also what reconnects this cell to _v3_trunk.
# ⚠⚠ AND IT WAS SEARCHED IN CELL 1, NOT CELL 0, WHICH IS THE WHOLE LESSON OF THE SECOND
# ATTEMPT. The first path ran its B.Cu leg at cell x -3.960, which is 0.02 mm from the
# I2C2_SCL spine -- and in cell 0 that is FINE, because the spine starts at y 61.269, below
# it. In the other four cells it is a short, and DRC said so three times. Verifying one cell
# and copying five is not verifying five: this path is checked in all five (0.227 mm
# required, ALL CLEAR) and its B.Cu leg sits 0.77 mm off the spine.
# ⚠ AND THE VIA MOVED 0.10 mm OUT, WHICH IS ABOUT In1 RATHER THAN CLEARANCE. At
# (-3.210, -0.022) it sat 1.06 mm from the I2C2_SCL spine via in every cell, and the two
# antipads left a 0.160 mm web in the analog reference plane where the board had documented
# 0.266 -- legal, check_north_si still passed, and still a measurable halving of a property
# this design states as measured. 0.10 mm further out along its own diagonal puts the web at
# 0.301 mm, better than it was before this change. Measured with check_north_si on the board
# before and after, not argued.
_V3_STUB = [("F.Cu", [(-3.462, 3.260), (-3.910, 2.828), (-3.960, 2.828), (-4.160, 2.628),
                      (-4.160, 1.828), (-3.960, 1.628), (-3.960, 0.828), (-3.110, 0.078)]),
            ("B.Cu", [(-3.110, 0.078), (_V3_CH_DX, -3.270)])]
_V3_VIA = (-3.110, 0.078)
_STUB_W = 0.20
# ⚠ ONE CELL'S VIA STANDS 0.09 LOWER, IN BOARD MILLIMETRES (2026-10-05). These vias go in
# after routing, so the router cannot know about them: on the route with the USB3300 it
# ran MID along In2 0.48 above converter 5's, 0.06 mm of clearance against 0.127. Moved,
# it has 0.15 to MID and 0.31 to I2C2_SCL below. A new route may want this gone again:
# the pass that reports the clearance is the check.
_V3_VIA_NUDGE = {4: (0.0, -0.09)}


def _v3_pt(k, q):
    x, y = _cell_pt(k, *q)
    if q == _V3_VIA and k in _V3_VIA_NUDGE:
        x, y = x + _V3_VIA_NUDGE[k][0], y + _V3_VIA_NUDGE[k][1]
    return (x, y)


def _shdnz_stubs():
    out = []
    for k in range(5):
        P = lambda dx, dy, k=k: _cell_pt(k, dx, dy)
        out.append(("SHDNZ%d" % (k + 1), "F.Cu", _STUB_W, [P(*q) for q in _SHDNZ_STUB]))
        for _lay, _pts in _V3_STUB:
            out.append(("+3V3D", _lay, _STUB_W, [_v3_pt(k, q) for q in _pts]))
    return out


def _shdnz_vias():
    """The one layer change each pull-up's +3V3D run needs. Post-route, like the tracks."""
    if not _V3_STUB:
        return []
    return [("+3V3D",) + _v3_pt(k, _V3_VIA) for k in range(5)]


def _outline_poly(cx, cy):
    """The board edge as a closed polygon, board-local. Adjacent bands with the same
    X extents are merged so the polygon has no zero-length edges for the fab to
    interpret."""
    bands = []
    for y0, y1, x1, x0 in sorted(OP._SECTIONS):
        if bands and abs(bands[-1][2] - x1) < 1e-9 and abs(bands[-1][3] - x0) < 1e-9:
            bands[-1] = (bands[-1][0], y1, x1, x0)
        else:
            bands.append((y0, y1, x1, x0))
    # Walk the +X side from -Y to +Y, then the -X side back down, one corner pair per band
    # on each side. Since the strip widened -X (2026-09-22) the -X edge is no longer one
    # straight line. Collinear points (a band whose edge continues its neighbour's) are
    # dropped: KiCad reads collinear duplicates on Edge.Cuts as a self-intersection.
    pts = []
    for y0, y1, _x1, x0 in bands:
        pts += [(x0, y0), (x0, y1)]
    for y0, y1, x1, _x0 in reversed(bands):
        pts += [(x1, y1), (x1, y0)]
    out = []
    for p in pts:
        if not out or out[-1] != p:
            out.append(p)
    if out[0] == out[-1]:
        out.pop()
    changed = True
    while changed:                              # drop points in the middle of a straight run
        changed = False
        for i in range(len(out)):
            a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
            if (abs(a[0] - b[0]) < 1e-9 and abs(b[0] - c[0]) < 1e-9) or \
               (abs(a[1] - b[1]) < 1e-9 and abs(b[1] - c[1]) < 1e-9):
                out.pop(i)
                changed = True
                break
    # the notch in front of the USB-C (OP.usb_notch): four more corners in the -Y edge
    nx0, nx1, ny0, ny1 = OP.usb_notch()
    for i in range(len(out)):
        a, b = out[i], out[(i + 1) % len(out)]
        if (abs(a[1] - ny0) < 1e-9 and abs(b[1] - ny0) < 1e-9
                and min(a[0], b[0]) < nx0 and max(a[0], b[0]) > nx1):
            ins = [(nx0, ny0), (nx0, ny1), (nx1, ny1), (nx1, ny0)]
            if a[0] > b[0]:
                ins.reverse()
            out[i + 1:i + 1] = ins
            break
    else:
        raise RuntimeError("the USB notch found no -Y edge to stand in")
    return [(x - cx, y - cy) for x, y in out]


def _placements(cx, cy):
    """{ref: (x, y, rot)} board-local, straight from the CAD's PARTS table."""
    out = {}
    for p in OP.PARTS:
        out[p["ref"]] = (round(p["x"] - cx, 4), round(p["y"] - cy, 4),
                         float(p.get("rot", 0.0)))
    return out


_XS = [v for s in OP._SECTIONS for v in (s[2], s[3])]
_YS = [v for s in OP._SECTIONS for v in (s[0], s[1])]
BOARD_X0, BOARD_X1 = min(_XS), max(_XS)
BOARD_Y0, BOARD_Y1 = min(_YS), max(_YS)
CX, CY = (BOARD_X0 + BOARD_X1) / 2.0, (BOARD_Y0 + BOARD_Y1) / 2.0
BOARD_W, BOARD_L = BOARD_X1 - BOARD_X0, BOARD_Y1 - BOARD_Y0

def _buck_sw():
    """The buck's switch node, laid rather than routed: the one net on this board that
    radiates, so its copper is the shortest that reaches the inductor and no more. Out
    of U13's top pad (pin 12), 0.5 mm, along the top of the regulator's row above C165
    and R40, into L1's near land: 6.5 mm. Positions come from the CAD's U13 and L1, so
    the track moves with them."""
    at = {q["ref"]: (q["x"] - CX, q["y"] - CY) for q in OP.PARTS}
    ux, uy = at["U13"]
    lx = at["L1"][0] - 1.50                       # L1's SW land
    top = uy + 2.00
    return [("SW", "F.Cu", 0.5, [(ux, uy + 1.20), (ux, top), (lx - 0.25, top),
                                 (lx, top - 0.60)])]


BOARD_NOTES = {
    "outline_mm": (round(BOARD_W, 3), round(BOARD_L, 3)),
    "outline_poly": [[round(x, 4), round(y, 4)] for x, y in _outline_poly(CX, CY)],
    # the O's HOLE: the bridge bearings and the block that carries them sit inside the
    # ring, so the board has a 30 x 105 mm rectangular cutout. Edge.Cuts AND a keepout --
    # freerouting cannot see Edge.Cuts (see layout._edge_hole).
    # ⚠ THE COMB, NOT ONE BIG HOLE (2026-09-23). This emitted a SINGLE 16.41 x 101.6 mm
    # rectangle spanning the whole slot band -- the old "O-shaped board with the bearing
    # block inside the ring" design. The board has been a COMB since the axle redesign:
    # ten L-shaped slots with 4.00 mm strips of copper between them, and those strips are
    # how all twenty TIA outputs cross to the converters. The CAD had the comb and the fab
    # data did not, so the GERBERS would have shipped a board with no comb at all -- and
    # the router, seeing a hole where the strips are, could not connect across it. That is
    # most of the 23 unconnected on the first route of this placement.
    # A divergence like this is invisible to every check that reads one side only: the CAD
    # gate was clean, ERC was clean, the netlist was clean, and BOM/CAD/netlist agreed.
    # Nothing compares the CAD's cutouts against the board's.
    "outline_holes": [],
    # ⚠ y - CY, NOT -y - CY. layout._to_board already flips to KiCad's y-down
    # (SHEET_ORIGIN[1] - y), and _placements feeds it an UNnegated y, so a second negation
    # here mirrors the cutouts against the parts. The outline_holes line this replaced had
    # exactly that error and it never showed, because a symmetric +-Y hole maps onto
    # itself; so does the comb, which is why the first route improved anyway. The jack
    # access hole below is the first asymmetric cutout on this board and would have landed
    # 91.2 mm from its screw.
    "outline_slots": ([{"poly": [[x - CX, y - CY] for x, y in _p],
                        "rects": [[r[0] - CX, r[1] - CY, r[2] - CX, r[3] - CY]
                                  for r in (OP.O_SLOTS[_i],
                                            OP.O_SLOTS[len(OP.O_SLOTS) // 2 + _i])]}
                       for _i, _p in enumerate(OP._slot_polys())] if OP.O_SHAPE else []),
    # ⚠ AND NOT THE JACK'S ACCESS HOLE, WHICH WAS HERE AND WAS A FAB DEFECT. The CAD
    # cut a O4.4 clearance hole for a driver to reach the pickup-height jack screw and
    # nothing emitted it, so it was added here -- correctly, for the board that existed
    # then. The strip has since moved -X twice and the jack is now OUTSIDE the board: its
    # centre is 1.775 mm past the -X edge, so the circle straddles the edge instead of
    # piercing the board.
    #
    # On Edge.Cuts that is not a hole, it is a broken outline. It is the "UNEXPECTED
    # invalid_outline: Circle on Edge.Cuts + Segment on Edge.Cuts" that survived every
    # route this week, AND the CAD/fab disagreement beside it -- the circle's rim reaches
    # x -32.58 where the board ends at -28.61, which is how a 57.21 mm board came to
    # export a 61.19 mm outline. I had written that off as a bounding-box quirk. It was
    # this, and it would have been milled.
    #
    # The driver still reaches the screw, because the board is not in its way: 1.775 mm of
    # air against the 1.444 a 2.5 mm hex key needs. optical_pickup.pcb() asserts that
    # rather than trusting it, since the margin is 0.33 mm.
    # ⚠⚠ THE BOARD'S OWN TWO MOUNTING HOLES, WHICH IT DID NOT HAVE (2026-09-29).
    # `cutouts` was an empty list -- O_ROD_HOLES is `[]` and says so -- so the only holes
    # this board exported were the ten sensor slots. Meanwhile src/build.py places an M4
    # through EACH of OP.mount_points(): head above the laminate, shank down, insert
    # seated immediately below. The overlap gate had been reporting the consequence all
    # along as `optical_pcb <-> optical_screw_0` 20.11 mm3 and `_1` 20.38 -- a 4.0 mm
    # cylinder crossing exactly 1.6 mm of laminate, centred on the mount point. Not a
    # declared contact either: check_overlaps allows {optical_screw, optical_insert} and
    # {optical_screw, bridge_endplate}, so the neighbouring pairs were considered and this
    # one was simply absent. THE SCREW WAS RIGHT AND THE BOARD WAS WRONG: the fab would
    # have shipped solid laminate at both points and neither screw could be fitted.
    # build.py records the near-miss that set it up -- "the old optical M2 went up from
    # below and did need [a flip]; copying that was what put this one through the board."
    # The flip was removed and the screw's ORIENTATION fixed; nobody then asked whether
    # the board had a hole for it.
    # Driven off mount_points() rather than a pair of constants so the hole cannot drift
    # from the screw, which is the same single-source rule the plinth's inserts follow.
    # M4.shaft_clr_d (4.4) is the canonical clearance bore, NOT insert_pilot_d (6.0) --
    # the plastic takes the insert, the board only has to let the shank past.
    # ⚠ AND IT NO LONGER HANGS OFF O_ROD_HOLES, WHICH IS A LANDMINE. That list is a leftover
    # from the abandoned O-shaped-board experiment (c50b68f): it is `[]` and its own comment
    # says "nothing uses it". Building the mount holes as an append to a comprehension over it
    # made a dead name look load-bearing while still reading as dead -- and main has already
    # run one "delete dead code, drop unused imports" pass over this file. Deleting
    # O_ROD_HOLES is the right call and it would have taken the mounting holes with it.
    # The holes stand on their own now, so the dead list can go whenever anyone gets to it.
    "cutouts": [{"xy": [round(x - CX, 4), round(y - CY, 4)], "d": OP.M4.shaft_clr_d}
                for x, y in OP.mount_points()],
    # ⚠ CORRIDORS ARE OFF, AND THE MEASUREMENT SAYS SO. The generator did what it was
    # built to do -- 20 of 20 comb crossings placed on assigned gaps, A through the strip
    # +Y of its string and B through the strip -Y -- and the BOARD GOT WORSE. Measured
    # against the same board without it: TIA_OUT failures 7 -> 11, total unconnected
    # 12 -> 16, and thirteen tracks left dangling.
    # The premise was wrong. A pre-laid run that stops in open copper mid-net assumes the
    # router will adopt it and route to both ends; it does not. route.py freezes only the
    # DECLARED pairs (17 wires, "as (type fix)"), so an unfrozen stub is just copper in
    # the way -- it costs the router the lane it occupies and gives nothing back. The
    # local-net pass gets away with the same shape because its clusters are ATTACHED to
    # the pads at one end and a few millimetres long; these were 18.8 mm and attached at
    # neither. The loop's own standing warning -- pre-laid geometry is never connected by
    # the router on this board -- was about vias, and I argued a track was different. It
    # is not, and the argument cost two routing rounds.
    # The code stays (layout._local_nets corridors=), documented and tested, because the
    # IDEA is still right: the router cannot know that a string's A and B are a pair that
    # must take different gaps, and that is a missing constraint no amount of search
    # fixes. What is missing is a way to hand it a COMPLETE path, pad to pad, which needs
    # the far end solved inside a converter cell. That is the next attempt, not this one.
    "corridors": [],
    "layers": 4,
    "thickness_mm": 1.6,
    # FOUR LAYERS, and on this board it is the least negotiable of the five. In1.Cu
    # is an unbroken ground plane under twenty summing nodes reading tens of
    # nanoamps AND under a 60 MHz ULPI bus; there is no version of this board that
    # works with a two-layer stack and a hatched pour.
    # ⚠ GND IS POURED ON F.Cu TOO, AND THAT IS A ROUTING DECISION AS MUCH AS AN
    # ELECTRICAL ONE. Every ground pad on this board is an SMD pad on F.Cu; the
    # planes are on In1/B, which an F.Cu pad cannot reach without a via. Left to the
    # autorouter that meant 75 pads each needing a stub and a via, and it half-did
    # them -- 13 of the 15 connections it could not make were dangling GND stubs with
    # no via on the end.
    #
    # A pour on F.Cu removes the problem rather than solving it: the zone fill
    # connects every ground pad directly, on its own layer, with no router
    # involvement and no per-pad via to place. The stitching between F/In1/B is what
    # vias are for, and those go in open copper where there is room for them.
    # It is also just the normal way to build a mixed-signal board -- ground on every
    # layer it can be on -- so this is the pipeline catching up with practice.
    # ⚠ DROPPING THE B.Cu POUR IS WORSE, MEASURED: 1 unconnected -> 4. The reasoning
    # was that B.Cu is the starved layer -- F.Cu carries 1121 track segments, In2.Cu 700,
    # B.Cu only 190 -- and that its GND pour is why, since In1.Cu is the real reference
    # plane, unbroken and directly under F.Cu. Free the layer, close the last net.
    #
    # It went the other way, and the reason is worth keeping: a GND POUR IS NOT ONLY AN
    # OBSTACLE, IT IS ALSO THE RETURN PATH AND THE VIA TARGET. Every ground pad and every
    # stitch via on that layer lands in the pour and needs no track at all. Remove it and
    # all of that becomes routing the router now has to do, on the layer it was supposed
    # to be freeing. The 190 segments were never the measure of how much work B.Cu does.
    #
    # So B.Cu being "half empty" is not spare capacity. Third structural lever tried on
    # this net and the third to lose, after the +3V3A pre-lay and the full permutation.
    # ⚠⚠ THIS BOARD IS NOT READY, AND "0 unconnected, 0 violations" DOES NOT SAY SO.
    # elec/fab.py's signal-integrity check reports THREE failures that DRC cannot see,
    # because DRC compares copper to a netlist and says nothing about timing or impedance:
    #
    #   USB_HS  the pair DOES NOT SHARE A LAYER SET -- USB_DP runs F.Cu + In2.Cu with
    #           TWO vias, USB_DM runs F.Cu with none. A differential pair's impedance is
    #           a property of the two conductors' geometry RELATIVE TO EACH OTHER, so a
    #           layer split destroys it, and the vias sit on one leg only. At 480 Mbps
    #           this is the difference between a link that works and one that enumerates
    #           sometimes.
    #   USB_HS  skew 3.28 mm against a 2.50 mm budget.
    #   ULPI    skew 55.21 mm against a 12.00 mm budget, 24.5..79.7 mm over 12 nets.
    #
    # ⚠ AND THE LAYER SPLIT LOOKS AVOIDABLE. The In2 excursion is 2.50 mm long, between
    # vias at (116.97, 188.65) and (119.47, 188.65) -- and the nearest F.Cu obstacle
    # along that same line is VBUS at 1.629 mm, with a 0.2 mm trace. The surface is
    # clear; the pair dived for no reason the geometry requires. diff_pair_inner is set
    # to In2.Cu, which PERMITS the inner layer, and something took it for one leg only.
    #
    # Recorded here rather than fixed because it is a real piece of work: the fix is in
    # how layout.py lays the declared pair, and both legs must transition together or
    # neither. Until then this board routes cleanly and would not run USB HS reliably.
    "zones": [("GND", "F.Cu", 0.3), ("GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],
    # ⚠ ONE VIA AND TWO SHORT TRACKS, WHICH IS WHAT THIS NET ACTUALLY NEEDED. Four
    # attempts to close +3V3A at U2 pad 4 reached for router SETTINGS -- pre-laying the
    # net class (1 -> 3), enabling retry rounds (1 -> 3 with 7 violations), dropping the
    # B.Cu pour (1 -> 4), narrowing the net (1 -> 2). All four lost, because the tool
    # could say "change the rules" but not "put a via here": `tracks` lays copper on ONE
    # layer, and this connection has to CHANGE layers. _add_via in elec/layout.py closed
    # that gap.
    #
    # SITED BY SEARCH, NOT BY EYE. A 14 x 14 mm grid at 0.1 mm, testing the via pad and
    # both segments against every foreign track and via with 0.15 mm on top of the
    # netclass rule: 2638 legal sites, and this is the shortest at 4.22 mm total. The
    # first run of that search returned ZERO and was wrong twice over -- it demanded
    # 0.20 mm of extra margin, and it read the narrowed-rail board rather than this one,
    # because the source had been reverted without re-routing. A search is only as good
    # as the board it reads.
    #
    # The geometry it threads: the rail already passes 3.86 mm from the pad on B.Cu, but
    # TIA_OUT_2A shadows that rail along its whole 12.8 mm, so the via cannot land on the
    # rail itself -- it lands clear and a 2.36 mm B.Cu spur reaches across.
    # ⚠ AND IT GOES IN AS A REPAIR, NOT A PRE-LAY -- THAT IS THE WHOLE FIX. Laid
    # before routing, this exact geometry closed +3V3A and cost FIVE analog nets
    # (1 unconnected -> 5), because the other 76 nets had to plan around it. Laid after
    # the router finishes it closes the same gap and disturbs nothing. route.py applies
    # repair_vias/repair_tracks in its repair block, beside the same-part gap join that
    # is there for the identical reason.
    #
    # Re-siting was tried first and is a dead end: scored by analog nets within 1.2 mm
    # of the path, the best of all 2638 legal sites touches SIX, and so does this one.
    # The corridor has no quiet corner, so timing was the only lever left.
    # ⚠ THE REPAIR IS OFF, AND THE REASON IS MY SEARCH, NOT THE MECHANISM. Laying one
    # via and two tracks AFTER routing does close +3V3A at U2 pad 4 and leaves the other
    # 76 nets untouched -- that part worked, and route.py keeps repair_vias/repair_tracks
    # for it. What failed is the geometry I fed it.
    #
    # The site search in this session checked clearance against TRACKS and VIAS only. It
    # never considered PADS or the board OUTLINE. The first path was 4.2 mm and came near
    # neither, so the gap stayed invisible; the second was 14.6 mm and immediately picked
    # up two solder_mask_bridge violations against U2's own pad 6, three
    # copper_edge_clearance, a copper_sliver and a clearance -- seven where the board had
    # one. A violation is worse than an unconnected pad (finish.py ranks them that way):
    # one is a board that cannot be made, the other a board that is not finished.
    #
    # TO RE-ENABLE: extend the search to pads and the outline, re-run it against the board
    # THIS netlist produces, and re-measure. The coordinates are not reusable -- they were
    # already invalidated once by the J2 two-way change, because a repair is geometry
    # pinned to one routing, not a property of the schematic.
    # ⚠ AND THE NET THAT NEEDS REPAIRING IS NO LONGER +3V3A. With J2 two-way the router
    # closes +3V3A on its own; MID is the casualty instead, and its break is a different
    # SHAPE -- a 2.54 mm gap on F.Cu, the pad's own layer, needing one track and no via.
    # The first search tool modelled only via-plus-spur and targeted B.Cu only, so it
    # reported "0 legal paths" for a repair that is one straight line. Generalised, the
    # same board offers 12 same-layer paths and 1181 via paths.
    #
    # This is the shortest same-layer one, 4.57 mm, found by elec/repair_search.py
    # against the board THIS netlist produces. Re-run it after any netlist change: the
    # coordinates are pinned to one routing and have already been invalidated once.
    # ⚠ AND THAT PATH CROSSED A +3V3A DIAGONAL, which the search called clear by
    # +0.758 mm. The bug was in the geometry, not the board knowledge: the minimum of
    # the four endpoint-to-segment distances is only the segment-to-segment distance
    # when the segments DO NOT CROSS. Two that properly intersect are at distance zero
    # while every endpoint stays far from the other line, so a crossing read as room.
    # Fixed in elec/repair_search.py; the same line now reads 0.000 and is rejected.
    # Re-searching needs a board WITHOUT this repair in it, so it is off for one run.
    # ⚠ U2 PAD 3 ESCAPES WEST ONLY, AND ONLY ON F.Cu. Measured on eight directions,
    # seven are negative: +3V3A's track at 0 and 45 deg, its pad at 90 and 135,
    # TIA_IN_3A's pad and track from 225 to 315. Pad 3 is IN A+ (MID) and pad 4 is V+
    # (+3V3A) -- adjacent SOIC pins on 1.27 mm pitch, each one's escape copper boxing
    # the other in, against the strip's own edge 1.72 mm away.
    #
    # A VIA CANNOT GO WEST even though a TRACK can: a through via has to clear every
    # layer, and TIA_OUT_1A (B.Cu) and TIA_OUT_3A (In2.Cu) both run under that corridor.
    # F.Cu is clear there and the layers below are not, which is why every via site in
    # the search failed while the track to it passed.
    #
    # So the repair is a DETOUR, not a hop: west 1.30 mm into the corridor, 2.54 mm along
    # it past the two pads that block the direct line, then 1.30 mm back east to the
    # stub the router left. 5.13 mm of F.Cu and no via. The search only tried straight
    # lines, which is why it reported zero -- a third shape of repair it did not model.
    # (2026-09-21: the detour itself is gone. It was fitted to the old triplet's copper;
    # the PD15 triplet moved every MID and summing-node pad it threaded between.)
    # ⚠ NARROWING +3V3A IS WORSE TOO: 0.25 -> 0.15 mm took it from 1 unconnected to 2.
    # This was the one lever that was not about giving the router more ROOM. Three
    # attempts had tried that (pre-lay, retry rounds, dropping the B.Cu pour) and all
    # three lost, and the measured geometry said the gaps were TIGHT rather than blocked
    # -- the rail already passes 3.86 mm from the pad on B.Cu, and the F.Cu lane at the
    # pad's own y is shadowed by MID at 0.56 mm centre to centre. So: make the net
    # smaller instead of the space bigger. It carries ~40 mA and 0.15 mm is good for
    # 0.62 A, so the width was free electrically.
    #
    # It still lost, and that is the useful part. A narrower net is not only a smaller
    # obstacle, it is also a DIFFERENT netclass -- the router re-plans every +3V3A
    # segment on the board, not just the failing hop, and the 101 segments that were
    # working had no reason to come back the same way. FOUR levers, four losses, and the
    # last one rules out "the corridor is too tight" as the explanation.
    # What is left is not a router setting. See the open note at the end of this file.
    # ⚠ THE PLACEMENTS NAME THE COURTYARD CENTRE, not the pad centroid. This is the
    # only board in elec/ where that is true, and it is true because these coordinates
    # come from a MECHANICAL model, which reasons about the box a part occupies rather
    # than about where its solder lands average out. layout.py honours it; see
    # _anchor_on_courtyard there for what it cost to discover.
    # ⚠ THE HIGH-SPEED BUDGETS, AND THEY ARE DELIBERATELY LOOSE. elec/verify.py
    # enforces these; the numbers come from the geometry rather than from habit.
    #
    # ULPI is 60 MHz source-synchronous over a 34.5 mm run -- about 207 ps of flight
    # at ~6 ps/mm in FR4. A 10 mm length mismatch is 60 ps against a 16,670 ps bit
    # period: 0.36%, against a setup window measured in nanoseconds. Matching this bus
    # to a tenth of a millimetre would LOOK rigorous and would be cargo cult, so the
    # budget is 12 mm and the reason is recorded. What actually matters here is the
    # continuous GND plane under it (In1.Cu) and keeping the clock out of the analog
    # band -- both placement decisions, already made.
    #
    # USB HS is the one with a real constraint, and it is still not length: at 480 Mbps
    # the bit period is 2,080 ps and the run is 25 mm, so intra-pair skew has room. The
    # binding requirements are that DP and DM stay a PAIR -- same layers, so the
    # differential impedance the stack-up was designed for still describes something --
    # and that neither collects vias, since each one is a discontinuity.
    "match": [
        # ⚠ THIS BUDGET IS DERIVED FROM THE PHY'S DATASHEET NOW, NOT PICKED. It read
        # 12.0 mm and the board measures 55.21 mm, so it failed -- and the rationale
        # attached to it argued the effect was four orders of magnitude below what
        # matters, which is not a derivation of 12 at all. A budget that its own
        # reasoning does not support cannot say whether a board is good.
        #
        # USB3300 datasheet (Microchip DS00001783C, table 6-2 ULPI Interface Timing):
        #     setup, STP and data in   T_SC / T_SD   5.0 ns MIN
        #     hold,  STP and data in   T_HC / T_HD   0.0 ns MIN
        # At 60 MHz the period is 16.67 ns, so 11.67 ns is left for the link's
        # clock-to-out, flight time, inter-signal skew and margin. Allocating 0.5 ns of
        # that to SKEW alone -- 4 % of the window, leaving the rest to the STM32's
        # output delay and margin -- gives 83 mm at 6.0 ps/mm in FR4. Rounded DOWN to
        # 80 mm, so the number is conservative against the allocation rather than
        # fitted to the board.
        #
        # The board's 55.21 mm is 331 ps, 2.8 % of that window, and passes with room.
        # The hold side is free: T_HC is 0.0 ns, so no amount of skew violates it.
        # ⚠ max_vias IS None HERE AND 2 ON THE PAIR BELOW, AND THE DIFFERENCE IS THE
        # STACKUP, not inattention. Measured on the routed board 2026-09-19, the twelve
        # ULPI nets carry 2 to 5 vias each (mean 2.9; the CLOCK, which everything else
        # is timed against, carries 3). That is fine here for a reason specific to this
        # board: In1.Cu is the ONLY plane, and every signal layer references it -- F.Cu
        # from above it, In2.Cu and B.Cu from below. So a via that moves a ULPI signal
        # between any two of those layers keeps the SAME reference plane, and the return
        # current stays on In1 instead of having to find a way between two planes. The
        # transition that actually hurts a source-synchronous bus -- a reference change
        # with no stitching via to carry the return -- cannot occur on this stackup.
        #
        # What is left is the via's own discontinuity, and at 60 MHz that is not the
        # constraint: the datasheet window below is 11.67 ns wide and the measured skew
        # spends 331 ps of it. The USB pair is held to 2 vias because 480 Mbps is where
        # a discontinuity starts to matter, not because its reference behaves worse.
        {"name": "ULPI", "max_skew_mm": 80.0, "same_layer": False, "max_vias": None,
         "nets": ["ULPI_D0", "ULPI_D1", "ULPI_D2", "ULPI_D3", "ULPI_D4", "ULPI_D5",
                  "ULPI_D6", "ULPI_D7", "ULPI_CK", "ULPI_STP", "ULPI_DIR", "ULPI_NXT"],
         "why": "USB3300 table 6-2: T_SC 5.0 ns setup, T_HC 0.0 ns hold. 16.67 ns "
                "period - 5.0 setup = 11.67 ns for clock-to-out, flight, skew and "
                "margin; 0.5 ns of that allocated to skew = 83 mm at 6.0 ps/mm, "
                "rounded down to 80. Measured 55.21 mm = 331 ps = 2.8 % of the "
                "window. Derived from the datasheet, NOT relaxed to fit -- the "
                "previous 12.0 mm did not follow from anything and failed a board "
                "that is comfortably inside the PHY's real requirement."},
        # ⚠ MEASURED PAST THE USB-C's PAD MERGE. A USB-C carries D+ on BOTH A6 and B6
        # and D- on both A7 and B7, so layout._flip_merge joins each net's two pads at
        # the connector -- and that join deliberately takes ONE rail to an inner layer
        # (which one is decided by the shorter link). Counting that stub, this group
        # read "does not share a layer set" and 3.28 mm of skew against a 2.50 budget;
        # measured past it, the coupled RUN is F.Cu for both rails and the skew is
        # 1.08 mm. The stub is a pad join, not transmission line, and the numbers that
        # matter are the ones for the coupled run.
        # ⚠ 2.5 -> 8.3 mm, DERIVED. This limit was never derived; the `why` below
        # argues skew "has room" and that pairness is what matters, which supports a
        # loose budget and then wrote a tight one. It only came up because output_panel
        # inherited the same 2.5 and a pair missed it at 2.98. Two independent bases --
        # 10 % of the USB 2.0 HS 500 ps minimum rise time, and half of USB-IF's ~100 ps
        # cable-assembly skew budget -- both give 50 ps, which at 6.0 ps/mm is 8.3 mm.
        # This board measures 1.08 mm and passed either way; the number is fixed because
        # it was wrong, not because it was failing. See output_panel.py for the working.
        {"name": "USB_HS", "max_skew_mm": 8.3, "same_layer": True, "max_vias": 2,
         "merge_at": "J1", "merge_r": 4.0,
         "nets": ["USB_DP", "USB_DM"],
         "why": "480 Mbps, 2,080 ps per bit over a 25 mm run. Skew has room; what has "
                "to hold is that the two stay a PAIR on the same layers (differential "
                "impedance is a property of the two conductors' geometry relative to "
                "each other, which a layer split destroys) and that neither collects "
                "vias, each being an impedance discontinuity."},
    ],
    # ⚠ In1.Cu IS A PLANE, NOT A ROUTING LAYER, and saying so is what makes it true.
    # KiCad's Specctra export calls every copper layer "signal", so the router happily
    # laid tracks across the ground plane and fragmented it -- 5729 mm2 of pour came
    # back as 1043. The impedance reference the USB pair and the ULPI bus both depend
    # on was being destroyed by the step that routed them. route.py now declares this
    # to freerouting as a plane and it leaves it alone.
    "plane_layers": ("In1.Cu",),
    # ⚠ In2.Cu IS A SIGNAL LAYER AND STAYS ONE -- TESTED, AND THE TEXTBOOK ANSWER LOSES.
    # The standard 4-layer mixed-signal stackup is signal / GND / POWER / signal, and by
    # that pattern this board is wasteful: +5V, +3V3D and MID are routed as tracks the
    # length of a 180 mm board, competing with twenty TIA outputs for the same copper,
    # while In2 carries a handful of nets. Pouring +5V on In2 (stitched per pad, as GND
    # is) should hand the strip its room back.
    # MEASURED: 16 unconnected and 22 violations, against 12 and 20 with In2 left alone.
    # It went the other way. The reason is that this board's difficulty is not supply
    # distribution -- it is twenty analog signals leaving a 13.6 mm strip for one MCU at
    # the far end -- and that traffic needs LAYERS, not a cleaner power rail. Taking a
    # third of the routing space to solve a problem the board did not have cost more
    # than the power tracks were ever costing.
    # The stackup is chosen by what the board is, not by what the pattern says.
    # ⚠ 25 PASSES, NOT THE DEFAULT 10, AND IT IS CONNECTIVITY THIS BUYS -- NOT NEATNESS.
    # Measured on this board: 1 pass 105 unconnected, 3 -> 50, 10 -> 13, 25 -> 6. The
    # comment in route.py used to say the curve was flat past ten, which is true of the
    # boards that finish and false of this one. A board at its routing limit comes out
    # of the early passes in a mess, and the later passes are where the optimiser rips
    # that mess up and re-lays it; stopping at ten freezes it half-done.
    # It costs 1069 s against about 700 -- 60% more wall clock for 54% fewer failures.
    # ⚠ B.Cu IS CHEAPER ON PURPOSE. In the MCU approach corridor B.Cu carried 4.6%
    # copper against F.Cu's 10.6% while the corridor was the thing that ran out of room.
    # A cost below 1.0 tells freerouting to prefer a layer; the bottom layer is the one
    # with headroom, so it gets 0.7. In1.Cu is absent because it is the ground plane.
    # ⚠ TEN, NOT FIFTY, AND IT IS AN ITERATION DECISION (user, 2026-09-25: "let's try with
    # just 10"). Fifty passes is 45 minutes and I spent six of them last night chasing the
    # last three nets, which is the wrong use of the machine: the user's rule is that a
    # board needing that many retries is telling you to move components, not to search
    # harder. Ten passes is about 9 minutes, so a placement change can be MEASURED in the
    # time it used to take to state one.
    # ⚠ AND MEASURED RATHER THAN ASSUMED, because I guessed "about 9 minutes" twice and
    # was wrong twice. On this board, with today's pre-lay:
    #     10 passes   25.1 min   5 unconnected
    #     50 passes   45.5 min   3 unconnected
    # So the pass count is NOT most of the runtime -- five times the passes is 1.8x the
    # wall clock, because the first route dominates and passes are the optimiser after it.
    # Ten costs 45% less time for two nets, which is the right trade while placement is
    # still moving and the wrong one for a board about to be ordered.
    # (route.py's own curve -- 1 -> 105, 3 -> 50, 10 -> 13, 25 -> 6, 50 -> 3 -- is from
    # before the pre-lay existed. Ten now lands at 5, not 13.)
    "router_passes": 10,
    # How far route.py's post-route repair may reach to join two ends of one net it finds
    # in different islands. 7.0 because a route left I2C2_SDA 5.85 mm short of its own
    # spine -- the router came the whole way from R51 and stopped just before the
    # handover -- and the default 5.0 declined to finish it. This costs the router
    # nothing: the repair runs after routing, on pairs that are already unconnected.
    "repair_mm": 7.0,
    # ⚠ THE BRING-UP PADS ARE PLACED AFTER ROUTING, AND THAT IS THE WHOLE REASON THEY
    # EXIST AT ALL. Four routes with these pads in the DSN cost a net every time, always
    # in the same neighbourhood (the USB PHY), and once on a rail whose own pad had been
    # removed -- so the cost was never the pad's area, it was handing the router one more
    # obstacle in the one region it re-solves from scratch and only just finishes. Placed
    # here they are invisible to it: layout skips them, route.py drops them in after the
    # session import, and DRC still checks every clearance.
    # Each site was SEARCHED against the finished board (scratchpad/padsite.py): a clear
    # 1.5 mm circle that already overlaps its own net's copper, so no track is needed, and
    # outside every courtyard, because a pad under a part is legal and unprobeable.
    #   TP8  BOOT0   headroom 0.492 mm    TP9  +24V   4.747
    #   TP10 +5V     1.214               TP11 +3V3A  1.956
    # ⚠ NONE OF THE SIX NEEDS A SINGLE MILLIMETRE OF NEW COPPER, which is the whole reason
    # they exist. Each one sits on a net the router has already finished: the three rails,
    # BOOT0 at its own pull-down, and the I2C2 pair on the converter control bus. TP6/TP7
    # are 1.0 mm rather than 1.5, because that is what turns 0.074 mm of clearance into
    # 1.696 and 0.743.
    # The one pad that DID need copper -- the buck's power-good -- is not here: its pin
    # cannot be escaped at any width. See the BUCK_PG_NC note for the numbers.
    # ⚠ THE EDGE KEEP-OUT THAT MATTERS HERE IS THE CAD'S 1.2 mm, NOT DRC'S 0.300. The
    # first USART lane found, x 27.55, clears copper by 2.6 mm and dies in
    # _assert_field_clear at 0.31 mm inside the model's keep-out. Whichever rule is
    # stricter is the rule.
    # ⚠ BOOT0 HAS NO CLEAR SITE AT ALL and TP8 is the one exception on this list: at D1.5,
    # D1.0 and even D0.8 the search returns ZERO sites, because every millimetre of BOOT0
    # copper lies inside somebody's courtyard -- the net runs from the pin to R30 and
    # stops. Its courtyard overlap with R30 is declared in netcheck (nothing is ever
    # fitted on a bring-up pad, so that courtyard reserves room for a body that does not
    # exist); its COPPER clears by 0.492 mm.
    "post_route_refs": ("TP6", "TP7", "TP8", "TP9", "TP10", "TP11",
                        # item 6: the five SHDNZ pull-ups. A RESISTOR being here is the
                        # same argument one step further -- a part the router never sees
                        # cannot cost it a net, and an 0402 in a site verified clear on the
                        # finished board is as safe there as a bare pad. It is still
                        # assembled: the fab builds from the board, not from the DSN.
                        "Rs11", "Rs21", "Rs31", "Rs41", "Rs51"),
    # ⚠ THE FIVE SHDNZ NETS DO NOT EXIST BEFORE ROUTING. Each is a converter pin and a
    # pull-up, and BOTH are post-route -- so layout leaves pin 14 bare, exactly as the
    # no-connect it used to be, the DSN gains nothing, and route.py builds the net over every
    # node after the import. The mechanism also covers the general case of a pad whose net is
    # new; the BUCK_PG attempt is what it was written for.
    "post_route_nets": ("SHDNZ1", "SHDNZ2", "SHDNZ3", "SHDNZ4", "SHDNZ5"),
    # ⚠ SAI_FS IS CLOSED HERE, AFTER ROUTING, AND THAT TIMING IS THE ENTIRE ANSWER.
    # This net was the board's last unconnected item for a dozen routes. Everything tried
    # BEFORE routing made it worse, every time, and the count is worth keeping because the
    # trend is the lesson: declaring its whole path on F.Cu -> 4 unconnected; the same haul
    # on B.Cu -> 6; a 1.2 mm stub and one via -> 3; moving its spine to B.Cu -> 6; swapping
    # lanes with SAI_SCK -> 7. Baseline with none of it: 1. Every one of those was verified
    # geometrically clear and every one produced 0 DRC violations -- they did not short
    # anything, they crowded neighbours out of lanes those neighbours still needed.
    # This is the same finding _add_via's note already records for +3V3A ("four successive
    # attempts all reached for router SETTINGS and all four made the board worse") and the
    # same one the repair block in route.py was built for. It was rediscovered the
    # expensive way; it is written here so it is not rediscovered again.
    #
    # WHY THE NET COULD NOT ROUTE. Not congestion in general -- the ROUTER SEALS THE PAD.
    # U6.3 sits between U6.2 (SAI_SD2) and U6.4 (SAI_SCK) on 0.5 mm pitch, both of which
    # escape east across its row, and by the time the router reaches FS its own escape lane
    # is gone. Measured on the finished board, the pad's reachable region is ~360 grid
    # cells: it is enclosed. No amount of aiming helps a net that cannot leave its pin.
    #
    # WHY THIS PATH IS LEGAL WHEN NOTHING ELSE WAS. It was searched against the FINISHED
    # board rather than the unrouted one, so it fits the copper that will actually be there
    # instead of copper that has not been laid yet -- which is precisely the flaw in all
    # five attempts above. It weaves F.Cu -> In2 -> B.Cu -> In2 -> B.Cu -> F.Cu, hopping
    # layers at each blockage, because along y -27.31 B.Cu is 26.0 of 29.05 mm free while
    # F.Cu is 21.2 and In2.Cu only 13.8. The one via site that gets off the pad is
    # (-5.30, -27.26) with 0.515 mm where a 0.6 via needs 0.500 -- it clears by 0.015 mm,
    # and a 0.06 mm search margin had been hiding it.
    #
    # ⚠ IT IS MEASURED AGAINST ONE PARTICULAR ROUTE, so anything that changes the route can
    # invalidate it. That is SAFE rather than fragile: laid here it is checked by the DRC
    # that follows, so a path that no longer fits appears as a clearance error and not as a
    # silent short. If this ever lights up, re-search it against the new finished board with
    # scratchpad/maze.py (MAZE_BOARD=elec/out/optical.kicad_pcb) and re-verify with
    # verify_path.py. Verified clear at 0.02 mm steps: tracks >= 0.268 mm of 0.260, vias
    # >= 0.503 mm of 0.500 on all four layers, and hole-to-hole >= 1.004 mm of 0.250.
    # ⚠ AND IT DOES NOT DRILL ITS OWN ESCAPE VIA, because one is already there. The first
    # version laid a via at (-5.30, -27.26) and it came out 0.055 mm from the via
    # link_close_gaps puts at (-5.2992, -27.315) -- two holes with -0.245 mm of laminate
    # between their walls, i.e. one broken-out hole. KiCad grades hole_to_hole a WARNING,
    # so the pipeline still printed "0 unconnected, 0 violations" over a board no fab house
    # would drill. The repair therefore STARTS at that existing via: the router's own F.Cu
    # stub already carries the pad to it, so the pad is reached for free.
    # ⚠ THE In2 HOP IS OFFSET 0.05 mm ALONG ITS OWN NORMAL, and the audit is why. Run
    # straight between its vias it passes 0.118 mm from an unnetted MCU pad against this
    # board's 0.127 mm rule -- a REAL violation, and one the DRC did not report. Offset it
    # and it clears. Four B.Cu segments remain TIGHT BUT LEGAL at 0.142-0.145 mm against
    # SWCLK and I2C2_SCL vias: over the 0.127 rule, under repair_search's 0.15 SEARCH
    # margin. That is measured and deliberate -- NO path with 0.15 mm of headroom exists
    # from this pin at all (searched at 0.28, 0.285 and 0.29 mm, with and without the
    # border clamp and over a wider region: boxed in every time), so the choice was
    # 0.143 mm or an unconnected frame clock.
    "repair_tracks": [
        # ⚠ RE-SEARCHED AGAINST THE ROUTE OF 2026-09-28 21:5x, AND THE OLD PATH SHORTED
        # SWDIO. That is this mechanism's documented failure and not a surprise: a
        # post-route repair fits ONE route, and freeing the converters' SHDNZ pins changed
        # the route. The previous path came back as a track_crossing plus a shorting_items
        # against SWDIO on B.Cu, which is exactly how it failed the last time too.
        # ⚠ AND THE CORRIDOR THE OLD PATH USED IS GONE, WHICH IS THE LESSON. Searched at
        # 0.26, 0.22 and 0.20 mm over the old region (~170,000 cells each): NO PATH. The
        # router has no reason to leave a lane it cannot see a use for, and this time it
        # took it. Widening the search region from 10 to 22 mm found one -- 40 mm and three
        # vias, F.Cu to B.Cu to In2 and back up -- where the old repair needed 21 mm.
        # The tail was truncated by hand from x 12.70 to 22.30: the maze was aimed at the
        # far end of the spine and ran the last 9.6 mm ON TOP of it, since it has no notion
        # that its own net's copper is a destination rather than an obstacle.
        # ⚠ AND y -25.42 IS THE MIDDLE OF A 0.063 mm WINDOW, measured after DRC rejected
        # -25.46 by 5.5 microns. maze.py's TRK is a WIDTH and it blocks cells within
        # TRK/2 + 0.06 of an obstacle, so TRK 0.24 modelled 0.18 mm of clearance where a
        # 0.25 mm track needs 0.127 + 0.125 = 0.252. Re-run with the honest TRK -- 0.384 --
        # the search cannot even leave the start cell. So this path is kept and the one
        # segment DRC caught was moved into the gap between the SAI_SCK via to its south
        # (needs y >= -25.455) and the MCU's pads 169/170 to its north (needs y <= -25.392).
        # -25.38 was tried first and failed the other way, against the pads, by 12 microns.
        # ⚠ STARTS ON THE TRACK'S TIP, (-6.5492, -27.315), not 0.07 mm past it. The maze
        # rounds to its grid, and a repair that lands mid-stub rather than on its end leaves
        # the tip sticking out.
        # ⚠ AND THE track_dangling WARNING ON THAT TIP SURVIVES ANYWAY -- chased, then
        # dropped. Writing the fourth decimal does not reach the board: 93.4508 goes in and
        # 93.4510 comes out, so the two ends sit ~0.2 microns apart and KiCad keeps grading
        # the tip dangling. It is a WARNING, and the connection is real -- the board is at
        # 0 unconnected, which is the check that decides it. So it stays as the fourth line
        # in a warning list whose other three are deliberate spine ends.
        # ⚠ RE-SEARCHED AND RE-MEASURED AGAINST THE ROUTE OF 2026-09-30, AND IT CLOSES
        # THE BOARD: DRC goes 1 unconnected item -> 0, with the violation list IDENTICAL to
        # the baseline (20 declared sensor-triplet courtyards, 0 unexpected). This is the
        # last open net on the optical board.
        # ⚠ AND THE "BOXED IN EVERY TIME" VERDICT ABOVE WAS AN ARTEFACT OF THE SEARCH,
        # NOT THE BOARD. Every one of those searches ran a tool that (a) modelled a pad as a
        # stadium or a circle rather than its real rounded rectangle, (b) could not see the
        # GND pours at all, and (c) could express at most ONE via -- while both SAI_FS
        # islands sit on F.Cu with no F.Cu path at any clearance, so the repair MUST leave
        # the layer and come back. A search that cannot represent the answer reports "no
        # path" in exactly the same words as a board that has none. With maze3d (layers in
        # the search space, vias as edges) the path falls out in 213 s at reach 12.0, and
        # its worst gap against every obstacle class INCLUDING THE POURS is +0.2602 mm --
        # not a near miss on a 0.127 rule, twice the headroom.
        # The old 4-run/3-via path is deleted rather than kept: it was measured against a
        # route that no longer exists, and re-deriving it costs 213 s.
        ("SAI_FS", "F.Cu", 0.127, [(-6.5492, -27.3150), (-6.3992, -27.2887),
                                   (-4.7492, -27.2887), (-4.5992, -27.1387)]),
        ("SAI_FS", "B.Cu", 0.127, [(-4.5992, -27.1387), (0.0508, -22.4887),
                                   (1.2508, -22.4887), (4.2508, -19.4887),
                                   (12.2008, -19.4887), (12.9508, -18.7387)]),
        ("SAI_FS", "F.Cu", 0.127, [(12.9508, -18.7387), (12.8008, -18.7387),
                                   (12.6500, -18.8887)]),
        # ── +3V3D at U6 pin 36: a DOG-LEG, and the shape is the whole point ──────────
        # The 2/0 board's remaining unconnected items are two +3V3D pads, and repair_search
        # reported "0 same-layer paths, 0 via paths" for BOTH. That is the signature of a
        # broken filter (padsite.py: "40548 of 40548 points failing the same criterion is a
        # broken test, not a full board"), so it was measured rather than believed -- and the
        # tool is right about what it TESTS. track_gap at this board's own 0.127 width, against
        # the 0.127 rule, on every straight hop to the nearest own-net copper:
        #     U6.36 -> (91.781,142.259) 2.282 mm   gap -0.2135  vs pad [no net]
        #     U6.36 -> (91.781,145.402) 2.304 mm   gap -0.2135  vs pad [GND]
        # NEGATIVE -- the straight track would sit INSIDE a pad, by 0.2 mm. Narrowing to
        # 0.100 recovers only 0.0135, because the obstruction is a pad BODY, not a clearance.
        # ⚠ BUT repair_search MODELS ONLY TWO SHAPES -- one straight track, or via-plus-spur
        # (its own docstring: "TWO SHAPES OF REPAIR"). A DOG-LEG ROUND THE PAD IS NOT TRIED,
        # and that is the obvious move when a single pad is 0.2 mm in the way. Searched with a
        # knee on 0.1 mm rings: 2 legal paths, and the best has 0.1557 mm of headroom -- which
        # CLEARS THE SEARCH'S OWN 0.15 MARGIN, so the tool would have accepted this path had it
        # ever looked for it. The gap is measured at 0.127 width, so the width below must stay
        # 0.127: the 0.25 the SAI_FS entries use would eat the clearance this was chosen for.
        # (the PHY supply pad, the other break, has NO legal dog-leg at 0.127 -- see the doc. It needs a
        # third segment, a via smaller than 0.6, or a placement nudge, and it is still open.)
        # ⚠⚠ COMMENTED OUT FOR THE 2026-09-30 RE-ROUTE, AND IT MUST BE RE-SEARCHED, NOT
        # RE-ENABLED. These three points were measured against the route of 2026-09-29 23:55.
        # A post-route repair fits ONE route -- that is this mechanism's documented failure
        # mode, and SAI_FS has demonstrated it twice by coming back as a track_crossing plus a
        # shorting_items after a placement change. Adding a PHY pin to pin_escapes moves copper in
        # the same QFN fan-out this dog-leg threads through, so its knee is the LAST thing that
        # can be assumed still clear.
        # It cannot be gated through STALE_REPAIRS either: that filter keys on the NET, and
        # "+3V3D" names this one dog-leg plus the ten _shdnz_stubs() tracks and five
        # _shdnz_vias() that feed the SHDNZ pull-ups. Gating the net would delete fifteen
        # working pieces of copper to disable one, which the counted assert there now refuses.
        # TO RESTORE: re-run the knee search against the NEW board (rings on 0.1 mm, both legs
        # at 0.127 width and the 0.127 rule, pours ignored because repair_planes refills), lay
        # it, refill, and check DRC shows no clearance violation. Last time that was
        # 4 unconnected items -> 2 with violations identical to the baseline.
        # ⚠ THE +3V3D DOG-LEG IS DELETED, AND IT WAS NOT WRONG -- IT BECAME UNNECESSARY.
        # It closed U6 pad 36 when +3V3D had no copper nearby: knee at (-7.2470, -43.8660),
        # measured on rings against the route of 2026-09-29, worth 4 unconnected items -> 2.
        # Giving VDDIO its own bypass cap (C119, at pin 9) put a +3V3D pad in that region, and
        # the ROUTER now closes pad 36 by itself. Tested rather than assumed: the two segments
        # were deleted from the finished board and DRC came back IDENTICAL -- same 4 items, same
        # violations, +3V3D still fully connected -- so they were carrying nothing.
        # Keeping it would have been the worse kind of dead weight: hand-laid copper re-laid
        # blind into every future route, at coordinates that only happened not to short this
        # time. The repair mechanism is not in question; this particular repair is retired.
        # +3V3A at U11 pad 5: a MAZE path, and the first repair this board has taken from
        # the new search. 25 points, 15.541 mm, worst clearance +0.1804 against a 0.127 rule.
        # Laid on the finished board and refilled, it takes DRC from 6 unconnected items to 4
        # with violations IDENTICAL to the baseline.
        # WHY 15.5 mm FOR A 6.97 mm GAP: straight is blocked, a dog-leg is blocked, and
        # via->In2->via is blocked -- 63 legal via sites at the pad and 224-563 at the islands,
        # but all ~8000 sampled pairs fail on the run BETWEEN them, because In2 carries no pour
        # yet the board's 400 vias pierce every layer. The detour is what exists.
        # ⚠ SEARCHED AT clearance 0.175, NOT THE 0.127 RULE, AND THAT IS NOT PADDING. At the
        # rule itself the path grazed C114 pad 2 and DRC returned four clearance violations of
        # 0.0864-0.1105 mm, because _pads models a pad as a STADIUM (a capsule with fully
        # rounded ends) where KiCad pads are ROUNDED RECTANGLES, which reach further at the
        # corners. 0.175 covers that underestimate; the model itself still wants fixing.
        ("+3V3A", "F.Cu", 0.127, [
            (7.6039, -61.1300), (7.3864, -60.9300), (3.0364, -56.5800),
            (3.0364, -56.2800), (2.5864, -55.8300), (2.2864, -55.8300),
            (2.1364, -55.9800), (1.8364, -55.9800), (1.6864, -55.8300),
            (1.5364, -55.8300), (1.3864, -55.9800), (1.2364, -55.9800),
            (1.0864, -56.1300), (0.7864, -55.8300), (0.4864, -55.8300),
            (0.0364, -56.2800), (0.0364, -59.8800), (0.1864, -60.0300),
            (0.1864, -60.1800), (0.3364, -60.3300), (0.3364, -60.4800),
            (0.4864, -60.6300), (0.4864, -60.7800), (0.6364, -60.9300),
            (0.6364, -61.0800)]),
        # ⚠ +3V3A's SECOND break IS NOW A FEED, NOT A REPAIR (2026-10-01). What stood here was
        # 62 mm of 0.127 mm from the cross-layer maze, F.Cu -> via -> In2, and it "closed the
        # net" -- true, and it hid what the net WAS: U9's output (the quiet LDO) on one
        # island, every op-amp and converter on another, and that thread the only thing
        # between them. So the whole analog rail, ~150 mA, was fed LDO -> 70 mm at 0.127 ->
        # U6's own 0.25 mm In2 run -> the spine: ~0.45 ohm, ~65 mV, and shared by every ADC's
        # AVDD. DRC cannot see it (connected is connected), and the width tally that found the
        # panel's and the motor board's thin power found this one.
        # The same search at an honest width: 0.8 mm on B.Cu, ~50 mm, two vias, from U9 pad 5
        # to the spine's own via at (-20.08, -21.08). Worst gap 0.2756 (the F.Cu stub at U9) against a 0.127 rule
        # (repair_search.track_gap on the routed board, every segment, at half 0.4). ~30 mohm.
        ("+3V3A", "F.Cu", 0.5, [(-5.16, -61.13), (-5.48, -60.73)]),
        # ⚠ IT GOES WEST OF THE MOUNTING HOLE at (-16.91, -27.83): the maze does not model
        # Edge.Cuts circles or their keepouts, and its straight diagonal ran through both.
        ("+3V3A", "B.Cu", 0.8, [(-5.48, -60.73), (-9.88, -56.33), (-9.88, -49.33),
                                (-10.08, -49.13), (-10.08, -36.0), (-12.08, -34.0),
                                (-20.2, -34.0), (-20.8, -33.4), (-20.8, -24.6),
                                (-20.08, -23.33)]),
        ("+3V3A", "F.Cu", 0.5, [(-20.08, -23.33), (-20.08, -21.08)]),
    ] + _shdnz_stubs(),
    "repair_vias": [("+3V3A", -5.48, -60.73), ("+3V3A", -20.08, -23.33),
                    ("SAI_FS", -4.5992, -27.1387),
                    ("SAI_FS", 12.9508, -18.7387)] + _shdnz_vias(),
    # ⚠ NO track_mm HERE: 0.15 was TESTED AND IS WORSE. It helps lever_sensor, whose
    # 0.4 mm pitch QFN needs the lane, and it hurt this board -- 12 unconnected and no
    # violations at the 0.25 default, against 15 and a real clearance violation at 0.15.
    # The finest part here is 0.5 mm pitch, which 0.25 clears comfortably, so there was
    # no escape problem to solve; all the narrowing did was change the geometry the pair
    # router and the stitcher had already been fitted around.
    # Narrower track is not "more room" for free -- it is a different board.
    # ⚠ AND EVERY GROUND PAD GETS ITS OWN VIA TO THAT PLANE. The F.Cu pour connects
    # them all when the board is placed -- and then 2,400 track segments chop it into
    # islands, every island that reaches no via becomes unconnected copper, and island
    # removal deletes it. 86 ground endpoints went that way. A via per pad makes the
    # connection independent of whatever the router does afterwards; the pour stays,
    # but as a bonus rather than the mechanism.
    # ⚠ THE TWENTY SENSING CELLS ARE ROUTED BY THE AUTOROUTER, AND I TRIED TO TAKE
    # THAT AWAY FROM IT AND COULD NOT. Each cell is the same four connections twenty
    # times -- photodiode into the summing node, the op-amp's inverting input, and the
    # feedback R and C across it -- and that node carries TENS OF NANOAMPS, so its loop
    # area is worth pinning down rather than re-rolling every time the board is
    # regenerated. I built a pre-router for it (straight and L-shaped paths between the
    # cell's own pads, collision-checked) and it placed SEVEN segments out of about
    # sixty before running out of clear paths.
    #
    # THE REASON IS THE INTERESTING PART: the parts in this strip sit a fraction of a
    # millimetre apart, so almost every path between two pads of one cell is blocked ON
    # F.Cu -- and the autorouter gets through because it drops to In2.Cu and B.Cu and
    # comes back. Matching that would mean placing vias and routing on inner layers,
    # which is writing a router, not configuring one. A pre-router that does an eighth
    # of the job while a comment claims the summing node is deterministic would be
    # worse than none, so there is none.
    #
    # ⚠ WHAT THAT LEAVES -- AND ONE HALF OF IT IS NO LONGER TRUE. This paragraph used to
    # end "the most sensitive geometry on this board is chosen by freerouting and DIFFERS
    # BETWEEN RUNS". Measured 2026-09-19 by routing optical twice from the same netlist
    # and hashing the result: the two .kicad_pcb files are BYTE-IDENTICAL, same md5,
    # 0 unconnected and 0 violations both times. Freerouting is deterministic given
    # deterministic input, and route.py canonicalises the UUIDs that used to be the only
    # thing separating two runs.
    #
    # So the limitation is smaller and differently shaped than it was written down as:
    # the summing-node geometry is still CHOSEN BY THE ROUTER rather than designed, which
    # is the real complaint, but it is stable, measurable and reviewable. If the analog
    # performance ever disappoints, you are debugging a fixed target rather than a moving
    # one -- and the fix is still to give the strip more room so the
    # cells CAN be wired on one layer, not to tune the router.
    # ⚠ THIS DECLARATION CURRENTLY FAILS, ON PURPOSE, AND THAT IS THE POINT.
    # layout.py reports "inner run U7->U10 blocked" on every build and verify.py fails
    # the pair's skew afterwards. Both are telling the truth about the same thing: THE
    # COMPUTE BLOCK'S PLACEMENT DOES NOT LEAVE ROOM FOR A PROPER USB PAIR. The PHY sits
    # above two rows of parts, so there is no top-layer path to the connector, and the
    # inner layer -- the normal escape -- is perforated by the 75 ground stitches that
    # every ground pad needs. Reserving a corridor was tried and the run still cannot
    # get across.
    #
    # THE FIX IS PLACEMENT, NOT ROUTING: the USB chain (PHY -> ESD -> connector) has to
    # be placed as a deliberate group before the row packer fills in around it, the way
    # U10 now is. That is a re-plan of the -Y block against the conduit budget, which is
    # a design decision rather than a patch, and it is left as one.
    #
    # The declaration STAYS so the failure stays visible. Deleting it would make the
    # build quiet and the board no better -- freerouting would go on laying DP and DM
    # as two unrelated traces, which is what it did before anyone looked.
    #
    # ⚠ THE USB PAIR SHOULD BE ROUTED AS A PAIR, because freerouting cannot. It routes
    # DP and DM as two independent nets that happen to share endpoints -- 39.6 mm of DP
    # against 32.0 of DM over a 22 mm path, two traces on visibly different routes. The
    # timing skew that implies is survivable (46 ps against a 2,080 ps bit); what is not
    # is that two traces on different paths are not COUPLED, so the differential
    # impedance the stack-up was designed around stops describing the interconnect.
    # That is a geometric defect, not a numeric one, and no budget value fixes it.
    # The chain is the order the signal physically travels: PHY -> ESD array -> socket.
    "diff_pairs": [{"nets": ["USB_DP", "USB_DM"], "chain": ["U7", "U10", "J1"],
                    "gap": 0.2, "width": 0.2}],
    # In2.Cu is the pair's escape layer: it sits directly under the In1.Cu ground
    # plane, so the run is referenced to solid copper for its whole length, and it
    # carries no pads at all -- which is what makes a clear path possible under two
    # rows of components.
    "diff_pair_inner": "In2.Cu",
    # ⚠ A RESERVED CORRIDOR FOR THAT INNER RUN, because the two features above compete
    # for the same copper. Stitching 75 ground pads puts 75 THROUGH vias in, and a
    # through via pierces In2.Cu as surely as F.Cu -- so the inner layer the pair needs
    # becomes a sieve and the 15 mm run from the PHY to the ESD array cannot get across
    # it, with or without dog-legs. Whichever routine runs first wins and the other
    # fails; reserving a lane is what lets both succeed.
    # x -34..-28 is the column between U13 and L1, which the pair already travels; the
    # ground pads displaced from it fall back to the pour, which is what they had
    # before any of this existed.
    # ⚠ THE SECOND RECTANGLE FENCES THE TWO SPINES IN THE WEST CHANNEL. The stitcher
    # places a ground via 0.9 off its pad and knows nothing about pre-laid copper, so it
    # dropped Cm54's onto the +3V3D trunk -- 0.100 mm where the fab rule is 0.127, the
    # single unexpected violation on an 8-unconnected board. Excluding the pad would have
    # cost that cap its ground; fencing the lane keeps the stitch and moves the via, which
    # is the same trade the escape fan already makes. Sized off the copper: the +3V3D
    # trunk at -33.268 (0.30 wide) and the I2C spine at -34.398 (0.25) each need
    # 0.127 + 0.30 + half their width of room for a 0.6 mm via.
    # ⚠ THE SECOND ONE IS DERIVED, AND IT WAS NOT, WHICH BROKE IT SILENTLY. Written as
    # literal coordinates it fenced the spines correctly -- until STRIP_GROW_MX moved the
    # whole column 1.5 mm west and the fence stayed put, leaving the I2C spine at -35.148
    # outside a keepout running to -34.95. Nothing failed: the DRC stayed at 0 violations
    # and SCL simply came back unconnected, which reads like the spine not working rather
    # than like a keepout that had quietly stopped covering it.
    # A keepout around moving copper has to be computed FROM that copper.
    # ⚠ _door_keepout() IS NOT IN THIS LIST, AND THAT IS THE MEASURED ANSWER, not an
    # oversight. Fencing the stitcher out of the coupling-cap doors is the right idea --
    # in four of five cells it puts ground copper straight through the only way into a
    # Ci pad -- but it bought ZERO extra comb runs and cost four Cm caps their ground
    # connection outright ("no room for a stitching via beside Cm24.2, Cm34.2, Cm44.2,
    # Cm54.2"). Those pads are boxed between the +3V3D trunk at x 9.05 and the I2C spine
    # at 7.92, 1.13 mm apart where a via needs 1.20, so with the door fenced there is no
    # legal spot left in any direction. Ground through the pour alone is worse than a
    # crossed door: routing can orphan a pour, and these are the converters' own
    # reference caps. The function is kept because the diagnosis is sound and the fix
    # belongs at the other end -- widening that channel, which is ADC_BUS_CH in
    # src/optical_pickup.py and was already widened once (2.4 -> 4.2) for this column.
    # ⚠ AND ONE MORE DOOR, THIS TIME THE MCU's (user spotted it in the routed board,
    # 2026-09-25: "there are already ground vias directly to their west where these new
    # vias ideally would go -- do the ground vias need to be so close?").
    # SAI_FS is U6.3 at (-6.55,-27.31) and SAI_SCK is U6.4 at (-6.55,-27.81), and both
    # need an escape via about a millimetre west. C106's ground via sits at (-8.22,-27.92),
    # which leaves 0.62 between centres where two 0.6 vias need 0.75. Two of the four nets
    # this board still fails on are the two pins that via is parked in front of.
    #
    # The answer to the user's question is yes AND no: it ties C106.2 at 0.81 mm and a
    # bypass capacitor's via IS its loop, so it must stay that close -- but not on that
    # SIDE. The stitcher tries eight directions at increasing radius and takes the first
    # that clears other PADS; it knows nothing about a neighbour's escape. Measured at the
    # same 0.81 mm radius, WEST has 0.95 mm and NORTH-WEST 1.32, so the loop is unchanged
    # either way.
    # The fence is the north spot only, and it stops short of x -8.55 so the west and
    # north-west candidates stay legal -- see _door_keepout's note for what happens when a
    # fence leaves a pad no direction at all.
    "via_keepouts": [[-34.5, -101.0, -27.5, -78.0],
                     [-8.55, -28.45, -7.00, -26.90]] + _spine_keepout(),
    # ⚠ THE FEEDBACK CLUSTERS, LAID HERE RATHER THAN SEARCHED FOR. Twenty identical
    # networks -- op-amp output, feedback R, feedback C, and the photodiode on the input
    # -- packed into the Y gaps of a 13.6 mm strip that already holds 107 parts. Nearly
    # every unconnected pad this board reports is one of them failing to reach the pin
    # beside it, and they are the most generator-shaped thing on the board: the same
    # three-pad star, twenty times, at a spacing the string fan fixes.
    # Only the LOCAL cluster is laid; the long run to the converter's coupling cap stays the
    # router's, which is the half it is good at. See _local_nets.
    # ⚠ THE POWER RAILS ARE *NOT* IN THIS LIST, AND THAT WAS TESTED. Since the emitters
    # and the quads were separated onto V5_PRE and +3V3A, the sensing strip carries two
    # rails where it carried one, and both route -- they just take the room the TIA
    # outputs wanted. Pre-laying their local hops (each quad to its own two decoupling
    # caps) looked like free space: the router would keep the copper it needs and lose
    # work it does not.
    # MEASURED: 9 unconnected but THREE clearance violations, against 10 and none. It
    # laid one extra segment and cost a manufacturable board. A violation is worse than
    # an unfinished net -- one board cannot be made, the other is not done -- which is
    # the rule finish.py already sorts by.
    # ⚠ +3V3A DOES NOT BELONG HERE, MEASURED: adding it took the board from ONE
    # unconnected net to THREE. After the strings 2/10 swap the only open net was +3V3A
    # -- a 5.93 mm gap between U2's supply pin and its own decoupling cap, well inside
    # _local_nets' 6 mm single-linkage reach, and ten identical op-amp-to-its-own-cap
    # hops are a pattern rather than a search, which is exactly what this routine is for.
    # It laid 122 segments and cost two nets.
    #
    # The reason is the one this file keeps re-learning: PRE-LAID COPPER IS FREEDOM THE
    # ROUTER CANNOT GET BACK. Going wider made output_panel 2 -> 5 and lever_sensor
    # 4 -> 7; here the twenty analog nets the swap had just freed were competing for the
    # same strip, and 122 fixed segments through it closed the corridor they were using.
    # The rail is better off routed than helped. Third time this lever has been tried and
    # lost -- treat "add one more net to the pre-lay" as measured-negative, not untested.
    # ⚠ MID IS A LOCAL NET TEN TIMES OVER, which is why it is in this list rather than
    # being given a spine of its own. It has 63 pads -- six per station (both MID pads of
    # each detector, and both non-inverting inputs of the dual) plus the buffer and its
    # bypass in the south -- and the six per station are a CLUSTER a couple of millimetres
    # across, exactly the shape this routine exists for. Hand-laying it was started and
    # abandoned: the op-amp's MID pins sit either side of GND on a 0.65 mm pitch, so
    # reaching them is a fan-out, and _local_nets already solves fan-outs. Single linkage
    # finds the ten stations on its own; what it will NOT do is join station to station,
    # and that is the rail, below.
    # ⚠ AND THE CONVERTERS' OWN REGULATOR/REFERENCE PINS, which were unconnected in every
    # cell -- AREG, DREG and VREF, two islands each, five cells, FIFTEEN connections the
    # router was drawing. Each is a pin and the bypass cap sitting directly beside it: the
    # shortest connection on the board, and the most obviously local. Found by the user
    # noticing the same short ratsnest stub repeating in all five cells ("whenever I see
    # that repetition I get suspicious"), which is a better detector for this class of
    # fault than anything automated here -- a per-cell omission looks like nothing at all
    # in a total, and like a pattern the moment you see the board.
    # ⚠ MID IS NOT IN THIS LIST, AND MUST NOT GO BACK IN -- see _mid_spine. Put back
    # (2026-09-24) to test whether the spine had become unnecessary now that TIA_IN_B
    # is laid first and takes a clean route: it has not. The MST went straight back to
    # crossing the TIA_IN lane and dropped all ten B channels again.
    "local_nets": (r"TIA_IN_\d+[AB]", r"TIA_OUT_\d+[AB]", r"\+3V3A",
                   r"ADC\d+_AREG", r"ADC\d+_DREG", r"ADC\d+_VREF",
                   r"LED_A\d+"),
    "local_mm": 6.8,

    # ⚠ THE NORTH HALF IS FROZEN, and it is only safe to freeze now (2026-09-24). This
    # turns every pre-laid run into freerouting's `(type fix)`, so the router is left with
    # the south half and the seven border crossings -- which is what the user asked for:
    # "scope the auto router to only check connections south of the border".
    #
    # route.py's note warns that freezing pre-laid copper is a TRADE, because fixed copper
    # stops being negotiable and this project has measured that going the wrong way. The
    # trade only pays when the frozen half is finished, and it now is: every net with pads
    # in the string array reaches the border under its own steam, nothing hands over more
    # than 5 mm up, and DRC reports no routing violation anywhere in it. Freezing an
    # UNFINISHED north half would be the mistake that note is about.
    #
    # If this is ever turned off again, expect the router to rip up the spines: it has no
    # idea that MID's B.Cu run is a bias reference or that the comb pattern is congruent
    # by construction, and it will happily trade both for a shorter total.
    "fix_prelaid": True,
    "stitch_nets": ("GND",),
    # ⚠ AN EXCEPTION LIST IS A SNAPSHOT OF A LAYOUT, and it goes stale silently: a pad
    # excused because the stitcher could not reach it stays excused after a re-plan makes
    # it reachable, and then sits unconnected on a routed board with nothing complaining.
    # Empty is the right default; re-add only what the stitcher reports.
    # J1's shell tabs are through-hole: their barrels reach the plane. Before the layout
    # fix that gives every duplicate-numbered pad its net, three of the four had no net and
    # drew no via; stitching them now re-planned the board and left TIA_OUT_1B open.
    # U14-U18 pin 4 (AVSS): TI wants AVSS shorted straight to the thermal pad, and it sits
    # beside it -- so it gets exactly that, a 0.2 mm track into the EP (see "tracks"),
    # rather than a via among the AVDD/AREG/VREF caps the cell puts on that side.
    # ⚠ THE F.Cu POUR DOES NOT DO IT, MEASURED: the pin's inner end is 0.20 from the EP and
    # the pour's 0.3 clearance cannot enter, so all five AVSS pins came back unconnected.
    # ...and pins 15/16 (ADDR1/ADDR0, both GND since the five parts share one address) the
    # same way, into the EP from the other side: stitched like ordinary GND pads, their vias
    # landed across the SHDNZ escape beside them and shorted it.
    # ⚠ PINS THE ROUTER STRANDS, ESCAPED BY NAME (user found each one by eye, 2026-09-25:
    # "this disconnected net SAI_FS doesn't have a via but seems like it needs one", then
    # ULPI_D1, then ULPI_D6). They are fine-pitch pins whose neighbours took the escape
    # positions first; the router spends the good spots on whichever net it reaches first
    # and never goes back. layout's stitcher searches for a legal via beside a pad and lays
    # the stub with it, which is exactly the operation needed, so these just name the pins.
    # ⚠ BY REF.PAD, NOT BY COORDINATE -- the coordinates version went stale the moment the
    # board's length changed and every pad moved 1.1 mm out from under its declared via.
    # ⚠ MORE ESCAPES IS NOT MONOTONICALLY BETTER, and that is worth recording because the
    # mechanism looks like it should be. These three took the board from 7 unconnected to
    # 5 with no ULPI net failing at all. Adding a +3V3D pin of the PHY and U18.18
    # (I2C2_SDA at the last converter) -- both the same "disconnected at a pad with no via"
    # shape -- took it to EIGHT, and broke ULPI_NXT, SAI_SD2 and SAI_SD4, which had been
    # fine. An escape via is not free: it claims a position in the same crowded fan the
    # other pins escape through. Add one only for a pin that is actually failing, and
    # measure after each.
    # U6.38 added alone, and this one is an ELECTRICAL fix as much as a routing one: the
    # MCU's analog supply pins (38 and 39, +3V3A) had NO local via -- the nearest was
    # 27.32 mm away, so VDDA reached its rail across the board. That is poor decoupling
    # whether or not the router ever closes it, and +3V3A has been in the failure list of
    # nearly every routing this board has had.
    # C125.1 is the oscillator's supply: three pads on one island, 10 mm from any other
    # 3.3 V copper, and the same shape as the PHY's bypasses that came back as islands.
    # (The PHY's four control pins are not here: their vias are laid, in _phy_copper.)
    "pin_escapes": ("U6.3", "U6.38", "U6.45", "C125.1"),
    # ⚠ U6.38 CARRIES ITS OWN INNER RUN TO THE +3V3A SPINE. The escape via gave the MCU's
    # analog supply a local connection (27.32 mm -> 1.25) and took the board from 5
    # unconnected to 3, but the router still would not join that via to the rail: +3V3A's
    # In2 spine is 28 mm west at (-20.08, -21.08) and the direct line clips a GND via.
    # MEASURED on In2 against the unrouted board, with a checker that knows an F.Cu LAND
    # does not block an inner layer (it did not, at first, and walled off the MCU's whole
    # pad field): one bend at (-9.0, -41.0) clears everything, 28.1 mm against 28.0 direct.
    # So this costs the rail essentially nothing -- it is the straight line with a nudge.
    # The run is laid by layout FROM THE VIA IT PLACED, not from coordinates written here:
    # a hard-coded escape position went stale once already when the board's length changed.
    # ⚠⚠ THE WAYPOINT AT (-12.00, -24.00) EXISTS TO DODGE THE TAIL MOUNTING HOLE, AND THIS
    # ENTRY IS WHY THAT HOLE COULD NOT BE PLACED (2026-09-29). The straight run from
    # (-9.00, -41.00) to (-20.08, -21.08) passes 0.385 mm from the hole's centre -- through
    # it -- and produced two of the board's violations:
    #     items_not_allowed:     Track [+3V3A] on In2.Cu, length 22.7941 mm
    #     copper_edge_clearance: Circle on Edge.Cuts + Track [+3V3A], actual 0.0000 mm
    # ⚠ AND NO GUARD COULD HAVE CAUGHT IT, which is the part worth keeping. The hole's
    # keepout is emitted correctly -- verified in the board, a 24-point polygon of r 2.800
    # centred on it -- but an escape_run is a pair of HAND-TYPED waypoints laid verbatim, and
    # route.py then freezes all pre-laid wire as "(type fix)". A frozen wire ignores a rule
    # area, so the router never had the option to move it. _local_nets is exonerated by
    # construction: both its call sites pass holes=_hole_pts(notes) and seg_clear samples
    # every 0.15 mm, so a 22.79 mm run gets ~152 samples and an r 2.8 hole cannot be missed.
    # escape_runs is simply a pass that never consults _hole_pts.
    # Searched, not chosen: 80 waypoints clear the hole; this one keeps +2.349 mm to it and
    # +6.179 mm to the nearest other declared In2 copper (LED_ROW), and costs 3.06 mm of
    # length. It goes NORTH of the hole, which is the side the spine corner is on anyway.
    # ⚠ THE FIRST THREE WAYPOINTS ARE NEW (2026-10-04), because the crystal and the VDDA
    # capacitors now stand where the old bend at (-9.00, -41.00) was and brought their
    # ground vias with them: the old line ran through C103's and 0.006 mm from C123's.
    # Measured on In2 against the placed board the same way: this one keeps 0.77 mm to the
    # nearest via (C123's old neighbour at (-9.08, -42.26)) and 1.0 or more to the rest,
    # and still passes north of the hole.
    "escape_runs": {"U6.38": ("In2.Cu", [(-10.10, -43.00), (-11.40, -39.00),
                                         (-11.40, -35.00), (-12.00, -24.00),
                                         (-20.08, -21.08)])},
    # +3V3A's last link is U9 -> the analog field, the whole rail (about 150 mA), and
    # the maze that closes it after routing lays 0.2 mm unless told otherwise.
    # +3V3D: the digital rail's last link has been the one between the MCU's ring and
    # the regulator (0.35 A); at 0.2 mm it failed the drop budget.
    # SAI_FS: 0.127, the width its searched repairs have always used -- U6.3 is sealed
    # between two escapes on a 0.5 mm pitch and 0.25 does not get out.
    "close_widths": {"+3V3A": 0.5, "V5_PRE": 0.5,    # V5_PRE: the emitter row's feed, 0.21 A
                     "+3V3D": 0.5, "SAI_FS": 0.127},
    "stitch_exceptions": ("J1.SH",) + tuple("U%d.%d" % (u, p) for u in range(14, 19)
                                            for p in (4, 15, 16))
                         # the PHY's two ground pins and its grounded RESET, each laid
                         # into the flag (_phy_copper)
                         + ("U7.1", "U7.2", "U7.9"),
    # THE CONVERTERS' INPUT FAN, laid rather than routed: from each top pin straight up to
    # its coupling cap's pin-side pad, widening by at most 0.25 -- see CELL_FAN in
    # src/optical_pickup.py for why the router could not find these (12 of 28 open).
    # Pin x (part turned 180): 12 -1.25, 11 -0.75, 10 -0.25, 9 +0.25, 8 +0.75, 7 +1.25 at
    # y +1.96; pin 6 (IN1P) at (+1.96, +1.25), pin 13 (IN4M) at (-1.96, +1.25). A near cap's
    # pin-side pad centres 0.48 below its centre, a far cap's likewise.
    # SHDNZ escapes: pin 14 sits on each part's crowded -X side between IN4M and the
    # grounded address straps, and failed on all five parts in two routings. A stub out to
    # a via 0.9 off the pad lets the router take the net on an inner layer from there.
    # AVSS -> EP, one per converter. Pin 4 sits at (+1.962, +0.25) from the EP centre with
    # the part turned 180 (read off the placed board through pcbnew); the track ends 0.9
    # in from the EP centre, well inside the 2.7 pad. Neighbour pins 3/5 clear by 0.27.
    "tracks": _cell_tracks() + _phy_copper()[0] + _mcu_feed()[0] + _buck_sw(),
    # ⚠ ONE +3V3D VIA PER CELL NOW, NOT TWO: the SHDNZ channel's HEAD via is gone with the
    # channel (pin 14 is pulled up locally -- see _shdn_tracks), and it had to go, because
    # it sat in the only escape from pin 14 and cost five SHDNZ-to-+3V3D shorts. The FOOT
    # via at -3.27 STAYS: _v3_trunk's spine lands on it, so it is how every converter's
    # IOVDD reaches the digital rail. Removing PRE-LAID copper is also the one change that
    # can safely reuse a routing session -- a route legal with an obstacle present stays
    # legal once it is gone.
    "vias": ([("+3V3D",) + _cell_pt(k, _V3_CH_DX, -3.27) for k in range(5)]
             + [("I2C2_SCL",) + _cell_pt(k, _I2C_SPINE_DX, _I2C_SCL_DY)
                for k in range(5)]
             + _led_row_vias() + _mid_vias() + _bus_vias() + _v3a_vias() + _sd_vias()
             + _phy_copper()[1] + _mcu_feed()[1]),
    # ⚠ ORDER OPTIONS ARE PART OF THE DESIGN, and nothing in a gerber records them.
    # Mask colour is usually cosmetic and on this board it is not: twenty photodiodes
    # look up through a 0.30 mm gap that runs 5.40 mm to the cover's aperture, and that
    # gap is a cavity whose walls are the board's own top surface. A green or white mask
    # makes it a light pipe -- ambient that gets past the aperture bounces along it and
    # arrives at a detector from the side, which is the one direction the cover's comb
    # cannot shield and the one error ambient subtraction cannot cancel, because it does
    # not track the emitter. Black mask makes the same cavity a light trap. JLCPCB
    # charges nothing for it.
    #
    # The silkscreen is already gone from around the optics (see strip_silk) -- that was
    # done to silence DRC and happens to be the same answer: white ink beside a detector
    # is a reflector.
    "order_options": {
        "soldermask": "black -- the sensor cavity is a light trap, not a light pipe; "
                      "see the note in optical.py. Functional, not cosmetic.",
        "silkscreen": "white (default). None is printed near the optics anyway.",
    },
    "anchor": "courtyard",
    "refs_on_fab": True,
    # The ten sensor triplets sit at a 1.6 pitch by optical design, so their silkscreen
    # outlines collide with each other and with their neighbours' pads -- 140 warnings
    # for ink the solder mask would clip anyway. See _place_ref's note in layout.py.
    "strip_silk": ("D", "PD"),
    "single_sided": True,      # every part on F.Cu: the optics FIRE UP through it
    "qty_per_instrument": 1,
    "placements": _placements(CX, CY),
}

# ⚠⚠ THE SAI_FS POST-ROUTE REPAIR IS WITHDRAWN AS STALE (2026-09-29). Its own header says
# what it is: "RE-SEARCHED AGAINST THE ROUTE OF 2026-09-28 21:5x ... a post-route repair fits
# ONE route". The mount holes and the -X mount move changed the route, so the path it was cut
# for no longer exists, and it now supplies THIRTEEN of the board's fifteen violations --
# SAI_FS shorting or crossing SWCLK, SWDIO, I2C2_SCL, SAI_SD2/SD3 and ULPI_D7.
# ⚠ THIS IS A DELIBERATE TRADE, TAKEN ON THIS PROJECT'S OWN RULE: "a violation is worse than
# an unconnected pad -- one is a board that cannot be made, the other a board that is not
# finished." Withdrawing it should cost SAI_FS its connection and buy back thirteen
# violations, which converts an unmakeable board into an unfinished one.
# ⚠ AND THE ORDER MATTERS, which is the lesson this keeps teaching. Re-searching the repair
# against a route that is still moving is exactly what produced this: the path was fitted, the
# placement then changed underneath it, and the fit became a short. Let the board settle
# FIRST, then search the repair once against the final route.
# ⚠ THE SEARCH TOOL NAMED IN THE TICK PROMPT DOES NOT EXIST. There is no scratchpad/
# directory at all -- no maze.py, no verify_path.py, no repair_search.track_gap -- so
# re-searching means rebuilding the search, not re-running it. Budget for that, and note the
# repair's own finding when doing it: NO path from this pin has 0.15 mm of headroom (searched
# at 0.28, 0.285 and 0.29, boxed in every time), so the answer was 0.143 mm or an unconnected
# frame clock. The +3V3D and SHDNZ members are NOT implicated and stay.
# Repairs that are RECORDED but must not be laid. Each one's analysis is kept beside its
# coordinates in repair_tracks, because the measurement is the valuable part and re-deriving it
# costs hours; what is switched off here is only the laying of copper.
#   SAI_FS  -- fits ONE route and the route has moved since; re-search before re-enabling.
#   +3V3D   -- the U6.36 dog-leg. It CLOSES the break (DRC: 4 unconnected items -> 2, verified
#              in place with the real rules) and it costs TWO clearance violations, so it is a
#              net loss as it stands. ⚠ AND THE REASON IS A HOLE IN repair_search, NOT A NEAR
#              MISS: its Board parses segments, vias, pads and edges and NOT ZONES, so the
#              +0.1557 mm headroom it measures is headroom against everything EXCEPT the GND
#              pour -- and this board's ZONE clearance is 0.5000 mm, four times the 0.127 the
#              search compares against. Measured after laying: 0.4892 mm (0.011 short) on the
#              first leg and 0.0225 mm on the second. repair_planes.py does not rescue it.
#              So a repair on this board has to be searched against the POURS as well, at
#              0.5 mm, and neither leg of this dog-leg survives that. Re-enable only when the
#              search knows about zones.
# ✅ +3V3D IS OFF THIS LIST AGAIN, AND THE REASON IS THE REFILL, NOT A NEW PATH. The dog-leg
# below is the SAME geometry that was gated here for costing two clearance violations against
# the GND pour (0.4892 and 0.0225 against a 0.5000 rule). It was not the path that was wrong --
# it was that nothing in the pipeline ever refilled the pour after laying a post-route repair.
# The pour is computed in layout.py during PLACEMENT, before any track exists; repair_planes.py
# reconnects copper the fill stranded but never updated the fill itself. With a genuine
# ZONE_FILLER pass (now in repair_planes) the pour retreats around the new track and this repair
# is clean: 4 unconnected items -> 2, violations IDENTICAL to the baseline, zero clearance.
# ⚠⚠ GATING BY NET NAME IS THE WRONG GRANULARITY, AND IT NEARLY COST THE CONVERTER ISOLATION.
# "+3V3D" was on this list for one tick, to disable ONE dog-leg. But _shdnz_stubs() emits TEN
# +3V3D tracks -- two per converter cell -- and _shdnz_vias() five more +3V3D vias, so the
# filter would have silently removed the whole SHDNZ supply: fifteen pieces of working,
# verified copper, to gate one. Nothing noticed, because audit_board reads the DECLARATION from
# <stem>.board.json and that file had not been regenerated since the edit, so it kept reporting
# "15 declared, 15 found" from before.
# So the filter now states HOW MANY repairs each name is expected to remove and fails if the
# count is wrong. A gate that removes more than its author meant is exactly the kind of silent
# damage this pipeline has been bitten by repeatedly, and it costs one integer to refuse.
#   SAI_FS -- 4 tracks, 3 vias: fits ONE route and the route has moved. Re-search before use;
#             ⚠ and its "boxed in every time" verdict is doubly suspect, having been reached
#             with a search that tried only two shapes AND could not see the pours.
# ✅ SAI_FS IS OFF THIS LIST, AND THE BOARD IS AT ZERO. Its repair was re-searched against
# the finished route of 2026-09-30 with maze3d and re-measured in place: 1 unconnected item
# -> 0, violations identical to the baseline. The entry that used to sit here read "4 tracks,
# 3 vias" and carried a note that its own "boxed in every time" verdict was doubly suspect --
# it was, and for a third reason nobody had written down: the search could express one via and
# the answer needs two. The list is now EMPTY, which is the point of keeping it typed rather
# than commented: a gate with nothing in it still asserts its own arithmetic.
# ⚠ BOTH ARE BACK ON IT (2026-10-04): the decoupling ring and the crystal moved to the MCU's
# pins, which is a new placement and therefore a new route. The +3V3A trunk's B.Cu leg runs up
# x -10.08 through what is now C123's ground via; SAI_FS's was fitted to the old route's gaps.
# Re-search each against the new finished board, or let close_last have them.
STALE_REPAIRS = {"+3V3A": (4, 2), "SAI_FS": (3, 2)}
for _net, (_nt, _nv) in STALE_REPAIRS.items():
    _t_before = len(BOARD_NOTES["repair_tracks"])
    _v_before = len(BOARD_NOTES["repair_vias"])
    BOARD_NOTES["repair_tracks"] = [t for t in BOARD_NOTES["repair_tracks"] if t[0] != _net]
    BOARD_NOTES["repair_vias"] = [v for v in BOARD_NOTES["repair_vias"] if v[0] != _net]
    _t_gone = _t_before - len(BOARD_NOTES["repair_tracks"])
    _v_gone = _v_before - len(BOARD_NOTES["repair_vias"])
    assert (_t_gone, _v_gone) == (_nt, _nv), (
        "gating %r removed %d track(s) and %d via(s), not the %d and %d it declares. A net "
        "name can cover repairs that have nothing to do with each other -- +3V3D names one "
        "dog-leg AND the ten stubs plus five vias that feed the SHDNZ pull-ups -- so either "
        "the count is stale or this gate is about to delete working copper."
        % (_net, _t_gone, _v_gone, _nt, _nv))


# ── the quality pass (cadkit/PCB_QUALITY.md) ──────────────────────────────────────────────
# Currents are the budget at U8 / U9 above, at its worst-case column.
BOARD_NOTES["quality"] = {
    "power_paths": [
        # 24 V in: 1.07 A of 5 V at the board's worst case is 0.26 A here at 85 %
        {"net": "V24_IN", "from": "J2.2", "to": ["R44.1"], "amps": 0.26},
        {"net": "+24V", "from": "R44.2", "to": ["U13.2", "U13.10"], "amps": 0.26},
        # the buck's output: U8 (digital 3V3, 452 mA at 85 C), the bead to U9, and the
        # ten emitter ballasts at 21 mA each while the row is on
        # the switch node carries the inductor's current: the whole 5 V load, 1.07 A worst
        # case. It is a laid 0.5 mm track (_buck_sw) because routed it came back as
        # 0.25 mm through two vias and an inner layer
        {"net": "SW", "from": "U13.12", "to": ["L1.1"], "amps": 1.07},
        {"net": "V5_PRE", "from": "L1.2", "to": ["U8.3"], "amps": 0.45},
        {"net": "V5_PRE", "from": "L1.2", "to": ["FB1.1"], "amps": 0.17},
        {"net": "V5_PRE", "from": "L1.2",
         "to": ["R%d.1" % k for k in range(1, 11)], "amps": 0.21, "split": True},
        {"net": "+5V", "from": "FB1.2", "to": ["U9.1"], "amps": 0.17},
        # The MCU's sixteen supply pins together ("split"). 0.35 A: ST's maxima are 220 mA
        # at TJ 25 C and 400 at 85 C with every peripheral clocked; this part dissipates
        # about 0.7 W into ~40 C/W, so it sits near 70 C in a 40 C enclosure, and it runs
        # three SAI blocks, USB, one I2C and one timer. Solved as a network the far side
        # of the ring (pins 62-136) loses 58 mV at that current against the 66 mV limit:
        # inside it, and the thinnest margin on the board -- on a route that fed the ring
        # directly. Later routes fed it by way of the PHY and lost 90 mV, so the feed is
        # now laid: _mcu_feed.
        {"net": "+3V3D", "from": "U8.2",
         "to": ["U6.%d" % n for n in (6, 15, 23, 36, 49, 62, 72, 82, 91, 103, 114, 127,
                                      136, 149, 159, 172)], "amps": 0.35, "split": True},
        {"net": "+3V3D", "from": "U8.2", "to": ["U7.6", "U7.16", "U7.25", "U7.30"],
         "amps": 0.08, "split": True},
        {"net": "+3V3D", "from": "U8.2", "to": ["Y2.4"], "amps": 0.01},
        {"net": "+3V3D", "from": "U8.2", "to": ["U%d.19" % u for u in range(14, 19)],
         "amps": 0.005},
        # the analog rail: 26 mA a converter (assumed at 192 kHz -- see the budget),
        # 1.5 mA a dual op-amp
        {"net": "+3V3A", "from": "U9.5", "to": ["U%d.1" % u for u in range(14, 19)],
         "amps": 0.03},
        {"net": "+3V3A", "from": "U9.5", "to": ["U%d.8" % u for u in range(21, 31)],
         "amps": 0.002},
        {"net": "+3V3A", "from": "U9.5", "to": ["U6.38", "U6.39", "U11.5"], "amps": 0.002},
    ],
    "not_power": {
        "VBUS": "a sense line: this board is powered from the 24 V trunk, and VBUS reaches only the "
                "clamp array's rail pin, C130 and R39's 10 k into the PHY's VBUS pin (75 k to "
                "ground: 0.06 mA)",
    },
    "decoupling": {"exempt": {
        "U7.31": "REG_EN, a logic input tied to +3V3D to run the PHY's own 1.8 V "
                 "regulators (DS00001783C table 3-1, pin 31); it draws no supply current",
    }},
    "manual": {
        "M35": "read 2026-10-05. ST ES0392 rev 15 (STM32H742/743/750/753), every entry, against "
               "this board: nothing in it needs a part or a track changed. Not used here: the "
               "internal OTG PHYs (2.2.13 drive limit, pull-up drift), LSE and PC13, the DAC, the "
               "MCU's ADCs, Ethernet, FMC, QUADSPI, SDMMC. No pin is driven above VDD (2.2.14). "
               "PDR_ON is tied high. For the firmware: 400 MHz ceiling on revision Y / W parts "
               "(2.2.21); I2C kernel clock at least 10 MHz for fast mode (2.19.3); SAI master stop "
               "truncates the last clock (2.23, rev Y). The PHY is a USB3300 BECAUSE of an erratum: "
               "Microchip DS80000645A (USB334x), module 2, has that family fail the high-speed "
               "chirp behind some link cores, the STM32's among them, and enumerate at full speed "
               "only. It follows the family's link power management, which the USB3300 does not "
               "have; ST's forum thread on the fault lists the USB3300 as working. For the USB3300 "
               "itself a web search found no errata sheet (2026-10-05); Microchip's product page "
               "refused the fetch, so its documents tab is worth one look at order time. Bring-up "
               "still reads the negotiated speed (docs/optical-bringup-diagnostics.md). JSCJ "
               "publishes none for the oscillator. TI publishes no errata sheet for the "
               "TLV320ADC3140 (searched, none found)",
        "M1": "two cables. J2 <- output_panel J9: two wires. That end is a 2-way XH (1 GND, "
              "2 +24 V), this a 4-way housing with the same two ways crimped and ways 3 / 4 "
              "empty (JST makes no 2-way SMT side-entry XH; the note at J2). It is the "
              "first two ways of the instrument's one order (harness.py: GND, power, ...) "
              "and the XH family says 24 V. Polarised; a CAN drop plugged here lands its "
              "ground and 24 V on the same two ways and its data on empty cavities. J1 <- "
              "the output panel's hub: a stock USB-C lead; D+ on A6 and B6, D- on A7 and "
              "B7, CC1 and CC2 each on its own 5k1, so either way up is the same circuit",
        "M2": "D1-D10 (LTE-C9901): pin 1 K on LED_ROW, the switched low side; pin 2 A on "
              "its ballast; KiCad's LED_0603 pad 1 is K. PD1A-PD10B (PD15-22B): pad 1 A on "
              "MID, pad 2 K on the summing node; the pad numbers are ours, Everlight's "
              "DPD-0000195 rev 4 p.2 calls the cathode lands 1 and 4 and stripes that "
              "side of the body, so the stripe sits on our pad 2, toward the op-amp. No other two-pad polarised part: no TVS, no "
              "electrolytic, no tantalum. Reel rotation is checked at order (M12)",
        "M3": "one ground net (the note at the top of optical()): In1 is an unbroken GND "
              "plane with GND pours on F.Cu and B.Cu, and every ground pad is stitched to "
              "it. The 24 V feed returns on J2 way 1 beside way 2; the buck's loop closes "
              "in its own cell; the emitter row's 0.21 A returns from Q1's source through "
              "the plane directly under its V5_PRE spine. No slot and no split under any "
              "path above",
        "M4": "U13 (LMR33630B, ZHCSHQ3F 9.2.2.6 and its RNX layout example): asks 10 uF of ceramic "
              "in total plus a 100 nF at each VIN / PGND pair for 3 A; this board draws 1.08 A of "
              "the 3 and fits C160 10 uF / 50 V 1206 (about 5 uF at 24 V of bias) + C161 / C165 100 "
              "nF / 50 V, one at each pair. Output: 2 x 22 uF / 16 V 0805 + C164 10 uF at U8, about "
              "28 uF at 5 V of bias, against the table's 2 x 22 uF nominal for 5 V at 1.4 MHz. BOOT "
              "100 nF, VCC 1 uF. U8 (AP2114H): asks 4.7 uF ceramic; C164 10 uF in, C131 10 uF + the "
              "3V3D field out. U9 (TPS7A20): asks 1 uF in and 1 to 200 uF out; C140 1 uF in, C132 "
              "10 uF + the converters' 5 x 1 uF out. PHY: 4.7 uF + 100 nF on each of its two "
              "regulator outputs and 100 nF at each of its four VDD3.3 pins and at the second "
              "VDD1.8 pin (its table 3-1). Y2: 100 nF at its supply land (its sheet's test circuit "
              "shows 10 nF). MCU: 2.2 uF on each VCAP, 1 uF + 100 nF on VDDA / VREF+. Converters: "
              "TI's figure 165 less its four paralleled 100 nF (the note at the Cs parts). Every "
              "capacitor on a 24 V net is a 50 V part and says so in its value",
        "M5": "24 V nets: capacitors 50 V, R44 200 V, U13 36 V operating / 38 V absolute. The rail "
              "is clamped at the panel (D6 there, SMAJ24A: breaks down at 26.7 to 29.5 V, 38.9 V at "
              "its rated 10.3 A) and at the motor board by the same part, and reaches U13 through "
              "the panel's 1 A fuse and R44's 2 ohm with 5 uF behind it: U13's 38 V needs about 9 A "
              "of surge at the clamp, and its 36 V operating limit is above the clamp's breakdown. "
              "This board has no clamp of its own and is only ever fed from the panel's J9. 5 V nets: 16 V bulk, U8 6 V maximum input, "
              "U9 6.0 V (6.5 absolute), fed 5.02 V. 3V3: converters 3.0 to 3.6 V, op-amps 5.5 V, "
              "MCU 3.6 V, PHY 3.0 to 3.6, Y2 2.97 to 3.63. The TIAs run on +3V3A so a saturated "
              "channel cannot exceed the converter's AVDD + 0.3 V. Emitters: 20 mA of 60 "
              "continuous, 28 mW of 100. Q1: 30 V, 5.7 A against 5 V and 0.21 A. Ballasts 72 to 80 "
              "mW whenever the row is held on, 36 to 40 at the 50 % the carrier runs at, in 0402 "
              "parts rated 100 mW (ERJ2RKF1800X; the house 0402 is 62.5 mW and was not used)",
        "M6": "ULPI, 60 MHz, clocked by the PHY: twelve nets, 22.1 to 57.5 mm, a spread of 35.4 mm "
              "(about 0.23 ns) against the 80 mm the board file budgets from the PHY's setup time "
              "(its table 6-2); the pass checks it on every route. All of it runs over the In1 "
              "ground plane, mostly on In2 directly beneath it. The first millimetre or two of "
              "CLKOUT / STP / DIR / NXT at the PHY, out to a via each, are laid by hand (the note "
              "at _phy_copper). The SAI lanes are 12.288 MHz, an 81 ns bit: not length-critical. "
              "USB is M23",
        "M7": "U13: 1.0 V x (1 + 100k / 24.9k) = 5.02 V, TI's own 5 V divider; 4.7 uH against the "
              "table's 2.2 on purpose (0.60 A of ripple instead of 1.29, so the part stays at fixed "
              "frequency down to 0.30 A, under the 0.35 A this board draws with its emitters off: "
              "the note at U13); EN tied to VIN, which the sheet allows; NC joined to SW as the pin "
              "table asks; PG open. U7 (DS00001783C table 3-1 and figure 7-1): RBIAS 12.0k 1 %; "
              "REG_EN high, so it makes its own two 1.8 V rails, VDD1.8 (pins 15 + 26 joined) and "
              "VDDA1.8 (pin 29) kept apart as the pin table demands; RESET to ground, the sheet's "
              "recommendation when unused; VBUS through 10 k, the value figure 7-1 names for a "
              "peripheral, which against the pin's 75 k leaves 4.4 V of a 5 V bus, above the 2.0 V "
              "session-valid ceiling that is the comparator a device uses (note 6-2); XI clocked by "
              "Y2 with XO open (section 6.3); CPEN, ID and EXTVBUS open (a device: ID has its own "
              "pull-up, EXTVBUS its own pull-down). U14-U18: figure 165, MICBIAS left open and "
              "powered down, inputs single-ended and AC-coupled as figure 31 draws them, each INxM "
              "to ground through its own 10 nF. U6: VCAP pair, PDR_ON to VDD, VBAT to VDD, 100 nF "
              "on NRST (C135), BOOT0 pulled down. TIAs: 249k / 2.2 pF, 1.57 times the least stable "
              "feedback capacitance (the arithmetic is at Rf). MID: 9k09 / 1k from +3V3A, bypassed "
              "at the divider (C114), buffered by U11, isolated from its 10 uF by R42. Q1: 100 ohm "
              "in the gate, 100k to ground",
        "M8": "BOOT0: R30, 10k to ground (TP8 to hold it high). NRST: R31 10k up, C135. PDR_ON: "
              "tied to VDD. Converter ADDR1 / ADDR0: all ten to ground -- the five share address "
              "0x4C deliberately and are written together (the note above SAI_CLK); firmware cannot "
              "read one back alone, and one PGA setting serves the same input position on all five. "
              "SHDNZ: 10k to IOVDD on each converter, so they leave shutdown as the rail rises: "
              "firmware MUST issue the software reset before configuring. U7 RESET (active high): "
              "to ground, so the PHY starts from its own power-on reset; REG_EN: to +3V3D; ID: open "
              "on its internal pull-up (a B-device). Y2 enable: to +3V3D. U13 EN: to VIN. U9 EN: to "
              "IN. Q1 gate: 100k to ground, so the emitters are off in reset",
        "M9": "SWD on bare 1.5 mm pads: TP1 SWDIO, TP2 SWCLK, TP3 NRST, TP4 GND, TP5 +3V3D. "
              "A second way in that needs no probe: the ROM bootloader's I2C2 is this "
              "board's own control bus, on TP6 / TP7, selected by holding TP8 (BOOT0) high. "
              "Rails: TP9 the 24 V as it arrives (ahead of R44, so the drop across R44 "
              "reads the input current), TP10 +5V, TP11 +3V3A, TP5 the digital 3V3. Each "
              "converter can be taken off the bus alone by grounding its SHDNZ pull-up's "
              "pad. No pad on MID, on purpose. docs/optical-bringup-diagnostics.md has the "
              "order of work",
        "M11": "finish.py's CAD check: 258 of 258 routed parts present in the CAD, "
               "every one where the CAD draws it. The lead's full build on main "
               "b0e7a911 (2026-10-05) with this board's geometry: 1010 components, 0 "
               "unintended overlaps, the rotating-part sweep clean -- the board, its "
               "parts at their drawn heights, its mated plugs and its cables against "
               "the plastic and the fasteners round it. The two mounting holes are "
               "cuts in the outline with their keep-outs in the board file, so DRC "
               "holds copper off them, and the screw heads are solids in that build. "
               "Parts the fab cannot place: none (M30 is the tier)",
        "M10": "USB: U10 (USBLC6-2SC6) is the first thing on the pair, 1.9 mm from the "
               "receptacle's pads, with VBUS on its rail pin; the PHY carries its own ESD "
               "cells behind it. This is an internal port (a 100 mm lead to the panel's hub, "
               "inside the instrument), so the CC pins have only their resistors. 24 V: an "
               "internal lead from the panel, fused there at 1 A (F1) and clamped there "
               "(D6); polarised housing; R44 in series. Nothing on this board is reached by "
               "a hand in use: the guard covers it and the photodiodes look up through its "
               "slots",
        "M13": "measured on the routed board, pad edge to pad edge, against TI's RNX layout "
               "example: C161 and C165, the two 100 nF, are each 0.60 mm from their VIN pin "
               "and 0.60 from the PGND pin beside it, on the part's layer, no via in either "
               "loop; the bulk C160 is 6.0 mm from pin 2 in the same row. The switch node is "
               "a laid 0.5 mm F.Cu track with no via, 6.5 mm from the top pad to L1 over the "
               "top of the cell, away from the feedback parts, which sit at the opposite "
               "(bottom) edge: R41 1.2 mm and R40 2.4 mm from FB, their node two pads long. "
               "Bootstrap C163 0.9 mm from BOOT and 0.7 from the SW pin TI provides for it; "
               "VCC's C166 2.4 mm. No copper pour on SW: it is not a heatsink here",
        "M14": "L1 (WPN4020H4R7MT, 4.7 uH): ripple (24 - 5) x (5 / 24) / (4.7 uH x 1.4 MHz) = 0.60 "
               "A, peak 1.08 + 0.30 = 1.38 A at the board's worst case against 4.00 A rated / 4.90 "
               "typical saturation (Sunlord, 30 % drop) and 2.85 A rms. TI's rule is the low-side "
               "limit, 3.5 A typical (2.9 to 4.1): covered at typical with 0.5 A in hand, 0.1 A "
               "short only with the IC at its maximum and the part at its floor, on a "
               "metal-composite core that gives way gradually. Closed magnetic circuit, which the "
               "twenty TIAs need; rated 40 V. Why not the 3.3 uH part that clears 4.1 A is at L1",
        "M15": "U13 is internally compensated for ceramic outputs; about 28 uF effective against "
               "the 2 x 22 uF nominal row, and 19 V of headroom. U8 (AP2114H) is specified stable "
               "with 4.7 uF of ceramic and has 10 uF + about 2 uF of 100 nF parts; 1.7 V in hand "
               "against 0.45 V of dropout at 1 A. U9 (TPS7A20) is stable with 1 to 200 uF of "
               "ceramic at up to 100 milliohm and has about 18 uF nominal; its input is 5.02 V less "
               "25 mV in the bead, 1.7 V over the output against well under 0.2 V of dropout at 166 "
               "mA. Both replaced ESR-compensated parts (an AMS1117 and an SPX3819) that this "
               "board's all-ceramic rails would have left unstable. The PHY's two internal "
               "regulators each have the 4.7 uF its sheet names (+-20 %, low ESR), as an 0805 so "
               "the value survives its bias",
        "M16": "J2 is damped. R44, 2 ohm, is in series ahead of every capacitor: against the 5 uF "
               "C160 keeps at 24 V, a metre of bench lead (1 uH) is a damping ratio of 2.2 and the "
               "150 mm harness more, so a live plug does not overshoot at all; without it the input "
               "rings toward 48 V on a part whose absolute maximum is 38. The resistor is a KOA "
               "2512 because the plug puts 288 W across it for microseconds and KOA's one-pulse "
               "curve allows 400 W below 10 us in that case (40 W in a 1206). USB: VBUS lands "
               "on 1 uF (C130) and a 10 k sense resistor: the capacitance the USB "
               "specification expects a device to present, behind a host's own limit",
        "M17": "FB1 (BLM18KG601SN1D, 1.3 A) carries 166 mA at the worst case, 13 % of its "
               "rating. Its resonance with the 1.3 uF on +5V was near 115 kHz, beside the "
               "emitter carrier's third harmonic (144 kHz), and undamped; R43 + C134 (1 ohm "
               "in series with 10 uF, the filter's characteristic impedance and several "
               "times its capacitance) flatten it. Arithmetic at FB1",
        "M18": "one supply: everything here hangs off the 24 V input, so no part of the board is up "
               "while another is down. The one foreign domain is the USB host. With the host up and "
               "this board down, VBUS reaches only the clamp array's rail pin, 100 nF and the PHY's "
               "VBUS pin through the 10 k its sheet's peripheral diagram names for exactly that (75 "
               "k to ground behind it); D+ / D- carry only the host's 15 k pull-downs. With this "
               "board up and the host down nothing is driven: VBUS is not sourced, and the PHY does "
               "not attach without it. A debug probe is used with the board powered (TP5 tells it "
               "so)",
        "M19": "Q1 (AO3400A): driven from a 3.3 V pin through 100 ohm; AOS specifies 52 "
               "milliohm maximum at VGS 2.5 V, so it is fully on with 0.8 V to spare and "
               "drops 11 mV at 0.21 A. Gate rating 12 V. R38, 100k to ground, holds the row "
               "off in reset and with the MCU unprogrammed",
        "M20": "I2C2: R50 / R51, 4.7 k to +3V3D, one pair for the bus. Lower bound (3.3 - "
               "0.4) / 3 mA = 0.97 k; upper for about 60 pF (six parts, two pads, 200 mm of "
               "track) is 300 ns / (0.8473 x 60 pF) = 5.9 k at 400 kHz, so 4.7 k serves "
               "standard and fast mode. SAI: BCLK is 12.288 MHz to five loads over the "
               "strip, FSYNC 192 kHz; no series resistor, decided: there is no room for one "
               "at pins 3 / 4, and firmware sets those two pins to MEDIUM drive speed "
               "(OSPEEDR 01: 5.2 ns edges into 50 pF, DS12110 table 63, where LOW tops out "
               "at 12 MHz), several times the line's 1 ns delay -- never high or very high. "
               "If the clock rings at bring-up, that setting is the first thing to check. No "
               "CAN on this board",
        "M21": "the converters' AVSS pin and pad and the MCU's VSSA are on the one In1 "
               "plane, unbroken under the whole analog strip; there is no analog / digital "
               "split (the ground note). Each converter's VREF and AREG capacitors are in "
               "its cell at their pins. The twenty summing nodes are 5.1 mm each and "
               "identical; the TIA outputs run in the comb lanes over solid ground to their "
               "coupling capacitors. The switcher is at the -Y tail, over 50 mm from the "
               "nearest photodiode, and the emitter current is on the buck's side of FB1",
        "M22": "twenty TIA sections in ten duals and one follower: no unused section. Inputs "
               "sit at MID, 0.33 V, inside a rail-to-rail input range; outputs swing up from "
               "MID toward 3.2 V into 250k and an AC-coupled converter input (2.5 to 20 k by "
               "register), a resistive load. TIA stability: Cf 2.2 pF against a 1.40 pF "
               "minimum (at Rf). The follower U11 does not drive MID's 10 uF directly: R42, "
               "100 ohm, isolates it and its feedback is taken at its own pin (TI gives the "
               "part 100 pF of capacitive load)",
        "M23": "clamp array first, 1.9 mm from the receptacle, the pair passing through its pads. "
               "Through path receptacle -> U10 -> PHY: F.Cu only, no via on either half, 10.7 and "
               "10.8 mm (0.17 mm apart, A3). The two vias on USB_DP are not on that path: they tie "
               "the receptacle's second D+ contact (B6) to the first with 2.5 mm of In2, as D- ties "
               "its own round on F.Cu -- the stub the unused cable orientation leaves, 5 mm, "
               "harmless at 480 Mbit/s. No series resistors and no external pull-up: the USB3300 "
               "has both internally (its 6.2.2). Clock: Y2 is an oscillator, +-20 ppm all-in "
               "against the +-500 ppm the PHY's note 5-1 allows, 1 ps rms of phase jitter, 7.6 mm "
               "from XI on F.Cu with no via. VBUS is sensed, never sourced. C130 on VBUS is 1 uF, "
               "the PHY's minimum for a device (its table 7-2)",
        "M24": "Y1 (TAXM25M4RDBCCT2T): CL 10 pF, ESR 30 ohm max, C0 3 pF max. C123 = C124 = 12 pF "
               "C0G; (12 + about 7 per leg) / 2 = 9.5 pF. gm_crit = 4 x 30 x (2 pi 25 MHz)^2 x (13 "
               "pF)^2 = 0.50 mA/V against the 1.5 the H7 guarantees to start: 3 times. Y2 is not a "
               "crystal: a 24 MHz oscillator (CJO05-240003320B30) drives the PHY's XI directly with "
               "XO left open, which the PHY's section 6.3 allows, because the PHY asks for a "
               "crystal rated 0.5 mW of drive or more and the stocked 3.2 x 2.5 crystals are rated "
               "0.1 mW. Its accuracy and jitter are in M23, its bypass in M4. Measured: Y1 is 1.9 "
               "mm from OSC_IN and 4.1 from OSC_OUT, each load capacitor 0.7 mm from its crystal "
               "pad. NOT ideal and recorded: OSC_OUT reaches the crystal's far pad through two vias "
               "and a 5 mm run on B.Cu under the part, with the ground plane one layer above it. It "
               "is 1 to 2 pF on the output leg: inside the gain margin, and a few ppm the "
               "firmware's audio clock does not care about. Y1's load capacitors are trimmed on the "
               "first board either way",
        "M25": "no part here depends on a pad for its life. Converters: about 0.1 W each, pad on "
               "GND (VSS) with one via to the plane 0.2 mm below (A8). PHY: about 0.2 W (62 mA "
               "typical transmitting, 73 max, all of it from 3.3 V), flag on GND, one via. U13 is a "
               "flip-chip-on-lead package with no pad, so its heat leaves through its pins into the "
               "row's copper, and it is the hottest part here. LMR33630B, 1.4 MHz, 5 V out from 24 "
               "V. Loss from TI's 24 V curve for the RNX package (ZHCSHQ3F figure 9-15): 0.77 W at "
               "the 0.46 A typical load (75 %), 0.88 W at the 1.08 A worst case (86 %); most of it "
               "is switching loss and does not go away at light load. Thermal resistance is an "
               "ESTIMATE, 60 C/W: TI's figure 9-4 gives 50 to 63 for this package on 2 oz / 1 oz "
               "copper, and this board is 1 oz / 0.5 oz. At 45 C in the endplate cavity beside the "
               "motors that is 91 C typical and 98 C worst, against 125: 27 C in hand. The 2.1 MHz "
               "variant read 1.03 / 1.31 W off figure 9-17, 107 / 124 C, and was replaced for it. "
               "U13's case temperature is on the bring-up list. U8's tab is VOUT (+3V3D), not "
               "ground, on its own land: 0.36 W typical. At ST's 85 C all-peripherals maximum it "
               "would be 0.79 W, which a SOT-223 on this little copper should not be asked to hold: "
               "firmware does not enable that set, and U8's temperature is on the bring-up list. "
               "U9: 0.28 W worst, 53 C of rise by TI's 187 C/W. Paste on the QFN pads is the "
               "footprints' windowed pattern",
        "M26": "SAI: BCLK and FSYNC leave the MCU (SAI1 block A, master) and enter the converters' "
               "BCLK / FSYNC pins, which are inputs in slave mode; each converter's SDOUT, its "
               "output, enters one SAI data pin configured as a receiver (SAI1 A / B, SAI2 A / B, "
               "SAI3 A). ULPI: DIR and NXT are PHY outputs into PI11 and PH4; STP is the MCU's "
               "output on PC0 into the PHY's STP input; CLKOUT, the PHY's 60 MHz output, enters PA5 "
               "(OTG_HS_ULPI_CK); D0-D7 are bidirectional. Pin functions from DS12110 table 9 and "
               "USB3300 table 3-1 (the pinouts above). Y2's output drives XI, an input when clocked "
               "externally. I2C is bidirectional",
        "M27": "BOOT0: R30 and TP8, nothing else. NRST: R31, C135 and TP3. SWDIO / SWCLK: their "
               "pads only; PA13 / PA14 are used for nothing else. PF0 / PF1, the bootloader's I2C2, "
               "also carry the five converters, at 0x4C against the bootloader's 0x4E: they cannot "
               "answer for it. The PHY's RESET is tied, not shared",
        "M28": "every active part's pinout above is from its maker's sheet for the ordering code in "
               "elec/fab.py: STM32H743IIT6 C89597 (LQFP176), USB3300-EZK-TR C108383, "
               "TLV320ADC3140IRTWT C1852021, TLV9062IDGKR C398356 (VSSOP), TLV9061IDBVR C398358 "
               "(the SOT-23 pinout, not the SC70's), LMR33630BRNXR C2071384 (the VQFN column), "
               "AP2114H-3.3TRG1 C150716 (the H order: tab and pin 2 are VOUT, and the tab's copper "
               "is +3V3D), TPS7A2033PDBVR C2862740 (pin 4 not connected), AO3400A C20917, "
               "USBLC6-2SC6 C7519, TAXM25M4RDBCCT2T C403946, CJO05-240003320B30 C712738, "
               "S4B-XH-SM4-TB, TYPE-C-31-M-12",
        "M31": "printed by kicad_silk on every route: the board's name and r1 on the front, "
               "every test pad's net beside it (TP1-TP11, TP9 reads V24_IN), J2's way names "
               "on the back under its tails. Pin-1 and polarity marks are the footprints' "
               "own, outside the bodies; the emitters' cathode marks included. DRC's silk "
               "warnings (five overlaps, five over copper) are reference designators in the "
               "0402 fields, which the fab clips; none is a label a person needs",
        "M32": "J2 is JST XH, 2.50 mm, on KiCad's JST_XH_S4B-XH-SM4-TB land; pad 1 checked "
               "against JST's drawing from the mating face (pinouts above); 3 A contacts and "
               "AWG 22-28 for 0.26 A. J1 is a 16-pin USB 2.0 Type-C receptacle numbered as "
               "the standard numbers it, on the footprint drawn for this exact part. Both "
               "carry ground. The plug envelopes and their leads are in the CAD (M11)",
        "M33": "added up at U13 in optical(), from each part's own sheet. +3V3A: 142 mA typical, "
               "166 worst, of U9's 300 (the converters' draw at 192 kHz is assumed at 26 mA each: "
               "MEASURE IT on the first board). +3V3D: 212 typical, 462 at ST's 85 C "
               "all-peripherals maximum, of U8's 1 A; 0.79 W in the SOT-223 at that corner. 5 V: "
               "0.46 A typical, 1.08 A worst, of U13's 3 A. 24 V: 79 mA typical, 0.26 A worst, "
               "through 3 A contacts, R44 (0.14 W of 1 W) and the panel's 1 A fuse. Those are the "
               "amps declared in power_paths",
        "M34": "one logic level throughout, 3.3 V: MCU, PHY, oscillator, converter IOVDD. SHDNZ is "
               "active low and pulled high (run); the PHY's RESET active high, tied low, and its "
               "REG_EN active high, tied high; Y2's enable active high, tied high; U13 EN and U9 EN "
               "active high, tied to their inputs; Q1 is on with LED_GATE high and held low by R38. "
               "Converter interrupt pins are not used. USB D+ to DP (pin 7), D- to DM (8) through "
               "the clamp array, same polarity at the receptacle. Each TIA's feedback returns to "
               "its inverting input (pins 2 and 6 of the dual); the follower's to pin 4. I2C is "
               "open-drain with its one pair of pull-ups",
        "M36": "no power leaves this board. VBUS is an input (sensed, never sourced) and the "
               "24 V input feeds only the buck",
        "M38": "ceramics larger than 0805: C160 only (1206), lying across the strip, at "
               "right angles to the direction this 188 mm board bends. R44, the one 2512, "
               "lies the same way for its solder joints. The outline is routed, no V-score "
               "and no break-off tab. The two M4 holes are unplated cut-outs with no copper "
               "at them (isolated on purpose: the screws go into printed plastic), and the "
               "CAD keeps every part clear of their heads. Both connectors are on the -Y "
               "edge with their plugs and leads modelled; every test pad is on the open face",
        "M39": "MCU: the unused pins have no pads' worth of copper and firmware sets them to analog "
               "or pulled inputs at start-up; no spare was brought out (the strip has no room, and "
               "I2C2 + SWD already reach the part). Converters: MICBIAS open (powered down); GPIO1 "
               "open -- it resets to an interrupt OUTPUT with a weak pull-up (GPIO_CFG0 reset 22h), "
               "so nothing floats. U13 PG open (open-drain output). U9 pin 4 has no internal "
               "connection. The PHY's CPEN (an output), ID and EXTVBUS (each with its own pull "
               "resistor) and XO (floated when XI is clocked, its sheet's instruction) are open. J2 "
               "ways 3 / 4 and the USB-C's SBU pins are not connected, on purpose",
        "M40": "the generator carries it at each part: Y1, Y2, L1, FB1, U8, U9 and R44 have the "
               "part number as their value with the parameter that chose them and 'do not "
               "substitute' where a look-alike fails (R44's pulse rating, U9's ceramic stability, "
               "the 60-ohm-not-600 bead trap, Y1's CL and ESR, Y2 being an oscillator and not a "
               "crystal). R37 is 1 % by specification. Cf and the crystal load capacitors are C0G. "
               "U8's tab is live at 3V3 and says so. Values are E24 / E96: 9k09, 12k, 24k9, 5k1, "
               "249k",
        "M41": "no switch or button on the board",
    },
    # A13 (cadkit/PCB_QUALITY.md): what the DESIGN leaves open, and how many nets each
    # repeated structure is on. The pass fails on any difference from the routed board.
    "unconnected": {
        "J1.[AB]8": "USB-C sideband (SBU): USB 2.0 does not use it",
        "J2.[34]": "the feed is two wires: ways 3 and 4 have no conductor",
        "J2.MP": "JST reinforcement tab: soldered, on no net",
        "U13.8": "LMR33630 PG: open drain, not read",
        "U1[4-8].5": "TLV320ADC3140 MICBIAS: no microphone, the bias stays powered down",
        "U1[4-8].20": "TLV320ADC3140 GPIO1: not used",
        "U6": {
            "pins": "1 7 8 9 10 11 12 18 19 20 21 24 25 26 27 28 33 34 35 41 42 43 44 46 50 52 53 54 55 58 59 60 63 64 65 66 67 68 69 70 73 74 75 76 77 78 83 84 85 86 87 88 89 94 95 96 97 98 99 100 101 104 105 106 107 108 109 110 111 112 115 116 117 118 119 120 121 122 123 128 129 130 131 132 133 134 138 139 140 141 142 144 145 146 147 150 151 152 153 154 155 156 157 160 162 164 165 167 168 169 170 173 174 176",
            "why": "GPIO this board gives no function: left open, firmware leaves it an input with pull-down"
        },
        "U7": {
            "pins": "3 5 10 27",
            "why": "USB3300 CPEN, ID and EXTVBUS (a device needs none: table 3-1) and XO (a clock is driven into XI)"
        },
        "U9.4": "the maker's NC pin"
    },
    "net_groups": [
        {
            "name": "twenty photodiodes: twenty cathodes, twenty summing nodes",
            "pins": [
                "PD*.2"
            ],
            "nets": 20,
            "each": 1,
            "pins_count": 20
        },
        {
            "name": "every photodiode anode is on MID",
            "pins": [
                "PD*.1"
            ],
            "nets": 1,
            "pins_count": 20
        },
        {
            "name": "ten dual op-amps: twenty outputs, twenty nets",
            "pins": [
                "U2[1-9].[17]",
                "U30.[17]"
            ],
            "nets": 20,
            "each": 1,
            "pins_count": 20
        },
        {
            "name": "ten dual op-amps: twenty inverting inputs, twenty summing nodes",
            "pins": [
                "U2[1-9].[26]",
                "U30.[26]"
            ],
            "nets": 20,
            "each": 1,
            "pins_count": 20
        },
        {
            "name": "five 4-channel converters: twenty + inputs, twenty nets, none idle",
            "pins": [
                "U1[4-8].6",
                "U1[4-8].8",
                "U1[4-8].10",
                "U1[4-8].12"
            ],
            "nets": 20,
            "each": 1,
            "pins_count": 20
        },
        {
            "name": "five 4-channel converters: twenty - inputs, each with its own capacitor",
            "pins": [
                "U1[4-8].7",
                "U1[4-8].9",
                "U1[4-8].11",
                "U1[4-8].13"
            ],
            "nets": 20,
            "each": 1,
            "pins_count": 20
        },
        {
            "name": "each TIA output reaches one converter input through its coupling capacitor",
            "nets_like": "TIA_OUT_\\d+[AB]",
            "count": 20,
            "pads": 4
        },
        {
            "name": "five converters: a data line each",
            "pins": [
                "U1[4-8].21"
            ],
            "nets": 5,
            "each": 1
        },
        {
            "name": "five converters: a shutdown line each",
            "pins": [
                "U1[4-8].14"
            ],
            "nets": 5,
            "each": 1
        },
        {
            "name": "five converters: one bit clock and one frame clock",
            "pins": [
                "U1[4-8].22",
                "U1[4-8].23"
            ],
            "nets": 2,
            "each": 5
        },
        {
            "name": "ten emitters: ten anodes, a ballast each",
            "pins": [
                "D*.2"
            ],
            "nets": 10,
            "each": 1,
            "pins_count": 10
        },
        {
            "name": "ten emitters: one switched cathode row",
            "pins": [
                "D*.1"
            ],
            "nets": 1,
            "pins_count": 10
        },
        {
            "name": "ULPI: eight data lines, PHY to MCU",
            "nets_like": "ULPI_D[0-7]",
            "count": 8,
            "pads": 2
        }
    ],
    "pinouts": {
        "TYPE-C-31-M-12": "KiCad's USB_C_Receptacle_HRO_TYPE-C-31-M-12 names each land by "
                          "its USB Type-C contact (A1 ... B12), the names Korean Hroparts' "
                          "drawing prints beside the same lands; every net is attached by "
                          "that name (A4/A9/B4/B9 VBUS, A5/B5 CC, A6/B6 D+, A7/B7 D-, "
                          "A1/A12/B1/B12 GND). Checked 2026-10-04",
        "S4B-XH-SM4-TB": "JST eXH.pdf p.6, Header / SMT type: seen from above with the "
                         "mouth pointing away and the tails toward the viewer, No. 1 "
                         "circuit is the right-hand post. KiCad JST_XH_S4B-XH-SM4-TB has "
                         "its tails at -Y, mouth +Y and pad 1 at -X: the same end. Board: "
                         "1 GND, 2 +24V, 3 and 4 not crimped. Read 2026-10-04",
        "AO3400A": "AOS AO3400A datasheet rev 3 p.1, package drawing: 1 G, 2 S, 3 D. Read "
                   "2026-09-30",
        "USBLC6-2SC6": "ST USBLC6-2 datasheet, SOT23-6L pin configuration: 1 I/O1, 2 GND, "
                       "3 I/O2, 4 I/O2, 5 VBUS, 6 I/O1. Board: D+ on 1 and 6, D- on 3 and "
                       "4, so each line passes through the part. Datasheet audit of "
                       "2026-09-17 (elec/fab.py)",
        "TLV9061IDBVR": "TI SBOS839, DBV (SOT-23-5): 1 OUT, 2 V-, 3 IN+, 4 IN-, 5 V+. "
                        "Board: a follower, 4 tied to 1, MID_RAW on 3. Audit of 2026-09-17",
        "TLV9062IDGKR": "TI SBOS839, DGK (VSSOP-8): 1 OUT1, 2 IN1-, 3 IN1+, 4 V-, 5 IN2+, "
                        "6 IN2-, 7 OUT2, 8 V+. Board: MID on both IN+, a photodiode on "
                        "each IN-. Audit of 2026-09-17",
        "LMR33630BRNXR": "TI LMR33630 datasheet (ZHCSHQ3F) section 6, figure 6-2 and "
                         "table 6-1, RNX: 1 PGND, 2 VIN, 3 NC (tied to SW on the board, as "
                         "the table asks), 4 BOOT, 5 VCC, 6 AGND, 7 FB, 8 PG, 9 EN, "
                         "10 VIN, 11 PGND, 12 SW. Board: EN on +24V, PG open. Read "
                         "2026-10-04",
        "TLV320ADC3140IRTWT": "TI SBAS993, RTW: 1 AVDD, 2 AREG, 3 VREF, 4 AVSS, "
                              "5 MICBIAS, 6-13 IN1P/M ... IN4P/M, 14 SHDNZ, 15 ADDR1, "
                              "16 ADDR0, 17 SCL, 18 SDA, 19 IOVDD, 20 GPIO1, 21 SDOUT, "
                              "22 BCLK, 23 FSYNC, 24 DREG, pad VSS (the pin list at "
                              "the converters' Part in this file). Audit of 2026-09-17",
        "STM32H743IIT6": "ST DS12110 figure 9 (LQFP176 pinout) and table 9, read pin by "
                         "pin 2026-10-04 for every pin this board uses: 2-5 PE3-PE6 "
                         "(SAI1 SD_B / FS_A / SCK_A / SD_A), 6 VBAT, 13 PI11 (ULPI_DIR), "
                         "16 / 17 PF0 / PF1 (I2C2), 29 / 30 PH0 / PH1 (HSE), 31 NRST, "
                         "32 PC0 (ULPI_STP), 37 VSSA, 38 VREF+, 39 VDDA, 40 PA0 "
                         "(SAI2_SD_B), 45 PH4 (ULPI_NXT), 47 PA3 (D0), 51 PA5 (CK), "
                         "56 / 57 PB0 / PB1 (D1 / D2), 79 / 80 PB10 / PB11 (D3 / D4), "
                         "81 and 125 VCAP, 92 / 93 PB12 / PB13 (D5 / D6), 114 VDD33USB, "
                         "124 PA13, 137 PA14, 166 BOOT0, 171 PDR_ON (to VDD), and VDD at "
                         "15, 23, 36, 49, 62, 72, 82, 91, 103, 127, 136, 149, 159, 172 "
                         "each beside its VSS",
        "USB3300-EZK-TR": "Microchip DS00001783C figure 3-1 and table 3-1: 1 GND, 2 GND, 3 CPEN, 4 "
                          "VBUS, 5 ID, 6 VDD3.3, 7 DP, 8 DM, 9 RESET (active high), 10 EXTVBUS, 11 "
                          "NXT, 12 DIR, 13 STP, 14 CLKOUT, 15 VDD1.8, 16 VDD3.3, 17-24 DATA7-DATA0, "
                          "25 VDD3.3, 26 VDD1.8, 27 XO, 28 XI, 29 VDDA1.8, 30 VDD3.3, 31 REG_EN, 32 "
                          "RBIAS, flag GND. Read 2026-10-05",
        "AP2114H-3.3TRG1": "Diodes AP2114 datasheet, 'Pin Descriptions', column SOT-223 "
                           "(H): 1 GND, 2 VOUT, 3 VIN, tab VOUT = KiCad "
                           "SOT-223-3_TabPin2 (the HA suffix is a different order: "
                           "not this part). Read 2026-10-04",
        "TPS7A2033PDBVR": "TI TPS7A20 datasheet (SBVS338 / ZHCSKY8G) fig. 5-4, DBV 5-pin "
                          "SOT-23 top view, and its pin table: 1 IN, 2 GND, 3 EN, 4 N/C (no "
                          "internal connection), 5 OUT. Board: 1 and 3 on +5V (EN tied to "
                          "IN), 2 GND, 4 open, 5 +3V3A. Read 2026-10-04",
        "TAXM25M4RDBCCT2T": "Yajingxin TAXM25M4RDBCCT2T sheet (LCSC C403946) p.7, outline: "
                            "lands 1 and 3 are the crystal, 2 and 4 the can. Board: "
                            "1 OSC_IN, 3 OSC_OUT, 2 / 4 GND. Read 2026-10-04",
        "CJO05-240003320B30": "JSCJ CJO05 sheet rev 1.0 (LCSC C712738) p.5, 'Pin connection' and "
                              "its test circuit: 1 enable (high or open runs), 2 GND, 3 output, 4 "
                              "VDD; lands numbered counter-clockwise from the marked corner, as the "
                              "footprint's are. Board: 1 and 4 +3V3D, 2 GND, 3 PHY_XI. Read "
                              "2026-10-05",
    },
}


def _assert_matches_cad(net_path):
    """The netlist and the CAD must describe the SAME board, part for part.

    ⚠ THIS IS THE WHOLE POINT OF IMPORTING THE PLACEMENTS. Two files listing 153
    parts will drift the moment someone edits one of them, and the failure is silent:
    a ref in the CAD with no net is a part nobody notices is unconnected, and a ref in
    the netlist with no placement lands at the origin on top of whatever is there. It
    caught four real things on the first run -- PD<side><string> vs PD<string><side>,
    Rf1..Rf20 vs Rf<quad><section>, R30/R31 swapped, and the PHY bias resistor and the
    H7's VCAP caps missing from the CAD entirely -- so it stays.

    FOOTPRINT vs PACKAGE is checked too, but only where the CAD's package name maps to
    exactly one footprint: the CAD's 0402 class covers both resistors and capacitors,
    so that one is checked by ref prefix instead of by name."""
    import re
    t = open(net_path, encoding="utf-8").read()
    got = dict(re.findall(r'\(comp\s*\(ref "([^"]+)"\).*?\(footprint "([^"]+)"\)', t, re.S))
    want = {q["ref"]: q["pkg"] for q in OP.PARTS}
    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    assert not missing, ("in src/optical_pickup.py but not in this netlist: %s -- either "
                         "wire it up or delete it from the CAD" % missing)
    assert not extra, ("in this netlist but not in src/optical_pickup.py: %s -- it has "
                       "no placement, so it would land on the origin" % extra)
    # 0402 and 0805OPT are CLASSES, not parts -- the CAD's name does not say whether
    # an 0402 is a resistor or a capacitor, nor whether an 0805 optical part is an
    # emitter or a detector, so those two are settled by ref prefix where the parts
    # are created (see the note above the pin map) and skipped here.
    # FB1 is the one genuine exception: a ferrite bead sharing the 1608 land with an
    # 0603 resistor. Exempted BY NAME rather than by loosening the rule, because the
    # rule was right to flag it -- it is the CAD's package class that is imprecise.
    class_pkgs = ("0402", "0603OPT")
    by_name = {"FB1"}
    bad = [(r, want[r], got[r]) for r in sorted(want)
           if want[r] not in class_pkgs and r not in by_name and got[r] != FP[want[r]]]
    assert not bad, "footprint disagrees with the CAD package: %s" % bad[:5]
    return len(want)


if __name__ == "__main__":
    optical(tag="optical")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "optical.net"))
    _assert_matches_cad(os.path.join(OUT_DIR, "optical.net"))
    netcheck.grounds_meet(os.path.join(OUT_DIR, "optical.net"))
    netcheck.no_orphan_pins(os.path.join(OUT_DIR, "optical.net"))
    # ⚠ THE CAD PLACES C112/C113 AT THE VCAP PINS AND KEEPS ITS OWN COPY OF THE PIN
    # NUMBERS. Check the copy: if this map moves and that one does not, the H7's core
    # regulator capacitors end up beside the wrong pins and nothing downstream -- not the
    # placement asserts, not DRC, not the router -- would see it.
    from src import optical_pickup as _cad
    assert (PIN["VCAP1"], PIN["VCAP2"]) == (_cad.VCAP1_PIN, _cad.VCAP2_PIN), (
        "VCAP pin numbers disagree: netlist says %s, the CAD places against %s"
        % ((PIN["VCAP1"], PIN["VCAP2"]), (_cad.VCAP1_PIN, _cad.VCAP2_PIN)))
    # ⚠ AND THE CAD'S SOURCING TABLE AGAINST THE NETLIST, every time, because the two
    # files name every part twice and drift apart silently. See elec/mpn_check.py for
    # what the first run found.
    import mpn_check
    if mpn_check.main():
        raise SystemExit("the CAD sourcing table and the netlist disagree -- see above")
    import volts_decl                   # A16: generated, see volts_decl.py
    volts_decl.into(BOARD_NOTES, "optical")
    with open(os.path.join(OUT_DIR, "optical.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.2f x %.2f mm, %d placements, x%d per instrument"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]),
             BOARD_NOTES["qty_per_instrument"]))
