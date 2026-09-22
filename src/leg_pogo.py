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
    floor (bar): a GOLD 1 x 4 target (Xinyangze YZ185115035T-04025-01, LCSC C54930022)
    and a side-entry JST ZR (S4B-ZR-SM4A-TF) on the SAME face, the harness dropping
    through a slot in the host right past the plug. The contacts are the target's own
    3 u" gold, not the board's finish -- so the panel stays on HASL (ENIG for the
    whole panel was ~$17-33 an order on a single small board, and scales with area).

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
mortise's roof or floor when seated). The male board's BACK is at t = 0 and everything
on it lies at t > 0.

t RUNS ALONG A DIAGONAL, and that is not a detail: THE TENON IS A SQUARE TURNED 45
DEGREES. It reaches 16.17 along X and Y -- those are its APEXES, trimmed by a 1.6
chamfer -- and its FLATS face the diagonals, 12 from the axis. The male board's screw
has to cross the board square and come out at a flat, so the board's face normal is a
diagonal. Built on X and Y instead, the head's recess ended 0.8 SHORT of the surface,
buried in solid material (check_thin found it as a 1.39 web).

DIMENSIONS ARE THE DRAWINGS' (C54799748 YZ165615055F-04025-02; JST ePH pp.3-4, read
as images) except where marked INFERRED or RESERVED. This is CAD for bronner to route
from, not a routed board.
"""

from __future__ import annotations

import math

import cadquery as cq

from cadkit.fasteners import M4, M4_BUTTON_HEAD_D, M4_BUTTON_HEAD_H, ScrewJoint
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

# ── the female's contacts: a vertical gold target, LCSC C54930022 ────────────
TG_N = 4
TG_PITCH = 2.54                 # NOT the header's 2.5: centred, the end contacts land
                                # 0.06 off -- counted in the landing budget below
TG_BODY_S = 10.2                # housing along the row
TG_BODY_T = 2.5                 # ...across it
TG_BODY_H = 2.5                 # ...off the board
TG_FACE_H = 3.5                 # the contact faces above the board
TG_FACE_D = 1.2                 # each contact's face
TG_PAD_D = 2.2                  # its SMT pads (drawing's layout)
TG_LCSC = "C54930022"           # YZ185115035T-04025-01, 3 u" Au, 210 in stock
MISALIGN = 0.45                 # where a plunger may land off its contact's centre: the
                                # octagon's 0.3 fit plus the two boards' pocket fits
_PITCH_ERR = (TG_N - 1) / 2.0 * abs(TG_PITCH - RA_PITCH)            # 0.06
# a DOMED plunger touches at its centre, so the rule is landing error < face radius
assert MISALIGN + _PITCH_ERR < TG_FACE_D / 2.0, (
    "a plunger landing %.2f off centre misses a O%.1f contact"
    % (MISALIGN + _PITCH_ERR, TG_FACE_D))

# ── the chain, up from the mating plane ──────────────────────────────────────
SEAT_C = 1.0                    # compression with the joint seated: 1.0 of the 1.5
LOAD_SLOP = 0.25                # the bottom joint hangs this far open on its latch
                                # (bar_latch: the tenon's pocket floor is CLR below the
                                # hook); the top one is pressed shut by the body
PRINT_TOL = 0.30                # and the pocket depths are prints
assert SEAT_C - LOAD_SLOP - PRINT_TOL >= 0.4, "the pins barely touch when loaded"
assert SEAT_C + PRINT_TOL <= RA_FREE - RA_WORK, "the pins pass their working height"
PAD_Z = PCB_T + TG_FACE_H       # 5.1 the contact faces (the female lies ON the host)
REAR = PAD_Z + RA_FREE - SEAT_C     # 9.6 the header's rear, seated
EDGE_D = REAR - RA_BODY_D           # 7.1 the male board's lower edge
TIP_REST = REAR - RA_FREE           # 4.1 -- the free tips, INSIDE the tenon's face
assert TIP_REST >= 0.5, "the free pin tips stand too near the tenon's face"

# ── the male board, standing on edge ─────────────────────────────────────────
CLR = 0.3                       # board / connector clearance in its printed pocket
WALL = D.MIN_WALL_2P
EDGE = 0.5                      # component to routed edge (JLCPCB's rule)
MB_S = 13.0                     # along the row: the side-entry PH's 11.9 + edges
TB = 0.0                        # the board's back...
TF = TB + PCB_T                 # ...and its component face
PIN_T = TF + RA_PIN_T           # 2.9 the plungers' line, and so the contacts'
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
DEEP = PLUG_TOP + BEND          # the pocket's end
assert TF + SE_H + CLR + WALL <= LS.TEN_W / 2.0, "the connector breaks the tenon's flat"
assert TB - CLR - WALL >= -LS.TEN_W / 2.0, "the board breaks the tenon's flat"

# ── the leg's harness ────────────────────────────────────────────────────────
# TWO TWISTED PAIRS of 28 AWG PVC hookup wire -- CAN_H/CAN_L one pair, 5V/GND the
# other -- crimped into PHR-4 housings at both ends AFTER threading. A round 4-core
# was rejected: the datasheeted ones that fit are too fat (Alpha 86004 is O4.83) and
# none pairs CAN_H with CAN_L. PVC hookup takes a heat-set coil on src.coil_mandrel.
HARNESS_WIRE_OD = 0.9           # 28 AWG 7/36 PVC hookup (Alpha 3048-class)
HARNESS_D = 3 * B               # 2.4: four 0.9 wires bundle to 0.9 (1 + sqrt2) = 2.17
HARNESS_BEND_STATIC = 3.0 * HARNESS_D   # 7.2 -- set once, no foil, no jacket
assert HARNESS_D >= HARNESS_WIRE_OD * (1 + math.sqrt(2)), "the bundle is under-sized"


# ── the female board, flat on the host face ──────────────────────────────────
# EVERY PART ON ITS FACE, like the male's: the target, and beside it (-t) a SIDE-ENTRY
# JST ZR, S4B-ZR-SM4A-TF (eZR p.5 SM4 type): 4 way B 9.0, body 5.0 deep with its tails
# (1.5) behind, 3.7 off the board. ZR's own sockets are IDC; its header also takes the
# ZH CRIMP housing (ZHR-4 + SZH-002T, eZR p.1), which is how this harness is made.
ZR_S = 9.0
ZR_DEPTH = 5.0
ZR_TAIL = 1.5
ZR_H = 3.7
ZR_PLUG = 2.0                   # the mated housing past the mouth (eZR p.2: 7 overall
                                # back of header to plug, less the 5.0 body)
ZR_LCSC = "C485354"             # S4B-ZR-SM4A-TF(LF)(SN), 27k in stock
HEAD_D = M4_BUTTON_HEAD_D       # 7.6 -- cadkit's ISO 7380 button, the head (not the
HEAD_H = M4_BUTTON_HEAD_H       # hole) is what sets every spacing here
_INS_R = M4.insert_pilot_d / 2.0
TG_T0 = PIN_T - TG_BODY_T / 2.0                         # 1.65 the target's -t side
ZR_T1 = TG_T0 - EDGE                                    # 1.15 the ZR's back (tails)
ZR_MOUTH = ZR_T1 - ZR_TAIL - ZR_DEPTH                   # -5.35 its mouth, facing -t
WIRE_T0 = ZR_MOUTH - ZR_PLUG - HARNESS_D                # -9.75 the harness drops here
# the M4 sits BEYOND the end of the target along the row -- nothing on the -t side has
# room for its head, and the +t side is the tenon's wall
F_HOLE_S = TG_BODY_S / 2.0 + CLR + HEAD_D / 2.0         # 8.9 from the row's centre
F_HOLE_T = PIN_T
FB_T0 = ZR_MOUTH                                        # the plug overhangs this edge
FB_T1 = PIN_T + TG_BODY_T / 2.0 + EDGE                  # 4.65
FB_S0 = -TG_BODY_S / 2.0 - EDGE                         # along the row, from its centre
FB_S1 = F_HOLE_S + HOLE_D / 2.0 + EDGE
F_SCREW_L = 8.0                 # M4 x 8 button: 1.6 of board, then 6.4 of insert bite
F_END = F_SCREW_L + 1.0          # the hole stops past the screw's tip
assert ZR_S / 2.0 <= TG_BODY_S / 2.0 + EDGE, "the ZR runs past the target's end"
assert PCB_T + ZR_H < EDGE_D and PCB_T + HEAD_H < EDGE_D, (
    "the female's parts reach the male board's edge")

# THE ROW IS OFF CENTRE by S_C, so the female's screw fits beyond the target's end;
# the male board shifts with it (Joint.p applies it)
S_C = -3.0
_HALF = LS.TEN_W / 2.0
assert S_C + F_HOLE_S + HEAD_D / 2.0 + CLR + WALL <= _HALF, "the female's head breaks a flat"
assert S_C + FB_S0 - CLR - WALL >= -_HALF, "the female breaks a flat"
assert S_C - MB_S / 2.0 - CLR - WALL >= -_HALF, "the male board breaks a flat"
assert WIRE_T0 - CLR - WALL >= -_HALF, "the harness's drop breaks the tenon's flat"
assert FB_T1 + CLR + WALL <= _HALF, "the female breaks the tenon's +t flat"

# the male's sideways screw: head recessed in the +t flat, insert pressed into the -t
# flat from outside -- the -t side is where nothing else is, at this height
M_SCREW_L = 20.0                # M4 x 20 button
M_RECESS = HEAD_H + 0.8         # buried in the flat, so the mortise never touches it
M_INSERT_AT = LS.TEN_W - M4.insert_depth        # the pocket's mouth, faceing the screw
M_END = LS.TEN_W + 0.5
M_HOLE_S = -S_C                 # ON THE LEG'S CENTRE LINE, not the row's: 3.5 off it the
                                # head's edge met the mortise's corner faces (the gate
                                # found 1.1 mm3 in each host)
assert abs(M_HOLE_S) + HOLE_D / 2.0 + EDGE <= MB_S / 2.0, "the M4 hole leaves the board"
M_HEAD_SEAT = _HALF - M_RECESS                          # the counterbore's floor, in t


def male_screw(j):
    """The sideways M4 through the tenon and the board: head in the +t flat, insert
    pressed into the -t flat from outside. cadkit shapes the whole hole per part."""
    return ScrewJoint(M4, j.p(_HALF, M_HOLE_S, M_HOLE_D), (-j.T[0], -j.T[1], 0.0),
                      M_SCREW_L, insert_at=M_INSERT_AT, end_at=M_END,
                      head_d=HEAD_D, head_h=HEAD_H, recess=M_RECESS)


def female_screw(j):
    """The female's M4, down the mortise: head on its board, insert in the host."""
    return ScrewJoint(M4, j.p(F_HOLE_T, F_HOLE_S, PCB_T), (0.0, 0.0, -j.dz),
                      F_SCREW_L, insert_at=PCB_T, end_at=F_END,
                      head_d=HEAD_D, head_h=HEAD_H)

