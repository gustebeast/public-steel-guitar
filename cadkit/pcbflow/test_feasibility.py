"""Hard near / decap rules against their regions, before placement (pi.feasibility).

    py -3.12 test_feasibility.py

brain_board sw2: C3 (U5's VIN cap, hard decap 2.0 at U5.2) was bound to region pd while U5
sat in power; the flow placed for 20 minutes and ended NO ROOM.
  1  regions apart by more than the reach              -> INFEASIBLE
  2  cap bound to another region that touches the IC's  -> REGION SPLIT
  3  cap bound with its IC                              -> nothing
  4  cap unbound (anywhere on the board)                -> nothing
  5  target held: its pin outside the cap's region's reach -> INFEASIBLE; inside -> nothing
  6  soft rule                                          -> never
Exit 0 = PASS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_intent as pi  # noqa: E402


def box(w, h):
    return [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]


def part(w, h, pads):
    return dict(crtyd=box(w, h), fab=[-w / 2, w / 2, -h / 2, h / 2], at=[0, 0, 0], side="F",
                pads=[dict(num=str(i + 1), net=n, xy=xy, size=[0.5, 0.5], rot=0.0) for i, (n, xy) in enumerate(pads)])


P = {"U5": part(4, 5, [("VIN", [-1.5, 0]), ("GND", [1.5, 0])]), "C3": part(1.0, 0.5, [("VIN", [-0.4, 0]), ("GND", [0.4, 0])])}
notes = dict(outline_poly=[[0, 0], [100, 0], [100, 50], [0, 50]])
REG = lambda n, x0, x1: dict(kind="region", name=n, poly=[[x0, 0], [x1, 0], [x1, 50], [x0, 50]])
IN = lambda ref, n: dict(kind="in_region", refs=[ref], region=n)
DEC = dict(kind="decap", cap="C3", pin="U5.1", max_mm=2.0, hard=True, src="test")
bad = []


def run(rules):
    return pi.feasibility(rules, P, notes)


cases = [("1 apart", [REG("power", 0, 30), REG("pd", 60, 100), IN("U5", "power"), IN("C3", "pd"), DEC], (1, 0)),
         ("2 touching", [REG("power", 0, 30), REG("pd", 30, 100), IN("U5", "power"), IN("C3", "pd"), DEC], (0, 1)),
         ("3 with its IC", [REG("power", 0, 30), IN("U5", "power"), IN("C3", "power"), DEC], (0, 0)),
         ("4 unbound", [REG("power", 0, 30), IN("U5", "power"), DEC], (0, 0)),
         ("5a held far", [REG("pd", 60, 100), IN("C3", "pd"),
                          dict(kind="fixed", ref="U5", xy=[10, 25], rot=0, hold="mechanical", why="t"), DEC], (1, 0)),
         ("5b held near", [REG("pd", 0, 100), IN("C3", "pd"),
                           dict(kind="fixed", ref="U5", xy=[10, 25], rot=0, hold="mechanical", why="t"), DEC], (0, 0)),
         ("6 soft", [REG("power", 0, 30), REG("pd", 60, 100), IN("U5", "power"), IN("C3", "pd"), dict(DEC, hard=False)], (0, 0))]
for name, rules, want in cases:
    b, s = run(rules)
    if (len(b), len(s)) != want:
        bad.append("%s: %d infeasible / %d split, want %s: %s" % (name, len(b), len(s), want, b + s))
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "place_flow.py"), encoding="utf-8").read()
if "pi.feasibility(rules, parts, notes)" not in src:
    bad.append("place_flow no longer runs pi.feasibility before placement")
print("\n".join(bad) if bad else "PASS")
sys.exit(1 if bad else 0)
