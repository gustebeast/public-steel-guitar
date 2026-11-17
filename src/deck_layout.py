"""The deck and rail layout the direct instrument still reads from the v1 body.

Lifted out of src/top_plate.py, src/chassis.py and src/changer_bench.py (lead, 2026-11-17, v1
removal round 3): the fret field and its markers, the pickup region (cavity, jacks, the height
plate), the deck joint, the -Y rail's inner face and the wiring trough's section, and the ghosts
that bound the drive. Everything else of those modules went with the v1 instrument (git tag
v1-instrument).

Each value keeps its derivation where the chain is still this instrument's (dimensions, the
pickup, the string fan). Where it only existed because of the v1 body, the number is FROZEN at
the value it had, and says so.
"""

from __future__ import annotations

import functools
import math

import cadquery as cq

from . import dimensions as D
from . import pickup_mount as PM
from .helpers import box_at, cyl, heal
from cadkit import fitted_joint as FIT
from cadkit.fasteners import M4, M4_BUTTON_HEAD_H, cut_insert_bore

# ── the rails and the deck joint (from src/chassis.py) ─────────────────────────────────────
T        = D.RAIL_T                    # rail thickness across Y (20.0: the steel bar's channel
# THE -Y RAIL'S INNER FACE is motor_bank.RAIL_INNER_Y: string 10's motor back less the larger
# of what that motor and the Pi's USB-C plug need (MB.RAIL_BACK_CLR). Nothing climbs behind the
# motor any more -- its CAN drop leaves inside its own footprint -- so the old 4.8 pigtail gap
# (RAIL_GAP) is gone (user, 2026-10-29). The wall is continuous and UNCUT the full length of the
# instrument (user, 2026-10-29: "we can't cut the wall to make it fit"): anything that would
# reach past it moves the wall, never a pocket in it.
RAIL_INNER_Y = -105.05  # FROZEN, v1: chassis.RAIL_INNER_Y = MB.RAIL_INNER_Y (tag v1-instrument)
Y_LO     = RAIL_INNER_Y - T / 2        # the rail's centre
                                       # the deck panels slide out -X once the
                                       # (removable) keyhead endplate is off
TP_GZ0, TP_GZ1 = 0.0, D.DECK_TOP_Z     # deck plate z-plane: bottom rests on the rail
                                       # top (lowered to z0 here), top = playing surface
# DECK JOINT — a cadkit slide joint. The deck plate caps the rail
# (right-angle bend) and drops a tongue straight down into a groove milled
# in the rail top. The foot is wider than the mouth, so the wide foot can't pull up
# through the narrow mouth -> +Z retention (plates stay put when inverted). The
# inboard groove wall is what the rail bears against if the rails try to spread, so
# it also ties the rails in Y. The tongue runs along X -> plates still slide out -X.
# top_plate.py builds the matching tongue; the rail top is lowered to z0 in the deck
# X-span so the plate sits flush on top.
TP_TG_DEPTH    = 9 * D.BEAD             # 7.2: the reserved groove ZONE below the deck: the

# ── THE DECK JOINT IS THE FIT-TESTED MOUTH-UP PAIR (user, 2026-10-16) ──────────────────
# The deck panels print TOP-FACE-DOWN (their leadscrew head pockets open at the bed), so the
# tongue grows toward the nozzle off the panel's underside, and the rail builds +Z toward the
# groove's opening: joinery step 1's LAYER/LAYER MOUTH-UP pair, sized up to this site (plate 8
# B: neck 3.2, head 6.4, straight sides 2.4, a flat groove floor, end relief in the groove
# only). Plate 8 B1, 0.25: "ideal, low friction and wobble". The panel's underside rests on
# the rail top, so the seat is 0. Built by cadkit.fitted_joint.halves (step 4, 2026-11-03).
TP_TG_W    = 8 * D.BEAD                # 6.4 across the head
TP_TG_CLR  = 0.25                      # plate 8 B1
DECK_FIT   = {"neck": 4 * D.BEAD, "head": TP_TG_W, "side": 3 * D.BEAD}
_DECK_HOST_W = 10 * D.BEAD             # 8.0 the tongue's root slab, inside the rail's 10.4


@functools.lru_cache(maxsize=None)
def _deck_halves(length, drop=0.0):
    """(tongue, groove) of the deck joint, `length` along X, in the joint frame (X the slide,
    Y across, Z down from the panel's underside once _deck_tg turns it over)."""
    ten, cav, _S = FIT.halves("up", "down", TP_TG_CLR, length, 0.0, _DECK_HOST_W, size=DECK_FIT,
                              drop=drop)
    bb = cav.val().BoundingBox()
    assert bb.zmax <= TP_TG_DEPTH + 1e-6, (
        "the deck groove reaches %.2f, past the reserved zone TP_TG_DEPTH %.2f" % (bb.zmax, TP_TG_DEPTH))
    assert (T - 2 * bb.ymax) / 2 >= D.MIN_WALL_2P - 1e-6, (
        "deck groove leaves %.2f of rail wall per side, under the tier" % ((T - 2 * bb.ymax) / 2))
    return ten, cav


def _deck_tg(yc, x0, x1, mortise):
    """The deck joint at rail Y=yc over x0..x1 — mortise (the rail-top groove) or tenon
    (the panel's tongue; top_plate calls it). Rotated 180° about X so the joint's local
    +Z points DOWN: the tenon grows off the panel's underside into the rail."""
    L = (x1 - x0) + (2.0 if mortise else 0.0)
    s = _deck_halves(L, 1.0)[1] if mortise else _deck_halves(L)[0]
    return (s.rotate((0, 0, 0), (1, 0, 0), 180)
            .translate((x0 - (1.0 if mortise else 0.0), yc, TP_GZ0)))

