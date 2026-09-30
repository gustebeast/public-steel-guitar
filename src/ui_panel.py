"""The UI station: the OLED, its encoder, the board that carries them, and the deck
around all three.

ONE FILE OWNS THE DATUMS AND BOTH SIDES READ THEM. `elec/ui_board.py` imports this
module for the board's size, its centre and where each connector's row has to land, and
fabs from that; the CAD here reads the ROUTED board back through `src/board_geom.py` and
draws what KiCad actually placed. So the two cannot drift: move the display and the
board's placements move with it, and if the router or a footprint change moves a part,
the CAD shows the part where it moved to rather than where the table said it would be.
`elec/cad_geom_check.py` closes the loop by asking whether the solid this file builds has
material where every routed footprint's body is.

WARNING: THE DATUMS ARE FUNCTIONS, NOT MODULE CONSTANTS, and that is load-bearing:
top_plate.py imports THIS module (it cuts the deck), so this module cannot import
top_plate at import time. Everything that needs the deck's own numbers takes them lazily.

-- WHERE IT SITS (user, 2026-09-25) ------------------------------------------
X: as far +X as the deck allows. The bridge end of the deck is a grid of BAND_W slots
that the pickup piece and its fillers SWAP AROUND in, so anything fixed there would block
a pickup position. The station therefore stops at the -X end of that region, and it stops
a full 1.6 mm short of it, because the display's pocket wall is what stands there and
1.6 is two beads -- the thinnest wall this project will print.

Y: "instrument edge, joystick, display, fret marker border with equal space between each"
(user). Measured between the VISIBLE things, which is what that sentence is about: the
deck's own -Y edge, the knob's O17 cap, the display's 63.41 x 32.69 VIEWING area, and the
-Y edge of the fretboard's border frame. Three equal gaps fall out of those four; nothing
here is typed.

...and the KNOB's X is its own rule, because the X above places the DISPLAY. The cap's
+X edge is level with the window's +X edge, so the two stand the same 9.90 off the seam.
See knob_x(), which records the two wrong readings of "equally spaced" that came first.

-- HOW IT GOES IN AND OUT (user, 2026-09-28) ---------------------------------
THE STATION IS BUILT ONTO THE PANEL WHILE THE PANEL IS OFF THE INSTRUMENT, and then
the panel is slid on with all of it attached. In order: build the station onto the mid
panel, slide that panel on, plug the ribbon into the Pi, slide the keyhead panel on,
fit the endplate. Out is the reverse.

ONE CLAMP PLATE AND TWO M4s HOLD IT. Plastic takes every direction but the one it
installs along: the display's pocket walls and the window ledge, the board's cradle wall
and four bearings. The clamp plate lies against the board's underside and its two screws
pull the whole sandwich up into the deck's own bosses -- and an arm off it reaches under
the display to press the module's far end into the ledge, which is the screen's only
positive retention. Undo two screws and the station comes away as one piece.

WHAT IS ACTUALLY UNDER IT, measured rather than assumed. An earlier probe of mine
reported 57.5 mm of clear air under the whole station and was WRONG -- it filtered out
almost every part in the instrument and found two. Intersecting a prism over the
station's plan with everything gives:

    under the BOARD     wire_usb at -18.00, then the motor pigtails at -21.45
    under the DISPLAY   wire_canl at -17.24, the tee boards at -19.65

The board's own through-hole tails already reach -16.50, so the clearance under this
station is a millimetre and a half, not five centimetres. That is why the clamp lies
AGAINST the board with reliefs for the tails instead of hanging below them, and why its
arm steps up to -8.0 before running +Y under the display.

...AND THE PANEL SLIDES ON WITH ALL OF IT ATTACHED, which is a 361 mm stroke past the
whole bay. Stepping the real solids along it, the only thing the station meets is
wire_usb, and only in the last 30 mm at the keyhead -- where that cable climbs to the
Pi, on a keyhead endplate that is not fitted until after the panels.

-- DOES THE SCREEN SIT LEVEL? (user, 2026-09-28) ------------------------------
Its face lies on the window ledge, which is a flat, so level means only: can the face
REACH that flat, and does anything hold it there.

REACH is the tolerance question, and it is why MOD_PRELOAD exists. If the socket bottoms
out on the header before the face touches, the module hangs on twenty pins at whatever
angle they give it, and no amount of clamping recovers that. So the header is made to
stand proud: with the face on the ledge the socket is 0.60 from bottoming, which is more
than the realistic stack (RSS 0.50 of the module's own +-0.3 and four printed +-0.2s).

HOLDING it there is the clamp's arm: two posts on the module's far mounting-hole row,
reaching exactly its back, so the far end cannot droop. The near end is the header's own
20 pins, 2.5 mm from the module's edge. Droop at the far end is bounded by the print
tolerance on those posts -- 0.2 short is 0.27 deg over the 43 mm hole pitch, which is
0.16 mm from one end of the window to the other.

-- THE STACK, TOP DOWN -------------------------------------------------------
    deck top            +6.4   the player's surface
    window ledge        1.6    two beads of deck left over the module: the bezel
    module face         +4.8   the glass, sunk in a pocket cut UP from the underside
    module back         -0.7   5.5 of module, so it hangs 0.7 below the deck
    socket + header     11.04  a 1x20 female on the MODULE over a 1x20 male on ours
    UI board top        -11.74
    UI board bottom     -13.34

MALE ON OUR BOARD, FEMALE ON THE MODULE, and it is not arbitrary. Newhaven ships the
module with plated holes and no header ("Recommended Pin Header: 1x20pin 2.54mm pitch",
note 5 on their drawing), so we choose both halves. Put the SOCKET on our board and the
module needs a header whose pins reach 8.5 mm down through it -- a long-pin part, not a
stock one. Put the socket on the MODULE and both halves are ordinary catalogue parts: a
6.0 mm pin engages 6.0 mm of contact. The cost is 2.5 mm more stack, which buys the
right-angle ribbon header underneath the room it needs.
"""
from __future__ import annotations

import math
from functools import lru_cache

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl
from cadkit.fasteners import (M4, M4_BUTTON_HEAD_H, cut_insert_bore, m4_button_screw,
                              seated_insert)

# -- THE DISPLAY, off Newhaven's own mechanical drawing (NHD-2.7-12864WDW3, rev
#    08/18/2023, read 2026-09-25) --------------------------------------------------
# Frame: the module's PCB, +Y toward the HEADER edge, origin at the PCB's centre.
MOD_W, MOD_L = 82.00, 47.50        # the module PCB, X x Y
MOD_T        = 5.50                # PCB back face to bezel front face
MOD_PCB_T    = 1.00
HDR_EDGE_DY  = 2.50                # header row below the header edge; the two mounting
                                   # holes on that side share the row
