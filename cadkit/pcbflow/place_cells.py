"""place_cells.py: turn each free-anchor cell to the rotation the ROUTER likes (PLACEMENT.md).

    py -3.12 place_cells.py <dir> <intent.json> [--parts <parts.json>] [--jobs 4]

<dir> holds one board (<stem>.net, <stem>.board.json with the placements to start from --
place_init's output); <stem>.parts.json is the parts geometry unless --parts says where.

For every `group` rule whose anchor is NOT fixed (a cell place_init placed whole), in
intent order:

  1. the parent -- the board as it stands -- is laid out and routed in full (score.py
     --save auto --intent), unless <dir>/cells/parent already holds that route;
  2. the cell's three other quarter turns: the whole cell turned about its anchor and
     dropped as one composite at the free spot nearest the anchor (place_init's
     legaliser, halos, the anchor's region); a turn with no room is skipped;
  3. each candidate is laid out (layout.py) and re-scored as a change of the parent
     (router/rescore.py, --parent), `jobs` at a time, floor breaches reported (--intent);
  4. the best by place_refine's key, if it beats the parent's, is routed IN FULL and kept
     only if the full route beats the parent too -- the confirm rule place_refine earned
     (a re-score is one sample of "what this change does"). It is the next cell's parent.

A FORBID ZONE IS HARD (lead ruling, 2026-11-11). A turn that breaks more `forbid` zones
than its parent gets ONE repair: the unit breaking it -- a free-anchor cell or a free part,
never the cell being turned -- is re-dropped at its turn, at the free spot nearest where it
is, clear of every zone it breaks; laid out and re-scored like any candidate. A turn the
repair cannot clear is not eligible, said loudly (FORBID: ...). --soft-forbid keeps the
best route and only reports the breach, for an author who wants that trade. (Optical's
PHY: the only turn that routed 0 open put the buck's switch node 9.2 mm from the PHY
crystal, zone 10.)

Bounded: at most 3 candidates + 3 repairs + 1 confirm per cell. Writes <dir>/cells/<anchor>_<rot>/,
<dir>/cells/cells.json (every candidate's score) and <dir>/<stem>.cells.json (the
placements kept).

⚠ WHY (optical, 2026-11-11): the PHY cell, placed whole, landed at 270 from place_init's
turn stage -- the turn that let layout lay the USB pair coupled (0.0 mm) but walled in the
ULPI fan (ULPI_D5/D6 open). A cell's turn decides how its whole pin field meets the board;
no pad-pull heuristic weighs a pre-laid pair against a 12-line bus. The route does, and
four turns of one cell is a measurement, not a sweep.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_init as pin  # noqa: E402
import place_intent as pi  # noqa: E402
from place_refine import _better, _key, _layout, _stem  # noqa: E402
import subprocess  # noqa: E402


def _score(stem, intent, parts_path, parent=None, save=False, budget=900):
    cmd = [sys.executable, "-m", "router.score", stem, "--jobs", "1", "--budget", str(budget),
           "--intent", intent, "--parts", parts_path]
    if parent:
        cmd += ["--parent", parent]
    if save:
        cmd += ["--save", "auto"]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    for line in reversed(p.stdout.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return {"error": (p.stderr or p.stdout)[-600:]}


def _write(d, src, stem, pl):
    """A board directory d holding src's netlist and notes with placements pl."""
    os.makedirs(d, exist_ok=True)
    base = os.path.basename(stem)
    shutil.copy(stem + ".net", os.path.join(d, base + ".net"))
    notes = dict(src, placements=pl)
    json.dump(notes, open(os.path.join(d, base + ".board.json"), "w"), indent=0)
    return os.path.join(d, base)


