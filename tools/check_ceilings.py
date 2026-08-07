"""Flat-ceiling (unsupported-bridge) checker for a part in ITS print orientation.

  py -3.12 -m tools.check_ceilings                 # every registered part
  py -3.12 -m tools.check_ceilings --only leg_head
  py -3.12 -m tools.check_ceilings --min 50        # only ceilings over 50 mm^2

WHY THIS EXISTS: the overlap gate reports interpenetration and nothing else. It
cannot see a flat roof over open air, and neither can a bead-grid check -- the
leg head's finger well was a 422 mm^2 flat ceiling sitting ON the print bed and
passed every automated check we had. A human spotted it in the viewer.

WHAT COUNTS. A flat ceiling is a PLANAR face whose normal points along the build
axis, AWAY from the bed, sitting back from the part's bed plane -- i.e. material
whose underside is open air parallel to the layers. The slicer must bridge it.

WHAT DOES NOT COUNT, and this is the distinction that matters:

  * 45 degree flanks. A dovetail undercut looks like an overhang to a crude
    point-probe (material inboard, void outboard) but is self-supporting by
    construction -- that is the whole reason the joints use 45. Testing FACE
    NORMALS instead of sampled points separates the two for free: a 45 flank's
    normal is nowhere near the build axis.
  * A pocket that opens AT the bed. That is a hole from layer one, not a
    ceiling; nothing is ever printed over air.

DEPTH IS REPORTED, because it changes what a ceiling means. One at the bed plane
bridges over the plate on layer one -- the worst case, and usually a real defect.
One deep inside a blind pocket bridges over a cavity that is already there; it
may droop, and whether that matters depends on what lives in the cavity. The
tool will not decide that for you, so it prints the depth and lets you judge.

Add a part below with the axis and direction it actually prints in. Getting that
wrong makes the whole report meaningless, so state it next to the part.
"""

from __future__ import annotations

import argparse

import src.latch as LT  # noqa: F401  (imported so a bad latch datum fails loudly)
from src import legs as LG

# name -> (builder, build axis 'x'|'y'|'z', bed plane coordinate on that axis,
#          which side the bed is on: +1 if the part's bed face is at MAX coord)
PARTS = {
    # The leg head lies on its +Y face: authored +Y is world -Y once every leg
    # is placed rot 180, so that face is both the bed and the button side.
    "leg_head": (lambda: LG.leg_head(latch=True), "y", LG.SQ_W / 2, +1),
    "leg_body_stub_trrs": (LG.leg_body_stub_trrs, "y", LG.SQ_W / 2, +1),
}

AX = {"x": 0, "y": 1, "z": 2}


def ceilings(part, axis: str, bed: float, side: int, tol: float = 1e-6):
    """Planar faces normal to `axis`, facing the bed, set back from it."""
    i = AX[axis]
    out = []
    for f in part.faces().vals():
        try:
            n = f.normalAt()
        except Exception:
            continue                      # non-planar: no flat ceiling to have
        comp = (n.x, n.y, n.z)
        # normal must lie ALONG the build axis (this is what excludes 45s)
        if abs(abs(comp[i]) - 1.0) > tol:
            continue
        if any(abs(c) > tol for j, c in enumerate(comp) if j != i):
            continue
        if comp[i] * side <= 0:           # must face the bed, not away from it
            continue
        c = (f.Center().x, f.Center().y, f.Center().z)
        depth = (bed - c[i]) * side
        if depth > tol:                   # set BACK from the bed plane
            out.append((f.Area(), depth, c))
    return sorted(out, reverse=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated part names")
    ap.add_argument("--min", type=float, default=1.0,
                    help="ignore ceilings smaller than this (mm^2)")
    a = ap.parse_args()

    names = list(PARTS)
    if a.only:
        want = {s.strip() for s in a.only.split(",")}
        names = [n for n in names if n in want]

    total = 0
    for nm in names:
        build, axis, bed, side = PARTS[nm]
        found = [c for c in ceilings(build(), axis, bed, side) if c[0] >= a.min]
        area = sum(c[0] for c in found)
        print("%-22s build axis %s, bed at %+.2f : %d ceiling(s), %.1f mm^2"
              % (nm, axis.upper(), bed, len(found), area))
        for ar, depth, c in found:
            flag = "  <-- ON THE BED" if depth < 0.6 else ""
            print("    %8.1f mm^2  %6.2f mm below the bed  at (%.1f, %.1f, %.1f)%s"
                  % (ar, depth, c[0], c[1], c[2], flag))
        total += len(found)
    if not total:
        print("\nno flat ceilings above the threshold.")
    return 0        # advisory: depth decides severity, so this never gates


if __name__ == "__main__":
    raise SystemExit(main())
