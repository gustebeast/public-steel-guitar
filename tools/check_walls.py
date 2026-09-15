"""Sample the motor bank for material thinner than MIN_WALL_2P.

WHY A SAMPLER. The overlap gate compares parts, the bead checker reads constants; neither can
see a wall that came out thin from the INTERACTION of two cuts. Every sliver the user has found
by eye in FreeCAD was of that kind -- a cut meeting another cut's face, leaving a rib nobody
wrote. This walks lines through the FINISHED solid and reports contiguous runs of material
shorter than the rule, which is the only way to measure a wall that no constant describes.

    py -3.12 -m tools.check_walls            # every string
    py -3.12 -m tools.check_walls 5 9        # just those strings

Each probe line is INTERSECTED with the solid, so the material intervals come back exactly;
each bay is cropped out first, which keeps those booleans cheap. The whole bank runs in
seconds once src.build has imported (that import, not this check, is the wait).
"""
import sys
import time

import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common

from src import build as B
from src import dimensions as D
from src import motor_bank as MB
from src.helpers import box_at

THIN = D.MIN_WALL_2P - 1e-6


def _runs(sols, p0, d, span):
    """Contiguous material runs along a line: [(t_start, length)].

    ONE BOOLEAN PER LINE. This walked the line in 0.1 mm steps asking isInside at each --
    ~10k point classifications per string, a minute each, ten minutes for the bank, which is
    too slow to run after a change (user). Intersecting the LINE ITSELF with the solid returns
    the material intervals directly: exact rather than quantised to the step, and ~100x faster.
    """
    p1 = (p0[0] + d[0] * span, p0[1] + d[1] * span, p0[2] + d[2] * span)
    line = cq.Edge.makeLine(cq.Vector(*p0), cq.Vector(*p1)).wrapped
    out = []
    for s in sols:
        common = BRepAlgoAPI_Common(line, s.wrapped)
        if not common.IsDone():
            continue
        for e in cq.Shape.cast(common.Shape()).Edges():
            c, ln = e.Center(), e.Length()
            t = ((c.x - p0[0]) * d[0] + (c.y - p0[1]) * d[1] + (c.z - p0[2]) * d[2])
            out.append((t - ln / 2.0, ln))          # start, length -- as the point walk gave
    return out


def bank_samples(targets=None):
    """[(string, axis, x, y, z, length)] for every run thinner than the rule."""
    chs = cq.Workplane()
    for name, shape in B.body_work_components():
        if name.startswith("chassis"):
            chs = chs.add(shape)

    bad, t0 = [], time.time()
    for i in (targets if targets is not None else range(D.N_STRINGS)):
        bx0, bx1, by0, by1, bz0, _ = MB.body_box(i)
        x0, x1 = bx0 - MB.side_room(i, -1) - 3.0, bx1 + MB.side_room(i, 1) + 3.0
        y0, y1 = by0 - MB.BACK_T - 3.0, by1 + MB.PLATE_T + 1.0
        z0, z1 = bz0 - 1.0, MB.SEAT_TOP + 1.0
        sols = chs.intersect(box_at(x1 - x0, y1 - y0, z1 - z0, x=(x0 + x1) / 2,
                                    y=(y0 + y1) / 2, z=(z0 + z1) / 2)).solids().vals()

        # Lines at the heights and offsets where the bay's own features meet: floor, the drive
        # cut's ceiling, the seat plane and the seat walls; and either side of every motor face.
        zs = [bz0 + 1.0, bz0 + 6.0, bz0 + MB.BUMP_H - 0.4, bz0 + MB.BUMP_H + 1.0,
              MB.Z_HI - 8.0, MB.Z_HI - 3.0, MB.Z_HI - 0.4, MB.Z_HI + 1.0, MB.SEAT_TOP - 0.4]
        ys = [by0 - MB.BACK_T + 0.4, by0 - MB.BACK_T + 1.6, by0 - 0.8, by0 + 3.0,
              (by0 + by1) / 2, by1 - 3.0, by1 + 1.0, by1 + MB.PLATE_T - 0.4]
        xs = [bx0 - MB.side_room(i, -1) + 0.8, bx0 - 0.8, bx0 + 6.0, (bx0 + bx1) / 2,
              bx1 - 6.0, bx1 + 0.8, bx1 + MB.side_room(i, 1) - 0.8]
        def thin(runs, span):
            """Runs shorter than the rule, EXCLUDING any that touch an end of the probe line.
            Those are cut by the crop box, not by the design: the material carries on past the
            sample region and its true thickness is unknown from this line. Counting them read
            as 42 phantom 1.0 mm walls at the crop's own +Y face."""
            return [(t, ln) for t, ln in runs
                    if ln < THIN and t > 1e-6 and t + ln < span - 1e-6]

        for z in zs:
            for y in ys:
                _sp = x1 - x0
                for t, ln in thin(_runs(sols, (x0, y, z), (1, 0, 0), _sp), _sp):
                    bad.append((i + 1, "X", x0 + t + ln / 2, y, z, ln))
            for x in xs:
                _sp = y1 - y0
                for t, ln in thin(_runs(sols, (x, y0, z), (0, 1, 0), _sp), _sp):
                    bad.append((i + 1, "Y", x, y0 + t + ln / 2, z, ln))
        print(f"  ...string {i + 1} done ({time.time() - t0:.0f}s, {len(bad)} thin so far)",
              flush=True)
    return bad