HDR_N        = 20
HDR_PITCH    = 2.54                # 19 x 2.54 = 48.26, centred in X
MOD_HOLE_D   = 2.50
MOD_HOLE_DX  = 36.70               # +-, from the module centre
MOD_HOLE_DY  = 43.00               # between the two hole rows
BEZEL_W, BEZEL_L = 74.20, 42.50    # the metal bezel
BEZEL_EDGE_DY    = 4.50            # bezel top below the header edge
OPEN_W, OPEN_L   = 66.00, 33.00    # bezel OPENING -- what actually limits the view
VIEW_W, VIEW_L   = 63.41, 32.69    # viewing area
ACT_W,  ACT_L    = 61.41, 30.69    # active area, 128 x 64 at a 0.48 dot pitch
# The optical centre, measured from the HEADER edge: the bezel starts 4.50 in and the
# opening/view/active are all centred in its 42.50. That is 2.00 further from the header
# edge than the PCB's own centre, which is the only asymmetry in the part.
VIEW_FROM_HDR = BEZEL_EDGE_DY + BEZEL_L / 2.0        # 25.75
VIEW_OFF_Y    = VIEW_FROM_HDR - MOD_L / 2.0          # 2.00, away from the header
# 0.25 OF THAT 2.00 IS AN INFERENCE. The drawing dimensions the bezel 4.50 from the
# header edge and 42.50 tall, and its bottom then lands 0.50 short of the PCB's bottom
# edge, which the side view draws as flush. One of the two is rounded. The standard
# tolerance on the sheet is +-0.3, so the optical centre is 2.00 +-0.25 -- immaterial
# inside a 33 mm window with 4 mm of ledge all round, and recorded because a later
# reader measuring the real part will find the difference and wonder which is wrong.

# -- THE ENCODER ------------------------------------------------------------
# MEASURED OFF ALPS' OWN 3D MODEL (the one LCSC ship with C160841, read 2026-09-28 by
# slicing its mesh level by level), NOT off the catalogue drawing. The drawing is a
# 592-pixel GIF and I read two of its numbers wrong from it:
#
#   * "1.8 +-0.03" is NOT a length. It is the WIDTH ACROSS THE FLAT of a D-cut shaft.
#     The mesh settles it: from z 12.10 up the section is x +-1.25 but y -1.24..+0.55,
#     which is O2.5 with one side milled to 1.79. A round bore on a rotary encoder is
#     a knob that spins, so this is the difference between a working control and a
#     useless one.
#   * "17.4" is measured to the MOUNTING FACE, not to the terminal tips. The shaft tip
#     stands 17.10 above the board, not the 14.2 that reading gave.
#
# And the catalogue's W x D x H "10.5" is over the COLLAR, not the body: the 17 x 17
# body tops out at 8.30 and a two-step collar carries on to 10.20.
ENC_SQ        = 17.0               # body, W x D
ENC_BODY_H    = 8.30               # the 17 x 17 body above the PCB
ENC_COLLAR_D  = 7.10               # first collar step, to ENC_COLLAR_Z
ENC_COLLAR_Z  = 10.20              # collar top (the catalogue's "10.5")
ENC_TAIL      = 3.5                # terminals below the PCB (the drawing says 3.2;
                                   # the model draws 3.5, so the model's is carried)
ENC_SHAFT_Z0  = 11.10              # shaft root above the PCB
ENC_SHAFT_TIP = 17.10              # shaft tip above the PCB
ENC_FLAT_Z0   = 12.10              # ...and where its flat starts: only THIS much of
                                   # the shaft can key a cap
ENC_SHAFT_D   = 2.5
ENC_FLAT_W    = 1.79               # across the flat (the drawing's 1.8 +-0.03)
ENC_FLAT_DIR  = +1                 # the flat faces +Y in the BOARD frame -- fixed by
                                   # the model, whose ground lug lands at y -3.75 where
                                   # the footprint's pad 10 is, so its Y is the board's
ENC_FULCRUM   = 5.55               # lever pivot above the PCB
ENC_TILT      = 9.0                # degrees, each direction

# -- THE PRINTED CAP --------------------------------------------------------
# O17 to match the body, because that is the width the Y spacing is measured on: what
# the player sees is the cap, not the switch under it.
KNOB_D       = ENC_SQ              # 17.0
KNOB_SHANK_D = 8.0                 # what passes through the deck
KNOB_CLR     = 0.5                 # air under the cap at rest
KNOB_H       = 4 * D.BEAD          # 3.2 of cap above its own underside
KNOB_HOLE_AIR = 1.0                # radial air left round the shank at FULL deflection,
                                   # measured at the deck's top face where the throw is
                                   # widest. It is not a fit gap: nothing bears here and
                                   # the stick must never find the hole before its own stop
KNOB_CONE     = 14.0               # the cap's underside cone, degrees. Anything over the
                                   # 9 deg tilt clears at every radius at once; 14 leaves
                                   # margin for a printed surface and still lets the cap
                                   # sit close to the deck
KNOB_BORE_CLR = 0.15               # per face, round AND flat: a press fit on a D that
                                   # has to TRANSMIT the detent torque, so it is tighter
                                   # than a sliding fit and looser than an interference
                                   # one -- the cap is PCTG and the shaft is steel
# THE CAP PRINTS DISC-DOWN, on the flat top face it presents to the player. Every other
# way up puts the shaft bore's blind end over air. Its own +Z is the world's, so the
# declaration is the world axis turned over.
KNOB_UP = (0.0, 0.0, -1.0)
# The clamp goes the other way: its flat underside is the bed and every pad, rib and
# post grows straight up off it.
CLAMP_UP = (0.0, 0.0, 1.0)

