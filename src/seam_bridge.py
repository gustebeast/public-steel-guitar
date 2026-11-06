"""SEAM BRIDGE: an optional plate under a chassis seam, holding the two sections together from
below.

WHAT (user, 2026-11-05): "a two lever tenon wide bridge which covers the gap between sections."
The seam joint (chassis._seg_halves) locates the sections in X and Y by shape and nothing in it
is in tension. Under string load the body bows about Y, and the bottom of the seam is the part
that opens. A plate across the bottom, keyed into the floor on BOTH sides, ties it shut.

AN OPTION, NOT A FIXTURE. The knee levers mount in any bay of the floor grid, and a lever
hanging over a seam fills the space this plate needs. So it goes under a seam only when the
levers placed leave that floor free (user: "only used if you choose to not put a lever
between a seam"). The seams do not move for it. Which seams carry one in a layout is
build.SEAM_BRIDGES.

ONE PART FOR EVERY SEAM. Every seam plane runs down the middle of a 3.2 wall of the floor's
lever grid (chassis.SPLIT_X, D.lever_wall_x), so a grid station stands 5.2 either side of it,
and every such station is one mortise run from past the -Y rail to the light window. The plate
carries the knee levers' own mount tenon (knee_lever._lever_joint, grown to a tighter fit: see
below) in those two mortises, and it is NO WIDER THAN THOSE TWO TENONS (user, 2026-11-05): it
ends at their necks' outer faces, the rule a lever housing's flush end keeps
(knee_lever.TEN_X_END), so a lever in the next slot has the clearance two levers have with each
other. The flares overhang the plate there, 45 deg off the neck, up inside the mortise. Out to
the flares' clip at the mortise edge, the plate stood 0.08 off a lever's axle end in the next
slot: too close to go in beside it (user: "not enough clearance"). It slides in from -Y the
way a lever does.

THE MORTISES' LENGTH IN Y (user: "it just needs to extend the full mortise length"): from the
-Y rail's outer face to where the tenons end, c short of the mortises' closed end at the light
window.

THICKNESS: 6 beads (4.8). The plate is in tension across the seam, and its section (160 x 4.8,
about 770 mm2) is not the weak link. The tenons and the 1.6 rib walls they bear on are, and
those are the levers' own, which carry a knee. 4.8 is for stiffness: the plate must not peel at
its free -Y end when the body flexes. It hangs 5.25 under the floor (c + 4.8).

A STEP TIGHTER THAN THE LEVERS: 0.35, not their 0.45 (user, 2026-11-05: "a bit loose which is
good for the levers since they have a lot of tenons but for a support bracket it means it doesn't
do its job well"). 0.35 is the step under 0.45 on the levers' own full-length ladder (fit_plate9:
0.275 too tight, 0.35 right, 0.45 a bit loose). The mortises are the levers' and stay at 0.45, so
the bridge's tenon is the levers' tenon offset out by the difference (GROW) on every face,
its rounded corners included. THEN 0.25 (user, 2026-11-06, the 0.35 printed: "grip a bit better
but they could go one tick tighter", and the tick is the same 0.10 again). Under the 0.275 that
was too tight on ONE lever tenon a fifth this length: the print is the judge, not the ladder.

NO RETAINER. Only the tenons' fit holds it in Y, as it holds the knee levers, whose depth lock
is still undesigned (knee_lever: an M4 does not fit beside a tenon). Every bit of floor over
the plate is mortise or rib wall, so there is nowhere for an insert.
"""
from __future__ import annotations

import functools

import cadquery as cq

from . import chassis as CH
from . import dimensions as D
from . import knee_lever as KL
from .helpers import box_at

T = 6 * D.BEAD                          # 4.8 thick
Z_MATE = KL.HOUS_Z1 + KL.MOUNT_Z        # the levers' mating plane: c under the floor
Z0 = Z_MATE - T                         # the plate's underside (its bed face)
Y0 = CH.Y_LO - CH.T / 2.0               # the -Y rail's outer face
Y1 = D.LIGHT_WIN_Y0 - KL.MORT_CLR       # the tenons' end: c short of the mortises' closed end
PRINT_UP = (0.0, 0.0, 1.0)              # plate on the bed, tenons up: the levers' own print
FIT_CLR = 0.25                          # the bridge's clearance in the levers' mortises
GROW = KL.MORT_CLR - FIT_CLR            # 0.20: what the levers' tenon grows by, every face


