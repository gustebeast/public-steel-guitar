"""JOINERY PLATE 2: the smallest joint per print-orientation pair, both halves drawn to
what they print, checked on BOTH solids.

    py -3.12 -m src.test.fit_plate2            # every pair's dims, corners, overhangs, walls, gap
    py -3.12 -m src.test.fit_plate2 --export   # ...and write src/test/test_plate2_petg_gf.step

WHAT PLATE 1 TAUGHT (fit_round3, the user's calipers and fingers, 2026-10-14, PETG-GF 0.8):
  corners   a corner prints within ~0.3 of the drawing only from: NOZZLE-made 2.0 convex
            AND 2.0 concave (a concave drawn 0.5 printed ~1.3 -- the knee is not the
            accurate point); LAYER-made 0.8 both (the standing rings).
  fit       round head (nozzle/nozzle) 0.40 for a long joint; octagon (layer/layer) 0.30;
            the mushroom bound at the neck, where its corners were drawn sharper than
            they print.
  even      the user: even clearance all round -- no separate depth relief on top.

THE RULES, per half, from how it prints (the joint frame: X the slide, Y across, Z from
the mating plane toward the tenon's head):
  NOZZLE  (profile in the layers)   corners >= NOZZLE_MIN; no overhang limit.
  LAYER   (profile across them)     corners >= LAYER_MIN; every face hanging over air must
                                    be 45 degrees or steeper: printed head-up ("up") that is
                                    the tenon's head underside / the socket's roof; printed
                                    mouth-up ("down") the socket's lip underside.
  BOTH    walls two beads; one SHARED profile drawn against both halves' rules (matched()
          radii; each face as long as its two end arcs need, up to the next whole bead);
          the tenon IS it, the socket its offset by c; then every check runs on both solids.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import sys

import cadquery as cq
import numpy as np

from src import dimensions as D
from . import fit_finder as F
from . import fit_round2 as R2

HERE = pathlib.Path(__file__).resolve().parent
BEAD = D.BEAD
WALL = 2 * BEAD
MIN = {"N": (2.0, 2.0), "L": (0.8, 0.8)}      # (convex, concave) that prints as drawn
ROOF_FLAT_MAX = 5 * BEAD                       # 4.0: a socket roof may bridge this much (round 1's
                                               # 18.3 failed; a few mm is routine in PETG)
TAG = "p2"

# (name, tenon prints, socket prints, clearances). "N" nozzle-made (the profile lies in the
# layers: the tenon stands on its end); "up" layer-made, head toward the nozzle; "down"
# layer-made, socket mouth toward the nozzle.
PAIRS = [
    ("nl_mouth_up", "N", "down", (0.25, 0.30, 0.35)),
    ("nl_mouth_down", "N", "up", (0.25, 0.30, 0.35)),
    ("ll_standing", "up", "up", (0.25, 0.30, 0.35)),
    ("ll_mouth_up", "up", "down", (0.25, 0.30, 0.35)),
]


def _kind(p):
    return "N" if p == "N" else "L"


def matched(c, tmin, smin):
    """(tenon (convex, concave), socket (convex, concave)) at clearance c."""
    tc = max(tmin[0], smin[1] - c)
    tv = max(tmin[1], smin[0] + c)
    return (tc, tv), (tv - c, tc + c)


def _beads_over(need):
    """The next whole bead ABOVE `need`: some flat is left between two end arcs."""
    return (math.floor(need / BEAD + 1e-9) + 1) * BEAD


def _arc(r, turn):
    """How much of a face an arc of radius r turning `turn` degrees takes."""
    return r * math.tan(math.radians(turn) / 2.0)


def shape(tenon, socket, cmax, size=None):
    """The shared profile's dimensions for one pair, sized at its loosest clearance.
    `size` raises the floors: {"neck": full width, "head": full width, "side": the head's
    straight side, "root": True, "trunc": mm} (plate 4: a layer/layer head that locates on
    45 degree stairs is not repeatable, so it gets straight sides to locate on)."""
    size = size or {}
    (tc, tv), (sc, sv) = matched(cmax, MIN[_kind(tenon)], MIN[_kind(socket)])
    # the head's underside at 45 degrees ALWAYS: a layer-made half may need it, and where
    # none does a flat one is only allowed, not smaller -- its two corners would each take
    # their whole radius of the face (a 90 degree underside made pair B 11.2 wide, not 4.8)
    flare = 45.0
    chamfer = socket == "up"                                         # the socket's roof
    n = size.get("neck", 2 * BEAD) / 2.0                             # neck: two beads wide
    # a mouth-down socket's mouth is a 45 degree chamfer (sharp on the bed); with "root" the
    # TENON grows the same chamfer at its root (one shared profile; plate 5: the chamfer's
    # air let a layer-made tenon's base rock), `root` up the neck -- long enough for the
    # tenon's two concave arcs onto it. Worth it only where the root corner is small
    # (layer-made: ~1.0); a nozzle-made one (2.0) keeps most of the air (plate 2)
    root = (math.ceil(2 * _arc(tv, 45.0) / math.sqrt(2.0) / (BEAD / 2.0) - 1e-9) * BEAD / 2.0
            if size.get("root") and socket == "up" else 0.0)
    # neck side: root corner to the flare corner; and the socket's lip over it two beads
    z1 = _beads_over(root + _arc(tv, 45.0 if root else 90.0) + _arc(tv, flare))
    # the socket's seat stands c off the host too (below), so its lip loses that c as well
    lip = (lambda z: z - cmax * math.sqrt(2.0)) if flare == 45.0 else (lambda z: z - 2 * cmax)
    while lip(z1) < WALL:
        z1 += BEAD
    # the underside: its flare corner to the head-side corner
    need = _arc(tv, flare) + _arc(tc, flare)
    k = 1
    while (k * BEAD * (math.sqrt(2.0) if flare == 45.0 else 1.0)) <= need + 1e-6:
        k += 1
    h = max(n + k * BEAD, size.get("head", 0.0) / 2.0)
    # the top: two 90 degree corners on a flat, or 45 degree chamfers to a short flat
    if chamfer:
        # a POINTED roof: the two chamfers meet at a rounded peak, no flat -- the bridge
        # is only the flatter middle of that peak's arc
        t = 0.0
        while h * math.sqrt(2.0) <= _arc(tc, 45.0) + _arc(tc, 90.0) + 1e-6:
            h += BEAD / 2.0
        top_turn = 45.0
    else:
        t = None
        while 2 * h <= 2 * _arc(tc, 90.0) + 1e-6:
            h += BEAD / 2.0
        top_turn = 90.0
    s = max(_beads_over(_arc(tc, flare) + _arc(tc, top_turn)), size.get("side", 0.0))
    # a socket printed mouth-down has its mouth ON THE BED, where its rounded corner would
    # start flat over air: it is a 45 degree CHAMFER instead, sharp on the bed, landing
    # just past where the tenon's root fillet runs out (tv from the neck) -- any nearer
    # and its bed end comes inside c of that fillet (the 45 tangent to the matched
    # corner came to 0.107 at c 0.25). The air it leaves is the mouth's, reported apart
    mouth = (n + tv) if socket == "up" and not root else None
    return dict(n=n, z1=z1, h=h, s=s, t=t, mouth=mouth, flare=flare, chamfer=chamfer, root=root,
                trunc=size.get("trunc", 0.0))


def _meet(l1, l2):
    """Intersection of two lines, each (point, direction), in (y, z)."""
    (p, d), (q, e) = l1, l2
    den = d[0] * e[1] - d[1] * e[0]
    u = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + u * d[0], p[1] + u * d[1])


def profile(S, o=0.0, zb=-0.5, o_root=None):
    """The closed (y, z) profile, every face moved out by `o` but the mating plane (the
    root chamfer, if any, by `o_root`, default `o`)."""
    n, z1, h, s, t = S["n"], S["z1"], S["h"], S["s"], S["t"]
    r2 = math.sqrt(0.5)
    if S["flare"] == 45.0:
        z2 = z1 + (h - n)
        under = ((n + o * r2, z1 - o * r2), (r2, r2))
    else:
        z2 = z1
        under = ((n, z1 - o), (1.0, 0.0))
    z3 = z2 + s
    neck = ((n + o, 0.0), (0.0, 1.0))
    side = ((h + o, 0.0), (0.0, 1.0))
    if S.get("root"):
        orr = o if o_root is None else o_root
        rc = ((n + S["root"] + orr * r2, orr * r2), (-r2, r2))
        pts = [_meet(rc, ((0.0, zb), (1.0, 0.0))), _meet(rc, neck)]
    else:
        pts = [(n + o, zb)]
    pts += [_meet(neck, under), _meet(under, side)]
    apex = None
    if S["chamfer"]:
        ch = ((h + o * r2, z3 + o * r2), (-r2, r2))
        pts += [_meet(side, ch)]
        if t:
            pts += [_meet(ch, ((0.0, z3 + (h - t) + o), (1.0, 0.0)))]
        else:
            apex = _meet(ch, ((0.0, 0.0), (0.0, 1.0)))   # the peak, on the centre line
    else:
        pts += [_meet(side, ((0.0, z3 + o), (1.0, 0.0)))]
    left = [(-y, z) for y, z in reversed(pts)]
    return pts + ([apex] if apex else []) + left


def _prism(pts, x0, x1):
    return (cq.Workplane("YZ").polyline(pts).close().extrude(x1 - x0)
            .translate((x0, 0, 0)))


# THE CHECKS RUN ON THE 2D SECTION: the joint is a straight extrusion of its profile, so
# a section at mid-length says everything, and its outline -- outer ring wound one way,
# holes the other -- gives each face's outward normal without probing the solid.
STEP = 0.05                                    # mm between the outline's samples


def rings(body, x=None):
    """The section's outlines at mid-length, (y, z) arrays, each wound so that its
    material lies to the LEFT (outer rings counter-clockwise, holes clockwise)."""
    x = F.L / 2.0 if x is None else x
    sec = body.val().intersect(cq.Face.makePlane(400, 400, cq.Vector(x, 0, 0),
                                                 cq.Vector(1, 0, 0)))
    out = []
    for face in sec.Faces():
        for k, w in enumerate([face.outerWire()] + face.innerWires()):
            n = max(8, int(w.Length() / STEP))
            pts = np.array([(q.y, q.z) for q in w.positions(np.linspace(0.0, 1.0, n, endpoint=False))])
            area = 0.5 * np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1])
            if (area < 0) == (k == 0):         # outer wants +area, holes -area
                pts = pts[::-1]
            out.append(pts)
    return out


def _segments(rs):
    a = np.vstack([r for r in rs])
    b = np.vstack([np.roll(r, -1, axis=0) for r in rs])
    return a, b


def _inside(pts, rs):
    """Even-odd point-in-section for many points."""
    a, b = _segments(rs)
    y, z = pts[:, 0:1], pts[:, 1:2]
    cross = ((a[:, 1] > z) != (b[:, 1] > z))
    t = (z - a[:, 1]) / np.where(b[:, 1] == a[:, 1], 1e-12, b[:, 1] - a[:, 1])
    yi = a[:, 0] + t * (b[:, 0] - a[:, 0])
    return (np.sum(cross & (y < yi), axis=1) % 2) == 1


def gaps(token, cell, above=1e-3, below=1e9, x=None):
    """The clearance as built, round the tenon's profile above z = `above`: each
    point's distance to the socket (negative where the two overlap). Sorted."""
    tr, cr = rings(token, x), rings(cell, x)
    pts = np.vstack(tr)
    pts = pts[(pts[:, 1] > above) & (pts[:, 1] < below)]
    a, b = _segments(cr)
    d = b - a
    L2 = np.maximum(np.sum(d * d, axis=1), 1e-12)
    t = np.clip(((pts[:, None, :] - a[None]) * d[None]).sum(axis=2) / L2, 0.0, 1.0)
    near = a[None] + t[..., None] * d[None]
    dist = np.sqrt(((pts[:, None, :] - near) ** 2).sum(axis=2)).min(axis=1)
    dist[_inside(pts, cr)] *= -1.0
    return np.sort(dist)


