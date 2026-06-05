"""Top-level coordinate system, dimensions, materials, and fit clearances.

These are the constants every part draws from. Part-local constants live
next to the part they apply to.

──────────────────────────────────────────────────────────────────────────
COORDINATE SYSTEM (global, millimetres) — the player's perspective
──────────────────────────────────────────────────────────────────────────
  +X : ALONG the strings. +X is the changer (bridge + actuators); −X is the
       nut / keyhead. The roller bridge sits at X = 0; the speaking length and
       the nut run out toward −X.
  +Y : ACROSS the strings (string-to-string). The 10-string field is centred
       on Y = 0.
  +Z : up (instrument thickness). The screw field lies in the Z = 0 plane so
       the playing portion stays thin; the motor layers sit at ±MOTOR_LAYER_Z.

Per-string kinematic chain, nut end → changer end:
  far locking tuner (−X) → roller bridge (X=0) → carriage (rides guide rod +
  leadscrew nut, anchors the string ball-end) → leadscrew (+X) → driven-end
  pulley + support bearing → GT2 belt → motor.

The speaking length and tuner (−X) are represented schematically; the modelled
detail is the actuator side (X ≥ 0).
"""

import math

# ─────────────────────────────────────────────────────────────────────────
# Variant switch
# ─────────────────────────────────────────────────────────────────────────
# COMPACT = the inline variant: small Ø5-class hardware sized so each actuator
# fits within the changer pitch, so the screw field is a SINGLE inline plane
# (no along-string bank stagger, no Z-split). Only the driven-end pulleys still
# cascade along X so the belts separate. Set to False for the bulkier-hardware
# 2-bank + Z-split design. Override with env var PSG_COMPACT=0/1.
import os as _os
COMPACT = _os.environ.get("PSG_COMPACT", "1") != "0"

# ─────────────────────────────────────────────────────────────────────────
# String field (strings spaced ACROSS, along Y)
# ─────────────────────────────────────────────────────────────────────────
N_STRINGS       = 10
# Strings FAN: tight at the nut/keyhead (playing end), wider at the changer
# (where the bulky per-string actuators live). The actuator field uses
# STRING_PITCH; the nut/tuner end converges to NUT_PITCH.
STRING_PITCH    = 9.5       # mm, changer/actuator pitch (across, +Y)
NUT_PITCH       = 6.5       # mm, string spacing at the nut/keyhead end
STRING_FIELD_W  = (N_STRINGS - 1) * STRING_PITCH   # 85.5 mm across

def string_y(i: int) -> float:
    """Y centre of string i (0..9) at the CHANGER/actuator end."""
    return (i - (N_STRINGS - 1) / 2.0) * STRING_PITCH

def nut_y(i: int) -> float:
    """Y centre of string i at the NUT/tuner end (the strings fan to here)."""
    return (i - (N_STRINGS - 1) / 2.0) * NUT_PITCH


# ─────────────────────────────────────────────────────────────────────────
# Two-bank along-string stagger (resolves the tight-pitch packing problem)
# ─────────────────────────────────────────────────────────────────────────
# Every per-string part WIDER than the 9.5 mm string pitch (carriage, nut,
# screw pulley, bearing block, motor) would collide with its lateral neighbour
# if all 10 sat at the same X. So the strings interleave into two banks along X:
# even strings forward (bank 0, ΔX = 0), odd strings back (bank 1, ΔX = BANK_DX).
# Within a bank, neighbours are 19 mm apart — ample for ≤19 mm-wide parts.
# COMPACT: 0 — the small hardware fits inline at the changer pitch (no bank).
BANK_DX         = 0.0 if COMPACT else 32.0

def string_bank_dx(i: int) -> float:
    """Along-string offset applied to all of string i's parts (0 even / BANK_DX odd)."""
    return 0.0 if i % 2 == 0 else BANK_DX


# A MILD Z-split of the two banks (even down, odd up). One cross-bank conflict
# remains in the bulky variant: a screw running back to its driven end passes
# alongside the other bank's screw pulley (Ø16 on 9.5 mm pitch overhangs the
# neighbour's screw line). Splitting the banks by ±ACT_LAYER_Z lifts each pulley
# clear, and aligns the actuator layers with the two motor layers (even→lower,
# odd→upper). COMPACT: 0 — all screws share one Z plane (the open bearing cradle
# keeps its bulk below the screw plane, so neighbours clear).
ACT_LAYER_Z     = 0.0 if COMPACT else 9.0

