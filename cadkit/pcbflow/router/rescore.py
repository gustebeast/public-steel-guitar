"""rescore.py: route a placement CHANGE, not the whole board (PLACEMENT.md step (c)).

A refinement candidate moves a few parts of a board that has already been routed (the
parent). Every net whose pads did not move, and whose parent copper is still legal against
the candidate's pads, starts from that copper; only the rest is routed, and the
negotiation then re-routes whatever they collide with -- the "plus whatever the
negotiation drags in" of the plan. The finishing stages (pairs, pour islands) look only at
nets that changed.

    save(r, path)                        after a full Router.run: the routed board, by net
    delta_run(r, parent, budget_s)       instead of Router.run on the candidate: returns the
                                          failed nets, as run() does, and how many were kept

A net is KEPT when its pieces (the pad copper it has to join, after the pad-merge
crossing) are cell-for-cell the parent's, and every cell of its parent paths keeps its
clearance from the candidate's fixed copper (pads, held tracks, vias, edge). A plane net
keeps the joins of its unchanged pieces (keep_paths, the machinery the negotiation already
uses) and re-joins the rest.
"""
from __future__ import annotations

import pickle
import time

import numpy as np


def _key(cells):
    return np.sort(np.asarray(cells, np.int64)).tobytes()


def save(r, path):
    out = {}
    for n in r.nets:
        out[n.name] = dict(paths=[np.asarray(p, np.int64) for p in (n.paths or ())],
                           necks=[np.asarray(k, bool) for k in (n.necks or ())],
                           failed=bool(n.failed), n_open=int(getattr(n, "n_open", 0) or 0),
                           pieces=[_key(p) for p in n.pieces], relaxed=bool(n.relaxed),
                           faulted=bool(n.mate is not None and not n.failed and (r.pair_faults(n) or ())))
    with open(path, "wb") as fh:
        pickle.dump({"H": r.H, "W": r.W, "L": r.L, "nets": out,
                     "hist": r.hist.copy(), "hist_v": r.hist_v.copy(),
                     "pf": float(getattr(r, "_pf_last", 1.0))}, fh)


def _legal(r, net, paths, necks):
    """Does this copper still clear the candidate's fixed copper?"""
    m = r.m
    L, H, W = r.L, r.H, r.W
    for q, p in enumerate(paths):
        if p.size == 0:
            continue
        k, rc = p // (H * W), p % (H * W)
        i, j = rc // W, rc % W
        own = m.n1[k, i, j] == net.id
        fd = np.where(own, m.d2[k, i, j], m.d1[k, i, j])
        nk = necks[q] if q < len(necks) and necks[q].size == p.size else np.zeros(p.size, bool)
        half = np.where(nk, r.NECK_W, net.width) / 2.0
        # a land's own cells sit inside the net's own copper: fd there is to the next net
        if (fd < half + m.clear + m.margin - 1e-6).any():
            return False
        if (m.edge[i, j] < half + m.edge_clear + m.margin - 1e-6).any():
            return False
        via = np.nonzero(k[1:] != k[:-1])[0]
        if via.size:
            vi, vj = i[via], j[via]
            fdv = np.where(m.n1[:, vi, vj] == net.id, m.d2[:, vi, vj], m.d1[:, vi, vj])
            if (fdv < m.via_d / 2.0 + m.clear + m.margin - 1e-6).any():
                return False
            if m.via_ban[vi, vj].any():
                return False
    return True


# ⚠ A CHANGE IS NEGOTIATED WHERE THE PARENT LEFT OFF (output_panel, 2026-11-10). Started
# cold -- no history, pf 0.5 -- one resistor moved 0.6 mm dragged 42 nets back into the
# negotiation, took 264 s against a 390 s full route, and ended 9 open against the full
# route's 1: the kept copper had been laid under a price in the thousands, and re-priced at
# 0.5 every net it touched walked back into contested space. The child starts from the
# parent's history and its closing price (PF_START caps it), so a new net goes round kept
# copper unless there is no way round.
PF_START = float(__import__("os").environ.get("RESCORE_PF", "50"))
LOCK_PAIRS = __import__("os").environ.get("RESCORE_LOCK", "1") != "0"


