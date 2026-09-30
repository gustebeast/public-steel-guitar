"""FLOATING MATERIAL: points on a part that the printer is asked to start in mid-air.

  py -3.12 -m tools.check_floating                 # every part that declares an up
  py -3.12 -m tools.check_floating --only fixed_tenon
  py -3.12 -m tools.check_floating --min-height 1.0

WHY THIS EXISTS, AND WHY `check_ceilings` CANNOT DO IT. That checker tests FACE
NORMALS: a flat roof is a planar face pointing down the build axis, and finding it
that way is what keeps legal 45 degree flanks out of the report. But put two such
cavities SIDE BY SIDE and the material caught between them comes to a point, and
under that point is air. Both flanks are 45 and both are individually legal. There
is no downward-facing face at all -- only the LINE where the two meet. A face-based
checker is blind to it by construction, not by oversight, and the ones in this model
were found by a human looking at the viewer (user: "it's material that's fully
floating in the air with nothing underneath to support it").

So this checker works on the SOLID, not on its faces, and it samples EDGES, because
an edge is exactly where this defect lives: the lowest material of a V valley is the
line two flanks share. (Face interiors are `check_ceilings`' half of the job; the two
together are the cover.)

THE TEST IS A RING, NOT A POINT, and that distinction is the whole tool. Drop one
layer straight down from a sample and ask "is there material here": on a plain 45
degree overhang the answer is NO, because the wall has receded by one layer's worth
-- so a point probe condemns the very geometry this project relies on. What the
printer actually needs is material SOMEWHERE WITHIN REACH below: at 45 degrees that
is one layer out horizontally. So the probe is a ring of radius `layer * tan(angle)`
about the point one layer down, plus its centre, and a sample is floating only when
NOTHING in that ring is inside the solid.

That makes the threshold honest and adjustable: `--angle 45` passes anything a
45 degree rule passes, and the V valleys still fail it, because one layer under a
wedge's tip there is no material in ANY direction.

EVERY FAILING SITE IS THEN MEASURED, by widening the ring until it does find
material -- and WHICH WAY the material lies is what the measurement is for, not how
far. Past about 60 degrees the "supporting" material is a whole millimetre to one
side, and at 87 it is nearly four, which is no longer an overhang in any useful
sense. What matters then is whether the layer below has material on BOTH SIDES:

  BRIDGED    two hits in opposing directions. The slicer spans the gap between two
             anchors. It may sag, and the span is the number that decides; this is
             the same population `check_ceilings` reports as flat ceilings, and a
             teardrop's one-bead apex cap lands here.
  CANTILEVER hits on ONE side only. Material reaching out over air with a single
             root -- it droops, and nothing catches it.
  FLOATING   nothing in any direction, out to ten layers. Material that BEGINS in
             mid-air: the V valley between two adjacent cavities, which has no
             downward-facing face for a normal-based checker to find, and which is
             the reason this tool exists.

Sorting these three apart is the difference between a report you act on and a list
of coordinates. They want completely different fixes.

AND EVERY SITE IS MEASURED FOR AREA, because the angle alone ranks badly. The angle
says how far the support is; it says nothing about HOW MUCH is hanging, so a 0.10
mm^2 whisker where two walls meet in a shallow edge and a 1405 mm^2 shelf that will
certainly droop print identically in an angle-only report. Both were in this model
at once, both read "cantilever at 75-87 deg", and I ranked them the same and was
wrong about both (user found the whisker by eye after the report had called much
worse things by the same name).

So the area is measured the way a slicer would see it: the site's own samples give a
window, and inside that window the solid is SLICED at the layers the site spans. In
each slice every cell of material is asked the same ring question, and the cells
with no answer are the unsupported area. That is a direct measurement of the thing
that matters -- the footprint the nozzle is asked to lay over air -- rather than an
inference from where the geometry happened to put an edge.

Points WITHIN ONE LAYER OF THE BED are skipped: the plate is under them.

ADVISORY, like `check_ceilings`: a floating sample high inside a blind cavity may
only mean a whisker of droop nobody will ever see, and this tool will not judge that
for you. It prints where and how big, and you look.
"""

from __future__ import annotations

import argparse
import math

from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN, TopAbs_ON

# The registry, the declared build directions and the bed derivation all come from
# check_ceilings: there is ONE record of which way a part prints (src/leg_stack.py's
# PRINT ORIENTATION block), and a second checker must not start a second copy of it.
from tools.check_ceilings import PARTS, _dot, _frame, bed_plane

LAYER = 0.2                     # nominal layer height; the angle rule scales with it


