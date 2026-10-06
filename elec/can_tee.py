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

import harness                                      # noqa: E402
import netcheck                                     # noqa: E402

# ── the harness contract ─────────────────────────────────────────────────────
# Four conductors, colours the user's: black GND / red 24V / yellow CAN_H /
# green CAN_L. The pin ORDER is the board's half of that contract and is the SAME
# on every connector in the instrument, so one crimp order serves all of them.
# The pin order lives in harness.py -- see the note there for why it is not
# allowed to have a second copy.
XH_PINOUT = harness.XH_PINOUT

# 120 R, 1%. ISO 11898 wants 120 ohm at each END of the trunk and nowhere else,
# so every board carries the resistor behind a switch that ships OFF; the one that
# lands at the bus end gets its slid to ON. One layout, one BOM, one assembly file
# for all ten -- populating R1 on only one would mean two JLCPCB variants.
TERM_OHMS = "120R"

# SPLIT TERMINATION (2x 60R + 4.7nF to GND) is the textbook EMC answer and is
# deliberately NOT used: it buys common-mode filtering that matters on a metres-
# long vehicle harness, and this trunk is ~1 m inside a plastic instrument. It
# would also put a capacitor's return current on the same GND the optical
# pickup's analog reference rides.


@subcircuit
def can_tee():
    """Trunk in and out through one 8-way, the motor on its own 4-way, and the
    terminator behind its switch."""
    gnd, v24 = Net("GND"), Net("+24V")
    can_h, can_l = Net("CAN_H"), Net("CAN_L")
    for n in (gnd, v24, can_h, can_l):
        n.drive = Pin.drives.POWER

    j1 = Part(name="B8B-XH-A", ref_prefix="J", tag="J1", dest="NETLIST", tool="skidl",
              value="S8B-XH-A", description="CAN trunk: in 1-4, out 5-8 (LCSC C157914)",
              footprint="Connector_JST:JST_XH_S8B-XH-A_1x08_P2.50mm_Horizontal",
              pins=[Pin(num=i + 1, name=n, func=Pin.types.PASSIVE) for i, n in enumerate(
                  harness.xh_trunk_pins())])
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
    # A SWITCH, placed by the fab: which tee ends the bus is chosen with a toothpick,
    # not an iron (user rule: no hand soldering anywhere on the instrument). Not a
    # shunt on a header either: a 2.54 shunt is taller than everything here bar the
    # connectors, and one that falls off is a bus that fails intermittently. A slide
    # DIP switch is detented, 2.3 mm tall and has nothing to lose.
    # DSHP01TSGER (LCSC C3293141): 1 position, SPST, recessed slide, gull wing, body
    # 5.4 x 2.88, lands 0.76 x 1.27 on 7.62 centres (elec/footprints/Steel.pretty, drawn
    # from the maker's sheet). 25 mA at 24 V switching, 100 mA carrying;
    # the terminator passes 17 mA at a 2 V dominant bit and is never switched live.
    sw1 = Part(name="SW_DIP_x01", ref_prefix="SW", tag="SW1", dest="NETLIST",
               tool="skidl", value="DSHP01TSGER",
               description="bus A terminator: ON on the LAST tee only (LCSC C3293141)",
               footprint="Steel:Kangshen_DSHP01TSGER",
               pins=[Pin(num=1, func=Pin.types.PASSIVE), Pin(num=2, func=Pin.types.PASSIVE)])
    term = Net("TERM_MID")
    can_h += r1[1]
    term += r1[2], sw1[1]
    can_l += sw1[2]


# 40 x 16. The connector row is 36.98 of courtyard, so 40 leaves a full 1.0 mm
# component-to-edge margin at both ends AND stays inside the 40.5 that lets the
# seat have locating walls on BOTH X edges -- at 42 only +X could be located, the
# -X side having 1.65 mm before the neighbouring motor's body.
BOARD_W, BOARD_L = 40.0, 16.0
# The terminator's two parts, in the strip behind the connector bodies.
R1_X, R1_Y = -10.5, 6.2
SW_X, SW_Y = 1.0, 6.30
SW_BODY = (5.4, 2.88, 0.3)               # along the leads, across them, +/- on the latter
SW_LAND_SPAN = 8.89                      # outer end to outer end of the two lands
XH_BACK = 2.3                            # header body behind its pin row (JST eXH.pdf)
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

