"""The one place the instrument's XH pin order is written down.

⚠ THIS CONSTANT WAS WRITTEN OUT THREE TIMES AND NOTHING COMPARED THE COPIES. can_tee.py
and motor_ctrl.py each defined their own `XH_PINOUT`, the second with the comment "same
order as every other board" -- which was a claim, not a check -- and lever_sensor.py did
not use either, it spelled the order inline in its J1 pin list. All three agreed on
2026-09-19 when this was found. Nothing would have said so if they had not.

⚠ AND THIS IS THE CONSTANT LEAST ABLE TO SURVIVE DISAGREEMENT. Every XH cable in the
instrument is interchangeable by construction -- that is the point of one pinout and one
crimp -- so the pin order is not a per-board detail, it is a property of the HARNESS,
and a board that gets it wrong does not fail on that board. It puts 24 V into CAN_H of
whatever it is plugged into. No DRC, netlist check or router can see it: each board is
internally consistent with its own copy, which is exactly why every copy has to go.

The trunk order is GND, +24 V, CAN_H, CAN_L. An 8-way trunk connector is that order
twice -- in on 1-4, out on 5-8 -- so a node sits INLINE on the bus and the chain
daisy-chains through it, which is how both the tees and the sensor boards are wired.
"""
from __future__ import annotations

XH_PINOUT = ("GND", "V24", "CAN_H", "CAN_L")
# ⚠ BUS B IS THE SAME ORDER AT A DIFFERENT VOLTAGE, AND IT NEEDS ITS OWN NAME (2026-09-22).
# The lever/pedal bus runs at 5 V on JST PH -- a different FAMILY from the 24 V XH motor
# tees precisely so no harness can cross them -- but way 2 is +5 V, not +24 V. Calling it
# XH_PINOUT would have put the string "V24" on a 5 V contact in every board that bound to
# it, which is the same class of silent disagreement this module exists to stop.
# lever_sensor.py had already spelled this tuple inline rather than import a wrong name.
PH_PINOUT = ("GND", "V5", "CAN_H", "CAN_L")

# BUS B's own pinout, and it is a SEPARATE constant on purpose. Bus B runs at 5 V, not
# 24, so pin 2 carries a different rail -- and the whole argument above is that a pin
# order which is wrong is invisible until it puts a rail into a signal. Sharing XH's
# tuple to save four words would mean bus B's pin 2 reading "V24" forever.
#
# The ORDER is deliberately the same shape (return, rail, H, L), so one crimp habit
# still covers the instrument; it is only the rail's NAME that differs.
PH_PINOUT = ("GND", "V5", "CAN_H", "CAN_L")


# THE UI RIBBON, way by way -- ONE list for both ends (2026-10-02). The Pi cap's J5 and the
# UI board's J2 are the same 1.27 mm 2x7 header joined by a straight 14-way IDC cable, so
# way n at one end IS way n at the other. Until today each board carried its own order:
# the cap had the clock beside the ground on ways 1-2, the UI board had the switches on
# 1-5, and the UI board's connector was a 2.54 mm IDC that takes a different ribbon
# altogether. Neither board's DRC could see the other.
# ⚠ THE ORDER IS THE UI BOARD'S, AND THE ROUTER CHOSE IT. The cap's order was tried first
# (clock on ways 1-2) and the UI board would not route: its header's pin 1 is at the end
# AWAY from the display, so every display net had to cross every switch net on two layers
# -- CS_N and RES_N left open on three runs out of three. This order puts the display's
# six lines at the display's end. The clock still runs between two quiet conductors:
# GND on 8, +3V3 (an AC ground) on 10. The cap has a 40-pin header to fan into and can
# take either order; the UI board cannot.
UI_RIBBON = ("SW_A", "SW_B", "SW_C", "SW_D", "SW_PUSH", "ENC_A", "ENC_B",
             "GND", "SCLK", "+3V3", "SDIN", "DC", "CS_N", "RES_N",
             # THE POWER BUTTON'S TWO THROWS, appended so ways 1-14 stay where both
             # boards routed them. They are NOT the Pi's: the cap passes them through to
             # the output board, which is where the supply comes in and the only place it
             # can be cut. Each is shorted to GND (way 8) in one of the button's two
             # states and open in the other -- UP with the button out, DN with it latched
             # in -- and whatever pulls them up has to stay at or under the switch's
             # 12 V 0.3 A (elec/ui_board.py, SW2).
             "PWR_SW_UP", "PWR_SW_DN")


