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

from cadkit.board_geom import Boards, SILK_CAP, SILK_T, fp_name  # noqa: F401  (re-exported)

GEOM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "elec", "geom")          # tracked: elec/out is git-ignored

# Laid OVER cadkit's tables (project wins).
_HEIGHT: dict = {
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
}
_THT_LEGS: dict = {}
_PANEL: dict = {}

# THE LETTERING'S FACE: the one the boards' silkscreen is plotted in. It is a licensed font
# with one glyph redrawn (tools/make_silk_font.py: the underscore, which is an ornament in
# the original), so the file is NOT in the repository: it is looked for in elec/fonts/
# (ignored by git) and then where Windows installs fonts, and a checkout without it draws
# the lettering in the kernel's default face and says so. SILK_FONT_CAP is the font's
# capital height over its em (OS/2 sCapHeight 667 / 1000): a silk "size" is a capital
# height, a font size is an em.
SILK_FONT_FILE = "RennieMackintoshPSG-Bold.otf"
SILK_FONT_CAP = 0.667


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
BOARDS = Boards(GEOM_DIR, height=_HEIGHT, tail=_TAIL, tht_legs=_THT_LEGS, panel=_PANEL,
                **({"silk_font": _FONT, "silk_cap": SILK_FONT_CAP} if _FONT else {}))

HEIGHT, TAIL, THT_LEGS, PANEL = BOARDS.HEIGHT, BOARDS.TAIL, BOARDS.THT_LEGS, BOARDS.PANEL

load = BOARDS.load
footprint = BOARDS.footprint
tails = BOARDS.tails
holes = BOARDS.holes
mouth = BOARDS.mouth
lead_exit = BOARDS.lead_exit
bodies = BOARDS.bodies
silk = BOARDS.silk
ink = BOARDS.ink
silk_boxes = BOARDS.silk_boxes
solid = BOARDS.solid
