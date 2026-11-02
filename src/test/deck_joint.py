"""Deck joint coupon: slices of the finished rail and deck panel, not a model of them, so the groove,
the tongue, the clearance and both print directions cannot drift from the instrument.

The two joints come in to SPAN (user): the chassis half is a small U, a post of each real rail with a
bar across the bottom, and the panel half is a strip of the real panel with the middle taken out. Only
the span and the wall height change. It proves two joints sliding at once, PCTG tongues in PETG-GF
grooves. It does not prove the real 170.05 span.

    py -3.12 -m src.test.deck_joint
"""
from __future__ import annotations

import sys

from .. import chassis as CH
from .. import dimensions as D
from .. import top_plate as TP
from ..helpers import box_at
from cadkit.step_export import export_step, print_pose

LEN = 40 * D.BEAD                                # 32.0: 5 head widths, 1.6 x the shortest panel
SPAN = 25 * D.BEAD                               # 20.0 rail centre to rail centre
BAR_Z0 = -13 * D.BEAD                            # -10.4 the part's bed
BAR_Z1 = -CH.TP_TG_DEPTH                         # -7.2 the bar's top, under the groove zone
RAIL_X0 = -540.0                                 # both X bands are plain section on the real parts
PANEL_X0 = -330.0
SIDES = ((CH.Y_LO, -1.0), (CH.Y_HI, 1.0))


def chassis():
    """The U: one post of each rail, moved in to SPAN, and the bar joining them."""
    out = box_at(LEN, SPAN, BAR_Z1 - BAR_Z0, x=LEN / 2, y=0.0, z=(BAR_Z0 + BAR_Z1) / 2)
    seg = next(s for s in CH.segments if s.val().BoundingBox().xmin < RAIL_X0 < s.val().BoundingBox().xmax)
    for yc, s in SIDES:
        band = box_at(LEN, CH.T, -BAR_Z0, x=RAIL_X0 + LEN / 2, y=yc, z=BAR_Z0 / 2)
        out = out.union(seg.intersect(band).translate((-RAIL_X0, s * SPAN / 2 - yc, 0.0)))
    return out


def panel():
    """The strip: each edge of the real panel, base and colour as one, moved in to meet at Y 0."""
    i = next(i for i, s in enumerate(TP.segments)
             if s.val().BoundingBox().xmin < PANEL_X0 < s.val().BoundingBox().xmax)
    whole = TP.segments[i].union(TP.segments_color[i])
    bb = whole.val().BoundingBox()
    out = None
    for yc, s in SIDES:
        edge, inner = (bb.ymin, yc + SPAN / 2) if s < 0 else (yc - SPAN / 2, bb.ymax)
        band = box_at(LEN, inner - edge, bb.zlen + 2.0, x=PANEL_X0 + LEN / 2, y=(edge + inner) / 2,
                      z=(bb.zmin + bb.zmax) / 2)
        half = whole.intersect(band).translate((-PANEL_X0, s * SPAN / 2 - yc, 0.0))
        out = half if out is None else out.union(half)
    return out


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    export_step(print_pose(chassis()), out + "/test_deck_joint_chassis.step")
    export_step(print_pose(panel(), "flip"), out + "/test_deck_joint_panel.step")


if __name__ == "__main__":
    main()
