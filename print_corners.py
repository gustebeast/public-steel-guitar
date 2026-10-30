"""PRINTED CORNERS: draw each corner as the printer makes it, and find the ones it can't.

A drawn edge is not a printed edge, and how far the two differ depends on which way the
part builds (user, 2026-10-30, after a nut insert's sharp thin lip printed badly):

  * an edge ALONG the build direction is a NOZZLE-made corner: the bead turns it in the
    layer plane, and it comes out round whatever was drawn;
  * an edge IN the layer plane is a LAYER-made corner: layers step it;
  * a diagonal edge is between the two.

MEASURED, PETG-GF on a 0.8 nozzle with 0.4 layers, by caliper on printed rings
(2026-10-14):

    what a corner drawn SHARP prints as     convex    concave
    nozzle-made (edge along the build)       2.00      1.05
    layer-made (edge in the layers)          0.70      0.52

    the smallest DRAWN radius that prints near its drawing: fitted_joint.MIN

NOT MEASURED, and said so wherever it matters:
  * another nozzle: the radii are scaled by nozzle_d / 0.8, on the reasoning that both
    come from the bead. Print a bracket before trusting a fit on it.
  * another material. PCTG and the rest use these numbers until someone rings them.
  * a diagonal edge: the radius is blended by cos^2 of the edge's angle off the build.
    Only the two ends of that blend were printed.
  * a face meeting a flat top: no ring tested it.

DRAW PRINTED SOLIDS WITH `Printed`, DON'T HAND-ROUND (user, 2026-10-30). It knows the
part's build direction and puts each corner's radius in the profile, before the extrude, so
the cost is a few wire calls and never a fillet on a finished solid:

    P = Printed(up=(0, 0, 1), nozzle_d=0.8)
    body = P.box(40, 20, 10, z=5)
    body = body.union(P.prism(pts, along=(1, 0, 0), h=12, at=(0, 0, 3), sharp={2}))
    body = body.cut(P.cutter(pts, along=(0, 0, 1), h=8, at=(0, 0, 2)))

WHAT THE DRAWING CALLS CAN'T SEE. A cut or a union leaves a tip where two features meet, so
corner_sites() reads the finished solid, and tools run it on the mesh they already have
(sites_from_edges). Each site carries a `hint`.

WHAT IS FLAGGED. Not every edge: every block has a corner, and a 90 degree one that prints
2 mm round loses nothing anyone cares about. A TIP is a convex edge sharper than TIP_ANGLE
whose printed end stands RECEDE_MIN or more back from where it is drawn: the feature is
shorter than drawn, or the slicer drops it. `recede` is the larger of two things that take
the tip away, and it is what a site is ranked by:
  * the radius: an arc r tangent to both faces stands r * (1 / sin(a / 2) - 1) back;
  * the bead: the slicer has nothing to lay where the wedge is under a bead wide, which is
    bead / (2 * tan(a / 2)) back from the point.
An edge already drawn round is a run of small turns, so it is never a site.

THE ANGLE THAT COUNTS IS THE ONE A LAYER SEES. Each layer is a slice, so a diagonal edge is
judged by the corner its two faces make in that slice, not by their dihedral: a 45 degree slope
meeting a side wall has a 65 degree dihedral and a square corner with a wide strip behind it in
every layer, which prints fine (found on the nut insert, 2026-10-30). An edge in the layer plane
has no corner in a slice, so there the dihedral is the wedge the layers stack into.

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

__all__ = ["Printed", "corner_sites", "sites_from_edges", "printed_radius", "printable_radius",
           "recede", "seat_radius"]

MEASURED_NOZZLE = 0.8
# (convex, concave) a corner drawn sharp prints as, on MEASURED_NOZZLE
PRINTS_SHARP = {"nozzle": (2.00, 1.05), "layer": (0.70, 0.52)}
# (convex, concave) the smallest drawn radius that prints near its drawing: fitted_joint.MIN
DRAW_MIN = {"nozzle": (2.0, 2.0), "layer": (0.8, 0.8)}

SHARP_TURN = 30.0        # a mesh edge turning less than this is a curved surface's facets (deg)
TIP_ANGLE = 80.0         # a convex edge is a tip under this interior angle (deg)
RECEDE_MIN = 0.5         # ...and flagged when it recedes this many beads
LENGTH_MIN = 1.0         # ...along at least this many beads
LAYER_EDGE = 10.0        # an edge within this of the layer plane is judged by its dihedral (deg)
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


def _layer_turn(V, ev, turn, normals, up):
    """`turn`, with every edge that crosses the layers re-read as the corner its two faces make
    in a layer: their normals with the build direction taken out. An edge within LAYER_EDGE of
    the layer plane keeps its dihedral."""
    u = _unit(up)
    d = V[ev[:, 1]] - V[ev[:, 0]]
    d = d / np.maximum(np.linalg.norm(d, axis=1), 1e-12)[:, None]
    crosses = np.abs(d @ u) > math.sin(math.radians(LAYER_EDGE))
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
    tips = convex & (turn > 180.0 - tip_angle)
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
            r = printed_radius(d[k], up, sign, nozzle_d)
            half = math.radians(angle) / 2.0
            back = recede(angle, r, bead) if sign else r * (1.0 / math.sin(half) - 1.0)
            if back < recede_min * bead:
                continue
            draw = printable_radius(d[k], up, sign, nozzle_d)
            hint = ("draw it r %.2f, or end it in a flat %.2f wide, %.2f back of the point"
                    % (draw, bead, bead / (2.0 * math.tan(half))) if sign else
                    "round the mate's corner to r %.2f, or relieve this corner" % r)
            sites.append(dict(kind="TIP" if sign else "POCKET", angle=angle, radius=r,
                              recede=back, length=length, share=nozzle_share(d[k], up),
                              at=tuple((a[k] + b[k]) / 2.0), ends=(tuple(a[k]), tuple(b[k])),
                              hint=hint))
    sites.sort(key=lambda s: (-s["recede"], -s["length"]))
    return sites


def corner_sites(shape, up, nozzle_d=MEASURED_NOZZLE, mating=(), tess=TESS, **kw):
    """[site] for a cadquery Shape building along `up`, deepest first: kind TIP or POCKET,
    angle (interior, deg), radius (what it prints at), share (1 nozzle-made, 0 layer-made),
    recede (mm), length (mm), at, ends, hint. `mating` is [((x0, y0, z0), (x1, y1, z1))]."""
    import trimesh
    vs, fs = shape.tessellate(tess, 0.3)
    m = trimesh.Trimesh(np.array([v.toTuple() for v in vs]), np.array(fs), process=True)
    adj = np.array(m.face_adjacency)
    fn = np.array(m.face_normals)
    return sites_from_edges(np.array(m.vertices), np.array(m.face_adjacency_edges),
                            np.degrees(np.array(m.face_adjacency_angles)),
                            np.array(m.face_adjacency_convex), up, nozzle_d, mating,
                            normals=fn[adj], **kw)


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
    assert abs(printable_radius((1, 0, 0), up) - 0.8) < 1e-9
    assert abs(recede(90.0, 2.0, 0.8) - 2.0 * (math.sqrt(2.0) - 1.0)) < 1e-9
    # a 100 mm block: its 90 degree corners are nobody's problem
    assert not corner_sites(cq.Workplane().box(100, 60, 40).val(), up)
    # a 30 degree wedge, its tip along the build (nozzle-made) and across it (layer-made)
    pts = [(0, 0), (20, 0), (20, 20 * math.tan(math.radians(30)))]

    def wedge():
        return cq.Workplane("XY").polyline(pts).close().extrude(10)
    s = corner_sites(wedge().val(), up)
    assert s and s[0]["share"] > 0.99 and s[0]["recede"] > 3.0, s
    s = corner_sites(wedge().val(), (1, 0, 0))
    assert s and s[0]["share"] < 0.01 and s[0]["angle"] < 31.0, s
    # a 45 degree slope meeting a side wall: under TIP_ANGLE as a dihedral (the slope's corner
    # cut across the wall makes one), a square corner in every layer, so quiet
    ramp = (cq.Workplane("XZ").polyline([(0, 0), (20, 0), (20, 20), (0, 0)]).close().extrude(10)
            .rotate((0, 0, 0), (0, 0, 1), 45)).val()
    assert not [q for q in corner_sites(ramp, up) if 0.05 < q["share"] < 0.95 and q["angle"] > 80]
    # the same wedge drawn by Printed is quiet
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
    # drawn across the build the same call uses the layer radius
    L = Printed((1, 0, 0))
    v = L.prism([(0, 0), (30, 0), (30, 10), (0, 10)], (0, 0, 1), 5).val().Volume()
    assert 1490.0 < v < 1499.0, v
    # a cutter's corners are the concave ones, and a seat holds them down
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    a = P.cutter(sq, (0, 0, 1), 5).val()
    c = P.cutter(sq, (0, 0, 1), 5, seat_r=0.5, c=0.25).val()
    assert a.Volume() < c.Volume() < 500.0
    print("print_corners: self-test ok")


def report(name, sites):
    """Print a part's sites, one line each."""
    print("%-26s %d corner site(s)" % (name, len(sites)))
    for s in sites:
        print("    %-6s %5.1f deg, %s, prints r %.2f: %.2f back of drawn, %.1f long  at (%.2f, %.2f, %.2f): %s"
              % (s["kind"], s["angle"],
                 "nozzle-made" if s["share"] > 0.9 else "layer-made" if s["share"] < 0.1
                 else "diagonal", s["radius"], s["recede"], s["length"], *s["at"], s["hint"]))


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
        report(p, corner_sites(shape, up, a.nozzle))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
