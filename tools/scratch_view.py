"""Scratch view for THIS project -- config only; the machinery is cadkit.scratch.

    py -3.12 -m tools.scratch_view --start   # BEGIN a flow: re-cache, then render
    py -3.12 -m tools.scratch_view           # iterate: live part fresh, rest cached
    py -3.12 -m tools.scratch_view --merge   # END a flow: DELETE the cache

WHY: a full `src.build` is minutes, and nearly all of it is geometry you are not
touching. This caches the surroundings and rebuilds only the part under work --
measured here at ~14 s per iteration against a ~4 min build.

TO POINT IT AT YOUR PART, edit the three lines in the CONFIG block below:
LIVE_MODULE, LIVE_ATTR and REPLACED. Nothing else needs changing. If the module
you name does not exist yet, this prints what to do rather than a traceback.

READ cadkit/scratch.py before trusting the cache. Short version: the LIFECYCLE
is the invalidation strategy (re-cache on --start, delete on --merge, so a cache
never outlives one sitting), and the cache is for the VIEW ONLY -- `src.build`
and tools.check_overlaps never read it, so a drift costs a surprise at merge
rather than a wrong part. Do not "improve" it into something the gate reads.
"""

from __future__ import annotations

import importlib
import pathlib

from cadkit.scratch import ScratchView, main

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ── CONFIG: the only part you edit ──────────────────────────────────────────
LIVE_MODULE = "src.leg_stack"      # the module you are working on
LIVE_ATTR = "assembly"             # a callable on it -> [(name, Workplane), ...]
REPLACED = ("leg_", "latch_")      # context parts the live one SUPERSEDES, so the
                                   # old ones are not drawn beside their successor
CROP_SIZE = (400.0, 400.0, 900.0)  # box around the region of interest; None = all
# ────────────────────────────────────────────────────────────────────────────


def _station():
    """The region of interest. Here: the -X/+Y (TRRS) leg station."""
    from src import chassis as CH
    return CH.LEG_STATIONS_X[1], CH.LEG_Y[0], CH.Z_BOT


def _live():
    try:
        mod = importlib.import_module(LIVE_MODULE)
    except ModuleNotFoundError:
        raise SystemExit(
            "scratch_view: LIVE_MODULE %r does not exist.\n"
            "Edit the CONFIG block at the top of tools/scratch_view.py to name\n"
            "the module you are working on." % LIVE_MODULE)
    parts = getattr(mod, LIVE_ATTR)()
    return [(n, w) for n, w in parts if not n.endswith("_CONTEXT")]


def _pose(name, wp):
    """leg_stack is authored +Z up from its own base; the instrument has the body
    at +Z, so it hangs off the chassis bottom, flipped. Drop this (pose=None) if
    your part is already authored in global coordinates."""
    lx, ly, zt = _station()
    return wp.rotate((0, 0, 0), (1, 0, 0), 180).translate((lx, ly, zt))


def _crop():
    if CROP_SIZE is None:
        return None
    lx, ly, zt = _station()
    return CROP_SIZE + (lx, ly, zt - 300.0)


VIEW = ScratchView(
    root=ROOT,
    context=lambda: importlib.import_module("src.build").collect_components(),
    live=_live,
    replaced=REPLACED,
    crop=_crop(),
    pose=_pose,
    # The LIVE set wears the same colours the full build gives it, so the part under
    # work reads as the material it is instead of one flat highlight. Resolved through
    # src.build._color_for -- the very function the real build uses -- so this view
    # cannot drift from the finished assembly. Cached context stays grey on purpose:
    # that contrast is what tells you which parts are live and which may be stale.
    colors=lambda n: importlib.import_module("src.build")._color_for(n),
)

if __name__ == "__main__":
    raise SystemExit(main(VIEW))
