"""Electronics bay: compute hardware mounts + purchased-part dummies.

The PRO compute stack (per the compute plan) lives on one printed TRAY in the
keyhead bay (x -608..-530 - between the keyhead bulkhead and motor 9, under
the strings, above the open floor):

  - Raspberry Pi 5            (pro: 10ch audio->MIDI + Dexed + USB audio)
  - Teensy 4.1 + audio shield (basic+pro: sensors, CAN servo loop, UI, USB)
  - multichannel TDM ADC stack (pro: 10ch analog in; modeled stacked)
  - buck converter            (24V -> 5V for Pi + Teensy)
  - CAN transceiver breakout  (SN65HVD230: Teensy logic <-> CAN-H/L bus)

A BASIC build prints the SAME tray and just leaves the Pi/ADC/buck mounts
empty - the sockets are the upgrade path.

Mounting is tool-free and zero-hardware: each board sits on corner posts
between low locator strips and is retained by two 45-degree snap fingers
(all clearance-fit in the model - posts stop 0.2 under the board, finger
nubs hover 0.15 over it, so the gate sees no contact). The tray itself
drops in from above: a 40-wide tab on each side edge rides a vertical
channel cut in the rail web (open at the top, floor at the tab's z) -
gravity plus the wire loom holds it; lift straight out for service.

Panel I/O (TS line out, DC power in, USB-C) mounts through a 4 mm recessed
wall in the bridge endplate's lower -Y corner - the endplate prints flat so
the holes are print-trivial, and the inside there is empty floor band.
"""

from __future__ import annotations

import re

import cadquery as cq

from . import dimensions as D
# Everything chassis reaches BACK for lives above the chassis import -- see the note
# below. (The AFE board's footprint used to live here; it is deleted.)
# The jack row below is DERIVED from the bridge axle, not hardcoded. The endplate's inboard wall follows
# BRIDGE_AXLE_X (= BRIDGE_X - OD/2, because the string rides the OD and has to leave
# at x = 0), so when the bearing grew Ø8 -> Ø13 the axle stepped 2.5 -X and the wall
# came with it — straight through this board's +X edge, which sat at a constant.
# NOTE: this block sits ABOVE the chassis import ON PURPOSE. chassis builds at
# import time and used to reach BACK here for the AFE_* constants to cut its
# matching boss; the AFE is gone but the ordering still matters for the rest.
# boss (it once also read the tray tab/channel constants, now gone). With the constants below the import, that reach-back hit a
# half-initialised module and `import src.electronics` failed outright with a
# circular-import ImportError -- only working at all because everything else
# happened to import chassis first. These are plain literals, so hoisting them is
# free and makes the module importable on its own.
# ---- bay geometry (the tray's FLAT frame; see STANDING TRAY below) ----
TRAY_X0, TRAY_X1 = -607.0, -547.0
TRAY_Y0, TRAY_Y1 = -127.5, 53.5        # 1.25 off each rail inner face
TRAY_Z0, TRAY_Z1 = -64.0, -61.0        # plate band (3 thick) - 1.15 ABOVE the
                                       # x -575 rib top so the bay rib passes
                                       # under the tray


from . import board_geom as BG      # the ROUTED boards -- see MCTRL_BOARD_X/Y below
from . import chassis as CH          # only early constants (X_*, Z_*) used here
from .helpers import box_at, cyl, cyl_x
from cadkit.pcb import (PCB_T as _PCB_T, jst_xh_header, jst_xh_side_header,
                        xh_length, xh_side_length)

# ---- board footprints (x0, x1, y0, y1); board bottom z = TRAY_Z1 + post ----
POST_H = 4 * D.BEAD                    # 3.2 printed standoff posts under each board
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
# ⚠ ONE SOURCE. This was a local 0.3 inside electronics_bay(), and board_screws() has to
# place the Pi's M4 at the SAME spot that function bores the anchor -- pcb_hold_xy() takes
# the clearance as an argument, so two copies of the number is two places for the screw and
# the hole it goes in to drift apart.
CRADLE_CLR = 0.3

# ⚠ WHERE EACH BOARD IS HELD, IN ONE PLACE, BECAUSE IT WAS IN TWO AND THEY DRIFTED.
# keyhead_cradles() BORES the anchor and board_screws() DRAWS the screw that goes in it,
# and each called pcb_hold_xy with its own literal edge. Moving the screws to the boards'
# undersides changed one copy and not the other, so the gate came back with four fresh
# chassis_2 overlaps -- the fasteners standing in cradle material because the hole was
# still being bored on the old edge. The comment at the top of this file already warned
# that two copies of this number is two places for the screw and its hole to drift apart;
# it was right, and the answer is to stop having two.
#   (edge, hold_at) -- searched against the built assembly, see board_screws()
MCTRL_HOLD = ("-y", 17.0)     # ⚠ the -Y EDGE STILL, but slid +17 along it
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
PI_HOLD    = ("+x", 0.0)
BD_T = 1.6
# ⚠⚠ THE PI LIES FLAT ON THE CHASSIS FLOOR AND THESE ARE WORLD COORDS (user, 2026-09-29,
# with two drawings: the footprint on a plan view and the board in it, "with the I/O facing
# +x"). It is NOT a tray part any more -- it does not go through stand() -- exactly as the
# output board already does not. 85 on X, 56 on Y, ports on the +X END.
# WHY: standing, the Pi ate 85 mm of a Y band only 152 wide, which is what squeezed its USB
# gap to 4.68 and made ask #3 unfixable by placement. Flat it eats 56, freeing 29 mm.
# MEASURED, not chosen: an 85 x 56 x 15.6 box here collides with NOTHING (0.00 mm3 against
# every part but the ones that move with it and the cables), and the floor under it is 90.3%
# solid across the whole footprint, so there is no hole at the leg station.
# ⚠ +8 IN X AND +3 IN Y OFF THE FIRST CLEAN POSITION (user, 2026-09-29: "move the pi over
# +x"). The +8 clears the compute bay's x range (-606.50..-591.70) so the motor board can come
# -Y past it -- the two moves are a package and neither works alone. The +3 buys wall for the
# floor retention on the -Y side, which the sweep found had ZERO room (the Pi sat hard against
# chassis_2; +5 hit it). Sweep says +X is clear to 80 and +Y to 20, so both are cheap.
PI_FP     = (-588.0, -503.0, -127.0, -71.0)   # WORLD x0,x1,y0,y1: 85 on X, 56 on Y;
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
# (MEASURED 2026-09-29). pi5 ymax -46.18 against motor_ctrl ymin -41.50 is 4.68 mm, and a
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
#      wire_usb, which is the output board's 20-channel USB audio and cannot move.
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
_MCTRL_CX, _MCTRL_CY = MCTRL_FLOOR_EDGE_X - MCTRL_BOARD_X / 2.0, -65.75
MCTRL_FP  = (_MCTRL_CX - MCTRL_BOARD_X / 2, _MCTRL_CX + MCTRL_BOARD_X / 2,
             _MCTRL_CY - MCTRL_BOARD_Y / 2, _MCTRL_CY + MCTRL_BOARD_Y / 2)

# ⚠ THE PI IS PINNED TOO, but to its DATASHEET rather than to a routed outline -- it is a
# purchased board and there is no elec/geom for it. PI_FP is already the single source for
# both the dummy in pi5() and the cradle in keyhead_cradles(), so those two cannot drift
# from each other; what was missing is anything tying PI_FP to the actual Pi. A Pi 5 is
# 85 x 56 mm (RPi mechanical drawing), long side on X here, FLAT. If someone re-sizes this to
# make something fit, the assert is what says the board stopped being a Pi.
assert (round(PI_FP[1] - PI_FP[0], 3), round(PI_FP[3] - PI_FP[2], 3)) == (85.0, 56.0),     "PI_FP is %.1f x %.1f; a Pi 5 is 85 x 56" % (PI_FP[1] - PI_FP[0], PI_FP[3] - PI_FP[2])

BOARD_Z = TRAY_Z1 + POST_H             # every bottom board sits at -67
# ⚠ THE PI HAS ITS OWN Z AND IT IS A WORLD ONE: it lies on the chassis floor, not on the
# tray's posts, so BOARD_Z (a TRAY z) does not apply to it. Read from motor_bank so the day
# the floor moves the Pi moves with it, instead of being falsified by it.
from . import motor_bank as _MB_FLOOR                      # noqa: E402
PI_Z = _MB_FLOOR.FLOOR_TOP             # -71.35, the laminate's underside
MCTRL_BOARD_Z = TRAY_Z1 + MCTRL_POST_H   # ...except the motor controller, 1.5 lower

# ── STANDING TRAY (user, 2026-09-11) ─────────────────────────────────────────
# Everything above is the tray's FLAT layout -- plate, posts, boards -- and it is still
# the frame the tray PRINTS in. In the instrument the whole thing stands on its end with
# the plate's underside against the keyhead endplate's inboard face, so it takes only
# its stack depth in X instead of its 60 mm length, and the motor bank packs up to it
# (dimensions.MOTOR_X0). ONE rigid transform poses every part, so nothing inside the tray
# moves relative to anything else: rotate +90 deg about Y through the flat tray's -X
# bottom edge (up -> +X, the old +X end -> down), plate underside onto the keyhead face,
# bottom edge STAND_Z0.
# NO MOUNT YET (user): bronner is reworking the keyhead endplate, so retention is left
# for that round. The old drop-in side tabs and their rail channels are gone -- they
# do not line up with a standing tray.
STAND_Z0 = -62.0                       # bottom edge: 1.1 above the wired leg's TRRS pigtail
                                       # (top -63.1) where it runs east under this corner
STAND_DX = D.KEYHEAD_INBOARD_X - TRAY_X0
STAND_DZ = (STAND_Z0 + (TRAY_X1 - TRAY_X0)) - TRAY_Z0


def stand(wp: cq.Workplane) -> cq.Workplane:
    """Pose a part authored in the flat tray frame into the standing position."""
    return (wp.translate((-TRAY_X0, 0.0, -TRAY_Z0))
              .rotate((0, 0, 0), (0, 1, 0), 90.0)
              .translate((TRAY_X0 + STAND_DX, 0.0, TRAY_Z0 + STAND_DZ)))


def stand_pt(x: float, y: float, z: float):
    """The same transform for a single point (wiring endpoints on the boards)."""
    dx, dz = x - TRAY_X0, z - TRAY_Z0
    return (TRAY_X0 + STAND_DX + dz, y, TRAY_Z0 + STAND_DZ - dx)


