"""Where under each fret board's BAY can an M4 button head hang?

    py -3.12 -m tools._probe_m4_room

The head hangs M4_BUTTON_HEAD_H below the board's underside, O7.6. Put a head-sized
cylinder at each candidate (x, y) in the bay and intersect it with every part of the
build that is not the board, the deck or the screw itself -- the method rule, not a
distance to the trunk.
"""
import cadquery as cq

from cadkit.fasteners import M4_BUTTON_HEAD_D, M4_BUTTON_HEAD_H
from src import fret_light as FL
from src.build import collect_components

SKIP = ("fret_", "top_plate")
CLR = 0.20          # head to anything below it


def main():
    others = [(n, s) for n, s in collect_components()
              if not n.startswith(SKIP)]
    for panel in FL.BOARD_NAME:
        x0, _x1 = FL.board_span(panel)
        bx1 = FL.board_span(panel)[0] + 9.40 if panel == "mid" else x0 + 15.0
        print("\n%s bay x %.2f..%.2f" % (panel, x0, bx1))
        near = []
        for n, s in others:
            b = s.val().BoundingBox()
            if b.xmax > x0 - 5 and b.xmin < bx1 + 5 and b.zmax > FL.BOARD_BOT - 6:
                near.append((n, s))
        print("  %d parts nearby: %s" % (len(near), ", ".join(sorted(n for n, _ in near))[:300]))
        r = M4_BUTTON_HEAD_D / 2.0 + CLR
        h = M4_BUTTON_HEAD_H + CLR
        for x in (x0 + 4.50, x0 + 6.0):
            row = []
            for y in [v * 2.0 for v in range(-16, 17)]:
                head = (cq.Workplane("XY").circle(r).extrude(h)
                        .translate((x, y, FL.BOARD_BOT - h)))
                hit = 0.0
                for _n, s in near:
                    i = head.val().intersect(s.val())
                    if i.Solids():
                        hit += i.Volume()
                row.append("%+.0f:%s" % (y, "ok" if hit < 1e-3 else "X"))
            print("  x %.2f  %s" % (x, " ".join(row)))


if __name__ == "__main__":
    main()
