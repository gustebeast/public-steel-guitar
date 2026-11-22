"""pour_around's neck note agrees with the power gate (2026-11-22).

    py -3.12 test_stub_own.py

brain_board sa_away s1: +5V_RAW's band read "neck 0.68 of 1.35 -- pinched by U221.1" while the
gate (rasterpath on the filled board) measured 1.37 PASS -- the pinch lay on U221.5's escape stub,
which the gate counts as pad. With the stub corridor as own copper the note must agree with the
gate within 0.05 mm (capped at the wanted width) on +5V_RAW and +5V_BB. Fixture: that run's
input notes, intent, parts and cell placement (testdata/stub_own_sa_away). Exit 0 = PASS.
"""
import gzip
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_flow as pf  # noqa: E402

FX = os.path.join(HERE, "testdata", "stub_own_sa_away")
GATE = {"+5V_RAW": 1.37, "+5V_BB": 1.04}       # rasterpath on sa_away_s1's filled pregate board


def load(name):
    return json.load(gzip.open(os.path.join(FX, name + ".gz"), "rt", encoding="utf-8"))


notes = load("input.board.json")
intent = load("intent.json")
rules = intent["rules"] if isinstance(intent, dict) else intent
parts = load("output_board.parts.json")["parts"]
pl = load("output_board.cells.json")
lines = pf._pours(notes, parts, pl, rules, list(notes.get("zones", []) or []))
bad = []
for net, g in GATE.items():
    m = [re.search(r"neck ([\d.]+) of ([\d.]+) mm wanted", x) for x in lines if x.startswith(net + " on F.Cu: band")]
    m = [x for x in m if x]
    if not m:
        bad.append("%s: no band note" % net)
        continue
    neck, want = float(m[0].group(1)), float(m[0].group(2))
    ok = abs(neck - min(g, want)) <= 0.05
    print("  %-8s note %.2f (wants %.2f)  gate %.2f  %s" % (net, neck, want, g, "ok" if ok else "DISAGREE"))
    if not ok:
        bad.append("%s: note %.2f vs gate %.2f" % (net, neck, g))
for x in bad:
    print("  FAIL:", x)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
