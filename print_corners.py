"""PRINTED CORNERS AND THIN FEATURES: what the printer can actually lay down.

JUDGE A BEND BY ITS AXIS (user, 2026-10-30, after a nut insert's thin lip printed badly):

  * a bend IN A LAYER, made by an edge running along the build direction, is limited by how
    tightly the nozzle can turn. That is where the rounding belongs, and it is large.
  * along the BUILD AXIS there is no turning limit. A flat top meeting a wall is a clean corner
    and needs no round. What limits that axis is stacking: a feature has to be wide enough for
    a bead in every layer, and tall enough to be a whole layer.

So Printed rounds in-layer corners only, and thin_sites() judges everything by slicing the part
into layers. The lip failed that way: its 45 degree tip was narrower than a bead, not too tight
a turn. An acute tip gets BLUNTED to a flat a bead wide, not rounded.

MEASURED, PETG-GF on a 0.8 nozzle with 0.4 layers, by caliper on printed rings
(2026-10-14):

    what a corner drawn SHARP prints as     convex    concave     (a MATE allows for this)
    nozzle-made (edge along the build)       2.00      1.05
    layer-made (edge in the layers)          0.70      0.52

    the smallest DRAWN radius that prints near its drawing: fitted_joint.MIN. The layer row
    belongs to fits; a free corner in the layer plane is drawn sharp (DRAW_MIN).

NOT MEASURED, and said so wherever it matters:
  * another nozzle: the radii are scaled by nozzle_d / 0.8, on the reasoning that both
    come from the bead. Print a bracket before trusting a fit on it.
  * another material. PCTG and the rest use these numbers until someone rings them.
  * a diagonal edge: the radius is scaled by cos^2 of the edge's angle off the build.
    Only the two ends of that were printed.
  * a face meeting a flat top: no ring tested it.

DRAW PRINTED SOLIDS WITH `Printed`, DON'T HAND-ROUND (user, 2026-10-30). It knows the
part's build direction and puts each corner's radius in the profile, before the extrude, so
the cost is a few wire calls and never a fillet on a finished solid:

    P = Printed(up=(0, 0, 1), nozzle_d=0.8)
    body = P.box(40, 20, 10, z=5)
    body = body.union(P.prism(pts, along=(1, 0, 0), h=12, at=(0, 0, 3), sharp={2}))
    body = body.cut(P.cutter(pts, along=(0, 0, 1), h=8, at=(0, 0, 2)))

WHAT THE DRAWING CALLS CAN'T SEE. A cut or a union leaves thin material where two features
meet, so thin_sites() reads the finished solid, and tools run it on the mesh they already have.

THE WIDTH CHECK slices the part every layer and finds two things. A POINT is material narrower
than a bead. The real slicer (slicer_check: 0.8 nozzle, 0.40 layers, Arachne, 2026-10-30) drops it
outright under 0.30 and lays one 0.69 bead from 0.30 to 0.69, so it prints FATTER than drawn; from
0.70 one bead is the drawn width, and from 1.20 two. These are hints: slicer_check is the measure.
A SINGLE is a bead up to SOFT_WIDTH, 1.6: it prints as one line, which is not an error, and it is reported so the designer can see and accept it
(user, 2026-10-30). It pairs points
on the slice's outline whose faces oppose across material, which is a morphological opening's
answer at a fraction of the cost of rastering. A square shelf and a wall ending in a flat are
not thin: their corners do not oppose. Slices repeated by a straight-sided stretch are skipped.

THE STEP CHECK finds what a slice can't: a wedge or sheet under one layer tall.

A TIP from corner_sites() is a convex edge CROSSING the layers, sharper than TIP_ANGLE in a
layer, whose nozzle-rounded end stands RECEDE_MIN back of drawn.

A CONCAVE edge only matters against something that has to seat in it, which a solid alone
cannot say. Pass `mating`, boxes round the faces that seat; a sharp concave edge inside one
is a POCKET site, and a sharp convex edge inside one is a TIP at any angle.

A POCKET THAT SEATS A SQUARE PART: a concave corner drawn r 2.0 fouls a mate whose corner is
sharper, and a sharp one still prints about 1.05. Give the cutter `seat_r=` (the mate's corner
radius) and `c=` (the fit's clearance) and it draws min(what prints, seat_r + c). If that is
under PRINTS_SHARP, the mate's corner has to be rounded or chamfered to suit: seat_radius()
says what the mate needs.

    py -3.12 -m cadkit.print_corners part.step --up 0,0,1 --nozzle 0.8

Self-test: `python -m cadkit.print_corners --test`.
"""