# ── -Y rail WIRING TROUGH ─────────────────────────────────────────────────
# A trough standing OFF the -Y rail's inner face, above the motors, for the harness to be
# laid into. It REPLACES a channel that was cut 4.8 mm into this 10.4 mm wall for most of
# its length (user, 2026-09-21: "that reduces structural integrity of the instrument...
# have it extend out from the wall rather than cutting into it"). Right: the rail is the
# body's side beam, and a pocket along its middle trades beam depth for a cable tray. This
# costs only the tray's own material and leaves the wall whole.
#
# WHY THIS HEIGHT. The motors fan across the body -- only string 10's (back 2.0 off the
# wall) and string 9's (11.5 off) come near it -- and every motor top is at z -29.05
# (MOTOR_BELT_Z + MOTOR_SQ/2). The deck's retention groove owns the wall from z -6.4 up. The
# trough lives in the band between: floor at -28.0, lip top at -15.2.
# TWO BEADS LOWER THAN IT WAS (user, 2026-10-29: "the cable channel also may be able to move
# -z if its colliding with the UI board"). The UI board sits 1.0 off the narrowed wall and
# its encoder's tails reach z -16.2 over the trunk (brenner); the trunk's top was -16.2. Every
# lane is set off this floor, so all of it comes down 1.6 together: the top 1.6 under the
# tails, the floor still 1.05 over the motor tops (asserted in wiring).
#
# SECTION (Y-Z, extruded along X), and why each face is the angle it is -- the chassis
# prints +Z, so every face that looks down must be 45 or steeper:
#   * a 45 deg GUSSET under the floor, from the wall out to the lip, so the floor is never
#     a ledge over air;
#   * a vertical outer LIP, a printed wall like any other;
#   * a small NUB at the lip's top, reaching back toward the wall with a 45 deg underside,
#     so the mouth is narrower than the trough and a stuffed-in cable stays put.
WT_Y0 = Y_LO + T / 2                     # the rail's inner face (-116.35 at 10-29)
WT_D = 8 * D.BEAD                        # 6.4 out from the wall (outer lip face 6.4 in)
WT_ZF = -35 * D.BEAD                     # -28.0 floor top (gusset root at -34.4)
WT_H = 16 * D.BEAD                       # 12.8 lip height above the floor (top -15.2)


YL = RAIL_INNER_Y                       # -Y rail inner face (top_plate.YL)

# ── the deck: datum, panels, the pickup region, the fret field (from src/top_plate.py) ──────
TZ = D.DECK_TOP_Z                       # deck surface (top_plate.TZ = electronics.DECK_TOP), 6.4
BZ = TZ - 8 * D.BEAD                    # 6.4 deck, bottom at 0 = the chassis groove
# Deck X-extent, DERIVED from the endplates so it tracks them. The stack installs
# +X -> -X: the FIRST panel butts the bridge endplate FLUSH (no gap -- you push it home),
# then each panel keeps GAP clearance to the previous so the stack can't bind, and the
# LAST panel stops EP_TOP_CLR short of the keyhead face so the keyhead slides in past the
# seated stack. Fret lines are at absolute X, so this positioning makes every marker land
# true on its panel.
PX0 = D.BRIDGE_BASE_X0                  # +X deck end: FLUSH with the bridge endplate -X face
                                        # (-16.5); +Z held by the rail-top grooves
PX1 = -610.8000000000001  # FROZEN, v1: top_plate.PX1 = CH.KH_RAIL_X (tag v1-instrument)
                                        # (-610.6) -> the keyhead can slide in past it
GAP = 0.05                              # assembly clearance between consecutive panels

# ── band slots at the bridge end ─────────────────────────────────────────────
# (The optical pickup does NOT live here. It hangs from the bridge endplate's tie bar,
# firing DOWN at the strings -- see optical_pickup.py. That keeps the whole slot grid
# for the MAGNETIC pickup, which needs every millimetre of approach to the changer.)
BAND_W   = 20.0                        # one slot (band material width)
# SIX, NOT SEVEN: the -X-most slot was handed to the mid panel (user, 2026-09-29), which is
# what takes the SHOWN fillers from three to two. Everything downstream is derived from this
# number, so the one edit moves the region end, the mid panel's +X edge, the UI station that
# hangs off it and the coarse swap count together.
# THE COST IS ONE COARSE POSITION: N_POS below goes 4 -> 3, so the pickup's coarse reach
# toward the neck is 20.05 mm shorter. Its FINE adjustment is untouched (CLAMP = BAND_W/2
# still makes the coverage continuous), and the slot that went is the one furthest from the
# changer, which is the end of the range the magnetic pickup is least likely to want.
N_SLOTS  = 6                           # pickup-region slots
PITCH    = BAND_W + GAP                # slot pitch = band + the gap after it
SLOT_X   = [PX0 - i * PITCH for i in range(N_SLOTS + 1)]   # +X face of each slot
PIECE_SLOTS = 4                        # the pickup piece spans 4 slots (enlarged one slot so the
PIECE_SHOWN = 0                        # piece occupies slots [0 .. PIECE_SLOTS)
PIECE_X0 = SLOT_X[PIECE_SHOWN]
PIECE_X1 = PIECE_X0 - (PIECE_SLOTS * BAND_W + (PIECE_SLOTS - 1) * GAP)   # spans its slots
                                       # INCLUDING the 2 internal gaps it absorbs, so
                                       # swapping it for 3 fillers leaves the downstream
                                       # panels (UI, keyhead) put
