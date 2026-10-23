"""ENDPLATE ROUND: the chassis <-> bridge endplate joint, ALL FOUR tenons at once, at full length.

    py -3.12 -m src.test.endplate_round chassis        # -> test_ep_chassis.step (once)
    py -3.12 -m src.test.endplate_round 0.40           # -> test_ep_socket_c040.step
    py -3.12 -m src.test.endplate_round plate 0.30 0.40   # lay out what is exported

Why (user, 2026-10-22: "what is left is testing the chassis to endplate joints"). The lever
and the seam both slid as single joints and bound as SETS (8 lever tenons, the seam's full
drop): a joint is only proven with every tenon it shares a part with, at their real spacing,
held as stiffly as the real parts hold them. The bridge endplate drops onto FOUR at once -- per
rail a LOWER one on the leg shell's face (bed .. the foot line, 58 long) and an UPPER one on
the rail's end (foot line .. -7.2), 39.7 apart in X, and the two rails 197.5 apart in Y.

THE TENON DOES NOT CHANGE WITH c (fit_plate2.halves: only the socket grows), so ONE chassis
coupon is printed and each step of the sweep is an endplate coupon alone. The keyhead end is
the same profile in the same print sense (both endplates build from their outer face, the
socket's mouth up), so this end answers for both.

MATERIAL (user: "see how much material you can save while keeping the important parts
supported without bridging and while maintaining enough rigidity to mimic the real part"):
each coupon is its real part cut down to the joint, plus FIXTURE (_fix_*) that only holds the
pieces at their real spacing:
  chassis (prints +Z): per rail, a POST under each tenon at the rail's full 10.4 (the tenon's
    host) joined by a 2-bead WEB of the shell between them -- a vertical wall, so nothing over
    air -- and, on the bed, a TRUSS across the rails: a beam under each line of posts and a
    diagonal, so neither rail can shift or rotate against the other.
  endplate (prints -X, outer face on the bed): per rail a CORNER, the outer wall round the lower
    socket and the foot block round the upper socket (whose underside is the foot that seats
    on the shell, the joint's drop stop), each 2 beads past the widest socket; and on the bed a
    FRAME of the same three bands. The foot block stands on the outer wall in the print, so
    it is carried, not bridged.
"""
from __future__ import annotations

import math
import pathlib
import sys

import cadquery as cq

HERE = pathlib.Path(__file__).resolve().parent
B2 = 2 * 0.8                     # two beads

BEAM_H = 6 * 0.8                 # 4.8 the truss / frame bands' height off the bed
BEAM_W = 8.0                     # their width
FOOT_H = 12 * 0.8                # 9.6 the chassis coupon's solid foot, over the leg-stub grooves
WALL_SOCK = 3.12 + B2            # an endplate corner's half-width round a socket at c 0.60


