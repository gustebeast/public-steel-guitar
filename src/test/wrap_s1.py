"""String 1 coupon: a slice of the finished keyhead, not a model of it. Everything comes off the real
solid, so the wrap space, the insert's travel, the screw's reach and the stow bore cannot drift from it.

It proves two things (user): with the M4 x 40 the insert drops far enough to wrap the string round the
rod, and the screw brings it back up to clamp the coil, lightly. It also proves the tail goes down its
stow bore. It is not a strength test.

The slab keeps 2.4 of wall +Y of string 1's pocket and the one finger -Y of it, whole height and depth.
Below that the bore leans out of the slab, so a wedge of the bed wall follows it down.

    py -3.12 -m src.test.wrap_s1
"""
from __future__ import annotations

import math
import sys

import cadquery as cq

from .. import chassis as CH
from .. import dimensions as D
from .. import keyhead_endplate as K
from .. import nut_block as NB
from ..helpers import box_at
from cadkit.step_export import export_step, print_pose

WALL = 3 * D.BEAD                                # 2.4 +Y of the pocket
BORE_WALL = 3 * D.BEAD                           # round the bore where it leaves the slab


def _pocket_y(i):
    """(lo, hi) of string i's pocket, as cut: both lobes grown by the fit."""
    lobes = NB.insert_lobes(i)
    c = NB._clr(i)
    return min(y - w / 2.0 for y, w in lobes) - c, max(y + w / 2.0 for y, w in lobes) + c


Y0 = NB.insert_lobes(1)[1][0] + NB.insert_lobes(1)[1][1] / 2.0 + NB._clr(1)    # string 2 clamp pocket, +Y
Y1 = _pocket_y(0)[1] + WALL


def _bore_wedge():
    """The bed wall that follows string 1's bore down past the slab's -Y face."""
    z_end = CH.Z_BOT - D.STRING_Z
    y_at = lambda z: NB.stow_y_at(0, z) - NB.STOW_D / 2.0 - BORE_WALL
    z0 = NB.STOW_PIVOT_Z - (NB.stow_y(0) - NB.STOW_D / 2.0 - BORE_WALL - Y0) / math.tan(NB.STOW_TILT)
    x0, x1 = NB.X_BACK, NB.STOW_X + NB.STOW_APEX + BORE_WALL
    w = (cq.Workplane("YZ").polyline([(Y0 + 0.5, z0), (Y0 + 0.5, z_end), (y_at(z_end), z_end)]).close()
         .extrude(x1 - x0).translate((x0, 0.0, 0.0)))
    return w.translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z))


def keep():
    """The slab through the part, and the wedge that follows the bore."""
    bb = K.keyhead_endplate.val().BoundingBox()
    slab = box_at(bb.xlen + 2.0, Y1 - Y0, bb.zlen + 2.0, x=(bb.xmin + bb.xmax) / 2, y=(Y0 + Y1) / 2,
                  z=(bb.zmin + bb.zmax) / 2)
    return slab.union(_bore_wedge())


def block():
    return K.keyhead_endplate.intersect(keep())


def insert():
    return NB.slide_insert(0).translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z))


def main():
    b, ins = block(), insert()
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    export_step(print_pose(b, ((0, 1, 0), -90)), out + "/test_wrap_s1.step")
    export_step(print_pose(ins, ((0, 1, 0), 90)), out + "/test_wrap_s1_insert.step")


if __name__ == "__main__":
    main()