import math

import numpy as np

__all__ = ["Printed", "thin_sites", "part_thin_sites", "corner_sites", "sites_from_edges", "printed_radius",
           "printable_radius", "recede", "seat_radius"]

MEASURED_NOZZLE = 0.8
# (convex, concave) a corner drawn sharp prints as, on MEASURED_NOZZLE
PRINTS_SHARP = {"nozzle": (2.00, 1.05), "layer": (0.70, 0.52)}
# (convex, concave) what Printed draws. Nozzle: fitted_joint.MIN. Layer plane: no turning limit
DRAW_MIN = {"nozzle": (2.0, 2.0), "layer": (0.0, 0.0)}

SHARP_TURN = 30.0        # a mesh edge turning less than this is a curved surface's facets (deg)
TIP_ANGLE = 80.0         # a convex edge is a tip under this interior angle (deg)
RECEDE_MIN = 0.5         # ...and flagged when it recedes this many beads
LENGTH_MIN = 1.0         # ...along at least this many beads
LAYER_EDGE = 10.0        # an edge within this of the layer plane has no corner in a layer (deg)
SOFT_WIDTH = 1.6         # the two-bead wall: the width check's softer tier
OPPOSED = -0.17          # two faces oppose when their normals' dot is under this: 80 degrees
SLICER_DROP = 0.30      # measured, 0.8 nozzle: narrower than this the slicer lays nothing
SLICER_BEAD = 0.69      # ...up to this it lays one bead this wide, fatter than the model
RESIDUE = 0.05           # a whole site narrower than this is a boolean's leftover, not a feature
SAMPLE = 0.4             # outline sample spacing, in beads
TESS = 0.05


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def nozzle_share(edge_dir, up):
    """1 for an edge along the build direction, 0 for one in the layer plane: cos^2 of the
    angle between them. The ends are measured; between them it is a blend."""
    return float(np.dot(_unit(edge_dir), _unit(up))) ** 2


def _blend(table, edge_dir, up, convex, nozzle_d):
    k = 0 if convex else 1
    s = nozzle_share(edge_dir, up)
    r = s * table["nozzle"][k] + (1.0 - s) * table["layer"][k]
    return r * nozzle_d / MEASURED_NOZZLE


def printed_radius(edge_dir, up, convex=True, nozzle_d=MEASURED_NOZZLE):
    """The radius a corner drawn SHARP comes out at."""
    return _blend(PRINTS_SHARP, edge_dir, up, convex, nozzle_d)


def printable_radius(edge_dir, up, convex=True, nozzle_d=MEASURED_NOZZLE):
    """The smallest radius to DRAW so the model matches the print."""
    return _blend(DRAW_MIN, edge_dir, up, convex, nozzle_d)


def recede(angle_deg, r, bead):
    """How far back of its drawn point a tip of interior angle `angle_deg` prints."""
    half = math.radians(angle_deg) / 2.0
    return max(r * (1.0 / math.sin(half) - 1.0), bead / (2.0 * math.tan(half)))


def seat_radius(prints_r, c):
    """The corner radius a mate needs to seat in a pocket corner printing at `prints_r`,
    with `c` of clearance."""
    return max(0.0, prints_r - c)


# -- the validator ---------------------------------------------------------------------
def _chains(ids, ev):
    """Groups of edge indices that share a vertex."""
    parent = {int(i): int(i) for i in ids}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    at = {}
    for i in ids:
        for v in ev[i]:
            j = at.setdefault(int(v), int(i))
            parent[find(int(i))] = find(j)
    out = {}
    for i in ids:
        out.setdefault(find(int(i)), []).append(int(i))
    return list(out.values())


def _crossing(V, ev, u):
    d = V[ev[:, 1]] - V[ev[:, 0]]
    d = d / np.maximum(np.linalg.norm(d, axis=1), 1e-12)[:, None]
    return np.abs(d @ u) > math.sin(math.radians(LAYER_EDGE))


def _layer_turn(V, ev, turn, normals, up):
    """`turn`, with every edge that crosses the layers re-read as the corner its two faces make
    in a layer: their normals with the build direction taken out. An edge within LAYER_EDGE of
    the layer plane keeps its dihedral."""
    u = _unit(up)
    crosses = _crossing(V, ev, u)
    m = normals - (normals @ u)[:, :, None] * u
    n = np.linalg.norm(m, axis=2)
    ok = crosses & (n > 1e-6).all(axis=1)
    c = (m[:, 0] * m[:, 1]).sum(axis=1) / np.maximum(n[:, 0] * n[:, 1], 1e-12)
    out = np.array(turn, float)
    out[ok] = np.degrees(np.arccos(np.clip(c[ok], -1.0, 1.0)))
    return out