# the dimensions datum the motor bank is packed against has to hold the real boards:
# tallest part above the plate's underside in the flat frame = depth in X once standing
_PI_TOP = BOARD_Z + BD_T + 14.0                # Pi 5 USB/ethernet block top (see pi5)
_MCTRL_TOP = MCTRL_BOARD_Z + BD_T + 9.8        # a MATED XH on the motor controller
_STACK = max(_PI_TOP, _MCTRL_TOP, BOARD_Z + BD_T + 9.0) - TRAY_Z0   # (+ buck caps)
assert _STACK <= D.ELEC_STACK_D + 1e-6, (
    f"the electronics stack is {_STACK:.2f} deep standing, over dimensions.ELEC_STACK_D "
    f"{D.ELEC_STACK_D} -- the motor bank is packed against that number")

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
#   * the output board rides JACK_FACE_DX (see output_panel), so it sat 20.36 mm too far
#     -X -- its USB-C, barrel and TS ended up in the bay instead of at the face;
#   * bridge_endplate cuts the 4 mm recess and the three jack bores at JACK_WALL_X, so
#     it was cutting them in FREE AIR 20 mm inboard of the wall. Probing the endplate at
#     the jack row (z -40.8, y -68/-85.5/-110) found no material anywhere in x -6..+12,
#     and the wall itself sitting at x 14.7..25.06 -- CH.T (10.4) thick, exactly as the
#     recess comment describes, and untouched.
# So the ports were not merely missing a cutout: the cutout existed and was being made
# somewhere else. Read the endplate's face from the same constant the endplate uses
# (bridge_endplate.XHI = D.BRIDGE_BASE_X1) and both land together.
JACK_TIP = D.BRIDGE_BASE_X1                          # the endplate's +X outer face (25.06)
# Fit clearance between the board and the plastic it registers against -- used both for
# the board's setback behind the panel and for the recess the endplate cuts around it.
# 0.3 is this project's usual printed-to-rigid fit (see pcb_cradle's clr default).
OP_PANEL_CLR = 0.3
# THE PANEL IN FRONT OF THE OUTPUT BOARD IS 1.6, NOT 4.0 (user, 2026-09-21: "the board is
# also 4mm recessed from the endplate +x wall ... make the endplate thinner there so it's
# closer to flush"). The board's placements are built to the same two numbers --
# elec/output_panel.py PANEL_CLR / PANEL_T -- and output_panel() checks the ROUTED board
# against them, so neither side can move alone. 1.6 is also strong enough for the one part
# that bears on it: the TS jack's nut clamps this plate, which prints lying on the bed, so
# pushing the jack out means shearing ~75 mm2 of unbroken in-plane strands -- about 2 kN
# against Neutrik's 7 N withdrawal force.
OP_PANEL_T = 2 * D.BEAD
JACK_WALL_X = JACK_TIP - OP_PANEL_T                   # the panel's inner face
JACK_Z = -51 * D.BEAD                  # -40.8 jack row centre height
# THE PANEL ROW IS NO LONGER EVENLY PITCHED, and it is not meant to be. TS and USB
# are now BOARD parts on output_panel and their spacing (31.27) is set by that board;
# only the DC inlet is still a free-standing panel jack, and it MOVED OUT of the
# board's span. It had been at -86, between the other two -- which put the 24 V pair
# for ten stepper drivers straight through the board that carries the output buffer,
# and the overlap gate found the wires passing through the PCB. At -118 it is 10 mm
# clear of the board, 10.75 from the -Y rail's inner face, and 50 mm from the audio
# jack, which is the separation that matters.
TS_Y = -68.0                           # THE ONE PANEL INPUT. Every other panel hole
                                       # is now an OUTPUT of the output+panel board
                                       # (see op_panel_openings) -- put all three
                                       # jacks on one PCB and the ROUTED board, not
                                       # this file, decides where the holes go.

# ---- UI: OLED + joystick on the top deck (mounted to the top plate) ----
# Centred along X. NOTE: the strings cover the deck within +-42.75 with only
# ~2 mm clearance, and the +Y/string-10 edge is just ~12 mm wide before the
# rail - too narrow for the 38 mm screen. So the UI sits on the WIDE -Y deck
# band (86 mm, over the motor PCBs, clear of the strings). The joystick (Alps
# RKJXT1F42001: 2-way rotary + 4-way + push) is the sole control.
UI_X      = (CH.X_BRIDGE + CH.X_NUT) / 2     # instrument X centre
DECK_TOP  = D.DECK_TOP_Z                      # 6.4 — THE deck datum (was a stale
                                              # STRING_Z - 10 = 6.0, which sank the UI
                                              # dummies 0.4 into the deck plate); 9.6
                                              # under the strings, bar still can't bottom
OLED_Y    = -100.0                            # wide -Y deck band (clear of strings)
OLED_W, OLED_L, OLED_T = 38.0, 72.0, 1.6      # 2.42" module PCB (Y x X)
JOY_X     = UI_X + 70 * D.BEAD                # -252.17: just +X of the screen
JOY_Y     = -102 * D.BEAD                     # -81.6


def oled() -> cq.Workplane:
    """2.42" 128x64 OLED module dummy: PCB + glass + header, face up."""
    b = box_at(OLED_L, OLED_W, OLED_T, x=UI_X, y=OLED_Y, z=DECK_TOP + OLED_T / 2)
    b = b.union(box_at(62.0, 33.0, 2.0, x=UI_X, y=OLED_Y,
                       z=DECK_TOP + OLED_T + 1.0))          # glass active area
    b = b.union(box_at(20.0, 2.5, 5.0, x=UI_X, y=OLED_Y - OLED_W / 2 + 2.0,
                       z=DECK_TOP + OLED_T + 2.5))          # pin header (-Y edge)
    return b


def joystick() -> cq.Workplane:
    """Alps RKJXT1F42001 multi-control dummy: ~13 mm body + actuator cap."""
    b = box_at(13.0, 13.0, 9.0, x=JOY_X, y=JOY_Y, z=DECK_TOP + 4.5)
    b = b.union(cyl(7.0, 6.0, z=DECK_TOP + 9.0).translate((JOY_X, JOY_Y, 0)))
    return b

# ---- analog front end (bridge-end -Y corner, near the pickup + jacks) ----
# JFET buffer + SPDT signal relay (true-bypass: de-energized = raw straight to
# the jack; energize = the Q-processed DAC output) + relay driver/flyback +
# a local low-noise LDO fed from the nearby 24 V inlet. Clustering all the
# noise-sensitive analog here (away from the motor drivers) is the whole point;
# only buffered/line-level/logic runs make the long trip to the keyhead bay.


def _support_posts(fp, bz):
    """Four plain corner posts for one board footprint (tops flush with the board bottom --
    the board RESTS on them). Support only: NO retention for now (user, 2026-09-10). The M2
    corner anchor, its fat boss and the two locator strips that used to live here are gone;
    these boards are revisited later under the one-M4-beside-the-board rule
    (cadkit.pcb.pcb_cradle hold_edge), so nothing here should grow an M2 back."""
    x0, x1, y0, y1 = fp
    out = cq.Workplane("XY")
    for px in (x0 + 5, x1 - 5):
        for py in (y0 + 5, y1 - 5):
            out = out.add(cyl(5.0, bz - TRAY_Z1, z=TRAY_Z1).translate((px, py, 0)))
    return out


# -- where the cradles' columns start, in the FLAT tray frame -------------------------
# stand() maps this frame to the world as  world_x = local_z - 543.8, so:
RIB_LZ    = -87.5        # local z -> world x -631.3: just inside the endplate's own wall,
                         # which ends at -631 behind the Pi and -627 behind the controller


