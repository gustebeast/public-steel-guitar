"""Geometric helper functions. Pure — no module-level state."""

from __future__ import annotations

import cadquery as cq

from .dimensions import NEMA17_BOLT_SQ, NEMA17_PILOT_D, M3_CLR_D, BOOL_OVERSHOOT


def cyl(d: float, h: float, z: float = 0.0) -> cq.Workplane:
    """Solid cylinder, diameter d, height h, base at z (axis = +Z). The vertical
    leadscrew axis."""
    return cq.Workplane("XY").workplane(offset=z).circle(d / 2).extrude(h)


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


def pose_dir(rots, v):
    """A DIRECTION carried through the same rotations a pose applies to a SHAPE.

    A part's print orientation is a fact about the part, but tools.check_ceilings wants it
    in WORLD coordinates, and several parts are rotated on their way there -- the vertical
    lever turns -90 about Z, the foot pedal takes three turns. Writing the rotated vector
    out by hand is exactly the transcription that checker's own docstring warns about:
    nothing would compare the two if a pose ever changed. So the pose hands its rotation
    list to this, which folds the SAME rotations over a vector.

    `rots` is [(axis, degrees)] about the origin, in order -- what .rotate() already takes.
    """
    x = cq.Vertex.makeVertex(*v)
    for ax, deg in rots:
        x = x.rotate(cq.Vector(0, 0, 0), cq.Vector(*ax), deg)
    return tuple(round(c, 9) + 0.0 for c in (x.X, x.Y, x.Z))


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


# ── CABLES: octagonal prisms, not cylinders (user, 2026-09-21) ────────────────────
# MOVED TO cadkit.cables (2026-09-22): nothing in it was project-specific, and the lesson it
# encodes -- that a sphere elbow meeting two cylinders is the tangent case OCCT silently
# drops material on -- is one every model here pays for once. Re-exported so the callers in
# this package (wiring, optical_pickup) keep importing it from helpers.
from cadkit.cables import oct_cable, oct_prism as _oct_prism, oct_area  # noqa: F401,E402
