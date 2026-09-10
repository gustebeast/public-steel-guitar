"""Top-level coordinate system, dimensions, materials, and fit clearances.

These are the constants every part draws from. Part-local constants live next to
the part they apply to.

──────────────────────────────────────────────────────────────────────────
COORDINATE SYSTEM (global, millimetres) — the player's perspective
──────────────────────────────────────────────────────────────────────────
  +X : ALONG the strings. +X is the changer (bridge); −X is the nut / keyhead.
       The bridge bearings sit at X = 0; the speaking length and nut run toward −X.
  +Y : ACROSS the strings. Field centred on Y = 0. The player sits at −Y.
  +Z : up (thickness). The speaking length rides on top; the mechanism hangs
       below (−Z).

LAYOUT (under-string, vertical-screw):
  Each string turns 90° over its bridge bearing and runs DOWN to a VERTICAL
  leadscrew (axis Z) at the bridge; the carriage travels in Z (only the bend
  range, so the screws are short — ~61 mm, no whip). The motors lie flat UNDER
  the speaking length in a staircase along −X, shaft facing +Y (body extends −Y
  toward the player). A twisted GT2 belt turns each motor pulley (axis Y) to its
  screw pulley (axis Z) — the common perpendicular of Y and Z is X, so the belt
  runs along X under the strings.
"""

# ─────────────────────────────────────────────────────────────────────────
# Print process — the min-material floor (cadkit.printing owns the rule)
# ─────────────────────────────────────────────────────────────────────────
from cadkit.fasteners import M4
from cadkit.printing import min_wall
NOZZLE_D        = 0.8       # the PROJECT DEFAULT nozzle. Most of this instrument is
                            # structure -- rails, legs, housings -- and prints 0.8.
BEAD            = NOZZLE_D  # THE UNIT. Every printed length is N * BEAD, or another
                            # feature +- N * BEAD (cadkit.printing documents the rule and
                            # the three exemptions; tools/check_beads.py enforces it).
                            # Write lengths as counts -- `13 * BEAD`, not `10.4` -- so the
                            # bead count is what you read and what you edit.
# PER-PART OVERRIDE (user): the nozzle is a property of the PART, not the project.
# A part with fine detail -- the belt clamp's tooth pitch is 2.0 mm, which 0.8 cannot
# resolve -- is printed with a finer nozzle and gets a finer grid. Such a module
# declares its own at the top and derives its own bead:
#
#     NOZZLE_D = 0.4                  # this part prints 0.4 (GT2 teeth)
#     B        = NOZZLE_D
#
# tools/check_beads reads that per module and grades the part against ITS grid.
# MATING is safe in one direction only, and it is worth knowing which: a coarse
# length is always valid on a finer grid (0.8 is exactly two 0.4 beads), but not
# the reverse. So a face SHARED between a 0.8 part and a 0.4 part must sit on the
# COARSER grid -- size shared features from the coarse part and let the fine part
# inherit them.
MIN_WALL        = min_wall(NOZZLE_D)          # 0.8 — one-bead HARD floor (web/ceiling/rib).
                                              # A lone bead slices mushy, so PREFER MIN_WALL_2P;
                                              # drop to MIN_WALL only in a genuinely tight room.
MIN_WALL_2P     = min_wall(NOZZLE_D, beads=2) # 1.6 — two-bead QUALITY target (crisp perimeters).
                                              # No buffer: Arachne fills exact nozzle multiples cleanly.

# ─────────────────────────────────────────────────────────────────────────
# MR85 (Ø5×8×2.5) — the ONE bearing, used at BOTH ends of every leadscrew.
# Hoisted up here because the thrust stack, the top radial bearing and the screw's
# own length all derive from it and they are declared far apart.
# ─────────────────────────────────────────────────────────────────────────
MR85_OD, MR85_ID, MR85_W = 8.0, 5.0, 2.5     # Ø5 bore — KNEE LEVER / pedal axles only
# THE SCREW'S BEARING IS NO LONGER MR85. Tr8 made that impossible rather than merely
# undesirable: MR85's bore is Ø5 and the screw is now Ø8, so the shaft does not pass
# through it at all. 688ZZ (Ø8 x Ø16 x 5) is the replacement, chosen over the closer-
# fitting MR148 (Ø14) on CAPACITY: MR148 publishes C0r 144-309 N, which as a thrust
# bearing is 72-154 N permissible axial against the 147 N a string actually pulls —
# inadequate. 688ZZ is 474-710 N, i.e. 237-355 N axial, so ONE clears it. The cost is
# OD: Ø16 in the 19.0 in-row pitch leaves 1.4 mm of web per side, over the one-bead
# floor but under the two-bead preference — the tightest spot in the new layout.
# ⚠ C0r spans 474-710 ACROSS MAKERS, which is wider than the 1.6x worst-case margin:
# buy a branded part and read its real C0r. See SUPPORT_BRG_N for the stacking story.
BRG688_OD, BRG688_ID, BRG688_W = 16.0, 8.0, 5.0  # 688ZZ — Ø8 bore, the leadscrew's
BELT_PLANE_DZ   = 11 * BEAD  # 8.8 — the two screw-pulley planes' Z separation.
# History: 14*BEAD = 11.2 while ten pulleys shared one X line at the 9.5 string pitch,
# where neighbouring Ø11 flanges physically overlapped and alternate ones had to be lifted
# clear. Two rows took the in-row pitch to 19.0, so that job went away and it was halved
# to 5.6. THAT WAS TOO FAR. The split's remaining job is keeping far-row BELTS off the
# near-row PULLEYS they run past, and the claim that those "clear laterally by 1.5 on
# their own" assumed a flat belt at its own string Y. It is not flat there — it is partway
# through its 90° twist, which widens it sideways into the neighbour's lower flange. Every
# far-row belt clipped its near-row neighbours (up to 9.8 mm^3), and no gate said so,
# because check_overlaps skips belts unless it is run with --full.
# The real bound is in Z: the near pulley reaches PULLEY_BOT below its band, and the far belt
# reaches above its own band by its section's HALF-DIAGONAL (a twisted 5 x 1.4 ribbon, not
# the 2.5 half-width) PLUS the rise of its centreline toward the motor plane by the time it
# gets to the near row — asserted after motor_pos, which the run length needs. A first
# pass at 8.0 used the half-width and no rise, and left two belts grazing at 0 clearance. It costs nothing
# at the thrust stack (the pulley TOP is the frozen datum, see PULLEY_TOP_Z); the LOW band
# drops instead, and the motors, riding midway between the planes, drop half of that.
# Declared up here because the pulleys' plane split is exactly this, and the thrust stack
# sits on top of the pulleys.


# ─────────────────────────────────────────────────────────────────────────
# String field (strings spaced ACROSS, along Y; lowest pitch at −Y / player)
# ─────────────────────────────────────────────────────────────────────────
N_STRINGS       = 10
STRING_PITCH    = 9.5       # mm, changer pitch (across, Y)
NUT_PITCH       = 6.5       # mm, spacing at the nut/keyhead end
STRING_FIELD_W  = (N_STRINGS - 1) * STRING_PITCH   # 85.5 mm
MOUNTING_SPAN   = 615.0     # between a string's two mounting ends (~24.2" scale)
XBAR            = 13 * BEAD  # 10.4 - the one square-module cross-section: square cross-rib section (10×10),
                            # end-crossbar width, and the leg/endplate border + L offset
WALL_THICKNESS  = 13 * BEAD  # 10.4 structural wall: I-beam rail thickness, the keyhead/bridge
                            # endplate faces, and the deck inner/outer face references

# The pedal bar's Z height. Lives HERE, not in pedal_bar, because legs.py needs it
# too (the -Y legs' wide block must equal foot + bar + tower + block on all four
# legs — the user's equal-wide-section rule) and legs cannot import pedal_bar
# without a cycle. Sized by the LID: the bar now prints -Y -> +Y, so the sliding
# dovetail moved from the +Z face to the +Y face, and that face spans Z. The
# dovetail's foot is the widest thing in it.
PEDAL_LID_FOOT_W = 30 * BEAD   # 24.0 dovetail foot (both asserts hold: bar skin
                               # (27.9-24)/2 = 1.95 >= 1.6, and the bar still hosts
                               # foot + 2 skins = 27.2 <= 27.9)
# WHAT SETS THE HEIGHT NOW: the user's playing datum, the height of the pedal AXLE
# centre above the floor (the TPU feet's underside) — 0.8*60, on the nozzle grid.
# The bar carries the pedal housings, so the axle rides FOOT_H + BAR_H + the
# housing's own standoff; inverting that gives the bar. foot_pedal asserts the
# achieved height against this datum, which is what keeps the chain honest if any
# of the three terms moves.
PEDAL_AXLE_H     = 0.8 * 60   # 48.0 — axle centre above the floor (user)
PEDAL_BAR_H      = 27.9     # = PEDAL_AXLE_H - legs.FOOT_H(12) - foot_pedal.HOUS_X1(8.1);
                            # spelled out rather than imported (legs/foot_pedal both
                            # read this module — the import only goes one way).
                            # Must still HOST the lid, which is the constraint that
                            # used to set it (23.8 of dovetail + 2 skins = 27.0 floor):
