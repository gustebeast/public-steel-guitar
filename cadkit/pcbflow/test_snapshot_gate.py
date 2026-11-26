"""A snapshot hold that keeps its part off the part's own rule stops the flow; a declared supply
pin makes its net a supply for auto_decaps (lead 2026-11-26, brain_board p11: U5's four VSTBY
input caps were snapshot-held 15-19 mm from U5, and VSTBY matched no SUPPLY pattern, so they had
no rule at all).

    py -3.12 test_snapshot_gate.py

A synthetic board, no files: U1 (an 8-pin part, pin 2 its input on net VSTBY, pin 1 GND) and
C1 / C2 (0402, VSTBY to GND).
1. auto_decaps gives C1 a rule on VSTBY once notes.supply_pins declares U1.2, and none without
   it (the name alone is not a supply).
2. _snapshot_broken names C1 held by a snapshot 15 mm off U1.2 against its decap rule, the hold
   and the rule both in the line; C2, free, at the pin, and a C1 hold of class "physical" (a
   constraint, not a memory) are not named.
3. place_flow stops on a snapshot breach before layout, and reports it under --place-only.
Exit 0 = PASS.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_flow as pf  # noqa: E402
import place_intent as pi  # noqa: E402

bad = []
pad = lambda num, net, x, y: dict(num=num, net=net, xy=[x, y], size=[0.56, 0.62], rot=0.0, tht=False)
cap = lambda: dict(fpid="C_0402_1005Metric", side="F", anchor="pads", at=[0.0, 0.0, 0.0],
                   pads=[pad("1", "VSTBY", -0.48, 0.0), pad("2", "GND", 0.48, 0.0)],
                   crtyd=[[0.905, 0.455], [0.905, -0.455], [-0.905, -0.455], [-0.905, 0.455]],
                   fab=[-0.55, 0.55, -0.3, 0.3])
u1 = dict(fpid="SOIC-8", side="F", anchor="pads", at=[0.0, 0.0, 0.0],
          pads=[pad(str(n), {1: "GND", 2: "VSTBY"}.get(n, "N%d" % n), -2.7 if n <= 4 else 2.7,
                    (n - 2.5) * 1.27 if n <= 4 else (6.5 - n) * 1.27) for n in range(1, 9)],
          crtyd=[[3.7, 2.7], [3.7, -2.7], [-3.7, -2.7], [-3.7, 2.7]], fab=[-2.0, 2.0, -2.5, 2.5])
parts = {"U1": u1, "C1": cap(), "C2": cap()}
notes = {"supply_pins": {"U1": {"2": "VIN"}}}

# 1. the declared supply pin
r_with = [r for r in pi.auto_decaps(parts, notes) if (r.get("cap") or r.get("ref")) == "C1"]
r_none = [r for r in pi.auto_decaps(parts, {}) if (r.get("cap") or r.get("ref")) == "C1"]
if not r_with:
    bad.append("auto_decaps gives no rule to a cap on VSTBY although U1.2 is a declared supply pin")
if r_none:
    bad.append("auto_decaps treats VSTBY as a supply by name (no supply pin declared)")

# 2. the gate
dec = {"kind": "decap", "cap": "C1", "pin": "U1.2", "max_mm": 3.0, "hard": False, "src": "test"}
dec2 = dict(dec, cap="C2")
snap = {"kind": "fixed", "ref": "C1", "xy": [-17.7, 0.0], "rot": 0.0, "hard": True, "snapshot": True,
        "why": "snapshot: where an old run left it", "src": "mP0 (test)"}
pl = {"U1": [0.0, 0.0, 0.0], "C1": [-17.7, 0.0, 0.0], "C2": [-4.0, -0.6, 0.0]}
P = pi.Placed(parts, pl)
sb = pf._snapshot_broken([dec, dec2, snap], P, {})
print("\n".join(sb) or "(no breach)")
if len(sb) != 1 or not sb[0].startswith("C1 held by a snapshot") or "mP0 (test)" not in sb[0] \
        or "decap C1 at U1.2" not in sb[0]:
    bad.append("the snapshot-held C1 off its decap rule is not named once with its hold and rule")
phys = dict(snap, hold="physical")
phys.pop("snapshot")
if pf._snapshot_broken([dec, phys], P, {}):
    bad.append("a physical hold (a constraint) was reported as a stale snapshot")

# 3. wired into the flow before layout
src = open(os.path.join(HERE, "place_flow.py"), encoding="utf-8").read().replace("\r\n", "\n")
i, j = src.find("sb = _snapshot_broken("), src.find("if _near_gate(nb, place_only):")
if i < 0 or j < 0 or i > j or "if sb and not place_only:" not in src[i:j] or "return 2" not in src[i:j]:
    bad.append("place_flow does not stop on a snapshot breach before layout")

for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
