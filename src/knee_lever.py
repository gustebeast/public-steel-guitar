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
import pathlib
import sys

import cadquery as cq

from . import dimensions as D
from . import components as C
from .helpers import box_at, cyl, cyl_y, heal

from cadkit.fasteners import (M2_SELFTAP_D, M4_SHAFT_CLR_D, M4_INSERT_D,
                       M4_INSERT_L, M4_SCREW_L, M4, cut_insert_bore,
                       cut_m4_pocket, seated_m4_insert, cut_m4_boss, m4_boss_insert)
from cadkit.pcb import (jst_xh_side_header, xh_side_length,
                        XH_SIDE_H, XH_SIDE_D)
from cadkit.joinery import PrintSpec, joint   # cadkit's one joinery entrypoint
from cadkit.supports import printable_bore, contact_rib
# the M4 insert pocket/boss helpers now live in cadkit/fasteners.py (shared); keep the old local names:
_insert_pocket, _seated_insert = cut_m4_pocket, seated_m4_insert
_insert_boss_cut, _insert_dummy = cut_m4_boss, m4_boss_insert

# ── bought parts (assembly dummies). REUSE existing line items where possible so they buy in
# bulk: MR85ZZ bearings + the M4×10 cup-tip set screws + M4 heat-set inserts are ALL already in
# the BOM (nut-block / screw-support). New: the Ø6 magnet, the MT6701 board, the springs.
AXLE_D  = 5.0                       # Ø5 axle journals — PCTG now (user: no steel pin).
                                    # Zero torque lives on the axle (the springs act on
                                    # the LOBE; the magnet only co-rotates for the
                                    # sensor) and the radial bearing reactions (~4-5x
                                    # knee force ≈ 130 N worst) sit ~5x under a Ø5 PCTG
                                    # journal's shear capacity; the steel MR85 inner
                                    # races take all the wear. +Y journal + magnet stub
                                    # print INTEGRAL with the lever (standing off its
                                    # lying -Y bed face); the -Y journal is the glued
                                    # kl_axle_insert (the bed face must stay flat).
BRG_OD, BRG_ID, BRG_W = 8.0, 5.0, 2.5   # MR85ZZ — shared with the screw-support bearings
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
PCB_WZ = 19.0                       # ONE board for every lever. The outline is ours; what
PCB_T = 1.6                         # sets it is the cradle + the reserved driver bore (see
                                    # the cradle block) and, in Z, the instrument itself —
                                    # the board runs from the chassis underside down.
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
INSERT_D, INSERT_L = M4_INSERT_D, M4_INSERT_L   # M4 heat-set insert Ø6 × 5 (standard set-screw process)
SCREW_CLR = M4_SHAFT_CLR_D          # M4 set-screw shaft clearance (Ø4.4)

# ── housing envelope ─────────────────────────────────────────────────────────
WALL    = 4.0                       # bearing-wall thickness (Y)
HALF_X  = 11.0                      # housing half-width in X (the bearing block; sits in the bay)
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
HUB_D   = 10.0                      # ONE lever constant: the hub OD *and* the arm depth (ARM_TX). Keeps
                                    # the feel on the clear cam above the round hub, and the arm as deep
                                    # as the hub is wide for a solid root.
ARM_LEN = 100.0                     # hub centre -> arm tip (knee reach, -Z)
ARM_TX  = HUB_D                     # arm depth in X (bending axis: knee pushes X) = the hub OD
ARM_WY  = 20.0                      # arm width in Y -- the face the player's leg bears on (no paddle)
LEVER_HW = ARM_WY / 2               # UNIFORM lever half-width: hub, lobe and arm are all ±LEVER_HW (one
                                    #   clean section). It no longer reaches the ±12 walls, so...
PIVOT_BOSS_D = 8.0                  # ...the housing carries a small Ø8 thrust boss at each hub end for
PIVOT_CLR = 0.2                     #   low-friction Y location (a ring, not the whole hub face)
THROW   = 30.0                      # neutral -> full throw (deg, +theta about +Y). 30° is the useful max
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
LOBE_RC = 9.0                                # lobe axis radius (pivot -> lobe) = axle->lobe Z. The whole
                                             #   feel block tracks -LOBE_RC (feel_place), so this sets how
                                             #   close the contact -- and the swept recess above it -- ride
                                             #   toward the axle. The recess just carves the hub as it
                                             #   rises, so the real limit is the solid WEB it leaves to the
                                             #   Ø5 axle bore: 9.0 leaves ~2.6mm (measured; each -1mm of
                                             #   LOBE_RC costs 1mm of web, 0.8mm being the thin-wall floor).
                                             #   Ratio ARM_LEN/LOBE_RC = 100/9 = 11.1:1, follower travel =
                                             #   9*sin30 = 4.5mm. 9 (not 8) so the Ø1.4 feel coil keeps
                                             #   fatigue headroom for the setscrew (10.3N knee ceiling vs
                                             #   8N target). Raising THROW would swing the lobe higher,
                                             #   thinning the web -> raise LOBE_RC.
LOBE_R  = 1.5                                # rounded lobe radius
LOBE_WY = 6.0                                # each lobe's / follower-tongue Y width -> a 6×6 SQUARE face.
                                             #   The two cartridges are flushed to the centre (dead wall gone)
                                             #   and the piston HEAD widened to (LOBE_WY+2) so the 0.8mm front
                                             #   lip survives -- so the tongue can be this wide within the 20mm
                                             #   arm (0.8mm arm-outboard wall) without a bigger coil.
CAM_TX  = 3.0                                # cam-plate thickness in X (the swing direction)
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

# ── HALF-STOP = a self-contained PRELOADED spring CARTRIDGE (three printed parts + a coil) ─────────
# The coil pushes a PISTON whose rounded NOSE protrudes -X out of the cartridge front. The cam blade
# bears DIRECTLY on that protruding nose -- NO lever nub. Because the nose always sticks out (its
# protrusion > its travel), the cam never has to reach inside the cartridge, and the ROUNDED tip keeps
# clean contact as the cam rotates through the throw. The coil is preloaded against the piston (held
# forward by front side-lips), so contact makes a crisp force SHELF, then rises.
#   * half_stop_spring_tension_setscrew -- cartridge back, compresses the coil = PRELOAD (shelf height)
#   * half_stop_start_setscrew          -- in the housing, slides the cartridge in X = engagement GAP
# The cartridge prints as a BASE (U-channel, open top) + a ROOF that slides on via a Y sliding dovetail
# -> no internal-roof overhang, and the piston drops into the base before the roof caps it. Rounded
# anti-bind RIBS run along X on the floor + roof underside, giving the piston clean bearing lines
# (cures stiction/cocking; pairs with dry PTFE). The cartridge front clears the cam tip (STOP_TIP_X).
# Both springs are the SAME cartridge (printed twice): the MAIN sits so its follower touches the lobe
# at REST (sets the rest angle), the HALF-STOP is slid back HS_SETBACK so it engages partway. Each
# piston has a FLAT FOLLOWER face (spans the lobe Z-band) on a tongue that protrudes -X out of the
# cartridge front; the coil preloads it forward against front side-lips.
# Feel coil (see knee-lever-feel-spring memory): servos pull the strings, so the coil only makes FEEL +
# return. At LOBE_RC=9 the 11.1:1 ratio turns the 8N-at-knee feel into ~89N at the piston over the 4.5mm
# throw travel -> a k~17 N/mm coil. That force OVER-STRESSES Ø1.2 music wire (fatigue), so the wire is
# Ø1.4: peak shear ~575 MPa with a 10.3N-at-knee fatigue ceiling, i.e. real setscrew headroom above the
# 8N target. The tradeoff is length -- k~17 with Ø1.4 needs ~25 coils (~34.5mm solid), so the coil/
# cartridge run longer than the old Ø1.2. Y (not Z) is the binding axis; the coil sits in a Ø6.6 bore
# (cartridge outer stays 8.8 -> same pocket, no bearing/cam changes). The Ø4 screw drives it through a
# loose captive GUIDE POST (Ø2.8 pilot into the now-Ø3.2 coil ID, Ø6 shoulder), not cup-on-coil.
HS_SPR_OD   = 6.0                   # coil OD (arm width-limited -- can't grow to drop stress, hence Ø1.4 wire)
HS_SPR_WIRE = 1.4                   # coil wire dia (up from 1.2: keeps peak shear fatigue-safe at ~89N)
HS_SPR_ID   = HS_SPR_OD - 2 * HS_SPR_WIRE      # 3.2 -> guide-post / piston pilot noses into this
HS_SPR_FREE = 42.0                  # coil free length = solid(34.5) + throw(4.5) + preload/clash margin
HS_SPR_INST = 41.4                  # coil length DRAWN = bay (lightest preload ~0.6mm; full throw clears solid)
HS_PILOT_D  = HS_SPR_ID - 0.4       # 2.8: centre pilot (piston back + guide-post front) into the coil ID
HS_GPOST_LX = 3.0                   # guide-post body: coil-shoulder -> cup face (screw bears here)
HS_PILOT_LX = 5.0                   # pilot length reaching into the coil ID (piston back & guide post)
HS_ARM    = 4.0                     # follower-tongue Y width band
FOLL_H    = 6.0                    # follower FLAT-face height (Z) = LOBE_WY -> SQUARE face. Centred (FOLL_DZ)
                                   #   so the window BOTTOM lands at the cartridge's already-open -Z bottom
                                   #   (no thin wall, no extra -Z) and the window TOP clears the +Z cap by
                                   #   0.8mm once the cap is raised to the mount (HS_ROOF_TZ). ~1.5mm tracks
                                   #   the lobe; the rest is strength.
