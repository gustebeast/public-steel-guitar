"""WALL BARS: the two steel flat bars that stiffen the side walls, and their length shims.

WHAT (user, 2026-11-06). The bench build detunes badly when the body is bowed by hand: two printed
walls cannot hold pitch however they are joined. Each side rail now carries a 5/8 x 2 in A-36
hot-rolled flat bar (dimensions BAR_*, prices.json wall_bar_a36_58x2) on edge in a channel down its
middle, from a pocket in the keyhead to a pocket in the bridge endplate. Bought parts, modelled
whole: the overlap gate sees them like any other part.

INSTALL: the chassis sections go together first; each bar slides into its rail's channel from
either end; the endplates then slide on along X over the bars' ends (chassis.bar_pocket), so the
steel ends up fully enclosed.

THE BAR IS LOOSE IN X ON PURPOSE. The endplates seat on the rail ends (chassis.ep_pad), so the scale
length never depends on how long a piece of steel was cut. The bar bears on the keyhead's pocket
floor, and the bridge pocket runs BAR_L_TOL past it (pre-cut is +1/8 in, -0). Printed SHIMS fill
what the measured bar leaves, so it cannot rattle: SHIM_SET per bar stacks to any 0.4 step from 0
to 4.4. The model carries the nominal bar, so it shows the stack that bar needs (1.6 + 1.6, 0.4 of
air left at the floor).

ZINC (user): cold-galvanizing spray, every face and both cut ends, cured before it goes in. The
channel's BAR_CLR is per side over the bar as measured, so the coating has room.
"""
from __future__ import annotations

import cadquery as cq

from . import chassis as CH
from . import dimensions as D
from .helpers import box_at

SHIM_SET = (0.4, 0.8, 1.6, 1.6)          # per bar: any 0.4 step 0 .. 4.4
SHIM_NOMINAL = (1.6, 1.6)                # what the model's nominal bar takes
# a shim fills the pocket's section less the bar's clearance, so it goes in as easily as the bar
SHIM_T, SHIM_W = D.BAR_T, D.BAR_W
SHIM_UP = (1.0, 0.0, 0.0)                # printed flat: its thickness is world X
BAR_ZC = (CH.BAR_Z0 + CH.BAR_Z1) / 2.0   # centred in the channel (it rests on the floor in life)
_AIR = (CH.BAR_POCKET_X1 - CH.BAR_X1) - sum(SHIM_NOMINAL)
assert 0.0 < _AIR <= 0.4 + 1e-9, "the nominal shim stack leaves %.2f at the bridge pocket's floor" % _AIR


def bar(yc):
    """The steel bar in rail `yc`, at its nominal length."""
    return box_at(D.BAR_L, D.BAR_T, D.BAR_W, x=(CH.BAR_X0 + CH.BAR_X1) / 2.0, y=yc, z=BAR_ZC)


def shim(t, x0, yc):
    """A shim `t` thick from x0 (+X), in rail `yc`."""
    return box_at(t, SHIM_T, SHIM_W, x=x0 + t / 2.0, y=yc, z=BAR_ZC)


def components():
    """The two bars and the nominal shim stack behind each, in the bridge pocket."""
    out = []
    for k, yc in enumerate((CH.Y_HI, CH.Y_LO)):
        out.append((f"wall_bar_{k}", bar(yc)))
        x = CH.BAR_X1
        for j, t in enumerate(SHIM_NOMINAL):
            out.append((f"bar_shim_{k}_{j}", shim(t, x, yc)))
            x += t
    return out


def shim_print_set():
    """One bar's SHIM_SET laid out side by side on the bed (thickness up), for the STEP."""
    out, y = None, 0.0
    for t in SHIM_SET:
        s = box_at(SHIM_W, SHIM_T, t, x=0.0, y=y, z=t / 2.0)
        out = s if out is None else out.union(s)
        y += SHIM_T + 4.0
    return out