BAR_Y, BAR_W, STUB_W = -1.5, 2.0, 1.5
# pad x of each rail's three lands, off the footprints: J1 at -7.0 spans 8 ways about its
# centre, J2 at 11.7 spans 4, both on 2.50 pitch
_J1_X0, _J2_X0, _PITCH = -7.0 - 3.5 * 2.5, 11.7 - 1.5 * 2.5, 2.5


def _power_copper():
    out = []
    for net, layer, way in (("GND", "B.Cu", 0), ("+24V", "F.Cu", 1)):
        xs = [_J1_X0 + way * _PITCH, _J1_X0 + (way + 4) * _PITCH, _J2_X0 + way * _PITCH]
        out.append((net, layer, BAR_W, [(xs[0], BAR_Y), (xs[-1], BAR_Y)]))
        for x in xs:
            out.append((net, layer, STUB_W, [(x, BAR_Y), (x, ROW_Y)]))
    return out


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
        # both connector courtyards cover y -7.74..+4.85 of a 16 mm board, so the
        # terminator pair lives in the strip above them, the switch lying along X.
        # THE SWITCH IS THE ONE PART INSIDE THE 1.0 mm EDGE MARGIN, and by measurement.
        # The headers' courtyard ends at y +4.85 (their BODY at +4.30: pin row + 2.3,
        # JST's drawing). The switch body is 2.88 +/- 0.3 across, so at SW_Y it spans
        # 4.86..7.74: its edge on the headers' courtyard line, 0.56 from their bodies
        # and 0.26 from the board edge -- 0.41 and 0.11 at the widest body the drawing
        # allows. Its LANDS (0.76 across) are 1.32 from the edge, and copper is what the
        # fab's edge rule measures. The seat wall stands 0.3 outside the board, so the
        # body is 0.4 from plastic at its widest. _strip_check() holds all of it.
        "R1": (R1_X, R1_Y, 0.0),
        "SW1": (SW_X, SW_Y, 0.0),
    },
    "ref_pos": {"J1": (-17.5, 6.4), "J2": (17.0, 6.4),
                "R1": (-14.0, 6.2), "SW1": (10.5, 6.4)},
    "silk_labels": {"SW1": "TERM"},
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
    # ⚠ THE TRUNK'S POWER IS DELIBERATE COPPER NOW, AND IT WAS THE WEAKEST LINK ON BUS A
    # (measured 2026-09-30 on the routed board). The router laid +24V from trunk-in to
    # trunk-out as 27.9 mm of the 0.25 mm default: ~55 mOhm per rail per tee against
    # ~2.4 mOhm for the 45 mm of 22 AWG between tees, rated ~0.88 A, and there are ten in
    # series carrying up to half the fleet from each end. The 3 A contact everyone worried
    # about was never the limit; this was. No netclass can fix it -- freerouting will not
    # choose a path for its resistance -- so the two rails are laid here:
    #   a 2.0 mm BAR under the connector bodies at y BAR_Y, +24V on F.Cu and GND on B.Cu,
    #   and a 1.5 mm stub up to each through-hole pad (1.7 wide, so the stub fits inside it
    #   and leaves 0.90 to the neighbouring pads). 1.5 because the quality pass measured the
    #   first 1.2 as a choke: 3 A (the XH contact rating) wants 1.37 mm at a 10 C rise.
    # ~5 mOhm per rail per tee. CAN keeps the +Y strip and both layers above the pad row.
    "tracks": _power_copper(),
    "frozen_nets": ("+24V", "GND"),
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
    # ── THE QUALITY RECORD (cadkit/PCB_QUALITY.md) ───────────────────────────────────
    # Each line says what it was checked AGAINST. A rule that is not here is OPEN, and
    # the reason it is open is in docs/pcb-quality-status.md.
    "quality": {
        # 3 A is the XH contact's rating and therefore the most the trunk may ever be
        # asked to pass; the budget case is 2.7 A (BOM.md, dual feed 54 / 46 at < 5 A).
        # The drop is one motor, 1-1.5 A input; declared at the same 3 A so the stub is
        # sized for the contact, not the load.
        "power_paths": [
            {"net": "+24V", "from": "J1.2", "to": ["J1.6", "J2.2"], "amps": 3.0},
        ],
        # A13 (cadkit/PCB_QUALITY.md): what the DESIGN leaves open, and how many nets each
        # repeated structure is on. The pass fails on any difference from the routed board.
        "unconnected": {},
        "net_groups": [
            {
                "name": "trunk in, trunk out and the motor drop are one bus, way for way",
                "pins": [
                    "J1.[1-8]",
                    "J2.[1-4]"
                ],
                "nets": 4,
                "each": 3
            }
        ],
        "pinouts": {
            "S8B-XH-A": "JST eXH.pdf p.5, Header / Side entry type, <3 circuits or more>: "
                        "seen from above with the mouth pointing away, No. 1 circuit is the "
                        "RIGHT-hand post. KiCad JST_XH_S8B-XH-A pad 1 is at the origin with "
                        "the body toward +Y and pads 2-8 toward +X -- the same end. Ways "
                        "bound from harness.xh_trunk_pins(), read 2026-10-04",
            "S4B-XH-A": "JST eXH.pdf p.5, same drawing and same view as the 8-way: No. 1 "
                        "circuit is the right-hand post seen from above, mouth away; KiCad "
                        "JST_XH_S4B-XH-A pad 1 at the origin, 2-4 at +2.5 / +5.0 / +7.5. "
                        "Ways bound from harness.XH_PINOUT, read 2026-10-04",
        },
        "manual": {
            "M3": "done: GND is the same copper as +24V by construction -- _power_copper() "
                  "lays both rails from one loop, a 2.0 mm bar plus a 1.5 mm stub per pad, "
                  "GND on B.Cu directly under +24V on F.Cu. No via and no plane slot in "
                  "either; no analog reference on this board",
            "M4": "no capacitor, no regulator and no load on this board: both rails pass "
                  "between connectors (A2 reports the same). The bulk for the motor's "
                  "current step is on the SERVO42D itself, which this board does not own",
            "M5": "voltage: the only parts on +24V are JST XH headers, 250 V (eXH.pdf p.1). "
                  "R1 sits across CAN_H / CAN_L only: a dominant bit is ~2 V differential, "
                  "33 mW in 120 R against 100 mW for an 0603. Contact CURRENT is M33",
            "M9": "decision: no test pads. There is no MCU, and all four nets are on "
                  "through-hole posts whose tails stand 3.4 mm proud on the back -- a "
                  "probe or clip lands on any of twelve of them, GND included",
            "M10": "decision: no TVS and no reverse-polarity part here. Both connectors are "
                   "inside the instrument and mate only to its own harness; XH is polarised "
                   "so the plug cannot be reversed; the trunk's clamp is D6 (SMAJ30A) on "
                   "the output panel, at the 24 V inlet, and each CAN transceiver board "
                   "carries its own bus protection",
            "M11": "finish.py: 4 / 4 routed parts present in the CAD, every one where the "
                   "CAD draws it. Mated height: XH side header 7.0 mm against 8.3 mm worst "
                   "headroom (docs/can-tee-power-tap.md, measured per tee). Tails: asserted "
                   "above, 6.0 of a 6.4 mm wall strip. Screw: the ear is bare laminate -- "
                   "no track reaches past x +15.5 and the ear starts at +20 -- so an M4 "
                   "button head (7.6 dia) on the 9.5 x 8.7 ear touches no copper on either "
                   "face. Mouths face -Y into free air over the motor. SW1 stands 2.5 mm in the strip "
                   "behind the header bodies (7.0): measured clearances are at its placement, "
                   "and it is reached from above with the plugs in",
            "M16": "decision: nothing to damp. The board has no capacitor, so a live plug "
                   "rings into nothing here; the ring is a property of the inputs that DO "
                   "have ceramics (motor driver, motor_ctrl J3) and is signed on those",
            "M20": "R1 = 120 R 1 % behind SW1, ON on the LAST tee only and OFF on the other nine; "
                   "the other end of bus A "
                   "is motor_ctrl's own 120 R, wired in permanently (motor_ctrl.py, 'TERMINATION -- "
                   "BUS A ONLY'). Two terminations, at the two ends. Stub per node is the motor "
                   "pigtail; no clock on this board",
            "M28": "the placed parts are JST S8B-XH-A(LF)(SN) C157914 and S4B-XH-A(LF)(SN) "
                   "C157925 -- JST's own, so the pinout cited above IS the exact part's. "
                   "R1 is an unpolarised two-pad part. SW1 is DSHP01TSGER C3293141, a single "
                   "SPST: either way round it is the same circuit, and the body prints ON "
                   "at the end that closes it (maker's drawing DSHP-001-S-A, read "
                   "2026-10-06: lands 0.76 x 1.27 at 6.35 inside / 8.89 outside, the "
                   "footprint's 7.62 centres; the footprint is drawn from that sheet, "
                   "Steel:Kangshen_DSHP01TSGER)",
            "M29": "A12 measures the board against JLCPCB's capability page, read "
                   "2026-10-04 (2-layer, 1 oz, standard service): all pass. No SMD pad has "
                   "a via in or touching it: the board's one via is beside a through-hole "
                   "post. R1 has one track on each pad and there is no pour, so its two "
                   "pads see the same copper",
            "M31": "name and revision 'CAN TEE r1' on the back at 1.5 mm; both connectors' "
                   "pin names on the back beside their tails; SW1 says TERM on the front, "
                   "beside its designator, and the switch body itself prints ON; J1 / J2 designators and the footprints' pin-1 "
                   "marks are in the strip behind the bodies, outside them. All text is "
                   "1.0 mm x 0.15 or larger (A12)",
            "M32": "footprint pitch read from the KiCad file: 2.50 (pads at 0 / 2.5 / 5.0 / "
                   "7.5), XH's pitch, and the 8-way spans 17.5 = JST's dimension A for 8 "
                   "circuits. Contact 3 A at AWG 22 (eXH.pdf p.1). Pad 1 against the JST "
                   "drawing: see pinouts. Every connector carries GND on way 1 (and 5)",
            "M34": "no active part. CAN_H lands on way 3 and CAN_L on way 4 of every "
                   "housing from one constant (harness.XH_PINOUT), so H meets H and L "
                   "meets L by construction; R1 + SW1 bridge H to L and nothing else",
            "M38": "no ceramic capacitor on the board. R1 (0603) lies along X, parallel to "
                   "the +Y edge 1.8 mm away, 35 mm from the screw. SW1 is a moulded "
                   "switch on two gull-wing leads, not a ceramic. No V-score: routed "
                   "outline. Plugs enter from -Y over the motor (see M11). The mounting "
                   "hole is unplated and has no copper round it: deliberately isolated",
            "M41": "SW1 is not read by anything: it puts R1 across the pair or does not, "
                   "is set once when the harness is built and never moved with the bus live. "
                   "Nothing to debounce",
            "M40": "120 R is an E24 value. R1 is the only part chosen for a parameter (bus "
                   "termination, 1 %) and its description says so. Nothing needs a heatsink",
        },
    },
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