# -- THE BOARD --------------------------------------------------------------
# 72 x 34, and both numbers are set by parts rather than chosen: the 1x20 header is
# 50.9 long and the right-angle ribbon header is 25.5, so the board is as wide as the
# header plus margin and as deep as the span from that header's row to the encoder's.
# It stays inside the display module's own 82 x 47.5 shadow in X, which is what keeps
# the whole station clear of the swappable band region (see the module docstring).
BOARD_W, BOARD_L = 72.0, 34.0
BOARD_T = 1.6
# Both halves READ, not assumed (LCSC, 2026-09-25): our male header is Kinghelm
# KH-2.54PH180-1X20P-L11.5 -- insulation height 2.5, mating pin 6.0, tail 3.0 -- and the
# module gets KH-2.54FH-1X20P-H8.5, an 8.5 socket. The module's PCB lands on the male
# insulator, so the stack is 2.5 + 8.5, with the full 6.0 of pin engaged in the socket.
SOCKET_H = 2.5 + 8.5
# ...AND THE STACK IS DELIBERATELY 1.0 TOO LONG, which is what keeps the SCREEN LEVEL.
# The module's face has to lie flat on the window ledge, and the only thing that can stop
# it getting there is its socket bottoming out on the header first -- which would leave
# the module hanging on twenty pins at whatever angle they happened to hold it. So the
# socket must never reach the bottom: the header is made to stand proud by more than the
# whole stack-up can swallow.
#
# The stack-up it has to swallow: the module's own 5.5 at the drawing's +-0.3, the
# printed pocket at +-0.2, the printed bearing posts at +-0.2, the socket's 8.5 and the
# header's 2.5 at +-0.2 each. Root-sum-square that and it is 0.50; add them all up the
# same way and it is 1.10.
#
# 0.6, WHICH IS THE RSS AND NOT THE SUM, and the reason is that it is not free: every
# 0.1 of preload lifts the BOARD 0.1 and takes 0.1 off the headroom under the deck, where
# the right-angle ribbon header stands. At 1.0 the assertion in elec/ui_board.py fired --
# 0.70 of margin against that header's (estimated) 10.0 -- which is the two constraints
# meeting. At 0.6 there is 1.10.
#
# What gives in the arithmetic worst case is the module's header end sitting a couple of
# tenths off the ledge, which the clamp's arm counteracts at the far end. What must NOT
# happen is the socket bottoming first, and 0.6 covers every realistic stack for that.
# The cost in engagement is 6.0 of pin down to 5.4.
MOD_PRELOAD = 0.6
# ONE M4, AND IT ONLY HAS TO HOLD Z (user, 2026-09-28). There were two, because one
# screw through a 72 mm board is a hinge -- but the answer to a hinge is not a second
# screw, it is plastic. X, Y and rotation are taken by two SPIGOTS that come down off
# the deck, pass through clearance holes in the board and enter sockets in the clamp
# plate. That is the project's own rule: plastic captures every direction but the one
# you install along, and one M4 takes that one.
#
# Central, because that is what a Z-only fastener wants and nothing else competes for
# the position now. It is also 16 mm clear of the encoder's -X edge: at 5.7 a clearance
# hole stood in the throat every switch net escapes through and the router left SW_PUSH
# and SW_B short.
SCREW_XY = (0.0, 0.0)

# THE TWO SPIGOTS, in board coordinates: as far apart as the routed board allows, which
# is what makes them a rotation stop rather than a pair of pivots. Both land on bare
# board -- (29.5, 9.0) in the gap between the encoder's courtyard and J1's row (at
# 8.0 its socket left a 1.03 mm web to the encoder's own relief in the clamp), and
# (-18.0, -9.0) in the clear block between the ribbon header and the encoder.
# ...and BOTH in the +Y half, which is not an accident: the -Y half of this board is one
# uninterrupted lane for the seven switch nets, and a O4.6 hole at (-18, -9) stood in it
# and left ENC_B unroutable. Two pins locate a plane wherever they sit, so the pair went
# where the copper has nothing to lose.
SPIGOTS = ((29.5, 9.0), (-18.0, 6.0))
SPIGOT_D = 4.0
SPIGOT_CLR = 0.3                   # per side, in the board's hole and the clamp's socket
# 1.6, not 2.4: the socket is BLIND and the plate is only 3.2, so the depth and the
# floor under it share that. At 2.4 the floor came out at exactly 0.80 -- the one-bead
# hard floor, not the two-bead one this project builds to. check_thin found it. A O4
# pin 1.6 deep is plenty for a locating feature that carries no load.
SPIGOT_DEPTH = 1.6

# -- THE RIBBON TO THE PI ---------------------------------------------------
# Its shape lives here rather than in wiring.py because elec/ui_board.py imports this
# module and can be held to it: the conductor count is J2's way count and the pitch is
# half the header's, which is what an IDC ribbon is.
RIBBON_N = 14
RIBBON_PITCH = 1.27
RIBBON_T = 0.9                     # 1.27 flat cable, and each conductor's pitch circle:
                                   # neighbouring ways touch, which is what makes it a
                                   # ribbon rather than fourteen wires
# ...AND IT TURNS TWO CORNERS BY BEING FOLDED. The run is flat under the deck -- width
# in Y, thickness in Z, because there is only 10.70 of headroom and 17.78 of it on edge
# does not fit -- so both of its 90 degree turns are IN THE RIBBON'S OWN PLANE, and flat
# cable can only do that creased over at 45 degrees. Ordinary, and free, but it is an
# assembly step somebody has to get the right way round, so the count is declared here
# and cadkit.cables.flat_bends holds the modelled path to it.
RIBBON_FOLDS = 2
RIBBON_W = RIBBON_N * RIBBON_PITCH  # 17.78, the cable's own width. Every way's insulation
                                    # touches its neighbour's, so the ribbon is exactly as
                                    # wide as the ways it has -- which is also the width
                                    # the CAD sweeps, as ONE prism rather than fourteen
SCREW_CLR_D = 4.5                  # its clearance hole in the board

# -- THE DECK ---------------------------------------------------------------
LEDGE_T    = D.MIN_WALL_2P         # 1.6 of deck left over the module = the bezel
# -- HOW MUCH OF THE SCREEN THE DECK IS ALLOWED TO COVER: none of it -------------------
# The window was the module's own BEZEL OPENING (66 x 33), on the reasoning that beyond
# that aperture there is only metal frame, so nothing is lost. True, and it is the wrong
# datum: it says what the MODULE shows, not what the deck must not cover, and the two
# only happen to be close. Against the 128 x 64 of ACTIVE area it left 1.155 mm a side in
# Y, and three things eat into that --
#     +-0.30  the module's slip fit in its pocket
#     +-0.30  the drawing's own standard linear tolerance
#     +-0.25  MY inference about where the optical centre sits in Y (see VIEW_OFF_Y)
# -- - 0.85 of the 1.155, leaving 0.30. Positive, so no lit pixel was ever going to be
# covered, and far too thin to have arrived at by accident.
#
# So the window is sized off the ACTIVE AREA and a stated margin instead. 1.6 is the
# project's two-bead unit and it swallows the 1.05 above with room over. In X that comes
# out INSIDE the bezel's aperture; in Y it runs 0.44 past it, which shows a hair of the
# module's own black frame and is the right trade -- a window tight to the lit rectangle
# also looks better than one with a band of dead glass round it.
WINDOW_MARGIN = D.MIN_WALL_2P
WIN_W = ACT_W + 2 * WINDOW_MARGIN          # 64.61
WIN_L = ACT_L + 2 * WINDOW_MARGIN          # 33.89
assert WIN_W <= BEZEL_W - 2 * D.MIN_WALL_2P and WIN_L <= BEZEL_L - 2 * D.MIN_WALL_2P, (
    "the window is %.2f x %.2f and the module's bezel is %.2f x %.2f -- the deck's ledge "
    "would have nothing to bear on" % (WIN_W, WIN_L, BEZEL_W, BEZEL_L))
POCKET_CLR = 0.3                   # slip fit round the module
EDGE_WALL  = D.MIN_WALL_2P         # 1.6 from the pocket to the panel's +X seam
POST_SQ    = 4.0                   # the deck's bearing posts. 4.0, not 5.0: the only
                                   # clear ground left at the +X end is the 5.4 mm strip
                                   # between the encoder's courtyard and the pull-up row
