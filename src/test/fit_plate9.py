"""JOINERY PLATE 9: the knee-lever mount joint at its FULL instrument length, one tenon a step.

    py -3.12 -m src.test.fit_plate9            # every step's dims, corners, overhangs, gap
    py -3.12 -m src.test.fit_plate9 --export   # ...and write src/test/test_plate9_petg_gf.step

Why (user, 2026-10-21): the 8-tenon bench rounds bound at c 0.275 -- "I can get a lubricated
single knee tenon to slide but even just two starts to bind right away". Plates 2-8 picked the
standing layer/layer pair's clearance on 12-long coupons (fit_finder.L); a housing's tenons are
the full TEN_Y1 - TEN_Y0. This is plate 8's family A, unchanged but for that length, stepped
from the clearance that just failed (0.275, the instrument's own) looser. One tenon per step,
so it answers the clearance alone; bench_joinery's r5_lever2 / r5_floor2 ask about the pitch.
NB plate 8's pairs (and these) carry the seat at c; the instrument's lever pair had it at 0.
"""
from __future__ import annotations

import sys

from src import dimensions as D
from src import knee_lever as KL
from . import fit_finder as F
from . import fit_plate2 as P2

TAG = "p9"
L_FULL = KL.TEN_Y1 - KL.TEN_Y0          # 34.9: the housing's own tenon length

PAIRS = [
    ("lever", "up", "up", (0.275, 0.35, 0.45),
     {"lead": P2.LEAD, "relief": "socket", "size": D.LEVER_FIT}),
]


_mark_size = P2.mark_size


def _mark_12(face_w, widest):
    """The step numbers sized as on every other plate (on a 12-long face): sized on the long
    face they grow until cut_mark draws nothing."""
    keep, F.L = F.L, 12.0
    try:
        return _mark_size(face_w, widest)
    finally:
        F.L = keep


def _full_length(fn):
    def run(*a, **k):
        keep, F.L, P2.mark_size = F.L, L_FULL, _mark_12
        try:
            return fn(*a, **k)
        finally:
            F.L, P2.mark_size = keep, _mark_size
    return run


@_full_length
def plate():
    return P2.plate(PAIRS, TAG)


@_full_length
def main(argv=None):
    return P2.main(argv, PAIRS, TAG, "test_plate9_petg_gf.step")


if __name__ == "__main__":
    sys.exit(main())