def motor_seating(targets=None):
    """[(string, support_pct, lift_obstruction)] -- does each motor REST on something, and is
    its way out still clear?

    NOT measured with lift_prism. The chassis is cut BY that prism, so intersecting the two can
    only ever return zero -- a check that cannot fail is not a check, and it is how a cut that
    reached 100 mm below every motor and hollowed out the ribs they rest on got through (user
    caught it by eye, 2026-09-15). So: the support patch is probed UNDER the motor's own
    underside, and the lift path ABOVE its own top face. Both come from body_box, which knows
    nothing about any cut.
    """
    chs = cq.Workplane()
    for name, shape in B.body_work_components():
        if name.startswith("chassis"):
            chs = chs.add(shape)

    def vol(w):
        return w.val().Volume() if w.solids().size() else 0.0

    out = []
    for i in (targets if targets is not None else range(D.N_STRINGS)):
        bx0, bx1, by0, by1, bz0, bz1 = MB.body_box(i)
        w, l = bx1 - bx0, by1 - by0
        patch = box_at(w, l, 0.8, x=(bx0 + bx1) / 2, y=(by0 + by1) / 2, z=bz0 - 0.4)
        up = box_at(w + 2 * MB.MOTOR_CLR, l + 2 * MB.MOTOR_CLR, 300.0,
                    x=(bx0 + bx1) / 2, y=(by0 + by1) / 2, z=bz1 + 150.0)
        out.append((i + 1, vol(chs.intersect(patch)) / (0.8 * w * l) * 100.0,
                    vol(chs.intersect(up))))
    return out


def main():
    targets = [int(a) - 1 for a in sys.argv[1:]] or None
    seats = motor_seating(targets)
    print("motor seating (support under the motor / obstruction above it)")
    for st, sup, lift in seats:
        flag = "" if sup > 0.1 and lift < 0.01 else "   <-- FAULT"
        print(f"  string {st:2d}  resting on {sup:5.1f}% of its base   "
              f"lift path {lift:7.1f} mm3{flag}")
    faults = sum(1 for _, sup, lift in seats if sup <= 0.1 or lift >= 0.01)

    bad = bank_samples(targets)
    print(f"\ncheck_walls: {len(bad)} samples under {D.MIN_WALL_2P} in the motor bank")
    for b in sorted(bad, key=lambda r: (r[0], r[5])):
        print("  string %2d  %s-run at (%8.2f, %8.2f, %8.2f)  %.2f mm" % b)
    if not bad:
        print("clean: every line through every bay holds the two-bead rule.")
    return 1 if (bad or faults) else 0


if __name__ == "__main__":
    sys.exit(main())
