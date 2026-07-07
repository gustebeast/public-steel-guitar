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
(X), so the housing's +-X faces are clean bearing walls -> they carry the
christmas-tree mount tenons into the flanking ribs, and the magnet/sensor exit the
+Y end into open space under the body (no rib conflict).

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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "freecad"))
from fasteners import (M2_SELFTAP_D, M4_SHAFT_CLR_D, M4_INSERT_D,  # noqa: E402
                       M4_INSERT_L, M4_SCREW_L)

# ── bought parts (assembly dummies). REUSE existing line items where possible so they buy in
# bulk: MR85ZZ bearings + the M4×10 cup-tip set screws + M4 heat-set inserts are ALL already in
# the BOM (nut-block / screw-support). New: the Ø6 magnet, the MT6701 board, the springs.
AXLE_D  = 5.0                       # Ø5 ground-steel pin axle (rotates with the lever)
BRG_OD, BRG_ID, BRG_W = 8.0, 5.0, 2.5   # MR85ZZ — shared with the screw-support bearings
MAG_D, MAG_T = 6.0, 2.5             # Ø6×2.5 diametrically-magnetised magnet (on the axle end)
AIR_GAP = 1.5                       # magnet face -> MT6701 chip (the 0.5-3 mm window)
PCB_W, PCB_T = 18.0, 1.6            # custom JLCPCB MT6701 board (square)
INSERT_D, INSERT_L = M4_INSERT_D, M4_INSERT_L   # M4 heat-set insert Ø6 × 5 (standard set-screw process)
SCREW_CLR = M4_SHAFT_CLR_D          # M4 set-screw shaft clearance (Ø4.4)

# ── housing envelope ─────────────────────────────────────────────────────────
WALL    = 4.0                       # bearing-wall thickness (Y)
HALF_X  = 11.0                      # housing half-width in X (the bearing block; sits in the bay)
WALL_Z0, WALL_Z1 = -9.0, 12.7       # bearing walls span this in Z (bearing centred z=0); top = yoke

# ── layout along the axle (Y): -Y outboard (player) .. +Y inboard (under body) ──
# The hub/cam is THICK (24 mm) so the main coil (-Y), the half-stop cartridge (+Y) and the centred
# stop screw all get their own Y lane without touching. The bearing walls flank it; magnet + sensor
# sit past the +Y wall.
HUB_Y0, HUB_Y1 = -12.0, 12.0        # hub / cam / feel cavity -- 24 mm thick
WN_Y0, WN_Y1   = HUB_Y0 - 4.0, HUB_Y0   # -Y bearing wall (-14 .. -10)
WP_Y0, WP_Y1   = HUB_Y1, HUB_Y1 + 4.0   # +Y bearing wall (10 .. 14)
MAG_Y0  = WP_Y1 + 0.5               # magnet on the axle +Y end, just past the +Y wall (14.5)
PCB_Y   = MAG_Y0 + MAG_T + AIR_GAP  # MT6701 board face (chip side, -Y) at the gap
AXLE_Y0, AXLE_Y1 = WN_Y0, MAG_Y0    # axle: through both bearing walls .. the magnet seat
HUB_YC  = (HUB_Y0 + HUB_Y1) / 2     # hub / cam / feel centre Y (0)

# ── lever ────────────────────────────────────────────────────────────────────
HUB_D   = 10.0                      # ONE lever constant: the hub OD *and* the arm depth (ARM_TX). Keeps
                                    # the feel on the clear cam above the round hub, and the arm as deep
                                    # as the hub is wide for a solid root.
ARM_LEN = 100.0                     # hub centre -> arm tip (knee reach, -Z)
ARM_TX  = HUB_D                     # arm depth in X (bending axis: knee pushes X) = the hub OD
ARM_WY  = 20.0                      # arm width in Y -- the face the player's leg bears on (no paddle)
THROW   = 45.0                      # neutral -> full throw (deg, +theta about +Y)
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
LOBE_RC = HUB_TOP + 3.0                      # lobe axis radius (pivot -> lobe): the feel band is tight
                                             #   between the hub (below) and the mount boss (above), so
                                             #   keep it as small as clears the hub at full throw
LOBE_R  = 1.5                                # rounded lobe (top-edge) radius
CAM_TX  = 3.0                                # cam-plate thickness in X (the swing direction)
CAM_Y0, CAM_Y1 = HUB_Y0 + 1.0, HUB_Y1 - 1.0  # cam-plate Y span (wide enough to span both followers,
                                             #   which sit flush against the bearing walls)
# lobe +X extremum (what a follower touches) and its Z, at rest and at full throw:
LOBE_X0 = LOBE_R                              # follower contact X at rest (a=0)
LOBE_X1 = LOBE_RC * math.sin(_THR) + LOBE_R  # follower contact X at full throw
FOLL_TRAVEL = LOBE_X1 - LOBE_X0              # follower / piston travel over the throw (BOUNDED)
SWING_X = LOBE_RC * math.sin(_THR) + CAM_TX  # cam-plate +X reach at full throw (housing swing slot)
# travel STOP: a screw (in a central web, at y0 -- the clear gap between the two cartridges) that the
# cam PLATE's +X FACE runs into at the throw limit; screwing it -X shortens the max throw. Contact
# height chosen so the contact point sits on the plate face (below the lobe) and clears the hub.
STOP_Z  = HUB_TOP + 0.5                      # stop-contact height: JUST above the hub, so the screw can
                                             #   drive all the way in to the cam's NEUTRAL face (x=CAM_TX/2)
                                             #   without fouling the hub -> full stop range (0 .. THROW)
