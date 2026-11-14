"""Connector board -- every field cable of the direct-drive instrument lands here. x1.

    py -3.12 elec/connector_board.py       # -> elec/out/connector_board.{net,board.json}

A NEW BOARD (user, 2026-11-13): "the output board becomes the brain board ... The motors, pedal
bus, lever bus, fret LED and floor LED all connect to the connector board. The connector board
goes in the +y -x corner and puts its connectors facing +z." It is PASSIVE: one 2 x 15 1.27 mm
IDC ribbon (harness.CONN_RIBBON) to the brain (output_board.py J240), and

  * TEN 4-WAY SCREW TERMINALS for the motors (user, 2026-11-13: "it saves a bunch of crimping and
    the motor already uses screw terminals"). 3.5 mm pitch, M2 slotted screws: the SAME 2.0 mm
    flat blade as the SERVO42D's own terminals ([[fastener-single-tool]] exception), so one
    screwdriver does both ends of a motor lead. Ways in harness.XH_PINOUT order (V24, GND,
    CAN_H, CAN_L) -- the motor end's order is an open item.
  * bus A, the motors' CAN, as a LINE along the terminal row: the brain's transceiver is one end
    (its 120R, R205, is there) and THIS board's far terminal the other (R1 here), with the clamp.
  * ONE PH4 for the pedal arm, ONE PH4 for the lever arm (bus B: 5 V + CAN, or the CM5's flash
    lane when the brain's switch says so), each with its ESD clamps and bulk at the header.
  * ONE XH4 for the fret LEDs, ONE XH4 for the floor LEDs (fused 24 V + clock / data).

FLAT ON THE FLOOR, component side up (branner, 2026-11-13): free box x -610..-448 (to -621.7 this
low: the keyhead nut prism only reaches down to z -64.8), y 27..65, ~100 mm open above. So the
terminals are ordinary HORIZONTAL-entry blocks with their screws straight up, and they need not
line the edge (user, 2026-11-13: "we can still put them in the middle as long as there is enough
space for the wires to come out and bend up"): each keeps 12 mm clear in front of its mouth for
the wires' bend, and the placer turns them freely. The JSTs are top entry. Frame: board x =
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
TB4 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-4-3.5-H_1x04_P3.50mm_Horizontal"
# TOP ENTRY: the board lies flat on the floor, mouths up (+Z), ~100 mm free above (branner 11-13)
XH4_TOP = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
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

    # ── J1: the ribbon from the brain (output_board.py J240), the same way order ─────────
    rib = {"V24": v24, "V24L": v24l, "GND": gnd, "CANA_H": n["CANA_H"], "CANA_L": n["CANA_L"],
           "PED_H": n["PED_H"], "PED_L": n["PED_L"], "LEV_H": n["LEV_H"], "LEV_L": n["LEV_L"],
           "V5_PED": n["+5V_PED"], "V5_LEV": n["+5V_LEV"], "SCK": n["SCK"], "SDT": n["SDT"],
           "SCK_FOOT": n["SCK_FOOT"], "SDT_FOOT": n["SDT_FOOT"]}
    harness.check_ways_2row(harness.CONN_RIBBON, ("V24", "V24L", "V5_PED", "V5_LEV"), where="J1")
    _ways("J1", "PZ1.27-2x15P ZZ", "the brain ribbon, 30-way 1.27 mm 2x15 IDC "
          "(harness.CONN_RIBBON; LCSC open item)", RIBBON, harness.CONN_RIBBON, rib,
          power=("V24", "V24L", "V5_PED", "V5_LEV"))
    _two("C1", "22uF/35V", "ribbon 24 V bulk at J1 -- the brain's F204 / C322 are 0.3 m away",
         v24, gnd, "Capacitor_SMD:C_1210_3225Metric")

    # ── J11-J20: the ten motors, screw terminals, bus A in a line along them ────────────
    for k in range(10):
        _ways("J%d" % (11 + k), "KF350-3.5-4P", "motor %d (string %d) -- SERVO42D: 24 V + bus A, "
              "3.5 mm screw terminal, M2 slotted (2.0 mm blade, as the motor's own)" % (k + 1, k + 1),
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

    # ── J4 / J5: the lights (fused 24 V at the brain, F203) ─────────────────────────────
    _ways("J4", "B4B-XH-A", "to fret_led_key J1 -- 24 V and SPI (harness.LED_DROP), top entry", XH4_TOP,
          harness.LED_DROP, {"V24": v24l, "GND": gnd, "SCK": n["SCK"], "SDT": n["SDT"]},
          power=("V24",))
    _ways("J5", "B4B-XH-A", "to foot_led_a J1 -- 24 V and SPI (harness.LED_DROP), top entry", XH4_TOP,
          harness.LED_DROP, {"V24": v24l, "GND": gnd, "SCK": n["SCK_FOOT"], "SDT": n["SDT_FOOT"]},
          power=("V24",))
    _two("C4", "10uF/50V", "lighting 24 V bulk at J4 / J5", v24l, gnd, C1206)


BOARD_NOTES = {
    "outline_mm": (172.7, 37.0),         # instrument x -621.7..-449.0, y 27.5..64.5 (branner 11-13: -X 1 mm off the 22.23 keyhead slab at -622.67)
    "frame": {"instrument_x": "board x - 535.35", "instrument_y": "board y + 46.0",
              "underside_z": -107.2, "faces": "+Z", "by": "branner 2026-11-13"},
    "layers": 2,
    "zones": [("GND", "B.Cu", 0.3)],
    "qty_per_instrument": 1,
    "open_items": [
        "the M4 mount: pick its x / y once placed and send them to branner (floor boss + heat-set)",
        "WIRE ENTRIES (branner 11-13, for the intent): never +Y (the wall is 1.5 off the +Y edge); not -Y over board x 12.35..67.35 (motor 4, 1.5 off the -Y edge at instrument x -523..-468) -- point those along X; parts at board x < -73.45 (instrument x < -608.8, branner 11-13: the nut block's +X face thickened 2.4) stay under 41 tall, top <= z -66.2 (the keyhead nut prism)",
        "J11-J20 wire entry side: the Phoenix PT-H footprint's entry assumed on its +Y (KiCad frame) -- check against the drawing before the mate rules are trusted",
        "motor leads: 0.4 m for motors 1, 6, 7 (branner's Manhattan runs to a board centred x -560 y 46); 0.4 for all = one SKU",
        "the SERVO42D's own 4-way terminal order -- match J11-J20's to it so a lead is straight across",
        "KF350-3.5-4P: confirm M2 slotted (2.0 mm blade) and its LCSC code; the footprint is Phoenix PT 1,5/4-3,5-H (same 3.5 mm pitch, check the pin-1 offset)",
        "J1 PZ1.27-2x15P ZZ: LCSC code and stock (the 2x8 is C22438123)",
    ],
}


if __name__ == "__main__":
    connector_board()
    ERC()
    net_path = os.path.join(OUT_DIR, "connector_board.net")
    generate_netlist(file_=net_path)
    netcheck.no_orphan_pins(net_path)
    with open(os.path.join(OUT_DIR, "connector_board.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("connector_board netlist written; %d open items" % len(BOARD_NOTES["open_items"]))
