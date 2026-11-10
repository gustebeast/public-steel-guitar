"""placescore.py: score placements with the router itself (see ROUTER.md, "Global plan").

A placement is judged the way it will be routed: candidate moves are laid out by layout.py
(PCBFLOW_NUDGE, so layout's own gates refuse an illegal one), each laid-out board is routed
router-alone, and the result is read off in a few plain numbers, best first:

    open      nets the router left open
    pairs     matched-pair faults (layers, vias, skew)
    islands   regional-pour pieces off the pour's main body
    contest   the negotiation's history cost: how hard the nets fought for room
    len_mm    routed length;  vias  layer changes;  sec  router time

Ranked by (open, pairs, islands, contest); length and vias break ties. Every candidate runs
in its own directory, several at once (a process each), and the unmoved board is always
candidate 0 -- the score is only ever read against the same board unmoved.

⚠ ONE ROUTE IS ONE SAMPLE (optical U10 cluster, 2026-11-09): C112 moved 0.3-0.7 mm took
the same board from clean to 2-3 pair faults or 2 nets open, and back. The negotiation is
deterministic but not smooth in the placement, so a single candidate's score is mostly
which way the negotiation happened to fall. Read a candidate against several of its own
neighbours (--n with a small --near R on the part) before believing it is better.

    py -3.12 placescore.py <gen_dir> <board> --near X Y R [--n 8] [--jobs 3] [--seed 1]
    py -3.12 placescore.py <gen_dir> <board> --moves moves.json [--jobs 3]
    py -3.12 placescore.py --score <stem>            (one placed board; prints a JSON line)

<gen_dir> holds the generator's output for <board> (.board.json, .net, ...); layout.py is
run on a copy of it. Moves are in BOARD coordinates (mm, y down), {ref: [dx, dy, drot]}.
The environment layout.py needs (PCBFLOW_FOOTPRINT_DIRS, PCBFLOW_PROJECT) is passed through;
KICAD_PYTHON names KiCad's Python as for ownroute.py.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_PY = os.environ.get("KICAD_PYTHON", "C:/Program Files/KiCad/10.0/bin/python.exe")
PY312 = ["py", "-3.12"]


# ------------------------------------------------------------------ the score (py 3.12)
def score(stem, budget_s=900):
    """Route <stem>.kicad_pcb router-alone; return the score dict."""
    sys.path.insert(0, HERE)
    import numpy as np
    from router.model import Model
    from router.negotiate import Router
    t0 = time.time()
    m = Model(stem)
    r = Router(m)
    r.log = lambda s: None
    nets = r.build_nets(pours=m.fills)
    failed = r.run(budget_s=budget_s)
    H, W = r.H, r.W
    length, vias = 0.0, 0
    for n in nets:
        for p in n.paths:
            if p.size < 2:
                continue
            k, rc = p // (H * W), p % (H * W)
            i, j = rc // W, rc % W
            same = k[1:] == k[:-1]
            vias += int((~same).sum())
            length += float(np.hypot(np.diff(i)[same], np.diff(j)[same]).sum()) * m.pitch
    pair = 0
    for n in nets:
        if n.mate is not None and n.partner is None:
            pair += len(r.pair_faults(n) or ())
    isl = 0
    for n in nets:
        if n.plane and not n.failed:
            got = r._islands(n)
            if got is not None:
                isl += len(got[0])
    return dict(open=len(failed), open_nets=[n.name for n in failed], pairs=pair, islands=isl,
                contest=round(float(r.hist.sum()) + float(r.hist_v.sum()), 1),
                len_mm=round(length, 1), vias=vias, sec=round(time.time() - t0, 1))


def rank_key(s):
    if s is None:
        return (1e9,)
    return (s["open"], s["pairs"], s["islands"], s["contest"], s["len_mm"], s["vias"])


# ------------------------------------------------------------------ candidates
def _parts(stem):
    """{ref: (x0, x1, y0, y1, npads)} from the placed board's pads (board frame)."""
    sys.path.insert(0, HERE)
    import repair_search as RS
    txt = open(stem + ".kicad_pcb", encoding="utf-8").read()
    box = {}
    for p in RS._pads(txt):
        ref = (p.get("name") or "").rsplit(".", 1)[0]
        if not ref:
            continue
        r_ = p["r"]
        xs = (p["x1"] - r_, p["x1"] + r_, p["x2"] - r_, p["x2"] + r_)
        ys = (p["y1"] - r_, p["y1"] + r_, p["y2"] - r_, p["y2"] + r_)
        b = box.get(ref)
        box[ref] = (min(xs + ((b[0],) if b else ())), max(xs + ((b[1],) if b else ())),
                    min(ys + ((b[2],) if b else ())), max(ys + ((b[3],) if b else ())),
                    (b[4] if b else 0) + 1)
    return box