# ── the two joints ───────────────────────────────────────────────────────────
class Joint(object):
    """A joint's mating plane and axes: `T` and `S` are world unit vectors (axis
    aligned) for t and s, `dz` is +-1, world Z of 'into the tenon'."""

    def __init__(self, name, z, dz, T, tenon_up, host_up):
        self.name, self.z, self.dz, self.T = name, z, dz, T
        self.S = (-T[1], T[0])          # s is t turned +90 about the joint's axis
        self.ang = math.degrees(math.atan2(T[1], T[0]))
        self.tenon_up, self.host_up = tenon_up, host_up
        # which s face of a cavity in the TENON is its ceiling: the one the part builds
        # toward (the tenon lies on a flat, so its build direction is +-S)
        self.up_s = 1.0 if (self.S[0] * tenon_up[0] + self.S[1] * tenon_up[1]) > 0 else -1.0
        self.x, self.y = LS.LEG_X, LS.LEG_Y

    def p(self, t, s, d):
        """Local -> world. s is measured from the ROW's centre, which sits S_C along
        the row from the leg's axis."""
        s = s + S_C
        return (self.x + t * self.T[0] + s * self.S[0],
                self.y + t * self.T[1] + s * self.S[1], self.z + self.dz * d)

    def box(self, t0, t1, s0, s1, d0, d1):
        """A box in LOCAL axes -- turned onto this joint's diagonal, not world-aligned."""
        # d is INTO the tenon, which is -Z at the top joint: take the lower world z,
        # not the lower d, or every cavity up there comes out mirrored about the seam
        z0 = min(self.z + self.dz * d0, self.z + self.dz * d1)
        b = cq.Workplane("XY").add(cq.Solid.makeBox(
            t1 - t0, s1 - s0, abs(d1 - d0), cq.Vector(t0, s0 + S_C, 0.0)))
        return (b.rotate((0, 0, 0), (0, 0, 1), self.ang)
                .translate((self.x, self.y, z0)))

    def house(self, t0, t1, s0, s1, d0, d1):
        """A cavity shaped like a HOUSE: the box, with a 45 degree gable standing on
        whichever s face the tenon builds toward, because that face is its CEILING.
        ONE closed profile, extruded along d -- not a box with a triangle unioned onto
        it. (It was that union: the gable's face was computed as -s1 rather than s0, so
        on a joint that builds toward -S the roof came out as a SEPARATE triangle
        floating beside the slot.)"""
        u = self.up_s
        sc = s1 if u > 0 else s0                # the ceiling face
        sf = s0 if u > 0 else s1                # and the floor opposite it
        hw = (t1 - t0) / 2.0                    # 45 degrees, so the ridge is half-span
        tm = (t0 + t1) / 2.0
        apex = sc + u * hw
        z0, z1 = sorted((self.z + self.dz * d0, self.z + self.dz * d1))
        pts = [(t0, sf + S_C), (t1, sf + S_C), (t1, sc + S_C)]
        s_flat = u * (LS.TEN_W / 2.0) - S_C     # the tenon's flat on the ceiling side
        if (apex - s_flat) * u > 0:
            # THE RIDGE DOES NOT FIT. The mouth is 10.6 wide and its ceiling sits 2.75
            # inside the flat, so a 45 degree ridge (5.3) runs out through the tenon's
            # face -- unavoidable, and harmless: assembled, this is 34 of the 40 of
            # engagement deep inside the mortise, walled in and closed at its far end.
            # What is NOT harmless is letting the 45 flanks themselves cross the flat:
            # they leave a wedge of material tapering to ZERO along the crossing, which
            # prints as a curled burr ON A SLIDING FACE. So the flanks stop one bead
            # short and go STRAIGHT out instead -- they run along the build direction
            # there, which prints fine -- and the slot breaks out square-edged.
            s_br = s_flat - u * D.MIN_WALL
            half = hw - abs(s_br - sc)
            assert half > 0.0, "the cavity's ceiling is already outside the flat"
            s_out = s_flat + u * 1.0
            pts += [(tm + half, s_br + S_C), (tm + half, s_out + S_C),
                    (tm - half, s_out + S_C), (tm - half, s_br + S_C)]
        else:
            pts += [(tm, apex + S_C)]
        pts += [(t0, sc + S_C)]
        return (cq.Workplane("XY").workplane(offset=z0)
                .polyline(pts).close().extrude(z1 - z0)
                .rotate((0, 0, 0), (0, 0, 1), self.ang)
                .translate((self.x, self.y, 0.0)))

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

    def targets(self):
        for k in range(TG_N):
            yield (k - (TG_N - 1) / 2.0) * TG_PITCH


