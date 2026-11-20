"""Judge finished boards against each other on one scale: python ab_judge.py RUN_DIR [RUN_DIR ...]

Each RUN_DIR holds a finish + quality run.log (score / finish / quality, as the replay
scripts write it) and its output_board.* files. Prints one row per run:

  unconnected  violations  verify(rules)  quality(judged)  joins: router open / joins_open

⚠ VERIFY IS COUNTED BY (GROUP, RULE), AND AN UNROUTED GROUP FAILS EVERY RULE IT HAS
(brain_board W48k/W48w, 2026-11-20). verify.py prints one line per finding, so a pair
routed badly scores 8-9 lines (a no-GND-via line per layer change, one per segment that
splits layers) while a pair left with NO copper scores one line ("nets carry no copper at
all"). Read as a count, not routing GADGET looked better than routing it: W48k 17 vs
W48w 24-40 was mostly that. Here each group is judged on the rules it declares in
board.json (skew, same_layer, max_vias, equal_vias, return_via_mm): a rule fails once
however many lines it printed, and a group without copper fails all of them.

⚠ QUALITY WITHOUT A4/A17 WHEN THE NETLIST SOURCES DIFFER. A4 (pinout citations) and A17
(connector labels) read the design source, not the routing; two arms generated from
different brain_board.py revisions differed by 12 on A4 alone. When the runs' netlists
differ (ignoring tstamps, the (source ...) path and SKiDL tags) OR their board.json
"quality" blocks differ (the citations A4 reads live there, not in the netlist: W48k and
W48w had identical netlists and still differed by 11 on A4), both are dropped from every
row, and the header says so. A3 inside quality is verify's line count again, so the
judged quality carries the (group, rule) count in its place.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

RULES = (("skew", "max_skew_mm"), ("layers", "same_layer"), ("via_budget", "max_vias"),
         ("equal_vias", "equal_vias"), ("return_via", "return_via_mm"))
SOURCE_RULES = ("A4", "A17")          # judged from the design source, not the board


def _kind(text):
    if "carry no copper" in text:
        return "all"
    if text.startswith("skew"):
        return "skew"
    if "share a layer set" in text or "run different layers" in text:
        return "layers"
    if "vias (budget" in text:
        return "via_budget"
    if "different via counts" in text:
        return "equal_vias"
    if "no GND via" in text:
        return "return_via"
    return "other"


def _net_key(path):
    """The netlist with what does not change the circuit stripped (tstamps, source, tags)."""
    txt = open(path, encoding="utf-8").read()
    txt = re.sub(r'\((?:date|tstamps?|source)\s[^)]*\)', "", txt)
    txt = re.sub(r'\(name "SKiDL Tag"\) "[^"]*"', "", txt)
    return hashlib.sha256(txt.encode()).hexdigest()


def judge(d):
    log = open(os.path.join(d, "run.log"), encoding="utf-8", errors="replace").read()
    groups = {g["name"]: g for g in json.load(open(os.path.join(d, "output_board.board.json"),
                                                    encoding="utf-8")).get("match", [])}
    row = {"run": os.path.basename(os.path.normpath(d))}
    m = re.findall(r"^output_board: (\d+) unconnected, (\d+) violation", log, re.M)
    row["unc"], row["viol"] = (int(m[-1][0]), int(m[-1][1])) if m else (None, None)
    m = re.search(r'"open": (\d+), "joins_open": (\d+)', log)
    row["open"], row["joins"] = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    failed = set()
    lines = 0
    for g, text in re.findall(r"^    FAIL (\S+)\s+(.*)$", log, re.M):
        if g not in groups:
            continue
        lines += 1
        k = _kind(text)
        if k == "all":
            failed |= {(g, r) for r, key in RULES if groups[g].get(key)}
        else:
            failed.add((g, k))
    row["verify_lines"], row["verify"] = lines, len(failed)
    q = log.split("## quality")[-1]
    rules = {}
    for a, text in re.findall(r"^\s+FAIL\s+([AM]\d+)\s+(.*)$", q, re.M):
        n = re.search(r"(\d+) FAIL", text)
        rules[a] = int(n.group(1)) if n else 1
    row["quality_rules"] = rules
    tot = re.findall(r"quality (\d+) FAIL", q)
    row["quality"] = int(tot[-1]) if tot else None
    net = os.path.join(d, "output_board.net")
    q_notes = json.load(open(os.path.join(d, "output_board.board.json"), encoding="utf-8")).get("quality")
    row["net"] = (_net_key(net) if os.path.isfile(net) else None,
                  hashlib.sha256(json.dumps(q_notes, sort_keys=True).encode()).hexdigest())
    return row


def main(dirs):
    rows = [judge(d) for d in dirs]
    differ = len({r["net"] for r in rows}) > 1
    for r in rows:
        # A3 is verify.py's FAIL lines again (the same 1-vs-9 artefact): swap in the
        # (group, rule) count, so quality and verify judge the pairs alike
        r["q_judged"] = (None if r["quality"] is None else
                         r["quality"] - (sum(r["quality_rules"].get(a, 0) for a in SOURCE_RULES)
                                         if differ else 0)
                         - r["quality_rules"].get("A3", 0) + r["verify"])
    print("design sources (netlist + board.json quality notes) %s -- quality judged %s" % (
        "DIFFER" if differ else "identical",
        "WITHOUT %s" % "/".join(SOURCE_RULES) if differ else "on every rule"))
    print("%-12s %5s %5s %8s %7s %8s %9s" % ("run", "unc", "viol", "verify", "(lines)",
                                            "quality", "open/join"))
    for r in rows:
        print("%-12s %5s %5s %8s %7s %8s %9s" % (
            r["run"], r["unc"], r["viol"], r["verify"], r["verify_lines"], r["q_judged"],
            "%s/%s" % (r["open"], r["joins"])))
    return rows


if __name__ == "__main__":
    main(sys.argv[1:])