def string_layer_z(i: int) -> float:
    """Z offset applied to string i's actuator (−even / +odd)."""
    return -ACT_LAYER_Z if i % 2 == 0 else ACT_LAYER_Z


# ─────────────────────────────────────────────────────────────────────────
# Leadscrew (single-start — self-locking, the keystone, §3) — axis +X
# ─────────────────────────────────────────────────────────────────────────
# T8×2 (standard) or Ø5×1 single-start (compact). Both self-locking; the Ø5×1
# lead angle is ~3.6° (very locking) and 1 mm lead is fast enough since a
# semitone is only ~1.5 mm of travel.
SCREW_OD        = 5.0 if COMPACT else 8.0
SCREW_LEAD      = 1.0 if COMPACT else 2.0
CARRIAGE_TRAVEL = 12.0      # mm usable carriage travel (bend ~3–6 + headroom)

# Distance between a string's two MOUNTING ENDS — the carriage ball-end (the
# changer side) and the far locking tuner (the keyhead) — at the nominal/open
# carriage position. Matches the user's instrument (~24.2" scale).
MOUNTING_SPAN   = 615.0

# Layout along the screw axis (X). Bridge at X=0; the screw lives toward +X.
# The drive end sits well forward (SCREW_DRIVEN_X) so the odd bank's carriage
# (at CARRIAGE_NOM_X + BANK_DX) tucks into the gap ahead of the even bank's
# bearing block without colliding.
SCREW_NEAR_X    = 12.0      # free/far-from-motor end (near the bridge)
CARRIAGE_NOM_X  = 26.0      # nominal (open-tuning) carriage centre, even bank
SCREW_DRIVEN_X  = 97.5      # driven (pulley) end, even bank
LEADSCREW_LEN   = SCREW_DRIVEN_X - SCREW_NEAR_X   # between supports


# ─────────────────────────────────────────────────────────────────────────
# Leadscrew nut (round brass, pressed into the carriage)
# ─────────────────────────────────────────────────────────────────────────
# A Ø-body with a small seat lip, pressed into the carriage pocket. Anti-rotation
# comes from the press/keyed pocket; the guide rod stops the carriage rotating.
NUT_OD          = 7.0 if COMPACT else 10.5   # round body OD (press pocket)
NUT_FLANGE_OD   = 9.0 if COMPACT else 13.0   # small seat lip OD
NUT_FLANGE_T    = 2.0       # seat lip thickness
NUT_BODY_LEN    = 7.0 if COMPACT else 8.0    # body length (excl. lip)


# ─────────────────────────────────────────────────────────────────────────
# Guide rod (anti-rotation) — axis +X, directly BELOW its screw
# ─────────────────────────────────────────────────────────────────────────
# Placed directly below its own screw (same Y, offset in −Z): a side rod would
# land on the neighbouring string's screw line. Coaxial-below keeps every rod on
# its own string's Y and keeps the carriage narrow.
GUIDE_ROD_D     = 2.5 if COMPACT else 4.0    # hardened steel
GUIDE_ROD_DZ    = (-6.0 if COMPACT else -9.0)   # Z offset below the screw centre


# ─────────────────────────────────────────────────────────────────────────
# Screw support bearing — ONE deep-groove ball bearing
# ─────────────────────────────────────────────────────────────────────────
# A single deep-groove bearing takes BOTH the radial location and the axial
# string load (~93 N, near-static). 685 (Ø5×11×5) for compact, MR128
# (Ø8×12×3.5) for standard; step up to a 688 (Ø16) for more axial margin.
SUPPORT_BRG_OD  = 11.0 if COMPACT else 12.0
SUPPORT_BRG_ID  = SCREW_OD
SUPPORT_BRG_W   = 5.0 if COMPACT else 3.5