def sites_from_edges(V, ev, turn, convex, up, nozzle_d=MEASURED_NOZZLE, mating=(),
                     tip_angle=TIP_ANGLE, recede_min=RECEDE_MIN, length_min=LENGTH_MIN,
                     normals=None):
    """[site] from a closed mesh's edge arrays: V vertices, ev (n, 2) its adjacent-face edges,
    turn their turning angles in degrees, convex their sign, and normals (n, 2, 3) the two
    faces' normals (without them every edge is judged by its dihedral). Vectorised down to the
    few candidates, so a tool already holding a mesh pays next to nothing."""
    V, ev = np.asarray(V), np.asarray(ev)
    turn, convex = np.asarray(turn), np.asarray(convex).astype(bool)
    if normals is not None:
        turn = _layer_turn(V, ev, turn, np.asarray(normals), up)
    bead = nozzle_d
    tips = convex & (turn > 180.0 - tip_angle) & _crossing(V, ev, _unit(up))
    if len(mating):
        mid = (V[ev[:, 0]] + V[ev[:, 1]]) / 2.0
        seated = np.zeros(len(ev), bool)
        for lo, hi in mating:
            seated |= ((mid >= np.asarray(lo)) & (mid <= np.asarray(hi))).all(axis=1)
        tips |= seated & (turn >= SHARP_TURN)
    sites = []
    for sign in (True, False):
        ids = np.flatnonzero(tips & (convex == sign))
        if not len(ids):
            continue
        for chain in _chains(ids, ev):
            a, b = V[ev[chain, 0]], V[ev[chain, 1]]
            d = b - a
            ln = np.linalg.norm(d, axis=1)
            length = float(ln.sum())
            if length < length_min * bead:
                continue
            k = int(np.argmax(ln))
            angle = 180.0 - float(np.average(turn[chain], weights=ln))
            # a tip turns as far as the nozzle can in a layer; a pocket's corner is what a mate
            # has to clear, so it reads the measured table
            r = (printed_radius(d[k], up, sign, nozzle_d) if not sign
                 else nozzle_share(d[k], up) * PRINTS_SHARP["nozzle"][0] * nozzle_d / MEASURED_NOZZLE)
            half = math.radians(angle) / 2.0
            back = recede(angle, r, bead) if sign else r * (1.0 / math.sin(half) - 1.0)
            if back < recede_min * bead:
                continue
            hint = ("blunt it to a flat %.2f wide, %.2f back of the point"
                    % (bead, bead / (2.0 * math.tan(half))) if sign else
                    "round the mate's corner to r %.2f, or relieve this corner" % r)
            sites.append(dict(kind="TIP" if sign else "POCKET", angle=angle, radius=r,
                              recede=back, length=length, share=nozzle_share(d[k], up),
                              at=tuple((a[k] + b[k]) / 2.0), ends=(tuple(a[k]), tuple(b[k])),
                              hint=hint))
    sites.sort(key=lambda s: (-s["recede"], -s["length"]))
    return sites


def corner_sites(shape, up, nozzle_d=MEASURED_NOZZLE, mating=(), tess=TESS, **kw):
    """[site] for a cadquery Shape building along `up`, deepest first: kind TIP or POCKET,
    angle (in a layer, deg), radius, share (1 nozzle-made, 0 layer-made), recede (mm), length
    (mm), at, ends, hint. `mating` is [((x0, y0, z0), (x1, y1, z1))]."""
    m = _mesh(shape, tess)
    adj = np.array(m.face_adjacency)
    fn = np.array(m.face_normals)
    return sites_from_edges(np.array(m.vertices), np.array(m.face_adjacency_edges),
                            np.degrees(np.array(m.face_adjacency_angles)),
                            np.array(m.face_adjacency_convex), up, nozzle_d, mating,
                            normals=fn[adj], **kw)


def _mesh(shape, tess):
    import trimesh
    vs, fs = shape.tessellate(tess, 0.3)
    return trimesh.Trimesh(np.array([v.toTuple() for v in vs]), np.array(fs), process=True)


def _to_z(up):
    """The rotation taking `up` to +Z."""
    u = _unit(up)
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(u, z)
    n, c = np.linalg.norm(v), float(u @ z)
    if n < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]) / n
    return np.eye(3) + k * n + k @ k * (1 - c)


