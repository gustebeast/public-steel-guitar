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
# ⚠ THE INDUCTOR IS SUNLORD SWPA5040S3R3NT, 5 x 5 x 4 (manual quality pass M14, 2026-10-05).
# It was the 4 x 4 SWPA4030S4R7MT, whose saturation current is 2.90 A guaranteed and 3.20
# typical (Sunlord's table; a 30 % drop in inductance). TI: "the inductor saturation
# current must not be less than the device low-side current limit", which is 3.5 A
# typical, 2.9 to 4.1 (SNVSAN3F 7.5 and 9.2.2.4) -- so a shorted rail saturated it. This
# one is 3.95 A guaranteed and 4.60 typical, at 31 milliohm instead of 78; and 3.3 uH is
# the value TI's own table gives for 12 V out at 2.1 MHz (ripple 0.83 to 0.86 A at these
# boards' 11.5 and 14.5 V: 28 % of the part's 3 A, where TI asks for 20 to 40).
L1_VALUE = "SWPA5040S3R3NT"
L1_LCSC = "C305173"
L1_FP = "Inductor_SMD:L_Sunlord_SWPA5040S"
L1_DESC = ("buck output inductor, 3.3 uH +-30 % shielded, Isat 3.95 A min / 4.60 typ, "
           "DCR 31 mohm max, 5.0 x 5.0 x 4.0 (LCSC C305173)")
L1_UH, L1_ISAT = 3.3, 3.95
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
