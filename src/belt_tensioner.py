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
    the seat wall at the inner end; between the two is a window the head turns in, open
    through A's bed face and top, with a two-bead wall either side of the head in z (WIN_HZ).
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

WIDTH, AND WHICH SIDE IS WHICH. Two neighbouring clamps can meet (tools/clamp_range.py):
an even string's clamp on its lower run and the next odd string's on its upper run pass
8.8 apart near the screws, each presenting its +y side to the other. So +y is kept as
thin as it can be: A's rail there IS the slot's side wall, 3.5 from the belt's centre, with
its two outer edges chamfered. Everything that needs room is on −y, which faces away:
B's rail runs OUTSIDE A on that side, and the screw sits 0.3 toward −y (it centred the
head window's old y rails; the window's walls are in z now). 8.55 across in all.

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

PROVEN ON THE BENCH (user, 2026-10-22, r6 on string 10's belt, cut to 195 teeth: "works
perfect, we can lock in this design"): the side-entry grip under tension, the dropped-in
insert holding still while the screw turns, the ball end reaching the socket at KEY_DEG,
and the dovetail rails keeping the halves together under load. LOCKED: change it only for
a reason found on the instrument. Still the drawing's: INS_D / INS_L (McMaster 94459A130).
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_x
from cadkit.fasteners import FastenerSpec, headed_screw, seated_insert
from cadkit.supports import printable_bore

NOZZLE_D = 0.4                    # this part prints 0.4 (GT2 ribs)
B = NOZZLE_D

BW  = D.BELT_W            # 5.0  belt width (y)
BT  = D.BELT_T            # 1.4  belt through its teeth (z)
BTH = D.BELT_TOOTH_H      # 0.75 tooth height
BP  = D.BELT_PITCH        # 2.0  pitch

# each half prints lying on a closed side face (see PRINT), so every bore along x is SIDEWAYS
UP_A = (0.0, -1.0, 0.0)           # A on its +y face, building -y
UP_B = (0.0, 1.0, 0.0)            # B on its -y face, building +y
TIP = 2 * B                       # a teardrop's tip dulled to a two-bead flat: the widest
                                  # flat ceiling allowed, and it keeps B's skin (asserted)

# ── the screw: M3 socket head cap (ISO 4762), the 2.5 mm key ─────────────────────────────
HEAD_D   = 5.5
HEAD_H   = 3.0
SCREW_L  = 12.0
INS_D    = 4.7            # McMaster 94459A130, brass heat-set M3: OD over the knurl 4.7,
INS_L    = 4.3            # installed length 4.3 (pilot end 3.9). OFF THE DRAWING -- MEASURE
                          # one before printing. It is not heat-set here: it drops into a
                          # side pocket and the screw pulls it against a shoulder.
INS_SLIP = 0.1            # the pocket over the insert's OD, so a printed slot takes a
                          # knurled part by hand. It is all the section has to give: the
                          # skin over and under the pocket is then one bead (asserted).
M3 = FastenerSpec(
    name="M3", screw_d=3.0, pitch=0.5, selftap_d=3.2, shaft_clr_d=D.M3_CLR_D,
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
END_WALL_A = 7 * B                           # 2.8 half A's: the key bore runs down through it
                                             # and stands two beads off the grip (asserted)
GAP      = 2 * BP                            # 4.0 between the halves, fully loose = tension travel (2 teeth)
SEAT_T   = 6 * B                             # 2.4 the wall the head bears on
HEAD_CLR = 0.15                              # head to the window's side walls
# THE HEAD WINDOW is a hole straight through A in y, its BED face to its top (user,
# 2026-10-22): the two pieces that carry the belt's tension past the head are WALLS either side
# of it in z, each two beads. They were rails across y -- a floor and a 6.4 bridge in A's print.
# The head needs 2 * WIN_HZ of the body's BODY_T, so along the window A stands HZ each side.
WIN_HZ   = HEAD_D / 2 + HEAD_CLR             # 2.9 the window's half-width in z
# NO KEEPER over the head (user, 2026-10-22, after the r5 print): B's rail covers the seat slot
# once the halves are slid together, and that is what keeps the screw in. The 45 deg lip that
# was here did the same job twice.
HZ       = WIN_HZ + 2 * B                    # 3.7 A's half-thickness, seat wall to end wall (0.5 proud)
IN_HW    = BW / 2 + EDGE_CLR + 2 * B         # 3.5 belt centre to the +y face, the side that
                                             # meets the neighbouring clamp: A's rail web alone
SCREW_Y  = (IN_HW - HW) / 2                  # -0.3 the screw, midway across half A
EDGE_CH  = B                                 # 0.4 chamfer on A's two +y edges
KEY_DEG  = 25.0                              # ball-end key off the screw's axis
KEY_FLANK = 48.0                             # the key bore's teardrop flanks off flat: the rim
                                             # a face at KEY_DEG leaves is then inside 45 deg
KEY_W    = 8 * B                             # 3.2 channel for the 2.5 key (2.9 over its corners)
SOCKET_IN = HEAD_H / 2                       # the ball's centre below the head's top
HEAD_ZONE = 16 * B                           # 6.4 window: the head, then room for the key to
                                             # rise clear of the belt's back before the grip
LEN_A    = SEAT_T + HEAD_ZONE + END_WALL_A + GRIP        # 24.0

SHOULDER = 4 * B                             # 1.6 the wall the insert is pulled against
INS_FIT  = 0.2                               # insert pocket over the insert, along the screw
RUNOUT   = SCREW_L - SEAT_T - SHOULDER - INS_L - INS_FIT # 3.5 screw tip past the insert, halves closed
INNER_B  = SHOULDER + INS_L + INS_FIT + RUNOUT + B       # 10.0 inner face to the belt's end wall
LEN_B    = INNER_B + END_WALL + GRIP                     # 23.2

RAIL_T   = 2 * B                             # 0.8 a channel rail's web
RAIL_CLR = 0.15                              # web to the mouth it covers
FLANGE   = 2 * B                             # 0.8 each flange's reach over a lip (y)
FLANGE_T = 0.75                              # flange through z; the lip is cut back for it
LIP_CLR  = 0.1                               # flange to lip: all the slot can open by
LIP_HT   = HT - FLANGE_T - LIP_CLR           # 2.35 half-thickness of a lip under a flange
# THE RAILS ARE DOVETAILS (user, 2026-10-22, r5 print: "the joinery doesn't prevent them from
# lifting off, and they do under load"). r5's flanges met the lips on flat z faces, which hold
# the slot shut but let the halves part SIDEWAYS (y) -- nothing hooked in y. Each flange now
# thickens toward its tip by DOVE, its inner face sloped, and the lip under it necks to match:
# the halves come apart only by sliding back out along x. DOVE is as deep as the lip can take
# with two beads left over the belt's slot, and the slope it makes is printable both ways
# (the flange's face and the lip's are each an overhang of DOVE_DEG in their own half's print).
DOVE     = LIP_HT - SLOT_H / 2 - 2 * B       # 0.75 the flange's tip over its root, in z
DOVE_DEG = math.degrees(math.atan2(DOVE, FLANGE))   # 43.2 off the build direction
RAIL_STEP = RAIL_T + RAIL_CLR                # 0.95 B's rail stood off A's −y face
MOUTH_B  = IN_HW - RAIL_STEP                 # 2.55 B's slot mouth, under A's rail
RAIL_A_L = LEN_B                             # A's rail: flush with B's outer end, halves closed
RAIL_B_L = LEN_A                             # B's rail: likewise over A

assert RUNOUT >= 0, "the screw is too long for half B at the closed position"
assert DOVE > 0 and DOVE_DEG <= 45.0, "the rails' dovetail is %.2f deep at %.1f deg" % (DOVE, DOVE_DEG)
_TEAR = max(SCR_CLR / 2 * math.sqrt(2.0) - TIP / 2, SCR_CLR / 2)   # bore axis -> teardrop flat
assert MOUTH_B - (SCREW_Y + _TEAR) >= 2 * B - 1e-9, (
    "B's screw-bore teardrop leaves %.2f under its +y face, under two beads"
    % (MOUTH_B - (SCREW_Y + _TEAR)))
# B's rail chamfer against the web's joint to its +z flange, measured square to the chamfer
# from the joint's inside corner (y = web + RAIL_T, z = the flange's underside)
_RAIL_JOINT = ((HT - (HT - FLANGE_T)) + RAIL_T - EDGE_CH) / math.sqrt(2.0)
assert _RAIL_JOINT >= 2 * B - 1e-6, (
    "B's rail chamfer leaves %.2f where the web meets its flange, under two beads" % _RAIL_JOINT)
_KEY_RIM = math.degrees(math.atan(math.cos(math.radians(KEY_DEG))
                                  * math.tan(math.radians(KEY_FLANK))))
assert _KEY_RIM >= 45.0, "the key bore's rim is %.1f deg off flat, past 45" % _KEY_RIM
# the key bore's flat under the lips' face (y = -HW + FLANGE), which is all A has over it
_KEY_LIG = (SCREW_Y - (KEY_W / 2 / math.cos(math.radians(KEY_FLANK)) - TIP / 2)) - (-HW + FLANGE)
assert _KEY_LIG >= 2 * B - 1e-6, (
    "the key bore leaves %.2f under the lips' face, under two beads" % _KEY_LIG)
INS_POCKET = INS_D + INS_SLIP                # 4.8 the pocket's bore and the side slot's height
assert (BODY_T - INS_POCKET) / 2 >= B * 2 - 1e-9, (
    "the insert's pocket leaves %.2f over and under it, under two beads of %.1f"
    % ((BODY_T - INS_POCKET) / 2, B))
# the key's bore must stand two beads off the belt's back where the grip begins
_KEY_RUN = SEAT_T + HEAD_ZONE + END_WALL_A - (SEAT_T + SOCKET_IN)
_KEY_Z   = (-_KEY_RUN * math.tan(math.radians(KEY_DEG))
            + (KEY_W / 2) / math.cos(math.radians(KEY_DEG)))
# ...measured SQUARE to the bore: the nearest point is the slot's corner at the grip's start
_KEY_WALL = (-SLOT_H / 2 - _KEY_Z) * math.cos(math.radians(KEY_DEG))
assert _KEY_WALL >= 2 * B - 1e-6, (
    "the key bore stands %.2f off the belt's slot at the grip, under two beads: lengthen "
    "END_WALL_A (a 25 deg ball end cannot go steeper)" % _KEY_WALL)

# ── where the belt's two cut ends are ─────────────────────────────────────────────────────
BELT_END_A = LEN_A - GRIP                    # 9.6 half A's inner face to its end wall
BELT_END_B = INNER_B + END_WALL              # 10.8 half B's, likewise
BELT_TOOTH_IN = B / 2                        # 0.2 an end wall to the nearest tooth's centre:
                                             # _ribs stands its first rib BP/2 past that
SHOULDER_Z = SLOT_H / 2 - BTH + SLOT_CLR     # 0.15 where r5's ribs ended (its trapezoid)
RIB_TIP  = -SLOT_H / 2 + (BT - BTH)          # -0.15 the valley floor, belt back on the far face


def _ribs(x0: float, y0: float, y1: float) -> cq.Workplane:
    """N_TEETH ribs hanging from the slot's +z face into the belt's valleys, the first
    centred BP/2 past x0. Trapezoid: BP/2 wide at the root, one bead at SHOULDER_Z (the shape
    the r5 belt's teeth filled exactly, user), then a one-bead NUB on down to the valley floor
    with the belt lying on the slot's far face (RIB_TIP): the r5 ribs stopped SLOT_CLR short of
    it by the model and further in print at 0.4, and the belt crept on them under tension."""
    top = SLOT_H / 2
    out = None
    for k in range(N_TEETH):
        xc = x0 + B / 2 + BP * (k + 0.5)
        pts = [(xc - BP / 4, top), (xc + BP / 4, top), (xc + B / 2, SHOULDER_Z),
               (xc + B / 2, RIB_TIP), (xc - B / 2, RIB_TIP), (xc - B / 2, SHOULDER_Z)]
        r = (cq.Workplane("XZ").polyline(pts).close().extrude(-(y1 - y0))
             .translate((0.0, y0, 0.0)))
        out = r if out is None else out.union(r)
    return out


def _belt_slot(x0: float, x1: float, open_y: int) -> tuple:
    """(cutter, (ya, yb)) for a belt slot over [x0, x1], open on the open_y (±1) side face and
    run past whichever X end is asked for by the caller's own overshoot."""
    yc = -open_y * (BW / 2 + EDGE_CLR)               # the closed end
    ya, yb = sorted((yc, open_y * (HW + 1.0)))
    cut = box_at(x1 - x0, yb - ya, SLOT_H, x=(x0 + x1) / 2, y=(ya + yb) / 2, z=0.0)
    return cut, (ya, yb)


def _yz(pts, x0: float, x1: float) -> cq.Workplane:
    """A (y, z) section run along x over [x0, x1]."""
    return cq.Workplane("YZ").polyline(pts).close().extrude(x1 - x0).translate((x0, 0.0, 0.0))


def _rail(x0: float, x1: float, y_web: float, toward: int) -> cq.Workplane:
    """A channel rail over [x0, x1]: the web's outer face on y_web, its flanges reaching
    `toward` (±1, in y) over the lips of the half it covers, each FLANGE_T thick at the web
    and FLANGE_T + DOVE at its tip (the dovetail)."""
    L, xc = x1 - x0, (x0 + x1) / 2
    out = box_at(L, RAIL_T, BODY_T, x=xc, y=y_web + toward * RAIL_T / 2)
    y_in, y_tip = y_web + toward * RAIL_T, y_web + toward * (RAIL_T + FLANGE)
    for sz in (1, -1):
        out = out.union(_yz([(y_web, sz * HT), (y_tip, sz * HT),
                             (y_tip, sz * (HT - FLANGE_T - DOVE)),
                             (y_in, sz * (HT - FLANGE_T)), (y_web, sz * (HT - FLANGE_T))],
                            x0, x1))
    return out


def _lips(x0: float, x1: float, y_from: float, toward: int) -> cq.Workplane:
    """Cutter that necks a half's two lips from y_from outward (`toward` ±1) to take a
    rail's dovetailed flanges: LIP_HT - DOVE under the flange's tip, LIP_HT under its root,
    and LIP_CLR off the flange square to every face, the slope included."""
    th = math.atan2(DOVE, FLANGE)
    dw = LIP_CLR * (1.0 / math.cos(th) - 1.0) / math.tan(th)   # the slope's offset, along y
    w = [0.0, RAIL_CLR + dw, RAIL_CLR + FLANGE + dw, 3.0]
    out = None
    for sz in (1, -1):
        pts = [(y_from + toward * w[0], sz * (LIP_HT - DOVE)),
               (y_from + toward * w[1], sz * (LIP_HT - DOVE)),
               (y_from + toward * w[2], sz * LIP_HT), (y_from + toward * w[3], sz * LIP_HT),
               (y_from + toward * w[3], sz * 2 * HT), (y_from + toward * w[0], sz * 2 * HT)]
        c = _yz(pts, x0, x1)
        out = c if out is None else out.union(c)
    return out


def _key_bore() -> cq.Workplane:
    """The key's bore, from the ball's centre in the socket out through the back: a teardrop
    whose apex points up A's print direction (UP_A), its flanks KEY_FLANK off flat and its tip
    dulled to TIP. Not cadkit's printable_bore: its 45 deg flanks, crossed by a face at KEY_DEG,
    leave a rim 48 deg off vertical (the edge's slope is atan(cos KEY_DEG * tan flank))."""
    a = math.radians(KEY_DEG)
    d = cq.Vector(-math.cos(a), 0.0, -math.sin(a))
    up = cq.Vector(*UP_A)
    r, f = KEY_W / 2, math.radians(KEY_FLANK)
    apex = r / math.cos(f)
    flat = apex - TIP / 2
    w = (apex - flat) / math.tan(f)
    pl = cq.Plane(origin=(-SEAT_T - SOCKET_IN, SCREW_Y, 0.0), xDir=up.cross(d), normal=d)
    L = 2 * BODY_T / math.sin(a)
    tear = [(-r * math.sin(f), r * math.cos(f)), (r * math.sin(f), r * math.cos(f)),
            (w, flat), (-w, flat)]
    return (cq.Workplane(pl).circle(r).extrude(L)
            .union(cq.Workplane(pl).polyline(tear).close().extrude(L)))


def half_a() -> cq.Workplane:
    """The HEAD half, inner face on x = 0, body toward −x. Slot opens −y, where its lips
    are thinned for B's rail; its own rail is on +y and reaches over B."""
    body = box_at(LEN_A, IN_HW + HW, BODY_T, x=-LEN_A / 2, y=(IN_HW - HW) / 2)
    wx0, wx1 = -SEAT_T - HEAD_ZONE, -SEAT_T                        # head window
    # the walls' room: A stands HZ through the seat wall, the window AND the end wall, so each
    # wall lands on a full-thickness block (only along the window, a wall met the 6.4 body on
    # 0.3 of its 0.8, user), stepping back down to HT at 45 deg into the grip
    xa = wx0 - END_WALL_A
    step = HZ - HT
    room = [(0.0, -HZ), (0.0, HZ), (xa, HZ), (xa - step, HT), (xa - step, -HT), (xa, -HZ)]
    body = body.union(cq.Workplane("XZ").polyline(room).close().extrude(-(IN_HW + HW))
                      .translate((0.0, -HW, 0.0)))
    gx0, gx1 = -LEN_A, -LEN_A + GRIP                              # grip: outer end .. end wall
    cut, (ya, yb) = _belt_slot(gx0 - 1.0, gx1, -1)
    body = body.cut(cut).union(_ribs(gx0, -HW, yb))
    body = body.cut(box_at(HEAD_ZONE, IN_HW + HW + 2.0, 2 * WIN_HZ, x=(wx0 + wx1) / 2,
                           y=(IN_HW - HW) / 2))                    # through, bed face to top
    # the screw's way through the seat is a SLOT open to A's top face (-y): the screw is 15
    # long and the window 6.4, so it cannot be fed in along its axis; it drops in sideways, head
    # in the window, shank in the slot, and B's rail covers the slot once the halves are slid
    # together. Open upward in A's print, so its round end is a floor, not a roof.
    body = body.cut(cyl_x(SCR_CLR, SEAT_T + 0.2, -SEAT_T - 0.1, y=SCREW_Y))
    body = body.cut(box_at(SEAT_T + 0.2, SCREW_Y + HW + 1.0, SCR_CLR,
                           x=-SEAT_T / 2, y=(SCREW_Y - HW - 1.0) / 2))
    # key channel: from the socket, down and outward through the back (−z) -- a BORE on the
    # key's own axis (the ball end turns about it), teardropped for A's print direction, its
    # flanks at KEY_FLANK so the rims it leaves where it crosses the faces at KEY_DEG print
    # (see _key_bore). It crosses the head window's -z wall, so it stays a bore: opened to the
    # bed face it would leave that wall a strip, and it cannot come in from the bed side at
    # all -- any tilt toward +y meets the belt in the grip.
    body = body.cut(_key_bore())
    body = body.cut(_lips(-LEN_A - 1.0, 1.0, -HW + FLANGE, -1))
    # over the seat's screw slot the lips' neck leaves only two islands either side of it,
    # cut off from the seat wall: clear them (the head bears 0.25 inside where they start)
    body = body.cut(box_at(SEAT_T + 0.2, 1.0 + FLANGE, 2 * LIP_HT,
                           x=-SEAT_T / 2, y=-HW + FLANGE - (1.0 + FLANGE) / 2))
    body = body.union(_rail(0.0, RAIL_A_L, IN_HW, -1))
    for x0, x1, h in ((-LEN_A - 1.0, xa - step, HT), (xa, 0.0, HZ), (0.0, RAIL_A_L + 1.0, HT)):
        for sz in (1, -1):                                         # the two +y edges
            tri = [(IN_HW + 0.1, sz * (h - EDGE_CH - 0.1)), (IN_HW + 0.1, sz * (h + 0.1)),
                   (IN_HW - EDGE_CH - 0.1, sz * (h + 0.1))]
            body = body.cut(cq.Workplane("YZ").polyline(tri).close()
                            .extrude(x1 - x0).translate((x0, 0.0, 0.0)))
    return body


def half_b() -> cq.Workplane:
    """The INSERT half, inner face on x = 0, body toward +x. Slot and insert pocket open
    +y, under A's rail, where its lips are thinned for the rail's flanges; its own rail is
    on −y, stood RAIL_STEP off half A so it passes OUTSIDE it."""
    y0, y1 = -HW - RAIL_STEP, MOUTH_B
    body = box_at(LEN_B, y1 - y0, BODY_T, x=LEN_B / 2, y=(y0 + y1) / 2)
    body = body.cut(printable_bore(SCR_CLR, INNER_B - B + 0.1, (-0.1, SCREW_Y, 0.0),
                                   (1.0, 0.0, 0.0), UP_B, nozzle=TIP))  # clearance + runout
    ix0, il = SHOULDER, INS_L + INS_FIT                            # insert pocket, side entry
    body = body.cut(cyl_x(INS_POCKET, il, ix0, y=SCREW_Y))
    body = body.cut(box_at(il, 6.0, INS_POCKET, x=ix0 + il / 2, y=SCREW_Y + 3.0))
    gx0, gx1 = INNER_B + END_WALL, LEN_B
    cut, (ya, yb) = _belt_slot(gx0, gx1 + 1.0, +1)
    body = body.cut(cut).union(_ribs(gx0, ya, MOUTH_B))
    lip0 = MOUTH_B - FLANGE
    body = body.cut(_lips(-1.0, LEN_B + 1.0, lip0, +1))
    body = body.cut(box_at(il, 3.0, BODY_T + 2.0, x=ix0 + il / 2, y=lip0 + 1.5))   # no skin left there
    body = body.union(_rail(-RAIL_B_L, 0.0, -HW - RAIL_STEP, +1))
    # the rail web's outer edge on the TOOTH side (+z, inside the loop) is chamfered EDGE_CH:
    # at a twist error of +20 deg it is what met the other run of string 10's own belt (tools/
    # clamp_range). One bead, so the web's joint to its flange keeps two (asserted below).
    yw = -HW - RAIL_STEP
    tri = [(yw - 0.1, HT - EDGE_CH - 0.1), (yw - 0.1, HT + 0.1), (yw + EDGE_CH + 0.1, HT + 0.1)]
    return body.cut(cq.Workplane("YZ").polyline(tri).close()
                    .extrude(RAIL_B_L + 2.0).translate((-RAIL_B_L - 1.0, 0.0, 0.0)))


def screw_dummy() -> cq.Workplane:
    """M3 × SCREW_L socket head in half A's frame: bearing face on the seat wall, shank +x."""
    scr = headed_screw(M3, SCREW_L, head_d=HEAD_D, head_h=HEAD_H, socket_af=2.5)
    return scr.rotate((0, 0, 0), (0, 1, 0), -90).translate((-SEAT_T - HEAD_H, SCREW_Y, 0.0))


# ── coupon: the two halves in their print poses ───────────────────────────────────────────
COUPON_UP = (0.0, 0.0, 1.0)     # the plate's direction; each half is turned onto its bed face
HALF_A_UP = UP_A                # each half on its own: A lies on its closed +y face,
HALF_B_UP = UP_B                # B on its closed -y face, both slots opening upward


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
    nut = seated_insert(M3, (gap / 2 + SHOULDER, SCREW_Y, 0.0), (1.0, 0.0, 0.0))
    P = "belt_tensioner_"
    return [(P + "half_a", at(_HALF_A, -gap / 2)), (P + "half_b", at(_HALF_B, gap / 2)),
            (P + "screw", at(_SCREW, -gap / 2)), (P + "insert", nut)]


def belt_ends(gap: float = GAP) -> tuple:
    """(x of the cut end in half A, x of the one in half B) in the BELT-LOCAL frame: each
    end lies against its slot's end wall."""
    return -gap / 2 - BELT_END_A, gap / 2 + BELT_END_B


def belt_fit(loop: float) -> tuple:
    """(teeth, gap) for a belt whose path, as a closed loop, is `loop` long on its pitch
    line. The belt is CUT TO A TOOTH COUNT, and both grips hold it by its teeth, so the
    gap between the halves is not free: it is whatever the loop leaves once `teeth`
    pitches are in it. The cut is `teeth` * BP + 2 * BELT_TOOTH_IN long -- each end wall
    is BELT_TOOTH_IN past the last tooth's centre, so the cut goes through a tooth there.

    Of the two counts whose gap is inside the screw's travel, this is the LONGER belt,
    gap in [GAP - BP, GAP): tensioned, the screw still has that much left to close, which
    is what takes up a belt that has stretched. ⚠ MY READING of the clamp, not a stated
    rule (2026-10-12): the shorter count would leave under one tooth of take-up."""
    room = loop - BELT_END_A - BELT_END_B - 2 * BELT_TOOTH_IN
    teeth = math.floor((room - GAP) / BP) + 1
    return teeth, room - teeth * BP