FOLL_DZ   = 0.5                    # follower centre offset up from HS_Z: puts the window bottom on the -Z open
                                   #   face and the window top 0.8mm under the mount-height cap
HS_Z      = HUB_TOP + 1.5           # piston / follower centre Z: the HS_ARM tongue spans the lobe band
                                    #   (5.66..8) and clears the hub below; the Ø6 body clears the boss
HS_PISTON_WY = LOBE_WY + 2.0        # piston HEAD width (Y): DECOUPLED from the Ø6 coil -- a wider plate that
                                   #   the coil still pushes on-centre, so the front lip = (head-(LOBE_WY+0.4))/2
                                   #   = 0.8mm survives a 6mm tongue. Rides the (widened) channel; catches the lip.
HS_PISTON_WZ = HS_SPR_OD            # head height (Z) = Ø6 coil seat (the coil bears on the head's -X back face)
HS_FOLLOW_WY = LOBE_WY             # follower width (Y) = the lobe width (only has to cover the lobe); < body
                                  #   so the front lips still capture the body, and it stays narrow enough
                                  #   that the arm keeps a ~0.8mm printable wall outboard of each lobe recess
# CART_RECEDE pushes the whole cartridge back (-X in the placed frame) while the follower NOSE stays on
# the lobe -- so the piston BODY and front walls sit OUT of the swinging arm's arc, and only the thin
# follower tongue reaches into it. Sized (with the front-bottom relief) to clear the full 0..THROW sweep.
CART_RECEDE = 8.0
HS_NOSE_PROTRUDE = FOLL_TRAVEL + 1.0 + CART_RECEDE  # tongue -X of the front (> travel: never retracts; the
                                                   #   extra CART_RECEDE lengthens the tongue = body recede.
                                                   #   8 mm clears the plain-prism cartridge to ~33° with NO
                                                   #   carve -- just push the whole box out of the arm's arc)
HS_BODY_LX = 3.0                    # piston body length in X (was 5; matched to the 3mm guide post -- the 2mm
                                    #   saved pulls the whole cartridge + its back-stop boss 2mm forward, all
                                    #   spent on thread engagement without moving the leg-facing extent). The
                                    #   pilot + tongue add effective bearing length so 3mm won't cock.
HS_CLR    = 0.4                     # piston/coil <-> channel slide clearance (per side)
HS_WALL   = 1.6                     # cartridge STRUCTURAL wall (floor / front / back); the coil-region
                                    #   SIDE walls end up thinner (~1.0, emergent) so the Ø6 coil fits Y
HS_HOUS_WALL = 2.4                  # housing shell wall around the pocket -- CONSTANT thickness, the
                                    #   outer /\ bottom parallels the pocket /\ (no thick flat bottom)
HS_ROOF_TZ = 1.4                    # +Z CAP thickness -> cap top at the mount ceiling (~11.3), giving the
                                   #   0.8mm front-wall above the tall tongue window
HS_LIP    = 1.5                     # front-lip depth in X (side lips that catch the piston body)
HS_TRAVEL = FOLL_TRAVEL + 0.5       # channel back-travel (>= follower travel)
HS_SPR_BORE = HS_SPR_OD + 0.6       # coil clearance bore
HS_ROOF_SPLIT = HS_Z + HS_PISTON_WZ / 2 + HS_CLR   # channel ceiling = +Z cap underside (just above piston)
M4_SELFTAP = 3.4                    # M4 self-tap pilot (compression-loaded position/stop screws)
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
HS_CH_BX    = HS_BODY_BX + HS_TRAVEL         # piston body rearmost (after full-throw travel)
HS_SPR_TIPX = HS_BODY_BX + HS_SPR_INST       # coil BACK / guide-post shoulder (drawn nominal-preload)
HS_GPOST_BX = HS_SPR_TIPX + HS_GPOST_LX      # guide-post back = tension-screw cup face
HS_BACK_X   = HS_GPOST_BX + INSERT_L + 0.5   # cartridge back wall (hosts the tension insert)
HS_CH_WY    = HS_PISTON_WY + 2 * HS_CLR      # channel clear width (Y) = 6.8 (Ø6 coil/piston + slide clr)
HS_CH_WZ    = HS_PISTON_WZ + 2 * HS_CLR      # channel clear height (Z) = 6.8 (unchanged; ribs removed)
HS_WIN_WY   = HS_FOLLOW_WY + 0.4             # front-lip opening in Y: passes the tongue, catches the body
HS_CART_WY  = HS_CH_WY + 2.0                 # cartridge outer Y = channel + 1.0mm side walls (was fixed 8.8;
                                             #   now derived so the wider head/channel carries its own walls)
# cartridge Y placement: align each POCKET (the hole the cartridge slots into) so its outer edge is
# flush with the bearing wall's INNER face on that side -- the cartridge shares the bearing wall (no
# separate wall, no gap). (Earlier this aligned the block's OUTER face with the wall's outer face,
# spreading the cartridges too far.)
HS_POCKET_HW = HS_CART_WY / 2 + HS_CLR        # cartridge pocket (slot) half-width
# Cartridge Y: place each lobe/tongue as far INBOARD as the 0.8mm arm-outboard wall allows -- that (plus
# the wider head) is what frees the width. The two cartridges nearly meet at the centre (the old dead wall
# between them is gone); the wall-side gaps to the bearing walls are the leftover slack.
_ARM_LOBE_WALL = 0.8
HS_YC   =  (LEVER_HW - _ARM_LOBE_WALL - (LOBE_WY + 1) / 2)   # +Y lobe/cartridge centre (arm-outboard-wall limited)
MAIN_YC = -(LEVER_HW - _ARM_LOBE_WALL - (LOBE_WY + 1) / 2)   # -Y
HS_CART_Z1  = HS_ROOF_SPLIT + HS_ROOF_TZ     # cartridge +Z CAP top (< mount boss ~11.3)
# INVERTED-U cartridge, OPEN on -Z (no separate roof): a solid +Z cap (toward the axle, narrow arc) + side
# walls, open on -Z where the arm's arc is WIDEST. The HOUSING floor is the -Z retaining wall (relieved to
# open air at the front, where the arm sweeps). The whole box is pushed clear of the arm's arc by
# CART_RECEDE. Plain rectangular prisms throughout (printability deferred).
HS_POCKET_X0 = SWING_X              # housing pocket front (cartridge front cantilevers -X into the slot)
# ── cartridge X-position retention (adjustable, per cartridge, independent) ──────────────────────────
# In use the contact force pushes each cartridge toward its BACK (+X build); a HOLLOW back-stop screw
# threaded into the housing back boss sets that back limit = the cartridge's X home (MAIN: rest / gravity-
# hold bias; HALF-STOP: engagement angle). It's HOLLOW so the coaxial M4 TENSION screw (preload) still
# reaches the cartridge insert THROUGH it -- the two adjustments stay independent. Compression-loaded (the
# contact force seats it onto the cartridge back), so it holds the load and won't back out. A passive TPU
# DRAG pad in the pocket resists transport drift when the lever is UNLOADED (the back-stop only holds the
# loaded direction). [Stage 1: threads are smooth-cylinder envelopes; the printed coarse thread comes once
# packing is confirmed.]
HS_BSTOP_BORE   = 5.0               # hollow bore -- clears the M4 tension-screw hex-key driver
HS_BSTOP_OD     = 9.0               # thread crest (major) OD; the drive flange stays just under the cartridge pitch
HS_TH_PITCH     = 3.0               # self-supporting 45deg thread pitch. Raised 2.0->3.0: at pitch 2 the
#                                    deep 0.75 flanks + overshoot made the valley (2.35) wider than the
#                                    pitch -> adjacent turns overlapped into a silent no-op cutter (the
#                                    updated cadkit thread check now REJECTS this). 3.0 keeps the grippy
#                                    flanks valid; the 6mm boss = 2 turns (was ~3), enough for a feel stop.
HS_TH_DEPTH     = 0.75              # flank depth <= pitch/2 (=1.5, margin kept); deeper flanks = more grip/prevailing torque
HS_TH_MINOR     = HS_BSTOP_OD - 2 * HS_TH_DEPTH   # 8.0 -> wall to the Ø5 bore = 1.5mm
HS_TH_CLR       = 0.4               # diametral thread clearance on the MALE side (TIGHTER than the 0.8 tested loose fit)
HS_BSTOP_ENGAGE = 6.0               # engagement in the boss = 3 turns (the 2mm reclaimed from the piston head
                                    #   pulls this boss forward, so 6mm now fits at the SAME 1.44mm leg clearance)
HS_BSTOP_FLANGE = 0.5               # +X drive flange (drive slots on its face; thin so the total extent clears the leg)
HS_DRAG_LX, HS_DRAG_SEAT, HS_DRAG_BULGE = 6.0, 1.5, 0.4  # TPU drag: X length, wall-recess depth, interference into lane
HS_HOUS_BACK = HS_BACK_X + HS_BSTOP_ENGAGE   # housing boss depth = engagement (no extra -- preserves the leg clearance)

