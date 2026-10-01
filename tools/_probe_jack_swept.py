"""How much room is there around the pickup-height jacks, as a function of driver size?

⚠ THE POINT OF SWEEPING. A single probe diameter answers the wrong question twice over: at
O2.887 (a bare 2.5 mm hex key, the project's standard) every jack reads CLEAR, and at O6.0
(key plus a grip) jack 0 reads blocked by 4.84 mm of bridge_endplate. Both are true, and
neither tells you how much material to remove. The user's report -- "we need a little trim
here to get access to the pickup height screw" -- is about turning the key, not inserting it.

So: sweep the column diameter and report the largest that fits, plus what is in the way and
by how much for the sizes above it. That converts "is it blocked" into "trim X for Y".

    py -3.12 -m tools._probe_jack_swept
"""
import cadquery as cq

from src.build import collect_components
from src import top_plate as TP

DIAS = [2.887, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0]
COL_H = 25.0


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    print("assembly %d solids ; sweeping a %.0f mm column above each head\n" % (len(comps), COL_H))

    for k in range(3):
        nm = "pickup_jack_screw_%d" % k
        scr = dict(comps).get(nm)
        if scr is None:
            continue
        bb = scr.BoundingBox()
        cx, cy = (bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0
        top = bb.zmax
        print("=== %s  axis (%.2f, %.2f)  head top z %.2f ===" % (nm, cx, cy, top))
        for d in DIAS:
            col = (cq.Workplane("XY")
                   .add(cq.Solid.makeCylinder(d / 2.0, COL_H, cq.Vector(cx, cy, top))))
            hits = []
            for name, shp in comps:
                if name.startswith("pickup_jack") or name.startswith("string"):
                    continue
                try:
                    it = shp.intersect(col.val())
                    v = it.Volume() if it.Solids() else 0.0
                except Exception:
                    v = 0.0
                if v > 0.5:
                    b = it.BoundingBox()
                    hits.append((v, name, b.zmin - top, b.xmax - b.xmin, b.ymax - b.ymin))
            if not hits:
                print("    O%-5.3f  CLEAR" % d)
            else:
                tot = sum(h[0] for h in hits)
                who = ", ".join("%s %.1f mm3 (from %.2f up, %.2f x %.2f)"
                                % (n, v, z, dx, dy) for v, n, z, dx, dy in sorted(hits, reverse=True)[:2])
                print("    O%-5.3f  %7.1f mm3   %s" % (d, tot, who))
        print()


if __name__ == "__main__":
    main()
