"""VERSION MARKS: numbers cut into a printed part, legible off any face it has.

    body = cut_mark(body, "12", at=(x, y, z), normal=(0, 0, 1), x_dir=(1, 0, 0))

Every printed part is to carry its version (user, 2026-10-13), so a part in the hand can
be matched to the model it came from. This is the mark, on trial: the fit finders
(src/test/fit_finder.py) carry it on a bed face, a side wall and a top face.

A SEVEN-SEGMENT FIGURE CUT AS A V. Each stroke is a groove whose two walls fall at 45
degrees to meet at the bottom, so its depth is half its width and it has no floor. That
one shape prints on every face without a thought for which way up the part is:

  * on TOP, anything prints;
  * on a SIDE WALL a square-cut stroke has a flat roof, a V has a 45 degree one;
  * on the BED a square-cut stroke is a ceiling one stroke wide bridged on the first
    layers, a V closes over itself a bead at a time.

Seven segments rather than a font because the chamfer is the point and a font fights it:
a glyph's strokes vary in width, so a 45 degree cut either runs out of stroke (and the
taper self-intersects) or leaves a floor in the wide parts. Segments are one width
everywhere by construction. (The font asked for, Berkeley Mono, is also not on this
machine; nothing here stops a font being tried beside it later.)

SIZES ARE IN BEADS. A stroke narrower than two beads is a slit the slicer may close;
`STROKE` is two, and the figure is five strokes tall, three wide.
"""
from __future__ import annotations

import cadquery as cq

from . import dimensions as D

STROKE = 2 * D.BEAD          # 1.6 across the mouth -> 0.8 deep
HEIGHT = 5 * STROKE          # 8.0
WIDTH = 3 * STROKE           # 4.8
GAP = STROKE                 # between figures
RIDGE = 0.04                 # the V stops this short of a knife edge (a taper to zero
                             # width is a degenerate solid)
PROUD = 0.2                  # the cutter stands this far out of the face, so the cut
                             # never shares a face with the part

#        a
#      f   b
#        g
#      e   c
#        d
SEGMENTS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
            "5": "afgcd", "6": "afgecd", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def _segment(p0, p1, stroke):
    """One stroke from p0 to p1 (centreline ends, in the face's plane): a bar with
    pointed ends reaching half a stroke past each, cut as a V below z=0."""
    (x0, y0), (x1, y1) = p0, p1
    h = stroke / 2.0
    if abs(y1 - y0) < 1e-9:                                   # along x
        pts = [(x0 - h, y0), (x0, y0 + h), (x1, y0 + h), (x1 + h, y0), (x1, y0 - h), (x0, y0 - h)]
    else:                                                     # along y
        pts = [(x0, y0 - h), (x0 + h, y0), (x0 + h, y1), (x0, y1 + h), (x0 - h, y1), (x0 - h, y0)]
    wire = cq.Workplane("XY").polyline(pts).close()
    vee = wire.extrude(h - RIDGE / 2.0, taper=45.0).mirror("XY")      # mouth at z=0, down
    return vee.union(cq.Workplane("XY").polyline(pts).close().extrude(PROUD))


def figure(ch, height=HEIGHT, width=WIDTH, stroke=STROKE):
    """The cutter for one figure, centred on the origin, cutting into -Z."""
    hx, hy = (width - stroke) / 2.0, (height - stroke) / 2.0
    ends = {"a": ((-hx, hy), (hx, hy)), "g": ((-hx, 0.0), (hx, 0.0)), "d": ((-hx, -hy), (hx, -hy)),
            "f": ((-hx, 0.0), (-hx, hy)), "b": ((hx, 0.0), (hx, hy)),
            "e": ((-hx, -hy), (-hx, 0.0)), "c": ((hx, -hy), (hx, 0.0))}
    out = None
    for s in SEGMENTS[ch]:
        seg = _segment(*ends[s], stroke=stroke)
        out = seg if out is None else out.union(seg)
    return out


def mark(text, height=HEIGHT, stroke=STROKE):
    """The cutter for a number, centred on the origin in XY, cutting into -Z."""
    width = WIDTH * height / HEIGHT
    pitch = width + GAP * height / HEIGHT
    out = None
    for i, ch in enumerate(str(text)):
        fig = figure(ch, height, width, stroke).translate(((i - (len(str(text)) - 1) / 2.0) * pitch, 0, 0))
        out = fig if out is None else out.union(fig)
    return out


def size(text, height=HEIGHT):
    """(width, height) of the face a number needs, strokes included."""
    k = height / HEIGHT
    n = len(str(text))
    return n * WIDTH * k + (n - 1) * GAP * k, height


def cut_mark(body, text, at, normal, x_dir, height=HEIGHT, stroke=STROKE):
    """`body` with `text` cut into the face through `at` whose OUTWARD normal is `normal`;
    `x_dir` is the reading direction along the face. Read from outside, it reads true --
    so a mark on a bed face is mirrored in the plan view, as it should be."""
    plane = cq.Plane(origin=cq.Vector(*at), xDir=cq.Vector(*x_dir), normal=cq.Vector(*normal))
    cutter = mark(text, height, stroke).val().moved(plane.location)
    return body.cut(cq.Workplane("XY").newObject([cutter]))
