# -*- coding: utf-8 -*-
"""THE LEG'S TWO BLIND-MATES, AS POGO PINS ON A PAIR OF BOARDS (user, 2026-09-21).

It replaces the TRRS pair at both joints: the top one (leg <-> body adapter) and the
bottom one (pedal bar <-> adjust tenon). Each joint is now TWO PCBs and nothing else:

  * MALE -- a 2 x 4 spring-pin header (Xinyangze YZ76615070R-08025-01, LCSC C5280862)
    on the LEG, in a pocket in the tenon's end. Its tips stand BELOW the tenon's face
    at rest, so a detached leg has nothing proud to knock (user rule).
  * FEMALE -- flat ENIG pads on the FIXED part, on a one-bead pedestal off the mortise
    roof (adapter) and floor (bar). The pedestal reaches up into the male pocket as
    the joint closes, which is how recessed tips find their pads.

Each board has ONE M4 through it into a heat-set insert (the project's PCB rule) and
ONE top-entry JST PH header on its back for the crimped leg harness -- the only
wiring through the leg now.

BOTH BOARDS ARE SINGLE-SIDED FOR SMT, because the whole PCB panel shares one set of
assembly settings (user). The FEMALE's face is bare copper pads, so its SMT PH on the
back is its only placed part. The MALE's pin header is SMT on its face, so its PH is
the THROUGH-HOLE B4B-PH-K-S on the back, soldered by JLCPCB's THT step (the tee
boards' XH headers already put that step on the panel) -- never by the user. Its
posts come through on the pin side, so it sits OUTBOARD of the pin header, not under
it. JLCPCB publish no rule on whether a bottom-bodied THT part counts as a second
side; their setup and stencil fees are priced by SMT side and THT is its own labour
line, so it should not -- confirm on the live quote with the part on the Bottom layer. There is no jack, plug, coil, float spring, TPU throat,
sleeve or bayonet left at either joint.

WHY THE PINS ARE ON THE LEG, which reverses what was first proposed (pads on the
leg). It is a depth budget, not a preference. A male stack is the pin's travel plus
the board plus the connector behind it -- 5.75 + 1.6 + 9.8 -- and the body adapter
has 12.8 above its mortise roof. The female stack is 1.6 + 9.8. So at the top joint
only the pads fit in the adapter, and the leg's 252 of solid tenon takes the pins;
the bottom joint does the same so there is ONE male board and ONE female board.
The pads remain a one-screw swap: their M4 is reached down the empty mortise.

WHY THIS HEADER AND NOT THE 3 mm-STROKE ONE the research first ranked highest (HJ Tech
C54935105). Its 3 mm was bought for a 3 mm latch slop that does not exist: FLOAT was a
TRRS allowance, and the latches themselves hang on CLR = 0.25 (bar_latch.planes: the
tenon pocket is CLR below the hook). And it is THROUGH-HOLE -- its tails fill the
back of the board exactly where the harness connector has to go. C5280862 is SMT, a
single 2 x 4 part, 10.16 x 5.08, 2.0 of total stroke. Both joints sit within +-0.3 of
their seated position when loaded (the top one under the instrument's weight, the
bottom one hanging on its latch), so SEAT_C of compression is set there with margin
both ways -- asserted below.

12 V RATING. The header's datasheet rates it 12 V DC / 2 A. Bus B runs at 5 V behind
the motor controller's current-limited switch, with an LDO on each sensor board
(user, 2026-09-21), so the pins run inside their rating.

FRAME. Every joint is built in LOCAL (u, v, d): u along world +Y, v along world X,
d INTO THE TENON from the mating plane (the tenon's end face = the mortise's roof or
floor when seated). v runs along X ON PURPOSE: the adapter and the bar both build
along +Y, so a cavity's +Y face is a ceiling, and with the connector's LONG side
along Y that ceiling is only 5.1 across and closes with a 2.6 gable -- the other way
round it wanted 6.3 and ran into the insert, whose own teardrop points +Y too. The two boards share one outline, one screw position and one
connector position, so the same numbers place both halves.

DIMENSIONS ARE THE DATASHEET'S where one exists (C5280862 drawing YZ76615070R-08025-01,
read 2026-09-21), and RESERVED -- marked -- where JST's PH SMT drawing was not read.
This is CAD for bronner to route from, not a routed board.
"""

from __future__ import annotations

