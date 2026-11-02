"""Every lead's cut length, with its lay: src/wiring.py's cables, measured.

    py -3.12 -m tools.lead_cuts

Prints the table and writes src/lead_cuts.json, the lengths on the first-flash tab's labels,
and src/wire_cuts.json, the length the viewer shows on a selected wire.
The build says when that file is stale. Run it after a route moves.
"""
from __future__ import annotations

import json


def notes():
    """{part name: the line the viewer shows while it is selected}, from src/wire_cuts.json."""
    import pathlib
    path = pathlib.Path(__file__).resolve().parent.parent / "src" / "wire_cuts.json"
    return {n: "cut %d mm" % mm for n, mm in json.loads(path.read_text(encoding="utf-8")).items()}


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
    wires = WR.wire_cuts(*WR.lever_bus(B.lever_bus_nodes()))
    WR.WIRE_CUTS.write_text(json.dumps(wires, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    print("%s: %d wires" % (WR.WIRE_CUTS.name, len(wires)))


if __name__ == "__main__":
    main()
