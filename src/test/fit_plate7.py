"""JOINERY PLATE 7: the standing layer/layer pair, shortened clear of its socket's roof.

    py -3.12 -m src.test.fit_plate7            # every pair's dims, corners, overhangs, walls, gap
    py -3.12 -m src.test.fit_plate7 --export   # ...and write src/test/test_plate7_petg_gf.step

WHAT PLATE 6 TAUGHT (the user, 2026-10-15, PETG-GF):
  mouth-up   SETTLED: head 4.8, straight sides 2.4, neck 2.4, socket-only end relief,
             0.25 for a long joint (a hair loose short).
  standing   still uneven with the tip cut 0.4 below its peak: the socket's bridged roof
             hangs down further at one spot and grips there. And the tenon stood 8.4 tall
             on a 4.8 head -- the user: shorten it toward round.

  and      the mouth-up socket's flat cavity end (a LAYER face) had been relieved too:
             a layer deeper at the joint's ends, visible in the slicer (fixed).

SO THIS PLATE: A the standing pair with straight sides 1.6 (two beads, still stair-free) and
its tip cut flat 1.2 below the peak (~6.4 tall, the flat top three times further under the
roof), socket-only end relief, root chamfer, 0.15 / 0.20 / 0.25; B the mouth-up pair again
with its cavity end flat, 0.15 / 0.20 / 0.25.
"""
from __future__ import annotations

import sys

from . import fit_plate2 as P2

TAG = "p7"
SIZE = {"neck": 3 * P2.BEAD, "head": 6 * P2.BEAD, "side": 2 * P2.BEAD, "root": True, "trunc": 1.2}

MOUTH_UP = {"neck": 3 * P2.BEAD, "head": 6 * P2.BEAD, "side": 3 * P2.BEAD}

PAIRS = [
    ("standing", "up", "up", (0.15, 0.20, 0.25), {"lead": P2.LEAD, "relief": "socket", "size": SIZE}),
    ("mouth_up", "up", "down", (0.15, 0.20, 0.25), {"lead": P2.LEAD, "relief": "socket", "size": MOUTH_UP}),
]


def plate():
    return P2.plate(PAIRS, TAG)


def main(argv=None):
    return P2.main(argv, PAIRS, TAG, "test_plate7_petg_gf.step")


if __name__ == "__main__":
    sys.exit(main())
