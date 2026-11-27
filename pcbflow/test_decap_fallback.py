"""auto_decaps says how it chose each cap's part, and place_flow prints every guess (lead
2026-11-26, brain_board C65 / C119: a description naming no part, or naming the wrong one, sent a
cap to the nearest supply pin and it sat 27 mm off before anyone saw).

    py -3.12 test_decap_fallback.py

A synthetic placed board, no files: U1 and U2 (supply pin 2 on +5V each, U2 nearer the caps) and
L1 (the rail's source, pin 2 on +5V); 0402 caps on +5V to GND.
1. C1 "5 V HF bypass" names no part: assigned "fallback: nearest ...", to U2 (the nearest).
2. C2 "buck output HF bypass, at L1" names L1, a candidate that is not a U: it goes to L1, assigned
   "named L1" (the nearest pin, U2, took it before).
3. C3 "U1 decoupling" names U1: it goes to U1, not to the nearer U2.
4. place_flow prints an "auto_decaps FALLBACK <cap> -> <part>" line per fallback rule.
Exit 0 = PASS.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_intent as pi  # noqa: E402

bad = []
pad = lambda num, net, x, y: dict(num=num, net=net, xy=[x, y], size=[0.56, 0.62], rot=0.0, tht=False)


def cap():
    return dict(fpid="C_0402_1005Metric", side="F", anchor="pads", at=[0.0, 0.0, 0.0],
                pads=[pad("1", "+5V", -0.48, 0.0), pad("2", "GND", 0.48, 0.0)],
                crtyd=[[0.905, 0.455], [0.905, -0.455], [-0.905, -0.455], [-0.905, 0.455]],
                fab=[-0.55, 0.55, -0.3, 0.3])


def ic(n_pins=8):
    return dict(fpid="SOIC-8", side="F", anchor="pads", at=[0.0, 0.0, 0.0],
                pads=[pad(str(n), {1: "GND", 2: "+5V"}.get(n, "N%d" % n), -2.7, (n - 4) * 1.27)
                      for n in range(1, n_pins + 1)],
                crtyd=[[3.7, 5.5], [3.7, -5.5], [-3.7, -5.5], [-3.7, 5.5]], fab=[-2.0, 2.0, -5.0, 5.0])


L1 = dict(fpid="L_1210", side="F", anchor="pads", at=[0.0, 0.0, 0.0],
          pads=[pad("1", "SW", -1.5, 0.0), pad("2", "+5V", 1.5, 0.0)],
          crtyd=[[2.5, 1.8], [2.5, -1.8], [-2.5, -1.8], [-2.5, 1.8]], fab=[-2.0, 2.0, -1.5, 1.5])
parts = {"U1": ic(), "U2": ic(), "L1": L1, "C1": cap(), "C2": cap(), "C3": cap()}
notes = {"placements": {"U1": [40.0, 0.0, 0.0], "U2": [6.0, 0.0, 0.0], "L1": [30.0, 20.0, 0.0],
                        "C1": [0.0, 0.0, 0.0], "C2": [0.0, 2.0, 0.0], "C3": [0.0, -2.0, 0.0]}}
desc = {"C1": "5 V HF bypass", "C2": "buck output HF bypass, at L1", "C3": "U1 decoupling"}
rules = {(r.get("cap") or r.get("ref")): r for r in pi.auto_decaps(parts, notes, descriptions=desc)}
for c, part, how in (("C1", "U2", "fallback"), ("C2", "L1", "named L1"), ("C3", "U1", None)):
    r = rules.get(c)
    got = (r.get("pin") or r.get("target") or "").split(".")[0] if r else None
    print("%s -> %s (%s)" % (c, got, r.get("assigned") if r else "no rule"))
    if got != part:
        bad.append("%s went to %s, not %s" % (c, got, part))
    if how and not str((r or {}).get("assigned", "")).startswith(how):
        bad.append("%s is assigned %r, not %s..." % (c, (r or {}).get("assigned"), how))
    if c == "C3" and str((r or {}).get("assigned", "")).startswith("fallback"):
        bad.append("C3 names U1 but is reported as a fallback")
src = open(os.path.join(HERE, "place_flow.py"), encoding="utf-8").read()
if 'say("auto_decaps FALLBACK %s -> %s' not in src or '.startswith("fallback")' not in src:
    bad.append("place_flow does not print each fallback assignment")
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
