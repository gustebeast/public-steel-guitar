"""swaps.py -- place_flow's channel-swap proposals, carried from a run into the netlist's generator.

⚠ A PROPOSAL NOBODY APPLIES IS A FINDING THAT DIES IN A LOG (brain_board, 2026-11-22): place_flow's
swap plan proposed FL3 / FL4's winding swap (twisted pair hops 7 -> 3) in 24 runs of one day and wrote
it to flow/pin_swaps.json every time; nothing carried it, so the only way into the netlist was a
hand edit of the generator -- and the one hand edit made skipped the A/B that swap_plan's own note asks
for (W48k, 2026-11-19: the same swap routed worse on its seed). This file is the path:

    py -3.12 swaps.py list RUN_DIR...                       every run's proposals, grouped, with gains
    py -3.12 swaps.py accept RUN_DIR ACCEPTED.json BOARD --why TEXT [--refs FL3,FL4]
                                                            record a run's proposal as accepted (after
                                                            its route A/B), with the nets it moves

and, in the generator, right after it writes the netlist:

    from cadkit.pcbflow.swaps import apply_accepted     (or `import swaps` from pcbflow)
    for line in apply_accepted(net_path, "brain_board", ACCEPTED.json): print(line)

apply_accepted moves each accepted swap's pins to the other rail's net in the written netlist. A swap
whose pins already sit on the swapped nets (the generator carries it in code) is skipped and said; a
swap whose pins match neither the recorded nets nor the swapped ones stops the generator -- the circuit
changed under the acceptance, so it is re-judged, not guessed.

ACCEPTED.json: {"<board>": [{"ref": "FL3", "pins": [["3", "4"], ["2", "1"]],
                             "nets": {"3": "USBA_DM", "4": "USBA_DP", ...},      (the nets BEFORE)
                             "gain": "7 -> 3", "run": "...", "why": "..."}]}
"""
import glob
import json
import os
import re
import sys


