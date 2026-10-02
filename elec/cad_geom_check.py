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
    if board == "ui_board":
        from src import ui_panel as UIP
        return UIP.ui_pcb()
    if board == "can_tee":
        from src import electronics as EL
        return EL.tee_pcb(0.0, 0.0)
    if board == "pi_cap":
        from src import electronics as EL
        return EL.pi_cap()
    if board == "optical":
        from src import optical_pickup as OP
        return OP.opt_pcb()
    if board == "lever_sensor":
        from src import knee_lever as KL
        s = KL.sensor_board()
        for _n, part in KL.sensor_hardware():
            s = s.union(part)
        return s.union(KL.sensor_connector())
    if board in ("fret_led_mid", "fret_led_key"):
        # the two fret boards: the laminate with every routed body, and the LEDs, which
        # src/fret_light.py draws as their own part so they read as lit
        from src import fret_light as FL
        panel = board.rsplit("_", 1)[1]
        return FL.pcb(panel)
    raise KeyError(board)


BOARDS = ("output_panel", "motor_ctrl", "optical", "lever_sensor", "can_tee",
          "pi_cap", "ui_board", "fret_led_mid", "fret_led_key")


def _ui_rule_check():
    """Does the UI board's routed switch land where the deck's spacing rule says?

    src/ui_panel.py owns the rule -- equal gaps between the deck's -Y edge, the knob,
    the display's window and the fretboard border, and the same gap again to the panel's
    +X seam -- and elec/ui_board.py places SW1 from it. Nothing downstream compares the
    two: the CAD draws the ROUTED switch, so if the placement drifted the deck's hole
    would drift with it, silently and consistently. This is the one check that reads
    both. It lives here rather than in ui_panel because ui_panel is on the generator's
    own import path, and an assertion there deadlocks the pipeline it is checking."""
    from src import ui_panel as UIP
    kx, ky = UIP.routed("SW1")
    wx, wy = UIP.knob_x(), UIP.y_layout()[1]
    off = max(abs(kx - wx), abs(ky - wy))
    if off > 0.05:
        print("   ui_board: the routed switch is at (%.3f, %.3f) and the spacing rule "
              "wants (%.3f, %.3f) -- %.3f off" % (kx, ky, wx, wy, off))
        return 1
    bad = 0
    for complaint in UIP.check_posts():
        print("   ui_board: %s" % complaint)
        bad += 1
    if bad:
        return bad
    print("   ui_board: the routed switch is on the spacing rule (%.3f off), and the "
          "cradle's four posts stand on bare board" % off)
    return 0
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
            # the face's BOX centre, not its centre of mass: a board with a mounting ear is
            # an L, and its mass centre sits millimetres off the frame the geom is written in
            # (both ear boards fell from 60/60 to ~20/60 on that alone)
            found.append((cq.Vector((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2,
                                    (bb.zmin + bb.zmax) / 2), f.normalAt(), f))
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


def _through_wires(plate, others, up):
    """The inner wires of `plate` that are CUTOUTS rather than parts sitting on it.

    ⚠ WHY THIS IS NOT JUST innerWires(). The CAD's board solid is the laminate FUSED WITH
    every part body, so a connector standing on the plate face leaves its own footprint as
    an inner wire of that face -- indistinguishable, by count, from a hole. pi_cap reported
    "the CAD plate has 10 hole(s), the routed board 0" for exactly that reason, and the
    number tracked how many parts were on the face rather than anything about cutouts: it
    was 4 with the connectors on the back, and 10 once every part moved there.

    The discriminator is the one thing a cutout has and a part does not: a cutout goes
    THROUGH, so it appears on BOTH plate faces at the same in-plane position. A part body
    appears on the face it stands on and nowhere else. So a wire counts only if the
    opposite face carries one whose offset from it is purely along the normal.
    """
    def _c(wr):
        bb = wr.BoundingBox()
        return cq.Vector((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2,
                         (bb.zmin + bb.zmax) / 2)
    # ⚠ `f is not plate` IS NOT AN IDENTITY TEST HERE. The caller re-runs _plates() to get
    # this list, so the plate's own twin is a DIFFERENT Python object wrapping the SAME face
    # -- and every wire then matches itself at zero offset, which reported all ten of
    # pi_cap's part outlines as through-cutouts. The face has to be excluded GEOMETRICALLY.
    opp = []
    for f in others:
        if abs(f.normalAt().dot(up)) > 0.9:
            opp.extend(_c(wr) for wr in f.innerWires())
    out = []
    for wr in plate.innerWires():
        c = _c(wr)
        for o in opp:
            d = o - c
            # in-plane offset ~0 (same hole) AND a real through-thickness offset (other face)
            if (d - up * d.dot(up)).Length < 0.20 and abs(d.dot(up)) > 0.5:
                out.append(wr)
                break
    return out


def _hole_check(board, plate, g, verbose, through=None):
    """Does the CAD's plate have the same CUTOUTS as the routed board?

    ⚠ THIS IS THE GAP THAT SHIPPED A BOARD WITH NO COMB. The footprint probe above asks
    whether every routed PART lands on CAD material, and it cannot see a cutout that is
    wrong in a region with no parts -- which is exactly what a cutout region is. The
    optical board's ten slots were emitted to Edge.Cuts as ONE rectangle spanning all of
    them, so the gerbers had a 16.41 x 101.6 mm hole where the CAD has ten slots and nine
    copper strips. Every check was green: the CAD gate, ERC, the netlist, and the
    CAD/netlist/BOM part reconciliation. They each read one side. The router found it, by
    failing to route across copper that the fab data said was not there.

    A plate face carries its holes as INNER WIRES, and the routed board's holes come back
    from export_geom via SHAPE_POLY_SET.Hole(). Comparing the two counts would have caught
    this on the first run; comparing areas catches a hole that is the right count and the
    wrong size. Both are cheap and need no per-board bookkeeping.
    """
    wires = plate.innerWires() if through is None else through
    cad_n = len(wires)
    routed = g.get("holes", [])
    def _area(pts):
        return abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1]
                       - pts[(i + 1) % len(pts)][0] * pts[i][1]
                       for i in range(len(pts)))) / 2.0
    cad_a = sum(abs(cq.Face.makeFromWires(wr).Area()) for wr in wires)
    routed_a = sum(_area(h) for h in routed)
    bad = 0
    if cad_n != len(routed):
        bad += 1
        if verbose:
            print("      CUTOUTS DISAGREE: the CAD plate has %d hole(s), the routed board "
                  "%d" % (cad_n, len(routed)))
    elif cad_a > 0 and abs(cad_a - routed_a) / max(cad_a, routed_a) > 0.05:
        bad += 1
        if verbose:
            print("      CUTOUT AREA DISAGREES: CAD %.1f mm2, routed %.1f mm2 (%.0f%%)"
                  % (cad_a, routed_a, 100 * abs(cad_a - routed_a) / max(cad_a, routed_a)))
    elif verbose:
        print("%-13s %3d cutout(s) match, %.1f mm2 vs %.1f" % ("", cad_n, cad_a, routed_a))
    return bad


