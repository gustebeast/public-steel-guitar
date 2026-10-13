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

TWO FACES OF TYPE ARE ON TRIAL, and the print decides between them:

  * SEVEN SEGMENTS (`mark`): one stroke width everywhere by construction, so the V is
    exact and the stroke can be set in beads -- two of them in a figure 8 mm tall.
  * THE INSTRUMENT'S OWN FONT (`font_mark`): Rennie Mackintosh PSG, the face on the
    boards and the display. Its strokes are 0.11 of its figure height -- 0.75 mm in a
    7 mm figure, ONE bead at 7.3 and two only at 14.5 -- so on a small part it is a
    hairline where the segments are a groove. It is cut the same way, each glyph tapered
    at 45 degrees as deep as its stroke allows (FONT_DEPTH; a V that deep nearly closes).

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


def cut_groove(body, at, normal, along, length, stroke=STROKE):
    """`body` with ONE V stroke cut into the face through `at` (outward `normal`),
    `length` long tip to tip and running `along` the face: a tally mark, or a segment of
    anything else, that prints on any face for the same reason a figure does."""
    half = max(0.0, length / 2.0 - stroke / 2.0)
    plane = cq.Plane(origin=cq.Vector(*at), xDir=cq.Vector(*along), normal=cq.Vector(*normal))
    cutter = _segment((-half, 0.0), (half, 0.0), stroke).val().moved(plane.location)
    return body.cut(cq.Workplane("XY").newObject([cutter]))


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


FONT_STROKE = 0.11           # the font's stroke over its figure height (measured: 2A/P)
FONT_FIGURE = 0.68           # ...and its figure height over the font size
FONT_DEPTH = 0.45            # of the stroke: a 45 deg V closes at 0.5


def _font():
    from . import board_geom as BG
    return BG._FONT


def font_mark(text, height=HEIGHT):
    """The cutter for `text` in the instrument's font, figures `height` tall, centred on
    the origin in XY and cutting into -Z; None if the font is not on this machine."""
    path = _font()
    if not path:
        return None
    depth = FONT_DEPTH * FONT_STROKE * height
    flat = cq.Workplane("XY").text(str(text), height / FONT_FIGURE, 1.0, fontPath=path,
                                   halign="center", valign="center")
    out = None
    for f in flat.faces("<Z").vals():
        prism = f.Area() * depth
        vee = None
        # the taper's sense follows the wire's winding, which a font does not promise:
        # take whichever way NARROWS with depth
        for taper in (45.0, -45.0):
            try:
                cand = cq.Solid.extrudeLinear(f.outerWire(), f.innerWires(),
                                              cq.Vector(0, 0, depth), taper=taper)
            except Exception:
                continue
            if cand.isValid() and 0.0 < cand.Volume() < prism:
                vee = cand
                break
        if vee is None:                    # no clean taper: a square cut that shallow
            vee = cq.Solid.extrudeLinear(f.outerWire(), f.innerWires(), cq.Vector(0, 0, depth))
        piece = (cq.Workplane("XY").newObject([vee]).mirror("XY")
                 .union(cq.Workplane("XY").newObject(
                     [cq.Solid.extrudeLinear(f.outerWire(), f.innerWires(),
                                             cq.Vector(0, 0, PROUD))])))
        out = piece if out is None else out.union(piece)
    return out


def cut_mark(body, text, at, normal, x_dir, height=HEIGHT, stroke=STROKE, font=False):
    """`body` with `text` cut into the face through `at` whose OUTWARD normal is `normal`;
    `x_dir` is the reading direction along the face. Read from outside, it reads true --
    so a mark on a bed face is mirrored in the plan view, as it should be. `font=True`
    cuts it in the instrument's font instead of segments (and cuts nothing, returning
    the body as it came, on a machine without the font)."""
    plane = cq.Plane(origin=cq.Vector(*at), xDir=cq.Vector(*x_dir), normal=cq.Vector(*normal))
    cutter = font_mark(text, height) if font else mark(text, height, stroke)
    if cutter is None:
        return body
    return body.cut(cq.Workplane("XY").newObject([cutter.val().moved(plane.location)]))
