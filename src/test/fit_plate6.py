"""JOINERY PLATE 6: the layer/layer pairs with plate 5's lessons in.

    py -3.12 -m src.test.fit_plate6            # every pair's dims, corners, overhangs, walls, gap
    py -3.12 -m src.test.fit_plate6 --export   # ...and write src/test/test_plate6_petg_gf.step

WHAT PLATE 5 TAUGHT (the user, 2026-10-15, PETG-GF, head 4.8 / straight sides 2.4 / neck 2.4):
  relief     of none / tenon / socket / both, SOCKET-only (C) ran best: the reference.
  standing   the tenon tip bound in the socket's bridged, stair-stepped peak (sanded off:
             even); then the base rocked in the mouth chamfer's air (~0.47).
  mouth-up   a socket relief that cut the SEAT face left a one-layer island on each lip
             (fixed: the relief never touches the seat outside the mouth).
  seam       the seat gap does not change how the seam looks: seat stays c.

SO THIS PLATE, 0.15 / 0.20 / 0.25 each, end relief on the socket only:
  A  standing   tip cut flat 0.4 below its peak; a 45 degree ROOT chamfer on the tenon
                matching the socket's mouth (a layer-made root corner is ~1.0, so the
                sharp-vs-round bed edge costs little), closing the base's air
  B  mouth-up   as plate 5, the seat now flat
"""
from __future__ import annotations

import sys

from . import fit_plate2 as P2

TAG = "p6"
SIZE = {"neck": 3 * P2.BEAD, "head": 6 * P2.BEAD, "side": 3 * P2.BEAD}
STEPS = (0.15, 0.20, 0.25)

PAIRS = [
    ("standing", "up", "up", STEPS,
     {"lead": P2.LEAD, "relief": "socket", "size": dict(SIZE, root=True, trunc=0.4)}),
    ("mouth_up", "up", "down", STEPS, {"lead": P2.LEAD, "relief": "socket", "size": SIZE}),
]


def plate():
    return P2.plate(PAIRS, TAG)


def main(argv=None):
    return P2.main(argv, PAIRS, TAG, "test_plate6_petg_gf.step")


if __name__ == "__main__":
    sys.exit(main())
