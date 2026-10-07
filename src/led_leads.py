"""The two lighting leads: the Pi cap to the fret boards (J3) and to the foot strip (J6).

Each is a 4-way JST XH to XH lead, and it is drawn AS FOUR CONDUCTORS, each in its own
colour and each landing on its own contact at both ends (user, 2026-10-05: "we model them
as separate wires with accurate color and placement into the JST port so we can use it as
a reference"). The way order is harness.LED_DROP at every one of the four sockets, so the
lead is straight-through: way n to way n, and WHICH way each conductor is on is read
from there and written nowhere here. A conductor is known by what it carries:

    GND   black
    V24   red
    SCK   white
    SDT   blue

White and blue rather than the CAN pair's yellow and green, so a lighting lead cannot be
read as a bus lead in the model or on the bench.

WHERE A CONTACT IS comes off the routed board (elec/geom/<board>.geom.json): the
footprint's rotation gives the direction the ways count in and the side its mouth faces,
the pad centroid gives the middle of the row, and the fab outline gives the mouth's
plane. The two direction rules were checked against the routed boards' own pads for
every socket used here (front at -90; back at 0 and at 180) and _socket refuses any
other case rather than guess at it.

HOW FOUR WIRES TURN CORNERS WITHOUT PASSING THROUGH EACH OTHER. Every run is along one
axis. Where the four would otherwise share a line, each takes its own lane, WIRE_LANE
apart, and which wire gets which lane is SEARCHED: _solve tries the orders and keeps the
first in which no two conductors come closer than a wire's diameter anywhere.
"""
from __future__ import annotations

import itertools
import math
import os as _os
import sys as _sys

from . import dimensions as D
from .helpers import box_at, oct_cable

_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "elec"))
import harness as _H                                   # noqa: E402

WAYS = tuple(_H.LED_DROP)                              # the lead's own order
WIRE_OD = 1.4                    # 24 AWG over its insulation; XH crimps take 22-28 AWG
WIRE_LANE = 1.6                  # lane to lane where the four share a direction
XH_PITCH = 2.5
PLUG_L = 5.0                     # straight out of a mouth before any bend: the XHP-4
                                 # housing stands about 4.3 past it
COLORS = {"GND": (0.05, 0.05, 0.05), "V24": (0.85, 0.12, 0.10),
          "SCK": (0.92, 0.92, 0.88), "SDT": (0.15, 0.35, 0.85)}
_CHECKED = {("F", -90.0), ("F", 0.0), ("F", 180.0)}


