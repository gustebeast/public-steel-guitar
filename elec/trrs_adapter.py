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

SIGNAL MAP -- and the pin order is a SAFETY decision, not a convenience.

    tip = +24 V,  ring1 = CAN_H,  ring2 = CAN_L,  sleeve = GND

+24 V GOES ON THE TIP. Inserting a TRRS plug drags its bands across the socket's
contacts, so a rail on the wrong contact lands briefly on the CAN pair -- and at
24 V that is past the SN65HVD230's -4..+16 V absolute maximum on its bus pins,
i.e. past destruction of every lever board up the leg. The escape is an asymmetry
in how the connector mates: each socket contact sits at a fixed depth, and each
plug band only ever travels as deep as its own resting position. The plug's tip
band passes every contact; ring1 passes only sleeve and ring2; the sleeve band
passes none. So THE SOCKET'S TIP CONTACT IS TOUCHED BY EXACTLY ONE THING in the
whole insertion -- the plug's tip band. Put the rail there, with the POWERED SIDE
CARRYING THE SOCKET (the chassis adapter), and 24 V never meets a conductor it
does not belong to.

What is left is harmless: on the way in the plug's tip band -- the leg's 24 V
conductor, with no source behind it until the tip lands -- sweeps the socket's
GND and CAN contacts, tying a floating unpowered net to them for a moment. It
only becomes live at full insertion, by which point nothing is still sweeping.

GND stays on the SLEEVE, which is right for its own reason: the sleeve makes
first and breaks last, so both ends share a reference before anything else
touches. (An earlier revision put CAN_L on the tip purely so the jack's contact
order matched the XH's pin order and the copper ran straight. That was worth four
tidy tracks; this is worth the transceivers.)

⚠ HARNESS CONSEQUENCE, NOT YET IN THE BOM: both adapter boards carry a JACK, so
the leg cable needs a PLUG AT BOTH ENDS -- a plain 4-pole male-male aux lead, not
the "TRRS M->F extension" BOM.md still lists, whose female barrel also has a
printed seat drawn around it.
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
    v_in += j1["T"]
    can_h += j1["R1"]
    can_l += j1["R2"]
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
#
# ⚠ THE MOUTH FACES ALONG THE LONG AXIS (branner, 2026-09-14), which is a
# MECHANICAL requirement and the one thing on this board that is an input rather
# than an output. The pocket over the leg is 22-26 across X, between the keyhead
# endplate's inner wall and the electronics tray. With the mouth on a SHORT edge
# the board had to lie 26 across that gap (29.8 with its cradle) and did not fit;
# turned 90 deg it lies 10.09 of jack inside a 20 mm width and reaches its 26
# INBOARD, along the plug's own line, where there is room.
#
# THE MOUTH IS NOW 0.1 OFF THE -Y EDGE -- it was 2.61 in, and every millimetre
# of that inset is another millimetre the plug has to reach through the chassis
# rail. Flush is what the footprint allows and not a millimetre less: KiCad's
# courtyard for this jack runs x -9.39..+5.79 about the pad centroid, and that
# -9.39 face IS the barrel opening, so the courtyard edge and the mouth are the
# same line. Putting it on the board edge spends the courtyard's own 0.25 of
# clearance and nothing else.
#
# The jack's courtyard is 15.18 x 10.09 and the XH's 13.49 x 6.84.
#
# ⚠ IT NOW CARRIES AN M4 THROUGH-HOLE, AND THAT IS A CORRECTION (user, 2026-09-15).
# The board went out at 26 long with NO hole, on the rule that plastic captures it
# on every axis but one and an M4 button head BESIDE the edge closes the last. The
# user's objection is right and it is the same one that produced the tee's ear:
# beside-the-edge retention is FRICTION. Nothing stops this board backing out along
# -Y except a tight screw, and -Y is exactly the direction a hand pulls when it
# unplugs the lead. A screw THROUGH the board takes that load in shear instead.
#
# WHERE IT GOES IS FORCED, and it is worth writing down so nobody re-derives it:
#   * NOT beside the jack. The free strips either side of the turned jack are
#     4.955 wide and a 4.5 clearance hole wants ~5.3, so a side hole means widening
#     the board past 20 -- and 20 across X is the whole reason the jack was turned.
#   * NOT at the +Y end past the XH: that puts the screw 15 from the jack's flange
#     and costs 34 of length.
#   * BETWEEN THE TWO CONNECTORS, which is both the shortest board and the best
#     place for the screw -- mid-span, where a lever arm about either connector is
#     smallest. The band cost 5 mm of length (26 -> 31) and the binding number is
#     not the HOLE, it is the BUTTON HEAD: an M4 button is ~7.0 across, so the band
#     has to clear 7.0 + 0.3 either side of the connectors' courtyards, not 4.5.
BOARD_W, BOARD_L = 20.0, 31.0
HOLE_D = 4.5                     # M4 clearance
HOLE_XY = (0.0, 3.6)             # head spans y 0.1..7.1 -- see the band note above
JACK_ROT = 90.0                  # mouth from -X to -Y
JACK_MOUTH_DY = -9.39            # mouth face from the pad centroid, once turned
JACK_X = -1.085                  # centres the turned courtyard (-3.96..+6.13) on X
JACK_EDGE = 0.1                  # the courtyard's only air against the outline; it is
                                 # there so a flush placement does not read as OFF BOARD
                                 # on a rounding error, not because the mouth wants inset
JACK_Y = -BOARD_L / 2.0 - JACK_MOUTH_DY + JACK_EDGE    # -6.01: mouth 0.1 off the -Y edge
XH_Y = 10.30                     # turned 180: courtyard 7.40..14.24, so it clears
                                 # the button head by 0.3 and the +Y edge by 1.26

BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "layers": 2,
    "thickness_mm": 1.6,
    "placements": {
        "J1": (JACK_X, JACK_Y, JACK_ROT),   # jack, mouth -Y and flush with the edge
        "J2": (0.0, XH_Y, 180.0),           # trunk XH, cable up; see the pin-order note
    },
    "ref_pos": {"J1": (7.0, -4.0), "J2": (0.0, 4.5)},
    # J2 IS STILL TURNED 180 deg, and the reason survived the jack's rotation
    # unchanged. Turned, the jack's three signal contacts stand in ONE COLUMN on
    # the -X side, reading (from the mouth inwards) CAN_L, CAN_H, +V, with GND
    # off on its own at +X. The XH's crimp order is fixed at GND, +V, CAN_H,
    # CAN_L, so end-for-end puts its pins in the order that column arrives in:
    # the deepest contact (+V) reaches furthest +X and the nearest (CAN_L) goes
    # straight up the -X side, and the four runs nest instead of crossing. The
    # crimp order is untouched -- pin 1 is simply at the other end of the part.
    #
    # THE HAND-LAID TRACKS ARE GONE with the rotation; they were written against
    # the old geometry to the tenth of a millimetre and re-deriving eight
    # segments by hand to save a router two seconds is not a trade worth making
    # on a four-net board. Freerouting lays it and DRC is what accepts it.
    # (Watch the jack's two NPTH mounting holes, which sit OUTSIDE its courtyard
    # and are invisible until DRC runs -- the router does see them.)
    "cutouts": [{"xy": HOLE_XY, "d": HOLE_D}],
    "zones": [("GND", "B.Cu", 0.3)],
    "hold_edge": "+x",
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