# 3.2, AND IT IS A CEILING, NOT A CHOICE. The bay under this station is not the clear
# air an earlier probe of mine reported -- that probe filtered out almost every part in
# the instrument and found two. Measured properly, by intersecting a prism over the
# board's plan with everything:
#     under the BOARD    the highest thing is wire_usb at -18.00
#     under the DISPLAY  wire_canl at -17.24, then the tee boards at -19.65
# The board's own through-hole tails already reach -16.50. So the whole budget between
# the tails and the harness is 1.50 mm, and a plate slung under the tails -- which is
# what this was -- lands in the middle of the motor bank's wiring.
#
# The plate therefore sits AT the board's underside and takes a relief under every
# footprint for the tails to hang into. Its top face IS the bearing surface, which is
# simpler than pads and grips the whole board rather than four spots.
CLAMP_T    = 4 * D.BEAD
CLAMP_TAIL_CLR = 0.5               # air under the longest through-hole tail
# 0.4, grown round each through-hole footprint. It is a CEILING, not a fit: the fab box
# already bounds the tails, so the relief only has to exist -- and J1's and J2's boxes
# pass within 2.43 of each other, so anything over 0.415 leaves a web under the two-bead
# floor between them. check_thin is what found that, at 1.43.
CLAMP_RELIEF = 0.4
CLAMP_RIB_W = 6.0                  # the arm that reaches under the display
CLAMP_RIB_H = 6.0
CLAMP_ARM_Z = -8.0                 # the arm's TOP, once it has stepped up past the
                                   # board. Its UNDERSIDE then sits at -14.0, which is
                                   # 3.2 clear of the highest thing under the display
                                   # (wire_canl at -17.24); at the plate's own level it
                                   # would have been 1.8 INSIDE it
# A stock length, and the SHORTER of the two that fit. 3.2 of clamp + 1.6 of board
# leaves 7.2 in a boss that is 11.1 deep -- full engagement in the 5.0 insert and 2.2 to
# spare. M4x16 also satisfies the bite, and its tip then stood 0.10 past the boss's top
# into the deck panel's own body, which the overlap gate reported at 1.26 mm3. A screw
# that ends inside the part it threads into is the better answer than a longer bore.
CLAMP_SCREW_L = 12.0
assert CLAMP_SCREW_L - CLAMP_T - BOARD_T >= M4.insert_depth, (
    "an M4 x %.1f leaves %.1f in the insert, which is %.1f deep"
    % (CLAMP_SCREW_L, CLAMP_SCREW_L - CLAMP_T - BOARD_T, M4.insert_depth))
POST_CLR   = 0.3


ENC_FOOTPRINT = "Alps_RKJXT1F42001"


@lru_cache(maxsize=None)
def enc_anchor_offset():
    """(dx, dy) from the encoder's BODY centre to its PAD CENTROID, board frame.

    elec/layout.py anchors every footprint on the mean of its pads, which is the right
    default -- for a symmetric header it is the pin row's centre, and for a two-pad
    passive it is the part. The Alps switch is neither: its ten terminals and its
    position lug sit round the shaft in no symmetry at all, so the pad centroid is
    0.14 x 0.12 off the shaft. Place the part on the rule's point and the SHAFT lands
    0.19 away from it -- under a print tolerance, and still a number nobody would ever
    find again.

    So it is measured, from the footprint file itself rather than copied out of it: the
    same .kicad_mod the fab gets. Edit a pad there and this follows.

    (The lug's O1.3 is an unnumbered np_thru_hole, and it COUNTS -- pcbnew's Pads()
    returns it and layout's centroid averages it in with the rest. Leaving it out here
    would put the shaft back where this function exists to stop it going.)"""
    import os
    import re
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "elec", "footprints", "Steel.pretty", ENC_FOOTPRINT + ".kicad_mod")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    pads = [(float(a), float(b)) for a, b in
            re.findall(r"\(pad\s+\"[^\"]*\"\s+\S+\s+\S+\s+\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\)",
                       src)]
    assert len(pads) == 11, ("%s: found %d pads, expected the 10 terminals plus the "
                             "position lug" % (ENC_FOOTPRINT, len(pads)))
    return (sum(p[0] for p in pads) / len(pads),
            -sum(p[1] for p in pads) / len(pads))       # .kicad_mod is +Y DOWN


# -- what the cap and the shaft have to agree about, stated once ------------
# Cheap arithmetic, checked at import. The SOLID proof is a separate matter: tilting the
# real knob against the real deck through 36 directions leaves 1.19 mm at full 9 deg
# deflection and 2.94 mm at rest, the tightest point being the shank against the wall of
# the deck's hole, 1.41 below the deck's top face. These three are the relationships
# that produce that, so they are the ones that would quietly stop being true.
assert KNOB_CONE > ENC_TILT, (
    "the cap's underside cone is %.1f deg against a %.1f deg tilt -- its rim would "
    "strike the deck before the stick reached its own stop" % (KNOB_CONE, ENC_TILT))
assert ENC_SHAFT_TIP - ENC_FLAT_Z0 >= 4.0, (
    "only %.2f mm of this shaft carries its flat; a printed cap needs more than that to "
    "key on" % (ENC_SHAFT_TIP - ENC_FLAT_Z0))
assert ENC_FLAT_W < ENC_SHAFT_D, (
    "the shaft's flat (%.2f) is not smaller than its diameter (%.2f) -- that is a ROUND "
    "shaft, and a round bore on a rotary encoder is a knob that spins"
    % (ENC_FLAT_W, ENC_SHAFT_D))


def _tp():
    """top_plate, imported late -- it imports THIS module (see the docstring)."""
    from . import top_plate as TP
    return TP


# -- Z: every face in the stack, derived downward from the deck's own top ----
@lru_cache(maxsize=None)
def z_stack():
    """(deck_top, deck_bot, mod_face, mod_back, board_top, board_bot)."""
    TP = _tp()
    mod_face = TP.TZ - LEDGE_T
    mod_back = mod_face - MOD_T
    board_top = mod_back - SOCKET_H + MOD_PRELOAD
    return (TP.TZ, TP.BZ, mod_face, mod_back, board_top, board_top - BOARD_T)


def collar_clears_deck():
    """The switch's collar has to stop short of the deck's underside: only the shaft is
    allowed through the hole. Checked as a function because it needs the deck's Z."""
    _tz, bz, _f, _b, board_top, _bb = z_stack()
    top = board_top + ENC_COLLAR_Z
    assert top < bz - 0.5, (
        "the switch's collar reaches z %.2f and the deck's underside is %.2f" % (top, bz))
    return bz - top


def board_z0():
    """The UI board's UNDERSIDE -- what board_geom.solid() is placed on."""
    return z_stack()[5]


