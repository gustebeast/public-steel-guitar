"""ownroute.py <stem>: route <stem>.kicad_pcb with pcbflow's own router (see ROUTER.md).

Drop-in for route.py in finish.py's chain (PCBFLOW_ROUTER=own): reads the placed board
layout.py wrote, routes it, and finishes it with route.post_route -- the same post-route
work freerouting's boards get (post-route parts, repairs, thermal spokes, refill, tidy,
canonical UUIDs), so the two routers are compared on equal terms.

Two interpreters, because the two halves need different things:
  --core   the routing: Python 3.12 + numba (re-run under `py -3.12` if this one lacks numba)
  --post   route.post_route: KiCad's Python (pcbnew)
Plain `ownroute.py <stem>` does both, each in whichever interpreter has what it needs."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_PY = os.environ.get("KICAD_PYTHON", "C:/Program Files/KiCad/10.0/bin/python.exe")


def core(stem):
    sys.path.insert(0, HERE)
    from router.model import Model
    from router.negotiate import Router
    from router import emit
    t0 = time.time()
    m = Model(stem)
    print("ownroute: grid %d x %d x %d at %.2f mm, %d nets (%.1f s)"
          % (m.L, m.ny, m.nx, m.pitch, len(m.net_id), time.time() - t0))
    pours = m.fills                  # the copper the pours really have, not their outlines
    r = Router(m)
    nets = r.build_nets(pours=pours)
    print("ownroute: %d net(s) to join (%d of them to their pours: %s)"
          % (len(nets), sum(n.plane for n in nets), ", ".join(sorted(pours)) or "none"))
    failed = r.run(budget_s=float(os.environ.get("OWNROUTE_BUDGET_S", "1800")))
    from router import congestion
    congestion.report(r)
    congestion.pair_dives(r)
    shutil.copyfile(stem + ".kicad_pcb", stem + ".unrouted.kicad_pcb")   # as route.py keeps it
    n = emit.write(m, [x for x in nets if not x.failed], stem + ".kicad_pcb")
    print("ownroute: wrote %d item(s); %d net(s) left open: %s (%.0f s)"
          % (n, len(failed), ", ".join(x.name for x in failed) or "none", time.time() - t0))


def post(stem):
    sys.path.insert(0, HERE)
    import pcbnew
    import route
    pcb = stem + ".kicad_pcb"
    notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    route.post_route(pcbnew.LoadBoard(pcb), stem, notes, pcb)


def _clean_env():
    """The other interpreter must not inherit this one's paths: under finish.py this runs in
    KiCad's Python, whose PYTHONUSERBASE (its 3rdparty folder) hid the user site and lost
    numba (first own-router finish run, 2026-11-08)."""
    env = dict(os.environ)
    for k in ("PYTHONHOME", "PYTHONPATH", "PYTHONNOUSERSITE", "PYTHONEXECUTABLE", "PYTHONUSERBASE"):
        env.pop(k, None)
    return env


def _has(mod):
    try:
        __import__(mod)
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    stem = os.path.abspath(sys.argv[1])
    me = os.path.abspath(__file__)
    if "--core" in sys.argv:
        core(stem)
    elif "--post" in sys.argv:
        post(stem)
    else:
        if _has("numba"):
            core(stem)
        elif subprocess.call(["py", "-3.12", me, stem, "--core"], env=_clean_env()):
            sys.exit("ownroute: routing failed")
        sys.stdout.flush()
        if _has("pcbnew"):
            post(stem)
        elif subprocess.call([KICAD_PY, me, stem, "--post"], env=_clean_env()):
            sys.exit("ownroute: post-route failed")
    # pcbnew's SWIG teardown can abort a clean exit (route.py has the story): leave directly
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
