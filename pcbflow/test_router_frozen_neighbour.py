"""A net's own frozen band does not hide a neighbour's from the router (2026-11-22).

    py -3.12 test_router_frozen_neighbour.py

brain_board rPS_11k1 and rPS_12k5 (ck_kwall) both stopped on one cut: +5V_SW's router track ran
0.40 mm from +5V_BB's band, where a 0.51 mm track needs 0.255 + the band's 0.5 zone clearance.
model.frozen_d holds the distance to the NEAREST band of any net, and there +5V_SW's own band was
nearer, so the wall and the end-of-route audit both read "own band, no wall".

On the committed fixture (testdata/frozen_bands, make.py): NEAR's F.Cu band y 15.0..15.35, FAR's
y 15.75..17.0, both zone clearance 0.5.
1. Along y 15.42 / 15.45 / 15.50 (NEAR's own band nearer), frozen_foreign() for NEAR names FAR
   within a 0.2 mm track's reach (the wall in negotiate and the audit in _frozen_hits ask it).
2. Every F.Cu cell within 3 mm of a band, where a frozen net's own band is nearest, gets the
   other band's distance to its EDGE (a brute per-net distance transform, sqrt(2) pitch less --
   model._edge_d; cadkit f857524).
Exit 0 = PASS.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from router.model import Model  # noqa: E402

FX = os.path.join(HERE, "testdata", "frozen_bands", "b")


def main():
    bad = []
    m = Model(FX)
    near, far = m.net_id["NEAR"], m.net_id["FAR"]
    k = m.route_layers.index("F.Cu")
    need = 0.2 / 2 + m.frozen_zclr[far]
    for y in (15.42, 15.45, 15.50):
        j = int(round((15.0 - m.x0) / m.pitch))
        i = int(round((y - m.y0) / m.pitch))
        fd, fn = m.frozen_foreign((k, i, j), near)
        print("(15.00, %.2f): nearest band %d at %.3f; foreign for NEAR: %d at %.3f (need %.3f)"
              % (y, m.frozen_nn[k, i, j], m.frozen_d[k, i, j], int(fn), float(fd), need))
        if m.frozen_nn[k, i, j] != near:
            bad.append("the fixture no longer has NEAR's own band nearest at y %.2f" % y)
        if int(fn) != far or not float(fd) < need:
            bad.append("NEAR at y %.2f does not see FAR's band within its reach" % y)
    from scipy.ndimage import distance_transform_edt
    fk = m.frozen_net[k]
    worst = 0.0
    for nid in np.unique(fk[fk != 0]):
        mine = m.frozen_nn[k] == nid
        other = (fk != 0) & (fk != nid)
        if not mine.any() or not other.any():
            continue
        dt = distance_transform_edt(~other)
        dt = np.where(dt > 0, np.maximum(dt - np.sqrt(2.0), 0.0), 0.0) * m.pitch   # to the edge (model._edge_d)
        near_ = mine & (dt < 3.0)
        fd, _ = m.frozen_foreign((k,) + np.nonzero(near_), nid)
        err = np.abs(fd - dt[near_]).max() if near_.any() else 0.0
        worst = max(worst, float(err))
    print("F.Cu: worst foreign-distance error within 3 mm of a band: %.4f mm" % worst)
    if worst > 1e-4:
        bad.append("frozen_foreign is off by %.3f mm somewhere on F.Cu" % worst)
    return bad


if __name__ == "__main__":
    bad = main()
    for x in bad:
        print("  FAIL:", x)
    print("PASS" if not bad else "FAIL")
    sys.stdout.flush()
    os._exit(1 if bad else 0)
