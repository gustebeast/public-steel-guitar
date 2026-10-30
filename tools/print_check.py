"""FAST PRINT CHECK: everything check_ceilings and check_floating look for, in seconds.

  py -3.12 tools/print_check.py --part chassis_0,knee_housing   # from the last scratch build
  py -3.12 tools/print_check.py --step src/test/test_ep_chassis.step  # a print-pose STEP (+Z up)
  py -3.12 tools/print_check.py --part belt_tensioner_half_a_3       # a placed copy: see POSE
  py -3.12 tools/print_check.py --part vkl_kv_housing --up 0,0,1     # direction in the CACHED pose

Exit 2 if any part named could not be checked (said why, at the end).

WHY (user, 2026-10-22: "it took you way too long to build this plate ... those should be
improved"). Measured on chassis_0: check_ceilings + check_floating spent 139 s IMPORTING
(their registry imports src.chassis, which builds the chassis), 513 s point-probing 1204
edge samples for floating material and 703 s measuring each site's area -- 22 minutes for
one part, where the ceiling test itself took 0.3 s.

HOW. Nothing is rebuilt and no part module is imported: the part comes from the scratch
cache as BUILT (your own, else the lead's), its build direction from the source (read, not
run -- see _up_of), and the test runs on its mesh, where every question is exact and
vectorised:
  FACE     a facet whose normal is within (90 - ANGLE) of straight down, off the bed: a
           ceiling (flat: span reported, one bead or under is a ledge) or an overhang past
           ANGLE (a curved roof, a steep chamfer).
  RIDGE    an underside EDGE -- convex, both its faces rising away from it, so nothing is
           under it -- that climbs at less than (90 - ANGLE): each layer would start past the
           last. This is what check_floating sampled for: the wedge between two 45 deg
           cavities (a horizontal ridge), the rim a 45 deg face leaves crossing a 45 deg flank
           (35 deg: "support at 55 deg"). Two faces that each pass can make a ridge that
           does not, which is why a face test alone was never enough.
  ISLAND   a vertex lower than everything round it, off the bed: material that starts in
           mid-air at a point.
  TIP      a convex edge crossing the layers, sharp enough in a layer that its printed end
           stands well back of the drawn one.
  POINT    material narrower than a bead in some layer: the model claims what no bead can lay.
  SINGLE   a bead up to 1.6: it prints as one line. Not an error: there to see and accept.
  STEP     a wedge or sheet under one layer tall.
  RESIDUE  under 0.05 wide, a boolean's leftover.
These last five are cadkit.print_corners on this same mesh, often left by a cut where no
drawing call could see them. They are REPORT-ONLY: nothing here fails on them yet.
Ridge and island candidates are then settled against the solid (_held: is there material
one layer down, within the cone?), so a corner that only LOOKS lowest is not reported.
Hits that share a mesh vertex, or lie within NEAR, are one SITE, reported with its area
(faces), length (ridges), worst angle off the build direction, height above the bed, and
for a roof its SPAN: the widest circle its plan holds (a strip w wide reads w).

ACCURACY. The mesh is the part tessellated to TESS, so a curved face is checked facet by
facet (a cylinder's roof reads from the facet past ANGLE); edges between facets of one
smooth surface are skipped (< SHARP of turn), so tessellation never invents a ridge, and
faces and ridges get FACET_TOL, so an exact 45 deg cone's chords do not read as past it.
VALIDATED (2026-10-22) against check_floating + check_ceilings on the same solids --
chassis_0..2 and one part of every declared family: every site either tool reported, the
other did too, bar single-sample edge hits of the old prober. Spans differ by method:
check_ceilings' 4 x area / perimeter reads a strip double.

POSE. A cached part is in its ASSEMBLY pose. A declared part is checked there along its
declared direction; a placed copy (belt_tensioner_half_a_3, lkr_knee_housing) has that
direction carried onto it from its cached canonical part, or, when that is not cached, is
checked as src.build EXPORTS it for printing (its print-pose STEP, flagged if it is not the
cached solid). Anything else: pass --up.
"""
from __future__ import annotations

