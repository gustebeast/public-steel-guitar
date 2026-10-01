"""Self-test for helpers.corbel_close, on three shapes whose answer is known by hand.

  py -3.12 -m tools.check_corbel

WHY A SELF-TEST AND NOT JUST THE CEILING CHECK. check_ceilings says whether a part has
an overhang left; it cannot say whether the closure took MORE than it had to, and that
is the half of this the user asked about ("do its best to maximize material"). Both
failures are silent in a render and both were real:

  * carrying each course's BOTTOM section as its support, rather than its top, is off by
    one course -- a 45 deg gable that was already perfect came back staircased, 1.1% of
    the block gone for nothing. The gable case below is what found it.
  * extruding the section for the MATERIAL as well as for the support staircases every
    sloped face in the band whether it needed it or not.

So: a 45 deg gable must come back BIT FOR BIT, a flat roof must be cut into a corbel
arch, and a roof shallower than 45 must be trimmed back to 45 and no further.
"""

from __future__ import annotations

import cadquery as cq

from src.helpers import box_at, corbel_close

# a 40 x 40 x 20 block with a Y-prism notched out of it, given as an XZ profile
CASES = [
    ("45 deg gable, already printable", [(-10, -1), (-10, 0), (0, 10), (10, 0), (10, -1)],
     1.000, 1.000),
    ("flat roof over a 20 mm void    ", [(-10, -1), (-10, 10), (10, 10), (10, -1)],
     0.80, 0.90),
    ("30 deg roof, too shallow       ", [(-10, -1), (-10, 0), (0, 5.8), (10, 0), (10, -1)],
     0.93, 0.99),
]


def _block(profile):
    face = cq.Face.makeFromWires(cq.Wire.makePolygon(
        [cq.Vector(x, -25.0, z) for x, z in profile]
        + [cq.Vector(profile[0][0], -25.0, profile[0][1])]))
    return box_at(40, 40, 20, z=10).cut(
        cq.Workplane("XY").add(cq.Solid.extrudeLinear(face, cq.Vector(0, 50, 0))))


def main() -> int:
    bad = 0
    for name, profile, lo, hi in CASES:
        b = _block(profile)
        v0 = b.val().Volume()
        out = corbel_close(b, box_at(24, 50, 400), 0.0, 20.0, 0.8, keep_frac=0.0)
        v1, n = out.val().Volume(), len(out.val().Solids())
        frac = v1 / v0
        ok = lo - 1e-6 <= frac <= hi + 1e-6 and n == 1
        bad += not ok
        print("  %s  %8.1f -> %8.1f  %6.1f%% kept, %d solid(s)   %s"
              % (name, v0, v1, 100 * frac, n,
                 "ok" if ok else "FAIL (wanted %.0f-%.0f%%, one solid)" % (100 * lo, 100 * hi)))
    print("corbel_close: %s" % ("all three known cases hold." if not bad
                                else "%d case(s) WRONG." % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
