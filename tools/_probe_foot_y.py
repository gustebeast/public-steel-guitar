"""How far -Y can the foot strip's channel grow, and how deep can its relief go?

    py -3.12 -m tools._probe_foot_y

Slabs 2 mm wide in Y, the window's whole run plus the -X approach, intersected with every
part: one set at channel height (floor .. lip top + what a raise would add) and one below
the floor (the relief groove, against the CHASSIS -- a full slab means solid floor).
"""
import cadquery as cq
from src import foot_light as F
from src.build import collect_components


YS = range(46, 56, 2)


def main():
    comps = [(n, wp.val()) for n, wp in collect_components() if not n.startswith("foot_")]
    x0, x1 = F.window()[0], F.window()[1]
    floor = F.window()[4]
    for tag, xa, xb, z0, z1 in (("channel band, run", x0, x1, floor + 0.05, -62.0),
                                ("channel band, -X approach", x0 - 45.0, x0, floor + 0.05, -62.0),
                                ("relief band, run", x0, x1, floor - 2.6, floor - 0.05)):
        print("\n%s  x %.1f..%.1f  z %.2f..%.2f" % (tag, xa, xb, z0, z1))
        for y in YS:
            box = (cq.Workplane("XY").box(xb - xa, 2.0, z1 - z0)
                   .translate(((xa + xb) / 2.0, y + 1.0, (z0 + z1) / 2.0)).val())
            hits = []
            for name, shp in comps:
                try:
                    i = shp.intersect(box)
                    v = i.Volume() if i.Solids() else 0.0
                except Exception:
                    v = -1.0
                if v > 0.5 or v < 0:
                    bb = i.BoundingBox() if v > 0 else None
                    hits.append("%s %.0f%s" % (name, v, " z%.2f..%.2f" % (bb.zmin, bb.zmax) if bb else ""))
            print("  y %2d..%2d  full %.0f | %s" % (y, y + 2, box.Volume(), "; ".join(hits[:7]) or "clear"))


if __name__ == "__main__":
    main()