def keyhead_cradles(standing: bool = True) -> cq.Workplane:
    """The Pi's and the motor controller's mounts, built INTO the keyhead endplate.

    ⚠ THIS REPLACES electronics_tray, AND _support_posts SAID IT WOULD: "these boards
    are revisited later under the one-M4-beside-the-board rule (cadkit.pcb.pcb_cradle
    hold_edge), so nothing here should grow an M2 back". The tray was a separate printed
    plate that stood against the endplate carrying four bare posts per board and NO
    retention at all -- the boards simply rested on them. This is that revisit.

    Each board gets its own cradle, independent of the other: walls capture it in the
    plate's plane, a lip under its edge carries it off the face, so the only way in or out
    is straight off the face -- and one M4 button closes that (through the motor
    controller's mounting ear; beside the Pi's +Y edge, its holes being too small). Same pattern, same
    single 2.5 mm hex key, as the motor tees and the output board.

    Authored in the FLAT tray frame (where PI_FP/MCTRL_FP and BOARD_Z are written) and
    posed by stand(), exactly as the tray was, so the footprints stay the numbers this
    file already carries. standoff is POST_H -- the height the posts used to stand the
    board off the plate -- so the boards do not move.

    The -Y side is open above the board for both: that is the rail the harness runs along, and a wall there
    would sit across every lead leaving the board.

    EACH ONE IS ATTACHED BY ITS OWN COLUMNS. The tray was a plate standing ~22 mm proud of
    the endplate's inboard face, and the first cradles fused at the tray's position attached
    to nothing -- the motor controller's came out a free-floating 18,121 mm3 lump, which the
    overlap gate cannot see (two solids that never touch do not interpenetrate). Every
    column here starts inside the endplate wall (RIB_LZ), and keyhead_endplate asserts the
    finished part is ONE solid.
    """
    from cadkit.fasteners import M4 as _M4, M4_BUTTON_HEAD_D, cut_anchor as _cut_anchor
    from cadkit.pcb import pcb_hold_xy
    from .helpers import box_at
    zb = RIB_LZ - TRAY_Z1          # cradle frame: the endplate's wall, -26.5 below the mount face
    # ⚠ RETENTION IS 3 BEADS, NOT 1.5 (user, 2026-09-29: "the retention pieces you have
    # designed are under the 1.6mm quality bar... ideally we can work even larger"). Both
    # of these were 1.2 -- under D.MIN_WALL_2P and not even on the bead grid, so Arachne
    # had to thin or pad them and neither would print at its drawn size. 3 * BEAD = 2.4
    # clears the two-bead quality bar with a whole bead of margin for the inaccuracy the
    # user is describing. They are written as BEAD COUNTS so they stay on the grid if the
    # nozzle ever changes.
    CLR, WALL, LIP = CRADLE_CLR, D.MIN_WALL_2P, 3 * D.BEAD
    RETAIN = 3 * D.BEAD   # how far the 45 deg lean reaches over the board (= its rise)
    HARNESS_W = 24.0      # the -Y notch the cable leaves through

    def _cyl_col(x, y, d, z0, z1):
        return cq.Workplane("XY").add(cq.Solid.makeCylinder(d / 2.0, z1 - z0, cq.Vector(x, y, z0)))

    def _frame(bw, bl, boss_xy, slide_in_x=False, harness_w=0.0, post_h=POST_H,
               open_down=False, root_d=None, boss_d=None, foot=0.0):
        """A board cradle made ONLY of columns rising from the endplate wall (local z `zb`)
        to the board: a ring round the board -- a LIP under its edge to carry it, then on up
        past its top as the locating wall -- and an M4 boss column at `boss_xy`, the insert
        in its top. Centred on the board.

        ⚠ ONE INSTALL DIRECTION, +Z -> -Z (user, 2026-09-24). Both boards used to have
        more than one way in, which is a way OUT for anything the single M4 does not hold:
        the motor controller had two (world -Y and world +X) and the Pi three. The axes are
        worth writing down because stand() inverts one and this file has already shipped a
        bug from getting it backwards:
            local +X -> world -Z      local +Y -> world +Y      local +Z -> world +X
        so world +Z, the drop-in, is local -X -- that is the mouth, and the only opening.
        Closing the other two means:
          * the local -Y wall comes BACK. It was cut full width for the harness; it is a
            `harness_w` notch now, so the cable still leaves and the board no longer does.
          * a RETAINER over the board, which is what stopped it lifting straight out --
            the locating wall ends beside the board with nothing above it.
        ⚠ AND THE RETAINER CANNOT BE A PLAIN LIP, because of the print direction. This
        endplate builds along world +X = local +z, so anything reaching over the board has
        its underside pointing DOWN the build axis: a ceiling. The wall therefore leans IN
        at 45 above the board's top face -- self-supporting, same trick as the LED roof --
        and the board is captured with about `RETAIN` of lift before it meets the lean.
        The board still slides in under it along the mouth direction, so the one install
        direction is unaffected.
        """
        ox, oy = bw / 2 + CLR + WALL, bl / 2 + CLR + WALL
        # ⚠ THE ROOT IS THE CHASSIS FLOOR NOW, NOT THE ENDPLATE WALL, and that is why these
        # frames stop being 26.5 mm deep. `zb` reached inside the endplate (RIB_LZ) because
        # the endplate was what carried them; carried from BELOW they only need enough depth
        # to be stiff and to bury the M4's insert, and depth is now a COST rather than free:
        #   * the Pi's band is filled behind it by the height-adjust block, whose inboard
        #     face is x -607.8 -- so its frame may reach 6.2 mm back and no further. Its
        #     BOSS may be deeper, because the hold point sits at y +36.9, outside that
        #     block's y -38.91..+33.2.
        #   * the motor band has no block in it at all (y -113..-51), so 10.4 is free there.
        # THIS IS ALSO WHAT RETIRES pi_cut. The insert-slot shadow existed only to carve the
        # old columns around the slots they landed on; a frame that stops at -607.2 never
        # reaches them.
        zr = zb if root_d is None else -root_d
        zbo = zb if boss_d is None else -boss_d
        btop = post_h + BD_T                       # the board's top face
        top = btop + RETAIN + 0.8                  # wall now clears the retainer too
        ring = (box_at(2 * ox, 2 * oy, post_h - zr, x=0.0, y=0.0, z=(zr + post_h) / 2)
                .cut(box_at(bw - 2 * LIP, bl - 2 * LIP, 80.0, x=0.0, y=0.0, z=0.0)))
        wall = (box_at(2 * ox, 2 * oy, top - post_h, x=0.0, y=0.0, z=(post_h + top) / 2)
                .cut(box_at(bw + 2 * CLR, bl + 2 * CLR, btop - post_h + 0.02,
                            x=0.0, y=0.0, z=(post_h + btop) / 2)))
        # the 45 deg lean: a void that opens OUT as it rises, cut from the wall above the
        # board. At the board's top face it is the board's own clearance box; RETAIN higher
        # it has grown by RETAIN on every side, so the material between leans inward at 45.
        # ⚠ THE VOID SHRINKS AS IT RISES, and getting that backwards is the whole trick.
        # Material must move INWARD going up, so each layer is carried by the one beneath
        # it -- at RETAIN over RETAIN that is exactly 45 deg and prints unsupported. The
        # first version lofted the void the other way: the wall receded outward as it rose
        # and nothing ever reached over the board, which measured as 0% retainer on every
        # edge while looking perfectly reasonable in the source.
        lean = (cq.Workplane("XY").workplane(offset=btop)
                .rect(bw + 2 * CLR, bl + 2 * CLR)
                .workplane(offset=RETAIN)
                .rect(bw + 2 * CLR - 2 * RETAIN, bl + 2 * CLR - 2 * RETAIN)
                .loft())
        wall = wall.cut(lean).cut(box_at(bw + 2 * CLR - 2 * RETAIN, bl + 2 * CLR - 2 * RETAIN,
                                         80.0, x=0.0, y=0.0, z=btop + RETAIN + 40.0))
        # THE HARNESS NOTCH, not an open side: the cable leaves, the board does not.
        if harness_w > 0.0:
            wall = wall.cut(box_at(harness_w, 2 * WALL + 2 * CLR + 2, 80.0,
                                   x=0.0, y=-bl / 2, z=0.0))
        if slide_in_x:
            # ⚠ THE MOUTH IS LOCAL -X, WHICH IS WORLD +Z. stand() inverts this axis, and
            # cutting +x instead left all 252 mm3 exactly where it was -- the swept volume,
            # not the picture, is what said which side had opened.
            mouth = box_at(2 * WALL + 2 * CLR + 2, 2 * oy + 2, 80.0,
                           x=-bw / 2, y=0.0, z=0.0)
            wall = wall.cut(mouth)
            # ⚠ AND IT CUTS THE RING TOO NOW, WHICH IS A PRINTABILITY FIX WITH A DESIGN
            # ARGUMENT BEHIND IT. These frames were shaped for the endplate, which builds
            # along world +X; the chassis builds along world +Z, and in that direction the
            # ring's upper member is a horizontal bar 1.2 mm wide spanning the board's whole
            # width between the two side members -- 85.6 mm of unsupported bridge on the Pi,
            # ~66 on the motor controller. Neither prints.
            # It is not needed either: that member is a LIP under the board's TOP edge, and a
            # board standing vertically is carried by the lip under its BOTTOM edge. What the
            # top edge needs is retention against lifting, and that is the M4 -- which is the
            # whole reason the mouth is up there. So the frame is a U, not a rectangle.
            ring = ring.cut(mouth)
        cr = ring.union(wall).union(_cyl_col(boss_xy[0], boss_xy[1], _M4.boss_od, zbo, post_h))
        # ⚠ AND THE FOOT, which is the whole point of rooting in the chassis: two legs off
        # the ring's own side walls, down past the board's bottom edge to the floor. Only
        # the SIDES, because the span between them is the harness lane and the motor board's
        # floor port. A board whose ring already reaches into the floor (the motor
        # controller, whose laminate ends 1.00 mm inside the underside) needs none: its side
        # walls ARE the legs, which is why 2711 mm3 of interference becomes a root.
        # ⚠ ONE CONTINUOUS RIB, NOT TWO LEGS, and again the build direction decides it. Two
        # legs at the ends leave the bottom lip bridging 85.6 mm between them; a rib the full
        # width of the frame carries that lip along its whole length, so there is no bridge at
        # all, and standing on the floor it is a vertical wall in the chassis's own build
        # direction -- the easiest thing a printer does. It costs 5.6 mm of the bay's depth in
        # X under the board, not a partition across the bay.
        if foot > 0.0:
            cr = cr.union(box_at(foot, 2 * oy, post_h - zr,
                                 x=bw / 2 + foot / 2, y=0.0, z=(zr + post_h) / 2))
        # ⚠ THE -Z EDGE CARRIES CONNECTORS, NOT RETENTION (user, 2026-09-25: "we likely
        # don't need -z retention at all since the chassis serves as -z retention and the
        # endplate -z retention will just clip into the chassis"). local +X is world -Z,
        # and on the motor controller that edge is the sterilised one -- the two bus-B
        # JSTs and nothing else. The ring's lip, the locating wall and the 45 deg retainer
        # all ran along it, so the frame closed over the very connectors a hand has to
        # reach. Nothing is lost by opening it: the board's bottom edge sits 0.35 mm above
        # the chassis floor, so the CHASSIS is what stops it moving -Z, and the endplate's
        # own -Z retention clips into that chassis rather than into this frame.
        # Everything beyond the board's +X edge goes -- lip, wall and lean together, since
        # cutting only the wall would leave the retainer leaning over the connectors.
        if open_down:
            cr = cr.cut(box_at(20.0, 2 * oy + 2, 80.0,
                               x=bw / 2 + 10.0, y=0.0, z=0.0))
        return cr

    # ── BOTH BOARDS: HOLLOW FRAMES OF COLUMNS, NO PLATE (user, 2026-09-21) ────────────────
    # They used to be pcb_cradle plates standing on ribs 27 mm off the endplate wall, and the
    # user read it right: the ribs cut the plates' bridges to 10 mm, but a bridge is still an
    # overhang, and each plate was 5.3 mm thick everywhere only because the M4 insert needed
    # 8.5 mm of depth in ONE spot. This endplate prints standing on its -X face, so anything
    # lying across the build axis is a ceiling -- the fix is to have nothing lying across it.
    # Every piece of these cradles is a COLUMN rising from the endplate wall straight to the
    # board. The boards need no floor: the motor controller is single-sided, and the Pi's
    # underside has only the GPIO header's tails, 1 mm inboard of the lip.

    # THE MOTOR CONTROLLER: the M4 goes THROUGH its mounting ear (elec/motor_ctrl.py EAR_*).
    x0, x1, y0, y1 = MCTRL_FP
    bw, bl = x1 - x0, y1 - y0
    # ⚠ THE HOLD MOVED OFF THE EAR, TO BESIDE THE BOARD'S -Y EDGE (2026-09-29). The M4 used to
    # go THROUGH the mounting ear at the board's +Y end, and the boss under it has to be deep
    # enough to bury an M4 insert (~8.5 mm). After the Y swap that boss lands at world y ~+15,
    # inside the nut height-adjust block (y -38.91..+33.2) -- 625.45 mm3 into
    # nut_slide_insert_2, a HEAT-SET INSERT for the string-nut slide. It cannot be shallowed
    # (no insert), the insert cannot move (it is string-nut hardware), and the board cannot
    # move: clearing the block needs ymax < -38.91 - EAR_H/2 while the adapter needs
    # ymin > -97.15, i.e. ymax >= -35.15 for a 62 mm board. Infeasible by 3.76 + EAR_H/2.
    # ⚠ AND THE DIP IS THE WHOLE BOARD, WHICH IS WHAT CLOSED THAT DOOR. It stands vertically,
    # so its bottom edge runs at z -83.85 along all 62 mm -- measured, not assumed; there is no
    # short plug region to slide past the adapter.
    # Beside the -Y edge the boss sits at y ~-44, outside the block, and the board stays where
    # it is. Same pattern and same helper as the Pi, same single 2.5 mm hex key.
    # ⚠ THE EAR IS NOW VESTIGIAL: elec/motor_ctrl.py still carries EAR_* and its 4.5 mm hole,
    # unused. Left alone deliberately -- removing it re-opens a board that is 0 unconnected /
    # 0 violations, and a spare hole costs nothing. Drop it at the next motor_ctrl revision.
    hx, hy = pcb_hold_xy(bw, bl, MCTRL_HOLD[0], hold_at=MCTRL_HOLD[1],
                         clr=CLR, spec=_M4)
    # ⚠ ROOTED IN THE CHASSIS FLOOR, 13 beads deep. Nothing of the endplate lies in this
    # board's y band (-113..-51 against the height-adjust block's -38.91..+33.2), so the
    # depth here is free. NO FOOT: this board passes THROUGH the floor -- its laminate ends
    # 1.00 mm inside the underside -- so the frame's two side walls already run down inside
    # the slab, either side of the board's own floor port (y -113..-51 against walls at
    # -114.9 and -49.1). Fused to the chassis those walls ARE the root, which is what turns
    # the 2711 mm3 the two parts used to share into structure.
    cr = _frame(bw, bl, (hx, hy), slide_in_x=True, harness_w=HARNESS_W,
                post_h=MCTRL_POST_H, open_down=True, root_d=4 * D.BEAD)
    cr = _cut_anchor(_M4, cr, (hx, hy, MCTRL_POST_H), (0, 0, -1), _M4.anchor_min_wall)
    # ⚠ AND THE HEAD NEEDS ITS OWN HOLE, exactly as the Pi's does 50 lines below. The boss
    # stands BESIDE the board, and the locating wall rises past the board's top face at
    # that same y -- so the button head, which seats on the board top and laps its edge,
    # lands INSIDE the wall. Measured before this cut: 83.7 mm3 of screw and 30.4 of insert
    # buried in the cradle, which the gate reports as chassis_2 because the cradle is fused
    # into the segment. The anchor bore does not help: it runs DOWN from the board, and the
    # head is above it.
    # (An earlier attempt at this cut "left the number exactly unchanged" and was reverted --
    # true, but that was at the old hold, where the head sat over the frame's mouth and
    # there was nothing to cut. The cut was right and the position was wrong.)
    cr = cr.cut(_cyl_col(hx, hy, M4_BUTTON_HEAD_D + 2 * CLR, MCTRL_POST_H,
                         MCTRL_POST_H + 20.0))
    # ⚠ THE HEAD GRAZES SOMETHING BY 0.72 mm3 AND IT IS NOT THIS FRAME. A head-clearance
    # cut at (hx, hy) -- the Pi's remedy, one-sided and then symmetric about the board
    # plane -- left the number EXACTLY unchanged both times, so the material the screw
    # touches is chassis structure, not the cradle. y -48.30..-48.10 is a 0.2 mm sliver on
    # one side of the screw's circle, i.e. a flat face it just crosses. Not chased further
    # for 0.72 mm3; see docs/bronner-work-items.md. Cutting this frame cannot fix it.
    mc = cr.translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, TRAY_Z1))

    # ⚠⚠ THE PI'S CRADLE IS GONE, AND IT IS NOT A REGRESSION -- THE PI LEFT THE TRAY
    # (2026-09-29). What stood here was a tray `_frame` with a root into the 3 mm plate,
    # columns, and a FOOT computed to reach the chassis floor. Every one of those exists to
    # hold a board STANDING off a plate. The Pi now lies ON the floor, so there is nothing
    # for a foot to reach and nothing for a root to root into; the assert that caught this
    # said so exactly -- "the legs would drive into the floor", foot -25.85.
    # ⚠ THE FLAT PI'S RETENTION IS A NEW DESIGN AND IT IS NOT BUILT YET. It wants a low
    # collar standing UP from the floor around the 85 x 56 footprint plus one M4 boss -- not
    # this frame with its z flipped, which is exactly the "bolt a mapping on the end" that
    # the orientation rule forbids. Until it exists the Pi is UNRETAINED in the model, and
    # that is stated here rather than faked with a shape that would render convincingly.
    # ⚠ AND ONE LONG-RUNNING BUG DIES WITH IT. The motor's M4 used to bury itself in the
    # PI's cradle wall at y -44.28 -- the defect that survived five attempted fixes, because
    # the two fasteners were never in the same solid. With no Pi cradle in the bay there is
    # nothing for it to bury itself in, so the `_mtx`/`_mty` clearance cut that compensated
    # for it is gone too.
    if not standing:
        return mc
    out = stand(mc)
    # ⚠ NOTHING MAY LEAN INTO A BOARD'S COMPONENTS (user, 2026-09-29: "on the +y side of
    # the pi the retention is clipping into the pi's components"). They were right, and
    # NOTHING IN THE PROJECT COULD SEE IT: cradle-to-board contact is a designed contact,
    # so check_overlaps does not report it, and the render is the only place it shows.
    # Measured before this cut: 56.3 mm3 into pi5 along the board's WHOLE length, 1.7 mm
    # ABOVE the laminate's top face -- that is component space, not board edge. Raising
    # RETAIN to 3 beads tripled it to 194.3, which is the honest cost of a deeper lean and
    # exactly why the two changes have to land together.
    # The boards' own solids are the authority on where their components are, so subtract
    # them: the lip below and the locating wall beside both survive (they are outside the
    # footprint), and only the part that reaches OVER a board is trimmed. Retention is
    # whatever the board's own envelope leaves room for, which is the most any cradle can
    # honestly claim.
    # ⚠ The cut is EXACT, so the cradle and the board now TOUCH rather than interfere. The
    # boards are held by their M4 -- head lapping the edge, clamping to the boss -- plus
    # the single install direction; the lean adds what it can where the envelope allows.
    # (pi5 is no longer in this solid's way -- it is on the floor, not in the bay.)
    out = out.cut(motor_ctrl())
    return out