def overhang(body, down, L=None):
    """(steepest overhang, bridge) of the joint's faces printed with `down` (y, z) the
    print's down. Anything flatter than 45 degrees is a BRIDGE -- the roof's flat AND the
    flatter parts of the arcs running into it -- measured by its width across (it must be
    under ROOF_FLAT_MAX); the overhang is the steepest face outside it (45 is the limit).
    The section's own outer box (bed, top, sides) is not joint and is left out."""
    rs = rings(body, None if L is None else L / 2.0)
    a, b = _segments(rs)
    allp = np.vstack(rs)
    lo, hi = allp.min(axis=0), allp.max(axis=0)
    m = (a + b) / 2.0
    keep = np.all((np.abs(m - lo) > 1e-3) & (np.abs(m - hi) > 1e-3), axis=1)
    d = (b - a)[keep]
    n = np.stack([d[:, 1], -d[:, 0]], axis=1)          # material on the left: air to the right
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    dot = n @ np.array(down)
    flat = dot > math.sqrt(0.5) + 0.005
    steep = (dot > 0) & ~flat
    worst = math.degrees(math.asin(min(1.0, dot[steep].max()))) if steep.any() else 0.0
    # each RUN of flat faces, unbroken round the outline, is one bridge: its width across
    full = np.zeros(len(m), bool)
    full[np.flatnonzero(keep)[flat]] = True
    widest, run = 0.0, []
    for i in range(len(full) + 1):
        if i < len(full) and full[i]:
            run.append(m[i, 0])
        elif run:
            widest, run = max(widest, max(run) - min(run)), []
    return worst, float(widest)


