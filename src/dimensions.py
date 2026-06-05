"""Top-level coordinate system, dimensions, materials, and fit clearances.

These are the constants every part draws from. Part-local constants live
next to the part they apply to.

──────────────────────────────────────────────────────────────────────────
COORDINATE SYSTEM (global, millimetres)
──────────────────────────────────────────────────────────────────────────
  +X : across the strings (string-to-string). String 0 is at the most −X
       position. The 10-string field is centred on X = 0.
  +Y : along the string pull line, pointing FROM the bridge toward the
       driven (motor) end. The speaking length / player side is −Y.
       The roller bridge sits at Y = 0.
  +Z : vertical (instrument thickness). The screw field lies in the
       Z = 0 plane so the playing portion stays thin; the motor brick's
       two layers sit at ±MOTOR_LAYER_Z, well above/below, in the
       outboard end-box where bulk is allowed.

Per-string kinematic chain (far end → driven end), all along +Y:
  far-end locking tuner (−Y, beyond the bridge on the player side is the
  speaking length; the tuner is actually at the far +Y... see note) →
  roller bridge (Y=0) → carriage (rides guide rod + leadscrew nut, anchors
  the string ball-end behind the bridge) → leadscrew → driven-end pulley +
  radial/thrust bearing block → GT2 belt → motor in the brick.

NOTE on the tuner: in this electro-mechanical design the player hand-tensions
at the FAR end of the speaking length (−Y, beyond the bar). For the assembly
we only model the actuator side (Y ≥ 0); the speaking length and tuner are
represented schematically.
"""

import math

# ─────────────────────────────────────────────────────────────────────────
# Variant switch
# ─────────────────────────────────────────────────────────────────────────
# COMPACT = the inline variant: small Ø5-class hardware sized so each actuator
# fits within the changer pitch, so the screw field is a SINGLE inline plane
# (no Y-bank stagger, no Z-split). Only the driven-end pulleys still cascade in
# Y so the belts separate. Set to False for the original (bulkier-hardware,
# 2-bank + Z-split) design. Override with env var PSG_COMPACT=0/1.
import os as _os
COMPACT = _os.environ.get("PSG_COMPACT", "1") != "0"

# ─────────────────────────────────────────────────────────────────────────
# String field
# ─────────────────────────────────────────────────────────────────────────
N_STRINGS       = 10
# Strings FAN: tight at the nut/keyhead (playing end), wider at the changer
# (where the bulky per-string actuators live). The actuator field uses
# STRING_PITCH; the nut/tuner end converges to NUT_PITCH.
STRING_PITCH    = 9.5       # mm, changer/actuator pitch (user's max; eases packing)
NUT_PITCH       = 6.5       # mm, string spacing at the nut/keyhead end
STRING_FIELD_W  = (N_STRINGS - 1) * STRING_PITCH   # 85.5 mm

def string_x(i: int) -> float:
    """X centre of string i (0..9) at the CHANGER/actuator end."""
    return (i - (N_STRINGS - 1) / 2.0) * STRING_PITCH

def nut_x(i: int) -> float:
    """X centre of string i at the NUT/tuner end (the strings fan to here)."""
    return (i - (N_STRINGS - 1) / 2.0) * NUT_PITCH


# ─────────────────────────────────────────────────────────────────────────
# Two-bank Y stagger (resolves the 11 mm-pitch packing problem)
# ─────────────────────────────────────────────────────────────────────────
# Every per-string part that is WIDER than the 9.5 mm string pitch (carriage,
# nut, screw pulley, bearing block, motor) would collide with its lateral
# neighbour if all 10 sat at the same Y. So the strings interleave into two
# Y "banks": even strings forward (bank 0, ΔY = 0), odd strings back
# (bank 1, ΔY = BANK_DY). Within a bank, neighbours are 19 mm apart — ample
# room for ≤19 mm-wide parts.
#
# Crucially the design stays in ONE Z-plane (thin, for the sit-on-keyboard
# goal). The transition congestion that a small stagger would cause (the odd
# bank's pulleys landing on the even bank's pulleys) is avoided by pushing the
# drive ends back far enough that the odd bank's CARRIAGE tucks into the gap
# between the even bank's carriage and its drive end — see the Y-station layout
# below (CARRIAGE_NOM_Y → SCREW_DRIVEN_Y). The motors clear the blocks because
# they sit in two Z-layers (±MOTOR_LAYER_Z) while the blocks stay at Z≈0.
# COMPACT: 0 — the small hardware fits inline at the changer pitch, so there is
# NO Y-bank stagger (all carriages/screws share one Y line).
BANK_DY         = 0.0 if COMPACT else 32.0