REGION_X1 = SLOT_X[-1]                  # -X end of the band region (after the last gap)
# the two long panels behind the band region
MID_X0 = REGION_X1                      # carries the UI (string-10 deck band)

# ── THE MID/KEY SEAM, set by the KEYHEAD PANEL'S LENGTH ──────────────────────────
# The KEYHEAD panel is the long one now, at 312 beads = 249.60, just inside the 250 the bed
# really gives (user, 2026-09-29). Anchoring its LENGTH rather than the seam's position is
# the right way round for the same reason the seam beat the mid panel's length before: the
# thing under constraint is how much panel has to fit on a bed, and that is a length.
#
# ⚠ WHAT THIS TRADES. The seam lands at -361.15, in fret SPACE 10, and the three things
# that were fighting over it resolve like this:
#
#     MARKER-FREE   yes -- 10 % 12 = 10 carries no symbol, and the nearest marking is
#                   12.65 away. This is what the old -380.80 could not do; it sat 1.49
#                   off the fret-9 pentagon.
#     ON THE BED    yes, both: 215.79 and 249.60.
#     EVEN          NO. 33.81 apart, against the 5.49 the old seam gave. Evenness is the
#                   one that was given up, deliberately, and the balance assertion that
#                   used to stand here has gone with it rather than being loosened to a
#                   number that asserts nothing.
#
# It is 5.73 off space 10's own midpoint, because the midpoint (-355.42) would make the
# keyhead panel 255.33 and that is over the bed. "Halfway between two frets" and "250 max"
# cannot both hold in this space; the line clearances are 3.33 to fret 9 and 14.79 to
# fret 10, and _fret_positions drops any line within 0.8 of a panel end, so nothing is cut.
#
# The seam itself is NOT on the bead grid (451.44 beads) because it is now derived from
# PX1, a chassis datum that is not. The LENGTH is what is on the grid. If the seam's own
# position matters more later, 451 beads gives exactly 250.00 and 452 gives 249.20.
KEY_L  = 312 * D.BEAD                   # 249.60, the keyhead panel: the bed-limited one
KEY_X1 = PX1
KEY_X0 = KEY_X1 + KEY_L
MID_X1 = KEY_X0 + GAP
WALL      = 5 * D.NOZZLE_D                                 # 4.0 piece end walls (was 3.5)
OPEN_X0   = PIECE_X0 - WALL                                # +X opening edge (-21.0)
OPEN_X1   = PIECE_X1 + WALL                                # -X opening edge (-74.0)
OPEN_CTR  = (OPEN_X0 + OPEN_X1) / 2                        # -47.5
SKIRT_T   = 4 * D.NOZZLE_D                                 # 3.2 (was 3.0)

# ── pickup Y placement + EXTENDED -Y utility zone (user) ─────────────────────
# The pickup is placed by MAGNETIC coverage: its 88.9 MAGNETIC range must sit over
# string 1 (there's a ~6.35mm DEAD FRAME at each Y end, so coverage is reckoned against
# the magnetic range, NOT the 101.6 body edge -> the +Y body edge lands ~+50.1). The -Y
# side is a LONG UTILITY ZONE that runs well past the pickup so the -Y HEIGHT JACK sits
# CLEAR of the pickup, reached from +Z. NO tall +Y skirt (the +Y rail YH=+54.75 is 4.6mm
# off the body edge). (Y hold-down clamp REMOVED for now -- height adjustment only.)
PK_MAG_INSET = (PM.PK_L - PM.PK_MAG_L) / 2               # 6.35 dead frame at each Y end
PK_YP    = D.string_y(0) + 1.0 + PK_MAG_INSET            # +Y body edge (~+50.1); mag covers string 1
PK_YM    = PK_YP - PM.PK_L                                # DEMO Alumitone -Y edge (~-51.5), for the render only
PK_CTR_Y = (PK_YP + PK_YM) / 2                            # DEMO Alumitone centre Y (demo placement)
# Supported pickup LENGTH window. EVERY pickup butts the +Y wall (the magnetic datum), so a shorter
# pickup's -Y face sits further +Y; the -Y screw's reach is what still retains it. Its usable
# tip travel is GRUB_SWEEP, so the window is [PK_MAX_L - GRUB_SWEEP, PK_MAX_L]. PK_MAX_L is the ROOM size (cavity/plate/-Y grub face), set a hair ABOVE the Alumitone so
# 101.6 isn't at the exact edge (0.4 mm headroom, user); the sweep goes DOWN over the dense 10-string
# cluster (George L ~97, Steeltronics ~98, Bill Lawrence/Wilde 100, Lace/Wallace/Sentell 101.6). The
# 108 Sentell LS20 + 120.7 wide-10 stay out (they'd need a longer screw AND a still-bigger cavity).
PK_MAX_L      = 102.0                                     # longest supported pickup -> sizes the room
GRUB_SWEEP    = 5.5                                       # the retention screw's tip travel (RET_SCREW_L - RET_BOSS_L)
PK_MAX_YM     = PK_YP - PK_MAX_L                          # ROOM -Y edge = the longest pickup's -Y face (~-51.9)
YZONE    = 16.0                                           # -Y utility-zone depth beyond the pickup
HY_CLAMP = -PK_MAX_YM + YZONE                             # -Y skirt inner = extended room -Y edge (~+67.9)
# Z-plate the pickup slides on in X (fine tone) -- lifted/tilted by the 3 jacks:
# 2.0, NOT 2.4 (user, 2026-10-29: the deepest pickup reaches a 6 mm string gap in as little Z
# as possible). The plate is drawn at the bottom of its travel, and there its underside must not
# hang below the jack screws' tips (SKIRT_DEEP_BOT), which the pickup region spends anyway. At
# 2.4 it hung 0.33 below them and would have set the envelope by itself. The insert pocket still
# leaves 1.0 of plate under it (asserted below) -- and the plate hangs on its nuts, so that floor
# is what the load seats on, a pickup's weight.
ZPL_T    = 2.0
ZPL_TOP  = PM.PK_BOT                                      # pickup rests on the plate top
ZPL_BOT  = ZPL_TOP - ZPL_T
# ⚠ 5 BEADS, NOT 8, AND THE DECK IS RELIEVED OVER EACH BOSS (2026-09-30, swept not assumed:
# scratchpad sweep.py lifted the plate in 1 mm steps against both deck solids). At 6.4 the
# three bosses met the solid deck underside after 4.6 mm of the 7.0 the pickup window needs
# (PK_H 22 down to PK_H_MIN 15) -- 69-75 mm3 each at full travel, invisible to a gate that
# only sees the demo pose. The insert does not need the height: its 5.0 pocket now starts
# 4.0 up and runs 1.0 INTO the 2.4 plate, leaving 1.4 under it, and the plate hangs on its
# nuts so the load seats the insert rather than pulling it. With JACK_BOSS_RELIEF in the deck
# the plate travels 8.6 before anything touches.
BOSS_H         = 5 * D.BEAD       # 4.0 (was 6.4)                              # NUT boss height ABOVE the plate top (nut boss is on TOP now,
                                                 # so the plate BOTTOM stays flat -> prints -Z->+Z, user)
