"""Does every wire end IN ITS OWN WAY of its own plug?

    PYTHONPATH=. py -3.12 -m tools.check_wire_ends            # the table, exit 1 on a miss
    PYTHONPATH=. py -3.12 -m tools.check_wire_ends --all      # every way, the good ones too

A harness is drawn conductor by conductor, and each end is a point somebody computed. The
overlap gate cannot say whether that point is a contact: a wire that stops a millimetre
under its way, or beside the housing, overlaps nothing. This asks the routed boards
instead. cadkit's Boards.wire_exit gives, for every way of every JST, the centre of that
way's wire cavity on the back face of the seated crimp housing and the direction the wire
leaves in; each is put where the placed board is (cadkit.board_check.place, which reads
the pose off the solid), and then:

  * a WAY IS TAKEN when a wire's solid holds the point just outside its cavity;
  * a WIRE END IS LOOSE when the wire comes within NEAR of a way's point without taking
    it -- it was meant for that connector and misses, and the miss is printed in the
    plug's own axes (along the row, across it, and in or out of the housing).

Two wires in one way, and a loose end, are failures. A way nothing takes is only listed:
not every way of every connector carries a conductor.

AND EVERY WIRE IS ACCOUNTED FOR BY NAME. A conductor that floats -- ends near nothing --
takes no way and misses none, so the way-by-way test passes it. ENDS says how many of
each wire's ends are JST ways (first match wins; two unless it says otherwise), and a
wire with fewer or more than that is a failure too.

WHAT THIS DOES NOT PROVE: that a way holds the RIGHT net (src.wiring.check_cables holds
each drawn cable to elec/harness.py, way by way, for the cables declared there); that an
end which is not a JST -- a screw terminal, a USB plug, the ribbon's IDC header, a pogo
board's pad, the motor's own terminals -- is anywhere in particular; or that the plug's
own dimensions are the part's (cadkit.pcb.JST_SERIES says which are estimates).
"""

from __future__ import annotations

import argparse
import re
import sys

import cadquery as cq

NEAR = 4.0          # a wire this close to a way's point and not in it was meant for it
STEP = 0.4          # how far out of the cavity, along the wire's exit, the wire is looked for

# placed board (component name) -> routed board
BOARD_OF = (
    (r"^tee_pcb_\d+$", "can_tee"),
    (r"^(\w+_)?k[lv]_pcb$|^pedal\d+_pcb$", "lever_sensor"),
    (r"^motor_ctrl$", "motor_ctrl"),
    (r"^pi_cap$", "pi_cap"),
    (r"^output_panel$", "output_panel"),
    (r"^optical_pcb$", "optical"),
    (r"^foot_pcb_a$", "foot_led_a"),
    (r"^fret_pcb_key$", "fret_led_key"),
    (r"^pogo_(male|female)_board_(top|bottom)$", r"leg_pogo_\1_\2"),
)
WIRE = re.compile(r"^wire_|pigtail|_cable_")

# how many of a wire's ends are JST ways, and why not two
ENDS = (
    (r"^motor_pigtail_\d+$", 0),            # the jacket: motor terminals to where it splits
    (r"^motor_pigtail_\d+_\d+$", 1),        # ...and each conductor from there into the tee's drop
    (r"^wire_link$", 0),                    # the jacket: the Pi's USB-A to where it splits
    (r"^wire_link_\d+$", 1),
    (r"^wire_canb_coil_", 0),               # the coiled middle of a lever-to-lever lead
    (r"^wire_canb_\w+_\d+_[01]$", 1),       # ...and its two halves, a plug on one end each
    (r"^wire_(usb|ui|pickup)$|^optical_cable_usb$", 0),   # USB, the IDC ribbon, screw terminals
)


def ends_of(name):
    for rx, n in ENDS:
        if re.match(rx, name):
            return n
    return 2


def _board(name):
    for rx, board in BOARD_OF:
        m = re.match(rx, name)
        if m:
            return m.expand(board)
    return None


def _pt(v):
    return (v.X, v.Y, v.Z)


