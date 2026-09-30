"""Is the -Y side of the foot-light channel actually clear? The board was widened to
y 38.00 and its wall to 36.10, past what tools/_probe_mouth.py verified (40.00)."""
import cadquery as cq
from src.build import collect_components

X0, X1 = -592.46, -19.74


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    for y0, y1, z0, z1 in ((36.10, 40.00, -71.35, -65.50),
                           (32.00, 36.10, -71.35, -65.50),
                           (36.10, 55.55, -72.85, -71.35)):
        box = (cq.Workplane("XY").box(X1 - X0, y1 - y0, z1 - z0)
               .translate(((X0 + X1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)).val())
        print("\ny %.2f..%.2f, z %.2f..%.2f:" % (y0, y1, z0, z1))
        hits = []
        for name, shp in comps:
            if name.startswith("foot_") or name.startswith("chassis"):
                tag = "CHASSIS" if name.startswith("chassis") else "self"
            else:
                tag = ""
            try:
                inter = shp.intersect(box)
                v = inter.Volume() if inter.Solids() else 0.0
            except Exception:
                v = 0.0
            if v > 0.5:
                hits.append((v, name, tag, inter.BoundingBox()))
        for v, name, tag, bb in sorted(hits, reverse=True)[:10]:
            print("   %-22s %-8s %9.1f mm3  x %8.2f..%8.2f y %6.2f..%6.2f z %7.2f..%7.2f"
                  % (name, tag, v, bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
        if not hits:
            print("   (clear)")


if __name__ == "__main__":
    main()
