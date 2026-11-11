"""place_flow.py: a fresh board, end to end, from its intent (PLACEMENT.md, "Writing intent").

    py -3.12 place_flow.py <dir> <intent.json> [--no-auto] [--soft-forbid] [--skip-finish] [--fold-post]

<dir> holds ONE board: <stem>.net, <stem>.board.json (the notes -- outline, cutouts, pairs,
layers; any placements in it are kept only for parts nothing else places, i.e. the
post_route_refs) and <stem>.parts.json (place_geom.py). The project's footprints come from
PCBFLOW_FOOTPRINT_DIRS / PCBFLOW_PROJECT, as for layout.py.

  1. intent    the rules JSON, plus place_intent's defaults -- auto_decaps, auto_singles,
               auto_floorplan -- for any the file does not already carry (by their `src`);
               --no-auto takes the file as it is. Written to flow/intent.json.
               Every `current` rule sets its net's width (place_intent.widths, IPC-2221
               outer), never below the notes' own net_widths. Nets with no `current` rule
               are sized by the router from quality.power_paths (router.model.power_width)
               -- unless net_widths states a width, which wins; where that stated width is
               under a declared, unwaived path's need the report says so (WIDTH lines).
  2. place     place_init (stages 1-6, forbid repair), then place_cells (each free cell's
               turn chosen by routing it; forbid zones hard unless --soft-forbid).
  3. gates     layout.py on the placed board -- courtyards, stitching, the legality gate.
               A refusal stops the flow here.
  4. route     the router's score of the placed board (score.py --intent: open, pairs,
               uncoupled, vias, length, floor), then finish.py (route + the finish chain:
               DRC-driven retry, close_last) and quality.py --brief.
               --skip-finish stops after the score (minutes instead of tens of minutes).
  5. report    flow/report.md and flow/report.json: score, floor and FORBID lines, finish
               DRC, quality FAIL / OPEN, and where every coordinate came from
               (flow/provenance.json: ref -> the rule or stage that set it).

--fold-post PLACES THE POST-ROUTE PARTS WITH EVERYTHING ELSE. A board whose notes list
post_route_refs (strap resistors, test points) and post_route_nets has them dropped onto the
FINISHED route by layout's post-route pass, at the free spot the copper left -- measured
against one route, so on a fresh placement they land on tracks (optical: solder-mask bridges
of Rs/Cs pads against I2C2_SCL) or nowhere. Folded, the lists are emptied, the parts are
placed by the intent (or auto_singles) and their nets routed with the rest. parts.json must
carry their geometry (place_geom on the full netlist); a missing one stops the flow, named.

Where a part finds no room the report says so -- the part and the region it was held to
(place_init's "no room", the silk labeller's "no free site") -- rather than leaving it to a
DRC count.

The board.json in <dir> is rewritten with the flow's placements (the input is kept as
flow/input.board.json). Every stage's output is in <dir>/flow/.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_intent as pi  # noqa: E402
from place_refine import KICAD_PY, _stem  # noqa: E402

AUTO = {"auto_decaps (netlist)": "decaps", "auto_singles (netlist)": "singles",
        "auto_floorplan (netlist)": "floorplan"}


def _run(cmd, log, cwd=HERE):
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = (p.stdout or "") + (p.stderr or "")
    log.write("$ %s\n%s\n[rc %d, %.0f s]\n\n" % (" ".join(cmd), out, p.returncode, time.time() - t))
    log.flush()
    return p.returncode, out, time.time() - t


def _intent(rules, parts, notes, net_path, auto):
    have = {r.get("src") for r in rules}
    added = []
    if auto:
        if "auto_decaps (netlist)" not in have:
            new = pi.auto_decaps(parts, notes, pi.read_values(net_path), cells=rules)
            for c in new:
                c.pop("_now", None)
            rules = rules + new
            added.append("auto_decaps %d" % len(new))
        if "auto_singles (netlist)" not in have:
            new = pi.auto_singles(parts)
            rules = rules + new
            added.append("auto_singles %d" % len(new))
        if "auto_floorplan (netlist)" not in have:
            new = pi.auto_floorplan(parts)
            rules = rules + new
            added.append("auto_floorplan %d" % len(new))
    return rules, added


def _klass(why):
    w = why or ""
    for k, pat in (("place_cells", r"^place_cells"), ("group (cell)", r"group"), ("fixed by rule", r"rule \d+ (fixed|pin)"),
                   ("panel", r"rule \d+ panel"), ("decap at pin", r"^decap"), ("near its target", r"^near"),
                   ("net graph", r"net graph"), ("carried from input", r"^carried"), ("keep", r"^keep")):
        if re.search(pat, w):
            return k
    return "other"


def _regions_of(rules, parts):
    """{ref: region name} from the in_region rules."""
    return {x: r["region"] for r in rules if r["kind"] == "in_region" for x in pi._refs(r["refs"], parts)}


def flow(d, intent_path, auto=True, soft=False, skip_finish=False, fold=False):
    d = os.path.abspath(d)
    stem = _stem(d)
    base = os.path.basename(stem)
    fd = os.path.join(d, "flow")
    os.makedirs(fd, exist_ok=True)
    log = open(os.path.join(fd, "flow.log"), "w", encoding="utf-8")
    T = {}
    notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    if not os.path.exists(os.path.join(fd, "input.board.json")):
        shutil.copy(stem + ".board.json", os.path.join(fd, "input.board.json"))
    notes = json.load(open(os.path.join(fd, "input.board.json"), encoding="utf-8"))
    parts_path = stem + ".parts.json"
    parts = json.load(open(parts_path, encoding="utf-8"))["parts"]
    if fold:
        post = list(notes.get("post_route_refs", ()))
        miss = [r_ for r_ in post if r_ not in parts]
        if miss:
            raise SystemExit("place_flow: --fold-post but parts.json has no geometry for %s -- re-run place_geom "
                             "on the full netlist" % " ".join(miss))
        notes["post_route_refs"], notes["post_route_nets"] = [], []
        for r_ in post:
            notes.get("placements", {}).pop(r_, None)

    # 1. intent
    rules, added = _intent(json.load(open(intent_path, encoding="utf-8")), parts, notes, stem + ".net", auto)
    # power is a width, from the current it carries (place_intent.widths): never narrower
    # than the notes already declare
    nw = dict(notes.get("net_widths", {}) or {})
    widened = []
    for n, w in pi.widths(rules).items():
        if w > nw.get(n, 0.0) + 1e-9:
            widened.append("%s %.2f->%.2f" % (n, nw.get(n, 0.0), w))
            nw[n] = w
    notes["net_widths"] = nw
    # a stated width under what a declared power path needs: the router obeys the statement,
    # quality A1 then fails the path. Said here, by net, so it is fixed in the notes or intent.
    wlines = []
    q_ = notes.get("quality", {}) or {}
    waived = set((q_.get("waive") or {}))
    from router.model import power_width
    for pp in q_.get("power_paths", ()) or ():
        n = pp["net"]
        dsts = pp["to"] if isinstance(pp["to"], (list, tuple)) else [pp["to"]]
        if n not in nw or all("A1:%s %s>%s" % (n, pp["from"], d_) in waived for d_ in dsts):
            continue
        need = power_width(dict(pp, to=[]), q_, {})            # heating width only: no positions yet
        if nw[n] + 1e-6 < need:
            wlines.append("%s: net_widths %.2f mm, %s -> %s at %.2f A needs %.2f mm (IPC-2221) -- give it a "
                          "`current` rule or widen it" % (n, nw[n], pp["from"], ",".join(dsts), float(pp["amps"]), need))
    ip = os.path.join(fd, "intent.json")
    json.dump(rules, open(ip, "w"), indent=1)
    say = lambda s: (print("place_flow: " + s), log.write("## " + s + "\n"), log.flush())
    say("intent: %d rules%s" % (len(rules), (" (+ " + ", ".join(added) + ")") if added else ""))
    if widened:
        say("net widths from `current`: " + ", ".join(widened))
    for w_ in wlines:
        say("WIDTH " + w_)

    # 2. place_init, place_cells
    init = os.path.join(fd, "init.json")
    rc, out, T["place_init"] = _run([sys.executable, "place_init.py", stem, ip, "--out", init], log)
    if rc not in (0, 3):
        raise SystemExit("place_flow: place_init failed (see flow/flow.log)\n" + out[-800:])
    init_log = [line for line in out.splitlines() if line.startswith("place_init:")]
    room = []
    reg = _regions_of(rules, parts)
    for line in init_log:
        m = re.search(r"\d+ with no room: (.*)$", line)
        if m:
            room += ["%s (place_init, %s)" % (x, "region " + reg[x] if x in reg else "board")
                     for x in m.group(1).split()]
    pl = json.load(open(init))
    why = json.load(open(init[:-5] + ".why.json"))
    for r_, v in notes.get("placements", {}).items():         # what nothing places (post-route parts)
        if r_ not in pl:
            pl[r_] = v
            why[r_] = "carried from input (not in parts.json: %s)" % (
                "post_route_refs" if r_ in notes.get("post_route_refs", ()) else "no geometry")
    json.dump(dict(notes, placements=pl), open(stem + ".board.json", "w"), indent=0)
    cmd = [sys.executable, "place_cells.py", d, ip, "--parts", parts_path] + (["--soft-forbid"] if soft else [])
    # place_cells keeps its own work in <dir>/cells; a stale parent route there would be a
    # different placement's
    shutil.rmtree(os.path.join(d, "cells"), ignore_errors=True)
    rc, out, T["place_cells"] = _run(cmd, log)
    if rc != 0:
        raise SystemExit("place_flow: place_cells failed (see flow/flow.log)\n" + out[-800:])
    cells_log = [line for line in out.splitlines() if line.startswith("place_cells:")]
    pc = json.load(open(stem + ".cells.json"))
    for r_ in pc:
        if pl.get(r_) != pc[r_]:
            why[r_] = "place_cells: cell turned / repaired by route (%s)" % why.get(r_, "")
    pl = pc
    json.dump(dict(notes, placements=pl), open(stem + ".board.json", "w"), indent=0)
    json.dump(why, open(os.path.join(fd, "provenance.json"), "w"), indent=0)

    # 3. layout's gates
    rc, out, T["layout"] = _run([KICAD_PY, os.path.join(HERE, "layout.py"), stem], log)
    gates = [line.strip() for line in out.splitlines()
             if re.search(r"refused|overlap|no room|stitch:|could only", line)][:12]
    if rc != 0:
        say("layout REFUSED the placement -- the flow stops at the gates")
        _report(fd, base, rules, init_log, cells_log, gates, None, None, None, why, T, refused=out[-1500:])
        return 2

    # 4. score, finish, quality
    rc, out, T["score"] = _run([sys.executable, "-m", "router.score", stem, "--save", "auto", "--intent", ip,
                                "--parts", parts_path], log)
    score = None
    for line in reversed(out.splitlines()):
        try:
            score = json.loads(line)
            break
        except ValueError:
            continue
    fin = qual = None
    if not skip_finish:
        rc, out, T["finish"] = _run([KICAD_PY, os.path.join(HERE, "finish.py"), stem], log)
        for line in out.splitlines():
            m = re.search(r"no free site for: (.*)$", line)
            if m:
                room += ["%s (silk label: no free site)" % x.strip() for x in m.group(1).split(",")]
        try:
            dr = json.load(open(stem + ".finish.drc.json", encoding="utf-8"))
            fin = {"unconnected": len(dr.get("unconnected_items", [])), "violations": len(dr.get("violations", [])),
                   "rc": rc}
            fin["by_type"] = dict(collections.Counter(v.get("type") for v in dr.get("violations", [])))
            fin["unconnected_nets"] = sorted({i.get("description", "").split("[")[-1].split("]")[0]
                                              for x in dr.get("unconnected_items", []) for i in x.get("items", [])
                                              if "[" in i.get("description", "")})
        except (OSError, ValueError):
            fin = {"error": out[-600:], "rc": rc}
        rc, out, T["quality"] = _run([KICAD_PY, os.path.join(HERE, "quality.py"), "--brief", stem], log)
        try:
            q = json.load(open(stem + ".quality.json", encoding="utf-8"))
            qual = {"fail": q.get("fail"), "open": q.get("open"), "waived": q.get("waived"),
                    "failed": [r.get("id") or r.get("rule") for r in q.get("results", [])
                               if str(r.get("status", "")).upper() == "FAIL"][:20]}
        except (OSError, ValueError):
            qual = {"error": out[-600:]}
    _report(fd, base, rules, init_log, cells_log, gates, score, fin, qual, why, T, room=room, width=wlines)
    return 0


def _report(fd, base, rules, init_log, cells_log, gates, score, fin, qual, why, T, refused=None, room=(), width=()):
    forbid = [l_ for l_ in init_log + cells_log if "FORBID" in l_]
    prov = collections.Counter(_klass(w) for w in why.values())
    S = {k: (score or {}).get(k) for k in ("open", "pairs", "islands", "uncoupled", "vias", "length_mm", "floor",
                                            "failed", "faulted", "floor_breaches", "error")}
    rep = {"board": base, "rules": len(rules), "score": S, "forbid": forbid, "gates": gates, "finish": fin,
           "quality": qual, "provenance": dict(prov), "seconds": {k: round(v) for k, v in T.items()},
           "refused": refused, "no_room": list(room), "width": list(width)}
    json.dump(rep, open(os.path.join(fd, "report.json"), "w"), indent=1)
    L = ["# place_flow: %s" % base, ""]
    if refused:
        L += ["**layout REFUSED the placement.**", "", "```", refused.strip()[-1200:], "```", ""]
    if score:
        L += ["| route score | open | pairs | islands | uncoupled | vias | length | floor |",
              "|---|---|---|---|---|---|---|---|",
              "| | %s | %s | %s | %s | %s | %s | %s |" % tuple(S[k] for k in ("open", "pairs", "islands", "uncoupled",
                                                                             "vias", "length_mm", "floor")), ""]
        if S.get("failed"):
            L.append("failed nets: " + " ".join(S["failed"]))
        for b in S.get("floor_breaches") or ():
            L.append("FLOOR %s %s" % (b[1], b[2]))
    L += ["FORBID: " + (" / ".join(forbid) if forbid else "none")]
    L += ["NO ROOM: " + ("; ".join(room) if room else "none")]
    L += ["WIDTH " + w_ for w_ in width]
    if fin:
        L += ["", "finish: %s" % (fin.get("error") or "%d unconnected%s, %d violation(s)%s" % (
            fin["unconnected"], (" (" + " ".join(fin.get("unconnected_nets", ())) + ")") if fin["unconnected"] else "",
            fin["violations"], (" (" + ", ".join("%s %d" % kv for kv in sorted(fin.get("by_type", {}).items())) + ")")
            if fin["violations"] else ""))]
    if qual:
        L += ["quality: %s" % (qual.get("error") or "%s FAIL, %s OPEN%s" % (
            qual["fail"], qual["open"], (" (" + " ".join(map(str, qual["failed"])) + ")") if qual.get("failed") else ""))]
    if gates:
        L += ["", "layout notes:"] + ["  " + g for g in gates]
    L += ["", "placement log:"] + ["  " + l_ for l_ in init_log + cells_log if "fixed " not in l_]
    L += ["", "provenance (flow/provenance.json, per ref): " + ", ".join("%s %d" % kv for kv in prov.most_common()),
          "", "seconds: " + ", ".join("%s %d" % (k, v) for k, v in T.items())]
    open(os.path.join(fd, "report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("intent")
    ap.add_argument("--no-auto", action="store_true")
    ap.add_argument("--soft-forbid", action="store_true")
    ap.add_argument("--skip-finish", action="store_true")
    ap.add_argument("--fold-post", action="store_true", help="place post_route_refs with the rest (see the doc)")
    a = ap.parse_args(argv)
    return flow(a.dir, os.path.abspath(a.intent), not a.no_auto, a.soft_forbid, a.skip_finish, a.fold_post)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