assert PEDAL_BAR_H >= PEDAL_LID_FOOT_W + 2 * MIN_WALL_2P, (
    f"a {PEDAL_BAR_H} bar cannot host the {PEDAL_LID_FOOT_W} dovetail with "
    f"{MIN_WALL_2P} skins")
PEDAL_TOWER_BAND = 24.0     # bar top -> tower seat: the latch button band

def string_y(i: int) -> float:
    """Y centre of string i (0..9) at the changer. Index 0 = string 1 (lightest) sits at
    +Y; the index rises toward −Y (the player side), where string 10 (heaviest) sits."""
    return ((N_STRINGS - 1) / 2.0 - i) * STRING_PITCH

def nut_y(i: int) -> float:
    """Y centre of string i at the nut end (strings fan to here); same ordering."""
    return ((N_STRINGS - 1) / 2.0 - i) * NUT_PITCH


# ─────────────────────────────────────────────────────────────────────────
# Heights (Z). Speaking length on top; mechanism below.
# ─────────────────────────────────────────────────────────────────────────
STRING_Z        = 16.0      # speaking-length / bridge-bearing top
DECK_TOP_Z      = 8 * BEAD  # 6.4 deck-plate top = playing-surface datum; the chassis deck
                            # plane (TP_GZ0/1) and the keyhead nut-block base both sit here
# Travel budget from string physics. f ∝ √(stretch) ⇒ stretch ∝ f², so the
# carriage travel between two pitches is the change in stretch:
#   travel(f1→f2) = DL_OPEN · ((f2/f_open)² − (f1/f_open)²)
# where DL_OPEN is the stretch beyond slack at open pitch:
#   DL_OPEN = T_open · L0 / (E · A_core)  ≈ 4 mm for typical steel strings at a
#   615 mm scale (T≈80–120 N, E≈200 GPa, steel core A). Varies with gauge → size
#   for the largest in the set (or measure: anchor travel from barely-taut to
#   pitch). Consequences: slack→open take-up ≤ DL_OPEN regardless of hand-tight
#   tightness; +6 semitones (3 whole steps) above open = DL_OPEN·(2^(6/6)−1) =
#   DL_OPEN. So usable travel = DL_OPEN (slack→open) + DL_OPEN (+6 st) + margin.
DL_OPEN         = 4.0
# 4 SEMITONES of upward bend, not 6 (user) — traded for the travel it frees, which is
# what lets the nut ride high enough for the thrust stack to move above the pulleys.
# stretch ∝ f², so the bend costs DL_OPEN·(2^(n/6) − 1): 4.00 at six semitones, 2.35 at
# four. The other two terms are unchanged — a full DL_OPEN of slack→open take-up (that
# is the "hand tight" allowance, and it is bounded by DL_OPEN however loosely you pull)
# plus 2.0 of margin for new-string break-in.
PITCH_UP_ST     = 4
CARRIAGE_TRAVEL = DL_OPEN * 2 ** (PITCH_UP_ST / 6) + 2.0    # 8.35

# ── THE NUT IS THE CARRIAGE (user) ─────────────────────────────────────────
# There is no printed carriage any more. The H-nut's own two mounting ears do
# both jobs it did: the +X ear ANCHORS THE STRING (ball end underneath, string up
# through the Ø3 hole — tension pulls the ball against the ear, exactly a guitar
# bridge plate) and the -X ear RIDES THE GUIDE ROD. That deletes a printed part
# ×10, twenty M2 screws, ten spacers, and with them the whole boss-recess / Y-open
# channel / 45° ramp chain — every one of which existed only to marry the nut to a
# carriage that is now gone.
#
# It also unpins the Z datum. The carriage's height was set by its BALL CAGE, which
# cleared the bridge bearings by exactly the 1.0 minimum and could not rise; that is
# what forced the boss to be recessed in the first place. With no cage the nut is
# free, and it now sits where the PULLEYS want it — high enough that the boss clears
# the raised plane by a comfortable margin instead of fighting for a millimetre.
#
# WHY THE STRING TAKES THE +X EAR (user): it has to be reachable, and the changer
# room already opens +X for exactly that. The cost is that the ear sits at
# SCREW_X + NUT_HOLE_DX = -1.5 rather than on the bearing's tangent at 0, so the
# dead run leaves the bearing ~2.6° off vertical over its ~33 mm drop — an ordinary
# break angle. THE POINT of accepting that angle is that SCREW_X DOES NOT MOVE. Put
# the string on the -X ear instead and the screw line would have to shift to suit a
# GUESSED hole pitch, dragging the rail, both pulley planes, ten belt runs and the
# motor bank with it. This way a wrong guess costs a fraction of a degree on a dead
# length and nothing else.
NUT_TOP_Z       = -7.2      # flange TOP at the top of travel. A FROZEN datum, not a
                            # derivation: it is asserted below against the THRUST STACK,
                            # which now sits on top of the pulleys rather than under them.


# ─────────────────────────────────────────────────────────────────────────
# Leadscrew nut — H-TYPE brass flange nut, BOLTED under the carriage.
# Declared BEFORE the screw because the screw's length derives from its travel.
# ─────────────────────────────────────────────────────────────────────────
# The round Ø20-flange nut is gone. Its flange had to be turned to Ø9 and its
# boss to Ø7 to fit the 9.5 mm string lane — a two-cut lathe job on ten parts,
# which is not something an open-source build should demand. The H-TYPE nut is
# the same part with the flange already milled to two flats tangent to the boss,
# so it arrives lane-ready: ACROSS FLATS is the dimension that has to fit 9.5,
# and it does.
#
# ⚠ EVERY NUMBER IN THIS BLOCK IS A GUESS. The part is on order and unmeasured;
# the seller publishes no drawing for the H version. They are derived from the
# CONFIRMED drawing of the round-flange T5 nut (flange Ø20 × 3.2, boss Ø8 × 6.6,
# total 9.8, three Ø3 holes on a Ø13 bolt circle) by taking the H cut to be
# exactly that disc with two flats milled at ±AF/2:
#   AF        — flats tangent to the Ø8 boss, +0.25 each side for a real cut
#   FLANGE_L  — the chord that survives: 2·√(10² − (AF/2)²) = 18.1
#   HOLE_DX   — the Ø13 bolt circle, re-drilled on the long axis (the disc's
#               120° pattern does not survive the flats: two of its three holes
#               sit at |y| 5.63, outside AF/2)
# CONFIRM ALL SIX ON ARRIVAL. FLANGE_L and HOLE_DX are the load-bearing guesses:
# FLANGE_L sets how far the ears sweep -X (see bridge_endplate's nut-sweep slot)
# and HOLE_DX sets the carriage's -X face. Both are asserted downstream, so a
# wrong guess fails the build loudly rather than quietly fouling something.
# Tr8x2 H-FLANGE brass nut, read off the seller's dimensioned drawing 2026-09-08
# (AliExpress 3256804704147842, SKU "Pitch 2mm Lead 2mm"). These are no longer
# extrapolated from a disc: the drawing gives every one directly. The listing still
# states its own accuracy as "a normal error of 0.5-1 mm", so the BOM keeps a
# buy-one-and-MEASURE gate -- see the row-spacing note under SCREW_ROW_DX, which is
# what spends that tolerance.
NUT_AF          = 10.5      # across flats (Y) — was THE lane-critical dimension, and
                            # is why the screws are now in TWO ROWS: 10.5 cannot live
                            # in a 9.5 lane at any screw size.
NUT_FLANGE_L    = 22.0      # long axis (X), tip to tip (R11 ears)
NUT_FLANGE_T    = 4.0
NUT_BOSS_D      = 10.2
NUT_BOSS_L      = 11.0      # 15 overall - 4 flange
NUT_H           = NUT_FLANGE_T + NUT_BOSS_L                            # 15.0
NUT_HOLE_D      = 3.5       # the ears' through-holes
NUT_HOLE_DX     = 8.0       # ± from the axis (16 mm hole pitch)
# MOUNTING — FLANGE UP, BOSS DOWN, and nothing bolts to anything.
# Flange up puts the EARS at the top of the nut, which is what keeps the string's
# ball end as high as possible: it hangs one flange-thickness below the ear, so at
# the bottom of travel it stops well clear of the drive pulleys instead of reaching
# down among them. The boss hangs below on the screw axis, where the pulley's own
# swept circle is the only thing nearby and NUT_BOT_MIN is asserted against it.
NUT_TOP_MAX     = NUT_TOP_Z                                            # -10.0
NUT_BOT_MIN     = NUT_TOP_Z - CARRIAGE_TRAVEL - NUT_H                  # -29.8, at BOTTOM of travel


