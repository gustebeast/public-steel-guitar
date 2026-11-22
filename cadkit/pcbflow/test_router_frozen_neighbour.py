"""A net's own frozen band does not hide a neighbour's from the router (2026-11-22).

    py -3.12 test_router_frozen_neighbour.py <dir holding rPS_12k5's UNROUTED board as
        b.kicad_pcb / b.board.json / b.kicad_pro / b.net>

brain_board rPS_11k1 and rPS_12k5 (ck_kwall) both stopped on one cut: +5V_SW's router track
(93.53, 131.10)->(95.08, 131.10) on F.Cu ran 0.40 mm from +5V_BB's band, where a 0.51 mm track
needs 0.255 + the band's 0.5 zone clearance. model.frozen_d holds the distance to the NEAREST
band of any net, and there +5V_SW's own band was nearer (0.29-0.40), so the wall and the
end-of-route audit both read "own band, no wall".

1. Along that track, frozen_foreign() for +5V_SW names +5V_BB within its reach (the wall in
   negotiate and the audit in _frozen_hits both ask frozen_foreign).
2. Every F.Cu cell within 3 mm of a band, where a frozen net's own band is nearest, gets the
   true nearest other band (against a brute per-net distance transform).
Exit 0 = PASS.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from router.model import Model  # noqa: E402


def main(d):
    bad = []
    m = Model(os.path.join(d, "b"))
    sw, bb = m.net_id["+5V_SW"], m.net_id["+5V_BB"]
    k = m.route_layers.index("F.Cu")
    need = 0.51 / 2 + m.frozen_zclr[bb]
    for x in (93.535, 94.0, 94.5):
        j = int(round((x - m.x0) / m.pitch))
        i = int(round((131.1 - m.y0) / m.pitch))
        fd, fn = m.frozen_foreign((k, i, j), sw)
        print("(%.3f, 131.10): nearest band %d at %.3f; foreign for +5V_SW: %d at %.3f (need %.3f)"
              % (x, m.frozen_nn[k, i, j], m.frozen_d[k, i, j], int(fn), float(fd), need))
        if int(fn) != bb or not float(fd) < need:
            bad.append("+5V_SW at (%.3f, 131.10) does not see +5V_BB's band within its reach" % x)
    # brute check on F.Cu: for every frozen net, cells whose nearest band is its own
    from scipy.ndimage import distance_transform_edt
    fk = m.frozen_net[k]
    worst = 0.0
    for nid in np.unique(fk[fk != 0]):
        mine = m.frozen_nn[k] == nid
        if not mine.any():
            continue
        other = (fk != 0) & (fk != nid)
        if not other.any():
            continue
        dt = distance_transform_edt(~other) * m.pitch
        near = mine & (dt < 3.0)                 # within any reach that matters
        fd, _ = m.frozen_foreign((k,) + np.nonzero(near), nid)
        err = np.abs(fd - dt[near]).max() if near.any() else 0.0
        worst = max(worst, float(err))
    print("F.Cu: worst foreign-distance error within 3 mm of a band: %.4f mm" % worst)
    if worst > m.pitch:
        bad.append("frozen_foreign is off by %.3f mm somewhere on F.Cu" % worst)
    return bad


if __name__ == "__main__":
    bad = main(os.path.abspath(sys.argv[1]))
    for x in bad:
        print("  FAIL:", x)
    print("PASS" if not bad else "FAIL")
    sys.stdout.flush()
    os._exit(1 if bad else 0)
