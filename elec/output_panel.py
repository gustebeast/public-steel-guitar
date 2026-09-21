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

import netcheck                                     # noqa: E402

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
ADC_FP = "Package_SO:TSSOP-14_4.4x5mm_P0.65mm"     # PCM1808PWR is a 14-pin TSSOP
DAC_FP = "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm"
HUB_FP = "Package_DFN_QFN:HVQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm"
# DPDT signal relay, 5 V coil. Only ONE pole switches audio (the tip); an
# unbalanced output has nothing for the second pole to do, and a DPDT in this
# package is what is stocked.
RELAY_FP = "Relay_SMD:Relay_DPDT_Omron_G6K-2F-Y"


# ⚠ THE REF IS PINNED FROM THE TAG. Every call passes a tag that spells the intended
# ref, and without ref= that agreement is a COINCIDENCE of CREATION ORDER, not a
# mechanism. On lever_sensor, adding a single resistor in the middle of the file consumed
# R5 and pushed every later resistor up one -- and BOARD_NOTES["placements"] is keyed by
# ref, so parts silently referred to refs that no longer existed while a new one with no
# placement would have landed on the board ORIGIN. ERC passed and the netlist was valid.
# This board had the same latent fault; pinning the ref makes creation order irrelevant.
def _r(tag, value, desc, fp="Resistor_SMD:R_0402_1005Metric"):
    return Part(name="R", ref_prefix="R", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, fp="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
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
# ⚠ EVERY REF IS PINNED, NOT JUST THE PASSIVES. _r and _c were given ref=tag earlier
# today after skidl's creation-order numbering silently renamed three resistors on
# lever_sensor. The CONNECTORS were left relying on the same coincidence, and adding J10
# broke it exactly the same way: the netlist came out J1-J7, J9, J10, J11 with NO J8,
# because the explicitly-named J10 displaced the screw terminal that used to autonumber
# there. BOARD_NOTES["placements"] still keyed J8, so layout stopped with "no placement
# given for: J10, J11" -- and this board had been unbuildable since J10 was added,
# because I added the part and never routed the board.
#
# Same defect, third occurrence, after I had already written the fix for it. Pinning one
# family and leaving the rest is not a fix, it is a smaller version of the bug.

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
    j5 = Part(name="NMJ4HCD2", ref_prefix="J", ref="J5", tag="J5", dest="NETLIST", tool="skidl",
              value="NMJ4HCD2", description="1/4 in TS output, PCB mount, panel bushing",
              footprint=TS_FP,
              pins=[Pin(num="T", name="TIP", func=P), Pin(num="TN", name="TIP_N", func=P),
                    Pin(num="S", name="SLEEVE", func=P), Pin(num="SN", name="SLEEVE_N", func=P)])
    outp += j5["T"]
    # The switched contacts go to ground rather than floating: an open switch lug
    # beside an audio contact is an antenna, and nothing here needs to sense a plug.
    agnd += j5["S"], j5["TN"], j5["SN"]

    # ── J6/J7: the 24 V inlet, crossing its own corner ───────────────────────
    # ⚠ AND THE SPLIT COSTS SOMETHING, MEASURED 2026-09-19: THIS BOARD HAS THE WORST
    # SWITCHER LOOP IN THE FLEET, and it is the split that makes it so. PWR_GND is a
    # separate net, so it gets NO POUR -- the zones here are GND on In1.Cu and B.Cu. The
    # buck's return current therefore cannot drop into a plane beneath its own trace the
    # way it does on every other board; it has to run as copper, all the way around the
    # package:
    #
    #     +24V out     U5.VIN -> C3      3.38 mm  straight
    #     PWR_GND back C3 -> U5.GND     10.72 mm  around the package
    #     enclosed                      11.38 mm2
    #
    # against the rest of the fleet, same measurement:
    #     lever_sensor U1   0.86 mm2   plane return, and 11 of these per instrument
    #     motor_ctrl   U5   plane return, input cap 8.93 mm from VIN
    #     motor_ctrl   U1   plane return, input cap 11.91 mm from VIN -- the longest
    #     optical      U13  6.23 mm2   trace return, forced by the package pinout
    #
    # ⚠ THE TRADE IS REAL AND WORTH STATING PLAINLY. The split keeps switcher return
    # current out of the audio ground, which is what it is for and which no loop-area
    # number argues against. What it costs is that the switcher's own loop is three
    # times the size it would otherwise be. Both effects are real; this board chose the
    # one that protects the signal chain.
    #
    # It is acceptable here for the same reason optical's is: distance. U5 sits in one
    # corner and the analog chain in the other -- nearest is U7 at 49.67 mm, then J8 at
    # 57.72, U3 at 58.80, U2 at 65.61 and the jack at 74.20, on a board whose diagonal is
    # 99 mm. Near-field coupling falls as 1/r^3 and the GND plane spans the gap. But of
    # the fleet's four switchers this is the one with the least margin, so if EMI ever
    # shows up in the audio path, this loop is the first thing to look at and the fix is
    # a local PWR_GND pour under the buck, tied to the split's single joining point.
    # ⚠ PWR_GND IS A SEPARATE NET AND IS NEVER JOINED TO THE SIGNAL GROUND HERE. The
    # trunk feeds ten stepper drivers and its return current is chopped at their
    # switching rate; sharing a plane with the audio reference would put that
    # current under the one signal a listener hears.
    #
    # ⚠ THIS USED TO SAY "the two meet at the instrument's star point, elsewhere", AND
    # THERE IS NO SUCH POINT. Checked across every board's netlist on 2026-09-17: this
    # is the only board in the instrument with a PWR_GND, and both boards the trunk
    # feeds -- motor_ctrl J3 and optical J2 -- bond the trunk return straight to their
    # own signal ground. So the topology is not a star. It is a TREE: power returns run
    # back to this board's PWR_GND and stop here, signal grounds run back to this
    # board's GND and stop here, and the two domains bond ONCE PER LEAF, at whichever
    # downstream board the cable ends on.
    #
    # ⚠ THAT IS COHERENT AND LOOP-FREE, AND IT ONLY STAYS THAT WAY IF THIS BOARD NEVER
    # TIES THEM. Trace it: panel GND -> USB -> optical GND -> 24 V cable -> panel
    # PWR_GND, and it dead-ends, because there is no path back to panel GND. Add a tie
    # here and that becomes a loop with the stepper return current flowing through a
    # USB cable's ground. So the absence of a tie on this board is not an omission to be
    # tidied up later -- it is the thing that makes the arrangement work, and it is
    # enforced by netcheck's declared_split, which prints on every build.
    # ⚠ AND IT MUST BE LAID OUT THAT WAY TO MEAN ANYTHING: V24/PWR_GND keep their
    # own island in the -Y corner, the pair runs tightly coupled so the loop
    # encloses no area, and NEITHER GROUND POUR may flood across them. A netlist
    # cannot express that; it is a layout obligation and this is where it is
    # written down.
    # THE RESPIN ADDS ONE TAP TO THAT ISLAND -- U5's input -- and that tap is the
    # only thing on it besides the two connectors.
    j6 = Part(name="PJ-102AH", ref_prefix="J", ref="J6", tag="J6", dest="NETLIST", tool="skidl",
              value="PJ-102AH", description="24 V inlet, PCB mount, panel bushing",
              footprint=DC_FP,
              pins=[Pin(num=1, name="TIP", func=P), Pin(num=2, name="SLEEVE", func=P),
                    Pin(num=3, name="SWITCH", func=P)])
    v24 += j6[1]
    pgnd += j6[2], j6[3]      # the switch contact ties to the sleeve, not left open
    # Trunk out on the instrument's standard 4-way, TWO CONTACTS PER RAIL. XH is
    # rated 3 A per contact and BOM.md sizes the 24 V bus at under 5 A, so one
    # contact would sit over its rating and two sit comfortably under.
    j7 = Part(name="B4B-XH-A", ref_prefix="J", ref="J7", tag="J7", dest="NETLIST", tool="skidl",
              value="B4B-XH-A", description="24 V trunk out (2 contacts per rail)",
              footprint=XH_FP,
              pins=[Pin(num=i + 1, name=n, func=P)
                    for i, n in enumerate(("PWR_GND", "+24V", "+24V", "PWR_GND"))])
    pgnd += j7[1], j7[4]
    v24 += j7[2], j7[3]

    # ⚠ J10 -- THE SECOND 24 V TRUNK OUTLET, WHICH FEEDS THE CHAIN'S FAR END (user,
    # 2026-09-18, "option A"). J7 feeds the tee chain at the EAST end; this one runs the
    # length of the instrument to motor_ctrl's J3, and motor_ctrl injects onto the WEST
    # end through its J1. Current then enters the bus from both ends and meets in the
    # middle, so the worst-loaded segment carries roughly half the fleet instead of all
    # of it -- the single +24V contact between tees is the 3 A ceiling this relieves.
    #
    # FOUR WAYS, DOUBLED, AND THAT IS DECIDED BY THE LEDS. This feed carries motor_ctrl
    # plus the Pi (0.70 A) plus the LED strip (1.05 A at full white) before a motor
    # moves, because the strip is driven from the Pi and so lives at that end. A single
    # conductor pair sits at 89 % of one contact with five motors moving and goes over
    # with ten; doubled it is 2.98 A and 5.24 A against 6 A. See BOM.md's power budget.
    #
    # ⚠ AND IT IS THE FOURTH 4-WAY XH THAT IS PIN-INCOMPATIBLE WITH A CAN DROP. Ways 3
    # and 4 are +24V and PWR_GND here; on a CAN drop they are CAN_H and CAN_L, and ways
    # 1-2 agree in both, so a mis-mated node powers up normally and fails on the signal
    # pins -- with 24 V on a transceiver rated -4 to +16. The user's decision is to mark
    # this family rather than key it: DYE THE HOUSINGS, board and cable, at both ends.
    # That makes a wrong plug visible instead of impossible, which is a weaker guarantee
    # than a 5-way shell and costs nothing; the trade is recorded in BOM.md.
    j10 = Part(name="B4B-XH-A", ref_prefix="J", ref="J10", dest="NETLIST", tool="skidl",
               value="B4B-XH-A",
               description="24 V trunk out #2 -- to motor_ctrl J3, west-end feed "
                           "(2 contacts per rail; DYED housing)",
               footprint=XH_FP,
               pins=[Pin(num=i + 1, name=n, func=P)
                     for i, n in enumerate(("PWR_GND", "+24V", "+24V", "PWR_GND"))])
    pgnd += j10[1], j10[4]
    v24 += j10[2], j10[3]


    # ── J8: the magnetic pickup, on SCREW TERMINALS (user) ───────────────────
    # It is the most likely thing anyone ever rewires -- swapping a pickup is a
    # normal thing to do to a guitar -- so it is the one field connection that is
    # neither soldered nor crimped. A pickup arrives as two bare tinned leads; a
    # screw terminal takes them as they are.
    pk_hot = Net("PICKUP_HOT")
    j8 = Part(name="SCREW_2", ref_prefix="J", ref="J8", tag="J8", dest="NETLIST", tool="skidl",
              value="MX126-5.0-02P", description="magnetic pickup in, screw terminals",
              footprint=TERM_FP,
              pins=[Pin(num=1, name="HOT", func=P), Pin(num=2, name="RET", func=P)])
    pk_hot += j8[1]
    agnd += j8[2]             # the coil's return IS the analog reference

    # ⚠ CREATED AFTER J8 ON PURPOSE -- DO NOT MOVE THIS BLOCK UP. SKiDL assigns
    # reference designators by CREATION ORDER and ignores `tag` for that. Written above
    # the pickup terminals, this part became J8 and renumbered the pickup to J9 -- and
    # the placement dictionary is keyed by REF, so the two silently SWAPPED POSITIONS:
    # the 24 V outlet landed on the +Y edge where the pickup belongs, and the pickup
    # landed on the 24 V island. The build printed 59 placements and said nothing.
    # ⚠ J9: THE SECOND 24 V OUTLET, AND THE OPTICAL BOARD HAD NO SOURCE WITHOUT IT.
    # Every 24 V connector in every netlist was listed on 2026-09-17. The instrument had
    # exactly ONE source -- J7 above -- and TWO sinks: the motor controller's J3 and the
    # optical board's J2. One of them was going to be fed by a splice, and the project's
    # standing rule is that every field connection is a connector.
    #
    # It goes here rather than on the optical board's USB feed because that board's 24 V
    # was a deliberate choice and stays one: it keeps the optical board independent of
    # this board's buck sizing, and -- the argument that actually decides it -- moving
    # the switcher here would not remove switching noise from a board carrying twenty
    # nanoamp transimpedance amplifiers, it would only make it SOMEBODY ELSE'S switcher
    # arriving over a cable, at a frequency that board does not control. A local
    # switcher at a chosen 1.1 MHz behind a bead and an LDO beats a remote one.
    #
    # Doubled like J7, though the load does not need it (the optical board draws 79 mA
    # typical, 120 mA worst case, against 3 A per XH contact). The reason is the cable:
    # one crimp order, one four-way housing, one pin order across the instrument, and no
    # conductor that lands on a pin connected to nothing.
    # ⚠ THIS CONNECTOR CUTS THE 24 V BUS IN HALF WHERE IT STANDS, AND DRC CALLS IT TWO
    # UNCONNECTED ITEMS. Measured on the routed board: every +24V and PWR_GND pad lives in
    # one row at y = 128, and the copper has a hole in it between x = 101 and x = 113 --
    # J9 is at 110 to 118, sitting squarely between J7 at 96-104 and the inlet J6 at 130.
    # The two islands that leaves are J6 + J9 on one side and U5 + J7 + D6 + the bulk caps
    # on the other.
    #
    # Read as a topology rather than a count, that is: THE INLET FEEDS ONLY THE OPTICAL
    # PICKUP. This board's own buck never powers up, the 24 V trunk to every pedal and
    # lever board is dead, and the TVS clamp is protecting nothing. A board that cannot
    # turn on, reported as "2 unconnected" -- the same shape of number that hid the
    # GND/PWR_GND split on the optical board.
    #
    # It is also self-inflicted and recent: J9 was added as a second outlet, and dropping
    # a four-pin connector into the corridor between the trunk-out and the inlet is what
    # broke the run. The gaps are 6.50 mm on PWR_GND and 11.50 mm on +24V, both straight
    # along y = 128 and both past link_close_gaps' 5 mm reach, so nothing downstream
    # repairs it either. The answer is placement -- J9 does not belong between them.
    # ⚠ TWO WAYS, NOT FOUR (user, 2026-09-18), AND IT IS A ROUTING FIX AS MUCH AS A
    # CABLE ONE. The optical board draws 79 mA typical and 120 mA worst case against 3 A
    # per XH contact, so the doubling this connector used to carry bought nothing
    # electrically -- it existed so every 24 V cable in the instrument shared one housing
    # and one crimp order. What it COST was five millimetres of the pad row at y -28, and
    # that row is why this board has two unconnected nets: +24V and PWR_GND both sever
    # there, and swapping J7 and J9 around inside the row did not help because the row is
    # full either way. Shrinking a connector is the one move that empties part of it.
    # 5.00 mm is ten lanes for a 0.25 mm track.
    #
    # ⚠ IT WORKED, AND THE COUNT HID IT. The board still reports 2 unconnected, and on
    # that number alone this was first written up as a failure. The COMPOSITION changed:
    # the open nets were +24V and PWR_GND, and they are now PWR_GND and BOOT0. The 24 V
    # BUS IS CLOSED -- the net this whole row exists to carry, and the one a severed
    # panel could not have powered the instrument through. What is left is PWR_GND, still
    # severed, plus BOOT0, a pull-down strap that was previously routed and got displaced.
    #
    # Vacating the 110..113 end of the row left 11.00 mm of clear board between J7's last
    # pad and J9's first, and that is what the bus needed. Re-ordering J7 and J9 inside
    # the row had not helped because re-ordering does not create width; shrinking does.
    #
    # THE LESSON IS ABOUT THE MEASUREMENT, NOT THE CONNECTOR. "2 unconnected" was equally
    # true before and after and describes two different boards. Every comparison in this
    # file that turns on a count should name the NETS -- a swap of one net for another is
    # invisible to the number and can be the whole result.
    #
    # It also removes the mis-mate hazard on this link outright: a 2-way XH cannot enter
    # a 4-way header, so this cable can no longer be plugged into a CAN drop and put
    # 24 V on CAN_H. See the two-pinouts note in BOM.md -- this is the cheap version of
    # the 5-way keying proposal, available here because the current never needed four.
    #
    # The cable and the optical board's J2 must change with it: both ends become 2-way.
    j9 = Part(name="B2B-XH-A", ref_prefix="J", ref="J9", tag="J9", dest="NETLIST", tool="skidl",
              value="B2B-XH-A", description="24 V out to the optical pickup board",
              footprint="Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
              pins=[Pin(num=i + 1, name=n, func=P)
                    for i, n in enumerate(("PWR_GND", "+24V"))])
    pgnd += j9[1]
    v24 += j9[2]

    # ── U1: the MCU. USB HS to the hub, full-duplex I2S, one GPIO for the relay ──
    # Pin numbers off WCH's QFN-68 column (CH32V303/305/307/317 V3.9, table 3-1):
    #   61 PB6  = USBHS_DM      62 PB7  = USBHS_DP
    #   35 PB12 = I2S2 WS       36 PB13 = I2S2 CK       38 PB15 = I2S2 SD  (to DAC)
    #   37 PB14 = I2S2ext SD (FROM the ADC) -- full duplex on ONE clock pair, which
    #            is what lets the ADC and the DAC share BCK/LRCK and stay sample-
    #            aligned with each other without a resampler in between.
    #   25 PC5 relay (the comment said PB0 until 2026-09-21; PB0 is pin 26 -- the WIRING was
    #            always pin 25, so firmware drives PC5), 48 PA13 SWDIO, 52 PA14 SWCLK, 63 BOOT0
    #   39 PC6  = I2S2_MCK -> the ADC's SCKI and the DAC's SCK (256 fS)
    #    1 VBAT -> 3V3 (it was floating: see motor_ctrl.py's note -- the same check that
    #            passed every WIRED pin never asked which pins were not wired)
    # Re-read 2026-09-21 off datasheet V3.8 Table 3-1 (the 303/305/307 table; pages 41-48
    # are the CH32V317's and number these pins differently).
    #
    # ⚠ ALL TEN CHECKED AGAINST THE QFN68 COLUMN, 2026-09-17, ZERO MISMATCHES, read
    # with per-word coordinates so the number taken is the one standing in that
    # column. Nothing downstream can catch a wrong pin number -- SKiDL wires to the
    # NUMBER, layout places the pad it names, DRC agrees the copper matches -- so it
    # is checked here or it is not checked at all. Same pass covered motor_ctrl's
    # twenty-four, which share this package and this table.
    i2s_ck, i2s_ws = Net("I2S_CK"), Net("I2S_WS")
    i2s_sdo, i2s_sdi = Net("I2S_SDO"), Net("I2S_SDI")
    relay = Net("RELAY")
    mcu_pins = [Pin(num=n, func=P) for n in
                (32, 50, 68, 17, 31, 51, 67, 13,        # VDD
                 18, 49, 12, 69,                        # VSS + the exposed pad
                 5, 6, 7,                               # OSC_IN, OSC_OUT, NRST
                 61, 62, 35, 36, 37, 38, 25, 48, 52, 63, 39, 1)]
    u1 = Part(name="CH32V307WCU6", ref_prefix="U", ref="U1", tag="U1", dest="NETLIST", tool="skidl",
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
    mclk = Net("I2S_MCK")
    mclk += u1[39]
    v3v3 += u1[1]             # VBAT: no backup battery, so it is the main supply
    swdio, swclk, boot0 = Net("SWDIO"), Net("SWCLK"), Net("BOOT0")
    swdio += u1[48]
    swclk += u1[52]

    # ⚠ SWDIO AND SWCLK REACHED THE MCU AND STOPPED. Single-node nets: layout drops them
    # as unplaceable, so no copper is ever laid and DRC then compares a clean board
    # against a netlist that never asked for anything. Found 2026-09-17 by running the
    # orphan-pin check across the whole fleet after the optical board had the same fault.
    #
    # THIS BOARD IS NOT AS BAD AS THE LEVER BOARD, which had no way in at all. Here the
    # CH32V307's USB reaches a connector, so WCH's ROM bootloader is reachable in
    # principle -- but BOOT0 goes only to a pull-down and the MCU pin, so entering it
    # means tack-soldering onto a resistor pad, and SWD debugging would be unavailable
    # for the life of the board. Five pads cost nothing and remove both problems.
    for _ref, _net, _what in (("TP1", swdio, "SWDIO"), ("TP2", swclk, "SWCLK"),
                              ("TP3", nrst, "NRST"), ("TP4", gnd, "GND"),
                              ("TP5", v3v3, "target sense")):
        _tp = Part(name="TestPoint", ref_prefix="TP", ref=_ref, dest="NETLIST",
                   tool="skidl", value="SWD",
                   description="SWD pad -- %s; bare copper, no component" % _what,
                   footprint="TestPoint:TestPoint_Pad_D1.5mm",
                   pins=[Pin(num=1, func=P)])
        _net += _tp[1]

    boot0 += u1[63]

    # ══ THE ANALOG HALF, REWIRED FROM TI'S DATASHEETS (2026-09-21) ══════════════════════
    # The 2026-09-17 audit found it unbuildable: both converters' pinouts invented, the DAC on
    # 5 V (abs max 3.9), the ADC's SCKI tied to BCK, and both buffers unable to go below
    # ground. Every pin below is off the part's own Pin Functions table (PCM1808 SLES177B,
    # PCM5102A SLAS859C, both read 2026-09-21), every support part off its typical-application
    # figure (PCM5102A Figure 33; PCM1808 sections 8.2 and 10.1.4). fab.py still holds the
    # board OPEN until someone checks this against the datasheets independently.

    # ── U2: PCM1808PWR, TSSOP-14 -- the magnetic channel's ADC ──────────────
    #   1 VREF 2 AGND 3 VCC(5 V) 4 VDD(3V3) 5 DGND 6 SCKI 7 LRCK 8 BCK 9 DOUT
    #   10 MD0 11 MD1 12 FMT 13 VINL 14 VINR
    # MD1 = MD0 = low: SLAVE mode, SCKI auto-detected at 256/384/512 fS, so the MCU owns BCK
    # and LRCK and the ADC and DAC share one clock. FMT low = I2S.
    # SCKI is the MCU's I2S2_MCK (PC6) -- a real 256 fS master clock. It was tied to BCK
    # (64 fS), which the part cannot run from.
    pk_buf, adc_in, vref = Net("PICKUP_BUF"), Net("ADC_IN"), Net("ADC_VREF")
    u2 = Part(name="PCM1808PWR", ref_prefix="U", ref="U2", tag="U2", dest="NETLIST", tool="skidl",
              value="PCM1808PWR", description="24-bit 99 dB 96 kHz stereo ADC",
              footprint=ADC_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(
                  ("VREF", "AGND", "VCC", "VDD", "DGND", "SCKI", "LRCK", "BCK", "DOUT",
                   "MD0", "MD1", "FMT", "VINL", "VINR"))])
    vref += u2["VREF"]
    agnd += u2["AGND"]
    v5 += u2["VCC"]
    v3v3 += u2["VDD"]
    gnd += u2["DGND"], u2["MD0"], u2["MD1"], u2["FMT"]
    mclk += u2["SCKI"]
    i2s_ws += u2["LRCK"]
    i2s_ck += u2["BCK"]
    i2s_sdi += u2["DOUT"]
    # BOTH inputs take the one buffered pickup (one coil), through ONE coupling cap: the ADC
    # biases its own inputs at VREF (0.5 VCC), 60k each, so the cap is the input HPF --
    # TI's 1 uF gives 2.7 Hz into one input; into the two in parallel, 5.3 Hz.
    adc_in += u2["VINL"], u2["VINR"]

    # ── U3: PCM5102APWR, TSSOP-20 -- the Pi's processed audio, made analog again ──
    #   1 CPVDD 2 CAPP 3 CPGND 4 CAPM 5 VNEG 6 OUTL 7 OUTR 8 AVDD 9 AGND 10 DEMP
    #   11 FLT 12 SCK 13 BCK 14 DIN 15 LRCK 16 FMT 17 XSMT 18 LDOO 19 DGND 20 DVDD
    # EVERY SUPPLY IS 3.3 V (AVDD/CPVDD/DVDD abs max 3.9 V). FLT, DEMP, FMT low: normal
    # latency, no de-emphasis, I2S. SCK takes the same 256 fS MCLK as the ADC (4-wire), so
    # the DAC's clock does not depend on its PLL locking to BCK. XSMT high = un-muted.
    proc = Net("AUDIO_PROC")
    capp, capm = Net("DAC_CAPP"), Net("DAC_CAPM")
    vneg, ldoo = Net("DAC_VNEG"), Net("DAC_LDOO")
    u3 = Part(name="PCM5102APWR", ref_prefix="U", ref="U3", tag="U3", dest="NETLIST", tool="skidl",
              value="PCM5102APWR", description="112 dB stereo DAC, 2.1 Vrms ground-centred out",
              footprint=DAC_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(
                  ("CPVDD", "CAPP", "CPGND", "CAPM", "VNEG", "OUTL", "OUTR", "AVDD", "AGND",
                   "DEMP", "FLT", "SCK", "BCK", "DIN", "LRCK", "FMT", "XSMT", "LDOO", "DGND",
                   "DVDD"))])
    v3v3 += u3["CPVDD"], u3["AVDD"], u3["DVDD"], u3["XSMT"]
    gnd += u3["CPGND"], u3["AGND"], u3["DGND"], u3["DEMP"], u3["FLT"], u3["FMT"]
    capp += u3["CAPP"]
    capm += u3["CAPM"]
    vneg += u3["VNEG"]
    ldoo += u3["LDOO"]
    mclk += u3["SCK"]
    i2s_ck += u3["BCK"]
    i2s_sdo += u3["DIN"]
    i2s_ws += u3["LRCK"]
    proc += u3["OUTL"]
    # ⚠ OUTR IS UNCONNECTED ON PURPOSE AND THAT IS NOW A DECISION, NOT AN OMISSION.
    # The user's call: the PI DOES THE STEREO->MONO SUM IN SOFTWARE. It already
    # chooses what to send here, so it can fold down for the jack while the
    # computer gets full stereo over the gadget port -- two different mixes from
    # one stream.
    Net("DAC_OUT_R_NC").connect(u3["OUTR"])

    # ── U4: the hub. HIGH SPEED -- a FS hub would reintroduce the TT ─────────
    # WCH CH334F, QFN-24 4x4 (LCSC C5187527). Pins off WCH's datasheet V2.5 Table 1-3, the
    # "4F" column (the pin-arrangement FIGURE's package labels are offset by one block --
    # read the table): 1 OVCUR# 2 NC 3 XO 4 XI 5 DM4 6 DP4 7 DM3 8 DP3 9 DM2 10 DP2
    # 11 DM1 12 DP1 13 LED3/SCL 14 DMU 15 DPU 16 RESET# 17 NC 18 NC 19 V5 20 VDD33
    # 21 LED4/SDA 22 LED1/PSELF 23 LED2/PGANG 24 PWREN#, EP = GND.
    # Powered at 3.3 V on BOTH V5 ("5V or 3.3V power input") and VDD33 ("LDO output and
    # 3.3V input"). RESET# has its own pull-up and WCH says leave it open; PSELF and PGANG
    # default high (self-powered, ganged) through their own pull-ups -- both what this board
    # is. OVCUR# is pulled high: nothing here measures port current. Ports 3/4 unused.
    # (The old generic "1 UDP 2 UDM 3 VDD..." pinout matched no real hub.)
    hub_xi, hub_xo, ovcur = Net("HUB_XI"), Net("HUB_XO"), Net("HUB_OVCUR_N")
    u4 = Part(name="CH334F", ref_prefix="U", ref="U4", tag="U4", dest="NETLIST", tool="skidl",
              value="CH334F", description="4-port USB 2.0 HIGH-SPEED hub (2 used): "
              "the MCU and the optical board reach the Pi on ONE cable",
              footprint=HUB_FP, pins=[Pin(num=i, func=P) for i in range(1, 26)])
    ovcur += u4[1]
    hub_xo += u4[3]
    hub_xi += u4[4]
    hub_dn2_dm += u4[9]
    hub_dn2_dp += u4[10]
    hub_dn1_dm += u4[11]
    hub_dn1_dp += u4[12]
    hub_up_dm += u4[14]
    hub_up_dp += u4[15]
    v3v3 += u4[19], u4[20]
    gnd += u4[25]
    for n in (2, 5, 6, 7, 8, 13, 16, 17, 18, 21, 22, 23, 24):
        Net("U4_NC_%d" % n).connect(u4[n])

    # ── U5: 24 -> 5 V. THE ONE SWITCHER, and it lives in the inlet corner. ───
    # TI SNVSA24 (LMR16006): 1 CB, 2 GND, 3 FB, 4 SHDN (float = enabled), 5 VIN,
    # 6 SW. Same part the lever board and the motor controller use, so the respin
    # adds a circuit but no SKU.
    sw, v5_pre, boot, fb = Net("SW"), Net("V5_PRE"), Net("BOOT"), Net("FB")
    # ── THE POWER BUDGET, ITEMISED -- because nothing added it up here either ────
    # The optical board got this treatment on 2026-09-17 and it found a buck at 54 % with
    # a worst-case row over its rating. This board has a 0.6 A buck, a relay coil and a
    # USB hub, and had no derivation at all. Every figure below is from the part's own
    # datasheet at this board's operating point, EXCEPT the two marked (est).
    #
    #   on 3V3 (all of it reaches the buck 1:1 through the LDO)
    #     CH32V307 @144 MHz, ext clock, all peripherals   22.4 mA   (WCH DS V2.9 p63)
    #     PCM1808   ICC 8.6 typ / 11 max  @48 kHz
    #               IDD 5.9 typ /  8 max  @48 kHz         14.5 / 19 (TI DS p6)
    #     PCM5102A  DVDD 8 / 9 + AVDD/CPVDD 11..22         19 / 31  (TI DS p9-10)
    #     op-amps, phantom guard, pulls                    ~5
    #   on 5V directly
    #     relay coil, FRT5-class 5 V, energised            ~40 (est)
    #     USB 2.0 HS hub                                   ~50 (est)
    #                                             total   ~151 / 167 mA
    #                                                      25 / 28 % of the buck
    #
    # ⚠ THE TWO ESTIMATES ARE THE WHOLE UNCERTAINTY AND THEY ARE BOUNDED. Even at double
    # both -- 80 mA of coil and 100 mA of hub -- the total is 257 mA, 43 % of the buck.
    # There is no plausible version of this board that runs out of buck, which is the
    # question worth answering; the exact figure is not.
    #
    # ⚠ THE RELAY IS THE ONE WORTH RE-READING. It is DE-ENERGISED = DIRECT, so the coil
    # draws nothing in the bypass path and its ~40 mA appears only when the processed path
    # is selected. That is the right way round for a true-bypass design -- a dead board
    # passes signal -- and it also means the worst-case supply current and the worst-case
    # audio path are the same state, not opposite ones.

    u5 = Part(name="LMR16006XDDCR", ref_prefix="U", ref="U5", tag="U5", dest="NETLIST", tool="skidl",
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
    u6 = Part(name="LDO_3V3", ref_prefix="U", ref="U6", tag="U6", dest="NETLIST", tool="skidl",
              value="AP2112K-3.3TRG1", description="5 V -> 3V3, AFTER the bead",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=i, func=P) for i in range(1, 6)])
    v5 += u6[1], u6[3]        # IN and EN; EN tied on
    gnd += u6[2]
    Net("LDO_NC").connect(u6[4])
    v3v3 += u6[5]

    # ── U7/U8: the two analog buffers ────────────────────────────────────────
    # ⚠ BOTH BUFFERS RUN AT MID-RAIL NOW (2026-09-21). They sit on 0..5 V, and neither
    # signal they carry is: the pickup is AC about 0 V and the DAC's OUTL is GROUND-CENTRED
    # (its charge pump makes the negative rail). Each op-amp input is AC-coupled and biased
    # at VMID = 2.5 V, so the whole waveform fits the rail instead of the bottom half
    # clipping at ground.
    sel, buf = Net("AUDIO_SEL"), Net("BUF_OUT")
    u7_in, pk_in, vmid = Net("OUT_BUF_IN"), Net("PICKUP_IN"), Net("VMID")
    u7 = Part(name="OPAMP", ref_prefix="U", ref="U7", tag="U7", dest="NETLIST", tool="skidl",
              value="TLV9061IDBVR", description="output buffer -- drives the TS jack",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                    Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                    Pin(num=5, name="V+", func=P)])
    buf += u7[1], u7[4]       # unity-gain follower
    agnd += u7[2]
    u7_in += u7[3]            # AC-coupled from the relay's common, biased at VMID
    v5 += u7[5]
    # ⚠ U8 IS NEW WITH THE PICKUP, AND IT IS WHAT MAKES ONE COIL FEED TWO THINGS.
    # The ADC and the relay's direct contact both want the pickup, and a magnetic
    # pickup's tone IS its loading -- hang two inputs straight on the coil and you
    # have changed the instrument's sound. One buffer, two taps off its output, so
    # the coil sees a single high impedance whichever mode is selected.
    u8 = Part(name="OPAMP", ref_prefix="U", ref="U8", tag="U8", dest="NETLIST", tool="skidl",
              value="TLV9061IDBVR", description="pickup buffer -- feeds BOTH the "
              "relay's direct contact and the ADC, so the coil sees one load",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                    Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                    Pin(num=5, name="V+", func=P)])
    pk_buf += u8[1], u8[4]
    agnd += u8[2]
    pk_in += u8[3]            # the coil through C37, biased at VMID through R8 (1M)
    v5 += u8[5]

    # ── K1/Q1: direct vs processed. DE-ENERGISED IS DIRECT. ──────────────────
    # With no power, no Pi and no firmware the magnetic pickup reaches the jack
    # through a mechanical contact, so the instrument is still a guitar when
    # everything clever about it is off.
    # ⚠ AND IT IS NOT LATCHING, WHICH CORRECTS ME: I wrote on the optical board
    # that latching was required because "a held coil hums at the audio it is
    # switching". Wrong -- the coil is driven with DC and a static field does not
    # hum. The real cost of holding it is ~30 mA, which this rail has.
    # OMRON G6K-2F-Y-DC5 (LCSC C326376), off Omron's own terminal arrangement (TOP VIEW,
    # datasheet p.6): coil 1 (+) / 8 (-); pole A COM 3, NC 2, NO 4; pole B COM 6, NC 7, NO 5.
    # It replaces an "FRT5-class" part numbered 1..10 with no datasheet behind it -- the
    # FRT5's own maker publishes no pin diagram that could be found, and its SMD variant is
    # not stocked where this board is built. Pole B is spare.
    # BOTH THROWS ARE AC-COUPLED (C38 on the direct side, the DAC is ground-centred already),
    # and the common is held at 0 V by R15 -- so switching between them moves no DC and
    # makes no click.
    coil, direct, dac_att = Net("RELAY_COIL"), Net("DIRECT_AC"), Net("DAC_ATT")
    k1 = Part(name="G6K-2F-Y", ref_prefix="K", tag="K1", dest="NETLIST", tool="skidl",
              value="G6K-2F-Y-DC5", description="true-bypass select; DE-ENERGISED = DIRECT "
              "(LCSC C326376)", footprint=RELAY_FP, pins=[Pin(num=i, func=P) for i in range(1, 9)])
    v5 += k1[1]
    coil += k1[8]
    sel += k1[3]
    direct += k1[2]
    dac_att += k1[4]
    for i in (5, 6, 7):
        Net("K1_NC_%d" % i).connect(k1[i])
    q1 = Part(name="Q_NMOS", ref_prefix="Q", tag="Q1", dest="NETLIST", tool="skidl",
              value="AO3400A", description="relay coil driver (LCSC C20917)",
              footprint="Package_TO_SOT_SMD:SOT-23",
              pins=[Pin(num=1, name="G", func=P), Pin(num=2, name="S", func=P),
                    Pin(num=3, name="D", func=P)])
    gnd += q1[2]
    coil += q1[3]

    # ── crystals ─────────────────────────────────────────────────────────────
    y1 = Part(name="Crystal", ref_prefix="Y", ref="Y1", tag="Y1", dest="NETLIST", tool="skidl",
              value="8MHz", description="MCU HSE -- the PLL source for USB HS",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=i, func=P) for i in range(1, 5)])
    osc_in += y1[1]
    osc_out += y1[3]
    gnd += y1[2], y1[4]
    y2 = Part(name="Crystal", ref_prefix="Y", ref="Y2", tag="Y2", dest="NETLIST", tool="skidl",
              value="12MHz", description="hub reference",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=i, func=P) for i in range(1, 5)])
    hub_xi += y2[1]
    hub_xo += y2[3]
    gnd += y2[2], y2[4]

    # ── L1 / FB1: the buck's output, and the ONE place the rails join ────────
    l1 = Part(name="L", ref_prefix="L", ref="L1", tag="L1", dest="NETLIST", tool="skidl",
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
    fb1 = Part(name="FerriteBead", ref_prefix="FB", ref="FB1", tag="FB1", dest="NETLIST",
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
    d5 = _d("D5", "ESD5B5.0ST1G", "bidirectional 5 V TVS (LCSC C93623): catches the "
            "insertion edge C1 passes through. The node it sits on idles at VMID and swings "
            "0..5 V, inside its 5.0 V working voltage")
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
    r8 = _r("R8", "1M", "pickup input bias to VMID -- and the LOAD the pickup sees, which "
            "sets its tone: 1M is a typical amplifier input")
    pk_in += r8[1]
    vmid += r8[2]
    r9 = _r("R9", "220R", "output series -- bounds a phantom-power fault and C1's inrush")
    buf += r9[1]
    blocked += r9[2]
    r10 = _r("R10", "100k", "output bleed -- stops the DC block thumping on unplug")
    outp += r10[1]
    agnd += r10[2]
    # VFB is 0.765 V (LMR16006 datasheet SNVSA24, "voltage reference (FB pin)"), so for
    # 5 V the bottom leg is 100k x 0.765 / (5 - 0.765) = 18.06k; 18k2 gives 4.97 V. The
    # lever board runs the same part at 3.3 V with 100k / 30k1, which is the same
    # arithmetic -- worth saying out loud, because "set at the bench" is not a value and
    # a divider with no value is a converter with no output voltage.
    r11 = _r("R11", "100k", "buck feedback divider, top")
    r12 = _r("R12", "18k2 1%", "buck feedback divider, bottom -- 4.97 V with R11")
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
            ("C14", "100nF", v3v3, agnd, "DAC AVDD bypass -- 3V3, never 5 V (abs max 3.9)")):
        fp = ("Capacitor_SMD:C_0805_2012Metric" if val == "10uF"
              else "Capacitor_SMD:C_0402_1005Metric")
        c = _c(tag, val, desc, fp)
        net += c[1]
        ref += c[2]
    for tag, net in (("C15", osc_in), ("C16", osc_out), ("C17", hub_xi), ("C18", hub_xo)):
        c = _c(tag, "12pF", "crystal load")
        net += c[1]
        gnd += c[2]

    # ── the analog rewrite's parts (2026-09-21) ────────────────────────────────
    C0805 = "Capacitor_SMD:C_0805_2012Metric"
    dac_filt = Net("DAC_FILT")
    for tag, val, a, b, desc, fp in (
            # U2, PCM1808: VREF, VCC and VDD each 0.1 uF + 10 uF (TI 10.1.4 / 8.2 C3-C5);
            # C13 is VCC's 0.1 uF
            ("C19", "100nF", vref, agnd, "ADC VREF", None),
            ("C20", "10uF", vref, agnd, "ADC VREF bulk", C0805),
            ("C21", "10uF", v5, agnd, "ADC VCC bulk", C0805),
            ("C22", "100nF", v3v3, gnd, "ADC VDD", None),
            ("C23", "10uF", v3v3, gnd, "ADC VDD bulk", C0805),
            ("C24", "1uF", pk_buf, adc_in, "ADC input coupling (TI's 1 uF)", C0805),
            # U3, PCM5102A, Figure 33: AVDD / CPVDD / DVDD / LDOO each 0.1 + 10 uF, the charge
            # pump's flying cap and VNEG 2.2 uF each; C14 is AVDD's 0.1 uF
            ("C25", "10uF", v3v3, agnd, "DAC AVDD bulk", C0805),
            ("C26", "100nF", v3v3, gnd, "DAC CPVDD", None),
            ("C27", "10uF", v3v3, gnd, "DAC CPVDD bulk", C0805),
            ("C28", "100nF", v3v3, gnd, "DAC DVDD", None),
            ("C29", "10uF", v3v3, gnd, "DAC DVDD bulk", C0805),
            ("C30", "100nF", ldoo, gnd, "DAC LDOO", None),
            ("C31", "10uF", ldoo, gnd, "DAC LDOO bulk", C0805),
            ("C32", "2.2uF", capp, capm, "DAC charge-pump flying cap", C0805),
            ("C33", "2.2uF", vneg, gnd, "DAC VNEG", C0805),
            ("C34", "2.2nF C0G", dac_filt, agnd, "DAC output filter, with R13 "
             "(TI's recommended 470R + 2.2 nF)", None),
            # U4, CH334F: V5 >= 1 uF, VDD33 0.1 + 10 uF (C12 is the 0.1)
            ("C35", "1uF", v3v3, gnd, "hub V5", None),
            ("C36", "10uF", v3v3, gnd, "hub VDD33 bulk", C0805),
            # the buffers
            ("C37", "100nF C0G", pk_hot, pk_in, "pickup input coupling -- 1.6 Hz into R8's "
             "1M. C0G: a coupling cap in the coil's own path must not have a voltage "
             "coefficient", "Capacitor_SMD:C_1206_3216Metric"),
            ("C38", "1uF", pk_buf, direct, "direct-path coupling to the relay -- 16 Hz into "
             "R15's 10k, two octaves under the lowest string (C2, 65 Hz)", C0805),
            ("C39", "1uF", sel, u7_in, "output buffer input coupling (1.6 Hz into R16)", C0805),
            ("C40", "10uF", vmid, agnd, "VMID reservoir", C0805)):
        c = _c(tag, val, desc, fp) if fp else _c(tag, val, desc)
        a += c[1]
        b += c[2]
    for tag, val, a, b, desc in (
            ("R13", "470R", proc, dac_filt, "DAC output filter, with C34"),
            ("R14", "10k", dac_filt, dac_att, "DAC -6 dB with R15: 2.1 Vrms (5.9 Vpp) is "
             "more than a 5 V rail carries; ~3 Vpp after this"),
            ("R15", "10k", sel, agnd, "relay common to 0 V -- no DC step when it switches"),
            ("R16", "100k", u7_in, vmid, "output buffer bias to VMID"),
            ("R17", "100k", v5, vmid, "VMID divider, top"),
            ("R18", "100k", vmid, agnd, "VMID divider, bottom"),
            ("R19", "10k", ovcur, v3v3, "hub OVCUR# pulled inactive")):
        r = _r(tag, val, desc)
        a += r[1]
        b += r[2]


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
# How far each panel connector's body front stands past the +X edge: the fit clearance
# between the board and the endplate's panel, plus the panel itself. src/electronics.py
# builds the panel to the same two numbers (OP_PANEL_CLR, OP_PANEL_T), and
# reads the placed board back from <board>.geom.json rather than trusting these.
PANEL_CLR, PANEL_T = 0.3, 1.6
PANEL_OVERHANG = PANEL_CLR + PANEL_T
_FRONT = {"J5": 13.40, "J1": 7.07, "J6": 10.70}
J1_SETBACK = 0.40
TS_CLAMP_T, TS_HEAD_T, TS_STUB = 4.0, 2.05, 3.0   # Neutrik: clamp 3.0..4.7; nut head; stub
TS_SHOULDER_DEPTH = TS_CLAMP_T + TS_HEAD_T         # 6.05: face -> jack shoulder

# THE MOUNTING EAR (user, 2026-09-21): "extend the PCB ... so we have room to put an M4 hole?
# Having the screw adjacent like you have now doesn't provide as strong of retention." Right --
# a head clamping the board round a hole holds it every way; a screw BESIDE the edge laps ~1 mm
# of it. The ear is a TAB off the -X edge at the -Y corner, where the side screw used to stand:
# the -X edge above it is where J2/J3/J4's mouths have to stay, so a tab costs nothing a wider
# board would. Bare laminate -- the pours cover only the outline_mm LAYOUT REGION -- so nothing
# is under the head. Same ear and hole as the CAN tee's (can_tee.EAR_*).
EAR_W, EAR_H = 9.5, 8.7
EAR_HOLE_D = 4.5                                   # M4 clearance
_EAR_X0 = -BOARD_W / 2 - EAR_W
_EAR_Y1 = -BOARD_L / 2 + EAR_H
EAR_HOLE_XY = (_EAR_X0 + EAR_W / 2, -BOARD_L / 2 + EAR_H / 2)

BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "outline_poly": [(_EAR_X0, -BOARD_L / 2), (BOARD_W / 2, -BOARD_L / 2),
                     (BOARD_W / 2, BOARD_L / 2), (-BOARD_W / 2, BOARD_L / 2),
                     (-BOARD_W / 2, _EAR_Y1), (_EAR_X0, _EAR_Y1)],
    "cutouts": [{"xy": EAR_HOLE_XY, "d": EAR_HOLE_D}],
    "mounting_hole_xy": EAR_HOLE_XY,
    # the ear moved the router's first-pass choices and BOOT0 (a one-resistor strap across
    # the digital block) came back unrouted at the default pass count; more passes let the
    # optimiser rip up and re-lay rather than freeze the early mess (route.py PASSES note)
    "router_passes": 20,
    # THE HUB'S THREE PAIRS ARE LAID AS PAIRS (2026-09-21). With the CH334F's real pinout the
    # upstream and downstream pins sit on different faces of the package than the invented
    # one put them, and freerouting -- which has no notion of a pair -- came back with
    # HUB_UP split across layers and HUB_DN1 12 mm skewed and split too (fab.py's budgets).
    # layout._diff_pairs routes each one off a single centreline, the optical board's USB
    # way, and freezes it before the router runs. THRU (J1 -> J2) routes clean as it is.
    # (HUB_UP stays with the router: J3 stands at 270 deg, its A/B pad rows run along Y,
    #  and _diff_pairs' flip-merge only handles rows along X. It routed as a pair before.)
    # (HUB_DN1 stays with the router too: _diff_pairs cannot fan a coupled pair out of the
    #  MCU's 0.4 mm-pitch QFN -- it reports an ESCAPE failure, a placement limit of the
    #  routine. With U4 turned to face U1 and the SWD pads moved off the MCU's top edge, the
    #  router has a direct corridor for it.)
    "diff_pairs": [{"nets": ["HUB_DN2_DP", "HUB_DN2_DM"], "chain": ["U4", "J4"],
                    "gap": 0.2, "width": 0.2}],
    "diff_pair_inner": "In2.Cu",
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
    # ⚠ THE 24 V RAILS ARE NOT SIGNAL NETS AND WERE BEING DRAWN AS IF THEY WERE. At the
    # board default of 0.25 mm they carry 0.88 A of 1 oz outer copper (IPC-2221, 10 C
    # rise) while the bus budget is under 5 A -- the cable and the connector contacts were
    # both sized for that figure and audited, and the traces between them never were.
    # 0.5 mm takes them to 1.45 A, which is as far as a blanket width can go here: these
    # nets land on 0402 decoupling parts whose pads are 0.6 mm, and freerouting does not
    # neck down into a land.
    #
    # ⚠ THE 0.5 mm FIGURE READ 1.6 A UNTIL IT WAS RECOMPUTED, AND 1.6 WAS NEVER COMPUTED.
    # The 0.88 and the 2.8 both come straight out of IPC-2221; the middle number looks
    # like 0.88 rounded up by eye. It scales as area^0.725, not linearly, so doubling the
    # width buys 1.65x and not 2x: 0.88 * 2**0.725 = 1.45. Recorded because it is the
    # only one of the three that was a guess wearing the same units as the other two.
    # Reproduce any of them with, external copper and a 10 C rise:
    #     I = 0.048 * dT**0.44 * (w_mm/0.0254 * 1.378*oz)**0.725     # w in mil, t in mil
    # -> 0.25 mm 0.88 A, 0.5 mm 1.45 A, 2.0 mm 3.95 A, 2.8 mm 5.05 A.
    # ⚠ SO THIS IS AN IMPROVEMENT AND NOT THE FIX. The J6 -> J7 pass-through still carries
    # the fleet's whole <5 A and wants about 2.8 mm at a 10 C rise, or 1.8 mm if a 20 C
    # rise is accepted. That is deliberate trunk copper, not a netclass number.
    "net_widths": {"+24V": 0.5, "PWR_GND": 0.5},
    # ⚠ THE TRUNK NEEDS DELIBERATE COPPER AND ONE LAYER CANNOT CARRY IT -- THE RAILS ARE
    # INTERLEAVED ON THE CONNECTOR. J6 -> J7 passes the fleet's whole <5 A and wants about
    # 2.8 mm at a 10 C rise; 0.5 mm of netclass is 1.45 A. Tried it: 2.0 mm lanes on B.Cu,
    # which is empty across this whole region (zero tracks in x 95..135, y 112..132), with
    # +24V at y = 121 and PWR_GND at y = 124, tapping down to the through-hole pads.
    #
    # It took the board from 2 unconnected to 4, and the reason is in the pinout. Both
    # outlets are wired PWR_GND, +24V, +24V, PWR_GND -- the rails doubled for contact
    # rating, which puts the +24V pads BETWEEN the PWR_GND pads. Two lanes on one layer
    # cannot both reach their own pads: whichever lane is farther from the row has to
    # cross the nearer one to tap down, and on a single layer that is a short. Mirroring
    # the lanes just moves the crossing to the other rail. The trunk that did get laid
    # joined J7 to J6 and stranded J9 and J6's remaining contacts instead.
    #
    # Three ways out, none of them a routing change, all of them a decision:
    #   * split the rails across layers -- +24V on B.Cu, PWR_GND on In2.Cu. They never
    #     meet and the through-hole pads join them. But 0.5 oz inner copper at 2 mm is
    #     about 1.1 A, so the RETURN would be the weak link instead of the feed.
    #   * pour PWR_GND on In2.Cu over the connector row. Area beats width for a return,
    #     and it is the normal answer -- but the router uses In2.Cu on this board, so the
    #     pour has to be bounded rather than board-wide.
    #   * group the rails in the pinout: PWR_GND, PWR_GND, +24V, +24V instead of
    #     interleaved. Then two lanes separate cleanly on one layer.
    #     ⚠ TRIED 2026-09-18 ACROSS THE WHOLE FLEET AND IT IS WORSE ON EVERY BOARD. All
    #     five doubled-rail connectors were regrouped at once -- this board's J7 and J9,
    #     optical's J2, motor_ctrl's J3 and its J5 5 V feed -- because a half-applied
    #     convention builds one cable wrong. Measured:
    #         output_panel  2 -> 3 unconnected
    #         optical       1 -> 2
    #         motor_ctrl    0 -> 1   (it lost a finished board)
    #     Reverted. The interleaved order is not an accident to be tidied: GND on the
    #     outside puts a return either side of the pair, which is what the pour and the
    #     escape both want, and grouping forces each rail to reach one side only. The
    #     argument in this note is still correct about the CROSSING and wrong about what
    #     it costs to remove it.
    #
    # Left undone deliberately: the board is better at 2 unconnected with 0.5 mm rails
    # than at 4 with a trunk that strands two connectors.
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
    # ⚠ THIS BOARD DECLARED NO MATCHED GROUPS AT ALL, and it carries FOUR USB 2.0
    # high-speed pairs. verify.py exists for exactly the failure that leaves: "a router
    # can produce a DRC-perfect board on which the USB pair is split across two layers
    # and takes two unrelated paths, and nothing in the pipeline would notice". Nothing
    # in the pipeline was noticing here, on the board that is the instrument's USB hub.
    #
    # One group per pair -- skew is intra-pair, so lumping all eight nets into one group
    # would measure the distance between unrelated ports.
    #
    # ⚠ 8.3 mm IS DERIVED, AND IT IS A RELAXATION OF THE NUMBER THIS STARTED WITH.
    # The first version copied the optical board's 2.5 mm, and THRU failed it at 2.98 --
    # at which point the number had to be defended rather than enforced, because 2.5 does
    # not follow from anything. Neither board's note ever derived it; both argue that at
    # 480 Mbps "skew has room" and that PAIRNESS is the real constraint, which is an
    # argument for a LOOSE budget and then writes a tight one.
    #
    # Two independent bases, and they agree:
    #   * USB 2.0 spec gives the HS driver a 500 ps MINIMUM rise time, and the standard
    #     SI criterion is to hold intra-pair skew under 10 % of the rise time to limit
    #     differential-to-common mode conversion. 50 ps.
    #   * USB-IF budgets ~100 ps of intra-pair skew for a cable assembly; half of that
    #     for the board is 50 ps.
    # At 6.0 ps/mm in FR4 -- the same figure the ULPI budget uses -- that is 8.3 mm.
    #
    # This is NOT fitted to the board: both bases are computed from the standard with no
    # reference to what this board measures, and they land on the same number. Measured,
    # the worst pair is THRU at 2.98 mm = 17.9 ps = 3.6 % of the rise time. Same move the
    # ULPI budget made when it went 12 -> 80 mm: an undefended limit replaced by a
    # derived one, in the direction the evidence pointed.
    "match": [
        {"name": "HUB_UP", "max_skew_mm": 8.3, "same_layer": True, "max_vias": 2,
         "nets": ["HUB_UP_DP", "HUB_UP_DM"],
         "why": "USB 2.0 high speed, hub upstream -- the whole board's traffic to the Pi. 480 Mbps is 2,080 ps a bit, so skew has "
                "room; what has to hold is that the two stay a PAIR on the same "
                "layers -- differential impedance is a property of the two "
                "conductors' geometry relative to each other, and a layer split "
                "destroys it -- and that neither collects vias, each being an "
                "impedance discontinuity."},
        {"name": "HUB_DN1", "max_skew_mm": 8.3, "same_layer": True, "max_vias": 2,
         "nets": ["HUB_DN1_DP", "HUB_DN1_DM"],
         "why": "USB 2.0 high speed, hub downstream port 1. 480 Mbps is 2,080 ps a bit, so skew has "
                "room; what has to hold is that the two stay a PAIR on the same "
                "layers -- differential impedance is a property of the two "
                "conductors' geometry relative to each other, and a layer split "
                "destroys it -- and that neither collects vias, each being an "
                "impedance discontinuity."},
        {"name": "HUB_DN2", "max_skew_mm": 8.3, "same_layer": True, "max_vias": 2,
         "nets": ["HUB_DN2_DP", "HUB_DN2_DM"],
         "why": "USB 2.0 high speed, hub downstream port 2. 480 Mbps is 2,080 ps a bit, so skew has "
                "room; what has to hold is that the two stay a PAIR on the same "
                "layers -- differential impedance is a property of the two "
                "conductors' geometry relative to each other, and a layer split "
                "destroys it -- and that neither collects vias, each being an "
                "impedance discontinuity."},
        {"name": "THRU", "max_skew_mm": 8.3, "same_layer": True, "max_vias": 2,
         "nets": ["THRU_DP", "THRU_DM"],
         "why": "USB 2.0 high speed, front-panel pass-through. 480 Mbps is 2,080 ps a bit, so skew has "
                "room; what has to hold is that the two stay a PAIR on the same "
                "layers -- differential impedance is a property of the two "
                "conductors' geometry relative to each other, and a layer split "
                "destroys it -- and that neither collects vias, each being an "
                "impedance discontinuity."},
    ],
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
    # ⚠ THE SEVERED 24 V BUS, CLOSED AS A POST-ROUTE REPAIR. Both power rails break in
    # the -Y connector row and three attempts to fix it as a ROUTING problem all failed:
    # re-ordering J7 and J9 inside the row changed nothing, a 2.0 mm B.Cu lane under it
    # went 2 unconnected to 4, and shrinking J9 to a 2-way freed 5 mm of row and closed
    # +24V for one build only. The row is full; re-ordering a full row does not empty it.
    #
    # Measured against every obstacle class on the ROUTED board (elec/repair_search.py):
    # PWR_GND's two ends see each other directly at 0.5 mm wide, and +24V needs one step
    # out of the row -- 1.50 mm to y -29.50 -- to get past what sits between J7 and J9.
    # Both at 0.5 mm, the width these rails already carry (1.45 A of 1 oz outer copper),
    # not the 0.25 signal default.
    #
    # Applied AFTER routing, like optical's MID detour, so the other 43 nets never plan
    # around them. Pinned to THIS routing: re-run repair_search after any netlist change.
    # THE HUB'S BELLY VIA, placed by hand: U4.25 is a stitch exception (the DN2 pair runs
    # under the package on In2, and the automatic belly via landed on it) but a QFN belly is
    # walled in by its own pins, so the pour cannot reach it either -- it came back
    # UNCONNECTED. This via sits in the pad's north half, 0.7 clear of DM on In2 at y -8.41.
    # The pair is laid deterministically by _diff_pairs, so this does not drift with the
    # router the way the repairs below do.
    "repair_vias": [("GND", -15.500, -7.300)],
    "repair_tracks": [
        # (the PWR_GND hop that stood first here is gone: since the mounting ear the router
        #  closes PWR_GND on its own, and the pinned copy crossed its V5_PRE, 2026-09-21)
        # ON B.Cu: the J7 -> J9 hop runs pad to pad UNDER the row. Both ends are THT pads,
        # so it needs no via, and B.Cu is empty there -- where on F.Cu the router's own
        # PWR_GND edge run (at y -30.05 since the board grew its mounting ear) crossed it.
        ("+24V", "B.Cu", 0.5, [(-1.250, -28.000), (-1.250, -29.500)]),
        ("+24V", "B.Cu", 0.5, [(-1.250, -29.500), (17.250, -29.500)]),
        ("+24V", "B.Cu", 0.5, [(17.250, -29.500), (17.250, -28.000)]),
        ("+24V", "F.Cu", 0.5, [(17.250, -29.500), (17.250, -28.000)]),
        # THE INLET'S OWN PIN. Turning J6 90 degrees so its mouth faces the panel put its
        # +24V pin (1, the centre pin) at the REAR corner of the body, and the router could
        # not get a trace out of it to either side -- the only two unconnected items on the
        # board. It sits straight above the end of the bus run above, so the bus simply
        # continues to it. Both runs pass under J6's plastic body, clear of its PWR_GND
        # pins at x 28.2 and 31.2.
        # ⚠ J10's +24V PADS ARE 2 AND 3 (x 28.45, 30.95), NOT PAD 1. Pad 1, straight above
        # this pin at x 25.95, is PWR_GND -- the first draft of this run landed on it, which
        # is a dead short across the 24 V bus. The run turns along y -12, below J10's pad
        # row, and comes up into pad 2.
        ("+24V", "F.Cu", 0.5, [(17.250, -29.500), (25.200, -29.500)]),
        ("+24V", "F.Cu", 0.5, [(25.200, -29.500), (25.200, -21.500)]),
        ("+24V", "F.Cu", 0.5, [(25.200, -21.500), (25.200, -12.000), (28.450, -12.000),
                               (28.450, -8.700)]),
    ],
    "stitch_nets": ("GND",),
    # ⚠ THE USB SHIELD TABS REACH THE PLANE THROUGH THEIR OWN BARRELS. J2.SH and J4.SH
    # are the shells' through-hole mounting tabs: big PTH pads whose plated barrel already
    # passes every layer, so a stitching via beside them adds copper that connects
    # nothing new. They used to be stitched via-in-pad -- a via dropped at the pad centre,
    # straight into the pad's own hole, which DRC reports as holes_co_located and grades
    # a WARNING, so it sat unnoticed behind a "0 violations" summary.
    #
    # With via-in-pad correctly refused for through-hole pads, these two have no room
    # BESIDE them either, and layout stopped the build rather than leave them unstitched.
    # That stop is right in general (an SMD pad on the pour alone can be orphaned by
    # routing) and wrong for these two specifically, which is exactly what this list is
    # for: a pad that really can live without a via, named with the reason.
    # U4.25 is the hub's exposed pad: the DN2 pair is pre-laid on In2 straight under the
    # package toward J4, and a through via at the pad's centre lands on it. The hub draws
    # ~50 mA and its pad reaches ground through the F.Cu pour it sits in; nothing here
    # needs that via, and the pair does.
    "stitch_exceptions": ("J2.SH", "J4.SH", "U4.25"),
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
        # +X, THE PANEL FACE. Each connector's BODY FRONT overhangs the board edge by
        # PANEL_OVERHANG, so it passes through the endplate's panel and finishes FLUSH
        # with the instrument's face -- which is where a player's plug has to meet it.
        #
        # ⚠ THIS USED TO SAY "all three flush to the edge", AND IT WAS THE COURTYARDS THAT
        # WERE FLUSH. A courtyard is the keep-out, not the part: it is bigger than the body,
        # so both bodies stopped 0.54 mm SHORT of the edge, behind a 4 mm wall, ~4.8 mm
        # inside the instrument. And J6 was at 0 degrees, where this footprint's mouth
        # (its local +Y) points along the board at the chassis rail -- a panel inlet no
        # hole in the panel could ever reach. Every check agreed with it, because every
        # check compared a copy of these numbers to these numbers.
        #
        # _FRONT is the body front ahead of the pad-centroid anchor, MEASURED off the
        # routed board's F.Fab (J6 after the 90-degree turn: 13.7 of body ahead of pin 1,
        # pin 1 3.0 behind the centroid).
        # ...AND J5 IS THE EXCEPTION THE OTHER WAY, set so its PLUG meets the face level with
        # the other two (user: "all at the same installation x value"). The NMJ4HCD2 is a
        # REAR-PANEL-MOUNT jack (Neutrik ST-NMJ4HCD2 + its STEP, read 2026-09-21): a 3.0 mm
        # O11.4 stub in front of the shoulder locates in the panel's O11.4 hole, and a
        # separate nose nut -- 2.05 hex head (A/F 11) on a 3.74 shank -- screws into the jack
        # and clamps the panel against the shoulder. The clamped thickness has to be 3.0..4.7
        # (the drawing's three 1.2 washers build thin panels up to it). So the endplate
        # thickens to a 4.0 clamp around this jack and counterbores the face 2.05 for the
        # nut's head: the head's front -- where a plug seats -- finishes flush. That puts the
        # SHOULDER TS_SHOULDER_DEPTH (6.05) behind the face; _FRONT["J5"] is to the F.Fab
        # front, which is the stub's tip, 3.0 ahead of the shoulder.
        "J5": (BOARD_W / 2 + PANEL_OVERHANG - TS_SHOULDER_DEPTH + TS_STUB
               - _FRONT["J5"], 21.50, 0.0),                                    # 1/4 in jack
        # ...EXCEPT J1, WHICH CANNOT GO AS FAR. Its front shell legs are plated oval pads
        # 1.60 long in X, and at the full overhang their far end crossed the board edge
        # (DRC: 0.000 against the 0.3 copper-to-edge rule -- a plated barrel the router
        # would cut in half). J1_SETBACK is what buys the 0.3: the USB-C finishes that far
        # behind the panel face, and the endplate opens an OVERMOLD-sized window for it so
        # a plug still seats fully (see electronics.OP_PANEL).
        "J1": (BOARD_W / 2 + PANEL_OVERHANG - J1_SETBACK - _FRONT["J1"], 4.00, 90.0),
        "J6": (BOARD_W / 2 + PANEL_OVERHANG - _FRONT["J6"], -19.93, 90.0),  # 24 V barrel
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
        "R8": (-3.20, 24.90, 0.0),
        "U2": (2.50, 29.00, 0.0),       # ADC
        # the ADC's supports fill the strip under it that the DAC vacated (2026-09-21)
        "C19": (0.00, 25.30, 0.0),      # VREF 0.1
        "C13": (2.20, 25.30, 0.0),      # VCC 0.1
        "C22": (4.40, 25.30, 0.0),      # VDD 0.1
        "C20": (-0.40, 22.90, 0.0),      # VREF 10u
        "C21": (3.10, 22.90, 0.0),      # VCC 10u
        "C23": (6.60, 22.90, 0.0),      # VDD 10u
        "C24": (7.60, 29.00, 90.0),     # input coupling, beside VINL/VINR
        "C37": (-6.20, 23.30, 90.0),    # pickup coupling (C0G 1206), J8 -> U8
        "C38": (-4.60, 19.80, 0.0),     # direct-path coupling to the relay
        # THE DAC MOVES to the clear block south of the MCU, with room for the ten parts
        # PCM5102A's Figure 33 hangs on it. (At (15, 0) it sat across the panel
        # pass-through's corridor and THRU came back 13 mm skewed and split.)
        "U3": (16.00, -16.30, 0.0),
        "C26": (11.00, -12.40, 0.0),       # CPVDD 0.1
        "C32": (8.60, -14.30, 0.0),       # charge-pump flying 2.2u
        "C33": (8.60, -16.40, 0.0),       # VNEG 2.2u
        "C25": (7.40, -18.60, 0.0),      # AVDD 10u
        "C14": (10.60, -18.20, 0.0),      # AVDD 0.1
        "R13": (10.60, -19.40, 0.0),      # output filter 470R
        "C34": (10.60, -20.60, 0.0),      # output filter 2.2nF
        "R14": (8.60, -20.60, 0.0),      # -6 dB
        "C28": (21.00, -13.40, 0.0),      # DVDD 0.1
        "C30": (21.00, -14.70, 0.0),      # LDOO 0.1
        "C27": (13.60, -21.40, 0.0),     # CPVDD 10u
        "C29": (17.20, -21.40, 0.0),     # DVDD 10u
        "C31": (20.80, -21.40, 0.0),     # LDOO 10u
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
        # the output buffer's AC coupling and the VMID it biases to
        "C39": (-0.20, 9.80, 0.0),
        "R16": (0.60, 7.60, 0.0),
        "R17": (0.60, 6.20, 0.0),
        "R18": (0.60, 5.00, 0.0),
        "C40": (0.40, 3.00, 0.0),
        "R15": (-1.60, 11.60, 0.0),     # relay common to 0 V
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
        "C16": (-6.00, -17.60, 0.0),     # under Y1, off the I2S pins' southward escape (35-39)
        # ⚠ 2.5 mm EAST, TO OPEN ITS WEST CHANNEL. At -17.00 the hub's courtyard came
        # within 0.75 mm of J4's, and ALL SIX of its west-edge pins -- the upstream
        # differential pair, 3V3, GND and both oscillator pins -- had to escape through
        # that gap or travel around the package. HUB_XI was the one that lost, and it
        # survived a crystal relocation and two routing attempts before the cause was
        # looked at rather than the symptom.
        # U1 sits at 89.36, so there were 3.69 mm of slack here doing nothing. The
        # channel goes to 3.25 mm and the hub keeps 1.2 mm to the MCU.
        # 90 deg (2026-09-21): the real CH334F's DN1 pins (11/12) then face EAST at the MCU,
        # UP (14/15) faces north toward J3, and DN2 (9/10) leaves east and turns south round
        # to J4 -- three pairs that do not cross. At 0 deg DN1 faced away from U1 entirely.
        "U4": (-15.50, -8.00, 90.0),     # 1 W: the DN2 pair runs between it and U1, and U1.12 (VSSA) still needs its via
        "C12": (-17.00, -4.00, 0.0),
        "C35": (-14.60, -3.00, 0.0),    # hub V5 1u
        "C36": (-18.50, 0.00, 0.0),   # hub VDD33 10u
        "R19": (-14.60, -1.70, 0.0),    # hub OVCUR# pull-up -- off U1's west edge, where the crystal nets escape
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
        "R6": (1.50, -12.00, 0.0),
        "R7": (1.50, -13.30, 0.0),
        # -Y CORNER: THE 24 V ISLAND AND ITS SWITCHER, on their own copper
        # ⚠ SWAPPING J7 AND J9 DOES NOT FIX THE SEVERED BUS -- measured, still 2
        # unconnected. The reasoning looked strong: along this edge the inlet J6 is at
        # x 32, J7 carries the fleet's <5 A and sits at x 0, J9 carries the optical
        # board's 120 mA and sits at x 16 -- so the low-current tap sits squarely between
        # the inlet and the big load, and the 24 V bus has to get past a connector
        # footprint to reach the pads drawing forty times more current. Putting J7 at 16
        # and J9 at 0 gives the 5 A leg a clear run and leaves the squeeze to the leg
        # carrying 4 % of it.
        #
        # The board came back 2 unconnected either way, which says the break is NOT about
        # which tap is inboard. Both rails sever in the same pad row whichever order they
        # sit in, so what blocks the bus is the ROW ITSELF -- three connectors' worth of
        # through-hole pads and courtyards in one line at y -28, with no lane left between
        # them on any layer. Re-ordering pads inside a full row does not empty it.
        # (A 2.0 mm B.Cu lane under it was tried separately and went 2 -> 4.)
        "J7": (0.00, -28.00, 0.0),
        # SWD pads -- the tightest free cluster next to U1; see the note in output_panel()
        "TP1": (-6.10, -0.60, 0.0),       # the SWD row sits 1.5 N of U1: USB (61/62) enters from above
        "TP2": (1.90, -8.10, 0.0),       # 2 E: the five I2S pins (35-39) escape east through here
        "TP3": (-3.10, -0.60, 0.0),
        "TP4": (1.90, -5.10, 0.0),
        "TP5": (-9.10, -0.60, 0.0),
        # ⚠ 16.00, NOT 14.00, AND THE TWO MILLIMETRES ARE THE 24 V BUS. At 14.00 this
        # connector's courtyard ran 107.25..120.75 against J7's 93.25..106.75 -- a gap of
        # 0.50 mm, where a 0.25 mm track needs 0.65 to pass with clearance on both sides.
        # The detour was shut too: C5 sits just above the gap and the board edge is a
        # millimetre below. So nothing could get from the trunk-out to the inlet, and the
        # rail arrived in two pieces. See the note at the part itself.
        # There is 18.66 mm between J7 and J6 for a 13.5 mm connector. Centred in it, both
        # gaps come out near 2.5 mm, which carries +24V and PWR_GND side by side with
        # room to spare -- the comment this line used to carry, "on the same island", was
        # the intent and not the measurement.
        "J9": (16.00, -28.00, 0.0),   # the optical board's feed
        # ⚠ J10 IS ON THE +X EDGE, NOT THE -Y ROW, BECAUSE THAT ROW IS FULL. The -Y edge
        # already carries U5, C3, C2, D6, J7, J9 and the barrel jack J6, and measured off
        # the board's real courtyards the widest remaining gap there is 5.25 mm against a
        # 13.40 mm connector. My first two guesses (x 17, then x 28) were both estimates
        # and the second landed three of J10's pads inside J6's courtyard -- the fourth
        # time today a part was placed by eye and rejected by DRC.
        #
        # Sited by searching the whole board against every real courtyard, preferring a
        # board edge so the cable can leave: +X edge, hard against it.
        "J10": (29.70, -8.70, 0.0),
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
    "single_sided": True,
    "qty_per_instrument": 1,
}


