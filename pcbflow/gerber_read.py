"""Read a package's gerbers with a reader that is not KiCad's, and say what is in them.

    py -3.12 cadkit/pcbflow/gerber_read.py <gerber dir>      # -> json on stdout

{file: {"flash": n, "region": n, "line": n, "arc": n, "bbox": [x0, y0, x1, y1] | null}}

⚠ M37 ASKS FOR THE PACKAGE TO BE OPENED IN AN INDEPENDENT VIEWER (2026-11-10), and the
point of "independent" is that the program which wrote the files is not the one saying
they are right. gerbonara is a separate RS-274X implementation; fab_package compares its
counts with the board's own -- on every copper layer the flashes are the board's flashed
pads plus its vias (output_panel: F.Cu 1099 = 665 + 434, In1 / In2 / B.Cu 479 = 45 + 434),
and the outline's extent is the board edge's -- so a layer that lost its pads, a stale
file, or an outline from another board shows as a count, not as a picture somebody has
to remember to look at. Runs under an ordinary Python (gerbonara is not in KiCad's).
"""
import json
import os
import sys
import warnings


def read(d):
    import gerbonara
    from gerbonara.graphic_objects import Arc, Flash, Line, Region
    out = {}
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith((".gtl", ".gbl", ".gm1")) and not fn.lower()[-3:-1] == ".g":
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g = gerbonara.rs274x.GerberFile.open(os.path.join(d, fn))
        c = {"flash": 0, "region": 0, "line": 0, "arc": 0}
        for o in g.objects:
            if isinstance(o, Flash):
                c["flash"] += 1
            elif isinstance(o, Region):
                c["region"] += 1
            elif isinstance(o, Line):
                c["line"] += 1
            elif isinstance(o, Arc):
                c["arc"] += 1
        bb = g.bounding_box(unit=gerbonara.utils.MM)
        c["bbox"] = [bb[0][0], bb[0][1], bb[1][0], bb[1][1]] if bb else None
        out[fn] = c
    return out


if __name__ == "__main__":
    json.dump(read(sys.argv[1]), sys.stdout)
