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
  * cadkit.web.export.export() uses it in place of meshing the proxy;
  * a kept() round trip CARRIES it (cadkit.kept stores it beside the BREP, key.mesh.pkl).
Anything that rebuilds the Workplane (a translate, a rotate, a union) DROPS it: move a
mesh-only part with `placed(part, fn)` and join several with `fused(parts)`, which carry it.

BOUGHT HARDWARE (2026-11-16). Screws, heat-set inserts and nuts are drawn the same way: the
proxy stays what the gate and the STEP see (cadkit.fasteners' dummies, a nut's lathe body), the
look is the real thing -- an ISO thread on every shank, a knurled insert with its thread inside,
a nut threaded through: `screw_mesh`, `insert_mesh`, and `swap_bore` (any solid's plain bore
drawn threaded, the rest of it tessellated as it is). cadkit.fasteners' headed_screw, insert and
seated_insert hang them. A hundred screws are a hundred copies of one mesh, which the web export
shares (cadkit.web.export: one mesh, moved).

A mesh is export's dict: {"pos": float32 (n, 3), "tri": uint32 (m, 3), "verts": float32
(k, 3), "geo": {"f", "r", "e", "fe"}}, and optionally "feat": the ANALYTIC FEATURES in it (a
thread's helical sheet, a coil's wire), each with its frame, its numbers and the triangle range
that draws it -- so a ray tracer can solve the surface itself, to any detail, in place of those
triangles (cadkit.web.export carries them into the GLB; the desktop viewer traces them). Every
move and merge here carries them. A closed-form piece is ONE face of kind "o" (other): the
measure tool snaps to its triangles, not to a radius. A tessellated piece (swap_bore, fused)
keeps the kernel's face records, so its flats and holes still measure as flats and holes.
"""
from __future__ import annotations

import functools
import math

import numpy as np

__all__ = ["threaded_rod_mesh", "coil_mesh", "screw_mesh", "insert_mesh", "swap_bore",
           "iso_minor", "with_mesh", "affine_of", "mesh_of", "placed", "fused", "looked", "ATTR"]

ATTR = "_cadkit_mesh"


def _pack(pos, tri) -> dict:
    pos = np.ascontiguousarray(pos, dtype=np.float32)
    tri = np.ascontiguousarray(tri, dtype=np.uint32)
    return {"pos": pos, "tri": tri, "verts": np.zeros((0, 3), dtype=np.float32),
            "geo": {"f": [["o"]], "r": [0, int(len(tri))], "e": [], "fe": [[]]}}


def _feats(meshes):
    """The meshes' analytic features as one list, each triangle range moved on past the
    triangles of the meshes before it."""
    out, nt = [], 0
    for m in meshes:
        for f in m.get("feat", ()):
            out.append(dict(f, tri=[f["tri"][0] + nt, f["tri"][1] + nt]))
        nt += len(m["tri"])
    return out


def _with_feats(m, feats):
    if feats:
        m["feat"] = feats
    return m


def _merge(meshes) -> dict:
    """Meshes as one: their faces, edges and corners kept (a run of faces each); closed-form
    pieces (one "o" face each) as one "o" face. Their analytic features carried."""
    meshes = [m for m in meshes if m is not None and len(m["tri"])]
    if len(meshes) == 1:
        return meshes[0]
    feats = _feats(meshes)
    pos, tri, n = [], [], 0
    for m in meshes:
        pos.append(m["pos"])
        tri.append(m["tri"].astype(np.int64) + n)
        n += len(m["pos"])
    if all(m["geo"]["f"] == [["o"]] for m in meshes):
        return _with_feats(_pack(np.concatenate(pos), np.concatenate(tri)), feats)
    verts, f, r, e, fe = [], [], [0], [], []
    for m in meshes:
        g = m["geo"]
        verts.append(m["verts"])
        ne = len(e)
        f += g["f"]
        r += [r[-1] + (b - a) for a, b in zip(g["r"], g["r"][1:])]
        e += g["e"]
        fe += [[k + ne for k in ids] for ids in g["fe"]]
    return _with_feats({"pos": np.concatenate(pos).astype(np.float32),
                        "tri": np.concatenate(tri).astype(np.uint32),
                        "verts": np.concatenate(verts).astype(np.float32),
                        "geo": {"f": f, "r": r, "e": e, "fe": fe}}, feats)


def _moved(mesh: dict, matrix) -> dict:
    """The mesh moved by a 4x4 matrix: its points, corners and face records."""
    R, t = matrix[:3, :3], matrix[:3, 3]
    p = mesh["pos"].astype(np.float64) @ R.T + t
    out = dict(mesh, pos=p.astype(np.float32))
    if len(mesh["verts"]):
        out["verts"] = (mesh["verts"].astype(np.float64) @ R.T + t).astype(np.float32)
    if np.linalg.det(R) < 0:
        out["tri"] = mesh["tri"][:, [0, 2, 1]]
    if mesh.get("feat"):
        out["feat"] = [_moved_feat(f, R, t) for f in mesh["feat"]]
    g = mesh["geo"]
    if any(f != ["o"] for f in g["f"]) or g["e"]:
        out["geo"] = dict(g, f=[_moved_face(f, R, t) for f in g["f"]], e=[None] * 0)
        out["geo"]["fe"] = [[] for _ in g["f"]]       # edges are not carried through a move
    return out


def _moved_feat(f, R, t):
    """An analytic feature moved: its origin, axis and angle-zero direction (a mirror turns its
    hand)."""
    o = R @ np.asarray(f["o"], float) + t
    z = R @ np.asarray(f["z"], float)
    x = R @ np.asarray(f["x"], float)
    out = dict(f, o=[float(v) for v in o], z=[float(v) for v in z], x=[float(v) for v in x])
    if np.linalg.det(R) < 0:
        out["h"] = -f["h"]
    return out


def _moved_face(f, R, t):
    def P(v):
        return [round(float(x), 4) for x in R @ np.asarray(v, float) + t]

    def V(v):
        return [round(float(x), 6) for x in R @ np.asarray(v, float)]
    k = f[0]
    if k in ("p", "c", "k", "t"):
        return [k] + P(f[1:4]) + V(f[4:7]) + list(f[7:])
    if k == "s":
        return [k] + P(f[1:4]) + list(f[4:])
    return f


def _disc(r, z, n, up: bool) -> dict:
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    pos = np.c_[np.r_[0.0, r * np.cos(a)], np.r_[0.0, r * np.sin(a)], np.full(n + 1, z)]
    k = np.arange(n)
    tri = np.c_[np.zeros(n, dtype=np.int64), 1 + k, 1 + (k + 1) % n]
    if not up:
        tri = tri[:, [0, 2, 1]]
    return _pack(pos, tri)


def _rings(rings, n) -> dict:
    """A sheet through closed rings, each sampled at the same n angles (from +X, anticlockwise
    seen from +Z, each ring turned on by its optional third term, a phase): rings = [(r, z)] or
    [(r, z, phase)], r a number or a function of the angle array. Consecutive
    rings are joined by quads whose faces point OUT where the rings climb +Z at a constant
    radius (a shank read bottom to top); a sequence running the other way faces in."""
    phi = 2 * math.pi * np.arange(n) / n
    pts = []
    for ring in rings:
        rf, z = ring[:2]
        ph = phi + (ring[2] if len(ring) > 2 else 0.0)
        r = np.broadcast_to(np.asarray(rf(ph) if callable(rf) else rf, float), ph.shape)
        pts.append(np.c_[r * np.cos(ph), r * np.sin(ph), np.full(n, float(z))])
    pos = np.concatenate(pts)
    k = np.arange(n)
    tri = []
    for i in range(len(rings) - 1):
        a, b = i * n + k, i * n + (k + 1) % n
        c, d = a + n, b + n
        tri += [np.c_[a, b, d], np.c_[a, d, c]]
    return _pack(pos, np.concatenate(tri))


def _creased(m: dict, deg: float = 40.0) -> dict:
    """The mesh with every vertex where faces meet sharper than `deg` split, one copy for each
    run of faces that are near one another. The viewers smooth a normal over the faces that
    share a vertex (desktop scene.rs, the page): without this a sheet's sharp corners -- a
    screw head's top edge, its socket's hex, a thread's crest -- shade as a soft blur.
    Triangle count and order are kept, so feature ranges still hold."""
    pos, tri = m["pos"].astype(np.float64), m["tri"].astype(np.int64)
    if not len(tri):
        return m
    fn = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
    ln = np.linalg.norm(fn, axis=1)
    fn = np.where(ln[:, None] > 1e-12, fn / np.maximum(ln, 1e-300)[:, None], 0.0)
    c = math.cos(math.radians(deg))
    flat = tri.ravel()
    order = np.argsort(flat, kind="stable")
    starts = np.flatnonzero(np.r_[True, flat[order][1:] != flat[order][:-1]])
    ends = np.r_[starts[1:], len(order)]
    # ONE PASS IN PLAIN FLOATS (2026-11-17): the same greedy grouping, but a corner's normal and
    # its dot with each run's seed are Python floats, not three-element numpy calls -- those were
    # 6.8 M ndarray.any() and @ calls a build, most of the drive-travel gate's time
    fl, live = fn.tolist(), fn.any(axis=1).tolist()
    fv, ol = flat.tolist(), order.tolist()
    out, extra = list(fv), []
    nv = len(pos)
    for a, b in zip(starts.tolist(), ends.tolist()):
        v = fv[ol[a]]
        seeds = []                                     # (normal, vertex index) of each run
        for k in ol[a:b]:
            f = k // 3
            if not live[f]:                            # a degenerate face goes with the first run
                continue
            n0, n1, n2 = fl[f]
            for s0, s1, s2, vi in seeds:
                if s0 * n0 + s1 * n1 + s2 * n2 >= c:
                    out[k] = vi
                    break
            else:
                vi = v if not seeds else nv + len(extra)
                if seeds:
                    extra.append(v)
                seeds.append((n0, n1, n2, vi))
                out[k] = vi
    if not extra:
        return m
    return dict(m, pos=np.ascontiguousarray(np.r_[m["pos"], m["pos"][extra]], dtype=np.float32),
                tri=np.ascontiguousarray(np.asarray(out, dtype=np.int64).reshape(-1, 3), dtype=np.uint32))


def _flip(m: dict) -> dict:
    return dict(m, tri=m["tri"][:, [0, 2, 1]])


def _profile(rc, rr, pitch, flank_deg):
    """One pitch of a trapezoidal thread's profile, (s, r) from the middle of a groove."""
    h = rc - rr
    fl = h * math.tan(math.radians(flank_deg))       # a flank's axial run
    cw = pitch / 2 - fl                              # the tooth across its crest (Tr: 0.366 p)
    gw = pitch - cw - 2 * fl                         # the groove across its root
    assert cw > 0 and gw > 0, "the profile does not close"
    return [(0.0, rr), (gw / 2, rr), (gw / 2 + fl, rc), (gw / 2 + fl + cw, rc),
            (gw / 2 + 2 * fl + cw, rr)]