def string_bank_dy(i: int) -> float:
    """Y offset applied to ALL of string i's parts (0 for even, BANK_DY odd)."""
    return 0.0 if i % 2 == 0 else BANK_DY


# A MILD Z-split of the two banks (even down, odd up). The Y-stagger handles
# every same-Y conflict, but one cross-Y conflict remains: a screw running back
# to its driven end passes ALONGSIDE the other bank's screw pulley (Ø16 on
# 9.5 mm pitch ⇒ the pulley overhangs the neighbour's screw line). Splitting the
# banks by ±ACT_LAYER_Z lifts each pulley clear of the neighbouring screw, and
# conveniently aligns the actuator layers with the two motor layers (even→lower,
# odd→upper). Kept small (±9) so the playing portion stays thin.
# Compact: 0 — ALL screws share one Z plane. (The open bearing cradle keeps its
# bulk below the screw plane, so neighbours clear; belts are handled separately.)
ACT_LAYER_Z     = 0.0 if COMPACT else 9.0

def string_layer_z(i: int) -> float:
    """Z offset applied to string i's actuator (−even / +odd)."""
    return -ACT_LAYER_Z if i % 2 == 0 else ACT_LAYER_Z


# ─────────────────────────────────────────────────────────────────────────
# Leadscrew (T8×2 single-start — self-locking, the keystone, §3)
# ─────────────────────────────────────────────────────────────────────────
# Leadscrew: T8×2 (standard) or Ø5×1 single-start (compact). Both self-locking;
# the Ø5×1 lead angle is ~3.6° (very locking) and 1 mm lead is fast enough since
# a semitone is only ~1.5 mm of travel.
SCREW_OD        = 5.0 if COMPACT else 8.0
SCREW_LEAD      = 1.0 if COMPACT else 2.0
CARRIAGE_TRAVEL = 12.0      # mm usable carriage travel (bend ~3–6 + headroom)

# Distance between a string's two MOUNTING ENDS — the carriage ball-end (the
# changer side, behind the bridge) and the far locking tuner (the keyhead) —
# measured at the nominal/open carriage position. Matches the user's
# instrument (~24.2" scale).
MOUNTING_SPAN   = 615.0

# Y layout along the screw axis. Bridge at Y=0; the screw lives behind it.
# The drive end sits well back (SCREW_DRIVEN_Y) so the odd bank's carriage
# (at CARRIAGE_NOM_Y + BANK_DY) tucks into the gap ahead of the even bank's
# bearing block without colliding — see the BANK_DY note above.
SCREW_NEAR_Y    = 12.0      # free/far-from-motor end (near bridge)
CARRIAGE_NOM_Y  = 26.0      # nominal (open-tuning) carriage centre, even bank
SCREW_DRIVEN_Y  = 97.5      # driven (pulley) end, even bank
LEADSCREW_LEN   = SCREW_DRIVEN_Y - SCREW_NEAR_Y   # between supports


# ─────────────────────────────────────────────────────────────────────────
# Leadscrew nut (purchased brass flanged, captured anti-rotation in carriage)
# ─────────────────────────────────────────────────────────────────────────
# The "brass ROUND" nut option (not the Ø22 flanged one): a Ø10.5 body with a
# small Ø13 seat lip, pressed into the carriage pocket. A flanged Ø22 nut
# cannot coexist with neighbours at 11 mm pitch even when bank-staggered, so
# the round nut is the physically sensible choice here. Anti-rotation comes
# from the press/keyed pocket; the guide rod stops the carriage rotating.
NUT_OD          = 7.0 if COMPACT else 10.5   # round body OD (press pocket)
NUT_FLANGE_OD   = 9.0 if COMPACT else 13.0   # small seat lip OD
NUT_FLANGE_T    = 2.0       # seat lip thickness
NUT_BODY_LEN    = 7.0 if COMPACT else 8.0    # body length (excl. lip)


# ─────────────────────────────────────────────────────────────────────────
# Guide rod (anti-rotation, parallel to screw)
# ─────────────────────────────────────────────────────────────────────────
# Placed directly BELOW its own screw (same X, offset in −Z) rather than to
# the side: a side rod at +11 mm X lands exactly on the neighbouring string's
# screw line and would run straight through it. Coaxial-below keeps every rod
# on its own string's X (rods are then 11 mm apart, Ø4 — clear) and keeps the
# carriage narrow.
GUIDE_ROD_D     = 2.5 if COMPACT else 4.0    # hardened steel
GUIDE_ROD_DZ    = (-6.0 if COMPACT else -9.0)   # Z offset below the screw centre