def board_screws():
    """The M4 through each of OUR boards' mounting ears: [(name, solid)] -- an M4x10 button
    head seated on the board's top face and its heat-set insert in the boss below, placed
    from the same hole the cradles are bored from. The motor controller's is authored in
    the flat tray frame and stood up with the board; the output board's is world-vertical."""
    from cadkit.fasteners import M4 as _M4, M4_BUTTON_HEAD_H, m4_button_screw, seated_insert
    L = 10.0                                   # M4x10: 1.6 of board, 8.4 into the 8.5 anchor
    assert L - _PCB_T <= _M4.anchor_min_wall + 1e-9
    # ⚠ THE MOTOR BOARD'S IS AN M4x6, NOT AN M4x10, AND THE REASON IS THE HEIGHT-ADJUST
    # BLOCK (2026-09-29). Its inboard face is world x -607.80 and this screw is driven along
    # world -X, so an M4x10 reaches -611.50 and buries 46.2 mm3 of itself in the block. That
    # was FREE until the board shrank: at the old -Y edge the screw sat at y ~-44, clear of the
    # block's -38.91, and BOARD_L 62.0 -> 55.0 moved that edge +7.00 to the far side of it.
    # ⚠ REPOSITIONING WAS TRIED AND IS DEAD. Swept 4 edges x 9 holds against 56 obstacles:
    # the only 0.00 was "+x" at -24, and it is a FALSE clean -- that screw sits at world z
    # -87.15 against a FLOOR_TOP of -71.35, i.e. UNDER THE FLOOR, 22.98 mm3 into chassis_2,
    # which is the recorded "+x inside the floor slab" failure. The current hold is the only
    # one clean against chassis_2, circularly, because the anchor bore is cut there.
    # So the fastener gets shorter instead of moving. Measured, not chosen:
    #     head height 2.20, so tip_x = -599.30 - (L + 2.20)
    #     L 10.0 -> tip -611.50   3.70 INSIDE the block
    #     L  6.0 -> tip -607.50   clear by 0.30, engagement 4.40 mm = 1.10 x D
    #     L  5.0 -> tip -606.50   clear by 1.30 but engagement 3.40 = 0.85 x D, under 1xD
    # 6.0 is the stock size that clears with thread engagement still over one diameter.
    # ⚠ 0.30 IS THINNER THAN A BEAD, and it is air between a PURCHASED screw and a PRINTED
    # face -- a tolerance to watch, not a wall. If it proves tight the block wants a 0.5
    # relief, but that is keyhead_endplate and not this scope.
    # ⚠ A SECOND LENGTH, NOT A SECOND SKU FAMILY: still M4, still a 2.5 mm hex button, so the
    # one-tool and one-diameter rules both hold. The BOM gains a length, not a driver.
    L_MCTRL = 6.0
    assert L_MCTRL - _PCB_T <= _M4.anchor_min_wall + 1e-9
    out = []
    # ⚠ BESIDE THE -Y EDGE, NOT THROUGH THE EAR (2026-09-29) -- and this has to track
    # keyhead_cradles, which bores the anchor. The ear's boss landed inside the nut
    # height-adjust block after the Y swap (625 mm3 into nut_slide_insert_2, a heat-set
    # insert), and an M4 boss cannot be shallowed below its insert. Same helper, same
    # arrangement and same SKU as the Pi's a few lines below. The ear on elec/motor_ctrl.py
    # is vestigial until that board is next revised; MCTRL_HOLE is no longer read here.
    from cadkit.pcb import pcb_hold_xy as _hold_xy
    cx, cy = _ctr(MCTRL_FP)
    _mx0, _mx1, _my0, _my1 = MCTRL_FP
    # ⚠ THE +X EDGE, WHICH STANDS AS THIS BOARD'S UNDERSIDE. It was "-y", beside the
    # edge that faces the Pi, and once the Pi went flush to the bay wall its boss spanned
    # y -47.8..-40.2 -- 1.6 mm PAST the Pi's new +Y edge at -46.18, straight into the
    # board. Both fasteners used to live in the gap between the two boards, which is why
    # the gap was 8.5 wide; with both off it the gap carries cable only.
    # ⚠ NOT the +Z face, which is where the user pointed and where I tried first: that is
    # the keyhead endplate's, 26..49 mm3 at EVERY position along the edge. Searched all
    # four edges x ten holds against the built assembly; "+x" at hold -18 is CLEAR, and
    # -18 also keeps it off the two floor-port slots, which are at the plugs' own y.
    # ⚠ NOT THROUGH THE EAR, and the ear is why the user asked. That M4 hole cannot be
    # used from here: its boss projects -X into the nut height-adjust block and put
    # 625 mm3 through nut_slide_insert_2 when it was tried. The hole is being removed
    # from the board rather than left as a fastening point that cannot be fastened.
    _mhx, _mhy = _hold_xy(_mx1 - _mx0, _my1 - _my0, MCTRL_HOLD[0],
                          hold_at=MCTRL_HOLD[1], clr=CRADLE_CLR, spec=_M4)
    tx, ty = cx + _mhx, cy + _mhy
    out.append(("board_insert_0", stand(seated_insert(_M4, (tx, ty, MCTRL_BOARD_Z), (0, 0, -1)))))
    out.append(("board_screw_0", stand(m4_button_screw(L_MCTRL).translate(
        (tx, ty, MCTRL_BOARD_Z + BD_T + M4_BUTTON_HEAD_H)))))
    ox, oy, oz = op_origin()
    (hx, hy, _hd), = BG.holes("output_panel")
    out.append(("board_insert_1", seated_insert(_M4, (ox + hx, oy + hy, oz), (0, 0, -1))))
    out.append(("board_screw_1", m4_button_screw(L).translate(
        (ox + hx, oy + hy, oz + _PCB_T + M4_BUTTON_HEAD_H))))

    # ⚠ THE PI'S M4 IS DRAWN NOW TOO (user: "the M4 isn't using the cadkit screw helper
    # which draws a fitted insert and screw"). electronics_bay() has always BORED its
    # anchor -- _cut_anchor at (phx, phy, POST_H) -- but nothing ever drew the fastener
    # that goes in it, so the render showed a bare boss and the overlap gate had no screw
    # to check against the plastic around it.
    #
    # BESIDE the board, not through it, because the Pi is a PURCHASED board and its own
    # holes are too small for M4 -- the same arrangement, and the same SKU, as the CAN tee
    # hold-downs: the head lands on the board's top face and laps its edge, clamping it to
    # the cradle boss. The seat plane is therefore the board top, exactly as it is for the
    # two boards above, and the assert at the top of this function covers it unchanged.
    from cadkit.pcb import pcb_hold_xy
    # ⚠⚠ THE PI'S M4 IS GONE WITH ITS CRADLE (2026-09-29). It threaded into a boss on the
    # tray frame that no longer exists -- the Pi lies on the chassis floor now, so there is
    # nothing at that hold point to thread into. Drawing the screw anyway would put a
    # fastener in the render with no boss behind it, which is the exact fault this project
    # already found once and named: "a hole designed for an M4 screw that isn't being used",
    # a fastening point that cannot be fastened.
    # ⚠ The flat Pi still needs ONE M4 -- it is a purchased board whose own holes are too
    # small, so the head has to lap an edge exactly as before -- but its position belongs to
    # the floor retention that has not been designed yet, and inventing one here would just
    # have to be re-searched against whatever collar that turns out to be.
    return out


