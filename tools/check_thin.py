# -*- coding: utf-8 -*-
"""THIN MATERIAL, measured on the finished solid.

check_beads reads CONSTANTS. That catches a length written off the bead grid, and it
is blind to the thing that actually matters: what the booleans left behind. A 1.2 mm
web between a bore and a pocket is made of two constants that are both perfectly on
grid. The user found exactly that by eye, in a joint whose every number checked out.

So this measures. For every face of the solid it samples points, walks INWARD along
the surface normal, and records how far it gets before it leaves the material. Where
the face it lands on is roughly PARALLEL and facing back (a wall has two sides), that
distance is a wall thickness. Anything under dimensions.MIN_WALL_2P is reported with
the point you can go and look at.

WHAT IT IS NOT. It samples, so it is a survey, not a proof -- a thin spot smaller than
the sample spacing can hide. Raise --grid where it matters. It also deliberately
ignores hits on faces that are NOT facing back: that is what keeps every chamfer and
fillet, which taper to nothing at their edge by design, out of the report.

    py -3.12 -m tools.check_thin                      every part in src.build.PARTS
    py -3.12 -m tools.check_thin fixed_tenon body_adapter
    py -3.12 -m tools.check_thin --limit 1.6 --grid 24 --top 15 bar_latch_collar
"""
from __future__ import annotations

import sys

from OCP.BRep import BRep_Tool
from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
from OCP.BRepTools import BRepTools
from OCP.BRepTopAdaptor import BRepTopAdaptor_FClass2d
from OCP.GeomLProp import GeomLProp_SLProps
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.TopAbs import TopAbs_FACE, TopAbs_OUT, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt, gp_Pnt2d, gp_Vec

from src import dimensions as D

EPS = 1e-3          # step off the surface before casting, so we do not hit ourselves
FACING = -0.9       # the far face must be within ~25 deg of PARALLEL. A wedge whose
                    # two faces close at an angle tapers to nothing at its edge by
                    # design and is not a thin wall; a wall has two parallel sides.
MAX_T = 40.0        # stop looking past this; anything thicker is not our problem
SPREAD = 1.0        # a WALL is thin over an area; a knife edge is thin only ON the
                    # edge. So every candidate is re-measured SPREAD away along the
                    # surface in four directions, and only counts if the material is
                    # still thin there. Without this every tangent breakout in the
                    # instrument reports 0.01 and buries the real findings.


def _faces(shape):
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        yield TopoDS.Face_s(exp.Current())
        exp.Next()


def _area(face):
    p = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face, p)
    return p.Mass()


def _normal_at(face, surf, u, v):
    """OUTWARD normal of the solid at (u, v) on `face`, and the point."""
    props = GeomLProp_SLProps(surf, u, v, 1, 1e-7)
    if not props.IsNormalDefined():
        return None, None
    n = gp_Vec(props.Normal())
    if face.Orientation() == TopAbs_REVERSED:
        n.Reverse()
    return props.Value(), n


def _thickness(shape, inter, face, surf, cls, u, v):
    """Material depth straight in from (u, v), or None if there is no face facing
    back within MAX_T (an open edge, a chamfer's tip, the outside world)."""
    if cls.Perform(gp_Pnt2d(u, v)) == TopAbs_OUT:
        return None
    p, nrm = _normal_at(face, surf, u, v)
    if p is None or nrm.Magnitude() < 1e-9:
        return None
    nrm.Normalize()
    ray = gp_Dir(-nrm.X(), -nrm.Y(), -nrm.Z())
    start = gp_Pnt(p.X() + ray.X() * EPS, p.Y() + ray.Y() * EPS, p.Z() + ray.Z() * EPS)
    inter.Init(shape, gp_Lin(start, ray), 1e-7)
    best = None
    while inter.More():
        w = inter.W()
        if EPS < w < MAX_T and (best is None or w < best[0]):
            f2 = inter.Face()
            _, n2 = _normal_at(f2, BRep_Tool.Surface_s(f2), inter.U(), inter.V())
            if n2 is not None and n2.Magnitude() > 1e-9:
                n2.Normalize()
                if nrm.Dot(n2) < FACING:            # a wall has two sides
                    best = (w, inter.Pnt())
        inter.Next()
    if best is None:
        return None
    q = best[1]
    return best[0] + EPS, ((p.X() + q.X()) / 2, (p.Y() + q.Y()) / 2, (p.Z() + q.Z()) / 2)


