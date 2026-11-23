"""Satellite seating and the stranding summary (lead 2026-11-22).

    py -3.12 test_seat_order.py

1. A HARD satellite seats before its soft siblings (place_init seat()): brain_board sw1,
   U205's hard VIN cap C218 found NO ROOM after its soft siblings took the pin's patch.
   Synthetic: U1's pin 1 has room for one cap inside 1.0 mm; two soft caps are listed
   ahead of the hard one. The hard cap must hold its rule.
2. The stranding report (place_flow._sat_broken / _sat_summary): every near / decap rule by
   its own check, held parts included, hard counted apart; the old free-only DECAP STRANDED
   count is gone; --place-only and --to-routability print it (run.log had it only on a stop).
Exit 0 = PASS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_flow as pf  # noqa: E402
import place_init as pin  # noqa: E402
import place_intent as pi  # noqa: E402

bad = []


def box(w, h):
    return [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]


def part(w, h, pads):
    return dict(crtyd=box(w, h), fab=[-w / 2, w / 2, -h / 2, h / 2], at=[0, 0, 0], side="F",
                pads=[dict(num=str(i + 1), net=n, xy=xy, size=[0.5, 0.5], rot=0.0) for i, (n, xy) in enumerate(pads)])


# U1 sits in a slot of the board just wide enough for it plus ONE cap off its -X edge
parts = {"U1": part(4.0, 4.0, [("VIN", [-1.75, 0.0])] + [("N%d" % k, [1.75, -1.5 + 0.5 * k]) for k in range(7)]),
         "C1": part(1.6, 0.9, [("VIN", [-0.5, 0]), ("GND", [0.5, 0])]),
         "C2": part(1.6, 0.9, [("VIN", [-0.5, 0]), ("GND", [0.5, 0])]),
         "C9": part(1.6, 0.9, [("VIN", [-0.5, 0]), ("GND", [0.5, 0])])}
notes = dict(outline_poly=[[0, 0], [7.2, 0], [7.2, 5.0], [0, 5.0]], cutouts=[], placements={})
rules = [dict(kind="outline", hard=True),
         dict(kind="fixed", ref="U1", xy=[5.0, 2.5], rot=0.0, hard=True, hold="mechanical", why="test"),
         dict(kind="decap", cap="C1", pin="U1.1", max_mm=1.0, hard=False, src="soft sibling"),
         dict(kind="decap", cap="C2", pin="U1.1", max_mm=1.0, hard=False, src="soft sibling"),
         dict(kind="decap", cap="C9", pin="U1.1", max_mm=1.0, hard=True, src="datasheet")]
try:
    pl, log, why = pin.place(parts, notes, rules)
    s = pin._slack(rules[-1], parts, pl) if "C9" in pl else float("-inf")
    if s < -0.05:
        bad.append("1: the hard cap C9 lost its seat (slack %.2f; C9 %s, C1 %s, C2 %s)"
                   % (s, pl.get("C9"), pl.get("C1"), pl.get("C2")))
except SystemExit as e:
    bad.append("1: place refused: %s" % e)

# the stranding report: every near / decap rule by its own check, held parts included
pl2 = {"U1": [5.0, 2.5, 0.0], "C1": [5.0, 2.5 - 0.0, 0.0], "C2": [0.9, 0.6, 0.0], "C9": [0.9, 4.4, 0.0]}
pl2["C1"] = [2.25, 2.5, 0.0]                                   # at the pin: kept
r2 = [dict(kind="fixed", ref="C2", xy=[0.9, 0.6], hold="snapshot", why="test"),
      dict(kind="decap", cap="C1", pin="U1.1", max_mm=1.0, hard=False, src="a"),
      dict(kind="decap", cap="C2", pin="U1.1", max_mm=1.0, hard=False, src="b"),
      dict(kind="decap", cap="C9", pin="U1.1", max_mm=1.0, hard=True, src="c")]
sat = pf._sat_broken(r2, parts, pl2)
got = {(x[1], x[4], x[5]) for x in sat}
if got != {("C2", False, True), ("C9", True, False)}:
    bad.append("2: _sat_broken gave %s (want C2 soft held, C9 hard free; C1 kept)" % sorted(got))
lines = pf._sat_summary(["place_init: DECAP STRANDED: C5 x", "place_init: TANGLE HINT t", "place_init: TANGLE HINT t"], sat)
if lines[-2] != "PLACEMENT: 2 near/decap rule(s) broken by > 1 mm (1 hard; 1 held, 1 free)" or lines[-1] != "TANGLE HINT t"         or any("DECAP STRANDED" in l_ for l_ in lines):
    bad.append("2: _sat_summary gave %s" % lines)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "place_flow.py"), encoding="utf-8").read()
if src.count("for l_ in _sat_summary(init_log):") < 2:
    bad.append("2: --place-only / --to-routability no longer print the stranding summary")
if "not _lifted(l_)" not in src:
    bad.append("2: the report's placement log repeats the summary lines")
print("\n".join(bad) if bad else "PASS")
sys.exit(1 if bad else 0)
