"""JOINERY PLATE 8 (step 2): every BENCH-TEST joint at its instrument size, as short coupons.

    py -3.12 -m src.test.fit_plate8            # every pair's dims, corners, overhangs, walls, gap
    py -3.12 -m src.test.fit_plate8 --export   # ...and write src/test/test_plate8_petg_gf.step

STEP 1 CLOSED (plates 2-7, the user, 2026-10-15): the plate-2 profile per print pair, with
these long-joint clearances -- nozzle tenon / layer socket 0.30, nozzle / nozzle 0.35, layer
/ layer standing 0.20 (tip cut flat, root chamfer), layer / layer mouth-up 0.25.

SCOPE (the user): every joint with a half on a bench-test part (endplates, chassis sections,
pulleys, nut slide inserts) -- BOTH halves, because a bench part that passes becomes the
instrument's part and the lever, deck and adapter attach to it later. Sites too small for the
quality joint were grown (user, 2026-10-16). Steps run from the step-1 pick LOOSER only (the
user: err loose, so a joint that prints tight still installs).

  A  knee-lever tenon -> chassis rib mortise    layer / layer, standing   head 5.6 (room 6.6 x 8.6)
  B  deck tongue -> chassis rail-top groove     layer / layer, mouth up   head 6.4 (room 6.4 x 6.4)
  C  chassis rail end -> either endplate        nozzle tenon / layer socket, mouth up, the
                                                endplate's 0.4 assembly air as its seat
  D  chassis segment seam                       nozzle / nozzle, the faces MEET (seat 0: the
                                                pocket keeps c over the root fillet only)

The body-adapter ridge shares A's mortise, so it takes A's profile (printed layer-made). Still
to come: the ridge in the ENDPLATE grooves (a socket mouth sideways to the layers, never
printed) and the nut slide insert (a straight pocket, best as a slice of the real keyhead).
"""
from __future__ import annotations

import sys

from src import chassis as CH
from . import fit_plate2 as P2

TAG = "p8"
B = P2.BEAD

LEVER = {"neck": 4 * B, "head": 7 * B, "side": 2 * B, "root": True, "trunc": 1.2}
DECK = {"neck": 4 * B, "head": 8 * B, "side": 3 * B}


def _from(pick):
    """The step-1 pick and two looser steps."""
    return tuple(round(pick + k * 0.05, 2) for k in range(3))


PAIRS = [
    ("lever", "up", "up", _from(0.20), {"lead": P2.LEAD, "relief": "socket", "size": LEVER}),
    ("deck", "up", "down", _from(0.25), {"lead": P2.LEAD, "relief": "socket", "size": DECK}),
    ("rail_end", "N", "down", _from(CH.KH_DT_CLR),
     {"lead": P2.LEAD, "relief": "socket", "seat": (CH.EP_TOP_CLR,) * 3, "row": 1}),
    ("seam", "N", "N", _from(CH._SEG_CLR), {"seat": (0.0,) * 3, "row": 1}),
]


def plate():
    return P2.plate(PAIRS, TAG)


def main(argv=None):
    return P2.main(argv, PAIRS, TAG, "test_plate8_petg_gf.step")


if __name__ == "__main__":
    sys.exit(main())
