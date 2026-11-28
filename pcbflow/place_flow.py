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

import _nowindow  # noqa: F401  (no console windows on Windows: _nowindow.py)
import argparse
import collections
import hashlib
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


def _handoff(init):
    """place_init's hand-off beside its --out (init.handoff.json): {"grown": {region: poly},
    "released": [ref, ...]}. A missing file is an error -- every place_init run writes one."""
    hp = init[:-5] + ".handoff.json"
    if not os.path.exists(hp):
        raise SystemExit("place_flow: place_init wrote no hand-off (%s)" % hp)
    h = json.load(open(hp))
    return dict(h.get("grown") or {}), list(h.get("released") or ())


def _drop_released(rules, released):
    """(rules less the snapshot holds of the refs place_init released, those refs). A mate /
    mechanical / user / physical hold is never dropped, whatever the hand-off names."""
    rel = sorted(set(released))
    keep = [r for r in rules if not (r["kind"] == "fixed" and r.get("ref") in rel and pi.is_snapshot(r))]
    return keep, rel


def _run(cmd, log, cwd=HERE, env=None):
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8", **(env or {})))
    out = (p.stdout or "") + (p.stderr or "")
    log.write("$ %s\n%s\n[rc %d, %.0f s]\n\n" % (" ".join(cmd), out, p.returncode, time.time() - t))
    log.flush()
    return p.returncode, out, time.time() - t


# PCBFLOW_STAGE_CACHE=<dir> (opt-in, bronner 2026-11-23): place_init and place_cells are
# deterministic in their inputs -- two seeds of one A/B arm placed all 455 brain_board parts
# identically (abB/abC 2026-11-22) -- yet each route re-ran them, ~63 min of a ~2.5 h route.
# A stage is keyed on its command (the trial dir masked), the BYTES of its input files, the
# pcbflow + router sources, and the PCBFLOW_/OWNROUTE_/CLOSE_/PLACE_ environment, less
# PCBFLOW_PROJECT (a scratch KiCad project path). OWNROUTE_SEED is left out ONLY for a
# seed_free stage (place_init: no route in it).
# ⚠ PLACE_CELLS IS SEED-DEPENDENT (tpC_s1 / tpC_s2, 2026-11-23): abB/abC agreed only because
# every cell turn there had no room. With U205 free, the two seeds' 900 s parent routes ended
# 82 v 59 open and kept U205 at 90 v 270 -- the cell choice samples route noise, so sharing it
# across seeds would make an A/B's two samples one. place_cells is cached per seed (a re-run).
_KEY_ENV_SKIP = {"PCBFLOW_PROJECT"}
_SRC_HASH = []


def _src_hash():
    if not _SRC_HASH:
        h = hashlib.sha256()
        for root, dirs, files in os.walk(HERE):
            dirs[:] = sorted(x for x in dirs if not x.startswith((".", "__")))
            for f in sorted(files):
                if f.endswith(".py"):
                    h.update(f.encode())
                    h.update(open(os.path.join(root, f), "rb").read())
        _SRC_HASH.append(h.hexdigest())
    return _SRC_HASH[0]


def _key_bytes(f):
    """A key input's bytes. A parts file's courtyards enter as their bounding boxes at 0.05 mm.
    ⚠ KICAD'S COURTYARD CHAIN IS NOT DETERMINISTIC (sc_b / sc_c, 2026-11-23): place_geom's
    GetCourtyard().Outline(0) of the stock QSOP-16 (U32: 20 um steps, 2.675 / 2.695) came out
    as two different 12-point chains on identical runs, one with a spurious (-2.205, 2.6949)
    vertex -- so a parts file never matched byte for byte and the cache never hit. Placement from
    either was identical (init.json byte-equal)."""
    if not os.path.exists(f):
        return b"<none>"
    if not f.endswith(".parts.json"):
        return open(f, "rb").read()
    pj = json.load(open(f, encoding="utf-8"))
    for p in (pj.get("parts") or {}).values():
        c = p.get("crtyd")
        if c:
            xs, ys = [v[0] for v in c], [v[1] for v in c]
            p["crtyd"] = [round(round(min(xs) / 0.05) * 0.05, 2), round(round(max(xs) / 0.05) * 0.05, 2),
                          round(round(min(ys) / 0.05) * 0.05, 2), round(round(max(ys) / 0.05) * 0.05, 2)]
    return json.dumps(pj, sort_keys=True).encode()


def _run_cached(name, cmd, log, d, inputs, outputs, ok=(0,), seed_free=False):
    """_run, memoised under PCBFLOW_STAGE_CACHE: outputs (files or directories) are restored
    on a hit and stored after a run whose rc is in ok. Without the variable it is _run."""
    root = os.environ.get("PCBFLOW_STAGE_CACHE")
    if not root:
        return _run(cmd, log)
    h = hashlib.sha256()
    h.update(name.encode())
    h.update("\0".join(c.replace(d, "<D>") for c in cmd).encode())
    for f in inputs:
        h.update(os.path.basename(f).encode())
        h.update(_key_bytes(f))
    h.update(_src_hash().encode())
    for k in sorted(os.environ):
        if (k.startswith(("PCBFLOW_", "OWNROUTE_", "CLOSE_", "PLACE_")) and k not in _KEY_ENV_SKIP
                and not (seed_free and k == "OWNROUTE_SEED")):
            h.update(("%s=%s\0" % (k, os.environ[k])).encode())
    key = h.hexdigest()[:20]
    c = os.path.join(root, name + "_" + key)
    if os.path.exists(os.path.join(c, "done.json")):
        meta = json.load(open(os.path.join(c, "done.json"), encoding="utf-8"))
        for i, o in enumerate(outputs):
            src = os.path.join(c, "o%d" % i)
            if os.path.isdir(src):
                shutil.rmtree(o, ignore_errors=True)
                shutil.copytree(src, o)
            elif os.path.exists(src):
                shutil.copy(src, o)
        log.write("$ %s\n[STAGE CACHE HIT %s: %s, first run %.0f s]\n%s\n\n" % (" ".join(cmd), name, key, meta["s"],
                                                                              meta["out"]))
        log.flush()
        print("place_flow: stage cache hit: %s %s (saves %.0f s)" % (name, key, meta["s"]))
        return meta["rc"], meta["out"], 0.0
    rc, out, s = _run(cmd, log)
    if rc in ok:
        tmp = c + ".tmp%d" % os.getpid()
        os.makedirs(tmp, exist_ok=True)
        for i, o in enumerate(outputs):
            if os.path.isdir(o):
                shutil.copytree(o, os.path.join(tmp, "o%d" % i))
            elif os.path.exists(o):
                shutil.copy(o, os.path.join(tmp, "o%d" % i))
        json.dump({"rc": rc, "out": out, "s": s, "cmd": cmd}, open(os.path.join(tmp, "done.json"), "w", encoding="utf-8"))
        try:
            os.rename(tmp, c)           # first writer wins; a concurrent twin's copy is left as .tmp
        except OSError:
            pass
    return rc, out, s


def _intent(rules, parts, notes, net_path, auto, singles=False):
    added = []
    # ⚠ AN AUTO RULE SAVED IN AN INTENT GOES STALE (output_board mP0, 2026-11-15): fin_mO's
    # intent carried auto_decaps rules written before the split-ground fix, the `have` check
    # below skipped regenerating them, and all twelve +3V3_A / +5V_A caps stayed ruled "at the
    # regulator" (U2.4 / U10.6) -- nine A2 FAILs the current code would not have made. The
    # netlist rules are DERIVED, so they are derived again every run: any saved in the file are
    # dropped first (auto_singles only when it is on, since it is opt-in).
    if auto:
        drop = {k for k in AUTO if k != "auto_singles (netlist)" or singles}
        old = [r for r in rules if r.get("src") in drop]
        if old:
            rules = [r for r in rules if r.get("src") not in drop]
            added.append("re-derived: dropped %d saved auto rule(s) from the intent file" % len(old))
    have = {r.get("src") for r in rules}
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
        # ⚠ ONE IC's SUPPLY PINS ARE ONE LOAD (output_signal, 2026-11-13): +3V3D at 0.58 A to
        # the H743's 19 VDD pins, unsplit, sized every pin's track for the whole 0.58 A, raised
        # the net to 0.71 mm through the MCU's fanout, and the finish went 0 open -> 11 and timed
        # out. A fan to 4+ pins of one part without `split` is almost always that -- said here.
        _refs = {d_.split(".")[0] for d_ in live}
        if not pp.get("split") and len(live) >= 4 and len(_refs) == 1:
            print("place_flow: WARNING: power path %s %s -> %d pins of %s at %.2f A each, not `split`: "
                  "if those pins draw the amps TOGETHER, mark it split" % (n, pp["from"], len(live),
                                                                          _refs.pop(), float(pp["amps"])))
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
                # raised to the DRAWN width, a raster step over the need (copper.draw_mm), as
                # the router draws a power net it sizes itself (lead ruling 2026-11-26)
                import copper
                nw[n] = min(POWER_W_MAX, copper.draw_mm(w))
    return out