# ── MOUNT (user): the housing's TOP FACE is already FLUSH with the chassis underside
# (HOUS_Z1 = BODY_Z = Z_BOT), so the mount needs no yoke, no boss and no floating part —
# FUSED OCTAGON TENONS rise straight off that face into matching mortises in the chassis
# cross-ribs. (The old double-christmas-tree floating tenon + its yoke plate are gone: they
# existed because the housing used to print +Z→-Z and could not carry a protruding tenon.
# It prints -Z→+Z now, so the tenon is just part of the part.) ──
RIB_PITCH = 46.0                    # MOTOR pitch. The chassis rib comb is HALF this (23 mm: a
                                    # crossbar per motor plus one between each pair), and the
                                    # tenon stations are generated on that finer pitch — see
                                    # TEN_X down in the prism block, where the housing X extents
                                    # that bound them are finally known.
BODY_Z    = 5.0 + 2.4               # body underside in local Z: the lever's Ø10 hub top (z=5) + a 2.4mm AIR
                                    #   gap (no material between the lever and the body). Raising the axle
                                    #   is equivalent to lowering BODY_Z here; MOUNT_Z tracks it (= -82.55)
# ── OCTAGON slide-joint (cadkit): cadkit's octagon slides along its extrude axis, so we
# rotate it 90° about Z — the slide becomes +Y (the knee-DEPTH adjustment) and the roof
# stays +Z. Both halves print -Z->+Z (facing 'up') -> the octagon family -> self-supporting
# on BOTH sides. One joint SIZE, two LENGTHS: short TENONS on the housing (its own Y span)
# and a long RIB MORTISE (the whole knee-depth range).
_JW       = 6.0                   # octagon flat-to-flat width. Sized on the MECHANICS (knee-strike
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
MORT_CLR  = 0.3                     # mortise clearance (slide fit)
TEN_H     = _lever_joint(10.0).height   # how far a tenon rises above its mating face (5.82)
MORT_Y0   = -2.0                  # mortise -Y mouth (opens outboard of the -Y rail for slide-in)
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
MOUNT_X, MOUNT_Y, MOUNT_Z = -501.0, -148.75, -75.15 - BODY_Z
MOUNT_POSE = (MOUNT_X, MOUNT_Y, MOUNT_Z)
# the mortise (slot) runs from the player face ALL THE WAY to the guitar's Y midpoint -- the lever's
# nub slides +Y along it to the player's chosen knee depth, then the retention screw locks it.
MID_Y     = -37.0                   # guitar Y-midpoint (= chassis (Y_LO + Y_HI)/2)
MORT_Y1   = MID_Y - MOUNT_Y         # mortise +Y end at mid-Y (in the local frame)
# DEPTH LOCK — still DEFERRED (it lands with the sensor mount, which shares the same +Y
# region). Plan of record: an M2 SELF-TAPPING set screw threading UP through the housing
# top beside one tenon, its cup pressing the rib's side column so the Y slide friction-
# locks. It needs no drilled pilot in the rib (it bears on the printed surface), and the
# rib runs in Y, so the ledge is above the screw at EVERY depth setting. The octagon
# carries the knee-strike load; this only holds the chosen depth. (The old M4 version
# doesn't fit: the W=6 octagon leaves only a 2 mm rib side column.)


def _bearing():
    """MR85ZZ dummy (axis Y), -Y face at y=0."""
    o = cyl_y(BRG_OD, BRG_W, y0=0.0)
    b = cyl_y(BRG_ID, BRG_W + 0.2, y0=-0.1)
    return o.cut(b)


def demo_parts():
    """Bought-part dummies in the local frame: (name, shape). Assembly-only."""
    out = []
    # (no kl_axle dummy: the axle is PRINTED now — +Y journal integral to
    #  the lever, -Y journal = the kl_axle_insert part)
    for i, by in enumerate((-(BRG_Y0 + BRG_W), BRG_Y0)):    # inner faces at ±BRG_Y0,
        out.append((f"kl_bearing_{i}", _bearing().translate((0, by, 0))))  # enclosed in the cheeks
    out.append(("kl_magnet", cyl_y(MAG_D, MAG_T, y0=MAG_Y0)))
    out += sensor_parts(HOUS_Z0, HOUS_Z1)
    # BOTH springs are the SAME cartridge: MAIN (at MAIN_YC) whose follower touches the lobe at REST
    # (sets the rest angle), and HALF-STOP (at HS_YC, slid +X by HS_SETBACK) that engages partway. Each
    # has a coil, a back TENSION screw (preload), and a FROM-BELOW CLAMP screw that jams the cartridge
    # up against the pocket ceiling -- locking its slid X (= rest / engagement) and retaining the roof.
    for nm, dx, dy in (("main", 0.0, MAIN_YC - HS_YC), ("half_stop", HS_SETBACK, 0.0)):
        # every dummy is BUILT in the +Z/+X frame then feel_place()d to its installed spot (below the axle,
        # coil -X) -- same map as the cartridge, so they track AXLE_Z too.
        out.append((f"{nm}_spring", feel_place((cyl(HS_SPR_OD, HS_SPR_INST, z=HS_BODY_BX)   # Ø6 coil (tube:
                    .cut(cyl(HS_SPR_ID, HS_SPR_INST + 2, z=HS_BODY_BX - 1)))                #  pilots thru ID)
                    .rotate((0, 0, 0), (0, 1, 0), 90).translate((dx, HS_YC + dy, HS_Z)))))
        # CUP tip bears on the GUIDE-POST back (HS_GPOST_BX); driving it in compresses the coil (preload).
        out.append((f"{nm}_spring_tension_setscrew", feel_place(C.set_screw().rotate((0, 0, 0), (0, 1, 0), 90)
                    .translate((HS_GPOST_BX + M4_SCREW_L + dx, HS_YC + dy, HS_Z)))))
        out.append((f"{nm}_spring_tension_insert",                      # Ø6×5 insert, flush at the back wall
                    feel_place(_seated_insert((HS_BACK_X + dx, HS_YC + dy, HS_Z), (0, 1, 0), -90))))
        # HOLLOW back-stop screw: threads the housing boss, its -X face the adjustable stop the cartridge
        # back seats against (sets the X home). The tension screw above runs THROUGH its Ø5.5 bore.
        out.append((f"{nm}_cart_backstop", feel_place(cart_backstop.translate((dx, dy, 0)))))
        # passive TPU drag pad (outboard wall): built at HS outboard; the MAIN copy is it mirrored in Y.
        # BOTH pads sit at the RECESS X (dx = HS_SETBACK -- a fixed housing feature, same in both
        # slots); the cartridge slides over the pad wherever it parks. (The old dx=0 main pad hung
        # 1.86 out of its recess -- a latent misfit the prism-round probe caught.)
        _drag = cart_drag if dy == 0 else cart_drag.mirror("XZ")
        out.append((f"{nm}_cart_drag", feel_place(_drag.translate((HS_SETBACK, 0, 0)))))
    # (no travel-stop screw: the +Z-cam-era stop boss was removed -- see _housing)
    # (no retention set-screw dummy: the rib-mount tenons + their M2 lock are
    #  DEFERRED with the mount -- prism round; see _housing)
    return out


def sensor_board():
    """THE board — one design for every lever (user). Drawn once, in its own frame:
    chip on the axle axis, top edge CHIP_DROP above it. Levers pose it; none of them
    redraws it, which is what makes "identical" structural rather than a promise."""
    return box_at(PCB_WX, PCB_T, PCB_WZ, x=(PCB_X0 + PCB_X1) / 2,
                  y=PCB_Y + PCB_T / 2, z=(PCB_Z0 + PCB_Z1) / 2)


def sensor_connector():
    """The CAN drop as drawn on that board: S4B-XH-SM4-TB, MATED (a connector nobody
    can get a plug onto is not a fit, and for side entry the plug's reach is the
    whole question). Height +Z -> -Y so it stands off the magnet-facing face, mating
    axis +Y -> +X so the plug arrives from -X, length -> Z."""
    return (jst_xh_side_header(CONN_N, mated=True)
            .rotate((0, 0, 0), (1, 0, 0), 90)
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((CONN_MOUTH_X, PCB_Y, PCB_Z0 + CONN_RISE)))


def _install(s, z_bot, z_top):
    """Pose a board-frame solid into a housing: identity, or turned over."""
    return (s.rotate((0, 0, 0), (0, 1, 0), 180)
            if board_flip(z_bot, z_top) else s)


def sensor_parts(z_bot, z_top, prefix="kl"):
    """Board + MT6701 + mated connector, posed for this housing. The board and the
    connector come from sensor_board/sensor_connector unchanged and are only ROTATED,
    so there is exactly one board design in the project."""
    return [
        (f"{prefix}_pcb", _install(sensor_board(), z_bot, z_top)),
        (f"{prefix}_chip", box_at(CHIP_W, CHIP_H, CHIP_W,
                                  x=0.0, y=PCB_Y - CHIP_H / 2, z=0.0)),
        (f"{prefix}_can_header", _install(sensor_connector(), z_bot, z_top)),
    ]