JACK_BOSS_RELIEF = 2 * D.BEAD                      # 1.6 blind pocket in the deck underside over each boss
JACK_MOUTH_Z   = ZPL_TOP + BOSS_H                  # plate NUT mouth = the boss TOP (screw threads down into it)
# The leadscrew is a real M4 BUTTON-HEAD cap screw (headed, hex-socket drive) captured in the
# deck: a counterbore seats the head, the shoulder bears on its floor, the shank threads down
# through the plate nut. Turning the head from +Z walks the plate up/down.
JACK_HEAD_D    = 7.6                               # M4 button-head cap screw head Ø (ISO 7380)
JACK_HEAD_H    = 2.2                               # button-head height
JACK_HEAD_Z    = TZ - (JACK_HEAD_H + 0.3)          # head SHOULDER (pocket floor) in the solid deck (=3.5)
HEAD_POCKET_D  = JACK_HEAD_D + 0.4                 # Ø8 head counterbore, opens at the bed (deck top TZ)
JACK_SCREW_L   = 20.0                              # NEW BOM part: M4×20 button-head leadscrew. 20 mm shank
SKIRT_DEEP_BOT = JACK_HEAD_Z - JACK_SCREW_L        # the jack screws' tips: the deepest thing the
                                                   # pickup region reserves anyway (-16.10)
# THE PICKUP PIECE'S ENVELOPE: the lowest it reaches anywhere in its travel. The screws are fixed
# in Z (heads captured in the deck), the plate is drawn at its lowest, and the skirt stops at the
# tips -- so it is the tips. Everything that sits under the piece (the motor bank's CAN tees as
# it slides out, the fret light) clears THIS, not a number of its own.
PIECE_Z_MIN = SKIRT_DEEP_BOT
# TOP-ACCESS at the PLATE's clear zones (pickup-agnostic): TWO +Y plate corners + ONE
# deep -Y. Equalise the two +Y = X LEVEL; the -Y jack = across-string tilt. The -Y jack is
# nudged slightly off-CENTRE (JACK_MX_OFF) to free the CENTRE for the retention setscrew --
# a plane is set by any 3 non-collinear points, so an off-centre tilt jack still levels fully.
PICKUP_X_NOM  = OPEN_CTR                          # nominal pickup centre X
# ⚠ 38 BEADS, NOT 39, AND THE ARM STOPS AT ITS BOSS (2026-09-30). At 31.2 the arm's outboard
# end stood 0.72 INSIDE each of the piece's end walls -- 37.24 mm3, carried as a DEFERRED
# overlap since the plate became a moving part. The jack cannot go far: its O9.2 boss has to
# stay outboard of a pickup slid X_SLIDE its way (boss inner edge 25.8 against 25.3). So it
# moves one bead in, and the arm ends at the boss's own radius instead of half a nub width
# past the screw -- 0.83 of air to the wall, which a part that travels needs.
JACK_INSET_X  = 38 * D.BEAD                       # 30.4: +Y jacks near the plate X-ends (toward the corners)
JACK_YP       = 57 * D.BEAD                        # 45.6: +Y corner jacks outboard of string 1, on the nubs
JACK_YM       = PK_MAX_YM - 13 * D.BEAD             # -Y jack deep in the -Y zone (~-62.3), below the room edge, on its nub
JACK_MX_OFF   = 12 * D.BEAD                        # 9.6 -Y jack X-nudge off centre: its boss clears the retention screw's HEAD by 1.2
JACK_POS      = [(PICKUP_X_NOM + JACK_INSET_X, JACK_YP),
                 (PICKUP_X_NOM - JACK_INSET_X, JACK_YP),
                 (PICKUP_X_NOM + JACK_MX_OFF, JACK_YM)]