STOP_X  = (CAM_TX / 2 + STOP_Z * math.sin(_THR)) / math.cos(_THR)   # cam +X face at the FULL-throw limit
STOP_X0 = CAM_TX / 2                          # cam +X face at NEUTRAL (stop screwed fully in = no travel)
# Stop-screw boss: a central boss (y0, in the gap between the cartridges) threads the screw. It must
# clear the cam's full +X reach (its front sits +0.3 past STOP_X) yet stay threaded over the whole
# cup range STOP_X0..STOP_X, so it uses a long (M4x16) screw. WALL 1.6 mm all round is met in Z and
# +X; in Y it is pocket-limited (see HS_STOP_BOSS_WY) since the flush cartridges leave only a 4.8 mm gap.
STOP_SCREW_L    = 16.0                         # long stop screw -> full thread engagement across the range
HS_STOP_WALL    = 1.6                          # target boss wall around the M4 pilot
STOP_BOSS_X0    = STOP_X + 0.3                 # boss front: +0.3 past the cam's full-throw reach at STOP_Z
STOP_BOSS_X1    = STOP_BOSS_X0 + 8.0           # boss back: ~8 mm of threaded engagement

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
# return. 8N-at-knee x the 12.75:1 lever de-amplification = ~100N at the piston; that energy needs a
# Ø6 x ~37mm coil (~19 turns Ø1.2 wire, ~9 N/mm -> ~8.5N). Y (not Z) is the binding axis, so the coil
# sits in a Ø6.6 bore whose 1.1mm side walls are THINNER than the 1.6mm structural wall (cartridge outer
# stays 8.8 -> drops into the current pocket, no bearing/cam changes). The Ø4 screw drives the coil
# through a loose captive GUIDE POST (Ø3.2 pilot into the coil ID, Ø6 shoulder), not cup-on-coil.
HS_SPR_OD   = 6.0                   # coil OD
HS_SPR_WIRE = 1.2                   # coil wire dia
HS_SPR_ID   = HS_SPR_OD - 2 * HS_SPR_WIRE      # 3.6 -> guide-post / piston pilot noses into this
HS_SPR_FREE = 35.4                  # coil free length (~8N; bay + light-preload compression, fits 92mm)
HS_SPR_INST = 34.0                  # coil length DRAWN = the bay (= coil at lightest preload, its longest)
HS_PILOT_D  = HS_SPR_ID - 0.4       # 3.2: centre pilot (piston back + guide-post front) into the coil ID
HS_GPOST_LX = 3.0                   # guide-post body: coil-shoulder -> cup face (screw bears here)
HS_PILOT_LX = 5.0                   # pilot length reaching into the coil ID (piston back & guide post)
HS_ARM    = 4.0                     # piston "arm" (follower tongue): HS_ARM x HS_ARM (Y x Z), ends in a
                                    #   half-cylinder nose of radius HS_ARM/2
HS_Z      = HUB_TOP + 1.5           # piston / follower centre Z: the HS_ARM tongue spans the lobe band
                                    #   (5.66..8) and clears the hub below; the Ø6 body clears the boss
HS_PISTON_WY = HS_SPR_OD            # piston body: round Ø6 (= coil OD) -> seats the coil, rides the
HS_PISTON_WZ = HS_SPR_OD            #   channel, and is caught by the front lips (window < Ø6)
HS_FOLLOW_WY = HS_ARM              # follower-tongue width (Y) < body, so the front lips capture the body
HS_NOSE_PROTRUDE = FOLL_TRAVEL + 1.0  # tongue sticks this far -X of the front (> travel: never retracts)
HS_BODY_LX = 5.0                    # piston body length in X (rides the channel; long enough not to cock)
HS_CLR    = 0.4                     # piston/coil <-> channel slide clearance (per side)
HS_WALL   = 1.6                     # cartridge STRUCTURAL wall (floor / front / back); the coil-region
                                    #   SIDE walls end up thinner (~1.0, emergent) so the Ø6 coil fits Y
HS_HOUS_WALL = 2.4                  # housing shell wall around the pocket -- CONSTANT thickness, the
                                    #   outer /\ bottom parallels the pocket /\ (no thick flat bottom)
HS_ROOF_TZ = 1.0                    # roof thickness (thin, so the cartridge top stays under the mount boss)
HS_TENON_H, HS_TENON_WY = 0.6, 1.0  # base->roof tenon (up into a BLIND roof mortise): square, NO Z
                                    #   retention -- only sets the roof's install position; blind +X = -X stop
HS_LIP    = 1.5                     # front-lip depth in X (side lips that catch the piston body)
HS_TRAVEL = FOLL_TRAVEL + 0.5       # channel back-travel (>= follower travel)
HS_SPR_BORE = HS_SPR_OD + 0.6       # coil clearance bore
HS_ROOF_SPLIT = HS_Z + HS_PISTON_WZ / 2 + HS_CLR   # base<->roof split plane (just above the piston/coil)
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
HS_WIN_WY   = HS_ARM + 0.4                   # front-lip opening in Y: passes the tongue, catches the body
HS_CART_WY  = 8.8                            # cartridge outer Y -- FIXED (keeps pocket/placement); the
                                             #   wider 6.8 channel leaves ~1.0mm coil-region side walls
# cartridge Y placement: align each POCKET (the hole the cartridge slots into) so its outer edge is
# flush with the bearing wall's INNER face on that side -- the cartridge shares the bearing wall (no
# separate wall, no gap). (Earlier this aligned the block's OUTER face with the wall's outer face,
# spreading the cartridges too far.)
HS_POCKET_HW = HS_CART_WY / 2 + HS_CLR        # cartridge pocket (slot) half-width
HS_YC   = WP_Y0 - HS_POCKET_HW                # HALF-STOP (+Y): pocket +Y edge flush with +Y bearing-wall inner face
MAIN_YC = WN_Y1 + HS_POCKET_HW                # MAIN (-Y): pocket -Y edge flush with -Y bearing-wall inner face
# Stop boss: Z gets a full 1.6 mm wall; Y is LOCKED to the cartridge-housing edge (the pocket inner face
# at HS_YC-HS_POCKET_HW) so the boss is continuous with the retainer housing wall and never protrudes
# past it. Where a block flanks the screw its inner wall already fills to this edge; at the tip (-X of
# the block fronts) the boss fills the same +-edge -> boss and housing are one locked wall.
HS_STOP_BOSS_WY = 2 * (HS_YC - HS_POCKET_HW)              # Y: flush with the cartridge-housing edge
HS_STOP_BOSS_WZ = M4_SELFTAP + 2 * HS_STOP_WALL           # Z: 1.6 mm wall all round
HS_CART_Z0  = HS_Z - HS_CH_WZ / 2 - HS_WALL  # cartridge floor underside
HS_CART_Z1  = HS_ROOF_SPLIT + HS_ROOF_TZ     # cartridge roof top (< mount boss ~11.3)
# Only the cartridge OUTER shell keeps a 45 /\ V bottom (apex toward -Z) that nests into the housing
# pocket /\; the channel and piston interior are square. Apex offset one wall inward (perpendicular = *sqrt2).
HS_CART_APEX = HS_CART_Z0 - HS_CART_WY / 2            # cartridge outer /\ apex (nests in the pocket /\)
HS_POCKET_X0 = SWING_X              # housing pocket front (cartridge front cantilevers -X into the slot)
HS_HOUS_BACK = HS_BACK_X + 1.0                      # housing ends at the pocket back (holds the insert);
                                                    #   the tension screw's hex is left PROUD out the back