def _tight_warns(rules, parts, P, notes, ic_pads=8):
    """WARN lines for `tight` rules: every unmet one with what it achieved against what it asks,
    and -- met or not -- one whose nets carry no part its stage can move.

    ⚠ A RULE THAT SILENTLY DOES NOTHING (brain_board so_ovw8, 2026-11-22): U21_OVLO's tight (3 mm,
    weight 2 then 8) left the node at 5.7 mm both times, overflow and every seat identical. Its
    members were U221 (the anchor) and R319 / R320 -- small parts with a `near` to a pin, which
    place_init seats as satellites at that pin after the stage the tight pulls; the weight never
    reached them. Satellites follow their own near / decap rule: tighten THAT, not the tight."""
    fixed = {r["ref"] for r in rules if r["kind"] in ("fixed", "pin")}
    sat, anchor = set(), {}
    for r in rules:
        if r["kind"] == "decap":
            sat.add(r["cap"])
            anchor[r["cap"]] = r["pin"].split(".")[0]
        elif (r["kind"] == "near" and r.get("ref") in parts and len(parts[r["ref"]]["pads"]) <= ic_pads):
            sat.add(r["ref"])
            anchor[r["ref"]] = r["target"].split(".")[0]
    out = []
    for i_, r in enumerate(rules):
        if r["kind"] != "tight":
            continue
        members = sorted({ref for ref, p in parts.items() if ref in P.pl
                          for q in p["pads"] if q["net"] in r["nets"]})
        sats = [m for m in members if m in sat]
        anchors = {anchor[m] for m in sats}
        movable = [m for m in members if m not in sat and m not in anchors and m not in fixed]
        res = pi.check(r, P, notes)
        unmet = [(s_, nm, det) for s_, nm, det in res if s_ < -0.05]
        for s_, nm, det in unmet:
            out.append("TIGHT UNMET rule %d: %s %s (%.2f mm over) [%s]" % (i_, nm, det, -s_, r.get("src", "")))
        if sats and not movable:
            out.append("TIGHT CANNOT ACT rule %d (%s): its members %s are pin satellites (seated by their "
                       "near / decap rule after the stage a tight pulls) and the rest are their anchors or "
                       "held -- its weight moves nothing (place_init only seats them first and reserves their strips); "
                       "tighten the satellites' own near / decap max_mm"
                       % (i_, " ".join(r["nets"]), " ".join(sats)))
    return out


def _near_broken(rules, P, notes):
    """(slack, line) for every HARD `near` rule the placement misses by more than 0.05 mm: the
    part, the rule's index, the distance it sits at and the distance it wants."""
    nb = []
    for i_, r_ in enumerate(rules):
        if r_["kind"] == "near" and r_.get("hard", True):
            for s_, ref_, det in pi.check(r_, P, notes):
                if s_ < -0.05:
                    nb.append((s_, "NEAR BROKEN (hard) rule %d: %s %s, wants %g (%.2f mm) [%s]"
                               % (i_, ref_, det, r_["max_mm"], s_, r_.get("src", ""))))
    return nb


def _snapshot_broken(rules, P, notes):
    """[line] for every SNAPSHOT hold (pi.is_snapshot) whose own part breaks a near / decap /
    in_region rule by more than STRANDED_MM on this placement, the hold and the rule named.

    ⚠ A SNAPSHOT IS A WARM START, NOT A REASON (lead 2026-11-22 / 11-23 / 11-26). brain_board p11:
    U5's four input caps (C2 C3 C17 C18) were snapshot-held where mP0 left them, 15-19 mm from U5
    after U5 moved, and quality A2 / A28 failed the laid-out board. A snapshot that keeps its part
    off the part's own rule is a stale memory holding the board against its design; the author
    removes the hold (the rule then places the part)."""
    snap = {r["ref"]: r for r in rules if pi.is_snapshot(r) and r.get("ref")}
    out = []
    for r in rules:
        if r["kind"] not in ("near", "decap", "in_region"):
            continue
        try:
            res = pi.check(r, P, notes)
        except (KeyError, ValueError, TypeError):
            continue
        for s, ref, det in res:
            if ref in snap and s < -STRANDED_MM:
                h = snap[ref]
                what = ("decap %s at %s <= %g" % (r["cap"], r["pin"], r.get("max_mm", 1.5)) if r["kind"] == "decap"
                        else "near %s to %s <= %g" % (r["ref"], r["target"], r["max_mm"]) if r["kind"] == "near"
                        else "in_region %s" % r.get("region"))
                out.append("%s held by a snapshot at (%.2f, %.2f) [%s] breaks %s by %.1f mm (%s) [%s]"
                           % (ref, h["xy"][0], h["xy"][1], h.get("src", "?"), what, -s, det, r.get("src", "?")))
    return out


def _near_gate(nb, place_only):
    """⚠ A BROKEN HARD `near` STOPS THE FLOW (lead 2026-11-21): the placer seated C222 17.2 mm
    from U205 against a hard 8 and C230 2.54 from U205.11 against a hard 1.5, said WARN and went
    on to layout -- the arm was judged on a board that did not keep its own constraints. A hard
    rule is a refusal, like BROKEN keepouts: 2 = stop. --place-only (an A/B's evidence) still
    only reports; PCBFLOW_NEAR_BROKEN_OK=1 is for replaying an old board as it was."""
    if not nb or place_only or os.environ.get("PCBFLOW_NEAR_BROKEN_OK", "0") == "1":
        return None
    return 2


def _copper(notes, P, rules):
    """Declared copper from the intent: kind "copper" {net, tracks: [{layer, width, pts}], vias:
    [[x, y]], on: ["REF.PIN", ...], frozen, why} in the intent frame. Into notes tracks / vias (laid
    by layout before the fill, so a frozen band is filled round it and frozen_check's baseline
    holds it); `frozen` adds the net to notes frozen_nets. Every pin in `on` must hold a track end
    -- a part moved off its copper is a stop, not a dangling stub.

    ⚠ WHY (brain_board esc10, 2026-11-21): U205's ISP/ISN sense pins sit in the elbow between
    its VOUT bar and +5V_BB's frozen band; the router cannot leave them without crossing the
    band (ISN open on every seed since k1) and a coupled lay starts from the pads it cannot
    leave. The pair is laid here, coupled by construction, as an engineer would draw it."""
    done = notes.setdefault("copper_rules", [])
    lines = []
    for r in rules:
        if r["kind"] != "copper":
            continue
        key = r.get("key") or json.dumps(r, sort_keys=True)
        if key in done:
            continue
        for lnd in r.get("on", ()):
            ref, num = lnd.split(".", 1)
            poly = np.asarray(P.pad_poly(ref, num), float)
            from matplotlib.path import Path as _Pth
            pp = _Pth(poly)
            ends = [e for t in r.get("tracks", ()) for e in (t["pts"][0], t["pts"][-1])]
            if not any(pp.contains_point(e, radius=0.02) or pp.contains_point(e, radius=-0.02) for e in ends):
                raise SystemExit("place_flow: copper for %s names %s, but no track end lands on that pad "
                                 "(a part moved off its declared copper?)" % (r["net"], lnd))
        done.append(key)
        if r.get("neck"):
            # a BOUNDED declared neck (lead 2026-11-22): the power gate accepts this net's neck only while
            # the fabbed copper is no narrower than min_w and no longer than max_len (widepath.judge)
            nk = r["neck"]
            notes.setdefault("declared_necks", []).append(dict(
                key=key, net=r["net"], frm=nk["from"], to=nk["to"], min_w=float(nk["min_w"]),
                max_len=float(nk["max_len"]), why=nk.get("why") or r.get("why", "")))
        for t in r.get("tracks", ()):
            notes.setdefault("tracks", []).append([r["net"], t["layer"], float(t["width"]), t["pts"]])
        for v in r.get("vias", ()):
            # [x, y] or [x, y, drill, d] -> notes [net, x, y(, drill, d)], what layout lays.
            # ⚠ The size went missing here (brain_board 2026-11-25): every declared via was laid
            # at 0.3 / 0.6, so +24V_LED's 0.8 / 0.5 ECO vias could not be declared.
            notes.setdefault("vias", []).append([r["net"]] + [float(e) for e in v[:4]])
        if r.get("frozen"):
            fz = notes.setdefault("frozen_nets", [])
            if r["net"] not in fz:
                fz.append(r["net"])
        lines.append("%s: declared copper, %d track(s), %d via(s)%s" % (
            r["net"], len(r.get("tracks", ())), len(r.get("vias", ())), ", frozen" if r.get("frozen") else ""))
    return lines


