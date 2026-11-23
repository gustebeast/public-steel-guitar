"""The brain board's LM5122 24 V boost (U220) as one designed cell, placed whole.

An engineer lays a switcher out once, from the vendor's layout guidance, and moves it as a
unit. The general placer chose U220's turn and L204's seat before it knew how much room the
satellites needed. Its screens (sw1, sw2, 2026-11-22) left the VIN / VCC / hot-loop caps with
NO ROOM and put the FETs 12-19 mm from their gate pins. buck_cell.py uses the same pattern for
the LMR33630.

TI SNVS954H (LM5122), section 10.1 and figure 49:
  * "the primary switching loop consists of the output capacitor and N-channel MOSFET power
    switches. Minimizing the area of this loop reduces the stray inductance". The fix is
    C315 (0402 HF) and C306 (2220, "high quality ceramic output capacitors as close to this
    loop") in the corner where Q209's +24V tab and Q208's sources meet.
  * "connect HO and SW to the gate and source of the high-side ... through short and low
    inductance paths", and the same for LO / PGND: both gate pins face U220's driver pins.
  * "VCC, VIN and BST capacitor must be as physically close as possible to the device": C298
    (VCC) at pin 17, C297 (VIN) at pin 5, C299 (BST) over pins 20 / 18.
  * "CSP and CSN ... place 100-pF ceramic filter capacitor close to the device": C304 over
    pins 3 / 4, with R310 / R311 just beyond them.
  * figure 49: "place controller as close to the switches".

TI SNVU197 (LM5122EVM-1PH user guide), section 8, figures 12-15:
  * Q2 / Q3 sit STACKED, with their switch-node ends turned the same way toward the inductor.
    The SW node is one short top-layer polygon from the FET pads to the inductor pad, with
    the bootstrap parts on it. The output ceramics sit on the far side of the FETs from the
    inductor, in the switching loop.
  * The controller sits close to the FETs, with the gate traces short and direct.
  * Figure 15: the bottom copper carries only control signals. Every power path, the SW
    polygon included, stays on top.
GATE LOOPS (lead, 2026-11-22). Stacking costs gate length: Q209's gate is about 11 mm of
track from HO, against about 4 mm side by side. That is what TI ships, and a small SW node
with a tight hot loop matters more. The gate LOOP AREA must stay small, though, and a near
rule cannot say that. ROUTE each driver line beside its return: HO beside the SW return from
Q209's source pins to U220.18, and LO beside the PGND return from Q208's sources to U220's
PGND. Run each pair side by side on F.Cu, with no other net between them.
This cell follows that arrangement. Q208 and Q209 are stacked, with Q209's SW pins 1-3 and
Q208's SW tab both facing +Y. L204 seats on +Y, with its SW pad toward them. The output
ceramics C315 and C306 are on -Y.

L204 (15.5 x 16.5) and R309 are MEMBERS. They were outside the cell at first, for size, tied
to it by hard near rules. Screen c3 (2026-11-22) showed why that fails: the placer chose the
cell's turn without them, turned the SW side to -X, and the power switch (Q202 / C201) had
already taken that ground. L204 found NO ROOM. An engineer places the inductor with its power
stage, so the cell now carries it:
  * L204 sits over the stacked FETs with its SW pad (2) toward them. Its rules to Q209's SW
    pins and Q208's SW tab keep the SW node small, as the high dv/dt copper must be.
  * R309 sits off L204's input pad (1): the current sense at the inductor's input end.
  * C292 (input bulk) and C296 (HF bypass) sit at R309's VIN_SW end: figure 49's input
    loop, with L204's input, R309 and the input caps in one tight run. They were outside the
    cell too, tied to R309 by hard rules, with seats inside its box. Screen c5 showed that
    fails as well: the composite reserves only its members' courtyards, so other parts took
    those gaps and both found NO ROOM. Their seats are designed, so they are members.
OUTER / REACH remain for parts that a hard rule ties to the cell from outside; today none.

The control parts (UVLO, SS, RT, FB, COMP, SLOPE, RES) are NOT members. They stay
auto_switcher satellites at their pins, and the cell leaves U220's -Y pin row free for them.

FRAME: offsets are in U220's frame at rot 0, in the parts' pad frame (pcbflow places a part by
its pads, as buck_cell's ORIGIN note says), in mm. rot is the member's own turn.
"""
from __future__ import annotations

import itertools
import json
import sys

