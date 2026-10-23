"""TAUT CABLE ROUTES: the path a cable takes when it is pulled tight between its ends.

(user, 2026-10-22) "The wire gets pulled taut so it makes a straight line between contact
points ... where it can't go fully straight end to end because [a part] is in the way, it
instead goes around the back, staying taut between each contact point." A hand-drawn
polyline of square turns is neither: it is longer than the cable will lie, so it hides
slack that is really there and invents bends that are not.

So a route here is a SHORTEST PATH among the solids, kept `r` clear of them (the cable's
own radius plus a little): straight wherever it can be, and bent only where it wraps an
obstacle. Three stages, each cheap enough on its own:

  1. a GRID SEARCH (A*, 26 neighbours) through the free cells of a box round the two ends
     -- it only has to find the right side of every obstacle, not the shape;
  2. STRING PULLING: from each vertex, jump to the furthest later one the straight
     segment reaches with clearance;
  3. TAUTENING: slide each bend toward the line of its neighbours as far as clearance
     allows, subdivide, and repeat until the length stops falling. What is left bends
     only where it touches an obstacle's clearance band -- a string round a peg.

CLEARANCE is measured against the parts' tessellated SURFACES (trimesh, exact closest
point) with an inside test, so a point deep inside a solid is never "far from a
surface". It is an approximation of the BRep by the tessellation tolerance; the overlap
gate still checks the drawn cable against the true solids.

THIS IS SLOW ON PURPOSE AND RUNS ON DEMAND. A route is seconds to a minute; the build
must not pay that. tools/route_cables.py runs it and writes the cache the build reads
(src/cable_routes.py); re-run it when geometry under a cable moved and before the wires
are cut.
"""

from __future__ import annotations

import heapq
import math

import numpy as np
import trimesh


# ── obstacles ────────────────────────────────────────────────────────────────
def mesh_of(shape, tol=0.1, ang=0.3):
    """A cadquery Shape as one trimesh, vertices merged so the inside test works."""
    verts, tris = shape.tessellate(tol, ang)
    if not tris:
        return None
    v = np.array([(p.x, p.y, p.z) for p in verts], dtype=float)
    m = trimesh.Trimesh(v, np.array(tris, dtype=np.int64), process=True)
    m.merge_vertices()
    return m