def _thread(length, rc, rr, pitch, flank_deg=15.0, hand="RH", seg=36, inward=False):
    """The bare helical surface of a thread, z = 0..length, faces out (inward=True: toward the
    axis, the inside of a nut). Returns (mesh, r_end): r_end(z, phi) is the surface's radius
    at height z, angle phi -- what an end face closes against."""
    prof = _profile(rc, rr, pitch, flank_deg)
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
    if (sgn < 0) != inward:
        tri = tri[:, [0, 2, 1]]
    # drop triangles squashed flat on an end plane (all three corners clipped to it)
    zt = pos[tri, 2]
    flat = ((zt <= 1e-9).all(axis=1)) | ((zt >= length - 1e-9).all(axis=1))
    tri = tri[~flat]
    used, inv = np.unique(tri.ravel(), return_inverse=True)
    xs = np.array([p[0] for p in prof] + [pitch])
    rs = np.array([p[1] for p in prof] + [prof[0][1]])

    def r_end(z, phi):
        t_ = np.mod(sgn * phi, 2 * math.pi)
        return np.interp(np.mod(z + 2 * pitch - pitch * t_ / (2 * math.pi), pitch), xs, rs)
    m = _pack(pos[used], inv.reshape(-1, 3))
    # THE SHEET AS A FEATURE: its surface is r = r_end(z, phi) for z in 0..length -- solid inside
    # it (a screw), or outside it (inward: a nut's hole)
    m["feat"] = [{"k": "t", "o": [0.0, 0.0, 0.0], "z": [0.0, 0.0, 1.0], "x": [1.0, 0.0, 0.0],
                  "L": float(length), "rc": float(rc), "rr": float(rr), "p": float(pitch),
                  "fl": float(flank_deg), "h": int(sgn), "in": int(bool(inward)),
                  "tri": [0, int(len(m["tri"]))]}]
    return m, r_end


