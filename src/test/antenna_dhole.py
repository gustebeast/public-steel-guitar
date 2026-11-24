"""ANTENNA D-HOLE COUPON (lead, 2026-11-23): the Wi-Fi antenna's floor tab cut out of the REAL body.

The SC0480 kit's SMA bulkhead keys into a D-hole (Ø6.5, a flat 6.0 across; src.antenna), drawn at the
kit's panel sizes and printed SIDEWAYS in the body (builds -Z -> +Z, the flat as the hole's ceiling).
INSTALL_NOTES calls it unverified until a coupon shows the thread passes and the flat keys it.

The coupon is the body itself -- kept(direct_bench._body) intersected with a box round the tab, its
ribs and the floor under them -- so it cannot drift from the instrument (cadkit AGENTS.md: share the
real geometry). Printed as the body prints: the floor on the bed, -Z -> +Z, PETG-GF on the 0.8.

    py -3.12 -m src.test.antenna_dhole            # sizes and the fit over the bulkhead's thread
    py -3.12 -m src.test.antenna_dhole --export   # ...and write src/test/test_antenna_dhole.step

THE TEST: push the bulkhead through from the ribs' side (+X), flat up. It should pass the hole
without forcing, and NOT turn once in (the flat keys it); the nut then runs down to the tab by
hand. Tight: the hole printed small (sideways holes print near size -- memory teardrop-hole-oversize);
turns: the flat printed high.
"""

from __future__ import annotations

import argparse
import os
import sys

import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src import antenna as A                            # noqa: E402
from src import direct_bench as DB                      # noqa: E402
from cadkit.kept import kept                            # noqa: E402

MARGIN = 3.0                       # round the tab and its ribs, in X and Y
THREAD_D, THREAD_FLAT = 6.35, 5.85  # the bulkhead's 1/4-36 thread and its flat across (direct_bench._antenna_parts)


def coupon() -> cq.Workplane:
    """The body round the antenna tab, in the world (as the body sits)."""
    bx, by, bz = A.BASE
    x0 = A.BOSS_X - MARGIN
    x1 = A.BOSS_X + A.PANEL_T + DB.ANT_RIB[1] + MARGIN
    hw = DB.ANT_TAB_R + MARGIN
    z0 = DB.body_box()["outer"][2][0] - 1.0            # the floor's underside, and a little
    z1 = bz + DB.ANT_TAB_R + 1.0                       # over the tab's round top
    box = DB.box_at(x1 - x0, 2 * hw, z1 - z0, x=(x0 + x1) / 2, y=by, z=(z0 + z1) / 2)
    out = kept(DB._body).intersect(box)
    assert len(out.solids().vals()) == 1, "the coupon is one piece"
    return out


def placed() -> cq.Workplane:
    """The coupon on the bed: the floor's underside at z 0, centred on the hole in X/Y."""
    w = coupon()
    bb = w.val().BoundingBox()
    _, by, _ = A.BASE
    return w.translate((-(bb.xmin + bb.xmax) / 2, -by, -bb.zmin))


def report(w: cq.Workplane) -> list:
    bb = w.val().BoundingBox()
    flat = A.D_HOLE_FLAT
    return [f"coupon {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, {w.val().Volume() / 1000:.2f} cm3",
            f"D-hole Ø{A.D_HOLE_D} with its flat {flat} across, over the bulkhead's Ø{THREAD_D} thread "
            f"(flat {THREAD_FLAT}): {A.D_HOLE_D - THREAD_D:.2f} on the Ø, {flat - THREAD_FLAT:.2f} on the flat",
            f"tab {A.PANEL_T} thick (the kit's panel), round top R {DB.ANT_TAB_R:.2f}"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", action="store_true", help="write src/test/test_antenna_dhole.step")
    a = ap.parse_args()
    w = placed()
    for ln in report(w):
        print(ln, flush=True)
    if a.export:
        from cadkit.step_export import export_step
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_antenna_dhole.step")
        export_step(w, path)
        print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
