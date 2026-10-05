"""Belt-tension clamp — TWO printed halves, one M3 socket-head screw, one insert. ×10.

Splices each cut GT2 belt into a loop and dials its tension. THE SCREW IS IN LINE WITH THE
BELT: it sits in the gap between the belt's two cut ends, on the belt's own centreline, so
the clamp's section is the belt's plus a wall each way and nothing stands out sideways.

Why in line (user, 2026-10-05; docs/belt-clamp-travel.md): the screw side of the old clamp
was the belt's TOOTH side, which is the inside of the loop, where the two runs close to
4.0 mm and the next string's belt passes through. No screw fits under the belt on either
side, and a screw beside it falls short of the travel on three strings. A stand-in of
this section cleared all ten.

  • HALF A — the HEAD half. The belt's end lies in a ribbed slot; the screw's head bears on
    the seat wall at the inner end; between the two is an open window the head turns in.
  • HALF B — the INSERT half. Same slot; the screw threads a brass insert that sits in a
    side-entry pocket BEHIND a shoulder, so belt tension presses the insert onto solid
    plastic. It is dropped in, not melted in: the pocket only has to stop it turning.
  • Each half carries a CHANNEL RAIL that slides over the other half's slot mouth as the
    two are brought together (user, 2026-10-05). It does three jobs: it closes the way the
    belt went in, so the belt cannot back out sideways; its two flanges hook the slot's
    lips, so belt tension on the ribs cannot creep the slot open and lose the teeth; and
    the pair stop the halves turning on the screw.

GRIP: each slot is the belt's own profile, open on one side face. The belt is pushed in
SIDEWAYS and its teeth sit between six ribs; tension pulls it along the slot, which the
ribs take. Nothing pinches. The two slots open on OPPOSITE faces (see PRINT).

WIDTH: A's rail runs INSIDE the section (B's mouth is set back for it). B's rail runs
OUTSIDE A, because A's head window needs both of its side rails to carry the tension
past the head. So the assembly is 0.95 wider on A's mouth side: 9.15 across.

THE KEY: the head faces the belt, so a straight key cannot reach it. A channel runs from
the socket out through the back of half A at KEY_DEG, for the BALL END of the instrument's
one 2.5 mm L-key (user: one stowed key works every fastener; the ball is its long arm).
The channel is on the belt's BACK, which is the outside of the loop.

Frame: X along the belt, origin at the splice (the middle of the gap); y across the belt's
width; z through it, belt centreline on z = 0, +z = the TOOTH side = INSIDE the loop.

PRINT: both halves at a 0.4 nozzle (the ribs), lying on their CLOSED side face so every
slot is a through-profile in the build direction and opens upward: A builds +y → −y, B
builds −y → +y. That is why the slots open on opposite faces: A's rail is on its bed face
and the lips it hooks on B are on B's top face, and in the assembly those are the same
side; likewise B's rail and A's lips.

⚠ NOT YET PROVEN, in the order a coupon should answer them: the side-entry grip under a
twisting belt; the dropped-in insert staying still while the screw is turned; the ball
end reaching the socket at KEY_DEG; the M3 insert's real size (INS_D / INS_L are a
typical short insert, no SKU picked).
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_x
from cadkit.fasteners import FastenerSpec, headed_screw, seated_insert

NOZZLE_D = 0.4                    # this part prints 0.4 (GT2 ribs)
B = NOZZLE_D

BW  = D.BELT_W            # 5.0  belt width (y)
BT  = D.BELT_T            # 1.4  belt through its teeth (z)
BTH = D.BELT_TOOTH_H      # 0.75 tooth height
BP  = D.BELT_PITCH        # 2.0  pitch

# ── the screw: M3 socket head cap (ISO 4762), the 2.5 mm key ─────────────────────────────
HEAD_D   = 5.5
HEAD_H   = 3.0
SCREW_L  = 12.0
INS_D    = 4.6            # ⚠ a typical short M3 insert; no SKU picked, MEASURE before printing
INS_L    = 4.0
M3 = FastenerSpec(
    name="M3", screw_d=3.0, pitch=0.5, selftap_d=3.2, shaft_clr_d=3.4,
    insert_pilot_d=INS_D, insert_depth=INS_L, insert_l=INS_L, insert_bore_d=3.4,
    boss_prot=5.0)
SCR_CLR  = M3.shaft_clr_d                    # 3.4

# ── the section ───────────────────────────────────────────────────────────────────────────
SLOT_CLR = 0.1                               # belt to slot, each face
SLOT_H   = BT + 2 * SLOT_CLR                 # 1.6
SKIN     = 6 * B                             # 2.4 over and under the belt
BODY_T   = SLOT_H + 2 * SKIN                 # 6.4 (z)
SIDE     = 4 * B                             # 1.6 closed side wall
BODY_W   = BW + 2 * SIDE                     # 8.2 (y); the belt sits centred, 1.6 in from the mouth
EDGE_CLR = 0.2                               # belt edge to the slot's closed end
HW, HT   = BODY_W / 2, BODY_T / 2

# ── along the belt ────────────────────────────────────────────────────────────────────────
N_TEETH  = 6                                 # ribs per grip (~the belt's full rating)
GRIP     = N_TEETH * BP + B                  # 12.4 slot length
END_WALL = 2 * B                             # 0.8 the wall the belt's cut end stops on
GAP      = 4.0                               # between the halves, fully loose = tension travel (2 teeth)
SEAT_T   = 6 * B                             # 2.4 the wall the head bears on
HEAD_CLR = 0.15                              # head to the window's side rails
HEAD_RAIL = HW - HEAD_D / 2 - HEAD_CLR       # 1.2 each side rail of the head window
KEY_DEG  = 25.0                              # ball-end key off the screw's axis
KEY_W    = 8 * B                             # 3.2 channel for the 2.5 key (2.9 over its corners)
SOCKET_IN = HEAD_H / 2                       # the ball's centre below the head's top
HEAD_ZONE = 16 * B                           # 6.4 window: the head, then room for the key to
                                             # rise clear of the belt's back before the grip
LEN_A    = SEAT_T + HEAD_ZONE + END_WALL + GRIP          # 22.0

SHOULDER = 4 * B                             # 1.6 the wall the insert is pulled against
INS_FIT  = 0.2                               # insert pocket over the insert, along the screw
RUNOUT   = SCREW_L - SEAT_T - SHOULDER - INS_L - INS_FIT # 3.8 screw tip past the insert, halves closed
INNER_B  = SHOULDER + INS_L + INS_FIT + RUNOUT + B       # 10.0 inner face to the belt's end wall
LEN_B    = INNER_B + END_WALL + GRIP                     # 23.2

RAIL_T   = 2 * B                             # 0.8 a channel rail's web
RAIL_CLR = 0.15                              # web to the mouth it covers
FLANGE   = 2 * B                             # 0.8 each flange's reach over a lip (y)
FLANGE_T = 0.75                              # flange through z; the lip is cut back for it
LIP_CLR  = 0.1                               # flange to lip: all the slot can open by
LIP_HT   = HT - FLANGE_T - LIP_CLR           # 2.35 half-thickness of a lip under a flange
RAIL_STEP = RAIL_T + RAIL_CLR                # 0.95 B's mouth set back / B's rail stood off A
RAIL_A_L = LEN_B                             # A's rail: flush with B's outer end, halves closed
RAIL_B_L = LEN_A                             # B's rail: likewise over A
BODY_Y   = BODY_W + RAIL_STEP                # 9.15 across the assembled clamp

assert RUNOUT >= 0, "the screw is too long for half B at the closed position"
# the key's channel must be clear of the belt's back where the grip begins
_KEY_RUN = SEAT_T + HEAD_ZONE + END_WALL - (SEAT_T + SOCKET_IN)
_KEY_Z   = (-_KEY_RUN * math.tan(math.radians(KEY_DEG))
            + (KEY_W / 2) / math.cos(math.radians(KEY_DEG)))
assert _KEY_Z <= -SLOT_H / 2 + 1e-6, (
    "the key channel reaches z %.2f at the grip, into the belt's slot (%.2f): lengthen "
    "HEAD_ZONE or steepen KEY_DEG" % (_KEY_Z, -SLOT_H / 2))


def _ribs(x0: float, y0: float, y1: float) -> cq.Workplane:
    """N_TEETH ribs hanging from the slot's +z face into the belt's valleys, the first
    centred BP/2 past x0. Trapezoid: BP/2 wide at the root, one bead at the tip, and
    SLOT_CLR short of the valley floor."""
    top, tip = SLOT_H / 2, SLOT_H / 2 - BTH + SLOT_CLR
    out = None
    for k in range(N_TEETH):
        xc = x0 + B / 2 + BP * (k + 0.5)
        pts = [(xc - BP / 4, top), (xc + BP / 4, top), (xc + B / 2, tip), (xc - B / 2, tip)]
        r = (cq.Workplane("XZ").polyline(pts).close().extrude(-(y1 - y0))
             .translate((0.0, y0, 0.0)))
        out = r if out is None else out.union(r)
    return out


def _belt_slot(x0: float, x1: float, open_y: int) -> tuple:
    """(cutter, ribs) for a belt slot over [x0, x1], open on the open_y (±1) side face and
    run past whichever X end is asked for by the caller's own overshoot."""
    yc = -open_y * (BW / 2 + EDGE_CLR)               # the closed end
    ya, yb = sorted((yc, open_y * (HW + 1.0)))
    cut = box_at(x1 - x0, yb - ya, SLOT_H, x=(x0 + x1) / 2, y=(ya + yb) / 2, z=0.0)
    return cut, (ya, yb)


