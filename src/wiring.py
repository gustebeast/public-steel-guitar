"""Wire harness: net-colored round cables, modeled as cylinder chains.

One component per electrical NET (so splices automatically share a color;
every unique source-dest pairing is its own component/color):

  wire_pickup  white   pickup hot+gnd coax -> splice -> {audio shield, TS jack}
  wire_can     green   CAN bus: transceiver -> servo daisy chain (one net)
  wire_power   red     DC inlet -> servo power chain -> buck input (one net)
  wire_usb     blue    USB-C panel -> Pi 5 (gadget/audio-interface port)
  wire_link    purple  Teensy <-> Pi data link
  wire_canjmp  orange  Teensy CAN TX/RX <-> transceiver logic side
  wire_tdm     teal    CS42448 stack TDM -> Pi

Routing: a 4-lane floor trunk at z -70.6 (under the motor bodies, over the
open floor) passes every cross-rib through diamond raceways cut at the lane
y's. Per-motor stubs dive to z -74.65 (under the lanes) and rise into each
motor body at a y chosen >= 4.2 from every lane. In the bay the wires fly
OVER the board stacks (z -33..-41, mutually separated >= 4.5 at crossings)
and drop into their targets. Wire ends deliberately clip ~1-2 mm into their
source / destination bodies to show the connection (whitelisted in the
checker); everywhere else the gate enforces real clearance.

Wires are modeled at the demo pose (pickup at its parked X) - physically
the pickup run gets a service loop.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import electronics as EL

WIRE_D = 3.5

# floor-trunk lane y's (rib raceway diamonds are cut at these, z -70.65)
LANE_USB, LANE_PWR, LANE_CAN, LANE_PU = -91.0, -80.5, -70.0, -59.5
# (motor 0's faceplate wall + foot reach south to y -56.8 at x -125..-95,
#  so the nearest lane sits at -59.5; the rest space 10.5 apart for the
#  rib raceway diamonds)
LANE_Z = -70.6
STUB_Z = -74.65          # under-lane crossing level for the motor stubs
RIB_RACE_Y = (LANE_USB, LANE_PWR, LANE_CAN, LANE_PU)


def _wire(pts, d=WIRE_D):
    """Polyline cable: cylinders between points + sphere elbows."""
    r = d / 2
    out = cq.Workplane("XY")
    for a, b in zip(pts, pts[1:]):
        va, vb = cq.Vector(*a), cq.Vector(*b)
        ax = vb - va
        if ax.Length < 1e-6:
            continue
        out = out.union(cq.Workplane("XY").add(
            cq.Solid.makeCylinder(r, ax.Length, va, ax)))
    for p in pts[1:-1]:
        out = out.union(cq.Workplane("XY").add(
            cq.Solid.makeSphere(r, cq.Vector(*p), angleDegrees1=-90)))
    return out


def _riser_y(sy):
    """Stub riser y inside the motor body footprint (body y = sy-84..sy+4),
    kept >= 4.2 away from every trunk lane so the vertical run can't shave
    a lane cable."""
    for cand in (sy - 40.0, sy - 36.0, sy - 44.0, sy - 32.0, sy - 48.0):
        if all(abs(cand - L) >= 4.2 for L in RIB_RACE_Y):
            return cand
    return sy - 30.0


def _chain(lane_y, x_off, x_from, x_to):
    """A trunk run along lane_y with a dive-under stub into each motor:
    trunk at LANE_Z, stub drops to STUB_Z, runs to the riser y, rises into
    the motor body bottom (clip ~2). Returns the point list."""
    pts = [(x_from, lane_y, LANE_Z)]
    motors = sorted(((D.motor_pos(i)[0], D.motor_pos(i)[1]) for i in range(10)),
                    key=lambda m: m[0], reverse=(x_from > x_to))
    for mx, sy in motors:
        sx = mx + x_off
        if not (min(x_from, x_to) < sx < max(x_from, x_to)):
            continue
        ry = _riser_y(sy)
        pts += [(sx, lane_y, LANE_Z), (sx, lane_y, STUB_Z),
                (sx, ry, STUB_Z), (sx, ry, -63.0),          # ~2 into the body
                (sx, ry, STUB_Z), (sx, lane_y, STUB_Z),
                (sx, lane_y, LANE_Z)]
    pts.append((x_to, lane_y, LANE_Z))
    return pts


def build_wires():
    """Returns [(name, workplane)] for every net."""
    out = []
    shield_top = EL.BOARD_Z + 1.0 + 11.0 + EL.BD_T      # Teensy shield top

    # -- pickup coax (white): pickup -> drop column -> splice at the floor;
    #    west branch to the audio shield, east branch to the TS jack
    top = [(-50.0, -45.0, -5.0),                 # starts inside the pickup
           (-18.0, -45.0, -11.0),                # over the bar, under strings
           (-18.0, LANE_PU, -40.0),              # drop past the bar end
           (-18.0, LANE_PU, LANE_Z)]             # splice point
    west = [(-18.0, LANE_PU, LANE_Z), (-522.0, LANE_PU, LANE_Z),
            (-522.0, LANE_PU, -38.0),            # rise east of the tray
            (-560.0, LANE_PU, -38.0),            # fly west over the bay
            (-560.0, -67.0, -38.0),              # jog over the Teensy stack
            (-560.0, -67.0, shield_top - 1.0)]   # drop into the shield
    east = [(-18.0, LANE_PU, LANE_Z), (-8.0, LANE_PU, LANE_Z),
            (-8.0, EL.TS_Y, EL.JACK_Z), (5.0, EL.TS_Y, EL.JACK_Z)]
    out.append(("wire_pickup", _wire(top + west[1:]).union(_wire(east))))

    # -- CAN bus (green): transceiver -> over the bay aisle (y -45) -> dives
    #    west of all belts -> floor lane -> stub into every motor
    head = [(-590.0, -45.0, -57.0),              # clip into the transceiver
            (-590.0, -45.0, -38.0),
            (-525.0, -45.0, -38.0),              # fly east over the bay
            (-525.0, -45.0, STUB_Z),             # drop west of belts/motor 9
            (-525.0, LANE_CAN, STUB_Z),          # cross under the pickup lane
            (-525.0, LANE_CAN, LANE_Z)]
    chain = _chain(LANE_CAN, 14.0, -525.0, -94.0)
    out.append(("wire_can", _wire(head + chain[1:])))

    # -- power (red): DC inlet -> floor lane west with a stub to every motor
    #    -> rises east of the tray -> ends in the buck converter
    head = [(5.0, EL.DC_Y, EL.JACK_Z), (-12.0, EL.DC_Y, EL.JACK_Z),
            (-12.0, LANE_PWR, LANE_Z)]
    chain = _chain(LANE_PWR, 18.0, -12.0, -523.0)
    tail = [(-523.0, LANE_PWR, -50.0),           # rise east of the tray
            (-540.0, LANE_PWR, -50.0),
            (-540.0, -88.0, -50.0)]              # ends inside a buck cap
    out.append(("wire_power", _wire(head + chain[1:] + tail)))

    # -- USB (blue): USB-C panel -> floor lane -> rises east of the tray ->
    #    flies over everything at z -33 -> drops into the Pi USB block
    pts = [(5.0, EL.USB_Y, EL.JACK_Z), (-16.0, EL.USB_Y, EL.JACK_Z),
           (-16.0, LANE_USB, LANE_Z), (-524.0, LANE_USB, LANE_Z),
           (-524.0, LANE_USB, -33.0),
           (-548.0, LANE_USB, -33.0), (-548.0, 10.0, -33.0),
           (-548.0, 10.0, -44.0)]
    out.append(("wire_usb", _wire(pts)))

    # -- Teensy <-> Pi link (purple): over the aisle into the Pi USB block
    pts = [(-554.0, -67.0, shield_top - 0.6), (-554.0, -67.0, -42.5),
           (-554.0, 5.0, -42.5), (-554.0, 5.0, -45.0)]
    out.append(("wire_link", _wire(pts)))

    # -- Teensy <-> CAN transceiver (orange): across the y -58..-52 aisle
    pts = [(-598.0, -66.0, shield_top - 0.6), (-598.0, -66.0, -41.0),
           (-598.0, -44.0, -41.0), (-598.0, -44.0, -57.0)]
    out.append(("wire_canjmp", _wire(pts)))

    # -- CS42448 TDM -> Pi (teal): up over its own header, over the Teensy
    #    stack at z -33, down into the Pi board
    pts = [(-580.0, -100.0, -43.0), (-580.0, -100.0, -33.0),
           (-580.0, -5.0, -33.0), (-580.0, -5.0, -57.0)]
    out.append(("wire_tdm", _wire(pts)))

    return out


# what each net is ALLOWED to touch (its source/destination bodies);
# everything else a wire grazes is a routing bug the gate reports
WIRE_OK = {
    "wire_pickup": {"pickup", "teensy_stack", "ts_jack"},
    "wire_can":    {"can_xcvr", "motor"},
    "wire_power":  {"dc_jack", "motor", "buck"},
    "wire_usb":    {"usbc_jack", "pi5"},
    "wire_link":   {"teensy_stack", "pi5"},
    "wire_canjmp": {"teensy_stack", "can_xcvr"},
    "wire_tdm":    {"cs_stack", "pi5"},
}
