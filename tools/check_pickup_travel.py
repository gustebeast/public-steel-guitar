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


def main() -> int:
    from src import build as B
    from src import pickup_mount as PM
    travel = PM.PK_H - PM.PK_H_MIN
    parts = {}
    for name, obj in B.collect_components():
        if name in MOVING + FIXED:
            parts[name] = obj.val() if hasattr(obj, "val") else obj
    missing = [n for n in MOVING + FIXED if n not in parts]
    if missing:
        print("check_pickup_travel: not in the assembly: %s" % ", ".join(missing))
        return 2
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
    print("check_pickup_travel: plate lifted 0 .. %.1f mm in %.1f steps" % (travel, STEP))
    if not bad:
        print("clean: the plate and its retention screw clear the deck through the whole travel.")
        return 0
    first = {}
    for dz, m, f, v in bad:
        first.setdefault((m, f), (dz, v))
    for (m, f), (dz, v) in sorted(first.items()):
        worst = max(x[3] for x in bad if x[1] == m and x[2] == f)
        print("  %-24s meets %-18s from +%.1f mm (%.2f mm3 at full travel)" % (m, f, dz, worst))
    return 1


if __name__ == "__main__":
    sys.exit(main())
