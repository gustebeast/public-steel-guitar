"""Zone fills that are the same for the same board: PCBFLOW_STABLE_FILL (default on; =0 for KiCad's own fill).

⚠ KICAD'S FILLER IS NOT REPRODUCIBLE (brain_board, 2026-11-19). layout.py run twice on
one input wrote two boards that differed ONLY in zone filled_polygon vertices: the same
shapes with different vertex sets on the rounded corners (VIN_BRAIN, VIN_SW). The router
takes those fills as plane-join targets (Model.fills), and the post-route refills feed
repair_planes / close_last / DRC, so two replays of one placement could split before any
routing. fill(board, zones) replaces pcbnew.ZONE_FILLER(board).Fill(zones) at every call
site: with the flag on, a board whose fill INPUTS were filled before gets that fill back,
byte for byte; anything new is filled by KiCad and remembered.

THE KEY is everything a fill depends on: the board as KiCad would save it with every
filled_polygon, uuid and tstamp stripped (copper, pads, zone outlines AND settings --
priority, clearances, thermal relief, minimum width, island removal -- and the board's
design rules), the project's .kicad_pro and .kicad_dru beside the board, the KiCad
version, and which zones are being filled. A stale hit would lay the wrong pour, which is
worse than jitter, so nothing is left out of the key to save time (a key costs a save,
~0.1 s on brain_board).

THE STORE is %LOCALAPPDATA%/pcbflow/fillcache (or $PCBFLOW_FILL_CACHE), one compressed
file per key, bounded by FILL_CACHE_MB: the least recently used entries go first.
"""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
import time

import numpy as np
import pcbnew

ON = os.environ.get("PCBFLOW_STABLE_FILL", "1") == "1"   # default on 2026-11-19 (gate: layout x2 md5, keep-route x2, XOR 0 vs fresh fill)
FILL_CACHE_MB = float(os.environ.get("PCBFLOW_FILL_CACHE_MB", "2000"))
STATS = {"hit": 0, "miss": 0}


def _store():
    d = os.environ.get("PCBFLOW_FILL_CACHE") or os.path.join(
        os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(), "pcbflow", "fillcache")
    os.makedirs(d, exist_ok=True)
    return d


def _strip_fills(txt):
    """The saved board with every (filled_polygon ...) block removed (paren-matched)."""
    out, i, tag = [], 0, "(filled_polygon"
    while True:
        j = txt.find(tag, i)
        if j < 0:
            out.append(txt[i:])
            return "".join(out)
        out.append(txt[i:j])
        depth, k = 0, j
        while True:
            c = txt[k]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        i = k + 1


def _blocks(txt):
    """The board's top-level s-expressions, SORTED: the key must not depend on the order
    KiCad holds items in (brain_board, 2026-11-19: two layout runs held the same 440
    footprints in different orders -- and the filler's output depends on that order, which
    is the jitter this module exists for)."""
    body = txt[txt.index("(", 1):]
    out, depth, start, q = [], 0, None, False
    for k, c in enumerate(body):
        if c == '"' and body[k - 1] != "\\":
            q = not q
        if q:
            continue
        if c == "(":
            depth += 1
            if depth == 1:
                start = k
        elif c == ")":
            if depth == 1:
                out.append(body[start:k + 1])
            depth -= 1
    return sorted(out)


def _zid(z):
    """A zone by what it IS, not where it sits in board.Zones() (the order moves)."""
    h = hashlib.sha256()
    o = z.Outline()
    h.update(repr((z.GetNetname(), [int(L) for L in z.GetLayerSet().Seq()],
                   z.GetAssignedPriority(), z.GetIsRuleArea(), o.OutlineCount(),
                   [[(o.COutline(i).CPoint(j).x, o.COutline(i).CPoint(j).y)
                     for j in range(o.COutline(i).PointCount())] for i in range(o.OutlineCount())]
                   )).encode())
    return h.hexdigest()[:16]


def _named(zones):
    """[(name, zone)]: content id, plus an ordinal among identical zones (which fill alike)."""
    seen, out = {}, []
    for z in sorted(zones, key=_zid):
        i = _zid(z)
        seen[i] = seen.get(i, -1) + 1
        out.append(("%s_%d" % (i, seen[i]), z))
    return out


def _key(board, zones):
    fd, tmp = tempfile.mkstemp(suffix=".kicad_pcb")
    os.close(fd)
    try:
        pcbnew.SaveBoard(tmp, board)
        txt = open(tmp, encoding="utf-8").read()
    finally:
        for p in (tmp, tmp[:-len(".kicad_pcb")] + ".kicad_pro"):
            try:
                os.remove(p)
            except OSError:
                pass
    txt = _strip_fills(txt)
    txt = re.sub(r'\((?:uuid|tstamp) "?[^)"]*"?\)', "", txt)
    txt = "\n".join(_blocks(txt))
    if os.environ.get("PCBFLOW_FILL_KEYDUMP"):            # debugging a key that will not repeat
        with open(os.environ["PCBFLOW_FILL_KEYDUMP"] + ".%d.txt" % os.getpid(), "w", encoding="utf-8") as fh:
            fh.write(txt)
    h = hashlib.sha256()
    h.update(pcbnew.Version().encode())
    h.update(txt.encode())
    stem = os.path.splitext(board.GetFileName())[0]
    for ext in (".kicad_pro", ".kicad_dru"):
        p = stem + ext
        h.update(ext.encode())
        if os.path.isfile(p):
            h.update(open(p, "rb").read())
    named = _named(zones)
    h.update(repr([n for n, _ in named]).encode())
    return h.hexdigest(), named