# Locknut threaded onto the screw end, snug against the bearing inner race — the
# axial retainer. Rotates with the screw, so it never works loose.
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
# §5 — Belt-offset motor layout  ◄ KEY PROBLEM
# ─────────────────────────────────────────────────────────────────────────
# Zero-skew: each belt runs in a plane perpendicular to the screw axis (a Y–Z
# plane) — motor pulley and its screw pulley share the same X, so there is NO
# belt skew. Motors are offset from their screws ACROSS (out to the wide motor
# pitch along Y) and in Z (two layers above/below the screw plane); the belt
# spans that Y–Z centre distance.
#
# Belt overlap is avoided without a long fan:
#   • Two Z-LAYERS: odd strings drive UPPER-layer motors (+Z), even lower (−Z).
#   • The two-bank along-X stagger (BANK_DX) separates even from odd along X.
#   • Within one Z-layer the 5 belts would still fan through the same X-plane, so
#     adjacent belts split into TWO X belt-planes (BELT_PLANE_DX apart); each
#     belt sits in its own clear plane and never touches a neighbour's pulley.
MOTOR_PITCH      = 44.0     # ≥ 42.3 motor square + clearance, per layer (across, Y)
MOTORS_PER_LAYER = 5
MOTOR_LAYER_Z    = 42.0     # |Z| of each motor pulley plane from the screw plane

# X gap between the two belt-planes. Compact (inline) needs a wider gap: the
# carriages are inline, but the driven-end blocks of adjacent (cross-plane)
# strings are only 9.5 mm apart across, so they must clear along X instead.
BELT_PLANE_DX    = 26.0 if COMPACT else 12.0

def belt_plane(i: int) -> int:
    """Which of the two belt-planes string i uses, so adjacent belts separate.
    Standard (2-bank): alternate by across-rank within a bank. Compact (inline):
    alternate by string, which also routes even→lower / odd→upper motor layer."""
    return (i % 2) if COMPACT else ((i // 2) % 2)

def screw_pulley_x(i: int) -> float:
    """X of string i's screw pulley = driven end + bank stagger + belt-plane."""
    return SCREW_DRIVEN_X + string_bank_dx(i) + belt_plane(i) * BELT_PLANE_DX

def motor_layer_y_positions(center_y: float):
    """Y centres of the MOTORS_PER_LAYER motors in one layer, centred on
    center_y at MOTOR_PITCH spacing (across the strings)."""
    half = (MOTORS_PER_LAYER - 1) / 2.0
    return [center_y + (k - half) * MOTOR_PITCH for k in range(MOTORS_PER_LAYER)]

def motor_target_for_string(i: int):
    """Return (motor_y, motor_z, pulley_x) for string i.

    Odd strings → upper layer (+Z), back bank; even → lower layer (−Z), front
    bank. The motor pulley shares its screw pulley's X (zero belt skew). Within a
    layer the 5 motors are centred on the mean Y of the strings they serve, so
    the across-offset (hence belt centre-distance) is minimised."""
    if i % 2 == 1:                       # odd → upper
        strings = [1, 3, 5, 7, 9]
        z = +MOTOR_LAYER_Z
    else:                                # even → lower
        strings = [0, 2, 4, 6, 8]
        z = -MOTOR_LAYER_Z
    px = screw_pulley_x(i)
    center_y = sum(string_y(s) for s in strings) / len(strings)
    ys = motor_layer_y_positions(center_y)
    rank = strings.index(i)              # 0..4 within the layer, Y-sorted
    return ys[rank], z, px


# ─────────────────────────────────────────────────────────────────────────
# Roller bridge — sets the string pitch; string anchors toward the changer (+X)
# ─────────────────────────────────────────────────────────────────────────
BRIDGE_BAR_LEN   = STRING_FIELD_W + 14.0   # bar spans the field + margin (across, Y)
BRIDGE_BAR_DEPTH = 12.0     # along-string depth (X) of the bar
BRIDGE_BAR_H     = 10.0     # Z height of the bar
BRIDGE_ROLLER_D  = 6.0      # roller diameter
BRIDGE_TOP_Z     = 8.0      # string height above the screw plane at the bridge


# ─────────────────────────────────────────────────────────────────────────
# Locking tuner (schematic) at the nut end (−X)
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
# Base rail (chassis under the screw field, simplified)
# ─────────────────────────────────────────────────────────────────────────
BASE_ACROSS     = STRING_FIELD_W + 24.0    # across width (Y) of the screw-field base
BASE_T          = 5.0                      # base plate thickness (Z)
# Base top sits below BOTH the screw (Z=0) and the coaxial guide rod (−Z).
BASE_TOP_Z      = GUIDE_ROD_DZ - GUIDE_ROD_D / 2 - 3.0
BASE_X0         = -4.0                     # base spans from just behind the bridge
BASE_X1         = SCREW_DRIVEN_X + BANK_DX + 16.0   # to past the back-bank blocks