# ── mount (FLOATING-TENON): the lever hangs ENTIRELY below the body. The housing carries NO
# protruding tenon -- so it can print +Z->-Z without the tenon causing overhangs -- only a MORTISE
# in its yoke. The rib carries the SAME mortise. A separate FLOATING TENON (a double christmas-tree:
# two 45° diamonds joined by a thin TRUNK) bridges them: its lower diamond GLUES into the yoke, its
# upper diamond SLIDES +Y in the rib. Each diamond is wider than its slit, so it can't pull out -Z;
# being 45°, both mortises are self-supporting (print bottom-to-top). The TRUNK is only 0.8 mm so
# neither mortise goes deep. The RIB mortise is the long part (player face -> guitar mid-Y) so the
# lever slides to the chosen knee depth; a -Y M4 screw locks it. Even pitch -> one tenon fits any bay. ──
RIB_PITCH = 46.0                    # uniform bottom-rib pitch
TEN_XC    = RIB_PITCH / 2           # |X| of each tenon = each rib's offset from the bay centre (23)
BODY_Z    = 16.0                    # body underside plane in local Z (= -75.15 once posed)
YOKE_Z0, YOKE_Z1 = BODY_Z - 3.3, BODY_Z - 0.3   # yoke plate (top 0.3 mm below the body underside)
NECK_W    = 3.0                     # trunk / slit width (X)
SEG       = 0.8                     # EVERY segment is 0.8 mm ALONG ITS EDGE (one 0.8 nozzle pass)
DZ45      = SEG / math.sqrt(2)      # a 45° segment of edge SEG rises this much in Z (= in X) (~0.566)
HW0       = NECK_W / 2              # trunk half-width (1.5)
HW1       = HW0 + DZ45              # widest half-width -- the captured tooth (the 0.8 mm 45° widen)
TAPER     = HW1                     # 45° taper: the Z it takes to come back to a POINT (computed)
# The narrow trunk extends SEG=0.8 mm into EACH mortise -- that 0.8 mm is the mortise SIDE-WALL
# height (the slit). So the tenon's own trunk spans 2*SEG + the yoke/rib gap. Then a 0.8 mm widen
# makes the captured tooth on each side, and a computed taper closes to a point. The tenon glues
# into the lever (lower half) + slides in the rib (upper half).
Z_TL      = YOKE_Z1 - SEG              # trunk low  = 0.8 mm vertical slit into the yoke (lever wall)
Z_TH      = BODY_Z + SEG               # trunk high = 0.8 mm vertical slit into the rib  (rib wall)
_LP       = Z_TL - DZ45 - TAPER        # lever point (deep in the yoke)
_RP       = Z_TH + DZ45 + TAPER        # rib point (deep in the rib)
TEN_PTS   = [(_LP, 0.0), (Z_TL - DZ45, HW1), (Z_TL, HW0),
             (Z_TH, HW0), (Z_TH + DZ45, HW1), (_RP, 0.0)]
BOSS_Z0   = _LP - 1.0                  # yoke-boss floor (hosts the lever-side taper point)
# the floating tenon + its lever-yoke mortise run the FULL Y length of the housing (a long glue
# joint + more rib engagement); the low 0.8 mm joint keeps it clear of the feel screws below.
TEN_Y0, TEN_Y1   = WN_Y0, 24.0     # floating-tenon / lever-mortise Y-span (outboard wall -> inboard)
TEN_STOP  = 1.5                    # -Y STOP wall closing the lever mortise: the tenon seats against it
                                   #   (sliding the lever in drags the tenon -Y into the stop -> located)
TEN_LY0   = TEN_Y0 + TEN_STOP      # tenon / lever-mortise -Y end (butts the stop)
MORT_CLR  = 0.3                     # mortise clearance (slide / glue fit)
MORT_Y0   = -2.0                    # mortise -Y mouth (opens outboard of the -Y rail for slide-in)
YOKE_Y0   = -10.0                   # yoke -Y extent (over the bearing block)
# global mount: LKL bay (centred between even ribs -524 / -478). build.py poses the lever here;
# chassis.py cuts the rib mortises at the same place.
MOUNT_X, MOUNT_Y, MOUNT_Z = -501.0, -148.75, -75.15 - BODY_Z
MOUNT_POSE = (MOUNT_X, MOUNT_Y, MOUNT_Z)
# the mortise (slot) runs from the player face ALL THE WAY to the guitar's Y midpoint -- the lever's
# nub slides +Y along it to the player's chosen knee depth, then the retention screw locks it.
MID_Y     = -37.0                   # guitar Y-midpoint (= chassis (Y_LO + Y_HI)/2)
MORT_Y1   = MID_Y - MOUNT_Y         # mortise +Y end at mid-Y (in the local frame)
# retention: the +X tenon's FLAT -X side leaves the rib ledge on that side reachable straight down, so
# ONE M4 set screw threads UP through the yoke boss beside the tenon and PRESSES the rib ledge (jamming
# the tenon in its mortise -> friction-locks the Y slide). The rib runs in Y, so the ledge is directly
# above the screw at EVERY slide position -- it never floats past a rail end like the old rail-biting
# screw did, and it needs no drilled pilot (it just bears on the printed rib surface).
# X: the Ø4.4 clearance bore runs TANGENT to the tenon's flat -X face (TEN_XC-HW0) so the screw clears
# the tenon and threads fully home. The bore may cut through the mortise WALL (fine) but not the tenon.
RETAIN_X = (TEN_XC - HW0) - SCREW_CLR / 2
# +Y of BOTH the half-stop cartridge (ends Y=12) AND the +Y bearing wall (ends Y=16), so the screw's
# whole Z path -- driver access + its up/down adjustment -- is open below the yoke boss; clear of the
# PCB wall at Y=20.5. (At Y=5 the cartridge housing sat right in that path.)
RETAIN_Y = 18.0                                         # yoke boss (TEN_Y0..TEN_Y1) clear of cart+wall+PCB
# Insert pocket TOP: as high (close to the rib the cup presses) as it can go without the Ø6 pocket
# reaching the mortise -- 1 mm below the mortise's lowest z (the grown christmas-tree tip, _LP-MORT_CLR).
# This lets the screw thread fully home AND still reach the rib. Derived, never hardcoded.
RETAIN_INS_TOP = (_LP - MORT_CLR) - 1.0


