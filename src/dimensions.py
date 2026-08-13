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
MR85_OD, MR85_ID, MR85_W = 8.0, 5.0, 2.5
BELT_PLANE_DZ   = 14 * BEAD  # 11.2 — the two screw-pulley planes' Z separation.
                             # Declared here rather than with the belts because the
                             # pulleys' STAGGER SPACER is exactly this, and the thrust
                             # stack sits on top of that.


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
NUT_AF          = 8.5       # across flats (Y) — THE lane-critical dimension
NUT_FLANGE_L    = 18.1      # long axis (X)
NUT_FLANGE_T    = 3.2
NUT_BOSS_D      = 8.0
NUT_BOSS_L      = 6.6
NUT_H           = NUT_FLANGE_T + NUT_BOSS_L                            # 9.8
NUT_HOLE_D      = 3.0       # the ears' through-holes (M2 screws pass with room)
NUT_HOLE_DX     = 6.5       # ± from the axis
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
SCREW_OD        = 5.0       # Ø5, single-start, 1 mm lead.
# WHY Ø5 AND NOT THE USUAL Tr8 — do not "upgrade" this. The ten screws sit on one X
# line at the STRING_PITCH (9.5), so each screw's NUT has to live inside a 9.5 mm lane.
# NUT_FLANGE_OD is already 9.0 in that lane (0.5 to its neighbour). A Tr8 nut — even a
# plain round one, let alone the usual Ø22 flanged 3D-printer part — cannot fit. The
# string pitch picks the screw, and it picks a size BELOW the ISO/DIN 103 trapezoidal
# series (which starts at Tr8), so this is a specialty part, not a catalogue one: see
# the BOM row for what that means for sourcing.
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
SCREW_PITCH     = 1.0       # Tr5x1: 1 mm pitch, single start
FORM_MINOR      = 4.2       # printed ridge Ø
FORM_MAJOR      = 4.8       # printed groove Ø
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
TOP_BRG_Z0      = NUT_TOP_Z + SCREW_RUNOUT + 2 * BEAD   # -3.2, seat mouth
TOP_BRG_Z1      = TOP_BRG_Z0 + MR85_W                   # -0.7
SCREW_TOP_Z     = TOP_BRG_Z1                            # the rod ends flush in that bearing


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
GUIDE_ROD_D     = 3.0       # Ø3 g6 precision shaft (shared with BRIDGE_AXLE_D)
GUIDE_ROD_FIT   = 0.05      # SNUG PRESS. Not zero: at zero the socket is drawn the
                            # rod's own Ø, which is not a hole you can install into,
                            # and coincident cylinders make the boolean unreliable
                            # too. 0.05 is the same snug the old rod sockets used.

# The bridge / string anchor sits at X=0; the screw can't occupy that spot, so
# it is offset −X by ANCHOR_DX and the carriage reaches over to the anchor.
BRIDGE_X        = 0.0
SCREW_X         = -8.0      # all 10 vertical screws sit on this X line
ANCHOR_DX       = BRIDGE_X - SCREW_X    # anchor is +X of the screw (8 mm)
# The two ears, as global X lines. Everything that used to be a carriage feature is
# now one of these.
STRING_ANCHOR_X = SCREW_X + NUT_HOLE_DX     # -1.5, the +X ear: ball end under it
GUIDE_ROD_X     = SCREW_X - NUT_HOLE_DX     # -14.5, the -X ear: rides the rod


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
# ONE PART, TWO ORIENTATIONS (user). The two pulley planes are BELT_PLANE_DZ apart
# and the thrust stack is ONE plane for all ten, so the obvious answer was two parts —
# a short one and a tall one. It is better to make a single part that FLIPS, and the
# relation that allows it is small: turning it over changes how far the toothed band
# sits below whichever end is up, so all that is needed is
#
#     (band → end B) − (band → end A) = BELT_PLANE_DZ
#
# A pilot boss at BOTH ends, and a plain column on the B side to make up the difference.
# Boss-A up gives the high plane, flipped gives the low one, and the envelope is
# identical either way up.
#
# The payoff is ENGAGEMENT. The pulley carries the full 147 N of string pull through
# its pilot thread now — it is the retaining collar — and the two-part scheme gave the
# high-plane half only 8.8 mm of it against the low half's 20.0. One part gives every
# station 20.8.
#
# END A costs nothing to keep as it is: 4.8 is exactly what the old high-plane pulley
# already measured from its top face to its band, so the thrust plane, the nut, the
# travel and the bridge-bearing gap above all stay put. END B is where the column goes.
PULLEY_GAP      = 5.4               # toothed gap = the 5 mm GT2 belt + 0.4
PULLEY_CONE_A   = (PULLEY_FLANGE_OD - PULLEY_OD) / 2        # 1.3, flange cone at end A
PULLEY_SPACER_D = 9 * BEAD          # 7.2 column: it has to slip past the NEIGHBOUR's
                                    # Ø11 flange at the 9.5 pitch, so 7.6 is the ceiling
