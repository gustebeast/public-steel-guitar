"""Every pad of a chain part is joined, not just the one a pair hop lands on (brain_board esc11, 2026-11-22).

    py -3.12 test_router_node_pads.py <dir holding a placed brain board as b.kicad_pcb /
        b.kicad_pro / b.board.json (rPS_11a3's .unrouted board)>

USB-C J1 carries D- on A7 and B7 (and D+ on A6 / B6). The pair's chain hop lands on one of
them; every pad of both parts was then marked done and the other was never joined -- USBA_DM_J,
USBB_DM_J and SVC_DM open in DRC on every esc11 seed while the router reported them routed.
Routes the USBA_DP_J / USBA_DM_J pair alone and requires, for each rail, either copper on every
one of its pads' pieces or the net reported open (failed / n_open). The old marking's switch is
deleted (it failed this test). Exit 0 = PASS.
"""
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from router.model import Model  # noqa: E402
from router.negotiate import Router  # noqa: E402

import _testargs  # noqa: E402
_testargs.need(1, '<dir> holding a placed brain board as b.kicad_pcb / b.kicad_pro')
m = Model(os.path.join(os.path.abspath(sys.argv[1]), "b"))
r = Router(m)
want = ("USBA_DP_J", "USBA_DM_J")
allnets = r.build_nets(pours=m.fills)
r.nets = [n for n in allnets if n.name in want]
r.log = lambda *a: None
r.run(budget_s=300)
H, W = r.H, r.W
bad = []
for n in r.nets:
    cells = np.unique(np.concatenate([p for p in n.paths if len(p)])) if any(len(p) for p in n.paths) else np.empty(0, np.int64)
    r2 = cells % (H * W)
    flat2 = set(r2.tolist())               # 2-D: a via reaches every layer
    lid = {nm: k for k, nm in enumerate(m.route_layers)}
    unreached = []
    for p in m.pads:
        if p["net"] != n.name:
            continue
        pc = r._cells("p", p, lid)
        if not (set(pc.tolist()) & set(cells.tolist())):
            unreached.append(p["name"])
    reported = bool(n.failed or getattr(n, "n_open", 0))
    print("%s: legs %d, paths %d, pads without copper %s, reported open %s"
          % (n.name, len(n.legs), len(n.paths), unreached or "none", reported))
    if unreached and not reported:
        bad.append("%s: %s never joined, and the net is reported routed" % (n.name, ", ".join(unreached)))
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.stdout.flush()
os._exit(1 if bad else 0)
