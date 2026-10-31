"""Lifted rod, the real part's winding: threading, insert fit and tail hold. No load test.

A slice of the real block, strings 7 to 10: rod, top outline, lanes, lane floor, pockets and fit all
read from nut_block, on the real part's -X down. The foot under it is cut short, and so is the insert.

    string 7's lane  the real pocket and the real SKU A insert, printed apart, with the real drop
    the bass bay     the real open rod and the stiffest wire

Fit the insert from the top with the rod out, then the rod. Push it up with a tool through the hole
in the floor. A real Ø4 dowel sits in its cradle.

    py -3.12 -m src.test.wrap_lift [out_dir]
"""
import sys

import cadquery as cq

from .. import dimensions as D
from .. import nut_block as N
from ..helpers import box_at
from cadkit.holes import teardrop_hole
from cadkit.step_export import export_step, print_pose

STRING = 6                                  # string 7: the fattest in an SKU A lane
PANEL_TOP = N.NUT_BASE
PANEL_RUN = 5 * D.BEAD                      # 4.0: enough panel to show the corner
SLAB = 10 * D.BEAD                          # 8.0 under the floor, for the vice
UNDER_FLAT = 20 * D.BEAD                    # 16.0 of the insert under its flat
WALL = 2 * D.BEAD                           # round the pocket, below the slab
CAP = D.MIN_WALL_2P                         # under the pocket
END = 4 * D.BEAD                            # 3.2: the end walls only hold the rod's ends
TOOL_D = 4.4
FLAT = N.insert_flat_z(STRING)
Z_FOOT = FLAT - UNDER_FLAT
Z_POCKET = N._FZ_LOW - UNDER_FLAT           # the real drop, for a .080 less the difference
Z0 = Z_POCKET - CAP
Z_SLAB = PANEL_TOP - SLAB
POCKET_HI = D.nut_y(STRING) + N.INS_LOBE_W / 2 + N._clr(STRING)
POCKET_LO = D.nut_y(STRING) + N.CLAMP_LO - N._clr(STRING)
FINGER_Y = (N.bays()[STRING][1] + 0.5)      # lanes +Y of here are not this coupon's
Y0, Y1 = N._INS_LO - END, POCKET_HI + END
TOP = N.NUT_TOP
X1 = N.X_FRONT + 0.2


def block():
    pts = N.BLOCK_TOP + [(N.X_FRONT, PANEL_TOP), (X1 + PANEL_RUN, PANEL_TOP), (X1 + PANEL_RUN, Z_SLAB),
                         (N.X_BACK, Z_SLAB)]
    body = cq.Workplane("XZ", origin=(0.0, Y1, 0.0)).polyline(pts).close().extrude(Y1 - Y0)
    # the pocket's depth hangs under the slab; to the bed, so it has no -X face to overhang
    x1 = X1 + WALL
    y0, y1 = POCKET_LO - WALL, POCKET_HI + WALL
    body = body.union(box_at(x1 - N.X_BACK, y1 - y0, Z_SLAB + 1.0 - Z0, x=(x1 + N.X_BACK) / 2,
                             y=(y0 + y1) / 2, z=(Z_SLAB + 1.0 + Z0) / 2))
    # the end walls stop past the bore's lid, +X: only the fingers run the whole root
    x2 = N.ROD_X + N.ROD_BORE / 2 + 3 * D.BEAD
    hi = D.nut_y(STRING) + N.CLAMP_HI + N._clr(STRING)      # not a neighbour's taper left as a fin
    for y0, y1 in ((Y0, N._plan(9)[2][1] - N._clr(9)), (hi, Y1)):
        body = body.cut(box_at(x1 + PANEL_RUN - x2, y1 - y0, TOP + 1.0 - PANEL_TOP,
                               x=(x1 + PANEL_RUN + x2) / 2, y=(y0 + y1) / 2,
                               z=(TOP + 1.0 + PANEL_TOP) / 2))
    # the bass's pockets only as far as the floor: nothing rides in them here
    above = box_at(200.0, 200.0, TOP + 1.0 - PANEL_TOP, x=0.0, y=FINGER_Y - 100.0,
                   z=(TOP + 1.0 + PANEL_TOP) / 2)
    for i in range(N.N_FINGERED, D.N_STRINGS):
        body = body.cut(N.insert_pocket(i).intersect(above))
    body = body.cut(N.lanes().intersect(above))
    body = body.cut(N._plan_wire(STRING).offset2D(N._clr(STRING), kind="arc")
                    .extrude(TOP + 1.0 - Z_POCKET).translate((0, 0, Z_POCKET)))
    body = body.cut(teardrop_hole(TOOL_D, CAP + 2.0, (N.ROD_X, D.nut_y(STRING) + N.CLAMP_C, Z0 - 1.0),
                                  (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)))
    return body.cut(teardrop_hole(N.ROD_BORE, (Y1 - D.MIN_WALL_2P - Y0) + 1.0,
                                  axis_point=(N.ROD_X, Y0 - 1.0, N.ROD_Z), axis_dir=(0.0, 1.0, 0.0),
                                  print_up=N.PRINT_UP))


