# -*- coding: utf-8 -*-
"""THE FIRST-FLASH BENCH, drawn: every board that takes firmware, the probe that reaches
it, and EVERY CONDUCTOR between them as a part with a name.

Not the instrument. It exists so that a missing lead is a missing object, seen before the
order goes in rather than on the day (docs/bench-order.md, Tools). Shown by
`py -3.12 -m tools.flash_bench_view`, in a viewer tab of its own.

THREE STATIONS, one board each, set up one at a time (the lever sensor boards are not
ordered yet and are flashed later, in their jig: src/lever_jig.py):
    motor     motor_ctrl                                                      WCH-LinkE
    panel     output_panel                                                    WCH-LinkE
    optical   optical                                                         ST-LINK/V2

A TOOL THERE IS ONE OF is drawn at every station it serves and is ONE unit in the parts
list (`units` below): the WCH-LinkE. What is drawn once per station, because one is made
per board, is that board's own tails.

POWER COMES DOWN THE INSTRUMENT'S OWN CHAIN (user, 2026-10-13: no bench supply). The
brick's plug goes into output_panel J6 and every other board is fed from the board before
it by the harness lead the instrument uses there (CHAIN below): no pigtail, no bench
lead, no second source. The price is in docs/bench-order.md, "Power without a bench
supply": nothing limits the current on first power but F1 and the bus B switch.

THE HOST IS THE INSTRUMENT'S OWN RASPBERRY PI 4 (user, 2026-10-13), bare on the bench on
its own USB-C supply, with no cap on its header. Both probes plug into its USB-A ports,
and so do the two USB leads the instrument already has (USB below). WHAT REACHES A BLANK
CHIP is the probes and nothing else: docs/bench-order.md, "The Pi as the flashing host",
says why for each board.

WHERE EVERY FIGURE COMES FROM
  * pads and headers: the routed boards (elec/geom), through src/board_geom.
  * WCH-LinkE header: the silkscreen of the user's own probe, v1.0, photographed
    2026-10-31 -- a 2x5 with NO pin numbers, so pins are named by signal and by place.
    LINKE_ROWS matches it, both faces. Its pins really run off the board's end, parallel
    to it; they are stood up here only so the leads read.
  * ST-LINK/V2 header: ST UM1075 rev 8, table 4.
  * ⚠ THE PROBES' OWN OUTLINES ARE NOT MEASURED. They are blocks the right kind of size
    with their headers in the right order; nothing here is a fit check on them.
"""
from __future__ import annotations

import cadquery as cq

from cadkit.cables import oct_cable

from . import board_geom as BG

PITCH = 2.54                 # both probes' headers
LEAD_OD = 1.3                # a jumper lead's insulation
SOCKET = (2.5, 2.5, 14.0)    # a jumper lead's 2.54 mm female end

# ── the probes' headers ──────────────────────────────────────────────────────────────
# WCH-LinkE (MuseLab): the two rows as its picture names them, one end to the other.
LINKE_ROWS = (("U_RX", "U_TX", "GND", "3V3", "RST"),          # front row
              ("SWCLK", "GND_B", "SWDIO", "3V3_B", "5V"))     # back row
# ST-LINK/V2, 2x10, numbered as UM1075 table 4: odd pins one row, even the other
STLINK = {"VAPP": 1, "SWDIO": 7, "GND": 8, "SWCLK": 9, "NRST": 15}

