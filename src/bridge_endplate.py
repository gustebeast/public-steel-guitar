"""Bridge endplate (§8) — PCTG, printed FLAT, dovetailed onto the rail ends.

ONE solid piece that closes the box at the +X end AND carries the bridge-bearing
axle (the 90° string turn — the highest-load point in the instrument). Because it
prints flat (on its face) it needs no supports, so it can be fully solid and
featured; the rails' dovetail tongues socket into blind pockets in the base, driving
the bearing load straight into the rails — far stronger than the old bolted
bridge support. NO GLUE: the sockets lock X and Y by shape, and +Z — the drop-on
install axis — is closed by the RETENTION LIP below, which the installed deck
panels trap (probed: seated 0, lift 0.2 fouls the deck by 114 mm³). Replaces the
bridge support, the +X bulkhead AND the +X crossbar.
Built in global position.

Endplate methodology: BOTH endplates start from THE SAME TWO PRISMS (shared code,
endplate_base): the fill slab (z -23.15..6, full 25 footprint) = the +X cross-tie
(no separate chassis crossbar), and the hollowed foot box below it whose kept
exterior walls are the +X END face (CH.T = 10 thick) and the +-Y side faces (=
the rail takeovers: the chassis removes the rail ends at x > -17.5 and this piece
IS the rail there). Each rail end sockets a low keyhead-style dovetail (wide +X /
narrow -X, gripping the bearing wrap's -X pull). Above z6 only the string-holding
mechanism: the bearing AXLE on two short ARM stubs (the 90° turn) and the
axle-support COMB. The +X carriages move in Z and install from +X; their whole
clearance volume is THE CHANGER ROOM — one prism with one ceiling (see ROOM_Z1)
cut through the base's field centre (below the lower guide ledge nothing sweeps —
the base stays solid to the bed); foot clearance is pocketed only over the +X
legs' kept chassis shells, and the panel-jack corner is recessed back to a 4 mm
panel.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from . import top_plate as TP
from . import optical_pickup as OP
from .endplate_base import endplate_base
from .screw_rail import screw_rail as _screw_rail, seat_cutter as _seat_cutter
from .screw_rail import BOT as _SR_BOT, TOP as _SR_TOP
from .screw_rail import PRINT_UP as _SR_PRINT_UP
from .helpers import box_at, cyl, cyl_y
from cadkit.fasteners import M2, M4, cut_selftap, cut_anchor
from cadkit.supports import printable_bore

# Build direction. The endplate prints FLAT on its +X face, so "up" out of the bed is -X.
# Any round hole whose axis runs SIDEWAYS to that -- the Y-axis axle bores -- has a
# circular ceiling that droops out of round without support. cadkit.supports.printable_bore
# shapes a 45 deg teardrop peak from this vector (and returns a plain cylinder for bores
# that run along it, so callers need not know which case they are in).
PRINT_UP = (-1.0, 0.0, 0.0)
assert _SR_PRINT_UP == PRINT_UP, (
    "the screw rail is FUSED into this part, so its teardrops must be shaped from "
    "the same build direction — one of the two copies has drifted")

X0   = CH.X_BRIDGE                 # cap -X face / field<->cap boundary: the field stays
                                   #   OPEN -X of here (carriage sweep / strings / rods)
# 25 mm block CENTERED on the bearing axle (the highest-load string-turn point), so the
# axle sits mid-material and the ~1.5 kN of string wrap is balanced about it. Both
# endplates are 25 mm (= CH.KH_EP_THK); the keyhead pins its inboard face to the rail
# end, the bridge instead centers that span on the axle. The arms, the fill band and the
# L-foot all span XLO..XHI SYMMETRIC about the axle, so the load path is balanced.
# XLO sits EP_TOP_CLR (0.4) +X of the rail end (CH.TP_EP_GX, derived as XLO - EP_TOP_CLR):
# the consistent top-joint X-gap to the housing; the dovetail's locking foot stays captured.
T_EP = D.ENDPLATE_W                # 25 mm width in X (shared with the keyhead + base)
XHI  = D.BRIDGE_BASE_X1            # +X outer tip (8.5), 12.5 +X of the axle
XLO  = D.BRIDGE_BASE_X0            # -X inboard face (-16.5), 12.5 -X of the axle
X1   = XHI                         # +X tip (8.5) -- alias for the mechanism references
ARM_X = XLO                        # arms span the FULL 25 mm block: symmetric edge webs
ARM_W = D.BRIDGE_ARM_W             # arm / edge-web thickness (Y) — kept clear of the +Y rail
# ── TIE BAR DELETED (user) -- THE TOP IS NOW FREE ───────────────────────────
# There is no longer ANY structure above the strings at the bridge. The old bar spanned
# x -16.6..8.6 at z 17..22, i.e. its underside was 0.11 mm over the thickest string's top
# and it started 12.6 mm out from the termination -- dead centre of the palm blocking
# zone, with no hand room at all.
#
# Removing it costs the axle almost nothing, and the reason is worth writing down: the
# axle bore is at z 12.0 and the SOLID field-centre cap band runs z 6..10, so the axle is
# carried 2 mm above the top of solid material. The arms are not really cantilevers at
# all at that height -- they are stubs. Everything the arm had from the bore's top (13.7)
# up to 22 was there to host the tie bar, not to hold the axle up. So the string load path
# is unchanged: bearings -> axle -> the nine comb fingers + two arm stubs -> cap band ->
# endplate block -> dovetails -> rails.
#
# The arms sit at y +-51.75, 9.35 mm OUTBOARD of the outermost string (+-42.4), so their
# height was never a string-clearance question either -- only the bar's span was.
# FLAT CHANGER TOP (user): the +Z extent of the whole bridge is the BEARING TOP, and the
# tail (string-termination → +X tip) is a solid prism filled to that height — no more
# drop-down cap. BEAR_TOP is single-sourced from the bearing OD so it tracks the string plane.
BEAR_TOP = D.STRING_Z                                              # 16.0 = bearing top = string plane
ARM_TOP = BEAR_TOP                                                # side walls flush to the flat top
#   (was 15.70 = bore + a 2 mm cap; now the arms rise the last 0.3 to the bearing top so the
#    side walls match the filled tail — the axle grub just reaches 0.3 deeper, still fine)
MIN_ADDED = D.MIN_WALL_2P         # 1.6 -- two-bead QUALITY floor for material this
                                  # feature ADDS (single-sourced via dimensions)

# ── OPTICAL-STRIP CARRIER (optical_pickup.py) ────────────────────────────────
# The strip moved OUT from under this bar and UNDER THE STRINGS (user): a bar 3 mm over
# the strings, starting 14.5 mm out from the termination, sat straight in the palm
# blocking zone. It now lies on the deck, and this carrier is what holds it.
#
# A PLINTH, not a slot, and it is monolithic with the endplate on purpose: the sensor
# standoff is the signal-critical dimension on this board, so it wants to reference the
# bridge directly rather than through the deck panel's tolerance stack. It simply RIDES
# ON TOP of the deck -- no slot is spent, so the magnetic pickup keeps the whole grid.
#
# The strip is single-sided with every part on its TOP face, so the whole underside can
# bear on a solid plinth top; no ledges, no floor, nothing to fuse back after a cut.
# X is capped by the deck band OP reads from top_plate (pickup cavity to deck end): there
# is 0.2 either side of the board, so the plinth cannot have an -X wall and the board is
# located +X against the endplate face.
#
# The plinth is BACKED BY THE COMB BRACE below -- which is what makes it printable at all.
# On its own its first layer floated: the field-centre band above z6 is only unioned from
# X0 (+6.0) to X1, so between XLO and +6 there is no material at this height for the
# plinth to start on. (User-caught.)
CARRIER_TOP  = OP.PLINTH_TOP                  # 9.501 -- the board bears directly on this.
                                              # PLINTH_TOP, not PCB_BOT: datumed off the
                                              # board's WORST-CASE thickness so fab tolerance
                                              # can only open the optical gap, never close the
                                              # roof clearance the board slides through.
# ── THE CHANGER ROOM: ONE PRISM, ONE CEILING (user) ─────────────────────────
# The changer hardware's clearance volume is a single rectangular prism, cut once
# in _cap: y ±WIN_HW (the arm inner faces), z ROOM_Z0 (under the nut's sweep) up
# to ROOM_Z1, running straight through the whole X. It replaces four overlapping
# cuts — the field-centre LOW + HIGH boxes, the stringing-access window and the
# guide-view window — whose union left a stepped ceiling measured at FOUR values
# on the finished underside (5.6 cap band / 6.0 finger roots / 6.5 carrier+brace
# / 7.4 tower relief). Each was justified; the staircase was nobody's design.
#
# THE CEILING IS SET BY THE TALLEST THING IN THE ROOM (user), clearing it by ≥ 1.0,
# with the SHELF LEFT ABOVE the cut on a whole number of beads. That tallest thing is
# now the CARRIAGE'S ANCHOR TOWER at the top of its travel. It used to be the ten
# leadscrew tops, until the screws were cut back to the nut they actually drive
# (D.SCREW_TOP_Z, once 2.4, now −7.6) — so this ceiling is re-datumed with them
# rather than left pointing at a rod that no longer comes near it.
# The shelf is BEAR_TOP − ROOM_Z1: 16 beads = 12.8 puts the ceiling at 3.20 and
# clears the tower by 1.20. (17 beads would clear by 0.40 — under the rule.)
# Writing it as `BEAR_TOP − N × BEAD` is what puts the SHELF on the grid rather than
# the ceiling's absolute height: the shelf is the material, the ceiling is only where
# it stops. For scale, the shelf was 8.60 = 10.75 beads when the user measured it.
# FLOOR and CEILING are both the nut's now — there is no carriage to clear. The old
# ceiling was held up by the carriage's ball cage (_TOWER_TOP), which cleared the
# bridge bearings by exactly its 1.0 minimum and so could never move; that is what
# forced the nut's boss to be recessed at all. With the cage gone the ceiling drops
# to just over the screw tops, and everything it used to squeeze goes away with it.
ROOM_Z0      = D.NUT_BOT_MIN - 1.0            # -26.35, under the nut's lowest sweep
ROOM_Z1      = D.TOP_BRG_Z0                   # -3.2 — the ceiling IS the top bearing's
                                              # seat mouth. The screw no longer stops
                                              # under the ceiling; it runs on past the
                                              # nut INTO the slab, to its top bearing.
assert D.NUT_TOP_MAX < ROOM_Z1 - 1.0 + 1e-9, (
    f"the nut's top of travel ({D.NUT_TOP_MAX}) does not clear the room ceiling")
# Fingers and braces — everything INSIDE the endplate — put their underside on the
# ceiling, so no later union can hang back down into the room.
UNDER_Z      = ROOM_Z1
# ...but the CARRIER PLINTH cannot: it is the one piece that reaches −X PAST the
# endplate face, out over the deck panel, so its floor is set by the DECK, not by
# the room. (It was flush with the comb while the ceiling happened to be above the
# deck; at a 4.00 ceiling that would bury it 2.4 mm inside the deck.) The step
# between the two planes falls exactly at XLO, and it faces −X — away from the bed
# in this +X → −X build — so it is an upward face, not an overhang, and the plinth
# is fully backed by the deeper brace behind it.
CARRIER_BOT  = CH.TP_GZ1 + 1.0                # 7.4 — 1.0 over the deck top
CARRIER_X1   = OP.PCB_X1S - 0.1               # -X face, inside the band by a hair
CARRIER_HY   = 68 * D.BEAD                    # 54.4 out to the arms

# TAIL PLINTH -- the strip's digital block, now that it widens +X OVER THIS PART instead
# of -X over the deck (user). That move is what makes it supportable at all: past
# CARRIER_HY there is no endplate material above z6 for a plinth to start on, but out here
# the FILL SLAB's top IS z6, so this plinth merges straight into solid material. It needs
# no deck standoffs, so top_plate is untouched, and printing +X -> -X it is backed the
# whole way. Bottom sits AT z6 (not UNDER_Z) precisely because it lands on the slab
# rather than hovering over the deck panel.
TAIL_X0 = XLO                                 # -16.60; the -X half is the carrier's job
# +X RUNS TO THE OUTER FACE, i.e. TO THE BUILD PLATE (user). It used to stop at OP.TAIL_X1
# (7.00), which is where the BOARD stops -- but the board's edge and the plinth's edge are
# different requirements. Printing +X -> -X the outer face IS the bed, so a plinth beginning
# at 7.00 starts its first layer 1.6 mm in mid-air, with the endplate's z6..9.5 band empty
# behind it out here (the tail prism only fills to z16 inboard of the arms). Probed: at
# y +-60 and -90 the solid ran out at 7.00 while at y 0 it reached 8.5. Running to XHI roots
# every layer on the plate. Costs a 1.6 mm ledge on the exterior face in the wrap/compute Y
# zones, below the board and out of the player's way.
TAIL_X1 = XHI                                 # 8.60 = the build plate
TAIL_Y0 = OP.PCB_YM                           # -106.85
TAIL_Y1 = -CARRIER_HY                         # -54.0: OVERLAP the carrier band rather than
                                              # meeting it at OP.Y_TAIL (-55.0), which left a
                                              # 1 mm strip with neither piece under it

# ── COMB BACK-BRACE (user's sketch) ──────────────────────────────────────────
# The comb fingers root on the cap band at x 2.6..6.0 and reach out to -6.5 with the AXLE
# BORE AT THEIR TIP -- a 12.5 mm cantilever carrying the highest load in the instrument.
# This braces the other side: each finger grows -X, then FLARES AT 45 deg in plan until
# neighbouring flares merge into one solid bar spanning the full Y extent. The finger
# stops being a cantilever and becomes a beam held at both ends.
#
# 45 deg is not cosmetic -- it is the print constraint. The endplate builds +X -> -X, so
# growing in Y as X decreases means new material with nothing behind it; 45 deg is exactly
# the self-supporting limit, so the gaps close without a single overhang.
#
# And the same bar keeps running -X to BECOME the PCB plinth, which is what fixes that
# part's floating first layer: the whole path from the cap band to the optical strip is
# now continuous material in the build direction.
BRACE_X0 = -11 * D.BEAD          # -8.8: start of the flare, 0.8 clear of the bearing OD
BRACE_X1 = XLO                   # -16.60, where the plinth takes over
BRACE_Z0 = UNDER_Z               # flush with the finger underside -- see UNDER_Z
# Raised to meet the light cover's top, since the brace is what the cover's roof lands on
# in the +X -> -X build -- at 13.0 the roof's upper 1.0 would have had no backing and its
# first layer would have floated. Same 1.10 string clearance the cover already carries.
BRACE_Z1 = OP.COVER_Z1           # 14.011; still covers the bore (10.3..13.7) entirely
AXLE_BORE = D.BRIDGE_AXLE_D + 0.4
# AXLE RETENTION, NO GLUE (user: every part comes apart). The Ø3 ground shaft slides
# -Y through both arms, 10 bearings and 9 comb fingers, so it can carry no shoulder;
# a glue dab at the arms used to hold it. Instead: the -Y arm's bore is BLIND (that
# wall is the -Y hard stop) and one M2 grub in the +Y arm's TOP bears on the shaft to
# close +Y. Deleting the tie bar freed that top face, so the grub is now reachable
# from straight above with the strings off. It self-taps in AXLE_GRUB_L of material
# rather than taking a heat-set insert (cadkit's usual set-screw preference): there
# are only 2.0 mm between the bore crown and the arm top, and 2.0 is five threads at
# 0.4 pitch against a shaft that nothing pushes axially -- 10 bearing bores of friction
# already hold it, and the blind end takes the other direction positively.
AXLE_END_WALL = MIN_ADDED                             # -Y blind-bore wall (the 2-bead tier)
AXLE_GRUB_Z   = ARM_TOP                               # grub mouth: the arm's free top
AXLE_GRUB_L   = ARM_TOP - (D.BRIDGE_BEARING_Z + D.BRIDGE_AXLE_D / 2) + 0.2

Z6     = CH.TP_GZ1                 # deck/top-plate level = the bridge's general top
# ── GUIDE RODS: SOCKETED FROM ABOVE, HANGING DOWN (user) ────────────────────
# The rods used to stand in blind sockets in a ledge BELOW. That end no longer
# exists: the drive relief and the nut's own sweep between them take out every scrap
# of endplate under the room at this X line. The top is the only end left — and it is
# also the end that prints, since everything up there is a straight -X extension of
# solid cap and every layer of it is backed.
#
# SUPPORTED AT BOTH ENDS, INSTALLED FROM +Z (user). The rod passes clean through the
# slab and lands in a blind socket in the SCREW RAIL below, so it is a beam rather
# than a cantilever and lateral load on it stops being a question. That bottom socket
# only exists because the thrust stack moved up onto the pulleys and took the rail
# with it — in the old layout the drive relief had cut away everything down there.
#
# It also stops the press fit mattering. A single-ended rod depended on that fit
# staying tight, and an interference fit in plastic sheds stress over time; located at
# two ends it is held whether or not the fit relaxes.
#
# RETENTION IS FREE: gravity seats it in the blind socket, and once the instrument is
# strung the string runs directly over this line 16 mm up, so the rod cannot be lifted
# out. No grub, no clip — captive by assembly order, the same trick the bridge axle uses.
GUIDE_DROP_Z1  = BRACE_Z1                       # 14.01, the top of the slab: the BORE
                                                # runs to here so the rods drop in from +Z,
                                                # LAST before stringing
# ...but the ROD ITSELF stops short of that. Its bore sits 0.025 mm INSIDE the bridge
# bearing's outer diameter — the rod line is 14.5 -X of the screw and the bearing
# reaches -13.0, so over z 3.0..14.0 they interfere rather than merely pass (user spotted
# it). Shortening the rod is the cheap half of the fix: the alternative, moving the rod
# further -X, drags the nut and therefore the string anchor with it and steepens a break
# angle that is already past 90°. The BORE keeps its full length, so the drop-in path is
# unaffected; only 0.025 of a slot wall is grazed, which is nothing.
GUIDE_ROD_TOP  = (D.STRING_Z - D.BRIDGE_BEARING_OD) - 1.0   # 2.0, a mm under the bearing
assert GUIDE_ROD_TOP <= D.STRING_Z - D.BRIDGE_BEARING_OD - 1.0 + 1e-9, (
    "the guide rod reaches into the bridge bearing's Z band")
GUIDE_SOCKET_H = 5 * D.BEAD                     # 4.0 of blind socket in the rail
GUIDE_SOCKET_Z = _SR_TOP - GUIDE_SOCKET_H       # -30.4, the socket's floor
# The web between this bore and the top bearing's pocket is the tight spot, and it is
# a teardrop-apex-to-bore-wall distance, not a wall anyone chose:
_GUIDE_WEB = ((D.GUIDE_ROD_X + (D.GUIDE_ROD_D + D.GUIDE_ROD_FIT) / 2)
              - (D.SCREW_X - (D.MR85_OD + 0.2) / 2 * 1.4143))
assert _GUIDE_WEB >= D.MIN_WALL - 1e-9, (
    f"only {_GUIDE_WEB:.2f} of slab between the guide-rod bore and the top bearing's "
    f"pocket (one bead is {D.MIN_WALL}) — it is set by NUT_HOLE_DX, still a guess")

# STRING SLOTS. The strings rise from the +X ears at D.STRING_ANCHOR_X and have to
# cross that same slab. They get a slot per string running OUT to the +X face rather
# than a hole, so a string DROPS IN SIDEWAYS once its ball is seated — the whole point
# of anchoring on the +X ear was that stringing stays a reach-in job, and threading a
# second blind hole 12 mm up would have given that back.
STRING_SLOT_W = 4 * D.BEAD                      # 3.2, clears the heaviest C6 string

# ── DRIVE RELIEF: the one extra prism under the changer room ───────────────
# The room's own floor now follows the nut down (ROOM_Z0), so the separate nut-sweep
# prism this used to need is gone with the carriage. What is still needed is relief
# for the things that TURN. The pulleys and the retaining collar sweep CIRCLES, not
# outlines — Ø11 and Ø8.8 about the screw line — which reaches x -2.5, and the
# endplate's foot block starts at x -4.2, so the pulleys were buried ~1.7 mm in it.
# That never showed up in the overlap gate because it compares parts where they SIT,
# and where they sit they only graze; the pair even sat in the allow list as an
# intended contact. Only a swept check finds it (tools/check_sweep.py).
DRIVE_SWEPT_R = D.PULLEY_FLANGE_OD / 2                    # 5.5 — the pulley is the
                                                          # widest turning thing left
DRIVE_X1 = D.SCREW_X + DRIVE_SWEPT_R + 0.4                # -2.1
DRIVE_Z1 = D.PULLEY_TOP_MAX + 0.4                         # -32.6
DRIVE_Z0 = D.SCREW_BOT_Z - 0.4                            # -53.4

# Room half-width: out to the arm inner faces, so the edge carriages / string
# balls are reachable through the room's +X opening (everything installs from +X).
WIN_HW     = D.BRIDGE_AXLE_Y - ARM_W / 2


MECH_HW = D.BRIDGE_AXLE_Y + ARM_W / 2   # field-centre upper-cap half-span (arm outer)
# +X-leg foot POCKET: the chassis now KEEPS a ~10 mm rail shell hugging the +X leg
# socket (CH._leg_shell over CH.LEG_SHELL_PX), so the leg is wrapped by body. The
# bridge's foot is therefore NOT a big empty box -- it is just the chassis-shell
# outer profile grown by a small assembly clearance, so the bridge nests over the
# kept shell as it drops -Z (no gap: leg -> 10 mm rail wall -> bridge, all touching).
FOOT_Z   = CH.KH_DT_Z0              # XBAR-above-tenon line (-23.15) = use-up box floor
LEG_CLR  = CH.EP_LEG_CLR            # assembly clearance around the kept chassis shell (shared)
LEG_SHELL_X0, LEG_SHELL_X1 = CH.LEG_SHELL_PX     # leg-wrap shell span (rail-takeover region)

# +Z RETENTION LIP (-Y bay, BRIDGE ONLY) -- see _build. A 5x5 mm bar protruding -X off
# the endplate's -X face at the deck-bottom plane, running in Y from the -Y rail inner
# face to the pickup piece's -Y skirt. The deck panels slide in OVER it (deck bottom and
# lip top both at z0), so once the deck is in the lip is trapped under it and the endplate
# can't lift +Z. Internal (under the deck) -> nothing shows on the outside. The keyhead
# is held in +Z separately (nut-block screw path), so it gets no lip.
LIP_DX  = 7 * D.NOZZLE_D                        # 5.6 -X protrusion off the endplate -X face (was 5.0)
LIP_DZ  = 7 * D.NOZZLE_D                        # 5.6 Z height, hanging below the deck bottom (was 5.0)
LIP_CLR = CH.EP_TOP_CLR                         # clearance to the rail inner face + skirt
LIP_Y0  = CH.Y_LO + CH.T / 2 + LIP_CLR          # -Y rail inner face + clr (-128.35)
LIP_Y1  = -(TP.HY_CLAMP + TP.SKIRT_T) - LIP_CLR # pickup -Y skirt outer face - clr; self-tracks the
                                                # top_plate -Y room (-(HY_CLAMP + SKIRT_T), ~-70.9 now
                                                # that the room sizes to PK_MAX_L=102, not the Alumitone)


def _cap() -> cq.Workplane:
    """SOLID BASE + box-closure plate at the +X end, from THE SHARED TWO-
    PRISM BASE (endplate_base — same code as the keyhead): the fill slab
    (z -23.15..6, full 25 footprint) = the +X cross-tie, and the hollowed
    foot box below it whose kept exterior walls are the +X END face
    (x -1.4..8.6, CH.T thick — no more 2.6 sliver) and the two +-Y side
    faces (= the rail takeovers; the chassis drops the rail ends here).
    Then cut only what the mechanism needs: THE CHANGER ROOM — one prism,
    |y| <= WIN_HW, ROOM_Z0..ROOM_Z1, through the whole X — where the
    nut sweep and the strings live (below ROOM_Z0
    nothing sweeps, so the base stays SOLID down to the bed).
    Only a field-centre upper band (z6..10) reaches the body top to back
    the window rim + axle comb + arm/tie roots. Foot clearance over each
    +X leg's kept chassis shell is pocketed afterward."""
    w = endplate_base(XLO, XHI, "hi")
    # CHANGER-TOP PRISM (user): a SOLID flat-topped shelf filled to the BEARING TOP, running from
    # the string TERMINATION — where the string breaks over its bearing and stops vibrating, i.e.
    # the bearing CENTRE, halfway along the bearing (D.BRIDGE_AXLE_X) — out to the +X tip. The
    # shelf is HIGH all the way to the termination; only −X of it (the vibrating speaking length)
    # does the top drop away. The bearings and their dead (non-vibrating) string rises are cut back
    # out of this prism afterwards (the field-centre opening below clears the low carriage sweep;
    # the bearing/string cuts in _build clear the rest). No +X drop past the termination — there is
    # no vibrating string there to dampen.
    w = w.union(box_at(X1 - D.BRIDGE_AXLE_X, 2 * MECH_HW, BEAR_TOP - Z6,
                       x=(D.BRIDGE_AXLE_X + X1) / 2, y=0, z=(BEAR_TOP + Z6) / 2))
    # THE CHANGER ROOM (see ROOM_Z1): one prism, arm face to arm face, the
    # bottom-stop plane up to the tower-relief ceiling, straight through the
    # whole X — the opening it leaves in the +X face IS the stringing access
    # (strings, balls and carriages all install from +X).
    w = w.cut(box_at((X1 + 1.0) - (XLO - 1.0), 2 * WIN_HW, ROOM_Z1 - ROOM_Z0,
                     x=((XLO - 1.0) + (X1 + 1.0)) / 2, y=0,
                     z=(ROOM_Z0 + ROOM_Z1) / 2))
    return w