# -- Y: the four visible things, equally spaced -----------------------------
@lru_cache(maxsize=None)
def y_layout():
    """(gap, knob_y, view_y) from the user's rule, derived, nothing typed.

    Between the deck's -Y edge and the -Y edge of the fretboard border sit the knob's
    cap and the display's VIEWING area, with three equal gaps. The knob is measured on
    its cap and the display on its window, because those are the two things the rule is
    about -- the module's 47.5 PCB is under the deck and nobody sees it."""
    TP = _tp()
    y0, y1 = TP.BY0, -TP.BORDER_HY          # deck -Y edge .. fretboard border
    gap = (y1 - y0 - KNOB_D - VIEW_L) / 3.0
    knob_y = y0 + gap + KNOB_D / 2.0
    view_y = knob_y + KNOB_D / 2.0 + gap + VIEW_L / 2.0
    assert abs(y1 - (view_y + VIEW_L / 2.0) - gap) < 1e-9, "the three gaps are not equal"
    return gap, knob_y, view_y


@lru_cache(maxsize=None)
def ui_x():
    """The station's X centre: the display's window, the knob and the board all share it.

    Pushed as far +X as the deck allows. The band region's -X end is where the swappable
    slots stop; the module's POCKET has to keep a printable wall to that seam, and the
    pocket is the module's outline plus its fit clearance -- so the module's +X edge is
    one wall plus one clearance short of the seam, and everything else hangs off that."""
    TP = _tp()
    mod_x1 = TP.REGION_X1 - EDGE_WALL - POCKET_CLR      # the module's +X edge
    return mod_x1 - MOD_W / 2.0


@lru_cache(maxsize=None)
def knob_x():
    """THE RULE for the knob's X: its cap's +X edge is level with the WINDOW's +X edge,
    so the two stand the same distance off the deck panel's +X seam (user, 2026-09-28).

    Two wrong answers came before this one, and the difference between them is worth
    stating because "equally spaced" can mean either.

      * It first shared the display's X CENTRE, which is equal spacing about the screen
        and leaves the knob 45 mm from the seam against 16.7 to the instrument's -Y edge.
      * It then took the Y layout's own gap, 16.69, to the seam -- equal to the other
        gaps in the station but NOT to the screen's own 9.90, which the user measured off
        the model and which is what "equally spaced from the top panel edge" meant.

    So the datum is the WINDOW, not the seam and not the module: the seam is only where
    the deck happens to be divided, and the module is under the deck where nobody sees
    it. Two visible things, one edge, one distance."""
    return ui_x() + OPEN_W / 2.0 - KNOB_D / 2.0


def knob_centre():
    """Where the knob ACTUALLY is: the routed switch's body centre.

    knob_x() and y_layout() are the RULE; this is what KiCad did with it, and the cap,
    its bore and the deck's hole are all cut from this one so they cannot disagree with
    the board that gets fabbed.

    THE TWO ARE COMPARED IN elec/cad_geom_check.py, NOT HERE, and the reason is a
    deadlock: elec/ui_board.py imports this module for the rule, importing it builds the
    deck, and building the deck reads the routed board. An assertion on that path stops
    the generator from running at all the moment the rule moves -- which is exactly when
    you need to run it. The check belongs after the route, and that is where it is."""
    return routed("SW1")


def module_centre():
    """(x, y) of the display module's PCB centre. Its optical centre is VIEW_OFF_Y away
    from it, on the side AWAY from the header -- and the header faces -Y, toward the
    knob, because that is the side our board is on."""
    return ui_x(), y_layout()[2] - VIEW_OFF_Y


def header_row_y():
    """World Y of the module's 1x20 row -- and so of our board's header.

    -Y of the module's centre, because the header edge faces the knob: our board is on
    that side and nothing else could reach the row."""
    return module_centre()[1] - (MOD_L / 2.0 - HDR_EDGE_DY)


def board_centre():
    """(x, y) of the UI board's centre.

    X is the station's. Y puts the encoder 4.263 below the centre, which is what makes
    the board reach from under the module's header row down past the encoder and stop
    clear of the -Y rail's inner face -- see the assertions in elec/ui_board.py, which
    are the ones that would fail if a part grew.

    THE BOARD OVERHANGS THE CABLE TROUGH, and it has to. The knob's Y is fixed by the
    spacing rule and the switch body is 17 across, so the board must reach into the
    band the chassis's -Y cable trough occupies; it passes 0.30 above that trough's
    lip. Fine standing still, not enough to slide 400 mm over -- and it never has to,
    because the assembly comes out before the panel moves either way. See the service
    order in the module docstring; deck_mount's own assertion holds everything that
    DOES slide clear of that trough."""
    return ui_x(), y_layout()[1] + 4.263


def board_local(x, y):
    """A world (x, y) in the board's own frame (+Y up), which is what elec/ places in."""
    cx, cy = board_centre()
    return x - cx, y - cy


# ============================================================================
# THE CAD, BUILT FROM THE ROUTED BOARD
# ============================================================================
# Everything below asks src/board_geom.py where KiCad actually put a part, and draws
# what it says. The display's position is the routed J1's; the knob's is the routed
# SW1's. Nothing here repeats a placement out of elec/ui_board.py, so nothing here can
# disagree with the board that gets fabbed.
#
# The import is LOCAL to each function on purpose: board_geom reads
# elec/geom/ui_board.geom.json, which does not exist until the board has been routed
# once, and elec/ui_board.py imports THIS module to place that board. Importing it at
# module scope would make the first run of a fresh checkout impossible.

def _bg():
    from . import board_geom as BG
    return BG


def routed(ref):
    """(x, y) of a routed footprint's F.Fab BODY centre, in WORLD coordinates."""
    f = _bg().footprint("ui_board", ref)
    x0, x1, y0, y1 = f["fab"]
    cx, cy = board_centre()
    return cx + (x0 + x1) / 2.0, cy + (y0 + y1) / 2.0


def ui_pcb():
    """The UI board and every part on it, as routed."""
    cx, cy = board_centre()
    return _bg().solid("ui_board").translate((cx, cy, board_z0()))


def display_module():
    """The Newhaven module, hung off the routed J1.

    The module's own 1x20 row plugs onto that header, so the header IS the module's
    datum: its row centre fixes the module in X and Y, and the deck's pocket fixes it
    in Z. The female socket on the module's back is NOT drawn -- it is exactly the
    SOCKET_H gap between our board's top face and the module's, and drawing it would
    put a solid through the very header it mates with."""
    hx, hy = routed("J1")
    mx = hx
    my = hy + (MOD_L / 2.0 - HDR_EDGE_DY)          # the header edge faces -Y
    _tz, _bz, face, back, _bt, _bb = z_stack()
    pcb = box_at(MOD_W, MOD_L, MOD_PCB_T, x=mx, y=my, z=back + MOD_PCB_T / 2.0)
    bez_y = my + VIEW_OFF_Y                         # the bezel is centred on the optics
    bez_z0 = back + MOD_PCB_T
    bezel = box_at(BEZEL_W, BEZEL_L, face - bez_z0,
                   x=mx, y=bez_y, z=(bez_z0 + face) / 2.0)
    # the lit area is its own part (see screen()), so take its skin out of the bezel
    # rather than letting the two share a volume
    return pcb.union(bezel).cut(box_at(ACT_W, ACT_L, 0.4, x=mx, y=bez_y, z=face - 0.1))


