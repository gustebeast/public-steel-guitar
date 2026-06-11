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