def _arm(sy, blind=False) -> cq.Workplane:
    """Edge arm (clear of the strings) holding the axle. Spans the FULL endplate
    X-depth (axle line → +X tip) so it fuses solidly to the cap and prints with no
    overhang when built up along X.

    `blind=True` (the -Y arm) stops the bore AXLE_END_WALL short of the outer face:
    that wall is the shaft's -Y hard stop. See AXLE_END_WALL for why."""
    z_lo = CH.Z_TOP - 4.0
    arm = box_at(X1 - ARM_X, ARM_W, ARM_TOP - z_lo,
                 x=(X1 + ARM_X) / 2, y=sy, z=(ARM_TOP + z_lo) / 2)
    y0 = sy - ARM_W / 2 + (AXLE_END_WALL if blind else -1.0)
    h = (ARM_W / 2 + 1.0) - (y0 - sy)
    return arm.cut(printable_bore(
        AXLE_BORE, h, axis_point=(D.BRIDGE_AXLE_X, y0, D.BRIDGE_BEARING_Z),
        axis_dir=(0, 1, 0), print_up=PRINT_UP))


_SRX = D.SCREW_X + 9 * D.BEAD     # 7.2: screw-rail +X face (keep = screw_rail.X_PX)


def _comb_brace(yc: float, cb_w: float) -> cq.Workplane:
    """One finger's back-brace: constant width out to BRACE_X0, then a 45 deg flare in
    plan. Neighbouring flares merge into a solid bar; the outermost ones run on toward the
    arms. Nothing here is an overhang -- 1 mm of Y growth per 1 mm of X is exactly the
    self-supporting limit for a +X -> -X build."""
    hw0 = cb_w / 2
    hw1 = hw0 + (BRACE_X0 - BRACE_X1)          # 45 deg: Y growth == X run
    pts = [(-6.5, yc - hw0), (-6.5, yc + hw0),
           (BRACE_X0, yc + hw0), (BRACE_X1, yc + hw1),
           (BRACE_X1, yc - hw1), (BRACE_X0, yc - hw0)]
    flare = (cq.Workplane("XY").polyline(pts).close()
             .extrude(BRACE_Z1 - BRACE_Z0).translate((0, 0, BRACE_Z0)))
    # The END fingers sit close enough to the arms that their flare would otherwise run
    # out past the arm outer face and into the rail. Clamp every flare there.
    lim = D.BRIDGE_AXLE_Y + ARM_W / 2
    return flare.intersect(box_at(40.0, 2 * lim, BRACE_Z1 - BRACE_Z0,
                                  x=BRACE_X1 + 20.0, y=0.0,
                                  z=(BRACE_Z0 + BRACE_Z1) / 2))


