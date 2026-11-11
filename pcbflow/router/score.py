"""score.py: a placed board's routability, measured by routing it (router alone, no finish).

    py -3.12 -m router.score <stem> [<stem> ...] [--jobs N] [--budget S]

One JSON line per board, keys in order of how much they matter:
  open        connections the router could not make (failed nets + open plane joins)
  pairs       differential-pair faults (pair_faults)
  islands     pour pieces left unjoined
  uncoupled   mm of declared pairs not running coupled
  contention  the negotiation's history cost summed over the board (where nets fought)
  hot         the three most contested 2 mm squares and the parts beside them
  length_mm   routed track length, vias  routed via count, sec  wall time
  failed      the nets behind `open`, faulted  the pairs behind `pairs` (what a placement fix aims at)
`key` is the tuple to sort placements by: smaller is better.

⚠ WHY THE ROUTE AND NOT A CHEAPER PROXY (ROUTER.md, "Pad-scale escape and RUDY", 2026-11-09).
Every cheap score tried failed to rank placements: per-part escape max-flow (every part
had 3-20x the lanes it needs; 0.24 correlation with its contention), RUDY over pad-scale
supply (Spearman 0.18-0.52, none of the router's top 10 blocks in its top 20), global
plan overflow (0.13-0.46), MST crossings and wirelength (flat across nudges). k-round
router proxies separate broken from fine but do not rank boards that close. With the
router at 15-75 s a board, the route itself is affordable -- and is the only measure
that agreed with the full chain. Several placements score at once, a process each
(negotiation does not parallelise inside one board: optical's 64 nets fall in 45 levels).
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def score(stem, budget_s=900.0):
    sys.path.insert(0, HERE)
    import numpy as np
    from router.model import Model
    from router.negotiate import Router
    from router import congestion
    t0 = time.time()
    m = Model(stem)
    r = Router(m)
    r.log = lambda s: None
    nets = r.build_nets(pours=m.fills)
    failed = r.run(budget_s=budget_s)
    pairs = sum(len(r.pair_faults(n) or ()) for n in nets
                if n.mate is not None and n.partner is None)
    isl = 0
    for n in nets:
        if n.plane and not n.failed:
            got = r._islands(n)
            if got is not None:
                isl += sum(1 for q in got[0] if q - 1 < len(n.paths) and n.paths[q - 1].size)
    part = sum(getattr(n, "n_open", 0) or 0 for n in nets if not n.failed)
    unc = 0.0
    for n in nets:
        if (n.mate is not None and n.partner is None and n.group is not None and not n.failed
                and not n.mate.failed and r._pair_spec(n) is not None):
            unc += r._uncoupled(n)
    # length and vias straight off the cell paths: a step within a layer is one pitch
    # (or a diagonal), a step between layers at the same cell is a via
    hw = r.H * r.W
    length, vias = 0.0, 0
    for n in nets:
        for p in n.paths or ():
            if p is None or len(p) < 2:
                continue
            p = np.asarray(p, np.int64)
            k, rc = p // hw, p % hw
            i, j = rc // r.W, rc % r.W
            same = k[1:] == k[:-1]
            vias += int((~same).sum())
            d = np.hypot(np.diff(i), np.diff(j))[same]
            length += float(d.sum()) * m.pitch
    hot = [{"x": round(x, 1), "y": round(y, 1), "near": refs[:3]}
           for _s, x, y, _l, refs in congestion.hotspots(r, top=3)]
    out = dict(open=len(failed) + part, pairs=pairs, islands=isl, uncoupled=round(unc, 2),
               contention=round(float(r.hist.sum()), 1), length_mm=round(length, 1),
               vias=vias, hot=hot, sec=round(time.time() - t0, 1),
               failed=sorted({getattr(n, "name", str(n)) for n in failed}
                             | {n.name for n in nets if not n.failed and (getattr(n, "n_open", 0) or 0)}),
               faulted=sorted(n.name for n in nets if n.mate is not None and n.partner is None
                              and (r.pair_faults(n) or ())))
    out["key"] = [out["open"], out["pairs"], out["islands"], out["uncoupled"],
                  out["contention"], out["vias"], out["length_mm"]]
    return out


def _one_proc(stem, budget_s):
    """Score in its own process: numba state, and a crash, stay per board."""
    p = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", stem,
                        "--budget", str(budget_s)], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"), cwd=HERE)
    line = (p.stdout.strip().splitlines() or ["null"])[-1]
    try:
        res = json.loads(line)
    except ValueError:
        res = {"error": (p.stderr or p.stdout)[-400:]}
    return dict(res or {"error": "no output"}, stem=stem)


def main(argv):
    jobs, budget, stems, one = max(1, (os.cpu_count() or 4) // 4), 900.0, [], False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--jobs":
            jobs = int(argv[i + 1]); i += 2; continue
        if a == "--budget":
            budget = float(argv[i + 1]); i += 2; continue
        if a == "--one":
            one = True; i += 1; continue
        stems.append(os.path.abspath(a[:-len(".kicad_pcb")] if a.endswith(".kicad_pcb") else a))
        i += 1
    if not stems:
        raise SystemExit(__doc__)
    if one:
        print(json.dumps(score(stems[0], budget)))
        return 0
    with ThreadPoolExecutor(jobs) as ex:
        res = list(ex.map(lambda s: _one_proc(s, budget), stems))
    for r in sorted(res, key=lambda r: r.get("key") or [math.inf]):
        print(json.dumps(r))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