ANCHOR = "U220"
SRC = "TI SNVS954H 10.1 / fig. 49 (LM5122); TI SNVU197 8 / figs. 12-15 (LM5122EVM-1PH)"
CELL = {   # member -> (dx, dy, rot)
    "Q208": (9.24, 3.30, 90.0),      # low side, stacked: SW tab (pad 5) toward +Y, gate pin 4 at LO's side
    "Q209": (15.10, 3.30, 270.0),    # high side, stacked: SW pins 1-3 toward +Y, +24V tab toward -Y
    "C315": (12.17, -1.24, 180.0),   # HF loop cap: +24V tab to Q208's sources, the loop corner
    "C306": (12.17, -4.84, 180.0),   # first output ceramic, behind C315 in the loop
    "C298": (5.26, 0.03, 270.0),     # VCC cap at pin 17
    "C299": (4.90, 2.80, 270.0),     # BST cap over pins 20 (BST) / 18 (SW), on the SW polygon
    "D217": (5.30, 5.40, 270.0),     # bootstrap diode VCC -> BST, beside C299
    "C304": (-4.75, 1.30, 90.0),     # CSP / CSN filter over pins 3 / 4
    "C297": (-5.00, -1.40, 270.0),   # VIN cap at pin 5
    "R311": (-4.75, 3.70, 270.0),    # CSN filter resistor
    "R310": (-5.95, 3.70, 270.0),    # CSP filter resistor
    "L204": (15.75, 15.75, 270.0),   # over the stacked FETs, SW pad (2) down toward them
    "R309": (8.50, 26.25, 0.0),      # current sense along L204's top, LMID pad at L204.1, VIN_SW end to -X
    "C296": (1.50, 23.25, 0.0),      # input HF bypass at R309's VIN_SW end
    "C292": (-0.25, 19.50, 0.0),     # input bulk at R309's VIN_SW end
}
# hard rules among the members (the gate checks them; the geometry alone must meet them)
RULES = [
    dict(kind="decap", cap="C298", pin="U220.17", max_mm=3.0, why="VCC capacitor 'as physically close as possible'"),
    dict(kind="decap", cap="C297", pin="U220.5", max_mm=3.0, why="VIN capacitor 'as physically close as possible'"),
    dict(kind="decap", cap="C299", pin="U220.20", max_mm=3.0, why="BST capacitor 'as physically close as possible'"),
    dict(kind="decap", cap="C304", pin="U220.3", max_mm=3.0, why="CSP / CSN filter capacitor 'close to the device'"),
    dict(kind="near", ref="Q209", target="U220.19", max_mm=10.0, why="HO to the high-side gate, 'short and low inductance'"),
    dict(kind="near", ref="Q208", target="U220.16", max_mm=10.0, why="LO to the low-side gate, 'short and low inductance'"),
    dict(kind="near", ref="Q208", target="Q209", max_mm=3.0, why="the primary switching loop: minimum area"),
    dict(kind="near", ref="C306", target="Q209", max_mm=3.0, why="first output ceramic in the switching loop"),
    dict(kind="near", ref="C315", target="Q209", max_mm=3.0, why="HF output ceramic in the switching loop"),
    dict(kind="near", ref="C315", target="Q208", max_mm=3.0, why="HF output ceramic: the loop's GND corner"),
    dict(kind="near", ref="C306", target="Q208", max_mm=3.0, why="first output ceramic: the loop's GND corner"),
    # a pin target is measured to the pin's centre, so a large pad's limit carries the pad's
    # depth inside its own part's courtyard: Q208's SW tab centre sits 2.5 mm in -> 4.0;
    # L204's 4.5 x 15 pads sit ~3.3 mm in -> 4.0 / 5.0
    dict(kind="near", ref="L204", target="Q209.2", max_mm=3.0, why="SW node: high dv/dt copper, keep it small (SNVU197 fig. 14)"),
    dict(kind="near", ref="L204", target="Q208.5", max_mm=4.0, why="SW node: high dv/dt copper, keep it small (SNVU197 fig. 14)"),
    dict(kind="near", ref="Q209", target="L204.2", max_mm=4.0, why="the inductor's SW end faces the FETs"),
    dict(kind="near", ref="R309", target="L204.1", max_mm=5.0, why="input loop: current sense at the inductor's input end"),
    dict(kind="near", ref="C292", target="R309.1", max_mm=3.0, why="input bulk at the inductor's input (via R309)"),
    dict(kind="near", ref="C296", target="R309.1", max_mm=3.0, why="input HF bypass at the inductor's input (via R309)"),
]
# hard rules tying OUTSIDE parts to the cell, and one proven legal seat for each (none today)
OUTER = []
REACH = {}   # outside part -> (dx, dy, rot) in the anchor frame, proven by check()
GAP_MM = 0.15     # courtyard to courtyard


def intent_rules():
    """The intent rules this cell adds: the group (placed whole) and its hard rules."""
    out = [dict(kind="group", anchor=ANCHOR, members={k: list(v) for k, v in CELL.items()}, hard=True,
                src=SRC, why="the LM5122 boost as one designed cell (elec/lm5122_cell.py)")]
    out += [dict(r, hard=True, src=SRC) for r in RULES + OUTER]
    return out


def check(parts, pi):
    """[problem] for the cell alone at the origin, plus REACH: courtyard overlaps, broken hard rules."""
    pl = {ANCHOR: [0.0, 0.0, 0.0]}
    pl.update({k: list(v) for k, v in CELL.items()})
    pl.update({k: list(v) for k, v in REACH.items()})
    P = pi.Placed(parts, pl)
    bad = []
    for a, b in itertools.combinations(pl, 2):
        d = pi._poly_dist(P.crtyd(a), P.crtyd(b))
        if d < GAP_MM:
            bad.append("courtyards %s / %s %.2f mm apart (< %.2f)" % (a, b, d, GAP_MM))
    for r in RULES + OUTER:
        for s, ref, det in pi.check(dict(r, hard=True), P, {}):
            if s < -0.05:
                bad.append("%s breaks its %s %s <= %g by %.2f (%s)" % (ref, r["kind"], r.get("pin") or r.get("target"),
                                                                     r["max_mm"], -s, det))
    return bad


if __name__ == "__main__":
    # py -3.12 elec/lm5122_cell.py <output_board.parts.json> <cadkit/pcbflow dir>
    sys.path.insert(0, sys.argv[2])
    import place_intent as _pi
    problems = check(json.load(open(sys.argv[1]))["parts"], _pi)
    print("\n".join(problems) if problems else "lm5122_cell: PASS (%d members, %d hard rules, %d outside parts seated)"
          % (len(CELL), len(RULES) + len(OUTER), len(REACH)))
    sys.exit(1 if problems else 0)
