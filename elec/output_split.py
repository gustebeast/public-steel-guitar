"""The output board, SPLIT into two boards stacked in the same box (lead, 2026-11-13).

    py -3.12 elec/output_power.py      # -> elec/out/output_power.{net,board.json}
    py -3.12 elec/output_signal.py     # -> elec/out/output_signal.{net,board.json}

WHY. As one 68 x 100 board, output_board did not route: its best placement (ob10) finished
with 30 nets open and 279 unconnected items, its planes cut up, at 0.54 courtyard fill with
the PD power stage, the H743 + ULPI PHY and the pickup preamp sharing one 37 mm box. The
dense boards that route here sit at 0.41-0.47. Two boards ~15 mm apart in the same box
give each a whole outline: the signal half lands near 0.33 and the power half near 0.21,
and the PD and buck switching leave the preamp's board. ~$1 an instrument.

ONE CIRCUIT, TWO BOARDS. There is no second copy of any circuit. output_board.py still
builds the whole thing -- its notes, its fixes, its part choices are the single source --
and this module removes the other half's parts from it and puts a 2 x 12 1.27 mm
board-to-board connector (J20, harness.OUTPUT_LINK) on every net that crosses. So a fix in
output_board.py reaches both boards, and the partition is the only thing defined here.

THE PARTITION, AND THE CHECK THAT HOLDS IT. A part is POWER if it is named in POWER_REFS
or has a pin on a POWER_NET; everything else is SIGNAL. The nets that then have pins on
both sides MUST be exactly the link's nets (harness.OUTPUT_LINK) -- a part added to
output_board.py that drags a new net across fails the build by name, rather than shipping
a board with an unconnected pin.
"""
from __future__ import annotations

import builtins
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import output_board as OB                          # noqa: E402  (builds nothing on import)
import harness                                     # noqa: E402
import netcheck                                    # noqa: E402
from skidl import ERC, Part, Pin, generate_netlist        # noqa: E402

P = Pin.types.PASSIVE

# the power half, by ref: the parts the POWER_NET rule cannot see (they sit on shared rails)
# but whose job is the power half's -- pull-ups beside their ICs, bypass caps, the star point
POWER_REFS = set("""
    J1 J2 J3 J10 J12 U5 U13 U14 U16 U17 U18 U19 Q4 Q5 Q6 Q7 RT1 RT2 L1 R60 R112
    D2 D3 D11 D12 D13 D14 D15 D16 D19
    R3 R4 R92 C117 R80 R81 R82 R83 R84 R85 R91 C116 R120 R122 C5 C6 C64 C65
""".split())
# ...and by net: anything touching the chargers, the buck's own nodes or a port's nets
POWER_NET = re.compile(r"^(VSTBY|VIN_BUS|VIN_BRAIN|PWR_GND|SW|BOOT|FB|BUCK_VCC|BUCK_PG_NC|"
                       r"P[AB]_.*|USB[AB]_D[PM]|GADGET_D[PM]|J1[02]_.*|J3_.*|U1[346789]_.*)$")
# harness way name -> the net it carries
LINK_NET = {"V5": "V5_PRE", "GND": "GND", "V3D": "+3V3D"}

LINK_FP = {   # power half: the socket; signal half: the header that plugs into it
    "power": ("PinSocket_2x12_P1.27mm", "Connector_PinSocket_1.27mm:PinSocket_2x12_P1.27mm_Vertical_SMD"),
    "signal": ("PinHeader_2x12_P1.27mm", "Connector_PinHeader_1.27mm:PinHeader_2x12_P1.27mm_Vertical_SMD"),
}

