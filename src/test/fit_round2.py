"""FIT FINDERS, ROUND 2: one PETG-GF plate, laid out so a token sits beside its own cell.

    py -3.12 -m src.test.fit_round2            # the table: what each number is
    py -3.12 -m src.test.fit_round2 --export   # ...and write src/test/test_fit2_plate_*.step

ROUND 1 (src/test/fit_finder.py, printed 2026-10-13, all in PETG-GF) said, by feel:

  * SEAM (both halves print with the profile flat on the bed), drawn 0.15 side / 0.30
    depth: 0.05-0.15 would not enter, 0.20-0.25 only with force. It BINDS AT THE NECK,
    on the profile's corners; the flat under the head has room to spare.
  * ENDPLATE (the tenon flat, the socket standing through the layers), drawn 0.30 / 0.60:
    0.30-0.40 wobble, 0.25 good, 0.20 best. The spare room is at the SIDES of the head.
  * OCTAGON: never tried -- its strip's skin closed every mouth.
  * the STACK slot's 18.3 roof bridge did not print; the keyhead now leaves it open.

So one clearance pair per joint is not one fit: it depends on which way the profile
prints, and on its corners. ROUND 2 TRIES THEORIES, NOT JUST SIZES (user: "export those
as different numbers"). A step here is (side, depth, corner radius) named outright:

  SEAM      1-3  sharp corners, the side opened up alone (0.25 / 0.35 / 0.45), depth held
            4-6  the SAME profile with every corner drawn at 0.4 -- half a bead, what the
                 nozzle rounds a corner to anyway -- at 0.15 (today's), 0.25, 0.35.
                 If 4 goes in where round 1's 0.15 would not, the corners were the bind
                 and the joint wants a radius, not a bigger gap.
  ENDPLATE  1-3  tighter than round 1 reached (0.10 / 0.15 / 0.20), depth as round 1's best
            4-5  0.15 and 0.20 again with the DEPTH brought down to 0.30: is the wobble
                 the side gap or the depth gap?
            6-8  1-3 again with every corner drawn at 0.4 (user, 2026-10-13: "have our
                 design match what is printed ... any joints that rely on the printer to
                 make a sharp turn"). The tenon prints with its profile flat on the bed,
                 so the nozzle turns its corners; the socket is drawn to the same radius
                 so the pair still mates.
  OCTAGON   1-5  0.10 .. 0.40 at the drawn depth. Both its halves print standing, like the
                 endplate's socket, so the drawn 0.30 is expected to be loose.

WHICH PROFILES THE NOZZLE TURNS. Only a profile lying flat on the bed has its corners
made by the nozzle changing direction: both halves of the SEAM, and the ENDPLATE's
tenon. The deck, the octagon and the inserts all print with the profile standing, their
corners made by one layer ending short of the next, and get no radius for that reason
(the deck's 4-6 carry one anyway, as a second theory for its tight first step).

  DECK      1-3  the side opened (0.20 / 0.25 / 0.30) with the depth held at 0.20
            4-6  corners drawn at 0.4, at 0.15 / 0.20 / 0.25
  INSERT A  1-5  the slot at 0.20 .. 0.40 all round; one insert tries all five
  STACK     1-5  0.15 .. 0.35 between two bass inserts, in the keyhead's slot as it is
                 now cut: open between two lips, no bridge

TWO PLATES, ONE FILE EACH (user, 2026-10-13: print the PETG-GF first, learn from the
PETG-GF to PETG-GF joints, and only then decide whether the PCTG is worth printing or
the sockets want another round). test_fit2_plate_petg_gf.step has everything that is
PETG-GF: the three all-GF joints whole, and the SOCKET strips of the deck, insert A and
the stack. test_fit2_plate_pctg.step has those three joints' tenons. Every piece is
already turned onto its bed face and set down where it prints -- each strip with its
tokens in a column beside it, token N level with cell N, both numbered. Import the one
STEP and do not let the slicer re-arrange it.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import cadquery as cq

from . import fit_finder as F

HERE = pathlib.Path(__file__).resolve().parent
R = 0.4                      # the drawn corner: half a bead
BESIDE = 3.0                 # air between a strip and its tokens
BETWEEN = 8.0                # ...and between one joint's group and the next

STEPS = {
    "seam": [(0.25, 0.30, 0.0), (0.35, 0.30, 0.0), (0.45, 0.30, 0.0),
             (0.15, 0.30, R), (0.25, 0.30, R), (0.35, 0.30, R)],
    "endplate": [(0.10, 0.50, 0.0), (0.15, 0.50, 0.0), (0.20, 0.50, 0.0),
                 (0.15, 0.30, 0.0), (0.20, 0.30, 0.0),
                 (0.10, 0.50, R), (0.15, 0.50, R), (0.20, 0.50, R)],
    "octagon": [(0.10, 0.60, 0.0), (0.15, 0.60, 0.0), (0.20, 0.60, 0.0),
                (0.30, 0.60, 0.0), (0.40, 0.60, 0.0)],
    "deck": [(0.20, 0.20, 0.0), (0.25, 0.20, 0.0), (0.30, 0.20, 0.0),
             (0.15, 0.20, R), (0.20, 0.20, R), (0.25, 0.20, R)],
}
# THE TWO-FILAMENT JOINTS. Their sockets are PETG-GF and go on that plate; their tenons
# are PCTG and go on the other, so each of these is split across the two files.
SPLIT = ("deck",)
INSERT_A = (0.0, 0.05, 0.10, 0.15, 0.20)       # added to the slot's own 0.20: 0.20 .. 0.40
STACK = (0.15, 0.20, 0.25, 0.30, 0.35)         # the gap between two bass inserts


def finders(steps=None):
    """Round 1's finders, re-stepped from `steps` (this round's STEPS by default); only
    the joints it names."""
    steps = STEPS if steps is None else steps
    out = []
    for f in F.finders():
        if f.name in steps:
            f.deltas = tuple(steps[f.name])
            out.append(f)
    return out


def _rot(w, up):
    """`w` turned so `up` is +Z -- the rotation alone, about the origin, so a point
    turned with it stays where the solid's own geometry went."""
    from cadkit.orientation import PrintOrientation as PO
    rot = PO.from_build_dir(up, "the build direction of the half it stands for").rot
    if rot == "flip":
        rot = ((1.0, 0.0, 0.0), 180.0)
    if rot is None:
        return w
    axis, deg = rot
    return w.rotate((0.0, 0.0, 0.0), tuple(axis), deg)


