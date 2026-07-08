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
HS_BODY_LX = 5.0                    # piston body length in X (rides the channel; long enough not to cock)
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
HS_TH_PITCH     = 2.0               # self-supporting 45deg thread pitch (whole-turn engagement)
HS_TH_DEPTH     = 0.75              # flank depth <= pitch/2 (=1.0, margin kept); deeper flanks = more grip/prevailing torque
HS_TH_MINOR     = HS_BSTOP_OD - 2 * HS_TH_DEPTH   # 8.0 -> wall to the Ø5 bore = 1.5mm
HS_TH_CLR       = 0.4               # diametral thread clearance on the MALE side (TIGHTER than the 0.8 tested loose fit)
HS_BSTOP_ENGAGE = 4.0               # engagement in the boss = 2 turns (the leg sits 1.44mm behind -> can't go deeper)
HS_BSTOP_FLANGE = 0.5               # +X drive flange (drive slots on its face; thin so the total extent clears the leg)
HS_DRAG_LX, HS_DRAG_SEAT, HS_DRAG_BULGE = 6.0, 1.5, 0.4  # TPU drag: X length, wall-recess depth, interference into lane
HS_HOUS_BACK = HS_BACK_X + HS_BSTOP_ENGAGE   # housing boss depth = engagement (no extra -- preserves the leg clearance)

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
        _drag = cart_drag if dy == 0 else cart_drag.mirror("XZ")
        out.append((f"{nm}_cart_drag", feel_place(_drag.translate((dx, 0, 0)))))
    # (no travel-stop screw: the +Z-cam-era stop boss was removed -- see _housing)
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


def _cam_swept(step=2.0, extra_deg=3.0):
    r"""Union of the lever ARM's near-axle (cam) region swept 0..THROW+extra about the +Y axle, grown by
    the slide clearance. Cut this from the cartridge front-bottom and the housing floor below it so the
    swinging arm never plows into them. Only the Z>-40 region is built -- the long paddle sweeps open air
    below the guitar. Built in the placed (final) frame (the arm lives there); feel_unplace() maps it into
    a cartridge PART's own build frame."""
    grow = HS_CLR                                                   # +0.4 clearance around the arm envelope
    hub = cyl_y(HUB_D + 2 * grow, 2 * LEVER_HW, y0=-LEVER_HW)
    arm = box_at(ARM_TX + 2 * grow, 2 * LEVER_HW, 40.0, x=0, y=HUB_YC, z=-20.0 + 2.5)
    cam = hub.union(arm)                                            # lobes sit inside this envelope
    swept = cam
    a = step
    while a <= THROW + extra_deg + 1e-9:
        swept = swept.union(cam.rotate((0, 0, 0), (0, 1, 0), a))
        a += step
    return heal(swept)


_CAM_SWEPT = _cam_swept()                            # built once (module import); reused for every relief cut


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
    # rear M4 heat-set insert (tension screw, opens +X) + Ø4.4 shaft clearance from the insert to the
    # guide-post cup face: the screw threads the insert and its cup pushes the guide post -> coil preload
    base = _insert_pocket(base, (HS_BACK_X, HS_YC, HS_Z), (0, 1, 0), -90)
    base = base.cut(cyl(SCREW_CLR, HS_BACK_X - HS_GPOST_BX, z=HS_GPOST_BX)
                    .rotate((0, 0, 0), (0, 1, 0), 90).translate((0, HS_YC, HS_Z)))
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
    from threads import cut_thread                                              # noqa: E402 (freecad/ on sys.path)
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
    r"""The housing pocket for one cartridge: a plain rectangular slot (flat floor + flat ceiling), CLR
    bigger than the cartridge all round. The FLOOR sits at the piston underside -- it is the -Z retaining
    wall for the open-bottomed cartridge. The cartridge slides in X and is jammed against the ceiling by the
    vertical clamp."""
    z0, z1 = HS_FLOOR_Z - HS_CLR, HS_CART_Z1 + HS_CLR
    return box_at(x1 - x0, 2 * hs_pocket_hw(), z1 - z0, x=(x0 + x1) / 2, y=yc, z=(z0 + z1) / 2)


