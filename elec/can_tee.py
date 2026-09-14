"""CAN bus TEE — the electrical design, as code.

The tee is a PASSIVE 3-way junction and nothing else. It exists because the MKS
SERVO42D has a SINGLE 6-pin JST-XH carrying power and CAN together, and a
single-port device cannot be daisy-chained without splicing — which the
solder-only-on-PCBs rule forbids. So every node on the trunk gets one of these:
TRUNK-IN + DROP + TRUNK-OUT, with a termination that can be closed at the two
ends of each bus.

    py -3.12 elec/can_tee.py            # -> elec/out/can_tee.net (+ .erc)

THE BOARD GEOMETRY IS NOT AUTHORED HERE. Outline, connector pitch and the three
connector positions all come from `src.electronics`, which is where the chassis
cradle and the harness routing already read them from. This module imports them
so a mechanical change cannot silently desync the board — see BOARD_NOTES at the
bottom, which is what the layout step consumes.

Parts are declared INLINE (pins + footprint) rather than pulled from a KiCad
symbol library. Four nets and two part types do not justify a library
dependency, and it keeps this file the whole truth for the netlist.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
# SKiDL names its log, ERC report and generated part library after the script
# and drops them in the CWD -- the log at IMPORT time, so this has to happen
# before the import, not in __main__. Every derived file belongs in elec/out.
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import json  # noqa: E402

from skidl import ERC, Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

from src import electronics as EL  # noqa: E402
from cadkit.pcb import xh_length  # noqa: E402

# ── the harness contract ─────────────────────────────────────────────────────
# Four conductors, and the colours are the USER'S (see the cable-colour rule):
# black GND / red 24V / yellow CAN_H / green CAN_L. The pin ORDER below is the
# board's half of that contract — the crimper reads it off here, and the
# SERVO42D's 6-pin pigtail lands its 4 relevant wires in this order.
XH_PINOUT = ("GND", "V24", "CAN_H", "CAN_L")

# 120 R, 1%. ISO 11898 wants 120 Ω ±10% at each END of the trunk and nowhere
# else, so every board carries the resistor and leaves the jumper OPEN; the two
# boards that land at a bus end get theirs closed. One layout, one BOM, one
# assembly file for all 13 — populating R1 on only two of them would mean two
# JLCPCB variants to save $0.02 of resistor.
TERM_OHMS = "120R"
TERM_PKG = "0603"

# SPLIT TERMINATION (2x 60R + 4.7nF to GND) is the textbook EMC answer and is
# deliberately NOT used: it buys common-mode filtering that matters on a metres-
# long vehicle harness at 500 kbps+, and this trunk is ~1 m of shielded cable
# inside a plastic instrument. It would also put a capacitor's return current on
# the same GND the optical pickup's analog reference rides.


def xh_header(ref: str, tag: str, desc: str) -> Part:
    """A 4-way JST B4B-XH-A, top entry, THT. Pin 1 is the pin-1 triangle on the
    housing; `XH_PINOUT` names what each one carries."""
    return Part(
        name="B4B-XH-A",
        ref_prefix=ref,
        tag=tag,
        dest="NETLIST",
        tool="skidl",
        value="B4B-XH-A",
        description=desc,
        footprint="Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
        pins=[Pin(num=i + 1, name=n, func=Pin.types.PASSIVE)
              for i, n in enumerate(XH_PINOUT)],
    )


@subcircuit
def can_tee():
    """Trunk-in, drop, trunk-out — every like pin strapped together — plus the
    terminator behind its jumper."""
    gnd = Net("GND")
    v24 = Net("+24V")
    can_h = Net("CAN_H")
    can_l = Net("CAN_L")
    for n in (gnd, v24, can_h, can_l):
        n.drive = Pin.drives.POWER

    j1 = xh_header("J", "J1", "trunk in")
    j2 = xh_header("J", "J2", "drop to this node's device")
    j3 = xh_header("J", "J3", "trunk out")

    # A tee is a junction: all three connectors are the same four nets. There is
    # no in/out direction in copper — the labels are for the person wiring it.
    for j in (j1, j2, j3):
        gnd += j[1]
        v24 += j[2]
        can_h += j[3]
        can_l += j[4]

    r1 = Part(name="R", ref_prefix="R", tag="R1", dest="NETLIST", tool="skidl",
              value=TERM_OHMS, description="CAN termination, 1%",
              footprint="Resistor_SMD:R_0603_1608Metric",
              pins=[Pin(num=1, func=Pin.types.PASSIVE),
                    Pin(num=2, func=Pin.types.PASSIVE)])
    # SOLDER jumper, not a shunt on a header: which two boards terminate is
    # fixed the moment the harness is built, a 2.54 shunt is taller than every
    # other part here bar the connectors, and a shunt that can fall off is a
    # bus that fails intermittently. A blob of solder is reversible with the
    # same iron that fits the heat-set inserts.
    jp1 = Part(name="SolderJumper_2_Open", ref_prefix="JP", tag="JP1", dest="NETLIST",
               tool="skidl", value="TERM",
               description="close on the LAST tee of each bus only",
               footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm",
               pins=[Pin(num=1, func=Pin.types.PASSIVE),
                     Pin(num=2, func=Pin.types.PASSIVE)])

    term = Net("TERM_MID")            # R1 and JP1 in series across the pair
    can_h += r1[1]
    term += r1[2], jp1[1]
    can_l += jp1[2]


# ── what the layout step needs, read from the mechanical model ───────────────
# Board-local millimetres, origin at the board centre, +Y the direction the
# board grows off the -Y rail. These are NOT restated numbers: every one is
# imported or derived from src.electronics, so moving the cradle moves the
# footprints too.
BOARD_NOTES = {
    "outline_mm": (EL.TEE_BOARD_X, EL.TEE_BOARD_Y),
    "layers": 2,
    "thickness_mm": 1.6,
    # J1/J2/J3 sit in one row along X at the connector centre-line, rotated 90
    # deg so their pin rows run along Y (cables rise +Z into the corridor).
    "placements": {
        "J1": (-EL.TEE_CONN_DX, EL.TEE_CONN_CY, 90.0),
        "J2": (0.0, EL.TEE_CONN_CY, 90.0),
        "J3": (+EL.TEE_CONN_DX, EL.TEE_CONN_CY, 90.0),
        # The terminator pair goes in the strip +Y of the connector courtyards.
        # A B4B-XH-A's courtyard is 13.49 x 6.84, so turned 90 deg it reaches
        # y +5.75 from the connector centre-line -- everything below that is
        # spoken for, and the first attempt (stacked at x -8, y 9 and 6) put
        # JP1 both inside J1's courtyard and on top of J1's CAN_L pad.
        "R1": (-8.0, 8.5, 0.0),
        "JP1": (-4.0, 8.5, 0.0),
    },
    # Designators go in the two clear strips the connector courtyards leave --
    # below them for the three headers, above for the terminator pair. On a
    # board this full there is nowhere else they can still be read once the
    # plugs are in.
    "ref_pos": {
        "J1": (-EL.TEE_CONN_DX, -9.6),
        "J2": (0.0, -9.6),
        "J3": (+EL.TEE_CONN_DX, -9.6),
        "R1": (-8.0, 10.8),
        "JP1": (-4.0, 10.8),
    },
    # ── copper ───────────────────────────────────────────────────────────
    # The three headers land their like pins on one straight line each
    # (pin row along Y at x = -DX, 0, +DX), so every trunk net is a single
    # horizontal track and nothing has to change layer. GND is the B.Cu pour
    # instead of a track -- the pads are THT, so they reach it through the
    # board, and a solid return under a differential pair is worth more here
    # than the 3 mm of copper a track would have saved.
    "tracks": [
        # net, layer, width, [(x, y), ...]
        ("+24V", "F.Cu", 1.0, [(-EL.TEE_CONN_DX, -2.25), (EL.TEE_CONN_DX, -2.25)]),
        ("CAN_H", "F.Cu", 0.3, [(-EL.TEE_CONN_DX, 0.25), (EL.TEE_CONN_DX, 0.25)]),
        ("CAN_L", "F.Cu", 0.3, [(-EL.TEE_CONN_DX, 2.75), (EL.TEE_CONN_DX, 2.75)]),
        # up to the terminator. CAN_H steps OUT to x -8.825 before climbing so
        # it passes J1's pad column (all four pads sit at x -DX) with 1.8 of
        # air; CAN_L climbs in the clear lane between J1 and J2.
        ("CAN_H", "F.Cu", 0.3, [(-EL.TEE_CONN_DX, 0.25), (-8.825, 0.25), (-8.825, 8.5)]),
        ("CAN_L", "F.Cu", 0.3, [(-3.35, 2.75), (-3.35, 8.5)]),
        ("TERM_MID", "F.Cu", 0.3, [(-7.175, 8.5), (-4.65, 8.5)]),
    ],
    # 24V shares the XH trunk at up to 3 A (the connector's limit, which is why
    # XT30 injects along the run), so its track is 1.0 mm -- ~3 A at a 10 degC
    # rise on 1 oz outer copper. The CAN pair and the terminator link carry
    # milliamps and stay at 0.3.
    "zones": [("GND", "B.Cu", 0.3)],       # net, layer, inset from the outline
    # ONE M4 button head BESIDE the +X edge holds the board down (the head laps
    # the edge; nothing passes through the board), so there is no mounting hole
    # to place — only a keep-out where the head reaches over.
    "hold_edge": "+x",
    "no_mounting_holes": True,
    # THT posts drop 3.4 below the board into a relief window in the cradle
    # base; nothing may be placed on the bottom side.
    "single_sided": True,
    "conn_len_mm": xh_length(EL.TEE_CONN_N),
}


if __name__ == "__main__":
    can_tee(tag="tee")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "can_tee.net"))
    # THE HAND-OFF TO LAYOUT. elec/layout.py runs under KiCad's own bundled
    # Python (it needs pcbnew), which has no cadquery and so cannot import
    # src/ -- this JSON is the whole interface between the two, and it is
    # written from the mechanical model every run.
    with open(os.path.join(OUT_DIR, "can_tee.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d-way XH (%.2f long), %d placements"
          % (*BOARD_NOTES["outline_mm"], EL.TEE_CONN_N,
             BOARD_NOTES["conn_len_mm"], len(BOARD_NOTES["placements"])))