# ── what each station wires: (signal, pad on the board, pin on the probe) ────────────
# TP numbers are each board's own: elec/<board>.py, and docs/bench-order.md's table.
WCH = (("SWDIO", "SWDIO"), ("SWCLK", "SWCLK"), ("NRST", "RST"), ("GND", "GND_B"))
TAILS = {
    "motor":   (("SWDIO", "TP1"), ("SWCLK", "TP2"), ("NRST", "TP3"), ("GND", "TP4")),
    "panel":   (("SWDIO", "TP1"), ("SWCLK", "TP2"), ("NRST", "TP3"), ("GND", "TP4")),
    "optical": (("SWDIO", "TP1"), ("SWCLK", "TP2"), ("NRST", "TP3"), ("GND", "TP4"),
                ("VAPP", "TP5")),
}
BOARD = {"motor": "motor_ctrl", "panel": "output_panel", "optical": "optical"}
# THE POWER CHAIN: (lead, from station, header, to station, header, ((net, way out,
# way in), ...)). Each is the instrument's own lead, way for way (elec/harness.py):
# POWER_PAIR and PWR_LINK.
CHAIN = (
    ("optical_power", "panel", "J9", "optical", "J2",
     (("V24", 1, 1), ("GND", 2, 2))),
    ("power_link", "panel", "J10", "motor", "J3",
     (("V24", 1, 1), ("GND", 2, 2), ("PWR_SW_UP", 3, 3), ("PWR_SW_DN", 4, 4),
      ("GND", 5, 5), ("V24", 6, 6))),
)
INLET = ("panel", "J6")      # where the brick's own plug goes
# THE LEADS MADE ONCE, AT INSTRUMENT LENGTH (user, 2026-10-31): crimp to crimp, for the bench
# and then the instrument. The longest conductor as src/wiring.py draws it (2026-10-31:
# optical 173.0, power link 756.9, USB lead 192.2 of jacket + 4.3 of tail), + 10 of slack,
# up to the next 5. Every conductor of a lead is cut the same. (lead, label)
LEAD_MM = {"optical_power": ("OPTICAL POWER", 185), "power_link": ("POWER LINK", 770),
           "motor_usb": ("USB TO PH-4", 210)}
LABEL_H = 9.0                # the labels' letters
# USB: (lead, from, to, what it is). An end is a Pi USB-A port ("pi", n), a probe's own
# socket ("linke", station) / ("stlink",), or a board's connector (station, ref).
USB = (
    ("linke_usb", ("linke", None), ("pi", 0), "the LinkE kit's USB-A to USB-C cable"),
    ("stlink_usb", ("stlink",), ("pi", 1), "USB-A to mini-B (the ST-LINK/V2's socket)"),
    ("motor_usb", ("motor", "J4"), ("pi", 2), "the instrument's USB-A to PHR-4 lead"),
    ("panel_usb", ("panel", "J3"), ("pi", 3), "USB-A to USB-C: the hub's upstream"),
    ("optical_usb", ("optical", "J1"), ("panel", "J4"), "USB-C to USB-C, 100 mm"),
)
_MATED = {(BOARD[s], r) for _n, s0, r0, s1, r1, _w in CHAIN for s, r in ((s0, r0), (s1, r1))}
_MATED |= {("motor_ctrl", "J4")}
# every OTHER header is empty on the bench
UNMATED = tuple((BOARD[s], f["ref"]) for s in BOARD for f in BG.load(BOARD[s])["footprints"]
                if "JST" in f["fpid"] and (BOARD[s], f["ref"]) not in _MATED)
BOARDS = BG.on_the_bench(UNMATED)

RGB = {"SWDIO": (0.10, 0.35, 0.85), "SWCLK": (0.95, 0.80, 0.10), "NRST": (0.92, 0.92, 0.92),
       "GND": (0.05, 0.05, 0.05), "VAPP": (0.95, 0.45, 0.10),
       "V24": (0.85, 0.12, 0.10),
       "PWR_SW_UP": (0.55, 0.55, 0.58), "PWR_SW_DN": (0.55, 0.55, 0.58),
       "probe": (0.04, 0.04, 0.05), "stlink": (0.90, 0.90, 0.92),
       "label": (1.0, 0.85, 0.15), "brick": (0.10, 0.10, 0.11), "pin": (0.83, 0.66, 0.22), "socket": (0.06, 0.06, 0.06),
       "usb": (0.45, 0.25, 0.60), "solder": (0.80, 0.80, 0.82),
       "bench": (0.55, 0.42, 0.28)}

# ── where the stations stand on the bench (z 0 is the bench top) ─────────────────────
AT = {"motor": (-40.0, 0.0), "panel": (95.0, 0.0), "optical": (290.0, 0.0)}
PROBE_DY = 75.2              # a probe's header, +Y of its station
RISE = 12.0                  # how high a lead arcs over the bench
USB_RISE = 44.0              # a USB cable's, over everything else
USB_OD = 3.2                 # a USB cable
PI_AT = (30.0, 200.0)        # the Pi: the middle of its USB end, which faces the stations
LINK_RISE = 28.0             # a harness lead's, over the tails


def _box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def _mv(w, x, y, z=0.0):
    return w.translate((x, y, z))


