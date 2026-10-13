# -*- coding: utf-8 -*-
"""A PRINTED POGO NEST for flashing the lever sensor boards.

SHOP TOOL, not a part of the instrument. The instrument has eleven lever/pedal sensor
boards (elec/lever_sensor.py) and SWD is their ONLY way in: no USB, no UART, BOOT0
grounded. Their four SWD pads are scattered -- TP1-TP3 on a 2.3 x 2.4 mm L and TP4
9.65 mm away -- because the board is full and a standard debug header does not fit
(docs/board-bringup-diagnostics.md 4.1). Hand-probing four scattered 1.0 mm pads eleven
times is eleven chances to slip, so the pads stay where they are and the TOOL carries
the pattern instead.

TWO PRINTED PARTS, ONE M4 SCREW, NO GLUE. The pins are CAPTURED, not stuck:
  * DOWN, every pin stands on the BASE plate's top face, so the base sets all four tips
    at one height with no gauge;
  * UP, each pin is held by its own lead: the lead is soldered to the pin's foot, runs
    flat along the pocket between nest and base, and is NIPPED where it leaves, under
    the ear the screw pulls down. A pin cannot rise without stretching its wire.
  * the bores are a loose slip fit (a printed O1 hole is not a fit anyone can hold).

HOW IT IS USED
  1. Solder a lead to the foot of each of four pogo pins (SWDIO / SWCLK / GND / NRST).
  2. Nest upside down: drop each pin head-first down its bore, lay the four leads side
     by side along the pocket and out over the ear.
  3. Put the base on and drive the one M4 button screw (the 2.5 mm key) into the ear's
     brass insert. The leads go to the WCH-LinkE: docs/bench-order.md, Tools.
  4. Drop a board in COMPONENT FACE DOWN, connector toward the open window, and plug the
     PH bench lead into J1 through that window -- the board has no +3V3 pad, so it is
     powered the way it is in the instrument, from +5 V on J1 (way 1 +5 V, way 2 GND).
  5. Hold the board down with a finger (its back is bare laminate, flush with the rim)
     and flash.

WHY FACE DOWN. The board is single-sided, so its back is flat and every part, pad and
the connector are on one face. Pins standing UP out of a one-piece nest need no lid, no
hinge and no second part; the finger is the clamp.

⚠ THE PAD POSITIONS ARE READ FROM THE ROUTED BOARD (elec/geom/lever_sensor.geom.json),
never typed here, so a re-route that moves a pad moves its pin. Rebuild the tool after
any lever_sensor re-route.

⚠ POGO_* ARE ADAFRUIT'S PUBLISHED FIGURES FOR ITS 2430 (P75-B1 class), read 2026-10-12:
"Diameter (body): 1mm", "Diameter (spring contact head): 0.7mm", "Uncompressed Length:
16mm", "Compressed Length: 13mm". No dimensioned drawing is published, and the design
needs none: it uses the overall length and the body diameter only. MEASURE ON ARRIVAL
before printing -- POGO_L sets the nest's height, and LEAD_OD (the jumper wire's
insulation, not published by its seller) sets the nip.
"""
from __future__ import annotations

import cadquery as cq

from cadkit.fasteners import (M4, M4_BUTTON_HEAD_D, M4_BUTTON_HEAD_H, cut_counterbore,
                              cut_insert_bore, m4_button_screw, seated_insert)

from . import board_geom as BG
from . import dimensions as D

BOARD = "lever_sensor"
PADS = ("TP1", "TP2", "TP3", "TP4")          # SWDIO, SWCLK, GND, NRST

_g = BG.load(BOARD)
BOARD_W, BOARD_L = _g["outline_mm"]          # 33.0 x 21.9
BOARD_T = _g["thickness_mm"]

# ── the pin (Adafruit 2430, P75-B1 class) -- measure on arrival ──────────────────────
POGO_D = 1.0                # body
POGO_HEAD_D = 0.7           # the needle the pad meets
POGO_L = 16.0               # foot to tip, uncompressed; base top to tip, so the nest's height
POGO_TRAVEL = 3.0           # 16 uncompressed less 13 compressed
POGO_PRELOAD = 1.5          # how far a seated board compresses each pin: half its travel
POGO_BORE_D = 1.4           # a LOOSE slip fit: the base and the lead hold the pin, not the bore
LEAD_OD = 1.3               # a 28 AWG jumper lead over its insulation (SparkFun PRT-12796 class)

# ── the nest ─────────────────────────────────────────────────────────────────────────
NEST_CLR = 0.2              # per side, board to rim
WALL = 3 * D.BEAD           # 2.4
LEDGE_REACH = 1.2           # how far the end ledge reaches in under the board
PART_ROOM = 8 * D.BEAD      # 6.4: J1 stands 5.5 off the board; everything else under 1.8
POST_D = 4 * D.BEAD         # 3.2
POST_DROP = 3 * D.BEAD      # 2.4: post tops this far below the board, under every part but J1
POCKET_H = 3 * D.BEAD       # 2.4: solder pocket over the pins' feet
POCKET_W = 7 * D.BEAD       # 5.6: four leads side by side (4 x 1.3) and room to lay them
NIP_H = D.BEAD              # 0.8: the pocket's height under the ear -- 0.5 less than a lead
EAR_L = 13 * D.BEAD         # 10.4: the ear the screw is in, past the nest's -X wall
BASE_T = 5 * D.BEAD         # 4.0: the button head sunk in it, and two beads left under the head
SCREW_L = 10.0              # the instrument's M4 x 10 button screw
PLUG_HALF_W = 12 * D.BEAD   # 9.6: the PH plug's window, each side of the board's centreline
NOTCH_HALF_W = 8 * D.BEAD   # 6.4: finger notches in the long rims, for lifting the board out

