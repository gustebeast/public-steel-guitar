"""A32: a series part passes on no more current than it receives (lead 2026-11-22).

    PYTHONPATH=<headless> "C:/Program Files/KiCad/10.0/bin/python.exe" \
        cadkit/pcbflow/test_quality_a32.py <stem of an esc12 brain_board run, e.g. rPS_12a2/output_board>

The board's notes as they were (+5V_SW at 2 A between U221 and F202, +5V_RAW and +5V_CM5 at 4 A):
  0  as laid                       -> A32 FAIL on F202: +5V_CM5 4 A after, +5V_SW 2 A before
  1  +5V_SW at 4 A                 -> no A32 FAIL anywhere on the board
  2  +5V_SW 4 A, +5V_CM5 at 3 A    -> A32 FAIL on F202: the pass-through net between U221 and the
                                      2-pin F202 must equal the net after F202
Exit 0 = PASS. In memory only.
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import quality as Q  # noqa: E402

import _testargs  # noqa: E402
_testargs.need(1, '<stem> of an esc12 brain_board run, e.g. rPS_12a2/output_board')
ctx = Q.Ctx(sys.argv[1])
orig = copy.deepcopy(ctx.q.get("power_paths"))
bad = []


def with_amps(**amps):
    pp = copy.deepcopy(orig)
    for p in pp:
        k = p["net"].replace("+", "P")
        if k in amps:
            p["amps"] = amps[k]
    ctx.q["power_paths"] = pp
    return [(s, ok, t) for s, ok, t in Q.RULES["A32"](ctx)]


r = with_amps()
f = [t for s, ok, t in r if ok is False]
print("case 0:", f)
if not any(t.startswith("F202:") and "+5V_CM5" in t and "+5V_SW" in t for t in f):
    bad.append("case 0: F202's 2 A -> 4 A not caught")
r = with_amps(P5V_SW=4.0)
f = [t for s, ok, t in r if ok is False]
print("case 1:", f or "no FAIL", "|", "; ".join(t for s, ok, t in r if ok)[:300])
if f:
    bad.append("case 1: FAIL with the chain consistent: %s" % f)
r = with_amps(P5V_SW=4.0, P5V_CM5=3.0)
f = [t for s, ok, t in r if ok is False]
print("case 2:", f)
if not any(t.startswith("F202:") and "between two series parts" in t for t in f):
    bad.append("case 2: the pass-through mismatch is not caught")
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.stdout.flush()
os._exit(1 if bad else 0)
