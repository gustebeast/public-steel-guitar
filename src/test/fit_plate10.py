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

import cadquery as cq

from src import chassis as CH
from . import fit_plate2 as P2
from . import fit_plate9 as P9

TAG = "p10"
L_FULL = CH._SEG_JZ1 - CH._SEG_JZ0

PAIRS = [
    ("seam", "N", "N", (0.40, 0.45, 0.50, 0.55), {"seat": (0.0,) * 4}),
]


# THE BRIM (user, 2026-10-21: "we need a brim for the tall skinny ones"): every piece stands
# 64 tall -- the tokens on a ~9 x 12 base -- so each gets BRIM_W of two-layer brim round its
# whole footprint. It is at the bed end only: insert a token TOP end first and the brim
# trails, stopping at the cell's top with the whole 64 engaged.
BRIM_W, BRIM_T = 6 * P2.BEAD, 2 * 0.2
_plate = P2.plate


def _brimmed(pairs=None, tag=TAG):
    out = []
    for n, sh in _plate(pairs, tag):
        bb = sh.BoundingBox()
        brim = cq.Solid.makeBox(bb.xlen + 2 * BRIM_W, bb.ylen + 2 * BRIM_W, BRIM_T,
                                cq.Vector(bb.xmin - BRIM_W, bb.ymin - BRIM_W, bb.zmin))
        out.append((n, sh.fuse(brim).clean()))
    return _spread(out)                 # the finder spaced bare pieces: brims would touch


def _spread(pieces):
    """Lay the brimmed pieces out again with a gap between brims (the finder's own layout
    was spaced for bare pieces)."""
    out, x = [], 0.0
    cells = [p for p in pieces if "_token_" not in p[0]]
    toks = sorted([p for p in pieces if "_token_" in p[0]],
                  key=lambda p: -p[1].BoundingBox().ymin)          # step 1 at the top (+Y)
    for n, sh in cells:
        bb = sh.BoundingBox()
        out.append((n, sh.translate(cq.Vector(x - bb.xmin, -bb.ymin, 0))))
        x += bb.xlen + GAP
    y = 0.0
    for n, sh in reversed(toks):                                     # bottom row first
        bb = sh.BoundingBox()
        out.append((n, sh.translate(cq.Vector(x - bb.xmin, y - bb.ymin, 0))))
        y += bb.ylen + GAP
    return out


GAP = 2.0


def _full_length(fn):
    def run(*a, **k):
        keep, P9.L_FULL, P2.plate = P9.L_FULL, L_FULL, _brimmed
        try:
            return P9._full_length(fn)(*a, **k)
        finally:
            P9.L_FULL, P2.plate = keep, _plate
    return run


@_full_length
def plate():
    return _brimmed(PAIRS, TAG)


@_full_length
def main(argv=None):
    return P2.main(argv, PAIRS, TAG, "test_plate10_petg_gf.step")


if __name__ == "__main__":
    sys.exit(main())
