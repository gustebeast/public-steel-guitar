"""JOINERY PLATE 6: closing the visible seam on a nozzle/nozzle joint.

    py -3.12 -m src.test.fit_plate6            # every pair's dims, corners, overhangs, walls, gap
    py -3.12 -m src.test.fit_plate6 --export   # ...and write src/test/test_plate6_petg_gf.step

The user (2026-10-15): nn shows a fairly noticeable seam on the side where the halves meet,
and on the instrument that is the FRONT face. The even-clearance rule stood the socket's
seat c off the host, so the seam is a c-wide line (plus each half's nozzle-made outer edge
printing ~2.0 round). Only the tenon's root fillet needs c at the seat: the socket keeps
it there as a pocket (c - g deep, as wide as the fillet runs) and the rest of its face
comes down to g. On a NOZZLE-made socket that pocket prints as drawn at any depth; on a
layer-made one it would round to whole 0.4 layers.

nn at its long-joint c (0.35) with the seat 0.35 (plate 4's, for comparison) / 0.15 / 0.05.
"""
from __future__ import annotations

import sys

from . import fit_plate2 as P2

TAG = "p6"

PAIRS = [
    ("nn", "N", "N", (0.35, 0.35, 0.35), {"seat": (0.35, 0.15, 0.05)}),
]


def plate():
    return P2.plate(PAIRS, TAG)


def main(argv=None):
    return P2.main(argv, PAIRS, TAG, "test_plate6_petg_gf.step")


if __name__ == "__main__":
    sys.exit(main())
