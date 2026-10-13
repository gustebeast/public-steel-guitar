# -*- coding: utf-8 -*-
"""THE RASPBERRY PI 4 MODEL B, as bought: its laminate, every connector, the chips and the
small parts, each in its own colour. One model for the instrument (src/electronics.py
places it) and for the first-flash bench (src/flash_bench.py).

WHERE EVERY FIGURE COMES FROM: Raspberry Pi's own mechanical drawing, RP-008343-DS-1
(datasheets.raspberrypi.com/rpi4/raspberry-pi-4-mechanical-drawing.pdf, read 2026-10-13).
The drawing is vector, so every outline below was READ OFF ITS LINES at the scale its own
85 x 56 gives, not scaled by eye: the connectors' and chips' rectangles, the four holes, and
the 128 small parts in SMALL. Its `Z=` callouts are heights over the board's top face.

  THE FRAME IS THE DRAWING'S: x along the 85 mm side from the SD-card end to the USB end,
  y from the edge with USB-C, HDMI and the audio jack to the edge with the 40-way header,
  z up from the laminate's UNDERSIDE.

⚠ WHAT THE DRAWING DOES NOT GIVE, and is therefore an estimate here:
  * the laminate's thickness (T, the project's own board thickness);
  * any height with no `Z=`: the memory, the radio's can, the other chips, the small parts;
  * the inside of every port (openings, tongues): the usual sizes for that connector;
  * NOTHING UNDER THE BOARD is drawn: the microSD socket is not on the drawing.
"""
from __future__ import annotations

import cadquery as cq

L, W, T = 85.0, 56.0, 1.6
CORNER_R = 3.0
HOLE_D = 2.7
HOLES = ((3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5))

# the 40-way header: centre, base height, overall height (Z=8.5)
HDR = (32.5, 52.5)
HDR_BASE_H = 2.5
HDR_H = 8.5
PIN = 0.64
PITCH = 2.54
POE = (61.5, 46.35)              # the four-pin PoE header, 6.14 under the top edge

# ports on the USB end: centre along y, (width, depth, height), and x of the mouth
ETH = (45.75, (15.5, 21.36, 13.5), 88.0)
USB2 = (9.0, (14.5, 17.5, 16.0), 88.0)
USB3 = (27.0, (14.5, 17.5, 16.0), 88.0)
# ports on the y = 0 edge: centre along x, (width, depth, height), y of the mouth
USB_C = (11.2, (8.65, 7.39, 3.2), -1.24)
HDMI = ((26.0, (7.2, 7.95, 3.0), -1.43), (39.5, (7.2, 7.95, 3.0), -1.43))
JACK = (54.0, (7.0, 12.5, 6.0), 0.0)          # ...and its barrel stands 2.5 past the edge
JACK_BARREL = (6.0, 2.5)
# the two 15-way ribbon sockets (display, camera): centre, (width, length), Z=5.5
FFC = ((3.48, 28.0), (47.02, 11.51))
FFC_BODY = (3.95, 22.4, 5.5)
FFC_LATCH = ((5.0, 28.0), (45.5, 11.51))      # each one's latch bar, 0.9 x 16.0
# chips: centre, (x, y), height
SOC = ((29.25, 32.5), (15.0, 15.0), 2.4)      # Z=2.4: the processor under its lid
RADIO = ((12.0, 42.6), (10.78, 13.0), 1.9)    # the wireless module's can
CHIPS = (((44.79, 32.5), (11.5, 15.0), 1.0),  # memory
         ((59.5, 24.0), (8.0, 8.0), 0.9),     # USB controller
         ((58.5, 38.0), (6.0, 6.0), 0.9),     # Ethernet PHY
         ((9.89, 12.21), (5.0, 5.0), 0.9))    # power management

