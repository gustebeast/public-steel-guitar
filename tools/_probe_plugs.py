"""What is in the way of the optical board's plugs? Intersect each plug's
insertion corridor with every component in the assembly and report the blockers."""
import cadquery as cq
from src.build import collect_components
import src.optical_pickup as OP

PCB_TOP = OP.PCB_BOT + OP.PCB_T
CLR = 1.0
DEPTH = 30.0


def corridor(x, w, h, ymouth):
    return (cq.Workplane("XY").box(w + 2 * CLR, DEPTH, h + 2 * CLR)
            .translate((x, ymouth - DEPTH / 2, PCB_TOP + h / 2)))


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    print("components: %d" % len(comps))
    for ref, x, ymouth, w, h in (("J2", -29.28583, -119.585, 15.00, 7.00),
                                 ("J1", 9.88083, -121.50, 8.94, 3.16)):
        c = corridor(x, w, h, ymouth).val()
        print("\n%s corridor (%.1f x %.1f, %.0f mm of -Y from y %.2f):" % (ref, w, h, DEPTH, ymouth))
        hits = []
        for name, shp in comps:
            if name == "optical_pcb":
                continue
            try:
                inter = shp.intersect(c)
                v = inter.Volume() if inter.Solids() else 0.0
            except Exception:
                v = 0.0
            if v > 0.5:
                bb = inter.BoundingBox()
                hits.append((v, name, bb))
        for v, name, bb in sorted(hits, reverse=True):
            print("   %-24s %9.1f mm3   y %8.2f..%8.2f  x %7.2f..%7.2f  z %6.2f..%6.2f"
                  % (name, v, bb.ymin, bb.ymax, bb.xmin, bb.xmax, bb.zmin, bb.zmax))
        if not hits:
            print("   (nothing blocks it)")


if __name__ == "__main__":
    main()
