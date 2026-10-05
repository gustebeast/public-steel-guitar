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
    "CVCC": (-3.295, -1.32, 90.0),
    "RFBB": (+2.115, -1.32, 90.0),
    "RFBT": (+3.295, -1.32, 270.0),
    "RFBP": (+2.115, -3.25, 270.0),
}
L1_DX = 6.535                # the inductor's centre, a 4 x 4 mm part with lands at +-1.50
L1_LAND = 1.50
SW_W = 0.50

# ── THE BULK, in a row along the cell's own axis ───────────────────────────────────────
# role -> (dx, dy, rot). Every 1206 stands ACROSS the row (rot 90: its own net's pad at
# -y, ground at +y), which is what lets one ground slab and one input slab run the length
# of the input side and take both capacitors in.
BULK = {
    "CIN_1": (-5.25, 0.0, 90.0),
    "CIN_2": (-7.85, 0.0, 90.0),
    "L1": (L1_DX, 0.0, 0.0),
    "COUT_1": (+10.20, 0.0, 90.0),
    "COUT_2": (+12.80, 0.0, 90.0),
    "COUT_HF": (+14.70, 0.0, 90.0),
}
X_MIN, X_MAX = -9.15, +15.20     # the cell's reach along its axis, copper and courtyards


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
# way. About 30 mm2 of copper 0.2 mm above the first plane, plus seven vias to the ground
# plane -- TI's own arrangement, drawn with tracks because this flow has no local pours.
#
# THE SWITCH NODE STAYS A TRACK: the one net here that radiates, never a heatsink. Out of
# the top pad (pin 12), over the right-hand ground bar, into the inductor's near land.
# THE HOT LOOPS are the two strips nearest the package, pin to capacitor pad on the part's
# own layer with no via between them. Every via named here is OUTBOARD of its capacitor.
#
# ⚠ AND THE STITCHER MUST LEAVE THE TWO PGND PINS ALONE (STITCH_EXCEPTIONS). Left to itself
# it ran pin 11's ground stub down the gap between the package and CIN_B and walled pins
# 9 and 10 off from the rest of the input net.
def copper(origin, turn, v_in="+24V", v_out=None):
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
    ]
    if v_out:
        out += [
            run(v_out, 1.00, (L1_DX + L1_LAND, -1.30), (BULK["COUT_2"][0], -1.475)),
            run("GND", 1.00, (BULK["COUT_1"][0], 1.60), (BULK["COUT_2"][0], 1.60)),
        ]
    return out


def vias(origin, turn):
    """[(net, x, y)] the ground slabs' own way down to the plane; a board adds its via size."""
    pts = [(x, 3.00) for x in (-2.60, -3.80, -5.00, -6.20, -7.40)] + [(2.90, 1.50), (3.60, 1.50)]
    return [("GND",) + at(origin, turn, x, y)[:2] for x, y in pts]


STITCH_EXCEPTIONS = ("U10.1", "U10.11")
