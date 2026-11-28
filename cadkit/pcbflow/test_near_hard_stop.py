"""A broken HARD near rule stops place_flow (lead 2026-11-21).

    py -3.12 cadkit/pcbflow/test_near_hard_stop.py RUN_DIR [RUN_DIR2]

RUN_DIR is a place_flow output (output_board.parts.json, flow/init.json, flow/intent.json)
whose placement breaks at least one hard `near` rule -- esc_pre16 left C230 2.54 mm from
U205.11 against a hard 1.5. Cases:

  0  the placement as it is                  -> _near_broken names the part, rule and distance
  1  that part moved onto its target pin     -> the rule is no longer reported
  2  the same rule made soft                 -> never reported, however far
  3  the gate                                -> _near_gate says stop (2) unless --place-only
                                                or PCBFLOW_NEAR_BROKEN_OK=1
  4  (RUN_DIR2) a decap on a long pad's end  -> kept: decaps measure to the pad's nearest point;
                                                the same seat as a non-capacitor reads the centre

Exit code 0 = every case answered as it should.
"""
from __future__ import annotations

import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_flow as pf  # noqa: E402
import place_intent as pi  # noqa: E402


def main(d):
    parts = json.load(open(os.path.join(d, "output_board.parts.json"), encoding="utf-8"))["parts"]
    pl = json.load(open(os.path.join(d, "flow", "init.json")))
    pl = pl.get("placements", pl)
    rules = json.load(open(os.path.join(d, "flow", "intent.json")))
    notes = json.load(open(os.path.join(d, "output_board.board.json"), encoding="utf-8"))
    ok = True

    def say(c, good, msg):
        nonlocal ok
        ok &= good
        print("%s case %s: %s" % ("PASS" if good else "FAIL", c, msg))

    nb = pf._near_broken(rules, pi.Placed(parts, pl), notes)
    say(0, bool(nb), "%d hard near rule(s) broken%s" % (len(nb), (": " + nb[0][1]) if nb else ""))
    if not nb:
        return 1
    i_ = int(nb[0][1].split("rule ", 1)[1].split(":", 1)[0])
    r_ = rules[i_]
    ref = r_["ref"]

    # 1: the part moved onto its target (a pin target: onto that pad's centre)
    pl1 = copy.deepcopy(pl)
    tgt = r_["target"]
    if "." in tgt:
        tr, tp = tgt.split(".", 1)
        pad = next(p for p in parts[tr]["pads"] if p["num"] == tp)
        x, y = [float(v) for v in __import__("numpy").asarray(pi.Placed(parts, pl).world(tr, [pad["xy"]])).reshape(-1)[:2]]
    else:
        x, y = pl[tgt][:2]
    pl1[ref] = [float(x), float(y), pl[ref][2]]
    nb1 = [w for w in pf._near_broken([r_], pi.Placed(parts, pl1), notes)]
    say(1, not nb1, "%s on its target -> %d report(s)" % (ref, len(nb1)))

    # 2: soft rules never stop the flow
    soft = dict(r_, hard=False)
    nb2 = pf._near_broken([soft], pi.Placed(parts, pl), notes)
    say(2, not nb2, "the same rule soft -> %d report(s)" % len(nb2))

    # 3: the gate
    os.environ.pop("PCBFLOW_NEAR_BROKEN_OK", None)
    say("3a", pf._near_gate(nb, place_only=False) == 2, "hard near broken -> stop")
    say("3b", pf._near_gate(nb, place_only=True) is None, "--place-only reports, does not stop")
    say("3c", pf._near_gate([], place_only=False) is None, "nothing broken -> go on")
    os.environ["PCBFLOW_NEAR_BROKEN_OK"] = "1"
    say("3d", pf._near_gate(nb, place_only=False) is None, "PCBFLOW_NEAR_BROKEN_OK=1 (old-board replay) -> go on")
    os.environ.pop("PCBFLOW_NEAR_BROKEN_OK", None)

    # 4: a DECAP pin target is measured to the pad's nearest point by default (lead 2026-11-21);
    # every other pin target keeps the centre. RUN_DIR2 (if given) holds the decap on a long
    # pad's near end (esc_pre19: C230 on U205.11's stub end, 0.49 from the pad, 2.20 from its
    # centre): kept as a decap; the same seat under a non-capacitor ref reads the centre, broken
    if len(sys.argv) > 2 and "." in r_["target"]:
        d2 = sys.argv[2]
        parts2 = json.load(open(os.path.join(d2, "output_board.parts.json"), encoding="utf-8"))["parts"]
        pl2 = json.load(open(os.path.join(d2, "flow", "init.json")))
        pl2 = pl2.get("placements", pl2)
        r0 = {k: v for k, v in r_.items() if k != "to"}          # no per-rule opt-in: one path
        P2 = pi.Placed(parts2, pl2)
        dec = pf._near_broken([r0], P2, notes)
        say("4a", not dec, "decap, default measure: %s" % (dec[0][1] if dec else "kept (" + pi.check(r0, P2, notes)[0][2] + ")"))
        say("4b", pi._is_decap_rule(P2, r0["ref"], r0["target"]), "%s -> %s is a decap rule" % (r0["ref"], r0["target"]))
        alias = "R9%s" % r0["ref"][1:]                           # the same part, not a capacitor
        parts3 = dict(parts2, **{alias: parts2[r0["ref"]]})
        pl3 = dict(pl2, **{alias: pl2[r0["ref"]]})
        P3 = pi.Placed(parts3, pl3)
        r3 = dict(r0, ref=alias)
        cen = pf._near_broken([r3], P3, notes)
        say("4c", bool(cen) and not pi._is_decap_rule(P3, alias, r3["target"]),
            "non-decap %s on the same seat keeps the centre: %s" % (alias, cen[0][1] if cen else "kept"))
        d_dec = float(pi.check(r0, P2, notes)[0][2].split(" ")[0])
        d_cen = float(pi.check(r3, P3, notes)[0][2].split(" ")[0])
        say("4d", d_dec < d_cen, "decap reads less than the centre (%.2f < %.2f)" % (d_dec, d_cen))
    return 0 if ok else 1


if __name__ == "__main__":
    import _testargs  # noqa: E402
    _testargs.need(1, 'RUN_DIR: a place_flow output whose placement breaks a hard near rule (esc_pre16)')
    sys.exit(main(sys.argv[1]))
