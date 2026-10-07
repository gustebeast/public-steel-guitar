"""The board-lettering font, made from the purchased one: elec/fonts/, never committed.

    py -3.12 tools/make_silk_font.py "<path to Rennie Mackintosh ITC Bold.otf>"

WHY A MODIFIED COPY. The font's underscore slot holds an ornament (a small T over an O)
and every net name on the boards has an underscore in it. KiCad lays lettering out as
text in an installed font and can swap one character for another but cannot move a
glyph, so the only place an underscore can be put right for the real silkscreen is in
the font. This writes a copy whose underscore is the font's own hyphen bar, lowered to
sit just under the baseline, and changes nothing else.

The copy carries its own family name, so it installs beside the original without
shadowing it and a board that names it cannot silently get the unmodified face. The
font is licensed: neither file belongs in the repository (elec/fonts/ is ignored).
"""
from __future__ import annotations

import os
import sys

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAMILY = "Rennie Mackintosh PSG"          # what KiCad is told to use
STYLE = "Bold"
OUT = os.path.join(ROOT, "elec", "fonts", "RennieMackintoshPSG-Bold.otf")
BAR_TOP = -22                             # font units: the bar's top, just under the baseline


def main(src):
    f = TTFont(src)
    gs = f.getGlyphSet()
    bp = BoundsPen(gs)
    gs["hyphen"].draw(bp)
    x0, y0, x1, y1 = bp.bounds
    dy = BAR_TOP - y1

    cff = f["CFF "].cff
    top = cff.topDictIndex[0]
    pen = T2CharStringPen(gs["hyphen"].width, gs)
    gs["hyphen"].draw(TransformPen(pen, (1, 0, 0, 1, 0, dy)))
    old = top.CharStrings["underscore"]
    new = pen.getCharString(private=old.private, globalSubrs=old.globalSubrs)
    top.CharStrings["underscore"] = new
    f["hmtx"]["underscore"] = (gs["hyphen"].width, f["hmtx"]["hyphen"][1])

    # its own name everywhere a program looks one up; the copyright notice stays
    ps = (FAMILY + "-" + STYLE).replace(" ", "")
    for rec in f["name"].names:
        if rec.nameID in (1, 16):
            rec.string = FAMILY
        elif rec.nameID in (2, 17):
            rec.string = STYLE
        elif rec.nameID == 3:
            rec.string = FAMILY + " " + STYLE + ": underscore redrawn"
        elif rec.nameID == 4:
            rec.string = FAMILY + " " + STYLE
        elif rec.nameID == 6:
            rec.string = ps
    cff.fontNames[0] = ps
    top.FullName = FAMILY + " " + STYLE
    top.FamilyName = FAMILY

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    f.save(OUT)

    g = TTFont(OUT)
    bp = BoundsPen(g.getGlyphSet())
    g.getGlyphSet()["underscore"].draw(bp)
    assert bp.bounds == (x0, y0 + dy, x1, y1 + dy), bp.bounds
    print("wrote %s\n  family %r, underscore bar %s (was the ornament), advance %d"
          % (OUT, g["name"].getDebugName(4), bp.bounds, g["hmtx"]["underscore"][0]))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
