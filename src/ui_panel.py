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

-- GETTING IT OUT AGAIN (user, 2026-09-28) -----------------------------------
ONE M4 RELEASES BOTH THE SCREEN AND THE BOARD, and plastic takes every other direction.
The display is caught in X and Y by its pocket walls and in +Z by the window ledge; the
board is caught in X and Y by the cradle's wall and in +Z by its four columns. Neither
is caught in -Z by plastic at all, because -Z is the installation direction -- and that
one direction is the M4's whole job. The display's own -Z stop is the board's header,
which is why the screw covers both: the two are plugged together into one assembly, and
one screw is all that holds that assembly in the panel.

...AND IT DROPS STRAIGHT OUT INTO THE BAY. Under the whole 82 x 47.5 footprint there is
nothing between the panel and the chassis floor at z -71.5: 57.5 mm of clear air,
measured across the station's whole plan. So undoing the one screw lets the assembly --
screen, board and all -- come down about 20 mm onto that floor, where its highest point
sits some 39 mm below the lowest thing hanging off any deck panel. Reach in, unplug the
ribbon, and every panel slides out over it; the assembly lifts out from above once they
are gone. It cannot come out THROUGH the deck: the module is 82 x 47.5 and the window is
66 x 33.

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
# ...AND THE STACK IS DELIBERATELY 0.3 TOO LONG. The module is trapped between the deck's
# window ledge above it and the header below, with nothing else holding it down, so an
# exact fit is a coin toss between a rattle and a preload. Making the header stand 0.3
# proud settles it: the module always seats UP against the ledge, the pins give up 0.3 of
# their 6.0 engagement, and nothing can buzz against a printed face under an instrument
# that gets stomped on.
MOD_PRELOAD = 0.3
# THE ONE M4, in board coordinates. It sits in the +Y half on purpose, twice over:
# it is nearer the display's overhang, which is where the assembly's weight is, and it
# leaves the whole -Y half of the board as one uninterrupted lane. Down in the -Y half
# its O4.5 clearance hole stood in the middle of the only route the seven switch nets
# have from the encoder to the ribbon header, and the router left two of them short.
SCREW_XY = (-15.5, 4.0)
SCREW_CLR_D = 4.5                  # its clearance hole in the board

# -- THE DECK ---------------------------------------------------------------
LEDGE_T    = D.MIN_WALL_2P         # 1.6 of deck left over the module = the bezel
POCKET_CLR = 0.3                   # slip fit round the module
EDGE_WALL  = D.MIN_WALL_2P         # 1.6 from the pocket to the panel's +X seam
POST_SQ    = 5.0                   # the board's corner posts
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
    return pcb.union(bezel)


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
    # the window: the BEZEL OPENING, which is what limits the view -- anything wider
    # only thins the ledge, and anything narrower crops the panel
    out = out.union(box_at(OPEN_W, OPEN_L, tz - face + 2.0,
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

    The four are placed in the gaps the routed board leaves; check_posts() below is what
    says so, and it runs AFTER the route rather than here. A post on a part does reach
    the overlap gate -- it caught two of these at 0.8 mm3 when the pull-ups moved into a
    row -- but as an anonymous solid-on-solid finding, and what you want to be told is
    WHICH post and WHICH part."""
    return [(11.0, 6.0), (11.0, -13.5), (-6.0, -13.0), (-6.0, 6.0)]


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
    for px, py in _posts():
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
    # the screw boss: a column like the others, with the insert pocket bored UP into it
    # from its own end face -- which prints as a blind hole opening at the top
    bx, by = cx + SCREW_XY[0], cy + SCREW_XY[1]
    s = s.union(cyl(M4.insert_pilot_d + 2 * D.MIN_WALL_2P, bz - board_top, z=board_top)
                .translate((bx, by, 0)))
    return cut_insert_bore(
        M4, s, (bx, by, board_top), (0, 0, 1),
        M4.screw_l - M4.insert_l + BOARD_T + 1.0,
        reason="the deck's only UI fastener: a self-tapped M4 in PCTG would strip the "
               "first time the board came off for service, and it comes off for every "
               "display swap",
        print_up=_tp().PIECE_UP)


def hardware():
    """[(name, solid)] the M4 that holds the board up, and its insert."""
    _tz, _bz, _face, _back, board_top, board_bot = z_stack()
    cx, cy = board_centre()
    bx, by = cx + SCREW_XY[0], cy + SCREW_XY[1]
    # THE SCREW GOES IN FROM UNDERNEATH, so the dummy is turned over: cadkit draws it
    # head-top at z=0 with the shank running -Z, and here the head is the low end and
    # the shank climbs through the board into the boss.
    screw = (m4_button_screw(M4.screw_l).rotate((0, 0, 0), (1, 0, 0), 180)
             .translate((bx, by, board_bot - M4_BUTTON_HEAD_H)))
    return [("ui_screw", screw),
            ("ui_insert", seated_insert(M4, (bx, by, board_top), (0, 0, 1)))]


def parts():
    """[(name, solid)] everything the assembly shows for the UI station."""
    return [("ui_pcb", ui_pcb()), ("ui_display", display_module()),
            ("ui_shaft", encoder_shaft()), ("ui_knob", knob())] + hardware()