def pour_priorities(zones):
    """Number the pours that declared no priority (priority None), in place; return
    [(layer, [(net, priority), ...] lowest first)] for the report.

    ⚠ A DECLARED PRIORITY IS A FIXED POINT (brain_board fold6, 2026-11-26). The old rule put
    each undeclared pour one above the highest taken on its layer, so BST_LMID's declared 11
    ("above +24V's 10") pushed the later BST_SW to 12 and +24V to 13: +24V filled over the boost
    input again (gate FAIL 0.79/2.63) with nothing in the intent saying so. Now, per layer:
    the undeclared pours keep their relative (rule) order and are numbered 1, 2, ... BELOW the
    lowest declared priority -- 1 and up so each still wins its region over a board-wide plane
    at 0, one number per net so two rails meeting at a fuse never share one (motor_ctrl
    +5V_RAW/+5V, 2026-11-11: DRC zones_intersect). If they do not fit under it, the declared
    pours rise as one block, keeping their order and gaps."""
    report = []
    for lyr in sorted({z["layer"] for z in zones}, key=str):
        on = [z for z in zones if z["layer"] == lyr]
        auto = []                                   # undeclared nets in rule order
        for z in on:
            if z["priority"] is None and z["net"] not in auto:
                auto.append(z["net"])
        decl = [z["priority"] for z in on if z["priority"] is not None]
        lift = max(0, len(auto) + 1 - min(decl)) if decl and auto else 0
        num = {n: i + 1 for i, n in enumerate(auto)}
        for z in on:
            z["priority"] = num[z["net"]] if z["priority"] is None else z["priority"] + lift
        seen, order = set(), []
        for z in sorted(on, key=lambda z: z["priority"]):
            if (z["net"], z["priority"]) not in seen:
                seen.add((z["net"], z["priority"]))
                order.append((z["net"], z["priority"]))
        report.append((lyr, order))
    return report


def _seg_x(p, q, a, b):
    """The parameter t on p->q where it properly crosses a->b, or None."""
    rx, ry, sx, sy = q[0] - p[0], q[1] - p[1], b[0] - a[0], b[1] - a[1]
    den = rx * sy - ry * sx
    if abs(den) < 1e-12:
        return None
    t = ((a[0] - p[0]) * sy - (a[1] - p[1]) * sx) / den
    u = ((a[0] - p[0]) * ry - (a[1] - p[1]) * rx) / den
    return t if (1e-9 < t < 1 - 1e-9 and -1e-9 <= u <= 1 + 1e-9) else None


def _inside(pt, poly):
    """Even-odd point in polygon."""
    x, y, c = pt[0], pt[1], False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def _ccw(poly):
    a = sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))
    return poly if a > 0 else poly[::-1]


def poly_union(pa, pb):
    """The outline of two overlapping simple polygons as one, or None when they do not overlap
    or the union is not one simple outline (it would enclose a hole). Board mm, [[x, y], ...].
    Two legs round one shared pin share that pin's circle corners exactly, which the edge walk
    cannot order: then the second is grown by 0.2 um about its centre and walked again."""
    u = _union_walk(pa, pb)
    if u is None:
        cx = sum(p[0] for p in pb) / len(pb)
        cy = sum(p[1] for p in pb) / len(pb)
        for k in (2e-4, 5e-4):
            g = [(cx + (p[0] - cx) * (1 + k / max(math.hypot(p[0] - cx, p[1] - cy), 1e-9)),
                  cy + (p[1] - cy) * (1 + k / max(math.hypot(p[0] - cx, p[1] - cy), 1e-9))) for p in pb]
            u = _union_walk(pa, g)
            if u is not None:
                break
    return u


def _union_walk(pa, pb):
    A, B = _ccw([tuple(map(float, p)) for p in pa]), _ccw([tuple(map(float, p)) for p in pb])

    def pieces(P, Q):
        out = []
        for i in range(len(P)):
            p, q = P[i - 1], P[i]
            ts = sorted({t for j in range(len(Q)) for t in [_seg_x(p, q, Q[j - 1], Q[j])] if t is not None})
            pts = [p] + [(p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])) for t in ts] + [q]
            out.extend(zip(pts, pts[1:]))
        return out
    pa_, pb_ = pieces(A, B), pieces(B, A)
    crosses = len(pa_) > len(A)
    if not crosses:
        if all(_inside(p, B) for p in A):
            return [list(p) for p in B]
        if all(_inside(p, A) for p in B):
            return [list(p) for p in A]
        return None                                   # apart
    keep = [e for e in pa_ if not _inside(((e[0][0] + e[1][0]) / 2, (e[0][1] + e[1][1]) / 2), B)]
    keep += [e for e in pb_ if not _inside(((e[0][0] + e[1][0]) / 2, (e[0][1] + e[1][1]) / 2), A)]
    key = lambda p: (round(p[0], 6), round(p[1], 6))
    nxt = {}
    for s, e in keep:
        if key(s) in nxt:
            return None                               # two edges leave one point: not simple
        nxt[key(s)] = (s, e)
    s0 = keep[0][0]
    loop, k = [s0], key(keep[0][1])
    while k != key(s0):
        if k not in nxt or len(loop) > len(keep):
            return None
        s, e = nxt[k]
        loop.append(s)
        k = key(e)
    if len(loop) != len(keep):
        return None                                   # a second loop: the union has a hole
    out = []
    for x, y in loop:
        q = [round(x, 3), round(y, 3)]
        if not out or q != out[-1]:
            out.append(q)
    while len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def merge_same_net_pours(zones):
    """One zone per net, layer and priority where pours overlap: (zones, report lines).

    ⚠ TWO LEGS OF ONE RAIL ARE ONE POUR (brain_board fold13, 2026-11-27). A long rail is
    written as legs -- a hull round distant pins covers everything between them -- and p20's
    V5_PRE north leg (U211.1-U36.5-R98.1) met its In3 leg (L1.2-U211.1-U215.3) at U211.1.
    pour_priorities numbers one priority per net, so both were In3.Cu priority 3, and KiCad
    DRC failed them (zones_intersect: two zones of one net, one priority, overlapping) --
    and close_last then left V5_PRE alone as a net "touched by a violation", so four of its
    branches stayed open. Overlapping pours of one net that agree on priority, whole and
    frozen are now one outline; ones that differ are refused by name here, not found by DRC."""
    out, res = [], []
    for z in zones:
        if not isinstance(z, dict) or not z.get("poly"):
            res.append(z)
            continue
        for i, y in enumerate(res):
            if not (isinstance(y, dict) and y.get("poly") and y["net"] == z["net"] and y["layer"] == z["layer"]):
                continue
            if not _touch(y["poly"], z["poly"]):
                continue                              # apart: two pours, no conflict
            u = poly_union(y["poly"], z["poly"])
            same = (y.get("priority"), bool(y.get("whole")), bool(y.get("frozen"))) == \
                   (z.get("priority"), bool(z.get("whole")), bool(z.get("frozen")))
            if not same or u is None:
                raise SystemExit(
                    "POUR OVERLAP: two %s pours on %s overlap and cannot be one zone (%s) -- "
                    "KiCad DRC would fail them as zones_intersect. Give them one priority and "
                    "the same whole / frozen, or move one leg off the other." % (
                        z["net"], z["layer"],
                        "priority %s vs %s, whole %s vs %s, frozen %s vs %s" % (
                            y.get("priority"), z.get("priority"), bool(y.get("whole")), bool(z.get("whole")),
                            bool(y.get("frozen")), bool(z.get("frozen"))) if not same
                        else "their union is not one simple outline"))
            res[i] = dict(y, poly=u)
            if y.get("legs") or z.get("legs"):
                res[i]["legs"] = list(y.get("legs") or []) + list(z.get("legs") or [])
            out.append("%s on %s: overlapping legs joined into one pour (%d corners)" % (z["net"], z["layer"], len(u)))
            break
        else:
            res.append(z)
    if out and len(res) > 1:                          # a joined pour may now meet another
        res, more = merge_same_net_pours(res)
        out += more
    return res, out


