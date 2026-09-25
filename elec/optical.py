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
against the USB334x datasheet's own numbers and the USB pair's coupled length,
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
    "SOT-223":  "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    "SOT-23":   "Package_TO_SOT_SMD:SOT-23",
    "SOT-23-5": "Package_TO_SOT_SMD:SOT-23-5",
    "SOT-23-6": "Package_TO_SOT_SMD:SOT-23-6",
    "SOT-563":  "Package_TO_SOT_SMD:SOT-23-6",        # ⚠ see the note above
    "3225":     "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    # Sunlord's own recommended land (1.1 x 3.7 pads on a 3.0 mm pitch), not the
    # Bourns SRN4018 one that used to be here -- LCSC stocks no usable SRN4018 value.
    "IND-4040": "Inductor_SMD:L_Sunlord_SWPA4030S",  # 4030 since the LMR33630 swap (same land)
    "TP": "TestPoint:TestPoint_Pad_D1.5mm",
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
        # 3 A LMR33630C since 2026-09-22, and the budget says so two lines above the number
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
        r = _r("R%d" % i, "180R", "LED ballast, string %d -- 21 mA, tune per string" % i)
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
            # Everlight PD15-22B/TR8: pad 1 ANODE, pad 2 CATHODE (DTD-152-002 p.2), two
            # pads each -- elec/layout.py nets every pad that shares a number.
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
        rf = _r("Rf%s" % n, "250k", "TIA feedback, string %d%s -- tune per string" % (i, side))
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
        v3d += u[14]              # SHDNZ tied high locally -- see THE CONVERTERS
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

    # ── U7: the ULPI PHY ─────────────────────────────────────────────────────
    # ⚠ THE ONE PART ON THIS BOARD THAT IS A SOURCING BLOCK RATHER THAN A CHOICE.
    # The USB3343-CP was recorded OUT OF STOCK at LCSC on 2026-08-04 and has not been
    # re-checked. There is no second source in the JLCPCB library that is pin-
    # compatible, so if it stays out the options are a different PHY (and a different
    # footprint) or a different MCU. It is the first thing to confirm before ordering.
    u7 = Part(name="USB3343", ref_prefix="U", ref="U7", dest="NETLIST", tool="skidl",
              value="USB3343-CP",
              description="USB 2.0 HIGH-SPEED ULPI PHY, QFN-24 (LCSC C633347) "
              "-- 98 in stock at JLCPCB 2026-09-17 (was 0 on 2026-08-04)",
              footprint="Package_DFN_QFN:HVQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm",
              pins=[Pin(num=n, func=P) for n in range(1, 26)])
    # ⚠ THE PINOUT BELOW IS READ OUT OF THE DATASHEET, AND THE ONE IT REPLACES WAS NOT.
    # SMSC/Microchip USB334x datasheet rev 1.2, Table 2.2 "USB3343 Pin Descriptions":
    #    1 DIR      2 CLKOUT   3 NXT      4 DATA0    5 DATA1    6 DATA2
    #    7 DATA3    8 DATA4    9 VDDIO   10 DATA5   11 DATA6   12 DATA7
    #   13 DP      14 DM      15 VDD33   16 VBAT    17 VBUS    18 ID
    #   19 RBIAS   20 XO      21 REFCLK/XI          22 RESETB  23 VDD18   24 STP
    #   FLAG (exposed pad) GND
    # The previous map had most of these wrong -- DP and DM on 16/15, the crystal on
    # 10/11, RBIAS on 17, DIR on 22 -- and this file said so itself: "must be checked
    # against Microchip's datasheet at schematic review". It never was, and every
    # placement decision around the PHY (which face the pair leaves by, where R37 goes,
    # where the crystal sits) was then fitted to pins that do not exist. DRC was clean
    # throughout: DRC checks copper against the netlist, and the netlist was wrong.
    #
    # WHAT THE DATASHEET ALSO REQUIRES, which the old map had no place for:
    #   * VDD33 (15) and VDD18 (23) are REGULATOR OUTPUTS, each needing 1.0 uF (<1 ohm
    #     ESR) as close as possible. Neither may be fed from a rail.
    #   * ID (18) goes to VDD33 for a device.
    #   * VBUS (17) needs a series resistor to the connector, sized by mode (Table 5.6):
    #     20 k +-5% for DEVICE ONLY. Its over-voltage clamp sinks through that resistor.
    #   * RESETB (22) high = run; tied to the same 3V3 that powers VBAT.
    #   * VDDIO (9) sets the ULPI logic level, so it is the MCU's 3V3.
    usb_dp, usb_dm = Net("USB_DP"), Net("USB_DM")
    v1v8, rbias = Net("PHY_1V8"), Net("PHY_RBIAS")
    phy_vdd33, phy_vbus = Net("PHY_VDD33"), Net("PHY_VBUS")
    for pin, sig in ((1, "ULPI_DIR"), (2, "ULPI_CK"), (3, "ULPI_NXT"),
                     (4, "ULPI_D0"), (5, "ULPI_D1"), (6, "ULPI_D2"), (7, "ULPI_D3"),
                     (8, "ULPI_D4"), (10, "ULPI_D5"), (11, "ULPI_D6"), (12, "ULPI_D7"),
                     (24, "ULPI_STP")):
        ulpi[sig] += u7[pin]
    usb_dp += u7[13]
    usb_dm += u7[14]
    phy_vdd33 += u7[15], u7[18]           # regulator output, and ID tied to it
    v3d += u7[16], u7[9], u7[22]          # VBAT, VDDIO, RESETB
    phy_vbus += u7[17]
    rbias += u7[19]
    phy_xi, phy_xo = Net("PHY_XI"), Net("PHY_XO")
    phy_xo += u7[20]
    phy_xi += u7[21]
    v1v8 += u7[23]
    gnd += u7[25]

    # ── U8/U9: the two 3V3 rails, and they are two on purpose ────────────────
    # U8 feeds the MCU and the PHY -- ~300 mA, which at 5 V in is 0.51 W and past
    # what a SOT-23-5 can shed, hence the SOT-223 tab. U9 feeds the ANALOG side and
    # is chosen for noise (40 uVrms) rather than current (~40 mA). Sharing one rail
    # would put the MCU's switching transients on the reference the TIAs measure
    # against, which is the one place on this board that cannot absorb them.
    u8 = Part(name="AMS1117-3.3", ref_prefix="U", ref="U8", dest="NETLIST",
              tool="skidl", value="AMS1117-3.3",
              description="3V3 DIGITAL LDO, SOT-223 tab (LCSC C6186)",
              footprint="Package_TO_SOT_SMD:SOT-223-3_TabPin2",
              # SOT-223-3_TabPin2: the TAB *is* pin 2, so there is no pad 4. That is
              # also the right electrical answer for an AMS1117 -- its tab is VOUT, not
              # ground -- which is worth knowing before anyone pours a heatsink area
              # under it and assumes it is at 0 V. The 0.51 W this part burns is shed
              # into whatever copper that tab sits on, and that copper is at 3V3.
              pins=[Pin(num=1, name="GND", func=P), Pin(num=2, name="VO/TAB", func=P),
                    Pin(num=3, name="VI", func=P)])
    gnd += u8[1]
    v3d += u8[2]
    v5_pre += u8[3]           # BUCK side: this LDO feeds the MCU and PHY
    u9 = Part(name="SPX3819", ref_prefix="U", ref="U9", dest="NETLIST", tool="skidl",
              value="SPX3819M5-L-3-3/TR",
              description="3V3 ANALOG LDO, 40 uVrms (LCSC C9055)",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=n, func=P) for n in range(1, 6)])
    # SPX3819 SOT-23-5: 1 IN, 2 GND, 3 EN, 4 BYP, 5 OUT
    v5 += u9[1], u9[3]
    gnd += u9[2]
    # ⚠ PIN 4 IS THE NOISE BYPASS AND IT WAS LEFT FLOATING -- which threw away the only
    # reason this part is here. The SPX3819 datasheet gives 300 uVrms without a bypass
    # capacitor and 40 uVrms with 1 uF on this pin (10 Hz - 100 kHz). The BOM line for
    # U9 says "chosen for noise (40 uVrms)"; as wired it was a 300 uVrms part feeding
    # the reference and supply of twenty transimpedance amplifiers.
    ldo_byp = Net("LDO_BYP")
    ldo_byp += u9[4]
    c127 = _c("C127", "1uF", "SPX3819 reference bypass -- 40 uVrms instead of 300")
    ldo_byp += c127[1]
    gnd += c127[2]
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
    mid += u11[1], u11[4]       # unity-gain follower
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
    #   +3V3A  (U9, SPX3819, off the QUIET side of FB1)
    #     5x TLV9064 quad          538 uA/amp typ, 750 max  ->  10.8 / 15.0 mA
    #     U11 TLV9061 single                                ->   0.54 / 0.75
    #     R34/R35 mid-rail divider 3.3 V / 10.09 k          ->   0.33 / 0.33
    #     5x TLV320ADC3140 AVDD (2026-09-21)   21.3 mA each, 4 ch at 48 kHz, PLL on
    #       (SBAS993B 7.5; 19.7 at 16 kHz, so it scales weakly) -- NO figure at 192 kHz;
    #       ~26 each assumed                                 ->  ~130 / ~150
    #                                                   subtotal ~142 / ~166 mA
    #     ⚠ THE CONVERTERS MULTIPLY THIS RAIL TENFOLD. U9 (SPX3819, 500 mA) carries it,
    #       but it burns (5 - 3.3) x 0.14 = 0.24 W in a SOT-23-5 -- ~45 C of rise -- and
    #       the buck's worst case below grows by the same ~150 mA. MEASURE AVDD current
    #       at 192 kHz on first boards before trusting either margin.
    #
    #   +3V3D  (U8, AMS1117, off the BUCK side)
    #     STM32H743 400 MHz VOS1, all peripherals enabled (DS12110 T30)
    #                              165 typ / 220 max @25 C / 400 max @85 C
    #     USB3343 sync mode, HS active (DS00002646 T4-2), VBAT + VDDIO
    #                               41 typ /  51 max
    #     R31 / R37 RBIAS / R38                             ->   0.8
    #                                            subtotal  207 / 272 / 452 mA
    #
    #   +5V / V5_PRE  (U13, LMR33630C since 2026-09-22 -- 3 A; this budget was the TPS560430's 600 mA)
    #     ten emitters at 21.1 mA, pulsed -- 105 mA average, 211 mA while on
    #       ⚠ THE 50% DUTY IS AN INFERENCE ABOUT FIRMWARE THAT DOES NOT EXIST YET, not
    #       a measurement: the emitters square-wave at 48 kHz, a quarter of the
    #       converters' 192 kHz, for the lock-in -- a square wave is 50% by nature.
    #       Firmware could choose a shorter pulse. IT DOES NOT CHANGE THE CONCLUSION --
    #       at 100% duty the emitters are 211 mA continuous and the typical total
    #       becomes 430 mA, still 72% of the buck -- so the budget holds whatever the
    #       firmware picks. Only the "324 mA typical" headline moves.
    #     U8 input ~= its output                             207 / 272 / 452
    #     U9 input ~= its output                              12 /  16 /  16
    #   + THE CONVERTERS' ~130 mA (2026-09-21, via U9 above): typical ~454 mA, worst ~629 mA
    #     -- 105 % of the 600 mA TPS560430 this budget was written against. RESOLVED
    #     2026-09-22 (user): U13 is now the 3 A LMR33630C, so the same worst case is 21 %.
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
    # ⚠ NOW THE LMR33630CRNXR (user, 2026-09-22) -- the TPS560430's 600 mA was 105 % used in
    # the worst case once the five converters landed on this board. 3 A, 36 V abs max, the
    # motor controller's family. THE VARIANT IS THE POINT:
    #   * "C" = 2.1 MHz. No forced-PWM LMR33630 is stocked, and a pulse-skipping buck at
    #     light load puts its switching energy at variable, low -- sometimes audio --
    #     frequencies beside twenty TIAs; that is why the TPS560430 was the FPWM part. At
    #     2.1 MHz with 4.7 uH the ripple is 0.40 A pk-pk, so the part stays in continuous
    #     conduction (fixed frequency) above ~0.2 A, and this board never draws less than
    #     the MCU's ~0.3 A. (TI's 5 V / 2.1 MHz example uses 1.5 uH -- sized for 3 A; at
    #     this board's load its 1.25 A ripple would drop the part into PFM.)
    #   * "RNX" = VQFN-HR 2 x 3 mm, NOT the motor controller's HSOIC-8: the buck row sits
    #     against the tail's 0.11 mm length margin and the SOIC grows it 0.86 mm.
    # Pinout, SNVSB08 Table 6-1 (VQFN column): 1 PGND, 2 VIN, 3 NC, 4 BOOT, 5 VCC, 6 AGND,
    # 7 FB, 8 PG, 9 EN, 10 VIN, 11 PGND, 12 SW. TI: "connect the SW pin to NC on the PCB"
    # (it simplifies the CBOOT loop), so pin 3 joins SW. PG is unused and left open.
    # Footprint: elec/footprints/Steel.pretty, drawn from TI's RNX0012B/C land (identical).
    # 793 in stock 2026-09-22 (C2071783).
    u13 = Part(name="LMR33630CRNX", ref_prefix="U", ref="U13", dest="NETLIST",
               tool="skidl", value="LMR33630CRNXR",
               description="24V -> 5V synchronous buck, 2.1 MHz, 3 A (LCSC C2071783)",
               footprint="Steel:Texas_RNX0012_VQFN-HR-12_2x3mm_P0.5mm",
               pins=[Pin(num=n, func=P) for n in range(1, 13)])
    v24 = Net("+24V")
    v24.drive = Pin.drives.POWER
    boot, vcc_buck = Net("BOOT"), Net("BUCK_VCC")
    pgnd += u13[1], u13[11], u13[6]
    v24 += u13[2], u13[10]
    sw += u13[3], u13[12]
    boot += u13[4]
    vcc_buck += u13[5]
    fb += u13[7]
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
    # (The TPS560430-era sizing above is history.) With the LMR33630C at 2.1 MHz the pick
    # is 4.7 uH -- see U13 -- in the same Sunlord 4x4 family, the 3.0-tall 4030 for its
    # 3.2 A saturation: the IC's own current limit is ~4 A, so a hard short saturates it
    # briefly either way; in service the peak is ~0.9 A.
    l1 = Part(name="L", ref_prefix="L", ref="L1", dest="NETLIST", tool="skidl",
              value="SWPA4030S4R7MT",
              description="buck output inductor, 4.7 uH shielded, Isat 3.2 A, "
              "DCR 78 mohm, 4.0 x 4.0 x 3.0 (LCSC C57269)",
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
               tool="skidl", value="GZ1608D601TF",
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
              value="TX322525M4LBDD2T",
              description="MCU HSE 25 MHz, CL 20 pF, ESR <= 30 ohm (LCSC C5308007)",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=n, func=P) for n in range(1, 5)])
    osc_in += y1[1]
    osc_out += y1[3]
    gnd += y1[2], y1[4]
    # ⚠ Y2 IS 26 MHz. Its frequency follows the PHY, and the CAD (24) and the MPN
    # table (25) disagreed with each other and with the part. The USB334x datasheet's
    # ordering table settles it: USB3343-CP-TR, REFCLK 26 MHz, "oscillator or crystal".
    # Neither 24 nor 25 would have produced a working USB link.
    # ⚠ CL 20 pF AND ESR <= 30 OHM ARE THE PHY'S REQUIREMENTS, not preferences:
    # USB334x Table 4.13 gives CL 20 pF typ and R1 30 ohm MAX. The obvious 26 MHz 3225
    # part (C15192) is CL 10 pF / ESR 50 ohm and fails both -- a mismatched load pulls
    # the frequency off the +-500 ppm budget, and 50 ohm against a 30 ohm limit is an
    # oscillator that may not start. K3A260002010 meets both.
    y2 = Part(name="Crystal", ref_prefix="Y", ref="Y2", dest="NETLIST", tool="skidl",
              value="K3A260002010",
              description="PHY reference 26 MHz, CL 20 pF, ESR <= 30 ohm (LCSC C2835957)",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=n, func=P) for n in range(1, 5)])
    phy_xi += y2[1]
    phy_xo += y2[3]
    gnd += y2[2], y2[4]

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
    v24 += j2[2]
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
    # only goes ONE WAY. The photodiode's anode is on the virtual earth and its cathode
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
    # new BOM line: 1 uF 0402 is already on this board (C127, and the converters' AVDD and
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
    r37 = _r("R37", "8k06 1%", "PHY RBIAS -- a PRECISION part: it sets the USB "
             "transmitter's drive current, so 1% is the spec, not a preference")
    rbias += r37[1]
    gnd += r37[2]
    # R39: the VBUS series resistor the USB3343 requires. 20 k is the DEVICE-ONLY value
    # (datasheet Table 5.6); the PHY's over-voltage clamp sinks current through it.
    r39 = _r("R39", "20k", "PHY VBUS series -- device-only value, USB334x Table 5.6")
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
    for k in range(12):
        c = _c("C1%02d" % k, "100nF", "MCU decoupling")
        rail = v3a if k >= 10 else v3d
        rail += c[1]
        gnd += c[2]
    # C112/C113: the H7 core regulator's VCAP pair. ADDED with R37/R38 -- see above.
    for tag, net in (("C112", vcap1), ("C113", vcap2)):
        c = _c(tag, "2.2uF", "H7 core regulator cap -- REQUIRED, not optional",
               "Capacitor_SMD:C_0805_2012Metric")
        net += c[1]
        gnd += c[2]
    # C120-C122: the PHY. C120 and C122 are its two REGULATORS' output caps, and the
    # datasheet specifies them -- 1.0 uF, <1 ohm ESR -- because a regulator's stability
    # depends on its output capacitance. They were 100 nF bypass caps, the wrong part for
    # that job. C121 bypasses the 3V3 the PHY is fed from (VBAT and VDDIO).
    for tag, net, val, why in (("C120", phy_vdd33, "1uF", "PHY VDD33 regulator output"),
                               ("C121", v3d, "100nF", "PHY VBAT/VDDIO bypass"),
                               ("C122", v1v8, "1uF", "PHY VDD18 regulator output")):
        c = _c(tag, val, why)
        net += c[1]
        gnd += c[2]
    # C123-C126: two load caps per crystal, and the VALUE FOLLOWS THE CRYSTAL'S CL.
    # C = 2 x (CL - Cstray). Both crystals are specified CL = 20 pF (see the MPN table
    # in src/optical_pickup.py, which now also fixes ESR -- the USB334x wants <= 30 ohm
    # and the part first picked was 50). Cstray is the pin capacitance plus the board's:
    #   PHY   XI/XO pins 3 pF typ each (USB334x Table 4.13) + ~2 pF of track -> 5 pF
    #   MCU   OSC_IN/OSC_OUT ~5 pF + ~2 pF                                    -> 7 pF
    # giving 30 pF for the PHY and 26 pF for the MCU; 27 pF is the E-series neighbour.
    # ⚠ THESE ARE THE STARTING VALUES, NOT THE FINAL ONES. Stray capacitance is a
    # property of the finished board, so the frequency is measured on the first article
    # and the caps trimmed -- that is normal for a crystal and it is not an admission
    # that the arithmetic is wrong.
    for tag, net, val in (("C123", osc_in, "27pF"), ("C124", osc_out, "27pF"),
                          ("C125", phy_xi, "30pF"), ("C126", phy_xo, "30pF")):
        c = _c(tag, val, "crystal load -- C0G")
        net += c[1]
        gnd += c[2]
    # C130-C133: the bulk caps and the reference bypass.
    # ⚠ C130 IS 100 nF, NOT 10 uF, BECAUSE VBUS IS A SENSE LINE HERE AND NOT A SUPPLY.
    # This board is self-powered from the 24 V trunk; the only thing downstream of VBUS
    # is the PHY's comparator, reached through R39's 20 k. Ten microfarads against 20 k
    # is a 0.2 SECOND time constant on the signal that tells the device whether a host
    # is present -- and 10 uF of bulk on a self-powered device is also inrush the host
    # pays for at plug-in, for a rail this board never draws from. 100 nF filters the
    # comparator input (2 ms) without either.
    for tag, net, desc in (("C130", vbus, "VBUS sense filter -- see note"),
                           ("C131", v3d, "3V3 digital bulk"),
                           ("C132", v3a, "3V3 analog bulk"),
                           ("C133", mid, "MID reference bypass -- the twenty summing "
                            "nodes share this, so it is what keeps them from talking "
                            "to each other through their own reference")):
        c = _c(tag, "100nF" if tag == "C130" else "10uF", desc,
               "Capacitor_SMD:C_0805_2012Metric")
        net += c[1]
        gnd += c[2]
    # C140-C143: decoupling at the power inputs, ANALOG side of the bead.
    for tag in ("C140", "C141", "C142", "C143"):
        c = _c(tag, "100nF", "power-input decoupling")
        v5 += c[1]
        gnd += c[2]
    # the buck's furniture, keeping the CAD's C16x names
    c160 = _c("C160", "10uF/50V", "24 V input bulk -- 1206 for the DC-bias derating",
              "Capacitor_SMD:C_1206_3216Metric")
    v24 += c160[1]
    pgnd += c160[2]
    c161 = _c("C161", "100nF", "24 V input HF bypass")
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
    c165 = _c("C165", "100nF", "24 V HF bypass -- the second VIN/PGND pair (pins 10/11)")
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
        out += [("+3V3D", "F.Cu", 0.15, [P(-1.96, 0.75), P(_V3_CH_DX, 0.75)]),
                # on B.Cu, NOT In2: down the channel on In2 it fenced the one free signal
                # layer off between every pair of cells, and the +3V3D rail itself then
                # failed to cross from cell to cell (4 of 14 open). B.Cu is a GND pour; a
                # 4 mm track in it costs the pour a slot, not the router a layer.
                ("+3V3D", "B.Cu", 0.15, [P(_V3_CH_DX, 0.75), P(_V3_CH_DX, -3.27)]),
                ("+3V3D", "F.Cu", 0.15, [P(_V3_CH_DX, -3.27), P(-1.25, -3.27)]),
                # and IOVDD's own pin 19 straight down onto that same pad
                ("+3V3D", "F.Cu", 0.2, [P(-1.25, -1.96), P(-1.25, -3.27)])]
    return out


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
    "cutouts": [{"xy": [round(x - CX, 4), round(y - CY, 4)], "d": OP.O_ROD_HOLE_D}
                for x, y in OP.O_ROD_HOLES],
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
        # USB334x datasheet (SMSC/Microchip rev 1.2, Table 4.4 ULPI Interface Timing):
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
         "why": "USB334x Table 4.4: T_SC 5.0 ns setup, T_HC 0.0 ns hold. 16.67 ns "
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
    "router_passes": 50,
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
    "via_keepouts": [[-34.5, -101.0, -27.5, -78.0]] + _spine_keepout(),
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
    # ⚠ ONE GROUND PAD GIVES WAY TO THE USB PAIR, and it is the right way round. The
    # pair routes first and its escape vias occupy the copper beside the PHY, which
    # leaves U7.19 nowhere to drill. The trade is not close once stated: a ground pad
    # that misses its own via still reaches the plane through the F.Cu pour -- a
    # degraded connection, not an absent one, and the connection every board in this
    # project had until this session. A differential pair that cannot escape as a pair
    # is not a differential pair at all, and nothing downstream recovers it.
    #
    # AND U7.19 IS THE CHEAPEST ONE TO LOSE: the USB3343 is a QFN whose EXPOSED PAD is
    # its primary ground, and that pad takes a via straight through its own copper (see
    # the big-pad branch in layout.py). U7.19 is a second ground pin on a part that is
    # already solidly grounded, not a part's only path to the plane.
    # ⚠ AN EXCEPTION LIST IS A SNAPSHOT OF A LAYOUT, and it goes stale silently. These
    # four were the ground pads the stitcher could not reach around the OLD USB cluster,
    # and after the chain was re-planned they were pads it could have reached and was
    # being told not to -- which showed up as U7.19 and U10.2 sitting unconnected on a
    # routed board. Empty is the right default; re-add only what the stitcher reports.
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
    "stitch_exceptions": ("J1.SH",) + tuple("U%d.%d" % (u, p) for u in range(14, 19)
                                            for p in (4, 15, 16)),
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
    "tracks": _cell_tracks(),
    "vias": ([("+3V3D",) + _cell_pt(k, _V3_CH_DX, y)
              for k in range(5) for y in (0.75, -3.27)]
             + [("I2C2_SCL",) + _cell_pt(k, _I2C_SPINE_DX, _I2C_SCL_DY)
                for k in range(5)]
             + _led_row_vias() + _mid_vias() + _bus_vias() + _v3a_vias() + _sd_vias()),
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
    with open(os.path.join(OUT_DIR, "optical.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.2f x %.2f mm, %d placements, x%d per instrument"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]),
             BOARD_NOTES["qty_per_instrument"]))