def _rail(x0: float, x1: float, y_web: float, toward: int) -> cq.Workplane:
    """A channel rail over [x0, x1]: the web's outer face on y_web, its flanges reaching
    `toward` (±1, in y) over the lips of the half it covers."""
    L, xc = x1 - x0, (x0 + x1) / 2
    out = box_at(L, RAIL_T, BODY_T, x=xc, y=y_web + toward * RAIL_T / 2)
    for sz in (1, -1):
        out = out.union(box_at(L, FLANGE, FLANGE_T, x=xc,
                               y=y_web + toward * (RAIL_T + FLANGE / 2),
                               z=sz * (HT - FLANGE_T / 2)))
    return out


def _lips(x0: float, x1: float, y_from: float, toward: int) -> cq.Workplane:
    """Cutter that thins a half's two lips to LIP_HT from y_from outward (`toward` ±1),
    so a rail's flanges pass over them."""
    L, xc, d = x1 - x0, (x0 + x1) / 2, 3.0
    out = None
    for sz in (1, -1):
        c = box_at(L, d, HT, x=xc, y=y_from + toward * d / 2, z=sz * (LIP_HT + HT / 2))
        out = c if out is None else out.union(c)
    return out


def half_a() -> cq.Workplane:
    """The HEAD half, inner face on x = 0, body toward −x. Slot opens −y, where its lips
    are thinned for B's rail; its own rail is on +y and reaches over B."""
    body = box_at(LEN_A, BODY_W, BODY_T, x=-LEN_A / 2)
    gx0, gx1 = -LEN_A, -LEN_A + GRIP                              # grip: outer end .. end wall
    cut, (ya, yb) = _belt_slot(gx0 - 1.0, gx1, -1)
    body = body.cut(cut).union(_ribs(gx0, max(ya, -HW), min(yb, HW)))
    wx1 = -SEAT_T                                                  # head window
    body = body.cut(box_at(HEAD_ZONE, BODY_W - 2 * HEAD_RAIL, BODY_T + 2.0,
                           x=wx1 - HEAD_ZONE / 2))
    body = body.cut(cyl_x(SCR_CLR, SEAT_T + 0.2, -SEAT_T - 0.1))   # screw clearance
    # key channel: from the socket, down and outward through the back (−z)
    a = math.radians(KEY_DEG)
    px = -SEAT_T - SOCKET_IN
    ex, ez = px - 40.0 * math.cos(a), -40.0 * math.sin(a)
    nx, nz = -math.sin(a) * KEY_W / 2, math.cos(a) * KEY_W / 2
    pts = [(px + nx, nz), (ex + nx, ez + nz), (ex, -40.0), (px, -40.0)]
    key = (cq.Workplane("XZ").polyline(pts).close().extrude(KEY_W / 2, both=True))
    body = body.cut(key)
    body = body.cut(_lips(-LEN_A - 1.0, 1.0, -HW + FLANGE, -1))
    return body.union(_rail(0.0, RAIL_A_L, HW, -1))


