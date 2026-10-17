"""PRINT-FITTED STRAIGHT JOINTS -- one shared profile, drawn to what each half prints.

PROVISIONAL (2026-10-17). Every number here was measured on ONE printer setup -- a 0.8 mm
nozzle, 0.4 mm layers, PETG-GF -- by printing coupons and judging them by feel and calipers
(the steel-guitar fit plates 1-8). The user's validation sequence is: (1) minimum-size
joints in every print-orientation pair -- DONE; (2) the real joint sections as short
coupons -- DONE for the steel guitar's sites; (3) full-length coupons -- NOT YET; (4) fold
into cadkit. This module is (4) ahead of (3), so another project can start from the rules
as they stand. Expect the full-length results to move the clearances (by ~0.05) and maybe
add a length-dependent rule. Other materials (PCTG, PLA) and nozzles are UNMEASURED: the
corner minimums and clearances will differ -- print a bracket of coupons before relying on
them, and err loose.

    from cadkit import fitted_joint as FJ
    c = FJ.clearance("N", "N", "long")                    # 0.35 (measured, PETG-GF 0.8)
    tenon, cavity, S = FJ.halves("N", "N", c, length, seat, host_w)

halves() returns both halves in the JOINT FRAME -- X the slide (0..length), Y across, Z the
depth from the mating plane (the tenon host's face) toward the tenon's head. The tenon
carries a host slab 2 * WALL behind that plane (union it into the real host; host_w must fit
inside the host); the cavity is what the socket host loses, from the seat (g) to the
cavity's end. Place both with the same transform.

THE PRINT MODES of a half:
  "N"     NOZZLE-made: the profile lies IN the layers (the half stands on its end, or the
          slide runs along the build). No overhang limit; its corners print round.
  "up"    LAYER-made, head toward the nozzle: the profile cuts across the layers, and every
          face hanging over air must be 45 deg or steeper (the tenon's head underside, the
          socket's roof). A socket printed this way has its MOUTH ON THE BED ("mouth down").
  "down"  LAYER-made socket, mouth toward the nozzle ("mouth up"): its lip undersides are
          the faces that must be 45 or steeper.

WHAT THE COUPONS TAUGHT (each rule is in the code below):
  * CORNERS print round whatever is drawn, and differently per mode: a NOZZLE-made corner
    only prints near its drawing from ~2.0 drawn, convex AND concave (a concave drawn 0.5
    printed ~1.3); a LAYER-made one within ~0.2 from 0.8 (one bead) both ways. So MIN is
    N (2.0, 2.0), L (0.8, 0.8), and corners are DRAWN at those radii: the model matches
    the print.
  * ONE SHARED PROFILE, EVEN CLEARANCE: the tenon IS the profile, the socket its offset by
    c everywhere (no separate depth relief on top -- it only left air). Mating radii are
    MATCHED: tenon convex r faces socket concave r + c, tenon concave r faces socket convex
    r - c, each raised to what its own half can print (matched()). Both solids are then
    CHECKED as built -- corners per half, overhangs per layer-made half, walls, and the gap
    measured on the section (gaps()), never trusted from the radii. Design the profile
    against BOTH halves' rules: a failed socket check reshapes the shared profile.
  * THE SEAT is a face like any other: the socket stands c off the tenon's host (g = c), or
    its mouth corner pinches the tenon's root fillet. A smaller seat (g < c) keeps c only
    over that fillet with a pocket -- never on the print BED (a pocket there hangs the second
    layer over air): a mouth-up socket with a root chamfer runs the chamfer to the bed.
  * A MOUTH-DOWN socket's mouth is a 45 deg CHAMFER, sharp on the bed (a rounded corner
    there starts flat over air). The air it leaves beside a nozzle-made tenon's root is
    irreducible; a layer-made tenon takes a matching ROOT CHAMFER (size "root").
  * LAYER/LAYER pairs print an HOURGLASS along the slide: ~0.1 under in the middle, ~+0.13
    over ~3 mm in from each end (the nozzle slows into the end turn). An END RELIEF (LEAD:
    0.12 a side from the end to 3 mm, gone by 4.5) on the SOCKET only evens it out. The
    relief never moves a face that prints as a LAYER surface (a seat, a flat cavity end, a
    flat top): that steps a layer and leaves an island.
  * LAYER/LAYER minimum size is bigger than the profile alone needs: a head locating on 45
    deg stairs is not repeatable, so it gets STRAIGHT SIDES (size "side") -- head 4.8, sides
    2.4 (mouth up) or 1.6 (standing), neck 2.4. A STANDING socket's roof is a bridge that
    sags ~0.13+, so the tenon's tip is CUT FLAT clear of it (size "trunc", 1.2).
  * FRICTION is partly texture: a nozzle-made half slides ACROSS its layer lines (washboard),
    a layer-made one along them -- so nozzle-made pairs want ~0.05 more c. Read WOBBLE as the
    dimensional signal. Steps under 0.05 are below print repeatability.
  * ERR LOOSE: prints vary, and a joint that prints tight must still install. Take the
    loosest c whose wobble is acceptable, not the snuggest.
  * A SEAM JOINT (two sections pulled together by a nozzle/nozzle joint whose head catches
    on 45 deg flanks) seats c*sqrt(2) apart. Compensate by moving each seam face in by
    opening/4, carrying its half of the joint with it (seam_face_trim) -- measured exact.
  * A standing nozzle-made coupon (tall on a small base) can break off the bed: give it a
    thin foot off the back of its base, where no socket goes.

SIZE: build the smallest joint that prints accurately (size=None) and scale up only for
strength, inside the site's room (size = {"neck", "head", "side": widths/lengths in mm,
"root": True, "trunc": mm}). Accuracy first, then small; strength is not a design goal.
"""
from __future__ import annotations