def _end(z, inner, outer, n, up, phase=0.0):
    """An end face at z from radius `inner` out to `outer` (numbers or functions of the angle;
    0 inside: a disc), facing +Z if `up`; `phase` turns its samples (to meet a twisted ring)."""
    m = _rings([(inner, z, phase), (outer, z, phase)], n)
    # inner -> outer at one height: the quads face -Z as _rings builds them
    return _flip(m) if up else m


def iso_minor(d: float, pitch: float) -> float:
    """An ISO metric thread's basic minor Ø (D1 = d - 1.0825 p): where a nut's crests sit, and
    the root a screw is drawn to here, so the two draw as one surface where they meet."""
    return d - 1.0825 * pitch


def _owned(fn):
    """Memoise a pure mesh builder by its (hashable) arguments; hand each caller its own copy of
    the arrays, so nothing a caller does to its mesh reaches the next one."""
    cached = functools.lru_cache(maxsize=None)(fn)

    @functools.wraps(fn)
    def build(*a, **k):
        m = cached(*a, **k)
        return {key: (val.copy() if isinstance(val, np.ndarray) else val) for key, val in m.items()}
    build.cache_clear = cached.cache_clear
    return build


@_owned
def threaded_rod_mesh(length: float, major: float, minor: float, pitch: float,
                      flank_deg: float = 15.0, hand: str = "RH", seg: int = 36,
                      ends=(True, True)) -> dict:
    """A single-start trapezoidal thread (ISO 2904 Tr by default: 30 deg included; ISO metric
    with flank_deg=30 and minor=iso_minor), axis +Z from z = 0 to `length`, crests on Ø`major`,
    roots on Ø`minor`. The surface is the profile swept along the helix (each profile corner its
    own helical line, so the flats are flat and the flanks straight), clipped to the two end
    planes, each end closed by a disc out to the thread's own edge there (`ends`: which).
    `seg` facets a turn."""
    rod, r_end = _thread(length, major / 2, minor / 2, pitch, flank_deg, hand, seg)
    n = 4 * seg
    out = [rod]
    if ends[0]:
        out.append(_end(0.0, 0.0, lambda p: r_end(0.0, p), n, up=False))
    if ends[1]:
        out.append(_end(length, 0.0, lambda p: r_end(length, p), n, up=True))
    return _creased(_merge(out))