def _classifier(shape):
    cls = BRepClass3d_SolidClassifier(shape.wrapped)

    def inside(p):
        cls.Perform(gp_Pnt(*p), 1e-7)
        return cls.State() in (TopAbs_IN, TopAbs_ON)

    return inside


def _ring(layer, angle, n):
    r = layer * math.tan(math.radians(angle)) * 1.02     # 2% slack: at exactly 45 the
    return [(math.cos(2 * math.pi * i / n) * r,          # probe lands ON the flank
             math.sin(2 * math.pi * i / n) * r) for i in range(n)]


# the angles a failing sample is re-probed at, to say HOW unsupported it is
PROBE = (50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 84.0, 87.0)

FLOATING, CANTILEVER, BRIDGED = "FLOATING", "cantilever", "bridged"
RANK = {FLOATING: 0, CANTILEVER: 1, BRIDGED: 2}      # worst first


def floating(part, up, bed, layer=LAYER, angle=45.0, samples=9, ring=8):
    """Samples on `part`'s edges with no material within reach one layer below.

    Returns [(height above the bed, point, angle needed, kind)], unclustered. `kind`
    is FLOATING / CANTILEVER / BRIDGED; the angle is None when nothing was found."""
    shape = part.val() if hasattr(part, "val") else part
    inside = _classifier(shape)
    fa, fb = _frame(up)
    ring_pts = _ring(layer, angle, ring)
    wider = [(a, _ring(layer, a, ring * 2)) for a in PROBE if a > angle]
    hits = []
    for e in shape.Edges():
        try:
            pts = [e.positionAt(i / float(samples - 1)).toTuple()
                   for i in range(samples)]
        except Exception:
            continue
        for p in pts:
            h = _dot(p, up) - bed
            if h <= layer:
                continue                                  # THE PLATE is what is under it.
            # (Not a tolerance: the bed is a PLANE under the whole part, so anything
            # within one layer of it rests on the plate wherever it sits. Skipping only
            # a hair above the bed instead reported every chamfer that leaves the bed --
            # 0.14 mm up, with its support one layer BELOW the plate.)
            q = tuple(p[k] - up[k] * layer for k in range(3))
            if inside(q):
                continue                                  # material directly under it
            def has(pts):
                return any(inside(tuple(q[k] + fa[k] * da + fb[k] * db
                                        for k in range(3))) for da, db in pts)

            if has(ring_pts):
                continue                                  # within reach at `angle`
            need, kind = None, FLOATING
            for a, pts in wider:
                dirs = [(da, db) for da, db in pts
                        if inside(tuple(q[k] + fa[k] * da + fb[k] * db
                                        for k in range(3)))]
                if dirs:
                    need = a
                    # OPPOSING hits mean the layer below reaches in from both sides:
                    # the slicer bridges between two anchors rather than hanging one
                    # end out over nothing.
                    kind = BRIDGED if any(u[0] * v[0] + u[1] * v[1] < 0.0
                                          for u in dirs for v in dirs) else CANTILEVER
                    break
            hits.append((h, p, need, kind))
    return hits


def unsupported_area(inside, pts, up, angle, layer, step=0.2, margin=1.0,
                     grid=96):
    """mm^2 of material in `pts`' neighbourhood with nothing within `angle` below it.

    `pts` are one site's failing samples; they set both the window and the layers,
    so the cost scales with the defect rather than with the part. The grid is capped
    at `grid` cells a side and the step coarsens to suit -- a wide shelf is measured
    roughly and a whisker finely, which is the right way round, because the whisker
    is the one whose SIZE is the whole question.
    """
    fa, fb = _frame(up)
    az = [_dot(p, fa) for p in pts]
    bz = [_dot(p, fb) for p in pts]
    hz = [_dot(p, up) for p in pts]
    a0, a1 = min(az) - margin, max(az) + margin
    b0, b1 = min(bz) - margin, max(bz) + margin
    step = max(step, (a1 - a0) / grid, (b1 - b0) / grid)
    ring = _ring(layer, angle, 8) + [(0.0, 0.0)]
    na = int((a1 - a0) / step) + 1
    nb = int((b1 - b0) / step) + 1
    n_layers = int(round((max(hz) - min(hz)) / layer)) + 1
    area = 0.0
    for li in range(n_layers):
        h = min(hz) + li * layer
        for ia in range(na):
            a = a0 + ia * step
            for ib in range(nb):
                b = b0 + ib * step
                q = tuple(fa[k] * a + fb[k] * b + up[k] * h for k in range(3))
                if not inside(q):
                    continue
                d = tuple(q[k] - up[k] * layer for k in range(3))
                if not any(inside(tuple(d[k] + fa[k] * da + fb[k] * db
                                        for k in range(3))) for da, db in ring):
                    area += step * step
    return area


