"""The foot slot's -X mouth and string 1's faceplate wall, read off the FINISHED chassis.

    py -3.12 -m tools._probe_foot_mouth
"""
import cadquery as cq
from src import foot_light as F
from src import motor_bank as MB
from src.build import collect_components


def main():
    comps = dict((n, wp.val()) for n, wp in collect_components())
    ch = comps["chassis_2"]
    b = ch.BoundingBox()
    floor = F.window()[4]
    led, bb, bt, _lf, lt = F.z_stack()
    print("chassis_2 x %.2f..%.2f   window -X end %.2f   slot cut from %.2f"
          % (b.xmin, b.xmax, F.window()[0], F.window()[0] - F.MOUTH_CUT))
    for tag, z in (("mid-slot (floor + 3.0)", floor + 3.0), ("just under the floor's top (floor - 0.5)", floor - 0.5),
                   ("above the roof (floor + 12)", floor + 12.0)):
        X0 = F.window()[0] - 22.0
        print()
        print("plan at %s, z %.2f -- x from %.1f in 0.5 steps, y top = 57" % (tag, z, X0))
        for yi in range(57, 26, -1):
            y = yi - 0.5
            row = "".join("#" if ch.isInside(cq.Vector(X0 + 0.25 + 0.5 * k, y, z)) else "."
                          for k in range(60))
            print("  y %5.1f  %s" % (y, row))
    # condition 2: the 1.60 against the motor, the wall's whole length, floor to the board's top
    mx = MB.D.motor_pos(0)[0]
    x0w, x1w = mx - MB.SEAT_HALF_W, mx + MB.D.MOTOR_SQ / 2 + MB.MOTOR_CLR + MB.POST_T
    gaps = []
    n = 0
    for k in range(int((x1w - x0w) / 0.25)):
        x = x0w + 0.125 + 0.25 * k
        for y in (F.MOTOR_FACE + 0.2, F.MOTOR_FACE + 0.8, F.MOTOR_FACE + 1.4):
            for z in (floor + 0.2, floor + 2.0, floor + 4.0, bt - 0.2):
                n += 1
                if not ch.isInside(cq.Vector(x, y, z)):
                    gaps.append((round(x, 2), round(y, 2), round(z, 2)))
    print("\nthe 1.60 against the motor, x %.2f..%.2f, floor to board top: %d samples, %d NOT material"
          % (x0w, x1w, n, len(gaps)))
    for g in gaps[:12]:
        print("   air at", g)
    # condition 1: the motor-side face is one plane -- nothing of the chassis -Y of it in the lift path
    # condition 3: above the roof line the wall is whole
    miss = 0
    tot = 0
    for k in range(int((x1w - x0w) / 0.5)):
        x = x0w + 0.25 + 0.5 * k
        if abs(x - mx) < (MB.D.NEMA17_PILOT_D / 2 + MB.BOSS_CLR + 0.3):
            continue                                   # the boss's own drop-in slot
        for y in (F.MOTOR_FACE + 0.5, F.MOTOR_FACE + 3.0, F.MOTOR_FACE + 5.9):
            z = bt + (y - F._slot_y()[0]) + 0.6 if y > F._slot_y()[0] else bt + 0.6
            z = max(z, bt + 0.6)
            tot += 1
            if not ch.isInside(cq.Vector(x, y, z)):
                miss += 1
    print("just above the roof line, clear of the boss slot: %d samples, %d NOT material" % (tot, miss))


if __name__ == "__main__":
    main()