def _hex_r(af):
    """A hexagon `af` across its flats, corners on 0, 60, ... deg: its radius at an angle."""
    return lambda phi: (af / 2) / np.cos(np.mod(phi, math.pi / 3) - math.pi / 6)


@_owned
def screw_mesh(d: float, pitch: float, length: float, head_d: float, head_h: float,
               socket_af: float, socket_depth: float = None, seg: int = 8,
               head_seg: int = 48) -> dict:
    """A socket-head cap screw as cadkit.fasteners.headed_screw draws its proxy: axis Z, HEAD
    TOP at z = 0, the head Ø`head_d` x `head_h` below it with its hex socket (`socket_af` across
    the flats, `socket_depth` deep to the drill point's rim) sunk in the top, and an ISO metric
    thread Ø`d` x `pitch` from under the head down to z = -head_h - length. `seg` facets a turn
    of the thread, `head_seg` the head (a multiple of six: the socket's corners)."""
    assert head_seg % 6 == 0
    depth = socket_depth if socket_depth else max(0.6, 0.6 * head_h)
    rh, ch = head_d / 2, min(0.1 * head_d, 0.4)       # the head's top edge, broken
    rr = iso_minor(d, pitch) / 2
    hexr = _hex_r(socket_af)
    tip = 0.5 * socket_af * math.tan(math.radians(31))  # the 118 deg drill point
    # one sheet from the socket's point to the shank: up the socket, across the top, round the
    # edge, down the side, in under the head
    head = _rings([(0.0, -depth - tip), (hexr, -depth), (hexr, 0.0), (rh - ch, 0.0),
                   (rh, -ch), (rh, -head_h), (rr, -head_h)], head_seg)
    shank = threaded_rod_mesh(length, d, 2 * rr, pitch, 30.0, seg=seg, ends=(True, False))
    return _merge([_creased(_orient(head, +1)), _moved(shank, _translate(0, 0, -head_h - length))])