def screen():
    """The 128 x 64 of LIT AREA, as a face on the module's front.

    Drawn separately, and only because of how the assembly read without it: the module
    was one dark block 74.2 x 42.5, the deck's ledge covered its outer 4-5 mm all round
    -- which is the BEZEL doing its job -- and the picture said the panel was covering
    the screen. It never was. This is the rectangle that matters, in its own colour, so
    the question can be answered by looking."""
    hx, hy = routed("J1")
    my = hy + (MOD_L / 2.0 - HDR_EDGE_DY)
    face = z_stack()[2]
    return box_at(ACT_W, ACT_L, 0.2, x=hx, y=my + VIEW_OFF_Y, z=face - 0.1)


def knob_geometry():
    """(flat_z, tip_z, cap_z0, hole_d) -- the numbers the cap, the shaft and the hole share.

    THE HOLE IS SIZED BY THE TILT, NOT BY THE SHANK. The stick pivots 9 deg about a
    fulcrum 5.55 above the board, so the shank sweeps a cone: what has to fit through
    the deck is the shank's diameter plus twice its throw at the deck's TOP face, which
    is the furthest point from the pivot.

    THE CAP'S UNDERSIDE IS A CONE, not a flat disc, and that is what buys the clearance.
    A flat cap has to sit its whole rim's dip (half its diameter times sin 9) above the
    deck, which parked it 1.8 mm proud -- a visible gap for a clearance that is only
    ever needed at full deflection. A cone whose slope exceeds sin(tilt) clears at every
    radius at once, so the cap can come down until its INNER edge just clears, and the
    rim takes care of itself."""
    tz, _bz, _face, _back, board_top, _bb = z_stack()
    tip = board_top + ENC_SHAFT_TIP
    flat = board_top + ENC_FLAT_Z0
    pivot = board_top + ENC_FULCRUM
    t = math.tan(math.radians(ENC_TILT))
    hole_d = KNOB_SHANK_D + 2.0 * ((tz - pivot) * t + KNOB_HOLE_AIR)
    dip = math.sin(math.radians(ENC_TILT))
    cap_z0 = tz + KNOB_CLR + (KNOB_SHANK_D / 2.0) * dip   # the cone's INNER edge
    return flat, tip, cap_z0, hole_d


def knob():
    """The printed cap: a shank up through the deck and a coned O17 disc over it.

    THE BORE IS A D, because the shaft is. O2.5 milled to 1.79 across (see the encoder
    block above): a round bore would turn on it and the encoder would do nothing. The
    bore keys on the 5.0 mm of shaft that actually carries the flat, not on the round
    root below it.

    The cap is UNINDEXED -- a plain disc with no marking -- so which way round it goes
    on the D is free at assembly. Nothing downstream reads its clocking."""
    kx, ky = knob_centre()
    flat, tip, cap_z0, _hole = knob_geometry()
    rim_z0 = cap_z0 + (KNOB_D - KNOB_SHANK_D) / 2.0 * math.tan(math.radians(KNOB_CONE))
    s = cyl(KNOB_SHANK_D, cap_z0 - flat, z=flat)
    s = s.union(cq.Workplane("XY").add(cq.Solid.makeCone(
        KNOB_SHANK_D / 2.0, KNOB_D / 2.0, rim_z0 - cap_z0,
        cq.Vector(0, 0, cap_z0))))
    s = s.union(cyl(KNOB_D, KNOB_H, z=rim_z0))
    # the D bore: the shaft's own section grown KNOB_BORE_CLR on every face, running
    # from just under the cap's underside to past the tip so the shaft never bottoms
    r = ENC_SHAFT_D / 2.0 + KNOB_BORE_CLR
    y_flat = ENC_FLAT_DIR * (ENC_FLAT_W - ENC_SHAFT_D / 2.0 + KNOB_BORE_CLR)
    bore = cyl(2.0 * r, (tip + 0.4) - (flat - 0.05), z=flat - 0.05)
    keep = box_at(4.0 * r, 4.0 * r, (tip + 0.5) - (flat - 0.1),
                  x=0.0, y=y_flat - ENC_FLAT_DIR * 2.0 * r,
                  z=((tip + 0.4) + (flat - 0.05)) / 2.0)
    return s.cut(bore.intersect(keep)).translate((kx, ky, 0))


def encoder_shaft():
    """The switch's collar and D-shaft above its body -- the tenon the cap mortises on.

    board_geom draws every part as its F.Fab body extruded to one height, which for this
    switch is the 17 x 17 case and nothing above it. The collar and the shaft are what
    the cap and the deck's hole have to agree with, so they are drawn here from the same
    constants the cap's bore is cut from."""
    kx, ky = knob_centre()
    _tz, _bz, _face, _back, board_top, _bb = z_stack()
    s = cyl(ENC_COLLAR_D, ENC_COLLAR_Z - ENC_BODY_H, z=board_top + ENC_BODY_H)
    shaft = cyl(ENC_SHAFT_D, ENC_SHAFT_TIP - ENC_SHAFT_Z0, z=board_top + ENC_SHAFT_Z0)
    flat_z = board_top + ENC_FLAT_Z0
    r = ENC_SHAFT_D / 2.0
    shaft = shaft.cut(box_at(4 * r, 4 * r, (board_top + ENC_SHAFT_TIP) - flat_z + 0.1,
                             x=0.0,
                             y=ENC_FLAT_DIR * (ENC_FLAT_W - r + 2.0 * r),
                             z=(flat_z + board_top + ENC_SHAFT_TIP) / 2.0 + 0.05))
    return s.union(shaft).translate((kx, ky, 0))


# -- the deck ---------------------------------------------------------------
def deck_cutter():
    """Everything the UI takes out of its deck panel: the module's pocket, the window
    through the ledge over it, and the knob's hole."""
    tz, bz, face, _back, _bt, _bb = z_stack()
    hx, hy = routed("J1")
    mx, my = hx, hy + (MOD_L / 2.0 - HDR_EDGE_DY)
    c = POCKET_CLR
    # the pocket: open at the underside, its ceiling the face the module presses on
    out = box_at(MOD_W + 2 * c, MOD_L + 2 * c, face - bz + 1.0,
                 x=mx, y=my, z=(bz - 1.0 + face) / 2.0)
    # the window: the ACTIVE AREA plus WINDOW_MARGIN, which is the only thing the deck
    # is not allowed to cover (see the constant's note -- the bezel opening was the
    # wrong datum for it)
    out = out.union(box_at(WIN_W, WIN_L, tz - face + 2.0,
                           x=mx, y=my + VIEW_OFF_Y, z=(face + tz + 2.0) / 2.0))
    kx, ky = knob_centre()
    out = out.union(cyl(knob_geometry()[3], tz - bz + 2.0, z=bz - 1.0)
                    .translate((kx, ky, 0)))
    return out


