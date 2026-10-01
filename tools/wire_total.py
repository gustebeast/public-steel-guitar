"""How much wire does one instrument need? Totalled from the drawn harness.

    py -3.12 tools/wire_total.py

WHY. elec/prices.json listed "wire" as NOT COUNTED AT ALL, with the note that "the cut
lists exist per-cable and nobody has totalled them". They do exist -- every cable in the
model is an octagonal sweep along a real polyline, and cadkit.cables.path_length calls
that polyline "the LENGTH YOU HAVE TO BUY". Nothing was adding them up.

HOW. cadkit.cables.oct_cable is the one door every cable goes through, so this wraps it,
runs the assembly, and records each call's polyline length and across-flats. That means
the total is whatever the model actually draws -- it cannot drift from the harness the
way a typed figure can, and a cable added later is counted without anyone remembering to.

WHAT IT IS NOT. Buying length, not conductor length in the strict sense: a four-conductor
bundle drawn as four paths counts four times, which is right, but slack and strip
allowance are only included where the harness model already draws them in. Treat it as
the floor of a purchase, not a cut list.
"""
from __future__ import annotations

import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cadkit.cables as cables                                    # noqa: E402

RECORDS = []
_REAL = cables.oct_cable


def _spy(pts, d):
    try:
        RECORDS.append((cables.path_length(pts), float(d)))
    except Exception:                       # never let accounting break a build
        pass
    return _REAL(pts, d)


def main():
    cables.oct_cable = _spy
    import src.wiring as wiring             # picks the patched name up at call time
    wiring.oct_cable = _spy
    import src.build as build
    for mod in (build,):
        if hasattr(mod, "oct_cable"):
            mod.oct_cable = _spy

    print("building the assembly to count its cable ...")
    comps = build.collect_components()
    print("  %d components built\n" % len(comps))

    by_d = collections.Counter()
    for mm, d in RECORDS:
        by_d[round(d, 2)] += mm
    total = sum(by_d.values())

    print("CABLE DRAWN IN ONE INSTRUMENT, by across-flats")
    print("  %-12s %10s %10s" % ("DIAMETER", "RUNS", "METRES"))
    for d, mm in sorted(by_d.items(), reverse=True):
        runs = sum(1 for _, dd in RECORDS if round(dd, 2) == d)
        print("  O%-11.2f %10d %10.2f" % (d, runs, mm / 1000.0))
    print("  %-12s %10d %10.2f" % ("TOTAL", len(RECORDS), total / 1000.0))
    print("\n  %d cable runs, %.2f m per instrument, %.1f m for a ten-instrument order"
          % (len(RECORDS), total / 1000.0, total / 100.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