def electronics_tray(standing: bool = True) -> cq.Workplane:
    """The printed tray: plate + board support posts. Prints flat (plate on the bed,
    posts up); stands against the keyhead endplate in the instrument (see STANDING TRAY).
    Pass standing=False for the print pose."""
    body = box_at(TRAY_X1 - TRAY_X0, TRAY_Y1 - TRAY_Y0, TRAY_Z1 - TRAY_Z0,
                  x=(TRAY_X0 + TRAY_X1) / 2, y=(TRAY_Y0 + TRAY_Y1) / 2,
                  z=(TRAY_Z0 + TRAY_Z1) / 2)
    # each board rests on four plain posts -- no retention yet (see _support_posts)
    for fp, bz in ((PI_FP, BOARD_Z), (MCTRL_FP, BOARD_Z)):
        body = body.union(_support_posts(fp, bz))
    # (the NORTH-SHELF lane channel for the TRRS pigtail is gone: standing, the tray's
    #  bottom edge rides above that pigtail instead of lying over it)
    return stand(body) if standing else body


def _board(fp, bz, t=BD_T):
    x0, x1, y0, y1 = fp
    return box_at(x1 - x0, y1 - y0, t, x=(x0 + x1) / 2, y=(y0 + y1) / 2,
                  z=bz + t / 2)


def _ctr(fp):
    return (fp[0] + fp[1]) / 2, (fp[2] + fp[3]) / 2


# ── THE PI'S PORTS, so a cable can be drawn to one instead of to an invented point ──
# ⚠ EVERY CABLE TO THE PI USED TO END AT A HAND-TYPED POINT, and the user saw it: "the USB
# for example enters the pi from +x which doesn't seem like how the USB would be oriented".
# wire_usb ended at stand_pt(-575.0, PI_FP[3] - 9.0, -44.0) = WORLD (-587.8, -55.18, -34.0),
# which is 1.8 mm inside the USB/ethernet block's outer face -- the cable ran in along world
# x at z -15 straight through the block's interior and stopped in the middle of it. It
# approached the COMPONENT face from +X, exactly as described.
# ⚠⚠ AND THE WORK-ITEMS NOTE THAT DIAGNOSED IT READ THE FRAME WRONG. It said the lead
# "lands at x -575.0, which is outboard of the whole Pi (xmax -586)". -575.0 is the TRAY x
# that stand_pt turns into world z -34.0; the world x is -587.8, which is INSIDE the block.
# The user's observation was right and the explanation under it was not. stand_pt's three
# arguments are tray (x, y, z) -> world (z-543.8, y, -609-x); never read one as a world x.
# The ports are on the +Y END, which is where a Pi 5's are, and pi5() already builds that
# block. These are its three connector groups along the 50 mm the block spans in tray x,
# taken mid-height so the plug shell sits inside the block's 14 mm rather than proud of it.
PI_PORT_Z  = BOARD_Z + BD_T + 7.0      # mid-block: world x -593.0, shell -596.4..-589.6
PI_PORT_IN = 1.0                       # end the lead 1 mm inside the face so it CONTACTS
PI_PORTS   = {"eth": -594.0, "usb3": -576.0, "usb2": -560.0}   # tray x (world z -15/-33/-49)


def pi_port_pt(which: str):
    """TRAY (x, y, z) of a port mouth on the Pi's +Y end -- feed it through stand_pt."""
    return (PI_PORTS[which], PI_FP[3] - PI_PORT_IN, PI_PORT_Z)


def pi5() -> cq.Workplane:
    """Raspberry Pi 5 dummy: board + USB/eth block + SoC. WORLD frame, lying FLAT.

    ⚠ NO stand(). This board is not in the tray any more -- it lies on the chassis floor,
    so it is authored where it sits, the way the output board already is. `_board` and
    `box_at` were always frame-agnostic; the stand() on this function's last line was the
    only thing that made the Pi a tray part.
    ⚠ THE SOLID IS UNCHANGED -- same 85 x 56 laminate, same 50 x 18 x 14 I/O block, same
    15 x 15 SoC. Only the frame and the block's END moved: the block is on the +X end now
    (user: "with the I/O facing +x"), looking down the instrument into open floor instead
    of into the keyhead endplate."""
    cx, cy = _ctr(PI_FP)
    b = _board(PI_FP, PI_Z)
    b = b.union(box_at(18.0, 50.0, 14.0, x=PI_FP[1] - 9.0, y=cy,
                       z=PI_Z + BD_T + 7.0))
    b = b.union(box_at(15.0, 15.0, 2.5, x=cx, y=cy, z=PI_Z + BD_T + 1.25))
    return b


# (adc_stack is DELETED, 2026-09-14. It modelled a three-PCM1864 carrier that
# digitised ten string signals for the Pi -- a path BOM.md struck out when the
# optical pickup board took on its own 20-channel conversion and sent audio over
# USB. The board had been struck in the BOM and left standing in the CAD, which
# is the wrong way round: the model is what other agents measure against.)


# (THE POWER BOARD IS DELETED, 2026-09-15, merged into the motor controller. It was
#  its own PCB here; folding it in removed a board, a connector and a cable -- and,
#  more usefully, a JUNCTION. The 24 V trunk had to feed both boards at the keyhead
#  and the power board had only a 4-way INLET, so that branch was the one splice in
#  an instrument where every other branch is a board. See elec/motor_ctrl.py U5/F1/F2.)


# ── OUTPUT + PANEL BOARD ─────────────────────────────────────────────────────
# EVERY FRONT-PANEL CONNECTION ON ONE PCB (user, 2026-09-15). It merges the USB
# break-out that stops a laptop back-feeding the Pi with the analog OUTPUT STAGE
# that would not fit on the optical pickup board -- and the merge pays for itself
# twice, because putting the output stage at the panel is what lets the TS JACK
# BE A BOARD PART.
#
# ⚠ THE TS JACK ON THE BOARD FIXES A RULE VIOLATION rather than adding a part.
# BOM.md already specifies a Neutrik NMJ4HCD2 and that jack is PCB-MOUNT with a
# panel bushing -- KiCad ships its footprint. Panel-mounted as this file had it,
# its lugs would have been HAND-SOLDERED, which the project forbids outside a
# factory-assembled board. Same part, same price, and the last hand-soldered
# joint in the instrument goes away. Its nut clamps the endplate, so the PANEL
# takes the cable-yank load and the PCB does not.
#
# ⚠ TWO THINGS THE ENDPLATE HAS TO ABSORB (branner):
#   1. THE PANEL HOLES ARE NO LONGER ONE ROW AT ONE HEIGHT. A 1/4 in jack's axis
#      and a USB-C's axis sit at different heights above the board they share, so
#      the two holes differ in Z by that much (see OP_TS_AXIS_H). Their Y spacing
#      is now 31.27, set by this board rather than by the old 18 mm pitch.
#   2. THERE ARE NOW THREE CONNECTORS ON THE -X EDGE, facing INTO the instrument
#      rather than out the panel: two USB-A shells (J2 to the Pi's gadget port, J4
#      to the optical board) and a USB-C (J3, the hub's upstream to a Pi host port).
#      They want cable room behind them, and a right-angle A shell stands 6.6 off
#      the board.
#   3. THE DC BARREL JACK IS ON THIS BOARD TOO (user, 2026-09-15), and my earlier
#      objection to it was weaker than I made it sound. Two facts settled it: the
#      PJ-005A it replaces is a SOLDER-LUG jack, so it carried the same hand-soldering
#      violation the TS jack did, and BOM.md sizes the 24 V bus UNDER 5 A because the
#      fleet slew is staggered -- which is routine to carry across a board corner. The
#      noise argument survives only as a LAYOUT OBLIGATION, and it is met by keeping
#      PWR_GND a separate net that never joins AGND on this board (see J5/J6).
# ── THE BOARD ITSELF COMES FROM THE ROUTED BOARD ─────────────────────────────────────
# Everything below used to be hand tables -- OP_J anchors, OP_BOX courtyard boxes, OP_BOM,
# OP_TS_* -- copied "straight out of" elec/output_panel.py and checked against that same
# file's placements, i.e. against the numbers layout was GIVEN. It agreed with itself while
# the panel connectors' bodies sat 0.54 short of the board edge, the barrel inlet faced the
# chassis rail, and the USB-C hole was cut 7.85 mm above the receptacle. src/board_geom.py
# builds it from elec/geom/output_panel.geom.json instead: the finished board, read back.
from . import board_geom as BG


# ── THE Pi CAP (elec/pi_cap.py) ──────────────────────────────────────────────
# Where the Pi's 40-way header is, in the tray frame. ⚠ ASSUMED FROM THE STANDARD Pi
# LAYOUT, NOT MEASURED: the header runs parallel to the 85 mm edge, its rows 3.5 and 6.04
# in from one long edge, pin 1 3.5 in from the short edge AWAY from the USB/ethernet block
# (which pi5() puts at +Y). If a real Pi says otherwise, these two numbers are the fix and
# nothing else moves. The cap is 56 x 26 against the Pi's 85 x 56, so it lands inside the
# Pi's outline apart from 0.37 mm at the -Y end -- real HATs sit flush, and 0.37 is the
# difference between the cap's half-length and the header's margin, not a placement error.
# ⚠ READ IT, DO NOT RESTATE IT. This was a hand-typed 139.0 beside a comment saying it was
# elec/led_strip.BOARD_W, and the moment the joint set the section width (140.5) the two
# would have disagreed silently -- the boards drawn 1.5 mm short each, the gap 1.5 too wide,
# and nothing comparing them. The same defect MCTRL_BOARD_X had against its routed outline.
LED_SECTION_W = BG.load("led_strip")["outline_mm"][0]
LED_SECTIONS = 4