import math

import cadquery as cq
import numpy as np

NOZZLE = 0.8                 # the setup every number in this module was measured on
BEAD = NOZZLE
LAYER = 0.4
WALL = 2 * BEAD
MIN = {"N": (2.0, 2.0), "L": (0.8, 0.8)}      # (convex, concave) that prints as drawn
ROOF_FLAT_MAX = 5 * BEAD                       # a socket roof may bridge this much

# MEASURED CLEARANCES, per side, by (tenon mode, socket mode): (short joint, long joint).
# Step 1: minimum size, PETG-GF 0.8 (fit plates 2-7). "long" is the pick for a long
# engagement (which firms a slight wobble up), "short" for a short friction-held one.
CLEARANCE = {
    ("N", "down"): (0.25, 0.30),     # nozzle tenon, layer socket MOUTH UP (0.35 freest)
    ("N", "up"): (0.25, 0.30),       # nozzle tenon, layer socket MOUTH DOWN
    ("up", "N"): (0.30, 0.30),       # layer tenon head-up, nozzle socket
    ("N", "N"): (0.30, 0.35),        # nozzle/nozzle (slides across the layer lines)
    ("up", "up"): (0.15, 0.20),      # layer/layer STANDING, at STANDING_SIZE
    ("up", "down"): (0.20, 0.25),    # layer/layer MOUTH UP, at MOUTH_UP_SIZE
}
STANDING_SIZE = {"neck": 3 * BEAD, "head": 6 * BEAD, "side": 2 * BEAD, "root": True,
                 "trunc": 1.2}
MOUTH_UP_SIZE = {"neck": 3 * BEAD, "head": 6 * BEAD, "side": 3 * BEAD}
# Step 2: the steel guitar's real sections (short coupons; full length still to print) --
# (tenon, socket, size, c in use), for a site that resembles one
SITES = {
    "lever_mount": ("up", "up", {"neck": 4 * BEAD, "head": 7 * BEAD, "side": 2 * BEAD,
                                 "root": True, "trunc": 1.2}, 0.275),
    "deck_tongue": ("up", "down", {"neck": 4 * BEAD, "head": 6.4, "side": 3 * BEAD}, 0.25),
    "rail_end": ("N", "down", None, 0.30),      # the seat 0.4 off the host
    "seam": ("N", "N", None, 0.375),            # faces flush (seat 0), seam_face_trim applied
}


