"""Printed-circuit boards in the CAD, READ BACK FROM THE ROUTED BOARD.

The machinery is cadkit's (`cadkit/board_geom.py`, shared with every project): the
exporter writes elec/geom/<board>.geom.json from the finished .kicad_pcb, and a `Boards`
object turns that into solids and answers where each connector's mouth actually is. This
module is this project's INSTANCE of it -- the geom folder, and the part facts that are
ours rather than everyone's -- under the names the rest of src/ has always imported:

    from . import board_geom as BG
    BG.solid("output_panel")      BG.mouth("output_panel", "J5")      BG.HEIGHT[...]

WHAT KiCad DOES NOT CARRY -- body heights, tail lengths, panel-connector mouths -- is
keyed by FOOTPRINT in cadkit's tables, because it is a fact about the PART. A part only
this instrument uses, or a figure this project has reason to hold differently, goes in
the override dicts below; a part worth sharing goes into cadkit (canonical repo, then
propagate) with its source.

PROJECT NOTES ON PARTICULAR PARTS (the numbers themselves are in cadkit):
  * PinSocket_2x20 8.5 IS THE STRUCTURE, not a bump: the pi_cap hangs off the Pi's header
    by it, so the figure is the standoff between the Pi's top face and the cap's
    underside. src/electronics.py places the cap by the same number.
  * PinHeader_2x07/2x08_P1.27mm_Horizontal (the UI ribbon's two ends): tail off the
    maker's drawing (_TAIL below); height still the LCSC listing's. The tail hangs into
    the UI clamp plate's relief (src/ui_panel.py).
  * Alps_RKJXT1F42001 8.30 is the CASE only; src/ui_panel.py draws the collar and the
    D-shaft, which pass through the deck.
  * XINGLIGHT_XL-5050RGBW stands inside a fret light cell: its height is floor taken out
    of the bounce, not just a clearance. The fret boards are SMT throughout because their
    underside sits 1.00 mm over the CAN harness (src/fret_light.py).
  * JST_SH side entry 2.95 is WHY the foot strip uses an SH: the board hangs into a
    3.40 mm trough and a 5.5 PH does not fit (src/foot_light.py).
  * The pogo barrel's plunger is not in F.Fab; src/fret_light.py models it.
  * The USB-C opening is overmold-sized because the receptacle cannot reach the panel
    face (J1_SETBACK in elec/output_panel.py): the plug has to follow it in.
"""
from __future__ import annotations

import os

from cadkit.board_geom import Boards, mask_rgb

GEOM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "elec", "geom")          # tracked: elec/out is git-ignored

# THE BOARD REVISION THE MODEL IS BUILT WITH, per board that has more than one (the same
# environment variables the generators read, so one switch sets both). 2 is the default
# everywhere; 1 is the ordered board in hand, whose geometry lives in elec/rev1 (it is NOT in
# elec/geom: see elec/rev1/README.md). THE BOARDS ONLY: the plastic and the wiring are drawn for
# R2 (user, 2026-10-30), so 1 regenerates an R1 board's files and is not an instrument build.
OUTPUT_PANEL_REV = int(os.environ.get("OUTPUT_PANEL_REV", "2"))
OPTICAL_REV = int(os.environ.get("OPTICAL_REV", "2"))
PI_CAP_REV = int(os.environ.get("PI_CAP_REV", "2"))
MOTOR_CTRL_REV = int(os.environ.get("MOTOR_CTRL_REV", "2"))
assert all(r in (1, 2) for r in (OUTPUT_PANEL_REV, OPTICAL_REV, PI_CAP_REV, MOTOR_CTRL_REV)), \
    "a board REV is 1 or 2"
REV1_DIR = os.path.join(os.path.dirname(GEOM_DIR), "rev1")
REV = {"output_panel": OUTPUT_PANEL_REV, "optical": OPTICAL_REV, "pi_cap": PI_CAP_REV,
       "motor_ctrl": MOTOR_CTRL_REV}


def _with_revs(boards):
    """`boards` with each rev-1 board's geometry read from elec/rev1 instead of elec/geom.
    Boards.load caches per board name, so the rev-1 file is put in that cache up front."""
    import json
    for name, rev in REV.items():
        if rev == 1:
            with open(os.path.join(REV1_DIR, name + ".geom.json"), encoding="utf-8") as fh:
                boards._cache[name] = json.load(fh)
    return boards

