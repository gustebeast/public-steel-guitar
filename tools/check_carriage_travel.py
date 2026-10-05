"""Does every string's carriage reach its whole travel without touching anything?

    py -3.12 -m tools.check_carriage_travel

check_overlaps compares parts WHERE THEY ARE DRAWN, and the assembly is drawn as it is
assembled: every nut on the ceiling, every belt clamp where it is spliced (user,
2026-10-05). Everything below the ceiling is invisible to it. This is check_sweep's idea
for parts that slide: for each of the ten strings the MOVING SET is posed at STATIONS
stations from the ceiling to the floor and intersected with everything that is not it.

  moving   nut_i (the carriage), string_nut_i (the ball end under its ear), string_i
           (redrawn at each station: its rise changes with the anchor), and the four
           parts of belt_tensioner_*_i, carried BELT_PER_MM along the belt per mm of nut
           and turned with it -- src.build.clamp_location, the same placement the build
           draws and tools/clamp_range.py steps.
  fixed    every other component as drawn, the other nine strings' moving sets included
           (at the ceiling; clamp against clamp at EVERY pair of positions, and clamps
           against belts, are tools/clamp_range.py's job).

A contact counts when check_overlaps would count it: its own allow-list (`intended`) and
volume floor are used, and belts are left out as its default gate leaves them out.
Baseline is 0.

COST. The first version added nine minutes to a build. Three things keep it short:
  * the STRING is redrawn only as its RISE, ball end to the bridge bearing
    (build._string_path(rise_only=True)). The wrap and the whole speaking length do not
    move with the nut, cost the most to draw, and have a bounding box the length of the
    instrument, which put every fret and LED in reach;
  * every pair is bounding-box filtered and allow-listed BEFORE any boolean, and what is
    left goes to cadkit.overlap_check's worker pool;
  * results are cached by the two solids' BRep fingerprints (.carriage-travel-cache.json),
    so a build that did not touch the drivetrain re-booleans nothing."""
from __future__ import annotations

import pathlib
import sys
import time

STATIONS = 5        # ceiling, floor and three between
SKIP_BASE = {"belt", "belt_clamp"}
CACHE = str(pathlib.Path(__file__).resolve().parent.parent / ".carriage-travel-cache.json")


def _moving_string(i, down):
    """The part of string i that moves, with the nut `down` below the ceiling: its rise,
    ball end to the bridge bearing, from the build's own string path."""
    from src import build as B, dimensions as D
    B.DEMO_POSE_DZ[i] = -down
    try:
        return B._string_path(i, D.string_y(i), rise_only=True).val()
    finally:
        B.DEMO_POSE_DZ.pop(i, None)


