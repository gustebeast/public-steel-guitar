"""Satellite seating and the stranding summary (lead 2026-11-22).

    py -3.12 test_seat_order.py

1. A HARD satellite seats before its soft siblings (place_init seat()): brain_board sw1,
   U205's hard VIN cap C218 found NO ROOM after its soft siblings took the pin's patch.
   Synthetic: U1's pin 1 has room for one cap inside 1.0 mm; two soft caps are listed
   ahead of the hard one. The hard cap must hold its rule.
2. place_flow._sat_summary lists each stranding line once with a count line, and the
   report's placement log leaves those lines out; --place-only and --to-routability print
   the summary (run.log had it only on a stop, and twice).
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

log = ["place_init: DECAP STRANDED: C5 seated 4 mm", "place_init: other", "place_init: DECAP STRANDED: C5 seated 4 mm",
       "place_init: SATELLITE OFF ITS PIN: C5 1 mm past"]
s = pf._sat_summary(log)
if s != ["DECAP STRANDED: C5 seated 4 mm", "SATELLITE OFF ITS PIN: C5 1 mm past",
         "PLACEMENT: 1 decap(s) stranded, 1 satellite(s) off their pins"]:
    bad.append("2: _sat_summary gave %s" % s)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "place_flow.py"), encoding="utf-8").read()
if src.count("for l_ in _sat_summary(init_log):") < 2:
    bad.append("2: --place-only / --to-routability no longer print the stranding summary")
if "not _lifted(l_)" not in src:
    bad.append("2: the report's placement log repeats the summary lines")
print("\n".join(bad) if bad else "PASS")
sys.exit(1 if bad else 0)
