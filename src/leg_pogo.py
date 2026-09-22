# -*- coding: utf-8 -*-
"""THE LEG'S TWO BLIND-MATES, AS SPRING PINS ON A PAIR OF BOARDS (user, 2026-09-21).

It replaces the TRRS pair at both joints: the top one (leg <-> body adapter) and the
bottom one (pedal bar <-> adjust tenon). Each joint is TWO PCBs and nothing else, and
there is no jack, plug, coil, float spring, TPU throat, sleeve or bayonet left:

  * MALE -- on the LEG, a board STANDING ON EDGE in a slot in the tenon's end: a
    RIGHT-ANGLE 1 x 4 spring-pin header (Xinyangze YZ165615055F-04025-02, LCSC
    C54799748; its -01 sibling C5296819 is the same drawing) on its lower edge, pins
    pointing down the joint axis, and a SIDE-ENTRY JST PH (S4B-PH-SM4-TB) on its upper
    edge, mouth pointing UP the leg, so the harness leaves straight along the bore.
    The free tips stand INSIDE the tenon's face -- a detached leg has nothing proud.
  * FEMALE -- on the FIXED part, a flat board lying on the mortise roof (adapter) /
    floor (bar): four bare ENIG pads in a row, a top-entry SMT PH on its back.

EVERY PLACED PART ON ONE FACE, on both boards: the panel shares one assembly setting
(user), and the live JLCPCB quote (2026-09-21) showed what the alternative costs. A
THT PH on the bottom made the job "Both Sides": setup $25.75 -> $51.50 plus a $16.54
fixture, ~$45 an order -- and it rules out Economic PCBA, where Both Sides does not
exist. Standing the male board on edge is what lets a right-angle header and a
side-entry connector share one face.

ONE HEADER, NOT TWO (user's call, 2026-09-21: two if the tenon's diagonal fitted
them, else one). Two side by side need 22 of pads, and it is the FEMALE board that
cannot take them: it stands above the host face, so all of it has to go inside the
tenon's pocket, and a pocket along a 24-square tenon's diagonal leaves ~23 x 7 -- no
room for a connector and a screw beside 22 of pads. So each circuit gets ONE pin, at
120 gf -- stiffer per contact than the 70 gf x 2 it replaces.

RETENTION, both on the project's one-M4-through-the-board rule. The female's screw is
vertical, driven down the empty mortise. The male's cannot be -- its board is -- so
it runs SIDEWAYS through the tenon: head recessed in one flat, through the board, into
an insert pressed into the opposite flat from outside. The end of the tenon it sits
in is exposed whenever the leg is off.

12 V RATING. The header is rated 12 V DC / 1 A; bus B runs at 5 V behind a
current-limited switch, with an LDO on each sensor board (user, 2026-09-21).

FRAME. Every joint is built in LOCAL (t, s, d): t off the male board's component face,
s along the pin row, d INTO THE TENON from the mating plane (the tenon's end face = the
mortise's roof or floor when seated). Each joint picks which world axis t is, because
each tenon end has different things in it (see TOP and BOTTOM). The male board's BACK
is at t = 0 and everything on it lies at t > 0.

DIMENSIONS ARE THE DRAWINGS' (C54799748 YZ165615055F-04025-02; JST ePH pp.3-4, read
as images) except where marked INFERRED or RESERVED. This is CAD for bronner to route
from, not a routed board.
"""

from __future__ import annotations

import math

import cadquery as cq

from cadkit.fasteners import M4, insert_bore_cutter
from cadkit.holes import teardrop_hole
from cadkit.pcb import PCB_T
from . import dimensions as D
from . import leg_stack as LS

B = D.BEAD

# ── the spring header: right angle, 1 x 4, LCSC C54799748 ────────────────────
RA_N = 4                        # ONE PIN PER CIRCUIT: GND, 5V, CAN_H, CAN_L
RA_PITCH = 2.5
RA_BODY_S = 11.0                # housing along the row
RA_BODY_T = 2.5                 # ...off the board's face
RA_BODY_D = 2.5                 # ...along the pins, rear to the side shoulders (the
                                # middle steps 1.0 further; the board edge sits here)
RA_PIN_T = 1.3                  # plunger axis off the board's face -- INFERRED: the
                                # drawing's 1.30 is dimensioned to the housing face
