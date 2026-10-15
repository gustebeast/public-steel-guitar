"""JOINERY PLATE 4: the layer/layer ends, and nozzle/nozzle's fine step.

    py -3.12 -m src.test.fit_plate4            # every pair's dims, corners, overhangs, walls, gap
    py -3.12 -m src.test.fit_plate4 --export   # ...and write src/test/test_plate4_petg_gf.step

WHAT PLATE 3 TAUGHT (the user's fingers and calipers, 2026-10-15, PETG-GF):
  the matrix   long-joint c: layer/layer 0.25, any nozzle-made half +0.05 (it slides
               ACROSS its layers: the friction is texture, the wobble is size); A 0.35 good.
  ends         C and D still tight at entry and seated with plate 3's lead-in (0.2, gone by
               1.6). A D2 head, drawn 3.20, read 2.6 at the tip, 3.33 about 3 mm in, 3.1 in
               the middle: an hourglass, the bulge past where that lead-in ended.
  nn           0.30 too tight, 0.35 a touch loose, very even.

SO THIS PLATE:
  ll_standing, ll_mouth_up   0.15-0.25 again with fit_plate2.LEAD: 0.12 a side off from
                             the tip to 3 mm, gone by 4.5 -- under the bulge
  nn                         0.30 / 0.325 / 0.35
"""
from __future__ import annotations

import sys

from . import fit_plate2 as P2

TAG = "p4"
RELIEF = {"lead": P2.LEAD}

PAIRS = [
    ("ll_standing", "up", "up", (0.15, 0.20, 0.25), RELIEF),
    ("ll_mouth_up", "up", "down", (0.15, 0.20, 0.25), RELIEF),
    ("nn", "N", "N", (0.30, 0.325, 0.35)),
]


def plate():
    return P2.plate(PAIRS, TAG)


def main(argv=None):
    return P2.main(argv, PAIRS, TAG, "test_plate4_petg_gf.step")


if __name__ == "__main__":
    sys.exit(main())
