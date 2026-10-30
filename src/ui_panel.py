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

-- WHERE IT SITS (user, 2026-10-30, replacing 2026-09-25's and 2026-10-29's) ----------
"Center the screen between the fretboard border and the -y edge of the top panel and then
put the joystick to the screen +x and the power to the screen -x, trying to keep them as
close to the screen as we can while maintaining sufficient clearance."

Y: the lit area's centre is halfway between the fret border and the deck's -Y edge, and
both inputs share that Y. See screen_y().

X: the bridge end of the deck is a grid of BAND_W slots that the pickup piece and its
fillers SWAP AROUND in, so nothing fixed may enter it. The board's +X edge stops EDGE_WALL
short of that seam, the knob stands on that edge, the display is a deck wall away from the
knob's hole, and the power button a deck wall away on the display's other side. See
knob_x(), ui_x() and power_x().

The board runs under the module from one input to the other, so it is 121 long, and the
deck can only reach it in the two wings either side of the pocket. See SCREW_XY.

-- HOW IT GOES IN AND OUT (user, 2026-09-28) ---------------------------------
THE STATION IS BUILT ONTO THE PANEL WHILE THE PANEL IS OFF THE INSTRUMENT, and then
the panel is slid on with all of it attached. In order: build the station onto the mid
panel, slide that panel on, plug the ribbon into the Pi, slide the keyhead panel on,
fit the endplate. Out is the reverse.

ONE CLAMP PLATE, ONE M4 AND ONE KEEPER HOLD IT. Plastic takes every direction but the one
it installs along: the display's pocket walls and the window ledge, the two spigots and
the deck's bearings. The clamp plate lies against the board's underside; its -X tongue
hooks into a keeper on the deck, and the M4 at the knob's end pulls the +X end up -- and
four columns off it press the module's PCB into the ledge at its four mounting holes,
which is the screen's only positive retention (the display's ribbon carries nothing).
Undo the M4, swing the +X end down and draw the tongue out: the station comes away as one
piece. Release the ribbon from J1 to part the board from the display.

WHAT IS ACTUALLY UNDER IT. The tee boards at -19.65 and the wires round them: the clamp's
underside is at -15.9 and the tails reach -16.1, so the whole budget is about 2 mm, which
is why the clamp lies AGAINST the board with reliefs for the tails.

AND THE PANEL SLIDES ON WITH ALL OF IT ATTACHED, past the Pi's USB-A leads, so THE Pi's
USB-A PLUGS GO IN AFTER THIS PANEL IS ON, in the same step as the ribbon, and come out
before it slides off. (INSTALL_NOTES.md says so.) The cable trough's lip runs the whole
stroke, top at -13.6: the clamp's near bar ramps up over it (clamp()).

-- DOES THE SCREEN SIT LEVEL? (user, 2026-09-28) ------------------------------
Its face lies on the window ledge, which is a flat, so level means only: does anything
hold it there. Nothing else touches the module now -- the ribbon below carries no load --
so the face reaches the flat by construction and the clamp is the whole answer.

HOLDING it there is the clamp: four columns, one at each of the module's mounting holes,
reaching its PCB's back face. The far two stand on the plate, past the board's +Y edge, and
the near two on a bar past its -Y edge.

-- THE DISPLAY'S CONNECTION IS A RIBBON (user, 2026-10-19) ---------------------
"Solderless" ruled out the through-hole module: Newhaven ship it with twenty bare plated
holes, so any header on it is a hand-soldered joint on a bought part. Its sibling,
NHD-2.7-12864WDW3-M, is the same panel, outline, bezel and pin table with a 20-way
1.0 mm FFC socket (Molex 52271-2079, bottom contact, 3.0 high) on its back. So the joint
is now three bought parts and no solder at all: that socket, a stock 50 mm same-side FFC
(JUSHUO JS10A-20P-050-4-8), and a JLC-placed Molex 52271-2079 on our board,
edge, its mouth facing the module. See ffc_path() for the cable's route.

