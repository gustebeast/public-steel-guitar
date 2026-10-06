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

import harness                                      # noqa: E402
import netcheck                                     # noqa: E402

P = Pin.types.PASSIVE

USBC_FP = "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"
# ⚠ NMJ6HCD2, NOT NMJ4HCD2: the 4 is the TS part and the 6 is its TRS sibling.
# Same body, same bushing, same panel cut-out, same mounting -- the TRS simply adds the
# RING and RING_N lands, and its pad set is a strict SUPERSET of the TS one (checked pad
# by pad, 2026-09-30). So the mechanical work already done against the TS part -- the
# 3.0 mm panel clamp, TS_SHOULDER_DEPTH, the endplate counterbore, _FRONT["J5"] -- all
# still holds, and the change costs a footprint name.
TRS_FP = "Connector_Audio:Jack_6.35mm_Neutrik_NMJ6HCD2_Horizontal"
# Kycon KPJX-4S-S, the 4-pin snap-and-lock power jack (user, 2026-10-01). The supply is
# a Mean Well GST160A24-R7B desktop adapter, 6.67 A, and its lead ends in a Kycon KPPX-4P;
# the PJ-102AH barrel jack that stood here is rated 5 A and does not take that plug.
# 7.5 A per pin, two pins per rail. Footprint drawn from Kycon's own land pattern:
# elec/footprints/Steel.pretty.
DC_FP = "Steel:Kycon_KPJX-4S-S"
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


