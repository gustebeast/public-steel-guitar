"""Knee lever (LKL — first instance of the input-side control core). PCTG.

NOT a mechanical changer: the lever does nothing to the strings. It is purely a
POSITION SENSOR — the player's left knee pushes the paddle, a diametric magnet on
the pivot axle rotates over a fixed MT6701 14-bit Hall angle encoder, and the
firmware maps that angle (per-control calibration + copedant) to string-pitch
targets. See pedal-knee-lever-design.md.

This is the reusable control core (pivot + on-axis magnet + fixed sensor board +
return springs + end stops). LKL is SINGLE-direction: neutral -> full throw one
way. Other controls reuse the core with a different arm/paddle and mount.

Canonical local frame (build.py places it under the body, between two cross-ribs):
  +Y = pivot axle. The lever mounts BETWEEN two X-position ribs and slides in from
       the player face: -Y = OUTBOARD (player side, hangs in open air past the rib
       ends); +Y = INBOARD (deep under the body) where the magnet + sensor live.
  -Z = down: the arm hangs to the knee paddle; NEUTRAL = arm straight down.
  throw = the LATERAL knee push: +theta about +Y swings the -Z arm toward -X
       (player's LEFT -> "left knee left"); the +Z return cam swings toward +X.
Pivot at the origin; the axle axis runs along Y through x=0, z=0.

The whole pivot/hub/cam/feel cluster sits OUTBOARD of the rib -Y ends in open air,
so the four M4 feel-adjuster screws are reachable from +-X. The throw is lateral
(X), so the housing's +-X faces stay clean, the mount tenons stand on its TOP face
(one per chassis rib crossing, sliding +Y for knee depth), and the magnet/sensor
exit the +Y end into open space under the body (no rib conflict).

Two springs per the project tensioner pattern: a PRIMARY return spring (sets the
main feel) and an optional HALF-STOP spring, set back so it only engages partway
through the throw -- a tactile resistance step the player can rest a half-pull on.
Both ride adjustment screws so tension is tunable.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import components as C
from . import motor_bank as MB          # for BED_Z, the chassis print-bed datum
                                        # (chassis imports knee_lever, so not chassis)
from .helpers import box_at, corbel_close, cyl, cyl_y, heal
from . import board_geom as BG

from cadkit.fasteners import (M4_SHAFT_CLR_D, M4_INSERT_D, M4_BUTTON_HEAD_D,
                              seated_insert,
                              M4_BUTTON_HEAD_H,
                              m4_button_screw,
                       M4_INSERT_L, M4_SCREW_L, M4, cut_insert_bore,
                       cut_selftap,
                       cut_m4_pocket, seated_m4_insert, cut_m4_boss, m4_boss_insert)
from cadkit.pcb import (PCB_T as _PCB_T, jst_ph_side_header, ph_side_length,
                        PH_SIDE_H, PH_SIDE_D, PH_TAB_D, PH_PLUG_RUN, PH_PITCH)
from cadkit.joinery import PrintSpec, joint   # cadkit's one joinery entrypoint
from cadkit.supports import printable_bore
# the M4 insert pocket/boss helpers now live in cadkit/fasteners.py (shared); keep the old local names:
_insert_pocket, _seated_insert = cut_m4_pocket, seated_m4_insert
_insert_boss_cut, _insert_dummy = cut_m4_boss, m4_boss_insert

# ── bought parts (assembly dummies). REUSE existing line items where possible so they buy in
# bulk: the 688ZZ bearings + the M4×10 button heads + M4 heat-set inserts are ALL already in
# the BOM. New: the Ø6 magnet, the MT6701 board, the springs.
AXLE_D  = D.BRG688_ID               # Ø8 axle journals (the 688ZZ bore, user 2026-09-10) — PCTG (user: no steel pin).
                                    # Zero torque lives on the axle (the springs act on
                                    # the LOBE; the magnet only co-rotates for the
                                    # sensor) and the radial bearing reactions (~4-5x
                                    # knee force ≈ 130 N worst) sit ~5x under a Ø5 PCTG
                                    # journal's shear capacity; the steel MR85 inner
                                    # races take all the wear. (HISTORICAL: this described
                                    # the integral-stub + glued-insert pair, retired at
                                    # round 2 — the axle is ONE part now, see kl_axle.)
BRG_OD, BRG_ID, BRG_W = D.BRG688_OD, D.BRG688_ID, D.BRG688_W   # 688ZZ (Ø8×16×5) — the ONE
                                    # bearing everywhere (user, 2026-09-10): the screws, the bridge,
                                    # these levers and the foot pedals, which share these constants.
                                    # 688ZZ C0r 474-710 N, so the ~130 N worst case is 3.6-5.5x.
                                    # (history) 695ZZ (Ø5×13×4) before that. Was MR85ZZ
                                    # (Ø8×2.5), which sat at exactly 1.0x its 130 N
                                    # static rating here; 695ZZ is 346 N -> 2.7x.
                                    # SAME Ø5 bore, so friction is unchanged (deep-
                                    # groove drag is mu*P*d/2 and d is the BORE), and
                                    # it adds no inertia — the bearing lives in the
                                    # HOUSING, not on the swinging lever. The cost is
                                    # bulk: the housing grows to clear the race.
BRG_WALL = 1.6                      # 2-bead seat wall around the outer race
BRG_SEAT_D = BRG_OD + 0.1           # the seat bore (race + press clearance) — walls measure from THIS
BRG_WALL_X = 4 * D.BEAD             # 3.2 +X of the seat (user): with the lever room open through the
                                    # +X face the cheek holds that side of the race from below only
                                    # (the seat's print peak opens its top), so it gets double the tier.
                                    # 1.6 measured off the RACE had left 1.55 off the seat.
MAG_D, MAG_T = 6.0, 2.5             # DIAMETRICALLY-magnetised NdFeB disc on the axle end
                                    # = DigiKey/Radial Magnets 8995 (N35, NiCuNi, 80 °C),
                                    # an EXISTING supplier, in stock, $0.33–0.40. SOURCING
                                    # PICKED THE SIZE (user asked): a Ø8×2.0 would save
                                    # 0.5 of +Y — going wider buys back a thinner magnet
                                    # because a diametric disc's poles sit on the CURVED
                                    # FLANKS, so pole separation (and the falloff length
                                    # over the gap) scales with DIAMETER — but nobody we
                                    # already buy from stocks Ø8×2.0: DigiKey's Ø8 is
                                    # 2.5 thick (saves nothing) and the Ø8×2.0 is a
                                    # 100-pack from a new vendor. Not worth it for 0.5,
                                    # especially now the MAG_Y0 anchor fix below has
                                    # already reclaimed 2.6 of +Y. Ø6×2.5 is also the
                                    # REFERENCE geometry for this sensor class (ams' own
                                    # AS5000-MD6H is D6×2.5), so the app notes apply
                                    # directly instead of us estimating the field.
                                    # AIR_GAP stays the trim knob (a printed dimension):
                                    # the IC reads field DIRECTION, so strength only has
                                    # to LAND in the window, it doesn't set accuracy.
AIR_GAP = 1.5                       # magnet face -> the IC's OWN TOP SURFACE. THE DATUM IS
                                    # THE PACKAGE FACE, not the board: the die looks at the
                                    # magnet, so the QFN's own height sits INSIDE the gap and
                                    # the board is a further CHIP_H out (PCB_Y below).
                                    # 1.2 -> 1.5 (this round), and the reason is a CLASH the
                                    # sensor round turned up rather than a field argument:
                                    # kl_magnet_cap's flange stands CAP_T = 0.8 proud of the
                                    # magnet face, so the chip's real clearance to a ROTATING
                                    # part is AIR_GAP - CAP_T, and the stack's axial float is
                                    # 0.4 in exactly that direction. At 1.2 the numbers were
                                    # 0.4 and 0.4 — the cap could touch the IC. At 1.5 it is
                                    # 0.7 nominal, 0.3 at full float. FLOAT DIRECTION
                                    # (measured): the axle flange seats -Y on the rib, so the
                                    # only travel left is +Y, carrying the magnet TOWARD the
                                    # chip — the gap band is 1.5 DOWN to 1.1, never up. That
                                    # is why the old worry about grazing the 2.0 ceiling was
                                    # backwards, and why 1.5 costs nothing: both ends sit
                                    # mid-window, and the magnet's pull toward the steel
                                    # bearing preloads the flange onto the rib, so 1.5 is
                                    # where it actually rests.
                                    # DATASHEET (MagnTek MT6701 Rev 1.5, 2021.03, §5 —
                                    # quoted, not estimated): Bpk 200-1,000 Gauss "Measure at
                                    # the IC Surface"; AG "Magnetic to IC Surface Distance"
                                    # 0.5 / 1.0 / 2.0 min/typ/max; recommended magnet Ø6 x
                                    # 2.5 — EXACTLY ours, so this is the nominal
                                    # configuration the part was characterised in.
# ── THE SENSOR BOARD AS SPECIFIED FOR ITS RE-SPIN (user, 2026-09-21; docs/lever-sensor-respin.md).
# SINGLE-SIDED, like every board on the shared panel (elec/fab.py). J1 is an S8B-PH-SM4-TB,
# SMT side-entry, on the MAGNET face at the -X edge, standing on end (user, 2026-09-21: the
# lever bus goes to 5 V, and a PH connector keys it apart from the 24 V XH motor tees so no
# harness can put 24 V on a lever board; PH is also 19,469 deep at LCSC against XH's 105).
# What changes from the routed board is the
# outline, trimmed from the routed 34 x 28 to what the three housings take: 3.0 off the +X side
# (the pedal's +X face) and the TOP down to 10.1 over the chip (user chose trimming the top,
# 2026-09-21): the pedal installs the board TURNED OVER -- J1 down into the bar -- which puts
# the TOP edge toward the player-side face, 10.15 from the axle. The bottom is then whatever
# J1's 20.0 on end needs (11.9), inside the horizontal lever's floor.
CHIP_DROP  = 10.1                   # chip centre below the board's TOP edge (routed: 14.6)
CEIL_CLR = 0.4                      # board top edge -> the instrument's underside. THE
                                    # INSTRUMENT IS THE BOARD'S +Z RETAINER (user), which is
                                    # why there is no retaining screw: the board goes in with
                                    # the lever OFF the guitar, and the chassis becomes its
                                    # lid the moment the lever slides into the ribs. 0.4 is
                                    # the slide clearance plus the board's own height
                                    # tolerance. The board still RESTS on the cradle floor, so
                                    # this is a LIFT STOP, not a datum.
PCB_WZ = 21.9                       # 10.1 up + 11.8 down: J1's 19.9 + the 1.0 edge rule twice.
                                    # History: 21.4 before the XH; the notes below are from
                                    # the PH-era layout. ONE board for every lever. 16.0 until the real circuit
                                    # was laid out (elec/lever_sensor.py): 29 parts and an
                                    # 8-way trunk connector do not fit 16, and the 8-way is
                                    # what lets the bus-B tee disappear into this board.
                                    # THE CAP IS THE FOOT PEDAL, not the knee levers: its
                                    # housing is clipped to the pedal BAR's own width, so the
                                    # board may not reach below foot_pedal.HOUS_Z0. That
                                    # number MOVED to -10.15, and 22.0 no longer fitted -- the
                                    # top is pinned at CHIP_DROP (+11.30) by the sensor sitting
                                    # on the axle, so the whole 0.6 comes off the BOTTOM and
                                    # the cap is 21.45. 21.4 is what is left, and it is now
                                    # limited by THE CONNECTOR rather than by the parts: J1's
                                    # courtyard is 21.29, so 0.055 of board edge at each end is
                                    # all there is. The board cannot get shorter without a
                                    # different connector. (25 was drawn before any of this was
                                    # checked; foot_pedal.py is what catches it, because
                                    # board_flip polices a cradle WINDOW and the pedal's budget
                                    # is tighter than the window.) (History: WAS 19.0, and that was 3.0
PCB_T = _PCB_T                      # taller than anything on it: the board ran to z -12 while
                                    # the lowest feature — the CONNECTOR, which is the tallest
                                    # thing in Z at 15.0 — bottomed at -8.0, leaving a 4.0 x 28
                                    # strip of dead FR4 (112 mm2) with nothing on it at all
                                    # (user spotted it). Now DERIVED: the connector's 15.0 plus
                                    # CONN_EDGE below it, topped out flush (see CONN_RISE — the
                                    # connector is deliberately flush with the top edge, and the
                                    # chip's CHIP_DROP fixes that edge relative to the axle).
                                    # In X the outline is already tight: the chip's keepout sets
                                    # +X and the connector's groove band sets -X.
CHIP_W, CHIP_H = 3.0, 0.80          # MT6701QT-STD, QFN-16. DATASHEET §9.2 (verified):
                                    # D = E = 2.900..3.100 (3.0 nominal) and A, the TOTAL
                                    # package height, = 0.700..0.800. CHIP_H takes the MAX,
                                    # not the typical: A is what stands between the board
                                    # face and the air gap's datum, so the tallest package is
                                    # the one the stack has to fit. (0.75 here before was a
                                    # generic-QFN guess; the real max is 0.80.)
                                    # §1.2 states "Sensing Center at Geometry Center" for the
                                    # QFN-16 (and the SOP-8) — so putting the package body's
                                    # centre on the axle axis IS putting the sensing centre
                                    # there; no package-specific offset to carry.
                                    # The QFN is the variant to buy: the SOP-8 is ~1.5 tall
                                    # and every tenth of that is +Y we do not have.
CHIP_DISP_MAX = 0.3                 # datasheet DISP: max misalignment between the sensing
                                    # centre and the magnet axis. This is the tolerance that
                                    # sizes the cradle's X/Z location, and it is spent on
                                    # (a) the board's routed-outline-to-copper tolerance
                                    # (JLCPCB ±0.2) and (b) the groove's 0.15 slip fit. It
                                    # buys INL only — ±1.0° typ vs ±1.5° max — and INL is a
                                    # smooth systematic error the per-control calibration map
                                    # already removes, so overrunning it slightly degrades
                                    # nothing we depend on. Repeatability (0.01° rms noise,
                                    # 0.088° hysteresis) is untouched by misalignment.
                                    # (PCB_TOP / the board's Z extent live in the cradle
                                    # block below — they are set by the instrument's
                                    # underside, which isn't known this early.)
INSERT_D, INSERT_L = M4_INSERT_D, M4_INSERT_L   # M4 heat-set insert Ø6 × 5
SCREW_CLR = M4_SHAFT_CLR_D          # M4 shaft clearance (Ø4.4)

# ── housing envelope ─────────────────────────────────────────────────────────
WALL    = 4.0                       # bearing-wall thickness (Y)
HALF_X  = 14 * D.BEAD               # 11.2 housing half-width in X (the bearing block; sits
                                    #   in the bay). Snapped UP: wider extents can only KEEP
                                    #   or ADD tenon stations, never drop one
WALL_Z0, WALL_Z1 = -9.0, 5.5        # bearing walls (axle plates) span this in Z (bearing centred z=0);
                                    #   top just clears the Ø10 hub (z 5) -- the mount is now to the -X SIDE
                                    #   (rails), NOT a yoke above the lever, so the plates stop at the lever top

# ── layout along the axle (Y): -Y outboard (player) .. +Y inboard (under body) ──
# The hub/cam is THICK (24 mm) so the main coil (-Y), the half-stop cartridge (+Y) and the centred
# stop screw all get their own Y lane without touching. The bearing walls flank it; magnet + sensor
# sit past the +Y wall.
HUB_Y0, HUB_Y1 = -12.0, 12.0        # hub / cam / feel cavity -- 24 mm thick
WN_Y0, WN_Y1   = HUB_Y0 - 4.0, HUB_Y0   # -Y bearing wall (-14 .. -10)
WP_Y0, WP_Y1   = HUB_Y1, HUB_Y1 + 4.0   # +Y bearing wall (10 .. 14)
# (MAG_Y0 / PCB_Y / AXLE_Y0 / AXLE_Y1 moved DOWN to the prism block: they
#  anchor to the housing face + bearing home, which are defined there. They
#  used to hang off WP_Y1 — the +Y bearing WALL, deleted in the prism round —
#  which left the magnet floating 2.6 outboard of the real face.)
# (the cone/pilot glue tenon and its protruding KEY tongue are retired with the
#  insert — the axle is one through-part now and the key is a D-FLAT, sized in
#  the prism block: a protruding tongue cannot pass the Ø5 bearing bore.)
HUB_YC  = (HUB_Y0 + HUB_Y1) / 2     # hub / cam / feel centre Y (0)

# ── lever ────────────────────────────────────────────────────────────────────
HUB_D   = 17 * D.BEAD               # 13.6 (was 10.4 on the Ø5 axle): the Ø8.2 bore keeps a 2.7 wall, the
                                    # 2.6 it had. ONE lever constant: the hub OD *and* the arm depth (ARM_TX). Keeps
                                    # the feel on the clear cam above the round hub, and the arm as deep
                                    # as the hub is wide for a solid root.
ARM_LEN = 100.0                     # hub centre -> arm tip (knee reach, -Z)
ARM_TX  = HUB_D                     # arm depth in X (bending axis: knee pushes X) = the hub OD
ARM_WY  = 32 * D.BEAD               # 25.6 arm width in Y -- the face the player's leg bears on (no paddle).
                                    #   24 -> 25.6 (user, 2026-09-21): the wall outboard of each lobe
                                    #   recess was 0.8 (one bead); +0.8 a side makes it 1.6 while the
                                    #   cartridge lanes (HS_YC) stay exactly where they are.
                                    #   Was 20: the Ø10 die-spring cartridges (2026-09-21) are 14 wide, and
                                    #   each spring axis has to sit ON its follower lobe (an offset axis
                                    #   cocks a 3.2-long piston). The lobes are placed inward from this
                                    #   edge (HS_YC), so widening the lever IS what spreads the cartridges
                                    #   apart -- Y is the cheap axis here (user); X is not.
LEVER_HW = ARM_WY / 2               # UNIFORM lever half-width: hub, lobe and arm are all ±LEVER_HW (one
                                    #   clean section). It no longer reaches the ±12 walls, so...
PIVOT_BOSS_D = 8.0                  # ...the housing carries a small Ø8 thrust boss at each hub end for
PIVOT_CLR = 0.2                     #   low-friction Y location (a ring, not the whole hub face)
THROW   = 30.0                      # neutral -> full throw (deg, +theta about +Y). 30° is the useful max
# ...and the OTHER way, for STORAGE (user, 2026-09-28: "for the LKL we want a storage
# sweep angle as well. It should be able to sweep until it touches the LKV"). The lever
# folds back out of the way; what stops it is the VERTICAL lever's own arm.
#
# MEASURED IN THE ASSEMBLY, because this one cannot be derived here: the angle depends on
# where src.build puts the stations, and on knee_lever_vert's geometry, and this module
# can import neither (KV imports KL, so the arrow only points one way). Swept through
# build's own poses, the binding station is LKL itself at x -500 -- the one next to the
# vertical lever -- and its gap to vkl_kv_lever closes as 2.37 at 44, 1.64 at 45, 0.91 at
# 46, 0.17 at 47, 0.00 at 48. LKR, the next one over, still has 1.11 at 54.
#
# SO IT IS A NUMBER, AND src.build ASSERTS IT. That is the compromise: the value is
# written once here where the sweep needs it, and checked every build against the real
# poses, so a station that moves fails loudly instead of quietly closing the gap.
STORAGE = 47.0                      # deg the other way: the fold, stopped by LKV's arm
                                    #   knee travel (this is a SENSOR input -- the MT6701 reads angle at
                                    #   14-bit; servos pull the strings). 45° drove the swinging arm into
                                    #   the -Z cartridges; 30° + the front-bottom relief (see _cam_swept)
                                    #   + a receded piston clears the whole sweep.
_THR    = math.radians(THROW)

# ── feel: a Y-wide cam PLATE off the hub (points +Z at neutral, swings +X on throw) with a rounded
# LOBE along its top edge. Both spring cartridges bear FLAT followers on that lobe, so the return
# travel stays BOUNDED (= LOBE_RC*sin(throw)) even at the full 45° throw -- a tall flat blade face
# would migrate to its tip and demand ~2x the travel + reach. The lobe rides the Z-band just above the
# hub; each follower spans the lobe's Z-excursion so it stays on the lobe through the whole throw. The
# MAIN cartridge's follower touches at rest (sets the rest angle -> no rest screw); the HALF-STOP's is
# set back so it engages partway. Springs only PUSH, so the lever also swings FREE the other way (fold
# flat for storage). ──
HUB_TOP = HUB_D / 2                          # top of the round hub -- feel clears this (z 5)
AXLE_Z  = 0.0                                # lever AXLE centre Z. The whole feel block is anchored to
                                             #   this (via feel_place()), so RAISING the axle later slides
                                             #   the cartridges up automatically -- no other edits needed.
LOBE_RC = 9.5                                # lobe axis radius (pivot -> lobe) = axle->lobe Z. The whole
                                             #   feel block tracks -LOBE_RC (feel_place), so this sets how
                                             #   close the contact -- and the swept recess above it -- ride
                                             #   toward the axle. The recess just carves the hub as it
                                             #   rises, so the real limit is the solid WEB it leaves to the
                                             #   Ø8.2 axle bore: 9.5 leaves 1.7mm (measured; 9.0 left 1.2 once
                                             #   the 688ZZ bore arrived, so the user took 9.5 for the 1.6
                                             #   tier; 9.0 had left ~2.6 on the Ø5.2 bore; each -1mm of
                                             #   LOBE_RC costs 1mm of web, 0.8mm being the thin-wall floor).
                                             #   Ratio ARM_LEN/LOBE_RC = 100/9 = 11.1:1, follower travel =
                                             #   9*sin30 = 4.5mm. 9 (not 8) so the Ø1.4 feel coil keeps
                                             #   fatigue headroom for the tension screw (10.3N knee ceiling vs
                                             #   8N target). Raising THROW would swing the lobe higher,
                                             #   thinning the web -> raise LOBE_RC.
LOBE_R  = 2 * D.BEAD                         # 1.6 rounded lobe radius
LOBE_WY = 4.5                                # each lobe's / follower-tongue Y width. 6.0 -> 5.0 for the
                                             #   CENTRE DIVIDER, then -> 4.5 when the cartridge side walls
                                             #   went to the 2-bead tier: the divider is
                                             #   10.6 - 2*LOBE_WY once the walls are 1.6, so 4.5 is what
                                             #   keeps it at 1.6. See the assertion below.
                                             #   The two cartridges are flushed to the centre (dead wall gone)
                                             #   and the piston HEAD widened to (LOBE_WY+2) so the 0.8mm front
                                             #   lip survives -- so the tongue can be this wide within the 20mm
                                             #   arm (0.8mm arm-outboard wall) without a bigger coil.
CAM_TX  = 4 * D.NOZZLE_D                     # 3.2 cam-plate thickness in X (was 3.0 = 3.75 beads)
CAM_Y0, CAM_Y1 = HUB_Y0 + 1.0, HUB_Y1 - 1.0  # cam-plate Y span (wide enough to span both followers,
                                             #   which sit flush against the bearing walls)
# lobe +X extremum (what a follower touches) and its Z, at rest and at full throw:
LOBE_X0 = LOBE_R                              # follower contact X at rest (a=0)
LOBE_X1 = LOBE_RC * math.sin(_THR) + LOBE_R  # follower contact X at full throw
FOLL_TRAVEL = LOBE_X1 - LOBE_X0              # follower / piston travel over the throw (BOUNDED)
SWING_X = LOBE_RC * math.sin(_THR) + CAM_TX  # cam +X reach at full throw (sizes the housing swing slot)
# (No travel-stop boss: the old central stop screw was designed for the +Z cam PLATE and, in the -Z
#  arm-as-cam layout, its boss landed a block right in the arm's swing path. Throw is bounded by the
#  sweep clearance / the sensor; add a proper -Z-geometry stop later if a hard limit is wanted.)

# ── HALF-STOP = a self-contained PRELOADED spring CARTRIDGE (two printed parts + a die spring) ──────
# The coil pushes a PISTON whose rounded NOSE protrudes -X out of the cartridge front. The cam blade
# bears DIRECTLY on that protruding nose -- NO lever nub. Because the nose always sticks out (its
# protrusion > its travel), the cam never has to reach inside the cartridge, and the ROUNDED tip keeps
# clean contact as the cam rotates through the throw. The coil is preloaded against the piston (held
# forward by front side-lips), so contact makes a crisp force SHELF, then rises.
#   * <lane>_spring_tension_screw -- cartridge back, on the axis: pushes the seat washer = PRELOAD
#   * <lane>_position_screw       -- cartridge back, above it: head on the housing washer
#                                    = the cartridge's X home (engagement angle / rest bias)
# The cartridge prints as a BASE (U-channel, open top) + a ROOF that slides on via a Y sliding dovetail
# -> no internal-roof overhang, and the piston drops into the base before the roof caps it. Rounded
# anti-bind RIBS run along X on the floor + roof underside, giving the piston clean bearing lines
# (cures stiction/cocking; pairs with dry PTFE). The cartridge front clears the cam tip (STOP_TIP_X).
# Both springs are the SAME cartridge (printed twice): the MAIN sits so its follower touches the lobe
# at REST (sets the rest angle), the HALF-STOP is slid back HS_SETBACK so it engages partway. Each
# piston has a FLAT FOLLOWER face (spans the lobe Z-band) on a tongue that protrudes -X out of the
# cartridge front; the coil preloads it forward against front side-lips.
# FEEL SPRING = a STOCK DIE SPRING (user, 2026-09-21; BOM "LEVER FEEL SPRING -- DECIDED"):
# uxcell B0B772B9V2, JIS light-load (blue), Ø10 hole / Ø5 rod x 30 free (+-2), 142.2 N at its
# 40% max (12 mm) -> ~11.9 N/mm. It replaces the custom Ø6 x 1.4 music-wire coil, which had no
# stock source (spring index 3.3) and topped out ~1 kg at the knee. Chosen range 0.5..1 kg at the
# knee, set by the M4 tension screw (a button head, like every screw here). Rectangular wire, ground ends -> modelled as a TUBE, the
# convention for every spring here. LENGTH is the costly dimension (it is X, and X decides where a
# lever can mount); a die spring's length is fixed by the adjustable RANGE, its Ø by the top force.
HS_SPR_OD   = 10.0                  # die-spring HOLE Ø (the spring's working OD)
HS_SPR_ID   = 5.0                   # die-spring ROD Ø (its ID)
HS_SPR_FREE = 30.0                  # free length (uxcell +-2 -- measure on arrival)
HS_SPR_RATE = 142.2 / (0.40 * HS_SPR_FREE)     # ~11.85 N/mm: published max load / max deflection
HS_SPR_MAXDEFL = 0.40 * HS_SPR_FREE            # 12.0: JIS blue max compression -- never exceed
HS_SPR_INST = HS_SPR_FREE           # the BAY: piston seat -> spring-seat washer with the tension
                                    #   screw backed out = a nominal spring at ZERO preload
HS_PILOT_D  = HS_SPR_ID - 0.4       # 4.6: piston pilot nosing into the spring's Ø5 bore
HS_PILOT_LX = 6 * D.BEAD            # 4.8 pilot length
# SPRING SEAT = a steel WASHER, not a printed guide post (user: the printed post spent 3.2 of X).
# McMaster 91100A120, DIN 9021 M3: Ø9, Ø3.2 hole, 0.7..0.9 thick (modelled at the 0.9 max, so the
# housing recess always swallows it). The M4 screw's Ø4 thread cannot pass the Ø3.2 hole, so its
# chamfered end nests in the hole and self-centres the washer on the axis, and the Ø9 face carries the
# spring's ground end (Ø5..10) across most of its width. 0.9 of X, not 3.2.
WASHER_OD, WASHER_ID, WASHER_T = 9.0, 3.2, 0.9
# TENSION: an M4 x 10 BUTTON HEAD (2.5 key -- the instrument's one tool) threads an insert in the
# cartridge back wall, head out the back, and its end pushes the washer. The screw spans the whole
# 5-long insert at every setting, and the advance ends when the head lands on the cartridge back:
# 4.2 of preload + the 4.75 throw puts a nominal spring at 8.95 of its 12 (~75% = long-life).
HS_BACKWALL = INSERT_L + D.MIN_WALL # 5.8 cartridge back wall: the 5.0 insert + a ONE-bead web to the bay
                                    #   (the web only stops the insert while it is melted in; in use the
                                    #   screw's reaction pulls the insert toward its mouth, off the web)
HS_TEN_ADV  = M4_SCREW_L - HS_BACKWALL   # 4.2 tension-screw advance (preload range): backed out
                                    #   its end is flush with the wall's front, fully in its head is
                                    #   on the wall's back
HS_TEN_TAIL = HS_TEN_ADV + M4_BUTTON_HEAD_H    # 6.4: how far the head's top stands behind the
                                    #   cartridge back with the screw backed out
FOLL_H    = 7 * D.BEAD             # 5.6 follower FLAT-face height (Z). Centred (FOLL_DZ)
                                   #   so the window BOTTOM lands at the cartridge's already-open -Z bottom
                                   #   (no thin wall, no extra -Z) and the window TOP clears the +Z cap by
                                   #   0.8mm once the cap is raised to the mount (HS_ROOF_TZ). ~1.5mm tracks
                                   #   the lobe; the rest is strength.
FOLL_DZ   = 0.5                    # follower centre offset up from HS_Z: puts the window bottom on the -Z open
                                   #   face and the window top 0.8mm under the mount-height cap
HS_Z      = HUB_TOP + 2 * D.BEAD    # piston / follower centre Z: the HS_ARM tongue spans the lobe band
                                    #   (5.66..8) and clears the hub below; the Ø6 body clears the boss
HS_PISTON_WY = HS_SPR_OD            # piston HEAD = the spring's full Ø10 seat, square. The front lip is then
HS_PISTON_WZ = HS_SPR_OD            #   (channel - window)/2 = 2.95 -- far more catch than the old 0.8.
HS_FOLLOW_WY = LOBE_WY             # follower width (Y) = the lobe width (only has to cover the lobe); < body
                                  #   so the front lips still capture the body, and it stays narrow enough
                                  #   that the arm keeps a ~0.8mm printable wall outboard of each lobe recess
# CART_RECEDE pushes the whole cartridge back (-X in the placed frame) while the follower NOSE stays on
# the lobe -- so the piston BODY and front walls sit OUT of the swinging arm's arc, and only the thin
# follower tongue reaches into it. Sized (with the front-bottom relief) to clear the full 0..THROW sweep.
CART_RECEDE = 12 * D.BEAD            # 9.6 (was 8.0). The Ø10 cartridge's floor sits 2.0 lower than the Ø6
                                     #   one's, into the arm's sweep: at 8.0 the arm reached 0.9 into the MAIN
                                     #   cartridge's front-bottom edge at 30°. A 45° chamfer there cleared it
                                     #   but cut through the 1.6 front lip wall (user: weak point), so the
                                     #   whole cartridge recedes instead -- measured clear to 31° (MAIN; the
                                     #   HALF-STOP parks HS_SETBACK further back and clears past 33°).
HS_NOSE_PROTRUDE = FOLL_TRAVEL + 1.0 + CART_RECEDE  # tongue -X of the front (> travel: never retracts; the
                                                   #   extra CART_RECEDE lengthens the tongue = body recede.
                                                   #   8 mm clears the plain-prism cartridge to ~33° with NO
                                                   #   carve -- just push the whole box out of the arm's arc)
HS_BODY_LX = 4 * D.BEAD             # 3.2 piston body length in X (was 5 -- the saved 2mm pulled the whole
                                    #   cartridge forward, all
                                    #   spent on thread engagement without moving the leg-facing extent). The
                                    #   pilot + tongue add effective bearing length so 3mm won't cock.
HS_CLR    = 0.4                     # piston/coil <-> channel slide clearance (per side)
HS_WALL   = D.MIN_WALL_2P           # cartridge STRUCTURAL wall (floor / front); sides are HS_CART_WALL
HS_HOUS_WALL = D.MIN_WALL_2P        # housing shell wall around the pocket -- CONSTANT thickness, the
                                    #   outer /\ bottom parallels the pocket /\ (no thick flat bottom)
HS_LIP    = 4 * D.BEAD              # 3.2 front wall (the lips that catch the piston head). Was 1.6: this
                                    #   wall holds the spring's PRELOAD at rest -- constantly, on the
                                    #   half-stop, whose follower is off the lobe at rest -- up to ~80 N
                                    #   (full tension on a +2 long spring). At 1.6 the 2.2-tall strip
                                    #   under the tongue window bent at ~25 MPa and the side lips ~12:
                                    #   creep territory for PETG-GF under a steady load (want <= ~7).
                                    #   Bending goes as t^2, so 3.2 takes them to ~6 and ~3 (user,
                                    #   durability pass 2026-09-21). Costs 1.6 of X.
HS_TRAVEL = FOLL_TRAVEL + 0.5       # channel back-travel (>= follower travel)
HS_ROOF_SPLIT = HS_Z + HS_PISTON_WZ / 2 + HS_CLR   # channel ceiling = +Z cap underside (just above piston)
HS_ENGAGE_DEG = 15.0                          # half-stop engagement angle (throw deg)
# The rounded nose meets the rotating plate ~1.5 deg later than the flat-follower sin() model, so the
# setback is tuned by a solid-contact solve to first-contact at HS_ENGAGE_DEG (clamp-adjustable in use).
HS_SETBACK = 1.863                            # = engages at 15.0 deg (sin(15) would give 16.5 deg)
# X layout (canonical build = MAIN placement: follower face rests at the lobe's rest extremum LOBE_X0):
# nose rests on the cam plate's +X face (= lobe rest extremum, LOBE_X0 = CAM_TX/2) at neutral, so
# the MAIN follower is loaded at rest (90 / no movement); the lobe takes over as theta grows
HS_NOSE_TIPX = LOBE_X0              # follower face at rest -- bears on plate face / lobe extremum
HS_FRONT    = HS_NOSE_TIPX + HS_NOSE_PROTRUDE   # cartridge front face (clears LOBE_X1 at full throw)
HS_BODY_X0  = HS_FRONT + HS_LIP     # piston body front at rest (bears on the front lips)
HS_BODY_BX  = HS_BODY_X0 + HS_BODY_LX        # piston body back = coil FRONT seat at rest
HS_SPR_TIPX = HS_BODY_BX + HS_SPR_INST       # spring BACK = the seat washer's front face (screw backed out)
HS_WASH_BX  = HS_SPR_TIPX + WASHER_T         # washer back = screw tip = cartridge back wall's FRONT face
HS_BACK_X   = HS_WASH_BX + HS_BACKWALL       # cartridge BACK face (both insert mouths)
HS_CH_WY    = HS_PISTON_WY + 2 * HS_CLR      # channel clear width (Y) = 10.8 (Ø10 spring/piston + slide clr)
HS_CH_WZ    = HS_PISTON_WZ + 2 * HS_CLR      # channel clear height to the eaves (Z) = 10.8; a 45° gable
                                             #   roof rides above it (a 10.8 flat ceiling would be a bridge)
HS_WIN_WY   = HS_FOLLOW_WY + 0.4             # front-lip opening in Y: passes the tongue, catches the body
HS_CART_WALL = D.MIN_WALL_2P                 # cartridge SIDE wall. Was a bare 1.0 -- not a nozzle
                                             #   multiple, so it slices as one bead plus a gap-fill
                                             #   sliver (user). Now the 2-bead quality tier.
HS_CART_WY  = HS_CH_WY + 2 * HS_CART_WALL    # cartridge outer Y = channel + its own side walls
# cartridge Y placement: align each POCKET (the hole the cartridge slots into) so its outer edge is
# flush with the bearing wall's INNER face on that side -- the cartridge shares the bearing wall (no
# separate wall, no gap). (Earlier this aligned the block's OUTER face with the wall's outer face,
# spreading the cartridges too far.)
HS_POCKET_HW = HS_CART_WY / 2 + HS_CLR        # cartridge pocket (slot) half-width
# Cartridge Y: place each lobe/tongue as far INBOARD as the 0.8mm arm-outboard wall allows -- that (plus
# the wider head) is what frees the width. The two cartridges nearly meet at the centre (the old dead wall
# between them is gone); the wall-side gaps to the bearing walls are the leftover slack.
_ARM_LOBE_WALL = D.MIN_WALL_2P       # 1.6 wall outboard of each lobe recess (was 0.8, user)
HS_YC   =  (LEVER_HW - _ARM_LOBE_WALL - (LOBE_WY + 1) / 2)   # +Y lobe/cartridge centre (arm-outboard-wall limited)
MAIN_YC = -(LEVER_HW - _ARM_LOBE_WALL - (LOBE_WY + 1) / 2)   # -Y

# CENTRE DIVIDER — the wall BETWEEN the two cartridge pockets (user-caught in a render).
# At LOBE_WY 6.0 this was -0.20: the pockets OVERLAPPED, so the two 45° gable roofs met in
# a knife edge that tapered to nothing. Every CAD face was still 45° and a face-normal scan
# found no flat overhang at all -- the defect only appears in the SLICER. Below the height
# where that wedge falls under one bead it prints as nothing, the two cavities merge into
# one ~23 mm span, and its ceiling is unsupported. That is the "overhang in the middle".
#
# The fix is a real 2-bead wall, and the room comes from the LOBE, not from moving anything:
# narrowing LOBE_WY does double duty because HS_YC is measured INWARD from the lever edge
# while the pocket width grows OUTWARD from the lobe --
#     divider = 2*(HS_YC - HS_POCKET_HW) = 11.8 - 2*LOBE_WY
# -- so 5.0 buys 1.80. And it is free where it counts: HOUS_HW is DERIVED from HS_YC plus
# the cartridge half-width, and the two shifts cancel exactly, so the housing stays 13.90 and
# the axle, flange, magnet, cap and board cradle do not move at all. The cost is real but
# small and local: the lobe/follower contact line goes 6.0 -> 5.0 (line contact, so stress
# rises ~10%), and the piston head 8.0 -> 7.0, still 1.0 wider than the Ø6 coil it seats.
HS_DIVIDER = 2 * (HS_YC - HS_POCKET_HW)
assert HS_DIVIDER >= D.MIN_WALL_2P - 1e-6, (          # 1e-6: this is a tier check on a
    # float sum, and an exact-tier value lands a few ulp low — 1.5999999999999996 is a PASS.
    f"the two cartridge pockets leave a {HS_DIVIDER:.2f} divider between them, under the "
    f"{D.MIN_WALL_2P} two-bead tier — at or below 0 the gable roofs meet in a knife edge "
    f"and the merged ceiling is a wide unsupported span. The knob is LOBE_WY: the divider "
    f"is 2*(HS_YC - HS_POCKET_HW), and BOTH terms move with it, so a narrower lobe buys "
    f"divider at ~2 mm per mm.")
# ── POSITION SCREW ────────────────────────────────────────────────────────────────────────────────
# A second M4 x 10 BUTTON HEAD threads a SECOND insert in the cartridge back wall, straight ABOVE the
# tension screw, HEAD OUT: the head's crown bears on a steel washer at the bottom of a recess in the
# housing pocket's back face, and the 2.5 key reaches its socket through the washer's own Ø3.2 hole
# and a key way behind it. So the thread lives inside the cartridge's own back wall -- the housing
# carries no insert, no boss and no printed thread -- and the head is swallowed by the housing's rear
# wall, so the adjustment costs only its RANGE in X. (A screw in the housing needs insert + web +
# range BEHIND the pocket.) The washer spreads the crown's small contact ring over Ø9 of printed face.
# Above, not beside: Y is free, but the two cartridges already sit side by side, while above the axis
# the back wall is solid gable.
# THE TWO HEADS SHARE THE REAR WALL, AND THEIR HOLES MEET. The tension head rides a Ø8.4 way straight
# through that wall (HS_HEAD_WAY_D) and the position head sits in the washer's Ø9.4 recess above it.
# A two-bead web between the two would put the position screw 2.8 higher, and the cartridge cap, the
# pocket roof and the housing top all stand on that height -- the whole lever would hang lower to keep
# a web that carries nothing. So the offset is the least that (a) leaves the two-bead web between the
# two INSERT pockets in the cartridge (each a TEARDROP: horizontal bore, -Z->+Z print, so the lower
# one reaches r*sqrt2) and (b) lands the washer's lowest point one bead above the round of the way
# below it. The way's 45 deg print peak breaks into the recess floor in a narrow notch; the washer is
# seated on the rest of its rim and the two heads stay 2 mm apart.
_INS_R = INSERT_D / 2
HS_WASH_RECESS_D = WASHER_OD + 0.4  # the housing's seat for the position washer (and the head: Ø7.6)
HS_HEAD_WAY_D = M4_BUTTON_HEAD_D + 2 * HS_CLR      # 8.4: the tension head's way through the rear wall
HS_POS_DZ = max(_INS_R * math.sqrt(2.0) + D.MIN_WALL_2P + _INS_R,               # cartridge: insert webs
                HS_HEAD_WAY_D / 2 + D.MIN_WALL + HS_WASH_RECESS_D / 2)          # housing: 9.7
HS_POS_RECESS = M4_BUTTON_HEAD_H + WASHER_T     # 3.1 deep: the washer at the bottom, the head on it
HS_POS_RANGE = 4 * D.BEAD           # 3.2 of cartridge travel (+-1.6 about nominal)
HS_POS_NOM   = HS_POS_RANGE / 2     # nominal gap: cartridge back -> pocket back face (HALF-STOP)
HS_POS_FWD   = M4_SCREW_L - HS_BACKWALL + 0.4   # 4.6: how far the screw's end can reach -X of the back
                                                #   wall (into the channel's roof) with the head down
                                                #   on the cartridge back
# CAP: tall enough that the upper insert's teardrop keeps a 2-bead wall under the outer 45° gable.
# Both are 45° faces, so the wall is the vertical gap /sqrt2 -- solve for the cap top, then round the
# cap UP to whole beads over the channel eaves.
_POS_APEX = HS_POS_DZ + _INS_R * math.sqrt(2.0)                     # upper teardrop apex above HS_Z
_CAP_MIN = max(_POS_APEX - HS_CART_WY / 2 + D.MIN_WALL_2P * math.sqrt(2.0) - HS_CH_WZ / 2,
               D.MIN_WALL_2P)
HS_ROOF_TZ = math.ceil(_CAP_MIN / D.BEAD - 1e-9) * D.BEAD            # 3.2 over the eaves
HS_CART_Z1  = HS_ROOF_SPLIT + HS_ROOF_TZ     # cartridge +Z CAP top (the outer gable stands on it)
# INVERTED-U cartridge, OPEN on -Z (no separate roof): a solid +Z cap (toward the axle, narrow arc) + side
# walls, open on -Z where the arm's arc is WIDEST. The HOUSING floor is the -Z retaining wall (relieved to
# open air at the front, where the arm sweeps). The whole box is pushed clear of the arm's arc by
# CART_RECEDE. Plain rectangular prisms throughout (printability deferred).
HS_POCKET_X0 = SWING_X              # housing pocket front (cartridge front cantilevers -X into the slot)
# ── HOUSING REAR (behind the pockets). Both pockets end at ONE back face, HS_POS_NOM behind the
# HALF-STOP cartridge's nominal back (the MAIN parks HS_SETBACK further forward on its own position
# screw -- either cartridge still fits either slot). Behind that face: the position head's recess,
# then wall. The wall is sized by the TENSION head -- HS_TEN_TAIL proud of the cartridge back with
# the screw backed out -- so neither screw ever stands out of the housing's back face, even with the
# cartridge parked hard against the pocket back.
HS_POCKET_BX = HS_BACK_X + HS_SETBACK + HS_POS_NOM
HS_REAR_T = max(HS_TEN_TAIL, HS_POS_RECESS + D.MIN_WALL_2P)   # 6.4
HS_KEY_D = WASHER_ID + 0.2          # Ø3.4 key way to the position head (a 2.5 key is 2.9 across its
                                    #   corners; the washer's Ø3.2 hole is the tighter of the two)
# ── MOUNT (user): the housing's TOP FACE is already FLUSH with the chassis underside
# (HOUS_Z1 = BODY_Z = Z_BOT), so the mount needs no yoke, no boss and no floating part —
# FUSED OCTAGON TENONS rise straight off that face into matching mortises in the chassis
# cross-ribs. (The old double-christmas-tree floating tenon + its yoke plate are gone: they
# existed because the housing used to print +Z→-Z and could not carry a protruding tenon.
# It prints -Z→+Z now, so the tenon is just part of the part.) ──
RIB_PITCH = D.MOTOR_X_STEP          # THE motor pitch. The bottom is a SLAB now, not a comb of
                                    # cross-ribs, and the mortise grid is D.LEVER_PITCH (8.8) --
                                    # see _TEN_PITCH down in the prism block, where the housing X
                                    # extents that bound the stations are finally known. This is
                                    # kept only for readers who reason in motor pitches.
BODY_Z    = HUB_TOP + 3 * D.BEAD    # body underside in local Z: the hub top (5.2) + a 2.4mm AIR
                                    #   gap (no material between the lever and the body). Raising the axle
                                    #   is equivalent to lowering BODY_Z here; MOUNT_Z tracks it (= -82.55)
# ── OCTAGON slide-joint (cadkit): cadkit's octagon slides along its extrude axis, so we
# rotate it 90° about Z — the slide becomes +Y (the knee-DEPTH adjustment) and the roof
# stays +Z. Both halves print -Z->+Z (facing 'up') -> the octagon family -> self-supporting
# on BOTH sides. One joint SIZE, two LENGTHS: short TENONS on the housing (its own Y span)
# and a long RIB MORTISE (the whole knee-depth range).
MORT_CLR  = 0.3                     # mortise clearance (slide fit)
# THE JOINT'S BOUNDING BOX IS THE RIB (user, 2026-09-10): the rib (D.XBAR wide) keeps a
# two-bead wall either side of the MORTISE, and the mortise is the tenon + MORT_CLR, so the
# tenon's flat-to-flat is what is left. It used to be a flat 8 beads (6.4), which put the
# 1.6 on the octagon's own shoulder and left the rib 1.7 beside the mortise.
_JW       = D.XBAR - 2 * D.MIN_WALL_2P - 2 * MORT_CLR   # 6.6 octagon flat-to-flat width.
#                                    Sized on the MECHANICS (knee-strike
#                                    pull-out): ~3x the shear area and 2x the retention shoulder of the
#                                    old 3mm, while the rib keeps ~77% of its section as a sound arch
#                                    (2mm side columns + 4.2mm top beam). The mortise roof now rises
#                                    into the harness lanes -- the rib raceways are removed and the
#                                    cables left colliding for now (a cable-routing pass comes next).
_JHW      = _JW / 2.0               # octagon half-width in X (after the Z-rotation)
_JUP      = PrintSpec(nozzle=0.8, material="PETG-GF", facing="up")
def _lever_joint(length):
    """The mount joint at a given SLIDE length (Y). MORT_CLR shrinks the tenon for fit."""
    return joint(_JW, length, tenon=_JUP, mortise=_JUP, clearance=MORT_CLR)
TEN_H     = _lever_joint(8.0).height    # how far a tenon rises above its mating face (5.82;
                                        # the length arg is a probe — height ignores it)
MORT_Y0   = -3 * D.BEAD           # -2.4 mortise -Y mouth (opens outboard of the -Y rail for slide-in)
# global mount: MOUNT_X = -501 is itself a rib X in the half-pitch comb, which is what lets
# the tenon stations be generated on a plain 23 mm walk from the axle. build.py poses the
# lever here; chassis.py cuts the rib mortises into EVERY rib at the same Y.
# ENGAGEMENT WARNING (measured, and worth reading before trusting the render): the chassis
# rails start at y = -133.75 and this pose puts the housing's +Y face at -134.85, so at
# MOUNT_Y the housing sits 1.1 mm entirely OUTBOARD of the rib comb and the tenons touch
# nothing. It is a legal state — the fully-slid-OUT end of the knee-depth travel — but it
# is not an installed one: engagement only starts once the lever is pushed +Y, and equals
# (slide - 1.1). If the assembly should SHOW the lever mounted, MOUNT_Y wants to move +Y by
# the intended depth; that changes where the whole lever appears, so it is left alone here.
# MOUNT_Z tracks the housing TOP, not BODY_Z: with the bigger race the top is set by
# the bearing seat, and the TOP is what must stay flush on the chassis underside.
# The axle simply sits lower in the guitar by the difference.
# SEAT ROOF (user, 2026-09-10). The springs load the axle into the +X side of each bearing, and
# with the +X face open that side is held from below only unless something ties the two
# sides together OVER the seat. So the top carries a BRG_WALL (1.6) band parallel to the
# seat's 45° print peak, and where that band's outer edge meets the top face it has to land
# INSIDE the mount tenon's stem (beside the stem is the rib's lip, not free space). The
# band's outer edge is the line x + z = (seat radius + wall)·√2, so the top sits where it
# crosses the stem wall (half-width _JW/4). The whole lever drops by the difference.
_SEAT_ROOF_Z = (BRG_SEAT_D / 2 + BRG_WALL) * math.sqrt(2.0) - _JW / 4
HOUS_TOP_Z = max(BODY_Z, BRG_OD / 2 + BRG_WALL, _SEAT_ROOF_Z,
                 max(CHIP_DROP, PCB_WZ - CHIP_DROP) + CEIL_CLR)
                                            # ...and the sensor board, which must stay
                                            # CEIL_CLR under the chassis EITHER WAY UP: as
                                            # drawn its top edge is CHIP_DROP over the axle
                                            # (10.5, not binding); turned over about the
                                            # axle, which is how the one board design goes
                                            # into a RIGHT-HAND housing, it is the long end
                                            # that is up (11.8 + 0.4 = 12.2, binding by 0.2).
# X is SNAPPED AGAIN once the tenons are known (see _TEN_PHASE, below the housing block): the
# TENONS are what must land on the grid, not the housing's origin, and the tenon set carries a
# phase now. This first value is the nominal; nothing between here and there reads it but
# MOUNT_POSE, which is rebuilt with it.
MOUNT_X = D.rib_comb_x(-501.0)
MOUNT_Y, MOUNT_Z = -148.75, MB.BED_Z - HOUS_TOP_Z
# (MOUNT_Z read the bed as a spelled -75.15, which went stale when SCREW_TOP_Z /
#  SCREW_PULLEY_Z / XBAR snapped to the grid — the live bed is MB.BED_Z = -74.95.)
MOUNT_POSE = (MOUNT_X, MOUNT_Y, MOUNT_Z)
# the mortise (slot) runs from the player face ALL THE WAY to the guitar's Y midpoint -- the lever's
# nub slides +Y along it to the player's chosen knee depth, then the retention screw locks it.
MID_Y     = -37.0                   # guitar Y-midpoint (= chassis (Y_LO + Y_HI)/2)
# The mortise used to stop at MID_Y, which was arbitrary — it was "halfway in" and
# nothing needed more. It does now: the VERTICAL lever is 77.4 deep in +Y, so a slot
# ending at mid-Y forced it to sit that much further -Y than the horizontal levers,
# putting its arm out in FRONT of the knee instead of above it. The player would have
# had to pull their knee back to reach it, when the whole point of a vertical lever is
# to lift without moving (user). The slot now runs to the inside edge of the
# instrument, which is as far as it can go and enough for any of them.
MORT_Y_END = D.LIGHT_WIN_Y0
#   ^ +Y end of the knee-depth slide, guitar Y: every mortise runs the full width of the
#     instrument and stops AT the transparent window's face (user, 2026-09-16). It ran to the
#     +Y rail's inner face before the window existed. No wall between the two -- the window is
#     solid (transparent) material in the finished print, so it IS the end of the slot.
                                    # = the chassis +Y rail INNER face, spelled via the same
                                    # D constants chassis.Y_HI uses (import direction forbids
                                    # chassis; the old 54.75 had gone stale twice over)
MORT_Y1   = MORT_Y_END - MOUNT_Y    # ...in the local frame
# DEPTH LOCK — still DEFERRED, and UNDESIGNED (it lands with the sensor mount, which shares
# the same +Y region). The octagon carries the knee-strike load; the lock only has to hold the
# chosen depth. It is an M4 button head or it is no screw at all (user: one screw, one key),
# and an M4 does not fit beside a tenon -- the octagon leaves the rib a 2 mm side column -- so
# it wants its own site or a printed detent.


def _bearing():
    """MR85ZZ dummy (axis Y), -Y face at y=0."""
    o = cyl_y(BRG_OD, BRG_W, y0=0.0)
    b = cyl_y(BRG_ID, BRG_W + 0.2, y0=-0.1)
    return o.cut(b)


def feel_dummies(place, prefix="", hs_setback=None):
    """The two feel cartridges' hardware, posed by `place` — the caller's own
    feel_place (horizontal), vplace (vertical) or pplace (pedal).

    Shared because all three levers carry the SAME cartridge: MAIN (at MAIN_YC)
    whose follower touches the lobe at REST (sets the rest angle), and HALF-STOP
    (at HS_YC, slid +X by HS_SETBACK) that engages partway. Each carries the Ø10
    die spring, its steel seat WASHER, the TENSION screw (preload) in the
    cartridge's lower insert, and the POSITION screw in the upper insert, whose
    head bears on a second washer in the housing's pocket back face (that
    screw's stand-off IS the cartridge's X home). Both are M4 x 10 button heads.

    Extracted so a lever cannot quietly show different hardware from its
    siblings: the vertical lever was emitting its cartridge bodies with NO
    springs, screws or back-stops at all, which read in the assembly as a lever
    with no feel system.
    """
    p = f"{prefix}_" if prefix else ""
    out = []

    def x_axis(solid, x, y, z):          # built along +Z from 0 -> along +X from x
        return solid.rotate((0, 0, 0), (0, 1, 0), 90).translate((x, y, z))

    def _x_screw(x_under, y, z):         # M4 x 10 button: head's UNDERSIDE at x_under, shank -X
        return (m4_button_screw(M4_SCREW_L).rotate((0, 0, 0), (0, 1, 0), 90)
                .translate((x_under + M4_BUTTON_HEAD_H, y, z)))

    washer = cyl(WASHER_OD, WASHER_T, z=0.0).cut(cyl(WASHER_ID, WASHER_T + 2, z=-1.0))
    # hs_setback: where the HALF-STOP cartridge parks on its position screw -- a per-lever
    # number, because the engagement angle depends on that lever's lobe radius (see HS_SETBACK)
    _hs = HS_SETBACK if hs_setback is None else hs_setback
    for nm, dx, dy in (("main", 0.0, MAIN_YC - HS_YC), ("half_stop", _hs, 0.0)):
        yc, zp = HS_YC + dy, HS_Z + HS_POS_DZ
        # every dummy is BUILT in the +Z/+X frame then placed to its installed spot (below the axle,
        # spring -X) -- same map as the cartridge, so they track AXLE_Z too. Drawn with the tension
        # screw BACKED OUT: the spring at its free length, the washer on the back wall.
        out.append((f"{p}{nm}_spring", place(x_axis(
            cyl(HS_SPR_OD, HS_SPR_INST, z=0.0).cut(cyl(HS_SPR_ID, HS_SPR_INST + 2, z=-1.0)),
            HS_BODY_BX + dx, yc, HS_Z))))
        out.append((f"{p}{nm}_spring_seat_washer", place(x_axis(washer, HS_SPR_TIPX + dx, yc, HS_Z))))
        # TENSION: end on the washer (nested in its Ø3.2 hole), head out the cartridge back.
        out.append((f"{p}{nm}_spring_tension_screw",
                    place(_x_screw(HS_WASH_BX + M4_SCREW_L + dx, yc, HS_Z))))
        out.append((f"{p}{nm}_spring_tension_insert",                    # Ø6×5 insert, flush at the back face
                    place(_seated_insert((HS_BACK_X + dx, yc, HS_Z), (0, 1, 0), -90))))
        # POSITION: head ON the housing washer at the bottom of its recess, so the screw's -X reach
        # is fixed by the POCKET, whichever cartridge it sits in.
        out.append((f"{p}{nm}_position_screw", place(_x_screw(HS_POCKET_BX, yc, zp))))
        out.append((f"{p}{nm}_position_insert",
                    place(_seated_insert((HS_BACK_X + dx, yc, zp), (0, 1, 0), -90))))
        out.append((f"{p}{nm}_position_washer",
                    place(x_axis(washer, HS_POCKET_BX + M4_BUTTON_HEAD_H, yc, zp))))
    return out


def cart_dummies(place, prefix="", stroke=(0.0, 0.0), hs_setback=None):
    """The two cartridges themselves — base and piston. `stroke` is the
    (main, half_stop) piston retraction for a posed throw; 0 at rest."""
    p = f"{prefix}_" if prefix else ""
    out = []
    for nm, off, s in (("main", CART_MAIN_OFFSET, stroke[0]),
                       ("half_stop", (HS_SETBACK if hs_setback is None else hs_setback, 0.0, 0.0),
                        stroke[1])):
        out.append((f"{p}{nm}_cart_base", place(cart_base.translate(off))))
        out.append((f"{p}{nm}_cart_piston",
                    place(cart_piston.translate(off)).translate((-s, 0, 0))))
    return out


def axle_dummies(place, prefix, z_bot, z_top, flip=None, shim_top=None, axle=True):
    """Bearings, magnet and the sensor stack — everything on the axle that is not
    the lever. `place` poses the whole group; z_bot/z_top size the board.

    `axle` adds the printed AXLE and MAGNET CAP too (user, 2026-09-21: LKV and all five
    pedals had neither -- only the horizontal stations drew them, because LKL's own
    builder adds them with its throw applied; that builder passes axle=False).

    `shim_top` overrides where the SHIM stops. It defaults to the housing ceiling,
    which is right when the thing pressing the shim is the chassis — but the foot
    pedal's ceiling is the bar's +Y face, and the lid groove is cut INTO that face,
    so the shim has to stop at the groove floor and let the LID do the pressing."""
    out = [(f"{prefix}_bearing_{i}", place(_bearing().translate((0, by, 0))))
           for i, by in enumerate((-(BRG_Y0 + BRG_W), BRG_Y0))]   # inner faces at ±BRG_Y0
    out.append((f"{prefix}_magnet", place(cyl_y(MAG_D, MAG_T, y0=MAG_Y0))))
    # the axle's END SCREW + washer, on the -Y tip (axisymmetric, so they need no swing)
    out.append((f"{prefix}_axle_washer", place(
        cyl_y(AXLE_WASHER_OD, AXLE_WASHER_T, y0=AXLE_Y0 - AXLE_WASHER_T)
        .cut(cyl_y(AXLE_WASHER_ID, AXLE_WASHER_T + 2.0, y0=AXLE_Y0 - AXLE_WASHER_T - 1.0)))))
    out.append((f"{prefix}_axle_screw", place(
        m4_button_screw(AXLE_SCREW_L).rotate((0, 0, 0), (1, 0, 0), 90)     # shank -Z -> +Y
        .translate((0.0, AXLE_Y0 - AXLE_WASHER_T - M4_BUTTON_HEAD_H, 0.0)))))
    out += [(n, place(s))
            for n, s in sensor_parts(z_bot, z_top, prefix=prefix, flip=flip)]
    _sh = pcb_shim(z_bot, z_top if shim_top is None else shim_top, flip)
    if _sh is not None:
        out.append((f"{prefix}_pcb_shim", place(_sh)))
    if axle:
        out.append((f"{prefix}_axle", place(kl_axle)))
        out.append((f"{prefix}_magnet_cap", place(kl_magnet_cap)))
    return out


def demo_parts():
    """Bought-part dummies in the local frame: (name, shape). Assembly-only."""
    # (no kl_axle dummy: the axle is PRINTED now — +Y journal integral to
    #  the lever, -Y journal = the kl_axle_insert part)
    out = axle_dummies(lambda s: s, "kl", HOUS_Z0, HOUS_Z1, axle=False)   # build adds them, swung
    out += feel_dummies(feel_place)
    # THE TRAVEL STOP, shown at its BACKED-OUT setting = the housing's own maximum, so
    # the assembly reads as the full throw rather than a random adjustment. (This line
    # used to say "no travel-stop screw: the +Z-cam-era stop boss was removed" -- it is
    # back, under the cartridges instead of over the cam, where there is room for it.)
    # ...AND THE INSERT IN IT (user: "I still don't see the fitted insert"). cut_anchor
    # leaves the pocket empty on purpose -- its whole idea is that the first build
    # self-taps and the insert is the REPAIR. But this screw is turned to set the lever's
    # travel and turned again whenever the feel changes, which is not what a formed
    # thread in PETG-GF is for, so here the insert goes in at BUILD time and the self-tap
    # below it is just the pilot it was always going to be. Seated from the same point
    # and direction as the anchor, so the two cannot drift.
    out.append(("kl_travel_stop_insert",
                seated_insert(M4, (STOP_ANCHOR_X, 0.0, STOP_Z), (1.0, 0.0, 0.0))))
    out.append(("kl_travel_stop_screw",
                m4_button_screw(STOP_SCREW_L)
                .rotate((0, 0, 0), (0, 1, 0), -90)          # head top -> -X, shank +X
                # ...m4_button_screw measures its LENGTH from under the head, so the
                # head's own 2.2 comes off the head end, not the tip
                .translate((STOP_TIP_OUT - STOP_SCREW_L - M4_BUTTON_HEAD_H,
                            0.0, STOP_Z))))
    return out


def sensor_board():
    """THE board — one design for every lever (user). Drawn once, in its own frame:
    chip on the axle axis, top edge CHIP_DROP above it. Levers pose it; none of them
    redraws it, which is what makes "identical" structural rather than a promise."""
    return box_at(PCB_WX, PCB_T, PCB_WZ, x=(PCB_X0 + PCB_X1) / 2,
                  y=PCB_Y + PCB_T / 2, z=(PCB_Z0 + PCB_Z1) / 2)


def sensor_connector():
    """J1 as SPECIFIED (docs/lever-sensor-respin.md): S8B-PH-SM4-TB, 8-way SMT side-entry
    PH, on the MAGNET face (single-sided, like every board on the shared panel). SMT, so no
    post tails. It stands on end at the -X edge, mouth facing -X, MATED so the plug's run
    is reserved. cadkit builds it row along X,
    mouth at y=0 with the body +Y and the plug -Y, height +Z off the board: this maps its
    X to -Z (length vertical), Y to +X (mouth -> -X) and Z to -Y (off the magnet face)."""
    c = jst_ph_side_header(CONN_N, mated=True)
    c = c.rotate((0, 0, 0), (0, 0, 1), 90)       # X->Y, Y->-X
    c = c.rotate((0, 0, 0), (1, 0, 0), -90)      # Y->-Z, Z->Y ... (checked by the bbox below)
    c = c.rotate((0, 0, 0), (0, 0, 1), 180)
    return c.translate((CONN_MOUTH_X, PCB_Y, CONN_ZC))


def _install(s, z_bot, z_top, flip=None):
    """Pose a board-frame solid into a housing: identity, or turned over."""
    return (s.rotate((0, 0, 0), (0, 1, 0), 180)
            if board_flip(z_bot, z_top, flip) else s)


def sensor_pcba():
    """The ASSEMBLED board as ONE part (user): the laminate, every part the fab places on
    it and its connector, fused. It arrives from the fab as one thing and is handled as
    one thing, so the model has one part for it -- not a board and twenty-five loose
    boxes. The connector is drawn MATED (sensor_connector), so the part also reserves the
    run the harness plug needs.

    Fused in ONE multi-fuse and checked by volume (a fuse can hand back a valid solid with
    material missing). The parts stand ON the board face and beside each other, so the
    whole is exactly the sum of its pieces."""
    board = sensor_board()
    parts = [s for _n, s in sensor_hardware()] + [sensor_connector()]
    solid = board.val().fuse(*[s.val() for s in parts], glue=True).clean()
    want = board.val().Volume() + sum(s.val().Volume() for s in parts)
    assert abs(solid.Volume() - want) < 1e-3 * want, (
        "the assembled sensor board fused to %.2f mm3, its pieces sum to %.2f"
        % (solid.Volume(), want))
    return cq.Workplane(obj=solid)


_SENSOR_INK = []


def sensor_silk():
    """The board's lettering, both faces, in sensor_pcba's frame -- its own part (white
    ink). The board is drawn from this module's own datums, not from board_geom.solid,
    so its pose is read off the drawn board (cadkit.board_check.place) rather than
    written a second time. Found once."""
    if not _SENSOR_INK:
        from cadkit.board_check import place
        _SENSOR_INK.append(place(sensor_pcba(), BG.load("lever_sensor"),
                                 BG.ink("lever_sensor")))
    return _SENSOR_INK[0]


def sensor_parts(z_bot, z_top, prefix="kl", flip=None):
    """The assembled board and its lettering, posed for this housing. Both come from
    sensor_pcba / sensor_silk unchanged and are only ROTATED, so there is exactly one
    board design in the project."""
    return [(f"{prefix}_pcb", _install(sensor_pcba(), z_bot, z_top, flip)),
            (f"{prefix}_pcb_silk", _install(sensor_silk(), z_bot, z_top, flip))]


def pcb_shim(z_bot, z_top, flip=None, right=False):
    """PRINTED SHIM (user): the board is one size and the housings are not, so the
    slack between the board's top edge and the instrument is taken up by a plastic
    block that slides down the SAME grooves on top of it. The chassis then presses
    the shim, the shim presses the board, and the retention stays exactly what it
    was — no fastener, no second board design. Returns None where the board already
    reaches the ceiling (the horizontal lever), so the part only exists where it is
    needed."""
    gap = (z_top - CEIL_CLR) - board_z(z_bot, z_top, flip, right)[1]
    if gap <= CR_CLR:
        return None
    bx0, bx1 = board_x(z_bot, z_top, flip, right)
    return box_at(bx1 - bx0, PCB_T, gap - CR_CLR, x=(bx0 + bx1) / 2,
                  y=PCB_Y + PCB_T / 2,
                  z=board_z(z_bot, z_top, flip, right)[1] + CR_CLR + (gap - CR_CLR) / 2)


def _cradle(w, z_bot=None, z_top=None, x_max=None, flip=None, right=False):
    """Add the MT6701 board cradle to the housing (user). Everything here grows UP
    off the same bed as the housing and has no ceiling anywhere, so it needs no
    supports; see the constant block for the retention scheme and the socket cone.

    Built as: two side webs + a front plinth + a floor, then ONE slot cut through
    them for the board — that slot IS both grooves. Cutting it after the webs is
    what makes them: the web material outboard of the slot survives as each
    groove's outer wall."""
    z_bot = HOUS_Z0 if z_bot is None else z_bot
    z_top = HOUS_Z1 if z_top is None else z_top
    pcb_z0, pcb_z1 = board_z(z_bot, z_top, flip, right)
    bx0, bx1 = board_x(z_bot, z_top, flip, right)   # installed edges — the flip swaps them
    conn_zc = conn_z(z_bot, z_top, flip, right)
    conn_mx = conn_mouth_x(z_bot, z_top, flip, right)
    _sx = -1.0 if _turned(z_bot, z_top, flip, right)[1] else 1.0
    x_max = CR_X1_MAX if x_max is None else x_max
    # The BOARD ITSELF must fit the housing's +X face, not just its groove web.
    # x_max below only caps the NEAR web, on the assumption the far side is never the
    # long one — and that assumption breaks the moment the board is turned or flipped
    # (a 180 puts the -25 edge at +25; the pedal's 90 puts a 7 edge here). Both were
    # caught by hand; this is the guard so they cannot come back silently.
    assert max(bx0, bx1) <= x_max + 1e-6, (
        f"the board as installed reaches x {max(bx0, bx1):.2f}, past the housing's "
        f"{x_max:.2f} +X face — it would stand outside the part")

    inner0, slot0, outer0 = _cr_faces(bx0)
    inner1, slot1, outer1 = _cr_faces(bx1)
    # WHICH SIDE GETS THE FULL-HEIGHT WEB is decided by the DRIVER BORE, not by the
    # sign of X. The board is asymmetric about the chip, so one groove sits far from
    # the axle axis and the other close to it; the close one cannot run full height
    # (it would stand inside the bore), the far one can. Turning the board over
    # swaps which is which — and assuming -X was always the far side left the
    # vertical lever with a full-height web 1.30 from the axis, straight through the
    # bore, and its housing in two pieces.
    _far, _near = (((inner0, outer0), (inner1, outer1)) if abs(inner0) > abs(inner1)
                   else ((inner1, outer1), (inner0, outer0)))
    # the NEAR side is the one that risks reaching past the housing's own +X face...
    _ni, _no = _near
    # ...AND THE ONE THAT NEEDS A LEG BESIDE THE DRIVER BORE. Running this web full
    # height only works if something carries it past the socket, and at its drawn width
    # nothing does: the web is 5.85 wide, the bore is 14, so the bore eats all of it but
    # a 0.15 mm rind and everything above stood on that (check_thin, 602 samples at
    # 0.15). Widened to clear SOCK_R by a two-bead wall it has a real column from the
    # plinth to the ceiling, and the material over the socket becomes an arch springing
    # off it -- which is what the teardrop roof is for.
    _no = math.copysign(min(x_max, max(abs(_no), SOCK_R + D.MIN_WALL_2P)), _no)
    _near = (_ni, _no)
    # write the capped extents back, because the plinth and the floor span
    # outer0..outer1 and would otherwise be built to the UNcapped width
    if _far[1] > 0:
        outer1, outer0 = _far[1], _no
    else:
        outer0, outer1 = _far[1], _no
    # SIDE WEBS, and they are deliberately UNEQUAL. The -X one runs the full height
    # of the cradle; the +X one stops at the plinth top, because everything above
    # that on this side is inside the driver bore and could not be printed anyway
    # (its inner face at 1.30 and top at -7.0 sit 7.12 from the axis, just outside
    # SOCK_R). So the +X side gives a 5 mm groove at the bottom and the -X side
    # carries the rest — which is the trade the user asked for, and it is a good
    # one: the -X web is 14 from the chip with a full-height groove, so it has far
    # more leverage on the board than a short +X one ever had.
    # ...and the near web runs FULL HEIGHT too, with the driver bore cut out of it.
    # It used to stop at the bore, on the reasoning that everything above that was
    # inside it. That is true of the band just above the plinth and false higher up: the
    # socket is a TEARDROP, so its apex is at SOCK_R * sqrt(2) and the material above
    # THAT is carried by the teardrop's own flanks, exactly as every sideways bore in
    # this project is. Cut short, the near side ended 17 mm below the shim, which is why
    # both shims could be lifted straight out sideways -- the far web was holding them
    # alone, and the plug tunnel takes its groove flanks away at that height.
    # BOTH WEBS STAND ON THE BED, so neither has an underside to ramp. There used to be
    # a 45 deg ramp here for a web that started partway up, and with it a note about how
    # it cost the groove its lowest CR_Y1-CR_Y0 of engagement -- which is exactly why a
    # partway-up web is not worth having: on the horizontal lever the ramp would have
    # eaten 8.35 mm of a 1.35 mm shim's worth of groove. The near web earns its full
    # height from the leg beside the socket instead.
    for a, b in (_far, _near):
        w = w.union(box_at(abs(b - a), CR_Y1 - CR_Y0, z_top - z_bot,
                           x=(a + b) / 2, y=(CR_Y0 + CR_Y1) / 2,
                           z=(z_bot + z_top) / 2))
    # front plinth: the slab the board's -Y face seats on, and the body the screw
    # boss lives in. Its top IS the socket cone's floor.
    w = w.union(box_at(outer1 - outer0, CR_SLOT_Y0 - CR_Y0, CR_PLINTH_Z1 - z_bot,
                       x=(outer0 + outer1) / 2, y=(CR_Y0 + CR_SLOT_Y0) / 2,
                       z=(z_bot + CR_PLINTH_Z1) / 2))
    # ...RELIEVED over the board's interior (2026-09-21). As a full-width slab it met the
    # magnet face wherever parts sit low on it -- the long-deferred board-parts-vs-housing
    # overlaps. The magnet face is now seated by the two edge grooves' front flanks alone
    # (the CR_EDGE_KEEP bands are kept clear of parts by rule; a bottom-edge strip is not --
    # the pre-route layout has parts 0.16 from that edge). Sized
    # off no layout: the whole interior, as deep as the tallest part that may stand on the
    # magnet face, so the re-spun board fits it whatever its placement.
    _ix0, _ix1 = sorted((bx0, bx1))
    _ix0, _ix1 = _ix0 + CR_EDGE_KEEP, _ix1 - CR_EDGE_KEEP
    _deep = max(r[4] for r in SENSOR_BOM) + CR_CLR + 0.3
    _rz0 = pcb_z0
    w = w.cut(box_at(_ix1 - _ix0, _deep + 1.0, (CR_PLINTH_Z1 + 1.0) - _rz0,
                     x=(_ix0 + _ix1) / 2, y=CR_SLOT_Y0 - _deep / 2 + 0.5,
                     z=(_rz0 + CR_PLINTH_Z1 + 1.0) / 2))
    # floor under the board + the tie between the two webs behind it
    w = w.union(box_at(outer1 - outer0, CR_Y1 - CR_SLOT_Y0, pcb_z0 - z_bot,
                       x=(outer0 + outer1) / 2, y=(CR_SLOT_Y0 + CR_Y1) / 2,
                       z=(z_bot + pcb_z0) / 2))
    # THE BOARD SLOT (both grooves in one cut): open at +Z — the install axis —
    # and bottoming on the floor at pcb_z0, which is the board's -Z seat.
    w = w.cut(box_at(slot1 - slot0, CR_SLOT_Y1 - CR_SLOT_Y0, (z_top + 2.0) - pcb_z0,
                     x=(slot0 + slot1) / 2, y=(CR_SLOT_Y0 + CR_SLOT_Y1) / 2,
                     z=(pcb_z0 + z_top + 2.0) / 2))
    # ── THE PLUG'S TUNNEL. J1 lives on the magnet face and its plug runs -X in the gap
    # between the board and the housing, so the -X web needs a way through, open out the
    # TOP (the board is lowered in, and a lid over it would be a flat overhang). It stops
    # at the housing's +Y face: the magnet stand-off (AXLE_LAND_T) makes that gap
    # PH_SIDE_H + CONN_GAP, so the tunnel NEVER cuts the cheek -- the old relief took 0.85
    # of the 1.6 wall beside the half-stop pocket (user).
    _cy0 = plug_tunnel_y()[0]
    _cz0 = conn_zc - CONN_L / 2 - CONN_POCKET
    _cx0 = conn_mx - _sx * CONN_UNPLUG                 # the plug's full unplug stroke
    _cx1 = conn_mx + _sx * (PH_SIDE_D + CONN_POCKET)
    _cz1 = z_top + 1.0
    w = w.cut(box_at(abs(_cx1 - _cx0), PCB_Y - _cy0, _cz1 - _cz0,
                     x=(_cx0 + _cx1) / 2, y=(_cy0 + PCB_Y) / 2,
                     z=(_cz0 + _cz1) / 2))
    # SOCKET CONE — reserved so kl_magnet_cap can be driven with the cradle in
    # place. Cut rather than merely avoided: it is a guarantee, not an intention,
    # and anything a later round adds in this zone now gets removed instead of
    # silently blocking the driver. Teardrop, like every sideways bore here.
    # IT STARTS AT THE HOUSING FACE, which is also the AXLE's clearance through here.
    # It used to start at MAG_Y0, the cap's rim, to protect two things that lived in the
    # band below it: the axle flange's printed CONTACT RIB and the +Y bearing seat's
    # outboard skin. Both are gone -- the bearings sit flush and the seats run out
    # through both faces (see cut_axle_stack) -- and CR_Y0 IS the housing's +Y face, so
    # starting there reaches nothing inside the housing at all.
    #
    # What it does reach is the 1.6 mm band between that face and the cap's rim, where
    # the axle FLANGE stands at AXLE_FLANGE_D (Ø12.8, r 6.40). Nothing was clearing it:
    # the socket started outboard of it and the webs used to stop below it. The moment
    # the near web ran full height it went straight through the flange -- 56 mm3 on every
    # lever station, which the overlap gate could not report because housing-vs-axle is
    # allow-listed as a designed contact (user, 2026-09-29: "this wall is clipping the
    # axel"). Ø14 clears Ø12.8 with 0.6 all round.
    _sock_y0 = min(MAG_Y0, CR_Y0)
    w = w.cut(printable_bore(SOCK_D, (CR_Y1 + 1.0) - _sock_y0, (0.0, _sock_y0, 0.0),
                             (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    return w


def plug_tunnel_y():
    """(y0, y1) of the plug's tunnel through the cradle: off the magnet face by the
    connector's height and its pocket clearance, never into the housing's cheek. The
    plug's wires have this width and no more until they are clear of the cradle."""
    return max(PCB_Y - PH_SIDE_H - CONN_POCKET, CR_Y0), PCB_Y


def _top_tenon(tx):
    """ONE fused octagon tenon at station tx: cadkit's octagon (slides +X, roof +Z) rotated
    90° about Z so it slides +Y, mating plane at the housing TOP face (which is the chassis
    underside), roof rising +Z into the rib above and the root reaching TEN_ROOT down into
    the prism for a volumetric fuse."""
    return (_lever_joint(TEN_Y1 - TEN_Y0).tenon(root=TEN_ROOT)
            .rotate((0, 0, 0), (0, 0, 1), 90)                 # slide axis X -> Y (roof stays +Z)
            .translate((tx, TEN_Y0, HOUS_Z1)))                # station X, -Y start, mate at the top face


def rib_mortise(rib_x, y0=None, y1=None):
    """ONE octagon MORTISE (GLOBAL) for the rib at rib_x: the same cadkit octagon as the tenon
    but LONG in Y (MORT_Y0..MORT_Y1 = the knee-depth slide range), rotated to slide +Y. Opens at
    the rib bottom (-Z, the mating plane = Z_BOT) and its roof bridges inside the rib. chassis.py
    cuts this into every rib so a lever can mount in ANY bay."""
    # WORLD y range: the caller's, or this station's own by the grid's rule. chassis.py is the
    # one that knows about legs and the light window, so for the end stations it passes the two
    # SHORT segments (one over each foot) rather than one run across the instrument.
    _y0 = (MORT_Y0 if y0 is None else y0 - MOUNT_Y)
    _y1 = ((D.mortise_y_end(rib_x) if y1 is None else y1) - MOUNT_Y)
    m = (_lever_joint(_y1 - _y0).mortise(drop=2.0)
         .rotate((0, 0, 0), (0, 0, 1), 90)                     # slide axis X -> Y
         .translate((0.0, _y0, HOUS_Z1)))                     # centred x=0, -Y mouth, mate at rib bottom
    #        ^ HOUS_Z1, not BODY_Z. The TENON mates at the housing top (_top_tenon),
    #          and with a bigger bearing the top is set by the seat, not by BODY_Z.
    #          Keyed to BODY_Z the mortise sat 0.7 low and every tenon on all six
    #          stations dug into its rib — which is exactly what the gate reported.
    return m.translate((rib_x, MOUNT_Y, MOUNT_Z))


# (retention now PRESSES the rib ledge -- no drilled pilot in the rib, so no per-bay chassis feature)


# Feel-block placement. The cartridge / pocket / clamp / stop are all BUILT in the historical +Z/+X frame
# (HS_Z ≈ +6.5, coil extends +X). feel_place() maps any such solid to its AS-INSTALLED spot -- BELOW the
# axle at the -Z lobe, pointing -X: mirror across X=0 (coil -> -X; the follower meets the arm-face lobe's
# -X extremum), shift X to that lobe, then drop to z = AXLE_Z - LOBE_RC. Mirror-X keeps the /\ apex DOWN
# and the roof on TOP, so print orientation is intact. Everything is anchored to AXLE_Z, so raising the
# axle later slides the whole feel block up with it.
_FEEL_DX = 0.0                                     # mirrored follower already lands at -LOBE_X0 = the
                                                  #   centred lobe's -X extremum (-1.5); no X shift needed
_FEEL_DZ = (AXLE_Z - LOBE_RC) - HS_Z               # build-frame HS_Z -> the -Z lobe (tracks AXLE_Z)


def feel_place(s):
    return s.mirror("YZ").translate((_FEEL_DX, 0, _FEEL_DZ))


def feel_place_pt(p):                               # same map for a bare point (e.g. the clamp axis origin)
    return (-p[0] + _FEEL_DX, p[1], p[2] + _FEEL_DZ)


def feel_unplace(s):                                # inverse of feel_place: placed-frame solid -> build frame
    return s.translate((-_FEEL_DX, 0, -_FEEL_DZ)).mirror("YZ")


# ── HOUSING = ONE PARAMETRIC PRISM (user round: draw the lever, then the
# cartridges incl. their back-stops, then DERIVE the housing box from their
# extents — each face computed from the previous stage, no hand numbers):
#   +X  the LEVER's +X extent (hub/arm half-depth; the knee face is exposed)
#   -X  the CARTRIDGE back + the position range + the rear wall (HS_REAR_T)
#   ±Y  the outermost cartridge face + slide clearance + one housing wall
#   +Z  the instrument BODY underside, FLUSH (user round 4: the slab
#       beside the lever fills the whole lever-top→body zone — 2.4 of
#       MATERIAL, no air gap; was 2.1 + 0.3 air)
#   -Z  the cartridge bottom (piston underside) + slide clearance + one wall
# Globals (MOUNT_POSE + these): x -578.26..-496.00, y -162.65..-134.85,
# z -97.35..-75.15 (top now flush with the chassis underside Z_BOT).
HOUS_X1 = max(ARM_TX / 2, BRG_SEAT_D / 2 + BRG_WALL_X)   # +11.25 (was +5.0, then 8.1: the Ø13
#           race needs 6.5 of radius plus its wall, where the arm wanted 5.0)
HOUS_X0 = -(HS_POCKET_BX + HS_REAR_T)                    # was -78.1 with the Ø6 coil
HOUS_HW = max(abs(HS_YC) + HS_CART_WY / 2 + HS_CLR + HS_HOUS_WALL,
              LEVER_HW + HS_CLR + BRG_W)                 # 17.45 — the cartridge pocket wall
#           sets it now (17.45 vs the seats' 17.4). There is NO outboard skin beyond the
#           bearings any more (user, 2026-09-21): the seats already ran out through the
#           face, so the old 1.0 "skin" was only an empty recess over each bearing.
HOUS_Z1 = HOUS_TOP_Z                                     # +12.0, the seat roof (was 9.6; flush: BODY_Z
#           = HUB_TOP + 2.4 — the designed 2.4 stands between lever and body)
# PRINT ORIENTATION (the record, declared once per part) -- the housing goes on the bed
# on its FLOOR and builds +Z, in world coordinates. It is written here rather than
# transcribed into a checker because it is a design fact: every 45 in this module is
# drawn self-supporting AGAINST THIS, the keeper's foot is sized "on the bed" at
# HOUS_Z0, and the buttress "grows up from the print bed". A part that is ever
# re-oriented brings this declaration along with it, and tools.check_ceilings reads it
# by name (src.leg_stack's SLEEVE_UP and friends set the pattern).
PRINT_UP = (0.0, 0.0, 1.0)
# ...and the rest of the family, which do NOT share it:
#
# THE ARM lies on its -Y face and builds +Y, and that was already written down in
# machine-readable form -- cut_axle_bore hands it to cadkit as print_up, and cadkit returns
# a plain cylinder instead of a teardrop precisely because the bore runs ALONG it. Naming
# it turns that argument into the declaration, so the arm, the vertical lever's arm and the
# foot pedal's arm all read ONE fact through their own poses.
LEVER_UP = (0.0, 1.0, 0.0)
# THE CARTRIDGE BASE builds +Z with the housing it sits in, which is what its peaked roof
# is drawn for ("so the housing pocket cut from it is self-supporting (no flat overhang) in
# the -Z->+Z print"). It too was already being passed to cadkit as a print_up.
CART_UP = (0.0, 0.0, 1.0)
# THE AXLE builds -Y: it prints standing, POCKET-DOWN, and the blank is drawn along +Z then
# rotated +Z -> +Y, so the collar end faces +Y and the build runs away from it.
AXLE_UP = (0.0, -1.0, 0.0)
# THE MAGNET CAP the same way and for the same reason: APERTURE-DOWN, drawn along +Z and
# rotated onto the lever's +Y axis, so the flange face is the bed.
MAGNET_CAP_UP = (0.0, -1.0, 0.0)
# THE PISTON builds -X: it stands on its +X SPRING-SEAT face, the one flat 10 x 10 end,
# and everything after it -- body, follower tongue, rounded nose -- grows along the build
# rather than out of a side. Printed +Z with the cartridge it would lay its tongue out
# sideways as a flat cantilever over air. It had no declaration at all until the pilot
# came off: with a Ø4.6 boss on the bed face there was no good answer, which is the
# tell that the boss was the problem (user).
PISTON_UP = (-1.0, 0.0, 0.0)
#
# NOT DECLARED: the half-stop PISTON. Nothing in the module says which way it prints, it
# takes no print_up, and its follower nose is a half-cylinder in X-Z that would be a
# bottom overhang in the base's +Z -- so the base's direction cannot just be assumed for
# it. Left out deliberately: check_ceilings reports it as a gap, which is honest, where a
# guess would make its report meaningless.

HOUS_Z0 = min((HS_Z - HS_PISTON_WZ / 2) + _FEEL_DZ - HS_CLR - HS_HOUS_WALL,   # the cartridges
              (CHIP_DROP - PCB_WZ) - 4 * D.NOZZLE_D)                      # the board + its floor
#           ^ = HS_FLOOR_Z placed, or PCB_Z0 - CR_FLOOR_T (both defined below). The cartridges
#           bind (-16.5); the board would need -15.1.
BRG_Y0 = HOUS_HW - BRG_W            # bearing INNER faces at ±12.45: the bearings sit FLUSH
                                    # with the housing's outer faces (user, 2026-09-21: full
                                    # seat engagement right to the face, nothing recessed).
                                    # That leaves 0.45 to the ±12 hub ends.
assert BRG_Y0 >= LEVER_HW + HS_CLR - 1e-9, "the flush bearings would bite the lever hub"
# ── MOUNT TENON STATIONS (user: "4 sets"). The chassis rib comb is a uniform
# RIB_PITCH/2 = 23 mm and the lever is posed ON a rib (MOUNT_X = -501 IS a rib X), so
# the stations are just k·23 walking -X from the axle, kept while the whole 6-wide
# octagon still lands on the top face: 0, -23, -46, -69 — four, and the count falls
# out of the geometry rather than being written down (widen or shift the housing and
# the comb re-solves). Generated here rather than in the mount block because it is
# HOUS_X0/X1 that bound them, and those aren't known until this point.
_TEN_PITCH = D.LEVER_PITCH          # = the chassis bottom grid (8.8). Was RIB_PITCH/2 (22.35),
                                    # the old rib comb; the stations follow the comb by design, so
                                    # densifying the comb densifies these -- more tenons in the same
                                    # housing, which is a stronger joint as well as a finer one.
# ...and a station must ROOT ON SOLID. The bearing seats are teardrops whose print peak
# can break out through the top face over the axle (it always did a little; the Ø16
# 688ZZ opens it 1.78 either side of x = 0), and a tenon whose root sits in that
# opening floats free. So a station within that half-width + the tenon's own half-width
# of the axle is skipped (user: dropping the x = 0 stubs is fine).
_SEAT_RS = BRG_SEAT_D / 2                               # the seat bore's radius
_SEAT_OPEN_HW = max(0.0, _SEAT_RS * math.sqrt(2.0) - HOUS_Z1)   # peak's width at the top face
# THE -X-MOST TENON'S STEM IS FLUSH WITH THE HOUSING'S -X EDGE (user, 2026-09-18), and that
# is what the set is anchored on now -- not the axle. WHY: the player picks which mortise the
# lever hangs in, and the housing used to reach 5.31 further -X than its last tenon, so the
# slot next to the body adapter could not be used: the tenon would fit, the housing behind it
# would not. Flush, nothing sticks out past the joint, and LKL reaches one slot further -X.
# The FLARE still overhangs that edge by (width - stem)/2, which is free: it is 45 deg, so it
# prints self-supporting off the stem, and it lives up inside the chassis mortise anyway.
# The stations stay a plain walk on the grid PITCH from there, so they still land in mortises;
# what moved is the phase, and MOUNT_X takes it back out so the render still sits on stations.
_J_STEM   = _JW / 2.0               # cadkit's octagon parity (stem = width/2 -- _octagon_profile)
TEN_X_END = HOUS_X0 + _J_STEM / 2.0     # the -X-most station: stem face ON the housing edge
TEN_X = tuple(TEN_X_END + k * _TEN_PITCH for k in range(40)
              if TEN_X_END + k * _TEN_PITCH <= HOUS_X1 - _JHW
              and (_SEAT_OPEN_HW <= 0.0
                   or abs(TEN_X_END + k * _TEN_PITCH) >= _SEAT_OPEN_HW + _JHW))
# THE POSE RE-SNAPS TO THE TENONS, not to the housing: the set has a phase now, so posing the
# axle on a station (as before) would leave every tenon half a stem off its mortise. Snap where
# the FIRST TENON lands and hand the phase back. MOUNT_POSE is rebuilt below so the two cannot
# disagree -- nothing between the nominal MOUNT_X and here reads either of them.
_TEN_PHASE = TEN_X[0]
MOUNT_X = D.rib_comb_x(-501.0 + _TEN_PHASE) - _TEN_PHASE
MOUNT_POSE = (MOUNT_X, MOUNT_Y, MOUNT_Z)
assert abs((min(TEN_X) - _J_STEM / 2.0) - HOUS_X0) < 1e-9, (
    "the -X-most tenon's stem sits %.2f from the housing edge, not flush"
    % (min(TEN_X) - _J_STEM / 2.0 - HOUS_X0))
# Each tenon runs the housing's FULL Y depth: it is a rail, and every millimetre of it
# is engagement the player can buy by sliding the lever inboard. The +X-most station
# (x=0) sits directly over the lever, where the lever-room slot opens the top face —
# so all that survives of it is a stub on top of each ±Y cheek wall. That is by
# construction, not by special-casing: the tenons are unioned BEFORE the lever-room
# cut, so the same sweep that clears the lever trims the tenon.
TEN_Y0, TEN_Y1 = -HOUS_HW, HOUS_HW
TEN_ROOT = D.MIN_WALL               # 0.8 root below the mating face — volumetric fuse into the
                                    # prism, never a coplanar touch (cadkit joinery rule)
# SENSOR-SIDE Y (re-anchored here — see the note up in the layout block): the
# magnet rides the integral +Y stub just past the HOUSING FACE, not past the
# long-deleted bearing wall. 0.5 running clearance to the static face.
# ── AXLE (user round 2: the previous integral-stub + glued-insert pair COULD
# NOT BE INSTALLED. The lever's +Y stub had to enter the +Y bearing, but the hub
# is boxed in by the cheeks with only 0.4 of axial travel, so the stub could
# never reach it — that pair only ever fitted in a render.) The axle is now ONE
# printed part fitted LAST: press both bearings, drop the lever in, then slide
# the axle +Y -> -Y through bearing / lever / bearing. Its magnet POCKET is
# threaded on the OD and a screw-on CAP traps the disc; the axle's flange seats
# on a cadkit CONTACT RIB on the housing's outer face, so the magnet's Y — and
# with it the sensor air gap — is set by a printed datum instead of by wherever
# the stack happens to come to rest.
# AXIAL DATUM = the +Y bearing's INNER RACE (user, 2026-09-21: bearings flush with the face).
# The printed contact rib that used to sit on the housing face is gone -- with the bearing flush
# it would have stood on the bearing, not on plastic. A Ø9.6 LAND on the axle flange seats on the
# inner race instead: that is the 688's shaft-abutment band (inner-ring shoulder ~Ø10, shield bore
# larger), so it touches only the ring that turns WITH the axle -- no rubbing datum at all -- and
# the Ø12.8 flange behind it stands AXLE_LAND_T clear of the shield. The air gap is unaffected:
# PCB_Y = MAG_Y1 + AIR_GAP + CHIP_H tracks the magnet, so the whole stack moves together.
AXLE_LAND_D = 12 * D.BEAD           # 9.6 inner-race land
# J1 stands PH_SIDE_H (5.5, JST's ePH drawing) off the magnet face, and the magnet face sits a fixed stack
# (land + pocket floor + magnet + air gap + chip) off the housing's +Y face -- 6.4 with a
# one-bead land. So the LAND grows until that stack clears J1 by CONN_GAP: the magnet, and
# with it the board, stands 0.9 further out instead of J1 cutting the housing wall (user:
# the old relief took 0.85 out of the 1.6 beside the half-stop pocket).
MAG_FLANGE_T    = 0.8                           # pocket floor under the magnet
CONN_GAP = 0.3                      # J1 body -> housing face
AXLE_LAND_T = max(D.MIN_WALL,
                  PH_SIDE_H + CONN_GAP - (MAG_FLANGE_T + MAG_T + AIR_GAP + CHIP_H))   # 0.8: the PH
                  # fits the 6.4 stack as it is (the XH's 7.0 needed 1.7 -- a 0.9 stand-off)
AXLE_SHOULDER_Y = HOUS_HW + AXLE_LAND_T         # flange face
AXLE_FLANGE_D   = 16 * D.BEAD       # 12.8 flange Ø (what seats on the rib; was 9.6 over the Ø5 journal —
                                    # the rib's mean Ø is this - 1.5 and its inner edge has to stay outside
                                    # the Ø9 axle way). NOT the thread
                                    # major any more — the hex cap forced those apart
MAG_Y0  = AXLE_SHOULDER_Y + MAG_FLANGE_T        # 15.55: magnet seat
MAG_Y1  = MAG_Y0 + MAG_T                        # 18.05: magnet face -> the air gap
MAG_POCKET_D  = MAG_D + 0.2                     # 6.2 slip fit for the Ø6 disc
MAG_COLLAR_H  = MAG_T - 0.1         # 2.4: the collar stops 0.1 SHORT of the disc so the
                                    # cap always lands on the MAGNET — bottoming on the
                                    # collar instead would leave the disc free to rattle
MAG_TH_PITCH  = 2.0                 # cap thread, cadkit 45° self-supporting profile
MAG_TH_DEPTH  = 0.3                 # (shallow + fine: the collar is only 2.4 long, and at
                                    # this pitch a deeper flank trips cadkit's valley-
                                    # overlap check)
MAG_TH_MAJOR  = 8.0                 # SIZED BY THE DRIVER rather than by strength. A 3/8"
                                    # socket is 9.525 across flats and the Ø6.2 magnet
                                    # pocket has to live inside it, so the entire radial
                                    # budget between them is ~1.66 — split between collar
                                    # wall, thread and cap wall. Major 8.0 divides it
                                    # 0.60 / 0.675: thin, but sound for a hand-tight
                                    # retainer holding a 0.5 g disc. (Keeping the old 9.0
                                    # would have left a 0.175 cap wall — unprintable, and
                                    # the reason this Ø split off from the flange's.)
MAG_TH_MINOR  = MAG_TH_MAJOR - 2 * MAG_TH_DEPTH
MAG_TH_CLR    = 0.4                 # male shrunk (same rule as the backstop)
CAP_T  = 0.8                                    # cap's clamping flange
CAP_HEX_AF = 9.2                    # across flats, for a 3/8" (9.525) female hex driver.
                                    # 0.325 total clearance, deliberately generous: printed
                                    # external features come out slightly OVER size, and the
                                    # two failure modes are not symmetric — a hex a hair too
                                    # big will not enter the socket at all, while one a hair
                                    # too small merely rocks. Across corners 10.62, so the
                                    # hex still sits inside the cap's old Ø11 envelope and
                                    # nothing downstream has to move.
CAP_BASE_CLR = 0.3                  # the cap's rim stops SHORT of the axle flange so it
                                    # can only ever land on the MAGNET; bottoming on the
                                    # flange would leave the disc loose — the same trap the
                                    # collar height already dodges at the other end
CAP_APERTURE = 6 * D.BEAD           # 4.8 open on the axis so the cap never intrudes on the
                                    # field path or on any future gap reduction
# D-FLAT key. The user asked for a tongue; a PROTRUDING one is impossible here —
# it would have to pass through the Ø5 bearing bore on the way in — so the key
# lives INSIDE the Ø5 envelope as a flat.
# ITS EXTENT IS FORCED, and a probe caught the naive version: the flat must run
# from the axle's LEADING (-Y) TIP all the way past the hub. Anything round
# ahead of the flat has to pass through the lever's D-bore during insertion,
# where the bore's flat leaves material standing at AXLE_FLAT_R — so a round
# leading section simply cannot get through. Only a flat that starts at the tip
# leaves no round section ahead of it.
# The cost is that the -Y journal runs on a flatted shaft. That lands on the
# right side: the magnet is at the +Y end, whose journal stays fully ROUND, so
# the disc's concentricity is set by the good bearing. Worst case the -Y end can
# shift by the flat depth, and ONLY toward +Z — gravity and the knee's lateral
# load both bear on round metal — which tilts the magnet by ~0.1 mm against the
# ±0.5 mm misalignment the encoder allows. Depth 0.5 (not 0.7) keeps that margin
# comfortable while still leaving a 3.0-wide key face.
AXLE_FLAT_DEPTH = 0.5
AXLE_FLAT_R = AXLE_D / 2 - AXLE_FLAT_DEPTH      # 2.0 from the axis
AXLE_FLAT_Y = LEVER_HW + 0.1                    # flat's +Y end (hub ±10, bearings ±10.4)
AXLE_BORE_D = AXLE_D + 0.2                      # lever's through D-bore (slip fit — the
                                                # end screw below is what holds it)
# AXIAL RETENTION, NO GLUE (user: every part comes apart) — ONE M4 BUTTON HEAD IN THE AXLE'S
# -Y END, the same screw and the same 2.5 key as everything else on the instrument. The axle is
# slid +Y -> -Y through both bearings, so it can carry no integral shoulder at its leading end
# (nothing there may exceed the Ø8 bore) and its flange already stops it going any further -Y.
# What has to be stopped is the way it came: +Y. So once the tip is through the -Y bearing a
# screw goes into it on the axis with a Ø9 washer under the head. The washer is wider than the
# bore and narrower than the inner ring (the same shaft-abutment band the flange's land uses at
# the other end), so it laps the -Y INNER RACE and nothing else, and it turns with the axle —
# nothing rubs.
# THE TIP STANDS AXLE_END_PROUD OF THE RACE, so the screw tightens against the AXLE'S OWN END and
# clamps nothing between the two bearings: the washer hangs that far off the race as running
# clearance. Tightened onto the race instead it would preload both bearings against each other
# through the housing, and how hard would depend on the hand holding the key.
# IT FORMS ITS OWN THREAD in the printed axle. An insert is Ø6 in a Ø8 shaft — a 1.0 wall — and
# the load is the axle's own gram or two: the screw stops a slide, it never carries the pivot
# (that is the journal in the bearing, which the steel core only stiffens). The axle prints
# standing, so the bore runs up the build and the wall round it is whole perimeters.
AXLE_END_PROUD = 0.2
AXLE_SCREW_L = M4_SCREW_L                       # M4 x 10 button — the cartridges' SKU
AXLE_WASHER_OD, AXLE_WASHER_ID, AXLE_WASHER_T = 9.0, 4.3, 0.8      # ISO 7089 M4
AXLE_TAP_L = AXLE_SCREW_L - AXLE_WASHER_T + 2 * D.BEAD            # 10.8: the screw's reach + a
                                                # chip well below its end
assert AXLE_D < AXLE_WASHER_OD <= AXLE_LAND_D, (
    f"the Ø{AXLE_WASHER_OD} retention washer must lap the inner race (bore Ø{AXLE_D}) and stay "
    f"inside its abutment band (Ø{AXLE_LAND_D}) — outside it rubs the shield")
assert AXLE_FLAT_R - M4.selftap_d / 2 >= D.MIN_WALL - 1e-9, (
    f"the axle's wall between the end screw's bore and the D-flat is "
    f"{AXLE_FLAT_R - M4.selftap_d / 2:.2f}, under one bead")
PCB_Y   = MAG_Y1 + AIR_GAP + CHIP_H             # board face = magnet + gap + PACKAGE
AXLE_Y0, AXLE_Y1 = -HOUS_HW - AXLE_END_PROUD, MAG_Y1   # axle: the -Y journal runs the full
                                                # bearing width (user, 2026-09-21) and its tip
                                                # stands AXLE_END_PROUD past the race for the
                                                # end screw to seat on .. the magnet face at
                                                # the +Y end

# ── SENSOR-BOARD CRADLE (user: "build material in the housing to hold the PCB").
# Fused to the housing's +Y face, printed with it (-Z→+Z), and every feature stands
# UP off the bed: two side WEBS (vertical plates), a front PLINTH and a floor.
# There is not a single ceiling in it, so no supports.
#
# RETENTION / INSTALL — retained on five faces by shape, and the sixth is the
# INSTRUMENT (user). There is NO retaining screw:
#     ±X   the grooves' side walls          ±Y  the grooves' front/back flanks
#     -Z   the floor the board's edge rests on   plus the plinth's seat face
#     +Z   the install axis — the board is lowered into the two grooves from above
#          and slides down to the floor. It is put in with the lever OFF the guitar;
#          when the lever then slides into the ribs, the CHASSIS UNDERSIDE closes
#          over it CEIL_CLR away and the board can no longer come out.
# So: axle in, cap on, board down the grooves, lever onto the instrument — and it is
# captive, with no fastener anywhere in the sensor stack. Service reverses it, and
# the order is forced rather than remembered: you cannot reach the board without
# first sliding the lever out, and you cannot reach the cap without first lifting
# the board. Because the board still RESTS on the floor, the ceiling is a lift stop
# and not a datum — the chip's position is set by the cradle either way.
#
# THE DRIVER BORE shapes the printed part. kl_magnet_cap has to be socketed at
# assembly, AFTER the cradle exists (it is printed into the housing) and BEFORE the
# board goes in, so a clear cylinder of SOCK_D about the axle axis is reserved and
# every PRINTED feature is checked against it — that is why the plinth stops at -7.0
# and why the board's edges cannot come inside 8.70. It does NOT bind the board or
# its connector: those arrive after the cap and leave before it, so they are as free
# to block the bore as the board obviously already does.
SOCK_D  = 14.0                      # reserved driver bore about the axis (a 3/8" socket /
                                    # nut driver runs ~12.5-13.5 OD; 14 gives it room)
SOCK_R  = SOCK_D / 2
CR_CLR   = 0.15                     # board slip fit, per face. The board's -Y face is the
                                    # AIR GAP's datum, so it is the M4 that sets it: doing
                                    # the screw up pulls the board onto the seat faces at
                                    # PCB_Y and the 0.3 of slot slop all lands behind.
CR_ENG   = 1.85                     # how deep each board edge sits in its groove
CR_WEB_T = 4.0                      # web thickness in X, outboard of the groove
CR_BACK  = D.MIN_WALL_2P   # 1.6 (was 1.5)                      # web material BEHIND the groove (the +Y flank)
# The board is DELIBERATELY ASYMMETRIC about the chip. Both edges are pushed out by
# the socket cone (a groove wall may not come inside SOCK_R, so an edge may not come
# inside SOCK_R + CR_ENG - CR_CLR = 8.70), and the -X edge is pushed out FURTHER by
# the M4, which needs 1.4 of FR4 around its Ø4.4 hole. Since the chip's X is fixed at
# the axle axis and the outline is ours, paying for the screw on one side only is
# free — and it keeps the +X web from reaching much past the housing's knee face.
PCB_X1  =  4.025                                # +X edge: as close to the CHIP as the GROOVE
                                                # allows, which is not the same as as close as
                                                # the board house allows. It was 3.0, chosen
                                                # against JLCPCB's 1.0 component-to-edge rule
                                                # and the QFN's 1.5 body half-width -- and the
                                                # groove does not grip 1.0, it grips CR_ENG.
                                                # U4's courtyard reaches 2.175, so the groove's
                                                # inner face at 1.30 was 0.87 inside it and 0.35
                                                # inside the bare body: the sensor fouled the
                                                # housing on the way down the slot, 3.05 mm3 at
                                                # 11 mm up the stroke (user, 2026-09-29: "this
                                                # component on the PCB looks like it will clip
                                                # when trying to insert the board... we need a
                                                # little bit of extra blank PCB at the edge for
                                                # the retention piece to grip without touching
                                                # PCB components"). Now the outermost part plus
                                                # CR_ENG, asserted below against the real BOM.
                                                # This used to be 8.70, set by the driver bore:
                                                # a groove wall may not come inside SOCK_R. That
                                                # no longer binds because the +X groove carrier
                                                # is now confined BELOW the bore (see CR_X1_MAX
                                                # and _cradle) instead of running full height.
PCB_X0  = -29.0                                 # -X edge: the routed board's (chip 29.0 in).
                                                # History: was -14.0, CONNECTOR-limited. It is now
                                                # CIRCUIT-limited, and the board had to grow.
                                                #
                                                # The board was modelled as a sensor plus a
                                                # connector, and that board cannot work: it has to
                                                # speak CAN, so it needs an MCU, a transceiver and
                                                # a 3.3 V rail off the 24 V bus. (The BOM already
                                                # BOUGHT a transceiver for it — ~10 off — while
                                                # the layout spec placed neither that nor any
                                                # controller. See SENSOR_BOM for the real parts.)
                                                # Those come to ~173 mm2 against 253 mm2 of usable
                                                # 17x19 board: 69% covered, not routable
                                                # single-sided. At 28 wide it is 38%.
                                                #
                                                # ALL the growth goes -X because that is the only
                                                # free direction: the chip sits on the axle axis,
                                                # so +X is the face nearest the player (every mm
                                                # there is a mm of lever depth), and Z is nearly
                                                # frozen by the HORIZONTAL lever, whose window is
                                                # 21.4 for a 19 board. -X is deep in all three
                                                # housings.
                                                #
                                                # 29.0 is what the CIRCUIT needs, no more: the
                                                # terminator switch (the motor tee's, 8.89 over
                                                # its lands) lies between the transceiver and
                                                # the +X groove band, and everything -X of it
                                                # stands off by that much. The knee housings
                                                # run to HOUS_X0, far past it; the pedal turns
                                                # the board over into the bar, and its bay is
                                                # measured from the posed board
                                                # (foot_pedal.board_bay_cutter), so it follows.
PCB_WX  = PCB_X1 - PCB_X0                       # 33.025
CR_FLOOR_T = 4 * D.NOZZLE_D         # 3.2 (was 2.8 = 3.5 beads)                    # cradle floor under the board
CONN_EDGE  = 1.0                    # connector body -> board's bottom edge (JLCPCB's
                                    # component-to-edge rule; the TOP end stays flush)
# THE BOARD IS ONE DESIGN, FIXED (user: "the boards should be fully identical").
# It is not derived from the housing any more: the chip has to sit on the axle axis,
# the outline hangs off the chip, so the board's Z span is a property of the BOARD.
# What varies between levers is which way up it goes in.
PCB_Z1 = CHIP_DROP                              # +7.0
PCB_Z0 = PCB_Z1 - PCB_WZ                        # -12.0

# ── WHAT IS ACTUALLY ON THE SENSOR BOARD ─────────────────────────────────────
# Modelled the way the optical board is (user): every part that has to be there,
# at its real package size, so the outline is sized by hardware instead of by
# guesswork. Sizes are package BODY from the datasheet / LCSC; prices and stock
# were read from lcsc.com/product-detail/C<n>.html, never a search snippet (that
# is what put three wrong numbers in the BOM).
#
# The board runs CLASSIC CAN 2.0B (user). That decision is what makes it small:
# the MCU is $0.57 instead of $5.15, and the transceiver can be a 3.3 V part, so
# there is ONE rail and no 5 V stage. Bus B carries no motors, so it is free to
# run at 1 Mbps — 10 controls x 76-bit frames at 500 Hz is 38% loaded there,
# against 76% at the BOM's 500 kbps.
#
# ── EVERY POPULATED PART, READ OFF THE ROUTED BOARD ──────────────────────────────
# (ref, footprint, X, Z, HEIGHT off the board face, and the centre in the CHIP's frame --
# the chip is the axle axis, so that is the frame the housing cares about.)
#
# IT WAS A TYPED TABLE, and the two copies drifted. It said it was "generated from the
# laid-out board", and it had been, once: by 2026-09-30 it still carried the BUCK
# CONVERTER and its inductor that the 2026-09-21 re-spin deleted, four parts that had no
# placement at all, and five sitting up to 10.65 mm from where the router put them. The
# CAD built and rendered perfectly the whole time, because nothing compared them
# (tools/check_board_match now does, and that is how this was found).
#
# So it is read instead, from the same tracked export src/board_geom.py already uses for
# every other board -- elec/geom/lever_sensor.geom.json, written back OUT of the finished
# .kicad_pcb by elec/export_geom.py. Three things come from there and one does not:
#   the POSITION and the BODY are the router's, measured off F.Fab rather than off a
#     courtyard, which is the keep-out and not the part;
#   the HEIGHT is not in a KiCad board at all, so it stays in board_geom.HEIGHT, keyed by
#     FOOTPRINT rather than by ref -- a property of the part, not of this board.
_SENSOR_BOARD = "lever_sensor"
_BOM_SKIP = ("J1",)                 # cadkit models the real connector: sensor_connector


def _sensor_bom():
    fps = {f["ref"]: f for f in BG.load(_SENSOR_BOARD)["footprints"]}
    chip = fps["U4"]                # THE DATUM IS THE SENSOR, not the board's centre:
    out = []                        #   it is the axle axis, and it does not move when
    for ref, f in sorted(fps.items()):        # an edge does
        name = BG.fp_name(f["fpid"])
        h = BG.HEIGHT[name]         # KeyError here means a new package needs a height
        if ref in _BOM_SKIP or h <= 0.0 or f["fab"] is None:
            continue                # bare copper, or modelled properly elsewhere
        x0, x1, z0, z1 = f["fab"]
        out.append((ref, name, x1 - x0, z1 - z0, h,
                    round(f["x"] - chip["x"], 4), round(f["y"] - chip["y"], 4)))
    return tuple(out)


SENSOR_BOM = _sensor_bom()

# NOTHING MAY STAND IN A GROOVE. Each X edge of the board is gripped CR_ENG deep, and
# that band has to be bare copper -- not because of a fabrication rule (JLCPCB's
# component-to-edge is 1.0 and every part clears that) but because the groove is
# material and the part would have to pass through it on the way down the slot. The
# board's outline is a SPEC rather than an output, so this is the thing that keeps the
# spec honest when a part moves: it is how the sensor's own courtyard came to be 0.87
# inside the +X groove without anything noticing.
_BOM_X1 = max(x + lx / 2 for _, _, lx, _, _, x, _ in SENSOR_BOM)
_BOM_X0 = min(x - lx / 2 for _, _, lx, _, _, x, _ in SENSOR_BOM)
for _e, _p, _w in ((PCB_X1, _BOM_X1, "+X"), (PCB_X0, _BOM_X0, "-X")):
    assert abs(_e) - abs(_p) >= CR_ENG - 1e-9, (
        "a part reaches %.3f of the board's %s edge at %.3f -- the groove grips %.2f, so "
        "it would be driven through the part. Move the edge to %.3f."
        % (_p, _w, _e, CR_ENG, math.copysign(abs(_p) + CR_ENG, _e)))
CR_EDGE_KEEP = CR_ENG               # the groove takes this much of each X edge — mechanical
# The magnet cap's SWEEP, which is what forces the empty annulus around the chip
# (user asked whether that gap was intentional — it is, and this is the number).
# Measured off kl_magnet_cap: 5.312 true circumradius about the axle. The bare 5.4
# it used to carry left only 0.088, which is LESS THAN THE BOARD'S OWN SLIP in its
# grooves (CR_CLR = 0.15): a part sitting exactly on the old limit could be swept
# just by the board resting 0.09 toward the cap. Nothing does today — the nearest
# part is 7.00 out — but the guard was thinner than it looked, so it now carries
# the slip and a print allowance instead of pretending the board is located.
CAP_SWEEP_R  = 5.312 + CR_CLR + 0.2     # 5.66
CAP_CLR_H    = 1.5                  # board-to-cap gap: anything TALLER must clear the sweep


def sensor_hardware():
    """(name, solid) for every populated part, on the board's -Y (magnet) face.
    Single-sided by design — one assembly setup."""
    out = []
    for n, _fp, lx, wz, hy, cx, cz in SENSOR_BOM:
        out.append((n, box_at(lx, hy, wz, x=cx, y=PCB_Y - hy / 2, z=cz)))
    return out




def board_flip(z_bot, z_top, prefer=None):
    """Which way up the board goes in a housing spanning z_bot..z_top.

    `prefer` FORCES an orientation (the caller's design intent) and is checked for
    fit rather than trusted. Orientation is not purely a fit outcome: the FOOT PEDAL
    fits both ways up and chooses flipped so its CAN connector points DOWN into the
    pedal bar, where the wiring can be hidden (user). Fit still decides when the
    caller has no preference.

    There is no freedom in the board's Z once the chip is on the axle axis, so the
    only lever available is turning it over — a rotation of 180° about the AXLE
    AXIS, which swaps top-for-bottom and left-for-right but leaves the chip on the
    axis and, crucially, leaves the populated face still looking at the magnet.
    (Mirroring would be a different physical board; rotating about any other axis
    turns the components away from the magnet.)

    On the horizontal lever the board goes in as drawn and its top edge lands on
    the ceiling. On the vertical one the axle sits 19 lower, so as-drawn the board
    would hang 4.2 through the housing floor; turned over it clears by 0.8 and
    leaves 14.2 to the ceiling, which is what pcb_shim fills.

    Raises if neither way up fits — better than silently drawing a board that
    hangs out of its own housing."""
    ceil = z_top - CEIL_CLR
    as_drawn = PCB_Z0 >= z_bot and PCB_Z1 <= ceil
    flipped = -PCB_Z1 >= z_bot and -PCB_Z0 <= ceil
    if prefer is not None:
        if not (flipped if prefer else as_drawn):
            raise ValueError(
                f"a housing spanning {z_bot:.2f}..{z_top:.2f} cannot take the board "
                f"{'flipped' if prefer else 'as drawn'}, which is what it asked for")
        return prefer
    if as_drawn:
        return False
    if flipped:
        return True
    raise ValueError(
        f"the {PCB_WZ:.1f} board fits a housing spanning {z_bot:.2f}..{z_top:.2f} "
        "neither way up — move the housing's floor or its ceiling, not the board")


def _turned(z_bot, z_top, flip=None, right=False):
    """(turned in Z, turned in X): how the board sits in a housing AS THAT HOUSING IS
    DRAWN HERE.

    A RIGHT-HAND housing (`right`) is built in this frame and then mirrored in X
    (_housing), and the board that goes into it is the same board turned over about the
    axle -- a rotation, so it is still the one design. Turning over reverses the board's
    X and Z; the housing's mirror reverses X again. So in this frame, before the mirror,
    the cradle a right-hand housing needs is the one for a board with ONLY ITS Z
    reversed. Nothing is ever built that way round: the board itself is posed by
    _install(flip=True) at the station, with no mirror."""
    t = board_flip(z_bot, z_top, True if right else flip)
    return t, (t and not right)


def board_z(z_bot, z_top, flip=None, right=False):
    """(bottom, top) of the board as INSTALLED in this housing."""
    return (-PCB_Z1, -PCB_Z0) if _turned(z_bot, z_top, flip, right)[0] else (PCB_Z0, PCB_Z1)


def board_x(z_bot, z_top, flip=None, right=False):
    """(-X, +X) edges as INSTALLED -- turning the board over swaps them too."""
    return (-PCB_X1, -PCB_X0) if _turned(z_bot, z_top, flip, right)[1] else (PCB_X0, PCB_X1)


def conn_z(z_bot, z_top, flip=None, right=False):
    """J1's centre height as installed (the flip turns it over)."""
    return -CONN_ZC if _turned(z_bot, z_top, flip, right)[0] else CONN_ZC


def conn_mouth_x(z_bot, z_top, flip=None, right=False):
    return -CONN_MOUTH_X if _turned(z_bot, z_top, flip, right)[1] else CONN_MOUTH_X


PCB_TOP = PCB_Z1
def _cr_faces(edge):
    """(web inner, groove wall, web outer) X for a board edge — the groove is the
    gap between the inner face and the wall, and the board's edge lives in it."""
    s = 1.0 if edge > 0 else -1.0
    return (edge - s * (CR_ENG - CR_CLR), edge + s * CR_CLR,
            edge + s * (CR_CLR + CR_WEB_T))
CR_Y0    = HOUS_HW                              # 13.9: root, on the housing's +Y face
CR_SLOT_Y0 = PCB_Y                              # 20.35: seat plane = board -Y face
CR_SLOT_Y1 = PCB_Y + PCB_T + 2 * CR_CLR         # 22.25: groove back flank
CR_Y1    = CR_SLOT_Y1 + CR_BACK                 # 23.75: cradle +Y face
CR_X1_MAX = HOUS_X1                 # NOTHING in the cradle may stand +X of the housing prism's
                                    # own +X face (user). That is what caps the +X web: it
                                    # would otherwise want to reach 7.15, and the part's whole
                                    # +X extent was 13.15. The retention lost there is bought
                                    # back on -X, where the web runs full height and the board
                                    # is 14 deep — see _cradle.
CR_Z1    = HOUS_Z1                              # web tops FLUSH with the housing top, i.e.
                                                # with the chassis underside: the grooves have
                                                # to guide the board as high as it goes, and
                                                # flush is exactly what already slides under
                                                # the ribs everywhere else on this part
# ── CAN DROP CONNECTOR: JST B4B-XH-A (the project standard — see BOM Connectors;
# the SERVO42D's own I/O is XH2.54 native, so the whole harness is one system).
# FOUR circuits because that is what CAN costs us: black GND / red 24 V / yellow H
# / green L. One connector, not two — the bus is daisy-chained by the TEE boards
# and every device hangs off its tee by one short drop.
# ── J1, the lever-bus connector (re-spin spec) ────────────────────────────────────────────
# S8B-PH-SM4-TB, SMT side entry, on the MAGNET face: the board stays SINGLE-SIDED like every
# other board on the shared panel (user, 2026-09-21 -- a back-face J1 was withdrawn for that).
# PH, not XH (user, same day): the lever bus runs at 5 V, and a different family means no
# harness can put the motor tees' 24 V on a lever board. It stands on end at the -X edge,
# mouth -X; its plug runs -X in the gap between the board and the housing, through a tunnel in
# the -X web. That gap is PH_SIDE_H + CONN_GAP (AXLE_LAND_T buys it), so the tunnel never
# reaches the housing's cheek. SMT: no post tails at all.
CONN_N       = 8
CONN_PART    = "S8B-PH-SM4-TB"                        # LCSC C265121
CONN_L       = ph_side_length(CONN_N)                 # 19.9, vertical (JST B)
CONN_MOUTH_X = PCB_X0 + 3.05                          # the PH-era layout's mouth: its courtyard
                                                      #   (10.29 deep) sits clear of the groove band
CONN_ZC      = (PCB_Z0 + PCB_Z1) / 2                  # centred on the board's height
CONN_POCKET  = 0.3                  # clearance around it in the web tunnel
CONN_PLUG_RUN = PH_PLUG_RUN         # 3.6: mated PHR reach past the mouth (JST's drawing)
CONN_UNPLUG = 2 * CONN_PLUG_RUN + 4 * D.BEAD   # the plug's full WITHDRAWAL. _cradle
                                    # tunnels the web this far so the plug can be drawn off
                                    # without lifting the board out, and the lace loop has to
                                    # start past it (it used to be a 3.0 literal in _cradle,
                                    # which is also what put the loop off the bead grid).
assert PCB_Z0 + CONN_EDGE <= CONN_ZC - CONN_L / 2 and CONN_ZC + CONN_L / 2 <= PCB_Z1 - CONN_EDGE, (
    "J1 standing on end does not fit the board's height with the 1.0 edge rule")
assert PCB_Y - PH_SIDE_H - CONN_POCKET >= HOUS_HW - 1e-6, (
    "J1's tunnel would cut the housing's +Y cheek -- the magnet stand-off is too small")
CR_PLINTH_Z1 = -SOCK_R              # -7.0: front plinth top = the driver bore's floor
# (the swept-arm relief _cam_swept — a union of rotated hub/arm copies — is
#  PULLED for now (user: no curved geometry around the axle; keep it simple,
#  build back up later). The lever room is all planar cuts in _housing.)

# ── SENSOR_BOM validation (here, not at the table: it needs the connector) ──
# The MT6701's reference on the laid-out board. It was the literal "chip" while
# SENSOR_BOM was hand-written; now the table is generated from the PCB and carries
# real designators, so the two exemptions below key off this instead.
_SENSOR_REF = "U4"
def _conn_keepout():
    """(x0, x1, z0, z1) J1 forbids on the magnet face: its body AND the mated plug's run.
    Parts of the pre-route SENSOR_BOM layout that land in it are a handoff item
    (CONN_PAD_CONFLICTS), not an error here: that table predates the routed board."""
    return (CONN_MOUTH_X - CONN_PLUG_RUN, CONN_MOUTH_X + PH_SIDE_D + PH_TAB_D,   # + the solder tabs
            CONN_ZC - CONN_L / 2, CONN_ZC + CONN_L / 2)


CONN_PAD_CONFLICTS = []
# ...AND THESE ARE ASSERTS NOW, not a list of handoff items. They were lenient because the
# table was the PRE-ROUTE layout against a spec outline it had never been laid out to, so
# a part off the edge was a note to whoever re-spun the board. The table is the ROUTED
# board now (see _sensor_bom), so a part off the outline or in a groove band is not a
# handoff item -- it is a part the housing would be driven through, on the board as it
# would actually be ordered.
for _n, _lcsc, _lx, _wz, _hy, _cx, _cz in SENSOR_BOM:
    _x0, _x1 = _cx - _lx / 2, _cx + _lx / 2
    _z0, _z1 = _cz - _wz / 2, _cz + _wz / 2
    assert PCB_Z0 <= _z0 and _z1 <= PCB_Z1, (
        "%s spans z %.3f..%.3f, off the board's %.3f..%.3f" % (_n, _z0, _z1, PCB_Z0, PCB_Z1))
    assert _n == _SENSOR_REF or (PCB_X0 + CR_EDGE_KEEP <= _x0
                                 and _x1 <= PCB_X1 - CR_EDGE_KEEP), (
        "%s spans x %.3f..%.3f, inside the %.2f the grooves grip of %.3f..%.3f"
        % (_n, _x0, _x1, CR_EDGE_KEEP, PCB_X0, PCB_X1))
    if _hy > CAP_CLR_H:
        # the board is installed by dropping it PAST the rotating magnet cap, so a part
        # deeper than the gap must clear the cap's sweep — measured as the true distance
        # from the axle axis to the part's FOOTPRINT RECTANGLE, not to its centre
        _dx = max(_x0, -_x1, 0.0)
        _dz = max(_z0, -_z1, 0.0)
        assert math.hypot(_dx, _dz) > CAP_SWEEP_R, (
            f"{_n} is {_hy} tall and comes within {math.hypot(_dx, _dz):.2f} of the axle "
            f"— inside the cap's {CAP_SWEEP_R} sweep, so the board could not be installed")
    if _n != _SENSOR_REF:
        _kx0, _kx1, _kz0, _kz1 = _conn_keepout()
        if _x0 < _kx1 and _x1 > _kx0 and _z0 < _kz1 and _z1 > _kz0:
            CONN_PAD_CONFLICTS.append(_n)




def recess_swept(yc, lobe_rc, throw, zc, sense=1, rest_span=45.0, step=3.0):
    """The follower TONGUE's clearance swept through a lever's motion, in the LEVER frame -- the
    recess that lets the lobe reach its follower while the lever keeps its material right
    behind the lobe. Shared by every lever in the family (user, 2026-09-21: LKV had been left
    with plain rectangular notches sized to the CARTRIDGE, 14.8 wide on a 24 leg).

      yc        the follower lane's Y
      lobe_rc   axle -> lobe radius (the tongue retreats lobe_rc*sin(a) as the lobe rises)
      throw     working throw (deg), follower engaged
      zc        the follower's centre Z in the lever frame at rest
      sense     +1 if the working throw is +a about +Y (LKL), -1 if it is -a (LKV)
      rest_span how far the lever travels the OTHER way with the follower at rest (LKL: the
                storage fold; LKV: sag past rest until its deferred rest stop)
    """
    c = HS_CLR
    x_hi, x_lo = 0.0, -13.0                              # lobe centre .. back into open air
    tongue = box_at(x_hi - x_lo, LOBE_WY + 1.0, FOLL_H + 2 * c,
                    x=(x_hi + x_lo) / 2, y=yc, z=zc)
    def at(deg):
        s = lobe_rc * math.sin(math.radians(deg)) if deg > 0 else 0.0
        # the lever turns by sense*deg, so in the LEVER frame the tongue turns the other way
        return tongue.translate((-s, 0, 0)).rotate((0, 0, 0), (0, 1, 0), -sense * deg)
    degs = list(range(0, int(round(throw)) + 1, int(step))) + \
           [-d for d in range(int(step), int(rest_span) + 1, int(step))]
    if int(round(throw)) % int(step):
        degs.append(throw)                               # always include the full throw
    env = None
    for d in degs:
        env = at(d) if env is None else env.union(at(d))
    return heal(env)


def _recess_swept(yc, step=3.0, fold=45.0):
    """The follower TONGUE's clearance region swept through the lever's WHOLE motion, mapped into the ARM
    frame -> the arm recess for one follower band. Two motions feed it:
      * THROW 0..THROW  -- tongue ENGAGED (slid back by LOBE_RC*sin as it rides the rising lobe). At full
        throw the tongue is deepest & most -X in the arm frame; its underside sets the sloped -Z wall
        (~parallel to the piston at 30 deg -- the tightest -Z clearance).
      * FOLD 0..-fold   -- tongue at REST while the lever folds flat toward +X for storage. In the arm
        frame the rest tongue swings UP, and THAT (not the 0 deg rest) sets the +Z wall: a 0-deg-height wall
        would be clipped as the lever folds. Past ~fold the tongue has swung -X of the arm face into open
        air, so capping the sweep there loses no clearance.
    A clearance box bounding tongue+nose (FOLL_H + 2*HS_CLR tall, opening from the lobe back into open air)
    is swept and unioned; only its in-arm part removes material, so the recess hugs the motion -- far less
    removed than the old rectangular notch, leaving the arm solid right behind the lobe."""
    return recess_swept(yc, LOBE_RC, THROW, _FEEL_DZ + HS_Z + FOLL_DZ, sense=1,
                        rest_span=fold, step=step)


_RECESS_SWEPT = _recess_swept(MAIN_YC)               # one band, built once; translated in Y for the other


def _half_stop_piston() -> cq.Workplane:
    """The piston (printed): a square BODY (the Ø10 spring's footprint) that slides in the channel and
    seats the spring's FRONT on its +X face, a centre PILOT boss that noses +X into the spring's Ø5 bore
    to keep it aligned, and a
    SHORT follower TONGUE at the lobe band that protrudes -X, ending in a HALF-CYLINDER nose (round in
    X-Z, square across Y) for clean rolling cam contact. The body is wider than the front-lip window, so
    the preloaded spring can't eject it."""
    body = box_at(HS_BODY_BX - HS_BODY_X0, HS_PISTON_WY, HS_PISTON_WZ,
                  x=(HS_BODY_X0 + HS_BODY_BX) / 2, y=HS_YC, z=HS_Z)
    # follower: a tongue ending in a ROUNDED NOSE (half-cylinder, axis Y -> round in X-Z, flat across Y).
    # The round tip keeps a clean TANGENT contact on the arm through the whole throw -- it can't edge-load
    # the way a flat -X face would when the arm rotates. Behind the nose a box (height FOLL_H, offset up by
    # FOLL_DZ) spans the lobe's ~3.4mm Z-excursion so the tip stays on the lobe from rest to full throw.
    _nose_r = FOLL_H / 2                                                    # round nose radius = half the face
    foll = box_at(HS_BODY_X0 - (HS_NOSE_TIPX + _nose_r), HS_FOLLOW_WY, FOLL_H,
                  x=(HS_NOSE_TIPX + _nose_r + HS_BODY_X0) / 2, y=HS_YC, z=HS_Z + FOLL_DZ)
    foll = foll.union(cyl_y(2 * _nose_r, HS_FOLLOW_WY, y0=HS_YC - HS_FOLLOW_WY / 2)
                      .translate((HS_NOSE_TIPX + _nose_r, 0, HS_Z + FOLL_DZ)))    # rounded -X tip
    # NO SPRING PILOT. It was a Ø4.6 x 4.8 boss on the +X end nosing into the coil's ID to
    # centre it, and it made the piston unprintable (user, 2026-09-25: "we need to remove
    # this extra spring guide cylinder from the piston, it makes it unprintable"): the
    # piston prints ON that end face, so the boss is the FIRST layer -- a Ø4.6 disc with
    # the piston's whole 10 x 10 section landing on it one layer up. The coil is centred
    # by the channel it sits in, which is what the side lips are for.
    return heal(body.union(foll))


HS_FLOOR_Z = HS_Z - HS_PISTON_WZ / 2               # piston underside = cartridge OPEN-bottom = housing floor


ROOF_FLAT = D.NOZZLE_D              # gable roof cap: ONE bead. See _roof_gable.


def _roof_gable(yc, hw, z_base, x0, x1):
    r"""A triangular GABLE prism (roof): base yc±hw at z_base, apex at (yc, z_base+hw) with
    45deg faces, extruded along X from x0 to x1. Unioned on top of a flat-topped cartridge/
    pocket so the roof over the cartridge is a self-supporting /\ (each face 45deg) instead of
    a flat -Z->+Z print overhang. It sits ABOVE the cap top (z_base >= HS_CART_Z1), well clear
    of the piston (top HS_Z+HS_PISTON_WZ/2), so no running clearance changes -- it just replaces
    the flat lid with a peak. The two cartridges' peaks (at ±HS_YC) leave a solid ridge between
    them; below the eaves each pocket is the usual vertical-walled box."""
    # FLAT TOP, one nozzle wide (user), not a point. Same reason cadkit's octagon roof
    # is capped: a 45° apex is a peak the nozzle rounds off, so it cannot print as drawn —
    # it comes out a blob, and on the POCKET side that blob is what the cartridge has to
    # slide under. Truncating at one bead gives the housing a roof it can actually bridge
    # (this is the one intentionally-minimal segment, exactly like the octagon's cap) and
    # gives the cartridge a matching flat instead of a rounded ridge. Costs flat/2 = 0.4
    # of peak height on both halves, so the running clearance between them is unchanged.
    pk = z_base + hw - ROOF_FLAT / 2.0
    pts = [(yc - hw, z_base), (yc + hw, z_base),
           (yc + ROOF_FLAT / 2.0, pk), (yc - ROOF_FLAT / 2.0, pk)]
    wire = cq.Wire.makePolygon([cq.Vector(x0, y, z) for (y, z) in pts] + [cq.Vector(x0, *pts[0])])
    face = cq.Face.makeFromWires(wire)
    return cq.Workplane("XY").add(cq.Solid.extrudeLinear(face, cq.Vector(x1 - x0, 0, 0)))


def _half_stop_cart_base() -> cq.Workplane:
    """Cartridge (printed -- ONE part, NO separate roof): an INVERTED-U. A solid +Z CAP (toward the axle,
    where the swinging arm's arc is narrow) + two side walls + front/back walls, OPEN on -Z. The piston
    drops in; the HOUSING FLOOR below is the final -Z retaining wall. This keeps cartridge material -Z of
    the piston at an absolute minimum (only the housing is there, and it's relieved to open air at the
    front where the arm sweeps). The channel is cut UP from the open bottom to the cap underside."""
    ch_top = HS_Z + HS_CH_WZ / 2                                           # channel EAVES
    base = box_at(HS_BACK_X - HS_FRONT, HS_CART_WY, HS_CART_Z1 - HS_FLOOR_Z,
                  x=(HS_FRONT + HS_BACK_X) / 2, y=HS_YC, z=(HS_FLOOR_Z + HS_CART_Z1) / 2)
    # 45deg gable cap: a peaked roof so the housing pocket cut from it is self-supporting (no flat
    # overhang) in the -Z->+Z print. Unioned BEFORE the channel so the channel's own roof can rise
    # into it.
    base = base.union(_roof_gable(HS_YC, HS_CART_WY / 2, HS_CART_Z1, HS_FRONT, HS_BACK_X))
    # ONE channel, OPEN on -Z: cut from below the part up to the eaves, then a 45° GABLE ROOF over it
    # (a flat 10.8 ceiling would be a bridge). The piston head and spring ride it; the housing floor
    # closes it from -Z. It runs back to the back wall's front face, where the seat washer parks.
    base = base.cut(box_at(HS_WASH_BX - HS_BODY_X0, HS_CH_WY, ch_top - (HS_FLOOR_Z - 5),
                           x=(HS_BODY_X0 + HS_WASH_BX) / 2, y=HS_YC, z=(ch_top + (HS_FLOOR_Z - 5)) / 2))
    base = base.cut(_roof_gable(HS_YC, HS_CH_WY / 2, ch_top, HS_BODY_X0, HS_WASH_BX))
    # front tongue window (at the lobe band): passes the follower tongue; the front wall still catches the
    # Ø10 head in Y (window < head). The tongue rides up through it as the lobe rises over the throw
    base = base.cut(box_at(HS_BODY_X0 - HS_FRONT + 0.1, HS_WIN_WY, FOLL_H + 1.0,
                           x=(HS_FRONT + HS_BODY_X0) / 2, y=HS_YC, z=HS_Z + FOLL_DZ))
    # the two inserts, both mouths on the BACK face (adjusters never self-tap -- they hold load):
    #   TENSION (on the axis): Ø6×5 pocket + the one-bead web's Ø4.4 way to the seat washer.
    #   POSITION (HS_POS_DZ above): its Ø4.4 way runs on HS_POS_FWD past the wall, because the screw's
    #   end reaches that far -X into the channel roof when the head is down on the face.
    _up = CART_UP
    base = cut_insert_bore(M4, base, (HS_BACK_X, HS_YC, HS_Z), (-1, 0, 0),
                           clr_len=HS_BACKWALL - INSERT_L + 0.2, print_up=_up,
                           reason="tension screw: its end pushes the spring-seat washer")
    base = cut_insert_bore(M4, base, (HS_BACK_X, HS_YC, HS_Z + HS_POS_DZ), (-1, 0, 0),
                           clr_len=HS_BACKWALL - INSERT_L + HS_POS_FWD, print_up=_up,
                           reason="position screw: its head is the cartridge's X stop")
    return heal(base)


def hs_pocket_hw():
    return HS_CART_WY / 2 + HS_CLR                          # pocket half-width (slot + slide clearance)


def _hs_pocket(yc, x0, x1):
    r"""The housing pocket for one cartridge: a rectangular slot with a 45deg GABLE ceiling, CLR bigger
    than the cartridge all round. The FLOOR sits at the piston underside -- it is the -Z retaining wall
    for the open-bottomed cartridge. The ceiling is a peaked /\ (not flat) so the roof over it prints
    self-supporting -Z->+Z; the cartridge cap carries the matching gable. The cartridge slides in X and
    is jammed against the ceiling by the vertical clamp."""
    z0, z1 = HS_FLOOR_Z - HS_CLR, HS_CART_Z1 + HS_CLR
    box = box_at(x1 - x0, 2 * hs_pocket_hw(), z1 - z0, x=(x0 + x1) / 2, y=yc, z=(z0 + z1) / 2)
    return box.union(_roof_gable(yc, hs_pocket_hw(), z1, x0, x1))     # peaked ceiling


# (the M4 insert pocket/boss geometry -- _insert_pocket/_seated_insert/_insert_boss_cut/_insert_dummy --
#  now lives in freecad/fasteners.py and is aliased in at the top of this file.)


def _hs_block(yc, x0, x1):
    r"""The housing SHELL around one cartridge pocket: a rectangular block, HS_HOUS_WALL thick on ALL SIX
    faces of the pocket (floor, ceiling, sides). Cut _hs_pocket() from this to leave the shell -- a flat
    floor shelf under the cartridge (the -Z retaining wall for the open-bottomed cartridge; relieved to
    open air at the front where the arm sweeps) + side walls + ceiling. Floor == ceiling thickness (both
    HS_HOUS_WALL) -- symmetric, so the -Z floor is a clean 0.8-multiple like every other housing wall."""
    hw = hs_pocket_hw()
    t = HS_HOUS_WALL
    # z_top clears the pocket GABLE apex (peak = ceiling + hw) plus one wall, so the shell fully caps the
    # peaked ceiling; the flat top merges into the solid rail<->cartridge block above.
    z_bot, z_top = (HS_FLOOR_Z - HS_CLR) - t, (HS_CART_Z1 + HS_CLR) + hw + t
    return box_at(x1 - x0, 2 * (hw + t), z_top - z_bot, x=(x0 + x1) / 2, y=yc, z=(z_bot + z_top) / 2)


# ════════════════════════════════════════════════════════════════════════════
# SHARED BY THE WHOLE LEVER FAMILY — LKL here, LKV in knee_lever_vert, and the
# foot pedal in foot_pedal. All three are the same control core in different
# POSES, so the three blocks below were three near-identical copies. They are
# functions now, and one of them fixed a live bug on the way: LKL and the foot
# pedal had the axle's retention, LKV did not, so its axle had none at all. The
# no-glue sweep missed it precisely because the block was pasted rather than
# called. A copy that can drift, does.
# ════════════════════════════════════════════════════════════════════════════
def cut_axle_bore(body, hw=None):
    """The lever's axle interface: the D-BORE through the hub. The flat is the
    key; what holds the axle in axially is the screw in its own -Y end (see
    AXLE_END_PROUD), so the hub carries no fastener at all.

    cadkit picks the bore shape from print_up: a lever prints lying on its -Y
    face, so this bore runs ALONG the build direction and correctly comes back a
    PLAIN cylinder where the same call hands the housing a teardrop."""
    hw = LEVER_HW if hw is None else hw
    bore = printable_bore(AXLE_BORE_D, 2 * hw, (0.0, -hw, 0.0),
                          (0.0, 1.0, 0.0), LEVER_UP, overshoot=1.0)
    zhi, zlo = AXLE_FLAT_R + 0.1, -(AXLE_BORE_D / 2 + 1.0)
    return body.cut(bore.intersect(box_at(       # flatten the +Z side -> D
        AXLE_BORE_D + 2.0, 2 * hw + 4.0, zhi - zlo,
        x=0.0, y=0.0, z=(zhi + zlo) / 2)))


def cut_axle_stack(w):
    """The housing's whole Y stack: both BEARING SEATS, the CONTACT RIB on the
    outer face, and the axle way out through it. Identical in every pose, because
    nothing about the sensor stack depends on which way the lever swings.

    Two orderings in here are load-bearing and were both found the hard way:

      * the seats are TEARDROPS, not round bores. Printed -Z->+Z these run
        sideways, and a drooping ceiling takes the seat OUT OF ROUND — the one
        property a press fit needs. The load helps: the lever's weight presses
        the axle DOWN onto round metal, so the opened top carries nothing.
      * (the printed contact rib and its axle way are gone: the bearings sit
        FLUSH with the faces and the axle's land seats on the +Y inner race.)"""
    # The seats run OUT THROUGH THE OUTER FACE — the bearing is open to the air (user).
    # There used to be a thin skin behind each one, and it was never real: at 0.70 (now
    # 0.50) it is under one 0.8 bead, so the slicer puts NOTHING there. The bearing was
    # already located by its press fit alone and the skin only existed in the CAD.
    # Modelling it open is the honest version, and it also lets the bearing be pressed
    # from outside rather than through the lever room.
    # Each seat starts at the LEVER-ROOM wall, not at the bearing's inner face: the flush bearings
    # sit 0.05 outboard of that wall, and starting the seat at the bearing left a 0.05 sliver of
    # housing across the axle's path.
    _seat_out, _seat_in = HOUS_HW + 1.0, LEVER_HW + HS_CLR
    for sgn in (1.0, -1.0):
        y0 = sgn * _seat_in if sgn > 0 else -_seat_out
        w = w.cut(printable_bore(BRG_SEAT_D, _seat_out - _seat_in, (0.0, y0, 0.0),
                                 (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    # (no contact rib and no separate axle way: the seats run out through BOTH faces at the
    # full Ø16.1, and the axle's own land seats on the +Y bearing's inner race -- see AXLE_LAND_D)
    return w


def cut_feel_pockets(w, place, x_front=None):
    """Both cartridge HOUSE-POCKETS, mapped into the
    housing by `place` — which is the only thing that differs between poses
    (feel_place here, the vertical lever's lift, the pedal's lift).

    The house profile runs ALL THE WAY OUT the +X face (user: extend to the prism
    edge) — one clean channel from the front face to the cartridge back, with the
    rear (cut_feel_rear) behind it. `x_front` IS that face, and it
    is a parameter rather than this module's HOUS_X1 for a reason a snapshot
    caught: LKL's front is 5.0 but LKV's and the pedal's are 7.8, so hardcoding
    LKL's left both of their channels 2.8 short of their own faces — 36 and 246
    mm³ of material that should not have been there, and it does not read as a
    defect in any view."""
    x1 = HOUS_X1 if x_front is None else x_front
    for dy in (MAIN_YC - HS_YC, 0.0):
        w = w.cut(place(_hs_pocket(HS_YC + dy, -x1 - 1.0, HS_POCKET_BX)))
    return cut_feel_rear(w, place)


def cut_feel_rear(w, place, reach=0.0):
    """The housing REAR behind each pocket: the position head's recess (the washer
    sits at its bottom) + the key way behind it, and the tension head's way
    straight through (the head rides in here when backed out; the screw passes
    through it to be fitted or replaced).

    `reach` carries both holes further out past HS_REAR_T -- the foot pedal's
    housing is fused into a bar that stands behind it, and the key has to get
    through that too. Plain bores along X, teardropped for the -Z->+Z print, so
    they survive heal() (no threads here)."""
    up = (0.0, 0.0, 1.0)
    run = HS_REAR_T + reach + 1.0
    for dy in (MAIN_YC - HS_YC, 0.0):
        yc = HS_YC + dy
        zp = HS_Z + HS_POS_DZ
        w = w.cut(place(cq.Workplane("XY").add(printable_bore(
            HS_HEAD_WAY_D, run + 0.5, (HS_POCKET_BX - 0.5, yc, HS_Z), (1.0, 0.0, 0.0), up))))
        w = w.cut(place(cq.Workplane("XY").add(printable_bore(
            HS_WASH_RECESS_D, HS_POS_RECESS + 0.5, (HS_POCKET_BX - 0.5, yc, zp),
            (1.0, 0.0, 0.0), up))))
        w = w.cut(place(cq.Workplane("XY").add(printable_bore(
            HS_KEY_D, run, (HS_POCKET_BX, yc, zp), (1.0, 0.0, 0.0), up))))
    return w



# -- THE CABLE KEEPER: where a lever's bus-B slack is stowed ----------------
# User, 2026-09-22: "we need a way to cable manage having some extra wire length
# between each lever. That way you can adjust the lever positions without having to
# make new cables."
#
# A lever is NOT at a fixed station. Its tenons drop into the chassis bottom's mortise
# grid (D.LEVER_PITCH, 10.4) so it steps along X, and the rib mortise runs MORT_Y1 -
# MORT_Y0 = 197.5 in Y, so it also slides to any knee depth. The harness therefore has
# to reach a lever that has MOVED since the cable was cut -- and the loom is the
# crimped, tooled, contacts-ordered part, the one thing that should survive a
# re-placement. So a bus-B segment is cut long and the excess is coiled and pressed in
# HERE, on the lever itself, which travels with it.
#
# IT IS OPEN, AND THAT IS THE POINT (user, 2026-09-22: "the cable clip doesn't work
# because it traps the cable and it can't be removed"). This was a closed loop -- a bore
# through a block -- which a cable can only reach by being THREADED from one end, i.e.
# before its connectors are crimped on, and can never leave. A harness you cannot take
# out is not serviceable and is barely installable.
#
# The section is the chassis wiring trough's, shrunk (chassis.WT_*): floor, outer wall,
# and a NUB at the wall's top reaching back toward the cheek with a 45 deg underside, so
# the MOUTH IS NARROWER THAN THE POCKET. Cable presses in past the nub and stays; a
# screwdriver tip under the coil pops it back out. Borrowing that profile is also what
# makes it print: the mouth opens along +Z, the build direction, so the pocket has no
# ceiling, and the nub's underside is the 45 deg this whole part is drawn to.
#
# ON THE CONNECTOR CHEEK, FLUSH WITH THE BACK END (user, both). Not the back face --
# that is how the key reaches all four feel screws, and a coil parked across it covers
# them for the life of the instrument. The +Y cheek is where the wire already is, since
# J1's plug leaves the board -X in the gap between the board and this very face.
# THE BUS-B CABLE, sized here because the KEEPER is sized from it -- and re-exported by
# src.wiring, which draws the harness, rather than the other way round: wiring already
# imports this module for the keeper's wound radius, so the constants have to live on
# this side of that edge.
CANB_WIRE_OD = 1.3                  # one bus-B conductor, 26 AWG, insulated
CANB_BUNDLE_OD = 2.5                # the four of them together (BOM, Wire)
KEEP_POST_D = 7 * D.NOZZLE_D        # 5.6 the barrel the slack winds onto
KEEP_HEAD   = 3 * D.NOZZLE_D        # 2.4 of 45 deg flare at the top: the coil cannot
                                    # walk off, but it lifts over with a screwdriver
KEEP_WOUND_D = 2 * (KEEP_POST_D + CANB_BUNDLE_OD) / 2.0 + CANB_BUNDLE_OD   # 10.6 wound OD
# THE SUPPORT MATCHES THE POST, not the coil (user, 2026-09-23: "the supports could
# also be cleaner to match the diameter of the post and join more aesthetically /
# strongly"). It was as wide as the WOUND cable (10.6) -- a slab sticking out either side
# of a 5.6 column. At the post's own diameter it reads as part of the post, and a 45 deg
# COLLAR at the joint carries the load into it instead of ending on a square corner.
KEEP_WEB_T  = KEEP_POST_D           # 5.6 -- the support is the post's width
KEEP_BUT_T  = KEEP_POST_D           # 5.6 of buttress, measured SQUARE to its own 45
                                    # (user, 2026-09-23, measuring the 3.20 it was:
                                    # "set the diagonal thickness here to match the
                                    # diameter of the column"). The strut is now the
                                    # post's section in BOTH directions -- as wide as it
                                    # in X and as deep as it across the diagonal -- so
                                    # the member does not thin down where it turns.
                                    # A strut's thickness is perpendicular, not vertical:
                                    # the band is sqrt(2) taller than this in Z.
KEEP_POST_DX = KEEP_WOUND_D / 2.0   # ...but the post still sits a WOUND radius in from
                                    # the housing's back face, so the coil is flush with
                                    # it rather than standing proud
# HOW MUCH BARE POST THE COIL NEEDS -- which is a LAYER's worth, not the whole slack
# (user, 2026-09-23: "you can wrap wire around itself so the outer wraps have a larger
# diameter"). That is what a hand-wound hank does, and it takes the capacity question
# off the column entirely: turns-per-layer set the HEIGHT, layers set the CAPACITY, and
# layers cost nothing in Z. The post stopped needing to be tall or fat the moment this
# was pointed out -- see wiring._coil_layers.
KEEP_WEB_H  = KEEP_POST_D           # 5.6 of base on the bed, under the winding -- the
                                    # POST'S OWN SECTION again (user, 2026-09-23,
                                    # measuring the 4.80 it was: "ditto for the other
                                    # levers, make the floor support equal height and
                                    # width matching the column diameter"). It was
                                    # already KEEP_WEB_T wide; now it is square. This
                                    # sets KEEP_DROP, so every coil in the instrument
                                    # rises the same 0.8 and they stay level with each
                                    # other -- which is the property that matters.
# ...far enough that the WOUND CABLE clears the CRADLE, not merely the cheek. The cradle
# stands CR_Y1 off the axle and carries the board, and a coil tucked inside its shadow
# put every run that left it straight along its own lever's PCB. Derived, so it tracks
# the cradle rather than being a number that was once right.
KEEP_CLR_Y  = CR_Y1 - HOUS_HW + D.MIN_WALL_2P   # 11.5: the coil's inner face clears
                                    # the cradle's outer one. Was one wall (0.8), which left
                                    # the wound cable almost touching the lever and nowhere
                                    # for a finger or a screwdriver to get in (user: "move
                                    # the columns further from the lever so we have more
                                    # space to fit wiring") -- and, worse, put every run
                                    # that LEFT the coil straight along its own board.
                                    # one wall (0.8), which left the wound cable almost
                                    # touching the lever and nowhere for a finger or a
                                    # screwdriver to get in (user: "move the columns
                                    # further from the lever so we have more space to
                                    # fit wiring").
KEEP_COIL_R = (KEEP_POST_D + CANB_BUNDLE_OD) / 2.0       # wound centre line, 4.05
# THE POST STANDS ON THE BED AND GROWS TOWARD THE INSTRUMENT (user, 2026-09-23: "for
# the cable winding posts, they create a print overhang... align them along the Z axis
# instead of the Y axis", and "you can have the material for the cable winding start at
# the print bed and grow up towards the instrument").
#
# That is the whole fix, and it removes a part rather than adding one. Lying along Y the
# barrel was a horizontal cantilever off a vertical face, so it needed a 45 deg gusset
# under it -- and the gusset sat exactly where the coil's lower half had to pass, which
# cost 67 mm3 of lever inside every coil and then a second fix (carry only the inner
# half) to get out of. Along Z it is a plain pillar in the build direction: no overhang,
# no gusset, and nothing in the way of the winding.
#
# The WEB ties it back to the cheek, and stops below the winding for the same reason the
# gusset had to: anything beside the post at the coil's height is something the coil
# cannot get round. It is a vertical wall, so it prints like any other.
#
# THE WINDING IS AT THE TOP, right under the instrument (user, 2026-09-22: "so it
# doesn't dangle and hit your knee"). The post's MATERIAL starts at the bed; the CABLE
# lives at the far end of it.
# THE POST HANGS OFF THE HOUSING'S TOP, NOT OFF THE BED (user: "raise it so it matches
# the height of the other levers... the bottom support grows up from the lever body at a
# 45 angle"). Every lever's housing top is FLUSH with the chassis underside, so measuring
# down from HOUS_Z1 puts every coil in the instrument at the same height -- which is what
# the harness strung between them wants. Measured up from the bed, as it was, the post
# was as tall as its housing: the VERTICAL lever is 46.6 deep, so its column ran the
# whole of that and its coil sat 18 below the horizontal ones.
#
# And the support becomes a 45 deg BUTTRESS off the cheek rather than a slab on the bed:
# the same self-supporting angle the rest of the part is drawn to, carrying the post at
# its base, taking no build-plate area at all.
KEEP_WIND_Z1 = HOUS_Z1 - KEEP_HEAD - D.MIN_WALL_2P       # the head sits under the top
KEEP_WIND_Z0 = HOUS_Z0 + KEEP_WEB_H                      # ...and the base ends down here
KEEP_WIND_H = KEEP_WIND_Z1 - KEEP_WIND_Z0                # whatever is left is winding
# HOW FAR BELOW THE TOP THE WINDING STARTS -- set by the HORIZONTAL lever, whose post
# stands on the bed, and then imposed on the others. Every housing top is flush with the
# chassis underside, so a common drop puts every coil in the instrument at one height,
# which is what the harness strung between them wants.
KEEP_DROP = HOUS_Z1 - KEEP_WIND_Z0
# THE BUTTRESS IS FOR THE VERTICAL LEVER ONLY (user, 2026-09-23: "I was only suggesting
# adding the 45 to the LKV. The other levers were fine the way they were"). Right: a
# post standing on the bed is the simpler thing and the horizontal housing is only 28.5
# deep, so its column is short anyway. LKV is 46.6 deep -- there its post ran the whole
# depth of the lever and put its coil 18 below everyone else's. Hung at KEEP_DROP with a
# 45 deg buttress down to the cheek, it matches. The buttress drops the post's whole
# offset before it lands, which is the budget the assert in cable_keeper checks.
_KEEP_DY = KEEP_CLR_Y + KEEP_COIL_R + CANB_BUNDLE_OD / 2.0


def _yz(pts, xc, t):
    """A YZ profile, t thick and centred on x=xc -- the keeper's struts are all 2D."""
    return (cq.Workplane("YZ").polyline(pts).close()
            .extrude(t).translate((xc - t / 2.0, 0.0, 0.0)))


def cable_keeper(y_face=None, z_bed=None, x_back=None, z_top=None, hung=False):
    """The cable keeper on a lever housing's +Y (connector) cheek, in the lever's local
    frame: a post standing off the bed, webbed to the cheek below the winding, with a
    45 deg head at the top.

    Parameterised because the VERTICAL lever (knee_lever_vert) is the same design with
    the feel block moved above the axle -- same cheek and same back face, its own floor
    -- and it adjusts on the same grid, so it needs the same keeper."""
    y0 = HOUS_HW if y_face is None else y_face
    z0 = HOUS_Z0 if z_bed is None else z_bed
    x0 = HOUS_X0 if x_back is None else x_back
    z1 = HOUS_Z1 if z_top is None else z_top
    xc, yc, wz0 = keeper_point(z0, x0, y0, z1)   # ...THE one place the axis is written
    wz1 = z1 - KEEP_HEAD - D.MIN_WALL_2P                        # winding top
    ov = D.MIN_WALL_2P
    head = cq.Workplane("XY").add(cq.Solid.makeCone(
        KEEP_POST_D / 2.0, KEEP_POST_D / 2.0 + KEEP_HEAD, KEEP_HEAD,
        cq.Vector(xc, yc, wz1), cq.Vector(0, 0, 1)))
    # NO CONICAL COLLAR at the joint, though it is the obvious way to spread it. The
    # support is the post's own width now, so a cone of any flare stands proud of it on
    # both sides and leaves a flat crescent hanging underneath -- 26 mm2 of it, found by
    # probing for downward faces. The 45 deg wedge IS the blend.
    if not hung:                       # ...stands on the bed, on a base (the default)
        post = cyl(KEEP_POST_D, wz1 - z0, z=z0).translate((xc, yc, 0.0))
        foot = box_at(KEEP_WEB_T, yc - y0, KEEP_WEB_H,
                      x=xc, y=(y0 + yc) / 2.0, z=z0 + KEEP_WEB_H / 2.0)
        return post.union(head).union(foot)
    # ...or HANGS at the common height on a 45 deg buttress off the cheek. The post runs
    # BELOW the winding base into the buttress, and the buttress bites INTO the cheek: a
    # triangle that merely touches its supports along an edge fuses into nothing, and
    # the housing came out as three separate solids.
    # A STRUT, NOT A GUSSET: parallel faces, both at 45 (user, 2026-09-23, on a shape
    # whose top ran flat from the post across to the cheek: "still not right", crossing
    # out the triangle under that flat top). The filled corner is the obvious shape and
    # it was wrong twice before this, so name the three that failed:
    #   a right triangle with the corner DOWN -- a flat 10.6 x 16.8 underside hanging in
    #     air, 178 mm2, the face measured in the screenshot;
    #   a triangle tapering to the post -- fixed that, but sloped its TOP the opposite
    #     way, so it read as an arrowhead;
    #   a triangle with a HORIZONTAL top -- printable and strong, but it is a gusset
    #     filling the corner rather than a member carrying a load along itself.
    #
    # ONE 45 DEG BAND does all of it. Its TOP passes through the post's outboard edge at
    # the winding base, so the band never rises into the coil; its UNDERSIDE is that
    # plane dropped KEEP_BUT_T square, and THE POST IS CUT ON IT -- which is what makes
    # the junction a junction. A flat-bottomed post stacked on a brace hangs part of its
    # disc in air (8 mm2 one way, 17 the other, both found by probing for downward-facing
    # faces, both invisible to check_ceilings); a post cut on the band's own underside
    # has no bottom disc at all. Post and strut share one continuous 45 deg face.
    px = yc + KEEP_POST_D / 2.0                                 # the band's outboard end
    tv = KEEP_BUT_T * math.sqrt(2.0)                            # ...its VERTICAL depth
    def top(y):                                                 # the band's upper plane
        return wz0 - (px - y)
    # THE DEPTH IS THE WHOLE BUDGET, and the vertical lever spends nearly all of it: 45
    # deg buys one mm of drop per mm of offset, the post stands _KEEP_DY + a radius out,
    # and that is most of the 22.9 between this winding base and this floor. Hence no
    # bare shaft below the winding (there were 4.0) -- there is no room for any.
    a = y0 - ov
    assert top(a) - z0 >= D.MIN_WALL_2P, (
        "the keeper's 45 deg strut reaches the cheek %.2f above its floor, too thin "
        "to fuse" % (top(a) - z0))
    post = cyl(KEEP_POST_D, wz1 - z0, z=z0).translate((xc, yc, 0.0))
    # below the band, over its whole reach and well past the post either way
    cut = [(a - KEEP_POST_D, top(a - KEEP_POST_D) - tv), (px, wz0 - tv),
           (px, z0 - KEEP_POST_D), (a - KEEP_POST_D, z0 - KEEP_POST_D)]
    # the band, clipped at the floor: the far end lands ON THE BED the way every other
    # lever's keeper foot does, rather than tapering to a knife edge that will not fuse
    yu = px - (wz0 - tv - z0)                                   # where the underside lands
    but = [(px, wz0), (a, top(a)), (a, z0), (yu, z0), (px, wz0 - tv)]
    return (post.cut(_yz(cut, xc, KEEP_POST_D * 2.0))
            .union(_yz(but, xc, KEEP_WEB_T)).union(head))


def plug_pin(way, z_bot=None, z_top=None, flip=None):
    """Where ONE conductor leaves J1, by WAY NUMBER (1..CONN_N) -- the plug's cable end,
    on that contact's own line.

    THIS IS MEANT TO BE READ OFF THE MODEL (user, 2026-09-23: "can you make the wires
    enter the JST in accurate placement so we can use it as a reference when deciding
    which slot to put each wire into?"). So the way numbers here are the harness's, not
    a drawing convenience: harness.ph_trunk_pins() is the bus IN on ways 1-4 and OUT on
    5-8, each group in PH_PINOUT order (GND, +5 V, CAN_H, CAN_L). A lever's ARRIVING
    cable lands on 1-4 and its DEPARTING cable leaves from 5-8, which is what makes the
    board pass the trunk through itself.

    WAY 1 IS AT THE +Z END of the connector on a board installed as drawn, and at the -Z
    end on one turned over (the pedal's): that is where the ROUTED board has pad 1
    (elec/geom/lever_sensor.geom.json: J1 at rot -90, pad 1 at geom +y, and geom +y is
    this frame's +Z -- the frame SENSOR_BOM places every other part in). The turn-over
    is a rotation about the axle, so it carries the row end for end with the board.
    """
    turned = z_bot is not None and board_flip(z_bot, z_top, flip)
    zc = -CONN_ZC if turned else CONN_ZC
    mx = -CONN_MOUTH_X if turned else CONN_MOUTH_X
    sx = -1.0 if mx <= 0 else 1.0
    up = -1.0 if turned else 1.0                       # way 1's end of the row
    return (mx + sx * CONN_PLUG_RUN, PCB_Y - PH_SIDE_H / 2.0,
            zc + up * ((CONN_N - 1) / 2.0 - (way - 1)) * PH_PITCH)


def plug_point(z_bot=None, z_top=None, flip=None):
    """The plug's cable end on the connector's axis -- the middle of the pin row."""
    return plug_pin((CONN_N + 1) / 2.0, z_bot, z_top, flip)


def pin_axis():
    """The direction the pin row runs, in the lever's LOCAL frame, on a board installed
    as drawn: J1 stands on end and its ways count DOWN, way 1 at the top (plug_pin)."""
    return (0.0, 0.0, -1.0)


def cheek_axis():
    """The connector cheek's outward normal, in the lever's LOCAL frame."""
    return (0.0, 1.0, 0.0)


def cheek_bypass():
    """How far off the cheek a cable has to be to pass the lever LENGTHWAYS: outboard of
    the cradle, which stands further out than the cheek does and carries the board."""
    return CR_Y1 - HOUS_HW + CANB_BUNDLE_OD


def plug_standoff(x_back=None):
    """How far along the plug's own axis a cable has to come before it can turn.

    The plug sits BEHIND its cradle, a board's length inside the housing, so a straight
    run at it from the next lever goes through whatever is in between -- on one station
    that was the board itself, its crystal and two of its capacitors. Coming in along
    the axis from past the housing's back end is the route that exists in air, and it is
    the one the user drew: "route it around the back".
    """
    x0 = HOUS_X0 if x_back is None else x_back
    return abs(plug_point()[0] - x0) + 4 * D.BEAD


def cable_guide(x_face, y_face, z_bed, z_top, sx=1.0, sy=1.0):
    """A TURN POST at a housing's front corner, on the connector side.

    Only one lever needs it, and it is the vertical one. LKV is the horizontal lever
    rotated 90 deg, so its body lies ALONG its plug's axis and its connector points down
    that axis, away from the neighbour the bus arrives from: every straight line to the
    plug crosses the housing, the axle or the arm. This is the alternative to bending
    the cable round nothing -- a post the cable genuinely wraps, so the turn has
    something making it, which is the rule the rest of this harness is drawn to.

    Same shape as the keeper: a pillar along the build direction with a 45 deg head, on
    a base in the corner it stands in. The base ties it to BOTH faces it sits against.
    `sx`/`sy` pick WHICH corner: the post projects that way off the faces given.

    IT GOES ON THE BACK CORNER, AWAY FROM THE ARM (user, 2026-09-23: "the cable
    shouldn't go around the front next to the lever arm, it should go around the back",
    and "the +y side"). Right: LKV's arm hangs to -Y and sweeps there, so a turn post at
    the front corner puts the cable through the one part of this lever that MOVES. The
    back corner -- past the +Y end, on the far cheek -- is still air at every throw.
    """
    r = KEEP_POST_D / 2.0
    xc = x_face + sx * (r + D.MIN_WALL_2P)
    yc = y_face + sy * (KEEP_COIL_R + CANB_BUNDLE_OD / 2.0 + KEEP_CLR_Y)
    z1 = z_top - KEEP_HEAD - D.MIN_WALL_2P
    post = cyl(KEEP_POST_D, z1 - z_bed, z=z_bed).translate((xc, yc, 0.0))
    head = cq.Workplane("XY").add(cq.Solid.makeCone(
        r, r + KEEP_HEAD, KEEP_HEAD, cq.Vector(xc, yc, z1), cq.Vector(0, 0, 1)))
    xe = xc + sx * r
    base = box_at(abs(xe - x_face), abs(yc - y_face), KEEP_WEB_H,
                  x=(x_face + xe) / 2.0, y=(y_face + yc) / 2.0,
                  z=z_bed + KEEP_WEB_H / 2.0)
    return post.union(head).union(base)


def guide_point(x_face, y_face, z_bed, sx=1.0, sy=1.0):
    """Where a cable wraps the turn post: its axis, above the base."""
    return (x_face + sx * (KEEP_POST_D / 2.0 + D.MIN_WALL_2P),
            y_face + sy * (KEEP_COIL_R + CANB_BUNDLE_OD / 2.0 + KEEP_CLR_Y),
            z_bed + KEEP_WEB_H)


def keeper_point(z_bed=None, x_back=None, y_face=None, z_top=None):
    """THE POST'S AXIS, at the winding base -- where the slack coil starts.

    ⚠ THE COIL IS DRAWN ON THIS, so it is the one place the post's position may be
    written down. cable_keeper builds the post FROM this rather than computing its own
    xc/yc, because it did compute its own and the two drifted the moment the support
    changed width: the post moved to a wound radius off the back face while this still
    returned half the WEB's width, so every coil in the instrument hung 2.5 mm beside
    its post (user, 2026-09-23: "the cable spirals should be pinned to match the column,
    they seem to be hardcoded so when we adjust the column they don't move")."""
    y0 = HOUS_HW if y_face is None else y_face
    x0 = HOUS_X0 if x_back is None else x_back
    return (x0 + KEEP_POST_DX,
            y0 + KEEP_COIL_R + CANB_BUNDLE_OD / 2.0 + KEEP_CLR_Y,
            (HOUS_Z1 if z_top is None else z_top) - KEEP_DROP)


def keeper_axis():
    """The post's axis in the lever's LOCAL frame: the build direction."""
    return (0.0, 0.0, 1.0)


# ── TRAVEL STOP = one M4 under the cartridge pockets (user, 2026-09-24) ──────────
# "a screw to set the maximum lever travel... an M4 centered between the two cartridges
# pointing +X so its head touches the lever and sets a stop point", adjustable over
# "between 5 degrees and the maximum travel amount set by the housing".
#
# THE STOP IS THE HOUSING'S OWN DEFINITION OF FULL THROW. The lever room is bounded on
# -X by the arm's face at THROW, and that plane is now a function of angle rather than
# one lambda inlined in the cut -- so the screw's two extremes are literally the same
# expression as the room it sits in. Back the screw all the way out and it lands ON the
# room's own wall, which is why it can never permit more travel than the part does.
STOP_MIN_DEG = 5.0                  # the shallowest travel the stop can be set to
STOP_SCREW_L = 40.0                 # M4 x 40 BUTTON, the leg lock pins' SKU, 2.5 mm hex --
                                    #   the instrument's one key (fastener_single_tool).
                                    #   x20 was enough for the TRAVEL, but not to park the
                                    #   head behind a cadkit ANCHOR: the pocket and its
                                    #   bite need 12 of solid ahead of where the head sits
                                    #   at the shallow stop, and x20 left 8.05. x40 parks
                                    #   it 16.2 back, and backed right out the head is
                                    #   still inside the housing's open channel
STOP_CH_W = M4_BUTTON_HEAD_D + 2 * HS_CLR       # 8.4: the head drops in through this
STOP_CH_SHOULDER = D.MIN_WALL_2P    # ...straight sides this far above the axis before
                                    #   the 45 deg gable starts, so the ROUND head still
                                    #   fits inside the gable (a gable springing from the
                                    #   axis clears only 2.9 of the head's 3.8 radius)
STOP_CH_FLAT = D.NOZZLE_D           # the gable's tip is DULLED to one bead, cadkit's
                                    #   own teardrop tip: a printer cannot lay a point, and
                                    #   a nozzle-wide flat bridges itself in one pass
STOP_CH_RISE = STOP_CH_SHOULDER + STOP_CH_W / 2.0               # 5.8, axis -> virtual apex
# THE SCREW GOES IN THROUGH cadkit's ANCHOR, not a bore of my own (user, 2026-09-24:
# "your screw isn't using the cadkit screw hole cutter... we always want a fitted
# insert"). cut_anchor is pocket-plus-bite: the Ø6 x 5 melt-fit pocket is cut NOW and
# stands empty, the screw forms its own thread in the selftap below it, and when those
# plastic threads strip a heat-set insert drops into the pocket that was always there.
# No reprint, no redesign -- and the objection that killed the insert first time round
# (nothing can melt one in 45 mm down a blind channel) is answered by the channel being
# open along its whole bottom: the iron comes at it from below.
STOP_ANCHOR_L = M4.insert_depth + 2 * 5 * M4.pitch      # 12: the pocket + the way out
# WHY IT SITS THIS LOW, and it is the whole cost of the feature: the two cartridge
# POCKETS run down to HS_FLOOR_Z - HS_CLR, so "between the cartridges" means BELOW them,
# not beside them -- the rib they leave between them is only 2.1 wide and an M4 wants
# seven. But that rib is REAL MATERIAL, and it is directly over the channel's peak (user,
# 2026-09-24: "directly above it there is a wall that runs between the two cartridges so
# that buys us a tiny bit more room to move the house cut up").
#
# So the wall that binds is not the vertical drop from the pocket FLOOR -- it is the
# PERPENDICULAR distance from the pocket's inner bottom CORNER to the 45 deg gable face,
# and a 45 deg face is only 1/sqrt(2) as far from a corner as its vertical offset makes
# it look. Constraining the apex vertically, as this did, was both the wrong measurement
# and the stingier one: it left 1.87 of wall where 1.6 was asked for, and paid 0.39 of
# part depth for the difference.
_STOP_RIB_HW = abs(HS_YC) - HS_POCKET_HW                        # 1.05: half the rib
STOP_POCKET_Z0 = HS_FLOOR_Z - HS_CLR + _FEEL_DZ                 # the pockets' underside
# the gable springs from the dulled tip, so the corner clears THAT line, not the point
_STOP_APEX = (STOP_POCKET_Z0 + (_STOP_RIB_HW - STOP_CH_FLAT / 2.0)
              - D.MIN_WALL_2P * math.sqrt(2.0)) + STOP_CH_FLAT / 2.0
STOP_Z = _STOP_APEX - STOP_CH_RISE                              # the screw's axis
# ...and the floor goes FLAT at the channel's own bottom (user: "thicken the lever
# housing towards -z along the whole bottom (needs a flat print bed)"). Flat matters more
# than thin here: a local boss under the channel alone would be a step in the bed face,
# i.e. a downward flat in mid air, which is the exact fault check_ceilings now hunts.
# ...and the bed clears whichever is deeper -- the channel, or the anchor's Ø6 pocket
# with its own 2-bead wall under it. The pocket wins by 0.4, which is very nearly the
# 0.39 the rib bought back above: a fitted insert costs what the better measurement saved.
STOP_FLOOR_Z = STOP_Z - max(STOP_CH_W / 2.0,
                            M4.insert_pilot_d / 2.0 + D.MIN_WALL_2P)


def arm_face_x(deg, z):
    """The arm's -X face (plus clearance) at depth `z`, with the lever at `deg`.

    ONE expression for two jobs that must not drift: it is the -X boundary of the lever
    room -- the housing's own statement of full throw -- and it is where the stop screw's
    tip has to land to allow exactly that much. Reading the second off the first is what
    makes "the maximum travel amount set by the housing" a fact rather than a matching
    pair of numbers."""
    t = math.radians(deg)
    return (math.tan(t) * z
            - ((ARM_TX / 2 + HS_CLR) + ARM_TX / 2 * (1 / math.cos(t) - 1) + 0.4))


STOP_TIP_OUT = arm_face_x(THROW, STOP_Z)            # fully backed out = the housing's max
STOP_TIP_IN = arm_face_x(STOP_MIN_DEG, STOP_Z)      # ...fully in = STOP_MIN_DEG of travel
# THE ANCHOR ENDS AT THE ROOM WALL, so its bite is as deep as the part allows, and it
# starts a whole anchor short of that. The channel runs out to meet it.
STOP_ANCHOR_X = STOP_TIP_OUT - STOP_ANCHOR_L        # the pocket's mouth = channel's end
STOP_HEAD_X = STOP_TIP_IN - STOP_SCREW_L            # where the head parks, screwed fully in
# THE BORE HAS TO CLEAR THE ROOM WALL AT THE SCREW'S TOP EDGE, not at its axis (user:
# "the screw cut doesn't extend far enough towards the lever, it leaves some material
# blocking the way"). That wall is the 30 deg SLANT, so it stands further +X the higher
# you measure it -- 3.07 further at the top of a Ø4.4 bore than on the centre line. Ending
# the bore at the axis's wall left exactly that wedge over the hole, and the screw drove
# into it 3.1 mm3 short of its own travel.
# ...AND IT RUNS AS FAR AS THE SCREW DOES, not as far as the room's wall. Tying it to
# arm_face_x tied it to the POLYGON room, and the moment the room became an honest sweep
# the wall moved and the bore stopped 8.7 short of the screw's own reach -- a lip, exactly
# where the tip has to pass (user, 2026-09-28: "the stop position setscrew still isn't
# drilled far enough towards +x. it stops a bit short leaving a lip here"). The bore
# serves the SCREW; its end is where the screw's tip can reach and nowhere else.
STOP_BORE_END = STOP_TIP_IN
assert STOP_HEAD_X <= STOP_ANCHOR_X + 1e-9, (
    "screwed fully in, the travel stop's head reaches %.2f -- %.2f INTO its own anchor. "
    "It needs a longer screw, not a deeper channel" % (STOP_HEAD_X, STOP_HEAD_X - STOP_ANCHOR_X))

# the wall the rib actually leaves, measured perpendicular to the gable it faces
_STOP_WALL = ((STOP_POCKET_Z0 - (STOP_Z + STOP_CH_RISE - STOP_CH_FLAT / 2.0))
              + (_STOP_RIB_HW - STOP_CH_FLAT / 2.0)) / math.sqrt(2.0)
assert _STOP_WALL >= D.MIN_WALL_2P - 1e-9, (
    "the travel stop's channel leaves only %.2f between its gable and the cartridge "
    "pocket's inner corner" % _STOP_WALL)



def stop_screw_x(deg):
    """Where the stop screw's TIP sits to allow `deg` of travel -- and so where its head
    is, STOP_SCREW_L behind. Used by the dummy, so the assembly shows a real setting."""
    return arm_face_x(deg, STOP_Z)


def _stop_channel():
    """The screw's way: a house profile (straight sides, 45 deg gable) along X, open out
    the -X face AND down through the new floor.

    OPEN AT THE BOTTOM because that is how the screw gets in (user: "a /\\ cut out in the
    lever housing floor which ensures you can both install the screw and adjust its
    rotation"). Threading a Ø7.6 head 45 mm down a blind bore would need the bore at head
    diameter its whole length, and under the pocket floor that costs another 1.7 of part
    depth; dropped in from below, the head only needs room where it actually parks. The
    gable is not decoration -- a flat roof over an 8.4 channel is a bridge, and this part
    prints -Z->+Z."""
    zb = STOP_FLOOR_Z - 1.0
    hw = STOP_CH_W / 2.0
    zs = STOP_Z + STOP_CH_SHOULDER
    fw = STOP_CH_FLAT / 2.0                       # ...the dulled tip, cadkit's teardrop
    pts = [(-hw, zb), (-hw, zs), (-fw, zs + hw - fw), (fw, zs + hw - fw), (hw, zs), (hw, zb)]
    # IT STOPS WHERE THE THREAD STARTS. Run out to STOP_PILOT_X1 instead and the channel
    # swallows the pilot whole -- the screw then passes through 7.25 mm of nothing and
    # forms its thread in air. Measured that way first: 0.9 mm3 of bite where there
    # should be 17.
    face = cq.Face.makeFromWires(cq.Wire.makePolygon(
        [cq.Vector(STOP_ANCHOR_X, y, z) for y, z in pts]
        + [cq.Vector(STOP_ANCHOR_X, pts[0][0], pts[0][1])]))
    return cq.Workplane("XY").add(cq.Solid.extrudeLinear(
        face, cq.Vector(STOP_ANCHOR_X - (HOUS_X0 - 1.0), 0, 0) * -1))


# ── KNEE RELIEF: the bottom +X corner comes off at 45 (user, 2026-09-24) ─────────
# There are two zones under this housing and only one of them costs anything. Zone A --
# the -X length of it -- is free height: the player's knee never goes there, so it only
# matters if it out-reaches the body adapter, which sets the instrument's Z extent and
# has headroom to spare. ZONE B is the bit beside the lever arm, and that is exactly
# where the top of a knee arrives. So the corner comes off at 45: self-supporting from
# below in the -Z->+Z print, and it hands the knee back everything it takes.
#
# WHAT STOPS IT IS THE BEARING, not a printing rule (user: "we shouldn't jeopardize the
# strength of the bearing which will be taking the force of the spring and the counter
# force of the player's knee... I wouldn't recommend going for our minimum bead size of
# 1.6mm"). So this wall is NOT D.MIN_WALL_2P. It is three times it, and the cut is a
# plane TANGENT to a circle of seat + wall about the axle -- the same construction
# _SEAT_ROOF_Z already uses for the seat's roof, so the two faces are the same idea
# measured the same way, one above the axle and one below it.
KNEE_BRG_WALL = 6 * D.BEAD          # 4.8 of backing behind the race, vs 1.6 elsewhere
KNEE_CHAM_C = (BRG_SEAT_D / 2.0 + KNEE_BRG_WALL) * math.sqrt(2.0)


def board_guard(z_bot=None, z_top=None, flip=None, right=False):
    """The sensor board's envelope grown a 2-bead wall, AS INSTALLED in this housing.

    Shared by both levers' knee reliefs. As it happens the two come out IDENTICAL today --
    board_flip is False for both, so board_x/board_z return the same constants and a copied
    wedge would have worked. That is not a reason to copy one: board_flip exists because
    this board CAN be installed turned over, knee_lever_vert asserts that LKV must not be,
    and the day either assertion moves, a guard that reads the housing follows the board
    while a copied one silently guards the other lever's. Its Y comes off the board itself;
    the cradle is the same part in both, so that dimension genuinely is shared.
    """
    z_bot = HOUS_Z0 if z_bot is None else z_bot
    z_top = HOUS_Z1 if z_top is None else z_top
    bx0, bx1 = board_x(z_bot, z_top, flip, right)
    bz0, bz1 = board_z(z_bot, z_top, flip, right)
    b = sensor_board().val().BoundingBox()
    g = D.MIN_WALL_2P
    return box_at(abs(bx1 - bx0) + 2 * g, b.ylen + 2 * g, abs(bz1 - bz0) + 2 * g,
                  x=(bx0 + bx1) / 2.0, y=(b.ymin + b.ymax) / 2.0, z=(bz0 + bz1) / 2.0)


def _knee_relief(right=False):
    """The 45 deg corner cut, across the housing's own width only.

    IT RUNS PAST THE CHEEKS AND OVER THE CRADLE (user, after seeing the -Y side: "ideally
    we could cut away material on the +y side as well in the same region, but we are
    limited somewhat by the PCB housing... without jeopardizing the PCB retention"). The
    measurement says the two do not actually contend: the board sits x -28..3, and at its
    own lowest the wedge does not begin until x 6.37, so the plane misses the board
    entirely. What it takes outboard of the cheeks -- 1212 mm3 of it -- is cradle CORNER,
    not anything that holds a board.

    The board is guarded anyway, by its own envelope grown a 2-bead wall. Not because the
    arithmetic above is in doubt, but because it is arithmetic about ONE pose of a board
    that has already been turned over once this year: if the board moves, the guard moves
    with it and the cut gives way, rather than quietly shaving a groove wall.
    """
    z0 = STOP_FLOOR_Z - 1.0
    xo = HOUS_X1 + 1.0
    y0, y1 = -HOUS_HW, CR_Y1 + D.MIN_WALL_2P
    pts = [(z0 + KNEE_CHAM_C, z0), (xo, z0), (xo, xo - KNEE_CHAM_C)]
    f = cq.Face.makeFromWires(cq.Wire.makePolygon(
        [cq.Vector(x, y0, z) for x, z in pts] + [cq.Vector(pts[0][0], y0, pts[0][1])]))
    wedge = cq.Workplane("XY").add(cq.Solid.extrudeLinear(f, cq.Vector(0, y1 - y0, 0)))
    return wedge.cut(board_guard(right=right))


def _stop_skirt(w):
    """The part's own BED FACE, carried down to the travel stop's floor.

    The stop needs the housing deeper, and the naive way to get that is a deeper prism --
    but the prism is not the whole footprint. The sensor cradle hangs off the +Y face and
    the cable keeper stands beside it, both bottoming at HOUS_Z0, and a deeper prism left
    the two of them 10 mm up in the air: 495 mm2 of flat ceiling over nothing, reported
    the moment check_ceilings looked. Dropping each one by hand means teaching each one
    the stop's floor -- and the cradle's z_bot is what the sensor BOARD's position is
    derived from, so that particular hand would have moved the board off its magnet.

    Taking the bed face itself and extruding it is the version with no hands in it. Every
    slot and opening the part already has comes down with it, nothing needs to know why,
    and HOUS_Z0 keeps its meaning for the cable keeper's winding datum.
    """
    out = w
    for f in w.val().Faces():
        try:
            n = f.normalAt()
        except Exception:
            continue
        if n.z < -0.99 and abs(f.Center().z - HOUS_Z0) < 1e-6:
            out = out.union(cq.Workplane("XY").add(cq.Solid.extrudeLinear(
                f, cq.Vector(0.0, 0.0, STOP_FLOOR_Z - HOUS_Z0))))
    return out


def _housing(right=False) -> cq.Workplane:
    """ONE PARAMETRIC PRISM (user simplification round): the box spanned by
    HOUS_* (every face derived from the lever / cartridge / body extents),
    PLUS the mount tenons, minus exactly four families of cuts.

    MOUNT (user): FOUR fused octagon tenons on the TOP face, one per chassis
    rib crossing the housing (TEN_X = 0, -23, -46, -69 on the rib comb's
    23 mm pitch). Each is a Y-RAIL running the housing's full depth and
    sliding +Y in its rib mortise — that slide IS the knee-depth adjustment.
    They are unioned onto the RAW prism, before any cut, which is what makes
    the +X-most station come out "minimal" without special-casing: it stands
    right over the lever, so the lever-room sweep removes its middle and
    leaves a stub on top of each ±Y cheek wall.

    The cuts:
      * the LEVER ROOM — a hub-band channel over the lever's ±X envelope
        (lever Y-span only, so ±Y CHEEKS survive at the +X end: the future
        bearing walls), opened out the TOP face (the slot hides 0.3 under
        the body; no round-crown ceiling over the lever), the full-width
        lobe/tongue SWING SLOT, and a PLANAR arm-throw wedge (one
        30°-slanted face = the full-throw arm plane; the old curved swept
        relief is PULLED per user — simple first, build back up).
      * two HOUSE-profile cartridge POCKETS (_hs_pocket: rect + 45° gable,
        self-supporting). Both run to the same backmost X — either
        cartridge fits either slot; the MAIN one just parks HS_SETBACK
        forward on its position screw. Their overlapping inner walls
        merge into one void (no unprintable centre sliver).
      * the REAR behind the pockets (cut_feel_rear): per cartridge a washer
        recess + Ø3.2 key way for the POSITION screw and a Ø4.4 way for the
        TENSION screw. No printed thread in the housing any more.
    SENSOR CRADLE (user, see _cradle): two webs + a plinth + a floor off the
    +Y face holding the MT6701 board — retained on five faces by shape, and
    on the sixth by the INSTRUMENT once the lever slides in, so there is no
    retaining screw. A Ø14 driver bore is RESERVED about the axle axis so
    kl_magnet_cap can still be socketed with all this printed.
    DEFERRED: the depth LOCK.
    NOTE — the tenons engage NOTHING at the modelled pose: MOUNT_Y puts the
    housing's +Y face at -134.85 and the chassis rails start at -133.75, so
    the whole housing hangs 1.1 mm OUTBOARD of the rib comb. That pose is the
    fully-slid-OUT limit; engagement = slide - 1.1. See the note in the mount
    block — moving MOUNT_Y +Y is the fix, and it is the user's call.
    Prints -Z→+Z (the tenons are the octagon family, self-supporting).

    `right` is the RIGHT-HAND housing (a lever struck by the knee moving +X): this
    part's mirror image in X, except that the board it holds is NOT a mirror image --
    there is one board design -- so its cradle and its knee relief are drawn for that
    board turned over about the axle (see _turned). The board then sits 1.7 higher in
    it, long end up, and needs no shim."""
    w = box_at(HOUS_X1 - HOUS_X0, 2 * HOUS_HW, HOUS_Z1 - HOUS_Z0,
               x=(HOUS_X0 + HOUS_X1) / 2, y=0.0, z=(HOUS_Z0 + HOUS_Z1) / 2)
    # MOUNT TENONS (user), unioned onto the raw prism BEFORE anything is cut — that
    # ordering is what makes the +X-most station come out "minimal" on its own: the
    # lever-room sweep below runs the full tenon height now, so it takes that tenon's
    # middle with it and leaves only the two cheek-wall stubs.
    for _tx in TEN_X:
        w = w.union(_top_tenon(_tx))
    _room = lever_room()        # built once: 31 unions is not free
    w = w.cut(_room)            # the lever's own sweep, and nothing else
    # BEARING SEATS (user): Ø8.1 pockets for the MR85ZZ pair, opening
    # INBOARD at the lever-room walls (±BRG_Y0) and reaching 2.8 into the
    # cheeks (0.3 axial float over the 2.5 bearing — the proven old wall
    # numbers) → 0.7 of outboard skin stays; bearings press in from the
    # lever room. The +Y seat adds a Ø6 axle through-bore out the face
    # (the axle continues to the magnet/sensor cluster); the -Y axle end
    # stops INSIDE its pocket (AXLE_Y0 -13.1). Horizontal round bores in
    # the -Z→+Z print — teardrop/roundness refinement rides the axle round.
    w = cut_axle_stack(w)          # bearing seats + contact rib + axle way
    w = cut_feel_pockets(w, feel_place)
    w = _cradle(w, right=right)                                     # the MT6701 board cradle (user)
    w = w.union(cable_keeper())     # ...and the bus-B keeper on the cheek
    w = _stop_skirt(w)              # ...the bed dropped to make room for the travel stop
    w = w.cut(_room)            # ...and again, after the skirt re-added material
    w = w.cut(_knee_relief(right))  # ...the bottom +X corner off at 45, for the knee
    w = w.cut(_stop_channel())      # ...and the stop's own way in, under the pockets
    # CLEARANCE AHEAD OF THE INSERT, not a self-tap (user: "the screw cut doesn't extend
    # far enough towards the lever, it leaves some material blocking the way"). cut_anchor
    # puts a Ø4.2 self-tapping bore beyond the pocket, which is right when the plastic IS
    # the thread -- but the insert carries this one, so 7 mm of formed thread in front of
    # it is just a second, tighter thread for the screw to fight through every time the
    # travel is set. cut_insert_bore is the same pocket with the bore ahead of it opened
    # to Ø4.4, so the screw spins free from the insert to the lever.
    w = cut_insert_bore(M4, w, (STOP_ANCHOR_X, 0.0, STOP_Z), (1.0, 0.0, 0.0),
                        STOP_BORE_END - (STOP_ANCHOR_X + M4.insert_depth),
                        reason="knee lever travel stop", print_up=PRINT_UP)
    w = heal(roof_close(w, _room))
    return w.mirror("YZ") if right else w


def roof_close(w, *rooms, z_top=None, align=None, step=None):
    """The 45 deg closure over the lever room -- LAST, so it sees the finished solid.

    THE ROOM LEAVES A ROOF AND THE ROOF HAS NOTHING UNDER IT. Now that the room is the
    lever's sweep and nothing else (user, 2026-09-28), the prism's own material closes
    back over the top of it, and a swept hub band's crown is flat: 326 mm2 of ceiling on
    this housing, the worst of it 180 mm2 bridging 11.15 mm. The cheap answer is to pick
    one wall and cut a 45 down to it, and it throws away everything the other walls could
    have carried -- so this grows a 45 out of ALL of them at once (user: "there are three
    walls which we can grow 45 supports out of, and ideally we would use all of them to
    maximize the amount of material above the levers"). See helpers.corbel_close.

    IT IS SCOPED TO THE ROOM, which is what makes it both right and cheap (user: "we can
    focus it to just the area we need help with"). The room's own footprint is the only
    place the prism was opened, so it is the only place a roof can be floating; and the
    material outside that footprint -- the two cheeks and the -X end, the three walls --
    is untouched and hands itself back in as support at every layer. The sweep then starts
    at the PRINT BED, where "supported" is not an assumption at all.

    A step of one BEAD is not a rounding of the layer height: each course of the corbel
    steps out exactly one nozzle width, which is the ledge check_ceilings already calls
    printable rather than a bridge.
    """
    bb = w.val().BoundingBox()
    bed = bb.zmin
    up = box_at(800.0, 800.0, 800.0, z=bed + 400.0).val()          # everything off the bed
    bs = [r.val().intersect(up).BoundingBox() for r in rooms]
    x0, x1 = min(b.xmin for b in bs), max(b.xmax for b in bs)
    y0, y1 = min(b.ymin for b in bs), max(b.ymax for b in bs)
    crop = box_at(x1 - x0, y1 - y0, 800.0, x=(x0 + x1) / 2, y=(y0 + y1) / 2)
    # ...AND IT RUNS TO THE VERY TOP OF THE PART, mount tenons included. Stopping at the
    # housing's top face left the tenon that stands over the lever sitting on the roof the
    # closure had just carved out from under it: 27 mm2 of its underside bridging 3.30 mm,
    # the worst ceiling left in the part. Carried on up, the tenon gives back 49 mm3 -- a
    # nibble out of the one corner of it that was over the void -- and the mortise faces,
    # which are its flanks, are untouched.
    # THE STEP IS NOT THE SURFACE QUALITY any more -- the cut is drafted, so its faces
    # are true planes whatever the step -- it is how finely the sweep TRACKS a change in
    # support. One bead is enough wherever the walls are wide. It is not enough on the
    # vertical lever, whose rib between the cartridge pockets is 2.1 wide: the support
    # there changes inside a single course and the sweep stepped straight over it,
    # leaving 1.72 mm2 of flat on the rib's underside (user, 2026-09-29: "there's an
    # overhang here"). Half a bead closes it completely, and costs that part 9.7 s.
    return corbel_close(w, crop, bed, bb.zmax if z_top is None else z_top,
                        D.BEAD if step is None else step,
                        align=HOUS_Z1 if align is None else align)


def _lever_envelope() -> cq.Workplane:
    """The lever grown by HS_CLR on every face -- the thing that gets swept to make the
    lever room. Built from the same primitives as _lever rather than offset from it, so a
    change to one is visibly a change to the other (the vertical lever's is the same)."""
    c = HS_CLR
    hub = cyl_y(HUB_D + 2 * c, 2 * (LEVER_HW + c), y0=-(LEVER_HW + c))
    arm = box_at(ARM_TX + 2 * c, 2 * (LEVER_HW + c), ARM_LEN + c,
                 x=0.0, y=HUB_YC, z=-(ARM_LEN + c) / 2.0)
    lobe = (cyl_y(2 * LOBE_R + 2 * c, 2 * (LEVER_HW + c), y0=-(LEVER_HW + c))
            .translate((0.0, 0.0, -LOBE_RC)))
    return heal(hub.union(arm).union(lobe))


def lever_room() -> cq.Workplane:
    """THE LEVER ROOM, and it is now exactly what the name says: the lever's own shape
    swept through its throw. Nothing else.

    IT USED TO BE A DRAWN POLYGON -- a hub band, a 30 deg slant at the full-throw arm
    face, a vertical at the rest arm's +X face, opened out through the top and carried
    past the +X face. Every one of those was a decision about something OTHER than the
    sweep: the top opening was there to avoid a ceiling, the +X extension to let a
    storage fold swing, the vertical to keep the +X half-space clear. They are real
    concerns, but folding them into the room made the room mean four things at once, and
    then nobody could tell which part of it any given face came from -- the user asked
    what made a vertical face and the honest answer took a measurement to find.

    A room is one of two things (user, 2026-09-28): the sweep of the lever's rotation, or
    the path that installs it. THIS lever needs only the first: its arm hangs -Z out of an
    open floor, so the rest pose being cut IS an install path, straight down.

    THE SWEEP RUNS BOTH WAYS -- -STORAGE to +THROW. Forward is the throw the knee drives;
    back is the fold that puts the lever out of the way, and it is stopped by the VERTICAL
    lever's arm rather than by anything here. The old polygon had a note about "the
    storage fold at +X swings into air" and a vertical face to keep that half-space open;
    this is that same intent, said as a sweep instead of as a wall.
    """
    env = None
    for i in range(-int(STORAGE), int(THROW) + 1):
        c = _lever_envelope().rotate((0, 0, 0), (0, 1, 0), float(i))
        env = c if env is None else env.union(c)
    return env


def _lever() -> cq.Workplane:
    # hub on the axle (bore Ø5). The arm hangs -Z (the leg bears on it) and now ALSO carries the return
    # CAM: a rounded LOBE ridge along its -X FACE at z=-LOBE_RC. The flat piston followers bear on that
    # ridge -> bounded travel through the throw. There is NO dedicated (thin) cam plate -- the THICK arm
    # IS the cam, so no fragile spot. The cam sits -Z of the axle so the feel cartridges hang below it and
    # point -X (a 180°-rotated LKR copy then points its cartridges the other way and never collides).
    hub = cyl_y(HUB_D, 2 * LEVER_HW, y0=-LEVER_HW)
    arm = box_at(ARM_TX, 2 * LEVER_HW, ARM_LEN, x=0, y=HUB_YC, z=-ARM_LEN / 2)
    body = hub.union(arm)
    # ONE centred lobe ridge spanning the FULL lever width. A CENTRED lobe (extremum ~x=0, right under the
    # axle) barely moves in Z through the throw, so the followers stay on it and the moment arm holds (an
    # off-axle face lobe traced a big arc and slipped off). It's reached through TWO LOCAL recesses in the
    # arm's -X face (one per follower); the ridge only PROTRUDES in those two bands -- between and around
    # them it's buried in the solid arm (identical contact, one primitive), and the un-recessed spans keep
    # the arm stiff.
    # Recess: instead of one oversized rectangular notch, cut the tongue's SWEPT-motion clearance envelope
    # (_recess_swept) at each lobe band -- its walls hug the piston (sloped -Z wall ~parallel to the 30 deg
    # piston; +Z wall set by the fold), so the arm keeps its material right behind the lobe. The lobe
    # protrudes -X into the opening for round contact. The arm keeps its full +X half at each band, so each
    # is a local notch, not a through-thin.
    body = body.cut(_RECESS_SWEPT)                                              # -Y (MAIN) follower band
    body = body.cut(_RECESS_SWEPT.translate((0, HS_YC - MAIN_YC, 0)))          # +Y (HALF-STOP) follower band
    body = body.union(cyl_y(2 * LOBE_R, 2 * LEVER_HW, y0=-LEVER_HW)        # ONE full-width lobe ridge; the
                      .translate((0, 0, -LOBE_RC)))                        #   spans between recesses bury in the arm
    body = cut_axle_bore(body)
    return heal(body)


def kl_axle() -> cq.Workplane:
    """PCTG AXLE ×1 per lever — ONE full-length printed part (user: the old
    integral-stub + glued-insert pair could not physically be assembled).
    Fitted LAST and slid +Y -> -Y through the +Y bearing, the lever hub and
    the -Y bearing, so nothing has to thread a rigid stub into an already-
    captured bearing.

      * Ø8 journals at both bearings.
      * a D-FLAT from the leading tip through the hub band = the anti-rotation
        key (a protruding tongue could not pass the bearing bore on the way in).
      * an M4 thread-forming BORE in the -Y tip: one button head and a washer
        go in there once the axle is through, and that is the axial retention
        (see AXLE_END_PROUD). No glue, and nothing in the hub.
      * a FLANGE that seats on the housing's contact rib — the axial datum
        that sets the magnet's Y, and with it the sensor air gap.
      * a magnet POCKET with a MALE thread on its OD; kl_magnet_cap screws
        over it and clamps the disc.

    Prints STANDING, POCKET-DOWN (collar face on the bed): that way the
    journal -> flange step is an upward-facing floor rather than an
    overhanging ledge, the 45° thread flanks self-support, and the end screw's
    bore is a plain hole down from the top. Use a brim —
    the bed footprint is only the collar's annulus under a ~31 mm column.
    Built along +Z, threaded, then rotated onto the lever's +Y axis; the flat
    is milled AFTER the thread (cadkit thread rule) and it is NEVER healed."""
    from cadkit.threads import cut_thread
    r = AXLE_D / 2
    # smooth blank along +Z: journal shaft, then the flange/collar barrel
    b = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        r, AXLE_SHOULDER_Y - AXLE_Y0, cq.Vector(0, 0, AXLE_Y0), cq.Vector(0, 0, 1)))
    b = b.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(   # inner-race LAND (the datum)
        AXLE_LAND_D / 2, AXLE_LAND_T, cq.Vector(0, 0, HOUS_HW), cq.Vector(0, 0, 1))))
    b = b.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        (MAG_TH_MAJOR - MAG_TH_CLR) / 2, MAG_FLANGE_T + MAG_COLLAR_H,
        cq.Vector(0, 0, AXLE_SHOULDER_Y), cq.Vector(0, 0, 1))))
    b = b.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(   # flange (clear of the shield)
        AXLE_FLANGE_D / 2, MAG_FLANGE_T,
        cq.Vector(0, 0, AXLE_SHOULDER_Y), cq.Vector(0, 0, 1))))
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(     # magnet pocket
        MAG_POCKET_D / 2, MAG_COLLAR_H + 1.0,
        cq.Vector(0, 0, MAG_Y0), cq.Vector(0, 0, 1))))
    b = cut_selftap(M4, b, (0.0, 0.0, AXLE_Y0), (0.0, 0.0, 1.0), AXLE_TAP_L,
                    overshoot=0.5, print_up=(0.0, 0.0, -1.0))      # the end screw's bore
    b = heal(b)
    # MALE thread on the collar (blank is already at crest Ø), then the flat
    b = cut_thread(b, minor_d=MAG_TH_MINOR - MAG_TH_CLR,
                   major_d=MAG_TH_MAJOR - MAG_TH_CLR,
                   pitch=MAG_TH_PITCH, length=MAG_COLLAR_H, z=MAG_Y0)
    b = b.rotate((0, 0, 0), (1, 0, 0), -90)          # +Z -> +Y (the lever's axis)
    # D-flat, milled last (cadkit thread rule), +Z side, running from the
    # leading tip to AXLE_FLAT_Y — see the constant block for why it cannot
    # stop short of the tip.
    _zhi, _ylo = r + 1.0, AXLE_Y0 - 1.0
    return b.cut(box_at(AXLE_D + 2.0, AXLE_FLAT_Y - _ylo, _zhi - AXLE_FLAT_R,
                        x=0.0, y=(_ylo + AXLE_FLAT_Y) / 2,
                        z=(AXLE_FLAT_R + _zhi) / 2), clean=False)


