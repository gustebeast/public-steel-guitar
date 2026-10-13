"""FIT FINDERS, ROUND 2: one PETG-GF plate, laid out so a token sits beside its own cell.

    py -3.12 -m src.test.fit_round2            # the table: what each number is
    py -3.12 -m src.test.fit_round2 --export   # ...and write src/test/test_fit2_plate.step

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
  OCTAGON   1-5  0.10 .. 0.40 at the drawn depth. Both its halves print standing, like the
                 endplate's socket, so the drawn 0.30 is expected to be loose.

THE PLATE IS ONE FILE. Every piece is already turned onto its bed face and set down where
it prints: each strip with its tokens in a column beside it, token N level with cell N,
both numbered. Import the one STEP and do not let the slicer re-arrange it.
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
                 (0.15, 0.30, 0.0), (0.20, 0.30, 0.0)],
    "octagon": [(0.10, 0.60, 0.0), (0.15, 0.60, 0.0), (0.20, 0.60, 0.0),
                (0.30, 0.60, 0.0), (0.40, 0.60, 0.0)],
}


def finders():
    """Round 1's seam, endplate and octagon finders, re-stepped."""
    out = []
    for f in F.finders():
        if f.name in STEPS:
            f.deltas = tuple(STEPS[f.name])
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


def _group(f):
    """One joint as it prints: [(name, solid)] with the strip standing at x >= 0 and each
    token beside it, level with its own cell; and the group's width in X."""
    from src.version_mark import cut_mark
    pairs = [f.make(k, d) for k, d in enumerate(f.deltas)]
    _tokens, strip = f.build()
    strip = _rot(strip, f.cell_up)
    sb = strip.val().BoundingBox()
    strip = strip.translate((-sb.xmin, 0.0, -sb.zmin))
    out = [("fit2_%s_strip" % f.name, strip.val())]
    x_tok = sb.xlen + BESIDE
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
        out.append(("fit2_%s_token_%d" % (f.name, k + 1), t.val()))
    return out, width


def plate():
    """[(name, solid)] for the whole plate, bed at z = 0: the three joints side by side,
    then the bass stack's slot as the keyhead now cuts it (open, for round 1's tokens)."""
    out, x = [], 0.0
    for f in finders():
        grp, w = _group(f)
        y0 = min(s.BoundingBox().ymin for _n, s in grp)
        out += [(n, s.moved(cq.Location(cq.Vector(x, -y0, 0.0)))) for n, s in grp]
        x += w + BETWEEN
    stack = [f for f in F.finders() if f.name == "insert_stack"][0]
    _tokens, strip = stack.build()
    strip = _rot(strip, stack.cell_up)
    b = strip.val().BoundingBox()
    out.append(("fit2_stack_strip", strip.val().moved(cq.Location(cq.Vector(x - b.xmin, -b.ymin, -b.zmin)))))
    # a solid that is valid as drawn can fail the checker once it is turned (a
    # tolerance, not a shape: the volume does not move); ShapeFix settles it
    return [(n, sh if sh.isValid() else sh.fix()) for n, sh in out]


def assembly(origin=(-560.0, 330.0, 160.0)):
    """[(name, Workplane)] for the scratch view: the plate as it prints, beside round 1."""
    return [("test_" + n, cq.Workplane("XY").newObject([s]).translate(origin)) for n, s in plate()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", action="store_true", help="write src/test/test_fit2_plate.step")
    a = ap.parse_args(argv)
    print("number  side / depth clearance, corners")
    for name, steps in STEPS.items():
        print(name)
        for k, (c, bc, r) in enumerate(steps):
            print("   %d    %.2f / %.2f  %s" % (k + 1, c, bc, "corners r %.1f" % r if r else "sharp"))
    pl = plate()
    lo = [min(s.BoundingBox().__getattribute__(a_) for _n, s in pl) for a_ in ("xmin", "ymin", "zmin")]
    hi = [max(s.BoundingBox().__getattribute__(a_) for _n, s in pl) for a_ in ("xmax", "ymax", "zmax")]
    print("\n%d pieces, %.1f cm3, plate %.1f x %.1f, %.1f tall, bed at z %.2f" % (
        len(pl), sum(s.Volume() for _n, s in pl) / 1000.0,
        hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], lo[2]))
    bad = [n for n, s in pl if not s.isValid() or len(s.Solids()) != 1]
    print("every piece one valid solid" if not bad else "NOT ONE VALID SOLID: %s" % ", ".join(bad))
    if a.export:
        from cadkit.step_export import export_step
        path = HERE / "test_fit2_plate.step"
        export_step(cq.Workplane("XY").newObject([cq.Compound.makeCompound([s for _n, s in pl])]),
                    str(path))
        print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
