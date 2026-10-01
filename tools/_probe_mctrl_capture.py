"""Could the TOP PANEL retain the motor board instead of its M4? (user, 2026-09-29)

The proposal: pack material under the board so its top edge sits just below the panel, and
let the panel capture it in Z when it goes on -- no screw at all. That would delete the M4
boss, which is also the part the user found printing as an overhang (it is a horizontal
cylinder once stand() has posed it, and the chassis prints Z-up).

What this measures, because the idea lives or dies on them:
  1. the board's world Z extent -- where its top edge actually is
  2. what is ABOVE it, and at what z its underside sits (the candidate captor)
  3. the gap, i.e. how far the board would have to rise
  4. what is BELOW it, since the board currently passes THROUGH the floor and the frame's
     side walls root in the slab -- lifting it may pull it out of its own root

    py -3.12 -m tools._probe_mctrl_capture
"""
import cadquery as cq

from src.build import collect_components
from src import electronics as EL
from src import motor_bank as MB


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    d = dict(comps)
    mc = d.get("motor_ctrl")
    if mc is None:
        print("motor_ctrl not in the assembly")
        return
    bb = mc.BoundingBox()
    print("motor_ctrl world  x %8.2f..%8.2f  y %8.2f..%8.2f  z %8.2f..%8.2f"
          % (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
    print("FLOOR_TOP %.3f  -> the board reaches %.2f BELOW the floor top"
          % (MB.FLOOR_TOP, MB.FLOOR_TOP - bb.zmin))

    # a column straight up from the board's own footprint: what could capture it?
    col = (cq.Workplane("XY")
           .box(bb.xmax - bb.xmin, bb.ymax - bb.ymin, 120.0)
           .translate(((bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0,
                       bb.zmax + 60.0)).val())
    print("\nwhat is ABOVE the board (its own footprint, 120 mm up):")
    hits = []
    for name, shp in comps:
        if name in ("motor_ctrl",) or name.startswith("wire_"):
            continue
        try:
            it = shp.intersect(col)
            v = it.Volume() if it.Solids() else 0.0
        except Exception:
            v = 0.0
        if v > 0.5:
            b = it.BoundingBox()
            hits.append((b.zmin, v, name, b))
    for z0, v, name, b in sorted(hits)[:10]:
        print("   %-22s underside z %8.2f   gap above the board %7.2f   %8.1f mm3"
              % (name, z0, z0 - bb.zmax, v))
    if not hits:
        print("   NOTHING -- the board's footprint is open to the sky")

    print("\nwhat is BELOW the board (what it is rooted in):")
    below = (cq.Workplane("XY")
             .box(bb.xmax - bb.xmin, bb.ymax - bb.ymin, 40.0)
             .translate(((bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0,
                         bb.zmin - 20.0)).val())
    low = []
    for name, shp in comps:
        if name in ("motor_ctrl",) or name.startswith("wire_"):
            continue
        try:
            it = shp.intersect(below)
            v = it.Volume() if it.Solids() else 0.0
        except Exception:
            v = 0.0
        if v > 0.5:
            b = it.BoundingBox()
            low.append((-b.zmax, v, name, b))
    for nz, v, name, b in sorted(low)[:8]:
        print("   %-22s top z %8.2f   %8.1f mm3" % (name, b.zmax, v))


if __name__ == "__main__":
    main()
