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
  * PinHeader_2x07_P1.27mm_Horizontal (the UI ribbon, both ends): height from the LCSC
    listing and tail ESTIMATED, neither off a drawing -- measure one. The tail sizes the
    UI clamp plate's relief (src/ui_panel.py).
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

# Laid OVER cadkit's tables (project wins). Empty: every part we use is in the shared set.
_HEIGHT: dict = {}
_TAIL: dict = {}
_THT_LEGS: dict = {}
_PANEL: dict = {}

BOARDS = Boards(GEOM_DIR, height=_HEIGHT, tail=_TAIL, tht_legs=_THT_LEGS, panel=_PANEL)

HEIGHT, TAIL, THT_LEGS, PANEL = BOARDS.HEIGHT, BOARDS.TAIL, BOARDS.THT_LEGS, BOARDS.PANEL

load = BOARDS.load
footprint = BOARDS.footprint
tails = BOARDS.tails
holes = BOARDS.holes
mouth = BOARDS.mouth
lead_exit = BOARDS.lead_exit
bodies = BOARDS.bodies
silk = BOARDS.silk
silk_boxes = BOARDS.silk_boxes
solid = BOARDS.solid