# ⚠ AND _d WAS THE ONE THAT NEVER GOT THE FIX. The note above says a ref that agrees
# with its tag "without ref= ... is a COINCIDENCE of CREATION ORDER" -- and _r and _c were
# both pinned while the diode helper was left as it was, so the fault the note describes
# was still live in this file. Adding D7 for the ring's phantom guard BEFORE D6 in the
# source proved it: the netlist came out with "D7" carrying +24V and PWR_GND, which are
# D6's nets, because skidl had numbered them by creation order and the placement dict --
# keyed by ref -- then put each part at the other one's coordinates. DRC found it as a
# solder-mask bridge between parts that should not have been near each other.
# Caught in one route. It would have been much harder to see in a year.
def _d(tag, value, desc, fp="Diode_SMD:D_SOD-523"):
    return Part(name="D", ref_prefix="D", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
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

    # ⚠ J2 AND J4 ARE USB-C NOW, NOT USB-A (user, 2026-10-02: "why do we need USB A, I
    # would expect C"). Nothing ever needed A: both are INTERNAL ports, chosen as A only so
    # the leads could be stock A-to-C. The GCT USB1046 they used had 3 in stock at JLCPCB
    # and no drop-in; the TYPE-C-31-M-12 is the part J1 and J3 already are, so the board
    # now carries ONE USB connector and the leads are stock C-to-C.
    # D+ and D- are tied across both rows, as on J1, so the lead works either way up.
    j2 = _usbc("J2", "to the Pi's USB-C gadget port, via a stock C-to-C lead")
    vbus_pi = Net("VBUS_PI_NC")
    vbus_pi += j2["A4"], j2["B4"], j2["A9"], j2["B9"]   # the lead's VBUS ends here, dead
    thru_dp += j2["A6"], j2["B6"]
    thru_dm += j2["A7"], j2["B7"]
    gnd += j2["A1"], j2["A12"], j2["B1"], j2["B12"], j2["SH"]
    # CC left open on purpose: this port neither sources nor sinks, it is a wire to J1,
    # and J1's own pull-downs are what the player's computer sees.

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

    j4 = _usbc("J4", "hub downstream -> the optical board, ~100 mm, stock C-to-C lead")
    # ⚠ THIS one DOES source VBUS -- it is a host port. The optical board runs off
    # its own 24 V and ignores the current, but a device that is not OFFERED VBUS
    # never enumerates, so the pin is fed rather than dead-ended.
    v5 += j4["A4"], j4["B4"], j4["A9"], j4["B9"]
    hub_dn2_dp += j4["A6"], j4["B6"]
    hub_dn2_dm += j4["A7"], j4["B7"]
    gnd += j4["A1"], j4["A12"], j4["B1"], j4["B12"], j4["SH"]
    # A USB-C HOST PORT SAYS SO WITH A PULL-UP ON EACH CC PIN: 56k to 5 V is the
    # "default USB power" advertisement. Over a C-to-C lead the optical board's own
    # 5k1 pull-downs see it and attach; the USB-A this replaces needed neither.
    for _tag, _pin in (("R29", "A5"), ("R30", "B5")):
        _rp = _r(_tag, "56k", "J4 CC pull-up: this port is a host (default USB power)")
        j4[_pin] += _rp[1]
        v5 += _rp[2]

    # ── J5: the 1/4 in jack. PCB-MOUNT, so no hand-soldered lug. ─────────────
    # BOM.md already specifies this Neutrik; it is a PCB part with a panel bushing,
    # and mounting it as a free-floating panel jack was what implied hand-soldered
    # lugs. Its nut clamps the endplate, so the PANEL takes the cable-yank load
    # rather than the PCB.
    # ⚠ THREE MODES OUT OF ONE JACK, AND THE PLUG PICKS BETWEEN TWO OF THEM MECHANICALLY.
    #   1. TS mono, "DIRECT"  -- a TS plug SHORTS RING TO SLEEVE. Nothing switches, nothing
    #      is told, and nothing has to detect the plug: the ring driver simply finds itself
    #      driving ground through its 220R series resistor, which is what that resistor is
    #      for. The tip carries the pickup through the relay's de-energised contact, so the
    #      instrument plays with no Pi, no firmware and no DAC.
    #   2. TRS stereo         -- tip = DAC left, ring = DAC RIGHT.
    #   3. TRS balanced mono  -- tip = +signal, ring = -signal.
    # ⚠⚠ THE JACK MODE AND THE SOURCE ARE INDEPENDENT AXES, AND AN EARLIER VERSION OF
    # THIS BLOCK CONFLATED THEM (corrected by the user, 2026-09-30). It read "balanced is a
    # processed mode", because it was cheaper: if balanced only ever happens when the Pi is
    # in the path, the Pi can emit -L on the right channel and the board needs no inverter.
    # That is true and it is the wrong shape. The two settings are:
    #
    #     jack     unbalanced mono | balanced mono | unbalanced stereo
    #     source   magnetic pickup (DIRECT) | optical pickup | MIDI
    #
    # and every combination is meant to work -- including BALANCED + DIRECT, which no amount
    # of Pi-side arithmetic can reach, because the direct path exists precisely so the Pi is
    # not in it. So the balancing lives HERE, in analog, and is source-agnostic by
    # construction. One code path instead of two, and the cold leg is correct even with the
    # firmware stopped.
    #
    # ⚠ THE SOURCE AXIS NEEDS NO NEW HARDWARE AT ALL, which is worth saying because it
    # looks like it should. "Optical pickup" and "MIDI" are both THE Pi VIA THE DAC -- they
    # differ in what the Pi computes, not in what arrives on this board -- so K1's existing
    # direct/processed throw already covers all three sources, and the Pi chooses between
    # the latter two internally.
    #
    # ⚠ AND STEREO + DIRECT COSTS NOTHING EITHER, BECAUSE K1 HAS A SPARE POLE. Pole B was
    # unused (it showed up in ERC as K1_NC_6 / K1_NC_7). Wiring its NC contact to the SAME
    # `direct` net as pole A, and its NO contact to the attenuated DAC right, makes pole B's
    # common mean "the right-hand signal, whatever the source": the pickup when direct, DAC
    # right when processed. Duplicating the mono pickup across both channels therefore falls
    # out of the relay that already selects the source, with no part and no second control.
    # The DAC's right channel already existed and was being thrown away -- it was literally
    # Net("DAC_OUT_R_NC").
    outp, ringp = Net("JACK_TIP"), Net("JACK_RING")
    j5 = Part(name="NMJ6HCD2", ref_prefix="J", ref="J5", tag="J5", dest="NETLIST", tool="skidl",
              value="NMJ6HCD2", description="1/4 in TRS output, PCB mount, panel bushing",
              footprint=TRS_FP,
              pins=[Pin(num="T", name="TIP", func=P), Pin(num="TN", name="TIP_N", func=P),
                    Pin(num="R", name="RING", func=P), Pin(num="RN", name="RING_N", func=P),
                    Pin(num="S", name="SLEEVE", func=P), Pin(num="SN", name="SLEEVE_N", func=P)])
    outp += j5["T"]
    ringp += j5["R"]
    # The switched contacts go to ground rather than floating: an open switch lug
    # beside an audio contact is an antenna, and nothing here needs to sense a plug.
    agnd += j5["S"], j5["TN"], j5["SN"], j5["RN"]

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
    # ⚠⚠ SUPERSEDED 2026-10-04 (user): THE TWO GROUNDS ARE JOINED HERE, ONCE, BY R60 (0 ohm)
    # AT THE BUCK'S OUTPUT CAPACITOR. The notes below are kept because their reasoning about
    # LAYOUT still holds (the 24 V pair keeps its own island and no pour floods across it),
    # but their conclusion -- never tie on this board -- did not survive the quality review:
    #   * U5 is a buck, and a buck's input return and output return are one node. Its
    #     output feeds +5V and every load on this board, and those loads return to GND. With
    #     no tie the board's own supply current (up to 257 mA) had no way home on the board:
    #     it went out through a USB cable's ground to whichever board bonds the two, and
    #     with only the inlet plugged in the board was dead.
    #   * "Loop-free" was true with ONE downstream bond. There are two -- the optical board
    #     (its 24 V lead and its USB) and the Pi (USB here, trunk return at motor_ctrl) --
    #     so the loop the notes warn about already existed, through two USB grounds.
    # R60 makes this board the star point the first draft said existed "elsewhere". What
    # it costs: the USB grounds now parallel the trunk return, so a share of the stepper
    # return current (roughly the ratio of a trunk conductor to a USB ground wire, about a
    # tenth) crosses this board's GND between the USB sockets and R60. Both are on the
    # board's -X edge, and the audio section is at the other end. R60 is an 0603 so it can
    # become a bead, or come off to restore the old arrangement, without a re-spin.
    # ⚠ (the older note) PWR_GND IS A SEPARATE NET AND IS NEVER JOINED TO THE SIGNAL GROUND HERE. The
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
    # ⚠ THE RAILS ARE A COLUMN EACH: +V ON PINS 2 AND 4, -V ON PINS 1 AND 3 (Kycon's
    # numbers). Three drawings, read 2026-10-06, because the two makers number the same
    # four contacts differently:
    #   * Kycon KPJX-4S-S (the jack), looking INTO the mouth with the key up: 1 top left,
    #     2 top right, 3 bottom left, 4 bottom right. Its land pattern has 3 and 4 in the
    #     row 11.00 behind the nose, 1 and 2 in the row at 14.65, 1 behind 3 and 2 behind 4.
    #     Our footprint is that pattern, pad for pad.
    #   * Kycon KPPX-4P (the plug), looking at its pins with the key at nine o'clock:
    #     1 top left, 3 top right, 2 bottom left, 4 bottom right -- the jack's face seen
    #     from the other side, so plug pin n meets jack pin n.
    #   * Mean Well GST160A-SPEC (2026-04-03), plug R7B, drawn the same way up: 2 top left,
    #     3 top right, 1 bottom left, 4 bottom right, and its table reads 1 +Vo, 2 -Vo,
    #     3 -Vo, 4 +Vo. MEAN WELL'S 1 AND 2 ARE KYCON'S 2 AND 1; 3 and 4 agree.
    #   physical position (into the jack, key up) -> pad -> net:
    #     top left     -> pad 1 -> PWR_GND          top right    -> pad 2 -> +24V_IN
    #     bottom left  -> pad 3 -> PWR_GND          bottom right -> pad 4 -> +24V_IN
    # The fab's library footprint numbers these pads another way again; it is placed by
    # position, so its numbers do not matter. METER THE PLUG BEFORE FIRST POWER
    # (docs/board-bringup-diagnostics.md): this is read off drawings, not off the part.
    # The shell goes to PWR_GND: the same spec ties -V to the AC inlet's earth pin, so the
    # shell is at that potential whatever this board does with it.
    j6 = Part(name="KPJX-4S-S", ref_prefix="J", ref="J6", tag="J6", dest="NETLIST", tool="skidl",
              value="KPJX-4S-S", description="24 V inlet, 4-pin snap-and-lock power jack",
              footprint=DC_FP,
              pins=[Pin(num=1, name="G1", func=P), Pin(num=2, name="V2", func=P),
                    Pin(num=3, name="G3", func=P), Pin(num=4, name="V4", func=P),
                    Pin(num="SH", name="SHELL", func=P)])
    # ⚠ THE INLET IS ITS OWN NET NOW: +24V_IN, AHEAD OF THE POWER SWITCH (2026-10-04). Nothing
    # but the switch Q2 and its sense divider is on it -- every load, the Pi's supply
    # included, is on +24V behind Q2. See "THE POWER BUTTON" below J10.
    v24_in = Net("+24V_IN")
    v24_in.drive = Pin.drives.POWER
    v24_in += j6[2], j6[4]
    pgnd += j6[1], j6[3], j6["SH"]
    # Trunk out on the instrument's standard 4-way: GND, 24 V, and NOTHING on ways 3 and 4.
    # ⚠ IT CARRIED BOTH RAILS TWICE (GND, 24, 24, GND) UNTIL 2026-10-04, and that put 24 V
    # and ground on the two ways where every other 4-way XH in the instrument has its
    # data. Any 4-way XH lead seats here: a motor drop would have had 24 V on CAN_H (a
    # transceiver rated -4 to +16 V) and the lights lead 24 V on a switch line whose
    # switch is a 12 V part. The user's rule (harness.py) is GND, power, data, data --
    # so on a lead with no data, ways 3 and 4 are empty and a wrong plug finds nothing
    # on them.
    # What the doubling was for, and why it was not buying it: this lead's far end is the
    # east tee's trunk header, which takes the rail on ONE contact (ways 1-4 of the 8 are
    # GND, 24, CAN_H, CAN_L). The pair was always limited by that contact; this end now
    # matches it. 2.9 A with ten motors moving, on a 3 A contact at each end.
    j7 = Part(name="B4B-XH-A", ref_prefix="J", ref="J7", tag="J7", dest="NETLIST", tool="skidl",
              value="B4B-XH-A", description="24 V trunk out: GND, 24 V, two empty ways",
              footprint=XH_FP,
              pins=[Pin(num=i + 1, name=n, func=P)
                    for i, n in enumerate(("PWR_GND", "+24V", "NC3", "NC4"))])
    pgnd += j7[1]
    v24 += j7[2]

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
    # ⚠ SIX WAYS SINCE 2026-10-04, AND THE SIXTH FINDING ABOVE IS GONE WITH IT. Ways 5 and 6
    # are the power button's two throws (user: "let's avoid a new cable between the output
    # and motor and just put the power switch signal on the same cable carrying power from
    # the output board to the motor board"). A 6-way plug cannot enter a 4-way header, so
    # this link no longer needs a dyed housing to tell it from a CAN drop.
    # The ways are the instrument's one order (harness.py): GND, 24 V, the two switch
    # lines where a 4-way has its data, then 24 V and GND again on ways 5 and 6 -- so the
    # row reads the same from either end and each rail still has two contacts.
    j10 = Part(name="B6B-XH-A", ref_prefix="J", ref="J10", dest="NETLIST", tool="skidl",
               value="B6B-XH-A",
               description="24 V trunk out #2 + the power button's throws in -- to "
                           "motor_ctrl J3 (2 contacts per rail)",
               footprint="Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical",
               pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(
                   # harness.PWR_LINK: the same list motor_ctrl J3 is built from
                   tuple({"GND": "PWR_GND", "V24": "+24V"}.get(w, w)
                         for w in harness.PWR_LINK))])
    pgnd += j10[1], j10[6]
    v24 += j10[2], j10[5]

    # ── THE POWER BUTTON (user, 2026-10-04) ──────────────────────────────────────────────
    # The button is SW2 on the UI board: a latching 2P2T rated 12 V / 0.3 A, so it cannot
    # break the supply itself. Its two throws arrive here on J10 ways 3 and 4 (UI ribbon ->
    # pi_cap -> lights cable -> motor_ctrl -> this cable), and what breaks the supply is Q2,
    # a P-channel MOSFET in the +24 V line between the inlet jack and everything else.
    #
    # WHICH WAY IT FAILS: ON. A throw is shorted to ground to say OFF and is open
    # otherwise, so a missing ribbon, an unplugged cable or a broken wire all read as "not
    # off" and the instrument runs. Nothing in the signal path is powered from behind the
    # switch, so there is no state in which it cannot turn itself back on.
    #
    #   +24V_IN --R33--R34--+-- SW_SENSE --JP1-- PWR_SW_UP (or _DN) --> button --> GND
    #                       |
    #                      D8 (10 V zener to PWR_GND)
    #                       +--R35--+-- Q3 gate     Q3 on  -> Q2 gate pulled low -> ON
    #                              C50              Q3 off -> R32 returns it     -> OFF
    #
    # THE BUTTON SEES 10 V AND 2.6 mA, against its 12 V / 0.3 A. Open, the line sits on D8's
    # 10 V (9.4-10.6); closed, 24 V across R33 + R34 = 9.4k is 2.55 mA. Two 4k7 because one
    # would carry 61 mW on an 0402 rated 62.5; each carries 31. That 2.55 mA is also the
    # INSTRUMENT'S WHOLE OFF-STATE DRAW from the supply: Q2 off, Q3 off, D8 not conducting.
    # (On, the same string carries 1.5 mA into D8 and R31 + R32 carry 0.05 mA.)
    # R35 / C50 (10k, 100 nF: 1 ms) keep cable-borne spikes off Q3's gate; D8 is the clamp
    # for anything that arrives on 600 mm of unshielded wire.
    #
    # JP1 PICKS THE THROW (lead's request). Read off the maker's drawing, not metered: UP
    # is closed to ground with the button OUT, DN with it latched IN -- so UP is the one
    # that says "off" when the button is out, and JP1 is made bridged 1-2 (UP). If a real
    # switch turns out the other way round the instrument works with the button's sense
    # inverted; cut 1-2 and bridge 2-3.
    #
    # Q2 = SQD50P06-15L (Vishay 69098 rev. E p.1): -60 V, 15.5 mOhm at -10 V, 20 mOhm at
    # -4.5 V, +-20 V gate, TO-252 with G left / D tab / S right seen from above, leads down
    # -- pad 1 G, 2 D, 3 S on KiCad's TO-252-2. The supply is 6.67 A: 0.9 W at 20 mOhm, on a
    # part good for 50 C/W on a square inch of copper; the realistic bus is under 5 A, 0.5 W.
    # 60 V because D6 clamps the trunk at 48 V and a 40 V part would sit under that.
    #
    # THE GATE IS A SOFT START, AND IT HAS TO BE. Behind Q2 sit ten motor drivers' bulk
    # capacitors. Closed hard onto a supply that is already up, the only thing limiting
    # the charge current would be the cable.
    #   R31 330k (gate to Q3) / R32 150k (gate to source): 7.5 V of gate drive at 24 V,
    #       5.6 V at an 18 V brown-in -- the part is specified at 4.5.
    #   C49 22 nF gate-to-DRAIN: with ~34 uA left for it at the plateau the output rises
    #       about 1.5 V/ms, 16 ms to 24 V, so 3000 uF of bulk draws ~4.5 A while it fills.
    #   C48 1 uF gate-to-SOURCE: when the supply is PLUGGED IN with the button on, C49 holds
    #       the gate at the (empty) output while the source jumps to 24 V. C48 divides
    #       that step: 24 V x 22n / (22n + ~0.6u at bias) = 0.85 V, under the 1.5 V
    #       minimum threshold, so the gate starts from off and ramps like any other start.
    #   Off: R32 alone discharges it, ~23 ms through the plateau.
    # No gate zener: the divider cannot exceed 9.4 V at a 30 V input against +-20.
    q2 = Part(name="Q_PMOS", ref_prefix="Q", ref="Q2", tag="Q2", dest="NETLIST", tool="skidl",
              value="SQD50P06-15L", description="24 V power switch, P-channel 60 V "
              "15.5 mOhm (LCSC C3281500). Chosen for Rds(on) at -4.5 V and 60 V: do not "
              "substitute a 40 V part. The tab is the switched +24V, electrically live",
              footprint="Package_TO_SOT_SMD:TO-252-2",
              pins=[Pin(num=1, name="G", func=P), Pin(num=2, name="D", func=P),
                    Pin(num=3, name="S", func=P)])
    pwr_gate = Net("PWR_GATE")
    v24_in += q2["S"]
    v24 += q2["D"]
    pwr_gate += q2["G"]
    # 2N7002 SOT-23: 1 G  2 S  3 D (CJ 2N7002 datasheet p.1 marking diagram, LCSC C8545)
    q3 = Part(name="Q_NMOS", ref_prefix="Q", ref="Q3", tag="Q3", dest="NETLIST", tool="skidl",
              value="2N7002", description="power-switch gate driver (LCSC C8545)",
              footprint="Package_TO_SOT_SMD:SOT-23",
              pins=[Pin(num=1, name="G", func=P), Pin(num=2, name="S", func=P),
                    Pin(num=3, name="D", func=P)])
    pwr_pull, sw_sense, sw_gate = Net("PWR_PULL"), Net("SW_SENSE"), Net("SW_GATE")
    sw_mid = Net("SW_PU_MID")
    sw_up, sw_dn = Net("PWR_SW_UP"), Net("PWR_SW_DN")
    sw_up += j10[3]
    sw_dn += j10[4]
    pgnd += q3["S"]
    pwr_pull += q3["D"]
    sw_gate += q3["G"]
    for _t, _v, _a, _b, _what in (
            ("R31", "330k", pwr_gate, pwr_pull, "Q2 gate pull-down through Q3 -- sets the "
                                                "soft-start current with C49"),
            ("R32", "150k", v24_in, pwr_gate, "Q2 gate to source: OFF when Q3 is off"),
            ("R33", "4k7", v24_in, sw_mid, "button pull-up, top half (31 mW)"),
            ("R34", "4k7", sw_mid, sw_sense, "button pull-up, bottom half (31 mW)"),
            ("R35", "10k", sw_sense, sw_gate, "Q3 gate filter, 1 ms with C50")):
        _rr = _r(_t, _v, _what)
        _a += _rr[1]
        _b += _rr[2]
    for _t, _v, _a, _b, _what in (
            ("C48", "1uF/25V", v24_in, pwr_gate, "Q2 gate-source: holds the gate off through "
                                                 "a live plug-in (see the note)"),
            ("C49", "22nF/50V", pwr_gate, v24, "Q2 gate-drain: the soft-start slope, "
                                               "~1.5 V/ms"),
            ("C50", "100nF", sw_gate, pgnd, "Q3 gate filter")):
        _cc = _c(_t, _v, _what)
        _a += _cc[1]
        _b += _cc[2]
    # KiCad diode footprints: pad 1 = K. BZT52C10T-7 (Diodes Inc): cathode band = K.
    d8 = _d("D8", "BZT52C10T-7", "10 V zener: the button never sees more than this, and "
            "the clamp for the switch cable (LCSC C248313)")
    sw_sense += d8[1]
    pgnd += d8[2]
    jp1 = Part(name="SolderJumper_3_Bridged12", ref_prefix="JP", ref="JP1", tag="JP1",
               dest="NETLIST", tool="skidl", value="THROW",
               description="which throw of the power button means OFF: bridged 1-2 = UP "
                           "(as made), cut and bridge 2-3 = DN",
               footprint="Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm",
               pins=[Pin(num=1, func=P), Pin(num=2, func=P), Pin(num=3, func=P)])
    sw_up += jp1[1]
    sw_sense += jp1[2]
    sw_dn += jp1[3]


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
    # ⚠ FUSED (2026-10-04). This outlet is ONE XH contact and a thin lead to a board that
    # has no fuse of its own, fed from a supply that will hold 6.67 A into a fault there:
    # 160 W into whatever failed. 1 A against a 0.12 A load -- the SKU motor_ctrl's F1 is.
    v24_opt = Net("+24V_OPT")
    f1 = Part(name="Fuse", ref_prefix="F", ref="F1", tag="F1", dest="NETLIST", tool="skidl",
              value="JFC1206-1100FS", description="1 A 63 V chip fuse: the optical board's "
              "24 V feed (LCSC C136343)",
              footprint="Fuse:Fuse_1206_3216Metric",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v24 += f1[1]
    v24_opt += f1[2], j9[2]

    # ── U1: the MCU. USB HS to the hub, two I2S units on one clock pair, one GPIO for the relay ──
    # Pin numbers off WCH's QFN-68 column (CH32V303/305/307/317 V3.9, table 3-1):
    #   61 PB6  = USBHS_DM      62 PB7  = USBHS_DP
    #   35 PB12 = I2S2 WS       36 PB13 = I2S2 CK       38 PB15 = I2S2 SD  (to DAC)
    #   53 PA15 = I2S3 WS       58 PB3  = I2S3 CK       60 PB5  = I2S3 SD  (FROM the ADC)
    # ⚠ THIS MCU HAS NO FULL-DUPLEX I2S (found 2026-10-04). The ADC's data used to land on
    # pin 37, PB14, written down here as "I2S2ext SD". There is no such function: WCH's
    # table gives PB14 SPI2_MISO, USART3_RTS and TIM1_CH2N, and section 2.5.18 says "2 sets
    # of standard I2S interfaces" -- each one-way, as on the F1 parts this peripheral is
    # modelled on. Wired that way the board would have played and never recorded.
    # So the two units each take one direction off the SAME wires: I2S2 is the master
    # transmitter (it makes MCK, CK and WS, and sends to the DAC), I2S3 is a slave receiver
    # whose WS and CK pins are tied on the board to I2S2's. One clock pair still serves
    # both converters, so they stay sample-aligned with no resampler between them.
    # Note 10 of the same table: I2S3_SD is PB5 unless 10M Ethernet is enabled, which
    # this board never does. PB14 is left unconnected.
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
                 61, 62, 35, 36, 38, 25, 48, 52, 63, 39, 1,
                 53, 58, 60,                            # I2S3: WS, CK, SD
                 64, 65, 26, 27)]   # PB8, PB9, PB0 pot SPI; PB1 the jack mode
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
    i2s_ws += u1[35], u1[53]      # I2S2 WS out, and I2S3 WS in
    i2s_ck += u1[36], u1[58]      # I2S2 CK out, and I2S3 CK in
    i2s_sdi += u1[60]
    i2s_sdo += u1[38]
    relay += u1[25]
    # ⚠ BIT-BANGED, AND DELIBERATELY. SPI1 (PA5/6/7) and SPI2 (PB13/14/15) are both
    # spoken for -- SPI2 IS the I2S2 that carries the audio -- and PB8/PB9/PB0 were the
    # three pins cross-checked as genuinely free against WCH's QFN-68 column. A digital
    # pot is written when the VOLUME CHANGES, not per sample: 16 bits at even 100 kHz is
    # 160 us, four hundred times inside the 50 ms budget below. Spending a hardware SPI
    # peripheral on it would buy nothing and cost a pin map that is already full.
    pot_cs, pot_sck, pot_sdi = Net("POT_CS"), Net("POT_SCK"), Net("POT_SDI")
    jack_mode = Net("JACK_MODE")   # 0 = balanced (inverted tip), 1 = stereo
    pot_cs += u1[64]
    pot_sck += u1[65]
    pot_sdi += u1[26]
    # ✅ ALL FOUR READ OFF THE TABLE, NOT INFERRED: 26 PB0, 27 PB1, 64 PB8, 65 PB9,
    # checked against .ins/ch32v307_qfn68.json -- the same QFN-68 column the other
    # twenty-four pins on this part were taken from. 27 was briefly written down as an
    # inference from "26 is PB0 and they are adjacent", which is reasoning about a table
    # rather than reading one; the note above is explicit that nothing downstream can
    # catch a wrong pin number, so it was read.
    jack_mode += u1[27]
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

    # (PCM1808 and PCM5102A re-read 2026-09-30, all 14 and all 20 pins: they match.)
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
    # ⚠ THIS USED TO BE Net("DAC_OUT_R_NC") -- the right channel existed and was
    # discarded, because the Pi summed to mono for a TS jack. With a TRS jack the ring
    # IS that channel, so the whole of modes 2 and 3 is already sitting on this pin.
    proc_r = Net("DAC_OUT_R")
    proc_r += u3["OUTR"]

    # ── U4: the hub. HIGH SPEED -- a FS hub would reintroduce the TT ─────────
    # WCH CH334F, QFN-24 4x4 (LCSC C5187527). Pins off WCH's datasheet V2.5 Table 1-3, the
    # "4F" column (the pin-arrangement FIGURE's package labels are offset by one block --
    # read the table): 1 OVCUR# 2 NC 3 XO 4 XI 5 DM4 6 DP4 7 DM3 8 DP3 9 DM2 10 DP2
    # 11 DM1 12 DP1 13 LED3/SCL 14 DMU 15 DPU 16 RESET# 17 NC 18 NC 19 V5 20 VDD33
    # 21 LED4/SDA 22 LED1/PSELF 23 LED2/PGANG 24 PWREN#, EP = GND.
    # Re-read 2026-09-30 against V2.91 (LCSC's copy for C5187527): every pin this board USES
    # is unchanged. One label moved: V2.91 lists pin 18 as PSELF, not NC (17 and 2 stay NC).
    # It has its own pull-up and open = self-powered, which is what this board is, so
    # leaving it on its own net is still right -- but do NOT ground it as a "spare NC".
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
    # The ring side's nets, declared together and BEFORE anything reaches for them.
    # They are used across three blocks that do not appear in signal order -- K1 wires
    # pole B, U12 selects, U10 attenuates -- and a net created where it is first
    # mentioned makes that order load-bearing for no reason.
    ring_in = Net("RING_BUF_IN")
    ring_buf = Net("RING_BUF_OUT")
    ring_blocked = Net("RING_BLOCKED")
    ring_gain = Net("RING_GAIN")
    ring_att = Net("RING_ATT")
    dac_r_filt = Net("DAC_R_FILT")
    u7_in, pk_in, vmid = Net("OUT_BUF_IN"), Net("PICKUP_IN"), Net("VMID")
    # TLV9061IDBVR x4 (U7, U8, U9, U11). Pins off TI SBOS839N Table 5-1, SOT-23 column,
    # read 2026-09-30: 1 OUT  2 V-  3 IN+  4 IN-  5 V+. (The SC70 and X2SON columns differ.)
    u7 = Part(name="OPAMP", ref_prefix="U", ref="U7", tag="U7", dest="NETLIST", tool="skidl",
              value="TLV9061IDBVR", description="output buffer -- drives the TS jack",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                    Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                    Pin(num=5, name="V+", func=P)])
    buf += u7[1], u7[4]       # unity-gain follower
    agnd += u7[2]
    tip_gain = Net("TIP_GAIN")
    tip_gain += u7[3]         # the pot's P0 wiper -- see U10
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

    # ── U9: the RING buffer. Third instance of a part already on this board. ─────
    # TLV9061 again rather than a dual: U7 and U8 are already this SKU, so the ring leg
    # adds a line to the reel count and not a new part to buy, place and stock. A dual
    # would have saved one package and cost a SKU, and on a board that already carries
    # two singles that is the wrong way round.
    # ⚠ AND IT MUST BE THE SAME PART FOR AN ELECTRICAL REASON TOO, not just a purchasing
    # one. In balanced mode the tip and ring are a differential pair, and the receiver
    # rejects common-mode noise only as well as the two legs MATCH. Identical amplifier,
    # identical topology, identical 220R series and identical 2.2 uF block is what makes
    # the two legs the same impedance; a different op-amp on the cold leg would be a
    # CMRR fault that measures fine on a bench and hums in a room.
    u9 = Part(name="OPAMP", ref_prefix="U", ref="U9", tag="U9", dest="NETLIST",
              tool="skidl", value="TLV9061IDBVR",
              description="ring buffer -- the TRS cold leg, matched to U7",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                    Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                    Pin(num=5, name="V+", func=P)])
    ring_buf += u9[1], u9[4]      # unity-gain follower, exactly as U7
    agnd += u9[2]
    u9_in = Net("RING_BUF_SEL")
    u9_in += u9[3]            # U12 picks what this is: the inverted tip, or the right channel
    v5 += u9[5]

    # ── U11: THE INVERTER. This is what "balanced" actually costs. ─────────────
    # A fourth TLV9061 -- the same SKU as U7, U8 and U9, so the balancing capability adds a
    # line to the reel count and no new part to buy or stock.
    # ⚠ ITS INPUT IS U7's OUTPUT, NOT THE POT WIPER, AND THAT IS THE WHOLE POINT. The two
    # legs of a balanced pair have to carry the same magnitude at EVERY volume setting. A
    # pot wiper's source impedance varies with position -- up to a quarter of the track,
    # 2.5k on a 10k part -- and that impedance sits in series with R26, so an inverter fed
    # from the wiper would have a gain that CHANGES AS THE VOLUME MOVES. Taking `buf`
    # instead puts an op-amp output (milliohms) in front of R26, so the gain is R27/R26 and
    # nothing else, and the cold leg tracks the hot one exactly.
    # ⚠ AND R26/R27 ARE 0.1%, NOT 1%. The receiver's common-mode rejection is set by how
    # well the two legs match: a 1% pair allows 2% of gain error, which is about 34 dB of
    # CMRR, and 0.1% buys roughly 54 dB. That is the difference between a balanced output
    # that measures balanced and one that merely has three contacts. The parts cost cents.
    inv_n, inv_out = Net("INV_IN_N"), Net("INV_OUT")
    u11 = Part(name="OPAMP", ref_prefix="U", ref="U11", tag="U11", dest="NETLIST",
               tool="skidl", value="TLV9061IDBVR",
               description="unity INVERTER -- makes the balanced cold leg in analog, so "
               "balanced works with the DIRECT source too",
               footprint="Package_TO_SOT_SMD:SOT-23-5",
               pins=[Pin(num=1, name="OUT", func=P), Pin(num=2, name="V-", func=P),
                     Pin(num=3, name="IN+", func=P), Pin(num=4, name="IN-", func=P),
                     Pin(num=5, name="V+", func=P)])
    inv_out += u11[1]
    agnd += u11[2]
    vmid += u11[3]            # it inverts ABOUT VMID, which is this board's signal zero
    inv_n += u11[4]
    v5 += u11[5]

    # ── U12: which of the two the ring carries. ONE BIT, and mode 1 needs none. ────
    # ⚠ UNBALANCED MONO IS NOT A SETTING HERE. A TS plug shorts ring to sleeve, so mode 1
    # is selected by the CABLE and this switch can be in either position. That is why three
    # jack modes need one control line and not two.
    # ⚠ THE SWITCH IS ON THE BUFFER'S INPUT, NOT ITS OUTPUT, and that is deliberate: an
    # analog switch's on-resistance varies with signal voltage, so passing CURRENT through
    # one is what turns it into distortion. U9's input draws picoamps, so Ron modulation has
    # nothing to act on.
    # ⚠ TS5A3159, NOT THE SN74LVC1G3157 THAT STOOD HERE (2026-10-04, the level review).
    # The switch runs on 5 V because the audio swings 0..5 V through it, and its control
    # pin is driven by a 3.3 V MCU output. The LVC part's control threshold is 0.7 x VCC
    # (SCES424 p.6): 3.48 V at this rail, ABOVE anything a 3.3 V pin can reach -- it would
    # have worked on most parts on most days. The TS5A3159 is the same SC-70-6 with the
    # same pin for pin function (TI SCDS174 p.3: 1 NO, 2 GND, 3 NC, 4 COM, 5 V+, 6 IN;
    # IN high joins COM to NO) and reads 2.4 V as high at 4.5-5.5 V (p.4). 1 ohm instead
    # of 6, same rail-to-rail signal range. Pin NAMES below are still the LVC part's:
    # B2 = NO, B1 = NC, A = COM, S = IN.
    u12 = Part(name="TS5A3159", ref_prefix="U", ref="U12", tag="U12", dest="NETLIST",
               tool="skidl", value="TS5A3159DCKR",
               description="SPDT analog switch, 2.4 V logic at a 5 V supply (LCSC C46388) "
               "-- ring = inverted tip (balanced) or the right-hand channel (stereo)",
               footprint="Package_TO_SOT_SMD:SOT-363_SC-70-6",
               # ⚠ READ OFF TI'S OWN TABLE 4-1 (SCES424O, rev June 2025), NOT REMEMBERED.
               # It was remembered first, as 1 B1 / 3 A / 4 B2, and ALL THREE SIGNAL PINS
               # WERE WRONG: the real order is 1 B2, 2 GND, 3 B1, 4 A, 5 VCC, 6 S. A route
               # was already running against the wrong netlist when the datasheet arrived.
               # This is the second time in one sitting that this file's rule -- "it is
               # checked here or it is not checked at all" -- has earned its keep, and the
               # first was the MCU pin four lines of comment away.
               pins=[Pin(num=1, name="B2", func=P), Pin(num=2, name="GND", func=P),
                     Pin(num=3, name="B1", func=P), Pin(num=4, name="A", func=P),
                     Pin(num=5, name="VCC", func=P), Pin(num=6, name="S", func=P)])
    # B1 conducts with S LOW and B2 with S HIGH (Table 4-1), which fixes the polarity of
    # JACK_MODE rather than leaving it to firmware to discover: 0 = balanced, 1 = stereo.
    inv_out += u12[3]         # B1, S low  -- balanced: the inverted tip
    agnd += u12[2]
    ring_gain += u12[1]       # B2, S high -- stereo: pole B's signal, after P1
    u9_in += u12[4]           # A: the common, into U9
    v5 += u12[5]
    jack_mode += u12[6]
    # ✅ AND THE PART IS RIGHT FOR THE JOB, from the same datasheet: "Audio signal
    # routing" is a listed application, Ron is ~6 ohm, and it is rail-to-rail on signals up
    # to VCC -- which matters because this board's audio is VMID-centred and swings most of
    # 0..5 V, so a switch that only passed a logic-level window would clip the loud half.

    # ── U10: THE GAIN, AND IT IS AN ATTENUATOR IN FRONT OF THE BUFFERS ─────────
    # MCP4261-103E/ST: dual 10k digital pot, SPI, TSSOP-14. Pinout off Microchip's
    # DS22059 Table 3-1 (14-lead), read 2026-09-30:
    #   1 CS   2 SCK  3 SDI  4 VSS  5 P1B  6 P1W  7 P1A
    #   8 P0A  9 P0W 10 P0B 11 WP  12 SHDN 13 SDO 14 VDD
    # ✅ CONFIRMED, AND FROM A SECOND SOURCE RATHER THAN A SECOND LOOK. It was briefly
    # marked unconfirmed here, and rightly: U12's pinout was also "read from the datasheet"
    # and all three of its signal pins were wrong, so one reading is not evidence on this
    # board. DS22059B could not settle it -- its pin table renders as an image and the
    # package drawing's text extracts with the column order scrambled, so it cannot even
    # say whether pin 2 is SCK or SDI, which was the only part in doubt.
    # What settled it was KiCad's OWN symbol for the same 14-lead MCP42X1 dual pot,
    # Potentiometer_Digital:MCP4251-xxxx-ST, which reads pin for pin:
    #   1 CS  2 SCK  3 SDI  4 VSS  5 P1B  6 P1W  7 P1A
    #   8 P0A 9 P0W 10 P0B 11 WP  12 SHDN 13 SDO 14 VDD
    # -- identical, including 2 and 3, and including WP/SHDN on 11/12, which is what makes
    # it the same MCP42X1 outline and not a neighbouring part's. An independent
    # transcription agreeing is worth more than reading the same page twice.
    # ⚠ WHY A POT AND NOT A GAIN THE Pi APPLIES IN SOFTWARE: BECAUSE OF MODE 1.
    # The user asked for gain control in the DIRECT mode -- the one whose whole point is
    # that the pickup reaches the jack without the Pi in the path. A software gain is by
    # definition unavailable there. This is an ANALOG attenuator, so it works in every
    # mode including the one with no firmware running, and it adds ZERO samples of
    # latency because there is no sample: it is a resistor divider that a wiper moves.
    # ⚠ AND IT SITS BEFORE THE BUFFER, WHICH IS THE WHOLE TRICK. Signal -> wiper ->
    # buffer -> jack. Put the pot AFTER the buffer and the jack sees 10k of source
    # impedance that varies with the setting; in front of a unity follower the jack
    # always sees the op-amp. The low end of each track goes to VMID rather than ground
    # because VMID IS the AC ground here (C40 is 10 uF across it) -- and because both
    # ends of the track then sit at the same DC as the wiper, so moving the wiper moves
    # no charge and the volume change does not click.
    # ⚠ 3.3 V LOGIC INTO A 5 V PART, CHECKED RATHER THAN ASSUMED: VIH is 0.45*VDD =
    # 2.25 V at VDD = 5 V, and the MCU drives 3.3 V. It runs off V5 and not V3V3 because
    # the AUDIO has to fit between its rails -- the signal is VMID-centred and swings the
    # full 0..5 V, which a 3.3 V-powered pot would clip against its own substrate diodes.
    u10 = Part(name="MCP4261-103E_ST", ref_prefix="U", ref="U10", tag="U10",
               dest="NETLIST", tool="skidl", value="MCP4261-103E/ST",
               description="dual 10k SPI digital pot -- the OUTPUT GAIN, analog so it "
               "works in the direct mode too (LCSC C185580)",
               footprint="Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
               pins=[Pin(num=n, func=P) for n in range(1, 15)])
    pot_cs += u10[1]
    pot_sck += u10[2]
    pot_sdi += u10[3]
    agnd += u10[4]
    v5 += u10[14]
    # WP and SHDN are tied INACTIVE rather than left to float: SHDN floating would let
    # noise mute the instrument, which is the one failure nobody would debug quickly.
    v5 += u10[11], u10[12]
    Net("POT_SDO_NC").connect(u10[13])   # daisy-chain out, nothing downstream
    # P0 = the TIP path, which is BOTH modes' hot leg and therefore the direct path too
    u7_in += u10[8]           # P0A: the relay common, AC-coupled and VMID-biased
    tip_gain += u10[9]        # P0W -> U7
    vmid += u10[10]           # P0B: AC ground
    # P1 = the RING path. Same 10k, same code written to both, so the two legs track
    # and a balanced pair stays balanced at every volume setting.
    ring_in += u10[7]         # P1A: pole B, attenuated, AC-coupled, VMID-biased
    ring_gain += u10[6]       # P1W -> U9
    vmid += u10[5]            # P1B

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
    ring_sel = Net("RING_SEL")   # pole B common: the right-hand signal, whichever source
    k1 = Part(name="G6K-2F-Y", ref_prefix="K", tag="K1", dest="NETLIST", tool="skidl",
              value="G6K-2F-Y-DC5", description="true-bypass select; DE-ENERGISED = DIRECT "
              "(LCSC C326376)", footprint=RELAY_FP, pins=[Pin(num=i, func=P) for i in range(1, 9)])
    v5 += k1[1]
    coil += k1[8]
    sel += k1[3]
    direct += k1[2]
    dac_att += k1[4]
    # ── POLE B: the right-hand signal, and it costs NOTHING because the pole existed ──
    # Pole A answers "what does the TIP carry"; pole B answers the same question for the
    # RING, off the same coil and therefore always in agreement with it. NC is direct and
    # NO is processed on both poles, so:
    #     direct   -> pole B carries the PICKUP, the same signal as the tip. That IS
    #                 "stereo + direct duplicates the mono pickup across both channels",
    #                 and it needs no control of its own.
    #     processed-> pole B carries the DAC's RIGHT channel, which the Pi is free to make
    #                 genuinely different from the left.
    # ⚠ BOTH NC CONTACTS SHARE ONE NET AND ONE COUPLING CAP. k1[7] joins `direct`, which
    # C38 already feeds from the pickup buffer -- the two poles want the identical signal,
    # so a second cap would only add a second high-pass corner to mismatch against the
    # first. U8 buffers the coil precisely so it can be tapped more than once.
    direct += k1[7]
    ring_att += k1[5]
    ring_sel += k1[6]
    # AO3400A SOT-23: 1 G  2 S  3 D -- AOS datasheet rev 3 p.1 package drawing (D alone on
    # its side, G at the pin-1 dot), read 2026-09-30. K1 re-read the same day off Omron's
    # G6K-2F-Y terminal diagram (p. B-83): matches the list above, contact for contact.
    q1 = Part(name="Q_NMOS", ref_prefix="Q", ref="Q1", tag="Q1", dest="NETLIST", tool="skidl",
              value="AO3400A", description="relay coil driver (LCSC C20917)",
              footprint="Package_TO_SOT_SMD:SOT-23",
              pins=[Pin(num=1, name="G", func=P), Pin(num=2, name="S", func=P),
                    Pin(num=3, name="D", func=P)])
    gnd += q1[2]
    coil += q1[3]

    # ── crystals ─────────────────────────────────────────────────────────────
    y1 = Part(name="Crystal", ref_prefix="Y", ref="Y1", tag="Y1", dest="NETLIST", tool="skidl",
              value="TAXM8M4RFDCET2T", description="MCU HSE 8 MHz, CL 12 pF -- the PLL source for USB HS",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=i, func=P) for i in range(1, 5)])
    osc_in += y1[1]
    osc_out += y1[3]
    gnd += y1[2], y1[4]
    y2 = Part(name="Crystal", ref_prefix="Y", ref="Y2", tag="Y2", dest="NETLIST", tool="skidl",
              value="TAXM12M4RFBCCT2T", description="hub reference, 12 MHz, CL 12 pF (LCSC C133337)",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=i, func=P) for i in range(1, 5)])
    hub_xi += y2[1]
    hub_xo += y2[3]
    gnd += y2[2], y2[4]

    # ── L1 / FB1: the buck's output, and the ONE place the rails join ────────
    l1 = Part(name="L", ref_prefix="L", ref="L1", tag="L1", dest="NETLIST", tool="skidl",
              # ⚠ A PART, CHOSEN FOR SATURATION AT THE IC'S LIMIT (2026-10-05). TI SNVSA24
              # 9.2.2.2: "Using a rating near 1.6 A will enable the LMR16006 to current
              # limit without saturating the inductor. This is preferable to the LMR16006
              # going into thermal shutdown mode and the possibility of damaging the
              # inductor if the output is shorted". The limit is 1.2 A typical, 1.7 max.
              # APV PNR3015 (its sheet, 2023-12; guaranteed / typical, 30 % drop):
              #   47 uH  0.65 / 0.88 A saturation, 0.45 / 0.58 A rms   <- what was here
              #   22 uH  1.15 / 1.40,  0.75 / 0.90
              #   15 uH  1.40 / 1.80,  1.00 / 1.20                     <- this
              #   10 uH  1.50 / 2.00,  1.50 / 2.00 (10,880 in stock: the alternate)
              # 15 uH is the largest value whose GUARANTEED saturation clears the typical
              # limit, and its typical clears the maximum. Same series, same land.
              # Ripple 5 x (1 - 5 / 24) / (15 uH x 700 kHz) = 0.38 A, so the 0.257 A worst
              # load peaks at 0.45 A. LCSC C19634062, 3 x 3 x 1.5.
              value="PNR3015-150M", description="15 uH buck output inductor, Isat 1.4 A, SHIELDED "
              "-- it sits on the same board as a magnetic pickup's preamp",
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
               tool="skidl", value="BLM18KG601SN1D",
               description="5 V rail split: buck side to board side. 600 ohm at "
               "100 MHz, 1.3 A, 150 mohm (LCSC C85833) -- the 200 mA bead this replaces "
               "sat under the board's 257 mA worst case",
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
        d = _d(tag, "LESD5L5.0CT1G", "panel USB data-line clamp, 0.5 pF, bidirectional "
               "(LCSC C5274293) -- J1 is the port a stranger plugs into")
        net += d[1]
        gnd += d[2]
    # ⚠ PAD 1 IS THE CATHODE AND IT GOES TO +5V (2026-10-04). It was drawn the other way
    # round -- cathode on the FET's drain, anode on the rail -- which is a diode forward
    # across the supply every time the relay is switched on: 5 V through a 150 mA diode
    # into a FET that is fully enhanced. Nothing in the build could see it (two nets, two
    # pads, either way round routes clean); the manual polarity review did.
    d4 = _d("D4", "1N4148WT", "coil flyback, cathode to +5V (LCSC C917006) -- the coil is "
            "an inductor and the FET is not")
    v5 += d4[1]
    coil += d4[2]
    # D5 IS THE PHANTOM GUARD'S CLAMP and it sits INSIDE the DC block: a blocking
    # capacitor stops the 48 V but passes the insertion edge straight through.
    blocked = Net("OUT_BLOCKED")
    d5 = _d("D5", "ESD5B5.0ST1G", "bidirectional 5 V TVS (LCSC C93623): catches the "
            "insertion edge C1 passes through. The node it sits on idles at VMID and swings "
            "0..5 V, inside its 5.0 V working voltage")
    blocked += d5[1]
    agnd += d5[2]
    # ⚠ D7 IS NOT OPTIONAL, AND FINDING THAT OUT IS THE REASON THE RING TOOK MORE THAN
    # A BUFFER. On a TRS-to-XLR cable the RING IS PIN 3, and a desk with phantom power on
    # puts +48 V down pin 3 through 6.81k exactly as it does down pin 2. The tip has been
    # guarded since this board was drawn -- R9, C1 and D5 -- and a ring added without the
    # same three parts would be a brand-new 48 V path onto a brand-new op-amp. So the cold
    # leg is a part-for-part mirror of the hot one, which the matching argument at U9 wants
    # anyway: R20 for R9, D7 for D5, C41 for C1, R21 for R10.
    d7 = _d("D7", "ESD5B5.0ST1G", "RING phantom-guard clamp -- the mirror of D5. A TRS "
            "plug's ring lands on XLR pin 3, which carries +48 V through 6.81k just like "
            "pin 2, and C41 blocks the DC but passes the insertion edge")
    ring_blocked += d7[1]
    agnd += d7[2]
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
    # The MCU pin floats until firmware sets it, and so did this gate: a relay free to
    # chatter in the audio path at every power-up. Held OFF (= the direct path) by 100k.
    r36 = _r("R36", "100k", "relay gate pull-down -- off through reset")
    q1[1] += r36[1]
    gnd += r36[2]
    r6 = _r("R6", "10k", "NRST pull-up")
    nrst += r6[1]
    v3v3 += r6[2]
    # NRST runs 10 mm to its SWD pad with nothing on it but a 10k: a glitch there is a reset
    c54 = _c("C54", "100nF", "NRST filter")
    nrst += c54[1]
    gnd += c54[2]
    r7 = _r("R7", "10k", "BOOT0 pull-down -- run from flash unless deliberately held")
    boot0 += r7[1]
    gnd += r7[2]
    # JACK_MODE floats through reset too, and it is an analog switch's control: low =
    # balanced until firmware says otherwise, instead of whatever the pin picks up.
    r37 = _r("R37", "100k", "JACK_MODE pull-down -- balanced through reset")
    jack_mode += r37[1]
    gnd += r37[2]
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
    c3 = _c("C3", "100nF/50V", "24 V input HF bypass")
    v24 += c3[1]
    pgnd += c3[2]
    # 100 nF, not the 10 nF that stood here: SNVSA24's pin table and its application
    # circuit both ask for 0.1 uF between CB and SW
    c4 = _c("C4", "100nF", "buck bootstrap")
    boot += c4[1]
    sw += c4[2]
    for tag in ("C5", "C6"):
        c = _c(tag, "22uF/16V", "5 V bulk, BUCK SIDE of the bead",
               "Capacitor_SMD:C_0805_2012Metric")
        v5_pre += c[1]
        pgnd += c[2]
    # THE GROUND TIE (see the J6/J7 note): the one place PWR_GND and GND meet, beside C5,
    # where the buck's output current comes back.
    r60 = _r("R60", "0R", "ground tie, PWR_GND to GND -- the instrument's star point",
             "Resistor_SMD:R_0603_1608Metric")
    pgnd += r60[1]
    agnd += r60[2]
    for tag, val, net, ref, desc in (
            ("C7", "10uF", v5, agnd, "5 V bulk, board side of the bead"),
            ("C8", "100nF", v5, agnd, "5 V HF bypass"),
            ("C9", "10uF", v3v3, gnd, "3V3 bulk"),
            ("C10", "100nF", v3v3, gnd, "MCU bypass"),
            ("C11", "100nF", v3v3, gnd, "MCU bypass"),
            # U1 has five groups of supply pins (1; 13 + 17; 31 + 32; 50 + 51; 67 + 68) and
            # had two capacitors, the nearer of them 9 mm from any of the nine pins. One
            # per group now, each at its pins (see the placements).
            ("C51", "100nF", v3v3, gnd, "MCU bypass"),
            ("C52", "100nF", v3v3, gnd, "MCU bypass"),
            ("C53", "100nF", v3v3, gnd, "MCU bypass"),
            # Supply pins that had no capacitor of their own (quality A2, 2026-10-04): the
            # inlet ahead of the switch had none on its net at all, the LDO's input shared
            # an op-amp's 100 nF 5 mm away, and two op-amps borrowed a neighbour's.
            ("C55", "100nF/50V", v24_in, pgnd, "inlet HF bypass, ahead of the switch"),
            ("C56", "100nF/50V", v24, pgnd, "24 V HF bypass at J10"),
            ("C57", "100nF", v5, gnd, "VBUS bypass at J4"),
            ("C61", "100nF/50V", v24_opt, pgnd, "HF bypass at the J9 outlet, after the fuse"),
            ("C58", "1uF", v5, gnd, "LDO input -- AP2112 asks for 1 uF at IN"),
            ("C59", "100nF", v5, agnd, "U8 bypass"),
            ("C60", "100nF", v5, agnd, "U7 bypass"),
            ("C12", "100nF", v3v3, gnd, "hub bypass"),
            ("C13", "100nF", v5, agnd, "ADC analog bypass"),
            ("C14", "100nF", v3v3, agnd, "DAC AVDD bypass -- 3V3, never 5 V (abs max 3.9)")):
        fp = ("Capacitor_SMD:C_0805_2012Metric" if val == "10uF"
              else "Capacitor_SMD:C_0402_1005Metric")
        c = _c(tag, val, desc, fp)
        net += c[1]
        ref += c[2]
    # Y1 and Y2 are both CL 12 pF parts: 15 pF each side is 7.5 in series plus about
    # 4.5 pF of pin and track. (The hub's pair was 12 pF "until its own part is chosen";
    # it is chosen, and 12 pF left it 1.5 pF light.)
    for tag, net in (("C15", osc_in), ("C16", osc_out), ("C17", hub_xi), ("C18", hub_xo)):
        c = _c(tag, "15pF", "crystal load")
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
            # C31 is the 0402 (6.3 V, on a 1.8 V pin): the 0805 stood in the mouth of the
            # channel the inlet's full current leaves by, and no other site clears both the
            # DAC's pins and the inlet's body
            ("C31", "10uF", ldoo, gnd, "DAC LDOO bulk", None),
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
            ("C40", "10uF", vmid, agnd, "VMID reservoir", C0805),
            # ── the RING leg ─────────────────────────────────────────
            ("C41", "2.2uF/100V", ring_blocked, ringp, "RING DC BLOCK -- C1's mirror, and a "
             "safety part for the same reason: 100 V is the RATING, because it sits charged "
             "to 48 V for the duration of a phantom fault",
             "Capacitor_SMD:C_1210_3225Metric"),
            ("C42", "1uF", ring_sel, ring_in, "ring path coupling, off K1 POLE B -- "
             "C39's mirror on the other pole", C0805),
            ("C43", "100nF", v5, agnd, "U9 bypass", None),
            ("C44", "100nF", v5, agnd, "U10 bypass -- the pot's supply is also the reference "
             "its wiper divides, so it gets its own", None),
            ("C45", "2.2nF C0G", dac_r_filt, agnd, "DAC right output filter, with R23 -- "
             "C34's mirror", None),
            ("C46", "100nF", v5, agnd, "U11 bypass", None),
            ("C47", "100nF", v5, agnd, "U12 bypass", None)):
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
            ("R19", "10k", ovcur, v3v3, "hub OVCUR# pulled inactive"),
            # ── the RING leg: every one of these is the mirror of a TIP part ─────────
            ("R20", "220R", ring_buf, ring_blocked, "ring output series -- R9's mirror, and "
             "the part that makes a TS PLUG SAFE: it shorts ring to sleeve, so this resistor "
             "is what the ring buffer drives in mode 1"),
            ("R21", "100k", ringp, agnd, "ring output bleed -- R10's mirror"),
            ("R22", "100k", ring_in, vmid, "ring buffer bias to VMID -- R16's mirror"),
            ("R23", "470R", proc_r, dac_r_filt, "DAC right output filter, with C45 -- R13's "
             "mirror. The right channel needs TI's filter for the same reason the left does"),
            ("R24", "10k", dac_r_filt, ring_att, "DAC right -6 dB with R25 -- R14's mirror. "
             "2.1 Vrms is more than a 5 V rail carries on EITHER channel"),
            ("R25", "10k", ring_att, agnd, "ring attenuator bottom -- R15's mirror, and it "
             "holds the node at 0 V so nothing steps when the DAC starts"),
            ("R26", "10k 0.1%", buf, inv_n, "inverter input -- 0.1% because this pair IS "
             "the balanced output's CMRR (1% would be ~34 dB, 0.1% ~54 dB)"),
            ("R27", "10k 0.1%", inv_n, inv_out, "inverter feedback -- the other half of "
             "that pair, and it must be the SAME tolerance and ideally the same reel"),
            ("R28", "10k", ring_sel, agnd, "pole B common to 0 V -- R15's mirror, so the "
             "ring throw makes no DC step either")):
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
# ── -X GROWTH (2026-09-30). The audio section ran out of room: twenty-one TRS/gain parts
# went in, every sweep ordering placed them legally, and every ordering left one part
# 5-9 mm from where it belongs. The +X edge IS the panel and cannot move, so the growth
# is -X, into the instrument's interior rather than at a wall.
#
# ⚠ MEASURED CLEAR BEFORE IT WAS APPLIED, by intersecting a 30 mm test prism in the
# board's own y/z band against every collect_components() solid: the ONLY two occupants
# are cables -- optical_cable_usb (3,246.9 mm3, starting AT the board edge) and wire_usb
# (102.9 mm3, 18.02 mm free). No plastic, no boards, no chassis structure in 30 mm. An
# earlier BOUNDING-BOX test told me nothing at all: it "found" chassis_0, the hollow
# shell the board sits INSIDE, so every clearance came out negative and it missed both
# real occupants. Probe the finished SOLID by intersection, never a bbox.
#
# ⚠⚠ THE BOARD STAYS SYMMETRIC ABOUT ITS OWN ORIGIN, AND THAT IS NOT A STYLE CHOICE --
# IT IS THE CONVENTION THIS PROJECT ALREADY SETTLED. layout.py's `_add_zone` builds each
# pour as a rectangle CENTRED ON THE ORIGIN out of `outline_mm`, so an asymmetric outline
# pours off-centre: at GROW_X = 12 the pour would overhang the +X edge by 6 mm (clipped,
# harmless) and stop 6 mm SHORT of the -X edge -- which is precisely where the USB block
# now lives and where its GND has to reach the plane. Tried it that way first, and the
# laid-out board said so out loud: `2 stitch via(s) landed where the plane is not ...
# 3.20 mm away`, up from none.
#   motor_ctrl hit this exact wall from the other side and wrote the answer down (see its
# BOARD_W note): "The frame had to shrink rather than the edge move: outline_mm is the
# POUR's layout region and it is centred on the origin, so an asymmetric board would pour
# off-centre. So BOARD_W drops 6.20 and all 64 placements moved +3.10 in x to re-centre --
# the parts did not move relative to each other or to the -X end, only the origin did."
# Same move here, mirrored: the origin shifts -GROW_X/2 with the laminate, so every
# placement gets +GROW_X/2 back. NOTHING is re-placed; the frame moved under it. That
# keeps the shared layout.py untouched, which matters -- eleven boards run through it.
#
# BOARD_W STAYS 74.0, as the PRE-GROWTH half-width datum: every placement below, and the
# panel expressions J5/J1/J6 (`BOARD_W / 2 + PANEL_OVERHANG`), are authored in the OLD
# frame and re-centred in one pass at the bottom of this dict. Read a coordinate here as
# "distance from the panel edge, as it always was".
GROW_X = 12.0
# J10's pad row. -9.15 since it became a 6-way turned 180 (2026-10-04): the body now stands
# on the +Y side of its pads, and this is the y that puts its courtyard between C28 (moved
# 0.3 down for it) and D3 with 0.2 to spare on each side.
_J10_Y = -9.15
# The USB mouths stand PROUD of the -X edge rather than 0.5 mm inboard of it: a plug's
# overmold is wider than the shell and its lower half sits below the board top (USB-A axis
# 3.3 mm up, 8 mm overmold; USB-C worse at 1.63 mm up), so with the mouth inboard the
# overmold lands on 0.5 mm of laminate (5.6 mm3 measured against J4's cable). Overhanging
# the receptacle is the usual remedy. Pads stay well behind the edge: J2/J4 copper 8.38 mm,
# J3 1.34 mm.
USB_MOUTH_SHIFT = -1.0     # 0.5 inboard -> 0.5 proud. Routes clean ONLY with THRU/HUB_DN1 frozen (see the bottom of this file)
BOARD_W_GROWN = BOARD_W + GROW_X        # 86.0 -- the laminate that gets fabricated
# How far each panel connector's body front stands past the +X edge: the fit clearance
# between the board and the endplate's panel, plus the panel itself. src/electronics.py
# builds the panel to the same two numbers (OP_PANEL_CLR, OP_PANEL_T), and
# reads the placed board back from <board>.geom.json rather than trusting these.
PANEL_CLR, PANEL_T = 0.3, 1.6
PANEL_OVERHANG = PANEL_CLR + PANEL_T
_FRONT = {"J5": 13.40, "J1": 7.07, "J6": 6.80}
# J6's O12.9 NOSE stands 4.0 in front of its body; it is the nose, not the body, that
# reaches the panel face. And its axis: 16 mm of body has to clear J10 above it and keep
# its shell legs 0.3 off the board's -Y edge, which leaves about a millimetre of choice.
J6_NOSE, J6_Y = 4.0, -23.00
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
_EAR_X0 = -BOARD_W_GROWN / 2 - EAR_W
_EAR_Y1 = -BOARD_L / 2 + EAR_H
EAR_HOLE_XY = (_EAR_X0 + EAR_W / 2, -BOARD_L / 2 + EAR_H / 2)

