# -*- coding: utf-8 -*-
"""A PRINTED POGO NEST for flashing the lever sensor boards.

SHOP TOOL, not a part of the instrument. The instrument has eleven lever/pedal sensor
boards (elec/lever_sensor.py) and SWD is their ONLY way in: no USB, no UART, BOOT0
grounded. Their four SWD pads are scattered -- TP1-TP3 on a 2.3 x 2.4 mm L and TP4
9.65 mm away -- because the board is full and a standard debug header does not fit
(docs/board-bringup-diagnostics.md 4.1). Hand-probing four scattered 1.0 mm pads eleven
times is eleven chances to slip, so the pads stay where they are and the TOOL carries
the pattern instead.

HOW IT IS USED
  1. Push four P75 pogo pins down their bores until each TAIL touches the bench the nest
     is standing on. The nest's height is the pin's barrel length, so that seats every
     pin at the same height with no gauge. Wick a drop of CA at the post top.
  2. Solder SWDIO / SWCLK / GND / NRST leads to the tails in the pocket underneath and
     lead them out of its open end to the WCH-LinkE.
  3. Drop a board in COMPONENT FACE DOWN, connector toward the open window, and plug the
     PH bench lead into J1 through that window -- the board has no +3V3 pad, so it is
     powered the way it is in the instrument, from +5 V on J1.
  4. Hold the board down with a finger (its back is bare laminate, flush with the rim)
     and flash.

WHY FACE DOWN. The board is single-sided, so its back is flat and every part, pad and
the connector are on one face. Pins standing UP out of a one-piece nest need no lid, no
hinge and no second part; the finger is the clamp.

⚠ THE PAD POSITIONS ARE READ FROM THE ROUTED BOARD (elec/geom/lever_sensor.geom.json),
never typed here, so a re-route that moves a pad moves its pin. Rebuild the tool after
any lever_sensor re-route.

⚠ POGO_* ARE FROM MEMORY OF THE P75-B1 DRAWING, NOT MEASURED. They set the nest height
and how far the tips stand proud. Put calipers on the pins that actually arrive before
printing; each is one constant.
"""
from __future__ import annotations

import cadquery as cq

from . import board_geom as BG
from . import dimensions as D

BOARD = "lever_sensor"
PADS = ("TP1", "TP2", "TP3", "TP4")          # SWDIO, SWCLK, GND, NRST

_g = BG.load(BOARD)
BOARD_W, BOARD_L = _g["outline_mm"]          # 31.0 x 21.9
BOARD_T = _g["thickness_mm"]

# ── the pin (P75-B1 class) ───────────────────────────────────────────────────────────
POGO_BARREL_D = 1.02
POGO_BARREL_L = 13.2        # the fixed tube; the nest is exactly this tall below the tips
POGO_PLUNGER_L = 3.3        # plunger standing out of the barrel, uncompressed
POGO_PRELOAD = 1.5          # how far a seated board compresses each pin (of ~2.65 travel)
POGO_BORE_D = 1.15          # printed bore: a slip fit on the barrel, held by CA

# ── the nest ─────────────────────────────────────────────────────────────────────────
NEST_CLR = 0.2              # per side, board to rim
WALL = 3 * D.BEAD           # 2.4
LEDGE_REACH = 1.2           # how far the end ledge reaches in under the board
PART_ROOM = 8 * D.BEAD      # 6.4: J1 stands 5.5 off the board; everything else under 1.8
POST_D = 4 * D.BEAD         # 3.2
POST_DROP = 3 * D.BEAD      # 2.4: post tops this far below the board, under every part but J1
POCKET_H = 3 * D.BEAD       # 2.4: solder pocket under the tails
POCKET_W = 7 * D.BEAD       # 5.6
PLUG_HALF_W = 12 * D.BEAD   # 9.6: the PH plug's window, each side of the board's centreline
NOTCH_HALF_W = 8 * D.BEAD   # 6.4: finger notches in the long rims, for lifting the board out