def _bearing():
    """MR85ZZ dummy (axis Y), -Y face at y=0."""
    o = cyl_y(BRG_OD, BRG_W, y0=0.0)
    b = cyl_y(BRG_ID, BRG_W + 0.2, y0=-0.1)
    return o.cut(b)


def demo_parts():
    """Bought-part dummies in the local frame: (name, shape). Assembly-only."""
    out = []
    out.append(("kl_axle", cyl_y(AXLE_D, AXLE_Y1 - AXLE_Y0, y0=AXLE_Y0)))
    for i, by in enumerate((WN_Y0 + (WALL - BRG_W) / 2, WP_Y0 + (WALL - BRG_W) / 2)):
        out.append((f"kl_bearing_{i}", _bearing().translate((0, by, 0))))
    out.append(("kl_magnet", cyl_y(MAG_D, MAG_T, y0=MAG_Y0)))
    out.append(("kl_pcb", box_at(PCB_W, PCB_T, PCB_W, x=0, y=PCB_Y + PCB_T / 2, z=0)))
    # BOTH springs are the SAME cartridge: MAIN (at MAIN_YC) whose follower touches the lobe at REST
    # (sets the rest angle), and HALF-STOP (at HS_YC, slid +X by HS_SETBACK) that engages partway. Each
    # has a coil, a back TENSION screw (preload), and a FROM-BELOW CLAMP screw that jams the cartridge
    # up against the pocket ceiling -- locking its slid X (= rest / engagement) and retaining the roof.
    for nm, dx, dy in (("main", 0.0, MAIN_YC - HS_YC), ("half_stop", HS_SETBACK, 0.0)):
        out.append((f"{nm}_spring", (cyl(HS_SPR_OD, HS_SPR_INST, z=HS_BODY_BX)   # Ø6 coil (tube: pilots
                    .cut(cyl(HS_SPR_ID, HS_SPR_INST + 2, z=HS_BODY_BX - 1)))      #   pass through the ID)
                    .rotate((0, 0, 0), (0, 1, 0), 90).translate((dx, HS_YC + dy, HS_Z))))
        # HEX faces +X (accessed through the back-wall bore), CUP faces -X: set_screw is hex(+Z)/cup(-Z)
        # -> rotate +90 maps hex->+X. The CUP tip bears on the GUIDE-POST back (HS_GPOST_BX); driving it
        # in pushes the post -> compresses the coil (preload). Hex sits in the housing access bore behind.
        out.append((f"{nm}_spring_tension_setscrew", C.set_screw().rotate((0, 0, 0), (0, 1, 0), 90)
                    .translate((HS_GPOST_BX + M4_SCREW_L + dx, HS_YC + dy, HS_Z))))
        out.append((f"{nm}_spring_tension_insert",                      # Ø6×5 insert, flush at the back wall
                    _seated_insert((HS_BACK_X + dx, HS_YC + dy, HS_Z), (0, 1, 0), -90)))
        cp = _hs_clamp_pt(HS_YC + dy, dx)
        out.append((f"{nm}_clamp_setscrew", C.set_screw().rotate((0, 0, 0), (1, 0, 0), -45)  # +Y+Z angled
                    .translate(cp)))
        out.append((f"{nm}_clamp_insert", _insert_dummy(cp, (1, 0, 0), -45)))               # Ø6×5 insert
    # travel STOP: a horizontal screw in the central web; the cam +X face hits its -X tip at the throw
    # limit (turn -X to shorten the travel). At y0 (centre gap), clear of both cartridges.
    # CUP tip -X (hits the cam), HEX +X (driver in the gap): set_screw is hex(+Z)/cup(-Z) -> rotate +90
    # maps hex->+X, cup->-X. Placed nominally at the full-throw contact (cup at STOP_X).
    _hexd = 2.0 / math.cos(math.radians(30))
    _stop = (cyl(4.0, STOP_SCREW_L, z=-STOP_SCREW_L)
             .cut(cq.Workplane("XY").polygon(6, _hexd).extrude(-3.0).translate((0, 0, 0.5))))
    out.append(("stop_angle_setscrew", _stop.rotate((0, 0, 0), (0, 1, 0), 90)
                .translate((STOP_X + STOP_SCREW_L, HUB_YC, STOP_Z))))
    # retention set screw: threads up through the yoke boss beside the +X tenon (flat -X side), CUP tip
    # +Z pressing the rib ledge, HEX -Z driven from below. set_screw is hex(+Z)/cup(-Z) -> rotate 180
    # about X flips it (cup +Z / hex -Z); cup tip lands at the rib bottom (BODY_Z).
    out.append(("retention_setscrew", C.set_screw().rotate((0, 0, 0), (1, 0, 0), 180)
                .translate((RETAIN_X, RETAIN_Y, BODY_Z - 10.0))))
    out.append(("retention_insert",                                  # Ø6×5 insert, top RETAIN_INS_TOP
                C.m4_insert().translate((RETAIN_X, RETAIN_Y, RETAIN_INS_TOP))))
    return out


def _ctree_prism_y(xc, y0, y1, grow=0.0):
    """A christmas-tree prism from TEN_PTS but with ONE FLAT SIDE: the +X side keeps the capture teeth
    (trunk + 0.8 mm 45 widen + tapered points), the -X side is a single VERTICAL WALL (at the trunk
    half-width, 45-chamfered to the shared point tips). The flat face gives the printed tenon a bed to
    lie on, and leaves the rib ledge on that side reachable STRAIGHT DOWN (no tooth notch) for the
    retention screw. Centred at xc, extruded +Y over y0..y1. `grow` -> slide-fit mortise from the same
    profile."""
    p = [(z, hw + grow) for z, hw in TEN_PTS]
    # tips: push grow DEEPER in z AND reset to a SHARP point (hw=0). The z-push is what keeps the 45
    # taper at 45 once hw is grown (Δz = TAPER+grow must equal Δx = HW1+grow); leaving the tip blunt at
    # hw=grow instead skews the taper to ~49/41 deg -- a non-clean MORTISE while the grow=0 tenon stays 45.
    p[0] = (p[0][0] - grow, 0.0); p[-1] = (p[-1][0] + grow, 0.0)
    right = [cq.Vector(xc + hw, y0, z) for z, hw in p]                      # +X: full christmas tree
    fw = HW0 + grow                                                        # flat wall at the trunk half-width
    left = [cq.Vector(xc - fw, y0, p[-1][0] - fw),                         # top 45 chamfer -> vertical wall
            cq.Vector(xc - fw, y0, p[0][0] + fw)]                          # -> bottom 45 chamfer (on close)
    verts = right + left
    face = cq.Face.makeFromWires(cq.Wire.makePolygon(verts + [verts[0]]))
    return cq.Workplane("XY").add(cq.Solid.extrudeLinear(face, cq.Vector(0, y1 - y0, 0)))


