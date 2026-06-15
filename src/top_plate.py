"""Removable top deck — PCTG. Swappable fret-marked BANDS + a pickup-cover piece.

Roles: (1) fret-position lines for the player; (2) dust cover over the motors +
electronics; (3) sound damping; (4) OLED + joystick mount; (5) hand rest; (6) the
pickup carrier.

Form: the deck is a STACK of panels that ride a GROOVE in both rail inner faces
(a tongue down each Y edge -> can't fall when the instrument is inverted) and
pull straight out -X for service (after the keyhead endplate + nut block come
off; the bridge endplate + a chassis stop ledge cap the +X end). The whole stack
is trapped between that +X ledge and the keyhead endplate, so no panel needs to
latch and none can slide out on its own.

The bridge end is divided into BAND_W-wide slots. A 3-slot PICKUP PIECE carries
the pickup: the pickup pokes up through an opening, depending side skirts form a
channel, and two clamp bolts in X-slots give +/-CLAMP mm of fine X-adjust. The
remaining slot(s) take plain fret-marked FILLER bands. Swapping which slots hold
the piece coarse-moves the pickup (tone: bridge<->neck); the clamp covers every
position in between -> continuous reach (50 mm spec min is comfortably inside).
Because the pickup region is always the same total width, the UI + keyhead
panels downstream never shift.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from . import electronics as EL
from . import pickup_mount as PM
from .helpers import box_at, cyl, heal

YL = CH.Y_LO + CH.T / 2                 # -Y rail inner face (-128.75)
YH = CH.Y_HI - CH.T / 2                 # +Y rail inner face (+54.75)
TZ = EL.DECK_TOP                        # deck surface (10 mm under strings = +6)
BZ = TZ - 6.0                           # 6 mm deck, recessed between the rails

# rail retention groove (cut into chassis by chassis.py; we ride it)
GZ0, GZ1 = CH.TP_GZ0, CH.TP_GZ1               # z 3.5..7
GROOVE_D = CH.TP_GROOVE_D                      # depth into the rail (Y)

PX0 = -17.5                             # +X deck end: panels butt the chassis stop
                                        # ledge just -X of the carriages (-13.6)
PX1 = -607.0                            # -X deck end (groove runs on to the rail end)

# ── band slots at the bridge end ─────────────────────────────────────────────
BAND_W   = 30.0                        # one slot
N_SLOTS  = 4                           # pickup-region slots (= 4*30 = 120 mm)
SLOT_X   = [PX0 - i * BAND_W for i in range(N_SLOTS + 1)]   # -17.5 .. -137.5
PIECE_SLOTS = 3                        # the pickup piece spans 3 slots (90 mm)
CLAMP    = 22.5                        # +/- fine X-adjust of the pickup in the piece

# shown installed state: piece in the 3 bridge-most slots, 1 filler behind it
PIECE_X0, PIECE_X1 = SLOT_X[0], SLOT_X[PIECE_SLOTS]        # -17.5, -107.5
FILL_X0,  FILL_X1  = SLOT_X[PIECE_SLOTS], SLOT_X[N_SLOTS]  # -107.5, -137.5
REGION_X1 = SLOT_X[-1]                                     # -137.5

# the two long panels behind the band region
MID_X0, MID_X1 = REGION_X1, -377.5     # carries the UI (string-10 deck band)
KEY_X0, KEY_X1 = MID_X1, PX1           # keyhead panel

# ── pickup-piece interior geometry ───────────────────────────────────────────
PIECE_CTR = (PIECE_X0 + PIECE_X1) / 2                      # -62.5
OPEN_X0   = PIECE_CTR + CLAMP + PM.PK_W / 2                # -23.5 (+X swept edge)
OPEN_X1   = PIECE_CTR - CLAMP - PM.PK_W / 2                # -101.5 (-X swept edge)
OPEN_HY   = PM.PK_L / 2 + 0.5                              # 50.0 (pickup half-len +clr)
SKIRT_T   = 3.0
SKIRT_BOT = PM.PK_BOT - 1.0                                # channel floor below pickup
SLOT_Z0, SLOT_Z1 = -6.5, -1.5                             # clamp-bolt X-slot Z band
SLOT_HX   = CLAMP + PM.CLAMP_BOLT_D / 2 + 0.3              # half-length of the X-slot

MARKER_FRETS = {3, 5, 7, 9, 12, 15, 17, 19, 21, 24}


def _fret_lines(plate, x0, x1):
    """Engrave EVERY 12-TET fret line across the panel (they compress toward the
    bridge: fret n at nut + scale*(1 - 2^(-n/12))), plus marker dots at the
    standard frets (double at 12 & 24). Stops where the spacing drops below
    1.5 mm (unmarkable, right at the bridge). Cosmetic recesses in the deck top."""
    nut = D.NUT_BLOCK_X
    scale = D.BRIDGE_X - nut                     # full speaking length (nut->bridge)
    n = 1
    while True:
        fx = nut + scale * (1 - 2 ** (-n / 12.0))
        nxt = nut + scale * (1 - 2 ** (-(n + 1) / 12.0))
        if fx >= D.BRIDGE_X or nxt - fx < 1.5:
            break
        if x1 + 0.8 < fx < x0 - 0.8:
            plate = plate.cut(box_at(0.7, YH - YL - 8, 0.9,
                                     x=fx, y=(YL + YH) / 2, z=TZ - 0.45))
            if n in MARKER_FRETS:
                for dy in ((-9.0, 9.0) if n in (12, 24) else (0.0,)):
                    plate = plate.cut(cyl(4.0, 1.3, z=TZ - 1.3)
                                      .translate((fx, dy, 0)))
        n += 1
    return plate


def _deck_body(xa, xb):
    """Bare deck panel, xa (+X) to xb (-X): body recessed between the rails with a
    retention tongue + web down each Y edge into the rail groove."""
    xm = (xa + xb) / 2
    BY0, BY1 = YL + 0.5, YH - 0.5        # body sits BETWEEN the rails (recessed)
    body = box_at(xa - xb, BY1 - BY0, TZ - BZ, x=xm, y=(BY0 + BY1) / 2,
                  z=(BZ + TZ) / 2)
    for inner, s in ((YL, -1), (YH, 1)):            # s = into-rail direction
        t0, t1 = inner + s * (GROOVE_D - 0.3), inner - s * 2.0      # tongue
        body = body.union(box_at(xa - xb, abs(t1 - t0), GZ1 - GZ0,
                                 x=xm, y=(t0 + t1) / 2, z=(GZ0 + GZ1) / 2))
        w0, w1 = inner - s * 0.5, inner - s * 3.0                   # web riser
        body = body.union(box_at(xa - xb, abs(w1 - w0), BZ - (GZ1 - 1.0),
                                 x=xm, y=(w0 + w1) / 2, z=((GZ1 - 1.0) + BZ) / 2))
    return body


def _band(xa, xb, *, ui=False):
    """A plain (filler / mid / keyhead) deck panel: body + fret lines + opt. UI."""
    body = _deck_body(xa, xb)
    if ui:
        # clearance windows for the OLED glass + joystick actuator
        body = body.cut(box_at(64.0, 35.0, TZ - BZ + 2, x=EL.UI_X, y=EL.OLED_Y,
                               z=(BZ + TZ) / 2))
        body = body.cut(cyl(9.0, TZ - BZ + 2, z=BZ - 1).translate(
            (EL.JOY_X, EL.JOY_Y, 0)))
        for dx in (-34, 34):                        # OLED mount bosses (M2 self-tap)
            for dy in (-15, 15):
                body = body.union(cyl(5.0, TZ - BZ, z=BZ).translate(
                    (EL.UI_X + dx, EL.OLED_Y + dy, 0)))
                body = body.cut(cyl(1.6, TZ - BZ + 1, z=BZ - 0.5).translate(
                    (EL.UI_X + dx, EL.OLED_Y + dy, 0)))
    return heal(_fret_lines(body, xa, xb))


def _pickup_piece():
    """3-slot deck panel that carries the pickup: opening to poke through, two
    depending side skirts forming the channel, and a clamp-bolt X-slot per skirt
    (the bolt threads the pickup side; loosen, slide +/-CLAMP, retighten)."""
    body = _deck_body(PIECE_X0, PIECE_X1)
    # opening through the deck for the pickup (spans its full clamp sweep in X)
    body = body.cut(box_at(OPEN_X0 - OPEN_X1, 2 * OPEN_HY, (TZ - BZ) + 2,
                           x=(OPEN_X0 + OPEN_X1) / 2, y=0, z=(BZ + TZ) / 2))
    for s in (1, -1):                               # +Y / -Y channel skirts
        y_in = s * OPEN_HY
        body = body.union(box_at(OPEN_X0 - OPEN_X1 + 4.0, SKIRT_T, BZ - SKIRT_BOT,
                                 x=(OPEN_X0 + OPEN_X1) / 2,
                                 y=y_in + s * SKIRT_T / 2,
                                 z=(BZ + SKIRT_BOT) / 2))
        # clamp-bolt X-slot through the skirt (bolt fixed to the pickup slides in it)
        body = body.cut(box_at(2 * SLOT_HX, SKIRT_T + 1.0, SLOT_Z1 - SLOT_Z0,
                               x=PIECE_CTR, y=y_in + s * SKIRT_T / 2,
                               z=(SLOT_Z0 + SLOT_Z1) / 2))
    return heal(body)


pickup_piece = _pickup_piece()
filler_band  = _band(FILL_X0, FILL_X1)
deck_mid     = _band(MID_X0, MID_X1, ui=True)
deck_keyhead = _band(KEY_X0, KEY_X1)

# build.py registers / places these as top_plate_0..3 (all PCTG deck panels)
segments = [pickup_piece, filler_band, deck_mid, deck_keyhead]