DOWN = {"up": (0.0, -1.0), "down": (0.0, 1.0)}   # the print's down in the joint's (y, z)


def _mouth_corners(S, c, socket):
    """The skip rule for a mouth-down socket's corners: those on the bed stay sharp, and
    the chamfer's corner onto the neck wall faces only the mouth's air, so it takes the
    socket's own printable minimum and leaves that wall to the corner that mates."""
    if S.get("root"):                    # the shared chamfer: only its bed edges stay sharp
        return lambda u, v: True if abs(v) < 1e-6 else None
    if not S["mouth"]:
        return None
    knee = S["mouth"] - (S["n"] + c)                     # the chamfer onto the wall, z
    return lambda u, v: True if abs(v) < 1e-6 else (
        MIN[_kind(socket)][0] if abs(v - knee) < 1e-6 else None)


# a layer-made half's END RELIEF: (distance in from the end, how far the air beside the
# profile grows there), joined straight. Plate 3's (0.2 at the tip, nothing by 1.6) missed:
# the user's calipers on a D2 head (drawn 3.20) read 2.6 at the tip, 3.33 about 3 mm in,
# 3.1 in the middle -- the nozzle slows into each end's turn and over-extrudes just before
# it, so the bulge peaks ~3 mm in whatever is drawn there. LEAD takes 0.12 a side off from
# the tip to 3 mm (3.33 -> ~3.1, the middle's), back to nothing by 4.5
LEAD_P3 = ((0.0, 0.2), (2 * BEAD, 0.0))
LEAD = ((0.0, 0.12), (3.0, 0.12), (4.5, 0.0))