# ─────────────────────────────────────────────────────────────────────────
# Vertical leadscrew (single-start, self-locking — the keystone, §3) — axis Z
# ─────────────────────────────────────────────────────────────────────────
# Ø5×1 single-start: lead angle ~3.6° (very self-locking) and fast enough (a
# semitone is only ~1.5 mm). Vertical ⇒ short (no whip).
SCREW_OD        = 8.0       # Tr8x2: Ø8, SINGLE-start, 2 mm lead.
# WAS Ø5x1, AND THE REASON IT IS NOT ANY MORE (2026-09-09). The old note here argued
# Ø5 was forced: ten screws on ONE X line at the 9.5 string pitch leave each nut a
# 9.5 mm lane, and no Tr8 nut fits that. Both halves of that have since failed.
#   The LANE was the wrong thing to hold. Ø5x1's 1 mm lead circulates the belt ~28 mm
#   per mm of carriage, so the splice clamp cannot stay inside the short strings' belt
#   runs at all -- a defect no nut choice fixes. The 2 mm lead halves that.
#   The ONE LINE was not required. Alternating strings between two rows doubles the
#   in-row pitch to 19.0, which fits the 10.5 across-flats nut with 8.5 to spare, and
#   costs nothing in string spacing (see SCREW_ROW_DX).
# Tr8x2 is also a CATALOGUE part where Tr5x1 was a specialty one -- it is the base of
# the ISO/DIN 103 series -- and single-start keeps the 5.2 deg lead angle that makes it
# self-locking, which is what holds tuning with the motors unpowered.
# TOP: the screw only has to clear the NUT, and the nut is now the whole moving
# assembly — so the screw stops SCREW_RUNOUT above the flange's top face and nothing
# else needs reaching. RUNOUT is pure insurance for build tolerance.
# THREAD-FORMING BORE — shared by the retaining collar and the drive pulley. Both grip
# a rod whose thread we cannot merely clamp (screw_collar.py has that arithmetic).
#
# It is a PILOT THREAD, not a plain cylinder (user). A Tr lead screw has blunt 30°
# flanks and no cutting edges, so it FORMS rather than cuts — the better process for
# plastic, but it needs somewhere to track. A plain bore gives it nothing: nothing sets
# the lead, nothing resists starting a turn crooked, and nothing pulls it back once it
# has. A printed helix at the true pitch is a track it can only follow.
#
# The two diameters are picked against the ROD, not against each other:
#   FORM_MINOR  the printed ridge. 0.1 mm radially CLEAR of the rod's root (Ø4.0), so
#               the ridge never bottoms out — root interference is all torque, no grip.
#   FORM_MAJOR  the printed groove. 0.1 mm radially UNDER the rod's crest (Ø5.0), so
#               the crest swages it going in. That 0.1 is the entire forming allowance,
#               and it is the usual figure for thread-forming into plastic.
# After forming, the plastic ridge spans 4.2..5.0 — 0.4 of the 0.5 radial full form,
# ~80% engagement, reached by displacement rather than by hoping a plain cylinder would
# flow into the right shape on its own.
# Depth is (4.8-4.2)/2 = 0.3 — inside cadkit.threads' depth <= pitch/2 rule, and 45°
# flanks, so it is self-supporting with the bore axis vertical, which is how both parts
# print. It does NOT resolve on the project's 0.8 nozzle (0.3 radial is under half a
# bead) — both parts are 0.2-NOZZLE prints and therefore unfilled, the same call
# belt_clamp already makes for GT2 ridges. At 0.2 the groove is a 1.5-bead feature.
SCREW_PITCH     = 2.0       # Tr8x2: 2 mm pitch, single start => 2 mm LEAD
FORM_MINOR      = 6.2       # printed ridge Ø (Tr8x2 root is Ø5.5; 0.35 radial clear)
FORM_MAJOR      = 7.8       # printed groove Ø (0.1 radial under the Ø8 crest)
                            # Depth (7.8-6.2)/2 = 0.80, NOT the pitch/2 = 1.0 ceiling.
                            # cadkit.threads measures the valley AT THE OVERSHOOT:
                            # valley = 2*depth + 0.2, and it must stay UNDER the 2.0
                            # turn spacing or adjacent turns merge into an invalid
                            # cutter that silently no-ops. Depth 1.0 gave 2.10 and 0.90
                            # gave exactly 2.00 — both rejected. 0.80 leaves 1.80.
                            # Engagement is 0.80 of the rod's 1.25 radial full form,
                            # ~64%, reached by displacement rather than by hoping.
SCREW_RUNOUT    = 3 * BEAD                          # 2.4 proud of the nut at top of travel
# TOP RADIAL BEARING. The screw runs on past the nut into one MR85 up in the endplate's
# slab, and this is not a refinement — it is what makes anchoring the string off-axis
# sound at all. The string pulls 147 N at the ear, NUT_HOLE_DX off the screw axis, which
# is a standing ~956 N·mm couple. The thrust stack alone would have to react that across
# two bearings 2.5 mm apart — about 382 N radial each, ~1.5× MR85's static radial rating.
# A second support ~28 mm away turns it into ~34 N.
# It must FLOAT axially (a plain slip-fit seat, no shoulder either side) or it fights the
# thrust stack for the string load and over-constrains the shaft: the classic
# fixed/floating pair, thrust at one end, alignment at the other.
# THE TOP BEARING IS GONE (see build._string_components), so this is no longer a seat
# mouth — it is only the CHANGER ROOM'S CEILING, which is the other job it was doing.
# Renamed to say so. Its formula is kept as-is deliberately: the ceiling wants to sit a
# clear 2 beads over the screw's own top, which is exactly what it already computed.
CHANGER_CEIL_Z  = NUT_TOP_Z + SCREW_RUNOUT + 2 * BEAD   # -3.2, changer room ceiling
# THE SCREW ONLY HAS TO CLEAR THE NUT. It used to end flush inside the top bearing
# (SCREW_TOP_Z = TOP_BRG_Z1, built on MR85_W — a bearing this design no longer uses at
# all). With that bearing deleted the screw was still running up to where it had been,
# 4.10 INTO the solid endplate slab (user saw it clipping). Nothing up there needs
# reaching now, so it stops SCREW_RUNOUT proud of the flange's top face and no further.
SCREW_TOP_Z     = NUT_TOP_Z + SCREW_RUNOUT              # -4.80


# ─────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────
# Guide rod (anti-rotation) — axis Z, through the nut's -X EAR
# ─────────────────────────────────────────────────────────────────────────
# It hangs from the endplate's guide RIB above and cantilevers DOWN through the ear
# (user). The other end has nowhere to go: the drive relief and nut sweep between
# them removed every scrap of endplate below the room at this X line, so the top is
# the only end left to anchor to — which is also the end that prints cleanly, since
# a rib is a straight -X extension of solid cap and every layer of it is backed.
#
# Ø3, NOT the Ø2.5 dowel, and the reason is slop rather than strength. The ear's hole
# is the nut's own Ø3: a Ø2.5 rod leaves 0.5 mm of play, which lets the nut rotate
# 38 mrad and walks the string 0.25 mm. A Ø3 g6 shaft leaves 0.01 and 0.8 mrad — 50×
# better — and it is 2.1× stiffer into the bargain. It is also the SAME PART as the
# bridge axle, so it costs no new BOM line, just ten more pieces.
# Bending was never the problem and an earlier note here overstated it: the rod only
# spans the ear's travel plus the ear, ~15 mm, not the room's height, and deflects
# 0.016 mm under the 11 N anti-rotation load. What matters is the SOCKET — over the
# rib's grip any clearance is amplified across that 15 mm, so it is a PRESS fit.
# MATCHED TO THE NUT'S EAR HOLE (user, 2026-09-10). Ø3 was chosen to take the slop out of
# the old nut's Ø3 ear; the Tr8x2 H-flange nut's ears are Ø3.5, so a Ø3 rod had put back
# exactly the 0.5 mm of play the Ø2.5 dowel was rejected for (~38 mrad of nut rotation).
# DERIVED from NUT_HOLE_D so the two cannot drift apart again. No longer the same stock
# as the bridge axle (Ø5): buy it as a Ø3.5 DRILL BLANK, which is sold in 0.1 mm steps —
# the seller's drawing is only +/-0.5-1, so MEASURE the real ear hole and pick the blank
# to it; that is the whole point of choosing a stock sold that finely.
GUIDE_ROD_D     = NUT_HOLE_D  # 3.5 — slide fit in the nut's ear, press in the endplate
GUIDE_ROD_FIT   = 0.05      # SNUG PRESS. Not zero: at zero the socket is drawn the
                            # rod's own Ø, which is not a hole you can install into,
                            # and coincident cylinders make the boolean unreliable
                            # too. 0.05 is the same snug the old rod sockets used.