# ─────────────────────────────────────────────────────────────────────────
# Screw support bearing (purchased) — ONE deep-groove ball bearing
# ─────────────────────────────────────────────────────────────────────────
# A single deep-groove bearing takes BOTH the radial location and the axial
# string load (~93 N, near-static), replacing the old separate radial + thrust
# bearings. MR128 (Ø8×Ø12) keeps the block within the 19 mm in-bank pitch; step
# up to a 688 (Ø8×Ø16) for more axial margin if the block can be a touch wider.
# 685 (Ø5×11×5) for compact, MR128 (Ø8×12×3.5) for standard.
SUPPORT_BRG_OD  = 11.0 if COMPACT else 12.0
SUPPORT_BRG_ID  = SCREW_OD
SUPPORT_BRG_W   = 5.0 if COMPACT else 3.5

# Locknut threaded onto the screw end, snug against the bearing inner race —
# the axial retainer (replaces the grub-screw shaft collar). Rotates with the
# screw, so it never works loose; engages the thread positively.
LOCKNUT_OD      = 9.0 if COMPACT else 13.0
LOCKNUT_W       = 4.0


# ─────────────────────────────────────────────────────────────────────────
# GT2 pulleys + belt
# ─────────────────────────────────────────────────────────────────────────
# GT2 14T (compact, ~Ø8.4 over teeth, Ø5 bore) or 20T (standard, Ø16, Ø8 bore).
PULLEY_TEETH    = 14 if COMPACT else 20
PULLEY_OD       = 8.4 if COMPACT else 16.0   # over teeth
PULLEY_W        = 10.0 if COMPACT else 16.0  # overall width incl. flanges
PULLEY_BORE_SCREW = SCREW_OD
PULLEY_BORE_MOTOR = 5.0
BELT_W          = 6.0       # GT2 6 mm
BELT_T          = 1.4


# ─────────────────────────────────────────────────────────────────────────
# Motor — MKS SERVO42D on a 48 mm NEMA17
# ─────────────────────────────────────────────────────────────────────────
MOTOR_SQ        = 42.3      # NEMA17 faceplate square
MOTOR_BODY_LEN  = 48.0      # motor body
MOTOR_PCB_LEN   = 22.0      # driver PCB stack on the rear
MOTOR_TOTAL_LEN = MOTOR_BODY_LEN + MOTOR_PCB_LEN   # ≈ 70 mm
MOTOR_SHAFT_D   = 5.0
MOTOR_SHAFT_LEN = 22.0
NEMA17_BOLT_SQ  = 31.0      # bolt-pattern square spacing (4× M3)
NEMA17_PILOT_D  = 22.0      # centre pilot boss diameter


# ─────────────────────────────────────────────────────────────────────────
# §5 — Belt-offset motor brick geometry  ◄ KEY PROBLEM
# ─────────────────────────────────────────────────────────────────────────
# SOLUTION MODELLED (zero-skew): each belt runs in a plane perpendicular to
# the screw axis (an X–Z plane) — motor pulley and its screw pulley share the
# same Y, so there is NO belt skew. The motors are offset from their screws
# in X (out to the wide motor pitch) and in Z (two layers above/below the
# screw plane); the belt simply spans that X–Z center distance.
#
# Belt overlap is avoided WITHOUT a long fan:
#   • Two Z-LAYERS: odd strings drive UPPER-layer motors (+Z), even strings
#     drive LOWER-layer motors (−Z).
#   • The two-bank Y stagger (BANK_DY) separates even from odd along Y.
#   • Within ONE Z-layer the 5 belts would still fan through the same Y-plane
#     and overlap each other and their neighbours' pulleys, so adjacent belts
#     are split into TWO Y belt-planes (BELT_PLANE_DY apart): each belt sits in
#     its own clear plane and no belt touches a neighbour's belt or pulley.
#
# Result: belt skew ≈ 0° by construction AND belts never overlap. The cost is
# end-box width (X) and height (Z), both of which live in the outboard end-box
# where bulk is fine. The trade vs. the spec's "fan each motor" idea is
# reported by build.py.
MOTOR_PITCH      = 44.0     # ≥ 42.3 motor square + clearance, per layer
MOTORS_PER_LAYER = 5
MOTOR_LAYER_Z    = 42.0     # |Z| of each motor pulley plane from the screw
                            # plane. Set so the motor mounting plate's top edge
                            # clears the screw pulleys hanging at Z≈∓17 (the
                            # belt-plane cascade brings some pulleys alongside
                            # the plates).
