"""THE NEW INSTRUMENT'S BOARDS IN PLACE -- a VIEW of the direct-drive instrument (src.direct_bench)
with the routed brain and output boards where the 2026-11-12 plan and their placement intents put
them. Not a fit study: no overlap gate, and the positions are the intents' frames, not a mount.

  * brain (320 x 70): on its side, -Y of the motors, component side facing -Y (away from the
    motors, JSTs mouth-up). Board X = instrument X + 360, board Y = instrument Z.
  * output_signal (68 x 100): stood in the XZ plane in the +X -Y box beside the endplate,
    component side facing -Y. Board X = instrument X, board Y = instrument Z.
  * output_power (68 x 72): 15 mm further -Y, FACING output_signal, its centre 14 mm lower.
    Board X = -instrument X, board Y = instrument Z.
  * the optical board is NOT drawn: it is being redesigned (user 2026-11-13: no forwarder MCU,
    a ribbon to the output board).

The geometry is whatever elec/geom/<board>.geom.json holds -- the latest finished trial.

    view: agent_sync.py scope --set src.new_boards_view --attr assembly; py -3.12 -m tools.scratch_view
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
    "TDSON-8-1": 1.10,                       # brain part_heights Q8/Q9
    "Texas_PWP0020A": 1.20,                  # HTSSOP-20, TI PWP0020A outline: 1.2 max
    "QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm": 1.0,   # ESTIMATED, a 4 x 4 QFN's usual 1.0 max
    "JST_XH_S6B-XH-SM4-TB_1x06-1MP_P2.50mm_Horizontal": 6.0,   # JST eXH p.6, as its 4-way sibling
    # the board-to-board pair: ESTIMATED so the mated stack spans the 15 mm between the boards
    "PinHeader_2x12_P1.27mm_Vertical_SMD": 7.0,
    "PinSocket_2x12_P1.27mm_Vertical_SMD": 8.0,
}

BOARDS = Boards(BG.GEOM_DIR, height={**BG.HEIGHT, **VIEW_HEIGHT}, tail=BG.TAIL,
                tht_legs=BG.THT_LEGS, panel=BG.PANEL)

GAP = 15.0                    # output_signal to output_power, board to board
SIG_Y = -66.0                 # output_signal's back face: just -Y of the motors' -64
SIG_X, SIG_Z = -56.0, -58.0   # its centre: inside the endplate (x -20), bottom on z -108
PWR_Z = SIG_Z - 14.0
BRAIN_Y, BRAIN_DX, BRAIN_Z = -66.0, -360.0, -71.0


def _fab_refs(board):
    return [f["ref"] for f in BOARDS.load(board)["footprints"] if f["fab"]]


@lru_cache(maxsize=None)
def _parts(board):
    """(laminate, parts) of `board` in its own frame: laminate z 0 .. t, parts above."""
    return BOARDS.plate(board), BOARDS.bodies(board, _fab_refs(board))


def _facing_minus_y(w, x, y, z):
    """Own frame -> instrument, component side toward -Y: board y -> Z, board z -> -Y."""
    return w.rotate((0, 0, 0), (1, 0, 0), 90).translate((x, y, z))


def _facing_plus_y_mirrored(w, x, y, z):
    """Own frame -> instrument, component side toward +Y and board X = -instrument X."""
    return (w.rotate((0, 0, 0), (1, 0, 0), -90).rotate((0, 0, 0), (0, 1, 0), 180)
            .translate((x, y, z)))


def boards() -> list:
    out = []
    t = BOARDS.load("output_power")["thickness_mm"]
    place = (
        ("brain", _facing_minus_y, (BRAIN_DX, BRAIN_Y, BRAIN_Z)),
        ("output_signal", _facing_minus_y, (SIG_X, SIG_Y, SIG_Z)),
        # its back face GAP + two laminates further -Y, its parts toward output_signal
        ("output_power", _facing_plus_y_mirrored, (SIG_X, SIG_Y - 2 * t - GAP, PWR_Z)),
    )
    from cadkit.web.finishes import made_of
    for b, pose, at in place:
        plate, parts = _parts(b)
        # this module's own names; tools.web_materials' general pcb rule answers both
        out.append(("%s_pcb" % b, made_of(pose(plate, *at), "board")))
        out.append(("%s_pcb_parts" % b, made_of(pose(parts, *at), "nylon")))
    return out


def assembly() -> list:
    from . import direct_bench as DB
    return DB.assembly() + boards()
