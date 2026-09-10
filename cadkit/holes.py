"""Print-aware HOLE cutters.

`teardrop_hole(d, length, axis_point, axis_dir, print_up)` returns a CUTTER
for a round hole whose axis runs PERPENDICULAR or OBLIQUE to the print
direction. A plain cylinder cut prints with an unsupported sagging
round ceiling; the teardrop replaces the TOP of the circle with two 45°
flats meeting at an apex r*sqrt(2) above the axis - every ceiling surface
sits at the self-support threshold, so the hole prints clean with no
supports. The round LOWER half is untouched: pins, rods and bearings ride
exactly as in a round bore (contact is at the bottom).

Conventions (same as supports.py): describe the site with `axis_point`
(a point on the bore axis where the cutter starts), `axis_dir` (the bore
axis; the cutter extrudes `length` that way) and `print_up` (the part's
build direction). Use the returned solid as-is - never post-rotate or
mirror it; orient via the arguments instead. `axis_dir` must be
perpendicular to `print_up` (a vertical hole prints round on its own -
asking for a teardrop there raises).

OBLIQUE HOLES (axis tilted from print_up, neither parallel nor square to it).
A round bore's worst surface is its crown, and that crown faces down only as
steeply as the hole is tilted: at tilt T from the build axis its slope is
90-T. So the peak is sized FROM THE TILT, not fixed at 45:

    T <= 45 (SELF_SUPPORT_DEG)   the round bore already self-supports -> the
                                 cutter IS the round bore, no peak at all
    45 < T < 90                  a partial peak: flats tangent at psi from the
                                 crown, cos(psi) = cos(45)/sin(T), apex r/cos(psi)
    T = 90 (sideways)            psi = 45, apex r*sqrt(2) -- the classic teardrop

Every case leaves the steepest ceiling at exactly the limit and no steeper. A
fixed 45 teardrop on an oblique hole is not wrong, just wasteful: it slits
walls the hole never needed to touch.

THE HOLE'S MOUTH adds no overhang of its own. Where a bore breaks out through
a surface the only faces are the bore (at the slope above) and that surface
(which is whatever it already was); the rim between them is an EDGE, and an
edge has no area to sag. Measured, not argued: a 45-built floating tenon with
Ø4 holes tilted exactly 45 has no surface steeper than 45 anywhere, mouths
included. The one case that still raises is PARALLEL -- a hole along the build
axis prints round on its own.

Mind the apex room: the peak reaches r*sqrt(2) from the axis in the
`print_up` direction - ~0.41*r beyond the round bore. In thin webs (e.g.
a bore through a ring whose wall is thinner than that) the apex will slit
the crown; usually harmless for a cutter, but check the site.
"""

import math

import cadquery as cq

__all__ = ["teardrop_hole", "SELF_SUPPORT_DEG"]

SELF_SUPPORT_DEG = 45.0     # steepest ceiling that prints without support


def _unit(v):
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if n < 1e-12:
        raise ValueError("zero-length direction")
    return (v[0] / n, v[1] / n, v[2] / n)


def teardrop_hole(d, length, axis_point=(0.0, 0.0, 0.0),
                  axis_dir=(1.0, 0.0, 0.0), print_up=(0.0, 0.0, 1.0)):
    """CUTTER for a round hole: a Ø`d` cylinder from `axis_point` along
    `axis_dir` for `length`, its ceiling peaked toward `print_up` only as far
    as the hole's tilt requires (see OBLIQUE HOLES above). Square to print_up
    that is the classic 45° teardrop, apex at (d/2)*sqrt(2); tilted 45° or
    less it is the plain round bore. Blind holes: the flat far end is the
    floor, as with a plain cylinder; overshoot the mouth by passing a longer
    length / earlier axis_point."""
    if d <= 0.0 or length <= 0.0:
        raise ValueError("d and length must be > 0")
    a = _unit(axis_dir)
    u = _unit(print_up)
    c = a[0] * u[0] + a[1] * u[1] + a[2] * u[2]
    if abs(c) > 1.0 - 1e-9:
        raise ValueError("teardrop_hole: axis_dir is PARALLEL to print_up - "
                         "a hole along the build direction prints round; no "
                         "teardrop needed there")
    # the part of print_up the bore's cross-section actually sees
    up = _unit((u[0] - c * a[0], u[1] - c * a[1], u[2] - c * a[2]))
    sin_t = math.sqrt(max(0.0, 1.0 - c * c))
    r = d / 2.0
    x = (up[1] * a[2] - up[2] * a[1],             # plane xDir = up x axis ->
         up[2] * a[0] - up[0] * a[2],             # plane yDir = axis x x
         up[0] * a[1] - up[1] * a[0])             #            = up
    plane = cq.Plane(origin=cq.Vector(*axis_point), xDir=cq.Vector(*x),
                     normal=cq.Vector(*a))
    bore = cq.Workplane(plane).circle(r).extrude(length)
    cos_psi = math.cos(math.radians(SELF_SUPPORT_DEG)) / sin_t
    if cos_psi >= 1.0 - 1e-9:
        return bore                               # tilt <= limit: round is fine
    psi = math.acos(cos_psi)
    k, h = r * math.sin(psi), r * math.cos(psi)   # tangent point
    peak = (cq.Workplane(plane)
            .polyline([(-k, h), (0.0, r / cos_psi), (k, h)])
            .close().extrude(length))
    return bore.union(peak)