# The bridge / string anchor sits at X=0; the screw can't occupy that spot, so
# it is offset −X by ANCHOR_DX and the carriage reaches over to the anchor.
BRIDGE_X        = 0.0
# TWO ROWS OF SCREWS (user, 2026-09-09). One row is impossible now: the Tr8 nut is
# NUT_AF 10.5 across flats and the string pitch is 9.5, so ten nuts cannot share an X
# line at any screw size. Alternating strings between two rows doubles the IN-ROW pitch
# to 19.0 and leaves 8.5 mm of clearance, at no cost to string spacing or playability.
#
# The rows are MIRRORED and SYMMETRIC about the bearing tangent (BRIDGE_X = 0), which
# is what keeps the string's break angle small. The dead run leaves the bearing at
# X = 0 and drops ~33 mm to the ball end; every mm the anchor sits off that line is
# break angle. Putting both rows on one side would cost 47-53 deg. Splitting them
# +/-ANCHOR_DX shares it: each row leaves the bearing at the SAME modest angle, in
# opposite directions, so the worst case is halved rather than doubled.
#
# ANCHOR_DX IS NOT FREELY CHOSEN. Mirrored rows put the screws (2*ANCHOR_DX +
# 2*NUT_HOLE_DX) apart, and cross-row flanges must clear by the full NUT_FLANGE_L
# (their Y overlap is unavoidable: 10.5 across flats on a 9.5 pitch). That floors
# ANCHOR_DX at 3.0 -> 5.2 deg. We take 4.0 -> 6.9 deg instead, because 3.0 leaves the
# rows exactly NUT_FLANGE_L apart -- ZERO clearance against a part whose own stated
# error is 0.5-1 mm, so a nut half a millimetre over nominal would not assemble. The
# 1.7 deg that buys is worth ~3% of string tension in bearing side load (sin 5.2 vs
# sin 6.9) and nothing else. Re-tighten to 3.5 once a real nut has been measured.
ANCHOR_DX       = 4.0       # anchor's |X| from the tangent -> break angle 6.9 deg
SCREW_ROW_DX    = ANCHOR_DX + NUT_HOLE_DX   # 12.0 — each row's |X|; rows 24.0 apart
                                            # (NUT_FLANGE_L 22 + 2.0 clearance)


def screw_far(i: int) -> bool:
    """Is string i on the FAR (+X) row? Reuses the belt-plane parity EXACTLY, so the
    two rows are also the two pulley planes -- far-row belts run BELT_PLANE_DZ below
    the near row's pulleys and never cross them. Phased so string 10 (last index) is
    FAR, which is what its short belt needs (user)."""
    return (N_STRINGS - 1 - i) % 2 == 0


def screw_x(i: int) -> float:
    """X of string i's leadscrew axis: +SCREW_ROW_DX on the far row, -on the near."""
    return SCREW_ROW_DX if screw_far(i) else -SCREW_ROW_DX


def string_anchor_x(i: int) -> float:
    """The ball-end ear. MIRRORED: the near row reaches +X to the tangent, the far row
    reaches -X to it, so both land ANCHOR_DX from BRIDGE_X on opposite sides."""
    return screw_x(i) - NUT_HOLE_DX if screw_far(i) else screw_x(i) + NUT_HOLE_DX


def guide_rod_x(i: int) -> float:
    """The anti-rotation ear — always the ear the string does NOT take."""
    return screw_x(i) + NUT_HOLE_DX if screw_far(i) else screw_x(i) - NUT_HOLE_DX


# String-end nut: a cylinder swaged on the string's bridge end (axis Y), slotted
# into the carriage anchor. The string exits +Z and its pull seats the nut up
# under the anchor roof (mechanical capture, no clamp). DEMO/purchased part.
STRING_NUT_D    = 4.0       # measured (user): Ø4 x 3 tall ball-end nut
STRING_NUT_L    = 3.0       # was modelled 6 -> oversize; the real 3 lets the carriage cage
                            # Y-walls go to 2.7 (= (WIDTH 9 - (L+0.6))/2), well over 2 beads
                            # (was 1.2 with the 6 mm nut)


# ─────────────────────────────────────────────────────────────────────────
# GT2 pulleys (14T) + belt. Flanges keep the (twisting) belt from walking off.
# ─────────────────────────────────────────────────────────────────────────
PULLEY_OD       = 8.4       # over teeth
PULLEY_W        = 8.0       # axial: ~6 mm toothed gap + 2 flanges (fits the 5 mm belt)
PULLEY_FLANGE_OD = PULLEY_OD + 2.6
PULLEY_FLANGE_T  = MIN_WALL      # 0.8 (was 1.0 = 1.25 beads). Rounded DOWN, not up: at 1.6 the
                                 # two flanges leave a 4.8 toothed gap for a 5.0 belt -- it would not
                                 # fit. One bead is the hard floor and fine here (a guide lip, not
                                 # structure); the gap goes to 6.4.
PULLEY_BORE_SCREW = FORM_MAJOR       # PILOT THREAD: the rod finishes its own
PULLEY_BORE_MOTOR = 5.0     # = MOTOR_SHAFT_D (declared below); the motor's own shaft
# THE PULLEY IS THE COLLAR (user). It is threaded on the rod by its pilot thread and
# the string's own 147 N jams it UP into the thrust bearings that now sit directly on
# top of it — the same jam that has always held the retaining collar, which is why that
# part never needed a set screw either. So the pulley needs no set screw, no clamp and
# no separate collar: the load that has to be carried anyway is what holds it.
# Four earlier attempts at a torque path are all dead, and each died differently:
#   • a GRUB alone — a tip on one thread crest is a point contact relying on preload.
#   • a -X LUG to hold that grub — r 8.6, swept Ø17 straight through the endplate.
#   • a C-CLAMP — needs a full-height slit, and closing an 0.8 mm gap shortens the
#     pitch circle ~3%, so the teeth stop matching the belt.
#   • a grub in a hub above the belt — worked, but it is still a screw to install per
#     station and a thing to come loose.
#
# TWO SKUs, EACH SPANNING THE WHOLE SCREW, EACH PRINTING ON ITS OWN GOOD FACE (user).
# Both pulleys run the full length of rod between the thrust plane and the screw's
# bottom, so BOTH get the same ~19.5 mm of formed-thread engagement — the pulley is
# what carries the 147 N and holds itself on the rod, so an 8 mm variant and a 20 mm
# one was never a sensible pair. Two SKUs rather than one flipping part because a part
# that flips can only stand on whichever end is smallest; two can each be printed on
# the face that suits them.
#
# THE SKUs ARE ENDCAPS (user, 2026-09-10). Neither passes the screw through its teeth
# any more. A Tr8 bore CANNOT pass through a 14T band at all: the Ø7.8 pilot groove is
# wider than the ~Ø6.9 tooth root, so the old through-bored pulley was not thin, it was
# impossible. Growing the teeth to clear it would have been a gear reduction and more
# belt circulation, and 18T+ fouls the guide rod. So the rod ENDS in a blind socket
# above the band, and the toothed band's core is SOLID.
#
# Both SKUs therefore put their column ABOVE the band — the socket has to live there —
# and they differ only in column LENGTH, by exactly BELT_PLANE_DZ. Both now print the
# same way: FLANGE-DOWN, a full Ø11 disc on the bed, the lower 45° cone narrowing up to
# the band, the upper cone flaring out, the column stepping in on top. The socket opens
# UP, so its floor is a supported floor, not a ceiling.
PULLEY_GAP      = 5.4               # toothed gap = the 5 mm GT2 belt + 0.4
PULLEY_CONE     = (PULLEY_FLANGE_OD - PULLEY_OD) / 2        # 1.3, top flange, 45° cone
# RE-SIZED FOR 688ZZ. At 7*BEAD = 5.6 this was sized for MR85's Ø5 bore and is now
# SMALLER than the Ø8 bore it is supposed to seat against -- it would have slid straight
# up through the bearing and the pulley's flange face would have landed on the SHIELD
# instead. That would have broken the screw's entire retention path, which is exactly
# this jam. 12*BEAD = 9.6 sits inside the inner ring's ~Ø8..10.2 with margin either side.
# Boss wall over the Ø7.8 pilot bore is 0.9 -- one bead, and it is pure COMPRESSION
# (147 N over 24.6 mm^2 = 6.0 MPa).
# ⚠ Ring diameters are the usual d + 0.28*(D-d) rule, not read values. CONFIRM against
# the datasheet of whichever 688 is actually bought -- same gate the BOM already carries.
PULLEY_BOSS_D   = 12 * BEAD         # 9.6 pilot on top: lands on the bearings' INNER
                                    # rings only (their OD is ~6.3). Anything wider would
                                    # drag the stationary outer ring against a pulley
                                    # that turns with the screw.
