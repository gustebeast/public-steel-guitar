"""Front-panel USB break-out — the board that stops a laptop back-feeding the Pi, x1.

    py -3.12 elec/usb_panel.py          # -> elec/out/usb_panel.{net,board.json}

WHY IT EXISTS, and it is one fact: ON THE Pi 4B THE USB-C VBUS PIN AND THE GPIO
5 V PINS ARE THE SAME NODE, with no polyfuse or protection between them. The Pi
has to be powered off the GPIO header, because its USB-C port is spoken for as
the front panel's gadget (audio interface + MIDI) -- and that means the instant
someone plugs a computer into the panel, the computer's VBUS lands directly on
top of our buck's output. Two ~5 V sources hard-paralleled on a rail with no
ORing, no fuse and no clamp.

So VBUS has to be broken, and the choice is WHERE. A cable with VBUS omitted
would do it, and is the wrong answer: it moves a safety property out of the
instrument and into a lead anyone can replace with a normal one, and the failure
is silent until it is not. This board breaks it STRUCTURALLY -- the receptacle's
VBUS pads go nowhere, and no cable can put them back.

WHAT IT IS. Two receptacles and four parts:
  J1  the panel USB-C the player plugs into. 2x 5k1 CC pull-downs so a host still
      sees a sink and enumerates; D+/D- doubled across A6/B6 and A7/B7 so the
      connector stays flippable. Its four VBUS pads are commoned onto a net that
      goes nowhere.
  J2  a USB-A receptacle facing the instrument, VBUS likewise dead-ended, so the
      ~800 mm run to the Pi is a STOCK A-to-C cable. That cable's C plug carries
      its own Rp on CC, so the Pi sees a source attached and no VBUS -- which is
      what it needs. Set `dtoverlay=dwc2,dr_mode=peripheral` so the Pi does not
      sit waiting for VBUS before deciding it is attached.

USB-A AND NOT A SECOND USB-C, deliberately. C-to-C would need our board to
present Rp pull-ups as a source, and Rp pulls up to 5 V -- which is the one thing
this board is built not to have. A-to-C puts that resistor inside the cable's
moulding, where it belongs.

D1/D2 ARE NOT OPTIONAL HERE. This is the one connector on the instrument a
stranger plugs into, so the data pair gets its ESD clamp at the port rather than
600 mm away at the Pi.

IT REPLACES a $7.50 Adafruit 4261 F-F panel coupler -- which would have passed
VBUS straight through, i.e. the part the BOM had would have caused exactly the
fault this board exists to prevent.
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

P = Pin.types.PASSIVE

USBC_FP = "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"
# GCT USB1046: a right-angle USB 2.0 A receptacle, four contacts and a shell. NOT the
# XKB U231-091N first tried here -- that is a USB 3.0 part with NINE contacts, five of
# which would sit on this board doing nothing but inviting a wrong assumption later.
# The link is USB 2.0 by the Pi's own gadget limit, so a 3.0 shell buys nothing.
USBA_FP = "Connector_USB:USB_A_Receptacle_GCT_USB1046"


def _r(tag, value, desc):
    return Part(name="R", ref_prefix="R", tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc,
                footprint="Resistor_SMD:R_0402_1005Metric",
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


@subcircuit
def usb_panel():
    gnd = Net("GND")
    gnd.drive = Pin.drives.POWER
    dp, dm = Net("USB_DP"), Net("USB_DM")

    # -- J1: the panel USB-C --------------------------------------------------
    cpins = ([Pin(num=n, func=P) for n in
              ("A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12",
               "B1", "B4", "B5", "B6", "B7", "B8", "B9", "B12")]
             + [Pin(num="SH", func=P)])
    j1 = Part(name="USB_C_Receptacle", ref_prefix="J", tag="J1", dest="NETLIST",
              tool="skidl", value="TYPE-C-31-M-12",
              description="panel USB-C to the player's computer (LCSC C165948)",
              footprint=USBC_FP, pins=cpins)
    gnd += j1["A1"], j1["A12"], j1["B1"], j1["B12"], j1["SH"]
    # THE WHOLE POINT OF THE BOARD. VBUS's four pads are one pin on the real part,
    # commoned onto a net that goes NOWHERE -- not to J2, not to a rail, not to a
    # sense input. A host will happily put 5 V on them and it will stop here.
    # (They must share a net rather than float: four netless pads read as four
    # separate nets and DRC reports the adjacent ones shorting each other.)
    vbus_panel = Net("VBUS_PANEL_NC")
    vbus_panel += j1["A4"], j1["B4"], j1["A9"], j1["B9"]
    dp += j1["A6"], j1["B6"]
    dm += j1["A7"], j1["B7"]
    # CC pull-downs: without them the host never sees an attachment and never
    # enables its data lines, so the port would be DEAD rather than merely
    # unpowered. 5k1 each, one per CC, which is also what keeps it flippable.
    for tag, pin in (("R1", "A5"), ("R2", "B5")):
        r = _r(tag, "5k1", "USB-C CC pull-down (upstream-facing port)")
        j1[pin] += r[1]
        gnd += r[2]

    # -- J2: the instrument side, a stock A-to-C cable to the Pi ---------------
    j2 = Part(name="USB_A", ref_prefix="J", tag="J2", dest="NETLIST", tool="skidl",
              value="U231-091N-4BLRA00-S",
              description="to the Pi's USB-C, via a stock A-to-C lead",
              footprint=USBA_FP,
              pins=[Pin(num=1, name="VBUS", func=P), Pin(num=2, name="D-", func=P),
                    Pin(num=3, name="D+", func=P), Pin(num=4, name="GND", func=P),
                    Pin(num="SH", name="SHIELD", func=P)])
    # VBUS DEAD-ENDED ON THIS SIDE TOO, for a different reason than J1's: the
    # A-to-C cable has a VBUS conductor whether we like it or not, and leaving pad
    # 1 unconnected is what makes that conductor a dead wire rather than a path
    # from the Pi's rail back out to the panel.
    vbus_pi = Net("VBUS_PI_NC")
    vbus_pi += j2[1]
    dm += j2[2]
    dp += j2[3]
    gnd += j2[4], j2["SH"]

    for tag, net in (("D1", dp), ("D2", dm)):
        d = Part(name="TVS", ref_prefix="D", tag=tag, dest="NETLIST", tool="skidl",
                 value="ESD", description="USB data-line ESD clamp, at the port",
                 footprint="Diode_SMD:D_SOD-523",
                 pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
        net += d[1]
        gnd += d[2]


# -- the board ---------------------------------------------------------------
# Sized off the two receptacles, like the TRRS adapter and unlike the boards that
# read a housing: there is no seat for it yet, so THE MECHANICAL SIDE SHOULD BE
# BUILT TO THESE NUMBERS. The USB-C mouth faces -Y (the panel) and the USB-A +Y
# (into the instrument), so the board is a straight-through and no cable has to
# turn inside the endplate corner.
BOARD_W, BOARD_L = 20.0, 32.0
BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 2,
    "thickness_mm": 1.6,
    # Both mouths sit 0.1 off their edge -- the courtyard's own clearance and no more,
    # for the same reason the TRRS jack does: an inset is reach the plug has to make up
    # through the panel. The four passives share the 5.7 mm band between the two
    # courtyards, which is the only free copper on a board that is two connectors.
    "placements": {
        "J1": (0.0, -8.34, 0.0),       # panel USB-C, mouth -Y at the board edge
        "J2": (0.0, 3.22, 180.0),      # USB-A to the Pi, mouth +Y at the board edge
        "R1": (-6.5, -2.5, 0.0),
        "R2": (-6.5, -4.5, 0.0),
        "D1": (6.5, -2.5, 0.0),
        "D2": (6.5, -4.5, 0.0),
    },
    "ref_pos": {"J1": (0.0, -6.0), "J2": (0.0, -1.0),
                "R1": (-3.2, -2.5), "R2": (-3.2, -4.5),
                "D1": (3.2, -2.5), "D2": (3.2, -4.5)},
    "zones": [("GND", "B.Cu", 0.3)],
    "hold_edge": "+x",
    "no_mounting_holes": True,
    "single_sided": True,
    "qty_per_instrument": 1,
}


if __name__ == "__main__":
    usb_panel(tag="panel")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "usb_panel.net"))
    with open(os.path.join(OUT_DIR, "usb_panel.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements, x%d per instrument"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]),
             BOARD_NOTES["qty_per_instrument"]))