BOARD_NOTES = {
    "outline_mm": (BOARD_W_GROWN, BOARD_L),
    "outline_poly": [(_EAR_X0, -BOARD_L / 2), (BOARD_W_GROWN / 2, -BOARD_L / 2),
                     (BOARD_W_GROWN / 2, BOARD_L / 2), (-BOARD_W_GROWN / 2, BOARD_L / 2),
                     (-BOARD_W_GROWN / 2, _EAR_Y1), (_EAR_X0, _EAR_Y1)],
    "cutouts": [{"xy": EAR_HOLE_XY, "d": EAR_HOLE_D}],
    "mounting_hole_xy": EAR_HOLE_XY,
    # the ear moved the router's first-pass choices and BOOT0 (a one-resistor strap across
    # the digital block) came back unrouted at the default pass count; more passes let the
    # optimiser rip up and re-lay rather than freeze the early mess (route.py PASSES note)
    "router_passes": 20,   # 40 was tried with the USB-C sockets (2026-10-02): no better, see close_last.py
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
    # ⚠ HUB_DN2 IS WITH THE ROUTER TOO SINCE J4 BECAME A USB-C (2026-10-02). It was the one
    # pair _diff_pairs could lay, because a USB-A's four pads sit in one row; a USB-C at
    # 270 deg has the same A/B rows along Y that stop it at J3, and it reports the same
    # ESCAPE failure ("no clear path U4->J4"). verify.py is what says whether the router
    # kept the two conductors together.
    "diff_pairs": [],
    # ⚠ U1.27 GETS AN ESCAPE VIA, AND THE MEASUREMENT SAYS WHY. JACK_MODE was the one net
    # the router left unconnected after the TRS parts went in, and it could not be repaired
    # afterwards either -- maze3d found no path at 0.127 mm on any of three layers at any
    # reach. The reason is not the 22 mm span, it is the FIRST 0.2 mm: a flood from that pad
    # across F.Cu reaches ONE CELL. The pad is walled in by its own neighbours' escapes.
    # But the same neighbourhood on B.Cu has 277 free cells of 289, and In2 has 193. So the
    # copper is not missing, it is on the wrong layer, and what the net needs is to leave
    # F.Cu at the pad rather than to travel on it.
    # ⚠ A POST-ROUTE REPAIR CANNOT DO THIS, which is the general lesson and not a quirk of
    # this net: a repair may not drop a via inside a 0.4 mm pad field, so it can only ever
    # work with the layer the pad is already on. Escaping a fine-pitch QFN is a PLACEMENT-time
    # move. The router escapes the other twenty-four signals here happily because it does it
    # before any of this copper exists.
    # ⚠ AND THIS IS THE OPPOSITE CONCLUSION TO THE OPTICAL BOARD, DELIBERATELY. There,
    # escape vias made the PHY edge monotonically worse (2 -> 3 -> 5 unconnected) and were
    # reverted. The difference is that those were added on a hypothesis about congestion;
    # this one is aimed at a pad whose F.Cu reachable set was MEASURED at one cell.
    # ⚠ TRIED AND REVERTED: ESCAPE VIAS ON 61/62, HUB_DN1's PAIR. With 27 escaped the
    # pair came back beautifully length-matched -- 11.0 and 11.1 mm, 0.15 mm of skew against
    # an 8.30 budget, where before it was 13.87 -- but still on different layer sets, DP on
    # B.Cu and DM on In2.Cu. Escaping both looked like the same medicine, and each half
    # already carries a via so it would have added no discontinuity.
    # It was MEASURED BEFORE ROUTING RATHER THAN AFTER, and that is what killed it: the two
    # vias land at 1.612 mm and 0.912 mm from their pads -- same direction, but 0.70 mm of
    # STAGGER. The escape's radial search finds each pad's first free position independently
    # and has no notion that these two belong to each other. A staggered pair of vias on a
    # 480 Mbps pair is a mode-conversion fault, which is a worse thing to own than the layer
    # split it was meant to fix. Cost: one layout run, no route.
    # ⚠⚠ AND THE NOTE THAT USED TO SIT HERE WAS WRONG, WHICH MATTERS MORE THAN THE
    # EXPERIMENT. It said "the mechanism is escape_runs, not pin_escapes -- it takes the
    # whole escape at coordinates chosen TOGETHER". It does not. Reading layout.py: the via
    # position is SEARCHED by the escape routine, and escape_runs only lays a run FROM the
    # via that search chose. layout.py says so in as many words, and says hard-coding a via
    # position in the board notes was tried and rejected -- "a hard-coded escape position
    # goes stale the moment any placement moves -- it already did once, leaving stubs at
    # angles through paths nobody had checked". So the correction is not a detail: a reader
    # following the old note would have reached for a mechanism that does not exist.
    # ⚠ AND THE REJECTION ITSELF WAS REASONED RATHER THAN MEASURED. 0.70 mm of via
    # stagger is ~4.7 ps against a 2,080 ps bit -- 0.2% -- while the layer split it would be
    # fixing is a CONTINUOUS impedance mismatch over the whole 11 mm run, because B.Cu and
    # In2.Cu sit at different distances from the In1 reference plane. Calling the small
    # continuous fault the lesser one needed a number and did not have one.
    # ✅ TESTED AND REVERTED: ESCAPE VIAS ON 61/62, AND THE TEST WAS WORTH RUNNING.
    # The previous note rejected this on 0.70 mm of via stagger without comparing it to what
    # it fixes; the route settles it, and it settles MORE than was asked:
    #   HUB_DN1 layer split  FIXED -- it came back ok on skew AND on layer set
    #   a SHORT              NEW   -- DP's 1.612 mm stub runs into DM's via on F.Cu. That is
    #                               the 0.70 mm asymmetry, cashed as a DRC violation rather
    #                               than as the theory it was
    #   THRU                 BROKE -- the layer split MOVED to a pair that was fine before
    # ⚠ AND THAT LAST LINE IS THE REAL FINDING. Fixing one pair's layer set pushed the
    # fault onto another, which says the split is not a property of HUB_DN1 at all -- it is
    # CONTENTION for a scarce inner lane. Four pairs want In2.Cu and the board has room for
    # three, so whichever pair is helped, another is displaced. No amount of per-pair
    # escaping fixes a shortage; that is a placement or a layer-count question.
    # Board to beat remains output_panel.best-0-0.kicad_pcb: 0 unconnected, 0 violations,
    # one layer-set problem -- which is strictly better than 1 unconnected, 1 violation and
    # one layer-set problem somewhere else.
    # U1.26 (POT_SDI) joined 2026-10-02: with the USB-C sockets the router laid +3V3 across the
    # inner side of this pad row and vias for 25 and 27 across the outer, and left 26 boxed in
    # on F.Cu through three rounds. Same fault as 27, same medicine.
    # (2026-10-04: none now. With U1 turned, 26 and 27 face east into open board, and the
    #  two escapes -- adjacent pins, both sent the same way -- landed one on the other.)
    "pin_escapes": (),   # was ("U1.27", "U1.26");   # U1.7 (NRST) was tried too: it closed NRST and opened OSC_IN, its neighbour
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
    # (2026-10-01: THAT TRUNK COPPER NOW EXISTS -- "THE 24 V POWER PATH, DECLARED AND SIZED"
    #  at the bottom of this file, 2.0 mm with the rails on a layer each. The netclass
    #  width below is what the router uses for the BRANCHES: the buck's input and D6.)
    "net_widths": {"+24V": 0.5, "PWR_GND": 0.5, "+24V_IN": 0.5, "+24V_OPT": 0.5},
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
        # same_layer is OFF for this one pair, and the reason is geometry, not convenience:
        # the hub and the MCU order DM/DP oppositely, so one conductor has to pass under the
        # other. The copper is drawn by hand (bottom of this file): DM on F.Cu throughout,
        # DP under it for 2.9 mm of B.Cu, the whole pair about 7 mm long. Making DM dip to
        # B.Cu as well, only to make the two layer sets read the same, would add two vias.
        {"name": "HUB_DN1", "max_skew_mm": 8.3, "same_layer": False, "max_vias": 2,
         "nets": ["HUB_DN1_DP", "HUB_DN1_DM"],
         "why": "USB 2.0 high speed, hub downstream port 1. 480 Mbps is 2,080 ps a bit, so skew has "
                "room; what has to hold is that the two stay together and that neither "
                "collects vias beyond the one crossover the pin order forces, each being "
                "an impedance discontinuity."},
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
    # ⚠⚠ BUT IT WAS A *REPAIR* VIA, LAID AFTER ROUTING, AND THAT IS NOT THE SAME THING AS
    # NOT DRIFTING. The 0.7 mm above was checked against DM on In2 only -- and a through
    # via is on EVERY layer, while B.Cu under the QFN is open ground to a router that does
    # not know the via is coming. It held on one route by luck. On 2026-09-30 a one-diode
    # move elsewhere re-rolled the router, a +3V3 B.Cu track ran through this spot, and the
    # via was stamped onto it afterwards: a dead short across the hub's supply, reported
    # as "shorting_items" with nothing near the part that had actually moved.
    # So it is DECLARED copper now ("vias", layout.py), laid before the searches and the
    # router like the 101 GND stitches beside it, which the router has always routed
    # around. Same point, same size; the only change is that the router can see it.
    "vias": [("GND", -15.500, -7.300)],
    # (V5_PRE's hop to C5 was repaired here for one route. With the 24 V path declared the
    #  router closes it itself -- 0.18 mm from where the repair via stood, so the two holes
    #  overlapped. Gone; the list is kept because the re-centring pass reads it.)
    "repair_vias": [],
    "repair_tracks": [
        # (the PWR_GND hop that stood first here is gone: since the mounting ear the router
        #  closes PWR_GND on its own, and the pinned copy crossed its V5_PRE, 2026-09-21)
        # (THE 24 V BUS IS NOT HERE ANY MORE. The J7 -> J9 hop and the inlet's own runs were
        #  0.5 mm post-route repairs; the whole power path is DECLARED copper now, sized for
        #  the supply -- see the bottom of this file.)
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
        # routed board's F.Fab. (J6 is the Kycon power jack now: its F.Fab is the BODY, whose
        # front is 6.80 ahead of the centroid of its eleven pads, and the nose is 4.0 more.)
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
        "J6": (BOARD_W / 2 + PANEL_OVERHANG - J6_NOSE - _FRONT["J6"], J6_Y, 90.0),  # 24 V inlet
        # -X, FACING INTO THE INSTRUMENT.
        # ⚠ 270, NOT 180, AND THE DIFFERENCE IS NOT COSMETIC. This footprint's
        # courtyard runs -12.68..+3.90 in Y about the pad centroid, so its MOUTH is
        # the -Y face; at 180 the shell points +Y -- along the board, opening onto
        # the pickup terminals -- while still measuring flush against the -X edge.
        # place_check passes either way (the rotated courtyard lands in free space
        # both times), so nothing catches it but reading the offset. 270 turns the
        # mouth out through the -X edge, which is what these three are for.
        "J2": (-29.44 - GROW_X + USB_MOUTH_SHIFT, 24.00, 270.0),   # -> the Pi's gadget port
        "J3": (-29.44 - GROW_X + USB_MOUTH_SHIFT, 8.00, 270.0),    # hub upstream -> a Pi host port
        "J4": (-29.44 - GROW_X + USB_MOUTH_SHIFT, -8.00, 270.0),   # hub downstream -> the optical board
        # J4's two CC pull-ups, in the board the USB-A shell used to cover
        "R29": (-35.50, -5.50, 0.0),
        "R30": (-35.50, -10.50, 0.0),
        # +Y BAND: THE ANALOG CHAIN. It is up here because the switcher is down
        # there -- 50 mm of board between a 24 V switching node and a magnetic
        # pickup's preamp is the cheapest noise measure available.
        "J8": (-13.50, 28.00, 0.0),     # pickup screw terminals
        "U8": (-4.50, 29.00, 0.0),      # pickup buffer, right at the terminals
        "R8": (-3.20, 24.90, 0.0),
        "U2": (2.50, 29.00, 0.0),       # ADC
        # the ADC's supports fill the strip under it that the DAC vacated (2026-09-21)
        # the row sits 1.8 mm further west than it did: U2's supply pins are the top of its
        # WEST column, and at 4.40 the VDD capacitor was 5.7 mm from its pin
        "C19": (-0.90, 32.35, 180.0),   # VREF 0.1, 1.4 mm above pin 1 (it was 5.7 mm below)
        "C13": (-1.25, 25.30, 0.0),     # VCC 0.1
        "C22": (0.67, 25.30, 0.0),      # VDD 0.1
        "C59": (-3.60, 31.50, 180.0),   # U8's own, above its V+ pin
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
        "C14": (10.60, -18.20, 180.0),    # AVDD 0.1 -- its 3V3 pad TOWARD pin 8 (turned away, it was walled in and left open)
        "R13": (10.60, -19.40, 0.0),      # output filter 470R
        "C34": (10.60, -20.60, 0.0),      # output filter 2.2nF
        "R14": (8.60, -20.60, 0.0),      # -6 dB
        # (C28, C30 and C31 moved 2026-10-01: the Kycon inlet's body is 16 wide where the
        #  barrel jack's was 9, and its corner and one shell leg landed on all three.)
        "C28": (21.00, -12.80, 0.0),      # DVDD 0.1
        "C30": (21.00, -14.00, 0.0),      # LDOO 0.1
        "C27": (13.60, -21.40, 0.0),     # CPVDD 10u
        "C29": (17.20, -21.40, 0.0),     # DVDD 10u
        "C31": (20.25, -20.50, 180.0),   # LDOO 10u, an 0402 under the DAC's last pin
        "K1": (-13.00, 15.00, 0.0),
        "Q1": (-4.00, 15.00, 0.0),
        "R5": (-4.00, 12.00, 0.0),
        "R36": (-6.60, 12.00, 0.0),
        "R37": (1.20, -9.60, 0.0),      # at U1's east side, where JACK_MODE leaves
        "F1": (-35.20, -21.50, 0.0),    # below J9
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
        # ── THE RING LEG, THE INVERTER AND THE GAIN POT. Sites SWEPT, not chosen ────
        # Every position below came out of a courtyard-collision sweep against the board as
        # it actually stood: 0.60 mm of air between courtyards, 1.0 mm off the rim, biggest
        # parts first, and each IC immediately followed by its own bypass so the bypass gets
        # the near site rather than whatever is left.
        # ⚠ 0.60 AND NOT 0.25, AND THE FIRST ROUTE IS WHY. At 0.25 mm of courtyard air the
        # board came back with eleven SOLDER_MASK_BRIDGE errors through this region: the
        # courtyards cleared each other and the MASK OPENINGS did not. Courtyard clearance
        # is not mask clearance, and only one of them is what the fab cares about.
        # ⚠⚠ AND THIS CORNER IS NOW FULL -- SAID PLAINLY, BECAUSE THE NUMBERS SAY IT.
        # Twenty-one parts went in and the sweep was re-run three times with different
        # orderings; every ordering placed all of them legally, and every ordering left at
        # least one part 5-9 mm from where it belongs. D7 is 9.25 mm from the ring it
        # clamps, C43 is 5.7 mm from U9's supply pin. Those are legal and they are not good,
        # and re-rolling the sweep a fourth time would only move which part is worst.
        # The honest reading is that the audio section has run out of room, not that the
        # placer needs another try. It is TOLERABLE as it stands -- D7 sits behind R20's
        # 220R, so U9 is current-limited whatever the clamp does, and an op-amp bypass at
        # 5.7 mm still resonates well above the audio band -- but if this board is ever
        # respun, the +X edge cannot move (it is the panel) so the growth is -X, and it
        # wants the USB block at that end spread out to free the middle for the audio.
        "U10": (14.00, 2.00, 0.0),      # MCP4261, between the two legs it drives
        "C44": (13.60, 5.60, 180.0),    # pot bypass, 3.2 mm from VDD (it stood 8.4 mm away); nearer is the THRU pair's via
        "C60": (5.40, 10.40, 180.0),    # U7's own, above its V+ pin
        "U9": (6.76, 0.43, 0.0),        # ring buffer, matched to U7
        "C43": (11.49, -2.53, 0.0),     # U9 bypass -- 5.7 mm, the worst of the op-amp three
        # ⚠ THESE SIX WERE RE-SWEPT AGAINST THEIR **REAL** COURTYARDS, AND THE FIRST
        # SET WAS GUESSED. The other fifteen were measured off a placed board; these did
        # not exist yet, so their sizes were typed from memory -- and they were wrong by
        # about a factor of two, because what got typed was the PAD EXTENT and the BODY,
        # not the courtyard: U11 is 4.19 x 3.49 and not 1.90 x 2.60, an 0402 courtyard is
        # 1.95 x 1.03 and not 1.05 x 0.55. The route found it as two courtyards_overlap
        # errors around U11 -- the only two errors on an otherwise 0-unconnected board.
        # A sweep is only as good as the boxes handed to it, and a guessed box is a
        # guessed placement wearing a measurement's clothes.
        "U11": (1.93, -0.45, 0.0),      # the inverter: the balanced cold leg
        "C46": (4.53, -3.98, 0.0),      # U11 bypass, 4.9 mm -- see the note above
        "U12": (14.50, -3.66, 0.0),     # SPDT: inverted tip, or the right-hand channel
        "C47": (7.75, -3.10, 0.0),      # U12 bypass. The switch draws no output current,
                                        # so its supply is the least demanding of the four
        "R26": (-3.25, 2.00, 0.0),      # the 0.1% pair that sets the balanced CMRR --
        "R27": (-3.32, 4.35, 0.0),      # same reel, and they stay near each other
        "C41": (21.54, 5.06, 0.0),      # ring DC block, 1210 (C1's mirror)
        "D7": (18.29, -3.91, 0.0),      # ring phantom clamp (D5's mirror) -- see above
        "R21": (21.19, 1.51, 0.0),      # ring bleed (R10's mirror)
        "R20": (7.76, 5.75, 0.0),       # ring series 220R (R9's mirror)
        "C42": (10.78, -5.29, 0.0),     # ring path coupling, off K1 pole B
        "R22": (16.95, -6.60, 90.0),     # ring bias to VMID (R16's mirror)
        "R28": (-7.25, 11.00, 0.0),     # pole B common to 0 V, beside K1
        # the DAC's right channel, beside the left channel's own filter and divider
        "R23": (9.55, -26.30, 90.0),     # right output filter 470R (R13's mirror)
        "C45": (9.55, -28.50, 90.0),     # right output filter 2.2nF (C34's mirror)
        "R24": (5.74, -21.34, 0.0),     # right -6 dB top (R14's mirror)
        "R25": (5.34, -23.81, 0.0),     # right -6 dB bottom (R15's mirror)
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
        # ⚠ U1 TURNED 90 DEG AND MOVED 1 MM EAST (2026-10-04), AND ITS NEIGHBOURHOOD IS
        # motor_ctrl's, PART FOR PART. At 0 deg the oscillator pins (5, 6) faced the hub
        # across a 2.4 mm channel while the crystal sat on the south side, 9 mm of track
        # round the package corner; the nine supply pins shared two capacitors, 9 and
        # 12 mm away; and the router left OSC_OUT and a +3V3 pin open. At 90 deg pins 1-17
        # face SOUTH at the crystal, the USB pair (61, 62) faces WEST at the hub, the I2S
        # pins (35-39) face north toward the ADC, and each supply group has its capacitor
        # within 3 mm. Offsets from U1 are the ones motor_ctrl routes clean with.
        "U1": (-5.00, -8.00, 90.0),
        "Y1": (-6.40, -14.55, 0.0),
        "C15": (-9.30, -14.55, 90.0),
        "C16": (-3.50, -14.55, 90.0),
        "C54": (-10.80, -14.55, 90.0),   # NRST
        "C51": (-11.50, -10.60, 90.0),   # pins 67 + 68
        "C52": (-11.50, -4.60, 90.0),    # pins 50 + 51
        "C53": (0.40, -4.45, 90.0),      # pins 31 + 32
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
        "C58": (3.20, -7.50, 270.0),    # across IN and GND, where the SWD pads stood
        "C55": (27.90, -13.40, 90.0),   # between the inlet and J10, off the PWR_GND bar
        "C56": (29.70, -4.40, 0.0),     # above J10's two +24V ways
        "C57": (-39.50, -3.80, 90.0),   # behind J4, north of the DN2 pair
        "C61": (-31.60, -20.50, 0.0),   # between F1 and L1, pad 1 toward the fuse
        "C9": (11.00, -8.00, 0.0),
        "C10": (-1.90, -14.55, 90.0),    # pins 13 + 17
        "C11": (-11.50, -12.60, 90.0),   # pin 1
        "R6": (-9.00, -17.00, 0.0),
        "R7": (-12.00, -14.55, 90.0),
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
        "TP1": (-7.00, -0.60, 0.0),      # SWDIO, pin 48, is on U1's north side now
        "TP2": (-10.00, -0.60, 0.0),     # SWCLK, pin 52, at its north-west corner
        "TP3": (-4.00, -17.80, 0.0),     # NRST, pin 7, south: below the crystal row
        "TP4": (-1.00, -17.80, 0.0),
        "TP5": (-13.00, 1.20, 0.0),
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
        "J9": (-33.50, -15.50, 0.0),   # the optical board's feed
        # ⚠ J10 IS ON THE +X EDGE, NOT THE -Y ROW, BECAUSE THAT ROW IS FULL. The -Y edge
        # already carries U5, C3, C2, D6, J7, J9 and the barrel jack J6, and measured off
        # the board's real courtyards the widest remaining gap there is 5.25 mm against a
        # 13.40 mm connector. My first two guesses (x 17, then x 28) were both estimates
        # and the second landed three of J10's pads inside J6's courtyard -- the fourth
        # time today a part was placed by eye and rejected by DRC.
        #
        # Sited by searching the whole board against every real courtyard, preferring a
        # board edge so the cable can leave: +X edge, hard against it.
        "J10": (27.20, _J10_Y, 180.0),
        # ── THE POWER SWITCH (2026-10-04) ──
        # Q2 stands where J9 stood, hard against the inlet jack: source lead 4 mm from
        # the jack's +24 V pin, tab toward J7 so the switched rail leaves it westward on
        # F.Cu with no via. (15.40 is the pad CENTROID; the body's origin is at 14.86.)
        # J9 -- 0.12 A to the optical board -- gave up the site and moved to the open
        # ground west of the buck. The gate's four parts and the two output-filter parts
        # that were here share the 3.4 mm strip between J7 and the tab, above the lane.
        "Q2": (15.40, -28.50, 180.0),
        "R31": (-0.60, -22.20, 180.0),
        "R32": (1.90, -22.20, 180.0),
        "C49": (-0.60, -23.40, 180.0),
        "C48": (1.90, -23.40, 180.0),
        # the button's sense parts, beside J9's new site: nothing here carries current
        "R33": (-27.00, -12.40, 0.0),
        "R34": (-27.00, -13.60, 0.0),
        "R35": (-27.00, -14.80, 0.0),
        "C50": (-27.00, -16.00, 0.0),
        "Q3": (-24.00, -13.20, 0.0),
        "D8": (-24.00, -15.60, 0.0),
        "JP1": (-20.25, -13.20, 90.0),
        "D6": (-12.00, -28.00, 0.0),
        # THE BUCK AS ONE CELL (2026-10-04). Its nine parts stood in a row on a 5 mm grid:
        # the bootstrap capacitor 11 mm from CB, the feedback divider 15 mm from FB, the
        # catch diode 3.4 mm from SW and the first output capacitor 36 mm from the
        # inductor -- beside an audio converter. Measured pad to pad now:
        #   C3 (100 nF) 0.6 mm from VIN, C2 (10 uF) 1.6; both hang off one 2.8 mm rail.
        #     C2 lies ALONG the board edge, 4 mm in: a 1206 across 24 V stood on end
        #     2 mm from an edge is the part that cracks when the board flexes
        #   D1 cathode 0.7 mm from SW, its anode straight down to the ground lane
        #   C4 between CB and SW, 0.75 mm from each, in the strip under the inductor
        #   L1's SW pad 2.1 mm above the pin; C5 1.15 mm from L1's output pad
        #   R12 / R11 0.5 and 0.7 mm west of FB, the FB node 2.6 mm of track in all
        # Pin 2's ground leaves UNDER the package (the 0.95 mm channel between the pad
        # rows) straight to the lane, so the hot loop C3 -> VIN .. SW -> D1 -> lane -> pin 2
        # is 7 mm of F.Cu with no via in it.
        "C2": (-24.45, -28.00, 0.0),
        "C3": (-27.30, -28.48, 270.0),
        "U5": (-30.00, -28.00, 0.0),
        "L1": (-29.90, -23.30, 180.0),
        "D1": (-25.50, -25.60, 0.0),
        "C4": (-30.00, -25.70, 0.0),
        "R11": (-33.10, -27.85, 0.0),
        "R12": (-33.10, -28.95, 180.0),
        "C5": (-34.00, -25.00, 180.0),
        # the ground tie, just west of C5's return, its PWR_GND pad on the lane's end
        "R60": (-36.60, -29.00, 180.0),
        # the second bulk cap and THE BEAD sit at the island's +X end, which is where the
        # rail leaves for the rest of the board
        "C6": (13.00, -23.50, 0.0),
        "FB1": (16.60, -23.50, 0.0),
    },
    "refs_on_fab": True,
    "single_sided": True,
    "qty_per_instrument": 1,
    # ⚠ THIS BOARD NEEDS THE RETRY, AND IT IS THE FIRST ONE THAT HAS (2026-09-30). With
    # U4's belly via declared, pass 1 leaves INV_OUT (U12 -> U11) open -- 0 violations, every
    # pair clean, one net -- and repair_search finds no via-plus-two-track path for it. Pass
    # 2 hands that one net back to the generator and comes out 0 unconnected / 0 violations
    # with all four USB groups on matching layers. finish.py's own note says the retry "HAS
    # NEVER YET PAID"; that was measured on optical, whose failures were a congested strip.
    # Here every failure has been a SINGLE long net, which is the case the retry is for.
    "finish_rounds": 2,
}