import math

import cadquery as cq

from cadkit.fasteners import M4, insert_bore_cutter
from cadkit.pcb import PCB_T
from . import dimensions as D
from . import leg_stack as LS

B = D.BEAD

# ── the spring header: Xinyangze YZ76615070R-08025-01, LCSC C5280862 ──────────
POGO_NU, POGO_NV = 4, 2         # 2 x 4 -- TWO PINS PER CIRCUIT (GND, 5V, CAN_H, CAN_L)
POGO_PITCH = 2.54
POGO_BODY_U = 10.16             # housing, off the drawing
POGO_BODY_V = 5.08
POGO_FOOT_H = 0.50              # the solder feet the housing stands on
POGO_BODY_TOP = 3.00            # housing top above the board
POGO_BARREL_D = 1.50
POGO_BARREL_TOP = 4.40          # barrel shoulder -- INFERRED from the drawing's view,
                                # it carries no dimension; cosmetic only
POGO_PLUNGER_D = 0.90
POGO_FREE = 7.00                # tip above the board, uncompressed
POGO_WORK = 5.50                # "working height": 70 gf at this compression
POGO_LIMIT = 5.00               # compression limit -- never reach it
POGO_V = 12.0                   # rated DC volts (the bus runs at 5)

# ── the female side: bare ENIG pads ──────────────────────────────────────────
PAD_D = 2.0                     # at the header's own 2.54 pitch: 0.54 between pads
PAD_T = 0.035                   # 1 oz copper
MISALIGN = 0.5                  # the most a tip may land off its pad centre: the
                                # octagon's 0.3 fit plus each board's pocket clearance
assert POGO_PLUNGER_D / 2.0 + MISALIGN <= PAD_D / 2.0 + 1e-9, (
    "a O%.2f tip landing %.2f off centre runs off a O%.1f pad"
    % (POGO_PLUNGER_D, MISALIGN, PAD_D))

# ── the chain, down from the pad face ────────────────────────────────────────
SEAT_C = 1.25                   # compression with the joint seated. Mid-way between
                                # free (0) and working (1.5), leaving room both ways:
LOAD_SLOP = 0.25                # the bottom joint hangs this far open on its latch
                                # (bar_latch: the tenon's pocket floor is CLR below the
                                # hook), the top one is pressed shut by the body's weight
PRINT_TOL = 0.30                # and the pocket depths are prints
assert SEAT_C - LOAD_SLOP - PRINT_TOL > 0.5, "the pins barely touch when loaded"
assert SEAT_C + PRINT_TOL < POGO_FREE - POGO_LIMIT, "the pins can reach their limit"
REACH = POGO_FREE - SEAT_C      # 5.75: male board face -> pad face, seated

PED_H = 1 * B                   # 0.8 the female pedestal: one bead off the roof/floor
PAD_Z = PED_H + PCB_T           # 2.4 the pad face, INTO the tenon side of the plane
MALE_FACE = PAD_Z + REACH       # 8.15 the male board's face, in the tenon
MALE_BACK = MALE_FACE + PCB_T   # 9.75 ...and its back, on the pocket's floor
TIP_REST = MALE_FACE - POGO_FREE    # 1.15 -- the free tips, RECESSED inside the face
assert TIP_REST > 0.5, "the free pin tips stand too near the tenon's face"

# ── one board outline, one screw, one connector: both halves ─────────────────
BOARD_U = 13.0                  # u: the connector (11.95 with its tabs) + edge
ARRAY_V = -3.4                  # the pin/pad array's centre, and the connector's
BOARD_V0 = -8.4                 # v: the connector's tails run out -v, so the board's
BOARD_V1 = 6.85                 # -v edge carries them; +v carries the screw
BOARD_V = BOARD_V1 - BOARD_V0   # 15.25
EDGE = 0.5                      # component to routed edge (JLCPCB's rule)
SCREW_V = 4.0                   # the M4 -- see the walls below
HOLE_D = 4.5                    # M4 clearance through the board (elec convention)
HEAD_D = 7.0                    # button head, as elec/trrs_adapter: the head, not the
HEAD_H = 2.2                    #   hole, is what sets the spacing
SCREW_L = 6.0                   # M4 x 6 button: board + 4.4 into the insert
assert SCREW_V - HEAD_D / 2.0 >= ARRAY_V + POGO_BODY_V / 2.0 + 0.3, (
    "the screw head lands on the pin header")