BOARD_W, BOARD_L = OB.BOARD_W, OB.BOARD_L
# THE STACK. The two boards FACE each other ~15 mm apart (both single-sided: every internal
# lead is side entry, so no plug points into the other board). The power board is only
# POWER_L tall (~0.3 fill) and sits at the BOTTOM of the box, so the signal board's top band
# -- the jack, the pickup's screws -- is open from the front. Each board is drawn from its
# own component side: signal x = instrument x, power x = -instrument x, and the power
# board's centre is STACK_DY below the signal board's. J20 is KiCad's 1.27 mm header on the
# signal board and its socket on the power board, both at rot 0: the socket footprint is
# the header's mirror (pin 1 at +1.8 against -1.95, read from both .kicad_mod files), which
# is exactly what facing boards need. The intents fix both at these points.
POWER_L = 72.0
STACK_GAP = 15.0
STACK_DY = (BOARD_L - POWER_L) / 2                 # 14: power centre below signal centre
J20_SIGNAL = (-14.0, -32.0)
J20_POWER = (-J20_SIGNAL[0], J20_SIGNAL[1] + STACK_DY)
NOTES = {
    "power": {
        "outline_mm": (BOARD_W, POWER_L),
        "stack": {"faces": "output_signal", "gap_mm": STACK_GAP, "dy_mm": -STACK_DY,
                  "x_mirrored": True, "J20": J20_POWER},
        "layers": 4,
        "zones": [("PWR_GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],
        "qty_per_instrument": 1,
        "panel_edge": "-X",
        "edge_parts": {"-X": ["J1", "J2"], "+X": ["J3", "J10", "J12"]},   # its own frame: mirrored
        "placements": {},
        "open_items": [
            "J20 (socket) and output_signal J20 (header): the stack height between the two "
            "boards is the connector pair's -- pick a 1.27 mm 2 x 12 pair stocked at JLC whose "
            "mated height matches branner's board spacing (~15 mm asks for a tall socket or "
            "long-tail header), then fix the footprints",
        ] + [o for o in OB.BOARD_NOTES["open_items"] if "AP33772S" in o or "NCEP4090" in o],
    },
    "signal": {
        "outline_mm": (BOARD_W, BOARD_L),
        "stack": {"faces": "output_power", "gap_mm": STACK_GAP, "dy_mm": STACK_DY,
                  "x_mirrored": False, "J20": J20_SIGNAL},
        "layers": 4,
        "zones": [("GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],
        "qty_per_instrument": 1,
        "panel_edge": "+X",
        "edge_parts": {"+X": ["J5"], "+Y": ["J8"], "-X": ["J4", "J9", "J11"]},
        "placements": {},
        "open_items": [
            "J20: see output_power's open item -- the pair's mated height is the board spacing",
        ],
    },
}


def side_of(part):
    nets = {pin.net.name for pin in part.pins if pin.net}
    if part.ref in POWER_REFS or any(POWER_NET.match(n) for n in nets):
        return "power"
    return "signal"


def build(half):
    """output_board's whole circuit, then only `half` of it, with J20 on the crossing nets."""
    assert half in ("power", "signal"), half
    OB.output_board()
    circ = builtins.default_circuit
    side = {p.ref: side_of(p) for p in circ.parts}
    on = {}
    for p in circ.parts:
        for pin in p.pins:
            if pin.net:
                on.setdefault(pin.net.name, set()).add(side[p.ref])
    crossing = {n for n, s in on.items() if len(s) == 2}
    want = {LINK_NET.get(w, w) for w in harness.OUTPUT_LINK}
    if crossing != want:
        raise SystemExit("output_split: the nets crossing the partition are not the link's.\n"
                         "  crossing, not on the link: %s\n  on the link, not crossing: %s\n"
                         "  -> place the new part in POWER_REFS, or add its net to "
                         "harness.OUTPUT_LINK" % (sorted(crossing - want), sorted(want - crossing)))
    nets = {}
    for p in circ.parts:
        for pin in p.pins:
            if pin.net and pin.net.name in crossing:
                nets[pin.net.name] = pin.net
    circ.rmv_parts(*[p for p in list(circ.parts) if side[p.ref] != half])
    name, fp = LINK_FP[half]
    j20 = Part(name=name, ref_prefix="J", ref="J20", tag="J20", dest="NETLIST", tool="skidl",
               value=name, description="board-to-board to output_%s J20 (harness.OUTPUT_LINK)"
               % ("signal" if half == "power" else "power"), footprint=fp,
               pins=[Pin(num=i + 1, name=w, func=P) for i, w in enumerate(harness.OUTPUT_LINK)])
    for i, w in enumerate(harness.OUTPUT_LINK):
        nets[LINK_NET.get(w, w)] += j20[i + 1]
    return sorted(r for r, s in side.items() if s == half)


def main(half):
    refs = build(half)
    ERC()
    stem = "output_" + half
    net_path = os.path.join(OB.OUT_DIR, stem + ".net")
    generate_netlist(file_=net_path)
    if half == "power":
        netcheck.grounds_meet(net_path)            # R60 joins GND and PWR_GND, on this half
    netcheck.no_orphan_pins(net_path)
    notes = dict(NOTES[half], split_from="output_board", parts=len(refs) + 1)
    with open(os.path.join(OB.OUT_DIR, stem + ".board.json"), "w") as f:
        json.dump(notes, f, indent=2)
    print("%s netlist written: %d parts + J20; %d open items"
          % (stem, len(refs), len(notes["open_items"])))
