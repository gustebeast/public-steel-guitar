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

⚠ ROUTING IS NOT FINISHED, AND HERE IS EXACTLY WHERE IT STOPPED. Freerouting gets
this board to 2 real violations and 15 unconnected items and then converges -- 20
passes and 30 passes give the same answer, and 30 is sometimes WORSE, so more
effort is not the missing ingredient. The remainder, diagnosed rather than
summarised, because "15 unconnected" is not something anyone can act on:

  * 13 of the 15 are DANGLING GND STUBS. The router laid a short track from a
    ground pad toward the plane and never placed the via at the end of it. GND
    lives on In1.Cu and B.Cu; a pad on F.Cu cannot reach it without one. These are
    a mechanical cleanup -- drop a via at each free end, or delete the stub and let
    the pad's own via serve it -- not a routing problem.
  * 2 are REAL: TIA_OUT_7A and TIA_IN_1B. Those are transimpedance amp nets in the
    dense sensing strip, and they want a human.
  * The 2 violations are dangling vias, same family as the first bullet.

AND THE COUNT IS NOT THE REASON TO FINISH IT BY HAND. Twenty summing nodes reading
tens of nanoamps and a 60 MHz ULPI bus are not things to hand to an autorouter and
stop looking at. Nothing here has checked that the ULPI pair is length-matched,
that the TIA inputs are guarded, or that the switcher's loop is tight -- and DRC
does not know to ask. Treat the routed .kicad_pcb as a CANDIDATE. The placement,
which is the part this file is actually responsible for, is clean: the only DRC
violations on the placed board are the 20 declared sensor-triplet courtyards.
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
    "QFN-24":   "Package_DFN_QFN:HVQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm",
    "SOT-223":  "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    "SOT-23":   "Package_TO_SOT_SMD:SOT-23",
    "SOT-23-5": "Package_TO_SOT_SMD:SOT-23-5",
    "SOT-23-6": "Package_TO_SOT_SMD:SOT-23-6",
    "SOT-563":  "Package_TO_SOT_SMD:SOT-23-6",        # ⚠ see the note above
    "3225":     "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    "IND-4040": "Inductor_SMD:L_Bourns-SRN4018",
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


# ── STM32H743ZIT6, LQFP144 ───────────────────────────────────────────────────
# ⚠ PIN NUMBERS READ OUT OF KiCad's OWN ST SYMBOL LIBRARY (MCU_ST_STM32H7.kicad_sym,
# symbol STM32H743ZITx), not recalled. That library is generated from ST's CubeMX
# database, so it is a source that can be pointed at rather than a memory. The VSS
# numbers are the eight pins the symbol leaves unnamed plus the one it names -- the
# symbol collapses stacked grounds, and a footprint needs all 144 pads netted.
MCU_VDD = (17, 30, 39, 52, 62, 72, 84, 108, 121, 131, 144)
MCU_VSS = (16, 38, 51, 61, 83, 94, 107, 120, 130)
PIN = {  # port name -> LQFP144 pin
    "PA0": 34, "PA1": 35, "PA2": 36, "PA3": 37, "PA4": 40, "PA5": 41,
    "PA6": 42, "PA7": 43, "PA13": 105, "PA14": 109,
    "PB0": 46, "PB1": 47, "PB3": 133, "PB4": 134, "PB5": 135,
    "PB10": 69, "PB11": 70, "PB12": 73, "PB13": 74,
    "PC0": 26, "PC1": 27, "PC2_C": 28, "PC3_C": 29, "PC4": 44, "PC5": 45,
    "PF3": 13, "PF4": 14, "PF5": 15, "PF6": 18, "PF7": 19, "PF8": 20,
    "PF9": 21, "PF10": 22, "PF11": 49, "PF12": 50, "PF13": 53, "PF14": 54,
    "PH0": 23, "PH1": 24,
    "NRST": 25, "BOOT0": 138, "PDR_ON": 143,
    "VBAT": 6, "VDDA": 33, "VSSA": 31, "VREF+": 32, "VDD33_USB": 95,
    "VCAP1": 71, "VCAP2": 106,
}