assert BOARD_V1 - SCREW_V - HOLE_D / 2.0 >= EDGE, "the M4 hole is off the board"
assert ARRAY_V - POGO_BODY_V / 2.0 >= BOARD_V0 + EDGE, "the header is off the board"

# JST PH, SMT TOP ENTRY (B4B-PH-SM4-TB), under the array on the BACK. SMT so it has
# no tails through to the pin side; top entry so the harness leaves straight up the
# tenon's bore. OFF JST's OWN DRAWING (ePH catalogue p.4 "Header (SMT type)", read as
# an image 2026-09-21 -- its text layer is unreadable, which is why cadkit had
# reserved these): 4 way B = 11.95 overall, body 5.0 deep with its signal tails
# running (2) further out ONE side, 6.6 tall. The PHR-4 housing is 6.85 tall (p.3).
PH_U = 11.95                    # overall, reinforcement tabs included
PH_V = 5.0                      # the body
PH_TAIL = 2.0                   # the SMT signal tails, flat on the board, one side (-v)
PH_TAIL_H = 0.5                 # their height off the board -- a low strip
PH_BODY_H = 6.6
PHR_H = 6.85                    # the crimp housing
PH_H = 8.5                      # MATED: the housing's 6.85 standing on the header's
                                # floor. The floor is not dimensioned; 1.65 of it is
                                # an allowance, and the harness's bend (below) gets its
                                # own room on top of this
BEND = 4 * B                    # 3.2 room above the housing for the harness to turn

# THE MALE's HEADER IS THROUGH-HOLE: JST B4B-PH-K-S (ePH p.3, "Header (Through-hole
# type)", top entry): 4 way B = 9.9, 4.5 deep, 6.0 tall, posts (3.4) below the seat.
PHK_U = 9.9
PHK_V = 4.5
PHK_H = 6.0
PHK_POST = 0.64                 # square post, as XH
PHK_HOLE_D = 1.0                # its PCB hole (as XH's: the post's diagonal is 0.91)
PHK_PROUD = 3.4 - PCB_T         # 1.8 of post through to the PIN side
PHK_LCSC = "C131334"            # B4B-PH-K-S(LF)(SN), JLCPCB Extended, 138k in stock
PH_LCSC = "C160354"             # B4B-PH-SM4-TB(LF)(SN), JLCPCB Extended, 45k in stock

CLR = 0.3                       # board / connector clearance in its printed pocket
WALL = D.MIN_WALL_2P

# the insert has to keep a wall to the connector's cavity beside it
_INS_R = M4.insert_pilot_d / 2.0
assert (SCREW_V - _INS_R) - (ARRAY_V + PH_V / 2.0 + CLR) >= WALL - 1e-9, (
    "only %.2f between the insert and the connector's cavity"
    % ((SCREW_V - _INS_R) - (ARRAY_V + PH_V / 2.0 + CLR)))
assert ARRAY_V - PH_V / 2.0 - PH_TAIL >= BOARD_V0 + EDGE - 1e-9, (
    "the connector's tails run off the board")
# the MALE's THT header, outboard of the pin header on -v: its posts come through on
# the pin side, so its row must clear the header's housing
PHK_ROW_V = ARRAY_V - POGO_BODY_V / 2.0 - 1.6 * B       # -7.22, 1.28 off the housing
MALE_V0 = PHK_ROW_V - PHK_V / 2.0 - EDGE                # -9.97 the male's -v edge
assert PHK_ROW_V + PHK_POST / 2.0 < ARRAY_V - POGO_BODY_V / 2.0 - 0.5, (
    "the THT posts come up under the pin header")
INS_CLR = 0.4                   # screw-tip clearance past the insert
_INS_WHY = ("a PCB's one M4 (project rule): an M4 x 6 through 1.6 of board ends inside "
            "the insert, and there is no depth behind it for a self-tap bite -- the "
            "pin travel and the connector own the rest of the stack")
assert SCREW_L - PCB_T <= M4.insert_depth + INS_CLR, "the screw bottoms out"


