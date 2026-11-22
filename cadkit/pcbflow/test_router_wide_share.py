"""Two wide nets too close are seen as sharing space (brain_board esc11, 2026-11-22).

    py -3.12 test_router_wide_share.py <dir holding a placed brain board as b.kicad_pcb /
        b.kicad_pro / b.board.json (rPS_11a3's .unrouted board)>

The router stamped every net for a REFERENCE-width neighbour and read "shares" on the
centreline only, so VIN_BUS (3.79) and VIN_BRAIN (4.0) could lie 2.26 mm apart where the rules
want 4.05 -- and route.py's import took the copper up as a short (7-10 tracks every esc11 seed).
Synthetic straight B.Cu runs for the two nets, nothing else marked:
  3.0 mm apart -> both nets share space (_conflicts non-empty); the old centreline test
                  called them clean (the bug; its switch is deleted);
  4.3 mm apart -> neither shares (no false alarm).
Exit 0 = PASS.
"""
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from router.model import Model  # noqa: E402
from router.negotiate import Router  # noqa: E402

m = Model(os.path.join(os.path.abspath(sys.argv[1]), "b"))
r = Router(m)
nets = {n.name: n for n in r.build_nets(pours=m.fills)}
A, B = nets["VIN_BUS"], nets["VIN_BRAIN"]
k = m.route_layers.index("B.Cu")
H, W = r.H, r.W
i_mid = H // 2
j0, j1 = W // 4, W // 4 + 400
bad = []


def run(sep_mm):
    for n in (A, B):
        r._unmark(n)
    di = int(round(sep_mm / m.pitch))
    A.paths = [np.array([k * H * W + i_mid * W + j for j in range(j0, j1)], np.int64)]
    B.paths = [np.array([k * H * W + (i_mid + di) * W + j for j in range(j0, j1)], np.int64)]
    A.necks, B.necks = [np.zeros(A.paths[0].size, bool)], [np.zeros(B.paths[0].size, bool)]
    r._mark(A)
    r._mark(B)
    return bool(r._conflicts(A)), bool(r._conflicts(B))


need = (A.width + B.width) / 2.0 + m.clear + m.margin
print("VIN_BUS %.2f, VIN_BRAIN %.2f: centrelines need %.3f mm" % (A.width, B.width, need))
got = run(3.0)
print("3.0 mm, wide test:", got)
if not all(got):
    bad.append("3.0 mm apart is not seen as sharing by both nets")
got = run(4.3)
print("4.3 mm, wide test:", got)
if any(got):
    bad.append("4.3 mm apart (legal) is called sharing")
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.stdout.flush()
os._exit(1 if bad else 0)