def _socket(board, ref, place, axis_z):
    """([world point of way n at the mouth, n = 1..4], world unit vector OUT of the mouth).

    `place` puts a solid authored in the board frame where the board is; `axis_z` is the
    wire row's height in that frame."""
    from . import board_geom as BG
    f = BG.footprint(board, ref)
    assert "XH" in BG.fp_name(f["fpid"]) and "1x04" in BG.fp_name(f["fpid"]), f["fpid"]
    key = (f["side"], float(f["rot"]))
    assert key in _CHECKED, (
        "%s %s is on side %s at %s deg, a case whose pin direction has not been checked "
        "against a routed board" % (board, ref, f["side"], f["rot"]))
    th = math.radians(f["rot"])
    row = (math.cos(th), math.sin(th))                 # the way count's direction
    sgn = 1.0 if f["side"] == "F" else -1.0
    out = (sgn * math.sin(th), -sgn * math.cos(th))    # out of the mouth
    cx, cy = f["pads_xy"]
    x0, x1, y0, y1 = f["fab"]
    # the mouth's plane: the fab edge on the side `out` points to
    if abs(out[0]) > 0.5:
        mx, my = (x1 if out[0] > 0 else x0), None
    else:
        mx, my = None, (y1 if out[1] > 0 else y0)

    def world(px, py):
        bb = place(box_at(0.01, 0.01, 0.01, x=px, y=py, z=axis_z)).val().BoundingBox()
        return ((bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0,
                (bb.zmin + bb.zmax) / 2.0)

    pins = []
    for n in range(1, 5):
        k = (n - 2.5) * XH_PITCH
        px = (cx + k * row[0]) if mx is None else mx
        py = (cy + k * row[1]) if my is None else my
        pins.append(world(px, py))
    a = world(cx, cy)
    b = world(cx + out[0], cy + out[1])
    return pins, tuple(int(round(b[i] - a[i])) for i in range(3))


def _seg_gap(p0, p1, q0, q1):
    """Distance between two axis-aligned segments (as degenerate boxes)."""
    d2 = 0.0
    for i in range(3):
        lo1, hi1 = min(p0[i], p1[i]), max(p0[i], p1[i])
        lo2, hi2 = min(q0[i], q1[i]), max(q0[i], q1[i])
        g = max(lo1 - hi2, lo2 - hi1, 0.0)
        d2 += g * g
    return math.sqrt(d2)


def _clear(paths):
    """The closest any two of the conductors come to each other."""
    worst = 1e9
    for a, b in itertools.combinations(paths, 2):
        for p0, p1 in zip(a, a[1:]):
            for q0, q1 in zip(b, b[1:]):
                worst = min(worst, _seg_gap(p0, p1, q0, q1))
    return worst


def _solve(build):
    """build(r1, r2) -> the four polylines for one choice of lane orders; the first choice
    that keeps every pair a diameter apart."""
    for r1 in itertools.permutations(range(4)):
        for r2 in itertools.permutations(range(4)):
            paths = build(r1, r2)
            if _clear(paths) >= WIRE_OD + 0.05:
                return paths
    raise AssertionError("no lane order keeps the four conductors apart")


FOOT_DROP_CLR = 1.0              # the foot lead comes down this much further from the cap
                                 # than a plug length: at a plug length exactly, its
                                 # first lane clipped the motor board's 24 V socket
                                 # (2.8 mm3, y -57..-61 -- the gate found it)


def _foot_ends():
    from . import board_geom as BG
    from . import electronics as EL
    from . import foot_light as FOOT
    a = _socket("foot_led_a", "J1", lambda w: FOOT._placed("a", w),
                FOOT.BOARD_T + FOOT.XH_H / 2.0)
    hb = BG.HEIGHT[BG.fp_name(BG.footprint("pi_cap", "J6")["fpid"])]
    b = _socket("pi_cap", "J6", EL._cap_place, EL._CAP_T + hb / 2.0)
    return a, b


def foot_paths():
    """The foot strip's lead: board A's J1, up the endplate, over string 1's motor and its
    CAN tee, down between that motor and the Pi, into the cap's J6. foot_light holds the
    numbers and why each is what it is."""
    from . import foot_light as FOOT
    (pa, oa), (pb, ob) = _foot_ends()
    assert oa == (-1, 0, 0) and ob == (0, 1, 0), (oa, ob)
    fly = D.MOTOR_BELT_Z + D.MOTOR_SQ / 2.0 + FOOT.LEAD_FLY
    xs = pa[0][0] - FOOT.LEAD_STUB

    def build(r1, r2):
        out = []
        for i in range(4):
            a, b = pa[i], pb[i]
            cx = FOOT.LEAD_COL_X + r1[i] * WIRE_LANE
            dy = b[1] + PLUG_L + FOOT_DROP_CLR + r2[i] * WIRE_LANE
            out.append([a, (xs, a[1], a[2]), (xs, a[1], fly), (cx, a[1], fly),
                        (cx, dy, fly), (cx, dy, b[2]), (b[0], dy, b[2]), b])
        return out
    return _solve(build)


def _fret_ends():
    from . import board_geom as BG
    from . import electronics as EL
    from . import fret_light as FL
    t = BG.load("fret_led_key")["thickness_mm"]
    ha = BG.HEIGHT[BG.fp_name(BG.footprint("fret_led_key", "J1")["fpid"])]
    a = _socket("fret_led_key", "J1", lambda w: FL._placed("key", w), t + ha / 2.0)
    hb = BG.HEIGHT[BG.fp_name(BG.footprint("pi_cap", "J3")["fpid"])]
    b = _socket("pi_cap", "J3", EL._cap_place, EL._CAP_T + hb / 2.0)
    return a, b


FRET_COL_X = -583.5              # the first lane; the rest step -X from it


def fret_paths():
    (pa, oa), (pb, ob) = _fret_ends()
    assert oa == (-1, 0, 0) and ob == (0, -1, 0), (oa, ob)

    def build(r1, r2):
        out = []
        for i in range(4):
            a, b = pa[i], pb[i]
            cx = FRET_COL_X - r1[i] * WIRE_LANE
            dy = b[1] - PLUG_L - r2[i] * WIRE_LANE
            out.append([a, (cx, a[1], a[2]), (cx, dy, a[2]), (cx, dy, b[2]),
                        (b[0], dy, b[2]), b])
        return out
    return _solve(build)


def parts():
    """[(name, solid)] -- eight conductors."""
    out = []
    for lead, paths in (("foot", foot_paths()), ("fret", fret_paths())):
        for way, pts in zip(WAYS, paths):
            out.append(("wire_%s_led_%s" % (lead, way.lower()), oct_cable(pts, WIRE_OD)))
    return out