-- THE STACK, TOP DOWN -------------------------------------------------------
    deck top            +6.4   the player's surface
    window ledge        1.6    two beads of deck left over the module: the bezel
    module face         +4.8   the glass, sunk in a pocket cut UP from the underside
    module PCB back     +1.4   2.4 of glass and bezel, 1.0 of PCB (Newhaven's side view)
    module rear         -0.7   its own parts on that back reach 5.5 from the face
    module's FFC socket -1.6   3.0 under the PCB: the -M's 6.40 overall
    ribbon loop                down from that socket and back into ours, in free air
    UI board top        -11.1
    UI board bottom     -12.7

THE BOARD'S Z IS NOT THE DISPLAY'S ANY MORE. It was set by the header stack under the
module, and it stays where that put it because two other things pin it to the tenth:
the encoder's collar clears the deck's underside by 0.9 above it, and the clamp's 2 mm
budget is below it. BOARD_GAP keeps that number.
"""
from __future__ import annotations

import math
from functools import lru_cache

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl
from cadkit.fasteners import (M4, M4_BUTTON_HEAD_H, cut_insert_bore, m4_button_screw,
                              seated_insert)

# -- THE DISPLAY, off Newhaven's own mechanical drawings (NHD-2.7-12864WDW3, rev
#    08/18/2023, read 2026-09-25; NHD-2.7-12864WDW3-M, 11/21/2022, read 2026-10-19) --
# Frame: the module's PCB, +Y toward the HEADER edge, origin at the PCB's centre. The
# "header edge" is the one the through-hole version's 1x20 row is on; the -M's FFC socket
# sits on the same edge.
MOD_W, MOD_L = 82.00, 47.50        # the module PCB, X x Y
MOD_T        = 5.50                # face to the rear of the parts on its back (the
                                   # drawing's 5.50; the -M adds its FFC socket below)
MOD_GLASS_T  = 2.40                # face to the PCB's FRONT: the side view's 2.40
MOD_PCB_T    = 1.00
# ...SO THE PCB'S BACK IS 3.40 UNDER THE FACE, NOT 5.50. The 5.50 was read as PCB-back
# to face until 2026-10-19, which left the clamp's posts 2.1 short of the board they were
# drawn pressing on. The side view puts 2.40 from the face to the PCB and the remaining
# 2.10 is the parts on its back, which is what MOD_T still bounds.
HDR_EDGE_DY  = 2.50                # the near mounting-hole row, below the header edge
MOD_HOLE_DX  = 36.70               # +-, from the module centre
MOD_HOLE_DY  = 43.00               # between the two hole rows
# THE -M's FFC SOCKET, Molex 52271-2079: 20 ways at 1.00, pins 1..20 centred in X (31.50
# from each end of the rear view), 3.00 above its board ("Height Above Board", Molex via
# DigiKey). Its Y extent is SCALED OFF the rear view, not dimensioned: the tails start
# 1.6 below the header edge, the housing 3.8, and the actuator's front -- the mouth, which
# faces the module's centre -- is 10.5 in. 27.2 across the actuator.
MOD_FFC_N      = 20
MOD_FFC_PITCH  = 1.00
MOD_FFC_W      = 27.2
MOD_FFC_Y0     = 3.8               # housing, from the header edge
MOD_FFC_MOUTH  = 10.5              # actuator front, from the header edge
MOD_FFC_H      = 3.00
MOD_FFC_SLOT   = 1.2               # ESTIMATE: the cable's centre under the module's PCB
# PIN 1 IS AT +X, seen from the front. The rear view shows it at the LEFT, and a rear view
# is the module turned over: its left is the front's right. CONFIRMED on the part
# (2026-10-19): Newhaven's product photo of the -M's back, its silkscreen reading the
# right way round, marks CN1 "1" at the left end and "20" at the right.
MOD_FFC_PIN1_DIR = +1
# THE PANEL'S OWN ZIF on the module's back, which the ribbon's top run passes under.
# SCALED OFF the rear view: ~20 wide, 19 to 26 below the header edge, and the drawing's
# MOD_T is the deepest anything on that back goes.
MOD_ZIF_W, MOD_ZIF_Y0, MOD_ZIF_Y1 = 20.0, 19.0, 26.0
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
# The power button's cap prints the same way up, for the same reason: its top face on
# the bed and the stem's square socket opening upward.
PWR_CAP_UP = (0.0, 0.0, -1.0)
# The clamp goes the other way: its flat underside is the bed and every pad, rib and
# post grows straight up off it.
CLAMP_UP = (0.0, 0.0, 1.0)

# -- THE BOARD --------------------------------------------------------------
# 121 x 32. The 121 is one input to the other: the knob's body and INPUT_EDGE at the +X end,
# the power switch, the clamp's web and the ribbon header at the -X end. The 32 is what the
# posts and the screw boss need above and below the encoder's 17 (see SCREW_XY).
BOARD_W, BOARD_L = 121.0, 32.0
BOARD_CY_OFF = 1.0                 # the board's centre, +Y of the inputs': the boss is
                                   # bigger than the post on the other side
BOARD_T = 1.6
# MODULE REAR TO BOARD TOP. It was the header stack (an 8.5 socket on a 2.5 insulator,
# 0.6 of it held back so the socket could never bottom before the face met the ledge).
# The headers are gone and the number is kept, because the board cannot move: see "THE
# BOARD'S Z" in the module docstring.
BOARD_GAP = 10.4

# -- THE DISPLAY'S RIBBON (user, 2026-10-19) -----------------------------------------
# JUSHUO JS10A-20P-050-4-8 (LCSC C2857604): 20 ways at 1.0, 50 mm overall, SAME-SIDE
# contacts, each end 4 mm of bare contacts under an 8 mm blue stiffener (its drawing).
# Same-side because the path below never turns the cable over: it leaves the module's
# socket with its contacts up against that board and arrives at ours with the same face
# down against this one, which is bottom contact at both ends.
FFC_L = 50.0
FFC_W = (MOD_FFC_N + 1) * MOD_FFC_PITCH   # 21.0, the drawing's (N+1) x 1.0
FFC_T = 0.30                       # the PLUG: "terminal thickness" T1/T2 0.3 +-0.05
FFC_STIFF = 8.0                    # the rigid end, measured from the cut
FFC_INSERT = 4.0                   # ...of which this much goes into a socket: the bare
                                   # contacts, which is what both sockets are drawn for
# THE LAYERS, off the same drawing. The film is three: 0.043 PET under, the 0.035 x 0.65
# tinned conductors, 0.043 PET over -- 0.121 in all ("thickness insulation"). At each
# end the OVER layer stops FFC_INSERT short of the cut, baring the conductors, and a
# 0.225 blue PET stiffener is laminated to the UNDER layer for FFC_STIFF. Under + copper
# + stiffener is the 0.30 that goes in a socket.
FFC_FILM_T = 0.121
FFC_INS_T = 0.043                  # each PET insulation layer
FFC_CU_T, FFC_CU_W = 0.035, 0.65
FFC_STIFF_T = 0.225
# the film's centre sits this far to the CONTACT side of the plug's centre, which is the
# slot's centre: about the film's centre the plug runs from +FFC_CU_T/2 (bare copper) to
# -(FFC_CU_T/2 + under + stiffener), so its middle is half of under + stiffener behind
FFC_FILM_OFF = (FFC_INS_T + FFC_STIFF_T) / 2.0
FFC_SLOT_H = 0.50                  # both sockets' mouths, drawn: the plug and some air
# Our end: Molex 52271-2079 (LCSC C588186), 3.0 high, 1.0 pitch, bottom contact.
# The slot's height over our board is an ESTIMATE off its section D-D.
J1_H = 3.0
J1_SLOT = 1.0
FFC_R_MIN = 1.2                    # the tightest bend drawn: four times its thickness
FFC_TOP_Z = -2.5                   # the run under the module, clear of its rear parts
# ONE M4, AND IT ONLY HAS TO HOLD Z (user, 2026-09-28). X, Y and rotation are taken by two
# SPIGOTS that come down off the deck, pass through clearance holes in the board and enter
# sockets in the clamp plate: plastic captures every direction but the one you install
# along, and one M4 takes that one.
#
# THE DECK ONLY REACHES THE BOARD IN ITS TWO WINGS, beside the module's pocket (2026-10-30),
# so the M4 is at the knob's end -- the end a thumb pushes hardest -- and the clamp's -X
# tongue in the KEEPER takes Z at the power button's. Each wing's bearings stand above and
# below its input. Board coordinates; the knob's body is at (51.0, -1.0), asserted in
# elec/ui_board.py, and the power switch's X is -49.6.
SCREW_XY = (51.0, 12.5)
SPIGOTS = ((51.0, -12.8), (-49.6, -11.5))
THIRD_POST = (-49.6, 9.5)
SPIGOT_D = 4.0
SPIGOT_CLR = 0.3                   # per side, in the board's hole and the clamp's socket
# 1.6, not 2.4: the socket is BLIND and the plate is only 3.2, so the depth and the
# floor under it share that. At 2.4 the floor came out at exactly 0.80 -- the one-bead
# hard floor, not the two-bead one this project builds to. check_thin found it. A O4
# pin 1.6 deep is plenty for a locating feature that carries no load.
SPIGOT_DEPTH = 1.6
# THE KEEPER: a column off the deck past the board's -X edge, with a tunnel the clamp's
# tongue enters heading -X. The deck prints face-down, so the tunnel's floor would be a
# ceiling: it is a 45 degree ramp and the tongue's underside is chamfered to match.
KEEPER_Y = 10.0                    # board coordinates: +Y of the ribbon's socket
KEEPER_W = 8.0                     # the tongue
KEEPER_CLR = 0.2
KEEPER_FLOOR = D.MIN_WALL_2P

# -- THE RIBBON TO THE PI ---------------------------------------------------
# Its shape lives here rather than in wiring.py because elec/ui_board.py imports this
# module and can be held to it: the conductor count is J2's way count and the pitch is
# half the header's, which is what an IDC ribbon is.
RIBBON_N = 16                      # 14 for the station + the power button's two throws
RIBBON_PITCH = 0.635               # was 1.27: the header is a 1.27 mm 2x7 now, the same
                                   # part as the Pi cap's end (2026-10-02), and its ribbon
                                   # is half ITS pitch
RIBBON_T = 0.65                    # 0.635 flat cable, and each conductor's pitch circle:
                                   # neighbouring ways touch, which is what makes it a
                                   # ribbon rather than sixteen wires
# ...AND IT TURNS ONE CORNER BY BEING FOLDED. The run is flat under the deck -- width
# in Y, thickness in Z, because there is only 10.70 of headroom and 17.78 of it on edge
# does not fit -- so its 90 degree turn onto the Pi cap's header's line is IN THE RIBBON'S
# OWN PLANE, and flat cable can only do that creased over at 45 degrees. Ordinary, and
# free, but it is an assembly step somebody has to get the right way round, so the count
# is declared here and cadkit.cables.flat_bends holds the modelled path to it. (Two until
# 2026-10-06, when the path ended at a typed point instead of on the header; the second
# turn, down onto the socket, is across the ribbon's width and is a plain bend.)
RIBBON_FOLDS = 1
RIBBON_W = RIBBON_N * RIBBON_PITCH  # 10.16, the cable's own width. Every way's insulation
                                    # touches its neighbour's, so the ribbon is exactly as
                                    # wide as the ways it has -- which is also the width
                                    # the CAD sweeps, as ONE prism rather than sixteen
# ...AND ITS TWO ENDS, the 2x8 1.27 IDC sockets pressed onto it (user, 2026-10-21: the
# cable ended in the air at the Pi). BOUGHT AS ONE LEAD, Samtec FFSD-08-D-20.00-01-N, and
# drawn off Samtec's own print (FFSD-XX-X-XX.XX-01-X-X-XXX, rev AW) and catalogue page
# (F-226): each socket 14.35 along the rows ("No of pos x 1.27 + 4.19"), 3.05 across them,
# 5.08 overall from its mating face, the last 1.02 of that a cover pressed over the cable
# onto the body's back. The ribbon lies between the two, across the rows -- square to the
# mating axis -- and ends flush with the socket's far side.
IDC_B = 8 * 1.27 + 4.19            # 14.35
IDC_BODY_R = IDC_COVER_R = 3.05
IDC_COVER_M = 1.02
IDC_GAP = RIBBON_T + 0.05          # the ribbon's slot between the two
IDC_BODY_M = 5.08 - IDC_COVER_M - IDC_GAP
IDC_CABLE_M = IDC_BODY_M + IDC_GAP / 2.0   # the ribbon's centre, out from the mating face
# WHERE IT STOPS ON THE PINS. The header (HX PZ1.27-2x8P WZ, its drawing 2022-04-24) puts
# 4.00 of pin out past its plastic, and this body is only 3.20 deep, so the socket bottoms
# on the pin tips and stands off the plastic -- it never reaches it. 3.00 of pin inside
# the body: Samtec give its insertion depth as 2.64 to 3.17. The board solid draws the
# pins as a block to their tips, and the
# socket's last IDC_PIN_IN of it is the designed mate (tools/check_overlaps.py).
HDR_PIN_OUT = 4.00
IDC_PIN_IN = 3.00


def idc_socket(mouth, m, r, w):
    """A 2x8 1.27 IDC socket: `mouth` the centre of its mating face, `m` the unit axis
    out of it (away from the header), `r` across the rows -- the way the ribbon leaves
    -- and `w` along them, all world axes. Body and cover as one solid with the ribbon's
    slot left open between them."""
    def box(dm0, dm1, dr, dw):
        ext = [abs(m[k]) * (dm1 - dm0) + abs(r[k]) * dr + abs(w[k]) * dw for k in range(3)]
        c = [mouth[k] + m[k] * (dm0 + dm1) / 2.0 for k in range(3)]
        return box_at(*ext, x=c[0], y=c[1], z=c[2])
    m0 = IDC_BODY_M + IDC_GAP
    return (box(0.0, IDC_BODY_M, IDC_BODY_R, IDC_B)
            .union(box(m0, m0 + IDC_COVER_M, IDC_COVER_R, IDC_B)))


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
# board's plan with everything (the numbers are in the module docstring): the tails
# reach -16.10 and the harness under them starts at -18.31, so the whole budget between
# the two is about 2 mm, and a plate slung under the tails -- which is
# what this was -- lands in the middle of the motor bank's wiring.
#
# The plate therefore sits AT the board's underside and takes a relief under every
# footprint for the tails to hang into. Its top face IS the bearing surface, which is
# simpler than pads and grips the whole board rather than four spots.
CLAMP_T    = 4 * D.BEAD
# 0.4, grown round each through-hole footprint. It is a CEILING, not a fit: the fab box
# already bounds the tails, so the relief only has to exist -- and the old 1x20 header's
# box and J2's passed within 2.43 of each other, so anything over 0.415 left a web under
# the two-bead floor between them. check_thin is what found that, at 1.43. (J1 is surface
# mount since the ribbon; J2 and SW2 keep a 2-bead web between theirs, ui_board asserts.)
CLAMP_RELIEF = 0.4
CLAMP_RIB_W = 6.0                  # the plate's far margin, past the far hole row
# THE FAR POSTS are O4 for the last stretch up, inside the deck's pocket: the hole is 2.5
# from the module's edge, so a O6 reached 0.5 past it and into the pocket's wall
# (POCKET_CLR is 0.3). The arm's own O6 carries on below the deck.
CLAMP_TIP_D = 2.0 * (HDR_EDGE_DY - 0.5)
CLAMP_ARM_Z = -6.0                 # the near bar's top
# M4 x 10, the length the rest of the instrument already buys (2026-10-07: one screw
# length fewer on the BOM; this was the x12). The head bears on the clamp's underside,
# the shank climbs 3.2 of clamp and 1.6 of board, and 5.2 is left for the boss: the whole
# 5.0 of the insert, whose mouth is the boss's end face on the board, and 0.2 beyond it.
# Measured on the solids, not only here -- tip at -5.90 against the insert's far end at
# -6.10, and the clamp is its full 3.2 round the screw hole (no recess, and the arm's
# step is elsewhere). CLAMP_RELIEF is sideways, round the footprints, and is not in this
# stack. A screw at the short end of its tolerance (ISO 7380: -0.29) still has 4.9 of
# the 5.0 in thread, more than a diameter. If this stack ever grows, take it out from
# under the head (a recess in the clamp), not with a longer screw: an M4 x 16 once stood
# 0.10 past the boss's top into the deck panel's own body.
CLAMP_SCREW_L = 10.0
assert CLAMP_SCREW_L - CLAMP_T - BOARD_T >= M4.insert_depth, (
    "an M4 x %.1f leaves %.1f in the insert, which is %.1f deep"
    % (CLAMP_SCREW_L, CLAMP_SCREW_L - CLAMP_T - BOARD_T, M4.insert_depth))
POST_CLR   = 0.3


ENC_FOOTPRINT = "Alps_RKJXT1F42001"

# -- THE POWER BUTTON (user, 2026-10-04) -----------------------------------------------
# A round cap that sits at one of two heights: proud is off, flush with the deck is on. Under it is
# a self-locking push switch on the board, Legion PB-22E85-S-5.7C-C-W (LCSC C22462024),
# and everything below except the cap is off its drawing:
PWR_BODY_H = 8.5                   # the case, which board_geom draws
PWR_STEM_SQ = 3.3                  # the stem the cap presses onto
PWR_STEM_H = 5.7                   # its top over the case, button OUT
PWR_LOCK = 1.5                     # how far down it sits latched
PWR_TRAVEL = 2.5                   # ...and how far it has to be pushed to latch or release
# ESTIMATE, scaled off the drawing rather than dimensioned on it: the stem is 3.3 square
# for roughly its top half and wider below. The cap's socket takes only this much of it,
# so the cap's skirt stops above the shoulder whatever the shoulder turns out to be.
PWR_STEM_GRIP = 2.5
# THE CAP'S DIAMETER IS A THUMB'S. It has to be followed a millimetre below the deck to
# release it, which the user put at about 15 (2026-10-04); 19 beads is that on the grid.
# The clamp plate keeps a two-bead web between the switch's relief and the ribbon header's;
# elec/ui_board.py asserts that web.
PWR_CAP_D = 19 * D.BEAD            # 15.2, against the knob's 17
PWR_HOLE_CLR = 0.3                 # per side, in the deck


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
    """(deck_top, deck_bot, mod_face, mod_back, board_top, board_bot). mod_back is the
    rear of the parts on the module's back; its PCB's back face is mod_pcb_back()."""
    TP = _tp()
    mod_face = TP.TZ - LEDGE_T
    mod_back = mod_face - MOD_T
    board_top = mod_back - BOARD_GAP
    return (TP.TZ, TP.BZ, mod_face, mod_back, board_top, board_top - BOARD_T)


def mod_pcb_back():
    """Z of the module PCB's back face: what the clamp's columns bear on."""
    return z_stack()[2] - MOD_GLASS_T - MOD_PCB_T


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


# -- WHERE IT SITS: see the module docstring ------------------------------------------
BOARD_WALL_CLR = 1.0               # board -Y edge to the -Y rail's inner face, at least
INPUT_EDGE = 1.0                   # bare board round the encoder's body: ui_board's margin
PWR_HALF = 4.25                    # the power switch's body


def fret_border_y():
    """World Y of the fret border's -Y outer edge."""
    return -_tp().BORDER_HY


def screen_y():
    """World Y of the LIT AREA's centre: halfway from the fret border to the deck's -Y edge
    (user, 2026-10-30). The window, the bezel and the active area all share it."""
    return (fret_border_y() + _tp().BY0) / 2.0


def input_y():
    """World Y of the knob's and the power button's centres: the screen's."""
    return screen_y()


def board_centre():
    """(x, y) of the UI board's centre. Its +X edge is the knob's body and INPUT_EDGE."""
    return (knob_x() + ENC_SQ / 2.0 + INPUT_EDGE - BOARD_W / 2.0,
            input_y() + BOARD_CY_OFF)


def header_edge_y():
    """World Y of the module's header edge, the one its FFC socket is on. It faces -Y."""
    return module_centre()[1] - MOD_L / 2.0


@lru_cache(maxsize=None)
def knob_x():
    """THE RULE for the knob's X: its body and INPUT_EDGE of board are EDGE_WALL short of
    the band region's seam (nothing fixed may enter that region), and the cap stands 2.6 off
    it. The display then comes as close as the knob's hole allows; see ui_x()."""
    return _tp().REGION_X1 - EDGE_WALL - INPUT_EDGE - ENC_SQ / 2.0


@lru_cache(maxsize=None)
def ui_x():
    """The display's X centre: its pocket a two-bead wall -X of the knob's hole."""
    return knob_x() - knob_geometry()[3] / 2.0 - D.MIN_WALL_2P - POCKET_CLR - MOD_W / 2.0


def power_x():
    """THE RULE for the power button's X: its hole a two-bead wall -X of the display's
    pocket. Its Y is the knob's, input_y()."""
    return (ui_x() - MOD_W / 2.0 - POCKET_CLR - D.MIN_WALL_2P
            - (PWR_CAP_D + 2 * PWR_HOLE_CLR) / 2.0)


def power_centre():
    """Where the button ACTUALLY is: the routed switch's body centre. See knob_centre()
    for why the rule and the route are compared after the route and not here."""
    return routed("SW2")


def knob_centre():
    """Where the knob ACTUALLY is: the routed switch's body centre.

    knob_x() and input_y() are the RULE; this is what KiCad did with it, and the cap,
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
    from it, on the side AWAY from the header, which faces -Y."""
    return ui_x(), screen_y() - VIEW_OFF_Y


def header_row_y():
    """World Y of the module's near mounting-hole row (the through-hole version's 1x20
    row shared it)."""
    return header_edge_y() + HDR_EDGE_DY


def mod_ffc_mouth():
    """(x, y, z) where the cable leaves the module's socket: the middle of the actuator's
    front face, at the slot's height."""
    return (module_centre()[0], header_edge_y() + MOD_FFC_MOUTH,
            mod_pcb_back() - MOD_FFC_SLOT)


def j1_mouth_y():
    """World Y of our FFC socket's mouth, off the ROUTED board: the end of its F.Fab body
    away from its contacts (it faces +Y, toward the module, and sits 1.62 inside the edge)."""
    f = _bg().footprint("ui_board", "J1")
    pads = list(f["pads"].values())
    pad_y = sum(q[1] for q in pads) / len(pads)
    mouth = max(f["fab"][2:], key=lambda v: abs(v - pad_y))
    assert mouth > pad_y, "the routed J1's mouth does not face +Y, toward the module"
    return board_centre()[1] + mouth


def board_local(x, y):
    """A world (x, y) in the board's own frame (+Y up), which is what elec/ places in."""
    cx, cy = board_centre()
    return x - cx, y - cy


# ============================================================================
# THE CAD, BUILT FROM THE ROUTED BOARD
# ============================================================================
# Everything below asks src/board_geom.py where KiCad actually put a part, and draws
# what it says. The knob's position is the routed SW1's and the ribbon's lower end the
# routed J1's. Nothing here repeats a placement out of elec/ui_board.py, so nothing here
# can disagree with the board that gets fabbed. The DISPLAY is the one exception, and
# rightly: it was hung off the routed 1x20 header that carried it, and since the ribbon
# nothing on the board holds it -- the deck's pocket does, so it is placed by the rule.
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
    """The UI board and every part on it, as routed -- with J1's mouth opened, so the
    ribbon's plug goes into it rather than through a block."""
    cx, cy = board_centre()
    f = _bg().footprint("ui_board", "J1")
    depth = max(f["fab"][2:]) - min(f["fab"][2:])
    assert FFC_INSERT + 0.2 < depth, (
        "J1's body is %.2f deep and the plug goes %.2f in" % (depth, FFC_INSERT + 0.2))
    return (_bg().solid("ui_board").translate((cx, cy, board_z0()))
            .cut(ffc_slot(ffc_ends()[1])))


def ui_silk():
    """The UI board's lettering, where the board is -- its own part (white ink)."""
    cx, cy = board_centre()
    w = _bg().ink("ui_board")
    return None if w is None else w.translate((cx, cy, board_z0()))


def display_module():
    """The Newhaven NHD-2.7-12864WDW3-M, where the deck's pocket holds it.

    PCB, glass and bezel, the panel's own ZIF on its back (the deepest thing there, so it
    stands for all of them), and the FFC socket the ribbon plugs into -- which is drawn
    as its own part, module_ffc_socket(), because it is a different thing in the hand."""
    mx, my = module_centre()
    _tz, _bz, face, back, _bt, _bb = z_stack()
    pcb_back = mod_pcb_back()
    pcb = box_at(MOD_W, MOD_L, MOD_PCB_T, x=mx, y=my, z=pcb_back + MOD_PCB_T / 2.0)
    bez_y = my + VIEW_OFF_Y                         # the bezel is centred on the optics
    bez_z0 = pcb_back + MOD_PCB_T
    bezel = box_at(BEZEL_W, BEZEL_L, face - bez_z0,
                   x=mx, y=bez_y, z=(bez_z0 + face) / 2.0)
    e = header_edge_y()
    zif = box_at(MOD_ZIF_W, MOD_ZIF_Y1 - MOD_ZIF_Y0, pcb_back - back,
                 x=mx, y=e + (MOD_ZIF_Y0 + MOD_ZIF_Y1) / 2.0, z=(pcb_back + back) / 2.0)
    # the lit area is its own part (see screen()), so take its skin out of the bezel
    # rather than letting the two share a volume
    return (pcb.union(bezel).union(zif)
            .cut(box_at(ACT_W, ACT_L, 0.4, x=mx, y=bez_y, z=face - 0.1)))


def module_ffc_socket():
    """The Molex 52271 on the module's back: housing and actuator as one block, from its
    tails' end to its mouth, hanging MOD_FFC_H under the PCB, with the plug's slot open."""
    mx, _my = module_centre()
    e = header_edge_y()
    z1 = mod_pcb_back()
    return (box_at(MOD_FFC_W, MOD_FFC_MOUTH - MOD_FFC_Y0, MOD_FFC_H,
                   x=mx, y=e + (MOD_FFC_Y0 + MOD_FFC_MOUTH) / 2.0, z=z1 - MOD_FFC_H / 2.0)
            .cut(ffc_slot(ffc_ends()[0])))


def _arc(cy, cz, r, a0, a1, n):
    """Points on a circle in the YZ plane, a0 to a1 degrees (0 = +Y, 90 = +Z)."""
    return [(cy + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(1, n + 1)]


@lru_cache(maxsize=None)
def ffc_path():
    """[(x, y, z)] the ribbon film's centreline, mouth to mouth: FFC_L less what is in
    the two sockets.

    THE SHAPE IS WHAT A 50 mm CABLE DOES BETWEEN THESE TWO MOUTHS, and the length is the
    constraint: 50 is the shortest 20-way same-side cable stocked, and the mouths are
    only ~21 apart. So the slack goes where there is room for it -- a hairpin under the
    module's centre, in the free air between its back and the clamp's plate:

      * out of the module's socket heading +Y (toward the module's centre), straight for
        the stiffener;
      * an S down to FFC_TOP_Z, under every part on the module's back -- the panel's own
        ZIF is the lowest, and the run passes 1.65 under it;
      * on +Y, then a half turn down to the height of our socket's slot;
      * back -Y, between the clamp's two arms, straight for the stiffener into our socket.

    Every turn is about the cable's width (X), so it is never folded or twisted. The top
    run's length is solved for, so the drawn cable is the bought one's length."""
    x, _y, _z = mod_ffc_mouth()
    hx, _hy = routed("J1")
    assert abs(hx - x) < 0.3, (
        "our FFC socket is at x %.2f and the module's at %.2f: a ribbon only bends about "
        "its width, so the two have to share a centreline" % (hx, x))
    (ym, zm_slot, nm), (yb, zb_slot, nb) = ffc_ends()
    # the path is the FILM's centreline, which is off the slot's centre toward the contacts
    zm = zm_slot + nm * FFC_FILM_OFF
    zb = zb_slot + nb * FFC_FILM_OFF
    out_ = FFC_STIFF - FFC_INSERT
    r1 = (zm - FFC_TOP_Z) / 2.0                     # each quarter of the S
    r2 = (FFC_TOP_Z - zb) / 2.0                     # the hairpin
    assert r1 >= FFC_R_MIN - 1e-9 and r2 >= FFC_R_MIN, (
        "the ribbon's bends are r %.2f and %.2f against a %.2f minimum" % (r1, r2, FFC_R_MIN))
    y_s = ym + out_                                 # end of the module's stiffener
    y_t = y_s + 2.0 * r1                            # start of the top run
    y_e = yb + out_                                 # start of our stiffener
    fixed = 2.0 * FFC_STIFF + math.pi * r1 + math.pi * r2
    # top run (y_c - y_t) + bottom run (y_c - y_e) is what the length has left
    y_c = (FFC_L - fixed + y_t + y_e) / 2.0
    assert y_c >= y_t and y_c >= y_e, (
        "the ribbon is too short for these mouths: its hairpin would be at y %.2f" % y_c)
    # THE FILM IS DRAWN MOUTH TO MOUTH: the FFC_INSERT at each end is the bared plug,
    # which ffc_plugs() draws inside the sockets' slots; it is counted in the length above
    yz = [(ym, zm), (y_s, zm)]
    yz += _arc(y_s, zm - r1, r1, 90, 0, 4)          # down...
    yz += _arc(y_s + 2.0 * r1, FFC_TOP_Z + r1, r1, 180, 270, 4)    # ...and level again
    yz += [(y_c, FFC_TOP_Z)]
    yz += _arc(y_c, FFC_TOP_Z - r2, r2, 90, -90, 10)               # the hairpin
    yz += [(y_e, zb), (yb, zb)]
    return [(x, y, z) for y, z in yz]


def ffc_ends():
    """[(mouth y, slot centre z, contact side), ...] the module's end, then ours. Both
    mouths face +Y, so at both a plug goes in heading -Y. The contacts face the module's
    board at its end (+Z) and ours at ours (-Z): a same-side cable that has turned over
    once, round the hairpin."""
    x, ym, zm = mod_ffc_mouth()
    return ((ym, zm, +1.0), (j1_mouth_y(), z_stack()[4] + J1_SLOT, -1.0))


def ffc_cable():
    """The display's ribbon film, one FFC_FILM_T prism along ffc_path(), mouth to mouth;
    it may not fold. Each end's bared FFC_INSERT -- its under-layer, since the over-layer
    is stripped there -- is added here; the copper and stiffeners are ffc_plugs()."""
    from cadkit.cables import flat_bends, flat_cable
    pts = ffc_path()
    folds = [b for b in flat_bends(pts, across=(1.0, 0.0, 0.0)) if b[1] == "fold"]
    assert not folds, "the display's ribbon folds: %r" % folds
    film = flat_cable(pts, FFC_W, FFC_FILM_T, across=(1.0, 0.0, 0.0))
    under = (-FFC_FILM_T / 2.0, -FFC_FILM_T / 2.0 + FFC_INS_T)
    for end in ffc_ends():
        film = film.union(_plug_layer(end, 0.0, FFC_INSERT, under))
    return film


def _plug_layer(end, y0, y1, u, x=None, w=FFC_W):
    """A box of the plug at `end` (an ffc_ends() row): from y0 to y1 into the socket
    from the mouth (negative = out of it, along the stiffener), u = (u0, u1) across the
    film from its centre, positive toward the contacts; w wide, centred on x."""
    ym, zs, n = end
    zf = zs + n * FFC_FILM_OFF
    za, zb = sorted((zf + n * u[0], zf + n * u[1]))
    cx = mod_ffc_mouth()[0] if x is None else x
    return box_at(w, y1 - y0, zb - za, x=cx, y=ym - (y0 + y1) / 2.0, z=(za + zb) / 2.0)


def ffc_contacts():
    """The bared conductors at both ends: FFC_INSERT of each of the 20, 0.65 wide at
    1.0, lying on the under-layer where the over-layer is stripped off."""
    cx = mod_ffc_mouth()[0]
    u = (-FFC_CU_T / 2.0, FFC_CU_T / 2.0)
    out = None
    for end in ffc_ends():
        for k in range(MOD_FFC_N):
            x = cx + (k - (MOD_FFC_N - 1) / 2.0) * MOD_FFC_PITCH
            b = _plug_layer(end, 0.0, FFC_INSERT, u, x=x, w=FFC_CU_W)
            out = b if out is None else out.union(b)
    return out


def ffc_stiffeners():
    """The two blue PET stiffeners, FFC_STIFF from each cut on the side away from the
    contacts: FFC_INSERT of each inside its socket, the rest in the air at the mouth."""
    u = (-FFC_FILM_T / 2.0 - FFC_STIFF_T, -FFC_FILM_T / 2.0)
    ends = ffc_ends()
    out = _plug_layer(ends[0], FFC_INSERT - FFC_STIFF, FFC_INSERT, u)
    return out.union(_plug_layer(ends[1], FFC_INSERT - FFC_STIFF, FFC_INSERT, u))


def ffc_slot(end):
    """The cutter for a socket's mouth: FFC_SLOT_H tall about the slot's centre, the
    plug's width and a little, FFC_INSERT + 0.2 deep."""
    ym, zs, _n = end
    d = FFC_INSERT + 0.2
    return box_at(FFC_W + 0.4, d + 0.2, FFC_SLOT_H,
                  x=mod_ffc_mouth()[0], y=ym - (d - 0.2) / 2.0, z=zs)


def screen():
    """The 128 x 64 of LIT AREA, as a face on the module's front.

    Drawn separately, and only because of how the assembly read without it: the module
    was one dark block 74.2 x 42.5, the deck's ledge covered its outer 4-5 mm all round
    -- which is the BEZEL doing its job -- and the picture said the panel was covering
    the screen. It never was. This is the rectangle that matters, in its own colour, so
    the question can be answered by looking."""
    return _screen_box().cut(screen_lit())


SCREEN_T = 0.2
# WHAT THE SCREEN SHOWS: the instrument's name, in the face the boards are lettered in.
# In that face a lower-case l is the capital L with two dots over its foot. A checkout
# without the font (it is licensed, and not in the repository) shows plain capitals.
SCREEN_WORD, SCREEN_WORD_PLAIN = "PUBlIC", "PUBLIC"
SCREEN_FILL = 0.75                 # of the lit area's width, and no more of its height


def _screen_box():
    mx, my = module_centre()
    face = z_stack()[2]
    return box_at(ACT_W, ACT_L, SCREEN_T, x=mx, y=my + VIEW_OFF_Y, z=face - SCREEN_T / 2.0)


@lru_cache(maxsize=1)
def screen_lit():
    """The dots that are ON: the name, centred, upright to the player (who sits at -Y).

    An OLED is black wherever it is not lit, so the lit dots are their own part, let
    into the screen's face, and the screen is what is left of the rectangle."""
    font = _bg()._FONT
    word, face = (SCREEN_WORD, {"fontPath": font}) if font else (SCREEN_WORD_PLAIN, {})

    def drawn(size):
        w = cq.Workplane("XY").text(word, size, SCREEN_T, **face)
        return w, w.val().BoundingBox()

    _w, b = drawn(10.0)
    size = 10.0 * min(SCREEN_FILL * ACT_W / b.xlen, SCREEN_FILL * ACT_L / b.ylen)
    w, b = drawn(size)
    c = _screen_box().val().BoundingBox()
    return w.translate(((c.xmin + c.xmax - b.xmin - b.xmax) / 2.0,
                        (c.ymin + c.ymax - b.ymin - b.ymax) / 2.0, c.zmin - b.zmin))


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
    collar_clears_deck()
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


def power_geometry():
    """(stem_z0, stem_top, cap_z0, cap_top) with the button OUT.

    THE CAP IS FLUSH WITH THE DECK WHEN IT IS ON (user, 2026-10-04): nothing stands proud
    of the playing surface while the instrument is in use. Off, it stands PWR_LOCK
    (1.5) proud, which is how you see it is off. To release it the cap has to go
    PWR_TRAVEL - PWR_LOCK (1.0) BELOW the deck, so the hole is a thumb's width -- that,
    and not the cap's looks, is the floor on PWR_CAP_D.
    """
    tz, _bz, _face, _back, board_top, _bb = z_stack()
    stem_z0 = board_top + PWR_BODY_H
    stem_top = stem_z0 + PWR_STEM_H
    cap_z0 = stem_top - PWR_STEM_GRIP
    assert cap_z0 - PWR_TRAVEL >= stem_z0 + 0.3, (
        "the power cap's skirt comes down to %.2f at full travel and the switch's case "
        "tops out at %.2f" % (cap_z0 - PWR_TRAVEL, stem_z0))
    return stem_z0, stem_top, cap_z0, tz + PWR_LOCK


def power_cap():
    """The printed button: a plain disc, pressed onto the switch's square stem and guided
    by its hole in the deck. Drawn OUT, which is off and the taller of its two states.

    It prints top face down with the socket opening upward. The socket bottoms on the
    stem's end, so a push goes through the cap's full thickness into the stem rather
    than through the press fit."""
    px, py = power_centre()
    _z0, stem_top, cap_z0, cap_top = power_geometry()
    s = cyl(PWR_CAP_D, cap_top - cap_z0, z=cap_z0)
    sq = PWR_STEM_SQ + 2 * KNOB_BORE_CLR
    s = s.cut(box_at(sq, sq, stem_top - cap_z0 + 0.1, x=0.0, y=0.0,
                     z=(stem_top + cap_z0 - 0.1) / 2.0))
    return s.translate((px, py, 0))


def power_stem():
    """The switch's stem above its case, drawn OUT. board_geom draws the 8.5 cube only."""
    px, py = power_centre()
    stem_z0, stem_top, _c0, _c1 = power_geometry()
    return box_at(PWR_STEM_SQ, PWR_STEM_SQ, stem_top - stem_z0,
                  x=px, y=py, z=(stem_z0 + stem_top) / 2.0)


# -- the deck ---------------------------------------------------------------
def deck_cutter():
    """Everything the UI takes out of its deck panel: the module's pocket, the window
    through the ledge over it, the knob's hole and the power button's."""
    tz, bz, face, _back, _bt, _bb = z_stack()
    mx, my = module_centre()
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
    px, py = power_centre()
    out = out.union(cyl(PWR_CAP_D + 2 * PWR_HOLE_CLR, tz - bz + 2.0, z=bz - 1.0)
                    .translate((px, py, 0)))
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
    # the wings' ground above and below each input (2026-10-30); the first two carry the
    # spigots
    return [SPIGOTS[0], SPIGOTS[1], THIRD_POST]


def bearings():
    """[(x, y)] every place the deck touches the board's top face: the four posts and the
    screw boss. The clamp plate bears on the whole underside against them, so the board
    is squeezed rather than bent."""
    return _posts() + [SCREW_XY]


def check_posts():
    """[complaint] -- a post under the display's pocket, or standing on a routed part.

    NOT an assertion, and not on the import path, for the same reason knob_centre()'s
    comparison is not: elec/ui_board.py imports this module, importing it builds the
    deck, and building the deck calls _posts(). An assertion there stops the generator
    from running the moment a part moves -- which is exactly when it has to run. This is
    called from elec/cad_geom_check.py, once the board it is checking against exists."""
    out = []
    half = POST_SQ / 2.0 + POST_CLR
    mx = board_local(module_centre()[0], 0.0)[0]
    edge = MOD_W / 2.0 + POCKET_CLR
    for px, py in bearings():
        if abs(px - mx) - half < edge:
            out.append("the post at (%+.1f, %+.1f) stands under the display's pocket, "
                       "+-%.2f of x %+.2f" % (px, py, edge, mx))
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
    """The cradle fused to the deck's underside: the posts, the spigots, the M4's boss and
    the keeper. There is no locating wall: the two spigots stand 100 apart, and they take
    X, Y and rotation between them."""
    _tz, bz, _face, _back, board_top, _bb = z_stack()
    cx, cy = board_centre()
    s = _keeper()
    for px, py in _posts():
        s = s.union(box_at(POST_SQ, POST_SQ, bz - board_top,
                           x=cx + px, y=cy + py, z=(bz + board_top) / 2.0))
    # ...and two of them carry on THROUGH the board as spigots, into the clamp plate.
    # These are what hold the station in X, Y and rotation; the M4 only holds Z.
    clamp_top, _clamp_bot = clamp_z()
    for px, py in SPIGOTS:
        s = s.union(cyl(SPIGOT_D, board_top - (clamp_top - SPIGOT_DEPTH),
                        z=clamp_top - SPIGOT_DEPTH).translate((cx + px, cy + py, 0)))
    # the screw boss: a column like the posts, its insert pocket bored UP from its own end
    # face -- which prints as a blind hole opening at the top. That face bears too.
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


def _keeper():
    """The column off the deck that takes the clamp's tongue. See KEEPER_Y."""
    bz = z_stack()[1]
    top, bot = clamp_z()
    cx, cy = board_centre()
    k1 = cx - BOARD_W / 2.0 - POST_CLR                      # its +X face, off the board
    run = CLAMP_T + 2 * KEEPER_CLR
    k0 = k1 - run - D.MIN_WALL_2P
    y = cy + KEEPER_Y
    z0 = bot - KEEPER_CLR - KEEPER_FLOOR
    s = box_at(k1 - k0, KEEPER_W + 2 * (KEEPER_CLR + D.MIN_WALL_2P), bz - z0,
               x=(k0 + k1) / 2.0, y=y, z=(bz + z0) / 2.0)
    zt, zf = top + KEEPER_CLR, bot - KEEPER_CLR
    tunnel = (cq.Workplane("XZ", origin=(0, y + KEEPER_W / 2.0 + KEEPER_CLR, 0))
              .polyline([(k1 + 1.0, zt), (k1 + 1.0, zf), (k1, zf), (k1 - run, zt)]).close()
              .extrude(KEEPER_W + 2 * KEEPER_CLR))
    return s.cut(tunnel)


def _tongue():
    """The clamp plate's -X tongue: its underside the keeper's 45 degree floor, KEEPER_CLR
    off it, and its tip blunted to one bead of thickness."""
    top, bot = clamp_z()
    cx, cy = board_centre()
    x1 = cx - BOARD_W / 2.0 + 1.0                           # in the plate
    k1 = cx - BOARD_W / 2.0 - POST_CLR
    xs = k1 + KEEPER_CLR * math.sqrt(2.0)                   # where the chamfer starts
    tip = xs - (CLAMP_T - D.MIN_WALL)
    return (cq.Workplane("XZ", origin=(0, cy + KEEPER_Y + KEEPER_W / 2.0, 0))
            .polyline([(x1, top), (x1, bot), (xs, bot), (tip, top - D.MIN_WALL), (tip, top)])
            .close().extrude(KEEPER_W))


def clamp():
    """THE CLAMP PLATE: what actually holds the station in (user, 2026-09-28).

    A printed plate against the board's underside. Its -X tongue hooks into the deck's
    keeper and one M4 pulls its +X end up into the deck's boss:

      * it SQUEEZES the board. Its whole top face bears against the deck's bearings.
      * it HOLDS THE SCREEN. Four columns press the module's PCB up into the window ledge,
        one at each mounting hole: the far two off the plate past the board's +Y edge, the
        near two off a bar past its -Y edge.
      * and it is the ONE PART you undo.

    A RELIEF UNDER THE THROUGH-HOLE FOOTPRINTS ONLY, from board_geom.TAIL. Relieving
    every footprint was tried and is worse: the 0402s do not need it, and two of their
    reliefs left a 1.38 mm web between them -- under the two-bead floor.

    THE COLUMNS BEAR ON THE MOUNTING-HOLE PADS, x +-36.70 on both hole rows, because that
    is the one region of a module's back guaranteed to be clear of components. CONFIRM IT
    against the real part before printing: Newhaven's rear view shows parts, and their
    drawing does not dimension them."""
    cx, cy = board_centre()
    top, bot = clamp_z()
    pcb_back = mod_pcb_back()
    mx, _my = module_centre()
    far_y = header_row_y() + MOD_HOLE_DY
    near_y = header_row_y()
    from . import chassis as CH
    bar_x = 2 * MOD_HOLE_DX + CLAMP_RIB_W
    # ...THE NEAR BAR RAMPS UP OVER THE CABLE TROUGH. The panel is slid on and off with the
    # whole station bolted to it, and the trough's lip runs the length of the rail, its top
    # above the plate's underside. So the plate stops short and a 45 degree face, which
    # prints, carries the bar over the lip with 1.0 of air.
    lip_y = CH.WT_Y0 + CH.WT_D
    lip_z = CH.WT_ZF + CH.WT_H
    y0 = lip_y + (lip_z + 1.0 - bot)
    y1 = far_y + CLAMP_RIB_W / 2.0
    s = box_at(BOARD_W, BOARD_L, CLAMP_T, x=cx, y=cy, z=(top + bot) / 2.0)
    s = s.union(box_at(bar_x, y1 - y0, CLAMP_T, x=mx, y=(y0 + y1) / 2.0, z=(top + bot) / 2.0))
    ym = near_y - CLAMP_TIP_D / 2.0                 # 1.0 off the rail's inner face
    assert ym < lip_y and bot + (y0 - ym) < CLAMP_ARM_Z, (
        "the near bar's ramp runs out at y %.2f" % ym)
    s = s.union(cq.Workplane("YZ", origin=(mx - bar_x / 2.0, 0, 0))
                .polyline([(y0 + 2.0, bot), (y0, bot), (ym, bot + (y0 - ym)),
                           (ym, CLAMP_ARM_Z), (y0 + 2.0, CLAMP_ARM_Z)])
                .close().extrude(bar_x))
    s = s.union(_tongue())
    for _ref, (x0, x1, fy0, fy1), tail in _bg().tails("ui_board"):
        if tail <= 0.0:
            continue
        s = s.cut(box_at(x1 - x0 + 2 * CLAMP_RELIEF, fy1 - fy0 + 2 * CLAMP_RELIEF,
                         CLAMP_T + 2.0, x=cx + (x0 + x1) / 2.0, y=cy + (fy0 + fy1) / 2.0,
                         z=(top + bot) / 2.0))
    bz = z_stack()[1]
    for sx in (-1, 1):
        for yc, z0 in ((far_y, bot), (near_y, CLAMP_ARM_Z - 1.0)):
            s = s.union(cyl(CLAMP_TIP_D, pcb_back - z0, z=z0)
                        .translate((mx + sx * MOD_HOLE_DX, yc, 0)))
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
    return ([("ui_pcb", ui_pcb()), ("ui_display", display_module()),
             ("ui_disp_ffc_socket", module_ffc_socket()), ("ui_ffc", ffc_cable()),
             ("ui_ffc_contacts", ffc_contacts()), ("ui_ffc_stiffener", ffc_stiffeners()),
             ("ui_screen", screen()), ("ui_screen_lit", screen_lit()), ("ui_clamp", clamp()),
             ("ui_shaft", encoder_shaft()), ("ui_knob", knob()),
             ("ui_pwr_stem", power_stem()), ("ui_pwr_cap", power_cap())]
            + [(n, w) for n, w in (("ui_pcb_silk", ui_silk()),) if w is not None]
            + hardware())
