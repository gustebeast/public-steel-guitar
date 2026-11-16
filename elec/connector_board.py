"""Connector board -- every field cable of the direct-drive instrument lands here. x1.

    py -3.12 elec/connector_board.py       # -> elec/out/connector_board.{net,board.json}

A NEW BOARD (user, 2026-11-13): "the brain board becomes the brain board ... The motors, pedal
bus, lever bus, fret LED and floor LED all connect to the connector board. The connector board
goes in the +y -x corner and puts its connectors facing +z." It is PASSIVE: one 2 x 15 1.27 mm
IDC ribbon (harness.CONN_RIBBON) to the brain (brain_board.py J240), and

  * TEN 4-WAY SCREW TERMINALS for the motors (user, 2026-11-13: "it saves a bunch of crimping and
    the motor already uses screw terminals"). 3.5 mm pitch, M2 slotted screws: the SAME 2.0 mm
    flat blade as the SERVO42D's own terminals ([[fastener-single-tool]] exception), so one
    screwdriver does both ends of a motor lead. Ways in harness.XH_PINOUT order (V24, GND,
    CAN_H, CAN_L) -- the motor end's order is an open item.
  * bus A, the motors' CAN, as a LINE along the terminal row: the brain's transceiver is one end
    (its 120R, R205, is there) and THIS board's far terminal the other (R1 here), with the clamp.
  * ONE PH4 for the pedal arm, ONE PH4 for the lever arm (bus B: 5 V + CAN, or the CM5's flash
    lane when the brain's switch says so), each with its ESD clamps and bulk at the header.
  * ONE 4-way terminal for the fret LEDs, ONE for the floor LEDs (fused 24 V + clock / data):
    the SAME pluggable screw terminal as the motors (user, 2026-11-14: "they are easier to
    install and can still be plugged/unplugged easily ... treat these plug style screw
    terminals as preferred where space allows"). The LED boards' own inputs may stay JST.
    One family for both means a motor lead fits an LED header: the power ways agree (V24,
    GND) and CAN meets SCK / SDT -- no damage at those levels, but the leads are labelled.

FLAT ON THE FLOOR, component side up (branner, 2026-11-13): free box x -610..-448 (to -621.7 this
low: the keyhead nut prism only reaches down to z -64.8), y 27..65, ~100 mm open above. So the
terminals are ordinary HORIZONTAL-entry blocks with their screws straight up, and they need not
line the edge (user, 2026-11-13: "we can still put them in the middle as long as there is enough
space for the wires to come out and bend up"): each keeps 12 mm clear in front of its mouth for
the wires' bend, and the placer turns them freely. PLUGGABLE since 2026-11-14 (MAX MX15EDGRC +
MX15EDGK): the mated plug runs 10.6 past the header's front, so the stroke is 10.6 + the 12 mm
bend, and its two M2 screws face +Z -- a 2.0 mm blade reaches them straight down only under
open sky, i.e. NOT at board x < -73.45 (the keyhead nut prism, ~41 mm above the face there). The JSTs are top entry. Frame: board x =
instrument x + 535.35, board y = instrument y - 46.0. One M4 into a floor boss (branner) -- its
x / y go to him once placed. Motor leads: 0.4 m for motors 1, 6, 7 (or 0.4 for all: one SKU).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = (os.environ.get("CONNECTOR_OUT")
           or os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

from skidl import ERC, Net, Part, Pin, generate_netlist  # noqa: E402

import harness                                      # noqa: E402
import netcheck                                     # noqa: E402

P = Pin.types.PASSIVE
C0402, C0805, C1206 = ("Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0805_2012Metric",
                       "Capacitor_SMD:C_1206_3216Metric")
R0603 = "Resistor_SMD:R_0603_1608Metric"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
# J11-J20 PLUGGABLE (lead, 2026-11-14): KF350-3.5-4P had zero stock, so a 3.5 mm pluggable 4-way
# with BOTH halves stocked -- MAX MX15EDGRC-3.5-04P header (C5188297, 8,523) + MX15EDGK-3.5-04P
# plug (C5188251, 9,319; M2 SLOTTED screw, the -Y suffix: the same 2.0 mm blade). 300 V / 8 A
# each (UL, both drawings). The land is Phoenix MC 1,5/4-G-3,5's at MAX's 1.40 mm hole; the
# courtyard carries the mated plug, 17 mm in front of the pin row
TB4 = "Steel:MAX_MX15EDGRC-3.5-04P_1x04_P3.50mm_Horizontal_Mated"
# TOP ENTRY: the board lies flat on the floor, mouths up (+Z), ~100 mm free above (branner 11-13)
PH4_TOP = "Connector_JST:JST_PH_B4B-PH-SM4-TB_1x04-1MP_P2.00mm_Vertical"
RIBBON = "Connector_PinHeader_1.27mm:PinHeader_2x15_P1.27mm_Vertical_SMD"


def _part(tag, name, value, desc, fp, pins):
    return Part(name=name, ref_prefix=tag.rstrip("0123456789"), ref=tag, tag=tag,
                dest="NETLIST", tool="skidl", value=value, description=desc, footprint=fp,
                pins=pins)


def _two(tag, value, desc, a, b, fp, prefix="C"):
    p = _part(tag, prefix, value, desc, fp, [Pin(num=1, func=P), Pin(num=2, func=P)])
    a += p[1]
    b += p[2]
    return p


def _ways(tag, value, desc, fp, ways, nets, power, mp=False):
    """A connector in the harness standard: each way to the net its NAME maps to."""
    harness.check_ways(ways, power, ("GND", harness.NC), where=tag)
    pins = [Pin(num=i + 1, name=n, func=P) for i, n in enumerate(ways)]
    if mp:
        pins.append(Pin(num="MP", name="MP", func=P))
    j = _part(tag, value, value, desc, fp, pins)
    for i, n in enumerate(ways):
        nets[n] += j[i + 1]
    if mp:
        nets["GND"] += j["MP"]
    return j


def connector_board():
    n = {k: Net(k) for k in ("GND", "+24V", "+24V_LED", "CANA_H", "CANA_L", "PED_H", "PED_L",
                             "LEV_H", "LEV_L", "+5V_PED", "+5V_LEV", "SCK", "SDT", "SCK_FOOT",
                             "SDT_FOOT")}
    for k in ("GND", "+24V", "+24V_LED", "+5V_PED", "+5V_LEV"):
        n[k].drive = Pin.drives.POWER
    gnd, v24, v24l = n["GND"], n["+24V"], n["+24V_LED"]

    # ── J1: the ribbon from the brain (brain_board.py J240), the same way order ─────────
    rib = {"V24": v24, "V24L": v24l, "GND": gnd, "CANA_H": n["CANA_H"], "CANA_L": n["CANA_L"],
           "PED_H": n["PED_H"], "PED_L": n["PED_L"], "LEV_H": n["LEV_H"], "LEV_L": n["LEV_L"],
           "V5_PED": n["+5V_PED"], "V5_LEV": n["+5V_LEV"], "SCK": n["SCK"], "SDT": n["SDT"],
           "SCK_FOOT": n["SCK_FOOT"], "SDT_FOOT": n["SDT_FOOT"]}
    harness.check_ways_2row(harness.CONN_RIBBON, ("V24", "V24L", "V5_PED", "V5_LEV"), where="J1")
    _ways("J1", "PZ1.27-2x15P ZZ", "the brain ribbon, 30-way 1.27 mm 2x15 IDC "
          "(harness.CONN_RIBBON; LCSC open item)", RIBBON, harness.CONN_RIBBON, rib,
          power=("V24", "V24L", "V5_PED", "V5_LEV"))
    _two("C1", "22uF/50V", "ribbon 24 V bulk at J1 -- the brain's F204 / C322 are 0.3 m away; "
         "50 V on a 24 V rail (the 35 V 1210 sat at 75 %)", v24, gnd, "Capacitor_SMD:C_2220_5750Metric")

    # ── J11-J20: the ten motors, screw terminals, bus A in a line along them ────────────
    for k in range(10):
        _ways("J%d" % (11 + k), "MX15EDGRC-3.5-04P", "motor %d (string %d) -- SERVO42D: 24 V + bus A, "
              "3.5 mm pluggable header; its MX15EDGK plug takes the wires on M2 slotted screws (2.0 mm "
              "blade, as the motor's own)" % (k + 1, k + 1),
              TB4, harness.XH_PINOUT,
              {"V24": v24, "GND": gnd, "CAN_H": n["CANA_H"], "CAN_L": n["CANA_L"]}, power=("V24",))
    # the row's far end: the bus's second 120R (the first is at the brain's transceiver)
    _two("R1", "120R", "bus A termination at the FAR end of the motor row (past J20), 1%",
         n["CANA_H"], n["CANA_L"], R0603, prefix="R")
    d1 = _part("D1", "NUP2105LT1G", "NUP2105LT1G", "bus A clamp: CAN_H and CAN_L to GND, 24 V "
               "stand-off (as the brain's D2 was)", SOT23, [Pin(num=i, func=P) for i in (1, 2, 3)])
    n["CANA_H"] += d1[1]
    n["CANA_L"] += d1[2]
    gnd += d1[3]
    # a 24 V HF return per neighbouring pair of motor terminals (the brain's C116-C121)
    for i, pair in enumerate(("J11 / J12", "J13 / J14", "J15 / J16", "J17 / J18", "J19 / J20")):
        _two("C%d" % (11 + i), "10uF/50V", "+24V bypass at motor terminals %s" % pair, v24, gnd, C1206)

    # ── J2 / J3: bus B, the pedal and lever arms (PH, 5 V) ───────────────────────────────
    for tag, h, l, v5, what, cb, d_h, d_l in (
            ("J2", "PED_H", "PED_L", "+5V_PED", "PEDAL", "C2", "D2", "D3"),
            ("J3", "LEV_H", "LEV_L", "+5V_LEV", "LEVER", "C3", "D4", "D5")):
        _ways(tag, "B4B-PH-SM4-TB", "bus B, the %s arm -- 5 V PH, top entry, mouth up (+Z)" % what,
              PH4_TOP, harness.PH_PINOUT,
              {"V5": n[v5], "GND": gnd, "CAN_H": n[h], "CAN_L": n[l]}, power=("V5",), mp=True)
        _two(cb, "10uF/16V", "%s arm bulk at %s" % (what.lower(), tag), n[v5], gnd, C0805)
        for dt, net in ((d_h, n[h]), (d_l, n[l])):
            d = _part(dt, "ESD5B5.0ST1G", "ESD5B5.0ST1G", "bus B ESD clamp, arm pin to GND "
                      "(LCSC C93623)", "Diode_SMD:D_SOD-523", [Pin(num=1, func=P), Pin(num=2, func=P)])
            net += d[1]
            gnd += d[2]

    # ── J4 / J5: the lights (fused 24 V at the brain, F203), the motors' pluggable terminal ──
    _ways("J4", "MX15EDGRC-3.5-04P", "to fret_led_key J1 -- 24 V and SPI (harness.LED_DROP); 3.5 mm "
          "pluggable header, its MX15EDGK plug takes the wires on M2 slotted screws", TB4,
          harness.LED_DROP, {"V24": v24l, "GND": gnd, "SCK": n["SCK"], "SDT": n["SDT"]},
          power=("V24",))
    _ways("J5", "MX15EDGRC-3.5-04P", "to foot_led_a J1 -- 24 V and SPI (harness.LED_DROP); 3.5 mm "
          "pluggable header, its MX15EDGK plug takes the wires on M2 slotted screws", TB4,
          harness.LED_DROP, {"V24": v24l, "GND": gnd, "SCK": n["SCK_FOOT"], "SDT": n["SDT_FOOT"]},
          power=("V24",))
    _two("C4", "10uF/50V", "lighting 24 V bulk at J4 / J5", v24l, gnd, C1206)


BOARD_NOTES = {
    # the mated MX15EDGRC + MX15EDGK pair, 11.10 tall (MAX drawings): the placer's height zones
    "part_heights": {"J%d" % k: 11.1 for k in list(range(11, 21)) + [4, 5]},
    # THREE ROWS, NARROWER AND DEEPER (user, 2026-11-15): "keep the -x end where it is and extend
    # out to the 5th row of screw terminals ... the rest ... move -y of the second row": five
    # motor terminals, five more, then the two LED terminals with the ribbon, the arms and the
    # passives -- every mouth -Y. 99.05 x 79.1 sits in the board house's <= 100 x 100 price
    # tier (172.7 x 37 did not). And -Y, off the floor LED board (its -Y edge at y 31.05), the
    # storage now being a cubby in the top panel: instrument x -621.7..-522.65, y -49.1..30.0
    # PROPOSED -- branner checks the floor there (motors, the nut prism, the cable path).
    "outline_mm": (99.05, 79.1),
    "frame": {"instrument_x": "board x - 572.175", "instrument_y": "board y - 9.55",
              "underside_z": -102.2, "faces": "+Z", "by": "branner 2026-11-13 / 2026-11-15"},
    # ⚠ LIFTED 5.0 ON ITS M4 BOSS (branner's floor check 2026-11-15): the inner floor is flat
    # at z -107.236, so at -107.2 the THT tails had nowhere to go. The longest tail is the
    # MX15's (J1 / J2 / J3 are SMD): ESTIMATED <= 4.0 under the board (MAX's drawing could
    # not be read -- open item), + 1 mm = underside -102.2. Top of the mated MX15 then
    # z -89.5 against the lowest strings' -86.2 (3.3 clear); the nut prism (bottom -64.18)
    # and motor_driver_4 over the +X end (z -80) are higher still.
    # THE M4: one hole at board (0, -18.95) -- instrument (-572.175, -28.5), the free spot
    # nearest branner's centroid: the middle of row 2's wire-bend band (no part there; a
    # 3 mm pan head sits under where the wires turn up). head_d 9: an M4 washer; tracks and
    # vias kept from under it on the top face (layout cutouts).
    # THE SCREW: M4 x 6 ISO 7380 button head (the one 2.5 mm hex key) with an ISO 7089 washer
    # (0.8). The boss's heat-set pocket is 5 deep and bottoms on the floor, so the shank may
    # reach 5 below the underside at most: L <= 0.8 + 1.6 + 5 = 7.4; the stock lengths are 6
    # and 8, so 6 -- 3.6 mm in the insert (0.9 d).
    "cutouts": [{"xy": (0.0, -18.95), "d": 4.5, "head_d": 9.0, "head_side": "front"}],
    "mount_screw": "M4 x 6 ISO 7380 button head (2.5 mm hex) + ISO 7089 M4 washer into the boss's heat-set (branner)",
    "layers": 2,
    # ⚠ GND ON BOTH LAYERS, STITCHED (d8, 2026-11-15): with +24V declared at 4 A its 2 mm
    # tracks crossed the B.Cu pour and cut it into four islands (3 unconnected), and B.Cu was
    # the only GND. A second pour on F.Cu round the signals, joined to B.Cu by a stitch via
    # at every GND pad, keeps each island tied and gives CAN on F.Cu its own reference.
    "zones": [("GND", "F.Cu", 0.3), ("GND", "B.Cu", 0.3)],
    "stitch_nets": ("GND",),
    # ⚠ EACH CAN BUS IS A PAIR ON ONE LAYER (d5, 2026-11-15): undeclared, the router laid
    # CANA_H on F.Cu and CANA_L beside it on B.Cu, and L's track cut a 6.28 mm slot in the
    # GND pour right under H (quality A15). A CAN pair is differential: its two wires
    # side by side on one layer is what the transceivers' common-mode rejection assumes,
    # and it keeps B.Cu for the pour. Skew is not the constraint: 5 Mbit/s CAN FD is a
    # 200 ns bit, and 100 mm of mismatch is 0.6 ns (6 ps/mm in FR4), 0.3 % of it.
    # max_vias None: every drop is a through-hole terminal, a layer change is free at it.
    # PED and LEV are NOT held to one layer (d6): each is a 13-30 mm run from J1 to its PH,
    # and J1's 1.27 mm pin field lets PED_H out only by a 3 mm hop under its neighbours --
    # same_layer then fails the pair (A3) for a hop that cuts no plane anything crosses.
    # ⚠ AND CANA IS NOT HELD TO ONE LAYER EITHER (d11, 2026-11-15): its lands (D1, R1, J1) are
    # SMD on F.Cu, so same_layer pinned the whole pair to F.Cu -- and +24V, a 2 mm trunk that
    # is also on F.Cu, has to cross it at every row. The pair could not hop, so the trunk took
    # a single via at each crossing (six 0.67 mm barrels on a 4 A path, A1 CHOKE POINT). A
    # declared pair still routes coupled and hops TOGETHER; that is what keeps the plane
    # whole under it (d5's split was an UNDECLARED pair, H and L on opposite layers).
    "match": [{"name": n, "max_skew_mm": 100.0, "same_layer": False, "max_vias": None,
               "nets": [n + "_H", n + "_L"],
               "why": "CAN: a differential pair, side by side on one layer over the GND "
                      "pour; 100 mm skew is 0.6 ns of a 200 ns CAN FD bit"
                      + ("" if n == "CANA" else "; a short stub from J1, a hop to escape "
                         "J1's 1.27 mm pin field allowed")}
              for n in ("CANA", "PED", "LEV")],
    "quality": {
        # (J11 / J13's back_only went 2026-11-15: the motor plugs are lettered A-D on the
        # front now -- silk_ways, in the band in front of the header -- with a key)
        "connector_labels": {
            # J1 (d14 / d15): 30 ways at 1.27 mm take a two-column block 15 lines tall; the front
            # round J1 is J2 / J3, their clamps and C1, so the block goes on the back, behind
            # J1. Its way-1 mark is on the front (silk_pinout prints the block)
            "J1": {"back_only": "30 ways at 1.27 mm: the 15-line block has no room among J2 / J3, "
                                "their clamps and C1; printed behind J1, way-1 mark on the front"}},
        # A15: CAN is differential -- the return of CANA_H is CANA_L beside it, not the plane,
        # and a 5 Mbit/s CAN FD edge (tens of ns) sees an 11 mm slot as nothing. The cut it
        # crosses is the +24V row feed on B.Cu (d15), which has to run under the row
        "return_slot_ok": {
            "CANA_H": {"mm": 11.5, "why": "differential pair: the return is CANA_L beside it, routed "
                                          "coupled; the cut is the +24V row feed on B.Cu. A CAN FD "
                                          "edge (tens of ns) over 11 mm is no reflection"},
        },
        # A1 +24V_LED: declared at the brain's 3 A FUSE (F203), against 1.70 A with every zone
        # full white (docs/lighting-bus.md). One transition by J1 has two vias, 1.35 mm of
        # barrel against 1.37 needed at 3 A for a 10 C rise -- power_vias' third opened a GND
        # neck and was refused. At the real 1.70 A two barrels have 2x margin
        "waive": {
            "A1:+24V_LED J1.7>J4.1": "1.35 mm of via barrel against 1.37 at the 3 A fuse; the load "
                                      "is 1.70 A at full white (docs/lighting-bus.md), 2x margin; "
                                      "a third via opened a GND neck (power_vias, reported)",
            "A1:+24V_LED J1.7>J5.1": "the same two vias as J4: 1.35 against 1.37 at the 3 A fuse, "
                                      "1.70 A real (docs/lighting-bus.md)",
        },
        # A1. The motors' 24 V is FUSED AT THE BRAIN AT 4 A (brain_board F204, its power_paths
        # declare the ribbon's ways 1-4 at 4.0 A split), so 4 A is the most this bus can ever
        # carry and every +24V track is sized for it. Not 10 x 0.8 A = 8 A: the motor bus budget
        # is <= 5 A with slewing staggered by firmware (docs/can-tee-power-tap.md; the PSU is
        # 6.5 A for the whole instrument), and the fuse caps it lower still. The 0.8 A per
        # moving motor is the DERIVED budget, not a measured peak (measured 2026-11-12: +0.9 W
        # moving, +0.65 W holding, ~20x below it). Each drop is one motor: 0.8 A.
        "power_paths": (
            # the ribbon's four 24 V ways share the 4 A, 1 A each (a PZ1.27 contact is rated
            # 3 A: M32 read 4 A on J1.1 alone when the trunk was declared from it), and meet at
            # C1, the bulk cap beside J1; the trunk runs from there
            [{"net": "+24V", "from": "J1.%d" % w, "to": ["C1.1"], "amps": 1.0} for w in (1, 2, 3, 4)]
            + [{"net": "+24V", "from": "C1.1", "to": ["J%d.1" % k for k in range(11, 21)],
                "amps": 4.0, "split": True}]
            + [{"net": "+24V", "from": "C1.1", "to": ["J%d.1" % k], "amps": 0.8}
               for k in range(11, 21)]
            # the lights: fused 3 A at the brain (F203, ways 7-8); every zone full white is 1.70 A
            # (docs/lighting-bus.md), sized here to the fuse
            + [{"net": "+24V_LED", "from": "J1.7", "to": ["J4.1", "J5.1"], "amps": 3.0}]
            # each arm's 5 V: the brain's limiter on each (U206 / U211) is declared 0.5 A
            + [{"net": "+5V_PED", "from": "J1.19", "to": ["J2.1"], "amps": 0.5},
               {"net": "+5V_LEV", "from": "J1.22", "to": ["J3.1"], "amps": 0.5}]),
        # A13: nothing is left open; how many nets each repeated structure is on
        "unconnected": {},
        "net_groups": [
            {"name": "ten motor terminals on one bus, way for way (24 V, GND, CAN_H, CAN_L)",
             "pins": ["J1[1-9].[1-4]", "J20.[1-4]"], "nets": 4, "each": 10},
            {"name": "two LED drops: shared 24 V_LED and GND, each its own SCK / SDT",
             "pins": ["J[45].[1-4]"], "nets": 6},
            {"name": "two arms: shared GND, each its own 5 V and CAN pair",
             "pins": ["J[23].[1-4]"], "nets": 7},
        ],
        # A4: each multi-pin part's pin order, against its maker's document
        "pinouts": {
            "B4B-PH-SM4-TB": "JST ePH.pdf p.2, PC board layout (SMT type) / Top entry type, "
                             "viewed from the mounting surface: the signal row above the two "
                             "reinforcement tabs, No. 1 circuit the RIGHT-hand post (p.4 header "
                             "drawing, Mark of No. 1 circuit). KiCad JST_PH_B4B-PH-SM4-TB has the "
                             "tabs at -Y (MP y -1.75 against the row's +0.5) and pad 1 at x -3: "
                             "the same drawing turned 180 deg, the same post. Way names from "
                             "harness.PH_PINOUT. Read 2026-11-15",
            "NUP2105LT1G": "onsemi NUP2105L/D rev 5 p.1, SOT-23 pin drawing: 1 and 2 are the two "
                           "lines (identical halves, which is which is free), 3 the common. Board "
                           "(D1): 1 CANA_H, 2 CANA_L, 3 GND -- the same assignment as motor_ctrl "
                           "D2, read 2026-10-06. KiCad SOT-23 uses the JEDEC TO-236 numbering the "
                           "drawing does",
            "PZ1.27-2x15P ZZ": "HX PZ1.27 family drawing (as the brain's PZ1.27-2x8P ZZ, LCSC "
                               "C22438123, p.1): a plain straight two-row header, the maker "
                               "numbers nothing -- the numbering is the footprint's (KiCad "
                               "PinHeader_2x15_P1.27mm_Vertical_SMD: odd pads one row, even the "
                               "other, 1 / 2 at one end) and the way order is "
                               "harness.CONN_RIBBON, which the brain's J240 is built from too "
                               "(IDC ribbon: wire n = pin n)",
            "MX15EDGRC-3.5-04P": "MAX drawings MX15EDGRC-3.5-XXP / MX15EDGK-3.5-XXP (22.09.14), the "
                                 "sheets the Steel footprint cites: four identical posts at 3.5 mm "
                                 "in one row; a screw-terminal plug takes a bare wire at each "
                                 "position, so the way order is this board's and the harness's "
                                 "(harness.XH_PINOUT for the motors, LED_DROP for J4 / J5), the "
                                 "footprint's pad 1 at its -X end, printed on the board: each "
                                 "way's name in front of it and the way-1 dot (A17). The leads are "
                                 "wired to those words, not to a maker's number",
        },
    },
    # A17: J1's 30 ways named as a block (two columns, odd left, even right) -- 1.27 mm is too
    # fine for a word per way
    "silk_pinout": ["J1"],
    # ⚠ A MOTOR PLUG IS TOLD BY ITS MOTOR, ITS WAYS BY A LETTER (user, 2026-11-15): "MTR X next
    # to each plug saying which motor is which, then the individual ports can be labeled
    # A B C D with a key on the side showing what A B C and D mean". Ten identical plugs read
    # by net names were a wall of +24V / GND / CANA_H; the letters are the motor lead's own
    # (the SERVO42D end is wired to the same key).
    "silk_labels": {"J%d" % (11 + k): "MTR %d" % (k + 1) for k in range(10)},
    "silk_ways": {"J%d" % (11 + k): {1: "A", 2: "B", 3: "C", 4: "D"} for k in range(10)},
    # the key, at the -X margin between the two motor rows (board x 50.8 - 64, clear of parts)
    "silk_words": [("A 24V" + chr(10) + "B GND" + chr(10) + "C CAN H" + chr(10) + "D CAN L", 57.0, 80.0, "front")],
    # ⚠ THE REAR ROW'S WAY-1 MARK GOES IN FRONT OF PIN 1, UNDER THE PLUG (d5, 2026-11-15):
    # J11-J15 stand 0.1 mm from the +Y edge, so behind them there is no board, and their
    # neighbours' courtyards fill both sides -- J11-J14 got no mark at all (quality A17).
    # The band between the header's body and the plug's front is where a pin-1 dot is
    # read: it is seen whenever the plug is out, which is when the plug goes in. Every
    # MX15, for one rule across the rows.
    "silk_mark_in_body": {"J%d" % k: "MX15 mated: the pin-1 dot in front of the header, "
                                      "under the plug's overhang -- read whenever the plug is out"
                          for k in list(range(11, 21)) + [4, 5]},
    "qty_per_instrument": 1,
    "open_items": [
        "the M4 mount: PICKED 2026-11-15 at board (0, -18.95) = instrument (-572.175, -28.5); branner's boss is in (Ø9.3, top z -102.2, heat-set pocket 5 deep bottoming on the floor)",
        "MX15EDGRC tail length under the board: ESTIMATED <= 4.0 (the lift is 5.0) -- read MAX's drawing or measure a sample before the boss is printed",
        "PLACEMENT PROPOSED 2026-11-15 (user: three rows, moved -Y off the floor LED board): instrument x -621.7..-522.65, y -49.1..30.0, underside z -107.2 -- branner to confirm the floor is clear there (motors, the keyhead nut prism's y reach, the motor cable path) and pick the M4 boss",
        "WIRE ENTRIES: every mouth -Y; parts at instrument x < -608.8 (board x < -36.625: the keyhead nut prism, branner 11-13) stay under 41 tall and get no screw terminal (a 2.0 blade from +Z) -- IF the prism still reaches over the board's new y span (branner)",
        "J11-J20 wire entry side: the Phoenix PT-H footprint's entry assumed on its +Y (KiCad frame) -- check against the drawing before the mate rules are trusted",
        "motor leads: 0.4 m for motors 1, 6, 7 (branner's Manhattan runs to a board centred x -560 y 46); 0.4 for all = one SKU",
        "the SERVO42D's own 4-way terminal order -- match J11-J20's to it so a lead is straight across",
        "J11-J20 MX15EDGRC + MX15EDGK: the mated depth (16.5 mm from the pin row, 17 courtyard) and 11.1 height are read off two drawings, not a sample -- check one pair",
        "placement intent (not written yet), J11-J20 each: mate Jn L+Y 22.6 1.0 (the plug's 10.6 past the header + the 12 mm wire bend), access Jn top 6 (the M2 screws, a 2.0 mm blade from +Z), and the body at board x >= -73.45 (open sky: the nut prism is ~41 mm above the face beyond it)",
        "instrument model: the connector board is not in src/ yet -- once placed, the overlap gate needs it at its frame with BOARDS.solid(mated=True) (src/board_geom.SIDE_PLUG_RUN carries the plug) against the nut block, the endplates and the motor cable path",
        "J1 PZ1.27-2x15P ZZ: LCSC code and stock (the 2x8 is C22438123)",
        "J4 / J5 (LED leads) are the motors' MX15 family: label the leads -- a motor plug fits an LED header (power ways agree; CAN onto SCK / SDT, no damage)",
    ],
}


if __name__ == "__main__":
    connector_board()
    ERC()
    net_path = os.path.join(OUT_DIR, "connector_board.net")
    generate_netlist(file_=net_path)
    netcheck.no_orphan_pins(net_path)
    import volts_decl                   # A16: generated by voltage_check.py --declare connector_board
    volts_decl.into(BOARD_NOTES, "connector_board")
    with open(os.path.join(OUT_DIR, "connector_board.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("connector_board netlist written; %d open items" % len(BOARD_NOTES["open_items"]))
