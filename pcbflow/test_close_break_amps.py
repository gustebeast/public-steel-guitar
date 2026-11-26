"""close_last sizes each break by the stated current crossing it (brain_board fold7d, 2026-11-26).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_close_break_amps.py

The fold7d shapes, islands stubbed: VIN_BRAIN's cap / TVS / sense branches carry 0 A though the
net's biggest path is 6.5 A; +5V_CM5's U221.6 -> J201 path (4 A) crosses BOTH breaks round the
R322.1 island that holds no path end; a break with an unjudged end stays None (net max).
Exit 0 = PASS.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wx  # noqa: E402
wx.DisableAsserts()
import close_last as CL  # noqa: E402

ISL = {
    "c202": {"C202.1"}, "u16": {"U16.8", "U16.9"}, "main": {"R112.2", "Q202.3", "F201.1", "C201.1"},
    "c97": {"C97.1"}, "u221": {"U221.6"}, "r322": {"R322.1"}, "j201": {"J201.77", "J201.79", "C223.1"},
    "lost": None,
}


class B:
    def BuildConnectivity(self):
        pass

    def GetConnectivity(self):
        return object()


CL._island_pads = lambda board, conn, net, it: frozenset(ISL[it]) if ISL[it] else None
todo = [("VIN_BRAIN",), ("VIN_BRAIN",), ("VIN_BRAIN",), ("+5V_CM5",), ("+5V_CM5",), ("SW",), ("GND",)]
raw = [("main", "c202"), ("c202", "u16"), ("u16", "c97"), ("u221", "r322"), ("r322", "j201"),
       ("lost", "main"), ("main", "c97")]
paths = [{"net": "VIN_BRAIN", "from": "R112.2", "to": "Q202.3", "amps": 6.5},
         {"net": "+5V_CM5", "from": "U221.6", "to": ["J201.77", "J201.79"], "amps": 4.0},
         {"net": "SW", "from": "U5.8", "to": "L1.1", "amps": 4.01}]
got = CL._break_amps(B(), todo, raw, paths)
want = [0.0, 0.0, 0.0, 4.0, 4.0, None, None]
bad = ["break %d %s: got %s, want %s" % (k, raw[k], g, w) for k, (g, w) in enumerate(zip(got, want)) if g != w]
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
