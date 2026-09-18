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
    Part("10-02135", "https://tensility.s3.us-west-2.amazonaws.com/imports/"
                     "product_spec_sheets/10-02135.pdf", "2026-09-18",
         {
             "cable OD":               (3.8, "src.leg_trrs.CABLE_D"),
             "cable length":           (915.0, "src.leg_trrs.CABLE_LEN"),
             "bend radius":            (22.8, "src.leg_trrs.CABLE_BEND_R"),
             # the PLUG end, as moulded
             "plug overmould OD":      (6.1, "src.leg_trrs.PLUG_D"),
             "plug bare barrel":       (14.0, "src.leg_trrs.BARREL_L"),
             "plug overall":           (23.3, lambda: __import__(
                 "src.leg_trrs", fromlist=["e"]).BARREL_L
                 + __import__("src.leg_trrs", fromlist=["e"]).PLUG_L),
             # ...and the JACK end, likewise
             "jack overmould OD":      (11.0, "src.leg_trrs.JACK_D"),
             "jack overall":           (45.0, "src.leg_trrs.JACK_L"),
         },
         "the FINISHED cable, off its own assembly drawing. Every figure here is the "
         "moulded part, which is the only part the instrument ever sees"),
]

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
