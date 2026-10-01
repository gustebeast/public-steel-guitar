"""Placement checks a board module runs BEFORE it writes its netlist.

    from placecheck import check_placement, fp_box

WHY THESE EXIST AND WHY THEY RUN HERE. The fret LED boards were the first in this
directory whose generated part and hand-placed part could be told apart in the DRC
report, and the split was total: 92 LEDs and 8 drivers laid out by a rule routed with
ZERO unconnected on the first attempt, while the twelve parts positioned from remembered
package sizes failed three separate ways across four runs. Every one of those failures
was knowable before the netlist was written, and every one of them cost a forty-minute
route to discover.

So a board module checks its own placement and refuses to emit a netlist it knows is
bad. That is the same bargain the rest of elec/ makes -- `netcheck` will not write a
netlist with a pin wired to nothing, `fab.py` will not package a board with an unsourced
part -- moved one stage earlier.

⚠ AND THE PART SIZES ARE READ, NOT TYPED. The SWPA4030 inductor's land is 4.6 x 4.5, not
the 4.0 x 4.0 its part number says; the 6-way side-entry PH's courtyard is 17.2 long.
Both of those were wrong in a first draft written from memory, and both were caught here
the moment the numbers came from the .kicad_mod instead.
"""
from __future__ import annotations

import io
import os
import re

FP_DIRS = [os.environ.get("KICAD10_FOOTPRINT_DIR")
           or r"C:\Program Files\KiCad\10.0\share\kicad\footprints",
           os.path.join(os.path.dirname(os.path.abspath(__file__)), "footprints")]

MIN_GAP = 0.30


def fp_box(fpid, layer="F.CrtYd"):
    """(w, h) of a footprint's outline on `layer`, read from the .kicad_mod.

    `F.CrtYd` is the assembly keep-out and is what parts are held apart by; `F.Fab` is
    the BODY, and is what a printed part has to clear -- see the note in check_spans."""
    lib, name = fpid.split(":")
    for d in FP_DIRS:
        path = os.path.join(d, lib + ".pretty", name + ".kicad_mod")
        if os.path.isfile(path):
            break
    else:
        raise KeyError("no footprint file for %s" % fpid)
    txt = io.open(path, encoding="utf-8").read()
    xs, ys = [], []
    for blk in re.findall(r"\(fp_(?:line|rect|poly|circle|arc)\b(.*?)\)\s*(?=\(fp_|\(pad|\)\s*$)",
                          txt, re.S):
        if layer not in blk:
            continue
        for a, b in re.findall(r"(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)", blk):
            xs.append(float(a))
            ys.append(float(b))
    if not xs:
        raise KeyError("%s has no %s" % (fpid, layer))
    return max(xs) - min(xs), max(ys) - min(ys)


def boxes(place, fps, layer="F.CrtYd"):
    """{ref: (x0, x1, y0, y1)} for a {ref: (x, y, rot)} placement."""
    out = {}
    for ref, (x, y, rot) in place.items():
        w, h = fp_box(fps[ref], layer)
        if round(rot) % 180:
            w, h = h, w
        out[ref] = (x - w / 2.0, x + w / 2.0, y - h / 2.0, y + h / 2.0)
    return out


def check_placement(name, place, fps, exempt=(), min_gap=MIN_GAP):
    """No two courtyards may come within `min_gap`. Raises with the pair and the gap.

    ⚠ IT TESTED OVERLAP AND THAT WAS NOT ENOUGH. The first version asked only whether two
    courtyards intersected, and a placement that passed it left a 0.10 mm LANE between a
    1206's courtyard and the 0402 beside it -- legal, and nowhere near enough room for the
    router to bring a stitch via down to the plane. The board came back with a via 0.1084
    mm from a GND track against a 0.127 floor, in exactly that lane. A gap of zero is a
    placement that has handed the router an impossible job and called it legal."""
    ok = {frozenset(e) for e in exempt}
    bx = boxes(place, fps)
    bad = []
    refs = sorted(bx)
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            if frozenset((a, b)) in ok:
                continue
            ax0, ax1, ay0, ay1 = bx[a]
            bx0, bx1, by0, by1 = bx[b]
            # the gap between two boxes is the LARGER of the two axis separations: they
            # clear each other if EITHER axis does
            gap = max(max(ax0, bx0) - min(ax1, bx1), max(ay0, by0) - min(ay1, by1))
            if gap < min_gap - 1e-6:
                bad.append("%s/%s %s %.2f" % (a, b, "overlap" if gap < 0 else "gap", gap))
    if bad:
        raise AssertionError(
            "%s: %d courtyard pair(s) closer than %.2f mm -- %s\nFix the placement here; "
            "DRC will report the consequence forty minutes later, somewhere else."
            % (name, len(bad), min_gap, ", ".join(bad[:8])))
    return bx


def check_spans(name, place, fps, spans, clr=0.3, axis=0, skip=()):
    """No part's BODY may sit in one of `spans` -- [(lo, hi)] of PRINTED material.

    ⚠ THE PLASTIC IS A KEEP-OUT NO DRC CAN SEE. These boards live inside printed
    channels and combs, and the print hangs walls onto their faces: the fret boards take
    a 1.60 mm light-cell wall at every fret boundary, the foot strip sits under retaining
    lips. Nothing in the PCB pipeline knows those exist -- DRC compares copper to copper,
    so a decoupling cap can be placed squarely under a wall and every electrical check
    passes. It surfaces an hour and a build later in the CAD overlap gate, as a
    part-versus-deck collision.

    It is not hypothetical: the fret boards' first placement put each driver's passives
    at xd +-4.8, and at the 9.14 mm pitch between frets 24 and 23 that is 0.05 mm INSIDE
    the wall.

    The BODY is the test, not the courtyard -- plastic may stand over copper, where it
    lands on solder mask and nothing cares, but it may not stand over a part. `axis` 0
    tests X, 1 tests Y; positions are in whatever frame `spans` is given in, so the
    caller adds its own board-to-world offset first."""
    bad = []
    for ref, (x, y, rot) in sorted(place.items()):
        if ref in skip:
            continue
        w, h = fp_box(fps[ref], "F.Fab")
        if round(rot) % 180:
            w, h = h, w
        p, size = (x, w) if axis == 0 else (y, h)
        p0, p1 = p - size / 2.0 - clr, p + size / 2.0 + clr
        for lo, hi in spans:
            if p0 < hi and p1 > lo:
                bad.append("%s at %.2f in the %.2f..%.2f wall"
                           % (ref, p, lo, hi))
    if bad:
        raise AssertionError(
            "%s: %d part(s) under printed material -- %s\nThe print hangs that onto this "
            "board's face; DRC cannot see it and the CAD gate will, an hour from now."
            % (name, len(bad), "; ".join(bad[:8])))