def _turned(parts, notes, rules, pl, anchor, members, turn, zone=(), at=None):
    """pl with the cell turned by `turn` about its anchor and dropped whole at the free spot
    nearest the anchor; None if it has no room. zone: [(refs, mm)] -- the cell's courtyards
    must stay mm clear of those parts' (a forbid zone being repaired)."""
    ax, ay, ar = pl[anchor]
    cell = [anchor] + list(members)
    comp = pin._composite(parts, anchor, members)
    P2 = {r: p for r, p in parts.items() if r not in members}
    P2[anchor] = comp
    poly = np.asarray(notes.get("outline_poly") or pi._rect(notes["outline_mm"]), float)
    G = pin.Grid(poly, [dict(c) for c in notes.get("cutouts", ())] +
                 [{"xy": r["xy"], "d": r["d"], "keepout": r.get("keepout", 0.0)} for r in rules if r["kind"] == "hole"],
                 [r["poly"] for r in rules if r["kind"] == "keepout"])
    for o, v in pl.items():
        if o in cell or o not in parts:
            continue
        m, ai, aj = pin.mask(parts[o], v[2])
        pin._stamp(G, m, ai, aj, *G.ij(*v[:2]), grow=pin.halo(parts[o]))
    forbid = None
    regions = {r["name"]: np.asarray(r["poly"], float) for r in rules if r["kind"] == "region"}
    for r in rules:
        if r["kind"] == "in_region" and set(pi._refs(r["refs"], parts)) & set(cell):
            out = ~pi._inside(regions[r["region"]], np.stack([G.X.ravel(), G.Y.ravel()], axis=1)).reshape(G.H, G.W)
            forbid = out if forbid is None else (forbid | out)
    from scipy.ndimage import distance_transform_edt
    for refs, mm in zone:
        occ = np.zeros((G.H, G.W), np.int16)
        for o in refs:
            if o in pl and o in parts and o not in cell:
                m, ai, aj = pin.mask(parts[o], pl[o][2])
                pin._put(occ, m, ai, aj, *G.ij(*pl[o][:2]))
        if occ.any():
            f = distance_transform_edt(occ == 0) * G.g < mm
            forbid = f if forbid is None else (forbid | f)
    out = {k: list(v) for k, v in pl.items() if k not in members}
    del out[anchor]
    if not pin._drop(G, P2, anchor, np.array([ax, ay]) if at is None else np.asarray(at, float),
                     [(ar + turn) % 360.0], out, forbid):
        return None
    nx, ny, nr = out[anchor]
    for m, (dx, dy, dr) in members.items():
        o = pi._rot([[dx, dy]], nr)[0]
        out[m] = [round(nx + float(o[0]), 4), round(ny + float(o[1]), 4), (nr + dr) % 360.0]
    return out


def _forbid_breaks(stem, rules, pl, parts_path):
    """How many `forbid` apart/thermal breaches pl has (the zones place_init keeps)."""
    fz = [r for r in rules if r["kind"] in ("apart", "thermal") and r.get("forbid", True)]
    return len(pi.floor_breaches(stem, fz + [r for r in rules if r["kind"] in ("fixed", "pin", "panel", "group")],
                                 placements=pl, parts_path=parts_path))


def _forbid_list(stem, rules, pl, parts_path):
    """[(subject, offender, rule)] for each broken `forbid` zone in pl."""
    fz = [r for r in rules if r["kind"] in ("apart", "thermal") and r.get("forbid", True)]
    fx = [r for r in rules if r["kind"] in ("fixed", "pin", "panel", "group")]
    out = []
    for r in fz:
        for sl, subj, det, _ in pi.floor_breaches(stem, [r] + fx, placements=pl, parts_path=parts_path):
            oth = det.split(" from ")[-1].split(",")[0].strip() if " from " in det else None
            out.append((subj, oth, r))
    return out


