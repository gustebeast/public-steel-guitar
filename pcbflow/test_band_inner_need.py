"""A pour band's need is its OWN layer's drawn width (brain_board fold10 pre-check, 2026-11-26:
an In3 +24V band at 3 A wanted 0.95, the outer width, where the gate wants 2.15).

    py -3.12 test_band_inner_need.py

Two lands 30 mm apart, a 3 A band between them on F.Cu and on In3.Cu at a 20 C rise:
pour_around.last["need"] is copper.drawn_width_mm for that layer (0.95 / 2.15), and the inner
band holds its need. Exit 0 = PASS.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_intent as pi  # noqa: E402
from copper import drawn_width_mm  # noqa: E402

land = lambda: {"side": "F", "pads": [{"num": "1", "xy": [0.0, 0.0], "size": [2.0, 2.0], "net": "P", "rot": 0.0}],
                "crtyd": None, "fab": None}
P = pi.Placed({"A1": land(), "A2": land()}, {"A1": [0.0, 0.0, 0.0], "A2": [30.0, 0.0, 0.0]})
q = {"copper_oz": 1.0, "inner_oz": 0.5, "temp_rise_c": 20.0}
notes = {"zone_clearance": 0.5, "quality": q}
bad = []
for layer in ("F.Cu", "In3.Cu"):
    want = drawn_width_mm(3.0, layer, q)
    rule = {"kind": "pour", "net": "P", "layer": layer, "along": ["A1.1", "A2.1"], "width_mm": want + 0.5,
            "around": True}
    poly = pi.pour_around(rule, P, notes, 3.0)
    lst = getattr(pi.pour_around, "last", None) or {}
    if poly is None or abs(float(lst.get("need", 0)) - want) > 1e-6:
        bad.append("%s: need %s, want %.2f (the layer's drawn width)" % (layer, lst.get("need"), want))
    elif float(lst.get("neck", 0)) < want - 1e-6:
        bad.append("%s: neck %.2f under the need %.2f" % (layer, lst["neck"], want))
    print("  %s: need %.2f, neck %.2f" % (layer, float(lst.get("need", 0)), float(lst.get("neck", 0))))
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