import argparse
import ast
import math
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ANGLE = 45.0          # the overhang rule
TESS = 0.01           # tessellation tolerance (mm)
SHARP = 3.0           # an edge turning less than this is inside one smooth surface (deg)
FACET_TOL = 1.0       # a facet chords a curved face: an exact 45 deg cone tessellates to
                      # facets a fraction of a degree past it, so faces/ridges get this much (deg)
NEAR = 1.0            # hits closer than this are one site (mm)
LAYER = 0.2
BEAD = 0.4


# ── the build direction, READ from the source ─────────────────────────────────────────
def _assign(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return node.value
                if isinstance(t, ast.Tuple):          # A, B = (..), (..)
                    for i, e in enumerate(t.elts):
                        if isinstance(e, ast.Name) and e.id == name and isinstance(node.value, ast.Tuple):
                            return node.value.elts[i]
    return None


def _import_of(tree, name, modname):
    """(module, attr) a name was imported as, if it was."""
    pkg = modname.rsplit(".", 1)[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                if (a.asname or a.name) == name:
                    mod = node.module or ""
                    if node.level:
                        base = modname.split(".")
                        mod = ".".join(base[:len(base) - node.level] + ([mod] if mod else []))
                    return mod, a.name
    return None


def _value(modname, name, depth=0):
    """A module constant, evaluated from its source: literals, tuples, unary minus, names
    in the same module, and names imported from another (followed there)."""
    if depth > 6:
        raise ValueError("too deep")
    path = ROOT / (modname.replace(".", "/") + ".py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = _assign(tree, name)
    if node is None:
        imp = _import_of(tree, name, modname)
        if imp is None:
            raise ValueError("%s.%s not found" % (modname, name))
        return _value(imp[0], imp[1], depth + 1)

    def ev(n):
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, (ast.Tuple, ast.List)):
            return tuple(ev(e) for e in n.elts)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -ev(n.operand)
        if isinstance(n, ast.Name):
            return _value(modname, n.id, depth + 1)
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
            imp = _import_of(tree, n.value.id, modname)
            mod = imp[0] + ("." + imp[1] if imp and imp[1] != n.value.id else "") if imp else None
            for cand in ([imp[0] + "." + imp[1], imp[0]] if imp else []):
                try:
                    return _value(cand, n.attr, depth + 1)
                except (ValueError, FileNotFoundError):
                    pass
            raise ValueError("cannot follow %s" % ast.dump(n))
        raise ValueError("not a plain constant: %s" % ast.dump(n)[:80])
    return ev(node)


def _declared():
    """check_ceilings' DECLARED_UP, read from its source (importing it builds the chassis)."""
    tree = ast.parse((ROOT / "tools" / "check_ceilings.py").read_text(encoding="utf-8"))
    node = _assign(tree, "DECLARED_UP")
    out = {}
    for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and isinstance(v, ast.Tuple):
            out[k.value] = tuple(e.value for e in v.elts)
    return out


def up_of(name):
    """The build direction for a part or one of its placed instances (knee_housing for
    lkr_knee_housing, belt_tensioner_half_a for belt_tensioner_half_a_3)."""
    dec = _declared()
    import re
    cands = [name, re.sub(r"_\d+$", "", name)]
    cands += [re.sub(r"^(lkr|rkl|rkr|lkl|vkl)_", "", c) for c in list(cands)]
    for c in cands:
        if c in dec:
            return tuple(float(x) for x in _value(*dec[c])), c
    if re.match(r"chassis_\d+$", name):
        return tuple(float(x) for x in _value("src.chassis", "PRINT_UP")), "chassis"
    if re.match(r"top_plate_\d+$", name):
        return tuple(float(x) for x in _value("src.top_plate", "PIECE_UP")), "top_plate"
    raise KeyError("no declared build direction for %r: pass --up" % name)


# ── parts ─────────────────────────────────────────────────────────────────────────────
FUSED_WITH = {"chassis_%d" % i: "chassis_light_%d" % i for i in range(3)}
FUSED_WITH.update({"top_plate_%d" % i: "top_plate_color_%d" % i for i in range(6)})


def _caches():
    out = [ROOT / ".scratch_cache"]
    try:
        from cadkit.scratch import shared_cache
        out.append(shared_cache(ROOT))
    except Exception:
        pass
    return [c for c in out if c.exists()]


def _read_brep(path):
    import cadquery as cq
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    s = TopoDS_Shape()
    BRepTools.Read_s(s, str(path), BRep_Builder())
    return cq.Shape.cast(s)


def load_part(name):
    def rd(n):
        for c in _caches():
            p = c / (n + ".brep")
            if p.exists():
                return _read_brep(p), p
        return None, None
    s, p = rd(name)
    if s is None:
        raise FileNotFoundError("%s is not in the scratch cache (build it: scratch_view)" % name)
    mate = FUSED_WITH.get(name)
    if mate:
        m, _ = rd(mate)
        if m is not None and m.Solids():
            s = s.fuse(m)
    return s, p


def print_steps(prefix):
    """{name: path} of the print-pose STEPs src.build exports (+Z up, bed at z 0) for every
    printed part named `prefix` or `prefix_...` (knee_housing, knee_housing_r): this
    worktree's file if it has one, else the lead's checkout's."""
    tree = ast.parse((ROOT / "src" / "build.py").read_text(encoding="utf-8"))
    node = _assign(tree, "PARTS")
    out = {}
    for k, v in zip(node.keys, node.values):
        if (isinstance(k, ast.Constant) and (k.value == prefix or k.value.startswith(prefix + "_"))
                and isinstance(v, ast.Tuple)):
            rel = v.elts[1].value if isinstance(v.elts[1], ast.Constant) else None
            if not rel:
                continue
            roots = [ROOT] + [next((a for a in c.parents if (a / "src" / "build.py").exists()), ROOT)
                              for c in _caches()]          # the checkout each cache sits in
            for r in roots:
                if (r / rel).exists():
                    out[k.value] = r / rel
                    break
    return out


def _vertices(shape):
    return np.array([v.toTuple() for v in shape.Vertices()])


def _rigid_up(inst, canon, up):
    """`up` carried onto a placed copy: the rigid map (rotation, or a mirror) taking the
    canonical part's vertices onto the instance's, in order -- a moved or mirrored copy keeps
    its topology. None when the two are not one solid moved."""
    A, B = _vertices(canon), _vertices(inst)
    if len(A) != len(B) or len(A) < 4:
        return None
    a0, b0 = A - A.mean(0), B - B.mean(0)
    U, _, Vt = np.linalg.svd(a0.T @ b0)
    R = (U @ Vt).T                                         # canon -> instance (a mirror allowed)
    err = np.abs(a0 @ R.T - b0).max()
    if err > 1e-3 * max(1.0, np.abs(a0).max()):
        return None
    return tuple(R @ np.asarray(up, float))


def resolve(name, up=None):
    """(label, loader, up) for a part name: the cached part as BUILT, in its assembly pose,
    with its declared direction carried onto that pose. A placed copy (belt_tensioner_half_a_3,
    lkr_knee_housing) is mapped from its canonical part when that is cached; when it is not,
    the part is checked as EXPORTED for printing (src.build's print-pose STEP, +Z up)."""
    if up is not None:
        return name, (lambda: load_part(name)[0]), up
    d, canon = up_of(name)
    if canon == name or canon in ("chassis", "top_plate"):
        return name, (lambda: load_part(name)[0]), d
    import cadquery as cq
    inst = load_part(name)[0]
    try:
        c_shape = load_part(canon)[0]
    except FileNotFoundError:
        c_shape = None
    if c_shape is not None:
        mapped = _rigid_up(inst, c_shape, d)
        if mapped is not None:
            return name, (lambda: inst), mapped
    # not a moved copy of a cached part (the clamps' canonical halves are never placed; a
    # right-hand housing is its own solid): the exported print-pose STEP -- what is printed --
    # of the family member nearest it in volume, flagged when the two are not the same solid
    vol = inst.Volume()
    best = None
    for pn, step in print_steps(canon).items():
        shp = cq.importers.importStep(str(step)).val()
        dv = abs(shp.Volume() - vol)
        if best is None or dv < best[0]:
            best = (dv, step, shp)
    if best is None:
        raise ValueError("%s is a placed copy of %s, which is neither cached nor exported: "
                         "pass --up" % (name, canon))
    dv, step, shp = best
    if dv > 0.01 * vol:
        raise ValueError("%s: no exported %s* STEP is its solid (nearest %s, %.0f mm^3 off): "
                         "pass --up, in the pose it is cached in" % (name, canon, step.name, dv))
    note = "its print STEP %s, %s" % ("/".join(step.parts[-2:]),
                                       time.strftime("%m-%d %H:%M", time.localtime(step.stat().st_mtime)))
    if dv > 1e-4 * max(vol, 1.0):
        note += "; %+.1f mm^3 off the cached %s -- one of them is stale" % (shp.Volume() - vol, name)
    return "%s (%s)" % (name, note), (lambda: shp), (0.0, 0.0, 1.0)


# ── the analysis ──────────────────────────────────────────────────────────────────────
def _rot_to_z(up):
    u = np.asarray(up, float)
    u /= np.linalg.norm(u)
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(u, z)
    s, c = np.linalg.norm(v), float(u @ z)
    if s < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]) / s
    return np.eye(3) + k * s + k @ k * (1 - c)