if __name__ == "__main__":
    output_panel(tag="panel")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "output_panel.net"))
    # ⚠ THIS BOARD'S SPLIT IS DELIBERATE AND ITS CLOSURE IS NOT ON THIS BOARD, so it
    # is declared rather than fixed -- see the J6/J7 note above for why the 24 V return
    # is kept off the audio reference.
    #
    # ⚠ AND THE STAR POINT IT NAMES DOES NOT EXIST YET. Checked across every board's
    # netlist on 2026-09-17: this is the ONLY board in the instrument with a PWR_GND,
    # and the two boards the trunk feeds (motor_ctrl J3, optical J2) tie the trunk
    # return straight to their own signal ground. So "the two meet at the instrument's
    # star point, elsewhere" currently resolves to "the two meet at whichever board the
    # cable reaches first", which is not a star point and not a decision anybody made.
    # Left as a declared split, loudly, until that is settled -- it is a system-level
    # call about where the instrument's single ground reference lives, not something to
    # fix quietly inside one board.
    netcheck.grounds_meet(
        os.path.join(OUT_DIR, "output_panel.net"),
        declared_split={
            "shape": "GND | PWR_GND",
            "why": "the 24 V return is chopped by ten stepper drivers and is kept "
                   "off the audio reference. NOT a star point -- the two domains bond "
                   "ONCE PER LEAF at the downstream boards, and a tie on THIS board "
                   "would close a loop through a USB ground. See the J6/J7 note",
        })
    netcheck.no_orphan_pins(os.path.join(OUT_DIR, "output_panel.net"))
    with open(os.path.join(OUT_DIR, "output_panel.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements, x%d per instrument"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]),
             BOARD_NOTES["qty_per_instrument"]))
