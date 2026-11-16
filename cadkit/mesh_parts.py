# -*- coding: utf-8 -*-
"""cadkit.mesh_parts — MESH-ONLY PARTS: what a part looks like, made straight as triangles, for
parts nobody prints and the gate never needs in detail.

    from cadkit.mesh_parts import threaded_rod_mesh, coil_mesh, with_mesh, affine_of

    proxy = cyl_x(8.0, L, x0, y=y, z=z)                       # what the gate and STEP see
    m = threaded_rod_mesh(L, major=8.0, minor=5.5, pitch=2.0)  # along +Z from z = 0
    part = with_mesh(proxy, m, affine_of(lambda w: w.rotate((0, 0, 0), (0, 1, 0), 90)
                                                    .translate((x0, y, z))))

WHY. A helix through OCCT (a leadscrew's thread cut, a spring's wire swept) is the slowest
thing a build makes -- minutes a part -- and it fails outright at some lengths (a "bad band"
where the cut hands back stacked rings, or nothing). Yet nobody prints a bought screw or a
spring, and every gate already checks them as their plain cylinder or tube. So such a part is
two things here: a PROXY SOLID (the cylinder, the tube: what the overlap gate, the STEP export
and every bounding box see) and its LOOK, a mesh computed in closed form with numpy in
milliseconds, at any length, every time.

HOW IT TRAVELS. `with_mesh(proxy, mesh, matrix)` hangs the mesh on the proxy Workplane as
`_cadkit_mesh` (already in the proxy's frame: the matrix is applied once, here). Then:
  * cadkit.scratch writes it BESIDE the proxy's BREP (mesh/<name>.override.pkl, tagged with
    the BREP file's sha1), and the view reads it in place of meshing the proxy;
  * cadkit.web.export.export() uses it in place of meshing the proxy.
Anything that rebuilds the Workplane (a translate, a kept() round trip) DROPS it: hang the
mesh on last, after the part is placed, and do not keep() a mesh-only part (it costs nothing
to make).

A mesh is export's dict: {"pos": float32 (n, 3), "tri": uint32 (m, 3), "verts": float32
(k, 3), "geo": {"f", "r", "e", "fe"}}. It is ONE face of kind "o" (other): the measure tool
snaps to its triangles, not to a radius.
"""
from __future__ import annotations

import math

import numpy as np

__all__ = ["threaded_rod_mesh", "coil_mesh", "with_mesh", "affine_of", "mesh_of", "ATTR"]

ATTR = "_cadkit_mesh"


def _pack(pos, tri) -> dict:
    pos = np.ascontiguousarray(pos, dtype=np.float32)
    tri = np.ascontiguousarray(tri, dtype=np.uint32)
    return {"pos": pos, "tri": tri, "verts": np.zeros((0, 3), dtype=np.float32),
            "geo": {"f": [["o"]], "r": [0, int(len(tri))], "e": [], "fe": [[]]}}


def _merge(meshes) -> dict:
    pos, tri, n = [], [], 0
    for m in meshes:
        pos.append(m["pos"])
        tri.append(m["tri"].astype(np.int64) + n)
        n += len(m["pos"])
    return _pack(np.concatenate(pos), np.concatenate(tri))


def _disc(r, z, n, up: bool) -> dict:
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    pos = np.c_[np.r_[0.0, r * np.cos(a)], np.r_[0.0, r * np.sin(a)], np.full(n + 1, z)]
    k = np.arange(n)
    tri = np.c_[np.zeros(n, dtype=np.int64), 1 + k, 1 + (k + 1) % n]
    if not up:
        tri = tri[:, [0, 2, 1]]
    return _pack(pos, tri)


