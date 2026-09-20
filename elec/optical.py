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
transimpedance amps turn tens of nanoamps into volts; twenty ADC channels on one
STM32H743 digitise them; firmware forms SUM (the audio) and DIFF (the lateral
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
nanoamps, or that a 60 MHz ULPI bus has timing. Two of the three things this
paragraph used to list as unchecked are now checked: verify.py holds ULPI skew
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
    "0805OPT":  "LED_SMD:LED_0805_2012Metric",
    "SOIC-14":  "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
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
    "IND-4040": "Inductor_SMD:L_Sunlord_SWPA4020S",
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

# ── THE ADC MAP, and the pair skew it cannot avoid ───────────────────────────
# ⚠ THE COUNTING BELOW WAS DONE FOR THE LQFP144 AND THE PART IS NOW AN LQFP176. The
# arithmetic that follows -- 28 ADC-capable pins, ULPI taking seven, 21 left for 20
# channels, one spare -- described the 144 and is kept because it is why the board is
# not an LQFP100 (16 channels) and why the channel-to-ADC split is what it is. On the
# 176 the constraint is looser, not tighter, so nothing here becomes unsafe; but the
# "one spare" is no longer the true headroom and the pin-crowding argument at the end
# of this note ("twelve on the strip-facing edge and eight round the corner") was
# measured on the 144's pinout and has NOT been re-measured on the 176.
# The pair mapping itself is package-independent: ADC channel numbers follow the PORT
# pin (PF3 is ADC3_INP5 on any package), so ADC_PAIRS did not have to move.
#
# ⚠ A STRING'S TWO DETECTORS SHOULD BE SAMPLED AT THE SAME INSTANT, AND THEY CANNOT
# ALL BE. SUM and DIFF are formed from a pair, so any time skew between A and B
# leaks the common mode (which is the large SUM signal) into the difference. The
# H743 has three ADCs, and the pins do not distribute 10/10:
#     ADC1 can reach 11 of the free pins, ADC2 9, ADC3 9
# -- and PF3..PF10, eight pins, are ADC3-ONLY, so ADC3 must carry at least eight
# channels. Sequences of 8/6/6 were the best split available on those pins alone.
#
# ⚠ THE SPLIT IS NOW 10/6/4, TRADED DELIBERATELY FOR ROUTING. Strings 5 and 8 moved
# their A channel from PF11/PF12 (ADC1, and on the package edge FACING AWAY from the
# sensing strip) onto PC2_C/PC3_C, the direct ADC3 inputs on the edge that faces it --
# see the corridor note further down for why that is the whole problem. ADC3 therefore
# runs ten conversions, ADC1 four.
#
# THE TIMING GOT BETTER, NOT WORSE, WHICH IS WHY IT WAS AFFORDABLE. The burst is bounded
# by the LONGEST sequence: 10 x 0.7 us = 7.0 us of a 20.8 us frame, against 5.6 us
# before -- still a burst, still finishing in the first third of the frame, which is the
# condition the argument above actually rests on. And both moved pairs are now SAME-ADC
# with their partner adjacent in the sequence, so their skew is ONE conversion, 0.7 us,
# where the worst cross-ADC pair sits at two. The -46 dB bound below is a worst case that
# these two pairs no longer occupy.
#
# THE RESIDUAL IS SMALL AND BOUNDED, which is the point of writing it down rather
# than discovering it. Run the sequence as a BURST at the top of each 48 kHz frame
# (~0.7 us per conversion at 16 bit, so ~6 us of a 20.8 us frame) and the worst
# pair skew is two conversions, ~1.4 us. At a 1 kHz fundamental that is 0.5 deg of
# phase and about -46 dB of SUM leaking into DIFF -- far below what DIFF is for,
# which is detecting that SUM has collapsed. It is also correctable for free in
# firmware: the skew is a known constant, so a short fractional delay on the earlier
# channel removes it. What must NOT happen is spreading the scan across the frame;
# then the skew is a whole conversion INTERVAL rather than a conversion, and the
# argument above stops holding.
#
# ⚠ AND THREE SEPARATE PROXIES FOR "HOW HARD IS THIS TO ROUTE" HAVE NOW BEEN WRONG ON
# THIS BOARD. Before trusting a fourth, read this. The permutation lever was re-opened
# 2026-09-18 with two metrics that both said a particular reassignment was better:
#
#     straight-line crossings   said 80 -> 44        actually destroyed the A side
#     weighted far-edge cost    said 519 -> 279      board went 1 -> 4 unconnected
#     per-edge inversions       said 40 -> 33        same run, same result
#
# The far-edge measure is the one that looked most principled: twenty nets, fifteen pins
# on the edge that faces the strip, so at least five must travel around the package, and
# it is obviously worse to spend a far pin on the string whose quad is already furthest
# away. String 2 sits 106 mm out and held a far pin; the reassignment gave it a
# near-only pair and handed the worst pair to string 10 at 30 mm. Both metrics improved,
# the argument still reads correctly, and the router lost three nets.
#
# The honest conclusion is not "use a better proxy" but that ON THIS BOARD the only
# measurement that has ever predicted routability is a routing run. Proxies are for
# generating candidates, never for accepting them.
#
# ⚠ THE ZERO-INVERSION CLAIM BELOW COULD NOT BE REPRODUCED, and it should be read with
# that in mind. Counting inversions per package edge -- nets on different edges cannot
# cross each other at the pin row, so mixing pads 1..44 with 45..88 in one ordering is
# meaningless and the first attempt at this did exactly that -- the CURRENT map scores 40,
# not 0. Either the measure differs from the one used below or the claim has gone stale;
# what is certain is that the PC2_C/PC3_C move took it from 31 to 40 and was still worth
# making, because the board went from 2 unconnected to 1. If inversions do not predict
# routability, the argument below deserves the same scepticism as the two above it.

# ⚠ WHICH STRING GETS WHICH PAIR IS FREE, AND IT IS ALREADY SPENT WELL -- CHECKED, so
# that nobody spends an afternoon rediscovering it. The skew argument above constrains
# what may form a PAIR and the order of the burst; it says nothing about which string
# uses which pair, so the mapping is available as a routing lever. Measured on the
# routed board, the A channels arrive at the MCU's -X edge in pad order 13,14,15,18,
# 19,20,21,22,27 against quads at y 38,38,57,57,76,76,94,94,113 -- monotonic, so the A
# side has ZERO crossings and permuting it can only make things worse.
#
# ⚠ WHAT IS LEFT IS SILICON, NOT PLACEMENT. Of the 20 ADC pins this board uses, 12 are
# on the strip-facing edge and EIGHT ARE NOT -- they are round the corner on the edge
# that faces away, so those eight nets must travel past the package to reach it.
# ⚠ AND THE LAST THREE NETS FAIL AT THE ESCAPE, NOT ON THE HAUL. Measured 2026-09-17
# after the ADC remap, with two experiments that both came back negative:
#   60 passes, continuing from the 25-pass board -> byte-identical result, same three
#     nets, same fragment lengths to four decimals. Router effort does nothing.
#   incremental (93 nets frozen, only the 3 free) -> also nothing, and no faster.
# Neither effort nor interference from movable neighbours, then. Copper per net says
# what it is:
#     TIA_OUT_8B  pin 24   26.8 mm   UNROUTED
#     TIA_OUT_2A  pin 33   13.1 mm   UNROUTED
#     TIA_OUT_5A  pin 59   18.4 mm   UNROUTED
#     TIA_OUT_2B  pin 63  159.7 mm   ok
#     TIA_OUT_4B  pin 55  152.0 mm   ok
# The three failures carry the LEAST copper of all twenty -- 13 to 27 mm against 44 to
# 160. They did not get most of the way and stall; the router barely got off the pad.
# That is escape congestion at a 0.5 mm pitch package carrying 20 ADC nets and a
# 12-signal ULPI bus, and it is why neither lever above touched it.
#
# ⚠ AND IT IS NOT THE PIN'S OWN NEIGHBOURHOOD EITHER -- that hypothesis was built,
# measured and disproved. Counting how many of a pin's four nearest neighbours also need
# a lateral escape gives the three failures 2.00 and the seventeen that routed 2.76: the
# ones that failed are LESS locally crowded, not more.
#
# WHAT IT ACTUALLY IS, measured: the approach corridor. Copper coverage in the 20 x 24 mm
# region where every ADC net and the ULPI bus converge on the MCU, against the board's
# own average --
#     F.Cu    10.6%  vs  3.3%   (3.2x)
#     In2.Cu  12.8%  vs  5.4%   (2.4x)
#     B.Cu     4.6%  vs  1.9%   (2.4x)
# Twenty analog nets and twelve ULPI signals all have to reach one 26 mm package, so the
# density piles up where they meet it. That is why more passes changed nothing: the
# corridor is full, and no amount of search finds room that is not there.
#
# ⚠ B.Cu IS THE LEAST USED LAYER IN THAT CORRIDOR -- 4.6% against F.Cu's 10.6%, less than
# half -- which is the cheapest lever left and has not been tried. If freerouting is
# steering away from the bottom layer (layer costs, preferred directions, or simply
# because the fan-out starts on F.Cu), pushing traffic down there costs nothing but a
# router setting. Try that before moving the MCU or the pin map.
#
# ⚠ THE OTHER LEVER, recorded rather than taken because it trades against something just
# won: PC2_C and PC3_C (pins 34 and 35) are now UNUSED -- freed when ULPI_DIR and
# ULPI_NXT moved to PI11/PH4 -- and 34 is adjacent to the failing pin 33. They are
# ADC3_INP0 and ADC3_INP1, so they are real channels. Moving a failing net onto one
# costs part of the zero-inversion ordering above, so it wants the same inversion
# scoring that produced that ordering, not a guess.
#
# ⚠ RE-MEASURED ON THE LQFP176, 2026-09-17, because this paragraph was written for the
# LQFP144 and a package change is exactly the kind of thing that silently invalidates a
# measurement. It does not: the split is still 12 / 8. Twelve TIA_OUT pads sit on U6's
# -X edge, which faces the strip; eight sit on its +Y edge, which faces away --
#     +Y: TIA_OUT_3B 4B 6B 7B 8B 9A 9B 10B
# and those eight are still the nets that finish last. Of the three unconnected left on
# the current route, TIA_OUT_8B is one of them. That is the H743's ADC pin distribution meeting a board whose analog all arrives
# from one direction, and there is no assignment that fixes it: the pins are where they
# are. Rotating the MCU does not help either (elec/orient.py scores it at its best
# orientation already), and the eight are why a handful of TIA_OUT nets are the last
# ones to finish routing.
#
# Order below is (A_pin, B_pin) per string, chosen so each pair spans two different
# ADCs where possible and sits adjacent in the scan otherwise.
# ⚠ REORDERED 2026-09-17, AND THE METRIC IS THE WHOLE STORY. Measured on the placed
# board, the twenty strip-to-MCU nets arrived at their pins with ELEVEN inversions from
# monotonic -- A side 0, B side 11. The A side's perfection is what the note above
# records and it is real; the B side had never been looked at, and 11 inversions across
# 7 pins on one package edge is most of the disorder there is room for.
#
# ⚠ THE FIRST ATTEMPT AT THIS MADE IT WORSE AND THE PROXY SAID IT WAS BETTER. Scoring
# candidate maps by CROSSINGS BETWEEN STRAIGHT RATSNEST LINES said the best permutation
# cut 80 crossings to 44 -- and it got there by destroying the A side, 0 inversions to
# 14, to buy ONE inversion on the B side. Those long diagonal lines cross each other
# because the board is long, not because the escape is hard; what actually costs a via
# is the ORDER nets arrive in at a pin row. Scored on inversions instead, the same
# search returns the opposite answer. The proxy was not slightly wrong, it was inverted.
#
# ⚠ AND PERMUTATION ALONE CANNOT FIX IT, which is why this was stuck. Which string gets
# which PAIR is free, but a pair carries both its pins, so re-ordering the B side drags
# the A side with it -- best case 8 inversions with A degraded to 2. The lever that
# works is swapping A and B WITHIN a pair: it moves one pin between the two lists
# without changing which pair a string owns, so both sides can be ordered at once.
# Result: ELEVEN INVERSIONS TO ZERO, both sides monotonic, three strings swapped.
#
# ⚠ WHAT THE SWAP COSTS -- AND THE FIRST VERSION OF THIS NOTE OVERSTATED IT. It claimed
# DIFF = A - B comes out sign-inverted on the three swapped strings. It does not. The
# hookup loop below is `tia_out[(i, "A")] += u6[PIN[pa]]`: detector A goes to the
# FIRST-LISTED pin of its pair, for all ten strings, before and after the reorder. Any
# firmware generated from this table therefore reads A as A, and the sign is uniform.
#
# What the swap actually breaks is an INCIDENTAL INVARIANT nobody declared. In the
# original order, detector A landed on ADC3 for strings 1-8 and ADC2 for 9-10 -- never on
# ADC1. The three swapped strings now put A on ADC1 (PA1, PF11, PF12) and B on ADC3. So
# firmware that tells the two detectors apart by WHICH ADC UNIT SAMPLED THEM -- a
# tempting shortcut when three ADCs run in parallel and the results are demultiplexed
# afterwards -- gets exactly these three backwards. Firmware that goes by the pin table
# is unaffected.
#
# The obligation is therefore: demultiplex by pin, not by ADC unit. DIFF_SIGN_INVERTED
# below names the three strings that would be wrong if that rule is broken; it is a
# tripwire, not a correction to apply. Since the PC2_C/PC3_C move the three fail in two
# different ways: string 1 has A on ADC1 where the other seven have A on ADC3 or ADC2,
# and strings 5 and 8 have BOTH channels on ADC3, so the unit does not distinguish them
# at all. Either way the unit is not the answer and the pin is. (SUM is symmetric and cannot be affected either
# way.) Recorded here because nothing in the netlist, the CAD or DRC can express it.
ADC_PAIRS = (
    ("PA1", "PF4"),          # 1   ADC1[1] / ADC3[1]
    ("PF3", "PA0"),          # 2   ADC3[0] / ADC1[0]  <- was string 10's pair
    ("PF10", "PA7"),         # 3   ADC3[7] / ADC2[5]
    ("PC4", "PC5"),          # 4   ADC2[0] / ADC2[1]
    ("PC3_C", "PF5"),        # 5   ADC3[9] / ADC3[2]
    ("PF9", "PA6"),          # 6   ADC3[6] / ADC2[4]
    ("PF8", "PA4"),          # 7   ADC3[5] / ADC1[5]
    ("PC2_C", "PF6"),        # 8   ADC3[8] / ADC3[3]
    ("PF7", "PA2"),          # 9   ADC3[4] / ADC1[4]
    ("PC1", "PF13"),         # 10  ADC2[2] / ADC2[3]  <- was string 2's pair
)
# ⚠ WHICH ADC UNIT A PIN CAN ACTUALLY REACH, CHECKED RATHER THAN ASSUMED. The pairing
# argument above is entirely about which ADC reads which detector -- and every word of it
# is worthless if a pin does not offer that ADC at all. Nothing downstream can catch it:
# the netlist just connects a net to a package pin, DRC compares copper to the netlist,
# and a pin wired to an ADC it does not have is a dead analog channel that looks perfect
# all the way to the bench.
#
# Verified 2026-09-17, all twenty pins against Table 9 of DS12110 (STM32H742/743/753),
# zero mismatches. The units each pin offers:
ADC_UNITS = {
    "PA0": (1, 2), "PA1": (1, 2), "PA2": (1, 2), "PA4": (1, 2),
    "PA6": (1, 2), "PA7": (1, 2), "PC1": (1, 2, 3), "PC4": (1, 2), "PC5": (1, 2),
    "PF3": (3,), "PF4": (3,), "PF5": (3,), "PF6": (3,), "PF7": (3,),
    "PF8": (3,), "PF9": (3,), "PF10": (3,), "PF11": (1,), "PF12": (1,), "PF13": (2,),
    "PC2_C": (3,), "PC3_C": (3,),   # ADC3_INP0 / ADC3_INP1, DS12110 p67
}
# the unit each pin is USED as, read off the ADCn[k] comments in ADC_PAIRS above
ADC_USED_AS = {
    "PA1": 1, "PF4": 3, "PC1": 2, "PF13": 2, "PF10": 3, "PA7": 2, "PC4": 2, "PC5": 2,
    "PC3_C": 3, "PF5": 3, "PF9": 3, "PA6": 2, "PF8": 3, "PA4": 1, "PC2_C": 3, "PF6": 3,
    "PF7": 3, "PA2": 1, "PF3": 3, "PA0": 1,
}
assert set(ADC_USED_AS) == {p for pair in ADC_PAIRS for p in pair}, (
    "ADC_USED_AS has drifted from ADC_PAIRS")
for _p, _u in sorted(ADC_USED_AS.items()):
    assert _u in ADC_UNITS[_p], (
        "%s is used as an ADC%d input and the H743 does not offer one there (it has %s)"
        % (_p, _u, ", ".join("ADC%d" % n for n in ADC_UNITS[_p])))

# ⚠ AND THE BRACKET IS A SCAN SLOT, NOT AN INP NUMBER. ADCn[k] above means "the k-th
# conversion in ADCn's sequence", a number this file assigns; it is NOT the datasheet's
# ADCn_INPk. The two disagree -- line 259 records PF3 as ADC3_INP5 while it sits in scan
# slot 0 -- and mixing them once already produced a contradiction: PC2_C and PC3_C were
# labelled ADC3[0] and ADC3[1], their real INP numbers, which collided with PF3's and
# PF4's slots when strings 5 and 8 moved onto them. They now carry slots 8 and 9, the two
# ADC3 had free. Only the UNIT digit is load-bearing (ADC_USED_AS is read off it); the
# slot is documentation, so it gets an assertion rather than trust.
ADC_SLOTS = {   # (unit, scan slot) per pin, read off the ADCn[k] comments above
    "PA0": (1, 0), "PA1": (1, 1), "PA2": (1, 4), "PA4": (1, 5),
    "PC4": (2, 0), "PC5": (2, 1), "PC1": (2, 2), "PF13": (2, 3),
    "PA6": (2, 4), "PA7": (2, 5),
    "PF3": (3, 0), "PF4": (3, 1), "PF5": (3, 2), "PF6": (3, 3), "PF7": (3, 4),
    "PF8": (3, 5), "PF9": (3, 6), "PF10": (3, 7), "PC2_C": (3, 8), "PC3_C": (3, 9),
}
assert set(ADC_SLOTS) == set(ADC_USED_AS), "ADC_SLOTS has drifted from ADC_PAIRS"
assert all(u == ADC_USED_AS[p] for p, (u, _k) in ADC_SLOTS.items()), (
    "a pin's ADC_SLOTS unit disagrees with ADC_USED_AS")
assert len(set(ADC_SLOTS.values())) == len(ADC_SLOTS), (
    "two pins claim the same ADCn[k] scan slot -- see the note above; this exact "
    "collision happened once")

# ⚠ DERIVED, BECAUSE THE HAND-WRITTEN VERSION OF THIS LIST WAS WRONG TWICE. It read
# (1, 5, 8) and named only one of the two ways the unit fails to identify a detector; it
# missed string 4, which has been same-ADC since before the list existed, and it did not
# follow the strings 2/10 swap, which moved the same-ADC pair from 2 to 10. A tripwire
# nothing downstream can check must not also be a fact nothing downstream can check.
DIFF_SIGN_INVERTED = tuple(
    i for i, (pa, pb) in enumerate(ADC_PAIRS, start=1)
    if ADC_USED_AS[pa] != 3 or ADC_USED_AS[pa] == ADC_USED_AS[pb])
#   strings whose detectors the ADC UNIT cannot tell apart -- either A is not on ADC3
#   where the majority put it, or both channels share one unit. A tripwire for firmware
#   that demultiplexes by unit, NOT a sign table to apply. Demultiplex by PIN.
assert DIFF_SIGN_INVERTED == (1, 4, 5, 8, 10), (
    "the demux-ambiguous set moved: %r -- re-read the note above before accepting it"
    % (DIFF_SIGN_INVERTED,))

# ⚠ AND THE TRAP THAT NEARLY MADE THIS CHECK LIE. The datasheet writes a channel shared
# between units as ADC12_INP14 or ADC123_INP11, one token, not as ADC1_INP14 plus
# ADC2_INP14. A search for "ADC1_INP" therefore finds NONE of the shared channels, and
# the first run of this check reported eleven of the twenty pins as having no ADC at all.
# Every one of those was the search being wrong. A second trap sits on top: extracting the
# table from the PDF as flat text scrambles the columns badly enough that a channel from
# one row lands beside another row's pin, so the answers that do come back cannot be
# trusted either. The numbers above were read with per-word coordinates, row by row,
# and the three the column logic could not resolve were read off the page by hand.
# ⚠ WHY THE MCU APPROACH CORRIDOR IS CROWDED, AND IT IS NOT A MAPPING MISTAKE. Measured
# on the placed board 2026-09-17: the H743 in LQFP176 has ADC-capable pins on only TWO of
# its four edges -- fifteen on the -X edge (PF3-PF10, PC0-PC3_C, PA0-PA2) and nine on the
# +Y edge (PA4-PA7, PC4, PC5, PF11-PF14). The other two edges have NONE.
#
# The sensing strip sits at -X and -Y of the package, spanning y 30 to 113 against the
# MCU at y 137. So the -X edge faces the strip and the +Y edge is the FAR side, and every
# net landing there has to travel around the package to reach it. Twenty nets, fifteen
# near pins: at least five must go the long way round whatever the assignment is. The
# current map sends eight, and two of the three nets that fail to route are among them.
#
# That is the density the corridor measurement found. It is a consequence of the pinout
# and the board being long, not of the pair ordering -- which is why re-permuting pairs
# could never fix it, and why the router settings could not either.
#
# ⚠ STRINGS 2 AND 10 HAVE SWAPPED PAIRS, AND IT CLOSED THE LAST ANALOG NET. Pair 2 is
# (PC1 near, PF13 FAR) and pair 10 is (PF3 near, PA0 near) -- both near. String 2's
# detectors sit 99 mm from the MCU, the farthest on the board; string 10's sit 23 mm away.
# Handing the far-edge pin to the string that barely travels, and the all-near pair to the
# string that travels farthest, is the trade the evidence asked for:
#
#     every net reaching a NEAR pin routes, at any distance up to 107 mm
#     five of the six nets reaching a FAR pin route
#     the one that failed was the FARTHEST of the far-pin group, at 99 mm
#
# TIA_OUT_1A runs 107 mm -- longer than the net that failed -- and routes, which is what
# rules out distance as the cause. The far-side crossing is a resource with about five
# slots, and the net arriving from farthest away was the one squeezed out of it.
#
# ⚠ WHAT IT COST: +3V3A. (STATE AT THE TIME -- the board is now 0 unconnected and 0
# violations; +3V3A is closed by the deliberate repair in route.py's repair block, which
# is where this paragraph's "better problem" was eventually solved.) The board was then
# still at 1 unconnected, but the open net had become the
# analog supply rail, 6.5 mm between a track at 71.16,46.43 and U2's pin 4 -- the freed
# analog nets took the corridor the rail had been using. That is a better problem than the
# one it replaced: a local gap beside an op-amp rather than a 123 mm run that has to get
# round the package, and it is in the part of the board the generator already pre-lays.
#
# ⚠ AND THE NEAR/FAR SPLIT IS NOT THE BINDING CONSTRAINT -- MEASURED BY MAKING IT ZERO.
# Everything above treats "at least five nets must travel around the package" as a floor
# set by the pinout. It is not a floor, because it assumes the package's ORIENTATION is
# fixed, and it is not: the ADC pins occupy two ADJACENT edges and the strip lies along
# two ADJACENT sides, so a rotation exists that puts both ADC edges against the strip.
# Measured on the placed board, classifying each pad by POSITION rather than by pin
# number (a metric keyed on (pin-1)//44 cannot see a rotation at all, which is how this
# went unnoticed):
#     U6 at   0 deg   -X 14 near  +Y  6 far
#     U6 at  90 deg   +Y 14 far   +X  6 far    -- zero near, the worst case
#     U6 at 270 deg   -Y 14 near  -X  6 near   -- ALL TWENTY face the strip
#
# ⚠ AND AT 270 THE BOARD ROUTES WORSE: 6 unconnected against 1. Reverted. Rotating the
# MCU moves every OTHER pin with it -- the ULPI bus, the USB pair, the crystals, the
# decoupling and the power entry are all placed around this package at 0 deg -- so
# perfecting the analog escape breaks the four things that were already working. The
# twenty analog nets are not the scarce resource they look like.
#
# The lesson is worth more than the experiment: the corridor-density diagnosis and the
# near/far split are descriptions of where the copper IS, not of what is stopping the
# router. Driving either to its optimum made the board worse, twice.

# ⚠ THE ONLY SLACK IS TWO PINS, AND THEY ARE ADC3-ONLY. PC0 is taken by ULPI_STP, PF14 is
# the spare on the far edge, so the free near-edge ADC pins are PC2_C (34) and PC3_C (35)
# -- ADC3_INP0 and ADC3_INP1, no other unit. Moving a far-edge net onto one takes the
# near/far split from 12/8 to 13/7, and makes that net's pair same-ADC unless its partner
# is already off ADC3. Strings 4 and 10 are same-ADC today (it was 2 and 4 until the
# strings 2/10 swap moved the pair), so that is a cost the design has accepted twice; the real cost is that ADC3 would carry ten channels against
# ADC1's four, which is a scan-rate imbalance and wants checking against the latency
# budget before it is spent.

ADC_SPARE = "PF14"      # the one channel left over; brought out to nothing


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
    # emitter return -- 211 mA pulsed at 96 kHz, the board's worst aggressor -- is
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
    # TIAs (a quarter of a quad each) with Rf/Cf, and two ADC pins.
    led_row = Net("LED_ROW")        # the switched low side, common to all ten
    pd_a, pd_b = {}, {}
    for i in range(1, 11):
        # THE BALLAST IS PER-STRING AND THAT IS LEVER 2 OF THE SIGNAL BUDGET. A .014
        # plain string returns ~14 dB less than a .070 wound one because the string IS
        # the reflective target, and with narrow-beam emitters unavailable in 0805
        # (lever 1 is gone -- see src/optical_pickup.py) drive current is the first
        # lever left. Values are set at bring-up, per string, not here.
        # 180R = 20 mA, WHICH IS THE DATASHEET'S OWN OPERATING POINT and deliberately
        # conservative. (5.0 - 1.2 VF) / 0.020 = 190; 180R gives 21 mA. The IR17-21C is
        # rated 65 mA continuous, so there is 3x of headroom -- and taking it is a SYSTEM
        # decision, not a resistor swap: ten emitters at 65 mA is 650 mA of peak rail
        # against a 600 mA buck, and the board's recorded 24 V draw (~85 mA, i.e. ~2 W)
        # assumes something near this value. Raising drive is the first SNR lever this
        # board has left, and spending it means re-checking U13, C162's droop over a
        # pulse, and the trunk's wire gauge together.
        r = _r("R%d" % i, "180R", "LED ballast, string %d -- 21 mA, tune per string" % i,
               "Resistor_SMD:R_0603_1608Metric")
        d = Part(name="LED_IR", ref_prefix="D", ref="D%d" % i, dest="NETLIST",
                 tool="skidl", value="IR17-21C/TR8",
                 description="IR emitter 940 nm, string %d (LCSC C131250)" % i,
                 footprint="LED_SMD:LED_0805_2012Metric",
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
            pd = Part(name="PHOTODIODE", ref_prefix="PD", ref="PD%d%s" % (i, tag),
                      dest="NETLIST", tool="skidl", value="VEMD4110X01",
                      description="filtered Si PIN photodiode, string %d side %s "
                      "(LCSC C3211080)" % (i, tag),
                      footprint="Diode_SMD:D_0805_2012Metric",
                      pins=[Pin(num=1, name="K", func=P), Pin(num=2, name="A", func=P)])
            store[i] = pd

    # ── U1-U5: the transimpedance amps, four to a quad ───────────────────────
    # TLV9064, SOIC-14. 500 fA input bias -- which is the spec that matters, because
    # the signal is tens of nanoamps and an op-amp's bias current adds directly to it.
    # Channel order within a quad follows the CAD's placement so the summing node
    # stays a few millimetres long; that node is the noise-critical point on this
    # board and the reason the quads sit immediately -X of the sensor row.
    quads = {}
    for q in range(1, 6):
        quads[q] = Part(
            name="TLV9064", ref_prefix="U", ref="U%d" % q, dest="NETLIST",
            tool="skidl", value="TLV9064IDR",
            description="quad op-amp, 4x transimpedance amp (LCSC C388176)",
            footprint="Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
            pins=[Pin(num=n, func=P) for n in range(1, 15)])
    # SOIC-14 quad pinout: 1 OUT_A, 2 IN-_A, 3 IN+_A, 4 V+, 5 IN+_B, 6 IN-_B,
    # 7 OUT_B, 8 OUT_C, 9 IN-_C, 10 IN+_C, 11 V-, 12 IN+_D, 13 IN-_D, 14 OUT_D
    SEC = {0: (1, 2, 3), 1: (7, 6, 5), 2: (8, 9, 10), 3: (14, 13, 12)}

    tia_out = {}
    for ch in range(20):                       # 0..19 -> (string, side)
        i, side = ch // 2 + 1, "A" if ch % 2 == 0 else "B"
        q, sec = quads[ch // 4 + 1], SEC[ch % 4]
        out_p, inn_p, inp_p = sec
        # Rf<quad><section>, the CAD's scheme: Rf11..Rf14 for quad 1, Rf21.. for quad 2.
        n = "%d%d" % (ch // 4 + 1, ch % 4 + 1)
        pd = (pd_a if side == "A" else pd_b)[i]
        summing = Net("TIA_IN_%d%s" % (i, side))
        out = Net("TIA_OUT_%d%s" % (i, side))
        tia_out[(i, side)] = out
        # ZERO BIAS: the photodiode's anode sits on the virtual earth and its cathode
        # on MID, so there is no reverse bias and therefore no dark current to speak
        # of. Dark current is the noise floor this board actually lives against.
        #
        # ⚠ ZERO BIAS ALSO MEANS THE DATASHEET'S HEADLINE NUMBERS ARE THE WRONG ONES.
        # Vishay characterises the VEMD4110X01 at VR = 5 V, and both figures that
        # matter here move at VR = 0:
        #   responsivity   Ira 2.4 uA/(mW/cm2) at VR = 5 V, but Ik 2.2 at zero bias --
        #                  and Ik, the SHORT-CIRCUIT current, is precisely what a
        #                  virtual-earth TIA measures. 2.2 is the number to design to.
        #   capacitance    CD 2.5 pF at VR = 5 V but 7 pF at VR = 0 (1 MHz). Nearly 3x,
        #                  and CD is what sets the TIA's noise gain and its stability
        #                  margin, so anyone re-deriving Cf from the front page of the
        #                  datasheet will get it wrong by a factor of three.
        # With Cin = 7 (diode) + 6 (TLV9064: CID 2 pF + CIC 4 pF both appear at the
        # inverting input) + ~2 (board) = 15 pF against Rf = 4M7 and the TLV9064's
        # 10 MHz GBW, the minimum feedback capacitance for stability is
        # sqrt(Cin / (2*pi*Rf*GBW)) = 0.23 pF. Cf is 2.2 pF -- ten times that,
        # deliberately overdamped, because the pole it sets is wanted anyway as the
        # anti-alias filter. The 3x capacitance error would still have been safe here;
        # it is recorded because the next person to move Rf will need it.
        #
        # AND THE NOISE BUDGET FALLS OUT OF THE SAME THREE NUMBERS, which is worth
        # having written down because it says how much room this design has:
        #   Rf thermal   sqrt(4kTR) = 279 nV/rtHz   -- dominant, as it should be
        #   in * Rf      23 fA/rtHz x 4M7 = 108     -- not negligible
        #   en * NG      10 nV/rtHz x (Cin+Cf)/Cf = 10 x 7.8 = 78
        # summing to 309 nV/rtHz -- but THE THREE TERMS DO NOT SHARE A BANDWIDTH, and
        # treating them as if they did understates this floor by about 2.5x.
        #
        # ⚠ Rf*Cf ROLLS OFF THE FIRST TWO TERMS AND NOT THE THIRD. Rf's thermal noise and
        # in*Rf both travel the feedback path, so the same 15.4 kHz pole that shapes the
        # signal shapes them: 24 kHz of equivalent noise bandwidth is right for those two.
        # The op-amp's OWN voltage noise does not travel that path. It appears at the
        # output multiplied by the noise gain 1 + Zf/Zin, which RISES from unity at a zero
        # of 1/(2*pi*Rf*(Cin+Cf)) = 1.97 kHz to the (Cin+Cf)/Cf = 7.8 plateau, and then
        # stays there until the loop runs out of gain at GBW/NG = 10 MHz / 7.8 = 1.28 MHz.
        # Rf*Cf does not end that plateau; it CREATES it.
        #
        #   Rf thermal   279 nV/rtHz over 24 kHz            ->   43.4 uVrms
        #   in * Rf      108 nV/rtHz over 24 kHz            ->   16.8
        #   en * NG       78 nV/rtHz over 1.28 MHz          ->  110.8   <- dominant
        #                                          total        120 uVrms
        #
        # Against the thinnest string's 0.28 V that is ~67 dB rather than the ~75 dB this
        # note used to claim, and ~55 dB on a worst-case emitter rather than ~63.
        #
        # ⚠ AND IT IS AN ALIASING PROBLEM, NOT ONLY A NOISE ONE, WHICH IS THE PART THAT
        # MATTERS. This pole is described elsewhere as the anti-alias filter, and for the
        # signal it is. For the dominant noise term it is not: 78 nV/rtHz of flat noise
        # from 2 kHz to 1.28 MHz meets a 48 kHz sampler with nothing in between -- the TIA
        # output net carries the op-amp, Rf and Cf and then goes straight to an ADC pin --
        # so essentially all of it folds into 0-24 kHz. Averaging does not recover it,
        # because it is white and already in band once sampled.
        #
        # The lever is therefore NOT emitter drive, which is what this note used to say.
        # The plateau ends at GBW/NG, so it scales with the op-amp's bandwidth: a 1 MHz
        # part in place of the TLV9064's 10 MHz would cut that term by sqrt(10) to ~35
        # uVrms and put the total back near 58. A real RC between each TIA and its ADC pin
        # would do it properly, at 40 parts across twenty channels. A FASTER op-amp would
        # make this worse, which is the opposite of the usual instinct.
        #
        # ⚠ 67 dB IS STILL WORKABLE and none of this is a reason to stop -- DIFF's job is
        # detecting that SUM has collapsed, and 55 dB on the worst-case emitter still does
        # that. It is recorded because the number was wrong, the conclusion drawn from it
        # pointed at the wrong lever, and the next person to tune this front end needs the
        # bandwidth argument more than they need the spot figures.
        mid += pd[1]
        summing += pd[2], q[inn_p]
        mid += q[inp_p]
        out += q[out_p]
        # ⚠ 4M7 IS A FIRST-ARTICLE VALUE WITH ARITHMETIC BEHIND IT, not a guess, and it
        # is expected to move per string. The optical budget, from the two datasheets:
        #   emitter   0.8 mW/sr at 20 mA (IR17-21C), gap 3.0 mm (OPT_GAP)
        #             ⚠ 0.8 IS THE TYPICAL AND THE DATASHEET'S MINIMUM IS 0.2 -- a
        #             FOURFOLD spread, guaranteed, on the part that sets the whole
        #             optical budget. Everlight's own table (IR17-21C/TR8,
        #             Electro-Optical Characteristics): Ie min 0.2, typ 0.8, no max.
        #             Everything below is computed on the typical, so a worst-case
        #             emitter delivers a QUARTER of it: the thinnest string's ~60 nA
        #             becomes ~15 nA and 0.28 V at the output becomes 0.07 V.
        #             THAT IS STILL WORKABLE -- against the 120 uVrms noise floor
        #             computed further down it is ~55 dB instead of ~67 -- but it is
        #             the number the per-string Rf tuning has to absorb, and it is why
        #             that tuning is not optional. Ten emitters from one reel will not
        #             span the full 4x; ten boards built a year apart might.
        #             -> ~8.9 mW/cm2 at the string
        #   string    a .014 plain intercepts ~0.036 x 0.1 cm and scatters it; at ~30%
        #             into a hemisphere that is ~0.003 mW/sr back
        #   detector  2.2 uA per mW/cm2 (VEMD4110X01 Ik, the ZERO-BIAS figure -- see
        #             the note at the summing node), ~3.4 mm away
        #             -> of order 60 nA for the THINNEST string
        # which is the "tens of nanoamps" this board was designed around, arrived at
        # independently. 4M7 turns 60 nA into 0.28 V and a wound string's ~300 nA into
        # 1.4 V, so the quiet end has signal and the loud end does not clip the 2.9 V
        # the ADC can see above MID. It is a compromise across a 14 dB spread, which is
        # exactly why the value is per string and why the footprints stay 0402.
        rf = _r("Rf%s" % n, "4M7", "TIA feedback, string %d%s -- tune per string" % (i, side))
        # ⚠ Cf IS C0G, NOT X7R, and that is not a general-purpose preference. It sets
        # the anti-alias pole with Rf; an X7R part's capacitance moves with bias and
        # temperature, so the pole would drift and the twenty channels would stop
        # matching each other -- which is exactly what DIFF cannot tolerate.
        # 2.2 pF against 4M7 puts the pole at 15.4 kHz -- below the 24 kHz Nyquist of a
        # 48 kHz frame, which is what an anti-alias pole is for. It is also the smallest
        # value worth specifying: stray capacitance across an 0402 is a few tenths of a
        # pF, so anything under ~2 pF is set by the layout rather than by the part.
        cf = _c("Cf%s" % n, "2.2pF", "TIA feedback cap, string %d%s -- C0G, 15.4 kHz pole"
                % (i, side))
        summing += rf[1], cf[1]
        out += rf[2], cf[2]
    # ⚠ THE QUADS RUN ON +3V3A, NOT +5V, AND THAT IS AN ABSOLUTE-MAXIMUM FIX.
    # Every TIA output goes straight to an ADC pin, and ST's Table 21 (DS12110,
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
    for q in range(1, 6):
        v3a += quads[q][4]
        gnd += quads[q][11]
        for k in (1, 2):
            c = _c("Cd%d%d" % (q, k), "100nF", "quad %d supply bypass" % q)
            v3a += c[1]
            gnd += c[2]

    # ── U6: the MCU ──────────────────────────────────────────────────────────
    mcu_pins = sorted(set(range(1, 177)))
    u6 = Part(name="STM32H743IIT6", ref_prefix="U", ref="U6", dest="NETLIST",
              tool="skidl", value="STM32H743IIT6",
              description="MCU, LQFP176, 20x ADC + OTG_HS ULPI (LCSC C89597)",
              footprint="Package_QFP:LQFP-176_24x24mm_P0.5mm",
              pins=[Pin(num=n, func=P) for n in mcu_pins])
    for n in MCU_VDD:
        v3d += u6[n]
    for n in MCU_VSS:
        gnd += u6[n]
    gnd += u6[PIN["VSSA"]]
    v3a += u6[PIN["VDDA"]], u6[PIN["VREF+"]]
    v3d += u6[PIN["VBAT"]], u6[PIN["VDD33_USB"]], u6[PIN["PDR_ON"]]

    # the twenty analog inputs, in the pair order argued above
    for i, (pa, pb) in enumerate(ADC_PAIRS, start=1):
        tia_out[(i, "A")] += u6[PIN[pa]]
        tia_out[(i, "B")] += u6[PIN[pb]]
    Net("ADC_SPARE_NC").connect(u6[PIN[ADC_SPARE]])

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
                         "VCAP1", "VCAP2", ADC_SPARE)}
    used |= {PIN[p] for pair in ADC_PAIRS for p in pair}
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
    #                                                   subtotal  11.7 / 16.1 mA
    #
    #   +3V3D  (U8, AMS1117, off the BUCK side)
    #     STM32H743 400 MHz VOS1, all peripherals enabled (DS12110 T30)
    #                              165 typ / 220 max @25 C / 400 max @85 C
    #     USB3343 sync mode, HS active (DS00002646 T4-2), VBAT + VDDIO
    #                               41 typ /  51 max
    #     R31 / R37 RBIAS / R38                             ->   0.8
    #                                            subtotal  207 / 272 / 452 mA
    #
    #   +5V / V5_PRE  (U13, TPS560430, 600 mA)
    #     ten emitters at 21.1 mA, pulsed -- 105 mA average, 211 mA while on
    #       ⚠ THE 50% DUTY IS AN INFERENCE ABOUT FIRMWARE THAT DOES NOT EXIST YET, not
    #       a measurement: the emitters run at 96 kHz against a 48 kHz sample rate with
    #       an LEDs-off ambient sample between, so equal on and off periods give 50%.
    #       Firmware could choose a shorter pulse. IT DOES NOT CHANGE THE CONCLUSION --
    #       at 100% duty the emitters are 211 mA continuous and the typical total
    #       becomes 430 mA, still 72% of the buck -- so the budget holds whatever the
    #       firmware picks. Only the "324 mA typical" headline moves.
    #     U8 input ~= its output                             207 / 272 / 452
    #     U9 input ~= its output                              12 /  16 /  16
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
    # Pinout, datasheet section 6: 1 CB, 2 GND, 3 FB, 4 EN, 5 VIN, 6 SW.
    u13 = Part(name="TPS560430XF", ref_prefix="U", ref="U13", dest="NETLIST",
               tool="skidl", value="TPS560430XFDBVR",
               description="24V -> 5V synchronous buck, 1.1 MHz FPWM, 600 mA "
               "(LCSC C523980)",
               footprint="Package_TO_SOT_SMD:SOT-23-6",
               pins=[Pin(num=n, func=P) for n in range(1, 7)])
    v24 = Net("+24V")
    v24.drive = Pin.drives.POWER
    boot = Net("BOOT")
    boot += u13[1]
    pgnd += u13[2]
    fb += u13[3]
    # EN WAS LEFT FLOATING, and the datasheet says in as many words "Do not float".
    # Tied to VIN, which it explicitly allows; its precision threshold is 1.23 V, so
    # 24 V is solidly on.
    v24 += u13[4]
    v24 += u13[5]
    sw += u13[6]
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
    l1 = Part(name="L", ref_prefix="L", ref="L1", dest="NETLIST", tool="skidl",
              value="SWPA4020S150MT",
              description="buck output inductor, 15 uH shielded, Isat 1.35 A, "
              "DCR 0.299 ohm max, 4.0 x 4.0 x 2.0 (LCSC C36407)",
              footprint="Inductor_SMD:L_Sunlord_SWPA4020S",
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
               # 96 kHz, synchronously with sampling, the one noise source ambient
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
    r40 = _r("R40", "40k2 1%", "buck feedback divider, top -- 5.02 V with R41")
    r41 = _r("R41", "10k 1%", "buck feedback divider, bottom")
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
    # it, and the emitters pulsing at 96 kHz share the same rail. 10 uF beside U8 costs
    # one 0805 and one BOM line already in the build.
    c164 = _c("C164", "10uF/16V", "U8 input bulk -- the only local cap on V5_PRE",
              "Capacitor_SMD:C_0805_2012Metric")
    v5_pre += c164[1]
    gnd += c164[2]
    # 100 nF, not 10: the TPS560430 datasheet specifies "a high quality 100-nF capacitor"
    # from CB to SW. Too small a bootstrap cap droops over the on-time and under-drives
    # the high-side FET.
    c163 = _c("C163", "100nF", "buck bootstrap, CB to SW -- 100 nF per datasheet")
    boot += c163[1]
    sw += c163[2]


# ── the board ────────────────────────────────────────────────────────────────
# ⚠ OUTLINE AND PLACEMENTS BOTH COME FROM THE CAD. See the header: this is the one
# board whose shape the instrument dictates. _SECTIONS is (y0, y1, x_minus, x_plus)
# per band, and the shape it makes is a bracket -- wide over the endplate at both Y
# ends, narrow through the middle where it has to fit the 14 mm deck band.
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
    # Walk the +X side from -Y to +Y, then the -X side back down. The -X edge is one
    # straight line end to end (see COMPUTE_X0 in the CAD), so it contributes just its
    # two extreme corners -- emitting a point per band there would put collinear
    # duplicates on Edge.Cuts, which KiCad reports as a self-intersecting outline.
    pts = []
    for y0, y1, _x1, x0 in bands:
        if not pts or pts[-1] != (x0, y0):
            pts.append((x0, y0))
        pts.append((x0, y1))
    x_left = min(b[2] for b in bands)
    pts += [(x_left, bands[-1][1]), (x_left, bands[0][0])]
    return [(x - cx, y - cy) for x, y in pts]


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
    "repair_tracks": [("MID", "F.Cu", 0.25, [(-29.443, 48.312), (-30.740, 48.312)]),
                      ("MID", "F.Cu", 0.25, [(-30.740, 48.312), (-30.740, 45.772)]),
                      ("MID", "F.Cu", 0.25, [(-30.740, 45.772), (-29.443, 45.772)])],
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
    "router_passes": 25,
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
    "via_keepouts": [[-34.5, -101.0, -27.5, -78.0]],
    # ⚠ THE FEEDBACK CLUSTERS, LAID HERE RATHER THAN SEARCHED FOR. Twenty identical
    # networks -- op-amp output, feedback R, feedback C, and the photodiode on the input
    # -- packed into the Y gaps of a 13.6 mm strip that already holds 107 parts. Nearly
    # every unconnected pad this board reports is one of them failing to reach the pin
    # beside it, and they are the most generator-shaped thing on the board: the same
    # three-pad star, twenty times, at a spacing the string fan fixes.
    # Only the LOCAL cluster is laid; the long run to the MCU's ADC pin stays the
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
    "local_nets": (r"TIA_IN_\d+[AB]", r"TIA_OUT_\d+[AB]"),
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
    "stitch_exceptions": (),
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
    class_pkgs = ("0402", "0805OPT")
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
