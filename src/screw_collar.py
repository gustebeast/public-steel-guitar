"""Leadscrew retaining collar (×10) — PETG-GF, the screw's axial anchor.

This is the part that stops the whole instrument's string tension from simply
pulling the ten leadscrews up out of the machine. Load path:

    string → carriage → H-nut → SCREW → **collar** → two MR85 inner rings
           → balls → outer rings → screw-rail ledge → endplate → rails

It replaces a purchased M5 locknut, which was the wrong part twice over: nothing
sold as an M5 nut threads onto a Tr5×1 rod, and the nuts that DO are the same
$6.50 part we are already buying one of per string.

HOW IT GRIPS — a FORMED thread, not a clamp. The bore prints plain at
COLLAR_BORE (4.6, between the Tr5×1 minor 4.0 and major 5.0) and the steel rod
cuts its own mating thread on the way in, the way a self-tapper does. Two things
rule out the alternatives, and both are worth keeping written down:
  • A PRINTED thread is impossible at this pitch. Tr5×1 is a 1 mm pitch, 0.5 mm
    deep form — smaller than one 0.8 mm bead radially AND axially — so the
    slicer would smear it into a smooth bore. (0.2 mm LAYERS do not help: layer
    height buys Z resolution, and the missing resolution here is in XY.)
  • A FRICTION clamp is not trustworthy for a permanent 147 N. Holding that by
    friction needs ~1.8 kN of normal force, which is ~69 MPa of hoop stress in
    the ring — over PETG-GF's tensile strength before creep is even considered,
    and creep is precisely what a static clamp cannot survive.
  The formed thread is a positive form lock instead. It is LENGTH-STARVED at 4.0
  mm — see dimensions.COLLAR_H for the budget it lost to the chassis end block —
  which is ~28 mm² of shear area, 5.2 MPa under 147 N, about 21-26% of PETG-GF's
  interlayer shear. That is inside the usual 25% static-creep guideline but only
  just, and it is the tightest margin in the drivetrain.
  The reason a formed thread is safe here at all and NOT for the carriage
  nut is that the collar never moves relative to the rod, whereas the carriage
  nut slides ~300 m over the instrument's life. That is a wear duty; it gets brass.

Local frame: axis Z, origin on the screw axis, BOSS TOP at z=0 — that is the face
that lands on the bearings' inner rings. Everything hangs -Z from there.

Print orientation: bore axis UP (+Z), flat on the body's bottom face. Every face
is then either vertical or horizontal — no overhang anywhere, and the formed
thread cuts across the layers rather than peeling them.

It ROTATES with the screw (the bearings above it are the stationary interface), so
everything about its shape is governed by the SWEPT circle — see OD below.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, box_at

PRINT_UP = (0.0, 0.0, 1.0)          # bore axis up; flat bottom on the bed

# THE COLLAR TURNS WITH THE SCREW, so its envelope is a SWEPT CIRCLE, not its
# outline. That kills any prismatic body: the first version was a 12.8 x 8.0 block
# with spanner flats, which sweeps Ø20.8 in a 9.5 mm lane and would have milled both
# neighbours on the first move. So the body is a cylinder at OD, and the wrench flats
# are milled into it — the swept circle is the cylinder either way, so the flats are
# free. 8.0 across them is a stock spanner size, which the part needs: seating it is
# four turns of a formed thread, not a push fit.
OD   = D.COLLAR_OD                  # 8.8 — the swept envelope
AF   = D.COLLAR_AF                  # 8.0 across the wrench flats
H    = D.COLLAR_H                   # 4.0 (Z) TOTAL, boss included

# The pilot boss reaches up through the SEAT_CLR slop at the bottom of the rail's
# bearing seat to touch the stack. Ø5.6 is deliberate: it must land on the INNER
# rings only (their OD is ~6.3). A boss wide enough to touch the outer rings would
# drag the stationary race against a rotating collar every time the screw moves.
BOSS_D = D.COLLAR_BOSS_D            # 5.6
BOSS_H = D.COLLAR_BOSS_H            # 0.8

# Wall around the forming bore, measured at the flats (its thinnest). It matters more
# than the load suggests: during forming the rod displaces material outward, and a thin
# ring can split rather than flow.
_WALL = (AF - D.COLLAR_BORE) / 2
assert _WALL >= D.MIN_WALL_2P - 1e-9, (
    f"the collar's wall at the flats is only {_WALL:.2f} (want {D.MIN_WALL_2P}): "
    f"widen COLLAR_AF or narrow COLLAR_BORE")


def _build() -> cq.Workplane:
    body_h = H - BOSS_H
    body = cyl(OD, body_h, z=-H)
    body = body.intersect(box_at(OD + 2, AF, body_h + 2,     # the two wrench flats
                                 x=0, y=0, z=-BOSS_H - body_h / 2))
    body = body.union(cyl(BOSS_D, BOSS_H, z=-BOSS_H))
    # ONE bore, straight through boss and body: the rod threads its own way in
    # from the bottom, so the bore must be the same Ø the whole height.
    return body.cut(cyl(D.COLLAR_BORE, H + 2, z=-H - 1))


screw_collar = _build()