# ⚠ THE 40-PIN HEADER RUNS ALONG X NOW, off the +Y long edge. Flat, the 2x20 runs down the
# board's 85 mm side; 3.5 mm in from the corner is the Pi's own pin-1 inset, and 1.27 is half
# the 2.54 row spacing so the datum sits BETWEEN the two rows, exactly as before.
# +Y edge chosen deliberately: the cap's two cable runs (the UI ribbon to the deck, and the
# LED strip) both go +Y, so the header faces the things it feeds.
PI_HDR_X = PI_FP[0] + 3.5 + (20 - 1) * 2.54 / 2.0   # the pad centroid along the row
PI_HDR_Y = PI_FP[3] - 3.5 - 1.27                    # between the two pin rows
PI_CAP_STANDOFF = BG.HEIGHT["PinSocket_2x20_P2.54mm_Vertical"]   # 8.5, the socket's body


# ── THE LED STRIP SECTIONS (elec/led_strip.py) in the chassis seat ───────────
# ⚠ WORLD FRAME, NOT THE TRAY FRAME. Everything else in this file is authored flat and
# `stand`s into place; these are not, because the seat they sit in is a CHASSIS feature
# (chassis.LED_*) already written in world coordinates. Anything here that reads a chassis
# datum has to stay in that frame or the two will drift apart silently.
def _led_place(shape, i):
    """Put anything authored in the LED SECTION'S BOARD FRAME where section `i` sits.
    Same one-transform rule as _cap_place: led_sections() and led_pin() both go through it,
    so a wire cannot be drawn to somewhere the board is not."""
    from . import chassis as CH
    w = LED_SECTION_W
    # ⚠ THE GAP IS THE BOARD'S NUMBER, NOT A DIVISION OF THE CHANNEL. This used to be
    # (channel - n*w) / (n-1), which spreads the sections evenly and silently absorbs any
    # disagreement between the rail the board was designed for and the channel the chassis
    # actually offers. It produced 4.00 mm junctions against the 8.0 led_strip.py requires
    # -- two facing PH plugs project 3.6 past their mouths and the mouths sit 1.0 inside
    # the board ends, so 5.2 is gone before the jumper's U has anywhere to turn. The strip
    # could not have been assembled, and nothing caught it because the boards never overlap
    # each other: there is only air where the plugs go.
    # Reading it from the board file makes the two numbers meet, and the assert below makes
    # them meet LOUDLY.
    gap = _led_junction_gap()
    zc = (CH.LED_BOARD_BOT + CH.LED_BOARD_TOP) / 2.0
    cx = CH.LED_X0 + w / 2.0 + i * (w + gap)
    return shape.rotate((0, 0, 0), (1, 0, 0), 90.0).translate((cx, CH.LED_Y0, zc))


def led_pin(i, ref, n, count=6, pitch=None, at="pad"):
    """World point of pin `n` on section `i`'s connector `ref`, off the ROUTED footprint."""
    f = BG.footprint("led_strip", ref)
    # ⚠ READ THE PITCH OUT OF THE FOOTPRINT, DO NOT DEFAULT IT. This was a literal 2.0,
    # and the joint moved to 2.54 the moment sourcing said a 2.00 mm right-angle MALE is
    # not stocked -- at which point every conductor in the Pi lead would have been computed
    # on the wrong spacing while still landing close enough to look right. KiCad puts the
    # pitch in the footprint name ("..._P2.54mm_Horizontal"), which is the one place it
    # cannot disagree with the pads.
    if pitch is None:
        _m = re.search(r"_P(\d+(?:\.\d+)?)mm", f["fpid"])
        if not _m:
            raise ValueError("led_pin: no pitch in %s -- pass one" % f["fpid"])
        pitch = float(_m.group(1))
    x0, x1, y0, y1 = f["fab"]
    if (x1 - x0) >= (y1 - y0):                  # the row runs along whichever axis is longer
        px = (x0 + x1) / 2.0 + (n - (count + 1) / 2.0) * pitch
        py = (y0 + y1) / 2.0
    else:
        px = (x0 + x1) / 2.0
        py = (y0 + y1) / 2.0 + (n - (count + 1) / 2.0) * pitch
    # ⚠ THE CONTACT, NOT THE UNDERSIDE. z=0 in the board frame is the face that ends up
    # AGAINST THE RAIL once _led_place stands the section up, so every lead drawn to this
    # point terminated inside the laminate -- 7.44 mm3 each, six of them, and it read as
    # the cable being mis-routed rather than as the target being on the wrong face.
    # Land on the connector's contact axis instead: the board's top face plus half the
    # part's height, both read from board_geom so neither can drift from the footprint.
    # ⚠ at="mouth" STOPS AT THE CONNECTOR'S FACE, and a lead wants that rather than the
    # pad. Drawn to the PAD, a cable runs the whole length of the connector's body to get
    # there, so it overlaps the very part it plugs into -- 7.26 mm3 per conductor, six of
    # them. That is real geometry, not an artefact to declare away. The mouth is the end of
    # the fab body furthest from the pads, which is where a plug actually stops.
    _g = BG.load("led_strip")
    _h = BG.HEIGHT.get(BG.fp_name(f["fpid"]), 0.0)
    if at == "mouth":
        # ⚠ MEASURE FROM THE PADS, NOT THE BODY'S CENTRE. px is the fab centre here, which
        # is equidistant from both ends, so "the end furthest from px" is a coin toss and
        # it landed on the wrong one -- the mouth came out 3.9 mm INSIDE the board. The
        # pads are at the footprint's own origin, and the mouth is the end away from them.
        px = x0 if abs(x0 - f["x"]) > abs(x1 - f["x"]) else x1
    bb = _led_place(box_at(0.01, 0.01, 0.01, x=px, y=py,
                           z=_g["thickness_mm"] + _h / 2.0), i).val().BoundingBox()
    return ((bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0, (bb.zmin + bb.zmax) / 2.0)


LED_RELIEF_CLR = 0.5


def led_wall_reliefs():
    """Pockets in the +Y rail for the LED connectors' through-hole tails.

    ⚠ THE TAILS WERE NEVER MODELLED, so nothing ever saw this. board_geom extruded every
    part UPWARD from the board's top face and stopped, and these boards sit with their BACK
    ON the wall (LED_Y0), so 3.4 mm of post per connector ran straight into it -- 364 mm3
    across the strip, and every overlap check passed. The project had already recorded the
    shape of this once ("post tails collide along the INSTALL STROKE, not at rest"); what
    was missing was the geometry to collide WITH.
    The wall is 10.40 thick and the tails need 3.40, so a relief leaves about 6.5 mm of it.
    ⚠ DERIVED FROM WHAT ACTUALLY PENETRATES, like the motor controller's floor ports: ask
    the posed sections which of them is inside the wall band and pocket that, rather than
    restating connector coordinates that would go stale the next time the joint moves.
    ⚠⚠ AND IT CUT 173,600 mm3 OF THE RAIL AWAY -- four 140 x 25 mm holes, 12.4 mm deep
    through a 10.40 mm wall, which is a window per LED board and not a relief at all (user,
    2026-09-28: "big holes in the front of the chassis behind the LEDs"). Two mistakes, and
    each one alone would have been visible:

      1. THE BAND REACHED 1.0 mm OUTSIDE THE WALL FACE, so it caught each board's own
         LAMINATE as well as its tails. Laminate plus tails intersect as ONE solid, and the
         bounding box of that solid is THE WHOLE BOARD -- 139 x 24. This file already
         records the lesson one function up, in mctrl_floor_ports: "THE FOOTPRINT, NOT ITS
         BOUNDING BOX ... the plate and the two plugs TOUCH, so they come back as ONE solid
         whose bbox is five times the opening needed". Same trap, same week.
      2. THE DEPTH WAS CH.T + 2.0, straight through a wall of CH.T. The docstring above
         says what was meant -- "the tails need 3.40, so a relief leaves about 6.5 mm of
         it" -- so the number contradicted the prose and the prose was right.

    Now the band starts AT the wall face, so only what actually penetrates is caught, and
    each pocket is cut to that solid's own depth plus clearance instead of to infinity.

    ⚠ AND ON THIS BOARD THE ANSWER IS ZERO, WHICH IS THE REAL VERDICT ON THOSE WINDOWS.
    led_strip's only connector is `JST_PH_S6B-PH-SM4-TB ... _Horizontal` -- SM4 is SMD, side
    entry -- so the strip has no through-hole part on it and nothing to relieve. Measured:
    each section spans y 48.45..55.55 and the wall face is 55.55, so the laminate's back is
    FLUSH with it and not one cubic millimetre is inside the wall. The relief this function
    was written for is the XH's 3.4 mm posts on the OTHER boards; it stays because a THT part
    here would need it, and it now produces nothing until one appears.
    """
    from . import chassis as CH
    band = box_at(4000.0, CH.T, 200.0, x=0.0, y=CH.LED_Y0 + CH.T / 2.0, z=0.0)
    out = []
    for _n, sec in led_sections():
        inside = sec.intersect(band)
        try:
            solids = inside.val().Solids()
        except Exception:
            continue
        for sol in solids:
            bb = sol.BoundingBox()
            c = LED_RELIEF_CLR
            # depth: from the wall face to the deepest this solid reaches, plus clearance,
            # and never more than the wall has to give.
            d = min(bb.ymax - CH.LED_Y0 + c, CH.T - D.MIN_WALL_2P)
            assert d > 0.0, "an LED relief came out %.2f mm deep" % d
            out.append(box_at(bb.xlen + 2 * c, d, bb.zlen + 2 * c,
                              x=(bb.xmin + bb.xmax) / 2.0,
                              y=CH.LED_Y0 + d / 2.0,
                              z=(bb.zmin + bb.zmax) / 2.0))
    # ⚠ AND A CEILING ON THE WHOLE LOT, because the failure this replaces was not a wrong
    # number, it was a wrong SHAPE that no check had an opinion about. Relief for a handful
    # of 3.4 mm connector tails is tens of mm3; 173,600 is a window.
    _v = sum(c.val().Volume() for c in out)
    assert _v < 4000.0, (
        "the LED wall reliefs would remove %.0f mm3 from the +Y rail. These are pockets for "
        "connector TAILS -- if this is in the thousands, the intersection has caught the "
        "boards themselves again and every pocket is a board-sized window." % _v)
    return out


def _led_junction_gap() -> float:
    """The board-to-board gap led_strip.py requires, checked against the chassis channel.

    ⚠ THIS ASSERT IS THE POINT. The board and the chassis each hold a length for the same
    space and they did not agree: led_strip.py sizes its sections for a 585.34 mm rail
    (KH_RAIL_X..TP_EP_GX) while chassis.LED_X0/LED_X1 are hardcoded -600/-32 = 568.0, so
    four 139 mm sections at the required 8.0 need 580.0 and the channel is 12.0 short.
    Dividing the channel hid that for as long as nobody measured a junction.
    """
    from . import chassis as CH
    import json as _json, os as _os
    # ⚠ board.json, NOT geom.json. BG.load() returns the ROUTED board's measured geometry
    # -- its outline comes off Edge.Cuts -- and a junction gap is design INTENT, which is
    # never measurable from a board that does not contain the gap. The two files answer
    # different questions and this one belongs to the generator.
    _bj = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                        "elec", "out", "led_strip.board.json")
    with open(_bj, encoding="utf-8") as _fh:
        notes = _json.load(_fh)
    gap = notes["junction_gap_mm"]
    n = notes["sections"]
    w = notes["outline_mm"][0]
    need = n * w + (n - 1) * gap
    have = CH.LED_X1 - CH.LED_X0
    assert need <= have + 1e-9, (
        "the LED strip does not fit its channel: %d sections of %.1f at the %.1f mm "
        "junction led_strip.py requires need %.1f mm, and chassis.LED_X0..LED_X1 is "
        "%.1f. Either widen the channel (the rail's clear run is KH_RAIL_X..TP_EP_GX, "
        "which has the room) or shorten the section -- but shortening pulls the end "
        "connectors inward and LED_PITCH is already set by their courtyards, so it is "
        "not the cheap end to change." % (n, w, gap, need, have))
    return gap


