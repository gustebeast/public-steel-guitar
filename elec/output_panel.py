"""Output + panel board — the front panel, both audio conversions, and a hub. x1.

    py -3.12 elec/output_panel.py       # -> elec/out/output_panel.{net,board.json}

EVERYTHING THE PLAYER TOUCHES IS ON THIS BOARD: the 1/4 in jack, the panel USB-C,
the 24 V inlet, and the magnetic pickup's screw terminals. Everything the audio
path needs is here too, which is the point of the 2026-09-15 respin -- NO ANALOG
SIGNAL CROSSES THE INSTRUMENT ANY MORE. The pickup lands here, is converted here,
comes back from the Pi here, and leaves here.

⚠ THE MAGNETIC PICKUP LANDS HERE, NOT ON THE OPTICAL BOARD (user). That is what
deletes the link between the two boards entirely: with the ADC and the DAC both
on this board nothing has to cross, the 8-way PH that used to carry audio + I2S +
5 V + relay is GONE, and the optical board's -Y edge goes back to its own USB and
its own power. It also puts DIRECT MODE wholly on one PCB -- pickup, buffer,
relay, jack -- so the instrument plays with no Pi, no firmware and no cable in
the path.

⚠ AND IT COSTS A SWITCHER ON THE AUDIO BOARD, which is worth saying plainly
because the rest of this design works to avoid exactly that. With the link gone
there is no 5 V arriving from anywhere, so U5 makes it from the 24 V that was
already coming in at J6. The defence is distance and partition: the inlet, the
buck and the trunk connector share the -Y corner on their own copper, the analog
chain sits along the +Y edge as far away as the board allows, and the 5 V rail
crosses between them through a bead (FB1) rather than a wire. The SIGNAL ground is
one plane, not two -- see the one-ground note in output_panel().

USB, AND THERE ARE THREE SEPARATE PATHS -- worth reading before touching any of
them, because they look alike and are not:
  1. J1 -> J2 is a PASS-THROUGH and nothing else. The player's computer reaches
     the Pi's USB-C gadget port through it; this board is wire. VBUS is dead at
     BOTH ends -- on the Pi 4B the USB-C VBUS pin and the GPIO 5 V pins are the
     same node with no polyfuse between, so a host's VBUS would land straight on
     the motor controller's 5 V output.
  2. J3 is the HUB's upstream, to a Pi USB-A host port.
  3. J4 is a hub DOWNSTREAM, to the optical board ~100 mm away. That is the whole
     point of carrying a hub: the optical board's 480 Mbps link stops being an
     800 mm cable back to the keyhead and becomes a short one to here.

⚠ U1 IS HIGH SPEED VIA ITS INTERNAL PHY, AND THAT IS WHY IT IS A CH32V307.
Datasheet (CH32V303/305/307/317, V3.9): "built-in USB2.0 high-speed PHY
transceivers (480Mbps)", USBHS_DM = PB6 = QFN-68 pin 61, USBHS_DP = PB7 = pin 62.
No external ULPI PHY, unlike the optical board. A FULL-SPEED part would sit
behind the hub's Transaction Translator and pay ~1 ms for it; a high-speed one is
REPEATED instead, so the hub adds no store-and-forward delay to either device.
Same MCU as the motor controller, so no new SKU. (The datasheet notes DVP_D5 and
FSMC_NADV default-map to PB6/PB7 and auto-remap away once USBHSEN is set. This
board enables neither peripheral, so the conflict cannot arise.)

WHY AN MCU AT ALL, INSTEAD OF A $2 USB CODEC: the converter sets the noise floor,
not the word length. The PCM1808 is 24-bit AND 99 dB, where 16 bit's THEORETICAL
ceiling is 98.1 -- about 10 dB of real floor over a CM108-class codec, on the one
signal a listener actually hears.

THE Pi SUMS STEREO TO MONO IN SOFTWARE for the jack (user): it already decides
what to send here, so summing there stays flexible -- a mono fold-down for the
jack while the computer gets full stereo over the gadget -- where a resistor pair
into the buffer would have frozen one fixed relationship in hardware.
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
TS_FP = "Connector_Audio:Jack_6.35mm_Neutrik_NMJ4HCD2_Horizontal"
# PJ-102AH: the PCB-MOUNT sibling of the PJ-005A the BOM already specifies -- same
# Same Sky/CUI family, same 2.0 mm pin, but board pins instead of solder lugs.
DC_FP = "Connector_BarrelJack:BarrelJack_CUI_PJ-102AH_Horizontal"
XH_FP = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
TERM_FP = "TerminalBlock:TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm"
MCU_FP = "Package_DFN_QFN:QFN-68-1EP_8x8mm_P0.4mm_EP5.2x5.2mm"
ADC_FP = "Package_SO:TSSOP-16_4.4x5mm_P0.65mm"
DAC_FP = "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm"
HUB_FP = "Package_DFN_QFN:HVQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm"
# DPDT signal relay, 5 V coil. Only ONE pole switches audio (the tip); an
# unbalanced output has nothing for the second pole to do, and a DPDT in this
# package is what is stocked.
RELAY_FP = "Relay_SMD:Relay_DPDT_FRT5_SMD"


def _r(tag, value, desc, fp="Resistor_SMD:R_0402_1005Metric"):
    return Part(name="R", ref_prefix="R", tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, fp="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _d(tag, value, desc, fp="Diode_SMD:D_SOD-523"):
    return Part(name="D", ref_prefix="D", tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _usbc(tag, desc):
    pins = ([Pin(num=n, func=P) for n in
             ("A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12",
              "B1", "B4", "B5", "B6", "B7", "B8", "B9", "B12")]
            + [Pin(num="SH", func=P)])
    return Part(name="USB_C_Receptacle", ref_prefix="J", tag=tag, dest="NETLIST",
                tool="skidl", value="TYPE-C-31-M-12", description=desc,
                footprint=USBC_FP, pins=pins)


def _usba(tag, desc):
    return Part(name="USB_A", ref_prefix="J", tag=tag, dest="NETLIST", tool="skidl",
                value="USB1046-GF-0180", description=desc, footprint=USBA_FP,
                pins=[Pin(num=1, name="VBUS", func=P), Pin(num=2, name="D-", func=P),
                      Pin(num=3, name="D+", func=P), Pin(num=4, name="GND", func=P),
                      Pin(num="SH", name="SHIELD", func=P)])


@subcircuit
def output_panel():
    # ⚠ EVERY PART BELOW IS CREATED IN THE ORDER ITS REF SHOULD TAKE. SKiDL numbers
    # a ref_prefix group by CREATION order and IGNORES the tag, so building a part
    # where it belongs logically rather than where it belongs numerically is how the
    # previous draft got a 1210 DC block called C6 sitting in an 0402's placement.
    # If you add a part, add it at the position its number implies.
    # ⚠ ONE SIGNAL GROUND, WHICH REVERSES WHAT I DID FIRST. The first draft split
    # GND (digital, In1.Cu) from AGND (analog, B.Cu) and kept the converters'
    # digital pins on GND. That is the split-plane habit, and it is wrong for
    # exactly these parts: TI's guidance for the PCM1808 and PCM5102 is a SINGLE
    # unbroken ground under both, with the analog and digital sections separated by
    # PLACEMENT rather than by a cut in the copper -- which is what the +Y/-Y band
    # floorplan already does. A split plane's return current does not vanish; it
    # detours to wherever the two halves meet, and that detour is a loop.
    #
    # The router found it before I did. Five of the converters' ground pins sat in
    # the analog band with their plane 50 mm away at the other end of the board, and
    # every routing attempt left GND stubs and dangling vias there -- not a router
    # defect but the netlist asking for something the floorplan could not give.
    #
    # ⚠ PWR_GND IS STILL SEPARATE AND THAT IS THE SPLIT THAT MATTERS. The 24 V
    # return feeds ten stepper drivers and is chopped at their switching rate; it
    # keeps its own island and meets this ground at the instrument's star point.
    gnd = Net("GND")
    agnd = gnd
    v5, v3v3 = Net("+5V"), Net("+3V3")
    v24, pgnd = Net("+24V"), Net("PWR_GND")
    for n in (gnd, v5, v3v3, v24, pgnd):
        n.drive = Pin.drives.POWER

    # ── J1/J2: the gadget PASS-THROUGH. This board is wire. ──────────────────
    thru_dp, thru_dm = Net("THRU_DP"), Net("THRU_DM")
    j1 = _usbc("J1", "panel USB-C to the player's computer (LCSC C165948)")
    gnd += j1["A1"], j1["A12"], j1["B1"], j1["B12"], j1["SH"]
    # The reason this path exists at all: on the Pi 4B the USB-C VBUS pin and the
    # GPIO 5 V pins are THE SAME NODE with no polyfuse between them, and the Pi is
    # fed from its GPIO header. A host's VBUS would land straight on the motor
    # controller's 5 V output. It stops here, structurally, where no cable can
    # undo it.
    vbus_panel = Net("VBUS_PANEL_NC")
    vbus_panel += j1["A4"], j1["B4"], j1["A9"], j1["B9"]
    thru_dp += j1["A6"], j1["B6"]
    thru_dm += j1["A7"], j1["B7"]

    j2 = _usba("J2", "to the Pi's USB-C gadget port, via a stock A-to-C lead")
    vbus_pi = Net("VBUS_PI_NC")
    vbus_pi += j2[1]                      # the lead's VBUS conductor ends here, dead
    thru_dm += j2[2]
    thru_dp += j2[3]
    gnd += j2[4], j2["SH"]

    # ── J3/J4: the hub's upstream, and the optical board's downstream ────────
    hub_dn1_dp, hub_dn1_dm = Net("HUB_DN1_DP"), Net("HUB_DN1_DM")   # -> U1, no cable
    hub_dn2_dp, hub_dn2_dm = Net("HUB_DN2_DP"), Net("HUB_DN2_DM")   # -> J4 -> optical
    hub_up_dp, hub_up_dm = Net("HUB_UP_DP"), Net("HUB_UP_DM")
    j3 = _usbc("J3", "hub upstream -> a Pi USB-A host port")
    gnd += j3["A1"], j3["A12"], j3["B1"], j3["B12"], j3["SH"]
    # VBUS dead here too, and for the same reason as J1: the Pi's host ports share
    # the 5 V node. This board is self-powered off the 24 V trunk and never wants
    # the Pi's rail.
    vbus_up = Net("VBUS_UP_NC")
    vbus_up += j3["A4"], j3["B4"], j3["A9"], j3["B9"]
    hub_up_dp += j3["A6"], j3["B6"]
    hub_up_dm += j3["A7"], j3["B7"]

    j4 = _usba("J4", "hub downstream -> the optical board, ~100 mm")
    # ⚠ THIS one DOES source VBUS -- it is a host port. The optical board runs off
    # its own 24 V and ignores the current, but a device that is not OFFERED VBUS
    # never enumerates, so the pin is fed rather than dead-ended.
    v5 += j4[1]
    hub_dn2_dm += j4[2]
    hub_dn2_dp += j4[3]
    gnd += j4[4], j4["SH"]

    # ── J5: the 1/4 in jack. PCB-MOUNT, so no hand-soldered lug. ─────────────
    # BOM.md already specifies this Neutrik; it is a PCB part with a panel bushing,
    # and mounting it as a free-floating panel jack was what implied hand-soldered
    # lugs. Its nut clamps the endplate, so the PANEL takes the cable-yank load
    # rather than the PCB.
    outp = Net("JACK_TIP")
    j5 = Part(name="NMJ4HCD2", ref_prefix="J", tag="J5", dest="NETLIST", tool="skidl",
              value="NMJ4HCD2", description="1/4 in TS output, PCB mount, panel bushing",
              footprint=TS_FP,
              pins=[Pin(num="T", name="TIP", func=P), Pin(num="TN", name="TIP_N", func=P),
                    Pin(num="S", name="SLEEVE", func=P), Pin(num="SN", name="SLEEVE_N", func=P)])
    outp += j5["T"]
    # The switched contacts go to ground rather than floating: an open switch lug
    # beside an audio contact is an antenna, and nothing here needs to sense a plug.
    agnd += j5["S"], j5["TN"], j5["SN"]

    # ── J6/J7: the 24 V inlet, crossing its own corner ───────────────────────
    # ⚠ PWR_GND IS A SEPARATE NET AND IS NEVER JOINED TO THE SIGNAL GROUND HERE. The
    # trunk feeds ten stepper drivers and its return current is chopped at their
    # switching rate; sharing a plane with the audio reference would put that
    # current under the one signal a listener hears. The two meet at the
    # instrument's star point, elsewhere.
    # ⚠ AND IT MUST BE LAID OUT THAT WAY TO MEAN ANYTHING: V24/PWR_GND keep their
    # own island in the -Y corner, the pair runs tightly coupled so the loop
    # encloses no area, and NEITHER GROUND POUR may flood across them. A netlist
    # cannot express that; it is a layout obligation and this is where it is
    # written down.
    # THE RESPIN ADDS ONE TAP TO THAT ISLAND -- U5's input -- and that tap is the
    # only thing on it besides the two connectors.
    j6 = Part(name="PJ-102AH", ref_prefix="J", tag="J6", dest="NETLIST", tool="skidl",
              value="PJ-102AH", description="24 V inlet, PCB mount, panel bushing",
              footprint=DC_FP,
              pins=[Pin(num=1, name="TIP", func=P), Pin(num=2, name="SLEEVE", func=P),
                    Pin(num=3, name="SWITCH", func=P)])
    v24 += j6[1]
    pgnd += j6[2], j6[3]      # the switch contact ties to the sleeve, not left open
    # Trunk out on the instrument's standard 4-way, TWO CONTACTS PER RAIL. XH is
    # rated 3 A per contact and BOM.md sizes the 24 V bus at under 5 A, so one
    # contact would sit over its rating and two sit comfortably under.
    j7 = Part(name="B4B-XH-A", ref_prefix="J", tag="J7", dest="NETLIST", tool="skidl",
              value="B4B-XH-A", description="24 V trunk out (2 contacts per rail)",
              footprint=XH_FP,
              pins=[Pin(num=i + 1, name=n, func=P)
                    for i, n in enumerate(("PWR_GND", "+24V", "+24V", "PWR_GND"))])
    pgnd += j7[1], j7[4]
    v24 += j7[2], j7[3]

    # ── J8: the magnetic pickup, on SCREW TERMINALS (user) ───────────────────
    # It is the most likely thing anyone ever rewires -- swapping a pickup is a
    # normal thing to do to a guitar -- so it is the one field connection that is
    # neither soldered nor crimped. A pickup arrives as two bare tinned leads; a
    # screw terminal takes them as they are.
    pk_hot = Net("PICKUP_HOT")
    j8 = Part(name="SCREW_2", ref_prefix="J", tag="J8", dest="NETLIST", tool="skidl",
              value="MX126-5.0-02P", description="magnetic pickup in, screw terminals",
              footprint=TERM_FP,
              pins=[Pin(num=1, name="HOT", func=P), Pin(num=2, name="RET", func=P)])
    pk_hot += j8[1]
    agnd += j8[2]             # the coil's return IS the analog reference

    # ── U1: the MCU. USB HS to the hub, full-duplex I2S, one GPIO for the relay ──
    # Pin numbers off WCH's QFN-68 column (CH32V303/305/307/317 V3.9, table 3-1):
    #   61 PB6  = USBHS_DM      62 PB7  = USBHS_DP
    #   35 PB12 = I2S2 WS       36 PB13 = I2S2 CK       38 PB15 = I2S2 SD  (to DAC)
    #   37 PB14 = I2S2ext SD (FROM the ADC) -- full duplex on ONE clock pair, which
    #            is what lets the ADC and the DAC share BCK/LRCK and stay sample-
    #            aligned with each other without a resampler in between.
    #   25 PB0 relay, 48 PA13 SWDIO, 52 PA14 SWCLK, 63 BOOT0
    i2s_ck, i2s_ws = Net("I2S_CK"), Net("I2S_WS")
    i2s_sdo, i2s_sdi = Net("I2S_SDO"), Net("I2S_SDI")
    relay = Net("RELAY")
    mcu_pins = [Pin(num=n, func=P) for n in
                (32, 50, 68, 17, 31, 51, 67, 13,        # VDD
                 18, 49, 12, 69,                        # VSS + the exposed pad
                 5, 6, 7,                               # OSC_IN, OSC_OUT, NRST
                 61, 62, 35, 36, 37, 38, 25, 48, 52, 63)]
    u1 = Part(name="CH32V307WCU6", ref_prefix="U", tag="U1", dest="NETLIST", tool="skidl",
              value="CH32V307WCU6",
              description="RISC-V MCU, USB2.0 HS with INTERNAL PHY (LCSC C5142795)",
              footprint=MCU_FP, pins=mcu_pins)
    for n in (32, 50, 68, 17, 31, 51, 67, 13):
        v3v3 += u1[n]
    for n in (18, 49, 12, 69):
        gnd += u1[n]
    osc_in, osc_out, nrst = Net("OSC_IN"), Net("OSC_OUT"), Net("NRST")
    osc_in += u1[5]
    osc_out += u1[6]
    nrst += u1[7]
    hub_dn1_dm += u1[61]      # the MCU is a hub DOWNSTREAM -- no connector needed
    hub_dn1_dp += u1[62]
    i2s_ws += u1[35]
    i2s_ck += u1[36]
    i2s_sdi += u1[37]
    i2s_sdo += u1[38]
    relay += u1[25]
    swdio, swclk, boot0 = Net("SWDIO"), Net("SWCLK"), Net("BOOT0")
    swdio += u1[48]
    swclk += u1[52]
    boot0 += u1[63]

    # ══ ⚠ AUDIT, 2026-09-17: THE ANALOG HALF OF THIS BOARD IS NOT BUILDABLE AS WIRED ══
    # Checked against TI's own datasheets (PCM5102A SLAS859C, PCM1808 SLES177B), not
    # memory. The board routes 0/0 in DRC and is electrically wrong, because DRC checks
    # copper against the netlist and these faults ARE the netlist.
    #
    # 1. U3 (PCM5102A) PINOUT IS INVENTED. Ten made-up pins on a 20-pin TSSOP. The real
    #    order is 1 CPVDD 2 CAPP 3 CPGND 4 CAPM 5 VNEG 6 OUTL 7 OUTR 8 AVDD 9 AGND
    #    10 DEMP 11 FLT 12 SCK 13 BCK 14 DIN 15 LRCK 16 FMT 17 XSMT 18 LDOO 19 DGND
    #    20 DVDD. It also needs a CAPP-CAPM flying cap, VNEG and LDOO decoupling, and
    #    DEMP/FLT/FMT/SCK strapped -- none of which exist here.
    # 2. U3 IS WIRED TO 5 V. AVDD and XSMT go to v5. AVDD/CPVDD/DVDD are ABSOLUTE
    #    MAXIMUM 3.9 V. As drawn, the first power-up damages the DAC.
    # 3. U2 (PCM1808) PINOUT IS INVENTED. 16 pins on a 14-pin TSSOP. Real order:
    #    1 VREF 2 AGND 3 VCC(5 V) 4 VDD(3.3 V) 5 DGND 6 SCKI 7 LRCK 8 BCK 9 DOUT
    #    10 MD0 11 MD1 12 FMT 13 VINL 14 VINR.
    # 4. SCKI IS TIED TO BCK. SCKI must be 256/384/512 fS; BCK is 64 fS. The ADC needs a
    #    real MCLK from the MCU (I2S2_MCK), which is not wired.
    # 5. THE BUFFERS CLIP HALF THE WAVEFORM. PCM5102A's OUTL is GROUND-CENTRED (its
    #    charge pump makes the negative rail), and the pickup is AC about 0 V. Both feed
    #    TLV9061s on 5 V with V- at AGND, which cannot go below ground. Each path needs
    #    a mid-rail bias and coupling caps -- a tone-affecting choice, and a design
    #    decision rather than a correction.
    # 6. U4 (hub) and K1 (relay) are numbered 1..N with no datasheet behind them.
    #
    # fab.py keeps every one of these parts OPEN so the panel cannot be ordered while
    # this stands. Delete this note only when each item is fixed and re-checked.
    # ══════════════════════════════════════════════════════════════════════════════

    # ── U2: the magnetic channel's ADC ───────────────────────────────────────
    # PCM1808: 1 VINL 2 VINR 3 AGND 4 VCC 5 MD1 6 MD0 7 SCKI 8 BCK 9 LRCK 10 DOUT
    #          11 DGND 12 VDD 13 FMT 14-16 unused on this part's TSSOP.
    # MD1/MD0 low = SLAVE mode: the MCU owns BCK and LRCK, which is what keeps the
    # ADC and the DAC on the same clock.
    pk_buf = Net("PICKUP_BUF")
    u2 = Part(name="PCM1808PWR", ref_prefix="U", tag="U2", dest="NETLIST", tool="skidl",
              value="PCM1808PWR", description="24-bit 99 dB 96 kHz stereo ADC",
              footprint=ADC_FP,
              pins=[Pin(num=i, func=P) for i in range(1, 17)])
    # BOTH inputs take the same buffered pickup: the instrument has one magnetic
    # coil, and driving the unused channel with the signal rather than leaving it
    # floating keeps the part's two halves at the same bias.
    pk_buf += u2[1], u2[2]
    agnd += u2[3]
    v5 += u2[4]
    gnd += u2[5], u2[6], u2[11], u2[13]
    i2s_ck += u2[7], u2[8]
    i2s_ws += u2[9]
    i2s_sdi += u2[10]
    v3v3 += u2[12]
    for n in (14, 15, 16):
        Net("U2_NC_%d" % n).connect(u2[n])

    # ── U3: the DAC -- the Pi's processed audio, made analog again ───────────
    proc = Net("AUDIO_PROC")
    u3 = Part(name="DAC_I2S", ref_prefix="U", tag="U3", dest="NETLIST", tool="skidl",
              value="PCM5102A-class", description="I2S stereo DAC, no MCLK needed",
              footprint=DAC_FP,
              pins=[Pin(num=1, name="LRCK", func=P), Pin(num=2, name="DIN", func=P),
                    Pin(num=3, name="BCK", func=P), Pin(num=4, name="DGND", func=P),
                    Pin(num=5, name="DVDD", func=P), Pin(num=6, name="AVDD", func=P),
                    Pin(num=7, name="AGND", func=P), Pin(num=8, name="OUTL", func=P),
                    Pin(num=9, name="OUTR", func=P), Pin(num=10, name="XSMT", func=P)]
                   + [Pin(num=i, func=P) for i in range(11, 21)])
    i2s_ws += u3[1]
    i2s_sdo += u3[2]
    i2s_ck += u3[3]
    gnd += u3[4]
    v3v3 += u3[5]
    v5 += u3[6]
    agnd += u3[7]
    # ⚠ OUTR IS UNCONNECTED ON PURPOSE AND THAT IS NOW A DECISION, NOT AN OMISSION.
    # The user's call: the PI DOES THE STEREO->MONO SUM IN SOFTWARE. It already
    # chooses what to send here, so it can fold down for the jack while the
    # computer gets full stereo over the gadget port -- two different mixes from
    # one stream. A resistor pair into the buffer's summing node would have frozen
    # one fixed relationship in copper and made both worse.
    proc += u3[8]
    Net("DAC_OUT_R_NC").connect(u3[9])
    v5 += u3[10]              # XSMT tied high: un-mute
    for n in range(11, 21):
        Net("U3_NC_%d" % n).connect(u3[n])

    # ── U4: the hub. HIGH SPEED -- a FS hub would reintroduce the TT ─────────
    # Generic 2-port pinout: 1 UDP 2 UDM (upstream) 3 VDD 4 GND 5 XI 6 XO
    #                        7 DP1 8 DM1 9 DP2 10 DM2, 11-23 unused, 24 GND/EP.
    hub_xi, hub_xo = Net("HUB_XI"), Net("HUB_XO")
    u4 = Part(name="USB_HUB", ref_prefix="U", tag="U4", dest="NETLIST", tool="skidl",
              value="CH334-class HS hub", description="2-port USB 2.0 HIGH-SPEED hub: "
              "the MCU and the optical board reach the Pi on ONE cable",
              footprint=HUB_FP, pins=[Pin(num=i, func=P) for i in range(1, 25)])
    hub_up_dp += u4[1]
    hub_up_dm += u4[2]
    v3v3 += u4[3]
    gnd += u4[4], u4[24]
    hub_xi += u4[5]
    hub_xo += u4[6]
    hub_dn1_dp += u4[7]
    hub_dn1_dm += u4[8]
    hub_dn2_dp += u4[9]
    hub_dn2_dm += u4[10]
    for n in range(11, 24):
        Net("U4_NC_%d" % n).connect(u4[n])

    # ── U5: 24 -> 5 V. THE ONE SWITCHER, and it lives in the inlet corner. ───
    # TI SNVSA24 (LMR16006): 1 CB, 2 GND, 3 FB, 4 SHDN (float = enabled), 5 VIN,
    # 6 SW. Same part the lever board and the motor controller use, so the respin
    # adds a circuit but no SKU.
    sw, v5_pre, boot, fb = Net("SW"), Net("V5_PRE"), Net("BOOT"), Net("FB")
    u5 = Part(name="LMR16006XDDCR", ref_prefix="U", tag="U5", dest="NETLIST", tool="skidl",
              value="LMR16006XDDCR", description="60 V 0.6 A buck, 24 V -> 5 V "
              "(LCSC C87080)", footprint="Package_TO_SOT_SMD:SOT-23-6",
              pins=[Pin(num=i, func=P) for i in range(1, 7)])
    boot += u5[1]
    pgnd += u5[2]
    fb += u5[3]
    Net("SHDN_NC").connect(u5[4])
    v24 += u5[5]
    sw += u5[6]

    # ── U6: 5 -> 3.3 V for the MCU, the hub and the converters' digital side ─
    u6 = Part(name="LDO_3V3", ref_prefix="U", tag="U6", dest="NETLIST", tool="skidl",
              value="AP2112K-3.3TRG1", description="5 V -> 3V3, AFTER the bead",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=i, func=P) for i in range(1, 6)])
    v5 += u6[1], u6[3]        # IN and EN; EN tied on
    gnd += u6[2]
    Net("LDO_NC").connect(u6[4])
    v3v3 += u6[5]

    # ── U7/U8: the two analog buffers ────────────────────────────────────────
    sel, buf = Net("AUDIO_SEL"), Net("BUF_OUT")
    u7 = Part(name="OPAMP", ref_prefix="U", tag="U7", dest="NETLIST", tool="skidl",
              value="TLV9061IDBVR", description="output buffer -- drives the TS jack",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                    Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                    Pin(num=5, name="V+", func=P)])
    buf += u7[1], u7[4]       # unity-gain follower
    agnd += u7[2]
    sel += u7[3]
    v5 += u7[5]
    # ⚠ U8 IS NEW WITH THE PICKUP, AND IT IS WHAT MAKES ONE COIL FEED TWO THINGS.
    # The ADC and the relay's direct contact both want the pickup, and a magnetic
    # pickup's tone IS its loading -- hang two inputs straight on the coil and you
    # have changed the instrument's sound. One buffer, two taps off its output, so
    # the coil sees a single high impedance whichever mode is selected.
    u8 = Part(name="OPAMP", ref_prefix="U", tag="U8", dest="NETLIST", tool="skidl",
              value="TLV9061IDBVR", description="pickup buffer -- feeds BOTH the "
              "relay's direct contact and the ADC, so the coil sees one load",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                    Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                    Pin(num=5, name="V+", func=P)])
    pk_buf += u8[1], u8[4]
    agnd += u8[2]
    pk_hot += u8[3]
    v5 += u8[5]

    # ── K1/Q1: direct vs processed. DE-ENERGISED IS DIRECT. ──────────────────
    # With no power, no Pi and no firmware the magnetic pickup reaches the jack
    # through a mechanical contact, so the instrument is still a guitar when
    # everything clever about it is off.
    # ⚠ AND IT IS NOT LATCHING, WHICH CORRECTS ME: I wrote on the optical board
    # that latching was required because "a held coil hums at the audio it is
    # switching". Wrong -- the coil is driven with DC and a static field does not
    # hum. The real cost of holding it is ~30 mA, which this rail has.
    # 1/10 coil, 2 common, 3 NC (direct), 4 NO (processed) on the pole in use.
    coil = Net("RELAY_COIL")
    k1 = Part(name="RELAY_DPDT", ref_prefix="K", tag="K1", dest="NETLIST", tool="skidl",
              value="FRT5-class 5V", description="true-bypass select; DE-ENERGISED = DIRECT",
              footprint=RELAY_FP, pins=[Pin(num=i, func=P) for i in range(1, 11)])
    v5 += k1[1]
    coil += k1[10]
    sel += k1[2]
    pk_buf += k1[3]
    proc += k1[4]
    for i in (5, 6, 7, 8, 9):
        Net("K1_UNUSED_%d" % i).connect(k1[i])
    q1 = Part(name="Q_NMOS", ref_prefix="Q", tag="Q1", dest="NETLIST", tool="skidl",
              value="AO3400A", description="relay coil driver (LCSC C20917)",
              footprint="Package_TO_SOT_SMD:SOT-23",
              pins=[Pin(num=1, name="G", func=P), Pin(num=2, name="S", func=P),
                    Pin(num=3, name="D", func=P)])
    gnd += q1[2]
    coil += q1[3]

    # ── crystals ─────────────────────────────────────────────────────────────
    y1 = Part(name="Crystal", ref_prefix="Y", tag="Y1", dest="NETLIST", tool="skidl",
              value="8MHz", description="MCU HSE -- the PLL source for USB HS",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=i, func=P) for i in range(1, 5)])
    osc_in += y1[1]
    osc_out += y1[3]
    gnd += y1[2], y1[4]
    y2 = Part(name="Crystal", ref_prefix="Y", tag="Y2", dest="NETLIST", tool="skidl",
              value="12MHz", description="hub reference",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=i, func=P) for i in range(1, 5)])
    hub_xi += y2[1]
    hub_xo += y2[3]
    gnd += y2[2], y2[4]

    # ── L1 / FB1: the buck's output, and the ONE place the rails join ────────
    l1 = Part(name="L", ref_prefix="L", tag="L1", dest="NETLIST", tool="skidl",
              value="47uH", description="buck output inductor, SHIELDED -- it sits on "
              "the same board as a magnetic pickup's preamp",
              footprint="Inductor_SMD:L_Taiyo-Yuden_NR-30xx",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw += l1[1]
    v5_pre += l1[2]
    # ⚠ V5_PRE BECOMES +5V THROUGH A BEAD, NOT A WIRE. The buck's return stays on
    # PWR_GND and the board's 5 V rides the signal ground; the bead is where the two
    # domains meet, deliberately and in one identifiable place. Route it as the
    # single crossing it is -- if copper joins the rails anywhere else, this part
    # is decoration.
    fb1 = Part(name="FerriteBead", ref_prefix="FB", tag="FB1", dest="NETLIST",
               tool="skidl", value="600R@100MHz",
               description="5 V rail split: buck side to board side",
               footprint="Inductor_SMD:L_0603_1608Metric",
               pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v5_pre += fb1[1]
    v5 += fb1[2]

    # ── diodes ───────────────────────────────────────────────────────────────
    d1 = _d("D1", "B5819W", "buck catch diode -- the LMR16006 is ASYNCHRONOUS, so this "
            "is required, not optional", "Diode_SMD:D_SOD-123")
    sw += d1[1]
    pgnd += d1[2]
    for tag, net in (("D2", thru_dp), ("D3", thru_dm)):
        d = _d(tag, "ESD", "panel USB data-line clamp -- J1 is the port a stranger "
               "plugs into")
        net += d[1]
        gnd += d[2]
    d4 = _d("D4", "flyback", "coil flyback -- the coil is an inductor and the FET is not")
    coil += d4[1]
    v5 += d4[2]
    # D5 IS THE PHANTOM GUARD'S CLAMP and it sits INSIDE the DC block: a blocking
    # capacitor stops the 48 V but passes the insertion edge straight through.
    blocked = Net("OUT_BLOCKED")
    d5 = _d("D5", "bidir clamp", "catches the insertion edge C1 passes through")
    blocked += d5[1]
    agnd += d5[2]
    d6 = _d("D6", "SMAJ30A", "24 V rail clamp -- the trunk is shared with ten stepper "
            "drivers and their inductive kick arrives here", "Diode_SMD:D_SMA")
    v24 += d6[1]
    pgnd += d6[2]

    # ── resistors ────────────────────────────────────────────────────────────
    for tag, pin in (("R1", "A5"), ("R2", "B5")):
        r = _r(tag, "5k1", "panel USB-C CC pull-down (upstream-facing port)")
        j1[pin] += r[1]
        gnd += r[2]
    for tag, pin in (("R3", "A5"), ("R4", "B5")):
        r = _r(tag, "5k1", "hub upstream CC pull-down")
        j3[pin] += r[1]
        gnd += r[2]
    r5 = _r("R5", "100R", "relay gate series")
    relay += r5[1]
    r5[2] += q1[1]
    r6 = _r("R6", "10k", "NRST pull-up")
    nrst += r6[1]
    v3v3 += r6[2]
    r7 = _r("R7", "10k", "BOOT0 pull-down -- run from flash unless deliberately held")
    boot0 += r7[1]
    gnd += r7[2]
    r8 = _r("R8", "1M", "pickup input bias to ground -- the coil is FLOATING until "
            "someone screws a pickup on, and an unbiased op-amp input rails")
    pk_hot += r8[1]
    agnd += r8[2]
    r9 = _r("R9", "220R", "output series -- bounds a phantom-power fault and C1's inrush")
    buf += r9[1]
    blocked += r9[2]
    r10 = _r("R10", "100k", "output bleed -- stops the DC block thumping on unplug")
    outp += r10[1]
    agnd += r10[2]
    r11 = _r("R11", "preset", "buck feedback divider, top -- set at the bench")
    r12 = _r("R12", "preset", "buck feedback divider, bottom")
    v5_pre += r11[1]
    fb += r11[2], r12[1]
    pgnd += r12[2]

    # ── capacitors ───────────────────────────────────────────────────────────
    # ⚠ C1 IS A SAFETY PART, NOT A BYPASS -- R9/C1/D5 are the PHANTOM-POWER guard.
    # Reach a combo TRS/XLR input with phantom on and +48 V arrives through 6.81k
    # on the tip. C1 blocks the DC outright; 100 V is the RATING and not margin,
    # because it sits charged to 48 V for the duration of the fault. Oversized at
    # 2.2 uF so the signal swing ACROSS it stays small, which is what makes an X7R
    # part's voltage coefficient a non-issue rather than a distortion argument.
    # Roughly $0.05, and impossible to add later.
    c1 = _c("C1", "2.2uF/100V", "OUTPUT DC BLOCK -- the phantom guard, see above",
            "Capacitor_SMD:C_1210_3225Metric")
    blocked += c1[1]
    outp += c1[2]
    c2 = _c("C2", "10uF/50V", "24 V input bulk -- 1206 for the DC-bias derating",
            "Capacitor_SMD:C_1206_3216Metric")
    v24 += c2[1]
    pgnd += c2[2]
    c3 = _c("C3", "100nF", "24 V input HF bypass")
    v24 += c3[1]
    pgnd += c3[2]
    c4 = _c("C4", "10nF", "buck bootstrap")
    boot += c4[1]
    sw += c4[2]
    for tag in ("C5", "C6"):
        c = _c(tag, "22uF/16V", "5 V bulk, BUCK SIDE of the bead",
               "Capacitor_SMD:C_0805_2012Metric")
        v5_pre += c[1]
        pgnd += c[2]
    for tag, val, net, ref, desc in (
            ("C7", "10uF", v5, agnd, "5 V bulk, board side of the bead"),
            ("C8", "100nF", v5, agnd, "5 V HF bypass"),
            ("C9", "10uF", v3v3, gnd, "3V3 bulk"),
            ("C10", "100nF", v3v3, gnd, "MCU bypass"),
            ("C11", "100nF", v3v3, gnd, "MCU bypass"),
            ("C12", "100nF", v3v3, gnd, "hub bypass"),
            ("C13", "100nF", v5, agnd, "ADC analog bypass"),
            ("C14", "100nF", v5, agnd, "DAC analog bypass")):
        fp = ("Capacitor_SMD:C_0805_2012Metric" if val == "10uF"
              else "Capacitor_SMD:C_0402_1005Metric")
        c = _c(tag, val, desc, fp)
        net += c[1]
        ref += c[2]
    for tag, net in (("C15", osc_in), ("C16", osc_out), ("C17", hub_xi), ("C18", hub_xo)):
        c = _c(tag, "12pF", "crystal load")
        net += c[1]
        gnd += c[2]


# ── the board ────────────────────────────────────────────────────────────────
# ⚠ THE OUTLINE IS AN OUTPUT and the MECHANICAL SIDE SHOULD BE BUILT TO IT, like
# the TRRS adapter. It lies FLAT in the bridge endplate's open -Y corner with the
# panel connectors along +X.
#
# ⚠ THE RESPIN GROWS IT IN X, NOT Y, AND THAT IS NOT A PREFERENCE. The board's -Y
# edge lands 3.67 mm off the chassis rail, so there is nothing to give in Y; the
# endplate corner is open about 100 mm in X. 52 -> 74 goes BACKWARDS into the bay,
# behind the panel face, where the new parts live. The panel connectors themselves
# did not move relative to each other.
#
# ⚠ TWO THINGS THE ENDPLATE HAS TO ABSORB, both for branner:
#   1. THE PANEL HOLES ARE NOT IN ONE ROW AT ONE HEIGHT. A TS jack's axis and a
#      USB-C's axis sit at different heights above the board they share, so the
#      holes differ in Z by that much. Their Y positions come from this board's
#      geometry, not from the old 18 mm pitch.
#   2. THERE ARE NOW TWO USB-A SHELLS ON THE -X EDGE (J2 to the Pi's gadget port,
#      J4 to the optical board) plus a USB-C (J3, hub upstream). Those face INTO
#      the instrument, not out the panel, and want cable room behind them.
BOARD_W, BOARD_L = 74.0, 66.0

BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 4,
    "thickness_mm": 1.6,
    # FOUR LAYERS because this board carries an audio output stage and THREE USB
    # pairs over the same copper -- two of them at 480 Mbps after the respin. In1.Cu
    # is an UNBROKEN ground plane under all of it: it is what gives the analog side
    # a quiet reference and the USB pairs a defined impedance, and neither is
    # negotiable on a board whose whole job is the signal a listener actually hears.
    # B.Cu pours the same net rather than a second one -- see the one-ground note in
    # output_panel() for why that stopped being a split.
    "zones": [("GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],
    # ⚠ IN1 IS A PLANE, AND THE ROUTER HAS TO BE TOLD. A zone is just copper as far
    # as freerouting is concerned: pour GND on In1 and say nothing, and it will route
    # signals straight through the plane, which is exactly what it did here. The damage
    # is not cosmetic -- a signal in the reference plane splits the return path of every
    # trace that crosses it, and the nets carved through this one included the ones that
    # care most.
    #
    # This was found and fixed on the optical board and the fix never reached the other
    # three 4-layer boards, because it was made where the symptom appeared instead of
    # where the property belonged. A board that pours a plane declares it.
    "plane_layers": ("In1.Cu",),
    # ⚠ NO track_mm HERE: 0.15 was TESTED AND CHANGED NOTHING -- 2 unconnected either
    # way. This board has a 0.4 mm pitch MCU like lever_sensor, where narrowing fixed
    # three nets, so it was worth trying; the two failures here are not escape failures.
    # A narrower track is slightly less robust to etch variation, so it does not stay for
    # a benefit it did not deliver.
    # ⚠ AND A PLANE NEEDS STITCHING TO IT. Declaring In1 a plane is only half the
    # job: it stops the router carrying ground THROUGH the plane, and then nothing
    # connects the ground pads TO it. Declared alone it stranded six GND pads on this
    # board -- the pour reaches them, but a pour is what routing can orphan, which is
    # the whole reason the plane is there. Every GND pad gets its own via down.
    "stitch_nets": ("GND",),
    # ⚠ NO local_nets HERE EITHER, AND NOW THERE IS A PATTERN. Measured on three
    # boards: it takes lever_sensor from 4 unconnected to 7, this board from 2 to 5, and
    # the optical board from 26 to 12. Pre-laying copper is not a general improvement --
    # it is a trade, and what it trades is the router's freedom for determinism.
    #
    # That trade pays when the router is losing anyway. Optical is 153 parts with twenty
    # identical feedback clusters in a 13.6 mm strip; the pattern is real and the search
    # is drowning. This board is 58 parts with room, and the router was two connections
    # short -- taking its freedom away to save it work it did not need saving from costs
    # three more.
    #
    # Keep the numbers rather than the rule: re-measure if either board gains a row.
    # THE FLOORPLAN IS THREE BANDS, which is the whole noise argument made
    # geometric: the 24 V island and its switcher in the -Y corner, the digital
    # block across the middle, and the ANALOG CHAIN along +Y as far from the
    # switching node as 66 mm allows.
    "placements": {
        # +X, THE PANEL FACE -- all three flush to the edge, because a connector
        # inset from the board edge is a connector the chassis wall cannot reach.
        "J5": (23.11, 21.50, 0.0),      # 1/4 in jack, 27.62 x 20.32 -- the big one
        "J1": (29.44, 4.00, 90.0),      # panel USB-C
        "J6": (32.02, -20.50, 0.0),     # 24 V barrel inlet
        # -X, FACING INTO THE INSTRUMENT.
        # ⚠ 270, NOT 180, AND THE DIFFERENCE IS NOT COSMETIC. This footprint's
        # courtyard runs -12.68..+3.90 in Y about the pad centroid, so its MOUTH is
        # the -Y face; at 180 the shell points +Y -- along the board, opening onto
        # the pickup terminals -- while still measuring flush against the -X edge.
        # place_check passes either way (the rotated courtyard lands in free space
        # both times), so nothing catches it but reading the offset. 270 turns the
        # mouth out through the -X edge, which is what these three are for.
        "J2": (-24.32, 24.00, 270.0),   # -> the Pi's gadget port
        "J3": (-29.44, 8.00, 270.0),    # hub upstream -> a Pi host port
        "J4": (-24.32, -8.00, 270.0),   # hub downstream -> the optical board
        # +Y BAND: THE ANALOG CHAIN. It is up here because the switcher is down
        # there -- 50 mm of board between a 24 V switching node and a magnetic
        # pickup's preamp is the cheapest noise measure available.
        "J8": (-13.50, 28.00, 0.0),     # pickup screw terminals
        "U8": (-4.50, 29.00, 0.0),      # pickup buffer, right at the terminals
        "R8": (-4.50, 25.00, 0.0),
        "C13": (-4.00, 22.50, 0.0),
        "U2": (2.50, 29.00, 0.0),       # ADC
        "U3": (2.50, 21.00, 0.0),       # DAC
        "C14": (-3.50, 21.00, 0.0),
        "K1": (-13.00, 15.00, 0.0),
        "Q1": (-4.00, 15.00, 0.0),
        "R5": (-4.00, 12.00, 0.0),
        "D4": (0.00, 15.00, 0.0),
        # the output chain runs BELOW the jack, not beside it: J5's courtyard owns
        # everything above y 11.34 out to the +X edge
        "U7": (4.00, 8.00, 0.0),
        "R9": (8.00, 8.00, 0.0),
        "C1": (13.00, 8.00, 0.0),
        "D5": (17.50, 8.00, 0.0),
        "R10": (21.00, 8.00, 0.0),
        "C7": (4.00, 4.00, 0.0),
        "C8": (7.50, 4.00, 0.0),
        # CC pull-downs and the panel ESD clamps, beside their own connectors
        "R1": (24.00, 2.00, 0.0),
        "R2": (24.00, 0.00, 0.0),
        "D2": (24.00, -2.50, 0.0),
        "D3": (24.00, -4.50, 0.0),
        # J3's pair could not stay beside J3 -- the -X column now fills that edge
        # top to bottom. A CC pull-down is a DC termination, so length costs it
        # nothing; it goes in the first clear ground below the column.
        "R3": (-25.50, -18.00, 0.0),
        "R4": (-25.50, -20.00, 0.0),
        # MIDDLE: THE DIGITAL BLOCK, where it can reach both bands
        "U1": (-6.00, -8.00, 0.0),
        "Y1": (-6.00, -15.00, 0.0),
        "C15": (-11.00, -15.00, 0.0),
        "C16": (-1.00, -15.00, 0.0),
        # ⚠ 2.5 mm EAST, TO OPEN ITS WEST CHANNEL. At -17.00 the hub's courtyard came
        # within 0.75 mm of J4's, and ALL SIX of its west-edge pins -- the upstream
        # differential pair, 3V3, GND and both oscillator pins -- had to escape through
        # that gap or travel around the package. HUB_XI was the one that lost, and it
        # survived a crystal relocation and two routing attempts before the cause was
        # looked at rather than the symptom.
        # U1 sits at 89.36, so there were 3.69 mm of slack here doing nothing. The
        # channel goes to 3.25 mm and the hub keeps 1.2 mm to the MCU.
        "U4": (-14.50, -8.00, 0.0),
        "C12": (-17.00, -4.00, 0.0),
        # ⚠ THE CRYSTAL MOVES UP UNDER ITS HUB, and this is a signal-integrity fix that
        # happened to surface as a routing failure. At -17.50 it sat 9.6 mm from U4's XI
        # pin, with its two load caps another 4.5 mm out either side -- a 12 MHz
        # oscillator node stretched across 18 mm of board. That is bad practice on its
        # own terms (stray capacitance on the loop, and an antenna at the one node that
        # cannot tolerate one), and the only reason it was noticed is that HUB_XI would
        # not route.
        # The board directly below U4 was empty, so the crystal takes it: XI/XO are on
        # U4's west edge at its bottom corner, and the loop drops from 18 mm to ~4.
        "Y2": (-16.00, -13.00, 0.0),
        "C17": (-17.50, -16.50, 0.0),
        "C18": (-14.50, -16.50, 0.0),
        "U6": (6.00, -8.00, 0.0),
        "C9": (11.00, -8.00, 0.0),
        "C10": (14.50, -8.00, 0.0),
        "C11": (6.00, -12.00, 0.0),
        "R6": (11.00, -12.00, 0.0),
        "R7": (14.00, -12.00, 0.0),
        # -Y CORNER: THE 24 V ISLAND AND ITS SWITCHER, on their own copper
        "J7": (0.00, -28.00, 0.0),
        "D6": (-12.00, -28.00, 0.0),
        "C2": (-20.00, -28.00, 0.0),
        "C3": (-25.00, -28.00, 0.0),
        "U5": (-30.00, -28.00, 0.0),
        "L1": (-30.00, -23.50, 0.0),
        "D1": (-24.00, -23.50, 0.0),
        "C4": (-19.00, -23.50, 0.0),
        "R11": (-16.00, -23.50, 0.0),
        "R12": (-16.00, -25.50, 0.0),
        # the bulk caps and THE BEAD sit at the island's +X end, which is where the
        # rail leaves for the rest of the board
        "C5": (9.00, -23.50, 0.0),
        "C6": (13.00, -23.50, 0.0),
        "FB1": (17.00, -23.50, 0.0),
    },
    "refs_on_fab": True,
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
