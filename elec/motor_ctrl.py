"""Motor controller — the head of both CAN buses, x1.

    py -3.12 elec/motor_ctrl.py         # -> elec/out/motor_ctrl.{net,board.json}

ONE JOB (user): read the lever and pedal angles off bus B, apply the saved travel
offsets, and command the SERVO42Ds on bus A. Audio, pitch detection, the OLED and
the joystick all live on the Raspberry Pi; the Pi computes what the offsets should
be during tuning and writes them down here, and this board then runs without it.

IT REPLACES THREE THINGS: the Teensy 4.1 ($31.50), its SGTL5000 audio shield
($9.80) and the teensy_ifc carrier. The Teensy's value was the Audio Library, USB
high-speed and the codec -- all irrelevant once no audio touches this board. What
could NOT be deleted is the pair of CAN TRANSCEIVERS: no general-purpose MCU
integrates one, because a transceiver has to survive +-58 V bus faults and cannot
share a die with 3.3 V logic. So the board was always going to exist; the only
question was whether an MCU sat on it too.

CAPACITY, checked rather than assumed. On a pedal steel one pedal changes several
strings, so "a few controls moving" IS the ten-motor case:
    bus A, 10 motors, 8-byte frames, command + drive reply
      500 kbps @ 100 Hz -> 52%       500 kbps @ 200 Hz -> 104%  (over)
      1 Mbps   @ 200 Hz -> 52%
    bus B, 11 sensor boards, 2-byte frames @ 500 Hz
      500 kbps -> 79.2%  (OVER)      1 Mbps -> 39.6%
⚠ BUS B AT 500 kbps IS NO LONGER VIABLE, and that is a consequence of the control
count, not of the respin. This table was written for EIGHT sensor boards (57.6%);
the real count is ELEVEN -- 6 knee levers + 5 pedals -- and the load is linear in
it, so the same bus reads 79.2%. That is past the 52% target and well into the
region where low-priority frames wait on arbitration. BUS B MUST RUN AT 1 Mbps
(39.6%), or its frame rate has to come down. Nothing on the board changes for
this -- both transceivers and the MCU's controllers are good for 1 Mbps, and R5's
slope-control note already assumes short cable -- but the FIRMWARE bitrate is now
a requirement rather than a preference.
52% is the target, not 90%: CAN arbitrates by priority, so high utilisation
delays low-priority frames unpredictably -- the headroom buys latency, not just
throughput. Worth confirming the SERVO42Ds will run 1 Mbps; it doubles the margin.
The MCU is nowhere near the limit -- ~6,000 frames/s across both buses is
single-digit percent of a 144 MHz core with two HARDWARE CAN controllers.

⚠ CAN1 IS REMAPPED, AND THAT IS A LAYOUT DECISION, NOT A FIRMWARE ONE. CAN1's
default pins are PA11/PA12 -- which are also OTG_FS_DM/DP. This board needs USB
to the Pi AND both buses, so bus A's transceiver goes on CAN1's REMAP, PB8/PB9
(pins 64/65). Wire it to PA11/PA12 and no firmware setting can rescue it.

EVERY PIN NUMBER IS OFF THE DATASHEET, parsed from WCH's own QFN-68 column
(CH32V303/305/307/317 datasheet V3.9, table 3-1), not trusted to a library symbol.
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
I, O, PWR = Pin.types.INPUT, Pin.types.OUTPUT, Pin.types.PWRIN

# ⚠ THIS USED TO BE ITS OWN COPY, annotated "same order as every other board" --
# a claim with nothing checking it. It is now the same OBJECT as every other board.
XH_PINOUT = harness.XH_PINOUT
MCU_FP = "Package_DFN_QFN:QFN-68-1EP_8x8mm_P0.4mm_EP5.2x5.2mm"
XH_FP = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"


# ⚠ THE REF IS PINNED FROM THE TAG. Every call passes a tag that spells the intended
# ref, and without ref= that agreement is a COINCIDENCE of CREATION ORDER, not a
# mechanism. On lever_sensor, adding a single resistor in the middle of the file consumed
# R5 and pushed every later resistor up one -- and BOARD_NOTES["placements"] is keyed by
# ref, so parts silently referred to refs that no longer existed while a new one with no
# placement would have landed on the board ORIGIN. ERC passed and the netlist was valid.
# This board had the same latent fault; pinning the ref makes creation order irrelevant.
def _r(tag, value, desc, pkg="Resistor_SMD:R_0402_1005Metric"):
    return Part(name="R", ref_prefix="R", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=pkg,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, pkg="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=pkg,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _xh(tag, desc):
    return Part(name="B4B-XH-A", ref_prefix="J", tag=tag, ref=tag, dest="NETLIST", tool="skidl",
                value="B4B-XH-A", description=desc, footprint=XH_FP,
                pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(XH_PINOUT)])


# ⚠ BUS B'S CONNECTOR IS THE 8-WAY TRUNK PART, NOT A 4-WAY DROP (user, 2026-09-22,
# topology option B). The controller MOVED TO THE MIDDLE of bus B: the pedals arrive from
# the leg at the -X end and the lever chain arrives at -X too, so both plug into this board
# instead of one chain looping back through the body. A mid-bus node is a PASS-THROUGH by
# construction -- bus in on ways 1-4, out on 5-8 -- which is the same S8B-PH-SM4-TB, the
# same crimps and the same pin order every other bus-B node already uses (lever_sensor J1).
# It is the VERTICAL 8-way, not the sensor boards' side-entry S8B-PH-SM4-TB. The harness
# contract is identical either way -- every S8B/B8B mates the same PHR-8 housing on the same
# SPH-002T-P0.5S crimps in the same pin order -- so what the variant buys is board fit: this
# board's connectors are top-entry and mid-board (J1 is), it already had the 4-way vertical
# PH here, and the side-entry part needs a board EDGE with its mouth off it. Placed at J2's
# existing site the side-entry body took C10's stitching-via room and layout refused it.
PH_FP = "Connector_JST:JST_PH_B8B-PH-K_1x08_P2.00mm_Vertical"
# ⚠ AND THE 4-WAY SIDE-ENTRY PAIR THAT REPLACED IT (user, 2026-09-25). See _ph4.
PH4_FP = "Connector_JST:JST_PH_S4B-PH-SM4-TB_1x04-1MP_P2.00mm_Horizontal"


def _ph4(tag, desc):
    """Bus B's trunk, as TWO 4-way side-entry PH instead of one 8-way vertical.

    ⚠ THE REASON IS SERVICE, NOT ELECTRONICS (user, 2026-09-25): "instead of having an
    8 pin which is locked inaccessible inside the instrument I'd like to put two 4 pin
    JSTs on the board such that we can drop the board down z, cut a hole in the instrument
    and have access to plug (and unplug) the 4 pins in from below".

    The tray STANDS: electronics.stand() rotates it +90 deg about Y, which maps the board's
    flat +X edge to world -Z. So the flat +X edge is the one facing the instrument's
    underside, and a SIDE-ENTRY connector there -- mouth off that edge -- mates straight
    down. A vertical part on the same edge would mate along world +X, into the instrument,
    which is exactly the connector nobody can reach.

    Splitting is free electrically because bus B was ALREADY a pass-through: ways 1-4 in,
    5-8 out, the same four nets on both halves. Two 4-ways are the same two harnesses with
    the same crimps in the same order; what changes is that each can be unplugged on its
    own. The 8-way's own note argued for one part on the grounds that a mid-bus node is a
    pass-through by construction -- true, and it is why this costs nothing to undo.

    S4B-PH-SM4-TB (LCSC C265102, 28.9k in stock) is the 4-way of the S8B-PH-SM4-TB the
    eleven lever boards already use: same family, same PHR housing, same SPH-002T-P0.5S
    crimps, same pin order. 11.9 mm of board edge each.
    """
    return Part(name="S4B-PH-SM4-TB", ref_prefix="J", tag=tag, ref=tag, dest="NETLIST", tool="skidl",
                value="S4B-PH-SM4-TB", description=desc, footprint=PH4_FP,
                pins=[Pin(num=i + 1, name=n, func=P)
                      for i, n in enumerate(harness.PH_PINOUT)])


def _ph(tag, desc):
    """The LEVER bus's TRUNK connector: JST PH, 8-way, vertical top entry. Same pin ORDER as
    the XH buses (GND / +V / CAN_H / CAN_L, harness.PH_PINOUT) so one crimp order serves
    the whole harness, but a different FAMILY, so a lever harness cannot mate a 24 V XH
    header and vice versa -- and way 2 is +5 V here, which is why bus B has its own
    pinout name rather than borrowing the 24 V one."""
    return Part(name="B8B-PH-K-S", ref_prefix="J", tag=tag, ref=tag, dest="NETLIST",
                tool="skidl", value="B8B-PH-K-S", description=desc, footprint=PH_FP,
                pins=[Pin(num=i + 1, name=n, func=P)
                      for i, n in enumerate(harness.ph_trunk_pins())])


def _xcvr(tag, desc):
    """SN65HVD230DR, SOIC-8: 1 D, 2 GND, 3 VCC, 4 R, 5 Vref, 6 CANL, 7 CANH, 8 Rs.

    TI SLOS346O section 7 "Pin Functions", read 2026-09-30."""
    return Part(name="SN65HVD230DR", ref_prefix="U", tag=tag, dest="NETLIST", tool="skidl",
                value="SN65HVD230DR", description=desc,
                footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                pins=[Pin(num=1, name="D", func=I), Pin(num=2, name="GND", func=PWR),
                      Pin(num=3, name="VCC", func=PWR), Pin(num=4, name="R", func=O),
                      Pin(num=5, name="Vref", func=O), Pin(num=6, name="CANL", func=P),
                      Pin(num=7, name="CANH", func=P), Pin(num=8, name="Rs", func=I)])


def _LMR33630_DDA_PINS():
    """The LMR33630's HSOIC-8 (DDA) pinout, from TI SNVSAN3F Table 6-1 -- READ, not recalled.

    ⚠⚠ THIS BOARD CARRIED A PINOUT WITH SEVEN OF EIGHT PINS WRONG UNTIL 2026-09-30, on both
    U5 (the Pi's 5 V) and U6 (the LED 5 V):

        pin   TI            what was here
         1    PGND          VIN      <- +24 V on the power-ground pin
         2    VIN           EN
         3    EN            "NC"     <- the part has no NC on this package
         4    PG            FB
         5    FB            GND
         6    VCC           SW
         7    BOOT          BOOT     (the one that was right)
         8    SW            VCC

    It carried no datasheet citation, unlike the LMR16006 forty lines up ("TI SNVSA24
    section 6"), and it routed, passed DRC and passed ERC: every check in this pipeline
    compares the board to the NETLIST, and the netlist was the thing that was wrong. As
    built, F1 would have blown at first power and neither 5 V rail would ever have come up.
    The VQFN instances (optical U13, fret_led/foot_led U10) were checked against the same
    table the same day and are correct.

    Found while asking what a first-article board would need for DIAGNOSIS -- the "NC" on
    a part whose feature list includes a power-good flag was the thread. The cheapest
    diagnostic there is turns out to be reading the pin table before the board is made.

    Connections are made BY NAME below so the numbers live in exactly one place. PG (4) is
    open-drain and "can be left open when not used"; it is the hook for a rail-status
    pad -- see docs/board-bringup-diagnostics.md."""
    return [Pin(num=1, name="PGND", func=Pin.types.PWRIN), Pin(num=2, name="VIN", func=Pin.types.PWRIN),
            Pin(num=3, name="EN", func=Pin.types.PASSIVE), Pin(num=4, name="PG", func=Pin.types.PASSIVE),
            Pin(num=5, name="FB", func=Pin.types.PASSIVE), Pin(num=6, name="VCC", func=Pin.types.PASSIVE),
            Pin(num=7, name="BOOT", func=Pin.types.PASSIVE), Pin(num=8, name="SW", func=Pin.types.PASSIVE),
            Pin(num=9, name="AGND", func=Pin.types.PWRIN)]


@subcircuit
def motor_ctrl():
    gnd, v24, v33 = Net("GND"), Net("+24V"), Net("+3V3")
    for n in (gnd, v24, v33):
        n.drive = Pin.drives.POWER

    # ── the two buses ────────────────────────────────────────────────────────
    # This board is the END of each bus, not a pass-through, so one 4-way each --
    # the 8-way in/out pattern belongs to the tees and lever boards in the middle.
    a_h, a_l = Net("CANA_H"), Net("CANA_L")
    b_h, b_l = Net("CANB_H"), Net("CANB_L")
    # ⚠ J1 CARRIES BUS A'S WHOLE CURRENT ON ONE 3 A CONTACT, and BOM.md has the analysis
    # -- see "The bottleneck moves rather than disappears" in the 24 V bus section. In
    # short: J3 below was doubled because its ways were idle, and doing the same here is
    # not free because ways 3 and 4 carry CAN. The BOM's own conclusion is that the answer
    # is probably a firmware slew cap rather than a connector change, since Tr8x2 is
    # self-locking and the bus carries essentially nothing at rest.
    # This pointer exists because the netlist is where someone meets this connector, and
    # the analysis lives three files away.
    j1 = _xh("J1", "bus A out -- the ten motor tees")
    # ⚠ J2 IS PH AND CARRIES 5 V, NOT 24 V (user, 2026-09-21). The lever boards run off a
    # 5 V bus now (their buck is gone -- elec/lever_sensor.py), and their trunk is PH, a
    # different family from the 24 V XH motor tees so no harness can cross them. J2's +V
    # comes off this board's own +5V (the Pi rail, after F2) -- wired further down, once
    # that net exists.
    j2 = _ph4("J2", "bus B IN -- from the pedals at the leg, 5 V, JST PH side entry")
    # ⚠ J6, AND NOT J5, WHICH THIS BOARD ALREADY USES (the Pi's 5 V XH). Taking a
    # ref that exists does not collide loudly -- SKiDL renumbers the OTHER part, so
    # the Pi's two connectors silently became J8 and J9 and their placements stopped
    # matching. The only symptom was "no placement given for: J8, J9".
    # Every connector here now passes ref= as well as tag=, which is the fix
    # lever_sensor.py already documents: "passing ref= makes the tag authoritative,
    # so where a part is CREATED stops mattering."
    j6 = _ph4("J6", "bus B OUT -- to the lever chain, 5 V, JST PH side entry")
    # ⚠ J3 IS A 6-WAY, AND WAYS 5 AND 6 ARE THE POWER BUTTON (user, 2026-10-04: "let's avoid
    # a new cable between the output and motor and just put the power switch signal on the
    # same cable carrying power from the output board to the motor board"). The button is on
    # the UI board; its two throws come down the 16-way ribbon to pi_cap, across the lights
    # cable to J7 below, over this board on copper, and out here to output_panel J10, where
    # the switch element on the 24 V inlet is. This board does not read them and puts
    # nothing on them: the pull-up lives on the output panel (the switch is a 12 V / 0.3 A
    # part), so with this board dark the lines still work -- which they must, because they
    # are what turns it on.
    # Ways 1-4 are what they were (the two 24 V contacts stay doubled: 3 A per XH contact),
    # so the declared 24 V copper under this connector did not move. A 6-way plug also
    # cannot enter any 4-way header on the instrument, which retires this link's share of
    # the "two pinouts on one 4-way XH" finding.
    j3 = Part(name="B6B-XH-A", ref_prefix="J", tag="J3", ref="J3", dest="NETLIST",
              tool="skidl", value="B6B-XH-A",
              description="24 V in from output_panel J10 + the power button's two throws out",
              footprint="Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical",
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(
                  # harness.PWR_LINK: the same list output_panel J10 is built from
                  tuple({"V24": "+24V"}.get(w, w) for w in harness.PWR_LINK))])
    # the inlet had no capacitor within 28 mm; this is its HF bypass
    c29 = _c("C29", "100nF/50V", "24 V HF bypass at the inlet J3")
    v24 += c29[1]; gnd += c29[2]
    sw_up, sw_dn = Net("PWR_SW_UP"), Net("PWR_SW_DN")
    sw_up += j3[5]; sw_dn += j3[6]
    gnd += j1[1], j2[1], j6[1], j3[1], j3[4]
    v24 += j1[2], j3[2], j3[3]
    a_h += j1[3]; a_l += j1[4]
    # bus B still passes THROUGH -- it is now two connectors rather than two halves of
    # one, which is the same node with a service joint in the middle of it
    b_h += j2[3], j6[3]; b_l += j2[4], j6[4]
    # ⚠ J3 NOW DOUBLES ITS CONTACTS, AND IT IS A RATING FIX RATHER THAN TIDINESS. This
    # is the sink end of the instrument's whole 24 V trunk. BOM.md sizes that bus at
    # under 5 A and XH is rated 3 A per contact, which is exactly why the SOURCE (the
    # output panel's J7) puts two contacts on each rail -- and this end was taking all
    # of it through one. A doubled source into a single-contact sink is not doubled.
    # The cavities were previously left empty on the reasoning that wiring the CAN pair
    # to a power-only connector would hang an unterminated stub; that reasoning was
    # right about CAN and does not apply to power, which is what they carry now. Pin
    # order is the instrument's standard: 1=GND 2=+24V 3=+24V 4=GND.
    #
    # ⚠ AND THE BOTTLENECK MOVES RATHER THAN DISAPPEARS -- FLAGGED, NOT FIXED. J1 and
    # J2 are the bus outputs, and on a four-wire CAN-plus-power bus (GND, +24V, H, L --
    # the user's colour scheme) the 24 V rides ONE conductor and one contact. Bus A
    # feeds ten SERVO42D drivers, so very nearly the whole <5 A passes through a single
    # 3 A contact at J1. Doubling here is free because J3's spare ways were idle; doing
    # the same at J1/J2 is not, because those ways carry CAN. Resolving it means a
    # wider shell, a separate power bus, or a measured slew budget showing the staggered
    # peak is genuinely under 3 A -- a motor-controller decision, recorded in BOM.md.

    # ── 24 V -> 3V3, LMR16006XDDCR (LCSC C87080), same part as the lever board ─
    # TI SNVSA24 section 6: 1 CB, 2 GND, 3 FB, 4 SHDN, 5 VIN, 6 SW. SHDN floats =
    # enabled. Asynchronous, so the catch diode is required, not optional.
    u4 = Part(name="LMR16006XDDCR", ref_prefix="U", tag="U4", dest="NETLIST", tool="skidl",
              value="LMR16006XDDCR", description="60 V 0.6 A buck, 24 V -> 3V3",
              footprint="Package_TO_SOT_SMD:SOT-23-6",
              pins=[Pin(num=1, name="CB", func=P), Pin(num=2, name="GND", func=PWR),
                    Pin(num=3, name="FB", func=I), Pin(num=4, name="SHDN", func=I),
                    Pin(num=5, name="VIN", func=PWR), Pin(num=6, name="SW", func=O)])
    sw, fb, cb = Net("SW"), Net("FB"), Net("CB")
    v24 += u4["VIN"]; gnd += u4["GND"]; sw += u4["SW"]; fb += u4["FB"]; cb += u4["CB"]
    l1 = Part(name="L", ref_prefix="L", tag="L1", dest="NETLIST", tool="skidl",
              # A PART (LCSC C19634068, APV): 47 uH, 0.58 A rms, 0.88 A saturation, 3x3x1.5.
              # Peak here is 0.25 A load + half of 87 mA ripple (700 kHz) = 0.29 A. The
              # common 3015 47 uH parts saturate at 0.43 A (ANR3015T470M, FNR3015S470MT):
              # they fit this land and clear the peak, but sit under the IC's 0.9 A limit.
              value="PNR3015-470M", description="47 uH buck inductor, Isat 0.88 A",
              footprint="Inductor_SMD:L_Taiyo-Yuden_NR-30xx",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw += l1[1]; v33 += l1[2]
    d1 = Part(name="B5819W", ref_prefix="D", tag="D1", dest="NETLIST", tool="skidl",
              value="B5819W", description="buck catch diode (Schottky, 40 V)",
              footprint="Diode_SMD:D_SOD-123",
              pins=[Pin(num=1, name="K", func=P), Pin(num=2, name="A", func=P)])
    sw += d1["K"]; gnd += d1["A"]
    cin = _c("C1", "4.7uF/50V", "buck input bulk -- 50 V part on a 24 V rail",
             "Capacitor_SMD:C_1206_3216Metric")
    v24 += cin[1]; gnd += cin[2]
    # ⚠ AND U1 HAD NO HF INPUT BYPASS AT ALL until 2026-09-19 -- only C1, which its own
    # description calls "input bulk", 11.50 mm from the VIN pin through 15.94 mm of
    # copper and two vias. Bulk at that distance is a DC reservoir; it cannot supply a
    # switching edge, because the path to it is ~10-15 nH and most of that is the B.Cu
    # stretch, a full core thickness from the plane. C21 is the part that actually holds
    # VIN up during the edge, and the only thing it has to be is CLOSE.
    c_hf = _c("C23", "100nF/50V", "buck input HF bypass -- must sit at U1's VIN/GND pins")
    v24 += c_hf[1]; gnd += c_hf[2]
    cout = _c("C2", "10uF/16V", "buck output bulk", "Capacitor_SMD:C_0805_2012Metric")
    v33 += cout[1]; gnd += cout[2]
    cboot = _c("C3", "100nF", "bootstrap, CB to SW")
    cb += cboot[1]; sw += cboot[2]
    r1 = _r("R1", "100k", "feedback divider, top")     # VOUT = 0.765 x (1 + R1/R2)
    r2 = _r("R2", "30k1", "feedback divider, bottom")
    v33 += r1[1]; fb += r1[2], r2[1]; gnd += r2[2]

    # ── the two transceivers ─────────────────────────────────────────────────
    a_tx, a_rx = Net("CAN1_TX"), Net("CAN1_RX")
    b_tx, b_rx = Net("CAN2_TX"), Net("CAN2_RX")
    u2 = _xcvr("U2", "bus A -- the motors")
    u3 = _xcvr("U3", "bus B -- the levers and pedals")
    for u, (tx, rx, ch, cl), rtag in ((u2, (a_tx, a_rx, a_h, a_l), "R3"),
                                      (u3, (b_tx, b_rx, b_h, b_l), "R4")):
        tx += u["D"]; rx += u["R"]
        gnd += u["GND"]; v33 += u["VCC"]
        ch += u["CANH"]; cl += u["CANL"]
        # Rs to GND through a resistor sets slope control. 10 k slews the edges,
        # which is right on a metre of cable in a box full of motors; neither bus
        # is anywhere near the part's 1 Mbps limit.
        rs = _r(rtag, "10k", "transceiver slope control")
        u["Rs"] += rs[1]; gnd += rs[2]

    # TERMINATION -- BUS A ONLY (user, 2026-09-22). A 120 ohm terminator is an END-OF-BUS
    # part, and since the controller moved to the MIDDLE of bus B it is no longer an end of
    # it. Terminating a mid-bus node puts a third 120 ohm across the pair: the two real
    # ends already load it to 60, a third drops it to 40 and the transceivers drive a load
    # they are not specified into. Bus B's two terminators now live where the bus actually
    # ends -- the +X-end lever board and the far-end pedal board, on the JP1 + R4 each
    # lever/pedal board already carries, so exactly two jumpers are closed in the
    # instrument and every board in between stays open.
    # Bus A is unchanged: this board IS its end, the last motor tee is the other.
    for tag, (ch, cl), jtag in (("R5", (a_h, a_l), "JP1"),):
        rt = _r(tag, "120R", "CAN termination, 1%", "Resistor_SMD:R_0603_1608Metric")
        jp = Part(name="SolderJumper_2_Open", ref_prefix="JP", tag=jtag, dest="NETLIST",
                  tool="skidl", value="TERM", description="close at the bus end",
                  footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm",
                  pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
        mid = Net("TERM_%s" % tag)
        ch += rt[1]; mid += rt[2], jp[1]; cl += jp[2]

    # BUS-PIN CLAMPS, two per pair. Separate BIDIRECTIONAL parts rather than a
    # 3-pin CAN array: a 2-pin bidirectional device is symmetric, so there is no
    # pinout to get wrong. The threat is the leg's TRRS -- a plug drags its bands
    # across every socket contact on insertion, and 24 V reaching a bus pin is
    # past this transceiver's -4..+16 V absolute maximum.
    for tag, net in (("D2", a_h), ("D3", a_l), ("D4", b_h), ("D5", b_l)):
        d = Part(name="TVS", ref_prefix="D", tag=tag, dest="NETLIST", tool="skidl",
                 # ⚠ THIS SAID "SMF24CA" UNTIL 2026-10-04, AND THAT PART DOES NOT EXIST IN
                 # THIS PACKAGE: SMF24CA is SOD-123FL, the land here is SOD-523. It was
                 # also the wrong clamp. A 24 V stand-off part clamps near 39 V and this
                 # transceiver's bus pins stop at 16 V, so it protected nothing; and no
                 # clamp turns a DC 24 V fault into a safe one. What a clamp can do here
                 # is ESD, and for that the house part fits: 5 V stand-off (the bus sits
                 # at 2.3 V, +-1 V of drive), ~10 V clamp, the same reel as the output
                 # panel's.
                 value="ESD5B5.0ST1G", description="bidirectional ESD clamp, bus pin to GND",
                 footprint="Diode_SMD:D_SOD-523",
                 pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
        net += d[1]; gnd += d[2]

    # ── MCU, CH32V307WCU6 QFN-68 (LCSC C5142795) ─────────────────────────────
    # Pins off WCH's CH32V303/305/307/317 datasheet V3.9, table 3-1, QFN68 column:
    #   69 VSS (exposed pad -- KiCad numbers that land 69)
    #   5 OSC_IN  6 OSC_OUT  7 NRST  12 VSSA  13 VDDA  63 BOOT0
    #   18/49 VSS   32/50/68 VDD   17/31/51/67 VIO   (this part has a SEPARATE
    #     I/O supply, which the CH32V203 on the lever board does not)
    #   64 PB8 = CAN1_RX_2 , 65 PB9 = CAN1_TX_2   <- bus A, THE REMAP
    #   35 PB12 = CAN2_RX  , 36 PB13 = CAN2_TX    <- bus B
    #   46 PA11 = OTG_FS_DM, 47 PA12 = OTG_FS_DP  <- the Pi link
    #   48 PA13 = SWDIO    , 52 PA14 = SWCLK
    #   1 VBAT -- tied to 3V3 (2026-09-21)
    #
    # ⚠ VBAT (PIN 1) WAS NEVER CONNECTED, on this board AND the output board, both "checked
    # against the QFN68 column". The check covered the pins that were WIRED; nothing asked
    # which pins of the package were not. VBAT feeds the backup domain (RTC, backup
    # registers) and WCH, like every part in this family, wants it tied to VDD when no
    # battery is fitted -- floating, the backup domain's supply is undefined. Found by
    # listing Table 3-1's QFN68 column whole (.ins/ch32v307_qfn68.json) against the netlist.
    #
    # ⚠ ALL TWENTY-FOUR CHECKED AGAINST THE QFN68 COLUMN, 2026-09-17, ZERO MISMATCHES --
    # numbers AND names, including every power pin, read with per-word coordinates so the
    # value taken is the one standing in the QFN68 column rather than whichever number
    # happens to be on the line. A wrong pin number here is invisible to everything
    # downstream: SKiDL connects a net to a pin NUMBER, layout places the pad it names,
    # and DRC agrees the copper matches the netlist. The board would simply not run.
    #
    # ⚠ AND THE DIRECTION OF THE CAN1 REMAP IS THE PART WORTH RE-READING. PB8 is RX and
    # PB9 is TX; an automated pass over the alternate-function table said PB8 = CAN1_TX_2,
    # which would have meant the bus-A transceiver wired backwards and a dead bus. It was
    # the extraction, not the datasheet: that table splits CAN1_RX_2 across two lines as
    # "CAN1_RX_" and "2", and the rows are close enough together that the tail of one
    # lands beside its neighbour. Read by eye off page 53, PB8 is RX. The remap exists at
    # all because CAN1's home pins are PA11/PA12, which USB is using.
    dm, dp = Net("USB_DM"), Net("USB_DP")
    nrst, boot0 = Net("NRST"), Net("BOOT0")
    osc1, osc2 = Net("OSC_IN"), Net("OSC_OUT")
    swdio, swclk = Net("SWDIO"), Net("SWCLK")
    pins = [(69, "VSS_PAD", PWR), (5, "OSC_IN", I), (6, "OSC_OUT", O), (7, "NRST", I),
            (12, "VSSA", PWR), (13, "VDDA", PWR), (18, "VSS_1", PWR), (49, "VSS_2", PWR),
            (32, "VDD_1", PWR), (50, "VDD_2", PWR), (68, "VDD_3", PWR),
            (17, "VIO_4", PWR), (31, "VIO_1", PWR), (51, "VIO_2", PWR), (67, "VIO_3", PWR),
            (35, "PB12", I), (36, "PB13", O), (46, "PA11", P), (47, "PA12", P),
            (48, "PA13", P), (52, "PA14", P), (63, "BOOT0", I),
            (64, "PB8", I), (65, "PB9", O), (1, "VBAT", PWR),
            # bring-up sense pins (docs/board-bringup-diagnostics.md 2.2, 2.3). Numbers off
            # the same QFN68 column (.ins/ch32v307_qfn68.json): 8 PC0, 9 PC1, 20 PA4, 39 PC6.
            (8, "PC0", I), (9, "PC1", I), (20, "PA4", I),
            (39, "PC6", I)]
    u1 = Part(name="CH32V307WCU6", ref_prefix="U", tag="U1", dest="NETLIST", tool="skidl",
              value="CH32V307WCU6", description="RISC-V MCU, 2x hardware CAN",
              footprint=MCU_FP,
              pins=[Pin(num=n, name=nm, func=f) for n, nm, f in pins])
    gnd += u1["VSS_PAD"], u1["VSS_1"], u1["VSS_2"], u1["VSSA"]
    v33 += (u1["VDD_1"], u1["VDD_2"], u1["VDD_3"], u1["VDDA"],
            u1["VIO_1"], u1["VIO_2"], u1["VIO_3"], u1["VIO_4"], u1["VBAT"])
    nrst += u1["NRST"]; boot0 += u1["BOOT0"]
    osc1 += u1["OSC_IN"]; osc2 += u1["OSC_OUT"]
    a_rx += u1["PB8"]; a_tx += u1["PB9"]         # CAN1 REMAPPED -- see the header
    b_rx += u1["PB12"]; b_tx += u1["PB13"]
    dm += u1["PA11"]; dp += u1["PA12"]
    swdio += u1["PA13"]; swclk += u1["PA14"]

    y1 = Part(name="Crystal", ref_prefix="Y", tag="Y1", dest="NETLIST", tool="skidl",
              # A PART, not a frequency (LCSC C403948, Yajingxin): CL 12 pF, ESR 250 ohm
              # max, C0 5 pF max, 100 uW. Lands 1 / 3 are the crystal, 2 / 4 the can.
              value="TAXM8M4RFDCET2T",
              description="8 MHz HSE, CL 12 pF -- CAN bit timing wants a crystal",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=i + 1, func=P) for i in range(4)])
    osc1 += y1[1]; osc2 += y1[3]; gnd += y1[2], y1[4]
    for tag, net in (("C4", osc1), ("C5", osc2)):
        # 15 pF each: CL = 15 / 2 + ~4 pF of pin and track = 11.5 pF against the
        # crystal's 12. (They were 12 pF, which is 10 pF of load and ~25 ppm fast.)
        c = _c(tag, "15pF", "crystal load"); net += c[1]; gnd += c[2]
    c_n = _c("C6", "100nF", "NRST filter"); nrst += c_n[1]; gnd += c_n[2]

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
                              ("TP5", v33, "target sense")):
        _tp = Part(name="TestPoint", ref_prefix="TP", ref=_ref, dest="NETLIST",
                   tool="skidl", value="SWD",
                   description="SWD pad -- %s; bare copper, no component" % _what,
                   footprint="TestPoint:TestPoint_Pad_D1.5mm",
                   pins=[Pin(num=1, func=P)])
        _net += _tp[1]

    r_b = _r("R7", "10k", "BOOT0 pull-down"); boot0 += r_b[1]; gnd += r_b[2]
    # Eight supply pins want their own decoupling; one bulk holds the rail up.
    for tag in ("C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14"):
        c = _c(tag, "100nF", "MCU supply decoupling"); v33 += c[1]; gnd += c[2]
    c_bulk = _c("C15", "10uF", "MCU bulk", "Capacitor_SMD:C_0805_2012Metric")
    v33 += c_bulk[1]; gnd += c_bulk[2]

    # ── the link to the Pi: USB 2.0 on a top-entry XH, NOT a USB-C receptacle ──────
    # ⚠ THE USB-C COULD NOT BE PLUGGED IN (2026-09-21). It sat on the board's -Y edge with
    # its mouth facing the -Y rail, and standing on the keyhead endplate that edge is 5.5 mm
    # from the wall -- no USB-C plug, straight or right-angle, fits in front of it, let alone
    # goes in. Every other edge is as tight (9 mm to the deck, 10 to the floor, 8 to the Pi).
    # The only direction with room is straight off the board's face into the bay, which is
    # the direction every OTHER lead on this board already leaves by: a top-entry XH.
    # So the link is a stock USB-A -> 4-way XH lead (Amazon B0H9QTYT83), plugged into the
    # Pi's USB-A like the old cable was. XH is what every board-level connector in the
    # instrument is (user), the cable's crimps re-pin in the housing without solder if a
    # batch arrives in another order, and nothing here needed USB-C: no CC (a USB-A host has
    # none, so R8/R9 went with it), no orientation, and full speed is all the link uses.
    # Pin order is USB's own: 1 VBUS, 2 D-, 3 D+, 4 GND.
    # VBUS IS DELIBERATELY UNCONNECTED, as it was on the USB-C: the board runs off the 24 V
    # rail, and taking VBUS as well would leave the Pi's supply and the instrument's
    # arguing over who holds the rail. It is a landing for a future VBUS-present sense.
    usb = Part(name="B4B-XH-A", ref_prefix="J", tag="J4", ref="J4", dest="NETLIST",
               tool="skidl",
               value="B4B-XH-A", footprint=XH_FP,
               description="USB 2.0 link to the Pi (USB-A -> XH lead): VBUS n/c, D-, D+, GND",
               pins=[Pin(num=i + 1, name=n, func=P)
                     for i, n in enumerate(("VBUS", "D-", "D+", "GND"))])
    vbus = Net("VBUS_NC")
    vbus += usb[1]
    dm += usb[2]
    dp += usb[3]
    gnd += usb[4]
    # ── 24 V -> 5 V FOR THE Pi, AND THE CROWBAR THAT MATTERS MORE ────────────
    # THE POWER BOARD IS GONE AND THIS IS IT (user, 2026-09-15). It was its own
    # PCB in the tray; merging it here deletes a board, a connector and a cable --
    # but the real reason is that it deletes a JUNCTION. The 24 V trunk had to
    # feed both boards at the keyhead and the power board had only a 4-way INLET,
    # so that branch was a SPLICE, the only one in the instrument without a board
    # behind it. One board at the end of the chain needs no branch at all.
    #
    # THE MOTOR CURRENT NEVER COMES THROUGH HERE. The chain runs output panel ->
    # tees -> keyhead and every motor taps at its own tee, so what reaches this
    # board is its own draw plus the Pi's 5 V worth -- about 0.7 A at 24 V.
    #
    # ⚠ THE CROWBAR IS THE POINT, NOT THE BUCK. The Pi is fed through its GPIO
    # header, and on a Pi 4B the USB-C VBUS pin and the GPIO 5 V pins are the SAME
    # NODE with no polyfuse between them -- so that path skips every input
    # protection the Pi has. If U5 ever fails SHORT, 24 V lands on the 5 V rail and
    # takes the Pi, the OLED and the joystick with it. D9 conducts, F2 opens, and
    # the damage stops at a $0.30 part.
    v5, v5_raw = Net("+5V"), Net("+5V_RAW")
    # F1 fuses ONLY the buck's feed. The bus connectors keep their unfused 24 V --
    # fusing the trunk here would put this board in series with every motor.
    #
    # ⚠ 1 A IS SIZED FOR THE Pi THIS BOARD EXPECTS, NOT FOR THE ONE THE BOM BUDGETS, and
    # the gap is worth knowing before someone loads the Pi's USB ports. BOM.md specifies a
    # "Pi buck >=3 A", i.e. 15 W at 5 V, and U5 is a 3 A part chosen to match. Referred to
    # 24 V through this fuse:
    #
    #     Pi draw    eff 90%    eff 85%    eff 80%
    #       3.0 A     0.694 A    0.735 A    0.781 A     69 / 74 / 78 % of F1
    #       1.5 A     0.347      0.368      0.391       35 / 37 / 39 %
    #       0.6 A     0.139      0.147      0.156       14 / 15 / 16 %
    #
    # A fuse is normally run at 75 % of rating or less continuously, and derates further
    # above 25 C. At a typical Pi load this is a third of the fuse and entirely fine; at
    # the FULL 3 A the design budgets it sits at the derating limit or past it, so the
    # failure mode is a nuisance blow under heavy USB load rather than anything unsafe.
    #
    # It is left at 1 A deliberately: the job here is fault containment -- "a shorted U5
    # must not feed the fault back out into the trunk" -- and a larger fuse is worse at
    # that job. What the number really says is that the Pi's ports are not a free
    # expansion slot on this instrument. If they ever need to be, this fuse and its
    # derating are the first thing to revisit, not the buck.
    v24_buck = Net("+24V_BUCK")
    f1 = Part(name="Fuse", ref_prefix="F", tag="F1", dest="NETLIST", tool="skidl",
              value="JFC1206-1100FS", description="1 A 63 V: 24 V fuse for the buck -- a shorted U5 must "
              "not feed the fault back out into the trunk",
              footprint="Fuse:Fuse_1206_3216Metric",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v24 += f1[1]
    v24_buck += f1[2]
    sw5, boot5, vcc5, fb5, en5 = (Net("SW5"), Net("BOOT5"), Net("VCC5"),
                                  Net("FB5"), Net("EN5"))
    for n in (v5, v5_raw):
        n.drive = Pin.drives.POWER
    # LMR33630: 3.8-36 V in, 3 A, SYNCHRONOUS (no catch diode), HSOIC-8 with a
    # thermal pad. 36 V of absolute maximum against a 24 V rail shared with ten
    # stepper drivers is the headroom that matters; the 24 V-max parts in this
    # class have none at all.
    u5 = Part(name="LMR33630ADDAR", ref_prefix="U", tag="U5", dest="NETLIST",
              tool="skidl", value="LMR33630ADDAR",
              description="36 V 3 A synchronous buck, 24 V -> 5 V for the Pi",
              footprint="Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm",
              pins=_LMR33630_DDA_PINS())
    v24_buck += u5["VIN"]
    en5 += u5["EN"]
    fb5 += u5["FB"]
    # The exposed pad is the ground connection AND the only heat path off the die.
    gnd += u5["PGND"], u5["AGND"]
    sw5 += u5["SW"]
    boot5 += u5["BOOT"]
    vcc5 += u5["VCC"]
    l2 = Part(name="L", ref_prefix="L", tag="L2", dest="NETLIST", tool="skidl",
              # ⚠ A PART, CHOSEN FOR SATURATION (2026-10-04; TDK, LCSC C415364). At 400 kHz the
              # ripple is 5 x (1 - 5/24) / (6.8 uH x 400 kHz) = 1.46 A, so 3 A of load peaks
              # at 3.73 A, and TI asks for a saturation current at or above the high-side
              # limit (4.5 A typ, SNVSAN3F 9.2.2.4). The Bourns SRN6028 this said, and the
              # 6028-size parts on its land, saturate at 2.6 A -- under the PEAK.
              # This one: 4.7 A saturation, 3.6 A rms, 36 mOhm, 6.0 x 6.0 x 4.5.
              # Do not substitute a 6028. Nearest alternate: Sunlord SWPA6045S6R8MT
              # (4.3 A, C57254), whose land is 0.15 mm wider each end.
              value="VLS6045EX-6R8M",
              description="6.8 uH 5 V buck inductor, Isat 4.7 A, shielded 6x6x4.5",
              footprint="Inductor_SMD:L_TDK_VLS6045EX_VLS6045AF",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw5 += l2[1]
    v5_raw += l2[2]
    # 1206 for the DC-BIAS derating, not merely the voltage rating: an 0805 50 V
    # part loses most of its capacitance at 24 V bias.
    for tag, val in (("C16", "10uF/50V"), ("C17", "10uF/50V")):
        c = _c(tag, val, "5 V buck input bulk", "Capacitor_SMD:C_1206_3216Metric")
        v24_buck += c[1]; gnd += c[2]
    c18 = _c("C18", "100nF/50V", "5 V buck input HF bypass -- nearest VIN/GND")
    v24_buck += c18[1]; gnd += c18[2]
    c19 = _c("C19", "1uF", "5 V buck VCC bypass")
    vcc5 += c19[1]; gnd += c19[2]
    c20 = _c("C20", "100nF", "5 V buck bootstrap -- BOOT to SW")
    boot5 += c20[1]; sw5 += c20[2]
    for tag in ("C21", "C22"):
        # 1206 / 25 V, for what is LEFT at 5 V of bias: about 15 uF each, where the 0805 /
        # 16 V parts these replaced keep about 11. With C27 behind the fuse that is ~37 uF
        # on the board; TI's equation 6 asks 37.5 uF for a 1.5 A step inside 250 mV, and
        # its 400 kHz / 5 V table row fits 4 x 22 uF. The Pi's own bulk is the rest.
        c = _c(tag, "22uF/25V", "5 V output bulk", "Capacitor_SMD:C_1206_3216Metric")
        v5_raw += c[1]; gnd += c[2]
    # Feedback from the RAW node, BEFORE the fuse: regulating after F2 would put
    # the fuse's resistance inside the loop and let a warm fuse move the rail.
    r10 = _r("R10", "100k", "5 V feedback divider, top")
    # 24k9: VREF is 1.0 V (LMR33630 datasheet SNVSAN3), so RFBB = RFBT / (VOUT/VREF - 1)
    # = 100k / 4 = 25k, and TI's own 5 V example in that datasheet uses 100k / 24.9k.
    r11 = _r("R11", "24k9 1%", "5 V feedback divider, bottom -- 5.02 V with R10")
    v5_raw += r10[1]; fb5 += r10[2], r11[1]; gnd += r11[2]
    # EN divider: hold the converter off until the 24 V rail is up, so it does not
    # try to start into a sagging supply and chatter.
    # The EN pin has a PRECISION threshold -- 1.231 V typ, 1.2 to 1.26 over temperature
    # (LMR33630 datasheet, VEN-H) -- which is what makes an external divider a real UVLO
    # rather than a pull-up. For turn-on at 18 V the divider must be 18/1.231 = 14.6:1,
    # so 137k over 10k (147k total) trips at 18.1 V typical and 17.6 to 18.5 V across the
    # threshold's own spread. Enable leakage is 0.2 nA, so a 147k divider is not loaded.
    r12 = _r("R12", "137k 1%", "5 V EN/UVLO divider, top -- turn-on at 18.1 V")
    r13 = _r("R13", "10k 1%", "5 V EN/UVLO divider, bottom")
    v24 += r12[1]; en5 += r12[2], r13[1]; gnd += r13[2]

    f2 = Part(name="Fuse", ref_prefix="F", tag="F2", dest="NETLIST", tool="skidl",
              value="JFC1206-1400FS", description="4 A 63 V: 5 V output fuse -- the element D9 blows when "
              "U5 fails short", footprint="Fuse:Fuse_1206_3216Metric",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v5_raw += f2[1]; v5 += f2[2]
    # 5 V out on TWO contacts and GND on two: XH is rated 3 A per contact and the
    # design draw IS 3 A, so a single contact would sit exactly on its rating.
    j5 = Part(name="B4B-XH-A", ref_prefix="J", tag="J5", ref="J5", dest="NETLIST",
              tool="skidl",
              value="B4B-XH-A", description="5 V to the Pi's GPIO pins 2/4 + 6/9",
              footprint=XH_FP,
              pins=[Pin(num=i + 1, name=n, func=P)
                    for i, n in enumerate(                 # = pi_cap J2, one list
                        {"V5": "+5V"}.get(w, w) for w in harness.PI_5V_LINK)])
    gnd += j5[1], j5[4]
    v5 += j5[2], j5[3]
    # THE LEVER BUS'S 5 V. Eleven boards at ~30 mA each (CH32V203 + SN65HVD230 + MT6701,
    # through each board's own AP2112K) is ~0.33 A on U5, which is a 3 A part sized for
    # the Pi. At a typical Pi draw (0.6-1.5 A) that is comfortable; at the full 3 A the
    # BOM budgets for the Pi it is 11 % over U5's rating -- the same "the Pi's USB ports
    # are not a free expansion slot" limit F1's note already names. And a D9 crowbar
    # event now also drops the lever bus, which is the right way round: nothing senses
    # while the Pi is dark anyway.
    # ⚠ AND IT IS BEHIND A CURRENT-LIMITED SWITCH NOW (2026-10-04). The wiring notes and
    # src/leg_pogo.py have always said bus B runs "behind a current-limited switch"; this
    # netlist tied J2 / J6 way 2 straight to +5V, behind nothing but F2's 4 A. Bus B's 5 V
    # is the one rail on this board that leaves the instrument's inside: it crosses the leg
    # joints on spring pins a hand or a dropped tool can bridge, and a short there pulled
    # the Pi's rail down with it until a 4 A fuse opened.
    # TPS2553 (TI SLVS841F): constant-current, 2 us to a short, reverse blocking, 85 mOhm.
    # RILIM 49.9k -> 475 / 520 / 565 mA (p.7, the datasheet's own row, -40..125 C). The
    # load is 0.33 A, so the MINIMUM limit is 44 % over it and the maximum is a sixth of
    # what F2 passes. Drop at 0.33 A: 28 mV typical, 45 mV hot (135 mOhm).
    # Constant-current and NOT the -1 latch-off part: eleven boards' input capacitors are
    # a start-up into a capacitive load, which a latching part can refuse for ever.
    # EN (active high on the 2553, p.5) is tied to IN: the bus is up whenever 5 V is.
    # FAULT is open-drain, active low; PC6 reads it with its INTERNAL pull-up, the same
    # arrangement as PG_5V on PC1, so "bus B is shorted" is something the board can say
    # over USB. ⚠ FIRMWARE: PC6 must be an input WITH PULL-UP.
    v5_b = Net("+5V_BUSB")
    v5_b.drive = Pin.drives.POWER
    u6 = Part(name="TPS2553DBVR", ref_prefix="U", tag="U6", ref="U6", dest="NETLIST",
              tool="skidl", value="TPS2553DBVR",
              description="bus B 5 V current-limited switch, 0.52 A (LCSC C55266)",
              footprint="Package_TO_SOT_SMD:SOT-23-6",
              pins=[Pin(num=1, name="IN", func=P), Pin(num=2, name="GND", func=P),
                    Pin(num=3, name="EN", func=P), Pin(num=4, name="FAULT", func=P),
                    Pin(num=5, name="ILIM", func=P), Pin(num=6, name="OUT", func=P)])
    v5 += u6["IN"], u6["EN"]
    gnd += u6["GND"]
    v5_b += u6["OUT"], j2[2], j6[2]
    ilim = Net("BUSB_ILIM")
    r22 = _r("R22", "49k9 1%", "bus B current limit: 520 mA typ (TPS2553 p.7)")
    ilim += u6["ILIM"], r22[1]; gnd += r22[2]
    busb_flt = Net("BUSB_FAULT_N")
    busb_flt += u6["FAULT"], u1["PC6"]
    c25 = _c("C25", "100nF", "TPS2553 IN bypass -- 0.1 uF or more, at the pin (p.5)")
    v5 += c25[1]; gnd += c25[2]
    # the fused 5 V had no capacitor of its own: every one sat on +5V_RAW, the other side
    # of F2. This is J5's and U6's local bulk.
    c27 = _c("C27", "10uF/16V", "+5V local bulk after F2, for J5 and U6",
             "Capacitor_SMD:C_0805_2012Metric")
    v5 += c27[1]; gnd += c27[2]
    c28 = _c("C28", "10uF/16V", "bus B 5 V bulk at J2 / J6, after the limit",
             "Capacitor_SMD:C_0805_2012Metric")
    v5_b += c28[1]; gnd += c28[2]
    # ...and the switch's own output capacitor, at the pin: C28 is the bus's bulk and sits
    # 36 mm away at the connectors, which is no bypass for the limiter's output.
    c30 = _c("C30", "1uF/16V", "TPS2553 OUT bypass, at the pin")
    v5_b += c30[1]; gnd += c30[2]

    for tag, net in (("D6", dp), ("D7", dm)):
        d = Part(name="TVS", ref_prefix="D", tag=tag, dest="NETLIST", tool="skidl",
                 # 0.5 pF, 5 V stand-off, bidirectional (LRC, LCSC C5274293)
                 value="LESD5L5.0CT1G", description="USB data-line ESD clamp",
                 footprint="Diode_SMD:D_SOD-523",
                 pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
        net += d[1]; gnd += d[2]

    # ⚠ THESE TWO ARE CREATED LAST ON PURPOSE. SKiDL numbers a ref_prefix group by
    # CREATION order and ignores the tag, so building them beside the buck -- where
    # they belong logically -- handed them D6/D7 and pushed the USB clamps to D8/D9.
    # The placement dict and the CAD table both key on the ref, so the names have to
    # follow the parts, not the narrative.
    d8 = Part(name="D_TVS", ref_prefix="D", tag="D8", dest="NETLIST", tool="skidl",
              value="SMAJ30A", description="24 V rail clamp -- the trunk is shared "
              "with ten stepper drivers", footprint="Diode_SMD:D_SMA",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v24 += d8[1]; gnd += d8[2]

    d9 = Part(name="D_TVS", ref_prefix="D", tag="D9", dest="NETLIST", tool="skidl",
              value="SMBJ5.0A", description="THE CROWBAR: clamps the 5 V rail and "
              "draws enough through F2 to open it", footprint="Diode_SMD:D_SMB",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v5 += d9[1]; gnd += d9[2]

    # â”€â”€ THE LED STRIP'S 5 V: A SECOND BUCK, NOT A BIGGER ONE (user, 2026-09-28) â”€â”€â”€â”€â”€â”€
    # The strip is 36 RGBW LEDs over four sections and draws 2.2 A at full white. Feeding
    # it from U5 was considered and does not fit: U5 is a 3 A part already budgeted at 3 A
    # for the Pi, and F1 -- a 1 A fuse on the 24 V side -- already sits at 69-78 % of
    # rating at that draw. Pi + strip is 5.2 A on a 3 A buck and ~1.27 A through a 1 A
    # fuse. F1's own note names this exact limit ("the Pi's ports are not a free expansion
    # slot"), so the answer is a separate converter rather than a larger shared one.
    #
    # âš  AND SEPARATE IS BETTER THAN SHARED HERE FOR TWO MORE REASONS, not just current.
    # A shared rail would put the strip's PWM current steps on the Pi's supply, and it
    # would mean a crowbar event on either one taking out the other. Two bucks off the
    # same 24 V trunk keep those faults apart, and cost one IC: the part is the SAME
    # LMR33630ADDAR as U5, so this adds a placement and not an SKU.
    #
    # âš  THE RAIL IS +5V_LED AND IT NEVER MEETS +5V. It leaves on J7, crosses to pi_cap's
    # J4, and pi_cap passes it to the strip on J3 beside the SPI pair -- so ONE cable
    # reaches the strip carrying both, which is what pi_cap was built for. The two 5 V
    # rails share only GND.
    # ⚠ SUPERSEDED 2026-09-30 (docs/lighting-bus.md 3-4): THERE IS NO LED BUCK ANY MORE.
    # Everything above this line is the history of U6, a second LMR33630 that made 5 V for
    # one LED strip. The strip is gone; the lights are now the two fret boards and the foot
    # strip, and EVERY lit board carries its own buck (a made rail sent down 600 mm of cable
    # drops a third of the sink headroom, and drops more the brighter it gets). So what this
    # board owes the lights is 24 V AND NOTHING ELSE: a fuse, local bulk, and J7.
    # Gone with U6: L3, C25, C27-C31, R14-R17, F4, D10 and the PG_LED line into PC6.
    # 1.63 A with every zone of all three boards at full white (software-capped worst case),
    # so 3 A: 54 % of rating, inside the 75 % continuous rule. Same SKU as F2. D8 already
    # clamps the trunk this branches from.
    v24_led = Net("+24V_LED")
    v24_led.drive = Pin.drives.POWER
    f3 = Part(name="Fuse", ref_prefix="F", ref="F3", tag="F3", dest="NETLIST",
              tool="skidl", value="JFC1206-1300FS",
              description="24 V fuse for the lighting bus -- a short on a 600 mm LED "
                          "cable must not take the motor trunk down",
              footprint="Fuse:Fuse_1206_3216Metric",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v24 += f3[1]; v24_led += f3[2]
    c24 = _c("C24", "10uF/50V", "lighting-bus local bulk, after the fuse",
             "Capacitor_SMD:C_1206_3216Metric")
    v24_led += c24[1]; gnd += c24[2]
    c26 = _c("C26", "100nF/50V", "lighting-bus HF bypass at J7")
    v24_led += c26[1]; gnd += c26[2]
    # ONE contact each way since 2026-10-04: 1.63 A is 54 % of an XH contact's 3 A, and
    # ways 3 and 4 are the power button's two throws, arriving from pi_cap J4 and leaving
    # on J3. See J3.
    j7 = Part(name="B4B-XH-A", ref_prefix="J", ref="J7", tag="J7", dest="NETLIST",
              tool="skidl", value="B4B-XH-A",
              description="24 V to the lights via pi_cap J4, + the power button's throws in",
              footprint=XH_FP,
              pins=[Pin(num=i + 1, name=n, func=P)
                    for i, n in enumerate(                 # = pi_cap J4, one list
                        {"V24": "+24V_LED"}.get(w, w) for w in harness.LIGHTS_LINK)])
    gnd += j7[1]
    v24_led += j7[2]
    sw_up += j7[3]; sw_dn += j7[4]

    # ── BRING-UP SENSE: the board reports its own rails (2026-09-30) ─────────────────────
    # docs/board-bringup-diagnostics.md 2.2 and 2.3. No LEDs: the MCU reads these and says
    # so over USB, which works with the board shut inside the keyhead.
    # PG is OPEN-DRAIN and each line uses the MCU's INTERNAL pull-up, so power-good costs
    # two tracks and no parts. (Until the pinout fix both PG pins were listed "NC".)
    # ⚠ FIRMWARE: PC1 must be an input WITH PULL-UP, or it reads low for ever.
    pg5 = Net("PG_5V")
    pg5 += u5["PG"], u1["PC1"]
    # Rail sense into two ADC pins. PC0 = ADC10, PA4 = ADC4 -- read off the QFN68 pin
    # drawing in WCH's CH32V307 datasheet ("PC0/ADC10", "PA4/ADC4/DAC0"), 2026-09-30.
    #   +24V: 100k / 10k -> 2.18 V at 24 V, 2.73 V at a 30 V overshoot: inside 3.3 V always.
    #   +5V : 10k / 10k  -> 2.50 V.
    # A sagging trunk under motor load is the fault no static meter reading shows.
    sense24, sense5 = Net("SENSE_24V"), Net("SENSE_5V")
    r20 = _r("R20", "100k", "+24V sense divider, top")
    r21 = _r("R21", "10k", "+24V sense divider, bottom")
    v24 += r20[1]; sense24 += r20[2], r21[1], u1["PC0"]; gnd += r21[2]
    r18 = _r("R18", "10k", "+5V sense divider, top")
    r19 = _r("R19", "10k", "+5V sense divider, bottom")
    v5 += r18[1]; sense5 += r18[2], r19[1], u1["PA4"]; gnd += r19[2]



# ── the board ────────────────────────────────────────────────────────────────
# 40 x 35, sized by its own contents like the TRRS adapter and NOT by a housing:
# it replaces teensy_ifc in the electronics tray, whose 18 x 13 footprint was for
# two transceivers and three headers. The tray has the room -- deleting the Teensy
# and its audio shield freed far more than this needs -- but the tray must be
# rebuilt around this outline rather than the other way round.
# ⚠ 10 mm LONGER IN +Y (user, 2026-09-25: "feel free to make the PCB larger given the need
# for this extra space"). Reserving the -Y edge for the bus-B pair left J4 with NO legal
# site anywhere above y -12 -- sitesearch returned 984 legal sites and not one of them
# clear of the band the JSTs now own. The board was simply full.
# +Y and not +X, because board +X IS the downward edge, so growing
# there would lengthen the very edge we shortened by rotating. board +Y is world UP, which
# costs nothing -- the bay has headroom once the board drops to the chassis floor.
# ⚠ AUTHORED IN THE ORIENTATION IT IS BUILT IN, WITH NO ROTATION APPLIED LATER (user
# rule, standing: "we shouldn't define one orientation and then a rotation, we should just
# define the proper orientation from the start"). This board hangs in the keyhead endplate
# with its +X EDGE FACING THE CHASSIS FLOOR -- electronics.stand() maps flat +X to world
# -Z -- and that edge carries the two bus-B JSTs and nothing else, because anything on it
# would have its cable pointing down through the service hole.
# So the +X EDGE is the 46 mm one (the narrow edge: a shorter downward edge sterilises
# less of the board), which makes BOARD_W the 68 mm span ACROSS the board and BOARD_L
# the 46 mm edge itself. The ear is at the -X end, which stands at the TOP.
# It was briefly written the other way up with electronics.MCTRL_ROT = 90 and a swap
# branch; that is the mapping-bolted-on-the-end this rule exists to prevent, and it is
# gone -- MCTRL_ROT with it.
# ⚠ THE DOWNWARD EDGE IS SET BY THE JST FACE, NOT BY A ROUND NUMBER (user, 2026-09-25:
# "there appears to be a fair amount of PCB -z of the JST connectors ... we would want the
# PCB to extend at most to the edge of the connector and perhaps sit a touch back").
# At 68.0 the +X edge stood at x 34.00 while J2/J6's bodies ended at 28.30 -- 5.70 mm of
# bare laminate hanging below the plugs, with nothing on it (D6/D7, the next parts out,
# stop at 25.00). That is 5.70 mm of extra hole the chassis floor has to give up for no
# board, and the downward edge is the one length we have been paying to keep short.
# The frame had to shrink rather than the edge move: outline_mm is the POUR's layout
# region and it is centred on the origin, so an asymmetric board would pour off-centre.
# So BOARD_W drops 6.20 and all 64 placements moved +3.10 in x to re-centre -- the parts
# did not move relative to each other or to the -X end, only the origin did.
# The 0.50 is the "touch back": J2/J6 now overhang the edge by that much, so the plug
# face is the lowest thing on the board and no laminate reaches past it.
# ⚠ BOARD_L 62.0 -> 55.0 (2026-09-29): 7.00 mm OF BARE LAMINATE CAME OFF THE PI-FACING
# EDGE so a plug can reach the Pi's USB ports. Measured on this file's own placements: the 82
# parts occupied y -22.00..28.50, 50.50 of a 62.00 board, leaving 9.00 mm empty below the
# lowest part (D6/D7, the USB ESD clamps) and 2.50 above the highest. _MCTRL_CY maps
# board-local -31.00 to world y -41.50, which is the edge sitting 4.68 mm off the Pi's port
# face -- so the empty 9 mm was exactly where the gap had to come from.
# ALL 82 PLACEMENTS MOVED y -3.50 with it, which keeps every part where it was relative to
# the +Y edge: new span -25.50..25.00 inside +-27.50, so 2.00 of edge clearance at -Y
# (D6/D7) and 2.50 at +Y. Nothing was re-placed; the board was re-centred.
# ⚠ src/electronics.py's _MCTRL_CY must go -10.5 -> -7.0 to match, or the board shrinks
# from BOTH ends and the +Y edge walks into body_adapter_0 (inner face y 21.15, and the old
# +Y edge at 20.50 had only 0.65 mm of slack). Route FIRST, then move the centre, so a
# routing failure stays separable from a placement failure.
BOARD_W, BOARD_L = 61.8, 55.0

# THE MOUNTING EAR was added 2026-09-21 on the user's "having the screw adjacent ...
# doesn't provide as strong of retention", and removed 2026-09-29 on their own report that
# its hole was never used. Both are right: a screw through the board IS better retention,
# and this one could not be reached -- see below. If a through-board mount is wanted again
# it needs a corner whose BOSS clears the nut height-adjust block, which is the thing that
# actually decided it, and that is a placement question before it is an outline one.
# ⚠ THE EAR IS GONE (user, 2026-09-29: this board "has a hole designed for an M4 screw
# that isn't being used"). It was right, and the hole was worse than merely spare:
#   * its boss cannot be used from where it is -- it projects into the nut height-adjust
#     block, 625 mm3 through nut_slide_insert_2 when it was tried, so the one fastening
#     point the board offered was a fastening point that could not be fastened; and
#   * it made the board 70.50 wide instead of 61.80, and src/electronics.py hands that
#     width to pcb_hold_xy. Every hold point on this board was therefore computed against
#     a rectangle the laminate does not occupy -- an unused hole steering the fastener
#     that replaced it.
# The board is a plain rectangle now and the M4 lives beside its edge, same as the Pi's.

BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    # (no outline_poly and no cutouts: with the ear gone the board is exactly outline_mm, and
    # a rectangle is better said by its absence than by four points restating it. No
    # mounting_hole_xy either -- there is no hole in this board to mount through.)
        # J4 going XH moved the router's first pass and OSC_OUT (Y1 -> U4) came back open at the
    # default ten; more passes let it rip up and re-lay (route.py PASSES note)
    "router_passes": 20,
    "layers": 4,
    "thickness_mm": 1.6,
    # SKiDL numbers refs by INSTANTIATION order, not by tag: U1 is the buck,
    # U2/U3 the transceivers, U4 the MCU. Named as they come out.
    # Three 13.49 mm XH courtyards are 40.47 in a row and the board is 40, so the
    # power connector turns 90 onto the +X edge instead of joining the other two.
    # THE BOARD GREW +Y, FROM 35 TO 58, AND THE ORIGINAL LAYOUT DID NOT MOVE.
    # Every pre-merge part keeps its position against the -Y edge (a flat -11.50 in
    # board-local Y, which is where the centre went), so the routing that was already
    # proven is disturbed as little as possible; the 5 V section lives entirely in
    # the strip the growth added.
    # ⚠ BOTH BUCKS' SUPPORT PARTS WERE RE-SEATED AT THEIR PINS, 2026-10-04 (quality M13).
    # Measured on the placed board before: U1's bootstrap capacitor 12 mm from CB / SW, its
    # feedback divider 9-12 mm from FB, its catch diode 8 mm from SW (an asynchronous buck:
    # that diode IS the hot loop); U5's bootstrap capacitor 10 mm out and its divider 8-10.
    # Every one of them is now inside 1.5 mm of the pin it serves:
    #   U1 turned 180 so SW and VIN face the free strip along the -Y edge; C3 between CB
    #   and SW on its east side, L1 next to that, D1 under SW, C23 under VIN, C1 beside it,
    #   R1 / R2 over FB with their FB pads facing the pin.
    #   U5: C20 over BOOT / SW (its SW pad sits ON the declared switch-node track), C19
    #   over VCC, R11 / R10 over FB. L2 moved 1.0 north to open that row.
    # The CAN clamps D2 / D3 moved from 19 mm to 4 mm off J1's pins, and the USB clamps
    # D6 / D7 from a stub south of J4 onto the pair's path east of it.
    # Notes further down that give older sites for these parts are history.
    "placements": {
        "J1": (0.60, -13.50, 90.0),
        # ⚠ J2 MOVED WHEN IT GREW 4-WAY -> 8-WAY (2026-09-22). At its old mid-board site the
        # 17.9 mm body overlapped J1's courtyard and put a PTH pad inside it. This site is
        # elec/sitesearch.py's top-ranked of 672 legal ones, which is the tool that exists
        # because this board "keeps being placed by eye and keeps being wrong" -- and it
        # puts bus B's trunk beside J3's 24 V inlet on the +X edge, where bus A's already is.
        # ⚠ J2 AND J5 SIT ON THE +X EDGE BECAUSE THAT EDGE FACES THE FLOOR. The tray
        # stands (electronics.stand(), +90 about Y), which maps flat +X to world -Z: the
        # board hangs with this edge downward at Z -59.0, with 22.85 mm of air under it
        # before the chassis floor at -81.85. Side entry here mates straight DOWN, through
        # an access hole, which is the whole point of the change -- see _ph4.
        # Nothing else may live on this edge: a cable leaving any other part on it has
        # nowhere to go but into the instrument.
        # ⚠ BOTH PLUGS MUST LAND IN THE ONE FREE BAND, AND THAT SETS THE SPACING. The
        # three mortise stations -X of the full-length lever one are SPLIT: at x -618.10,
        # -607.70 and -597.30 the slot runs y -151.2..-97.1 and again y ~21..67, with the
        # middle free. Only that middle is available to cut into (user, 2026-09-25, with a
        # diagram) -- the full-length mortise at x -586.90 runs y -151.2..46.4 unbroken and
        # a lever has to be installable anywhere along it.
        # The board reaches world y -60.8 at its +Y end, so the usable band is
        # y -97.1..-60.8 = 36.3 mm. At 30 mm centres the pair needs 42 and the -Y one lands
        # at y -109.2, straight over a body-adapter slot. 14 mm centres put both inside:
        # board y 8 and 22 -> world y -86.2 and -72.2, with 31.3 mm of span used of 36.3.
        # The chassis keeps ~4.7 mm between the two holes rather than the 8 I wanted, which
        # is the price of the band being 36 mm wide.
        # ⚠ ON THE +X EDGE, WHICH IS THE NARROW ONE AND THE ONE THAT FACES THE FLOOR, AND THAT IS THE POINT (user,
        # 2026-09-25: "the two JSTs don't take that much room so it seems sensible to put
        # them on the narrower board edge so we have a smaller keep out zone"). The
        # downward edge is sterilised -- no other connector may sit on it, because its
        # cable would point into the chassis through the service hole -- so the cost is
        # proportional to that edge's LENGTH. 46 mm instead of 66.7 to carry the same
        # 24 mm of connector. The board is authored with +X as that edge; see BOARD_W.
        #
        # y -22.92 puts the MOUTHS on the Edge.Cuts at y -29.00: the courtyard reaches
        # 6.08 past the origin on the mouth side, measured off the placed part rather
        # than assumed. (At 20.90 on the +X edge they overhung the board by 3.98 mm --
        # that placement was written against a 54 mm outline that the re-export corrected
        # to 46, and nothing recomputed it.)
        "J2": (24.92, -11.50, 90.0),
        "J6": (24.92, 4.50, 90.0),
        # 6-way since 2026-10-04: centre -2.50 so ways 1-4 (and the 24 V copper declared
        # under them) stay exactly where they were and ways 5 / 6 are added at -X.
        "J3": (9.10, 11.50, 180.0),
        # the bus-B current limit, in the empty strip north of J3: C25 at IN, R22 at ILIM
        # ⚠ THE SOUTH ROW WAS RE-LAID 2026-10-04 (quality A2 / A9), AND THE CRYSTAL IS WHY.
        # Y1 stood at (3.35, -4.25), 12.2 mm of trace from OSC_OUT, with its OSC_IN load
        # capacitor 15 mm away on the far side of the MCU; the oscillator pins are on the
        # SOUTH edge (5 and 6, x 11.0 / 11.4). It is now directly under them: Y1 at
        # (11.20, -14.05) unrotated, so pad 1 (OSC_IN) is its south-west corner and pad 3
        # (OSC_OUT) its north-east, each under 3 mm from its pin, with C4 west and C5 east
        # of it. The 3.9 mm between the MCU's courtyard and the 3V3 buck's row is exactly
        # the crystal's 3.58, which is why the row is at y -14.05 and not a rounder number.
        # What that displaced, and where the supply capacitors went while they were moving:
        #   C7  -> under pins 13 / 17 (VDDA, VIO_4)      C8  -> beside pins 31 / 32
        #   C12 -> between U3 and the MCU: U3's 3V3 pin had no capacitor within 9 mm
        #   C19 -> at U5's VCC pin (was 9.7 mm away)     C6, R7 -> west end of the row
        #   TP1 / TP3 -> the crystal's old site
        "U6": (-3.00, 19.50, 0.0),
        "C29": (8.00, 17.00, 0.0),       # 24 V bypass at the inlet J3
        "C25": (-6.00, 19.50, 90.0),
        "C30": (-1.90, 21.85, 0.0),      # pad 1 over U6 pin 6
        "R22": (0.00, 19.50, 90.0),
        "C27": (-14.00, 17.50, 0.0),     # on the 2 mm +5V bar's north side
        "C28": (25.60, -3.50, 0.0),      # in the 2.7 mm gap between J2 and J6
        # SWD pads -- nearest free 2.5 mm sites to U4; see the note in motor_ctrl()
        "TP1": (3.60, -3.00, 90.0),
        "TP2": (20.60, -23.60, 90.0),    # below TP4: "SWCLK" at full size needs 4.5 mm of clear board
        "TP3": (0.70, -3.00, 90.0),
        "TP4": (20.60, -20.10, 90.0),    # beside TP5, where its name fits at full size
        # ⚠ J2/J6 IN BY 1.10, AND TP5/C15 OUT OF THEIR WAY -- three shorts, three mask
        # bridges and four edge-clearance errors, all pre-existing and all hidden behind a
        # motor_ctrl-drc.rpt dated 2026-09-20 that predates three reworks of this board.
        # The XH mounting pads reached x 31.55 against a +X edge at 30.90 with a 0.30 rule:
        # 0.65 mm of copper off the side of the board. And TP5's pad (23.70..25.20) sat
        # INSIDE J2 pad 3's (22.35..25.85) -- not a near miss, an overlap -- with C15 pad 1
        # doing the same against J2 pad 2.
        # TP5 is a bare SWD pad and C15 is MCU bulk, so neither is pinned to a pin the way
        # an HF bypass is; both move to the nearest site that clears every neighbour by the
        # 0.30 rule.
        "TP5": (24.45, -20.10, 90.0),
        # ⚠ J4 IS OFF THE -Y EDGE NOW: that edge belongs to the bus-B pair alone (see J2).
        # It keeps its top-entry XH and its mating direction -- world +X once standing --
        # so the USB lead still leaves toward the bay; only its seat moved.
        "J4": (-25.90, -16.50, 90.0),
        "U4": (12.60, -7.50, 90.0),
        "U2": (8.10, 2.80, 90.0),
        "U3": (14.60, 2.80, 90.0),
        "U1": (6.60, -19.50, 270.0),
        "L1": (11.80, -19.60, 0.0),
        "D1": (10.40, -22.90, 0.0),
        "C1": (5.60, -24.60, 180.0),
        # ⚠ C23 SITS AS CLOSE TO U1's VIN PIN AS A COURTYARD ALLOWS, and that is the
        # whole specification. Vertical so it clears U1 (right edge -13.905) and TP3
        # (left edge -12.145); its pads land 1.73 mm from the VIN pad, against C1's
        # 11.50 mm through two vias.
        "C23": (6.12, -22.40, 180.0),
        "C2": (15.30, -19.60, 270.0),
        "C3": (9.15, -19.50, 270.0),
        "R1": (6.40, -16.40, 270.0),
        "R2": (5.20, -16.40, 90.0),
        "C6": (6.80, -14.05, 90.0),
        "R7": (5.60, -14.05, 90.0),
        "C7": (15.70, -14.05, 90.0),
        "C8": (18.00, -3.95, 90.0),
        "C9": (6.10, -12.10, 90.0),
        "C10": (6.10, -10.10, 90.0),
        "C11": (6.10, -8.10, 90.0),
        "C12": (15.30, -1.90, 0.0),
        "C13": (6.10, -4.10, 90.0),
        "C14": (6.10, -2.10, 90.0),
        # ⚠ ABOVE U4, BECAUSE THE CORRIDOR BESIDE IT IS 3.46 mm AND THE CRYSTAL IS 3.58.
        # Y1 sat at x 19.60 between U4's courtyard (right edge 17.25) and J2's body
        # (left edge 20.71) and overlapped J2 by 0.69 -- and there is no x that clears
        # both, which is why nudging it failed twice. North of U4 is no better: U2 and
        # U3 sit shoulder to shoulder there with 1.02 mm between them, and EVERY
        # corridor on that side of the board measures 3.37..3.46 mm. This site is the
        # NEAREST of 9974 that a free-space search found -- 2.81 mm off U4's package
        # edge, and nothing on this board is closer. Searched, not guessed: three
        # hand-picked spots in a row landed on C3, then U2/U3, then J1. The alternative was spreading
        # J2/J6 apart in y to open the gap, and that swallows C2 under J2 and JP1 under
        # J6: the +X edge is full. So the crystal moves instead, to free board directly
        # WEST of U4 -- still a short hop to the oscillator pins. ⚠ IF OSC_IN/OSC_OUT
        # COME BACK UNCONNECTED, THIS IS WHY (it happened once before, see the J4 note).
        "Y1": (11.20, -14.05, 0.0),
        "C4": (8.30, -14.05, 90.0),
        "C5": (14.10, -14.05, 90.0),
        "C15": (28.60, -20.25, 90.0),
        "R3": (8.10, 7.70, 90.0),
        "R4": (14.60, 7.70, 90.0),
        "R5": (-3.60, 13.00, 90.0),      # R5 / D2 / D3 moved -3.20 to make room for J3's 6-way
        "JP1": (20.60, 13.00, 90.0),
        "D2": (-3.60, -12.60, 90.0),
        "D3": (-3.60, -9.40, 90.0),
        "D4": (19.60, 6.50, 90.0),
        "D5": (19.60, 9.50, 90.0),
        # ⚠ BESIDE J4, THE USB CONNECTOR THEY CLAMP. They sat at x 27.60, which is
        # 53 mm from it and INSIDE J2's courtyard -- J2 is side entry, so its body lies
        # on the board across x 20.71..31.00 and these were underneath it. The comment
        # they carried ("take R8/R9's old slots") recorded where they were put, not what
        # they are for: an ESD clamp 53 mm downstream of the connector protects the
        # board from nothing, because the transient is already past it. Both faults have
        # the same fix, so the courtyard error was the one that made the other visible.
        "D6": (-21.10, -15.20, 90.0),
        "D7": (-21.10, -18.40, 90.0),
        "C19": (-14.77, -14.70, 90.0),
        "C20": (-16.67, -14.70, 180.0),
        "R10": (-12.45, -14.70, 270.0),
        "R11": (-13.55, -14.70, 90.0),
        "R12": (-5.90, -4.50, 90.0),
        "R13": (-5.90, -0.50, 90.0),
        "F1": (-9.90, -21.50, 90.0),
        "C16": (-9.90, -15.50, 90.0),
        "C17": (-9.90, -9.50, 90.0),
        # ⚠ C18 WAS 18.08 mm FROM THE PIN IT EXISTS TO BYPASS -- the FARTHEST of the
        # three caps on +24V_BUCK, behind the 10 uF bulk at 8.93 and C17 at 13.26. Its
        # own description says "nearest VIN/GND". Nothing checks that a placement honours
        # what a part is FOR, so it drifted and read as decoupling that was present.
        # Now north of U5's VIN pad (-18.475, 20.405), clear of the courtyard's y 21.25.
        "C18": (-18.80, -21.98, 90.0),
        "D8": (-9.90, 1.50, 90.0),
        "F2": (-9.90, 9.50, 90.0),
        "U5": (-15.40, -19.50, 90.0),
        "L2": (-15.40, -9.50, 90.0),
        "D9": (-15.40, -1.50, 90.0),
        "C21": (-15.40, 5.50, 90.0),
        "C22": (-15.40, 10.30, 90.0),
        "J5": (-22.90, -2.60, 90.0),
        # â”€â”€ the LED strip's buck â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # âš  TWO ROWS, AND THE LAND SIZES ARE WHY. Measured off the routed board rather
        # than assumed from the body: L3 (Bourns SRN6028) lands 6.92 x 8.11 and U6's
        # SOIC-8-1EP lands 7.45 x 6.97. Spacing them on the 6x6 BODY put L3's pad 0.69 mm
        # inside U6's and swallowed C27 whole -- four shorting_items and four
        # solder_mask_bridges, on a board that was 0/0 before the buck arrived.
        # Those two parts are ~7-8 mm tall in Y, so they fill a single row by themselves:
        # row A carries them and the other large bodies, row B the passives.
        # âš  THE DIVIDERS STAY AT THEIR PINS. An earlier version put FB and EN 20 mm away
        # and EN_LED came back unconnected; both sit directly above U6 in row B now.
        # âš  HOT LOOP FIRST: C24/C25 sit against U6's VIN and SW runs straight into L3.
        # That loop is what radiates, and this board shares an instrument with a magnetic
        # pickup.
        "F3": (-27.00, 19.70, 0.0),
        "C24": (-21.93, 19.70, 0.0),
        # ⚠ J7 IS OFF THE DOWNWARD EDGE, AND IT WAS OVER IT (user, measured 2026-09-30).
        # board +X is world -Z -- electronics.stand() maps the flat +X edge to the chassis
        # floor -- and the rule written 20 lines above is that this edge "carries the two
        # bus-B JSTs and nothing else, because anything on it would have its cable pointing
        # down through the service hole". J7 was not merely near that edge: its courtyard
        # ran to x 130.96 against an outline at 130.95, so it OVERHUNG the board by 0.01 mm
        # and sat 0.26 mm inside its own clearance. The rule was stated and then not applied
        # to the part added after it, which is the ordinary way a design rule fails.
        # Moved 3.00 mm inboard to the NEAREST site that passes a courtyard sweep with a
        # 2.50 mm keep-off on +X (1.00 elsewhere); it now clears that edge by 2.74 mm, and
        # J2/J6 have it to themselves as intended.
        "J7": (21.21, 19.83, 0.0),
        # row B: the passives, above row A. U6 and L3 are ~7-8 mm tall in Y and fill
        # row A by themselves, so nothing else fits beside them.
        "C26": (11.70, 25.00, 0.0),      # at J7, on C31's old site
        # ⚠ 3.2 mm PITCH, NOT 3.0. At 3.0 the output bulk caps left 0.100 mm between
        # adjacent pads against a 0.127 rule -- 0.027 short, and DRC is right to say so.
        # bring-up sense dividers, in the two strips the board already had free:
        # +5V between U4's courtyard (x 17.25) and J2's (20.71), C4 above and C5 below;
        # +24V between the decoupling row (y -15.46) and L1 (y -17.66), beside C23's +24V.
        "R18": (19.00, -9.00, 90.0),
        "R19": (19.00, -6.50, 90.0),
        "R20": (9.20, -16.55, 0.0),
        "R21": (11.40, -16.55, 0.0),
    },
    "refs_on_fab": True,
    # THE GROUND PLANE is why this is four layers, same as the lever board: the
    # buck switches on a board carrying a 12 MHz USB pair and two CAN pairs.
    "zones": [("GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],
    # ⚠ +24V IS A PASS-THROUGH ON THIS BOARD, NOT A LOCAL SUPPLY. v24 reaches J1 and J2 as
    # well as the inlet J3, so the drivers' current crosses this PCB on its way to the
    # motors -- BOM.md's "very nearly the whole <5 A". At the board default of 0.25 mm
    # that is 0.88 A of 1 oz outer copper by IPC-2221 at a 10 C rise, about 5.7x short,
    # and it went unnoticed because until now no board could state a per-net width at all.
    # The audit that found it also cleared the other two: optical's inlet is ~324 mA
    # against 0.88 A, and lever_sensor's 0.15 mm pass-through is 0.60 A on the sensor bus.
    #
    # 0.5 mm takes it to 1.45 A. That is the ceiling for a blanket width here for the same
    # reason as on the panel -- this net lands on 0402 parts with 0.6 mm pads and
    # freerouting does not neck into a land -- so it is an improvement, not the answer.
    # The J3 -> J1/J2 path still wants deliberate copper; see the trunk note on
    # output_panel for why that is a pinout decision rather than a routing one.
    # GND needs nothing: it has plane copper on In1.Cu and a pour on B.Cu.
    # +24V_LED is the lighting bus after F3: 1.63 A worst case, so it gets the same 0.5 mm
    # (1.45 A at a 10 C rise; the worst case is every LED at full white, software-capped).
    # +5V_BUSB: 0.52 A limited, 0.4 mm (1.2 A).
    "net_widths": {"+24V": 0.5, "+24V_LED": 0.5, "+5V_BUSB": 0.4},
    # THE BUS-A WEST FEED CROSSES THIS BOARD: J3 (inlet) -> J1 (bus A out). The router laid
    # it as 35.9 mm of In2.Cu + 20.7 mm of F.Cu at 0.5 mm, ~91 mOhm, which split the dual
    # feed ~64 / 36 and put up to 2.9 A (ten movers) on copper good for 1.45 A. So that one
    # path is DECLARED: a 2.0 mm B.Cu bar (1 oz outer, ~4 A at a 10 C rise), 45.5 mm,
    # ~11 mOhm, down the one B.Cu corridor that was empty on the routed board except for a
    # four-track band at y -7..-8 the router now has to hop. The rest of the net (fuses,
    # buck input, sense divider) stays the router's at 0.5 mm.
    "tracks": [
        ("+24V", "B.Cu", 2.0, [(12.85, 11.5), (12.85, 3.0), (11.85, 2.0), (-1.0, 2.0),
                               (-2.0, 1.0), (-2.0, -13.75), (-1.0, -14.75), (0.6, -14.75)]),
        ("+24V", "B.Cu", 1.2, [(10.35, 11.5), (12.85, 11.5)]),      # J3's two 24 V ways tied
        # THE PI'S 5 V SUPPLY, DECLARED (2026-10-01). U5 is a 3 A buck behind a 4 A fuse and
        # the router drew its whole power path -- 24 V in, the switch node, the inductor's
        # output, the fuse, the run to J5 -- at the board default, 0.25 mm (0.88 A at a
        # 10 C rise), and the feed to F1 at 0.2. `net_widths` is the wrong tool: these nets
        # also land on 0402s (the FB divider, the boot cap) and freerouting does not neck
        # into a land. So the CURRENT PATH is drawn here and the sense/boot branches stay
        # the router's. Lanes sit in the gaps between the part columns at x -15.4 / -9.9:
        #   24 V -> F1: 0.6 mm (1.6 A; the buck draws ~0.8 A at full load)
        ("+24V", "F.Cu", 0.6, [(0.6, -14.75), (-7.9, -14.75), (-7.9, -22.9), (-9.9, -22.9)]),
        #   F1 -> C16 -> C17, and round U5's south end to VIN and its 100 nF
        ("+24V_BUCK", "F.Cu", 1.0, [(-9.9, -20.1), (-9.9, -16.97)]),
        ("+24V_BUCK", "F.Cu", 0.6, [(-9.9, -20.1), (-11.6, -20.1)]),
        ("+24V_BUCK", "F.Cu", 0.6, [(-9.9, -16.97), (-11.6, -16.97)]),
        ("+24V_BUCK", "F.Cu", 0.6, [(-11.6, -24.4), (-11.6, -10.97), (-9.9, -10.97)]),
        ("+24V_BUCK", "F.Cu", 0.5, [(-11.6, -24.4), (-18.8, -24.4), (-18.8, -22.46)]),
        ("+24V_BUCK", "F.Cu", 0.5, [(-16.03, -24.4), (-16.03, -21.97)]),
        #   the switch node: short and straight into the inductor's land
        ("SW5", "F.Cu", 0.6, [(-17.31, -17.03), (-17.31, -11.6), (-15.4, -11.6)]),
        #   inductor -> output caps -> F2: 2 mm (3.95 A)
        ("+5V_RAW", "F.Cu", 2.0, [(-15.4, -7.4), (-12.525, -7.4), (-12.525, 8.1)]),
        ("+5V_RAW", "F.Cu", 1.4, [(-12.525, 8.1), (-9.9, 8.1)]),     # 3 A wants 1.37
        ("+5V_RAW", "F.Cu", 1.0, [(-12.525, 4.025), (-15.4, 4.025)]),
        ("+5V_RAW", "F.Cu", 1.0, [(-12.525, 8.1), (-13.25, 8.825), (-15.4, 8.825)]),
        #   F2 -> J5 (the Pi) and the TVS D9: 2 mm, over the top of the cap column
        ("+5V", "F.Cu", 1.5, [(-9.9, 10.9), (-9.9, 13.8)]),
        ("+5V", "F.Cu", 2.0, [(-9.9, 13.8), (-19.2, 13.8), (-19.2, -3.85)]),
        ("+5V", "F.Cu", 1.5, [(-19.2, -3.85), (-22.9, -3.85)]),
        ("+5V", "F.Cu", 1.5, [(-19.2, -1.35), (-22.9, -1.35)]),
        ("+5V", "F.Cu", 1.5, [(-19.2, -3.65), (-15.4, -3.65)]),
        #   the TVS D8 (and the EN divider behind it) straight off the 2 mm bar: the router
        #   left that island open once the lanes above were in its way
        ("+24V", "F.Cu", 0.6, [(-2.0, 1.0), (-2.75, 1.75), (-8.0, 1.75), (-8.0, 0.2), (-9.9, 0.2)]),
    ],
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
    # ⚠ AND A PLANE NEEDS STITCHING TO IT. Declaring In1 a plane is only half the
    # job: it stops the router carrying ground THROUGH the plane, and then nothing
    # connects the ground pads TO it. Declared alone it stranded six GND pads on this
    # board -- the pour reaches them, but a pour is what routing can orphan, which is
    # the whole reason the plane is there. Every GND pad gets its own via down.
    "stitch_nets": ("GND",),
    "single_sided": True,
    "qty_per_instrument": 1,
}

# the via that drops the D8 link (see "tracks") onto the 2 mm B.Cu bar
BOARD_NOTES["vias"] = list(BOARD_NOTES.get("vias", [])) + [("+24V", -2.0, 1.0)]

# THREE PINS LEAVE U4 INWARD, DECLARED TOGETHER (2026-10-04). Pins 7 / 8 / 9 (NRST,
# SENSE_24V, PG_5V) face the crystal: OSC_IN and OSC_OUT leave either side of them and
# Y1's lands close the row 1.2 mm out, so there is no outward lane. Inward there is one
# slot, 1.05 mm between the pin row and the belly land, and it holds a 0.6 mm via with
# 0.16 / 0.17 mm either side -- but only three abreast if they are spaced on purpose.
# Left to the router it took the slot for two of the three and reported the third open,
# a different one each run. So all three are drawn: 0.87 mm apart, each reached by a
# 0.15 mm track that leaves its own pin at 45 degrees (0.137 mm off the next pin's corner).
BOARD_NOTES["vias"] += [("NRST", 11.33, -10.56), ("SENSE_24V", 12.20, -10.56),
                        ("PG_5V", 13.07, -10.56)]
BOARD_NOTES["tracks"] += [
    ("NRST", "F.Cu", 0.15, [(11.80, -11.44), (11.80, -11.03), (11.33, -10.56)]),
    ("SENSE_24V", "F.Cu", 0.15, [(12.20, -11.44), (12.20, -10.56)]),
    ("PG_5V", "F.Cu", 0.15, [(12.60, -11.44), (12.60, -11.03), (13.07, -10.56)]),
]

# U5's PG pin is walled in on its own layer: the thermal pad north, EN west, and the
# declared input copper south and east. The router has no way out of that pocket it will
# find twice running, so the pin drops straight to an inner layer in the 1.3 mm between
# itself and the input bar.
BOARD_NOTES["vias"] += [("PG_5V", -12.52, -21.98)]

# U5'S HEAT GOES DOWN THROUGH FIVE VIAS, FOUR OF THEM BESIDE THE PAD. The stitcher gives the
# thermal pad one via; a second inside it would swallow the paste (quality A12 counts the
# barrel). So the pad is extended 0.7 mm past each open end on F.Cu and the vias stand
# there, two a side, clear of the SW and FB pins by 0.6 mm.
BOARD_NOTES["vias"] += [("GND", -17.60, -20.10), ("GND", -17.60, -18.90),
                        ("GND", -13.20, -20.10), ("GND", -13.20, -18.90)]
BOARD_NOTES["tracks"] += [
    ("GND", "F.Cu", 0.8, [(-17.60, -20.10), (-13.20, -20.10)]),
    ("GND", "F.Cu", 0.8, [(-17.60, -18.90), (-13.20, -18.90)]),
]
BOARD_NOTES["tracks"] += [("PG_5V", "F.Cu", 0.25, [(-13.50, -21.98), (-12.52, -21.98)])]

# THE NORTH STRIP'S THREE SUPPLY PATHS, DECLARED (quality A1 / A12, 2026-10-04). Left to the
# router: the lighting bus's 1.63 A ran on 0.5 mm (0.59 wanted) and squeezed between two of
# J3's pins; that feed, drawn straight across at y 16.3, walled U6 and C27 off from the 5 V
# bar, so their 0.57 A came up through a via INSIDE C27's land and 0.2 mm of inner copper.
#   24 V to F3: out of J3's second 24 V pin northward, 0.7 mm, along y 16.1
#   F3 -> C24 -> J7: 0.6 mm round the north edge, entering J7 from above (not between pins)
#   5 V to C27 / U6: off the 2 mm bar, UNDER the 24 V lane on B.Cu between two vias that
#   sit beside the lands, then 0.5 mm along y 18.94 to C25 and into U6's IN (pin 1)
BOARD_NOTES["vias"] += [("+5V", -14.95, 15.2), ("+5V", -16.2, 17.5)]
BOARD_NOTES["tracks"] += [
    ("+24V", "F.Cu", 0.7, [(10.35, 11.5), (10.35, 14.7), (8.95, 16.1), (-24.8, 16.1),
                           (-28.4, 19.7)]),
    ("+24V", "F.Cu", 0.3, [(7.52, 16.1), (7.52, 17.0)]),                # C29
    ("+24V_LED", "F.Cu", 0.6, [(-25.6, 19.7), (-23.41, 19.7), (-22.08, 18.37),
                               (-19.31, 18.37), (-12.69, 25.0), (9.9, 25.0),
                               (13.53, 21.37), (19.96, 21.37), (19.96, 19.83)]),
    ("+24V_LED", "F.Cu", 0.5, [(9.9, 25.0), (11.22, 25.0)]),            # C26
    ("+5V", "F.Cu", 0.6, [(-14.95, 13.8), (-14.95, 15.2)]),
    ("+5V", "B.Cu", 0.6, [(-14.95, 15.2), (-16.2, 16.45), (-16.2, 17.5)]),
    ("+5V", "F.Cu", 0.6, [(-16.2, 17.5), (-14.95, 17.5)]),
    ("+5V", "F.Cu", 0.5, [(-14.95, 17.5), (-13.51, 18.94), (-6.0, 18.94)]),
    ("+5V", "F.Cu", 0.4, [(-6.0, 18.94), (-5.25, 18.94), (-5.25, 20.0), (-4.8, 20.45),
                          (-4.14, 20.45)]),
]

# short words for the pin legends: a legend is as wide as its longest net name
BOARD_NOTES["silk_labels"] = {"PWR_SW_UP": "SW UP", "PWR_SW_DN": "SW DN", "+24V_LED": "24V",
                              "+5V_BUSB": "5V", "+24V": "24V", "+5V": "5V"}

BOARD_NOTES["quality"] = {
    "power_paths": [
        # the inlet from output_panel, two XH contacts. Bus A's west feed is the big one:
        # up to 2.9 A with ten movers slewing (the dual-feed split, see "tracks")
        {"net": "+24V", "from": "J3.2", "to": ["J1.2"], "amps": 2.9},
        {"net": "+24V", "from": "J3.2", "to": ["J3.3"], "amps": 2.7},
        # the Pi's buck: 15 W out at ~88 % is 0.71 A at 24 V; F1 is 1 A
        {"net": "+24V", "from": "J3.2", "to": ["F1.1"], "amps": 0.8},
        {"net": "+24V_BUCK", "from": "F1.2", "to": ["U5.2"], "amps": 0.8},
        # the lighting bus, every zone at full white (docs/lighting-bus.md); F3 is 3 A
        {"net": "+24V", "from": "J3.2", "to": ["F3.1"], "amps": 1.63},
        {"net": "+24V_LED", "from": "F3.2", "to": ["J7.2"], "amps": 1.63},
        # the 3V3 buck's input: 0.2 A of 3V3 is 30 mA at 24 V
        {"net": "+24V", "from": "J3.2", "to": ["U1.5"], "amps": 0.1},
        # U5's output, 3 A rated, through F2 (4 A) to the Pi on J5's two contacts
        {"net": "+5V_RAW", "from": "L2.2", "to": ["F2.1"], "amps": 3.0},
        {"net": "+5V", "from": "F2.2", "to": ["J5.2", "J5.3"], "amps": 3.0},
        # bus B's limiter: 565 mA is the TPS2553's maximum limit at 49.9 k
        {"net": "+5V", "from": "F2.2", "to": ["U6.1"], "amps": 0.57},
        {"net": "+5V_BUSB", "from": "U6.6", "to": ["J2.2", "J6.2"], "amps": 0.57},
        # the MCU (~120 mA at 144 MHz with both CANs and USB) and two transceivers
        {"net": "+3V3", "from": "L1.2", "to": ["U4.1", "U2.3", "U3.3"], "amps": 0.25},
    ],
    # the power button's two throws pass straight through, J7 to J3: a few mA of pull-up
    # from the output panel. VCC5 is U5's internal regulator pin and its one capacitor.
    "not_power": ("PWR_SW_UP", "PWR_SW_DN", "VCC5"),
    "unmatched_ok": {
        "USB_DP": "full speed, 12 Mbit/s: a bit is 83 ns and the pair is under 40 mm, so "
                  "its whole length is 0.25 ns and no skew it could have is 1 % of a bit",
    },
    "pinouts": {
        "B4B-XH-A": "JST eXH.pdf p.5, Header / Top entry type: seen from the slotted wall "
                    "(the wall 2.35 mm from the posts), No. 1 circuit is the right-hand "
                    "post. KiCad JST_XH_B4B-XH-A has that wall at -Y and pad 1 at the -X "
                    "end: the same post. Way names from harness (XH_PINOUT, LIGHTS_LINK, "
                    "PI_5V_LINK); J4 is USB's own order, 1 VBUS 2 D- 3 D+ 4 GND. Read "
                    "2026-10-04",
        "B6B-XH-A": "the same JST drawing and the same KiCad family as the 4-way (eXH.pdf "
                    "p.5; pad 1 at the -X end, slotted wall -Y). Way names are "
                    "harness.PWR_LINK, the list output_panel J10 is built from",
        "S4B-PH-SM4-TB": "JST ePH.pdf p.4, SMT side entry: looking into the mouth with the "
                         "board below, No. 1 circuit is on the left. KiCad "
                         "JST_PH_S4B-PH-SM4-TB: mouth +Y, pad 1 at -X -- the same end. "
                         "Way names from harness.PH_PINOUT. Read 2026-10-04",
        "LMR16006XDDCR": "TI SNVSA24 section 6, Pin Functions (SOT-23-6): 1 CB, 2 GND, 3 FB, "
                         "4 SHDN, 5 VIN, 6 SW. Board: 1 CB, 2 GND, 3 FB, 4 open (float = "
                         "enabled, same table), 5 +24V, 6 SW. Re-read 2026-10-04",
        "SN65HVD230DR": "TI SLOS346 Pin Functions (SOIC-8): 1 D, 2 GND, 3 VCC, 4 R, 5 Vref, "
                        "6 CANL, 7 CANH, 8 RS. Board: 1 CANn_TX, 2 GND, 3 +3V3, 4 CANn_RX, "
                        "5 open, 6 L, 7 H, 8 slope resistor. Re-read 2026-10-04",
        "CH32V307WCU6": "WCH CH32V303/305/307/317 datasheet V3.4 p.21, the CH32V307WCU6 "
                        "pin drawing, read pin by pin against the placed board 2026-10-04: "
                        "1 VBAT, 5 OSC_IN, 6 OSC_OUT, 7 NRST, 8 PC0, 9 PC1, 12 VSSA, "
                        "13 VDDA, 17 VIO_4, 18 VSS_1, 20 PA4, 31 VIO_1, 32 VDD_1, 35 PB12, "
                        "36 PB13, 39 PC6, 46 PA11/USB1DM, 47 PA12/USB1DP, 48 PA13/SWDIO, "
                        "49 VSS_2, 50 VDD_2, 51 VIO_2, 52 PA14/SWCLK, 63 BOOT0, 64 PB8, "
                        "65 PB9, 67 VIO_3, 68 VDD_3, pad 0 VSS (KiCad's pad 69). All 28 "
                        "connected pads agree",
        "LMR33630ADDAR": "TI SNVSAN3F Table 6-1, HSOIC (DDA) column: 1 PGND, 2 VIN, 3 EN, "
                         "4 PG, 5 FB, 6 VCC, 7 BOOT, 8 SW, thermal pad AGND. Board: 1 GND, "
                         "2 +24V_BUCK, 3 EN5, 4 PG_5V, 5 FB5, 6 VCC5, 7 BOOT5, 8 SW5, "
                         "9 GND. Re-read 2026-10-04",
        "TPS2553DBVR": "TI SLVS841F p.5, DBV package: 1 IN, 2 GND, 3 EN (active high on "
                       "the 2553), 4 FAULT, 5 ILIM, 6 OUT. Board: 1 +5V, 2 GND, 3 +5V, "
                       "4 BUSB_FAULT_N, 5 BUSB_ILIM, 6 +5V_BUSB. Read 2026-10-04",
        "TAXM8M4RFDCET2T": "Yajingxin TAXM8M4RFDCET2T sheet (LCSC C403948), 'Connection' "
                           "drawing: lands 1 and 3 are the crystal, 2 and 4 the can (GND). "
                           "Board: 1 OSC_IN, 3 OSC_OUT, 2 / 4 GND. Read 2026-10-04",
        "VLS6045EX-6R8M": "two-pad, unpolarised",
        "PNR3015-470M": "two-pad, unpolarised",
    },
    "manual": {
        "M1": "five cables, each a straight lead, each end built from one list. J1 -> the "
              "motor tees: harness.XH_PINOUT (GND, 24 V, CAN_H, CAN_L). J2 / J6 -> the "
              "pedal and lever chains: harness.PH_PINOUT (GND, 5 V, CAN_H, CAN_L). J3 <- "
              "output_panel J10: harness.PWR_LINK (GND, 24, 24, GND, SW_UP, SW_DN). J7 -> "
              "pi_cap J4: harness.LIGHTS_LINK (GND, 24, SW_UP, SW_DN). J5 -> pi_cap J2: "
              "harness.PI_5V_LINK (GND, 5, 5, GND). J4 is a bought USB-A lead: 1 VBUS "
              "(open here), 2 D-, 3 D+, 4 GND. Every housing is polarised; the 6-way "
              "cannot enter a 4-way; PH cannot enter XH. Three 4-way XH on this board "
              "carry three different things (J1, J5, J7) and J4 a fourth: each is named "
              "on the silk beside it and in INSTALL_NOTES",
        "M2": "D1 (B5819W): pad 1 is K in KiCad's D_SOD-123 and is on SW, anode on GND. "
              "D8 (SMAJ30A) pad 1 = K on +24V; D9 (SMBJ5.0A) pad 1 = K on +5V; both "
              "unidirectional, anode to GND. D2-D7 are bidirectional. No electrolytic or "
              "tantalum part. Reel rotation is ROTATION-CHECK.txt's job at order (M12)",
        "M3": "In1 is an unbroken GND plane (plane_layers) under every supply path above, "
              "with a GND pour on B.Cu; every ground pad has its own via to the plane. "
              "The 2.9 A bus-A feed returns J1.1 -> plane -> J3.1 / J3.4 directly under "
              "its own B.Cu bar. No slot, no split",
        "M4": "U1 (LMR16006, SNVSA24 9.2.2): CIN 4.7 uF / 50 V + 100 nF at the pin "
              "(asks 1-10 uF); COUT 10 uF / 16 V at 3.3 V plus the MCU's 10 uF and nine "
              "100 nF on the same rail (asks 4.7-100 uF, ESR under 0.7 ohm). U5 "
              "(LMR33630, SNVSAN3F table 9-2, 400 kHz / 5 V row): CIN 2 x 10 uF / 50 V "
              "1206 + 100 nF (asks 10 uF + 220 nF; about 9 uF left at 24 V of bias); "
              "COUT 2 x 22 uF / 25 V 1206 + 10 uF behind F2, about 37 uF at 5 V of bias "
              "against equation 6's 37.5 uF for a 1.5 A step inside 250 mV -- the Pi's "
              "own bulk and pi_cap's 22 uF are the margin. U6: 100 nF in, 1 uF at OUT, "
              "10 uF at the connectors. Every capacitor on a 24 V net is a 50 V part",
        "M5": "24 V nets: capacitors 50 V, fuses 63 V, U1 60 V, U5 36 V operating / 38 V "
              "absolute, R12 and R20 0402 (50 V) at 4 and 5 mW. D8 stands off 30 V so "
              "motor regeneration does not hold it in conduction, breaks down at 33.3-"
              "36.8 V and reaches U5's 38 V at about 1 A of surge; U5 sits behind F1 with "
              "20 uF at its pin, which a fast spike has to charge first (a 1 uH, 5 A "
              "kick is 12 uJ: 30 mV). 5 V nets: 16 and 25 V capacitors, D9 clamps at "
              "9.2 V and opens F2. MCU pins: SENSE_24V is 2.18 V at 24 V and 3.3 V only "
              "at 36 V; SENSE_5V 2.5 V. CAN pins: -4..16 V, clamped by D2-D5 near 10 V",
        "M6": "nothing here is fast: CAN at 1 Mbit/s and full-speed USB (A3 has the "
              "arithmetic). No clocked parallel bus",
        "M7": "U1: 0.765 V x (1 + 100k / 30.1k) = 3.31 V; 47 uH gives 87 mA of ripple, "
              "35 % of the 0.25 A load (asks 30-40 %); bootstrap 100 nF; SHDN floating = "
              "enabled; catch diode 40 V / 1 A (asks 1.25 x VIN and the load current). "
              "U5: 1.0 V x (1 + 100k / 24.9k) = 5.02 V, TI's own 5 V divider; 6.8 uH "
              "against the table's 8; BOOT 100 nF, VCC 1 uF; EN from a 137k / 10k divider "
              "(on at 18.1 V); pad on GND. U6: RILIM 49.9k is inside 15k-232k; EN tied "
              "to IN. U2 / U3: RS through 10k to GND = slope control; Vref open",
        "M8": "BOOT0: R7, 10k to GND. NRST: the MCU's own 40k pull-up + C6 100 nF. "
              "BOOT1 (PB2) is read only when BOOT0 is high. U5 EN: divider. U6 EN: tied "
              "to IN; ILIM: R22. U2 / U3 RS: 10k to GND. FAULT and PG are open-drain "
              "into MCU pins that firmware sets input-with-pull-up (noted at both nets)",
        "M9": "SWD on bare 1.5 mm pads TP1 SWDIO, TP2 SWCLK, TP3 NRST, TP4 GND, TP5 3V3, "
              "all labelled, on the front. 24 V and 5 V are probed on the through-hole "
              "pins of J3 and J5, and the board reports both itself (SENSE_24V, SENSE_5V, "
              "PG_5V, BUSB_FAULT_N) over USB",
        "M10": "bus A and bus B pins: D2-D5, bidirectional 5 V clamps 4 mm from J1 and "
               "1.3 mm from J6 (J2 shares J6's node, 15 mm of track away). USB: D6 / D7, "
               "0.5 pF, on the pair 5 mm from J4. 24 V in: D8; this board does not fuse "
               "the trunk because it is in the middle of a ring fed from both ends -- the "
               "supply's own limit is the protection, and the three branches that end "
               "here are each fused (F1, F3) or limited (U6). Reverse polarity: every "
               "connector is a polarised JST on a made harness. Bus B's 5 V, the one "
               "rail a hand can reach (the leg's spring pins), is behind U6",
        "M13": "measured on the routed board, pad edge to pad edge. U1: C23 to VIN 0.8 mm "
               "on the part's own layer, its ground pad on its own via to the plane 3 mm "
               "from the GND pin; D1 cathode 1.1 mm from SW, its anode on its own via; L1 "
               "2.5 mm from SW; C3 between CB and SW, 1.0 mm from each; R1 / R2 0.5 mm "
               "from FB with only their FB pads at the pin. U5: C18 0.9 mm from PGND and "
               "2.2 from VIN, same layer, no via in the loop; SW to L2 on declared 0.6 mm "
               "track, 7.3 mm for a 3.5 mm gap (it leaves the pin away from the feedback "
               "side); C20 1.0 mm from BOOT with its other pad on that track; C19 0.6 mm "
               "from VCC; R10 / R11 0.6 and 0.7 mm from FB. Neither feedback node runs "
               "under an inductor or beside a switch node: U5's leaves on the far side "
               "of the package from SW",
        "M14": "L1 (PNR3015-470M): peak 0.25 + 0.087 / 2 = 0.29 A against 0.88 A "
               "saturation, 0.58 A rms; the IC's limit is 1.2 A, above it -- accepted, "
               "no 3015 part reaches that and a shorted 3V3 trips the IC thermally. "
               "L2 (VLS6045EX-6R8M): ripple 1.46 A, peak 3.73 A at 3 A, against 4.7 A "
               "saturation (TDK, 30 % drop) and 3.6 A rms; the high-side limit is 4.5 A "
               "typical, 5.05 maximum",
        "M15": "both converters are internally compensated for ceramic outputs. U1: "
               "about 17 uF effective on 3V3 against the 4.7-100 uF the datasheet gives. "
               "U5: about 37 uF effective against a table row of 4 x 22 uF nominal "
               "(roughly 44 uF at bias), plus the Pi's bulk across 150 mm of cable. "
               "Headroom: 24 V in for 3.3 and 5 V out. No linear regulator",
        "M16": "J3 is plugged with the supply off, inside the instrument, and the supply "
               "now arrives through the output panel's switch, which ramps it at about "
               "1.5 V/ms: no ring. Were it plugged live, 48 V lands on 50 V capacitors, "
               "a 60 V buck and D8; U5 (38 V) is behind F1 and its own 20 uF",
        "M18": "one supply feeds everything: the Pi is powered FROM this board, so its "
               "USB cannot be up while this board is down; every CAN node is on the same "
               "24 V. The two switch lines touch no pin here. A debug probe on the SWD "
               "pads is used with the board powered",
        "M20": "bus A ends here: R5, 120 ohm 1 %, across the pair through JP1 (closed at "
               "assembly -- INSTALL_NOTES); the other 120 is on the last motor tee. Bus B "
               "passes through (J2 in, J6 out) and is NOT terminated here: its two fixed "
               "120 ohm sit at the far ends. Stubs to U2 / U3 are under 25 mm",
        "M21": "the only converter is the MCU's ADC reading two dividers. VSSA and VSS "
               "join at the part on the In1 plane; VDDA has its own 100 nF. SENSE_24V "
               "leaves pin 8 on a declared escape and runs on an inner layer away from "
               "both inductors. Source impedance is 9.1k and 5k: firmware uses the "
               "longest sample time",
        "M22": "no op-amp on the board",
        "M24": "Y1 TAXM8M4RFDCET2T: CL 12 pF, ESR 250 ohm max, C0 5 pF max. C4 = C5 = "
               "15 pF C0G: 15 / 2 + about 4 pF of pin and track = 11.5 pF. Gain: gm_crit "
               "= 4 x 250 x (2 pi 8 MHz)^2 x (17 pF)^2 = 0.73 mA/V against the MCU's "
               "17 mA/V (WCH V3.4 table 4-12): 23 times, where 5 is the test. The crystal "
               "is 0.8 mm from OSC_OUT and 2.5 mm from OSC_IN with its capacitors beside it; A9 "
               "measures the distance",
        "M25": "U5 is the only part that needs its pad: about 1.7 W at 3 A out (TI's "
               "efficiency curve, 24 V in, 5 V, 400 kHz: 90 %). The pad is on GND with "
               "five vias to the In1 plane 0.2 mm below -- one inside it and two at each "
               "open end, joined to it by 0.8 mm copper (declared, see the vias note) -- "
               "about 22 C/W each over that depth, 4.4 C/W together, 7 C at full load, "
               "into an unbroken 62 x 55 mm plane. More vias INSIDE the pad would take "
               "the paste (A12): the four are beside it for that reason. The MCU's pad "
               "is its ground, about 0.1 W; nothing else on the board has one",
        "M26": "bus A: PB9 = CAN1_TX (remap) -> U2 pin 1 D, the driver INPUT; U2 pin 4 R, "
               "the receiver OUTPUT -> PB8 = CAN1_RX. Bus B: PB13 = CAN2_TX -> U3 D; U3 R "
               "-> PB12 = CAN2_RX. MCU functions from WCH's table 3-1, transceiver pins "
               "from SLOS346. No UART or SPI leaves the board",
        "M27": "BOOT0: R7 and the MCU pin, nothing else. NRST: C6, TP3. SWDIO / SWCLK: "
               "their pads only. PB2 / BOOT1: unconnected",
        "M28": "TI: LMR16006XDDCR C87080, LMR33630ADDAR C841384 (the DDA / HSOIC column, "
               "not the VQFN one), TPS2553DBVR C55266 (the constant-current part, not "
               "the -1 latch-off), SN65HVD230DR C12084. WCH CH32V307WCU6 C5142795. "
               "Yajingxin TAXM8M4RFDCET2T C403948. JST B4B / B6B-XH-A, S4B-PH-SM4-TB. "
               "Each pinout above is from that maker's sheet for that ordering code",
        "M31": "name and revision on the front; every connector's way names on the back "
               "beside its tails; the five SWD pads and JP1 (TERM) labelled on the "
               "front. Pin-1 marks are the footprints', outside the bodies",
        "M34": "U5 EN is active high (on above 1.23 V); U6 EN active high, tied to IN; "
               "U1 SHDN is active low and floats high. FAULT and PG are open-drain, "
               "active low, into 3.3 V pins with internal pull-ups, never above 3.3 V. "
               "CAN: U2 pin 7 CANH -> J1 way 3 CAN_H, pin 6 CANL -> way 4; U3 the same to "
               "J2 / J6. Transceiver logic and the MCU are both 3.3 V. USB D+ on PA12, "
               "D- on PA11",
        "M36": "bus B's 5 V: U6, 0.52 A, constant current. 24 V to the lights: F3, 3 A. "
               "5 V to the Pi: F2, 4 A, with D9. 24 V to bus A on J1 is the trunk itself "
               "and is deliberately not fused here (M10): the supply's limit covers it",
        "M38": "0402 parts lie along the nearest edge; the nearest capacitor to an edge "
               "is over 2 mm in; the outline is routed, no V-score, and there is no "
               "screw through the board (the M4 sits beside its edge). J2 / J6 mate "
               "downward through the chassis access hole, the five XH upward into the "
               "bay; the SWD pads are on the same open face",
        "M39": "U2 / U3 pin 5 (Vref) is an output and is left open, as SLOS346 allows. "
               "U1 pin 4 (SHDN) floats = enabled, per its pin table. J4 way 1 (VBUS) is "
               "open on purpose. The MCU's 40 unused pins have no pads: firmware sets "
               "them input-with-pull-down at start-up. No spare was brought out -- the "
               "board talks over USB and both CAN buses already",
        "M40": "every resistor is an E96 value (137k, 49k9, 30k1, 24k9) or E12. The parts "
               "that must not be swapped say so where they are defined: L2 (saturation), "
               "U6 (constant-current, not the -1), Y1 (CL 12 pF), the 50 V capacitors on "
               "24 V, R22 (the current limit). Nothing needs a heatsink; U5's pad is GND",
    },
}


if __name__ == "__main__":
    motor_ctrl(tag="ctrl")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "motor_ctrl.net"))
    netcheck.grounds_meet(os.path.join(OUT_DIR, "motor_ctrl.net"))
    netcheck.no_orphan_pins(os.path.join(OUT_DIR, "motor_ctrl.net"))
    with open(os.path.join(OUT_DIR, "motor_ctrl.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"])))
