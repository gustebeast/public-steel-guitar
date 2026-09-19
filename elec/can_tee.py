"""CAN bus TEE — trunk pass-through + one motor drop, x9.

    py -3.12 elec/can_tee.py            # -> elec/out/can_tee.{net,board.json}

WHY IT EXISTS: the MKS SERVO42D has a SINGLE 6-pin JST-XH carrying power and CAN
together, so it cannot be daisy-chained without splicing -- and splicing is
soldering, which this project forbids outside a factory-assembled PCB. The tee is
what lets a motor be replaced with no solder and no splice. THAT is the purpose;
everything else about it is a consequence. (An earlier revision of this file
claimed the purpose was "unplugging a device never breaks the bus". That is a
property it happens to have, not the reason it exists, and promoting it to the
reason is what made me reject the multi-way trunk connector below.)

TWO CONNECTORS, NOT THREE. The trunk passes THROUGH one 8-way (in on 1-4, out on
5-8) and the motor hangs off its own 4-way. Keeping the DROP separate is what
serves the purpose: pull one 4-way, swap the motor, plug it back, and the trunk
is never disturbed. Three separate 4-ways came to 40.47 mm of courtyard in a row;
8-way + 4-way is 36.98, which is what lets the board come in at 40 x 16 with a
full 1.0 mm component-to-edge margin AND locating walls on both X edges.

SAME DAISY-CHAIN PATTERN AS THE LEVER BOARD (user): an 8-way carrying trunk in on
1-4 and out on 5-8, identical pin order, so one crimp order and one wiring habit
covers both buses -- the motors simply add a 4-pin step the levers do not need.
The HOUSING differs by bus and cannot be helped: the lever board needs side-entry
SMT (a top-entry plug would insert from inside its housing, and THT posts would
sweep the magnet cap) and LCSC stocks no side-entry SMT 8-way XH, so bus B is PH.
The two buses never share a cable, so nothing has to mate across the difference.

SIDE ENTRY, not top (branner, 2026-09-14). A mated top-entry plug stands 9.8 mm,
and string 10's tee then fouled the magnetic pickup by 1.38 mm -- that one motor
would have kept its 45 deg screw while the other nine got board retention. Side
entry stands 7.0 and clears, so the bank has no exception. S8B-XH-A is LCSC
C157914, $0.0705 with 66,430 in stock -- cheaper than the top-entry part it
replaces. It is still THROUGH-HOLE, so the tails and their constraint survive.

THE BOARD IS ALSO A MOTOR RETENTION PIECE (branner). It seats with its underside
0.8 mm over the motor's top face and its +Y edge flush with the faceplate wall,
so 6.4 mm of board lands on the wall and 9.6 mm laps the motor -- that lap IS the
retention, and the hold screw does both jobs at once. THE CONSTRAINT THAT FALLS
OUT: the through-hole tails hang 3.4 mm below the board, so THE WHOLE TAIL BAND
MUST STAY WITHIN 6.4 mm OF THE +Y EDGE, over the wall. Anything further -Y hangs
over the motor, where a live tail is the first thing the motor touches on the way
out. Both pin rows are therefore collinear on ONE line near that edge. The pad row
sits ASYMMETRICALLY in the side-entry courtyard -- 2.85 to the back, 9.74 to the
mouth -- so y +2.0 keeps the tails 6.0 from the +Y edge while the body still fits
the 16, mouth facing -Y and the plug running out over the motor into free air.

Nine of the ten motors take one. String 10's would foul the magnetic pickup in
its neck-most position, so that one stays on the rail with its 45 deg screw --
same board either way.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
# SKiDL names its log, ERC report and generated part library after the script and
# drops them in the CWD -- the log at IMPORT time, so this has to happen before
# the import, not in __main__. Every derived file belongs in elec/out.
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import json  # noqa: E402

from skidl import ERC, Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

import netcheck                                     # noqa: E402

# ── the harness contract ─────────────────────────────────────────────────────
# Four conductors, colours the user's: black GND / red 24V / yellow CAN_H /
# green CAN_L. The pin ORDER is the board's half of that contract and is the SAME
# on every connector in the instrument, so one crimp order serves all of them.
XH_PINOUT = ("GND", "V24", "CAN_H", "CAN_L")

# 120 R, 1%. ISO 11898 wants 120 ohm at each END of the trunk and nowhere else,
# so every board carries the resistor and leaves the jumper OPEN; the one that
# lands at the bus end gets its closed. One layout, one BOM, one assembly file
# for all nine -- populating R1 on only one would mean two JLCPCB variants to
# save two cents of resistor.
TERM_OHMS = "120R"

# SPLIT TERMINATION (2x 60R + 4.7nF to GND) is the textbook EMC answer and is
# deliberately NOT used: it buys common-mode filtering that matters on a metres-
# long vehicle harness, and this trunk is ~1 m inside a plastic instrument. It
# would also put a capacitor's return current on the same GND the optical
# pickup's analog reference rides.


@subcircuit
def can_tee():
    """Trunk in and out through one 8-way, the motor on its own 4-way, and the
    terminator behind its jumper."""
    gnd, v24 = Net("GND"), Net("+24V")
    can_h, can_l = Net("CAN_H"), Net("CAN_L")
    for n in (gnd, v24, can_h, can_l):
        n.drive = Pin.drives.POWER

    j1 = Part(name="B8B-XH-A", ref_prefix="J", tag="J1", dest="NETLIST", tool="skidl",
              value="S8B-XH-A", description="CAN trunk: in 1-4, out 5-8 (LCSC C157914)",
              footprint="Connector_JST:JST_XH_S8B-XH-A_1x08_P2.50mm_Horizontal",
              pins=[Pin(num=i + 1, name=n, func=Pin.types.PASSIVE) for i, n in enumerate(
                  tuple(x + "_IN" for x in XH_PINOUT) + tuple(x + "_OUT" for x in XH_PINOUT))])
    j2 = Part(name="B4B-XH-A", ref_prefix="J", tag="J2", dest="NETLIST", tool="skidl",
              value="S4B-XH-A", description="drop to this node's motor",
              footprint="Connector_JST:JST_XH_S4B-XH-A_1x04_P2.50mm_Horizontal",
              pins=[Pin(num=i + 1, name=n, func=Pin.types.PASSIVE)
                    for i, n in enumerate(XH_PINOUT)])
    gnd += j1[1], j1[5], j2[1]
    v24 += j1[2], j1[6], j2[2]
    can_h += j1[3], j1[7], j2[3]
    can_l += j1[4], j1[8], j2[4]

    r1 = Part(name="R", ref_prefix="R", tag="R1", dest="NETLIST", tool="skidl",
              value=TERM_OHMS, description="CAN termination, 1%",
              footprint="Resistor_SMD:R_0603_1608Metric",
              pins=[Pin(num=1, func=Pin.types.PASSIVE), Pin(num=2, func=Pin.types.PASSIVE)])
    # SOLDER jumper, not a shunt on a header: which board terminates is fixed
    # when the harness is built, a 2.54 shunt is taller than everything here bar
    # the connectors, and one that falls off is a bus that fails intermittently.
    jp1 = Part(name="SolderJumper_2_Open", ref_prefix="JP", tag="JP1", dest="NETLIST",
               tool="skidl", value="TERM", description="close on the bus's LAST tee only",
               footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm",
               pins=[Pin(num=1, func=Pin.types.PASSIVE), Pin(num=2, func=Pin.types.PASSIVE)])
    term = Net("TERM_MID")
    can_h += r1[1]
    term += r1[2], jp1[1]
    can_l += jp1[2]


# ── the board ────────────────────────────────────────────────────────────────
# 40 x 16. The connector row is 36.98 of courtyard, so 40 leaves a full 1.0 mm
# component-to-edge margin at both ends AND stays inside the 40.5 that lets the
# seat have locating walls on BOTH X edges -- at 42 only +X could be located, the
# -X side having 1.65 mm before the neighbouring motor's body.
BOARD_W, BOARD_L = 40.0, 16.0
# Pin rows COLLINEAR at this Y, which is what keeps the through-hole tails in a
# narrow band 4.0 mm from the +Y edge -- over the faceplate wall, not the motor.
ROW_Y = 2.0

# ── THE EAR (branner, 2026-09-15) ────────────────────────────────────────────
# A SCREW BESIDE THE BOARD ONLY RESISTS PULL-OUT BY FRICTION, and this board is
# pulled in exactly that direction every time a cable comes off: the connector
# mouths face -Y, so unplugging tugs -Y and only the head's grip on the board top
# opposes it. A screw THROUGH the board is positive in X and Y both.
#
# It would not fit inside 40 x 16. An M4 clearance hole wants 4.4 of
# component-free board and the connector courtyards reach to within 3.145 of the
# +Y edge -- 1.255 short, with nothing to give. So the OUTLINE grew instead of
# the layout: the 40 x 16 region is untouched, every courtyard stays where it was
# and TEE_CONN_CY is still 2.0. What is added is a bare EAR off the +X end.
#
# ⚠ THE EAR IS A TAB, NOT FULL DEPTH, and that is load-bearing (branner): the
# motor bank staggers 9.5 in Y, and that stagger is what lets ten ears interlock
# past each other. A full-depth ear clashed board-into-board at 48.5 mm3 per pair.
EAR_W, EAR_H = 9.5, 8.7                  # the tab, off the +X end at the +Y corner
BOARD_OUTLINE_W = BOARD_W + EAR_W        # 49.5 overall; the LAYOUT region is still 40
HOLE_D = 4.5                             # M4 clearance, centred in the ear

# ONE TEE PER MOTOR, AND ONE MOTOR PER STRING -- see the qty note below.
def _tee_qty():
    from src import dimensions as D
    return D.N_STRINGS


_TEE_QTY = _tee_qty()

_HW, _HL = BOARD_W / 2.0, BOARD_L / 2.0
_EAR_X1 = _HW + EAR_W                    # +29.5
_EAR_Y0 = _HL - EAR_H                    # -0.7

BOARD_NOTES = {
    # THE LAYOUT REGION, not the outline: every part lives in the original 40 x 16
    # and place_check measures against this. The board EDGE is outline_poly below.
    "outline_mm": (BOARD_W, BOARD_L),
    "outline_poly": [(-_HW, -_HL), (_HW, -_HL), (_HW, _EAR_Y0), (_EAR_X1, _EAR_Y0),
                     (_EAR_X1, _HL), (-_HW, _HL)],
    # Centred in the ear: 4.75 from the +X edge, 4.35 from the +Y edge.
    "cutouts": [{"xy": (_EAR_X1 - EAR_W / 2.0, _HL - EAR_H / 2.0), "d": HOLE_D}],
    "layers": 2,
    "thickness_mm": 1.6,
    "placements": {
        "J1": (-7.0, ROW_Y, 0.0),      # trunk, 8-way
        "J2": (11.7, ROW_Y, 0.0),      # motor drop, 4-way
        # both connector courtyards now cover y -7.74..+4.85 of a 16 mm board,
        # so the terminator pair lives in the strip above them
        "R1": (-6.0, 6.2, 0.0),
        "JP1": (-1.0, 6.4, 0.0),
    },
    "ref_pos": {"J1": (-14.0, 6.4), "J2": (15.5, 6.4),
                "R1": (-9.5, 6.2), "JP1": (2.5, 6.4)},
    # AUTOROUTED. Four nets across twelve pads on one line cannot run without
    # crossings, so the hand-laid tracks the three-connector version used do not
    # survive the reshape. GND is the B.Cu pour; route.py refills it after the
    # session import so the router's vias get their clearance.
    # NO GROUND POUR, and that is a decision. Four nets across twelve pads on one
    # line cannot be routed without crossings, and on two layers the crossings
    # have to go on B.Cu -- which carves the pour into islands the router then
    # leaves unjoined (two zone-to-zone opens on the first try). A pour that has
    # to be a signal layer is not a plane. GND is routed as a track like every
    # other net; at 40 mm with a metre of cable either side, a plane on this
    # board buys nothing the track does not.
    # NO LONGER a screw beside the board: the ear carries a real through-hole, so
    # hold_edge is gone and the cradle's job is locating, not gripping.
    "mounting_hole_xy": (_EAR_X1 - EAR_W / 2.0, _HL - EAR_H / 2.0),
    "single_sided": True,
    "tail_band_from_plus_y": BOARD_L / 2.0 - ROW_Y,   # 6.0, against a 6.4 limit
    # ⚠ THIS READ 9 AND THE INSTRUMENT HAS 10. It has been 9 since the board was reshaped
    # to 40 x 16, through the tee purpose being corrected and through tee 10's deletion,
    # and neither moved it -- a hand-typed count in the file that ORDERS THE BOARDS, one
    # short. One tee per motor is the board's whole definition ("a tee board exists to
    # give a MOTOR power and CAN", which is why tee 10 went: it served none), so it is
    # now the motor count and not a number.
    "qty_per_instrument": _TEE_QTY,
}


# ── TWO CHECKS THIS FILE WAS MISSING ─────────────────────────────────────────
# ⚠ THE TAIL BAND WAS PRINTED, NOT CHECKED, AND THE COMMENT BESIDE IT SAID 4.0.
# The value is 6.0. The through-hole tails have to land on the faceplate wall's
# 6.4 mm strip -- everything -Y of that overhangs the motor and there is nothing
# under it -- so the real margin is 0.4 mm, not the 2.4 the comment implied. Six
# times tighter than it read. A number that close to its limit gets an assertion,
# not a print: a print is only seen by whoever happens to be reading the run.
WALL_STRIP = 6.4        # faceplate wall depth -- the only support under this board
assert BOARD_NOTES["tail_band_from_plus_y"] <= WALL_STRIP, (
    "the THT tail band sits %.2f mm from the +Y edge and the faceplate wall is only "
    "%.2f deep -- the tails would hang over the motor with no support"
    % (BOARD_NOTES["tail_band_from_plus_y"], WALL_STRIP))

# ⚠ AND SIX NUMBERS ARE TYPED TWICE, ONCE HERE AND ONCE IN src/dimensions.py. The CAD
# cuts the motor bay's seat from ITS copy; this file fabs the board from this one. They
# agree today, and nothing anywhere would notice if they stopped: the netlist does not
# know the board's outline, DRC compares copper to the netlist, and the overlap gate
# reads one file at a time. elec/cad_geom_check.py catches exactly this for output_panel
# and motor_ctrl -- it cannot reach this board, because the CAD keeps no connector
# anchor table for the tee. (optical and lever_sensor need no check at all: their CAD is
# GENERATED from the board, one source, not two copies.) So the check lives here.
def _check_against_cad():
    from src import dimensions as D
    for name, mine, theirs in (
            ("board X", BOARD_W, D.TEE_BOARD_X),
            ("board Y", BOARD_L, D.TEE_BOARD_Y),
            ("ear X", EAR_W, D.TEE_EAR_X),
            ("ear Y", EAR_H, D.TEE_EAR_Y),
            ("fabbed outline X", BOARD_OUTLINE_W, D.TEE_OUTLINE_X),
            ("tail row Y", ROW_Y, D.TEE_TAIL_CY)):
        assert abs(mine - theirs) < 1e-9, (
            "%s: elec/can_tee.py says %.3f, src/dimensions.py says %.3f -- the fabbed "
            "board and the seat cut for it would not match" % (name, mine, theirs))


_check_against_cad()


if __name__ == "__main__":
    can_tee(tag="tee")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "can_tee.net"))
    netcheck.grounds_meet(os.path.join(OUT_DIR, "can_tee.net"))
    netcheck.no_orphan_pins(os.path.join(OUT_DIR, "can_tee.net"))
    with open(os.path.join(OUT_DIR, "can_tee.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, tails %.1f mm from the +Y edge (limit 6.4)"
          % (BOARD_W, BOARD_L, BOARD_NOTES["tail_band_from_plus_y"]))
