"""What is UNDER the fret boards' long edges, where a retaining tab has to hang?

The tab reaches inward over the board's underside, and in the deck's print direction
(top_plate PIECE_UP = -Z) its retention face is a horizontal overhang -- so it wants a
45 degree underside, which makes it DEEPER than a flat tab by its own reach. This asks
how deep it may go before it is in the CAN harness or the tee boards.
"""
import cadquery as cq

from src import fret_light as FL
from src.build import collect_components

REACH = 2.30            # docs/fret-led.md section 8: tab reach over the board's edge
SKIP = ("fret_pcb", "fret_led", "top_plate")


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()
             if not n.startswith(SKIP)]
    print("board z %.2f..%.2f, half-width %.2f; cable top %.2f, tee top %.2f\n"
          % (FL.BOARD_BOT, FL.BOARD_TOP, FL.BOARD_HALF_W, FL.CABLE_TOP, FL.TEE_TOP))
    for panel in ("key", "mid"):
        x0, x1 = FL.board_span(panel)
        for sgn, side in ((-1.0, "-Y"), (1.0, "+Y")):
            ye = sgn * FL.BOARD_HALF_W
            y0, y1 = sorted((ye - sgn * REACH, ye + sgn * 2.0))
            z0, z1 = FL.BOARD_BOT - 6.0, FL.BOARD_BOT
            box = (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0)
                   .translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)).val())
            print("%s %s edge -- x %8.2f..%8.2f  y %6.2f..%6.2f  z %7.2f..%7.2f"
                  % (panel, side, x0, x1, y0, y1, z0, z1))
            hits = []
            for name, shp in comps:
                try:
                    inter = shp.intersect(box)
                    v = inter.Volume() if inter.Solids() else 0.0
                except Exception:
                    v = 0.0
                if v > 0.5:
                    hits.append((v, name, inter.BoundingBox()))
            for v, name, bb in sorted(hits, reverse=True)[:8]:
                print("     %-24s %9.1f mm3  y %7.2f..%7.2f z %7.2f..%7.2f  (top %.2f)"
                      % (name, v, bb.ymin, bb.ymax, bb.zmin, bb.zmax, bb.zmax))
            if not hits:
                print("     (clear for the full 6.00 mm)")
            print("")


if __name__ == "__main__":
    main()