PULLEY_BOSS_H   = 1 * BEAD          # 0.8
# COLUMN = BOSS Ø. It was Ø7.2 because it had to slip past the NEIGHBOUR's Ø11 flange at
# the 9.5 string pitch. In two rows the in-row pitch is 19.0, so that ceiling is ~Ø27 and
# the column can be as fat as the boss — which it must be: at Ø7.2 it could not even
# contain the Ø7.8 socket.
PULLEY_COL_D    = PULLEY_BOSS_D                                         # 9.6
# HIGH SKU's column is the SHORT one, and the only new height this design spends: it is
# the socket's depth budget on the tighter SKU. It comes out of the pulley PLANE, not the
# thrust stack — see SCREW_PULLEY_Z. 3 beads gives a 4.1 socket at ~2.0 MPa on the formed
# thread, under a third of the 6.5 MPa the old collar was accepted at.
PULLEY_COL_HI   = 3 * BEAD                                              # 2.4, HIGH
PULLEY_COL_H    = PULLEY_COL_HI + BELT_PLANE_DZ                         # 8.0, LOW
PULLEY_END_A    = (PULLEY_GAP / 2 + PULLEY_CONE
                   + PULLEY_COL_HI + PULLEY_BOSS_H)                     # 7.2, HIGH band→top
PULLEY_END_B    = PULLEY_END_A + BELT_PLANE_DZ                          # 12.8, LOW band→top
# BOTH FLANGES CHAMFER TOWARD THE BELT (user): each presents a 45° face, so the pair is a
# shallow V and the belt self-centres. Below the lower cone a full disc is the bed face.
PULLEY_BOT      = (PULLEY_GAP / 2 + PULLEY_FLANGE_T
                   + PULLEY_CONE)                                       # 4.8, both, bed face
# BLIND SOCKET, bored down from the top. Its floor stops above the band's top, inside the
# upper cone: that cone flares 45° from the band's Ø8.4, so the wall over the Ø7.8 groove is
# 0.3 at the band and grows 1:1 going up — 0.4 above it gives 0.7, three-and-a-half traces
# of this part's 0.2 nozzle. Identical on both SKUs, so the rod ends at the same Z on every
# station and there is still ONE screw length.
PULLEY_SOCKET_FLOOR_CLR = 2 * 0.2                                       # 0.4, 0.2-nozzle part
PULLEY_SOCKET_L = PULLEY_END_A - PULLEY_GAP / 2 - PULLEY_SOCKET_FLOOR_CLR  # 4.1
# ─────────────────────────────────────────────────────────────────────────
# BOTTOM OF THE SCREW — drive pulley, thrust bearings, retaining collar (axis Z)
# ─────────────────────────────────────────────────────────────────────────
# THE PULLEY PLANE IS A ROOT DATUM — DO NOT DERIVE IT FROM THE NUT. motor_bank's
# floor and the whole belt plane hang off it (see MOTOR_BELT_Z), so when the H-nut
# moved the nut's lowest point 7.8 mm down, the old `NUT_BOT_MIN - 25·BEAD` form
# would have dragged the entire motor bank down with it for no reason at all.
# Frozen here at the value belt-plane centring settled on; the nut clearance that
# expression used to guarantee is now an assert (below, once PULLEY_W exists).
# THE FROZEN DATUM IS THE PULLEY TOP — the thrust seat the nut-sweep gap depends on — and
# the band plane DERIVES from it, so a change to BELT_PLANE_DZ or to the pulley column moves
# the band and never the thrust stack. (It used to be frozen the other way round, at -49.0;
# the warning above against deriving it from the NUT still stands.)
# The band has moved twice for the endcap pulleys (user, 2026-09-10): -49.0 -> -51.4 for
# the socket's column, then -> -54.6 when BELT_PLANE_DZ went back up to 8.8. Every belt
# stays aligned with its motor, because MOTOR_BELT_Z rides midway between the planes. The
# cost is that the chassis floor hangs off MOTOR_BELT_Z (-> motor_bank.FLOOR_TOP -> BED_Z
# -> chassis.Z_BOT and the knee-lever mounts): 4.0 deeper than before the endcap.
PULLEY_TOP_Z    = -38.6
SCREW_PULLEY_Z  = PULLEY_TOP_Z - BELT_PLANE_DZ - PULLEY_END_A   # -54.6, LOW-plane band
# THRUST STACK: TWO MR85ZZ (Ø5×8×2.5) in TANDEM per screw, not one bearing.
# Sizing is by STATIC capacity, not life. Per-string tension runs 88–147 N and a
# single MR85's permissible static axial load is ~130 N (C0r ≈ 260 N — a typical
# supplier figure, CONFIRM against the datasheet of whatever gets bought), so
# strings 1 and 5 are over the limit on one bearing. Two clear it at any plausible
# split: 50/50 gives 1.77× margin, a pessimistic 80/20 still gives 1.11×. The
# split is uncertain because two loose MR85s are NOT a ground duplex set — they
# share unevenly, whichever has less internal clearance seating first — but even
# the pessimistic case passes, so the uncertainty does not change the answer.
# The arrangement must be TANDEM (both inner rings stacked, both outer rings
# stacked, load in parallel). Back-to-back/face-to-face would preload the pair
# but then only ONE of them would carry a unidirectional pull — which defeats the
# entire point of the second bearing. And preload is unnecessary anyway: string
# tension is a permanent 88–147 N axial load, one to two orders of magnitude more
# than any deliberate miniature-bearing preload, so the internal clearance is
# taken up and the contact angle fully developed before we do anything.
# The other two failure modes are non-issues here, which is why static capacity
# governs: fatigue, because half a turn per move over a plausible life is only
# ~300k revolutions against millions for L10; and false brinelling, because each
# move rotates 180° and carries every ball onto fresh track — unlike the bridge
# bearing, which only rocks 4.3° and IS a genuine fretting risk.
SUPPORT_BRG_N   = 1
# ONE, not the old TANDEM PAIR — and the pair was never about redundancy. It existed
# because a single MR85's permissible static axial load (~130 N, C0r ~260) sat UNDER the
# 88-147 N per-string tension, so strings 1 and 5 were over the limit on one bearing and
# two were needed to share it. 688ZZ is a much larger bearing: C0r 474-710 N gives ONE
# 237-355 N permissible axial = 1.6-2.4x on the worst string (P0/C0 = 0.21-0.31, inside
# the normal smooth-running band), so the second buys nothing but stack height
# — and stack height is exactly what the taller Tr8 nut needs back; a second 688 does
# not even FIT (it drives the thrust ledge 3.55 into the nut's sweep). Still no preload
# wanted: the string's 147 N is a permanent axial load that has long since taken up the
# internal clearance. ⚠ CONFIRM C0r on the datasheet of whatever is actually bought.
SUPPORT_BRG_OD  = BRG688_OD # Ø16 — 1.4 mm of web each side at the 19.0 in-row pitch
SUPPORT_BRG_ID  = BRG688_ID # Ø8 — the bore the Tr8 screw actually passes through
SUPPORT_BRG_W   = SUPPORT_BRG_N * BRG688_W          # 5.0 — ONE bearing now, not a stack
BRG_LEDGE_T     = 5 * BEAD                          # 4.0 of rail over the outer rings: a 1.6
                                                    # lip + 2.4 of nut band, whose lowest 0.8
                                                    # is the guide-rod sockets' solid floor (user)
# 2 -> 4 beads (user, 2026-09-10). The plate the guide rods stand in was only 1.6 thick,
# so each rod had a printed collar built up round its base for engagement — a free-standing
# ring on a face that prints sideways, i.e. an overhang. Thickening the whole plate to the
# collar's top deletes the collar and gives each rod a 1.6 socket in solid plate instead.
# It does NOT count against the nut — see the nut assert below.
# THE STACK SITS ON THE PULLEYS, and moving it here is what deleted the retaining
# collar. The screw is pulled +Z, so whatever grips it has to bottom against something
# grounded ABOVE; put the bearings on the pulley tops and the PULLEY is that thing.
# The belts do not object, which was the objection: they wrap the toothed band, whose
# top is 1.5 mm below the pulley's own top (measured), so a rail seated on the tops
# clears them. Everything that used to live under the pulley is gone with it — no
# collar, no fight for the 10.7 mm between the bottom flange and the chassis end block,
# and ~9 mm off the screw.
PULLEY_TOP_MAX  = (SCREW_PULLEY_Z + BELT_PLANE_DZ
                   + PULLEY_END_A)                  # -38.6, BOTH SKUs' top (same Z)
SUPPORT_BRG_BOT = PULLEY_TOP_MAX                    # the stack seats straight on it
SUPPORT_BRG_Z   = SUPPORT_BRG_BOT + SUPPORT_BRG_W   # -28.0, thrust ledge underside
# THE NUT'S LOWEST SWEEP. The deepest part of the nut is its Ø10.2 BOSS, and it descends
# INSIDE the thrust ledge's bore (screw_rail.SEAT_LEDGE_D — asserted there, radially), so
# the thing it has to clear vertically is the BEARING at the bottom of that bore, not the
# ledge plane. The old form, NUT_BOT_MIN - (ledge top), stopped being true the moment the
# ledge grew thicker than the gap: it would have blocked a change that collides with nothing.
_NUT_BRG_GAP = NUT_BOT_MIN - SUPPORT_BRG_Z
assert _NUT_BRG_GAP >= 1.0 - 1e-9, (
    f"the nut boss's lowest sweep clears the thrust bearing by only {_NUT_BRG_GAP:.2f} "
    f"(want 1.0): raise NUT_TOP_Z or shorten CARRIAGE_TRAVEL")