def _spans(text, head):
    """[(i, j)]: each balanced s-expression starting with `head` (`(net`, `(node`) and whitespace --
    KiCad writes `(net` then a newline, skidl `(net ` then a space; `(nets` is not a `(net`."""
    out, i = [], 0
    while True:
        i = text.find(head, i)
        if i < 0:
            return out
        if not text[i + len(head):i + len(head) + 1].isspace():
            i += len(head)
            continue
        depth, j = 0, i
        while True:
            c = text[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append((i, j + 1))
        i = j + 1


_NODE = re.compile(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)')
_NAME = re.compile(r'\(name "([^"]*)"\)')


def netlist_pins(text, refs=None):
    """{(ref, pin): net} from a KiCad netlist's (nets ...) section, for `refs` (all if None)."""
    out = {}
    for i, j in _spans(text, "(net"):
        blk = text[i:j]
        m = _NAME.search(blk)
        if not m:
            continue
        for ni, nj in _spans(blk, "(node"):
            n = _NODE.search(blk[ni:nj])
            if n and (refs is None or n.group(1) in refs):
                out[(n.group(1), n.group(2))] = m.group(1)
    return out


def move_pins(text, moves):
    """The netlist text with each (ref, pin)'s node moved into net `moves[(ref, pin)]`."""
    nodes = {}
    for i, j in reversed(_spans(text, "(net")):
        blk = text[i:j]
        new = blk
        for ni, nj in reversed(_spans(blk, "(node")):
            n = _NODE.search(blk[ni:nj])
            if n and (n.group(1), n.group(2)) in moves:
                nodes[(n.group(1), n.group(2))] = blk[ni:nj]
                new = new[:ni] + new[nj:]
        text = text[:i] + new + text[j:]
    missing = set(moves) - set(nodes)
    if missing:
        raise ValueError("swaps: pins not in the netlist: %s" % sorted(missing))
    for key, nd in nodes.items():
        net = moves[key]
        hit = [(i, j) for i, j in _spans(text, "(net") if _NAME.search(text[i:j]).group(1) == net]
        if not hit:
            raise ValueError("swaps: net %s not in the netlist" % net)
        i, j = hit[0]
        text = text[:j - 1] + "\n      " + nd + text[j - 1:]
    return text


def _swapped(nets, pins):
    out = dict(nets)
    for a, b in pins:
        out[a], out[b] = nets[b], nets[a]
    return out


def apply_accepted(net_path, board, accepted_path):
    """Apply ACCEPTED.json's swaps for `board` to the netlist at net_path (rewritten in place).
    Returns report lines; raises SystemExit when a swap matches neither its recorded nets nor the
    swapped ones."""
    if not os.path.exists(accepted_path):
        return []
    acc = (json.load(open(accepted_path, encoding="utf-8")) or {}).get(board) or []
    if not acc:
        return []
    text = open(net_path, encoding="utf-8").read()
    now = netlist_pins(text, {s["ref"] for s in acc})
    moves, lines = {}, []
    for s in acc:
        ref, pins, before = s["ref"], [tuple(p) for p in s["pins"]], s["nets"]
        cur = {p: now.get((ref, p)) for p in before}
        after = _swapped(before, pins)
        if cur == before:
            for p, net in after.items():
                if net != before[p]:
                    moves[(ref, p)] = net
            lines.append("swaps: %s %s applied (accepted %s; %s)" % (
                ref, ", ".join("%s<->%s" % pr for pr in pins), s.get("gain", "?"), s.get("why", "")))
        elif cur == after:
            lines.append("swaps: %s already carried by the generator -- the accepted entry is redundant" % ref)
        else:
            raise SystemExit("swaps: %s's pins are on %s, neither the accepted swap's nets before (%s) nor after "
                             "(%s): the circuit changed under the acceptance -- re-judge it"
                             % (ref, cur, before, after))
    if moves:
        open(net_path, "w", encoding="utf-8").write(move_pins(text, moves))
    return lines


def proposals(run_dirs):
    """[(key, gain, applied, [runs])]: each distinct pin_swaps.json proposal over the runs."""
    seen = {}
    for d in run_dirs:
        f = os.path.join(d, "flow", "pin_swaps.json")
        if not os.path.exists(f):
            continue
        p = json.load(open(f, encoding="utf-8"))
        if not p.get("swaps"):
            continue
        key = tuple((s["ref"], tuple(tuple(x) for x in s["pins"])) for s in p["swaps"])
        k2 = (key, "%d -> %d" % (p["twisted_before"], p["twisted_after"]), bool(p.get("applied")))
        seen.setdefault(k2, []).append(os.path.basename(os.path.normpath(d)))
    return [(k, g, a, runs) for (k, g, a), runs in sorted(seen.items(), key=lambda x: -len(x[1]))]


def accept(run_dir, accepted_path, board, why, refs=None):
    """Record run_dir's proposal (all its parts, or `refs`) as accepted for `board`, with the nets
    its pins carry in that run's netlist (the nets BEFORE the swap)."""
    p = json.load(open(os.path.join(run_dir, "flow", "pin_swaps.json"), encoding="utf-8"))
    net = glob.glob(os.path.join(run_dir, "flow", "input.net")) or glob.glob(os.path.join(run_dir, "*.net"))
    if not net:
        raise SystemExit("swaps: no netlist in %s" % run_dir)
    now = netlist_pins(open(net[0], encoding="utf-8").read())
    acc = json.load(open(accepted_path, encoding="utf-8")) if os.path.exists(accepted_path) else {}
    lst = acc.setdefault(board, [])
    added = []
    for s in p["swaps"]:
        if refs and s["ref"] not in refs:
            continue
        if any(e["ref"] == s["ref"] for e in lst):
            raise SystemExit("swaps: %s already accepted for %s" % (s["ref"], board))
        pins = [list(x) for x in s["pins"]]
        lst.append(dict(ref=s["ref"], pins=pins,
                        nets={q: now[(s["ref"], q)] for pr in pins for q in pr},
                        gain="%d -> %d" % (p["twisted_before"], p["twisted_after"]),
                        run=os.path.basename(os.path.normpath(run_dir)), why=why))
        added.append(s["ref"])
    json.dump(acc, open(accepted_path, "w", encoding="utf-8"), indent=1)
    return added


def main(argv):
    if len(argv) >= 2 and argv[0] == "list":
        for key, gain, applied, runs in proposals(argv[1:]):
            print("%s  twisted %s%s  in %d run(s): %s" % (
                "; ".join("%s %s" % (r, ", ".join("%s<->%s" % pr for pr in prs)) for r, prs in key), gain,
                " (applied in the run)" if applied else "", len(runs), ", ".join(sorted(runs)[:6])
                + (" ..." if len(runs) > 6 else "")))
        return 0
    if len(argv) >= 4 and argv[0] == "accept":
        why = argv[argv.index("--why") + 1] if "--why" in argv else ""
        refs = set(argv[argv.index("--refs") + 1].split(",")) if "--refs" in argv else None
        if not why:
            raise SystemExit("swaps accept: --why is required (the A/B that accepted it)")
        print("accepted:", accept(argv[1], argv[2], argv[3], why, refs))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