# ── Self-test: geometry gates (run `py -3.12 holes.py`) ──────────────────────
if __name__ == "__main__":
    import sys

    fails = []
    D, L = 5.3, 8.0
    R = D / 2.0
    # teardrop cross-section area = pi*r^2 + r^2*(1 - pi/4)
    want_v = (math.pi * R * R + R * R * (1.0 - math.pi / 4.0)) * L

    t = teardrop_hole(D, L)                       # axis +X, up +Z
    v = t.val().Volume()
    ok = abs(v - want_v) < 1e-3
    print(f"volume        {v:.3f} (want {want_v:.3f}){'' if ok else '  <-- FAIL'}")
    if not ok:
        fails.append(f"volume {v:.3f} != {want_v:.3f}")
    bb = t.val().BoundingBox()
    ok = (abs(bb.zmax - R * math.sqrt(2.0)) < 1e-6 and abs(bb.zmin + R) < 1e-6
          and abs(bb.xmin) < 1e-6 and abs(bb.xmax - L) < 1e-6
          and abs(bb.ymin + R) < 1e-6 and abs(bb.ymax - R) < 1e-6)
    print(f"apex/extents  z[{bb.zmin:.3f},{bb.zmax:.3f}] x[{bb.xmin:.3f},"
          f"{bb.xmax:.3f}]{'' if ok else '  <-- FAIL'}")
    if not ok:
        fails.append("extents wrong")

    # orientation: axis +Y, print up +X -> apex along +X
    t2 = teardrop_hole(D, L, (1.0, 2.0, 3.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0))
    bb2 = t2.val().BoundingBox()
    ok = (abs(bb2.xmax - (1.0 + R * math.sqrt(2.0))) < 1e-6
          and abs(bb2.ymin - 2.0) < 1e-6 and abs(bb2.ymax - (2.0 + L)) < 1e-6
          and abs(t2.val().Volume() - want_v) < 1e-3)
    print(f"reoriented    apex x={bb2.xmax:.3f} (want {1.0 + R * math.sqrt(2.0):.3f})"
          f"{'' if ok else '  <-- FAIL'}")
    if not ok:
        fails.append("reoriented placement wrong")

    # diagonal horizontal axis, up -Z (a flipped print) -> apex points DOWN
    s2 = 1.0 / math.sqrt(2.0)
    t3 = teardrop_hole(D, L, (0.0, 0.0, 0.0), (s2, s2, 0.0), (0.0, 0.0, -1.0))
    bb3 = t3.val().BoundingBox()
    ok = (abs(bb3.zmin + R * math.sqrt(2.0)) < 1e-6
          and abs(bb3.zmax - R) < 1e-6
          and abs(t3.val().Volume() - want_v) < 1e-3)
    print(f"flipped print apex z={bb3.zmin:.3f} (want {-R * math.sqrt(2.0):.3f})"
          f"{'' if ok else '  <-- FAIL'}")
    if not ok:
        fails.append("flipped-print apex wrong")

    # a rod one fit-gap smaller must ride the cut bore without touching
    block = (cq.Workplane("XY").box(L, 20.0, 20.0, centered=(False, True, True))
             .cut(teardrop_hole(D, L + 2.0, (-1.0, 0.0, 0.0))))
    rod = (cq.Workplane(cq.Plane(origin=cq.Vector(0, 0, 0),
                                 xDir=cq.Vector(0, 1, 0),
                                 normal=cq.Vector(1, 0, 0)))
           .circle(R - 0.15).extrude(L))
    try:
        inter = sum(s.Volume() for s in block.intersect(rod).solids().vals())
    except Exception:
        inter = 0.0
    ok = inter < 1e-6
    print(f"rod clearance {inter:.6f} mm3 (must be 0){'' if ok else '  <-- FAIL'}")
    if not ok:
        fails.append(f"rod interferes {inter}")

    # OBLIQUE: the steepest ceiling a cutter leaves must be AT the limit and
    # never past it, at every tilt; and a tilt <= 45 must be the plain bore.
    def _worst_ceiling(cutter, axis, up):
        """Largest n.up over the cutter's side surface. The cutter's UP-facing
        surface is the part's DOWN-facing ceiling. End caps excluded."""
        worst = -1.0
        for f in cutter.val().Faces():
            vs, tris = f.tessellate(0.02)
            for i, j, k2 in tris:
                A, Bv, C = vs[i], vs[j], vs[k2]
                e1 = (Bv.x - A.x, Bv.y - A.y, Bv.z - A.z)
                e2 = (C.x - A.x, C.y - A.y, C.z - A.z)
                n = (e1[1] * e2[2] - e1[2] * e2[1],
                     e1[2] * e2[0] - e1[0] * e2[2],
                     e1[0] * e2[1] - e1[1] * e2[0])
                m = math.sqrt(sum(q * q for q in n))
                if m < 1e-12:
                    continue
                n = tuple(q / m for q in n)
                if abs(sum(n[q] * axis[q] for q in range(3))) > 0.99:
                    continue                      # an end cap, not the bore
                worst = max(worst, sum(n[q] * up[q] for q in range(3)))
        return worst

    lim = math.cos(math.radians(SELF_SUPPORT_DEG))
    for tilt in (90.0, 75.0, 60.0, 50.0, 45.0, 30.0):
        ax = (math.sin(math.radians(tilt)), 0.0, math.cos(math.radians(tilt)))
        cut = teardrop_hole(D, L, (0.0, 0.0, 0.0), ax, (0.0, 0.0, 1.0))
        w = _worst_ceiling(cut, ax, (0.0, 0.0, 1.0))
        vol = cut.val().Volume()
        ok = w <= lim + 2e-3
        if tilt <= SELF_SUPPORT_DEG:
            ok = ok and abs(vol - math.pi * R * R * L) < 1e-3
        ang = math.degrees(math.acos(max(-1.0, min(1.0, w))))
        print(f"tilt {tilt:4.0f}     steepest ceiling {ang:4.1f} deg from down, "
              f"vol {vol:7.3f}" + ("" if ok else "  <-- FAIL"))
        if not ok:
            fails.append(f"oblique tilt {tilt}: worst {w:.4f}, vol {vol:.3f}")
    # the PLAIN bore must fail that same check sideways, or it proves nothing
    plain = (cq.Workplane(cq.Plane((0, 0, 0), (0, 1, 0), (1, 0, 0)))
             .circle(R).extrude(L))
    w = _worst_ceiling(plain, (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    ok = w > lim + 0.1
    print("control      plain sideways bore is flagged: %s" % ok
          + ("" if ok else "  <-- FAIL"))
    if not ok:
        fails.append("ceiling check cannot see a plain bore's crown")

    # vertical axis must raise; zero size must raise
    for label, kwargs in (("parallel axis", dict(axis_dir=(0, 0, 1))),
                          ("zero d", dict())):
        try:
            teardrop_hole(0.0 if label == "zero d" else D, L, **kwargs)
            fails.append(f"{label} did not raise")
            print(f"{label:13s} did NOT raise  <-- FAIL")
        except ValueError:
            print(f"{label:13s} raises (ok)")

    if fails:
        print("FAIL:", *fails, sep="\n  ")
    else:
        print("OK - teardrop hole: exact area, apex tracks print_up (incl. "
              "flipped prints), round lower half preserved, oblique peaks "
              "sized to the tilt (round at <=45), parallel refused.")
    sys.exit(len(fails))