# BOTH JOINTS put t on the -X+Y diagonal, so the board's parts and the ZR's mouth face
# +X-Y: at the bottom that points the harness's drop at the bar's trough (user), and at
# the top it puts everything clear of the leg latch's pocket (y < -1.6 from 27.75 down).
# The tenon builds along -S here, so every cavity's s0 face is its ceiling: house()
# stands a 45 degree gable on it, in the SAME profile as the cavity.
_D = math.sqrt(0.5)
TOP = Joint("top", LS.Z_MORTISE_ROOF, -1.0, (-_D, _D),
            LS.PRINT_UP["fixed_tenon"], LS.PRINT_UP["body_adapter"])
# BOTTOM: the adjust tenon's lower end, in the pedal bar. Into the tenon is +Z.
BOTTOM = Joint("bottom", LS.Z_ADJ_TEN_BOT, 1.0, (-_D, _D),
               LS.PRINT_UP["adjust_tenon"], (0.0, 1.0, 0.0))


# ── the boards, as dummies ───────────────────────────────────────────────────
def male(j, compress: float = SEAT_C):
    """The leg's board on edge, pins down the joint axis at `compress` (SEAT_C is the
    seated state; 0 is the leg off)."""
    board = j.box(TB, TF, -MB_S / 2.0, MB_S / 2.0, EDGE_D, MB_TOP)
    board = board.cut(j.cyl_t(HOLE_D, TB - 1.0, TF + 1.0, M_HOLE_S, M_HOLE_D))
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
    """The fixed part's board: on the host face, the gold target and the ZR side by
    side on its face."""
    board = j.box(FB_T0, FB_T1, FB_S0, FB_S1, 0.0, PCB_T)
    board = board.cut(j.cyl_d(HOLE_D, F_HOLE_T, F_HOLE_S, -1.0, PCB_T + 1.0))
    tg = j.box(TG_T0, TG_T0 + TG_BODY_T, -TG_BODY_S / 2.0, TG_BODY_S / 2.0,
               PCB_T, PCB_T + TG_BODY_H)
    for s in j.targets():
        tg = tg.union(j.cyl_d(TG_FACE_D, PIN_T, s, PCB_T + TG_BODY_H - 0.01, PAD_Z))
    zr = j.box(ZR_MOUTH, ZR_MOUTH + ZR_DEPTH, -ZR_S / 2.0, ZR_S / 2.0, PCB_T,
               PCB_T + ZR_H)
    zr = zr.union(j.box(ZR_MOUTH + ZR_DEPTH - 0.01, ZR_T1, -ZR_S / 2.0 + 1.0,
                        ZR_S / 2.0 - 1.0, PCB_T, PCB_T + 0.5))
    zr = zr.union(j.box(ZR_MOUTH - ZR_PLUG, ZR_MOUTH + 0.01, -ZR_S / 2.0 + 0.75,
                        ZR_S / 2.0 - 0.75, PCB_T + 0.3, PCB_T + ZR_H - 0.3))
    return [("pogo_female_board_%s" % j.name, board),
            ("pogo_female_pads_%s" % j.name, tg),
            ("pogo_female_ph_%s" % j.name, zr)]