def _slice(T, fn, z, step):
    """Sample points along a layer's outline: (points (n, 2), their outward normals (n, 2))."""
    d = T[:, :, 2] - z
    below = d < 0.0
    n0 = below.sum(axis=1)
    keep = (n0 == 1) | (n0 == 2)
    if not keep.any():
        return np.zeros((0, 2)), np.zeros((0, 2))
    t, dd, b, nx = T[keep], d[keep], below[keep], fn[keep]
    # the one vertex on its own side of the plane: both crossing edges leave it
    lone = np.where(b.sum(axis=1) == 1, b.argmax(axis=1), (~b).argmax(axis=1))
    r = np.arange(len(t))
    a0, a1, a2 = t[r, lone], t[r, (lone + 1) % 3], t[r, (lone + 2) % 3]
    d0, d1, d2 = dd[r, lone], dd[r, (lone + 1) % 3], dd[r, (lone + 2) % 3]
    p = a0 + (a1 - a0) * (d0 / (d0 - d1))[:, None]
    q = a0 + (a2 - a0) * (d0 / (d0 - d2))[:, None]
    p, q = p[:, :2], q[:, :2]
    ln = np.linalg.norm(q - p, axis=1)
    n = np.maximum(np.ceil(ln / step).astype(int), 1)
    i = np.repeat(np.arange(len(p)), n)
    k = (np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n) + 0.5) / n[i]
    m = nx[i, :2]
    return p[i] + (q[i] - p[i]) * k[:, None], m / np.maximum(np.linalg.norm(m, axis=1), 1e-12)[:, None]


def _thin_in_slice(P, N, w):
    """The pairs of outline points closer than w whose faces oppose across MATERIAL."""
    from scipy.spatial import cKDTree
    if len(P) < 2:
        return np.zeros((0, 2), int), np.zeros(0)
    pairs = cKDTree(P).query_pairs(w, output_type="ndarray")
    if not len(pairs):
        return pairs, np.zeros(0)
    a, b = pairs[:, 0], pairs[:, 1]
    keep = (N[a] * N[b]).sum(axis=1) < OPPOSED
    a, b = a[keep], b[keep]
    rel = P[b] - P[a]
    keep = ((rel * N[a]).sum(axis=1) < 0.0) & ((rel * N[b]).sum(axis=1) > 0.0)
    a, b, rel = a[keep], b[keep], rel[keep]
    return np.stack([a, b], axis=1), np.linalg.norm(rel, axis=1)


