"""LED light strip SECTION -- 9 RGBW LEDs on 3 TLC59711s, daisy-chained, x4.

    py -3.12 elec/led_strip.py          # -> elec/out/led_strip.{net,board.json}

WHY A CUSTOM STRIP (user, 2026-09-22). The lighting brief ranks QUALITY first: a real white
channel, deep bit depth for smooth low-brightness fades, and PWM well above the audio band
because the strip sits in the body beside a MAGNETIC pickup. No buyable strip does all three:
every addressable RGBW chip with a strip on sale PWMs at 1-4 kHz (SK6812 RGBW 1.2 kHz,
UCS8904B and SM16825E 4 kHz -- datasheets), and the one chip that does all three, HD108
RGBW, is sold quote-only. So the strip is built from stocked parts:
  * TLC59711 (TI, LCSC C116842): 12 constant-current channels, 16-bit PWM, clocked two-wire
    input with re-buffered SCKO/SDTO for chaining, input high 0.7 x VREG = 2.31 V, so the
    Pi's 3.3 V SPI drives it with no level shifter. Its PWM is "enhanced spectrum": each
    period is spread over 128 segments of ~19.5 kHz. ⚠ At grey levels under 128/65535 the
    energy lands at sub-audio multiples of the 152 Hz full cycle -- tiny current, but it is
    the one audio-band term; bench it against the pickup before committing.
  * XINGLIGHT XL-5050RGBW (LCSC C7371891): R/G/B/W dice with SEPARATE anodes (1-4) and
    cathodes (5-8), so each die sinks into its own channel. One TLC59711 = 3 RGBW LEDs.
WHY SECTIONS. Four identical 145 mm boards make the 580 mm run (BOM.md), each small enough to
share the panel with the tee and sensor boards (user). A crimped PH jumper joins them; the
data and clock pass through every chip, so the chain is one SPI stream from the Pi.
⚠ OPEN (user): where the strip's 5 V comes from. Up to 2.2 A at full white (4 x 9 LEDs x
4 x 15 mA), capped in the effects daemon. It must NOT share the Pi's 3 A rail at full load
or the analog 5 V; see BOM.md's power budget, which carries it as its own buck.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

from skidl import ERC, Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

import netcheck                                     # noqa: E402

P = Pin.types.PASSIVE

BOARD_W, BOARD_L = 145.0, 20.0          # X along the strip, Y = the strip's height (20: the
                                        # PH tabs need 1.0 to the long edges)
SECTIONS = 4                            # 580 mm / 145
LED_PITCH = 14.5                        # 9 LEDs over 116 mm: ~62 per metre (the end LEDs
                                        # clear the connectors' courtyards by 0.9)
N_LED, N_DRV = 9, 3
# IREF sets every output's ceiling: I = 41 x 1.21 V / R (TLC59711 datasheet). 3k3 = 15.0 mA,
# three quarters of the LED's 20 mA rating -- headroom, and 2.2 A for the whole strip.
R_IREF = "3k3"

LED_FP = "Steel:XINGLIGHT_XL-5050RGBW"
DRV_FP = "Package_SO:HTSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3.4x6.5mm_Mask2.75x3.43mm"
J_FP = "Connector_JST:JST_PH_S6B-PH-SM4-TB_1x06-1MP_P2.00mm_Horizontal"
# PH, 6 way: 5 V and GND on TWO contacts each -- section 1's input carries all four sections
# (2.2 A at full white against PH's 2 A per contact). Same order in and out.
J_PINS = ("GND", "V5", "V5", "GND", "SCK", "SDI")
# TLC59711 (PWP) pins, datasheet Terminal Functions: 1 IREF 2 GND 3 R0 4 G0 5 B0 6 R1 7 G1
# 8 B1 9 SDTI 10 SCKI 11 SCKO 12 SDTO 13 R2 14 G2 15 B2 16 R3 17 G3 18 B3 19 VCC 20 VREG,
# thermal pad = GND (KiCad numbers it 21).
# ⚠ OUTPUTS ARE MAPPED BY GEOMETRY, NOT BY THE DATASHEET'S GROUPS (2026-09-22). The driver
# sits under the middle LED with its pin columns facing -X (pins 1-10, top to bottom) and +X
# (pins 20-11, top to bottom); every LED's cathodes are its +X pad column, R/G/B/W top to
# bottom. Mapped in datasheet order, cathodes crossed the chip and 8 would not route:
#   left LED    R0 G0 B0 R1   (pins 3 4 5 6   -- top of the -X column)
#   middle LED  B3 G3 R3 B2   (pins 18 17 16 15 -- top of the +X column, right under it)
#   right LED   G2 R2 B1 G1   (pins 14 13 8 7 -- the rest)
# FIRMWARE MUST USE THIS TABLE. The chip's global brightness correction is per colour GROUP
# (R, G, B) and this mapping mixes groups within an LED, so set all three BC fields equal.
DRV_LED_OUTS = (((3, 4, 5), 6), ((18, 17, 16), 15), ((14, 13, 8), 7))


def _r(tag, value, desc):
    return Part(name="R", ref_prefix="R", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint="Resistor_SMD:R_0402_1005Metric",
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, fp="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


@subcircuit
def led_strip():
    gnd, v5 = Net("GND"), Net("+5V")
    for n in (gnd, v5):
        n.drive = Pin.drives.POWER
    j = {}
    for tag, what in (("J1", "strip in (from the Pi / previous section)"),
                      ("J2", "strip out (to the next section)")):
        j[tag] = Part(name="S6B-PH-SM4-TB", ref_prefix="J", ref=tag, tag=tag, dest="NETLIST",
                      tool="skidl", value="S6B-PH-SM4-TB",
                      description="%s, LCSC C265405" % what, footprint=J_FP,
                      pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(J_PINS)])
        gnd += j[tag][1], j[tag][4]
        v5 += j[tag][2], j[tag][3]
    sck, sdi = Net("SCK_IN"), Net("SDI_IN")
    sck += j["J1"][5]
    sdi += j["J1"][6]
    bulk = _c("C1", "10uF", "section bulk at the input", "Capacitor_SMD:C_0805_2012Metric")
    v5 += bulk[1]
    gnd += bulk[2]
    for k in range(N_DRV):
        u = Part(name="TLC59711", ref_prefix="U", ref="U%d" % (k + 1), dest="NETLIST",
                 tool="skidl", value="TLC59711PWPR",
                 description="12-ch 16-bit constant-current LED driver (LCSC C116842)",
                 footprint=DRV_FP, pins=[Pin(num=n, func=P) for n in range(1, 22)])
        iref = Net("IREF%d" % (k + 1))
        u[1] += iref
        gnd += u[2], u[21]
        v5 += u[19]
        vreg = Net("VREG%d" % (k + 1))
        vreg += u[20]
        sdi += u[9]
        sck += u[10]
        if k < N_DRV - 1:
            sck, sdi = Net("SCK_%d" % (k + 1)), Net("SDI_%d" % (k + 1))
        else:
            sck, sdi = Net("SCK_OUT"), Net("SDI_OUT")
        sck += u[11]
        sdi += u[12]
        r = _r("R%d" % (k + 1), R_IREF, "U%d IREF -- 15.0 mA per channel" % (k + 1))
        iref += r[1]
        gnd += r[2]
        cv = _c("C%d" % (10 + k), "1uF", "U%d VREG (datasheet: 1 uF required)" % (k + 1))
        vreg += cv[1]
        gnd += cv[2]
        cc = _c("C%d" % (20 + k), "100nF", "U%d VCC bypass" % (k + 1))
        v5 += cc[1]
        gnd += cc[2]
        for m, (rgb, w) in enumerate(DRV_LED_OUTS):
            n = 3 * k + m + 1
            d = Part(name="LED_RGBW", ref_prefix="D", ref="D%d" % n, dest="NETLIST",
                     tool="skidl", value="XL-5050RGBW",
                     description="RGBW LED %d (LCSC C7371891)" % n, footprint=LED_FP,
                     pins=[Pin(num=i, func=P) for i in range(1, 9)])
            v5 += d[1], d[2], d[3], d[4]                   # R, G, B, W anodes
            for die, out in zip((5, 6, 7), rgb):           # R, G, B cathodes
                Net("D%d_K%d" % (n, die)).connect(d[die], u[out])
            Net("D%d_KW" % n).connect(d[8], u[w])          # W cathode
    j["J2"][5] += sck
    j["J2"][6] += sdi


# ── the board ────────────────────────────────────────────────────────────────
# Board-local mm, origin at the centre; +X runs along the strip, +Y up the rail wall.
# Connectors: the side-entry PH's mouth is its footprint's +Y (4.4 from its origin) and its
# placement anchors on the PAD CENTROID (1.4125 behind the origin); rot 270 turns the mouth
# -X (J1), rot 90 turns it +X (J2), each mouth 1.0 inside its board end -- the metal tabs sit
# 1.2 behind the mouth face and reached the edge at 0.2 (copper-to-edge violations).
# TWO ROWS: LEDs along the top half, each driver directly UNDER the middle LED of its three
# so every cathode drops straight down; the driver's three passives stack beside it. Inline
# between the LEDs, the far LED's cathodes had to pass under its neighbour's pads and 9 of
# the 14 first-route opens were exactly that.
_MOUTH = BOARD_W / 2 - 1.0
_LED_Y, _DRV_Y = 4.5, -4.6
# the centroid sits on the INBOARD side of the origin (mouth + 4.4 + 1.4125 in from the
# end); the first two layouts had the sign wrong and hung both connectors ~1.8 mm off the ends
_J_ANCHOR = _MOUTH - 4.4 - 1.4125
_LED_X = [(-(N_LED - 1) / 2 + i) * LED_PITCH for i in range(N_LED)]
_place = {"J1": (-_J_ANCHOR, 0.0, 270.0), "J2": (_J_ANCHOR, 0.0, 90.0),
          "C1": (_LED_X[0], _DRV_Y, 0.0)}
for i, x in enumerate(_LED_X):
    _place["D%d" % (i + 1)] = (x, _LED_Y, 0.0)
for k in range(N_DRV):
    xm = _LED_X[3 * k + 1]
    # UNROTATED: the pin columns face -X and +X, i.e. up and across to the LEDs either side
    # (turned 90, one row faced the board edge and its cathodes had no way round)
    _place["U%d" % (k + 1)] = (xm, _DRV_Y, 0.0)
    # the passives go UP in the LED row, in the gap left of the middle LED: beside the driver
    # they stood between the left LED's cathodes and the driver's -X pins, squarely in the
    # path (those two nets failed in every layout that had them there)
    for ref, dy in (("R%d" % (k + 1), 1.6), ("C%d" % (10 + k), 0.0), ("C%d" % (20 + k), -1.6)):
        _place[ref] = (xm - LED_PITCH / 2, _LED_Y + dy, 0.0)

BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 2,
    "thickness_mm": 1.6,
    "placements": _place,
    # GND pours on F.Cu ONLY. B.Cu is where the router takes the cathode runs -- 36 of them
    # across a 145 mm board -- so a pour there comes back as fragments, and joining those
    # fragments to the F.Cu pour was the last open net through three layouts. F.Cu carries
    # the pour (every GND pad is on it), B.Cu carries routing, and GND crosses between them
    # on the router's own vias like any other net.
    "zones": [("GND", "F.Cu", 0.3)],
    # GND stitching in every LED-row gap the passives do not occupy: a pour ties to a via by
    # the fill itself, so these join the two layers' ground wherever the routing has cut the
    # F.Cu pour into pieces (the last open net on the first clean layout was exactly that).
    # (No stitching vias: with one pour there is nothing to stitch TO. Laid before routing
    # they were deleted as dangling; laid after, they landed on the router's own tracks.)
    # ...and each driver's passive cluster: the three parts' GND pads (pad 2, one column) are
    # joined by one track and hopped to the via beside them. Stacked 1.6 apart with traces
    # round them, the pour cannot get in and their stitch stubs were left dangling.
    "tracks": [trk for k in range(N_DRV) for trk in (
        ("GND", "F.Cu", 0.25, [(_LED_X[3 * k + 1] - LED_PITCH / 2 + 0.48, _LED_Y + 1.6),
                               (_LED_X[3 * k + 1] - LED_PITCH / 2 + 0.48, _LED_Y - 1.6)]),
        ("GND", "F.Cu", 0.25, [(_LED_X[3 * k + 1] - LED_PITCH / 2 + 0.48, _LED_Y),
                               (_LED_X[3 * k + 1] - LED_PITCH / 2 + 2.2, _LED_Y)]))],
    "stitch_nets": ("GND",),
    "single_sided": True,
    "no_mounting_holes": True,       # the rail's channel holds it (src/chassis.py)
    "qty_per_instrument": SECTIONS,
    "router_passes": 30,
}


if __name__ == "__main__":
    led_strip(tag="led")
    ERC()
    net = os.path.join(OUT_DIR, "led_strip.net")
    generate_netlist(file_=net)
    netcheck.grounds_meet(net)
    netcheck.no_orphan_pins(net)
    with open(os.path.join(OUT_DIR, "led_strip.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("section %.0f x %.0f mm, %d LEDs on %d drivers, x%d per instrument"
          % (BOARD_W, BOARD_L, N_LED, N_DRV, SECTIONS))
