"""Power board — 24 V in, 5 V out to the Pi's GPIO header, x1.

    py -3.12 elec/power.py              # -> elec/out/power.{net,board.json}

WHY THE Pi IS FED FROM GPIO AT ALL. Its USB-C port is the front panel's gadget
port (audio interface + MIDI), so it cannot also be the power inlet. GPIO is the
only other way in -- and on the Pi 4B the USB-C VBUS pin and the GPIO 5 V pins
are THE SAME NODE with no polyfuse between them, so feeding the header skips
every input protection the board has. That is not a reason to avoid it; it is a
reason this board exists, because the protection has to be rebuilt on our side.
(The other half of that node -- a host's VBUS arriving through the panel -- is
broken structurally on elec/usb_panel.py.)

IT DELETES $42.90 OF PURCHASED MODULES. BOM.md carried a Pololu D24V50F5 at
$29.95 for the Pi and a D24V10F5 at $12.95 that existed only to power the Teensy,
which is gone. Both are through-hole modules on 0.1 in headers and neither is an
LCSC line, so they cannot be placed by the assembler -- they become hand-soldered
wiring in the tray, which is the exact thing the connector strategy exists to
delete. And neither has anywhere to put a fuse or a clamp.

IT DROPS INTO THE SLOT THE MODULE ALREADY HAD. BUCK_FP in src/electronics.py is
23 x 36 of tray between the motor controller and the tray's +X edge; 22 x 36
lands inside it, so the tray does not move.

⚠ THE CROWBAR IS THE POINT OF THE BOARD, not the buck. F2 in series with the 5 V
output and D2 (a 5.0 V TVS) across it: if U1 ever fails SHORT, 24 V lands on the
5 V rail and takes the Pi, the OLED, the joystick and everything else on that
header with it. D2 conducts, F2 opens, and the damage stops at a $0.30 part. A
buck without this is a single component failure away from destroying the most
expensive thing in the instrument.

D1 + F1 are the same idea pointed the other way: the 24 V rail is shared with ten
stepper drivers, so it carries switching transients that a bench supply does not.
D1 clamps them before U1 sees them and F1 stops a shorted input from feeding the
fault out of the trunk.

⚠ REFS RUN IN CREATION ORDER, NOT TAG ORDER -- SKiDL numbers a ref_prefix group by
when the parts were instantiated and quietly ignores the tag. The first version of
this file named the OUTPUT crowbar F1/D1 and the INPUT clamp F2/D2, and got the
opposite: the 24 V clamp came out as D1 and was placed at the 5 V end of the board,
24 mm from the rail it exists to clamp. It routed and passed DRC, because the nets
were right and only the geometry was wrong. Numbering now follows the signal path,
so the name and the position cannot disagree again.

REVERSE POLARITY IS HANDLED BY THE CONNECTOR, not by silicon. Both ends are keyed
XH, so neither plug goes in backwards -- which is also why the instrument has one
connector family.
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
PWR = Pin.types.PWRIN

XH_FP = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
# LMR33630: 3.8-36 V in, 3 A, SYNCHRONOUS (no catch diode) in HSOIC-8 with a thermal
# pad. 36 V of absolute maximum against a 24 V rail is 12 V of headroom, which is what
# a rail shared with ten stepper drivers wants -- the 24 V-max parts in this class
# (MP2315, MP2307) have none at all and the 28 V ones (MP1584, TPS54331) have 4.
# ⚠ CONFIRM LCSC STOCK AT ORDER TIME. One board per instrument, so a shortage here
# stops a build.
BUCK_MPN = "LMR33630ADDAR"
BUCK_FP = "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm"

XH_PINOUT = ("GND", "V24", "CAN_H", "CAN_L")     # the instrument's one crimp order


def _r(tag, value, desc):
    return Part(name="R", ref_prefix="R", tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc,
                footprint="Resistor_SMD:R_0402_1005Metric",
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, fp="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _2pin(name, ref_prefix, tag, value, desc, fp):
    return Part(name=name, ref_prefix=ref_prefix, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


@subcircuit
def power():
    gnd = Net("GND")
    v24_in, v24 = Net("+24V_IN"), Net("+24V")
    v5_raw, v5 = Net("+5V_RAW"), Net("+5V")
    sw, boot, vcc, fb, en = (Net("SW"), Net("BOOT"), Net("VCC"),
                             Net("FB"), Net("EN"))
    for n in (gnd, v24_in, v24, v5_raw, v5):
        n.drive = Pin.drives.POWER

    # -- 24 V in, from the trunk tail -----------------------------------------
    # A 4-way in the instrument's standard order with the two CAN cavities EMPTY,
    # exactly as the motor controller's own inlet does it. One crimp order across
    # the whole instrument matters more than saving two contacts.
    j1 = Part(name="B4B-XH-A", ref_prefix="J", tag="J1", dest="NETLIST", tool="skidl",
              value="B4B-XH-A", description="24 V in from the trunk (2 contacts used)",
              footprint=XH_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(XH_PINOUT)])
    gnd += j1[1]
    v24_in += j1[2]

    f1 = _2pin("Fuse", "F", "F1", "1A", "input fuse -- a shorted U1 must not feed "
               "the fault back out into the trunk", "Fuse:Fuse_1206_3216Metric")
    v24_in += f1[1]
    v24 += f1[2]
    d1 = _2pin("D_TVS", "D", "D1", "SMAJ30A", "24 V rail clamp -- the trunk is shared "
               "with ten stepper drivers", "Diode_SMD:D_SMA")
    v24 += d1[1]
    gnd += d1[2]

    # -- U1: 24 -> 5 V, 3 A, synchronous --------------------------------------
    # TI SNVSB78 pinout: 1 VIN, 2 EN, 3 -, 4 FB, 5 GND, 6 SW, 7 BOOT, 8 VCC, 9 EP.
    u1 = Part(name=BUCK_MPN, ref_prefix="U", tag="U1", dest="NETLIST", tool="skidl",
              value=BUCK_MPN, description="36 V 3 A synchronous buck, 24 V -> 5 V",
              footprint=BUCK_FP,
              pins=[Pin(num=1, name="VIN", func=PWR), Pin(num=2, name="EN", func=P),
                    Pin(num=3, name="NC", func=P), Pin(num=4, name="FB", func=P),
                    Pin(num=5, name="GND", func=PWR), Pin(num=6, name="SW", func=P),
                    Pin(num=7, name="BOOT", func=P), Pin(num=8, name="VCC", func=P),
                    Pin(num=9, name="EP", func=PWR)])
    v24 += u1[1]
    en += u1[2]
    fb += u1[4]
    # THE EXPOSED PAD IS THE GROUND CONNECTION, not a mechanical afterthought: it is
    # both the return and the only heat path off the die. It goes to the plane.
    gnd += u1[5], u1[9]
    sw += u1[6]
    boot += u1[7]
    vcc += u1[8]

    c1 = _c("C1", "10uF/50V", "24 V input bulk -- 1206 for the DC-BIAS derating, not "
            "just the voltage rating", "Capacitor_SMD:C_1206_3216Metric")
    c2 = _c("C2", "10uF/50V", "24 V input bulk, second", "Capacitor_SMD:C_1206_3216Metric")
    c3 = _c("C3", "100nF", "input HF bypass -- closest part to VIN/GND")
    for c in (c1, c2, c3):
        v24 += c[1]
        gnd += c[2]
    c4 = _c("C4", "1uF", "VCC bypass")
    vcc += c4[1]
    gnd += c4[2]
    c5 = _c("C5", "100nF", "bootstrap -- BOOT to SW")
    boot += c5[1]
    sw += c5[2]

    l1 = Part(name="L", ref_prefix="L", tag="L1", dest="NETLIST", tool="skidl",
              value="6.8uH", description="buck output inductor, shielded 6x6",
              footprint="Inductor_SMD:L_Bourns-SRN6028",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw += l1[1]
    v5_raw += l1[2]

    c6 = _c("C6", "22uF/16V", "5 V output bulk", "Capacitor_SMD:C_0805_2012Metric")
    c7 = _c("C7", "22uF/16V", "5 V output bulk, second",
            "Capacitor_SMD:C_0805_2012Metric")
    for c in (c6, c7):
        v5_raw += c[1]
        gnd += c[2]
    # Feedback taken from the RAW node, before the fuse: regulating after F1 would put
    # the fuse's resistance inside the loop and let a warm fuse move the rail.
    r1 = _r("R1", "100k", "feedback divider, top")
    r2 = _r("R2", "preset", "feedback divider, bottom -- value set with the part")
    v5_raw += r1[1]
    fb += r1[2], r2[1]
    gnd += r2[2]
    # EN divider: hold the converter off until the 24 V rail is up, so it does not
    # try to start into a sagging supply and chatter.
    r3 = _r("R3", "preset", "EN/UVLO divider, top -- turn-on around 18 V")
    r4 = _r("R4", "preset", "EN/UVLO divider, bottom")
    v24 += r3[1]
    en += r3[2], r4[1]
    gnd += r4[2]

    # -- THE CROWBAR, and then out to the Pi ----------------------------------
    f2 = _2pin("Fuse", "F", "F2", "4A", "5 V output fuse -- the element D2 blows when "
               "U1 fails short", "Fuse:Fuse_1206_3216Metric")
    v5_raw += f2[1]
    v5 += f2[2]
    d2 = _2pin("D_TVS", "D", "D2", "SMBJ5.0A", "THE CROWBAR: clamps the 5 V rail and "
               "draws enough through F2 to open it", "Diode_SMD:D_SMB")
    v5 += d2[1]
    gnd += d2[2]

    # 5 V out on 2 contacts and GND on 2: XH is rated 3 A per contact and the design
    # draw IS 3 A, so a single contact would sit exactly on its rating. Doubling puts
    # each at 1.5 A and costs nothing -- the shell is the same 4-way.
    j2 = Part(name="B4B-XH-A", ref_prefix="J", tag="J2", dest="NETLIST", tool="skidl",
              value="B4B-XH-A", description="5 V to the Pi's GPIO pins 2/4 + 6/9",
              footprint=XH_FP,
              pins=[Pin(num=i + 1, name=n, func=P)
                    for i, n in enumerate(("GND", "+5V", "+5V", "GND"))])
    gnd += j2[1], j2[4]
    v5 += j2[2], j2[3]


# -- the board ---------------------------------------------------------------
# 22 x 36, inside the 23 x 36 the purchased module already occupies in the tray
# (electronics.BUCK_FP), so this drops into its slot rather than moving anything.
#
# FOUR LAYERS on eighteen parts, which looks like overkill and is not: In1.Cu is an
# UNBROKEN ground plane directly under the switching loop. On two layers the return
# path is a pour that the routing carves up, and the one thing a 3 A converter cannot
# have is a return that detours around a track. The extra layers cost pennies at this
# size and buy the only thing that makes the layout forgiving.
#
# The chain runs -Y to +Y: inlet, fuse and clamp, input bulk, the converter, the
# inductor, output bulk, the crowbar, outlet. Nothing doubles back, so the high-di/dt
# loop (C1/C2 - U1 - GND) stays in one place instead of spanning the board.
BOARD_W, BOARD_L = 22.0, 36.0

BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 4,
    "thickness_mm": 1.6,
    "placements": {
        "J1": (0.0, -15.0, 180.0),     # 24 V in, -Y edge
        "F1": (-7.0, -8.5, 0.0),
        "D1": (1.0, -8.5, 0.0),
        "C1": (-7.0, -4.5, 0.0),
        "C2": (-1.5, -4.5, 0.0),
        "C3": (3.0, -4.5, 0.0),        # HF bypass, nearest VIN
        "U1": (-3.0, 0.0, 0.0),
        "L1": (5.5, 0.0, 0.0),
        # the converter's furniture, in a column on the -X edge clear of the loop
        "R1": (-9.0, -2.0, 0.0),
        "R2": (-9.0, -0.5, 0.0),
        "R3": (-9.0, 1.0, 0.0),
        "R4": (-9.0, 2.4, 0.0),
        "C4": (-9.0, 3.6, 0.0),
        "C5": (-9.0, 4.8, 0.0),
        "C6": (-3.0, 6.0, 0.0),
        "C7": (-3.0, 8.5, 0.0),
        "F2": (-7.5, 7.0, 0.0),
        "D2": (4.0, 7.0, 0.0),
        "J2": (0.0, 15.0, 0.0),        # 5 V out, +Y edge
    },
    "ref_pos": {"J1": (0.0, -10.2), "J2": (0.0, 10.2),
                "F1": (-7.0, -10.2), "D1": (1.0, -11.0),
                "C1": (-7.0, -2.6), "C2": (-1.5, -2.6), "C3": (3.0, -2.6),
                "U1": (-3.0, 3.6), "L1": (5.5, 3.9),
                "R1": (-6.0, -2.0), "R2": (-6.0, -0.5), "R3": (-6.0, 1.0),
                "R4": (-6.0, 2.4), "C4": (-6.6, 3.6), "C5": (-6.6, 4.8),
                "C6": (-0.5, 6.0), "C7": (-0.5, 8.5),
                "F2": (-7.5, 9.0), "D2": (4.0, 10.0)},
    # Nineteen designators will not fit the silkscreen of a 22 x 36 that is half
    # connector -- the first pass came back with 14 silk violations and no electrical
    # ones. They go on F.Fab (the assembly drawing, which is what JLCPCB and a human
    # with a schematic both actually read) and the silkscreen stays clean.
    "refs_on_fab": True,
    "zones": [("GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],
    "hold_edge": "+x",
    "no_mounting_holes": True,
    "single_sided": True,
    "qty_per_instrument": 1,
}


if __name__ == "__main__":
    power(tag="pwr")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "power.net"))
    with open(os.path.join(OUT_DIR, "power.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements, x%d per instrument"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]),
             BOARD_NOTES["qty_per_instrument"]))