def check(board, verbose=True):
    g = BG.load(board)
    w, l = g["outline_mm"]
    t = g["thickness_mm"]
    solid = _cad(board).val()
    parts = [f for f in g["footprints"]
             if f["fab"] and not f["ref"].startswith(NO_BODY_PREFIX)]
    best = None
    for c, down, plate in _plates(cq.Workplane(obj=solid), w, l):
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
                best = (misses, mirrored, plate)
    misses, mirrored, plate = best
    _faces = [pl for _c, _d, pl in _plates(cq.Workplane(obj=solid), w, l)]
    holes = _hole_check(board, plate, g, verbose,
                        through=_through_wires(plate, _faces, plate.normalAt()))
    ok = len(parts) - len(misses)
    if verbose:
        print("%-13s %3d / %3d routed parts present in the CAD%s"
              % (board, ok, len(parts), "   !! MIRRORED" if mirrored else ""))
        for ref, name, bx, by in misses:
            print("      MISSING %-6s %-44s routed at (%.2f, %.2f)" % (ref, name[:44], bx, by))
    return len(misses) + (1 if mirrored else 0) + holes


def main(argv):
    bad = 0
    for b in (argv or BOARDS):
        try:
            bad += check(b)
        except Exception as exc:                  # a board the check cannot read is a
            print("%-13s COULD NOT CHECK: %s" % (b, exc))   # finding, not a pass
            bad += 1
        if b == "ui_board":
            try:
                bad += _ui_rule_check()
            except Exception as exc:
                print("   ui_board: COULD NOT CHECK THE SPACING RULE: %s" % exc)
                bad += 1
    print("\n%s" % ("every routed part is where the CAD draws it" if not bad
                    else "*** %d DISAGREEMENT(S) BETWEEN THE CAD AND THE ROUTED BOARDS ***"
                    % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
