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

import cadquery as cq

from cadkit.board_geom import Boards

from . import board_geom as BG

# Footprints these three boards use that the project's HEIGHT table does not have yet. VIEW ONLY,
# kept out of board_geom.HEIGHT on purpose (lead, 2026-11-13: placement heights live in each
# board's part_heights); each from the part's drawing where one was read, else marked.
VIEW_HEIGHT = {
    "CP_Elec_10x10.5": 13.0,                 # brain C113/C114 polymer, part_heights 13.0
    "D_SOD-323": 1.10,                       # brain part_heights D13
    # the CM5 mezzanine's RECEPTACLE (ours): the 1.5 mated stack (CM5 datasheet) is drawn as two
    # halves, this and the CM5's plug (_cm5) -- the 1.0 / 0.5 split ESTIMATED, not off Hirose's print
    "Hirose_DF40C-100DS-0.4V_2x50_P0.4mm": 1.0,
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
    # the connector board's (2026-11-14)
    "PinHeader_2x15_P1.27mm_Vertical_SMD": 5.3,   # J1 PZ1.27-2x15P: AS its 2x8 / 2x10 siblings
    "JST_PH_B4B-PH-SM4-TB_1x04-1MP_P2.00mm_Vertical": 5.5,   # AS cadkit's PH side-entry (PH_SIDE_H); mated -> ph_mated_h
    "C_2220_5750Metric": 2.5,                # ESTIMATED: a 22 uF / 50 V 2220's usual 2.5 max
    # output_board parts with no height in the project table (the view raised KeyError
    # at HEAD, 2026-11-14; geom = the mL2 trial): from the drawings where read
    "L_CommonModeChoke_Coilank_ACM2012": 1.3,     # TDK ACM2012: 2.0 x 1.2 x 1.3
    "Converter_DCDC_Murata_MEE1SxxxxSC_THT": 10.0,   # U30 B0509S-1WR3: 11.50 x 6.0 x 10.0 (Mornsun)
    "L_CommonModeChoke_Wuerth_WE-SL5-HC": 5.0,    # ESTIMATED: Wurth's PDF refused the fetch -- read it
    "Fuse_2920_7451Metric": 2.0,             # F204 2920L200/60GR: ESTIMATED (conservative) -- read Littelfuse's drawing
    "L_Changjiang_FXL0630": 3.0,             # L1: the series' 0630 = 6.6 x 7.0 x 3.0
    "TerminalBlock_Phoenix_PT-1,5-2-3.5-H_1x02_P3.50mm_Horizontal": 8.5,   # J8: ESTIMATED, a 3.5 mm PT's usual body
}

# built EXACTLY as src.board_geom.BOARDS (silk font, revisions), heights extended: the web export
# finds a board by its lettering drawn by THAT instance, so a different font is a different board
BOARDS = BG._with_revs(Boards(BG.GEOM_DIR, height={**BG.HEIGHT, **VIEW_HEIGHT}, tail=BG.TAIL,
                              tht_legs=BG.THT_LEGS, panel=BG.PANEL, side_plug_run=BG.SIDE_PLUG_RUN,
                              body_material=BG.BODY_MATERIAL,
                              **({"silk_font": BG._FONT, "silk_cap": BG.SILK_FONT_CAP}
                                 if BG._FONT else {})))

BRAIN_Y, BRAIN_DX, BRAIN_Z = -66.0, -360.0, -71.0
# connector_board: FLAT ON THE FLOOR, component side up (+Z), its own frame's centre at
# instrument (-572.175, -9.55) PROPOSED 11-15 (three rows, user), underside z -107.2 (notes "frame", branner
# 11-13). Drawn MATED: J11-J20's plugs (side_plug_run) and the PH / XH housings, what the
# nut block, the endplates and the cable path have to clear.
CB_X, CB_Y, CB_Z = -572.175, -9.55, -102.2
OB_X, OB_BACK_Y, OB_Z = -74.985, -87.5, -58.24     # output_board (= brain) centre, FINAL (x -150.4..0.43, 150.83 wide), back face (branner)


def _build(board):
    """(board, lettering) of `board` in its own frame, as the shipped boards are drawn: ONE
    solid (laminate + every part, BOARDS.solid) and its silkscreen (BOARDS.ink). The web
    export finds the board by its lettering and swaps the boxes for KiCad's coloured models
    (cadkit.web.boards), so the two must be posed alike and the parts must not be split off."""
    return (BOARDS.solid(board, skip=SKIP.get(board, ()), mated=board in MATED),
            BOARDS.ink(board))


# parts the project draws as THE PART, not a box (as output_panel's J8 is: src/screw_terminal.py,
# the slotted MX128 -- one flat blade for it and the motors' terminals)
# output_board's J8 is a 3.5 mm terminal now (screw_terminal draws the 5.00-pitch MX128 and
# asserts it): drawn as its box until screw_terminal learns the part (2026-11-14)
SKIP = {}
# boards drawn with their plugs in (BOARDS.solid(mated=True)): NONE. This is a view, not a fit
# study, and a mated solid carries each side-entry plug's RUN as a bare box (SIDE_PLUG_RUN)
# that no model replaces -- J11-J20 showed as big boxes in front of the screw terminals
# (user, 2026-11-14: "that shouldn't appear in the render"). The JST crimp housings are drawn
# by the web export from its own plug models either way.
MATED = set()


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


def _flat_up(w, x, y, z):
    """Own frame -> instrument, component side up: a translation."""
    return w.translate((x, y, z))


