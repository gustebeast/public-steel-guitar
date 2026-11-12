"""Helical solids -> their cylinders, for the overlap gate (user, 2026-11-12: "treat helixes as
cylinders so it doesn't run so slow").

A swept helix (a coil spring's wire, a leadscrew's thread) is the costliest thing the boolean
scan meets: a 43-coil spring against one neighbour can take minutes, and every part that moves
near it re-pays that. For a CLEARANCE question the coils add nothing a cylinder doesn't answer
-- and the cylinder is the stricter answer (it fills the gaps between coils), which is what
direct_bench's own gate already did by hand (COILS False).

So before the scan, every solid that IS a helix -- it has a B-spline face (or is a mesh of
MESH_FACES faces or more: the leadscrews are drawn whole_mesh), AND it is round about
its own axis (all 16 sectors round the axis reach the same outer radius, within 12 %) -- is swapped
for the cylinder that wraps it:
  hollow (the axis at mid-length is outside the solid: a spring)  -> a TUBE, inner to outer radius
  solid  (a threaded rod)                                          -> a ROD, its outer radius
Each solid on its own, so a spring's tangs (plain cylinders) stay as drawn and do not swell the
tube. Anything else with B-spline faces (a loft, an imported motor) fails the roundness test and
is left alone. Only the GATE sees the proxies; the view and the export keep the coils.
"""

from __future__ import annotations

import math

SECTORS = 16
ROUND_TOL = 0.12          # each sector's outer radius within 12 % of the largest (a
                          # B-spline thread bulges ~8 %; a square motor misses by 41 %)
MESH_FACES = 300          # a solid of this many faces or more is a mesh (a leadscrew drawn
                          # whole_mesh): a candidate too, if it is round
SNAP_DEG = 2.0            # an axis this close to a world axis IS that axis (inertia axes of a
                          # part-turn helix lean a little, and a lean fattens the tube)
EDGE_STEP = 1.0           # mm between samples along a B-spline face's edges
GRID = (240, 8)           # samples over a B-spline face: along the sweep, round the wire


def _axes(solid):
    """(centre of mass, the three principal axes, each snapped to a world axis within SNAP_DEG).
    Which one is the helix's own is settled by the fit in proxy(): for a long spring it is the
    smallest moment, for a short squat one (a 3-turn grip) the largest."""
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(solid.wrapped, p)
    pp = p.PrincipalProperties()
    out = []
    for a in (pp.FirstAxisOfInertia(), pp.SecondAxisOfInertia(), pp.ThirdAxisOfInertia()):
        a = (a.X(), a.Y(), a.Z())
        for j in range(3):
            if abs(a[j]) >= math.cos(math.radians(SNAP_DEG)):
                a = tuple(1.0 if q == j else 0.0 for q in range(3))
                break
        out.append(a)
    # and the world axes themselves: a short helix (a 3-turn grip) leans its inertia axes by
    # more than SNAP_DEG, and every helix in this model runs along one of them
    for w in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)):
        if w not in out:
            out.append(w)
    c = p.CentreOfMass()
    return (c.X(), c.Y(), c.Z()), out


