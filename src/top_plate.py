"""Removable top deck plates (PCTG) — cover, hand rest, fret markers, UI mount.

Roles: (1) printed fret-position lines for the player; (2) dust cover over the
motors + electronics; (3) some sound damping of motor noise; (4) the mount for
the OLED + joystick; (5) a hand rest.

Form: split into 3 segments at the same X lines as the chassis (SPLIT_X), each
short enough to print, joined to its neighbour by a centred mortise/tenon.
Each segment rides a GROOVE cut into both rail inner faces (like the pickup
mount) on a tongue down each Y edge — so the plates can't fall off when the
instrument is inverted, yet pull straight out toward −X for motor service
(after the keyhead/nut block is removed; the bridge endplate caps the +X end).

Two regions stay OPEN: a long slot over the pickup's slide path (so the pickup
pokes through and still slides), and cut-outs for the OLED + joystick (mounted
to the mid segment, centred along X by string 10).
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from . import electronics as EL
from .helpers import box_at, cyl, heal

YL = CH.Y_LO + CH.T / 2                 # -Y rail inner face (-128.75)
YH = CH.Y_HI - CH.T / 2                 # +Y rail inner face (+54.75)
BZ, TZ = CH.Z_TOP, EL.DECK_TOP          # plate body z 10..14 (rests on the rails)

# rail retention groove (cut into chassis by chassis.py; we ride it)
GZ0, GZ1 = CH.TP_GZ0, CH.TP_GZ1               # z 3.5..7
GROOVE_D = CH.TP_GROOVE_D                      # depth into the rail (Y)
TONGUE_CLR = 0.3

PX0, PX1 = CH.TP_X0, CH.TP_X1           # plate span (matches the groove)
SEG_X = [PX0, -220.0, -440.0, PX1]      # 3 segments at the chassis splits
PICKUP_SLOT = (-168.0, PX0)            # open over the pickup slide path
PICKUP_SLOT_HY = 52.0                   # half-Y of the pickup opening
TENON_W = 30.0                          # inter-segment mortise/tenon width (Y)


def _fret_lines(plate, x0, x1):
    """Shallow engraved fret-position lines across the deck (cosmetic)."""
    nut = D.NUT_BLOCK_X                          # scale 0
    span = D.BRIDGE_AXLE_X - nut                 # speaking length
    for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24):
        fx = nut + span * (1 - 2 ** (-n / 12.0))
        if x1 + 3 < fx < x0 - 3:
            plate = plate.cut(box_at(1.2, YH - YL - 8, 0.8,
                                     x=fx, y=(YL + YH) / 2, z=TZ - 0.4))
    return plate


def _segment(xa, xb, *, pickup=False, ui=False):
    """One deck segment, xa (+X) to xb (-X). Body rests on the rail tops; each
    Y edge drops a tongue into the rail groove (retention) tied up by a web."""
    xm = (xa + xb) / 2
    BY0, BY1 = YL - 2.25, YH + 2.25      # body spans onto both rail tops
    body = box_at(xa - xb, BY1 - BY0, TZ - BZ, x=xm, y=(BY0 + BY1) / 2,
                  z=(BZ + TZ) / 2)
    for inner, s in ((YL, -1), (YH, 1)):            # s = into-rail direction
        # tongue: in the groove (s side) + inboard a couple mm to meet the web
        t0, t1 = inner + s * (GROOVE_D - 0.3), inner - s * 2.0
        body = body.union(box_at(xa - xb, abs(t1 - t0), GZ1 - GZ0,
                                 x=xm, y=(t0 + t1) / 2, z=(GZ0 + GZ1) / 2))
        # web: inboard riser tying the tongue up to the body (clears the lip)
        w0, w1 = inner - s * 0.5, inner - s * 3.0
        body = body.union(box_at(xa - xb, abs(w1 - w0), BZ - GZ1,
                                 x=xm, y=(w0 + w1) / 2, z=(GZ1 + BZ) / 2))
    # inter-segment tenon on the -X end (slots into the next segment's +X end)
    body = body.union(box_at(6.0, TENON_W, TZ - BZ,
                             x=xb - 3.0, y=(YL + YH) / 2, z=(BZ + TZ) / 2))
    body = body.cut(box_at(6.2, TENON_W + 0.4, TZ - BZ + 0.2,   # mortise on +X end
                           x=xa - 3.0, y=(YL + YH) / 2, z=(BZ + TZ) / 2))
    if pickup:
        body = body.cut(box_at(PICKUP_SLOT[1] - PICKUP_SLOT[0], 2 * PICKUP_SLOT_HY,
                               TZ - BZ + 2,
                               x=(PICKUP_SLOT[0] + PICKUP_SLOT[1]) / 2, y=0,
                               z=(BZ + TZ) / 2))
    if ui:
        # clearance windows for the OLED glass + joystick actuator
        body = body.cut(box_at(64.0, 35.0, TZ - BZ + 2, x=EL.UI_X, y=EL.OLED_Y,
                               z=(BZ + TZ) / 2))
        body = body.cut(cyl(9.0, TZ - BZ + 2, z=BZ - 1).translate(
            (EL.JOY_X, EL.JOY_Y, 0)))
        # 4 mount bosses around the OLED (M2 self-tap)
        for dx in (-34, 34):
            for dy in (-15, 15):
                body = body.union(cyl(5.0, TZ - BZ, z=BZ).translate(
                    (EL.UI_X + dx, EL.OLED_Y + dy, 0)))
                body = body.cut(cyl(1.6, TZ - BZ + 1, z=BZ - 0.5).translate(
                    (EL.UI_X + dx, EL.OLED_Y + dy, 0)))
    return _fret_lines(body, xa, xb)


def _build():
    segs = []
    for i in range(3):
        xa, xb = SEG_X[i], SEG_X[i + 1]
        segs.append(heal(_segment(xa, xb, pickup=(i == 0), ui=(i == 1))))
    return segs


segments = _build()