RA_PLUNGER_D = 1.0
RA_FREE = 5.5                   # tip beyond the housing's rear, uncompressed
RA_WORK = 4.0                   # "working height": 120 gf here
RA_V = 12.0                     # rated DC volts (the bus runs at 5)
RA_GF = 120.0
RA_LCSC = ("C54799748", "C5296819")     # -02 and -01, the same drawing

# ── the female side: bare ENIG pads ──────────────────────────────────────────
PAD_D = 2.1                     # at the header's 2.5 pitch: 0.4 between pads
PAD_T = 0.035                   # 1 oz copper
MISALIGN = 0.45                 # the most a tip may land off its pad centre: the
                                # octagon's 0.3 fit plus the two boards' pocket fits
assert RA_PLUNGER_D / 2.0 + MISALIGN < PAD_D / 2.0, (
    "a O%.1f tip landing %.2f off centre runs off a O%.1f pad"
    % (RA_PLUNGER_D, MISALIGN, PAD_D))

# ── the chain, up from the mating plane ──────────────────────────────────────
SEAT_C = 1.0                    # compression with the joint seated: 1.0 of the 1.5
LOAD_SLOP = 0.25                # the bottom joint hangs this far open on its latch
                                # (bar_latch: the tenon's pocket floor is CLR below the
                                # hook); the top one is pressed shut by the body
PRINT_TOL = 0.30                # and the pocket depths are prints
assert SEAT_C - LOAD_SLOP - PRINT_TOL >= 0.4, "the pins barely touch when loaded"
assert SEAT_C + PRINT_TOL <= RA_FREE - RA_WORK, "the pins pass their working height"
PAD_Z = PCB_T                   # the female lies ON the host face: pads at 1.6
REAR = PAD_Z + RA_FREE - SEAT_C     # 6.1 the header's rear, seated
EDGE_D = REAR - RA_BODY_D           # 3.6 the male board's lower edge
TIP_REST = REAR - RA_FREE           # 0.6 -- the free tips, INSIDE the tenon's face
assert TIP_REST >= 0.5, "the free pin tips stand too near the tenon's face"

# ── the male board, standing on edge ─────────────────────────────────────────
CLR = 0.3                       # board / connector clearance in its printed pocket
WALL = D.MIN_WALL_2P
EDGE = 0.5                      # component to routed edge (JLCPCB's rule)
MB_S = 13.0                     # along the row: the side-entry PH's 11.9 + edges
TB = 0.0                        # the board's back...
TF = TB + PCB_T                 # ...and its component face
PIN_T = TF + RA_PIN_T           # 2.9 the plungers' line, and so the pads'
HOLE_D = 4.5                    # M4 clearance through a board (elec convention)
_SHAFT_R = M4.shaft_clr_d / 2.0
# the male's M4 runs sideways through the tenon ABOVE the header's cavity, a WALL clear
M_HOLE_D = REAR + CLR + WALL + _SHAFT_R         # 10.2
# JST PH, SIDE ENTRY, SMT: S4B-PH-SM4-TB (ePH p.4): 4 way B 11.9, body 6.0 deep with
# its tails (2.6) behind, 5.5 off the board. Mouth UP the leg, at the board's top edge.
SE_S = 11.9
SE_DEPTH = 6.0
SE_TAIL = 2.6
SE_H = 5.5
SE_LCSC = "C265102"             # S4B-PH-SM4-TB(LF)(SN), 30k in stock
PLUG_RUN = 3.6                  # the PHR-4's reach past the mouth (branner's table)
PLUG_S = 9.8                    # PHR-4 across (ePH p.3)
SE_TAIL0 = M_HOLE_D + _SHAFT_R + WALL + CLR # 14.3 the connector's cavity (which starts
                                            # CLR under its tails) a WALL above the screw
MB_TOP = SE_TAIL0 + SE_TAIL + SE_DEPTH      # 22.6 the board's top edge = the mouth
PLUG_TOP = MB_TOP + PLUG_RUN                # 26.2
BEND = 4 * B                    # 3.2 room above the plug for the harness to turn
DEEP = PLUG_TOP + BEND          # 29.4 the pocket's end
_HALF = LS.TEN_W / 2.0
assert TF + SE_H + CLR + WALL <= _HALF, "the connector breaks the tenon's flat"
assert TB - CLR - WALL >= -_HALF, "the board breaks the tenon's flat"

