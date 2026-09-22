# -*- coding: utf-8 -*-
"""Do the CODE and the BOM still describe the parts the VENDOR publishes?

A bought part's dimensions get written down three times: on the vendor's page, in
BOM.md so someone can order it, and in `src/` as the constants geometry is cut to.
Nothing made those three agree. Change a SKU and the BOM row moves while every bore,
clearance and printed tool keeps quietly sizing itself to the old part.

THE VENDOR'S PAGE IS THE SOURCE. Both other copies are answerable to it, so the
published figures are transcribed HERE, each with the URL and the date they were
read, and the check compares the code against them. Transcription is still a hand
step -- but it is ONE hand step, in one file, with a date on it, instead of numbers
drifting apart in two places that never meet.

Adding a part is one entry in PARTS. Each `fields` row is
    "vendor's own label": (published value, "module.CONSTANT" or a callable)

    py -3.12 tools/check_part_specs.py

Exit code is the number of disagreements (0 = clean).
"""

import importlib
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BOM = "BOM.md"
TOL = 0.05


class Part(object):
    def __init__(self, sku, url, read, fields, note=""):
        self.sku, self.url, self.read = sku, url, read
        self.fields, self.note = fields, note


# THE SOURCE IS THE ASSEMBLY DRAWING, NOT THE COMPONENT PAGE. This distinction is not
# pedantry -- it is the specific mistake that put a wrong jack through two joints. A
# vendor's page for 50-00041 describes the BARE BRASS CONNECTOR (O7.8 x 25.8). What is
# actually on the end of 10-02135 is that connector inside a PVC OVERMOULD, and the
# assembly drawing gives the finished part as O11 x 45. We never touch the connector.
# We only ever touch the moulding. Check against the thing you can hold.
PARTS = [
    # THE LEG'S BLIND-MATES ARE POGO BOARDS NOW (2026-09-21), and this header is the
    # bought part their pockets and pedestals are cut to. Off its own drawing
    # (YZ76615070R-08025-01), not the LCSC listing's attributes, which carry no stroke.
    Part("C54799748", "https://datasheet.lcsc.com/datasheet/pdf/"
                      "7aab94cc3f2faa41c25b1234644cb837.pdf?productCode=C54799748",
         "2026-09-21",
         {
             "pin pitch":            (2.5, "src.leg_pogo.RA_PITCH"),
             "housing length":       (11.0, "src.leg_pogo.RA_BODY_S"),
             "housing thickness":    (2.5, "src.leg_pogo.RA_BODY_T"),
             "free height":          (5.5, "src.leg_pogo.RA_FREE"),
             "working height":       (4.0, "src.leg_pogo.RA_WORK"),
             "plunger":              (1.0, "src.leg_pogo.RA_PLUNGER_D"),
             "rated DC volts":       (12.0, "src.leg_pogo.RA_V"),
             "force at working, gf": (120.0, "src.leg_pogo.RA_GF"),
         },
         "the right-angle 1 x 4 spring-pin header on both male boards (its -01 sibling "
         "C5296819 is the same drawing)"),
]

# SUPERSEDED 2026-09-21 -- the TRRS cable the leg used before the pogo boards. Its
# ASSEMBLY drawing (not the component pages) was the source, and that distinction put a
# wrong jack through two joints once:
#   10-02135  cable O3.8 x 915, bend R 22.8; plug overmould O6.1, 14 bare barrel, 23.3
#             overall; jack overmould O11 x 45 overall

# The bare connectors, kept for reference ONLY. They are what is INSIDE the mouldings
# above; nothing in the model should be cut to them.
#   50-00397  plug, O3.5 x L20.7  (14 of it is the exposed barrel)
#   50-00041  jack, O7.8 x L25.8


def _resolve(ref):
    if callable(ref):
        return ref()
    mod, _, name = ref.rpartition(".")
    return getattr(importlib.import_module(mod), name)


def _bom_text():
    try:
        return io.open(BOM, encoding="utf-8").read()
    except IOError:
        return ""


def main():
    bom = _bom_text()
    bad = 0
    for part in PARTS:
        print("%s  (%s, read %s)" % (part.sku, part.url, part.read))
        if part.note:
            print("  %s" % part.note)
        if bom and not re.search(re.escape(part.sku), bom):
            print("  <<< the BOM does not mention this SKU at all")
            bad += 1
        for label in sorted(part.fields):
            pub, ref = part.fields[label]
            try:
                got = _resolve(ref)
            except Exception as exc:
                print("  %-26s vendor %8.2f   code MISSING (%s: %s)"
                      % (label, pub, ref, exc))
                bad += 1
                continue
            ok = abs(float(got) - pub) < TOL
            bad += 0 if ok else 1
            where = ("(derived)" if callable(ref)
                     else ref.replace("src.", ""))
            print("  %-26s vendor %8.2f   code %8.2f   %-28s %s"
                  % (label, pub, got, where, "ok" if ok else "<<< DISAGREE"))
        print()
    print("%d disagreement(s)" % bad)
    return bad


if __name__ == "__main__":
    sys.exit(main())