# THE SOLDER MASK EACH BOARD IS ORDERED IN, where it is not the fab's default green. A
# board is drawn in it (src/build.py's colours), so the model shows the board that will
# be in the hand. The order itself is each board's "order_options" in elec/<board>.py:
# keep the two in step.
MASK: dict = {
    "optical": "black",      # functional, not taste: the sensor cavity is a light trap
}


def mask(board: str):
    """(r, g, b) of `board` as made: its solder mask's colour."""
    return mask_rgb(MASK.get(board, "green"))


# Laid OVER cadkit's tables (project wins).
_HEIGHT: dict = {
    "Hanxia_HX-TYPE-C-16P-180-LC-B-H10.0_Vertical": 10.0,     # motor_ctrl R2 J4, drawing L
    # optical's R1, drawn from its geometry only on the first-flash bench (src/flash_bench.py);
    # the instrument's optical board is drawn by src/optical_pickup.py
    "Everlight_PD15-22B": 1.10,
    "LQFP-176_24x24mm_P0.5mm": 1.6,
    "R_2512_6332Metric": 0.6,
    "SOT-223-3_TabPin2": 1.8,
    "Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm": 0.8,
    "VSSOP-8_3x3mm_P0.65mm": 1.1,
    # output_panel R2. SOD-123F: SMF24A, 1.1 max; MSOP-10: INA226, 1.1 max; SOIC-16: CH340C, 1.75 max;
    # X2QFN-12: TUSB320, 0.4 max; UQFN-10: TS3USB221, 0.55 max; MX128: as src/screw_terminal.py draws it
    "D_SOD-123F": 1.10, "MSOP-10_3x3mm_P0.5mm_Tight": 1.10, "SOIC-16_3.9x9.9mm_P1.27mm": 1.75,
    "Texas_RWB0012A_X2QFN-12_1.6x1.6mm_P0.4mm": 0.40, "Texas_UQFN-10_1.5x2mm_P0.5mm": 0.55,
    "MaiXu_MX128-5.0-02P_1x02_P5.00mm": 14.0,
    # connector board J11-J20 (2026-11-14): MAX MX15EDGRC-3.5-04P header 9.20 tall, its MX15EDGK
    # plug 11.10 (both drawings, 22.09.14) -- the mated pair's height, since the instrument
    # always has the plug in (and SIDE_PLUG_RUN carries it past the header's mouth)
    "MAX_MX15EDGRC-3.5-04P_1x04_P3.50mm_Horizontal_Mated": 11.1,
    "MAX_MX15EDGRC-3.5-02P_1x02_P3.50mm_Horizontal_Mated": 11.1,   # brain_board J8 (2026-11-14), as the 04P
    # output_panel U10, the AD8402 gain pot: 14-lead narrow SOIC, 1.75 max (JEDEC MS-012-AB)
    "SOIC-14_3.9x8.7mm_P1.27mm": 1.75,
    # the tee's 8-way trunk: the same shell as cadkit's S4B-XH-A, eight ways long. The tee
    # is drawn by hand (electronics.tee_pcb), so this is read only for where a wire leaves it
    "JST_XH_S8B-XH-A_1x08_P2.50mm_Horizontal": 6.1,
    # the 3.3 V buck inductors on motor_ctrl and output_panel, on APV's own land (the
    # project footprint Steel:L_APV_PNR3015): 3.0 x 3.0 x 1.5 max, its sheet
    "L_APV_PNR3015": 1.50,
    # the UI ribbon's 2x8, the 2x7's sibling (HX PZ1.27-2x8P WZ): the same LISTED 3.9
    "PinHeader_2x08_P1.27mm_Horizontal": 4.0,
    # the power button's CASE, off Legion's drawing; src/ui_panel.py draws the stem
    "Legion_PB-22E85": 8.5,
    # the optical board's ULPI PHY, USB3300-EZK: "5 x 5 x 0.9 mm body" (DS00001783C fig. 8-1)
    "QFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm": 0.9,
    # the optical board's 24 MHz oscillator, JSCJ CJO05: "1.2 max" (its outline drawing)
    "Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm": 1.2,
    # the LED drivers, TLC5971RGER: "VQFN - 1 mm max height" (SBVS146D, RGE0024H outline)
    "Texas_RGE0024H_VQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm": 1.0,
    # both LED supplies' inductor (elec/buck_cell.py): Sunlord's table, C = 4.0 max
    "L_Sunlord_SWPA5040S": 4.0,
    # the CAN tee's terminator switch, DSHP01TSGER: 2.30 +-0.20 off the board (its drawing)
    "Kangshen_DSHP01TSGER": 2.5,
    # the UI board's display FFC socket, Molex 52271-2079: 3.0 +-0.2 (SD-52271-036, side view)
    "Molex_52271-2079_1x20-1MP_P1.0mm_Horizontal": 3.0,
    # the lever board's angle sensor, MA730GQ-Z on MPS's own land (Steel.pretty): the side view
    # gives the package 0.80 .. 1.00 (MA730 rev 1.1 p.26), so the max
    "MPS_QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm": 1.00,
}
_TAIL: dict = {
    # READ, not estimated (2026-10-04): HX's PZ1.27-2xNP WZ drawing gives the solder leg
    # as 3.40 +-0.25 under the insulator, so 1.8 shows under a 1.6 board. One drawing
    # covers every way count, so the 2x7 on the Pi cap takes the same figure.
    "PinHeader_2x08_P1.27mm_Horizontal": 1.8,
    "PinHeader_2x07_P1.27mm_Horizontal": 1.8,
    "Legion_PB-22E85": 1.8,                      # 3.4 of terminal less a 1.6 board
    # the Pi cap's 2x20 socket. ESTIMATED: 2.54 mm sockets are sold with a 3.0 mm solder
    # tail, so 1.4 shows through a 1.6 board; read the chosen part's drawing at order
    "PinSocket_2x20_P2.54mm_Vertical": 1.4,
    "JST_XH_S4B-XH-SM4-TB_1x04-1MP_P2.50mm_Horizontal": 0.0,   # surface mount
    "SOT-23-6": 0.0,                             # surface mount (the Pi cap's U1)
    "L_Sunlord_SWPA5040S": 0.0,
    "Kangshen_DSHP01TSGER": 0.0,                 # gull wing
    "Molex_52271-2079_1x20-1MP_P1.0mm_Horizontal": 0.0,  # surface mount
}
_THT_LEGS: dict = {}
# THE JACK'S COUNTERBORE AND BOSS follow the printed nut socket that ships with the instrument
# (src.jack_socket, user 2026-11-23): sized for it, not for an 11 mm thin-wall metal socket.
# The pocket export reads these; the endplate reads the export.
from . import jack_socket as _JS  # noqa: E402
from cadkit.board_geom import PANEL as _CK_PANEL  # noqa: E402
_PANEL: dict = {n: dict(_CK_PANEL[n], cbore_d=_JS.CBORE_D, boss_d=_JS.BOSS_D) for n in _JS.JACK_FPS}

