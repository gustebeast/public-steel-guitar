"""What is around the Pi hold-down's ANCHOR, below the floor? (user, 2026-09-29)

The user's report: the Pi's retention screw "doesn't have room since it needs to avoid
interfering with the mortise/tenon system for the levers and not create any sub 1.6mm
material down there", and proposes a printed spacer between the screw head and the PCB so
the screw can move to where there IS room.

⚠ THE OVERLAP GATE READS CLEAN HERE, so this is not a collision -- it is a THIN WALL, which
the gate cannot report by construction: two solids 0.2 mm apart interpenetrate by nothing.
This measures the gap from the anchor bore to everything around it, at several radii, so
"where is there room" becomes a number instead of a look at a render.

    py -3.12 -m tools._probe_pi_anchor
"""
import cadquery as cq

from src.build import collect_components
from src import electronics as EL
from src import motor_bank as MB
from cadkit.fasteners import M4

MIN_WALL = 1.6                     # D.MIN_WALL_2P, the bar the user named


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    hx, hy = EL.pi_hold_pt()
    z1 = EL.PI_Z
    z0 = z1 - M4.anchor_min_wall
    print("assembly %d solids" % len(comps))
    print("Pi anchor: axis (%.3f, %.3f), z %.3f..%.3f, bore O%.2f (insert) / O%.2f (tap)"
          % (hx, hy, z0, z1, M4.insert_bore_d, M4.selftap_d))
    print("FLOOR_TOP %.3f -- the anchor reaches %.2f mm below it\n"
          % (MB.FLOOR_TOP, MB.FLOOR_TOP - z0))

    # a shell around the bore: what sits within `t` of it?
    for t in (MIN_WALL, 2.0, 3.0, 5.0):
        outer = (cq.Workplane("XY")
                 .add(cq.Solid.makeCylinder(M4.insert_bore_d / 2.0 + t, z1 - z0,
                                            cq.Vector(hx, hy, z0))))
        inner = (cq.Workplane("XY")
                 .add(cq.Solid.makeCylinder(M4.insert_bore_d / 2.0, z1 - z0,
                                            cq.Vector(hx, hy, z0))))
        shell = outer.val().cut(inner.val())
        rows = []
        for name, shp in comps:
            if name.startswith("board_screw") or name.startswith("board_insert"):
                continue
            try:
                it = shp.intersect(shell)
                v = it.Volume() if it.Solids() else 0.0
            except Exception:
                v = 0.0
            if v > 0.5:
                rows.append((v, name))
        tot = shell.Volume()
        filled = sum(v for v, _ in rows)
        print("  within %.1f mm of the bore: %6.1f of %6.1f mm3 is solid (%.0f%%)   %s"
              % (t, filled, tot, 100.0 * filled / tot if tot else 0.0,
                 ", ".join("%s %.0f" % (n, v) for v, n in sorted(rows, reverse=True)[:3])))

    # and what are the NEAREST distinct parts below the floor near this point?
    print("\nparts near the anchor (20 mm box around it, below FLOOR_TOP):")
    box = (cq.Workplane("XY").box(20.0, 20.0, (z1 - z0) + 4.0)
           .translate((hx, hy, (z0 + z1) / 2.0)).val())
    for name, shp in comps:
        if name.startswith("board_screw") or name.startswith("board_insert"):
            continue
        try:
            it = shp.intersect(box)
            v = it.Volume() if it.Solids() else 0.0
        except Exception:
            v = 0.0
        if v > 0.5:
            b = it.BoundingBox()
            print("   %-22s %8.1f mm3   x %8.2f..%8.2f y %8.2f..%8.2f z %7.2f..%7.2f"
                  % (name, v, b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax))


if __name__ == "__main__":
    main()
