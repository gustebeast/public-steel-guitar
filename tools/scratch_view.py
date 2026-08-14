"""Scratch view for THIS project -- config only; the machinery is cadkit.scratch.

  py -3.12 -m tools.scratch_view --start      # BEGIN a flow: re-cache, then render
  py -3.12 -m tools.scratch_view              # iterate: live part fresh, rest cached
  py -3.12 -m tools.scratch_view --merge      # END a flow: DELETE the cache

Read cadkit/scratch.py for why a geometry cache is safe here (short version: the
LIFECYCLE is the invalidation strategy, and the cache is for the VIEW only --
`py -3.12 -m src.build` and tools.check_overlaps never read it).

POINT IT AT WHAT YOU ARE WORKING ON by editing LIVE/REPLACED below. Right now
that is the redesigned leg (src.leg_stack), which supersedes the old leg_* and
latch_* parts, so they are left out of the context rather than drawn alongside
their own replacement.
"""

from __future__ import annotations

import pathlib

from cadkit.scratch import ScratchView, main

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _station():
    from src import chassis as CH
    return CH.LEG_STATIONS_X[1], CH.LEG_Y[0], CH.Z_BOT


def _live():
    """What gets rebuilt FRESH every iteration.

    The pedal bar is in here as well as the leg (user): the mechanism joining the
    adjustable floating tenon to the bar still has to be designed, so caching the
    bar would freeze exactly the thing being changed. Anything you are editing
    belongs on this side; the cache is only for scenery."""
    from src import leg_stack as LS, pedal_bar as PB
    out = [(n, w) for n, w in LS.assembly() if not n.endswith("_CONTEXT")]
    out += [(n, w) for n, w in PB.assembly_parts()]
    return out


def _pose(name, wp):
    """Only leg_stack needs posing -- the bar is already in global coordinates.

    leg_stack is authored +Z up from its adapter; the instrument has the body
    at +Z and the bar at -Z, so it hangs off the chassis bottom, flipped."""
    if not name.startswith(("body_adapter", "fixed_", "adjust_")):
        return wp                       # already global (the pedal bar)
    lx, ly, zt = _station()
    return wp.rotate((0, 0, 0), (1, 0, 0), 180).translate((lx, ly, zt))


def _crop():
    # a box round the leg station: the chassis is 645 mm of geometry nobody is
    # looking at, and the STEP size is what the viewer has to chew through
    lx, ly, zt = _station()
    return (400.0, 400.0, 900.0, lx, ly, zt - 300.0)


VIEW = ScratchView(
    root=ROOT,
    context=lambda: __import__("src.build", fromlist=["e"]).collect_components(),
    live=_live,
    replaced=("leg_", "latch_", "pedal_bar", "pedal_"),
    crop=_crop(),
    pose=_pose,
)

if __name__ == "__main__":
    raise SystemExit(main(VIEW))
