"""A free-anchor cell whose anchor finds NO ROOM is reported, not a KeyError (c1, 2026-11-22).

    py -3.12 test_cell_noroom.py

place() places each free-anchor `group` as one composite part, then expands the members
from the anchor's pose. When the composite found no room, _place_bus left it out of the
placements, and the expansion read pl[anchor]: a KeyError instead of the flow's NO ROOM stop.
  0  anchor unplaced -> no exception; anchor and members absent; a "NO ROOM: cell" log line
  1  anchor placed   -> members expanded from its pose (offset turned with the anchor)
  2  big-first ranks a cell by its members' box, not its anchor's courtyard (c2: the
     LM5122 cell, 15 x 24, ranked as its 5 x 5 IC and seated after L204 and the bulk caps)
  3  a member with no courtyard and no fab box (a NetTie) adds its pads and no courtyard
     (t1, 2026-11-23: TPS552892's Kelvin ties NT205 / NT206 raised a TypeError)
Exit 0 = PASS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_init as pin  # noqa: E402


def part(w, h, nets):
    b = [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]
    return dict(crtyd=b, fab=[-w / 2, w / 2, -h / 2, h / 2], at=[0, 0, 0], side="F",
                pads=[dict(num=str(i + 1), net=n, xy=[0.5 * i, 0], size=[0.4, 0.4], rot=0.0)
                      for i, n in enumerate(nets)])


PARTS = {"U1": part(4, 4, ["A", "B"]), "C1": part(1, 0.5, ["A", "GND"]), "R1": part(1, 0.5, ["B", "X"])}
RULES = [dict(kind="group", anchor="U1", members={"C1": [3.0, 0.0, 90.0]}, hard=True)]
bad = []
real = pin._place_bus

pin._place_bus = lambda parts, notes, rules, keep: ({"R1": [5.0, 5.0, 0.0]}, ["NO ROOM WHY: U1 ..."], {})
try:
    pl, log, why = pin.place(PARTS, {}, RULES)
except KeyError as e:
    bad.append("0: KeyError %s" % e)
else:
    if "U1" in pl or "C1" in pl:
        bad.append("0: an unplaced cell's anchor or member was placed: %s" % pl)
    if not any(line.startswith("NO ROOM: cell U1") for line in log):
        bad.append("0: no 'NO ROOM: cell U1' line in %s" % log)

pin._place_bus = lambda parts, notes, rules, keep: ({"U1": [10.0, 10.0, 90.0], "R1": [5.0, 5.0, 0.0]}, [], {})
pl, log, why = pin.place(PARTS, {}, RULES)
c = pl.get("C1")
if not c or abs(c[0] - 10.0) > 1e-6 or abs(c[1] - 13.0) > 1e-6 or c[2] != 180.0:
    bad.append("1: C1 expected [10, 13, 180], got %s" % c)
pin._place_bus = real
comp = pin._composite(PARTS, "U1", {"C1": [10.0, 0.0, 0.0]})     # U1 4 x 4, C1 1 x 0.5 at x 10
if abs(pin._area(comp) - 12.5 * 4.0) > 1e-6 or abs(pin._area(PARTS["U1"]) - 16.0) > 1e-6:
    bad.append("2: cell area %.2f (want 50.00), U1 alone %.2f (want 16.00)"
               % (pin._area(comp), pin._area(PARTS["U1"])))
nt = dict(crtyd=None, fab=None, at=[0, 0, 0], side="F",
          pads=[dict(num="1", net="A", xy=[0.0, 0.0], size=[0.2, 0.2], rot=0.0)])
try:
    comp = pin._composite(dict(PARTS, NT1=nt), "U1", {"C1": [10.0, 0.0, 0.0], "NT1": [2.0, 0.0, 90.0]})
except TypeError as e:
    bad.append("3: a NetTie member raised %s" % e)
else:
    if len(comp["crtyd_multi"]) != 2 or not any(q["num"] == "NT1/1" for q in comp["pads"]):
        bad.append("3: %d courtyards (want 2: U1, C1), pads %s"
                   % (len(comp["crtyd_multi"]), [q["num"] for q in comp["pads"]]))

print("\n".join(bad) if bad else "test_cell_noroom: PASS")
sys.exit(1 if bad else 0)
