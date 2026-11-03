"""Light window weld coupon: a slice of the real chassis_1, rail + window + body, so the PCTG to PETG-GF
contact is the instrument's own. chassis_1's +Y rail has no PETG-GF path to the body: the weld is all
that holds it until the seams go together.

One STEP, two named bodies, as chassis_1's own file: Bambu loads it as one object; put
test_window_weld on PETG-GF and test_window_weld_light on PCTG, on the 0.8 nozzle. Then look at the window's ends for peeling, and bend the rail
over by hand until something gives. Break in the plastic: the joint holds. A clean peel along the
window's faces: it does not.
Both faces are bricked (chassis.BRICK_*): the clear keys into the opaque, course by course. The
coupon's two cut ends slice through keys, so a little of each end is not the real joint.

    py -3.12 -m src.test.window_weld
"""
from __future__ import annotations

import sys

from .. import chassis as CH
from .. import dimensions as D
from ..helpers import box_at
from cadkit.orientation import PrintOrientation as PO
from cadkit.step_export import export_print_parts

SEG = 1                                          # the section whose rail hangs on the window
LEN = 3 * D.LEVER_PITCH                          # 31.2: whole pitches, so the contact is the real share
X0 = D.lever_wall_x(-320.0)                      # plain band, clear of both seams
Y0 = CH.Y_HI - CH.LIGHT_BAND_DY - 30 * D.BEAD    # 20.0 of body inboard of the window
HIGH = 50 * D.BEAD                               # 40.0 of rail above the bed, the handle


def keep():
    y1 = CH.Y_HI + CH.T / 2 + 1.0
    return box_at(LEN, y1 - Y0, HIGH, x=X0 + LEN / 2, y=(Y0 + y1) / 2, z=CH.Z_BOT + HIGH / 2)


def _posed(w):
    """On the bed in the part's own print direction. Both halves move alike: they are one object."""
    return w.translate((-X0 - LEN / 2, -CH.Y_HI, -CH.Z_BOT))


def opaque():
    return _posed(CH.segments[SEG].intersect(keep()))


def window():
    return _posed(CH.segments_light[SEG].intersect(keep()))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    export_print_parts([("test_window_weld", opaque()), ("test_window_weld_light", window())],
                       PO(None, "chassis_1's own bed face: a slice of it, standing as it prints"),
                       out + "/test_window_weld.step")


if __name__ == "__main__":
    main()