def _lead(body, hw, z0, z1, zlim, stations=LEAD, keep=None, L=None):
    """`body` with the END RELIEF `stations` at both joint ends: the air beside its profile
    grown by each station's amount at its distance in, lofted between (the loft from the
    ROUNDED section keeps every corner as drawn). Only z in `zlim` is cut, and with
    `keep` = (y, z) nothing beyond |y| below z -- the SEAT face outside the mouth (plate 5:
    a seat cut 0.12 at the ends left the last layer an island over the middle)."""
    L = F.L if L is None else L
    x = L / 2.0
    sec = body.val().intersect(cq.Face.makePlane(400, 400, cq.Vector(x, 0, 0), cq.Vector(1, 0, 0)))
    rect = cq.Face.makeFromWires(cq.Wire.makePolygon(
        [cq.Vector(x, -hw, z0), cq.Vector(x, hw, z0), cq.Vector(x, hw, z1), cq.Vector(x, -hw, z1)],
        close=True))
    tools = []
    for f in rect.cut(sec).Faces():
        w = f.outerWire()
        rings = []
        for _d, e in stations:
            g = w.offset2D(e, "intersection")[0] if e > 0 else w
            assert len(g.Edges()) == len(w.Edges()), "lead-in outline changed shape: the loft would twist"
            rings.append(g)
        for sgn, x0 in ((1.0, 0.0), (-1.0, L)):
            tools.append(cq.Solid.makeLoft([g.moved(cq.Location(cq.Vector(x0 + sgn * d - x, 0, 0)))
                                            for (d, _e), g in zip(stations, rings)], True))
    cut = tools[0]
    for t in tools[1:]:
        cut = cut.fuse(t)
    cut = cut.intersect(
        cq.Solid.makeBox(L + 2.0, 4 * hw + 2.0, zlim[1] - zlim[0], cq.Vector(-1.0, -2 * hw - 1.0, zlim[0])))
    if keep:
        ky, kz = keep
        for y0 in (ky, -2 * hw - 1.0):
            cut = cut.cut(cq.Solid.makeBox(L + 2.0, 2 * hw + 1.0 - ky, kz - zlim[0],
                                           cq.Vector(-1.0, y0, zlim[0])))
    out = body.val().cut(cut)
    if not (out.isValid() and len(out.Solids()) == 1):
        out = body.val().cut(cut, tol=1e-5)
    assert out.isValid() and len(out.Solids()) == 1, "lead-in broke the solid (%d solids, valid %s)" % (
        len(out.Solids()), out.isValid())
    return cq.Workplane("XY").newObject([out])