def clearance(tenon, socket, length="long"):
    """The measured per-side clearance for a print-mode pair; length "long" or "short"."""
    key = (tenon, socket)
    if key not in CLEARANCE:
        raise KeyError("no measured clearance for tenon %r / socket %r: print a bracket" % key)
    return CLEARANCE[key][1 if length == "long" else 0]


def seam_opening(c):
    """How far a seam joint (nozzle/nozzle, head catching on 45 deg flanks) seats its two
    sections apart at clearance c."""
    return c * math.sqrt(2.0)


def seam_face_trim(c):
    """How far to move EACH seam face in, carrying its half of the joint with it, so the
    seated sections close up (measured exact at c 0.45: opening / 4)."""
    return seam_opening(c) / 4.0


def _box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0)
            .translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)))


def _round(body, axis, r, hosts=True, skip=None):
    """`body` with its profile corners rounded: the edges that run along `axis` (the
    joint's extrusion), bar the block's own two bed corners.

    `r` is one radius for every corner (round 2), or a (CONVEX, CONCAVE) pair (round 3:
    the corner-radius rings showed the two print differently -- a nozzle-made convex
    corner comes out about 2 mm round whatever is drawn under that, a concave one about
    1 mm -- so each kind is drawn at what it will print). A corner is convex where the
    solid fills ONE quadrant round it, concave where it fills three. One edge at a time,
    and a radius the edge has no room for is tried smaller (to 0.4, or to a smaller
    asked radius) before it is
    skipped. hosts=False leaves the host block's own side edges (its +/-Y faces) sharp:
    they are coupon, not joint. `skip(u, v)` True leaves that corner as drawn (a socket
    mouth on the print bed: any fillet there starts flat over air); a number rounds it
    to that radius instead (a corner no mate faces only needs its own printable one).
    Returns
    (body, [(u, v, kind, radius used or None)])."""
    cx, cv = (r, r) if not isinstance(r, tuple) else r
    bb = body.val().BoundingBox()
    lo = {"x": (bb.ymin, bb.zmin), "z": (bb.xmin, bb.ymin)}[axis]
    hi = {"x": (bb.ymax, bb.zmax), "z": (bb.xmax, bb.ymax)}[axis]
    mid = {"x": (bb.xmin + bb.xmax) / 2.0, "z": (bb.zmin + bb.zmax) / 2.0}[axis]

    def uv_of(e):
        c = e.Center()
        return (c.y, c.z) if axis == "x" else (c.x, c.y)

    def pt(u, v):
        return cq.Vector(mid, u, v) if axis == "x" else cq.Vector(u, v, mid)

    spots, own = [], {}
    for e in body.edges("|%s" % axis.upper()).vals():
        uv = uv_of(e)
        if not all(abs(uv[i] - lo[i]) < 1e-6 or abs(uv[i] - hi[i]) < 1e-6 for i in (0, 1)):
            if not hosts and (abs(e.Center().y - bb.ymin) < 1e-6 or abs(e.Center().y - bb.ymax) < 1e-6):
                continue
            got = skip(*uv) if skip else False
            if got is True:
                continue
            if got is not False and got is not None:
                own[uv] = got
            spots.append(uv)
    log = []
    for u, v in spots:
        sel = [e for e in body.edges("|%s" % axis.upper()).vals()
               if abs(uv_of(e)[0] - u) < 1e-6 and abs(uv_of(e)[1] - v) < 1e-6]
        solid = body.val()
        # the share of a small circle round the corner that is solid: a convex corner
        # (90 or 135 degrees inside) holds under half of it, a concave one over half
        ring = [pt(u + 0.05 * math.cos(math.radians(a)), v + 0.05 * math.sin(math.radians(a)))
                for a in range(0, 360, 15)]
        share = sum(solid.isInside(q, 1e-6) for q in ring) / float(len(ring))
        kind = "convex" if share < 0.45 else "concave" if share > 0.55 else None
        want = own.get((u, v), cx if kind == "convex" else cv if kind == "concave" else 0.0)
        used = None
        rr = want
        while sel and rr > 1e-9 and rr >= min(0.4, want) - 1e-9:
            try:
                new = body.newObject(sel).fillet(rr)
                if new.val().isValid() and len(new.val().Solids()) == 1:
                    body, used = new, rr
                    break
            except Exception:
                pass
            rr = round(rr - 0.2, 3)
        log.append((u, v, kind, used))
    return body, log



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