def _held(mesh, pts, angle):
    """For points in the BUILD frame: is there material one layer down, within the overhang
    cone (straight below, or up to LAYER * tan(angle) to the side)? The mesh tests find the
    candidates; this settles each against the solid, so a corner that merely LOOKS like the
    lowest point (a re-entrant mouth, a step) is not reported. One vectorised containment
    query on the mesh (it is closed: process=True welds it)."""
    r = LAYER * math.tan(math.radians(angle + FACET_TOL)) + 2 * TESS   # AT the limit is held
    ring = np.array([(0.0, 0.0)] + [(r * math.cos(k * math.pi / 4), r * math.sin(k * math.pi / 4))
                                    for k in range(8)]
                    + [(r / 2 * math.cos(k * math.pi / 4), r / 2 * math.sin(k * math.pi / 4))
                       for k in range(8)])
    P = np.asarray(pts, float)
    Q = np.repeat(P, len(ring), axis=0)
    Q[:, :2] += np.tile(ring, (len(P), 1))
    Q[:, 2] -= LAYER
    inside = _contains(mesh, Q).reshape(len(P), len(ring))
    return inside.any(axis=1)


class _ZRays(object):
    """Point-in-solid by parity of a vertical ray's crossings, the triangles binned on an XY
    grid so each point only meets the few above it (trimesh's own test, without embree, wanted
    20 GB for the chassis)."""
    def __init__(self, mesh, cell=2.0):
        T = mesh.triangles
        keep = np.abs(mesh.face_normals[:, 2]) > 1e-9          # walls have no XY area
        self.T = T[keep]
        lo, hi = self.T[:, :, :2].min(1), self.T[:, :, :2].max(1)
        self.o, self.c = lo.min(0) - 1.0, cell
        i0 = np.floor((lo - self.o) / cell).astype(int)
        i1 = np.floor((hi - self.o) / cell).astype(int)
        self.n = i1.max(0) + 2
        cells, tris = [], []
        for t in range(len(self.T)):
            xs = np.arange(i0[t, 0], i1[t, 0] + 1)
            ys = np.arange(i0[t, 1], i1[t, 1] + 1)
            g = (xs[:, None] * self.n[1] + ys[None, :]).ravel()
            cells.append(g)
            tris.append(np.full(len(g), t))
        cells, tris = np.concatenate(cells), np.concatenate(tris)
        order = np.argsort(cells, kind="stable")
        self.cells, self.tris = cells[order], tris[order]

    def contains(self, Q):
        Q = np.asarray(Q, float) + np.array([1.13e-5, 2.71e-5, 0.0])   # off every edge
        g = np.floor((Q[:, :2] - self.o) / self.c).astype(int)
        key = g[:, 0] * self.n[1] + g[:, 1]
        a = np.searchsorted(self.cells, key, "left")
        b = np.searchsorted(self.cells, key, "right")
        out = np.zeros(len(Q), bool)
        for k in range(len(Q)):
            if a[k] == b[k]:
                continue
            T = self.T[self.tris[a[k]:b[k]]]
            p = Q[k]
            v0, v1, v2 = T[:, 0], T[:, 1], T[:, 2]
            d = ((v1[:, 1] - v2[:, 1]) * (v0[:, 0] - v2[:, 0]) + (v2[:, 0] - v1[:, 0]) * (v0[:, 1] - v2[:, 1]))
            l0 = ((v1[:, 1] - v2[:, 1]) * (p[0] - v2[:, 0]) + (v2[:, 0] - v1[:, 0]) * (p[1] - v2[:, 1])) / d
            l1 = ((v2[:, 1] - v0[:, 1]) * (p[0] - v2[:, 0]) + (v0[:, 0] - v2[:, 0]) * (p[1] - v2[:, 1])) / d
            l2 = 1.0 - l0 - l1
            hit = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
            z = l0 * v0[:, 2] + l1 * v1[:, 2] + l2 * v2[:, 2]
            out[k] = (np.count_nonzero(hit & (z > p[2])) % 2) == 1
        return out


