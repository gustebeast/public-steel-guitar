# -*- coding: utf-8 -*-
"""THE FIRST-FLASH BENCH, drawn: every board that takes firmware, the probe that reaches
it, and EVERY CONDUCTOR between them as a part with a name.

Not the instrument. It exists so that a missing lead is a missing object, seen before the
order goes in rather than on the day (docs/bench-order.md, Tools). Shown by
`py -3.12 -m tools.flash_bench_view`, in a viewer tab of its own.

FOUR STATIONS, one board each, set up one at a time:
    lever     the jig (src/lever_jig.py) with a lever board face down in it;  WCH-LinkE
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

WHERE EVERY FIGURE COMES FROM
  * pads and headers: the routed boards (elec/geom), through src/board_geom.
  * WCH-LinkE header: the MuseLab board's own picture on its Tindie listing, read
    2026-10-12 -- a 2x5 with NO pin numbers, so pins are named by signal and by place.
    WCH's manual gives the layout only as a figure that could not be read: CHECK THE
    SILKSCREEN of the probe that arrives against LINKE_ROWS before the first wire.
  * ST-LINK/V2 header: ST UM1075 rev 8, table 4.
  * ⚠ THE PROBES' OWN OUTLINES ARE NOT MEASURED. They are blocks the right kind of size
    with their headers in the right order; nothing here is a fit check on them.
"""
from __future__ import annotations

import cadquery as cq

from cadkit.cables import oct_cable

from . import board_geom as BG
from . import lever_jig as LJ

PITCH = 2.54                 # both probes' headers
LEAD_OD = LJ.LEAD_OD
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
    "lever":   (("SWDIO", "TP1"), ("SWCLK", "TP2"), ("GND", "TP3"), ("NRST", "TP4")),
    "motor":   (("SWDIO", "TP1"), ("SWCLK", "TP2"), ("NRST", "TP3"), ("GND", "TP4")),
    "panel":   (("SWDIO", "TP1"), ("SWCLK", "TP2"), ("NRST", "TP3"), ("GND", "TP4")),
    "optical": (("SWDIO", "TP1"), ("SWCLK", "TP2"), ("NRST", "TP3"), ("GND", "TP4"),
                ("VAPP", "TP5")),
}
BOARD = {"lever": "lever_sensor", "motor": "motor_ctrl", "panel": "output_panel",
         "optical": "optical"}
# THE POWER CHAIN: (lead, from station, header, to station, header, ((net, way out,
# way in), ...)). Each is the instrument's own lead, way for way (elec/harness.py):
# POWER_PAIR, PWR_LINK, and a bus B drop (PH_PINOUT into the first four ways of J1).
CHAIN = (
    ("optical_power", "panel", "J9", "optical", "J2",
     (("V24", 1, 1), ("GND", 2, 2))),
    ("power_link", "panel", "J10", "motor", "J3",
     (("V24", 1, 1), ("GND", 2, 2), ("PWR_SW_UP", 3, 3), ("PWR_SW_DN", 4, 4),
      ("GND", 5, 5), ("V24", 6, 6))),
    ("bus_b_drop", "motor", "J6", "lever", "J1",
     (("V5", 1, 1), ("GND", 2, 2), ("CAN_H", 3, 3), ("CAN_L", 4, 4))),
)
INLET = ("panel", "J6")      # where the brick's own plug goes
_MATED = {(BOARD[s], r) for _n, s0, r0, s1, r1, _w in CHAIN for s, r in ((s0, r0), (s1, r1))}
# every OTHER header is empty on the bench
UNMATED = tuple((BOARD[s], f["ref"]) for s in BOARD for f in BG.load(BOARD[s])["footprints"]
                if "JST" in f["fpid"] and (BOARD[s], f["ref"]) not in _MATED)
BOARDS = BG.on_the_bench(UNMATED)

RGB = {"SWDIO": (0.10, 0.35, 0.85), "SWCLK": (0.95, 0.80, 0.10), "NRST": (0.92, 0.92, 0.92),
       "GND": (0.05, 0.05, 0.05), "VAPP": (0.95, 0.45, 0.10),
       "V24": (0.85, 0.12, 0.10), "V5": (0.85, 0.12, 0.10),
       "CAN_H": (0.95, 0.80, 0.10), "CAN_L": (0.10, 0.60, 0.20),
       "PWR_SW_UP": (0.55, 0.55, 0.58), "PWR_SW_DN": (0.55, 0.55, 0.58),
       "probe": (0.10, 0.25, 0.60), "stlink": (0.90, 0.90, 0.92),
       "brick": (0.10, 0.10, 0.11), "pin": (0.83, 0.66, 0.22), "socket": (0.06, 0.06, 0.06),
       "jig": (0.90, 0.45, 0.10), "bench": (0.55, 0.42, 0.28)}