def _uv_step(surf, u, v, mm):
    """(du, dv) that move about `mm` across the surface at (u, v)."""
    props = GeomLProp_SLProps(surf, u, v, 1, 1e-7)
    du = props.D1U().Magnitude()
    dv = props.D1V().Magnitude()
    return (mm / du if du > 1e-9 else 0.0), (mm / dv if dv > 1e-9 else 0.0)


def thin_spots(shape, limit, grid=16, top=10):
    """[(thickness, (x, y, z)), ...] worst first, for walls under `limit`."""
    faces = list(_faces(shape))
    inter = BRepIntCurveSurface_Inter()
    surfs = {}
    for f in faces:
        surfs[f] = BRep_Tool.Surface_s(f)
    hits = []
    for face in faces:
        surf = surfs[face]
        umin, umax, vmin, vmax = BRepTools.UVBounds_s(face)
        cls = BRepTopAdaptor_FClass2d(face, 1e-7)
        # sample denser on bigger faces: a 400 mm2 face gets more looks than a 4 mm2 one
        n = max(4, min(3 * grid, int(grid * (_area(face) / 100.0) ** 0.5) + grid // 2))
        for i in range(n):
            u = umin + (umax - umin) * (i + 0.5) / n
            for j in range(n):
                v = vmin + (vmax - vmin) * (j + 0.5) / n
                got = _thickness(shape, inter, face, surf, cls, u, v)
                if got is None or got[0] + EPS >= limit:
                    continue
                # ...and is it thin a millimetre away, or is this a knife edge?
                du, dv = _uv_step(surf, u, v, SPREAD)
                near, seen = True, 0
                for su, sv in ((du, 0.0), (-du, 0.0), (0.0, dv), (0.0, -dv)):
                    g2 = _thickness(shape, inter, face, surf, cls, u + su, v + sv)
                    if g2 is None:
                        continue                    # off the face: says nothing
                    seen += 1
                    if g2[0] + EPS >= limit:
                        near = False
                        break
                if near and seen >= 2:
                    hits.append((got[0], tuple(round(c, 2) for c in got[1])))
    hits.sort(key=lambda h: h[0])
    # thin one spot on a wall means thin all along it: keep the worst per 3 mm cluster
    kept = []
    for t, q in hits:
        if not any(abs(q[0] - r[0]) < 3 and abs(q[1] - r[1]) < 3 and abs(q[2] - r[2]) < 3
                   for _, r in kept):
            kept.append((t, q))
        if len(kept) >= top:
            break
    return kept, len(hits)


def main(argv):
    limit, grid, top = D.MIN_WALL_2P, 16, 10
    names = []
    it = iter(range(len(argv)))
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--limit":
            i += 1
            limit = float(argv[i])
        elif a == "--grid":
            i += 1
            grid = int(argv[i])
        elif a == "--top":
            i += 1
            top = int(argv[i])
        else:
            names.append(a)
        i += 1

    from src import build as B
    parts = B.PARTS
    if not names:
        names = [k for k in parts]
    print("thin check: material under %.2f mm (MIN_WALL_2P %.2f, hard floor %.2f)"
          % (limit, D.MIN_WALL_2P, D.MIN_WALL))
    bad = 0
    for nm in names:
        if nm not in parts:
            print("  ?? no part %r" % nm)
            continue
        obj = parts[nm][0]()
        shape = (obj.val() if hasattr(obj, "val") else obj).wrapped
        kept, n = thin_spots(shape, limit, grid, top)
        if not kept:
            print("  ok   %-24s nothing under %.2f" % (nm, limit))
            continue
        bad += 1
        print("  THIN %-24s %d sample(s), worst %.2f:" % (nm, n, kept[0][0]))
        for t, q in kept:
            print("         %5.2f at (%9.2f, %7.2f, %8.2f)" % (t, q[0], q[1], q[2]))
    print("\n%d part(s) with material under %.2f" % (bad, limit))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
