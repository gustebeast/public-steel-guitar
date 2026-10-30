"""Winding row: real string bays, one option per insert, on the real Ø8 axle.

Strings 1-5 of the real nut block at their real pitch and pockets, with the real rod bore, as one
block (PETG-GF, +X up, the part's real direction). Five real inserts (PCTG, -X up), each with a
different floor where the tail turns under the rod. No screws: push an insert with a small tool
through the hole under it. The options are at the -X end of the floor, where the tail comes down
the wall and has to turn +X under the rod; +X ramp as today. Trimmed in Z: everything the winding touches is true size, the pocket's
floor stands where the insert's real down travel ends, and the insert's long foot is cut short.

The insert's number is sunk in its -X face, low on the foot. It fits any bay, so bay order is free.

    py -3.12 -m src.test.wrap_row [out_dir]
"""
import math
import os
import sys

import cadquery as cq

from .. import nut_block as N
from .. import dimensions as D
from cadkit.holes import teardrop_hole
from cadkit.step_export import export_step, print_pose
from .wrap_bay import side_token

STRINGS = range(5)
FOOT = 5 * D.BEAD                           # 4.0 of foot under the insert's body, to push and grip
CAP = D.MIN_WALL_2P                         # the floor under the pocket
WALL = D.MIN_WALL_2P                        # stands in for the deck panel the +X face bears on
TOOL_D = 4.4
Z_FOOT = min(N.insert_flat_z(i) for i in STRINGS) - N.INS_H - FOOT    # the inserts' cut end
Z_FLOOR = Z_FOOT - N.INS_DROP               # ...and where it lands, dropped


G = max(D.STRING_GAUGE[:N.N_FINGERED])      # the fattest coil on these inserts: the floor's worst
R = N.ROD_D / 2 + G                         # ...at home, the flat tangent under it


def profile(pts, fz):
    """Solid under the -X end of the floor: pts are (x, height over the flat), -X end first."""
    x0 = N.INS_X0 - 0.5
    w = cq.Workplane("XZ").moveTo(x0, fz - 0.5).lineTo(x0, fz + pts[0][1])
    for p in pts:
        w = w.lineTo(p[0], fz + p[1])
    return w.lineTo(pts[-1][0], fz - 0.5).close()


def flat(fz):
    return None


def chute45(fz):
    return profile([(N.INS_X0, N.RAMP_END), (N.INS_X0 + N.RAMP_END, 0.0)], fz)


def _pts30():
    a = math.radians(30.0)
    xt, zt = N.ROD_X - R * math.sin(a), R * (1 - math.cos(a))           # on the coil
    x0 = xt + zt / math.tan(a)
    return [(N.INS_X0, (x0 - N.INS_X0) * math.tan(a)), (x0, 0.0)]


def chute30(fz):
    return profile(_pts30(), fz)


CURVE_R, CURVE_XT = 6.4, N.ROD_X - 0.4


def _pts_curve():
    """Floor tangent, turning up to 45 deg and no further (the print's limit), then straight."""
    pts = []
    for k in range(25, -1, -1):
        a = math.radians(45.0) * k / 25
        pts.append((CURVE_XT - CURVE_R * math.sin(a), CURVE_R * (1 - math.cos(a))))
    xa, za = pts[0]
    return [(N.INS_X0, za + (xa - N.INS_X0))] + pts


def curve(fz):
    return profile(_pts_curve(), fz)


CUP_R = R + N.INS_DROP                      # round the rod with the insert dropped


def _pts_cup():
    pts = []
    x0 = N.INS_X0
    for k in range(0, 26):
        x = x0 + (N.ROD_X - x0) * k / 25
        pts.append((x, CUP_R - math.sqrt(CUP_R ** 2 - (x - N.ROD_X) ** 2)))
    return pts


def cup(fz):
    return profile(_pts_cup(), fz)


OPTIONS = [("flat", flat, None), ("45, today", chute45, [(N.INS_X0, N.RAMP_END), (N.INS_X0 + N.RAMP_END, 0.0)]),
           ("30", chute30, _pts30()), ("curve r6.4 to 45", curve, _pts_curve()), ("cup r%.2f" % CUP_R, cup, _pts_cup())]


def clearance(pts, g):
    """Least air between a floor, polyline (x, height), and string g's coil at home."""
    r = N.ROD_D / 2 + g
    best = 9.0
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        for t in [q / 40.0 for q in range(41)]:
            x, z = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
            best = min(best, math.hypot(x - N.ROD_X, z - r) - r)
    return best