def screws(j):
    """Both M4s and their inserts, drawn by cadkit from the same joints the parts cut."""
    return (female_screw(j).dummies("pogo_female_screw_%s" % j.name,
                                    "pogo_female_insert_%s" % j.name)
            + male_screw(j).dummies("pogo_male_screw_%s" % j.name,
                                    "pogo_male_insert_%s" % j.name))


def dummies():
    out = []
    for j in (TOP, BOTTOM):
        out += male(j) + female(j) + screws(j)
    return out + harness()


# ── what the TENON gives up ──────────────────────────────────────────────────
MOUTH_D = PCB_T + max(TG_FACE_H, ZR_H, HEAD_H) + CLR    # the female's parts come in
                                                        # this far


def tenon_negatives(j, route_xy, route_d, route_top, up=None):
    """Cut in the tenon: the MOUTH that swallows the female board and its screw head,
    the SLOT the male board slides up (a CLR fit that locates it in t and s), the
    header's and the connector's room on its face, the plug and the harness's turn,
    the sideways screw (counterbore in the +t flat, insert from the -t flat), and a way
    over to the lead's bore at `route_xy` (world), `route_d` wide, on to `route_top`."""
    up = up or j.tenon_up
    out = j.house(FB_T0 - CLR, FB_T1 + CLR, FB_S0 - CLR, FB_S1 + CLR, -1.0, MOUTH_D)
    # ...its screw head, which overhangs the board's end, and the ZR's plug and the
    # harness's drop, which overhang its -t edge
    out = out.union(j.bore_d(HEAD_D + 2 * CLR, F_HOLE_T, F_HOLE_S, -1.0, MOUTH_D, up))
    out = out.union(j.house(WIRE_T0 - CLR, FB_T0 + 0.01, -ZR_S / 2.0 - CLR,
                            ZR_S / 2.0 + CLR, -1.0, MOUTH_D))
    out = out.union(j.house(TB - CLR, TF + 0.01, -MB_S / 2.0 - CLR, MB_S / 2.0 + CLR,
                            -1.0, MB_TOP + CLR))
    out = out.union(j.house(TF, TF + RA_BODY_T + CLR, -RA_BODY_S / 2.0 - CLR,
                            RA_BODY_S / 2.0 + CLR, -1.0, REAR + CLR))
    out = out.union(j.house(TF, TF + SE_H + CLR, -SE_S / 2.0 - CLR, SE_S / 2.0 + CLR,
                            SE_TAIL0 - CLR, PLUG_TOP + CLR))
    # the harness's turn over to the lead's bore, then the bore itself onward
    rx, ry = route_xy
    rt = (rx - j.x) * j.T[0] + (ry - j.y) * j.T[1]
    rs = (rx - j.x) * j.S[0] + (ry - j.y) * j.S[1] - S_C
    pt = TF + SE_H / 2.0
    t0, t1 = sorted((pt, rt))
    s0, s1 = sorted((0.0, rs))
    out = out.union(j.box(t0 - route_d / 2.0, t1 + route_d / 2.0,
                          s0 - route_d / 2.0, s1 + route_d / 2.0, PLUG_TOP, DEEP))
    top_d = (route_top - j.z) * j.dz
    out = out.union(j.bore_d(route_d, rt, rs, DEEP - route_d, top_d, up))
    return out.union(male_screw(j).cutter(up))


