"""Output + panel board — every front-panel connection on one PCB, x1.

    py -3.12 elec/output_panel.py       # -> elec/out/output_panel.{net,board.json}

IT IS THE MERGE of two boards that wanted to be one (user, 2026-09-15): the USB
break-out that stops a laptop back-feeding the Pi, and the analog OUTPUT STAGE
that would not fit on the optical pickup board. They belong together because they
are both "the front panel", and because putting the output stage here is what
lets the TS jack be a BOARD part instead of a hand-soldered one.

⚠ THE TS JACK BEING ON THE BOARD FIXES A RULE VIOLATION, it does not add a part.
BOM.md already specifies a Neutrik NMJ4HCD2, and that jack is a PCB-MOUNT part
with a panel bushing -- KiCad ships its footprint. Mounted as the CAD had it, its
lugs would have been hand-soldered, which the project forbids outside a
factory-assembled board. Same part number, same price, and the last hand-soldered
joint in the instrument disappears. Its nut clamps the endplate, so the PANEL
takes the cable-yank load rather than the PCB.

WHAT CROSSES FROM THE OPTICAL BOARD (J3, one 8-way): the Pi's processed audio
arrives there over USB and leaves as I2S, the magnetic pickup's buffered tap
comes along for the direct path, plus 5 V and one relay control line. THE PIN
ORDER IS A CROSSTALK DECISION: AUDIO sits at one end with its own return and the
POWER PAIR between it and the clocks, so the I2S edges never run beside the
analog pair.
    1 AGND   2 AUDIO   3 GND   4 +5V   5 BCK   6 LRCK   7 DIN   8 RELAY

K1 IS "DIRECT MODE" AND IT IS DE-ENERGISED THERE. With no power, no Pi and no
firmware the magnetic pickup reaches the jack through a mechanical contact, so
the instrument is still a guitar when everything clever about it is off.

⚠ AND IT IS NOT LATCHING, WHICH CORRECTS ME. I wrote on the optical board that
latching was required because "a held coil hums at the audio it is switching".
That is wrong: the coil is driven with DC, and a static magnetic field does not
hum. The real cost of a held coil is ~30 mA, which this rail has. A non-latching
relay also needs ONE control line instead of two, which is what keeps J3 at the
instrument's standard 8-way instead of growing it.

R3/C1/D4 ARE THE PHANTOM-POWER PROTECTION. If someone reaches a combo TRS/XLR
input with phantom on, +48 V arrives through 6.81k on the tip. C1 blocks the DC
outright (100 V rated -- it sits charged to 48 V for the duration, so that is the
RATING, not margin), R3 bounds the fault current and C1's inrush, and D4 catches
the insertion edge a DC block passes straight through. Roughly $0.05, and
impossible to add later.
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
USBA_FP = "Connector_USB:USB_A_Receptacle_GCT_USB1046"
PH_FP = "Connector_JST:JST_PH_S8B-PH-SM4-TB_1x08-1MP_P2.00mm_Horizontal"
TS_FP = "Connector_Audio:Jack_6.35mm_Neutrik_NMJ4HCD2_Horizontal"
# DPDT signal relay, 5 V coil. Only ONE pole switches audio (the tip); an
# unbalanced output has nothing for the second pole to do, and a DPDT in this
# package is what is stocked.
RELAY_FP = "Relay_SMD:Relay_DPDT_FRT5_SMD"
DAC_FP = "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm"


def _r(tag, value, desc, fp="Resistor_SMD:R_0402_1005Metric"):
    return Part(name="R", ref_prefix="R", tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, fp="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _d(tag, value, desc):
    return Part(name="D", ref_prefix="D", tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint="Diode_SMD:D_SOD-523",
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


@subcircuit
def output_panel():
    gnd, agnd, v5 = Net("GND"), Net("AGND"), Net("+5V")
    for n in (gnd, agnd, v5):
        n.drive = Pin.drives.POWER
    dp, dm = Net("USB_DP"), Net("USB_DM")
    bck, lrck, din, relay = Net("I2S_BCK"), Net("I2S_LRCK"), Net("I2S_DIN"), Net("RELAY")
    raw, proc = Net("AUDIO_RAW"), Net("AUDIO_PROC")
    sel, outp = Net("AUDIO_SEL"), Net("JACK_TIP")

    # -- J1: the panel USB-C, VBUS DEAD-ENDED -------------------------------
    cpins = ([Pin(num=n, func=P) for n in
              ("A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12",
               "B1", "B4", "B5", "B6", "B7", "B8", "B9", "B12")]
             + [Pin(num="SH", func=P)])
    j1 = Part(name="USB_C_Receptacle", ref_prefix="J", tag="J1", dest="NETLIST",
              tool="skidl", value="TYPE-C-31-M-12",
              description="panel USB-C to the player's computer (LCSC C165948)",
              footprint=USBC_FP, pins=cpins)
    gnd += j1["A1"], j1["A12"], j1["B1"], j1["B12"], j1["SH"]
    # The reason the USB half of this board exists: on the Pi 4B the USB-C VBUS pin
    # and the GPIO 5 V pins are THE SAME NODE with no polyfuse between them, and the
    # Pi is fed from its GPIO header. A host's VBUS would land straight on the power
    # board's output. It stops here, structurally, where no cable can undo it.
    vbus_panel = Net("VBUS_PANEL_NC")
    vbus_panel += j1["A4"], j1["B4"], j1["A9"], j1["B9"]
    dp += j1["A6"], j1["B6"]
    dm += j1["A7"], j1["B7"]
    for tag, pin in (("R1", "A5"), ("R2", "B5")):
        r = _r(tag, "5k1", "USB-C CC pull-down (upstream-facing port)")
        j1[pin] += r[1]
        gnd += r[2]

    # -- J2: USB-A, so the run to the Pi is a stock A-to-C lead --------------
    j2 = Part(name="USB_A", ref_prefix="J", tag="J2", dest="NETLIST", tool="skidl",
              value="USB1046-GF-0180", description="to the Pi's USB-C, via an A-to-C lead",
              footprint=USBA_FP,
              pins=[Pin(num=1, name="VBUS", func=P), Pin(num=2, name="D-", func=P),
                    Pin(num=3, name="D+", func=P), Pin(num=4, name="GND", func=P),
                    Pin(num="SH", name="SHIELD", func=P)])
    vbus_pi = Net("VBUS_PI_NC")
    vbus_pi += j2[1]                      # the lead's VBUS conductor ends here, dead
    dm += j2[2]
    dp += j2[3]
    gnd += j2[4], j2["SH"]
    for tag, net in (("D1", dp), ("D2", dm)):
        d = _d(tag, "ESD", "USB data-line ESD clamp, at the port")
        net += d[1]
        gnd += d[2]

    # -- J3: the link to the optical board -----------------------------------
    j3 = Part(name="S8B-PH-SM4-TB", ref_prefix="J", tag="J3", dest="NETLIST",
              tool="skidl", value="S8B-PH-SM4-TB",
              description="optical board: audio + I2S + 5V + relay (LCSC C265121)",
              footprint=PH_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(
                  ("AGND", "AUDIO", "GND", "+5V", "BCK", "LRCK", "DIN", "RELAY"))])
    agnd += j3[1]
    raw += j3[2]
    gnd += j3[3]
    v5 += j3[4]
    bck += j3[5]
    lrck += j3[6]
    din += j3[7]
    relay += j3[8]

    # -- U1: the DAC, the Pi's return path made analog again -----------------
    u1 = Part(name="DAC_I2S", ref_prefix="U", tag="U1", dest="NETLIST", tool="skidl",
              value="PCM5102A-class", description="I2S stereo DAC, TSSOP-20",
              footprint=DAC_FP,
              pins=[Pin(num=1, name="LRCK", func=P), Pin(num=2, name="DIN", func=P),
                    Pin(num=3, name="BCK", func=P), Pin(num=4, name="DGND", func=P),
                    Pin(num=5, name="DVDD", func=P), Pin(num=6, name="AVDD", func=P),
                    Pin(num=7, name="AGND", func=P), Pin(num=8, name="OUTL", func=P),
                    Pin(num=9, name="OUTR", func=P), Pin(num=10, name="XSMT", func=P)]
                   + [Pin(num=i, func=P) for i in range(11, 21)])
    lrck += u1[1]
    din += u1[2]
    bck += u1[3]
    gnd += u1[4]
    v5 += u1[5], u1[6], u1[10]            # XSMT tied high: un-mute
    agnd += u1[7]
    # Mono output: the instrument has one jack, so the DAC's left channel is the one
    # that goes anywhere. OUTR is left unconnected ON PURPOSE rather than summed --
    # summing two op-amp outputs through a resistor pair is a way to make a mono
    # signal quieter and no way to make it better.
    proc_pre = Net("DAC_OUT_L")
    proc_pre += u1[8]
    dac_r_nc = Net("DAC_OUT_R_NC")
    dac_r_nc += u1[9]
    # ⚠ REFS ARE ASSIGNED IN CREATION ORDER, NOT BY TAG -- SKiDL ignores the tag for
    # numbering. The first draft named these by role and got a shuffle: the 100 V
    # OUTPUT DC BLOCK came out as C6 while C1 was a 1 nF filter, so the placement put
    # a 1210 part where an 0402 was drawn. Numbering now follows the order the parts
    # are built in, which is the only order SKiDL respects.
    r3 = _r("R3", "470R", "DAC output filter, with C1")
    proc_pre += r3[1]
    proc += r3[2]
    c1 = _c("C1", "1nF", "DAC output filter -- corner well above audio")
    proc += c1[1]
    agnd += c1[2]
    for tag, val, net, fp in (("C2", "10uF", v5, "Capacitor_SMD:C_0805_2012Metric"),
                              ("C3", "100nF", v5, "Capacitor_SMD:C_0402_1005Metric"),
                              ("C4", "100nF", v5, "Capacitor_SMD:C_0402_1005Metric")):
        c = _c(tag, val, "DAC supply bypass", fp)
        net += c[1]
        agnd += c[2] if tag == "C2" else c[2]

    # -- K1: direct vs processed, de-energised = direct ----------------------
    k1 = Part(name="RELAY_DPDT", ref_prefix="K", tag="K1", dest="NETLIST", tool="skidl",
              value="FRT5-class 5V", description="true-bypass select; DE-ENERGISED = DIRECT",
              footprint=RELAY_FP,
              pins=[Pin(num=i, func=P) for i in range(1, 11)])
    # 1/10 coil, 2 common, 3 NC (direct), 4 NO (processed) on the pole in use.
    v5 += k1[1]
    coil = Net("RELAY_COIL")
    coil += k1[10]
    sel += k1[2]
    raw += k1[3]
    proc += k1[4]
    for i in (5, 6, 7, 8, 9):
        n = Net("K1_UNUSED_%d" % i)
        n += k1[i]
    q1 = Part(name="Q_NMOS", ref_prefix="Q", tag="Q1", dest="NETLIST", tool="skidl",
              value="AO3400A", description="relay coil driver (already on the optical board)",
              footprint="Package_TO_SOT_SMD:SOT-23",
              pins=[Pin(num=1, name="G", func=P), Pin(num=2, name="S", func=P),
                    Pin(num=3, name="D", func=P)])
    r4 = _r("R4", "100R", "relay gate series")
    relay += r4[1]
    r4[2] += q1[1]
    gnd += q1[2]
    coil += q1[3]
    d3 = _d("D3", "flyback", "coil flyback -- the coil is an inductor and the FET is not")
    coil += d3[1]
    v5 += d3[2]

    # -- U2: the buffer, then the phantom guard, then the jack ---------------
    u2 = Part(name="OPAMP", ref_prefix="U", tag="U2", dest="NETLIST", tool="skidl",
              value="single RRO op-amp", description="output buffer -- drives the TS jack",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                    Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                    Pin(num=5, name="V+", func=P)])
    buf = Net("BUF_OUT")
    sel += u2[3]
    buf += u2[1], u2[4]                   # unity-gain follower
    agnd += u2[2]
    v5 += u2[5]
    c5 = _c("C5", "100nF", "buffer supply bypass")
    v5 += c5[1]
    agnd += c5[2]
    r5 = _r("R5", "1M", "buffer input bias to AGND -- the relay's NC path is floating "
            "until a pickup is connected")
    sel += r5[1]
    agnd += r5[2]
    r6 = _r("R6", "100k", "output bleed -- stops the DC block thumping on unplug")

    r7 = _r("R7", "220R", "output series -- bounds a phantom-power fault and C6's inrush")
    buf += r7[1]
    blocked = Net("OUT_BLOCKED")
    blocked += r7[2]
    c6 = _c("C6", "2.2uF/100V", "OUTPUT DC BLOCK -- phantom guard, see the header",
            "Capacitor_SMD:C_1210_3225Metric")
    blocked += c6[1]
    outp += c6[2]
    outp += r6[1]
    agnd += r6[2]
    d4 = _d("D4", "bidir clamp", "catches the insertion edge C1 passes through")
    blocked += d4[1]
    agnd += d4[2]

    j4 = Part(name="NMJ4HCD2", ref_prefix="J", tag="J4", dest="NETLIST", tool="skidl",
              value="NMJ4HCD2", description="1/4 in TS output jack, PCB mount, panel bushing",
              footprint=TS_FP,
              pins=[Pin(num="T", name="TIP", func=P), Pin(num="TN", name="TIP_N", func=P),
                    Pin(num="S", name="SLEEVE", func=P), Pin(num="SN", name="SLEEVE_N", func=P)])
    outp += j4["T"]
    agnd += j4["S"]
    # The switched contacts are brought to AGND rather than left floating: an open
    # switch lug beside an audio contact is an antenna, and nothing here needs to
    # sense whether a plug is in.
    agnd += j4["TN"], j4["SN"]


# -- the board ---------------------------------------------------------------
# ⚠ THE OUTLINE IS AN OUTPUT and the MECHANICAL SIDE SHOULD BE BUILT TO IT, like
# the TRRS adapter. It lies FLAT in the bridge endplate's open -Y corner with the
# panel connectors along +X. The TS jack alone is 27.62 x 20.32 of courtyard, which
# is what sets the size -- 1/4 inch jacks are big.
#
# ⚠ TWO THINGS THE ENDPLATE HAS TO ABSORB, both for branner:
#   1. THE PANEL HOLES ARE NO LONGER IN ONE ROW AT ONE HEIGHT. A TS jack's axis and
#      a USB-C's axis sit at different heights above the board they share, so the
#      two holes differ in Z by that much. Their Y positions are now set by this
#      board's geometry, not by the old 18 mm pitch.
#   2. THE DC BARREL JACK SHOULD LEAVE THIS BOARD'S SPAN. It is the 24 V inlet for
#      ten stepper drivers, and it currently sits at y -86, between the TS jack and
#      the USB-C. Bringing the motor supply onto the same board as the output buffer
#      is asking for exactly the noise the rest of this design works to avoid. Move
#      it to the far end of the panel row.
BOARD_W, BOARD_L = 52.0, 48.0

BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 4,
    "thickness_mm": 1.6,
    # FOUR LAYERS because this board carries an audio output stage and a USB pair
    # over the same copper. In1.Cu is an unbroken ground plane under both: it is
    # what gives the analog side a quiet reference and the USB pair a defined
    # impedance, and neither is negotiable on a board whose whole job is the signal
    # a listener actually hears.
    # THE TS JACK IS AT +Y AND THE USB-C AT -Y, which is not arbitrary: the panel row
    # already runs TS at the +Y end and USB at the -Y end, and a board whose connectors
    # come out in the other order would have to be posed upside down to match it.
    "placements": {
        "J4": (12.01, 13.24, 0.0),
        "J1": (18.34, -18.03, 90.0),
        "J2": (-17.61, 10.72, 180.0),
        "J3": (-14.76, -19.95, 180.0),
        "K1": (-18.00, -1.50, 0.0),
        "U1": (-4.00, -4.50, 0.0),
        "U2": (6.00, -4.00, 0.0),
        "Q1": (11.00, -4.00, 0.0),
        "C2": (-9.00, -10.20, 0.0),
        "C3": (-5.50, -10.20, 0.0),
        "C4": (-3.00, -10.20, 0.0),
        "C1": (-0.50, -10.20, 0.0),
        "R3": (2.00, -10.20, 0.0),
        "C5": (4.50, -10.20, 0.0),
        "R5": (-9.00, 1.20, 0.0),
        "R4": (-6.50, 1.20, 0.0),
        "R7": (-4.00, 1.20, 0.0),
        "R6": (-1.50, 1.20, 0.0),
        "C6": (2.50, 1.20, 0.0),
        "D4": (6.50, 1.20, 0.0),
        "D3": (9.50, 1.20, 0.0),
        "R1": (12.00, -21.00, 0.0),
        "R2": (12.00, -19.00, 0.0),
        "D1": (12.00, -17.00, 0.0),
        "D2": (12.00, -15.00, 0.0),
    },
    "refs_on_fab": True,
    "zones": [("GND", "In1.Cu", 0.3), ("AGND", "B.Cu", 0.3)],
    "hold_edge": "-x",
    "no_mounting_holes": True,
    "single_sided": True,
    "qty_per_instrument": 1,
}


if __name__ == "__main__":
    output_panel(tag="panel")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "output_panel.net"))
    with open(os.path.join(OUT_DIR, "output_panel.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements, x%d per instrument"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]),
             BOARD_NOTES["qty_per_instrument"]))
