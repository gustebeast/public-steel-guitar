"""A swap rejected by its route A/B is not proposed again (2026-11-22).

    py -3.12 test_swap_rejected.py

brain_board: FL3 / FL4's winding swap was proposed in every run after it lost W48k's A/B, and lost
again in esc13's 2-seed A/B. With notes["swap_rejected"] naming FL3 / FL4: 1. the plan proposes no
swap on them; 2. the flow says once why; 3. without the note the swap is still proposed (the
fixture is sa_away s1's placement, testdata/stub_own_sa_away). Exit 0 = PASS.
"""
import gzip
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_flow as pf  # noqa: E402

FX = os.path.join(HERE, "testdata", "stub_own_sa_away")


def load(name):
    return json.load(gzip.open(os.path.join(FX, name + ".gz"), "rt", encoding="utf-8"))


notes = load("input.board.json")
parts = load("output_board.parts.json")["parts"]
pl = load("output_board.cells.json")
bad = []
with tempfile.TemporaryDirectory() as fd:
    plain = pf._swap_lines(notes, parts, pl, os.path.join(fd, "b"), fd)
    if not any(x.startswith("SWAP FL3") for x in plain):
        bad.append("without swap_rejected the FL3 swap was not proposed: %s" % plain)
    rej = dict(notes, swap_rejected=[{"refs": ["FL3", "FL4"], "why": "esc13 A/B: USB pair FAILs 2 vs 0, 2 vs 1"}])
    got = pf._swap_lines(rej, parts, pl, os.path.join(fd, "b"), fd)
    if any(x.startswith("SWAP FL3") or x.startswith("SWAP FL4") for x in got):
        bad.append("a rejected swap was proposed again: %s" % got)
    if not any(x.startswith("SWAP not proposed for FL3 FL4: rejected by route A/B (esc13") for x in got):
        bad.append("the rejection was not said: %s" % got)
    if json.load(open(os.path.join(fd, "pin_swaps.json")))["swaps"]:
        bad.append("pin_swaps.json still lists a swap")
for x in bad:
    print("  FAIL:", x)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