def threaded_rod_mesh(length: float, major: float, minor: float, pitch: float,
                      flank_deg: float = 15.0, hand: str = "RH", seg: int = 36) -> dict:
    """A single-start trapezoidal thread (ISO 2904 Tr by default: 30 deg included), axis +Z
    from z = 0 to `length`, crests on Ø`major`, roots on Ø`minor`. The surface is the profile
    swept along the helix (each profile corner its own helical line, so the flats are flat and
    the flanks straight), clipped to the two end planes, with a root-Ø disc over each end.
    `seg` facets a turn."""
    rc, rr = major / 2, minor / 2
    h = rc - rr
    fl = h * math.tan(math.radians(flank_deg))       # a flank's axial run
    cw = pitch / 2 - fl                              # the tooth across its crest (Tr: 0.366 p)
    gw = pitch - cw - 2 * fl                         # the groove across its root
    assert cw > 0 and gw > 0, "the profile does not close"
    # one pitch of profile, s along the axis from the middle of a groove: (s, r)
    prof = [(0.0, rr), (gw / 2, rr), (gw / 2 + fl, rc), (gw / 2 + fl + cw, rc),
            (gw / 2 + 2 * fl + cw, rr)]
    K = len(prof)
    turns = int(math.ceil(length / pitch)) + 3
    J = turns * seg + 1                              # angle steps over the whole run
    j = np.arange(J)
    th = 2 * math.pi * j / seg
    z0 = -2 * pitch + pitch * j / seg                # start two pitches under the end
    sgn = 1.0 if hand == "RH" else -1.0
    s = np.array([p[0] for p in prof])
    r = np.array([p[1] for p in prof])
    Z = np.clip(z0[:, None] + s[None, :], 0.0, length)                       # (J, K)
    X = r[None, :] * np.cos(sgn * th)[:, None]
    Y = r[None, :] * np.sin(sgn * th)[:, None]
    pos = np.stack([X, Y, np.broadcast_to(Z, X.shape)], axis=-1).reshape(-1, 3)
    idx = (j[:, None] * K + np.arange(K)[None, :])                           # (J, K)
    a = idx[:-1, :]                                  # (j, k)
    b = idx[1:, :]                                   # (j+1, k)
    # the next profile point: k+1 on the same angle, and past the last one the first one of
    # the NEXT TURN (seg steps on)
    c = np.empty_like(a)
    d = np.empty_like(a)
    c[:, :-1] = idx[:-1, 1:]
    d[:, :-1] = idx[1:, 1:]
    nxt = np.minimum(j[:-1] + seg, J - 1)
    nxt1 = np.minimum(j[:-1] + 1 + seg, J - 1)
    c[:, -1] = nxt * K
    d[:, -1] = nxt1 * K
    ok = (j[:-1] + 1 + seg) < J                      # quads whose next turn exists
    a, b, c, d = a[ok], b[ok], c[ok], d[ok]
    t1 = np.stack([a, b, d], axis=-1).reshape(-1, 3)
    t2 = np.stack([a, d, c], axis=-1).reshape(-1, 3)
    tri = np.concatenate([t1, t2])
    if sgn < 0:
        tri = tri[:, [0, 2, 1]]
    # drop triangles squashed flat on an end plane (all three corners clipped to it)
    zt = pos[tri, 2]
    flat = ((zt <= 1e-9).all(axis=1)) | ((zt >= length - 1e-9).all(axis=1))
    tri = tri[~flat]
    used, inv = np.unique(tri.ravel(), return_inverse=True)
    rod = _pack(pos[used], inv.reshape(-1, 3))
    return _merge([rod, _disc(rr, 0.0, seg, False), _disc(rr, length, seg, True)])


def coil_mesh(pieces, coil_r: float, wire_d: float, seg: int = 24, ring: int = 8,
              hand: str = "RH") -> dict:
    """A wire of Ø`wire_d` wound on a helix of radius `coil_r` about +Z, in PIECES of
    (z0, pitch, height), each starting at angle 0 (local +X), as the steel guitar's springs
    are drawn: close-wound grip coils, the stretched working coils, grip coils. The tube's
    ring is kept square to the helix (its own lead), its ends left open (a wire's end face
    is under 0.1 mm^2 and nobody looks)."""
    out = []
    sgn = 1.0 if hand == "RH" else -1.0
    a = np.linspace(0, 2 * math.pi, ring, endpoint=False)
    for z0, pitch, height in pieces:
        n = max(2, int(math.ceil(height / pitch * seg)) + 1)
        th = np.linspace(0.0, 2 * math.pi * height / pitch, n)
        c = np.c_[coil_r * np.cos(sgn * th), coil_r * np.sin(sgn * th), z0 + pitch * th / (2 * math.pi)]
        t = np.c_[-coil_r * np.sin(sgn * th) * sgn, coil_r * np.cos(sgn * th) * sgn,
                  np.full(n, pitch / (2 * math.pi))]
        t /= np.linalg.norm(t, axis=1)[:, None]
        er = np.c_[np.cos(sgn * th), np.sin(sgn * th), np.zeros(n)]          # out from the axis
        bn = np.cross(t, er)
        bn /= np.linalg.norm(bn, axis=1)[:, None]
        er = np.cross(bn, t)
        R = wire_d / 2
        pos = (c[:, None, :] + R * (np.cos(a)[None, :, None] * er[:, None, :]
                                    + np.sin(a)[None, :, None] * bn[:, None, :])).reshape(-1, 3)
        i = np.arange(n - 1)[:, None] * ring
        k = np.arange(ring)[None, :]
        p00 = i + k
        p01 = i + (k + 1) % ring
        p10 = p00 + ring
        p11 = p01 + ring
        tri = np.concatenate([np.stack([p00, p11, p10], -1).reshape(-1, 3),     # outward
                              np.stack([p00, p01, p11], -1).reshape(-1, 3)])
        out.append(_pack(pos, tri))
    return _merge(out)


def affine_of(place) -> np.ndarray:
    """The 4x4 matrix of a placement given as a function Workplane -> Workplane (the same
    rotate / translate calls that place the proxy), read off four points it moves."""
    import cadquery as cq
    pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
    wp = cq.Workplane("XY").add([cq.Vertex.makeVertex(*p) for p in pts])
    moved = [v.toTuple() for v in place(wp).vals()]
    o = np.array(moved[0])
    m = np.eye(4)
    for k in range(3):
        m[:3, k] = np.array(moved[k + 1]) - o
    m[:3, 3] = o
    return m


def with_mesh(proxy, mesh: dict, matrix=None):
    """Hang `mesh` (in its own frame; `matrix` places it, as affine_of gives) on the proxy
    Workplane, and return the proxy."""
    if matrix is not None:
        p = mesh["pos"].astype(np.float64)
        p = p @ matrix[:3, :3].T + matrix[:3, 3]
        mesh = dict(mesh, pos=p.astype(np.float32))
        if np.linalg.det(matrix[:3, :3]) < 0:
            mesh["tri"] = mesh["tri"][:, [0, 2, 1]]
    setattr(proxy, ATTR, mesh)
    return proxy


def mesh_of(obj):
    """The mesh hung on a part, or None."""
    return getattr(obj, ATTR, None)
