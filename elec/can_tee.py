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
        # the terminator pair lives where the 3D model already reserves it:
        # -X of the connectors, up in the +Y corner clear of the tail relief
        "R1": (-8.0, 9.0, 0.0),
        "JP1": (-8.0, 6.0, 0.0),
    },
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
    print("board %.1f x %.1f mm, %d-way XH (%.2f long), %d placements"
          % (*BOARD_NOTES["outline_mm"], EL.TEE_CONN_N,
             BOARD_NOTES["conn_len_mm"], len(BOARD_NOTES["placements"])))