# ── plate SHAPE (user): GREEN pickup-area prism + 3 RED nubs out to the screws ────
# The plate is JUST the usable pickup area (a green prism) plus nubs that reach the 3 jack
# nuts. Everywhere else the plate used to occupy is now SOLID DECK (reclaimed as coloured
# top surface) -- the deck cavity is only the pickup + the 3 screws.

# ── pickup RETENTION (user): +Y WALL + -Y SCREW lock the pickup to the PLATE only ─
# (so the plate still moves up/down freely). The pickup's +Y face butts a wall that rises
# from the plate; a horizontal M4 grub through a -Y boss pushes the pickup +Y against it.
RET_WALL_T = 3 * D.NOZZLE_D                        # 2.4 -Y wall room on the plate (was 2.0)
# The +Y WALL is 1.6, two beads (D.MIN_WALL_2P), not RET_WALL_T: the plate's +Y edge is its outer
# face and has to stay clear of the chassis wall, which came in to string 1's belt clamp (user,
# 2026-10-29). The wall still has to be there -- the grub clamps the pickup +Y against the PLATE;
# pressed against the chassis instead, it would pin the deck panel and it could not slide off.
RET_WALL_YP = D.MIN_WALL_2P
RET_WALL_H = 8.0                                   # +Y wall height above the plate top (enough to lock, not tall)
# ⚠ THE RETENTION SCREW IS AN M4 BUTTON HEAD, NOT A CUP-TIP GRUB (user, 2026-09-30:
# "everything should be M4 with 2.5mm hex" -- an M4 set screw takes a 2.0 key). A head changes
# three things a grub never has to care about:
#   * the head is O7.6 and turns just over the plate, so the axis stands 6 beads up: the head's
#     underside clears the plate top by 1.0 (at 4 beads it was 0.6 INTO it);
#   * the -Y jack's O9.2 boss has to stand outside the head's swing: JACK_MX_OFF 9.6;
#   * it is driven from -Y, through the piece's skirt.
# IT IS AN M4 x 20, a length the instrument already buys (user, 2026-10-07: fewer lengths on
# the BOM, the full sweep kept). The reach does not depend on the length: seated, the tip
# stands RET_SCREW_L - RET_BOSS_L = GRUB_SWEEP past the room's -Y edge, which is what the
# 96.5-102 pickup window is sized on, so the BOSS grew with the screw. What the length does
# set is where the HEAD is: with the longest pickup in, the tip is at the room edge and the
# head is RET_SCREW_L behind it, 0.8 OUTSIDE the skirt's outer face. So the screw passes
# THROUGH the skirt (RET_SLOT_*: head-wide, not key-wide) and the deck's relief runs on
# past the skirt over wherever the head can be (RET_HEAD_OUT).
RET_SCREW_L = 20.0                                 # M4 x 20 button (m4_button_20)
RET_SCREW_Z = ZPL_TOP + 6 * D.BEAD                 # 4.8 screw axis height (head clears the plate by 1.0)
RET_BOSS_L = RET_SCREW_L - GRUB_SWEEP              # 14.5 -Y screw boss length (Y): the insert pocket + its floor to the boss +Y
                                                   # face at PK_MAX_YM (the LONGEST supported pickup's -Y face).
                                                   # Shorter pickups butt the +Y wall, so their -Y face sits +Y of
                                                   # here and the grub protrudes across open cavity to reach it.
RET_SCREW_X = PICKUP_X_NOM                          # CENTRED (the -Y jack was nudged off centre to free it):
                                                   # a centred setscrew stays on the pickup across the FULL
                                                   # +/-X_SLIDE, unlike the old +14 offset (rode off the +X
                                                   # edge in the last ~0.7 mm of -X slide). The setscrew boss
                                                   # + jack nub are one part (the plate) so they overlap
                                                   # freely; only the screw/insert dummies keep JACK_MX_OFF.
# The -Y grub is an M4 cup-tip SET SCREW threading a heat-set insert (cadkit set-screw bore), so the
# boss ceiling must clear the Ø6 insert pocket by MIN_WALL_2P (2 beads) on EVERY side (the reported
# thin-ceiling fix). Ceiling = axis + pocket radius + MIN_WALL_2P.
RET_HEAD_OUT  = PK_MAX_YM - RET_SCREW_L - M4_BUTTON_HEAD_H   # -74.1: the head's far face, backed
                                                   # right out against the LONGEST pickup
RET_RELIEF_Y0 = RET_HEAD_OUT - D.BEAD              # from a bead past the head's furthest reach ...
RET_RELIEF_Y1 = PK_MAX_YM                          # ... to the boss's +Y face (the room edge)
RET_RELIEF_Z1 = TZ - D.MIN_WALL                    # leaves a ONE-bead skin: at two the boss met it
                                                   # after 6.4 of the 7.0 travel (swept)