@_owned
def insert_mesh(d: float, pitch: float, od: float, length: float, seg: int = 8,
                ridges: int = None, depth: float = None) -> dict:
    """A heat-set insert as cadkit.fasteners.insert draws its proxy: axis Z, TOP at z = 0, down
    to z = -length, Ø`od` over its knurl. Two knurled bands twisted opposite ways with a plain
    groove between (what holds it in the plastic), an ISO metric thread Ø`d` x `pitch` inside."""
    ro = od / 2
    depth = depth if depth else 0.06 * od              # the knurl's teeth
    ridges = ridges if ridges else max(8, int(round(math.pi * od / 1.2)))
    n = 4 * ridges                                     # four samples a tooth
    rg = ro - 1.6 * depth                              # the groove
    lead = 2 * math.pi * ro / math.tan(math.radians(30))   # a tooth's turn, 30 deg off the axis

    def tw(z, sg):
        return sg * 2 * math.pi * z / lead             # the band's twist at z

    def knurl(z, sg):
        return lambda phi: ro - depth * 2 * np.abs(
            np.mod((phi - tw(z, sg)) * ridges / (2 * math.pi), 1.0) - 0.5)

    # every ring sampled TURNED WITH THE TWIST, so its samples sit on the teeth's corners at
    # every height and the teeth run straight up the sheet (a fixed grid saws them)
    out = []
    bands = [(-0.45 * length, 0.0, +1), (-length, -0.55 * length, -1)]
    for z0, z1, sg in bands:
        zs = np.linspace(z0, z1, max(2, int(math.ceil((z1 - z0) / 0.5)) + 1))
        out.append(_orient(_rings([(knurl(z, sg), z, tw(z, sg)) for z in zs], n), +1))
    z0, z1 = bands[0][0], bands[1][1]
    out.append(_end(z0, rg, knurl(z0, +1), n, up=False, phase=tw(z0, +1)))   # the groove's roof
    out.append(_end(z1, rg, knurl(z1, -1), n, up=True, phase=tw(z1, -1)))    # ... and floor
    out.append(_orient(_rings([(rg, z1), (rg, z0)], n), +1))
    hole, r_end = _thread(length, d / 2, iso_minor(d, pitch) / 2, pitch, 30.0, seg=seg,
                          inward=True)
    out.append(_moved(hole, _translate(0, 0, -length)))
    out.append(_end(0.0, lambda p: r_end(length, p), knurl(0.0, +1), n, up=True, phase=tw(0.0, +1)))
    out.append(_end(-length, lambda p: r_end(0.0, p), knurl(-length, -1), n, up=False,
                    phase=tw(-length, -1)))
    return _creased(_merge(out))


def _orient(m: dict, sense: int) -> dict:
    """A sheet turned to face out (+1) or in (-1) from the Z axis, judged by its triangles'
    normals against their radial direction (summed: a sheet faces one way throughout)."""
    p = m["pos"].astype(np.float64)[m["tri"]]
    nrm = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    c = p.mean(axis=1)
    rad = np.c_[c[:, 0], c[:, 1], np.zeros(len(c))]
    s = float((nrm * rad).sum())
    if s == 0.0:
        return m
    return m if (s > 0) == (sense > 0) else _flip(m)


