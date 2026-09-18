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


PARTS = [
    Part("10-02135", "https://www.tensility.com/products/10-02135", "2026-09-18",
         {
             # the vendor's own label -> (what it publishes, where the code keeps it)
             "wire outer diameter": (3.8, "src.leg_trrs.CABLE_D"),
             "cable length":        (915.0, "src.leg_trrs.CABLE_LEN"),
             "bend radius":         (22.8, "src.leg_trrs.CABLE_BEND_R"),
         },
         "the leg's whole TRRS lead. PVC jacket, spiral + foil shield -- the foil is "
         "why the bend radius is as large as it is"),
    Part("50-00041", "https://www.tensility.com/products/50-00041", "2026-09-18",
         {
             "connector outer diameter": (7.8, "src.leg_trrs.JACK_D"),
             "connector length":         (25.8, "src.leg_trrs.JACK_L"),
         },
         "the cable's JACK end (its connector 2)"),
    Part("50-00397", "https://www.tensility.com/products/50-00397", "2026-09-18",
         {
             "connector outer diameter": (3.5, "src.leg_trrs.BARREL_D"),
             "connector length":         (20.7, "src.leg_trrs.BARREL_L"),
         },
         "the cable's PLUG end (its connector 1). NOTE the vendor's 'connector length' "
         "is the CONNECTOR, not the finished moulded end -- the moulding these are "
         "assembled into is not a published dimension"),
]


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
            print("  %-26s vendor %8.2f   code %8.2f   %-26s %s"
                  % (label, pub, got, ref.rpartition(".")[0].replace("src.", "") + "."
                     + ref.rpartition(".")[2], "ok" if ok else "<<< DISAGREE"))
        print()
    print("%d disagreement(s)" % bad)
    return bad


if __name__ == "__main__":
    sys.exit(main())