def kl_magnet_cap() -> cq.Workplane:
    """PCTG MAGNET CAP ×1 per lever (user): a HEX nut with a FEMALE thread on
    its ID that screws over the axle's pocket collar and clamps the Ø6 magnet
    in. Sized across flats for a 3/8" female hex driver (user) — and that is
    what set the thread Ø, since a 3/8" socket around a Ø6.2 pocket leaves only
    ~1.66 of radius for collar wall + thread + cap wall (see MAG_TH_MAJOR).
    Fit it BEFORE the sensor board: the socket comes down the axis the board
    later occupies.
    Its bore stops 0.1 short of the collar's rim, so it always lands on the
    DISC rather than bottoming on the collar and leaving it loose.

    The centre stays OPEN (CAP_APERTURE): the cap must never sit between the
    magnet and the chip — that distance is the air gap, and anything in it
    would have to come out of the gap budget.

    Prints APERTURE-DOWN: with the flange on the bed, the bore's step out to
    the thread Ø is an upward-facing floor (nothing overhangs), and the
    internal 45° thread flanks self-support. Built along +Z and rotated onto
    the lever's +Y axis; threaded LAST and NEVER healed."""
    from cadkit.threads import threaded_rod
    _ac = CAP_HEX_AF * 2.0 / math.sqrt(3.0)          # hex across-corners
    _z0 = MAG_Y0 + CAP_BASE_CLR                      # rim held clear of the axle flange
    # THREADED BARREL ONLY, up to the magnet face...
    b = heal(cq.Workplane("XY").workplane(offset=_z0)
             .polygon(6, _ac).extrude(MAG_Y1 - _z0))
    nut = threaded_rod(MAG_TH_MINOR, MAG_TH_MAJOR, MAG_TH_PITCH,
                       MAG_Y1 - _z0, z=_z0)
    b = b.cut(nut, clean=False)
    # ...and the clamping FLANGE unioned on AFTERWARDS. Order matters: the
    # thread cutter rounds its span up to whole turns, so building the flange
    # first lets it overrun and quietly eat the very face that holds the magnet
    # (a probe caught exactly that — the cap came out a plain ring that touched
    # nothing but its own collar).
    flange = (cq.Workplane("XY").workplane(offset=MAG_Y1)
              .polygon(6, _ac).extrude(CAP_T)
              .cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(   # sensor aperture
                  CAP_APERTURE / 2, CAP_T + 2.0,
                  cq.Vector(0, 0, MAG_Y1 - 1.0), cq.Vector(0, 0, 1)))))
    b = b.union(flange, clean=False)
    return b.rotate((0, 0, 0), (1, 0, 0), -90)          # +Z -> +Y


knee_housing = _housing()
knee_housing_r = _housing(right=True)       # the right-hand lever's (LKR, RKR)
knee_lever = _lever()
kl_axle = kl_axle()                            # printed: full-length PCTG axle
kl_magnet_cap = kl_magnet_cap()                # printed: screw-on magnet retainer
# ONE shared cartridge (printed twice: MAIN + HALF-STOP). Built canonically (MAIN placement: follower
# at the lobe rest extremum); the assembly slides a HALF-STOP copy +X by HS_SETBACK and a MAIN copy to
# MAIN_YC. Placement helper for build.py / tools:
CART_MAIN_OFFSET = (0.0, MAIN_YC - HS_YC, 0.0)        # main copy: shift to -Y
CART_HALFSTOP_OFFSET = (HS_SETBACK, 0.0, 0.0)         # half-stop copy: slide +X (engagement setback)
cart_base = _half_stop_cart_base()             # printed: cartridge (inverted-U, open -Z; no separate roof)
cart_piston = _half_stop_piston()              # printed: piston (Ø10 head + follower tongue + spring pilot)

# (the FLOATING TENON is retired -- the octagon tenons are now FUSED onto the housing yoke, so
# the lever mounts as a single part; the rib carries the matching octagon mortise. See _mount.)
