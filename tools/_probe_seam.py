"""Put the pogo where it would go and intersect it.

⚠ THIS REPLACES A VERSION THAT MEASURED THE WRONG SIDE OF THE WALL. It computed key's
clear board top between the wall's OUTER face and the board edge -- 0.80 of overhang, so
negative -- and concluded key needed its comb wall moved 5.30 mm, which would have cost
fret 9. The body does not go there. It goes INBOARD of the wall, where the whole board is.
Distances to walls are a derivation; this intersects solids, which is the rule bronner's
method note gives and which this project has now got wrong three times.

C5203987 (YZF0002-38080-02), read off Xinyangze's drawing 2026-09-30:
    8.00 free, 6.00 working height, 5.70 compression limit
    barrel 4.50 long, 3.00 wide x 3.80 tall, bore centred at 1.90
    plunger O2.00, R0.50 dome, so it protrudes 1.50 beyond the barrel at working height
"""
import cadquery as cq

from src import fret_light as FL
from src.helpers import box_at

BODY_L, BODY_W, BODY_H = 4.50, 3.00, 3.80
AXIS_Z = 1.90
PLUNGER_D = 2.00
WORK = 6.00
LANE_Y = (-27.35 + -13.45) / 2.0     # a clear lane between two LED rows
N_POGO = 4
PITCH_Y = 3.40


def pogo(x_tip, sgn, y):
    """One pogo at working height: barrel + plunger, tip at x_tip, firing `sgn`."""
    z0 = FL.BOARD_TOP
    front = x_tip - sgn * (WORK - BODY_L)          # barrel's front face
    back = front - sgn * BODY_L
    body = box_at(BODY_L, BODY_W, BODY_H, x=(front + back) / 2.0, y=y,
                  z=z0 + BODY_H / 2.0)
    pl = (cq.Workplane("YZ").circle(PLUNGER_D / 2.0)
          .extrude(WORK - BODY_L)
          .translate((min(front, x_tip), y, z0 + AXIS_Z)))
    return body.union(pl), back, front


def main():
    k0, k1 = FL.board_span("key")
    m0, m1 = FL.board_span("mid")
    contact = (k1 + m0) / 2.0
    print("key board %.2f..%.2f   mid board %.2f..%.2f   gap %.2f, contact at %.2f"
          % (k0, k1, m0, m1, m0 - k1, contact))

    ys = [LANE_Y + (i - (N_POGO - 1) / 2.0) * PITCH_Y for i in range(N_POGO)]
    parts, out = {}, None
    for tag, sgn in (("mid", -1.0), ("key", +1.0)):
        for i, y in enumerate(ys):
            p, back, front = pogo(contact, sgn, y)
            if i == 0:
                print("  %s pogo: barrel %.2f..%.2f, plunger to %.2f  (setback from its "
                      "board edge %.2f)"
                      % (tag, back, front, contact,
                         abs(back - (k1 if tag == "key" else m0))))
            parts["%s%d" % (tag, i)] = p
            out = p if out is None else out.union(p)

    comb = FL.walls().union(FL.ramps())
    print("\nINTERSECTIONS (mm3):")
    hit = out.val().intersect(comb.val())
    v = hit.Volume() if hit.Solids() else 0.0
    b = hit.BoundingBox() if hit.Solids() else None
    print("  pogos vs comb+ramps   %8.2f   %s"
          % (v, "x %.2f..%.2f" % (b.xmin, b.xmax) if b else "clear"))

    for panel in ("key", "mid"):
        leds = FL.leds(panel).val()
        h = out.val().intersect(leds)
        print("  pogos vs %s LEDs      %8.2f" % (panel, h.Volume() if h.Solids() else 0.0))
        pcb = FL.pcb(panel).val()
        h = out.val().intersect(pcb)
        print("  pogos vs %s board     %8.2f" % (panel, h.Volume() if h.Solids() else 0.0))

    # what the wall actually has to give up: the plungers crossing key's end wall
    print("\nthe notch, if any: the intersection above is what must be cut from the comb.")


if __name__ == "__main__":
    main()
