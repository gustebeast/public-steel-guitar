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
CARRIAGE_TRAVEL = 2 * DL_OPEN + 2.0    # ≈10 mm; open sits ~DL_OPEN up from slack

# The carriage's REST HEIGHT is set by the BRIDGE BEARING, not by the screw. Its
# ball-cage top must stay 1.0 under the bearing's underside (STRING_Z − OD), which
# is what caps the bearing OD in the first place. Spelled here rather than imported
# from carriage.py (that module imports THIS one), and ASSERTED there against the
# live carriage geometry — see carriage._BRG_GAP, which has already caught one
# regrid that quietly ate 0.4 of this gap.
# It used to read `SCREW_TOP_Z − 13.4`, which had the dependency backwards: the
# screw's length was setting where the carriage lived. Now the carriage is the
# datum and the screw is sized to reach it.
CARRIAGE_NOM_Z  = -11.0     # default = TOP of travel (travel runs DOWNWARD from here)
CARRIAGE_THICK  = 12.0      # carriage body band in Z; single-sourced here because the
                            # nut placement and the screw length both need it (carriage.py
                            # re-exports it as THICK)


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
# MOUNTING — flange DOWN clamped flat under the carriage's BOTTOM FACE, boss UP
# into a Y-OPEN RECESS in the carriage, two M2 screws up through the ears.
#   • The load direction picks the face. String pulls the carriage +Z, so the
#     nut has to pull it back -Z: the nut's DOWN-facing surface must bear on the
#     carriage's UP-facing surface, or fasteners must span the gap. The original
#     "flange-down against the bottom face" seat had those two backwards — it
#     could only ever have held by the press fit's friction. Bolted ears put the
#     pull in tension, which is an ordinary joint and needs no seat at all.
#   • The boss CANNOT go in a BORE. Ø8 plus clearance in an 8.8 wide carriage
#     leaves ≤0.3 mm side walls — under the one-bead floor, and the carriage
#     prints on its -X face, so a wall thin in Y is one bead or nothing. Its
#     recess is therefore Y-OPEN, a channel straight through the part's width,
#     which has no side walls to be thin. (The old Ø7 pocket only worked because
#     the boss had been turned down on a lathe.)
#   • The boss CANNOT hang below the carriage either, and THAT is what forces a
#     recess rather than simply inverting the nut. The drive pulleys alternate
#     between two Z planes to fit the 9.5 lane, and the RAISED plane's top sits at
#     -31.4. A nut hanging its full 9.8 reaches -36.8 at the bottom of travel and
#     drives into five of the ten pulleys. Recessed, only the 3.2 flange hangs and
#     the nut stops at -30.2. The carriage cannot move up to dodge it: its ball
#     cage already clears the bridge bearings by exactly the 1.0 minimum.
#   • The flats do no anti-rotation work, which is just as well — an 8.5 flat in
#     an 8.8 carriage leaves 0.15 mm of wall to react torque against.
NUT_TOP_MAX     = (CARRIAGE_NOM_Z - CARRIAGE_THICK / 2
                   + NUT_BOSS_L)                                       # -10.4, at TOP of travel
NUT_BOT_MIN     = (CARRIAGE_NOM_Z - CARRIAGE_TRAVEL
                   - CARRIAGE_THICK / 2 - NUT_FLANGE_T)                # -30.2, at BOTTOM of travel


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
# TOP: the screw only has to clear the NUT, not the carriage (user) — it used to run
# all the way to the carriage's top, which left 12.4 mm of thread above the highest the
# nut ever reaches. The nut's top is now its boss top, sitting NUT_BOSS_L up inside the
# carriage's recess. RUNOUT is pure insurance for build tolerance.
SCREW_RUNOUT    = 3 * BEAD                          # 2.4 proud of the nut at top of travel
SCREW_TOP_Z     = NUT_TOP_MAX + SCREW_RUNOUT        # -14.6


