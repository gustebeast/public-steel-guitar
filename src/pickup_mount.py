"""Pickup carrier hardware — the DEMO pickup body + its mount screws.

The pickup is carried by the swappable PICKUP PIECE in the deck (top_plate.py):
a tray with a FLOOR running under the pickup (material that does the holding,
like the old bar mount, but now riding the SAME rail grooves as the other deck
cover pieces). The pickup rests on the tops of three HEIGHT set-screws threaded
up through the floor (3-point -> sets height + a little tilt), and is pinned in
the X/Y plane by two CLAMP screws through the -Y skirt.

Service flow (all from above, NO plate removal):
  1. loosen the two X/Y clamp screws -> pickup free to slide in the piece
  2. slide the pickup aside (toward +X, off the height screws)
  3. the three height screws are now exposed -> turn them to set the string gap
  4. slide the pickup back over the screws, check the spacing
  5. repeat, then retighten the clamp screws

  X (tone, bridge<->neck): clamp position (fine) + which slots the piece sits in
    (coarse); the clamp travel bridges the 20 mm slot step -> continuous reach.
  Z (string gap): the three height screws, adjustable in place per above.
  Y: centred by the tray skirts + held by the clamp screws.

All screws are the stocked M4 set/button screws (zero new BOM lines).
Frames: pickup centred X/Y, top at z=0 (build.py lifts it to PK_TOP); height
screw vertical, top at z=0; clamp screw axis +Y, shank tip at y=0.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl, cyl_y

# ── the pickup itself (Lace Alumitone ToneBar 10, 3.75") ──────────────────────
# The RECOMMENDED pickup (user). A current-driven BLADE humbucker (no per-string
# poles). The strings FAN: 9.5mm pitch at the changer (STANDARD pedal steel, ~85mm
# field) -> 6.5mm at the nut. The pickup sits near the changer, so the 95mm blade
# fits the ~85mm changer-end field well (NOT oversized -- an earlier note wrongly
# used the 6.5mm nut spacing). It's +Y-referenced (top_plate) to just cover string
# 1 where it crosses the pickup (~+42, string_y(0)), overhanging -Y ~8mm past
# string 10. Depth 22 is deeper than the -14 ribs allow at the neck-slide positions
# -- a known TODO the user will review.
PK_W, PK_L, PK_H = 38.0, 95.0, 22.0            # X (along neck), Y (across strings), Z (height)
PK_H_MIN = 15.0                                 # carrier-wall cap datum: walls stay this far
                                               # above the plate so they never top the pickup
                                               # (< PK_H) even raised -- never foul bar/strings
GAP     = 3.0                                   # pickup top -> heaviest string bottom
PK_TOP  = D.STRING_Z - max(D.STRING_GAUGE) - GAP
PK_BOT  = PK_TOP - PK_H

# ── mount screws (all stocked M4) ────────────────────────────────────────────
HSCREW_D = 4.0                                  # M4 height set-screw
CSCREW_D = 4.0                                  # M4 X/Y clamp screw


def pickup_demo() -> cq.Workplane:
    """Lace Alumitone ToneBar 10 envelope (38 x 95 x 22), centred X/Y, top at z=0."""
    return box_at(PK_W, PK_L, PK_H, z=-PK_H / 2)


def height_screw() -> cq.Workplane:
    """DEMO M4 height set-screw, axis +Z, top at z=0 (the pickup rests here);
    short enough that its base stays above the chassis ribs at z -14."""
    return cyl(HSCREW_D, 4.0, z=-4.0)


def clamp_screw() -> cq.Workplane:
    """DEMO M4x12 button-head X/Y clamp screw, axis +Y: shank tip at y=0."""
    return cyl_y(CSCREW_D, 12.0, y0=0.0).union(cyl_y(7.5, 2.2, y0=12.0))