# THE LETTERING'S FACE: the one the boards' silkscreen is plotted in. It is a licensed font
# with one glyph redrawn (tools/make_silk_font.py: the underscore, which is an ornament in
# the original), so the file is NOT in the repository: it is looked for in elec/fonts/
# (ignored by git) and then where Windows installs fonts, and a checkout without it draws
# the lettering in the kernel's default face and says so.
# SILK_FONT_CAP turns a silk "size" (KiCad's text size) into the em the kernel draws at.
# KiCad's size is NOT the capital height in an outline font: measured off the plotted ink
# in KiCad 10, a capital in this face stands 0.934 of the text size (1.308 at 1.4), and
# the font's capital is 667 of a 1000 em. At the boards' 1.5 that is a 1.40 mm capital
# and a 0.153 underscore bar here, as on the plot.
SILK_FONT_FILE = "RennieMackintoshPublicSteelGuitar-Bold.otf"
KICAD_CAP = 0.934                    # capital height / KiCad text size, measured
SILK_FONT_CAP = 0.667 / KICAD_CAP    # 0.714 of an em per unit of text size


def _silk_font():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for d in (os.path.join(here, "elec", "fonts"),
              os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"),
              os.path.join(os.environ.get("WINDIR", ""), "Fonts")):
        f = os.path.join(d, SILK_FONT_FILE)
        if os.path.isfile(f):
            return f
    print("board_geom: %s not found (elec/fonts/ or installed) -- board lettering is drawn "
          "in the default face" % SILK_FONT_FILE)
    return None


