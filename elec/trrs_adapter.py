"""TRRS <-> JST-XH adapter — the board at each end of the leg link.

    py -3.12 elec/trrs_adapter.py       # -> elec/out/trrs_adapter.{net,board.json}

TWO of them, and they are the SAME board used in opposite directions: it is a
passive four-wire pass-through, so "TRRS in, JST out" and "JST in, TRRS out" are
the same copper. One at the chassis (trunk -> leg), one at the bar cradle
(leg -> the bar's tees).

WHAT IT REPLACES. Today's BOM crosses both TRRS joints with FACTORY-CABLED parts
-- a Tensility 10-03404 jack-on-a-cable at $8.19 and a CA-354S plug-on-a-cable at
$3.53 -- each with an XH crimped onto its cut end. Putting the jack ON A BOARD
instead costs about $0.10 of connector, deletes both crimps, and deletes tee 12
(the "leg socket" tee), whose only job was to land that cable on the trunk.

THE OUTLINE IS AN OUTPUT HERE, NOT AN INPUT. Every other board in elec/ reads its
geometry from src/ because the plastic already exists. This one has no housing
yet -- the leg-carrier CAD was never built (the column became an off-the-shelf
extension cable), so there is nothing to read. The numbers below are therefore
the board sizing ITSELF, derived from the two connector courtyards, and the
mechanical side should be built to them rather than the other way round.

SIGNAL MAP is the project's existing one, and the assignment of GND to the SLEEVE
is not arbitrary: the sleeve is the first contact made and the last broken, so
the two ends share a reference before anything else touches.
    tip = CAN_L,  ring1 = CAN_H,  ring2 = +V,  sleeve = GND
CAN_H and CAN_L are swapped against the old note, and the swap is free: both
ends of this link are THIS board, so the pair only has to agree with itself,
and the leg column is a straight-through extension cable. Taking tip = CAN_L
makes the jack's contact order match the XH's pin order, so all four nets run
straight down the board and nothing has to change layer.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import json  # noqa: E402

from skidl import ERC, Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

from cadkit.pcb import xh_length  # noqa: E402

# Korean Hroparts PJ-320D-4A, LCSC C95562 -- a 4-pole 3.5 mm jack that is both in
# KiCad's own library and stocked for JLCPCB assembly, which is a narrower gate
# than it sounds (most 4-pole jacks fail one or the other). Rated 30 V / 500 mA:
# comfortably past the trunk's 24 V at the tens of mA a leg's sensor boards draw.
JACK_MPN = "PJ-320D-4A"
JACK_LCSC = "C95562"
JACK_FP = "Connector_Audio:Jack_3.5mm_KoreanHropartsElec_PJ-320D-4A_Horizontal"

# NO TVS CLAMP HERE, and that is a decision rather than an omission. A clamp on
# the CAN pair belongs beside the TRANSCEIVER it protects -- on the lever boards
# and the motor-controller board, which is also where every transceiver datasheet
# puts it. Putting one on this board instead would protect the pair at a point
# where nothing sensitive is connected, and on a 4-wire pass-through it was the
# only part that made the copper need to cross itself.
#
# WHAT IT WOULD HAVE BEEN PROTECTING AGAINST, because the risk is real and now
# lands on those boards: every conductor of a TRRS plug sweeps every socket
# contact on the way in, so the trunk's +V momentarily reaches CAN_H and CAN_L.
# No pin order avoids that -- it is how the connector works. At 24 V that is past
# the SN65HVD230's -4..+16 V absolute maximum on its bus pins, i.e. past
# destruction of every lever board on the leg.

LEG_RAIL_NOTE = """The trunk's +V is 24 V today (the tees carry gnd/24V/H/L) and
each lever board bucks it down. Dropping the LEG's rail to 5 V instead -- one
buck on the chassis side, LDOs on the lever boards -- puts the hot-plug transient
inside the transceiver's own -4..+16 V rating and removes the failure mode rather
than clamping it. Cost is current: ~3 boards x ~50 mA at 3.3 V is ~300 mA at 5 V,
which over 2.4 m of 28 AWG round trip is ~0.15 V of drop. This board does not
care either way -- +V is a pass-through pin -- but the lever board does."""


def jack():
    """The 4-pole socket. Pads are named T / R1 / R2 / S in KiCad's footprint,
    matching the drawing, so the netlist reads as the signal map does."""
    return Part(name=JACK_MPN, ref_prefix="J", tag="J1", dest="NETLIST", tool="skidl",
                value=JACK_MPN, description="TRRS 3.5 mm 4-pole socket (%s)" % JACK_LCSC,
                footprint=JACK_FP,
                pins=[Pin(num="T", name="TIP", func=Pin.types.PASSIVE),
                      Pin(num="R1", name="RING1", func=Pin.types.PASSIVE),
                      Pin(num="R2", name="RING2", func=Pin.types.PASSIVE),
                      Pin(num="S", name="SLEEVE", func=Pin.types.PASSIVE)])


@subcircuit
def trrs_adapter():
    gnd, v_in = Net("GND"), Net("+V")
    can_h, can_l = Net("CAN_H"), Net("CAN_L")
    for n in (gnd, v_in, can_h, can_l):
        n.drive = Pin.drives.POWER

    j1 = jack()
    can_l += j1["T"]
    can_h += j1["R1"]
    v_in += j1["R2"]
    gnd += j1["S"]

    j2 = Part(name="B4B-XH-A", ref_prefix="J", tag="J2", dest="NETLIST", tool="skidl",
              value="B4B-XH-A", description="trunk side (same pinout as the tees)",
              footprint="Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
              pins=[Pin(num=i + 1, name=n, func=Pin.types.PASSIVE)
                    for i, n in enumerate(("GND", "V", "CAN_H", "CAN_L"))])
    # SAME PIN ORDER AS THE MOTOR TEE, deliberately: one crimp order for every XH
    # in the instrument means a lead made for a tee plugs in here too.
    gnd += j2[1]
    v_in += j2[2]
    can_h += j2[3]
    can_l += j2[4]


# ── the board ────────────────────────────────────────────────────────────────
# Sized off the two courtyards, not off a housing (see the module docstring).
# The jack's courtyard is 15.18 x 10.08 and the XH's 13.49 x 6.84; stacking them
# along Y with the jack's mouth facing -X gives 20 x 24 with ~2 mm of air in
# every direction. NO MOUNTING HOLE: the project's rule is that plastic captures
# the board on every axis but one and a single M4 button head beside it closes
# the last -- nothing passes through the board.
BOARD_W, BOARD_L = 20.0, 26.0

BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 2,
    "thickness_mm": 1.6,
    "placements": {
        "J1": (2.0, 3.5, 0.0),         # jack, mouth -X
        "J2": (0.0, -7.5, 0.0),        # trunk XH, cable up
    },
    "ref_pos": {"J1": (0.0, 9.5), "J2": (8.0, -11.3)},
    # Four nets, four runs, no crossings and no vias -- which is the whole reason
    # the signal map got swapped. GND is the exception: the sleeve contact sits
    # on the jack's own -Y side, so it takes the long way round the +X edge and
    # under the header. It is an explicit track, NOT left to the pour, because
    # the jack's contacts are surface pads and a B.Cu pour cannot reach them.
    "tracks": [
        ("+V", "F.Cu", 0.4, [(-1.65, 5.17), (-1.65, -6.5), (-1.25, -6.5), (-1.25, -7.5)]),
        ("CAN_H", "F.Cu", 0.3, [(1.35, 5.17), (1.35, -7.0), (1.25, -7.5)]),
        # straight down at the tip pad's own X: threading it further -X ran it
        # into the jack's NPTH mounting hole, which the courtyard does not show
        ("CAN_L", "F.Cu", 0.3, [(5.35, 5.17), (5.35, -6.0), (3.75, -6.0),
                                (3.75, -7.5)]),
        ("GND", "F.Cu", 0.4, [(6.45, -1.33), (8.6, -1.33), (8.6, -10.0),
                              (-3.75, -10.0), (-3.75, -7.5)]),
    ],
    "zones": [("GND", "B.Cu", 0.3)],
    "hold_edge": "+x",
    "no_mounting_holes": True,
    "single_sided": True,
    "conn_len_mm": xh_length(4),
    "qty_per_instrument": 2,
}


if __name__ == "__main__":
    trrs_adapter(tag="adapter")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "trrs_adapter.net"))
    with open(os.path.join(OUT_DIR, "trrs_adapter.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f mm, %d placements, x%d per instrument"
          % (BOARD_W, BOARD_L, len(BOARD_NOTES["placements"]),
             BOARD_NOTES["qty_per_instrument"]))