# THE THREE CABLES BETWEEN THE KEYHEAD BOARDS AND THE OUTPUT PANEL, way by way (2026-10-04).
# Each is a straight lead, so way n at one end is way n at the other, and each end's
# generator asserts its connector against the tuple here rather than typing its own.
# Rails are named by voltage; a board maps them onto its own net names.
#   PWR_LINK     output_panel J10 <-> motor_ctrl J3   6-way: the 24 V trunk on two contacts
#                each way, and the power button's two throws going back to the panel
#   LIGHTS_LINK  motor_ctrl J7 <-> pi_cap J4          4-way: fused 24 V for the lights out,
#                the two throws in
#   PI_5V_LINK   motor_ctrl J5 <-> pi_cap J2          6-way PH: the Pi's 5 V on two contacts
#
# ⚠ THE WIRE-TO-BOARD STANDARD (user, 2026-10-04). Every JST lead in the instrument has
# its ways in ONE order and its family set by its voltage:
#     way 1 GND   way 2 power   ways 3, 4 data (or nothing)   -- every 4-way
#     way 5 power   way 6 GND                                  -- a 6-way adds these
#     XH carries 24 V.  PH carries 5 V.
# A 6-way is the 4-way with a second power pair on the far end, mirrored, so the lead reads
# the same from either end and ground is the outside way on both sides. What it buys: a
# lead that will physically seat in the wrong socket of its own family puts ground on
# ground and power on power, and the two families cannot be crossed at all, so 24 V has no
# way onto a 5 V contact.
# "NC" is a way with no conductor: the contact is in the header, nothing is crimped to it.
NC = "NC"
PWR_LINK = ("GND", "V24", "PWR_SW_UP", "PWR_SW_DN", "V24", "GND")
LIGHTS_LINK = ("GND", "V24", "PWR_SW_UP", "PWR_SW_DN")
PI_5V_LINK = ("GND", "V5", NC, NC, "V5", "GND")
# the two lighting drops (pi_cap J3 -> the fret boards, pi_cap J6 -> the foot strip)
LED_DROP = ("GND", "V24", "SCK", "SDT")


def same_ways(ways, link, rails):
    """True if a connector's pin names are `link`, once `rails` ({"+24V": "V24", ...})
    has mapped the board's own net names onto the link's."""
    return tuple(rails.get(w, w) for w in ways) == tuple(link)


def ph_drop_pins():
    """Pin names for a 4-way bus-B drop: the leg blind-mate's PH and ZH housings, and
    the lever/pedal sensor boards' PH. Pin 1 is GND at every one of them."""
    return tuple(PH_PINOUT)


def xh_drop_pins():
    """Pin names for a 4-way drop: one node hanging off the bus."""
    return tuple(XH_PINOUT)


def xh_trunk_pins():
    """Pin names for an 8-way trunk: bus in on 1-4, bus out on 5-8."""
    return (tuple(x + "_IN" for x in XH_PINOUT)
            + tuple(x + "_OUT" for x in XH_PINOUT))


def ph_trunk_pins():
    """Pin names for bus B's 8-way PH trunk: bus in on 1-4, bus out on 5-8."""
    return (tuple(x + "_IN" for x in PH_PINOUT)
            + tuple(x + "_OUT" for x in PH_PINOUT))


def xh_nets(pinout_nets):
    """Map {name: Net} onto trunk pin NUMBERS, so a board binds by order, not by hand.

    Returns [(pin_number, net)] for all eight ways of a trunk connector. The point is
    that a board never writes `j1[3]` beside a net name again: the pairing comes from
    XH_PINOUT, so it cannot drift from it.
    """
    out = []
    for i, name in enumerate(xh_trunk_pins()):
        out.append((i + 1, pinout_nets[name.rsplit("_", 1)[0]]))
    return out
