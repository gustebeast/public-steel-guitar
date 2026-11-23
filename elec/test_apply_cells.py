"""apply_cells: a re-run is a no-op, a real hold stops it, and each cell passes its own check.

    py -3.12 elec/test_apply_cells.py [<output_board.parts.json> <cadkit/pcbflow dir>]

  0  synthetic cell applied twice -> the second pass changes nothing (same rules, nothing
     dropped / unbound / released); the net neighbour within ESC_MM and a part bound to the
     anchor's region are released once, the far net neighbour never
  1  a member held as mate / mechanical / user / physical -> SystemExit naming it
  2  brain_board.intent.json is current: apply_cells --check exits 0
  3  (with the two paths) every cell in apply_cells.CELLS: check() finds no overlap and no
     broken hard rule
Exit 0 = PASS.
"""
import json
import os
import subprocess
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import apply_cells as AC  # noqa: E402

cell = types.ModuleType("fake_cell")
cell.ANCHOR, cell.CELL = "U1", {"C1": (2.0, 0.0, 0.0)}
cell.OUTER = [dict(kind="near", ref="L1", target="U1.2", max_mm=3.0)]
cell.intent_rules = lambda: [dict(kind="group", anchor="U1", members={"C1": [2.0, 0.0, 0.0]}, hard=True),
                             dict(kind="decap", cap="C1", pin="U1.1", max_mm=3.0, hard=True)] + \
    [dict(r, hard=True) for r in cell.OUTER]
NETS = {"N1": {"U1", "C1", "R1", "R9"}, "N2": {"U1", "L1"}, "GND": {"U1", "C1", "R2"}}


def snap(ref, xy):
    return dict(kind="fixed", ref=ref, xy=xy, rot=0.0, hold="snapshot", why="held where mP0 put it")


RULES = [snap("U1", [10.0, 10.0]), snap("C1", [12.0, 10.0]), snap("R1", [15.0, 10.0]),
         snap("R9", [80.0, 10.0]), snap("R2", [11.0, 11.0]),
         dict(kind="decap", cap="C1", pin="U1.1", max_mm=5.0, hard=False),
         dict(kind="in_region", refs=["C1", "L1", "R1"], region="r", hard=True),
         snap("R5", [90.0, 90.0]), dict(kind="in_region", refs=["U1", "R5"], region="b", hard=True)]
bad = []

r1, log1 = AC.apply(RULES, cell, NETS)
r2, log2 = AC.apply(r1, cell, NETS)
if r1 != r2 or log2["dropped"] or log2["unbound"] or log2["released"]:
    bad.append("0: the re-run changed the rules (%s)" % log2)
if sorted(log1["released"]) != ["C1", "R1", "R5", "U1"]:
    bad.append("0: released %s, wanted C1 R1 R5 U1 (R5 shares U1's region; R9 is far, R2 only shares GND)"
               % sorted(log1["released"]))
if log1["dropped"] != ["C1"] or log1["unbound"] != {"C1", "L1"}:
    bad.append("0: dropped %s unbound %s" % (log1["dropped"], log1["unbound"]))

for cls in ("mate", "mechanical", "user", "physical"):
    held = [dict(kind="fixed", ref="C1", xy=[12.0, 10.0], rot=0.0, hold=cls, why="x")] + RULES[2:]
    try:
        AC.apply(held, cell, NETS)
        bad.append("1: a %s hold on a member did not stop the tool" % cls)
    except SystemExit as e:
        if "C1" not in str(e):
            bad.append("1: the stop does not name C1: %s" % e)

rc = subprocess.run([sys.executable, os.path.join(HERE, "apply_cells.py"), "--check"], capture_output=True).returncode
if rc:
    bad.append("2: brain_board.intent.json is stale: run py -3.12 elec/apply_cells.py")

if len(sys.argv) == 3:
    sys.path.insert(0, sys.argv[2])
    import importlib
    import place_intent  # noqa: E402
    parts = json.load(open(sys.argv[1]))["parts"]
    for mod in AC.CELLS:
        bad += ["3: %s: %s" % (mod, p) for p in importlib.import_module(mod).check(parts, place_intent)]

print("\n".join(bad) if bad else "test_apply_cells: PASS")
sys.exit(1 if bad else 0)
