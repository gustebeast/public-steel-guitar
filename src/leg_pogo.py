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
ONE top-entry SMT JST PH header on its back for the crimped leg harness -- the only
wiring through the leg now. There is no jack, plug, coil, float spring, TPU throat,
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
BOARD_U = 13.0                  # u: the connector (12.0 with its nails) + edge
BOARD_V = 13.4                  # v: the header, then the screw head beside it
EDGE = 0.76                     # component to routed edge (JLCPCB wants 0.5)
ARRAY_V = -BOARD_V / 2.0 + EDGE + POGO_BODY_V / 2.0     # -3.40 the pin/pad array
SCREW_V = 3.9                   # the M4 -- see the walls below
HOLE_D = 4.5                    # M4 clearance through the board (elec convention)
HEAD_D = 7.0                    # button head, as elec/trrs_adapter: the head, not the
HEAD_H = 2.2                    #   hole, is what sets the spacing
SCREW_L = 6.0                   # M4 x 6 button: board + 4.4 into the insert
assert SCREW_V - HEAD_D / 2.0 >= ARRAY_V + POGO_BODY_V / 2.0 + 0.3, (
    "the screw head lands on the pin header")
assert BOARD_V / 2.0 - SCREW_V - HOLE_D / 2.0 >= 0.5, "the M4 hole is off the board"

# JST PH, SMT TOP ENTRY (B4B-PH-SM4-TB), under the array on the BACK. SMT so it has
# no tails through to the pin side; top entry so the harness leaves straight up the
# tenon's bore. ⚠ RESERVED ENVELOPE: its body is from JST's PH series table, the
# mated height is XH's 9.8 (PH is the smaller series) -- read the drawing and tighten.
PH_U = 12.0                     # body incl. its solder nails
PH_V = 4.5
PH_H = 9.8                      # mated, RESERVED
PH_LCSC = None                  # bronner to pick (C265121 is the 8-way side entry)

CLR = 0.3                       # board / connector clearance in its printed pocket
WALL = D.MIN_WALL_2P

# the insert has to keep a wall to the connector's cavity beside it
_INS_R = M4.insert_pilot_d / 2.0
assert (SCREW_V - _INS_R) - (ARRAY_V + PH_V / 2.0 + CLR) >= WALL - 1e-9, (
    "only %.2f between the insert and the connector's cavity"
    % ((SCREW_V - _INS_R) - (ARRAY_V + PH_V / 2.0 + CLR)))
INS_CLR = 0.4                   # screw-tip clearance past the insert
_INS_WHY = ("a PCB's one M4 (project rule): an M4 x 6 through 1.6 of board ends inside "
            "the insert, and there is no depth behind it for a self-tap bite -- the "
            "pin travel and the connector own the rest of the stack")
assert SCREW_L - PCB_T <= M4.insert_depth + INS_CLR, "the screw bottoms out"


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


def _board(j, face_d, back_d):
    b = j.box(-BOARD_U / 2.0, BOARD_U / 2.0, -BOARD_V / 2.0, BOARD_V / 2.0,
              min(face_d, back_d), max(face_d, back_d))
    return b.cut(j.cyl(HOLE_D, 0.0, SCREW_V, face_d - 1.0, back_d + 1.0)
                 if face_d < back_d else
                 j.cyl(HOLE_D, 0.0, SCREW_V, back_d - 1.0, face_d + 1.0))


def _ph(j, back_d, sign):
    """The harness connector on a board's back, mated: `sign` is the direction of
    'away from the board' in d."""
    d1 = back_d + sign * PH_H
    return j.box(-PH_U / 2.0, PH_U / 2.0, ARRAY_V - PH_V / 2.0, ARRAY_V + PH_V / 2.0,
                 min(back_d, d1), max(back_d, d1))


def male(j, compress: float = SEAT_C):
    """The leg's board, pins toward the mating plane (-d), drawn with the pins at
    `compress` (the seated SEAT_C by default; 0 = the leg off)."""
    f = MALE_FACE
    board = _board(j, f, MALE_BACK)
    hdr = j.box(-POGO_BODY_U / 2.0, POGO_BODY_U / 2.0,
                ARRAY_V - POGO_BODY_V / 2.0, ARRAY_V + POGO_BODY_V / 2.0,
                f - POGO_BODY_TOP, f - POGO_FOOT_H)
    tip = f - (POGO_FREE - compress)
    for u, v in _array():
        hdr = hdr.union(j.cyl(POGO_BARREL_D, u, v, f - POGO_BARREL_TOP, f - POGO_BODY_TOP))
        hdr = hdr.union(j.cyl(POGO_PLUNGER_D, u, v, tip, f - POGO_BARREL_TOP))
    return [("pogo_male_board_%s" % j.name, board),
            ("pogo_male_pins_%s" % j.name, hdr),
            ("pogo_male_ph_%s" % j.name, _ph(j, MALE_BACK, +1.0))]


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
    return out


# ── what the TENON gives up (the male pocket) ────────────────────────────────
POCKET_U = BOARD_U + 2 * CLR    # the board's own zone, where it is LOCATED: a CLR fit
POCKET_V = BOARD_V + 2 * CLR
DEEP = MALE_BACK + PH_H + CLR   # the connector's cavity floor
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
    out = j.box(-PED_U / 2.0 - CLR, PED_U / 2.0 + CLR, PED_V0 - CLR, PED_V1 + CLR,
                -1.0, MALE_FACE)
    # ...then the board's own zone, a CLR fit that locates it
    out = out.union(j.box(-POCKET_U / 2.0, POCKET_U / 2.0, -POCKET_V / 2.0,
                          POCKET_V / 2.0, MALE_FACE - 0.01, MALE_BACK))
    out = out.union(j.box(-PH_U / 2.0 - CLR, PH_U / 2.0 + CLR,
                          ARRAY_V - PH_V / 2.0 - CLR, ARRAY_V + PH_V / 2.0 + CLR,
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
    v0, v1 = sorted((ARRAY_V, rv))
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
PED_U = 2 * (_CAV_U + WALL)                     # 15.8
PED_V0 = _CAV_V0 - WALL                         # -7.55
PED_V1 = BOARD_V / 2.0                          # 6.70
assert PED_U / 2.0 + CLR + WALL <= LS.TEN_W / 2.0, "the mouth breaks the tenon's flat"
assert -PED_V0 + CLR + WALL <= LS.TEN_W / 2.0, "the mouth breaks the tenon's flat"
F_DEEP = PED_H - PH_H - CLR     # the connector's cavity floor, into the host (d < 0)


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
    out = out.union(insert_bore_cutter(
        M4, j.p(0.0, SCREW_V, PED_H), (0, 0, -j.dz), INS_CLR, overshoot=0.01,
        reason=_INS_WHY, print_up=up))
    return out


# ── the two hosts' own ways out ──────────────────────────────────────────────
CHAN_W = 4 * B                  # 3.2: four 28 AWG leads side by side, loose
CHAN_D = 4.8                    # the old lead groove's depth


def adapter_features(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """(pedestal, negatives) for the body adapter at the signal corner, in the
    adapter's own frame (it is built at the leg's axis and moved afterwards). The
    harness leaves the connector straight up into a groove in the top face that runs
    out the -Y face, inboard, under the instrument -- the old lead's exit, which the
    chassis closes over."""
    j = TOP
    neg = host_negatives(j)
    xc = j.p(0, ARRAY_V, 0)[0]
    y_in = j.p(0, 0, 0)[1]                      # into the cavity's middle
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
