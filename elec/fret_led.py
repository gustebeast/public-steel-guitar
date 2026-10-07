"""FRET LIGHTING boards -- one RGBW zone per fret, four LEDs per zone. x2.

    py -3.12 elec/fret_led.py     # -> elec/out/fret_led_{mid,key}.{net,board.json}

TWO BOARDS FROM ONE MODULE, because there are two deck panels and each board has to
come off with its own panel:

    fret_led_mid   frets 24..10   15 zones   60 channels   5 x TLC5971   210.3 x 70.4
    fret_led_key   frets  9.. 2    8 zones   32 channels   3 x TLC5971   211.8 x 70.4

⚠ THE GEOMETRY IS AN INPUT, NOT AN OUTPUT -- the second board in elec/ of which that
is true (the first is optical.py, for the same reason). Every fret's X, the four LED
Y positions, the board's width and its Z all come from `src/fret_light.py`, which
solved them against the deck's own datums and the illuminance model. Nothing here is
retyped: if a fret moves, this board moves with it, and if the two ever disagree the
build stops rather than laying out a board that does not match the instrument.

WHAT IT DRIVES, and why it is shaped like this (docs/fret-led.md sections 4 and 6):
one CONTROLLABLE ZONE per fret, and a zone is four LEDs IN SERIES on one channel.
Series is the whole economy of the board -- a series string draws the same current as
a single LED, so four-per-fret costs rail VOLTS, not rail amps, and the channel count
follows FRETS (24) rather than LEDs (92). A TLC5971 carries 3 RGBW zones, so zones
come in threes and both boards land on a whole number of drivers with nothing wasted.

ONE CHAIN ACROSS TWO BOARDS, JOINED AT THE PANEL SEAM BY FOUR TIP-TO-TIP POGOS
(docs/fret-led.md 9.1f). The keyhead board carries the harness plug, the fuse and the
24 V -> 14.5 V buck for BOTH; the seam carries +14V5, GND and the TLC5971 chain out of
key's last driver into mid's first:

    Pi cap --J1--> fret_led_key: U1 (fret 2) .. U3 (fret 8)
                     --SCK_SEAM/SDT_SEAM, +14V5, GND over the seam-->
                   fret_led_mid: U1 (fret 10) .. U5 (fret 24), chain end

⚠ THE SUPPLY MOVED TO KEY BECAUSE MID'S BAY COULD NOT HOLD IT AND THE JOINT. The pads
have to sit within ~3.3 mm of each board's seam edge -- the two setbacks SUM to the
tip-to-tip span, 2 x (6.30 - 2.25) - 1.45 = 6.65, so neither can be generous -- and
mid's seam end is its 9.70 mm bay, which already held J1, the buck column and L1.
Key's bay is at the far (nut) end and has 17 mm. Moving the harness there also makes
the whole fretboard ONE chain in ascending X with no trace doubling back: the harness
lands at key's -X end, key's chain runs +X to the seam, crosses, and mid's runs +X to
the bridge. And one SDT does both boards, so the Pi cap's second fret header goes.

⚠ AND THE SEAM CARRIES 14.5 V, NOT 24. §9.1b assumed each board made its own rail; with
one buck the rail crosses instead, which is what lets mid lose its whole supply. The
part is unchanged -- C5203987 is still the only side-mount pogo in the library rated
above 12 V, and 14.5 is above 12.

⚠ THE HISTORY, for whoever reads 9.1: the joint was retracted there on a contact-height
argument that was right (a side-mount pin fires 1.90 above its own board and misses a
coplanar neighbour's EDGE) and a length argument that was wrong (the 12.00 is a SUM of
two setbacks, not a gap they must fit in). Tip to tip, both axes are 1.90 up.

THE INSTALL ORDER: attach each board to its panel, slide the mid panel on, slide the
keyhead panel on until the panels butt (the pogos load in that last few mm -- 9.1e),
plug J1 on key, fit the endplate.
"""
from __future__ import annotations

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import fret_light as FL  # noqa: E402  (the geometry source -- see above)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import skidl  # noqa: E402
from skidl import ERC, Net, Part, Pin, generate_netlist  # noqa: E402

import netcheck  # noqa: E402
import harness as _H  # noqa: E402
import placecheck  # noqa: E402
import buck_cell as BC  # noqa: E402
from placecheck import check_placement, fp_box  # noqa: E402

P = Pin.types.PASSIVE

# ── the parts ────────────────────────────────────────────────────────────────────────
LED_FP = "Steel:XINGLIGHT_XL-5050RGBW"
DRV_FP = "Package_DFN_QFN:Texas_RGE0024H_VQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm"
DRV_ROT = 90.0
DRV_OUT_PINS = tuple(range(7, 13)) + tuple(range(19, 25))    # SBVS146D: OUTR2..B3, R0..B1
BUCK_FP = "Steel:Texas_RNX0012_VQFN-HR-12_2x3mm_P0.5mm"
IND_FP = "Inductor_SMD:L_Sunlord_SWPA5040S"   # = buck_cell.L1_FP, asserted in _supply
J_FP = "Connector_JST:JST_XH_S4B-XH-SM4-TB_1x04-1MP_P2.50mm_Horizontal"
# mouth (the footprint's local +Y 5.30) to the PAD CENTROID layout anchors on (the mean of
# its six pads, -0.9833), both read out of the .kicad_mod
J_ANCHOR = 5.30 + 0.9833
R_FP = "Resistor_SMD:R_0402_1005Metric"
C_FP = "Capacitor_SMD:C_0402_1005Metric"
C08_FP = "Capacitor_SMD:C_0805_2012Metric"
C12_FP = "Capacitor_SMD:C_1206_3216Metric"
POGO_FP = "Steel:Xinyangze_YZF0002-38080-02"
TP_FP = "TestPoint:TestPoint_Pad_D1.5mm"
# the board that carries the harness plug and the buck -- see the module docstring
HARNESS = "key"

# ⚠ THE LED IS TOP-MOUNT, WHICH IS THE ONE THING THIS BOARD NEEDS OF IT AND WHICH THIS
# PROJECT HAD RECORDED WRONG. docs/fret-led.md section 5.3 called XL-5050RGBW "a
# side-mount 5050 chosen for a side-firing strip" and left the package choice open on
# that basis. LCSC's own attribute table for C7371891 reads "Installation method:
# Top-mount", 120 degree viewing angle, 5.0 x 5.0 x 1.6 -- it fires UP, out of the
# clear encapsulant, which is exactly what a cell wants. The package choice is closed
# and the part does not change.
LED_MPN = "XL-5050RGBW"
# ⚠ AND ITS BODY IS 1.60 TALL, not the 1.40 fret_light carried. Same listing, same
# line: "Dimensions (L/W/H): 5.0x5.0x1.6mm". 0.20 mm of optical depth, and the module
# now reads 1.60 -- see the note there.

# IREF sets every channel's ceiling: I = 41 x 1.21 / R (TLC5971 datasheet). 3k3 =
# 15.0 mA, three quarters of the LED's 20 mA rating, and the figure the whole power
# budget in docs/fret-led.md section 6.2 is written against. Dimming rides BC and GS,
# not this resistor -- see 6.5 item 3.
R_IREF = "3k3"

# ── the rail ─────────────────────────────────────────────────────────────────────────
# FOUR DICE IN SERIES, AND THE TOP OF THE BIN SETS THE RAIL.
# ⚠ THE STRING IS 13.6 V, NOT 12.8 (manual quality pass, 2026-10-05). XINGLIGHT's sheet
# gives green, blue and white 3.0 to 3.4 V at 20 mA, +-0.1, and red 2.0 to 2.4 -- this
# file said "3.0-3.2". Four at 3.4 is 13.6 V, and the 14.02 V this rail was could sit as
# low as 13.6 itself (0.985 V reference, 1 % resistors): no headroom at all on a
# top-of-bin string, where the sink needs about 0.3 V at 15 mA to stay flat (TI SBVS146D
# figures 7 and 8).
#
# 14.52 V: R10 over (R11 parallel R12) on the LMR33630's 1.000 V reference, 100k over
# (7k68 || 200k). The rail's own low limit is then 14.04 V, 0.44 V over the worst string
# -- and the sheet's 3.4 V is at 20 mA, where these run at 15.
# ⚠ AND NOT HIGHER, BECAUSE EVERY EXTRA VOLT IS HEAT IN THE DRIVER. One shared rail means
# red drops the difference:
#     red     (14.52 - 4 x 2.1) x 15 mA = 92 mW per channel, typical dice
#     W/G/B   (14.52 - 4 x 3.1) x 15 mA = 32 mW per channel
#     per TLC5971, 3 zones x (92 + 3 x 32) = 0.56 W, plus about 0.12 W of its own supply
#     current at 14.5 V: 0.68 W typical, 0.86 W with every die at the bottom of its bin
# At 38 C/W (SBVS146D thermal table, RGE) that is 26 to 33 C over the air under the deck,
# with every fret at full white: 73 C at the junction in 40 C air, against 125 operating
# and 150 shutdown. 15.0 V would have matched the foot strip's 0.9 V of worst-case
# headroom and cost another 7 C here. Red also wants trimming down for colour balance,
# which takes its share off again (docs/fret-led.md 6.2).
R_FBT, R_FBB, R_FBP = 100e3, 7.68e3, 200e3
V_RAIL = round(1.0 * (1.0 + R_FBT / (R_FBB * R_FBP / (R_FBB + R_FBP))), 2)      # 14.52
assert abs(V_RAIL - 14.52) < 0.005, V_RAIL
I_CHAN = 0.015
I_VCC = 0.03                         # a TLC5971's own supply current, with margin: what
                                     # its VCC pin's stub carries. The LED current does not
                                     # pass through it.

# ── the deck's own numbers, read not copied ──────────────────────────────────────────
# Everything below comes out of src/fret_light.py. A board-local X is a world X minus
# the board's centre; Y is the world Y unchanged, because the fret runs along it and
# the LED positions ARE the optical solution.
BOARD_W = 2.0 * FL.BOARD_HALF_W                  # 70.40
LED_YS = FL.LED_YS                               # -30.40 -10.40 +10.40 +30.40