def near_moves(stem, x, y, rad, n, seed=1, step=(0.3, 1.2), turn_p=0.15, gap=0.25,
               kinds="CRLD", max_pads=3):
    """`n` single-part moves of small parts within `rad` mm of (x, y), each kept `gap` mm
    clear of every other part's lands (layout's own gates judge the rest)."""
    box = _parts(stem)
    rng = random.Random(seed)
    cand = sorted(r for r, b in box.items()
                  if r[:1] in kinds and r[1:].isdigit() and b[4] <= max_pads
                  and math.hypot((b[0] + b[1]) / 2 - x, (b[2] + b[3]) / 2 - y) <= rad)
    # every part once before any part twice: a pool that drew C112 four times out of five
    # judged C112, not the cluster
    order = []
    out, tries = [], 0
    while cand and len(out) < n and tries < 200 * n:
        tries += 1
        if not order:
            order = list(cand)
            rng.shuffle(order)
        ref = order.pop()
        x0, x1, y0, y1, _ = box[ref]
        a, d = rng.uniform(0, 2 * math.pi), rng.uniform(*step)
        dx, dy = round(d * math.cos(a), 3), round(d * math.sin(a), 3)
        rot = rng.choice((90, 180, 270)) if rng.random() < turn_p else 0
        q = (x0 + dx - gap, x1 + dx + gap, y0 + dy - gap, y1 + dy + gap)
        if any(k != ref and q[0] < b[1] and q[1] > b[0] and q[2] < b[3] and q[3] > b[2]
               for k, b in box.items()):
            continue
        mv = {ref: [dx, dy, rot]}
        if mv not in out:
            out.append(mv)
    return out


# ------------------------------------------------------------------ one candidate
def _layout(gen_dir, board, work, moves, env):
    os.makedirs(work, exist_ok=True)
    for f in os.listdir(gen_dir):
        src = os.path.join(gen_dir, f)
        if f.startswith(board + ".") and os.path.isfile(src) and not f.endswith(".kicad_pcb"):
            shutil.copyfile(src, os.path.join(work, f))
    e = dict(env)
    if moves:
        nj = os.path.join(work, "nudge.json")
        # layout's nudge frame is the generator's: y up
        json.dump({r: [d[0], -d[1], d[2] if len(d) > 2 else 0] for r, d in moves.items()},
                  open(nj, "w"))
        e["PCBFLOW_NUDGE"] = nj
    r = subprocess.run([KICAD_PY, os.path.join(HERE, "layout.py"), os.path.join(work, board)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)
    ok = r.returncode == 0 and os.path.exists(os.path.join(work, board + ".kicad_pcb"))
    tail = (r.stdout + r.stderr).strip().splitlines()
    return ok, (tail[-1] if tail else "")[:160]


def _one(args):
    i, gen_dir, board, out, moves, env = args
    work = os.path.join(out, "c%02d" % i)
    if os.path.isdir(work):
        shutil.rmtree(work)
    t0 = time.time()
    ok, why = _layout(gen_dir, board, work, moves, env)
    if not ok:
        return dict(i=i, moves=moves, refused=why, sec=round(time.time() - t0, 1))
    r = subprocess.run(PY312 + [os.path.abspath(__file__), "--score", os.path.join(work, board)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("{")]
    if not line:
        return dict(i=i, moves=moves, refused="score failed: " + (r.stderr.strip().splitlines() or [""])[-1][:160])
    return dict(i=i, moves=moves, score=json.loads(line[-1]), sec=round(time.time() - t0, 1))


def run(gen_dir, board, out, cands, jobs=3, log=print):
    """Lay out and score [{}] + cands, `jobs` at once; returns the results, best first."""
    os.makedirs(out, exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    todo = [(i, gen_dir, board, out, mv, env) for i, mv in enumerate([{}] + list(cands))]
    res = []
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for got in ex.map(_one, todo):
            res.append(got)
            log(_row(got))
            with open(os.path.join(out, "scores.jsonl"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps(got) + "\n")
    res.sort(key=lambda g: rank_key(g.get("score")))
    return res


def _row(g):
    mv = " ".join("%s(%+.2f,%+.2f%s)" % (r, d[0], d[1], ",%g" % d[2] if len(d) > 2 and d[2] else "")
                  for r, d in g["moves"].items()) or "unmoved"
    s = g.get("score")
    if s is None:
        return "c%02d %-34s refused: %s" % (g["i"], mv, g.get("refused"))
    return ("c%02d %-34s open %d pairs %d islands %d contest %9.1f len %7.1f vias %3d  %4.0f s%s"
            % (g["i"], mv, s["open"], s["pairs"], s["islands"], s["contest"], s["len_mm"],
               s["vias"], g["sec"], "  " + ",".join(s["open_nets"]) if s["open_nets"] else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("gen_dir", nargs="?")
    ap.add_argument("board", nargs="?")
    ap.add_argument("--score", metavar="STEM")
    ap.add_argument("--near", nargs=3, type=float, metavar=("X", "Y", "R"))
    ap.add_argument("--moves", help="json: a list of {ref: [dx, dy, drot]} candidates")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.score:
        print(json.dumps(score(a.score)))
        return
    out = a.out or os.path.join(a.gen_dir, "placescore")
    if a.moves:
        cands = json.load(open(a.moves))
    else:
        # candidates are drawn on the unmoved board: lay it out once first
        ok, why = _layout(a.gen_dir, a.board, os.path.join(out, "base"), {},
                          dict(os.environ, PYTHONIOENCODING="utf-8"))
        if not ok:
            sys.exit("layout refused the unmoved board: " + why)
        cands = near_moves(os.path.join(out, "base", a.board), *a.near, n=a.n, seed=a.seed)
    print("%d candidate(s) + unmoved, %d at once" % (len(cands), a.jobs))
    res = run(a.gen_dir, a.board, out, cands, jobs=a.jobs)
    print("\nbest first:")
    for g in res:
        print("  " + _row(g))


if __name__ == "__main__":
    main()
