"""Independent audit of a routed board -- does NOT trust finish.py's summary line.

    py -3.12 elec/audit_board.py elec/out/optical

⚠ WHY THIS EXISTS. "0 unconnected, 0 violations" is one number from one tool, and this
session produced that same number from boards that were materially different, plus a
"still 2 unconnected" that was actually a fixed power bus with a different net open. A
count is not a verification: it does not say WHICH nets, whether the copper that closed
them is really there, or whether the thing DRC calls connected is one island or two.

Every check here is computed from the board and the netlist directly, and each one is
meant to be able to FAIL independently of the others. Where a check duplicates something
finish.py already does, that is the point -- the two should agree, and if they ever do
not, the disagreement is the finding.
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import repair_search as RS   # noqa: E402  (the obstacle parsers, already debugged)


def _load(stem):
    pcb = open(stem + ".kicad_pcb", encoding="utf-8").read()
    net = open(stem + ".net", encoding="utf-8").read()
    drc = json.load(open(stem + ".finish.drc.json", encoding="utf-8"))
    return pcb, net, drc


def _netlist_nets(net_txt):
    """net name -> set of (ref, pin), from the generated netlist."""
    out = {}
    seg = net_txt[net_txt.find("(nets"):]
    for m in re.finditer(r'\(name "([^"]+)"\)(.*?)(?=\(name "|\Z)', seg, re.S):
        nodes = re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', m.group(2))
        out[m.group(1)] = set(nodes)
    return out


def check(stem):
    pcb, net, drc = _load(stem)
    fails, notes = [], []

    # 1. what DRC says, spelled out by NET rather than counted
    open_nets = set()
    for v in drc.get("unconnected_items", []):
        for it in v["items"]:
            m = re.search(r"\[([^\]]+)\]", it["description"])
            if m:
                open_nets.add(m.group(1))
    notes.append("unconnected nets: %s" % (sorted(open_nets) or "none"))
    if open_nets:
        fails.append("%d net(s) unconnected: %s" % (len(open_nets), sorted(open_nets)))

    # 2. violations by type, ERRORS separated from WARNINGS.
    #    ⚠ THE FIRST VERSION OF THIS CHECK IGNORED SEVERITY and reported motor_ctrl's 20
    #    holes_co_located as undeclared violations on a board finish.py calls clean. They
    #    are warnings, and finish.py is right to keep them out of its error count -- so
    #    that was my bug, not the board's. But they are NOT nothing, which is why they
    #    are still printed here rather than filtered away: see the note below.
    errs = [v for v in drc.get("violations", []) if v.get("severity") != "warning"]
    warns = [v for v in drc.get("violations", []) if v.get("severity") == "warning"]
    ekinds = collections.Counter(v["type"] for v in errs)
    wkinds = collections.Counter(v["type"] for v in warns)
    notes.append("violation ERRORS by type:   %s" % (dict(ekinds) or "none"))
    notes.append("violation WARNINGS by type: %s" % (dict(wkinds) or "none"))
    undeclared = {k: n for k, n in ekinds.items() if k != "courtyards_overlap"}
    if undeclared:
        fails.append("undeclared violation errors: %s" % undeclared)

    # 3. co-located drills, called out by name because a warning count hides them.
    #    ⚠ A VIA DRILLED ON TOP OF A THROUGH-HOLE PAD IS A FAB PROBLEM even when DRC
    #    grades it a warning: the drill enters an already-drilled hole, which risks the
    #    bit and leaves an oval bore. It is also pointless copper -- a PTH pad already
    #    connects every layer, so the via buys nothing. Found on motor_ctrl: 20 of them,
    #    every one a same-net stitching via landing on a connector pin.
    colo = [v for v in warns if v["type"] == "holes_co_located"]
    if colo:
        fails.append("%d co-located drill(s) -- a via sharing a hole with a PTH pad; "
                     "harmless to DRC, not to the drill" % len(colo))

    # 3. EVERY net in the netlist has copper on the board.
    #    ⚠ A net that layout DROPPED never reaches the board, so DRC has nothing to
    #    compare and reports it clean -- the exact hole netcheck.no_orphan_pins was
    #    written for, checked here from the other side.
    nl = _netlist_nets(net)
    on_board = set(re.findall(r'\(segment[^)]*?\(net "([^"]*)"', pcb, re.S))
    on_board |= {s["net"] for s in RS._segments(pcb)}
    multi = {n for n, nodes in nl.items() if len(nodes) > 1}
    missing = sorted(n for n in multi if n not in on_board and not re.search(
        r"(^|_)(NC|SPARE|NOT_CONNECTED)(_|$)", n, re.I))
    notes.append("nets in netlist: %d (%d with >1 pin); with copper: %d"
                 % (len(nl), len(multi), len(on_board)))
    if missing:
        fails.append("%d multi-pin net(s) have NO copper at all: %s"
                     % (len(missing), missing[:6]))

    # 4. the repair copper this board declares is actually PRESENT
    bj = json.load(open(stem + ".board.json", encoding="utf-8"))
    want = bj.get("repair_tracks", []) or []
    if want:
        segs = RS._segments(pcb)
        found = 0
        for rt in want:
            nname, layer, _w, pts = rt[0], rt[1], rt[2], rt[3]
            a, b = tuple(pts[0]), tuple(pts[1])
            for s in segs:
                if s["net"] != nname or s["layer"] != layer:
                    continue
                for (p, q) in (((s["x1"] - 100, 100 - s["y1"]), (s["x2"] - 100, 100 - s["y2"])),
                               ((s["x2"] - 100, 100 - s["y2"]), (s["x1"] - 100, 100 - s["y1"]))):
                    if (abs(p[0] - a[0]) < 0.01 and abs(p[1] - a[1]) < 0.01
                            and abs(q[0] - b[0]) < 0.01 and abs(q[1] - b[1]) < 0.01):
                        found += 1
                        break
                else:
                    continue
                break
        notes.append("declared repair tracks: %d, found on the board: %d" % (len(want), found))
        if found != len(want):
            fails.append("%d declared repair track(s) are NOT on the board"
                         % (len(want) - found))

    # 5. every declared repair track still clears everything, measured independently
    if want:
        for rt in want:
            nname, layer, w, pts = rt[0], rt[1], rt[2], rt[3]
            b_ = RS.Board(stem, nname)
            p = (pts[0][0] + 100, 100 - pts[0][1])
            q = (pts[1][0] + 100, 100 - pts[1][1])
            if not b_.track_ok(p, q, layer, w / 2.0):
                fails.append("repair track on %s %s does not clear the board" % (nname, layer))
        notes.append("repair tracks re-checked against every obstacle class: done")

    # 6. board outline sanity -- a board with no edge is a board that cannot be made
    edges = RS._edges(pcb)
    notes.append("edge lines: %d" % len(edges))
    if len(edges) < 3:
        fails.append("board outline has %d edge segments" % len(edges))

    return fails, notes


def main(argv):
    if len(argv) < 2:
        raise SystemExit("usage: audit_board.py <stem>")
    stem = argv[1]
    fails, notes = check(stem)
    print("AUDIT %s" % os.path.basename(stem))
    for n in notes:
        print("   %s" % n)
    print()
    if fails:
        print("*** %d PROBLEM(S) ***" % len(fails))
        for f in fails:
            print("   - %s" % f)
        return 1
    print("all checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