_FONT = _silk_font()
# A SIDE-ENTRY part's mated plug past its own mouth, by footprint-name prefix (cadkit
# SIDE_PLUG_RUN; project wins). MX15EDGK-3.5: 15.90 long, 5.30 of it inside the header -> 10.6
# past the header's front face (5.9 from the pin row): 16.5 from the pins, the footprint's
# 17 mm courtyard
SIDE_PLUG_RUN = {"MAX_MX15EDGRC-3.5-": 10.6}
# WHAT EACH BODY WITH NO 3D MODEL IS MADE OF (cadkit Boards(body_material=), 2026-11-14): the
# web export has no board-green default any more -- a footprint with no model, no web_parts
# drawing and no entry here stops the export. Colours as these packages usually come; a part
# whose datasheet says otherwise is corrected here.
BLACK, CREAM_LCP = (0.05, 0.05, 0.05), (0.85, 0.80, 0.68)
BODY_MATERIAL = {
    "Converter_DCDC_Murata_MEE1SxxxxSC_THT": ("epoxy", BLACK),        # isolated DC-DC, black SIP case
    "Fuse_1812_4532Metric": ("epoxy", (0.78, 0.62, 0.25)),             # PPTC, tan coat
    "Fuse_2920_7451Metric": ("epoxy", (0.78, 0.62, 0.25)),             # PPTC, tan coat
    "Hanxia_HX-TYPE-C-16P-180-LC-B-H10.0_Vertical": "stainless",       # USB-C receptacle shell
    "Hirose_DF40C-100DS-0.4V_2x50_P0.4mm": ("nylon", CREAM_LCP),       # CM5 mezzanine (LCP)
    "JST_PH_B4B-PH-SM4-TB_1x04-1MP_P2.00mm_Vertical": ("nylon", (0.93, 0.90, 0.80)),
    "L_Bourns_SRP1770TA_16.9x16.9mm": ("ferrite", (0.22, 0.22, 0.23)),  # moulded composite
    "L_Bourns_SRP1513CA_15.5x16.5mm": ("ferrite", (0.22, 0.22, 0.23)),  # brain L4, metal alloy powder
    "L_CommonModeChoke_Wuerth_WE-SL5-HC": ("ferrite", (0.10, 0.10, 0.10)),
    "MaiXu_MX128-5.0-02P_1x02_P5.00mm": ("nylon", (0.10, 0.45, 0.20)),  # green terminal block
    "Molex_52271-2079_1x20-1MP_P1.0mm_Horizontal": ("nylon", CREAM_LCP),
    "Texas_RNX0012_VQFN-HR-12_2x3mm_P0.5mm": ("epoxy", BLACK),
    "Texas_RWB0012A_X2QFN-12_1.6x1.6mm_P0.4mm": ("epoxy", BLACK),
    "Texas_UQFN-10_1.5x2mm_P0.5mm": ("epoxy", BLACK),
    "Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm": ("epoxy", BLACK),   # U221 TPS22965
    "Texas_RYQ0021B_VQFN-HR-21_3x5mm_P0.5mm": ("epoxy", BLACK),               # U205 TPS552892
    "Texas_RPW0010A_VQFN-HR-10_2x2mm_P0.45mm": ("epoxy", BLACK),              # U221 TPS259470A
    "Texas_DDA0008_HSOP-8-1EP_3.9x4.9mm_P1.27mm": ("epoxy", BLACK),   # U5 LMR33640
    "WCH_QFN-16-1EP_3x3mm_P0.5mm_EP1.8x1.8mm": ("epoxy", BLACK),              # U37 CH334P
}
BOARDS = _with_revs(Boards(GEOM_DIR, height=_HEIGHT, tail=_TAIL, tht_legs=_THT_LEGS, panel=_PANEL,
                           side_plug_run=SIDE_PLUG_RUN, body_material=BODY_MATERIAL,
                           **({"silk_font": _FONT, "silk_cap": SILK_FONT_CAP} if _FONT else {})))

HEIGHT, TAIL, THT_LEGS, PANEL = BOARDS.HEIGHT, BOARDS.TAIL, BOARDS.THT_LEGS, BOARDS.PANEL


def on_the_bench(unmated) -> Boards:
    """The same boards with the same part facts, as they lie on a BENCH: `unmated` names
    the (board, ref) headers nothing is plugged into there (in the instrument every
    header has its plug)."""
    return _with_revs(Boards(GEOM_DIR, height=_HEIGHT, tail=_TAIL, tht_legs=_THT_LEGS,
                             panel=_PANEL, unmated=unmated, side_plug_run=SIDE_PLUG_RUN,
                             body_material=BODY_MATERIAL,
                             **({"silk_font": _FONT, "silk_cap": SILK_FONT_CAP} if _FONT else {})))


load = BOARDS.load
footprint = BOARDS.footprint
tails = BOARDS.tails
holes = BOARDS.holes
mouth = BOARDS.mouth
bodies = BOARDS.bodies
silk = BOARDS.silk
ink = BOARDS.ink
solid = BOARDS.solid
