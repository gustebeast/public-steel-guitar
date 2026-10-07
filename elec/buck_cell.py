"""The LMR33630 in its RNX package, and the seven parts that have to stand against it.

One placement, measured once, for every board here that carries this buck (the two foot
strips and the keyhead fret board). It is the optical board's U13 cell (elec/optical.py,
M13), which was compared against TI's own RNX layout example on a routed board: the same
IC in the same package. The bulk capacitors and the inductor follow in one row (BULK); a fuse and test pads are
each board's own.

    ROLE    PINS            WHY IT IS WHERE IT IS (SNVSAN3F 9.2.2.6 and section 10)
    CIN_A   VIN 2 / PGND 1  the RNX has a VIN and a PGND pin on EACH long side, and TI
    CIN_B   VIN 10 / PGND 11  wants a small 50 V capacitor across each pair, on the
                            part's own layer with no via in the loop
    CBOOT   BOOT 4 / SW 3   pin 3 is the SW pin TI provides for exactly this
    CVCC    VCC 5
    RFBB    FB 7 / GND      the divider is AT the pin: FB is the one high-impedance
    RFBT    rail / FB 7     node here
    RFBP    FB 7 / GND      optional, across RFBB: trims the rail with two stock values

Every two-pad part is wired pin 1 = its own net and pin 2 = ground (CBOOT: BOOT / SW;
RFBT: rail / FB), which is what puts the right pad at the pin.

⚠ OFFSETS ARE FROM THE PLACEMENT POINT, WHICH IS THE PAD CENTROID AND NOT THE FOOTPRINT'S
ORIGIN: layout anchors a part on the mean of its pads, and the RNX's is 0.159 below its
origin. Read off a laid-out board: VIN pins at y +0.634, PGND at +1.284, x +-0.90; an
0402's pads at +0.32 and +1.28, x +-2.115.
"""
from __future__ import annotations

import math

# role -> (dx, dy, rot), the cell's own frame: +x is the way the inductor goes
CORE = {
    "CIN_A": (-2.115, +0.80, 90.0),
    "CIN_B": (+2.115, +0.80, 90.0),
    "CBOOT": (-2.115, -1.32, 90.0),
    # CVCC STANDS UNDER ITS OWN PIN, pad 1 up against pin 5 and its ground pad beside the
    # track that comes down from pin 6: the gate drivers' supply loop is 3 mm of front
    # copper. Beside CBOOT, where it stood until 2026-10-05, the bootstrap capacitor
    # walled it in and the router took it through two vias and 4.6 mm of 0.15 track.
    "CVCC": (-0.75, -2.72, 270.0),
    "RFBB": (+2.115, -1.32, 90.0),
    "RFBT": (+3.295, -1.32, 270.0),
    "RFBP": (+2.115, -3.25, 270.0),
}
# ⚠ THE REGULATOR IS THE 1.4 MHz PART, LMR33630BRNXR, AND HEAT IS WHY (manual quality
# pass M25, 2026-10-05). These boards carried the 2.1 MHz LMR33630CRNXR, the optical
# board's. Read off TI's own curves at 24 V in (SNVSAN3F figures 9-15 and 9-17, RNX
# package), the converter loses
#     2.1 MHz   1.2 W at 0.7 A   1.25 W at 1 A   1.45 W at 1.4 A
#     1.4 MHz   0.9 W            0.95 W          1.1 W
# and about 0.75 W of the 2.1 MHz figure is there at any load: it is what switching 24 V
# two million times a second costs. The RNX package has no thermal pad, so on this copper
# (about 57 to 60 C/W, see heat_copper) the C part sat at about 117 to 127 C at 45 C
# ambient with every LED at full white, against 125 C. The B part is the same package,
# the same pins and the same sheet: 99 to 107 C.
# ⚠ THE C PART STILL FITS THIS BOARD, with this inductor (ripple 0.6 A at 2.1 MHz, 20 %).
# It is the named alternate if the B is out of stock on the day -- JLCPCB held 260 on
# 2026-10-05 against 3,453 of the C -- and then full white must be capped in firmware.
U_VALUE = "LMR33630BRNXR"
U_LCSC = "C2071384"
U_ALT = "LMR33630CRNXR (C2071783): same land, 2.1 MHz, about 0.35 W hotter"
U_FSW = 1.4e6
# ⚠ THE INDUCTOR IS SUNLORD SWPA5040S4R7MT, 5 x 5 x 4, and both its numbers were chosen.
# 4.7 uH is the value TI's table gives for 12 V out at 1.4 MHz; their floor, 0.28 x
# Vout / fsw, is 2.3 uH on the foot boards' 11.5 V and 2.9 uH on the fret board's 14.5 V
# against this part's 3.76 at -20 %. Ripple is 0.87 to 0.91 A, 30 % of the IC's 3 A.
# SATURATION: 3.50 A guaranteed, 3.90 typical (Sunlord's table; a 30 % drop in
# inductance). TI: "the inductor saturation current must not be less than the device
# low-side current limit", 3.5 A typical, 2.9 to 4.1 (SNVSAN3F 7.5, 9.2.2.4). The 4 x 4
# SWPA4030S4R7MT these boards started with is 2.90 guaranteed and 3.20 typical, so a
# shorted rail saturated it; it also had twice the resistance (78 against 39 milliohm).
L1_VALUE = "SWPA5040S4R7MT"
L1_LCSC = "C48496"
L1_FP = "Inductor_SMD:L_Sunlord_SWPA5040S"
L1_DESC = ("buck output inductor, 4.7 uH +-20 % shielded, Isat 3.50 A min / 3.90 typ, "
           "DCR 39 mohm max, 5.0 x 5.0 x 4.0 (LCSC C48496)")
