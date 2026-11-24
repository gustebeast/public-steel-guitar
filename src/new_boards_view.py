"""THE NEW INSTRUMENT'S BOARDS IN PLACE -- a VIEW of the direct-drive instrument (src.direct_bench)
with the routed brain and brain boards where their frames put them. Not a fit study: no overlap
gate, and the positions are the intents' frames, not a mount.

  * brain (320 x 70): on its side, -Y of the motors, component side facing -Y (away from the
    motors, JSTs mouth-up). Board X = instrument X + 360, board Y = instrument Z. (To move: user
    2026-11-13, flat in the -X +Y corner -- not drawn there until it is re-placed.)
  * brain_board (167.73 x 100, ONE board, instrument x -167.3 .. 0.43; it drops in -Z at its FINAL x with the +X endplate
    off, then the endplate slides back on over it: user 2026-11-19): back face on the -Y side at y -87.5 (branner: +1.7 so
    unclipped 3.4 tails clear the wall at -91.7), parts facing +Y; geom x -> instrument x by OB_X (read, below), board y =
    instrument z + 58.24. The panel (board -X edge) sits 1.6 behind the outer face; flush panel (2026-11-23): USB-C shells 1.5 past the edge, J5 stub tip 1.55 back, nut in a face counterbore; parts in the pocket: elec/brain_board.pocket.json.
  * the optical board is NOT drawn: it is being redesigned (user 2026-11-13: no forwarder MCU,
    a ribbon to the brain board).

The geometry is elec/geom/<board>.geom.json: bronner exports the CHOSEN trial into it (cadkit
kicad_geom.py --out), since trial runs all write there. Each board's solids are KEPT (cadkit.kept,
keyed on that file): a render rebuilds only a board whose geometry changed.

    view: agent_sync.py scope --set src.new_boards_view --attr assembly; agent_sync.py view --solo
"""
from __future__ import annotations

from functools import lru_cache

import os
import sys

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
    "L_Bourns_SRP1770TA_16.9x16.9mm": 7.0,   # brain part_heights L4 (before 2026-11-17)
    "L_Bourns_SRP1513CA_15.5x16.5mm": 7.3,   # brain L4 APS1513M100F: 7.0 +- 0.3
    "PinHeader_2x08_P1.27mm_Vertical": 5.3,  # brain part_heights J5 (HX PZ1.27-2x8P ZZ)
    "PinHeader_2x10_P1.27mm_Vertical_SMD": 5.3,   # brain_board J4 PZ1.27-2x10P: AS its 2x8 sibling
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
    # brain_board parts with no height in the project table (the view raised KeyError
    # at HEAD, 2026-11-14; geom = the mL2 trial): from the drawings where read
    "L_CommonModeChoke_Coilank_ACM2012": 1.3,     # TDK ACM2012: 2.0 x 1.2 x 1.3
    "Converter_DCDC_Murata_MEE1SxxxxSC_THT": 10.0,   # U30 B0509S-1WR3: 11.50 x 6.0 x 10.0 (Mornsun)
    "L_CommonModeChoke_Wuerth_WE-SL5-HC": 5.0,    # ESTIMATED: Wurth's PDF refused the fetch -- read it
    "Fuse_2920_7451Metric": 2.0,             # F204 2920L200/60GR: ESTIMATED (conservative) -- read Littelfuse's drawing
    "L_Changjiang_FXL0630": 3.0,             # L1: the series' 0630 = 6.6 x 7.0 x 3.0
    "TerminalBlock_Phoenix_PT-1,5-2-3.5-H_1x02_P3.50mm_Horizontal": 8.5,   # J8: ESTIMATED, a 3.5 mm PT's usual body
    # the U5 rework and the service port (2026-11-17): ESTIMATED, the packages' usual max --
    # read TI's DSG0008A / RYQ0021B outlines and WCH's CH334 drawing before any clearance rides on them
    "Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm": 0.8,   # U221 TPS22965
    "Texas_RYQ0021B_VQFN-HR-21_3x5mm_P0.5mm": 1.0,               # U205 TPS552892
    "Texas_DDA0008_HSOP-8-1EP_3.9x4.9mm_P1.27mm": 1.7,   # U5 LMR33640: DDA0008J/B "1.7 mm max height" (SNVSB99C p.38/41)
    "WCH_QFN-16-1EP_3x3mm_P0.5mm_EP1.8x1.8mm": 0.85,             # U37 CH334P
    "Texas_RPW0010A_VQFN-HR-10_2x2mm_P0.45mm": 1.0,   # U221 TPS259470A: "VQFN-HR - 1 mm max height" (TI RPW0010A outline, datasheet p.72)
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
OB_BACK_Y, OB_Z = -87.5, -58.24                    # brain_board's back face, centre z (branner)
# ITS X IS READ, NOT TYPED (lead, 2026-11-19): geom.json is centred on the outline's bounding box
# (cadkit kicad_geom), so every outline change moves its origin -- the 167.73 board's sits 8.45
# off the old 150.83's. bronner's pocket export records where that origin lands in the
# instrument; the drawn edges are checked against the export's own edge_x / minus_x_edge.
def _ob_x() -> float:
    import json as _j
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pk = _j.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "brain_board_pocket.json"), encoding="utf-8"))
    g = _j.load(open(os.path.join(root, "elec", "geom", "brain_board.geom.json"), encoding="utf-8"))
    x = pk["geom_frame_origin_instrument_x"]
    w = g["outline_mm"][0]
    lo, hi = -w / 2 + x, w / 2 + x                     # instrument x = -(geom x) + x
    assert abs(lo - pk["minus_x_edge"]) < 0.05 and abs(hi - pk["edge_x"]) < 0.05, (
        "brain board drawn at x %.3f..%.3f, the pocket export says %.3f..%.3f: geom.json and "
        "pocket.json are not one trial's pair" % (lo, hi, pk["minus_x_edge"], pk["edge_x"]))
    return x


