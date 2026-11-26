"""OWNROUTE_RAILS_EARLY: rails alone first, signals round the held rails, then everyone.

    py -3.12 test_rails_early.py

The stage order with _rounds stubbed (no board): the rails are the non-plane nets drawn at
least RAIL_W_MIN wide (a 4.0 mm plane net and a 0.39 mm signal are not), negotiated alone and
widest first (ties: shortest span); the signal rounds lock every rail and route no rail; the
last negotiation starts from the nets that share or failed, so a rail that settled keeps its
copper. With the flag unset, run()'s single negotiation is unchanged (source check).
Exit 0 = PASS.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from router.negotiate import Router  # noqa: E402

bad = []


class N:
    def __init__(self, name, w, span, plane=False):
        self.name, self.width, self.plane = name, w, plane
        self.bbox = (0.0, span, 0.0, 0.0)
        self.paths, self.failed = [[1]], False


r = Router.__new__(Router)
nets = [N("SIG_A", 0.20, 5), N("V5_PRE", 1.20, 30), N("GND", 4.0, 90, plane=True), N("NEAR", 0.39, 3),
        N("+24V", 1.20, 10), N("VSTBY", 0.60, 4), N("SIG_B", 0.15, 50)]
r.nets = nets
r.log = lambda s: None
calls = []


def rounds(todo, pf, iters, budget_s, locked=()):
    calls.append(([n.name for n in todo], set(n.name for n in locked), iters))
    return [], pf * 2


r._rounds = rounds
r._conflicts = lambda n: [np.array([7])] if n.name == "SIG_B" else [np.array([], np.int64)]
todo, pf = r._rails_early(0.5, 40, 1000)
if len(calls) != 3:
    bad.append("want 3 negotiations (rails, signals held, everyone), got %d" % len(calls))
else:
    (c1, l1, i1), (c2, l2, i2), (c3, l3, _i3) = calls
    if c1 != ["+24V", "V5_PRE", "VSTBY"]:
        bad.append("rails / order: %s (want +24V V5_PRE VSTBY: widest, then shortest span)" % c1)
    if l1:
        bad.append("the rails stage locked %s" % l1)
    if i1 != Router.RAILS_ROUNDS:
        bad.append("rails stage ran %d rounds, want RAILS_ROUNDS" % i1)
    if set(c2) & set(c1) or l2 != set(c1) or i2 != Router.RAILS_HOLD_ROUNDS:
        bad.append("signal rounds: routed %s locked %s rounds %d" % (c2, l2, i2))
    if c3 != ["SIG_B"] or l3:
        bad.append("last negotiation should start from the sharing nets only (SIG_B), got %s" % c3)
src = open(os.path.join(HERE, "router", "negotiate.py"), encoding="utf-8").read()
if "todo, pf = self._rounds(list(self.nets), pf0, iters, budget_s)" not in src:
    bad.append("flag unset: run()'s single negotiation is not the unchanged call")
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
