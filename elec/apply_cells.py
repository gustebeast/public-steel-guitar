"""Write the designed switcher cells into brain_board.intent.json.

Each cell module (lm5122_cell, ...) is the single source of its rules: intent_rules() gives
the group (placed whole) and its hard rules, and OUTER names the parts outside the cell that
hard rules tie to it. For each cell this tool:
  * replaces every rule tagged with the cell's name ("cell": <module>) with intent_rules(),
    so a re-run after a cell edit rewrites the cell's rules instead of stacking them;
  * drops the older near / decap rules whose subject is a member or an outside part. The
    cell's own rules supersede them, and a leftover soft rule can pull against a hard one;
  * unbinds the members and outside parts from in_region rules. One region per cell: the
    anchor's. A member held to a different region is pi.feasibility's REGION SPLIT;
  * releases the snapshot holds (remembered positions, not reasons) of the anchor, the
    members, the outside parts, every part bound to the anchor's region, and every part on
    their nets within ESC_MM of the anchor's remembered seat. A snapshot left in place would pin the escape fan-out where the old
    layout put it.
A fixed rule on any of those parts that has a real hold class (mate / mechanical / user /
physical) stops the tool: a cell cannot move a part that is held for a reason.

usage: py -3.12 elec/apply_cells.py [--check]   (--check: exit 1 if the file would change)
"""
from __future__ import annotations

import importlib
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INTENT = os.path.join(HERE, "brain_board.intent.json")
NETLIST = os.path.join(HERE, "out", "brain_board.net")
CELLS = ["lm5122_cell"]          # landed one at a time, each after its route A/B
ESC_MM = 8.0 + 20.0              # anchor-seat radius for releasing a net neighbour's snapshot
NET_MAX = 12                     # nets with more parts than this are rails, not escape nets


def _nets():
    """{net: {ref}} from the KiCad netlist."""
    txt = open(NETLIST, encoding="utf-8").read()
    out = {}
    for blk in re.split(r"\(net\s*\n?\s*\(code", txt)[1:]:
        name = re.search(r'\(name\s+"([^"]*)"\)', blk).group(1)
        out[name] = set(re.findall(r'\(node\s*\n?\s*\(ref\s+"([^"]+)"\)', blk))
    return out


def _snapshot(r):
    return r["kind"] == "fixed" and (r.get("snapshot") or r.get("hold") == "snapshot")


def apply(rules, cell, nets):
    name = cell.__name__.rsplit(".", 1)[-1]
    mem, outer = set(cell.CELL), {r["ref"] for r in cell.OUTER}
    tied = mem | outer
    every = tied | {cell.ANCHOR}
    snap = {r["ref"]: r["xy"] for r in rules if _snapshot(r)}
    # the anchor's remembered seat: its snapshot on the first run, then the copy the cell's
    # group rule keeps (seat_xy), so a re-run releases the same neighbours
    at = snap.get(cell.ANCHOR) or next((r.get("seat_xy") for r in rules
                                        if r.get("cell") == name and r["kind"] == "group"), None)
    release = set(every)
    # the cell re-lays its region, so every part bound to the anchor's region loses its
    # snapshot too (c4, 2026-11-22: the output polymers C313 / C314, on the +24V rail and so
    # outside the net sweep, held their mP0 seats and left the cell NO ROOM)
    regions = {r["region"] for r in rules if r["kind"] == "in_region" and cell.ANCHOR in (r.get("refs") or ())}
    for r in rules:
        if r["kind"] == "in_region" and r["region"] in regions:
            release |= {x for x in r.get("refs") or () if x in snap}
    for n, refs in nets.items():
        if n == "GND" or len(refs) > NET_MAX or not refs & every:
            continue
        release |= {x for x in refs if x in snap and (at is None or math.dist(snap[x], at) <= ESC_MM)}
    out, log = [], {"dropped": [], "unbound": set(), "released": []}
    for r in rules:
        k = r["kind"]
        if r.get("cell") == name:
            continue
        if k == "fixed" and r.get("ref") in release and _snapshot(r):
            log["released"].append(r["ref"])
            continue
        if k == "fixed" and r.get("ref") in every:
            raise SystemExit("%s: %s is held for a reason (%s): a cell cannot move it"
                             % (name, r["ref"], r.get("hold")))
        if k in ("near", "decap") and (r.get("cap") or r.get("ref")) in tied:
            log["dropped"].append(r.get("cap") or r.get("ref"))
            continue
        if k == "in_region" and isinstance(r.get("refs"), list) and set(r["refs"]) & tied:
            log["unbound"] |= set(r["refs"]) & tied
            r = dict(r, refs=[x for x in r["refs"] if x not in tied])
        out.append(r)
    for r in cell.intent_rules():
        r = dict(r, cell=name)
        if r["kind"] == "group" and at is not None:
            r["seat_xy"] = list(at)
        out.append(r)
    return out, log


def main(argv):
    sys.path.insert(0, HERE)
    raw = open(INTENT, encoding="utf-8").read()
    rules = json.loads(raw)
    nets = _nets()
    for mod in CELLS:
        cell = importlib.import_module(mod)
        rules, log = apply(rules, cell, nets)
        print("%s: %d cell rules; dropped %d near/decap (%s); unbound %s; released %d snapshots (%s)"
              % (mod, len(cell.intent_rules()), len(log["dropped"]), " ".join(sorted(log["dropped"])),
                 " ".join(sorted(log["unbound"])) or "none", len(log["released"]), " ".join(sorted(log["released"]))))
    new = json.dumps(rules, indent=1, ensure_ascii=False) + "\n"     # the file's own format
    if "--check" in argv:
        sys.exit(0 if new == raw else 1)
    if new != raw:
        open(INTENT, "w", encoding="utf-8", newline="\n").write(new)


if __name__ == "__main__":
    main(sys.argv[1:])
