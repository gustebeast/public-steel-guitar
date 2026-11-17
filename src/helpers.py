"""Geometric helper functions. Pure — no module-level state."""

from __future__ import annotations

import cadquery as cq


def cyl(d: float, h: float, z: float = 0.0) -> cq.Workplane:
    """Solid cylinder, diameter d, height h, base at z (axis = +Z). The vertical
    leadscrew axis."""
    return cq.Workplane("XY").workplane(offset=z).circle(d / 2).extrude(h)


def ball_bearing(od: float, bore: float, w: float) -> cq.Workplane:
    """A shielded (ZZ) deep-groove ball bearing as it looks, axis +Z from z = 0: two
    rings with broken corners and a pressed shield set back between them on each face.
    It is the od x bore x w tube with material taken OFF, so whatever cleared the tube
    clears this. ⚠ The ring thicknesses, the shield's setback and the corner break are
    proportions read off a 688ZZ, not a drawing: for the look only."""
    rb, R = bore / 2.0, od / 2.0
    t = R - rb
    ri, ro = rb + 0.26 * t, R - 0.24 * t          # the shield spans ri..ro
    c, s = min(0.3, 0.08 * t), 0.08 * w           # corner break; shield setback
    pts = [(rb + c, 0.0), (ri, 0.0), (ri, s), (ro, s), (ro, 0.0), (R - c, 0.0), (R, c),
           (R, w - c), (R - c, w), (ro, w), (ro, w - s), (ri, w - s), (ri, w),
           (rb + c, w), (rb, w - c), (rb, c)]
    return cq.Workplane("XZ").polyline(pts).close().revolve(360.0, (0, 0, 0), (0, 1, 0))


def ball_bearing_y(od: float, bore: float, w: float, y0: float, *, x: float = 0.0,
                   z: float = 0.0) -> cq.Workplane:
    """ball_bearing with its axis along +Y, its -Y face at y0, centred on (x, z)."""
    return ball_bearing(od, bore, w).rotate((0, 0, 0), (1, 0, 0), -90).translate((x, y0, z))


def cyl_y(d: float, length: float, y0: float, *, x: float = 0.0,
          z: float = 0.0) -> cq.Workplane:
    """Solid cylinder with axis along +Y (the motor shaft axis), base face at y0,
    centred on (x, z).

    The two OFF-AXIS coordinates are keyword-only on purpose. belt_tensioner kept a
    private near-copy of cyl_x whose 4th parameter was z, not y; folding it onto this
    module was a one-line change that silently moved 22 screw channels off axis,
    because the call passed its z positionally. Nothing passes these positionally
    today, so the guard costs nothing and makes that mistake impossible."""
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        d / 2, length, pnt=cq.Vector(x, y0, z), dir=cq.Vector(0, 1, 0)))


def cyl_x(d: float, length: float, x0: float, *, y: float = 0.0,
          z: float = 0.0) -> cq.Workplane:
    """Solid cylinder with axis along +X (the belt / screw axis), base face at x0,
    centred on (y, z). Off-axis coordinates keyword-only -- see cyl_y."""
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        d / 2, length, pnt=cq.Vector(x0, y, z), dir=cq.Vector(1, 0, 0)))


def box_at(dx: float, dy: float, dz: float,
           x: float = 0.0, y: float = 0.0, z: float = 0.0) -> cq.Workplane:
    """Axis-aligned box of size (dx,dy,dz) CENTRED at (x,y,z)."""
    return (cq.Workplane("XY")
            .box(dx, dy, dz, centered=(True, True, True))
            .translate((x, y, z)))


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