def _touch(pa, pb):
    """Any edge of one crosses the other's, or a corner of one lies inside the other."""
    return (any(_seg_x(pa[i - 1], pa[i], pb[j - 1], pb[j]) is not None for i in range(len(pa)) for j in range(len(pb)))
            or any(_inside(p, pb) for p in pa) or any(_inside(p, pa) for p in pb))


def _pours(notes, parts, pl, rules, base_zones):
    """notes["zones"] = the input's own zones + one per `pour` rule at the placed pins
    (place_intent.pour_poly); a pour that declares no priority is numbered by pour_priorities
    (1 and up, below every declared one on its layer). Returns the POUR lines for the report."""
    P = pi.Placed(parts, pl)
    cl = _copper(notes, P, rules)
    notes_r = dict(notes, _regions={r["name"]: r["poly"] for r in rules if r["kind"] == "region"})
    amps_of = lambda r: pi.pour_amps(r, notes)
    # a notes file that is itself a flow's output already carries last run's pours: a
    # dict zone on a pour rule's own net and layer is replaced, not stacked on (two +24V
    # pours on B.Cu, motor_ctrl v4: DRC zones_intersect)
    mine = {(r["net"], r["layer"]) for r in rules if r["kind"] == "pour"}
    base_zones = [z for z in base_zones if not (isinstance(z, dict) and (z.get("net"), z.get("layer")) in mine)]
    zones, out, pv = list(base_zones), [], []
    out.extend(cl)
    bands = []                          # (net, layer, poly) of the around bands drawn so far
    for r in rules:
        if r["kind"] != "pour":
            continue
        poly = pi.pour_poly(r, P, notes_r, amps_of(r))
        if poly is not None and r.get("around") and not r.get("region"):
            # opt-in (auto_pour `around`): the band goes round other nets' pads (pour_around)
            # ...and round the OTHER bands on its layer: their end pins (a B.Cu trunk's lands are
            # F.Cu pads, invisible to the pad walls -- VIN_SW's band from Q202.2 took the room
            # VIN_BRAIN's from Q202.3 needed) and the bands already drawn
            ra = dict(r, _avoid_pins=[x for o in rules if o["kind"] == "pour" and o.get("around")
                                      and o["layer"] == r["layer"] and o["net"] != r["net"]
                                      for x in o.get("along", ())],
                      _avoid_polys=[pg for n_, l_, pg in bands if l_ == r["layer"] and n_ != r["net"]])
            ar = pi.pour_around(ra, P, notes_r, amps_of(r))
            if ar is not None:
                bands.append((r["net"], r["layer"], ar))
                # fine-pitch end pins get a declared escape stub the band takes over from
                for e_ in pi.pin_escapes(r, P, notes):
                    if any(x_["key"] == e_["key"] for x_ in notes.get("band_escapes", ())):
                        continue                 # _pours runs twice: declare a stub once
                    notes.setdefault("tracks", []).append([e_["net"], e_["layer"], e_["width"], e_["pts"]])
                    notes.setdefault("band_escapes", []).append(e_)
                    out.append("%s: escape stub %.2f wide, %.2f past the pad (pitch %.2f)" % (
                        e_["key"], e_["width"], e_["beyond"], e_["pitch"]))
                lst = getattr(pi.pour_around, "last", None)
                if lst:
                    out.append("%s on %s: band %.1f mm long, neck %.2f of %.2f mm wanted%s" % (
                        r["net"], r["layer"], lst.get("length", 0), lst["neck"], lst["need"],
                        (" -- pinched by " + " ".join(lst["pinch"][:10])) if lst.get("pinch") else ""))
            if ar is None:
                out.append("%s on %s: no band round the other nets' pads reaches every pin -- "
                           "the hull kept" % (r["net"], r["layer"]))
            else:
                poly = ar
        if poly is not None and r.get("auto_amps") is not None:
            ow, ol = (notes.get("outline_mm") or (0, 0))[:2]
            area = abs(sum(poly[i][0] * poly[i - 1][1] - poly[i - 1][0] * poly[i][1]
                           for i in range(len(poly)))) / 2.0
            if ow and ol and area > r["max_frac"] * ow * ol:
                w = pi.width_for(r["auto_amps"], pi.design_dt(notes))
                nw = notes.setdefault("net_widths", {})
                nw[r["net"]] = max(nw.get(r["net"], 0.0), w)
                out.append("%s on %s: auto pour would cover %.0f %% of the board (max %.0f %%) -- "
                           "NOT poured, width %.2f mm instead" % (r["net"], r["layer"],
                                                                   100 * area / (ow * ol), 100 * r["max_frac"], w))
                continue
        if poly is None:
            out.append("%s on %s: NO OUTLINE (region %r unknown, no pins along) -- not poured"
                       % (r["net"], r["layer"], r.get("region")))
            continue
        # priority: declared, or None = numbered by pour_priorities() once every pour is in
        pr = int(r["priority"]) if "priority" in r else None
        zones.append({"net": r["net"], "layer": r["layer"], "poly": poly, "priority": pr,
                      # the pins this pour must join, for layout's pre-route pour gate (pour_gate.py)
                      **({"legs": [list(r["along"])]} if len(r.get("along") or ()) >= 2 else {}),
                      **({"whole": True} if r.get("whole") else {}),
                      **({"frozen": True} if r.get("frozen") else {})})
        # opt-in (`pad_vias`, set by auto_pour): the pour's big lands on another layer get a
        # via array sized to the current -- layout._pour_pad_vias
        if (r.get("pad_vias") or r.get("auto_amps") is not None) and r.get("along") and amps_of(r):
            pv.append({"net": r["net"], "layer": r["layer"], "pads": list(r["along"]),
                       "amps": amps_of(r), "width_mm": pi.width_for(amps_of(r), pi.design_dt(notes)),
                       **({"field": dict(r["field"], frozen=bool(r.get("frozen")))} if r.get("field") else {})})
        f = pi.pour_foreign(r, P, poly)
        out.append("%s on %s %s: %d corner(s), %s" % (
            r["net"], r["layer"], ("region " + r["region"]) if r.get("region") else "along " + "-".join(r["along"]),
            len(poly), ("%d other net pad(s) inside -- the layer may not have room: %s" % (len(f), " ".join(f[:8])))
            if f else "no other net's pad inside"))
    mine_z = zones[len(base_zones):]
    for lyr, order in pour_priorities(mine_z):
        out.append("pour order on %s (fills first last): %s" % (lyr, " < ".join("%s %d" % o for o in order)))
    mine_z, merged = merge_same_net_pours(mine_z)
    out.extend(merged)
    zones = zones[:len(base_zones)] + mine_z
    notes["zones"] = zones
    if pv:
        notes["pour_vias"] = pv
    else:
        notes.pop("pour_vias", None)      # never set on a board that does not opt in
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