def rings(body, x):
    """The section's outlines at mid-length, (y, z) arrays, each wound so that its
    material lies to the LEFT (outer rings counter-clockwise, holes clockwise)."""
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


def overhang(body, down, L):
    """(steepest overhang, bridge) of the joint's faces printed with `down` (y, z) the
    print's down. Anything flatter than 45 degrees is a BRIDGE -- the roof's flat AND the
    flatter parts of the arcs running into it -- measured by its width across (it must be
    under ROOF_FLAT_MAX); the overhang is the steepest face outside it (45 is the limit).
    The section's own outer box (bed, top, sides) is not joint and is left out."""
    rs = rings(body, L / 2.0)
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


def _lead(body, hw, z0, z1, zlim, stations, L, keep=None):
    """`body` with the END RELIEF `stations` at both joint ends: the air beside its profile
    grown by each station's amount at its distance in, lofted between (the loft from the
    ROUNDED section keeps every corner as drawn). Only z in `zlim` is cut, and with
    `keep` = (y, z) nothing beyond |y| below z -- the SEAT face outside the mouth (plate 5:
    a seat cut 0.12 at the ends left the last layer an island over the middle)."""
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


def make_pair(name, tenon, socket, c, S, host_w, top, L, g=None, relief="both"):
    """(token, cell, report) at clearance c, the socket's seat `g` off the host (default c);
    `relief` says which layer-made halves take S["lead"]: both / tenon / socket / none."""
    g = c if g is None else g
    rt, rs = matched(c, MIN[_kind(tenon)], MIN[_kind(socket)])
    # with a ROOT chamfer the socket's sharp bed edge faces the tenon's ROUND root corner;
    # that one chamfer steps out (quarter-tenths) until it clears by c
    d = 0.0
    while True:
        hw = host_w / 2.0
        token = _box(0, L, -hw, hw, -2 * WALL, 0).union(_prism(profile(S), 0.0, L))
        if S.get("trunc"):               # the tip cut flat clear of a bridged socket roof (user)
            token = token.cut(_box(-1.0, L + 1.0, -hw, hw, S["tip"] - S["trunc"], S["tip"] + 1.0))
        # the SEAT is a face of the joint like any other: the socket stands c off the host, so
        # its mouth corner is the tenon root fillet's true offset (seated flush, that corner
        # rounded against the seat and pinched the gap to 0 for 1.7 up the neck). The cavity is
        # cut c low in the socket's own frame; `seated` puts the socket where it rides
        cell = (_box(0, L, -hw, hw, 0, top)
                .cut(_prism(profile(S, c, -1.0, c + d), -1.0, L + 1.0).translate((0, 0, -g))))
        # a seat closer than c (the user: the seam shows on the instrument's front face) keeps
        # c only over the tenon's root fillet -- a pocket c - g deep, as wide as that fillet
        # runs -- so the mouth corner is still the fillet's true offset, and the rest of the
        # face comes down to g
        n_root = None
        # NO POCKET ON THE BED (user, 2026-10-16: it printed as a true overhang at the bed --
        # a box pocket hung the second layer ~1.3 over air, and no chamfered one can avoid a
        # flat: the fillet's c-offset lies 0.33 outside the root chamfer's 45 line, parallel to
        # it). A mouth-up socket with a root chamfer runs that chamfer's face straight to the
        # bed instead, 45 degrees all the way. Off the tenon's root fillet that leaves c from
        # the fillet's tangent (z ~0.5) up, closing to 0 only ON the bed line, where the seat
        # faces meet flush anyway.
        bed_pocket = g < c - 1e-9 and socket == "up" and S.get("root")
        if g < c - 1e-9 and not bed_pocket:
            n_root = S["n"] + S["root"] + rt[1] + 0.05   # a hair past the fillet (and any root
                                                         # chamfer it runs off): room for the full arc
            cell = cell.cut(_box(-1.0, L + 1.0, -n_root, n_root, -1.0, c - g))
        if S["mouth"]:
            m = S["mouth"]
            cell = cell.cut(_prism([(m + 1.0, -1.0), (0.0, m), (-m - 1.0, -1.0)], -1.0, L + 1.0))
        token, lt = _round(token, "x", rt, False)
        skip = _mouth_corners(S, c, socket)
        if n_root:                       # the pocket's own edge corners face only air: as drawn
            skip0 = skip
            skip = lambda u, v: True if abs(abs(u) - n_root) < 1e-6 else (skip0(u, v) if skip0 else None)
        cell, ls = _round(cell, "x", rs, False, skip=skip)
        if S.get("lead"):
            if tenon != "N" and relief in ("both", "tenon"):
                token = _lead(token, hw, 0.0, S["tip"] + 1.0, (0.0, 1e3), S["lead"], L)
            if socket != "N" and relief in ("both", "socket"):
                # a seat OFF the bed takes the lead-in too (the band under it keeps the offset
                # outline's edges one-for-one); one ON the bed must not be undercut
                # a mouth-up socket's flat cavity end prints as a LAYER face: relieved too, it
                # stepped a layer deeper at the joint's ends (plate 6 B, seen in the slicer by
                # the user) -- the relief stops at it, as at the seat
                cell = _lead(cell, hw, 0.0 if socket == "up" else -0.3, top,
                             (-1.0, top - 1e-3) if socket == "up" else (-1.0, S["tip"] + c - g - 1e-3),
                             S["lead"], L, None if socket == "up" else (S["n"] + c + rs[0] + 0.05, 0.3))
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


