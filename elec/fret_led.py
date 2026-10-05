"""FRET LIGHTING boards -- one RGBW zone per fret, four LEDs per zone. x2.

    py -3.12 elec/fret_led.py     # -> elec/out/fret_led_{mid,key}.{net,board.json}

TWO BOARDS FROM ONE MODULE, because there are two deck panels and each board has to
come off with its own panel:

    fret_led_mid   frets 24..10   15 zones   60 channels   5 x TLC59711   210.3 x 70.4
    fret_led_key   frets  9.. 2    8 zones   32 channels   3 x TLC59711   211.8 x 70.4

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
follows FRETS (24) rather than LEDs (92). A TLC59711 carries 3 RGBW zones, so zones
come in threes and both boards land on a whole number of drivers with nothing wasted.

ONE CHAIN ACROSS TWO BOARDS, JOINED AT THE PANEL SEAM BY FOUR TIP-TO-TIP POGOS
(docs/fret-led.md 9.1f). The keyhead board carries the harness plug, the fuse and the
24 V -> 14.5 V buck for BOTH; the seam carries +14V5, GND and the TLC59711 chain out of
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
DRV_FP = "Package_SO:HTSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3.4x6.5mm_Mask2.75x3.43mm"
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

# IREF sets every channel's ceiling: I = 41 x 1.21 / R (TLC59711 datasheet). 3k3 =
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
# top-of-bin string, where the sink needs about 0.3 V at 15 mA to stay flat (TI SBVS181A
# figure 12).
#
# 14.52 V: R10 over (R11 parallel R12) on the LMR33630's 1.000 V reference, 100k over
# (7k68 || 200k). The rail's own low limit is then 14.04 V, 0.44 V over the worst string
# -- and the sheet's 3.4 V is at 20 mA, where these run at 15.
# ⚠ AND NOT HIGHER, BECAUSE EVERY EXTRA VOLT IS HEAT IN THE DRIVER. One shared rail means
# red drops the difference:
#     red     (14.52 - 4 x 2.1) x 15 mA = 92 mW per channel, typical dice
#     W/G/B   (14.52 - 4 x 3.1) x 15 mA = 32 mW per channel
#     per TLC59711, 3 zones x (92 + 3 x 32) = 0.56 W, plus about 0.12 W of its own supply
#     current at 14.5 V: 0.68 W typical, 0.86 W with every die at the bottom of its bin
# At 68.6 C/W (SBVS181A thermal table) that is 47 to 59 C over the air under the deck,
# with every fret at full white: 99 C at the junction in 40 C air, against 125 operating
# and 150 shutdown. 15.0 V would have matched the foot strip's 0.9 V of worst-case
# headroom and cost another 7 C here. Red also wants trimming down for colour balance,
# which takes its share off again (docs/fret-led.md 6.2).
R_FBT, R_FBB, R_FBP = 100e3, 7.68e3, 200e3
V_RAIL = round(1.0 * (1.0 + R_FBT / (R_FBB * R_FBP / (R_FBB + R_FBP))), 2)      # 14.52
assert abs(V_RAIL - 14.52) < 0.005, V_RAIL
I_CHAN = 0.015
I_VCC = 0.03                         # a TLC59711's own supply current, with margin: what
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
#     TLC59711's inputs (SDTI 9, SCKI 10) are at the bottom of its -X column and its
#     re-buffered outputs (SCKO 11, SDTO 12) at the bottom of its +X column, so a
#     left-to-right chain is a straight line;
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

# TLC59711 (PWP), datasheet Terminal Functions: 1 IREF 2 GND 3 R0 4 G0 5 B0 6 R1 7 G1
# 8 B1 9 SDTI 10 SCKI 11 SCKO 12 SDTO 13 R2 14 G2 15 B2 16 R3 17 G3 18 B3 19 VCC
# 20 VREG, thermal pad = GND (KiCad numbers it 21).
#
# ⚠ OUTPUTS ARE MAPPED BY GEOMETRY, NOT BY THE DATASHEET'S COLOUR GROUPS -- the same
# finding as elec/led_strip.py, for the same reason and with a different answer here.
# The three zones a driver serves are spread in X, one either side and one directly
# above, so:
#   zone -X   pins 5, 6, 7, 8        the -X column's lower half
#   zone mid  pins 3, 4, 17, 18      the TOP of both columns, straight down from y 30.4
#   zone +X   pins 13, 14, 15, 16    the +X column's lower half
# FIRMWARE MUST USE THIS TABLE. Global brightness correction (BC) is per colour GROUP
# and this mapping puts one zone's four dice in different groups, so all three BC
# fields are set equal and every per-fret adjustment happens in GS -- which is also
# what keeps the 16-bit depth useful at the dim end (docs/fret-led.md 6.5, 6.6).
ZONE_OUTS = {-1: (5, 6, 7, 8), 0: (3, 4, 17, 18), 1: (13, 14, 15, 16)}
COLOURS = ("R", "G", "B", "W")


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

# ── 1 k IN SERIES WITH EACH SIGNAL AT THE CABLE (manual quality pass M18, 2026-10-05) ────
# The Pi drives SCK and SDT at 3.3 V through 68 ohm (pi_cap R1..R4), and this board can be
# dark while the Pi is up: its fuse open, the lights' fuse on the motor board open, the
# 24 V lead off, or a Pi on its own USB supply on the bench. A TLC59711's inputs are rated
# to VREG + 0.6 V (SBVS181A 7.1), and VREG is 0 V then: the pin's protection diode
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

    # ⚠ THE 2.1 MHz VARIANT, AND IT IS THE POINT. LMR33630CRNXR is the optical board's
    # buck (C2071783) and the "C" is 2.1 MHz: a 400 kHz part beside a magnetic pickup
    # puts its fundamental four octaves nearer the audio band, and at light load every
    # LMR33630 pulse-skips, which drops the switching energy to a load-dependent rate.
    # Measured against THIS board's floor: the eight drivers' own ICC is tens of mA
    # even with every LED dark, which puts the skip rate in the hundreds of kHz. It
    # only reaches the audio band at loads this board cannot present while powered.
    # Pinout, SNVSAN3F Table 6-1 (VQFN column): 1 PGND, 2 VIN, 3 NC, 4 BOOT, 5 VCC,
    # 6 AGND, 7 FB, 8 PG, 9 EN, 10 VIN, 11 PGND, 12 SW. TI: "connect the SW pin to NC
    # on the PCB". PG unused. EN to VIN, which the datasheet allows.
    u = Part(name="LMR33630CRNX", ref_prefix="U", ref="U10", tag="U10", dest="NETLIST",
             tool="skidl", value="LMR33630CRNXR",
             description="24 V -> %.2f V synchronous buck, 2.1 MHz, 3 A "
                         "(LCSC C2071783)" % V_RAIL,
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
    # "3.3uH" does not specify an inductor, and saturation is what decides whether this
    # supply survives a fault. buck_cell.L1_VALUE says which part and why. Ripple at
    # 14.52 V out, 24 V in, 2.1 MHz: Vout(1-D)/(f L) = 0.83 A pk-pk, so the peak at BOTH
    # boards' 1.38 A full-white load is 1.79 A against 3.95 A of guaranteed saturation.
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
        u = Part(name="TLC59711", ref_prefix="U", ref="U%d" % (k + 1), tag="U%d" % (k + 1),
                 dest="NETLIST", tool="skidl", value="TLC59711PWPR",
                 description="12-ch 16-bit constant-current LED driver (LCSC C116842)",
                 footprint=DRV_FP, pins=[Pin(num=n, func=P) for n in range(1, 22)])
        iref, vreg = Net("IREF%d" % (k + 1)), Net("VREG%d" % (k + 1))
        u[1] += iref
        gnd += u[2], u[21]
        vrail += u[19]
        vreg += u[20]
        sdt += u[9]
        sck += u[10]
        # the LAST driver's re-buffered outputs: on the harness board they ARE the
        # chain's way across the seam; on the other they go nowhere, and the names say
        # NC rather than leaving netcheck to find a pin wired to nothing.
        if k < n_drv - 1:
            sck, sdt = Net("SCK_%d" % (k + 1)), Net("SDT_%d" % (k + 1))
        elif panel == HARNESS:
            sck, sdt = seam["SCK_SEAM"], seam["SDT_SEAM"]
        else:
            sck, sdt = Net("SCKO_CHAIN_END_NC"), Net("SDTO_CHAIN_END_NC")
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
        place["U%d" % (k + 1)] = (xd, DRV_Y, 0.0)
        fps["U%d" % (k + 1)] = DRV_FP
        for ref, dx, dy, fp in (("R%d" % (k + 1), -1.40, -5.00, R_FP),
                                ("C%d" % (k + 1), 1.40, -5.00, C_FP),
                                ("C%d" % (10 + k + 1), -1.90, 5.20, C_FP),
                                ("C%d" % (20 + k + 1), 1.40, 5.20, C08_FP)):
            place[ref] = (xd + dx, DRV_Y + dy, 0.0)
            fps[ref] = fp
        drivers.append((u, xd, trio))

    for k, (u, xd, trio) in enumerate(drivers):
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
    # each driver's heat pad gets its six vias (DRV_PAD_VIAS)
    notes["vias"] = list(notes.get("vias", [])) + [
        ("GND", round(xd + dx, 3), round(DRV_Y + dy, 3))
        for _u, xd, _trio in drivers for dx, dy in DRV_PAD_VIAS]
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
             "to": ["U%d.19" % (k + 1) for k in range(n_drv)], "amps": I_VCC},
        ]
        pin = {"S4B-XH-SM4-TB": "JST XH S4B-XH-SM4-TB drawing for pin 1; the way order is "
                                "J_PINS in _supply(), the Pi cap's end to match",
            "LMR33630CRNXR": "TI LMR33630 datasheet SNVSAN3F, Table 6-1, VQFN (RNX) column",
        }
        # ⚠ A SECOND BARREL, IN THE INDUCTOR'S OWN LAND. All 1.38 A of the rail leaves L1.2,
        # and the stitcher gives a pad one via because it does not know currents. The
        # land is 1.4 x 4.2 (over the 4 mm2 at which a via in a soldered land is
        # accepted), so one more goes straight down through it to the plane.
        # ONE, NOT TWO: two open barrels hold 0.23 of the 0.49 mm3 of paste printed on
        # the land, and a quarter is the limit (cadkit quality A12).
        # (L1_LAND along the part to the land's centre, 1.2 along the land from there)
        import math
        lx, ly, lrot = place["L1"]
        _kc, _ks = math.cos(math.radians(lrot)), math.sin(math.radians(lrot))
        notes["vias"] = list(notes.get("vias", [])) + [
            ("+14V5", round(lx + BC.L1_LAND * _kc - 1.2 * _ks, 3),
             round(ly + BC.L1_LAND * _ks + 1.2 * _kc, 3))]
        # the switch node and the two input loops are laid, not routed (buck_cell.tracks)
        notes["tracks"] = list(notes.get("tracks", [])) + BC.copper(
            *cell_org, v_out="+14V5") + BC.heat_copper(*cell_org)
        notes["vias"] = notes["vias"] + BC.vias(*cell_org) + BC.heat_vias(*cell_org)
        notes["stitch_exceptions"] = BC.STITCH_EXCEPTIONS
        waive = {
            # IPC-2221, 1 oz outer: 0.250 mm carries 0.875 A at a 10 C rise, so 0.89 A is
            # 10.4 C -- over 2 mm, between lands that are each a heat sink.
            "A1:+24V F1.2>U10.2": "U10.2's land is 0.25 mm wide, so the 2 mm of track "
                                  "into it cannot be wider; pins 9 and 10 take the same "
                                  "rail at 0.30. 10.4 C rise, by IPC-2221",
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
                  "to": ["U%d.19" % (k + 1) for k in range(n_drv)], "amps": I_VCC}]
        pin, waive = {}, {}
    notes["quality"] = {
        "power_paths": paths,
        "pinouts": dict({
            "XL-5050RGBW": "XINGLIGHT XL-5050RGBW datasheet, package drawing: pads 1-4 the "
                           "four anodes, 5-8 their cathodes; Steel:XINGLIGHT_XL-5050RGBW "
                           "is drawn from it",
            "TLC59711PWPR": "TI TLC59711 datasheet, Terminal Functions table, PWP "
                            "(HTSSOP-20) column, top view",
        }, **pin),
        "waive": waive,
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
