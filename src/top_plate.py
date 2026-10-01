"""Removable top deck — swappable fret-marked BANDS + a pickup-cover piece.

Roles: (1) fret-position lines for the player; (2) dust cover over the motors +
electronics; (3) sound damping; (4) OLED + joystick mount; (5) hand rest; (6) the
pickup carrier.

MULTI-MATERIAL: every panel is TWO aligned parts printed as ONE object (the
ha-keypad keycaps/keycaps_text pattern): `top_plate_N` — the TRANSPARENT PCTG
base (full body below the colour line, plus the fret lines + marker dots
EMBOSSED up to the deck top, so bay light glows through the full plate) — and
`top_plate_N_color` — the COLOUR PCTG layer (the top FRET_T band between the
lines; exact complement, flush top). Same origin; assign one filament per part
in the slicer. BOTH parts are PCTG (never glass-filled): the deck is the
player's forearm rest, and abrasion slowly exposes fiber ends on GF surfaces —
plus same-resin pairs weld and purge cleanest.

Form: the deck is a STACK of panels that ride a GROOVE in both rail inner faces
(a tongue down each Y edge -> can't fall when the instrument is inverted) and
pull straight out -X for service (after the keyhead endplate + nut block come
off; the bridge endplate + a chassis stop ledge cap the +X end). The whole stack
is trapped between that +X ledge and the keyhead endplate, so no panel needs to
latch and none can slide out on its own.

The bridge end is divided into BAND_W-wide slots. A 3-slot PICKUP PIECE carries
the pickup: the pickup pokes up through an opening, depending side skirts form a
channel, and two clamp bolts in X-slots give +/-CLAMP mm of fine X-adjust. The
remaining slot(s) take plain fret-marked FILLER bands. Swapping which slots hold
the piece coarse-moves the pickup (tone: bridge<->neck); the clamp covers every
position in between -> continuous reach (50 mm spec min is comfortably inside).
Because the pickup region is always the same total width, the UI + keyhead
panels downstream never shift.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from . import electronics as EL
from . import pickup_mount as PM
from . import ui_panel as UIP
from .helpers import box_at, cyl, heal
from cadkit.fasteners import M4, cut_counterbore, cut_insert_bore

YL = CH.Y_LO + CH.T / 2                 # -Y rail inner face (-128.75)
YH = CH.Y_HI - CH.T / 2                 # +Y rail inner face (+54.75)
BY0 = CH.Y_LO - CH.T / 2                # deck cap -Y edge (-Y rail OUTER face)
BY1 = CH.Y_HI + CH.T / 2                # deck cap +Y edge (+Y rail OUTER face)
TZ = EL.DECK_TOP                        # deck surface = D.DECK_TOP_Z (+6.4)
BZ = TZ - 8 * D.BEAD                    # 6.4 deck, bottom at 0 = the chassis groove
                                        # plane TP_GZ0 (the old 6.0 left a 0.4 gap
                                        # under the plate once the datum snapped)

# Deck joint: each plate CAPS both rails and drops a vertical DOVETAIL tongue down
# the rail centre-line into a rail-top groove (chassis.py). Wide foot, narrow mouth
# -> +Z retention (plates can't fall out inverted) AND a Y-tie (the inboard groove
# wall stops the rails spreading). The tongue runs along X -> plates slide out -X.

# Deck X-extent, DERIVED from the endplates so it tracks them. The stack installs
# +X -> -X: the FIRST panel butts the bridge endplate FLUSH (no gap -- you push it home),
# then each panel keeps GAP clearance to the previous so the stack can't bind, and the
# LAST panel stops EP_TOP_CLR short of the keyhead face so the keyhead slides in past the
# seated stack. Fret lines are at absolute X, so this positioning makes every marker land
# true on its panel.
PX0 = D.BRIDGE_BASE_X0                  # +X deck end: FLUSH with the bridge endplate -X face
                                        # (-16.5); +Z held by the rail-top grooves
PX1 = CH.KH_RAIL_X                      # -X deck end: EP_TOP_CLR off the keyhead face
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
                                       # 38.6-wide Alumitone still has >= +/-10 continuous X slide)
N_POS    = N_SLOTS - PIECE_SLOTS + 1   # = 4 coarse swap positions
CLAMP    = BAND_W / 2                  # 10.0 +/- fine X-adjust (BAND_W/2 -> continuous
                                       # by construction, so the identity is now literal)
# (DEAD_SLOTS is GONE with the spare fillers. It named the slots the piece covers in every
#  position, whose marked fillers could never be installed and so were never printed. With
#  one fret-free filler design there is nothing per-slot left to leave out.)

# shown installed state: piece in the 3 bridge-most slots, fillers behind it
# The -X run that can reach the MOTOR BANK at the neck-most slot position: everything -X of the
# bank's +X-most housing face, measured with the piece shifted all the way. Only this much of the
# skirt has to be shallow; the rest keeps its depth.
from . import motor_bank as _MB                    # motor_bank imports no deck module: no cycle
_BANK_X1 = (D.motor_pos(D.N_STRINGS - 1)[0] + D.MOTOR_SQ / 2
            + _MB.MOTOR_CLR + _MB.POST_T)
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

# ── pickup-piece interior geometry ───────────────────────────────────────────
# The pickup does NOT rest on the height screws directly (those would block its X
# travel); it rests on a full-width Z-PLATE that the screws lift. The plate slides
# only in Z inside the piece pocket, so the pickup can sit ANYWHERE across its
# +/-CLAMP fine-X range -> that's what lets the piece be only 3 bands wide. Height
# screws thread the floor and are turned from BELOW (a long driver past the belts);
# a side CLAMP screw drives a protective shim that pins the pickup +Y against the
# reference skirt (friction then holds X and, with the plate under it, Z).
PIECE_CTR = (PIECE_X0 + PIECE_X1) / 2                      # -47.5
WALL      = 5 * D.NOZZLE_D                                 # 4.0 piece end walls (was 3.5)
OPEN_X0   = PIECE_X0 - WALL                                # +X opening edge (-21.0)
OPEN_X1   = PIECE_X1 + WALL                                # -X opening edge (-74.0)
OPEN_CTR  = (OPEN_X0 + OPEN_X1) / 2                        # -47.5
OPEN_LEN  = OPEN_X0 - OPEN_X1                              # 53.0 = PK_W + 2*CLAMP
SKIRT_T   = 4 * D.NOZZLE_D                                 # 3.2 (was 3.0)
FLG_T     = 4 * D.NOZZLE_D                                 # 3.2 Z-plate guide flange (was 2.5)
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
# pickup's -Y face sits further +Y; the -Y grub's reach is what still retains it. With the shared
# M4x10 cup-tip the grub's usable tip travel is ~GRUB_SWEEP, so the window is [PK_MAX_L - GRUB_SWEEP,
# PK_MAX_L]. PK_MAX_L is the ROOM size (cavity/plate/-Y grub face), set a hair ABOVE the Alumitone so
# 101.6 isn't at the exact edge (0.4 mm headroom, user); the sweep goes DOWN over the dense 10-string
# cluster (George L ~97, Steeltronics ~98, Bill Lawrence/Wilde 100, Lace/Wallace/Sentell 101.6). The
# 108 Sentell LS20 + 120.7 wide-10 stay out (they'd need a longer screw AND a still-bigger cavity).
PK_MAX_L      = 102.0                                     # longest supported pickup -> sizes the room
GRUB_SWEEP    = 5.5                                       # M4x10 usable tip travel (screw_l - min_bite - ~1 tip)
PK_MIN_L      = PK_MAX_L - GRUB_SWEEP                     # 96.5 shortest retained (covers the whole cluster)
PK_MAX_YM     = PK_YP - PK_MAX_L                          # ROOM -Y edge = the longest pickup's -Y face (~-51.9)
PK_ROOM_CTR_Y = (PK_YP + PK_MAX_YM) / 2                   # plate/cavity centre (room grows -Y, not toward the rail)
YZONE    = 16.0                                           # -Y utility-zone depth beyond the pickup
OPEN_YP  = PK_YP + 0.6                                    # +Y opening edge (open bay; < rail YH)
HY_CLAMP = -PK_MAX_YM + YZONE                             # -Y skirt inner = extended room -Y edge (~+67.9)
OPEN_YC  = (OPEN_YP - HY_CLAMP) / 2                       # opening/floor Y centre
OPEN_YW  = OPEN_YP + HY_CLAMP                             # opening/floor Y width
# Z-plate the pickup slides on in X (fine tone) -- lifted/tilted by the 3 jacks:
ZPL_T    = 3 * D.NOZZLE_D  # 2.4 (was 2.0)
ZPL_TOP  = PM.PK_BOT                                      # pickup rests on the plate top
ZPL_BOT  = ZPL_TOP - ZPL_T
FLG_BOT  = ZPL_BOT
FLG_TOP  = ZPL_TOP + PM.PK_H_MIN                          # -Y guide wall top (capped below pickup top)
# ── LEADSCREW JACKS (user): head captured in the SOLID DECK, plate rides the thread ──
# The deck is SOLID at the jacks now (only the pickup cavity + a small nub-cavity below are
# open), so each leadscrew HEAD is captured DIRECTLY in the solid deck at the print bed (TZ)
# -- a Ø7.5 head pocket + a Ø4.6 shaft bore, NO boss/web/overhang. The thread runs down
# through a cadkit heat-set-insert NUT on a plate NUB. Turning the head from +Z (axially
# fixed, free to rotate; gravity holds it on the shoulder) walks the plate up/down.
JACK_D         = 4.0                             # M4 (cadkit heat-set-insert nut on the plate)
BOSS_H         = 8 * D.NOZZLE_D   # 6.4 (was 6.0)                              # NUT boss height ABOVE the plate top (nut boss is on TOP now,
                                                 # so the plate BOTTOM stays flat -> prints -Z->+Z, user)
JACK_MOUTH_Z   = ZPL_TOP + BOSS_H                  # plate NUT mouth = the boss TOP (screw threads down into it)
# The leadscrew is a real M4 BUTTON-HEAD cap screw (headed, hex-socket drive) captured in the
# deck: a counterbore seats the head, the shoulder bears on its floor, the shank threads down
# through the plate nut. Turning the head from +Z walks the plate up/down.
JACK_HEAD_D    = 7.6                               # M4 button-head cap screw head Ø (ISO 7380)
JACK_HEAD_H    = 2.2                               # button-head height
JACK_HEAD_Z    = TZ - (JACK_HEAD_H + 0.3)          # head SHOULDER (pocket floor) in the solid deck (=3.5)
HEAD_POCKET_D  = JACK_HEAD_D + 0.4                 # Ø8 head counterbore, opens at the bed (deck top TZ)
JACK_SCREW_L   = 20.0                              # NEW BOM part: M4×20 button-head leadscrew. 20 mm shank
                                                   # spans the full height-adjust travel (15..22 mm pickup
                                                   # depths + string-gap set) with the nut engaged throughout.
# SKIRT DEPTH (user, 2026-09-14). It used to hang 4.8 below the Z-plate, which made it the
# deepest thing in the pickup region and cost the bay underneath 4.8 mm of headroom -- and this
# piece SLIDES, so at its neck-most position that edge swings out over the motor bank, right
# over string 10's CAN tee. The skirt is the piece's only beam (a 6.4 plate with a 53 opening
# through it), so it is STEPPED rather than shortened everywhere:
#   DEEP  (SKIRT_DEEP_BOT) down to the jack screws' tips -- Z the pickup region already spends,
#         so the beam keeps its depth over the span that matters
#   SHALLOW (FLOOR_BOT, the Z-plate's underside) for the -X run that can reach over the bank
# The endplate lip datums off the skirt's outer FACE in Y, which neither change touches.
FLOOR_BOT      = ZPL_BOT                           # -Y skirt / end-wall bottom, shallow section
SKIRT_DEEP_BOT = JACK_HEAD_Z - JACK_SCREW_L        # the jack screws' tips: the deepest thing the
                                                   # pickup region reserves anyway (-16.10)
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
HEIGHT_HOLE = PICKUP_X_NOM
# ── plate SHAPE (user): GREEN pickup-area prism + 3 RED nubs out to the screws ────
# The plate is JUST the usable pickup area (a green prism) plus nubs that reach the 3 jack
# nuts. Everywhere else the plate used to occupy is now SOLID DECK (reclaimed as coloured
# top surface) -- the deck cavity is only the pickup + the 3 screws.
# ── pickup RETENTION (user): +Y WALL + -Y SCREW lock the pickup to the PLATE only ─
# (so the plate still moves up/down freely). The pickup's +Y face butts a wall that rises
# from the plate; a horizontal M4 grub through a -Y boss pushes the pickup +Y against it.
RET_WALL_T = 3 * D.NOZZLE_D                        # 2.4 +Y wall thickness (was 2.0)
RET_WALL_H = 8.0                                   # +Y wall height above the plate top (enough to lock, not tall)
# ⚠ THE RETENTION SCREW IS AN M4 x 12 BUTTON HEAD NOW, NOT A CUP-TIP GRUB (user, 2026-09-30:
# "everything should be M4 with 2.5mm hex" -- an M4 set screw takes a 2.0 key). A head changes
# three things the grub never had to care about:
#   * the head is O7.6 and turns just over the plate, so the axis rises to 6 beads: the head's
#     underside clears the plate top by 1.0 (at 4 beads it was 0.6 INTO it);
#   * the -Y jack's O9.2 boss stood 0.4 inside the head's swing, so JACK_MX_OFF goes 8.0 -> 9.6;
#   * it can only be driven from -Y, through the piece's skirt: RET_KEY_* is the slot for the key.
# The reach is unchanged: seated, the tip stands RET_SCREW_L - RET_BOSS_L = GRUB_SWEEP past the
# room's -Y edge, which is what the 96.5-102 pickup window was sized on.
RET_SCREW_L = 12.0                                 # M4 x 12 button (m4_button_12, already a BOM line)
RET_SCREW_Z = ZPL_TOP + 6 * D.BEAD                 # 4.8 screw axis height (head clears the plate by 1.0)
RET_BOSS_L = RET_SCREW_L - GRUB_SWEEP              # 6.5 -Y screw boss length (Y): the insert pocket + its floor to the boss +Y
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
RET_RELIEF_Y0 = -HY_CLAMP                          # from the skirt's inner face ...
RET_RELIEF_Y1 = PK_MAX_YM                          # ... to the boss's +Y face (the room edge)
RET_RELIEF_Z1 = TZ - D.MIN_WALL_2P                 # leaves a two-bead skin of deck over it
RET_KEY_W     = 5 * D.BEAD                         # 4.0: a 2.5 mm key is 2.9 across its corners
RET_KEY_Z0    = RET_SCREW_Z - RET_KEY_W / 2        # slot floor, half a slot under the axis
RET_BOSS_TOP_Z = RET_SCREW_Z + M4.insert_pilot_d / 2 + D.MIN_WALL_2P   # 1.6 (2-bead quality floor) over the bore
X_SLIDE   = 6.0                                    # pickup X-position room on the plate (+/-)
PLATE_X   = PM.PK_W + 2 * X_SLIDE                  # green X (pickup + slide) ~50.6
PLATE_Y   = (PK_YP - PK_MAX_YM) + 2 * RET_WALL_T   # green Y (LONGEST pickup + wall room each side) ~106.0
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
# (Y hold-down CLAMP removed; retention above locks the pickup to the plate instead.)

MARKER_FRETS = {3, 5, 7, 9, 12, 15, 17, 19, 21, 24}
# ── fret lines + fretboard border as a MATERIAL split, not an engraving ──────
FRET_T  = 1.6      # colour-layer thickness = embossed inlay height (Z)
INLAY_W = 2.4      # SHARED in-plane width: transparent fret-line width (to fret 24) AND the border-frame band
MIN_WEB = D.MIN_WALL   # smallest colour web left between lines (1-bead floor; stops dense micro-lines at the bridge)
# The high frets crowd toward the bridge, so from fret HI_FRET UP the LINES go THIN (user): a 2.4 line there
# needs a 3.2 gap and culls early; 1.6 (2-bead min) reads cleaner in the crowd and renders a few frets closer.
HI_FRET    = 24
HI_INLAY_W = D.MIN_WALL_2P


def _inlay_w(n):
    """Fret-LINE width for fret n: full INLAY_W below HI_FRET, thin HI_INLAY_W at HI_FRET and above."""
    return HI_INLAY_W if n >= HI_FRET else INLAY_W
# border X: the fretted length — from the bridge end of the fretboard (just -X of the pickup region) to
# the nut/keyhead end. Absolute coords; _split gives each panel its portion so the frame is continuous.
FRET_AREA_X0 = SLOT_X[PIECE_SHOWN + PIECE_SLOTS]   # +X (bridge) end of the FRET FIELD (lines + markers)
FRET_AREA_X1 = PX1                                 # -X (nut / keyhead) end
# The BORDER's side bands run further +X than the field, all the way to the deck's bridge end, so the
# band-region fillers carry the same top/bottom border as the rest of the fretboard (user). Those slots
# only ever hold the pickup piece OR a filler, and whichever fillers aren't covered are installed — an
# unbordered band there read as the fretboard just stopping short of the bridge.
BORDER_X0 = PX0                                    # +X (bridge) end of the border side bands
# The strings FAN (nut pitch 6.5 -> changer pitch 9.5), so size the fret BOX (border included) in Y to
# the OUTER-string span at its WIDEST edge (the +X / bridge end); the frets then finish INLAY_W short.


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
        if fx > FRET_AREA_X0 or nxt - fx < (_inlay_w(n) + _inlay_w(n + 1)) / 2 + MIN_WEB:
            break
        if x1 + 0.8 < fx < x0 - 0.8:
            out.append((n, fx))
        n += 1
    return out


def _border_frame():
    """Transparent U-frame (band width INLAY_W) around the fret field — the two long Y sides + the
    -X (nut/keyhead) end. OPEN at the +X (bridge) end: there is no fretboard edge there — the field
    just runs out under the pickup, whose seam X MOVES with the pickup's slot position (user), so a
    fixed +X edge would be both wrong and a false 'fret' on the seam. Same inlay/material as the fret
    lines, in the colour band (TZ-FRET_T .. TZ); _split clips it to each panel so the U reads continuous.

    The side bands run to BORDER_X0 (the deck's bridge end), PAST the fret field, so the band-region
    fillers are bordered too. The pickup PIECE is split lines=False and never takes any of this; where
    it sits, its cavity is wider than the frame anyway, so the border could not survive there."""
    x_hi, x_lo = BORDER_X0, FRET_AREA_X1                          # +X (bridge) end, -X (nut) end
    outer = box_at(x_hi - x_lo, 2 * BORDER_HY, FRET_T,
                   x=(x_hi + x_lo) / 2, y=0.0, z=TZ - FRET_T / 2)
    ix_lo, ix_hi = x_lo + INLAY_W, x_hi + 1.0                     # inset the -X end; RUN PAST the +X end
    inner = box_at(ix_hi - ix_lo, 2 * FRET_HY, FRET_T + 1.0,
                   x=(ix_hi + ix_lo) / 2, y=0.0, z=TZ - FRET_T / 2)
    return outer.cut(inner)


# ── fret-position MARKERS (between the lines, not on them) ───────────────────
# Different symbols mark the frets, keyed by the fret's position in the octave (n % 12) and REPEATING
# every octave: circle, triangle, square, pentagon, and a 4-circle octave marker (12 & 24).
MARK_D     = 6 * D.BEAD                # 4.8 marker circumscribed size
MARK_SHAPE = {3: "circle", 5: "triangle", 7: "square", 9: "pentagon", 0: "quad"}
# Per-marker X nudge for panel-edge printability: the fret-24 quad sits right at the mid panel's +X
# edge (its dots were 0.12 mm off it); shift it -X so ≥0.8 mm of material backs the dots (0.8 nozzle).
MARK_X_ADJ = {24: -0.7}


def _fret_x(n):
    return D.NUT_BLOCK_X + (D.BRIDGE_X - D.NUT_BLOCK_X) * (1 - 2 ** (-n / 12.0))


def _mark_x(n):
    return (_fret_x(n) + _fret_x(n - 1)) / 2 + MARK_X_ADJ.get(n, 0.0)   # fret-space centre + edge nudge


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


_MARKERS = None
for _n in sorted(MARKER_FRETS):
    _m = _marker(_n)
    _MARKERS = _m if _MARKERS is None else _MARKERS.union(_m)


def _fret_solids(x0, x1, frets=True):
    """The fret lines (string-field Y only) + the fretboard border frame + all fret-position markers
    (absolute; _split clips each panel's share), as prisms in the colour band (TZ-FRET_T .. TZ). _split
    embosses these into the transparent base and cuts them from the colour layer.

    frets=False LEAVES ONLY THE BORDER -- the two long side bands, and no line or marker across
    the field. That is what the SWAPPABLE FILLERS get (user, 2026-09-29), and the reason is that
    a fret line is at an ABSOLUTE X: mark a filler and it fits one slot only, so every slot the
    pickup piece might vacate needs its own printed part. Unmarked, one filler fits any slot, and
    the two that are installed are the same part as each other and as any spare. The border runs
    on because it is constant along X -- it is the only marking that can survive being movable."""
    out = _border_frame()
    if not frets:
        return out
    out = out.union(_MARKERS)
    for n, fx in _fret_positions(x0, x1):
        out = out.union(box_at(_inlay_w(n), 2 * FRET_HY, FRET_T, x=fx, y=0.0, z=TZ - FRET_T / 2))
    return out


SIDE_SKIN_T = D.MIN_WALL_2P     # colour carried DOWN the +-Y faces (user, 2026-09-16): the
                                # panel is transparent below the colour band, and at the edges
                                # that read as an exposed transparent underbelly along both
                                # flanks. Two beads of colour wrap it.


# PRINT ORIENTATION (user's convention: the record, declared once per part, and the hole
# cutters read it so every hole is shaped for the way its part actually prints).
PIECE_UP = (0.0, 0.0, -1.0)     # the DECK pieces print deck-DOWN: the top face (TZ) is on the
                                # bed and the part builds -Z, which is what lets each leadscrew
                                # head be captured in solid deck with no boss and no web
ZPL_UP   = (0.0, 0.0, 1.0)      # the height plate the other way up: flat bottom on the bed,
                                # every boss standing up


def _pickup_cavity(grow=0.0):
    """The deck's pickup opening, optionally grown `grow` all round -- ONE definition, used by
    the cut that makes it and by the colour skin that lines it, so the two cannot drift."""
    return box_at(CAVITY_X + 2 * grow, CAVITY_Y + 2 * grow, (TZ - BZ) + 2,
                  x=PICKUP_X_NOM, y=PK_ROOM_CTR_Y, z=(BZ + TZ) / 2)


def _cavity_skin():
    """A two-bead COLOUR lining round the pickup opening, its full depth (user, 2026-09-17).

    The opening's walls were transparent base material top to bottom, so the light this deck
    pipes along its length leaked straight out into the pickup cavity -- the one place it is
    not wanted, since that cavity is what the pickup and its shadow live in. Turning the
    border colour costs nothing structural (it is the same printed object, the same wall) and
    stops the bleed at the source rather than masking it later."""
    return _pickup_cavity(SIDE_SKIN_T).cut(_pickup_cavity())


def _side_skin(xa, xb):
    """The +-Y outer faces of a panel, SIDE_SKIN_T deep -- the colour part's wrap."""
    h = (TZ - BZ) + 2.0
    return box_at(xa - xb + 2.0, SIDE_SKIN_T, h,
                  x=(xa + xb) / 2, y=BY1 - SIDE_SKIN_T / 2, z=(TZ + BZ) / 2).union(
           box_at(xa - xb + 2.0, SIDE_SKIN_T, h,
                  x=(xa + xb) / 2, y=BY0 + SIDE_SKIN_T / 2, z=(TZ + BZ) / 2))


def _split(panel, xa, xb, lines=True, frets=True, cavity=False, opaque=None):
    """Split a finished panel at the colour line (z = TZ-FRET_T) → (base, colour).
    BASE (transparent PCTG) keeps everything below, plus the embossed fret solids
    trimmed to the panel (openings/windows interrupt the lines automatically);
    COLOUR (colour PCTG) is the top band PLUS the +-Y side skin, minus those solids. Exact
    complements with a flush top at TZ — the deck datum doesn't move. Print the pair as one
    object."""
    slab = box_at(xa - xb + 2.0, BY1 - BY0 + 2.0, FRET_T,
                  x=(xa + xb) / 2, y=(BY0 + BY1) / 2, z=TZ - FRET_T / 2)
    slab = slab.union(_side_skin(xa, xb))
    if cavity:
        slab = slab.union(_cavity_skin())  # ...and the pickup opening's own wall
    # ⚠ cavity=False IS NOT JUST AN OPTIMISATION, and the comment that used to stand here --
    # "no-op on the panels that have no opening: it lands on nothing" -- was wrong. The skin
    # is at the pickup's ABSOLUTE X, so on a FILLER built for a slot the opening passes
    # through it lands squarely INSIDE the panel and turns a patch of its top to colour: a
    # phantom rectangle of the pickup's outline, on a part that has no pickup in it. Caught by
    # the filler congruence check below, which is exactly the class of thing it is for (640.9
    # mm3 of one filler's top, moved from colour to base against its neighbour's).
    inlays = _fret_solids(xa, xb, frets=frets) if lines else None
    base, colour = panel.cut(slab), panel.intersect(slab)
    # ...and anything handed in as `opaque` is COLOUR material wherever it lies, not just
    # in the top band. The fret-light comb is the case: it runs from the board at -16.05
    # up to the inlay's underside, so a plain Z split would hand most of it to the
    # transparent base and the cells would not block anything (src/fret_light.py).
    if opaque is not None:
        base = base.cut(opaque)
        colour = colour.union(opaque.intersect(panel))
    if inlays is not None:
        inlay = inlays.intersect(panel)
        if inlay.solids().vals():          # nothing lands on this panel (e.g. a pickup-region filler)
            base = base.union(inlay)
            colour = colour.cut(inlays)
    return heal(base), heal(colour)


def _deck_body(xa, xb):
    """Bare deck plate, xa (+X) to xb (-X): a slab that CAPS both rails (the chassis
    lowers their tops to z0 across the deck span) with a vertical DOVETAIL tongue
    dropping down each rail centre-line into the rail-top groove. Wide foot, narrow
    mouth -> the plate can't lift out when inverted, and the tongue ties the rails
    in Y. The tongue runs along X, so the plate still slides out -X."""
    xm = (xa + xb) / 2
    body = box_at(xa - xb, BY1 - BY0, TZ - BZ, x=xm, y=(BY0 + BY1) / 2,
                  z=(BZ + TZ) / 2)
    for yc in (CH.Y_HI, CH.Y_LO):        # cadkit mushroom tenon down each rail
        body = body.union(CH._deck_tg(yc, xb, xa, mortise=False))
    return body


def _band(xa, xb, *, ui=False, cells=False):
    """A plain (filler / mid / keyhead) deck panel body + opt. UI (fret lines are
    applied by _split, which turns them into the base/colour material boundary).

    `cells` hangs the FRET LIGHT COMB under it -- one opaque wall per fret boundary from
    the LED board up to the inlay's underside, closed outboard by ramps. See
    src/fret_light.py; the comb is returned to the caller as well so _split can assign it
    the colour material."""
    body = _deck_body(xa, xb)
    if ui:
        # THE UI STATION. src/ui_panel.py owns all of it and derives its geometry from
        # the ROUTED ui_board -- the display's pocket and window hang off the header
        # KiCad placed, and the knob's hole off the switch KiCad placed. What lands
        # here is a cutter and a cradle; the two placeholder windows that used to be
        # cut at guessed coordinates are gone with the guesses.
        # ORDER MATTERS: the cradle is fused BEFORE the cutter runs, so the module's
        # pocket also clears anything of the cradle that strayed into it.
        body = body.union(UIP.deck_mount()).cut(UIP.deck_cutter())
    if cells:
        from . import fret_light as FL
        # the tabs go in with the comb: they are opaque structure under the board's
        # edges, outboard of every LED courtyard, and _split treats them as comb
        # ...and the seam pogos' notches through key's end wall go AFTER every union
        # that could refill them (docs: endplate cut order)
        comb = (FL.walls(xb, xa).union(FL.ramps(xb, xa))
                .union(FL.edge_walls(xb, xa)).cut(FL.strip_groove(xb, xa)))
        notch = FL.pogo_notches(xb, xa)        # empty on the mid panel: no wall there
        if notch.vals():
            comb = comb.cut(notch)
        # the M4 boss is cut into the COMB (not the deck body) so _split keeps it
        # opaque with the rest of the structure hanging below the transparent base
        comb = FL.m4_boss(comb, xb, xa)
        return heal(body.union(comb)), comb
    return body, None


def _pickup_piece():
    """4-slot deck panel that carries the pickup. The deck is SOLID except (a) the PICKUP
    CAVITY -- a hole the pickup pokes up through and moves in -- and (b) the 3 LEADSCREW
    bores. Everywhere the plate no longer needs to move is filled deck (reclaimed as
    coloured top surface, user). A -Y skirt + two end walls hang below (structure / the
    endplate-lip datum). Each leadscrew HEAD is captured in the SOLID DECK at the print bed
    (Ø7.5 pocket down to the shoulder + Ø4.6 shaft bore) -- no boss/web, so no overhang."""
    body = _deck_body(PIECE_X0, PIECE_X1)
    # PICKUP CAVITY only (pickup pokes through + slides/rises); rest of the deck stays solid
    body = body.cut(_pickup_cavity())
    # -Y skirt + end walls below the deck (structure / endplate-lip datum), built DEEP and then
    # stepped up over the -X run that can swing out above the motor bank (see SKIRT_DEEP_BOT)
    body = body.union(box_at(OPEN_LEN + 2 * WALL, SKIRT_T, BZ - SKIRT_DEEP_BOT,
                             x=OPEN_CTR, y=-(HY_CLAMP + SKIRT_T / 2),
                             z=(BZ + SKIRT_DEEP_BOT) / 2))
    for xe in (PIECE_X0 - WALL / 2, PIECE_X1 + WALL / 2):
        body = body.union(box_at(WALL, OPEN_YW, BZ - SKIRT_DEEP_BOT,
                                 x=xe, y=OPEN_YC, z=(BZ + SKIRT_DEEP_BOT) / 2))
    # ...and the step: shallow where this piece can ever lie over the bank
    _shift = (N_POS - 1) * PITCH                       # its neck-most travel
    _step_x1 = _BANK_X1 + _shift                       # in the piece's own (drawn) frame
    _x0 = OPEN_X1 - WALL - 1.0
    if _step_x1 > _x0:
        body = body.cut(box_at(_step_x1 - _x0, OPEN_YW + 2 * SKIRT_T, FLOOR_BOT - SKIRT_DEEP_BOT,
                               x=(_x0 + _step_x1) / 2, y=OPEN_YC,
                               z=(SKIRT_DEEP_BOT + FLOOR_BOT) / 2))
    # THE RETENTION SCREW'S TWO CUTS, after every union above (a later union would refill them).
    # (1) A RELIEF in the deck's underside over the screw's boss and head. The boss top stands
    #     RET_BOSS_TOP_Z, 1.6 under the deck at the lowest plate, so without this the plate could
    #     rise 1.6 and no further; the relief leaves a two-bead skin of deck and gives it
    #     RET_RELIEF_Z1 - RET_BOSS_TOP_Z. Blind from below, so the top surface is untouched, and
    #     this piece prints deck-down, so it is an open pocket on the bed side: no ceiling.
    # (2) THE KEY SLOT through the -Y skirt, on the screw's axis: a 2.5 mm key reaches the head
    #     from -Y with the piece on the bench (INSTALL_NOTES: set the pickup before the piece
    #     goes in). Open up to the deck so the one slot serves the plate at any bench height.
    body = body.cut(box_at(RET_RELIEF_W, RET_RELIEF_Y1 - RET_RELIEF_Y0, RET_RELIEF_Z1 - BZ + 0.5,
                           x=RET_SCREW_X, y=(RET_RELIEF_Y0 + RET_RELIEF_Y1) / 2,
                           z=(BZ - 0.5 + RET_RELIEF_Z1) / 2))
    body = body.cut(box_at(RET_KEY_W, SKIRT_T + 2.0, BZ - RET_KEY_Z0,
                           x=RET_SCREW_X, y=-(HY_CLAMP + SKIRT_T / 2),
                           z=(BZ + RET_KEY_Z0) / 2))
    # LEADSCREW BORES through the solid deck: head pocket (Ø7.5, opens at the bed TZ, down
    # to the shoulder) + shaft bore (Ø4.6, on down into the open bay where the plate nut is)
    # LEADSCREW BORES, through cadkit's counterbore so the PRINT DIRECTION is checked (user,
    # 2026-09-17): this piece builds -Z from the deck face, so the step from the head pocket
    # down to the shaft bore is drilled INTO the build -- a flat annular ceiling bridging over
    # the pocket. cadkit turns it into a 45 deg cone under the seat plane; the head still seats
    # on its rim (0.2 lower, where the cone passes its own Ø). Hand-rolled cylinders could not
    # know any of that, which is why they had the overhang.
    for jx, jy in JACK_POS:
        body = cut_counterbore(body, HEAD_POCKET_D, TZ - JACK_HEAD_Z,
                               M4.shaft_clr_d + 0.4, TZ - (BZ - 1.0),
                               (jx, jy, TZ), (0.0, 0.0, -1.0),
                               print_up=PIECE_UP, overshoot=1.0)
    return heal(body)


def _pickup_zplate():
    """The height plate: a GREEN pickup-area prism (the pickup rests on it; X-slide room)
    plus 3 NUBS reaching the leadscrew NUTS (user's green+red shape). PRINTS -Z->+Z with a
    FLAT BOTTOM (user): every boss is on TOP -- the nut bosses stand UP (insert pocket down
    from the boss top; the screw tail passes through a Ø4.4 hole in the flat plate). RETENTION
    (user): a +Y WALL the pickup butts + a -Y horizontal grub that pushes it +Y against the
    wall, locking the pickup to the PLATE only (so the plate still travels)."""
    # the prism is the DECK OPENING plus LIGHT_FLANGE all round, not the pickup's own footprint:
    # the pickup only needs PLATE_X x PLATE_Y to rest and slide on, but the plate is also the
    # lid over a lit body, and light does not care where the pickup ends (user)
    plate = box_at(CAVITY_X + 2 * LIGHT_FLANGE, CAVITY_Y + 2 * LIGHT_FLANGE, ZPL_T,
                   x=PICKUP_X_NOM, y=PK_ROOM_CTR_Y, z=(ZPL_BOT + ZPL_TOP) / 2)
    for jx, jy in JACK_POS:
        dx, dy = jx - PICKUP_X_NOM, jy - PK_ROOM_CTR_Y
        if abs(dx) - PLATE_X / 2 >= abs(dy) - PLATE_Y / 2:      # jack juts past the green in X -> X-arm
            sg = 1.0 if dx > 0 else -1.0
            xe = PICKUP_X_NOM + sg * PLATE_X / 2
            xa, xb = xe - sg * NUB_W / 2, jx + sg * M4.boss_od / 2    # root in the plate .. boss edge
            plate = plate.union(box_at(abs(xb - xa), NUB_W, ZPL_T,
                                       x=(xa + xb) / 2, y=jy, z=(ZPL_BOT + ZPL_TOP) / 2))
        else:                                                  # -> Y-arm
            ye = PK_ROOM_CTR_Y + (PLATE_Y / 2 if dy > 0 else -PLATE_Y / 2)
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
    plate = plate.union(box_at(PM.PK_W, RET_WALL_T, RET_WALL_H,
                               x=PICKUP_X_NOM, y=PK_YP + RET_WALL_T / 2,
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


def _filler(slot):
    """One fret-marked filler band at slot index `slot` (its own fixed X span; BAND_W
    wide, with the GAP to the next slot left as clearance)."""
    return _band(SLOT_X[slot], SLOT_X[slot] - BAND_W)[0]


# ── the two long panels' seam, and the bed ──────────────────────────────────────────────
# 255 on this printer. It was a number in a COMMENT beside MID's length ("both panels stay
# < 255 mm bed") and nothing checked it -- which is fine until a slot is handed over and the
# mid panel grows by 20, at which point the comment is the only thing standing between the
# deck and a panel that will not print.
BED_XY = 255.0
for _n, _xa, _xb in (("mid", MID_X0, MID_X1), ("keyhead", KEY_X0, KEY_X1)):
    assert _xa - _xb <= BED_XY, (
        "the %s panel is %.2f long against a %.0f bed" % (_n, _xa - _xb, BED_XY))

# (THE BALANCE ASSERTION THAT STOOD HERE IS GONE. It held the two long panels within 10 mm
#  of each other, which they no longer are -- 215.79 against 249.60 -- because the keyhead
#  panel was set to fill the bed instead (user, see KEY_L). Loosening it to 40 would have
#  been an assertion that asserts nothing; the constraint that actually binds is BED_XY
#  above, and it is checked.)

# ...AND THE SEAM BETWEEN THEM CLEARS EVERY MARKING. This is what MID's length was chosen
# for and it was only ever written down: a seam through a fret line or a marker dot reads as
# a broken inlay on a deck somebody looks at all day. Checked against the real solids rather
# than against the fret numbers, so a marker nudge (MARK_X_ADJ) cannot sneak past it.
_SEAM_CLR = D.MIN_WALL              # 0.8, one bead of material either side of the cut
for _n, _fx in _fret_positions(MID_X0 + 50.0, MID_X1 - 50.0):
    assert abs(_fx - MID_X1) > _inlay_w(_n) / 2.0 + _SEAM_CLR, (
        "the mid/key seam at %.2f runs through fret %d's line at %.2f"
        % (MID_X1, _n, _fx))
for _s in _MARKERS.val().Solids():
    _b = _s.BoundingBox()
    assert not (_b.xmin - _SEAM_CLR < MID_X1 < _b.xmax + _SEAM_CLR), (
        "the mid/key seam at %.2f runs through a marker at x %.2f..%.2f"
        % (MID_X1, _b.xmin, _b.xmax))


pickup_zplate = heal(_pickup_zplate())

# every panel becomes a (base, colour) print pair. The pickup piece keeps a fully
# line-free top (its opening chops the field, and it had no lines before); the two LONG
# panels carry the fret lines and markers; the FILLERS carry the border and nothing else,
# so any filler fits any slot.
# SHOWN config: piece in slots [0..PIECE_SLOTS), fillers in the rest.
_piece_pair   = _split(_pickup_piece(), PIECE_X0, PIECE_X1, lines=False, cavity=True)
# FRET-FREE, so every filler is the same part -- see _fret_solids. The congruence is
# asserted below rather than asserted in prose.
_filler_pairs = [_split(_filler(i), SLOT_X[i], SLOT_X[i] - BAND_W, frets=False)
                 for i in range(N_SLOTS)]
def _mctrl_capture():
    """A rib down from the keyhead panel to just above the motor board's top edge, so the
    PANEL retains that board and it needs no screw (user, 2026-09-29).

    ⚠ THIS REPLACES AN M4 AND ITS BOSS, which is the point -- and the boss was also the part
    the user found printing as an overhang: keyhead_cradles builds it as a column along LOCAL
    +Z, and stand() maps that to WORLD +X, so it is a horizontal O9.2 cylinder in a chassis
    that prints Z-up. check_ceilings cannot see it (it looks for FLAT ceilings; a cylinder's
    underside is curved), so deleting it beats buttressing it.
    ⚠ THE RIB REACHES DOWN; THE BOARD DOES NOT COME UP. See electronics.mctrl_capture_target
    for why the board's Z cannot move -- its plug latches have to stay reachable from outside.
    ⚠ SIZED FROM MEASUREMENT. Within the laminate's own footprint the board's top 10 mm is
    PURE LAMINATE (880.0 mm3, exactly 1.6 x 55 x 10), and the whole board's zmax equals the
    laminate's, so nothing stands proud of the edge the rib lands on. The column above the
    board is empty but for this panel. The rib is therefore wider than the 1.6 laminate --
    it bears on the edge, and the extra width is section rather than contact.
    It prints the right way up: top_plate builds DECK-DOWN, so this points UP off the bed.
    """
    x0, x1, y0, y1, ztop = EL.mctrl_capture_target()
    return box_at(EL.MCTRL_CAP_T, EL.MCTRL_CAP_L,
                  BZ - (ztop + EL.MCTRL_CAP_GAP),
                  x=(x0 + x1) / 2.0, y=(y0 + y1) / 2.0,
                  z=(BZ + ztop + EL.MCTRL_CAP_GAP) / 2.0)


_mid_body, _mid_comb = _band(MID_X0, MID_X1, ui=True, cells=True)
_key_body, _key_comb = _band(KEY_X0, KEY_X1, cells=True)
# ⚠ THE CAPTURE RIB GOES INTO THE KEY BAND'S BODY, NOT ITS COMB. main split _band into
# (body, comb) so the lit cells can be drawn as their own colour; this rib is structure --
# it reaches down to retain the motor board -- so it belongs to the body the comb is cut
# from. Unioning it into the pair after the split would have put a structural rib in the
# part that exists to be a different colour.
_key_body = _key_body.union(_mctrl_capture())
_mid_pair     = _split(_mid_body, MID_X0, MID_X1, opaque=_mid_comb)
_key_pair     = _split(_key_body, KEY_X0, KEY_X1, opaque=_key_comb)

# build.py places these in the assembly (piece + visible fillers + the 2 panels)
# and exports base + colour side by side (top_plate_N + top_plate_N_color). The
# fillers under the piece are exported as parts but not placed (they'd clash).
_shown_pairs = [_filler_pairs[i] for i in range(PIECE_SHOWN + PIECE_SLOTS, N_SLOTS)]
_seg_pairs   = [_piece_pair, *_shown_pairs, _mid_pair, _key_pair]
segments        = [b for b, _ in _seg_pairs]
segments_color  = [c for _, c in _seg_pairs]

# ⚠ THERE ARE NO SPARE FILLERS ANY MORE, and their absence is the point of the fret-free
# filler (user, 2026-09-29). They existed because a marked filler fits one slot: whichever
# slots the pickup piece vacated needed their own printed parts, so the build carried
# N_SLOTS - PIECE_SLOTS installed ones PLUS a set for every other position, exported off to
# the side of the instrument. Unmarked, a filler is the same part in any slot: print the
# N_SLOTS - PIECE_SLOTS that are installed and move them when the pickup moves.
N_FILLERS = N_SLOTS - PIECE_SLOTS

# ...AND THAT IS CHECKED, not just described. If a filler ever stops being congruent with
# its neighbours -- a stray absolute-X feature, a marker creeping into the region -- the
# "one part fits any slot" claim is silently false and the instrument gets a filler that
# only goes in one way round.
_fv = [(b.val().Volume(), c.val().Volume()) for b, c in _filler_pairs]
for _i, (_bv, _cv) in enumerate(_fv[1:], 1):
    assert abs(_bv - _fv[0][0]) < 1e-3 and abs(_cv - _fv[0][1]) < 1e-3, (
        "filler %d is not the same part as filler 0 (base %.3f vs %.3f, colour %.3f vs "
        "%.3f) -- something in it is at an absolute X, so it no longer fits any slot"
        % (_i, _bv, _fv[0][0], _cv, _fv[0][1]))
