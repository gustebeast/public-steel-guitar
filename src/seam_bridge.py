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
carries the knee levers' own mount tenon (knee_lever._lever_joint, the fit-tested 0.45 pair) in
those two mortises, and it is NO WIDER THAN THOSE TWO TENONS (user, 2026-11-05): their root
material's outer faces, measured off the built tenons, centred on the seam. A lever's housing reaches past its own
outermost tenon, so a plate out to the next walls' centres (20.8) could not go in beside one.
It slides in from -Y the way a lever does.

THE MORTISES' LENGTH IN Y (user: "it just needs to extend the full mortise length"): from the
-Y rail's outer face to where the tenons end, c short of the mortises' closed end at the light
window.

THICKNESS: 6 beads (4.8). The plate is in tension across the seam, and its section (160 x 4.8,
about 770 mm2) is not the weak link. The tenons and the 1.6 rib walls they bear on are, and
those are the levers' own, which carry a knee. 4.8 is for stiffness: the plate must not peel at
its free -Y end when the body flexes. It hangs 5.25 under the floor (c + 4.8).

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


def stations(i):
    """The two grid stations flanking seam i: (-X one, +X one)."""
    s, g = CH.SPLIT_X[i], list(D.lever_grid_x())
    return max(x for x in g if x < s), min(x for x in g if x > s)


def x_span(i):
    """The plate's X: exactly the outer faces of its two tenons, measured off the built tenons
    (user: "stops right at the tenon material on either end"), and nothing past them."""
    a, b = stations(i)
    return _tenon(a).val().BoundingBox().xmin, _tenon(b).val().BoundingBox().xmax


@functools.lru_cache(maxsize=None)
def _tenon(st):
    """The levers' mount tenon in the mortise at station st, over the run it slides into:
    from the plate's -Y edge to c short of the run's closed end, clipped to that mortise
    above the mating plane (as the leg adapters' ridges are)."""
    runs = CH.mort_segments(st)
    assert len(runs) == 1 and runs[0][0] < Y0, (
        "the mortise at station %.2f is not one run open past the -Y rail (%s): a seam bridge "
        "slides in from -Y" % (st, runs))
    assert abs(runs[0][1] - KL.MORT_CLR - Y1) < 1e-9, (
        "the mortise at station %.2f ends at y %.2f, not the light window: the plate's +Y end "
        "(Y1) is set from the window" % (st, runs[0][1]))
    y0, y1 = Y0, Y1
    t = (KL._lever_joint(y1 - y0).tenon()
         .rotate((0, 0, 0), (0, 0, 1), 90)                      # slide axis X -> Y
         .translate((st, y0, Z_MATE)))
    keep = KL.rib_mortise(st, runs[0][0], runs[0][1]).union(
        box_at(D.LEVER_PITCH, y1 - y0 + 2.0, 20.0, x=st, y=(y0 + y1) / 2.0, z=Z_MATE - 10.0))
    return t.intersect(keep)


@functools.lru_cache(maxsize=None)
def bridge(i):
    """Seam i's bridge, in its world pose (it prints as it sits: plate down, tenons up)."""
    x0, x1 = x_span(i)
    b = box_at(x1 - x0, Y1 - Y0, T, x=(x0 + x1) / 2.0, y=(Y0 + Y1) / 2.0, z=Z0 + T / 2.0)
    for st in stations(i):
        b = b.union(_tenon(st))
    assert len(b.val().Solids()) == 1, "seam bridge %d is not one solid" % i
    return b


def components(seams):
    """The bridges a layout places: one under each chassis seam index in `seams`."""
    return [(f"seam_bridge_{i}", bridge(i)) for i in seams]