def make_pair(name, tenon, socket, c, S, host_w, top, g=None, relief="both", L=None):
    """(token, cell, report) at clearance c, the socket's seat `g` off the host (default c);
    `relief` says which layer-made halves take S["lead"]: both / tenon / socket / none."""
    g = c if g is None else g
    L = F.L if L is None else L
    rt, rs = matched(c, MIN[_kind(tenon)], MIN[_kind(socket)])
    # with a ROOT chamfer the socket's sharp bed edge faces the tenon's ROUND root corner;
    # that one chamfer steps out (quarter-tenths) until it clears by c
    d = 0.0
    while True:
        hw = host_w / 2.0
        token = F._box(0, L, -hw, hw, -2 * WALL, 0).union(_prism(profile(S), 0.0, L))
        if S.get("trunc"):               # the tip cut flat clear of a bridged socket roof (user)
            token = token.cut(F._box(-1.0, L + 1.0, -hw, hw, S["tip"] - S["trunc"], S["tip"] + 1.0))
        # the SEAT is a face of the joint like any other: the socket stands c off the host, so
        # its mouth corner is the tenon root fillet's true offset (seated flush, that corner
        # rounded against the seat and pinched the gap to 0 for 1.7 up the neck). The cavity is
        # cut c low in the socket's own frame; `seated` puts the socket where it rides
        cell = (F._box(0, L, -hw, hw, 0, top)
                .cut(_prism(profile(S, c, -1.0, c + d), -1.0, L + 1.0).translate((0, 0, -g))))
        # a seat closer than c (the user: the seam shows on the instrument's front face) keeps
        # c only over the tenon's root fillet -- a pocket c - g deep, as wide as that fillet
        # runs -- so the mouth corner is still the fillet's true offset, and the rest of the
        # face comes down to g
        n_root = None
        if g < c - 1e-9:
            n_root = S["n"] + rt[1] + 0.05          # a hair past the fillet: room for the full arc
            cell = cell.cut(F._box(-1.0, L + 1.0, -n_root, n_root, -1.0, c - g))
        if S["mouth"]:
            m = S["mouth"]
            cell = cell.cut(_prism([(m + 1.0, -1.0), (0.0, m), (-m - 1.0, -1.0)], -1.0, L + 1.0))
        token, lt = F._round(token, "x", rt, False)
        skip = _mouth_corners(S, c, socket)
        if n_root:                       # the pocket's own edge corners face only air: as drawn
            skip0 = skip
            skip = lambda u, v: True if abs(abs(u) - n_root) < 1e-6 else (skip0(u, v) if skip0 else None)
        cell, ls = F._round(cell, "x", rs, False, skip=skip)
        if S.get("lead"):
            if tenon != "N" and relief in ("both", "tenon"):
                token = _lead(token, hw, 0.0, S["tip"] + 1.0, (0.0, 1e3), S["lead"], L=L)
            if socket != "N" and relief in ("both", "socket"):
                # a seat OFF the bed takes the lead-in too (the band under it keeps the offset
                # outline's edges one-for-one); one ON the bed must not be undercut
                # a mouth-up socket's flat cavity end prints as a LAYER face: relieved too, it
                # stepped a layer deeper at the joint's ends (plate 6 B, seen in the slicer by
                # the user) -- the relief stops at it, as at the seat
                cell = _lead(cell, hw, 0.0 if socket == "up" else -0.3, top,
                             (-1.0, top - 1e-3) if socket == "up" else (-1.0, S["tip"] + c - g - 1e-3),
                             S["lead"], None if socket == "up" else (S["n"] + c + rs[0] + 0.05, 0.3), L=L)
        seated = cell.translate((0, 0, g))
        gp = gaps(token, seated, x=L / 2.0)
        if not S.get("root") or gp[0] >= min(c, g) - 0.005 or d > 1.0:
            break
        d = round(d + 0.025, 3)
    # the joint's own clearance is measured above the mouth, the mouth's air reported apart
    # and below a cut-flat tip, whose extra air is by design (reported in mouth_air's max)
    below = S["tip"] - S["trunc"] - 0.5 if S.get("trunc") else 1e9
    above = (S["mouth"] + c) if S["mouth"] else (S["root"] + 1.0) if S.get("root") else 1e-3
    if g < c - 1e-9:                     # faces that MEET: the root fillet's tail sits in the
        above = max(above, c - g)        # pocket, beside faces touching by design
    gj = gaps(token, seated, above, below, x=L / 2.0)
    # a corner FAILS only below what its half can print: one drawn short of its matched
    # radius (no room) still prints as drawn, and the measured gap says whether the pair
    # still meets evenly
    off = [(half, kind, used) for half, log, mn in (("tenon", lt, MIN[_kind(tenon)]),
                                                     ("socket", ls, MIN[_kind(socket)]))
           for _u, _v, kind, used in log
           if kind and (used is None or used < mn[0 if kind == "convex" else 1] - 1e-6)]
    rep = dict(c=c, tenon_r=rt, socket_r=rs, gap=(gj[0] if g < c - 1e-9 else gp[0], gj[-1]), mouth_air=gp[-1], corners_off=off,
               root_step=d,
               tenon_overhang=(None, 0.0) if tenon == "N" else overhang(token, DOWN[tenon], L),
               socket_overhang=(None, 0.0) if socket == "N" else overhang(cell, DOWN[socket], L))
    return token, cell, rep


