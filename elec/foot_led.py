"""FOOT LIGHTING board -- a 572.72 mm strip firing DOWN through the chassis window.

    py -3.12 elec/foot_led.py       # -> elec/out/foot_led.{net,board.json}

    286.36 x 17.20, 4 layers, 36 LEDs, 12 zones, 4 x TLC59711.  TWO PER INSTRUMENT.

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

⚠ BUT ONE PART NUMBER, BUILT TWICE -- and that is the install talking (user, 2026-09-30:
"we install this LED before we put the -x endplate on so it can slide in from -x"). Both
halves go in the same way up and the same way round, one after the other through the same
mouth, so the +X board is not a mirror of the -X board: it is the SAME board, 286.36
further along. A first draft had them as mirror images with their drops at opposite outer
ends, which cost a second fab and assembly setup and put one harness at the bridge end,
600 mm from the Pi. Sliding both from -X deletes all of that.

HOW THE POWER GETS TO THE FAR BOARD, which is the one thing -X-only insertion makes hard.
The +X board is pushed the full length of the channel first, so its own connector ends up
286 mm inside and its cable can never reach the mouth on its own -- and it cannot rise out
of the channel either, because it is UNDER a board everywhere except at a board edge. So
the strip is a CHAIN: every board carries an IN connector at its -X end and an OUT at its
+X end, both in the component lane, and a short jumper joins them in the relief groove.
The -X board's IN is the only thing that leaves the instrument.

    Pi -> J1 [board A] J2 -> jumper -> J1 [board B] J2 (unused)

Both connectors are populated on both boards because they are the same board; the far
board's J2 is a 21-cent spare. 24 V passes straight through and the SPI chain runs
J1 -> U1 -> U2 -> J2, so all four drivers are one stream from one Pi pin.

⚠ AND THE SEAM COSTS NO LIGHT. The connectors are in the LANE, not at the board ends, so
the LED row runs to within half a pitch of both edges and the two boards butt: 48 LEDs at
one pitch from end to end, with the seam falling exactly half a pitch past LED 23. The
jumper's wires run -X in the relief groove UNDER the far board for the 12 mm to its edge,
which is the whole reason the lane is relieved.
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

P = Pin.types.PASSIVE

# ── the parts: all but J1/J2 are already bought for another board ────────────────────
LED_FP = "Steel:XINGLIGHT_XL-5050RGBW"
DRV_FP = "Package_SO:HTSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3.4x6.5mm_Mask2.75x3.43mm"
BUCK_FP = "Steel:Texas_RNX0012_VQFN-HR-12_2x3mm_P0.5mm"
IND_FP = "Inductor_SMD:L_Sunlord_SWPA4030S"
R_FP = "Resistor_SMD:R_0402_1005Metric"
C_FP = "Capacitor_SMD:C_0402_1005Metric"
C08_FP = "Capacitor_SMD:C_0805_2012Metric"
C12_FP = "Capacitor_SMD:C_1206_3216Metric"
FUSE_FP = "Fuse:Fuse_1206_3216Metric"
# ⚠ JST SH, AND THE HEIGHT IS WHY -- the one new sourcing line on this board. Everything
# on the strip hangs from the board's underside into a trough that the LED sets the depth
# of: AIR_GAP + LED_H = 1.90 mm, relieved to 3.40 under the lane. The PH the rest of the
# instrument uses is 5.50 tall and does not fit at any relief worth cutting; the SH is
# **2.95**, read off JST's own drawing (side-entry side view, not a catalogue field).
# ⚠ 1.0 A / 50 V AGAINST 0.37 A A BOARD AT 24 V -- AND 0.73 A THROUGH THE -X BOARD'S
# J1 AND THE SEAM JUMPER, which carry both boards. That is the tightest number on this
# strip, 73% of a contact's rating, and it is the price of the 72-LED row. It is also a
# worst case the firmware never has to reach: it is every zone at full white at once,
# which the effects daemon caps the same way it caps the fret boards' 1.38 A. S4B is 4-way: GND, 24V, SCK, SDT.
# SM04B-SRSS-TB(LF)(SN), C160404, JST, 3,495 in stock at $0.2131@50.
J_FP = "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal"

R_IREF = "3k3"                       # 15.0 mA per channel, as the fret boards
# ⚠ 11.00 V, AND THE STRING LENGTH IS THE ONLY THING THAT SETS IT. A channel sinks
# constant current from the rail down through its series string, so the rail has to sit one
# string plus the sink's headroom above ground -- and every volt above that is heat in the
# driver rather than light. Three dice in series (src/foot_light.N_SERIES) is 9.6 V at the
# LED's 3.2 max, so 11.00 leaves 1.40 V of headroom, a little more than the 1.27 the
# earlier 4-in-series/14 V board ran on.
#
# The whole rail change is R11: 100k / 10k on the LMR33630's 1.000 V reference is 11.00 V.
#
# ⚠ RAIL CURRENT DOES NOT MOVE WHEN THE LED COUNT DOES, and that is the fact the whole
# strip is designed around. A channel draws 15.0 mA whether it feeds two dice or three, and
# the channel count is set by ZONES: 48 a board, before and after. Going from 48 LEDs to 72
# bought half again the light for 3.3 V of rail and $1.56 of LEDs -- no more drivers, no
# more amps, no more board.
#
# Each driver dissipates 0.39 W here: red's string is 6.6 V so its sink drops 4.4, and
# W/G/B drop the 1.40 headroom. 1.55 W a board, in a bay with 572 mm of aluminium-free
# plastic around it -- the four packages spread over 286 mm, not stacked.
V_RAIL = 11.00
I_CHAN = 0.015
COLOURS = ("R", "G", "B", "W")
# ⚠ +24V ON AN END PAD, AND IT IS THE ONE THING THAT KEPT FAILING. The SH is a 1.00 mm
# pitch part: its pads are ~0.60 wide with 0.40 between them, so an INTERIOR pad can only
# be entered by a track narrow enough to pass its neighbours -- 0.15 plus two 0.127
# clearances is 0.40, which is the whole gap. +24V sat on pin 2 and three separate routes
# left it 0.27..0.37 mm short of that pad, including an incremental run with every other
# net frozen. GND can live on an interior pad because it drops straight to its own plane;
# the traces want the ends.
J_PINS = ("V24", "GND", "SCK", "SDT")

# ── the two lanes ────────────────────────────────────────────────────────────────────
# ⚠ BOARD-LOCAL Y IS A MIRROR OF WORLD Y, because this board is installed FACE DOWN: the
# CAD turns it over about X to point the LEDs at the floor, which negates Y as well as Z.
# foot_light.to_board_y() is the one place that conversion lives. Getting it backwards
# would put the LED row on the wrong side of an 8 mm window and nothing downstream would
# notice -- the board routes, the CAD renders, and the light misses the slot.
LED_Y = FL.to_board_y(FL.led_y())           # -3.75
LANE_Y = FL.to_board_y(FL.DRV_Y)            # +4.05
J_Y = FL.to_board_y(FL.J_Y)                 # +4.20
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

# J1/J2 sit J_INSET in from their board ends. 12.0 is what gives the jumper somewhere to
# be: mouth to mouth across the butted seam is 2 x 12 = 24 mm, and the two mated plugs
# take about 8 of it, so ~16 mm of free wire lies in the relief groove under the boards.
J_INSET = FL.J_INSET
SUPPLY_LEN = 47.31                   # the thirteen supply parts plus their gaps,
                                     # measured by Row itself on the first run
J_ANCHOR = 4.4 + 0.7083              # mouth (local +Y 4.4) to the PAD CENTROID, read out
                                     # of the .kicad_mod -- NOT the PH's 5.8125


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

    def __init__(self, place, fps, x, gap=0.45, dirn=1.0):
        self.place, self.fps, self.x, self.gap, self.dirn = place, fps, x, gap, dirn

    def add(self, ref, fp, rot=0.0):
        w, h = fp_box(fp)
        if round(rot) % 180:
            w = h
        self.x += self.dirn * w / 2.0
        self.place[ref] = (self.x, LANE_Y, rot)
        self.fps[ref] = fp
        self.x += self.dirn * (w / 2.0 + self.gap)
        return self


def build(passes=20):
    name = FL.BOARD_NAME
    skidl.reset()
    x0, x1 = FL.board_span("a")
    length = x1 - x0
    xs = [FL.to_board_x("a", x) for x in FL.board_leds("a")]
    n_zone = len(xs) // FL.N_SERIES
    n_drv = (n_zone + 2) // 3
    assert len(xs) % FL.N_SERIES == 0 and n_zone % 3 == 0, (
        "%s: %d LEDs is %d zones -- zones come in threes (a TLC59711 carries three) "
        "and strings in N_SERIES" % (name, len(xs), n_zone))
    half = length / 2.0

    gnd, v24, vrail = Net("GND"), Net("+24V"), Net("+11V")
    for n in (gnd, v24, vrail):
        n.drive = Pin.drives.POWER
    place, fps = {}, {}

    # ── the two ends of the chain ────────────────────────────────────────────────────
    js = {}
    for ref, sgn, what in (("J1", -1.0, "in: from the Pi, or from the previous board"),
                           ("J2", +1.0, "out: to the next board (-X board only; the +X "
                                        "board's is a spare)")):
        js[ref] = Part(name="SM04B-SRSS-TB", ref_prefix="J", ref=ref, tag=ref,
                       dest="NETLIST", tool="skidl", value="SM04B-SRSS-TB",
                       description="%s -- GND, +24V, SCK, SDT (LCSC C160404)" % what,
                       footprint=J_FP,
                       pins=[Pin(num=i + 1, name=n, func=P)
                             for i, n in enumerate(J_PINS)])
        # mouth faces OUTBOARD on both: rot 270 turns it -X, rot 90 turns it +X, and the
        # placement anchors on the pad centroid J_ANCHOR behind the mouth
        mouth = sgn * (half - J_INSET)
        place[ref] = (mouth - sgn * J_ANCHOR, J_Y, 270.0 if sgn < 0 else 90.0)
        fps[ref] = J_FP
    v24_in = Net("+24V_IN")
    gnd += js["J1"][1], js["J2"][1]
    v24_in += js["J1"][2]
    v24 += js["J2"][2]                       # 24 V passes THROUGH to the next board
    sck, sdt = Net("SCK_IN"), Net("SDT_IN")
    sck += js["J1"][3]
    sdt += js["J1"][4]

    f1 = Part(name="Fuse", ref_prefix="F", ref="F1", tag="F1", dest="NETLIST",
              tool="skidl", value="1A",
              description="24 V fuse -- a shorted U10 must not feed the fault back out "
                          "into the trunk, nor into the next board", footprint=FUSE_FP,
              pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    v24_in += f1[1]
    v24 += f1[2]

    # ── the buck: the fret boards', unchanged ────────────────────────────────────────
    u10 = Part(name="LMR33630CRNX", ref_prefix="U", ref="U10", tag="U10", dest="NETLIST",
               tool="skidl", value="LMR33630CRNXR",
               description="24 V -> 11.00 V synchronous buck, 2.1 MHz, 3 A (LCSC C2071783)",
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
              value="SWPA4030S4R7MT",
              description="buck output inductor, 4.7 uH shielded, Isat 3.2 A, "
                          "DCR 78 mohm, 4.0 x 4.0 x 3.0 (LCSC C57269)",
              footprint=IND_FP, pins=[Pin(num=1, func=P), Pin(num=2, func=P)])
    sw += l1[1]
    vrail += l1[2]
    for ref, val, fp, net, why in (
            ("C30", "10uF/50V", C12_FP, v24, "buck input bulk"),
            ("C31", "10uF/50V", C12_FP, v24, "buck input bulk"),
            ("C32", "100nF", C_FP, v24, "buck input HF bypass -- at U10's VIN/GND pins"),
            ("C34", "1uF", C_FP, vcc, "buck VCC bypass"),
            ("C36", "10uF/50V", C12_FP, vrail, "11 V output bulk"),
            ("C37", "10uF/50V", C12_FP, vrail, "11 V output bulk"),
            ("C38", "100nF", C_FP, vrail, "11 V output HF bypass")):
        c = _c(ref, val, why, fp)
        net += c[1]
        gnd += c[2]
    c33 = _c("C33", "100nF", "buck bootstrap -- BOOT to SW")
    boot += c33[1]
    sw += c33[2]
    r10 = _r("R10", "100k", "11 V feedback divider, top")
    r11 = _r("R11", "10k 1%", "11 V feedback divider, bottom -- 11.00 V with R10, "
                              "against a 9.60 V string at the LED's max Vf")
    vrail += r10[1]
    fb += r10[2], r11[1]
    gnd += r11[2]

    # ⚠ THE SUPPLY SITS IN THE MIDDLE OF THE BOARD, AND THE RETURNS ARE WHY. Each
    # driver's outer two zones return along the lane from +-2.5 pitches away, so the
    # lane between a driver and its outer zones -- x -101..-41 and +41..+101 -- is a
    # traffic corridor carrying four returns each way. Parked next to J1, the supply
    # sat squarely in the -X one, and route after route left exactly one of zone 0's
    # four returns unconnected -- a different colour each time, which is what a board
    # at its limit looks like. The middle 82 mm carries no returns at all.
    #
    # ⚠ IT COSTS DISTANCE TO THE PICKUP AND THAT IS WORTH STATING. On the +X board
    # the buck moves from ~187 mm away to ~73, which is 16x the coupling by 1/r^3. It
    # is still the quieter of the two things on this board: a tight 2.1 MHz hot loop
    # of ~5 mm2 at 73 mm is 4x below the LED loop's 15 mm2 at 66 mm that shares the
    # board with it, and its spectrum is nowhere near the audio band.
    row = Row(place, fps, -SUPPLY_LEN / 2.0)
    for ref, fp in (("F1", FUSE_FP), ("C30", C12_FP), ("C31", C12_FP), ("C32", C_FP),
                    ("U10", BUCK_FP), ("C33", C_FP), ("C34", C_FP), ("L1", IND_FP),
                    ("C36", C12_FP), ("C37", C12_FP), ("C38", C_FP), ("R10", R_FP),
                    ("R11", R_FP)):
        row.add(ref, fp)

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
                    if k < n_drv - 1 else (Net("SCK_OUT"), Net("SDT_OUT")))
        sck += u[11]
        sdt += u[12]
        r = _r("R%d" % (k + 1), R_IREF, "U%d IREF -- 15.0 mA per channel" % (k + 1))
        iref += r[1]
        gnd += r[2]
        cv = _c("C%d" % (k + 1), "1uF", "U%d VREG (datasheet: 1 uF required)" % (k + 1))
        vreg += cv[1]
        gnd += cv[2]
        cc = _c("C%d" % (10 + k + 1), "100nF", "U%d VCC bypass" % (k + 1))
        vrail += cc[1]
        gnd += cc[2]
        cb = _c("C%d" % (20 + k + 1), "4.7uF/25V", "U%d local bulk -- its zones' PWM "
                "current must come from here, not the far end of the rail" % (k + 1),
                C08_FP)
        vrail += cb[1]
        gnd += cb[2]
        place["U%d" % (k + 1)] = (xd, LANE_Y, 0.0)
        fps["U%d" % (k + 1)] = DRV_FP
        # the driver's own four passives go OUTBOARD of it, in the lane -- away from the
        # board's middle, which is where the supply block sits. See Row on the direction.
        sgn = -1.0 if xd < 0 else 1.0
        prow = Row(place, fps, xd + sgn * (fp_box(DRV_FP)[0] / 2.0 + 0.45), dirn=sgn)
        for ref, fp in (("R%d" % (k + 1), R_FP), ("C%d" % (k + 1), C_FP),
                        ("C%d" % (10 + k + 1), C_FP), ("C%d" % (20 + k + 1), C08_FP)):
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

    # the chain leaves on J2
    sck += js["J2"][3]
    sdt += js["J2"][4]

    check_placement(name, place, fps)
    ERC()
    net = os.path.join(OUT_DIR, "%s.net" % name)
    generate_netlist(file_=net)
    netcheck.grounds_meet(net)
    netcheck.no_orphan_pins(net)

    notes = dict(BOARD_NOTES)
    notes["outline_mm"] = (round(length, 3), round(BOARD_W, 3))
    notes["placements"] = {k: list(v) for k, v in place.items()}
    notes["router_passes"] = passes
    with open(os.path.join(OUT_DIR, "%s.board.json" % name), "w") as f:
        json.dump(notes, f, indent=2)
    print("%-9s %6.1f x %.2f mm, %2d LEDs, %d zones, %d drivers, x%d per instrument"
          % (name, length, BOARD_W, len(xs), n_zone, n_drv, FL.BOARD_QTY))
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
    # In1 = +14V and In2 = GND, for the reason fret_led.py records: the conductor that
    # mirrors a zone's long F.Cu run is the RAIL, not ground, because the local bulk sits
    # at the driver.
    "layers": 4,
    "thickness_mm": 1.6,
    "zones": [("+11V", "In1.Cu", 0.3), ("GND", "In2.Cu", 0.3)],
    "plane_layers": ("In1.Cu", "In2.Cu"),
    "local_inner": "B.Cu",
    "stitch_nets": ("+11V", "GND"),
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
    # are a 1.00 mm pitch SH and a 0.65 mm pitch HTSSOP-20 with twelve outputs, and the
    # default 0.25 does not leave either escape room to turn. 0.15 on 1 oz carries ~0.5 A
    # at a 10 C rise against this board's largest signal load of 15 mA -- the constraint
    # is geometry, not current. The rails keep their own width below.
    "track_mm": 0.15,
    # ...and the two power nets are widened back up. +11V and GND are planes, so this is
    # really just the 24 V pass-through, which carries 0.24 A the length of the board.
    "net_widths": {"+24V": 0.30},
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
    "qty_per_instrument": FL.BOARD_QTY,
}


if __name__ == "__main__":
    n_led, n_zone, n_drv = build()
    q = FL.BOARD_QTY
    print("%d LEDs, %d zones, %d channels, %d drivers per instrument, %.2f A at %.2f V"
          % (n_led * q, n_zone * q, 4 * n_zone * q, n_drv * q,
             4 * n_zone * q * I_CHAN, V_RAIL))
    print("run %.2f mm, pitch %.3f, depth %.2f -> %.3f : 1"
          % (FL.run_len(), FL.pitch(), FL.depth(), 1.0 / FL.check_optics()))
