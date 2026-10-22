"""ROUND 6: the 8-tenon lever and its 8-mortise floor cut from an instrument BUILT at a given
lever clearance (D.LEVER_MORT_CLR), so the floor's depth (D.BOTTOM_T) and every lever part
follow it as they would in the instrument.

    py -3.12 -m src.test.lever_c_round6 0.35     # -> src/test/test_r6_lever8_c035.step + floor

The clearance is patched before anything reads it: run one clearance per process.
"""
from __future__ import annotations

import sys

from src import dimensions as D


def main(argv=None):
    c = float((argv or sys.argv[1:])[0])
    D.LEVER_MORT_CLR = c
    from src.test import bench_joinery as BJ
    from src import knee_lever as KL
    assert KL.MORT_CLR == c, "knee_lever read the clearance before the patch"
    from cadkit.orientation import PrintOrientation as PO
    from cadkit.step_export import export_print
    comps, where = BJ.components(live=True)
    tag = "c%03d" % round(c * 100)
    for name, out in (("r3_lever", "r6_lever8"), ("r6_floor8", "r6_floor8")):
        cp = next(k for k in BJ.COUPONS if k.name == name)
        wp, n, _crumbs, _fx = cp.build(comps)
        assert n == 1, "%s: %d solids" % (name, n)
        path = BJ.HERE / ("test_%s_%s.step" % (out, tag))
        export_print(wp, PO.from_build_dir(cp.up, "as the part it is cut from"), str(path))
        print("wrote", path, "%.1f cm3" % (wp.val().Volume() / 1000.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
