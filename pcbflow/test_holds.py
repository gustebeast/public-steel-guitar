"""Every hold says why (user 2026-11-22; pi.HOLD_CLASSES, pi.check_holds).

    py -3.12 test_holds.py

1. hold_class / is_snapshot: "snapshot": true and hold "snapshot" are both snapshots; a
   `fixed` with any other class is a constraint; non-fixed rules have no class.
2. check_holds refuses a `fixed` with no class, an unknown class, a snapshot flag that
   contradicts its class, or no why -- and passes the classified ones, counting by class
   (+ transient window scaffolding).
3. place_flow runs check_holds and stops on a problem; the overflow-spread flag is gone.
5. auto_switcher: a snapshot hold does not count as the author's tie (the LM5122's 18 rules
   were all skipped on brain_board); a mate / physical hold still does.
4. Every writer of `fixed` rules gives a class: window_intent, place_init's two-sided front
   pass, and the optical example intent.
Exit 0 = PASS.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_intent as pi  # noqa: E402

bad = []
F = lambda **k: dict(kind="fixed", ref="R1", xy=[0, 0], why="a reason", **k)
for r, want in ((F(snapshot=True), True), (F(hold="snapshot"), True), (F(hold="mate"), False),
                (F(), False), (dict(kind="near", ref="R1", target="U1", snapshot=True), False)):
    if pi.is_snapshot(r) != want:
        bad.append("is_snapshot(%s) is %s" % (r, not want))

for r, n_bad in ((F(), 1), (F(hold="wish"), 1), (F(hold="mate", snapshot=True), 1),
                 (dict(kind="fixed", ref="R1", xy=[0, 0], hold="user"), 1),
                 (dict(kind="fixed", ref="R1", xy=[0, 0], hold="user", why="  "), 1),
                 (F(hold="mate"), 0), (F(hold="snapshot", snapshot=True), 0), (F(snapshot=True), 0)):
    _c, b = pi.check_holds([r])
    if len(b) != n_bad:
        bad.append("check_holds(%s) gave %d problem(s), want %d: %s" % (r, len(b), n_bad, b))
c, b = pi.check_holds([F(hold="mate"), F(hold="physical"), F(snapshot=True), F(hold="snapshot", transient=True),
                       dict(kind="region", name="win0", poly=[], transient=True)])
if b or c != {"mate": 1, "physical": 1, "snapshot": 2, "transient": 2}:
    bad.append("check_holds counts %s / %s" % (c, b))

src = lambda f: open(os.path.join(HERE, f), encoding="utf-8").read()
pf = src("place_flow.py")
if "pi.check_holds(rules)" not in pf or "HOLDS:" not in pf:
    bad.append("place_flow no longer runs check_holds / prints HOLDS")
if "PCBFLOW_OVERFLOW_SPREAD" in pf or os.path.exists(os.path.join(HERE, "place_spread.py")):
    bad.append("the no-effect overflow spread (PCBFLOW_OVERFLOW_SPREAD, place_spread) is back")
for f in ("window_intent.py", "place_init.py", os.path.join("examples", "intent_optical.py")):
    s = src(f)
    for m in re.finditer(r'(dict\(kind="fixed"|r\("fixed")', s):
        stmt = s[m.start():s.find(")\n", m.start()) + 1]
        if "hold=" not in stmt:
            bad.append("%s writes a fixed rule with no hold class: %s" % (f, stmt[:80]))
print("\n".join(bad) if bad else "PASS")
sys.exit(1 if bad else 0)
