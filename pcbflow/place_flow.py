"""place_flow.py: a fresh board, end to end, from its intent (PLACEMENT.md, "Writing intent").

    py -3.12 place_flow.py <dir> <intent.json> [--no-auto] [--soft-forbid] [--skip-finish] [--fold-post]

<dir> holds ONE board: <stem>.net, <stem>.board.json (the notes -- outline, cutouts, pairs,
layers; any placements in it are kept only for parts nothing else places, i.e. the
post_route_refs) and <stem>.parts.json (place_geom.py; when it is missing the flow makes it
with place_geom --from-net, from the footprints alone -- no layout needed). The project's footprints come from
PCBFLOW_FOOTPRINT_DIRS / PCBFLOW_PROJECT, as for layout.py.

  1. intent    the rules JSON, plus place_intent's defaults -- auto_decaps and
               auto_floorplan (auto_singles only with --auto-singles) -- for any the file
               does not already carry (by their `src`);
               --no-auto takes the file as it is. Written to flow/intent.json.
               Every `current` rule sets its net's width (place_intent.widths, IPC-2221
               outer), never below the notes' own net_widths. Nets with no `current` rule
               are sized by the router from quality.power_paths (router.model.power_width)
               -- unless net_widths states a width, which wins; once placed, a stated
               width under an unwaived path's need (heating + drop over the placed
               distance, a `split` path as a tapped trunk) is RAISED to it, capped at
               POWER_W_MAX (WIDTH lines;
               --keep-widths only reports).
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
import numpy as np
import math
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
        "auto_floorplan (netlist)": "floorplan", "auto_switcher (netlist)": "switcher"}


def _run(cmd, log, cwd=HERE):
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = (p.stdout or "") + (p.stderr or "")
    log.write("$ %s\n%s\n[rc %d, %.0f s]\n\n" % (" ".join(cmd), out, p.returncode, time.time() - t))
    log.flush()
    return p.returncode, out, time.time() - t


def _intent(rules, parts, notes, net_path, auto, singles=False):
    have = {r.get("src") for r in rules}
    added = []
    # ⚠ A HOLE'S KEEP-OUT IS THE CAD'S, NOT THE AUTHOR'S (ui_board holdout 3, 2026-11-12): the cold
    # intent guessed 1.0 round a spigot and stopped on the CAD-fixed encoder 0.24 inside it. A
    # cutout that carries `keepout_d` -- the boss, post or head that lands on the board there, as
    # the board generator reads it from the CAD -- sets its hole rule: added when the intent has
    # none at that xy, overwritten (and said so) when the intent typed another number.
    for c in notes.get("cutouts", ()) or ():
        if not c.get("keepout_d"):
            continue
        k = max(0.0, (float(c["keepout_d"]) - float(c["d"])) / 2.0)
        same = [r for r in rules if r["kind"] == "hole"
                and math.hypot(r["xy"][0] - c["xy"][0], r["xy"][1] - c["xy"][1]) < 0.05]
        src = "notes cutouts keepout_d (CAD%s)" % (": " + c["what"] if c.get("what") else "")
        for r in same:
            if abs(float(r.get("keepout", 0.0)) - k) > 1e-6:
                added.append("hole (%.1f, %.1f) keep-out %.2f -> %.2f from the CAD"
                             % (c["xy"][0], c["xy"][1], float(r.get("keepout", 0.0)), k))
                r["keepout"], r["src"] = k, src
        if not same:
            rules = rules + [dict(kind="hole", why=c.get("what") or "mounting hole: the CAD's keep-out",
                                  src=src, hard=True, xy=list(c["xy"]), d=float(c["d"]), keepout=k)]
            added.append("hole (%.1f, %.1f) from the CAD" % (c["xy"][0], c["xy"][1]))
    if auto:
        if "auto_decaps (netlist)" not in have:
            new = pi.auto_decaps(parts, notes, pi.read_values(net_path), cells=rules,
                                 descriptions=pi.read_descriptions(net_path))
            for c in new:
                c.pop("_now", None)
            rules = rules + new
            added.append("auto_decaps %d" % len(new))
        if "auto_switcher (netlist)" not in have:
            new = pi.auto_switcher(parts, cells=rules)
            rules = rules + new
            added.append("auto_switcher %d" % len(new))
        # ⚠ auto_singles IS OPT-IN (lead ruling, 2026-11-12): two boards where the test pads'
        # 8 mm `near` cost routing -- output_panel op12, 3 rules: a pair fault and 20.9 mm
        # uncoupled against op14's 0 / 0.52. A test pad's `access` rule is what matters;
        # where it sits along its net is a nice-to-have. --auto-singles turns it on.
        if singles and "auto_singles (netlist)" not in have:
            new = pi.auto_singles(parts)
            rules = rules + new
            added.append("auto_singles %d" % len(new))
        if "auto_floorplan (netlist)" not in have:
            new = pi.auto_floorplan(parts)
            # ⚠ THE AUTHOR'S TIE BEATS THE GUESS (lever_sensor holdout 2d, 2026-11-12): U6, the
            # BOOT0 detector, is `near` U3.44 by the author's rule; auto_floorplan read its
            # BUS_SENSE input as analog and asked it 6 mm off the MCU's USB edge. The two
            # cannot both hold and FLOOR reported a breach no placement could fix. A part
            # the author ties (near / decap) to a part on the other side of an auto `apart`
            # leaves that rule; the part it is tied to stays on its own side.
            tie = set()
            for r_ in rules:
                if r_["kind"] in ("near", "decap"):
                    x = r_.get("ref") or r_.get("cap")
                    y = (r_.get("target") or r_.get("pin") or "").split(".")[0]
                    if x and y:
                        tie.add((x, y))         # x is tied TO y: x leaves, y stays
            for r_ in new:
                if r_["kind"] != "apart":
                    continue
                a_, b_ = list(r_["a"]), list(r_["b"])
                gone = sorted({m for m in b_ for o in a_ if (m, o) in tie})
                gone_a = sorted({m for m in a_ for o in b_ if (m, o) in tie} - set(gone))
                if gone or gone_a:
                    r_["b"] = [m for m in b_ if m not in gone]
                    r_["a"] = [m for m in a_ if m not in gone_a]
                    added.append("auto_floorplan: %s left out of '%s' (tied by the intent's near/decap)"
                                 % (" ".join(gone + gone_a), r_["why"]))
            new = [r_ for r_ in new if r_["kind"] != "apart" or (r_["a"] and r_["b"])]
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


def _raise_widths(notes, parts, pl, keep=False):
    """A STATED WIDTH UNDER WHAT A DECLARED POWER PATH NEEDS IS RAISED, once the parts have
    positions. net_widths wins over the router's own sizing (router.model.power_width), and
    on a fresh board the statement is usually the hand board's, sized for its routes: optical
    V5_PRE stated 0.35 mm, half its 183 mm on In2, dropped 51 mV against 50 (lead,
    2026-11-11: widen the trunk rather than rework the placement). The need is the router's
    own -- IPC-2221 heating and the drop over the placed distance, a `split` path as a
    tapped trunk -- capped at POWER_W_MAX; waived paths (quality.waive "A1:...") are left
    alone. keep=True (--keep-widths) only reports. Returns the WIDTH lines; edits notes."""
    from router.model import power_width, POWER_W_MAX
    q_ = notes.get("quality", {}) or {}
    waived = set(q_.get("waive") or {})
    nw = notes.setdefault("net_widths", {})
    P = pi.Placed(parts, pl)
    at = {}
    for r_ in parts:
        if r_ in pl:
            for q in parts[r_]["pads"]:
                if q["num"]:
                    try:
                        at["%s.%s" % (r_, q["num"])] = tuple(float(v) for v in P.pad(r_, q["num"]))
                    except (KeyError, ValueError, IndexError):
                        pass
    need = {}
    for pp in q_.get("power_paths", ()) or ():
        n = pp["net"]
        dsts = pp["to"] if isinstance(pp["to"], (list, tuple)) else [pp["to"]]
        live = [d_ for d_ in dsts if "A1:%s %s>%s" % (n, pp["from"], d_) not in waived]
        if n not in nw or not live:
            continue
        # a "split" path feeds taps along its run (optical V5_PRE: ten emitter resistors):
        # a uniformly tapped trunk drops what HALF its current would over the whole length,
        # where power_width charges all of it to the far end (0.92 mm asked for 0.21 A).
        # Modelled here, not in the router's own sizing: changing that cost the series gate
        # a pair on ONX03 (2026-11-11).
        pp_ = dict(pp, to=live, amps=float(pp["amps"]) / 2.0) if pp.get("split") else dict(pp, to=live)
        w = min(POWER_W_MAX, power_width(pp_, q_, at))
        if w > need.get(n, (0.0,))[0]:
            need[n] = (w, pp["from"], live, float(pp["amps"]))
    out = []
    for n, (w, src, live, amps) in sorted(need.items()):
        if nw[n] + 1e-6 < w:
            out.append("%s: net_widths %.2f mm, %s -> %s at %.2f A needs %.2f mm (heating + drop, router.model."
                       "power_width)%s" % (n, nw[n], src, ",".join(live[:3]) + ("..." if len(live) > 3 else ""), amps, w,
                                           " -- kept (--keep-widths)" if keep else " -- raised"))
            if not keep:
                nw[n] = w
    return out


def _pours(notes, parts, pl, rules, base_zones):
    """notes["zones"] = the input's own zones + one per `pour` rule at the placed pins
    (place_intent.pour_poly), priority 1 by default so it wins its region over a board-wide
    ground pour on the same layer. Returns the POUR lines for the report."""
    P = pi.Placed(parts, pl)
    notes_r = dict(notes, _regions={r["name"]: r["poly"] for r in rules if r["kind"] == "region"})
    amps_of = lambda r: pi.pour_amps(r, notes)
    # a notes file that is itself a flow's output already carries last run's pours: a
    # dict zone on a pour rule's own net and layer is replaced, not stacked on (two +24V
    # pours on B.Cu, motor_ctrl v4: DRC zones_intersect)
    mine = {(r["net"], r["layer"]) for r in rules if r["kind"] == "pour"}
    base_zones = [z for z in base_zones if not (isinstance(z, dict) and (z.get("net"), z.get("layer")) in mine)]
    zones, out = list(base_zones), []
    for r in rules:
        if r["kind"] != "pour":
            continue
        poly = pi.pour_poly(r, P, notes_r, amps_of(r))
        if poly is None:
            out.append("%s on %s: NO OUTLINE (region %r unknown, no pins along) -- not poured"
                       % (r["net"], r["layer"], r.get("region")))
            continue
        # ⚠ TWO POURS OF DIFFERENT NETS ON ONE LAYER NEED DIFFERENT PRIORITIES (motor_ctrl,
        # 2026-11-11): +5V_RAW (L2-F2) and +5V (F2-J5) both on F.Cu at priority 1 met at F2:
        # DRC zones_intersect, and the fill gave neither a clean edge. A later pour on a layer
        # that already holds one goes a step above it; KiCad fills the higher first and keeps
        # clearance, which is what two rails meeting at a fuse want.
        pr = int(r.get("priority", 1))
        taken = [z["priority"] for z in zones[len(base_zones):] if z["layer"] == r["layer"] and z["net"] != r["net"]]
        if "priority" not in r and pr in taken:
            pr = max(taken) + 1
        zones.append({"net": r["net"], "layer": r["layer"], "poly": poly, "priority": pr})
        f = pi.pour_foreign(r, P, poly)
        out.append("%s on %s %s: %d corner(s), %s" % (
            r["net"], r["layer"], ("region " + r["region"]) if r.get("region") else "along " + "-".join(r["along"]),
            len(poly), ("%d other net pad(s) inside -- the layer may not have room: %s" % (len(f), " ".join(f[:8])))
            if f else "no other net's pad inside"))
    notes["zones"] = zones
    return out


def _project_guard(stem):
    """Refuse a run whose finish chain would write into a MAIN checkout.

    ⚠ (lead, 2026-11-11): the motor_ctrl trial ran with PCBFLOW_PROJECT on the main
    checkout's elec/, and finish's export_geom rewrote elec/geom/motor_ctrl.geom.json
    there -- a trial's geometry in the shipped project, which blocked a propagation until
    it was restored. The project (PCBFLOW_PROJECT, else the stem's grandparent, as
    finish.project_dir) must not sit in a git MAIN working tree (a .git DIRECTORY); a
    linked worktree (.git file) or a plain scratch folder is fine. PCBFLOW_ALLOW_MAIN=1 for
    a deliberate run."""
    env = os.environ.get("PCBFLOW_PROJECT")
    proj = os.path.abspath(env) if env else os.path.dirname(os.path.dirname(os.path.abspath(stem)))
    if os.environ.get("PCBFLOW_ALLOW_MAIN") == "1":
        return proj
    d_ = proj
    while True:
        g = os.path.join(d_, ".git")
        if os.path.isdir(g):
            raise SystemExit("place_flow: REFUSED -- the project %s is inside the main checkout %s; the finish "
                             "chain writes geom/ and out/ there. Point PCBFLOW_PROJECT at a scratch worktree "
                             "(PCBFLOW_ALLOW_MAIN=1 to mean it)." % (proj, d_))
        if os.path.isfile(g):
            return proj                                 # a linked worktree: scratch by design
        up = os.path.dirname(d_)
        if up == d_:
            return proj
        d_ = up


def flow(d, intent_path, auto=True, soft=False, skip_finish=False, fold=False, keep_widths=False, singles=False):
    d = os.path.abspath(d)
    stem = _stem(d)
    _project_guard(stem)
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
    if not os.path.exists(parts_path):
        # a fresh board has no layout to read geometry from: every netlist part's pads and
        # courtyard come from its footprint (place_geom --from-net; identical to a layout dump)
        rc, out, T["geom"] = _run([KICAD_PY, os.path.join(HERE, "place_geom.py"), stem, "pads", "--from-net"], log)
        if rc or not os.path.exists(parts_path):
            raise SystemExit("place_flow: place_geom --from-net failed: " + out[-2000:])
    parts = json.load(open(parts_path, encoding="utf-8"))["parts"]
    if fold:
        post = list(notes.get("post_route_refs", ()))
        miss = [r_ for r_ in post if r_ not in parts]
        if miss:
            raise SystemExit("place_flow: --fold-post but parts.json has no geometry for %s -- re-run place_geom "
                             "--from-net (every netlist part)" % " ".join(miss))
        notes["post_route_refs"], notes["post_route_nets"] = [], []
        for r_ in post:
            notes.get("placements", {}).pop(r_, None)

    # 1. intent
    rules, added = _intent(json.load(open(intent_path, encoding="utf-8")), parts, notes, stem + ".net", auto, singles)
    # TWO-SIDED (opt-in: `side` rules with side "B", place_intent.back_refs). The parts file is
    # turned over ON DISK, once (mirror_back is idempotent), so place_init, score and every
    # check read the geometry layout builds; layout turns the same parts over from back_refs.
    back = pi.back_refs(rules)
    if back:
        parts = pi.mirror_back(parts, back)
        pj = json.load(open(parts_path, encoding="utf-8"))
        pj["parts"] = parts
        json.dump(pj, open(parts_path, "w", encoding="utf-8"), indent=0)
        notes["back_refs"] = sorted(set(notes.get("back_refs", ())) | set(back))
        print("place_flow: two-sided: %d part(s) on the back (B.Cu)" % len(back))
        log.write("## two-sided: %s on the back\n" % " ".join(back))
    # power is a width, from the current it carries (place_intent.widths): never narrower
    # than the notes already declare
    nw = dict(notes.get("net_widths", {}) or {})
    widened = []
    for n, w in pi.widths(rules).items():
        if w > nw.get(n, 0.0) + 1e-9:
            widened.append("%s %.2f->%.2f" % (n, nw.get(n, 0.0), w))
            nw[n] = w
    notes["net_widths"] = nw
    wlines = []
    for r_ in rules:
        if r_["kind"] == "panel":
            try:
                pi.panel_face(r_)
            except ValueError as e:
                raise SystemExit("place_flow: intent refused -- %s" % e)
    ip = os.path.join(fd, "intent.json")
    json.dump(rules, open(ip, "w"), indent=1)
    say = lambda s: (print("place_flow: " + s), log.write("## " + s + "\n"), log.flush())
    floor = pi.unregioned_sensitive(parts, rules)
    for f_ in floor:
        say("WARN " + f_)
    say("intent: %d rules%s" % (len(rules), (" (+ " + ", ".join(added) + ")") if added else ""))
    if widened:
        say("net widths from `current`: " + ", ".join(widened))

    # 2. place_init, place_cells
    init = os.path.join(fd, "init.json")
    rc, out, T["place_init"] = _run([sys.executable, "place_init.py", stem, ip, "--out", init], log)
    if rc not in (0, 3):
        raise SystemExit("place_flow: place_init failed (see flow/flow.log)\n" + out[-800:])
    init_log = [line for line in out.splitlines() if line.startswith("place_init:")]
    # a GROW is the floorplan the board was placed in: every later gate judges that one
    gp = init[:-5] + ".grow.json"
    if os.path.exists(gp):
        grown = json.load(open(gp))
        for r in rules:
            if r["kind"] == "region" and r["name"] in grown:
                r["poly"] = grown[r["name"]]
        json.dump(rules, open(ip, "w"), indent=1)
        say("regions grown by place_init (GROW): " + ", ".join(sorted(grown)))
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
    # ⚠ THE FLOW STOPS BEFORE LAYOUT ON A PLACEMENT IT KNOWS IS BROKEN (lever_sensor holdouts
    # 1 / 1b, 2026-11-12): a part with no room was left overlapping and a connector sat wholly
    # off the board, and both went on to layout, which refused them as courtyard overlaps --
    # naming the victims, not the cause. Two stops, each naming the part and its rules:
    #   NO ROOM  -- place_init found no legal seat; the rules that bind the part are listed
    #   BROKEN   -- a hard MECHANICAL rule (outline, keepout, hole, fixed, height) fails
    if room:
        bind = []
        for x in room:
            ref_ = x.split(" ", 1)[0]
            rs = [_rule_line(r_) for r_ in rules if ref_ in _rule_refs(r_, parts)]
            bind.append("%s -- bound by: %s" % (x, "; ".join(rs) if rs else "no rule (the board is full)"))
        say("NO ROOM -- the flow stops before layout: " + " | ".join(bind))
        _report(fd, base, rules, init_log, [], [], None, None, None, why, T,
                refused="place_init: NO ROOM\n" + "\n".join(bind), floor=floor, room=room)
        return 2
    notes_k = dict(notes, _panel=[r_ for r_ in rules if r_["kind"] == "panel"])
    P_k = pi.Placed(parts, pl)
    broken = []
    for i_, r_ in enumerate(rules):
        if r_["kind"] in ("outline", "keepout", "hole", "fixed", "height") and r_.get("hard", True):
            for s_, ref_, det in pi.check(r_, P_k, notes_k):
                if s_ < -0.05:
                    broken.append("rule %d %s: %s %s (%.2f mm)" % (i_, r_["kind"], ref_, det, s_))
    if broken:
        say("BROKEN hard rules -- the flow stops before layout: " + " | ".join(broken[:8]))
        _report(fd, base, rules, init_log, [], [], None, None, None, why, T,
                refused="intent check: BROKEN hard mechanical rules\n" + "\n".join(broken[:20]), floor=floor, room=room)
        return 2
    for w_ in _chain_warns(rules, parts, pl):
        say("WARN " + w_)
        floor.append(w_)
    wlines = _raise_widths(notes, parts, pl, keep_widths)
    for w_ in wlines:
        say("WIDTH " + w_)
    base_zones = list(notes.get("zones", []) or [])
    plines = _pours(notes, parts, pl, rules, base_zones)
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
    plines = _pours(notes, parts, pl, rules, base_zones)
    for p_ in plines:
        say("POUR " + p_)
    w2 = _raise_widths(notes, parts, pl, keep_widths)
    for w_ in w2:
        if w_ not in wlines:
            say("WIDTH " + w_)
            wlines.append(w_)
    json.dump(dict(notes, placements=pl), open(stem + ".board.json", "w"), indent=0)
    json.dump(why, open(os.path.join(fd, "provenance.json"), "w"), indent=0)

    # 3. layout's gates
    rc, out, T["layout"] = _run([KICAD_PY, os.path.join(HERE, "layout.py"), stem], log)
    gates = [line.strip() for line in out.splitlines()
             if re.search(r"refused|overlap|no room|stitch:|could only", line)][:12]
    if rc != 0:
        say("layout REFUSED the placement -- the flow stops at the gates")
        _report(fd, base, rules, init_log, cells_log, gates, None, None, None, why, T, refused=out[-1500:], floor=floor,
                room=room, width=wlines, fill=pi.region_fill(rules, parts, pl))
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
            # ⚠ COUNT AS finish.py COUNTS (lever_sensor holdout 2d, 2026-11-12): finish said "0
            # violation(s)" and this report said 10 -- nine silk_overlap WARNINGS and the J1/J2
            # courtyard the project DECLARES (pcb_declared.py). Errors that are not declared are
            # the violations; declared ones and warnings are listed apart.
            vs = dr.get("violations", [])
            warn = [v for v in vs if v.get("severity") == "warning"]
            err = [v for v in vs if v.get("severity") != "warning"]
            try:
                import finish as _fin
                import netcheck as _nc
                ok_, bad_ = _nc.classify_violations(dict(dr, violations=err), _fin._declared(stem))
            except Exception:                       # no project / no declarations: all count
                ok_, bad_ = [], [(v.get("type"), []) for v in err]
            fin = {"unconnected": len(dr.get("unconnected_items", [])), "violations": len(bad_),
                   "declared": len(ok_), "warnings": len(warn), "rc": rc}
            fin["by_type"] = dict(collections.Counter(t for t, _ in bad_))
            fin["warn_by_type"] = dict(collections.Counter(v.get("type") for v in warn))
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
    _report(fd, base, rules, init_log, cells_log, gates, score, fin, qual, why, T, room=room, width=wlines, pours=plines,
            floor=floor, fill=pi.region_fill(rules, parts, pl))
    return 0


CHAIN_WARN_MM = 20.0     # a near-chain's far signal run longer than this is reported


def _chain_warns(rules, parts, pl):
    """WARN lines: a part held in an author's band, a part `near` it, and that part's other
    small signal nets running far to an IC -- the band is what keeps the chain long.

    ⚠ WHY (motor_ctrl trial, 2026-11-12): the intent banded J1 on the -X edge; U2 (`near` J1)
    followed it and CAN1_TX / RX ran ~30 mm to U4's pins and stayed open in every run. The
    band was an authoring error (J1 is mid-board on the hand board and in the CAD), and
    nothing said so. A WARN, not a stop: the band may be real, and then the run is the price."""
    band = {x: r_["region"] for r_ in rules if r_["kind"] == "in_region" for x in pi._refs(r_["refs"], parts)}
    net_of = {}
    for ref, v in parts.items():
        for q in v["pads"]:
            if q["net"]:
                net_of.setdefault(q["net"], []).append((ref, q["num"]))
    P = pi.Placed(parts, pl)
    out = []
    for r_ in rules:
        if r_["kind"] != "near" or "ref" not in r_ or r_["ref"] not in pl:
            continue
        y = r_["ref"]
        x = (r_.get("target") or "").split(".")[0]
        if x not in band:
            continue
        xn = {q["net"] for q in parts.get(x, {}).get("pads", ()) if q["net"]}
        for q in parts[y]["pads"]:
            nm = q["net"]
            ends = net_of.get(nm, ())
            if (not nm or nm in xn or nm in ("GND",) or pi.SUPPLY.search(nm) or len(ends) > 4):
                continue
            for z, num in ends:
                if z in (x, y) or z not in pl or not re.match(r"^U\d", z):
                    continue
                d = float(np.hypot(*(P.pad(y, q["num"]) - P.pad(z, num))))
                if d > CHAIN_WARN_MM:
                    out.append("CHAIN %s (band %s) -> %s (near %s, %.0f mm) -> %s.%s %s: %.1f mm -- the band holds the "
                               "chain's IC end far away; is %s's band mechanical?"
                               % (x, band[x], y, x, float(r_.get("max_mm", 0)), z, num, nm, d, x))
    return out


def _rule_refs(r, parts):
    """The refs a rule names (ref, refs, cap, a, b, members, anchor; a target part)."""
    out = set()
    for k in ("ref", "cap", "anchor"):
        if isinstance(r.get(k), str):
            out.add(r[k])
    for k in ("refs", "a", "b"):
        if r.get(k):
            out |= set(pi._refs(r[k], parts))
    if isinstance(r.get("target"), str):
        out.add(r["target"].split(".")[0])
    out |= set(r.get("members") or ())
    return out


def _rule_line(r):
    keys = [k for k in ("ref", "target", "a", "b", "tool_d", "min_mm", "max_mm", "region", "edge") if k in r]
    return "%s(%s)" % (r["kind"], ", ".join("%s=%s" % (k, r[k]) for k in keys))


def _report(fd, base, rules, init_log, cells_log, gates, score, fin, qual, why, T, refused=None, room=(), width=(), pours=(),
            floor=(), fill=()):
    forbid = [l_ for l_ in init_log + cells_log if "FORBID" in l_]
    prov = collections.Counter(_klass(w) for w in why.values())
    S = {k: (score or {}).get(k) for k in ("open", "pairs", "islands", "uncoupled", "vias", "length_mm", "floor",
                                            "failed", "faulted", "floor_breaches", "error")}
    rep = {"board": base, "rules": len(rules), "score": S, "forbid": forbid, "gates": gates, "finish": fin,
           "quality": qual, "provenance": dict(prov), "seconds": {k: round(v) for k, v in T.items()},
           "refused": refused, "no_room": list(room), "width": list(width), "pours": list(pours),
           "region_fill": [dict(region=n, area_mm2=round(a), courtyard_mm2=round(u), fill=round(f, 3))
                           for n, a, u, f in fill]}
    json.dump(rep, open(os.path.join(fd, "report.json"), "w"), indent=1)
    L = ["# place_flow: %s" % base, ""]
    if refused:
        L += ["**%s**" % ("place_init found NO ROOM -- the flow stopped before layout." if refused.startswith("place_init: NO ROOM")
                          else "the intent check found BROKEN hard rules -- the flow stopped before layout."
                          if refused.startswith("intent check:") else "layout REFUSED the placement."),
              "", "```", refused.strip()[-1200:], "```", ""]
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
    L += ["POUR " + p_ for p_ in pours]
    if fill:
        L += ["REGION FILL (courtyards / area): " + "  ".join("%s %.2f" % (n, f) for n, _, _, f in fill)]
    L += ["WARN " + f_ for f_ in floor]
    L += [x_.split("place_init: ", 1)[-1] for x_ in init_log if "TANGLE HINT" in x_ or "GROW" in x_]
    if fin:
        L += ["", "finish: %s" % (fin.get("error") or "%d unconnected%s, %d violation(s)%s" % (
            fin["unconnected"], (" (" + " ".join(fin.get("unconnected_nets", ())) + ")") if fin["unconnected"] else "",
            fin["violations"], (" (" + ", ".join("%s %d" % kv for kv in sorted(fin.get("by_type", {}).items())) + ")")
            if fin["violations"] else "") + (", %d declared" % fin["declared"] if fin.get("declared") else "")
            + (", %d warning(s) (%s)" % (fin["warnings"], ", ".join("%s %d" % kv for kv in sorted(fin.get("warn_by_type", {}).items())))
               if fin.get("warnings") else ""))]
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
    ap.add_argument("--keep-widths", action="store_true",
                    help="report a stated net width under its power path's need instead of raising it")
    ap.add_argument("--auto-singles", action="store_true",
                    help="also add auto_singles (a test pad `near` its driver pin) -- off by default")
    a = ap.parse_args(argv)
    return flow(a.dir, os.path.abspath(a.intent), not a.no_auto, a.soft_forbid, a.skip_finish, a.fold_post,
                a.keep_widths, a.auto_singles)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