def block():
    x0, x1 = N.X_BACK, N.X_FRONT + 0.3 + WALL
    y0 = N.D.nut_y(STRINGS[-1]) - N.INS_LOBE_W - 4 * D.BEAD
    y1 = N.D.nut_y(STRINGS[0]) + N.INS_LOBE_W + 4 * D.BEAD
    z0 = Z_FLOOR - CAP
    keep = cq.Workplane("XY").box(N.X_FRONT - x0, y1 - y0, N.NUT_TOP - z0, centered=False).translate(
        (x0, y0, z0))
    body = N.nut_block.intersect(keep)
    body = body.union(cq.Workplane("XY").box(x1 - x0, y1 - y0, N.NUT_BASE - z0, centered=False)
                      .translate((x0, y0, z0)))
    for i in STRINGS:
        body = body.cut(N._plan_wire(i).offset2D(N._clr(i), kind="arc")
                        .extrude(N.NUT_TOP + 1.0 - Z_FLOOR).translate((0, 0, Z_FLOOR)))
        body = body.cut(teardrop_hole(TOOL_D, CAP + 2.0, (N.INS_X0 + 6.0, D.nut_y(i), z0 - 1.0),
                                      (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)))
    return body.cut(N.rod_bore())


def insert(k, i):
    section = OPTIONS[k][1]
    fz = N.insert_flat_z(i)
    body = N.slide_insert(i).val()
    bb = body.BoundingBox()
    body = cq.Workplane("XY").newObject([body]).intersect(
        cq.Workplane("XY").box(40.0, 40.0, bb.zmax - Z_FOOT, centered=False).translate(
            (-25.0, bb.ymin - 10.0, Z_FOOT)))
    # today's end ramp off, the option on, in the insert's own plan
    body = body.cut(cq.Workplane("XY").box(N.RAMP_END + 1.0, 40.0, N.RAMP_END + 1.0, centered=False)
                    .translate((N.INS_X0 - 1.0, bb.ymin - 10.0, fz)))
    s_ = section(fz)
    if s_ is not None:
        keep = N._part_wire(i).extrude(14.0).translate((0, 0, fz - 1.0))
        body = body.union(s_.extrude(40.0).translate((0, bb.ymax + 10.0, 0)).intersect(keep))
    mark = (cq.Workplane("YZ").workplane(offset=N.INS_X0 - 0.01)
            .center(D.nut_y(i) - 2.0, Z_FOOT + 2.4).text(str(k + 1), 3.2, 0.41))
    return body.cut(mark)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "..")
    print("INS_DROP %.2f, gap under the rod, dropped: string 1 %.2f" % (
        N.INS_DROP, N.INS_DROP + D.STRING_GAUGE[0]))
    for label, _f, pts in OPTIONS:
        if pts:
            leave = pts[-1][0]
            print("%-18s rise at the end %.2f, leaves the flat at x %.2f, flat left to the +X ramp "
                  "%.2f; air to the coil at home: .036 %.2f  .036 fat %.2f  .070 %.2f" % (
                      label, pts[0][1], leave, N._neck_x0(0) - N.RAMP_NECK - leave,
                      clearance(pts, D.STRING_GAUGE[6]), clearance(pts, G), clearance(pts, D.STRING_GAUGE[9])))
    b = print_pose(block(), ((0, 1, 0), -90))
    bb = b.val().BoundingBox()
    print("block %.1f x %.1f x %.1f tall, %d solid(s), valid %s, %.1f cm3" % (
        bb.xlen, bb.ylen, bb.zlen, len(b.val().Solids()), b.val().isValid(), b.val().Volume() / 1000))
    export_step(b, os.path.join(out, "test_wrap_row_block.step"))
    parts = []
    for k, i in enumerate(STRINGS):
        s = insert(k, i)
        print(k + 1, OPTIONS[k][0], "valid", s.val().isValid(), "solids", len(s.val().Solids()),
              "%.0f mm3" % s.val().Volume())
        p = print_pose(s, ((0, 1, 0), 90)).val()
        parts.append(p.moved(cq.Location(cq.Vector(0.0, k * 14.0, 0.0))))
    pb = parts[-1].BoundingBox()
    print("inserts each %.1f x %.1f x %.1f tall" % (pb.xlen, pb.ylen, pb.zlen))
    export_step(cq.Workplane("XY").newObject([cq.Compound.makeCompound(parts)]),
                os.path.join(out, "test_wrap_row_inserts.step"))
    export_step(print_pose(side_token(), ((1, 0, 0), 90)), os.path.join(out, "test_wrap_side.step"))


if __name__ == "__main__":
    main()