def pcb_shim(z_bot, z_top):
    """PRINTED SHIM (user): the board is one size and the housings are not, so the
    slack between the board's top edge and the instrument is taken up by a plastic
    block that slides down the SAME grooves on top of it. The chassis then presses
    the shim, the shim presses the board, and the retention stays exactly what it
    was — no fastener, no second board design. Returns None where the board already
    reaches the ceiling (the horizontal lever), so the part only exists where it is
    needed."""
    gap = (z_top - CEIL_CLR) - board_z(z_bot, z_top)[1]
    if gap <= CR_CLR:
        return None
    bx0, bx1 = board_x(z_bot, z_top)
    return box_at(bx1 - bx0, PCB_T, gap - CR_CLR, x=(bx0 + bx1) / 2,
                  y=PCB_Y + PCB_T / 2,
                  z=board_z(z_bot, z_top)[1] + CR_CLR + (gap - CR_CLR) / 2)


def _cradle(w, z_bot=None, z_top=None, x_max=None):
    """Add the MT6701 board cradle to the housing (user). Everything here grows UP
    off the same bed as the housing and has no ceiling anywhere, so it needs no
    supports; see the constant block for the retention scheme and the socket cone.

    Built as: two side webs + a front plinth + a floor, then ONE slot cut through
    them for the board — that slot IS both grooves. Cutting it after the webs is
    what makes them: the web material outboard of the slot survives as each
    groove's outer wall."""
    z_bot = HOUS_Z0 if z_bot is None else z_bot
    z_top = HOUS_Z1 if z_top is None else z_top
    pcb_z0, pcb_z1 = board_z(z_bot, z_top)
    conn_zc = conn_z(z_bot, z_top)
    bx0, bx1 = board_x(z_bot, z_top)      # installed edges — the flip swaps them
    conn_mx = conn_mouth_x(z_bot, z_top)
    _sx = -1.0 if board_flip(z_bot, z_top) else 1.0
    x_max = CR_X1_MAX if x_max is None else x_max

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
    # the NEAR side is the one that risks reaching past the housing's own +X face
    _ni, _no = _near
    _no = min(_no, x_max) if _no > 0 else max(_no, -x_max)
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
    # ...and WHICH part of the board's height the +X side can hold is derived, not
    # fixed. The bore forbids printed material within SOCK_R of the axis, so the +X
    # carrier has to live either below -SOCK_R or above +SOCK_R; the right answer is
    # whichever of those two bands actually OVERLAPS THE BOARD. On this lever the
    # board hangs low and it is the lower band (a 5 mm groove at the bottom); on the
    # vertical lever the axle sits 19 lower, the board is entirely ABOVE the bore,
    # and the upper band is the only one that touches it — pinning this to the lower
    # band left that lever with NO +X retention at all, which the push probe caught.
    _lo = (z_bot, min(pcb_z1, CR_PLINTH_Z1))
    _hi = (max(z_bot, SOCK_R), z_top)
    _span = max(_lo, _hi, key=lambda r: max(0.0, min(r[1], pcb_z1) - max(r[0], pcb_z0)))
    for a, b, z0, z1 in ((_far[0], _far[1], z_bot, z_top), _near + _span):
        w = w.union(box_at(abs(b - a), CR_Y1 - CR_Y0, z1 - z0,
                           x=(a + b) / 2, y=(CR_Y0 + CR_Y1) / 2,
                           z=(z0 + z1) / 2))
        if z0 > z_bot + 1e-6:
            # This web does not start on the bed — it cantilevers off the housing's
            # +Y cheek — so its underside is a CR_Y1-CR_Y0 deep unsupported ledge.
            # Ramp it at 45° off the cheek instead. Costs the groove its lowest
            # (CR_Y1-CR_Y0) of engagement and nothing else, and the band it takes
            # is the far end from the board's seat anyway.
            _p = [(CR_Y0 - 1.0, z0 - 1.0), (CR_Y1 + 1.0, z0 - 1.0),
                  (CR_Y1 + 1.0, z0 + (CR_Y1 + 1.0) - (CR_Y0 - 1.0)), (CR_Y0 - 1.0, z0)]
            _f = cq.Face.makeFromWires(cq.Wire.makePolygon(
                [cq.Vector(min(a, b) - 1.0, y, z) for y, z in _p]
                + [cq.Vector(min(a, b) - 1.0, _p[0][0], _p[0][1])]))
            w = w.cut(cq.Workplane("XY").add(cq.Solid.extrudeLinear(
                _f, cq.Vector(abs(b - a) + 2.0, 0, 0))))
    # front plinth: the slab the board's -Y face seats on, and the body the screw
    # boss lives in. Its top IS the socket cone's floor.
    w = w.union(box_at(outer1 - outer0, CR_SLOT_Y0 - CR_Y0, CR_PLINTH_Z1 - z_bot,
                       x=(outer0 + outer1) / 2, y=(CR_Y0 + CR_SLOT_Y0) / 2,
                       z=(z_bot + CR_PLINTH_Z1) / 2))
    # floor under the board + the tie between the two webs behind it
    w = w.union(box_at(outer1 - outer0, CR_Y1 - CR_SLOT_Y0, pcb_z0 - z_bot,
                       x=(outer0 + outer1) / 2, y=(CR_SLOT_Y0 + CR_Y1) / 2,
                       z=(z_bot + pcb_z0) / 2))
    # THE BOARD SLOT (both grooves in one cut): open at +Z — the install axis —
    # and bottoming on the floor at pcb_z0, which is the board's -Z seat.
    w = w.cut(box_at(slot1 - slot0, CR_SLOT_Y1 - CR_SLOT_Y0, (z_top + 2.0) - pcb_z0,
                     x=(slot0 + slot1) / 2, y=(CR_SLOT_Y0 + CR_SLOT_Y1) / 2,
                     z=(pcb_z0 + z_top + 2.0) / 2))
    # ── ROOM FOR THE CONNECTOR, which lives on the board's MAGNET-facing face.
    # Two cuts, both through material that is ours — the cradle's own plinth and
    # web, and 0.85 of the housing's +Y cheek. The cheek can afford it: it is 3.50
    # thick (lever-room wall at BRG_Y0, outer face at HOUS_HW), this leaves 2.65,
    # and the LEVER never comes past y=10.00 at any angle in its whole -95°..+34°
    # range — 3.35 short of the deepest point of this relief. Nothing that moves
    # is anywhere near it.
    # ONE relief, doing two jobs, and open out the TOP so it has no ceiling:
    #   * a DESCENT CHANNEL for the connector — not merely a pocket at its rest
    #     position, since the board is lowered in and the body needs the relief all
    #     the way up. That is also why the cut runs past z_top rather than stopping
    #     at the connector: a lid over it would be a 45 mm² flat overhang.
    #   * a PLUG RUN-IN through the -X web, which is what stood in the plug's way.
    # The web keeps its groove and its +Y back flank — both live outboard of PCB_Y,
    # so this cut never reaches them. What it gives up is the seat face on that side
    # above _cz0; the board's -X edge is then seated by the plinth below and by the
    # +X groove, which is enough for a rigid board.
    _cy0 = PCB_Y - XH_SIDE_H - CONN_POCKET          # 13.05: relief floor
    _cz0 = conn_zc - xh_side_length(CONN_N) / 2 - CONN_POCKET       # -8.3
    # -X end: far enough for the plug to come fully OFF, not merely to sit there.
    # It needs its own length of straight travel before it clears the header, and
    # for that whole stroke its inboard face is still inside the cheek's outer
    # 0.85 — probed, and it was a real foul until this reached out here.
    _cx0 = conn_mx - _sx * (2 * CONN_PLUG_RUN + 3.0)   # the plug's unplug stroke
    _cx1 = conn_mx + _sx * (XH_SIDE_D + CONN_POCKET)
    # +Z end: clear THROUGH the mount tenons, not just up to the cradle top. The
    # x=-23 tenon is a Y-rail that runs out to HOUS_HW, so it stands in this
    # relief's path; stopping the cut at z_top left a 2.9 mm² flat ceiling notched
    # into it. Running past TEN_H instead trims 0.85 off that tenon's +Y end — 3%
    # of a 27.8 rail, and it exits cleanly.
    _cz1 = z_top + TEN_H + 1.0
    w = w.cut(box_at(abs(_cx1 - _cx0), PCB_Y - _cy0, _cz1 - _cz0,
                     x=(_cx0 + _cx1) / 2, y=(_cy0 + PCB_Y) / 2,
                     z=(_cz0 + _cz1) / 2))
    # SOCKET CONE — reserved so kl_magnet_cap can be driven with the cradle in
    # place. Cut rather than merely avoided: it is a guarantee, not an intention,
    # and anything a later round adds in this zone now gets removed instead of
    # silently blocking the driver. Teardrop, like every sideways bore here.
    # It starts at MAG_Y0, NOT at the housing face: the socket only ever has to
    # reach the cap's rim, and running it inboard of that would bore Ø14 straight
    # through the two features that live there — the axle flange's CONTACT RIB
    # (the air gap's whole datum) and the +Y bearing seat's 0.7 outboard skin
    # (what stops the bearing walking out). Both are well inside Ø14.
    w = w.cut(printable_bore(SOCK_D, (CR_Y1 + 1.0) - MAG_Y0, (0.0, MAG_Y0, 0.0),
                             (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    return w


def _top_tenon(tx):
    """ONE fused octagon tenon at station tx: cadkit's octagon (slides +X, roof +Z) rotated
    90° about Z so it slides +Y, mating plane at the housing TOP face (which is the chassis
    underside), roof rising +Z into the rib above and the root reaching TEN_ROOT down into
    the prism for a volumetric fuse."""
    return (_lever_joint(TEN_Y1 - TEN_Y0).tenon(root=TEN_ROOT)
            .rotate((0, 0, 0), (0, 0, 1), 90)                 # slide axis X -> Y (roof stays +Z)
            .translate((tx, TEN_Y0, HOUS_Z1)))                # station X, -Y start, mate at the top face


def rib_mortise(rib_x):
    """ONE octagon MORTISE (GLOBAL) for the rib at rib_x: the same cadkit octagon as the tenon
    but LONG in Y (MORT_Y0..MORT_Y1 = the knee-depth slide range), rotated to slide +Y. Opens at
    the rib bottom (-Z, the mating plane = Z_BOT) and its roof bridges inside the rib. chassis.py
    cuts this into every rib so a lever can mount in ANY bay."""
    m = (_lever_joint(MORT_Y1 - MORT_Y0).mortise(drop=2.0)
         .rotate((0, 0, 0), (0, 0, 1), 90)                     # slide axis X -> Y
         .translate((0.0, MORT_Y0, BODY_Z)))                   # centred x=0, -Y mouth, mate at rib bottom
    return m.translate((rib_x, MOUNT_Y, MOUNT_Z))


# (retention now PRESSES the rib ledge -- no drilled pilot in the rib, so no per-bay chassis feature)


def _guide_post() -> cq.Workplane:
    """Loose captive guide post (printed): a Ø6 SHOULDER that seats the coil BACK and rides the channel,
    with a Ø3.2 PILOT nosing -X into the coil ID. The Ø4 tension-screw cup bears on its +X face -- it only
    ever pushes, and is trapped between cup, coil and roof once assembled (see knee-lever-feel-spring)."""
    shoulder = cyl(HS_SPR_OD, HS_GPOST_LX, z=HS_SPR_TIPX)                  # Ø6: coil back -> cup face
    pilot = cyl(HS_PILOT_D, HS_PILOT_LX, z=HS_SPR_TIPX - HS_PILOT_LX)      # Ø3.2: -X into the coil ID
    return heal(shoulder.union(pilot).rotate((0, 0, 0), (0, 1, 0), 90).translate((0, HS_YC, HS_Z)))


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
#   -X  the CARTRIDGE back + the back-stop screw's thread engagement
#   ±Y  the outermost cartridge face + slide clearance + one housing wall
#   +Z  the instrument BODY underside, FLUSH (user round 4: the slab
#       beside the lever fills the whole lever-top→body zone — 2.4 of
#       MATERIAL, no air gap; was 2.1 + 0.3 air)
#   -Z  the cartridge bottom (piston underside) + slide clearance + one wall
# Globals (MOUNT_POSE + these): x -578.26..-496.00, y -162.65..-134.85,
# z -97.35..-75.15 (top now flush with the chassis underside Z_BOT).
HOUS_X1 = ARM_TX / 2                                     # +5.0
HOUS_X0 = -(HS_HOUS_BACK + HS_SETBACK)                   # -77.26
HOUS_HW = abs(HS_YC) + HS_CART_WY / 2 + HS_CLR + HS_HOUS_WALL   # 13.9
HOUS_Z1 = BODY_Z                                         # +7.4 (flush: BODY_Z
#           = HUB_TOP + 2.4 — the designed 2.4 stands between lever and body)
HOUS_Z0 = (HS_Z - HS_PISTON_WZ / 2) + _FEEL_DZ - HS_CLR - HS_HOUS_WALL  # -14.8
#           ^ = HS_FLOOR_Z (defined below, after the piston) placed
BRG_Y0 = LEVER_HW + HS_CLR          # bearing INNER faces at ±10.4 = the lever-room wall
                                    # (user: the old wall-station bearings poked along Y —
                                    # moved against the lever so both sit FULLY inside the
                                    # ±13.9 cheeks: span 10.4..12.9, 1.0 outboard skin;
                                    # 0.4 gap to the ±10 hub ends. Seats = axle round.)
# ── MOUNT TENON STATIONS (user: "4 sets"). The chassis rib comb is a uniform
# RIB_PITCH/2 = 23 mm and the lever is posed ON a rib (MOUNT_X = -501 IS a rib X), so
# the stations are just k·23 walking -X from the axle, kept while the whole 6-wide
# octagon still lands on the top face: 0, -23, -46, -69 — four, and the count falls
# out of the geometry rather than being written down (widen or shift the housing and
# the comb re-solves). Generated here rather than in the mount block because it is
# HOUS_X0/X1 that bound them, and those aren't known until this point.
_TEN_PITCH = RIB_PITCH / 2.0        # = the chassis half-pitch rib comb
TEN_X = tuple(-k * _TEN_PITCH for k in range(20)
              if HOUS_X0 + _JHW <= -k * _TEN_PITCH <= HOUS_X1 - _JHW)
# Each tenon runs the housing's FULL Y depth: it is a rail, and every millimetre of it
# is engagement the player can buy by sliding the lever inboard. The +X-most station
# (x=0) sits directly over the lever, where the lever-room slot opens the top face —
# so all that survives of it is a stub on top of each ±Y cheek wall. That is by
# construction, not by special-casing: the tenons are unioned BEFORE the lever-room
# cut, so the same sweep that clears the lever trims the tenon.
TEN_Y0, TEN_Y1 = -HOUS_HW, HOUS_HW
TEN_ROOT = 1.0                      # root below the mating face — volumetric fuse into the
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
RIB_T = RIB_PROUD = 0.85            # cadkit house contact-rib section
AXLE_SHOULDER_Y = HOUS_HW + RIB_PROUD           # 14.75: flange face, ON the rib
AXLE_FLANGE_D   = 9.0               # flange Ø (what seats on the rib). NOT the thread
                                    # major any more — the hex cap forced those apart
MAG_FLANGE_T    = 0.8                           # pocket floor under the magnet
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
CAP_APERTURE = 5.0                  # open on the axis so the cap never intrudes on the
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
AXLE_BORE_D = AXLE_D + 0.2                      # lever's through D-bore (glue fit)
PCB_Y   = MAG_Y1 + AIR_GAP + CHIP_H             # board face = magnet + gap + PACKAGE
AXLE_Y0, AXLE_Y1 = -13.1, MAG_Y1                # axle: -Y journal tip (stops INSIDE its
                                                # bearing pocket, back wall -13.2) .. the
                                                # magnet face at the +Y end

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
CR_BACK  = 1.5                      # web material BEHIND the groove (the +Y flank)
# The board is DELIBERATELY ASYMMETRIC about the chip. Both edges are pushed out by
# the socket cone (a groove wall may not come inside SOCK_R, so an edge may not come
# inside SOCK_R + CR_ENG - CR_CLR = 8.70), and the -X edge is pushed out FURTHER by
# the M4, which needs 1.4 of FR4 around its Ø4.4 hole. Since the chip's X is fixed at
# the axle axis and the outline is ours, paying for the screw on one side only is
# free — and it keeps the +X web from reaching much past the housing's knee face.
PCB_X1  =  3.0                                  # +X edge: as close to the CHIP as the board
                                                # house allows (user: pull the lever's +X extent
                                                # in). The QFN body ends at 1.5, so this leaves
                                                # 1.5 of edge keepout — comfortably over
                                                # JLCPCB's 1.0 component-to-edge rule, on a
                                                # board that panelises with the tee PCBs anyway.
                                                # This used to be 8.70, set by the driver bore:
                                                # a groove wall may not come inside SOCK_R. That
                                                # no longer binds because the +X groove carrier
                                                # is now confined BELOW the bore (see CR_X1_MAX
                                                # and _cradle) instead of running full height.
PCB_X0  = -14.0                                 # -X edge: CONNECTOR-limited, and by a lot. The
                                                # connector now lives on the MAGNET side and has
                                                # to sit entirely outside the cap's sweep, so the
                                                # board has to reach far enough -X to carry it
                                                # there and still have 1.85 of edge left for the
                                                # groove. Asymmetry is free: the outline is ours
                                                # and only the chip's position is fixed.
PCB_WX  = PCB_X1 - PCB_X0                       # 23.0
CEIL_CLR = 0.4                      # board top edge -> the instrument's underside. THE
                                    # INSTRUMENT IS THE BOARD'S +Z RETAINER (user), which is
                                    # why there is no retaining screw: the board goes in with
                                    # the lever OFF the guitar, and the chassis becomes its
                                    # lid the moment the lever slides into the ribs. 0.4 is
                                    # the slide clearance plus the board's own height
                                    # tolerance. The board still RESTS on the cradle floor, so
                                    # this is a LIFT STOP, not a datum — it costs the chip's
                                    # position nothing. PROBED against the built chassis at
                                    # the board's own Y: the ceiling is real over x -9..-1.8
                                    # and 1.8..9.0, the gap being only the rib's own mortise
                                    # slot, which the rigid board simply bridges.
CR_FLOOR_T = 2.8                    # cradle floor under the board
CONN_RISE  = 11.5                   # connector row above the board's bottom edge
CHIP_DROP  = 7.0                    # chip below the board's TOP edge

# THE BOARD IS ONE DESIGN, FIXED (user: "the boards should be fully identical").
# It is not derived from the housing any more: the chip has to sit on the axle axis,
# the outline hangs off the chip, so the board's Z span is a property of the BOARD.
# What varies between levers is which way up it goes in.
PCB_Z1 = CHIP_DROP                              # +7.0
PCB_Z0 = PCB_Z1 - PCB_WZ                        # -12.0


def board_flip(z_bot, z_top):
    """Which way up the board goes in a housing spanning z_bot..z_top.

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
    if as_drawn:
        return False
    if flipped:
        return True
    raise ValueError(
        f"the {PCB_WZ:.1f} board fits a housing spanning {z_bot:.2f}..{z_top:.2f} "
        "neither way up — move the housing's floor or its ceiling, not the board")


def board_z(z_bot, z_top):
    """(bottom, top) of the board as INSTALLED in this housing."""
    return (-PCB_Z1, -PCB_Z0) if board_flip(z_bot, z_top) else (PCB_Z0, PCB_Z1)


def board_x(z_bot, z_top):
    """(-X, +X) edges as INSTALLED — turning the board over swaps them too."""
    return (-PCB_X1, -PCB_X0) if board_flip(z_bot, z_top) else (PCB_X0, PCB_X1)


def conn_z(z_bot, z_top):
    """Connector row Z as installed: a fixed rise off the board's own bottom edge,
    carried through the flip with it."""
    f = board_flip(z_bot, z_top)
    return -(PCB_Z0 + CONN_RISE) if f else PCB_Z0 + CONN_RISE


def conn_mouth_x(z_bot, z_top):
    return -CONN_MOUTH_X if board_flip(z_bot, z_top) else CONN_MOUTH_X


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
# It goes on the +Y face (the magnet side is spoken for) and DOWN LOW, and the
# driver bore is why: a connector inside SOCK_R would block the socket, and the
# board is installed last precisely so it doesn't. Its Ø0.64 post TAILS matter
# more than the body here — they protrude 3.4 back out of the board's SEATING
# face, so they have to miss both the driver bore and the plinth.
CONN_N     = 4
# THE CONNECTOR IS ON THE MAGNET SIDE (user), so that the QFN and it share ONE face
# and the board is a single-sided SMT job — that is the entire point, and it is worth
# the geometry below because double-sided assembly is a per-order setup fee.
# It has to be the SIDE-ENTRY SMT part, S4B-XH-SM4-TB, for two independent reasons:
#   * SMT — a through-hole header's posts would stand 1.8 proud of this face, which is
#     the face that seats, and would sweep the magnet cap on the way in.
#   * SIDE entry — a top-entry plug would have to be inserted from -Y, i.e. from
#     inside the housing. Mating parallel to the board turns that into a horizontal
#     run-in, which is a cut we can make.
# X POSITION is forced. The board installs by dropping straight down past the cap, so
# anything on this face deeper than the 1.5 between the board and the cap's outer
# face must keep its WHOLE footprint outside the cap's 5.4 circumradius + clearance.
# The body is XH_SIDE_D deep, so the mouth goes at -11.9 and the body runs +X to -5.8
# — 0.4 clear of the cap for the entire stroke, not just at rest.
CONN_MOUTH_X = -11.9                # mouth face; body extends +X from here
CONN_ZC      = conn_z(HOUS_Z0, HOUS_Z1)   # -0.5 here. A fixed RISE off the board's
                                    # bottom edge rather than an absolute Z, so the same
                                    # rule lands it on the vertical lever too (conn_z).
                                    # Was: length centre -> the body spans z -8.0..+7.0, i.e.
                                    # topped out flush with the board. HIGH on purpose: the
                                    # plug's run-in tunnel has to be cut through the -X web
                                    # and the plinth, and putting the connector high keeps
                                    # that tunnel above the plinth, which survives whole
                                    # below -8.5 and goes on carrying the board's seat.
CONN_POCKET  = 0.3                  # clearance around it in the housing/cradle relief
CONN_PLUG_RUN = 7.5                 # how far the mated XHP-4 reaches past the mouth. Taken
                                    # as the housing's own height with NO credit for shroud
                                    # engagement — JST doesn't publish a mated projection for
                                    # side entry, and over-reserving is the safe error here
                                    # because the relief it buys is 0.85 of a 3.50 cheek.
CR_PLINTH_Z1 = -SOCK_R              # -7.0: front plinth top = the driver bore's floor
# (the swept-arm relief _cam_swept — a union of rotated hub/arm copies — is
#  PULLED for now (user: no curved geometry around the axle; keep it simple,
#  build back up later). The lever room is all planar cuts in _housing.)


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
    c = HS_CLR
    zc = _FEEL_DZ + HS_Z + FOLL_DZ                       # follower centre, placed frame
    x_hi, x_lo = 0.0, -13.0                              # lobe centre .. back into open air (past -X face)
    tongue = box_at(x_hi - x_lo, LOBE_WY + 1.0, FOLL_H + 2 * c,
                    x=(x_hi + x_lo) / 2, y=yc, z=zc)
    def at(deg):
        s = LOBE_RC * math.sin(math.radians(deg)) if deg > 0 else 0.0
        return tongue.translate((-s, 0, 0)).rotate((0, 0, 0), (0, 1, 0), -deg)
    degs = list(range(0, int(round(THROW)) + 1, int(step))) + \
           [-d for d in range(int(step), int(fold) + 1, int(step))]
    env = None
    for d in degs:
        env = at(d) if env is None else env.union(at(d))
    return heal(env)


_RECESS_SWEPT = _recess_swept(MAIN_YC)               # one band, built once; translated in Y for the other


def _half_stop_piston() -> cq.Workplane:
    """The piston (printed): a square BODY (Ø6 footprint) that slides in the channel and seats the coil
    FRONT on its +X face, a centre PILOT boss that noses +X into the coil ID to keep it aligned, and a
    SHORT follower TONGUE at the lobe band that protrudes -X, ending in a HALF-CYLINDER nose (round in
    X-Z, square across Y) for clean rolling cam contact. The body is wider than the front-lip window, so
    the preloaded coil can't eject it."""
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
    pilot = (cyl(HS_PILOT_D, HS_PILOT_LX, z=HS_BODY_BX)                    # +X boss centring the coil ID
             .rotate((0, 0, 0), (0, 1, 0), 90).translate((0, HS_YC, HS_Z)))
    return heal(body.union(foll).union(pilot))


HS_FLOOR_Z = HS_Z - HS_PISTON_WZ / 2               # piston underside = cartridge OPEN-bottom = housing floor


def _roof_gable(yc, hw, z_base, x0, x1):
    r"""A triangular GABLE prism (roof): base yc±hw at z_base, apex at (yc, z_base+hw) with
    45deg faces, extruded along X from x0 to x1. Unioned on top of a flat-topped cartridge/
    pocket so the roof over the cartridge is a self-supporting /\ (each face 45deg) instead of
    a flat -Z->+Z print overhang. It sits ABOVE the cap top (z_base >= HS_CART_Z1), well clear
    of the piston (top HS_Z+HS_PISTON_WZ/2), so no running clearance changes -- it just replaces
    the flat lid with a peak. The two cartridges' peaks (at ±HS_YC) leave a solid ridge between
    them; below the eaves each pocket is the usual vertical-walled box."""
    pts = [(yc - hw, z_base), (yc + hw, z_base), (yc, z_base + hw)]
    wire = cq.Wire.makePolygon([cq.Vector(x0, y, z) for (y, z) in pts] + [cq.Vector(x0, *pts[0])])
    face = cq.Face.makeFromWires(wire)
    return cq.Workplane("XY").add(cq.Solid.extrudeLinear(face, cq.Vector(x1 - x0, 0, 0)))


def _half_stop_cart_base() -> cq.Workplane:
    """Cartridge (printed -- ONE part, NO separate roof): an INVERTED-U. A solid +Z CAP (toward the axle,
    where the swinging arm's arc is narrow) + two side walls + front/back walls, OPEN on -Z. The piston
    drops in; the HOUSING FLOOR below is the final -Z retaining wall. This keeps cartridge material -Z of
    the piston at an absolute minimum (only the housing is there, and it's relieved to open air at the
    front where the arm sweeps). The channel is cut UP from the open bottom to the cap underside."""
    ch_top = HS_Z + HS_CH_WZ / 2                                           # channel ceiling = cap underside
    base = box_at(HS_BACK_X - HS_FRONT, HS_CART_WY, HS_CART_Z1 - HS_FLOOR_Z,
                  x=(HS_FRONT + HS_BACK_X) / 2, y=HS_YC, z=(HS_FLOOR_Z + HS_CART_Z1) / 2)
    # ONE wide channel, OPEN on -Z: cut from below the part up to the cap underside (Ø6 piston/coil/guide
    # post ride it; the housing floor closes it from -Z)
    base = base.cut(box_at(HS_GPOST_BX - HS_BODY_X0, HS_CH_WY, ch_top - (HS_FLOOR_Z - 5),
                           x=(HS_BODY_X0 + HS_GPOST_BX) / 2, y=HS_YC, z=(ch_top + (HS_FLOOR_Z - 5)) / 2))
    # front tongue window (at the lobe band): passes the follower tongue; the front wall still catches the
    # Ø6 body in Y (window < body). The tongue rides up through it as the lobe rises over the throw
    base = base.cut(box_at(HS_BODY_X0 - HS_FRONT + 0.1, HS_WIN_WY, FOLL_H + 1.0,
                           x=(HS_FRONT + HS_BODY_X0) / 2, y=HS_YC, z=HS_Z + FOLL_DZ))
    # rear M4 insert_bore (tension SET SCREW, opens +X): Ø6×5 melt pocket + Ø4.4 shaft clearance running -X
    # to the guide-post cup face. The screw threads the insert and its cup pushes the guide post -> coil
    # preload; the shaft-clearance beyond the pocket is the sanctioned insert-bore deviation (set screws
    # must never self-tap -- they hold load), reason recorded in-line.
    base = cut_insert_bore(M4, base, (HS_BACK_X, HS_YC, HS_Z), (-1, 0, 0),
                           clr_len=HS_BACK_X - HS_GPOST_BX - M4_INSERT_L,
                           reason="tension set screw: cup drives the guide post through the shaft clearance")
    # 45deg gable cap: replace the flat lid with a peaked roof so the housing pocket cut from it is
    # self-supporting (no flat overhang) in the -Z->+Z print. Above the cap top, clear of the coil/piston.
    base = base.union(_roof_gable(HS_YC, HS_CART_WY / 2, HS_CART_Z1, HS_FRONT, HS_BACK_X))
    return heal(base)


def _cart_backstop() -> cq.Workplane:
    """HOLLOW back-stop screw (printed PCTG, one per cartridge -- print 2). A self-supporting 45deg MALE
    thread screws into the housing boss; its -X face is the adjustable stop the cartridge back seats against,
    setting the cartridge's X home. HOLLOW (Ø HS_BSTOP_BORE) so the coaxial M4 tension screw reaches the
    cartridge insert through it -- preload (inner) and position (this) stay independent. Turned by drive
    slots on the +X flange face; the contact force keeps it compression-seated so it holds without backing
    out. The thread carries HS_TH_CLR of clearance (tighter than the 0.8 tested loose fit). SHORT screw ->
    print AXIS-VERTICAL (no side-print needed); the 45deg flanks self-support. Threads cut LAST, un-healed
    (thread rules). Built along X at the cartridge back, HS_YC (feel_place()d into the assembly)."""
    from cadkit.threads import cut_thread
    maj, mnr = HS_BSTOP_OD - HS_TH_CLR, HS_TH_MINOR - HS_TH_CLR                 # male shrunk by the clearance
    fl_od = min(HS_BSTOP_OD + 2.0, 2 * abs(HS_YC) - 1.5)                        # flange < cartridge pitch (no centre clash)
    blank = (cyl(maj, HS_BSTOP_ENGAGE, z=HS_BACK_X)                             # SMOOTH crest-Ø body...
             .union(cyl(fl_od, HS_BSTOP_FLANGE, z=HS_BACK_X + HS_BSTOP_ENGAGE)) # ...+ drive flange...
             .cut(cyl(HS_BSTOP_BORE, HS_BSTOP_ENGAGE + HS_BSTOP_FLANGE + 2, z=HS_BACK_X - 1)))  # ...hollowed
    male = cut_thread(blank, minor_d=mnr, major_d=maj, pitch=HS_TH_PITCH, length=HS_BSTOP_ENGAGE, z=HS_BACK_X)
    return male.rotate((0, 0, 0), (0, 1, 0), 90).translate((0, HS_YC, HS_Z))    # NO heal on a threaded part


def _drag_seat_xc(dx=0.0):
    return (HS_BODY_BX + HS_GPOST_BX) / 2 + dx         # coil-bay X (solid floor, behind the swept relief)


def _cart_drag() -> cq.Workplane:
    """Passive TPU DRAG pad (printed TPU, print 2). Seats in the housing pocket OUTBOARD-wall recess and
    bulges HS_DRAG_BULGE into the cartridge lane, so a few N of slide friction keeps the cartridge from
    drifting in X during transport (the back-stop only holds the loaded direction; this never holds the
    ~100N in-use load). Built at the HS cartridge's OUTBOARD (+Y) wall over the solid coil bay; the MAIN
    copy is this mirrored in Y."""
    y_tip  = HS_YC + HS_CART_WY / 2 - HS_DRAG_BULGE     # bulges past the cartridge outboard face into the lane
    y_back = HS_YC + hs_pocket_hw() + HS_DRAG_SEAT      # recess back (into the wall)
    pad = box_at(HS_DRAG_LX, y_back - y_tip, HS_PISTON_WZ, x=_drag_seat_xc(), y=(y_tip + y_back) / 2, z=HS_Z)
    return heal(pad)


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


def _hs_clamp_pt(yc, dx):
    r"""Point under the cartridge's INBOARD SIDE WALL (toward the centre gap), in the coil-bay X (back of the
    swinging arm's reach, clear of the open channel AND the rear tension insert), where a VERTICAL clamp
    screw presses UP from below -- jamming the cartridge cap against the pocket ceiling to lock the slid X."""
    wall_off = HS_CH_WY / 2 + HS_WALL / 2                       # side-wall centre offset from yc
    inboard = yc - (1 if yc > 0 else -1) * wall_off            # the wall facing the centre gap
    return ((HS_BODY_BX + HS_GPOST_BX) / 2 + dx, inboard, HS_FLOOR_Z)


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


def _housing() -> cq.Workplane:
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
        forward on its back-stop screw. Their overlapping inner walls
        merge into one void (no unprintable centre sliver).
      * the TPU drag-pad recesses in the outboard pocket walls.
      * the two female BACK-STOP THREADS in the solid behind the pockets
        (cut last, alone, un-healed — thread rules).
    SENSOR CRADLE (user, see _cradle): two webs + a plinth + a floor off the
    +Y face holding the MT6701 board — retained on five faces by shape, and
    on the sixth by the INSTRUMENT once the lever slides in, so there is no
    retaining screw. A Ø14 driver bore is RESERVED about the axle axis so
    kl_magnet_cap can still be socketed with all this printed.
    DEFERRED: the M2 depth LOCK.
    NOTE — the tenons engage NOTHING at the modelled pose: MOUNT_Y puts the
    housing's +Y face at -134.85 and the chassis rails start at -133.75, so
    the whole housing hangs 1.1 mm OUTBOARD of the rib comb. That pose is the
    fully-slid-OUT limit; engagement = slide - 1.1. See the note in the mount
    block — moving MOUNT_Y +Y is the fix, and it is the user's call.
    Prints -Z→+Z (the tenons are the octagon family, self-supporting)."""
    w = box_at(HOUS_X1 - HOUS_X0, 2 * HOUS_HW, HOUS_Z1 - HOUS_Z0,
               x=(HOUS_X0 + HOUS_X1) / 2, y=0.0, z=(HOUS_Z0 + HOUS_Z1) / 2)
    # MOUNT TENONS (user), unioned onto the raw prism BEFORE anything is cut — that
    # ordering is what makes the +X-most station come out "minimal" on its own: the
    # lever-room sweep below runs the full tenon height now, so it takes that tenon's
    # middle with it and leaves only the two cheek-wall stubs.
    for _tx in TEN_X:
        w = w.union(_top_tenon(_tx))
    # LEVER ROOM = ONE PLANAR SWEEP CUT (user round 3: 'solid everywhere
    # except the house cut and a sweep cut for the lever range of motion' —
    # the old full-width swing slot notched the front cheeks and the full-
    # height hub band slotted the top face; both are gone, the followers'
    # path lives inside the through house channels now). The cut is the
    # planar envelope of the lever swept 0..THROW, lever Y-span only:
    #   x +5.4 vertical  = the rest arm's +X face + clearance (the prism
    #                      face at +5.0 is inside it, so the whole +X
    #                      half-space stays open — the storage fold at +X
    #                      swings into air)
    #   OPEN OUT THE TOP = user round 4: the flat ceiling directly above
    #                      the lever was a 10.8-wide print overhang — cut;
    #                      the band exits the top face as a slot
    #   30° slant        = the full-throw arm's -X face + clearance
    _hw = LEVER_HW + HS_CLR
    _e = ARM_TX / 2 + HS_CLR                          # 5.4: lever half-depth + clr
    _zb = HOUS_Z0 - 1.0
    _slant = lambda z: math.tan(_THR) * z - (_e + ARM_TX / 2 * (1 / math.cos(_THR) - 1) + 0.4)
    # -X boundary: x = tan(30°)·z − c, the rotated arm face + clearance;
    # it crosses the hub band's -5.4 at z ≈ 1.5, so the polygon walks
    # hub-top → hub-side → slant → bottom → rest-side
    _zc = (-_e + (_e + ARM_TX / 2 * (1 / math.cos(_THR) - 1) + 0.4)) / math.tan(_THR)
    _zt = HOUS_Z1 + TEN_H + 1.0                       # ABOVE the tenons, so the sweep
    _p = [(_e, _zt), (-_e, _zt), (-_e, _zc),          #   trims the x=0 station too
          (_slant(_zb), _zb), (_e, _zb)]
    _face = cq.Face.makeFromWires(cq.Wire.makePolygon(
        [cq.Vector(x, -_hw, z) for x, z in _p] + [cq.Vector(_p[0][0], -_hw, _p[0][1])]))
    w = w.cut(cq.Workplane("XY").add(
        cq.Solid.extrudeLinear(_face, cq.Vector(0, 2 * _hw, 0))))
    # BEARING SEATS (user): Ø8.1 pockets for the MR85ZZ pair, opening
    # INBOARD at the lever-room walls (±BRG_Y0) and reaching 2.8 into the
    # cheeks (0.3 axial float over the 2.5 bearing — the proven old wall
    # numbers) → 0.7 of outboard skin stays; bearings press in from the
    # lever room. The +Y seat adds a Ø6 axle through-bore out the face
    # (the axle continues to the magnet/sensor cluster); the -Y axle end
    # stops INSIDE its pocket (AXLE_Y0 -13.1). Horizontal round bores in
    # the -Z→+Z print — teardrop/roundness refinement rides the axle round.
    # BEARING SEATS, also through cadkit (user). These run sideways in the
    # -Z->+Z print exactly like the axle way, and a drooping ceiling here is
    # worse than anywhere else: the droop is what takes the seat OUT OF ROUND,
    # which is the one property a press fit needs. The teardrop keeps the bore
    # round where the bearing actually seats and sends the overhang into an
    # attic above it. The load helps — the lever's weight presses the axle DOWN
    # onto round metal, so the opened top carries nothing.
    for by in (BRG_Y0, -(BRG_Y0 + BRG_W + 0.3)):
        w = w.cut(printable_bore(BRG_OD + 0.1, BRG_W + 0.3, (0.0, by, 0.0),
                                 (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    # CONTACT RIB on the outer face: the axle's flange seats here, so this ring
    # IS the air gap's datum. Narrow on purpose — the flange turns against it,
    # and a ring costs a fraction of a full annulus's friction.
    # UNIONED BEFORE THE BORE, and the order is the whole point: cadkit builds
    # the ring ROUND, so adding it after the bore laid a round aperture right
    # across the teardrop's peak and undid it (user spotted the round hole).
    # Cutting the bore through the rib afterwards opens its top too.
    w = w.union(contact_rib(AXLE_FLANGE_D - 1.5, RIB_PROUD, RIB_T,
                            (0.0, HOUS_HW, 0.0), (0.0, 1.0, 0.0),
                            (0.0, 0.0, 1.0)))
    # axle way out through the +Y cheek AND the rib. TEARDROP — cadkit picks
    # that itself from print_up: this bore runs SIDEWAYS in the -Z->+Z print,
    # so a round ceiling would droop into it and take it out of round.
    _bore_y0 = BRG_Y0 + BRG_W + 0.2
    w = w.cut(printable_bore(AXLE_D + 1.0, (HOUS_HW + RIB_PROUD) - _bore_y0,
                             (0.0, _bore_y0, 0.0),
                             (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), overshoot=0.6))
    # cartridge house-pockets + drag recesses. The house profile runs ALL
    # THE WAY OUT the +X face (user: extend to the prism edge, toward +x) —
    # one clean house channel from the front face to the cartridge back;
    # the 6mm threaded back-stop boss behind it stays solid. (Build frame
    # is mirrored: placed +X face = build -HOUS_X1; 1.0 overshoot.)
    for dy in (MAIN_YC - HS_YC, 0.0):
        dx = HS_SETBACK
        yc = HS_YC + dy
        w = w.cut(feel_place(_hs_pocket(yc, -HOUS_X1 - 1.0, HS_BACK_X + dx)))
        _sgn = 1.0 if yc > 0 else -1.0
        _yw = yc + _sgn * hs_pocket_hw()                          # pocket wall inner face
        _ys = yc + _sgn * (hs_pocket_hw() + HS_DRAG_SEAT)         # recess back (into the wall)
        w = w.cut(feel_place(box_at(HS_DRAG_LX + 0.4, abs(_ys - _yw), HS_PISTON_WZ + 0.4,
                                    x=_drag_seat_xc(dx), y=(_yw + _ys) / 2, z=HS_Z)))
    w = _cradle(w)                                                  # the MT6701 board cradle (user)
    w = heal(w)                                                     # heal EVERYTHING except the threads...
    # ...then cut the two FEMALE back-stop threads LAST and ALONE (thread rules: clean=False, and NEVER
    # heal a threaded part). Nominal thread; the printed screw carries the clearance (HS_TH_CLR).
    from cadkit.threads import threaded_rod
    for dy in (MAIN_YC - HS_YC, 0.0):                               # symmetric: both bosses at the same backmost X
        nut = (threaded_rod(HS_TH_MINOR, HS_BSTOP_OD, HS_TH_PITCH, HS_BSTOP_ENGAGE)
               .rotate((0, 0, 0), (0, 1, 0), 90).translate((HS_BACK_X + HS_SETBACK, HS_YC + dy, HS_Z)))
        w = w.cut(feel_place(nut), clean=False)
    return w


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
    # AXLE THROUGH-BORE (user round 2: the axle is a separate full-length part
    # now, so the hub simply takes a bore). D-BORE — the flat IS the key. cadkit
    # picks the shape from print_up: the lever prints lying on its -Y face, so
    # this bore runs ALONG the build direction, has no ceiling, and correctly
    # comes back as a PLAIN cylinder — the same call site that hands the housing
    # a teardrop.
    _bore = printable_bore(AXLE_BORE_D, 2 * LEVER_HW, (0.0, -LEVER_HW, 0.0),
                           (0.0, 1.0, 0.0), (0.0, 1.0, 0.0), overshoot=1.0)
    _zhi, _zlo = AXLE_FLAT_R + 0.1, -(AXLE_BORE_D / 2 + 1.0)
    body = body.cut(_bore.intersect(box_at(               # flatten the +Z side -> D
        AXLE_BORE_D + 2.0, 2 * LEVER_HW + 4.0, _zhi - _zlo,
        x=0.0, y=0.0, z=(_zhi + _zlo) / 2)))
    return heal(body)


def kl_axle() -> cq.Workplane:
    """PCTG AXLE ×1 per lever — ONE full-length printed part (user: the old
    integral-stub + glued-insert pair could not physically be assembled).
    Fitted LAST and slid +Y -> -Y through the +Y bearing, the lever hub and
    the -Y bearing, so nothing has to thread a rigid stub into an already-
    captured bearing.

      * Ø5 journals at both bearings, kept fully ROUND.
      * a D-FLAT over the hub band = the anti-rotation key (a protruding
        tongue could not pass the Ø5 bearing bore on the way in). Glue in the
        lever's matching D-bore is what holds it axially; the flat means that
        glue never carries torque.
      * a FLANGE that seats on the housing's contact rib — the axial datum
        that sets the magnet's Y, and with it the sensor air gap.
      * a magnet POCKET with a MALE thread on its OD; kl_magnet_cap screws
        over it and clamps the disc.

    Prints STANDING, POCKET-DOWN (collar face on the bed): that way the
    Ø5 -> Ø9 flange step is an upward-facing floor rather than a 2 mm
    overhanging ledge, and the 45° thread flanks self-support. Use a brim —
    the bed footprint is only the collar's annulus under a ~31 mm column.
    Built along +Z, threaded, then rotated onto the lever's +Y axis; the flat
    is milled AFTER the thread (cadkit thread rule) and it is NEVER healed."""
    from cadkit.threads import cut_thread
    r = AXLE_D / 2
    # smooth blank along +Z: journal shaft, then the flange/collar barrel
    b = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        r, AXLE_SHOULDER_Y - AXLE_Y0, cq.Vector(0, 0, AXLE_Y0), cq.Vector(0, 0, 1)))
    b = b.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        (MAG_TH_MAJOR - MAG_TH_CLR) / 2, MAG_FLANGE_T + MAG_COLLAR_H,
        cq.Vector(0, 0, AXLE_SHOULDER_Y), cq.Vector(0, 0, 1))))
    b = b.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(   # flange (rides the rib)
        AXLE_FLANGE_D / 2, MAG_FLANGE_T,
        cq.Vector(0, 0, AXLE_SHOULDER_Y), cq.Vector(0, 0, 1))))
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(     # magnet pocket
        MAG_POCKET_D / 2, MAG_COLLAR_H + 1.0,
        cq.Vector(0, 0, MAG_Y0), cq.Vector(0, 0, 1))))
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
knee_lever = _lever()
kl_axle = kl_axle()                            # printed: full-length PCTG axle
kl_magnet_cap = kl_magnet_cap()                # printed: screw-on magnet retainer
# ONE shared cartridge (printed twice: MAIN + HALF-STOP). Built canonically (MAIN placement: follower
# at the lobe rest extremum); the assembly slides a HALF-STOP copy +X by HS_SETBACK and a MAIN copy to
# MAIN_YC. Placement helper for build.py / tools:
CART_MAIN_OFFSET = (0.0, MAIN_YC - HS_YC, 0.0)        # main copy: shift to -Y
CART_HALFSTOP_OFFSET = (HS_SETBACK, 0.0, 0.0)         # half-stop copy: slide +X (engagement setback)
cart_base = _half_stop_cart_base()             # printed: cartridge (inverted-U, open -Z; no separate roof)
cart_piston = _half_stop_piston()              # printed: piston (Ø6 body + follower tongue + coil pilot)
guide_post = _guide_post()                     # printed: loose coil-back guide post (screw pushes it)
cart_backstop = _cart_backstop()               # printed: hollow X-position back-stop screw (tension screw runs through it)
cart_drag = _cart_drag()                       # printed TPU: passive drag pad (transport retention; print 2, MAIN mirrored)
# (the FLOATING TENON is retired -- the octagon tenons are now FUSED onto the housing yoke, so
# the lever mounts as a single part; the rib carries the matching octagon mortise. See _mount.)
