"""Geometric helper functions. Pure — no module-level state."""

from __future__ import annotations

import cadquery as cq

from .dimensions import NEMA17_BOLT_SQ, NEMA17_PILOT_D, M3_CLR_D, BOOL_OVERSHOOT


def cyl(d: float, h: float, z: float = 0.0) -> cq.Workplane:
    """Solid cylinder, diameter d, height h, base at z (axis = +Z). The vertical
    leadscrew axis."""
    return cq.Workplane("XY").workplane(offset=z).circle(d / 2).extrude(h)


def cyl_y(d: float, length: float, y0: float, x: float = 0.0, z: float = 0.0) -> cq.Workplane:
    """Solid cylinder with axis along +Y (the motor shaft axis), base face at y0,
    centred on (x, z)."""
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        d / 2, length, pnt=cq.Vector(x, y0, z), dir=cq.Vector(0, 1, 0)))


def cyl_x(d: float, length: float, x0: float, y: float = 0.0, z: float = 0.0) -> cq.Workplane:
    """Solid cylinder with axis along +X (the belt / screw axis), base face at x0,
    centred on (y, z)."""
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        d / 2, length, pnt=cq.Vector(x0, y, z), dir=cq.Vector(1, 0, 0)))


def box_at(dx: float, dy: float, dz: float,
           x: float = 0.0, y: float = 0.0, z: float = 0.0) -> cq.Workplane:
    """Axis-aligned box of size (dx,dy,dz) CENTRED at (x,y,z)."""
    return (cq.Workplane("XY")
            .box(dx, dy, dz, centered=(True, True, True))
            .translate((x, y, z)))


def nema17_face_cutter_y(y_face: float, depth: float, *,
                         x: float = 0.0, z: float = 0.0,
                         pilot_d: float = NEMA17_PILOT_D,
                         bolt_d: float = M3_CLR_D,
                         slot: float = 0.0) -> cq.Workplane:
    """Cutter for a NEMA17 mounting face in an X–Z plane (motor shaft along Y).
    Centre pilot bore + 4 corner bolt holes, bored along +Y from y_face inward by
    `depth`, centred on (x, z). `slot` elongates each bolt hole along X for belt
    tensioning (0 = round).

    SELF-SUPPORTING tops (the walls print standing, hole axes horizontal): the
    bolt slots keep their stadium bottom but their top is a 45°-shouldered flat
    (the slot-wide flat is a short bridge — printable; the arc crowns are not);
    the big pilot bore gets a teardrop roof (45° lines from the arc's ±45°
    tangent points), tall enough that the full Ø still passes the motor boss."""

    def _prism(pts, y0, length):
        """Extrude an XZ-plane polygon (local (x,z) points) from y0, +Y by length."""
        wp = cq.Workplane("XZ").polyline(pts).close().extrude(-length)
        return wp.translate((0, y0, 0))

    half = NEMA17_BOLT_SQ / 2.0
    y0 = y_face - BOOL_OVERSHOOT
    dep = depth + BOOL_OVERSHOOT

    # pilot: full bore + teardrop roof (arc is ≤45° overhang up to ±45°, then 45° lines)
    out = cyl_y(pilot_d, dep, y0=y0, x=x, z=z)
    rp = pilot_d / 2.0
    t = rp * 0.7071
    out = out.union(_prism([(x - t, z + t), (x + t, z + t), (x, z + rp * 1.4142)],
                           y0, dep))

    rb = bolt_d / 2.0
    for sx in (-half, half):
        for sz in (-half, half):
            cx, cz = x + sx, z + sz
            # stadium bottom: a bolt-round hole at each end of the ±slot/2 travel
            hole = cyl_y(bolt_d, dep, y0=y0, x=cx, z=cz)
            if slot > 0:
                L = slot / 2.0
                for ex in (-L, L):
                    hole = hole.union(cyl_y(bolt_d, dep, y0=y0, x=cx + ex, z=cz))
                hole = hole.union(box_at(slot, dep, bolt_d,
                                         x=cx, y=y0 + dep / 2, z=cz))
                # strip everything above the equator (the arc crowns exceed 45°)…
                hole = hole.cut(box_at(2 * (L + rb) + 2, dep + 2, rb + 2,
                                       x=cx, y=y0 - 1 + (dep + 2) / 2,
                                       z=cz + (rb + 2) / 2))
                # …then roof it with 45° shoulders up to a bridgeable slot-wide flat
                hole = hole.union(_prism([(cx - L - rb, cz), (cx + L + rb, cz),
                                          (cx + L, cz + rb), (cx - L, cz + rb)],
                                         y0, dep))
            out = out.union(hole)
    return out