L1_UH, L1_ISAT = 4.7, 3.50
L1_DX = 7.035                # the inductor's centre, a 5 x 5 mm part with lands at +-1.85
L1_LAND = 1.85
SW_W = 0.50

# ── THE BULK, in a row along the cell's own axis ───────────────────────────────────────
# role -> (dx, dy, rot). Every 1206 stands ACROSS the row (rot 90: its own net's pad at
# -y, ground at +y), which is what lets one ground slab and one input slab run the length
# of the input side and take both capacitors in.
BULK = {
    "CIN_1": (-5.25, 0.0, 90.0),
    "CIN_2": (-7.85, 0.0, 90.0),
    "L1": (L1_DX, 0.0, 0.0),
    "COUT_1": (+11.20, 0.0, 90.0),
    "COUT_2": (+13.80, 0.0, 90.0),
    "COUT_HF": (+15.70, 0.0, 90.0),
}
X_MIN, X_MAX = -9.15, +16.20     # the cell's reach along its axis, copper and courtyards


def at(origin, turn, dx, dy, rot=0.0):
    """A cell-frame point (and part angle) on the board: the cell turned `turn` degrees
    anticlockwise about U10's placement point, which is at `origin`."""
    t = math.radians(turn)
    x = origin[0] + dx * math.cos(t) - dy * math.sin(t)
    y = origin[1] + dx * math.sin(t) + dy * math.cos(t)
    return (round(x, 4), round(y, 4), (rot + turn) % 360.0)