# ── the female board, flat on the host face ──────────────────────────────────
HEAD_D = 7.0                    # M4 button head: the head, not the hole, sets spacing
HEAD_H = 2.2
# its screw head stands to PAD_Z + HEAD_H = 3.8, past the male board's lower edge
# (3.6), so it sits BEHIND the male board (-t)
F_HOLE_T = TB - CLR - HEAD_D / 2.0 - CLR        # -4.1
_INS_R = M4.insert_pilot_d / 2.0
# its top-entry PH (B4B-PH-SM4-TB, C160354) on the back, +t of the insert -- clear of
# the insert's TEARDROP apex, which points +Y and so +t wherever t is Y
PH_S = 11.95
PH_V = 5.0
PH_TAIL = 2.0                   # its SMT tails, +t
PH_H = 8.5                      # MATED: the PHR-4's 6.85 on the header's undimensioned
                                # floor -- 1.65 of allowance
PH_LCSC = "C160354"
PH_T0 = F_HOLE_T + _INS_R * math.sqrt(2.0) + WALL + CLR  # 2.04 the body's -t edge
PH_T1 = PH_T0 + PH_V
FB_T0 = F_HOLE_T - HOLE_D / 2.0 - EDGE                  # -6.85 the female's -t edge
FB_T1 = PH_T1 + PH_TAIL + EDGE                          # ...and +t
FB_S = 13.0                                             # along the row
F_SCREW_L = 6.0                 # M4 x 6: 1.6 of board + 4.4 into the insert
INS_CLR = 0.4
_INS_WHY = ("a PCB's one M4 (project rule), into plastic with no depth behind it for "
            "a self-tap bite")
assert F_HOLE_T + HEAD_D / 2.0 <= TB - CLR, "the female's screw head hits the male board"
assert FB_T0 - CLR - WALL >= -_HALF and FB_T1 + CLR + WALL <= _HALF, (
    "the female's mouth breaks the tenon's flats")

# the male's sideways screw: head recessed in the +t flat, insert from the -t flat
M_SCREW_L = 20.0                # M4 x 20 button
M_HEAD_SEAT = _HALF - HEAD_H - 0.2                      # the counterbore's floor, in t
assert M_HEAD_SEAT - M_SCREW_L > -_HALF + 1.0, "the M4 x 20 pokes out the far flat"
assert M_HEAD_SEAT - M_SCREW_L < -_HALF + M4.insert_depth - 3.0, (
    "under 3 of the M4 x 20 reaches its insert")

# ── the leg's harness ────────────────────────────────────────────────────────
# TWO TWISTED PAIRS of 28 AWG PVC hookup wire -- CAN_H/CAN_L one pair, 5V/GND the
# other -- crimped into PHR-4 housings at both ends AFTER threading. A round 4-core
# was rejected: the datasheeted ones that fit are too fat (Alpha 86004 is O4.83) and
# none pairs CAN_H with CAN_L. PVC hookup takes a heat-set coil on src.coil_mandrel.
HARNESS_WIRE_OD = 0.9           # 28 AWG 7/36 PVC hookup (Alpha 3048-class)
HARNESS_D = 3 * B               # 2.4: four 0.9 wires bundle to 0.9 (1 + sqrt2) = 2.17
HARNESS_BEND_STATIC = 3.0 * HARNESS_D   # 7.2 -- set once, no foil, no jacket
assert HARNESS_D >= HARNESS_WIRE_OD * (1 + math.sqrt(2)), "the bundle is under-sized"


