"""quick.py: one negotiation round -- the cheap REJECT filter in front of a placement score.

    py -3.12 -m router.quick <stem> [k]        # prints one JSON line

k rounds (default 1) of the main negotiation, no global plan, no rip / pair finish. What it
can tell (optical, 2026-11-09 and 11-14): a move that leaves a net with NO PATH, or that makes
several nets newly share space in round 1, is broken -- 0 false alarms on 23 placements. What
it CANNOT tell: which of two working placements routes better (12 deterministic optical
variants, rank correlation with the full route about 0 at every k <= 8). So it rejects, it
never ranks: the score is the full route or rescore.delta_run from a parent.
"""
from __future__ import annotations

import json
import sys
import time


def quick(stem, k=1):
    from .model import Model
    from .negotiate import Router
    t0 = time.process_time()
    m = Model(stem)
    r = Router(m)
    r.log = lambda s: None
    r.build_nets(pours=m.fills)
    r._premerge()
    r._neg = (1.6, 0.4)
    todo, _ = r._rounds(list(r.nets), 0.5, k, 1e9)
    return dict(nopath=sorted(n.name for n in r.nets if n.failed),
                share=sorted(n.name for n in todo if not n.failed),
                cpu=round(time.process_time() - t0, 1))


def reject(cand, parent, max_new_share=4):
    """Why `cand` (a quick() result) is broken against its parent's, or None."""
    np_ = sorted(set(cand["nopath"]) - set(parent["nopath"]))
    if np_:
        return "no path in round 1: %s" % " ".join(np_)
    ns = sorted(set(cand["share"]) - set(parent["share"]))
    if len(ns) > max_new_share:
        return "%d nets newly share space in round 1 (over %d): %s" % (len(ns), max_new_share, " ".join(ns[:8]))
    return None


if __name__ == "__main__":
    print(json.dumps(quick(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1)), flush=True)