class Obstacles:
    """The solids a cable must stay clear of, as a CLEARANCE FIELD over a box.

    `parts` is [(name, cq.Shape)]; `box` is (lo, hi), the region routes will use. Each
    solid is first CLIPPED to the box (so a chassis costs only the corner of it a route
    can reach), tessellated, its surface sampled finer than the grid and marked, and its
    interior filled; one Euclidean distance transform then gives the distance from every
    free cell to the nearest solid. A query is a lookup.

    MEMORY IS BOUNDED ON PURPOSE (user, 2026-10-22: the first version ate the machine):
    the grid is capped at `max_cells` (h grows to fit), the field is float32, and each
    part's mesh is dropped as soon as it is marked. `guard`, if given, is called after
    every part and may raise to stop a run that is growing too big.

    The field is good to about h/2, and reads conservative by that much."""

    def __init__(self, parts, box, h=0.5, tol=0.1, max_cells=6e6, guard=None):
        import cadquery as cq
        from scipy import ndimage
        lo, hi = np.asarray(box[0], float), np.asarray(box[1], float)
        while np.prod((hi - lo) / h + 5) > max_cells:
            h *= 1.25
        pad = 2.0 * h                   # clipped caps sit inside the grid, so shells close
        self.lo, self.h = lo - pad, h
        self.shape = tuple(int(v) for v in np.ceil((hi - lo + 2 * pad) / h).astype(int) + 1)
        top = self.lo + h * (np.array(self.shape) - 1)
        clip = cq.Solid.makeBox(*(hi - lo), pnt=cq.Vector(*lo))
        occ = np.zeros(self.shape, dtype=bool)
        self.names, self.times = [], {}
        import time as _t
        for name, shape in parts:
            t0 = _t.perf_counter()
            try:
                if not shape.Solids():
                    continue                # bare faces (lettering) take no room
                bb = shape.BoundingBox()
            except Exception:
                continue
            b0 = np.array([bb.xmin, bb.ymin, bb.zmin])
            b1 = np.array([bb.xmax, bb.ymax, bb.zmax])
            if np.any(b1 < lo) or np.any(b0 > hi):
                continue
            piece = shape
            if np.any(b0 < lo) or np.any(b1 > hi):
                try:
                    piece = shape.intersect(clip)
                    if not piece.Solids() or piece.Volume() < 1e-6:
                        continue
                except Exception:
                    piece = shape
            m = mesh_of(piece, tol)
            if m is None:
                continue
            pts = _surface_points(m, self.lo, top, 0.6 * h)
            del m, piece
            if not len(pts):
                continue
            idx = np.round((pts - self.lo) / h).astype(int)
            ok = np.all((idx >= 0) & (idx < np.array(self.shape)), axis=1)
            part = np.zeros(self.shape, dtype=bool)
            part[tuple(idx[ok].T)] = True
            del pts, idx
            occ |= ndimage.binary_fill_holes(part)
            del part
            self.names.append(name)
            self.times[name] = _t.perf_counter() - t0
            if guard is not None:
                guard()
        h32 = np.float32(h)
        field = ndimage.distance_transform_edt(~occ, return_indices=False).astype(np.float32)
        field *= h32
        inside = ndimage.distance_transform_edt(occ, return_indices=False).astype(np.float32)
        field[occ] = -inside[occ] * h32
        del inside
        field -= np.float32(h / 2.0)    # conservative by half a cell
        self.field = field
        self.occ = occ

    def clearance(self, pts):
        """Distance from each point to the nearest solid (negative inside one), from the
        field. Points OUTSIDE the box read as blocked: nothing is known there, so a route
        may not use it."""
        pts = np.atleast_2d(np.asarray(pts, dtype=float))
        idx = np.round((pts - self.lo) / self.h).astype(int)
        ok = np.all((idx >= 0) & (idx < np.array(self.shape)), axis=1)
        out = np.full(len(pts), -1e3)
        out[ok] = self.field[tuple(idx[ok].T)]
        return out

    def touching(self, pts, r):
        """Whether any of `pts` is within `r` of a solid -- the route's contacts."""
        return bool((self.clearance(pts) < r).any())


def _surface_points(m, lo, hi, spacing):
    """Points on the mesh's surface inside (lo, hi), no further apart than `spacing`:
    each triangle filled with a barycentric lattice of its own density, built for every
    triangle of the same density at once. (trimesh's subdivide_to_size did this by
    halving edges, iteratively, and spent five minutes on one clipped chassis.)"""
    tri = m.triangles
    t0, t1 = tri.min(axis=1), tri.max(axis=1)
    tri = tri[np.all((t1 >= lo) & (t0 <= hi), axis=1)]
    if not len(tri):
        return np.zeros((0, 3))
    edge = np.max(np.linalg.norm(tri - np.roll(tri, 1, axis=1), axis=2), axis=1)
    k = np.maximum(1, np.ceil(edge / spacing).astype(int))
    out = []
    for kk in np.unique(k):
        t = tri[k == kk]
        i, j = np.meshgrid(np.arange(kk + 1), np.arange(kk + 1), indexing="ij")
        keep = (i + j) <= kk
        u = (i[keep] / kk)[None, :, None]
        v = (j[keep] / kk)[None, :, None]
        p = t[:, None, 0] + u * (t[:, None, 1] - t[:, None, 0]) + v * (t[:, None, 2] - t[:, None, 0])
        p = p.reshape(-1, 3)
        out.append(p[np.all((p >= lo) & (p <= hi), axis=1)])
    return np.vstack(out)