def _cluster(pts):
    """Labels for 3D points, joined within ~1.5 mm: by occupied 1 mm voxels, so a hundred
    thousand hits cost what a few thousand voxels do."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    vox, inv = np.unique(np.floor(pts).astype(int), axis=0, return_inverse=True)
    inv = np.asarray(inv).ravel()
    pairs = cKDTree(vox).query_pairs(2.0, output_type="ndarray")
    g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])) if len(pairs)
                   else ([], ([], [])), shape=(len(vox), len(vox)))
    return connected_components(g, directed=False)[1][inv]


def _width_sites(V, F, FN, nozzle_d, layer, soft):
    T = V[F]
    wall = np.abs(FN[:, 2]) < 1.0 - 1e-6
    T, fn = T[wall], FN[wall]
    side = np.abs(fn[:, 2]) < 1e-6                         # a straight wall, the same at any z
    zlo, zhi = T[:, :, 2].min(axis=1), T[:, :, 2].max(axis=1)
    bed, top = V[:, 2].min(), V[:, 2].max()
    step = SAMPLE * nozzle_d
    hits, widths, areas = [], [], []
    last, repeat = None, 1
    tiers = (nozzle_d - 0.02, soft - 0.02)
    for z in np.arange(bed + layer / 2.0, top, layer):
        live = (zlo < z) & (zhi > z)
        if last is not None and np.array_equal(live, last) and side[live].all():
            repeat += 1                                    # the same slice as the layer below
            if hits and abs(hits[-1][0, 2] - (z - layer)) < 1e-6:
                # a thin stretch runs on: carry its hits up a layer
                h = hits[-1].copy()
                hits.append(np.column_stack([h[:, :2], np.full(len(h), z), h[:, 3]]))
                widths.append(widths[-1])
                areas.append(areas[-1])
            continue
        last = live
        P, N = _slice(T[live], fn[live], z, step)
        pairs, d = _thin_in_slice(P, N, tiers[1])
        if not len(d):
            continue
        idx = pairs.ravel()
        w = np.repeat(d, 2)
        order = np.argsort(w)[::-1]
        best = np.full(len(P), np.inf)
        best[idx[order]] = w[order]                        # each point's narrowest strip
        got = np.flatnonzero(np.isfinite(best))
        tier = (best[got] < tiers[0]).astype(float)
        hits.append(np.column_stack([P[got], np.full(len(got), z), tier]))
        widths.append(best[got])
        areas.append(best[got] * step / 2.0)
    if not hits:
        return []
    H, W, A = np.concatenate(hits), np.concatenate(widths), np.concatenate(areas)
    return H, W, A


def _step_sites(V, F, FN, ev, turn, convex, nozzle_d, layer):
    """A sliver under one layer tall: a wedge in the layer plane so shallow that it stays under
    a layer for more than a bead, or a flat sheet thinner than a layer."""
    sites = []
    flat = 180.0 - turn
    limit = math.degrees(math.atan2(layer, nozzle_d))
    ids = np.flatnonzero(convex & (flat < limit) & ~_crossing(V, ev, np.array([0.0, 0.0, 1.0])))
    for chain in (_chains(ids, ev) if len(ids) else []):
        a, b = V[ev[chain, 0]], V[ev[chain, 1]]
        length = float(np.linalg.norm(b - a, axis=1).sum())
        if length >= nozzle_d:
            ang = float(flat[chain].mean())
            sites.append(dict(kind="STEP", tier=0, width=layer, length=length, volume=0.0,
                              at=tuple(a[0]), z=(float(a[:, 2].min()), float(a[:, 2].max())),
                              angle=ang, hint="a %.0f degree wedge stays under one layer for %.2f: "
                              "end it in a step a layer tall" % (ang, layer / math.tan(math.radians(ang)))))
    tz = V[F][:, :, 2]
    level = tz.max(axis=1) - tz.min(axis=1) < 1e-6
    ups, dns = level & (FN[:, 2] > 0.999), level & (FN[:, 2] < -0.999)
    zu, zd = np.unique(np.round(tz[ups, 0], 4)), np.unique(np.round(tz[dns, 0], 4))
    for u in zu:
        for w in zd[(zd < u) & (zd > u - layer + 1e-6)]:
            tu = V[F[ups & (np.abs(tz[:, 0] - u) < 1e-3)]]
            td = V[F[dns & (np.abs(tz[:, 0] - w) < 1e-3)]]
            c = tu.mean(axis=1)[:, :2]
            for t in td:
                a, b, q = t[:, :2]
                m = np.linalg.det(np.array([b - a, q - a]))
                if abs(m) < 1e-12:
                    continue
                r = c - a
                l1 = (r[:, 0] * (q - a)[1] - r[:, 1] * (q - a)[0]) / m
                l2 = ((b - a)[0] * r[:, 1] - (b - a)[1] * r[:, 0]) / m
                if ((l1 >= 0) & (l2 >= 0) & (l1 + l2 <= 1)).any():
                    sites.append(dict(kind="STEP", tier=0, width=u - w, length=0.0, volume=0.0,
                                      at=(float(a[0]), float(a[1]), float(w)), z=(float(w), float(u)),
                                      angle=0.0, hint="a sheet %.2f thick, under one layer" % (u - w)))
                    break
    return sites


def thin_sites(V, F, FN, ev, turn, convex, nozzle_d=MEASURED_NOZZLE, layer=None, soft=SOFT_WIDTH,
               min_volume=0.0):
    """[site] on a closed mesh ALREADY IN THE BUILD FRAME (+Z up), hard tier first, biggest
    first: kind POINT (narrower than a bead, a mismatch), RESIDUE (under 0.05, a boolean's
    leftover, ranked last), SINGLE (a bead up to `soft`, reported
    for the designer to accept) or STEP (a mismatch); width (the
    narrowest, mm), length, z (low, high), volume (mm3, roughly what is lost), at, hint."""
    layer = nozzle_d / 2.0 if layer is None else layer
    V, F, FN = np.asarray(V), np.asarray(F), np.asarray(FN)
    out = _step_sites(V, F, FN, np.asarray(ev), np.asarray(turn), np.asarray(convex), nozzle_d, layer)
    got = _width_sites(V, F, FN, nozzle_d, layer, soft)
    if not len(got):
        return out
    H, W, A = got
    lab = _cluster(H[:, :3])
    order = np.argsort(lab, kind="stable")
    cuts = np.searchsorted(lab[order], np.arange(lab.max() + 2))
    for c in range(lab.max() + 1):
        k = order[cuts[c]:cuts[c + 1]]
        hard = H[k, 3] > 0.5
        if hard.any():
            k = k[hard]
        vol = float(A[k].sum() * layer)
        if vol < min_volume:
            continue
        p, w = H[k], float(W[k].min())
        lo, hi = p[:, :3].min(axis=0), p[:, :3].max(axis=0)
        kind = "POINT" if hard.any() else "SINGLE"
        if hard.any() and float(W[k].max()) < RESIDUE:
            kind = "RESIDUE"
        at = tuple(p[np.argmin(W[k]), :3])
        scale = nozzle_d / MEASURED_NOZZLE
        band = "dropped" if w < SLICER_DROP * scale else "fat" if w < SLICER_BEAD * scale else None
        out.append(dict(kind=kind, tier={"POINT": 0, "SINGLE": 1, "RESIDUE": 2}[kind], width=w, volume=vol,
                        length=float(np.hypot(*(hi - lo)[:2])), z=(float(lo[2]), float(hi[2])), at=at,
                        angle=0.0, band=band if hard.any() else None, hint="a boolean's leftover: no slicer lays it" if kind == "RESIDUE"
                        else ("under a bead: under 0.30 the slicer drops it, from there it prints a 0.69 bead, "
                                         "fatter than drawn; check it with slicer_check" if hard.any() else
                                         "single-bead material: fine if you meant it, it prints as one line")))
    out.sort(key=lambda s: (s["tier"], -s["volume"]))
    return out


def part_thin_sites(shape, up, nozzle_d=MEASURED_NOZZLE, layer=None, tess=TESS, **kw):
    """thin_sites() for a cadquery Shape building along `up`; `at` and `z` stay in the build
    frame."""
    m = _mesh(shape, tess)
    V = np.array(m.vertices) @ _to_z(up).T
    fn = np.array(m.face_normals) @ _to_z(up).T
    return thin_sites(V, np.array(m.faces), fn, np.array(m.face_adjacency_edges),
                      np.degrees(np.array(m.face_adjacency_angles)),
                      np.array(m.face_adjacency_convex), nozzle_d, layer, **kw)


# -- the drawing calls -----------------------------------------------------------------
def _plane(along, at):
    """The Plane square to `along`, an axis, and the local axes its profile is drawn in:
    +-Z takes (x, y), +-X (y, z), +-Y (z, x)."""
    import cadquery as cq
    u = _unit(along)
    k = int(np.argmax(np.abs(u)))
    if abs(abs(u[k]) - 1.0) > 1e-9:
        raise ValueError("Printed draws along an axis, not %r" % (along,))
    x = [0.0, 0.0, 0.0]
    x[(k + 1) % 3] = 1.0
    return cq.Plane(origin=tuple(at), xDir=tuple(x), normal=tuple(u))


class Printed(object):
    """Draws a part's solids with each corner at the radius its orientation prints at. One
    per part: `up` is its build direction, in the frame the part is drawn in."""

    def __init__(self, up, nozzle_d=MEASURED_NOZZLE):
        self.up = tuple(_unit(up))
        self.nozzle_d = nozzle_d

    def _axis(self):
        k = int(np.argmax(np.abs(self.up)))
        return tuple(float(k == i) for i in range(3))

    def _wire(self, pts, along, at, sharp, r, cut, seat_r, c):
        import cadquery as cq
        P = [np.asarray(q, float) for q in pts]
        n = len(P)
        r = r or {}
        area = sum(P[k][0] * P[(k + 1) % n][1] - P[(k + 1) % n][0] * P[k][1] for k in range(n))
        rad, trim, unit = [0.0] * n, [0.0] * n, []
        for k in range(n):
            a, b, q = P[k - 1], P[k], P[(k + 1) % n]
            u, v = _unit(a - b), _unit(q - b)
            unit.append((u, v))
            turn = (b - a)[0] * (q - b)[1] - (b - a)[1] * (q - b)[0]
            if k in sharp or abs(turn) < 1e-9:
                continue
            convex = (turn * area > 0.0) != bool(cut)
            rad[k] = r.get(k, printable_radius(along, self.up, convex, self.nozzle_d))
            if seat_r is not None and not convex and k not in r:
                rad[k] = min(rad[k], seat_r + c)
            half = math.acos(float(np.clip(u @ v, -1.0, 1.0))) / 2.0
            trim[k] = rad[k] / math.tan(half)
        # no room on a side: the corners at its ends share it, so a thin wall ends in a round
        scale = [1.0] * n
        for k in range(n):
            j = (k + 1) % n
            room = float(np.linalg.norm(P[j] - P[k]))
            if trim[k] + trim[j] > room:
                f = room / (trim[k] + trim[j])
                scale[k], scale[j] = min(scale[k], f), min(scale[j], f)
        path = []
        for k in range(n):
            b, (u, v) = P[k], unit[k]
            t, rr = trim[k] * scale[k], rad[k] * scale[k]
            if rr <= 0.0:
                path.append(("line", b))
                continue
            half = math.acos(float(np.clip(u @ v, -1.0, 1.0))) / 2.0
            path.append(("line", b + u * t))
            path.append(("arc", b + _unit(u + v) * (rr / math.sin(half) - rr), b + v * t))
        w = cq.Workplane(_plane(along, at)).moveTo(*path[0][1])
        here = path[0][1]
        for step in path[1:]:
            if step[0] == "arc":
                w = w.threePointArc(tuple(step[1]), tuple(step[2]))
            elif np.linalg.norm(step[1] - here) > 1e-9:
                w = w.lineTo(*step[1])
            here = step[-1]
        return w.close()

    def prism(self, pts, along=None, h=1.0, at=(0, 0, 0), sharp=(), r=None):
        """The polygon `pts` extruded h along `along` (an axis; default the one nearest up),
        from `at`, drawn in that plane's local axes (see _plane). `sharp` lists corner indices
        to leave sharp, `r` overrides a corner's radius: {index: radius}."""
        along = along or self._axis()
        return self._wire(pts, along, at, sharp, r, False, None, 0.0).extrude(h)

    def cutter(self, pts, along=None, h=1.0, at=(0, 0, 0), sharp=(), r=None, seat_r=None, c=0.0):
        """A prism to CUT with: each corner radiused for the hole it leaves, so the cutter's
        convex corners get the concave radius. `seat_r` and `c`: see the module docstring."""
        along = along or self._axis()
        return self._wire(pts, along, at, sharp, r, True, seat_r, c).extrude(h)

    def box(self, w, l, h, x=0.0, y=0.0, z=0.0, sharp=()):
        """A box, world-aligned and centred on (x, y, z), extruded along the axis nearest up
        so its four rounded edges are the ones the bead turns."""
        axis = self._axis()
        k = axis.index(1.0)
        size = (w, l, h)
        a, b = size[(k + 1) % 3] / 2.0, size[(k + 2) % 3] / 2.0
        at = [x, y, z]
        at[k] -= size[k] / 2.0
        return self.prism([(-a, -b), (a, -b), (a, b), (-a, b)], axis, size[k], at, sharp)


