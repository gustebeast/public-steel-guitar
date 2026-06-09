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
  range, so the screws are short — ~53 mm, no whip). The motors lie flat UNDER
  the speaking length in a staircase along −X, shaft facing +Y (body extends −Y
  toward the player). A twisted GT2 belt turns each motor pulley (axis Y) to its
  screw pulley (axis Z) — the common perpendicular of Y and Z is X, so the belt
  runs along X under the strings.
"""

# ─────────────────────────────────────────────────────────────────────────
# String field (strings spaced ACROSS, along Y; lowest pitch at −Y / player)
# ─────────────────────────────────────────────────────────────────────────
N_STRINGS       = 10
STRING_PITCH    = 9.5       # mm, changer pitch (across, Y)
NUT_PITCH       = 6.5       # mm, spacing at the nut/keyhead end
STRING_FIELD_W  = (N_STRINGS - 1) * STRING_PITCH   # 85.5 mm
MOUNTING_SPAN   = 615.0     # between a string's two mounting ends (~24.2" scale)

def string_y(i: int) -> float:
    """Y centre of string i (0..9) at the changer; string 0 at −Y (player side)."""
    return (i - (N_STRINGS - 1) / 2.0) * STRING_PITCH

def nut_y(i: int) -> float:
    """Y centre of string i at the nut end (strings fan to here)."""
    return (i - (N_STRINGS - 1) / 2.0) * NUT_PITCH


# ─────────────────────────────────────────────────────────────────────────
# Heights (Z). Speaking length on top; mechanism below.
# ─────────────────────────────────────────────────────────────────────────
STRING_Z        = 16.0      # speaking-length / bridge-bearing top
SCREW_TOP_Z     = 2.0       # screw top, below the bend / carriage travel
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


# ─────────────────────────────────────────────────────────────────────────
# Vertical leadscrew (single-start, self-locking — the keystone, §3) — axis Z
# ─────────────────────────────────────────────────────────────────────────
# Ø5×1 single-start: lead angle ~3.6° (very self-locking) and fast enough (a
# semitone is only ~1.5 mm). Vertical ⇒ short (no whip).
SCREW_OD        = 5.0       # Ø5, single-start, 1 mm lead
SCREW_LEN       = 61.0      # +8 vs the minimum: drops the whole drive stack (pulleys,
                            # belts, motors, support bearing, chassis floor — all derive
                            # from here) 8 mm so the raised odd pulleys clear the carriage's
                            # full down-travel + a bottom stop, restoring the travel margin
SCREW_BOT_Z     = SCREW_TOP_Z - SCREW_LEN          # -59
CARRIAGE_NOM_Z  = SCREW_TOP_Z - 8.0                # default = TOP of travel; the anchor post
                                                   # clears the bridge bearings by 1 mm (the
                                                   # endplate's upper guide ledge hard-stops
                                                   # the carriage foot here, protecting them)
SCREW_PULLEY_Z  = SCREW_BOT_Z + 15.0               # screw drive pulley near bottom (-36)


# ─────────────────────────────────────────────────────────────────────────
# Leadscrew nut (round brass, pressed into the carriage)
# ─────────────────────────────────────────────────────────────────────────
NUT_OD          = 7.0
NUT_FLANGE_OD   = 9.0
NUT_FLANGE_T    = 2.0
NUT_BODY_LEN    = 7.0


# ─────────────────────────────────────────────────────────────────────────
# Guide rod (anti-rotation) — axis Z, on the +X (cap) side of the screw, BELOW
# the stringing window. The carriage reaches it with a low FOOT (column + leg
# hanging under the plate), keeping the whole window clear for string access.
# Both rod seats and both hard stops are cap-backed ledges on the endplate —
# no spanning bar, so the endplate prints with no overhang.
# ─────────────────────────────────────────────────────────────────────────
GUIDE_ROD_D     = 2.5
GUIDE_ROD_DX    = 10.75     # screw→rod offset, now +X: rod X = SCREW_X + DX = +2.75
                            # (max that leaves a printable +X wall on the foot, whose
                            # face stops 0.5 shy of the cap face at +6)
GUIDE_FOOT_DZ   = -14.0     # foot TOP from the carriage centre (plate bottom −6,
                            # then an 8.0 column — clears the upper ledge's Z band,
                            # which sits 0.5 below the anchor cage's sweep bottom)
GUIDE_FOOT_H    = 6.0       # foot height = guide-bore engagement length

# The bridge / string anchor sits at X=0; the screw can't occupy that spot, so
# it is offset −X by ANCHOR_DX and the carriage reaches over to the anchor.
BRIDGE_X        = 0.0
SCREW_X         = -8.0      # all 10 vertical screws sit on this X line
ANCHOR_DX       = BRIDGE_X - SCREW_X    # anchor is +X of the screw (8 mm)

# String-end nut: a cylinder swaged on the string's bridge end (axis Y), slotted
# into the carriage anchor. The string exits +Z and its pull seats the nut up
# under the anchor roof (mechanical capture, no clamp). DEMO/purchased part.
STRING_NUT_D    = 3.5
STRING_NUT_L    = 6.0


# ─────────────────────────────────────────────────────────────────────────
# Screw support bushing (Ø8, fits the pitch) + locknut — axis Z
# ─────────────────────────────────────────────────────────────────────────
# Ø8 so it fits the 9.5 mm pitch inline: a bushing or MR85 (Ø5×8) for radial
# location + a thrust washer for the axial string pull (~93 N near-static, held
# mostly by the self-locking screw — the support only rotates during a move).
# The 10 supports live in a single shared rail (no overlapping per-screw cradles).
SUPPORT_BRG_OD  = 8.0
SUPPORT_BRG_ID  = SCREW_OD
SUPPORT_BRG_W   = 5.0
SUPPORT_BRG_Z   = SCREW_PULLEY_Z - 8.5     # below the pulley; clears the 5 mm belt wrap
LOCKNUT_OD      = 8.0
LOCKNUT_W       = 4.0


# ─────────────────────────────────────────────────────────────────────────
# GT2 pulleys (14T) + belt. Flanges keep the (twisting) belt from walking off.
# ─────────────────────────────────────────────────────────────────────────
PULLEY_OD       = 8.4       # over teeth
PULLEY_W        = 8.0       # axial: ~6 mm toothed gap + 2 flanges (fits the 5 mm belt)
PULLEY_FLANGE_OD = PULLEY_OD + 2.6
PULLEY_FLANGE_T  = 1.0
PULLEY_BORE_SCREW = SCREW_OD
PULLEY_BORE_MOTOR = 5.0
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
# overlap. Order: string 0 (lowest, −Y) CLOSEST to the bridge, string 9 (highest,
# +Y) FURTHEST — so every belt, running back to the bridge at its string's Y,
# stays on the +Y side of the closer motors' (−Y-extending) bodies and clears.
# First motor offset sized so even the shortest belt (string 0, closest) has a
# ≥100 mm free span — long enough to develop the 90° belt twist gently (≲1°/mm)
# and lie flat at each pulley (a 6 mm toothed belt wants ≳15× width to twist).
MOTOR_X0        = 110.0     # first motor's −X offset from the bridge
MOTOR_X_STEP    = 44.0      # along-X step between motors (≥ motor square)
MOTOR_BELT_Z    = SCREW_PULLEY_Z    # motors all sit at the (even) screw-pulley height

# Belt-plane cascade: a Ø8.4 pulley + belt wrap is wider than the 9.5 mm string
# pitch, so adjacent screw pulleys' belts would collide. Raise the ODD pulleys
# into a second Z plane so neighbours always differ by BELT_PLANE_DZ. Only the
# pulley moves — the motors stay coplanar and the bottom hardware is unchanged;
# the odd belt simply rises this much over its run.
BELT_PLANE_DZ   = 10.0

def screw_pulley_z(i: int) -> float:
    return SCREW_PULLEY_Z + (i % 2) * BELT_PLANE_DZ

def motor_pos(i: int):
    """Return (x, y, z) of string i's motor pulley (on the string's Y line)."""
    return (-(MOTOR_X0 + i * MOTOR_X_STEP), string_y(i), MOTOR_BELT_Z)


# ─────────────────────────────────────────────────────────────────────────
# Bridge bearings — turn each string 90° (vertical rise → −X speaking length).
# One small ball bearing PER STRING on a shared axle (axis Y): a freely-spinning
# bearing keeps the bend near-frictionless so the two sides' tensions equalize
# (a fixed surface would mismatch them ~37% at 90° and cause tuning hysteresis).
# ─────────────────────────────────────────────────────────────────────────
BRIDGE_BEARING_OD = 8.0     # MR builds (e.g. 693 Ø3×8); fits the 9.5 mm pitch
BRIDGE_BEARING_W  = 4.0     # along the axle (Y); string rides a groove in the OD
BRIDGE_AXLE_D     = 3.0     # shared axle (axis Y)
BRIDGE_BEARING_Z  = STRING_Z - BRIDGE_BEARING_OD / 2     # axle/bearing centre (12)
# The string rises vertically from the anchor (at BRIDGE_X) tangent to the
# bearing's +X extent, wraps 90° over the top, then leaves −X along the top. So
# the bearing centre sits OD/2 to −X of the anchor line.
BRIDGE_AXLE_X     = BRIDGE_X - BRIDGE_BEARING_OD / 2     # bearing/axle centre X
BRIDGE_AXLE_Y     = STRING_FIELD_W / 2 + 9.0             # axle/support half-span
BRIDGE_ARM_W      = 5.0     # bridge-endplate bearing-arm / edge-web thickness (Y); the
                            # screw rail widens by this so the rib overlaps it cleanly
BRIDGE_BAR_DEPTH  = 12.0    # along-string depth (X) of the supports


# ─────────────────────────────────────────────────────────────────────────
# Locking tuner (schematic) at the nut end (−X)
# ─────────────────────────────────────────────────────────────────────────
TUNER_W         = 6.0
TUNER_H         = 18.0
TUNER_D         = 20.0

# ─────────────────────────────────────────────────────────────────────────
# String gauges → the nut break inserts are GAUGED to these so the string TOPS
# sit coplanar at STRING_Z. Reprint the (bolt-on) nut block to switch sets.
# Index 0 = −Y (player side, lowest/heaviest) → mapped to the set's low end.
# ─────────────────────────────────────────────────────────────────────────
GAUGES_E9_IN = (.013, .015, .011, .014, .017, .020, .026, .030, .034, .038)  # str 1→10
GAUGES_C6_IN = (.015, .014, .017, .020, .024, .030, .036, .042, .054, .070)
STRING_GAUGE = tuple(g * 25.4 for g in reversed(GAUGES_C6_IN))   # mm, our index 0..9 (C6)

# Nut block sits with its break edge (the open-string scale endpoint) here.
NUT_BLOCK_X  = -MOUNTING_SPAN


# ─────────────────────────────────────────────────────────────────────────
# Fits / fasteners
# ─────────────────────────────────────────────────────────────────────────
FIT_CLR         = 0.30      # slip-fit clearance (e.g. guide rod in its bore)
M3_CLR_D        = 3.4       # M3 clearance hole (NEMA17 bolt pattern)
BOOL_OVERSHOOT  = 0.5       # extra length on cutting tools so faces clear cleanly