def halves(tenon, socket, c, L, g, host_w, size=None, relief="socket"):
    """The fit-tested joint for an INSTRUMENT site (step 2 of the user's sequence, until it
    moves into cadkit): (tenon, cavity, S), both in the joint frame -- X the slide (0..L),
    Y across, Z the depth from the mating plane (the tenon host's face). The tenon carries
    its host slab 2 * WALL back behind that plane (fused into the real host; host_w must fit
    inside it) with the root fillets in it; the cavity is what the socket host loses, from
    `g` (where its material starts: its seat, or an assembly standoff) to the cavity's end."""
    S = dict(shape(tenon, socket, c, size), lead=LEAD)
    S["tip"] = max(z for _y, z in profile(S))
    top = S["tip"] + c + 2 * WALL
    token, cell, rep = make_pair("site", tenon, socket, c, S, host_w, top, g=g, relief=relief, L=L)
    assert rep["gap"][0] >= min(c, g) - 0.005, "the joint pinches to %.3f" % rep["gap"][0]
    hw = host_w / 2.0
    cavity = F._box(0, L, -hw, hw, 0, top).cut(cell).translate((0, 0, g))
    return token, cavity, S


REPORT = {}


def mark_size(face_w, widest):
    """The biggest number that fits a host's face (host_w across, the joint's length L
    along), WALL clear all round: each step's figure as cut_mark draws it, tried from
    the biggest down in half beads (its stroke and depth stay -- the material under it
    is two beads either way)."""
    from src.version_mark import cut_mark
    face = F._box(0, F.L, -face_w / 2.0, face_w / 2.0, -2 * WALL, 0)
    h = F.L - 2 * WALL
    while h > 2 * BEAD:
        mk = dict(height=h, stroke=0.8)
        ok = True
        for k in range(1, widest + 1):
            gb = face.val().cut(cut_mark(face, k, (F.L / 2.0, 0.0, 0.0), (0, 0, 1), (0, 1, 0), **mk).val())
            gb = gb.BoundingBox()
            if gb.xmin < WALL - 1e-6 or gb.xmax > F.L - WALL + 1e-6 or                     gb.ymin < -face_w / 2.0 + WALL - 1e-6 or gb.ymax > face_w / 2.0 - WALL + 1e-6:
                ok = False
                break
        if ok:
            return mk
        h -= BEAD / 2.0
    return dict(height=2 * BEAD, stroke=0.8)