def delta_run(r, parent, iters=40, pf0=None, budget_s=900, log=None):
    """Router.run for a candidate routed from its parent. Returns (failed nets, stats)."""
    log = log or (lambda s: None)
    t0 = time.time()
    if (parent["H"], parent["W"], parent["L"]) != (r.H, r.W, r.L):
        raise SystemExit("rescore: the parent was routed on another grid (outline or layers changed)")
    r._premerge()
    r._neg = (1.6, 0.4)
    kept, changed, partial = [], [], []
    for net in r.nets:
        par = parent["nets"].get(net.name)
        if par is None or par["failed"]:
            changed.append(net)
            continue
        mine = [_key(p) for p in net.pieces]
        if not net.plane:
            if mine == par["pieces"] and _legal(r, net, par["paths"], par["necks"]):
                net.paths, net.necks = list(par["paths"]), list(par["necks"])
                net.relaxed = par["relaxed"]
                kept.append(net)
            else:
                changed.append(net)
            continue
        # a plane net: piece 0 is the pour; path q joins piece q + 1
        if mine == par["pieces"] and _legal(r, net, par["paths"], par["necks"]):
            net.paths, net.necks = list(par["paths"]), list(par["necks"])
            kept.append(net)
            continue
        where = {kk: q for q, kk in enumerate(par["pieces"])}
        kp = {}
        for q in range(1, len(net.pieces)):
            pq = where.get(mine[q])
            if pq is None or pq - 1 >= len(par["paths"]) or not par["paths"][pq - 1].size:
                continue
            p_, n_ = par["paths"][pq - 1], par["necks"][pq - 1] if pq - 1 < len(par["necks"]) else None
            if _legal(r, net, [p_], [n_] if n_ is not None else []):
                kp[q] = (p_, n_)
        net.keep_paths = kp or None
        partial.append(net)
        changed.append(net)
    for net in kept:
        r._mark(net)
    if pf0 is None:
        if parent.get("hist") is not None and parent["hist"].shape == r.hist.shape:
            r.hist[:] = parent["hist"]
            r.hist_v[:] = parent["hist_v"]
            pf0 = min(parent.get("pf", 1.0), PF_START)
        else:
            pf0 = 0.5
    log("rescore: %d nets kept from the parent, %d to route (%d plane nets keep %d joins)"
        % (len(kept), len(changed), len(partial), sum(len(n.keep_paths or ()) for n in partial)))
    # ⚠ A PAIR THE PARENT COULD NOT FINISH IS LOCKED, A CLEAN ONE IS NOT (2026-11-10).
    # Left free, output_panel's THRU_DP/DM -- faulted in the parent -- was dragged back into
    # the negotiation by a resistor moved 0.6 mm and its finish ran again: 140 s of a 210 s
    # re-score, to the same fault. But locking EVERY kept pair broke optical u10e/c05: its
    # clean ULPI pairs could not make way, 2 nets open where the full route closes all (6 s
    # and clean unlocked, 37 s and 2 open locked). So only a kept pair that was faulted in
    # the parent holds its copper: the change cannot finish it (its pads did not move),
    # and a move that targets it changes its pieces, which un-keeps it. Any lock also ends
    # the re-score's rounds after 3 without gain, not 8.
    lock = ({n for n in kept if n.group is not None
             and (parent["nets"][n.name].get("faulted")
                  or (n.mate is not None and parent["nets"].get(n.mate.name, {}).get("faulted")))}
            if LOCK_PAIRS else set())
    todo, pf = r._rounds(changed, pf0, iters, budget_s, locked=lock)
    r._pf_last = pf
    todo = r._priority_repair(todo, pf)
    r._rip(todo)
    # the finish looks at what changed: a pair kept whole from the parent is as it was
    moved = set(changed) | {n for n in r.nets if n.failed}
    for n in r.nets:
        if n in kept and n.paths and parent["nets"][n.name]["paths"]:
            same = len(n.paths) == len(parent["nets"][n.name]["paths"]) and all(
                a.size == b.size and (a == b).all() for a, b in zip(n.paths, parent["nets"][n.name]["paths"]))
            if not same:
                moved.add(n)
    r._only = moved | {n.mate for n in moved if n.mate is not None}
    try:
        r._finish_pairs()
        r._fallback_pairs()
        r._pour_islands()
    finally:
        r._only = None
    for n in kept:
        if n not in moved and parent["nets"][n.name]["n_open"]:
            n.n_open = parent["nets"][n.name]["n_open"]
    return [n for n in r.nets if n.failed], dict(kept=len(kept), routed=len(changed),
                                                  moved=len(moved), sec=round(time.time() - t0, 1))