def flow(d, intent_path, auto=True, soft=False, skip_finish=False, fold=False, keep_widths=False, singles=False,
         apply_swaps=False, place_only=False, to_routability=False, no_score=False):
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
    # ⚠ A FLOW'S OUTPUT NOTES ARE NOT ITS INPUT (brain br9 rerun, 2026-11-13): the run rewrites
    # <stem>.board.json with every part's placement, and a "control" rerun copied from that
    # file started from br9's finished layout as seeds -- 21 failed nets against br9's 1, read
    # at first as the router drifting. A notes file that already places most of the board is
    # said out loud; a clean rerun copies <dir>/flow/input.board.json instead.
    _npl = len(set(notes.get("placements", {}) or {}) & set(parts))
    if parts and _npl >= 0.5 * len(parts):
        print("place_flow: WARNING: the input notes already place %d of %d parts -- a previous flow's "
              "OUTPUT? Those are seeds, not a fresh start (a clean rerun copies flow/input.board.json)"
              % (_npl, len(parts)))
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
    # a kelvin tie sits on its shunt's land (place_intent.kelvin_seats): seated as a group member
    # when no rule places it, refused when a rule holds it off the land; then no two held parts
    # may overlap (place_intent.hold_overlaps) -- both before any placement is spent
    _vals = pi.read_values(stem + ".net") if os.path.exists(stem + ".net") else {}
    rules, klines_, kbad_ = pi.kelvin_seats(rules, parts, _vals)
    for k_ in klines_:
        print("place_flow: KELVIN " + k_)
        log.write("## kelvin: %s\n" % k_)
    if kbad_:
        raise SystemExit("place_flow: intent refused -- %d kelvin tie(s) not on their shunt land:\n  %s"
                         % (len(kbad_), "\n  ".join(kbad_)))
    hov_ = pi.hold_overlaps(rules, parts, _vals)
    if hov_:
        raise SystemExit("place_flow: intent refused -- %d pair(s) of held parts overlap (two holds the "
                         "placer seats as told):\n  %s" % (len(hov_), "\n  ".join(hov_[:20])))
    # an `access` / `mate` part's courtyard holds its reach (tool circle, plug stroke), ON DISK like the back side above, so
    # place_init, place_cells and every check keep neighbours out of the probe's reach
    parts, grown_ = pi.grow_reach(parts, rules)
    if grown_:
        pj = json.load(open(parts_path, encoding="utf-8"))
        pj["parts"] = parts
        json.dump(pj, open(parts_path, "w", encoding="utf-8"), indent=0)
        print("place_flow: access / mate: %d courtyard(s) grown to their reach: %s" % (len(grown_), " ".join(grown_)))
    # opt-in: big currents as pours, not tracks (place_intent.auto_pour)
    rules, aplines = pi.auto_pour(rules, parts, notes)
    for a_ in aplines:
        print("place_flow: AUTO_POUR " + a_)
        log.write("## auto_pour: %s\n" % a_)
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
    # ⚠ EVERY HOLD SAYS WHY (user 2026-11-22, pi.check_holds): a `fixed` rule with no hold class
    # or no why stops here, before any placement is spent on it; the HOLDS line reports by class.
    hc_, hbad_ = pi.check_holds(rules)
    say("HOLDS: %d fixed -- %s" % (sum(v for k, v in hc_.items() if k != "transient"),
                                  ", ".join(["%s %d" % (k, hc_[k]) for k in pi.HOLD_CLASSES + ("transient",) if hc_.get(k)]
                                            + (["UNCLASSIFIED %d" % len(hbad_)] if hbad_ else []))))
    if hbad_:
        raise SystemExit("place_flow: intent refused -- %d hold(s) without a reason (hold: %s, and a why):\n  %s"
                         % (len(hbad_), " / ".join(pi.HOLD_CLASSES), "\n  ".join(hbad_[:20])))
    # a hard near / decap its regions cannot meet stops here, before placement (pi.feasibility)
    try:
        fbad_, fsplit_ = pi.feasibility(rules, parts, notes)
    except (KeyError, ValueError) as e_:
        fbad_, fsplit_ = [], ["FEASIBILITY check could not run: %r" % (e_,)]
    # (REGION SPLIT stops too: a hot-loop cap whose only seat is the border of two regions is an
    # intent error -- sw2's C3 / C299 / C306 -- and ended as NO ROOM after 20 minutes)
    if fbad_ or fsplit_:
        for l_ in fbad_ + fsplit_:
            say(l_)
        raise SystemExit("place_flow: intent refused -- %d hard rule(s) INFEASIBLE, %d REGION SPLIT:\n  %s"
                         % (len(fbad_), len(fsplit_), "\n  ".join((fbad_ + fsplit_)[:20])))
    # ⚠ A RULE THAT NAMES A PART THE NETLIST NO LONGER HAS STOPS THE FLOW HERE, NOT LATER
    # (brain_board mV20a/b, 2026-11-17): a saved pour rule still ran `along` R223.2 after the
    # U5 rework removed R223; both runs placed for 20 minutes and died in _pours on a KeyError.
    # A rule anchored on a missing part or pin (ref, cap, anchor, target, pin, also, along)
    # is broken -- said now, every one at once; a missing name in a membership list (refs,
    # a, b, members, except) only drops out of that list, so it is a warning.
    stale, thin = [], []
    for i_, r_ in enumerate(rules):
        for k_ in ("ref", "cap", "anchor", "target", "pin", "also", "along", "refs", "a", "b", "members", "except"):
            v_ = r_.get(k_)
            for x_ in (v_ if isinstance(v_, list) else [v_]):
                if not isinstance(x_, str) or not re.fullmatch(r"[A-Z]+\d+(\.\w+)?", x_):
                    continue
                if x_.split(".")[0] in parts:
                    continue
                (thin if k_ in ("refs", "a", "b", "members", "except") else stale).append(
                    "rule %d (%s %s, src %s): %s %s" % (i_, r_["kind"], r_.get("net") or r_.get("name") or "",
                                                       r_.get("src", "?"), k_, x_))
    for x_ in thin:
        say("WARN rule names a part the netlist does not have (dropped from its list): " + x_)
    if stale:
        say("STALE RULES -- the flow stops before placement: these rules are anchored on parts the "
            "netlist does not have (renamed or removed?): " + " | ".join(stale))
        return 2
    # ⚠ A BOARD THAT NAMES SUPPLY PINS NAMES THEM ALL (brain_board mV20, 2026-11-17): the
    # service port's ICs were added after supply_pins was written, so U43 (an ideal diode whose
    # VIN_BUS pin is a cathode SENSE input) fell back to "every rail pin is a supply" and took
    # C96 and both VIN_BUS bulks, 55 mm from where they are held. Said, by name, every run.
    sp_ = notes.get("supply_pins") or {}
    if sp_:
        und_ = sorted(u for u in parts if re.match(r"^U\d", u) and u not in sp_
                      and any(q["net"] and pi.SUPPLY.search(q["net"]) for q in parts[u]["pads"]))
        if und_:
            say("WARN supply_pins: %d IC(s) on a supply rail are not declared, so EVERY one of their "
                "rail pins counts as a supply (decaps, quality A2): %s" % (len(und_), " ".join(und_)))
    floor = pi.unregioned_sensitive(parts, rules)
    for f_ in floor:
        say("WARN " + f_)
    # held parts inside the region they belong to with no rule binding them there: they leak the
    # day the hold goes (place_intent.region_leaks; brain_board mV31). PCBFLOW_REGION_LEAK_STOP=1
    # stops the flow on any.
    leaks_ = pi.region_leaks(parts, rules)
    for g_, refs_ in leaks_:
        say("REGION LEAK %s: %d held part(s) belong there by the netlist but no in_region binds "
            "them -- bind them, or list them in the region's `free`: %s" % (g_, len(refs_), " ".join(refs_)))
    if leaks_ and os.environ.get("PCBFLOW_REGION_LEAK_STOP") == "1":
        say("REGION LEAK -- the flow stops before placement (PCBFLOW_REGION_LEAK_STOP=1)")
        return 2
    say("intent: %d rules%s" % (len(rules), (" (+ " + ", ".join(added) + ")") if added else ""))
    # ⚠ A GUESSED PART IS SAID BY NAME (lead 2026-11-26, brain_board C65 / C119): every cap
    # auto_decaps assigned by fallback -- no part named in its description -- with the part it
    # picked, so a wrong guess shows on the first run, not 27 mm off on a laid-out board
    _desc = pi.read_descriptions(stem + ".net") or {}
    for r_ in rules:
        if str(r_.get("assigned", "")).startswith("fallback"):
            c_ = r_.get("cap") or r_.get("ref")
            say("auto_decaps FALLBACK %s -> %s (%s; description %r)"
                % (c_, r_.get("pin") or r_.get("target"), r_["assigned"], _desc.get(c_, "")))
    if widened:
        say("net widths from `current`: " + ", ".join(widened))

    # 2. place_init, place_cells
    init = os.path.join(fd, "init.json")
    rc, out, T["place_init"] = _run_cached("place_init", [sys.executable, "place_init.py", stem, ip, "--out", init], log, d,
                                         [stem + ".net", stem + ".board.json", parts_path, ip],
                                         [init, init[:-5] + ".why.json", init[:-5] + ".handoff.json"], ok=(0, 3),
                                         seed_free=True)
    if rc not in (0, 3):
        raise SystemExit("place_flow: place_init failed (see flow/flow.log)\n" + out[-800:])
    init_log = [line for line in out.splitlines() if line.startswith("place_init:")]
    # a GROW is the floorplan the board was placed in: every later gate judges that one
    grown, released = _handoff(init)
    if grown:
        for r in rules:
            if r["kind"] == "region" and r["name"] in grown:
                r["poly"] = grown[r["name"]]
        json.dump(rules, open(ip, "w"), indent=1)
        say("regions grown by place_init (GROW): " + ", ".join(sorted(grown)))
    # ⚠ A RELEASED SNAPSHOT IS RELEASED FOR EVERY LATER STAGE (brain_board vip_s1, 2026-11-23):
    # place_init released U13's snapshot (it broke a hard near once J1 turned) and seated it
    # under the rule, but flow/intent.json still held the snapshot, and the BROKEN gate graded
    # U13 9.05 mm off it -- the flow stopped anyway. Like a GROW, place_init's release is
    # written back (its hand-off file): the released snapshot holds leave the intent every later
    # gate and stage reads.
    rules, rel_ = _drop_released(rules, released)
    if rel_:
        json.dump(rules, open(ip, "w"), indent=1)
        say("snapshot holds released by place_init (a hard rule outranks a remembered seat): " + " ".join(rel_))
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
    _SAT[:] = _sat_broken(rules, parts, pl)
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
        if r_["kind"] in pi.GATE_KINDS and pi.is_hard(r_):
            for s_, ref_, det in pi.check(r_, P_k, notes_k):
                if s_ < -0.05:
                    broken.append("rule %d %s: %s %s (%.2f mm)" % (i_, r_["kind"], ref_, det, s_))
    if broken:
        say("BROKEN hard rules -- the flow stops before layout: " + " | ".join(broken[:8]))
        _report(fd, base, rules, init_log, [], [], None, None, None, why, T,
                refused="intent check: BROKEN hard mechanical rules\n" + "\n".join(broken[:20]), floor=floor, room=room)
        return 2
    # declared copper is an obstacle to other nets' pads (place_intent.pad_copper; lead 2026-11-22):
    # a pad inside a declared track's clearance is a short layout refuses later -- say it here, with
    # whether the part was held there (the intent must move) or placed there (the placer missed it).
    # (the A/B against hand keep-outs, 2026-11-22: sqp 16.52 / 15.41 with the rule, 16.69 / 15.58 with the keep-out)
    held_ = {x for r_ in rules if r_["kind"] in ("fixed", "pin", "panel") for x in (pi._refs(r_["refs"], parts) if "refs" in r_ else [r_.get("ref")])}
    it_ = pi.declared_items(rules, notes)
    pc_ = sorted(set(x for x in pi.pad_copper(P_k, it_) if x[0] < -0.005))
    for v_, s_, d_ in sorted(set(pi.pad_copper(P_k, it_, exp=pi.PAD_MASK_EXP, near=0.0))):
        if v_ < -0.005 and not any(s_ == x[1] for x in pc_):
            w_ = "PAD BY DECLARED COPPER %s: %s -- inside the %.2f mask band" % (s_, d_, pi.PAD_MASK_EXP)
            say("WARN " + w_)
            floor.append(w_)
    if pc_:
        lines_ = ["%s%s: %s (%.3f mm short)" % (s_, " (held)" if s_.split(".")[0] in held_ else "", d_, -v_)
                  for v_, s_, d_ in sorted(pc_)]
        say("PAD ON DECLARED COPPER -- the flow stops before layout: " + " | ".join(lines_[:8]))
        _report(fd, base, rules, init_log, [], [], None, None, None, why, T,
                refused="intent check: PAD ON DECLARED COPPER\n" + "\n".join(lines_[:20]), floor=floor, room=room)
        return 2
    for w_ in _chain_warns(rules, parts, pl):
        say("WARN " + w_)
        floor.append(w_)
    for w_ in _twist_warns(notes, parts, pl):
        say("WARN " + w_)
        floor.append(w_)
    for w_ in _swap_lines(notes, parts, pl, stem, fd, apply_swaps):
        say("WARN " + w_)
        floor.append(w_)
    for w_ in _tight_warns(rules, parts, P_k, notes_k):
        say("WARN " + w_)
        floor.append(w_)
    # ⚠ A BROKEN HARD `near` IS SAID, NOT LEFT TO A SIDE EFFECT (output_board mN, 2026-11-14):
    # "U17 within 30 of FL3" ended 39.6 mm and the report showed only a CHAIN warning about
    # it; the board went on to a 30-minute route with its USB pairs as long as before.
    nb = _near_broken(rules, P_k, notes_k)
    # ⚠ A HELD PART CANNOT KEEP A HARD RULE IT WAS NEVER ASKED TO (output_board mP / mQ, 2026-11-15):
    # every part was pinned `fixed` where fin_mO left it, so C124 sat 4.6 mm from U1.62 against
    # a HARD 3 mm rule and no placer could move it -- one WARN among fourteen, and quality A2
    # FAILed it three runs running. A broken hard rule whose part is held is said on its own
    # line, by name: the hold outranks the rule, so the author must release one or the other.
    held_ = {r_["ref"] for r_ in rules if r_["kind"] in ("fixed", "pin") and r_.get("hard", True)}
    hb = sorted({w_.split(": ", 1)[1].split(" ", 1)[0] for _s, w_ in nb} & held_)
    if hb:
        w_ = ("HELD PARTS BREAK HARD RULES -- %d part(s) pinned by a fixed/pin rule miss a hard near "
              "rule, and no placer may move them: %s. Release them or relax the rule."
              % (len(hb), " ".join(hb)))
        say("⚠ " + w_)
        floor.insert(0, w_)
    for _s, w_ in sorted(nb)[:12]:
        say("WARN " + w_)
        floor.append(w_)
    if len(nb) > 12:
        floor.append("NEAR BROKEN (hard): %d more" % (len(nb) - 12))
    sb = _snapshot_broken(rules, P_k, dict(notes_k, _regions={r_["name"]: r_["poly"] for r_ in rules
                                                              if r_["kind"] == "region"}))
    for w_ in sb:
        say("SNAPSHOT BROKEN " + w_)
        floor.append("SNAPSHOT BROKEN " + w_)
    if sb and not place_only:
        say("SNAPSHOT HOLDS BREAK RULES -- the flow stops before layout: remove these holds")
        _report(fd, base, rules, init_log, [], [], None, None, None, why, T,
                refused="intent check: SNAPSHOT BROKEN\n" + "\n".join(sb[:20]), floor=floor, room=room)
        return 2
    if _near_gate(nb, place_only):
        say("NEAR BROKEN hard rules -- the flow stops before layout: " + " | ".join(x[1] for x in sorted(nb)[:8]))
        _report(fd, base, rules, init_log, [], [], None, None, None, why, T,
                refused="intent check: NEAR BROKEN hard rules\n" + "\n".join(x[1] for x in sorted(nb)[:20]),
                floor=floor, room=room)
        return 2
    if place_only:
        # --place-only: a placement A/B across boards (a placer change's evidence) needs
        # NO ROOM, BROKEN and NEAR BROKEN, not a route -- minutes per board instead of an hour
        for l_ in _sat_summary(init_log):
            say(l_)
        say("PLACE ONLY: %d placed, %d with no room, %d hard near rule(s) broken%s"
            % (len(pl), len(room), len(nb), (": " + " | ".join(x[1] for x in nb[:6])) if nb else ""))
        return 0
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
    rc, out, T["place_cells"] = _run_cached("place_cells", cmd, log, d, [stem + ".net", stem + ".board.json", parts_path, ip],
                                          [stem + ".cells.json", os.path.join(d, "cells")])
    if rc != 0:
        raise SystemExit("place_flow: place_cells failed (see flow/flow.log)\n" + out[-800:])
    cells_log = [line for line in out.splitlines() if line.startswith("place_cells:")]
    pc = json.load(open(stem + ".cells.json"))
    for r_ in pc:
        if pl.get(r_) != pc[r_]:
            why[r_] = "place_cells: cell turned / repaired by route (%s)" % why.get(r_, "")
    pl = pc
    _SAT[:] = _sat_broken(rules, parts, pl)
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
    # netlist-owned parts placed OUTSIDE their region (place_intent.region_strays): reported,
    # never a stop -- bind the part, or record why in the region's `away`
    for g_, ref_, at_, ok_ in pi.region_strays(parts, rules, pl):
        say("REGION STRAY %s: %s belongs there by the netlist but sits %s%s"
            % (g_, ref_, ("in " + at_) if at_ else "outside every region",
               (" -- OK: " + ok_) if ok_ else " -- bind it (in_region) or say why in the region's `away`"))

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
    # the global plan's routability (ROUTER.md "Global plan", SCORE_UTIL): seconds, recorded so a
    # set of trials of ONE netlist and outline can be ranked before routes are spent on them
    rout = None
    if os.environ.get("PCBFLOW_ROUTABILITY") == "1" or to_routability:
        rc, out, T["routability"] = _run([sys.executable, "-m", "router.globalroute", stem], log)
        for line in reversed(out.splitlines()):
            try:
                rout = json.loads(line)
                break
            except ValueError:
                continue
        if rout:
            say("ROUTABILITY overflow %.2f over %d square(s), %.0f mm, %d via(s); hot %s"
                % (rout["overflow"], rout["squares_over"], rout["length_mm"], rout["vias"],
                   "; ".join("%.1f at (%.0f, %.0f) %s" % (o, x, y, "/".join(nr)) for o, x, y, nr in rout["hot"])))
    if to_routability:
        # --to-routability: a placement change judged by the global plan (seconds) before an
        # hour of route is spent on it -- the spreading pass's A/B (brain_board, 2026-11-17)
        for l_ in _sat_summary(init_log):
            say(l_)
        say("TO ROUTABILITY: stopped before the route")
        return 0
    # ⚠ THE SCORE'S ROUTE IS THE BOARD'S ROUTE (brain_board mV41 vs mV44, 2026-11-18): the finish
    # starts from it (OWNROUTE_PARENT) and gets 300 s for the rest, so a flow's board is a
    # 900 s route -- a replay, routing again from nothing at ownroute's 1800 s, finished the
    # same placement at 3 unconnected where the flows ended at 27-28. PCBFLOW_SCORE_BUDGET_S
    # sets the score's budget (router.score --budget; default 900 as before).
    # --no-score (a FINAL, lead 2026-11-18): with PCBFLOW_FINISH_FRESH the finish routes from
    # nothing anyway, so the score's ~40 min judges nothing; placement A/Bs keep it.
    _sb = os.environ.get("PCBFLOW_SCORE_BUDGET_S")
    if no_score:
        out = ""
        say("NO SCORE: the finish routes the board from nothing")
    else:
        rc, out, T["score"] = _run([sys.executable, "-m", "router.score", stem, "--save", "auto", "--intent", ip,
                                    "--parts", parts_path] + (["--budget", _sb] if _sb else []), log)
    score = None
    for line in reversed(out.splitlines()):
        try:
            score = json.loads(line)
            break
        except ValueError:
            continue
    fin = qual = None
    if not skip_finish:
        # the finish starts from the route the score just drew (ownroute.py, OWNROUTE_PARENT)
        par = stem + ".route.pkl"
        # ...or, with PCBFLOW_FINISH_FRESH=1, routes the board again from nothing at ownroute's own
        # budget, as the replay that finished brain_board mV41 at 3 unconnected did: the score
        # stays a cheap 900 s judge for placement A/Bs, the board gets the real route.
        fresh = os.environ.get("PCBFLOW_FINISH_FRESH", "1") == "1" or no_score
        rc, out, T["finish"] = _run([KICAD_PY, os.path.join(HERE, "finish.py"), stem], log,
                                    env={"OWNROUTE_PARENT": par} if os.path.isfile(par) and not fresh else None)
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
        # ⚠ A QUALITY PASS THAT DID NOT RUN IS A FAIL (rPS_10a5, 2026-11-21): quality.py refused
        # (A26-A31 in the code, not in PCB_QUALITY.md), the report's "quality:" line carried the
        # refusal text in the middle of the summary, and five seeds were scored with no A-rule
        # numbers before anyone noticed. No quality.json written by THIS run (a refusal writes
        # none; a stale one from an earlier pass is older) is now `skipped` and leads the report.
        # Not the rc: quality.py exits 1 whenever any rule FAILs, which is a pass that ran.
        qj = stem + ".quality.json"
        t_q = time.time()
        rc, out, T["quality"] = _run([KICAD_PY, os.path.join(HERE, "quality.py"), "--brief", stem], log)
        try:
            if os.path.getmtime(qj) < t_q - 1:
                raise ValueError("quality.py rc %d, no quality.json from this run" % rc)
            q = json.load(open(qj, encoding="utf-8"))
            qual = {"fail": q.get("fail"), "open": q.get("open"), "waived": q.get("waived"),
                    "failed": [r.get("id") or r.get("rule") for r in q.get("results", [])
                               if str(r.get("status", "")).upper() == "FAIL"][:20]}
        except (OSError, ValueError) as exc:
            qual = {"skipped": True, "error": "%s: %s" % (exc, out.strip()[-600:])}
    _report(fd, base, rules, init_log, cells_log, gates, score, fin, qual, why, T, room=room, width=wlines, pours=plines,
            floor=floor, fill=pi.region_fill(rules, parts, pl), routability=rout)
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