def _mount():
    """The mount: a yoke plate (slides +Y under the ribs, entirely below the body) carrying NO
    protruding tenon -- just a lever-side christmas-tree MORTISE (the lower half of the profile) in a
    boss at each rib. So the housing has no +Z tenon to obstruct its print; the floating tenon glues
    into the mortise, running the full housing length."""
    out = box_at(2 * (TEN_XC + 3), TEN_Y1 - YOKE_Y0, YOKE_Z1 - YOKE_Z0,
                 x=0, y=(YOKE_Y0 + TEN_Y1) / 2, z=(YOKE_Z0 + YOKE_Z1) / 2)
    for s in (1, -1):                                          # a boss to host the mortise
        out = out.union(box_at(2 * HW1 + 4, TEN_Y1 - TEN_Y0, YOKE_Z1 - BOSS_Z0,
                               x=s * TEN_XC, y=(TEN_Y0 + TEN_Y1) / 2, z=(YOKE_Z1 + BOSS_Z0) / 2))
    for s in (1, -1):                                          # lever-side mortise = profile z <= yoke top
        mortise = _ctree_prism_y(s * TEN_XC, TEN_LY0, TEN_Y1, grow=MORT_CLR)   # -Y end closed = the stop
        mortise = mortise.intersect(box_at(400, 500, 400, z=YOKE_Z1 - 200))   # keep z <= yoke top
        out = out.cut(mortise)
    return out


def rib_mortise(rib_x):
    """ONE christmas-tree mortise (GLOBAL) = the RIB half of the profile (z >= rib bottom), centred on
    the crossbar at rib_x, opening at the rib bottom (-Z) and running +Y from the player face to the
    guitar mid-Y. chassis.py cuts this into EVERY rib so a lever can mount in ANY bay."""
    m = _ctree_prism_y(0.0, MORT_Y0, MORT_Y1, grow=MORT_CLR)
    m = m.intersect(box_at(400, 500, 400, z=BODY_Z + 200))                 # keep z >= rib bottom
    return m.translate((rib_x, MOUNT_Y, MOUNT_Z))


# (retention now PRESSES the rib ledge -- no drilled pilot in the rib, so no per-bay chassis feature)


def _guide_post() -> cq.Workplane:
    """Loose captive guide post (printed): a Ø6 SHOULDER that seats the coil BACK and rides the channel,
    with a Ø3.2 PILOT nosing -X into the coil ID. The Ø4 tension-screw cup bears on its +X face -- it only
    ever pushes, and is trapped between cup, coil and roof once assembled (see knee-lever-feel-spring)."""
    shoulder = cyl(HS_SPR_OD, HS_GPOST_LX, z=HS_SPR_TIPX)                  # Ø6: coil back -> cup face
    pilot = cyl(HS_PILOT_D, HS_PILOT_LX, z=HS_SPR_TIPX - HS_PILOT_LX)      # Ø3.2: -X into the coil ID
    return heal(shoulder.union(pilot).rotate((0, 0, 0), (0, 1, 0), 90).translate((0, HS_YC, HS_Z)))


def _half_stop_piston() -> cq.Workplane:
    """The piston (printed): a square BODY (Ø6 footprint) that slides in the channel and seats the coil
    FRONT on its +X face, a centre PILOT boss that noses +X into the coil ID to keep it aligned, and a
    SHORT follower TONGUE at the lobe band that protrudes -X, ending in a HALF-CYLINDER nose (round in
    X-Z, square across Y) for clean rolling cam contact. The body is wider than the front-lip window, so
    the preloaded coil can't eject it."""
    body = box_at(HS_BODY_BX - HS_BODY_X0, HS_PISTON_WY, HS_PISTON_WZ,
                  x=(HS_BODY_X0 + HS_BODY_BX) / 2, y=HS_YC, z=HS_Z)
    rn = HS_ARM / 2                                                        # nose radius = half the arm height
    neck = box_at(HS_BODY_X0 - (HS_NOSE_TIPX + rn), HS_FOLLOW_WY, HS_ARM,
                  x=(HS_NOSE_TIPX + rn + HS_BODY_X0) / 2, y=HS_YC, z=HS_Z)
    cap = cyl_y(HS_ARM, HS_FOLLOW_WY, y0=HS_YC - HS_FOLLOW_WY / 2).translate((HS_NOSE_TIPX + rn, 0, HS_Z))
    pilot = (cyl(HS_PILOT_D, HS_PILOT_LX, z=HS_BODY_BX)                    # +X boss centring the coil ID
             .rotate((0, 0, 0), (0, 1, 0), 90).translate((0, HS_YC, HS_Z)))
    return heal(body.union(neck).union(cap).union(pilot))


def _hs_wall_yc(s):
    return HS_YC + s * (HS_CH_WY / 2 + HS_WALL / 2)                         # centre-Y of the ±Y side wall


