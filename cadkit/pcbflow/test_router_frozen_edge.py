"""The router's frozen-band wall measures to the band's EDGE, not its nearest cell centre
(brain_board fold10, 2026-11-26; cadkit f857524).

    py -3.12 test_router_frozen_edge.py

fold10 routed two CM5_PWRBTN vias (r 0.3) 0.778 mm from +5V_CM5's B.Cu band outline, where the
wall promises r + zc = 0.8: model.frozen_d was measured cell centre to cell centre, and the
outline sits up to a pitch nearer. The refill knocked the 1.45 band back and the gate read its
declared 1.70 neck at 2.25.

On the committed fixture (testdata/frozen_bands, make.py): BAND, a 1.45 mm B.Cu band at 30
degrees, zone clearance 0.5.
1. A via of net SIG whose edge is 0.47 mm (centre 0.77) off the outline, at 40 places along the
   band, is walled at every one (frozen_foreign under r + zc; the ban in negotiate and the
   audit in _frozen_hits both ask it).
2. On every B.Cu cell within 2 mm outside the band, frozen_d is a LOWER bound on the exact
   distance to its outline.
Exit 0 = PASS (FAILs on f857524's parent).
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from router.model import Model  # noqa: E402

FX = os.path.join(HERE, "testdata", "frozen_bands", "b")


def _seg_d(px, py, pts):
    """Exact distance from points (px, py) to a closed polygon's edges."""
    best = np.full(np.shape(px), np.inf)
    for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy or 1e-12
        t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0.0, 1.0)
        best = np.minimum(best, np.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return best


def main():
    bad = []
    m = Model(FX)
    sig, band = m.net_id["SIG"], m.net_id["BAND"]
    k = m.route_layers.index("B.Cu")
    poly = [list(map(tuple, p)) for L_, p in m.frozen["BAND"] if L_ == "B.Cu"]
    reach = m.via_d / 2.0 + m.frozen_zclr[band]
    a = math.radians(30)
    ux, uy = math.cos(a), math.sin(a)
    unwalled = 0
    for n in range(40):
        s = 2.0 + n * 0.36                              # along the band, clear of its ends
        for side in (1, -1):
            x = 4.0 + ux * s - side * uy * (1.45 / 2 + 0.77)
            y = 4.0 + uy * s + side * ux * (1.45 / 2 + 0.77)
            j, i = int(round((x - m.x0) / m.pitch)), int(round((y - m.y0) / m.pitch))
            cx, cy = float(m.cx[j]), float(m.cy[i])       # the cell the via would sit on
            true = float(min(_seg_d(cx, cy, p) for p in poly))
            fd, fn = m.frozen_foreign((slice(None), i, j), sig)
            if true < reach and not ((fn == band) & (fd < reach)).any():
                unwalled += 1
    print("vias inside r + zc of the band's edge left unwalled: %d of 80 sites" % unwalled)
    if unwalled:
        bad.append("%d via site(s) inside the band's reach are not walled" % unwalled)
    fk = m.frozen_net[k]
    rr, cc = np.nonzero(fk == band)
    i0, i1 = max(rr.min() - 40, 0), min(rr.max() + 41, fk.shape[0])
    j0, j1 = max(cc.min() - 40, 0), min(cc.max() + 41, fk.shape[1])
    ii, jj = np.mgrid[i0:i1, j0:j1]
    exact = np.minimum.reduce([_seg_d(m.cx[jj], m.cy[ii], p) for p in poly])
    out = (fk[i0:i1, j0:j1] == 0) & (m.frozen_nn[k, i0:i1, j0:j1] == band) & (exact < 2.0)
    over = (m.frozen_d[k, i0:i1, j0:j1] - exact)[out]
    worst = float(over.max()) if over.size else 0.0
    print("B.Cu cells within 2 mm outside the band: %d; worst frozen_d over the exact edge "
          "distance %.4f mm (must be <= 0)" % (int(out.sum()), worst))
    if not out.any():
        bad.append("the fixture has no cells beside its band")
    if worst > 1e-3:
        bad.append("frozen_d overstates the distance to the band's edge by %.3f mm" % worst)
    return bad


if __name__ == "__main__":
    bad = main()
    for x in bad:
        print("  FAIL:", x)
    print("PASS" if not bad else "FAIL")
    sys.stdout.flush()
    os._exit(1 if bad else 0)