# ── the leg's harness ────────────────────────────────────────────────────────
# TWO TWISTED PAIRS of 28 AWG PVC hookup wire -- CAN_H/CAN_L one pair, 5V/GND the
# other -- crimped into PHR-4 housings at both ends AFTER threading, so no bore
# ever has to pass more than a contact. Not a round jacketed 4-core: the ones with a
# datasheet that fit (Alpha 86004 is O4.83) are fatter than the bores the old lead
# set, and a round 4-core does not pair CAN_H with CAN_L. A pair twisted is what CAN
# wants, and PVC hookup takes a heat-set coil on src.coil_mandrel.
HARNESS_WIRE_OD = 0.9           # 28 AWG 7/36 PVC hookup (Alpha 3048-class) -- inside
                                # the SPH-002T contact's 0.8..1.5 insulation range
HARNESS_D = 3 * B               # 2.4: four 0.9 wires bundle to 0.9 (1 + sqrt2) = 2.17
HARNESS_BEND_STATIC = 3.0 * HARNESS_D   # 7.2 -- a set-once bundle of loose stranded
                                # conductors: no foil, no jacket, so the 3xOD rule of
                                # thumb is the honest yardstick here, and the duty is
                                # the one leg_trrs.CABLE_BEND_STATIC already argued
assert HARNESS_D >= HARNESS_WIRE_OD * (1 + math.sqrt(2)), "the bundle is under-sized"


# ── the two joints ───────────────────────────────────────────────────────────
class Joint(object):
    """Where a joint's mating plane is and which way is which. `vx` is +-1: world X
    of the board's v axis (u is always world +Y). `dz` is +-1: world Z of 'into the
    tenon'."""

    def __init__(self, name, z, vx, dz, tenon_up, host_up):
        self.name, self.z, self.vx, self.dz = name, z, vx, dz
        self.tenon_up, self.host_up = tenon_up, host_up
        self.x, self.y = LS.LEG_X, LS.LEG_Y

    def p(self, u, v, d):
        return (self.x + self.vx * v, self.y + u, self.z + self.dz * d)

    def uv(self, x, y):
        """World (x, y) -> local (u, v)."""
        return y - self.y, (x - self.x) * self.vx

    def box(self, u0, u1, v0, v1, d0, d1):
        a, b = self.p(u0, v0, d0), self.p(u1, v1, d1)
        lo = [min(a[i], b[i]) for i in range(3)]
        hi = [max(a[i], b[i]) for i in range(3)]
        return cq.Workplane("XY").add(cq.Solid.makeBox(
            hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], cq.Vector(*lo)))

    def cyl(self, dia, u, v, d0, d1):
        z0 = self.p(u, v, min(d0, d1))
        return cq.Workplane("XY").add(cq.Solid.makeCylinder(
            dia / 2.0, abs(d1 - d0), cq.Vector(*z0), cq.Vector(0, 0, self.dz)))

    def bore(self, dia, u, v, d0, d1, up):
        """A printable round hole along the joint axis: teardropped for `up`."""
        from cadkit.holes import teardrop_hole
        return teardrop_hole(dia, d1 - d0, self.p(u, v, d0), (0, 0, self.dz), up)


# Both joints put the connector on -X (v = +X), the side the old lead's spine is on
# (x -1.6), so the harness's way across to it is short; the screw goes to +X.
# TOP: the fixed tenon's upper end in the adapter. Into the tenon is -Z.
TOP = Joint("top", LS.Z_MORTISE_ROOF, 1.0, -1.0,
            LS.PRINT_UP["fixed_tenon"], LS.PRINT_UP["body_adapter"])
# BOTTOM: the adjust tenon's lower end in the pedal bar. Into the tenon is +Z. The
# bar latch's pocket across this tenon's +Y side starts at y 10.5 (probed), clear of
# everything here. The bar's wiring chamber is on -X of here, which is where the
# connector's cavity runs down into it.
BOTTOM = Joint("bottom", LS.Z_ADJ_TEN_BOT, 1.0, 1.0,
               LS.PRINT_UP["adjust_tenon"], (0.0, 1.0, 0.0))


# ── the boards, as dummies (board-local numbers, posed by a Joint) ───────────
def _array():
    for i in range(POGO_NU):
        for j in range(POGO_NV):
            yield ((i - (POGO_NU - 1) / 2.0) * POGO_PITCH,
                   ARRAY_V + (j - (POGO_NV - 1) / 2.0) * POGO_PITCH)