def swap_bore(shape, d: float, pitch: float, axis_pt, axis_dir, flank_deg: float = 30.0,
              minor: float = None, hand: str = "RH", seg: int = 24, tol: float = 0.02) -> dict:
    """`shape` tessellated as it is (cadkit.web.export.mesh_shape: its faces keep their records)
    except its plain Ø`d` bore about (axis_pt, axis_dir), which is drawn threaded instead --
    roots on Ø`d`, crests on Ø`minor` (ISO metric's D1 by default) -- with a ring closing each
    end of the bore against the thread. A nut, a tapped hole: any solid with a hole a thread
    belongs in. In the shape's own frame."""
    from cadkit.web.export import mesh_shape
    sh = shape.val() if hasattr(shape, "val") else shape
    m = mesh_shape(getattr(sh, "wrapped", sh))
    ax = np.asarray(axis_dir, float)
    ax = ax / np.linalg.norm(ax)
    o = np.asarray(axis_pt, float)
    keep, drop = [], []
    for k, f in enumerate(m["geo"]["f"]):
        bore = (f[0] == "c" and abs(f[7] - d / 2) < tol
                and abs(abs(float(np.dot(f[4:7], ax))) - 1) < 1e-6
                and np.linalg.norm(np.cross(np.asarray(f[1:4], float) - o, ax)) < tol)
        (drop if bore else keep).append(k)
    if not drop:
        raise ValueError("swap_bore: no Ø%.3f bore on that axis" % d)
    r = m["geo"]["r"]
    ids = np.concatenate([np.arange(r[k], r[k + 1]) for k in drop])
    t = (m["pos"][m["tri"][ids].ravel()].astype(float) - o) @ ax
    t0, t1 = float(t.min()), float(t.max())
    L = t1 - t0
    hole, r_end = _thread(L, d / 2, (minor or iso_minor(d, pitch)) / 2, pitch, flank_deg,
                          hand, seg, inward=True)
    n = 4 * seg
    local = _merge([hole, _end(0.0, lambda p: r_end(0.0, p), d / 2, n, up=False),
                    _end(L, lambda p: r_end(L, p), d / 2, n, up=True)])
    return _merge([_sub_faces(m, keep), _moved(local, _frame(o + t0 * ax, ax))])


def _sub_faces(m, keep):
    """The mesh `m` with only faces `keep` (indices), their records and edges kept."""
    r = m["geo"]["r"]
    tris, runs, faces, fe = [], [0], [], []
    for k in keep:
        tris.append(m["tri"][r[k]:r[k + 1]])
        runs.append(runs[-1] + (r[k + 1] - r[k]))
        faces.append(m["geo"]["f"][k])
        fe.append(m["geo"]["fe"][k])
    tri = np.concatenate(tris) if tris else np.zeros((0, 3), np.uint32)
    return {"pos": m["pos"], "tri": tri.astype(np.uint32), "verts": m["verts"],
            "geo": {"f": faces, "r": runs, "e": m["geo"]["e"], "fe": fe}}


def _translate(x, y, z):
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m


