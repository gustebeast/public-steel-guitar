"""Winding-bay coupon: can a string's tail be pushed round under the rod and back up?

The tail goes down the -X side of the rod, along the insert's floor, and up the narrow +X side.
That floor is the INSERT's, which prints -X up, so where it climbs +X every layer edge is a riser
facing the tail's point: 0.4 * tan(slope) tall. This prints that surface the way the part does,
one bay per floor, on one Ø8 rod, the insert dropped by INS_DROP as it is for winding.

Bays run 1, 2, 3.. from the TOP (+Y) of the plate. All have the fingered strings' neck face (the
tightest gap to the rod), and the 45 deg end ramp and -X pocket wall of today's part.

    py -3.12 -m src.test.wrap_bay [out_dir]
"""
import math
import os
import sys

import cadquery as cq

from .. import nut_block as N
from .. import dimensions as D
from cadkit.holes import teardrop_hole
from cadkit.step_export import export_step, print_pose

G = D.STRING_GAUGE[0]                       # the coil the floor must clear at home
R = N.ROD_D / 2 + G
BAY_W, WALL = 10 * D.BEAD, 2 * D.BEAD       # one bay, and the wall between two
RISE = N.RAMP_NECK                          # how far every +X floor climbs before the neck face
TOP_Z = N.ROD_Z                             # the block stops at the rod's centre: the bays are open
FLAT = N.ROD_Z - R - N.INS_DROP             # the floor, dropped
BASE = 4 * D.BEAD                           # floor under the lowest point
BACK = 4 * D.BEAD                           # X of block behind each wall
NECK_X = N._neck_x0(0)
WALL_X = N.STOW_POCKET_X0


def ramp(deg):
    """(x where it leaves the floor, x at the neck face): a straight ramp at `deg`, tangent to the
    coil at home, so the wrap can still be clamped."""
    a = math.radians(deg)
    xt, zt = N.ROD_X + R * math.sin(a), R * (1 - math.cos(a))        # on the coil, above the flat
    x0 = xt - zt / math.tan(a)
    return x0, x0 + RISE / math.tan(a)


# (label, what it is, section builder input). control = today's 45 deg RAMP_NECK at today's face.
VARIANTS = [("45 deg, today", "line", (NECK_X - RISE, NECK_X)),
            ("30 deg", "line", ramp(30.0)),
            ("20 deg", "line", ramp(20.0)),
            ("15 deg", "line", ramp(15.0)),
            ("round r3.2", "arc", (NECK_X - 3.2, NECK_X))]
BED_X = max(v[2][1] for v in VARIANTS) + BACK


def void(kind, x0, x1, y0, w):
    """A bay's air, XZ section, extruded y0..y0 + w."""
    left = FLAT + N.RAMP_END
    s = (cq.Workplane("XZ").moveTo(WALL_X, TOP_Z + 1.0).lineTo(WALL_X, left)
         .lineTo(WALL_X + N.RAMP_END, FLAT).lineTo(x0, FLAT))
    if kind == "line":
        s = s.lineTo(x1, FLAT + RISE)
    else:
        r = x1 - x0
        c = math.radians(45.0)
        s = s.threePointArc((x0 + r * math.sin(c), FLAT + r * (1 - math.cos(c))), (x1, FLAT + r))
    return (s.lineTo(x1, TOP_Z + 1.0).close().extrude(w).translate((0.0, y0 + w, 0.0)))


def block():
    n = len(VARIANTS)
    span = n * BAY_W + (n + 1) * WALL
    x0, z0 = WALL_X - BACK, FLAT - BASE
    body = (cq.Workplane("XY").box(BED_X - x0, span, TOP_Z - z0, centered=False)
            .translate((x0, 0.0, z0)))
    for k, (label, kind, (a, b)) in enumerate(VARIANTS):
        y0 = span - (k + 1) * (BAY_W + WALL)
        body = body.cut(void(kind, a, b, y0, BAY_W))
        # the number, sunk in the bed-side top of the block beside its bay
        mark = (cq.Workplane("XY").workplane(offset=TOP_Z - 0.4)
                .center(BED_X - BACK / 2.0, y0 + BAY_W / 2.0).text(str(k + 1), 5.0, 1.0))
        body = body.cut(mark)
    body = body.cut(teardrop_hole(N.ROD_BORE, span + 2.0, (N.ROD_X, -1.0, N.ROD_Z),
                                  (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0)))
    return body


def side_token():
    """Today's section in one bay, printed Y UP: the tail's path then lies IN the layers, on one
    perimeter, with no risers at all. Whether that is the fix is a question for the real insert's
    print direction, not its shape."""
    w = 2 * WALL + BAY_W
    x0, z0 = WALL_X - BACK, FLAT - BASE
    body = (cq.Workplane("XY").box(NECK_X + BACK - x0, w, TOP_Z - z0, centered=False)
            .translate((x0, 0.0, z0)))
    body = body.cut(void("line", NECK_X - RISE, NECK_X, WALL, BAY_W))
    # rod hole's roof toward the build
    return body.cut(cq.Workplane("XZ").center(N.ROD_X, N.ROD_Z).circle(N.ROD_BORE / 2)
                    .extrude(WALL).translate((0.0, WALL, 0.0)))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "..")
    print("floor %.2f, neck %.2f, rod %.2f..%.2f, bed x %.2f" % (FLAT, NECK_X, N.ROD_X - 4,
                                                                  N.ROD_X + 4, BED_X))
    for k, (label, kind, (a, b)) in enumerate(VARIANTS):
        print("bay %d %-14s floor leaves at x %.2f, neck face %.2f, X cost %.2f, gap to rod %.2f" %
              (k + 1, label, a, b, b - NECK_X, b - (N.ROD_X + 4)))
    bay = print_pose(block(), ((0, 1, 0), 90))
    tok = print_pose(side_token(), ((1, 0, 0), 90))
    bb = bay.val().BoundingBox()
    tok = tok.translate((0.0, bb.ylen / 2.0 + 16.0, 0.0))
    print("bay part %.1f x %.1f x %.1f; solids %d; valid %s" % (
        bb.xlen, bb.ylen, bb.zlen, len(bay.val().Solids()), bay.val().isValid()))
    p = os.path.join(out, "test_wrap_bay.step")
    export_step(cq.Workplane("XY").newObject(
        [cq.Compound.makeCompound([bay.val(), tok.val()])]), p)
    print("wrote", p)


if __name__ == "__main__":
    main()