def _board(j, face_d, back_d, v0=BOARD_V0):
    b = j.box(-BOARD_U / 2.0, BOARD_U / 2.0, v0, BOARD_V1,
              min(face_d, back_d), max(face_d, back_d))
    return b.cut(j.cyl(HOLE_D, 0.0, SCREW_V, face_d - 1.0, back_d + 1.0)
                 if face_d < back_d else
                 j.cyl(HOLE_D, 0.0, SCREW_V, back_d - 1.0, face_d + 1.0))


def _ph(j, back_d, sign):
    """The harness connector on a board's back, mated: `sign` is the direction of
    'away from the board' in d. Body, its flat tails, and the housing in it."""
    d1 = back_d + sign * PH_H
    out = j.box(-PH_U / 2.0, PH_U / 2.0, ARRAY_V - PH_V / 2.0, ARRAY_V + PH_V / 2.0,
                min(back_d, d1), max(back_d, d1))
    dt = back_d + sign * PH_TAIL_H
    return out.union(j.box(-PH_U / 2.0 + 1.0, PH_U / 2.0 - 1.0,
                           ARRAY_V - PH_V / 2.0 - PH_TAIL, ARRAY_V - PH_V / 2.0 + 0.01,
                           min(back_d, dt), max(back_d, dt)))


def _phk(j, back_d):
    """The male's THT header on its back (+d), mated, and its posts through the board
    to the pin side (-d)."""
    out = j.box(-PHK_U / 2.0, PHK_U / 2.0, PHK_ROW_V - PHK_V / 2.0,
                PHK_ROW_V + PHK_V / 2.0, back_d, back_d + PH_H)
    face_d = back_d - PCB_T
    for i in range(4):
        u = (i - 1.5) * 2.0
        out = out.union(j.box(u - PHK_POST / 2.0, u + PHK_POST / 2.0,
                              PHK_ROW_V - PHK_POST / 2.0, PHK_ROW_V + PHK_POST / 2.0,
                              face_d - PHK_PROUD, back_d))
    return out


def male(j, compress: float = SEAT_C):
    """The leg's board, pins toward the mating plane (-d), drawn with the pins at
    `compress` (the seated SEAT_C by default; 0 = the leg off)."""
    f = MALE_FACE
    board = _board(j, f, MALE_BACK, MALE_V0)
    for i in range(4):                  # the THT header's plated holes
        board = board.cut(j.cyl(PHK_HOLE_D, (i - 1.5) * 2.0, PHK_ROW_V, f - 1.0,
                                MALE_BACK + 1.0))
    hdr = j.box(-POGO_BODY_U / 2.0, POGO_BODY_U / 2.0,
                ARRAY_V - POGO_BODY_V / 2.0, ARRAY_V + POGO_BODY_V / 2.0,
                f - POGO_BODY_TOP, f - POGO_FOOT_H)
    tip = f - (POGO_FREE - compress)
    for u, v in _array():
        hdr = hdr.union(j.cyl(POGO_BARREL_D, u, v, f - POGO_BARREL_TOP, f - POGO_BODY_TOP))
        hdr = hdr.union(j.cyl(POGO_PLUNGER_D, u, v, tip, f - POGO_BARREL_TOP))
    return [("pogo_male_board_%s" % j.name, board),
            ("pogo_male_pins_%s" % j.name, hdr),
            ("pogo_male_ph_%s" % j.name, _phk(j, MALE_BACK))]


def female(j):
    """The fixed part's board: pads up at PAD_Z, back on the pedestal."""
    board = _board(j, PAD_Z, PED_H)
    pads = None
    for u, v in _array():
        # flush with the board's face (copper sits IN the drawing's 1.6), so the
        # seated plungers touch the pads and overlap nothing
        p = j.cyl(PAD_D, u, v, PAD_Z - PAD_T, PAD_Z)
        pads = p if pads is None else pads.union(p)
    board = board.cut(pads)
    return [("pogo_female_board_%s" % j.name, board),
            ("pogo_female_pads_%s" % j.name, pads),
            ("pogo_female_ph_%s" % j.name, _ph(j, PED_H, -1.0))]


def screws(j):
    """Both boards' M4 x 6 buttons: the female's head stands on its pads' face and the
    male's on its pin face, each driven from the mortise side."""
    out = []
    for nm, face, sign in (("female", PAD_Z, -1.0), ("male", MALE_FACE, +1.0)):
        head = j.cyl(HEAD_D, 0.0, SCREW_V, face, face - sign * HEAD_H)
        shank = j.cyl(M4.screw_d, 0.0, SCREW_V, face, face + sign * SCREW_L)
        out.append(("pogo_%s_screw_%s" % (nm, j.name), head.union(shank)))
    return out


