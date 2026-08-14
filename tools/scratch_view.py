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
LIVE_MODULE = "src.keyhead_endplate"   # the module you are working on
LIVE_ATTR = "keyhead_endplate"         # callable -> [(name, Workplane)], or a bare Workplane
# Context parts the live one SUPERSEDES. Two kinds go in here (user):
#   the PART ITSELF, so the cached copy is not drawn beside its successor; and
#   ALL HARDWARE THAT LIVES INSIDE IT -- the wrap rod, the break dowels, the clamp
#   screws and their inserts, and the strings. Those are what the part is being
#   designed AROUND, so a CACHED one is worse than none: it shows a dowel sitting in
#   a cradle that no longer exists, at a position derived from geometry that has since
#   moved, and it looks exactly as authoritative as the live part beside it.
#
# What the cache IS for is the things this part has to INTERFACE with and which are
# not moving -- the chassis segments, the top panel, the deck. Those stay cached.
REPLACED = ("keyhead_endplate", "nut_wrap_rod", "break_dowel",
            "set_screw", "nut_insert", "string")
CROP_SIZE = (120.0, 140.0, 90.0)       # box around the region of interest; None = all
# ────────────────────────────────────────────────────────────────────────────


def _station():
    """The region of interest. Here: the keyhead nut block -- the break edge (the
    scale "0") at the string plane, which is what the capstan is built around."""
    from src import dimensions as D
    return D.NUT_BLOCK_X, 0.0, D.STRING_Z


def _live():
    try:
        mod = importlib.import_module(LIVE_MODULE)
    except ModuleNotFoundError:
        raise SystemExit(
            "scratch_view: LIVE_MODULE %r does not exist.\n"
            "Edit the CONFIG block at the top of tools/scratch_view.py to name\n"
            "the module you are working on." % LIVE_MODULE)
    attr = getattr(mod, LIVE_ATTR)
    # the attr may be a callable returning [(name, wp), ...] or a bare Workplane
    parts = attr() if callable(attr) else [(LIVE_ATTR, attr)]
    return ([(n, w) for n, w in parts if not n.endswith("_CONTEXT")] + _hardware())


def _hardware():
    """The in-part hardware, REBUILT LIVE beside the endplate rather than cached.

    These are the things the part is designed around -- the wrap rod, the gauged break
    dowels and the strings -- and every one of them is positioned from constants in the
    module under work (nut_block.DOWEL_X, .rod(), .wrap_y()). A CACHED copy would be
    drawn at wherever those constants stood when the cache was made, which is exactly
    the lie the cache is meant not to tell. So they are excluded from the cache (see
    REPLACED) and rebuilt here instead."""
    from src import dimensions as D, nut_block as NB, components as C, build as B
    out = [("nut_wrap_rod", NB.rod().translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z)))]
    for i in range(D.N_STRINGS):
        pin_z = -D.STRING_GAUGE[i] - NB.PIN_D / 2
        out.append((f"break_dowel_{i}", C.dowel().translate(
            (D.NUT_BLOCK_X + NB.DOWEL_X, D.nut_y(i), D.STRING_Z + pin_z))))
        out.append((f"string_{i}", B._string_path(i, D.string_y(i))))
    return out


# keyhead_endplate is authored in GLOBAL coordinates already, so there is no pose
# to apply -- see the ScratchView(pose=None) below.


def _crop():
    if CROP_SIZE is None:
        return None
    lx, ly, zt = _station()
    return CROP_SIZE + (lx, ly, zt)


VIEW = ScratchView(
    root=ROOT,
    context=lambda: importlib.import_module("src.build").collect_components(),
    live=_live,
    replaced=REPLACED,
    crop=_crop(),
    pose=None,
    # The live set wears the SAME colours the full build gives it, so the part under
    # work reads as the material it is instead of one flat highlight. Cached context
    # stays grey -- that contrast is what tells you which is which.
    colors=lambda n: importlib.import_module("src.build")._color_for(n),
)

if __name__ == "__main__":
    raise SystemExit(main(VIEW))
