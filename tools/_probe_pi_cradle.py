"""Where can the FLAT Pi's cradle go? Two questions, both answered by intersection
rather than by reading a datum -- this file's own method note, earned three times over.

  1. which edge can carry the one M4 hold-down boss (-x, +y or -y; +x is the I/O and is
     the open edge), and
  2. how much STANDOFF is available under the board before its top face hits something.

Run from the worktree root:  py -3.12 tools/_probe_pi_cradle.py
"""
import cadquery as cq

from src.build import collect_components
from src import electronics as EL
from src import motor_bank as MB
from cadkit.fasteners import M4

FP = EL.PI_FP                                   # world x0, x1, y0, y1
BW, BL = FP[1] - FP[0], FP[3] - FP[2]           # 85 x 56
CX, CY = (FP[0] + FP[1]) / 2.0, (FP[2] + FP[3]) / 2.0
FLOOR = MB.FLOOR_TOP
CLR, WALL = 0.3, 1.6
PI_H = 15.6                                     # board + the tallest thing on it


def _box(w, l, h, x, y, z0):
    return (cq.Workplane("XY").box(w, l, h)
            .translate((x, y, z0 + h / 2.0)).val())


def _hits(shape, comps, skip=(), floor=0.5):
    out = []
    for name, shp in comps:
        if name in skip or name.startswith("pi5"):
            continue
        try:
            inter = shp.intersect(shape)
            v = inter.Volume() if inter.Solids() else 0.0
        except Exception:
            v = 0.0
        if v > floor:
            out.append((v, name, inter.BoundingBox()))
    return sorted(out, reverse=True)


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    print("assembly: %d solids" % len(comps))
    print("Pi footprint world x %.1f..%.1f  y %.1f..%.1f   floor top %.2f"
          % (FP[0], FP[1], FP[2], FP[3], FLOOR))

    # ---- 1. the boss, one candidate per edge -------------------------------------
    off = CLR + M4.shaft_clr_d / 2.0            # 2.50, how far the axis sits off the edge
    D = M4.boss_od                              # 9.20
    print("\n=== 1. M4 hold-down boss, O%.1f, axis %.2f mm outside the edge ===" % (D, off))
    print("    (boss runs floor %.2f up to the board underside; tested full board height)" % FLOOR)
    for edge, (bx, by) in (("-x", (FP[0] - off, CY)),
                           ("+y", (CX, FP[3] + off)),
                           ("-y", (CX, FP[2] - off))):
        col = (cq.Workplane("XY")
               .add(cq.Solid.makeCylinder(D / 2.0, PI_H, cq.Vector(bx, by, FLOOR))))
        h = _hits(col.val(), comps)
        print("\n  %-3s boss at (%.2f, %.2f):" % (edge, bx, by))
        if not h:
            print("      CLEAR -- nothing in the way")
        for v, name, bb in h[:6]:
            print("      %-24s %8.2f mm3   x %8.2f..%8.2f y %8.2f..%8.2f z %7.2f..%7.2f"
                  % (name, v, bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))

    # ---- 2. the walls, as one ring ----------------------------------------------
    ox, oy = BW / 2 + CLR + WALL, BL / 2 + CLR + WALL
    print("\n=== 2. the wall ring (open on +x for the I/O) ===")
    ring = None
    for w, l, x, y in ((WALL, 2 * oy, CX - (BW / 2 + CLR + WALL / 2), CY),
                       (2 * ox, WALL, CX, CY + (BL / 2 + CLR + WALL / 2)),
                       (2 * ox, WALL, CX, CY - (BL / 2 + CLR + WALL / 2))):
        b = _box(w, l, PI_H, x, y, FLOOR)
        ring = b if ring is None else ring.fuse(b)
    for v, name, bb in _hits(ring, comps)[:10]:
        print("   %-24s %8.2f mm3   x %8.2f..%8.2f y %8.2f..%8.2f z %7.2f..%7.2f"
              % (name, v, bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
    else:
        pass
    if not _hits(ring, comps):
        print("   CLEAR -- the whole ring fits")

    # ---- 3. headroom: how far can the board rise? -------------------------------
    print("\n=== 3. standoff headroom -- raise the board and see what it meets ===")
    for so in (0.0, 1.6, 2.4, 2.5, 3.2, 4.0, 6.0):
        slab = _box(BW, BL, PI_H, CX, CY, FLOOR + so)
        h = _hits(slab, comps)
        tot = sum(v for v, _n, _b in h)
        tag = "CLEAR" if not h else "%8.2f mm3  %s" % (tot, ", ".join(n for _v, n, _b in h[:3]))
        print("   standoff %4.2f -> board z %8.2f..%8.2f   %s"
              % (so, FLOOR + so, FLOOR + so + PI_H, tag))


if __name__ == "__main__":
    main()
