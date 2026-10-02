"""What the foot channel's cut left of string 1's faceplate wall, and where the strip's
free plungers stand.   py -3.12 -m tools._probe_foot_cut"""
import cadquery as cq
from src import foot_light as F
from src import motor_bank as MB
from src.build import collect_components


def main():
    comps = dict((n, wp.val()) for n, wp in collect_components())
    pins = comps["foot_pogo_pins"]
    for n in ("chassis_0", "chassis_1", "chassis_2"):
        i = comps[n].intersect(pins)
        if i.Solids():
            b = i.BoundingBox()
            print("%s vs plungers %.2f mm3  x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f"
                  % (n, i.Volume(), b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax))
    print("window x %.2f..%.2f  seam %.2f" % (F.window()[0], F.window()[1], F.seam_x()))
    bx0, bx1, by0, by1, bz0, bz1 = MB.body_box(0)
    print("motor 0 body x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f" % (bx0, bx1, by0, by1, bz0, bz1))
    xm = (bx0 + bx1) / 2.0 + 14.0          # off the boss slot's centreline
    ch = comps["chassis_2"]
    floor = F.window()[4]
    print("section through the wall at x %.2f: material in 0.5 x 0.5 cells (y right, z up)" % xm)
    for k in range(30, -1, -1):
        z = floor + 0.25 + k * 0.5
        row = ""
        for j in range(0, 22):
            y = by1 - 1.0 + 0.25 + j * 0.5
            row += "#" if ch.isInside(cq.Vector(xm, y, z)) else "."
        print("  z %7.2f  %s" % (z, row))
    print("            y from %.2f, 0.5 a column; motor face %.2f, slot wall %.2f"
          % (by1 - 1.0, by1, F._slot_y()[0]))


if __name__ == "__main__":
    main()
