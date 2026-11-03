"""Lever / pedal sensor board — MA730 angle sensor + CAN node, x8.

    py -3.12 elec/lever_sensor.py       # -> elec/out/lever_sensor.{net,board.json}

ONE BOARD FOR EVERY CONTROL: five knee levers and three foot pedals. It reads the
pivot angle off a diametric magnet on the axle and puts it on CAN bus B.

IT ABSORBS THE BUS-B TEE (user). Earlier rounds hung each lever off a trunk tee by
a single 4-way drop; the trunk now passes THROUGH the board, in on J1 and out on J2.
That deletes eight tee boards and eight cradles. THE COST, stated once because it is
real: a daisy chain means unplugging one lever breaks the bus for everything
downstream of it, which is exactly the property the trunk-and-drop topology was
chosen to have.

TWO 4-WAY PH, NOT ONE 8-WAY (user, 2026-10-19). With in and out in one PHR-8 housing,
every hop's cable was crimped into the next board's housing alongside the cable after
it, so moving or pulling one lever meant re-making the harness either side of it. Two
4-ways make each hop its own straight PHR-4 jumper (way n to way n, both connectors in
harness.PH_PINOUT order): a lever comes out by its two plugs, and a hop that changes
length is one new cable. THROUGH-HOLE, S4B-PH-K-S (LCSC C157926, ~40k stock), because
it is what fits: two SMT S4B-PH-SM4-TB stand 23.8 end to end against the 19.9 the
board's height leaves (the foot pedal caps it), and two S4B-PH-K-S stand 19.8 -- the
length of the S8B-PH-SM4-TB they replace, so the outline and every housing are
unchanged. The pins come through to the back face; the cradle has no back wall there.
(History: two S4B-XH-SM4-TB needed 31.0 of height; the 8-way XH was not stocked; PHD
2x4 was rejected on sourcing.)

THE CHIP'S POSITION IS NOT NEGOTIABLE. MA730 sensing point = package geometric
centre (datasheet rev 1.1 p.10 fig. 3: 1.50 +-0.05 in from the edge of the 3.00
package, 0.45 below its top), and it must sit on the axle axis. Everything else is
placed around it.

THE SENSOR IS AN MA730GQ-Z SINCE 2026-11-03 (user, via the lead): the MT6701 went to
0 stock at LCSC under both codes and MagnTek has no DigiKey listing. Same QFN-16 3x3
outline, same 14 bits, but NOT pin-compatible and read over SPI, not I2C -- so the I2C
pair, its pull-ups and the MODE strap are gone, and SPI1 + PB5 read it. SOURCING (user):
JLC's listing (C161798), no consignment. Order-time check: the listing still covers 11+;
if it is gone the fallback is AS5600-ASOM (C79815), which is a board change.

EVERY PIN NUMBER BELOW IS OFF THE DATASHEET, not a library symbol -- see the
per-part notes. Getting one wrong is the failure this file exists to prevent.

⚠ RE-SPUN 2026-09-21 TO branner's SPEC (docs/lever-sensor-respin.md), user decisions:
  * the lever bus runs at 5 V -- the 24 V buck (U1 LMR16006, L1, D1, C1-C3, R1/R2) is
    gone, and a 5 V -> 3V3 LDO (AP2112K) takes its place
  * J1 is PH again (2026-10-19: J1 + J2, two S4B-PH-K-S, see above), on the magnet face, on
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
# respin.md, 2026-09-21). In the spec's frame -- origin on the sensor, +X toward the lever,
# +Z up -- the edges are +X 4.025, top 10.1, bottom -11.8, -X -29.0: 33.025 x 21.9. This file
# works in board-local mm with the origin at the board CENTRE, so the chip sits at
# (+12.49, +0.85): 4.025 from the +X edge and 10.1 below the top.
# J1's plug run and the tunnel in the -X web follow the -X edge (knee_lever.PCB_X0).
# ⚠ FOOTPRINTS: the MCU's QFN-28 pitch (0.4 vs 0.45) and exposed pad are still the nearest
# stock KiCad land, not read off the drawing -- resolve before ordering. The SENSOR'S IS READ
# OFF ITS DRAWING: MA730 rev 1.1 p.26 "recommended land pattern", pads 0.70 x 0.25 on 0.50
# pitch with their centres 2.90 apart, exposed pad 1.70 (elec/footprints/Steel.pretty).
MCU_FP = "Package_DFN_QFN:QFN-28-1EP_4x4mm_P0.4mm_EP2.4x2.4mm"
SENSOR_FP = "Steel:MPS_QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm"
# THE SPEC'S FOUR EDGES, in the spec's own frame (origin on the sensor, +X toward the
# lever, +Z up). Everything else about the outline is derived from them, because it was
# not: BOARD_W and CHIP_XY were both typed, and both encode the edges, so the +X edge
# moving on 2026-09-29 left this file describing a board that no longer existed while
# every number in it stayed self-consistent (tools/check_board_match.py now says so).
# -X: the terminator switch needs 8.89 mm over its lands between the transceiver and
# the +X groove band, so the transceiver, MCU, crystal, regulator and J1 stand 1.0
# further from the chip than they otherwise would.
SPEC_X0, SPEC_X1 = -29.0, 4.025
SPEC_Z0, SPEC_Z1 = -11.8, 10.1
BOARD_W, BOARD_L = SPEC_X1 - SPEC_X0, SPEC_Z1 - SPEC_Z0
# the axle axis in board-local mm -- half the board, less the chip's distance to the far
# edge. Grow the board on +X alone and the CENTRE moves, so this moves too.
CHIP_XY = (BOARD_W / 2 - SPEC_X1, BOARD_L / 2 - SPEC_Z1)

# Anything TALLER than 1.5 mm must keep its whole footprint outside the magnet
# cap's swept circle, because the board installs by dropping straight down past
# the cap. Only the connector and the transceiver (SOIC-8, 1.75) qualify now that the
# inductor went with the buck; every passive here is under 1.5, the LDO is 1.45.
CAP_SWEEP_R = 5.66
TALL_PARTS = ("J1", "J2", "U2", "SW1")
SW1_XY = (-2.5500, -7.3000)       # the terminator switch's centre, chip frame


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

    # ── the trunk, in on J1 and out on J2 ────────────────────────────────────
    # Two 4-way PH, each in the instrument's one order (harness.PH_PINOUT: 5 V, GND,
    # CAN_H, CAN_L), so the cable between two boards is a STRAIGHT jumper, way n to way n.
    # The two are the same four nets -- a pass-through, not a switch -- so in and out may
    # be swapped without effect. PH, THT side entry (user, 2026-10-19; see the header):
    # the power way is the 5 V LEVER bus, which is why the family differs from the 24 V
    # tees -- a lever harness physically cannot mate a motor tee.
    _trunk = harness.ph_trunk_pins()
    _rail = {"GND": gnd, "V5": v5, "CAN_H": can_h, "CAN_L": can_l}
    for j, (ref, side) in enumerate((("J1", "in"), ("J2", "out"))):
        names = _trunk[4 * j:4 * j + 4]
        jx = Part(name="S4B-PH-K-S", ref_prefix="J", ref=ref, tag=ref, dest="NETLIST",
                  tool="skidl", value="S4B-PH-K-S",
                  description="lever bus %s, 5 V, LCSC C157926" % side,
                  footprint="Connector_JST:JST_PH_S4B-PH-K_1x04_P2.00mm_Horizontal",
                  pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(names)])
        ways = tuple(n.rsplit("_", 1)[0] for n in names)
        harness.check_ways(ways, ("V5",), where=ref)
        for i, n in enumerate(ways):
            _rail[n] += jx[i + 1]

    # ── 5 V -> 3V3, AP2112K-3.3TRG1 (LCSC C51118) ─────────────────────────────
    # Replaces the 24 V buck. SOT-23-5 (Diodes Inc DS33549): 1 IN, 2 GND, 3 EN, 4 NC,
    # 5 OUT -- the same part and pin map the output panel uses. EN tied to IN: always on.
    # 1 uF ceramic on each side is the datasheet's stability requirement. Load is ~30 mA
    # (MCU + transceiver + sensor), so it drops (5 - 3.3) x 0.03 = 0.05 W -- nothing.
    # A LINEAR regulator is also the right call beside a magnetic angle sensor: the buck
    # was the one switching node on this board, 15 mm from the angle sensor.
    # Pins off Diodes DS39724 rev 2-2 "Pin Descriptions", SOT25 column, read 2026-09-30:
    #   1 VIN  2 GND  3 EN (high = on)  4 NC  5 VOUT
    u1 = Part(name="AP2112K-3.3", ref_prefix="U", ref="U1", tag="U1", dest="NETLIST",
              tool="skidl", value="AP2112K-3.3TRG1",
              description="600 mA LDO, 5 V -> 3V3 (LCSC C51118)",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="IN", func=PWR), Pin(num=2, name="GND", func=PWR),
                    Pin(num=3, name="EN", func=I), Pin(num=4, name="NC", func=P),
                    Pin(num=5, name="OUT", func=P)])
    # THE REGULATOR SITS BEHIND 2.2 OHM (2026-10-04). The pedal boards are reached through
    # the leg's spring pins, a joint a player can make with the instrument on. A live 5 V
    # bus, a metre of 26 AWG (about 1 uH and 0.3 ohm) and a bare 1 uF ceramic is a tank
    # with a damping ratio near 0.2: it rings to about 7.6 V, and the AP2112's input is
    # 6.5 V absolute maximum. With 2.2 ohm in the branch the ratio is about 0.9 and there
    # is no overshoot to speak of. It costs 0.18 V at 80 mA, against 1.2 V of headroom,
    # and it is in the branch only: the bus itself passes J1 -> J2 untouched.
    # The bus keeps a 100 nF of its own at the connector (the regulator's capacitor is on
    # the far side of the resistor now). It rings on a hot plug like any bare ceramic and
    # does not mind: nothing else is on this net but the connector and the resistor.
    c_bus = _c("C3", "100nF/16V", "bus HF bypass at J1 -- rated for the hot-plug ring")
    v5 += c_bus[1]; gnd += c_bus[2]
    v5_ldo = Net("+5V_LDO")
    r_in = _r("R", "R8", "2R2", "damps the input capacitor against a hot-plugged bus")
    v5 += r_in[1]; v5_ldo += r_in[2]
    v5_ldo += u1["IN"], u1["EN"]
    gnd += u1["GND"]
    v33 += u1["OUT"]
    Net("U1_NC").connect(u1["NC"])
    cin = _c("C1", "1uF", "LDO input")
    v5_ldo += cin[1]; gnd += cin[2]
    cout = _c("C2", "1uF", "LDO output")
    v33 += cout[1]; gnd += cout[2]

    # ── CAN transceiver, SN65HVD230DR (LCSC C12084) ──────────────────────────
    # SOIC-8: 1 D, 2 GND, 3 VCC, 4 R, 5 Vref, 6 CANL, 7 CANH, 8 Rs.
    # (TI SLOS346O section 7 "Pin Functions", read 2026-09-30. Rs hard to GND = high speed.)
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

    # BUS-B FAR-END TERMINATION, behind a slide switch placed by the fab: fitted on all
    # eleven, ON on the ONE board at each far end of the bus. A switch, not a solder
    # bridge, so that ending the bus needs no iron (user rule: no hand soldering).
    # R4 is 0402: a single 120R across the pair sees ~17 mA in normal traffic, 0.034 W.
    # ⚠ A 100 mW 0402 (Panasonic ERJ2RKF1200X, C413065), NOT THE HOUSE 62.5 mW ONE
    # (2026-10-06, found by elec/voltage_check.py when this board was added to it). The
    # 34 mW is a typical drive at a typical duty. A transceiver's dominant output may be
    # 3 V (SLOS346, VOD max), and the SN65HVD230 has no dominant time-out: firmware that
    # parks TXD low holds 3 V across this part for as long as it stays there, 75 mW, 120 %
    # of the house part. Same land, same value.
    rt = _r("R", "R4", "120R 100mW", "CAN termination, in circuit only with SW1 ON",
            "Resistor_SMD:R_0402_1005Metric")
    # DSHP01TSGER (LCSC C3293141), THE MOTOR TEE'S SWITCH: one part number ends both
    # buses. 1 position, SPST, recessed slide, gull wing, body 5.4 x 2.88 x 2.3, lands
    # 0.76 x 1.27 on 7.62 centres -- 8.89 over the lands, which is what sets this board's
    # -X edge (see SPEC_X0). ON is printed on the body.
    sw1 = Part(name="SW_DIP_x01", ref_prefix="SW", ref="SW1", tag="SW1", dest="NETLIST",
               tool="skidl", value="DSHP01TSGER",
               description="bus B terminator: ON on the LAST board only (LCSC C3293141)",
               footprint="Steel:Kangshen_DSHP01TSGER",
               pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    term = Net("TERM_MID")
    can_h += rt[1]; term += rt[2], sw1[2]; can_l += sw1[1]

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
                 value="ESD5B5.0ST1G", description="bidirectional 5 V TVS, bus pin to GND "
                 "(LCSC C93623, the part motor_ctrl clamps the same bus with)",
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
    #   11 PA5  = SPI1_SCK   12 PA6  = SPI1_MISO   13 PA7 = SPI1_MOSI   26 PB5 = sensor CS
    #   (the SPI pins off datasheet V3.0 table 3-1-3, QFN28 column, default functions, read
    #    2026-11-03; the KiCad MCU_WCH_RiscV symbol agrees. PB6 / PB7, the I2C1 pair the
    #    MT6701 was read on, are unused GPIO since the MA730)
    # (HISTORY -- NO LONGER TRUE: pin 1 is now tied hard to GND, see "TIED HARD TO GND" below,
    #  and WCH's own table confirms the pin: 3-1-3 note 6. Kept for the reasoning. This stale
    #  heading was read as current on 2026-09-30 and BOOT0 was reported floating. It is not.)
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
    sck, miso, mosi = Net("SENS_SCK"), Net("SENS_MISO"), Net("SENS_MOSI")
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
                    Pin(num=22, name="PA14", func=P),
                    Pin(num=11, name="PA5", func=O),   # SPI1_SCK  -- table 3-1-3, QFN28
                    Pin(num=12, name="PA6", func=I),   # SPI1_MISO
                    Pin(num=13, name="PA7", func=O),   # SPI1_MOSI
                    Pin(num=26, name="PB5", func=O),   # sensor CS -- table 3-1-3, QFN28
                    Pin(num=1, name="PB8", func=I)])   # BOOT0 -- see the note above
    gnd += u2["VSS"], u2["VSS_PAD"]
    v33 += u2["VDD"], u2["VDDA"]
    nrst += u2["NRST"]
    osc1 += u2["OSC_IN"]; osc2 += u2["OSC_OUT"]
    can_rx += u2["PA11"]; can_tx += u2["PA12"]
    swdio += u2["PA13"]; swclk += u2["PA14"]
    sck += u2["PA5"]; miso += u2["PA6"]; mosi += u2["PA7"]
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
    # ⚠ FIRMWARE, from WCH CH32V203 datasheet table 3-1-3 (read 2026-09-30):
    #   note 6 -- pin 1 is BOOT0 AND PB8 on one pin. It is grounded here, so PB8 must NEVER
    #             be driven as an output: that is a dead short through the pin driver.
    #   note 7 -- on the 28-pin package PA10 and PA11 are ONE pin (19). This board uses it
    #             as PA11 = CAN1_RX, so PA10 must stay an input.
    gnd += u2["PB8"]


    y1 = Part(name="Crystal", ref_prefix="Y", ref="Y1", tag="Y1", dest="NETLIST", tool="skidl",
              value="TAXM8M4RFDCET2T", description="HSE 8 MHz, CL 12 pF (LCSC C403948, the "
              "crystal motor_ctrl and output_panel use) -- CAN bit timing wants a "
              "crystal, not the RC",
              footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P),
                    Pin(num=3, func=P), Pin(num=4, func=P)])
    osc1 += y1[1]; osc2 += y1[3]
    gnd += y1[2], y1[4]
    for tag, net in (("C5", osc1), ("C6", osc2)):
        c = _c(tag, "15pF", "crystal load: 7.5 in series + ~4.5 of pin and track = CL 12")
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

    # ── the sensor, MA730GQ-Z QFN-16 (JLC C161798, the listing; see the header) ──
    # Pins off MPS MA730 datasheet rev 1.1 (8/8/2022) p.2 "package reference" and p.8 "pin
    # functions", read 2026-11-03:
    #   1 SSD  2 A  3 Z  4 MOSI  5 CS  6 B  7 MISO  8 GND
    #   9 PWM  10 TEST  11 MGL  12 SCLK  13 VDD  14 NC  15 SSCK  16 MGH ; 17 the pad
    # Only VDD (13) sits where the MT6701's did, so C11 stays at that corner.
    # Read over SPI (p.11-14): mode 0 or 3, detected by the part; 25 MHz at most; one 16-bit
    # frame with MOSI 0 returns the angle, MSB first, 14 bits used. A register read is the
    # command 010 + a 5-bit address, and its value comes back in the next frame's high byte.
    # THE FIELD DIAGNOSTIC THE MT6701 GAVE ONLY OVER SSI IS A REGISTER HERE: register 27 bit 7
    # MGH (field over MGHT), bit 6 MGL (under MGLT), thresholds in register 6 (p.18, p.21).
    # A missing, flipped or mis-gapped magnet is the likeliest MECHANICAL fault on a lever,
    # and this reads it without opening the housing -- over the same four wires, so the
    # MGL / MGH output pins (11, 16) are left open.
    # Pin handling (p.8): TEST "connect to ground"; NC "leave unconnected"; CS has an internal
    # pull-up, so the sensor stays deselected while the MCU is in reset and PB5 floats; MOSI,
    # SCLK and SSCK have internal pull-downs. SSD, A, B, Z, PWM, MGL, MGH are outputs: open.
    # The pad: "recommended ... connected to ground" (p.11).
    # VDD is 3.0-3.6 V (p.4), 11.7 mA typical, so 3V3 straight off the LDO, 100 nF at the pin
    # (p.11 asks 1 uF "close to the sensor": C10's 4.7 uF on the same rail is 3.6 mm from the
    # package centre, C11 the 100 nF at the pin itself).
    # Field (p.4): 40 mT minimum, 60 typical, no maximum given. MPS's reference magnet is
    # dia 5 x 3 N35 at a 1.5 gap (p.10); ours is dia 6 x 2.5 at AIR_GAP 1.5 (knee_lever.py),
    # the MT6701's reference. Bench check: MGL clear with MGLT raised to 001 (41 mT rising).
    # Nothing is burned into the part: zero and direction stay in the MCU, as with the MT6701.
    u4 = Part(name="MA730GQ-Z", ref_prefix="U", ref="U4", tag="U4", dest="NETLIST",
              tool="skidl", value="MA730GQ-Z",
              description="14-bit angle sensor, SPI; sensing point = package centre",
              footprint=SENSOR_FP,
              pins=[Pin(num=4, name="MOSI", func=I), Pin(num=5, name="CS", func=I),
                    Pin(num=7, name="MISO", func=O), Pin(num=8, name="GND", func=PWR),
                    Pin(num=10, name="TEST", func=I), Pin(num=12, name="SCLK", func=I),
                    Pin(num=13, name="VDD", func=PWR), Pin(num=17, name="EP", func=PWR)])
    v33 += u4["VDD"]; gnd += u4["GND"], u4["TEST"], u4["EP"]
    sck += u4["SCLK"]; miso += u4["MISO"]; mosi += u4["MOSI"]
    csn = Net("SENS_CSN")
    csn += u4["CS"], u2["PB5"]
    c_sens = _c("C11", "100nF", "sensor decoupling")
    v33 += c_sens[1]; gnd += c_sens[2]


def _sensor_qty():
    """One board per sensed player control: 6 knee levers + 5 pedals."""
    from src import dimensions as D
    return D.N_SENSED


_SENSOR_QTY = _sensor_qty()

# ── WHERE EVERY PART SITS, IN THE CHIP'S FRAME ───────────────────────────────
# Authored about the CHIP, not the board's centre, because the chip is the axle axis:
# it is the one datum the housing, the spec and this file all share, and it does not
# move when an edge does. Board-local comes out of it below, once, via CHIP_XY.
# (They were board-local until 2026-09-30. That is a frame whose origin moves whenever
# the outline changes, so widening the +X edge by 1.025 would have shifted all 28 of
# them 0.5125 mm sideways relative to the chip, silently, while every number here
# stayed the same.)
_PLACE_CHIP = {
        "U4": (0.0000, 0.0000, 0.0),
        # SWD: SWDIO / SWCLK / GND in a row for a clip, NRST stranded (recovery only)
        # one row on a 2.4 mm pitch, 3 mm in from the +Y edge so a name fits on either side
        # of a pad: the names are 3 mm wide at 1.0 mm, wider than the pitch, so they
        # alternate above and below. As a 2 x 2 block they had nowhere to go: DIO landed
        # beside the CLK pad, GND 5 mm from its own, and CLK only fitted at 0.8
        "TP1": (-4.8000, 7.1000, 0.0),     # SWDIO
        "TP2": (-2.4000, 7.1000, 0.0),     # SWCLK
        "TP3": (0.0000, 7.1000, 0.0),      # GND
        "TP4": (-15.1100, 8.0500, 0.0),    # NRST
        # J1 (in) and J2 (out) on end, END TO END, mouths -X, 3.05 in from the -X edge
        # (the spec's figure, unchanged from the 8-way they replace). Placements anchor on
        # the PAD CENTROID: S4B-PH-K's pins are its local y 0, its mouth local +y 6.25, and
        # rot 270 turns +y to -X -- so the pin row sits 6.25 +X of the mouth. Along Z each
        # body is 9.9 (pins 1.95 from either end), the two 0.1 apart (knee_lever.CONN_SPLIT:
        # all the 19.9 window leaves), the pair centred on the board's height, -0.85: J1's
        # pins 7.15..1.15, J2's -2.85..-8.85, way 1 of each at its top.
        "J1": (-19.7000, 4.1500, 270.0),
        "J2": (-19.7000, -5.8500, 270.0),
        "U1": (-9.5000, 7.1500, 0.0),
        # 0.55 toward the regulator (courtyards 0.03 apart), which leaves 3.10 mm between
        # J1 and these two for the reset pad's name at 1.0 mm: RST is 3.07 wide and only
        # went down at 0.8. TP4 sits 0.04 off its old x so the placer's 0.25 grid lands in
        # the 0.03 mm of slack
        "C1": (-12.3500, 7.7500, 0.0),
        "C2": (-12.3500, 6.4500, 0.0),
        # the input damper, above C1 against the +Y edge: pad 2 (the regulator side) over
        # C1's input pad, pad 1 toward the regulator where the bus comes round to it
        "R8": (-12.3500, 8.8500, 180.0),
        # the bus bypass, behind the connector tails between the outgoing 5 V and GND ways
        # (6 and 5): pad 1 (+5V) toward way 6
        "C3": (-15.8400, -3.0000, 90.0),
        # (R5, R6, R7 -- the MT6701's MODE strap and I2C pull-ups -- went with it, 2026-11-03)
        # ⚠ U3 (the MCU) AT 0 ROTATION, AND IT IS A ROUTING DECISION -- measured across all
        # four rotations on the old board (see lever_sensor()). The CAN fan (pins 19-21,
        # 0.4 pitch) closes only with the 0.50/0.25 via; see via_mm.
        "U3": (-11.0000, 2.1500, 0.0),
        "C9": (-5.5000, 3.8000, 0.0),
        "C8": (-3.5000, 3.8000, 0.0),
        # the sensor bypass sits AT the sensor supply pin (13, the north-east corner, on the
        # MA730 as on the MT6701), pad 1 (+3V3) toward it; it was 5 mm away, west of the chip
        "C11": (1.6000, 3.4000, 90.0),
        "C10": (-1.5000, -3.3000, 0.0),
        "Y1": (-12.9000, -2.4000, 0.0),
        # C5/C6 stay east of the crystal: moving them west measured 1 -> 5 unconnected
        "C5": (-8.4000, -1.9000, 0.0),
        "C6": (-8.4000, -3.7000, 0.0),
        # C7 (NRST) steps 2.8 +Y off the MCU's west edge: J1's pads now stand 1.9 from
        # it rather than 3.6, and at its old site it sat squarely in OSC_OUT's escape
        # (pin 3, the pin below NRST) -- 1 unconnected with no legal repair path.
        "C7": (-14.5500, 4.4500, 90.0),
        "U2": (-11.5000, -7.0000, 0.0),
        # the transceiver bypass is on the side VCC and GND are (pins 3 and 2, west), in
        # the 1.2 mm strip between U2 and the connector tails: pad 1 (+3V3) faces pin 3.
        # It was on the far side of the package, 7.7 mm from the pin
        "C4": (-15.8400, -7.1000, 90.0),
        # THE TERMINATOR CORNER. SW1 lies along X between the transceiver and the +X
        # groove band, its lands 8.89 apart; it is 2.3 tall, so its body keeps outside the
        # magnet cap's sweep (CAP_SWEEP_R about the chip). R3 and R4 sit above it,
        # and the two bus clamps lie in a row in the strip between the switch and the
        # bottom edge.
        "R3": (-5.0200, -5.1700, 0.0),
        "R4": (-1.5000, -5.1500, 0.0),
        "SW1": SW1_XY + (0.0,),
        "D2": (-1.6500, -10.2000, 180.0),
        "D3": (0.9500, -10.2000, 180.0),
    }


BOARD_NOTES = {
    # ⚠ THE ONLY BOARD THERE IS MORE THAN ONE OF, AND IT USED TO DECLARE NO COUNT AT ALL.
    # Every other board states it -- optical 1, output_panel 1, motor_ctrl 1, can_tee one
    # per motor -- and this one, the multi-unit board, stated nothing. The count existed
    # only as the BOM's angle-sensor quantity, 11, with no record of what the 11 WERE, so
    # it could not be checked and could not be traced if it moved.
    #
    # It is 6 knee levers and 5 pedals (user, 2026-09-18): one sensed axis each, one
    # angle sensor each, one of these boards each. That is D.N_SENSED, and it reproduces the
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
    # ⚠ NRST's HOP IS DECLARED, NOT LEFT TO THE ROUTER (2026-09-30). U3 pin 4 sits between
    # the crystal pins (2, 3) and its own cap and pad (C7, TP4) are on the far side of the
    # chip from the crystal -- so on F.Cu the reset line MUST cross both oscillator tracks at
    # a 0.4 mm-pitch escape. The router found that hop on some rolls and not others: one net
    # added (the sensor's CSN) left NRST open on five placements out of five. One via in the
    # pocket beside the pin, laid BEFORE routing so the crystal tracks go round it, and the
    # same netlist closes first pass. CHIP frame like the placements (it was board-local
    # (-0.90, 2.30) on the 31.0 board); 0.50/0.25 like the rest of the board.
    "vias": [("NRST", -14.40 + CHIP_XY[0], 1.45 + CHIP_XY[1], 0.25, 0.50)],
    "placements": {_r: (_x + CHIP_XY[0], _y + CHIP_XY[1], _rot)
                    for _r, (_x, _y, _rot) in _PLACE_CHIP.items()},
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
    # ⚠ STITCH EXCEPTIONS: THE SENSOR'S BELLY PAD HAS NO VIA (quality A14, 2026-10-06).
    # The stitcher's 0.3 mm via in its centre is a barrel that drinks the paste (70 % of the
    # MT6701's joint), on the pad that also sets how flat the chip sits over the magnet. The
    # MA730's pad is 1.70 under four 0.69 windows, and the same reasoning holds: it carries
    # no heat (40 mW) and no current of its own, so it is joined to pin 8, the part's ground
    # pin 0.25 mm away, by copper on its own layer, and pin 8 keeps the via to the plane.
    # TEST (pin 10, "connect to ground") is joined to the pad the same way, 0.25 mm across,
    # rather than given a via of its own at the +X groove band.
    "stitch_exceptions": ("U4.17", "U4.10", "U3.1"),   # U3.1: see the pin-1 link at "tracks"
    # ⚠ AND THE MCU'S PIN 1 (VSS, the corner pin) GOES STRAIGHT INTO ITS OWN BELLY LAND.
    # Left to the router it ran north along the package's west edge to a via, and with
    # SCL leaving pin 27 north-eastward that shut SDA -- pin 28, the corner pin between
    # them -- in a 1 mm pocket with no exit: 1 unconnected on every run since J1's
    # ways were re-ordered (2026-10-07). 0.7 mm of copper to the land frees the corner.
    # ⚠ AND THE PASS-THROUGH'S 5 V IS LAID, J1.1 -> J2.1, ON F.Cu (quality A1). Left to the
    # router it went down to In2.Cu at 0.40, and an inner layer needs 0.72 for 0.57 A at a
    # 10 C rise. The two pins share a column with J1's other three between them, so the
    # track steps 1.9 toward the mouth, under J1's own body (nothing else may stand there:
    # the connector zone), runs down, and steps back. 0.725 clear of every pad's edge.
    # The sensor's two links (stitch_exceptions), in the CHIP frame like the placements: the
    # board frame is y-up, so KiCad's pin 8 at (+0.75, +1.45) is chip (+0.75, -1.45) and pin 10
    # at (+1.45, +0.25) is chip (+1.45, -0.25). Each runs from inside its pad's heel (1.10 from
    # centre) to inside the 1.70 pad's edge (0.85), 0.30 clear of the pins either side.
    "tracks": [("+5V", "F.Cu", 0.5, [(-7.2125, 8.00), (-9.1125, 8.00), (-9.1125, -2.00),
                                     (-7.2125, -2.00)]),
               ("GND", "F.Cu", 0.2, [(0.75 + CHIP_XY[0], -1.20 + CHIP_XY[1]),
                                     (0.75 + CHIP_XY[0], -0.70 + CHIP_XY[1])]),
               ("GND", "F.Cu", 0.15, [(1.20 + CHIP_XY[0], -0.25 + CHIP_XY[1]),
                                      (0.70 + CHIP_XY[0], -0.25 + CHIP_XY[1])]),
               ("GND", "F.Cu", 0.15, [(-0.45, 4.20), (0.10, 4.20), (0.50, 3.80)])],
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
    # ⚠ (2026-10-06: THE ORDER PAGE DISAGREES WITH WHAT FOLLOWS. The reading of the
    # capability page below concluded "not surcharged"; a real order of a board with the
    # same 0.50/0.25 via was charged about 17 USD for it, plus a Kelvin test and Tg155 the
    # form adds with it. The geometry argument stands; the cost claim does not, and
    # order_options below says what the form actually does.)
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
    # the lever bus passes THROUGH this board (J1 in, J2 out), so the first board of
    # a chain carries every later board supply: up to bus B limit, 0.57 A
    "net_widths": {"+5V": 0.4},
    # the words the silkscreen uses. A legend is as wide as its longest line and this
    # board is 32 x 22: at the full net names the J1 legend and one SWD label only went
    # down at 0.8 mm, under the fab minimum of 1.0
    "silk_labels": {"TP1": "DIO", "TP2": "CLK", "TP4": "RST", "SW1": "TERM",
                    "CAN_H": "H", "CAN_L": "L", "+5V": "5V"},
    # ⚠ THE VIA SIZE IS AN ORDER-FORM FIELD, NOT JUST A GERBER FACT. JLCPCB's own
    # capability page says "please select corresponding via size option when placing
    # order" for 0.2/0.25 mm hole sizes. The gerbers carry the geometry; the process is
    # chosen on the form, and nothing in the drill file makes the operator pick it.
    "order_options": {
        "via size": "0.25 mm hole / 0.50 mm diameter -- SELECT THIS ON THE ORDER FORM. It is "
                    "CHARGED FOR, whatever the capability page suggests (order page, "
                    "2026-10-06): about +17 USD for the via size, and choosing it makes "
                    "the form add a 4-wire Kelvin test (+17) and Tg155 material (+3.5 "
                    "to 7.8) by itself. The board does not route at the 0.6/0.3 default -- see the CAN fan note.",
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
    "groove_exempt": ["U4", "J1", "J2"],
    # J1 + J2's zone (spec rule 4): their bodies (7.6 deep) and the mated plugs' run past
    # the mouths, over the pair's 19.8 -- x ..-5.86 here, clipped to the board as before.
    "conn_keepout": {"box": [-15.5, -9.9, -5.86, 9.9], "exempt": ["J1", "J2", "U4"]},
    # ── the quality pass (cadkit/PCB_QUALITY.md) ─────────────────────────────
    "quality": {
        # A17 (cadkit/PCB_QUALITY.md): a connector whose pinout block is on the OTHER face,
        # and why. Way 1 is marked on the connector's own side in every case.
        "connector_labels": {
            "J1": {"back_only": "the labeller finds no free site on the front for a word at each way (run 2026-10-19): -X of the pins is the connector's own body and its plug's run, +X of them the parts that sit against it. The pins come through, so each gets its word on the back, in line with it"},
            "J2": {"back_only": "as J1, the connector below it: no front site for its words (run 2026-10-19), a word at each pin on the back where the pins come through"},
        },
        # A8 asks for a via in every exposed pad; the sensor's has none, deliberately (the
        # note at stitch_exceptions). A8's own exception: a part that needs no heat path,
        # with the pad still on its net by copper on its own layer.
        "waive": {
            "A8:U4": "MA730, about 40 mW (11.7 mA at 3.3 V): its 1.70 mm exposed pad needs no "
                     "heat path, and a via in it would take most of its paste (A14). The pad is "
                     "on GND through 0.25 mm of F.Cu to pin 8, whose own via reaches the plane",
        },
        "power_paths": [
            # the bus passes through: the first board of a chain carries the rest, up to
            # the 565 mA maximum of motor_ctrl's TPS2553 at 49.9 k
            {"net": "+5V", "from": "J1.1", "to": ["J2.1"], "amps": 0.57},
            # this board: MCU ~10 mA at 48 MHz, sensor 10 mA, transceiver 17 mA dominant
            # plus ~35 mA into the bus while it drives -- 80 mA with margin
            {"net": "+5V", "from": "J1.1", "to": ["R8.1"], "amps": 0.08},
            {"net": "+5V_LDO", "from": "R8.2", "to": ["U1.1"], "amps": 0.08},
            {"net": "+3V3", "from": "U1.5", "to": ["U3.17", "U3.5", "U2.3", "U4.13"],
             "amps": 0.08},
        ],
        # A13 (cadkit/PCB_QUALITY.md): what the DESIGN leaves open, and how many nets each
        # repeated structure is on. The pass fails on any difference from the routed board.
        "unconnected": {
            "U1.4": "the maker's NC pin",
            "U2.5": "SN65HVD230 Vref output: nothing here uses the reference",
            "U3": {
                "pins": "6 7 8 9 10 14 15 18 23 24 25 27 28",
                "why": "GPIO this board gives no function: left open, firmware leaves it an input with pull-down"
            },
            "U4": {
                "pins": "1 2 3 6 9 11 14 15 16",
                "why": "MA730 (rev 1.1 p.8): SSD, A, Z, B, PWM and the MGL / MGH flag outputs, the SSI clock input (internal pull-down) and NC; the angle and the field flags are read over SPI only"
            }
        },
        "net_groups": [
            {
                "name": "bus B in and out are the same four ways",
                "pins": [
                    "J[12].[1-4]"
                ],
                "nets": 4,
                "each": 2
            },
            {
                "name": "one CAN transceiver: TX and RX each reach the MCU",
                "nets_like": "CAN_(TX|RX)",
                "count": 2,
                "pads": 2
            },
            {
                "name": "the transceiver's bus pins",
                "pins": [
                    "U2.[67]"
                ],
                "nets": 2,
                "each": 1
            },
            {
                "name": "one angle sensor: its four SPI pins",
                "pins": [
                    "U4.[457]",
                    "U4.12"
                ],
                "nets": 4,
                "each": 1
            }
        ],
        "pinouts": {
            "S4B-PH-K-S": "KiCad JST_PH_S4B-PH-K_1x04_P2.00mm_Horizontal (generated from "
                          "JST's ePH drawing, which refuses a scripted fetch): pins 1-4 on "
                          "local x 0..6, mouth +y 6.25. J1 and J2 are each "
                          "harness.PH_PINOUT (5 V, GND, CAN_H, CAN_L) on ways 1-4, no "
                          "mounting pegs or tabs. Read 2026-10-19",
            "AP2112K-3.3TRG1": "Diodes DS39724 p.1-2, Pin Descriptions, SOT25 column: 1 VIN, "
                               "2 GND, 3 EN (high = on), 4 NC, 5 VOUT. Board: 1 +5V_LDO, 2 GND, "
                               "3 +5V_LDO, 4 open, 5 +3V3. Read 2026-10-04",
            "SN65HVD230DR": "TI SLOS346 Pin Functions (SOIC-8): 1 D, 2 GND, 3 VCC, 4 R, "
                            "5 Vref, 6 CANL, 7 CANH, 8 RS. Board: 1 CAN_TX, 2 GND, 3 +3V3, "
                            "4 CAN_RX, 5 open, 6 CAN_L, 7 CAN_H, 8 slope resistor. Re-read "
                            "2026-10-04",
            "CH32V203G6U6": "WCH CH32V203 datasheet V2.8 table 3-1-3 (pp. 8-10), the QFN28 "
                            "(G6) column, read off the page image because the text layer "
                            "scrambles it: 0 VSS (the exposed pad, KiCad pad 29), 1 BOOT0 / "
                            "PB8, 2 OSC_IN, 3 OSC_OUT, 4 NRST, 5 VDDA, 16 VSS, 17 VDD, "
                            "19 PA10 and PA11 on ONE pin (note 7) = CAN1_RX, 20 PA12 = "
                            "CAN1_TX, 21 PA13 = SWDIO, 22 PA14 = SWCLK, 26 PB5. Board: "
                            "those, pin 1 to GND, pin 26 the sensor CS. Read 2026-10-04. "
                            "SPI1 added 2026-11-03 off datasheet V3.0 table 3-1-3 (QFN28 "
                            "column, from the JLC parts record's copy): 11 PA5 = SPI1_SCK, "
                            "12 PA6 = SPI1_MISO, 13 PA7 = SPI1_MOSI, their default "
                            "functions; 27 PB6 / 28 PB7 now open",
            "MA730GQ-Z": "MPS MA730 datasheet rev 1.1 (8/8/2022) p.2 package reference "
                         "(top view) and p.8 pin functions: 1 SSD, 2 A, 3 Z, 4 MOSI, 5 CS, "
                         "6 B, 7 MISO, 8 GND, 9 PWM, 10 TEST, 11 MGL, 12 SCLK, 13 VDD, 14 NC, "
                         "15 SSCK, 16 MGH, 17 the pad. Land off p.26 (Steel.pretty). Board: "
                         "4 SENS_MOSI, 5 SENS_CSN, 7 SENS_MISO, 12 SENS_SCK, 13 +3V3, 8 / 10 / "
                         "the pad GND, the rest open. Read 2026-11-03",
            "TAXM8M4RFDCET2T": "Yajingxin TAXM8M4RFDCET2T sheet (LCSC C403948), 'Connection' "
                               "drawing: lands 1 and 3 are the crystal, 2 and 4 the can "
                               "(GND). Board: 1 OSC_IN, 3 OSC_OUT, 2 / 4 GND. Read "
                               "2026-10-04",
        },
        # The manual review, 2026-10-04. Each entry is the evidence, not a tick. Left OPEN on
        # purpose: M11 (the CAD fit, after these placements reach the build), M35 (errata)
        # and the order-time items M12, M29, M30, M37, M42.
        "manual": {
            "M35": "read 2026-10-05. " + 'WCH publishes no errata sheet: its product page lists the datasheet and the reference manual (CH32FV2x_V3xRM) and nothing else, read 2026-10-05. ' + "(CH32V203: same "
                   "manual.) The other parts were not searched for errata sheets",
            "M1": "each hop is a straight PHR-4 jumper (INSTALL_NOTES, KL-6): J1 the bus "
                  "in and J2 the bus out, both in harness.PH_PINOUT order (5 V, GND, CAN_H, "
                  "CAN_L), the list motor_ctrl J2 / J6 and the leg boards are built from. "
                  "J1 and J2 are the same four nets on this board, so in and out may be "
                  "swapped without effect. "
                  "The housing is polarised and a PH cannot enter an XH, so a lever lead "
                  "cannot reach a 24 V motor tee",
            "M2": "no polarised two-pad part: D2 / D3 are bidirectional, every capacitor "
                  "is ceramic",
            "M3": "In1 is an unbroken GND plane under the whole board and B.Cu carries a "
                  "second GND pour. The pass-through's return (up to 0.57 A) goes J2.2 -> "
                  "plane -> J1.2, 10 mm, directly under its own +5V track. No slot, no "
                  "split; the regulator and every IC ground drop into the plane on their "
                  "own vias",
            "M4": "U1 (AP2112K, DS39724): asks 1 uF ceramic at IN and at OUT. C1 1 uF at "
                  "IN behind R8; C2 1 uF at OUT plus C10 4.7 uF and four 100 nF on the same "
                  "rail. Nothing on this board steps current. No rating is written on a "
                  "value here because the highest rail is 5 V and the fab's 0402 parts at "
                  "these values are 6.3 V or more; C3, the one capacitor that can see a "
                  "hot-plug ring (about 10 V), is called out as a 16 V part",
            "M5": "+5V bus: C3 (16 V), R8 and the connector only. +5V_LDO: U1, absolute "
                  "maximum 6.5 V, behind R8 (M16). +3V3: MCU 3.6 V max operating, sensor "
                  "3.3-5 V, transceiver 3.6 V. CAN pins: the SN65HVD230 stands -4..16 V "
                  "and the bus supply is 5 V, so no fault on this bus exceeds it; D2 / D3 "
                  "clamp ESD. R4 carries 17 mA: 34 mW, and 75 mW with the bus held dominant at 3 V, in an 0402 rated "
                  "100 mW (ERJ2RKF1200X; the house 0402 is 62 mW and was not used). R8 carries "
                  "80 mA: 14 mW",
            "M6": "nothing fast: CAN at 1 Mbit/s with slope control, SPI to the sensor at "
                  "a few MHz over about 12 mm (the part takes 25), an "
                  "8 MHz crystal 3.4 and 5.5 mm from its pins",
            "M7": "U1: EN tied to IN, fixed 3.3 V part. U2 (SLOS346): RS through 10 k to "
                  "GND = slope control; Vref left open, as the sheet allows. U4 (MA730 "
                  "rev 1.1 p.8, p.11): TEST and the pad to GND, NC open, 100 nF at VDD, "
                  "SPI mode detected by the part. U3: 8 MHz crystal on OSC_IN / OSC_OUT (M24), "
                  "100 nF on NRST, VDDA and VDD on the same rail with a capacitor each",
            "M8": "BOOT0 (pin 1) hard to GND: the board is programmed over SWD only. NRST: "
                  "the MCU's internal pull-up and C7. U1 EN: tied to IN. U2 RS: R3 to GND. "
                  "U4 CS: SENS_CSN is an MCU output and floats until firmware drives "
                  "it; the sensor's own pull-up holds it high (deselected) until then",
            "M9": "SWD on bare 1 mm pads in a row on the magnet face, each with its name "
                  "beside it at 1.0 mm: DIO, CLK, GND, and RST by the connector. No 3V3 "
                  "pad: the rail is probed on C10 or C2, and the board reports itself "
                  "over CAN once it runs",
            "M10": "CAN_H / CAN_L: D2 / D3 (ESD5B5.0ST1G, bidirectional) from each line to "
                   "GND. They sit about 8 mm PAST the transceiver's bus pins, beyond the terminator switch, not at J1: the "
                   "only strip beside the connector tails is 1.16 mm wide and holds the two "
                   "bypass capacitors. Accepted because the transceiver's bus pins are "
                   "themselves rated 16 kV HBM and the fault this pair was first fitted "
                   "for (24 V swept onto the bus by a plug) cannot happen on a 5 V bus. "
                   "Reverse polarity: one polarised housing. Over-current: the bus is "
                   "limited to 0.52 A by motor_ctrl's U6",
            "M15": "AP2112K is ceramic-stable from 1 uF. Effective output capacitance at "
                   "3.3 V of bias is about 0.6 uF (C2) + 2.5 uF (C10) + 0.3 uF (the four "
                   "100 nF): over 3 uF. Headroom: 5 V less 0.3 V of harness less 0.18 V "
                   "in R8 is 4.5 V at the pin, against 3.3 V + 0.25 V of dropout. It "
                   "dissipates 1.2 V x 80 mA = 0.1 W at most",
            "M16": "a pedal board is reached through the leg's spring pins, a joint that "
                   "can be made with the bus live. R8, 2.2 ohm, is in series with the "
                   "regulator's input capacitor: a metre of 26 AWG (about 1 uH, 0.3 ohm) "
                   "into 1 uF has a damping ratio near 0.2 without it (a ring to about "
                   "7.6 V against 6.5 V absolute maximum) and about 0.9 with it. C3 on the "
                   "bus side rings freely and is a 16 V part with nothing else on its net",
            "M18": "every board on bus B takes its 5 V from the same switch, so they rise "
                   "and fall together; a board left unplugged presents no supply and the "
                   "SN65HVD230's bus pins are high-impedance unpowered (SLOS346). An SWD "
                   "probe is the one outside driver and is connected with the board "
                   "powered",
            "M20": "SPI to the sensor: push-pull both ways, no pull-ups; CS idles high on "
                   "the part's own pull-up. "
                   "CAN: R4 120 ohm behind SW1, ON only on the board at each far end "
                   "of bus B (two in all; the controller sits mid-bus and carries "
                   "none). This board's stub from J1 to the transceiver is about 15 mm",
            "M21": "the sensor's ground pin drops into the In1 plane on its own via, its pad "
                   "and TEST reach that pin on F.Cu, C11 is 0.9 mm from its supply pin, and the only regulator is "
                   "linear -- chosen for that, in place of the buck that stood 15 mm "
                   "from the sensor",
            "M22": "no op-amp on this board",
            "M24": "Y1 TAXM8M4RFDCET2T, CL 12 pF. C5 = C6 = 15 pF: 7.5 pF in series plus "
                   "about 4.5 pF of pin and track = 12 pF. The same crystal and capacitors "
                   "as motor_ctrl and output_panel",
            "M25": "two exposed pads, both GND. The MCU's is on a via to the plane (A8) and "
                   "dissipates about 35 mW. The sensor's (U4, about 40 mW) has NO via, on "
                   "purpose: a 0.3 mm barrel would take most of that 1.70 mm pad's paste "
                   "(A14), so it is joined to pin 8 on its own layer and pin 8's via "
                   "carries its ground. Neither needs the pad for heat",
            "M26": "CAN_TX: MCU pin 20 (PA12, CAN1_TX) to U2 pin 1, D, the driver input. "
                   "CAN_RX: U2 pin 4, R, the receiver output, to MCU pin 19 (PA11, "
                   "CAN1_RX). SPI1: MCU pin 11 (PA5, SCK) to the sensor's 12 (SCLK), 12 (PA6, MISO) "
                   "to its 7 (MISO, the sensor's output), 13 (PA7, MOSI) to its 4 (MOSI); "
                   "PB5 (26) to its 5 (CS)",
            "M27": "BOOT0: tied to GND, nothing else on the pin (the package shares it "
                   "with PB8, which is therefore unused). SWDIO / SWCLK: a test pad each, "
                   "nothing else. NRST: C7 and a test pad. Pin 19 is PA10 and PA11 bonded "
                   "together (datasheet note 7): it is CAN1_RX here and firmware must "
                   "leave PA10 an input",
            "M28": "CH32V203G6U6 is the QFN28 'G6' column of table 3-1-3, not the QSOP28 "
                   "G8 one (different numbering). MA730GQ-Z is the QFN-16 on tape and reel "
                   "(-Z), the only package it comes in. AP2112K-3.3TRG1 is the SOT-25 part and SN65HVD230DR "
                   "the SOIC-8. Each read against the footprint "
                   "the board places (quality.pinouts)",
            "M31": "no polarised two-pad part to mark. Each IC's pin-1 mark is the KiCad "
                   "footprint's own silk, outside the body; J1, J2 and the four SWD pads are "
                   "named in silk at 1.0 mm; the terminator switch says TERM; the pinout "
                   "legend and the board name are on the back",
            "M41": "SW1 is not read by anything: it puts R4 across the pair or does not, "
                   "and is set once, on the bench, before the board goes into its "
                   "housing. Nothing to debounce",
            "M32": "J1 and J2 are JST PH, 2.0 mm, the family the lever harness is crimped in "
                   "(harness.PH_PINOUT). PH contacts are rated 2 A; the most this bus can "
                   "deliver is 0.57 A",
            "M33": "5 V in: MCU about 10 mA, sensor 10 mA, transceiver 17 mA dominant "
                   "plus about 35 mA into the bus while it transmits: 25 mA idle, 75 mA "
                   "peak, through a 600 mA regulator. Bus B: eleven boards idle at 25 mA "
                   "and one transmitting is about 0.33 A against U6's 0.475 A minimum "
                   "limit",
            "M34": "CAN_TX / CAN_RX, SPI and SWD are all 3.3 V at both ends. The sensor "
                   "runs from 3.3 V, so its outputs cannot exceed the MCU's rail",
            "M36": "the pass-through J1 -> J2 is the bus itself: limited upstream to "
                   "0.52 A by motor_ctrl's U6, carried here on 0.4 mm copper and 2 A "
                   "contacts. This board adds no source",
            "M38": "the board is held by printed grooves on its two long edges; every "
                   "part stands at least 1.85 mm in from them (groove_keepout_x). J1 "
                   "and J2 take plug force on their four through-hole joints each. Every "
                   "part is on the magnet face (single_sided); J1 / J2's pins come "
                   "through to the back, where the cradle has no wall",
            "M39": "MCU: unused GPIO are left open and set by firmware to pulled inputs; "
                   "PB8 is grounded with BOOT0. U4: SSD, A, B, Z, PWM, MGL, MGH are outputs, "
                   "left open; SSCK has its own pull-down; NC is open; TEST is grounded. U2 Vref: an output, open. U1 pin 4: NC",
            "M40": "the generator carries the record beside each value: the crystal and "
                   "its capacitors (M24), R8 (M16), the 0.50 / 0.25 via the MCU's fan "
                   "needs, the row of SWD pads, the capacitor at each supply pin, and "
                   "the MCU rotation (measured, not chosen)",
        },
    },
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
    import volts_decl                   # A16: generated, see volts_decl.py
    volts_decl.into(BOARD_NOTES, "lever_sensor")
    with open(os.path.join(OUT_DIR, "lever_sensor.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements, chip on the axle at (%.1f, %.1f)"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]), *CHIP_XY))