# Z = 0 is the board's component face, resting on the ledge. Tips stand POGO_PRELOAD
# above it until a board presses them down.
Z_TOP = BOARD_T                                           # rim flush with the board's back
Z_BOTTOM = POGO_PRELOAD - POGO_L                          # -14.5: the pins' feet, on the base
Z_BASE = Z_BOTTOM - BASE_T                                # -18.5: the bench
Z_FLOOR = -PART_ROOM
Z_POST = -POST_DROP

HX = BOARD_W / 2 + NEST_CLR                               # pocket half-size
HY = BOARD_L / 2 + NEST_CLR
OX, OY = HX + WALL, HY + WALL                             # outer half-size

XE = OX + EAR_L                                           # the ear's far end, at -XE
SCREW_XY = (-OX - EAR_L / 2, -OY / 2)                     # clear of the leads, which leave at +y

JIG_UP = (0.0, 0.0, 1.0)    # prints as drawn: flat on its base face, posts growing up
BASE_UP = (0.0, 0.0, -1.0)  # prints the other way up: the head's counterbore opens upward

assert LEAD_OD - NIP_H >= 0.3, "the nip does not pinch a %.1f lead" % LEAD_OD
assert 4 * LEAD_OD <= POCKET_W, "four leads do not lie side by side in the pocket"
assert 0 < POGO_PRELOAD < POGO_TRAVEL, "the preload is not inside the pin's travel"
assert BASE_T - M4_BUTTON_HEAD_H >= D.MIN_WALL_2P, "under two beads below the screw head"


def pad_xy(ref: str) -> tuple[float, float]:
    """A pad in the NEST's frame: the board is turned face down about its Y axis."""
    f = BG.footprint(BOARD, ref)
    return (-f["x"], f["y"])


def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def _pocket_y() -> float:
    ys = [pad_xy(r)[1] for r in PADS]
    assert max(ys) - min(ys) + POGO_D < POCKET_W - 2 * D.BEAD, (
        "the pads spread %.2f in y, wider than one %.1f pocket can serve"
        % (max(ys) - min(ys), POCKET_W))
    return (min(ys) + max(ys)) / 2


def jig() -> cq.Workplane:
    body = _box(-XE, OX, -OY, OY, Z_BOTTOM, Z_TOP)
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
    # the pocket over the pins' feet, where the leads are soldered on and lie; under the
    # ear it is only NIP_H high, and that is where the screw pinches them
    yc = _pocket_y()
    x_hi = max(x for x, _ in pts) + POCKET_W / 2
    body = body.cut(_box(-OX, x_hi, yc - POCKET_W / 2, yc + POCKET_W / 2,
                         Z_BOTTOM, Z_BOTTOM + POCKET_H))
    body = body.cut(_box(-XE, -OX, yc - POCKET_W / 2, yc + POCKET_W / 2,
                         Z_BOTTOM, Z_BOTTOM + NIP_H))
    # the bores, post top to base
    for x, y in pts:
        body = body.cut(cq.Workplane("XY").circle(POGO_BORE_D / 2)
                        .extrude(Z_POST - Z_BOTTOM).translate((x, y, Z_BOTTOM)))
    # the base's screw: a brass insert in the ear's underside
    return cut_insert_bore(M4, body, SCREW_XY + (Z_BOTTOM,), (0, 0, 1),
                           SCREW_L - (BASE_T - M4_BUTTON_HEAD_H) - M4.insert_l + D.BEAD,
                           reason="the screw clamps the base and the leads to the nest: it "
                                  "must run in metal, and a tool is opened more than once",
                           print_up=JIG_UP)


def base() -> cq.Workplane:
    """The plate the pins stand on. Flat on top, so all four feet are at one height; the
    screw's button head is sunk in its underside, so the jig sits flat on the bench."""
    plate = _box(-XE, OX, -OY, OY, Z_BASE, Z_BOTTOM)
    return cut_counterbore(plate, M4_BUTTON_HEAD_D + 2 * D.BEAD / 2, M4_BUTTON_HEAD_H,
                           M4.shaft_clr_d, BASE_T, SCREW_XY + (Z_BASE,), (0, 0, 1),
                           print_up=BASE_UP)


def hardware():
    """[(name, solid)] of what is bought: the four pins standing on the base as they do
    with no board on them, the insert and the screw."""
    from cadkit.web.finishes import made_of
    out = []
    for r in PADS:
        x, y = pad_xy(r)
        body_l = POGO_L - POGO_TRAVEL - 1.0          # how the length splits is not published
        pin = (cq.Workplane("XY").circle(POGO_D / 2).extrude(body_l)
               .union(cq.Workplane("XY").workplane(offset=body_l)
                      .circle(POGO_HEAD_D / 2).extrude(POGO_L - body_l)))
        out.append(("jig_pin_" + r.lower(), made_of(pin.translate((x, y, Z_BOTTOM)), "gold")))
    out.append(("jig_insert", seated_insert(M4, SCREW_XY + (Z_BOTTOM,), (0, 0, 1))))
    out.append(("jig_screw", m4_button_screw(SCREW_L).rotate((0, 0, 0), (1, 0, 0), 180)
                .translate(SCREW_XY + (Z_BASE,))))
    return out


def report() -> str:
    lines = ["lever programming jig: %.1f x %.1f x %.1f on a %.1f base, tips %.1f proud "
             "of the seat" % (OX + XE, 2 * OY, Z_TOP - Z_BOTTOM, BASE_T, POGO_PRELOAD)]
    for r in PADS:
        lines.append("  %s at nest (%.2f, %.2f)" % ((r,) + pad_xy(r)))
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