# STRING ACCESS CHANNELS (user, 2026-09-10). With two screw rows, a string can no longer be
# threaded into its nut ear from the +X face: the far row is buried behind the near one.
# Instead each string feeds UP from underneath, through a straight vertical channel in the
# rail plate and the chassis floor, already pointing along Z the way it has to leave the ear.
# The channel CANNOT sit under the ear itself: the ear is NUT_HOLE_DX = 8.0 off the screw
# axis, exactly the 688ZZ's outer radius, so a channel there runs through the thrust bearing.
# It stands off sideways instead, as close to the bearing as the seat allows, and the last
# few mm to the ear are a step the builder pushes across with a long thin tool from +X.
# The channel is a HOUSE cut (cadkit.holes.house_hole, user 2026-09-10): a 4.8 x 4.8 rectangle
# with a 45° roof on top, apex toward -X (the endplate's print direction). Its BEARING-FACING end
# is placed so the Ø4.6 barrel passage just touches the Ø16.2 seat bore; the extra size grows
# AWAY from the bearing. There is no wall between channel and seat — only the house breaks in:
#   NEAR row — the ROOF points at its seat. The passage circle nestled in the roof is tangent to
#              the bore, so the apex pokes ~0.95 past it, notching a short arc of the seat round
#              and the ledge's outer edge (r 7.15..8.1): a few % of the thrust annulus.
#   FAR row  — the FLOOR faces the seat, tangent to the bore, inside the seat's own teardrop
#              apex void, so nothing is notched.
# Either way the barrel passes the 688's OD with 0.3 to spare (8.0 + 2.0 + 0.3 = 10.3 < 10.4).
STRING_ACCESS_D = 6 * BEAD                      # 4.8 house width (user)
STRING_ACCESS_H = 6 * BEAD                      # 4.8 house wall height, roof on top (user)
_ACCESS_PASS_R  = STRING_NUT_D / 2 + 0.3        # 2.3 — the Ø4 swaged end's passage, for the standoff


def string_access_x(i: int) -> float:
    """X of string i's vertical access channel, stood off its screw AWAY from the screw axis
    (toward the bearing tangent) — the house_hole axis point; its bearing-facing end sits on the seat bore."""
    seat_r = (SUPPORT_BRG_OD + 0.2) / 2
    toward = 1.0 if screw_x(i) < 0 else -1.0    # away from its own screw, toward X = 0
    if screw_far(i):                            # floor faces the seat, tangent to the bore
        off = seat_r + STRING_ACCESS_D / 2
    else:                                       # roof faces it: apex where the nestled passage
        apex = seat_r + _ACCESS_PASS_R - _ACCESS_PASS_R * 2 ** 0.5   # circle touches the bore
        off = apex + STRING_ACCESS_H            # house_hole's apex is `wall` above its axis
    return screw_x(i) + toward * off
# BOTTOM of the rod: it ends in the pulley's BLIND SOCKET, a hair short of the floor so it
# never bottoms and preloads the formed thread. Both SKUs share the top (PULLEY_TOP_MAX)
# and the socket depth, so the rod ends at the same Z on every station.
SCREW_SOCKET_GAP = 0.2
SCREW_BOT_Z     = PULLEY_TOP_MAX - PULLEY_SOCKET_L + SCREW_SOCKET_GAP   # -42.5
SCREW_LEN       = SCREW_TOP_Z - SCREW_BOT_Z         # 52.3 — the CUT length (see BOM).
# Not a purchasable length: Tr5x1 stock starts at 100 mm, so every screw is cut from a
# longer blank. That is fine because the requirement is a WINDOW, not a number — the
# rod has to clear the nut's top at the top of travel and fill the collar at the
# bottom, and both ends are derived above, so saw accuracy is a non-issue. Ten pieces
# plus nine kerfs need ~500 mm; the BOM's 2×350 mm buy yields 7 per rod, 14 in all.


BELT_PITCH      = 2.0       # GT2 tooth pitch
BELT_TOOTH_H    = 0.75      # tooth height (rounded GT2 profile)
# 5 mm-wide GT2 (open, cut-to-length): the narrowest STANDARD-STOCK GT2 open belt
# (see BOM.md). 6 mm is too wide to clear its neighbour's twist at 9.5 mm pitch;
# 3 mm clears but isn't a standard stock item. The move tension is tiny (~15 N).
BELT_W          = 5.0
BELT_T          = 1.4


# ─────────────────────────────────────────────────────────────────────────
# Motor — MKS SERVO42D on a 48 mm NEMA17 — lies flat, shaft +Y
# ─────────────────────────────────────────────────────────────────────────
MOTOR_SQ        = 42.3
MOTOR_BODY_LEN  = 48.0      # body + PCB run ≈ 70 mm along Y (toward −Y)
MOTOR_PCB_LEN   = 22.0
MOTOR_SHAFT_D   = 5.0
NEMA17_BOLT_SQ  = 31.0
NEMA17_PILOT_D  = 22.0


# ─────────────────────────────────────────────────────────────────────────
# Motor bank — staircase under the strings
# ─────────────────────────────────────────────────────────────────────────
# Each motor's pulley sits on its string's Y line (shaft +Y), body extending −Y
# (toward the player). The motors step along −X by MOTOR_X_STEP so they don't
# overlap. Order is by Y, not by index: the −Y string (the LAST index, heaviest)
# sits CLOSEST to the bridge, the +Y string (index 0, lightest) FURTHEST — so every
# belt, running back to the bridge at its string's Y, stays on the +Y side of the
# closer motors' (−Y-extending) bodies and clears. First motor offset sized so even
# the shortest belt (the −Y string, closest) has a ≥100 mm free span — long enough
# to develop the 90° belt twist gently (≲1°/mm)
# and lie flat at each pulley (a 6 mm toothed belt wants ≳15× width to twist).
MOTOR_X0        = 110.0     # first motor's −X offset from the bridge
MOTOR_X_STEP    = 46.0      # along-X step between motors. Body is 42.3 sq; with
                            # the ±1.5 (3 mm) tension slot the worst-case gap to a
                            # neighbour at the opposite slot extreme is 0.7 mm, so
                            # every motor keeps a full 3 mm (>1 belt tooth) of
                            # independent tension travel. (44 left only 1.7 mm and
                            # the slots overlapped - motors could collide.)
# Belt-plane cascade: a Ø8.4 pulley + belt wrap is wider than the 9.5 mm string
# pitch, so adjacent screw pulleys' belts would collide. Raise the ODD pulleys
# into a second Z plane so neighbours always differ by BELT_PLANE_DZ. Only the
# pulley moves — the motors stay coplanar and the bottom hardware is unchanged.
# 14 beads, not 13, so HALF a plane is a whole 7 beads — the centring below wants
# the half, and it also buys 0.8 more belt-to-belt room at no cost.

# MOTORS SIT MIDWAY BETWEEN THE TWO PULLEY ROWS (user). They used to be coplanar
# with the LOW row (MOTOR_BELT_Z = SCREW_PULLEY_Z), so half the belts ran dead
# flat and the other half climbed a full belt plane — the whole Z change was paid
# by the odd strings alone. Splitting it means every belt rises or falls the SAME
# ±BELT_PLANE_DZ/2, so the twist develops symmetrically and no belt takes the
# full plane. The motors do NOT move to do this: SCREW_LEN grew by exactly half a
# plane above, which drops both pulley rows around the unchanged motor line, so
# motor_bank's floor/bed (derived from here) and the chassis are untouched.
MOTOR_BELT_Z    = SCREW_PULLEY_Z + BELT_PLANE_DZ / 2


def screw_pulley_z(i: int) -> float:
    # raise alternate pulleys a belt-plane so neighbours never collide; phased off the
    # −Y end (last index on the base plane) so the SAME physical pulleys rise
    return SCREW_PULLEY_Z + ((N_STRINGS - 1 - i) % 2) * BELT_PLANE_DZ

def motor_pos(i: int):
    """Return (x, y, z) of string i's motor pulley (on the string's Y line). The −Y
    string (last index) is closest to the bridge, stepping out toward +Y (see above)."""
    return (-(MOTOR_X0 + (N_STRINGS - 1 - i) * MOTOR_X_STEP), string_y(i), MOTOR_BELT_Z)


# FAR-ROW BELTS vs NEAR-ROW PULLEYS (see BELT_PLANE_DZ). Each far-row belt passes the near
# row 2*SCREW_ROW_DX along its run, where its centreline has already climbed that fraction
# of the DZ/2 up to the motor plane; its section reaches the HALF-DIAGONAL above that
# (upper bound over every twist angle). Worst case is the SHORTEST run, where the climb is
# steepest. The overlap gate only sees this with --full, so it is asserted here.
_BELT_HALF_DIAG = (BELT_W ** 2 + BELT_T ** 2) ** 0.5 / 2
_BELT_PLANE_CLR = min(
    BELT_PLANE_DZ - PULLEY_BOT - _BELT_HALF_DIAG
    - (BELT_PLANE_DZ / 2) * (2 * SCREW_ROW_DX) / abs(screw_x(i) - motor_pos(i)[0])
    for i in range(N_STRINGS) if screw_far(i))
