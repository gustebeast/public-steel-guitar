"""place_refine.py: refine a placement from the router's own reports (PLACEMENT.md step (d)).

    py -3.12 place_refine.py <dir> <intent.json> [--rounds 4] [--cands 8] [--jobs 4]

<dir> holds the board (<stem>.net, <stem>.board.json with the placements to start from,
<stem>.parts.json from place_geom); the stem is the one *.board.json in it. Each round:

  1. the parent is routed in full (score.py --save): its failed nets, faulted pairs and
     hotspots name the parts to move -- the parts beside the hotspots, and the small parts
     on a failed net or a faulted pair (a fine-pitch IC is not shoved to free one pin);
  2. moves for those parts only: 0.5 / 1.0 mm along each axis, a quarter turn within the
     part's `rot` rule (a half turn for a two-pad part), each kept only if every HARD
     intent rule still holds and no courtyard meets another;
  3. the best `cands` (nearest the trouble first) are laid out (layout.py) and re-scored as
     changes of the parent (router/rescore.py), `jobs` at a time;
  4. the best candidate that beats the parent is routed in full; kept only if the full
     route beats the parent too (a re-score is "what this change does", one route is one
     sample, so a gain is believed only when the full route sees it), and it becomes the
     next parent. A round with nothing kept ends the run.

Bounded: rounds x cands fixed up front. Writes <dir>/refine/<round>/<cand>/ and a log of
every candidate (refine.json), and leaves the best placements in <dir>/<stem>.refined.json.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_intent as pi  # noqa: E402

KICAD_PY = os.environ.get("KICAD_PYTHON", r"C:\Program Files\KiCad\10.0\bin\python.exe")
STEPS = (0.5, 1.0)
SMALL = 8                # a part with more pads than this is not moved to free one net


def _key(s):
    """Lexicographic: open, pair faults, islands, uncoupled mm in 0.5 mm bins (below that is
    noise), then vias and length."""
    return (s["open"], s["pairs"], s["islands"], round(s["uncoupled"] * 2) / 2.0, s["vias"], s["length_mm"])


def _better(a, b):
    """a beats b on the first four, or ties them with 2 % fewer vias or 2 % less length."""
    ka, kb = _key(a)[:4], _key(b)[:4]
    return ka < kb or (ka == kb and (a["vias"] <= b["vias"] * 0.98 or a["length_mm"] <= b["length_mm"] * 0.98))


def _stem(d):
    js = glob.glob(os.path.join(d, "*.board.json"))
    if len(js) != 1:
        raise SystemExit("place_refine: %s must hold exactly one *.board.json" % d)
    return js[0][:-len(".board.json")]


def _score(stem, parent=None, save=False, budget=900):
    cmd = [sys.executable, "-m", "router.score", stem, "--jobs", "1", "--budget", str(budget)]
    if parent:
        cmd += ["--parent", parent]
    if save:
        cmd += ["--save", "auto"]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    for line in reversed(p.stdout.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return {"error": (p.stderr or p.stdout)[-600:]}


def _layout(stem):
    p = subprocess.run([KICAD_PY, os.path.join(HERE, "layout.py"), stem], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return p.returncode == 0, (p.stdout + p.stderr)[-600:]


def _subjects(score, parts, notes, fixed):
    """The parts the router's report names, worst trouble first: the small parts on a failed
    net (an open outranks everything), then on a faulted pair, then beside the hotspots
    (small parts before ICs).

    ⚠ OPENS FIRST (output_panel, 2026-11-11): hotspot parts were listed first and the eight
    candidates went to R17 / C29 / C26 / U1 -- contention -- while SWDIO stayed open, its
    test pad TP1 eleventh on the list and never tried."""
    pl = notes["placements"]
    out = []

    def pair_mates(names):
        names = set(names)
        for nm in list(names):
            if nm.endswith("_DP"):
                names.add(nm[:-3] + "_DM")
            if nm.endswith("_DM"):
                names.add(nm[:-3] + "_DP")
        return names

    for bad in (set(score.get("failed") or ()), pair_mates(score.get("faulted") or ())):
        for ref in sorted(parts):
            if ref in fixed or ref in out or ref not in pl or len(parts[ref]["pads"]) > SMALL:
                continue
            if any(q["net"] in bad for q in parts[ref]["pads"]):
                out.append(ref)
    hot = [ref for h in score.get("hot") or () for ref in h.get("near") or ()]
    for big in (False, True):
        for ref in hot:
            if ref in parts and ref not in fixed and ref not in out and ref in pl                     and (len(parts[ref]["pads"]) > SMALL) == big:
                out.append(ref)
    return out


def _pull(ref, parts, pl, notes, rules, bad):
    """A part on a failed net, dropped at the free spot nearest the far end of that net
    (place_init's legaliser: courtyards, halos, outline, holes, keep-outs, its region)."""
    import place_init as pin
    P = pi.Placed(parts, pl)
    mine = [q for q in parts[ref]["pads"] if q["net"] in bad]
    if not mine:
        return None
    far = []
    for o, p in parts.items():
        if o == ref or o not in pl:
            continue
        for q in p["pads"]:
            if q["net"] == mine[0]["net"]:
                far.append(P.pad(o, q["num"]))
    if not far:
        return None
    # the anchor goes where the pad lands on the far end, offset by the pad's own offset
    off = pi._rot([mine[0]["xy"]], pl[ref][2])[0]
    t = np.mean(far, axis=0) - off
    poly = np.asarray(notes.get("outline_poly") or pi._rect(notes["outline_mm"]), float)
    G = pin.Grid(poly, [dict(c) for c in notes.get("cutouts", ())] +
                 [{"xy": r["xy"], "d": r["d"], "keepout": r.get("keepout", 0.0)} for r in rules if r["kind"] == "hole"],
                 [r["poly"] for r in rules if r["kind"] == "keepout"])
    for o in pl:
        if o == ref or o not in parts:
            continue
        m, ai, aj = pin.mask(parts[o], pl[o][2])
        pin._stamp(G, m, ai, aj, *G.ij(*pl[o][:2]), grow=pin.halo(parts[o]))
    out = dict(pl)
    if not pin._drop(G, parts, ref, t, [pl[ref][2]], out):
        return None
    return out


def _moves(ref, parts, rules, rot_of):
    m = []
    for s in STEPS:
        for dx, dy in ((s, 0), (-s, 0), (0, s), (0, -s)):
            m.append((dx, dy, 0.0))
    allowed = rot_of.get(ref)
    turns = (90.0, -90.0) if len(parts[ref]["pads"]) > 2 else (90.0, 180.0)
    for t in turns:
        m.append((0.0, 0.0, t))
    return m, allowed


def _legal(P, ref, rules, notes, H, near):
    """Every hard rule that names ref (or every outline/keepout/hole rule) still holds, and
    its courtyard meets no other's."""
    for r in rules:
        if not r.get("hard", True):
            continue
        k = r["kind"]
        names = set()
        for f in ("ref", "cap"):
            if r.get(f):
                names.add(r[f])
        if isinstance(r.get("refs"), list):
            names |= set(r["refs"])
        if k in ("outline", "keepout", "hole", "height") or ref in names:
            for s, subj, _ in pi.check(r, P, notes, H):
                if s < -1e-6 and (subj == ref or k not in ("outline", "keepout", "hole", "height")):
                    return False
    c = P.crtyd(ref)
    for o in near:
        if pi._poly_dist(c, P.crtyd(o)) < 0.0:
            return False
    return True


def refine(d, intent, rounds=4, cands=8, jobs=4, log=print):
    stem = _stem(d)
    base = os.path.basename(stem)
    parts = json.load(open(stem + ".parts.json", encoding="utf-8"))["parts"]
    rules = json.load(open(intent, encoding="utf-8"))
    notes0 = json.load(open(stem + ".board.json", encoding="utf-8"))
    notes0["_regions"] = {r["name"]: r["poly"] for r in rules if r["kind"] == "region"}
    notes0["_panel"] = [r for r in rules if r["kind"] == "panel"]
    rot_of = {r["ref"]: [float(a) % 360 for a in r["allowed"]] for r in rules if r["kind"] == "rot"}
    fixed = {r["ref"] for r in rules if r["kind"] in ("fixed", "pin", "panel")}
    H = pi.heights()
    hist = []
    work = os.path.join(d, "refine")
    os.makedirs(work, exist_ok=True)
    # round 0: the parent, laid out and routed in full
    cur = os.path.join(work, "r0")
    os.makedirs(cur, exist_ok=True)
    # the parent's full route is reused while its board and netlist are unchanged
    same = all(os.path.exists(os.path.join(cur, base + ext)) and
               open(stem + ext, "rb").read() == open(os.path.join(cur, base + ext), "rb").read()
               for ext in (".net", ".board.json")) \
        and os.path.exists(os.path.join(cur, "score.json")) and os.path.exists(os.path.join(cur, base + ".route.pkl"))
    t0 = time.time()
    if same:
        ps = json.load(open(os.path.join(cur, "score.json")))
    else:
        for ext in (".net", ".board.json"):
            shutil.copy(stem + ext, os.path.join(cur, base + ext))
        ok, out = _layout(os.path.join(cur, base))
        if not ok:
            raise SystemExit("place_refine: the starting placement fails layout:\n" + out)
        ps = _score(os.path.join(cur, base), save=True)
        json.dump(ps, open(os.path.join(cur, "score.json"), "w"))
    log("r0 parent: %s  (%.0f s)" % ({k: ps.get(k) for k in ("open", "pairs", "uncoupled", "vias", "failed", "faulted")},
                                      time.time() - t0))
    hist.append(dict(round=0, cand="parent", score=ps))
    for rd in range(1, rounds + 1):
        notes = json.load(open(os.path.join(cur, base + ".board.json"), encoding="utf-8"))
        notes["_regions"], notes["_panel"] = notes0["_regions"], notes0["_panel"]
        subj = _subjects(ps, parts, notes, fixed)
        props = []
        bad = set(ps.get("failed") or ())
        for ref in subj:
            if any(q["net"] in bad for q in parts[ref]["pads"]):
                pl = _pull(ref, parts, notes["placements"], notes, rules, bad)
                if pl is not None:
                    x0, y0 = notes["placements"][ref][:2]
                    dx, dy = pl[ref][0] - x0, pl[ref][1] - y0
                    if math.hypot(dx, dy) > 0.3:
                        P = pi.Placed(parts, pl)
                        near = [o for o in pl if o != ref and math.hypot(pl[o][0] - pl[ref][0], pl[o][1] - pl[ref][1]) < 15.0]
                        if _legal(P, ref, rules, notes, H, near):
                            props.append((ref, round(dx, 2), round(dy, 2), 0.0, pl, "pull"))
        for ref in subj:
            mv, allowed = _moves(ref, parts, rules, rot_of)
            x, y, a = notes["placements"][ref]
            for dx, dy, t in mv:
                na = (a + t) % 360
                if t and allowed is not None and na not in allowed:
                    continue
                pl = dict(notes["placements"])
                pl[ref] = [x + dx, y + dy, na]
                P = pi.Placed(parts, pl)
                cx, cy = x + dx, y + dy
                near = [o for o in pl if o != ref and math.hypot(pl[o][0] - cx, pl[o][1] - cy) < 15.0]
                if _legal(P, ref, rules, notes, H, near):
                    props.append((ref, dx, dy, t, pl, "step"))
        # worst trouble first; per part a pull, then the smallest steps
        props.sort(key=lambda p: (subj.index(p[0]), p[5] != "pull", abs(p[1]) + abs(p[2]) + (0.75 if p[3] else 0)))
        seen, pick = {}, []
        for p in props:
            if seen.get(p[0], 0) < 2:
                pick.append(p)
                seen[p[0]] = seen.get(p[0], 0) + 1
            if len(pick) >= cands:
                break
        log("r%d: %d parts named (%s), %d legal moves, %d tried" % (rd, len(subj), " ".join(subj[:10]), len(props), len(pick)))
        if not pick:
            break
        parent_pkl = os.path.join(cur, base + ".route.pkl")

        def run(i_p):
            i, (ref, dx, dy, t, pl, _kind) = i_p
            cd = os.path.join(work, "r%d" % rd, "c%02d" % i)
            os.makedirs(cd, exist_ok=True)
            shutil.copy(os.path.join(cur, base + ".net"), os.path.join(cd, base + ".net"))
            nb = json.load(open(os.path.join(cur, base + ".board.json"), encoding="utf-8"))
            nb["placements"] = pl
            json.dump(nb, open(os.path.join(cd, base + ".board.json"), "w"), indent=0)
            ok, out = _layout(os.path.join(cd, base))
            if not ok:
                return dict(dir=cd, ref=ref, move=[dx, dy, t], error="layout: " + out[-200:])
            s = _score(os.path.join(cd, base), parent=parent_pkl)
            return dict(dir=cd, ref=ref, move=[dx, dy, t], score=s)

        t1 = time.time()
        with ThreadPoolExecutor(jobs) as ex:
            res = list(ex.map(run, enumerate(pick)))
        for r_ in res:
            hist.append(dict(round=rd, cand=os.path.basename(r_["dir"]), ref=r_["ref"], move=r_["move"],
                             score=r_.get("score"), error=r_.get("error")))
            s = r_.get("score") or {}
            log("   %-5s %+.1f %+.1f %+4.0f : %s" % (r_["ref"], *r_["move"], r_.get("error") or
                {k: s.get(k) for k in ("open", "pairs", "uncoupled", "vias", "length_mm", "sec", "failed")}))
        good = sorted((r_ for r_ in res if r_.get("score") and "open" in r_["score"]
                       and _better(r_["score"], ps)), key=lambda r_: _key(r_["score"]))
        log("r%d: %d candidates re-scored in %.0f s, %d beat the parent" % (rd, len(res), time.time() - t1, len(good)))
        kept = None
        for g in good[:2]:
            t2 = time.time()
            fs = _score(os.path.join(g["dir"], base), save=True)
            log("   confirm %s %s: full route %s (%.0f s)" % (g["ref"], g["move"], {k: fs.get(k) for k in (
                "open", "pairs", "uncoupled", "vias", "failed", "faulted")}, time.time() - t2))
            hist.append(dict(round=rd, cand="confirm " + os.path.basename(g["dir"]), score=fs))
            if "open" in fs and _better(fs, ps):
                kept = (g, fs)
                break
        json.dump(hist, open(os.path.join(work, "refine.json"), "w"), indent=1)
        if kept is None:
            log("r%d: nothing confirmed -- stopping" % rd)
            break
        cur, ps = kept[0]["dir"], kept[1]
        log("r%d: kept %s %s" % (rd, kept[0]["ref"], kept[0]["move"]))
    best = json.load(open(os.path.join(cur, base + ".board.json"), encoding="utf-8"))["placements"]
    json.dump(best, open(stem + ".refined.json", "w"), indent=0)
    json.dump(hist, open(os.path.join(work, "refine.json"), "w"), indent=1)
    log("best: %s -> %s.refined.json" % ({k: ps.get(k) for k in ("open", "pairs", "uncoupled", "vias", "failed", "faulted")}, base))
    return ps


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("intent")
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--cands", type=int, default=8)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    t0 = time.time()
    refine(os.path.abspath(a.dir), os.path.abspath(a.intent), a.rounds, a.cands, a.jobs,
           log=lambda s: print("[%5.0f s] %s" % (time.time() - t0, s), flush=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
