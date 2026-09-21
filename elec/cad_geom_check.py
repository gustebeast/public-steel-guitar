"""Does each board's CAD actually render the board that was ROUTED?

    py -3.12 elec/cad_geom_check.py            # every board
    py -3.12 elec/cad_geom_check.py optical    # one

⚠ WHAT THIS REPLACED, AND WHY IT HAD TO. The previous version compared the CAD's
hand-copied connector anchors with elec/<board>.py's placements -- the numbers layout is
GIVEN. A copy checked against its own source can only agree, and it did while:
  * the output board's two panel connectors' bodies stopped 0.54 mm short of the edge
    (their COURTYARDS had been placed flush; a courtyard is the keep-out, not the part),
  * the 24 V barrel inlet faced along the board at the chassis rail (0 degrees, where
    that footprint's mouth is its local +Y) and the CAD drew it as a panel inlet,
  * and the USB-C hole was cut 7.85 mm above the receptacle.
The user's words for the gap: "your validation passes didn't cover accurately rendering
each board in CAD". Right -- DRC checks copper against the netlist, the overlap gate checks
solids against solids, and nothing ever compared the CAD's board with the real one.

WHAT THIS DOES. elec/geom/<board>.geom.json is the ROUTED board read back (export_geom.py,
run by finish.py). For every footprint it takes the centre of the part's F.Fab BODY, just
above the board face, and asks whether the CAD's board solid has material there. A part
that is missing, moved, or turned so its body lands somewhere else, fails.

It needs no per-board frame bookkeeping, because the boards live in five different frames
(the output board and motor controller centred on their own origin, the optical strip in
world coordinates, the lever sensor standing in XZ, the tee on the chassis floor). It FINDS
the pose: the plate is the planar face whose bounding box matches the routed outline, its
normal is the board's down, and of the eight ways the board can lie in that plane it keeps
the one where the most parts land -- and SAYS if that one is mirrored.
"""
import itertools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import cadquery as cq                                 # noqa: E402

from src import board_geom as BG                      # noqa: E402

# Solder jumpers are flat copper with no body; nothing stands above the board to find.
NO_BODY_PREFIX = ("JP", "TP")


def _cad(board):
    """The board's CAD solid, whole: plate plus every part, in whatever frame it is built."""
    if board == "output_panel":
        from src import electronics as EL
        return EL.output_panel_pcb()
    if board == "motor_ctrl":
        from src import electronics as EL
        return EL.motor_ctrl_pcb()
    if board == "can_tee":
        from src import electronics as EL
        return EL.tee_pcb(0.0, 0.0)
    if board == "optical":
        from src import optical_pickup as OP
        return OP.opt_pcb()
    if board == "lever_sensor":
        from src import knee_lever as KL
        s = KL.sensor_board()
        for _n, part in KL.sensor_hardware():
            s = s.union(part)
        return s.union(KL.sensor_connector())
    raise KeyError(board)


BOARDS = ("output_panel", "motor_ctrl", "optical", "lever_sensor", "can_tee")
AX = {"x": cq.Vector(1, 0, 0), "y": cq.Vector(0, 1, 0), "z": cq.Vector(0, 0, 1)}


def _plates(solid, w, l):
    """[(centre, outward normal)] of every flat face the size of the routed outline.

    ⚠ PLURAL, because a plate has TWO such faces and only one is its underside. The first
    version took the best-matching one, which was the TOP face as often as not -- "up" then
    pointed into the board and every probe landed underneath it: the output board, whose
    CAD is generated from this very export, scored 0 of 60. The caller tries each as the
    underside and keeps whichever the parts agree with."""
    found, best = [], None
    for f in solid.faces().vals():
        if f.geomType() != "PLANE":
            continue
        bb = f.BoundingBox()
        dims = sorted([bb.xlen, bb.ylen, bb.zlen])[1:]      # the two in-plane extents
        err = abs(dims[0] - min(w, l)) + abs(dims[1] - max(w, l))
        best = err if best is None else min(best, err)
        if err <= 0.5:
            found.append((f.Center(), f.normalAt()))
    if not found:
        # the CAD's plate is not the routed board's size at all -- report both, because
        # that IS the finding (the lever sensor grew 28 x 21.4 -> 34 x 28 and its CAD did not)
        sizes = sorted({tuple(round(d, 2) for d in sorted([f.BoundingBox().xlen,
                        f.BoundingBox().ylen, f.BoundingBox().zlen])[1:])
                        for f in solid.faces().vals() if f.geomType() == "PLANE"},
                       key=lambda d: -d[0] * d[1])[:3]
        raise RuntimeError("the CAD's board is not the routed board: routed outline %.2f x "
                           "%.2f, largest flat faces in the CAD %s" % (w, l, sizes))
    return found


def check(board, verbose=True):
    g = BG.load(board)
    w, l = g["outline_mm"]
    t = g["thickness_mm"]
    solid = _cad(board).val()
    parts = [f for f in g["footprints"]
             if f["fab"] and not f["ref"].startswith(NO_BODY_PREFIX)]
    best = None
    for c, down in _plates(cq.Workplane(obj=solid), w, l):
        up = cq.Vector(-down.x, -down.y, -down.z)
        inplane = [q for q in AX.values() if abs(q.dot(up)) < 0.5]
        for a, b, sa, sb in ((a, b, sa, sb) for a, b in itertools.permutations(inplane, 2)
                             for sa, sb in itertools.product((1, -1), (1, -1))):
            u, v = a * sa, b * sb
            mirrored = u.cross(v).dot(up) < 0
            misses = []
            for f in parts:
                x0, x1, y0, y1 = f["fab"]
                bx, by = (x0 + x1) / 2.0, (y0 + y1) / 2.0
                lift = t + 0.15 if f["side"] == "F" else -0.15
                if not solid.isInside(c + u * bx + v * by + up * lift, 0.01):
                    misses.append((f["ref"], BG.fp_name(f["fpid"]), bx, by))
            # fewest misses wins; on a tie the UNmirrored pose does, or a board that renders
            # perfectly could be reported as mirrored just because that pose was tried first
            key = (len(misses), mirrored)
            if best is None or key < (len(best[0]), best[1]):
                best = (misses, mirrored)
    misses, mirrored = best
    ok = len(parts) - len(misses)
    if verbose:
        print("%-13s %3d / %3d routed parts present in the CAD%s"
              % (board, ok, len(parts), "   !! MIRRORED" if mirrored else ""))
        for ref, name, bx, by in misses:
            print("      MISSING %-6s %-44s routed at (%.2f, %.2f)" % (ref, name[:44], bx, by))
    return len(misses) + (1 if mirrored else 0)


def main(argv):
    bad = 0
    for b in (argv or BOARDS):
        try:
            bad += check(b)
        except Exception as exc:                  # a board the check cannot read is a
            print("%-13s COULD NOT CHECK: %s" % (b, exc))   # finding, not a pass
            bad += 1
    print("\n%s" % ("every routed part is where the CAD draws it" if not bad
                    else "*** %d DISAGREEMENT(S) BETWEEN THE CAD AND THE ROUTED BOARDS ***"
                    % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
