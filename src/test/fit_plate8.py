"""JOINERY PLATE 8 (step 2): the BENCH-TEST joints whose real section is bigger than step 1's.

    py -3.12 -m src.test.fit_plate8            # every pair's dims, corners, overhangs, walls, gap
    py -3.12 -m src.test.fit_plate8 --export   # ...and write src/test/test_plate8_petg_gf.step

STEP 1 CLOSED (plates 2-7, the user, 2026-10-15): the plate-2 profile per print pair, with
these long-joint clearances -- nozzle tenon / layer socket 0.30, nozzle / nozzle 0.35, layer
/ layer standing 0.20 (tip cut flat, root chamfer), layer / layer mouth-up 0.25.

SCOPE (the user): only joints with a half on a bench-test part (endplates, chassis
sections, pulleys, nut slide inserts). The instrument's own clearance constants are
ignored: they were never printed. Steps run from the step-1 pick LOOSER only (the user:
err loose, so a joint that prints tight still installs).

  A  knee-lever housing -> chassis rib mortise  layer / layer, standing   (room 6.6 wide, 8.6 deep)
  B  deck tongue -> chassis rail-top groove     layer / layer, mouth up   (room 6.4 wide, 6.4 deep)

NOT HERE, because the step-1 MINIMUM already fills (or overfills) the site, so its coupon
would repeat a step-1 one: every site whose tenon is nozzle-made (body-adapter ridge, the
two chassis rail ends, the chassis seam). Their 2.0 corners make the smallest joint 8.0 to
9.6 deep, against 8.0 or less of room. Also still to come: the adapter ridge in the ENDPLATE
grooves (that socket's mouth faces sideways to the layers, never printed) and the nut slide
insert (a straight prismatic pocket, best tested as a slice of the real keyhead).
"""
from __future__ import annotations

import sys

from . import fit_plate2 as P2

TAG = "p8"
B = P2.BEAD

LEVER = {"neck": 4 * B, "head": 7 * B, "side": 2 * B, "root": True, "trunc": 1.2}
DECK = {"neck": 4 * B, "head": 8 * B, "side": 3 * B}

PAIRS = [
    ("lever", "up", "up", (0.20, 0.25, 0.30), {"lead": P2.LEAD, "relief": "socket", "size": LEVER}),
    ("deck", "up", "down", (0.25, 0.30, 0.35), {"lead": P2.LEAD, "relief": "socket", "size": DECK}),
]


def plate():
    return P2.plate(PAIRS, TAG)


def main(argv=None):
    return P2.main(argv, PAIRS, TAG, "test_plate8_petg_gf.step")


if __name__ == "__main__":
    sys.exit(main())