def led_sections() -> list:
    """The four RGBW sections standing in the +Y rail's channel, facing -Y.

    board_geom hands the board flat -- centred in XY, underside at z = 0, parts rising +Z --
    so ONE rotation stands it up: +90 about X takes its own +Z (the component side) to world
    -Y and its +Y (the board's height) to world +Z. Then its BACK sits on the wall and its
    centre goes midway up the channel, both of which chassis already states."""
    from . import chassis as CH
    from . import board_geom as _BG
    w = LED_SECTION_W
    gap = (CH.LED_X1 - CH.LED_X0 - LED_SECTIONS * w) / (LED_SECTIONS - 1)
    zc = (CH.LED_BOARD_BOT + CH.LED_BOARD_TOP) / 2.0
    # ⚠ THE LAST SECTION'S OUTGOING HEADER IS NOT FITTED. The chain ends there, so J2 has
    # nothing to mate with -- and modelled it reaches 5.5 mm past chassis.LED_X1 and into
    # the chassis. DNP on that one board, which is how a chained strip is always built.
    return [("led_strip_%d" % i,
             _led_place(BG.solid("led_strip",
                                  omit=("J2",) if i == LED_SECTIONS - 1 else ()), i))
            for i in range(LED_SECTIONS)]


# ⚠ NO INSTALL RELIEF IS NEEDED IN THE ENDPLATE, and the near-miss is worth recording.
# With the cradle's mouth open (see _frame slide_in_x) the Pi and its cap sweep through
# 17 mm3 on the way down, in a band at z 14.26..16.07 -- which looked like the nut block's
# slot fins, and a cut was written to relieve them. Asked part by part, every one of those
# 17 mm3 is STRING: string_5 through string_9. The endplate is clear. So the install
# constraint is "fit the Pi before stringing", which is an assembly ORDER note, not a
# geometry change -- and cutting the nut block for it would have weakened a part that
# carries string load to make room for the strings themselves.


def pi_cap() -> cq.Workplane:
    """The Pi's connector board, plugged onto its GPIO header.

    The board is turned -90 so its socket (which runs along the board's X) lies along the
    header's axis, and lifted by the socket's own body height so the socket fills the
    standoff between the two boards -- which is why board_geom carries that 8.5 once and
    both this and the flipped footprint read it from there."""
    return _cap_place(BG.solid("pi_cap"))


def _cap_place(shape):
    """Put anything authored in the CAP'S BOARD FRAME where the cap is.

    ⚠ ONE TRANSFORM, USED BY EVERYTHING. The board, and every wire that has to land on one
    of its pins, go through this exact call -- because stand() inverts an axis and the last
    time that was reimplemented by hand it cut the wrong side of a part."""
    # ⚠ -4.5 SINCE THE CAP GREW TO 34 mm (elec/pi_cap.py). This is the number the whole
    # board is positioned BY -- the socket's y in the board's own frame -- so when the board
    # gained 8 mm on its -Y edge and every placement moved +4.00 with it, this moved too.
    # Leave it at -8.5 and the board lands 4 mm off the header it is supposed to plug into.
    j1_y = -4.5
    # ⚠ NO ROTATE AND NO stand() SINCE THE PI WENT FLAT. The -90 existed to swing the cap's
    # socket (which runs along the cap board's own X) onto the header's axis, which was the
    # TRAY's y. Flat, the header runs along WORLD X -- the cap's own axis already -- so the
    # rotation is not just unnecessary, it would put the cap across the header.
    # The j1_y offset moves to Y for the same reason: it positions the socket, and the socket
    # now varies in y rather than x.
    # ⚠ 180 ABOUT Z, AND IT IS NOT COSMETIC: the cap is 34 mm across a 56 mm board and the
    # header sits 4.77 in from the +Y edge, so the board it carries has to extend -Y OVER the
    # Pi. Placed unrotated it reached y -57.27 -- 16.7 mm off the Pi's +Y edge, a HAT hanging
    # in mid-air. The 180 turns its long axis around so it lies on the board it plugs into,
    # and j1_y therefore ADDS rather than subtracts.
    return (shape.rotate((0, 0, 0), (0, 0, 1), 180.0)
                 .translate((PI_HDR_X, PI_HDR_Y + j1_y,
                             PI_Z + BD_T + PI_CAP_STANDOFF)))


