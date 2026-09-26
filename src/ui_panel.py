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

# -- THE ENCODER, off Alps' RKJXT1F series drawing (read 2026-09-25) ---------
ENC_SQ       = 17.0                # body, W x D
ENC_BODY_H   = 10.5                # body above the PCB (the catalogue's H)
ENC_TAIL     = 3.2                 # terminals below the PCB
ENC_TOTAL    = 17.4                # shaft tip to terminal tips
ENC_SHAFT_H  = ENC_TOTAL - ENC_TAIL - ENC_BODY_H     # 3.7 of shaft above the body
ENC_SHAFT_D  = 2.5
ENC_SHAFT_GRIP = 1.8               # the O2.5 length a cap can grip
ENC_FULCRUM  = 5.55                # lever pivot above the PCB
ENC_TILT     = 9.0                 # degrees, each direction

# -- THE PRINTED CAP --------------------------------------------------------
# O17 to match the body, because that is the width the Y spacing is measured on: what
# the player sees is the cap, not the switch under it.
KNOB_D       = ENC_SQ              # 17.0
KNOB_SHANK_D = 8.0                 # what passes through the deck
KNOB_CLR     = 0.5                 # air under the cap at rest
KNOB_H       = 4 * D.BEAD          # 3.2 of cap above its own underside
# THE CAP PRINTS DISC-DOWN, on the flat top face it presents to the player. Every other
# way up puts the O2.6 shaft bore's blind end over air. Its own +Z is the world's, so
# the declaration is the world axis turned over.
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
SCREW_XY = (-15.5, -2.5)           # the one M4, in board coordinates
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
    board_top = mod_back - SOCKET_H
    return (TP.TZ, TP.BZ, mod_face, mod_back, board_top, board_top - BOARD_T)


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
    lip. That is fine standing still and is not enough to slide 400 mm over -- so THE
    UI BOARD COMES OFF BEFORE THE DECK STACK IS WITHDRAWN. One M4 from underneath,
    which is a screw you are taking out to reach the display anyway. Everything else
    on the panel stops at the board's top face or clear of the trough in Y, so the
    panel alone slides free (deck_mount's own assertion holds it to that)."""
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
    """(shaft_tip_z, cap_z0, hole_d) -- the three numbers the cap and its hole share.

    THE HOLE IS SIZED BY THE TILT, NOT BY THE SHANK. The stick pivots 9 deg about a
    fulcrum 5.55 above the board, so the shank sweeps a cone: what has to fit through
    the deck is the shank's diameter plus twice its throw at the deck's TOP face, which
    is the furthest point from the pivot. And the cap has to start high enough that its
    low side still clears the deck when the stick is over -- it dips half its own
    diameter times sin(tilt)."""
    tz, _bz, _face, _back, board_top, _bb = z_stack()
    tip = board_top + ENC_TOTAL - ENC_TAIL
    pivot = board_top + ENC_FULCRUM
    t = math.tan(math.radians(ENC_TILT))
    hole_d = KNOB_SHANK_D + 2.0 * ((tz - pivot) * t + 0.4)
    cap_z0 = tz + KNOB_D / 2.0 * math.sin(math.radians(ENC_TILT)) + KNOB_CLR
    return tip, cap_z0, hole_d


def knob():
    """The printed cap: a shank up through the deck and a O17 disc over it."""
    kx, ky = routed("SW1")
    tip, cap_z0, _hole = knob_geometry()
    z0 = tip - ENC_SHAFT_GRIP
    s = cyl(KNOB_SHANK_D, cap_z0 - z0, z=z0).translate((kx, ky, 0))
    s = s.union(cyl(KNOB_D, KNOB_H, z=cap_z0).translate((kx, ky, 0)))
    return s.cut(cyl(ENC_SHAFT_D + 0.2, ENC_SHAFT_GRIP + 0.1, z=z0 - 0.05)
                 .translate((kx, ky, 0)))


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
    kx, ky = routed("SW1")
    out = out.union(cyl(knob_geometry()[2], tz - bz + 2.0, z=bz - 1.0)
                    .translate((kx, ky, 0)))
    return out


def _posts():
    """[(x, y)] in BOARD coordinates of the four columns the board is pulled up onto.

    COLUMNS, NOT LEDGES, and the print decides it: the deck prints face-DOWN
    (top_plate.PIECE_UP), so everything under it grows away from the bed and a shelf
    poking inward off a wall would be a ceiling with nothing beneath it. A column from
    the deck's own underside is supported the whole way.

    The four are placed in the gaps the routed board leaves: none may stand under the
    display module (which reaches down to 0.7 below the deck), so all four sit -Y of
    the module's edge, and none may land on a part."""
    return [(30.0, 9.0), (30.0, -12.0), (0.0, 8.0), (-19.0, 8.0)]


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
            ("ui_knob", knob())] + hardware()
