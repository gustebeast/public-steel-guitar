"""The Pi spacer's FINAL bar: how long, and centred where? (2026-09-29)

Two findings from the LAP x W sweep changed the question, and both were invisible in the
summary line "biggest clear clamp: lap 3.0 x W 32":

  1. W 32 centred on the screw runs to x -494, and the board's +X edge is -503. Nine
     millimetres of that bar laps AIR -- and that edge is `open_edge`, the I/O end the board
     slides out of, so overhanging it is worse than useless. Clamp only counts over laminate.
  2. Every TAIL hit chassis_2 at W 24 (50.9 mm3) where W 16 hit only 23.0, so the wall that
     limits the tail is off to one side in X, not straight ahead. A wider bar does not just
     cost more at the far end; it changes which obstacle binds.

So the bar does not have to be centred on its screw. Sweep (centre, W) pairs over the WHOLE
stepped part -- lap and shank as one solid, which is what will actually exist -- and report
where the material that stops it lives.

    py -3.12 -m tools._probe_pi_spacer_bar
"""
import cadquery as cq

from src.build import collect_components
from src import electronics as EL

SITE = (-510.0, -58.50)
T, LAP, TAIL = 2.4, 2.5, 4.0
HEAD_R = 3.8                        # M4 button head
CANDS = ((-510.0, 14.0), (-512.0, 18.0), (-514.0, 20.0), (-516.0, 24.0), (-513.0, 22.0))


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    hx, hy = SITE
    y_edge = EL.PI_FP[3]
    x_board = EL.PI_FP[1]                       # -503, the board's +X (open) edge
    z0, z_top = EL.PI_Z, EL.PI_Z + EL.BD_T + T
    y_out = hy + TAIL
    print("board +X edge %.2f ; screw x %.2f ; head needs +-%.2f\n" % (x_board, hx, HEAD_R))

    for cx, w in CANDS:
        x0, x1 = cx - w / 2.0, cx + w / 2.0
        lap = (cq.Workplane("XY").box(w, LAP, T)
               .translate((cx, y_edge - LAP / 2.0, EL.PI_Z + EL.BD_T + T / 2.0)))
        shank = (cq.Workplane("XY").box(w, y_out - y_edge, z_top - z0)
                 .translate((cx, (y_edge + y_out) / 2.0, (z0 + z_top) / 2.0)))
        bar = lap.union(shank).val()
        hits = []
        for n, s in comps:
            if (n.startswith("board_screw") or n.startswith("board_insert")
                    or n == "pi_spacer"):
                continue        # ⚠ pi_spacer is IN the assembly now: it would find ITSELF
            try:
                it = s.intersect(bar)
                v = it.Volume() if it.Solids() else 0.0
            except Exception:
                continue
            if v > 0.5:
                hits.append((round(v, 1), n, it.BoundingBox()))
        over = max(0.0, min(x1, x_board) - x0)          # bar length actually over laminate
        note = []
        if x1 > x_board:
            note.append("%.1f past the board edge" % (x1 - x_board))
        if hx + HEAD_R > x1 or hx - HEAD_R < x0:
            note.append("HEAD OVERHANGS")
        print("centre %8.2f  W %5.1f  x %8.2f..%8.2f  clamp %5.1f mm2 over laminate  %s"
              % (cx, w, x0, x1, over * LAP, "; ".join(note) if note else ""))
        if not hits:
            print("      CLEAR")
        for v, n, b in sorted(hits, reverse=True):
            print("      %-18s %7.1f mm3  x %8.2f..%8.2f y %8.2f..%8.2f z %7.2f..%7.2f"
                  % (n, v, b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax))


if __name__ == "__main__":
    main()