def heal(wp: cq.Workplane) -> cq.Workplane:
    """ShapeFix + UnifySameDomain to clean minor tolerance issues and merge
    coplanar faces before STEP export, so strict STEP importers accept it."""
    from OCP.ShapeFix import ShapeFix_Shape          # type: ignore[import]
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain  # type: ignore[import]
    from OCP.TopAbs import TopAbs_COMPOUND
    shape = wp.val().wrapped
    fixer = ShapeFix_Shape(shape)
    fixer.SetPrecision(1e-4)
    fixer.SetMaxTolerance(1e-3)
    fixer.Perform()
    fixed = fixer.Shape()
    try:
        unifier = ShapeUpgrade_UnifySameDomain(fixed, True, True, True)
        unifier.Build()
        unified = unifier.Shape()
    except Exception:
        unified = fixed
    if unified.ShapeType() == TopAbs_COMPOUND:
        wrapped = cq.Compound(unified)
    else:
        wrapped = cq.Solid(unified)
    return cq.Workplane("XY").add(wrapped)


# ── CABLES: octagonal prisms, not cylinders (user, 2026-09-21) ─────────────────────────
# A round cable made of cylinders with sphere elbows is the slowest and least reliable thing
# in the model to fuse and to check. Measured on the J7 24 V head (36 points, one loop):
# its cylinders alone fused whole, but with the elbow spheres every tolerance came back
# 0.19-0.31 of the cable or in loose pieces -- a sphere meeting two cylinders along a shared
# circle is the tangent case OCCT handles worst -- and every boolean the overlap gate runs
# against a curved face costs more than one against planes.
#
# So a cable is an OCTAGONAL prism per segment, ACROSS-FLATS = the cable's diameter: the real
# round cable always fits inside it, so any error lands on the side of clearance (the corners
# stand 8 % proud). Bends have no elbow solid at all: each segment runs on past an interior
# corner by half its width, and the overlapping ends fill the outside of the bend with flat
# faces. Nothing in the fuse is tangent to anything.
import math as _math

_OCT_R = 1.0 / _math.cos(_math.pi / 8)          # circumradius per unit half-across-flats


def _oct_prism(s0, u, length, d):
    """One octagonal prism from point s0 along unit vector u, across-flats d."""
    ref = cq.Vector(0, 0, 1) if abs(u.z) < 0.9 else cq.Vector(1, 0, 0)
    x = ref.cross(u).normalized()
    plane = cq.Plane(origin=s0, xDir=x, normal=u)
    # rotate 22.5 deg so a FLAT (not a corner) faces each principal direction: stacked lanes
    # then sit flat against each other and against the floor of a trough
    return (cq.Workplane(plane).transformed(rotate=(0, 0, 22.5))
            .polygon(8, 2 * (d / 2) * _OCT_R).extrude(length).val())


def oct_cable(pts, d: float) -> cq.Workplane:
    """A cable through `pts` (a polyline of (x, y, z)), octagonal section, across-flats d.

    The ends at the first and last point stay where they are (they are connector
    contacts); every interior corner is filled by running the segments past it. The fuse is
    checked BY VOLUME against the section times the path length: a failed fuse here does not
    raise, it returns one clean solid with cable missing out of the middle (645 of 1776 mm3,
    once), and only the volume says so."""
    segs = []
    for a, b in zip(pts, pts[1:]):
        va, vb = cq.Vector(*a), cq.Vector(*b)
        if (vb - va).Length > 1e-6:
            segs.append((va, vb))
    if not segs:
        return cq.Workplane("XY")
    r = d / 2.0
    parts = []
    for i, (va, vb) in enumerate(segs):
        u = (vb - va).normalized()
        s0 = va - u * r if i > 0 else va
        s1 = vb + u * r if i < len(segs) - 1 else vb
        parts.append(_oct_prism(s0, u, (s1 - s0).Length, d))
    if len(parts) == 1:
        return cq.Workplane("XY").add(parts[0])
    area = 2.0 * d * d * (_math.sqrt(2.0) - 1.0)          # regular octagon, across-flats d
    want = area * sum((vb - va).Length for va, vb in segs)
    for tol in (None, 1e-5, 1e-4):
        try:
            fused = parts[0].fuse(*parts[1:], tol=tol) if tol else parts[0].fuse(*parts[1:])
        except Exception:
            continue
        if fused.Solids() and fused.Volume() >= 0.9 * want:
            return cq.Workplane("XY").add(fused.clean())
    raise RuntimeError("oct_cable: no fuse tolerance returned a whole cable "
                       "(%d segments, wanted >= %.1f mm3)" % (len(segs), want))
