"""Cables against CABLES -- the one pairing the overlap gate never looks at.

    py -3.12 -m tools.check_cable_pairs

The gate allow-lists wire against wire as insulated crossings, which is right for a
crossing and wrong for two cables lying THROUGH each other. That blind spot hid, on the
committed model: the two 24 V feeds sharing one lane (416 mm3 each), every tee-to-tee trunk
hop's CAN pair inside its 24 V pair (18 x ~80 mm3), and three keyhead bay wires sharing one
column (234 / 69 / 15.5 mm3). None of it was ever reported.

A contact confined to one small region (under 4 mm across) is a touch -- cables converging
on one connector, or a crossing -- and is only counted. A contact that runs is listed: that
is two cables occupying the same length of space. Exit code = the number that run.
"""
import itertools
import sys
import time

sys.path.insert(0, ".")
import cadquery as cq                                        # noqa: E402

from src import wiring as W, optical_pickup as O             # noqa: E402

RUN_MM, MIN_VOL = 4.0, 0.5


def main():
    ws = {n: w.val() for n, w in W.build_wires()}
    ws["optical_cable_usb"] = O.opt_cables("usb").val()
    ws["optical_cable_pwr"] = O.opt_cables("pwr").val()
    t = time.time()
    runs, touches = [], 0
    for a, b in itertools.combinations(list(ws), 2):
        A, B = ws[a], ws[b]
        ba, bb = A.BoundingBox(), B.BoundingBox()
        if (ba.xmin > bb.xmax or bb.xmin > ba.xmax or ba.ymin > bb.ymax
                or bb.ymin > ba.ymax or ba.zmin > bb.zmax or bb.zmin > ba.zmax):
            continue
        it = cq.Workplane("XY").add(A).intersect(cq.Workplane("XY").add(B)).val()
        v = it.Volume()
        if v <= MIN_VOL:
            continue
        ib = it.BoundingBox()
        span = max(ib.xlen, ib.ylen, ib.zlen)
        if span < RUN_MM:
            touches += 1
        else:
            runs.append((a, b, v, span))
    for a, b, v, span in sorted(runs, key=lambda r: -r[2]):
        print("  RUNS THROUGH  %-18s %-18s %7.2f mm3 over %.1f mm" % (a, b, v, span))
    print("%.1fs: %d pair(s) run through each other, %d touch at one spot"
          % (time.time() - t, len(runs), touches))
    return len(runs)


if __name__ == "__main__":
    sys.exit(main())
