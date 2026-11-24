"""PROOF that the drive-travel gate's input is unchanged by reusing the parts that stand still.

The gate redraws the instrument at each end of the drive's travel (t 0 and 1). Since 2026-11-23
it redraws only the drive and reuses the rest of the T_OPEN list (src.build.collect_components(t,
base=...); direct_bench.assembly_at). This draws BOTH ways at t 0 and 1 and compares them
component by component: the name (and its place in the list), the volume, the centre of mass,
the bounding box, and the overlap gate's own fingerprint of the shape (cadkit.overlap_check:
the BREP's bytes, which its pair cache keys on). Prints the diff -- it must be empty -- and the
time each way.

    py -3.12 -m tools.check_travel_reuse
"""

from __future__ import annotations

import sys
import time


def _row(name, wp):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from cadkit.overlap_check import fingerprint
    s = wp.val() if hasattr(wp, "val") else wp
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(s.wrapped, g)
    c = g.CentreOfMass()
    bb = s.BoundingBox()
    return (name, round(g.Mass(), 6), tuple(round(v, 6) for v in (c.X(), c.Y(), c.Z())),
            tuple(round(v, 6) for v in (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)),
            fingerprint(s))


def main() -> int:
    from src.build import collect_components
    base = collect_components()
    diffs = 0
    for t in (0.0, 1.0):
        # the reuse FIRST: the drive is kept in memory once drawn, so whichever runs second is
        # flattered -- this way the saving printed is the least it can be
        t0 = time.perf_counter()
        fast = collect_components(t, base=base)
        t_fast = time.perf_counter() - t0
        t0 = time.perf_counter()
        full = collect_components(t)
        t_full = time.perf_counter() - t0
        a = [_row(n, w) for n, w in full]
        b = [_row(n, w) for n, w in fast]
        d = [(k, x, y) for k, (x, y) in enumerate(zip(a, b)) if x != y]
        if len(a) != len(b):
            d.append(("length", len(a), len(b)))
        print(f"t = {t:.0f}: {len(a)} components each way; full redraw {t_full:.1f} s, reuse "
              f"{t_fast:.1f} s ({t_full - t_fast:+.1f} s); {len(d)} difference(s)", flush=True)
        for k, x, y in d[:20]:
            print(f"   [{k}]\n     full  {x}\n     reuse {y}")
        diffs += len(d)
    print("DIFF EMPTY: the gate's input is unchanged" if diffs == 0 else f"{diffs} DIFFERENCE(S)")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
