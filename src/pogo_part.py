# -*- coding: utf-8 -*-
"""The side-mount pogo both lighting joints use, as the part itself is drawn.

Nothing here knows about a board. `fret_light` (the deck seam) and `foot_light` (the foot
strip's seam) both read it, and tools/check_part_specs.py checks it against the datasheet.
It is its own module so that neither of those has to import the other.
"""
# Xinyangze YZF0002-38080-02 (LCSC C5203987), off LCSC's own EasyEDA footprint
# CONN-SMD_YZF0002-38080-02 and the maker's drawing, both read 2026-09-30. Everything
# is measured from the PAD CENTRE, because that is where elec/ places the part:
#     pad         5.00 (along the axis) x 3.50
#     barrel      4.50 x 3.00 x 3.80, centred on the pad: rear face 2.25 BEHIND the
#                 centre, front face 2.25 AHEAD of it
#     plunger     O2.00, 3.50 proud of the barrel at free length (8.00 rear-to-tip),
#                 bottoms at 5.70, rated 200 gf at 6.00
POGO_MPN = "YZF0002-38080-02"
POGO_PAD_L, POGO_PAD_W = 5.00, 3.50
POGO_BODY_L, POGO_BODY_W, POGO_BODY_H = 4.50, 3.00, 3.80
POGO_AXIS_H = 1.90
POGO_PLUNGER_D = 2.00
# ⚠ THE BARREL AS BUILT IS 4.60, NOT 4.50. board_geom extrudes a part's F.Fab to KiCad's
# bounding box, which includes the outline's 0.10 stroke -- 0.05 proud all round. The
# plungers start at THAT face, or each one sits 0.05 inside its own barrel and the gate
# reads 0.94 mm3 per board (tools/_probe_seam.py found it). Geometry of the pogo itself
# (setbacks, working height) still uses the drawing's 4.50.
POGO_FAB_STROKE = 0.10
POGO_FREE, POGO_LIMIT = 8.00, 5.70
# ⚠ 6.30 AT FLUSH, NOT THE CATALOGUE'S 6.00 -- 9.1e. Bottoming is the failure that
# cannot be recovered: a pogo at its 5.70 limit is a brass strut holding the panels
# apart, and no endplate clamping closes that seam. Losing a little force is not.
POGO_WORK = 6.30
# The same drawing gives what the pin is made of: plunger and barrel brass C3604, gold
# over 50-80 u-in nickel (plunger 3 u-in, barrel 1 u-in), spring SUS304 -- so the whole
# pin is gold to look at. Read 2026-10-12.
POGO_RGB = (0.83, 0.68, 0.25)       # cadkit.web.parts.GOLD: the barrel is drawn there


def plunger(x_root, x_tip, y, z):
    """One plunger along X, from the barrel's front face at x_root to its tip at x_tip:
    cadkit's spring pin (cadkit.pcb.spring_plunger), flat ended as the drawing has it."""
    from cadkit.pcb import spring_plunger
    return (spring_plunger(POGO_PLUNGER_D, abs(x_tip - x_root), "flat")
            .rotate((0, 0, 0), (0, 1, 0), 90.0 if x_tip > x_root else -90.0)
            .translate((x_root, y, z)))
