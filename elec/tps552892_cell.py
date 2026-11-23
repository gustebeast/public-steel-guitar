"""The brain board's TPS552892-Q1 buck-boost (U205, +5V_CM5) as one designed cell, placed whole.

The general placer left this converter's parts where its spring forces put them. In c7
(2026-11-22) that meant:
  * the BOOT1 cap C220 3.5 mm off its pins;
  * an output bulk cap 3.5 mm out;
  * the Kelvin net ties NT205 / NT206 about 13 mm from the R313 pads they must sit on;
  * L202 10 mm above the IC.
TI's layout (SLVSGT7 8.4.1, figure 8-13) is one arrangement, and the cell is that
arrangement.

TI SLVSGT7 (TPS552892-Q1), section 8.4.1 and figure 8-13, at U205 rot 0:
  * item 3, "Minimize the SW1 and SW2 loop areas as these are high dv/dt nodes": L202 sits
    straight over the IC (+Y), its pads over the SW1 (pin 8) and SW2 (pin 10) bars. That is
    figure 8-13's inductor, fed by the two wide SW pours.
  * item 5, "Place the BOOT1 bootstrap capacitor close to the IC and connect directly to the
    BOOT1 to SW1 pins" (and BOOT2 / SW2 the same): C220 and C323 sit in the two top corners,
    BOOT pad at pin 20 / 19, SW pad under L202's pad.
  * item 6, "Place the VCC capacitor close to the IC with wide and short trace": C219 sits
    top right at pin 18, with its ground pad outward for the PGND vias.
  * item 1, "Place the 0.1-uF small package (0402) ceramic capacitors close to the VIN/VOUT
    pins": C218 bridges the VIN (7) and PGND (9) bars just below the IC, and C230 bridges
    PGND and VOUT (11).
  * figure 8-13: input bulk C216 / C217 stacked below-left, on the VIN side of the PGND
    strip; output bulk C221 / C222 below-right, with C231 / C232 beside them.
  * item 4, "Use Kelvin connections to RSENSE for the current sense signals ISP and ISN and
    run lines in parallel from the RSENSE terminals to the IC pins": R313 sits at the
    output's end, and NT205 / NT206 sit on its two pads' IC-side edges. ISP (pin 12) and ISN
    (pin 13) run as a pair to them.
  * item 8, the compensation and feedback parts "as close to the COMP pin as possible" and
    "far away from ... SW1 and SW2": NOT members. They stay auto_switcher satellites on the
    right pin row (14-16), which the cell leaves free. EN / PG / FSW on the left row stay
    satellites too.

A pin target is measured to the pin's CENTRE. Pins 7-11 are 3.4 mm bars whose centre sits
1.7 mm inside the IC, so a cap or inductor at a bar's end measures about 1.7 mm more than its
copper run. The limits below carry that: VIN / VOUT HF 3.2, L202 4.0.

FRAME: offsets are in U205's frame at rot 0, in the parts' pad frame, in mm. rot is the
member's own turn.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switcher_cell as _sc  # noqa: E402

WHAT = "TPS552892 buck-boost"
ANCHOR = "U205"
SRC = "TI SLVSGT7 8.4.1 / fig. 8-13 (TPS552892-Q1)"
CELL = {   # member -> (dx, dy, rot)
    "C220": (-2.30, 2.62, 180.0),    # BOOT1 cap: BOOT5_1 pad at pin 20, SW5_1 pad under L202.1
    "C323": (2.30, 2.62, 0.0),       # BOOT2 cap: BOOT5_2 pad at pin 19, SW5_2 pad under L202.2
    "C219": (4.85, 2.62, 0.0),       # VCC cap at pin 18, ground pad outward (PGND vias)
    "L202": (0.00, 7.07, 0.0),       # over the IC: pads over the SW1 (8) / SW2 (10) bars
    "C218": (-1.12, -2.90, 0.0),     # VIN HF: across the VIN (7) and PGND (9) bars
    "C230": (1.42, -2.62, 180.0),    # VOUT HF: across PGND (9) and VOUT (11)
    "C216": (-2.40, -5.35, 0.0),     # input bulk, VIN side of the PGND strip
    "C217": (-2.40, -7.80, 0.0),     # input bulk
    "C221": (2.40, -5.35, 180.0),    # output bulk, VOUT side
    "C222": (2.40, -7.80, 180.0),    # output bulk
    "C231": (7.15, -5.35, 180.0),    # output bulk, second column
    "C232": (7.15, -7.80, 180.0),    # output bulk
    "R313": (6.20, -2.90, 0.0),      # Rsense at the output's end: +5V_BB pad (1) IC side
    "NT205": (4.74, -1.525, 90.0),   # ISP Kelvin tie on R313.1's IC-side edge
    "NT206": (7.66, -1.525, 90.0),   # ISN Kelvin tie on R313.2's IC-side edge
}
RULES = [
    dict(kind="decap", cap="C220", pin="U205.20", max_mm=1.5, why="BOOT1 cap 'close to the IC', direct to BOOT1 / SW1 (8.4.1 item 5)"),
    dict(kind="decap", cap="C323", pin="U205.19", max_mm=1.5, why="BOOT2 cap 'close to the IC', direct to BOOT2 / SW2 (8.4.1 item 5)"),
    dict(kind="decap", cap="C219", pin="U205.18", max_mm=2.5, why="VCC cap 'close to the IC with wide and short trace' (8.4.1 item 6)"),
    dict(kind="decap", cap="C218", pin="U205.7", max_mm=3.2, why="VIN HF cap 'close to the VIN/VOUT pins' (8.4.1 item 1); pin 7 is a bar, centre 1.7 in"),
    dict(kind="decap", cap="C230", pin="U205.11", max_mm=3.2, why="VOUT HF cap 'close to the VIN/VOUT pins' (8.4.1 item 1); pin 11 is a bar, centre 1.7 in"),
    dict(kind="near", ref="L202", target="U205.8", max_mm=4.0, why="'Minimize the SW1 and SW2 loop areas' (8.4.1 item 3); bar centre 1.7 in"),
    dict(kind="near", ref="L202", target="U205.10", max_mm=4.0, why="'Minimize the SW1 and SW2 loop areas' (8.4.1 item 3); bar centre 1.7 in"),
    dict(kind="near", ref="C216", target="U205.7", max_mm=5.0, why="input bulk in the VIN loop (fig. 8-13)"),
    dict(kind="near", ref="C217", target="U205.7", max_mm=7.0, why="input bulk in the VIN loop (fig. 8-13)"),
    dict(kind="near", ref="C221", target="U205.11", max_mm=5.0, why="output bulk in the VOUT loop (fig. 8-13)"),
    dict(kind="near", ref="C222", target="U205.11", max_mm=7.0, why="output bulk in the VOUT loop (fig. 8-13)"),
    dict(kind="near", ref="C231", target="U205.11", max_mm=7.0, why="output bulk in the VOUT loop (fig. 8-13)"),
    dict(kind="near", ref="C232", target="U205.11", max_mm=8.0, why="output bulk in the VOUT loop (fig. 8-13)"),
    dict(kind="near", ref="R313", target="U205.12", max_mm=4.0, why="Kelvin sense: ISP / ISN 'in parallel' from RSENSE to the IC (8.4.1 item 4)"),
]
OUTER = []
REACH = {}
GAP_MM = 0.15


def intent_rules():
    """The intent rules this cell adds: the group (placed whole) and its hard rules."""
    return _sc.intent_rules(sys.modules[__name__])


def check(parts, pi):
    """[problem] for the cell alone at the origin: courtyard overlaps, broken hard rules."""
    return _sc.check(sys.modules[__name__], parts, pi)


if __name__ == "__main__":
    # py -3.12 elec/tps552892_cell.py <output_board.parts.json> <cadkit/pcbflow dir>
    sys.exit(_sc.main(sys.modules[__name__], sys.argv[1:]))
