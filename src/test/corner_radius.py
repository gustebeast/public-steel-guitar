"""CORNER RADIUS FINDER: what is the sharpest corner the printer actually makes?

    py -3.12 -m src.test.corner_radius            # the table: what each number is
    py -3.12 -m src.test.corner_radius --export   # ...and write src/test/test_corner_radius_plate.step

The user's idea (2026-10-14), before the next joint round: the same shape printed over
and over with its corners drawn at a growing radius. A drawn right angle prints with
whatever corner the nozzle leaves, so the first few should come out the SAME -- the
nozzle cannot turn tighter than its bead -- and from some radius on each is rounder
than the one before. That transition is the radius the printer reproduces as drawn:
the "print-accurate corner radius" to draw joints at.

MEASURED, NOT ONLY SEEN. Each piece is a SQUARE RING lying flat (profile on the bed, so
the nozzle makes its corners, as it does a joint's in-plane profile): an outer square
whose corners are CONVEX, which the nozzle rounds off, and a square hole whose corners
are CONCAVE, which the bead fills in. Both are drawn at the step's radius. With
calipers, across the FLATS (s) and corner to corner across the DIAGONAL (d):

    d = s * sqrt(2) - 2 * r * (sqrt(2) - 1)      so the corner it printed is
    r = (s * sqrt(2) - d) / 0.828

Every 0.1 of radius is 0.083 off the diagonal. Measure the flats on the PRINT, not the
drawing, so a part printed fat or thin all round cancels out. Plot printed r against
drawn r: flat at first (the printer's own corner), then rising along r = r -- the knee
is the answer. The outside answers for convex corners, the hole for concave ones, and
they need not agree.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import sys

import cadquery as cq

from src import dimensions as D
from src.version_mark import cut_mark

HERE = pathlib.Path(__file__).resolve().parent
RADII = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2)
OUT_S = 20 * D.BEAD          # 16.0 across the outer flats
IN_S = 10 * D.BEAD           # 8.0 across the hole's flats (inside jaws reach its corners)
T = 5 * D.BEAD               # 4.0 tall: ten 0.4 layers
GAP = 4.0                    # between pieces on the bed
PER_ROW = 5
MARK = dict(height=3.2, stroke=0.8)


def ring(r: float) -> cq.Workplane:
    """One ring, bed at z = 0, centred on the origin; every corner, in and out, at radius r."""
    def square(s, h):
        if r <= 0:
            return cq.Workplane("XY").rect(s, s).extrude(h)
        return cq.Workplane("XY").sketch().rect(s, s).vertices().fillet(r).finalize().extrude(h)
    return square(OUT_S, T).cut(square(IN_S, T + 2.0).translate((0, 0, -1.0)))


def diagonal(s: float, r: float) -> float:
    """Corner to corner across a square of flats s whose corners are radius r."""
    return s * math.sqrt(2.0) - 2.0 * r * (math.sqrt(2.0) - 1.0)


def pieces():
    """[(name, solid)]: every step's ring, numbered on its -Y wall's top, laid out on the bed."""
    out = []
    wall_mid = (OUT_S + IN_S) / 4.0                     # the middle of a wall, off the centre
    for k, r in enumerate(RADII):
        p = cut_mark(ring(r), k + 1, (0.0, -wall_mid, T), (0, 0, 1), (1, 0, 0), **MARK)
        col, row = k % PER_ROW, k // PER_ROW
        p = p.translate((col * (OUT_S + GAP), -row * (OUT_S + GAP), 0.0))
        out.append(("corner_r_%d" % (k + 1), p.val()))
    return out


def assembly(origin=(-560.0, 450.0, 160.0)):
    """[(name, Workplane)] for the scratch view: the plate as it prints."""
    return [("test_" + n, cq.Workplane("XY").newObject([s]).translate(origin)) for n, s in pieces()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", action="store_true", help="write src/test/test_corner_radius_plate.step")
    a = ap.parse_args(argv)
    print("number  drawn r   outside: flats / diagonal    hole: flats / diagonal")
    for k, r in enumerate(RADII):
        print("   %2d    %.1f       %.2f / %.3f            %.2f / %.3f" % (
            k + 1, r, OUT_S, diagonal(OUT_S, r), IN_S, diagonal(IN_S, r)))
    pl = pieces()
    bad = [n for n, s in pl if not s.isValid() or len(s.Solids()) != 1]
    print("%d pieces, %.1f cm3; %s" % (len(pl), sum(s.Volume() for _n, s in pl) / 1000.0,
                                       "every piece one valid solid" if not bad else "BAD: " + ", ".join(bad)))
    if a.export:
        from cadkit.step_export import export_step
        path = HERE / "test_corner_radius_plate.step"
        export_step(cq.Workplane("XY").newObject(
            [cq.Compound.makeCompound([s for _n, s in pl])]), str(path))
        print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