def _lead(a, b, rise=RISE):
    """A lead from `a` straight up, across and down onto `b` (it enters b from above)."""
    top = max(a[2], b[2]) + rise
    return oct_cable([a, (a[0], a[1], top), (b[0], b[1], top), b], LEAD_OD)


def _label(lead, x, y, z):
    """The floating length label beside a lead, lying flat, read from the bench's -Y side."""
    name, mm = LEAD_MM[lead]
    return (cq.Workplane("XY").text("%s  %d mm" % (name, mm), LABEL_H, 0.8)
            .translate((x, y, z)))


def _socket(p):
    """The jumper lead's female end, standing on header pin `p` (the pin's tip)."""
    w, d, h = SOCKET
    return _box(p[0] - w / 2, p[0] + w / 2, p[1] - d / 2, p[1] + d / 2, p[2] - 5.0, p[2] - 5.0 + h)


def linke(x, y):
    """The WCH-LinkE lying flat, header pins standing up at (x, y): (body, pins,
    {signal: pin tip})."""
    body = _box(-9.0, 9.0, -8.0, 42.0, 0.0, 1.6).union(_box(-4.5, 4.5, 34.0, 42.0, 1.6, 4.8))
    pins, tip = cq.Workplane("XY"), {}
    for r, row in enumerate(LINKE_ROWS):
        for c, sig in enumerate(row):
            px, py = (c - 2) * PITCH, (0.5 - r) * PITCH - 4.0
            pins = pins.union(_box(px - 0.32, px + 0.32, py - 0.32, py + 0.32, 1.6, 10.0))
            tip[sig] = (x + px, y + py, 10.0)
    return _mv(body, x, y), _mv(pins, x, y), tip