def _half_stop_cart_base() -> cq.Workplane:
    """Half-stop cartridge BASE (printed): a U-channel (floor + side walls, OPEN TOP -> no roof
    overhang) with a back wall (coil bore + tension insert) and front side-lips that capture the piston
    body. Rounded anti-bind ribs on the floor; a small TENON on each side-wall top rises into a blind
    mortise in the roof (locates the roof + gives a -X install stop)."""
    # OUTER shell: flat top + a 45 /\ BOTTOM (apex toward -Z) that nests into the housing pocket /\ and
    # gives the angled clamp a flush face. The INSIDE (channel) and the piston stay SQUARE -- so the base
    # is solid between the /\ outer and the flat channel floor.
    ch_z0 = HS_Z - HS_CH_WZ / 2                                            # (square) channel floor
    base = _v_prism(HS_YC, HS_CART_WY / 2, HS_ROOF_SPLIT, HS_CART_APEX, HS_FRONT, HS_BACK_X)
    # ONE wide channel: the Ø6 piston, coil and guide post all ride it (open top for the roof drop-on)
    base = base.cut(box_at(HS_GPOST_BX - HS_BODY_X0, HS_CH_WY, (HS_ROOF_SPLIT + 5) - ch_z0,
                           x=(HS_BODY_X0 + HS_GPOST_BX) / 2, y=HS_YC, z=(ch_z0 + HS_ROOF_SPLIT + 5) / 2))
    # front tongue window (at the lobe band): passes the follower tongue; the front wall catches the body
    base = base.cut(box_at(HS_BODY_X0 - HS_FRONT + 0.1, HS_WIN_WY, HS_ARM + 0.4,
                           x=(HS_FRONT + HS_BODY_X0) / 2, y=HS_YC, z=HS_Z))
    # rear M4 heat-set insert (tension screw, opens +X) + Ø4.4 shaft clearance from the insert to the
    # guide-post cup face: the screw threads the insert and its cup pushes the guide post -> coil preload
    base = _insert_pocket(base, (HS_BACK_X, HS_YC, HS_Z), (0, 1, 0), -90)
    base = base.cut(cyl(SCREW_CLR, HS_BACK_X - HS_GPOST_BX, z=HS_GPOST_BX)
                    .rotate((0, 0, 0), (0, 1, 0), 90).translate((0, HS_YC, HS_Z)))
    # a tenon on each side-wall top: rises HS_TENON_H into the roof's blind mortise
    for s in (1, -1):
        base = base.union(box_at(HS_BACK_X - 1 - HS_BODY_X0, HS_TENON_WY, HS_TENON_H,
                                 x=(HS_BODY_X0 + HS_BACK_X - 1) / 2, y=_hs_wall_yc(s),
                                 z=HS_ROOF_SPLIT + HS_TENON_H / 2))
    return heal(base)


def _half_stop_cart_roof() -> cq.Workplane:
    """Half-stop cartridge ROOF (printed): a FULL-cover lid (solid +Z face) with two BLIND mortises that
    swallow the base tenons -- open at -X, closed at +X, so the roof drops on and slides -X to a hard stop
    (its install position). No Z retention (that's the clamp screw / housing pocket); the -X stop means
    sliding the cartridge into the housing seats the roof harder rather than peeling it off. Prints flat."""
    lid = box_at(HS_BACK_X - HS_FRONT, HS_CART_WY, HS_CART_Z1 - HS_ROOF_SPLIT,
                 x=(HS_FRONT + HS_BACK_X) / 2, y=HS_YC, z=(HS_ROOF_SPLIT + HS_CART_Z1) / 2)
    # blind mortises for the tenons: open at the -X (front) edge, closed at +X (HS_BACK_X-1) = -X stop
    for s in (1, -1):
        lid = lid.cut(box_at((HS_BACK_X - 1) - HS_FRONT, HS_TENON_WY + 0.4, HS_TENON_H + 0.3,
                             x=(HS_FRONT + HS_BACK_X - 1) / 2, y=_hs_wall_yc(s),
                             z=HS_ROOF_SPLIT + (HS_TENON_H + 0.3) / 2 - 0.15))
    return heal(lid)


def hs_pocket_hw():
    return HS_CART_WY / 2 + HS_CLR                          # pocket half-width (slot + slide clearance)


def hs_pocket_zridge():                                     # /\ roof apex z (self-supporting print)
    return (HS_CART_Z0 - HS_CLR) - hs_pocket_hw()


def _v_prism(yc, hw, z_top, z_apex, x0, x1):
    r"""A flat-top rectangle (down to where the 45 slopes start) + a /\ V bottom to a centre apex at
    z_apex, centred at yc. Extruded in X over x0..x1. The shared shape for the housing pocket, the
    cartridge shell, its channel, and the piston -- so they all nest at 45."""
    z_v = z_apex + hw                                  # sides meet the V here (45 deg)
    pts = [(yc - hw, z_top), (yc + hw, z_top), (yc + hw, z_v), (yc, z_apex), (yc - hw, z_v)]
    verts = [cq.Vector(x0, y, z) for (y, z) in pts]
    face = cq.Face.makeFromWires(cq.Wire.makePolygon(verts + [verts[0]]))
    return cq.Workplane("XY").add(cq.Solid.extrudeLinear(face, cq.Vector(x1 - x0, 0, 0)))


def _hs_pocket(yc, x0, x1):
    r"""The housing pocket for one cartridge: a rectangular slot whose FLOOR is a /\ roof (self-supporting
    for the +Z->-Z print, no floor-bridge overhang) that the cartridge's /\ bottom nests into."""
    return _v_prism(yc, hs_pocket_hw(), HS_CART_Z1 + HS_CLR, hs_pocket_zridge(), x0, x1)


def _hs_clamp_pt(yc, dx):
    r"""Midpoint of the -Y /\ slope, where the angled clamp screw bears (axis along +Y+Z)."""
    hw = hs_pocket_hw()
    return ((HS_FRONT + HS_BACK_X) / 2 + dx, yc - hw / 2, ((HS_CART_Z0 - HS_CLR) + hs_pocket_zridge()) / 2)


_INS_BOSS_PROT = 6.0                # how far the insert boss protrudes past the (too-thin) wall


def _oriented(s, axis, deg, pt):
    return s.rotate((0, 0, 0), axis, deg).translate(pt)


def _insert_boss_cut(w, pt, axis, deg, clr_len=(M4_SCREW_L - M4_INSERT_L) + 2.0):
    """Add a STANDARD Ø6×5-insert boss along a screw axis where the local wall is too thin: a protruding
    Ø(6+2) boss to host the insert, the Ø6×5 insert pocket at the -axis (entry) face, and Ø4.4 shaft
    clearance running +axis to the working tip. `axis`,`deg` rotate local +Z (toward the tip) onto the
    screw axis; `pt` is the axis origin (local z=0, the wall face). Shared by the angled cartridge clamp
    and the vertical retention screw -- returns the modified housing.
    clr_len defaults to the screw's PROTRUDING reach only (screw len - insert engagement + 2 mm cup
    margin); a longer bore punches out the far wall past the cup (e.g. the +Y cartridge housing)."""
    bp = _INS_BOSS_PROT
    w = w.union(_oriented(cyl(M4_INSERT_D + 2.0, bp, z=-bp), axis, deg, pt))
    w = w.cut(_oriented(cyl(M4_INSERT_D, M4_INSERT_L, z=-bp), axis, deg, pt))
    w = w.cut(_oriented(cyl(SCREW_CLR, clr_len, z=-bp + M4_INSERT_L), axis, deg, pt))
    return w


