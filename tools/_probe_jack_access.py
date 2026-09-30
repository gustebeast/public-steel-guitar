"""Can a 2.5 mm hex key reach each PICKUP HEIGHT JACK? (user: "we need a little trim
here to get access to the pickup height screw")

The jacks are M4 buttons driven from +Z -- heads captured in the solid deck, the
counterbore opening at the deck top -- so access is a clear column straight up from the
head. Anything standing in that column has to be trimmed, and this says WHAT and HOW MUCH.

Run:  py -3.12 -m tools._probe_jack_access
"""
import cadquery as cq

from src.build import collect_components
from src import top_plate as TP

# ⚠ THE BARE KEY, NOT A DRIVER BODY. This was 6.0 "generous on purpose" and that generosity
# produced a WRONG ANSWER: it reported the optical board obstructing jack 0 by 1.60 mm, when
# the board is deliberately sized for a bare key and clears it by 1.775 against the 1.4435 it
# needs (optical_pickup's own assert, once it was reading the right edge). Size the probe to
# the tool the project actually standardised on -- 2.5 mm across flats, 2.887 across corners.
KEY_D = 2.887          # 2.5 mm hex key, ACROSS CORNERS (= 2 * _HEX25_R)
COL_H = 45.0           # how far up the key has to swing clear
BORE_D = TP.HEAD_POCKET_D


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    print("assembly %d solids ; head pocket O%.1f, probing a O%.1f column %.0f mm up"
          % (len(comps), BORE_D, KEY_D, COL_H))

    for k in range(3):
        nm = "pickup_jack_screw_%d" % k
        scr = dict(comps).get(nm)
        if scr is None:
            print("\n%s: NOT IN THE ASSEMBLY" % nm)
            continue
        bb = scr.BoundingBox()
        cx, cy = (bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0
        top = bb.zmax
        print("\n=== %s  axis (%.2f, %.2f)  head top z %.2f ===" % (nm, cx, cy, top))
        col = (cq.Workplane("XY")
               .add(cq.Solid.makeCylinder(KEY_D / 2.0, COL_H, cq.Vector(cx, cy, top))))
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
                hits.append((v, name, it.BoundingBox()))
        if not hits:
            print("    CLEAR -- a driver reaches this one")
        for v, name, b in sorted(hits, reverse=True):
            print("    %-22s %8.2f mm3   z %7.2f..%7.2f   x %8.2f..%8.2f y %8.2f..%8.2f"
                  % (name, v, b.zmin, b.zmax, b.xmin, b.xmax, b.ymin, b.ymax))
            print("        -> blocks from %.2f mm above the head; trim depth needed %.2f mm"
                  % (b.zmin - top, b.zmax - b.zmin))


if __name__ == "__main__":
    main()
