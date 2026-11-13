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
    D2 D3 D11 D12 D13 D14 D15 D16 D19 D20 D21 D22 D23
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
        # every ground pad -- the AP33772S bellies above all -- drops a via to its plane
        "stitch_nets": ("PWR_GND", "GND"),
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
        "stitch_nets": ("GND",),   # U4's belly and every GND pad to the plane
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


# ── quality (cadkit/PCB_QUALITY.md) ──────────────────────────────────────────────────────────
# Parts whose idle pins are DESIGN, with why; the pins themselves are read from the built
# netlist (no net, or alone on an *_NC net) so the list cannot drift from the circuit.
IDLE_WHY = {
    "U1": "STM32H743 GPIO / functions this board gives no job: left open, firmware leaves each an "
          "analog input (RM0433 8.3.1 reset state); the optical board's own map, re-pointed",
    "U4": "USB3300 CPEN, EXTVBUS (this board switches the optical board's VBUS itself, U15) and XO "
          "(the PHY is clocked on XI by Y2)",
    "U5": "LMR33630 PG: open drain, not read",
    "U6": "AP2112K pin 4 is the maker's NC",
    "U13": "AP33772S FLIP, GPIO / VSEL (FA02 only), LED, DP / DN (moisture sensing, unused) and NC",
    "U14": "AP33772S FLIP, GPIO / VSEL (FA02 only), LED, DP / DN (moisture sensing, unused) and NC",
}
PINOUT_VALUES = ("TYPE-C-31-M-12 S6B-XH-SM4-TB S6B-PH-SM4-TB INA226AIDGSR TS3USB221RSER LMR33630BRNXR "
                 "NMJ6HCD2 G6K-2F-Y-DC5 AO3400A STM32H743IIT6 AD8402ARZ10 TLV9061IDBVR TS5A3159DCKR "
                 "TPS2553DBVR PCM1808PWR AP2114H-3.3TRG1 PCM5102APWR USB3300-EZK-TR AP2112K-3.3TRG1 "
                 "TAXM25M4RDBCCT2T CJO05-240003320B30").split()
J20_CITE = ("harness.OUTPUT_LINK: way n is the footprint's pad n. KiCad's 1.27 mm 2-row header "
            "puts pad 1 at -1.95, the socket at +1.8 (read from both .kicad_mod files, 2026-11-13): "
            "the socket is the header's mirror, which is what two boards facing each other need, "
            "and output_split.J20_SIGNAL / J20_POWER put them on one axis")
VDD = ["U1.%d" % n for n in OB.MCU_VDD]


def _idle(net_path, refs):
    """{ref: "pin pin ..."} -- pins with no net, or alone on their net, read from the .net."""
    import collections
    t = open(net_path, encoding="utf-8").read()
    body = t[t.index("(nets"):]
    on = collections.defaultdict(list)
    for blk in re.split(r"\(net\s", body)[1:]:
        nodes = re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk)
        if len(nodes) == 1:
            on[nodes[0][0]].append(nodes[0][1])
    out = {}
    for ref in refs:
        pins = sorted(set(on.get(ref, ())), key=lambda p: (len(p), p))
        if pins:
            out[ref] = " ".join(pins)
    return out