def _items(board):
    """{identity: pad or via}: what the filler marks with zone-layer overrides (a pad's
    "zone_layer_connections" -- which inner pours flash it). Identity, not position in
    board order, which moves between runs."""
    out = {}
    for f in board.Footprints():
        for p in f.Pads():
            q = p.GetPosition()
            out["P|%s|%s|%d|%d" % (f.GetReference(), p.GetNumber(), q.x, q.y)] = p
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            q = t.GetPosition()
            out["V|%s|%d|%d" % (t.GetNetname(), q.x, q.y)] = t
    return out


def _grab_over(board):
    rows = []
    for k, it in _items(board).items():
        for L in it.GetLayerSet().CuStack():
            o = int(it.GetZoneLayerOverride(L))
            if o != int(pcbnew.ZLO_NONE):
                rows.append("%s|%d|%d" % (k, L, o))
    return np.array(sorted(rows) or [""], dtype=str)


def _lay_over(board, rows):
    its = _items(board)
    for it in its.values():
        it.ClearZoneLayerOverrides()
    for r in rows:
        if not r:
            continue
        k, L, o = r.rsplit("|", 2)
        its[k].SetZoneLayerOverride(int(L), int(o))


def _grab(named, board):
    arrs = {"overrides": _grab_over(board)}
    for nm, z in named:
        if z.GetIsRuleArea():
            continue                      # keep-outs are never filled: leave them untouched
        arrs["f_%s" % nm] = np.array([int(z.IsFilled())], np.int64)
        for L in z.GetLayerSet().Seq():
            arrs["ff_%s_%d" % (nm, L)] = np.array([int(z.GetFillFlag(L))], np.int64)
            ps = z.GetFilledPolysList(L)
            for o in range(ps.OutlineCount()):
                if ps.HoleCount(o):
                    raise ValueError("unfractured fill")      # never seen: fills come fractured
                ch = ps.Outline(o)
                arrs["%s_%d_%d" % (nm, L, o)] = np.array(
                    [[ch.CPoint(j).x, ch.CPoint(j).y] for j in range(ch.PointCount())], np.int64)
            arrs["n_%s_%d" % (nm, L)] = np.array([ps.OutlineCount()], np.int64)
    return arrs


def _lay(board, named, arrs):
    _lay_over(board, arrs["overrides"])
    for nm, z in named:
        if z.GetIsRuleArea():
            continue
        for L in z.GetLayerSet().Seq():
            n = int(arrs["n_%s_%d" % (nm, L)][0])
            ps = pcbnew.SHAPE_POLY_SET()
            for o in range(n):
                ps.NewOutline()
                for x, y in arrs["%s_%d_%d" % (nm, L, o)]:
                    ps.Append(int(x), int(y))
            z.SetFilledPolysList(L, ps)
            z.SetFillFlag(L, bool(arrs["ff_%s_%d" % (nm, L)][0]))
            z.BuildHashValue(L)
        z.SetIsFilled(bool(arrs["f_%s" % nm][0]))
    board.BuildConnectivity()


def _evict(d):
    fs = [(os.path.getatime(p), os.path.getsize(p), p)
          for p in (os.path.join(d, f) for f in os.listdir(d) if f.endswith(".npz"))]
    tot = sum(s for _, s, _ in fs)
    for _, s, p in sorted(fs):
        if tot <= FILL_CACHE_MB * 1e6:
            break
        try:
            os.remove(p)
            tot -= s
        except OSError:
            pass


def fill(board, zones=None):
    """pcbnew.ZONE_FILLER(board).Fill(zones), reproducible when PCBFLOW_STABLE_FILL=1."""
    zones = list(board.Zones() if zones is None else zones)
    if not ON:
        return pcbnew.ZONE_FILLER(board).Fill(zones)
    key, named = _key(board, zones)
    d = _store()
    path = os.path.join(d, key + ".npz")
    if os.path.isfile(path):
        try:
            with np.load(path) as f:
                arrs = {k: f[k] for k in f.files}
            _lay(board, named, arrs)
            os.utime(path)
            STATS["hit"] += 1
            return True
        except Exception as exc:                            # a bad entry: fill afresh
            print("  stable_fill: cache entry %s unreadable (%r) -- filling" % (key[:12], exc))
    ok = pcbnew.ZONE_FILLER(board).Fill(zones)
    STATS["miss"] += 1
    try:
        tmp = path + ".%d.tmp.npz" % os.getpid()
        np.savez_compressed(tmp, **_grab(named, board))
        os.replace(tmp, path)
        _evict(d)
    except Exception as exc:
        print("  stable_fill: could not store %s (%r)" % (key[:12], exc))
    return ok