def _points(solid):
    """Points on the solid's surface: a mesh's vertices, a B-spline face sampled on a grid, every
    other face's vertices and edge samples -- no tessellation (41 s on a 43-coil spring)."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepTopAdaptor import BRepTopAdaptor_FClass2d
    from OCP.gp import gp_Pnt2d
    from OCP.TopAbs import TopAbs_OUT
    faces = solid.Faces()
    if len(faces) >= MESH_FACES:
        return [(v.X, v.Y, v.Z) for v in solid.Vertices()]
    out = []
    bb = solid.BoundingBox(tolerance=0.01)
    for f in faces:
        if f.geomType() == "BSPLINE":
            sa = BRepAdaptor_Surface(f.wrapped)
            u0, u1, v0, v1 = (sa.FirstUParameter(), sa.LastUParameter(),
                              sa.FirstVParameter(), sa.LastVParameter())
            # the surface runs on past a TRIMMED face (a thread's flank past its crest): keep
            # only the samples that are on the face itself
            fc = BRepTopAdaptor_FClass2d(f.wrapped, 1e-6)
            nu, nv = GRID if (u1 - u0) >= (v1 - v0) else GRID[::-1]
            for i in range(nu + 1):
                for j in range(nv + 1):
                    u, v = u0 + (u1 - u0) * i / nu, v0 + (v1 - v0) * j / nv
                    if fc.Perform(gp_Pnt2d(u, v)) == TopAbs_OUT:
                        continue
                    q = sa.Value(u, v)
                    if (bb.xmin <= q.X() <= bb.xmax and bb.ymin <= q.Y() <= bb.ymax
                            and bb.zmin <= q.Z() <= bb.zmax):   # the classifier lets some
                        out.append((q.X(), q.Y(), q.Z()))       # overrun through: the box won't
            out += [(v_.X, v_.Y, v_.Z) for v_ in f.Vertices()]
            for e in f.Edges():                      # its edges (a thread's crest and root
                n = max(8, int(e.Length() / EDGE_STEP))   # helices) at EDGE_STEP: every turn
                for t in range(n + 1):                    # reaches every sector
                    q = e.positionAt(t / n)
                    out.append((q.x, q.y, q.z))
        else:
            out += [(v.X, v.Y, v.Z) for v in f.Vertices()]
            for e in f.Edges():
                for t in (0.25, 0.5, 0.75):
                    q = e.positionAt(t)
                    out.append((q.x, q.y, q.z))
    return out


def _frame(ax):
    """Two unit vectors square to ax."""
    ux, uy, uz = ax
    t = (1.0, 0.0, 0.0) if abs(ux) < 0.9 else (0.0, 1.0, 0.0)
    e1 = (uy * t[2] - uz * t[1], uz * t[0] - ux * t[2], ux * t[1] - uy * t[0])
    n = math.sqrt(sum(v * v for v in e1))
    e1 = tuple(v / n for v in e1)
    e2 = (uy * e1[2] - uz * e1[1], uz * e1[0] - ux * e1[2], ux * e1[1] - uy * e1[0])
    return e1, e2


def _enclosing_centre(u, v, steps=200):
    """Centre of (about) the smallest circle round the points (Badoiu-Clarkson: step toward the
    farthest point by 1/(k+1)); ~0.1 % of the radius after a few hundred steps."""
    n = len(u)
    if n > 3000:                                   # a thinned set: the farthest points survive
        k = n // 3000 + 1
        u, v = u[::k] + [max(u), min(u)], v[::k] + [v[u.index(max(u))], v[u.index(min(u))]]
    cu, cv = (max(u) + min(u)) / 2, (max(v) + min(v)) / 2
    for k in range(1, steps + 1):
        j = max(range(len(u)), key=lambda q: (u[q] - cu) ** 2 + (v[q] - cv) ** 2)
        cu += (u[j] - cu) / (k + 1)
        cv += (v[j] - cv) / (k + 1)
    return cu, cv


def _fit(rel, ax):
    """The enclosing cylinder about direction ax: (volume, centre offset u0 v0, frame, s range,
    rmin, rout), or None if the points are not round about it."""
    e1, e2 = _frame(ax)
    s = [r[0] * ax[0] + r[1] * ax[1] + r[2] * ax[2] for r in rel]
    u = [r[0] * e1[0] + r[1] * e1[1] + r[2] * e1[2] for r in rel]
    v = [r[0] * e2[0] + r[1] * e2[1] + r[2] * e2[2] for r in rel]
    # the axis may sit a little off the centre of mass (a part-turn): centre it on the SMALLEST
    # CIRCLE round the points -- the tightest cylinder that still holds every one of them
    u0, v0 = _enclosing_centre(u, v)
    rmax = [0.0] * SECTORS
    rmin, rout = float("inf"), 0.0
    for a, b in zip(u, v):
        a, b = a - u0, b - v0
        r = math.hypot(a, b)
        k = int((math.atan2(b, a) + math.pi) / (2 * math.pi) * SECTORS) % SECTORS
        rmax[k] = max(rmax[k], r)
        rmin, rout = min(rmin, r), max(rout, r)
    if rout <= 0 or min(rmax) < (1 - ROUND_TOL) * rout:
        return None                                  # not round about this axis
    s0, s1 = min(s), max(s)
    return math.pi * rout * rout * (s1 - s0), u0, v0, e1, e2, s0, s1, rmin, rout


def proxy(solid):
    """The cylinder for a helical solid, or None if it is not one: about whichever principal axis
    it is round about, the one that wraps it tightest."""
    import cadquery as cq
    if not _candidate(solid):
        return None
    pts = _points(solid)
    if len(pts) < SECTORS * 4:
        return None
    c, axes = _axes(solid)
    rel = [(p[0] - c[0], p[1] - c[1], p[2] - c[2]) for p in pts]
    best = None
    for ax in axes:
        f = _fit(rel, ax)
        if f is not None and (best is None or f[0] < best[1][0]):
            best = (ax, f)
    if best is None:
        return None                                  # round about no axis: leave it
    ax, (_, u0, v0, e1, e2, s0, s1, rmin, rout) = best
    o = tuple(c[j] + u0 * e1[j] + v0 * e2[j] + s0 * ax[j] for j in range(3))
    mid = cq.Vector(*(o[j] + (s1 - s0) / 2 * ax[j] for j in range(3)))
    hollow = not solid.isInside(mid) and rmin > 0.3 * rout
    return _make([list(o), list(ax), s1 - s0, rmin if hollow else 0.0, rout])


def _make(params):
    """The cylinder from its cached numbers: [origin, axis, length, inner r (0: solid), outer r]."""
    import cadquery as cq
    o, ax, L, ri, ro = params
    o, ax = cq.Vector(*o), cq.Vector(*ax)
    out = cq.Solid.makeCylinder(ro, L, o, ax)
    if ri > 0:
        out = out.cut(cq.Solid.makeCylinder(ri, L, o, ax))
    out.params = params
    return out


def _candidate(solid) -> bool:
    faces = solid.Faces()
    return len(faces) >= MESH_FACES or any(f.geomType() == "BSPLINE" for f in faces)


def swap(comps, cache_path=None):
    """[(name, shape)] -> ([(name, shape with its helices as cylinders)], [names swapped]).
    Each candidate solid's answer is remembered by its BRep fingerprint (cadkit.overlap_check's,
    the overlap cache's own key) in cache_path, so an unchanged spring costs nothing next run."""
    import json
    import cadquery as cq
    from cadkit.overlap_check import _canonical, fingerprint
    memo = {}
    if cache_path:
        try:
            memo = json.load(open(cache_path, encoding="utf-8"))
        except (OSError, ValueError):
            memo = {}
    used = {}
    out, hit = [], []
    for nm, sh in comps:
        sols = sh.Solids() if hasattr(sh, "Solids") else []
        cands = [s_ for s_ in sols if _candidate(s_)]
        if not cands:
            out.append((nm, sh))
            continue
        _canonical(cands)
        new, changed = [], False
        for s_ in sols:
            p = None
            if _candidate(s_):
                key = fingerprint(s_)
                if key in memo:
                    params = memo[key]
                else:
                    pr = proxy(s_)
                    params = None if pr is None else pr.params
                used[key] = params
                p = None if params is None else _make(params)
            if p is not None:
                changed = True
                new.extend(p.Solids())
            else:
                new.append(s_)
        if changed:
            hit.append(nm)
            out.append((nm, cq.Compound.makeCompound(new) if len(new) > 1 else new[0]))
        else:
            out.append((nm, sh))
    if cache_path:
        try:
            json.dump(used, open(cache_path, "w", encoding="utf-8"))
        except OSError:
            pass
    return out, hit
