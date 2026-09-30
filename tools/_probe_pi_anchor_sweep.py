"""Where can the Pi's hold-down screw go, judged by what its ANCHOR hits BELOW the floor?

The current hold at (-515.50, -68.50) leaves under 1.6 mm of chassis between its bore and
`knee_housing` -- the levers' mortise/tenon -- which is the user's report and which the
overlap gate cannot see (a thin wall is not an interpenetration).

The user's spacer proposal is what makes this searchable at all: with a printed piece
spanning from the screw head to the board's edge, the screw NO LONGER HAS TO SIT BESIDE THE
BOARD. So sweep a wide region and score each candidate by:

  * foreign material within MIN_WALL of the anchor bore   (knee_housing etc. -- must be 0)
  * chassis material AROUND the bore                       (must be ~solid: it is the boss)
  * the column above the head                              (a driver has to reach it)

    py -3.12 -m tools._probe_pi_anchor_sweep
"""
import math

import cadquery as cq

from src.build import collect_components
from src import electronics as EL
from src import motor_bank as MB
from src import top_plate as TP
from cadkit.fasteners import M4

MIN_WALL = 1.6
KEY_D = 2.887                      # the 2.5 mm hex key, across corners


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    foreign = [(n, s) for n, s in comps
               if not n.startswith("chassis") and not n.startswith("board_screw")
               and not n.startswith("board_insert") and not n.startswith("wire_")
               and not n.startswith("pi5") and not n.startswith("pi_cap")]
    chassis = [(n, s) for n, s in comps if n.startswith("chassis")]
    z1 = EL.PI_Z
    z0 = z1 - M4.anchor_min_wall
    fp = EL.PI_FP
    print("sweeping the Pi's hold; anchor z %.2f..%.2f, FLOOR_TOP %.2f" % (z0, z1, MB.FLOOR_TOP))
    print("board x %.1f..%.1f  y %.1f..%.1f ; the spacer lets the screw sit away from it\n"
          % (fp[0], fp[1], fp[2], fp[3]))

    rows = []
    x = fp[0] + 6.0
    while x <= fp[1] - 6.0:
        for y in [fp[3] + 2.5 + 1.0 * k for k in range(4)]:      # HUG the edge: span 2.5..5.5
            bore = (cq.Workplane("XY")
                    .add(cq.Solid.makeCylinder(M4.insert_bore_d / 2.0 + MIN_WALL,
                                               z1 - z0, cq.Vector(x, y, z0))).val())
            bad = 0.0
            who = ""
            for n, s in foreign:
                try:
                    it = s.intersect(bore)
                    v = it.Volume() if it.Solids() else 0.0
                except Exception:
                    v = 0.0
                if v > 0.5:
                    bad += v
                    who = n if not who else who
            if bad > 0.5:
                continue
            # is there chassis to anchor INTO?
            host = 0.0
            for n, s in chassis:
                try:
                    it = s.intersect(bore)
                    host += it.Volume() if it.Solids() else 0.0
                except Exception:
                    pass
            # can a key reach the head?
            col = (cq.Workplane("XY")
                   .add(cq.Solid.makeCylinder(KEY_D / 2.0, 30.0,
                                              cq.Vector(x, y, z1 + 2.2))).val())
            blocked = 0.0
            for n, s in comps:
                if n.startswith("board_screw") or n.startswith("board_insert"):
                    continue
                try:
                    it = s.intersect(col)
                    blocked += it.Volume() if it.Solids() else 0.0
                except Exception:
                    pass
            span = y - fp[3]                     # how far the spacer must reach
            rows.append((round(span, 2), round(host, 1), round(blocked, 1), x, y))
        x += 2.0

    rows.sort()
    print("candidates with NOTHING foreign within %.1f mm of the bore: %d" % (MIN_WALL, len(rows)))
    print("  span = how far the spacer reaches from the board's +Y edge\n")
    for span, host, blocked, x, y in rows[:16]:
        print("   (%8.2f, %7.2f)  span %5.2f   chassis round the bore %7.1f mm3   "
              "driver column %s"
              % (x, y, span, host, "CLEAR" if blocked < 0.5 else "blocked %.1f" % blocked))


if __name__ == "__main__":
    main()