PULLEY_CONE_B   = (PULLEY_FLANGE_OD - PULLEY_SPACER_D) / 2  # 1.9, flange cone at end B
PULLEY_BOSS_D   = 7 * BEAD          # 5.6 pilot at each end: lands on the bearings' INNER
                                    # rings only (their OD is ~6.3). Anything wider would
                                    # drag the stationary outer ring against a pulley that
                                    # turns with the screw.
PULLEY_BOSS_H   = 1 * BEAD          # 0.8
PULLEY_BOSS_TPR = 1 * BEAD          # 0.8, the 45° step from boss to column at end B
# PRINT ORIENTATION IS LOAD-BEARING HERE, not cosmetic. Printed COLUMN-END-DOWN every
# outward step is 45° or less (boss → taper → column → taper → flange → band, then
# Ø11 → Ø5.6 at end A, which is inward and free). Printed the other way up, the boss
# meeting the flange is a 2.7 mm unsupported annulus, and tapering that away would push
# the band 1.4 lower — moving the thrust plane, raising the nut, and eating into the
# clearance under the bridge bearing. Ø5.6 on the bed for a 20.8 part wants a brim.
PULLEY_END_A    = PULLEY_GAP / 2 + PULLEY_CONE_A + PULLEY_BOSS_H            # 4.8
PULLEY_END_B    = PULLEY_END_A + BELT_PLANE_DZ                              # 16.0
PULLEY_COL_H    = (PULLEY_END_B - PULLEY_GAP / 2 - PULLEY_CONE_B
                   - PULLEY_BOSS_TPR - PULLEY_BOSS_H)                       # 9.8
PULLEY_L        = PULLEY_END_A + PULLEY_END_B                               # 20.8
                                    # backs the hole from below and the hub from above
# ─────────────────────────────────────────────────────────────────────────
# BOTTOM OF THE SCREW — drive pulley, thrust bearings, retaining collar (axis Z)
# ─────────────────────────────────────────────────────────────────────────
# THE PULLEY PLANE IS A ROOT DATUM — DO NOT DERIVE IT FROM THE NUT. motor_bank's
# floor and the whole belt plane hang off it (see MOTOR_BELT_Z), so when the H-nut
# moved the nut's lowest point 7.8 mm down, the old `NUT_BOT_MIN - 25·BEAD` form
# would have dragged the entire motor bank down with it for no reason at all.
# Frozen here at the value belt-plane centring settled on; the nut clearance that
# expression used to guarantee is now an assert (below, once PULLEY_W exists).
SCREW_PULLEY_Z  = -49.0     # drive pulley, near the bottom of the screw
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
SUPPORT_BRG_N   = 2
SUPPORT_BRG_OD  = MR85_OD   # Ø8 is what fits the 9.5 mm pitch inline
SUPPORT_BRG_ID  = MR85_ID
SUPPORT_BRG_W   = SUPPORT_BRG_N * MR85_W            # 5.0 — the STACK, not one bearing
BRG_LEDGE_T     = 2 * BEAD                          # 1.6 of rail over the outer rings
# THE STACK SITS ON THE PULLEYS, and moving it here is what deleted the retaining
# collar. The screw is pulled +Z, so whatever grips it has to bottom against something
# grounded ABOVE; put the bearings on the pulley tops and the PULLEY is that thing.
# The belts do not object, which was the objection: they wrap the toothed band, whose
# top is 1.5 mm below the pulley's own top (measured), so a rail seated on the tops
# clears them. Everything that used to live under the pulley is gone with it — no
# collar, no fight for the 10.7 mm between the bottom flange and the chassis end block,
# and ~9 mm off the screw.
PULLEY_TOP_MAX  = (SCREW_PULLEY_Z + BELT_PLANE_DZ
                   + PULLEY_END_A)                  # -33.0, the HIGH plane's boss top
