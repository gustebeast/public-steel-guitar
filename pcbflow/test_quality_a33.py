"""A33: a test pad keeps room for a probe (lead 2026-11-22).

    PYTHONPATH=<headless> "C:/Program Files/KiCad/10.0/bin/python.exe" \
        cadkit/pcbflow/test_quality_a33.py <stem of a brain_board run, e.g. rPS_13c1/output_board>

  0  as laid                     -> A33 checks every test pad, and its verdicts are the measured gaps
  1  a resistor moved onto TP2   -> A33 FAIL on TP2 naming that resistor, under 0.75 mm
  2  the resistor 3 mm away      -> TP2 passes again
Exit 0 = PASS. In memory only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew  # noqa: E402
import quality as Q  # noqa: E402

ctx = Q.Ctx(sys.argv[1])
bad = []


def tp2():
    return [(s, ok, t) for s, ok, t in Q.RULES["A33"](ctx) if s.startswith("TP2.")]


r0 = Q.RULES["A33"](ctx)
n_tp = sum(1 for r in ctx.fps if Q._prefix(r) == "TP")
print("case 0: %d row(s) for %d test pad(s); %d FAIL" % (len(r0), n_tp, sum(1 for _s, ok, _t in r0 if ok is False)))
if n_tp and len(r0) < n_tp:
    bad.append("case 0: fewer rows than test pads")
tp = ctx.fps["TP2"]
mover = next(r for r in sorted(ctx.fps) if r.startswith("R") and ctx.fps[r].IsFlipped() == tp.IsFlipped())
fp = ctx.fps[mover]
home = fp.GetPosition()
c = tp.GetPosition()
fp.SetPosition(pcbnew.VECTOR2I(c.x + pcbnew.FromMM(1.2), c.y))
r1 = tp2()
print("case 1:", r1)
if not any(ok is False and mover in t for _s, ok, t in r1):
    bad.append("case 1: %s moved onto TP2 was not caught" % mover)
fp.SetPosition(pcbnew.VECTOR2I(c.x + pcbnew.FromMM(6.0), c.y + pcbnew.FromMM(6.0)))
r2 = tp2()
print("case 2:", r2)
if any(ok is False and mover in t for _s, ok, t in r2):
    bad.append("case 2: %s 6 mm away still failed TP2" % mover)
fp.SetPosition(home)
for x in bad:
    print("  FAIL:", x)
print("PASS" if not bad else "FAIL")
sys.stdout.flush()
os._exit(1 if bad else 0)
