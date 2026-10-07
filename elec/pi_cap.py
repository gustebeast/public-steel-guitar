"""Pi cap -- the Raspberry Pi's connector board, x1.

    py -3.12 elec/pi_cap.py             # -> elec/out/pi_cap.{net,board.json}

WHY IT EXISTS (user, 2026-09-22). The BOM has committed for a long time to feeding the Pi
through its GPIO HEADER rather than its USB-C port (that port is the front panel's gadget
port, and on a Pi 4B the USB-C VBUS pin and the GPIO 5 V pins are the same node). But the
GPIO header is 2.54 mm MALE PINS, and nothing in the instrument bridged a crimped JST cable
to them. That left the single least-defined joint in the build: either somebody solders
wires to a header, or the 5 V arrives on friction-fit crimp housings pushed onto pins in a
box full of stepper vibration. The lighting made it worse rather than causing it, by adding
a clocked SPI pair to the same crossing.

So: one small board with a 2x20 socket that plugs onto the header, and JST connectors for
everything else. The solder is all ON A PCB, which is the standing rule; the harness stays
crimped end to end.

WHAT CROSSES HERE
  * Pi 5 V IN, from motor_ctrl J5 -- GPIO pins 2/4 (5 V) and 6/9 (GND). Up to 3 A.
  * LED 24 V, passing through to both lighting drops (docs/lighting-bus.md, 2026-09-30).
    It arrives on J4 from the motor board's fused J7 and leaves on J3 (fret boards, 0.93 A
    over two contacts) and J6 (foot strip, 0.77 A over one). Every lit board makes its own
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
  advice backwards. The LED DRIVER was chosen for a high PWM rate -- the frequency its driver
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
     and a chain of twelve of them is 2688 bits per frame; at 1 MHz that frame takes
     2.69 ms, so refreshing at 200 Hz gives 2.69 ms of activity and 2.3 ms of silence,
     repeating 200 times a second. That envelope sits squarely in the audio band, and
     anything that rectifies it turns it into a 200 Hz buzz. Slowing the clock makes the
     burst LONGER, not smaller. So: pick a clock with enough headroom to write frames
     BACK TO BACK and keep writing, so the line carries a steady inaudible carrier with no
     audio-band modulation. The chip latches per packet, so continuous writes are fine.
     ⚠ FIRMWARE: continuous streaming, not a timed refresh. Rate is then free to choose.
  3. A GROUND RETURN IN THE SAME CABLE. J3's four ways (V24 GND SCK SDT, fret_led's own
     J1) put GND beside the clock, so the pair has a return conductor in the lead instead
     of finding its way home through the chassis. Loop AREA is what couples to a coil, not
     wire length.
  4. DISTANCE, which is the harness's job, not this board's: the run should reach the lit
     boards without crossing the deck past the pickup. See INSTALL_NOTES.md.

  ⚠ NONE OF THIS TOUCHES THE ONE KNOWN AUDIO-BAND TERM. At grey levels under 128/65535
  the TLC59711's own PWM energy lands at sub-audio multiples of its 152 Hz full cycle (the
  working was in elec/led_strip.py, deleted 2026-10-01 -- git history). That is inside the driver, on the lit board, not on this cable -- bench it
  beside the pickup before committing, because no cable discipline can reach it.

  If a bench test beside the pickup still shows the lighting in the audio, the escalation is a
  differential pair (RS-422 driver here, receiver at the lit board) -- NOT more filtering. That
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
# (a 2.54 male header is 8.54 BEFORE its socket goes over it). So: HX PZ1.27-2x7P WZ,
# LCSC C22438113, the RIGHT-ANGLE one (2902 in stock 2026-10-02). The note here used to
# name C22438122, which is the same family's VERTICAL header and not this footprint.
# ⚠ WHICH MEANS THE KEYING IS THE CABLE'S LENGTH, and that is a real constraint rather
# than a hope: the run is fixed and short, pin 1 is on the silk, and a cable cut to reach
# only one way cannot be fitted reversed. The alternative was FFC/ZIF, keyed by the
# connector's own shape -- rejected because this instrument gets stomped on and brenner
# flagged mating cycles. Reversing this cable puts 3V3 into a GPIO, so if the assembled
# machine ever shows someone forcing it, that is the escalation.
# ⚠ 2x8 SINCE 2026-10-04: THE POWER BUTTON (user). The ribbon grew two ways, 15 and 16,
# for the button's two throws. Same family, one position longer: HX PZ1.27-2x8P WZ, LCSC
# C22438114 (2,050 in stock that day). Ways 1-14 are where they were.
UI_FP = "Connector_PinHeader_1.27mm:PinHeader_2x08_P1.27mm_Horizontal"

# way -> (signal, Pi header pin). Decided in docs/pi-cap-ui-ribbon.md: the display is on
# SPI1 because SPI0 belongs to the LED chain and a TLC59711 has no chip select, so any
# display byte on that bus becomes LED data. GPIO19 (pin 35) stays EMPTY on purpose --
# the spi1-1cs overlay claims it as MISO and a switch there would work until the overlay
# loads. The order puts the clock beside the ground and keeps the two fast lines away from
# the seven switch lines, which are static on a human timescale.
# ⚠ THE WAY ORDER IS harness.UI_RIBBON's (2026-10-02), which is the UI board's: that board
# could not route this cap's original order. Each signal keeps its Pi header pin; only
# the way it rides changes.
# ⚠ UI_RES_N IS ON PIN 22 (GPIO25), NOT 33 (pre-order review, 2026-10-06). Pin 33 is
# GPIO13, and the foot strip's bus on pins 8 / 10 is SPI5: the stock spi5-1cs overlay
# "enables spi5 on GPIOs 13-15" and has no no_miso parameter, so loading it muxes GPIO13
# to SPI5 MISO and the display's reset stops being a driven line. GPIO13 was picked as a
# plain GPIO two days before SPI5 was. GPIO25 is an alternate function of no bus this
# instrument uses (SPI0 is 7-11, SPI1 16-21, SPI5 12-15), and pin 22 stands directly
# over the ribbon header. Pin 36 (GPIO16) was tried first and did not route: from x 19
# it has to cross the whole east half of the header, and UI_DC and UI_RES_N both came
# back open. Pin 33 is left empty for the same reason as pin 35.
# UI_DC MOVED WITH IT, from pin 37 (GPIO26) to pin 7 (GPIO4), the same day. Its way on
# the ribbon header is in the edge-side row's WEST half, so its drawn escape comes out
# round the header's west end; with the reset line now coming down beside it there was
# no way back east to pin 37 (or to pin 36, tried next), and it came back open both
# times. Pin 7 is on the side the escape already faces. GPIO4 is a plain GPIO unless
# the 1-wire overlay is loaded, which this instrument does not use.
UI_WAYS = (("UI_SW_A", 11), ("UI_SW_B", 13), ("UI_SW_C", 15), ("UI_SW_D", 16),
           ("UI_SW_PUSH", 18), ("UI_ENC_A", 29), ("UI_ENC_B", 31), ("GND", 6),
           ("UI_SCLK", 40), ("+3V3_PI", 1), ("UI_SDIN", 38), ("UI_DC", 7),
           ("UI_CS_N", 12), ("UI_RES_N", 22),
           # ⚠ NOT THE PI'S. The power button's two throws pass straight through this board
           # to J4 and on to the output panel, which is where the supply comes in and the
           # only place it can be cut. No header pin: the Pi must not be able to hold its
           # own supply on or off, and a line that reaches the inlet's side of the switch
           # has no business on a GPIO.
           ("PWR_SW_UP", None), ("PWR_SW_DN", None))

import harness as _H  # noqa: E402
assert tuple(s.replace("UI_", "").replace("+3V3_PI", "+3V3") for s, _ in UI_WAYS) == _H.UI_RIBBON, (
    "the cap's ribbon order is not harness.UI_RIBBON -- the UI board is built from that "
    "list, so the two ends of one cable would disagree")

XH_FP = "Connector_JST:JST_XH_S4B-XH-SM4-TB_1x04-1MP_P2.50mm_Horizontal"
PH6_FP = "Connector_JST:JST_PH_S6B-PH-SM4-TB_1x06-1MP_P2.00mm_Horizontal"
SOCKET_FP = "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical"

# Raspberry Pi 40-way header, PHYSICAL pin numbers -- which is also how the 2x20 footprint
# numbers its pads (1/2 the first pair, odd on one row, even on the other), so the socket's
# pad n IS header pin n and no mapping table is needed.
PI_5V = (2, 4)
# ⚠ PINS 14 AND 20 ARE DELIBERATELY NOT TAKEN, and this is the UI ribbon's doing.
# The header has eight GND pins; this board uses six. Fanning J5's thirteen signals out of
# the socket band put +3V3_PI across the whole band at y -7.23 -- on B.Cu east of x -7.95 and
# on F.Cu west of it, so there is no layer on which anything can cross it -- and pins 14 and
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

# The fret boards' cable. SAME ORDER as fret_led's J1 -- one crimp order, and GND lands on
# both ends of the row so each signal has a return beside it (note 3).
# ⚠ V24, NOT V5 (2026-09-30, docs/lighting-bus.md 3-4): every lit board carries its own buck
# now, so what crosses this board is the 24 V bus and nothing is regulated for the LEDs
# upstream. Same connector, same six ways, same order -- only the rail's name and voltage.
# ⚠ FOUR WAYS, IN THE INSTRUMENT'S ONE ORDER (user, 2026-10-04; harness.py has the rule):
# GND, power, data, data -- and because the power is 24 V the fret drop is an XH, like
# every other 24 V lead. It was a PH for a day, with 24 V on way 1 so that swapping it with
# bus B's PH drop could not put 24 V on a sensor's 5 V pin; the family now does that job
# outright (no XH plug enters a PH header) and the order no longer has to.
#   What a wrong mate does now, XH for XH: on a CAN drop or a tee, GND meets GND and
#   24 V meets 24 V, and the Pi's two SPI pins, through 68 ohm each, meet CAN_H / CAN_L --
#   0 to 3.3 V on a bus that idles at 2.5 V. On the lights inlet J4 the same, with the two
#   switch lines instead of CAN. Nothing is over-volted by any of them.
STRIP_PINS = _H.LED_DROP          # = fret_led J1
# ⚠ THE FOOT DROP IS AN XH TOO, AND IT IS THE THROUGH-HOLE ONE BECAUSE THE SURFACE-MOUNT ONE
# DOES NOT FIT. The band it sits in is 9.4 mm between the socket's courtyard and the board
# edge. The side-entry SMT part every other XH here uses (S4B-XH-SM4-TB) needs its lands
# across 10.3 mm of board -- signal tails at the back, hold-down tabs at the mouth -- so it
# would have cost ~3 mm of board toward the endplate. S4B-XH-A is the same header on four
# posts and nothing else: 2 mm of land at the back, and the body may hang past the edge
# because nothing of it is soldered there. It overhangs by 2.7 mm, into the space the
# ribbon's plug and both cables already leave through. Same housing, same crimp, same
# 6.1 mm height (under the socket's 8.5 mm gap).
FOOT_PINS = _H.LED_DROP           # = foot_led_a J1
XH_THT_FP = "Connector_JST:JST_XH_S4B-XH-A_1x04_P2.50mm_Horizontal"


def _r(tag, value, desc):
    return Part(name="R", ref_prefix="R", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint="Resistor_SMD:R_0402_1005Metric",
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, fp="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _xh(tag, desc, rail="V5", ways=None):
    return Part(name="S4B-XH-SM4-TB", ref_prefix="J", ref=tag, tag=tag,
                dest="NETLIST", tool="skidl", value="S4B-XH-SM4-TB",
                description=desc, footprint=XH_FP,
                pins=[Pin(num=i + 1, name=n, func=P)
                      for i, n in enumerate(ways or ("GND", rail, rail, "GND"))])


# ⚠ THE LIGHTING CABLE CARRIES THE POWER BUTTON TOO (2026-10-04), AND IT GAVE UP ITS DOUBLED
# CONTACTS TO DO IT. The two switch lines have to reach the output panel, and the only
# cables that leave this board for the motor controller (which holds the far end of the
# panel's supply cable) are J2 and J4. The connector row is full -- 50.6 of the board's
# 56 mm -- so J4 cannot grow past a 4-way, and J2 needs both its 5 V contacts (3 A to
# the Pi against PH's 2 A per contact). J4 does not: the lighting bus is 1.70 A at full
# white, 57 % of ONE contact. So J4 is GND, 24 V, switch UP, switch DN -- ways 1 and 2
# where every 4-way XH in the instrument has them.
# The lines are the switch's own contacts to ground and nothing else: whatever pulls them
# up lives on the output panel and stays at or under the switch's 12 V / 0.3 A.
LED_IN_PINS = _H.LIGHTS_LINK                                 # = motor_ctrl J7, one list


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
            | {h for _s, h in UI_WAYS if h})
    for n in range(1, 41):
        if n not in used:
            Net("PI_NC_%d" % n).connect(j1[n])

    # ⚠ THE UI BOARD'S RIBBON (brenner's station). 14 ways, 1.27 mm, 2x7, right-angle so
    # the cable leaves IN PLANE inside the socket's own 8.5 mm standoff rather than upward
    # into the endplate -- the same argument that made every other connector on this board
    # a side-entry part. See UI_WAYS above for the map and why SPI1 rather than SPI0.
    # ⚠ AND THIS IS THE FIRST TIME THIS BOARD TOUCHES +3V3. It carried +5V_PI, +5V_LED, GND
    # and the two SPI0 lines and nothing else, so way 7 is a new net off header pin 1 -- the
    # PI'S OWN 3V3 REGULATOR, good for about 500 mA across everything on it. Under 100 mA
    # for a display module is fine; if the station ever grows a backlight or a second
    # module it needs its own regulator rather than creeping up on the Pi's budget.
    j5 = Part(name="PinHeader_2x08", ref_prefix="J", ref="J5", tag="J5", dest="NETLIST",
              tool="skidl", value="PZ1.27-2x8P",
              description="UI board ribbon, 16-way 1.27 mm 2x8 right-angle (LCSC C22438114)",
              footprint=UI_FP, pins=[Pin(num=i + 1, func=P) for i in range(16)])
    ui_nets = {}
    for _way, (_sig, _hdr) in enumerate(UI_WAYS, start=1):
        if _sig == "GND":
            gnd += j5[_way]
            continue
        n = ui_nets.setdefault(_sig, Net(_sig))
        if _sig == "+3V3_PI":
            # ⚠ THE RIBBON'S 3V3 LEAVES THROUGH A CURRENT-LIMITED SWITCH. It is the Pi's
            # OWN 3V3 rail going out on a cable, and a short anywhere along that cable or
            # on the UI board is a short on the rail the Pi's SD card and SoC I/O run from.
            # ⚠ A SWITCH AND NOT A POLYFUSE, BECAUSE THE BUDGET HERE IS VOLTS. The display
            # (Newhaven NHD-2.7-12864WDW3, its sheet p.6) draws 345 mA typical / 375 max
            # at 3.3 V with every pixel lit and wants 3.0 V at its pin: 0.30 V to lose
            # between the Pi and the module, of which half a metre of ribbon takes about
            # 0.13 and the UI board's copper about 0.06. An 0805 polyfuse is 0.15 to 0.85
            # ohm (a 200 mA one 0.65 to 3.5): 0.06 to 0.32 V at 375 mA, so no polyfuse
            # guarantees a full-white frame. TPS2553 (TI SLVS841): 85 mohm typical, 135
            # hot, so 0.03 to 0.05 V, and the total is 0.24 V at the worst.
            # RILIM 49.9k -> 475 / 520 / 565 mA (the sheet's own row): the least limit is
            # 27 % over the display's most, and a dead short draws at most 0.57 A from
            # the Pi until the part's thermal cut-out cycles it. Same part and resistor
            # as motor_ctrl's bus-B switch. EN (active high) is tied to IN. FAULT is
            # open-drain and left open: every GPIO on the ribbon is spoken for.
            # Constant-current, not latch-off: the module's own capacitors are a start
            # into a capacitive load.
            u1 = Part(name="TPS2553DBVR", ref_prefix="U", ref="U1", tag="U1", dest="NETLIST",
                      tool="skidl", value="TPS2553DBVR",
                      description="3V3 to the UI ribbon: current-limited switch, 0.52 A "
                                  "(LCSC C55266)",
                      footprint="Package_TO_SOT_SMD:SOT-23-6",
                      pins=[Pin(num=1, name="IN", func=P), Pin(num=2, name="GND", func=P),
                            Pin(num=3, name="EN", func=P), Pin(num=4, name="FAULT", func=P),
                            Pin(num=5, name="ILIM", func=P), Pin(num=6, name="OUT", func=P)])
            v33_ui = Net("+3V3_UI")
            n += j1[_hdr], u1["IN"], u1["EN"]
            gnd += u1["GND"]
            v33_ui += u1["OUT"], j5[_way]
            Net("U1_NC_4").connect(u1["FAULT"])
            r5 = _r("R5", "49k9 1%", "ribbon 3V3 current limit: 520 mA typ (TPS2553 p.7)")
            Net("UI_ILIM").connect(u1["ILIM"], r5[1])
            gnd += r5[2]
            for _t, _net, _val, _what in (
                    ("C5", v33_ui, "1uF/16V", "TPS2553 OUT bypass, at the pin"),
                    ("C6", n, "100nF", "TPS2553 IN bypass -- 0.1 uF or more, at the pin")):
                _cc = _c(_t, _val, _what)
                _net += _cc[1]
                gnd += _cc[2]
            continue
        n += j5[_way]
        if _hdr:                     # the power button's two ways reach no header pin
            n += j1[_hdr]

    # 5 V is a PH (harness.py: XH carries 24 V, PH carries 5 V) and a 6-way, because the
    # Pi's 3 A needs two contacts and the second power pair lives on ways 5 and 6. Ways 3
    # and 4 are the standard's data ways; this lead has no data, so they join nothing.
    j2 = Part(name="S6B-PH-SM4-TB", ref_prefix="J", ref="J2", tag="J2",
              dest="NETLIST", tool="skidl", value="S6B-PH-SM4-TB",
              description="Pi 5 V in, from motor_ctrl J5 (GPIO pins 2/4 + 6/9), LCSC C265405",
              footprint=PH6_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(_H.PI_5V_LINK)])
    gnd += j2[1], j2[6]
    v5_pi += j2[2], j2[5]

    j4 = _xh("J4", "LED 24 V in + the power button's two throws out, to motor_ctrl J7",
             ways=LED_IN_PINS)
    gnd += j4[1]
    v24_led += j4[2]
    ui_nets["PWR_SW_UP"] += j4[3]
    ui_nets["PWR_SW_DN"] += j4[4]

    # the fret drop: power and both signals, in fret_led's J1 order
    j3 = _xh("J3", "to fret_led_key J1 -- 24 V and SPI0", ways=STRIP_PINS)
    gnd += j3[1]
    v24_led += j3[2]

    # the foot drop: S4B-XH-A, the through-hole side-entry XH (why that one: the note at
    # FOOT_PINS). 0.77 A through its one V24 contact (3 A rated) -- lighting-bus.md 3.
    j6 = Part(name="S4B-XH-A", ref_prefix="J", ref="J6", tag="J6",
              dest="NETLIST", tool="skidl", value="S4B-XH-A",
              description="to foot_led_a J1 -- 24 V and SPI5, LCSC C157925",
              footprint=XH_THT_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(FOOT_PINS)])
    gnd += j6[1]
    v24_led += j6[2]
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
    sck += r1[2], j3[3]
    r2 = _r("R2", SERIES_R, "MOSI series source termination (see docstring note 1)")
    sdi_pi += r2[1]
    sdi += r2[2], j3[4]

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
    "layers": 4,
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
        "J1": (0.00, -4.50, 90.0),    # 4.5 from the board edge = the Pi header's own margin
        # ⚠ RE-TILED FOR THE SIDE-ENTRY BODIES. Courtyards are 16.7 x 12.0 (4-way XH) and
        # 17.2 x 10.2 (6-way PH) against the 12.4 x 5.75 of the vertical parts they
        # replace, so the three together take 50.6 of the board's 56: 0.9 mm at the east
        # edge, 0.8 and 1.4 between them, 2.3 at the west edge. Their courtyards sit 6.05 ABOVE the placement point, which is why y is 5.4
        # and not 8 -- at 8 they overhung the +Y edge by 2 mm.
        "J2": (18.50, 9.40, 180.0),       # Pi 5 V in (6-way PH, courtyard 17.2 wide)
        "J4": (0.75, 9.40, 180.0),        # LED 24 V in
        "J3": (-17.35, 9.40, 180.0),      # out to the fret boards
        # the foot drop goes in the ribbon's band, mouth -Y like the ribbon, at the -X end
        # (placed by its post row: posts at y -10.50, 2.9 below the socket's pads, ways at
        # x -22.50 / -20.00 / -17.50 / -15.00; the body runs out to y -19.7, 2.7 past the edge)
        # (2026-10-05: 2 mm in from where it was. In the instrument the mated XHP-4 housing
        # stood in the slot the trunk's ground and feed-2 conductors drop through onto
        # motor_ctrl J3 -- 3.5 mm3 into each. The gate could not see it: a plug is not a
        # built solid.)
        "J6": (-18.75, -10.50, 0.0),
        # (and its two series resistors 2 mm in with it, out of its courtyard)
        "R3": (-10.50, -9.00, 180.0),
        "R4": (-10.50, -11.00, 180.0),
        # the passives drop into the band between J1's socket and the connector row
        "C1": (20.00, 1.00, 180.0),
        "C3": (15.00, 1.00, 180.0),
        "C2": (6.00, 1.00, 180.0),
        "C4": (1.00, 1.00, 180.0),
        "R1": (-5.00, 1.00, 180.0),
        "R2": (-8.00, 1.00, 180.0),
        # ⚠ THE UI RIBBON SITS IN THE NEW BAND AND FACES AWAY FROM THE POWER CABLES. The
        # band is y -17..-7, clear of the socket's pad rows at -5.8..-3.2; the part is
        # ~7.6 x 1.3 of pads with its body 3.07 beyond them. ROT 270 turns the body -Y, so
        # the ribbon leaves on the opposite edge from J2/J3/J4 -- which carry up to 3 A to
        # the Pi and 1.6 A at 24 V to the lights, and this one carries a display clock.
        # ⚠ ITS PLASTIC STOPS AT THE BOARD EDGE AND ITS PINS HANG PAST IT (2026-10-02). At
        # y -11.00 the pin TIPS were at the edge and the 4 mm of pin lay over the board --
        # where the IDC socket has to go, and that socket is ~5.5 mm across its rows on
        # pins standing ~1.4 and ~2.7 off the laminate: it would have had to sink 0.7 mm
        # into the board to seat. -17.00 (edge) + 2.135 (pad centroid -> plastic face).
        # ⚠ +0.635 WHEN IT BECAME A 2x8 (2026-10-04), SO WAYS 1-14 DID NOT MOVE. The part is
        # placed by its pad centroid, and one more pin pair moves the centroid half a pitch;
        # left at 3.80 every one of the fourteen routed ways shifted 0.635 and the first
        # route came back with UI_DC and UI_RES_N open. The new pair lands at x -1.28.
        "J5": (3.80 - 0.635, -BOARD_L / 2.0 + 2.135, 270.0),
        # the ribbon's 3V3 switch, off the header's -X end, unturned so IN / EN (the
        # Pi's side) face the socket's pin 1 and OUT / ILIM face the ribbon; its output
        # capacitor and limit resistor on the ribbon side, its input bypass on the other,
        # each with its live pad toward the pin it serves
        "U1": (-8.00, -13.50, 0.0),
        "C5": (-4.90, -14.30, 0.0),
        "R5": (-4.90, -12.60, 0.0),
        "C6": (-11.00, -14.30, 180.0),
    },
    # ⚠ THE SOCKET'S GROUND PADS TAKE NO STITCHING VIA, AND DO NOT NEED ONE. The check
    # exists because an SMD pad touching only a pour can be orphaned when routing carves
    # the pour up. These are PLATED THROUGH-HOLE pads: the barrel already spans B.Cu and
    # F.Cu, so each one IS its own via and reaches both pours by construction. There is no
    # room beside them either -- 2.54 mm pitch leaves ~0.8 mm between pads, under a 0.6 mm
    # via plus clearance -- so the check can only ever fail here.
    # J5.8 (the ribbon's ground way) joined them 2026-10-04: its stitch via stood 0.30 mm,
    # hole edge to hole edge, from the pin's own hole against the fab's 0.45 (quality A12).
    "stitch_exceptions": (tuple("J1.%d" % n for n in (6, 9, 14, 20, 25, 30, 34, 39))
                          + ("J5.8",)),
    # GND pour on both layers: this board carries up to 3 A to the Pi and 1.6 A to the
    # strip, and the return for both shares it.
    "zones": [("GND", "F.Cu", 0.3), ("GND", "In2.Cu", 0.3), ("GND", "B.Cu", 0.3)],
    # a pour the router is not told about is copper it routes signals through (motor_ctrl)
    # In2, the inner layer next to the bare face: the Pi's 5 V lane runs on B.Cu, right over it
    "plane_layers": ("In2.Cu",),
    "stitch_nets": ("GND",),
    "edge_escape": ("J5",),       # the ribbon header's edge-side row: layout._edge_row_escape
    # ⚠ THE LIGHTING BUS IS NOT A SIGNAL. Every net here was the 0.25 mm default (0.88 A at a
    # 10 C rise by IPC-2221) and this one carries 0.93 A to J3 and 0.77 A to J6.
    # 0.3 mm (~1.0 A) IS WHAT ROUTES, NOT WHAT WAS WANTED: 0.5, 0.4 and 0.35 each left one
    # GND island -- the wider rail cuts the pour in the band the UI ribbon already fans
    # across. The deliberate wide strip that sentence used to ask for is "tracks" below; this
    # width now only governs what the router still lays (the two caps' stubs).
    "net_widths": {"+24V_LED": 0.3},
    # ⚠ AND THE FRET BRANCH IS LAID BY HAND, BECAUSE THE NETCLASS COULD NOT GIVE IT MARGIN.
    # J4 -> J3 is the stretch that carries everything (1.70 A in, 0.93 A on to the fret
    # boards), and at 0.3 mm it was on a ~1.0 A track. It is one straight run in the strip
    # ABOVE the connector lands, where nothing else goes: a 1.0 mm bar (~2.4 A) at y 10.5,
    # 0.29 off J3's lands and clear of the mounting pads, dropping into J4 way 2 and J3 way 1
    # (2026-10-04: J3 is a 4-way with ONE 24 V way, which stands at the same x the 6-way's
    # way 2 did, so the bar did not move and the tie across to a second way is gone -- that
    # land is GND now). The router keeps the rest
    # of the net -- the caps and the 0.77 A foot branch -- at 0.3 mm.
    # (2026-10-04: J4's 24 V is way 2 ALONE now -- ways 3 and 4 are the power button's --
    # so the bar comes down at x 2.00 and the tie across to way 3 is gone.)
    # (2026-10-04, later: J3 is an XH with 24 V on way 2, at x -16.10. The bar is 1.75 mm
    # longer and comes down there; the foot branch leaves from the same land.)
    # U1's ground pin stands between its IN and EN pins, both on the Pi's 3V3: the pour
    # cannot reach it and neither could the stitcher (2026-10-05, a 1.0 x 0.3 island and
    # the pin open). It goes inward, to a via under the middle of the package, 0.31 from
    # the ILIM pad opposite and 0.33 from the pads either side.
    "tracks": [("GND", "F.Cu", 0.3, [(-9.14, -13.50), (-8.00, -13.50)]),
               ("+24V_LED", "F.Cu", 1.0, [(2.00, 7.13), (2.00, _BAR_Y), (-16.10, _BAR_Y)]),
               ("+24V_LED", "F.Cu", 0.8, [(-16.10, _BAR_Y), (-16.10, 7.13)]),
               # the foot branch, on the path the router found when the net was all its own
               # (with the bar declared it left J6 way 1 open): 0.77 A at 0.4 mm
               # (2026-10-04: it leaves J3's land 0.8 mm lower than it did, because the land
               # beside it is GND now and the old diagonal passed its corner at 0.06 mm)
               ("+24V_LED", "F.Cu", 0.4, [(-16.10, 7.13), (-16.10, 4.45), (-19.44, 1.11),
                                          (-20.25, 1.11),
                                          # x -20.25 is the gap between two of the socket's
                                          # pads, and the only one: the last step is to J6
                                          (-20.25, -9.90), (-20.00, -10.15), (-20.00, -10.50)])],
    # ⚠ TWO GND STITCHES IN THE RIBBON'S BAND. Growing the board and fanning 13 UI signals
    # across it cut the GND pour into the main body plus small fragments, and the fragments
    # are the band's own return path -- each one is what a switch line runs over. They are
    # each anchored on a socket pad, but one pair came back as a ratline between the B.Cu and
    # F.Cu pours, which is the pour's way of saying the anchoring is a hairline rather than a
    # connection. These two vias tie the band to both planes outright.
    # Sites searched against the routed board (clearance headroom 1.213 and 1.188 mm over the
    # rule), not chosen -- the same method the optical board's bring-up pads used.
    # ⚠ AND THE LAST TWO ARE THE ONES THAT MATTER, because the first two fixed the wrong
    # thing. Every GND pad on this board is either a socket pin -- all eight of them in the
    # band, at y -4.5 -- or an SMD pad on J2/J3/J4, which touch F.Cu ONLY, being
    # surface-mount parts. So once the ribbon's fan cut the band into fragments, those
    # eight pins anchored the FRAGMENTS and the B.Cu MAIN POUR was left with no anchor of its
    # own: one ratline, B.Cu zone to F.Cu zone, and stitching the fragments did nothing for
    # it. These two sit in the new band's bottom strip, below J5's body (which reaches
    # y -14.07), where both layers carry the main pour.
    # ⚠ A FIFTH VIA WAS TRIED AT (-1.30, -6.00) AND IT WAS BOTH WRONG AND DESTRUCTIVE.
    # It was meant to anchor the 5.3 mm2 F.Cu sliver at x -1.95..-0.64 -- which turned out to
    # be anchored already, by J1.20 at (-1.27, -5.77), a GND pad my own spot-search skipped
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
    #     MAIN     B4,F3 + B3,B2   (J1.6, J1.9, J1.14, J1.25, J1.39 and most vias)
    #     ISLAND A B1,B0 + F0,F1,F2 (J1.20, J1.30, J1.34, J5.1)
    # Nothing joined them: every through item lands inside ONE cluster on both layers. The
    # bridge has to be a point that is in cluster A on one layer and MAIN on the other, and
    # (16.62, -10.91) is exactly that -- B island 0, over the F main pour, 3.739 mm of
    # clearance headroom. One via, not a fifth guess.
    "vias": [("GND", -8.00, -13.50), ("GND", 21.50, -11.00), ("GND", 11.75, -7.00),
             ("GND", 20.00, -15.50), ("GND", -14.00, -15.50),
             ("GND", 16.62, -10.91),
             # ⚠ AND ONE ON THE WEST SIDE, FOR THE SAME REASON AS THE BRIDGE ABOVE (2026-09-30).
             # The foot drop's fan (R3/R4 -> J6) and its declared 24 V branch down x -20.25 cut
             # a second cluster off west of the socket: F island x -19.6..-6.5, y -5.1..3.0 and
             # B island x -21.0..-6.7, y -5.1..-1.2, anchored on each other and on nothing else.
             # Five bar/branch variants all left it open, which is what a missing bridge looks
             # like -- not router luck. This point is in the F cluster and the B main pour.
             ("GND", -12.50, 1.20)],
    "router_passes": 12,
    # ⚠ EVERY PART IS ON ONE FACE, THE ONE TOWARD THE PI, and the socket is why: its body
    # is the standoff the cap hangs off the Pi's header by, so it has to be between the two
    # boards. On the far face it would be a bump with nothing holding the board on.
    # ⚠ THE CONNECTORS SHARE THAT FACE, AND THAT IS A HEIGHT FIX, NOT A STYLE CHOICE
    # (2026-09-22). dimensions.ELEC_STACK_D reserves 14.0 mm above the Pi's PCB and the
    # MOTOR BANK is packed against that number, so it cannot grow to suit this board. With
    # vertical connectors on the far face the cap needed 8.5 (socket) + 1.6 (board) +
    # 7.0 (XH) = 17.1 and drove 260 mm3 into the endplate -- measured by sweeping it, not by
    # looking at it. Side entry there still needs 15.85. Between the boards the connectors
    # live in the socket's own 8.5 mm gap (PH 5.5, XH 5.75), the cap's far face is bare PCB
    # at 10.1, and the cables leave sideways instead of upward into the endplate.
    # ⚠ THE PASSIVES TOO, AND THAT IS AN ASSEMBLY-COST FIX (user, 2026-09-28: "I hope you
    # aren't making a two sided board, that increases the cost"). Two LAYERS of copper is
    # standard and cheap; what costs is parts on BOTH FACES, because the fab runs a second
    # placement setup. They are 0.5 mm tall against a 8.5 mm gap, so they go where the
    # connectors are and the far face is bare laminate.
    # ⚠ AND THE POPULATED FACE IS THE DRAWING'S FRONT, because the fab's cheaper assembly
    # tier places on the top side only (quoted 2026-10-06: a board populated on its bottom
    # is Standard PCBA, 25.75 setup against 8.24). The board is installed FACE DOWN on the
    # Pi -- see electronics._cap_place.
    "single_sided": True,           # documentation: nothing reads it
    # short words for the pin legends: a legend is as wide as its longest net name
    # THE LETTERING READS AT 180 (tools/silk_read.py). The cap goes on the Pi FACE DOWN,
    # so the face a person sees is its BACK, from the player's side. Back lettering is
    # mirror writing that reads right once the board is turned over left-to-right; as
    # the cap sits, that needs the half turn. (The front then reads the same way up when
    # the cap is lifted off and rolled over toward you.)
    "silk_read": 180,
    "silk_labels": {"+24V_LED": "24V", "+5V_PI": "5V", "SCK_FOOT": "SCK", "SDT_FOOT": "SDT",
                    "PWR_SW_UP": "SW UP", "PWR_SW_DN": "SW DN"},
    "qty_per_instrument": 1,
    "quality": {
        "power_paths": [
            # the Pi's whole supply: 3 A is motor_ctrl U5's rating and F2 is 4 A
            {"net": "+5V_PI", "from": "J2.2", "to": ["J1.2", "J1.4"], "amps": 3.0},
            # lighting bus, every zone at full white (software-capped): 1.70 A in,
            # 0.93 A on to the fret boards, 0.77 A to the foot strip (docs/lighting-bus.md)
            {"net": "+24V_LED", "from": "J4.2", "to": ["J3.2"], "amps": 1.70},
            {"net": "+24V_LED", "from": "J4.2", "to": ["J6.2"], "amps": 0.77},
            # the display's supply, behind U1: 375 mA with every pixel lit (its sheet's
            # maximum) plus the UI board's pull-ups
            {"net": "+3V3_PI", "from": "J1.1", "to": ["U1.1"], "amps": 0.4},
            {"net": "+3V3_UI", "from": "U1.6", "to": ["J5.10"], "amps": 0.4},
        ],
        # the power button's two throws: a few mA of pull-up current from the output
        # panel, switched to ground on the UI board. Signals, not supplies.
        "not_power": ("PWR_SW_UP", "PWR_SW_DN"),
        "waive": {
            # A1 does not add parallel vias up (PCB_QUALITY.md A1, "How it is checked"), so
            # it reports one barrel. The arithmetic it asks for:
            "A1:+5V_PI J2.2>J1.2": "eight 0.4 mm vias in parallel join the F.Cu lands to "
                                   "the B.Cu lane, on a 2.2 mm patch each side: 8 x 0.90 mm "
                                   "of equivalent barrel = 7.2 mm against the 1.37 mm that "
                                   "3 A needs; any two of them carry it",
            "A1:+5V_PI J2.2>J1.4": "the same eight vias as J2.2>J1.2: 7.2 mm equivalent "
                                   "against 1.37 mm needed",
        },
        # A13 (cadkit/PCB_QUALITY.md): what the DESIGN leaves open, and how many nets each
        # repeated structure is on. The pass fails on any difference from the routed board.
        # A16: the one part voltage_check.py could not rate, stated here instead.
        "pin_volts": {
            "J1": {"max": "none",
                   "src": "JLCPCB parts API attributes for C5124634 (2.54-2*20P socket): 2.5 A "
                          "a contact and no voltage figure; its datasheet is an image of the "
                          "drawing with no electrical table. Read 2026-10-06",
                   "why": "a 2.54 mm pin socket: formed contacts in a moulded body, with no "
                          "junction and no film dielectric to break down, on a header whose "
                          "highest net is the Pi's own 5 V. Its maker publishes no working "
                          "voltage to quote, and the parts of this pattern that do publish one "
                          "give hundreds of volts"},
        },
        "unconnected": {
            "J1": {
                "pins": "3 5 14 17 20 21 24 26 27 28 32 33 35 36 37",
                "why": "Pi header pins this cap gives no function (the GPIO map is in pi_cap.py)"
            },
            "J2.[34]": "the 6-way's two middle ways: no conductor (harness.PI_5V_LINK)",
            "J[234].MP": "JST reinforcement tab: soldered, on no net",
            "U1.4": "TPS2553 FAULT: open drain, not read"
        },
        "net_groups": [
            {
                "name": "UI ribbon: sixteen ways, sixteen nets",
                "pins": [
                    "J5.*"
                ],
                "nets": 16,
                "each": 1
            },
            {
                "name": "two lighting drops: their clock and data are separate buses",
                "pins": [
                    "J3.[34]",
                    "J6.[34]"
                ],
                "nets": 4,
                "each": 1
            },
            {
                "name": "the two drops share ground and the lights' 24 V",
                "pins": [
                    "J[36].[12]"
                ],
                "nets": 2,
                "each": 2
            },
            {
                "name": "lights lead: four ways, four nets",
                "pins": [
                    "J4.[1-4]"
                ],
                "nets": 4,
                "each": 1
            }
        ],
        # A15 tests a track against the ground copper on EVERY other layer, one at a time.
        # The gap it finds under the 5 V lane (5.03 mm, at x 3.8 y 2.5) is in the F.Cu
        # pour, three layers away, where C2 and C4 and their tracks sit.
        "return_slot_ok": {
            "+5V_PI": "a DC supply lane on B.Cu. The layer next to it is In2, the ground "
                      "plane, and that is whole under the lane's full length (sampled "
                      "every 0.25 mm). The cut is in the far face's pour",
        },
        "pinouts": {
            "2.54-2*20P": "Raspberry Pi 4B mechanical drawing + src/electronics._cap_place, "
                          "worked through 2026-10-04: pad 1 sits at board (-24.13, -3.23), "
                          "pad 2 at (-24.13, -5.77), numbers rising toward +X. The cap is "
                          "placed face down (turned 180 about X) over a Pi lying ports-to-+X, its "
                          "header on the +Y long edge, which lands pad 1 at 3.5 mm from the "
                          "Pi's -X end on the INNER row and pad 2 on the edge row: the Pi's "
                          "pin 1 and pin 2 seen from its component side. Pad n is header "
                          "pin n",
            "S4B-XH-SM4-TB": "JST eXH.pdf p.6, Header / SMT type: seen from above with the "
                             "mouth pointing away and the tails toward the viewer, No. 1 "
                             "circuit is the right-hand post. KiCad JST_XH_S4B-XH-SM4-TB "
                             "has its tails at -Y, mouth +Y and pad 1 at -X: the same end. "
                             "Read 2026-10-04",
            "S6B-PH-SM4-TB": "JST ePH.pdf p.4, SMT side entry: looking into the mouth with "
                             "the board below, No. 1 circuit is on the left. KiCad "
                             "JST_PH_S6B-PH-SM4-TB: mouth +Y, pad 1 at -X -- the same end. "
                             "Ways are harness.PI_5V_LINK (GND 5V nc nc 5V GND), which "
                             "reads the same from either end. Read 2026-10-04",
            "S4B-XH-A": "JST eXH.pdf p.5, Header / Side entry type, 3 circuits or more: "
                        "seen from above with the mouth pointing away and the posts toward "
                        "the viewer, No. 1 circuit is the right-hand post. KiCad "
                        "JST_XH_S4B-XH-A: pad 1 at the origin, the others toward +X, body "
                        "toward +Y (down the screen) -- turned mouth-up, pad 1 is on the "
                        "right: the same end. Ways are harness.LED_DROP (GND V24 SCK SDT). "
                        "Read 2026-10-04",
            "PZ1.27-2x8P": "a plain two-row header: the maker numbers nothing, so the "
                           "numbering is the footprint's (KiCad PinHeader_2x08 Horizontal: "
                           "odd pads on the inner row, even on the edge row, 1 / 2 at one "
                           "end) and the way order is harness.UI_RIBBON, asserted above -- "
                           "the same list ui_board's J2 is built from. Which end of the "
                           "cable is way 1 is M1's question, not this one's",
            "TPS2553DBVR": "TI SLVS841 p.5, DBV package: 1 IN, 2 GND, 3 EN (active high "
                           "on the 2553), 4 FAULT, 5 ILIM, 6 OUT. Board: 1 and 3 +3V3_PI, "
                           "2 GND, 4 open, 5 UI_ILIM, 6 +3V3_UI. Read 2026-10-05",
        },
        "manual": {
            "M1": "done 2026-10-05, read off both ROUTED boards. UI ribbon: J5 here and J2 "
                  "on ui_board (main, c9159a48) are the same footprint (PinHeader_2x08 "
                  "P1.27 Horizontal, C22438114) and carry the same net on every pad, 1 to "
                  "16 (SW_A SW_B SW_C SW_D SW_PUSH ENC_A ENC_B GND SCLK +3V3 SDIN DC CS_N "
                  "RES_N PWR_SW_UP PWR_SW_DN), so a straight-through 16-way IDC lead joins "
                  "them pin for pin. The header has no shroud: a reversed socket is an "
                  "assembly error the stripe-to-pin-1 step in INSTALL_NOTES guards, not a "
                  "wiring one. The four JST leads, pad nets read at both ends, all crimped "
                  "1:1: J2 <-> motor_ctrl J5 (GND 5V - - 5V GND, PI_5V_LINK); J4 <-> "
                  "motor_ctrl J7 (GND 24 SW_UP SW_DN, LIGHTS_LINK); J3 <-> fret_led_key J1 "
                  "and J6 <-> foot_led_a J1 (GND 24 SCK SDT, LED_DROP)",
            "M3": "done: In2 is an unbroken GND plane under the whole board (plane_layers), "
                  "with GND pours on B.Cu and F.Cu stitched to it. Every supply path above "
                  "runs over it; no slot, and no return necks through a single via",
            "M4": "no regulator on this board. U1 (TPS2553, a switch): C6 100 nF at IN, the 0.1 uF "
                  "or more its sheet asks for, and C5 1 uF at OUT; the sheet requires no output "
                  "capacitance. C1 22 uF / 16 V + C3 100 nF on the Pi's 5 V at the socket (about 16 "
                  "uF effective at 5 V bias on an 0805 X5R); C2 4.7 uF / 50 V + C4 100 nF / 50 V on "
                  "the 24 V lighting bus -- about half its value at 24 V, which is why it is local "
                  "HF bulk only: each lit board carries its own buck and its own input capacitors",
            "M5": "5 V rail: 16 V capacitor, XH 250 V. 24 V rail: 50 V capacitors, XH 250 V, PH 100 "
                  "V. 3V3: U1 works from 2.5 to 6.5 V; C5 is a 16 V part. R1-R4 are 68 R in series "
                  "with 3.3 V logic. The two switch lines carry the output panel's pull-up, which "
                  "that board holds at or under the switch's 12 V. Contact current is M33",
            "M6": "nothing here needs matching: the display's SPI and the two LED streams are clock "
                  "and data from one master with no data returning, each through this board in a "
                  "few centimetres over the unbroken In2 plane (M3)",
            "M7": "U1, TI SLVS841 typical application: 0.1 uF at IN (C6), RILIM from ILIM to ground "
                  "(R5, 49.9k 1 %, inside the 15k to 232k the sheet allows), EN driven high (tied "
                  "to IN), FAULT an open-drain output with nothing on it, a capacitor at OUT (C5 1 "
                  "uF). No other IC",
            "M8": "U1 EN: tied to IN, on whenever the Pi's 3V3 is. ILIM: R5 to ground. No address, "
                  "mode or boot pin on the board",
            "M9": "no MCU, nothing to program. Every net on the board is on a through-hole "
                  "pin of J1 or J5 or on a connector land, all reachable with a probe from "
                  "the bare back face; ground is on eight socket pins",
            "M11": "finish.py's CAD check: 18 of 18 routed parts present in the CAD, "
                   "every one where the CAD draws it, all eighteen on the one face. The lead's full build on main b0e7a911 (2026-10-05) "
                   "with this board's geometry: 1010 components, 0 unintended "
                   "overlaps, the rotating-part sweep clean -- the board, its parts at "
                   "their drawn heights, its mated plugs and its cables against the "
                   "plastic and the fasteners round it. No mounting hole: the board "
                   "hangs on the Pi's 40-pin header. Parts the fab cannot place: none "
                   "(M30 is the tier)",
            "M10": "decision: no clamp on this board. Every connector mates inside the instrument "
                   "to its own harness. The 24 V it carries is clamped at motor_ctrl (D8, SMAJ30A) "
                   "and fused there (F3); the Pi's 5 V has motor_ctrl's crowbar (D9 + F2). The one "
                   "supply this board SOURCES to a cable, the ribbon's 3V3, is behind U1's current "
                   "limit. Polarised housings on every JST; the ribbon header is not keyed -- see "
                   "M1",
            "M15": "no regulator. U1 is a switch: 3.3 V in against a 2.5 V minimum, 0.05 V across "
                   "it at the worst, and no stability condition on its output capacitor",
            "M16": "decision: no added damping. Both inlets (J2, J4) are plugged at "
                   "assembly with the supply off -- they are inside the closed instrument "
                   "and nothing in service unplugs them. Were one plugged live: 5 V rings "
                   "toward 10 V on a 16 V capacitor, 24 V toward 48 V on 50 V parts",
            "M18": "U1 is fed by the rail it switches, so it is never driven unpowered, and it "
                   "blocks reverse current if its output is held above its input. The UI board has "
                   "no supply of its own. The two switch lines carry the output panel's pull-up and "
                   "touch no IC here",
            "M20": "no pull-up and no termination on this board. The UI's pull-ups are on the UI "
                   "board; the two LED streams are source-terminated here by R1-R4, 68 R at the "
                   "Pi's pins",
            "M21": "no converter on the board",
            "M22": "no op-amp on the board",
            "M25": "U1 has no thermal pad. 0.4 A through 135 mohm is 22 mW. Into a dead short it "
                   "holds about 0.5 A at 3.3 V, 1.7 W, until its own thermal cut-out cycles it: the "
                   "part's designed behaviour, and the fault is not a running condition",
            "M26": "U1 IN is the Pi's side and OUT the ribbon's, by its pinout above. Every other "
                   "net keeps one name from header pin to connector way",
            "M27": "no strap, boot or debug pin is used: header pins 27 / 28 (the HAT ID bus) are "
                   "not connected, and none of the pins taken (7 11 12 13 15 16 18 22 29 31 38 40, "
                   "the SPI0 / SPI5 pairs) is read by the Pi at boot",
            "M28": "JST's own parts: S4B-XH-SM4-TB(LF)(SN) C161861, S6B-PH-SM4-TB(LF)(SN) C265405, "
                   "S4B-XH-A(LF)(SN) C157925 -- the cited drawings are theirs. The 2x20 socket and "
                   "the 2x8 header are symmetric pin fields with no maker numbering. One IC: "
                   "TPS2553DBVR C55266, the constant-current part (not the -1 latch-off one), "
                   "SOT-23-6, pinout above",
            "M31": "name and revision on the front; J2 / J3 / J4 / J6 pin names on the back, "
                   "over each connector, the face that shows with the cap on the Pi; designators at 1.0 mm or larger (A12). The ribbon header's "
                   "pin-1 mark is the footprint's, outside the body",
            "M32": "pitches read from the KiCad files: XH 2.50, PH 2.00, socket "
                   "2.54, ribbon header 1.27. XH 3 A per contact at AWG 22, PH 2 A "
                   "(JST eXH / ePH p.1). Every connector is in the instrument's one order "
                   "(harness.py): GND on way 1, power on way 2, data or nothing on 3 and "
                   "4, and J2's second power pair on 5 and 6. 24 V is on XH and 5 V on "
                   "PH. J6 is the through-hole side-entry XH (same housing; the SMT one "
                   "does not fit its band -- the note at FOOT_PINS)",
            "M33": "5 V: 3 A through J2's two PH contacts (1.5 A each, 75 % of 2 A) and socket pins "
                   "2 + 4. 24 V: 1.70 A through J4's one contact (57 %), 0.93 A through J3's one XH "
                   "contact (31 % of 3 A), 0.77 A through J6's one XH contact (26 %; both figures "
                   "are a software cap with every zone at full white). 3V3: the display is 345 mA "
                   "typical / 375 max with every pixel lit (Newhaven NHD-2.7-12864WDW3 sheet p.6, "
                   "read 2026-10-05), under 0.1 A for a white-on-black page, plus a few mA of "
                   "pull-ups: 0.4 A declared. That is 80 % of the 0.5 A commonly quoted for the "
                   "header's 3V3 pins -- NOT a figure from a Pi 4 document, none was found -- so a "
                   "full-white frame is the one case worth measuring on the first unit (the Pi's "
                   "3V3 at the header). Volts: 0.30 V from 3.3 to the module's 3.0 V minimum; U1 "
                   "0.03 to 0.05 V (85 to 135 mohm), ribbon about 0.13, UI board about 0.06: 0.24 V "
                   "at the worst. Through header pin 1 alone, one socket contact (3 A class)",
            "M34": "U1: IN from the Pi's 3V3 (header pin 1), OUT to the ribbon's way 10; nothing "
                   "else on the board is active. SPI0 SCLK / MOSI and SPI5 SCLK / MOSI leave the Pi "
                   "as outputs and reach inputs on the lit boards through 68 R; the UI nets keep "
                   "one name from the header pin to the ribbon way. The two switch lines touch "
                   "nothing here",
            "M35": "TI publishes no errata document for the TPS2553; a web search (2026-10-05) "
                   "found only forum threads on behaviour the sheet already describes -- FAULT is "
                   "deglitched and can trail a marginal overload, and the part cycles thermally "
                   "while limiting. Neither matters here: FAULT is not used",
            "M36": "3V3 to the ribbon: U1, current-limited at 475 to 565 mA (RILIM 49.9k, the "
                   "sheet's own row), constant-current with thermal cut-out, so a short on the "
                   "ribbon costs the Pi at most 0.57 A. 24 V to the lit boards: fused at its "
                   "source, motor_ctrl F3 (3 A), which is every XH contact's own rating. 5 V does "
                   "not leave this board except into the Pi",
            "M38": "every part is on the front, the face toward the Pi, inside the socket's 8.5 mm "
                   "standoff; the 0805s lie along X, parallel to the long edges, and the "
                   "nearest is over 4 mm from an edge. Routed outline, no V-score, no "
                   "mounting hole: the board hangs on the 40-pin socket. All five cables "
                   "leave sideways (side-entry parts) with open board edge in front",
            "M39": "U1 FAULT is an open-drain output and is left open. Unused header pins are the "
                   "Pi's own and have no pad on a net. J4 / J6 / J3 carry no unused way that is not "
                   "named in harness.py",
            "M40": "68 R, 22 uF, 4.7 uF and 100 nF are stock values. R5 is 49.9k 1 %, the tolerance "
                   "the limit's table assumes, and says so; U1's description gives its limit. "
                   "Nothing needs a heatsink",
        },
    },
}


# ── THE PI'S 5 V, DECLARED (2026-10-01) ──────────────────────────────────────────────────
# J2 (from motor_ctrl's J5) -> J1 pins 2 and 4 is the Pi's ENTIRE supply, up to ~3 A, and
# the router laid it as 67 mm of 0.25 mm (0.88 A at a 10 C rise) through ONE 0.3 mm via.
# Same fault, same day, as motor_ctrl's side of this cable. It is now one B.Cu lane:
# a field of 0.4 mm vias beside J2's two 5 V lands, 2 mm (3.95 A) across
# the board between the cap row's stitch vias and the header, round the west end of the
# header outside pin 1, and into pins 2 and 4. The return is the two GND pours.
# The caps' stubs stay the router's.
BOARD_NOTES["vias"] = list(BOARD_NOTES.get("vias", [])) + [
    # ⚠ BESIDE THE LANDS, NOT IN THEM (quality A12, 2026-10-04). The vias used to sit two to
    # a land, inside J2's two 5 V lands: 0.40 mm3 of open barrel in a land printed with
    # 0.70 mm3 of paste, on the joint that carries the Pi's whole supply. They are now a
    # field of eight in the strip between the lands and the capacitors, joined to the
    # lands on F.Cu and to the lane on B.Cu.
    ("+5V_PI", x, y, 0.4, 0.8) for x in (17.1, 18.2, 19.3, 20.4) for y in (3.75, 2.65)]
BOARD_NOTES["tracks"] = list(BOARD_NOTES.get("tracks", [])) + [
    # (2026-10-04: J2 is a 6-way PH. Its two 5 V lands are ways 2 and 5, 6 mm apart at
    # x 21.5 and 15.5 with the two unused ways between them, so the patch is 6 mm long
    # and each land drops onto one end of it; the via field has not moved.)
    ("+5V_PI", "F.Cu", 1.0, [(21.5, 6.5), (21.5, 3.2)]),
    ("+5V_PI", "F.Cu", 1.0, [(15.5, 6.5), (15.5, 3.2)]),
    ("+5V_PI", "F.Cu", 2.2, [(21.5, 3.2), (15.5, 3.2)]),
    ("+5V_PI", "B.Cu", 2.2, [(20.4, 3.2), (17.1, 3.2)]),
    # the two capacitors, straight onto the F.Cu patch: left to the router they came back
    # joined through a via in C3's land and 46 mm of 0.2 mm track to C1
    ("+5V_PI", "F.Cu", 0.6, [(20.95, 1.0), (20.95, 2.6)]),
    ("+5V_PI", "F.Cu", 0.4, [(15.48, 1.0), (15.48, 1.9), (16.6, 3.0)]),
    ("+5V_PI", "B.Cu", 2.0, [(18.6, 3.2), (18.6, 2.5), (-1.5, 2.5), (-4.4, -0.4),
                             (-25.3, -0.4)]),
    ("+5V_PI", "B.Cu", 1.6, [(-25.3, -0.4), (-26.1, -1.2), (-26.1, -5.77), (-24.13, -5.77)]),
    ("+5V_PI", "B.Cu", 1.2, [(-24.13, -5.77), (-21.59, -5.77)]),
]

# ⚠ AND THE HEADER'S EAST HALF NEEDS ITS OWN GROUND BRIDGE. The B.Cu pour cannot pass
# between J1's pads (0.84 mm gaps, less two clearances), so the ground south of the header
# reaches the rest only where the router happens to leave F.Cu open -- and with the lane in
# it did not: UI_SW_PUSH ran a U round the whole east cluster (three F fragments, two B,
# J1.30 and J1.34 in them) and no via site joins it to the main pour on either face
# (searched: 0 sites). So the link is DRAWN, before routing, where no route has used
# B.Cu: from J1.30 up through the gap between pins 29 and 31 into the strip the lane leaves
# north of the header. 0.25 mm in a 0.84 mm gap, 0.295 a side.
BOARD_NOTES["tracks"] += [("GND", "B.Cu", 0.25, [(11.43, -5.77), (12.70, -4.50),
                                                (12.70, -1.20)])]

# THE POWER BUTTON TOOK THIS BOARD TO FOUR LAYERS (2026-10-04). Its two lines are the only
# nets that cross the whole board -- ribbon header at -Y, J4 at +Y -- and they cross it
# through the band the ribbon's own fan already filled. Measured, on two layers: routed
# free, 2 then 3 nets open; drawn by hand down two socket gaps on F.Cu, 3 open and 3
# violations, because two columns on F leave B.Cu as the only layer east-west traffic can
# cross on. The band had been at its limit since the ribbon arrived -- the six hand-placed
# GND bridge vias above are what that looked like. So In2 is a ground plane (which makes
# those bridges redundant rather than load-bearing) and In1 is a second signal layer.


if __name__ == "__main__":
    pi_cap(tag="picap")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "pi_cap.net"))
    netcheck.grounds_meet(os.path.join(OUT_DIR, "pi_cap.net"))
    import volts_decl                   # A16: generated, see volts_decl.py
    volts_decl.into(BOARD_NOTES, "pi_cap")
    with open(os.path.join(OUT_DIR, "pi_cap.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    # ⚠ THE UI WAYS COUNT TOO. This line kept its own copy of the used-pin set and did not
    # learn about the ribbon, so it said 12 while the board was holding 25 of the header's
    # pins. A summary that is computed separately from the thing it summarises drifts the
    # first time the design changes -- so it reads the same UI_WAYS the netlist does.
    _used = (set(PI_5V) | set(PI_GND) | {PI_SCLK, PI_MOSI, PI_SCLK_FOOT, PI_MOSI_FOOT}
             | {h for _s, h in UI_WAYS if h})
    print("board %.1f x %.1f mm, %d of the header's 40 pins used (%d of them the UI ribbon's), "
          "SPI streams continuously (see docstring)"
          % (BOARD_W, BOARD_L, len(_used), len({h for _s, h in UI_WAYS if h})))