# ⚠ THE BAY AND THE SPAN COME FROM fret_light TOO. Where a board may reach is a fact
# about the deck and the harness -- the mid board stops 0.90 mm short of the keyhead
# comb's overhanging end wall, the keyhead board 2.30 short of `wire_usb` -- so both
# ends are measured there and read here. See fret_light.BOARD_BAY for the numbers and
# what was probed to get them.

# ── the layout's Y lanes ─────────────────────────────────────────────────────────────
# ⚠ THE DRIVERS LIVE IN THE +Y MID-BAND, AND THAT IS THE WHOLE ROUTING IDEA. The LED
# rows sit at |y| = 10.40 and 30.40 with a 6.10 courtyard, which leaves two clear bands
# 13.90 mm tall running the FULL LENGTH of the board at 13.45 < |y| < 27.35, plus a
# 14.70 mm one down the middle. Put every driver in the +Y band and:
#   * a zone's return leaves its +Y outer LED at y 30.40 and travels 10 mm to the
#     driver, crossing NO row of LEDs -- the alternative, a driver in the central band,
#     makes all twelve returns cross the inner row through a 3.04 mm gap between
#     courtyards at the 9.14 mm fret pitch;
#   * the SPI chain runs straight down the same band, driver to driver, because the
#     TLC5971's inputs (SDTI 1, SCKI 2) and its re-buffered outputs (SCKO 5, SDTO 6)
#     are the two ends of one side of the package, turned to face the band's lower
#     edge, so a left-to-right chain is a straight line;
#   * the -Y band stays empty, and IS the bay's overflow on both boards.
DRV_Y = 20.40
PASSIVE_Y = 15.60                                # under the driver, out of the returns
SPI_Y = 13.95                                    # the band's lower edge
LED_ROW = tuple(LED_YS)

# ⚠ WHICH WAY A ZONE'S LEDs FACE IS A ROUTING DECISION. The footprint's anodes (1-4)
# are its -X pad column and its cathodes (5-8) its +X column. A zone's four returns
# leave from the cathode column, so a zone sitting +X of its driver is rotated 180 to
# turn that column back toward it. Rotating a WHOLE zone keeps its three chain links
# parallel; rotating single LEDs (or alternating the feed direction per colour, which
# was the first attempt at balancing the two sides) crosses them, and four crossings
# per fret gap is 180 vias on the mid board for nothing.
ROT_TOWARD_DRIVER = {-1: 0.0, 0: 0.0, 1: 180.0}

# TLC5971 (RGE, VQFN-24), SBVS146D Pin Functions: 1 SDTI 2 SCKI 3 NC 4 NC 5 SCKO 6 SDTO
# 7 R2 8 G2 9 B2 10 R3 11 G3 12 B3 13 VCC 14 NC 15 VREG 16 IREF 17 NC 18 GND 19 R0
# 20 G0 21 B0 22 R1 23 G1 24 B1, thermal pad = GND (KiCad numbers it 25).
# Turned a quarter turn (DRV_ROT): 19..24 run down the -X side, 7..12 up the +X side,
# the data side faces -Y and the supply side +Y.
#
# ⚠ OUTPUTS ARE MAPPED BY GEOMETRY, NOT BY THE DATASHEET'S COLOUR GROUPS -- the same
# finding as elec/led_strip.py, for the same reason and with a different answer here.
# The three zones a driver serves are spread in X, one either side and one directly
# above, so:
#   zone -X   pins 21, 22, 23, 24    the -X side's lower four
#   zone mid  pins 19, 20, 11, 12    the TOP of both sides, straight down from y 30.4
#   zone +X   pins 7, 8, 9, 10       the +X side's lower four
# FIRMWARE MUST USE THIS TABLE. Global brightness correction (BC) is per colour GROUP
# and this mapping puts one zone's four dice in different groups, so all three BC
# fields are set equal and every per-fret adjustment happens in GS -- which is also
# what keeps the 16-bit depth useful at the dim end (docs/fret-led.md 6.5, 6.6).
ZONE_OUTS = {-1: (21, 22, 23, 24), 0: (19, 20, 11, 12), 1: (7, 8, 9, 10)}
COLOURS = ("R", "G", "B", "W")


def _idle_outs(n_drv, n_zone):
    """Outputs of the LAST driver that no fret uses: a short trio sits at sides 0 and +1
    (see build), so the -X zone's four are the idle ones."""
    short = 3 * n_drv - n_zone
    assert short in (0, 1), (n_drv, n_zone)
    return ZONE_OUTS[-1] if short else ()


def _unconnected(panel, n_drv, n_zone):
    d = {"U[1-%d]" % n_drv: {"pins": "3 4 14 17",
                             "why": "TLC5971 RGE: no internal connection (SBVS146D)"}}
    idle = _idle_outs(n_drv, n_zone)
    if idle:
        d["U%d.2[1-4]" % n_drv] = ("constant-current sinks no fret uses (%d frets on %d "
                                  "drivers): left open, GS data 0" % (n_zone, n_drv))
        assert tuple(idle) == (21, 22, 23, 24), idle
    if panel == HARNESS:
        d["U10.8"] = "LMR33630 PG: an open drain, left open as its sheet allows"
        d["J1.MP"] = "the socket's two mounting lands: solder only"
    else:
        d["U%d.[56]" % n_drv] = "SCKO / SDTO of the last driver in the chain"
    return d


# ── the placement checks ─────────────────────────────────────────────────────────────
# Both live in elec/placecheck.py now, because the foot-light strip needs the same two
# and a second copy is how two files stop agreeing. See that module for what each one
# caught and why it runs before the netlist rather than after the route.
#
# check_spans is the deck-wall check, given this board's own walls: the comb hangs a
# 1.60 mm wall onto the board's top face at EVERY fret boundary, which no DRC can see.
def check_walls(name, place, fps, walls, bay_x1, cx):
    """No part's BODY may sit under one of the light-cell comb's walls."""
    from src import fret_light as _FL
    spans = [(bx - _FL.WALL / 2.0, bx + _FL.WALL / 2.0) for bx in walls]
    bay = {r for r, (x, _y, _rot) in place.items() if x + cx <= bay_x1}
    placecheck.check_spans(name, {r: (x + cx, y, rot)
                                  for r, (x, y, rot) in place.items()},
                           fps, spans, clr=WALL_CLR, axis=0, skip=bay)


WALL_CLR = 0.3

# ── THE DRIVER'S HEAT PAD: FIVE VIAS, NOT ONE (manual quality pass M25) ───────────────
# The stitcher gives an exposed pad one via at its centre, which is a ground connection
# and not a heat path: one 0.30 mm barrel down 1.28 mm to the ground plane is about
# 190 C/W, under a part that dissipates most of a watt at full white. TI's land pattern
# for the RGE package (SBVS146D, RGE0024H example board layout) draws nine on a 1.1 mm
# grid across the 2.7 x 2.7 copper.
# ⚠ FOUR MORE, ON THE CROSS BETWEEN THE PASTE PANES. The footprint prints the pad's paste
# as four panes with a gap down each axis; TI's four corner vias stand in the middle of a
# pane each and would drink it. These four stand on the axes, on TI's own 1.1 mm pitch:
# with the centre one about 40 C/W to the plane.
DRV_PAD_VIAS = ((-1.10, 0.0), (+1.10, 0.0), (0.0, -1.10), (0.0, +1.10))

# ── 1 k IN SERIES WITH EACH SIGNAL AT THE CABLE (manual quality pass M18, 2026-10-05) ────
# The Pi drives SCK and SDT at 3.3 V through 68 ohm (pi_cap R1..R4), and this board can be
# dark while the Pi is up: its fuse open, the lights' fuse on the motor board open, the
# 24 V lead off, or a Pi on its own USB supply on the bench. A TLC5971's inputs are rated
# to VREG + 0.6 V (SBVS146D 6.1), and VREG is 0 V then: the pin's protection diode
# conducts and the Pi powers the driver's logic through it, as much as a GPIO will give.
# 1 k limits that to 2.7 mA. Against the pin's few pF it is a 10 ns corner, on a clock
# TI allow to 10 MHz and edges the source resistor has already slowed.
R_SERIES = "1k 1%"

# ── the buck's cell in the bay: buck_cell's frame, +x towards the inductor ────────────
CELL_Y = -17.80                      # U10: the input slab ends 0.5 short of J1's courtyard
                                     # and the output HF capacitor 2.2 from the -Y edge
CELL_REFS = {"CIN_A": "C32", "CIN_B": "C35", "CBOOT": "C33", "CVCC": "C34",
             "RFBB": "R11", "RFBT": "R10", "RFBP": "R12"}
BULK_REFS = {"CIN_1": "C30", "CIN_2": "C31", "L1": "L1",
             "COUT_1": "C36", "COUT_2": "C37", "COUT_HF": "C38"}
CELL_BULK = dict({ref: BC.BULK[role] for role, ref in BULK_REFS.items()}, **{
    "TP1": (-6.50, +5.00, 0.0),      # +24V, beside the input bulk
    "TP3": (+2.50, +5.00, 0.0),      # GND
    "TP2": (+12.50, +5.00, 0.0),     # the rail, beside the output bulk
})
cell_org = []                        # (origin, turn) of the cell as _supply placed it