# ── what the FIXED part gives up (the female's insert and the harness's slot) ─
F_DEEP = -(LS.Z_TOP - LS.Z_MORTISE_ROOF - 6 * B + B)    # the slot's floor in the
                                                        # ADAPTER: into its top groove


def _gable(j, t0, t1, s0, s1, d0, d1, up):
    """A box cavity whose ceiling is PRINTABLE in a host that builds along world +Y.
    The joint sits on the tenon's DIAGONAL, so in the host's frame the cavity is a
    rectangle turned 45 degrees: its two upper edges already rise at 45 degrees and
    meet in a point, which is self-supporting, and it needs no roof at all.

    It used to get one anyway, off the cavity's BOUNDING BOX -- and once the joint was
    rotated onto the diagonal that box was the diamond's AABB, so the roof came out as
    a wide axis-aligned triangle floating clear of the slot (two cutouts in section,
    not one)."""
    assert up[1] > 0.99, "the gable assumes a +Y build"
    assert abs((j.ang % 90.0) - 45.0) < 1e-6, (
        "the cavity is no longer on the diagonal, so its ceiling is flat again and "
        "this owes it a real gable")
    return j.box(t0, t1, s0, s1, d0, d1)


def host_negatives(j, up=None, deep=F_DEEP):
    """Cut in the adapter / the bar: the female's insert, and the SLOT the harness
    drops through past the ZR's plug (gabled -- both hosts build +Y). The caller adds
    whatever the slot runs on into."""
    up = up or j.host_up
    out = _gable(j, WIRE_T0 - CLR, ZR_MOUTH - ZR_PLUG + CLR, -ZR_S / 2.0 - CLR,
                 ZR_S / 2.0 + CLR, deep, 0.01, up)
    return out.union(female_screw(j).cutter(up))


