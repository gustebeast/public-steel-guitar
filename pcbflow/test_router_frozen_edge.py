"""The router's frozen-band wall measures to the band's EDGE, not its nearest cell centre
(brain_board fold10, 2026-11-26).

    py -3.12 test_router_frozen_edge.py <dir holding fold10_s2's UNROUTED board as
        b.kicad_pcb / b.board.json / b.kicad_pro / b.net>

fold10 routed two CM5_PWRBTN vias (r 0.3) at (127.08, 93.70) and (125.94, 94.85), 0.778 mm from
+5V_CM5's B.Cu band outline where the wall promises r + zc = 0.8: model.frozen_d was measured
cell centre to cell centre, and the outline sits up to a pitch nearer. The refill knocked the
1.45 band back there and the gate read its declared 1.70 neck at 2.25.

1. At both vias, frozen_foreign() for CM5_PWRBTN names +5V_CM5 within a via's reach (the ban
   in negotiate and the audit in _frozen_hits both ask it).
2. On every B.Cu cell within 2 mm outside that band, frozen_d is a LOWER bound on the exact
   distance to its outline (the band polygons the model read).
Exit 0 = PASS.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from router.model import Model  # noqa: E402


def _seg_d(px, py, pts):
    """Exact distance from points (px, py) to a closed polygon's edges."""
    best = np.full(px.shape, np.inf)
    for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy or 1e-12
        t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0.0, 1.0)
        best = np.minimum(best, np.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return best


def main(d):
    bad = []
    m = Model(os.path.join(d, "b"))
    me, band = m.net_id["CM5_PWRBTN"], m.net_id["+5V_CM5"]
    k = m.route_layers.index("B.Cu")
    for x, y in ((127.08, 93.70), (125.94, 94.85)):
        j, i = int(round((x - m.x0) / m.pitch)), int(round((y - m.y0) / m.pitch))
        fd, fn = m.frozen_foreign((slice(None), i, j), me)
        reach = m.via_d / 2.0 + m.frozen_zclr[band]
        hit = (fn == band) & (fd < reach)
        print("(%.2f, %.2f): +5V_CM5 band at %.3f on B.Cu (a via needs %.3f) -> %s"
              % (x, y, float(fd[k]), reach, "walled" if hit.any() else "NOT walled"))
        if not hit.any():
            bad.append("a CM5_PWRBTN via at (%.2f, %.2f) is not walled off +5V_CM5's band" % (x, y))
    polys = [pts for L_, pts in m.frozen["+5V_CM5"] if L_ == "B.Cu"]
    fk = m.frozen_net[k]
    rr, cc = np.nonzero(fk == band)
    i0, i1 = max(rr.min() - 40, 0), rr.max() + 41
    j0, j1 = max(cc.min() - 40, 0), cc.max() + 41
    sub = fk[i0:i1, j0:j1]
    ii, jj = np.mgrid[i0:min(i1, fk.shape[0]), j0:min(j1, fk.shape[1])]
    X, Y = m.cx[jj], m.cy[ii]
    exact = np.minimum.reduce([_seg_d(X, Y, list(map(tuple, p))) for p in polys])
    fdb = m.frozen_d[k, i0:i1, j0:j1]
    out = (sub == 0) & (m.frozen_nn[k, i0:i1, j0:j1] == band) & (exact < 2.0)
    over = (fdb - exact)[out]
    worst = float(over.max()) if over.size else 0.0
    print("B.Cu cells within 2 mm outside the band: %d; worst frozen_d over the exact edge "
          "distance %.4f mm (must be <= 0)" % (int(out.sum()), worst))
    if worst > 1e-3:
        bad.append("frozen_d overstates the distance to +5V_CM5's edge by %.3f mm" % worst)
    for b_ in bad:
        print("  FAIL:", b_)
    print("PASS" if not bad else "FAIL")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