def _repair(stem, parts, notes, rules, pl, turning, cellmap, fixed, parts_path):
    """One forbid repair for a candidate: the first movable unit on a broken zone that is not
    the cell being turned -- a free-anchor cell or a free part -- re-dropped (same turn)
    at the free spot nearest where it is, clear of every zone it breaks. Returns
    (placements, unit) or (None, why)."""
    br = _forbid_list(stem, rules, pl, parts_path)
    owner = {m: a for a, ms in cellmap.items() for m in ms}
    for subj, oth, r in br:
        for x in (subj, oth):
            if x is None:
                continue
            unit = owner.get(x, x)
            if unit == turning or unit in fixed:
                continue
            members = cellmap.get(unit, {})
            mine = {unit} | set(members)
            # every zone the unit is in, not only the broken ones: the move that fixed the
            # buck's crystal zone first broke its 45 mm photodiode one (optical U7_90). Soft
            # apart rules are tried as zones too, and dropped only if there is no room with
            # them: with forbid zones alone the buck was re-dropped beside the USB socket.
            def zones(soft_too):
                z = []
                for r_ in rules:
                    if r_["kind"] not in ("apart", "thermal") or not (r_.get("forbid", True) or soft_too):
                        continue
                    a_ = set(pi._refs(r_.get("a") or [r_["ref"]], parts))
                    b_ = set(pi._refs(r_.get("b") or r_["others"], parts))
                    if (a_ | b_) & mine:
                        other = (b_ if a_ & mine else a_) - mine
                        z.append((sorted(other), float(r_.get("min_mm", r_.get("apart_mm", 0.0)))))
                return z
            # aimed where the unit WANTS to be -- its own `near` targets -- not where it was
            tg = []
            for r_ in rules:
                if r_["kind"] == "near" and r_.get("ref") in mine and r_["target"].split(".")[0] in pl:
                    tg.append(pl[r_["target"].split(".")[0]][:2])
            at = np.mean(tg, axis=0) if tg else None
            q = (_turned(parts, notes, rules, pl, unit, members, 0.0, zones(True), at=at)
                 or _turned(parts, notes, rules, pl, unit, members, 0.0, zones(False), at=at))
            if q is None:
                return None, "%s has no room clear of its zone" % unit
            return q, unit
    return None, "no movable unit on the broken zone (both sides fixed, or only the turned cell)"


