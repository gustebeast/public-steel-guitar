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
    tensioning (0 = round)."""
    half = NEMA17_BOLT_SQ / 2.0
    out = cyl_y(pilot_d, depth + BOOL_OVERSHOOT, y0=y_face - BOOL_OVERSHOOT, x=x, z=z)
    for sx in (-half, half):
        for sz in (-half, half):
            # stadium slot: a bolt-round hole at each end of the ±slot/2 travel,
            # bridged by a box. (A single centred box used to SWALLOW the round
            # hole entirely, leaving bare rectangles in the faceplate.)
            hole = cyl_y(bolt_d, depth + BOOL_OVERSHOOT,
                         y0=y_face - BOOL_OVERSHOOT, x=x + sx, z=z + sz)
            if slot > 0:
                for ex in (-slot / 2, slot / 2):
                    hole = hole.union(cyl_y(bolt_d, depth + BOOL_OVERSHOOT,
                                            y0=y_face - BOOL_OVERSHOOT,
                                            x=x + sx + ex, z=z + sz))
                hole = hole.union(box_at(slot, depth + BOOL_OVERSHOOT, bolt_d,
                                         x=x + sx,
                                         y=y_face - BOOL_OVERSHOOT + (depth + BOOL_OVERSHOOT) / 2,
                                         z=z + sz))
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
