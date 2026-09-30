"""Does every cable actually REACH the parts it is declared to touch?

    py -3.12 tools/check_cable_ends.py            # all cables
    py -3.12 tools/check_cable_ends.py --max 5    # a different "far" threshold

⚠ WHY THIS EXISTS. check_overlaps is a COLLISION check: it reports two solids sharing space and
has no opinion whatever about two solids that SHOULD touch and do not. On 2026-09-29 the USB
lead carrying the Pi's travel offsets (wire_link, motor_ctrl J4 -> pi4) was found terminating
about 80 mm from the Pi, in the space the Pi occupied before the Y swap moved it -- its endpoint
was a hardcoded SP(-585.0, 20.0, -58.0). The ONLY symptom was a 1.77 mm3 graze where the lead
clipped a chassis wall on its way to nowhere, and "fixing" that graze with a millimetre nudge
would have produced a GREEN GATE over a cable connected to nothing.

WHAT IT USES. src.wiring.WIRE_OK already maps each cable to the parts it is allowed to touch --
which is very nearly the list of parts it is SUPPOSED to touch. A cable sitting far from every
one of them is not routed, whatever the overlap count says. The check is deliberately loose: it
flags DISTANCE, it does not claim to know which end lands where.

IT IS ADVISORY, NOT A GATE. Some entries in WIRE_OK are parts a cable merely passes (the trough,
a rail), so a nonzero distance there is normal. What is never normal is a cable whose distance to
EVERY declared part is large.
"""
from __future__ import annotations

import argparse
import sys

from OCP.BRepExtrema import BRepExtrema_DistShapeShape

from src.build import collect_components
from src.wiring import WIRE_OK


def _dist(a, b) -> float:
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value() if d.IsDone() else float("nan")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=float, default=2.0,
                    help="a cable is FAR from a part beyond this (mm)")
    args = ap.parse_args(argv)

    comps = {n: wp.val() for n, wp in collect_components()}
    print("assembly: %d solids" % len(comps))

    bad, checked = [], 0
    for wire, parts in sorted(WIRE_OK.items()):
        # WIRE_OK keys are base names; the assembly numbers the instances
        inst = [n for n in comps if n == wire or n.startswith(wire + "_")]
        if not inst:
            continue
        for w in inst:
            near = []
            for p in sorted(parts):
                pi = [n for n in comps if n == p or n.startswith(p + "_")]
                for q in pi:
                    try:
                        near.append((_dist(comps[w], comps[q]), q))
                    except Exception:
                        pass
            if not near:
                continue
            checked += 1
            near.sort()
            if near[0][0] > args.max:
                bad.append((near[0][0], w, near[0][1], len(near)))

    print("checked %d cable instances against their WIRE_OK parts" % checked)
    if not bad:
        print("\nevery cable reaches something it is declared to touch.")
        return 0
    bad.sort(reverse=True)
    print("\n== cables FAR from every part they are declared to touch (%d) ==" % len(bad))
    for d, w, q, n in bad:
        print("   %-24s nearest of %2d declared parts is %-22s %8.2f mm away" % (w, n, q, d))
    print("\nadvisory: a cable far from ALL of them is not routed to anything.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