SUPPORT_BRG_BOT = PULLEY_TOP_MAX                    # the stack seats straight on it
SUPPORT_BRG_Z   = SUPPORT_BRG_BOT + SUPPORT_BRG_W   # -28.0, thrust ledge underside
_NUT_PULLEY_GAP = NUT_BOT_MIN - (SUPPORT_BRG_Z + BRG_LEDGE_T)
assert _NUT_PULLEY_GAP >= 1.0 - 1e-9, (
    f"the nut's lowest sweep clears the thrust ledge by only {_NUT_PULLEY_GAP:.2f} "
    f"(want 1.0): raise NUT_TOP_Z or shorten CARRIAGE_TRAVEL")
# BOTTOM of the rod: it simply ends inside the drive pulley — there is nothing below.
# The rod ends at the pulley's far boss — the same depth either way up, because the
# flip leaves the envelope unchanged.
SCREW_BOT_Z     = (SCREW_PULLEY_Z + BELT_PLANE_DZ
                   - PULLEY_END_B)                  # -53.8
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


# ─────────────────────────────────────────────────────────────────────────
# Bridge bearings — turn each string 90° (vertical rise → −X speaking length).
# One small ball bearing PER STRING on a shared axle (axis Y): a freely-spinning
# bearing keeps the bend near-frictionless so the two sides' tensions equalize
# (a fixed surface would mismatch them ~37% at 90° and cause tuning hysteresis).
# ─────────────────────────────────────────────────────────────────────────
# 695ZZ (Ø5×13×4) — ONE bearing for the changer AND the levers (user), and its Ø5
# bore is what makes the bridge axle, both lever axles and the nut wrap rod ONE
# stock shaft.
#
# THE 693ZZ IT REPLACES WAS OVER ITS RATING. The string turns 90° here — level in
# from the nut, straight down to the carriage beneath — so each bearing carries
# sqrt(2)×147 = 208 N permanently, against a 693ZZ static rating of 177 N. C0 is the
# BRINELLING threshold: the races dent and the bearing stops doing its only job,
# letting the two sides of the string equalise. 695ZZ is 346 N -> 1.66×.
#
# WHY NOT BIGGER: OD is capped by the VERTICAL gap between STRING_Z and the
# carriage's ball cage, because the string rides the OD so the axle is pinned at
# STRING_Z - OD/2. Ø16 needs the whole 8 mm of slack under the carriage; Ø13 needs
# 5 and leaves 3. Y is not the constraint (4 wide in a 9.5 lane) and neither is X.
BRIDGE_BEARING_OD = 13.0    # 695ZZ; string rides a groove in the OD
BRIDGE_BEARING_W  = 4.0     # along the axle (Y) — unchanged, so the comb fingers stay 5.5
BRIDGE_AXLE_D     = 5.0     # shared axle (axis Y) — the ONE Ø5 shaft
BRIDGE_BEARING_Z  = STRING_Z - BRIDGE_BEARING_OD / 2     # axle/bearing centre (12)
# The string rises vertically from the anchor (at BRIDGE_X) tangent to the
# bearing's +X extent, wraps 90° over the top, then leaves −X along the top. So
# the bearing centre sits OD/2 to −X of the anchor line.
BRIDGE_AXLE_X     = BRIDGE_X - BRIDGE_BEARING_OD / 2     # bearing/axle centre X
BRIDGE_AXLE_Y     = STRING_FIELD_W / 2 + 12 * BEAD  # 9.6             # axle/support half-span
BRIDGE_ARM_W      = 6 * BEAD  # 4.8 bridge-endplate bearing-arm / edge-web thickness (Y); the
                            # screw rail widens by this so the rib overlaps it cleanly

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
BRIDGE_BASE_X0 = BRIDGE_AXLE_X - ENDPLATE_W / 2     # -16.5  (-X inboard face)
BRIDGE_BASE_X1 = BRIDGE_AXLE_X + ENDPLATE_W / 2     #  8.5   (+X outer tip)


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

# Nut block sits with its break edge (the open-string scale endpoint) here.
NUT_BLOCK_X  = -MOUNTING_SPAN


# ─────────────────────────────────────────────────────────────────────────
# Fits / fasteners
# ─────────────────────────────────────────────────────────────────────────
FIT_CLR         = 0.30      # slip-fit clearance (e.g. guide rod in its bore)
M3_CLR_D        = 3.4       # M3 clearance hole (NEMA17 bolt pattern)
BOOL_OVERSHOOT  = 0.5       # extra length on cutting tools so faces clear cleanly