# ── the two joints ───────────────────────────────────────────────────────────
class Joint(object):
    """A joint's mating plane and axes: `T` and `S` are world unit vectors (axis
    aligned) for t and s, `dz` is +-1, world Z of 'into the tenon'."""

    def __init__(self, name, z, dz, T, S, tenon_up, host_up):
        self.name, self.z, self.dz, self.T, self.S = name, z, dz, T, S
        self.tenon_up, self.host_up = tenon_up, host_up
        self.x, self.y = LS.LEG_X, LS.LEG_Y

    def p(self, t, s, d):
        return (self.x + t * self.T[0] + s * self.S[0],
                self.y + t * self.T[1] + s * self.S[1], self.z + self.dz * d)

    def box(self, t0, t1, s0, s1, d0, d1):
        pts = [self.p(t, s, d) for t in (t0, t1) for s in (s0, s1) for d in (d0, d1)]
        lo = [min(q[i] for q in pts) for i in range(3)]
        hi = [max(q[i] for q in pts) for i in range(3)]
        return cq.Workplane("XY").add(cq.Solid.makeBox(
            hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], cq.Vector(*lo)))

    def cyl_d(self, dia, t, s, d0, d1):
        """A cylinder along the joint axis."""
        return cq.Workplane("XY").add(cq.Solid.makeCylinder(
            dia / 2.0, abs(d1 - d0), cq.Vector(*self.p(t, s, min(d0, d1))),
            cq.Vector(0, 0, self.dz)))

    def cyl_t(self, dia, t0, t1, s, d):
        """A cylinder along t."""
        return cq.Workplane("XY").add(cq.Solid.makeCylinder(
            dia / 2.0, abs(t1 - t0), cq.Vector(*self.p(min(t0, t1), s, d)),
            cq.Vector(self.T[0], self.T[1], 0)))

    def bore_d(self, dia, t, s, d0, d1, up):
        return teardrop_hole(dia, d1 - d0, self.p(t, s, d0), (0, 0, self.dz), up)

    def bore_t(self, dia, t0, t1, s, d, up):
        return teardrop_hole(dia, t1 - t0, self.p(t0, s, d),
                             (self.T[0], self.T[1], 0), up)

    def rows(self):
        for k in range(RA_N):
            yield (k - (RA_N - 1) / 2.0) * RA_PITCH


# TOP: the fixed tenon's upper end, in the adapter. Into the tenon is -Z. t is +Y:
# the leg latch's pocket owns y < -1.6 from 27.75 down, the harness turns at 26-29,
# and with t = +Y everything of the male's lies at y >= -CLR. The sideways screw runs
# along Y, 17 above that pocket.
TOP = Joint("top", LS.Z_MORTISE_ROOF, -1.0, (0.0, 1.0), (1.0, 0.0),
            LS.PRINT_UP["fixed_tenon"], LS.PRINT_UP["body_adapter"])
# BOTTOM: the adjust tenon's lower end, in the pedal bar. Into the tenon is +Z. t is +X
# and the row runs along Y: the bar latch's pocket across the +Y side starts at y 10.5
# (probed) and its lead-in at 11.81, and the ladder is 64 up.
BOTTOM = Joint("bottom", LS.Z_ADJ_TEN_BOT, 1.0, (1.0, 0.0), (0.0, 1.0),
               LS.PRINT_UP["adjust_tenon"], (0.0, 1.0, 0.0))
assert MB_S / 2.0 + CLR + WALL <= _HALF and FB_S / 2.0 + CLR + WALL <= _HALF, (
    "a board breaks the tenon's flat along the row")


# ── the boards, as dummies ───────────────────────────────────────────────────
def male(j, compress: float = SEAT_C):
    """The leg's board on edge, pins down the joint axis at `compress` (SEAT_C is the
    seated state; 0 is the leg off)."""
    board = j.box(TB, TF, -MB_S / 2.0, MB_S / 2.0, EDGE_D, MB_TOP)
    board = board.cut(j.cyl_t(HOLE_D, TB - 1.0, TF + 1.0, 0.0, M_HOLE_D))
    hdr = j.box(TF, TF + RA_BODY_T, -RA_BODY_S / 2.0, RA_BODY_S / 2.0, EDGE_D, REAR)
    tip = REAR - (RA_FREE - compress)
    for s in j.rows():
        hdr = hdr.union(j.cyl_d(RA_PLUNGER_D, PIN_T, s, tip, EDGE_D + 0.01))
    ph = j.box(TF, TF + SE_H, -SE_S / 2.0, SE_S / 2.0, MB_TOP - SE_DEPTH, MB_TOP)
    ph = ph.union(j.box(TF, TF + 0.5, -SE_S / 2.0 + 1.0, SE_S / 2.0 - 1.0,
                        SE_TAIL0, MB_TOP - SE_DEPTH + 0.01))
    ph = ph.union(j.box(TF + 0.5, TF + SE_H - 0.5, -PLUG_S / 2.0, PLUG_S / 2.0,
                        MB_TOP - 0.01, PLUG_TOP))
    return [("pogo_male_board_%s" % j.name, board),
            ("pogo_male_pins_%s" % j.name, hdr),
            ("pogo_male_ph_%s" % j.name, ph)]


