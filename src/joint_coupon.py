"""Print coupon for the cadkit octagon ("stop-sign") slide joint — the joint the
knee levers use to key into the body.

Two small blocks, both printed -Z→+Z (the real lever/body orientation): one
grows the octagon TENON standing up, the other carries the MORTISE slot. Print
both, slide them together along X, and check the fit + that the mortise roof
bridged cleanly. It calls the SAME library functions the levers use
(`cadkit.joinery.octagon_*`) at the SAME nozzle/span — never re-models the joint,
so the coupon can't drift from the real geometry.
"""

import cadquery as cq

from cadkit.joinery import octagon_tenon, octagon_mortise, octagon_height

NOZZLE = 0.8          # pedal-steel nozzle
WIDTH  = 6.0          # flat-to-flat room (well above the ~1.93 mm floor)
LENGTH = 14.0         # slide / engagement depth along X (the real load path)
CLR    = 0.1          # mortise↔tenon fit clearance (tenon is shrunk by this)
PLATE  = 4.0          # coupon base-plate / floor thickness
CEIL   = 2.0          # mortise ceiling over the roof = the printed bridge
MARGIN = 6.0          # material each side of the joint in Y

_H = octagon_height(WIDTH, NOZZLE)   # mortise depth above the mating plane


def tenon_coupon():
    """Base plate with the octagon tenon standing up (+z). Prints -Z→+Z: plate,
    then stem, then the 45° flare, narrowing to the roof."""
    plate = (cq.Workplane("XY")
             .box(LENGTH, WIDTH + 2 * MARGIN, PLATE, centered=(True, True, False))
             .translate((0, 0, -PLATE)))                       # z -PLATE..0
    ten = octagon_tenon(WIDTH, LENGTH, nozzle=NOZZLE, clearance=CLR).translate((-LENGTH / 2.0, 0, 0))
    return plate.union(ten)


def mortise_coupon():
    """Block with the octagon mortise as a through-slot along X. Prints -Z→+Z; the
    thin ceiling over the slot is the one-nozzle bridge the shape is designed for."""
    block = (cq.Workplane("XY")
             .box(LENGTH, WIDTH + 2 * MARGIN, _H + PLATE + CEIL, centered=(True, True, False))
             .translate((0, 0, -PLATE)))                        # z -PLATE.._H+CEIL (ceiling = bridge)
    cut = (octagon_mortise(WIDTH, LENGTH + 2, nozzle=NOZZLE, clearance=CLR, drop=PLATE)
           .translate((-(LENGTH + 2) / 2.0, 0, 0)))             # slot open both X ends
    return block.cut(cut)