# ── RE-CENTRE THE FRAME ON THE GROWN LAMINATE (one pass, nothing re-placed) ───────────
# Every placement above is authored in the PRE-GROWTH frame, whose origin is the centre of
# the 74 mm board. -X growth moves the laminate's centre -GROW_X/2, so each x gets
# +GROW_X/2 to stay exactly where it was relative to the +X panel edge and to every other
# part. See the BOARD_W note for why this is a re-centring and not a placement change.
#
# ⚠ THE THREE USB SHELLS TRAVEL WITH THE -X EDGE, NOT WITH THE PANEL. Their mouths ride
# that edge because their plugs come in from outside the board -- measured at 0.49-0.50 mm
# of fab-body relief off the old edge, from the routed board's own export. So they are
# authored `- GROW_X` above (the edge moved GROW_X further out in the old frame) AND take
# this pass's +GROW_X/2 like everything else (the frame moved under them too). Both terms.
#
# ⚠⚠ I GOT THIS WRONG BOTH WAYS BEFORE THE ASSERT BELOW SETTLED IT, and the second error
# was the more convincing one. First: shifted everything and trusted it. Then a hand check
# "at the far corner" said the USB shells would land 6.00 mm too far from the new edge, so
# I EXCLUDED them from the pass -- and the assert fired at once, J2 12.680 -> 6.680 mm,
# i.e. the exclusion was the bug and the original was right. The hand check had silently
# worked in export_geom's frame, which centres on the EAR-INCLUSIVE bounding box, and took
# the new edge from the asymmetric draft rather than the symmetric board. Two frames, one
# sum. This is the "verify derived frames" rule biting in a third place: do not derive a
# frame mapping by hand when a one-line invariant can be asserted in a single frame.
# ⚠ AND A PLACEMENT NAMES THE PAD CENTROID, NOT THE FOOTPRINT ORIGIN (layout.py
# `_anchor_on_pads`), while export_geom reports the ORIGIN. On a USB-A receptacle those are
# 5.40 mm apart, and that gap is why the exported x of J2/J3/J4 does not equal the authored
# x plus the frame offset. It looked for a while like layout was nudging edge connectors by
# hand. It is not. Do not "correct" a placement to close that difference.
EDGE_REFS = ("J2", "J3", "J4")          # mouths on the -X edge: referenced to THAT edge
_authored = dict(BOARD_NOTES["placements"])
BOARD_NOTES["placements"] = {
    _ref: (_x + GROW_X / 2.0, _y, _rot)
    for _ref, (_x, _y, _rot) in _authored.items()
}