def _hs_clamp_pt(yc, dx):
    r"""Point under the cartridge's INBOARD SIDE WALL (toward the centre gap), in the coil-bay X (back of the
    swinging arm's reach, clear of the open channel AND the rear tension insert), where a VERTICAL clamp
    screw presses UP from below -- jamming the cartridge cap against the pocket ceiling to lock the slid X."""
    wall_off = HS_CH_WY / 2 + HS_WALL / 2                       # side-wall centre offset from yc
    inboard = yc - (1 if yc > 0 else -1) * wall_off            # the wall facing the centre gap
    return ((HS_BODY_BX + HS_GPOST_BX) / 2 + dx, inboard, HS_FLOOR_Z)


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
    r"""The housing SHELL around one cartridge pocket: a rectangular block, HS_HOUS_WALL thick on ALL SIX
    faces of the pocket (floor, ceiling, sides). Cut _hs_pocket() from this to leave the shell -- a flat
    floor shelf under the cartridge (the -Z retaining wall for the open-bottomed cartridge; relieved to
    open air at the front where the arm sweeps) + side walls + ceiling. Floor == ceiling thickness (both
    HS_HOUS_WALL) -- symmetric, so the -Z floor is a clean 0.8-multiple like every other housing wall."""
    hw = hs_pocket_hw()
    t = HS_HOUS_WALL
    z_bot, z_top = (HS_FLOOR_Z - HS_CLR) - t, (HS_CART_Z1 + HS_CLR) + t     # pocket floor/ceiling ± one wall
    return box_at(x1 - x0, 2 * (hw + t), z_top - z_bot, x=(x0 + x1) / 2, y=yc, z=(z_bot + z_top) / 2)


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
    # small Ø8 thrust bosses just inboard of each wall: the uniform ±LEVER_HW lever's hub bears on this
    # RING for low-friction Y location (a small annulus, not the whole hub face on the wall). PIVOT_CLR
    # running gap. The pin still carries the radial load in the bearings; these only locate Y.
    _bl = WP_Y0 - (LEVER_HW + PIVOT_CLR)
    w = w.union(cyl_y(PIVOT_BOSS_D, _bl, y0=WN_Y1))                         # -Y boss (-12 -> -10.2)
    w = w.union(cyl_y(PIVOT_BOSS_D, _bl, y0=LEVER_HW + PIVOT_CLR))          # +Y boss (10.2 -> 12)
    w = w.cut(cyl_y(AXLE_D + 1.0, 2 * WP_Y0, y0=WN_Y1))                     # axle bore through the bosses
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
    w = w.cut(box_at(2 * SWING_X + 4, cw, slot_h, x=0, y=HUB_YC,          # cam swing slot (now -Z, around
                     z=-(slot_h / 2 + PIVOT_BOSS_D / 2 + 0.5)))          #   the -Z lobe; clears the bosses)
    # SYMMETRIC single prism: BOTH slots run to the same backmost (retracted) X (dx = HS_SETBACK), so the
    # housing is one uniform prism -- the MAIN vs HALF-STOP distinction is purely where you set that slot's
    # hollow back-stop screw (either cartridge can go in either slot). The forward-set (main) cartridge
    # leaves ~HS_SETBACK of empty pocket behind it = its screw travel.
    for dy in (MAIN_YC - HS_YC, 0.0):
        dx = HS_SETBACK
        yc  = HS_YC + dy
        bx0, bx1 = HS_POCKET_X0 + dx, HS_HOUS_BACK + dx
        # constant-wall shell (/\ bottom parallels the pocket /\) + the /\ pocket cut (self-supporting,
        # no floor-bridge overhang); the cartridge front cantilevers -X of HS_POCKET_X0 into the swing slot
        w = w.union(feel_place(_hs_block(yc, bx0, bx1)))                # block now runs +X into the back-stop boss
        w = w.cut(feel_place(_hs_pocket(yc, bx0, HS_BACK_X + dx)))      # pocket STOPS at the cartridge back (boss stays solid)
        # (the HOLLOW back-stop's FEMALE thread is cut into this solid boss AFTER heal -- threads must be cut
        #  last & alone and never healed; see the end of _housing)
        # TPU drag-pad seat: a shallow recess in the OUTBOARD pocket wall over the coil bay (solid region);
        # the pad presses out of it onto the cartridge for light transport-drift friction.
        _sgn = 1.0 if yc > 0 else -1.0
        _yw = yc + _sgn * hs_pocket_hw()                          # pocket wall inner face
        _ys = yc + _sgn * (hs_pocket_hw() + HS_DRAG_SEAT)         # recess back (into the wall)
        w = w.cut(feel_place(box_at(HS_DRAG_LX + 0.4, abs(_ys - _yw), HS_PISTON_WZ + 0.4,
                                    x=_drag_seat_xc(dx), y=(_yw + _ys) / 2, z=HS_Z)))
    # CENTRE-WALL removal: each pocket keeps a full HS_HOUS_WALL on its INBOARD side, but the two
    # cartridges only leave a ~0.6mm gap between them -- so those two inboard walls merge into one solid
    # central slab that BOTH cartridges clip into by ~2.3mm each. It isn't a printable wall anyway. Cut it
    # out in the pocket Z-band only: the floor shelf below (the -Z piston retainer) and the cap above stay,
    # now tying the two halves into one span. The pistons sit at |Y| >= HS_PISTON_WY/2 = clear of the
    # centre, so no piston loses -Z support. Skip if the cartridges are far enough apart to leave no wall.
    _clr_hw = (hs_pocket_hw() + HS_HOUS_WALL) - HS_YC + 0.1
    if _clr_hw > 0:
        _cx0, _cx1 = HS_POCKET_X0, HS_BACK_X + HS_SETBACK            # span both cartridges (HS slid +X); stop at the back-stop boss
        _cz0, _cz1 = HS_FLOOR_Z - HS_CLR, HS_CART_Z1 + HS_CLR        # pocket void Z (floor/cap left intact)
        w = w.cut(feel_place(box_at(_cx1 - _cx0, 2 * _clr_hw, _cz1 - _cz0,
                                    x=(_cx0 + _cx1) / 2, y=0.0, z=(_cz0 + _cz1) / 2)))
    # front-bottom RELIEF: open the housing floor below each cartridge FRONT where the swinging arm
    # sweeps (X ~ -10..-18, the front ~8mm) so the arm clears. The clamp, coil bay and pocket back
    # (X < -20) are untouched -- the arm never reaches them. Cut BEFORE the stop boss (whose cup is
    # meant to sit in the cam's path). _CAM_SWEPT is already in the placed frame.
    w = w.cut(_CAM_SWEPT)
    # (No travel-stop boss here: the old central stop-screw boss was sized for the +Z cam PLATE and, in the
    #  -Z arm-as-cam layout, its block sat right in the arm's swing path -- it's removed. A hard stop for
    #  the new geometry can be added later if wanted; for now throw is bounded by clearance / the sensor.)
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
    w = heal(w)                                                     # heal EVERYTHING except the threads...
    # ...then cut the two FEMALE back-stop threads LAST and ALONE (thread rules: clean=False, and NEVER
    # heal a threaded part). Nominal thread; the printed screw carries the clearance (HS_TH_CLR). A short
    # nut cutter (2 turns) per cartridge, mapped into the -Z/-X placed boss by feel_place.
    from threads import threaded_rod                                # noqa: E402  (freecad/ on sys.path)
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
    body = body.cut(cyl_y(AXLE_D + 0.05, 2 * LEVER_HW + 2, y0=-LEVER_HW - 1))   # axle bore
    return heal(body)


knee_housing = _housing()
knee_lever = _lever()
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
# the FLOATING TENON: a separate printed rail (one per rib); glue its lower half into the lever
# yoke, slide its upper half into the rib. Full housing length, built centred in Y at the origin.
floating_tenon = heal(_ctree_prism_y(0.0, TEN_LY0, TEN_Y1))   # built at absolute Y (seats at the -Y stop)
