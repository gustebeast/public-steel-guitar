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

# BUS B's own pinout, and it is a SEPARATE constant on purpose. Bus B runs at 5 V, not
# 24, so pin 2 carries a different rail -- and the whole argument above is that a pin
# order which is wrong is invisible until it puts a rail into a signal. Sharing XH's
# tuple to save four words would mean bus B's pin 2 reading "V24" forever.
#
# The ORDER is deliberately the same shape (return, rail, H, L), so one crimp habit
# still covers the instrument; it is only the rail's NAME that differs.
PH_PINOUT = ("GND", "V5", "CAN_H", "CAN_L")


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