# ⚠ AND THE HAND-LAID COPPER RIDES THE SAME FRAME, OR IT LANDS 6 mm FROM ITS PADS.
# vias and repair_tracks are raw board coordinates, authored against the same
# pre-growth origin as the placements. The first route after the growth shifted the parts
# and not these, and came back 3 unconnected / 18 violations against a committed 0 / 0 --
# every one of the eighteen was the SAME +24V repair run, now drawn straight across U3
# (the DAC) and C31 six millimetres from the J7 -> J9 -> J6 -> J10 pads it was laid to
# join. One pass, one frame, for everything that carries an x.
# None of these repairs touches J2/J3/J4, so none of them has to follow the -X edge.
BOARD_NOTES["vias"] = [
    (_net, _x + GROW_X / 2.0, _y) for _net, _x, _y in BOARD_NOTES["vias"]]
BOARD_NOTES["repair_tracks"] = [
    (_net, _layer, _w, [(_x + GROW_X / 2.0, _y) for _x, _y in _pts])
    for _net, _layer, _w, _pts in BOARD_NOTES["repair_tracks"]]
BOARD_NOTES["repair_vias"] = [
    (_net, _x + GROW_X / 2.0, _y) for _net, _x, _y in BOARD_NOTES["repair_vias"]]

# THE INVARIANT, ASSERTED: growth must not move any part relative to the edge it is
# referenced to. Panel parts keep their distance to +X; the USB shells keep theirs to -X.
# Distances are computed in each frame's own terms -- pre-growth half-width BOARD_W / 2,
# post-growth BOARD_W_GROWN / 2 -- because that is exactly what the re-centring changes.
for _ref, (_x, _y, _rot) in BOARD_NOTES["placements"].items():
    _x0 = _authored[_ref][0]
    if _ref in EDGE_REFS:
        _was, _now = _x0 + GROW_X + BOARD_W / 2, _x + BOARD_W_GROWN / 2
        _which = "-X edge"
    else:
        _was, _now = BOARD_W / 2 - _x0, BOARD_W_GROWN / 2 - _x
        _which = "+X panel edge"
    assert abs(_was - _now) < 1e-9, (
        "-X growth moved %s relative to the %s: %.3f mm -> %.3f mm. The re-centring pass "
        "and the per-part offsets disagree." % (_ref, _which, _was, _now))