def _test():
    import cadquery as cq
    up = (0, 0, 1)
    assert abs(printed_radius((0, 0, 1), up) - 2.0) < 1e-9
    assert abs(printed_radius((1, 0, 0), up, False) - 0.52) < 1e-9
    assert abs(printed_radius((0, 0, 1), up, True, 0.4) - 1.0) < 1e-9
    assert printable_radius((1, 0, 0), up) == 0.0
    assert abs(recede(90.0, 2.0, 0.8) - 2.0 * (math.sqrt(2.0) - 1.0)) < 1e-9
    # a 100 mm block: its 90 degree corners are nobody's problem
    assert not corner_sites(cq.Workplane().box(100, 60, 40).val(), up)
    pts = [(0, 0), (20, 0), (20, 20 * math.tan(math.radians(30)))]

    def wedge():
        return cq.Workplane("XY").polyline(pts).close().extrude(10)
    s = corner_sites(wedge().val(), up)
    assert s and s[0]["share"] > 0.99 and s[0]["recede"] > 3.0, s
    # the same edge across the build has no turning limit: the width check takes it
    assert not corner_sites(wedge().val(), (1, 0, 0))
    assert [q for q in part_thin_sites(wedge().val(), (1, 0, 0)) if q["kind"] == "POINT"]
    assert [q for q in part_thin_sites(wedge().val(), up) if q["kind"] == "POINT"]
    # a square shelf and a wall ending in a flat are not thin, a 0.6 fin claims too much, a 1.2 is an accepted single bead
    shelf = cq.Workplane().box(30, 30, 10).translate((0, 0, 5)).union(
        cq.Workplane().box(10, 10, 10).translate((0, 0, 15))).val()
    assert not part_thin_sites(shelf, up)
    assert not part_thin_sites(cq.Workplane().box(30, 2.0, 10).val(), up)
    # a lip drawn as what prints, a 0.8 x 0.4 strip: reported, not a mismatch
    lip = cq.Workplane().box(30, 0.8, 0.4).translate((0, 10.4, 0.2)).union(
        cq.Workplane().box(30, 20, 5).translate((0, 0, 2.5))).val()
    assert [q["kind"] for q in part_thin_sites(lip, (0, 0, 1)) if q["kind"] != "SINGLE"] == [], part_thin_sites(lip, (0, 0, 1))
    assert [q["kind"] for q in part_thin_sites(cq.Workplane().box(30, 0.6, 10).val(), up)] == ["POINT"]
    assert [q["band"] for q in part_thin_sites(cq.Workplane().box(30, 0.6, 10).val(), up)] == ["fat"]
    assert [q["band"] for q in part_thin_sites(cq.Workplane().box(30, 0.25, 10).val(), up)] == ["dropped"]
    assert [q["kind"] for q in part_thin_sites(cq.Workplane().box(30, 1.2, 10).val(), up)] == ["SINGLE"]
    # under one layer: a very shallow wedge, and a sheet on a block
    low = cq.Workplane("XZ").polyline([(0, 0), (30, 0), (30, 2.0)]).close().extrude(10).val()
    assert [q for q in part_thin_sites(low, up) if q["kind"] == "STEP"]
    sheet = cq.Workplane().box(10, 10, 0.3).val()
    assert [q for q in part_thin_sites(sheet, up) if q["kind"] == "STEP"]
    # the same wedge drawn by Printed is quiet at the tip
    P = Printed(up)
    r = P.prism(pts, (0, 0, 1), 10).val()
    assert r.isValid() and not corner_sites(r, up), corner_sites(r, up)
    # a seat: a sharp concave corner only counts inside a declared mating box
    pocket = cq.Workplane().box(40, 40, 20).faces(">Z").workplane().rect(20, 20).cutBlind(-10).val()
    assert not corner_sites(pocket, up)
    assert corner_sites(pocket, up, mating=[((-20, -20, -10), (20, 20, 10))])
    # a box round its axis nearest up; a thin wall's ends share the side
    b = P.box(30, 10, 5, x=1, y=2, z=3).val()
    assert b.isValid() and abs(b.Center().x - 1) < 1e-6 and abs(b.BoundingBox().zmax - 5.5) < 1e-6
    assert b.Volume() < 1500.0
    w = P.box(30, 1.6, 5).val()
    assert w.isValid() and w.BoundingBox().ylen > 1.59
    # drawn across the build a right-angle corner stays sharp: no turning limit on that axis
    L = Printed((1, 0, 0))
    v = L.prism([(0, 0), (30, 0), (30, 10), (0, 10)], (0, 0, 1), 5).val().Volume()
    assert abs(v - 1500.0) < 1e-6, v
    # a cutter's corners are the concave ones, and a seat holds them down
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    a = P.cutter(sq, (0, 0, 1), 5).val()
    c = P.cutter(sq, (0, 0, 1), 5, seat_r=0.5, c=0.25).val()
    assert a.Volume() < c.Volume() < 500.0
    print("print_corners: self-test ok")


