"""Re-check the Pi spacer's chosen anchor site AT THE Z THE SPACER ACTUALLY NEEDS.

The sweep that chose (-510.0, -58.5) bored from the board's UNDERSIDE (PI_Z, -68.95). The
spacer lies on the board's TOP face, so it has to be supported at that height at the screw
end too: the chassis needs a boss there topping out level with the board, and the bore then
starts at PI_Z + BD_T = -67.35. That is 1.6 mm HIGHER than what was swept, and `knee_housing`
was already the binding constraint at z -79.45..-73.25 -- so the bore moving up does not
automatically help, it moves the far end of the bore further INTO the housing's band.

⚠ The overlap gate cannot answer this. The failure mode is a THIN WALL, not an
interpenetration: two solids 0.2 mm apart interpenetrate by nothing.

    py -3.12 -m tools._probe_pi_spacer
"""
import cadquery as cq

from src.build import collect_components
from src import electronics as EL
from src import motor_bank as MB
from cadkit.fasteners import M4

MIN_WALL = 1.6
KEY_D = 2.887                       # the 2.5 mm hex key, across corners
SITE = (-510.0, -58.5)              # chosen by tools/_probe_pi_anchor_sweep
SPAN_TO = EL.PI_FP[3]               # the board edge the spacer reaches back to


def _vol(shape, cutter):
    try:
        it = shape.intersect(cutter)
        return it.Volume() if it.Solids() else 0.0
    except Exception:
        return 0.0


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    hx, hy = SITE
    z_top = EL.PI_Z + EL.BD_T                     # the boss tops out LEVEL WITH THE BOARD
    z_bot = z_top - M4.anchor_min_wall
    print("Pi spacer anchor re-check at (%.2f, %.2f)" % (hx, hy))
    print("  board underside PI_Z %.2f, laminate %.2f -> top face %.2f"
          % (EL.PI_Z, EL.BD_T, z_top))
    print("  bore z %.2f..%.2f   (the sweep used %.2f..%.2f -- %.2f mm LOWER)"
          % (z_bot, z_top, EL.PI_Z - M4.anchor_min_wall, EL.PI_Z, EL.BD_T))
    print("  FLOOR_TOP %.2f ; spacer spans %.2f mm from the board's +Y edge (%.2f)\n"
          % (MB.FLOOR_TOP, hy - SPAN_TO, SPAN_TO))

    shell_o = cq.Solid.makeCylinder(M4.insert_bore_d / 2.0 + MIN_WALL, z_top - z_bot,
                                    cq.Vector(hx, hy, z_bot))
    shell_i = cq.Solid.makeCylinder(M4.insert_bore_d / 2.0, z_top - z_bot,
                                    cq.Vector(hx, hy, z_bot))
    shell = shell_o.cut(shell_i)

    foreign, host = [], 0.0
    for n, s in comps:
        if n.startswith("board_screw") or n.startswith("board_insert"):
            continue
        v = _vol(s, shell)
        if v <= 0.5:
            continue
        if n.startswith("chassis"):
            host += v
        else:
            foreign.append((v, n))

    print("within %.1f mm of the bore: %.1f mm3 of chassis to anchor into" % (MIN_WALL, host))
    if foreign:
        for v, n in sorted(foreign, reverse=True):
            b = None
            try:
                b = s and None
            except Exception:
                pass
            print("  ⚠ FOREIGN %-20s %8.1f mm3 -- the 1.6 mm shell is not ours" % (n, v))
    else:
        print("  nothing foreign in the shell ✓")

    # name the z band of the nearest offender either way, so the next move is informed
    box = (cq.Workplane("XY").box(24.0, 24.0, 30.0)
           .translate((hx, hy, z_bot - 4.0)).val())
    print("\nparts in a 24 mm box below the site (z %.2f..%.2f):" % (z_bot - 19.0, z_bot + 11.0))
    for n, s in comps:
        if n.startswith("board_screw") or n.startswith("board_insert"):
            continue
        try:
            it = s.intersect(box)
            v = it.Volume() if it.Solids() else 0.0
        except Exception:
            continue
        if v > 0.5:
            bb = it.BoundingBox()
            print("   %-22s %8.1f mm3   z %7.2f..%7.2f" % (n, v, bb.zmin, bb.zmax))

    col = cq.Solid.makeCylinder(KEY_D / 2.0, 30.0, cq.Vector(hx, hy, z_top + 2.2))
    blocked = [(v, n) for v, n in
               ((_vol(s, col), n) for n, s in comps
                if not n.startswith("board_screw") and not n.startswith("board_insert"))
               if v > 0.5]
    print("\ndriver column above the head: %s"
          % ("CLEAR ✓" if not blocked else
             ", ".join("%s %.1f mm3" % (n, v) for v, n in sorted(blocked, reverse=True))))


if __name__ == "__main__":
    main()