def _contains(mesh, Q):
    rays = getattr(mesh, "_zrays", None)
    if rays is None:
        rays = mesh._zrays = _ZRays(mesh)
    return rays.contains(Q)


def _span(tris, res=0.02, cap=1500):
    """The bridge a roof asks for: twice the radius of the largest circle inside its plan
    (tris: (n, 3, 2)). A strip w wide reads w, a disc reads its diameter -- a true width,
    where 4 x area / perimeter reads a strip double and area / length reads a ragged roof
    short. Rasterised at res (coarser if the roof is big), then a distance transform."""
    from scipy.ndimage import distance_transform_edt
    lo, hi = tris.reshape(-1, 2).min(0), tris.reshape(-1, 2).max(0)
    res = max(res, float((hi - lo).max()) / cap)
    lo = lo - 2 * res
    shape = np.ceil((hi - lo) / res).astype(int) + 3
    grid = np.zeros(shape, bool)
    for t in tris:
        a, b, c = (t - lo) / res - 0.5                         # pixel-centre coordinates
        i0, j0 = np.floor(np.minimum(np.minimum(a, b), c)).astype(int)
        i1, j1 = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
        I, J = np.mgrid[max(i0, 0):i1 + 1, max(j0, 0):j1 + 1]
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l0 = ((b[1] - c[1]) * (I - c[0]) + (c[0] - b[0]) * (J - c[1])) / d
        l1 = ((c[1] - a[1]) * (I - c[0]) + (a[0] - c[0]) * (J - c[1])) / d
        inside = (l0 >= -1e-9) & (l1 >= -1e-9) & (l0 + l1 <= 1 + 1e-9)
        grid[I[inside], J[inside]] = True
    if not grid.any():
        return 0.0
    return float(2.0 * distance_transform_edt(grid).max() * res)


