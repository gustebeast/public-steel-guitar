"""A legaliser never breaks a hard distance (lead 2026-11-22; place_init._drop / _HARD).

    py -3.12 test_legal_hard.py

brain_board rpl: the quadratic stage met U13's hard `near` J1 (14 mm, DS46176 fig. 1);
legalisation took the nearest FREE spot to U13's target, 16.44 mm out, and the flow
stopped at the intent check. Synthetic board, J1 held at the -X end, U13's target 30 mm
away at +X:

  0  hard near J1 14 mm      -> U13 seated with the rule kept (slack >= -0.05)
  1  the same rule soft      -> U13 at its target (the rule does not bind the seat)
  2  hard, J1's 14 mm ring blocked -> _drop says no room (False); nothing seated
  3  hard decap at a pin     -> the cap keeps its 1.5 mm to J1.1 although its target is far
  4  the rule's partner not placed yet -> unconstrained (the later drop is judged instead)
  5  the partner placed but IN FLIGHT (a group move) -> unconstrained until it lands
Exit 0 = PASS.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_init as pin  # noqa: E402
import place_intent as pi  # noqa: E402


def box(w, h):
    return [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]


def part(w, h, pads):
    return dict(crtyd=box(w, h), fab=[-w / 2, w / 2, -h / 2, h / 2], at=[0, 0, 0], side="F",
                pads=[dict(num=str(i + 1), net=n, xy=xy, size=[0.6, 0.6], rot=0.0) for i, (n, xy) in enumerate(pads)])


PARTS = {"J1": part(8, 8, [("VBUS", [3.6, 0]), ("GND", [-2, 0])]),
         "U13": part(5, 5, [("N%d" % k, [-2 + 0.5 * (k % 8), -2 + 0.5 * (k // 8)]) for k in range(20)]),
         "C1": part(1.6, 0.9, [("VBUS", [-0.5, 0]), ("GND", [0.5, 0])])}
POLY = [[0, 0], [60, 0], [60, 40], [0, 40]]
bad = []


def setup(rules, block=False):
    G = pin.Grid(POLY, [], [])
    pl = {"J1": [6.0, 20.0, 0.0]}
    m, ai, aj = pin.mask(PARTS["J1"], 0.0)
    pin._stamp(G, m, ai, aj, *G.ij(6.0, 20.0), force=True, grow=pin.halo(PARTS["J1"]))
    if block:                                   # everything within 26 mm of J1 taken
        G.occ[np.hypot(G.X - 6.0, G.Y - 20.0) <= 26.0] += 1
    pin._HARD.clear()
    for r in rules:
        if r["kind"] in pin.HARD_DIST_KINDS and pi.is_hard(r):
            for x in pin._rule_refs(r):
                pin._HARD.setdefault(x, []).append(r)
    return G, pl


def slack(r, pl):
    return pin._slack(r, PARTS, pl)


near = dict(kind="near", ref="U13", target="J1", max_mm=14.0, hard=True, src="DS46176 fig. 1")
G, pl = setup([near])
if not pin._drop(G, PARTS, "U13", (40.0, 20.0), [0.0], pl):
    bad.append("0: U13 found no seat")
elif slack(near, pl) < -0.05:
    bad.append("0: U13 seated %.2f mm past its hard near (at %s)" % (-slack(near, pl), pl["U13"]))
soft = dict(near, hard=False)
G, pl = setup([soft])
pin._drop(G, PARTS, "U13", (40.0, 20.0), [0.0], pl)
if np.hypot(pl["U13"][0] - 40.0, pl["U13"][1] - 20.0) > 0.2:
    bad.append("1: a soft near moved U13 off its target: %s" % pl["U13"])
G, pl = setup([near], block=True)
if pin._drop(G, PARTS, "U13", (40.0, 20.0), [0.0], pl) or "U13" in pl:
    bad.append("2: U13 seated with its whole hard ring blocked: %s" % pl.get("U13"))
dec = dict(kind="decap", cap="C1", pin="J1.1", max_mm=1.5, hard=True, src="test")
G, pl = setup([dec])
if not pin._drop(G, PARTS, "C1", (40.0, 20.0), [0.0, 90.0], pl) or slack(dec, pl) < -0.05:
    bad.append("3: hard decap C1 at %s, slack %.2f" % (pl.get("C1"), slack(dec, pl) if "C1" in pl else float("nan")))
G, pl = setup([dict(near, ref="U13", target="C1")])
pin._drop(G, PARTS, "U13", (40.0, 20.0), [0.0], pl)
if np.hypot(pl["U13"][0] - 40.0, pl["U13"][1] - 20.0) > 0.2:
    bad.append("4: a rule whose partner is not placed bound the seat: %s" % pl["U13"])
G, pl = setup([near])
pin._INFLIGHT.add("J1")
pin._drop(G, PARTS, "U13", (40.0, 20.0), [0.0], pl)
pin._INFLIGHT.clear()
if np.hypot(pl["U13"][0] - 40.0, pl["U13"][1] - 20.0) > 0.2:
    bad.append("5: an in-flight partner bound the seat: %s" % pl["U13"])
pin._HARD.clear()
print("\n".join(bad) if bad else "PASS")
sys.exit(1 if bad else 0)
