"""ownroute.py <stem>: route <stem>.kicad_pcb with pcbflow's own router (see ROUTER.md).

Drop-in for route.py in finish.py's chain (the default; PCBFLOW_ROUTER=freerouting for route.py): reads the placed board
layout.py wrote, routes it, and finishes it with route.post_route -- the same post-route
work freerouting's boards get (post-route parts, repairs, thermal spokes, refill, tidy,
canonical UUIDs), so the two routers are compared on equal terms.

Two interpreters, because the two halves need different things:
  --core   the routing: Python 3.12 + numba (re-run under `py -3.12` if this one lacks numba)
  --post   route.post_route: KiCad's Python (pcbnew)
Plain `ownroute.py <stem>` does both, each in whichever interpreter has what it needs."""
from __future__ import annotations

import _nowindow  # noqa: F401  (no console windows on Windows: _nowindow.py)
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
    wins = getattr(r, "fallback_wins", [])
    with open(stem + ".fallback.json", "w", encoding="utf-8") as fh:
        json.dump(wins, fh)


def freeze_fallbacks(stem):
    """The pairs whose fallback copper beat their lay (router/coupled.py, _fallback_pairs)
    go back to that copper: its tracks and vias into notes, the nets frozen, the pair's
    spec out of diff_pairs -- the board.json the pair had before it was declared coupled.
    Returns the pairs frozen.

    ⚠ A SECOND LAYOUT AND ROUTE, NOT A SPLICE (output_panel THRU, 2026-11-10): laid into
    the finished board, the fallback met GND stitch vias layout had placed where the
    lifted copper used to run, and re-negotiating round it left 57 nets open. Laid out
    with the copper in place, the board is the one the copper was drawn for."""
    path = stem + ".fallback.json"
    if not os.path.isfile(path):
        return []
    wins = json.load(open(path, encoding="utf-8"))
    os.remove(path)
    if not wins:
        return []
    bj = stem + ".board.json"
    notes = json.load(open(bj, encoding="utf-8"))
    keep, done = [], []
    for spec in notes.get("diff_pairs", ()):
        if list(spec.get("nets", ())) in wins and spec.get("fallback"):
            fb = spec["fallback"]
            notes["tracks"] = list(notes.get("tracks", ())) + list(fb.get("tracks", ()))
            notes["vias"] = list(notes.get("vias", ())) + list(fb.get("vias", ()))
            notes["frozen_nets"] = list(notes.get("frozen_nets", ())) + list(spec["nets"])
            done.append(spec["nets"])
        else:
            keep.append(spec)
    notes["diff_pairs"] = keep
    notes["fallback_frozen"] = list(notes.get("fallback_frozen", ())) + done
    with open(bj, "w", encoding="utf-8") as fh:
        json.dump(notes, fh, indent=2)
    return done


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
        for attempt in (1, 2):
            if _has("numba"):
                core(stem)
            elif subprocess.call(["py", "-3.12", me, stem, "--core"], env=_clean_env()):
                sys.exit("ownroute: routing failed")
            sys.stdout.flush()
            frozen = freeze_fallbacks(stem) if attempt == 1 else []
            if not frozen:
                break
            print("ownroute: %s laid worse than the copper they had -- frozen to it; layout and "
                  "route again" % ", ".join("/".join(f) for f in frozen))
            sys.stdout.flush()
            if subprocess.call([KICAD_PY, os.path.join(HERE, "layout.py"), stem], env=_clean_env()):
                sys.exit("ownroute: layout (fallback pass) failed")
        if _has("pcbnew"):
            post(stem)
        elif subprocess.call([KICAD_PY, me, stem, "--post"], env=_clean_env()):
            sys.exit("ownroute: post-route failed")
    # pcbnew's SWIG teardown can abort a clean exit (route.py has the story): leave directly
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
