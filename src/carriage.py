"""Carriage (×10) — PETG-GF, load-critical (§8 item 1).

The moving element, riding a VERTICAL leadscrew (axis Z) — it travels in Z. It
presses the round nut into its pocket, rides the guide rod (anti-rotation), and
anchors the string ball-end directly under the bridge bearing, reaching +X over
the screw to do so. Tension path: string → carriage → nut → screw → support brg.

Local frame: origin on the SCREW axis (axis Z). The nut presses in from below;
the string ball-end anchor is at X=+ANCHOR_DX (under the bridge bearing),
opening +Z so the string runs up to it. The guide bore lives in a +X BOSS at
the nut level (no hanging column) — the rod sits below the stringing window.

Print orientation: build −X → +X (PRINT_UP = +X). The whole part lies on its
−X face; the layer lines then run in Z (and Y), so the string-tension load — up
the Z axis through the nut and cage — is carried ALONG the layers, not across
them. Consequences of that choice, both handled here:
  • The three bores (screw clearance, nut pocket, guide) AND the string EXIT hole
    have axis Z ⊥ the build direction, so each is a `printable_bore` TEARDROP (apex
    toward +X) — a plain cylinder would sag its ceiling. The round lower half is
    untouched (the nut and rod ride the bottom exactly as in a round bore).
  • A tower rising off a lower shelf casts a −X-facing overhang. So the part is
    two SOLID PRISMS with the gap between them filled in (not a floating post):
    prism A = body + anchor tower as one block (Z −6..+13); prism B = the guide
    boss shelf (Z −6..+2). Then the features are cut. Filling the leadscrew→tower
    gap solid also ties the nut region straight up into the cage (stronger).
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import box_at
from cadkit.supports import printable_bore

PRINT_UP = (1.0, 0.0, 0.0)                 # build −X → +X (layer lines run in Z at the nut)

THICK   = D.CARRIAGE_THICK                  # Z height of the body band (single-sourced in
                                            # dimensions: the nut placement and the screw
                                            # length are both derived from it)
WIDTH   = D.NUT_OD + 2 * 1.0               # across (Y), ≤ string pitch
NUT_POCKET_D = D.NUT_OD + 0.2
X_LO    = -(NUT_POCKET_D / 2 + 2.0)        # wall past the nut pocket (−X) = the bed face
X_HI    = D.ANCHOR_DX + D.BEAD             # body/tower +X shoulder, 1 bead past the
                                           # anchor line (boss overlaps it; was 0.9)
# Guide-rod bore — defined up here so the tower face can be sized off it (its real +X limit).
GUIDE_CLR_D = D.GUIDE_ROD_D + D.FIT_CLR
GUIDE_R     = GUIDE_CLR_D / 2
# tower +X face — as far +X as it reaches: the guide-rod bore sits ROD_FACE_GAP outboard, and
# closing that to a full 2 beads would shove the rod past the endplate edge (the known +X limit),
# so the exit hole moves INBOARD to win its wall instead of growing the face.
ROD_FACE_GAP = D.MIN_WALL                  # one bead (was 0.9; the face slides +X 0.1)
POST_X1H = D.GUIDE_ROD_DX - GUIDE_R - ROD_FACE_GAP
# String EXIT hole up through the roof (+Z): a printable_bore TEARDROP (apex +X — the "45 /\" cap),
# self-supporting in the +X print, Ø only enough to pass the heaviest string, < the Ø4 nut so the
# nut is captured under the roof. Pulled INBOARD of the anchor (EXIT_DX) so its +X apex clears the
# face by a full 2 beads (MIN_WALL_2P) — bought entirely on this side, no rod or bearing move (so
# the scale length is untouched). The string still exits at the anchor (ANCHOR_DX), riding the
# hole's +X side ~0.15 mm off the apex — a slight offset the user confirmed is fine. Ø is kept
# small so the hole's −X edge still leaves a 1-bead roof lip to the cavity back wall, and the
# leadscrew web (screw apex → back wall) stays a full 1.6 mm.
STRING_EXIT_D = 2.2                         # heaviest string (C6 .070 ≈ 1.8) + threading clearance
EXIT_DX = POST_X1H - D.MIN_WALL_2P - STRING_EXIT_D / 2 * math.sqrt(2.0)

# Anchor tower (fused into prism A): a tall BALL CAGE toward the bridge bearing.
ANCHOR_POST_H = 7.0                        # tower above the body: top 1 mm under the bearings
POST_Z1  = THICK / 2 + ANCHOR_POST_H       # tower top (+13) = prism A top
# THE CAGE IS WHAT CAPS THE BRIDGE BEARING'S OD, so assert the gap rather than
# trusting two constants in different files to stay in step. The string rides the
# bearing OD, so its underside sits at STRING_Z - OD; the cage top is right beneath.
# This fired once already: a bead-grid round moved SCREW_TOP_Z 2.0 -> 2.4, which
# quietly ate 0.4 of the clearance the 695ZZ round had just bought.
_BRG_GAP = (D.STRING_Z - D.BRIDGE_BEARING_OD) - (D.CARRIAGE_NOM_Z + POST_Z1)
assert _BRG_GAP >= 1.0 - 1e-9, (
    f"the carriage's ball cage clears the bridge bearings by only {_BRG_GAP:.2f} "
    f"(want 1.0): drop CARRIAGE_NOM_Z, or shrink BRIDGE_BEARING_OD")
ROOF_T   = 3.2                             # capture roof — its slot edges bear the string pull
CAGE_TOP = POST_Z1 - ROOF_T                # roof underside: the nut seats up against it
CAGE_BOT = 3 * D.BEAD                      # 2.4 cavity mouth bottom, dropped into the body
CAGE_W   = D.STRING_NUT_L + 0.6            # cavity width (Y): the nut slides in freely
CAGE_FLOOR = CAGE_BOT + 2.0               # cavity floor, FLUSH with the mouth bottom (solid base
                                           # under the side walls; string tension holds the nut up)
SEAT_Z   = CAGE_TOP - D.STRING_NUT_D / 2   # seated-nut centre (demo placement + string path)

# Bores (axis Z, ⊥ the +X build → teardrops). Trim screw clearance to Ø5.5 (0.25 mm
# radial on this NON-CONTACT bore — the guide rod's 0.15 mm slop bottoms out first) so
# the teardrop apex, which pokes +X toward the cavity, still leaves a 2-bead tension web:
#   web = CAVITY_X0 − apex = 5.5 − (5.5/2)·√2 = 1.61 ≥ MIN_WALL_2P.
SCREW_CLR_D  = D.SCREW_OD + 0.5
NUT_POCKET_D = D.NUT_OD + 0.2
# guide boss +X face: 2-bead wall past the TEARDROP APEX (the peak reaches r·√2, ~0.41 r
# further +X than a round bore — size to the apex, not the circle).
GUIDE_BOSS_X1 = D.GUIDE_ROD_DX + GUIDE_R * math.sqrt(2.0) + D.MIN_WALL_2P

CAVITY_X0 = 7 * D.BEAD                     # 5.6 cavity back wall (mouth depth); web to the
                                           # screw teardrop apex = 5.6 - 3.89 = 1.71 ≥ 1.6

# guide-boss z-band (nut level): top at D.GUIDE_FOOT_DZ, one bore-engagement tall.
FZ1 = D.GUIDE_FOOT_DZ                       # +2 (below the cavity bottom 2.5)
FZ0 = FZ1 - D.GUIDE_FOOT_H                  # −6 (body bottom)


def _bore(d, z0, length, x=0.0, overshoot=0.0):
    """A `printable_bore` teardrop cutter, axis +Z from z0, apex toward +X."""
    return printable_bore(d, length, axis_point=(x, 0.0, z0),
                          axis_dir=(0.0, 0.0, 1.0), print_up=PRINT_UP,
                          overshoot=overshoot)


def _build() -> cq.Workplane:
    # ── Two SOLID PRISMS (user) ───────────────────────────────────────────────
    # A: body + anchor tower as ONE block — the leadscrew→tower gap is filled in,
    #    so nothing overhangs the −X face when printing +X.
    body = box_at(POST_X1H - X_LO, WIDTH, POST_Z1 - (-THICK / 2),
                  x=(X_LO + POST_X1H) / 2, y=0, z=(-THICK / 2 + POST_Z1) / 2)
    # B: guide-boss shelf (rides the rod), overlapping A's +X shoulder.
    body = body.union(box_at(GUIDE_BOSS_X1 - X_HI, WIDTH, FZ1 - FZ0,
                             x=(X_HI + GUIDE_BOSS_X1) / 2, y=0, z=(FZ0 + FZ1) / 2))

    # ── Cuts ──────────────────────────────────────────────────────────────────
    # Screw clearance, full Z (the screw runs on up past the carriage), teardrop.
    body = body.cut(_bore(SCREW_CLR_D, -THICK / 2, THICK / 2 + POST_Z1, overshoot=1.0))
    # Nut press-pocket from the bottom face (seat lip bears on the bottom), teardrop.
    body = body.cut(_bore(NUT_POCKET_D, -THICK / 2 - 0.01, D.NUT_BODY_LEN))
    # Guide bore through the boss — closed, so the rod alone captures a loose
    # carriage during assembly (carriage in place → rod drops in → screw last).
    body = body.cut(_bore(GUIDE_CLR_D, FZ0 - 1, (FZ1 - FZ0) + 2, x=D.GUIDE_ROD_DX))

    # TWO cuts make the cage (user):
    # (1) NUT-ENTRY cavity, open to the +X face — big enough to install the nut. Floor
    #     flush with the mouth bottom (solid Y walls, no through-seat; solid block below
    #     the floor). Stringing: the plain end enters the +X mouth, threads up out the
    #     roof exit hole, the whole string pulls through, and the ball-end cylinder NUT
    #     (axis Y) swings in last, seating UP against the roof.
    body = body.cut(box_at(POST_X1H - CAVITY_X0 + 2.0, CAGE_W, CAGE_TOP - CAGE_FLOOR,
                           x=(CAVITY_X0 + POST_X1H + 2.0) / 2, y=0,
                           z=(CAGE_TOP + CAGE_FLOOR) / 2))
    # (2) STRING-EXIT hole up through the roof — a teardrop (apex +X), so it prints clean
    #     with no lead-in funnel. Ø < the nut, so the seated nut bears on the roof lip and the
    #     pull captures it (no clamp). Pulled INBOARD to EXIT_DX (string rides its +X side).
    body = body.cut(_bore(STRING_EXIT_D, CAGE_TOP, POST_Z1 - CAGE_TOP,
                          x=EXIT_DX, overshoot=1.0))
    return body


carriage = _build()