def _cm5(t):
    """(module, soc) in the output board's own frame: the Compute Module 5 on its two DF40s.

    Holes and outline from elec/cm5_mech.py (Raspberry Pi's CM5IO carrier); the 1.5 mm stack,
    the 1.24 module PCB and the 2.2 SoC (4.94 mounted height) from RP-008180-DS-7 4.1.1; the
    SoC's centre from Fig. 4 (31.99 from the pin-99 edge, 16.98 from the pin-200 edge -- the
    module's +Y edge is its pin-1 end, its +X edge the pin-101 row). The SoC is drawn 15 x 15
    (scaled off Fig. 4): a stand-in, not a datasheet dimension."""
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "elec"))
    import cm5_mech as CM5
    x0, y0, x1, y1 = CM5.outline()
    z0 = t + CM5.STANDOFF_H
    mod = (cq.Workplane("XY").box(x1 - x0, y1 - y0, CM5.MODULE_PCB_T, centered=False)
           .edges("|Z").fillet(3.0).translate((x0, y0, z0)))
    for hx, hy in CM5.holes():
        mod = mod.cut(cq.Workplane("XY").circle(CM5.HOLE_D / 2).extrude(5.0).translate((hx, hy, z0 - 1.0)))
    sx, sy, ss, sh = x1 - 16.975, y0 + 31.9875, 15.0, 2.2
    soc = cq.Workplane("XY").box(ss, ss, sh).translate((sx, sy, z0 + CM5.MODULE_PCB_T + sh / 2))
    # HOW IT PLUGS IN (user, 2026-11-14: "how does the CM5 attach ... I don't see pins"): no
    # pins -- two 100-way 0.4 mm Hirose DF40 mezzanines under the module, J201 / J202 on our
    # side. Each is drawn as the pair it is: our receptacle (the footprint body, VIEW_HEIGHT 1.0),
    # the CM5's plug hanging from the module's underside to meet it (1.5 stack), and a gold
    # lead on each of the 200 pads, past the receptacle's body, where the solder joints are.
    plug = leads = None
    for ref in ("J201", "J202"):
        f = BG.footprint("output_board", ref)
        fx0, fx1, fy0, fy1 = f["fab"]
        cx, cy = (fx0 + fx1) / 2.0, (fy0 + fy1) / 2.0
        w, l = (fx1 - fx0) - 0.6, (fy1 - fy0) - 0.6          # the plug inside the receptacle's walls
        hp = CM5.STANDOFF_H - VIEW_HEIGHT[f["fpid"].split(":")[-1]]
        pb = cq.Workplane("XY").box(w, l, hp).translate((cx, cy, z0 - hp / 2.0))
        plug = pb if plug is None else plug.union(pb)
        pts = []
        for x, y in f["pads"].values():
            s = 1.0 if x > cx else -1.0
            pts.append((x + s * 0.2, y))                       # the pad's outer half, past the body
        ld = (cq.Workplane("XY").pushPoints(pts).rect(0.35, 0.2).extrude(0.12).translate((0, 0, t)))
        leads = ld if leads is None else leads.union(ld)
    return mod, soc, plug, leads


def boards() -> list:
    out = []
    place = (
        # the 320 x 70 brain is NOT drawn: the output board is the brain now (2026-11-13), and
        # the old board read as a second connector board in the view (user, 2026-11-14)
        # board -X = instrument +X, parts toward +Y: (x, y, z) -> (-x, z, y)
        ("output_board", _facing_plus_y_mirrored, (OB_X, OB_BACK_Y, OB_Z)),
        ("connector_board", _flat_up, (CB_X, CB_Y, CB_Z)),
    )
    from cadkit.web.finishes import made_of
    for b, pose, at in place:
        solid, ink = _parts(b)
        out.append(("%s_pcb" % b, made_of(pose(solid, *at), "board")))
        if ink is not None:
            out.append(("%s_pcb_silk" % b, made_of(pose(ink, *at), "ink")))
        if b == "output_board":
            import json as _json
            import os as _os
            _g = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                               "elec", "geom", "output_board.geom.json")
            mod, soc, plug, leads = _cm5(_json.load(open(_g))["thickness_mm"])
            out.append(("output_board_cm5", made_of(pose(mod, *at), "board")))
            out.append(("output_board_cm5_soc", made_of(pose(soc, *at), "polished")))
            out.append(("output_board_cm5_plug", made_of(pose(plug, *at), "nylon")))
            out.append(("output_board_df40_leads", made_of(pose(leads, *at), "gold")))
        # the ribbon headers' IDC sockets and a stub of each ribbon (src/ribbon_socket.py)
        from . import ribbon_socket as RS
        rs = RS.parts(b)
        if rs:
            out.append(("%s_idc" % b, made_of(pose(rs["socket"], *at), "nylon")))
            out.append(("%s_idc_ribbon" % b, made_of(pose(rs["ribbon"], *at), "pvc")))
        if b == "connector_board":
            # J11-J20: the MX15EDGK screw plugs in their headers (src/pluggable_terminal.py)
            from . import pluggable_terminal as PT
            tb = PT.parts(b)
            out.append(("connector_board_tb_plug", made_of(pose(tb["housing"], *at), "nylon")))
            out.append(("connector_board_tb_screws", made_of(pose(tb["metal"], *at), "steel")))
        if "J8" in SKIP.get(b, ()):
            from . import screw_terminal as ST
            for k, v in ST.parts(b, "J8").items():
                out.append(("%s_term%s" % (b, "" if k == "housing" else "_metal"), pose(v, *at)))
    return out


def assembly() -> list:
    from . import direct_bench as DB
    # ob_board is branner's stand-in for the output board (the gates' courtyards): the
    # routed board drawn here replaces it
    return [p for p in DB.assembly() if p[0] != "ob_board"] + boards()