def half_b() -> cq.Workplane:
    """The INSERT half, inner face on x = 0, body toward +x. Slot and insert pocket open
    +y, where the mouth is set back RAIL_STEP and its lips thinned for A's rail; its own
    rail is on −y, stood RAIL_STEP off the section so it passes OUTSIDE half A."""
    body = box_at(LEN_B, BODY_W, BODY_T, x=LEN_B / 2, y=-RAIL_STEP)
    body = body.cut(cyl_x(SCR_CLR, INNER_B - B + 0.1, -0.1))        # clearance + runout
    ix0, il = SHOULDER, INS_L + INS_FIT                            # insert pocket, side entry
    body = body.cut(cyl_x(INS_D, il, ix0))
    body = body.cut(box_at(il, HW + 1.0, INS_D, x=ix0 + il / 2, y=(HW + 1.0) / 2))
    gx0, gx1 = INNER_B + END_WALL, LEN_B
    cut, (ya, yb) = _belt_slot(gx0, gx1 + 1.0, +1)
    mouth = HW - RAIL_STEP
    body = body.cut(cut).union(_ribs(gx0, max(ya, -HW), mouth))
    body = body.cut(_lips(-1.0, LEN_B + 1.0, mouth - FLANGE, +1))
    return body.union(_rail(-RAIL_B_L, 0.0, -HW - RAIL_STEP, +1))


