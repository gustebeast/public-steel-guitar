# Rev 1 boards in hand

A board that was ordered and has since been changed keeps its rev-1 record here. This
folder is NOT `elec/geom`: the viewer, `tools/cost.py` and the geometry checks glob that
folder, and a second copy of a board there would be counted and drawn twice.

| Board | Rebuild rev 1 | Geometry as made |
|---|---|---|
| `output_panel` | `OUTPUT_PANEL_REV=1 py -3.12 elec/output_panel.py`. It writes the 66 mm board with R1's placements and R1's frozen THRU pair (`elec/output_panel.frozen.json`), identical to the board file as of `1c4fd301` | `output_panel.geom.json`, copied from `elec/geom` before rev 2 was exported |
| `optical` | `OPTICAL_REV=1 py -3.12 elec/optical.py` (point `OPTICAL_OUT` at a scratch folder). Placements equal the ordered board, the MCU block frozen at its as-ordered x | `optical.geom.json`, copied from `elec/geom` before rev 2's placed board was exported (2026-10-29) |

Rev 2 is the default everywhere. Point `OUTPUT_PANEL_OUT` at a scratch folder to write a
trial build anywhere other than `elec/out`.