OB_X = _ob_x()


def _build(board):
    """(board, lettering) of `board` in its own frame, as the shipped boards are drawn: ONE
    solid (laminate + every part, BOARDS.solid) and its silkscreen (BOARDS.ink). The web
    export finds the board by its lettering and swaps the boxes for KiCad's coloured models
    (cadkit.web.boards), so the two must be posed alike and the parts must not be split off."""
    return (BOARDS.solid(board, skip=SKIP.get(board, ()), mated=board in MATED),
            BOARDS.ink(board))


# parts the project draws as THE PART, not a box (as output_panel's J8 is: src/screw_terminal.py,
# the slotted MX128 -- one flat blade for it and the motors' terminals)
# brain_board's J8 is a 3.5 mm terminal now (screw_terminal draws the 5.00-pitch MX128 and
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


def _facing_plus_y_mirrored(w, x, y, z):
    """Own frame -> instrument, component side toward +Y and board X = -instrument X."""
    return (w.rotate((0, 0, 0), (1, 0, 0), -90).rotate((0, 0, 0), (0, 1, 0), 180)
            .translate((x, y, z)))


def _flat_up(w, x, y, z):
    """Own frame -> instrument, component side up: a translation."""
    return w.translate((x, y, z))


# Raspberry Pi's own CM5 model, RP-007222-DD-2 "rpi-cm5 3D_STEP" (CM5R5-3dsteps.step, Spatial
# InterOp AP214, 2024-12-17), from pip.raspberrypi.com Compute Module 5 design files. *.step is
# git-ignored, so the file lives here locally; without it the view keeps the drawn stand-in.
CM5_STEP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "elec", "models", "CM5R5-3dsteps.step")


def _cm5_step(t):
    """(pcb, top parts, plugs) of Raspberry Pi's CM5 STEP in the brain board's frame, or None.

    THE MODEL'S FRAME (read off the file, 2026-11-15): the module 55 (x) by 40 (y), PCB z 0..1.1,
    holes at (3.5, 3.5) .. (51.5, 36.5), the DF40 plugs under it at y 1.5-4.5 and 35.5-38.5
    (z down to -1.11), the SoC centred at (31.99, 16.98) -- RP-008180-DS-7 Fig. 4's 31.99 from
    the pin-99 edge and 16.98 from the pin-200 edge. In OUR frame (_cm5's docstring) the pin-101
    row is the +X edge and the pin-1 end +Y, so the model's y = 0 edge is our +X edge and its
    x = 0 edge our -Y edge: a +90 degree turn about Z (det +1, no mirror), then its corner at
    (x1, y0) and its underside on the 1.5 mm DF40 stack."""
    if not os.path.exists(CM5_STEP):
        return None
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "elec"))
    import cm5_mech as CM5
    x0, y0, x1, y1 = CM5.outline()
    z0 = t + CM5.STANDOFF_H
    sols = cq.importers.importStep(CM5_STEP).solids().vals()
    pcb = max(sols, key=lambda s: s.Volume())
    move = lambda s: s.rotate((0, 0, 0), (0, 0, 1), 90).translate((x1, y0, z0 - 0.03))
    plugs = [move(s) for s in sols if s is not pcb and s.BoundingBox().zmax < 0.05]
    tops = [move(s) for s in sols if s is not pcb and s.BoundingBox().zmax >= 0.05]
    W = lambda ss: cq.Workplane("XY").newObject([cq.Compound.makeCompound(ss)])
    return cq.Workplane("XY").newObject([move(pcb)]), W(tops), W(plugs)