def _box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def _bar(p, q, w, z0, z1):
    """A flat bar on the bed from (x, y) p to q, w wide."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy)
    b = _box(0.0, L, -w / 2, w / 2, z0, z1)
    return (b.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), math.degrees(math.atan2(dy, dx)))
            .translate(cq.Vector(p[0], p[1], 0.0)))


def _bar_yz(p, q, w, x0, x1):
    """A flat bar on a bed that is an X face: from (y, z) p to q, w wide, x0..x1 thick."""
    dy, dz = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dy, dz)
    b = _box(x0, x1, -w / 2, w / 2, 0.0, L)                       # along +Z
    b = b.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), math.degrees(math.atan2(-dy, dz)))
    return b.translate(cq.Vector(0.0, p[0], p[1]))


def _one(shapes):
    out = shapes[0]
    for s in shapes[1:]:
        out = out.fuse(s)
    out = out.clean()
    assert len(out.Solids()) == 1, "came out in %d pieces" % len(out.Solids())
    return out


def _frame():
    from src import chassis as C
    return C, C.Z_BOT, C.TP_EP_GX, C._SHELL_PX, C.KH_DT_Z0, C.TP_GZ0 - C.TP_TG_DEPTH


def chassis_coupon(chassis):
    """The four tenons on their rail ends, cut from the built chassis_0 (+X end)."""
    C, ZB, XU, XL, ZF, ZT = _frame()
    T = C.T
    up_x0, up_x1 = XU - 5 * 0.8, XU + C.KH_DT_DEPTH        # 4.0 of rail behind the upper face
    lo_x0, lo_x1 = XL - 5 * 0.8, XL + C.KH_DT_DEPTH        # 4.0 of shell behind the lower face
    keep = []
    for yr in C.ENDPLATE_JOINT_Y:
        y0, y1 = yr - T / 2, yr + T / 2
        keep.append(_box(up_x0, up_x1, y0, y1, ZB, ZT))      # upper post: shell + rail + tenon
        keep.append(_box(lo_x0, lo_x1, y0, y1, ZB, ZF))      # lower post: shell + tenon
        keep.append(_box(up_x1, lo_x0, yr - B2 / 2, yr + B2 / 2, ZB, ZF))   # the shell's web
    real = [chassis.intersect(k) for k in keep]
    # _fix_foot: the leg-stub grooves run through the shell along its foot and leave a bridge
    # and its hanging ends over each in the posts and the web; they are the BODY ADAPTER's
    # joint, not this one, so the coupon's foot is solid to FOOT_H (the tenons stay untouched:
    # the lower post's fill stops at its face)
    for yr in C.ENDPLATE_JOINT_Y:
        y0, y1 = yr - T / 2, yr + T / 2
        keep_fill = [_box(up_x0, up_x1, y0, y1, ZB, ZB + FOOT_H),
                     _box(lo_x0, XL, y0, y1, ZB, ZB + FOOT_H),
                     _box(up_x1, lo_x0, yr - B2 / 2, yr + B2 / 2, ZB, ZB + FOOT_H)]
        real.extend(keep_fill)
    yl, yh = min(C.ENDPLATE_JOINT_Y) - T / 2, max(C.ENDPLATE_JOINT_Y) + T / 2
    fix = [_bar((up_x0 + BEAM_W / 2, yl), (up_x0 + BEAM_W / 2, yh), BEAM_W, ZB, ZB + BEAM_H),
           _bar((XL - BEAM_W / 2, yl), (XL - BEAM_W / 2, yh), BEAM_W, ZB, ZB + BEAM_H),
           _bar((up_x0 + BEAM_W / 2, yl + BEAM_W / 2), (XL - BEAM_W / 2, yh - BEAM_W / 2),
                BEAM_W, ZB, ZB + BEAM_H)]
    return _one([s for r in real for s in (r.Solids() if hasattr(r, 'Solids') and not isinstance(r, cq.Solid) else [r])] + fix)


def endplate_coupon(ep):
    """The four sockets in their two corners of the built bridge endplate, on a frame."""
    C, ZB, XU, XL, ZF, ZT = _frame()
    bb = ep.BoundingBox()
    x_out = bb.xmax                                           # the outer face: the print's bed
    top = ZT + 1.7                                            # the upper socket's end, plus
    keep = []
    for yr in C.ENDPLATE_JOINT_Y:
        s = 1 if yr > 0 else -1                               # outward
        yin, yfar = yr - s * WALL_SOCK, (bb.ymax if s > 0 else bb.ymin)
        y0, y1 = sorted((yin, yfar))
        keep.append(_box(XL, x_out, y0, y1, ZB, top))         # outer wall round the lower socket
        keep.append(_box(XU - 4.0, XL, y0, y1, ZF, top))      # the foot block round the upper one
    real = [ep.intersect(k) for k in keep]
    yl = min(C.ENDPLATE_JOINT_Y) + WALL_SOCK - 1.0
    yh = max(C.ENDPLATE_JOINT_Y) - WALL_SOCK + 1.0
    x0 = x_out - BEAM_H
    fix = [_box(x0, x_out, yl, yh, ZB, ZB + BEAM_W),          # bottom band
           _box(x0, x_out, yl, yh, top - BEAM_W, top)]        # top band
    fix.append(_bar_yz((yl + BEAM_W / 2, ZB + BEAM_W / 2), (yh - BEAM_W / 2, top - BEAM_W / 2),
                       BEAM_W, x0, x_out))                    # the frame's diagonal
    return _one([s for r in real for s in r.Solids()] + fix)


def _loose_halves(C):
    """chassis._ep_halves without its outer-wall assert: past c 0.30 the socket's corner necks
    the endplate's outer wall under two beads (1.56 at 0.40, 1.48 at 0.50). A coupon may print
    it, and says so; the INSTRUMENT may not -- a looser winner moves the joint in off the face."""
    import functools
    from src.test import fit_plate2 as FIT

    @functools.lru_cache(maxsize=None)
    def halves(length):
        ten, cav, S = FIT.halves("N", "down", C.KH_DT_CLR, length, C.EP_TOP_CLR, C.EP_J_HOST_W)
        throat = (5.0 - (S["h"] + C.KH_DT_CLR)) / math.sqrt(2.0)
        print("c %.2f: the endplate's outer wall necks to %.2f across the diagonal%s"
              % (C.KH_DT_CLR, throat, "" if throat >= B2 - 1e-9 else " -- UNDER two beads"))
        return ten, cav
    return halves


def _export(shape, up, name):
    from cadkit.orientation import PrintOrientation as PO
    from cadkit.step_export import export_print
    path = HERE / ("test_%s.step" % name)
    export_print(cq.Workplane("XY").newObject([shape]), PO.from_build_dir(up, "as the part it is cut from"),
                 str(path))
    print("wrote", path, "%.1f cm3" % (shape.Volume() / 1000.0))
    return path


def main(argv=None):
    args = list(argv or sys.argv[1:])
    if args[0] == "chassis":
        from src.test import bench_joinery as BJ
        comps, where = BJ.components(own=True)
        print("chassis from", where)
        _export(chassis_coupon(comps["chassis_0"]), (0.0, 0.0, 1.0), "ep_chassis")
        return 0
    c = float(args[0])
    from src import chassis as C                 # the socket reads KH_DT_CLR when it is cut
    C.KH_DT_CLR = c
    C._ep_halves = _loose_halves(C)
    from src import bridge_endplate as BE        # ...which is at import: patch first
    ep = BE.bridge_endplate
    ep = ep.val() if hasattr(ep, "val") else ep
    _export(endplate_coupon(ep), BE.PRINT_UP, "ep_socket_c%03d" % round(c * 100))
    return 0


if __name__ == "__main__":
    sys.exit(main())