def gate(comps, quiet=False, jobs=None, cache=CACHE) -> int:
    """Number of (moving, fixed) pairs that touch somewhere in a travel; 0 is clean.
    ``comps`` is [(name, solid)] -- src.build hands over the model it just built."""
    import concurrent.futures as cf
    import multiprocessing as mp
    import os
    import tempfile
    from cadkit import overlap_check as OC
    from src import build as B, dimensions as D, belt_tensioner as BTn
    from tools import check_overlaps as CO
    t0 = time.perf_counter()
    if CO.WIRE_OK is None:
        import src.wiring
        CO.WIRE_OK = src.wiring.WIRE_OK
    parts = {n: s for n, s in comps}
    fixed = [(n, s, s.BoundingBox()) for n, s in comps if CO.base(n) not in SKIP_BASE]
    t_box = time.perf_counter() - t0
    clamp = [(n, w.val()) for n, w in BTn.clamp_components()]
    downs = [D.CARRIAGE_TRAVEL * k / (STATIONS - 1) for k in range(STATIONS)]
    saved = dict(B.DEMO_POSE_DZ)
    shapes, index, cands = [], {}, []      # every solid in a candidate pair, once

    def slot(key, shape):
        if key not in index:
            index[key] = len(shapes)
            shapes.append(shape)
        return index[key]

    try:
        for i in range(D.N_STRINGS):
            mine = {"nut_%d" % i, "string_nut_%d" % i, "string_%d" % i} | {
                "%s_%d" % (n, i) for n, _s in clamp}
            missing = [n for n in ("nut_%d" % i, "string_nut_%d" % i) if n not in parts]
            if missing:
                raise KeyError("not in the assembly: %s" % ", ".join(missing))
            for k, down in enumerate(downs):
                moving = [(n, parts[n].translate((0.0, 0.0, -down)))
                          for n in ("nut_%d" % i, "string_nut_%d" % i)]
                if "string_%d" % i in parts:
                    moving.append(("string_%d" % i, _moving_string(i, down)))
                loc = B.clamp_location(i, down)
                moving += [("%s_%d" % (n, i), s.moved(loc)) for n, s in clamp]
                for mn, ms in moving:
                    mb = ms.BoundingBox()
                    for fn, fs, fb in fixed:
                        if fn in mine or not OC.bbox_overlap(mb, fb) or CO.intended(mn, fn):
                            continue
                        cands.append((slot((mn, k), ms), slot(fn, fs), mn, fn, down))
    finally:
        B.DEMO_POSE_DZ.clear()
        B.DEMO_POSE_DZ.update(saved)

    t_pose = time.perf_counter() - t0 - t_box
    OC._canonical(shapes)
    fps = [OC.fingerprint(s) for s in shapes]
    cached, last_run = OC._cache_load(cache) if cache else ({}, 0)
    vols, todo = {}, []
    for a, b, _mn, _fn, _d in cands:
        if (a, b) in vols:
            continue
        hit = cached.get(OC._cache_key(fps[a], fps[b]))
        if hit is not None:
            vols[(a, b)] = hit[0]
        else:
            vols[(a, b)] = None
            todo.append((a, b))
    t_fp = time.perf_counter() - t0 - t_box - t_pose
    jobs = OC.default_jobs() if jobs is None else jobs
    if todo and jobs <= 1:
        for a, b in todo:
            vols[(a, b)] = OC.common_volume(shapes[a], shapes[b])
    elif todo:
        fd, path = tempfile.mkstemp(suffix=".bin", prefix="carriage_")
        os.close(fd)
        try:
            OC._serialize(shapes, path)
            with OC._detached_main(), cf.ProcessPoolExecutor(
                    jobs, mp_context=mp.get_context(),
                    initializer=OC._worker_load, initargs=(path, CO.MIN_VOL)) as ex:
                futs = {ex.submit(OC._pair_vol, ab): ab for ab in todo}
                for fut in cf.as_completed(futs):
                    try:
                        vols[futs[fut]] = fut.result()[0]
                    except Exception:                  # a dead worker: an UNKNOWN, not a pass
                        vols[futs[fut]] = float("nan")
        finally:
            os.remove(path)
    if cache:
        OC._cache_save(cache, cached, {OC._cache_key(fps[a], fps[b]): v
                                       for (a, b), v in vols.items() if v is not None and v == v},
                       last_run + 1)
    bad = {}
    for a, b, mn, fn, down in cands:
        v = vols[(a, b)]
        if v != v or v > CO.MIN_VOL:                   # NaN counts against the gate
            w, d0 = bad.get((mn, fn), (0.0, down))
            bad[(mn, fn)] = (max(w, v) if v == v else float("nan"), min(d0, down))
    gate.last = dict(seconds=time.perf_counter() - t0, pairs=len(vols), computed=len(todo),
                     boxes=t_box, posing=t_pose, fingerprints=t_fp)
    if not quiet:
        print("check_carriage_travel: %d strings x %d stations, nut 0 .. %.2f mm below the "
              "ceiling; %d pair(s) in reach, %d computed, %.1fs"
              % (D.N_STRINGS, STATIONS, D.CARRIAGE_TRAVEL, len(vols), len(todo),
                 gate.last["seconds"]))
        if not bad:
            print("clean: every nut, ball end, string and belt clamp clears everything "
                  "through its whole travel.")
        for (m, f), (v, d0) in sorted(bad.items()):
            print("  %-28s meets %-26s from %.2f mm down (%s mm3 worst)"
                  % (m, f, d0, "NOT CHECKED" if v != v else "%.2f" % v))
    return len(bad)


gate.last = {}


def main() -> int:
    from src import build as B
    comps = [(n, o.val() if hasattr(o, "val") else o) for n, o in B.collect_components()]
    try:
        return 1 if gate(comps) else 0
    except KeyError as e:
        print("check_carriage_travel: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
