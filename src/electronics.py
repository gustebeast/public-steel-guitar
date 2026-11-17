"""The TEST boards' CAD: output_panel, motor_ctrl, can_tee and pi_cap (R1, ordered).

What is left of the v1 electronics bay (lead, 2026-11-17, v1 removal round 3): only what
elec/cad_geom_check.py draws these four boards from -- each board's plate, parts and lettering.
The bay, the tray frame's cradles, the Pi and every placement in the v1 body went with the v1
instrument (git tag v1-instrument). The boards still sit where the v1 body put them, so the few
numbers that came from that body (its floor, its -Y rail, the Pi's motor) are FROZEN at their
values and say so; the check only compares each board against its own parts, so where they sit
does not matter to it.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import board_geom as BG      # the ROUTED boards -- see MCTRL_BOARD_X/Y below
from .helpers import box_at
from cadkit.pcb import jst_xh_side_header

_RAIL_INNER_Y = -105.05  # FROZEN, v1: chassis.Y_LO + chassis.T / 2, the -Y rail's inner face (tag v1-instrument)

# ---- bay geometry: the FLAT authoring frame (see THE STANDING FRAME below) ----
TRAY_X0, TRAY_X1 = -607.0, -547.0
TRAY_Z0, TRAY_Z1 = -64.0, -61.0        # plate band (3 thick) - 1.15 ABOVE the
# ⚠ THE MOTOR CONTROLLER STANDS LOWER, AND IT BUYS CLEARANCE IN X, NOT IN Z. The tray
# stands, so a board's standoff off the plate is a WORLD -X offset: less standoff puts the
# board further -X. That matters because the board is about to drop into the chassis
# bottom prism (Z -81.85..-71.35) so its two bus-B plugs can be reached from underneath,
# and the -X-most LEVER mortise is cut in that same prism with its -X wall at x -590.50.
# Everything entering that band has to stay 1.6 (one bead) clear of it, so at x <= -592.10.
#   the bus-B plugs sit at x -592.00 -- 0.10 mm over
#   1.5 mm of -X gives them 1.6 mm of bead AND leaves the access hole a real edge
# The tall mated XH plugs reach x -590.20 but never enter the prism band; they sit high on
# the standing board, which is why the whole-board bounding box was the wrong measurement
# (it said 1.90 mm was needed; only what descends into the band counts).
# The tray plate cannot move -X instead: it already bears on the endplate's inboard face.
MCTRL_POST_H = 1.7                     # user, 2026-09-25 -- 3.2 - 1.5
# The edge was never the problem; the POSITION along it was. At hold 0 the boss sits at the
# Pi's own z and reaches past its +Y edge once the Pi went flush. The clear window is the
# band between the Pi's BOTTOM edge (world z -62) and the floor's top (-72.15): about 10 mm,
# and the boss is 6. +17 centres it at z -67, roughly 5 mm clear of each.
# ⚠ AND THIS ONLY BECAME COMPUTABLE ONCE THE EAR WENT. pcb_hold_xy was being handed
# bw = 70.50, the outline INCLUDING the ear, so every hold on this board was measured from
# a rectangle the laminate does not occupy -- which is why three hand-picked positions in a
# row missed. The board is 61.80 now and the number means what it says.
# ⚠ AND NOT THE UNDERSIDE, which is where I put it first. "+x" reads CLEAR of every part,
# but this board passes THROUGH the floor, so a boss on that edge lands in the floor SLAB:
# 17.9 + 16.2 mm3 of chassis_2 that no cradle bore reaches. Boring the floor to hold a
# board is the same objection as the wall pocket this whole change exists to remove.
BD_T = 1.6
_PI_Y1 = -37.45  # FROZEN, v1: electronics._PI_Y1 = _MB_POSE.body_box(PI_MOTOR_I)[2] - D.PI_MOTOR_CLR (tag v1-instrument)
PI_FP     = (-588.0, -503.0, _PI_Y1 - D.PI_BOARD_L, _PI_Y1)   # WORLD x0,x1,y0,y1: 85 on X, 56 on Y;
# ⚠ THE -Y EDGE IS FLUSH WITH THE BAY WALL, AND THAT IS THE WHOLE POINT (user,
# 2026-09-29: "the pi is too far -y and requires cutting into the chassis wall which
# reduces its strength"). That wall runs y -141.95..-131.55 -- 10.40, exactly CH.T --
# and the Pi STACK's -Y face is the CAP, not the board: pi_cap overhangs 0.37 past the
# laminate, so the stack reached -135.37 and stood 3.82 INSIDE the wall. pi_cap_relief
# used to pocket that 3.82 away; moving +3.82 puts the cap exactly on -131.55 and the
# wall goes back to full thickness with nothing cut from it at all.
# ⚠ MEASURE THE STACK, NOT THE BOARD. Sliding by the board's own 3.45 would have left
# the cap 0.37 proud and the relief still necessary -- a 0.37 mm pocket instead of a
# 3.82 mm one, which is the same defect in a less visible size.
                                       # slid 19 SOUTH (FLUSH round): the wired
                                       # leg's jack chimney + cable drop own the
                                       # tray's west-north corner (x > -603 must
                                       # stay clear of y > 35 there; east is
                                       # walled by motor 0)


# THE SOUTH HALF WAS RE-LAID-OUT around the motor controller (2026-09-14). The
# Teensy stack and the teensy_ifc carrier are both gone -- one board does their job.
# (⚠ THE SIZES IN THIS PARAGRAPH WERE 40 x 35 AND A 90 DEG ROTATION, both true of the
# board as it stood on 09-14 and neither true since: it is 46 x 58 and UNROTATED, which
# is what MCTRL_BOARD_X/Y below already say. The constants moved and the
# prose above them did not.) The board sits in the -X -Y
# corner and the buck turns with it into the strip east of it. The ADC shifted
# 3 south to clear it; 0.5 of gap is all that is left between them, which is the
# honest state of a 60 x 181 tray holding four boards.
# ⚠ THE CRADLE IS PINNED TO THE ROUTED BOARD NOW (user, 2026-09-24: "we need the mounting
# plastic to be pinned to the board shape so they can't get out of sync").
# It was not, and the board had outgrown it: MCTRL_BOARD_X was a hand-typed 46.0 while the
# routed outline is 54.0, so the board overhung its own cradle by 8 mm -- 4 mm each side --
# and the cradle's border cut straight through both the board and its screw. motor_ctrl()
# already draws the PCB from BG.load("motor_ctrl")["outline_poly"], so the BOARD tracked
# reality and only the plastic around it did not. Nothing could have caught that: the two
# were never compared.
# Y was fine and shows what the right shape looks like -- MCTRL_EAR_H is already read off
# the same polygon, and 58.00 + 8.70 = 66.70 reproduces the routed bbox exactly.
# The rectangle's top is the highest y at which the outline is still FULL WIDTH; above it
# is the mounting ear, which is narrower and is accounted separately.
def _mctrl_rect():
    _poly = BG.load("motor_ctrl")["outline_poly"]
    _xs = [q[0] for q in _poly]
    _x0, _x1 = min(_xs), max(_xs)
    _ylo = min(q[1] for q in _poly)
    _yhi = min(max(q[1] for q in _poly if abs(q[0] - _x0) < 1e-6),
               max(q[1] for q in _poly if abs(q[0] - _x1) < 1e-6))
    return _x1 - _x0, _yhi - _ylo


# ⚠ ROTATED 90 AGAIN (user, 2026-09-25), AND FOR A REASON THE OLD NOTE DID NOT HAVE. The
# board's DOWNWARD edge is sterilised: nothing else may sit on it, because any other
# connector there would have its cable pointing into the chassis through the service hole.
# That cost is proportional to the edge's LENGTH, and the two bus-B JSTs need only ~24 mm
# of it -- so the narrow edge is the cheaper one to spend. 46 mm instead of 66.7.
# -Y and not +Y, because the mounting ear is on +Y and rotating THAT downward would bury
# the mount in the chassis floor.
MCTRL_BOARD_X, MCTRL_BOARD_Y = _mctrl_rect()   # straight from the routed outline: the
# board is authored in the orientation it is built in, so nothing is swapped here
# The tray POSITION is ours; only the SIZE comes from the board.
# ⚠ THE BOARD'S HEIGHT IS SET BY ITS BOTTOM EDGE MEETING THE FLOOR, AND IN THE FLAT FRAME
# THAT IS X. stand() maps flat +X to world -Z, so moving the board along the tray's length
# raises or drops it in the instrument -- and where it stops is what puts its two bus-B
# plugs within reach of a hand under the chassis (user, 2026-09-25).
# It lands the board's own bottom EDGE at world Z -71.00, against the bottom prism's top
# face at -71.35, so the board stops AT the chassis floor and only the PLUGS enter it
# (mated tips at -75.10, 3.75 mm into a 10.5 mm prism). That is two plug-sized holes
# instead of a slot for the board's whole edge, and a slot that long would cost far more
# of the floor than the holes do.
# ⚠ THIS WAS WRITTEN AS "12 mm LOWER THAN IT DID" AND THE NUMBER WENT STALE THE MOMENT THE
# BOARD WAS RE-AUTHORED IN ITS BUILT ORIENTATION. The 12 was measured when the board's
# VERTICAL span was the 46 mm edge; making the +X edge the downward one put the 68 mm span
# on Z instead, and the bottom edge fell to -83.60 -- 12.60 past the floor it was supposed
# to stop at, with the bare laminate buried 7.1 mm into the bottom prism. The comment went
# on describing the intent while the geometry did something else, and nothing compared the
# two. State the TARGET (bottom edge at the floor) rather than an offset from a position
# that no longer exists.
# ⚠ _MCTRL_CY IS SET BY THE MORTISES, AND IT WAS CHECKED AGAINST PLUG CENTRES RATHER
# THAN PLUG BODIES. The body-adapter mortises are two slots at x -608 and x -598, both
# ending at y -98 (measured off the built chassis, not off a station table). At -86.5 the
# plug centres sat at -78.5 and -94.5, which reads as clear -- but a mated PH plug is 12 mm
# across, so the -Y one spanned -100.5..-88.5 and clipped the x -598 slot over about
# 2.5 x 2.5 mm (user spotted it in the render, 2026-09-25).
# -82.0 puts the plug bodies at -80.0..-68.0 and -96.0..-84.0, so the nearer one clears
# y -98 by 2.0 mm with the 1.6 bead clearance inside that. Measure the BODY against the
# obstacle, never the centre.
# ⚠ THE TWO BOARDS SWAPPED ENDS ALONG Y (user, 2026-09-28, with a diagram). The motor
# controller was at the -Y end and the Pi at +Y; they are the other way round now. The reason
# that decided it is not comfort, it is the BODY ADAPTER: this board's cradle walls run down
# INSIDE the floor slab -- they have to, because the board's own bottom edge sits at the floor
# so its two bus-B plugs can enter it -- and at y -82 that put 170.65 mm3 of wall through
# body_adapter_3 at z -80.85..-73.82, which was handed to brenner as an unfixable-from-here
# conflict. The Pi has no such structure below the floor top: its foot rib stops at
# FLOOR_TOP + a bead (z -72.15), which is 1.67 mm ABOVE the top of that conflict zone. So
# putting the Pi at the -Y end retires the handover instead of relocating it.
#
# THE Y BUDGET IS EXACT AND THE BOSS IS WHAT SETS IT. Band -113..42.1, Pi 85 long, motor 62,
# and the Pi's M4 stands BESIDE its +Y edge (pcb_hold_xy "+y") reaching 7.1 mm past the board.
# So: Pi -113..-28, 8.1 of gap for that boss, motor -19.9..42.1. Moving the boss to the -Y
# edge instead would buy the gap back but would push a column out to y -120.1, into chassis
# that has never been asked to be there. Spend the gap, not the unknown.
# ⚠ ANCHORED ON THE FLOOR EDGE, NOT ON A CENTRE. This was a literal -563.40, which is the
# centre of a board whose WIDTH is about to change: dropping the vestigial ear takes
# MCTRL_BOARD_X from 70.50 to 61.80 (it is read off the routed outline), and a fixed centre
# would have slid both edges inward by 4.35 -- lifting the board's bottom edge off the floor
# it has to sit on for its two bus-B plugs to enter the floor slot. State the TARGET, which
# is the edge that must not move, exactly as the note above this block says for Y.
# -528.15 is where that edge is today; -563.40 = -528.15 - 70.50/2, so this is a no-op until
# the outline changes and then it is right by construction.
MCTRL_FLOOR_EDGE_X = -528.15           # tray +X edge == world z -80.85, the floor
# ⚠⚠ NOTHING CAN BE PLUGGED INTO THE PI, AND THE BAND CANNOT BE OPENED TO FIX IT
# (MEASURED 2026-09-29). pi4 ymax -46.18 against motor_ctrl ymin -41.50 is 4.68 mm, and a
# USB-A plug's overmould needs ~10 mm of Y beyond the port face even right-angled, ~22
# straight. I moved _MCTRL_CY -10.5 -> -0.5 to open it and the gate went 110 -> 115: the
# board ran into body_adapter_0 (91.41 mm3) and through all four 5 V conductors (4.0 each).
# THE MEASUREMENT THAT SETTLES IT: body_adapter(-X,+Y) spans y 21.15..65.95, so with the
# motor board's +Y edge at 20.50 there was 0.65 mm of slack above it, not 8.1.
#       band    body_adapter inner 21.15 down to the Pi's -Y face -131.18   152.33
#       boards  Pi 85.00 + motor 62.00                                      147.00
#       SLACK                                                                 5.33
# 5.33 is the whole budget, already spent as 4.68 between the boards and 0.65 above. The Y
# budget note below says the band is exact and it IS -- what is wrong in it is the claim
# that 8.1 mm is held for the Pi's +Y M4 boss and could be reclaimed now the boss has moved
# to +x. The gap is not reclaimable: the adapter caps the other end.
# ⚠ AND THE 5.7 mm OF CLEAR HEIGHT IS NOT A WAY OUT EITHER: motor_ctrl spans world x
# -606.50..-591.70 and the Pi's USB block -600..-586, so the top 5.7 mm of the port face has
# open +Y air above the motor board -- but a USB-A plug body is 8-12 mm tall.
# SO THE LEADS NOW END AT THE RIGHT PORTS, APPROACHED FROM THE RIGHT SIDE, IN A GAP NO PLUG
# FITS. That is the honest state and it is strictly better than a lead buried in the block.
# THREE WAYS OUT, none of them a nudge, all bigger than this file:
#   1. SHORTEN motor_ctrl IN Y. It is 62.00 off its own routed outline, so this is ours to
#      change; -8 mm buys a 12.68 gap. A board re-layout.
#   2. ROTATE THE PI 90 deg in its own plane: 56 along Y instead of 85 frees 29 mm of band,
#      and the tray has the Z for it. Relays the whole bay, the cradles and every lead.
#   3. TAKE wire_link OFF USB -- the Pi<->motor_ctrl link is travel offsets, low rate, and
#      could ride the GPIO header pi_cap already sits on. That removes one plug but not
#      wire_usb, which is the brain board's 20-channel USB audio and cannot move.
# ⚠ _MCTRL_CY -10.5 -> -7.0 GOES WITH BOARD_L 62.0 -> 55.0 (2026-09-29). The board lost
# 7.00 mm of bare laminate off its PI-FACING edge; _MCTRL_CY is a CENTRE, so leaving it at
# -10.5 would have taken 3.50 off each end and walked the +Y edge from 20.50 to 17.00 --
# shrinking away from body_adapter_0 but giving back half the gap the shrink existed to open.
# +3.50 holds the +Y edge at exactly 20.50, where it has always been and where body_adapter
# (inner face y 21.15) leaves it 0.65 mm.
#   before   y -41.50..20.50   gap to the Pi's port face (-46.18)   4.68
#   after    y -34.50..20.50   gap                                 11.68
# 11.68 takes a right-angle USB-A plug (~10 needed); a straight one (~22) still will not fit.
# ⚠ -58.75 TO THE -Y END (user, 2026-09-29: "having the motor board over at +y makes it
# quite cramped with the motor right next to it. Perhaps we should move it back to -y").
# ⚠⚠ THE OLD SWAP'S REASON NO LONGER BINDS, AND THE NUMBERS SAY WHY. The board went +Y
# because its cradle walls run BELOW the floor slab (they must -- the board's bottom edge sits
# at the floor so its two bus-B plugs can enter it) and at y -82 that put 170.65 mm3 through
# body_adapter_3. Measured now: ALL FOUR adapters top out at z -73.82, under FLOOR_TOP -71.35,
# and the cradle's below-floor material spans y -36.40..22.40. So the only hard limit is the
# adapter's +Y face at -97.15, and the cradle can travel 60.75 before reaching it.
# ⚠ motor_0 IS NOT A CONSTRAINT, though it is what looked cramped: it sits ON the floor
# (z -71.35..-29.05) while the below-floor cradle passes UNDER it, and above the floor the two
# are 8.1 mm apart in X. They already overlap in Y today without colliding.
# -58.75 leaves 2.0 mm to the adapter and drops the Y overlap with motor_0 from 55 mm to 3.
# ⚠ -71.05, BEHIND STRING 1'S MOTOR (user, 2026-10-02). The motor bank moved up to the
# keyhead endplate, so the board no longer stands between the two: it stands -Y of that
# motor, and ONE two-bead wall is both the motor's back stop and this board's +Y locating
# wall. The Y is dimensions' (MCTRL_Y0 / MCTRL_Y1) because the chassis' mortises, the motor
# bay and the -X/-Y body adapter all have to keep off it and none of them can import this
# file. Its -Y edge is now 1.40 PAST the adapter's +Y face (-97.15): the mortise over that
# foot stops a wall short of the board's port and the adapter is relieved under its edge.
_MCTRL_CX, _MCTRL_CY = MCTRL_FLOOR_EDGE_X - MCTRL_BOARD_X / 2.0, (D.MCTRL_Y0 + D.MCTRL_Y1) / 2.0
MCTRL_FP  = (_MCTRL_CX - MCTRL_BOARD_X / 2, _MCTRL_CX + MCTRL_BOARD_X / 2,
             _MCTRL_CY - MCTRL_BOARD_Y / 2, _MCTRL_CY + MCTRL_BOARD_Y / 2)
PI_Z = -57.74999999999999  # FROZEN, v1: electronics.PI_Z = _MB_FLOOR.FLOOR_TOP + PI_STANDOFF (tag v1-instrument)
MCTRL_BOARD_Z = TRAY_Z1 + MCTRL_POST_H   # ...except the motor controller, 1.5 lower

# ── THE STANDING FRAME (user, 2026-09-11) ────────────────────────────────────
# Everything above is the tray's FLAT layout -- plate, posts, boards -- and it is still
# the frame the tray PRINTS in. In the instrument the whole thing stands on its end with
# the plate's underside against the keyhead endplate's inboard face, so it takes only
# its stack depth in X instead of its 60 mm length, and the motor bank packs up to it
# (dimensions.MOTOR_X0). ONE rigid transform poses every part, so nothing inside the tray
# moves relative to anything else: rotate +90 deg about Y through the flat tray's -X
# bottom edge (up -> +X, the old +X end -> down), plate underside onto the keyhead face,
# bottom edge STAND_Z0.
# RETENTION LANDED 2026-09-20 (bronner): cradles fused into keyhead_endplate, one M4
# through each board's own mounting ear. The old drop-in side tabs and their rail
# channels are gone -- they did not line up with a standing stack.
STAND_Z0 = -62.0                       # bottom edge: 1.1 above the wired leg's TRRS pigtail
                                       # (top -63.1) where it runs east under this corner
STAND_DX = D.KEYHEAD_INBOARD_X - TRAY_X0
STAND_DZ = (STAND_Z0 + (TRAY_X1 - TRAY_X0)) - TRAY_Z0


def stand(wp: cq.Workplane) -> cq.Workplane:
    """Pose a part authored in the flat tray frame into the standing position."""
    return (wp.translate((-TRAY_X0, 0.0, -TRAY_Z0))
              .rotate((0, 0, 0), (0, 1, 0), 90.0)
              .translate((TRAY_X0 + STAND_DX, 0.0, TRAY_Z0 + STAND_DZ)))


# ---- panel jacks (through the endplate recess wall, kept 4 mm thick) ----
# The real connectors are deep (TS ~22 mm, DC ~15.5 mm). Behind the endplate
# the corner is open in X for ~100 mm (out to motor 0 at x -89) EXCEPT the low
# bridge cross-rib (tops at z -65). So the jacks ride HIGH (z -41), clear above
# the rib (and above where the AFE board used to sit) - their bodies then reach
# freely into the open bay.
# The +X face is now the centred 25 mm bridge's tip (BRIDGE_AXLE_X + 25/2 = 8.5), NOT
# X_BRIDGE+WALL -- the block is centred on the axle, not pinned to the rail end. Keep a
# 4 mm panel at that tip and slide the connectors (authored with their panel face at
# x~14) by JACK_FACE_DX so they ride the tip wherever it lands.
# ⚠ JACK_TIP READS THE ENDPLATE'S OWN +X FACE, and it used to compute a different one.
# It was BRIDGE_AXLE_X + ENDPLATE_W/2, annotated "= 8.5" -- true when D.BRIDGE_BASE_X1
# WAS 8.5. That constant has since moved to 25.06 and this formula did not follow, so
# JACK_TIP read 4.70: 20.36 mm -X of the face it is supposed to name.
#
# Both halves of the panel I/O ride this number, which is why one stale constant broke
# the whole interface and why fixing it here fixes both:
#   * the brain board rides JACK_FACE_DX (see output_panel), so it sat 20.36 mm too far
#     -X -- its USB-C, barrel and TS ended up in the bay instead of at the face;
#   * bridge_endplate cuts the 4 mm recess and the three jack bores at JACK_WALL_X, so
#     it was cutting them in FREE AIR 20 mm inboard of the wall. Probing the endplate at
#     the jack row (z -40.8, y -68/-85.5/-110) found no material anywhere in x -6..+12,
#     and the wall itself sitting at x 14.7..25.06 -- CH.T (10.4) thick, exactly as the
#     recess comment describes, and untouched.
# So the ports were not merely missing a cutout: the cutout existed and was being made
# somewhere else. Read the endplate's face from the same constant the endplate uses
# (bridge_endplate.XHI = D.BRIDGE_BASE_X1) and both land together.
JACK_TIP = D.BRIDGE_BASE_X1                          # the endplate's +X outer face (23.43)
# Fit clearance between the board and the plastic it registers against -- used both for
# the board's setback behind the panel and for the recess the endplate cuts around it.
# 0.3 is this project's usual printed-to-rigid fit (see pcb_cradle's clr default).
OP_PANEL_CLR = D.OP_PANEL_CLR             # (in dimensions: motor_bank's rail reads it)
# THE PANEL IN FRONT OF THE BRAIN BOARD IS 1.6, NOT 4.0 (user, 2026-09-21: "the board is
# also 4mm recessed from the endplate +x wall ... make the endplate thinner there so it's
# closer to flush"). The board's placements are built to the same two numbers --
# elec/output_panel.py PANEL_CLR / PANEL_T -- and output_panel() checks the ROUTED board
# against them, so neither side can move alone. 1.6 is also strong enough for the one part
# that bears on it: the TS jack's nut clamps this plate, which prints lying on the bed, so
# pushing the jack out means shearing ~75 mm2 of unbroken in-plane strands -- about 2 kN
# against Neutrik's 7 N withdrawal force.
OP_PANEL_T = 2 * D.BEAD
JACK_WALL_X = JACK_TIP - OP_PANEL_T                   # the panel's inner face


def _ctr(fp):
    return (fp[0] + fp[1]) / 2, (fp[2] + fp[3]) / 2


# ⚠ THE 40-PIN HEADER RUNS ALONG X, off the +Y long edge, and its place is READ OFF THE
# Pi's OWN DRAWING (src/pi4b.py HDR): its centre is midway between the two mounting holes
# on that edge, 32.5 along the board and 3.5 in from the edge, which is the line BETWEEN
# the two pin rows. Pin 1 is therefore 8.37 from the short edge.
# +Y edge chosen deliberately: the cap's two cable runs (the UI ribbon to the deck, and the
# LED strip) both go +Y, so the header faces the things it feeds.
from . import pi4b as _P4                                        # noqa: E402
PI_HDR_X = PI_FP[0] + _P4.HDR[0]                    # the pad centroid along the row
PI_HDR_Y = PI_FP[2] + _P4.HDR[1]                    # between the two pin rows
# ⚠ 11.0, NOT 8.5 (2026-10-07). The socket's body is 8.5, and it does not reach the Pi's
# board: it seats on the 2.5 mm plastic base of the Pi's own header. The cap was drawn
# 2.5 mm low, which hid that its J3 stood into the Pi's display connector (pi4 below).
PI_HDR_BASE = 2.5                                                # the Pi header's plastic
# R2: AN ADAFRUIT 4079 RISER BETWEEN THE Pi AND THE CAP (user, 2026-11-03). A 2x20 socket on
# 6 mm pins: it seats on the Pi's header base like the cap's own socket did, and the cap's
# socket seats on its body, 8.5 higher. That puts the cap's 6.0 side-entry connectors at 13.5
# over the Pi instead of 5.0: over the display / camera FFCs (5.5) and the audio jack (6.0),
# which is what lets the cap move inside the Pi's footprint. R1 (bench) has no riser.
PI_RISER_H = 8.5 if BG.PI_CAP_REV != 1 else 0.0      # adafruit.com/product/4079: 8.5 body
PI_CAP_STANDOFF = (BG.HEIGHT["PinSocket_2x20_P2.54mm_Vertical"] + PI_HDR_BASE + PI_RISER_H)


def pi_cap() -> cq.Workplane:
    """The Pi's connector board, plugged onto its GPIO header.

    The board goes on FACE DOWN: every part is on its front, and the front is the face
    toward the Pi, so the socket's body fills the standoff between the two boards -- which
    is why board_geom carries that 8.5 once and both this and the footprint read it from
    there.

    Its three through-hole parts -- the 2x20 socket, the ribbon header and J6, the foot
    drop's side-entry XH -- put their solder ends out of the OTHER face, the bare one
    toward the deck; board_geom draws them, so what stands over the cap has to clear
    them."""
    return _cap_place(BG.solid("pi_cap"))


def pi_cap_silk():
    """The cap's lettering, both faces -- its own part, so it can be white. The face
    that shows with the cap on the Pi is the board's BACK; _cap_place turns the ink over
    with the board."""
    w = BG.ink("pi_cap")
    return None if w is None else _cap_place(w)


_CAP_T = BG.load("pi_cap")["thickness_mm"]


def _cap_place(shape):
    """Put anything authored in the CAP'S BOARD FRAME where the cap is.

    ⚠ ONE TRANSFORM, USED BY EVERYTHING. The board, and every wire that has to land on one
    of its pins, go through this exact call -- because stand() inverts an axis and the last
    time that was reimplemented by hand it cut the wrong side of a part."""
    # ⚠ -4.5 SINCE THE CAP GREW TO 34 mm (elec/pi_cap.py). This is the number the whole
    # board is positioned BY -- the socket's y in the board's own frame -- so when the board
    # gained 8 mm on its -Y edge and every placement moved +4.00 with it, this moved too.
    # Leave it at -8.5 and the board lands 4 mm off the header it is supposed to plug into.
    # ⚠ BY J1's PADS, READ OFF THE ROUTED BOARD, NOT A TYPED -4.5 AND THE BOARD'S CENTRE
    # (2026-11-03). The geometry is centred on the board, so when the cap grew 7.0 at -X
    # (CAP_EXT_X) its frame moved 3.5 and the socket was drawn 3.5 mm east of the header it
    # plugs onto, every lead onto the cap with it. Placing by the pads cannot drift so.
    j1_x, j1_y = BG.footprint("pi_cap", "J1")["pads_xy"]
    # ⚠ NO ROTATE AND NO stand() SINCE THE PI WENT FLAT. The -90 existed to swing the cap's
    # socket (which runs along the cap board's own X) onto the header's axis, which was the
    # TRAY's y. Flat, the header runs along WORLD X -- the cap's own axis already -- so the
    # rotation is not just unnecessary, it would put the cap across the header.
    # The j1_y offset moves to Y for the same reason: it positions the socket, and the socket
    # now varies in y rather than x.
    # ⚠ FACE DOWN, TURNED OVER ABOUT ITS OWN X: the parts are on the board's front and the
    # front goes toward the Pi. That also turns the board's long axis around in y, which it
    # needs: the cap is 34 mm across a 56 mm board and the header sits 4.77 in from the +Y
    # edge, so the board it carries has to extend -Y OVER the Pi (the other way up in y it
    # reached y -57.27 -- 16.7 mm off the Pi's +Y edge, a HAT hanging in mid-air), and
    # j1_y therefore ADDS rather than subtracts. Turned over, the laminate lies below its
    # own z 0, so it is lifted by its thickness to stand on the socket.
    return (shape.rotate((0, 0, 0), (1, 0, 0), 180.0)
                 .translate((PI_HDR_X - j1_x, PI_HDR_Y + j1_y,
                             PI_Z + BD_T + PI_CAP_STANDOFF + _CAP_T)))


_OP = BG.load("output_panel")
OP_BOARD_X, OP_BOARD_Y = _OP["outline_mm"]
# THE BRAIN BOARD SITS AS LOW AS ITS PINS ALLOW (user, 2026-10-29: "Why is the brain board as
# high +Z as it is? Why not lower it so it's just as far above the floor as needed to clear its
# pins"). JACK_Z was a typed -40.8 and the board hung off it, 12 mm higher than anything needed.
# The chain runs from the floor up now:
#   the CHASSIS FLOOR (motor_bank.FLOOR_TOP -- under the whole board, in the bay and under the
#   endplate's hollow foot alike), the cradle's plate lying on it (OP_PLATE_T), the longest
#   THT tail below the board (3.4, every XH post and the R1 and R2 boards alike: bronner) plus
#   a fit, rounded up to whole beads (OP_STANDOFF) -- or the M4 insert's anchor depth under the
#   board's ear, if that is deeper (it is: 8.5 against 6.4, so the screw sets the height, not
#   the pins) -- gives the board's underside; the TS jack's axis above that is the row height.
from cadkit.pcb import XH_POST_TAIL as _OP_TAIL                        # noqa: E402
from cadkit.fasteners import M4 as _OP_M4                              # noqa: E402
OP_CHASSIS_FLOOR = -71.35  # FROZEN, v1: electronics.OP_CHASSIS_FLOOR = _MB_FLOOR.FLOOR_TOP (tag v1-instrument)
# THE PLATE STANDS OFF THE FLOOR (user, 2026-11-04): touching, it was a second stop fighting the
# endplate's own joinery for its install height. The gap is the endplate's clearance to the
# chassis everywhere else (chassis.EP_TOP_CLR, not imported: chassis imports this module).
OP_FLOOR_GAP = D.BEAD / 2.0               # 0.4
OP_FLOOR_Z = OP_CHASSIS_FLOOR + OP_FLOOR_GAP   # the cradle plate's underside (-70.95)
OP_PLATE_T = 3 * D.BEAD                   # the cradle's plate (bridge_endplate.op_cradle)
OP_TAIL_CLR = 0.3                         # air under the pins' cut ends, at least
OP_STANDOFF = math.ceil((_OP_TAIL + OP_TAIL_CLR) / D.BEAD - 1e-9) * D.BEAD   # 4.0
OP_UNDER_Z = OP_FLOOR_Z + max(OP_PLATE_T + OP_STANDOFF, _OP_M4.anchor_min_wall)   # -62.45
# the three connectors a player reaches through the panel, in the order they sit along it
OP_PANEL_REFS = ("J5", "J1", "J6")          # 1/4 in jack, USB-C, 24 V inlet


def output_panel_pcb() -> cq.Workplane:
    """The output + panel board in its OWN frame: centred on the origin in XY, underside
    at z = 0, parts rising +Z, the panel connectors facing +X -- built from the routed
    board, not from a table of what it was meant to be. J8, the pickup's screw terminal,
    is left out: src/screw_terminal.py draws it as the part (output_panel_term)."""
    return BG.solid("output_panel", skip=("J8",))


def output_panel_term() -> dict:
    """J8 posed with the board: {"housing", "metal"} (src/screw_terminal.py)."""
    from . import screw_terminal as ST
    return {k: v.translate(op_origin()) for k, v in ST.parts("output_panel", "J8").items()}


# ⚠ ONE ORIGIN FOR THE BOARD, because two copies of it drifted apart and put a 24 V
# feed outside the instrument. output_panel() posed the solid and op_pt() computed the
# same pose independently; when the pose was corrected in one, op_pt kept the old
# double-shift and returned J10 at x 28.81 -- 3.75 mm PAST the endplate's outer face at
# 25.06 -- so the wires leaving it were drawn through the wall. Anything that needs the
# board's world position reads this.
def op_origin():
    """World (x, y, z) the board solid is translated BY: its CENTRE in x and y, and
    its underside in z.

    X: the board's +X edge sits OP_PANEL_CLR behind the panel's inner face.
    Y: the board's -Y edge sits OP_PANEL_CLR off the -Y rail's inner face.
    Z: OP_UNDER_Z, the floor + plate + whatever clears the pins (or the M4's anchor). The
       panel's holes follow the board (op_panel_openings): each is centred on its own
       connector's axis. (They used to share the TS jack's one Z, which is how the USB-C hole
       ended up 7.85 mm too high.)"""
    return (JACK_WALL_X - OP_PANEL_CLR - OP_BOARD_X / 2,
            _RAIL_INNER_Y + OP_PANEL_CLR + OP_BOARD_Y / 2.0,
            OP_UNDER_Z)


def op_panel_fronts():
    """{ref: world x of the part's FRONT} -- where each connector finishes relative to the
    panel. The through-mount parts are meant to reach the face (JACK_TIP); J1 falls short
    by the board's J1_SETBACK because its own shell legs would otherwise cross the edge."""
    cx = op_origin()[0]
    out = {}
    for ref in OP_PANEL_REFS:
        m = BG.mouth("output_panel", ref)
        # a part with a NOSE finishes at the nose's tip, not at its body (the 24 V inlet)
        nose = m["spec"]["nose"]
        out[ref] = cx + m["front"] + (nose[2] if nose else 0.0)
    return out


def _check_panel():
    """The ROUTED board against the panel it is built for. Raises rather than drawing a
    board whose connectors cannot be reached -- which is what the old tables did, three
    ways, with every check passing."""
    fronts = op_panel_fronts()
    for ref in OP_PANEL_REFS:
        m = BG.mouth("output_panel", ref)
        assert m["dir"][0] > 0.99, (
            "output_panel %s's mouth faces %r, not +X out through the panel -- check its "
            "rotation on the routed board" % (ref, m["dir"]))
        if m["spec"]["mount"] == "through":
            assert JACK_TIP - 0.45 <= fronts[ref] <= JACK_TIP + 0.05, (
                "output_panel %s's front is at x %.2f; the panel face is %.2f -- a "
                "through-mount connector has to reach it" % (ref, fronts[ref], JACK_TIP))
        else:
            # a clamped part: its SHOULDER must sit where the clamp puts it, or the nut's
            # head is not flush and its plug does not meet the face with the others'
            sp = m["spec"]
            shoulder = fronts[ref] - sp["stub"][1]
            want = JACK_TIP - sp["clamp"] - sp["nut"][1]
            assert abs(shoulder - want) <= 0.05, (
                "output_panel %s's shoulder is at x %.2f, the clamp wants it at %.2f"
                % (ref, shoulder, want))


def output_panel() -> cq.Workplane:
    """The output + panel board posed at the bridge endplate: flat, panel connectors out
    through the wall at +X. See op_origin for how each axis is set."""
    _check_panel()
    return output_panel_pcb().translate(op_origin())


def output_panel_silk():
    """The brain board's lettering, both faces, where the board is -- its own part
    (white ink)."""
    return BG.ink("output_panel").translate(op_origin())


# ── MOTOR CONTROLLER PCB ─────────────────────────────────────────────────────
# ONE per instrument, and it REPLACES THREE THINGS: the Teensy 4.1, its SGTL5000
# audio shield and the teensy_ifc carrier. The Teensy's value was the Audio
# Library, USB high-speed and the codec, all irrelevant once no audio touches
# this board (user: audio goes to the Pi; this board reads angles off bus B,
# applies the saved travel offsets and commands the SERVO42Ds on bus A). What
# could NOT be deleted is the pair of CAN TRANSCEIVERS -- no general-purpose MCU
# integrates one -- so the board was always going to exist; the only question was
# whether an MCU sat on it too. It now does, which is what deletes the jumper
# harness that used to run from the Teensy stack to the carrier.
#
# ⚠ THE OUTLINE IS AN OUTPUT, like the TRRS adapter and unlike every purchased
# board here: 46 x 58 is what elec/motor_ctrl.py's own contents came to, and the
# TRAY was re-laid-out around it (see MCTRL_FP). It carries no rotation at all.
# (Said "40 x 35 ... stands 90 deg to the tray's X" until 2026-09-19, directly above
# a constant reading 46.0, 58.0. A number in prose beside the number it describes is
# the one place nothing checks; BOM.md carried the same stale 40 x 35 for this board
# and sized an enclosure row from it.)
# MCTRL_BOARD_X/Y are derived from the routed outline at the top of this file now.
# ⚠ THERE IS NO MCTRL_ROT ANY MORE, AND THAT IS THE POINT (user rule): the board is
# AUTHORED with its downward edge as +X (elec/motor_ctrl.py BOARD_W/BOARD_L), so posing it
# is stand() and nothing else. A rotation constant here meant two orientations in the
# codebase and a swap branch to reconcile them -- and to_tray carried a second copy of the
# same reconciliation for connector points.
# THE MOUNTING EAR, read off the ROUTED board (elec/geom/motor_ctrl.geom.json), moved into
# this file's frame: the rectangle's centre, which is what MCTRL_FP is written about. The
# geom file centres on the outline's BOX, which the ear pushes +Y by half its height.
def _mctrl_ear():
    poly = BG.load("motor_ctrl")["outline_poly"]
    ymin = min(p[1] for p in poly)
    dy = -ymin - MCTRL_BOARD_Y / 2.0                  # geom frame -> rectangle frame
    out = [(p[0], p[1] + dy) for p in poly]
    # ⚠ THE BOARD MAY HAVE NO MOUNTING HOLE AT ALL, and now does not: the ear was removed
    # (user, 2026-09-29 -- "a hole designed for an M4 screw that isn't being used"). This
    # used to unpack exactly one, which is an assertion disguised as a destructuring.
    _h = BG.holes("motor_ctrl")
    hole = (_h[0][0], _h[0][1] + dy, _h[0][2]) if _h else None
    ear_h = max(p[1] for p in out) - MCTRL_BOARD_Y / 2.0
    return out, hole, ear_h, dy


MCTRL_OUTLINE, MCTRL_HOLE, MCTRL_EAR_H, _MCTRL_DY = _mctrl_ear()


def motor_ctrl_pcb(mating: bool = False) -> cq.Workplane:
    """The motor controller, in its OWN frame: the rectangle centred on the origin in XY
    (its mounting ear off the +Y edge), underside at z=0, every part rising +Z -- the
    ROUTED board (board_geom.solid), not a table. `mating=True` stands the XH headers at
    their plugged height, which is the volume a housing has to leave alone."""
    return BG.solid("motor_ctrl", mated=mating).translate((0.0, _MCTRL_DY, 0.0))


# pi_cap_relief() lived here and is DELETED (user, 2026-09-29). It cut a 5.8 mm pocket in
# the bay's -Y wall so the Pi cap's 3.82 mm of overhang could sit inside it. The Pi now
# stands +3.82 further +Y with the cap FLUSH on the wall's face, so the wall is whole and
# the pocket has nothing to do. Kept as a note rather than silence because the pocket was
# deliberate and reasoned when it was written -- what changed is the board's position, and
# a reader finding the old call in history should see why it went rather than assume it was
# lost in a merge.
def motor_ctrl_silk():
    """The motor controller's lettering, through the SAME pose as the board itself."""
    cx, cy = _ctr(MCTRL_FP)
    return stand(BG.ink("motor_ctrl").translate((0.0, _MCTRL_DY, 0.0))
                 .translate((cx, cy, MCTRL_BOARD_Z)))


def motor_ctrl() -> cq.Workplane:
    """The motor controller posed in the standing tray (see MCTRL_FP)."""
    cx, cy = _ctr(MCTRL_FP)
    b = motor_ctrl_pcb(mating=True).translate((cx, cy, MCTRL_BOARD_Z))
    return stand(b)


# floor plane (bed top) — tee PCBs and the trunk-and-drop harness live here.
# = the LIVE chassis print-bed datum. Was a spelled-out -75.15, which had gone
# STALE: SCREW_TOP_Z, SCREW_PULLEY_Z and XBAR each moved onto the bead grid and
# the copy silently ended 0.2 below the real bed (-74.95). The off-grid audit is
# what caught it — a derived value that can't land on the grid means a parent
# moved without it.
FLOOR_Z = -81.18862925010151  # FROZEN, v1: electronics.FLOOR_Z = CH.Z_BOT (tag v1-instrument)

# ── CAN bus TEE PCB ──────────────────────────────────────────────────────────
# The SERVO42D has a SINGLE 6-pin XH (power+CAN); a single-port device can't be
# daisy-chained without soldering, so each node needs a 3-way junction -- this tee:
# TRUNK-IN + DROP + TRUNK-OUT + a switchable 120R terminator. Connectors are the
# real cadkit JST-XH: TOP-ENTRY (B4B-XH-A), cables rising +Z into the corridor
# harness, so the board packs compactly (the 15 mm SIDE-entry parts used on the
# knee lever would need a ~45 mm board -- infeasible at the 32 mm tee pitch). All
# three are 4-pin: a single-motor DROP needs only the 4 CAN conductors (gnd/24V/
# H/L), so the SERVO42D's 6-pin pigtail lands its 4 relevant wires here. Single-
# sided placement (all bodies on top); the THT posts drop 3.4 through the board
# and are cleared by a relief WINDOW in the cradle base (see wiring.tee_cradles).
TEE_CONN_N   = 4                                     # CAN = 4 conductors (gnd/24V/H/L)
# RESHAPED for the motor seats (bronner, 2026-09-14). It was 22 x 24 with three 4-way XH
# rotated 90 deg, which put a 16 x 11 band of 3.4-deep THT tails across the board's MIDDLE --
# unusable on a motor, where the only support is the faceplate wall's 6.4 strip and everything
# else overhangs the motor it has to lap. Now: ONE 8-way trunk (in on 1-4, out on 5-8) plus its
# own 4-way motor drop, pin rows COLLINEAR along X in a band at the +Y edge, so the tails land
# on the wall and the rest of the board laps the motor. Pulling the 4-way swaps a motor without
# disturbing the trunk -- which is what the tee is for.
TEE_BOARD_X  = D.TEE_BOARD_X                         # one row of 8-way + 4-way
TEE_BOARD_Y  = D.TEE_BOARD_Y                         # shallow: it sits ON the motor, not on the rail
TEE_YSHIFT   = 5.0                                   # board centre shift +Y so the -Y edge stays at y-7
TEE_TRUNK_N  = 8                                     # trunk in (1-4) / out (5-8) on ONE housing
# SIDE ENTRY (bronner, 2026-09-14): S8B-XH-A / S4B-XH-A, mouth facing -Y so the plugs run out
# OVER the motor instead of up. It stands 7.0 off the board where the top-entry pair stood 9.8
# mated -- and that 2.8 is what lets string 10's tee sit on its motor at all: the magnetic
# pickup's neck-most position dips to z -18.2 right over it. So the bank has no exception left.
TEE_CONN_CY  = 2.0                                   # PAD ROW: 6.0 in from the +Y edge, over the wall
TEE_MOUTH_DY = 3.25                                  # pad row -> mouth face (body 6.1, pads 2.85 off its back)


def tee_board_cy(y: float) -> float:
    """Board (and cradle) centre Y for a tee at station y: the -Y edge stays at y-7
    (clear of the -Y rail, as before); the board grows +Y into the open corridor."""
    return y + TEE_YSHIFT


def tee_conn_dx(which: str = "trunk") -> float:
    """X of a tee connector's centre, from the centre of the board's 40 mm LAYOUT region:
    the 8-way trunk (J1) or the 4-way drop (J2).

    READ OFF THE ROUTED BOARD (elec/geom/can_tee.geom.json), not worked out here. The two
    headers used to be drawn butted end to end and centred on the region, which is not
    where the board has them: there is 1.2 mm of laminate between the two housings, and
    the pair sits 0.65 toward -X. Drawn butted they read as one 12-way block (user,
    2026-10-06) and each stood 0.5 to 0.8 mm off its own pads. The geom file measures
    from the centre of the whole OUTLINE, ear included, hence the half ear."""
    f = BG.BOARDS.footprint("can_tee", "J1" if which == "trunk" else "J2")
    return f["pads_xy"][0] + D.TEE_EAR_X / 2


_TEE_INK = []


def tee_silk(x: float, y: float):
    """A tee's lettering, both faces, for the tee tee_pcb(x, y) draws -- its own part
    (white ink). The tee is modelled by hand, not from board_geom.solid, so its pose is
    read off the drawn board (cadkit.board_check.place) rather than written a second
    time; found once, at the origin, and moved with the board after that."""
    if not _TEE_INK:
        from cadkit.board_check import place
        _TEE_INK.append(place(tee_pcb(0.0, 0.0), BG.load("can_tee"), BG.ink("can_tee")))
    return _TEE_INK[0].translate((x, y, 0.0))


def tee_substrate(x: float, y: float, t_layout: float = 1.6) -> cq.Workplane:
    """The tee board's bare substrate, underside at FLOOR_Z: tee_pcb's board, and the printed
    dummy that stands in for it on the motor bay coupon (motor_bank.tee_dummy), which thickens
    the layout region to t_layout and leaves the ear at 1.6 for the M4 to clamp."""
    cy = tee_board_cy(y)
    # `x` is the OUTLINE centre. Bronner's 40 mm layout region is the -X part of it; off its
    # +X end is a bare EAR, D.TEE_EAR_X by D.TEE_EAR_Y at the +Y corner, with the retaining M4's
    # clearance hole through it. An L, not a rectangle -- see D.TEE_EAR_Y.
    xl = x - D.TEE_EAR_X / 2                         # the layout region's own centre
    ey = cy + (TEE_BOARD_Y - D.TEE_EAR_Y) / 2        # the ear's own centre Y
    # (below the ear the board's +X edge stands D.TEE_EDGE_BACK inside the region's line)
    b = box_at(TEE_BOARD_X - D.TEE_EDGE_BACK, TEE_BOARD_Y, t_layout,
               x=xl - D.TEE_EDGE_BACK / 2, y=cy, z=FLOOR_Z + t_layout / 2)
    # ...so the ear reaches back that much further to meet it
    b = b.union(box_at(D.TEE_EAR_X + D.TEE_EDGE_BACK, D.TEE_EAR_Y, 1.6,
                       x=x + TEE_BOARD_X / 2 - D.TEE_EDGE_BACK / 2, y=ey, z=FLOOR_Z + 0.8))
    return b.cut(cq.Workplane(obj=cq.Solid.makeCylinder(
        2.25, 3.6, cq.Vector(x + TEE_BOARD_X / 2, ey, FLOOR_Z - 1.0))))   # M4 clearance


def tee_pcb(x: float, y: float, drop: int = 1) -> cq.Workplane:
    """CAN bus TEE PCB dummy. ONE ROW of side-entry XH, drawn MATED (cadkit
    jst_xh_side_header): the 8-way trunk J1 (in on ways 1-4, out on 5-8) and beside it
    the 4-way drop J2 to the motor, each where the routed board has it (tee_conn_dx) --
    plus the 120 ohm terminator and its slide switch (ON only on each bus's LAST tee).
    Serves the 10 bus-A motor tees. `drop` = +-1 marks the device side (it does not
    change the board). Mount: ONE M4 THROUGH the bare ear off its +X end
    (wiring.tee_hold)."""
    top = FLOOR_Z + 1.6                              # board top face; connectors rise +Z from here
    cy = tee_board_cy(y)
    xl = x - D.TEE_EAR_X / 2                         # the layout region's own centre
    b = tee_substrate(x, y)
    # ONE row along X: the 8-way trunk, then the 4-way drop beside it. Pin rows collinear, so
    # the tail band is ~1.5 deep instead of 7.5 and clears the faceplate wall's strip.
    for n, dx in ((TEE_TRUNK_N, tee_conn_dx("trunk")), (TEE_CONN_N, tee_conn_dx("drop"))):
        b = b.union(jst_xh_side_header(n, smt=False, mated=True)
                    .translate((xl + dx, cy + TEE_CONN_CY - TEE_MOUTH_DY, top)))
    for px, py, sx, sy, h in (D.TEE_TERM_R, D.TEE_TERM_SW):       # 120 R and its switch
        b = b.union(box_at(sx, sy, h, x=xl + px, y=cy + py, z=top + h / 2))
    # THE THT TAILS AND THEIR SOLDER, under the board (user, 2026-11-03: they stood on the
    # motor's metal faceplate and shorted every pin -- and the overlap gate could not see it,
    # because they were not drawn). Each pin XH_POST_TAIL long; each joint a lump TEE_SOLDER_H
    # deep, grown TEE_SOLDER_GROW past its land all round, because real solder sits proud of
    # the pad. Read off the routed board's pads (outline-centre frame, as tee_conn_dx).
    from cadkit.pcb import XH_POST_TAIL
    under = top - 1.6
    for ref in ("J1", "J2"):
        f = BG.BOARDS.footprint("can_tee", ref)
        for px, py in f["pads"].values():
            b = b.union(box_at(TEE_PAD[0] + 2 * TEE_SOLDER_GROW, TEE_PAD[1] + 2 * TEE_SOLDER_GROW,
                               TEE_SOLDER_H, x=x + px, y=cy + py, z=under - TEE_SOLDER_H / 2))
            b = b.union(box_at(0.64, 0.64, XH_POST_TAIL, x=x + px, y=cy + py,
                               z=under - XH_POST_TAIL / 2))
    return b


TEE_PAD = (1.7, 1.95)          # XH THT land, X by Y (elec/geom/can_tee.geom.json)
TEE_SOLDER_GROW = 0.3
TEE_SOLDER_H = 1.0