def cluster(hits, radius=2.0):
    """One entry per SITE. A floating edge yields a sample every 1/8 of its length, and
    a V valley is one defect however many samples fall on it.

    SINGLE LINKAGE, and it has to be: a new sample joins a site when it is within
    `radius` of ANY sample already in it, not just of the first one. Comparing against
    the first alone chops a long valley into `radius`-sized pieces -- pedal_bar_a came
    out as 102 sites that way -- and once the area is being measured that is not merely
    untidy, it is wrong, because each piece is then measured in its own little window
    and a wide shelf reports as a crowd of small ones.
    """
    sites = []          # [[pts], lo, need, kind]
    for h, p, need, kind in sorted(hits, key=lambda x: (x[0], x[1])):
        near = [i for i in range(len(sites))
                if any(math.dist(p, q) < radius for q in sites[i][0])]
        if not near:
            sites.append([[p], h, need, kind])
            continue
        # the LOWEST index keeps the site, so popping the others cannot move it
        keep = sites[near[0]]
        keep[0].append(p)
        for i in reversed(near[1:]):            # this sample BRIDGES sites: one now
            o = sites.pop(i)
            keep[0].extend(o[0])
            keep[1] = min(keep[1], o[1])
            keep[2] = (None if (keep[2] is None or o[2] is None)
                       else max(keep[2], o[2]))
            if RANK[o[3]] < RANK[keep[3]]:
                keep[3] = o[3]
        # the SITE takes its WORST sample: one floating point in a cluster is the
        # defect, however many of its neighbours are merely steep
        keep[1] = min(keep[1], h)
        keep[2] = None if (keep[2] is None or need is None) else max(keep[2], need)
        if RANK[kind] < RANK[keep[3]]:
            keep[3] = kind
    return [(pts, pts[0], lo, need, kind) for pts, lo, need, kind in sites]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated part names")
    ap.add_argument("--angle", type=float, default=45.0,
                    help="the overhang rule to hold parts to (default 45)")
    ap.add_argument("--layer", type=float, default=LAYER)
    ap.add_argument("--min-height", type=float, default=0.0,
                    help="ignore sites less than this far above the bed")
    ap.add_argument("--floating-only", action="store_true",
                    help="drop the BRIDGED sites -- leave what droops or floats")
    ap.add_argument("--min-area", type=float, default=0.0,
                    help="ignore sites with less unsupported area than this (mm^2)")
    ap.add_argument("--no-area", action="store_true",
                    help="skip the area measurement (the slow half of the run)")
    a = ap.parse_args()

    names = list(PARTS)
    if a.only:
        want = {s.strip() for s in a.only.split(",")}
        names = [n for n in names if n in want]

    total = 0
    for nm in names:
        build, up, bed, _ = PARTS[nm]
        part = build()
        if bed is None:
            bed = bed_plane(part, up)
        hits = [x for x in floating(part, up, bed, layer=a.layer, angle=a.angle)
                if x[0] >= a.min_height]
        if a.floating_only:
            hits = [x for x in hits if x[3] != BRIDGED]
        sites = cluster(hits)
        inside = _classifier(part.val() if hasattr(part, "val") else part)
        sites = [(pts, q, lo, w, k,
                  0.0 if a.no_area else
                  unsupported_area(inside, pts, up, a.angle, a.layer))
                 for pts, q, lo, w, k in sites]
        shown = [x for x in sites if a.no_area or x[5] >= a.min_area]
        print("%-22s build up (%+.2f,%+.2f,%+.2f) : %d site(s), %d sample(s) with "
              "nothing within %.0f deg below%s"
              % (nm, up[0], up[1], up[2], len(sites), len(hits), a.angle,
                 "" if len(shown) == len(sites) else
                 "   (%d under --min-area %.2f, not shown)"
                 % (len(sites) - len(shown), a.min_area)))
        # AREA FIRST, angle second: the area is what decides whether a site is worth
        # touching, and the angle only says which fix it wants.
        for pts, p, h, need, kind, ar in sorted(
                shown, key=lambda s: (RANK[s[4]], -s[5])):
            print("    %-10s %8.2f mm^2  %-11s %2d sample(s) at "
                  "(%.2f, %.2f, %.2f)  %.2f above bed"
                  % (kind, ar, "" if need is None else "support at %.0f deg" % need,
                     len(pts), p[0], p[1], p[2], h))
        total += len(sites)
    if not total:
        print("\nno floating material: every sampled edge has support within "
              "%.0f degrees." % a.angle)
    return 0        # advisory, like check_ceilings -- severity is a judgement call


if __name__ == "__main__":
    raise SystemExit(main())