RET_SLOT_W    = 11 * D.BEAD                        # 8.8: the O7.6 head + 0.6 each side
RET_SLOT_Z0   = RET_SCREW_Z - RET_SLOT_W / 2       # slot floor, half a slot under the axis (the
RET_BOSS_TOP_Z = RET_SCREW_Z + M4.insert_pilot_d / 2 + D.MIN_WALL_2P   # 1.6 (2-bead quality floor) over the bore
X_SLIDE   = 6.0                                    # pickup X-position room on the plate (+/-)
PLATE_X   = PM.PK_W + 2 * X_SLIDE                  # green X (pickup + slide) ~50.6
PLATE_Y0  = PK_MAX_YM - RET_WALL_T                # green -Y edge (LONGEST pickup + wall room)
PLATE_Y1  = PK_YP + RET_WALL_YP                   # green +Y edge = the +Y wall's outer face
PLATE_Y   = PLATE_Y1 - PLATE_Y0                   # ~105.2
PLATE_CTR_Y = (PLATE_Y0 + PLATE_Y1) / 2           # plate/cavity centre (room grows -Y, not toward the wall)
# THE PICKUP'S LEAD LEAVES ITS UNDERSIDE, SO THE PLATE IT RESTS ON NEEDS A WAY THROUGH.
# A slot rather than a hole because the pickup slides +/-X_SLIDE on the plate and takes its
# lead with it. It sits under the pickup's own -Y end at every slide position, so the pickup
# lids it and the plate stays a light block. wiring.py draws the lead through this Y.
LEAD_SLOT_W = 4 * D.BEAD                           # 3.2: the 2.4 lead + a 0.4 bead-half each side
LEAD_SLOT_L = 2 * X_SLIDE + LEAD_SLOT_W            # the lead's whole X travel
LEAD_SLOT_Y = PK_YM + 5 * D.BEAD                   # 4.0 in from the demo pickup's -Y edge
NUB_W     = 14 * D.NOZZLE_D                        # 11.2 (was 11.0) nub/arm width (>= boss Ø8)
RET_RELIEF_W  = NUB_W + 2 * D.BEAD                 # the boss (NUB_W) + a bead of air each side
CAVITY_X  = PLATE_X + 1.5                          # pickup cavity in the deck (green + clearance)
CAVITY_Y  = PLATE_Y + 1.5
# LIGHT FLANGE (user, 2026-09-17): the plate's BOTTOM reaches this far PAST the deck opening on
# every side, so it laps the deck's underside instead of stopping 0.75 short of the opening --
# the gap round its edge was a clear line of sight from the lit body out through the cavity.
# 2.0 is what the room allows: probed through the plate's whole travel band, the ring outside
# the cavity is clear of everything at +2.0 and hits the chassis at +3.0. It costs no lift
# either -- the flange tops out 2.5 below the deck's underside at the jacks' highest (the boss
# top reaches the head shoulder first, 8.53 up), so it never has to enter the opening.
LIGHT_FLANGE = 2.0
MARKER_FRETS = {3, 5, 7, 9, 12, 15, 17, 19, 21, 24}

# ── fret lines + fretboard border as a MATERIAL split, not an engraving ──────
FRET_T  = 1.6      # colour-layer thickness = embossed inlay height (Z)
INLAY_W = 2.4      # SHARED in-plane width: every transparent fret line AND the border-frame band
MIN_WEB = D.MIN_WALL   # smallest colour web left between lines (1-bead floor; stops dense micro-lines at the bridge)
# border X: the fretted length — from the bridge end of the fretboard (just -X of the pickup region) to
# the nut/keyhead end. Absolute coords; _split gives each panel its portion so the frame is continuous.
FRET_AREA_X0 = SLOT_X[PIECE_SHOWN + PIECE_SLOTS]   # +X (bridge) end of the FRET FIELD (lines + markers)
# The BORDER's side bands run further +X than the field, all the way to the deck's bridge end, so the
# band-region fillers carry the same top/bottom border as the rest of the fretboard (user). Those slots
# only ever hold the pickup piece OR a filler, and whichever fillers aren't covered are installed — an
# unbordered band there read as the fretboard just stopping short of the bridge.
BORDER_X0 = PX0                                    # +X (bridge) end of the border side bands


def _string_half_span(x):
    """Half the Y between the two outer strings at deck X (linear nut->bridge fan)."""
    t = (x - D.NUT_BLOCK_X) / (D.BRIDGE_X - D.NUT_BLOCK_X)   # 0 at nut, 1 at the bridge/changer
    return D.nut_y(0) + (D.string_y(0) - D.nut_y(0)) * t


BORDER_HY = _string_half_span(BORDER_X0)      # box half-Y = outer-string half-span at the frame's WIDEST
                                              # (+X) edge -- which is BORDER_X0, not FRET_AREA_X0, now that
                                              # the side bands run on to the bridge end. Datuming to the
                                              # field edge instead would leave the outer strings crossing
                                              # OUT over the band across the last ~80 mm of fan.
FRET_HY   = BORDER_HY - INLAY_W               # frets end one border-width short of the box edge


def _fret_positions(x0, x1):
    """(n, absolute X) of every 12-TET fret line landing on panel x0(+X)..x1 AND inside the fret
    FIELD: fret n at nut + scale*(1 - 2^(-n/12)) — they compress toward the bridge.

    The field ends at FRET_AREA_X0. Frets run monotonically +X toward the bridge, so passing it
    ends the walk. Without that clamp this emitted any fret that merely LANDED on a panel, which
    put frets 33-35 on the band-region fillers — lines +X of the fretboard, in the region the
    pickup piece occupies. Those panels get the BORDER only (user)."""
    nut = D.NUT_BLOCK_X
    scale = D.BRIDGE_X - nut                     # full speaking length (nut->bridge)
    out, n = [], 1
    while True:
        fx = nut + scale * (1 - 2 ** (-n / 12.0))
        nxt = nut + scale * (1 - 2 ** (-(n + 1) / 12.0))
        if fx > FRET_AREA_X0 or nxt - fx < INLAY_W + MIN_WEB:
            break
        if x1 + 0.8 < fx < x0 - 0.8:
            out.append((n, fx))
        n += 1
    return out