def _posts():
    """[(x, y)] in BOARD coordinates of the four columns the board is pulled up onto.

    COLUMNS, NOT LEDGES, and the print decides it: the deck prints face-DOWN
    (top_plate.PIECE_UP), so everything under it grows away from the bed and a shelf
    poking inward off a wall would be a ceiling with nothing beneath it. A column from
    the deck's own underside is supported the whole way.

FOUR, spread as widely as the routed board allows, because the single M4 no longer
    shares the bearing job with a second one. The first two of them carry the SPIGOTS
    (see SPIGOTS): a post that already stops at the board's top face is the natural place
    to continue a locating pin through it. check_posts() below is what says none of them
    lands on a part, and it runs AFTER the route rather than here. A post on a part does reach
    the overlap gate -- it caught two of these at 0.8 mm3 when the pull-ups moved into a
    row -- but as an anonymous solid-on-solid finding, and what you want to be told is
    WHICH post and WHICH part."""
    return [(29.5, 9.0), (-18.0, -9.0), (-18.0, 6.0), (10.0, -9.0)]


def bearings():
    """[(x, y)] every place the deck touches the board's top face: the four posts and the
    screw boss. The clamp plate bears on the whole underside against them, so the board
    is squeezed rather than bent."""
    return _posts() + [SCREW_XY]


def check_posts():
    """[complaint] -- a post under the display module, or standing on a routed part.

    NOT an assertion, and not on the import path, for the same reason knob_centre()'s
    comparison is not: elec/ui_board.py imports this module, importing it builds the
    deck, and building the deck calls _posts(). An assertion there stops the generator
    from running the moment a part moves -- which is exactly when it has to run. This is
    called from elec/cad_geom_check.py, once the board it is checking against exists."""
    out = []
    half = POST_SQ / 2.0 + POST_CLR
    edge = board_local(0.0, module_centre()[1] - MOD_L / 2.0)[1]
    for px, py in bearings():
        if py + half > edge:
            out.append("the post at (%+.1f, %+.1f) reaches y %+.2f, under the display "
                       "module, whose edge is at %+.2f" % (px, py, py + half, edge))
        for f in _bg().load("ui_board")["footprints"]:
            if not f["fab"]:
                continue
            x0, x1, y0, y1 = f["fab"]
            if (px + half > x0 - 0.5 and px - half < x1 + 0.5
                    and py + half > y0 - 0.5 and py - half < y1 + 0.5):
                out.append("the post at (%+.1f, %+.1f) lands on %s, whose body is "
                           "x %.2f..%.2f y %.2f..%.2f" % (px, py, f["ref"], x0, x1, y0, y1))
    return out


def deck_mount():
    """The cradle fused to the deck's underside: two locating walls and the columns.

    ONE WALL, AND IT IS THE +X ONE. The board is located in X and Y by the screw
    itself -- a 4.0 shank in a 4.5 hole is a 0.25 fit, which is a location -- and all
    the wall has to do is stop it turning about that screw, which it does from 48 mm
    away. The columns set Z and the screw pulls the board up onto them from below.

    THERE IS NO -Y WALL, and the rail is why. The board's -Y edge sits 2.05 from the
    -Y rail's inner face, and a two-bead wall with a fit gap either side is 2.2 -- it
    would not go, and squeezing it to fit would put a printed fin a quarter of a
    millimetre off a printed rail that the whole deck panel slides -X past. There is no
    +Y wall either, because the display module hangs over that entire edge; the module's
    own 20-way socket ties the board that way once it is assembled.
    """
    _tz, bz, _face, _back, board_top, board_bot = z_stack()
    cx, cy = board_centre()
    hw, hl = BOARD_W / 2.0, BOARD_L / 2.0
    wall_t = D.MIN_WALL_2P
    wall_h = bz - (board_bot - 0.8)
    wall_z = (bz + board_bot - 0.8) / 2.0
    inner = POST_CLR
    y_stop = module_centre()[1] - MOD_L / 2.0 - POCKET_CLR      # the module's -Y edge
    # ...AND IT STOPS SHORT OF THE WIRE TROUGH. The wall is the only thing on this
    # panel that reaches below the board's underside, and the chassis's cable trough
    # runs the length of the -Y rail with its lip top at chassis.WT_ZF + WT_H. The deck
    # panel SLIDES OUT -X past all of it, so a wall that dipped over the trough would
    # scrape 400 mm of lip. It gives the trough a clear millimetre and keeps the wall
    # nearer the module, which is all the anti-rotation the one screw needs.
    from . import chassis as CH
    y0 = max(cy - hl - inner, CH.WT_Y0 + CH.WT_D + 1.0)
    s = box_at(wall_t, y_stop - y0, wall_h,
               x=cx + hw + inner + wall_t / 2.0, y=(y0 + y_stop) / 2.0, z=wall_z)
    assert (wall_z - wall_h / 2.0 > CH.WT_ZF + CH.WT_H
            or y0 > CH.WT_Y0 + CH.WT_D), (
        "the UI cradle's wall dips to %.2f over the cable trough, whose lip tops out "
        "at %.2f, and the deck panel slides -X past the whole length of it"
        % (wall_z - wall_h / 2.0, CH.WT_ZF + CH.WT_H))
    for px, py in _posts():
        s = s.union(box_at(POST_SQ, POST_SQ, bz - board_top,
                           x=cx + px, y=cy + py, z=(bz + board_top) / 2.0))
    # ...and two of them carry on THROUGH the board as spigots, into the clamp plate.
    # These are what hold the station in X, Y and rotation; the M4 only holds Z.
    clamp_top, _clamp_bot = clamp_z()
    for px, py in SPIGOTS:
        s = s.union(cyl(SPIGOT_D, board_top - (clamp_top - SPIGOT_DEPTH),
                        z=clamp_top - SPIGOT_DEPTH).translate((cx + px, cy + py, 0)))
    # the two screw bosses: columns like the posts, each with its insert pocket bored UP
    # from its own end face -- which prints as a blind hole opening at the top. Their end
    # faces are bearing surfaces too, which is why there are only two separate posts.
    bx, by = cx + SCREW_XY[0], cy + SCREW_XY[1]
    s = s.union(cyl(M4.insert_pilot_d + 2 * D.MIN_WALL_2P, bz - board_top, z=board_top)
                .translate((bx, by, 0)))
    return cut_insert_bore(
        M4, s, (bx, by, board_top), (0, 0, 1),
        CLAMP_SCREW_L - M4.insert_l + 1.0,
        reason="the UI's only fastener: a self-tapped M4 in PCTG would strip the first "
               "time the clamp came off for service, and it comes off for every display "
               "swap",
        print_up=_tp().PIECE_UP)


def clamp_z():
    """(top, bottom) of the clamp plate: its top face IS the board's underside.

    It used to hang below the THROUGH-HOLE TAILS -- 3.5 for the encoder's terminals,
    3.0 for the two headers -- which put it at -17.0/-23.4 and straight through the
    motor bank's harness. There is no room down there. It sits against the board
    instead and lets the tails hang into a relief under each footprint."""
    board_bot = z_stack()[5]
    return board_bot, board_bot - CLAMP_T


