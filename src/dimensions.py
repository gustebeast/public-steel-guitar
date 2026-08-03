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
NOZZLE_D        = 0.8       # this build runs a 0.8 mm nozzle
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
XBAR            = 10.0      # the one "10 mm" module: square cross-rib section (10×10),
                            # end-crossbar width, and the leg/endplate border + L offset
WALL_THICKNESS  = 13 * NOZZLE_D  # 10.4 (was 10.0 = 12.5 beads) structural wall: I-beam rail thickness, the keyhead/bridge
                            # endplate faces, and the deck inner/outer face references

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
DECK_TOP_Z      = 6.0       # deck-plate top = playing-surface datum; the chassis deck
                            # plane (TP_GZ0/1) and the keyhead nut-block base both sit here
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
GUIDE_ROD_DX    = 12.95     # screw→rod offset: rod X = SCREW_X + DX = +4.95 (global). Moved +X
                            # (user) so the rod's metal −X edge clears the anchor-cage OPENING
                            # (POST_X1H, global +2.1) by 1.6 mm — was only 0.15, and that gap was
                            # what pinned the guide foot LOW. INSTALL (top-down): the rod drops
                            # through the stop bar, the carriage's closed bore, into the blind
                            # socket — friction-held top + bottom; the closed bore captures a loose
                            # carriage (carriage in place → rod drops in → screw threads in).
GUIDE_FOOT_DZ   = 2.0       # foot TOP from the carriage centre. Now at the NUT LEVEL (user): the
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
PULLEY_FLANGE_T  = MIN_WALL      # 0.8 (was 1.0 = 1.25 beads). Rounded DOWN, not up: at 1.6 the
                                 # two flanges leave a 4.8 toothed gap for a 5.0 belt -- it would not
                                 # fit. One bead is the hard floor and fine here (a guide lip, not
                                 # structure); the gap goes to 6.4.
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
MOTOR_BELT_Z    = SCREW_PULLEY_Z    # motors all sit at the (even) screw-pulley height

# Belt-plane cascade: a Ø8.4 pulley + belt wrap is wider than the 9.5 mm string
# pitch, so adjacent screw pulleys' belts would collide. Raise the ODD pulleys
# into a second Z plane so neighbours always differ by BELT_PLANE_DZ. Only the
# pulley moves — the motors stay coplanar and the bottom hardware is unchanged;
# the odd belt simply rises this much over its run.
BELT_PLANE_DZ   = 10.0

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
SCREW_NX_WALL   = 3 * NOZZLE_D  # 2.4 solid wall -X behind the far insert's OD (was 2.2)

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