# ── THE COPPER THAT IS LAID RATHER THAN ROUTED ─────────────────────────────────────────
# ⚠ MOST OF IT IS THERE TO CARRY HEAT (manual quality pass M25, 2026-10-05). This package
# has no thermal pad: TI say so (SNVSAN3F 9.2.2.11, "a DAP is not available ... this
# package exhibits a somewhat large value R-theta-JA") and give 50 to 63 C/W on a
# four-layer board against the copper round it (figure 9-4), 72.5 C/W on the JEDEC board.
# At 24 V in and 2.1 MHz the part burns about a watt whatever it delivers -- read off the
# RNX efficiency curves (figure 9-17: 83 % at 1 A of 5 V is 1.0 W, 86 % at 2 A is 1.6) --
# and until now each power pin left on 0.6 mm of 0.25 mm track to an 0402 pad. That is the
# JEDEC case or worse: 1.25 W on the fret board is about 100 C of rise.
#
# So each VIN and PGND pin now sits IN copper as wide as the pin pitch allows (0.4 and
# 0.8 mm), and that copper runs straight out into a slab: ground along the top of the
# input side, the input rail beside it, both taking the bulk capacitors' pads in on the
# way. About 30 mm2 of copper 0.2 mm above the first plane, plus eight vias to the ground
# plane (four declared, four the stitcher's) -- TI's own arrangement, drawn with tracks because this flow has no local pours.
#
# THE SWITCH NODE STAYS A TRACK: the one net here that radiates, never a heatsink. Out of
# the top pad (pin 12), over the right-hand ground bar, into the inductor's near land.
# THE HOT LOOPS are the two strips nearest the package, pin to capacitor pad on the part's
# own layer with no via between them. Every via named here is OUTBOARD of its capacitor.
#
# ⚠ AND THE STITCHER MUST LEAVE THE TWO PGND PINS ALONE (STITCH_EXCEPTIONS). Left to itself
# it ran pin 11's ground stub down the gap between the package and CIN_B and walled pins
# 9 and 10 off from the rest of the input net.
def copper(origin, turn, v_in="+24V", v_out=None, v_cc="BUCK_VCC"):
    """BOARD_NOTES["tracks"] entries. `v_out` (the rail's net) adds the output side: the
    inductor's far land to both output capacitors, and their grounds to each other."""
    def run(net, w, *pts):
        return (net, "F.Cu", w, [at(origin, turn, x, y)[:2] for x, y in pts])
    lx = L1_DX - L1_LAND
    out = [
        run("SW", SW_W, (0.0, 1.20), (0.0, 2.45), (lx - 0.60, 2.45), (lx, 1.40)),
        # input side: the two pins in copper, then the slabs
        run("GND", 0.80, (-0.95, 1.50), (-2.30, 1.50)),
        run("GND", 2.60, (-2.30, 2.40), (BULK["CIN_2"][0], 2.40)),
        run(v_in, 0.40, (-0.95, 0.60), (-1.60, 0.60), (-2.00, 0.35)),
        run(v_in, 0.90, (-2.00, 0.15), (BULK["CIN_2"][0], 0.15)),
        run(v_in, 1.00, (BULK["CIN_1"][0], 0.15), (BULK["CIN_1"][0], -1.475)),
        run(v_in, 1.00, (BULK["CIN_2"][0], 0.15), (BULK["CIN_2"][0], -1.475)),
        # the other pair, and EN (pin 9) onto its neighbour's copper
        run("GND", 0.80, (0.95, 1.50), (3.60, 1.50)),
        run(v_in, 0.40, (0.95, 0.60), (1.60, 0.60), (2.115, 0.35)),
        run(v_in, 0.70, (2.115, 0.35), (3.70, 0.35)),
        run(v_in, 0.25, (0.95, -0.016), (1.65, -0.016), (1.65, 0.35)),
        # ⚠ THE BOOTSTRAP CAPACITOR'S TWO 1 mm LINKS ARE LAID TOO, and pin 3 to the switch
        # pad. Pin 3 is the SW pin TI put beside BOOT for exactly this capacitor. Left to
        # the router, the foot boards got these three short front-layer links and the
        # keyhead fret board got C33's switch side taken through a via, 9 mm along the
        # BACK under the feedback divider, and up through a second via into the
        # inductor's land: a switch node on two layers. This is the foot boards' routed
        # solution, copied: 0.13 where BOOT and SW pass each other, as it was.
        run("SW", 0.15, (-2.115, -0.84), (-2.00, -0.84), (-1.34, -0.18)),
        run("SW", 0.13, (-1.34, -0.18), (-1.06, -0.18), (-0.90, -0.01)),
        run("SW", 0.15, (0.0, 0.81), (-0.83, -0.01), (-0.90, -0.01)),
        run("BOOT", 0.15, (-2.115, -1.80), (-1.76, -1.80), (-1.59, -1.64)),
        run("BOOT", 0.13, (-1.59, -1.64), (-1.59, -1.21), (-1.11, -0.73)),
        run("BOOT", 0.15, (-1.11, -0.73), (-0.90, -0.51)),
        # VCC (pin 5) into its capacitor, and AGND (pin 6) round to the capacitor's
        # other pad: see CORE["CVCC"]
        run(v_cc, 0.25, (-0.50, -1.24), (-0.50, -2.00), (-0.75, -2.24)),
        run("GND", 0.25, (0.0, -1.24), (0.0, -3.20), (-0.75, -3.20)),
        # ...and the two input sides joined UNDER the package, on the back: the right-hand
        # pair is walled in by the ground bar and the switch node, and the router found
        # no way out for it (one unconnected, 1.8 mm long). Via to via, see vias().
        (v_in, "B.Cu", 0.50, [at(origin, turn, *VIN_LINK[0])[:2],
                              at(origin, turn, *VIN_LINK[1])[:2]]),
    ]
    if v_out:
        out += [
            run(v_out, 1.00, (L1_DX + L1_LAND, -1.30), (BULK["COUT_2"][0], -1.475)),
            run("GND", 1.00, (BULK["COUT_1"][0], 1.60), (BULK["COUT_2"][0], 1.60)),
        ]
    return out