def finders(pairs=None):
    out = []
    for name, tenon, socket, steps, *opt in (pairs or PAIRS):
        S = shape(tenon, socket, max(steps), opt[0].get("size") if opt else None)
        S["lead"] = opt[0].get("lead") if opt else None          # END RELIEF stations
        S["seat"] = opt[0].get("seat") if opt else None          # per-step seat gaps
        S["relief"] = opt[0].get("relief") if opt else None      # relief halves (or per step)
        prof = profile(S)
        tip = max(z for _y, z in prof)
        host_w = 2 * (S["h"] + max(steps) + WALL)
        top = tip + max(steps) + 2 * WALL                   # roof two beads + the number's depth
        S.update(host_w=host_w, top=top, tip=tip,
                 lip=min((S["z1"] - c * math.sqrt(2.0)) if S["flare"] == 45.0 else S["z1"] - 2 * c
                         for c in steps),
                 side_wall=host_w / 2.0 - (S["h"] + max(steps)), roof=top - (tip + max(steps)))
        REPORT[name] = dict(shape=S, steps=[])

        def make(k, d, name=name, tenon=tenon, socket=socket, S=S, host_w=host_w, top=top):
            g = S["seat"][k] if S.get("seat") else None
            rl = S.get("relief") or "both"
            rl = rl if isinstance(rl, str) else rl[k]
            token, cell, rep = make_pair(name, tenon, socket, d, S, host_w, top, g, rl)
            rep["relief"] = rl
            rep["seat"] = d if g is None else g
            REPORT[name]["steps"].append(rep)
            return token, cell
        mark = mark_size(host_w, len(steps))
        S["mark"] = mark["height"]
        t_up = F.UP_X if tenon == "N" else F.UP_Z
        c_up = {"down": F.DOWN_Z, "up": F.UP_Z, "N": F.UP_X}[socket]
        f = F.Finder(name, "%s tenon / %s socket" % (tenon, socket), make, (steps[0], steps[0]),
                     host_w + F.GAP, t_up, c_up, "chassis_0", "chassis_0", deltas=tuple(steps),
                     skin_top=socket == "up",                        # mouths on the bed
                     cell_mark=((F.L / 2.0, 0.0, top), (0, 0, 1), (0, 1, 0), mark),
                     token_mark=((F.L / 2.0, 0.0, -2 * WALL), (0, 0, -1), (0, 1, 0), mark))
        out.append(f)
    return out


def _top_down(grp):
    """The group with step 1 at the TOP of the plate (+Y), 2 and 3 below it, every family
    alike (user: the finder's order varied with each strip's print flip). A family that
    runs the other way has its strip turned 180 degrees about Z round its cells' middle,
    and its tokens' slots swapped end for end."""
    def cy(sh):
        bb = sh.BoundingBox()
        return (bb.ymin + bb.ymax) / 2.0
    toks = sorted([(n, sh) for n, sh in grp if "_token_" in n], key=lambda t: t[0])
    if cy(toks[0][1]) >= cy(toks[-1][1]):
        return grp
    slots = [cy(sh) for _n, sh in toks]
    mid = (slots[0] + slots[-1]) / 2.0          # the cells' middle (the strip's tab is off it)
    swap = {n: slots[len(slots) - 1 - i] for i, (n, _sh) in enumerate(toks)}

    def turn(sh, to=None):
        if to is not None:                      # a token only MOVES (it is symmetric across
            return sh.translate(cq.Vector(0, to - cy(sh), 0))   # the joint): base stays +X
        bb = sh.BoundingBox()
        c = cq.Vector((bb.xmin + bb.xmax) / 2.0, mid, 0.0)
        return sh.rotate(c, c + cq.Vector(0, 0, 1), 180.0)
    return [(n, turn(sh, swap.get(n))) for n, sh in grp]


FOOT_L = 5 * BEAD                 # how far a standing token's foot reaches past its base
FOOT_T = 2 * 0.4                  # two 0.4 layers


def _footed(grp, standing):
    """A nozzle-made token stands 12 tall on its ~3 deep base, and A3 broke free of the bed
    (user): each gets a thin FOOT off the back of its base, full base width -- behind the
    base, where no socket ever goes, so the fit never sees it."""
    out = []
    for n, sh in grp:
        bb = sh.BoundingBox()
        if standing and "_token_" in n:
            back = cq.Solid.makeBox(0.5, bb.ylen, 0.4, cq.Vector(bb.xmax - 0.5, bb.ymin, 0.0))
            assert sh.intersect(back).Volume() > 0.95 * back.Volume(), "%s: base not at +X" % n
            sh = sh.fuse(cq.Solid.makeBox(FOOT_L, bb.ylen, FOOT_T,
                                          cq.Vector(bb.xmax - 0.01, bb.ymin, 0.0))).clean()
        out.append((n, sh))
    return out


