"""Does every string's carriage reach its whole travel without touching anything?

    py -3.12 -m tools.check_carriage_travel

check_overlaps compares parts WHERE THEY ARE DRAWN, and the assembly is drawn as it is
assembled: every nut on the ceiling, every belt clamp where it is spliced (user,
2026-10-05). Everything below the ceiling is invisible to it. This is check_sweep's idea
for parts that slide: for each of the ten strings the MOVING SET is posed at STATIONS
stations from the ceiling to the floor and intersected with everything that is not it.

  moving   nut_i (the carriage), string_nut_i (the ball end under its ear), string_i
           (redrawn at each station: its rise changes with the anchor), and the four
           parts of belt_tensioner_*_i, carried BELT_PER_MM along the belt per mm of nut
           and turned with it -- src.build.clamp_location, the same placement the build
           draws and tools/clamp_range.py steps.
  fixed    every other component as drawn, the other nine strings' moving sets included
           (at the ceiling; clamp against clamp at EVERY pair of positions, and clamps
           against belts, are tools/clamp_range.py's job).

A contact counts when check_overlaps would count it: its own allow-list (`intended`) and
volume floor are used, and belts are left out as its default gate leaves them out.
Baseline is 0."""
from __future__ import annotations

import sys

STATIONS = 5        # ceiling, floor and three between
SKIP_BASE = {"belt", "belt_clamp"}


def _far(a, b):
    return (a.xmax < b.xmin or b.xmax < a.xmin or a.ymax < b.ymin or b.ymax < a.ymin
            or a.zmax < b.zmin or b.zmax < a.zmin)


def gate(comps, quiet=False) -> int:
    """Number of (moving, fixed) pairs that touch somewhere in a travel; 0 is clean.
    ``comps`` is [(name, solid)] -- src.build hands over the model it just built."""
    import cadquery as cq
    from src import build as B, dimensions as D, belt_tensioner as BTn
    from tools import check_overlaps as CO
    if CO.WIRE_OK is None:
        import src.wiring
        CO.WIRE_OK = src.wiring.WIRE_OK
    parts = {n: s for n, s in comps}
    fixed = [(n, s, s.BoundingBox()) for n, s in comps if CO.base(n) not in SKIP_BASE]
    clamp = [(n, w.val()) for n, w in BTn.clamp_components()]
    downs = [D.CARRIAGE_TRAVEL * k / (STATIONS - 1) for k in range(STATIONS)]
    bad = {}
    saved = dict(B.DEMO_POSE_DZ)
    try:
        for i in range(D.N_STRINGS):
            mine = {"nut_%d" % i, "string_nut_%d" % i, "string_%d" % i} | {
                "%s_%d" % (n, i) for n, _s in clamp}
            missing = [n for n in ("nut_%d" % i, "string_nut_%d" % i) if n not in parts]
            if missing:
                raise KeyError("not in the assembly: %s" % ", ".join(missing))
            for down in downs:
                moving = [(n, parts[n].translate((0.0, 0.0, -down)))
                          for n in ("nut_%d" % i, "string_nut_%d" % i)]
                if "string_%d" % i in parts:
                    B.DEMO_POSE_DZ[i] = -down
                    moving.append(("string_%d" % i, B._string_path(i, D.string_y(i)).val()))
                loc = B.clamp_location(i, down)
                moving += [("%s_%d" % (n, i), s.moved(loc)) for n, s in clamp]
                for mn, ms in moving:
                    mb = ms.BoundingBox()
                    for fn, fs, fb in fixed:
                        if fn in mine or _far(mb, fb) or CO.intended(mn, fn):
                            continue
                        try:
                            v = ms.intersect(fs).Volume()
                        except Exception:
                            v = 0.0
                        if v > CO.MIN_VOL:
                            w, d0 = bad.get((mn, fn), (0.0, down))
                            bad[(mn, fn)] = (max(w, v), min(d0, down))
            B.DEMO_POSE_DZ.pop(i, None)
    finally:
        B.DEMO_POSE_DZ.clear()
        B.DEMO_POSE_DZ.update(saved)
    if not quiet:
        print("check_carriage_travel: %d strings x %d stations, nut 0 .. %.2f mm below the "
              "ceiling" % (D.N_STRINGS, STATIONS, D.CARRIAGE_TRAVEL))
        if not bad:
            print("clean: every nut, ball end, string and belt clamp clears everything "
                  "through its whole travel.")
        for (m, f), (v, d0) in sorted(bad.items()):
            print("  %-28s meets %-26s from %.2f mm down (%.2f mm3 worst)" % (m, f, d0, v))
    return len(bad)


def main() -> int:
    from src import build as B
    comps = [(n, o.val() if hasattr(o, "val") else o) for n, o in B.collect_components()]
    try:
        return 1 if gate(comps) else 0
    except KeyError as e:
        print("check_carriage_travel: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