VIN_LINK = ((-3.40, 0.15), (+3.40, 0.35))        # a via in each input slab


def vias(origin, turn, v_in="+24V"):
    """[(net, x, y)]: the ground slabs' own way down to the plane, and the two ends of the
    input link. A board adds its via size.

    ⚠ FOUR GROUND VIAS, PLACED BETWEEN THE STITCHER'S. Every capacitor's ground pad gets a
    stitch via of its own beside it (at x -7.85, -5.25 and -2.1 on the input slab, 2.9 on
    the right-hand bar), and the first set declared here landed on top of three of them:
    two drills 0.05 mm INTO each other."""
    gnd = [(-2.60, 3.00), (-3.80, 3.00), (-6.55, 3.00), (3.60, 1.50)]
    return ([("GND",) + at(origin, turn, x, y)[:2] for x, y in gnd]
            + [(v_in,) + at(origin, turn, x, y)[:2] for x, y in VIN_LINK])


STITCH_EXCEPTIONS = ("U10.1", "U10.11")


# ── MORE GROUND COPPER, for the board whose buck runs hot ─────────────────────────────
# The RNX package has no pad: its heat leaves through the pins, mostly the two PGND
# pins, into whatever copper they are soldered to, and 35 um copper is 74 C/W a SQUARE.
# The ground slab under the input side is 14 mm2 with six vias. This lays a second band
# beside it, joined to it, on the front and again on the back, with nine vias between
# them and the ground plane: about three times the copper within 5 mm of pin 1.
# ⚠ ONLY ON THE +y SIDE AND ONLY FROM THE INPUT SLAB. The right-hand PGND pin is walled
# in by the switch node, which leaves the package at +y and turns over it.
# The keyhead fret board asks for it (1.15 W at full white); the foot boards' 0.9 W
# does not need it and their lane has no room beside the cell.
HEAT_Y = 4.50                                    # the band's centre line, 2.0 wide
HEAT_X = (-4.30, +10.20)                         # clear of a test pad at -6.5 and at 12.5
HEAT_VIAS_X = (-4.00, -2.50, -1.00, 0.50, 4.20, 5.70, 7.20, 8.70, 10.20)   # none in 2.5's pad


def heat_copper(origin, turn):
    """BOARD_NOTES["tracks"] entries: see above."""
    a = at(origin, turn, HEAT_X[0], HEAT_Y)[:2]
    b = at(origin, turn, HEAT_X[1], HEAT_Y)[:2]
    return [("GND", "F.Cu", 2.00, [a, b]), ("GND", "B.Cu", 2.00, [a, b]),
            # and a fat join into the input slab, which the band only overlaps by 0.2
            ("GND", "F.Cu", 1.60, [at(origin, turn, -3.20, 2.40)[:2],
                                   at(origin, turn, -3.20, HEAT_Y)[:2]])]


def heat_vias(origin, turn):
    return [("GND",) + at(origin, turn, x, HEAT_Y)[:2] for x in HEAT_VIAS_X]