def _r(ref, value, desc, fp=R_FP):
    return Part(name="R", ref_prefix="R", ref=ref, tag=ref, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(ref, value, desc, fp=C_FP):
    return Part(name="C", ref_prefix="C", ref=ref, tag=ref, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=fp,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def zones_for(x_lo, x_hi):
    """[(fret, world x)] the frets this board serves, KEYHEAD END FIRST -- off fret_light.

    ⚠ THE ORDER IS THE SPI CHAIN'S ORDER AND IT DECIDES TWO THINGS, both of which came
    out backwards when this simply took `fret_xs()` as it comes (bridge end first):

    1. **The clock would have run the length of the board and back.** The harness lands
       in the bay at the -X end, so a chain starting at the bridge end means SCK and SDT
       travel 200 mm +X to reach driver one and the chain then walks back -- two passes
       of a clocked edge over the rail plane, the outbound one ending at the board's +X
       tip, which is the end that comes within 14.08 mm of the magnetic pickup. Starting
       at the bay makes it one pass, away from the pickup, and costs nothing.
    2. **The driver's pin mapping was mirrored.** ZONE_OUTS keys a trio by which side of
       its driver a zone sits on, and with the list descending in X, `trio[0]` was the
       +X zone being handed the -X pin column and the unrotated footprint. Both are the
       wrong way round: its cathodes faced away from the driver and its returns had to
       cross the package. The router coped; it should not have been asked to.

    Ascending X puts trio[0] on the -X side, which is what ZONE_OUTS and
    ROT_TOWARD_DRIVER are written for, and puts driver one next to the connector."""
    return sorted(((n, x) for n, x in FL.fret_xs() if x_lo <= x <= x_hi),
                  key=lambda t: t[1])


def _supply(place, fps, gnd, v24, vrail, bay_x0, bay_x1, cx):
    """The bay: harness in, fused, 24 V -> 14.5 V, at the board's -X end.

    ⚠ AT THE -X END BECAUSE THAT IS THE FAR END FROM THE PICKUP (docs/fret-led.md 6.3
    item 3). The buck is the highest di/dt thing on the board and the magnetic pickup
    comes within 14.08 mm of the MID board's +X edge at its neck-most slide; putting
    the switcher 210 mm away leaves nothing but the smoothed rail at that end. It is also
    where the harness has to land, so one region carries all the service access."""
    # A 4-WAY XH, ONE CONTACT A CIRCUIT (user, 2026-10-04). It was a 6-way PH with the rail
    # and its return doubled. XH is 3 A per contact against the 0.93 A both boards draw
    # at 24 V.
    # ⚠ XH BECAUSE IT IS 24 V. The instrument's rule (user, 2026-10-04): PH carries 5 V
    # and XH carries 24 V, so no lead can put the higher rail on the lower one's socket.
    # ⚠ AND THE ORDER IS harness.XH_PINOUT's -- GND, V24, then the two signals -- so the one
    # mistake still possible is harmless both ways round: a motor-bus lead on this socket
    # powers the board correctly and lays CAN on the two SPI inputs, and this lead on a
    # motor-bus socket lays 3.3 V logic on CAN. Neither reverses a supply.
    J_PINS = tuple(_H.LED_DROP)          # GND, V24, SCK, SDT: the Pi cap's J3, way for way
    assert J_PINS[:2] == tuple(_H.XH_PINOUT[:2]), (
        "the fret harness plug is an XH and its supply ways are not the XH bus's own")
    j = Part(name="S4B-XH-SM4-TB", ref_prefix="J", ref="J1", tag="J1", dest="NETLIST",
             tool="skidl", value="S4B-XH-SM4-TB",
             description="harness in from the Pi daughter board: GND, 24 V, SCK, SDT",
             footprint=J_FP,
             pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(J_PINS)])
    v24_in = Net("+24V_IN")
    gnd += j[1]
    v24_in += j[2]
    sck, sdt = Net("SCK_IN"), Net("SDT_IN")
    series = []
    for ref, way, net in (("R21", 3, sck), ("R22", 4, sdt)):
        cable = Net("%s_CABLE" % J_PINS[way - 1])
        rs = _r(ref, R_SERIES, "%s in series at the cable: limits what a live Pi can push "
                               "into a dark driver's input" % J_PINS[way - 1])
        cable += j[way], rs[1]
        net += rs[2]
        series.append(ref)

    # The fuse protects the TRUNK, not the board: a shorted buck must not pull the
    # instrument's 24 V down. Same argument, same part class as motor_ctrl's F1.
    # ⚠ 2 A, NOT 1: this buck feeds BOTH boards now. 23 zones x 4 x 15 mA = 1.38 A at
    # 14.52 V is 0.93 A at 24 V at 90 %, and a 1 A fuse at 93 % of rating ages open.
    # ⚠ A PART, NOT "2A": a fuse is chosen for its voltage and its speed as well as its
    # current, and a value string picks none of them. JDT JFC1206 fast-acting, 63 V.
    f1 = Part(name="Fuse", ref_prefix="F", ref="F1", tag="F1", dest="NETLIST",
              tool="skidl", value="JFC1206-1200FS",
              description="24 V fuse, fast, 63 V, 2 A (LCSC C136345) -- a shorted U10 "
                          "must not feed the fault back out into the trunk",
              footprint="Fuse:Fuse_1206_3216Metric",
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v24_in += f1[1]
    v24 += f1[2]

    # ⚠ A MEGAHERTZ VARIANT, AND IT IS THE POINT. It was LMR33630CRNXR, the optical
    # board's 2.1 MHz buck; it is the 1.4 MHz LMR33630BRNXR now, on the same land, because
    # the C part lost 1.45 W here and sat at about 127 C (elec/buck_cell.py has the
    # figures). What must NOT go here is the 400 kHz "A": beside a magnetic pickup it
    # puts its fundamental two octaves nearer the audio band than this one, and it wants
    # a 15 uH inductor that does not fit the bay. At light load every LMR33630 pulse-skips
    # whatever its letter, which drops the switching energy to a load-dependent rate.
    # Measured against THIS board's floor: the eight drivers' own ICC is tens of mA
    # even with every LED dark, which puts the skip rate in the hundreds of kHz. It
    # only reaches the audio band at loads this board cannot present while powered.
    # Pinout, SNVSAN3F Table 6-1 (VQFN column): 1 PGND, 2 VIN, 3 NC, 4 BOOT, 5 VCC,
    # 6 AGND, 7 FB, 8 PG, 9 EN, 10 VIN, 11 PGND, 12 SW. TI: "connect the SW pin to NC
    # on the PCB". PG unused. EN to VIN, which the datasheet allows.
    u = Part(name="LMR33630", ref_prefix="U", ref="U10", tag="U10", dest="NETLIST",
             tool="skidl", value=BC.U_VALUE,
             description="24 V -> %.2f V synchronous buck, %.1f MHz, 3 A (LCSC %s)"
                         % (V_RAIL, BC.U_FSW / 1e6, BC.U_LCSC),
             footprint=BUCK_FP, pins=[Pin(num=n, func=P) for n in range(1, 13)])
    sw, boot, vcc, fb = Net("SW"), Net("BOOT"), Net("BUCK_VCC"), Net("FB")
    gnd += u[1], u[11], u[6]
    v24 += u[2], u[10], u[9]
    sw += u[3], u[12]
    boot += u[4]
    vcc += u[5]
    fb += u[7]
    Net("BUCK_PG_NC").connect(u[8])

    # ⚠ THE VALUE IS THE PART NUMBER, for the reason optical.py gives at its own L1:
    # "4.7uH" does not specify an inductor, and saturation is what decides whether this
    # supply survives a fault. buck_cell.L1_VALUE says which part and why. Ripple at
    # 14.52 V out, 24 V in, 1.4 MHz: Vout(1-D)/(f L) = 0.87 A pk-pk, so the peak at BOTH
    # boards' 1.38 A full-white load is 1.82 A against 3.50 A of guaranteed saturation.
    assert IND_FP == BC.L1_FP
    l1 = Part(name="L", ref_prefix="L", ref="L1", tag="L1", dest="NETLIST", tool="skidl",
              value=BC.L1_VALUE, description=BC.L1_DESC,
              footprint=IND_FP, pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw += l1[1]
    vrail += l1[2]

    # 1206 on the input for DC-BIAS derating, not merely the voltage rating: an 0805
    # 50 V part loses most of its capacitance at 24 V of bias. Same on the output --
    # 14 V is most of an 0805 25 V part's curve.
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
    # VREF is 1.0 V (SNVSAN3F 7.5: 0.985 to 1.015), and the divider is V_RAIL's, above.
    r10 = _r("R10", "100k 1%", "rail feedback divider, top (TI: 100k)")
    r11 = _r("R11", "7k68 1%", "rail feedback divider, bottom")
    r12 = _r("R12", "200k 1%", "across R11: 7k68 || 200k = 7.396k, %.2f V with R10"
                               % V_RAIL)
    vrail += r10[1]
    fb += r10[2], r11[1], r12[1]
    gnd += r11[2], r12[2]
    # THREE TEST PADS, bare copper, labelled by kicad_silk with their nets (M9): the two
    # rails a first power-up is checked on, and a ground beside them for the other probe.
    for ref, net, what in (("TP1", v24, "+24V behind the fuse"),
                           ("TP2", vrail, "the LED rail, %.2f V" % V_RAIL),
                           ("TP3", gnd, "ground for the probe")):
        tp = Part(name="TestPoint", ref_prefix="TP", ref=ref, tag=ref, dest="NETLIST",
                  tool="skidl", value="TP",
                  description="test pad -- %s; bare copper, no component" % what,
                  footprint=TP_FP, pins=[Pin(num=1, func=P)])
        net += tp[1]

    # ── THE BAY, the only part of this board laid out by hand ────────────────────────
    # J1's mouth is its footprint's +Y and the placement anchors on the PAD CENTROID, so
    # rot 270 turns the mouth -X and the centroid sits 5.8125 +X of it (4.4 from the
    # footprint origin to the mouth, 1.4125 from the origin back to the centroid) -- the
    # arithmetic elec/led_strip.py records for this exact part, whose first two layouts
    # had the sign wrong and hung both connectors off the board ends.
    #
    # ⚠ J1's COURTYARD REACHES 11.91 BACK FROM THE BOARD EDGE AND THE MID BOARD'S BAY IS
    # 10.50, and that is fine: the last 1.41 hangs over the first light cell, where the
    # nearest other part is fret 10's outer LED, 0.38 further in. Its BODY is what has to
    # fit, and that is 7.6 deep (F.Fab -3.2..+4.4) -- 8.6 from the edge with the mouth
    # 1.0 inside it, clear of the comb's end wall by 1.9. A courtyard is an assembly
    # keep-out against other PARTS; the deck is not one, and check_walls measures the
    # deck against bodies for exactly that reason.
    #
    # ⚠ AND THE REST IS THE BUCK'S OWN CELL, TURNED TO RUN DOWN THE BAY (manual quality
    # pass M13, 2026-10-05). It was one column of parts in the supply's own order, which
    # put the feedback divider 15 mm from the FB pin, at the far end past the inductor and
    # the output bulk, and gave the package one input capacitor where TI asks for one at
    # each of its two VIN/PGND pairs. elec/buck_cell.py is the placement the optical board
    # measured against TI's layout example; here it is turned so its inductor end points
    # -Y, away from J1, with the feedback parts on the board-edge side and the switch node
    # on the other.
    #
    # ⚠ IT STAYS IN THE -Y HALF: the M4's deck boss is O9.2 on the board's top face in
    # the +Y half of the bay (fret_light.M4_Y), and the +Y edge carries the retaining
    # notches. F1 is alone in +Y because it is the only part of the supply that is NOT in
    # a loop that matters: it is upstream of the input bulk, so the hot loop closes
    # without it and its feed from J1 can be as long as it likes.
    #
    # ⚠ THE FOUR 1206s LIE ALONG X HERE, WHICH IS THE BOARD'S LONG AXIS, AND THAT IS A
    # DECISION (M38). On the foot strip the same cell stands them across a 290 x 17 mm
    # board that bends. This board is 211 x 70, held by two M4s and a lip, and these four
    # are within 10 mm of its -X end, where a bend along X has no moment to give them. In
    # exchange the cell keeps one shape on both boards, with its ground and input slabs
    # taking the bulk capacitors in.
    bx0, bx1 = bay_x0 - cx, bay_x1 - cx
    mouth = bx0 + 1.0
    # 5.25 from the board edge: 1.07 between the board edge and the feedback pair's far
    # courtyard on one side, and the whole rest of the bay for the test pads on the other
    col = bx0 + 5.25
    org, turn = (col, CELL_Y), 270.0
    place["J1"] = (mouth + J_ANCHOR, 0.00, 270.0)
    place["U10"] = BC.at(org, turn, 0.0, 0.0)
    for role, ref in CELL_REFS.items():
        place[ref] = BC.at(org, turn, *BC.CORE[role])
    for ref, (dx, dy, rot) in CELL_BULK.items():
        place[ref] = BC.at(org, turn, dx, dy, rot)
    place["F1"] = (col, 12.00, 180.0)
    # the two series resistors, just past J1's courtyard on their own lands' lines (the
    # lands' centres are 3.25 +X of the pad centroid, the courtyard ends at 6.05, and
    # ways 3 and 4 are 1.25 and 3.75 towards -Y)
    for ref, dy in zip(series, (-1.25, -3.75)):
        place[ref] = (mouth + J_ANCHOR + 7.30, dy, 0.0)
        fps[ref] = R_FP
    fps.update(dict(
        [("J1", J_FP), ("U10", BUCK_FP), ("L1", IND_FP),
         ("F1", "Fuse:Fuse_1206_3216Metric"), ("R10", R_FP), ("R11", R_FP), ("R12", R_FP)]
        + [(r, C12_FP) for r in ("C30", "C31", "C36", "C37")]
        + [(r, C_FP) for r in ("C32", "C33", "C34", "C35", "C38")]
        + [(r, TP_FP) for r in ("TP1", "TP2", "TP3")]))
    cell_org[:] = [org, turn]
    assert bx1 - bx0 >= 9.0, "the bay is %.2f mm long and J1 plus the buck needs 9" % (
        bx1 - bx0)
    return sck, sdt


# the rail and its return cross the seam on one spring pin each, 0.90 A, and each enters
# its plane on three barrels, not the stitcher's one (buck_cell.land_vias, M3)
SEAM_SUPPLY = {"+14V5": "+14V5", "GND": "GND"}
seam_vias = []


def _seam(panel, place, fps, cx, nets):
    """The four seam pogos at this board's seam edge -- geometry from fret_light.

    ⚠ NOT PLACED HERE. The pad X is where the two setbacks sum to the tip-to-tip span
    with the panels butted, and the lanes are between key's fret-9 LED rows; both are
    deck facts, so src/fret_light.py owns them and this reads them (pogo_pads)."""
    rot = 0.0 if FL.pogo_fire(panel) < 0 else 180.0     # the footprint fires -X
    for i, (x, y, net) in enumerate(FL.pogo_pads(panel)):
        ref = "J%d" % (11 + i)
        j = Part(name="POGO", ref_prefix="J", ref=ref, tag=ref, dest="NETLIST",
                 tool="skidl", value=FL.POGO_MPN,
                 description="seam pogo, %s -- tip to tip with the other board's %s "
                             "(LCSC C5203987)" % (net, ref),
                 footprint=POGO_FP, pins=[Pin(num=1, func=P)])
        nets[net] += j[1]
        place[ref] = (x - cx, y, rot)
        fps[ref] = POGO_FP
        if net in SEAM_SUPPLY:
            seam_vias.extend(BC.land_vias(SEAM_SUPPLY[net], x - cx, y))


def _arrival(place, fps, gnd, vrail, bay_x0, cx):
    """Mid's end of the rail: bulk where it comes in over the seam.

    Every driver has its own local bulk, which is what its zones' PWM draws from; this
    is for the JOINT -- 0.90 A arriving through two spring contacts has an inductance a
    plane does not, and the step each time a zone switches should not ring against it."""
    bx0 = bay_x0 - cx
    col = bx0 + FL.pogo_set()["mid"]          # the pogos' own column, in the -Y half
    for ref, val, fp, xy, why in (
            ("C36", "10uF/50V", C12_FP, (col, -9.40), "rail arrival bulk"),
            ("C37", "10uF/50V", C12_FP, (col, -12.60), "rail arrival bulk"),
            ("C38", "100nF/50V", C_FP, (bx0 + 7.50, -4.50), "rail arrival HF bypass")):
        c = _c(ref, val, why + " -- the rail comes in over the seam pogos", fp)
        vrail += c[1]
        gnd += c[2]
        place[ref] = xy + (0.0,)
        fps[ref] = fp



def _manual(panel, n_drv, n_zone, facts):
    """The manual quality items (cadkit/PCB_QUALITY.md), signed 2026-10-05 against the
    routed boards and the makers' sheets. M12 is left open on purpose: what remains of
    it can only be done on the day of the order (.ins/WORKLIST-brenner.md, NEEDS USER).
    `facts` are the numbers measured after the last route (MEASURED, below)."""
    key = panel == HARNESS
    n_ch = 4 * n_zone
    seam_y = "+14V5 at -9.05, GND -4.55, SCK 11.35, SDT 15.85"
    m = {
        "M1": ("two joints. J1 to the Pi cap's J3: a 4-way JST XH lead, straight through, "
               "way n to way n -- 1 GND, 2 24 V, 3 SCK, 4 SDT at both ends "
               "(harness.LED_DROP, asserted here and in pi_cap.py; this board's lands "
               "read GND, +24V_IN, SCK_CABLE, SDT_CABLE on the routed board). XH is "
               "shrouded and keyed. The seam, J11..J14 to the mid board's J11..J14: "
               "spring pins tip to tip, both boards face up under one deck, so equal Y "
               "is the same pin -- %s on BOTH routed boards. SCK_SEAM here is U3's SCKO "
               "and is the mid board's U1 SCKI" % seam_y
               if key else
               "one joint, the seam: J11..J14 meet the keyhead board's J11..J14 tip to "
               "tip, both boards face up under one deck, so equal Y is the same pin -- "
               "%s on BOTH routed boards. SCK_SEAM is key's U3 SCKO and this board's U1 "
               "SCKI. Each board is screwed to its own panel and the panels butt on "
               "the deck's rails, which is what holds the pins in line; nothing else "
               "plugs into this board" % seam_y),
        "M2": "the only polarised parts are the LEDs. XINGLIGHT's drawing: pads 1 to 4 "
              "are the four anodes, 5 to 8 their cathodes; the netlist takes the rail to "
              "an anode and the cathode on to the next LED or the driver's sinking "
              "output. The fab's own library footprint for C7371891 was compared with "
              "ours pad for pad: identical at 0 degrees, so the reel's orientation is "
              "the CPL's angle unchanged. No diode, electrolytic or tantalum",
        "M3": "ground is a whole inner layer (In2) and the rail another (In1), each "
              "broken only by via clearances and the two M4 keep-outs. "
              + ("24 V arrives on a 0.30 mm track and returns through the ground plane "
                 "to J1's ground land, which has a via in it and a second 0.8 mm past "
                 "its toe. The rail leaves L1 on 1.0 mm of laid copper to both output "
                 "capacitors, four vias down, and crosses to the mid board on J11 with "
                 "three vias in the land; its return comes back on J12, three vias"
                 if key else
                 "The rail's 0.90 A arrives on J11 and returns on J12, each a 5.0 x 3.5 "
                 "land with THREE vias to its plane (it was one, the stitcher's)") +
              ". Each driver's ground is its pad's five vias",
        "M4": ("LMR33630 (SNVSAN3F 9.2.2.6 to 9.2.2.8). Input: 2 x 10 uF / 50 V 1206 on "
               "24 V (asked: 10 uF, rated twice the input if possible) and 100 nF / 50 V "
               "at each of the RNX package's two VIN/PGND pairs. Bootstrap 100 nF / 50 V "
               "(asked 100 nF, 10 V). VCC 1 uF / 25 V (asked 1 uF, 16 V). Output: TI's "
               "table for 12 V at 1.4 MHz is 4.7 uH and 4 x 10 uF; this rail has 2 x "
               "10 uF at the inductor, 2 x 10 uF where it lands on the mid board and "
               "eight 4.7 uF at the drivers, 77.6 uF by the markings, all 50 V parts at "
               "29 % of their rating. TI's equation 6 for all 1.38 A arriving as one "
               "step with a 2 % dip asks 6.1 uF. " if key else
               "no regulator here: the rail is made on the keyhead board. Where it "
               "lands, 2 x 10 uF / 50 V (C36, C37) and 100 nF stand beside the two "
               "supply pins for the joint's own inductance. ") +
              "Each driver: 1 uF on VREG (its sheet requires it), 100 nF on VCC and its "
              "own 4.7 uF / 50 V for the 0.18 A its twelve channels switch together",
        "M5": ("24 V bus: U10 36 V operating and 38 V absolute, capacitors 50 V, F1 "
               "63 V. " if key else "") +
              "The rail: 14.52 V, 14.0 to 15.0 with the 1.5 % reference and 1 % "
              "resistors, on drivers rated 17 V (18 absolute) at VCC and at every "
              "output, 50 V capacitors, and a spring pin whose catalogue line is 24 V. "
              "Logic: SCK and SDT are 3.3 V into inputs rated VREG + 0.6 V, VREG 3.1 to "
              "3.5 V" + ("; a live plug is M16, a dark board with live signals M18"
                         if key else ""),
        "M6": "no parallel bus and nothing matched. SCK and SDT are a 10 MHz-capable "
              "pair that the Pi clocks far slower; each driver re-drives both (10 ns "
              "edges) to the next, %s mm at the longest, which is %s ns of flight. They "
              "run over the unbroken rail plane or, on the back, against the ground "
              "plane" % (facts["hop_mm"], facts["hop_ns"]),
        "M7": ("divider: 100k over 7k68 || 200k = 7.396k on the 1.000 V reference is "
               "14.52 V. Inductor 4.7 uH: TI's table value at 1.4 MHz; their floor of "
               "0.28 x Vout / fsw is 2.9 uH against 3.76 at the part's -20 %; ripple "
               "0.87 A, 29 % of the 3 A they size it on. EN is tied to VIN on laid "
               "copper (TI: may go straight to VIN, must not float); PG is an open "
               "drain that 'can be left open when not used'. The RNX has no exposed "
               "pad. " if key else "") +
              "TLC5971: IREF 3k3 gives 41 x 1.21 V / 3.3k = 15.0 mA; its thermal pad is "
              "on GND",
        "M8": "nothing here has a reset, boot or address pin. A TLC5971 powers up with "
              "BLANK set, every output off, until a write that begins with command 25h. "
              "Its two inputs are driven, "
              + ("through R21 / R22, by Pi pins whose reset state is a pull-down (GPIO "
                 "9 to 27); with the lead off the board has no supply either" if key else
                 "by the keyhead board's last driver, which is on the same rail") +
              ". IREF has its resistor to ground" + ("; the buck's EN is tied" if key else ""),
        "M9": ("no MCU. Three bare 1.5 mm pads in the bay, each named in silk: +24V "
               "(after the fuse), +14V5 and GND. SCK and SDT can be probed at R21 / "
               "R22 and at the seam lands" if key else
               "no MCU. The rail and ground are the seam lands J11 and J12, 5.0 x 3.5 "
               "and named on the back; C36's pads are the same two nets from the "
               "front. SCK and SDT are J13 and J14"),
        "M10": ("decision: no TVS. J1 is inside the instrument, on a 4-way lead from the "
                "Pi cap that is plugged with the instrument off. Over-current: F1, 2 A "
                "fast, 63 V, ahead of everything. Reverse supply: the XH housing is "
                "keyed and its two supply ways are the XH bus's own order. The two "
                "signal ways have 1 k in series beside the socket (R21, R22), which is "
                "what an ESD strike or a foreign lead meets before a driver's input. "
                "The seam lands are only reachable with the panels apart and the "
                "instrument off" if key else
                "decision: no TVS and no fuse of its own. No cable reaches this board: "
                "its four lands meet the keyhead board's spring pins under the deck, "
                "and they can only be touched with the panels apart and the "
                "instrument off. Its supply is the keyhead board's buck, which limits "
                "at 3.85 to 5.05 A and hiccups into a short, behind that board's 2 A "
                "fuse"),
        "M11": "elec/cad_geom_check.py %s, 2026-10-05: every routed part is where the "
               "CAD draws it and the cut-outs match. check_walls (this file): no part's "
               "body under a wall of the light-cell comb. Two M4s through 4.5 mm "
               "unplated holes with a keep-out on every layer, the button heads on the "
               "back; the lip takes the -Y edge. %s"
               % ("fret_led_" + panel,
                  "J1's mouth is at the -X end, plugged last, before the endplate "
                  "(INSTALL_NOTES). Tallest part: J1 at 5.75 mm, then the inductor at 4.0"
                  if key else "Nothing is plugged into it"),
        "M15": ("U10 is internally compensated for ceramic outputs and TI give no ESR "
                "window, only the table's inductance and capacitance (M4). Capacitance "
                "under bias is NOT read off a curve: every part is at 29 % of its "
                "rating, and a tenth of the marked 77.6 uF still covers TI's equation "
                "6. No linear regulator: the buck is at 61 % duty against a 98 % "
                "maximum" if key else "no regulator on this board"),
        "M16": ("J1 is plugged with the instrument off, and 24 V then arrives through "
                "the output panel's switch at about 1.5 V/ms: no ring. Plugged live it "
                "would be a lead of about 0.5 uH into about 11 uF of biased ceramic, "
                "0.2 ohm characteristic, against 0.13 ohm in F1 alone (JDT's cold "
                "resistance) plus the lead and four contacts: close to critically "
                "damped, a few percent over 24 V. U10's 38 V is the lowest limit on "
                "the net" if key else
                "no cable. The rail arrives across the seam, which is made by sliding "
                "the keyhead panel home with the instrument off; it then rises with "
                "the buck's 4 ms soft start"),
        "M18": ("decision, and two resistors. The Pi can be up while this board is "
                "dark (F1 open, the motor board's lights fuse open, a Pi on USB power "
                "on the bench), and a TLC5971 input is rated to VREG + 0.6 V with "
                "VREG then 0. R21 and R22, 1 k at the socket, hold what the Pi can "
                "push through the input's protection diode to 2.7 mA. Nothing here "
                "drives back towards the Pi" if key else
                "one supply: this board's drivers are fed by the same rail, over the "
                "same joint, as the keyhead board's last driver that drives their "
                "inputs. Neither can be up without the other"),
        "M20": "no I2C and no CAN. SCK and SDT are terminated at their source: 68 ohm "
               "in series at the Pi cap. On the board each hop is from a driver with "
               "10 ns edges and a small fraction of the edge in flight (M6): lumped, "
               "nothing to terminate",
        "M21": "no ADC, DAC, codec or analog reference on the board",
        "M22": "no op-amp or comparator on the board",
        "M25": "TLC5971 (RGE): the pad is on GND, as TI name it, solid, with five vias "
               "(the centre and four on the axes between the paste panes; TI draw "
               "nine) and paste in four panes. At full white a driver burns 0.68 W "
               "typical and 0.86 W worst (12 x 15 mA across the rail less four LEDs, "
               "plus its own supply current); at TI's 38 C/W for this package that is "
               "26 to 33 C over ambient, 78 C at 45 C against 150 C -- and at the "
               "68.6 of the HTSSOP it replaced, on fewer vias than TI draw, still "
               "104 C. " + (
               "U10 has no pad: its heat leaves through the pins into the laid slabs, "
               "a second ground band front and back, and nine more vias. Loss, off "
               "TI's 24 V curve for this package at 1.4 MHz (figure 9-15) at 1.4 A: "
               "1.1 W, all of it charged to the IC. Thermal resistance is an "
               "ESTIMATE, 57 C/W: TI's 23.5 junction to board, then this board's "
               "copper; their figure 9-4 gives 50 to 63 for the package on four "
               "layers of heavier copper. 45 C ambient (under the deck, over the "
               "motors) + 1.1 x 57 = 107 C against 125 C operating, 165 C shutdown. "
               "That is every fret at full white, which the firmware's lights cap "
               "does NOT prevent (this board alone at full is 0.93 A of the 1.07 A "
               "cap). The 2.1 MHz part it had loses 1.45 W, 127 C: that is why it "
               "was changed (elec/buck_cell.py)" if key else "No regulator and no "
               "tab on this board"),
        "M26": "one link, a daisy chain. Read off TI's pin table (RGE): 1 SDTI, 2 SCKI, "
               "11 SCKO, 12 SDTO. " + ("SDT_IN and SCK_IN (from the cable through R22 "
               "/ R21) reach U1 pins 1 and 2; each driver's 6 and 5 go to the next "
               "one's 1 and 2; U3's leave as SDT_SEAM / SCK_SEAM on J14 / J13. At the "
               "Pi the two are an SPI's MOSI and SCLK" if key else "SDT_SEAM and "
               "SCK_SEAM (J14, J13) reach U1 pins 1 and 2; each driver's 6 and 5 "
               "go to the next one's 1 and 2; U5's are the end of the chain"),
        "M27": "no strap, reset or debug net on the board",
        "M28": "no transistor or small regulator. Each IC's pin order is read from its "
               "own sheet (pinouts, above). Compared pad for pad with the fab's "
               "library footprint for the LCSC code: XL-5050RGBW C7371891" + (
               ", LMR33630BRNXR C2071384 (and the alternate C part's, C2071783: the "
               "same frame), S4B-XH-SM4-TB C161861" if key else "") + " -- matching under "
               "a pure rotation. TLC5971RGER C543004 (land: KiCad's Texas_RGE0024H, "
               "TI's own drawing for the package) was not laid pad on pad; it was "
               "SEEN in the fab's placement preview on this board, 2026-10-06: body "
               "centred on its lands, the fab's pin-1 dot on the board's pin-1 mark, "
               "at the angle KiCad wrote",
        "M29": "four layers, 1.6 mm, 1 oz outside and 0.5 oz inside: JLCPCB's standard "
               "table, read 2026-10-04 (A12 measured against it). 211 x 70.4 mm plus "
               "the ear is inside the size limits. Every 0402's plane-side pad reaches "
               "its plane through a via beside the pad on a short track, as the other "
               "pad has: no pad sits in a pour",
        "M30": "JLCPCB's assembly page, read 2026-10-05: Economic PCBA takes "
               "single-sided assembly on 2, 4 or 6 layers at 1.6 mm, a single board "
               "from 10 x 10 to 470 x 500 mm, parts from 0402 and IC pitch from 0.4 mm; "
               "Standard starts at 70 x 70, which this board (70.4 wide) also clears. "
               "Finest pitch here " + ("0.5 mm (U10)" if key else "0.65 mm (the "
               "drivers)") + ". Every part is in the assembly library; the extended "
               "ones are the LED, the driver, the spring pin, the 4.7 uF / 50 V" + (
               ", the buck, the inductor, the fuse, the socket and the 7k68" if key
               else ""),
        "M31": "'FRET LED %s r1' on the front. " % panel.upper() + (
               "The three test pads are named (+24V, +14V5, GND). J1's four ways are "
               "named on the back: 1 GND, 2 +24V_IN, 3 SCK_CABLE, 4 SDT_CABLE. "
               if key else "") + "Each seam land is named on the back with its net. "
               "All text 1.0 mm or more with a 0.15 stroke (A12). Pin-1 and LED "
               "polarity marks are the footprints', outside the bodies. The legend is "
               "cut back from every mask opening: the gerber carries the pads in "
               "clear polarity",
        "M32": ("J1: lands 2.50 mm apart measured on the footprint, which is XH (PH is "
                "2.00); 3 A a contact against 0.93 A; pad 1 per JST's drawing. " if key
                else "") + "The spring pins are not a pitch series: single lands, 12 A "
               "each against 0.90 A on the rail pin and on the ground pin",
        "M33": ("the rail, both boards: 92 channels x 15 mA = 1.38 A, plus eight "
                "drivers at no more than 22 mA (TI's maximum at twice this current "
                "setting, with data clocking), 1.56 A of a 3 A regulator: 52 %. 1.38 A is what is declared "
                "on +14V5. The 24 V side at 90 %: 0.93 A, through J1's 3 A contact and "
                "the 2 A fuse" if key else
                "this board's share of the keyhead board's rail: %d channels x 15 mA "
                "= %.2f A, plus five drivers at no more than 22 mA. It arrives on one "
                "12 A spring pin and returns on another; the regulator's budget is "
                "the keyhead board's M33 (52 %% of 3 A for both boards)"
                % (n_ch, n_ch * 0.015)),
        "M34": "SCK and SDT: a 3.3 V output into an input that wants 0.7 x VREG, "
               "2.45 V at VREG's 3.5 V maximum, with 0.2 x VREG of hysteresis -- the "
               "Pi's at the head of the chain, a VREG-level output between drivers. "
               "The protocol has no chip select and no enable" + (
               ". U10's EN is active high, 1.23 V threshold, tied to VIN as its sheet "
               "allows" if key else ""),
        "M35": "TI's product page for TLC5971, read 2026-10-06" + (
               ", and for LMR33630, read 2026-10-05" if key else "") +
               ": active, no errata document listed",
        "M36": ("the rail is offered to the mid board at the seam. It is U10's output: "
                "limited at 3.85 to 5.05 A, hiccup into a short, and behind F1 (2 A) "
                "on the 24 V side. 24 V itself does not leave the board" if key else
                "no supply leaves this board"),
        "M38": ("decision, stated at the cell: the four 1206s lie along the board's "
                "length, within 10 mm of its -X end, on a 211 x 70 board held by two "
                "M4s and a lip -- not a strip that bends. The 0805s are in the "
                "drivers' rows, 20 mm and more from any edge. " if key else
                "C36 and C37 (1206) are 3.3 mm from the seam edge and lie along the "
                "board's length; the board is 211 x 70, held by two M4s and a lip, and "
                "is ordered as a routed single with no V-score or tab. The 0805s are "
                "13 mm and more from any edge. ") +
               "Both M4 holes are unplated and isolated, with no copper under the "
               "button head. " + ("J1's plug goes on from the open -X end; the test "
               "pads are 1.5 mm, 9 mm apart" if key else "Nothing is plugged in"),
        "M39": "no unused input. " + ("Four of the 36 outputs are unused (eight zones "
               "of four on three drivers): constant-current sinks, left open, which "
               "need no load. U10's PG is an open drain left open, as its sheet "
               "allows" if key else "All 60 outputs are used. U5's SCKO and SDTO are "
               "the end of the chain: push-pull outputs, left open"),
        "M40": "3k3" + (", 7k68 (an E96 value), 100k, 200k, 1k" if key else "") +
               ", 100 nF, 1 uF, 4.7 uF and 10 uF are stock values, and every "
               "capacitor's voltage is in its value. Do-not-substitute parts say so "
               "where they are defined: " + ("L1 and U10 (elec/buck_cell.py: "
               "saturation, and heat), F1 (a part number: speed and 63 V), " if key
               else "") + "the 4.7 uF, which must be the 50 V part on this rail, and "
               "the LED, whose 3.0 to 3.4 V sets the rail",
        "M42": "JLCPCB stock on 2026-10-05: LED 40,185, driver 3,826, spring pin 594, "
               "4.7 uF / 50 V 343 k" + (", buck LMR33630BRNXR 260 (THIN: the "
               "alternate is the 2.1 MHz LMR33630CRNXR, 3,453, on the same land with "
               "no other change, and then full white is capped in firmware -- "
               "elec/buck_cell.py), inductor C48496 8,632, fuse 11 k, socket 20,309" if
               key else "") + "; the other passives are basic parts. TI parts active. "
               "Single-maker parts: the spring pin (Xinyangze, no second source on "
               "this land: the thin one, eight a pair of boards) and the LED (other "
               "5050 RGBW parts exist but their pad order must be read first)",
    }
    if key:
        m["M13"] = ("measured on the routed board, pad edge to pad edge, against TI's RNX "
                    "layout: C32 and C35 %s mm from VIN and from PGND at their own pair, "
                    "on the part's layer, on laid copper with no via in either loop; the "
                    "bulk pair on the same slabs. The switch node is a laid 0.5 mm "
                    "track, %s mm from the pin to the inductor's land, no via, no pour. "
                    "The feedback parts are on the opposite side of the package from "
                    "it: R11 %s mm and R10 %s mm from FB, R12 on R11, none of it under "
                    "the inductor. Bootstrap %s mm from BOOT. VCC's capacitor %s mm "
                    "from its pin, its ground pad on the track from AGND"
                    % (facts["cin"], facts["sw"], facts["r11"], facts["r10"],
                       facts["boot"], facts["vcc"]))
        m["M14"] = ("L1 SWPA5040S4R7MT, 4.7 uH +-20 %. Ripple 14.52 x (1 - 14.52/24) / "
                    "(4.7 uH x 1.4 MHz) = 0.87 A, so the peak at both boards' 1.38 A is "
                    "1.82 A. Saturation (Sunlord: 30 % inductance drop, 20 C) 3.50 A "
                    "guaranteed, 3.90 typical; heating current 3.0 A. TI: saturation "
                    "'must not be less than the device low-side current limit', 3.5 A "
                    "typical (2.9 to 4.1) -- met at the guarantee, with nothing over. "
                    "The high-side limit is 4.5 A typical, above this part: accepted. "
                    "A dead short on the rail pulls FB under 0.4 V and the part "
                    "hiccups at 94 ms. The 4 x 4 part this replaced saturated at 2.90 A")
        m["M37"] = facts["m37"]
    else:
        m["M37"] = facts["m37"]
    return {k: v for k, v in m.items() if v}


# What was measured on the routed boards after the last route (scratch scripts in the
# session; the figures are re-read whenever a board is re-routed).
MEASURED = {
    "key": {"hop_mm": "82", "hop_ns": "0.5", "cin": "0.60", "sw": "4.4",
            "r11": "1.17", "r10": "2.35", "boot": "1.07", "vcc": "0.42",
            "m37": (
                "elec/fab.py fret_led_key, 2026-10-06, run after finish.py's refill and DRC; "
                "gerbers and drill written together. Opened outside KiCad: every layer "
                "rendered with pygerber 2.4.3 and looked at, the Excellon file parsed "
                "separately and laid over the copper -- all 366 plated holes have copper all "
                "round them on both outer layers. Paste only on soldered lands; stack-up and "
                "the via choice are in ORDER.txt")},
    "mid": {"hop_mm": "51", "hop_ns": "0.3", "m37": (
                "elec/fab.py fret_led_mid, 2026-10-06, run after finish.py's refill and DRC; "
                "gerbers and drill written together. Opened outside KiCad: every layer "
                "rendered with pygerber 2.4.3 and looked at, the Excellon file parsed "
                "separately and laid over the copper -- all 601 plated holes have copper all "
                "round them on both outer layers. Paste only on soldered lands; stack-up and "
                "the via choice are in ORDER.txt")},
}

def build(panel):
    """One board: its netlist and its board.json."""
    name = FL.BOARD_NAME[panel]
    skidl.reset()
    x_lo, x_hi = FL.panel_range(panel)
    zs = zones_for(x_lo, x_hi)
    assert zs, "%s: fret_light gives this panel no lit frets" % name
    n_drv = (len(zs) + 2) // 3
    xs = [x for _n, x in zs]
    bnd = FL._boundaries(xs, x_lo, x_hi)
    x0, x1 = FL.board_span(panel)
    cx = FL.board_cx(panel)
    length = x1 - x0

    gnd, v24, vrail = Net("GND"), Net("+24V"), Net("+14V5")
    for n in (gnd, v24, vrail):
        n.drive = Pin.drives.POWER
    place, fps = {}, {}
    seam = {"+14V5": vrail, "GND": gnd,
            "SCK_SEAM": Net("SCK_SEAM"), "SDT_SEAM": Net("SDT_SEAM")}
    if panel == HARNESS:
        sck, sdt = _supply(place, fps, gnd, v24, vrail, x0, min(bnd), cx)
    else:
        # the chain comes in over the seam, from the harness board's last driver
        sck, sdt = seam["SCK_SEAM"], seam["SDT_SEAM"]
        _arrival(place, fps, gnd, vrail, x0, cx)
    del seam_vias[:]
    _seam(panel, place, fps, cx, seam)

    drivers = []
    for k in range(n_drv):
        trio = zs[3 * k:3 * k + 3]
        # ⚠ THE DRIVER SITS ON A FRET CENTRE, AND ON THE -X ONE WHEN THE TRIO IS SHORT.
        # It is the middle zone of a full three; the keyhead board's 8 zones leave a trio
        # of TWO, and "the middle of two" is trio[1], the +X one -- which on that board is
        # fret 9, 3.68 mm from the board's own +X edge. layout.py refused it outright:
        # "no room for a stitching via beside U3.19". Taking trio[0] instead puts the
        # driver a whole fret pitch further in, with its two zones at side 0 and +1.
        # ⚠ AND NOT THE MIDPOINT OF THE TWO, which is the obvious alternative and is
        # exactly where a comb wall stands: every boundary between two frets carries one.
        di = 1 if len(trio) == 3 else 0
        xd = trio[di][1] - cx
        u = Part(name="TLC5971", ref_prefix="U", ref="U%d" % (k + 1), tag="U%d" % (k + 1),
                 dest="NETLIST", tool="skidl", value="TLC5971RGER",
                 description="12-ch 16-bit constant-current LED driver (LCSC C543004)",
                 footprint=DRV_FP, pins=[Pin(num=n, func=P) for n in range(1, 26)])
        iref, vreg = Net("IREF%d" % (k + 1)), Net("VREG%d" % (k + 1))
        u[16] += iref
        gnd += u[18], u[25]
        vrail += u[13]
        vreg += u[15]
        sdt += u[1]
        sck += u[2]
        for n in (3, 4, 14, 17):          # no internal connection (SBVS146D, pin functions)
            Net("U%d_P%d_NC" % (k + 1, n)).connect(u[n])
        # the LAST driver's re-buffered outputs: on the harness board they ARE the
        # chain's way across the seam; on the other they go nowhere, and the names say
        # NC rather than leaving netcheck to find a pin wired to nothing.
        if k < n_drv - 1:
            sck, sdt = Net("SCK_%d" % (k + 1)), Net("SDT_%d" % (k + 1))
        elif panel == HARNESS:
            sck, sdt = seam["SCK_SEAM"], seam["SDT_SEAM"]
        else:
            sck, sdt = Net("SCKO_CHAIN_END_NC"), Net("SDTO_CHAIN_END_NC")
        sck += u[5]
        sdt += u[6]
        r = _r("R%d" % (k + 1), R_IREF, "U%d IREF -- 15.0 mA per channel" % (k + 1))
        iref += r[1]
        gnd += r[2]
        cv = _c("C%d" % (k + 1), "1uF/25V", "U%d VREG (datasheet: 1 uF required)" % (k + 1))
        vreg += cv[1]
        gnd += cv[2]
        cc = _c("C%d" % (10 + k + 1), "100nF/50V", "U%d VCC bypass" % (k + 1))
        vrail += cc[1]
        gnd += cc[2]
        # ⚠ LOCAL BULK AT EVERY DRIVER, and it is item 4 of the noise plan, not tidiness.
        # Without it each zone's PWM current is drawn down the full-length rail and the
        # supply loop becomes the whole board, which undoes the plane.
        # 50 V: twice the rail and more (M4). The 25 V part this was keeps about a
        # third of its marking at 14.5 V of bias.
        cb = _c("C%d" % (20 + k + 1), "4.7uF/50V", "U%d local bulk -- its zones' PWM "
                "current must come from here, not from the far end of the rail" % (k + 1),
                C08_FP)
        vrail += cb[1]
        gnd += cb[2]
        # ⚠ THE PASSIVES STACK IN Y, NOT IN X, and that is the fret pitch's doing. They
        # were in a row at xd -4.8 .. +5.0, which is fine at the nut end and 0.05 mm
        # INSIDE the comb's wall at the bridge end (see check_walls). Everything now
        # sits within 2.7 mm of its driver's fret centre, against the 3.77 the tightest
        # gap allows, in two rows clear of the driver's own courtyard.
        place["U%d" % (k + 1)] = (xd, DRV_Y, DRV_ROT)
        fps["U%d" % (k + 1)] = DRV_FP
        # ⚠ THE THREE SMALL ONES STAND AT THE SUPPLY SIDE, +Y, each over the pin it serves
        # (manual quality pass, 2026-10-05): IREF 16, VREG 15 and VCC 13 are all on that
        # side, with each part's pin-side pad turned toward its pin. TI ask for the
        # reference resistor "close to the device", and VREG is a regulator output. The
        # bulk capacitor, which serves the LED strings through the planes and not a
        # pin, takes the far side alone.
        for ref, dx, dy, rot, fp in (("R%d" % (k + 1), -2.30, 3.75, 180.0, R_FP),
                                     ("C%d" % (k + 1), 0.00, 3.75, 180.0, C_FP),
                                     ("C%d" % (10 + k + 1), 2.30, 3.75, 0.0, C_FP),
                                     ("C%d" % (20 + k + 1), 0.00, -5.20, 0.0, C08_FP)):
            place[ref] = (xd + dx, DRV_Y + dy, rot)
            fps[ref] = fp
        drivers.append((u, xd, trio, di))

    # ⚠ EACH DRIVER'S OWN di. This loop read the one left over from the loop above -- the
    # LAST driver's -- and on the keyhead board that driver has the short trio, so every
    # full trio there was keyed as (0, +1, +1): two frets on the same four outputs and
    # four outputs idle. Frets 3 + 4 and 6 + 7 were one zone each, 24 return nets where
    # 32 were meant, on a board that routed clean and passed every check (found
    # 2026-10-06). `used` below is the check that would have caught it.
    for k, (u, xd, trio, di) in enumerate(drivers):
        used = [p for s in range(len(trio))
                for p in ZONE_OUTS[max(-1, min(1, s - di))]]
        assert len(set(used)) == 4 * len(trio), (
            "%s U%d: its %d zones share driver outputs %s" % (name, k + 1, len(trio), used))
        for s, (fret, xf) in enumerate(trio):
            zi = 3 * k + s
            side = s - di
            side = -1 if side < 0 else (1 if side > 0 else 0)
            rot = ROT_TOWARD_DRIVER[side]
            outs = ZONE_OUTS[side]
            leds = []
            for j, y in enumerate(LED_ROW):
                ref = "D%d" % (4 * zi + j + 1)
                d = Part(name="LED_RGBW", ref_prefix="D", ref=ref, tag=ref,
                         dest="NETLIST", tool="skidl", value=LED_MPN,
                         description="fret %d RGBW LED at y %+.2f (LCSC C7371891)"
                                     % (fret, y), footprint=LED_FP,
                         pins=[Pin(num=i, func=P) for i in range(1, 9)])
                place[ref] = (xf - cx, y, rot)
                fps[ref] = LED_FP
                leds.append(d)
            # the series string, -Y to +Y: rail on the -Y outer LED's anodes, driver on
            # the +Y outer LED's cathodes, three links in between.
            for i, col in enumerate(COLOURS):
                vrail += leds[0][i + 1]
                for a, b in ((0, 1), (1, 2), (2, 3)):
                    Net("Z%d_%s_%d" % (fret, col, a)).connect(leds[a][i + 5],
                                                              leds[b][i + 1])
                Net("Z%d_%s_RET" % (fret, col)).connect(leds[3][i + 5], u[outs[i]])

    # ⚠ BEFORE THE NETLIST, NOT AFTER THE ROUTE. See check_placement.
    # the buck's cell is laid out to TI's figure, closer than the lane-keeping gap this
    # check enforces; real courtyard overlaps are still DRC's to refuse
    cell = ["U10"] + sorted(CELL_REFS.values()) + sorted(CELL_BULK)
    exempt = ([(a, b) for i, a in enumerate(cell) for b in cell[i + 1:]]
              if panel == HARNESS else [])
    check_placement(name, place, fps, exempt=exempt)
    check_walls(name, place, fps, bnd, min(bnd), cx)
    ERC()
    net = os.path.join(OUT_DIR, "%s.net" % name)
    generate_netlist(file_=net)
    netcheck.grounds_meet(net)
    netcheck.no_orphan_pins(net)

    notes = dict(BOARD_NOTES)
    notes["outline_mm"] = (round(length, 3), BOARD_W)
    notes["placements"] = {k: list(v) for k, v in place.items()}
    # ⚠ TWO M4s, BOTH ON THE +Y SIDE, opposite the tilt-in lip (fret_light.m4_xys): one in
    # the BAY at the -X end, and one on an EAR off the +Y edge at the +X end, outside the
    # lit line -- so neither keepout takes anything off a cell's floor and neither boss
    # stands in a cell. Both positions are READ from the deck, not retyped.
    # head_d: the M4's button head bears on the UNDERSIDE (fret_light.m4_joint), so no
    # copper runs under it on that face
    from cadkit.fasteners import M4_BUTTON_HEAD_D
    notes["cutouts"] = [{"xy": [round(wx - cx, 4), round(wy, 4)], "d": 4.50,
                         "head_d": M4_BUTTON_HEAD_D, "head_side": "back"}
                        for wx, wy in FL.m4_xys(panel)]
    # the rectangle, plus the ear. outline_mm above stays the LAYOUT REGION.
    hl, hw = length / 2.0, BOARD_W / 2.0
    ex0, ex1, ey = FL.ear_span(panel)
    assert abs((ex1 - cx) - hl) < 1e-6, (ex1 - cx, hl)
    notes["outline_poly"] = [[round(v, 4) for v in pt] for pt in (
        (-hl, -hw), (hl, -hw), (hl, ey), (ex0 - cx, ey), (ex0 - cx, hw), (-hl, hw))]
    notes["qty_per_instrument"] = 1
    # each driver's heat pad gets its four more vias (DRV_PAD_VIAS)
    notes["vias"] = list(notes.get("vias", [])) + [
        ("GND", round(xd + dx, 3), round(DRV_Y + dy, 3))
        for _u, xd, _trio, _di in drivers for dx, dy in DRV_PAD_VIAS] + list(seam_vias)
    # ⚠ IREF IS LAID, NOT ROUTED: 3 mm from pin 16 to its resistor. Left to the router it
    # was the one net unrouted at EVERY driver, because the stitcher runs first and stood
    # the VREG capacitor's ground via in the only gap the track had (2026-10-06).
    notes["tracks"] = list(notes.get("tracks", [])) + [
        ("IREF%d" % (k + 1), "F.Cu", 0.25,
         [(round(xd + dx, 3), round(DRV_Y + dy, 3))
          for dx, dy in ((-0.25, 1.96), (-0.25, 2.75), (-1.79, 2.75), (-1.79, 3.75))])
        for k, (_u, xd, _trio, _di) in enumerate(drivers)]
    if panel == HARNESS:
        # ...and the socket's ground way, which is the whole instrument's fret-light return
        _trk, _via = BC.xh_ground_via(*place["J1"][:2])
        notes["tracks"] = list(notes.get("tracks", [])) + [_trk]
        notes["vias"] = notes["vias"] + [_via]
    # WHAT EACH SUPPLY NET CARRIES, all-white. The 14 V rail is made on the key board and
    # crosses the seam pogos to the mid board, so the key board's rail is held to BOTH
    # boards' channels and the mid board's to its own.
    i_own = 4 * len(zs) * I_CHAN
    rail_j = ["J%d" % (11 + i) for i, (_x, _y, _net) in enumerate(FL.pogo_pads(panel))
              if _net == "+14V5"]            # the seam pogo(s) the rail crosses on
    i_all = 4 * I_CHAN * sum(len(zones_for(*FL.panel_range(q))) for q in ("mid", "key"))
    if panel == "key":
        i_24 = i_all * V_RAIL / 24.0 / 0.90
        paths = [
            {"net": "+24V_IN", "from": "J1.2", "to": "F1.1", "amps": round(i_24, 3)},
            {"net": "+24V", "from": "F1.2", "to": "U10.2", "amps": round(i_24, 3)},
            # the rail: out of the inductor, onto the plane, across the seam pogos. Held
            # to the WHOLE rail rather than the mid board's share, because the stretch
            # that matters is L1's own exit and all of it leaves there. A driver's VCC is
            # only its logic supply (the LED current enters at the anodes, off the plane).
            {"net": "+14V5", "from": "L1.2", "to": [r + ".1" for r in rail_j],
             "amps": round(i_all, 3)},
            {"net": "+14V5", "from": "L1.2",
             "to": ["U%d.13" % (k + 1) for k in range(n_drv)], "amps": I_VCC},
        ]
        pin = {"S4B-XH-SM4-TB": "JST XH S4B-XH-SM4-TB drawing for pin 1; the way order is "
                                "J_PINS in _supply(), the Pi cap's end to match",
            BC.U_VALUE: "TI LMR33630 datasheet SNVSAN3F, Table 6-1, VQFN (RNX) column",
        }
        # ⚠ NO SECOND BARREL IN THE INDUCTOR'S LAND, which this board once declared. The
        # 5 x 5 part's land is 1.4 x 4.2 and the stitcher puts its own via IN it; a second
        # open barrel there holds 0.23 of the land's 0.71 mm3 of paste, over the quarter
        # cadkit quality A12 allows. All 1.38 A still has more than one way down:
        # buck_cell lays 1.0 mm of copper from this land to both output capacitors, each
        # with its own via, and A1 measures the path.
        notes["vias"] = list(notes.get("vias", []))
        # the switch node and the two input loops are laid, not routed (buck_cell.tracks)
        notes["tracks"] = list(notes.get("tracks", [])) + BC.copper(
            *cell_org, v_out="+14V5") + BC.heat_copper(*cell_org)
        # ⚠ THE 24 V FEED FROM THE FUSE IS LAID, 0.5 mm. F1 stands on the far side of J1
        # from the cell, and the way between them is the 2.6 mm of board under the
        # socket's body, between its four lands and its two mounting lands. The router
        # left this net for last and its repair closed it with 24 mm of 0.20 track,
        # which is 0.93 A on copper sized for 0.7. Along the cell's own input slab's
        # line, so it arrives end-on.
        _fx = CELL_Y - place["F1"][1]              # the fuse, in the cell's frame: -29.8
        notes["tracks"] += [("+24V", "F.Cu", 0.50, [
            BC.at(*cell_org, dx=_fx, dy=-1.40)[:2],
            BC.at(*cell_org, dx=_fx + 1.30, dy=-1.40)[:2],
            BC.at(*cell_org, dx=_fx + 2.85, dy=0.15)[:2],
            BC.at(*cell_org, dx=BC.BULK["CIN_2"][0], dy=0.15)[:2]])]
        notes["vias"] = notes["vias"] + BC.vias(*cell_org) + BC.heat_vias(*cell_org)
        notes["stitch_exceptions"] = BC.STITCH_EXCEPTIONS
        waive = {
            "A2:J1": "the harness plug, ahead of the fuse; the input capacitors C30-C32 "
                     "are on the fused side so a shorted one blows F1",
        }
        for _rj in rail_j:
            waive["A2:" + _rj] = ("a seam pogo handing the rail to the mid board, not a "
                                 "load; the rail is a plane with C36-C38 on it")
    else:
        # the rail arrives on a pogo land that is stitched straight to the plane; what
        # leaves the plane by a track is a driver's logic supply
        paths = [{"net": "+14V5", "from": rail_j[0] + ".1",
                  "to": ["U%d.13" % (k + 1) for k in range(n_drv)], "amps": I_VCC}]
        pin, waive = {}, {}
    notes["quality"] = {
        "power_paths": paths,
        "pinouts": dict({
            "XL-5050RGBW": "XINGLIGHT XL-5050RGBW datasheet, package drawing: pads 1-4 the "
                           "four anodes, 5-8 their cathodes; Steel:XINGLIGHT_XL-5050RGBW "
                           "is drawn from it",
            "TLC5971RGER": "TI TLC5971 datasheet SBVS146D, Pin Functions table, RGE "
                           "(VQFN-24) column",
        }, **pin),
        "waive": waive,
        "manual": _manual(panel, n_drv, len(zs), MEASURED[panel]),
        # WHAT THE DESIGN MEANS, for cadkit quality A13 to hold the routed board to:
        # written from the counts (drivers, frets, four LEDs a string), not read off it.
        "unconnected": _unconnected(panel, n_drv, len(zs)),
        "net_groups": [
            {"name": "driver outputs in use: four a fret, every one on its own return",
             "pins": ["U%d.%d" % (k + 1, p) for k in range(n_drv) for p in DRV_OUT_PINS
                      if not (k == n_drv - 1 and p in _idle_outs(n_drv, len(zs)))],
             "nets": 4 * len(zs), "each": 1, "pins_count": 4 * len(zs)},
            {"name": "string returns: one a colour a fret, last cathode to a driver output",
             "nets_like": "Z[0-9]+_[RGBW]_RET", "count": 4 * len(zs), "pads": 2},
            {"name": "string links: three a string of four LEDs, a colour a fret",
             "nets_like": "Z[0-9]+_[RGBW]_[0-9]+", "count": 4 * len(zs) * 3, "pads": 2},
            {"name": "each driver's own IREF and VREG",
             "pins": ["U[1-%d].1[56]" % n_drv], "nets": 2 * n_drv, "each": 1},
            {"name": "the chain between drivers: SCK and SDT, driver to driver",
             "nets_like": "S(CK|DT)_[0-9]+", "count": 2 * (n_drv - 1), "pads": 2},
            {"name": "the seam: four pins, four ways",
             "pins": ["J1[1-4].1"], "nets": 4, "each": 1, "pins_count": 4},
        ] + ([{"name": "the cable socket: four ways", "pins": ["J1.[1-4]"],
               "nets": 4, "each": 1}] if panel == HARNESS else []),
    }
    notes["world_x"] = [round(x0, 3), round(x1, 3)]
    notes["board_frame"] = {"cx": round(cx, 4), "z_bot": FL.BOARD_BOT}
    with open(os.path.join(OUT_DIR, "%s.board.json" % name), "w") as f:
        json.dump(notes, f, indent=2)
    print("%-13s %6.1f x %.1f mm, frets %d..%d, %d zones, %d LEDs, %d drivers"
          % (name, length, BOARD_W, zs[-1][0], zs[0][0], len(zs), 4 * len(zs), n_drv))
    return len(zs), n_drv


# ── the board ────────────────────────────────────────────────────────────────────────
BOARD_NOTES = {
    "layers": 4,
    "thickness_mm": 1.6,
    # ⚠ +14V5 ON In1, GND ON In2 -- AND THAT INVERTS docs/fret-led.md 6.3, ON PURPOSE.
    # That section says "GND plane directly under the LED layer", having assumed the
    # LED loop's return conductor is ground. It is not. A zone's switched current runs
    # local bulk -> +14V5 -> four LEDs in series along 60 mm of fret -> the driver's
    # output pin -> through the chip to its GND pad -> back to the cap, and the cap sits
    # AT the driver. So the conductor that mirrors the long F.Cu run is the RAIL, and
    # the loop is the area between the chain and the rail plane beneath it:
    #     In1 = +14V5   0.21 mm under F.Cu    ~15 mm2      (this board)
    #     In2 = +14V5   1.28 mm under F.Cu    ~90 mm2
    # Six times smaller, for a swap that costs nothing. GND is still a solid plane one
    # layer down, which is all the SPI chain (a few MHz) asks for, and the two planes
    # face each other across 1.065 mm of core, which is free interplane decoupling.
    "zones": [("+14V5", "In1.Cu", 0.3), ("GND", "In2.Cu", 0.3)],
    # ⚠ BOTH INNERS ARE PLANES AND THE ROUTER HAS TO BE TOLD. A zone is just copper to
    # freerouting: pour and say nothing and it routes signals straight through the
    # reference, which splits the return path of every trace that crosses it -- here
    # that would be the rail under the LED strings, i.e. the one thing this stackup
    # exists for. (Found on the optical board; see the note in elec/lever_sensor.py.)
    "plane_layers": ("In1.Cu", "In2.Cu"),
    # ...which leaves F.Cu and B.Cu to route on, and B.Cu is empty of parts, so it is
    # where anything that cannot make it across the LED rows on the top goes.
    "local_inner": "B.Cu",
    # A plane needs stitching to it, or nothing connects the pads. Every anode on the
    # rail and every GND pad gets its own via down.
    "stitch_nets": ("+14V5", "GND"),
    "single_sided": True,      # every part on the face that fires into the cells
    "refs_on_fab": True,       # 92 LEDs: silkscreen refs would be ink over copper
    "no_mounting_holes": True,  # the hole is declared per board, in the bay
    "router_passes": 20,
    # THE RAILS' OWN WIDTHS, from the currents in build()'s quality block (IPC-2221, 1 oz,
    # 10 C): 0.93 A of 24 V wants 0.27 and was routed at 0.19-0.25; the 14 V rail's whole
    # 1.38 A left L1 on ONE 0.25 track and wants 0.47. The plane carries the rail the
    # length of the board -- these are the stubs that reach it.
    "net_widths": {"+24V_IN": 0.30, "+24V": 0.30, "+14V5": 0.50},
}


if __name__ == "__main__":
    tot_z = tot_d = 0
    for panel in ("mid", "key"):
        z, d = build(panel)
        tot_z += z
        tot_d += d
    print("%d zones, %d channels, %d drivers, %.2f A at %.2f V all-white"
          % (tot_z, 4 * tot_z, tot_d, 4 * tot_z * I_CHAN, V_RAIL))