def _frame(origin, zdir):
    """The matrix taking +Z at the origin onto `zdir` at `origin` (any turn about it)."""
    z = np.asarray(zdir, float) / np.linalg.norm(zdir)
    helper = np.array([1.0, 0, 0]) if abs(z[0]) < 0.9 else np.array([0, 1.0, 0])
    x = np.cross(helper, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, origin
    return m


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
        m = _pack(pos, tri)
        # THE PIECE AS A FEATURE: a tube of radius wire_d / 2 round the helix
        # (coil_r cos a, coil_r sin a, z0 + pitch a / 2 pi), a from 0 to 2 pi height / pitch
        m["feat"] = [{"k": "c", "o": [0.0, 0.0, 0.0], "z": [0.0, 0.0, 1.0], "x": [1.0, 0.0, 0.0],
                      "z0": float(z0), "p": float(pitch), "H": float(height), "R": float(coil_r),
                      "w": float(R), "h": int(sgn), "tri": [0, int(len(tri))]}]
        out.append(m)
    return _merge(out)


def _tube(c, t, ref, w, ring):
    """A tube of radius w round the centre line c (n, 3) with tangents t and a reference
    direction `ref` (n, 3) to start each ring from, its faces out (as coil_mesh's), open ends."""
    t = t / np.linalg.norm(t, axis=1)[:, None]
    bn = np.cross(t, ref)
    bn /= np.linalg.norm(bn, axis=1)[:, None]
    er = np.cross(bn, t)
    a = np.linspace(0, 2 * math.pi, ring, endpoint=False)
    pos = (c[:, None, :] + w * (np.cos(a)[None, :, None] * er[:, None, :]
                                + np.sin(a)[None, :, None] * bn[:, None, :])).reshape(-1, 3)
    i = np.arange(len(c) - 1)[:, None] * ring
    k = np.arange(ring)[None, :]
    p00, p01 = i + k, i + (k + 1) % ring
    p10, p11 = p00 + ring, p01 + ring
    tri = np.concatenate([np.stack([p00, p11, p10], -1).reshape(-1, 3),
                          np.stack([p00, p01, p11], -1).reshape(-1, 3)])
    return _pack(pos, tri)


def tube_path_mesh(pieces, d: float, ring: int = 16, seg: int = 64) -> dict:
    """A wire of Ø`d` along a path, as a string runs: straight between things, round a bearing,
    wound on an axle -- each piece an ANALYTIC FEATURE (a ray tracer draws it exact, at any
    zoom) over a triangle tube for everything else. Pieces, in the frame the mesh is in:
        ("line", a, b)                                  straight from a to b
        ("arc", centre, axis, start, angle_deg)         round `axis` (right hand) from the point
                                                        `start` through angle_deg
        ("helix", base, axis, start, pitch, height[, hand])  wound on `axis` from `start`
                                                        (its radius = |start - base| across the
                                                        axis), rising `height` along it
    The pieces are drawn each with round ends, so where one meets the next they join smooth.
    `ring` facets the wire round, `seg` an arc's full turn (the triangles only)."""
    w = d / 2
    out = []
    for pc in pieces:
        kind = pc[0]
        if kind == "line":
            a, b = np.asarray(pc[1], float), np.asarray(pc[2], float)
            L = float(np.linalg.norm(b - a))
            if L < 1e-9:
                continue
            c = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, L]])
            m = _tube(c, np.tile([0.0, 0.0, 1.0], (2, 1)), np.tile([1.0, 0.0, 0.0], (2, 1)), w, ring)
            m["feat"] = [{"k": "s", "o": [0.0, 0.0, 0.0], "z": [0.0, 0.0, 1.0], "x": [1.0, 0.0, 0.0],
                          "L": L, "w": float(w), "h": 1, "tri": [0, int(len(m["tri"]))]}]
            out.append(_moved(m, _frame(a, b - a)))
        elif kind == "arc":
            cen, ax, st = (np.asarray(v, float) for v in pc[1:4])
            ax = ax / np.linalg.norm(ax)
            r0 = st - cen
            r0 = r0 - ax * (r0 @ ax)
            R = float(np.linalg.norm(r0))
            th = math.radians(float(pc[4]))
            if R < 1e-9 or abs(th) < 1e-9:
                continue
            if th < 0:                                # a negative angle: the same arc round -axis
                ax, th = -ax, -th
            n = max(2, int(math.ceil(th / (2 * math.pi) * seg)) + 1)
            aa = np.linspace(0.0, th, n)
            c = np.c_[R * np.cos(aa), R * np.sin(aa), np.zeros(n)]
            m = _tube(c, np.c_[-np.sin(aa), np.cos(aa), np.zeros(n)], np.c_[np.cos(aa), np.sin(aa), np.zeros(n)], w, ring)
            m["feat"] = [{"k": "a", "o": [0.0, 0.0, 0.0], "z": [0.0, 0.0, 1.0], "x": [1.0, 0.0, 0.0],
                          "R": R, "A": math.degrees(th), "w": float(w), "h": 1, "tri": [0, int(len(m["tri"]))]}]
            x = r0 / R
            M = np.eye(4)
            M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, np.cross(ax, x), ax, cen
            out.append(_moved(m, M))
        elif kind == "helix":
            base, ax, st = (np.asarray(v, float) for v in pc[1:4])
            pitch, height = float(pc[4]), float(pc[5])
            hand = pc[6] if len(pc) > 6 else "RH"
            ax = ax / np.linalg.norm(ax)
            r0 = st - base
            z0 = float(r0 @ ax)
            r0 = r0 - ax * z0
            R = float(np.linalg.norm(r0))
            m = coil_mesh([(z0, pitch, height)], R, d, ring=ring, hand=hand)
            x = r0 / R
            M = np.eye(4)
            M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, np.cross(ax, x), ax, base
            out.append(_moved(m, M))
        else:
            raise ValueError("tube_path_mesh: no piece kind %r" % (kind,))
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
    Workplane, and return the proxy -- made a LOOKED Workplane, so its look rides every
    translate / rotate / mirror / union after this (see looked())."""
    if matrix is not None:
        mesh = _moved(mesh, matrix)
    setattr(proxy, ATTR, mesh)
    return looked(proxy)


# A LOOK THAT CANNOT BE DROPPED (user, 2026-11-16: "All screws and fitted inserts should render via
# the same pipeline so they have to be consistent"). A look used to survive only where its caller
# remembered placed() / fused(): a screw turned with a plain .rotate().translate(), or a washer
# .union()-ed onto it, came out a bare cylinder -- the nut block's M4s and the keyhead's M3s, while
# the drive's, placed, rendered threaded. Now any Workplane with a look is a _Looked one: its
# translate, rotate and mirror move the look with the solid, and its union merges the looks (a
# part with none lends its tessellation, as fused does). A cut or intersect hands back the plain
# solid's tessellation: the look no longer describes it.
_LOOKED = None


def _looked_cls():
    global _LOOKED
    if _LOOKED is not None:
        return _LOOKED
    import cadquery as cq

    def _carry(src, out, place):
        m = mesh_of(src)
        if m is not None:
            setattr(out, ATTR, _moved(m, affine_of(place)))
        return out

    class _Looked(cq.Workplane):
        def translate(self, vec):
            return _carry(self, super().translate(vec), lambda w: w.translate(vec))

        def rotate(self, axisStartPoint, axisEndPoint, angleDegrees):
            return _carry(self, super().rotate(axisStartPoint, axisEndPoint, angleDegrees),
                          lambda w: w.rotate(axisStartPoint, axisEndPoint, angleDegrees))

        def mirror(self, mirrorPlane="XY", basePointVector=None, union=False):
            out = super().mirror(mirrorPlane, basePointVector, union)
            if union:                                    # the solid and its image: no one matrix
                return out
            return _carry(self, out, lambda w: cq.Workplane.mirror(w, mirrorPlane, basePointVector))

        def union(self, *others, **kw):
            out = super().union(*others, **kw)
            parts = [self] + [o for o in others if isinstance(o, cq.Workplane)]
            if all(mesh_of(p) is None for p in parts):
                return out
            from cadkit.web.export import mesh_shape
            looks = []
            for p in parts:
                m = mesh_of(p)
                if m is None:
                    sh = p.val() if hasattr(p, "val") else p
                    m = mesh_shape(getattr(sh, "wrapped", sh))
                looks.append(m)
            setattr(out, ATTR, _merge(looks))
            return out

    _LOOKED = _Looked
    return _LOOKED


def looked(w):
    """`w` (a Workplane) made one whose look rides its moves and unions; anything else as is."""
    try:
        import cadquery as cq
    except ImportError:
        return w
    if isinstance(w, cq.Workplane) and type(w) is cq.Workplane:
        w.__class__ = _looked_cls()
    return w


def mesh_of(obj):
    """The mesh hung on a part, or None."""
    return getattr(obj, ATTR, None)


def placed(part, place):
    """`place(part)` (rotates, translates: a function Workplane -> Workplane), its hung mesh
    moved with it -- what a plain `.translate` drops."""
    out = place(part)
    m = mesh_of(part)
    if m is None or out is part:
        return out
    return with_mesh(out, m, affine_of(place))


def fused(parts):
    """The parts as one Workplane: their solids unioned (the proxy), their looks merged -- a
    part with no mesh of its own lends its tessellation. Two screws in a lid are one part."""
    parts = [p for p in parts if p is not None]
    if not parts:
        return None
    out = parts[0]
    for p in parts[1:]:
        out = out.union(p)
    if all(mesh_of(p) is None for p in parts):
        return out
    from cadkit.web.export import mesh_shape
    looks = []
    for p in parts:
        m = mesh_of(p)
        if m is None:
            sh = p.val() if hasattr(p, "val") else p
            m = mesh_shape(getattr(sh, "wrapped", sh))
        looks.append(m)
    setattr(out, ATTR, _merge(looks))
    return out
