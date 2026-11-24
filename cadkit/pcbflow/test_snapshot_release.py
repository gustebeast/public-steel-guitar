"""A snapshot hold never outranks a hard rule; a real hold still stops the flow (lead 2026-11-23).

    py -3.12 test_snapshot_release.py

brain_board pr_s1: U13 was snapshot-held where mP0 left it, J1's panel turn moved its lands, and
U13 sat 14.74 mm from J1 against a HARD 14 -- the flow stopped before layout. A tiny board:

  1  U1 snapshot-held 30 mm from J1, hard near J1 <= 5   -> _release_snapshots drops U1's hold
                                                            and says SNAPSHOT RELEASED
  2  place() on that board                               -> U1 seated within 5 of J1; no hard
                                                            near broken, place_flow's gate goes on
  3  the same seat held "user" (and "mate")              -> kept: the hold stands, the rule is
                                                            broken and place_flow's gate stops (2)
  4  a snapshot that already meets its rule              -> kept where it is
  5  place_init has no off-switch for it                 -> PCBFLOW_SNAPSHOT_RELEASE is gone
  6  place_flow takes place_init's release (vip_s1: the  -> the released snapshot leaves the
     release seated U13, the intent still held it and       intent every later gate reads; the
     the BROKEN gate stopped the flow 9.05 mm off it)       BROKEN gate passes the new seat; a
                                                            user hold named in the hand-off stays
  7  place_init's main writes the hand-off FILE           -> init.handoff.json {"grown", "released"}
     (not log text: lead 2026-11-23), every run              names U1; place_flow._handoff reads
                                                            it; a missing file stops the flow

Fails without the fix: place_init has no _release_snapshots, U1 stays at its snapshot.
Exit 0 = PASS.
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_flow as pf  # noqa: E402
import place_init as P  # noqa: E402
import place_intent as pi  # noqa: E402


def part(w, h, pads):
    c = [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]
    return {"crtyd": c, "fab": [-w / 2, w / 2, -h / 2, h / 2], "at": [0.0, 0.0, 0.0], "side": "F",
            "pads": [{"num": str(i + 1), "xy": xy, "size": [0.6, 0.6], "net": n}
                     for i, (xy, n) in enumerate(pads)]}


PARTS = {"J1": part(4.0, 4.0, [([-1.0, 0.0], "A"), ([1.0, 0.0], "B")]),
         "U1": part(3.0, 3.0, [([-1.0, 0.0], "A"), ([1.0, 0.0], "B")])}
NOTES = {"outline_mm": [60.0, 40.0], "placements": {}}
NEAR = {"kind": "near", "ref": "U1", "target": "J1", "max_mm": 5.0, "hard": True, "src": "test"}
J1_HOLD = {"kind": "fixed", "ref": "J1", "xy": [-25.0, 0.0], "rot": 0.0, "hold": "mechanical", "why": "the panel"}


def rules_with(hold):
    u1 = {"kind": "fixed", "ref": "U1", "xy": [10.0, 0.0], "rot": 0.0, "why": "test seat", "hold": hold}
    return [J1_HOLD, u1, NEAR]


bad = []


def want(ok, msg):
    print("%s %s" % ("PASS" if ok else "FAIL", msg))
    if not ok:
        bad.append(msg)


if not hasattr(P, "_release_snapshots"):
    want(False, "place_init has no _release_snapshots (the fix is missing)")
    sys.exit(1)

# 1
r1, lines = P._release_snapshots(PARTS, NOTES, rules_with("snapshot"))
want(not any(r["kind"] == "fixed" and r["ref"] == "U1" for r in r1) and len(r1) == 2,
     "1 snapshot U1 35 mm from J1 (hard <= 5): its hold dropped")
want(len(lines) == 1 and lines[0].startswith("SNAPSHOT RELEASED: U1"), "1 says SNAPSHOT RELEASED: %s" % lines)

# 2
pl, log, _why = P.place(copy.deepcopy(PARTS), copy.deepcopy(NOTES), rules_with("snapshot"))
d = pi.check(NEAR, pi.Placed(PARTS, pl), NOTES)[0]
want(d[0] >= 0, "2 place() seats U1 under the rule: %s (slack %.2f)" % (d[2], d[0]))
want(any("SNAPSHOT RELEASED" in x for x in log), "2 the release is in place()'s log")
rel2 = list(P.RELEASED_REFS)
want(rel2 == ["U1"], "2 place() records the released ref for the hand-off: %s" % rel2)
nb = pf._near_broken(rules_with("snapshot"), pi.Placed(PARTS, pl), NOTES)
want(not nb and pf._near_gate(nb, place_only=False) is None, "2 no hard near broken, the gate goes on")

# 3
for hold in ("user", "mate"):
    r3, l3 = P._release_snapshots(PARTS, NOTES, rules_with(hold))
    want(len(r3) == 3 and not l3, "3 a %s hold at the same seat is kept" % hold)
    pl3, _l, _w = P.place(copy.deepcopy(PARTS), copy.deepcopy(NOTES), rules_with(hold))
    want(abs(pl3["U1"][0] - 10.0) < 1e-6, "3 %s-held U1 stays at its seat (x %.2f)" % (hold, pl3["U1"][0]))
    nb3 = pf._near_broken(rules_with(hold), pi.Placed(PARTS, pl3), NOTES)
    want(bool(nb3) and pf._near_gate(nb3, place_only=False) == 2, "3 %s hold: the broken rule stops the flow" % hold)

# 4
ok4 = rules_with("snapshot")
ok4[1] = dict(ok4[1], xy=[-21.0, 0.0])
r4, l4 = P._release_snapshots(PARTS, NOTES, ok4)
want(len(r4) == 3 and not l4, "4 a snapshot that meets its rule is kept")

# 5
want("PCBFLOW_SNAPSHOT_RELEASE" not in open(os.path.join(HERE, "place_init.py"), encoding="utf-8").read(),
     "5 no off-switch")

# 6
r6, rel6 = pf._drop_released(rules_with("snapshot"), rel2)
want(rel6 == ["U1"] and len(r6) == 2, "6 place_flow drops the released hold: %s, %d rules" % (rel6, len(r6)))
P6 = pi.Placed(PARTS, pl)
brk = [c for r in r6 if r["kind"] in pi.GATE_KINDS and pi.is_hard(r) for c in pi.check(r, P6, NOTES) if c[0] < -0.05]
brk0 = [c for r in rules_with("snapshot") if r["kind"] in pi.GATE_KINDS and pi.is_hard(r)
        for c in pi.check(r, P6, NOTES) if c[0] < -0.05]
want(not brk and bool(brk0), "6 BROKEN gate: passes after the drop (%d), would stop without it (%d)" % (len(brk), len(brk0)))
r6u, _ = pf._drop_released(rules_with("user"), ["U1"])
want(len(r6u) == 3, "6 a user hold is never dropped, whatever the hand-off names")

# 7
import json  # noqa: E402
import tempfile  # noqa: E402
td = tempfile.mkdtemp(prefix="snaprel_")
stem = os.path.join(td, "b")
json.dump({"parts": PARTS}, open(stem + ".parts.json", "w"))
json.dump(NOTES, open(stem + ".board.json", "w"))
json.dump(rules_with("snapshot"), open(os.path.join(td, "intent.json"), "w"))
init = os.path.join(td, "init.json")
import contextlib, io  # noqa: E401,E402
with contextlib.redirect_stdout(io.StringIO()):
    rc7 = P.main([stem, os.path.join(td, "intent.json"), "--out", init])
h7 = json.load(open(init[:-5] + ".handoff.json")) if os.path.exists(init[:-5] + ".handoff.json") else None
want(rc7 == 0 and h7 == {"grown": {}, "released": ["U1"]}, "7 place_init writes the hand-off: %s" % h7)
want(pf._handoff(init) == ({}, ["U1"]), "7 place_flow._handoff reads it")
try:
    pf._handoff(os.path.join(td, "none.json"))
    want(False, "7 a missing hand-off must stop the flow")
except SystemExit:
    want(True, "7 a missing hand-off stops the flow")

print("PASS" if not bad else "FAIL: %d" % len(bad))
sys.exit(1 if bad else 0)
