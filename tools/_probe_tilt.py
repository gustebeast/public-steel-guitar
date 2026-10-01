"""Can each fret board actually be TILTED IN under its lip? Sweep the stroke.

    py -3.12 -m tools._probe_tilt

The board goes in with its +Y edge low, hooks its -Y edge over the lip's ramp, and swings
up flat. A part collides along its INSTALL STROKE, not at rest (the THT-tail rule), so
this poses the whole board -- laminate, every routed body, the LEDs and its seam plungers
-- at a run of tilt angles and intersects it with the panel's comb built the way
top_plate builds it (walls, ramps, edge walls + lip, groove, notches, M4 boss).

At each angle the board is free to sit anywhere the hand would put it, so the probe
searches a small grid of offsets (dy inboard, dz down) and reports the best. A path
exists if every angle has a clear pose; the seated pose (0 degrees, no offset) must be
clear on its own.
"""
import cadquery as cq

from src import fret_light as FL

ANGLES = (15.0, 10.0, 7.0, 5.0, 3.0, 2.0, 1.0, 0.5, 0.0)
DYS = (0.0, 0.2, 0.4, 0.6, 0.9, 1.3, 1.8, 2.4)
DZS = (0.0, -0.3, -0.8, -1.5)


def comb(panel):
    xb, xa = FL.panel_range(panel)
    c = (FL.walls(xb, xa).union(FL.ramps(xb, xa))
         .union(FL.edge_walls(xb, xa)).cut(FL.strip_groove(xb, xa)))
    notch = FL.pogo_notches(xb, xa)
    if notch.vals():
        c = c.cut(notch)
    return FL.m4_boss(c, xb, xa)


def body(panel):
    parts = [FL.pcb(panel).val(), FL.leds(panel).val(), FL.pogo_pins(panel)[0][1].val()]
    return cq.Compound.makeCompound(parts)


def hit(b, c):
    h = b.intersect(c)
    return h.Volume() if h.Solids() else 0.0


def main():
    s = FL.HINGE_SGN
    yh, zh = s * FL.BOARD_HALF_W, FL.BOARD_TOP          # the hinge edge's top corner, seated
    ok_all = True
    for panel in FL.BOARD_NAME:
        c = comb(panel).val()
        b0 = body(panel)
        print("\n%s -- hinge edge y %.2f, lip reach %.2f" % (panel, yh, FL.lip_reach()))
        for a in ANGLES:
            # +Y edge DOWN about the hinge corner: a negative turn about +X for a -Y hinge
            rot = b0.rotate(cq.Vector(0, yh, zh), cq.Vector(1, yh, zh), s * a)
            best = None
            for dz in DZS:
                for dy in DYS:
                    v = hit(rot.translate(cq.Vector(0, -s * dy, dz)), c)
                    if best is None or v < best[0]:
                        best = (v, dy, dz)
                    if v < 1e-3:
                        break
                if best[0] < 1e-3:
                    break
                if a == 0.0:
                    break
            ok = best[0] < 1e-3
            ok_all = ok_all and ok
            print("  %5.1f deg   %s   dy %.1f dz %+.1f   %8.3f mm3"
                  % (a, "clear" if ok else "HITS ", best[1], best[2], best[0]))
    print("\n%s" % ("A CLEAR POSE AT EVERY ANGLE" if ok_all else "!! THE STROKE IS BLOCKED"))


if __name__ == "__main__":
    main()
