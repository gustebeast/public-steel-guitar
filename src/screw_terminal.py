"""The magnetic pickup's screw terminal on the output board (J8), drawn as the part.

MAX / MaiXu MX126-5.0-02P-GN01-Cu-S-A (LCSC C5188434). The board's own solid draws every
other part as its F.Fab box extruded to a height; this one is drawn here instead
(`BG.solid(..., skip=("J8",))`) because it is the one field connection a player works
on -- strip, insert, tighten -- so its wire holes and screw wells are what the space
round it has to leave room for, the way src/servo42d.py draws the motor's terminals.

FROM THE MAKER'S DRAWING (MX126-5.0-XXP, Cixi Maixu, 22.09.14; the 3-way sheet the KiCad
footprint cites, read 2026-10-20):
  * pitch 5.00; body 5.00 x P wide plus a 0.50 interlock lip on pin 1's side; 7.80 deep;
    10.30 tall off the board
  * the pin row is 4.00 from the WIRE-ENTRY face and 3.80 from the back; pins 1.00 x 0.60,
    4.00 below the body's seat
  * screw M2.5, 0.4 N m; wire 26-14 AWG (0.5-2.5 mm2); strip 6-7 mm
  * the ordering code's screw letter: Y slotted, S cross, PS flat cross. Ours is S.
ESTIMATED (not dimensioned on the sheet; from the listing's photos, scaled off the body):
  * the wire hole: round, O3.2, its centre 4.0 above the seat (the side view's 4.00 +-0.30)
  * the screw well: square 3.4, 3.0 deep, over the pin; the screw head O3.2 x 1.2 in its bottom,
    so the head is 1.8 below the top
  * the back's top edge chamfered 2.0

THE WIRE-ENTRY FACE IS THE BOARD'S +Y. The routed board's fab box runs 3.85 below the pads
and 4.05 above (KiCad's -4.0 / +3.8 with its Y flipped), so the 4.0 side -- the entry --
is +Y: the side src/wiring.py has always landed the pickup lead on.
"""
from __future__ import annotations

import math

import cadquery as cq

from . import board_geom as BG

PITCH = 5.00
LIP = 0.50                  # the interlock lip, pin 1's side
DEPTH = 7.80
H = 10.30
PIN_TO_ENTRY, PIN_TO_BACK = 4.00, 3.80
PIN_W, PIN_T, PIN_BELOW = 1.00, 0.60, 4.00
HOLE_D, HOLE_Z, HOLE_DEPTH = 3.2, 4.0, 4.5          # estimated (see the docstring)
WELL, WELL_DEPTH = 3.4, 3.0                         # estimated
HEAD_D, HEAD_H, RECESS_W, RECESS_L, RECESS_D = 3.2, 1.2, 0.6, 2.4, 0.6   # M2.5 cross head
BACK_CHAMFER = 2.0
SCREW = "M2.5 cross head (ordering code S), 0.4 N m"
STRIP_MM = (6.0, 7.0)


def _box(w, l, h, x, y, z):
    return cq.Workplane("XY").box(w, l, h).translate((x, y, z))


def _frame(board, ref):
    """(pin x list, pin y, seat z, way count) of a terminal on `board`, in the board's frame."""
    f = BG.footprint(board, ref)
    assert abs(float(f.get("rot") or 0.0)) < 1e-6, (
        "%s %s is turned %s: only the unturned case was checked against its pads"
        % (board, ref, f.get("rot")))
    pads = sorted(f["pads"].items(), key=lambda kv: int(kv[0]))
    xs = [p[1][0] for p in pads]
    y = pads[0][1][1]
    assert all(abs(p[1][1] - y) < 1e-6 for p in pads), "%s %s: pads not in one row" % (board, ref)
    assert all(abs(b - a - PITCH) < 0.01 for a, b in zip(xs, xs[1:])), (
        "%s %s: pads are not on the %.2f pitch" % (board, ref, PITCH))
    # the routed fab box agrees with the drawing to its line width, or this is not the part
    x0, x1, y0, y1 = f["fab"]
    assert abs((x1 - x0) - (PITCH * len(xs) + LIP)) < 0.2 and abs((y1 - y0) - DEPTH) < 0.2, (
        "%s %s: fab box %.2f x %.2f is not an MX126-5.0 of %d ways"
        % (board, ref, x1 - x0, y1 - y0, len(xs)))
    assert (y1 - y) > (y - y0), "%s %s: the entry (4.0) side is not +Y" % (board, ref)
    return xs, y, BG.load(board)["thickness_mm"], len(xs)


def parts(board="output_panel", ref="J8") -> dict:
    """{"housing": green PA66 with its wire holes and screw wells, "metal": the screws in
    their wells and the pins below the board}, in the board's own frame."""
    xs, py, t, n = _frame(board, ref)
    x0 = xs[0] - PITCH / 2.0 - LIP
    x1 = xs[-1] + PITCH / 2.0
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
        for w, l in ((RECESS_W, RECESS_L), (RECESS_L, RECESS_W)):
            head = head.cut(_box(w, l, RECESS_D + 0.01, x, py, z_head + HEAD_H - RECESS_D / 2.0 + 0.005))
        pin = _box(PIN_W, PIN_T, PIN_BELOW - t, x, py, -(PIN_BELOW - t) / 2.0)   # below the board only
        for s in (head, pin):
            metal = s if metal is None else metal.union(s)
    return {"housing": body, "metal": metal}


def way_points(board="output_panel", ref="J8"):
    """[(point, exit direction)] per way, board frame: where a conductor ends in its wire
    hole (3 mm in from the face) and the direction out of the hole (+Y)."""
    xs, py, t, _n = _frame(board, ref)
    face = py + PIN_TO_ENTRY
    return [((x, face - 3.0, t + HOLE_Z), (0.0, 1.0, 0.0)) for x in xs]


def summary() -> str:
    xs, py, t, n = _frame("output_panel", "J8")
    return ("J8 MX126-5.0-%02dP: %.1f wide, %.1f deep, %.1f tall; wire holes O%.1f at %.1f "
            "off the board, face at y %.2f; %s; strip %.0f-%.0f mm"
            % (n, PITCH * n + LIP, DEPTH, H, HOLE_D, HOLE_Z, py + PIN_TO_ENTRY, SCREW, *STRIP_MM))
