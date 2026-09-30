"""What stands over the keyhead end of the fret LED board? The power bay (buck,
inductor, harness connector) wants x < the comb's last wall, and that region is
where the Pi cluster lives. Measure it rather than derive it."""
import cadquery as cq
from src.build import collect_components

Z0 = -14.55          # fret_light.BOARD_TOP
HY = 35.2            # fret_light.BOARD_HALF_W


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    print("components: %d" % len(comps))
    for x0, x1, z1 in ((-580.0, -555.6, -4.0), (-555.6, -350.0, -4.0)):
        box = (cq.Workplane("XY").box(x1 - x0, 2 * HY, z1 - Z0)
               .translate(((x0 + x1) / 2.0, 0.0, (Z0 + z1) / 2.0)).val())
        print("\nx %.1f .. %.1f, |y| < %.1f, z %.2f .. %.2f:" % (x0, x1, HY, Z0, z1))
        hits = []
        for name, shp in comps:
            if name.startswith("fret_"):
                continue
            try:
                inter = shp.intersect(box)
                v = inter.Volume() if inter.Solids() else 0.0
            except Exception:
                v = 0.0
            if v > 0.5:
                hits.append((v, name, inter.BoundingBox()))
        for v, name, bb in sorted(hits, reverse=True)[:25]:
            print("   %-26s %9.1f mm3   x %8.2f..%8.2f  y %7.2f..%7.2f  z %7.2f..%7.2f"
                  % (name, v, bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
        if not hits:
            print("   (clear)")


if __name__ == "__main__":
    main()
