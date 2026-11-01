"""Every lead's cut length, with its lay: src/wiring.py's cables, measured.

    py -3.12 -m tools.lead_cuts

Prints the table and writes src/lead_cuts.json, the lengths on the first-flash tab's labels.
The build says when that file is stale. Run it after a route moves.
"""
from __future__ import annotations

import json


def main():
    from src import build as B
    from src import wiring as WR
    WR.build_wires()
    WR.optical_feed()
    B._ctrl_bus_components()
    print("%-22s %-9s %8s %8s %6s" % ("CABLE", "LAY", "DRAWN", "WIRE", "CUT"))
    for key in sorted(WR._CABLES):
        lay = WR._CABLES[key]["lay"]
        drawn, wire = WR.cable_cut(key)
        print("%-22s %-9s %8.1f %8.1f %6d" % (
            key, "straight" if lay is WR.STRAIGHT else "twisted", drawn, wire, WR.lead_mm(wire)))
    cuts = WR.lead_cuts()
    WR.LEAD_CUTS.write_text(json.dumps(cuts, indent=2) + "\n", encoding="utf-8")
    print("\n%s: %s" % (WR.LEAD_CUTS.name, cuts))


if __name__ == "__main__":
    main()