# EVERY OTHER OUTLINE ON THE DRAWING: (centre x, centre y, x size, y size). The larger
# ones are drawn as dark parts 2.0 or 0.9 tall, the rest as passives 0.5 tall.
SMALL = (
    (0.55, 7.90, 0.39, 1.30), (0.55, 11.50, 0.39, 1.30), (0.65, 41.30, 0.31, 0.60), (0.65, 42.60, 0.31, 0.60),
    (1.09, 7.90, 0.70, 1.59), (1.09, 11.51, 0.70, 1.61), (3.01, 41.30, 0.31, 0.60), (3.01, 42.60, 0.31, 0.60),
    (3.20, 9.15, 1.20, 1.98), (3.20, 15.30, 1.20, 2.00), (4.80, 11.50, 1.59, 0.81), (4.80, 12.90, 1.59, 0.81),
    (5.01, 47.85, 0.64, 0.64), (5.50, 9.20, 2.00, 2.50), (5.50, 15.30, 2.00, 2.50), (6.67, 18.09, 0.95, 1.20),
    (8.10, 18.11, 2.81, 2.00), (8.30, 16.20, 1.61, 0.81), (9.01, 7.99, 0.99, 0.50), (9.52, 18.09, 0.95, 1.20),
    (10.91, 7.99, 0.99, 0.50), (11.61, 17.09, 1.20, 2.00), (12.00, 20.50, 7.60, 2.00), (12.30, 7.90, 0.52, 1.01),
    (14.00, 31.00, 1.03, 1.98), (14.10, 9.20, 2.00, 2.50), (14.90, 16.10, 3.99, 3.99), (15.01, 11.50, 1.59, 0.81),
    (15.01, 12.90, 1.59, 0.81), (16.10, 9.31, 0.81, 1.59), (18.20, 15.89, 1.20, 2.00), (18.30, 24.99, 0.87, 1.98),
    (18.70, 47.59, 1.01, 0.50), (18.70, 48.60, 1.01, 0.50), (20.00, 8.50, 3.59, 4.40), (20.10, 15.89, 1.20, 2.00),
    (21.91, 40.85, 0.60, 0.31), (22.59, 19.00, 0.93, 1.98), (24.19, 19.00, 0.87, 1.98), (25.89, 47.20, 0.64, 0.62),
    (27.43, 19.00, 0.91, 1.98), (28.51, 22.60, 0.50, 0.99), (30.50, 3.00, 0.60, 0.50), (31.59, 3.01, 1.59, 3.00),
    (31.70, 6.10, 1.14, 1.14), (32.30, 7.55, 0.60, 0.31), (32.70, 2.04, 0.62, 0.50), (32.70, 3.95, 0.62, 0.50),
    (32.80, 16.70, 0.83, 2.00), (33.20, 3.01, 0.60, 0.31), (33.79, 6.10, 1.16, 1.14), (36.41, 43.40, 0.64, 0.62),
    (39.20, 43.00, 1.01, 0.52), (41.77, 44.74, 0.87, 1.98), (43.38, 44.74, 0.91, 1.98), (44.00, 40.70, 0.62, 0.31),
    (45.60, 40.70, 0.60, 0.31), (46.62, 44.74, 0.83, 1.98), (48.23, 44.74, 0.91, 1.98), (48.49, 41.20, 2.00, 1.22),
    (51.50, 15.40, 1.98, 3.00), (51.70, 30.40, 1.20, 2.00), (52.89, 19.59, 3.00, 2.00), (52.90, 17.91, 0.99, 0.50),
    (53.70, 23.10, 0.60, 0.31), (53.70, 23.70, 0.60, 0.31), (53.70, 24.30, 0.60, 0.31), (53.70, 24.90, 0.60, 0.31),
    (53.70, 25.50, 0.60, 0.31), (53.70, 26.10, 0.60, 0.31), (54.00, 14.30, 0.50, 1.01), (54.00, 16.20, 0.50, 1.01),
    (54.89, 13.99, 0.31, 0.60), (55.60, 13.99, 0.31, 0.60), (55.60, 16.30, 2.00, 1.20), (56.30, 13.99, 0.31, 0.60),
    (56.70, 33.10, 0.50, 1.01), (57.20, 14.30, 0.50, 1.01), (57.20, 16.20, 0.50, 1.01), (57.89, 32.60, 0.81, 1.61),
    (58.59, 13.00, 0.60, 0.52), (59.14, 32.40, 0.50, 1.01), (59.70, 7.99, 1.98, 1.20), (59.70, 10.10, 1.98, 1.20),
    (59.70, 13.00, 1.61, 3.00), (60.59, 32.60, 0.81, 1.61), (60.80, 12.05, 0.60, 0.52), (60.80, 13.95, 0.60, 0.52),
    (61.50, 17.21, 3.20, 2.40), (62.30, 8.00, 0.50, 1.01), (62.30, 10.10, 0.50, 0.99), (62.59, 32.85, 1.20, 2.00),
    (62.80, 35.99, 0.60, 0.31), (63.00, 34.99, 0.99, 0.50), (63.19, 12.70, 1.20, 0.41), (63.20, 12.00, 1.80, 0.99),
    (63.20, 14.50, 1.01, 0.50), (63.80, 17.20, 0.31, 0.60), (64.20, 38.50, 2.48, 2.48), (64.20, 41.80, 2.48, 2.46),
    (65.10, 9.01, 0.81, 1.61), (65.39, 20.65, 0.60, 0.31), (65.39, 24.90, 0.60, 0.31), (65.49, 6.21, 0.31, 0.60),
    (65.90, 13.29, 2.00, 2.50), (66.54, 8.40, 0.39, 0.60), (66.54, 10.61, 0.39, 0.60), (66.89, 4.75, 0.60, 0.41),
    (66.89, 5.70, 0.60, 0.41), (66.89, 6.65, 0.60, 0.41), (66.99, 2.90, 0.50, 1.01), (67.39, 15.91, 2.00, 1.20),
    (67.39, 17.91, 2.00, 1.20), (67.40, 19.50, 0.99, 0.50), (67.49, 9.50, 2.91, 1.61), (67.49, 10.61, 0.39, 0.60),
    (67.69, 33.40, 4.30, 7.31), (67.99, 5.70, 1.59, 2.89), (68.00, 2.90, 0.50, 1.01), (68.19, 13.30, 1.20, 1.98),
    (68.44, 8.40, 0.39, 0.60), (68.44, 10.61, 0.39, 0.60), (68.99, 2.90, 0.50, 1.01), (69.09, 4.75, 0.62, 0.41),
    (69.09, 5.70, 0.62, 0.41), (69.09, 6.65, 0.62, 0.41), (69.59, 8.50, 0.50, 1.01), (69.59, 10.50, 0.50, 1.01),
)