# ── ULPI, and it takes seven pins the ADC wanted ─────────────────────────────
# The OTG_HS ULPI mapping is essentially fixed on this part -- most of these signals
# have exactly one pin, and the alternates that exist (PI11 for DIR, PH4 for NXT)
# are not bonded out on LQFP144. So this is not a choice, it is the only mapping.
#
# ⚠ ULPI_DIR AND ULPI_NXT LAND ON PC2_C / PC3_C, WHICH ARE NOT ORDINARY PINS.
# On H7 in LQFP144 the package pin reaches the digital IO through an ANALOG SWITCH
# controlled by SYSCFG_PMCR (PC2SO/PC3SO). The switch is CLOSED by default -- 0 =
# closed -- and the digital alternate functions are available through it, so ULPI
# works. Two consequences for whoever writes the firmware and reads this netlist:
#   * The switch must be LEFT closed. Opening it to use the direct analog path
#     disconnects the ULPI signal, and the failure looks like a dead PHY.
#   * These two pins are therefore NOT available as ADC inputs, which is why the
#     photodiode budget below excludes them.
ULPI = {"ULPI_D0": "PA3", "ULPI_D1": "PB0", "ULPI_D2": "PB1", "ULPI_D3": "PB10",
        "ULPI_D4": "PB11", "ULPI_D5": "PB12", "ULPI_D6": "PB13", "ULPI_D7": "PB5",
        "ULPI_CK": "PA5", "ULPI_STP": "PC0", "ULPI_DIR": "PC2_C",
        "ULPI_NXT": "PC3_C"}