def female(j):
    """The fixed part's board: on the host face, pads up at PAD_Z, PH underneath."""
    board = j.box(FB_T0, FB_T1, -FB_S / 2.0, FB_S / 2.0, 0.0, PAD_Z)
    board = board.cut(j.cyl_d(HOLE_D, F_HOLE_T, 0.0, -1.0, PAD_Z + 1.0))
    pads = None
    for s in j.rows():
        p = j.cyl_d(PAD_D, PIN_T, s, PAD_Z - PAD_T, PAD_Z)
        pads = p if pads is None else pads.union(p)
    board = board.cut(pads)
    ph = j.box(PH_T0, PH_T1, -PH_S / 2.0, PH_S / 2.0, -PH_H, 0.0)
    ph = ph.union(j.box(PH_T1 - 0.01, PH_T1 + PH_TAIL, -PH_S / 2.0 + 1.0,
                        PH_S / 2.0 - 1.0, -0.5, 0.0))
    return [("pogo_female_board_%s" % j.name, board),
            ("pogo_female_pads_%s" % j.name, pads),
            ("pogo_female_ph_%s" % j.name, ph)]


def screws(j):
    """The female's M4 x 6 (down the mortise) and the male's M4 x 20 (sideways)."""
    fh = j.cyl_d(HEAD_D, F_HOLE_T, 0.0, PAD_Z, PAD_Z + HEAD_H)
    fs = j.cyl_d(M4.screw_d, F_HOLE_T, 0.0, PAD_Z - F_SCREW_L, PAD_Z)
    mh = j.cyl_t(HEAD_D, M_HEAD_SEAT, M_HEAD_SEAT + HEAD_H, 0.0, M_HOLE_D)
    ms = j.cyl_t(M4.screw_d, M_HEAD_SEAT - M_SCREW_L, M_HEAD_SEAT, 0.0, M_HOLE_D)
    return [("pogo_female_screw_%s" % j.name, fh.union(fs)),
            ("pogo_male_screw_%s" % j.name, mh.union(ms))]


def dummies():
    out = []
    for j in (TOP, BOTTOM):
        out += male(j) + female(j) + screws(j)
    return out + harness()


# ── what the TENON gives up ──────────────────────────────────────────────────
MOUTH_D = PAD_Z + HEAD_H + CLR      # 4.1 the female board + its head come in this far


def tenon_negatives(j, route_xy, route_d, route_top, up=None):
    """Cut in the tenon: the MOUTH that swallows the female board and its screw head,
    the SLOT the male board slides up (a CLR fit that locates it in t and s), the
    header's and the connector's room on its face, the plug and the harness's turn,
    the sideways screw (counterbore in the +t flat, insert from the -t flat), and a way
    over to the lead's bore at `route_xy` (world), `route_d` wide, on to `route_top`."""
    up = up or j.tenon_up
    out = j.box(FB_T0 - CLR, FB_T1 + CLR, -FB_S / 2.0 - CLR, FB_S / 2.0 + CLR,
                -1.0, MOUTH_D)
    # ...and the female's screw head, which overhangs its board's -t edge
    out = out.union(j.bore_d(HEAD_D + 2 * CLR, F_HOLE_T, 0.0, -1.0, MOUTH_D, up))
    out = out.union(j.box(TB - CLR, TF + 0.01, -MB_S / 2.0 - CLR, MB_S / 2.0 + CLR,
                          -1.0, MB_TOP + CLR))
    out = out.union(j.box(TF, TF + RA_BODY_T + CLR, -RA_BODY_S / 2.0 - CLR,
                          RA_BODY_S / 2.0 + CLR, -1.0, REAR + CLR))
    out = out.union(j.box(TF, TF + SE_H + CLR, -SE_S / 2.0 - CLR, SE_S / 2.0 + CLR,
                          SE_TAIL0 - CLR, PLUG_TOP + CLR))
    # the harness's turn over to the lead's bore, then the bore itself onward
    rx, ry = route_xy
    rt = (rx - j.x) * j.T[0] + (ry - j.y) * j.T[1]
    rs = (rx - j.x) * j.S[0] + (ry - j.y) * j.S[1]
    pt = TF + SE_H / 2.0
    t0, t1 = sorted((pt, rt))
    s0, s1 = sorted((0.0, rs))
    out = out.union(j.box(t0 - route_d / 2.0, t1 + route_d / 2.0,
                          s0 - route_d / 2.0, s1 + route_d / 2.0, PLUG_TOP, DEEP))
    top_d = (route_top - j.z) * j.dz
    out = out.union(j.bore_d(route_d, rt, rs, DEEP - route_d, top_d, up))
    # the male's sideways M4: counterbore in the +t flat, clearance through, insert
    # pocket from the -t flat
    out = out.union(j.bore_t(HEAD_D + 2 * CLR, M_HEAD_SEAT, _HALF + 1.0, 0.0,
                             M_HOLE_D, up))
    out = out.union(j.bore_t(M4.shaft_clr_d, -_HALF + M4.insert_depth - 0.01,
                             M_HEAD_SEAT + 0.01, 0.0, M_HOLE_D, up))
    out = out.union(insert_bore_cutter(
        M4, j.p(-_HALF, 0.0, M_HOLE_D), (j.T[0], j.T[1], 0), 0.01, overshoot=1.0,
        reason=_INS_WHY, print_up=up))
    return out


