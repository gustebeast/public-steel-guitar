"""FOOT LIGHTING board -- a 572.72 mm strip firing DOWN through the chassis window.

    py -3.12 elec/foot_led.py       # -> elec/out/foot_led_{a,b}.{net,board.json}

    286.36 (B) and 293.36 (A) x 24.15, 4 layers, 36 LEDs, 12 zones, 4 x TLC59711 each.

The other lighting job (elec/fret_led.py is the first). It lies on top of the transparent
band through the chassis's bottom prism and shines into it; the 10.80 mm of PCTG is the
diffuser and the player's feet are what comes out the other side.

⚠ THE GEOMETRY IS AN INPUT, like the fret boards and the optical board: the window's
length, the LED pitch, the board span, the Z stack and both lane positions come from
`src/foot_light.py`, which measured them off the chassis. Nothing here is retyped.

⚠ TWO BOARDS, AND IT IS THE ASSEMBLER'S LIMIT. JLCPCB's published capability, read from
the page 2026-09-30: **Economic PCBA takes a single PCB from 10x10 to 470x500 mm,
Standard from 70x70 to 460x500.** 572.72 is past both, so one board cannot be built at
any price. Two of 286.36 are a long way inside.

⚠ AND TWO DESIGNS, WHICH DIFFER ONLY AT THEIR ENDS (user, 2026-10-04). Both slide in from
-X, the far one first, so nothing can be plugged into the far board once it is home and
the joint between them is POGOS, tip to tip, made by pushing the second board against
the first. The near board is the one a cable can reach:

    Pi cap J6 --cable--> J1 [board A] J21..J24 -><- J11..J14 [board B]

A is fed by a 4-way JST XH on a 7 mm tail at its -X end (XH is the instrument's 24 V
connector; PH is its 5 V one) and carries the seam's four pogos at its +X end;
B carries the seam's four at its -X end and nothing at the other. 24 V passes straight
through A behind its fuse and the SPI chain runs J1 -> U1 .. U4 -> seam -> U1 .. U4, so
all eight drivers are one stream from one Pi pin.

⚠ AND THE SEAM COSTS NO LIGHT. The pogos stand beside the LED row, not in it, so the row
runs to within half a pitch of both edges and the two boards butt: one pitch from end to
end, with the seam falling exactly half a pitch past the last LED of the first board.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import foot_light as FL  # noqa: E402  (the geometry source -- see above)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import skidl  # noqa: E402
from skidl import ERC, Net, Part, Pin, generate_netlist  # noqa: E402

import netcheck  # noqa: E402
from placecheck import check_placement, fp_box  # noqa: E402
import buck_cell as BC  # noqa: E402

P = Pin.types.PASSIVE

# ── the parts: every one is already bought for another board ────────────────────
LED_FP = "Steel:XINGLIGHT_XL-5050RGBW"
DRV_FP = "Package_SO:HTSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3.4x6.5mm_Mask2.75x3.43mm"
BUCK_FP = "Steel:Texas_RNX0012_VQFN-HR-12_2x3mm_P0.5mm"
IND_FP = BC.L1_FP                    # with its reason, in buck_cell
R_FP = "Resistor_SMD:R_0402_1005Metric"
C_FP = "Capacitor_SMD:C_0402_1005Metric"
C08_FP = "Capacitor_SMD:C_0805_2012Metric"
C12_FP = "Capacitor_SMD:C_1206_3216Metric"
FUSE_FP = "Fuse:Fuse_1206_3216Metric"
# (No cable socket: the JST SH this board carried at each end went with the jumper. The
#  -X board still passes both boards' 0.77 A, through one pogo rated 12 A.)

R_IREF = "3k3"                       # 15.0 mA per channel, as the fret boards
# ⚠ 11.50 V, AND THE STRING LENGTH IS THE ONLY THING THAT SETS IT. A channel sinks
# constant current from the rail down through its series string, so the rail has to sit one
# string plus the sink's headroom above ground -- and every volt above that is heat in the
# driver rather than light.
# ⚠ THE STRING IS 10.2 V, NOT 9.6 (manual quality pass, 2026-10-05). XINGLIGHT's sheet
# gives green, blue and white 3.0 to 3.4 V at 20 mA, +-0.1 -- this file said "3.2 max".
# Three in series (src/foot_light.N_SERIES) is 10.2 V at the top of the bin. The sink is
# flat from about 0.3 V at 15 mA (TI SBVS181A figure 12). At the 11.00 V this rail was,
# its low tolerance (10.64 V: 0.985 V reference, 1 % resistors) left 0.44 V; at 11.50 it
# leaves 0.92.
#
# R10 over (R11 parallel R12) on the LMR33630's 1.000 V reference: 100k / (10k || 200k).
# Two stock values instead of one 9.53k, which JLCPCB only carries as an extended part.
R_FBT, R_FBB, R_FBP = 100e3, 10e3, 200e3
V_RAIL = round(1.0 * (1.0 + R_FBT / (R_FBB * R_FBP / (R_FBB + R_FBP))), 2)      # 11.50
assert abs(V_RAIL - 11.50) < 0.005, V_RAIL
I_CHAN = 0.015
COLOURS = ("R", "G", "B", "W")
# THE SEAM AND THE INLET ARE POGOS: four Xinyangze YZF0002-38080-02 (LCSC C5203987) at
# each end, tip to tip with the next board's -- src/foot_light.py owns where they stand
# and src/pogo_part.py what they are. The 4-way SH sockets this board carried are gone,
# and with them the jumper nothing stocked was short enough to be.
POGO_FP = "Steel:Xinyangze_YZF0002-38080-02"
# THE INLET, board A only: a side-entry JST XH, S4B-XH-SM4-TB (LCSC C161861) -- the Pi
# cap's own XH part.
# ⚠ XH BECAUSE IT IS 24 V. The instrument's rule (user, 2026-10-04): PH carries 5 V and XH
# carries 24 V, so no lead can put the higher rail on the lower one's socket.
# ⚠ AND THE ORDER IS harness.XH_PINOUT's -- GND, V24, then the two signals -- so the one
# mistake still possible is harmless both ways round: a motor-bus lead on this socket
# powers the board correctly and lays CAN on the two SPI inputs, and this lead on a
# motor-bus socket lays 3.3 V logic on CAN. Neither reverses a supply.
J_FP = "Connector_JST:JST_XH_S4B-XH-SM4-TB_1x04-1MP_P2.50mm_Horizontal"
J_PINS = ("GND", "+24V_IN", "SCK_CABLE", "SDT_CABLE")
# ── 1 k IN SERIES WITH EACH SIGNAL AT THE CABLE (manual quality pass M18, 2026-10-05) ────
# The Pi drives SCK and SDT at 3.3 V through 68 ohm (pi_cap R1..R4), and this board can be
# dark while the Pi is up: its fuse open, the lights' fuse on the motor board open, the
# 24 V lead off, or a Pi on its own USB supply on the bench. A TLC59711's inputs are rated
# to VREG + 0.6 V (SBVS181A 7.1), and VREG is 0 V then: the pin's protection diode
# conducts and the Pi powers the driver's logic through it, as much as a GPIO will give.
# 1 k limits that to 2.7 mA. Against the pin's few pF it is a 10 ns corner, on a clock
# TI allow to 10 MHz and edges the source resistor has already slowed.
R_SERIES = "1k 1%"
# They stand just past the socket's courtyard, each on its own land's line. Measured on the
# routed board from J1's pad centroid: the lands' centres are 3.25 towards +X, the
# courtyard ends at 6.05, and ways 3 and 4 are 1.24 and 3.74 towards the LED row.
J_SERIES = (("R21", 7.30, -1.24), ("R22", 7.30, -3.74))
J_ANCHOR = 5.30 + 0.9833             # mouth (local +Y 5.30) to the PAD CENTROID (the mean
                                     # of its six pads), both read out of the .kicad_mod
J_Y = FL.to_board_y(FL.J_Y)
import harness as _H                                  # noqa: E402
assert tuple(n.replace("+24V_IN", "V24") for n in J_PINS[:2]) == tuple(_H.XH_PINOUT[:2]), (
    "the foot strip's socket is an XH and its supply ways are not the XH bus's own")
from src import board_geom as _BG                     # noqa: E402
assert abs(_BG.HEIGHT[_BG.fp_name(J_FP)] - FL.XH_H) < 1e-9, (
    "foot_light.XH_H is %.2f and board_geom draws the socket %.2f tall"
    % (FL.XH_H, _BG.HEIGHT[_BG.fp_name(J_FP)]))

# ── the two lanes ────────────────────────────────────────────────────────────────────
# ⚠ BOARD-LOCAL Y IS A MIRROR OF WORLD Y, because this board is installed FACE DOWN: the
# CAD turns it over about X to point the LEDs at the floor, which negates Y as well as Z.
# foot_light.to_board_y() is the one place that conversion lives. Getting it backwards
# would put the LED row on the wrong side of an 8 mm window and nothing downstream would
# notice -- the board routes, the CAD renders, and the light misses the slot.
LED_Y = FL.to_board_y(FL.led_y())           # -3.75
LANE_Y = FL.to_board_y(FL.DRV_Y)            # +4.05
BOARD_W = FL.BOARD_W                        # 17.20

# ⚠ THE MIDDLE ZONE TAKES THE PINS NEAREST THE LED ROW, and getting that backwards is
# what left the last net unrouted for three attempts. At rot 0 the HTSSOP's pins run in
# Y: the -X column is pins 1..10 top to bottom, the +X column 11..20 bottom to top, so
# outputs 8 and 13 are the LOWEST -- and LOW is where the LED row is, 7.80 mm below the
# lane. Every return on this board comes up from there.
#
# The table was copied from fret_led.py, where the driver sits BETWEEN two LED rows and
# "the tops of both columns" is the right answer for the zone underneath it. Here there
# is one row, below, so the middle zone -- whose four returns arrive in the package's own
# shadow with nowhere to go round -- wants the bottom pins, and the +-X zones can take
# the tops because they arrive from the sides and can climb on the way in.
ZONE_OUTS = {-1: (3, 4, 5, 6), 0: (7, 8, 13, 14), 1: (15, 16, 17, 18)}

# ── THE DRIVER'S HEAT PAD: SEVEN VIAS, NOT ONE (manual quality pass M25, 2026-10-05) ────
# The stitcher gives an exposed pad one via at its centre, which is a ground connection
# and not a heat path: one 0.25 mm barrel down 1.28 mm to the ground plane is about
# 200 C/W, under a part that dissipates most of a watt at full white. TI's land pattern
# for this package (SBVS181A, PWP land pattern data) draws fifteen 0.3 mm vias on a 1.3 mm
# grid across the 3.4 x 6.5 copper.
# ⚠ SIX MORE, AND ONLY UNDER THE SOLDER MASK. The pad's copper is 6.5 long but only the
# middle 3.43 is opened and pasted; the two ends are mask over copper. Vias there cost no
# paste, where each one inside the opening would drink a tenth of what is printed. Three
# across each end, on TI's own 1.3 mm pitch: with the centre one about 30 C/W to the plane.
DRV_PAD_VIAS = tuple((dx, dy) for dy in (-2.60, +2.60) for dx in (-1.30, 0.0, +1.30))

# ── THE BUCK'S CELL: where each of its parts stands, measured from U10 ────────────────
# ⚠ THE OPTICAL BOARD'S U13 CELL, WHICH WAS MEASURED AGAINST TI'S LAYOUT EXAMPLE on a
# routed board (elec/optical.py M13): the same IC in the same package. The RNX has a VIN
# and a PGND pin on EACH long side, and TI puts a small 50 V capacitor across each pair
# (SNVSAN3F 9.2.2.6); this board had one, on one side. C32 and C35 are the pair.
# (dx, dy, rot) from U10's placement point.
# The package's seven close parts, the bulk row and the laid copper are all
# elec/buck_cell.py's, shared with the keyhead fret board. This board adds a fuse and
# three test pads, in the same row: X is the only axis a strip has.
# ⚠ EVERY 1206 STANDS ACROSS THE STRIP (manual quality pass M38, 2026-10-05), the fuse
# included. A 290 x 17 mm board bends along its length when it is handled, and a large
# ceramic lying along that bend takes the strain through its two solder joints and
# cracks. Turned a quarter turn the same bend only rocks it.
BUCK_REFS = {"CIN_A": "C32", "CIN_B": "C35", "CBOOT": "C33", "CVCC": "C34",
             "RFBB": "R11", "RFBT": "R10", "RFBP": "R12"}
BULK_REFS = {"CIN_1": "C30", "CIN_2": "C31", "L1": "L1",
             "COUT_1": "C36", "COUT_2": "C37", "COUT_HF": "C38"}
BUCK_CELL = dict({ref: BC.CORE[role] for role, ref in BUCK_REFS.items()},
                 **{ref: BC.BULK[role] for role, ref in BULK_REFS.items()})
BUCK_CELL.update({
    "F1": (-10.75, 0.0, 270.0),        # its +24V end beside the input bulk's own
    # THREE TEST PADS, bare copper, labelled by kicad_silk with their nets (M9): the two
    # rails a first power-up is checked on, and a ground beside them for the other probe.
    "TP1": (-13.40, 0.0, 0.0),         # +24V, after the fuse
    "TP2": (+18.00, 0.0, 0.0),         # the rail
    "TP3": (+20.60, 0.0, 0.0),         # GND
})
TP_FP = "TestPoint:TestPoint_Pad_D1.5mm"
BUCK_X = -1.75                       # U10 itself: centres the cell on the board


def _r(ref, value, desc, fp=R_FP):
    return Part(name="R", ref_prefix="R", ref=ref, tag=ref, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(ref, value, desc, fp=C_FP):
    return Part(name="C", ref_prefix="C", ref=ref, tag=ref, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


class Row(object):
    """A cursor that lays parts along the component lane with a real gap between them.

    The lane is 9.30 mm tall and 286 long, so X is the only axis worth spending and the
    only thing that can go wrong is two parts touching. check_placement catches that
    anyway; this just makes the spacing an outcome of the part sizes rather than of
    thirteen numbers typed by hand -- which is how the fret board's bay went wrong twice.

    `dirn` lays a row out towards -X instead of +X, which is what the drivers' own
    passives need. At 12 zones this board had two drivers with the whole middle to
    themselves; at 24 it has four, and the inner two would walk their passives straight
    into the supply block. Sending every driver's passives OUTBOARD keeps the middle clear
    symmetrically and needs no clamp.
    """

    def __init__(self, place, fps, x, gap=0.45, dirn=1.0, y=None):
        self.place, self.fps, self.x, self.gap, self.dirn = place, fps, x, gap, dirn
        self.y = LANE_Y if y is None else y

    def add(self, ref, fp, rot=0.0):
        w, h = fp_box(fp)
        if round(rot) % 180:
            w = h
        self.x += self.dirn * w / 2.0
        self.place[ref] = (self.x, self.y, rot)
        self.fps[ref] = fp
        self.x += self.dirn * (w / 2.0 + self.gap)
        return self



def _manual(board, n_drv):
    """The manual quality items (cadkit/PCB_QUALITY.md), signed 2026-10-05 against the
    routed boards and the makers' sheets. M12 is left open on purpose: what remains of
    it can only be done on the day of the order (.ins/WORKLIST-brenner.md, NEEDS USER)."""
    a = board == "a"
    seam = ("J21..J24" if a else "J11..J14")
    m = {
        "M1": ("two joints. J1 to the Pi cap's J6: a 4-way JST XH lead, straight through, "
               "way n to way n -- 1 GND, 2 24 V, 3 SCK, 4 SDT at both ends "
               "(harness.LED_DROP; pi_cap.py wires J6 pins 1 to 4 in that order, and this "
               "board's lands read GND, +24V_IN, SCK_CABLE, SDT_CABLE on the routed "
               "board). XH is shrouded and keyed: it goes on one way and cannot sit one "
               "pin along. The seam, J21..J24 to board B's J11..J14: spring pins tip to "
               "tip, both boards face down in one channel, so equal Y is the same pin -- "
               "+24V at 8.88, GND 5.08, SCK 1.28, SDT -2.52 on BOTH routed boards. "
               "SCK_OUT here is U4's SCKO and lands on B's SCK_IN, its U1's SCKI"
               if a else
               "one joint, the seam: J11..J14 meet board A's J21..J24 tip to tip, both "
               "boards face down in one channel, so equal Y is the same pin -- +24V at "
               "8.88, GND 5.08, SCK 1.28, SDT -2.52 on BOTH routed boards. A's SCK_OUT "
               "(its U4's SCKO) lands on SCK_IN here, U1's SCKI. The channel's walls "
               "hold both boards in Y; nothing else plugs into this board"),
        "M2": "the only polarised parts are the LEDs. XINGLIGHT's drawing: pads 1 to 4 "
              "are the four anodes, 5 to 8 their cathodes; the netlist takes the rail to "
              "pad c+1 and pad c+5 on to the next LED or the driver's sinking output. "
              "The fab's own library footprint for C7371891 was compared with ours pad "
              "for pad: identical at 0 degrees (worst pad 0.03 mm), so the reel's "
              "orientation is the CPL's angle unchanged. No diode, electrolytic or "
              "tantalum on the board",
        "M3": "ground is a whole inner layer (In2) and the rail another (In1), each "
              "broken only by via clearances; every ground pad has its own via beside "
              "it and the buck's ground slab has six. 24 V arrives on a 0.30 mm track "
              "(A1: 0.08 needed) and returns through that plane to "
              + ("J1's ground land, which is 1.3 x 4.5 with a via in it" if a else
                 "J12, a 5.0 x 3.5 land") +
              ". The feedback divider's ground (R11, R12) goes down its own vias 2 mm "
              "from the AGND pin, not along the power slab",
        "M4": "LMR33630 (SNVSAN3F 9.2.2.6 to 9.2.2.8). Input: TI ask 10 uF ceramic rated "
              "at least the input, preferably twice -- C30 + C31 are 2 x 10 uF / 50 V "
              "1206 on 24 V; and, for the RNX package, a small capacitor at each of its "
              "two VIN/PGND pairs -- C32 and C35, 100 nF / 50 V, 0.60 mm from their pins. "
              "Bootstrap 100 nF (asked: 100 nF, 10 V or more; fitted 50 V). VCC 1 uF / "
              "25 V (asked: 1 uF, 16 V). Output: TI's table for 12 V at 1.4 MHz is 4.7 uH "
              "and 4 x 10 uF; this rail has 2 x 10 uF / 50 V at the inductor plus "
              "%d x 4.7 uF / 25 V on the same plane, 38.8 uF by the "
              "markings. The 25 V parts sit at 46 %% of their rating and the 50 V ones "
              "at 23 %%. TI's equation 6 for the whole 0.72 A arriving as one step with "
              "a 2 %% dip asks 5.1 uF. Each driver: 1 uF on VREG (its sheet requires "
              "it), 100 nF on VCC, and its own 4.7 uF for the 0.18 A its twelve "
              "channels switch together" % n_drv,
        "M5": "24 V bus: U10 is rated 36 V operating and 38 V absolute, every capacitor "
              "on it 50 V, F1 63 V. The spring pin's catalogue line is 24 V, which is "
              "the bus itself: it is a bare barrel with no insulation of its own, and "
              "what stands off the voltage is 0.30 mm of masked board between the +24V "
              "and GND lands and 0.8 mm of air between barrels. The rail: 11.50 V, "
              "11.12 to 11.88 with the 1.5 % reference and 1 % resistors, on drivers "
              "rated 17 V (18 absolute) at VCC and at every output; 25 V and 50 V "
              "capacitors. Logic: SCK and SDT are 3.3 V, into inputs rated VREG + 0.6 V "
              "with VREG 3.1 to 3.5 V. A live plug is M16, a dark board with live "
              "signals M18",
        "M6": "no parallel bus and nothing matched. SCK and SDT are a 10 MHz-capable "
              "pair that the Pi clocks far slower; each driver re-drives both (10 ns "
              "edges) to the next, 66 mm on, which is 0.45 ns of flight. Both run over "
              "the unbroken rail plane, and where SCK_2 / SDT_2 drop to the back to "
              "pass the buck they run against the ground plane with both planes "
              "between them and the switch node",
        "M7": "divider: 100k over 10k || 200k = 9.524k on the 1.000 V reference is "
              "11.50 V. Inductor 4.7 uH: TI's table value at 1.4 MHz; their floor of "
              "0.28 x Vout / fsw is 2.3 uH against 3.76 at the part's -20 %; ripple "
              "0.91 A, 30 % of the 3 A they size it on. EN (pin 9) is tied to VIN on laid copper (TI: "
              "may go straight to VIN, must not float). PG (pin 8) is an open drain "
              "that 'can be left open when not used', and is. The RNX has no exposed "
              "pad. TLC59711: IREF 3k3 gives 41 x 1.21 V / 3.3k = 15.0 mA; its "
              "PowerPAD is on GND",
        "M8": "nothing here has a reset, boot or address pin. A TLC59711 powers up with "
              "BLANK set, every output off, and stays so until a write that begins "
              "with command 25h (SBVS181A, 'BLANK bit'). Its two inputs are driven, "
              + ("through R21 / R22, by Pi pins whose reset state is a pull-down "
                 "(GPIO 9 to 27); with the lead off, the board has no supply either"
                 if a else
                 "by board A's last driver, which shares this board's supply joint") +
              ". IREF has its resistor to ground; the buck's EN is tied",
        "M9": "no MCU. Three bare 1.5 mm pads by the buck, each named in silk: +24V "
              "(after the fuse), +11V5 and GND. SCK and SDT can be probed at "
              + ("R21 / R22 and at the seam lands" if a else "the seam lands") +
              ", which are 5.0 x 3.5",
        "M10": ("decision: no TVS. J1 is inside the instrument, on a 4-way lead from the "
                "Pi cap that is plugged with the instrument off. Over-current: F1, "
                "2 A fast, 63 V, ahead of everything. Reverse supply: the XH housing "
                "is keyed, and the two supply ways are the XH bus's own order so even "
                "the wrong lead feeds it the right way round. The two signal ways "
                "have 1 k in series 2.0 mm from the socket's lands (R21, R22), which "
                "is what an ESD strike or a foreign lead sees before a driver's "
                "input. Nothing on this board can back-feed 24 V: it only consumes it"
                if a else
                "decision: no TVS. No cable reaches this board: its four lands meet "
                "board A's spring pins inside the channel. Over-current: its own F1, "
                "1 A fast, 63 V, so a fault here opens this fuse and leaves A lit. "
                "It cannot back-feed anything"),
        "M11": "elec/cad_geom_check.py %s, 2026-10-05: every routed part is where "
               "the CAD draws it. Tallest hanging part %s against a 6.05 mm trough "
               "(src/foot_light.py asserts the air gap). No mounting hole by design: "
               "the channel holds five faces and the endplate the sixth. %s"
               % (FL.BOARD_NAME[board],
                  "is J1 at 5.75 mm, then the inductor at 4.0" if a else
                  "is the inductor at 4.0 mm",
                  "J1's mouth is at the -X end and is plugged before the "
                  "endplate goes on (INSTALL_NOTES)" if a else
                  "It goes in first and nothing is plugged into it"),
        "M13": "measured on the routed board, pad edge to pad edge, against TI's RNX "
               "layout: C32 and C35 0.60 mm from VIN and 0.60 from PGND at their own "
               "pair, on the part's layer, on laid copper with no via in either loop; "
               "the bulk pair 3.5 and 6.0 mm away on the same slabs. The switch node is "
               "a laid 0.5 mm track, 4.4 mm from the pin to the inductor's land, no "
               "via, no pour. The feedback parts are on the opposite side of the "
               "package from it: R11 1.17 mm and R10 2.35 mm from FB, R12 on R11, the "
               "whole node 4.3 mm of track and none of it under the inductor. "
               "Bootstrap 1.07 mm from BOOT and 0.74 from SW. VCC's capacitor 0.42 mm "
               "from its pin on 1.1 mm of 0.25 track, its ground pad on the track from "
               "AGND",
        "M14": "L1 SWPA5040S4R7MT, 4.7 uH +-20 %%. Ripple 11.5 x (1 - 11.5/24) / (4.7 uH "
               "x 1.4 MHz) = 0.91 A, so the peak at this board's 0.72 A is 1.18 A. "
               "Saturation (Sunlord: 30 %% inductance drop, 20 C) 3.50 A guaranteed, "
               "3.90 typical; heating current 3.0 A. TI: saturation 'must not be less "
               "than the device low-side current limit', 3.5 A typical (2.9 to 4.1) -- "
               "met at the guarantee, with nothing over. The high-side limit is 4.5 A "
               "typical (3.85 to 5.05), above this part: accepted. A dead short on "
               "the rail pulls FB under 0.4 V and the part hiccups at 94 ms. The 4 x 4 "
               "part this replaced saturated at 2.90 A",
        "M15": "U10 is internally compensated for ceramic outputs and TI give no ESR "
               "window, only the table's inductance and capacitance (M4). Capacitance "
               "under bias is NOT read off a curve here: the 1206 and 0805 parts are "
               "at 23 %% and 46 %% of their ratings, and a tenth of the marked 38.8 uF "
               "still covers TI's equation 6. No linear regulator, so no dropout: the "
               "buck is at 48 %% duty against a 98 %% maximum",
        "M16": ("J1 is plugged with the instrument off, and the 24 V then arrives "
                "through the output panel's switch at about 1.5 V/ms (motor_ctrl's "
                "M16): no ring. Plugged live it would be a lead of about 0.4 uH into "
                "about 11 uF of biased ceramic, 0.19 ohm characteristic, against "
                "0.13 ohm in F1 alone (JDT's cold resistance) plus the lead and four "
                "contacts: close to critically damped, a few percent over 24 V. U10's "
                "38 V is the lowest limit on the net"
                if a else
                "this board's 24 V arrives across the seam, which is made by sliding "
                "board A home with the instrument off; the supply then ramps at about "
                "1.5 V/ms. Were it made live, F1 here is 0.49 ohm cold (JDT) in series "
                "with about 11 uF of biased ceramic: overdamped"),
        "M18": ("decision, and two resistors. The Pi can be up while this board is "
                "dark (F1 open, the motor board's lights fuse open, a Pi on USB power "
                "on the bench), and a TLC59711 input is rated to VREG + 0.6 V with "
                "VREG then 0. R21 and R22, 1 k at the socket, hold what the Pi can "
                "push through the input's protection diode to 2.7 mA. The other way "
                "round nothing is driven: this board has no output towards the Pi"
                if a else
                "decision: nothing added. This board's inputs are driven by board A's "
                "last driver, a 3.3 V output of a few mA. They can only be live while "
                "this board is dark if this board's own F1 has opened, which is a "
                "fault being repaired, not a state it is run in. In normal use both "
                "boards take their 24 V through the same socket"),
        "M20": "no I2C and no CAN. SCK and SDT are terminated at their source: 68 ohm "
               "in series at the Pi cap. On the board each hop is 66 mm from a driver "
               "with 10 ns edges, a twentieth of the edge in flight: lumped, nothing to "
               "terminate",
        "M21": "no ADC, DAC, codec or analog reference on the board",
        "M22": "no op-amp or comparator on the board",
        "M25": "TLC59711: the pad is on GND, as TI name it, solid, with seven vias "
               "(six under the mask at the pad's ends, one in the pasted middle; TI "
               "draw fifteen) and paste in four panes. At full white a driver burns "
               "0.57 W typical and 0.75 W worst (12 x 15 mA across the rail less three "
               "LEDs, plus its own supply current); at TI's 68.6 C/W that is 39 to "
               "51 C over ambient, 96 C at 45 C against 150 C. U10 has no pad: its "
               "heat leaves through the pins into the laid slabs and their vias. "
               "Loss, read off TI's 24 V curve for this package at 1.4 MHz (figure "
               "9-15) at 0.7 A: 0.9 W, all of it charged to the IC. Thermal "
               "resistance is an ESTIMATE, 60 C/W: TI's 23.5 junction to board, then "
               "this board's copper; their figure 9-4 gives 50 to 63 for the package "
               "on four layers of heavier copper. 45 C ambient (inside the chassis, "
               "beside the motors) + 0.9 x 60 = 99 C against 125 C operating and a "
               "165 C shutdown. The 2.1 MHz part these boards had loses 1.2 W at the "
               "same load, 117 C: that is why it was changed (elec/buck_cell.py). No "
               "tab on the board",
        "M26": "one link, a daisy chain. Read off TI's pin table: 9 SDTI, 10 SCKI, "
               "11 SCKO, 12 SDTO. " + ("SDT_IN and SCK_IN (from the cable through R22 "
               "/ R21) reach U1 pins 9 and 10" if a else "SDT_IN and SCK_IN (the seam) "
               "reach U1 pins 9 and 10") + "; each driver's 12 and 11 go to the next "
               "one's 9 and 10 as SDT_n / SCK_n; " + ("U4's leave as SDT_OUT / SCK_OUT "
               "on J24 / J23" if a else "U4's are the end of the chain, named _NC") +
               ". At the Pi the two are an SPI's MOSI and SCLK",
        "M27": "no strap, reset or debug net on the board",
        "M28": "no transistor or small regulator. The three ICs' pin orders are read "
               "from their own sheets (pinouts, above), and each placed footprint was "
               "compared pad for pad with the fab's library footprint for that exact "
               "LCSC code: TLC59711PWPR C116842, the RNX0012 land of LMR33630CRNXR "
               "C2071783 (the B part is the same package), XL-5050RGBW "
               "C7371891" + (", S4B-XH-SM4-TB C161861" if a else "") + " -- all match "
               "under a pure rotation",
        "M29": "four layers, 1.6 mm, 1 oz outside and 0.5 oz inside: JLCPCB's standard "
               "table, read 2026-10-04 (A12 measured against it). The 0.25 / 0.50 via "
               "is an order-form choice and is in ORDER.txt. %s x 24.15 mm is inside "
               "the size limits. Every 0402's plane-side pad reaches its plane through "
               "a via beside the pad on a short track, as the other pad has: no pad "
               "sits in a pour" % ("293.4" if a else "286.4"),
        "M30": "JLCPCB's assembly page, read 2026-10-05: Economic PCBA takes "
               "single-sided assembly on 2, 4 or 6 layers at 1.6 mm, a single board "
               "from 10 x 10 to 470 x 500 mm, parts from 0402 and IC pitch from 0.4 mm. "
               "This board is 24 mm wide, under Standard's 70 x 70 minimum, so "
               "Economic is the tier it must be accepted in (or it is panelised with "
               "rails): confirming that on the quote page is in M12. Finest pitch "
               "here 0.5 mm (U10). Every part is in the assembly library; the "
               "extended ones are the LED, the driver, the buck, the inductor, the "
               "fuse, the spring pin" + (" and the socket" if a else ""),
        "M31": "'FOOT LED %s r1' on the front. The three test pads are named (+24V, "
               "+11V5, GND). " % board.upper() + ("J1's four ways are named on the "
               "BACK, which is the face that looks up at whoever plugs it: 1 GND, "
               "2 +24V_IN, 3 SCK_CABLE, 4 SDT_CABLE. " if a else "") + "Each seam land "
               "is named on the back with its net. All text 1.0 mm or more with a "
               "0.15 stroke (A12). Pin-1 and LED polarity marks are the footprints', "
               "outside the bodies. The legend is cut back from every mask opening: "
               "the gerber carries the pads in clear polarity",
        "M32": ("J1: lands 2.50 mm apart measured on the footprint, which is XH (PH is "
                "2.00); 3 A a contact against 0.77 A; pad 1 per JST's drawing. " if a
                else "") + "The spring pins are not a pitch series: single lands at "
               "3.80 mm, 12 A each against " + ("0.38 A handed on" if a else "0.38 A") +
               ", and ground has a pin beside the supply and the two signals",
        "M33": "the rail: 48 channels x 15 mA = 0.72 A, plus four drivers at no more "
               "than 18 mA (TI's maximum at twice this current setting), 0.79 A of a "
               "3 A regulator: 26 %%. That is the 0.72 A declared "
               "on +11V5. The 24 V side at 90 %%: 0.38 A a board" + (
               ", and this one carries both, 0.77 A: J1's contact is 3 A, F1 2 A, "
               "the seam pin 12 A" if a else ": F1 here is 1 A, the seam pin 12 A"),
        "M34": "SCK and SDT: the Pi's 3.3 V output into an input that wants 0.7 x "
               "VREG, 2.45 V at VREG's 3.5 V maximum, with 0.2 x VREG of hysteresis; "
               "between drivers it is a VREG-level output into the same input. The "
               "protocol has no chip select and no enable. U10's EN is active high, "
               "1.23 V threshold, tied to VIN as its sheet allows",
        "M35": "TI's product pages for TLC59711 and LMR33630, read 2026-10-05: both "
               "active, no errata document listed for either",
        "M36": ("24 V is offered to board B at the seam, from behind F1 (2 A); B has "
                "its own 1 A fuse behind its lands. The rail does not leave the board"
                if a else "no supply leaves this board"),
        "M37": "elec/fab.py %s, 2026-10-05, run after finish.py's refill and DRC; "
               "gerbers and drill written together. Opened outside KiCad: every layer "
               "rendered with pygerber 2.4.3 and looked at, the Excellon file parsed "
               "separately and laid over the copper -- all %d plated holes have copper "
               "all round them on both outer layers. Paste only on soldered lands; "
               "stack-up and the via choice are in ORDER.txt"
               % (FL.BOARD_NAME[board], 259 if a else 253),
        "M38": "the board bends along its length when it is handled, so every 1206 -- "
               "four capacitors and the fuse -- stands across it. Decision: the four "
               "4.7 uF 0805s lie along it, in the row over each driver that keeps the "
               "driver's escape lane open; they are 6.6 mm from the long edges, the "
               "board is ordered as a routed single with no V-score or tab, and in "
               "service the channel holds it flat along its whole length. Test pads: "
               "1.5 mm, 1.1 mm apart. No mounting hole. " + (
               "J1's plug is pushed on from the open -X end of the channel" if a else
               "Nothing is plugged into it"),
        "M39": "no unused input. All 48 outputs are used. " + (
               "" if a else "U4's SCKO and SDTO are the end of the chain: push-pull "
               "outputs, left open. ") + "U10's PG is an open drain left open, as its "
               "sheet allows",
        "M40": "3k3, 10k, 100k, 200k" + (", 1k" if a else "") + ", 100 nF, 1 uF, "
               "4.7 uF and 10 uF are stock values, and every capacitor's voltage is "
               "in its value. Do-not-substitute parts say so where they are defined: "
               "L1 (elec/buck_cell.py: saturation), F1 (a part number: speed and "
               "63 V), the 100 nF / 50 V at VIN, and the LED, whose 3.0 to 3.4 V sets "
               "the rail",
        "M42": "JLCPCB stock on 2026-10-05: LED 40,185, driver 3,826, buck "
               "LMR33630BRNXR 260 (THIN: the alternate is the 2.1 MHz LMR33630CRNXR, "
               "3,453, on the same land with no other change, and then full white is "
               "capped in firmware -- elec/buck_cell.py), inductor C48496 8,632, fuse " + ("11 k" if a else "96 k") + ", spring "
               "pin 594" + (", socket 20,309" if a else "") + "; passives are basic "
               "parts. Both TI parts active. Single-maker parts: the spring pin "
               "(Xinyangze, no second source on this land: the thin one, eight a "
               "pair of boards) and the LED (other 5050 RGBW parts exist but their "
               "pad order must be read first)",
    }
    return m


def build(board, passes=20):
    """One of the two boards: "a" is the near (-X) one with the cable socket."""
    name = FL.BOARD_NAME[board]
    skidl.reset()
    x0, x1 = FL.board_span(board)
    length = x1 - x0
    xs = [FL.to_board_x(board, x) for x in FL.board_leds(board)]
    n_zone = len(xs) // FL.N_SERIES
    n_drv = (n_zone + 2) // 3
    assert len(xs) % FL.N_SERIES == 0 and n_zone % 3 == 0, (
        "%s: %d LEDs is %d zones -- zones come in threes (a TLC59711 carries three) "
        "and strings in N_SERIES" % (name, len(xs), n_zone))
    half = length / 2.0

    gnd, v24, vrail = Net("GND"), Net("+24V"), Net("+11V5")
    for n in (gnd, v24, vrail):
        n.drive = Pin.drives.POWER
    place, fps = {}, {}

    # ── the two ends of the chain ────────────────────────────────────────────────────
    # Board A: J1 (the cable) IN at -X, J21..J24 (the seam) OUT at +X.
    # Board B: J11..J14 (the seam) IN at -X, and its last driver's outputs go nowhere.
    # The pogo footprint fires -X as drawn, so A's set is turned half a turn.
    v24_in = Net("+24V_IN")
    sck, sdt = Net("SCK_IN"), Net("SDT_IN")
    pogo_refs = {}
    if board == "a":
        sck_out, sdt_out = Net("SCK_OUT"), Net("SDT_OUT")
        j1 = Part(name="S4B-XH-SM4-TB", ref_prefix="J", ref="J1", tag="J1",
                  dest="NETLIST", tool="skidl", value="S4B-XH-SM4-TB",
                  description="in, from the Pi cap's J6 -- GND, +24V, SCK, SDT "
                              "(LCSC C161861)",
                  footprint=J_FP,
                  pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(J_PINS)])
        gnd += j1[1]
        v24_in += j1[2]
        # mouth faces -X (rot 270), J_INSET in from the board's end; the placement
        # anchors on the pad centroid, J_ANCHOR behind the mouth
        place["J1"] = (-(half - FL.J_INSET) + J_ANCHOR, J_Y, 270.0)
        fps["J1"] = J_FP
        for (ref, dx, dy), way, net in zip(J_SERIES, (3, 4), (sck, sdt)):
            cable = Net(J_PINS[way - 1])
            rs = _r(ref, R_SERIES, "%s in series at the cable: limits what a live Pi can "
                                   "push into a dark driver's input" % J_PINS[way - 1][:3])
            cable += j1[way], rs[1]
            net += rs[2]
            place[ref] = (place["J1"][0] + dx, J_Y + dy, 0.0)
            fps[ref] = R_FP
        seam = (+1.0, 20, "out", {"+24V": v24, "GND": gnd, "SCK": sck_out, "SDT": sdt_out})
    else:
        # named NC rather than leaving netcheck to find two pins wired to nothing
        sck_out, sdt_out = Net("SCK_OUT_NC"), Net("SDT_OUT_NC")
        seam = (-1.0, 10, "in", {"+24V": v24_in, "GND": gnd, "SCK": sck, "SDT": sdt})
    sgn, base, what, nets_of = seam
    for i, (px, py, net) in enumerate(FL.pogo_pads(sgn)):
        ref = "J%d" % (base + i + 1)
        j = Part(name="YZF0002-38080-02", ref_prefix="J", ref=ref, tag=ref,
                 dest="NETLIST", tool="skidl", value="YZF0002-38080-02",
                 description="seam pogo, %s: %s (LCSC C5203987)" % (what, net),
                 footprint=POGO_FP, pins=[Pin(num=1, func=P)])
        nets_of[net] += j[1]
        place[ref] = (px, py, 0.0 if sgn < 0 else 180.0)
        fps[ref] = POGO_FP
        pogo_refs.setdefault(sgn, []).append(ref)

    # ⚠ A PART, NOT "1A": a fuse is chosen for its voltage and its speed as well as its
    # current, and a value string picks none of them. JDT JFC1206 fast-acting, 63 V.
    # Board A's carries BOTH boards (0.77 A all-white), so it is the 2 A part at 38 %;
    # board B's carries its own 0.38 A on the 1 A part, so a fault on B opens B's fuse
    # and leaves A lit.
    f_val = {"a": "JFC1206-1200FS", "b": "JFC1206-1100FS"}[board]
    f1 = Part(name="Fuse", ref_prefix="F", ref="F1", tag="F1", dest="NETLIST",
              tool="skidl", value=f_val,
              description="24 V fuse, fast, 63 V, %s (LCSC %s) -- a shorted U10 must not "
                          "feed the fault back out into the trunk, nor into the next "
                          "board" % ({"a": "2 A", "b": "1 A"}[board],
                                     {"a": "C136345", "b": "C136343"}[board]),
              footprint=FUSE_FP,
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v24_in += f1[1]
    v24 += f1[2]

    # ── the buck: the fret boards', unchanged ────────────────────────────────────────
    u10 = Part(name="LMR33630", ref_prefix="U", ref="U10", tag="U10", dest="NETLIST",
               tool="skidl", value=BC.U_VALUE,
               description="24 V -> %.2f V synchronous buck, %.1f MHz, 3 A (LCSC %s)"
                           % (V_RAIL, BC.U_FSW / 1e6, BC.U_LCSC),
               footprint=BUCK_FP, pins=[Pin(num=n, func=P) for n in range(1, 13)])
    sw, boot, vcc, fb = Net("SW"), Net("BOOT"), Net("BUCK_VCC"), Net("FB")
    gnd += u10[1], u10[11], u10[6]
    v24 += u10[2], u10[10], u10[9]
    sw += u10[3], u10[12]
    boot += u10[4]
    vcc += u10[5]
    fb += u10[7]
    Net("BUCK_PG_NC").connect(u10[8])
    l1 = Part(name="L", ref_prefix="L", ref="L1", tag="L1", dest="NETLIST", tool="skidl",
              value=BC.L1_VALUE, description=BC.L1_DESC,
              footprint=IND_FP, pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw += l1[1]
    vrail += l1[2]
    for ref, val, fp, net, why in (
            ("C30", "10uF/50V", C12_FP, v24, "buck input bulk"),
            ("C31", "10uF/50V", C12_FP, v24, "buck input bulk"),
            # 50 V SAID IN THE VALUE: the fab picks a passive by its value text and a bare
            # "100nF" 0402 is its 16 V part (C1525). 100nF/50V is CL05B104KB54PNC, C307331,
            # also a basic part -- so every 100 nF on the board is that one line.
            ("C32", "100nF/50V", C_FP, v24, "buck input HF bypass -- VIN/PGND, pins 2 and 1"),
            ("C35", "100nF/50V", C_FP, v24, "buck input HF bypass -- VIN/PGND, pins 10 "
                                            "and 11, the pair on the other side"),
            ("C34", "1uF/25V", C_FP, vcc, "buck VCC bypass (TI: 1 uF, 16 V or more)"),
            ("C36", "10uF/50V", C12_FP, vrail, "rail output bulk"),
            ("C37", "10uF/50V", C12_FP, vrail, "rail output bulk"),
            ("C38", "100nF/50V", C_FP, vrail, "rail output HF bypass")):
        c = _c(ref, val, why, fp)
        net += c[1]
        gnd += c[2]
    c33 = _c("C33", "100nF/50V", "buck bootstrap -- BOOT to SW (TI: 100 nF, 10 V or more)")
    boot += c33[1]
    sw += c33[2]
    r10 = _r("R10", "100k 1%", "rail feedback divider, top (TI: 100k)")
    r11 = _r("R11", "10k 1%", "rail feedback divider, bottom")
    r12 = _r("R12", "200k 1%", "across R11: 10k || 200k = 9.524k, %.2f V with R10"
                               % V_RAIL)
    vrail += r10[1]
    fb += r10[2], r11[1], r12[1]
    gnd += r11[2], r12[2]

    # ⚠ THE SUPPLY SITS IN THE MIDDLE OF THE BOARD, AND THE RETURNS ARE WHY. Each
    # driver's outer two zones return along the lane from +-2.5 pitches away, so the
    # lane between a driver and its outer zones -- x -101..-41 and +41..+101 -- is a
    # traffic corridor carrying four returns each way. Parked at the -X end, the supply
    # sat squarely in the -X one, and route after route left exactly one of zone 0's
    # four returns unconnected -- a different colour each time, which is what a board
    # at its limit looks like. The middle 82 mm carries no returns at all.
    #
    # ⚠ IT COSTS DISTANCE TO THE PICKUP AND THAT IS WORTH STATING. On the +X board
    # the buck moves from ~187 mm away to ~73, which is 16x the coupling by 1/r^3. It
    # is still the quieter of the two things on this board: a tight 1.4 MHz hot loop
    # of ~5 mm2 at 73 mm is 4x below the LED loop's 15 mm2 at 66 mm that shares the
    # board with it, and its spectrum is nowhere near the audio band.
    place["U10"] = (BUCK_X, LANE_Y, 0.0)
    fps["U10"] = BUCK_FP
    for ref, net, what in (("TP1", v24, "+24V behind the fuse"),
                           ("TP2", vrail, "the LED rail, %.2f V" % V_RAIL),
                           ("TP3", gnd, "ground for the probe")):
        tp = Part(name="TestPoint", ref_prefix="TP", ref=ref, tag=ref, dest="NETLIST",
                  tool="skidl", value="TP",
                  description="test pad -- %s; bare copper, no component" % what,
                  footprint=TP_FP, pins=[Pin(num=1, func=P)])
        net += tp[1]
    cell_fp = {"TP1": TP_FP, "TP2": TP_FP, "TP3": TP_FP, "F1": FUSE_FP, "C30": C12_FP, "C31": C12_FP, "C36": C12_FP, "C37": C12_FP,
               "L1": IND_FP, "R10": R_FP, "R11": R_FP, "R12": R_FP}
    for ref, (dx, dy, rot) in BUCK_CELL.items():
        place[ref] = (BUCK_X + dx, LANE_Y + dy, rot)
        fps[ref] = cell_fp.get(ref, C_FP)

    # ── the zones ────────────────────────────────────────────────────────────────────
    # A zone is N_SERIES consecutive LEDs in series on one channel; a driver serves three
    # and sits on the middle one. The CHAIN DIRECTION is chosen per zone so the end that
    # returns to the driver is the end NEAREST it -- the far end goes to the rail, and a
    # long rail run is a pour while a long return is a trace. At 2 in series the worst
    # return is 1.5 zone-pitches, 18 mm: HALF what the 12-zone board asked of it.
    zones = [list(range(z * FL.N_SERIES, (z + 1) * FL.N_SERIES)) for z in range(n_zone)]
    for k in range(n_drv):
        trio = zones[3 * k:3 * k + 3]
        mid = trio[len(trio) // 2]
        xd = sum(xs[i] for i in mid) / len(mid)   # the middle zone's centre
        # (no clamp against the supply row any more: it is in the middle, and the
        # drivers are what it has to stay clear of rather than the other way round)
        u = Part(name="TLC59711", ref_prefix="U", ref="U%d" % (k + 1),
                 tag="U%d" % (k + 1), dest="NETLIST", tool="skidl", value="TLC59711PWPR",
                 description="12-ch 16-bit constant-current LED driver (LCSC C116842)",
                 footprint=DRV_FP, pins=[Pin(num=n, func=P) for n in range(1, 22)])
        iref, vreg = Net("IREF%d" % (k + 1)), Net("VREG%d" % (k + 1))
        u[1] += iref
        gnd += u[2], u[21]
        vrail += u[19]
        vreg += u[20]
        sdt += u[9]
        sck += u[10]
        sck, sdt = ((Net("SCK_%d" % (k + 1)), Net("SDT_%d" % (k + 1)))
                    if k < n_drv - 1 else (sck_out, sdt_out))
        sck += u[11]
        sdt += u[12]
        r = _r("R%d" % (k + 1), R_IREF, "U%d IREF -- 15.0 mA per channel" % (k + 1))
        iref += r[1]
        gnd += r[2]
        cv = _c("C%d" % (k + 1), "1uF/25V", "U%d VREG (datasheet: 1 uF required)" % (k + 1))
        vreg += cv[1]
        gnd += cv[2]
        cc = _c("C%d" % (10 + k + 1), "100nF/50V", "U%d VCC bypass" % (k + 1))
        vrail += cc[1]
        gnd += cc[2]
        cb = _c("C%d" % (20 + k + 1), "4.7uF/25V", "U%d local bulk -- its zones' PWM "
                "current must come from here, not the far end of the rail" % (k + 1),
                C08_FP)
        vrail += cb[1]
        gnd += cb[2]
        place["U%d" % (k + 1)] = (xd, LANE_Y, 0.0)
        fps["U%d" % (k + 1)] = DRV_FP
        # THE DRIVER'S FOUR PASSIVES STAND IN A ROW ABOVE IT, on the side away from the
        # LEDs, in the order of the pins they serve: IREF is pin 1 and VCC / VREG are 19
        # and 20, the top of the package's two columns.
        # ⚠ NOT BESIDE IT, WHICH IS WHERE THEY WERE. Every one of them has a pad on a
        # plane net, and its stitch via now stands beside the pad rather than in it
        # (cadkit quality A12: no open via in a small soldered land). Beside the driver
        # that is a row of fenced vias across the mouth of the one lane the package's
        # outboard column escapes by, and its outer zones' returns stopped routing --
        # two nets, then six when the row was only lifted 2 mm and sat on the pins.
        # Above the package nothing has to pass.
        row = (("R%d" % (k + 1), R_FP), ("C%d" % (20 + k + 1), C08_FP),
               ("C%d" % (10 + k + 1), C_FP), ("C%d" % (k + 1), C_FP))
        gap = 0.45
        span = sum(fp_box(fp)[0] for _r, fp in row) + gap * (len(row) - 1)
        row_y = LANE_Y + fp_box(DRV_FP)[1] / 2.0 + gap + fp_box(C08_FP)[1] / 2.0
        prow = Row(place, fps, xd - span / 2.0, gap=gap, dirn=1.0, y=row_y)
        for ref, fp in row:
            prow.add(ref, fp)

        for s, zone in enumerate(trio):
            side = s - len(trio) // 2
            side = -1 if side < 0 else (1 if side > 0 else 0)
            outs = ZONE_OUTS[side]
            fwd = abs(xs[zone[-1]] - xd) < abs(xs[zone[0]] - xd)
            order = zone if fwd else list(reversed(zone))
            rot = 0.0 if fwd else 180.0
            leds = []
            for i in order:
                ref = "D%d" % (i + 1)
                d = Part(name="LED_RGBW", ref_prefix="D", ref=ref, tag=ref,
                         dest="NETLIST", tool="skidl", value="XL-5050RGBW",
                         description="RGBW LED %d (LCSC C7371891)" % (i + 1),
                         footprint=LED_FP,
                         pins=[Pin(num=n, func=P) for n in range(1, 9)])
                place[ref] = (xs[i], LED_Y, rot)
                fps[ref] = LED_FP
                leds.append(d)
            zi = 3 * k + s
            for c, col in enumerate(COLOURS):
                vrail += leds[0][c + 1]
                for a in range(len(leds) - 1):
                    Net("Z%d_%s_%d" % (zi, col, a)).connect(leds[a][c + 5],
                                                            leds[a + 1][c + 1])
                Net("Z%d_%s_RET" % (zi, col)).connect(leds[-1][c + 5], u[outs[c]])

    # ⚠ THE POGO ROW IS CHECKED AS COPPER, NOT AS COURTYARDS. Four 3.50 lands stand at a
    # 3.80 pitch because that is all the lane between the -Y shoulder and the end LED
    # allows (foot_light.POGO_PITCH), which puts neighbouring courtyards edge to
    # edge and the last one 0.05 off the end LED's. The courtyard rule is there to
    # leave the router a lane; nothing routes between two pogos. foot_light.check_optics
    # asserts what matters instead: 0.30 of board between lands, 0.30 to the LED.
    xs_sorted = sorted(xs)
    end_led = {-1.0: "D%d" % (xs.index(xs_sorted[0]) + 1),
               +1.0: "D%d" % (xs.index(xs_sorted[-1]) + 1)}
    exempt = []
    for sgn, refs in pogo_refs.items():
        exempt += [(refs[i], refs[i + 1]) for i in range(len(refs) - 1)]
        exempt.append((refs[-1], end_led[sgn]))
    if board == "a":
        # ⚠ THE SOCKET AND THE FIRST LED ARE CHECKED AS PARTS, NOT AS COURTYARDS, for the
        # reason the pogo row is. The XH's courtyard is 16.7 x 12.0 because it includes
        # the plug's approach and both mounting lands; what actually comes near the LED
        # is the back of its body in X and its four signal lands in Y.
        jx, jy, _rot = place["J1"]
        mouth = jx - J_ANCHOR
        lx, ly, _lrot = place[end_led[-1.0]]
        led_half = 6.10 / 2.0                      # the LED's courtyard, as check_optics
        body_back = mouth + 7.00                   # F.Fab: 7.00 deep from the mouth
        lands_y = jy - (3.75 + 1.30 / 2.0)         # the signal lands' edge nearest the row
        assert (lx - led_half) - body_back >= 0.30 - 1e-9, (
            "the socket's body ends %.2f from the first LED's courtyard"
            % ((lx - led_half) - body_back))
        assert lands_y - (ly + led_half) >= 0.30 - 1e-9, (
            "the socket's signal lands are %.2f from the first LED's courtyard"
            % (lands_y - (ly + led_half)))
        exempt.append(("J1", end_led[-1.0]))
    # the buck's cell is laid out to TI's figure, closer than the lane-keeping gap this
    # check enforces; real courtyard overlaps are still DRC's to refuse
    cell = ["U10"] + sorted(BUCK_CELL)
    exempt += [(a, b) for i, a in enumerate(cell) for b in cell[i + 1:]]
    FL.check_optics()
    check_placement(name, place, fps, exempt=exempt)
    ERC()
    net = os.path.join(OUT_DIR, "%s.net" % name)
    generate_netlist(file_=net)
    netcheck.grounds_meet(net)
    netcheck.no_orphan_pins(net)

    notes = dict(BOARD_NOTES)
    notes["outline_mm"] = (round(length, 3), round(BOARD_W, 3))
    notes["placements"] = {k: list(v) for k, v in place.items()}
    notes["router_passes"] = passes
    # THE BUCK'S COPPER IS LAID, NOT ROUTED (buck_cell.copper says what and why), and
    # each driver's heat pad gets its six vias (DRV_PAD_VIAS).
    ux, uy, _ur = place["U10"]
    v_dia, v_drill = BOARD_NOTES["via_mm"]
    notes["tracks"] = BC.copper((ux, uy), 0.0, v_out="+11V5")
    notes["vias"] = [v + (v_drill, v_dia) for v in BC.vias((ux, uy), 0.0)] + [
        ("GND", round(place["U%d" % (k + 1)][0] + dx, 3),
         round(place["U%d" % (k + 1)][1] + dy, 3), v_drill, v_dia)
        for k in range(n_drv) for dx, dy in DRV_PAD_VIAS]
    # WHAT EACH SUPPLY NET CARRIES, all-white. A board's own rail is its channels and
    # its 24 V draw is that through the buck at 90 %. Board A's inlet and fuse carry
    # BOTH boards' and it hands B's share across the seam; B carries its own.
    i_rail = 4 * n_zone * I_CHAN
    i_own = i_rail * V_RAIL / 24.0 / 0.90
    if board == "a":
        i_24 = len(FL.HALVES) * i_own
        paths_24 = [
            {"net": "+24V_IN", "from": "J1.2", "to": "F1.1", "amps": round(i_24, 3)},
            {"net": "+24V", "from": "F1.2", "to": ["U10.2", "J21.1"],
             "amps": round(i_24, 3)},
        ]
        waive = {
            "A2:J21": "a pogo handing 24 V to board B, not a load: that board's own "
                      "input capacitors (C30-C32) are behind its fuse",
            "A2:J1": "the cable socket, ahead of the fuse; the input capacitors C30-C32 "
                     "are on the fused side so a shorted one blows F1",
        }
    else:
        paths_24 = [
            {"net": "+24V_IN", "from": "J11.1", "to": "F1.1", "amps": round(i_own, 3)},
            {"net": "+24V", "from": "F1.2", "to": "U10.2", "amps": round(i_own, 3)},
        ]
        waive = {
            "A2:J11": "the seam pogo, ahead of the fuse; the input capacitors C30-C32 "
                      "are on the fused side so a shorted one blows F1",
        }
    notes["quality"] = {
        "power_paths": paths_24 + [
            # ⚠ HELD TO THE WHOLE RAIL, though a driver's VCC is only its logic supply:
            # the stretch that matters is L1's own exit onto the plane, all of the rail
            # leaves there, and every one of these paths starts with it.
            {"net": "+11V5", "from": "L1.2",
             "to": ["U%d.19" % (k + 1) for k in range(n_drv)], "amps": round(i_rail, 3)},
        ],
        "pinouts": {
            "XL-5050RGBW": "XINGLIGHT XL-5050RGBW datasheet, package drawing: pads 1-4 the "
                           "four anodes, 5-8 their cathodes; Steel:XINGLIGHT_XL-5050RGBW "
                           "is drawn from it",
            "TLC59711PWPR": "TI TLC59711 datasheet, Terminal Functions table, PWP "
                            "(HTSSOP-20) column, top view",
            BC.U_VALUE: "TI LMR33630 datasheet SNVSAN3F, Table 6-1, VQFN (RNX) column",
        },
        "waive": waive,
        "manual": _manual(board, n_drv),
    }
    if board == "a":
        notes["quality"]["pinouts"]["S4B-XH-SM4-TB"] = (
            "JST XH S4B-XH-SM4-TB drawing for pin 1; the way order is J_PINS above, "
            "harness.XH_PINOUT's supply ways first")
    with open(os.path.join(OUT_DIR, "%s.board.json" % name), "w") as f:
        json.dump(notes, f, indent=2)
    print("%-9s %6.1f x %.2f mm, %2d LEDs, %d zones, %d drivers, x%d per instrument"
          % (name, length, BOARD_W, len(xs), n_zone, n_drv, 1))
    return len(xs), n_zone, n_drv


BOARD_NOTES = {
    # ⚠ FOUR LAYERS -- AND NOT FOR THE PICKUP'S SAKE, WHICH IS WHY IT IS WORTH WRITING
    # DOWN. On noise this board wants two. The fret boards took four because their +X
    # edge comes within 14.08 mm of the magnetic pickup; this strip lies in the chassis
    # bottom, ~66 mm from the coil in Y and Z together, and coupling falls as 1/r^3:
    #     fret board, 4-layer   15.9 mm2 / 14.08^3 = 0.0057
    #     this board, 2-layer   96   mm2 / 66^3    = 0.00033
    # 17x quieter on two layers than the board already judged acceptable on four. That
    # argument still stands and it is not what decided this.
    #
    # WHAT DECIDED IT IS THAT A POUR CANNOT STAY IN ONE PIECE ON A 17 mm BOARD. Two
    # layers means the GND pour shares F.Cu with the parts, and the LED row's 6.10
    # courtyard plus the component lane's 7.80 leave it 3.30 mm to get past every LED --
    # in 24 places. The first route came back with 7 unconnected and FOUR OF THEM WERE
    # GND ZONE ISLANDS: the pour had been cut into pieces that never met. The other three
    # were zone returns that ran out of room in the same squeeze.
    #
    # Widening the board is the cheap fix and the chassis will not have it: the motor
    # bay's structure comes in below y ~40 and the +Y rail's inner face is at 55.55, so
    # the lane is what it is. Four layers puts GND and the rail on their own planes,
    # gives both outer layers back to routing, and turns every anode and every GND pad
    # into a via -- for about $19 on an order of five.
    #
    # In1 = the rail and In2 = GND, for the reason fret_led.py records: the conductor that
    # mirrors a zone's long F.Cu run is the RAIL, not ground, because the local bulk sits
    # at the driver.
    "layers": 4,
    "thickness_mm": 1.6,
    "zones": [("+11V5", "In1.Cu", 0.3), ("GND", "In2.Cu", 0.3)],
    "plane_layers": ("In1.Cu", "In2.Cu"),
    "local_inner": "B.Cu",
    "stitch_nets": ("+11V5", "GND"),
    # U10's two PGND pins reach the plane through the input capacitor beside each: a laid
    # 0.25 track, pin to capacitor pad, 0.6 mm, and the capacitor's own stitch via. TI's
    # layout wants no via inside that loop, and there is no room for one anyway.
    "stitch_exceptions": BC.STITCH_EXCEPTIONS,
    # ⚠ A SMALLER VIA, AND IT IS THE DRIVER'S ESCAPE FAN THAT ASKS FOR IT. Twelve outputs
    # leave one HTSSOP-20 on a 0.65 mm pitch and every one of them has to dive to an
    # outer layer beside the package: six vias have to fit in the 5.85 mm the pin column
    # spans, which is 0.98 apiece. At the 0.60/0.30 default that is 0.38 of air and the
    # router left two returns 1.1 mm short of their pads; at 0.50/0.25 it is 0.48.
    #
    # elec/lever_sensor.py records the same lever with the measurement behind it, and
    # the cost: 0.50/0.25 is inside JLCPCB's standard capability ("Multilayer: 0.15 mm
    # hole / 0.25 mm diameter") and is NOT surcharged -- the surcharge is for a 0.25 hole
    # with a diameter UNDER 0.45. It is an order-form field, though, not just a gerber
    # fact, which is why it is repeated in order_options below.
    "via_mm": (0.50, 0.25),
    # ⚠ 0.15 mm TRACK, for the same reason lever_sensor takes it: the tightest parts here
    # is a 0.65 mm pitch HTSSOP-20 with twelve outputs, and the
    # default 0.25 does not leave either escape room to turn. 0.15 on 1 oz carries ~0.5 A
    # at a 10 C rise against this board's largest signal load of 15 mA -- the constraint
    # is geometry, not current. The rails keep their own width below.
    "track_mm": 0.15,
    # ...and the two power nets are widened back up. +11V and GND are planes, so this is
    # really just the 24 V pass-through, which carries 0.24 A the length of the board.
    "net_widths": {"+24V": 0.30, "+24V_IN": 0.30},   # the inlet stub was routed at 0.15
                                                      # for 0.77 A, which wants 0.20
    "order_options": {
        "via size": "0.25 mm hole / 0.50 mm diameter -- SELECT THIS ON THE ORDER FORM. "
                    "Inside standard capability and not surcharged. The driver fan does "
                    "not route at the 0.60/0.30 default.",
    },
    "single_sided": True,        # every part on the face that fires at the floor
    "refs_on_fab": True,
    # ⚠ NO MOUNTING HOLE, AND NOT BECAUSE IT WAS FORGOTTEN. The channel holds five faces
    # -- shoulders under, lips over, a wall on -Y and the chassis body on +Y -- and the
    # sixth is the sliding axis, which the -X endplate closes when it goes on. The same
    # argument elec/lever_sensor.py records for its grooves.
    "no_mounting_holes": True,
    "qty_per_instrument": 1,
}


if __name__ == "__main__":
    for _b in FL.HALVES:
        n_led, n_zone, n_drv = build(_b)
    q = len(FL.HALVES)
    print("%d LEDs, %d zones, %d channels, %d drivers per instrument, %.2f A at %.2f V"
          % (n_led * q, n_zone * q, 4 * n_zone * q, n_drv * q,
             4 * n_zone * q * I_CHAN, V_RAIL))
    print("run %.2f mm, pitch %.3f, depth %.2f -> %.3f : 1"
          % (FL.run_len(), FL.pitch(), FL.depth(), 1.0 / FL.check_optics()))