def screw_dummy() -> cq.Workplane:
    """M3 × SCREW_L socket head in half A's frame: bearing face on the seat wall, shank +x."""
    scr = headed_screw(M3, SCREW_L, head_d=HEAD_D, head_h=HEAD_H, socket_af=2.5)
    return scr.rotate((0, 0, 0), (0, 1, 0), -90).translate((-SEAT_T - HEAD_H, 0.0, 0.0))


# ── coupon: the two halves in their print poses ───────────────────────────────────────────
COUPON_UP = (0.0, 0.0, 1.0)     # the plate's direction; each half is turned onto its bed face


def tensioner_coupon() -> cq.Workplane:
    """Both halves lying on their closed side faces (A's +y, B's −y), slots opening up."""
    def _on_bed(w):
        return w.translate((0.0, 0.0, -w.val().BoundingBox().zmin))
    a = _on_bed(half_a().rotate((0, 0, 0), (1, 0, 0), -90))
    b = _on_bed(half_b().rotate((0, 0, 0), (1, 0, 0), 90)).translate((0.0, 12.0, 0.0))
    return a.union(b)


_HALF_A = half_a()               # built ONCE; every placement re-places these
_HALF_B = half_b()
_SCREW  = screw_dummy()


def clamp_components(gap: float = GAP):
    """The clamp as named (name, Workplane) parts in the BELT-LOCAL frame (splice at the
    origin, belt centreline on z = 0, +z inside the loop), at a given tension gap:
    gap = GAP is fully loose, gap = 0 has the halves closed."""
    def at(p, dx): return p.translate((dx, 0.0, 0.0))
    nut = seated_insert(M3, (gap / 2 + SHOULDER, 0.0, 0.0), (1.0, 0.0, 0.0))
    P = "belt_tensioner_"
    return [(P + "half_a", at(_HALF_A, -gap / 2)), (P + "half_b", at(_HALF_B, gap / 2)),
            (P + "screw", at(_SCREW, -gap / 2)), (P + "insert", nut)]
