"""THE NEW INSTRUMENT'S BOARDS IN PLACE -- a VIEW of the direct-drive instrument (src.direct_bench)
with the routed brain and output boards where their frames put them. Not a fit study: no overlap
gate, and the positions are the intents' frames, not a mount.

  * brain (320 x 70): on its side, -Y of the motors, component side facing -Y (away from the
    motors, JSTs mouth-up). Board X = instrument X + 360, board Y = instrument Z. (To move: user
    2026-11-13, flat in the -X +Y corner -- not drawn there until it is re-placed.)
  * output_board (120.3 x 100, ONE board, drops in -Z then slides +X 19 into a pocket fitted to it in the +X endplate: user 2026-11-13): back face on the
    -Y side at y -87.5 (branner: +1.7 so unclipped 3.4 tails clear the wall at -91.7), parts facing +Y; board x = -(instrument x + 59.72), board y =
    instrument z + 58.24 (x -119.87 .. 0.43). The panel (board -X edge) sits 1.6 behind the outer face (USB inset 1.6, J5 2.4 back on the board); parts in the pocket: elec/output_board.pocket.json.
  * the optical board is NOT drawn: it is being redesigned (user 2026-11-13: no forwarder MCU,
    a ribbon to the output board).

The geometry is elec/geom/<board>.geom.json: bronner exports the CHOSEN trial into it (cadkit
kicad_geom.py --out), since trial runs all write there. Each board's solids are KEPT (cadkit.kept,
keyed on that file): a render rebuilds only a board whose geometry changed.

    view: agent_sync.py scope --set src.new_boards_view --attr assembly; agent_sync.py view --solo
"""
from __future__ import annotations

from functools import lru_cache

from cadkit.board_geom import Boards

from . import board_geom as BG

# Footprints these three boards use that the project's HEIGHT table does not have yet. VIEW ONLY,
# kept out of board_geom.HEIGHT on purpose (lead, 2026-11-13: placement heights live in each
# board's part_heights); each from the part's drawing where one was read, else marked.
VIEW_HEIGHT = {
    "CP_Elec_10x10.5": 13.0,                 # brain C113/C114 polymer, part_heights 13.0
    "D_SOD-323": 1.10,                       # brain part_heights D13
    "Hirose_DF40C-100DS-0.4V_2x50_P0.4mm": 1.5,   # the CM5 mezzanine's mated stack (CM5 datasheet)
    "L_Bourns_SRP1770TA_16.9x16.9mm": 7.0,   # brain part_heights L4
    "PinHeader_2x08_P1.27mm_Vertical": 5.3,  # brain part_heights J5 (HX PZ1.27-2x8P ZZ)
    "PinHeader_2x10_P1.27mm_Vertical_SMD": 5.3,   # output_board J4 PZ1.27-2x10P: AS its 2x8 sibling
    "TDSON-8-1": 1.10,                       # brain part_heights Q8/Q9
    "Texas_PWP0020A": 1.20,                  # HTSSOP-20, TI PWP0020A outline: 1.2 max
    "QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm": 1.0,   # ESTIMATED, a 4 x 4 QFN's usual 1.0 max
    "JST_XH_S6B-XH-SM4-TB_1x06-1MP_P2.50mm_Horizontal": 6.0,   # JST eXH p.6, as its 4-way sibling
    # the board-to-board pair: ESTIMATED so the mated stack spans the 15 mm between the boards
    "PinHeader_2x12_P1.27mm_Vertical_SMD": 7.0,
    "PinSocket_2x12_P1.27mm_Vertical_SMD": 8.0,
}

# built EXACTLY as src.board_geom.BOARDS (silk font, revisions), heights extended: the web export
# finds a board by its lettering drawn by THAT instance, so a different font is a different board
BOARDS = BG._with_revs(Boards(BG.GEOM_DIR, height={**BG.HEIGHT, **VIEW_HEIGHT}, tail=BG.TAIL,
                              tht_legs=BG.THT_LEGS, panel=BG.PANEL,
                              **({"silk_font": BG._FONT, "silk_cap": BG.SILK_FONT_CAP}
                                 if BG._FONT else {})))

BRAIN_Y, BRAIN_DX, BRAIN_Z = -66.0, -360.0, -71.0
OB_X, OB_BACK_Y, OB_Z = -74.985, -87.5, -58.24     # output_board (= brain) centre, FINAL (x -150.4..0.43, 150.83 wide), back face (branner)


def _build(board):
    """(board, lettering) of `board` in its own frame, as the shipped boards are drawn: ONE
    solid (laminate + every part, BOARDS.solid) and its silkscreen (BOARDS.ink). The web
    export finds the board by its lettering and swaps the boxes for KiCad's coloured models
    (cadkit.web.boards), so the two must be posed alike and the parts must not be split off."""
    return BOARDS.solid(board, skip=SKIP.get(board, ())), BOARDS.ink(board)


# parts the project draws as THE PART, not a box (as output_panel's J8 is: src/screw_terminal.py,
# the slotted MX128 -- one flat blade for it and the motors' terminals)
SKIP = {"output_board": ("J8",)}


@lru_cache(maxsize=None)
def _parts(board):
    # kept: keyed on the code and the geom.json it opens, so an unchanged board is a read
    from cadkit.kept import kept
    return tuple(kept(_build, board))


def _facing_minus_y(w, x, y, z):
    """Own frame -> instrument, component side toward -Y: board y -> Z, board z -> -Y."""
    return w.rotate((0, 0, 0), (1, 0, 0), 90).translate((x, y, z))


def _facing_plus_y_mirrored(w, x, y, z):
    """Own frame -> instrument, component side toward +Y and board X = -instrument X."""
    return (w.rotate((0, 0, 0), (1, 0, 0), -90).rotate((0, 0, 0), (0, 1, 0), 180)
            .translate((x, y, z)))


def boards() -> list:
    out = []
    place = (
        ("brain", _facing_minus_y, (BRAIN_DX, BRAIN_Y, BRAIN_Z)),
        # board -X = instrument +X, parts toward +Y: (x, y, z) -> (-x, z, y)
        ("output_board", _facing_plus_y_mirrored, (OB_X, OB_BACK_Y, OB_Z)),
    )
    from cadkit.web.finishes import made_of
    for b, pose, at in place:
        solid, ink = _parts(b)
        out.append(("%s_pcb" % b, made_of(pose(solid, *at), "board")))
        if ink is not None:
            out.append(("%s_pcb_silk" % b, made_of(pose(ink, *at), "ink")))
        if "J8" in SKIP.get(b, ()):
            from . import screw_terminal as ST
            for k, v in ST.parts(b, "J8").items():
                out.append(("%s_term%s" % (b, "" if k == "housing" else "_metal"), pose(v, *at)))
    return out


def assembly() -> list:
    from . import direct_bench as DB
    return DB.assembly() + boards()
