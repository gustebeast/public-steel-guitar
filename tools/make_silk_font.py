"""The board-lettering font, made from the purchased one: elec/fonts/, never committed.

    py -3.12 tools/make_silk_font.py "<path to Rennie Mackintosh ITC Bold.otf>"

WHY A MODIFIED COPY. Two of the font's slots hold ornaments where the boards need plain
signs: the underscore is a small T over an O, and the plus is a TH ligature, so "+5V"
plots as "TH5V". Every net name has an underscore and ten of the fifteen boards print a
rail. KiCad lays lettering out as text in an installed font and can swap one character
for another but cannot move or draw a glyph, so the only place these can be put right
for the real silkscreen is in the font. This writes a copy whose underscore is the
font's own hyphen bar, lowered to sit just under the baseline, and whose plus is a plain
cross of the font's stem weight, and changes nothing else.

The slot names say nothing about what is drawn in them (both ornaments sit under the
right names), so a character is only known good once it has been LOOKED at.

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
PLUS_ARM = 180                            # centre to arm tip: a 360 cross, about half a capital
PLUS_ADV = 450                            # advance, near the digits'


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

    # the plus: one cross outline, its bars as thick as the font's vertical stems (never
    # thinner than the underscore's bar, which is what sets the smallest printable size),
    # centred on the capital height
    t = max(int(getattr(top.Private, "StdVW", 0)), int(round(y1 - y0))) / 2.0
    cx, cy, r = PLUS_ADV / 2.0, f["OS/2"].sCapHeight / 2.0, PLUS_ARM
    cross = [(cx - t, cy - r), (cx + t, cy - r), (cx + t, cy - t), (cx + r, cy - t),
             (cx + r, cy + t), (cx + t, cy + t), (cx + t, cy + r), (cx - t, cy + r),
             (cx - t, cy + t), (cx - r, cy + t), (cx - r, cy - t), (cx - t, cy - t)]
    pen = T2CharStringPen(PLUS_ADV, gs)
    pen.moveTo(cross[0])
    for q in cross[1:]:
        pen.lineTo(q)
    pen.closePath()
    oldp = top.CharStrings["plus"]
    top.CharStrings["plus"] = pen.getCharString(private=oldp.private,
                                                globalSubrs=oldp.globalSubrs)
    f["hmtx"]["plus"] = (PLUS_ADV, int(cx - r))

    # its own name everywhere a program looks one up; the copyright notice stays
    ps = (FAMILY + "-" + STYLE).replace(" ", "")
    for rec in f["name"].names:
        if rec.nameID in (1, 16):
            rec.string = FAMILY
        elif rec.nameID in (2, 17):
            rec.string = STYLE
        elif rec.nameID == 3:
            rec.string = FAMILY + " " + STYLE + ": underscore and plus redrawn"
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
    bp = BoundsPen(g.getGlyphSet())
    g.getGlyphSet()["plus"].draw(bp)
    print("  plus %s, bars %.0f thick, advance %d" % (bp.bounds, 2 * t, g["hmtx"]["plus"][0]))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
