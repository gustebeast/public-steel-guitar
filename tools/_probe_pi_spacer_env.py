"""Does the Pi spacer's ENVELOPE fit before it is built? (2026-09-29)

The site probe cleared a 1.6 mm shell around the ANCHOR. That is not the same question as
whether the PART fits: the spacer is a bar lying across the board's edge, and the box listing
from that probe turned up `motor_1` at z -68.35..-64.85 -- the exact band the spacer occupies.
A 24 mm box around a point cannot say whether that was under the part or merely nearby.

So intersect the spacer's actual envelope with the assembly, in two pieces, because the part
is STEPPED: over the board it rests on the laminate's top face, and outboard of the edge it
drops by one board thickness to sit on its boss at the board's underside. That step is not
decoration -- it is what lets one part touch both the board's top and a boss level with its
bottom, and it registers on the board's edge instead of guessing at a position.

    py -3.12 -m tools._probe_pi_spacer_env
"""
import cadquery as cq

from src.build import collect_components
from src import electronics as EL

SITE = (-510.0, -58.50)
T = 3 * 0.8              # 2.4 over the board -- D.BEAD * 3, the retention thickness
W = 16.0                 # along X: the run of edge it clamps
LAP = 6.0                # how far it reaches IN over the laminate
TAIL = 5.0               # how far it runs past the screw


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    y_edge = EL.PI_FP[3]                       # -71.0, the board's +Y edge
    z_board_top = EL.PI_Z + EL.BD_T            # -67.35
    z_top = z_board_top + T                    # -64.95
    z_boss = EL.PI_Z                           # -68.95, the outboard underside
    x0, x1 = SITE[0] - W / 2.0, SITE[0] + W / 2.0
    y_out = SITE[1] + TAIL
    print("spacer envelope   x %.2f..%.2f   top z %.2f" % (x0, x1, z_top))
    print("  lap   over the board : y %.2f..%.2f  z %.2f..%.2f  (rests on the laminate)"
          % (y_edge - LAP, y_edge, z_board_top, z_top))
    print("  shank outboard       : y %.2f..%.2f  z %.2f..%.2f  (steps down %.2f = BD_T)\n"
          % (y_edge, y_out, z_boss, z_top, EL.BD_T))

    lap = (cq.Workplane("XY").box(W, LAP, T)
           .translate((SITE[0], y_edge - LAP / 2.0, (z_board_top + z_top) / 2.0)).val())
    shank = (cq.Workplane("XY").box(W, y_out - y_edge, z_top - z_boss)
             .translate((SITE[0], (y_edge + y_out) / 2.0, (z_boss + z_top) / 2.0)).val())

    for label, env in (("lap", lap), ("shank", shank)):
        hits = []
        for n, s in comps:
            if n.startswith("board_screw") or n.startswith("board_insert"):
                continue
            try:
                it = s.intersect(env)
                v = it.Volume() if it.Solids() else 0.0
            except Exception:
                continue
            if v > 0.5:
                b = it.BoundingBox()
                hits.append((v, n, b))
        if not hits:
            print("%-6s CLEAR" % label)
        else:
            print("%-6s %d hit(s):" % (label, len(hits)))
            for v, n, b in sorted(hits, reverse=True):
                print("        %-20s %8.1f mm3   x %8.2f..%8.2f y %8.2f..%8.2f z %7.2f..%7.2f"
                      % (n, v, b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax))


if __name__ == "__main__":
    main()
