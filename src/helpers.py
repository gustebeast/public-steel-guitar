"""Geometric helper functions. Pure — no module-level state."""

from __future__ import annotations

import math

import cadquery as cq
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain  # type: ignore[import]

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


def corbel_close(w, crop, z0, z1, step, align=None, keep_frac=0.5, debug=False):
    r"""Cut ONE REGION of a part back to what the 45 deg rule can support, growing the
    support out of EVERY wall around it at once.

    THE RULE, AND WHY ONE PLANE IS NOT ENOUGH. Material prints if it is within 45 deg of
    material below it, transitively -- each layer may step out one layer-height. The cheap
    fix for a roof over a void is to pick one wall and cut a 45 down to it, but that
    throws away everything the OTHER walls could have carried. Here the supported set is
    grown from every wall there is, at once, so the roof survives wherever ANY of them can
    reach it (user, 2026-09-28: "ideally we would use all of them to maximize the amount
    of material above the levers").

    HOW. Layer by layer, inside `crop` only:

        supported(z) = dilate_xy( supported(z - step) U material_outside_crop(z), step )
                       AND material(z)

    THE `crop` IS NOT AN OPTIMISATION, IT IS THE SEED (user, 2026-09-28: "we can focus it
    to just the area we need help with"). Run over a whole part the sweep has to start at
    the print bed, because anywhere else something begins higher up, has no seed, and gets
    cut -- measured on this housing as 5 solids and 17% of the volume gone. Sweeping from
    the bed then timed out past 500 s. Confined to the region that actually has the
    overhang, the material OUTSIDE it is by definition untouched, so it can be handed in
    as support at every layer -- which is both correct and cheap, because the walls that
    re-seed the sweep are exactly the walls the user wants the 45s grown from.

    AND IT DOES NO BOOLEANS ON THE REAL PART. The obvious 3D form -- eight translated
    copies fused per layer -- ran past 600 s on one housing against a 30 s budget for the
    instrument. The work is all in the booleans, so this takes a 0.02 thick SECTION per
    layer (0.3 s for nine), dilates those faces with a 2D offset, and only ever intersects
    thin prisms of faces against each other.

    IT UNDER-CUTS RATHER THAN OVER-CUTS. The dilation is an outward 2D offset, exact for
    straight walls and slightly generous on a convex corner; the intersection against the
    real section clips whatever that generosity invented. `keep_frac` asserts the result
    is not a collapse: a sweep that silently returns almost nothing is the failure mode
    this project has already been bitten by once (see the note on the 16-way growth fuse).
    """
    sol = w.val() if hasattr(w, "val") else w
    crop_s = crop.val() if hasattr(crop, "val") else crop
    big = 400.0
    # THE BAND ENDS AT z1 EXACTLY, and the courses are laid out to land on `align`.
    #
    # Rounding the course count instead left the band 0.11 short of the housing's top
    # face, so the last 0.11 of the roof was never in the sweep: an untouched slab on
    # top of the carved course below it, 104 mm2 bridging 10.13 mm. Filling that in with
    # a leftover course of its own was no better -- a course is allowed to step out by
    # its own height, and a 0.11 mm course carrying a 0.8 mm ledge is an 82 deg overhang
    # with 0.11 mm of material in it, which check_thin duly found.
    #
    # The cure is to put a course boundary ON the face that matters (`align` -- the
    # housing's roof), so the roof's top is a course top and nothing is left over above
    # it. The remainder goes to the BOTTOM course instead, where it is harmless: that
    # one sits on the print bed and steps out nowhere.
    bnds = [z0]
    g = z1 if align is None else align - step * math.ceil((align - z0) / step - 1e-9)
    if align is None:
        while bnds[-1] + step < z1 - 1e-9:
            bnds.append(bnds[-1] + step)
    else:
        while g < z1 - 1e-9:
            if g > z0 + 1e-9:
                bnds.append(g)
            g += step
    bnds.append(z1)
    band = crop_s.intersect(box_at(big, big, z1 - z0, x=0.0, y=0.0,
                                   z=(z0 + z1) / 2.0).val())
    region = sol.intersect(band)            # the only material this may change
    outside = sol.cut(crop_s)               # ...and the walls it grows the 45s out of

    def faces_at(shape, z):
        """The cross-section at `z`, as the bottom faces of a hair-thin slab ABOVE it.

        Above, not centred on it: the region is clipped to the band, so a slab centred on
        z0 is half outside it and the section comes back at the band's own bottom face,
        z0 exactly -- which a `< z` test then discards. The seed layer came out EMPTY and
        the sweep kept 2% of the first layer before anything was wrong with the rule."""
        sl = shape.intersect(box_at(big, big, 0.02, x=0.0, y=0.0, z=z + 0.01).val())
        return [f for f in sl.Faces()
                if abs(f.normalAt().z) > 0.999 and f.Center().z < z + 0.005]

    def prism(fs, z, t):
        """The faces stood up as one solid `t` tall at `z` -- in ONE multi-fuse.

        Fusing them on at a time is quadratic, and it is the whole cost of this: the
        supported set fragments as it grows, and by the top layer a one-at-a-time fuse of
        its pieces took 96 s against 0.1 s at the bottom."""
        prs = [cq.Solid.extrudeLinear(f.translate((0, 0, z - f.Center().z)),
                                      cq.Vector(0, 0, t)) for f in fs]
        return None if not prs else (prs[0] if len(prs) == 1 else prs[0].fuse(*prs[1:]))

    def _top_faces(sh, z):
        """The course's TOP section -- what the next course is allowed to step out from.

        Its BOTTOM section is the obvious thing to carry and it is wrong by one course: a
        slice that reaches z + t may overhang the material at z by t, so the support for
        it is the section at z, which is the top of the course below. Carrying the bottom
        instead shaved the upper half of every step off a 45 deg face that was already
        perfect -- a clean gable came back staircased, 1.1% of the block gone."""
        return [f for f in sh.Faces()
                if abs(f.normalAt().z) > 0.999 and f.Center().z > z - 1e-6]

    def unify(sh):
        """Merge the coplanar faces an intersection leaves behind.

        Same reason as the multi-fuse: each layer is cut out of the one below it, so its
        underside comes back as dozens of coplanar shards, and the NEXT layer offsets and
        stands up every one of them. Merging them back into whole faces keeps the count
        flat instead of compounding."""
        try:
            u = ShapeUpgrade_UnifySameDomain(sh.wrapped, True, True, False)
            u.Build()
            return cq.Shape.cast(u.Shape())
        except Exception:
            return sh

    def _off(wire, d):
        return cq.Workplane(obj=wire).wires().toPending().offset2D(d, kind="intersection").vals()

    def dilate(fs, d):
        """Each face grown by `d` in XY -- OUTER wire out, INNER wires in.

        Offsetting every wire of a face the same way, which is what a plain offset2D on
        the face does, grows the HOLES as well and then rebuilds them as solid faces: a
        Ø6 bore came back as a Ø8 disc of support. That is the wrong direction -- it
        invents support over a hole -- so the outer and inner wires are offset with
        opposite signs, and a hole narrower than 2d simply closes.
        """
        out = []
        for f in fs:
            try:
                inner = []
                for iw in f.innerWires():
                    try:
                        inner += [v for v in _off(iw, -d) if isinstance(v, cq.Wire)]
                    except Exception:
                        pass              # a hole smaller than the step: it closes up
                for ow in _off(f.outerWire(), d):
                    if isinstance(ow, cq.Face):
                        out.append(ow)
                        continue
                    try:
                        out.append(cq.Face.makeFromWires(ow, inner))
                    except Exception:
                        out.append(cq.Face.makeFromWires(ow))
            except Exception:
                out.append(f)             # un-offsettable (a sliver): leave it as it is
        return out

    keep, area_kept, area_all = [], 0.0, 0.0
    t0 = bnds[1] - bnds[0]                # the bottom course stands as it is: it is the
    lay = region.intersect(box_at(big, big, t0, x=0.0, y=0.0, z=z0 + t0 / 2.0).val())
    if lay.Solids():                      #   print bed, or the floor under the region
        keep.append(lay)
    sup = _top_faces(lay, z0 + t0)
    for i in range(1, len(bnds) - 1):
        z, t = bnds[i], bnds[i + 1] - bnds[i]   # a course steps out by its OWN height
        out_f = faces_at(outside, z)
        # THE REAL SLICE, not the section stood up. Extruding the section is what the
        # supported set is made of, but using it for the material too STAIRCASES the
        # part: a 45 deg gable that was already perfect came back as 0.8 mm steps, 1.2%
        # of the block gone for nothing. Intersected against its own slice instead,
        # anything already inside the cone survives untouched and only what is over the
        # line gets cut.
        allowed = region.intersect(box_at(big, big, t, x=0.0, y=0.0, z=z + t / 2.0).val())
        if not allowed.Solids():
            sup = []
            continue
        grown = prism(dilate(sup + out_f, t), z, t)
        lay = allowed if grown is None else unify(allowed.intersect(grown))
        area_kept += lay.Volume(); area_all += allowed.Volume()
        if debug:
            print("   z %7.2f  kept %6.1f of %6.1f mm3  (%3.0f%%)"
                  % (z, lay.Volume(), allowed.Volume(),
                     100 * lay.Volume() / max(allowed.Volume(), 1e-9)), flush=True)
        keep.append(lay)                  # ONE multi-fuse at the end, not N unions:
                                          #   fusing layer onto layer took this housing
                                          #   past 600 s on its own
        sup = _top_faces(lay, z + t)
    assert area_all > 0 and area_kept / area_all >= keep_frac, (
        "the 45 deg closure kept only %.0f%% of the material in %.2f..%.2f -- that is a "
        "collapsed sweep, not a roof" % (100 * area_kept / max(area_all, 1e-9), z0, z1))
    return cq.Workplane("XY").add(sol.cut(band).fuse(*keep))


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