def clamp():
    """THE CLAMP PLATE: what actually holds the station in (user, 2026-09-28).

    A printed plate against the board's underside, pulled up by two M4s into the deck's
    own bosses. It does three things the single screw did not:

      * it SQUEEZES the board rather than hinging it. Its whole top face bears, against
        four bearing faces on the deck -- two posts and the two bosses' own ends -- so
        the board is gripped between opposed surfaces instead of pinched at one point.
      * it REACHES THE SCREEN. An arm steps up past the board and runs +Y under the
        display to its far mounting-hole row, where two posts press the module's back up
        into the window ledge. Until this the module's 47.5 mm was carried at one edge by
        its own 20-way header and nothing else -- the "lackluster" the user was looking
        at.
      * and it is the ONE PART you undo.

A RELIEF UNDER THE THROUGH-HOLE FOOTPRINTS ONLY, from board_geom.TAIL. Relieving
    every footprint was tried and is worse: the 0402s do not need it, and two of their
    reliefs left a 1.38 mm web between them -- under the two-bead floor.

    THE ARM BEARS ON THE MOUNTING-HOLE PADS, x +-36.70 at the module's far hole row,
    because that is the one region of a module's back guaranteed to be clear of
    components. CONFIRM IT against the real part before printing: Newhaven's rear view
    shows parts, and their drawing does not dimension them."""
    cx, cy = board_centre()
    top, bot = clamp_z()
    hw, hl = BOARD_W / 2.0, BOARD_L / 2.0
    _tz, _bz, _face, mod_back, _board_top, _board_bot = z_stack()
    from . import chassis as CH
    # ...AND ITS -Y EDGE STOPS CLEAR OF THE CABLE TROUGH, for the same reason the deck's
    # wall does: the panel is slid on and off with the whole station bolted to it, and
    # the trough's lip runs the length of the rail.
    y0 = max(cy - hl - 2.0, CH.WT_Y0 + CH.WT_D + 0.5)
    # +Y OF THE BOARD BY MORE THAN THE ARM IS WIDE, so the riser stands on plate that
    # is not over the board -- at 2.0 it stood on the board itself and drove 121 mm3 of
    # rib straight up through it. Its WIDTH is the board's, not more: the deck's own
    # locating wall runs down the +X side and a wider plate lands inside it.
    y1 = cy + hl + CLAMP_RIB_W + 2.0
    s = box_at(BOARD_W, y1 - y0, CLAMP_T, x=cx, y=(y0 + y1) / 2.0,
               z=(top + bot) / 2.0)
    assert bot > CH.WT_ZF + CH.WT_H or y0 > CH.WT_Y0 + CH.WT_D, (
        "the clamp plate reaches z %.2f over the cable trough, whose lip tops out at "
        "%.2f" % (bot, CH.WT_ZF + CH.WT_H))
    for _ref, (x0, x1, fy0, fy1), tail in _bg().tails("ui_board"):
        if tail <= 0.0:
            continue
        s = s.cut(box_at(x1 - x0 + 2 * CLAMP_RELIEF, fy1 - fy0 + 2 * CLAMP_RELIEF,
                         CLAMP_T + 2.0, x=cx + (x0 + x1) / 2.0, y=cy + (fy0 + fy1) / 2.0,
                         z=(top + bot) / 2.0))
    # the arm to the display: up past the board, +Y to the far mounting-hole row, a
    # crossbar there, and two posts to the module's back
    # ...AND THE ARM IS A FIN OFF THE BED, not a beam in mid-air. Drawn as a 6 mm bar
    # at the arm's height it was a 35 mm bridge over nothing -- 650 mm2 of unsupported
    # ceiling, on a part whose whole point is stiffness. Taken down to the plate's own
    # underside it grows straight up off the bed, needs no support, and is four times
    # the section it was.
    mx, _my = module_centre()
    far_y = header_row_y() + MOD_HOLE_DY
    fin_y0 = y1 - CLAMP_RIB_W
    s = s.union(box_at(CLAMP_RIB_W, far_y - fin_y0, CLAMP_ARM_Z - bot, x=mx,
                       y=(fin_y0 + far_y) / 2.0, z=(bot + CLAMP_ARM_Z) / 2.0))
    s = s.union(box_at(2 * MOD_HOLE_DX + CLAMP_RIB_W, CLAMP_RIB_W, CLAMP_ARM_Z - bot,
                       x=mx, y=far_y, z=(bot + CLAMP_ARM_Z) / 2.0))
    for sx in (-1, 1):
        s = s.union(cyl(CLAMP_RIB_W, mod_back - CLAMP_ARM_Z, z=CLAMP_ARM_Z)
                    .translate((mx + sx * MOD_HOLE_DX, far_y, 0)))
    # the spigot sockets: blind, so the plate keeps a floor under them -- a through
    # hole would leave two O4.6 windows in the one part that is here for stiffness
    for px, py in SPIGOTS:
        s = s.cut(cyl(SPIGOT_D + 2 * SPIGOT_CLR, SPIGOT_DEPTH + 0.1,
                      z=top - SPIGOT_DEPTH).translate((cx + px, cy + py, 0)))
    s = s.cut(cyl(M4.shaft_clr_d, CLAMP_T + 2.0, z=bot - 1.0)
              .translate((cx + SCREW_XY[0], cy + SCREW_XY[1], 0)))
    assert CLAMP_T - SPIGOT_DEPTH >= D.MIN_WALL_2P, (
        "the spigot socket leaves %.2f of floor under it, against a two-bead floor of "
        "%.2f" % (CLAMP_T - SPIGOT_DEPTH, D.MIN_WALL_2P))
    return s


def hardware():
    """[(name, solid)] the one M4 that pulls the clamp up, and its insert."""
    _tz, _bz, _face, _back, board_top, _bb = z_stack()
    cx, cy = board_centre()
    _top, bot = clamp_z()
    bx, by = cx + SCREW_XY[0], cy + SCREW_XY[1]
    # IT GOES IN FROM UNDERNEATH, so the dummy is turned over: cadkit draws one head-top
    # at z=0 with its shank running -Z, and here the head is the low end and the shank
    # climbs through the clamp and the board into the boss.
    return [("ui_screw", m4_button_screw(CLAMP_SCREW_L)
             .rotate((0, 0, 0), (1, 0, 0), 180)
             .translate((bx, by, bot - M4_BUTTON_HEAD_H))),
            ("ui_insert", seated_insert(M4, (bx, by, board_top), (0, 0, 1)))]


def parts():
    """[(name, solid)] everything the assembly shows for the UI station."""
    return [("ui_pcb", ui_pcb()), ("ui_display", display_module()),
            ("ui_screen", screen()), ("ui_clamp", clamp()),
            ("ui_shaft", encoder_shaft()), ("ui_knob", knob())] + hardware()
