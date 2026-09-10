"""Print-aware HOLE cutters.

`house_hole(d, length, axis_point, axis_dir, print_up)` is the teardrop's
bounding "house": the same 45° roof and apex, but straight walls tangent to
the Ø`d` circle and a flat floor tangent to it - a pentagon. Use it for
CLEARANCE passages (something Ø<d must pass, nothing rides the bore): the
square corners are free room, and where a round floor would have left a thin
cusp against a neighbouring cut the flat one merges cleanly.

`teardrop_hole(d, length, axis_point, axis_dir, print_up)` returns a CUTTER
for a round hole whose axis runs PERPENDICULAR to the print direction (a
"sideways" hole). A plain cylinder cut prints with an unsupported sagging
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

Mind the apex room: the peak reaches r*sqrt(2) from the axis in the
`print_up` direction - ~0.41*r beyond the round bore. In thin webs (e.g.
a bore through a ring whose wall is thinner than that) the apex will slit
the crown; usually harmless for a cutter, but check the site.
"""

import math

import cadquery as cq

__all__ = ["teardrop_hole", "house_hole"]


def _unit(v):
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if n < 1e-12:
        raise ValueError("zero-length direction")
    return (v[0] / n, v[1] / n, v[2] / n)


def _hole_plane(axis_point, axis_dir, print_up, who):
    a = _unit(axis_dir)
    u = _unit(print_up)
    if abs(a[0] * u[0] + a[1] * u[1] + a[2] * u[2]) > 1e-6:
        raise ValueError(f"{who} needs axis_dir PERPENDICULAR to "
                         "print_up - a hole along the build direction "
                         "prints round; no teardrop needed there")
    x = (u[1] * a[2] - u[2] * a[1],               # x = print_up x axis ->
         u[2] * a[0] - u[0] * a[2],               # plane yDir = axis x x
         u[0] * a[1] - u[1] * a[0])               #            = print_up
    return cq.Plane(origin=cq.Vector(*axis_point), xDir=cq.Vector(*x),
                    normal=cq.Vector(*a))


def teardrop_hole(d, length, axis_point=(0.0, 0.0, 0.0),
                  axis_dir=(1.0, 0.0, 0.0), print_up=(0.0, 0.0, 1.0)):
    """CUTTER for a sideways round hole: a Ø`d` cylinder from `axis_point`
    along `axis_dir` for `length`, its ceiling replaced by the 45° teardrop
    peak toward `print_up` (apex at (d/2)*sqrt(2) off the axis). Blind
    holes: the flat far end is the floor, as with a plain cylinder;
    overshoot the mouth by passing a longer length / earlier axis_point."""
    if d <= 0.0 or length <= 0.0:
        raise ValueError("d and length must be > 0")
    plane = _hole_plane(axis_point, axis_dir, print_up, "teardrop_hole")
    r = d / 2.0
    k = r / math.sqrt(2.0)                        # 45° tangent point
    bore = cq.Workplane(plane).circle(r).extrude(length)
    peak = (cq.Workplane(plane)
            .polyline([(-k, k), (0.0, r * math.sqrt(2.0)), (k, k)])
            .close().extrude(length))
    return bore.union(peak)


def house_hole(d, length, axis_point=(0.0, 0.0, 0.0),
               axis_dir=(1.0, 0.0, 0.0), print_up=(0.0, 0.0, 1.0), wall=None):
    """CUTTER for a sideways CLEARANCE passage: a `d`-wide rectangle `wall`
    tall with a 45° roof on top (roof height d/2), apex toward `print_up`.
    The axis sits d/2 above the flat floor, so the apex is `wall` above it.
    Default wall = (d/2)*sqrt(2): the pentagon that bounds a Ø`d` teardrop
    (same roof, same apex), so anything Ø<=d passes. A shorter wall cuts into
    that circle. Same argument conventions as teardrop_hole."""
    r = d / 2.0
    if wall is None:
        wall = r * math.sqrt(2.0)
    if d <= 0.0 or length <= 0.0 or wall <= 0.0:
        raise ValueError("d, length and wall must be > 0")
    plane = _hole_plane(axis_point, axis_dir, print_up, "house_hole")
    return (cq.Workplane(plane)
            .polyline([(-r, -r), (r, -r), (r, wall - r), (0.0, wall), (-r, wall - r)])
            .close().extrude(length))


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

    # house: pentagon area = d*(r+eave) + r*(r*sqrt2-eave); apex = teardrop's; holds the round
    eave = R * (math.sqrt(2.0) - 1.0)
    want_h = (2 * R * (R + eave) + R * (R * math.sqrt(2.0) - eave)) * L
    h = house_hole(D, L, (1.0, 2.0, 3.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0))
    bbh = h.val().BoundingBox()
    cont = h.intersect(teardrop_hole(D, L, (1.0, 2.0, 3.0), (0.0, 1.0, 0.0),
                                     (1.0, 0.0, 0.0))).val().Volume()
    ok = (abs(h.val().Volume() - want_h) < 1e-3 and abs(cont - want_v) < 1e-3
          and abs(bbh.xmax - (1.0 + R * math.sqrt(2.0))) < 1e-6
          and abs(bbh.xmin - (1.0 - R)) < 1e-6 and abs(bbh.zmax - (3.0 + R)) < 1e-6)
    print(f"house         vol {h.val().Volume():.3f} (want {want_h:.3f}), holds the "
          f"teardrop {cont:.3f}/{want_v:.3f}, apex x={bbh.xmax:.3f}{'' if ok else '  <-- FAIL'}")
    if not ok:
        fails.append("house_hole geometry wrong")
    hw = house_hole(D, L, wall=2.0 * R)           # explicit wall: area d*wall + r^2, apex at wall
    bbw = hw.val().BoundingBox()
    ok = (abs(hw.val().Volume() - (D * 2.0 * R + R * R) * L) < 1e-3
          and abs(bbw.zmax - 2.0 * R) < 1e-6 and abs(bbw.zmin + R) < 1e-6)
    print(f"house wall    vol {hw.val().Volume():.3f} apex z={bbw.zmax:.3f}"
          f"{'' if ok else '  <-- FAIL'}")
    if not ok:
        fails.append("house_hole wall geometry wrong")

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
              "flipped prints), round lower half preserved, perpendicularity "
              "enforced.")
    sys.exit(len(fails))
