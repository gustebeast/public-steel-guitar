"""The magnetic pickup's screw terminal on the output board (J8), drawn as the part.

MAX / MaiXu MX128-5.0-02P-GN01-Cu-Y-A (LCSC C5188463), the slotted R2 part (R2-3). The board's own solid draws every
other part as its F.Fab box extruded to a height; this one is drawn here instead
(`BG.solid(..., skip=("J8",))`) because it is the one field connection a player works
on -- strip, insert, tighten -- so its wire holes and screw wells are what the space
round it has to leave room for, the way src/servo42d.py draws the motor's terminals.

FROM THE MAKER'S DRAWING (MX128-5.0-XXP, Cixi Maixu, 22.09.14):
  * pitch 5.00; holes O1.40; 10.20 deep; 14.00 tall off the board; 3.10 past the end pin on
    one side, 2.50 on the other: which side the drawing does not settle, so the land and
    this solid take 3.10 on both, the envelope. Verify on the part
  * the pin row is 5.50 from one long face and 4.70 from the other. The sheet could not be
    read for which is the wire entry; entry = 5.50, as MX126's entry is its deeper side
  * screw M2.5, 0.4 N m; wire 24-12 AWG
  * the ordering code's screw letter: Y slotted (no second tool: the user, R2-3)
ESTIMATED, as for the MX126 this replaced:
  * the wire hole: round, O4.0, its centre 4.5 above the seat
  * the screw well: square 3.8, 3.0 deep, over the pin; the screw head O3.6 x 1.2 in its bottom
  * the back's top edge chamfered 2.0

THE WIRE-ENTRY FACE IS THE BOARD'S +Y -- unturned. output_panel R2 turns J8 180 degrees (its
+Y entry sat in string 10's clamp sweep on the dropped board), so there it faces -Y: the part
is drawn unturned and turned about its pad row (_turn), and way_points turn with it. The routed board's fab box runs 4.70 below the pads
and 5.50 above (the land's -5.5 / +4.7 with its Y flipped), so the 5.5 side -- the entry --
is +Y: the side src/wiring.py has always landed the pickup lead on.
"""
from __future__ import annotations

import math

import cadquery as cq

from . import board_geom as BG

PITCH = 5.00
END = 3.10                  # body past the end pins, both sides (docstring)
DEPTH = 10.20
H = 14.00
PIN_TO_ENTRY, PIN_TO_BACK = 5.50, 4.70
PIN_W, PIN_T, PIN_BELOW = 1.00, 0.60, 4.00
HOLE_D, HOLE_Z, HOLE_DEPTH = 4.0, 4.5, 4.5          # estimated (see the docstring)
WELL, WELL_DEPTH = 3.8, 3.0                         # estimated
HEAD_D, HEAD_H, RECESS_W, RECESS_L, RECESS_D = 3.6, 1.2, 0.6, 3.6, 0.6   # M2.5 slotted head
BACK_CHAMFER = 2.0
SCREW = "M2.5 slotted (ordering code Y), 0.4 N m"
STRIP_MM = (6.0, 7.0)


def _box(w, l, h, x, y, z):
    return cq.Workplane("XY").box(w, l, h).translate((x, y, z))


def _turned(board, ref):
    """(turned, pad-row centre x, pad y): TURNED is the footprint at 180 degrees, its entry
    facing -Y (output_panel R2's J8). Only 0 and 180 are drawn."""
    f = BG.footprint(board, ref)
    rot = float(f.get("rot") or 0.0) % 360.0
    assert min(abs(rot), abs(rot - 180.0), abs(rot - 360.0)) < 1e-6, (
        "%s %s is turned %s: only 0 and 180 were checked against its pads" % (board, ref, rot))
    xs = [p[0] for p in f["pads"].values()]
    return abs(rot - 180.0) < 1e-6, (min(xs) + max(xs)) / 2.0, next(iter(f["pads"].values()))[1]