def dummies():
    out = []
    for j in (TOP, BOTTOM):
        out += male(j) + female(j) + screws(j)
    return out + harness()


# ── what the TENON gives up (the male pocket) ────────────────────────────────
POCKET_U = BOARD_U + 2 * CLR    # the board's own zone, where it is LOCATED: a CLR fit
DEEP = MALE_BACK + PH_H + BEND  # the connector's cavity floor, with the harness's turn
ROUTE_D = MALE_BACK + M4.insert_depth + INS_CLR + WALL   # 16.75: where the harness
                                # turns across to the lead's bore -- one WALL past the
                                # insert's hole, which it runs over


def tenon_negatives(j, route_xy, route_d, route_top, up=None):
    """Cut in the tenon: the board's pocket (face -> MALE_BACK), the connector's
    cavity behind it, the insert, and a way from the connector across to the lead's
    existing bore at `route_xy` (world), `route_d` wide, running on to `route_top`
    (a world z)."""
    up = up or j.tenon_up
    # the MOUTH: wide enough to swallow the female's pedestal as the joint closes...
    out = j.box(-PED_U / 2.0 - CLR, PED_U / 2.0 + CLR, min(PED_V0, MALE_V0) - CLR,
                PED_V1 + CLR, -1.0, MALE_FACE)
    # ...then the board's own zone, a CLR fit that locates it
    out = out.union(j.box(-POCKET_U / 2.0, POCKET_U / 2.0, MALE_V0 - CLR,
                          BOARD_V1 + CLR, MALE_FACE - 0.01, MALE_BACK))
    out = out.union(j.box(-PHK_U / 2.0 - CLR, PHK_U / 2.0 + CLR,
                          PHK_ROW_V - PHK_V / 2.0 - CLR, PHK_ROW_V + PHK_V / 2.0 + CLR,
                          MALE_BACK - 0.01, DEEP))
    out = out.union(insert_bore_cutter(
        M4, j.p(0.0, SCREW_V, MALE_BACK), (0, 0, j.dz), INS_CLR, overshoot=0.01,
        reason=_INS_WHY, print_up=up))
    # ...and room for the FEMALE's screw head as the pedestal comes in: the head is
    # HEAD_D wide at SCREW_V, so it stands 0.7 past the board's edge
    out = out.union(j.bore(HEAD_D + 2 * CLR, 0.0, SCREW_V, -1.0, MALE_FACE, up))
    # the harness's way over to the lead's bore: a slot from the connector's cavity to
    # the bore's axis, at the cavity's far end, then the bore itself onward
    ru, rv = j.uv(*route_xy)
    v0, v1 = sorted((PHK_ROW_V, rv))
    u0, u1 = sorted((0.0, ru))
    out = out.union(j.box(u0 - route_d / 2.0, u1 + route_d / 2.0,
                          v0 - route_d / 2.0, v1 + route_d / 2.0, ROUTE_D, DEEP))
    top_d = (route_top - j.z) * j.dz
    out = out.union(j.bore(route_d, ru, rv, ROUTE_D, top_d, up))
    return out


# ── what the FIXED part gets (the female pedestal and its cavities) ───────────
# THE PEDESTAL IS WIDER THAN THE BOARD, and has to be: the connector's cavity runs
# through it, and at the board's own outline that left 0.2 of plinth beside the
# cavity (check_thin). So it is the cavity plus a WALL all round, and the board's
# screw side. The tenon is a 24 square with 1.6 corner chamfers, not an octagon, so
# its corners have the room to swallow it.
_CAV_U = PH_U / 2.0 + CLR                       # the connector's cavity, half-width
_CAV_V0, _CAV_V1 = ARRAY_V - PH_V / 2.0 - CLR, ARRAY_V + PH_V / 2.0 + CLR
_TAIL_V0 = ARRAY_V - PH_V / 2.0 - PH_TAIL - CLR # ...and its low strip for the tails
PED_U = 2 * (_CAV_U + WALL)                     # 15.55
PED_V0 = _TAIL_V0 - WALL                        # -9.8
PED_V1 = BOARD_V1                               # 6.85
assert PED_U / 2.0 + CLR + WALL <= LS.TEN_W / 2.0, "the mouth breaks the tenon's flat"
assert -min(PED_V0, MALE_V0) + CLR + WALL <= LS.TEN_W / 2.0, (
    "the mouth breaks the tenon's flat")
