"""THE ROUTED CABLES' CACHE, as the build reads it -- fast, and never routing anything.

A cable that wants its real, taut path (tools/cable_route.py) asks for it here:

    pts = cable_routes.taut("bus B pedal cable", a, b, r, legacy=[...], gates=[...])

and gets the cached route when one was made for exactly these ends, this radius and
these gates, or `legacy` (its hand-drawn path) when not. A miss is NOT an error -- the
build must stay fast and must not depend on a route having been run -- but it is
REPORTED, once per build, with the command that fixes it:

    py -3.12 -m tools.route_cables            # route every stale cable
    py -3.12 -m tools.route_cables --check    # which routes' surroundings have changed

Every request is also recorded in REQUESTS, which is how the route tool knows what to
route: it draws the wires once, reads the requests, and solves them.

The cache is src/cable_routes.json, TRACKED, so every checkout builds the same cables.
A route is keyed by what it was solved for (ends, radius, gates); geometry moving round
it does not invalidate it on its own -- `--check` reports that, from the shared part
cache's hashes, and a route is re-run when the cut list needs to be right.
"""

from __future__ import annotations

import json
import math
import pathlib

CACHE = pathlib.Path(__file__).resolve().parent / "cable_routes.json"
TOL = 0.05                      # mm: an end this close is the same end

REQUESTS: dict = {}             # name -> {"a", "b", "r", "gates", "legacy"}
STALE: list = []                # names served their legacy path this build
_cache = None


def _load():
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            _cache = {}
    return _cache


def _same(p, q):
    return len(p) == len(q) and all(math.dist(u, v) <= TOL for u, v in zip(p, q))


def _key(a, b, r, gates):
    return {"a": [float(v) for v in a], "b": [float(v) for v in b], "r": float(r),
            "gates": [[[float(v) for v in c] for c in g] for g in gates]}


def matches(entry, a, b, r, gates):
    """Was `entry` solved for these ends, this radius and these gates?"""
    k = _key(a, b, r, gates)
    return (_same([entry["a"], entry["b"]], [k["a"], k["b"]])
            and abs(entry["r"] - k["r"]) <= 1e-6
            and len(entry["gates"]) == len(k["gates"])
            and all(_same(g, h) for g, h in zip(entry["gates"], k["gates"])))


def taut(name, a, b, r, legacy, gates=()):
    """The cable `name`'s centreline from a to b: its cached taut route, or `legacy`.

    a and b are where the cable is FREE to take its own line -- the end of each
    connector's straight lead, not the pin -- and `legacy` must run between the same two
    points. `r` is the clearance it keeps from every solid (its own radius and a little).
    """
    gates = [tuple(tuple(c) for c in g) for g in gates]
    REQUESTS[name] = dict(_key(a, b, r, gates), legacy=[list(map(float, p)) for p in legacy])
    e = _load().get(name)
    if e is not None and matches(e, a, b, r, gates):
        return [tuple(p) for p in e["pts"]]
    if name not in STALE:
        STALE.append(name)
    return [tuple(map(float, p)) for p in legacy]


def report():
    """One line for the build log: which cables are still on their hand-drawn paths."""
    if not STALE:
        return None
    return ("cable routes: %d of %d on their HAND-DRAWN path (no cached taut route for "
            "their current ends): %s -- py -3.12 -m tools.route_cables"
            % (len(STALE), len(REQUESTS), ", ".join(STALE)))


def save(entries):
    """Merge `entries` ({name: entry}) into the cache file, sorted, one route a block."""
    data = dict(_load())
    data.update(entries)
    CACHE.write_text(json.dumps(dict(sorted(data.items())), indent=1) + "\n", encoding="utf-8")
    global _cache
    _cache = data