def _twist_warns(notes, parts, pl):
    """TWIST lines: a declared pair whose rails swap sides between two lands
    (place_intent.pair_twists). Placement feedback: a coupled pair cannot run that hop on one
    layer, so it pays a layer change or uncoupled mm round a land."""
    groups = list(notes.get("match") or []) + list(notes.get("diff_pairs") or [])
    try:
        tw = pi.pair_twists(parts, pl, groups)
    except Exception as e:                   # feedback only: never stops the flow
        return ["TWIST check failed: %s" % e]
    # a part that passes a pair through, whose rails can be swapped between its channels: small (<= 10
    # pads) and either two pins per rail (a flow-through clamp, optical U10) or both rails of a
    # second declared pair (a CMC, FL3: USBA on one side, USBA_J on the other). Not a connector
    # or IC that merely carries several pairs (J202).
    pairs = [set(g.get("nets") or ()) for g in groups if len(g.get("nets") or ()) == 2]
    def thru(ref):
        pads_ = parts.get(ref, {}).get("pads", ())
        if len(pads_) > 10:
            return False
        nets_ = collections.Counter(q.get("net") for q in pads_ if q.get("net"))
        held = [pr for pr in pairs if pr <= set(nets_)]
        return any(all(nets_[n_] >= 2 for n_ in pr) for pr in held) or len({frozenset(pr) for pr in held}) >= 2
    out = []
    for name, a, b, st in tw:
        if st != "twisted":
            continue
        t = sorted(r for r in (a, b) if thru(r))
        out.append("TWIST %s %s -> %s: the rails swap sides between these lands, so the pair cannot run coupled "
                   "on one layer here (it pays a layer change or uncoupled mm round a land). Fix: %sa polarity / "
                   "pin swap at %s or %s if the part allows it, or one end mirrored to the other side. Turning a "
                   "part never fixes it (a rotation keeps the rails' order)."
                   % (name, a, b, ("swap the two rails between %s's channels (it passes the pair through; "
                                   "free if its channels are identical, as a CMC's windings or a clamp's are), "
                                   % "/".join(t)) if t else "", a, b))
    return out