# ── THE ADC MAP, and the pair skew it cannot avoid ───────────────────────────
# 28 of the LQFP144's pins are ADC-capable; ULPI takes seven of them; 21 are left
# and the board needs 20. IT CLOSES WITH ONE SPARE (PF14), which is worth stating
# plainly because it is the tightest constraint on the whole board and it is the
# reason the part is an LQFP144 rather than the cheaper LQFP100 (16 channels).
#
# ⚠ A STRING'S TWO DETECTORS SHOULD BE SAMPLED AT THE SAME INSTANT, AND THEY CANNOT
# ALL BE. SUM and DIFF are formed from a pair, so any time skew between A and B
# leaks the common mode (which is the large SUM signal) into the difference. The
# H743 has three ADCs, and the pins do not distribute 10/10:
#     ADC1 can reach 11 of the free pins, ADC2 9, ADC3 9
# -- and PF3..PF10, eight pins, are ADC3-ONLY, so ADC3 must carry at least eight
# channels. Sequences of 8/6/6 are the best split available, which leaves two pairs
# sharing ADC2 and two pairs two conversions apart.
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
# Order below is (A_pin, B_pin) per string, chosen so each pair spans two different
# ADCs where possible and sits adjacent in the scan otherwise.
ADC_PAIRS = (
    ("PF3",  "PA0"),    # 1   ADC3[0] / ADC1[0]
    ("PF4",  "PA1"),    # 2   ADC3[1] / ADC1[1]
    ("PF5",  "PF11"),   # 3   ADC3[2] / ADC1[2]
    ("PF6",  "PF12"),   # 4   ADC3[3] / ADC1[3]
    ("PF7",  "PA2"),    # 5   ADC3[4] / ADC1[4]
    ("PF8",  "PA4"),    # 6   ADC3[5] / ADC1[5]
    ("PF9",  "PA6"),    # 7   ADC3[6] / ADC2[4]  -- skew 2
    ("PF10", "PA7"),    # 8   ADC3[7] / ADC2[5]  -- skew 2
    ("PC4",  "PC5"),    # 9   ADC2[0] / ADC2[1]  -- same ADC, skew 1
    ("PC1",  "PF13"),   # 10  ADC2[2] / ADC2[3]  -- same ADC, skew 1
)
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
    gnd, pgnd = Net("GND"), Net("PWR_GND")
    v5, v3d, v3a = Net("+5V"), Net("+3V3D"), Net("+3V3A")
    for n in (gnd, pgnd, v5, v3d, v3a):
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
        r = _r("R%d" % i, "ballast", "LED ballast, string %d -- PER-STRING VALUE" % i,
               "Resistor_SMD:R_0603_1608Metric")
        d = Part(name="LED_IR", ref_prefix="D", ref="D%d" % i, dest="NETLIST",
                 tool="skidl", value="IR17-21C/TR8",
                 description="IR emitter 940 nm, string %d (LCSC C131250)" % i,
                 footprint="LED_SMD:LED_0805_2012Metric",
                 pins=[Pin(num=1, name="K", func=P), Pin(num=2, name="A", func=P)])
        v5 += r[1]
        r[2] += d[2]
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
        mid += pd[1]
        summing += pd[2], q[inn_p]
        mid += q[inp_p]
        out += q[out_p]
        rf = _r("Rf%s" % n, "Rf", "TIA feedback, string %d%s -- PER-STRING VALUE" % (i, side))
        # ⚠ Cf IS C0G, NOT X7R, and that is not a general-purpose preference. It sets
        # the anti-alias pole with Rf; an X7R part's capacitance moves with bias and
        # temperature, so the pole would drift and the twenty channels would stop
        # matching each other -- which is exactly what DIFF cannot tolerate.
        cf = _c("Cf%s" % n, "Cf C0G", "TIA feedback cap, string %d%s -- C0G" % (i, side))
        summing += rf[1], cf[1]
        out += rf[2], cf[2]
    for q in range(1, 6):
        v5 += quads[q][4]
        gnd += quads[q][11]
        for k in (1, 2):
            c = _c("Cd%d%d" % (q, k), "100nF", "quad %d supply bypass" % q)
            v5 += c[1]
            gnd += c[2]

    # ── U6: the MCU ──────────────────────────────────────────────────────────
    mcu_pins = sorted(set(range(1, 145)))
    u6 = Part(name="STM32H743ZIT6", ref_prefix="U", ref="U6", dest="NETLIST",
              tool="skidl", value="STM32H743ZIT6",
              description="MCU, LQFP144, 20x ADC + OTG_HS ULPI (LCSC C114408)",
              footprint="Package_QFP:LQFP-144_20x20mm_P0.5mm",
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
    swdio, swclk = Net("SWDIO"), Net("SWCLK")
    swdio += u6[PIN["PA13"]]
    swclk += u6[PIN["PA14"]]
    led_gate = Net("LED_GATE")
    led_gate += u6[PIN["PB3"]]       # the emitter row's on/off, one GPIO for all ten
    # VCAP: the H7's internal core regulator needs its own capacitors, and leaving
    # them off is a part that boots intermittently rather than one that fails cleanly.
    vcap1, vcap2 = Net("VCAP1"), Net("VCAP2")
    vcap1 += u6[PIN["VCAP1"]]
    vcap2 += u6[PIN["VCAP2"]]
    # Every remaining pin is unconnected ON PURPOSE. The LQFP144 brings out far more
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
              "-- ⚠ OUT OF STOCK 2026-08-04, confirm before ordering",
              footprint="Package_DFN_QFN:HVQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm",
              pins=[Pin(num=n, func=P) for n in range(1, 26)])
    # Microchip USB3343 QFN-24: 1 DATA3, 2 DATA4, 3 DATA5, 4 DATA6, 5 DATA7,
    # 6 VDD33, 7 REFCLK, 8 VDD18, 9 CLKOUT, 10 XI, 11 XO, 12 VBAT, 13 ID,
    # 14 VBUS, 15 DM, 16 DP, 17 RBIAS, 18 VDDIO, 19 GND, 20 STP, 21 NXT,
    # 22 DIR, 23 DATA0, 24 DATA1, 25(EP) GND ... DATA2 shares with RESETB on
    # this package variant.
    # ⚠ THIS PINOUT IS THE ONE NUMBER SET ON THIS BOARD I COULD NOT READ OUT OF A
    # LIBRARY -- KiCad ships no USB3343 symbol. It is written here so it is VISIBLE
    # and must be checked against Microchip's datasheet at schematic review; see the
    # assertion in fab.py that stops an unconfirmed part reaching an order.
    usb_dp, usb_dm = Net("USB_DP"), Net("USB_DM")
    v1v8, refclk, rbias = Net("PHY_1V8"), Net("PHY_REFCLK"), Net("PHY_RBIAS")
    for pin, sig in ((1, "ULPI_D3"), (2, "ULPI_D4"), (3, "ULPI_D5"), (4, "ULPI_D6"),
                     (5, "ULPI_D7"), (20, "ULPI_STP"), (21, "ULPI_NXT"),
                     (22, "ULPI_DIR"), (23, "ULPI_D0"), (24, "ULPI_D1")):
        ulpi[sig] += u7[pin]
    ulpi["ULPI_D2"] += u7[13]
    ulpi["ULPI_CK"] += u7[9]
    v3d += u7[6], u7[12], u7[18]
    v1v8 += u7[8]
    refclk += u7[7]
    phy_xi, phy_xo = Net("PHY_XI"), Net("PHY_XO")
    phy_xi += u7[10]
    phy_xo += u7[11]
    Net("PHY_VBUS_NC").connect(u7[14])
    usb_dm += u7[15]
    usb_dp += u7[16]
    rbias += u7[17]
    gnd += u7[19], u7[25]

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
    v5 += u8[3]
    u9 = Part(name="SPX3819", ref_prefix="U", ref="U9", dest="NETLIST", tool="skidl",
              value="SPX3819M5-L-3-3/TR",
              description="3V3 ANALOG LDO, 40 uVrms (LCSC C9055)",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=n, func=P) for n in range(1, 6)])
    # SPX3819 SOT-23-5: 1 IN, 2 GND, 3 EN, 4 BYP, 5 OUT
    v5 += u9[1], u9[3]
    gnd += u9[2]
    Net("LDO_BYP_NC").connect(u9[4])
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
    vbus = Net("VBUS_NC")
    vbus += u10[5]

    # ── U11: the mid-rail buffer the twenty TIAs share ───────────────────────
    u11 = Part(name="TLV9061", ref_prefix="U", ref="U11", dest="NETLIST", tool="skidl",
               value="TLV9061IDCKR",
               description="single op-amp, TIA mid-rail reference buffer "
               "(LCSC C398357) -- ⚠ SC-70-5, not the SOT-23-5 the CAD models",
               footprint="Package_TO_SOT_SMD:SOT-23-5",
               pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                     Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                     Pin(num=5, name="V+", func=P)])
    mid_raw = Net("MID_RAW")
    mid += u11[1], u11[4]       # unity-gain follower
    gnd += u11[2]
    mid_raw += u11[3]
    v5 += u11[5]

    # ── U13 / L1: the board's ONLY switcher, at the far end on purpose ───────
    # 24 V arrives at J2, so one switching stage is unavoidable (24->3V3 linearly is
    # 6.2 W and no package here sheds that). It sits at the -Y tail, as far from the
    # photodiode array as this board has room for, with a ~10 mm input path.
    # ⚠ AND ITS SWITCHING FREQUENCY IS A REAL SPEC, not a detail: this board samples
    # at 48 kHz and a switcher near a sub-multiple of that aliases straight into the
    # audio band, where subtraction cannot remove it because it is synchronous.
    sw, v5_pre, fb = Net("SW"), Net("V5_PRE"), Net("FB")
    u13 = Part(name="BUCK_24_5", ref_prefix="U", ref="U13", dest="NETLIST",
               tool="skidl", value="24V->5V sync buck",
               description="24V -> 5V synchronous buck, SOT-23-6, >=0.5 A. OPEN -- "
               "pick one whose fSW is far from 48 kHz and its sub-multiples",
               footprint="Package_TO_SOT_SMD:SOT-23-6",
               pins=[Pin(num=n, func=P) for n in range(1, 7)])
    v24 = Net("+24V")
    v24.drive = Pin.drives.POWER
    boot = Net("BOOT")
    boot += u13[1]
    pgnd += u13[2]
    fb += u13[3]
    Net("BUCK_EN_NC").connect(u13[4])
    v24 += u13[5]
    sw += u13[6]
    l1 = Part(name="L", ref_prefix="L", ref="L1", dest="NETLIST", tool="skidl",
              value="buck L", description="buck output inductor -- SHIELDED is not "
              "optional: an unshielded one radiates into 20 TIAs",
              footprint="Inductor_SMD:L_Bourns-SRN4018",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw += l1[1]
    v5_pre += l1[2]
    fb1 = Part(name="FerriteBead", ref_prefix="FB", ref="FB1", dest="NETLIST",
               tool="skidl", value="600R@100MHz",
               description="5 V rail split: buck side to analog side",
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
    y1 = Part(name="Crystal", ref_prefix="Y", ref="Y1", dest="NETLIST", tool="skidl",
              value="25MHz", description="MCU HSE (LCSC C13740)",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=n, func=P) for n in range(1, 5)])
    osc_in += y1[1]
    osc_out += y1[3]
    gnd += y1[2], y1[4]
    # ⚠ Y2's FREQUENCY FOLLOWS THE PHY, not the MCU. The CAD calls it 24 MHz and the
    # MPN table calls the same part 25 MHz -- one of those is wrong, and which one
    # depends on the USB3343's reference options. Confirm against the datasheet in
    # the same pass that confirms U7's pinout.
    y2 = Part(name="Crystal", ref_prefix="Y", ref="Y2", dest="NETLIST", tool="skidl",
              value="PHY ref", description="ULPI PHY reference crystal -- ⚠ 24 or "
              "25 MHz, confirm against the USB3343 datasheet",
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
    # ESD array's VBUS reference and nowhere else: sensed, not consumed.
    vbus += j1["A4"], j1["B4"], j1["A9"], j1["B9"]
    usb_dp += j1["A6"], j1["B6"]
    usb_dm += j1["A7"], j1["B7"]

    # ── J2: 24 V in, on the instrument's standard 4-way ──────────────────────
    j2 = Part(name="S4B-XH-SM4-TB", ref_prefix="J", ref="J2", dest="NETLIST",
              tool="skidl", value="S4B-XH-SM4-TB",
              description="24 V in -- 24V, PWR_GND, 2 cavities empty",
              footprint="Connector_JST:JST_XH_S4B-XH-SM4-TB_1x04-1MP_P2.50mm_Horizontal",
              pins=[Pin(num=i + 1, name=n, func=P)
                    for i, n in enumerate(("PWR_GND", "+24V", "NC3", "NC4"))])
    pgnd += j2[1]
    v24 += j2[2]
    Net("J2_NC_3").connect(j2[3])
    Net("J2_NC_4").connect(j2[4])

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
    r32 = _r("R32", "5k1", "USB-C CC1 pull-down (upstream-facing port)")
    j1["A5"] += r32[1]
    gnd += r32[2]
    r33 = _r("R33", "5k1", "USB-C CC2 pull-down")
    j1["B5"] += r33[1]
    gnd += r33[2]
    r34 = _r("R34", "mid-rail top", "MID divider, top -- sets the TIA virtual earth")
    r35 = _r("R35", "mid-rail bot", "MID divider, bottom")
    v5 += r34[1]
    mid_raw += r34[2], r35[1]
    gnd += r35[2]
    r36 = _r("R36", "100R", "LED driver gate series")
    led_gate += r36[1]
    r36[2] += q1[1]
    # R37/R38 and C112/C113 are the four parts this netlist ADDED to the CAD -- see the
    # note beside them in src/optical_pickup.py. They are here because turning a part
    # table into nets is what exposed them: a part no net needs looks exactly like a
    # part nobody noticed was missing.
    r37 = _r("R37", "8k06 1%", "PHY RBIAS -- a PRECISION part: it sets the USB "
             "transmitter's drive current, so 1% is the spec, not a preference")
    rbias += r37[1]
    gnd += r37[2]
    r38 = _r("R38", "100k", "LED gate pull-down -- the emitters must be OFF while "
             "the MCU is in reset, not floating at whatever the gate charges to")
    led_gate += r38[1]
    gnd += r38[2]
    r40 = _r("R40", "preset", "buck feedback divider, top")
    r41 = _r("R41", "preset", "buck feedback divider, bottom")
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
    # C120-C122: PHY decoupling. C122 is the 1V8 the PHY regulates for itself, which
    # needs a cap even though nothing else on the board uses that rail.
    for tag, net in (("C120", v3d), ("C121", v3d), ("C122", v1v8)):
        c = _c(tag, "100nF", "PHY decoupling")
        net += c[1]
        gnd += c[2]
    # C123-C126: two load caps per crystal.
    for tag, net in (("C123", osc_in), ("C124", osc_out),
                     ("C125", phy_xi), ("C126", phy_xo)):
        c = _c(tag, "load C0G", "crystal load")
        net += c[1]
        gnd += c[2]
    # C130-C133: the bulk caps and the reference bypass.
    for tag, net, desc in (("C130", vbus, "VBUS bulk"),
                           ("C131", v3d, "3V3 digital bulk"),
                           ("C132", v3a, "3V3 analog bulk"),
                           ("C133", mid, "MID reference bypass -- the twenty summing "
                            "nodes share this, so it is what keeps them from talking "
                            "to each other through their own reference")):
        c = _c(tag, "10uF", desc, "Capacitor_SMD:C_0805_2012Metric")
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
    c163 = _c("C163", "10nF", "buck bootstrap")
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
    "zones": [("GND", "F.Cu", 0.3), ("GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],
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
        {"name": "ULPI", "max_skew_mm": 12.0, "same_layer": False, "max_vias": None,
         "nets": ["ULPI_D0", "ULPI_D1", "ULPI_D2", "ULPI_D3", "ULPI_D4", "ULPI_D5",
                  "ULPI_D6", "ULPI_D7", "ULPI_CK", "ULPI_STP", "ULPI_DIR", "ULPI_NXT"],
         "why": "60 MHz over 34.5 mm = 207 ps of flight; 12 mm of mismatch is 72 ps "
                "against a 16,670 ps bit period. Loose ON PURPOSE -- tightening it "
                "would fail builds for an effect four orders of magnitude below what "
                "matters on this bus."},
        {"name": "USB_HS", "max_skew_mm": 2.5, "same_layer": True, "max_vias": 2,
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
    # ⚠ WHAT THAT LEAVES: the most sensitive geometry on this board is chosen by
    # freerouting and differs between runs. That is a real limitation and it is not
    # visible in any DRC report. If the analog performance ever disappoints, this is
    # the first thing to look at -- and the fix is to give the strip more room so the
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
    with open(os.path.join(OUT_DIR, "optical.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.2f x %.2f mm, %d placements, x%d per instrument"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]),
             BOARD_NOTES["qty_per_instrument"]))