def stlink(x, y):
    """The ST-LINK/V2, its 20-pin header's pins standing up at (x, y)."""
    body = _box(-16.0, 16.0, 8.0, 80.0, 0.0, 16.0).union(_box(-14.0, 14.0, -6.0, 8.0, 0.0, 6.0))
    pins, tip = cq.Workplane("XY"), {}
    for n in range(1, 21):
        px, py = ((n - 1) // 2 - 4.5) * PITCH, (0.5 - (n - 1) % 2) * PITCH
        pins = pins.union(_box(px - 0.32, px + 0.32, py - 0.32, py + 0.32, 6.0, 12.0))
        tip[n] = (x + px, y + py, 12.0)
    return _mv(body, x, y), _mv(pins, x, y), {s: tip[n] for s, n in STLINK.items()}


def brick_plug(p):
    """The brick's own plug standing in the inlet at `p`, and a stub of its lead (the
    brick itself is off the bench): a block the right kind of size, not the Kycon part."""
    return (cq.Workplane("XY").circle(5.5).extrude(26.0)
            .union(cq.Workplane("XY").workplane(offset=26.0).circle(3.0).extrude(40.0))
            .translate(p))


def pi4(x, y):
    """The Raspberry Pi 4 (src/pi4b.py, the instrument's own model) lying flat, its USB
    end toward -Y with the middle of that end at (x, y), on 3 mm feet:
    ([(name, solid, rgb)], [the four USB-A mouths], the USB-C power socket's mouth)."""
    from cadkit.kept import kept
    from . import pi4b as P4

    def pt(p):                               # the drawing's frame -> the bench
        return (x - P4.W / 2 + p[1], y + P4.L + 3.0 - p[0], 3.0 + p[2])
    out = [("pi4" + k, kept(P4.part, k).rotate((0, 0, 0), (0, 0, 1), -90)
            .translate((x - P4.W / 2, y + P4.L + 3.0, 3.0)), P4.RGB[c])
           for k, (c, _f) in P4.GROUPS.items()]
    mouths = [pt(P4.usb_mouth(port, up)) for port in (P4.USB2, P4.USB3) for up in (False, True)]
    return out, mouths, pt(P4.usb_c_mouth())


def _usb(a, b, a_dir, b_dir, k):
    """A USB cable from `a` to `b`, leaving each along its own direction."""
    a1 = tuple(a[i] + 14.0 * a_dir[i] for i in range(3))
    b1 = tuple(b[i] + 14.0 * b_dir[i] for i in range(3))
    top = USB_RISE + USB_OD * 1.5 * k
    return oct_cable([a, a1, (a1[0], a1[1], top), (b1[0], b1[1], top), b1, b], USB_OD)


def _board_solid(board):
    """A board in its OWN frame (origin as routed, underside on z 0). The optical board
    is drawn by its own module, where the instrument has it: brought back from there."""
    if board != "optical":
        return BOARDS.solid(board)
    from . import optical_pickup as OP
    dx, dy = OP._silk_to_world()
    return OP.opt_pcb().translate((-dx, -dy, BG.load(board)["thickness_mm"] - OP.PCB_TOP))


def _board_at(station):
    """(place, pad): the board's own frame onto the bench at its station, face up."""
    x0, y0 = AT[station]

    def place(w):
        return w.translate((x0, y0, 0.0))

    def pt(p):
        return (x0 + p[0], y0 + p[1], p[2])
    return place, pt


def components():
    """[(name, solid, (r, g, b))] -- the whole bench."""
    out = []

    def add(name, w, rgb):
        out.append((name, w, rgb))

    xs = [AT[s][0] for s in AT]
    add("bench", _box(min(xs) - 90, max(xs) + 90, -110.0, 310.0, -6.0, 0.0), RGB["bench"])
    ends = {}                    # a USB end -> (point, the way a cable leaves it)
    for st in BOARD:
        b = BOARD[st]
        x0, y0 = AT[st]
        place, pt = _board_at(st)
        add("%s_board" % st, place(_board_solid(b)), BG.mask(b))
        ink = BOARDS.ink(b)
        if ink is not None:
            add("%s_board_silk" % st, place(ink), (0.95, 0.95, 0.92))
        t = BG.load(b)["thickness_mm"]
        # the probe
        if st == "optical":
            body, pins, tip = stlink(x0 - 75.0, y0 - 53.0)
            add("stlink_v2", body, RGB["stlink"])
            add("stlink_v2_pins", pins, RGB["pin"])
            ends[("stlink",)] = ((x0 - 75.0, y0 - 53.0 + 80.0, 8.0), (0.0, 1.0, 0.0))
        else:
            body, pins, tip = linke(x0, y0 + PROBE_DY)
            add("wch_linke__%s" % st, body, RGB["probe"])
            add("wch_linke_pins__%s" % st, pins, RGB["pin"])
            ends[("linke", st)] = ((x0, y0 + PROBE_DY + 42.0, 3.2), (0.0, 1.0, 0.0))
        # the tails: pad -> probe pin, one lead each, a 2.54 female end on the pin
        wch = dict(WCH)
        for sig, tp in TAILS[st]:
            f = BOARDS.footprint(b, tp)
            # A SOLDERED TAIL: the lead's cut end soldered to the bare pad, once
            a = pt((f["x"], f["y"], t))
            b_ = tip[sig if st == "optical" else wch[sig]]
            name = "%s_soldered_tail_%s" % (st, sig.lower())
            add(name, _lead(a, b_), RGB[sig])
            add(name + "__solder", cq.Workplane("XY").circle(1.1).workplane(offset=0.9)
                .circle(LEAD_OD / 2).loft().translate(a), RGB["solder"])
            add(name + "__socket", _socket(b_), RGB["socket"])
    # power: the brick's plug in the inlet, then each harness lead of the chain

    def way_out(st, ref, way):
        """(a way's contact, a point 8 mm out of its housing) on the bench."""
        _place, pt = _board_at(st)
        plug = BOARDS.plug(BOARD[st], ref)
        w, o = pt(plug["ways"][way]), plug["out"]
        return w, (w[0] + 8.0 * o[0], w[1] + 8.0 * o[1], w[2] + 8.0 * o[2])
    _place, pt = _board_at(INLET[0])
    f = BOARDS.footprint(BOARD[INLET[0]], INLET[1])
    add("brick_plug", brick_plug(pt((f["x"], f["y"], BG.load(BOARD[INLET[0]])["thickness_mm"]))),
        RGB["brick"])
    for k, (lead, s0, r0, s1, r1, ways) in enumerate(CHAIN):
        for j, (net, w0, w1) in enumerate(ways):
            a, a1 = way_out(s0, r0, w0)
            b_, b1 = way_out(s1, r1, w1)
            top = max(a1[2], b1[2]) + LINK_RISE + 4.0 * k + LEAD_OD * j
            add("%s_%d_%s" % (lead, w0, net.lower()),
                oct_cable([a, a1, (a1[0], a1[1], top), (b1[0], b1[1], top), b1, b_], LEAD_OD),
                RGB[net])
            if j == 0:
                add("label_" + lead, _label(lead, (a1[0] + b1[0]) / 2, (a1[1] + b1[1]) / 2 + 14.0,
                                            top + 12.0), RGB["label"])
    # the host: the Pi on its own supply, and every USB lead
    pi_parts, mouths, power = pi4(*PI_AT)
    for n, w, rgb in pi_parts:
        add(n, w, rgb)
    add("pi_usb_c_supply", _usb(power, (power[0] - 60.0, power[1], 0.0), (-1.0, 0.0, 0.0),
                                (0.0, 0.0, 1.0), 0), RGB["brick"])
    for n, m in enumerate(mouths):
        ends[("pi", n)] = (m, (0.0, -1.0, 0.0))
    for st, ref in (("motor", "J4"), ("panel", "J3"), ("panel", "J4"), ("optical", "J1")):
        _place, pt = _board_at(st)
        if ref == "J4" and st == "motor":
            plug = BOARDS.plug(BOARD[st], ref)
            ends[(st, ref)] = (pt(plug["ways"][2]), tuple(plug["out"]))
            continue
        f = BOARDS.footprint(BOARD[st], ref)
        t = BG.load(BOARD[st])["thickness_mm"]
        x0_, x1_, y0_, y1_ = f["fab"]
        # a USB-C receptacle's mouth is the end of its body nearest the board's edge
        if st == "panel":
            ends[(st, ref)] = (pt((x0_, (y0_ + y1_) / 2, t + 1.6)), (-1.0, 0.0, 0.0))
        else:
            ends[(st, ref)] = (pt(((x0_ + x1_) / 2, y0_, t + 1.6)), (0.0, -1.0, 0.0))
    for k, (lead, a, b, _what) in enumerate(USB):
        for st in (("motor", "panel") if a == ("linke", None) else [None]):
            (pa, da), (pb, db) = ends[("linke", st) if st else a], ends[b]
            add(lead + ("__%s" % st if st else ""), _usb(pa, pb, da, db, k), RGB["usb"])
            if lead in LEAD_MM:
                add("label_" + lead, _label(lead, (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2,
                                            USB_RISE + 16.0), RGB["label"])
    return out


def unit_of(name: str):
    """One tool drawn at several stations is one thing in the parts list, and so is
    the Pi, which is drawn as one part per colour."""
    if name.startswith("pi4_"):
        return "pi4"
    return name.split("__")[0] if "__" in name else None


def conductors():
    """[(name, from, to)] in words: the list docs/bench-order.md is checked against."""
    rows = []
    wch = dict(WCH)
    for st in TAILS:
        for sig, tp in TAILS[st]:
            to = ("ST-LINK/V2 pin %d" % STLINK[sig] if st == "optical"
                  else "WCH-LinkE %s" % wch[sig].replace("_B", " (back row)"))
            rows.append(("%s_soldered_tail_%s" % (st, sig.lower()),
                         "%s %s (soldered to the pad)" % (BOARD[st], tp), to))
    def end(e):
        if e[0] == "pi":
            return "Pi USB-A port %d" % (e[1] + 1)
        if e[0] in ("linke", "stlink"):
            return "WCH-LinkE" if e[0] == "linke" else "ST-LINK/V2"
        return "%s %s" % (BOARD[e[0]], e[1])
    for lead, a, b, what in USB:
        rows.append((lead, end(a), "%s (%s)" % (end(b), what)))
    rows.append(("pi_usb_c_supply", "the Pi's own USB-C supply", "Pi USB-C power socket"))
    rows.append(("brick_plug", "the brick's own plug", "%s %s" % (BOARD[INLET[0]], INLET[1])))
    for lead, s0, r0, s1, r1, ways in CHAIN:
        for net, w0, w1 in ways:
            rows.append(("%s_%d_%s" % (lead, w0, net.lower()),
                         "%s %s way %d" % (BOARD[s0], r0, w0),
                         "%s %s way %d (%s)" % (BOARD[s1], r1, w1, net)))
    return rows


if __name__ == "__main__":
    for r in conductors():
        print("%-28s %-34s -> %s" % r)
