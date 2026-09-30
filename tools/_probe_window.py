"""What stands over the downward light window? The foot-lighting board fires -Z
through it and slides in along X, so the free run above it is what sizes the board."""
import cadquery as cq
from src.build import collect_components

X0, X1 = -592.46, -19.74
YC, ZTOP = 50.35, -71.35


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    print("components: %d" % len(comps))
    for hy, z1, tag in ((4.0, -50.0, "over the window itself, 8 wide"),
                        (12.0, -50.0, "24 wide, centred on the window"),
                        (20.0, -60.0, "40 wide, 11.35 tall")):
        box = (cq.Workplane("XY").box(X1 - X0, 2 * hy, z1 - ZTOP)
               .translate(((X0 + X1) / 2.0, YC, (ZTOP + z1) / 2.0)).val())
        print("\n%s -- y %.2f..%.2f, z %.2f..%.2f:"
              % (tag, YC - hy, YC + hy, ZTOP, z1))
        hits = []
        for name, shp in comps:
            try:
                inter = shp.intersect(box)
                v = inter.Volume() if inter.Solids() else 0.0
            except Exception:
                v = 0.0
            if v > 0.5:
                hits.append((v, name, inter.BoundingBox()))
        for v, name, bb in sorted(hits, reverse=True)[:18]:
            print("   %-24s %10.1f mm3  x %8.2f..%8.2f y %7.2f..%7.2f z %7.2f..%7.2f"
                  % (name, v, bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
        if not hits:
            print("   (clear)")


if __name__ == "__main__":
    main()