RGB = {"board": (0.05, 0.38, 0.20), "shell": (0.78, 0.79, 0.81), "lid": (0.74, 0.75, 0.77),
       "black": (0.07, 0.07, 0.08), "pin": (0.83, 0.68, 0.25), "cream": (0.90, 0.87, 0.78),
       "blue": (0.10, 0.30, 0.75), "passive": (0.36, 0.25, 0.14)}
# the parts, by what each is made of: name suffix -> (colour, finish)
GROUPS = {"": ("board", "board"), "_shells": ("shell", "steel"), "_lids": ("lid", "steel"),
          "_black": ("black", "nylon"), "_pins": ("pin", "gold"), "_ffc": ("cream", "nylon"),
          "_usb3": ("blue", "nylon"), "_passives": ("passive", "painted")}


def _box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def _at(c, size, h, z0=T):
    return _box(c[0] - size[0] / 2, c[0] + size[0] / 2, c[1] - size[1] / 2,
                c[1] + size[1] / 2, z0, z0 + h)


def _all(solids):
    """Several solids that do not touch, as one part."""
    return cq.Workplane("XY").newObject(
        [cq.Compound.makeCompound([v for s in solids for v in s.vals()])])


def _end_port(port, openings, recess=6.0):
    """A port on the USB end: its shell, with `openings` [(z centre, width, height)]
    let in `recess` from the mouth."""
    yc, (w, d, h), x1 = port
    shell = _box(x1 - d, x1, yc - w / 2, yc + w / 2, T, T + h)
    for zc, ow, oh in openings:
        shell = shell.cut(_box(x1 - recess, x1, yc - ow / 2, yc + ow / 2,
                               T + zc - oh / 2, T + zc + oh / 2))
    return shell


def _edge_port(port, ow, oh, recess=4.0):
    """A port on the y = 0 edge, likewise: (shell, the tongue inside it)."""
    xc, (w, d, h), y0 = port
    shell = _box(xc - w / 2, xc + w / 2, y0, y0 + d, T, T + h)
    shell = shell.cut(_box(xc - ow / 2, xc + ow / 2, y0, y0 + recess, T + h / 2 - oh / 2,
                           T + h / 2 + oh / 2))
    tongue = _box(xc - ow / 2 + 0.6, xc + ow / 2 - 0.6, y0 + 0.8, y0 + recess,
                  T + h / 2 - 0.3, T + h / 2 + 0.3)
    return shell, tongue


USB_A_OPEN = (12.5, 5.1)         # a USB-A mouth
USB_A_Z = (4.4, 12.0)            # the two mouths of a stack, over the board's top face