# ── THE TWO PAIRS THE ROUTER MAY NOT RE-ROLL (2026-09-30) ────────────────────────────────
# HUB_DN2 is laid as a coupled pair by layout._diff_pairs and frozen. THRU (J1 -> J2) and
# HUB_DN1 (U4 -> U1) cannot be -- _diff_pairs reports an ESCAPE failure on both (J1's rows
# run along Y; U1 is a 0.4 mm QFN) -- so freerouting routed each conductor on its own, and
# every placement change since has split one or both across layers: D7's re-site and five
# USB overhang values, six of six, all with a DRC-clean board. verify.py is what saw it.
#
# So their copper is LIFTED FROM THE ONE BOARD THAT PASSES (overhang 0.0, D7 at its old
# site: four pairs `ok`) and laid before routing as fixed wires. output_panel.frozen.json
# holds it in the POST-growth frame, which is why it is added down here, after the
# re-centring pass, and not in BOARD_NOTES above.
# ⚠ IT IS A SNAPSHOT. If J1, J2, U1 or U4 moves, the copper no longer meets its pads:
# re-extract it with elec/freeze_pairs.py from a board that passes verify.py (see
# docs/bronner-work-items.md) rather than editing the json by hand.
import json as _json
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_panel.frozen.json"), encoding="utf-8") as _fh:
    _frozen = _json.load(_fh)
# HUB_DN1 (U4 -> U1) is no longer in the snapshot's care: U1 turned (see its placement) and
# the pair is drawn by hand below, 5 mm long, where the lifted copy wandered over two
# layers to reach pins on the far side of the package.
_frozen["tracks"] = [_t for _t in _frozen["tracks"] if not _t[0].startswith("HUB_DN1")]
_frozen["vias"] = [_v for _v in _frozen["vias"] if not _v[0].startswith("HUB_DN1")]
BOARD_NOTES["frozen_nets"] = list(_frozen["nets"])
BOARD_NOTES["tracks"] = list(BOARD_NOTES.get("tracks", [])) + [
    (_n, _layer, _w, [tuple(_p) for _p in _pts]) for _n, _layer, _w, _pts in _frozen["tracks"]]
BOARD_NOTES["vias"] = list(BOARD_NOTES["vias"]) + [tuple(_v) for _v in _frozen["vias"]]

# ── THE 24 V POWER PATH, DECLARED AND SIZED (2026-10-01) ─────────────────────────────────
# The supply is 6.67 A now (GST160A24-R7B) and everything it delivers crosses this board:
# in at J6, out at J7 (the motor trunk's head), J10 (feed 2: the motor controller, the Pi
# and the lights) and J9 (the optical board, 0.12 A). Until today that path was 0.5 mm of
# netclass and post-route repair -- 1.45 A at a 10 C rise, flagged above as "an improvement
# and not the fix". This is the fix: 2.0 mm (3.95 A at 10 C, about 5.5 A at 20 C) on every
# leg that carries a trunk.
#
# THE RAILS TAKE A LAYER EACH UNDER THE CONNECTOR ROW, which is the way out of the trap the
# net_widths note describes: J7 and J10 are wired PWR_GND, +24V, +24V, PWR_GND, so two lanes
# on ONE layer cannot both tap down. +24V runs on B.Cu, PWR_GND on F.Cu, both along
# y -31 -- 1.0 below the pad row and 1.0 off the board edge -- and every pad is
# through-hole, so each lane reaches its own pads with a plain stub and no via.
#
# J6 is the Kycon 4-pin jack: +24V_IN on pins 2 and 4, the column on the J10 side, and
# PWR_GND on pins 1 and 3, the column on the lane's side (the pinout note is at j6).
# ⚠ J10's +24V PADS ARE 2 AND 3, NOT PAD 1 -- pad 1 is PWR_GND.
# Authored in the PRE-growth frame like the placements, shifted here like the repairs.
_g = GROW_X / 2.0
_p1, _p2 = (24.250, J6_Y - 2.9), (24.250, J6_Y + 2.9)
_p3, _p4 = (27.900, J6_Y - 2.5), (27.900, J6_Y + 2.5)
_LANE_Y, _ROW_Y = -31.0, -28.0
# ⚠ RE-LAID 2026-10-04 FOR THE POWER SWITCH. The inlet no longer feeds the lanes directly:
#   +24V_IN  pin 4 joined straight to pin 2, then from pin 2 down the channel between
#            the pin rows and out of its west end into Q2's source lead.
#   +24V     starts at Q2's TAB. West along the lane on F.Cu -- the tab is on F.Cu, so the
#            trunk head (J7) gets there with no via -- and to J10 on B.Cu: four vias in the
#            tab (0.8 mm3 of barrel in a land printed with 4.5), east under Q2's leads at
#            y -27.4, north at x 19.9, and along under J10's row.
#   PWR_GND  therefore swaps layer east of J7: B.Cu along the lane from the inlet's pin 3,
#            under Q2, to x 6.0 -- just east of J7's row. West of J7 it stays on F.Cu,
#            where every ground pad of the buck's corner drops onto it. The two halves
#            join through J7's through-hole pad 1: the B.Cu half turns north at x 6.0,
#            passes over the top of the row at y -25.6 and comes down into pad 1.
#            (Until 2026-10-04 it went through pad 4 as well; ways 3 and 4 are empty now.)
#   J10's return (2026-10-06) leaves pin 3 on F.Cu, passes between the jack's two pegs,
#            through the shield tab's land and north along x 33.75 into J10's way 1.
_QS = (19.90, -26.22)          # Q2 source pad;  tab spans x 10.40..16.80, y -31.4..-25.6
# ways 1..6 with the part turned 180: GND, 24 V, switch, switch, 24 V, GND
_J10_PADS = (33.45, 30.95, 28.45, 25.95, 23.45, 20.95)
# EIGHT 0.3 mm VIAS, TWO IN EACH OF THE TAB'S FOUR PASTE WINDOWS (2026-10-04). They were
# four 0.4 mm ones in the two northern windows: 0.40 mm3 of barrel under 1.01 mm3 of paste,
# enough to starve the joint that carries the whole supply (quality A12). Two 0.3 mm
# barrels take 0.23 mm3, under a quarter of what each window prints, and eight of them
# carry more than the four did.
BOARD_NOTES["vias"] = list(BOARD_NOTES["vias"]) + [
    ("+24V", _x + _g, _y, 0.3, 0.6) for _y in (-27.5, -29.2)
    for _x in (11.3, 12.6, 14.6, 15.9)]
BOARD_NOTES["tracks"] += [
    (_n, _l, _w, [(_x + _g, _y) for _x, _y in _pts]) for _n, _l, _w, _pts in [
        # +24V_IN: pin 4 -> pin 2; pin 2 -> Q2 source
        ("+24V_IN", "F.Cu", 2.0, [_p4, _p2]),
        # 4.2 mm: the one stretch that carries the whole 6.67 A (4.12 mm for a 10 C rise).
        # It leaves the channel between the pin rows by its west mouth, between C31 and
        # FB1 on one side and pin 1's land on the other, 0.33 mm clear of each.
        ("+24V_IN", "F.Cu", 4.2, [_p2, (24.050, -22.200), (20.850, -23.500),
                                  (20.150, -25.400), _QS]),
        # +24V on F.Cu: the tab -> the lane -> J7 pad 2
        ("+24V", "F.Cu", 2.0, [(11.5, _LANE_Y), (-1.250, _LANE_Y)]),
        ("+24V", "F.Cu", 1.4, [(-1.250, _ROW_Y), (-1.250, _LANE_Y)]),
        # (the buck's feed leaves J7 pad 2 on B.Cu, in the buck's-corner block below)
        ("+24V", "B.Cu", 1.4, [(-1.250, _ROW_Y), (-1.250, _LANE_Y)]),
        # +24V on B.Cu: the tab's vias -> east -> north -> under J10 -> pads 2 and 3
        # ⚠ x 19.9, NOT 21.2: the inlet's rear shell legs are through-hole lands on PWR_GND
        # at x 21.30..24.50 (y -15.2 and -30.8), and a through-hole land is on EVERY layer.
        # At 21.2 this bar ran straight through the north one.
        # (2.6 mm under the tab, to take both rows of vias; 0.35 mm above the PWR_GND lane)
        ("+24V", "B.Cu", 2.6, [(11.3, -28.35), (19.9, -28.35)]),
        ("+24V", "B.Cu", 2.0, [(19.9, -28.35), (19.9, -12.9), (20.9, -11.9),
                               (_J10_PADS[1], -11.9)]),
        ("+24V", "B.Cu", 1.2, [(_J10_PADS[1], -11.9), (_J10_PADS[1], _J10_Y)]),
        ("+24V", "B.Cu", 1.2, [(_J10_PADS[4], -11.9), (_J10_PADS[4], _J10_Y)]),
        # PWR_GND on B.Cu: the inlet's pin 3 -> the lane -> x 6.0, 0.65 mm east of J7's
        # empty way 4 ...
        ("PWR_GND", "B.Cu", 2.0, [(6.000, _LANE_Y), (_p3[0], _LANE_Y), _p3]),
        # ...north past the row, west over the top of it, and down into pad 1
        ("PWR_GND", "B.Cu", 1.5, [(6.000, _LANE_Y), (6.000, -25.6), (-3.750, -25.6),
                                  (-3.750, _ROW_Y)]),
        ("PWR_GND", "F.Cu", 1.2, [(-3.750, _ROW_Y), (-3.750, _LANE_Y)]),
        # PWR_GND: pin 1 -> pin 3 on B.Cu
        ("PWR_GND", "B.Cu", 2.0, [_p1, _p3]),
        # J10's return on F.Cu: pin 3, between the pegs (3.3 mm of board between two
        # 1.7 mm holes), through the shield tab's land, north past the front shell leg's
        # land (same net) and into way 1
        ("PWR_GND", "F.Cu", 2.0, [_p3, (30.400, -23.000), (33.750, -23.000),
                                  (33.750, -11.000)]),
        ("PWR_GND", "F.Cu", 1.5, [(33.750, -11.000), (_J10_PADS[0], -10.700),
                                  (_J10_PADS[0], _J10_Y)]),
        # ...and on from way 1 to way 6 round the NORTH of the row, 1.0 mm (half the
        # return, 1.9 A). Not along the south: C28's ground via has exactly one site, 1.3 mm
        # west of way 6 and below it, and a leg coming in under the row closes it.
        ("PWR_GND", "F.Cu", 1.0, [(_J10_PADS[0], _J10_Y), (_J10_PADS[0], -6.9),
                                  (_J10_PADS[5], -6.9), (_J10_PADS[5], _J10_Y)]),
    ]]

# ── THE BUCK'S CORNER, DECLARED TOO (2026-10-01) ─────────────────────────────────────────
# Three things were wrong west of J7, all found by tracing the 0.2 mm tracks the retry laid:
#   * D6, THE SURGE DIODE, hung off 14 mm of 0.2 mm track. A clamp is only as good as the
#     copper to it: it is on 1.0 mm now, straight off J7's +24V pins and the PWR_GND lane.
#   * THE BUCK'S HOT LOOP (C2 -> U5 -> SW -> D1 -> C2) returned from D1 through ten vias,
#     hopping F.Cu / In2 at 0.2 mm -- the "worst switcher loop in the fleet" the J6/J7 note
#     records. D1's anode now goes to C2's ground pad on 0.8 mm of F.Cu, 6 mm, no via.
#   * THE FEED AND RETURN were 0.2 mm where the board asks for 0.5 (`net_widths`).
# How it fits: the PWR_GND lane carries on west along the row on F.Cu, so every ground
# pad drops straight onto it; the +24V feed comes along UNDER it on B.Cu and rises through
# one via beside C2, which keeps F.Cu between D1 and C2 clear for the loop's return.
BOARD_NOTES["vias"] = list(BOARD_NOTES["vias"]) + [("+24V", -25.925 + _g, -26.600)]
BOARD_NOTES["tracks"] += [
    (_n, _l, _w, [(_x + _g, _y) for _x, _y in _pts]) for _n, _l, _w, _pts in [
        # D6: +24V over the top of J7's pad 1, PWR_GND straight down to the lane
        ("+24V", "F.Cu", 1.0, [(-1.250, _ROW_Y), (-1.250, -26.200), (-14.000, -26.200),
                               (-14.000, _ROW_Y)]),
        ("PWR_GND", "F.Cu", 1.2, [(-10.000, _ROW_Y), (-10.000, _LANE_Y)]),
        # the lane, west of J7: 1.2 mm, on under the buck cell to C5's ground pad. Pin 2
        # reaches it under the package; C2's ground pad shares D1's drop to it
        ("PWR_GND", "F.Cu", 1.2, [(-3.750, _LANE_Y), (-34.950, _LANE_Y)]),
        ("PWR_GND", "F.Cu", 0.4, [(-30.000, _LANE_Y), (-30.000, _ROW_Y), (-31.140, _ROW_Y)]),
        ("PWR_GND", "F.Cu", 0.4, [(-27.300, -28.960), (-27.300, _LANE_Y)]),         # C3
        ("PWR_GND", "F.Cu", 0.4, [(-33.610, -28.950), (-33.610, _LANE_Y)]),         # R12
        ("PWR_GND", "F.Cu", 0.5, [(-34.950, -25.000), (-34.950, _LANE_Y)]),         # C5
        ("PWR_GND", "F.Cu", 0.5, [(-34.950, _LANE_Y), (-35.800, _LANE_Y),
                                  (-35.800, -29.000)]),                             # R60
        # the buck's feed: B.Cu under the lane -> a via under D1 -> C2 -> C3 -> U5 pin 5
        ("+24V", "B.Cu", 0.8, [(-1.250, _LANE_Y), (-25.925, _LANE_Y), (-25.925, -26.600)]),
        ("+24V", "F.Cu", 0.6, [(-25.925, -26.600), (-25.925, _ROW_Y)]),
        ("+24V", "F.Cu", 0.5, [(-25.925, _ROW_Y), (-28.860, _ROW_Y)]),
        # the hot loop's return: D1 anode straight down to the lane, through C2's
        # ground pad on the way
        ("PWR_GND", "F.Cu", 0.8, [(-23.850, -25.600), (-23.850, _LANE_Y)]),
        ("PWR_GND", "F.Cu", 0.8, [(-22.975, _ROW_Y), (-23.850, _ROW_Y)]),
        # the switch node: pin 6 up to the inductor, a spur to the diode, one to C4
        ("SW", "F.Cu", 0.5, [(-28.862, -27.050), (-28.862, -24.300)]),
        ("SW", "F.Cu", 0.5, [(-28.862, -25.600), (-27.150, -25.600)]),
        ("SW", "F.Cu", 0.3, [(-29.520, -25.700), (-28.862, -25.700)]),
        ("BOOT", "F.Cu", 0.25, [(-30.480, -25.700), (-31.138, -26.360), (-31.138, -27.050)]),
        # feedback: the pin, R12's pad, R11's pad
        ("FB", "F.Cu", 0.25, [(-31.138, -28.950), (-32.590, -28.950), (-32.590, -27.850)]),
        # the output: inductor to C5, and the divider senses AT the capacitor
        ("V5_PRE", "F.Cu", 0.5, [(-31.000, -24.300), (-31.700, -25.000), (-33.050, -25.000)]),
        ("V5_PRE", "F.Cu", 0.25, [(-33.050, -25.000), (-33.610, -25.560), (-33.610, -27.850)]),
        # C6's return (the second output capacitor, at the bead): west above the gate
        # parts and down through a via onto the B.Cu return where it turns over J7's row
        ("PWR_GND", "F.Cu", 0.6, [(13.950, -23.500), (13.950, -24.700), (6.900, -24.700),
                                  (6.000, -25.600)]),
    ]]