F_DEEP = PED_H - PH_H - BEND    # the connector's cavity floor, into the host (d < 0)


def host_pedestal(j):
    """Unioned onto the roof/floor: a one-bead plinth the board screws down on."""
    return j.box(-PED_U / 2.0, PED_U / 2.0, PED_V0, PED_V1, -0.5, PED_H)


def _gable(j, u0, u1, v0, v1, d0, d1, up):
    """A box cavity whose ceiling is PRINTABLE: in a host that builds along world
    +Y, the cavity's +Y face (u1) is a ceiling, so it is carried up to a 45 degree
    ridge running along the joint axis. Returns box + roof."""
    assert up[1] > 0.99, "the gable assumes a +Y build"
    cav = j.box(u0, u1, v0, v1, d0, d1)
    sy = 1.0
    y_ceil = j.p(u1, 0, 0)[1]
    xs = sorted((j.p(0, v0, 0)[0], j.p(0, v1, 0)[0]))
    hw = (xs[1] - xs[0]) / 2.0
    xc = (xs[0] + xs[1]) / 2.0
    zs = sorted((j.p(0, 0, d0)[2], j.p(0, 0, d1)[2]))
    tri = (cq.Workplane("XY").workplane(offset=zs[0])
           .polyline([(xc - hw, y_ceil - sy * 0.01), (xc + hw, y_ceil - sy * 0.01),
                      (xc, y_ceil + sy * hw)]).close().extrude(zs[1] - zs[0]))
    return cav.union(tri)


def host_negatives(j, up=None, deep=F_DEEP):
    """Cut in the adapter / the bar: the connector's cavity under the pedestal and the
    insert. The caller adds the way out for the harness (it is host-specific)."""
    up = up or j.host_up
    out = _gable(j, -_CAV_U, _CAV_U, _CAV_V0, _CAV_V1, deep, PED_H + 0.01, up)
    out = out.union(j.box(-_CAV_U, _CAV_U, _TAIL_V0, _CAV_V0 + 0.01,
                          PED_H - PH_TAIL_H - CLR, PED_H + 0.01))
    out = out.union(insert_bore_cutter(
        M4, j.p(0.0, SCREW_V, PED_H), (0, 0, -j.dz), INS_CLR, overshoot=0.01,
        reason=_INS_WHY, print_up=up))
    return out


# ── the two hosts' own ways out ──────────────────────────────────────────────
CHAN_W = 4 * B                  # 3.2: the harness (HARNESS_D) with room
# the groove reaches down to the connector's cavity, so the harness turns straight
# out of the housing into it
# ...and it keeps the old lead groove's 4.8 regardless: the body tenons are fused onto
# the top face after this is cut, and their overlap refills the groove's top ~1 mm
CHAN_D = max(6 * B, LS.Z_TOP - (LS.Z_MORTISE_ROOF - F_DEEP) + 1.0)