def _frame(board, ref):
    """(pin x list, pin y, seat z, way count) of a terminal on `board`, in the board's frame
    AS IF UNTURNED: a turned part is drawn so and then turned about its pad row (_turn)."""
    f = BG.footprint(board, ref)
    turned, cx, _py = _turned(board, ref)
    pads = sorted(f["pads"].items(), key=lambda kv: int(kv[0]))
    xs = [(2.0 * cx - p[1][0]) if turned else p[1][0] for p in pads]
    y = pads[0][1][1]
    assert all(abs(p[1][1] - y) < 1e-6 for p in pads), "%s %s: pads not in one row" % (board, ref)
    assert all(abs(b - a - PITCH) < 0.01 for a, b in zip(xs, xs[1:])), (
        "%s %s: pads are not on the %.2f pitch" % (board, ref, PITCH))
    # the routed fab box agrees with the drawing to its line width, or this is not the part
    x0, x1, y0, y1 = f["fab"]
    if turned:
        y0, y1 = 2.0 * y - y1, 2.0 * y - y0
    assert abs((x1 - x0) - (PITCH * (len(xs) - 1) + 2.0 * END)) < 0.2 and abs((y1 - y0) - DEPTH) < 0.2, (
        "%s %s: fab box %.2f x %.2f is not an MX128-5.0 of %d ways"
        % (board, ref, x1 - x0, y1 - y0, len(xs)))
    assert (y1 - y) > (y - y0), "%s %s: the entry (4.0) side is not +Y unturned" % (board, ref)
    return xs, y, BG.load(board)["thickness_mm"], len(xs)


def _turn(board, ref, wp):
    """A Workplane drawn unturned, turned with the footprint about its pad row."""
    turned, cx, py = _turned(board, ref)
    return wp.rotate((cx, py, 0.0), (cx, py, 1.0), 180.0) if turned else wp


def parts(board="output_panel", ref="J8") -> dict:
    """{"housing": green PA66 with its wire holes and screw wells, "metal": the screws in
    their wells and the pins below the board}, in the board's own frame."""
    xs, py, t, n = _frame(board, ref)
    x0, x1 = xs[0] - END, xs[-1] + END
    y0, y1 = py - PIN_TO_BACK, py + PIN_TO_ENTRY
    body = _box(x1 - x0, DEPTH, H, (x0 + x1) / 2.0, (y0 + y1) / 2.0, t + H / 2.0)
    body = body.edges("|X").edges(">Z").edges("<Y").chamfer(BACK_CHAMFER)
    metal = None
    for x in xs:
        hole = (cq.Workplane("XZ").circle(HOLE_D / 2.0).extrude(HOLE_DEPTH)
                .translate((x, y1 + 0.01, t + HOLE_Z)))   # XZ extrudes toward -Y: into the body
        body = body.cut(hole)
        body = body.cut(_box(WELL, WELL, WELL_DEPTH + 0.01, x, py, t + H - WELL_DEPTH / 2.0 + 0.005))
        z_head = t + H - WELL_DEPTH            # the head sits in the bottom of its well
        head = (cq.Workplane("XY").circle(HEAD_D / 2.0).extrude(HEAD_H).translate((x, py, z_head)))
        head = head.cut(_box(RECESS_W, RECESS_L, RECESS_D + 0.01, x, py,
                             z_head + HEAD_H - RECESS_D / 2.0 + 0.005))
        pin = _box(PIN_W, PIN_T, PIN_BELOW - t, x, py, -(PIN_BELOW - t) / 2.0)   # below the board only
        for s in (head, pin):
            metal = s if metal is None else metal.union(s)
    return {"housing": _turn(board, ref, body), "metal": _turn(board, ref, metal)}


def way_points(board="output_panel", ref="J8"):
    """[(point, exit direction)] per way, board frame: where a conductor ends in its wire
    hole (3 mm in from the face) and the direction out of the hole (+Y)."""
    xs, py, t, _n = _frame(board, ref)
    face = py + PIN_TO_ENTRY
    turned, cx, _ = _turned(board, ref)
    if turned:                       # way n where pin n is: the point and its exit turned
        return [((2.0 * cx - x, 2.0 * py - (face - 3.0), t + HOLE_Z), (0.0, -1.0, 0.0))
                for x in xs]
    return [((x, face - 3.0, t + HOLE_Z), (0.0, 1.0, 0.0)) for x in xs]


def summary() -> str:
    xs, py, t, n = _frame("output_panel", "J8")
    if _turned("output_panel", "J8")[0]:
        py = py - 2.0 * PIN_TO_ENTRY             # so `py + PIN_TO_ENTRY` reads the turned face
    return ("J8 MX128-5.0-%02dP: %.1f wide, %.1f deep, %.1f tall; wire holes O%.1f at %.1f "
            "off the board, face at y %.2f; %s; strip %.0f-%.0f mm"
            % (n, PITCH * (n - 1) + 2.0 * END, DEPTH, H, HOLE_D, HOLE_Z, py + PIN_TO_ENTRY, SCREW, *STRIP_MM))