def _nozzle():
    return float(_value("src.dimensions", "NOZZLE_D"))


def _tips(V, F, FN, adj, ev, turn, convex, bed, R):
    """cadkit.print_corners on the mesh already in hand: V is in the build frame, so up is +Z."""
    from cadkit.print_corners import sites_from_edges, thin_sites
    n = _nozzle()
    out = []
    found = (sites_from_edges(V, ev, turn, convex, (0.0, 0.0, 1.0), n, normals=FN[adj])
             + thin_sites(V, F, FN, ev, turn, convex, n))
    for s in found:
        p = np.asarray(s["at"])
        out.append(dict(s, area=0.0, span=None, height=float(p[2] - bed), n=1, at=p @ R, geo=[]))
    return out


def analyse(shape, up, angle=ANGLE, tess=TESS):
    """[site dict] for a cadquery Shape building along `up` (bed = its lowest point)."""
    import trimesh
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree

    vs, fs = shape.tessellate(tess, 0.1)
    R = _rot_to_z(up)
    V = np.array([v.toTuple() for v in vs]) @ R.T
    m = trimesh.Trimesh(V, np.array(fs), process=True)
    # plain arrays, read once: every attribute read of a trimesh re-hashes the whole mesh
    V, F = np.array(m.vertices), np.array(m.faces)
    FN, TC, AF = np.array(m.face_normals), np.array(m.triangles_center), np.array(m.area_faces)
    bed = V[:, 2].min()
    eps = 1e-3
    down = -FN[:, 2]                                 # a facet past `angle` of overhang has
    thr = math.cos(math.radians(angle - FACET_TOL))  # its normal within (90-angle) of down
    f_bad = (down > thr + 1e-6) & (V[F].min(axis=1)[:, 2] > bed + eps)

    # ridges
    adj, ev = np.array(m.face_adjacency), np.array(m.face_adjacency_edges)
    sharp = m.face_adjacency_angles > math.radians(SHARP)
    convex = np.array(m.face_adjacency_convex)
    tips = _tips(V, F, FN, np.array(m.face_adjacency), ev,
                 np.degrees(np.array(m.face_adjacency_angles)), convex, bed, R)
    a, b = V[ev[:, 0]], V[ev[:, 1]]
    d = b - a
    d /= np.linalg.norm(d, axis=1)[:, None]
    mid = (a + b) / 2
    rising = np.ones(len(adj), bool)
    for side in (0, 1):
        n = FN[adj[:, side]]
        t = np.cross(n, d)
        t *= np.sign(np.einsum("ij,ij->i", t, TC[adj[:, side]] - mid))[:, None]
        rising &= t[:, 2] >= -1e-6
    elev = np.degrees(np.arcsin(np.clip(np.abs(d[:, 2]), 0, 1)))
    e_bad = (sharp & convex & rising & (elev < (90.0 - angle) - FACET_TOL)
             & (np.minimum(a[:, 2], b[:, 2]) > bed + eps))
    # an edge of a facet already reported is that facet's, not a ridge of its own
    e_bad &= ~(f_bad[adj[:, 0]] | f_bad[adj[:, 1]])

    # islands: a vertex whose every facet faces DOWN (a point the material hangs from --
    # a facet facing up or sideways means something is beside or under it), off the bed
    # and not on a reported facet
    vf = np.array(m.vertex_faces)
    nz = np.where(vf >= 0, FN[np.clip(vf, 0, None), 2], -1.0)
    low = (nz < -1e-3).all(axis=1) & (vf >= 0).any(axis=1)
    on_bad = np.zeros(len(V), bool)
    on_bad[F[f_bad].ravel()] = True
    on_bad[ev[e_bad].ravel()] = True
    v_bad = low & (V[:, 2] > bed + eps) & ~on_bad
    # ...each candidate settled against the solid
    ci = np.flatnonzero(e_bad)
    if len(ci):
        e_bad[ci[_held(m, mid[ci], angle)]] = False
    ci = np.flatnonzero(v_bad)
    if len(ci):
        v_bad[ci[_held(m, V[ci], angle)]] = False

    # sites: every hit is a point (face centre, edge midpoint, vertex), joined within NEAR
    # every hit is a point (face centre, edge midpoint, vertex) carrying its mesh vertices;
    # hits sharing a vertex are one site (a long roof tessellates into slivers whose centres
    # lie far apart), and so are hits within NEAR of each other
    pts, kind, w, ang, z, fidx, vid, geo = [], [], [], [], [], {}, [], []
    for i in np.flatnonzero(f_bad):
        fidx[len(pts)] = i
        pts.append(TC[i]); kind.append("face"); w.append(AF[i])
        ang.append(math.degrees(math.acos(min(1.0, down[i])))); z.append(V[F[i], 2].min())
        vid.append(F[i]); geo.append(V[F[i]])
    for i in np.flatnonzero(e_bad):
        pts.append(mid[i]); kind.append("ridge"); w.append(np.linalg.norm(b[i] - a[i]))
        ang.append(90.0 - elev[i]); z.append(min(a[i, 2], b[i, 2]))
        vid.append(ev[i]); geo.append(np.array([a[i], b[i]]))
    for i in np.flatnonzero(v_bad):
        pts.append(V[i]); kind.append("island"); w.append(0.0); ang.append(90.0); z.append(V[i, 2])
        vid.append(np.array([i])); geo.append(V[i][None])
    if not pts:
        return tips
    P = np.array(pts)
    pairs = cKDTree(P).query_pairs(NEAR, output_type="ndarray")
    hv = np.concatenate([[k] * len(v) for k, v in enumerate(vid)]).astype(int)
    vv = np.concatenate(vid).astype(int) + len(P)            # vertex nodes after the hits
    rows = np.concatenate([pairs[:, 0], hv]) if len(pairs) else hv
    cols = np.concatenate([pairs[:, 1], vv]) if len(pairs) else vv
    nn = len(P) + len(V)
    g = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(nn, nn))
    _, lab = connected_components(g, directed=False)
    lab = lab[:len(P)]
    _, lab = np.unique(lab, return_inverse=True)
    nc = lab.max() + 1
    Rinv = R.T
    sites = []
    members = np.argsort(lab, kind="stable")
    cuts = np.searchsorted(lab[members], np.arange(nc + 1))
    for c in range(nc):
        idx = members[cuts[c]:cuts[c + 1]]
        ks = {kind[i] for i in idx}
        area = sum(w[i] for i in idx if kind[i] == "face")
        length = sum(w[i] for i in idx if kind[i] == "ridge")
        worst = min(ang[i] for i in idx)                    # off the build direction: 0 = flat
        flat = [i for i in idx if kind[i] == "face" and ang[i] < 5.0]
        span = None
        if flat:                    # the roof's width: the widest circle it holds (flat AND sloped facets)
            span = _span(V[F[[fidx[i] for i in idx if kind[i] == "face"]]][:, :, :2])
        k = ("FLOATING" if ks == {"island"} else
             "CEILING" if flat else
             "RIDGE" if "face" not in ks else "OVERHANG")
        where = P[idx].mean(0) @ Rinv.T
        sites.append(dict(kind=k, area=area, length=length, angle=worst, span=span,
                          height=float(min(z[i] for i in idx) - bed), at=where, n=len(idx),
                          geo=[geo[i] @ Rinv.T for i in idx]))
    order = {"FLOATING": 0, "RIDGE": 1, "OVERHANG": 2, "CEILING": 3}
    sites.sort(key=lambda s: (order[s["kind"]], -(s["area"] + s["length"])))
    return sites + tips


