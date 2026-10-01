"""The seam joint AS BUILT: intersect the build's own solids, per panel.

    py -3.12 -m tools._probe_seam

⚠ THIS PROBE HAS BEEN WRONG TWICE, AND BOTH TIMES FOR THE SAME REASON: it measured
something other than what gets built. First it measured the wrong SIDE of key's end wall
(a distance to a face, not an intersection), then it called `FL.walls()` with no range and
met a wall top_plate never builds. So it now builds the comb exactly the way
top_plate._piece does -- per panel, clamped, grooved, notched -- and intersects the
plungers and the boards' own routed bodies (which carry the pogo barrels) against it.
Nothing here is a copy of a number: every solid comes from src/fret_light.py.
"""
from src import fret_light as FL


def _v(a, b):
    h = a.val().intersect(b.val())
    return (h.Volume() if h.Solids() else 0.0), (h.BoundingBox() if h.Solids() else None)


def comb(panel):
    """top_plate's comb for this panel, built the way top_plate builds it."""
    xb, xa = FL.panel_range(panel)
    c = (FL.walls(xb, xa).union(FL.ramps(xb, xa))
         .union(FL.edge_walls(xb, xa)))
    notch = FL.pogo_notches(xb, xa)
    return c.cut(notch) if notch.vals() else c


def main():
    ps = FL.pogo_set()
    print("flush separation %.2f   setbacks mid %.2f key %.2f   contact x %.3f"
          % (FL.pogo_sep_flush(), ps["mid"], ps["key"], FL._pogo_contact()))
    m, k = FL.pogo_pads("mid")[0][0], FL.pogo_pads("key")[0][0]
    work = (m - k) / 2.0 + FL.POGO_BODY_L / 2.0
    print("working height as modelled %.3f (at flush %.3f, limit %.2f, free %.2f)"
          % (work, FL.POGO_WORK, FL.POGO_LIMIT, FL.POGO_FREE))

    pins = FL.pogo_pins()[0][1]
    combs = {p: comb(p) for p in FL.BOARD_NAME}
    print("\nINTERSECTIONS, mm3 (every one should be 0):")
    worst = 0.0
    for p in FL.BOARD_NAME:
        for tag, a, b in (("plungers vs %s comb" % p, pins, combs[p]),
                          ("%s board+barrels vs %s comb" % (p, p), FL.pcb(p), combs[p]),
                          ("plungers vs %s LEDs" % p, pins, FL.leds(p))):
            v, bb = _v(a, b)
            worst = max(worst, v)
            print("  %-34s %8.3f   %s" % (tag, v, "x %.2f..%.2f z %.2f..%.2f"
                                           % (bb.xmin, bb.xmax, bb.zmin, bb.zmax)
                                           if bb else "clear"))
    # the plungers against the boards: they must clear the laminate they fly over
    for p in FL.BOARD_NAME:
        v, _bb = _v(pins, FL.pcb(p))
        worst = max(worst, v)
        print("  %-34s %8.3f" % ("plungers vs %s board (not barrels)" % p, v))
    print("\n%s" % ("CLEAR" if worst < 1e-3 else "!! NOT CLEAR -- worst %.3f mm3" % worst))


if __name__ == "__main__":
    main()