def _strip_check():
    """The switch against the two things either side of it, at its widest body."""
    half = (SW_BODY[1] + SW_BODY[2]) / 2.0
    back = ROW_Y + XH_BACK
    to_header = (SW_Y - half) - back
    to_edge = BOARD_L / 2.0 - (SW_Y + half)
    assert to_header >= 0.25 and to_edge >= 0.10, (
        "the terminator switch no longer fits its strip: %.2f mm to the header bodies, "
        "%.2f mm to the +Y edge at the widest body the drawing allows (want 0.25 / 0.10)"
        % (to_header, to_edge))
    assert SW_Y - SW_BODY[1] / 2.0 >= ROW_Y + 2.85, "the switch is in the headers' courtyard"
    gap = (SW_X - SW_LAND_SPAN / 2.0) - (R1_X + 0.83 + 0.25)
    assert gap >= 0.5, "R1 and the switch's land are %.2f mm apart" % gap
    assert SW_X + SW_LAND_SPAN / 2.0 <= BOARD_W / 2.0 - 1.0
    return to_header, to_edge


_strip_check()

# ⚠ AND TWELVE NUMBERS ARE TYPED TWICE, ONCE HERE AND ONCE IN src/dimensions.py. The CAD
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
            ("tail row Y", ROW_Y, D.TEE_TAIL_CY),
            ("terminator R1 X", R1_X, D.TEE_TERM_R[0]),
            ("terminator R1 Y", R1_Y, D.TEE_TERM_R[1]),
            ("terminator switch X", SW_X, D.TEE_TERM_SW[0]),
            ("terminator switch Y", SW_Y, D.TEE_TERM_SW[1]),
            ("terminator switch length", SW_BODY[0], D.TEE_TERM_SW[2]),
            ("terminator switch width", SW_BODY[1], D.TEE_TERM_SW[3])):
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