def report(name, sites, up, min_area=0.0, min_length=0.0, ledge=2 * BEAD, quiet_ledges=False):
    shown = [s for s in sites if not (s["kind"] in ("CEILING", "OVERHANG") and s["area"] < min_area)
             and not (s["kind"] == "RIDGE" and s["length"] < min_length)
             and not (quiet_ledges and s["kind"] == "CEILING" and s["span"] is not None
                      and s["span"] <= ledge)]
    print("%-26s build up (%+.2f,%+.2f,%+.2f): %d site(s)%s" % (
        name, up[0], up[1], up[2], len(sites),
        "" if len(shown) == len(sites) else "  (%d not shown)" % (len(sites) - len(shown))))
    groups = {}
    for s in shown:                     # a grid of identical features is one line, counted
        key = (s["kind"], round(s["area"], 1), round(s["length"], 1), round(s["angle"]),
               None if s["span"] is None else round(s["span"], 2), round(s["height"], 1))
        groups.setdefault(key, []).append(s)
    for key, ss in groups.items():
        s = ss[0]
        x, y, zz = s["at"]
        if s["kind"] == "CEILING":
            what = "%7.2f mm^2  span %.2f%s" % (s["area"], s["span"],
                                                "  (a ledge, not a bridge)" if s["span"] <= ledge else "")
        elif s["kind"] == "OVERHANG":
            what = "%7.2f mm^2  %.0f deg off flat" % (s["area"], s["angle"])
        elif s["kind"] == "RIDGE":
            what = "%7.2f mm long  climbs %.0f deg (needs %.0f)" % (s["length"], 90 - s["angle"], 90 - ANGLE)
        elif s["kind"] == "TIP":
            what = "%7.2f mm long  %.0f deg in a layer, prints %.2f back of drawn: %s" % (
                s["length"], s["angle"], s["recede"], s["hint"])
        elif s["kind"] in ("POINT", "SINGLE", "STEP", "RESIDUE"):
            what = "%5.2f wide, %.1f long, ~%.1f mm3: %s" % (
                s["width"], s["length"], s["volume"], s["hint"])
        else:
            what = "a point in mid-air"
        print("    %-8s %s   %.2f above the bed  at (%.2f, %.2f, %.2f)%s" % (
            s["kind"], what, s["height"], x, y, zz, "" if len(ss) == 1 else "  and %d more like it" % (len(ss) - 1)))
    return shown


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--part", help="comma-separated part names in the scratch cache")
    ap.add_argument("--step", nargs="*", default=[], help="print-pose STEP (or .brep) files (+Z up)")
    ap.add_argument("--up", help="x,y,z build direction (overrides the declared one)")
    ap.add_argument("--angle", type=float, default=ANGLE)
    ap.add_argument("--min-area", type=float, default=0.0)
    ap.add_argument("--min-length", type=float, default=0.0)
    ap.add_argument("--quiet-ledges", action="store_true", help="hide ceilings one bead wide or less")
    a = ap.parse_args(argv)
    t0 = time.time()
    jobs = []
    skipped = []
    for n in (a.part.split(",") if a.part else []):
        try:
            jobs.append(resolve(n.strip(), tuple(float(v) for v in a.up.split(",")) if a.up else None))
        except (KeyError, ValueError, FileNotFoundError) as e:
            skipped.append("NOT CHECKED: %s" % (e.args[0] if e.args else e))
    for p in a.step:
        up = tuple(float(v) for v in a.up.split(",")) if a.up else (0.0, 0.0, 1.0)

        def ld(p=p):
            import cadquery as cq
            if p.lower().endswith(".brep"):
                return _read_brep(p)
            return cq.importers.importStep(p).val()
        jobs.append((pathlib.Path(p).stem, ld, up))
    total = 0
    for name, ld, up in jobs:
        t = time.time()
        shape = ld()
        sites = analyse(shape, up, a.angle)
        total += len(report(name, sites, up, a.min_area, a.min_length, quiet_ledges=a.quiet_ledges))
        print("    (%.1f s)" % (time.time() - t))
    for msg in skipped:
        print(msg)
    print("\n%d site(s) shown, %.0f s in all" % (total, time.time() - t0))
    return 2 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