# Z = 0 is the board's component face, resting on the ledge. Tips stand POGO_PRELOAD
# above it until a board presses them down.
Z_TOP = BOARD_T                                           # rim flush with the board's back
Z_BARREL_TOP = POGO_PRELOAD - POGO_PLUNGER_L              # -1.8
Z_BOTTOM = Z_BARREL_TOP - POGO_BARREL_L                   # -15.0 -- the bench
Z_FLOOR = -PART_ROOM
Z_POST = -POST_DROP

HX = BOARD_W / 2 + NEST_CLR                               # pocket half-size
HY = BOARD_L / 2 + NEST_CLR
OX, OY = HX + WALL, HY + WALL                             # outer half-size

JIG_UP = (0.0, 0.0, 1.0)    # prints as drawn: flat on the bench face, posts growing up


def pad_xy(ref: str) -> tuple[float, float]:
    """A pad in the NEST's frame: the board is turned face down about its Y axis."""
    f = BG.footprint(BOARD, ref)
    return (-f["x"], f["y"])


def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def jig() -> cq.Workplane:
    body = _box(-OX, OX, -OY, OY, Z_BOTTOM, Z_TOP)
    # the board's own pocket, rim to rim
    body = body.cut(_box(-HX, HX, -HY, HY, 0.0, Z_TOP))
    # room for the parts: everything under the board except the END LEDGE at -X (the
    # board's +X end, where the cradle grooves keep 1.85 mm of laminate bare) and two
    # CORNER pads at +X, outside the PH plug's width
    cav = _box(-HX + LEDGE_REACH, HX, -HY, HY, Z_FLOOR, 0.0)
    for s in (1, -1):
        y0, y1 = sorted((s * (PLUG_HALF_W + 0.1), s * HY))
        cav = cav.cut(_box(HX - 2.4, HX, y0, y1, Z_FLOOR, 0.0))
    body = body.cut(cav)
    # the window J1's plug and lead come in through
    body = body.cut(_box(HX, OX, -PLUG_HALF_W, PLUG_HALF_W, Z_FLOOR, Z_TOP))
    # finger notches in both long rims
    for s in (1, -1):
        y0, y1 = sorted((s * HY, s * OY))
        body = body.cut(_box(-NOTCH_HALF_W, NOTCH_HALF_W, y0, y1, Z_POST, Z_TOP))
    # posts up to just under the board, one per pad (TP1-TP3 fuse into one)
    pts = [pad_xy(r) for r in PADS]
    for x, y in pts:
        body = body.union(cq.Workplane("XY").circle(POST_D / 2)
                          .extrude(Z_POST - Z_FLOOR).translate((x, y, Z_FLOOR)))
    # the solder pocket under the tails, open at the -X end for the leads
    ys = [y for _, y in pts]
    yc = (min(ys) + max(ys)) / 2
    assert max(ys) - min(ys) + POGO_BARREL_D < POCKET_W - 2 * D.BEAD, (
        "the pads spread %.2f in y, wider than one %.1f pocket can serve"
        % (max(ys) - min(ys), POCKET_W))
    x_hi = max(x for x, _ in pts) + POCKET_W / 2
    body = body.cut(_box(-OX, x_hi, yc - POCKET_W / 2, yc + POCKET_W / 2,
                         Z_BOTTOM, Z_BOTTOM + POCKET_H))
    # the bores, post top to bench
    for x, y in pts:
        body = body.cut(cq.Workplane("XY").circle(POGO_BORE_D / 2)
                        .extrude(Z_POST - Z_BOTTOM).translate((x, y, Z_BOTTOM)))
    return body


def report() -> str:
    lines = ["lever programming jig: %.1f x %.1f x %.1f, tips %.1f proud of the seat"
             % (2 * OX, 2 * OY, Z_TOP - Z_BOTTOM, POGO_PRELOAD)]
    for r in PADS:
        lines.append("  %s at nest (%.2f, %.2f)" % ((r,) + pad_xy(r)))
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