def _swap_lines(notes, parts, pl, stem, fd, apply=False):
    """SWAP lines: the channel swaps on pass-through parts that untwist the most pair hops
    (place_intent.swap_plan), written to flow/pin_swaps.json. With apply (--apply-swaps, opt-in)
    they go into this run's <stem>.net and parts.json (the input netlist kept as
    flow/input.net) -- the netlist's GENERATOR must then carry them, or the next export loses
    them."""
    groups = list(notes.get("match") or []) + list(notes.get("diff_pairs") or [])
    # notes["swap_rejected"]: [{refs: [...], why: "the route A/B that rejected it"}] -- those parts
    # are left out of the plan, and said once, so a lost A/B is not re-proposed every run
    rej = [e for e in (notes.get("swap_rejected") or ()) if isinstance(e, dict) and e.get("refs")]
    rejected = {r for e in rej for r in e["refs"]}
    try:
        n0, n1, sw = pi.swap_plan(parts, pl, groups, flip=set(notes.get("pair_flip") or ()), rejected=rejected)
    except Exception as e:                   # feedback only: never stops the flow
        return ["SWAP check failed: %s" % e]
    json.dump(dict(twisted_before=n0, twisted_after=n1, applied=bool(apply and sw),
                   swaps=[dict(ref=r, pins=[list(x) for x in prs]) for r, prs in sw]),
              open(os.path.join(fd, "pin_swaps.json"), "w"), indent=1)
    said = ["SWAP not proposed for %s: rejected by route A/B (%s)" % (" ".join(e["refs"]), e.get("why") or "no reason given")
            for e in rej if set(e["refs"]) & set(parts)]
    if not sw:
        return said
    nets = {r: {q["num"]: q["net"] for q in parts[r]["pads"]} for r, _ in sw}
    out = ["SWAP %s: pins %s -- its channels are identical, so swapping the rails between them is free "
           "in the netlist; twisted pair hops %d -> %d%s"
           % (r, ", ".join("%s<->%s (%s/%s)" % (a, b, nets[r][a], nets[r][b]) for a, b in prs), n0, n1,
              "" if apply else " (proposed, NOT applied: --apply-swaps tries it on this run; once a route A/B "
                             "accepts it, `swaps.py accept` records it and the generator's apply_accepted "
                             "carries it; a rejected one goes in the board notes' swap_rejected)") for r, prs in sw] + said
    if apply:
        net_path = stem + ".net"
        keep = os.path.join(fd, "input.net")
        if not os.path.exists(keep):
            shutil.copy(net_path, keep)
        text = pi.apply_swaps(parts, open(net_path, encoding="utf-8").read(), sw)
        open(net_path, "w", encoding="utf-8").write(text)
        pj = json.load(open(stem + ".parts.json", encoding="utf-8"))
        pj["parts"] = parts
        json.dump(pj, open(stem + ".parts.json", "w", encoding="utf-8"), indent=0)
        out.append("SWAP APPLIED to this run's %s.net and parts.json (input kept as flow/input.net): CARRY IT "
                   "INTO THE NETLIST'S GENERATOR, or the next export undoes it" % os.path.basename(stem))
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