CHAN_W = 4 * B                  # 3.2: the harness with room
CHAN_D = 6 * B                  # 4.8 -- the body tenons are fused on after this is cut
                                # and refill the groove's top ~1 mm


def adapter_features(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """(None, negatives) for the body adapter at the signal corner, in its own frame.
    The harness rises out of the female's connector into a groove in the top face that
    runs out the -Y face, inboard, under the instrument (the old lead's exit)."""
    j = TOP
    neg = host_negatives(j)
    fc = j.p((WIRE_T0 + ZR_MOUTH - ZR_PLUG) / 2.0, 0.0, 0.0)
    y_out = j.y - LS.LEG_W / 2.0 - 1.0
    y_in = fc[1] + CHAN_W
    neg = neg.union(cq.Workplane("XY").add(cq.Solid.makeBox(
        CHAN_W, y_in - y_out, CHAN_D + 1.0,
        cq.Vector(fc[0] - CHAN_W / 2.0, y_out, LS.Z_TOP - CHAN_D))))
    return None, neg


def bar_features(floor_z: float, chamber_top_z: float):
    """(None, negatives) for the pedal bar, in the BAR's frame: the connector's cavity
    runs on down into the wiring chamber, which it overlaps."""
    j = Joint("bottom_bar", floor_z, BOTTOM.dz, BOTTOM.T, BOTTOM.tenon_up,
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
    fr = ZR_MOUTH - ZR_PLUG - d / 2.0 - 0.1         # running past the plug, clear of it
    fc = fr                                          # ...and it drops there
    zd = PCB_T + ZR_H / 2.0                         # the plug's height off the host
    f0 = TOP.p(ZR_MOUTH - ZR_PLUG - 0.1, 0.0, zd)     # just off the plug's end
    zc = LS.Z_TOP - CHAN_D + d / 2.0 + 0.2          # lying in the groove's bottom
    y_out = LS.LEG_Y - LS.LEG_W / 2.0
    f1 = TOP.p(fr, 0.0, zd)
    body = _run([f0, f1, (f1[0], f1[1], zc), (f1[0], y_out, zc),
                 (f1[0], y_out - 12.0, zc)], d)
    g0 = BOTTOM.p(ZR_MOUTH - ZR_PLUG - 0.1, 0.0, zd)
    g0b = BOTTOM.p(fr, 0.0, zd)                    # clear of the plug first...
    g1a = BOTTOM.p(fr, -S_C, zd)                   # ...over to the leg's axis line,
    g2 = BOTTOM.p(fc, -S_C, -17.0)                 # ...and down into it
    bar = _run([g0, g0b, g1a, g2, (g2[0] + 10.0, g2[1], g2[2])], d)   # along the chamber, toward
                                                            # the trough
    return [("pogo_harness_leg", leg), ("pogo_harness_body", body),
            ("pogo_harness_bar", bar)]