def insert():
    """The real string 7 insert, its foot cut short."""
    return N.slide_insert(STRING).intersect(box_at(60.0, 40.0, 40.0, x=-5.0, y=D.nut_y(STRING),
                                                   z=Z_FOOT + 20.0))


def wire(g, y):
    z = (N.LANE_FLOOR + N.ROD_Z - N.ROD_D / 2) / 2
    return cq.Solid.makeCylinder(g / 2, 60.0, cq.Vector(-45.0, y, z), cq.Vector(1, 0, 0))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    b = block()
    ins = insert()
    v, s = b.val(), ins.val()
    bb, ib = v.BoundingBox(), s.BoundingBox()
    rod = cq.Solid.makeCylinder(N.ROD_D / 2, Y1 - D.MIN_WALL_2P - Y0 + 40.0,
                                cq.Vector(N.ROD_X, Y0 - 40.0, N.ROD_Z), cq.Vector(0, 1, 0))
    print("block %.1f x %.1f x %.1f, %d solid(s), valid %s, %.1f cm3" % (
        bb.xlen, bb.ylen, bb.zlen, len(v.Solids()), v.isValid(), v.Volume() / 1000.0))
    print("insert %.1f x %.1f x %.1f, %d solid(s), valid %s, %.1f cm3" % (
        ib.xlen, ib.ylen, ib.zlen, len(s.Solids()), s.isValid(), s.Volume() / 1000.0))
    low = s.moved(cq.Location(cq.Vector(0.0, 0.0, Z_POCKET - Z_FOOT)))
    print("drop %.2f, top low %.2f, lane floor %.2f, rod under %.2f" % (
        Z_FOOT - Z_POCKET, low.BoundingBox().zmax, N.LANE_FLOOR, N.ROD_Z - N.ROD_D / 2))
    print("insert in block home %.3f low %.3f, rod in block %.3f, rod in insert %.3f" % (
        s.intersect(v).Volume(), low.intersect(v).Volume(), rod.intersect(v).Volume(),
        rod.intersect(s).Volume()))
    z = box_at(60.0, 5.0, 0.2, x=-9.0, y=-14.5, z=PANEL_TOP + 0.5).val()
    print("finger 7|8 at its root, cut plane z %.1f: %.1f mm2" % (PANEL_TOP + 0.5, z.intersect(v).Volume() / 0.2))
    for n, y, gs in ((7, D.nut_y(STRING) - 0.4, (D.STRING_GAUGE[STRING],)),
                     (10, D.nut_y(9) - 0.4, (D.STRING_GAUGE[9], D.STRING_GAUGE_MAX))):
        for g in gs:
            w = wire(g, y)
            print("  string %d %.3f along X: block %.3f rod %.3f insert %.3f, air %.2f each side" % (
                n, g, w.intersect(v).Volume(), w.intersect(rod).Volume(), w.intersect(low).Volume(),
                (N.ROD_Z - N.ROD_D / 2 - N.LANE_FLOOR - g) / 2))
    export_step(print_pose(b, ((0, 1, 0), -90)), out + "/test_wrap_lift.step")
    export_step(print_pose(ins, ((0, 1, 0), 90)), out + "/test_wrap_lift_insert.step")


if __name__ == "__main__":
    main()
