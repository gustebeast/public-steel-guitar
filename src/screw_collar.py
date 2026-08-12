"""Leadscrew retaining collar (×10) — PCTG at a 0.2 NOZZLE, the screw's axial anchor.

This is the part that stops the whole instrument's string tension from simply
pulling the ten leadscrews up out of the machine. Load path:

    string → carriage → H-nut → SCREW → **collar** → two MR85 inner rings
           → balls → outer rings → screw-rail ledge → endplate → rails

It replaces a purchased M5 locknut, which was the wrong part twice over: nothing
sold as an M5 nut threads onto a Tr5×1 rod, and the nuts that DO are the same
$6.50 part we are already buying one of per string.

HOW IT GRIPS — a PILOT thread that the rod then FORMS to size. The bore prints as a
shallow female helix at the true 1 mm pitch (dimensions.FORM_MINOR/FORM_MAJOR) and
the rod swages the last 0.1 mm of it going in. Three things shaped that, and all
three are worth keeping written down:
  • A FRICTION clamp is not trustworthy for a permanent 147 N. Holding that by
    friction needs ~1.8 kN of normal force, which is ~69 MPa of hoop stress in the
    ring — past the material's tensile strength before creep is even considered,
    and creep is precisely what a static clamp cannot survive.
  • A PLAIN forming bore was the next attempt, and the user called it: a Tr screw
    has blunt 30° flanks and no cutting edges, so it swages rather than cuts, and a
    cylinder gives it nothing to track. Nothing sets the lead and nothing stops it
    starting a turn crooked. The pilot helix is a track it can only follow.
  • THE NOZZLE IS WHAT MAKES THE PILOT POSSIBLE. At the project's 0.8 the 0.3 mm
    groove is under half a bead and the slicer smears it into a smooth bore. At 0.2
    it is a 1.5-bead feature and prints as a thread. So this part declares its own
    finer nozzle, exactly as belt_clamp does for GT2 ridges — and that decides the
    material too, because glass fibre through a 0.2 nozzle is not a thing. PCTG
    instead of PETG-GF costs nothing here (the duty is ~6.5 MPa against ~20-25
    interlayer) and matches the drive pulley, itself a 0.2 print for its GT2 teeth.
  The result is a positive form lock, not friction. It is LENGTH-STARVED at 4.0 mm
  — see dimensions.COLLAR_H for the budget it lost to the chassis end block — which
  is ~28 mm² of shear area at full form and ~80% of that once the pilot's engagement
  is counted: about 6.5 MPa under 147 N, a quarter to a third of interlayer shear.
  Inside the usual 25% static-creep guideline but only just, and it is the tightest
  margin in the drivetrain.
  The reason a formed thread is safe here at all and NOT for the carriage
  nut is that the collar never moves relative to the rod, whereas the carriage
  nut slides ~300 m over the instrument's life. That is a wear duty; it gets brass.

Local frame: axis Z, origin on the screw axis, BOSS TOP at z=0 — that is the face
that lands on the bearings' inner rings. Everything hangs -Z from there.

Print orientation: bore axis UP (+Z), flat on the body's bottom face. Every face is
then either vertical or horizontal — the pilot thread's 45° flanks are
self-supporting inside the bore, and the formed thread's load runs across the layers
rather than peeling them.

It ROTATES with the screw (the bearings above it are the stationary interface), so
everything about its shape is governed by the SWEPT circle — see OD below.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, box_at
from cadkit.threads import threaded_rod

PRINT_UP = (0.0, 0.0, 1.0)          # bore axis up; flat bottom on the bed
# PER-PART NOZZLE (the dimensions.py idiom, as belt_clamp does for GT2 ridges): the
# pilot thread's groove is 0.3 mm deep, which 0.8 cannot resolve. 0.2 makes it a
# 1.5-bead feature. The unfilled material follows from the nozzle, not the reverse.
NOZZLE_D = 0.2
B        = NOZZLE_D

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

# Wall around the bore, measured at the flats AND over the thread groove — the two
# thinnest things at once. It matters more than the load suggests: forming displaces
# material outward, and a thin ring can split rather than flow.
_WALL = (AF - D.FORM_MAJOR) / 2
assert _WALL >= D.MIN_WALL_2P - 1e-9, (
    f"the collar's wall at the flats is only {_WALL:.2f} (want {D.MIN_WALL_2P}): "
    f"widen COLLAR_AF or narrow COLLAR_BORE")


LEAD_IN = 2 * B                     # 0.4 of 45° countersink at each end of the bore
# Two cadkit.threads defaults are tuned for a male rod and are wrong for a nut cutter,
# so both are overridden (and both are now parameters there because of this part):
#   overshoot  costs 2x itself out of every pitch. At 1.0 the 0.3 default makes EVERY
#              depth illegal — it is why this thread could not be built at all at first.
#              Cutting into solid stock, there is no coincident face to avoid.
#   bevel_ends tapers the cutter's ends down to the MINOR Ø, which would leave this
#              bore's entry a plain Ø4.2 hole the rod's Ø5.0 crest cannot even enter.
_CUT_OVERSHOOT = 0.05
_CUT_LEN = int(H + BOSS_H + 2)                      # whole turns: the pitch is 1.0


def _cone(d_bottom, d_top, h, z):
    return cq.Workplane("XY").add(
        cq.Solid.makeCone(d_bottom / 2.0, d_top / 2.0, h,
                          cq.Vector(0, 0, z), cq.Vector(0, 0, 1)))


def _build() -> cq.Workplane:
    body_h = H - BOSS_H
    body = cyl(OD, body_h, z=-H)
    body = body.intersect(box_at(OD + 2, AF, body_h + 2,     # the two wrench flats
                                 x=0, y=0, z=-BOSS_H - body_h / 2))
    body = body.union(cyl(BOSS_D, BOSS_H, z=-BOSS_H))
    # ONE pilot thread, straight through boss and body — the same Ø the whole height,
    # so the rod is guided over its full engagement and not just at the entry.
    body = body.cut(threaded_rod(D.FORM_MINOR, D.FORM_MAJOR, D.SCREW_PITCH, _CUT_LEN,
                                 z=-H - 1, overshoot=_CUT_OVERSHOOT,
                                 bevel_ends=False), clean=False)
    # LEAD-IN at BOTH ends: a 45° countersink so the rod meets the helix square rather
    # than on whatever face it happens to touch first. Both, because nothing about the
    # part tells you which way up it goes on.
    for zc, d0, d1 in ((-H - 0.01, D.FORM_MAJOR + 2 * LEAD_IN, D.FORM_MAJOR),
                       (BOSS_H - LEAD_IN, D.FORM_MAJOR, D.FORM_MAJOR + 2 * LEAD_IN)):
        body = body.cut(_cone(d0, d1, LEAD_IN + 0.01, zc), clean=False)
    return body


screw_collar = _build()
