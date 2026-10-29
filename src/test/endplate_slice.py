"""Fit coupon: one screw station sliced out of the +X (bridge) endplate.

Validates the 688ZZ bearing seat and the guide-rod socket against the real parts: the
user drops in the bearing, the leadscrew with its pulley, the H-nut and the guide rod
(user, 2026-10-29). Cut from the FINISHED bridge_endplate solid (endplate-prism-first:
measure the finished solid), so every seat, lip, teardrop and bore is exactly what the
instrument prints -- nothing is redrawn here.

The slice is string 6 (index 5): a far-row screw at x +12, its rod at x +20, mid-field
so both Y cut faces land half-way across the in-row webs. X runs from just -X of the
bearing seat to the endplate's +X face, which stays the bed: the coupon prints exactly
as the endplate does (bridge_endplate.PRINT_UP, flat on +X, building -X).

  py -3.12 -m src.test.endplate_slice      -> coupons/test_endplate_slice.step (print pose)
"""
from __future__ import annotations

import pathlib

import cadquery as cq

from .. import dimensions as D
from .. import bridge_endplate as BE
from .. import screw_rail as SR
from cadkit.step_export import export_step

STRING_I = 5                                   # string 6
X0 = D.screw_x(STRING_I) - D.SUPPORT_BRG_OD / 2 - 2 * D.MIN_WALL_2P   # 0.8 clear of the seat + web
X1 = D.BRIDGE_BASE_X1 + 1.0                    # past the +X face: the bed stays whole
Y_HALF = D.STRING_PITCH                        # half the in-row pitch: mid-web both sides
Z0 = D.SCREW_BOT_Z - 3.0                       # under the screw's foot: the pulley's ascent
Z1 = BE.GUIDE_ROD_TOP + 2 * D.MIN_WALL_2P      # over the rod's top, in its slab bore

OUT = pathlib.Path(__file__).resolve().parents[2] / "coupons"


# COUPON-ONLY TIES. The changer room runs clean through the whole X, so in the endplate the
# screw rail (below) and the slab (above) meet only at the Y edge ribs, far outside one lane.
# A lane slice is therefore two loose pieces. Two side walls on the slice's Y faces, two
# beads thick, hold them at their true spacing. They stand outside the nut's 10.5 across
# flats (and the rod's line), so nothing that is being fitted touches them.
TIE_T = D.MIN_WALL_2P


def _box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def build() -> cq.Workplane:
    y = D.string_y(STRING_I)
    ep = BE.bridge_endplate
    s = ep.intersect(_box(X0, X1, y - Y_HALF, y + Y_HALF, Z0, Z1))
    xt1 = D.BRIDGE_BASE_X1
    for y0 in (y - Y_HALF, y + Y_HALF - TIE_T):
        s = s.union(_box(X0, xt1, y0, y0 + TIE_T, SR.TOP - 1.0, BE.ROOM_Z1 + 1.0))
    assert Y_HALF - TIE_T > D.NUT_AF / 2 + 0.5, "a tie wall reaches into the nut's lane"
    vals = s.solids().vals()
    assert len(vals) == 1, f"the slice fell apart into {len(vals)} solids"
    assert D.screw_x(STRING_I) - D.SUPPORT_BRG_OD / 2 > X0 and D.guide_rod_x(STRING_I) < X1
    assert SR.BOT - SR.BRG_DROP > Z0 and BE.GUIDE_SOCKET_Z > Z0
    return s


def print_pose(s: cq.Workplane) -> cq.Workplane:
    """bridge_endplate.PRINT_UP is -X; turn it to +Z and sit the bed on z = 0."""
    assert tuple(BE.PRINT_UP) == (-1.0, 0.0, 0.0)
    r = s.rotate((0, 0, 0), (0, 1, 0), 90)     # (-1,0,0) -> (0,0,1)
    bb = r.val().BoundingBox()
    return r.translate((-bb.xmin, -bb.ymin, -bb.zmin))


if __name__ == "__main__":
    s = build()
    bb = s.val().BoundingBox()
    print("slice  x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f  vol %.0f mm3"
          % (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax, s.val().Volume()))
    OUT.mkdir(exist_ok=True)
    f = OUT / "test_endplate_slice.step"
    export_step(print_pose(s), str(f))
    print("wrote", f)