BOARD_NOTES["vias"] = list(BOARD_NOTES["vias"]) + [("PWR_GND", 6.000 + _g, -25.600)]




# ── HUB_DN1, DRAWN (2026-10-04) ──────────────────────────────────────────────────────────
# U4.11/12 face east at U1.61/62 across 3.8 mm, and the two ends disagree about which
# conductor is north: DM is the southern pin at the hub and the northern one at the MCU.
# No rotation of either part changes that (turning a pair never swaps it), so ONE crossover
# is intrinsic. DP takes it: down to B.Cu, under DM, and up again beside its pin. DM stays
# on F.Cu the whole way. Both leave the hub north-east, over the DN2 pair's two vias
# (0.57 and 0.75 mm from their centres), and run east below C52's pad.
# The snapshot this replaces put two vias in EACH conductor and 8 mm on two layers.
BOARD_NOTES["vias"] = list(BOARD_NOTES["vias"]) + [
    ("HUB_DN1_DP", -10.55 + _g, -5.80), ("HUB_DN1_DP", -10.75 + _g, -8.60)]
BOARD_NOTES["tracks"] += [
    (_n, _l, _w, [(_x + _g, _y) for _x, _y in _pts]) for _n, _l, _w, _pts in [
        ("HUB_DN1_DM", "F.Cu", 0.2, [(-13.562, -7.25), (-13.00, -7.25), (-12.05, -6.30),
                                     (-11.00, -6.30), (-10.20, -7.10), (-10.20, -8.00),
                                     (-9.80, -8.40), (-8.938, -8.40)]),
        ("HUB_DN1_DP", "F.Cu", 0.2, [(-13.562, -6.75), (-13.00, -6.75), (-12.05, -5.80),
                                     (-10.55, -5.80)]),
        ("HUB_DN1_DP", "B.Cu", 0.2, [(-10.55, -5.80), (-10.55, -8.40), (-10.75, -8.60)]),
        ("HUB_DN1_DP", "F.Cu", 0.2, [(-10.75, -8.60), (-10.55, -8.80), (-8.938, -8.80)]),
    ]]


# ── THE QUALITY RECORD (cadkit/PCB_QUALITY.md) ───────────────────────────────────────────
# -- I2S3'S CK AND SD LEAVE U1 INWARD (2026-10-04) --
# Pins 58 and 60 face west, 0.4 mm apart either side of an unused pin and directly above
# the hub pair's two (61, 62). The pair's hand-drawn DM runs north past them 0.75 mm off
# the pad ends, so there is no room for a via on that side and no way round on F.Cu.
# Each gets a via between the pad row and the exposed pad, the exit the old pin-37 escape
# used on the north row: 0.88 mm in from the pad centre, 0.16 off the pad's copper.
BOARD_NOTES["vias"] = list(BOARD_NOTES["vias"]) + [
    ("I2S_CK", -8.058 + _g, -7.20), ("I2S_SDI", -8.058 + _g, -8.00)]
BOARD_NOTES["tracks"] += [
    ("I2S_CK", "F.Cu", 0.15, [(-8.938 + _g, -7.20), (-8.058 + _g, -7.20)]),
    ("I2S_SDI", "F.Cu", 0.15, [(-8.938 + _g, -8.00), (-8.058 + _g, -8.00)])]

