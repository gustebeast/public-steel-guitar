# -*- coding: utf-8 -*-
"""Does the CODE still describe the cable the BOM says we are buying?

The leg's TRRS lead is a bought part, and its four measurements -- cable OD, jack
body, jack length, plug length -- are restated in two places: the BOM row that says
what to order, and `src/leg_trrs.py` that cuts geometry to fit it. Nothing made those
two agree. Change the SKU and the BOM row moves while every bore, every clearance and
the whole coil mandrel keep quietly sizing themselves to the old part.

That matters more than the usual duplicated-constant complaint, because the mandrel
is cut to the cable's OD end to end: the barrel, the sleeve bore, the slit width, the
turn pitch and the coil's mean diameter all derive from `leg_trrs.CABLE_D`. A tool
built for the wrong cable is a tool that sets the wrong coil.

This reads the numbers back out of the BOM row and compares them. It is deliberately
blunt about parsing -- if the row is reworded so the numbers cannot be found, that is
a FAILURE, not a pass, because a spec you cannot read is not a spec you can check.

    py -3.12 tools/check_cable_spec.py

Exit code is the number of disagreements (0 = clean).
"""

import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import leg_trrs as LT                                     # noqa: E402

SKU = "10-02135"
BOM = "BOM.md"


def _row():
    """The BOM line that specifies the cable."""
    text = io.open(BOM, encoding="utf-8").read()
    for line in text.splitlines():
        if SKU in line and line.lstrip().startswith("|"):
            return line
    return None


def main():
    row = _row()
    if row is None:
        print("FAIL  no BOM row mentions %s -- has the cable been re-sourced?" % SKU)
        return 1

    # what the row claims, in its own words
    claims = {}
    m = re.search(r"cable\s*[ØO]\s*([0-9]+(?:\.[0-9]+)?)", row)
    if m:
        claims["cable OD"] = (float(m.group(1)), LT.CABLE_D, "leg_trrs.CABLE_D")
    m = re.search(r"jack\s*\*{0,2}\s*([0-9]+(?:\.[0-9]+)?)\s*[×x]\s*([0-9]+(?:\.[0-9]+)?)\s*[×x]\s*L\s*([0-9]+(?:\.[0-9]+)?)",
                  row)
    if m:
        claims["jack body"] = (float(m.group(2)), LT.JACK_D, "leg_trrs.JACK_D")
        claims["jack length"] = (float(m.group(3)), LT.JACK_L, "leg_trrs.JACK_L")
    m = re.search(r"plug\s*\*{0,2}\s*([0-9]+(?:\.[0-9]+)?)\s*[×x]\s*L\s*([0-9]+(?:\.[0-9]+)?)", row)
    if m:
        claims["plug barrel"] = (float(m.group(1)), LT.BARREL_D, "leg_trrs.BARREL_D")
        claims["plug length"] = (float(m.group(2)), LT.PLUG_L + LT.BARREL_L,
                                 "leg_trrs.PLUG_L + BARREL_L")

    if not claims:
        print("FAIL  the %s row is there but none of its dimensions parse -- reword it "
              "so they can be read, or this check is decoration" % SKU)
        return 1

    bad = 0
    print("cable spec: BOM %s  vs  the code that is cut to it" % SKU)
    for name in sorted(claims):
        bom_v, code_v, where = claims[name]
        ok = abs(bom_v - code_v) < 0.05
        bad += 0 if ok else 1
        print("  %-14s BOM %6.2f   code %6.2f   %-28s %s"
              % (name, bom_v, code_v, where, "ok" if ok else "<<< DISAGREE"))

    # ...and the tool that is cut to the cable in turn
    try:
        from src import coil_mandrel as CM
        print("\nthe coil mandrel derives from the same constant:")
        print("  barrel %.1f + cable %.1f = mean %.1f, sleeve bore %.1f, slit %.1f, "
              "pitch %.2f" % (CM.BARREL_D, LT.CABLE_D, CM.MEAN_SET, CM.SLEEVE_ID,
                              CM.CLEAT_W, CM.PITCH))
    except Exception as exc:                        # pragma: no cover
        print("\n(could not load the mandrel: %s)" % exc)

    print("\n%d disagreement(s)" % bad)
    return bad


if __name__ == "__main__":
    sys.exit(main())