assert _BELT_PLANE_CLR >= 0.4 - 1e-9, (
    f"far-row belts clear the near-row pulleys' lower flange by only {_BELT_PLANE_CLR:.2f} "
    f"(want 0.4): raise BELT_PLANE_DZ")


# ─────────────────────────────────────────────────────────────────────────
# Bridge bearings — turn each string 90° (vertical rise → −X speaking length).
# One small ball bearing PER STRING on a shared axle (axis Y): a freely-spinning
# bearing keeps the bend near-frictionless so the two sides' tensions equalize
# (a fixed surface would mismatch them ~37% at 90° and cause tuning hysteresis).
# ─────────────────────────────────────────────────────────────────────────
# 688ZZ (Ø8×16×5) — the SAME part as the ten screw thrust bearings (user, 2026-09-10:
# one bearing SKU everywhere, since the Tr8 screw already forces a Ø8 bore), so the bridge
# axle goes Ø8 with it. The knee-lever and pedal axles follow in their own rounds, and the nut
# wrap rod is now the SAME Ø8 x BRIDGE_AXLE_L shaft (user) — one shaft SKU at both ends.
#
# (history) 695ZZ (Ø5×13×4) was the one bearing before this, and its Ø5 bore made the
# bridge axle, both lever axles and the nut wrap rod one stock shaft.
#
# THE 693ZZ IT REPLACES WAS OVER ITS RATING. The string turns 90° here — level in
# from the nut, straight down to the carriage beneath — so each bearing carries
# sqrt(2)×147 = 208 N permanently, against a 693ZZ static rating of 177 N. C0 is the
# BRINELLING threshold: the races dent and the bearing stops doing its only job,
# letting the two sides of the string equalise. 695ZZ was 346 N -> 1.66×; 688ZZ
# publishes C0r 474-710 N -> 2.3-3.4×.
#
# WHY Ø16 FITS NOW. The OD used to be capped at 13 by the carriage's ball cage under
# the bearing (the string rides the OD, so the axle is pinned at STRING_Z - OD/2 and a
# bigger bearing reaches lower). The carriage is gone — the nut is the carriage — so the
# bearing's underside (STRING_Z - OD = 0) only has to clear the nut and screw tops below
# it, which the asserts under these constants check. In Y it is 5 wide in the 9.5 lane,
# which leaves the comb fingers 3.7.
BRIDGE_BEARING_OD = BRG688_OD   # 16 — 688ZZ; the string rides the OD
BRIDGE_BEARING_W  = BRG688_W    # 5 along the axle (Y)
BRIDGE_AXLE_D     = BRG688_ID   # Ø8 shared axle (axis Y), the 688's bore
BRIDGE_BEARING_Z  = STRING_Z - BRIDGE_BEARING_OD / 2     # axle/bearing centre (8)
_BRIDGE_BRG_BOT   = STRING_Z - BRIDGE_BEARING_OD         # 0, the bearing's underside
assert _BRIDGE_BRG_BOT - NUT_TOP_MAX >= 1.0, (
    f"the bridge bearing's underside clears the nut's top of travel by only "
    f"{_BRIDGE_BRG_BOT - NUT_TOP_MAX:.2f}")
assert _BRIDGE_BRG_BOT - SCREW_TOP_Z >= 1.0, (
    f"the bridge bearing's underside clears the leadscrew tops by only "
    f"{_BRIDGE_BRG_BOT - SCREW_TOP_Z:.2f}")
# The string rises vertically from the anchor (at BRIDGE_X) tangent to the
# bearing's +X extent, wraps 90° over the top, then leaves −X along the top. So
# the bearing centre sits OD/2 to −X of the anchor line.
BRIDGE_AXLE_X     = BRIDGE_X - BRIDGE_BEARING_OD / 2     # bearing/axle centre X
# WIDTH DATUM (not the axle's span any more -- see BRIDGE_AXLE_L). chassis.Y_HI,
# knee_lever.MORT_Y_END and screw_rail.ACROSS are measured from this.
BRIDGE_AXLE_Y     = STRING_FIELD_W / 2 + 12 * BEAD  # 52.35
BRIDGE_ARM_W      = 6 * BEAD  # 4.8 bridge-endplate bearing-arm / edge-web thickness (Y); the
                            # screw rail widens by this so the rib overlaps it cleanly
# THE AXLE'S TWO ENDS. It is a plain ground shaft with no shoulder — it has to be, since
# it threads through 10 bearings and 11 comb fingers in one pass — so both ends are held
# by the STRUCTURE, and it goes in from +Y (user):
#   -Y  the +Y arm's opposite number is BLIND. That 1.6 wall IS the -Y hard stop.
#   +Y  the shaft ends FLUSH with the +Y arm's outer face, and the optical strip's +X
#       head turns over the endplate 0.75 further out (optical_pickup.HEAD_Y0, which
#       derives from this same face). The board's underside sits 2.34 BELOW the shaft's
#       crown, so once it is screwed down the shaft cannot travel +Y without driving its
#       own crown into FR4 — a positive stop, from a part that is already there and
#       already fastened. That replaces the M2 grub that used to close this direction:
#       one less fastener, one less thing to back out, and nothing to reach in and turn.
# Install order, and it is now load-bearing: bearings and fingers aligned → shaft in from
# +Y → optical strip on. Same trick the guide rods use at the other end of this part.
# ── THE AXLE IS A PURCHASED LENGTH NOW, AND IT DRIVES THE ARMS ──────────────
# It used to run the other way: the arms sat at BRIDGE_AXLE_Y and the shaft came out
# 107.9 long, which is not a length anyone sells. Locking the SKU and deriving the arms
# from it makes the shaft a BOM line instead of an offcut.
#
# THIS SPLITS A CONSTANT THAT WAS DOING TWO JOBS. BRIDGE_AXLE_Y is the axle's support
# half-span AND the instrument's width datum -- chassis.Y_HI, knee_lever.MORT_Y_END and
# screw_rail.ACROSS all hang off it. Shortening the shaft must not narrow the guitar, so
# BRIDGE_AXLE_Y keeps the width job and the ARMS move to their own constant. Only the
# upper block and the optical PCB that references its faces are affected (user).
#
# NOTHING IS LOST AT THE ENDS. Shaft and arms shorten together, so both engagements come
# out exactly as before -- 3.20 into the blind -Y bore, 4.80 through the +Y arm. What
# shrinks is the margin outboard of the string field, 9.60 -> 5.65, and nothing lives
# there but the arm itself.
BRIDGE_AXLE_L     = 100.0                               # the Ø8 shaft, as bought
BRIDGE_AXLE_END_W = MIN_WALL_2P                         # 1.6, the -Y blind wall = the stop
BRIDGE_ARM_OUT    = (BRIDGE_AXLE_L + BRIDGE_AXLE_END_W) / 2   # 50.80, the arms' outer faces
BRIDGE_ARM_Y      = BRIDGE_ARM_OUT - BRIDGE_ARM_W / 2   # 48.40, the arm centres
BRIDGE_AXLE_Y0    = -BRIDGE_ARM_OUT + BRIDGE_AXLE_END_W # -49.20, against the blind wall
BRIDGE_AXLE_Y1    = BRIDGE_ARM_OUT                      # +50.80, flush with the arm face
assert BRIDGE_AXLE_Y1 - BRIDGE_AXLE_Y0 == BRIDGE_AXLE_L, "the axle is not its own SKU length"
assert BRIDGE_ARM_Y - BRIDGE_ARM_W / 2 > STRING_FIELD_W / 2, (
    "the bearing arms have come inboard of the string field")

# ── Keyhead nut-block hardware → ENDPLATE_W (BOTH ends + bridge base) ────────
# The endplate THICKNESS in X is not a round number -- it's exactly what the string-
# termination hardware needs. Laid out -X from the break dowel (which sits at the scale
# endpoint NUT_BLOCK_X, the +X-most part) the X stack is: a +X strength lip, the dowel,
# the run to the NEAR clamp row, the X-stagger to the FAR clamp row, then a wall behind
# the far clamp's heat-set insert (its OD is the -X-most hardware). BOTH endplates inherit
# this width (the bridge centres it on the bearing axle) and the drivetrain base spans it,
# so editing any buffer here resizes both ends together -- never a hardcoded tip. The
# keyhead nut block (nut_block.py) reads these same constants to place its features.
# These four ARE cadkit's M4 spec — read from it rather than repeated. They used to be
# literals whose comment pointed at "freecad/fasteners.py", a path the cadkit migration
# retired, so the numbers had already outlived their own citation. It matters more than
# tidiness here: ENDPLATE_W is computed from NUT_INSERT_D, so BOTH endplates' width (and
# with it the bridge's whole X datum chain) hangs off a heat-set insert's diameter. If
# cadkit ever re-specs M4, that should follow by itself instead of silently not.
NUT_INSERT_D    = M4.insert_pilot_d     # 6.0  — heat-set insert install Ø
NUT_INSERT_L    = M4.insert_l           # 5.0
NUT_SCREW_D     = M4.shaft_clr_d        # 4.4  — set-screw shaft clearance
NUT_SCREW_L     = M4.screw_l            # 10.0. The boss is NOT one screw tall: the
                                # insert sinks to a small gap off the string (nut_block.INSERT_GAP)
                                # and this screw's surplus length stands PROUD of the top surface.