def _insert_dummy(pt, axis, deg):
    """The Ø6×5 insert TUBE dummy seated in an _insert_boss_cut pocket (call with the SAME pt/axis/deg)."""
    return _oriented(C.m4_insert().translate((0, 0, -_INS_BOSS_PROT + M4_INSERT_L)), axis, deg, pt)


# --- flat-wall insert (no boss): a matched pocket/dummy PAIR --------------------------------------
# Both take the SAME (mouth_pt, axis, deg) and both derive their size from M4_INSERT_D / M4_INSERT_L,
# so the pocket depth ALWAYS equals the insert thickness and the fitted insert ALWAYS seats flush
# against the depth lip -- there is no per-call depth/diameter to drift. `axis`,`deg` rotate local +Z
# (the insertion direction, INTO the material) onto the bore axis; `mouth_pt` is the wall face the
# insert enters at. (_insert_boss_cut / _insert_dummy are the equivalent pair when a boss must host it.)
def _insert_pocket(w, mouth_pt, axis, deg):
    """Cut the STANDARD Ø(M4_INSERT_D) x M4_INSERT_L heat-set pocket, mouth at `mouth_pt`, bore +axis."""
    return w.cut(_oriented(cyl(M4_INSERT_D, M4_INSERT_L, z=0), axis, deg, mouth_pt))


def _seated_insert(mouth_pt, axis, deg):
    """The insert dummy seated FLUSH in an _insert_pocket -- fills the same z=0..L span (SAME args)."""
    return _oriented(C.m4_insert().translate((0, 0, M4_INSERT_L)), axis, deg, mouth_pt)


def _hs_block(yc, x0, x1):
    r"""The housing SHELL around one cartridge pocket: rectangular top (slot side walls + ceiling) with a
    /\ bottom that PARALLELS the pocket /\ at a CONSTANT wall HS_HOUS_WALL -- so there's no thick flat
    bottom. Y-Z section extruded in X. Cut _hs_pocket() from this to leave the even-thickness shell."""
    hw = hs_pocket_hw()
    t = HS_HOUS_WALL
    z_top, z_bot, z_ridge = HS_CART_Z1 + HS_CLR, HS_CART_Z0 - HS_CLR, hs_pocket_zridge()
    z_corner = z_bot - (math.sqrt(2) - 1) * t      # outer /\ meets the vertical side wall
    z_apex   = z_ridge - math.sqrt(2) * t          # outer apex (perpendicular offset t from inner apex)
    pts = [(yc - (hw + t), z_top + t), (yc + (hw + t), z_top + t), (yc + (hw + t), z_corner),
           (yc, z_apex), (yc - (hw + t), z_corner)]
    verts = [cq.Vector(x0, y, z) for (y, z) in pts]
    face = cq.Face.makeFromWires(cq.Wire.makePolygon(verts + [verts[0]]))
    return cq.Workplane("XY").add(cq.Solid.extrudeLinear(face, cq.Vector(x1 - x0, 0, 0)))


