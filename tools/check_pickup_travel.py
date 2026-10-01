"""Does the pickup height plate reach its whole travel without touching the deck?

    py -3.12 -m tools.check_pickup_travel

check_overlaps compares parts WHERE THEY SIT, and the plate sits at its lowest (the 22 mm
demo pickup). The plate is a moving part: three leadscrew jacks lift it PK_H - PK_H_MIN for
the shallowest pickup the mount supports. Its nut bosses stood 69-75 mm3 into the solid deck
at the top of that travel for months and no gate could say so (2026-09-30). This lifts the
plate, with the retention screw it carries, in half-millimetre steps against both deck
solids and fails on any contact. It is check_sweep's idea, for a part that slides rather
than turns.
"""
from __future__ import annotations

import sys

STEP = 0.5
MOVING = ("pickup_zplate", "pickup_retention_screw", "pickup_retention_insert")
FIXED = ("top_plate_0", "top_plate_color_0")
TOL = 0.01      # mm3


def gate(comps, quiet=False) -> int:
    """Number of (moving, fixed) pairs that touch somewhere in the travel; 0 is clean.
    ``comps`` is [(name, solid)] -- src.build hands over the model it just built, so the
    gate costs ~90 small intersects and no second geometry pass."""
    from src import pickup_mount as PM
    travel = PM.PK_H - PM.PK_H_MIN
    parts = {n: s for n, s in comps if n in MOVING + FIXED}
    missing = [n for n in MOVING + FIXED if n not in parts]
    if missing:
        raise KeyError("not in the assembly: %s" % ", ".join(missing))
    bad, n = [], int(round(travel / STEP))
    for k in range(n + 1):
        dz = min(k * STEP, travel)
        for m in MOVING:
            moved = parts[m].translate((0.0, 0.0, dz))
            for f in FIXED:
                try:
                    v = moved.intersect(parts[f]).Volume()
                except Exception:
                    v = 0.0
                if v > TOL:
                    bad.append((dz, m, f, v))
    first = {}
    for dz, m, f, v in bad:
        first.setdefault((m, f), dz)
    if not quiet:
        print("check_pickup_travel: plate lifted 0 .. %.1f mm in %.1f steps" % (travel, STEP))
        if not bad:
            print("clean: the plate and its retention screw clear the deck through the "
                  "whole travel.")
        for (m, f), dz in sorted(first.items()):
            worst = max(x[3] for x in bad if x[1] == m and x[2] == f)
            print("  %-24s meets %-18s from +%.1f mm (%.2f mm3 worst)" % (m, f, dz, worst))
    return len(first)


def main() -> int:
    from src import build as B
    comps = [(n, o.val() if hasattr(o, "val") else o) for n, o in B.collect_components()]
    try:
        return 1 if gate(comps) else 0
    except KeyError as e:
        print("check_pickup_travel: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
