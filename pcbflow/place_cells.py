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

Floor breaches are reported per candidate. With --strict, a turn that breaks more `forbid`
zones than its parent is not eligible (optical's PHY: the only turn that routed 0 open put
the buck's switch node 9.2 mm from the PHY crystal against a 10 mm zone -- the author's
call, so it is a flag, not a default).

Bounded: at most 3 candidates + 1 confirm per cell. Writes <dir>/cells/<anchor>_<rot>/,
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


def _turned(parts, notes, rules, pl, anchor, members, turn):
    """pl with the cell turned by `turn` about its anchor and dropped whole at the free spot
    nearest the anchor; None if it has no room."""
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
    out = {k: list(v) for k, v in pl.items() if k not in members}
    del out[anchor]
    if not pin._drop(G, P2, anchor, np.array([ax, ay]), [(ar + turn) % 360.0], out, forbid):
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


def cells(d, intent, parts_path=None, jobs=4, strict=False, log=print):
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
        # --strict: a turn that breaks more forbid zones than its parent is not eligible
        fb0 = _forbid_breaks(stem, rules, pl, parts_path)
        for tag, q, s in good:
            s["forbid"] = _forbid_breaks(stem, rules, q, parts_path)
        if strict:
            out_ = [t for t, q, s in good if s["forbid"] > fb0]
            if out_:
                log("place_cells: --strict: %s break more forbid zones than the parent (%d) -- not eligible"
                    % (" ".join(out_), fb0))
            good = [(t, q, s) for t, q, s in good if s["forbid"] <= fb0]
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
    ap.add_argument("--strict", action="store_true",
                    help="a turn that breaks more forbid zones than its parent is not eligible")
    a = ap.parse_args(argv)
    cells(os.path.abspath(a.dir), os.path.abspath(a.intent),
          os.path.abspath(a.parts) if a.parts else None, a.jobs, a.strict)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
