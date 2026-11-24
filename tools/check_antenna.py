"""THE ANTENNA'S MARGINS, GATED (lead, 2026-11-23) -- and the search that chose its home.

GATE (the build runs it with the components it just built; also standalone, on the lead's
cached build): the SC0480 dipole and its connector, where src/antenna.py puts them, must keep
  * >= METAL_MIN (15) from every non-plastic part -- steel, stainless, brass, aluminium, the
    motors' painted bodies (tools.web_materials.material_of);
  * >= COPPER_MIN (10) from every board;
  * (plastic is its mount -- the floor boss and the clip -- so plastic is reported, not gated;
    a drawn dipole named antenna* is skipped);
  * within the cable's reach of the CM5's U.FL.
Distances are EXACT (BRepExtrema) and only the parts whose boxes come within reach are
measured, so it costs about a second.

SEARCH (--search): the scan that found the spot -- every axis-aligned straight dipole inside the
body on a 6 mm grid, scored on clearance fields built from the cached model (~2 min, ~1 GB).
Run it again if the gate goes RED and the dipole has to move.

    py -3.12 -m tools.check_antenna            # the gate, on the cached build
    py -3.12 -m tools.check_antenna --search   # where else it could go
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
PLASTIC = {"nylon", "pctg", "pctg-black", "pctg-clear", "petg-gf", "pvc", "ink", "tpu"}


def _kind(name):
    from tools.web_materials import material_of
    try:
        m = material_of(name)
    except Exception:                       # noqa: BLE001 -- unknown material: treat as metal
        m = "?"
    return "board" if m == "board" else ("plastic" if m in PLASTIC else "metal")


def _dist(a, b):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    e = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    return e.Value() if e.IsDone() else float("inf")


def gate(parts, log=print) -> int:
    """`parts` is [(name, cq.Shape)]. Returns the number of broken margins (0 = green)."""
    from src import antenna as A
    ant = A.solids()
    reach = max(A.METAL_MIN, A.COPPER_MIN) + max(A.BASE_R, A.CONN_R) + 1.0
    lo = [min(p[k] for s in A.segments() for p in s[:2]) - reach for k in range(3)]
    hi = [max(p[k] for s in A.segments() for p in s[:2]) + reach for k in range(3)]
    worst = {"metal": (math.inf, None), "board": (math.inf, None), "plastic": (math.inf, None)}
    for name, s in parts:
        if name.startswith("antenna"):
            continue
        try:
            b = s.BoundingBox()
        except Exception:                   # noqa: BLE001
            continue
        if (b.xmax < lo[0] or b.xmin > hi[0] or b.ymax < lo[1] or b.ymin > hi[1]
                or b.zmax < lo[2] or b.zmin > hi[2]):
            continue
        k = _kind(name)
        d = min(_dist(a, s) for a in ant)
        if d < worst[k][0]:
            worst[k] = (d, name)
    bad = 0
    for k, need in (("metal", A.METAL_MIN), ("board", A.COPPER_MIN), ("plastic", None)):
        d, n = worst[k]
        if need is None:                    # plastic HOLDS it (the floor boss, the clip): report only
            log("  antenna: nearest plastic %6s mm (%s) -- its mount; not gated"
                % ("-" if n is None else "%.1f" % d, n or "nothing near"))
            continue
        ok = d >= need
        bad += not ok
        log("  antenna: nearest %-7s %6s mm (%s), needs >= %.0f%s"
            % (k, "-" if n is None else "%.1f" % d, n or "nothing near", need, "" if ok else "   <-- BROKEN"))
    back = [A.BASE[k] - A.AXIS[k] * A.CONN_L for k in range(3)]
    run = math.dist(back, A.UFL)
    if run > A.CABLE_L - 30.0:              # the cable cannot run straight: keep 30 for its path
        bad += 1
        log("  antenna: the SMA is %.0f mm from the U.FL in a straight line; the cable is %.0f  <-- BROKEN"
            % (run, A.CABLE_L))
    return bad


def _cached_parts():
    from cadkit import scratch as S
    cache = S.shared_cache(REPO)
    man = json.loads((cache / S.MANIFEST).read_text())
    out = []
    for n in man["parts"]:
        try:
            out.append((n, S.read_brep(cache / (n + ".brep"))))
        except Exception:                   # noqa: BLE001
            pass
    return out, man


def search(top=12):
    """Every axis-aligned straight dipole inside the body: the margins it keeps and its way out."""
    import numpy as np
    from src import antenna as A
    from tools.cable_route import Obstacles
    parts, man = _cached_parts()
    print("model: build #%s (%s)" % (man["build"], man["commit"][:8]))
    ufl = np.array(A.UFL)
    lo = np.array([ufl[0] - A.CABLE_L, -102.0, -112.0])
    hi = np.array([min(2.0, ufl[0] + A.CABLE_L), 77.0, -8.0])
    groups = {"metal": [], "board": [], "all": []}
    for n, s in parts:
        if n.startswith("antenna"):
            continue
        b = s.BoundingBox()
        if b.xmax < lo[0] - 30 or b.xmin > hi[0] + 30:
            continue
        groups["all"].append((n, s))
        k = _kind(n)
        if k != "plastic":
            groups[k].append((n, s))
    F = {k: Obstacles(v, (lo, hi), h=2.0, max_cells=3e6) for k, v in groups.items()}
    R, L, C = A.DIPOLE_R, A.DIPOLE_L, A.CONN_L
    res = []
    for c in itertools.product(*(np.arange(lo[k] + 4, hi[k] - 2, 6.0) for k in range(3))):
        c = np.array(c)
        if F["all"].clearance(c[None])[0] < R + 0.5:
            continue
        for ax, sg in itertools.product(range(3), (-1, 1)):
            u = np.zeros(3); u[ax] = sg
            pts = c + np.outer(np.linspace(0, L, 28), u)
            allp = np.vstack([pts, c - np.outer(np.linspace(0, C, 6), u)])
            if (allp[:, 2].max() > -10.0 or allp[:, 2].min() < -108.0 or allp[:, 0].max() > -21.0
                    or allp[:, 1].min() < -93.0 or allp[:, 1].max() > 67.0):
                continue                    # inside only (user: nothing pokes out)
            if F["all"].clearance(allp).min() - R < 0.5:
                continue
            metal = F["metal"].clearance(pts).min() - R
            board = F["board"].clearance(pts).min() - R
            run = np.linalg.norm(c - C * u - ufl)
            if metal < A.METAL_MIN or board < A.COPPER_MIN or run > A.CABLE_L - 30.0:
                continue
            res.append({"base": c.round(1).tolist(), "axis": "%s%s" % ("+-"[sg < 0], "XYZ"[ax]),
                        "metal": round(float(metal), 1), "board": round(float(board), 1),
                        "cable_run": round(float(run))})
    res.sort(key=lambda r: -r["metal"])
    print("%d placements keep %.0f from metal and %.0f from copper inside the body" % (len(res), A.METAL_MIN, A.COPPER_MIN))
    shown = []
    for r in res:
        if all(math.dist(r["base"], s["base"]) >= 40 for s in shown):
            shown.append(r)
            print("  ", r)
        if len(shown) >= top:
            break
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--search", action="store_true", help="scan for every placement that keeps the margins")
    a = ap.parse_args()
    if a.search:
        search()
        return 0
    parts, man = _cached_parts()
    print("model: build #%s (%s)" % (man["build"], man["commit"][:8]))
    n = gate(parts)
    print("ANTENNA GATE: %s" % ("green" if n == 0 else "RED -- %d margin(s) broken" % n))
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