def _group(f, which="both", tag="fit2"):
    """One joint as it prints: [(name, solid)] with the strip standing at x >= 0 and each
    token beside it, level with its own cell; and the group's width in X. `which` keeps
    only the "strip" or only the "tokens" (which then start at x = 0), for a joint whose
    halves are different filaments and print on different plates."""
    from src.version_mark import cut_mark
    pairs = [f.make(k, d) for k, d in enumerate(f.deltas)]
    _tokens, strip = f.build()
    strip = _rot(strip, f.cell_up)
    sb = strip.val().BoundingBox()
    strip = strip.translate((-sb.xmin, 0.0, -sb.zmin))
    out = [("%s_%s_strip" % (tag, f.name), strip.val())] if which != "tokens" else []
    if which == "strip":
        return out, sb.xlen
    x_tok = sb.xlen + BESIDE if which == "both" else 0.0
    width = 0.0
    for k, (tok, _cell) in enumerate(pairs):
        if f.token_mark:
            at, n, xd = f.token_mark[:3]
            tok = cut_mark(tok, k + 1, at, n, xd, **(f.token_mark[3] if len(f.token_mark) > 3 else {}))
        # where cell k's middle went when the strip was turned: its y is the token's
        cy = _rot(cq.Workplane("XY").box(0.2, 0.2, 0.2).translate((F.L / 2.0, k * f.pitch, 0.0)),
                  f.cell_up).val().Center().y
        t = _rot(tok, f.token_up)
        tb = t.val().BoundingBox()
        t = t.translate((x_tok - tb.xmin, cy - (tb.ymin + tb.ymax) / 2.0, -tb.zmin))
        width = max(width, x_tok + tb.xlen)
        out.append(("%s_%s_token_%d" % (tag, f.name, k + 1), t.val()))
    return out, width


def _set_down(wp, up, x):
    """A finished piece (a strip, or a row of tokens) turned onto its bed face and set
    down with its corner at (x, 0); and its width in X."""
    w = _rot(wp, up)
    b = w.val().BoundingBox()
    return w.val().moved(cq.Location(cq.Vector(x - b.xmin, -b.ymin, -b.zmin))), b.xlen


def _inserts():
    """The two insert finders, re-stepped: (insert A, the bass stack)."""
    fs = {f.name: f for f in F.finders()}
    fs["insert_a"].deltas = INSERT_A
    return fs["insert_a"], fs["insert_stack"]