def plate(pairs=None, tag=TAG):
    """Every family as it prints, left to right; a family whose options carry "row": k goes
    in row k, row 0 at the top of the plate (+Y) and the rest below it."""
    pairs = pairs or PAIRS
    rows = {}
    for f, pr in zip(finders(pairs), pairs):
        k = pr[4].get("row", 0) if len(pr) > 4 else 0
        grp = _footed(_top_down(R2._group(f, "both", tag)[0]), f.token_up == F.UP_X)
        x0 = min(sh.BoundingBox().xmin for _n, sh in grp)
        y0 = min(sh.BoundingBox().ymin for _n, sh in grp)
        x = rows.setdefault(k, [0.0, []])[0]
        rows[k][1] += [(n, sh.moved(cq.Location(cq.Vector(x - x0, -y0, 0.0)))) for n, sh in grp]
        rows[k][0] = x + max(sh.BoundingBox().xmax for _n, sh in grp) - x0 + R2.BETWEEN
    out, y = [], 0.0
    for k in sorted(rows, reverse=True):                   # the last row at the front
        grp = rows[k][1]
        out += [(n, sh.moved(cq.Location(cq.Vector(0.0, y, 0.0)))) for n, sh in grp]
        y += max(sh.BoundingBox().ymax for _n, sh in grp) + R2.BETWEEN
    return [(n, sh if sh.isValid() else sh.fix()) for n, sh in out]


def assembly(origin=(-560.0, 210.0, 160.0)):
    return [("test_" + n, cq.Workplane("XY").newObject([s]).translate(origin)) for n, s in plate()]


def main(argv=None, pairs=None, tag=TAG, out="test_plate2_petg_gf.step"):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", action="store_true")
    a = ap.parse_args(argv)
    REPORT.clear()
    pl = plate(pairs, tag)
    for name, r in REPORT.items():
        S = r["shape"]
        print("%s: neck %.1f, head %.1f wide x %.2f tall, underside %d deg, top %s | lip %.2f, side wall %.2f,"
              " roof %.2f | numbers %.1f tall"
              % (name, 2 * S["n"], 2 * S["h"], S["tip"], S["flare"],
                 "pointed" if S["chamfer"] else "flat", S["lip"], S["side_wall"], S["roof"], S["mark"]))
        for rep in r["steps"][:len(r["steps"]) // 2 or None]:
            (to, tb), (so, sb) = rep["tenon_overhang"], rep["socket_overhang"]
            bad = ((to or 0) > 45.5 or (so or 0) > 45.5 or max(tb, sb) > ROOF_FLAT_MAX + 1e-6
                   or rep["gap"][1] > max(rep["c"], rep.get("seat", rep["c"])) + 0.01 or rep["corners_off"])
            print("   c %.2f seat %.2f %-6s tenon %.2f/%.2f socket %.2f/%.2f  gap %.3f..%.3f (mouth %.2f)  overhang tenon %s"
                  " socket %s  bridge %.2f%s"
                  % (rep["c"], rep.get("seat", rep["c"]), rep.get("relief", ""), rep["tenon_r"][0], rep["tenon_r"][1], rep["socket_r"][0], rep["socket_r"][1],
                     rep["gap"][0], rep["gap"][1], rep["mouth_air"], "-" if to is None else "%.0f" % to, "-" if so is None else "%.0f" % so,
                     max(tb, sb),
                     "   FAILS A CHECK %s" % (rep["corners_off"] or "") if bad else ""))
    lo = [min(getattr(s.BoundingBox(), k) for _n, s in pl) for k in ("xmin", "ymin")]
    hi = [max(getattr(s.BoundingBox(), k) for _n, s in pl) for k in ("xmax", "ymax", "zmax")]
    print("plate: %d pieces, %.1f cm3, %.1f x %.1f, %.1f tall" % (
        len(pl), sum(s.Volume() for _n, s in pl) / 1000.0, hi[0] - lo[0], hi[1] - lo[1], hi[2]))
    bad = [n for n, s in pl if not s.isValid() or len(s.Solids()) != 1]
    print("every piece one valid solid" if not bad else "NOT ONE VALID SOLID: %s" % ", ".join(bad))
    if a.export:
        from cadkit.step_export import export_step
        path = HERE / out
        export_step(cq.Workplane("XY").newObject([cq.Compound.makeCompound([s for _n, s in pl])]), str(path))
        print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