# ── A SUPPLY DOES NOT ENTER A PLANE THROUGH ONE VIA (manual quality pass M3) ────────────
# Not part of the cell, but both LED boards need it and this is the file they share. The
# stitcher gives a plane-net land one via. For a decoupling capacitor that is right; for
# the land a whole board's supply or its return arrives on -- a seam spring pin, the
# cable socket's ground way -- it is 0.9 A through a single plated barrel, which carries
# it (about 1.5 A at a 10 C rise) and is still the one thing whose crack darkens the
# board. So those lands get two more.
POGO_VIA_DX = (-1.60, +1.60)         # along the 5.0 mm land, either side of the stitcher's


def land_vias(net, x, y):
    """Two more vias in a 5.0 x 3.5 spring-pin land centred (x, y)."""
    return [(net, round(x + dx, 3), round(y, 3)) for dx in POGO_VIA_DX]


# The XH socket's lands are 4.5 x 1.3, too small for a second open barrel (it would hold
# a third of the land's paste), so its ground way gets a via just past the land's toe on
# 0.4 mm of track. From the footprint's PAD CENTROID at rot 270, which is where elec/
# places it: way 1 is 3.75 towards +y and each way after it 2.50 further towards -y, the
# lands' centres 2.27 towards +x, their toes 4.52.
XH_WAY1_DY = 3.75
XH_PITCH = 2.50
XH_TOE_VIA = 5.30


def xh_way_dy(way):
    """Board y of way `way` (1-based) from the pad centroid of an XH at rot 270."""
    return XH_WAY1_DY - XH_PITCH * (way - 1)


def xh_way(ways, name):
    """The 1-based way that carries `name` in a lead's order (harness.LED_DROP)."""
    return tuple(ways).index(name) + 1


def xh_ground_via(jx, jy, way):
    """(track, via) for an S4B-XH-SM4-TB placed at (jx, jy), rot 270, whose ground is
    way `way` -- whichever one the lead's order puts it on."""
    y = round(jy + xh_way_dy(way), 3)
    return (("GND", "F.Cu", 0.40, [(round(jx + 3.50, 3), y), (round(jx + XH_TOE_VIA, 3), y)]),
            ("GND", round(jx + XH_TOE_VIA, 3), y))


# ── WHAT EVERY NET REACHES, AND WHAT EVERY PIN ON IT IS RATED FOR (quality A16) ───────
# One declaration for every board built on this cell -- the fret boards and the foot
# strip carry the same regulator, the same drivers, the same LEDs and the same seam pin.
# The WORST CASE, not the nominal, and each rating read from its maker's own table.
# ⚠ 24.72 V, NOT 24: Mean Well's GST160A24 is 24 V +-3.0 % (specification table, "voltage
# tolerance", which their note 4 says includes set-up, line and load). It matters in one
# place: the seam pin is rated 24 V, so a seam that carries the 24 V bus is over it.
V24_MAX = 24.72


def net_volts(rail, rail_max, rail_why):
    """quality.net_volts for a board whose LED rail is the net `rail`."""
    return {
        "GND": 0,
        "*_NC": 0,                       # a no-connect pin or an output left open
        "+24V*": {"v": V24_MAX, "why": "Mean Well GST160A24-R7B: 24 V +-3.0 %. The "
                                       "leads are plugged with the instrument off "
                                       "(M16), so there is no ring to add"},
        "SW": {"v": V24_MAX, "why": "the switch node swings between ground and the input"},
        "BOOT": {"v": V24_MAX + 5.25, "why": "the switch node plus the regulator's own VCC"},
        "BUCK_VCC": {"v": 5.25, "why": "LMR33630's internal LDO, SNVSAN3F 7.5: 5 V nominal"},
        "FB": {"v": 1.02, "why": "the 1.000 V reference, +1.5 %"},
        rail: {"v": rail_max, "why": rail_why},
        "Z*": {"v": rail_max, "why": "a node of an LED string: at the rail whenever its "
                                     "sink is off, lower when it conducts"},
        "VREG*": {"v": 3.5, "why": "TLC5971's internal regulator, SBVS146D 6.5: 3.5 V "
                                   "maximum"},
        "IREF*": {"v": 1.25, "why": "the 1.21 V reference across the IREF resistor"},
        "SCK*": {"v": 3.5, "why": "the Pi's 3.3 V, or a driver's VREG-level output"},
        "SDT*": {"v": 3.5, "why": "the Pi's 3.3 V, or a driver's VREG-level output"},
    }