BOARD_NOTES["quality"] = {
    "power_paths": [
        # the whole supply, ahead of the switch: two jack contacts in, one FET source
        {"net": "+24V_IN", "from": "J6.2", "to": ["Q2.3"], "amps": 6.67},
        {"net": "+24V_IN", "from": "J6.4", "to": ["Q2.3"], "amps": 3.34},   # one of two contacts
        # behind the switch. J7 heads the motor trunk (bus A's east feed, 2.9 A with ten
        # movers slewing); J10 is feed 2, two contacts at 2.7 A each -- motor_ctrl's own
        # record splits that into bus A's west feed, the Pi's buck and the lights
        {"net": "+24V", "from": "Q2.2", "to": ["J7.2"], "amps": 2.9},
        # ⚠ 3.8 A, NOT THE 5.4 THAT motor_ctrl's FOUR LOADS ADD UP TO: the supply is 6.67 A
        # and bus A is fed from both ends, so with J7 carrying its 2.9 A share there is
        # 3.77 A left for this connector whatever is switched on behind it.
        {"net": "+24V", "from": "Q2.2", "to": ["J10.2", "J10.5"], "amps": 3.8},
        {"net": "+24V", "from": "Q2.2", "to": ["F1.1"], "amps": 0.12},
        {"net": "+24V_OPT", "from": "F1.2", "to": ["J9.2"], "amps": 0.12},
        {"net": "+24V", "from": "Q2.2", "to": ["U5.5"], "amps": 0.1},
        # the board's own 5 V: 257 mA worst case (the budget at U5), through the bead
        {"net": "V5_PRE", "from": "L1.2", "to": ["FB1.1"], "amps": 0.3},
        {"net": "+5V", "from": "FB1.2", "to": ["U6.1"], "amps": 0.2},
        {"net": "+5V", "from": "FB1.2", "to": ["K1.1"], "amps": 0.04},
        {"net": "+5V", "from": "FB1.2", "to": ["J4.A4", "J4.B4"], "amps": 0.1},
        {"net": "+5V", "from": "FB1.2", "to": ["U2.3", "U7.5", "U8.5", "U9.5", "U11.5",
                                               "U10.14", "U12.5"], "amps": 0.02},
        # 3V3: the hub is the big one (100 mA), then the MCU with its PHY running
        {"net": "+3V3", "from": "U6.5", "to": ["U4.19", "U4.20"], "amps": 0.1},
        {"net": "+3V3", "from": "U6.5", "to": ["U1.1", "U1.13", "U1.17", "U1.31", "U1.32",
                                               "U1.50", "U1.51", "U1.67", "U1.68"],
         "amps": 0.06},
        {"net": "+3V3", "from": "U6.5", "to": ["U3.1", "U3.8", "U3.20", "U2.4"],
         "amps": 0.03},
    ],
    "not_power": {
        "PWR_GATE": "Q2's gate: 34 uA through the 330k / 150k divider",
        "PWR_PULL": "Q3's drain to the gate divider, the same 34 uA",
        "PWR_SW_UP": "a throw of the power button: 2.55 mA at most, through R33 + R34",
        "PWR_SW_DN": "the button's other throw, as PWR_SW_UP",
    },
    "pinouts": {
        "TYPE-C-31-M-12": "KiCad's USB_C_Receptacle_HRO_TYPE-C-31-M-12 names each land by "
                          "its USB Type-C contact (A1 ... B12), the names Korean Hroparts' "
                          "drawing for the part prints beside the same lands; every net "
                          "here is attached by that name (A4/A9/B4/B9 VBUS, A5/B5 CC, "
                          "A6/B6 D+, A7/B7 D-, A1/A12/B1/B12 GND). Checked 2026-10-04",
        "B6B-XH-A": "JST eXH.pdf p.5, Header / Top entry type: seen from the slotted wall, "
                    "No. 1 circuit is the right-hand post; KiCad's footprint has that wall "
                    "at -Y and pad 1 at -X. Way names are harness.PWR_LINK, the list "
                    "motor_ctrl J3 is built from. Read 2026-10-04",
        "B4B-XH-A": "the same JST drawing and KiCad family as the 6-way (eXH.pdf p.5). "
                    "J7: 1 PWR_GND, 2 +24V, 3 and 4 empty -- the instrument's order "
                    "(harness.py) with no data ways used",
        "NMJ6HCD2": "Neutrik NMJ6HCD2 drawing: T / R / S contacts and their normalling "
                    "contacts TN / RN / SN. KiCad's Jack_6.35mm_Neutrik_NMJ6HCD2 names the "
                    "lands by those letters and was checked pad by pad against the "
                    "drawing, 2026-09-30 (note at TRS_FP). Board: T tip, R ring, S sleeve "
                    "to GND, normals grounded or open as the jack section says",
        "KPJX-4S-S": "Kycon KPJX-4S-S land pattern (footprint Steel:Kycon_KPJX-4S-S was "
                     "drawn from it); the rails are Mean Well's GST160A-SPEC (2026-04-03) "
                     "for the R7B plug: 1 +V, 2 -V, 3 -V, 4 +V, shell to -V, in MEAN WELL'S "
                     "numbering, whose 1 and 2 are Kycon's 2 and 1 (both plug-face "
                     "drawings read 2026-10-06). Board, Kycon's numbers: 2 and 4 "
                     "+24V_IN, 1 and 3 PWR_GND, SH PWR_GND. The plug is metered before "
                     "first power (docs/board-bringup-diagnostics.md)",
        "THROW": "KiCad SolderJumper-3 bridged 1-2: pad 2 is the common. Board: 1 "
                 "PWR_SW_UP, 2 SW_SENSE, 3 PWR_SW_DN",
        "G6K-2F-Y-DC5": "Omron G6K-2F-Y datasheet p.6 (p. B-83 in the catalogue), terminal "
                        "arrangement, top view: coil 1 (+) / 8 (-); pole A COM 3, NC 2, "
                        "NO 4; pole B COM 6, NC 7, NO 5. Read 2026-09-30, re-read the "
                        "same day against the netlist contact for contact",
        "AO3400A": "AOS AO3400A datasheet rev 3 p.1, package drawing: 1 G, 2 S, 3 D. Read "
                   "2026-09-30",
        "SQD50P06-15L": "Vishay 69098 rev. E p.1: TO-252, seen from above with the leads "
                        "down, G left / D tab / S right = KiCad TO-252-2 pads 1 G, 2 D, "
                        "3 S. Read 2026-10-04",
        "2N7002": "CJ 2N7002 datasheet p.1 (LCSC C8545), marking diagram: 1 G, 2 S, 3 D",
        "CH32V307WCU6": "WCH CH32V303/305/307/317 datasheet V3.4 p.21, the CH32V307WCU6 "
                        "pin drawing, and V3.8 Table 3-1 QFN68 column (2026-09-21): 1 VBAT, "
                        "5 OSC_IN, 6 OSC_OUT, 7 NRST, 12 VSSA, 13 VDDA, 17/31/51/67 VIO, "
                        "18/49 VSS, 32/50/68 VDD, 25 PC5, 26 PB0, 27 PB1, 35 PB12, 36 PB13, "
                        "38 PB15, 39 PC6, 48 PA13/SWDIO, 52 PA14/SWCLK, 53 PA15, 58 PB3, 60 PB5, 61 PB6 = "
                        "USBHS_DM, 62 PB7 = USBHS_DP, 63 BOOT0, 64 PB8, 65 PB9, pad VSS",
        "MCP4261-103E/ST": "Microchip DS22059 Table 3-1, 14-lead column: 1 CS, 2 SCK, "
                           "3 SDI, 4 VSS, 5 P1B, 6 P1W, 7 P1A, 8 P0A, 9 P0W, 10 P0B, 11 WP, "
                           "12 SHDN, 13 SDO, 14 VDD. Read 2026-09-30 and confirmed from a "
                           "second source (note at U10)",
        "TLV9061IDBVR": "TI SBOS839N Table 5-1, SOT-23 (DBV) column: 1 OUT, 2 V-, 3 IN+, "
                        "4 IN-, 5 V+. Read 2026-09-30",
        "TS5A3159DCKR": "TI SCDS174 p.3 Pin Functions (DBV and DCK): 1 NO, 2 GND, 3 NC, "
                        "4 COM, 5 V+, 6 IN; IN low joins COM to NC. Board: 1 RING_GAIN "
                        "(stereo), 2 GND, 3 INV_OUT (balanced), 4 the ring buffer's "
                        "input, 5 +5V, 6 JACK_MODE. Read 2026-10-04",
        "PCM1808PWR": "TI SLES177B Pin Functions: 1 VREF, 2 AGND, 3 VCC, 4 VDD, 5 DGND, "
                      "6 SCKI, 7 LRCK, 8 BCK, 9 DOUT, 10 MD0, 11 MD1, 12 FMT, 13 VINL, "
                      "14 VINR. Read 2026-09-21, re-read 2026-09-30, all 14",
        "PCM5102APWR": "TI SLAS859C Pin Functions: 1 CPVDD, 2 CAPP, 3 CPGND, 4 CAPM, "
                       "5 VNEG, 6 OUTL, 7 OUTR, 8 AVDD, 9 AGND, 10 DEMP, 11 FLT, 12 SCK, "
                       "13 BCK, 14 DIN, 15 LRCK, 16 FMT, 17 XSMT, 18 LDOO, 19 DGND, "
                       "20 DVDD. Read 2026-09-21, re-read 2026-09-30, all 20",
        "CH334F": "WCH CH334 datasheet V2.5 Table 1-3, the 4F column, re-read against "
                  "V2.91 2026-09-30: 1 OVCUR#, 3 XO, 4 XI, 9 DM2, 10 DP2, 11 DM1, 12 DP1, "
                  "14 DMU, 15 DPU, 16 RESET#, 19 V5, 20 VDD33, EP GND (the figure's "
                  "package labels are offset by one block: the table is the source)",
        "LMR16006XDDCR": "TI SNVSA24 section 6, Pin Functions (SOT-23-6): 1 CB, 2 GND, "
                         "3 FB, 4 SHDN, 5 VIN, 6 SW. Re-read 2026-10-04",
        "AP2112K-3.3TRG1": "Diodes DS39724 rev. 2-2 p.1 Pin Assignments and p.2 Pin "
                           "Descriptions, SOT25: 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT. Board: "
                           "1 and 3 +5V, 2 GND, 4 alone, 5 +3V3. Read 2026-10-04",
        "TAXM8M4RFDCET2T": "Yajingxin TAXM8M4RFDCET2T sheet (LCSC C403948): lands 1 and 3 "
                           "are the crystal, 2 and 4 the can. Board: 1 OSC_IN, 3 OSC_OUT, "
                           "2 / 4 GND. Read 2026-10-04",
        "TAXM12M4RFBCCT2T": "the same maker's 3225 four-land outline as Y1 (LCSC C133337): "
                            "1 and 3 the crystal, 2 and 4 the can. Board: 1 HUB_XI, "
                            "3 HUB_XO, 2 / 4 GND",
        "PNR3015-150M": "two-pad, unpolarised",
    },
    "waive": {
        # A1 reports one barrel and does not add parallel vias up. The tab has eight.
        "A1:+24V Q2.2>J10.2": "eight 0.3 mm vias join the tab to the B.Cu bar, two in each "
                              "paste window: 8 x 0.67 mm of equivalent barrel = 5.4 mm "
                              "against 2.0 mm for 3.8 A, and 4.12 mm if the whole supply "
                              "went this way; any four carry it",
        "A1:+24V Q2.2>J10.5": "as J10.2: the same eight vias",
        "A6:J2.A5": "J2 is not a port: it is the far end of a wire from J1 to the Pi's "
                    "gadget socket, with VBUS dead-ended on purpose (the note at J2). "
                    "Nothing behind it sources or sinks, so there is no VBUS for a CC "
                    "resistor to ask for; the player's computer sees J1's two pull-downs",
        "A6:J2.B5": "as J2.A5",
    },
    # The manual review, 2026-10-04. Each entry is the evidence, not a tick. Left OPEN on
    # purpose: M32 (the split of the trunk current between J7 and J10 rests on an
    # unmeasured motor current), M11 (CAD fit after the build), M35 (errata) and the
    # order-time items M12, M29, M30, M37, M42.
    "manual": {
        "M35": "read 2026-10-05. " + 'WCH publishes no errata sheet: its product page lists the datasheet and the reference manual (CH32FV2x_V3xRM) and nothing else, read 2026-10-05. ' + "The CH334F hub "
               "has a datasheet only (its product page was not found under that name). "
               "The USB chapter of the manual was read for motor_ctrl's M23 and holds "
               "here too",
        "M3": "24 V: in on J6's two +V contacts and back on its two -V contacts, out and "
              "back on J7 / J10 / J9, each pair side by side; measured on the routed "
              "board 2026-10-06, after the inlet's nets were corrected (track copper "
              "only, 1 oz): from J6's -V contacts the return is 12.5 mohm to J7, "
              "narrowest copper 1.5 mm; 4.1 mohm to J10's way 1 (1.5 mm) and 7.9 to "
              "its way 6 (1.0 mm, round the north of the row). The feed from the +V "
              "contacts to Q2 is 1.0 mohm, narrowest 4.2 mm. 5 V: the buck's output returns through R60 "
              "(0 ohm, the one join of PWR_GND and GND, beside C5), 0.5 mm from the lane "
              "to its pad; every load is on the GND planes (In1 whole, B.Cu) under its "
              "supply track. Before R60 that current left the board by a USB ground. "
              "C55, the inlet's 100 nF, is on 0.5 mm track from pin 2 (8.9 mm) and returns "
              "by 5.4 mm of 0.38 to 0.5 mm track to the jack's front north shell leg; a "
              "bypass ahead of the switch, carrying no load current",
        "M21": "one ground plane under the converters, joined to the power return at ONE "
               "point (R60, at x -36.6, y -29, the board's -X / -Y corner). What crosses "
               "the plane besides the board's own return: the share of the motors' "
               "return that comes back along the USB grounds instead of the trunk, about "
               "a tenth by conductor resistance, entering at J2 / J3 / J4 on the -X edge "
               "(x -42) and leaving at R60 on the same edge. The pickup terminals, their "
               "buffer and the ADC are at x -13 to +3, y +28, and the DAC and output "
               "stage at x +2 to +16: none lies between the sockets and R60, and each "
               "takes its reference from the plane under itself. The ADC's and DAC's "
               "analog supply pins are bypassed to that plane at the pins (A2). If motor "
               "noise is ever heard, R60 becomes a bead; that is why it is an 0603",
        "M1": "J6: Mean Well's R7B plug, 1 +V, 2 -V, 3 -V, 4 +V (GST160A-SPEC) in its own "
              "numbering = Kycon pins 2 and 4 +V, 1 and 3 -V, on a jack whose "
              "footprint was drawn from Kycon's land pattern; metered before first power (bring-up "
              "step 0). J10 <-> motor_ctrl J3: harness.PWR_LINK (GND, 24, SW_UP, SW_DN, 24, GND), a "
              "6-way straight lead, both ends built from that list. J7 -> the trunk's far end: GND, "
              "24, and two empty ways. J9 -> the optical board: 2-way here, 1 GND, 2 +24V_OPT; the "
              "optical board's J2 is a 4-way housing with ways 1 and 2 crimped in the same order "
              "(JST makes no 2-way SMT side-entry XH; the note at that J2). J1 / J2 / J3 / J4 are "
              "USB-C receptacles on stock C-to-C leads with D+ / D- tied across both rows. J8: two "
              "screw terminals, hot and ground, marked on the silk. J5: tip / ring / sleeve. The "
              "6-way cannot enter a 4-way or a 2-way",
        "M2": "D1 (B5819W) pad 1 = K on SW, anode on PWR_GND. D4 (1N4148WT) pad 1 = K on "
              "+5V, anode on RELAY_COIL: it conducts the coil's turn-off current back to "
              "the rail (it was fitted the other way round until this review). D6 "
              "(SMAJ30A) pad 1 = K on +24V. D8 (BZT52C10) pad 1 = K on SW_SENSE. D2 / D3 / "
              "D5 / D7 are bidirectional. No electrolytic or tantalum part",
        "M4": "U5 (LMR16006, SNVSA24): CIN 10 uF / 50 V 1206 + 100 nF / 50 V at the pin "
              "(asks 1-10 uF); COUT 2 x 22 uF / 16 V 0805, about 2 x 9 uF at 5 V of "
              "bias (asks 4.7-100 uF, ESR under 0.7 ohm); bootstrap 100 nF. U6 (AP2112K): 1 uF at IN "
              "(C58), 10 uF at OUT (C9) with the rail's other capacitors. Every capacitor "
              "on a 24 V net is a 50 V part; C1 / C41 at the jack are 100 V against 48 V "
              "phantom power; C48 on Q2's gate is 25 V against 7.5 V",
        "M5": "+24V_IN and +24V: Q2 60 V, U5 60 V operating, capacitors 50 V, F1 63 V, "
              "D6 stands off 30 V and breaks down at 33-37 V. Q2's gate sees 7.5 V of its "
              "20 V; Q3's sees 10 V (D8) of its 20 V. R33 / R34 dissipate 31 mW each "
              "with the switch held off, in 0402 parts rated 62 mW. 5 V rail: 16 V "
              "capacitors, op-amps and switch 5.5 V, the pot 5.5 V. 3V3: the DAC (3.9 V "
              "absolute) is on 3V3, not 5 V. Jack: 100 V blocking capacitors, then 220 "
              "ohm and a 5 V clamp ahead of each buffer",
        "M6": "USB 2.0 high speed on four pairs, each a declared diff pair over the In1 "
              "plane, matched (verify: 4 groups, 0 problems). HUB_DN1 crosses once, on "
              "B.Cu, by construction (the note beside its tracks). I2S is 12.288 MHz MCK "
              "and 3 MHz BCK over 20-30 mm: not a length-matched bus",
        "M7": "U5: 0.765 V x (1 + 100k / 18.2k) = 4.97 V; 15 uH at 700 kHz gives 0.38 A of ripple, "
              "63 % of the IC's 0.6 A against the 30 to 40 % the sheet suggests (the smaller value "
              "is for saturation, M14); bootstrap 100 nF (the sheet's value; it was 10 nF); SHDN "
              "open = enabled; catch diode 40 V / 1 A. U6: EN tied to IN. U2 (PCM1808): MD0 = MD1 = "
              "0, slave; FMT = 0, I2S; SCKI from the MCU's MCK at 256 fS. U3 (PCM5102A): FMT = 0 "
              "I2S, DEMP = 0, FLT = 0, XSMT high, charge-pump and LDO capacitors at the sheet's "
              "values. U4 (CH334F): V5 tied to VDD33 for 3.3 V supply, as WCH allows; 12 MHz "
              "crystal; unused ports open. U10 (MCP4261): WP and SHDN high. U12 (TS5A3159): IN from "
              "the MCU, COM to the ring buffer",
        "M8": "BOOT0: R7, 10 k to GND. NRST: R6 10 k to 3V3 and C54. Relay gate: R36, "
              "100 k to GND, so the relay is released (the direct, unprocessed path) "
              "while the MCU is in reset. JACK_MODE: R37, 100 k to GND, so the ring is "
              "the balanced inverse in reset. Hub: OVCUR# pulled high by R19; RESET#, "
              "PSELF and PGANG on WCH's internal pulls. U5 SHDN: open = on. Q3's gate: "
              "pulled up to 10 V from the inlet (R33 / R34 / D8) with no cable fitted, "
              "so the instrument is ON with the switch lead missing",
        "M9": "SWD on bare 1.5 mm pads TP1 SWDIO, TP2 SWCLK, TP3 NRST, TP4 GND, TP5 3V3, "
              "all named in silk. 24 V is probed on J7's through-hole pins, 5 V on J4's "
              "VBUS pins or K1 pin 1. The MCU is also reachable over USB through the hub",
        "M11": "finish.py's CAD check: 138 of 138 routed parts present in the CAD, "
               "every one where the CAD draws it. The lead's full build on main "
               "45eeb5b8 (2026-10-06) with this board's geometry: 1010 components, 0 "
               "unintended overlaps, the rotating-part sweep clean -- the board, its "
               "parts at their drawn heights, its mated plugs and its cables against "
               "the plastic and the fasteners round it. One M4 through the ear at its "
               "-X / -Y corner: a 4.5 mm cut in bare laminate outside the pours, so "
               "nothing is under the head. The ten unplated holes are the connectors' "
               "own locating pegs. Parts the fab cannot place: none (M30 is the tier)",
        "M10": "the jack (the one connector a player handles): 100 V capacitor, 220 ohm "
               "and a bidirectional 5 V clamp per conductor, proof against 48 V phantom "
               "power. The panel USB-C (J1): D2 / D3 on the pair, 8.6 and 10.5 mm along "
               "it with nothing between them and the connector. J3 / J4 / J2 are leads "
               "inside the instrument to our own boards: no clamps, by decision. J8 is a "
               "screw terminal inside the enclosure, hand-wired to the pickup: no clamp. "
               "24 V inlet: D6, and the supply's own limit; reverse polarity is prevented "
               "by the keyed 4-pin plug and the meter check (M1)",
        "M13": "U5, measured pad to pad on the routed board. C3 (100 nF) 0.6 mm from VIN "
               "and C2 (10 uF) 1.7 mm, both on one F.Cu rail; pin 2's ground leaves "
               "under the package straight to the ground lane, so the loop C3 -> VIN .. "
               "SW -> D1 -> lane -> pin 2 is about 7 mm of F.Cu with no via. D1's "
               "cathode 0.8 mm from SW. L1's SW pad 2.1 mm from the pin; the SW copper "
               "is three short declared tracks. C4 0.75 mm from CB and from SW. R12 / "
               "R11 0.5 and 0.7 mm from FB, the node 2.6 mm of track, sensing at C5. C5 "
               "1.15 mm from L1's output pad; C6 stays at the bead, 45 mm on. (Before "
               "this review the same parts stood 2.4-15 mm from their pins and C5 36 mm "
               "from the inductor.)",
        "M14": "L1 PNR3015-150M, 15 uH: ripple 5 x (1 - 5 / 24) / (15 uH x 700 kHz) = 0.38 A, peak "
               "0.257 A worst-case load + 0.19 = 0.45 A, against 1.40 A guaranteed / 1.80 typical "
               "saturation and 1.00 / 1.20 A rms (APV, 30 % drop). TI SNVSA24 9.2.2.2 on the "
               "inductor: 'Using a rating near 1.6 A will enable the LMR16006 to current limit "
               "without saturating the inductor. This is preferable to the LMR16006 going into "
               "thermal shutdown mode and the possibility of damaging the inductor if the output is "
               "shorted' -- advice, against a limit of 1.2 A typical / 1.7 max. So the guaranteed "
               "figure clears the typical limit and the typical one the maximum; in a held short "
               "the IC limits near 1.2 A, at about the part's rms rating, and its thermal cut-out "
               "cycles it. Shielded, beside a magnetic pickup's preamp",
        "M15": "U5 is internally compensated for ceramic output capacitors of 10 uF and "
               "up: about 18 uF effective fitted. U6 (AP2112K) is ceramic-stable from "
               "1 uF: 10 uF at its output. Headroom: 4.97 V less 40 mV in the bead "
               "against 3.3 V + 0.25 V. It dissipates 1.67 V x 0.18 A = 0.3 W worst "
               "case (0.18 W typical) in a SOT-23-5: about 70 C of rise at the worst",
        "M16": "the inlet is hot-plugged by design. Ahead of the switch there is only "
               "C55 (100 nF / 50 V), Q2 (60 V) and the sense divider; a ring to 48 V is "
               "inside all three. Behind it the rail is raised by Q2 at about 2 V/ms "
               "(C49 across gate and drain, 44 uA into it), so nothing downstream sees "
               "an edge: about 2 A of inrush per 1000 uF on the trunk. J9 / J7 / J10 are "
               "plugged with the supply off",
        "M17": "FB1 BLM18KG601SN1D: 600 ohm at 100 MHz, 150 mohm, rated 1.3 A against "
               "0.26 A (the 200 mA part it replaces was past its rating). Between 18 uF "
               "on one side and 10 uF + the rail's bypass on the other, with 150 mohm in "
               "series, the pair is damped (Q about 0.9)",
        "M18": "the board's 3V3 and 5 V rise together from one buck. The Pi and the "
               "optical board are powered separately, and what joins them to this board "
               "is USB (pairs through the hub, which is built for it) -- VBUS from the "
               "panel and from the Pi is dead-ended here on purpose (the notes at J1 / "
               "J2 / J3), so neither can back-feed this board's 5 V. The switch lines on "
               "J10 are pulled from this board's inlet only",
        "M19": "Q2 (SQD50P06-15L): gate driven to -7.5 V by R32 / R31, 15-20 mohm there; "
               "0.76 W at the supply's full 6.67 A. Off when Q3 is off (R32 to source). "
               "Q3 (2N7002): 10 V on its gate when on. Q1 (AO3400A): 3.3 V on its gate "
               "against a 1.45 V maximum threshold, 21 mA of coil; held off in reset by "
               "R36",
        "M20": "no I2C and no CAN here. USB: CC resistors per port role (A6). I2S: the "
               "clock tracks are 20-30 mm, a small fraction of an edge's length, so no "
               "series resistors. The I2S clocks reach two MCU pins each (I2S2 out, "
               "I2S3 in) as short stubs at the package",
        "M22": "four TLV9061, all single, all used: three followers and one unity "
               "inverter about VMID (2.5 V, from R17 / R18 with C40). Inputs and "
               "outputs stay inside the 0-5 V rails by construction (rail-to-rail "
               "parts, signals biased at mid-rail). Each output drives its cable "
               "through 220 ohm, which isolates the capacitance",
        "M23": "panel port J1: clamps on the pair (M10), 5k1 on each CC, VBUS not "
               "connected. Hub (self-powered, 3.3 V): upstream on J3 with 5k1 per CC, "
               "downstream J4 with 56 k pull-ups per CC and VBUS from this board's 5 V "
               "(limited by the buck, M36), 100 nF on it at the connector (C57). The "
               "MCU hangs on hub port 1 with no connector: its high-speed PHY is "
               "internal and its speed is set in software (datasheet 2.5.22), so there "
               "is no external pull-up to fit. Port 1's pair has no via on one "
               "conductor and two on the other: recorded at the pair",
        "M24": "Y1 (8 MHz, CL 12 pF): 15 pF each side = 7.5 + about 4.5 pF of pin and "
               "track. Y2 (12 MHz, CL 12 pF): the same 15 pF (it was 12 pF, 1.5 pF "
               "light, from before the crystal was chosen)",
        "M25": "U1 and U4: exposed pads on GND with vias to the plane (A8). Q2: the tab "
               "is its drain, on eight vias to a 2.6 mm B.Cu bar and the F.Cu land: "
               "0.76 W at 6.67 A, about 0.2 W at the 3.5 A the instrument is budgeted "
               "to draw. U6: 0.3 W worst case through its leads (M15)",
        "M26": "I2S_SDO: MCU pin 38 (PB15, I2S2_SD, transmit) to the DAC's DIN. I2S_SDI: "
               "the ADC's DOUT to MCU pin 60 (PB5, I2S3_SD, receive). It used to land "
               "on PB14, which is not an I2S pin on this part. POT_SDI: MCU out to the "
               "pot's SDI; the pot's SDO is unused",
        "M27": "BOOT0: R7 only. SWDIO / SWCLK: a test pad each. NRST: R6, C54, a test "
               "pad. PA15, PB3 (I2S3) are plain GPIO at reset on this RISC-V part: SWD "
               "is two-wire, so they are not debug pins. The hub's strap pins are open",
        "M28": "CH32V307WCU6 is the QFN68 column (not the VCT6's LQFP100 numbering). "
               "TS5A3159DCKR is the SC-70 with IN on pin 6. PCM1808PWR / PCM5102APWR "
               "are the TSSOPs. AP2112K is the SOT-25. Each read against the footprint "
               "the board places (quality.pinouts)",
        "M31": "the jack, the screw terminal's hot and ground, each connector's name and "
               "the five SWD pads are in silk at 1.0 mm or more. Diode cathodes and IC "
               "pin 1 are the KiCad footprints' own marks, outside the bodies",
        "M33": "5 V: 257 mA at the doubled worst case against the buck's 600 mA (the "
               "itemised table at U5). 3V3: MCU 22 mA, ADC 19, DAC 31, hub up to 100, "
               "pulls 5: about 0.18 A through a 600 mA regulator. 24 V: this board's "
               "own draw is under 0.1 A; the rest passes through to J7 / J10 / J9 on "
               "copper checked for it (A1)",
        "M34": "MCU (3.3 V) to the 5 V pot: the MCP4261's input-high is 0.45 x VDD = "
               "2.25 V. MCU to the analog switch: the TS5A3159 needs 2.4 V at 5 V (the "
               "SN74LVC1G3157 it replaces needed 3.5 V and would not have switched). "
               "MCU to both converters: all 3.3 V. The DAC's XSMT, the ADC's mode "
               "pins: tied",
        "M36": "J9 (the optical board, a thin lead): F1, 1 A. J4's VBUS: the buck's own "
               "limit, behind a 1.3 A bead. J7 and J10 are the trunk itself: limited "
               "by the supply (6.67 A), on copper sized for all of it at the inlet and "
               "3.8 / 2.9 A at each outlet; the contact loading is M32",
        "M38": "ceramics larger than 0805 are C2 (1206, in the buck cell, lying "
               "parallel to the nearest edge) and the two 100 V jack capacitors. All "
               "connectors are on the panel edge or reachable from above",
        "M39": "MCU: unused GPIO open, set by firmware; PB14 (the old ADC data pin) is "
               "one of them now. Hub: ports 3 / 4 and the LED / strap pins open, as "
               "WCH's sheet allows. Pot: SDO open. U5 SHDN open (= on). J1 / J2 / J3 "
               "VBUS pins dead-ended on purpose",
        "M40": "the generator carries it beside each value: the feedback divider, the "
               "bead, the soft-start parts, the relay's default state, the CC "
               "resistors, the crystal capacitors, the buck cell's placement and why "
               "the ground domains are not tied here",
        "M41": "the power button is debounced by R35 / C50 (10 k x 100 nF = 1 ms) ahead "
               "of Q3, and Q2's own gate network (0.1 s) behind it. The button is a "
               "latching 2P2T rated 12 V / 0.3 A: it switches 10 V (D8) at 2.6 mA. No "
               "other contact on this board",
    },
}


if __name__ == "__main__":
    output_panel(tag="panel")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "output_panel.net"))
    # R60 joins them (2026-10-04): one group, nothing to declare.
    netcheck.grounds_meet(os.path.join(OUT_DIR, "output_panel.net"))
    netcheck.no_orphan_pins(os.path.join(OUT_DIR, "output_panel.net"))
    with open(os.path.join(OUT_DIR, "output_panel.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements, x%d per instrument"
          % (BOARD_W_GROWN, BOARD_L, len(BOARD_NOTES["placements"]),
             BOARD_NOTES["qty_per_instrument"]))
