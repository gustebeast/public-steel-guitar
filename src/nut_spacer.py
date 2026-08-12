"""H-nut mounting spacer (×10) — PETG-GF, a 3-minute part that exists for one reason.

The leadscrew nut is bolted under the carriage through both of its ears. The −X ear
lands on solid material. The +X one does not, and cannot, and that is a printing
constraint rather than a layout one:

The nut's Ø8 boss has to be recessed into the carriage (hanging free it would drive
into the raised-plane drive pulleys), and the recess has to be Y-OPEN, because Ø8.4
inside an 8.8 mm wide part leaves 0.2 mm side walls. A Y-open recess has a ceiling at
its +X end, and the carriage builds −X → +X, so that ceiling must close at 45°. The
closure can only grow DOWNWARD off the body that is already there above the recess —
growing up from the bottom face would drop a floating island into every layer for
7 mm. So the carriage's bottom face simply does not exist between x 4.2 and 11.2, and
the +X ear at x 6.5 stands off it by exactly the ramp's height there.

This packs that gap so the ear clamps against something instead of being pulled up
into thin air and cocking the nut. It is in COMPRESSION only — ~164 N over an 8 mm²
annulus, about 20 MPa, well inside PETG-GF — and it is short and fat, so buckling is
not in the conversation.

Both ears must be tied: the string enters the carriage at the anchor (x +8) and
leaves through the nut on the screw axis (x 0), a standing 1176 N·mm couple. Split
across ears at ±6.5 that is ±90 N. On the −X screw alone it would be 2132 N·mm with
no arm to react it, and the carriage would cock until the screw bore and guide bore
took up their slop — roughly 0.2 mm at the anchor, about 13 cents of pitch.

Height is DERIVED from the carriage's ramp, not written down, because it and the ear
position both hang off NUT_HOLE_DX — which is still a guess until the nut is measured.

Print orientation: bore axis up, flat both ends, ten to a plate.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import carriage as CR
from .helpers import cyl
from cadkit.fasteners import M2

PRINT_UP = (0.0, 0.0, 1.0)

H  = CR.NUT_SPACER_H            # 2.3 — the ramp's height at the +X ear
ID = M2.shaft_clr_d             # 2.4 — the screw spins free through it
OD = ID + 2 * D.MIN_WALL_2P     # 5.6 — two beads of wall all round

assert H > 0.0, "no gap to pack: the +X ear is not over the ramp"


def _build() -> cq.Workplane:
    return cyl(OD, H, z=0.0).cut(cyl(ID, H + 2, z=-1.0))


nut_spacer = _build()
