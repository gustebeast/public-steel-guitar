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

THE ORDER, FOR EVERY JST LEAD IN THE INSTRUMENT: POWER ON THE OUTSIDE, GROUND NEXT TO
IT, DATA IN THE MIDDLE.

    2-way   power, GND
    4-way   power, GND, data, data
    6-way   power, GND, data, data, GND, power
    8-way   power, GND, data, data, data, data, GND, power

A housing wider than four is the 4-way and its mirror, so it reads the same from either
end. XH carries 24 V and PH carries 5 V, and the two families do not mate.

⚠ TWO FAULTS DECIDE IT, AND AN ORDER THAT ANSWERS ONLY ONE IS WRONG.
  1. A WHISKER BETWEEN TWO CRIMPS. Neighbouring ways short far more easily than distant
     ones, so no data way sits beside a power way: its neighbours are ground or data.
     Power's one neighbour is ground, and that short is the supply's own to clear. (A
     strand from the 24 V way to a clock way beside it would be the rail on a Pi GPIO
     through 68 ohm.)
  2. A LEAD PUSHED INTO THE WRONG SOCKET OF ITS FAMILY. There are a dozen 4-way XH leads
     in the instrument and they all seat in each other's sockets. Because EVERY lead has
     the same order, a wrong one still puts power on power and ground on ground. This is
     why the order may not be changed for one lead alone, however good the reason looks
     on that lead: one connector with ground and power swapped turns "the lights lead in
     a tee" from nothing into the trunk shorted through a board's ground.

The trunk is +24 V, GND, CAN_H, CAN_L. An 8-way trunk connector carries the bus in on
ways 1-4 and out on ways 5-8 MIRRORED (CAN_L, CAN_H, GND, +24 V), so a node sits INLINE
on the bus and the chain daisy-chains through it -- how the tees and the sensor boards
are wired -- and the two CAN_L ways meet in the middle, not CAN_L and the rail.
"""
from __future__ import annotations

XH_PINOUT = ("V24", "GND", "CAN_H", "CAN_L")
# ⚠ BUS B IS THE SAME ORDER AT A DIFFERENT VOLTAGE, AND IT NEEDS ITS OWN NAME (2026-09-22).
# The lever/pedal bus runs at 5 V on JST PH -- a different FAMILY from the 24 V XH motor
# tees precisely so no harness can cross them -- but way 1 is +5 V, not +24 V. Calling it
# XH_PINOUT would have put the string "V24" on a 5 V contact in every board that bound to
# it, which is the same class of silent disagreement this module exists to stop.
# lever_sensor.py had already spelled this tuple inline rather than import a wrong name.
# The ORDER is deliberately the same shape (rail, return, H, L), so one crimp habit
# covers the instrument; it is only the rail's NAME that differs.
PH_PINOUT = ("V5", "GND", "CAN_H", "CAN_L")


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
# Each is the standard at the top of this file: power, GND, data, data, and a 6-way adds
# GND, power on the far end.
# "NC" is a way with no conductor: the contact is in the header, nothing is crimped to it.
NC = "NC"
PWR_LINK = ("V24", "GND", "PWR_SW_UP", "PWR_SW_DN", "GND", "V24")
LIGHTS_LINK = ("V24", "GND", "PWR_SW_UP", "PWR_SW_DN")
PI_5V_LINK = ("V5", "GND", NC, NC, "GND", "V5")
# the two lighting drops (pi_cap J3 -> the fret boards, pi_cap J6 -> the foot strip)
LED_DROP = ("V24", "GND", "SCK", "SDT")
# a two-way power lead (output_panel J9 -> the optical board's J2)
POWER_PAIR = ("V24", "GND")


def check_ways(ways, power, ground=("GND",), where=""):
    """Raise unless `ways` (a connector's names, way 1 first) keeps the standard: every
    way named in `power` at an END or beside a ground, and no other way beside power.
    Generators call it on every JST they build, so an order typed by hand cannot ship."""
    ways = tuple(ways)
    for i, w in enumerate(ways):
        if w not in power:
            continue
        for j in (i - 1, i + 1):
            if 0 <= j < len(ways) and ways[j] not in ground and ways[j] not in power:
                raise AssertionError(
                    "%s: way %d (%s) carries a rail and way %d (%s) beside it is neither "
                    "ground nor that rail -- elec/harness.py, the standard"
                    % (where or "connector", i + 1, w, j + 1, ways[j]))
    return ways


def same_ways(ways, link, rails):
    """True if a connector's pin names are `link`, once `rails` ({"+24V": "V24", ...})
    has mapped the board's own net names onto the link's."""
    return tuple(rails.get(w, w) for w in ways) == tuple(link)


def ph_drop_pins():
    """Pin names for a 4-way bus-B drop: the leg blind-mate's PH and ZH housings, and
    the lever/pedal sensor boards' PH. Pin 1 is +5 V at every one of them."""
    return tuple(PH_PINOUT)


def xh_drop_pins():
    """Pin names for a 4-way drop: one node hanging off the bus."""
    return tuple(XH_PINOUT)


def xh_trunk_pins():
    """Pin names for an 8-way trunk: bus in on 1-4, bus out on 5-8 mirrored."""
    return (tuple(x + "_IN" for x in XH_PINOUT)
            + tuple(x + "_OUT" for x in reversed(XH_PINOUT)))


def ph_trunk_pins():
    """Pin names for bus B's 8-way PH trunk: bus in on 1-4, bus out on 5-8 mirrored."""
    return (tuple(x + "_IN" for x in PH_PINOUT)
            + tuple(x + "_OUT" for x in reversed(PH_PINOUT)))


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