def pi_cap_pin(ref, n):
    """World point of pin `n` (1-based) on the cap's connector `ref`.

    Read off the ROUTED footprint (board_geom), so the pin order a wire is drawn into is the
    one the board actually has -- not a second copy of the pitch that could drift from it."""
    f = BG.footprint("pi_cap", ref)
    x0, x1, y0, y1 = f["fab"]
    pitch = 2.5 if "XH" in BG.fp_name(f["fpid"]) else 2.0
    cnt = {"J2": 4, "J4": 4, "J3": 6}[ref]
    px = (x0 + x1) / 2.0 + (n - (cnt + 1) / 2.0) * pitch
    py = (y0 + y1) / 2.0
    marker = box_at(0.01, 0.01, 0.01, x=px, y=py, z=0.0)
    bb = _cap_place(marker).val().BoundingBox()
    return ((bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0, (bb.zmin + bb.zmax) / 2.0)
_OP = BG.load("output_panel")
OP_BOARD_X, OP_BOARD_Y = _OP["outline_mm"]
_OP_T = _OP["thickness_mm"]
# the three connectors a player reaches through the panel, in the order they sit along it
OP_PANEL_REFS = ("J5", "J1", "J6")          # 1/4 in jack, USB-C, 24 V barrel


def output_panel_pcb() -> cq.Workplane:
    """The output + panel board in its OWN frame: centred on the origin in XY, underside
    at z = 0, parts rising +Z, the panel connectors facing +X -- built from the routed
    board, not from a table of what it was meant to be."""
    return BG.solid("output_panel")


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
    Y: the TS jack's axis lands on TS_Y.
    Z: from the TS jack's BORE, not the board -- it is the part whose hole a player has
       to hit with a plug, so it owns the row height and the board hangs where that puts
       it. (The other two holes are wherever the board then puts THEIR axes; they used
       to share this one Z, which is how the USB-C hole ended up 7.85 mm too high.)"""
    ts = BG.mouth("output_panel", "J5")
    return (JACK_WALL_X - OP_PANEL_CLR - OP_BOARD_X / 2, TS_Y - ts["across"],
            JACK_Z - _OP_T - ts["axis_h"])


def op_panel_openings():
    """[(ref, world y, world z, opening)] -- the hole the panel needs for each connector,
    centred where the ROUTED board puts that connector. A "rect" opening may carry its own
    centre height (the barrel's body is not symmetric about its bore)."""
    cx, cy, cz = op_origin()
    out = []
    for ref in OP_PANEL_REFS:
        m = BG.mouth("output_panel", ref)
        op = m["spec"]["opening"]
        zc = op[3] if (op[0] == "rect" and len(op) > 3) else m["axis_h"]
        out.append((ref, cy + m["across"], cz + _OP_T + zc, op))
    return out


def op_rear_mounts():
    """[(ref, world y, world axis z, spec)] -- the panel parts that CLAMP to the panel (the TS
    jack): the endplate stands a boss behind the panel for their shoulder and counterbores
    the face for their nut."""
    cx, cy, cz = op_origin()
    out = []
    for ref in OP_PANEL_REFS:
        m = BG.mouth("output_panel", ref)
        if m["spec"]["mount"] == "rear":
            out.append((ref, cy + m["across"], cz + _OP_T + m["axis_h"], m["spec"]))
    return out


def op_panel_fronts():
    """{ref: world x of the part's FRONT} -- where each connector finishes relative to the
    panel. The through-mount parts are meant to reach the face (JACK_TIP); J1 falls short
    by the board's J1_SETBACK because its own shell legs would otherwise cross the edge."""
    cx = op_origin()[0]
    return {ref: cx + BG.mouth("output_panel", ref)["front"] for ref in OP_PANEL_REFS}


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


def op_top(ref: str):
    """World (x, y, z) of the TOP of the output board's connector `ref`, over its body
    centre -- where a lead leaves a TOP-ENTRY header (J7, J9, J10 are vertical XH)."""
    cx, cy, cz = op_origin()
    f = BG.footprint("output_panel", ref)
    x0, x1, y0, y1 = f["fab"]
    h = BG.HEIGHT[BG.fp_name(f["fpid"])]
    return (cx + (x0 + x1) / 2.0, cy + (y0 + y1) / 2.0, cz + _OP_T + h)


def op_pt(ref: str):
    """World (x, y, z) where a lead leaves the output+panel board's connector `ref` -- so
    wiring.py asks the board rather than carrying a copy of its layout, the same contract
    mctrl_pt provides for the motor controller.

    ⚠ IT RETURNS THE BODY'S FAR FACE ALONG +Y FOR EVERY REF, which is right for the
    connectors the harness actually uses (J7, J9, J10 exit +Y) and not for the -X three.
    Those need their own exit vector before wiring.py routes a lead to one."""
    cx, cy, cz = op_origin()
    f = BG.footprint("output_panel", ref)
    x0, x1, y0, y1 = f["fab"]
    h = BG.HEIGHT[BG.fp_name(f["fpid"])]
    return (cx + (x0 + x1) / 2.0, cy + y1, cz + _OP_T + h / 2.0)


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


def _mctrl_fab(ref):
    """(x0, x1, y0, y1) of a part's routed F.Fab body, in the rectangle frame."""
    x0, x1, y0, y1 = BG.footprint("motor_ctrl", ref)["fab"]
    return x0, x1, y0 + _MCTRL_DY, y1 + _MCTRL_DY


# ⚠ EVERY PART OF THIS BOARD IS READ OFF THE ROUTED BOARD NOW (2026-09-21). It was a hand
# table -- sixty rows of courtyard boxes and pad-row centres typed from motor_ctrl.py's
# placements -- and cad_geom_check found 8 of its 60 parts not where the router left them.
# A copy of the layout's INPUT cannot know where the layout's OUTPUT put anything; the same
# export the output board's CAD reads (elec/geom/*.geom.json) can.
# The connectors wiring.py asks about: each lead leaves its body's centre.
MCTRL_J = {r: ((_f := _mctrl_fab(r))[0] / 2 + _f[1] / 2, _f[2] / 2 + _f[3] / 2,
               BG.footprint("motor_ctrl", r)["rot"])
           for r in ("J1", "J2", "J3", "J4", "J5", "J6")}
# J1 bus A, J3 24 V, J4 the USB link to the Pi (a top-entry XH now -- the USB-C it replaced
# faced the -Y rail 5.5 mm away and could not be plugged in), J5 5 V to the Pi.
# ⚠ J2 AND J6 ARE THE BUS-B PAIR, AND THEY ARE SIDE ENTRY (2026-09-25). The 8-way vertical
# PH became two 4-way S4B-PH-SM4-TB on the board's flat +X edge -- the edge stand() maps to
# world -Z -- so each half of the lever/pedal bus unplugs DOWNWARD, through the chassis,
# without reaching inside the instrument. mctrl_pt's mated-height lookup only knows the
# VERTICAL parts, so what it returns for these two is the body's reach, not a seated plug.


def motor_ctrl_pcb(mating: bool = False) -> cq.Workplane:
    """The motor controller, in its OWN frame: the rectangle centred on the origin in XY
    (its mounting ear off the +Y edge), underside at z=0, every part rising +Z -- the
    ROUTED board (board_geom.solid), not a table. `mating=True` stands the XH headers at
    their plugged height, which is the volume a housing has to leave alone."""
    return BG.solid("motor_ctrl", mated=mating).translate((0.0, _MCTRL_DY, 0.0))


def mctrl_pt(ref: str):
    """Tray FLAT-frame (x, y, z) where a lead leaves the motor controller's
    connector `ref` -- so wiring.py asks the board where its connectors are
    instead of carrying a copy of the layout. Every lead, the USB link's included,
    leaves +Z off the top of a mated XH plug.

    ⚠ THERE IS NO MAPPING HERE ANY MORE. The board is authored in the orientation it is
    built in (elec/motor_ctrl.py), so board-local IS tray-local up to the footprint's
    centre. This used to hold a 90 deg turn to reconcile two frames, and then a branch to
    decide whether to apply it -- two places to get the same fact wrong."""
    cx, cy = _ctr(MCTRL_FP)
    # ⚠ board_geom ANSWERS THIS, because it is the module that already knows a side-entry
    # plug leaves through the board EDGE (it grows the solid that way for _SIDE_PLUG_RUN).
    # This used to add a MATED HEIGHT to every connector alike, which for J2/J6 -- the
    # whole bus-B input, side entry on the +X edge -- put the lead over the top of a
    # shell that has no top, inside the socket instead of on a seated plug.
    lx, ly, lz = BG.lead_exit("motor_ctrl", ref)
    return (cx + lx, cy + ly + _MCTRL_DY, MCTRL_BOARD_Z + lz)


MCTRL_PORT_CLR = 0.5                 # around whatever of the board enters the floor


def mctrl_floor_ports():
    """The floor openings the motor controller needs, as cutters.

    ⚠ THE BOARD HANGS INTO THE FLOOR ON PURPOSE (user, 2026-09-25: "move the board -z until
    the latch mechanism for the JST is clear of the instrument underside"). A mated PH plug
    stands only 4.1 mm past the board's edge and the floor is 10.5 mm thick, so no amount of
    plug reaches daylight while the board stops at the floor -- the BOARD has to come down
    with it. It does: the plug tips sit 3.10 mm proud of the underside, which is what a hand
    squeezes, and the laminate still stops 1.00 mm inside.
    ⚠ A THIN SLOT, NOT A FINGER HOLE. Because the latch is reachable from OUTSIDE, none of
    this has to admit a hand -- 287 mm2 against roughly 1000 for two finger holes, which is
    the whole reason the downward edge was made the narrow one.
    ⚠ THE FOOTPRINT, NOT ITS BOUNDING BOX. The plate and the two plugs TOUCH, so they come
    back as ONE solid whose bbox is the full 8.1 x 47 mm rectangle -- five times the opening
    needed, and the opposite of the point. Walk the board's length and take each slice's own
    x-extent: the shape is axis-aligned, so slices recover it exactly and equal neighbours
    merge back into runs.
    ⚠ IT LIVES HERE AND NOT IN chassis.py. chassis builds its segments at import and
    electronics imports chassis, so the chassis cannot ask where this board is without a
    circular import -- it asked, and got a half-initialised module. The chassis stays
    ignorant of its contents and the ASSEMBLY cuts these (see build.py).
    """
    from . import motor_bank as MB
    z0 = CH.Z_BOT - 1.0
    h = (MB.FLOOR_TOP - CH.Z_BOT) + 2.0
    zc = (CH.Z_BOT + MB.FLOOR_TOP) / 2.0
    band = box_at(1600.0, 1600.0, MB.FLOOR_TOP - CH.Z_BOT, x=-300.0, y=0.0, z=zc)
    below = motor_ctrl().intersect(band)
    bb = below.val().BoundingBox()
    runs, step = [], 0.5
    for i in range(int(round((bb.ymax - bb.ymin) / step))):
        ya, yb = bb.ymin + i * step, bb.ymin + (i + 1) * step
        try:
            sb = below.intersect(
                box_at(1600.0, yb - ya, h, x=-300.0, y=(ya + yb) / 2, z=zc)).val().BoundingBox()
        except Exception:
            continue
        if sb.xlen <= 0.0:
            continue
        key = (round(sb.xmin, 2), round(sb.xmax, 2))
        if runs and runs[-1][0] == key and abs(runs[-1][2] - ya) < 1e-6:
            runs[-1][2] = yb
        else:
            runs.append([key, ya, yb])
    c = MCTRL_PORT_CLR
    return [box_at(k[1] - k[0] + 2 * c, yb - ya + 2 * c, h,
                   x=(k[0] + k[1]) / 2, y=(ya + yb) / 2, z=z0 + h / 2)
            for k, ya, yb in runs]


# pi_cap_relief() lived here and is DELETED (user, 2026-09-29). It cut a 5.8 mm pocket in
# the bay's -Y wall so the Pi cap's 3.82 mm of overhang could sit inside it. The Pi now
# stands +3.82 further +Y with the cap FLUSH on the wall's face, so the wall is whole and
# the pocket has nothing to do. Kept as a note rather than silence because the pocket was
# deliberate and reasoned when it was written -- what changed is the board's position, and
# a reader finding the old call in history should see why it went rather than assume it was
# lost in a merge.
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
FLOOR_Z = CH.Z_BOT


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
TEE_RELIEF   = (38.0, 3.0)                           # base tail-relief window (w × l), board-local, at (0, CONN_CY)


def tee_board_cy(y: float) -> float:
    """Board (and cradle) centre Y for a tee at station y: the -Y edge stays at y-7
    (clear of the -Y rail, as before); the board grows +Y into the open corridor."""
    return y + TEE_YSHIFT


def tee_pcb(x: float, y: float, drop: int = 1, accurate: bool = True) -> cq.Workplane:
    """CAN bus TEE PCB dummy, flat on the chassis floor. THREE 4-pin TOP-ENTRY XH
    (B4B-XH-A; cadkit jst_xh_header, drawn MATED) -- trunk-in / drop / trunk-out,
    L-to-R, cables up -- plus the 120 Ω-behind-jumper terminator (closed only on
    each bus's LAST tee). Serves the 10 bus-A motor tees on the open -Y rail. `drop`
    = ±1 marks the device side (cables are top-entry, so it doesn't change the board
    geometry). Mount: ONE M4 THROUGH the bare ear off its +X end (wiring.tee_hold). `accurate=False` -> the compact bus-B
    placeholder (see _tee_pcb_placeholder)."""
    if not accurate:
        return _tee_pcb_placeholder(x, y, drop)
    top = FLOOR_Z + 1.6                              # board top face; connectors rise +Z from here
    cy = tee_board_cy(y)
    # `x` is the OUTLINE centre. Bronner's 40 mm layout region is the -X part of it; off its
    # +X end is a bare EAR, D.TEE_EAR_X by D.TEE_EAR_Y at the +Y corner, with the retaining M4's
    # clearance hole through it. An L, not a rectangle -- see D.TEE_EAR_Y.
    xl = x - D.TEE_EAR_X / 2                         # the layout region's own centre
    ey = cy + (TEE_BOARD_Y - D.TEE_EAR_Y) / 2        # the ear's own centre Y
    b = box_at(TEE_BOARD_X, TEE_BOARD_Y, 1.6, x=xl, y=cy, z=FLOOR_Z + 0.8)
    b = b.union(box_at(D.TEE_EAR_X, D.TEE_EAR_Y, 1.6,
                       x=x + TEE_BOARD_X / 2, y=ey, z=FLOOR_Z + 0.8))
    b = b.cut(cq.Workplane(obj=cq.Solid.makeCylinder(
        2.25, 3.6, cq.Vector(x + TEE_BOARD_X / 2, ey, FLOOR_Z - 1.0))))   # M4 clearance
    # ONE row along X: the 8-way trunk, then the 4-way drop beside it. Pin rows collinear, so
    # the tail band is ~1.5 deep instead of 7.5 and clears the faceplate wall's strip.
    l8, l4 = xh_side_length(TEE_TRUNK_N, smt=False), xh_side_length(TEE_CONN_N, smt=False)
    run = l8 + l4
    for n, dx in ((TEE_TRUNK_N, -run / 2 + l8 / 2), (TEE_CONN_N, run / 2 - l4 / 2)):
        b = b.union(jst_xh_side_header(n, smt=False, mated=True)
                    .translate((xl + dx, cy + TEE_CONN_CY - TEE_MOUTH_DY, top)))
    b = b.union(box_at(3.5, 2.0, 1.8, x=xl - run / 2 - 1.5, y=cy - 4.0, z=top + 0.9))  # 120R + jumper
    return b


# (THE TRRS <-> JST-XH ADAPTER PCB IS DELETED, 2026-09-16, user. It existed to put the
#  leg-link TRRS jack on a board so the joint could be crossed without crimping a
#  factory-cabled part -- and the leg column has since become an off-the-shelf TRRS
#  M->F extension cable with molded ends, which crosses the same joint with ZERO
#  connections on the leg. The board was solving a problem the cable stopped having.
#
#  Nothing referenced trrs_adapter_pcb: it was modelled, dimensioned against the real
#  PJ-320D-4A and B4B-XH-A courtyards, given an M4 through-hole for retention, and never
#  placed in an assembly. Worth noting, because a part with no caller is exactly the kind
#  that survives a design change unnoticed.
#
#  The leg's own TRRS geometry is NOT this and stays: see TRRS_DX/TRRS_DY and
#  leg_shaft_trrs in legs.py, which seat the naked 10-03404 jack and the extension
#  cable's molded barrel. Same four wires, different problem.)


# (ts_jack is DELETED: the 1/4 in jack is a PCB part on the output+panel board
#  now -- see board_geom.PANEL. Modelling it as a free-floating panel jack implied
#  hand-soldered lugs, which the project forbids.)


# (dc_jack is DELETED: the 24 V inlet is a PCB part on the output+panel board now
#  -- J6 on the routed board (board_geom). As a free-standing panel jack it was
#  a PJ-005A, whose SOLDER
#  LUGS carried the same hand-soldering violation the TS jack did.)
