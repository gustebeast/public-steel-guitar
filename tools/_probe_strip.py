"""Does the retainer strip actually retain, and does it clear everything it must?

⚠ THE TABS IT REPLACED FAILED THIS TEST AND NOBODY RAN IT. They were committed with the
notch at the SAME X as the tab, so at the board's design position every tab sat inside its
notch and the board lifted straight out -- and a solid intersection could never have shown
it, because the tab is BELOW the board and reads 0.00 either way. Retention is a PLAN-VIEW
overlap question. This asks it that way, and asks the clearances as solids.
"""
import cadquery as cq

from src import fret_light as FL
from src.build import collect_components

SKIP = ("fret_pcb", "fret_led", "fret_strip", "top_plate")


def main():
    print("strip thickness is per-edge and measured: -Y %.2f, +Y %.2f\n"
          % (FL.strip_t(-1.0), FL.strip_t(1.0)))

    strips = {n: s.val() for n, s in FL.strips()}

    # 1. RETENTION: the strip must lap the board in plan. Test by pushing the strip up
    #    into the board's own Z band and intersecting -- if it laps, it collides there.
    for panel in ("mid", "key"):
        board = FL.pcb(panel).val()
        bb = board.BoundingBox()
        for tag in ("ny", "py"):
            st = strips["fret_strip_%s_%s" % (panel, tag)]
            lifted = st.translate((0, 0, FL.BOARD_BOT - st.BoundingBox().zmin + 0.10))
            hit = lifted.intersect(board)
            v = hit.Volume() if hit.Solids() else 0.0
            lap = v / (FL.strip_t(-1.0 if tag == "ny" else 1.0) * (bb.xmax - bb.xmin)) \
                if v else 0.0
            print("  %-4s %-3s laps the board by %5.2f mm  %s"
                  % (panel, tag, lap, "OK" if lap >= 1.0 else "!! NOT RETAINED"))

    # 2. CLEARANCE: the strip must miss the comb, the LEDs and everything under the deck.
    allsol = None
    for s in strips.values():
        allsol = s if allsol is None else allsol.fuse(s)
    comb = None
    for panel in ("mid", "key"):
        xa, xb = FL.panel_range(panel)
        c = (FL.walls(min(xa, xb), max(xa, xb))
             .union(FL.ramps(min(xa, xb), max(xa, xb)))
             .union(FL.edge_walls(min(xa, xb), max(xa, xb)))
             .cut(FL.strip_groove(min(xa, xb), max(xa, xb))))
        comb = c.val() if comb is None else comb.fuse(c.val())
    h = allsol.intersect(comb)
    print("\n  strips vs the grooved comb   %8.2f mm3  %s"
          % (h.Volume() if h.Solids() else 0.0,
             "OK" if not h.Solids() or h.Volume() < 1.0 else "!! FOULS"))

    comps = [(n, wp.val()) for n, wp in collect_components() if not n.startswith(SKIP)]
    worst = []
    for name, shp in comps:
        try:
            i = allsol.intersect(shp)
            v = i.Volume() if i.Solids() else 0.0
        except Exception:
            v = 0.0
        if v > 0.5:
            worst.append((v, name))
    print("  strips vs the rest of the instrument:")
    for v, n in sorted(worst, reverse=True)[:8]:
        print("     !! %-26s %8.2f mm3" % (n, v))
    if not worst:
        print("     clear")


if __name__ == "__main__":
    main()