NUT_PIN_D       = 2.0           # Ø2 break-dowel NOMINAL diameter
NUT_PIN_L       = 4.0           # Ø2×4 dowel length (axis Y)
NUT_PIN_CLR     = 0.4           # clearance perimeter around the dowel in its pocket (drop-in fit,
                                # all faces -- the seat is Ø+2*clr and length+2*clr)

BREAK_PX_BUF    = 4.0           # +X of the dowel: the lip the deck/pickup plate seat against
DOWEL_SCREW_RUN = 8.0           # dowel -> NEAR clamp row centre (the break run to the clamp)
SCREW_ROW_GAP   = 8.0           # NEAR -> FAR clamp row centre (rows stagger so inserts keep Y pitch)
SCREW_NX_WALL   = 3 * BEAD      # 2.4 solid wall -X behind the far insert's OD (strength)

ENDPLATE_W = (BREAK_PX_BUF + DOWEL_SCREW_RUN + SCREW_ROW_GAP
              + NUT_INSERT_D / 2 + SCREW_NX_WALL)            # = 25.0
# THE KEYHEAD IS THICKER THAN THE BRIDGE, and the two are now separate numbers.
# ENDPLATE_W above is the BRIDGE's (and the shared base's) 25.4, frozen: the whole
# changer end is built on it. The keyhead needs more, and for a reason that only
# exists at that end -- the WRAP CAPSTAN (nut_block) spends X on the rod and its
# threading bay, and the clamp inserts behind it still have to stagger across TWO
# rows to keep O6 pockets apart at a 6.5 string pitch. One row cannot be made to
# fit: even perfectly spaced it leaves 0.5 mm of wall. So the keyhead grows -X, away
# from the strings -- the break edge (the scale "0") does not move, only the block's
# back face -- and the bridge is left exactly where it is (user).
KEYHEAD_W  = 36 * BEAD                              # 28.8 = 25.4 + 5.0 of clamp room,
                                                    # less the 1.6 reclaimed at the front
# ...AND ITS FRONT BUFFER IS ITS OWN NUMBER TOO (user: decouple the endplates). The
# keyhead needs far less material +X of the break dowel than BREAK_PX_BUF's 4.0 -- just
# enough to grow a 45 deg up to the dowel's MIDPOINT, since a dowel cradled to its own
# centreline can only lift, not roll out, and the string lies across it:
#
#     seat +X tangent          PIN_SEAT_D/2 = 1.4
#     45 deg rise to midpoint                 1.0
#                                       ---> 2.4
#
# BREAK_PX_BUF stays 4.0 because ENDPLATE_W is computed from it and that sets the BRIDGE
# base -- this is the same split KEYHEAD_W itself needed. The dowel does not move (it is
# the scale "0", and NUT_BLOCK_X puts the block's local origin exactly there), so the
# scale length is untouched; what shortens is the lip that protruded past it.
# FLUSH WITH THE ENDPLATE'S +X FACE (user). At 2.4 the nut block stopped 1.4 short of
# it and still carried 0.8 of its own material +X of the inserts -- and BOTH are
# overhangs in a -X -> +X build, printed out over the insert slot with nothing behind
# them. Nothing needs to be there: the dowel is carried by the INSERT now, not by the
# block, so the insert can run right out to the face and bear against the deck panel
# that butts it.
KEYHEAD_PX_BUF = 19 * BEAD / 4                      # 3.8 = KH_X - NUT_BLOCK_X, flush

# THE BRIDGE BASE IS NO LONGER ENDPLATE_W WIDE. That width is the KEYHEAD's, derived
# from ITS nut-block hardware, and the bridge merely shared it back when ten screws sat
# on one line 8 mm off the axle. With the screws in TWO ROWS the bridge end has to host
# both rows and both guide-rod lines, so its span is DERIVED from the rows and centred
# on the BEARING TANGENT (BRIDGE_X) instead of on the axle — the rows are symmetric
# about the tangent, so anything centred elsewhere wastes width on one side and runs
# short on the other. ENDPLATE_W keeps its keyhead job untouched.
#
# Sized to the GUIDE ROD, not to the nut flange. The flange tip reaches further (-23.0),
# but the nut SWEEPS in Z through the changer room — it wants a slot, not containment,
# and the old single-row nut already overhung this face (-17.05 against -16.50). The rod
# socket is the thing that must live in solid material. Containing the flange as well
# cost 1.5 mm per side, and every mm here comes straight off the DECK, whose +X end is
# flush with this face (top_plate.PX0).
# The binding feature is the BEARING SEAT'S TEARDROP, not the guide rod. Every Z bore
# in this part runs sideways to its -X build, so each is a teardrop, and a teardrop's
# APEX stands r*1.4143 from the axis — not r. The Ø16.2 seat therefore reaches 11.46
# from the screw axis, further than the guide rod's bore does at NUT_HOLE_DX + 2.16.
# At the old 23.10 face the apex stood 0.36 PROUD of it, i.e. the seat broke out through
# the -X face. Sized from whichever of the two reaches further, plus a 2-bead wall.
_BRG_TEARDROP = (SUPPORT_BRG_OD + 0.2) / 2 * 1.4143            # 11.46, seat apex
_ROD_TEARDROP = (GUIDE_ROD_D + GUIDE_ROD_FIT) / 2 * 1.4143     # 2.16, rod-bore apex
BRIDGE_BASE_HALF = (SCREW_ROW_DX
                    + max(_BRG_TEARDROP, NUT_HOLE_DX + _ROD_TEARDROP)
                    + MIN_WALL_2P)                             # 25.06
BRIDGE_BASE_X0 = BRIDGE_X - BRIDGE_BASE_HALF        # -23.1  (-X face)
BRIDGE_BASE_X1 = BRIDGE_X + BRIDGE_BASE_HALF        # +23.1  (+X face)


# ─────────────────────────────────────────────────────────────────────────
# String gauges → the nut break inserts are GAUGED to these so the string TOPS
# sit coplanar at STRING_Z. Reprint the (bolt-on) nut block to switch sets.
# Index i = string (i+1), low to high: index 0 = string 1 (lightest, +Y); index 9 =
# string 10 (heaviest, −Y player side). Edit GAUGES_C6_IN (or swap in another set in
# the same string-1→10 order) and rebuild to regenerate the endplate for that set.
# ─────────────────────────────────────────────────────────────────────────
GAUGES_E9_IN = (.013, .015, .011, .014, .017, .020, .026, .030, .034, .038)  # str 1→10
GAUGES_C6_IN = (.015, .014, .017, .020, .024, .030, .036, .042, .054, .070)  # str 1→10
STRING_GAUGE = tuple(g * 25.4 for g in GAUGES_C6_IN)            # mm, index 0..9 = str 1..10 (C6)

# THE HEAVIEST GAUGE THE KEYHEAD IS BUILT TO TAKE -- the ENVELOPE, not the demo SET above.
# STRING_GAUGE is what this model happens to be strung with; a printed part has to clear
# whatever a player may fit, or a heavier set means a reprint. Published pedal steel gauge
# charts put the lowest wound string at up to .080: steelguitar.com's string-gauge chart
# gives ".070 - .080 Wound" for A and ".072 - .080" for G# (b0b.com's gauge guide tops out
# lower, G#/Ab ".072 or .074"). Only the outermost slot, string 10, ever carries it.
GAUGE_MAX_IN     = .080
STRING_GAUGE_MAX = GAUGE_MAX_IN * 25.4                          # 2.032 mm
assert STRING_GAUGE_MAX >= max(STRING_GAUGE), (
    "the demo string set is heavier than the gauge envelope the keyhead is built to take")

# Nut block sits with its break edge (the open-string scale endpoint) here.
NUT_BLOCK_X  = -MOUNTING_SPAN


# ─────────────────────────────────────────────────────────────────────────
# Fits / fasteners
# ─────────────────────────────────────────────────────────────────────────
FIT_CLR         = 0.30      # slip-fit clearance (e.g. guide rod in its bore)
M3_CLR_D        = 3.4       # M3 clearance hole (NEMA17 bolt pattern)
BOOL_OVERSHOOT  = 0.5       # extra length on cutting tools so faces clear cleanly