def _cm5(t):
    """(module, soc) in the brain board's own frame: the Compute Module 5 on its two DF40s.

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
        f = BG.footprint("brain_board", ref)
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
        # the 320 x 70 brain is NOT drawn: the brain board is the brain now (2026-11-13), and
        # the old board read as a second connector board in the view (user, 2026-11-14)
        # board -X = instrument +X, parts toward +Y: (x, y, z) -> (-x, z, y)
        ("brain_board", _facing_plus_y_mirrored, (OB_X, OB_BACK_Y, OB_Z)),
        ("connector_board", _flat_up, (CB_X, CB_Y, CB_Z)),
    )
    from cadkit.web.finishes import made_of
    for b, pose, at in place:
        solid, ink = _parts(b)
        out.append(("%s_pcb" % b, made_of(pose(solid, *at), "board")))
        if ink is not None:
            out.append(("%s_pcb_silk" % b, made_of(pose(ink, *at), "ink")))
        if b == "brain_board":
            import json as _json
            import os as _os
            _g = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                               "elec", "geom", "brain_board.geom.json")
            _t = _json.load(open(_g))["thickness_mm"]
            mod, soc, plug, leads = _cm5(_t)
            real = _cm5_step(_t)             # Raspberry Pi's own model, when it is on this machine
            if real is not None:
                mod, soc, plug = real
            out.append(("brain_board_cm5", made_of(pose(mod, *at), "board")))
            out.append(("brain_board_cm5_soc", made_of(pose(soc, *at), "polished")))
            out.append(("brain_board_cm5_plug", made_of(pose(plug, *at), "nylon")))
            out.append(("brain_board_df40_leads", made_of(pose(leads, *at), "gold")))
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
    # ob_board is branner's stand-in for the brain board (the gates' courtyards): the
    # routed board drawn here replaces it
    return [p for p in DB.assembly() if p[0] != "ob_board"] + boards()


# ── WHERE A BOARD'S HEADER IS, IN THE INSTRUMENT (lead, 2026-11-23) ───────────────────────────────
# One answer for every board the harness wires to, read from the code that places each board in
# the model -- never typed: tools/harness_runs.py measured three of its ends from guesses (UI J2,
# fret J1, optical) until this.
#   brain_board, connector_board   as boards() poses them (above)
#   ui_board                       src.ui_panel.ui_pcb() lays the routed board unflipped at
#                                  board_centre() / board_z0(), and src.direct_bench moves the whole
#                                  UI station +Y by ui_parts()[1]
#   fret_led_key, fret_led_mid     src.fret_light's own placing of the routed board (_placed: its
#                                  x span and the ear offset), at the DIRECT deck's board height
#                                  (src.deck_v2.BOARD_BOT): the deck draws that board as a stand-in
#                                  slab over the same frets (deck_v2.board_x() ends at the mid
#                                  board's +X end, -149.7), so the routed board is where the slab is
def header_pose(board: str, ref: str) -> tuple:
    """(x, y, z) in instrument mm of the middle of footprint `ref`'s F.Fab body on `board`, 1 mm
    tall off the board's component face (what a lead's end is measured from)."""
    import cadquery as cq
    from . import board_geom as BG
    f = BG.footprint(board, ref)
    x0, x1, y0, y1 = f["fab"]
    if board in ("brain_board", "connector_board"):
        w = cq.Workplane("XY").box(x1 - x0, y1 - y0, 1).translate(((x0 + x1) / 2, (y0 + y1) / 2, 0.5))
        w = (_facing_plus_y_mirrored(w, OB_X, OB_BACK_Y, OB_Z) if board == "brain_board"
             else _flat_up(w, CB_X, CB_Y, CB_Z))
        c = w.val().BoundingBox().center
        return (c.x, c.y, c.z)
    t = BG.load(board)["thickness_mm"]
    up = 1.0 if f["side"] == "F" else -1.0
    zf = t + 0.5 if up > 0 else -0.5                   # the face the part stands on, 0.5 off it
    if board == "ui_board":
        from . import ui_panel as U, direct_bench as DB
        cx, cy = U.board_centre()
        return (cx + (x0 + x1) / 2, cy + DB.ui_parts()[1] + (y0 + y1) / 2, U.board_z0() + zf)
    if board.startswith("fret_led_"):
        from . import fret_light as FL, deck_v2 as DK
        panel = {v: k for k, v in FL.BOARD_NAME.items()}[board]
        return (FL.board_cx(panel) + (x0 + x1) / 2, FL.ear_h() / 2 + (y0 + y1) / 2,
                DK.BOARD_BOT + zf)
    raise KeyError("header_pose: %s is not placed in the instrument" % board)