def _build() -> cq.Workplane:
    body = _cap()
    for sy in (-D.BRIDGE_AXLE_Y, D.BRIDGE_AXLE_Y):
        body = body.union(_arm(sy, blind=sy < 0))     # -Y arm: blind bore = the -Y stop
    # +Y arm: the M2 grub that closes the shaft's one remaining direction
    body = cut_selftap(M2, body, (D.BRIDGE_AXLE_X, D.BRIDGE_AXLE_Y, AXLE_GRUB_Z),
                       (0.0, 0.0, -1.0), AXLE_GRUB_L, overshoot=0.5)
    # Tie bar linking the arm tops above the strings. Runs from the +X tip out to
    # TIE_X0 -- past the endplate block -- so its underside can carry the DOWN-FIRING
    # optical strip at OP.SENSE_X, ~20 mm off the string termination.
    # OPTICAL-STRIP CARRIER: a plinth reaching -X over the deck, top face at the board's
    # underside. Prints with the rest -- at x = XLO its whole cross-section is backed by
    # the endplate's z6..10 field-centre band, which is why CARRIER_HY stops at 54.
    # ...RUNNING THE BOARD'S WHOLE Y LENGTH, not just the sensing field (user). It used to
    # stop at +-CARRIER_HY because at x = XLO only the endplate's z6..10 field-centre band
    # backs it, and that band ends at the arms. Past there the WRAP/COMPUTE PLINTHS below
    # now provide the same backing, so the carrier can continue on top of them -- and it has
    # to: probed, the compute section and both wrap bands had NO material at x -29, -24 or
    # -18, i.e. ~20 mm of the board's 37.4 mm width was hanging over nothing.
    body = body.union(box_at(XLO - CARRIER_X1, OP.PCB_YP - OP.PCB_YM,
                             CARRIER_TOP - CARRIER_BOT,
                             x=(XLO + CARRIER_X1) / 2, y=(OP.PCB_YM + OP.PCB_YP) / 2,
                             z=(CARRIER_BOT + CARRIER_TOP) / 2))
    # ...and the TWO WRAP PLINTHS, +Y head and -Y tail, both sitting on the fill slab out
    # past the field centre. These carry the board's two M4 grips: the plinth alone is only
    # 3.66 thick, but it lands on solid slab, so the insert bores straight down through it
    # into the endplate body and gets full depth. Their inner Y edges OVERLAP the carrier
    # band so the -X carrier is backed continuously along its whole length.
    for _y0, _y1 in ((TAIL_Y0, TAIL_Y1), (CARRIER_HY, OP.PCB_YP)):
        body = body.union(box_at(TAIL_X1 - TAIL_X0, _y1 - _y0, CARRIER_TOP - CH.TP_GZ1,
                                 x=(TAIL_X0 + TAIL_X1) / 2, y=(_y0 + _y1) / 2,
                                 z=(CH.TP_GZ1 + CARRIER_TOP) / 2))
    for _mx, _my in OP.mount_points():
        # Screw enters from ABOVE, down through the board's clearance hole. The plinth is
        # only 3.66 thick but it sits ON the fill slab, so the anchor gets M4's full
        # anchor_min_wall (8.5 = insert pocket + a real bite) inside solid material.
        # Deeper than M4.anchor_min_wall (8.5) so a stock M4x12 -- the length already in
        # the BOM -- cannot bottom out: it reaches z -0.74 and the anchor floor is -1.34.
        # Depth is free here, the plinth sits on ~29 mm of fill slab.
        body = cut_anchor(M4, body, (_mx, _my, CARRIER_TOP), (0, 0, -1), depth=11.0)
    # FUSE IN the screw-support rail and bridge it to the cap at the bottom + tie it
    # up to the bearing arms at the edges — the whole bridge end becomes one solid
    # piece (screw support + bearing support + box closure) with continuous material.
    # The bottom + edge bridges run the FULL X-depth (screw line → +X tip).
    # DRIVE RELIEF (see DRIVE_X1) — cut FIRST, so the rail unioned in next survives.
    body = body.cut(box_at(DRIVE_X1 - (XLO - 1.0), 2 * WIN_HW, DRIVE_Z1 - DRIVE_Z0,
                           x=((XLO - 1.0) + DRIVE_X1) / 2, y=0,
                           z=(DRIVE_Z0 + DRIVE_Z1) / 2))
    body = body.union(_screw_rail)
    body = body.union(box_at(X1 - _SRX, 2 * D.BRIDGE_AXLE_Y,          # bottom bridge → tip
                             _SR_TOP - _SR_BOT,                       # tied to the rail, which
                             x=(X1 + _SRX) / 2, y=0,                  # moved up onto the pulleys
                             z=(_SR_BOT + _SR_TOP) / 2))
    z_lo = CH.Z_TOP - 4.0
    sr_bot = _SR_BOT                                                  # screw-rail −Z extent
    for sy in (-D.BRIDGE_AXLE_Y, D.BRIDGE_AXLE_Y):                    # edge webs rail→arm
        body = body.union(box_at(X1 - _SRX, ARM_W, z_lo - sr_bot,     # down to the rail bottom
                                 x=(X1 + _SRX) / 2, y=sy, z=(z_lo + sr_bot) / 2))
    # RE-CUT the bearing seats. The foot block below reaches -X to ~-4.2, which is
    # inside the +X sliver of every Ø8.2 seat, so the unions above refill 0.2 mm of
    # each bore. Cutting again here is the only place that sees the finished solid.
    body = body.cut(_seat_cutter())
    # (no +X deck-lock shelf / capture groove / dropped section / -Y roof: the solid
    #  base over the rail ends now IS the cross-tie + the deck panels' +X stop; the
    #  deck is held in +Z by the rail-top grooves along its length, not by the bridge.)
    # GUIDE-ROD LOWER LEDGE ONLY: bottom bar + blind landing sockets (rod bottom
    # retention). The UPPER stop bar + drop-in holes are DEFERRED (user: ignore stops
    # for now) -- the guide foot rides at the NUT LEVEL now, so an upper bar at that Z
    # protrudes -X into the string-nut path. The rod top rides free in the open field;
    # re-home the top retention + the top/bottom hard stops in a later endplate pass.
    # (No separate guide-view or stringing-access window cuts any more: the
    #  CHANGER ROOM prism in _cap opens the cap band down to ROOM_Z0, so the
    #  rods' free span is visible and the strings thread in from +X through the
    #  one opening. Below ROOM_Z0 the base stays solid.)

    # AXLE-SUPPORT COMB: nine fingers from the cap band above the stringing
    # window, one in each gap between bridge bearings. Without them the Ø3 axle
    # spans 103.5 mm carrying ~1.5 kN of string wrap load (≈28 mm computed
    # deflection — it would simply bend); the fingers cut the free span to one
    # string pitch (δ ≈ 0.004 mm, ~140 MPa in the shaft). Each finger: a ROOT on
    # the cap band, a flat underside riding the room ceiling (UNDER_Z), and a
    # HEAD with the axle bore on the axle line. Assembly is
    # still "set all 10 bearings in their slots, then slide the axle through
    # arms + finger bores + bearing bores in one pass" (axle must be a g6/h6
    # precision shaft, NOT an m6 dowel — see BOM), but the bearings are now held
    # by an OFF-INSTRUMENT fixture rather than by printed rest tabs.
    # REST TABS DELETED (user). They protruded 0.8 into each gap with a shallow V
    # at Z 8.0 to park each bearing's bore on the axle line. Two reasons they had
    # to go. PRINT: 0.8 is exactly one 0.8-nozzle bead, and the tab appeared
    # abruptly at x −2.0 with nothing behind it in the +X → −X build, so it was a
    # thin feature AND an overhang. FUNCTION, which is the worse one: that V sat
    # at the bearing OD tangent, i.e. bearing on the ROTATING OUTER RACE — the
    # surface the string rides — where ±0.2 of print tolerance could preload it
    # and add friction at the exact point the bearing exists to remove it.
    # 45° ramps keep every surface
    # self-supporting printing along X from the cap.
    # CB_W = pitch(9.5) − slot(4.8) so each finger is FLUSH with the slot walls: inner faces land
    # exactly on ±BR_HW, so the finger cannot poke into the opening (the old 5.2 sat at ±2.15, 0.25
    # inside the 4.8 slot → the "4.3" the user measured). The single slot cut now owns the opening
    # on BOTH Y faces; the finger is just the leftover between two slots. Cost the user accepted
    # (4.8 uniform over min-wall): the Ø3.3 axle bore in a 4.7 finger leaves 0.70 mm bore-side walls
    # — below the 0.8 1-bead floor, but SHORT and off the load path (the wrap loads the axle
    # DOWN-and-−X, so the grip is the solid finger BELOW the bore, not these side walls).
    CB_W = round(abs(D.string_y(1) - D.string_y(0)) - 2 * (D.BRIDGE_BEARING_W / 2 + 0.4), 3)  # 4.70: flush to the 4.8 slot
    # Finger head lowered 14.5 → BRACE_Z1 (14.01, the cover plane) so the −X region is ONE height,
    # not the axle-wall bump the user flagged. Safe because the string wrap sits on the bearing's
    # +X-top, so its load pushes the axle DOWN-and-−X — the bore's TOP wall carries none of it, and
    # the finger still grips the shaft from below/−X. The thin cap over the bore is just a
    # closure, not structure.
    # UNDERSIDE: one flat line at the room ceiling (UNDER_Z = ROOM_Z1). The old profile stepped
    # root 6.0 / web 7.8 / tip 6.5 with 45° ramps between — each step hugging a different ceiling
    # of the old four-cut field opening. One room plane deletes all of it.
    _fpro = (cq.Workplane("XZ")
             .polyline([(6.0, UNDER_Z), (-6.5, UNDER_Z),
                        (-6.5, BRACE_Z1), (-1.5, BRACE_Z1),
                        (3.0, 10.0), (6.0, 10.0)])
             .close().extrude(CB_W / 2, both=True))
    # A finger in every bearing GAP, plus one off EACH END of the axle (user), so all ten
    # bearings are flanked on both sides instead of the outer two leaning on the arm 4.5
    # away. 11 fingers, one half-pitch outboard of strings 1 and 10 -- close enough to the
    # arms that they merge into them, which is exactly the tie the end bearings wanted.
    _pitch = abs(D.string_y(1) - D.string_y(0))
    _comb_y = ([D.string_y(0) + _pitch / 2]
               + [(D.string_y(k) + D.string_y(k + 1)) / 2 for k in range(D.N_STRINGS - 1)]
               + [D.string_y(D.N_STRINGS - 1) - _pitch / 2])
    for yc in _comb_y:
        body = body.union(_fpro.translate((0, yc, 0)))
        body = body.union(_comb_brace(yc, CB_W))
        body = body.cut(printable_bore(
            D.BRIDGE_AXLE_D + 0.3, CB_W + 2,
            axis_point=(D.BRIDGE_AXLE_X, yc - CB_W / 2 - 1, D.BRIDGE_BEARING_Z),
            axis_dir=(0, 1, 0), print_up=PRINT_UP))

    # GUIDE-ROD SOCKETS. CUT HERE, AFTER THE COMB, and that ordering is load-bearing:
    # BRACE_Z0 is UNDER_Z is ROOM_Z1, so dropping the room ceiling 9.2 mm grew the comb
    # brace down by the same 9.2 and it swallowed these sockets whole — cut earlier,
    # they were unioned shut again and the rod ended up buried in solid plastic (user
    # caught it). The brace is no accident though: it flares 45° in plan until
    # neighbouring flares merge into one solid bar, so it IS the slab these bore into,
    # and it reaches from XLO to -6.5 — more depth than the socket asks for.
    # Teardrops, like every Z bore in this part: the axis runs sideways to the -X
    # build, so a plain cylinder droops out of round, and a socket that is not round
    # cannot hold a press fit square — which here is the entire job.
    for i in range(D.N_STRINGS):
        sy = D.string_y(i)
        # ONE bore, all the way from the slab's top down to the blind socket floor in
        # the rail. Everything it crosses on the way — slab, changer room, rail — is
        # either open or wants the hole, so it is a single cut rather than three.
        body = body.cut(printable_bore(
            D.GUIDE_ROD_D + D.GUIDE_ROD_FIT, GUIDE_DROP_Z1 - GUIDE_SOCKET_Z,
            axis_point=(D.GUIDE_ROD_X, sy, GUIDE_SOCKET_Z),
            axis_dir=(0.0, 0.0, 1.0), print_up=PRINT_UP))
    # TOP RADIAL BEARING seats, bored UP into the same slab. FLOATING: the pocket is
    # half a millimetre deeper than the bearing and has no shoulder either side, so it
    # can only locate the shaft radially — give it a face to push on and it would fight
    # the thrust stack for the string load and over-constrain the screw.
    for i in range(D.N_STRINGS):
        sy = D.string_y(i)
        body = body.cut(printable_bore(
            D.MR85_OD + 0.2, D.MR85_W + 0.5 + 0.01,
            axis_point=(D.SCREW_X, sy, D.TOP_BRG_Z0 - 0.01),
            axis_dir=(0.0, 0.0, 1.0), print_up=PRINT_UP))
    # STRING SLOTS through the same slab, one per string, running OUT to the +X face
    # so a string drops in sideways instead of being threaded down a second hole.
    for i in range(D.N_STRINGS):
        sy = D.string_y(i)
        body = body.cut(box_at((X1 + 1.0) - D.STRING_ANCHOR_X, STRING_SLOT_W,
                               (Z6 + 1.0) - GUIDE_SOCKET_Z,
                               x=(D.STRING_ANCHOR_X + X1 + 1.0) / 2, y=sy,
                               z=(GUIDE_SOCKET_Z + Z6 + 1.0) / 2))
    # LIGHT COVER for the optical strip, unioned in: its roof lands on the comb
    # brace at XLO and its slots sit over the sensor triplets.
    body = body.union(OP.opt_cover())
    # BEARING + STRING opening: ONE cut per string owns the whole opening (user). Constant ±BR_HW
    # width in Y over the whole rectangle, flat +X face — but a HOUSE plan (user), not a plain
    # prism: the −X end closes at 45° in plan to a ridge on the string line, because that end IS
    # the print ceiling. In the +X → −X build the +X end wall faces the bed (a floor — nothing to
    # fix, and the knife point the earlier "house" put THERE was rejected as a print reflex), but
    # the −X wall is backed by the brace/plinth from z 6.5 to 14.01, so a flat wall there is a
    # 4.8 × 7.5 downward-facing ceiling per slot — measured on the finished solid: ten 36 mm²
    # faces with n = (+1,0,0), the largest overhangs on the part. The gable is the comb
    # back-brace doctrine (45° in plan = self-supporting, see BRACE) applied to the cut: roof
    # planes at exactly 45°, ridge depth = BR_HW, peak buried 0.5 −X of the race, invisible in
    # use. The apex leaves 0.6–0.7 to the plinth/brace −X face, but that web is LAYER-direction
    # thickness (3–4 solid top layers over an already-closed void), not a bead-width wall — the
    # in-plan walls stay ≥ the slot's own. The slot still reaches −X past the bearing top and
    # TRIMS the comb finger/brace flare back to the wall line — the CUT, not the comb, sets the
    # opening on BOTH Y faces (that flare was the −X "angled shoulder" the user flagged). Both
    # bearing↔ and string↔endplate are gate-BLIND (allowlisted) → verified by hand (xsec/ywidth).
    # SIZED FROM THE BEARING AND THE FATTEST STRING (user), not from constants. The
    # slot has to contain the bearing's whole CIRCLE, because the bearing sits in this
    # opening between two comb fingers -- so every face of it derives from the OD and
    # the axle, and the +X face from the largest gauge's rise.
    #
    # This was -2.5 and Z6-1.0, tuned by hand when the bearing was O8. The 695ZZ round
    # took it to O13 and 788 mm3 of bearing ended up buried in endplate material --
    # and NOTHING REPORTED IT, because bearing<->endplate is one of the allowlisted
    # pairs. An allowlist is a promise that a contact is intended; it does not stay
    # true when the part it excuses changes size. Derived, it cannot go stale again.
    BR_CLR   = 0.5                                        # air round the race
    BR_HW    = D.BRIDGE_BEARING_W / 2 + 0.4               # opening half-width (bearing + clr)
    _br_x0   = D.BRIDGE_AXLE_X - D.BRIDGE_BEARING_OD / 2  # bearing -X extent
    _br_x1   = D.BRIDGE_AXLE_X + D.BRIDGE_BEARING_OD / 2  # bearing +X extent
    _br_z0   = D.BRIDGE_BEARING_Z - D.BRIDGE_BEARING_OD / 2   # bearing bottom
    SLOT_X0  = _br_x0 - BR_CLR                            # −X floor, clear of the race
    SLOT_X1  = max(D.BRIDGE_X + max(D.STRING_GAUGE) / 2 + 0.5,
                   _br_x1 + BR_CLR)                       # +X face: dead-string rise OR the race
    SLOT_Z0  = min(Z6 - 1.0, _br_z0 - BR_CLR)             # floor: the shelf OR the race's underside
    SLOT_Z1  = BEAR_TOP + 1.0                             # open above the string plane
    # the house pentagon in plan: |_| spanning SLOT_X0..X1, /\ ridge at SLOT_X0 − BR_HW on y 0
    _slot = (cq.Workplane("XY", origin=(0.0, 0.0, SLOT_Z0))
             .polyline([(SLOT_X1, -BR_HW), (SLOT_X1, BR_HW), (SLOT_X0, BR_HW),
                        (SLOT_X0 - BR_HW, 0.0), (SLOT_X0, -BR_HW)])
             .close().extrude(SLOT_Z1 - SLOT_Z0))
    for i in range(D.N_STRINGS):
        body = body.cut(_slot.translate((0.0, D.string_y(i), 0.0)))
    # FOOT POCKET: the chassis KEEPS a ~10 mm rail shell hugging each +X leg socket
    # (CH._leg_shell), capped at the foot line (z FOOT_Z = -23.15). Pocket exactly
    # that shell + a small assembly clearance out of the bridge so it nests over the
    # shell as it drops -Z. No empty box: leg -> 10 mm rail wall -> bridge, all
    # touching. The pocket ONLY clears z = Z_BOT .. FOOT_Z (over the shell) -- NOT
    # full-Z -- so the solid fill band (z -23.15..6) stays intact over the legs (the
    # band sits on top of the capped shell; the shell ends at FOOT_Z so nothing above
    # it needs clearing on the install drop).
    for yr, s in ((CH.Y_HI, 1), (CH.Y_LO, -1)):
        yf = yr + s * CH.T / 2 + s * LEG_CLR        # shell outer face + clearance
        yi = yr - s * CH.T / 2 - s * LEG_CLR        # shell inner face + clearance
        body = body.cut(box_at((LEG_SHELL_X1 + LEG_CLR) - (LEG_SHELL_X0 - 1.0),
                               abs(yf - yi), FOOT_Z - (CH.Z_BOT - 1.0),   # stop AT the foot line
                               x=((LEG_SHELL_X0 - 1.0) + (LEG_SHELL_X1 + LEG_CLR)) / 2,
                               y=(yf + yi) / 2,
                               z=((CH.Z_BOT - 1.0) + FOOT_Z) / 2))
    # SOCKET the rail-end dovetail tongue on each rail (keyhead-style, low band z
    # -23.15..-6): the endplate drops straight down onto the rail tongues. No glue —
    # the deck panels trap the +Z retention lip (see the module docstring).
    # The dovetail (wide +X / narrow -X) locks it in X+Y and grips the bearing-wrap
    # pull (-X); the low band leaves the cap free to drop to z6.
    for yr in CH.ENDPLATE_JOINT_Y:
        body = body.cut(CH._br_tongue(yr, socket=True))
    # LEG-STUB grooves (Y-INSTALL round — user: the stubs print on their
    # side and SLIDE IN ALONG Y): cut this end's corner negatives from the
    # SAME shared source the chassis uses (legs.corner_groove_negatives),
    # so the end-wall groove continues seamlessly across the kept-shell /
    # endplate boundary at the rail bands. The bridge hosts the 44-long
    # END-WALL groove at x 3.6 (wall centreline; blind inboard end = the
    # flush hard stop) — its band (bed..bed+7.34) sits far below the jack
    # recess floor (-55) and the guide windows.
    # relief=False: the 45° overhang wedge relieves the CHASSIS tongue
    # only — cut here it eats the end-wall groove roof (user-caught).
    # + the per-leg M4 LOCK SCREW ways along x through the end face
    # (Ø4.6 outboard cheek / Ø3.6 pilot through tongue + inboard cheek).
    from .legs import (corner_groove_negatives as _cgn,
                       endwall_screw_negatives as _esn)
    for _ly, _s in ((CH.LEG_Y[0], 1.0), (CH.LEG_Y[1], -1.0)):
        for _n in _cgn(CH.LEG_STATIONS_X[0], _ly, _s, 1.0, CH.Z_BOT,
                       relief=False):
            body = body.cut(_n)
        for _n in _esn(CH.LEG_STATIONS_X[0], _ly, 1.0, CH.Z_BOT):
            body = body.cut(_n)
    # PANEL I/O (the instrument's right face): the base's +X end wall is CH.T (10)
    # thick -- too deep for the jacks (their bodies span x -16..6) -- so RECESS its
    # interior back to a 4 mm panel at the -Y jack corner (the wall face at
    # JACK_WALL_X..XHI stays; the bodies seat through the recess into the hollow
    # foot interior). Recess band z (JACK_Z-14)..FOOT_Z, inside the hollow's Y span
    # (the Y-INSTALL leg grooves top out at bed+7.34, 12.7 below the recess floor,
    # so the recess is back at its full pre-EP-tenon size).
    # Then the three jack holes - 1/4" TS line out, DC power inlet, USB-C (audio-interface
    # port). Printed flat, so the panel + holes are vertical in the print - no supports.
    from .electronics import TS_Y, DC_Y, USB_Y, JACK_Z, JACK_WALL_X
    body = body.cut(box_at(JACK_WALL_X - (XLO - 1.0), 62.0, FOOT_Z - (JACK_Z - 14.0),
                           x=((XLO - 1.0) + JACK_WALL_X) / 2, y=-88.0,
                           z=(FOOT_Z + (JACK_Z - 14.0)) / 2))
    for jy, jd in ((TS_Y, 11.8), (DC_Y, 6.2)):   # Ø11.4 TS bushing, Ø5.7 DC thread
        body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            jd / 2, 6.0, cq.Vector(JACK_WALL_X - 1.0, jy, JACK_Z),
            cq.Vector(1, 0, 0))))
    body = body.cut(box_at(6.0, 13.2, 6.8, x=JACK_WALL_X + 2.0, y=USB_Y, z=JACK_Z))
    for sy in (USB_Y - 9.0, USB_Y + 9.0):       # USB-C flange screw pilots
        body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            1.25, 6.0, cq.Vector(JACK_WALL_X - 1.0, sy, JACK_Z),
            cq.Vector(1, 0, 0))))
    # +Z RETENTION LIP: protrudes -X under the deck in the -Y bay (see the LIP_* block);
    # the installed deck panels trap it, blocking the endplate from lifting +Z. Its +X face
    # is the endplate -X face (XLO); top is the deck-bottom plane (z0) so the deck rides it.
    body = body.union(box_at(LIP_DX, LIP_Y1 - LIP_Y0, LIP_DZ,
                             x=XLO - LIP_DX / 2, y=(LIP_Y0 + LIP_Y1) / 2,
                             z=CH.TP_GZ0 - LIP_DZ / 2))
    # ── CABLE CONDUIT, cut LAST so nothing unioned later refills it ──────────────────
    # Down from this part's top face, then out its -X face into the chassis interior.
    # Sized to pass a CONNECTOR one at a time -- see optical_pickup.opt_conduit. The
    # magnetic pickup's top panel is never touched: the deck ends at TP.PX0 = -16.60 and
    # the endplate begins there, so out past the board this face is open sky.
    #
    # IT MUST BE LAST. Cut earlier, the +Z RETENTION LIP above was unioned afterwards and
    # partly refilled it -- leaving a 0.25 mm sliver that read as a printability blip when
    # the real fault was structural.
    #
    # AND THE LIP HAS TO GO WITH IT across this Y band. The lip hangs off the -X FACE, and
    # the conduit removes that face here, so leaving the lip would leave a 5 x 5 tab rooted
    # on nothing -- worse than not having it. Trimming it costs 19.5 mm of its 57.4 mm run,
    # leaving 37.6 mm CONTIGUOUS (65%) still trapped by the deck panels, which is the one
    # piece of load-bearing material the conduit spends. There is no placement that avoids
    # it: the lip spans y -128.35..-71.30 and the conduit must sit -Y of the board at
    # -108.85..-131.85, so they overlap wherever it goes inside the endplate. The only
    # alternative was routing the USB lead ~47 mm back +Y to clear the lip entirely, which
    # buys whole-lip retention at the cost of a doubled-back cable and a longer run.
    body = body.cut(OP.opt_conduit())
    body = body.cut(box_at(LIP_DX + 2.0, OP.CONDUIT_D, LIP_DZ + 2.0,
                           x=XLO - (LIP_DX + 2.0) / 2 + 1.0,
                           y=(OP.CONDUIT_Y0 + OP.CONDUIT_Y1) / 2,
                           z=CH.TP_GZ0 - LIP_DZ / 2))
    return body


bridge_endplate = _build()