def pin_volts(pogo_mpn, resistors, pogo_accepted=None):
    """quality.pin_volts for the same boards. `resistors` are the 0402 values fitted."""
    r0402 = {"max": 50.0, "src": "UNI-ROYAL 0402WGF series (and Yageo RC0402): maximum "
                                 "working voltage 50 V"}
    fuse = {"max": 63.0, "src": "JDT JFC1206 series sheet: voltage rating 63 V"}
    d = {
        "TLC5971RGER": {
            "src": "TI TLC5971 datasheet SBVS146D, 6.1 absolute maximum ratings",
            "max": 18.0,                 # VCC and the twelve outputs
            "pins": {
                "[12]": {"max": 3.7, "why": "SDTI / SCKI: VREG + 0.6 V, at this driver's "
                                            "lowest VREG (3.1 V)"},
                "[56]": {"max": "none", "why": "SCKO / SDTO are this pin's own VREG-level "
                                               "outputs, rated VREG + 0.3 V"},
                "15": {"max": 6.0},      # VREG
                "16": {"max": 3.4, "why": "IREF: VREG + 0.3 V, at the lowest VREG"},
            }},
        U_VALUE: {
            "src": "TI LMR33630 datasheet SNVSAN3F, 7.1 absolute maximum ratings",
            "max": 38.0,                 # VIN; EN is tied to it and rated VIN + 0.3 V
            "pins": {
                "3": {"max": V24_MAX + 0.3, "why": "SW: VIN + 0.3 V"},
                "12": {"max": V24_MAX + 0.3, "why": "SW: VIN + 0.3 V"},
                "4": {"max": "none", "why": "BOOT is rated 5.5 V to SW, not to ground, "
                                            "and it is the regulator's own VCC that "
                                            "charges it"},
                "5": {"max": 5.5}, "7": {"max": 5.5}, "8": {"max": 22.0},
            }},
        "JFC1206-1200FS": fuse, "JFC1206-1100FS": fuse,
        "S4B-XH-SM4-TB": {"max": 250.0, "src": "JST XH series: rated 250 V"},
        pogo_mpn: dict({"max": 24.0, "src": "Xinyangze YZF0002-38080-02 specification A.0: "
                                            "voltage rating 24 V AC (rms) / DC"},
                       **({"accepted": pogo_accepted, "peak": "none",
                           "why": "the sheet gives one voltage and no transient rating, "
                                  "and the input declares no transient above its steady "
                                  "worst case: the leads are plugged with the "
                                  "instrument off (M16)"} if pogo_accepted else {})),
        "XL-5050RGBW": {
            "max": "none", "src": "XINGLIGHT XL-5050RGBW sheet, absolute maximum ratings",
            "why": "a die in a series string has no rating to ground: its limits are "
                   "forward current, which the sink sets, and 5 V reverse, which a "
                   "string fed from one rail through one sink cannot apply"},
        L1_VALUE: {"max": "none", "src": "-", "why": "an inductor: no voltage rating to "
                                                     "ground, its limits are current (M14)"},
        "TP": {"max": "none", "src": "-", "why": "a bare test pad, not a part"},
    }
    d.update({v: r0402 for v in resistors})
    return d



# The pogo pin is rated a nominal 24 V and a board that passes the raw input through one
# runs it at the supply's top tolerance, 3 % over. Accepted by the user, for that voltage
# and no more: a board whose pin carries the input passes this to pin_volts().
POGO_24V_ACCEPTED = {
    "v": V24_MAX, "by": "user", "date": "2026-10-06",
    "why": "\"If it's rated 24V it seems likely it could handle a 3% increase\": a nominal "
           "24 V rating on a nominal 24 V supply at the top of its +-3 % (24.72 V), on "
           "single pins standing on lands more than 2 mm apart"}