# ── where the stations stand on the bench (z 0 is the bench top) ─────────────────────
AT = {"lever": (-150.0, 0.0), "motor": (-40.0, 0.0), "panel": (95.0, 0.0),
      "optical": (290.0, 0.0)}
PROBE_DY = 75.2              # a probe's header, +Y of its station
RISE = 12.0                  # how high a lead arcs over the bench
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


def _board_solid(board):
    """A board in its OWN frame (origin as routed, underside on z 0). The optical board
    is drawn by its own module, where the instrument has it: brought back from there."""
    if board != "optical":
        return BOARDS.solid(board)
    from . import optical_pickup as OP
    dx, dy = OP._silk_to_world()
    return OP.opt_pcb().translate((-dx, -dy, BG.load(board)["thickness_mm"] - OP.PCB_TOP))


def _board_at(station):
    """(place, pad): the board's own frame onto the bench at its station. The lever board
    lies FACE DOWN in the jig; the others face up on the bench."""
    x0, y0 = AT[station]
    t = BG.load(BOARD[station])["thickness_mm"]
    if station == "lever":
        dz = -LJ.Z_BASE                      # the jig's base on the bench

        def place(w):
            return w.rotate((0, 0, 0), (0, 1, 0), 180).translate((x0, y0, dz + t))

        def pt(p):
            return (x0 - p[0], y0 + p[1], dz + t - p[2])
    else:
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
    add("bench", _box(min(xs) - 90, max(xs) + 90, -110.0, 190.0, -6.0, 0.0), RGB["bench"])
    for st in ("lever", "motor", "panel", "optical"):
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
        else:
            body, pins, tip = linke(x0, y0 + PROBE_DY)
            add("wch_linke__%s" % st, body, RGB["probe"])
            add("wch_linke_pins__%s" % st, pins, RGB["pin"])
        # the tails: pad -> probe pin, one lead each, a 2.54 female end on the pin
        wch = dict(WCH)
        for sig, tp in TAILS[st]:
            f = BOARDS.footprint(b, tp)
            if st == "lever":                # the pin's foot, in the jig's pocket
                jx, jy = LJ.pad_xy(tp)
                a = (x0 + jx, y0 + jy, -LJ.Z_BASE + LJ.Z_BOTTOM + LJ.LEAD_OD / 2)
                out_x = x0 - LJ.XE - 6.0     # out under the ear, where the screw nips it
                yc = y0 + LJ._pocket_y() + (TAILS[st].index((sig, tp)) - 1.5) * LJ.LEAD_OD
                b_ = tip[wch[sig]]
                path = [a, (a[0], yc, a[2]), (out_x, yc, a[2]), (out_x, yc, b_[2] + RISE),
                        (b_[0], b_[1], b_[2] + RISE), b_]
                wire = oct_cable(path, LEAD_OD)
            else:
                a = pt((f["x"], f["y"], t))
                b_ = tip[sig if st == "optical" else wch[sig]]
                wire = _lead(a, b_)
            name = "%s_tail_%s" % (st, sig.lower())
            add(name, wire, RGB[sig])
            add(name + "__socket", _socket(b_), RGB["socket"])
    # power: the brick's plug in the inlet, then each harness lead of the chain

    def way_out(st, ref, way):
        """(a way's contact, a point 8 mm out of its housing) on the bench."""
        _place, pt = _board_at(st)
        plug = BOARDS.plug(BOARD[st], ref)
        w, o = pt(plug["ways"][way]), plug["out"]
        if st == "lever":
            o = (-o[0], o[1], -o[2])
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
    # the jig itself, and what is bought for it
    x0, y0 = AT["lever"]
    dz = -LJ.Z_BASE
    add("lever_prog_jig", _mv(LJ.jig(), x0, y0, dz), RGB["jig"])
    add("lever_prog_jig_base", _mv(LJ.base(), x0, y0, dz), RGB["jig"])
    for n, w in LJ.hardware():
        add(n, _mv(w, x0, y0, dz), RGB["pin"])
    return out


def unit_of(name: str):
    """One tool drawn at several stations is one thing in the parts list."""
    return name.split("__")[0] if "__" in name else None


def conductors():
    """[(name, from, to)] in words: the list docs/bench-order.md is checked against."""
    rows = []
    wch = dict(WCH)
    for st in TAILS:
        for sig, tp in TAILS[st]:
            to = ("ST-LINK/V2 pin %d" % STLINK[sig] if st == "optical"
                  else "WCH-LinkE %s" % wch[sig].replace("_B", " (back row)"))
            rows.append(("%s_tail_%s" % (st, sig.lower()),
                         "%s %s%s" % (BOARD[st], tp, " (jig pin)" if st == "lever" else ""), to))
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
