"""THE KEYHEAD'S BASS-STACK ROOF, OPEN -- ON TRIAL, NOT IN THE INSTRUMENT.

The roof over a nut slide insert's pocket is a flat bridge (nut_block._roof_cutter). Over
one pocket it is 1.5 across; over the bass stack (strings 8-10, one roof) it is 18.3,
standing on the tips of two 45 degree ramps, and on the bench it printed as spaghetti
(user, 2026-10-13). The trial: a group whose flat would be wider than BRIDGE_MAX gets NO
flat -- its two ramps stay, each stopping two beads short of the wall's +X face and running
out straight (so the lip ends square, not in a knife), and the gap between them runs open
through the wall. The roof also tied the stack's outer wall to the rest of the comb, so
that wall goes from two beads to four (keyhead_endplate.HS_Y0).

The user asked to see it beside the lead's keyhead and has not decided, so it lives here,
where nothing printed reads it: the scratch tab shows `keyhead()` in place of the real
part, and the stack fit finder cuts its slot with `roof_cutter`. If it is approved, these
lines move into nut_block and keyhead_endplate as their own change.
"""
from __future__ import annotations

import pathlib
import types

import cadquery as cq

from src import dimensions as D
from src import nut_block as NB

BRIDGE_MAX = 8 * D.BEAD                 # the widest roof flat left in


def roof_open(lo: float, hi: float) -> bool:
    """Whether the roof over lo..hi would bridge further than BRIDGE_MAX, and so is left out."""
    return (hi - lo) - 2 * NB.HS_ROOF_T > BRIDGE_MAX + 1e-9


def roof_cutter(lo: float, hi: float, c: float, z_top: float) -> cq.Workplane:
    """nut_block._roof_cutter, with the too-wide roof left open between its two ramps."""
    if not roof_open(lo, hi):
        return NB._roof_cutter(lo, hi, c, z_top)
    x0 = NB.INS_X1 + c                              # the pockets' +X face: where the ramp starts
    d = (NB.HS_POCKET_X1 + D.MIN_WALL_2P) - x0      # the wall's whole depth past the pockets
    r = d - D.MIN_WALL_2P                           # the ramp's run, and its rise
    assert r > 0 and hi - lo > 2 * r + BRIDGE_MAX, "no opening left between the ramps"
    pts = [(x0 - 0.5, lo), (x0, lo), (x0 + r, lo + r), (x0 + d + 1.0, lo + r),
           (x0 + d + 1.0, hi - r), (x0 + r, hi - r), (x0, hi), (x0 - 0.5, hi)]
    return (cq.Workplane("XY").polyline(pts).close()
            .extrude(z_top - NB.HS_FLOOR).translate((0, 0, NB.HS_FLOOR)))


_WALL = "HS_Y0, HS_Y1 = NB._INS_LO - D.MIN_WALL_2P, NB._INS_HI + D.MIN_WALL_2P"


def keyhead():
    """The keyhead endplate as the trial draws it: keyhead_endplate's own source, run again
    with the stack's outer wall doubled and nut_block's roof cutter swapped for the one
    above while it builds."""
    src = (pathlib.Path(NB.__file__).parent / "keyhead_endplate.py").read_text(encoding="utf-8")
    assert src.count(_WALL) == 1, "keyhead_endplate's wall line moved: re-point the trial"
    src = src.replace(_WALL, _WALL.replace("NB._INS_LO - D.MIN_WALL_2P", "NB._INS_LO - 2 * D.MIN_WALL_2P"))
    mod = types.ModuleType("src.keyhead_endplate_trial")
    mod.__file__, mod.__package__ = NB.__file__, "src"
    real = NB._roof_cutter
    NB._roof_cutter = lambda lo, hi, c, z: (roof_cutter if roof_open(lo, hi) else real)(lo, hi, c, z)
    try:
        exec(compile(src, "keyhead_endplate.py (roof trial)", "exec"), mod.__dict__)
    finally:
        NB._roof_cutter = real
    return mod.keyhead_endplate