# ─────────────────────────────────────────────────────────────────────────
# Guide rod (anti-rotation) — axis Z, on the +X (cap) side of the screw, BELOW
# the stringing window. The carriage reaches it with a low FOOT (column + leg
# hanging under the plate), keeping the whole window clear for string access.
# Both rod seats and both hard stops are cap-backed ledges on the endplate —
# no spanning bar, so the endplate prints with no overhang.
# ─────────────────────────────────────────────────────────────────────────
GUIDE_ROD_D     = 2.5
GUIDE_ROD_DX    = 17 * BEAD  # 13.6 screw→rod offset: rod X = SCREW_X + DX = +4.95 (global). Moved +X
                            # (user) so the rod's metal −X edge clears the anchor-cage OPENING
                            # (POST_X1H, global +2.1) by 1.6 mm — was only 0.15, and that gap was
                            # what pinned the guide foot LOW. INSTALL (top-down): the rod drops
                            # through the stop bar, the carriage's closed bore, into the blind
                            # socket — friction-held top + bottom; the closed bore captures a loose
                            # carriage (carriage in place → rod drops in → screw threads in).
GUIDE_FOOT_DZ   = 3 * BEAD  # 2.4 foot TOP from the carriage centre. Now at the NUT LEVEL (user): the
                            # guide bore rides in the body's own z-band (−6..+2, just below the
                            # cage bottom 2.5), NOT on a hanging column — the carriage drops ~16 mm
                            # in Z (a much stiffer part) and the bore ties straight into the body.
GUIDE_FOOT_H    = 8.0       # foot height = guide-bore engagement length (rod engagement)

# The bridge / string anchor sits at X=0; the screw can't occupy that spot, so
# it is offset −X by ANCHOR_DX and the carriage reaches over to the anchor.
BRIDGE_X        = 0.0
SCREW_X         = -8.0      # all 10 vertical screws sit on this X line
ANCHOR_DX       = BRIDGE_X - SCREW_X    # anchor is +X of the screw (8 mm)

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
PULLEY_BORE_SCREW = SCREW_OD + 0.2   # slip fit over the Tr5 crests
PULLEY_BORE_MOTOR = 5.0     # = MOTOR_SHAFT_D (declared below); the motor's own shaft
# THE SCREW PULLEY HAD NO TORQUE PATH AT ALL — a plain Ø5 bore on a round rod (user
# caught it). It is now a C-CLAMP: one full-height slit and an M2 screw squeezing the
# bore onto the rod. Three constraints shaped it, two of them learned the hard way:
#   • A GRUB was the first attempt and it is the wrong part here (user). A set screw
#     bearing on a thread crest is a point contact relying on preload staying put; a
#     clamp grips the whole circumference and cannot back off into a valley.
#   • The clamp screw must sit ABOVE THE BELT (user). Anything at r > the tooth OD
#     inside the toothed band jams the belt once per turn. So the screw lives in a hub
#     stacked on the top flange, and the hub is at the FLANGE Ø so it adds nothing to
#     the swept envelope — an earlier -X lug reached r 8.6 and swept a Ø17 circle.
#   • The screw axis must be X. Along Y a driver would have to reach past every other
#     station in the row; -X is open all the way to the motors.
# The SLIT does cross the toothed band — it has to, or the hub is fused to the body
# below and squeezing it does nothing. It is clocked to a tooth VALLEY so it notches no
# crest, and being axial it splits one tooth lengthwise rather than removing any.
PULLEY_HUB_H    = 3 * BEAD  # 2.4 of hub above the top flange, at the flange Ø
PULLEY_SLIT_W   = 1 * BEAD  # 0.8 — one bead, the narrowest gap that prints open
PULLEY_CLAMP_DY = 4.0       # clamp-screw axis, +Y of the bore, crossing the slit
PULLEY_CLAMP_Z  = PULLEY_W / 2      # its height: the cone/hub junction, so the cone
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
MR85_OD, MR85_ID, MR85_W = 8.0, 5.0, 2.5
SUPPORT_BRG_N   = 2
SUPPORT_BRG_OD  = MR85_OD   # Ø8 is what fits the 9.5 mm pitch inline
SUPPORT_BRG_ID  = MR85_ID
SUPPORT_BRG_W   = SUPPORT_BRG_N * MR85_W            # 5.0 — the STACK, not one bearing
# SUPPORT_BRG_Z is the THRUST LEDGE plane: the screw is pulled +Z, so the outer
# rings bear UP against the shared rail's top ledge and the stack hangs below it.
# (It used to be read as the stack's centre in one place and its ledge in another;
# screw_rail always meant the ledge, so that is what it now says.)
RAIL_PULLEY_CLR = 0.4                               # running gap, rail top → pulley flange
BRG_LEDGE_T     = 2 * BEAD                          # 1.6 of rail over the outer rings
SUPPORT_BRG_Z   = (SCREW_PULLEY_Z - PULLEY_W / 2
                   - RAIL_PULLEY_CLR - BRG_LEDGE_T) # -55.0, ledge underside