def plate(filament="petg-gf", steps=None, tag="fit2", inserts=True):
    """[(name, solid)] for one plate, bed at z = 0.

    "petg-gf": the three joints that are PETG-GF on both sides, each strip with its
    tokens beside it; then the SOCKET strips of the two-filament joints -- the deck's
    rail, insert A's slots, the bass stack's slot as the keyhead now cuts it.
    "pctg": those joints' other halves -- the deck's tongues, the one insert A, and the
    five sets of three bass inserts."""
    out, x = [], 0.0
    ins_a, stack = _inserts()
    saved, F.STACK_STEPS = F.STACK_STEPS, STACK       # the stack finder reads its steps here
    try:
        for f in finders(steps):
            split = f.name in SPLIT
            if split != (filament == "pctg") and not (split and filament == "petg-gf"):
                continue
            which = "both" if not split else ("tokens" if filament == "pctg" else "strip")
            grp, w = _group(f, which, tag)
            y0 = min(sh.BoundingBox().ymin for _n, sh in grp)
            out += [(n, sh.moved(cq.Location(cq.Vector(x, -y0, 0.0)))) for n, sh in grp]
            x += w + BETWEEN
        for f in (ins_a, stack) if inserts else ():
            tokens, strip = f.build()
            if filament == "petg-gf":
                sh, w = _set_down(strip, f.cell_up, x)
                out.append(("%s_%s_strip" % (tag, f.name), sh))
            else:
                row, w = _set_down(tokens, f.token_up, x)
                out += [("%s_%s_token_%d" % (tag, f.name, k + 1), t)
                        for k, t in enumerate(row.Solids())]
            x += w + BETWEEN
    finally:
        F.STACK_STEPS = saved
    # a solid that is valid as drawn can fail the checker once it is turned (a
    # tolerance, not a shape: the volume does not move); ShapeFix settles it
    return [(n, sh if sh.isValid() else sh.fix()) for n, sh in out]


def assembly(origin=(-560.0, 330.0, 160.0)):
    """[(name, Workplane)] for the scratch view: both plates as they print, beside round 1."""
    out = []
    for j, fil in enumerate(("petg-gf", "pctg")):
        o = (origin[0], origin[1] + j * 110.0, origin[2])
        out += [("test_" + n.replace("fit2_", "fit2_%s_" % fil.replace("-", "")),
                 cq.Workplane("XY").newObject([s]).translate(o)) for n, s in plate(fil)]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", action="store_true", help="write src/test/test_fit2_*.step")
    a = ap.parse_args(argv)
    print("number  side / depth clearance, corners")
    for name, steps in STEPS.items():
        print(name)
        for k, (c, bc, r) in enumerate(steps):
            print("   %d    %.2f / %.2f  %s" % (k + 1, c, bc, "corners r %.1f" % r if r else "sharp"))
    from src import nut_block as NB
    print("insert_a  (one insert, five slots)")
    for k, d in enumerate(INSERT_A):
        print("   %d    %.2f all round" % (k + 1, NB._clr(6) + d))
    print("insert_stack  (one slot, five sets of three)")
    for k, st in enumerate(STACK):
        print("   %d    %.2f between two inserts" % (k + 1, st))
    for fil in ("petg-gf", "pctg"):
        pl = plate(fil)
        lo = [min(getattr(s.BoundingBox(), a_) for _n, s in pl) for a_ in ("xmin", "ymin", "zmin")]
        hi = [max(getattr(s.BoundingBox(), a_) for _n, s in pl) for a_ in ("xmax", "ymax", "zmax")]
        print("\n%s plate: %d pieces, %.1f cm3, %.1f x %.1f, %.1f tall, bed at z %.2f" % (
            fil, len(pl), sum(s.Volume() for _n, s in pl) / 1000.0,
            hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], lo[2]))
        bad = [n for n, s in pl if not s.isValid() or len(s.Solids()) != 1]
        print("every piece one valid solid" if not bad else "NOT ONE VALID SOLID: %s" % ", ".join(bad))
        if a.export:
            from cadkit.step_export import export_step
            path = HERE / ("test_fit2_plate_%s.step" % fil.replace("-", "_"))
            export_step(cq.Workplane("XY").newObject(
                [cq.Compound.makeCompound([s for _n, s in pl])]), str(path))
            print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