def parts() -> dict:
    """{suffix: solid} in the drawing's frame -- "" is the laminate; GROUPS says what
    colour and finish each is. No two of them share volume."""
    board = (cq.Workplane("XY").box(L, W, T, centered=False).edges("|Z").fillet(CORNER_R))
    for x, y in HOLES:
        board = board.cut(cq.Workplane("XY").circle(HOLE_D / 2).extrude(T).translate((x, y, 0)))

    shells, black, blue = [], [], []
    shells.append(_end_port(ETH, [(6.6, 11.7, 8.2)], recess=11.0))
    for port, tongues in ((USB2, black), (USB3, blue)):
        shells.append(_end_port(port, [(z,) + USB_A_OPEN for z in USB_A_Z]))
        yc, x1 = port[0], port[2]
        for z in USB_A_Z:                        # the tongue in each mouth
            tongues.append(_box(x1 - 6.0, x1 - 1.0, yc - 5.6, yc + 5.6, T + z + 0.3, T + z + 2.2))
    usbc, tongue = _edge_port(USB_C, 8.0, 2.4)
    shells.append(usbc)
    black.append(tongue)
    for port in HDMI:
        shell, tongue = _edge_port(port, 5.9, 2.2)
        shells.append(shell)
        black.append(tongue)

    # the audio jack: a moulded body, its barrel past the edge, the socket's bore
    xc, (w, d, h), y0 = JACK
    jack = _box(xc - w / 2, xc + w / 2, y0, y0 + d, T, T + h).union(
        cq.Workplane("XZ").circle(JACK_BARREL[0] / 2).extrude(JACK_BARREL[1])
        .translate((xc, y0, T + h / 2)))
    jack = jack.cut(cq.Workplane("XZ").circle(1.8).extrude(9.0)
                    .translate((xc, y0 + 9.0 - JACK_BARREL[1], T + h / 2)))
    black.append(jack)

    # the headers: a moulded base and the pins standing through it
    def header(c, cols, rows):
        base = _at(c, (cols * PITCH, rows * PITCH - 0.08), HDR_BASE_H)
        pins = []
        for i in range(cols):
            for j in range(rows):
                px = c[0] + (i - (cols - 1) / 2) * PITCH
                py = c[1] + (j - (rows - 1) / 2) * PITCH
                pin = _box(px - PIN / 2, px + PIN / 2, py - PIN / 2, py + PIN / 2, T, T + HDR_H)
                base = base.cut(pin)
                pins.append(pin)
        return base, pins
    base, pins = header(HDR, 20, 2)
    base2, pins2 = header(POE, 2, 2)
    black += [base, base2]
    pins = pins + pins2

    ffc = []
    for c, latch in zip(FFC, FFC_LATCH):
        bar = _at(latch, (0.9, 16.0), FFC_BODY[2])
        ffc.append(_at(c, FFC_BODY[:2], FFC_BODY[2]).cut(bar))
        black.append(bar)

    lids = [_at(SOC[0], SOC[1], SOC[2]), _at(RADIO[0], RADIO[1], RADIO[2])]
    black += [_at(c, s, h) for c, s, h in CHIPS]
    passives = []
    for x, y, w, h in SMALL:
        if min(w, h) >= 3.5:
            black.append(_at((x, y), (w, h), 2.0))
        elif min(w, h) >= 1.5:
            black.append(_at((x, y), (w, h), 0.9))
        else:
            passives.append(_at((x, y), (w, h), 0.5))
    # two outlines on the drawing can lap (a part and its land pattern): one solid there
    black = _all(black)
    small = passives[0]
    for s in passives[1:]:
        small = small.union(s)
    return {"": board, "_shells": _all(shells), "_lids": _all(lids), "_black": black,
            "_pins": _all(pins), "_ffc": _all(ffc), "_usb3": _all(blue),
            "_passives": small.cut(black)}


def part(suffix: str) -> cq.Workplane:
    """One of parts(), by its suffix: what cadkit.kept draws once and then reads."""
    return parts()[suffix]


def usb_mouth(port, upper: bool):
    """(x, y, z) of the middle of a USB-A mouth on the USB end, in the drawing's frame."""
    return (port[2], port[0], T + USB_A_Z[1 if upper else 0])


def usb_c_mouth():
    """(x, y, z) of the USB-C power socket's mouth."""
    return (USB_C[0], USB_C[2], T + USB_C[1][2] / 2)