def _lifted(line):
    """A placement-log line the report lifts to its summary (tangles, grows, decap room)."""
    return any(k in line for k in ("TANGLE HINT", "GROW", "DECAP ROOM"))


# ⚠ STRANDING IS EVERY near / decap RULE, JUDGED BY ITS OWN CHECK, HELD PARTS INCLUDED (lead
# 2026-11-22). place_init's DECAP STRANDED line counted only FREE satellites, centre to pin:
# a snapshot-held cap 26 mm off its pin (C119) never showed, and two intents that freed
# different parts read 7 against 11 stranded with the same 8 rules broken on each. The count
# here is the only one: each rule pi.check misses by more than STRANDED_MM, hard counted
# apart, held / free said. (place_init's lines stay in flow.log as diagnostics -- who holds
# the pin's patch -- and are no longer counted or lifted.)
STRANDED_MM = 1.0
_SAT = []          # the current placement's broken satellite rules (flow sets it, _report reads it)


def _sat_broken(rules, parts, pl):
    """[(mm past, ref, target, max_mm, hard, held, src)] for every near / decap rule broken by
    more than STRANDED_MM at placement pl (rules naming an unplaced part are skipped)."""
    held = {r["ref"] for r in rules if r["kind"] in ("fixed", "pin", "panel") and r.get("ref")}
    P = pi.Placed(parts, pl)
    out = []
    for r in rules:
        if r["kind"] not in ("near", "decap"):
            continue
        try:
            res = pi.check(r, P, {})
        except (KeyError, ValueError, TypeError):
            continue
        for s, ref, _det in res:
            if s < -STRANDED_MM:
                out.append((round(-s, 2), ref, r.get("pin") or r.get("target"), r.get("max_mm"),
                            pi.is_hard(r), ref in held, r.get("src", "")))
    return sorted(out, key=lambda t: -t[0])


def _sat_summary(init_log, sat=None):
    """The stranding list (_sat_broken, each rule once) and its count line, then the log's
    tangle / grow lines once each."""
    sat = _SAT if sat is None else sat
    out = ["SATELLITE BROKEN (%s, %s): %s %.1f mm past its rule (%s <= %g) [%s]"
           % ("HARD" if h else "soft", "held" if hd else "free", ref, mm, t, m, src)
           for mm, ref, t, m, h, hd, src in sat]
    out.append("PLACEMENT: %d near/decap rule(s) broken by > %g mm (%d hard; %d held, %d free)"
               % (len(sat), STRANDED_MM, sum(1 for x in sat if x[4]), sum(1 for x in sat if x[5]),
                  sum(1 for x in sat if not x[5])))
    return out + list(dict.fromkeys(x_.split("place_init: ", 1)[-1] for x_ in init_log if _lifted(x_)))


def _report(fd, base, rules, init_log, cells_log, gates, score, fin, qual, why, T, refused=None, room=(), width=(), pours=(),
            floor=(), fill=(), routability=None):
    forbid = [l_ for l_ in init_log + cells_log if "FORBID" in l_]
    prov = collections.Counter(_klass(w) for w in why.values())
    S = {k: (score or {}).get(k) for k in ("open", "pairs", "islands", "uncoupled", "vias", "length_mm", "floor",
                                            "failed", "faulted", "floor_breaches", "error")}
    rep = {"board": base, "rules": len(rules), "score": S, "forbid": forbid, "gates": gates, "finish": fin,
           "quality": qual, "provenance": dict(prov), "seconds": {k: round(v) for k, v in T.items()},
           "refused": refused, "no_room": list(room), "width": list(width), "pours": list(pours),
           "region_fill": [dict(region=n, area_mm2=round(a), courtyard_mm2=round(u), fill=round(f, 3))
                           for n, a, u, f in fill],
           "routability": routability}
    json.dump(rep, open(os.path.join(fd, "report.json"), "w"), indent=1)
    L = ["# place_flow: %s" % base, ""]
    if qual and qual.get("skipped"):
        L += ["**FAIL: THE QUALITY PASS DID NOT RUN -- no A-rule result on this board.**", ""]
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
    L += _sat_summary(init_log)
    if fin:
        L += ["", "finish: %s" % (fin.get("error") or "%d unconnected%s, %d violation(s)%s" % (
            fin["unconnected"], (" (" + " ".join(fin.get("unconnected_nets", ())) + ")") if fin["unconnected"] else "",
            fin["violations"], (" (" + ", ".join("%s %d" % kv for kv in sorted(fin.get("by_type", {}).items())) + ")")
            if fin["violations"] else "") + (", %d declared" % fin["declared"] if fin.get("declared") else "")
            + (", %d warning(s) (%s)" % (fin["warnings"], ", ".join("%s %d" % kv for kv in sorted(fin.get("warn_by_type", {}).items())))
               if fin.get("warnings") else ""))]
    if qual:
        L += ["quality: %s" % (("FAIL, DID NOT RUN -- " + qual["error"]) if qual.get("skipped") else qual.get("error") or "%s FAIL, %s OPEN%s" % (
            qual["fail"], qual["open"], (" (" + " ".join(map(str, qual["failed"])) + ")") if qual.get("failed") else ""))]
    if gates:
        L += ["", "layout notes:"] + ["  " + g for g in gates]
    L += ["", "placement log (less the lines listed above):"] + [
        "  " + l_ for l_ in init_log + cells_log if "fixed " not in l_ and not _lifted(l_)]
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
    ap.add_argument("--place-only", action="store_true",
                    help="stop after placement and its rule checks (no cells, layout or route)")
    ap.add_argument("--to-routability", action="store_true",
                    help="stop after layout and the global plan's routability (no route)")
    ap.add_argument("--no-score", action="store_true",
                    help="a final: skip the score route; the finish routes the board from nothing")
    ap.add_argument("--apply-swaps", action="store_true",
                    help="apply the proposed pair channel swaps (SWAP lines) to this run's netlist and parts "
                         "-- the generator must then carry them")
    a = ap.parse_args(argv)
    return flow(a.dir, os.path.abspath(a.intent), not a.no_auto, a.soft_forbid, a.skip_finish, a.fold_post,
                a.keep_widths, a.auto_singles, a.apply_swaps, a.place_only, a.to_routability, a.no_score)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
