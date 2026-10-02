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
The +X board is pushed the full length of the channel first, so nothing can be plugged
into it once it is home. So the strip is a CHAIN joined by POGOS: every board carries four
side-mount pogos at its -X end (IN) and four at its +X end (OUT), under the board, and
they meet the next board's tip to tip when the second board is pushed home (user,
2026-10-02). No cable anywhere in the channel.

    inlet -> J11..J14 [board A] J21..J24 -><- J11..J14 [board B] J21..J24 (unused)

Both sets are populated on both boards because they are the same board. 24 V passes
straight through behind the fuse and the SPI chain runs IN -> U1 .. U4 -> OUT, so all
eight drivers are one stream from one Pi pin.

⚠ AND THE SEAM COSTS NO LIGHT. The pogos stand beside the LED row, not in it, so the row
runs to within half a pitch of both edges and the two boards butt: one pitch from end to
end, with the seam falling exactly half a pitch past the last LED of the first board.

⚠ THE INLET IS NOT ON THIS BOARD. The -X board's IN set is how the strip is fed, and a
cable socket cannot share that end with it: its lead would have to leave -X through a
row of four barrels that fill the trough from wall to LED. What mates that set is the
open item in .ins/WORKLIST-brenner.md.
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

# ── the parts: every one is already bought for another board ────────────────────
LED_FP = "Steel:XINGLIGHT_XL-5050RGBW"
DRV_FP = "Package_SO:HTSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3.4x6.5mm_Mask2.75x3.43mm"
BUCK_FP = "Steel:Texas_RNX0012_VQFN-HR-12_2x3mm_P0.5mm"
IND_FP = "Inductor_SMD:L_Sunlord_SWPA4030S"
R_FP = "Resistor_SMD:R_0402_1005Metric"
C_FP = "Capacitor_SMD:C_0402_1005Metric"
C08_FP = "Capacitor_SMD:C_0805_2012Metric"
C12_FP = "Capacitor_SMD:C_1206_3216Metric"
FUSE_FP = "Fuse:Fuse_1206_3216Metric"
# (No cable socket: the JST SH this board carried at each end went with the jumper. The
#  -X board still passes both boards' 0.73 A, through one pogo rated 12 A.)

R_IREF = "3k3"                       # 15.0 mA per channel, as the fret boards
# ⚠ 11.00 V, AND THE STRING LENGTH IS THE ONLY THING THAT SETS IT. A channel sinks
# constant current from the rail down through its series string, so the rail has to sit one
# string plus the sink's headroom above ground -- and every volt above that is heat in the
# driver rather than light. Three dice in series (src/foot_light.N_SERIES) is 9.6 V at the
# LED's 3.2 max, so 11.00 leaves 1.40 V of headroom.
#
# The whole rail change is R11: 100k / 10k on the LMR33630's 1.000 V reference is 11.00 V.
V_RAIL = 11.00
I_CHAN = 0.015
COLOURS = ("R", "G", "B", "W")
# THE SEAM AND THE INLET ARE POGOS: four Xinyangze YZF0002-38080-02 (LCSC C5203987) at
# each end, tip to tip with the next board's -- src/foot_light.py owns where they stand
# and src/pogo_part.py what they are. The 4-way SH sockets this board carried are gone,
# and with them the jumper nothing stocked was short enough to be.
POGO_FP = "Steel:Xinyangze_YZF0002-38080-02"

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

SUPPLY_LEN = 47.31                   # the thirteen supply parts plus their gaps,
                                     # measured by Row itself on the first run


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
    # J11..J14 at the -X end are IN, J21..J24 at the +X end are OUT, one per net in
    # foot_light.POGO_NETS' order. The footprint fires -X as drawn, so the +X set is
    # turned half a turn.
    v24_in = Net("+24V_IN")
    sck, sdt = Net("SCK_IN"), Net("SDT_IN")
    sck_out, sdt_out = Net("SCK_OUT"), Net("SDT_OUT")
    ends = {-1.0: {"+24V": v24_in, "GND": gnd, "SCK": sck, "SDT": sdt},
            +1.0: {"+24V": v24, "GND": gnd, "SCK": sck_out, "SDT": sdt_out}}
    pogo_refs = {}
    for sgn, base, what in ((-1.0, 10, "in"), (+1.0, 20, "out")):
        for i, (px, py, net) in enumerate(FL.pogo_pads(sgn)):
            ref = "J%d" % (base + i + 1)
            j = Part(name="YZF0002-38080-02", ref_prefix="J", ref=ref, tag=ref,
                     dest="NETLIST", tool="skidl", value="YZF0002-38080-02",
                     description="seam pogo, %s: %s (LCSC C5203987)" % (what, net),
                     footprint=POGO_FP, pins=[Pin(num=1, func=P)])
            ends[sgn][net] += j[1]
            place[ref] = (px, py, 0.0 if sgn < 0 else 180.0)
            fps[ref] = POGO_FP
            pogo_refs.setdefault(sgn, []).append(ref)

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
                    if k < n_drv - 1 else (sck_out, sdt_out))
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
    # is a 0.65 mm pitch HTSSOP-20 with twelve outputs, and the
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
