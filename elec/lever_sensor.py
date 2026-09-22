"""Lever / pedal sensor board — MT6701 angle sensor + CAN node, x8.

    py -3.12 elec/lever_sensor.py       # -> elec/out/lever_sensor.{net,board.json}

ONE BOARD FOR EVERY CONTROL: five knee levers and three foot pedals. It reads the
pivot angle off a diametric magnet on the axle and puts it on CAN bus B.

IT ABSORBS THE BUS-B TEE (user). Earlier rounds hung each lever off a trunk tee by
a single 4-way drop; the trunk now passes THROUGH the board, in on one half of an
8-way connector and out on the other. That deletes eight tee boards and eight
cradles. THE COST, stated once because it is real: a daisy chain means unplugging
one lever breaks the bus for everything downstream of it, which is exactly the
property the trunk-and-drop topology was chosen to have.

WHY AN 8-WAY PH AND NOT TWO 4-WAY XH. Two S4B-XH-SM4-TB need 31.0 mm of board
height stacked (the window is 26.10) or 27.2 of the 28 mm width laid in line,
which leaves nothing for the circuit. The 8-way XH fits on paper at 25.0 but LCSC
stocks only the 4-way. S8B-PH-SM4-TB is 19.9 long, 20,215 in stock, takes the
trunk's existing 26 AWG mid-range (30-24), and keeps a same-family fallback --
S8B-PH-K-S, the THT right-angle PH -- that would cost a footprint change and NO
harness change at all. PHD 2x4 is smaller still and was rejected on sourcing:
niche dual-row contacts against PH's commodity ones.

THE CHIP'S POSITION IS NOT NEGOTIABLE. MT6701 sensing centre = package geometric
centre, and it must sit on the axle axis. Everything else is placed around it.

EVERY PIN NUMBER BELOW IS OFF THE DATASHEET, not a library symbol -- see the
per-part notes. Getting one wrong is the failure this file exists to prevent.

⚠ RE-SPUN 2026-09-21 TO branner's SPEC (docs/lever-sensor-respin.md), user decisions:
  * the lever bus runs at 5 V -- the 24 V buck (U1 LMR16006, L1, D1, C1-C3, R1/R2) is
    gone, and a 5 V -> 3V3 LDO (AP2112K) takes its place
  * J1 is PH again: S8B-PH-SM4-TB (LCSC C265121), SMT side entry, on the magnet face, on
    end with its mouth -X -- a different family from the 24 V XH tees, so no harness can
    put 24 V on a lever board
  * the outline is the spec's 31.0 x 21.9, trimmed at +X and at the top
The paragraph above on why PH is right again; the XH interlude it replaced is in git.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import json  # noqa: E402
import re  # noqa: E402

from skidl import ERC, Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

import harness                                      # noqa: E402
import netcheck                                     # noqa: E402

P = Pin.types.PASSIVE
I, O, PWR, PIN = Pin.types.INPUT, Pin.types.OUTPUT, Pin.types.PWRIN, Pin.types.PWRIN

# ── the board ────────────────────────────────────────────────────────────────
# ⚠ THE OUTLINE IS branner's RE-SPIN SPEC, NOT AN OUTPUT OF THIS FILE (docs/lever-sensor-
# respin.md, 2026-09-21). In the spec's frame -- origin on the MT6701, +X toward the lever,
# +Z up -- the edges are +X 3.0, top 10.1, bottom -11.8, -X -28.0: 31.0 x 21.9. This file
# works in board-local mm with the origin at the board CENTRE, so the chip sits at
# (+12.5, +0.85): 3.0 from the +X edge and 10.1 below the top.
# The -X edge is an upper bound the spec allows shrinking; it stays, because J1's plug run
# and the tunnel in the -X web are sized to it.
# ⚠ FOOTPRINTS: the MCU's QFN-28 pitch (0.4 vs 0.45) and both QFNs' exposed pads are still
# the nearest stock KiCad lands, not read off the drawings -- resolve before ordering.
MCU_FP = "Package_DFN_QFN:QFN-28-1EP_4x4mm_P0.4mm_EP2.4x2.4mm"
SENSOR_FP = "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.45x1.45mm"
BOARD_W, BOARD_L = 31.0, 21.9
CHIP_XY = (12.5, 0.85)        # the axle axis, in board-local mm

# Anything TALLER than 1.5 mm must keep its whole footprint outside the magnet
# cap's swept circle, because the board installs by dropping straight down past
# the cap. Only the connector and the transceiver (SOIC-8, 1.75) qualify now that the
# inductor went with the buck; every passive here is under 1.5, the LDO is 1.45.
CAP_SWEEP_R = 5.66
TALL_PARTS = ("J1", "U2")


# ⚠ THE REF IS PINNED FROM THE TAG, AND IT HAS TO BE. Every call already passes a tag
# that spells the intended ref ("R5", "C11"), and until 2026-09-18 that was a COINCIDENCE:
# skidl numbered these parts in CREATION order and the order happened to agree. Adding one
# resistor in the MCU block broke it -- R5 vanished, the two I2C pull-ups became R7 and R9,
# and BOARD_NOTES["placements"] is keyed by ref, so three placed parts silently referred to
# refs that no longer existed while a new R9 had no placement and would have landed on the
# origin. The board still generated, ERC still passed, and the netlist was still valid.
# Passing ref= makes the tag authoritative, so where a part is CREATED stops mattering.
def _r(ref, tag, value, desc, pkg="Resistor_SMD:R_0402_1005Metric"):
    return Part(name="R", ref_prefix=ref, ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=pkg,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, pkg="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=pkg,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


@subcircuit
def lever_sensor():
    gnd, v5, v33 = Net("GND"), Net("+5V"), Net("+3V3")
    can_h, can_l = Net("CAN_H"), Net("CAN_L")
    for n in (gnd, v5, v33, can_h, can_l):
        n.drive = Pin.drives.POWER

    # ── the trunk, in and out of one connector ───────────────────────────────
    # Pins 1-4 are the incoming cable and 5-8 the outgoing one, each in the SAME
    # order the motor tee uses (GND / +V / CAN_H / CAN_L) so one crimp order
    # serves every connector in the instrument. The two halves are the same four
    # nets -- a pass-through, not a switch.
    # PH, SMT side entry (user, 2026-09-21). Pin order is the XH trunk's (harness.XH_PINOUT)
    # so one crimp order serves every connector -- but the +V way is the 5 V LEVER bus, which
    # is why the family differs from the 24 V tees: a lever harness physically cannot mate
    # a motor tee. The footprint's two MP tabs are mechanical and carry no net.
    j1 = Part(name="S8B-PH-SM4-TB", ref_prefix="J", ref="J1", tag="J1", dest="NETLIST",
              tool="skidl", value="S8B-PH-SM4-TB",
              description="lever bus in (1-4) and out (5-8), 5 V, LCSC C265121",
              footprint="Connector_JST:JST_PH_S8B-PH-SM4-TB_1x08-1MP_P2.00mm_Horizontal",
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(
                  tuple(x + "_IN" for x in ("GND", "V5", "CAN_H", "CAN_L"))
                  + tuple(x + "_OUT" for x in ("GND", "V5", "CAN_H", "CAN_L")))])
    gnd += j1[1], j1[5]
    v5 += j1[2], j1[6]
    can_h += j1[3], j1[7]
    can_l += j1[4], j1[8]

    # ── 5 V -> 3V3, AP2112K-3.3TRG1 (LCSC C51118) ─────────────────────────────
    # Replaces the 24 V buck. SOT-23-5 (Diodes Inc DS33549): 1 IN, 2 GND, 3 EN, 4 NC,
    # 5 OUT -- the same part and pin map the output panel uses. EN tied to IN: always on.
    # 1 uF ceramic on each side is the datasheet's stability requirement. Load is ~30 mA
    # (MCU + transceiver + sensor), so it drops (5 - 3.3) x 0.03 = 0.05 W -- nothing.
    # A LINEAR regulator is also the right call beside a magnetic angle sensor: the buck
    # was the one switching node on this board, 15 mm from the MT6701.
    u1 = Part(name="AP2112K-3.3", ref_prefix="U", ref="U1", tag="U1", dest="NETLIST",
              tool="skidl", value="AP2112K-3.3TRG1",
              description="600 mA LDO, 5 V -> 3V3 (LCSC C51118)",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="IN", func=PWR), Pin(num=2, name="GND", func=PWR),
                    Pin(num=3, name="EN", func=I), Pin(num=4, name="NC", func=P),
                    Pin(num=5, name="OUT", func=P)])
    v5 += u1["IN"], u1["EN"]
    gnd += u1["GND"]
    v33 += u1["OUT"]
    Net("U1_NC").connect(u1["NC"])
    cin = _c("C1", "1uF", "LDO input")
    v5 += cin[1]; gnd += cin[2]
    cout = _c("C2", "1uF", "LDO output")
    v33 += cout[1]; gnd += cout[2]

    # ── CAN transceiver, SN65HVD230DR (LCSC C12084) ──────────────────────────
    # SOIC-8: 1 D, 2 GND, 3 VCC, 4 R, 5 Vref, 6 CANL, 7 CANH, 8 Rs.
    can_tx, can_rx = Net("CAN_TX"), Net("CAN_RX")
    # ⚠ ref= PINNED: this part has always been U2 on the board (skidl numbered it second,
    # after the buck), and with the buck gone creation order would make it U1.
    u3 = Part(name="SN65HVD230DR", ref_prefix="U", ref="U2", tag="U3", dest="NETLIST",
              tool="skidl", value="SN65HVD230DR", description="3.3 V CAN transceiver",
              footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
              pins=[Pin(num=1, name="D", func=I), Pin(num=2, name="GND", func=PWR),
                    Pin(num=3, name="VCC", func=PWR), Pin(num=4, name="R", func=O),
                    Pin(num=5, name="Vref", func=O), Pin(num=6, name="CANL", func=P),
                    Pin(num=7, name="CANH", func=P), Pin(num=8, name="Rs", func=I)])
    can_tx += u3["D"]; can_rx += u3["R"]
    gnd += u3["GND"]; v33 += u3["VCC"]
    can_l += u3["CANL"]; can_h += u3["CANH"]
    # Rs to GND through a resistor sets slope control; 0 R would be full speed.
    # 10 k slews the edges, which is the right default on a metre of cable in a
    # box full of motors -- bus B runs at 500 k-1 M, nowhere near the limit.
    rs = _r("R", "R3", "10k", "transceiver slope control")
    u3["Rs"] += rs[1]; gnd += rs[2]
    c_xcvr = _c("C4", "100nF", "transceiver decoupling")
    v33 += c_xcvr[1]; gnd += c_xcvr[2]

    # BUS-B FAR-END TERMINATION, behind a solder jumper exactly as the motor tee
    # does it: populated on all eight, closed on the ONE board that ends the bus.
    # 0402, NOT the 0603 this was. When the board came down to 21.4 (the foot pedal
    # housing's floor, see knee_lever.PCB_WZ) R4 ended up in a 1.48 mm gap between JP1
    # and C10 needing 1.55, and every column on this board is full -- there is nowhere
    # else for it. 0402 fits with 0.45 to spare and is not a compromise: a single 120R
    # across the pair sees ~17 mA, i.e. 0.034 W against 0402's 0.063 W rating. It also
    # makes this board ALL-0402 for resistors, dropping a feeder.
    rt = _r("R", "R4", "120R", "CAN termination, closed only on the last board",
            "Resistor_SMD:R_0402_1005Metric")
    jp1 = Part(name="SolderJumper_2_Open", ref_prefix="JP", ref="JP1", tag="JP1", dest="NETLIST",
               tool="skidl", value="TERM", description="close on the bus's LAST board only",
               footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm",
               pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    term = Net("TERM_MID")
    can_h += rt[1]; term += rt[2], jp1[1]; can_l += jp1[2]

    # BUS-PIN CLAMPS. Two SEPARATE bidirectional TVS rather than one three-pin
    # CAN array, on purpose: a 2-pin bidirectional part is symmetric, so there is
    # no pinout to get wrong, and the 3-pin arrays' pin order is the one number I
    # could not verify. The threat is real -- a TRRS plug sweeps every contact on
    # insertion, so the leg's supply momentarily reaches CAN_H and CAN_L, and this
    # transceiver's bus pins are absolute-max -4..+16 V. (That supply is 5 V on the lever
    # bus now, inside the rating -- the clamps stay for ESD, which is what a plug on a
    # player-handled lever mostly sees.)
    for tag, net in (("D2", can_h), ("D3", can_l)):
        d = Part(name="TVS", ref_prefix="D", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                 value="PESD1CAN-like", description="bidirectional TVS, bus pin to GND",
                 # SOD-523, not SOD-123: these are signal-line ESD clamps, not power
                 # TVS, and the big package cost 18 mm2 the board no longer has once
                 # the foot pedal's Y budget capped its height at 22.55.
                 footprint="Diode_SMD:D_SOD-523",
                 pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
        net += d[1]; gnd += d[2]

    # ── MCU, CH32V203G6U6 QFN-28 (LCSC C5142280) ─────────────────────────────
    # Pins off WCH CH32V203 datasheet V2.8 table 3-1-3, the QFN28 (G6) column:
    #   0 VSS (exposed pad -- KiCad numbers that land 29, which is what is used
#     below)             2 OSC_IN  3 OSC_OUT  4 NRST  5 VDDA  16 VSS  17 VDD
    #   19 PA11 = CAN1_RX    20 PA12 = CAN1_TX
    #   21 PA13 = SWDIO      22 PA14 = SWCLK
    #   27 PB6  = I2C1_SCL   28 PB7  = I2C1_SDA
    # ⚠ PIN 1 IS BOOT0/PB8, AND NOTHING ON THIS BOARD CONNECTS TO IT. This note used to
    # say pin 1 was unidentified and had to be resolved against the package drawing
    # before fabrication. A second source now answers it: KiCad's own MCU_WCH_RiscV
    # library gives CH32V203GxUx pin 1 as BOOT0/PB8, and its pin list agrees with this
    # board's other twelve declarations exactly. That is a library rather than WCH's
    # drawing, so it is corroboration and not proof -- but the question is no longer open,
    # it is answerable, and the answer has a consequence.
    #
    # ⚠ A FLOATING BOOT STRAP IS NOT A NEUTRAL STATE. BOOT0 selects where the part starts;
    # left unconnected it is whatever the die's internal pull does, which is a thing to
    # confirm rather than assume -- and if there is no internal pull-down, an assembled
    # board's boot mode is set by leakage. motor_ctrl ties its BOOT0 to a pull-down and a
    # test pad for exactly this reason. Resolve it before fabrication: either confirm the
    # internal pull from WCH's manual, or spend one 0402 on a pull-down.
    #
    # ⚠ AND ALL FOUR MCU ROTATIONS ARE NOW MEASURED, not inferred. The rotation note
    # in BOARD_NOTES picked 0 by total pin-to-net distance, which is a PROXY -- and this
    # project has a long record of proxies being inverted (see the optical board, where
    # three of them were). Routed on the 34 x 28 board, one run each:
    #       rot   0   1 unconnected, 0 violations   <- kept
    #       rot  90   3 unconnected
    #       rot 180   3 unconnected
    #       rot 270   2 unconnected
    # The proxy was right this time. Recorded because "we chose it by a proxy" and "we
    # measured it" are different claims, and only one of them survives someone asking.
    #
    # ⚠ THOSE FOUR NUMBERS WERE TAKEN AT THE 0.6/0.3 VIA, when the best any rotation
    # could do was 1 unconnected. At 0.50/0.25 rotation 0 reaches ZERO, so the absolute
    # figures no longer describe this board -- only the RANKING is still being relied on,
    # and the ranking has not been re-measured at the smaller via. If a rotation is ever
    # in question again, re-run it rather than reading this table as current.

    # ⚠ AND THE BIGGER BOARD DID NOT FIX IT -- MEASURED AGAIN 2026-09-19, after the
    # board went to 34 x 28 for the XH. The open net swapped from CAN_RX to CAN_TX,
    # exactly the clean swap predicted below, and the shape is identical: the
    # TRANSCEIVER end has 14 of 24 clear bearings and 566 reachable via sites, the MCU
    # end (U3 pad 20) has ZERO and ZERO.
    #
    # That locates the constraint precisely, and it is not board area: the blockage is
    # inside the QFN's own escape fan, where the neighbouring pins' escapes take the
    # lane, so adding 6 mm of board in another direction cannot reach it. Two nets need
    # to leave adjacent pins of a 0.4 mm-pitch package through the same gap and only one
    # can. Re-assigning the pins is not available either -- see the remap note below;
    # this package brings out no PB9.
    #
    # What is left is moving the MCU or the transceiver relative to each other, which is
    # a placement question for the next revision rather than a routing one.

    # ⚠ CAN_RX MEASURED, 2026-09-18: THE MCU PIN CANNOT ESCAPE AT ALL. Probed at 24
    # directions and five distances from 0.3 to 1.5 mm, U3 pad 19 has ZERO clear exits --
    # not one bearing, not at any length. Reachable via sites: 885 from the transceiver's
    # pad, NONE from this one. No 2-segment or 3-segment F.Cu path exists between the two
    # pads, and no In2.Cu link between any of the 60 nearest reachable via sites.
    #
    # The blockers name the cause: CAN_TX's own track and pads take four of the eight
    # bearings, +3V3 one, GND pads the rest. CAN_TX and CAN_RX are adjacent MCU pins, and
    # whichever routes first takes the other's escape -- which is exactly what the note
    # below already predicted ("pre-lay CAN_RX and it connects, and CAN_TX becomes the
    # unconnected net instead, a clean swap"). The measurement corroborates it rather
    # than adding anything new.
    #
    # So this is NOT repairable the way optical's MID was. That pin had one clear bearing
    # and needed only a detour around two pads; this one has none, so there is no
    # geometry to find and no post-route track can help. The recorded conclusion stands
    # and is now measured rather than argued: only MOVING PARTS fixes this corner.
    # ⚠ AND THE SAME PIN LIST CLOSES OFF THE CAN REMAP. This package brings out PB8 (on
    # pin 1) but NO PB9 at all, so CAN1's PB8/PB9 remap -- the one motor_ctrl uses to get
    # CAN off PA11/PA12 -- does not exist here, and remap 3 is PD0/PD1, which the crystal
    # occupies. CAN_RX and CAN_TX are therefore stuck on PA11/PA12, immediately beside
    # SWDIO on PA13, which is the crowded corner described below. That corner cannot be
    # fixed by moving signals; only by moving parts.
    sda, scl = Net("SDA"), Net("SCL")
    swdio, swclk, nrst = Net("SWDIO"), Net("SWCLK"), Net("NRST")
    osc1, osc2 = Net("OSC_IN"), Net("OSC_OUT")
    u2 = Part(name="CH32V203G6U6", ref_prefix="U", ref="U3", tag="U2", dest="NETLIST",
              tool="skidl", value="CH32V203G6U6",
              description="RISC-V MCU, 2x CAN; same toolchain as the controller board",
              footprint=MCU_FP,
              pins=[Pin(num=29, name="VSS_PAD", func=PWR), Pin(num=2, name="OSC_IN", func=I),
                    Pin(num=3, name="OSC_OUT", func=O), Pin(num=4, name="NRST", func=I),
                    Pin(num=5, name="VDDA", func=PWR), Pin(num=16, name="VSS", func=PWR),
                    Pin(num=17, name="VDD", func=PWR), Pin(num=19, name="PA11", func=I),
                    Pin(num=20, name="PA12", func=O), Pin(num=21, name="PA13", func=P),
                    Pin(num=22, name="PA14", func=P), Pin(num=27, name="PB6", func=P),
                    Pin(num=28, name="PB7", func=P),
                    Pin(num=1, name="PB8", func=I)])   # BOOT0 -- see the note above
    gnd += u2["VSS"], u2["VSS_PAD"]
    v33 += u2["VDD"], u2["VDDA"]
    nrst += u2["NRST"]
    osc1 += u2["OSC_IN"]; osc2 += u2["OSC_OUT"]
    can_rx += u2["PA11"]; can_tx += u2["PA12"]
    swdio += u2["PA13"]; swclk += u2["PA14"]
    scl += u2["PB6"]; sda += u2["PB7"]
    # ⚠ BOOT0 RESOLVED: IT GETS THE 0402. The note above left two ways out -- confirm the
    # die's internal pull from WCH's manual, or spend a resistor -- and the resistor is
    # right even if the manual turns out to say there is a pull-down. An explicit strap is
    # immune to a datasheet revision and to a part substitution, motor_ctrl already does
    # exactly this on the same vendor's silicon (its R7, "BOOT0 pull-down"), and the cost
    # is one 0402 of a value this board already stocks -- no new SKU and no new feeder,
    # across all eleven boards. Confirming the internal pull would have cost more reading
    # than the part costs and still left the board leaning on an undocumented default.
    #
    # NO TEST PAD BESIDE IT, unlike motor_ctrl. A BOOT0 pad exists to force the ROM
    # bootloader, and that only helps if the bootloader can be REACHED -- this board has
    # no USB and brings out no USART, so the entry path does not exist. That absence is
    # the whole reason the SWD pads were added; SWD is the recovery route here.
    # ⚠ TIED HARD TO GND, NOT PULLED DOWN -- AND THE BOARD DECIDED THAT, NOT ME. The
    # 0402 pull-down went in first, matching motor_ctrl. It could not be placed: this
    # board is FULL (its own note: six free 2.0 mm sites, four already spent on the SWD
    # pads), and three sitings gave three different failures -- inside two courtyards
    # (3 unconnected, 3 violations), clearing pads but not courtyards (2 and 2), and
    # clearing both but displacing the router badly (4 and 1). The part was costing more
    # than it bought every time.
    #
    # A pull-down exists so BOOT0 can be forced HIGH externally to reach the ROM
    # bootloader. THIS BOARD HAS NO BOOTLOADER PATH -- no USB, no USART brought out --
    # which is the whole reason the SWD pads were added. So the resistor buys an entry
    # to a door that does not exist here, and a hard tie is the honest wiring of "this
    # part always boots from flash". motor_ctrl keeps ITS pull-down because it has USB
    # on a connector and the door is real.
    #
    # What a hard tie costs: forcing the bootloader later would mean cutting copper
    # rather than lifting a resistor. Against a board with no way to use the bootloader
    # and a working SWD route, that is not a cost worth one 0402 and three re-routes.
    gnd += u2["PB8"]


    y1 = Part(name="Crystal", ref_prefix="Y", ref="Y1", tag="Y1", dest="NETLIST", tool="skidl",
              value="8MHz", description="HSE -- CAN bit timing wants a crystal, not the RC",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P),
                    Pin(num=3, func=P), Pin(num=4, func=P)])
    osc1 += y1[1]; osc2 += y1[3]
    gnd += y1[2], y1[4]
    for tag, net in (("C5", osc1), ("C6", osc2)):
        c = _c(tag, "12pF", "crystal load")
        net += c[1]; gnd += c[2]
    c_nrst = _c("C7", "100nF", "NRST filter")
    nrst += c_nrst[1]; gnd += c_nrst[2]

    # ⚠ WITHOUT THESE FOUR PADS THIS BOARD CANNOT BE PROGRAMMED AT ALL, and there are
    # eight to ten of them in the instrument. Audited 2026-09-17, after the same fault
    # was found on the optical board: SWDIO and SWCLK reached the MCU and stopped --
    # single-node nets, which layout drops as unplaceable and DRC cannot complain about.
    #
    # AND UNLIKE THE OTHER BOARDS THERE IS NO SECOND WAY IN. Listed from the netlist,
    # the only externally reachable nets were +24V, CAN_H, CAN_L and GND. The CH32V203
    # has no CAN bootloader -- WCH's ISP is USB or USART -- and this board brings out
    # neither, nor a BOOT0 pin. motor_ctrl and output_panel at least have USB on a
    # connector, so their ROM bootloader is reachable in principle; this one had nothing.
    # An assembled lever board would have been a brick, ten times over.
    #
    # Four pads, not five: the board is FULL. A scan of its courtyards found six free
    # 2.0 mm sites and no contiguous strip at all, so there is no room for the +3V3
    # target-sense pad the optical board carries. SWDIO, SWCLK and GND are clustered
    # within 2.5 mm for a probe; NRST is the outlier, which is the right one to strand
    # because it is only needed for connect-under-reset recovery.
    for _ref, _net, _what in (("TP1", swdio, "SWDIO"), ("TP2", swclk, "SWCLK"),
                              ("TP3", gnd, "GND"), ("TP4", nrst, "NRST")):
        _tp = Part(name="TestPoint", ref_prefix="TP", ref=_ref, dest="NETLIST",
                   tool="skidl", value="SWD",
                   description="SWD pad -- %s; bare copper, no component" % _what,
                   footprint="TestPoint:TestPoint_Pad_D1.0mm",
                   pins=[Pin(num=1, func=P)])
        _net += _tp[1]
    for tag in ("C8", "C9"):
        c = _c(tag, "100nF", "MCU decoupling")
        v33 += c[1]; gnd += c[2]
    c_bulk = _c("C10", "4.7uF", "MCU bulk -- 0402 since the re-spin (6.3 V X5R)")
    v33 += c_bulk[1]; gnd += c_bulk[2]

    # ── the sensor, MT6701QT-STD QFN-16 (LCSC C2913974) ──────────────────────
    # Pins off MagnTek MT6701 datasheet section 1.2 (QFN-16 pin list):
    #   5 PUSH  6 A(SDA)  7 B(SCL)  8 Z(CSN)  9 W  11 U  12 V
    #   13 VDD  14 MODE  15 OUT  16 GND ; 1-4 and 10 are NC
    # MODE selects ABZ against I2C/SSI. It is strapped through a resistor rather
    # than tied, because which level selects which is a datasheet detail to
    # confirm on the first board -- a resistor is a jumper you can move.
    u4 = Part(name="MT6701QT-STD", ref_prefix="U", ref="U4", tag="U4", dest="NETLIST",
              tool="skidl", value="MT6701QT-STD",
              description="14-bit Hall angle encoder, sensing centre = package centre",
              footprint=SENSOR_FP,
              pins=[Pin(num=5, name="PUSH", func=O), Pin(num=6, name="A_SDA", func=P),
                    Pin(num=7, name="B_SCL", func=P), Pin(num=8, name="Z_CSN", func=P),
                    Pin(num=13, name="VDD", func=PWR), Pin(num=14, name="MODE", func=I),
                    Pin(num=15, name="OUT", func=O), Pin(num=16, name="GND", func=PWR),
                    Pin(num=17, name="EP", func=PWR)])
    v33 += u4["VDD"]; gnd += u4["GND"], u4["EP"]
    sda += u4["A_SDA"]; scl += u4["B_SCL"]
    r_mode = _r("R", "R5", "0R", "MODE strap -- confirm polarity on the first board")
    u4["MODE"] += r_mode[1]; gnd += r_mode[2]
    c_sens = _c("C11", "100nF", "sensor decoupling")
    v33 += c_sens[1]; gnd += c_sens[2]
    for tag, net in (("R6", sda), ("R7", scl)):
        r = _r("R", tag, "4k7", "I2C pull-up")
        v33 += r[1]; net += r[2]


def _sensor_qty():
    """One board per sensed player control: 6 knee levers + 5 pedals."""
    from src import dimensions as D
    return D.N_SENSED


_SENSOR_QTY = _sensor_qty()

BOARD_NOTES = {
    # ⚠ THE ONLY BOARD THERE IS MORE THAN ONE OF, AND IT USED TO DECLARE NO COUNT AT ALL.
    # Every other board states it -- optical 1, output_panel 1, motor_ctrl 1, can_tee one
    # per motor -- and this one, the multi-unit board, stated nothing. The count existed
    # only as the BOM's angle-sensor quantity, 11, with no record of what the 11 WERE, so
    # it could not be checked and could not be traced if it moved.
    #
    # It is 6 knee levers and 5 pedals (user, 2026-09-18): one sensed axis each, one
    # MT6701 each, one of these boards each. That is D.N_SENSED, and it reproduces the
    # BOM's 11 independently -- the first time those two numbers have had a common source
    # rather than agreeing by coincidence. Derived, not typed, because a typed board count
    # is how can_tee came to ship a 9 against a ten-motor instrument (see the note there).
    "qty_per_instrument": _SENSOR_QTY,
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 4,
    "thickness_mm": 1.6,
    # Board-local mm, origin at the board centre. The housing frame is x -25..+3
    # and z -14.2..+7.8, so the axle axis (housing 0,0) lands at CHIP_XY.
    "chip_on_axle_xy": CHIP_XY,
    # ⚠ RE-PLACED 2026-09-21 FOR THE RE-SPIN. The circuit is the routed board's, moved
    # as a block by (+1.5, +1.45) -- the frame shift that keeps the chip on the axle in the
    # new board-centred frame -- so every relationship the CAN-fan notes below were
    # measured on (MCU beside transceiver beside crystal) is preserved exactly. What
    # changed: the buck is gone from the top, the LDO and its two caps take that corner,
    # R6 steps 0.57 -X out of the +X groove band, and the four SWD pads come in off the
    # trimmed +X edge into the top strip (one column of three plus NRST, as before).
    "placements": {
        "U4": (12.50, 0.85, 0.0),
        # SWD: SWDIO / SWCLK / GND in a row for a clip, NRST stranded (recovery only)
        "TP1": (8.00, 8.80, 0.0),     # SWDIO
        "TP2": (10.40, 8.80, 0.0),    # SWCLK
        "TP3": (8.00, 6.50, 0.0),     # GND
        "TP4": (-1.65, 8.90, 0.0),    # NRST
        # J1 on end, mouth -X at x -12.45 (3.05 in from the -X edge, the spec's figure).
        # Placements anchor on the PAD CENTROID: the footprint's mouth is its local +y 4.4,
        # its pad centroid local y -1.70 (eight pins at -2.85, two tabs at +2.90), and rot
        # 270 turns +y to -X -- so the centroid sits 6.10 +X of the mouth. Read back off
        # the routed geom, not assumed: -8.05 put the mouth at -14.15.
        "J1": (-6.35, 0.00, 270.0),
        "U1": (4.00, 8.00, 0.0),
        "C1": (0.60, 8.60, 0.0),
        "C2": (0.60, 7.30, 0.0),
        "R7": (12.40, 7.15, 0.0),
        # ⚠ U3 (the MCU) AT 0 ROTATION, AND IT IS A ROUTING DECISION -- measured across all
        # four rotations on the old board (see lever_sensor()). The CAN fan (pins 19-21,
        # 0.4 pitch) closes only with the 0.50/0.25 via; see via_mm.
        "U3": (2.50, 3.00, 0.0),
        "C9": (7.00, 4.65, 0.0),
        "C8": (9.00, 4.65, 0.0),
        "R5": (12.50, 4.35, 0.0),
        "C11": (8.50, 0.85, 0.0),
        "C10": (11.00, -2.45, 0.0),
        "Y1": (0.60, -1.55, 0.0),
        # C5/C6 stay east of the crystal: moving them west measured 1 -> 5 unconnected
        "C5": (5.10, -1.05, 0.0),
        "C6": (5.10, -2.85, 0.0),
        # C7 (NRST) steps 2.8 +Y off the MCU's west edge: J1's pads now stand 1.9 from
        # it rather than 3.6, and at its old site it sat squarely in OSC_OUT's escape
        # (pin 3, the pin below NRST) -- 1 unconnected with no legal repair path.
        "C7": (-1.05, 5.30, 90.0),
        "R6": (12.90, -2.47, 270.0),
        "U2": (2.00, -6.15, 0.0),
        "C4": (7.50, -4.85, 0.0),
        "R3": (7.50, -6.35, 0.0),
        "R4": (11.00, -4.30, 0.0),
        "JP1": (11.00, -6.25, 0.0),
        "D2": (7.30, -8.35, 0.0),
        "D3": (10.10, -8.35, 0.0),
    },
    "cap_keepout": {"xy": list(CHIP_XY), "r": CAP_SWEEP_R, "tall": list(TALL_PARTS)},
    # FOUR LAYERS: an unbroken GND plane on In1 under a magnetic angle sensor, and the
    # layer set the 0.4 mm-pitch MCU's escape needs. (It was first argued against the 24 V
    # buck's switching loop; the buck is gone and the plane's other two jobs remain.)
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
    # ⚠ THE LAYER LOCAL/RETRIED NETS MAY DIVE TO. In1.Cu is the ground plane and B.Cu
    # carries a second GND pour, so In2.Cu is the one inner layer with no pads on it.
    # Without this the generator has no way off the component layer at all, which is
    # exactly why the nets stranded at the QFN stayed stranded: its only escape was
    # gated on a differential-pair setting this board has no reason to declare.
    "local_inner": "In2.Cu",
    # ⚠ 0.15 mm TRACK, because the tightest part on this board is a 0.4 mm pitch QFN-28
    # and the default 0.25 does not leave its escape fan room to turn. Four nets -- NRST,
    # OSC_OUT, CAN_RX and a +3V3 pin -- were stranded at that package and neither the
    # router nor the generator could get them out.
    # 0.15 on 1 oz copper carries ~0.5 A at a 10 C rise, against this board's largest
    # load of roughly 100 mA; the constraint here is geometry, not current.
    "track_mm": 0.15,
    # 20 passes on the re-spun board: at the default 10 the J1 move alone swapped 0
    # unconnected for 1 (OSC_OUT) -- the router re-plans everything on any change.
    "router_passes": 20,
    # ⚠ AND A PLANE NEEDS STITCHING TO IT. Declaring In1 a plane is only half the
    # job: it stops the router carrying ground THROUGH the plane, and then nothing
    # connects the ground pads TO it. Declared alone it stranded six GND pads on this
    # board -- the pour reaches them, but a pour is what routing can orphan, which is
    # the whole reason the plane is there. Every GND pad gets its own via down.
    "stitch_nets": ("GND",),
    # (No stitch exceptions: J1 is SMT again, so its GND pads get vias like every other.)
    # ⚠ NO local_nets ON THIS BOARD, AND THE MEASUREMENT SAYS SO. Pre-laying every
    # short net here took it from 4 unconnected to 7. The generator is not better than
    # the router in general -- it wins on the optical board because twenty identical
    # feedback clusters in a strip holding 107 parts is a pattern, and a pattern is a
    # thing a generator does better than a search. This board is 28 x 21 with 29 parts
    # and the router has slack; deterministic copper laid first only takes that slack
    # away, and the search it constrains could have done better.
    #
    # Worth keeping the number rather than the conclusion: if this board grows a
    # component row, re-measure rather than assuming either way.
    #
    # ⚠ RE-MEASURED 2026-09-19 AS THAT NOTE ASKS, on the 34 x 28 board: "local_nets":
    # ("CAN_RX",) lays ZERO segments. The generator's reach is 6 mm single-linkage and
    # CAN_RX spans 12.5 mm end to end, so pre-laying it is not refused, it is out of
    # range. The conclusion stands for a new reason, which is worth more than the
    # conclusion: the generator is not an option for this net AT ALL, so "pre-lay
    # CAN_RX and CAN_TX fails instead" cannot be reproduced on this board and is not
    # the state to reason from any more.
    # ⚠ A SMALLER VIA, AND IT IS WHAT CLOSES THE CAN FAN -- see the note in
    # lever_sensor() for the measurement. Three signals leave three adjacent 0.4 mm-pitch
    # QFN pins and a 0.6 mm via leaves room for two; at 0.50 all three escape and this
    # board reaches 0 unconnected, 0 violations for the first time.
    #
    # THE PAD IS THE DIMENSION THAT MATTERS, NOT THE DRILL, which the sweep separates:
    #     0.60 / 0.30   1 unconnected (CAN_RX)     -- the fan has room for two
    #     0.55 / 0.30   2 unconnected (SCL, SWDIO) -- worse, not a gradient
    #     0.50 / 0.30   0 unconnected, 12 hole_clearance errors
    #     0.50 / 0.25   0 unconnected, 0 violations
    #     0.45 / 0.25   0 unconnected, 11 hole_clearance errors
    # The drill only shrinks to keep the annulus wide enough for KiCad's DEFAULT 0.25 mm
    # hole-clearance constraint, which the 0.30 drill misses by 0.011 mm.
    #
    # ⚠ AND IT COSTS NOTHING, WHICH WAS WORTH CHECKING RATHER THAN ASSUMING. The via
    # note in layout.py chose 0.6/0.3 because it is JLCPCB's standard capability, so the
    # obvious reading is that this leaves it. Their published capabilities (2026-09-19)
    # say otherwise on both counts:
    #   * "Min. Via hole size/diameter ... Multilayer: 0.15 mm hole size / 0.25 mm via
    #     diameter", so 0.50/0.25 is inside standard capability, not beyond it.
    #   * The surcharge is specific: "0.2mm or 0.25mm hole size with via diameter LESS
    #     THAN 0.45mm will cost more". 0.50 is above that, so a 0.25 drill here is not
    #     surcharged. It also satisfies their "via diameter should be 0.1mm (0.15mm
    #     preferred) larger than via hole size" -- this is 0.25 larger.
    #   * Their real hole-to-copper rule is "Via hole to Track 0.2mm", LOOSER than the
    #     0.25 KiCad enforces. So the 0.50/0.30 board that failed 12 hole_clearance
    #     checks was failing a house default and not a fab limit -- it is manufacturable
    #     too. 0.50/0.25 is used because it needs no rule relaxed to prove it.
    "via_mm": (0.50, 0.25),
    # ⚠ THE VIA SIZE IS AN ORDER-FORM FIELD, NOT JUST A GERBER FACT. JLCPCB's own
    # capability page says "please select corresponding via size option when placing
    # order" for 0.2/0.25 mm hole sizes. The gerbers carry the geometry; the process is
    # chosen on the form, and nothing in the drill file makes the operator pick it.
    "order_options": {
        "via size": "0.25 mm hole / 0.50 mm diameter -- SELECT THIS ON THE ORDER FORM. "
                    "Inside standard capability and NOT surcharged (the surcharge is for "
                    "a 0.25 hole with a diameter under 0.45; this is 0.50). The board "
                    "does not route at the 0.6/0.3 default -- see the CAN fan note.",
    },
    # ⚠ THE ONE DRC WARNING THIS BOARD KEEPS IS COSMETIC, AND IS KEPT ON PURPOSE.
    # silk_overlap x1: the segment of Y1's silkscreen OUTLINE against U2's outline
    # polygon, ~0.96 mm apart at 97.0,104.7. It is two part outlines touching on the ink
    # layer -- not a reference designator over a pad, which is the case that actually
    # costs something, and not anything the fab cannot handle (silk over copper is
    # clipped automatically). The parts either side of it are the crystal and the CAN
    # transceiver, both of which are where they are for routing reasons that took four
    # rounds to settle; moving one to tidy ink would risk the 0 unconnected this board
    # only just reached. Recorded rather than chased, so it is not mistaken later for a
    # warning nobody looked at.
    "refs_on_fab": True,
    "hold_edge": None,          # NO screw: the grooves hold five faces and the
                                # instrument's underside closes over the sixth
    "no_mounting_holes": True,
    "single_sided": True,       # every part on the magnet-facing face
    # MECHANICAL keepouts, mirrored from knee_lever.py so this side catches them
    # too. The cradle's grooves take 1.85 off each X edge (the sensor is the one
    # part allowed in, its position being fixed on the axle), and the connector's
    # mated plug forbids a strip -- board-local, converted from the chip frame.
    "groove_keepout_x": 1.85,
    "groove_exempt": ["U4", "J1"],
    # J1's zone (spec rule 4): its body, its solder tabs and the mated plug's 3.6 run past
    # the mouth, over J1's length -- x -16.05..-3.85 here, clipped to the board.
    "conn_keepout": {"box": [-15.5, -9.95, -3.85, 9.95], "exempt": ["J1", "U4"]},
}


if __name__ == "__main__":
    lever_sensor(tag="lever")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "lever_sensor.net"))
    netcheck.grounds_meet(os.path.join(OUT_DIR, "lever_sensor.net"))
    netcheck.no_orphan_pins(os.path.join(OUT_DIR, "lever_sensor.net"))
    # ⚠ EVERY PART PLACED, EVERY PLACEMENT REAL. placements is keyed by REF, and a ref
    # is assigned by skidl rather than written here, so the two can disagree without
    # anything downstream objecting: a part with no entry lands on the ORIGIN, and an
    # entry naming a ref that no longer exists is simply ignored. Both happened on
    # 2026-09-18 from adding one resistor -- see the note on _r. ERC passed, the netlist
    # was valid, and three parts were in the wrong place.
    _refs = set(re.findall(r'\(comp\s*\(ref "([^"]+)"\)',
                           open(os.path.join(OUT_DIR, "lever_sensor.net"),
                                encoding="utf-8").read()))
    _placed = set(BOARD_NOTES["placements"])
    assert not (_refs - _placed), (
        "no placement for %s -- it would be laid on the board origin"
        % sorted(_refs - _placed))
    assert not (_placed - _refs), (
        "placements name %s, which no part has -- a ref moved under it"
        % sorted(_placed - _refs))
    with open(os.path.join(OUT_DIR, "lever_sensor.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements, chip on the axle at (%.1f, %.1f)"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]), *CHIP_XY))