# ── fret-position MARKERS (between the lines, not on them) ───────────────────
# Different symbols mark the frets, keyed by the fret's position in the octave (n % 12) and REPEATING
# every octave: circle, triangle, square, pentagon, and a 4-circle octave marker (12 & 24).
MARK_D     = 6 * D.BEAD                # 4.8 marker circumscribed size
MARK_SHAPE = {3: "circle", 5: "triangle", 7: "square", 9: "pentagon", 0: "quad"}


def _fret_x(n):
    return D.NUT_BLOCK_X + (D.BRIDGE_X - D.NUT_BLOCK_X) * (1 - 2 ** (-n / 12.0))


def _mark_x(n):
    return (_fret_x(n) + _fret_x(n - 1)) / 2        # the centre of the space behind fret n


def _reg_prism(nsides, r, x, ang0):
    """Regular nsides polygon, circumradius r, centred at (x, 0), first vertex at ang0, in the colour band."""
    pts = [(x + r * math.cos(ang0 + 2 * math.pi * k / nsides),
            r * math.sin(ang0 + 2 * math.pi * k / nsides)) for k in range(nsides)]
    verts = [cq.Vector(px, py, TZ - FRET_T) for px, py in pts]
    face = cq.Face.makeFromWires(cq.Wire.makePolygon(verts + [verts[0]]))
    return cq.Workplane("XY").add(cq.Solid.extrudeLinear(face, cq.Vector(0, 0, FRET_T)))


def _marker(n):
    """One fret marker at its space, shaped by n % 12 (see MARK_SHAPE), embossed in the colour band."""
    x, r = _mark_x(n), MARK_D / 2
    shape = MARK_SHAPE[n % 12]
    if shape == "circle":
        return cyl(MARK_D, FRET_T, z=TZ - FRET_T).translate((x, 0, 0))
    if shape == "triangle":
        return _reg_prism(3, r + 0.5, x, 0.0)                       # a vertex toward +X (bridge)
    if shape == "square":
        return box_at(MARK_D * 0.85, MARK_D * 0.85, FRET_T, x=x, y=0.0, z=TZ - FRET_T / 2)
    if shape == "pentagon":
        return _reg_prism(5, r + 0.5, x, math.pi / 2)               # a vertex toward +Y
    out = None                                                      # "quad" octave marker: 4 circles across Y
    for i in range(4):
        c = cyl(MARK_D * 0.5, FRET_T, z=TZ - FRET_T).translate((x, (i - 1.5) * 3.0, 0))
        out = c if out is None else out.union(c)
    return out


# PRINT ORIENTATION (user's convention: the record, declared once per part, and the hole
# cutters read it so every hole is shaped for the way its part actually prints).
PIECE_UP = (0.0, 0.0, -1.0)     # the DECK pieces print deck-DOWN: the top face (TZ) is on the


def _pickup_zplate():
    """The height plate: a GREEN pickup-area prism (the pickup rests on it; X-slide room)
    plus 3 NUBS reaching the leadscrew NUTS (user's green+red shape). PRINTS -Z->+Z with a
    FLAT BOTTOM (user): every boss is on TOP -- the nut bosses stand UP (insert pocket down
    from the boss top; the screw tail passes through a Ø4.4 hole in the flat plate). RETENTION
    (user): a +Y WALL the pickup butts + a -Y horizontal grub that pushes it +Y against the
    wall, locking the pickup to the PLATE only (so the plate still travels)."""
    # the prism is the DECK OPENING plus LIGHT_FLANGE round -Y/-X/+X (+Y stops at the wall), not the pickup's own footprint:
    # the pickup only needs PLATE_X x PLATE_Y to rest and slide on, but the plate is also the
    # lid over a lit body, and light does not care where the pickup ends (user)
    fy0 = PLATE_CTR_Y - CAVITY_Y / 2 - LIGHT_FLANGE    # -Y: the flange laps the deck
    plate = box_at(CAVITY_X + 2 * LIGHT_FLANGE, PLATE_Y1 - fy0, ZPL_T,   # +Y: no flange
                   x=PICKUP_X_NOM, y=(fy0 + PLATE_Y1) / 2, z=(ZPL_BOT + ZPL_TOP) / 2)
    for jx, jy in JACK_POS:
        dx, dy = jx - PICKUP_X_NOM, jy - PLATE_CTR_Y
        if abs(dx) - PLATE_X / 2 >= abs(dy) - PLATE_Y / 2:      # jack juts past the green in X -> X-arm
            sg = 1.0 if dx > 0 else -1.0
            xe = PICKUP_X_NOM + sg * PLATE_X / 2
            xa, xb = xe - sg * NUB_W / 2, jx + sg * M4.boss_od / 2    # root in the plate .. boss edge
            plate = plate.union(box_at(abs(xb - xa), NUB_W, ZPL_T,
                                       x=(xa + xb) / 2, y=jy, z=(ZPL_BOT + ZPL_TOP) / 2))
        else:                                                  # -> Y-arm
            ye = PLATE_Y1 if dy > 0 else PLATE_Y0
            plate = plate.union(box_at(NUB_W, abs(jy - ye) + NUB_W, ZPL_T,
                                       x=jx, y=(jy + ye) / 2, z=(ZPL_BOT + ZPL_TOP) / 2))
        # LEADSCREW NUT boss ON TOP (flat plate bottom): Ø8 boss up from the plate, Ø6×5
        # insert pocket down from the boss top, Ø4.4 screw-tail clearance on through the plate.
        plate = plate.union(cyl(M4.boss_od, BOSS_H, z=ZPL_TOP).translate((jx, jy, 0.0)))
        plate = plate.cut(cyl(M4.insert_pilot_d, M4.insert_depth + 0.6,
                              z=JACK_MOUTH_Z - M4.insert_depth).translate((jx, jy, 0.0)))
        plate = plate.cut(cyl(M4.shaft_clr_d, (JACK_MOUTH_Z - M4.insert_depth) - (ZPL_BOT - 2),
                              z=ZPL_BOT - 2).translate((jx, jy, 0.0)))
    # +Y RETENTION WALL (rises from the plate top; the pickup +Y face butts its -Y face)
    plate = plate.union(box_at(PM.PK_W, RET_WALL_YP, RET_WALL_H,
                               x=PICKUP_X_NOM, y=PK_YP + RET_WALL_YP / 2,
                               z=ZPL_TOP + RET_WALL_H / 2))
    # -Y RETENTION grub boss: a pedestal rising from the plate at the LONGEST supported pickup's -Y edge
    # (PK_MAX_YM), hosting a HORIZONTAL M4 heat-set insert (cadkit set-screw bore -> a cup-tip grub, which
    # must never self-tap). The grub pushes the pickup +Y against the wall; threading it in/out lets its
    # tip meet any pickup in the [PK_MIN_L, PK_MAX_L] window (its -Y face floats +Y for shorter pickups).
    # The pedestal ceiling reaches RET_BOSS_TOP_Z so >= MIN_WALL_2P (1.6) rings the Ø6 pocket every side.
    ret_face_y = PK_MAX_YM - RET_BOSS_L               # -Y outer face = the insert-entry (grub) face
    plate = plate.union(box_at(NUB_W, RET_BOSS_L, RET_BOSS_TOP_Z - ZPL_BOT,
                               x=RET_SCREW_X, y=(ret_face_y + PK_MAX_YM) / 2,
                               z=(ZPL_BOT + RET_BOSS_TOP_Z) / 2))
    plate = cut_insert_bore(M4, plate, (RET_SCREW_X, ret_face_y, RET_SCREW_Z), (0, 1, 0),
                            clr_len=RET_BOSS_L - M4.insert_depth + 1.0,
                            reason="set screw: -Y pickup-retention grub, must not self-tap")
    # the lead slot, LAST: every union above would refill it (see LEAD_SLOT_W)
    plate = plate.cut(box_at(LEAD_SLOT_L, LEAD_SLOT_W, ZPL_T + 2.0,
                             x=PICKUP_X_NOM, y=LEAD_SLOT_Y, z=(ZPL_BOT + ZPL_TOP) / 2))
    return plate