def _grown(solid, d):
    """`solid` offset out by d on every face (rounded edges stay round, d larger)."""
    from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffsetShape
    from OCP.BRepOffset import BRepOffset_Skin
    from OCP.GeomAbs import GeomAbs_Arc
    mk = BRepOffsetAPI_MakeOffsetShape()
    mk.PerformByJoin(solid.wrapped, d, 1e-4, BRepOffset_Skin, False, False, GeomAbs_Arc)
    sh = cq.Shape.cast(mk.Shape())
    out = cq.Solid.makeSolid(sh) if isinstance(sh, cq.Shell) else sh
    assert out.isValid() and out.Volume() > solid.Volume() + 0.5 * d * solid.Area(), (
        "growing the tenon by %.2f failed (%.0f -> %.0f mm3)" % (d, solid.Volume(), out.Volume()))
    return out


def stations(i):
    """The two grid stations flanking seam i: (-X one, +X one)."""
    s, g = CH.SPLIT_X[i], list(D.lever_grid_x())
    return max(x for x in g if x < s), min(x for x in g if x > s)


def x_span(i):
    """The plate's X: the outer neck faces of its two tenons, as a lever housing ends at its
    last tenon's neck. The levers' neck, not the grown one: the grow is for the fit inside the
    mortise, and a lever beside the plate is clear of it by the levers' own spacing."""
    a, b = stations(i)
    return a - KL._J_STEM / 2.0, b + KL._J_STEM / 2.0


@functools.lru_cache(maxsize=None)
def _tenon(st, grow=GROW):
    """The levers' mount tenon, grown by `grow` (to FIT_CLR), in the mortise at station st, over the run it
    slides into: from the plate's -Y edge to FIT_CLR short of the run's closed end, clipped to
    that mortise above the mating plane (as the leg adapters' ridges are)."""
    runs = CH.mort_segments(st)
    assert len(runs) == 1 and runs[0][0] < Y0, (
        "the mortise at station %.2f is not one run open past the -Y rail (%s): a seam bridge "
        "slides in from -Y" % (st, runs))
    assert abs(runs[0][1] - KL.MORT_CLR - Y1) < 1e-9, (
        "the mortise at station %.2f ends at y %.2f, not the light window: the plate's +Y end "
        "(Y1) is set from the window" % (st, runs[0][1]))
    y0, y1 = Y0, Y1
    t = KL._lever_joint(y1 - y0).tenon()
    if grow:
        t = cq.Workplane(obj=_grown(t.val(), grow))
    t = (t
         .rotate((0, 0, 0), (0, 0, 1), 90)                      # slide axis X -> Y
         .translate((st, y0, Z_MATE)))
    keep = KL.rib_mortise(st, runs[0][0], runs[0][1]).union(
        box_at(D.LEVER_PITCH, y1 - y0 + 2.0, 20.0, x=st, y=(y0 + y1) / 2.0, z=Z_MATE - 10.0))
    return t.intersect(keep).intersect(                         # no further -Y than the plate
        box_at(D.LEVER_PITCH, y1 - y0 + 2.0, 40.0, x=st, y=y0 + (y1 - y0 + 2.0) / 2.0, z=Z_MATE))


def _undercut(x, out, y0, y1):
    """Everything past the plate edge x (on the side `out`, -1 or +1) under a 45 deg plane
    rising outward from the edge at the mating plane. The tenon's root foot is the mortise's
    width at the mating plane, 2.0 past a neck-wide plate on each side: flat over air. This
    makes its underside a 45 deg overhang off the plate edge. The plane meets the (grown)
    root's chamfer within GROW/2 of the mortise mouth's height (c, 0.45 over the mating plane),
    so what the joint locates on, inside the mortise, is all but untouched. Below the plane is the next slot's lever."""
    d = 4 * D.LEVER_PITCH
    pts = [(x, Z_MATE), (x + out * d, Z_MATE + d), (x + out * d, Z0 - 1.0), (x, Z0 - 1.0)]
    w = cq.Workplane("XZ").polyline(pts).close().extrude(-(y1 - y0))   # XZ extrudes -Y: flip
    return w.translate((0, y0 - w.val().BoundingBox().ymin, 0))


@functools.lru_cache(maxsize=None)
def bridge(i):
    """Seam i's bridge, in its world pose (it prints as it sits: plate down, tenons up)."""
    x0, x1 = x_span(i)
    y1 = Y1 + GROW                      # out to the grown tenons' tip: no ledge past the plate
    b = box_at(x1 - x0, y1 - Y0, T, x=(x0 + x1) / 2.0, y=(Y0 + y1) / 2.0, z=Z0 + T / 2.0)
    for st in stations(i):
        b = b.union(_tenon(st))
    for x, out in ((x0, -1.0), (x1, 1.0)):
        b = b.cut(_undercut(x, out, Y0 - 1.0, y1 + 1.0))
    assert len(b.val().Solids()) == 1, "seam bridge %d is not one solid" % i
    return b


def components(seams):
    """The bridges a layout places: one under each chassis seam index in `seams`."""
    return [(f"seam_bridge_{i}", bridge(i)) for i in seams]