def cells(d, intent, parts_path=None, jobs=4, soft=False, log=print):
    stem = _stem(d)
    src = json.load(open(stem + ".board.json", encoding="utf-8"))
    parts_path = parts_path or stem + ".parts.json"
    parts = json.load(open(parts_path, encoding="utf-8"))["parts"]
    rules = json.load(open(intent, encoding="utf-8"))
    fixed = pi.fixed_refs(rules)
    todo = [r for r in rules if r["kind"] == "group" and r["anchor"] not in fixed]
    pl = {k: list(v) for k, v in src["placements"].items()}
    work = os.path.join(d, "cells")
    os.makedirs(work, exist_ok=True)
    rec = []
    if not todo:
        log("place_cells: no free-anchor cell in the intent -- nothing to turn")
        json.dump(pl, open(stem + ".cells.json", "w"), indent=0)      # unchanged, for a pipeline
        return pl, rec
    # 1. the parent, routed in full
    pstem = _write(os.path.join(work, "parent"), src, stem, pl)
    if not (os.path.exists(pstem + ".route.pkl") and os.path.exists(pstem + ".score.json")):
        ok, msg = _layout(pstem)
        if not ok:
            raise SystemExit("place_cells: the starting board does not lay out:\n" + msg)
        s = _score(pstem, intent, parts_path, save=True)
        json.dump(s, open(pstem + ".score.json", "w"))
    parent = json.load(open(pstem + ".score.json"))
    if "error" in parent:
        raise SystemExit("place_cells: the parent did not route: " + parent["error"])
    log("place_cells: parent %s" % {k: parent.get(k) for k in ("open", "pairs", "uncoupled", "vias", "length_mm", "floor")})
    for g in todo:
        a, members = g["anchor"], g["members"]
        cands = []
        for turn in (90.0, 180.0, 270.0):
            q = _turned(parts, src, rules, pl, a, members, turn)
            tag = "%s_%d" % (a, int((pl[a][2] + turn) % 360))
            if q is None:
                log("place_cells: %s no room" % tag)
                rec.append({"cell": a, "cand": tag, "skipped": "no room"})
                continue
            cands.append((tag, q))

        def run(c):
            tag, q = c
            cs = _write(os.path.join(work, tag), src, stem, q)
            ok, msg = _layout(cs)
            if not ok:
                return tag, q, {"error": "layout: " + msg[-300:]}
            return tag, q, _score(cs, intent, parts_path, parent=pstem + ".route.pkl")

        with ThreadPoolExecutor(jobs) as ex:
            res = list(ex.map(run, cands))
        for tag, q, s in res:
            rec.append({"cell": a, "cand": tag, "score": s})
            log("place_cells:   %-10s %s" % (tag, s.get("error") or {k: s.get(k) for k in
                                                                    ("open", "pairs", "uncoupled", "vias", "length_mm",
                                                                     "floor", "failed")}))
        good = [(tag, q, s) for tag, q, s in res if "error" not in s]
        # A FORBID ZONE IS HARD (lead ruling 2026-11-11): a turn that breaks more zones than
        # its parent gets ONE repair -- the unit breaking it (not this cell) re-dropped clear
        # of the zone, re-scored -- and is otherwise not eligible. --soft-forbid: reported only.
        fb0 = _forbid_breaks(stem, rules, pl, parts_path)
        cellmap = {r["anchor"]: r["members"] for r in todo}
        fixed_units = fixed | {m for r in rules if r["kind"] == "group" and r["anchor"] in fixed for m in r["members"]}
        keep, rep_ = [], []
        for tag, q, s in good:
            s["forbid"] = _forbid_breaks(stem, rules, q, parts_path)
            if s["forbid"] <= fb0 or soft:
                keep.append((tag, q, s))
                continue
            q2, unit = _repair(stem, parts, src, rules, q, a, cellmap, fixed_units, parts_path)
            if q2 is None or _forbid_breaks(stem, rules, q2, parts_path) > fb0:
                log("place_cells: FORBID: %s breaks %d zone(s) (parent %d) and the repair failed: %s -- not eligible"
                    % (tag, s["forbid"], fb0, unit if q2 is None else "%s moved, zones still broken" % unit))
                rec.append({"cell": a, "cand": tag, "ineligible": "forbid", "repair": str(unit)})
                continue
            rep_.append((tag + "r", q2, unit))

        def run2(c):
            tag, q, unit = c
            cs = _write(os.path.join(work, tag), src, stem, q)
            ok, msg = _layout(cs)
            if not ok:
                return tag, q, {"error": "layout: " + msg[-300:]}, unit
            return tag, q, _score(cs, intent, parts_path, parent=pstem + ".route.pkl"), unit

        with ThreadPoolExecutor(jobs) as ex:
            res2 = list(ex.map(run2, rep_))
        for tag, q, s, unit in res2:
            rec.append({"cell": a, "cand": tag, "repaired": unit, "score": s})
            log("place_cells:   %-10s (repaired: %s moved clear of its zone) %s" % (
                tag, unit, s.get("error") or {k: s.get(k) for k in ("open", "pairs", "uncoupled", "vias", "length_mm",
                                                                    "floor", "failed")}))
            if "error" not in s:
                s["forbid"] = _forbid_breaks(stem, rules, q, parts_path)
                keep.append((tag, q, s))
        good = keep
        best = min(good, key=lambda t: _key(t[2])) if good else None
        if best is None or not _better(best[2], parent):
            log("place_cells: %s stays at %g" % (a, pl[a][2]))
            continue
        # 4. confirm by a full route
        tag, q, s = best
        cs = os.path.join(work, tag, os.path.basename(stem))
        full = _score(cs, intent, parts_path, save=True)
        rec.append({"cell": a, "cand": tag, "confirm": full})
        log("place_cells:   %-10s full route %s" % (tag, full.get("error") or {k: full.get(k) for k in (
            "open", "pairs", "uncoupled", "vias", "length_mm", "floor", "failed")}))
        if "error" not in full and _better(full, parent):
            pl, parent, pstem = q, full, cs
            json.dump(full, open(pstem + ".score.json", "w"))
            log("place_cells: %s turned to %g (kept)" % (a, pl[a][2]))
        else:
            log("place_cells: %s's best turn lost its full-route confirm; stays at %g" % (a, pl[a][2]))
    json.dump(rec, open(os.path.join(work, "cells.json"), "w"), indent=1)
    json.dump(pl, open(stem + ".cells.json", "w"), indent=0)
    log("place_cells: best %s -> %s" % ({k: parent.get(k) for k in ("open", "pairs", "uncoupled", "vias", "floor")},
                                       stem + ".cells.json"))
    return pl, rec


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("intent")
    ap.add_argument("--parts")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--soft-forbid", action="store_true",
                    help="keep the best route even where it breaks a forbid zone (reported, not repaired)")
    a = ap.parse_args(argv)
    cells(os.path.abspath(a.dir), os.path.abspath(a.intent),
          os.path.abspath(a.parts) if a.parts else None, a.jobs, a.soft_forbid)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
