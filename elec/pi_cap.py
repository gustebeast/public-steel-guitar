"""Pi cap -- the Raspberry Pi's connector board, x1.

    py -3.12 elec/pi_cap.py             # -> elec/out/pi_cap.{net,board.json}

WHY IT EXISTS (user, 2026-09-22). The BOM has committed for a long time to feeding the Pi
through its GPIO HEADER rather than its USB-C port (that port is the front panel's gadget
port, and on a Pi 4B the USB-C VBUS pin and the GPIO 5 V pins are the same node). But the
GPIO header is 2.54 mm MALE PINS, and nothing in the instrument bridged a crimped JST cable
to them. That left the single least-defined joint in the build: either somebody solders
wires to a header, or the 5 V arrives on friction-fit crimp housings pushed onto pins in a
box full of stepper vibration. The LED strip made it worse rather than causing it, by adding
a clocked SPI pair to the same crossing.

So: one small board with a 2x20 socket that plugs onto the header, and JST connectors for
everything else. The solder is all ON A PCB, which is the standing rule; the harness stays
crimped end to end.

WHAT CROSSES HERE
  * Pi 5 V IN, from motor_ctrl J5 -- GPIO pins 2/4 (5 V) and 6/9 (GND). Up to 3 A.
  * LED 24 V, passing through to both lighting drops (docs/lighting-bus.md, 2026-09-30).
    It arrives on J4 from the motor board's fused J7 and leaves on J3 (fret boards, 0.89 A
    over two contacts) and J6 (foot strip, 0.73 A over one). Every lit board makes its own
    rail from it, so nothing here is regulated for the LEDs and the rail meets the Pi's
    5 V nowhere but GND.
    HISTORY: until that date J4 carried a 5 V LED rail made by a second buck (U6) on the
    motor board, for one strip at 2.2 A. The strip is gone and so is the reason for U6.
  * LED SPI OUT, two chains on two controllers: SPI0 -- SCLK (GPIO 11, pin 23) and MOSI
    (GPIO 10, pin 19) -- to the fret boards on J3; SPI5 -- SCLK (GPIO 15, pin 10) and MOSI
    (GPIO 14, pin 8) -- to the foot strip on J6. See PI_SCLK_FOOT for why not one clock.

⚠ THE SPI PAIR IS THE ONE DELIBERATE AERIAL IN THE INSTRUMENT, and it runs past a MAGNETIC
pickup. Four things are done about it here, cheapest first, because a clocked edge on a
300-600 mm unshielded cable is exactly what an inductive sensor is built to hear:

  ⚠ FIRST, TWO CLOCKS THAT ARE NOT THE SAME CLOCK, because conflating them gets the
  advice backwards. The STRIP was chosen for a high PWM rate -- the frequency its driver
  switches LED current at, which has to sit above the audio band or the pickup simply hears
  it (SK6812 at 1.2 kHz and SK9822 at 4.7 kHz were rejected for this; the TLC59711's
  enhanced-spectrum PWM spreads each period over 128 segments at ~19.5 kHz). Nothing below
  changes that. What follows is about the SPI DATA clock on the cable, a different wire
  carrying a different signal.

  1. SERIES SOURCE TERMINATION, R1/R2 at the driver. THIS IS THE REAL FIX. What radiates is
     the EDGE RATE, not the clock frequency: a 1 MHz clock with 2 ns edges emits the same
     harmonics as a 10 MHz clock with 2 ns edges, just fewer per second. The Pi's GPIO
     output impedance is ~30-50 ohm against a loose pair's ~100-120, so a bare edge also
     reflects and rings. 68 ohm in series damps the ringing AND slopes the edge, which is
     what actually removes the high-frequency content. At the SOURCE on purpose -- a
     resistor at the far end does not stop the launch.
  2. STREAM CONTINUOUSLY; DO NOT BURST. ⚠ THIS REPLACES AN EARLIER "cap the clock at
     1 MHz" NOTE, WHICH WAS WRONG, and wrong in the direction that matters. The audio-band
     threat is not the clock frequency -- it is the ENVELOPE. A TLC59711 packet is 224 bits
     and the strip is twelve of them = 2688 bits per frame; at 1 MHz that frame takes
     2.69 ms, so refreshing at 200 Hz gives 2.69 ms of activity and 2.3 ms of silence,
     repeating 200 times a second. That envelope sits squarely in the audio band, and
     anything that rectifies it turns it into a 200 Hz buzz. Slowing the clock makes the
     burst LONGER, not smaller. So: pick a clock with enough headroom to write frames
     BACK TO BACK and keep writing, so the line carries a steady inaudible carrier with no
     audio-band modulation. The chip latches per packet, so continuous writes are fine.
     ⚠ FIRMWARE: continuous streaming, not a timed refresh. Rate is then free to choose.
  3. A GROUND RETURN BESIDE EACH SIGNAL. J3's order puts GND on both ends of the six ways
     (GND V24 V24 GND SCK SDT matches fret_led's own J1), so the pair has a return
     conductor in the same cable instead of finding its way home through the chassis. Loop
     AREA is what couples to a coil, not wire length.
  4. DISTANCE, which is the harness's job, not this board's: the run should reach the strip
     along the +Y rail, not across the deck past the pickup. See INSTALL_NOTES.md.

  ⚠ NONE OF THIS TOUCHES THE ONE KNOWN AUDIO-BAND TERM. At grey levels under 128/65535
  the TLC59711's own PWM energy lands at sub-audio multiples of its 152 Hz full cycle (see
  elec/led_strip.py). That is inside the driver, on the strip, not on this cable -- bench it
  beside the pickup before committing, because no cable discipline can reach it.

  If a bench test beside the pickup still shows the strip in the audio, the escalation is a
  differential pair (RS-422 driver here, receiver at the strip) -- NOT more filtering. That
  costs two parts and a board change, so it is worth measuring before it is worth building.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import json  # noqa: E402

from skidl import ERC, Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

import netcheck  # noqa: E402

P = Pin.types.PASSIVE

# ⚠ 34, NOT 26: THE UI RIBBON NEEDED A BAND AND THIS IS THE ONLY DIRECTION IT COULD COME
# FROM. The board's +Y is world +Z (see electronics._cap_place: rotate -90 then stand), so
# the +Y edge is the Pi's own top edge with 0.3 mm to spare -- it cannot move. The -Y edge
# grows instead, DOWN over the Pi, where the only thing under the cap is the SoC block:
# 2.5 mm tall against the socket's 8.5 mm standoff, so 6.0 mm of air. Every placement below
# moved +4.0 in y with it so nothing shifted relative to the socket, and
# electronics._cap_place's j1_y moved with them.
BOARD_W, BOARD_L = 56.0, 34.0

# ⚠ THE UI RIBBON IS A PLAIN HEADER, NOT A SHROUDED ONE, AND THAT IS A SOURCING FACT RATHER
# THAN A PREFERENCE. LCSC stocks no shrouded 1.27 mm 2x7; the nearest shrouded part is
# 2.54 mm and 2x13, and 2.54 is what does not fit the 8.5 mm standoff in the first place
# (a 2.54 male header is 8.54 BEFORE its socket goes over it). So: HX PZ1.27-2x7P ZZ,
# LCSC C22438122, 10535 in stock, the same HX family as the LED connector already here.
# ⚠ WHICH MEANS THE KEYING IS THE CABLE'S LENGTH, and that is a real constraint rather
# than a hope: the run is fixed and short, pin 1 is on the silk, and a cable cut to reach
# only one way cannot be fitted reversed. The alternative was FFC/ZIF, keyed by the
# connector's own shape -- rejected because this instrument gets stomped on and brenner
# flagged mating cycles. Reversing this cable puts 3V3 into a GPIO, so if the assembled
# machine ever shows someone forcing it, that is the escalation.
UI_FP = "Connector_PinHeader_1.27mm:PinHeader_2x07_P1.27mm_Horizontal"

# way -> (signal, Pi header pin). Decided in docs/pi-cap-ui-ribbon.md: the display is on
# SPI1 because SPI0 belongs to the LED strip and a TLC59711 has no chip select, so any
# display byte on that bus becomes strip data. GPIO19 (pin 35) stays EMPTY on purpose --
# the spi1-1cs overlay claims it as MISO and a switch there would work until the overlay
# loads. The order puts the clock beside the ground and keeps the two fast lines away from
# the seven switch lines, which are static on a human timescale.
UI_WAYS = (("GND", 6), ("UI_SCLK", 40), ("UI_SDIN", 38), ("UI_CS_N", 12),
           ("UI_DC", 37), ("UI_RES_N", 33), ("+3V3_PI", 1), ("UI_ENC_A", 29),
           ("UI_ENC_B", 31), ("UI_SW_PUSH", 18), ("UI_SW_A", 11), ("UI_SW_B", 13),
           ("UI_SW_C", 15), ("UI_SW_D", 16))

XH_FP = "Connector_JST:JST_XH_S4B-XH-SM4-TB_1x04-1MP_P2.50mm_Horizontal"
PH6_FP = "Connector_JST:JST_PH_S6B-PH-SM4-TB_1x06-1MP_P2.00mm_Horizontal"
SOCKET_FP = "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical"

# Raspberry Pi 40-way header, PHYSICAL pin numbers -- which is also how the 2x20 footprint
# numbers its pads (1/2 the first pair, odd on one row, even on the other), so the socket's
# pad n IS header pin n and no mapping table is needed.
PI_5V = (2, 4)
# ⚠ PINS 14 AND 20 ARE DELIBERATELY NOT TAKEN, and this is the UI ribbon's doing.
# The header has eight GND pins; this board uses six. Fanning J5's thirteen signals out of
# the socket band put +3V3_PI across the whole band at y -7.23 -- on F.Cu west of x 7.95 and
# on B.Cu east of it, so there is no layer on which anything can cross it -- and pins 14 and
# 20 are north of that fence with the switch lines filling what is left. Measured, not
# assumed: the pour around each is a closed island on BOTH layers (an exact
# SHAPE_POLY_SET.Contains map, not a bounding box), no via site exists that lands in the
# island on one layer and the main pour on the other, and a maze over both layers at 0.10 mm
# finds NO PATH at track widths 0.25, 0.20 and 0.16.
#
# So the choice was six ground pins or re-routing +3V3_PI out of the band on a board that is
# otherwise 0 violations. Six wins on the numbers: the high-current returns are J2/J3/J4's
# own GND ways, not the header, and what the header carries is the Pi's own 3 A shared over
# six pins. Taking two pins the pour cannot reach would leave two isolated copper islands and
# two unconnected items to buy nothing.
PI_GND = (6, 9, 25, 30, 34, 39)
PI_SCLK = 23                      # GPIO 11, SPI0 -- the FRET chain
PI_MOSI = 19                      # GPIO 10
# ⚠ THE FOOT CHAIN GETS ITS OWN CLOCK, AND THAT IS ONE GPIO MORE THAN docs/lighting-bus.md
# ASKED FOR (2026-09-30). The ask was "1 SCK fanned to both headers + 2 SDT". A TLC59711
# has no chip select, so two chains showing different pictures need two DATA lines -- and a
# Pi's hardware SPI has exactly one MOSI per clock. One SCK with two SDT can only be made by
# bit-banging both, at which point the "stream continuously" rule below (note 2) is at the
# mercy of the scheduler. Two controllers cost one more pin and each chain is real SPI.
# SPI5: MOSI GPIO 14 (pin 8), SCLK GPIO 15 (pin 10) -- the UART pins, free here because the
# console is on USB. SPI1 is the display's, SPI4's MOSI is GPIO 6 = UI_ENC_B, and SPI3 is
# the I2C pair with 1.8 k pull-ups on it. dtoverlay=spi5-1cs claims GPIO 12 (pin 32) as its
# CE0 by default; nothing is on pin 32, so it may keep it.
# It also retires that note's open item 3 (three stubs off one clock driver): every clock
# here drives ONE cable through its own series resistor.
# The headers' pin-outs are exactly as asked, so neither LED board changes.
PI_SCLK_FOOT = 10                 # GPIO 15, SPI5
PI_MOSI_FOOT = 8                  # GPIO 14
SERIES_R = "68R"                  # see note 1 in the docstring

# The strip's cable. SAME ORDER as led_strip.J_PINS -- one crimp order, and GND lands on
# both ends of the row so each signal has a return beside it (note 3).
# ⚠ V24, NOT V5 (2026-09-30, docs/lighting-bus.md 3-4): every lit board carries its own buck
# now, so what crosses this board is the 24 V bus and nothing is regulated for the LEDs
# upstream. Same connector, same six ways, same order -- only the rail's name and voltage.
STRIP_PINS = ("GND", "V24", "V24", "GND", "SCK", "SDT")     # = fret_led J1
# the foot strip's inlet, in foot_led.J_PINS order -- V24 on an END pad, as that board needs
FOOT_PINS = ("V24", "GND", "SCK", "SDT")
SH4_FP = "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal"


def _r(tag, value, desc):
    return Part(name="R", ref_prefix="R", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint="Resistor_SMD:R_0402_1005Metric",
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, fp="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _xh(tag, desc, rail="V5"):
    return Part(name="S4B-XH-SM4-TB", ref_prefix="J", ref=tag, tag=tag,
                dest="NETLIST", tool="skidl", value="S4B-XH-SM4-TB",
                description=desc, footprint=XH_FP,
                pins=[Pin(num=i + 1, name=n, func=P)
                      for i, n in enumerate(("GND", rail, rail, "GND"))])


@subcircuit
def pi_cap():
    gnd = Net("GND")
    gnd.drive = Pin.drives.POWER
    v5_pi, v24_led = Net("+5V_PI"), Net("+24V_LED")
    for n in (v5_pi, v24_led):
        n.drive = Pin.drives.POWER

    j1 = Part(name="PinSocket_2x20", ref_prefix="J", ref="J1", tag="J1", dest="NETLIST",
              tool="skidl", value="2.54-2*20P",
              description="Raspberry Pi 40-way GPIO socket (LCSC C5124634)",
              footprint=SOCKET_FP,
              pins=[Pin(num=i + 1, func=P) for i in range(40)])
    for n in PI_5V:
        v5_pi += j1[n]
    for n in PI_GND:
        gnd += j1[n]
    sck_pi, sdi_pi = Net("SCK_PI"), Net("SDI_PI")
    sck_pi += j1[PI_SCLK]
    sdi_pi += j1[PI_MOSI]
    # ⚠ EVERY OTHER HEADER PIN IS DELIBERATELY NOT CONNECTED, and saying so is the point:
    # an unnamed pin and a pin nobody thought about look identical in a netlist. The socket
    # spans all 40 for MECHANICAL reasons -- it is what holds the board on -- not because
    # this board has any business with the other GPIOs.
    # ⚠ AND THE UI RIBBON'S PINS JOIN THE USED SET. Without this every one of them would
    # ALSO get a PI_NC_n net -- two nets on one pad, which ERC reports as a short and which
    # would be a genuine one on the board.
    sck_ft_pi, sdt_ft_pi = Net("SCK_FOOT_PI"), Net("SDT_FOOT_PI")
    sck_ft_pi += j1[PI_SCLK_FOOT]
    sdt_ft_pi += j1[PI_MOSI_FOOT]
    used = (set(PI_5V) | set(PI_GND) | {PI_SCLK, PI_MOSI, PI_SCLK_FOOT, PI_MOSI_FOOT}
            | {h for _s, h in UI_WAYS})
    for n in range(1, 41):
        if n not in used:
            Net("PI_NC_%d" % n).connect(j1[n])

    # ⚠ THE UI BOARD'S RIBBON (brenner's station). 14 ways, 1.27 mm, 2x7, right-angle so
    # the cable leaves IN PLANE inside the socket's own 8.5 mm standoff rather than upward
    # into the endplate -- the same argument that put every other connector on this board
    # on its back face. See UI_WAYS above for the map and why SPI1 rather than SPI0.
    # ⚠ AND THIS IS THE FIRST TIME THIS BOARD TOUCHES +3V3. It carried +5V_PI, +5V_LED, GND
    # and the two SPI0 lines and nothing else, so way 7 is a new net off header pin 1 -- the
    # PI'S OWN 3V3 REGULATOR, good for about 500 mA across everything on it. Under 100 mA
    # for a display module is fine; if the station ever grows a backlight or a second
    # module it needs its own regulator rather than creeping up on the Pi's budget.
    j5 = Part(name="PinHeader_2x07", ref_prefix="J", ref="J5", tag="J5", dest="NETLIST",
              tool="skidl", value="PZ1.27-2x7P",
              description="UI board ribbon, 14-way 1.27 mm 2x7 right-angle (LCSC C22438122)",
              footprint=UI_FP, pins=[Pin(num=i + 1, func=P) for i in range(14)])
    ui_nets = {}
    for _way, (_sig, _hdr) in enumerate(UI_WAYS, start=1):
        if _sig == "GND":
            gnd += j5[_way]
            continue
        n = ui_nets.setdefault(_sig, Net(_sig))
        n += j5[_way], j1[_hdr]

    j2 = _xh("J2", "Pi 5 V in, from motor_ctrl J5 (GPIO pins 2/4 + 6/9)")
    gnd += j2[1], j2[4]
    v5_pi += j2[2], j2[3]

    j4 = _xh("J4", "LED 24 V in, from the motor board's fused J7 -- NOT the Pi's rail",
             rail="V24")
    gnd += j4[1], j4[4]
    v24_led += j4[2], j4[3]

    # the fret drop: power and both signals, in fret_led's J1 order
    j3 = Part(name="S6B-PH-SM4-TB", ref_prefix="J", ref="J3", tag="J3",
              dest="NETLIST", tool="skidl", value="S6B-PH-SM4-TB",
              description="to fret_led_key J1 -- 24 V and SPI0, LCSC C265405",
              footprint=PH6_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(STRIP_PINS)])
    gnd += j3[1], j3[4]
    v24_led += j3[2], j3[3]

    # the foot drop: SM04B-SRSS, the foot board's own inlet part, so the cable is a stock
    # SH-to-SH lead. 0.73 A through its one V24 contact (1 A rated) -- lighting-bus.md 3.
    j6 = Part(name="SM04B-SRSS-TB", ref_prefix="J", ref="J6", tag="J6",
              dest="NETLIST", tool="skidl", value="SM04B-SRSS-TB",
              description="to foot_led J1 -- 24 V and SPI5, LCSC C160404",
              footprint=SH4_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(FOOT_PINS)])
    v24_led += j6[1]
    gnd += j6[2]
    sck_ft, sdt_ft = Net("SCK_FOOT"), Net("SDT_FOOT")
    r3 = _r("R3", SERIES_R, "foot SCLK series source termination")
    sck_ft_pi += r3[1]
    sck_ft += r3[2], j6[3]
    r4 = _r("R4", SERIES_R, "foot MOSI series source termination")
    sdt_ft_pi += r4[1]
    sdt_ft += r4[2], j6[4]

    sck, sdi = Net("SCK"), Net("SDT")
    r1 = _r("R1", SERIES_R, "SCLK series source termination (see docstring note 1)")
    sck_pi += r1[1]
    sck += r1[2], j3[5]
    r2 = _r("R2", SERIES_R, "MOSI series source termination (see docstring note 1)")
    sdi_pi += r2[1]
    sdi += r2[2], j3[6]

    for tag, net, what in (("C1", v5_pi, "Pi 5 V bulk at the header"),
                           ("C2", v24_led, "LED 24 V local bulk -- 50 V part on a 24 V rail; "
                                           "the lit boards carry their own")):
        c = _c(tag, "22uF/16V" if net is v5_pi else "4.7uF/50V", what,
               "Capacitor_SMD:C_0805_2012Metric")
        net += c[1]
        gnd += c[2]
    for tag, net, what in (("C3", v5_pi, "Pi 5 V HF bypass"),
                           ("C4", v24_led, "LED 24 V HF bypass")):
        c = _c(tag, "100nF" if net is v5_pi else "100nF/50V", what)
        net += c[1]
        gnd += c[2]


_BAR_Y = 10.5      # the lighting bus bar, in the strip above the connector lands

BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 2,
    "thickness_mm": 1.6,
    "placements": {
        # The socket is the board's spine: 50.8 mm of pads down the middle, and what holds
        # the assembly on the Pi. Everything else lives in the strip above it.
        # ⚠ ROT 90: PinSocket_2x20_Vertical runs along Y in its own frame, so unrotated it
        # stood 51.9 mm tall on a 26 mm board and hung off both edges. "Vertical" in the
        # footprint name is the MATING direction (pins up), not the row's direction.
        # ⚠ EVERY y HERE MOVED +4.00 WHEN THE BOARD GREW, so nothing moved relative to the
        # socket or to anything else -- the board gained 8 mm on its -Y edge and the parts
        # kept their distances. electronics._cap_place's j1_y moved with them, because that
        # is the number the whole board is positioned by.
        "J1": (0.00, -4.50, 90.0),   # 4.5 from the board edge = the Pi header's own margin
        # ⚠ RE-TILED FOR THE SIDE-ENTRY BODIES. They are 16.8 x 12.1 (XH) and 17.3 x 10.3
        # (PH) against the 12.4 x 5.75 of the vertical parts they replace, so the three
        # together take 50.9 of the board's 56: ~1 mm of margin at each edge, 1.05 between
        # them. Their courtyards sit 6.05 ABOVE the placement point, which is why y is 5.4
        # and not 8 -- at 8 they overhung the +Y edge by 2 mm.
        "J2": (-18.60, 9.40, 0.0),      # Pi 5 V in
        "J4": (-0.75, 9.40, 0.0),       # LED 24 V in
        "J3": (17.35, 9.40, 0.0),       # out to the fret boards
        # the foot drop goes in the ribbon's band, mouth -Y like the ribbon, at the +X end
        "J6": (20.00, -11.00, 180.0),
        "R3": (12.50, -9.00, 0.0),
        "R4": (12.50, -11.00, 0.0),
        # the passives drop into the band between J1's socket and the connector row
        "C1": (-20.00, 1.00, 0.0),
        "C3": (-15.00, 1.00, 0.0),
        "C2": (-6.00, 1.00, 0.0),
        "C4": (-1.00, 1.00, 0.0),
        "R1": (5.00, 1.00, 0.0),
        "R2": (8.00, 1.00, 0.0),
        # ⚠ THE UI RIBBON SITS IN THE NEW BAND AND FACES AWAY FROM THE POWER CABLES. The
        # band is y -17..-7, clear of the socket's pad rows at -5.8..-3.2; the part is
        # ~7.6 x 1.3 of pads with its body 3.07 beyond them. ROT 270 turns the body -Y, so
        # the ribbon leaves on the opposite edge from J2/J3/J4 -- which carry up to 3 A to
        # the Pi and 1.6 A at 24 V to the lights, and this one carries a display clock.
        "J5": (-3.80, -11.00, 270.0),
    },
    # ⚠ THE SOCKET'S GROUND PADS TAKE NO STITCHING VIA, AND DO NOT NEED ONE. The check
    # exists because an SMD pad touching only a pour can be orphaned when routing carves
    # the pour up. These are PLATED THROUGH-HOLE pads: the barrel already spans F.Cu and
    # B.Cu, so each one IS its own via and reaches both pours by construction. There is no
    # room beside them either -- 2.54 mm pitch leaves ~0.8 mm between pads, under a 0.6 mm
    # via plus clearance -- so the check can only ever fail here.
    "stitch_exceptions": tuple("J1.%d" % n for n in (6, 9, 14, 20, 25, 30, 34, 39)),
    # GND pour on both layers: this board carries up to 3 A to the Pi and 1.6 A to the
    # strip, and the return for both shares it.
    "zones": [("GND", "F.Cu", 0.3), ("GND", "B.Cu", 0.3)],
    "stitch_nets": ("GND",),
    # ⚠ THE LIGHTING BUS IS NOT A SIGNAL. Every net here was the 0.25 mm default (0.88 A at a
    # 10 C rise by IPC-2221) and this one carries 0.89 A to J3 and 0.73 A to J6.
    # 0.3 mm (~1.0 A) IS WHAT ROUTES, NOT WHAT WAS WANTED: 0.5, 0.4 and 0.35 each left one
    # GND island -- the wider rail cuts the pour in the band the UI ribbon already fans
    # across. The deliberate wide strip that sentence used to ask for is "tracks" below; this
    # width now only governs what the router still lays (the two caps' stubs).
    "net_widths": {"+24V_LED": 0.3},
    # ⚠ AND THE FRET BRANCH IS LAID BY HAND, BECAUSE THE NETCLASS COULD NOT GIVE IT MARGIN.
    # J4 -> J3 is the stretch that carries everything (1.63 A in, 0.89 A on to the fret
    # boards), and at 0.3 mm it was on a ~1.0 A track. It is one straight run in the strip
    # ABOVE the connector lands, where nothing else goes: a 1.0 mm bar (~2.4 A) at y 10.5,
    # 0.29 off J3's lands and 0.98 off the mounting pads, dropping into J4 way 3 and J3 way 2,
    # with each connector's two 24 V ways tied across their lands. The router keeps the rest
    # of the net -- the caps and the 0.73 A foot branch -- at 0.3 mm.
    "tracks": [("+24V_LED", "B.Cu", 1.0, [(0.50, 7.13), (0.50, _BAR_Y), (14.35, _BAR_Y)]),
               ("+24V_LED", "B.Cu", 0.8, [(14.35, _BAR_Y), (14.35, 7.96)]),
               ("+24V_LED", "B.Cu", 0.8, [(14.35, 7.96), (16.35, 7.96)]),
               ("+24V_LED", "B.Cu", 1.0, [(-2.00, 7.13), (0.50, 7.13)]),
               # the foot branch, on the path the router found when the net was all its own
               # (with the bar declared it left J6 way 1 open): 0.73 A at 0.4 mm
               ("+24V_LED", "B.Cu", 0.4, [(14.35, 7.96), (14.35, 7.01), (20.25, 1.11),
                                          (20.25, -6.96), (21.50, -8.21), (21.50, -9.71)])],
    # ⚠ TWO GND STITCHES IN THE RIBBON'S BAND. Growing the board and fanning 13 UI signals
    # across it cut the GND pour into the main body plus small fragments, and the fragments
    # are the band's own return path -- each one is what a switch line runs over. They are
    # each anchored on a socket pad, but one pair came back as a ratline between the F.Cu and
    # B.Cu pours, which is the pour's way of saying the anchoring is a hairline rather than a
    # connection. These two vias tie the band to both planes outright.
    # Sites searched against the routed board (clearance headroom 1.213 and 1.188 mm over the
    # rule), not chosen -- the same method the optical board's bring-up pads used.
    # ⚠ AND THE LAST TWO ARE THE ONES THAT MATTER, because the first two fixed the wrong
    # thing. Every GND pad on this board is either a socket pin -- all eight of them in the
    # band, at y -4.5 -- or an SMD pad on J2/J3/J4, which touch B.Cu ONLY because every
    # connector is on the back. So once the ribbon's fan cut the band into fragments, those
    # eight pins anchored the FRAGMENTS and the F.Cu MAIN POUR was left with no anchor of its
    # own: one ratline, F.Cu zone to B.Cu zone, and stitching the fragments did nothing for
    # it. These two sit in the new band's bottom strip, below J5's body (which reaches
    # y -14.07), where both layers carry the main pour.
    # ⚠ A FIFTH VIA WAS TRIED AT (1.30, -6.00) AND IT WAS BOTH WRONG AND DESTRUCTIVE.
    # It was meant to anchor the 5.3 mm2 B.Cu sliver at x 0.64..1.95 -- which turned out to
    # be anchored already, by J1.20 at (1.27, -5.77), a GND pad my own spot-search skipped
    # because it filters SAME-NET pads and a via must not sit on one. So the via landed
    # 0.23 mm inside that pad, drop_redundant_pth_vias correctly removed it as redundant,
    # and that SECOND removal in one pass is what tipped pcbnew's SWIG container over:
    # GetFootprints() started handing back bare proxies and link_close_gaps died on
    # fp.Pads(). One removal had never shown it.
    # TWO LESSONS, BOTH ABOUT MY OWN TOOLS: a via site must clear its OWN net's pads too,
    # not just foreign ones; and the sliver diagnosis was wrong twice because a bounding-box
    # point-in-polygon with 0.3 mm of slack was asked a question it cannot answer.
    # ⚠ THE LAST ONE IS THE BRIDGE, AND IT IS THE ONLY ONE THAT WAS EVER REQUIRED. Fanning
    # 13 UI signals across the band splits the GND pour into two CLUSTERS, not merely into
    # islands, and every island in each cluster is anchored -- which is why four rounds of
    # "find the island with no anchor" all failed. Mapping each through-hole item to its
    # island index on BOTH layers settles it in one pass:
    #     MAIN     F4,B3 + F3,F2   (J1.6, J1.9, J1.14, J1.25, J1.39 and most vias)
    #     ISLAND A F1,F0 + B0,B1,B2 (J1.20, J1.30, J1.34, J5.1)
    # Nothing joined them: every through item lands inside ONE cluster on both layers. The
    # bridge has to be a point that is in cluster A on one layer and MAIN on the other, and
    # (-16.62, -10.91) is exactly that -- F island 0, over the B main pour, 3.739 mm of
    # clearance headroom. One via, not a fifth guess.
    "vias": [("GND", -21.50, -11.00), ("GND", -11.75, -7.00),
             ("GND", -20.00, -15.50), ("GND", 14.00, -15.50),
             ("GND", -16.62, -10.91),
             # ⚠ AND ONE ON THE EAST SIDE, FOR THE SAME REASON AS THE BRIDGE ABOVE (2026-09-30).
             # The foot drop's fan (R3/R4 -> J6) and its declared 24 V branch down x 20.25 cut
             # a second cluster off east of the socket: B island x 6.5..19.6, y -5.1..3.0 and
             # F island x 6.7..21.0, y -5.1..-1.2, anchored on each other and on nothing else.
             # Five bar/branch variants all left it open, which is what a missing bridge looks
             # like -- not router luck. This point is in the B cluster and the F main pour.
             ("GND", 12.50, 1.20)],
    "router_passes": 12,
    # ⚠ THE SOCKET IS ON THE BACK, and that is the whole mechanical idea: its body is the
    # standoff the cap hangs off the Pi's header by. Mounted on the front it would be a
    # bump on top of the board with nothing holding the board on.
    # ⚠ EVERY CONNECTOR IS ON THE BACK TOO, AND THAT IS A HEIGHT FIX, NOT A STYLE CHOICE
    # (2026-09-22). dimensions.ELEC_STACK_D reserves 14.0 mm above the Pi's PCB and the
    # MOTOR BANK is packed against that number, so it cannot grow to suit this board. With
    # vertical connectors the cap needed 8.5 (socket) + 1.6 (board) + 7.0 (XH) = 17.1 and
    # drove 260 mm3 into the endplate -- measured by sweeping it, not by looking at it.
    # Side entry on TOP still needs 15.85. Underneath, the cap's top face is bare PCB at
    # 10.1 and the connectors live in the socket's own 8.5 mm gap (PH 5.5, XH 5.75), with
    # their cables leaving sideways instead of upward into the endplate.
    # ⚠ EVERY PART IS ON THE BACK NOW, AND THAT IS AN ASSEMBLY-COST FIX (user, 2026-09-28:
    # "I hope you aren't making a two sided board, that increases the cost"). Two LAYERS of
    # copper is standard and cheap; what costs is parts on BOTH FACES, because the fab runs
    # a second placement setup. This board had six 0402s on the front and five connectors on
    # the back -- the only board in the fleet populated on both sides, and it had been that
    # way since the connectors moved to the back on 2026-09-22 for the height reason below.
    # The connectors CANNOT move: the 2x20 socket's body is the standoff the cap hangs off
    # the Pi's header by. The passives can, and they are 0.5 mm tall against a 8.5 mm gap,
    # so they go where the connectors already are and the front face becomes bare laminate.
    "back_refs": ("J1", "J2", "J3", "J4", "J5", "J6",
                  "C1", "C2", "C3", "C4", "R1", "R2", "R3", "R4"),
    # ⚠ AND THIS FLAG IS DOCUMENTATION -- nothing reads it (checked across the tree), so it
    # never made the board one-sided and never will. It says what the layout is FOR; the
    # thing that decides the invoice is back_refs above.
    "single_sided": True,           # all eleven parts on one face, connectors and passives
    "qty_per_instrument": 1,
}


# ── THE PI'S 5 V, DECLARED (2026-10-01) ──────────────────────────────────────────────────
# J2 (from motor_ctrl's J5) -> J1 pins 2 and 4 is the Pi's ENTIRE supply, up to ~3 A, and
# the router laid it as 67 mm of 0.25 mm (0.88 A at a 10 C rise) through ONE 0.3 mm via.
# Same fault, same day, as motor_ctrl's side of this cable. It is now one F.Cu lane:
# two 0.4 mm vias in each of J2's two 5 V lands (J2 is on the back), 2 mm (3.95 A) across
# the board between the cap row's stitch vias and the header, round the east end of the
# header outside pin 1, and into pins 2 and 4. The return is the two GND pours.
# The caps' stubs stay the router's.
BOARD_NOTES["vias"] = list(BOARD_NOTES.get("vias", [])) + [
    ("+5V_PI", x, y, 0.4, 0.8) for x in (-19.85, -17.35) for y in (6.0, 8.2)]
BOARD_NOTES["tracks"] = list(BOARD_NOTES.get("tracks", [])) + [
    ("+5V_PI", "F.Cu", 1.2, [(-19.85, 8.2), (-19.85, 6.0), (-17.35, 6.0), (-17.35, 8.2)]),
    ("+5V_PI", "F.Cu", 2.0, [(-18.6, 6.0), (-18.6, 2.5), (1.5, 2.5), (4.4, -0.4),
                             (25.3, -0.4)]),
    ("+5V_PI", "F.Cu", 1.6, [(25.3, -0.4), (26.1, -1.2), (26.1, -5.77), (24.13, -5.77)]),
    ("+5V_PI", "F.Cu", 1.2, [(24.13, -5.77), (21.59, -5.77)]),
]

# ⚠ AND THE HEADER'S WEST HALF NEEDS ITS OWN GROUND BRIDGE. The F.Cu pour cannot pass
# between J1's pads (0.84 mm gaps, less two clearances), so the ground south of the header
# reaches the rest only where the router happens to leave B.Cu open -- and with the lane in
# it did not: UI_SW_PUSH ran a U round the whole west cluster (three B fragments, two F,
# J1.30 and J1.34 in them) and no via site joins it to the main pour on either face
# (searched: 0 sites). So the link is DRAWN, before routing, where no route has used
# F.Cu: from J1.30 up through the gap between pins 29 and 31 into the strip the lane leaves
# north of the header. 0.25 mm in a 0.84 mm gap, 0.295 a side.
BOARD_NOTES["tracks"] += [("GND", "F.Cu", 0.25, [(-11.43, -5.77), (-12.70, -4.50),
                                                (-12.70, -1.20)])]


if __name__ == "__main__":
    pi_cap(tag="picap")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "pi_cap.net"))
    netcheck.grounds_meet(os.path.join(OUT_DIR, "pi_cap.net"))
    with open(os.path.join(OUT_DIR, "pi_cap.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    # ⚠ THE UI WAYS COUNT TOO. This line kept its own copy of the used-pin set and did not
    # learn about the ribbon, so it said 12 while the board was holding 25 of the header's
    # pins. A summary that is computed separately from the thing it summarises drifts the
    # first time the design changes -- so it reads the same UI_WAYS the netlist does.
    _used = (set(PI_5V) | set(PI_GND) | {PI_SCLK, PI_MOSI, PI_SCLK_FOOT, PI_MOSI_FOOT}
             | {h for _s, h in UI_WAYS})
    print("board %.1f x %.1f mm, %d of the header's 40 pins used (%d of them the UI ribbon's), "
          "SPI streams continuously (see docstring)"
          % (BOARD_W, BOARD_L, len(_used), len({h for _s, h in UI_WAYS})))