def __getattr__(name):
    """pickup_zplate is built on first use, not at import (top_plate built it at import)."""
    if name == "pickup_zplate":
        v = globals()["pickup_zplate"] = heal(_pickup_zplate())
        return v
    raise AttributeError(name)

# ── the ghosts: the instrument's limits (from src/changer_bench.py) ───────────────────────
DECK_UNDER = -3.2                                   # world: nothing of the drive above this (x < -20)
GHOST_Y_LO, GHOST_Y_HI = -116.35, 54.75                         # the rails' inner faces (motor_bank, chassis)
KEYHEAD_X = D.KEYHEAD_INBOARD_X                     # -607.8
BODY_BOT_NOW = -81.8                                # today's bottom (the chassis bed, measured)

# ── ghosts: the instrument's limits ─────────────────────────────────────────────────────────
PICKUP_GHOST = ((-74.0, -21.0), (-51.9, 50.1), (-20.0, 7.97))   # OPEN_X, PK_MAX_YM..PK_YP,
                                                                # the Z-plate's foot..PK_TOP


def ghosts(y_hi: float = None) -> list:
    """The instrument's limits; y_hi moves the +Y rail (the direct bench widens it)."""
    Y_HI = GHOST_Y_HI if y_hi is None else y_hi
    (x0, x1), (y0, y1), (z0, z1) = PICKUP_GHOST
    g = [("ghost_pickup", box_at(x1 - x0, y1 - y0, z1 - z0, x=(x0 + x1) / 2, y=(y0 + y1) / 2,
                                 z=(z0 + z1) / 2))]
    dx0, dx1 = KEYHEAD_X, -21.0                      # the deck, keyhead to the changer
    g.append(("ghost_deck", box_at(dx1 - dx0, Y_HI - GHOST_Y_LO, 9.6, x=(dx0 + dx1) / 2,
                                   y=(Y_HI + GHOST_Y_LO) / 2, z=DECK_UNDER + 4.8)))
    for nm, (a, b) in (("ghost_wall_hi", (Y_HI, Y_HI + 20.0)), ("ghost_wall_lo", (GHOST_Y_LO - 20.0, GHOST_Y_LO))):
        g.append((nm, box_at(-KEYHEAD_X - 21.0, b - a, 9.6 - BODY_BOT_NOW, x=(KEYHEAD_X - 21.0) / 2,
                             y=(a + b) / 2, z=(9.6 + BODY_BOT_NOW) / 2)))
    g.append(("ghost_keyhead", box_at(40.0, Y_HI - GHOST_Y_LO, 100.0, x=KEYHEAD_X - 20.0,
                                      y=(Y_HI + GHOST_Y_LO) / 2, z=-40.0)))
    g.append(("ghost_bottom_now", box_at(-KEYHEAD_X + 60.0, Y_HI - GHOST_Y_LO, 0.4, x=KEYHEAD_X / 2 + 30,
                                         y=(Y_HI + GHOST_Y_LO) / 2, z=BODY_BOT_NOW - 0.2)))
    return g