# ── what the FIXED part gives up (the female's cavity and insert) ────────────
# the connector's cavity floor, into the host (d < 0): the housing plus room to turn --
# capped so the ADAPTER keeps a WALL of skin under its top face (it has 12.8 above the
# roof); the harness turns straight into the top-face groove, which reaches below it
F_DEEP = -min(PH_H + BEND, LS.Z_TOP - LS.Z_MORTISE_ROOF - WALL)       # -11.2


def _gable(j, t0, t1, s0, s1, d0, d1, up):
    """A box cavity whose ceiling is PRINTABLE: in a host that builds along world +Y
    the cavity's +Y face is a ceiling, so it is carried up to a 45 degree ridge along
    the joint axis."""
    assert up[1] > 0.99, "the gable assumes a +Y build"
    cav = j.box(t0, t1, s0, s1, d0, d1)
    b = cav.val().BoundingBox()
    hw = (b.xmax - b.xmin) / 2.0
    xc = (b.xmax + b.xmin) / 2.0
    tri = (cq.Workplane("XY").workplane(offset=b.zmin)
           .polyline([(xc - hw, b.ymax - 0.01), (xc + hw, b.ymax - 0.01),
                      (xc, b.ymax + hw)]).close().extrude(b.zmax - b.zmin))
    return cav.union(tri)


def host_negatives(j, up=None, deep=F_DEEP):
    """Cut in the adapter / the bar: the female's PH cavity (gabled -- both hosts
    build +Y) and its insert. The caller adds the harness's way out."""
    up = up or j.host_up
    out = _gable(j, PH_T0 - CLR, PH_T1 + PH_TAIL + CLR, -PH_S / 2.0 - CLR,
                 PH_S / 2.0 + CLR, deep, 0.01, up)
    out = out.union(insert_bore_cutter(
        M4, j.p(F_HOLE_T, 0.0, 0.0), (0, 0, -j.dz), INS_CLR, overshoot=0.01,
        reason=_INS_WHY, print_up=up))
    return out


CHAN_W = 4 * B                  # 3.2: the harness with room
CHAN_D = max(6 * B, LS.Z_TOP - (LS.Z_MORTISE_ROOF - F_DEEP) + 1.0)
                                # 4.8, and it reaches the connector's cavity -- the
                                # body tenons are fused on after this is cut and refill
                                # the groove's top ~1 mm