# ── the route ────────────────────────────────────────────────────────────────
class Router:
    """Taut routes between pairs of points among `obstacles`, keeping `r` clear.

    `free_near` relaxes the clearance near the two ends: a cable leaves a connector
    pressed against its housing, so within that distance of an end it only has to be
    outside the solids, not `r` from them."""

    def __init__(self, obstacles: Obstacles, r: float, free_near=3.0, step=None):
        self.ob, self.r, self.free_near, self.step = obstacles, r, free_near, step

    # clearance a point needs, given the two ends
    def _need(self, pts):
        need = np.full(len(pts), self.r)
        for e in self._ends:
            d = np.linalg.norm(pts - e, axis=1)
            need = np.where(d < self.free_near, 0.0, need)
        return need

    def _clear(self, pts):
        pts = np.atleast_2d(pts)
        return self.ob.clearance(pts) >= self._need(pts) - 1e-9

    def segment_clear(self, a, b, ds=0.4):
        a, b = np.asarray(a, float), np.asarray(b, float)
        n = max(2, int(math.ceil(np.linalg.norm(b - a) / ds)) + 1)
        t = np.linspace(0.0, 1.0, n)[:, None]
        return bool(self._clear(a + t * (b - a)).all())

    def route(self, a, b, gates=()):
        """[(x, y, z)] from a to b, taut, inside the obstacles' box. Raises if there is
        none: make the box bigger, or the clearance smaller.

        GATES are where WE decide the cable goes (user, 2026-10-22: "we can also decide
        ... what objects it will be pulled taut against. For example, we have a cable
        channel"). Each is a box (lo, hi) the cable must pass through, in order -- a
        channel's two mouths, a clip, a slot in a floor. The cable is still pulled taut:
        it passes each gate wherever in the box is shortest, and while it tightens, its
        point in a gate may only slide about inside that box."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        self._ends = (a, b)
        gates = [(np.asarray(g[0], float), np.asarray(g[1], float)) for g in gates]
        if not gates and self.segment_clear(a, b):
            return [tuple(a), tuple(b)]
        self._free = None
        pts, pins, cur = [a], {}, a
        for gi, g in enumerate(gates + [None]):
            leg = self._grid(cur, b if g is None else g)
            if leg is None:
                raise RuntimeError("no route from %s to %s inside the box with %.2f clear"
                                   % (cur.round(2), "the end" if g is None else
                                      "gate %d" % gi, self.r))
            pts += leg[1:]
            if g is not None:
                pins[len(pts) - 1] = g
            cur = pts[-1]
        pts, pins = self._pull(pts, pins)
        return [tuple(map(float, p)) for p in self._tauten(pts, pins)]

    # 1 -- coarse grid search, to a point or into a gate's box
    def _grid(self, a, goal):
        lo = self.ob.lo
        hi = lo + self.ob.h * (np.array(self.ob.shape) - 1)
        h = self.step or max(1.0, min(3.0, float(np.max(hi - lo)) / 150.0))
        shape = np.maximum(np.ceil((hi - lo) / h).astype(int) + 1, 2)
        if self._free is None:                  # one free-cell map per route, not per leg
            axes = [lo[i] + h * np.arange(shape[i]) for i in range(3)]
            g = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
            self._free = self._clear(g).reshape(shape)
        free = self._free.copy()
        cell = lambda p: tuple(int(v) for v in np.clip(np.round((p - lo) / h).astype(int),
                                                          0, shape - 1))
        ia = cell(a)
        free[ia] = True
        if isinstance(goal, tuple):             # a gate: any free cell inside it
            g0, g1 = goal
            i0 = np.ceil((g0 - lo) / h).astype(int)
            i1 = np.floor((g1 - lo) / h).astype(int)
            i0, i1 = np.minimum(i0, i1), np.maximum(i0, i1)
            is_goal = lambda c: all(i0[k] <= c[k] <= i1[k] for k in range(3))
            centre = ((g0 + g1) / 2.0 - lo) / h
            half = np.abs(g1 - g0) / 2.0 / h
            heur = lambda c: float(np.linalg.norm(
                np.maximum(np.abs(np.array(c) - centre) - half, 0.0)))
            end_pt = None
        else:
            ib = cell(goal)
            free[ib] = True
            is_goal = lambda c: c == ib
            heur = lambda c: math.dist(c, ib)
            end_pt = goal
        nbr = [(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)
               if (i, j, k) != (0, 0, 0)]
        cost = {n: math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) for n in nbr}
        best, prev = {ia: 0.0}, {}
        q = [(heur(ia), 0.0, ia)]
        while q:
            _f, gc, c = heapq.heappop(q)
            if is_goal(c):
                cells = [c]
                while c in prev:
                    c = prev[c]
                    cells.append(c)
                pts = [lo + h * np.array(c, float) for c in reversed(cells)]
                pts[0] = a
                if end_pt is not None:
                    pts[-1] = end_pt
                elif len(pts) == 1:
                    pts.append(pts[0].copy())
                return pts
            if gc > best.get(c, 1e18):
                continue
            for n in nbr:
                d = (c[0] + n[0], c[1] + n[1], c[2] + n[2])
                if not (0 <= d[0] < shape[0] and 0 <= d[1] < shape[1] and 0 <= d[2] < shape[2]):
                    continue
                if not free[d]:
                    continue
                ng = gc + cost[n]
                if ng < best.get(d, 1e18):
                    best[d] = ng
                    prev[d] = c
                    heapq.heappush(q, (ng + heur(d), ng, d))
        return None

    # 2 -- string pulling, never past a gate's point
    def _pull(self, pts, pins):
        out, newpins, i = [pts[0]], {}, 0
        while i < len(pts) - 1:
            j = min([k for k in pins if k > i] + [len(pts) - 1])
            while j > i + 1 and not self.segment_clear(pts[i], pts[j]):
                j -= 1
            out.append(pts[j])
            if j in pins:
                newpins[len(out) - 1] = pins[j]
            i = j
        return out, newpins

    # 3 -- tautening
    def _tauten(self, pts, pins, rounds=40, tol=0.01):
        pts = [np.asarray(p, float) for p in pts]
        last = _length(pts)
        for _ in range(rounds):
            pts, pins = self._subdivide(pts, 6.0, pins)
            for i in range(1, len(pts) - 1):
                p, a, b = pts[i], pts[i - 1], pts[i + 1]
                ab = b - a
                t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-12), 0.0, 1.0)
                goal = a + t * ab
                if i in pins:                   # a gate's point stays in its gate
                    goal = np.clip(goal, np.minimum(*pins[i]), np.maximum(*pins[i]))
                lo_, hi_ = 0.0, 1.0             # the largest step toward the chord that clears
                for _k in range(10):
                    mid = (lo_ + hi_) / 2.0
                    q = p + mid * (goal - p)
                    if self.segment_clear(a, q) and self.segment_clear(q, b):
                        lo_ = mid
                    else:
                        hi_ = mid
                pts[i] = p + lo_ * (goal - p)
            pts, pins = self._pull(pts, pins)
            now = _length(pts)
            if last - now < tol:
                break
            last = now
        return _drop_straight(pts, keep=set(pins))

    def _subdivide(self, pts, every, pins):
        out, newpins = [pts[0]], {}
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            n = max(1, int(np.linalg.norm(b - a) // every))
            for k in range(1, n):
                out.append(a + (b - a) * k / n)
            out.append(b)
            if i + 1 in pins:
                newpins[len(out) - 1] = pins[i + 1]
        return out, newpins


def _length(pts):
    return float(sum(np.linalg.norm(np.asarray(b) - np.asarray(a)) for a, b in zip(pts, pts[1:])))


def _drop_straight(pts, deg=0.5, keep=()):
    """Remove vertices that do not turn the path (within `deg`); `keep` are gate points."""
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        if i in keep:
            out.append(pts[i])
            continue
        u = pts[i] - out[-1]
        v = pts[i + 1] - pts[i]
        nu, nv = np.linalg.norm(u), np.linalg.norm(v)
        if nu < 1e-6 or nv < 1e-6:
            continue
        if math.degrees(math.acos(np.clip(np.dot(u, v) / (nu * nv), -1.0, 1.0))) > deg:
            out.append(pts[i])
    out.append(pts[-1])
    return out


def length(pts):
    """The length of a polyline."""
    return _length([np.asarray(p, float) for p in pts])