def adapter_features(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """(pedestal, negatives) for the body adapter at the signal corner, in the
    adapter's own frame (it is built at the leg's axis and moved afterwards). The
    harness leaves the connector straight up into a groove in the top face that runs
    out the -Y face, inboard, under the instrument -- the old lead's exit, which the
    chassis closes over."""
    j = TOP
    neg = host_negatives(j)
    xc = j.p(0, ARRAY_V, 0)[0]
    y_in = j.p(0, 0, 0)[1] + CHAN_W             # past the cavity's middle, so the
                                                # harness's turn up into it is inside
    y_out = j.y - LS.LEG_W / 2.0 - 1.0
    neg = neg.union(cq.Workplane("XY").add(cq.Solid.makeBox(
        CHAN_W, y_in - y_out, CHAN_D + 1.0,
        cq.Vector(xc - CHAN_W / 2.0, y_out, LS.Z_TOP - CHAN_D))))
    return host_pedestal(j), neg


def bar_features(floor_z: float, chamber_top_z: float):
    """(pedestal, negatives) for the pedal bar, in the BAR's frame: `floor_z` is its
    mortise floor there. The connector's cavity runs on down into the wiring chamber,
    whose -Y wall it overlaps, so the harness drops straight in."""
    j = Joint("bottom_bar", floor_z, BOTTOM.vx, BOTTOM.dz,
              BOTTOM.tenon_up, BOTTOM.host_up)
    neg = host_negatives(j, deep=chamber_top_z - floor_z - 0.01)
    return host_pedestal(j), neg


# ── the harness, drawn ───────────────────────────────────────────────────────
def _coil(cx, cy, z_top, z_bot, turns, r, d):
    """The leg's slack as a helix of `turns` whole turns about (cx, cy)."""
    path = cq.Wire.makeHelix((z_top - z_bot) / turns, z_top - z_bot, r,
                             cq.Vector(cx, cy, z_bot), cq.Vector(0, 0, 1))
    start = path.startPoint()
    prof = cq.Wire.makeCircle(d / 2.0, start, path.tangentAt(0.0))
    return cq.Workplane("XY").add(cq.Solid.sweep(prof, [], path, isFrenet=True))


def harness():
    """THE RUN, drawn: male housing to male housing down the whole leg -- over to the
    old lead's bore, down the fixed tenon, COILED through the gap between the tenons
    (src.coil_mandrel's coil, at the span the leg is drawn at), into the adjust
    tenon's channel past the ladder, the jog, and back over to the bottom board -- plus
    the two female stubs, as far as each host's own way out."""
    from . import leg_trrs as LTR
    from . import bar_trrs as BT
    from . import coil_mandrel as CM
    from .leg_trrs import _run
    d = HARNESS_D
    dm = MALE_BACK + PH_H + BEND / 2.0      # the turn, clear of the housing's top
    assert dm - d / 2.0 > MALE_BACK + PH_H and dm + d / 2.0 < DEEP, "the turn is off"
    top_h, bot_h = TOP.p(0.0, PHK_ROW_V, MALE_BACK + PH_H), BOTTOM.p(0.0, PHK_ROW_V,
                                                                      MALE_BACK + PH_H)
    xs, ys = LTR._ax()
    xb, yb = BT._ax()
    xc, yc = LS.LEG_X + BT.CH_X, LS.LEG_Y + BT.CH_Y
    z_a, z_b = LS.Z_FIX_TEN_BOT - 8.0, LS.Z_ADJ_TEN_TOP + 8.0
    span = z_a - z_b
    pitch = span / CM.TURNS
    r = math.sqrt(max((CM.COIL_LEN / CM.TURNS) ** 2 - pitch ** 2, 0.0)) / math.pi / 2.0
    ax, ay = LS.LEG_X, LS.LEG_Y
    upper = _run([top_h, TOP.p(0.0, PHK_ROW_V, dm), (xs, ys, TOP.p(0, 0, dm)[2]),
                  (xs, ys, LS.Z_FIX_TEN_BOT - 2.0), (ax + r, ay, z_a)], d)
    lower = _run([(ax + r, ay, z_b), (xc, yc, LS.Z_ADJ_TEN_TOP + 2.0),
                  (xc, yc, BT.PASS_TOP), (xb, yb, BT.CH_BOT),
                  (xb, yb, BOTTOM.p(0, 0, dm)[2]), BOTTOM.p(0.0, PHK_ROW_V, dm), bot_h], d)
    coil = _coil(ax, ay, z_a, z_b, CM.TURNS, r, d)
    leg = upper.union(coil).union(lower)
    # the body adapter's female: up out of the housing into the groove, out -Y
    f0 = TOP.p(0.0, ARRAY_V, PED_H - PH_H)
    zc = LS.Z_TOP - CHAN_D + d / 2.0 + 0.2     # lying in the groove's bottom
    y_out = LS.LEG_Y - LS.LEG_W / 2.0
    body = _run([f0, (f0[0], LS.LEG_Y, zc), (f0[0], y_out, zc),
                 (f0[0], y_out - 12.0, zc)], d)
    # the bar's female: down out of the housing into the wiring chamber, toward the trough
    g0 = BOTTOM.p(0.0, ARRAY_V, PED_H - PH_H)
    g1 = BOTTOM.p(0.0, ARRAY_V, -17.0)
    bar = _run([g0, g1, (g1[0] + 20.0, g1[1], g1[2])], d)
    return [("pogo_harness_leg", leg), ("pogo_harness_body", body),
            ("pogo_harness_bar", bar)]
