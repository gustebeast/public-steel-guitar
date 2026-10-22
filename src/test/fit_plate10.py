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


# THE BRIM (user, 2026-10-21: "we need a brim for the tall skinny ones" -- then: they "fuse
# everything together" and "block one side from being inserted"). Every piece stands 64 tall,
# so each gets BRIM_W of two-layer brim -- but ONLY where no mate ever goes, so either end
# of a token still goes into either end of its cell:
#   a cell: its back (-X) and its two ends, never the +X face it opens on (nor under it --
#     it runs through the bed: the finder's strip skin that closed it is gone, see _cells);
#   a token: its back (+X, behind the foot) and its sides, from the host's front face back --
#     never round the tenon, which stands -X of that face.
# Pieces sit GAP apart brim to brim, each its own solid.
BRIM_W, BRIM_T = 6 * P2.BEAD, 2 * 0.2
GAP = 4.0
_plate = P2.plate


def _front_x(sh):
    """A token's host front face: the least x where its mid-height section is full width."""
    bb = sh.BoundingBox()
    z = bb.zmin + bb.zlen / 2.0
    x = bb.xmin
    while x < bb.xmax:
        a = sh.intersect(cq.Solid.makeBox(0.1, bb.ylen, 0.05, cq.Vector(x, bb.ymin, z))).Volume()
        if a >= 0.99 * 0.1 * bb.ylen * 0.05:
            return x
        x += 0.1
    raise ValueError("no full-width section: not a token")


def _brim(sh, x0, x1):
    """The ring of brim round `sh`'s footprint between x0 and x1 (open toward the joint)."""
    bb = sh.BoundingBox()
    ring = cq.Solid.makeBox(x1 - x0, bb.ylen + 2 * BRIM_W, BRIM_T,
                            cq.Vector(x0, bb.ymin - BRIM_W, bb.zmin))
    return ring.cut(cq.Solid.makeBox(bb.xlen, bb.ylen, BRIM_T + 1.0,
                                     cq.Vector(bb.xmin, bb.ymin, bb.zmin - 0.5)))


def _cells(sh, skin=1.0):
    """The finder's cell strip as SEPARATE cells (user: the brims "fuse everything together"):
    above its bed skin it is already one block per cell, joined only by that skin, which also
    closed every cell's bed end. Each cell is its block with its own section carried straight
    down to the bed, so a token goes into either end. Ordered by Y, step 1 (top) first."""
    bb = sh.BoundingBox()
    z = bb.zmin + 2.0
    sec = sh.intersect(cq.Solid.makeBox(bb.xlen + 2, bb.ylen + 2, 0.01,
                                        cq.Vector(bb.xmin - 1, bb.ymin - 1, z)))
    up = sh.intersect(cq.Solid.makeBox(bb.xlen + 2, bb.ylen + 2, bb.zlen,
                                       cq.Vector(bb.xmin - 1, bb.ymin - 1, bb.zmin + skin)))
    out = []
    for blk in up.Solids():
        q = blk.BoundingBox()
        faces = [f for f in sec.Faces() if f.normalAt().z < -0.9
                 and q.ymin - 1e-6 <= f.Center().y <= q.ymax + 1e-6]
        cell = blk
        for f in faces:
            col = cq.Solid.extrudeLinear(f.translate(cq.Vector(0, 0, bb.zmin - z)),
                                         cq.Vector(0, 0, skin + 0.01))
            cell = cell.fuse(col)
        cell = cell.clean()
        assert len(cell.Solids()) == 1, "a cell came out in pieces"
        out.append(cell)
    out.sort(key=lambda c: -c.BoundingBox().ymin)
    assert len(out) == len(PAIRS[0][3]), "%d cells for %d steps" % (len(out), len(PAIRS[0][3]))
    return out


def _brimmed(pairs=None, tag=TAG):
    """Each cell beside its own token, one row a step, step 1 at the top (+Y); every piece its
    own solid on its own brim, GAP clear of the next."""
    pcs = _plate(pairs, tag)
    strip = [sh for n, sh in pcs if "_token_" not in n]
    assert len(strip) == 1, "expected one cell strip"
    cells = _cells(strip[0])
    toks = sorted([(n, sh) for n, sh in pcs if "_token_" in n], key=lambda p: p[0])   # 1, 2, ...
    out, y = [], 0.0
    rows = []
    for k, (cell, (tn, tok)) in enumerate(zip(cells, toks), 1):
        cb, tb = cell.BoundingBox(), tok.BoundingBox()
        cell = cell.fuse(_brim(cell, cb.xmin - BRIM_W, cb.xmax)).clean()
        tok = tok.fuse(_brim(tok, _front_x(tok), tb.xmax + BRIM_W)).clean()
        rows.append((k, cell, tn, tok))
    for k, cell, tn, tok in reversed(rows):                  # the last step at the front
        cb = cell.BoundingBox()
        cell = cell.translate(cq.Vector(-cb.xmin, y - cb.ymin, 0))
        x = cell.BoundingBox().xmax + GAP
        tb = tok.BoundingBox()
        tok = tok.translate(cq.Vector(x - tb.xmin, y - tb.ymin, 0))
        out += [("%s_seam_cell_%d" % (tag, k), cell), (tn, tok)]
        y += max(cell.BoundingBox().ylen, tok.BoundingBox().ylen) + GAP
    return out


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
