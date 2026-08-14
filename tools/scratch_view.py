"""Scratch view: rebuild the part you are WORKING on, against CACHED surroundings.

  py -3.12 -m tools.scratch_view --start      # BEGIN a flow: re-cache, then render
  py -3.12 -m tools.scratch_view              # iterate: leg fresh, context cached
  py -3.12 -m tools.scratch_view --merge      # END a flow: DELETE the cache

WHAT THIS IS FOR (user): a fast inner loop. You iterate against cached context,
then "merge" into the real build and deal with whatever crops up. The cache is
never a source of truth and nothing ships from it.

WHY THAT FRAMING MAKES IT SAFE. A stale cache is silently wrong -- a part that
should have changed but did not looks exactly like a correct build, and you then
design against a lie. This codebase has been bitten by that three times
recently (latch.OCT_TOP frozen after the leg grew, knee_lever.MOUNT_X pointing
at a rib that had moved, a dovetail guard asserting an old SQ_W/2). Caching
GEOMETRY invites more of it. What makes it acceptable here is that the cache is
scoped to the VIEW: the canonical `py -3.12 -m src.build` and the overlap gate
never read it, so a drift costs a surprise at merge, not a bad part.

THE LIFECYCLE IS WHAT MAKES IT SAFE (user), more than any hashing scheme would:

    --start   rebuild the cache from scratch, every time a flow BEGINS
    (iterate) the part under work is rebuilt fresh each run; context is cached
    --merge   DELETE the cache, every time you merge back to the real build

so a cache never outlives one iteration session. That beats trying to invalidate
on a dependency hash -- which is the approach that looks rigorous and then misses
the one edge (a constant read through two modules) that matters. Here staleness
is bounded by the length of a sitting, not by the correctness of a hash.

Three rules follow, and they are the whole design:
  * THE PART UNDER WORK IS NEVER CACHED. Only the surroundings are.
  * NO CACHE, NO RENDER. Running without one is an error telling you to --start,
    rather than a silent auto-build that quietly begins an unbounded flow.
  * IT SAYS SO, LOUDLY, every run -- the cache's age and what is in it. A silent
    cache is the dangerous kind.

Complements tools/fast_build.py, which speeds up a single PART with no geometry
cache at all. Use that when you want one STEP; use this when you want to see
your part IN CONTEXT.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import time

import cadquery as cq

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / ".scratch_cache"

# The surroundings worth showing around a leg. Prefixes, matched against the
# names src.build.collect_components() hands out.
CONTEXT = ("chassis", "pedal_bar_")

# Everything is cropped to this box around the leg station -- the full chassis is
# 645 mm of geometry nobody is looking at, and the STEP is what the viewer has to
# chew through.
CROP = (400.0, 400.0, 900.0)


def _station():
    from src import chassis as CH
    return CH.LEG_STATIONS_X[1], CH.LEG_Y[0], CH.Z_BOT


def build_cache():
    """Import the heavy build ONCE, crop the context, write it as BREP."""
    from src import build
    from src.helpers import box_at
    lx, ly, zt = _station()
    crop = box_at(CROP[0], CROP[1], CROP[2], x=lx, y=ly, z=zt - CROP[2] / 3)
    CACHE.mkdir(exist_ok=True)
    n = 0
    t0 = time.time()
    for name, wp in build.collect_components():
        if not name.startswith(CONTEXT):
            continue
        cut = wp.intersect(crop)
        if not cut.solids().vals():
            continue
        cut.val().exportBrep(str(CACHE / (name + ".brep")))
        n += 1
    (CACHE / "STAMP").write_text(str(time.time()))
    print("cached %d context solids in %.0fs" % (n, time.time() - t0))


def load_cache():
    if not (CACHE / "STAMP").exists():
        return None
    age = time.time() - float((CACHE / "STAMP").read_text())
    out = []
    for f in sorted(CACHE.glob("*.brep")):
        out.append((f.stem, cq.Workplane("XY").add(cq.Shape.importBrep(str(f)))))
    return age, out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", action="store_true",
                    help="begin a flow: rebuild the cache from scratch, then render")
    ap.add_argument("--merge", action="store_true",
                    help="end a flow: delete the cache (then run src.build for real)")
    a = ap.parse_args()

    if a.merge:
        shutil.rmtree(CACHE, ignore_errors=True)
        print("cache DELETED -- merge back with:  py -3.12 -m src.build")
        print("                then gate with:    py -3.12 -m tools.check_overlaps")
        return 0
    if a.start:
        shutil.rmtree(CACHE, ignore_errors=True)
        build_cache()
    elif not (CACHE / "STAMP").exists():
        print("no cache -- start a flow with:  py -3.12 -m tools.scratch_view --start")
        return 1

    from src import leg_stack as LS
    lx, ly, zt = _station()

    got = load_cache()
    age, ctx = got
    # LOUD, every run: the whole risk of a geometry cache is not knowing you are
    # on one. Age in minutes is the number that tells you whether to --refresh.
    print("=" * 68)
    print(" SCRATCH VIEW -- leg_stack is FRESH; %d context solids are CACHED"
          % len(ctx))
    print(" cache age: %.0f min   (--start to re-cache | --merge to end the flow)"
          % (age / 60.0))
    print("=" * 68)

    asm = cq.Assembly()
    for name, wp in LS.assembly():
        if name.endswith("_CONTEXT"):
            continue                       # real cached geometry replaces these
        # the leg is authored +Z up from its adapter; the instrument has the body
        # at +Z and the bar at -Z, so it hangs off the chassis bottom flipped
        posed = wp.rotate((0, 0, 0), (1, 0, 0), 180).translate((lx, ly, zt))
        asm.add(posed, name=name, color=cq.Color(0.85, 0.45, 0.20))
    for name, wp in ctx:
        asm.add(wp, name="cached_" + name, color=cq.Color(0.32, 0.36, 0.40))

    out = ROOT / "assembly.step"
    asm.save(str(out), exportType="STEP")
    print("wrote %s (%.0f KB)" % (out.name, out.stat().st_size / 1024))
    from cadkit.freecad import show
    show(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
