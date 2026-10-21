"""JOINERY PLATE 10: the chassis seam joint at its FULL instrument length, one tenon a step.

    py -3.12 -m src.test.fit_plate10            # every step's dims, corners, overhangs, gap
    py -3.12 -m src.test.fit_plate10 --export   # ...and write src/test/test_plate10_petg_gf.step

Why (user, 2026-10-21): the seam at c 0.40 bound "much too tight" on two round-5 stubs whose
geometry is round 2's (0.40, "a touch loose") to the vertex, and fit_plate9 moved the lever
pair from plate 8's 0.20 (12 long) to 0.35 at its full 34.9. Plate 8's family D, unchanged but
for the length -- the seam's whole drop, _SEG_JZ1 - _SEG_JZ0 -- from 0.40 (the control) up.
"""
from __future__ import annotations

import sys

from src import chassis as CH
from . import fit_plate2 as P2
from . import fit_plate9 as P9

TAG = "p10"
L_FULL = CH._SEG_JZ1 - CH._SEG_JZ0

PAIRS = [
    ("seam", "N", "N", (0.40, 0.45, 0.50, 0.55), {"seat": (0.0,) * 4}),
]


def _full_length(fn):
    def run(*a, **k):
        keep, P9.L_FULL = P9.L_FULL, L_FULL
        try:
            return P9._full_length(fn)(*a, **k)
        finally:
            P9.L_FULL = keep
    return run


@_full_length
def plate():
    return P2.plate(PAIRS, TAG)


@_full_length
def main(argv=None):
    return P2.main(argv, PAIRS, TAG, "test_plate10_petg_gf.step")


if __name__ == "__main__":
    sys.exit(main())