def quality(half, net_path):
    import quality_share as QS
    q = {"pinouts": dict(QS.cited(PINOUT_VALUES))}
    if half == "power":
        q["pinouts"].update(OB.PD_PINOUTS)
    q["pinouts"]["PinSocket_2x12_P1.27mm" if half == "power" else "PinHeader_2x12_P1.27mm"] = J20_CITE
    idle = _idle(net_path, [r for r in IDLE_WHY])
    unc = {ref: {"pins": pins, "why": IDLE_WHY[ref]} for ref, pins in idle.items()}
    usbc, jst = ("J[123]", "J1[02]") if half == "power" else ("J[49]", "J11")
    unc[usbc + ".[AB]8"] = "USB-C sideband (SBU): USB 2.0 does not use it"
    unc[jst + ".MP"] = "a side-entry JST's mounting tabs: solder only"
    q["unconnected"] = unc
    if half == "power":
        unc["J1[02].4"] = "BRAIN_POWER way 4: the lead's one empty way (harness)"
        q["power_paths"] = (
            [{"net": "P%s_VBUS" % s, "from": "%s.%s" % (j, w), "to": [r], "amps": 2.5}
             for s, j, r in (("A", "J1", "R70.1"), ("B", "J2", "R75.1")) for w in ("A4", "B9")]
            + [{"net": "P%s_VCC" % s, "from": r, "to": [qs], "amps": 5.0}
               for s, r, qs in (("A", "R70.2", "Q4.5"), ("B", "R75.2", "Q5.5"))]
            + [{"net": "P%s_VOUT" % s, "from": a, "to": [b], "amps": 5.0}
               for s, a, b in (("A", "Q4.1", "Q6.1"), ("B", "Q5.1", "Q7.1"))]
            + [{"net": "VIN_BUS", "from": d, "to": ["R112.1"], "amps": 5.0} for d in ("Q6.5", "Q7.5")]
            + [{"net": "VIN_BRAIN", "from": "R112.2", "to": ["%s.%d" % (j, w)], "amps": 2.5}
               for j in ("J10", "J12") for w in (1, 6)]
            + [{"net": "VSTBY", "from": d, "to": ["U5.2", "U5.9", "U5.10"], "amps": 1.5}
               for d in ("D14.1", "D16.1")]
            + [{"net": "V5_PRE", "from": "L1.2", "to": ["J20.%d" % w for w in range(1, 6)],
                "amps": 2.64}])
        q["not_power"] = {n: "a presence loop from a brain lead's way 3: a logic level behind 1k / 10k"
                          for n in ("PWR_LEAD1_N", "PWR_LEAD2_N")}
        q["power_paths"].append({"net": "+3V3D", "from": "J20.9", "to": ["U17.10", "U16.6"],
                                 "amps": 0.005})
        # A2 reads every pin on a power net as a supply pin; these are SENSE inputs drawing
        # microamps, and a cap on them would sit across the measurement, not bypass a load
        sense = "a sense input (uA), not a supply: a cap here filters the reading, it bypasses nothing"
        q["decoupling"] = {"exempt": {
            "U16.8": "INA226 VBUS (SBOS547, pin functions): bus-voltage " + sense,
            "U16.9": "INA226 IN- (SBOS547, pin functions): shunt " + sense,
            "U16.10": "INA226 IN+ (SBOS547, pin functions): shunt " + sense,
            "U18.4": "LM74700-Q1 CATHODE (SNOSD17, pin functions): reverse-current " + sense,
            "U19.4": "LM74700-Q1 CATHODE (SNOSD17, pin functions): reverse-current " + sense}}
        q["net_groups"] = [{"name": "two PD ports, one set of nets each",
                            "nets_like": "^P[AB]_(VBUS|VCC|VOUT|GATE|ORGATE|VCAP|CC1|CC2)$", "count": 16}]
        q["match"] = QS.usb_match([
            ("GADGET", "GADGET_DP", "GADGET_DM", "U17 -> J3, the CM5's gadget port."),
            ("USBA", "USBA_DP", "USBA_DM", "J1's data to U17."),
            ("USBB", "USBB_DP", "USBB_DM", "J2's data to U17.")])
    else:
        q["power_paths"] = (
            [{"net": "V5_PRE", "from": "J20.%d" % w, "to": ["U15.1", "R98.1", "FB1.1"], "amps": 0.53}
             for w in range(1, 6)]
            + [{"net": "VBUS_OPT", "from": "U15.6", "to": ["J4.A4", "J4.B9"], "amps": 1.8}]
            + [{"net": "+3V3D", "from": "U21.2", "to": VDD, "amps": 0.58}])
        q["not_power"] = dict({n: "a presence loop from a brain lead's way 3: a logic level"
                               for n in ("PWR_LEAD1_N", "PWR_LEAD2_N")},
                              LOW_PWR="an MCU output to the brain lead J11: a logic level",
                              PWR_BTN="the power button from the brain lead J11: a logic level")
        q["power_paths"] += [{"net": "+5V", "from": "FB1.2", "to": ["U6.1"], "amps": 0.26},
                             {"net": "+3V3", "from": "U6.5", "to": ["U2.4", "U3.1"], "amps": 0.05}]
        q["waive"] = {"A7:" + n: "pulled up on output_power (R80-R85, 10k / 4k7 to +3V3D), at the "
                                 "far end of J20: one pair per bus"
                      for n in ("PDA_SCL", "PDA_SDA", "PDB_SCL", "PDB_SDA", "I2C2_SCL", "I2C2_SDA")}
        q["net_groups"] = [{"name": "three I2C buses out to the power board on J20",
                            "nets_like": "^(PDA|PDB|I2C2)_(SCL|SDA)$", "count": 6}]
        q["match"] = QS.usb_match([
            ("MCU", "MCU_DP", "MCU_DM", "the H743's OTG_FS -> J9, a CM5 host port."),
            ("OPT", "OPT_DP", "OPT_DM", "the USB3300 -> J4, high speed to the optical board.")])
    # J20 is a mezzanine pair: it mates blind as the two boards stack, so there is no
    # "side it is plugged from" to label, and its 1.27 mm row has no room for 24 words.
    # The pinout of record is harness.OUTPUT_LINK (checked at import).
    q.setdefault("waive", {})["A17:J20"] = (
        "board-to-board mezzanine, mated blind by the stack and never plugged by hand; "
        "its pinout is harness.OUTPUT_LINK")
    return q


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
    q = quality(half, net_path)
    notes["match"] = q.pop("match")
    notes["quality"] = q
    import volts_decl                   # A16: generated by voltage_check.py --declare output_<half>
    volts_decl.into(notes, stem)
    with open(os.path.join(OB.OUT_DIR, stem + ".board.json"), "w") as f:
        json.dump(notes, f, indent=2)
    print("%s netlist written: %d parts + J20; %d open items"
          % (stem, len(refs), len(notes["open_items"])))
