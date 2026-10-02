"""Where can a SECOND M4 stand at each fret board's far (+X) end, on the +Y side?

    py -3.12 -m tools._probe_m4_far

Puts the real volumes there -- the O9.2 boss from the deck down to the board's top, and
the button head under the board -- and intersects them with every part of the build.
"""
import cadquery as cq

from cadkit.fasteners import M4, M4_BUTTON_HEAD_D, M4_BUTTON_HEAD_H
from src import fret_light as FL
from src.build import collect_components

CAND = {"mid": [(x, y) for x in (-154.5, -160.0) for y in (40.5, 42.5, 44.4, 46.0)],
        "key": [(x, y) for x in (-367.0, -372.0) for y in (40.5, 42.5, 44.4, 46.0)]}


def main():
    parts = collect_components()
    for panel, cands in CAND.items():
        print("\n%s  board %.2f..%.2f" % ((panel,) + FL.board_span(panel)))
        for x, y in cands:
            boss = (cq.Workplane("XY").circle(M4.boss_od / 2.0).extrude(-FL.BOARD_TOP)
                    .translate((x, y, FL.BOARD_TOP))).val()
            head = (cq.Workplane("XY").circle(M4_BUTTON_HEAD_D / 2.0 + 0.2)
                    .extrude(M4_BUTTON_HEAD_H + 0.2)
                    .translate((x, y, FL.BOARD_BOT - M4_BUTTON_HEAD_H - 0.2))).val()
            ear = (cq.Workplane("XY").box(9.2, y + 4.6 - FL.BOARD_HALF_W, FL.BOARD_T)
                   .translate((x, (y + 4.6 + FL.BOARD_HALF_W) / 2.0,
                               FL.BOARD_BOT + FL.BOARD_T / 2.0))).val()
            hits = []
            for n, s in parts:
                b = s.val().BoundingBox()
                if b.xmax < x - 8 or b.xmin > x + 8 or b.ymax < y - 8 or b.ymin > y + 8:
                    continue
                for tag, v in (("boss", boss), ("head", head), ("ear", ear)):
                    i = v.intersect(s.val())
                    if i.Solids() and i.Volume() > 1e-3:
                        hits.append("%s/%s %.1f" % (tag, n, i.Volume()))
            print("  (%.2f, %.2f)  %s" % (x, y, "; ".join(hits) or "CLEAR"))


if __name__ == "__main__":
    main()