def halves(tenon, socket, c, L, g, host_w, size=None, relief="socket", drop=0.0):
    """The fit-tested joint for an INSTRUMENT site (step 2 of the user's sequence, until it
    moves into cadkit): (tenon, cavity, S), both in the joint frame -- X the slide (0..L),
    Y across, Z the depth from the mating plane (the tenon host's face). The tenon carries
    its host slab 2 * WALL back behind that plane (fused into the real host; host_w must fit
    inside it) with the root fillets in it; the cavity is what the socket host loses, from
    `g` (where its material starts: its seat, or an assembly standoff) to the cavity's end --
    and `drop` further back across the mating plane, where a socket host that ends exactly
    there would otherwise be cut coplanar (only where nothing of the tenon's host is behind)."""
    S = dict(shape(tenon, socket, c, size), lead=LEAD)
    S["tip"] = max(z for _y, z in profile(S))
    top = S["tip"] + c + 2 * WALL
    token, cell, rep = make_pair("site", tenon, socket, c, S, host_w, top, L, g=g, relief=relief)
    assert rep["gap"][0] >= min(c, g) - 0.005, "the joint pinches to %.3f" % rep["gap"][0]
    hw = host_w / 2.0
    cavity = _box(0, L, -hw, hw, 0, top).cut(cell).translate((0, 0, g))
    if drop:
        mouth = cavity.val().intersect(_box(-1.0, L + 1.0, -hw, hw, g, g + 0.01).val())
        cavity = cavity.union(cq.Workplane("XY").newObject([mouth]).faces("<Z").wires().toPending()
                              .extrude(-(drop + 0.01)))
    return token, cavity, S
