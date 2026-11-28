"""Router.frozen_audit: a foreign path into a frozen band is named, and ripped before emit.

    py -3.12 cadkit/pcbflow/test_frozen_audit.py <stem>

The stem is an unrouted board with frozen bands (brain_board esc10 rPS_10a1's +5V_BB band was
the reference: R211.2 GND at (90.50, 133.90), the band's inside at (90.33, 133.20)).
  1  a GND join from R211.2 to a via INSIDE the band       -> one hit, the band named
  2  rip=True                                               -> that join empty, n_open + 1
  3  the same join to a via 3 mm clear of every band        -> no hit
Exit code 0 = all as expected.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from router.model import Model  # noqa: E402
from router.negotiate import Router  # noqa: E402

import _testargs  # noqa: E402
_testargs.need(1, '<stem>: an unrouted board with frozen bands (brain_board rPS_10a1)')
m = Model(sys.argv[1])
r = Router(m)
r.log = print
r.build_nets(pours=m.fills)
H, W = r.H, r.W
bad = []


def line(x0, y0, x1, y1, k):
    n = int(max(abs(x1 - x0), abs(y1 - y0)) / m.pitch) + 1
    out = []
    for t in np.linspace(0, 1, n):
        i, j = m.ij(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
        c = k * H * W + i * W + j
        if not out or out[-1] != c:
            out.append(c)
    return out


gnd = next(n for n in r.nets if n.name == "GND")
f = line(90.50, 133.90, 90.335, 133.20, 0)
inside = np.array(f + [f[-1] % (H * W) + H * W], np.int64)          # F.Cu then a via to In1
gnd.paths = [inside] + [np.empty(0, np.int64)] * (len(gnd.pieces) - 2)
gnd.necks = [np.zeros(p.size, bool) for p in gnd.paths]
hits = r._frozen_hits(gnd)
ok = len(hits) == 1 and hits[0][3] == ["+5V_BB"]
print("ok " if ok else "BAD", "1 inside the band:", hits)
bad += [] if ok else ["1"]
n0 = getattr(gnd, "n_open", 0)
r._mark(gnd)
r.frozen_audit("test", rip=True)
ok = gnd.paths[0].size == 0 and gnd.n_open == n0 + 1 and not gnd.failed
print("ok " if ok else "BAD", "2 ripped: path %d cells, n_open %d" % (gnd.paths[0].size, gnd.n_open))
bad += [] if ok else ["2"]
f = line(90.50, 133.90, 90.50, 136.90, 0)
clear = np.array(f + [f[-1] % (H * W) + H * W], np.int64)
i_, j_ = m.ij(90.50, 136.90)
print("   (clear end: frozen_d F.Cu %.2f)" % float(m.frozen_d[0, i_, j_]))
gnd.paths[0] = clear
gnd.necks[0] = np.zeros(clear.size, bool)
hits = r._frozen_hits(gnd)
ok = not hits
print("ok " if ok else "BAD", "3 clear of every band:", hits)
bad += [] if ok else ["3"]
print("frozen audit: %s" % ("PASS" if not bad else "FAIL " + ",".join(bad)))
sys.stdout.flush()
os._exit(1 if bad else 0)
