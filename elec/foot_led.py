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
    u10 = Part(name="LMR33630CRNX", ref_prefix="U", ref="U10", tag="U10", dest="NETLIST",
               tool="skidl", value="LMR33630CRNXR",
               description="24 V -> %.2f V synchronous buck, 2.1 MHz, 3 A "
                           "(LCSC C2071783)" % V_RAIL,
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
    # is still the quieter of the two things on this board: a tight 2.1 MHz hot loop
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
            "LMR33630CRNXR": "TI LMR33630 datasheet SNVSAN3F, Table 6-1, VQFN (RNX) column",
        },
        "waive": waive,
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
