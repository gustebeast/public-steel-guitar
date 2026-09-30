"""Where can the foot-light board ENTER its channel? It slides in along X, so the
question is what stands in the lane beyond each end of the window."""
import cadquery as cq
from src.build import collect_components

YC, Y0, Y1 = 50.35, 40.0, 55.0
Z0, Z1 = -71.35, -65.5


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    for x0, x1, tag in ((-640.0, -592.46, "-X (keyhead) approach"),
                        (-19.74, 30.0, "+X (bridge) approach"),
                        (-592.46, -19.74, "the lane itself, board-width")):
        box = (cq.Workplane("XY").box(x1 - x0, Y1 - Y0, Z1 - Z0)
               .translate(((x0 + x1) / 2.0, (Y0 + Y1) / 2.0, (Z0 + Z1) / 2.0)).val())
        print("\n%s -- x %.1f..%.1f, y %.1f..%.1f, z %.2f..%.2f:"
              % (tag, x0, x1, Y0, Y1, Z0, Z1))
        hits = []
        for name, shp in comps:
            try:
                inter = shp.intersect(box)
                v = inter.Volume() if inter.Solids() else 0.0
            except Exception:
                v = 0.0
            if v > 0.5:
                hits.append((v, name, inter.BoundingBox()))
        for v, name, bb in sorted(hits, reverse=True)[:14]:
            print("   %-26s %10.1f mm3  x %8.2f..%8.2f y %7.2f..%7.2f z %7.2f..%7.2f"
                  % (name, v, bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
        if not hits:
            print("   (clear)")


if __name__ == "__main__":
    main()
