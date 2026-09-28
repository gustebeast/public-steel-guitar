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


def corbel_close(w, step, z0, z1, zb, keep_frac=0.5):
    r"""Cut a part back to what the 45 deg rule can actually support, growing the
    support out of EVERY wall at once.

    THE RULE, AND WHY ONE PLANE IS NOT ENOUGH. Material prints if it is within 45 deg of
    material below it, transitively -- each layer may step in one layer-height. The cheap
    fix for a roof over a void is to pick one wall and cut a 45 down to it, but that
    throws away everything the OTHER walls could have carried. Here the supported set is
    grown from every wall there is, simultaneously, so the roof survives wherever ANY of
    them can reach it (user, 2026-09-28: "ideally we would use all of them to maximize the
    amount of material above the levers").

    HOW, AND WHY IT IS CHEAP. Layer by layer:

        supported(z) = dilate_xy(supported(z - step), step)  AND  material(z)

    which is the textbook closure. Done as 3D solids it is unusable -- the obvious form,
    eight translated copies fused per layer, ran past 600 s on ONE housing against a 30 s
    budget for the whole instrument. The work is all in the booleans, so this does none of
    them on the real part: it takes a 0.02 thick SECTION per layer (0.3 s for nine),
    dilates the faces with a 2D offset, and only ever intersects thin prisms of those
    faces against each other. 4.6 s for a knee-lever housing.

    IT UNDER-CUTS RATHER THAN OVER-CUTS. The dilation is an outward 2D offset, which is
    exact for the straight walls here and slightly generous on a convex corner; the
    intersection against the real section then clips whatever that generosity invented.
    Material that is supported only by something appearing ABOVE z0 is not seen, so it
    gets cut -- conservative in the right direction. `keep_frac` asserts the result is not
    a collapse: a sweep that silently returns almost nothing is the failure mode this
    project has already been bitten by once (see the note on the 16-way growth fuse).
    """
    sol = w.val() if hasattr(w, "val") else w
    big = 400.0

    def faces_at(z):
        sl = sol.intersect(box_at(big, big, 0.02, x=0.0, y=0.0, z=z).val())
        return [f for f in sl.Faces() if abs(f.normalAt().z) > 0.999 and f.Center().z < z]

    def prism(fs, z, t):
        out = None
        for f in fs:
            pr = cq.Solid.extrudeLinear(f.translate((0, 0, z - f.Center().z)),
                                        cq.Vector(0, 0, t))
            out = pr if out is None else out.fuse(pr)
        return out

    def dilate(fs, d):
        out = []
        for f in fs:
            try:
                wires = cq.Workplane(obj=f).wires().toPending().offset2D(d, kind="intersection")
                out += [v if isinstance(v, cq.Face) else cq.Face.makeFromWires(v)
                        for v in wires.vals()]
            except Exception:
                out.append(f)             # un-offsettable (a sliver): leave it as it is
        return out

    # COARSE BELOW THE PROBLEM BAND, FINE INSIDE IT. Seeding the sweep at the band's
    # bottom is wrong: any wall that only starts higher up has no seed, gets cut, and the
    # part comes apart -- measured, 5 solids and 17% of the volume gone. So the sweep has
    # to start at the BED, where "supported" needs no assumption. That is 24 fine layers
    # and it timed out; at 4 mm below the band and `step` inside it, it is 15. The coarse
    # layers still dilate one layer-height per layer, so they are still 45 on average --
    # and there is nothing to correct down there anyway.
    coarse = 4.0
    zs = []
    z = zb
    while z < z0 - 1e-9:
        zs.append(z)
        z += coarse
    zs += [z0 + i * step for i in range(int((z1 - z0) / step) + 1)]
    sup = faces_at(zs[0])
    keep = []
    area_kept = area_all = 0.0
    for i in range(1, len(zs)):
        allowed = prism(faces_at(zs[i]), zs[i], step)
        if allowed is None:
            sup = []
            continue
        grown = prism(dilate(sup, step), zs[i], step)
        lay = allowed if grown is None else allowed.intersect(grown)
        area_kept += lay.Volume(); area_all += allowed.Volume()
        keep.append(lay)                  # ONE multi-fuse at the end, not N unions:
                                          #   fusing layer onto layer took the LKL
                                          #   housing past 600 s on its own
        sup = [f for f in lay.Faces()
               if abs(f.normalAt().z) > 0.999 and f.Center().z < zs[i] + step / 2]
    assert area_all > 0 and area_kept / area_all >= keep_frac, (
        "the 45 deg closure kept only %.0f%% of the material in %.2f..%.2f -- that is a "
        "collapsed sweep, not a roof" % (100 * area_kept / max(area_all, 1e-9), z0, z1))
    below = sol.intersect(box_at(big, big, 1000.0, x=0.0, y=0.0, z=zb - 500.0).val())
    return cq.Workplane("XY").add(below.fuse(*keep))


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
