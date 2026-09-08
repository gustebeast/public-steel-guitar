"""Scratch view for THIS project -- renders YOUR portion into YOUR OWN FreeCAD tab.

    py -3.12 cadkit/tools/agent_sync.py view            # the normal way to run this
    py -3.12 -m tools.scratch_view --start              # BEGIN a flow: re-cache, render
    py -3.12 -m tools.scratch_view                      # iterate: your part fresh
    py -3.12 -m tools.scratch_view --merge              # END a flow: DELETE the cache

WHY: a full `src.build` is minutes, and nearly all of it is geometry you are not
touching. This caches the surroundings and rebuilds only the part under work --
measured here at ~14 s per iteration against a ~4 min build.

WHICH PART IS YOURS COMES FROM THE SCOPE REGISTRY, NOT FROM THIS FILE. Claim it once:

    py -3.12 cadkit/tools/agent_sync.py scope --set src.<your_module> [--attr assembly]

That deliberately does NOT live here. This file is TRACKED, so a per-agent config
block would put every agent's "which part am I on" edit on the same three lines --
a guaranteed conflict on every merge request, between two agents who are both
right. The registry is per-worktree state under .git instead (cadkit/agents.py).

The only thing you may need to add here is a POSE or CROP helper, and only if your
part is not authored in global coordinates -- see POSES / CROPS below. Those are
additive, so two agents adding one do not collide.

READ cadkit/scratch.py before trusting the cache. Short version: the LIFECYCLE is
the invalidation strategy (re-cache on --start, delete on --merge, so a cache never
outlives one sitting), and the cache is for the VIEW ONLY -- `src.build` and
tools.check_overlaps never read it, so a drift costs a surprise at merge rather
than a wrong part. Do not "improve" it into something the gate reads.
"""

from __future__ import annotations

import importlib
import pathlib

from cadkit.agents import current_agent, get_scope
from cadkit.scratch import ScratchView, main

ROOT = pathlib.Path(__file__).resolve().parent.parent

SCOPE = get_scope()
if SCOPE is None:
    raise SystemExit(
        f"scratch_view: {current_agent()} has not claimed a portion yet.\n"
        "  py -3.12 cadkit/tools/agent_sync.py scope --set src.<your_module>\n"
        "Then see who owns what with:  agent_sync.py scope")

LIVE_MODULE = SCOPE["module"]
LIVE_ATTR = SCOPE.get("attr", "assembly")
REPLACED = tuple(SCOPE.get("replaced", ()))


# ── optional per-part helpers ────────────────────────────────────────────────
# Only needed when a part is NOT authored in global coordinates, or when you want
# the context cropped to a region. Add yours; a scope opts in with
#   scope --set ... --pose <key> --crop <key>
# and anything unregistered simply gets no pose and the whole instrument.
def _leg_station():
    """The -X/+Y (TRRS) leg station."""
    from src import chassis as CH
    return CH.LEG_STATIONS_X[1], CH.LEG_Y[0], CH.Z_BOT


def _pose_leg_stack(name, wp):
    """leg_stack is authored +Z up from its own base; on the instrument it hangs
    off the chassis bottom, flipped."""
    lx, ly, zt = _leg_station()
    return wp.rotate((0, 0, 0), (1, 0, 0), 180).translate((lx, ly, zt))


POSES = {"leg_stack": _pose_leg_stack}
def _crop_leg_station():
    """400 sq x 900 box round the leg station. Spelled out rather than built by
    tuple concatenation -- the one-liner read `(w,d,h) + station[:2] + (z-300.0)`,
    and that last term is a FLOAT, not a 1-tuple, so it raised the moment anyone
    actually used a crop. Nobody had until now."""
    lx, ly, zt = _leg_station()
    return (400.0, 400.0, 900.0, lx, ly, zt - 300.0)


CROPS = {"leg_station": _crop_leg_station}
# ─────────────────────────────────────────────────────────────────────────────


def _live():
    try:
        mod = importlib.import_module(LIVE_MODULE)
    except ModuleNotFoundError:
        raise SystemExit(
            f"scratch_view: your scope names {LIVE_MODULE!r}, which does not exist.\n"
            "Re-point it with:  agent_sync.py scope --set src.<your_module>")
    try:
        parts = getattr(mod, LIVE_ATTR)()
    except AttributeError:
        raise SystemExit(
            f"scratch_view: {LIVE_MODULE} has no {LIVE_ATTR!r}. Name the callable that\n"
            "returns [(name, Workplane), ...]:  agent_sync.py scope --set "
            f"{LIVE_MODULE} --attr <fn>")
    return [(n, w) for n, w in parts if not n.endswith("_CONTEXT")]


VIEW = ScratchView(
    root=ROOT,
    context=lambda: importlib.import_module("src.build").collect_components(),
    live=_live,
    replaced=REPLACED,
    crop=CROPS[SCOPE["crop"]]() if SCOPE.get("crop") in CROPS else None,
    pose=POSES.get(SCOPE.get("pose")),
    # The LIVE set wears the same colours the full build gives it, so the part under
    # work reads as the material it is instead of one flat highlight. Resolved through
    # src.build._color_for -- the very function the real build uses -- so this view
    # cannot drift from the finished assembly. Cached context stays grey on purpose:
    # that contrast is what tells you which parts are live and which may be stale.
    colors=lambda n: importlib.import_module("src.build")._color_for(n),
)

if __name__ == "__main__":
    raise SystemExit(main(VIEW))
