"""JOINERY PLATE 5: the layer/layer pair at a size that locates on smooth faces.

    py -3.12 -m src.test.fit_plate5            # every pair's dims, corners, overhangs, walls, gap
    py -3.12 -m src.test.fit_plate5 --export   # ...and write src/test/test_plate5_petg_gf.step

WHAT PLATE 4 TAUGHT (the user, 2026-10-15, PETG-GF):
  end relief   fit_plate2.LEAD took the tight start and end out of C and D.
  but          C stayed inconsistent along the travel (worn in: easier, then wobbly); D2
               fitted well but may be luck. At 0.4 layers a 45 degree face stairs ~0.14,
               the clearance's own size, and the 3.2 head located mostly on those stairs.
               The user: C and D share ONE minimum, and it has to grow.
  nn           0.30 short, 0.35 long; its 0.325 was tighter than both -- steps under ~0.05
               are below the print's repeatability.

SO THIS PLATE: C and D again, head 4.8 wide with straight sides >= 2.4 (stair-free on a
layer-made half) to locate on, neck 2.4, the same end relief, 0.15 / 0.20 / 0.25.

AND THE SEAM: the user saw a fairly noticeable seam on nn where the halves meet -- on the
instrument, the FRONT face. The even-clearance rule stood the socket's seat c off the host,
so the seam is a c-wide line (plus each half's nozzle-made outer edge printing ~2.0 round).
Only the tenon's root fillet needs c at the seat: the socket keeps it there as a pocket
(c - g deep, as wide as the fillet runs) and the rest of its face comes down to g. On a
NOZZLE-made socket that prints as drawn at any depth; a layer-made one rounds to 0.4 layers.
nn at its long-joint c (0.35), seat 0.35 (as before) / 0.15 / 0.05.
"""
from __future__ import annotations

import sys

from . import fit_plate2 as P2

TAG = "p5"
OPT = {"lead": P2.LEAD, "size": {"neck": 3 * P2.BEAD, "head": 6 * P2.BEAD, "side": 3 * P2.BEAD}}

PAIRS = [
    ("ll_standing", "up", "up", (0.15, 0.20, 0.25), OPT),
    ("ll_mouth_up", "up", "down", (0.15, 0.20, 0.25), OPT),
    ("nn_seat", "N", "N", (0.35, 0.35, 0.35), {"seat": (0.35, 0.15, 0.05)}),
]


def plate():
    return P2.plate(PAIRS, TAG)


def main(argv=None):
    return P2.main(argv, PAIRS, TAG, "test_plate5_petg_gf.step")


if __name__ == "__main__":
    sys.exit(main())
