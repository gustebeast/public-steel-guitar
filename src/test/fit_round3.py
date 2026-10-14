"""FIT FINDERS, ROUND 3: the PETG-GF to PETG-GF joints again, every corner rounded.

    py -3.12 -m src.test.fit_round3            # the table: what each number is
    py -3.12 -m src.test.fit_round3 --export   # ...and write src/test/test_fit3_plate_petg_gf.step

ROUND 2 (src/test/fit_round2.py, printed 2026-10-13 in PETG-GF) said, by feel:

  * SEAM      sharp 0.25 tight, 0.35 and 0.45 loose; ROUNDED 0.15 and 0.25 would not go
              in, 0.35 tight. Rounded wants more side clearance than sharp did.
  * ENDPLATE  sharp 0.10 and 0.15 (depth 0.50) a bit tight, 0.20 slides easily with no
              wobble; at depth 0.30 both a bit tight; ROUNDED 0.10-0.20 all a bit tight.
  * OCTAGON   0.10 too tight, 0.20 nice and low-friction with a tiny wobble, 0.40 too
              loose; 0.15 and 0.30 came off the bed (plate not clean), so untested.

The user, on reading them: the corners stay rounded -- "I want our models to more
accurately match the prints" -- and a rounded joint is tight because the shape now
meets over its whole face, so the next round steps rounded joints LOOSER until the
balance is found. Every step here is rounded (r = half a bead, fit_round2.R).

  SEAM      0.40 .. 0.60 side, depth held at 0.30 (its flat has always had room)
  ENDPLATE  1-4  0.25 .. 0.40 side at depth 0.50 (round 2: 0.30 depth was tight)
            5-6  0.30 / 0.35 side at depth 0.70: does more room under the head help?
  OCTAGON   0.15 .. 0.30 around round 2's good 0.20, at the drawn 0.60 depth. Its profile
            prints standing, so its corners are layer steps, not nozzle turns; rounded
            here so the whole family is drawn one way, and for the two lost cells.

The two-filament joints (deck, the inserts) wait for a PCTG print; round 2's PCTG plate
still stands for them. Same layout as round 2: token N beside cell N, both numbered.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import cadquery as cq

from . import fit_round2 as R2

HERE = pathlib.Path(__file__).resolve().parent
R = R2.R
STEPS = {
    "seam": [(0.40, 0.30, R), (0.45, 0.30, R), (0.50, 0.30, R), (0.55, 0.30, R), (0.60, 0.30, R)],
    "endplate": [(0.25, 0.50, R), (0.30, 0.50, R), (0.35, 0.50, R), (0.40, 0.50, R),
                 (0.30, 0.70, R), (0.35, 0.70, R)],
    "octagon": [(0.15, 0.60, R), (0.20, 0.60, R), (0.25, 0.60, R), (0.30, 0.60, R)],
}
TAG = "fit3"


def plate():
    """[(name, solid)], bed at z = 0: the three all-PETG-GF joints, each strip with its
    tokens beside it."""
    return R2.plate("petg-gf", steps=STEPS, tag=TAG, inserts=False)


def assembly(origin=(-560.0, 330.0, 160.0)):
    """[(name, Workplane)] for the scratch view: the plate as it prints."""
    return [("test_" + n, cq.Workplane("XY").newObject([s]).translate(origin)) for n, s in plate()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", action="store_true", help="write src/test/test_fit3_plate_petg_gf.step")
    a = ap.parse_args(argv)
    print("number  side / depth clearance, corners r %.1f" % R)
    for name, steps in STEPS.items():
        print(name)
        for k, (c, bc, _r) in enumerate(steps):
            print("   %d    %.2f / %.2f" % (k + 1, c, bc))
    pl = plate()
    lo = [min(getattr(s.BoundingBox(), a_) for _n, s in pl) for a_ in ("xmin", "ymin", "zmin")]
    hi = [max(getattr(s.BoundingBox(), a_) for _n, s in pl) for a_ in ("xmax", "ymax", "zmax")]
    print("plate: %d pieces, %.1f cm3, %.1f x %.1f, %.1f tall, bed at z %.2f" % (
        len(pl), sum(s.Volume() for _n, s in pl) / 1000.0,
        hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], lo[2]))
    bad = [n for n, s in pl if not s.isValid() or len(s.Solids()) != 1]
    print("every piece one valid solid" if not bad else "NOT ONE VALID SOLID: %s" % ", ".join(bad))
    if a.export:
        from cadkit.step_export import export_step
        path = HERE / "test_fit3_plate_petg_gf.step"
        export_step(cq.Workplane("XY").newObject(
            [cq.Compound.makeCompound([s for _n, s in pl])]), str(path))
        print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