SUPPORT_BRG_BOT = SUPPORT_BRG_Z - SUPPORT_BRG_W     # -60.0, stack bottom
# RETAINING COLLAR — printed (src/screw_collar.py), replacing the purchased locknut.
# It drives the inner rings up against the balls, closing the load path
# screw → collar → inner rings → balls → outer rings → rail ledge → endplate.
#
# It grips by a FORMED thread, not friction: the bore is printed plain at 4.6
# (between the Tr5×1 minor 4.0 and major 5.0) and the steel rod cuts its own mating
# thread on the way in, exactly as a self-tapper does. That matters because we
# CANNOT print a Tr5×1 thread — a 1 mm pitch, 0.5 mm deep form is smaller than one
# 0.8 mm bead in both directions, so a slicer would smear it into a smooth bore —
# and a friction clamp is not trustworthy for a permanent 147 N: getting there
# needs ~1.8 kN of normal force, which puts ~69 MPa of hoop stress into a PETG-GF
# ring that will then creep and let go. The formed thread is a positive form lock
# instead: 8 mm of engagement is ~46 mm² of shear area, 3.2 MPa at 147 N, ~11×
# margin, and creep at that stress is nothing. It is safe HERE and not on the
# carriage nut for one reason — the collar never moves relative to the rod, while
# the carriage nut slides ~300 m over its life. That is a wear duty and needs brass.
#
# ⚠ THE COLLAR IS LENGTH-STARVED, and it is worth knowing exactly why. Everything
# below the pulley has to fit between two things neither of which will move: the
# pulley's bottom flange (-53.0, frozen by the motor bank) and the CHASSIS END
# BLOCK, which is solid from -64.5 down. That is a 10.7 mm budget for ledge (1.6)
# + bearings (5.0) + collar, so the collar gets 4.0 — half what it wants. At 4 turns
# of engagement that is ~28 mm² of shear area, 5.2 MPa under 147 N, against a
# ~20-25 MPa interlayer shear (the collar prints bore-up, so the thread ridges shear
# ALONG the layer bond). ~21-26% of strength: inside the usual 25% static-creep
# guideline, but only just, and it is the tightest margin in the drivetrain. If it
# ever needs more, the lever is the chassis end block, not anything in this file.
COLLAR_BORE     = 4.6       # thread-FORMING bore (minor 4.0 < this < major 5.0)
# THE COLLAR IS A BODY OF REVOLUTION, and that is not a style choice — IT TURNS WITH
# THE SCREW. It was first drawn as a 12.8 x 8.0 prism with spanner flats, which sweeps
# a Ø20.8 circle in a 9.5 mm lane: every collar would have milled both its neighbours
# on the first move (user caught it). The envelope is a cylinder at COLLAR_OD and the
# wrench flats are milled INTO that, which costs nothing — the swept circle is the
# cylinder either way.
COLLAR_OD       = 11 * BEAD # 8.8 — THE SWEPT ENVELOPE. 0.7 to the next screw's.
COLLAR_AF       = 10 * BEAD # 8.0 across flats, for a stock 8 mm spanner. Only 0.4/side
                            # off the cylinder, so the hoop round the forming bore stays
                            # almost continuous.
