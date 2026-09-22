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
  * LED strip 5 V, passing through to the strip's own cable so ONE cable reaches the strip.
    ⚠ OPEN: where that 5 V is generated. Not here and not the Pi's rail -- 2.2 A at full
    white. BOM.md carries it as its own buck; this board only passes it on.
  * LED SPI OUT -- SCLK (GPIO 11, pin 23) and MOSI (GPIO 10, pin 19) to the strip.

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
     (GND V5 V5 GND SCK SDI matches the strip's own J_PINS), so the pair has a return
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

BOARD_W, BOARD_L = 56.0, 26.0

XH_FP = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
PH6_FP = "Connector_JST:JST_PH_B6B-PH-K_1x06_P2.00mm_Vertical"
SOCKET_FP = "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical"

# Raspberry Pi 40-way header, PHYSICAL pin numbers -- which is also how the 2x20 footprint
# numbers its pads (1/2 the first pair, odd on one row, even on the other), so the socket's
# pad n IS header pin n and no mapping table is needed.
PI_5V = (2, 4)
PI_GND = (6, 9, 14, 20, 25, 30, 34, 39)
PI_SCLK = 23                      # GPIO 11
PI_MOSI = 19                      # GPIO 10
SERIES_R = "68R"                  # see note 1 in the docstring

# The strip's cable. SAME ORDER as led_strip.J_PINS -- one crimp order, and GND lands on
# both ends of the row so each signal has a return beside it (note 3).
STRIP_PINS = ("GND", "V5", "V5", "GND", "SCK", "SDI")


def _r(tag, value, desc):
    return Part(name="R", ref_prefix="R", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint="Resistor_SMD:R_0402_1005Metric",
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, fp="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _xh(tag, desc):
    return Part(name="B4B-XH-A", ref_prefix="J", ref=tag, tag=tag, dest="NETLIST",
                tool="skidl", value="B4B-XH-A", description=desc, footprint=XH_FP,
                pins=[Pin(num=i + 1, name=n, func=P)
                      for i, n in enumerate(("GND", "V5", "V5", "GND"))])


@subcircuit
def pi_cap():
    gnd = Net("GND")
    gnd.drive = Pin.drives.POWER
    v5_pi, v5_led = Net("+5V_PI"), Net("+5V_LED")
    for n in (v5_pi, v5_led):
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
    used = set(PI_5V) | set(PI_GND) | {PI_SCLK, PI_MOSI}
    for n in range(1, 41):
        if n not in used:
            Net("PI_NC_%d" % n).connect(j1[n])

    j2 = _xh("J2", "Pi 5 V in, from motor_ctrl J5 (GPIO pins 2/4 + 6/9)")
    gnd += j2[1], j2[4]
    v5_pi += j2[2], j2[3]

    j4 = _xh("J4", "LED strip 5 V in, from the strip's own buck -- NOT the Pi's rail")
    gnd += j4[1], j4[4]
    v5_led += j4[2], j4[3]

    # the one cable to the strip: power and both signals, in led_strip.J_PINS order
    j3 = Part(name="B6B-PH-K-S", ref_prefix="J", ref="J3", tag="J3", dest="NETLIST",
              tool="skidl", value="B6B-PH-K-S",
              description="to the LED strip's section 1 -- 5 V and SPI, LCSC C131342",
              footprint=PH6_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(STRIP_PINS)])
    gnd += j3[1], j3[4]
    v5_led += j3[2], j3[3]

    sck, sdi = Net("SCK"), Net("SDI")
    r1 = _r("R1", SERIES_R, "SCLK series source termination (see docstring note 1)")
    sck_pi += r1[1]
    sck += r1[2], j3[5]
    r2 = _r("R2", SERIES_R, "MOSI series source termination (see docstring note 1)")
    sdi_pi += r2[1]
    sdi += r2[2], j3[6]

    for tag, net, what in (("C1", v5_pi, "Pi 5 V bulk at the header"),
                           ("C2", v5_led, "LED 5 V bulk -- 2.2 A of strip starts here")):
        c = _c(tag, "22uF/16V", what, "Capacitor_SMD:C_0805_2012Metric")
        net += c[1]
        gnd += c[2]
    for tag, net, what in (("C3", v5_pi, "Pi 5 V HF bypass"),
                           ("C4", v5_led, "LED 5 V HF bypass")):
        c = _c(tag, "100nF", what)
        net += c[1]
        gnd += c[2]


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
        "J1": (0.00, -8.50, 90.0),   # 4.5 from the board edge = the Pi header's own margin
        # the three connectors are 13.5 wide in courtyard and the board is 56: they tile
        # -26.75..15.5 with the requested x at each courtyard's CENTRE
        "J2": (-20.00, 8.00, 0.0),      # Pi 5 V in
        "J4": (-6.00, 8.00, 0.0),       # LED 5 V in
        "J3": (9.00, 8.00, 0.0),        # out to the strip (J4 ends at 0.75; this starts 1.5)
        # passives in their own row, spaced so each GND pad keeps its stitching-via room
        "C1": (-20.00, 1.50, 0.0),
        "C3": (-15.00, 1.50, 0.0),
        "C2": (-6.00, 1.50, 0.0),
        "C4": (20.00, -1.00, 0.0),
        "R1": (5.00, 1.50, 0.0),
        "R2": (8.00, 1.50, 0.0),
    },
    # ⚠ THE SOCKET'S GROUND PADS TAKE NO STITCHING VIA, AND DO NOT NEED ONE. The check
    # exists because an SMD pad touching only a pour can be orphaned when routing carves
    # the pour up. These are PLATED THROUGH-HOLE pads: the barrel already spans F.Cu and
    # B.Cu, so each one IS its own via and reaches both pours by construction. There is no
    # room beside them either -- 2.54 mm pitch leaves ~0.8 mm between pads, under a 0.6 mm
    # via plus clearance -- so the check can only ever fail here.
    "stitch_exceptions": tuple("J1.%d" % n for n in (6, 9, 14, 20, 25, 30, 34, 39)),
    # GND pour on both layers: this board carries up to 3 A to the Pi and 2.2 A to the
    # strip, and the return for both shares it.
    "zones": [("GND", "F.Cu", 0.3), ("GND", "B.Cu", 0.3)],
    "stitch_nets": ("GND",),
    "router_passes": 12,
    # ⚠ THE SOCKET IS ON THE BACK, and that is the whole mechanical idea: its body is the
    # standoff the cap hangs off the Pi's header by. Mounted on the front it would be a
    # bump on top of the board with nothing holding the board on.
    "back_refs": ("J1",),
    "single_sided": False,          # the 2x20 socket is through-hole, and on the far side
    "qty_per_instrument": 1,
}


if __name__ == "__main__":
    pi_cap(tag="picap")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "pi_cap.net"))
    netcheck.grounds_meet(os.path.join(OUT_DIR, "pi_cap.net"))
    with open(os.path.join(OUT_DIR, "pi_cap.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d GPIO pins used of 40, SPI streams continuously (see docstring)"
          % (BOARD_W, BOARD_L, len(set(PI_5V) | set(PI_GND) | {PI_SCLK, PI_MOSI})))