def report(name, sites):
    """Print a part's sites, one line each."""
    print("%-26s %d site(s)" % (name, len(sites)))
    for s in sites:
        if "recede" in s:
            print("    %-6s %5.1f deg in a layer, %.2f back of drawn, %.1f long  at (%.2f, %.2f, %.2f): %s"
                  % (s["kind"], s["angle"], s["recede"], s["length"], *s["at"], s["hint"]))
        else:
            print("    %-6s %.2f wide, %.1f long, z %.1f..%.1f, ~%.1f mm3  at (%.2f, %.2f, %.2f): %s"
                  % (s["kind"], s["width"], s["length"], s["z"][0], s["z"][1], s["volume"], *s["at"], s["hint"]))


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path", nargs="*", help="a print-pose STEP or BREP")
    ap.add_argument("--up", default="0,0,1")
    ap.add_argument("--nozzle", type=float, default=MEASURED_NOZZLE)
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args(argv)
    if a.test:
        _test()
        return 0
    import cadquery as cq
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    up = tuple(float(v) for v in a.up.split(","))
    for p in a.path:
        if p.lower().endswith(".brep"):
            s = TopoDS_Shape()
            BRepTools.Read_s(s, p, BRep_Builder())
            shape = cq.Shape.cast(s)
        else:
            shape = cq.importers.importStep(p).val()
        report(p, part_thin_sites(shape, up, a.nozzle) + corner_sites(shape, up, a.nozzle))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