def ways(parts, boards):
    """[(board part, ref, way, point, out, row, up)] in the world, for every JST of every
    placed board."""
    from cadkit.board_check import place
    out = []
    for name, solid in parts:
        board = _board(name)
        if board is None:
            continue
        geom = boards.load(board)
        for f in geom["footprints"]:
            plug = boards.plug(board, f["ref"])
            if plug is None:
                continue
            # the way's point and three more, one along each of the plug's axes: the pose
            # is read once and the axes come out of it as differences
            marks = []
            for n, p in sorted(plug["ways"].items()):
                marks.append(cq.Vertex.makeVertex(*p))
            o = plug["ways"][min(plug["ways"])]
            for axis in (plug["out"], plug["row"], plug["up"]):
                marks.append(cq.Vertex.makeVertex(*(o[k] + axis[k] for k in range(3))))
            try:
                placed = place(solid, geom, cq.Workplane("XY").newObject(marks)).vals()
            except Exception as exc:
                print("  ?? %s: its pose could not be read (%s)" % (name, exc))
                break
            pts = [_pt(v) for v in placed]
            base = pts[0]
            ax = [tuple(pts[-3 + i][k] - base[k] for k in range(3)) for i in range(3)]
            for (n, _), p in zip(sorted(plug["ways"].items()), pts):
                out.append((name, f["ref"], n, p, ax[0], ax[1], ax[2], plug["housing"]))
    return out


def audit(parts, boards, show_all=False):
    wires = [(n, s.val() if hasattr(s, "val") else s) for n, s in parts if WIRE.search(n)]
    boxes = {n: s.BoundingBox() for n, s in wires}
    table = ways(parts, boards)
    bad = 0
    taken_by = {}
    rows = []
    for part, ref, n, p, out, row, up, housing in table:
        probe = cq.Vector(*(p[k] + STEP * out[k] for k in range(3)))
        here, near = [], []
        for wn, ws in wires:
            b = boxes[wn]
            if not (b.xmin - NEAR < p[0] < b.xmax + NEAR and b.ymin - NEAR < p[1] < b.ymax + NEAR
                    and b.zmin - NEAR < p[2] < b.zmax + NEAR):
                continue
            if ws.isInside(probe, 1e-4):
                here.append(wn)
                continue
            d = ws.distToShape(cq.Vertex.makeVertex(*p)) if hasattr(ws, "distToShape") else None
            if d is None:
                from OCP.BRepExtrema import BRepExtrema_DistShapeShape
                e = BRepExtrema_DistShapeShape(ws.wrapped, cq.Vertex.makeVertex(*p).wrapped)
                d = e.Value()
                q = e.PointOnShape1(1)
                at = (q.X(), q.Y(), q.Z())
            if d < NEAR:
                v = tuple(at[k] - p[k] for k in range(3))
                near.append((d, wn, tuple(sum(v[k] * a[k] for k in range(3)) for a in (row, up, out))))
        for wn in here:
            taken_by.setdefault(wn, []).append((part, ref, n))
        rows.append((part, ref, n, housing, here, sorted(near)))
    # a wire that takes a way of this connector is not "near" its neighbours: it is home
    for part, ref, n, housing, here, near in rows:
        home = {wn for wn, ends in taken_by.items() if any(e[:2] == (part, ref) for e in ends)}
        loose = [x for x in near if x[1] not in home]
        if len(here) > 1:
            bad += 1
            print("  TWO IN ONE  %s %s way %d (%s): %s" % (part, ref, n, housing, ", ".join(here)))
        elif here and show_all:
            print("  ok          %s %s way %d: %s" % (part, ref, n, here[0]))
        if not here and loose:
            d, wn, (dr, du, do) = loose[0]
            bad += 1
            print("  LOOSE       %s %s way %d (%s): %s is %.2f off -- %+.2f along the row, "
                  "%+.2f across, %+.2f out of the housing" % (part, ref, n, housing, wn, d, dr, du, do))
        elif not here and show_all:
            print("  empty       %s %s way %d" % (part, ref, n))
    ends = {wn: len(e) for wn, e in taken_by.items()}
    none = sorted(wn for wn, _ in wires if wn not in ends)
    one = sorted(wn for wn, k in ends.items() if k == 1)
    print("wire ends: %d ways on %d connectors; %d wires, %d with both ends in a way, %d with "
          "one, %d with none" % (len(table), len({r[:2] for r in rows}), len(wires),
                                 sum(1 for k in ends.values() if k >= 2), len(one), len(none)))
    if show_all:
        print("  one end in a way: " + ", ".join(one))
        print("  no end in a way:  " + ", ".join(none))
    for wn, _ in wires:
        got, want = ends.get(wn, 0), ends_of(wn)
        if got != want:
            bad += 1
            print("  FLOATS      %s has %d end(s) in a way, and should have %d" % (wn, got, want))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--all", action="store_true", help="list every way and every wire")
    a = ap.parse_args(argv)
    from src import build as B
    from src.board_geom import BOARDS
    parts = [(n, w) for n, w in B.wiring_work_components()]
    bad = audit(parts, BOARDS, a.all)
    print("check_wire_ends: %s" % ("%d way(s) wrong" % bad if bad else "clean"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