def _housing() -> cq.Workplane:
    xc, xw = 0.0, 2 * HALF_X
    zc, zh = (WALL_Z1 + WALL_Z0) / 2, WALL_Z1 - WALL_Z0
    # two bearing walls (normal to Y) + the top spine that ties them (and is the mount face)
    w = box_at(xw, WALL, zh, x=xc, y=WN_Y0 + WALL / 2, z=zc)
    w = w.union(box_at(xw, WALL, zh, x=xc, y=WP_Y0 + WALL / 2, z=zc))
    # bearing pockets (Ø8) + axle clearance through-bores
    for by in (WN_Y0, WP_Y0):
        w = w.cut(cyl_y(BRG_OD + 0.1, BRG_W + 0.3, y0=by + (WALL - BRG_W) / 2))
        w = w.cut(cyl_y(AXLE_D + 1.0, WALL + 1.0, y0=by - 0.5))
    # PCB mount: a wall at +Y carrying the board, with a magnet keep-out bore
    w = w.union(box_at(PCB_W + 4, WALL, PCB_W + 4, x=0, y=PCB_Y + PCB_T + WALL / 2, z=0))
    w = w.cut(cyl_y(MAG_D + 3.0, 8.0, y0=PCB_Y - 4))                        # keep-out + gap
    for sx in (1, -1):                                                      # PCB screw bosses (M2)
        for sz in (1, -1):
            w = w.cut(cyl_y(M2_SELFTAP_D, 8.0, y0=PCB_Y)
                      .translate((sx * PCB_W / 3, 0, sz * PCB_W / 3)))
    # ── feel mechanism (open air below the body): a +Z cam PLATE with a rounded LOBE swings +X on
    # throw; TWO identical spring cartridges (MAIN at -Y, HALF-STOP at +Y) push flat followers on the
    # lobe. Each sits in a slide-fit pocket, is CLAMPED UP from below (locks its slid X + retains the
    # roof), and its tension screw is reached from +X. No rest/stop screws: the MAIN cartridge sets the
    # rest, and the springs only PUSH so the lever folds free the other way (storage). ──
    cw  = (CAM_Y1 - CAM_Y0) + 1                                             # swing-slot Y width (clears walls)
    slot_h = LOBE_RC + 2 * LOBE_R + 3
    w = w.cut(box_at(2 * SWING_X + 4, cw, slot_h, x=0, y=HUB_YC, z=slot_h / 2 - 1))   # cam swing slot
    for dx, dy in ((0.0, MAIN_YC - HS_YC), (HS_SETBACK, 0.0)):
        yc  = HS_YC + dy
        bx0, bx1 = HS_POCKET_X0 + dx, HS_HOUS_BACK + dx
        # constant-wall shell (/\ bottom parallels the pocket /\) + the /\ pocket cut (self-supporting,
        # no floor-bridge overhang); the cartridge front cantilevers -X of HS_POCKET_X0 into the swing slot
        w = w.union(_hs_block(yc, bx0, bx1))
        w = w.cut(_hs_pocket(yc, bx0, HS_BACK_X + 1.0 + dx))
        # ANGLED clamp (axis +Y+Z): threads into a Ø6×5 insert at the -Y/-Z player face; its cup presses
        # the cartridge UP against the ceiling. The /\ slope wall is too thin, so a boss protrudes -axis
        # into the player-side air to host it; the pocket is RE-CUT after so the boss can't reach the slot.
        w = _insert_boss_cut(w, _hs_clamp_pt(yc, dx), (1, 0, 0), -45)
        w = w.cut(_hs_pocket(yc, bx0, HS_BACK_X + 1.0 + dx))
        # (no back-wall access bore: the housing stops at the pocket back, so the tension screw's hex
        #  simply protrudes into open air past it -- reached by a driver directly)
    # travel STOP: a central boss (y0, in the clear gap between the cartridges) carrying a horizontal
    # self-tap screw whose CUP tip faces -X (the cam +X FACE runs into it) and whose HEX faces +X (driver
    # reaches it in the gap). The boss sits +X of the cam's full-throw reach; the screw drives in over the
    # full range -- cup at STOP_X0 (neutral = no travel) out to STOP_X (full throw). Turn -X to shorten.
    sb0, sb1 = STOP_BOSS_X0, STOP_BOSS_X1
    w = w.union(box_at(sb1 - sb0, HS_STOP_BOSS_WY, HS_STOP_BOSS_WZ,
                       x=(sb0 + sb1) / 2, y=HUB_YC, z=STOP_Z))
    # (boss Y is flush with the pocket inner face, so no pocket re-cut is needed -- it can't protrude)
    # M4 pilot through the full boss (driver reaches the hex down this bore); the cup protrudes -X into
    # the swing slot to meet the cam face. Long (M4x16) screw stays threaded over the whole cup range.
    w = w.cut(cyl(M4_SELFTAP, (sb1 - sb0) + 2, z=sb0 - 1)
              .rotate((0, 0, 0), (0, 1, 0), 90).translate((0, HUB_YC, STOP_Z)))
    # mount: yoke with a lever-side christmas-tree mortise at each rib (the floating tenon glues in)
    w = w.union(_mount())
    # retention: the Ø6×5 insert + Ø4.4 clearance sit in a boss beside the +X tenon. The boss runs the
    # FULL Z to the yoke top (backed by the body -> no overhang), then the +X tenon MORTISE is re-cut so
    # it passes cleanly THROUGH the boss (the tenon still slides). The insert stops RETAIN_INS_TOP (1 mm
    # below the mortise) so the screw threads fully home yet its cup still reaches the rib.
    _ins_bot = RETAIN_INS_TOP - M4_INSERT_L
    w = w.union(cyl(M4_INSERT_D + 2.0, YOKE_Z1 - _ins_bot, z=_ins_bot).translate((RETAIN_X, RETAIN_Y, 0)))
    _mort = (_ctree_prism_y(TEN_XC, TEN_LY0, TEN_Y1, grow=MORT_CLR)
             .intersect(box_at(400, 500, 400, z=YOKE_Z1 - 200)))     # +X tenon mortise (z <= yoke top)
    w = w.cut(_mort)                                                 # re-cut it THROUGH the boss
    w = w.cut(cyl(M4_INSERT_D, M4_INSERT_L, z=_ins_bot).translate((RETAIN_X, RETAIN_Y, 0)))       # Ø6×5 insert
    w = w.cut(cyl(SCREW_CLR, (YOKE_Z1 + 2) - RETAIN_INS_TOP, z=RETAIN_INS_TOP)
              .translate((RETAIN_X, RETAIN_Y, 0)))                   # Ø4.4 shaft clearance up to the rib
    return heal(w)


def _lever() -> cq.Workplane:
    # hub on the axle (bore Ø5), arm down -Z (the player's leg bears on it directly -- no paddle), cam +Z
    hub = cyl_y(HUB_D, HUB_Y1 - HUB_Y0, y0=HUB_Y0)
    arm = box_at(ARM_TX, ARM_WY, ARM_LEN, x=0, y=HUB_YC, z=-ARM_LEN / 2)
    # return CAM: a Y-wide plate off the hub (+Z at neutral) with a rounded LOBE along its top edge.
    # The flat piston followers bear on the lobe -> bounded travel through the throw. No lever nub.
    plate = box_at(CAM_TX, CAM_Y1 - CAM_Y0, LOBE_RC, x=0, y=(CAM_Y0 + CAM_Y1) / 2, z=LOBE_RC / 2)
    lobe = cyl_y(2 * LOBE_R, CAM_Y1 - CAM_Y0, y0=CAM_Y0).translate((0, 0, LOBE_RC))
    body = hub.union(arm).union(plate).union(lobe)
    body = body.cut(cyl_y(AXLE_D + 0.05, (HUB_Y1 - HUB_Y0) + 2, y0=HUB_Y0 - 1))   # axle bore
    return heal(body)


knee_housing = _housing()
knee_lever = _lever()
# ONE shared cartridge (printed twice: MAIN + HALF-STOP). Built canonically (MAIN placement: follower
# at the lobe rest extremum); the assembly slides a HALF-STOP copy +X by HS_SETBACK and a MAIN copy to
# MAIN_YC. Placement helper for build.py / tools:
CART_MAIN_OFFSET = (0.0, MAIN_YC - HS_YC, 0.0)        # main copy: shift to -Y
CART_HALFSTOP_OFFSET = (HS_SETBACK, 0.0, 0.0)         # half-stop copy: slide +X (engagement setback)
cart_base = _half_stop_cart_base()             # printed: cartridge base (U-channel + coil bay + lips)
cart_roof = _half_stop_cart_roof()             # printed: cartridge roof (drops on; blind tenon mortises)
cart_piston = _half_stop_piston()              # printed: piston (Ø6 body + follower tongue + coil pilot)
guide_post = _guide_post()                     # printed: loose coil-back guide post (screw pushes it)
# the FLOATING TENON: a separate printed rail (one per rib); glue its lower half into the lever
# yoke, slide its upper half into the rib. Full housing length, built centred in Y at the origin.
floating_tenon = heal(_ctree_prism_y(0.0, TEN_LY0, TEN_Y1))   # built at absolute Y (seats at the -Y stop)