def adapter_features(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """(None, negatives) for the body adapter at the signal corner, in its own frame.
    The harness rises out of the female's connector into a groove in the top face that
    runs out the -Y face, inboard, under the instrument (the old lead's exit)."""
    j = TOP
    neg = host_negatives(j)
    fc = j.p((PH_T0 + PH_T1) / 2.0, 0.0, 0.0)
    y_out = j.y - LS.LEG_W / 2.0 - 1.0
    y_in = fc[1] + CHAN_W
    neg = neg.union(cq.Workplane("XY").add(cq.Solid.makeBox(
        CHAN_W, y_in - y_out, CHAN_D + 1.0,
        cq.Vector(fc[0] - CHAN_W / 2.0, y_out, LS.Z_TOP - CHAN_D))))
    return None, neg


def bar_features(floor_z: float, chamber_top_z: float):
    """(None, negatives) for the pedal bar, in the BAR's frame: the connector's cavity
    runs on down into the wiring chamber, which it overlaps."""
    j = Joint("bottom_bar", floor_z, BOTTOM.dz, BOTTOM.T, BOTTOM.S, BOTTOM.tenon_up,
              BOTTOM.host_up)
    return None, host_negatives(j, deep=chamber_top_z - floor_z - 0.01)


# ── the harness, drawn ───────────────────────────────────────────────────────
def _coil(cx, cy, z_top, z_bot, turns, r, d):
    """The leg's slack as a helix of `turns` whole turns about (cx, cy)."""
    path = cq.Wire.makeHelix((z_top - z_bot) / turns, z_top - z_bot, r,
                             cq.Vector(cx, cy, z_bot), cq.Vector(0, 0, 1))
    prof = cq.Wire.makeCircle(d / 2.0, path.startPoint(), path.tangentAt(0.0))
    return cq.Workplane("XY").add(cq.Solid.sweep(prof, [], path, isFrenet=True))


def harness():
    """THE RUN, drawn: plug to plug down the whole leg -- over to the old lead's bore,
    down the fixed tenon, COILED through the gap between the tenons (src.coil_mandrel's
    coil at the span the leg is drawn at), the adjust tenon's channel past the ladder,
    the jog, and over to the bottom board -- plus the two female stubs."""
    from . import leg_trrs as LTR
    from . import bar_trrs as BT
    from . import coil_mandrel as CM
    from .leg_trrs import _run
    d = HARNESS_D
    dm = PLUG_TOP + BEND / 2.0
    pt = TF + SE_H / 2.0
    xs, ys = LTR._ax()
    xb, yb = BT._ax()
    xc, yc = LS.LEG_X + BT.CH_X, LS.LEG_Y + BT.CH_Y
    z_a, z_b = LS.Z_FIX_TEN_BOT - 8.0, LS.Z_ADJ_TEN_TOP + 8.0
    pitch = (z_a - z_b) / CM.TURNS
    r = math.sqrt(max((CM.COIL_LEN / CM.TURNS) ** 2 - pitch ** 2, 0.0)) / math.pi / 2.0
    ax, ay = LS.LEG_X, LS.LEG_Y
    upper = _run([TOP.p(pt, 0.0, PLUG_TOP), TOP.p(pt, 0.0, dm),
                  (xs, ys, TOP.p(0, 0, dm)[2]), (xs, ys, LS.Z_FIX_TEN_BOT - 2.0),
                  (ax + r, ay, z_a)], d)
    lower = _run([(ax + r, ay, z_b), (xc, yc, LS.Z_ADJ_TEN_TOP + 2.0),
                  (xc, yc, BT.PASS_TOP), (xb, yb, BT.CH_BOT),
                  (xb, yb, BOTTOM.p(0, 0, dm)[2]), BOTTOM.p(pt, 0.0, dm),
                  BOTTOM.p(pt, 0.0, PLUG_TOP)], d)
    leg = upper.union(_coil(ax, ay, z_a, z_b, CM.TURNS, r, d)).union(lower)
    fc = (PH_T0 + PH_T1) / 2.0
    f0 = TOP.p(fc, 0.0, -PH_H)
    zc = max(LS.Z_TOP - CHAN_D + d / 2.0 + 0.2,      # in the groove, clear of the
             TOP.p(0, 0, -PH_H)[2] + d / 2.0 + 0.2)   # housing it passes over
    y_out = LS.LEG_Y - LS.LEG_W / 2.0
    body = _run([f0, (f0[0], f0[1], zc), (f0[0], y_out, zc), (f0[0], y_out - 12.0, zc)],
                d)
    g0 = BOTTOM.p(fc, 0.0, -PH_H)
    g1 = BOTTOM.p(fc, 0.0, -17.0)
    bar = _run([g0, g1, (g1[0] + 10.0, g1[1], g1[2])], d)   # along the chamber, toward
                                                            # the trough
    return [("pogo_harness_leg", leg), ("pogo_harness_body", body),
            ("pogo_harness_bar", bar)]