assert COLLAR_OD <= STRING_PITCH - 0.5 + 1e-9, (
    f"collars at Ø{COLLAR_OD} sweep into each other at the {STRING_PITCH} string pitch")
assert (COLLAR_AF - COLLAR_BORE) / 2 >= MIN_WALL_2P - 1e-9, (
    "the collar's wall at the flats is under two beads")
COLLAR_H        = 5 * BEAD                          # 4.0 TOTAL, boss included — the
                                                    # bore runs the full height, so this
                                                    # is also the thread engagement
COLLAR_BOSS_D   = 7 * BEAD  # 5.6 pilot: reaches the INNER rings only (their OD is ~6.3;
                            # 6.4 would risk grazing the stationary outer ring)
COLLAR_BOSS_H   = 1 * BEAD                          # 0.8
COLLAR_Z1       = SUPPORT_BRG_BOT                   # -60.0, boss top ON the inner rings
COLLAR_Z0       = COLLAR_Z1 - COLLAR_H              # -64.0
# BOTTOM of the rod: flush with the collar's bottom face — the collar IS the last
# thing on the screw, so there is nothing to leave rod for.
SCREW_BOT_Z     = COLLAR_Z0                         # -64.0
CHASSIS_END_TOP = -64.5     # measured off chassis_0 at the screw line: the hard floor
assert SCREW_BOT_Z - CHASSIS_END_TOP >= 0.4 - 1e-9, (
    f"the screw bottom sits {SCREW_BOT_Z - CHASSIS_END_TOP:.2f} over the chassis end "
    f"block (want 0.4): shorten COLLAR_H, or pocket the chassis")
SCREW_LEN       = SCREW_TOP_Z - SCREW_BOT_Z         # 49.4 — the CUT length (see BOM).
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
BELT_PLANE_DZ   = 14 * BEAD  # 11.2

# MOTORS SIT MIDWAY BETWEEN THE TWO PULLEY ROWS (user). They used to be coplanar
# with the LOW row (MOTOR_BELT_Z = SCREW_PULLEY_Z), so half the belts ran dead
# flat and the other half climbed a full belt plane — the whole Z change was paid
# by the odd strings alone. Splitting it means every belt rises or falls the SAME
# ±BELT_PLANE_DZ/2, so the twist develops symmetrically and no belt takes the
# full plane. The motors do NOT move to do this: SCREW_LEN grew by exactly half a
# plane above, which drops both pulley rows around the unchanged motor line, so
# motor_bank's floor/bed (derived from here) and the chassis are untouched.
MOTOR_BELT_Z    = SCREW_PULLEY_Z + BELT_PLANE_DZ / 2

# The clearance the frozen SCREW_PULLEY_Z used to get for free from being derived off
# NUT_BOT_MIN. It MUST be read against the RAISED pulley plane: five of the ten pulleys
# sit BELT_PLANE_DZ higher, and taking the base plane here is exactly how a 3 mm
# nut-into-pulley collision walked straight past this assert once already.
PULLEY_TOP_MAX  = SCREW_PULLEY_Z + BELT_PLANE_DZ + PULLEY_W / 2 + PULLEY_HUB_H
_NUT_PULLEY_GAP = NUT_BOT_MIN - PULLEY_TOP_MAX
assert _NUT_PULLEY_GAP >= 1.0 - 1e-9, (
    f"the nut's lowest point clears the RAISED-plane pulleys by only "
    f"{_NUT_PULLEY_GAP:.2f} (want 1.0): recess more of the nut into the carriage, or "
    f"shorten PULLEY_HUB_H — moving the pulley moves the whole motor bank with it")

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
