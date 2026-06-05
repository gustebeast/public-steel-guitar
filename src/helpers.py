"""Geometric helper functions. Pure — no module-level state."""

from __future__ import annotations

import cadquery as cq

from .dimensions import NEMA17_BOLT_SQ, NEMA17_PILOT_D, M3_CLR_D, BOOL_OVERSHOOT


def cyl(d: float, h: float, z: float = 0.0) -> cq.Workplane:
    """Solid cylinder, diameter d, height h, base at z (axis = +Z)."""
    return cq.Workplane("XY").workplane(offset=z).circle(d / 2).extrude(h)


def cyl_x(d: float, length: float, x0: float, y: float = 0.0, z: float = 0.0) -> cq.Workplane:
    """Solid cylinder with axis along +X (the screw/string axis), length
    `length`, base face at x0, centred on (y, z)."""
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        d / 2, length,
        pnt=cq.Vector(x0, y, z),
        dir=cq.Vector(1, 0, 0),
    ))


def box_at(dx: float, dy: float, dz: float,
           x: float = 0.0, y: float = 0.0, z: float = 0.0) -> cq.Workplane:
    """Axis-aligned box of size (dx,dy,dz) CENTRED at (x,y,z)."""
    return (cq.Workplane("XY")
            .box(dx, dy, dz, centered=(True, True, True))
            .translate((x, y, z)))


def nema17_face_cutter(x_face: float, depth: float, *,
                       y: float = 0.0, z: float = 0.0,
                       pilot_d: float = NEMA17_PILOT_D,
                       bolt_d: float = M3_CLR_D,
                       slot: float = 0.0) -> cq.Workplane:
    """Cutter for a NEMA17 motor mounting face lying in a Y–Z plane (motor shaft
    along X). Removes a centre pilot bore + 4 corner bolt holes, all bored along
    −X from x_face inward by `depth`, centred on (y, z).

    `slot` (mm) elongates each bolt hole along Z for belt tensioning; 0 = plain
    round holes."""
    half = NEMA17_BOLT_SQ / 2.0
    out = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        pilot_d / 2, depth + BOOL_OVERSHOOT,
        pnt=cq.Vector(x_face + BOOL_OVERSHOOT, y, z),
        dir=cq.Vector(-1, 0, 0)))
    for sy in (-half, half):
        for sz in (-half, half):
            hole = cq.Workplane("XY").add(cq.Solid.makeCylinder(
                bolt_d / 2, depth + BOOL_OVERSHOOT,
                pnt=cq.Vector(x_face + BOOL_OVERSHOOT, y + sy, z + sz),
                dir=cq.Vector(-1, 0, 0)))
            if slot > 0:
                slotbox = box_at(depth + BOOL_OVERSHOOT, bolt_d, slot,
                                 x=x_face + BOOL_OVERSHOOT - (depth + BOOL_OVERSHOOT) / 2,
                                 y=y + sy, z=z + sz)
                hole = hole.union(slotbox)
            out = out.union(hole)
    return out


def heal(wp: cq.Workplane) -> cq.Workplane:
    """ShapeFix + UnifySameDomain to clean minor tolerance issues and merge
    coplanar faces before STEP export, so strict importers (Onshape) accept the
    result."""
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
