"""Carriage (×10) — PA6-GF, load-critical (§8 item 1).

The moving element, riding a VERTICAL leadscrew (axis Z) — it travels in Z. It
presses the round nut into its pocket, rides the guide rod (anti-rotation), and
anchors the string ball-end directly under the bridge bearing, reaching +X over
the screw to do so. Tension path: string → carriage → nut → screw → support brg.

Local frame: origin on the SCREW axis (axis Z). The nut presses in from below;
the string ball-end anchor is at X=+ANCHOR_DX (under the bridge bearing),
opening +Z so the string runs up to it. The guide bore lives in a low FOOT
(column + leg hanging below the plate at the +X end): the rod sits below the
stringing window, so the window stays clear, and the foot's top/bottom faces
are the hard-stop contacts against the endplate's two guide ledges.

Print orientation: the string-tension axis is Z; lay the part so that runs along
the layer lines.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, box_at

THICK   = 12.0                              # Z height
WIDTH   = D.NUT_OD + 2 * 1.0               # across (Y), ≤ string pitch
NUT_POCKET_D = D.NUT_OD + 0.2
X_LO    = -(NUT_POCKET_D / 2 + 2.0)        # wall past the nut pocket (−X)
X_HI    = D.ANCHOR_DX + 2.9                # ONE flush +X face for plate, post and
                                           # column: 0.5 clear of the endplate's stop
                                           # bar (X ≥ +3.4) and clear of the dropping
                                           # rod's install path (rod −X edge +3.15)
BODY_X  = X_HI - X_LO
BODY_XC = (X_HI + X_LO) / 2

# Guide foot: a thick column straight down the flush +X face, then a leg whose
# +X-open yoke slot rides the rod (nested against the cap face). Foot top =
# D.GUIDE_FOOT_DZ (the top-stop face against the endplate's stop stub).
COL_X0, COL_X1   = 4.5, X_HI               # column: clear of the screw bore; flush face
FOOT_X0, FOOT_X1 = 6.5, 13.5               # leg: −X face clears the belt wrap, +X
                                           # face stops 0.5 shy of the cap face
SCREW_CLR_D  = D.SCREW_OD + 1.0
GUIDE_CLR_D  = D.GUIDE_ROD_D + D.FIT_CLR
# +Z hole the string exits through — must clear the heaviest string (C6 .070 ≈ 1.8 mm)
# and leave room to bend it in. Still < the Ø3.5 nut, so the nut is captured.
STRING_SLOT_W = 2.6
STRING_SLOT_Y = 4.0                        # slot length along Y (< the 6 mm nut → captured)
ANCHOR_POST_H = 7.0                        # post above the body: top 1 mm under the bearings
POST_Z1  = THICK / 2 + ANCHOR_POST_H       # post top (+13)
ROOF_T   = 3.2                             # capture roof — its slot edges bear the string pull
CAGE_TOP = POST_Z1 - ROOF_T                # roof underside: the nut seats up against it
CAGE_BOT = 2.5                             # cage floor, dropped into the plate: cage ≈ 2× the
                                           # nut Ø so the string/nut can angle in (sets the
                                           # post's sweep bottom → the upper ledge's Z)
CAGE_W   = D.STRING_NUT_L + 0.6            # cavity width (Y): the nut slides in freely
SILL_H   = 2.0                             # mouth sill: a slack nut can't roll back out +X
SEAT_Z   = CAGE_TOP - D.STRING_NUT_D / 2   # seated-nut centre (demo placement + string path)


def _build() -> cq.Workplane:
    body = box_at(BODY_X, WIDTH, THICK, x=BODY_XC, y=0, z=0)

    # Screw clearance through (axis Z) at the origin.
    body = body.cut(cyl(SCREW_CLR_D, THICK + 2, z=-THICK / 2 - 1))
    # Nut press-pocket from the bottom face (seat lip bears on the bottom).
    body = body.cut(cyl(NUT_POCKET_D, D.NUT_BODY_LEN, z=-THICK / 2 - 0.01))

    # Guide FOOT: column + leg below the plate, guide bore through the leg.
    col_h = -D.GUIDE_FOOT_DZ - THICK / 2                   # plate bottom → foot top
    body = body.union(box_at(COL_X1 - COL_X0, WIDTH, col_h,
                             x=(COL_X0 + COL_X1) / 2, y=0,
                             z=-THICK / 2 - col_h / 2))
    body = body.union(box_at(FOOT_X1 - FOOT_X0, WIDTH, D.GUIDE_FOOT_H,
                             x=(FOOT_X0 + FOOT_X1) / 2, y=0,
                             z=D.GUIDE_FOOT_DZ - D.GUIDE_FOOT_H / 2))
    # C-bore riding the rod: a full bore plus a narrow slit out the +X face. It
    # wraps ~245°, so the Ø2.5 rod cannot pass the 1.8 slit — the rod alone
    # captures a loose carriage during assembly (carriage → rod → screw) — while
    # skipping the thick closed-bore +X wall that would force a stepped profile.
    body = body.cut(cyl(GUIDE_CLR_D, D.GUIDE_FOOT_H + 2,
                        z=D.GUIDE_FOOT_DZ - D.GUIDE_FOOT_H - 1)
                    .translate((D.GUIDE_ROD_DX, 0, 0)))
    body = body.cut(box_at((FOOT_X1 + 1) - D.GUIDE_ROD_DX, 1.8, D.GUIDE_FOOT_H + 2,
                           x=(D.GUIDE_ROD_DX + FOOT_X1 + 1) / 2, y=0,
                           z=D.GUIDE_FOOT_DZ - D.GUIDE_FOOT_H / 2))

    # Anchor POST: a tall BALL CAGE toward the bridge bearing. Stringing: the
    # plain end enters the +X mouth at an angle, threads up out the roof slot,
    # the whole string pulls through, and the ball-end cylinder NUT (axis Y)
    # swings in last, seating UP against the roof — the slot is narrower than
    # the nut, so the pull captures it (no clamp). The cage is ~2× the nut Ø
    # (floor dropped into the plate) so there's room for that angled entry; at
    # exactly nut height the bend would have to happen at zero distance.
    body = body.union(box_at(X_HI - 4.0, WIDTH, POST_Z1 - CAGE_BOT,
                             x=(4.0 + X_HI) / 2, y=0, z=(POST_Z1 + CAGE_BOT) / 2))
    # cavity, open to the +X face above the sill (solid Y walls — no through-seat)
    body = body.cut(box_at(7.5, CAGE_W, CAGE_TOP - (CAGE_BOT + SILL_H),
                           x=5.5 + 7.5 / 2, y=0,
                           z=(CAGE_TOP + CAGE_BOT + SILL_H) / 2))
    # floor well behind the sill (the sill ties the Y-wall bottoms together)
    body = body.cut(box_at(4.1, CAGE_W, SILL_H + 0.1,
                           x=5.5 + 2.05, y=0, z=CAGE_BOT + (SILL_H + 0.1) / 2))
    # +Z string slot through the roof (both spans < the nut → captured)
    body = body.cut(box_at(STRING_SLOT_W, STRING_SLOT_Y, ROOF_T + 1,
                           x=D.ANCHOR_DX, y=0, z=CAGE_TOP + (ROOF_T + 1) / 2))
    # lead-in on the roof's UNDERSIDE so the threaded-up tip finds the slot. The
    # flare stays smaller than the Ø3.5 nut in X (3.2) so the seated nut bears on
    # the slot edges and can't wedge in; Y can flare wide (the nut is 6 long).
    lead = (cq.Workplane("XY", origin=(D.ANCHOR_DX, 0, CAGE_TOP))
            .rect(3.2, 5.5)
            .workplane(offset=1.2).rect(STRING_SLOT_W, STRING_SLOT_Y)
            .loft(combine=False))
    body = body.cut(lead)
    # small top-edge relief: under tension the string leans −X toward the bearing,
    # so it bears on a slope instead of the slot's sharp top edge
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCone(
        STRING_SLOT_W / 2, 2.25, 1.0,
        cq.Vector(D.ANCHOR_DX, 0, POST_Z1 - 1.0), cq.Vector(0, 0, 1))))
    return body


carriage = _build()
