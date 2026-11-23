"""auto_floorplan gives an external-FET converter's SW node its `apart` (brain_board c5, 2026-11-22).

    py -3.12 test_sw_apart.py

The LM5122's BST_SW joins five parts (controller, inductor, two FETs, bootstrap cap). The
switch-node rule took nets of at most 4 parts, so the boost had no apart, and the USB hub's
crystal was crowded against its inductor.
  0  a 5-part SW node (U1 L1 Q1 Q2 C1) -> one forbid apart with the crystal Y1 on its b side
  1  a 3-part SW node (integrated buck) -> still its apart (unchanged)
  2  a 7-part net with an L and an IC  -> no apart (a rail-like net, over the bound)
Exit 0 = PASS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_intent as pi  # noqa: E402


def part(nets):
    return dict(crtyd=[[0, 0], [1, 0], [1, 1], [0, 1]], fab=[0, 1, 0, 1], at=[0, 0, 0], side="F",
                pads=[dict(num=str(i + 1), net=n, xy=[0.2 * i, 0], size=[0.2, 0.2], rot=0.0) for i, n in enumerate(nets)])


PARTS = {
    "U1": part(["SWA", "HO", "LO", "BOOT", "GND"]), "L1": part(["LIN", "SWA"]),
    "Q1": part(["SWA", "HO", "OUT"]), "Q2": part(["SWA", "LO", "GND"]), "C1": part(["BOOT", "SWA"]),
    "U2": part(["SWB", "GND", "FBB"]), "L2": part(["SWB", "OUTB"]), "C2": part(["SWB", "BOOTB"]),
    "U3": part(["SWC", "GND"]), "L3": part(["SWC", "OUTC"]),
    "R1": part(["SWC", "X1"]), "R2": part(["SWC", "X2"]), "R3": part(["SWC", "X3"]),
    "R4": part(["SWC", "X4"]), "R5": part(["SWC", "X5"]),
    "Y1": part(["HUB_XI", "HUB_XO"]), "U4": part(["HUB_XI", "HUB_XO", "GND"]),
}
rules = pi.auto_floorplan(PARTS)
sw = {tuple(r["a"]): r for r in rules if r["kind"] == "apart" and r.get("forbid")}
bad = []
a0 = ("C1", "L1", "Q1", "Q2", "U1")
if a0 not in sw or "Y1" not in sw[a0]["b"]:
    bad.append("0: no forbid apart for the 5-part SW node with Y1 (got %s)" % sorted(sw))
if ("C2", "L2", "U2") not in sw:
    bad.append("1: the 3-part SW node lost its apart (got %s)" % sorted(sw))
if any("L3" in a for a in sw):
    bad.append("2: a 7-part net got a switch-node apart")
print("\n".join(bad) if bad else "test_sw_apart: PASS")
sys.exit(1 if bad else 0)