# Y gap between the two belt-planes. Compact (inline) needs a wider gap: the
# carriages are inline, but the driven-end blocks of adjacent (cross-plane)
# strings are only 9.5 mm apart in X, so they must clear in Y instead. The depth
# is behind the playing area, so it's cheap.
BELT_PLANE_DY    = 26.0 if COMPACT else 12.0

def belt_plane(i: int) -> int:
    """Which of the two belt-planes string i uses, so adjacent belts separate.
    Standard (2-bank): alternate by X-rank within a bank. Compact (inline):
    alternate by string, which also routes even→lower / odd→upper motor layer."""
    return (i % 2) if COMPACT else ((i // 2) % 2)

def screw_pulley_y(i: int) -> float:
    """Y of string i's screw pulley = driven end + bank stagger + belt-plane."""
    return SCREW_DRIVEN_Y + string_bank_dy(i) + belt_plane(i) * BELT_PLANE_DY

def motor_layer_x_positions(center_x: float):
    """X centres of the MOTORS_PER_LAYER motors in one layer, centred on
    center_x at MOTOR_PITCH spacing."""
    half = (MOTORS_PER_LAYER - 1) / 2.0
    return [center_x + (k - half) * MOTOR_PITCH for k in range(MOTORS_PER_LAYER)]

def motor_target_for_string(i: int):
    """Return (motor_x, motor_z, pulley_y) for string i.

    Odd strings → upper layer (+Z), back bank; even → lower layer (−Z), front
    bank. The motor pulley shares its screw pulley's Y (zero belt skew). Within
    a layer the 5 motors are centred on the mean X of the strings they serve,
    so the X offset (hence belt center-distance) is minimised."""
    if i % 2 == 1:                       # odd → upper
        strings = [1, 3, 5, 7, 9]
        z = +MOTOR_LAYER_Z
    else:                                # even → lower
        strings = [0, 2, 4, 6, 8]
        z = -MOTOR_LAYER_Z
    py = screw_pulley_y(i)
    center_x = sum(string_x(s) for s in strings) / len(strings)
    xs = motor_layer_x_positions(center_x)
    rank = strings.index(i)              # 0..4 within the layer, X-sorted
    return xs[rank], z, py


# ─────────────────────────────────────────────────────────────────────────
# Roller bridge (purchased) — sets the string pitch; string anchors BEHIND it
# ─────────────────────────────────────────────────────────────────────────
BRIDGE_BAR_W    = STRING_FIELD_W + 14.0    # bar spans the field + margin
BRIDGE_BAR_DEPTH = 12.0     # Y depth of the bridge bar
BRIDGE_BAR_H    = 10.0      # Z height of the bridge bar
BRIDGE_ROLLER_D = 6.0       # roller diameter
BRIDGE_TOP_Z    = 8.0       # string height above the screw plane (Z=0) at
                            # the bridge — strings ride above the carriages


# ─────────────────────────────────────────────────────────────────────────
# Locking tuner (purchased, schematic) at the far end
# ─────────────────────────────────────────────────────────────────────────
TUNER_W         = 6.0       # schematic; real locking tuners stagger at the keyhead
TUNER_H         = 18.0
TUNER_D         = 20.0


# ─────────────────────────────────────────────────────────────────────────
# Materials / fits / print
# ─────────────────────────────────────────────────────────────────────────
# PCTG — body, brackets, enclosures (dimensionally stable, non-load).
# PA6-GF — carriage, anchors, bearing blocks (sustained-tension path).
FIT_CLR         = 0.30      # general clearance hole
PRESS_CLR       = 0.10      # press-fit interference (per side, into the part)
WALL            = 2.4       # default structural wall
BUILD_VOL       = 255.0     # printer build volume cube edge (split body above this)

# Heat-set insert / fastener pilots
M3_CLR_D        = 3.4       # M3 clearance
M3_INSERT_D     = 4.0       # heat-set insert pilot
M3_HEAD_D       = 6.0
INSERT_DEPTH    = 5.0

BOOL_OVERSHOOT  = 0.5       # extend cutters into host for clean booleans


# ─────────────────────────────────────────────────────────────────────────
# Base rail (chassis under the screw field, simplified for v1)
# ─────────────────────────────────────────────────────────────────────────
BASE_W          = STRING_FIELD_W + 24.0    # X width of the screw-field base
BASE_T          = 5.0                      # base plate thickness (Z)
# Base top sits below BOTH the screw (Z=0) and the coaxial guide rod (−Z).
BASE_TOP_Z      = GUIDE_ROD_DZ - GUIDE_ROD_D / 2 - 3.0
BASE_Y0         = -4.0                     # base spans from just behind bridge
BASE_Y1         = SCREW_DRIVEN_Y + BANK_DY + 16.0   # to past the BACK bank blocks
