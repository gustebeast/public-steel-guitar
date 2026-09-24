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

from elec import harness as EH             # the PCB's pin order, single-sourced
from cadkit.cables import bundle_paths, helix_cable, oct_cable
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
# THE FEMALE BOARD IS RECESSED INTO THE HOST, top flush with the host face, and that
# is a RETENTION decision before it is anything else. Lying on the face it was held by
# ONE M4 and nothing else: free to rotate about that screw and to creep until it was
# tightened, with a 0.45 landing budget to spend. Now four walls of plastic take every
# direction except the one it is installed along, and the screw only has to stop it
# coming back out (user's rule).
#
# A raised RIM around a board sitting ON the face would have done the same job, and it
# is the obvious move -- but the tenon's mouth has to clear whatever stands proud, and
# the rim grows that cavity by its own thickness on every side. Measured: the mouth's
# breakout through the tenon's flat goes from 5.10 wide to 12.70. Recessing costs the
# mouth nothing; it SHRINKS it, because the board's own 1.6 is no longer in the way.
F_TOP = 0.0                     # the board's top face -- the host's face
F_BOT = -PCB_T                  # ...and its underside, the pocket's floor
PAD_Z = F_TOP + TG_FACE_H       # 3.5 the contact faces, off the host's face
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
PH_PITCH = 2.0                  # JST ePH: the PH family is 2.00 mm pitch
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
PIN_LEAD = 2 * B                # 1.6 of STRAIGHT wire square out of every pin before
                                # the fan starts (user). Fanning straight off the face
                                # leaves four wires converging at shallow angles and
                                # you cannot see which one lands where; a short square
                                # lead-in reads at a glance, and is what a crimped
                                # harness does anyway -- the contact holds the wire in
                                # line for its own length.
BEND = 7 * B                    # 5.6 above the plug for the harness to turn: the lead-in
                                # takes 1.6 and the fan 2.4, and the turn at the end of
                                # those runs past itself by the cable's own radius, so
                                # the pocket has to end clear of all three
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

# FOUR CONDUCTORS, DRAWN AS FOUR (user), the way src.wiring already draws every CAN run
# rather than as one jacket -- there is no jacket here to draw. They sit in the
# connector's own PIN ORDER around the bundle's axis, so no conductor has to cross a
# neighbour to reach its crimp: GND, 5V, CAN_H, CAN_L on 1-4 at both ends.
#
# The pair that matters is CAN_H/CAN_L, and they are placed DIAGONALLY OPPOSITE across
# the bundle rather than side by side. Twisted, that is the pair; untwisted -- which is
# what the model draws -- keeping them on one diagonal at least keeps their spacing
# equal down the whole run instead of letting the power pair sit between them.
# The four centres sit on a square of SIDE 2 * _WOFF, so the neighbour spacing is that
# side, NOT the diagonal: at anything under one wire OD the conductors interpenetrate
# down the whole run (0.37 gave 24 overlaps, the worst 48 mm3).
_WOFF = (HARNESS_WIRE_OD + 0.1) / 2.0                   # 0.5: touching plus 0.1 of air
# THE PIN ORDER IS THE PCB's, IMPORTED, NOT RETYPED (elec.harness). That module exists
# because this constant was written out three times with nothing comparing the copies,
# and a wrong pin order is invisible until it puts a rail into a signal -- so the CAD
# reads it rather than keeping a fourth copy. Change PH_PINOUT and the wires move.
_PINOUT = tuple(n.lower() for n in EH.ph_drop_pins())   # ('gnd', 'v5', 'can_h', 'can_l')
_PLACE = ((-_WOFF, -_WOFF), (_WOFF, -_WOFF), (_WOFF, _WOFF), (-_WOFF, _WOFF))
HARNESS_WIRES = tuple(zip(_PINOUT, _PLACE))
# ...and THE TWO PAIRS MUST STAY PAIRS. This is two twisted pairs, not a four-core:
# CAN_H with CAN_L, and the rail with its return. A twisted pair is twisted with its
# OWN partner, so each pair sits on one side of the square -- ADJACENT, sharing an
# edge. (Diagonal is what an earlier pass of this file claimed and drew; it is wrong
# on both counts, and this assert is what caught it.)
def _adjacent(a, b):
    return sum(1 for u, v in zip(_PLACE[a], _PLACE[b]) if u != v) == 1


for _p, _q in (("can_h", "can_l"), ("gnd", _PINOUT[1])):
    assert _adjacent(_PINOUT.index(_p), _PINOUT.index(_q)), (
        "%s and %s are a TWISTED PAIR and no longer sit side by side in the bundle -- "
        "elec.harness.PH_PINOUT moved a pin and _PLACE has not followed" % (_p, _q))
assert 2 * (_WOFF * math.sqrt(2) + HARNESS_WIRE_OD / 2.0) <= HARNESS_D, (
    "the four conductors as placed do not fit the O%.1f bundle" % HARNESS_D)


# ── the female board, flat on the host face ──────────────────────────────────
# EVERY PART ON ITS FACE, like the male's: the target, and beside it (-t) a SIDE-ENTRY
# JST ZR, S4B-ZR-SM4A-TF (eZR p.5 SM4 type): 4 way B 9.0, body 5.0 deep with its tails
# (1.5) behind, 3.7 off the board. ZR's own sockets are IDC; its header also takes the
# ZH CRIMP housing (ZHR-4 + SZH-002T, eZR p.1), which is how this harness is made.
ZR_PITCH = 1.5                  # JST eZR/eZH: the ZR/ZH family is 1.50 mm pitch
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
F_HOLE_S = -(TG_BODY_S / 2.0 + CLR + HEAD_D / 2.0)      # -9.2 from the row's centre
F_HOLE_T = PIN_T
FB_T0 = ZR_MOUTH                                        # the plug overhangs this edge
FB_T1 = PIN_T + TG_BODY_T / 2.0 + EDGE                  # 4.65
FB_S0 = F_HOLE_S - HOLE_D / 2.0 - EDGE                  # -11.95: past the screw
FB_S1 = TG_BODY_S / 2.0 + EDGE                          # 5.6: just past the target
F_SCREW_L = 8.0                 # M4 x 8 button: 1.6 of board, then 6.4 of insert bite
F_END = F_SCREW_L + 1.0          # the hole stops past the screw's tip
assert ZR_S / 2.0 <= TG_BODY_S / 2.0 + EDGE, "the ZR runs past the target's end"
assert PCB_T + ZR_H < EDGE_D and PCB_T + HEAD_H < EDGE_D, (
    "the female's parts reach the male board's edge")

# THE ROW IS OFF CENTRE by S_C, so the female's screw fits beyond the target's end;
# the male board shifts with it (Joint.p applies it). It is offset AWAY from the tenon's
# build direction, which is what leaves the cavities' roofs their headroom -- the
# ceiling-side flat sits 15.0 off the row, against the 9.0 it would have on the other
# side of the axis. That is why this sign and the board's s dimensions above go
# together, and why neither is free on its own.
S_C = 3.0
_HALF = LS.TEN_W / 2.0
assert S_C + F_HOLE_S - HEAD_D / 2.0 - CLR - WALL >= -_HALF, "the female's head breaks a flat"
assert S_C + FB_S1 + CLR + WALL <= _HALF, "the female breaks a flat"
assert S_C + MB_S / 2.0 + CLR + WALL <= _HALF, "the male board breaks a flat"
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
    return ScrewJoint(M4, j.p(F_HOLE_T, F_HOLE_S, F_TOP), (0.0, 0.0, -j.dz),
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

    def house(self, t0, t1, s0, s1, d0, d1, shed=0):
        """A cavity shaped like a HOUSE: the box, with a 45 degree gable standing on
        whichever s face the tenon builds toward, because that face is its CEILING.
        ONE closed profile, extruded along d -- not a box with a triangle unioned onto
        it. (It was that union: the gable's face was computed as -s1 rather than s0, so
        on a joint that builds toward -S the roof came out as a SEPARATE triangle
        floating beside the slot.)

        `shed` makes the roof ONE-SIDED instead -- +1 rising toward t1, -1 toward t0 --
        for a cavity that sits against a TALLER neighbour. A gable there puts a
        descending flank right where the neighbour's wall climbs, and those two make a
        V VALLEY: the material caught between them narrows to a knife edge that has to
        start from a point in mid-air. Every face involved is a legal 45, which is
        exactly why it is worth naming -- a valley is the one place not to sit at the
        limit. A shed runs up INTO the neighbour's wall, and there is no valley."""
        u = self.up_s
        sc = s1 if u > 0 else s0                # the ceiling face
        sf = s0 if u > 0 else s1                # and the floor opposite it
        hw = (t1 - t0) / 2.0                    # 45 degrees, so the ridge is half-span
        tm = (t0 + t1) / 2.0
        apex = sc + u * hw
        z0, z1 = sorted((self.z + self.dz * d0, self.z + self.dz * d1))
        s_flat = u * (LS.TEN_W / 2.0) - S_C     # the tenon's flat on the ceiling side
        if shed:
            top = sc + u * (t1 - t0)            # 45 degrees across the whole span
            assert (top - s_flat) * u < 0, (
                "the shed roof runs out through the tenon's flat")
            hi_t = t1 if shed > 0 else t0
            lo_t = t0 if shed > 0 else t1
            pts = [(t0, sf + S_C), (t1, sf + S_C),
                   (hi_t, top + S_C), (lo_t, sc + S_C)]
            return (cq.Workplane("XY").workplane(offset=z0)
                    .polyline(pts).close().extrude(z1 - z0)
                    .rotate((0, 0, 0), (0, 0, 1), self.ang)
                    .translate((self.x, self.y, 0.0)))
        pts = [(t0, sf + S_C), (t1, sf + S_C), (t1, sc + S_C)]
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


# BOTH JOINTS put t on the +X-Y diagonal, so the board's parts and the ZR's mouth face
# -X+Y, and the board's own body sits on the tenon's -Y side -- clear of the latch,
# which takes the +Y middle at both joints (leg_latch.BUTTON_SIDE).
#
# THE DIAGONAL IS NOT A FREE CHOICE, and neither is the side the board sits on:
#
#   * Only two of the tenon's four flats can carry a joint. house() needs S parallel to
#     the tenon's build direction or its gables do not land on the cavities' ceilings,
#     and TENON_UP is the -X-Y diagonal, so T is +-(-_D, _D).
#   * The board's s layout is ASYMMETRIC -- the row sits S_C off the leg's axis, away
#     from the build direction, and that offset is what gives the roofs their headroom
#     (12.0 to the ceiling-side flat). Putting the board on the other side of the axis
#     is therefore not a sign flip: every s dimension and assert here is written from
#     the row toward that flat and has to be authored for the side it is on.
#   * Which side it IS on is the same decision as leg_latch.BUTTON_SIDE. The latch takes
#     one of the tenon's Y middles and this board's lane takes the other (see DROP_OFF).
#
# The tenon builds along -S here, so every cavity's s0 face is its ceiling: house()
# stands a 45 degree gable on it, in the SAME profile as the cavity.
_D = math.sqrt(0.5)
TOP = Joint("top", LS.Z_MORTISE_ROOF, -1.0, (_D, -_D),
            LS.PRINT_UP["fixed_tenon"], LS.PRINT_UP["body_adapter"])
assert abs(TOP.S[0] * LS.TENON_UP[0] + TOP.S[1] * LS.TENON_UP[1]) > 0.999, (
    "the top joint's s axis must lie along the tenon's build direction, or house()'s "
    "gables are not on the cavities' ceilings")
# BOTTOM: the adjust tenon's lower end, in the pedal bar. Into the tenon is +Z.
BOTTOM = Joint("bottom", LS.Z_ADJ_TEN_BOT, 1.0, (_D, -_D),
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
    board = j.box(FB_T0, FB_T1, FB_S0, FB_S1, F_BOT, F_TOP)
    board = board.cut(j.cyl_d(HOLE_D, F_HOLE_T, F_HOLE_S, F_BOT - 1.0, F_TOP + 1.0))
    tg = j.box(TG_T0, TG_T0 + TG_BODY_T, -TG_BODY_S / 2.0, TG_BODY_S / 2.0,
               F_TOP, F_TOP + TG_BODY_H)
    for s in j.targets():
        tg = tg.union(j.cyl_d(TG_FACE_D, PIN_T, s, F_TOP + TG_BODY_H - 0.01, PAD_Z))
    zr = j.box(ZR_MOUTH, ZR_MOUTH + ZR_DEPTH, -ZR_S / 2.0, ZR_S / 2.0, F_TOP,
               F_TOP + ZR_H)
    zr = zr.union(j.box(ZR_MOUTH + ZR_DEPTH - 0.01, ZR_T1, -ZR_S / 2.0 + 1.0,
                        ZR_S / 2.0 - 1.0, F_TOP, F_TOP + 0.5))
    zr = zr.union(j.box(ZR_MOUTH - ZR_PLUG, ZR_MOUTH + 0.01, -ZR_S / 2.0 + 0.75,
                        ZR_S / 2.0 - 0.75, F_TOP + 0.3, F_TOP + ZR_H - 0.3))
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
MOUTH_D = max(TG_FACE_H, ZR_H, HEAD_H) + CLR    # only what stands PROUD of the host's
                                               # face now -- the board itself is in it


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
    # the wire's cavity abuts the MOUTH, whose ceiling stands 7.45 higher, so it gets a
    # SHED rising toward it rather than a gable -- a gable's far flank and the mouth's
    # wall made the V the user found at t -5.65
    out = out.union(j.house(WIRE_T0 - CLR, FB_T0 + 0.01, -ZR_S / 2.0 - CLR,
                            ZR_S / 2.0 + CLR, -1.0, MOUTH_D, shed=+1))
    # THE BOARD'S POCKET IS ONE CAVITY, NOT THREE. The slot, the header's room and the
    # PH's room sit side by side along t, and cut as three houses each grew ITS OWN
    # gable -- so where two met, their flanks formed a V VALLEY (user spotted it in the
    # tab). Each flank is a legal 45, but a valley is the one place not to sit at the
    # limit: the material under it comes to a knife edge and starts from a point.
    #
    # One roof over the lot removes them. It costs almost nothing in material: the three
    # lanes were already contiguous (the header and the PH both start at TF), so all
    # this gives up is the sliver above the header's shorter ceiling.
    # THE PH's ROOM IS SWEPT DOWN THE INSTALL STROKE, not just cut where the connector
    # ends up. The board slides in from the tenon's mouth, so everything standing off
    # its face travels the WHOLE depth to reach its seat: cut only at the seat, the PH
    # gouged up to 396 mm3 of tenon on the way past (the board and the pins are clean
    # -- nothing else stands as far off the face). At rest AND fully withdrawn it read
    # zero, which is why this survived every static check the project has.
    # ...and it STEPS IN once the board has ended. The full-width pocket needs a ridge
    # 3.85 above its ceiling, and up where the PH alone still needs room that ridge came
    # within 0.30 of the LEG LATCH's pocket. Above MB_TOP only the PH's lane is wanted,
    # which is 1.90 narrower and rides 1.50 lower, and the step between the two is free:
    # its face is square to the joint axis, and the tenon builds ACROSS that axis, so it
    # is a wall in the print, not a ceiling.
    _w = max(MB_S, RA_BODY_S, SE_S) / 2.0 + CLR
    out = out.union(j.house(TB - CLR, TF + SE_H + CLR, -_w, _w, -1.0, MB_TOP + CLR))
    out = out.union(j.house(TF, TF + SE_H + CLR, -SE_S / 2.0 - CLR, SE_S / 2.0 + CLR,
                            MB_TOP + CLR - 0.01, PLUG_TOP + CLR))
    # THE WAY UP, STRAIGHT OUT OF THE PORT. `route_xy` None means exactly that: the
    # bore stands on the connector's own line, so the harness leaves the plug and goes
    # without a turn.
    #
    # It used to aim at the RETIRED TRRS BORE's axis and hop 2.10 across to reach it,
    # then jog a second time to clear the ladder -- two doglegs inherited from a part
    # that no longer exists, in a channel sized for a plug that no longer travels it
    # (user spotted the offset in the tab). The port's own line clears the ladder on
    # its own: the ladder owns |y| <= 2.00 and wants 1.60 of wall, so a O4.0 lane needs
    # |y| >= 4.80 and the port sits at y +5.20.
    pt = TF + SE_H / 2.0
    rt, rs = (pt, 0.0)
    if route_xy is not None:
        rx, ry = route_xy
        rt = (rx - j.x) * j.T[0] + (ry - j.y) * j.T[1]
        rs = (rx - j.x) * j.S[0] + (ry - j.y) * j.S[1] - S_C
        t0, t1 = sorted((pt, rt))
        s0, s1 = sorted((0.0, rs))
        # ...and the link has to hold the FAN, not just the bundle: above the plug the
        # four conductors are still spread across the pin row, which reaches further in
        # s (+-3.0 at PH pitch) than half the lane's width (2.0).
        _fan = abs(pin_s(PH_PITCH, 0)) + HARNESS_D
        # house(), not box(): this is the ONE cavity here that kept a flat roof, and at
        # span 4.80 it was the only real ceiling either tenon had (user spotted it in the
        # tab, in the print orientation -- I had first mis-read it as a wall by probing
        # the nearest face CENTRE instead of the nearest surface).
        out = out.union(j.house(t0 - route_d / 2.0, t1 + route_d / 2.0,
                                min(s0 - route_d / 2.0, -_fan),
                                max(s1 + route_d / 2.0, _fan), PLUG_TOP, DEEP))
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
    assert abs(up[1]) > 0.99, "this assumes the host builds along Y, either way up"
    assert abs((j.ang % 90.0) - 45.0) < 1e-6, (
        "the cavity is no longer on the diagonal, so its ceiling is flat again and "
        "this owes it a real gable")
    return j.box(t0, t1, s0, s1, d0, d1)


def host_negatives(j, up=None, deep=F_DEEP):
    """Cut in the adapter / the bar: the female's insert, and the SLOT the harness
    drops through past the ZR's plug (gabled -- both hosts build +Y). The caller adds
    whatever the slot runs on into."""
    up = up or j.host_up
    # ...half a bundle wider than the wire's own lane on the far side: the harness turns
    # down here, and a turn in oct_cable runs each segment PAST the corner by the cable's
    # radius, so the run reaches further than its centreline does
    # the slot stops WALL short of the pocket, not at its own clearance: at the plug's
    # own +CLR the web between the two was 1.40, under the two-bead floor. It still
    # covers the plug's end (-7.35) and the wires leaving it (-7.45).
    out = _gable(j, WIRE_T0 - CLR - HARNESS_D / 2.0,
                 min(ZR_MOUTH - ZR_PLUG + CLR, FB_T0 - CLR - WALL),
                 -ZR_S / 2.0 - CLR,
                 ZR_S / 2.0 + CLR, deep, 0.01, up)
    # THE POCKET the board drops into: four walls, a floor, and the board's own outline
    # plus a slip fit. Its walls run along the joint's diagonal, so in a host that
    # builds +Y every one of them stands at 45 to the build and holds itself up -- the
    # same reason the tenon's own cavities need no roof (see _gable).
    out = out.union(j.box(FB_T0 - CLR, FB_T1 + CLR, FB_S0 - CLR, FB_S1 + CLR,
                          F_BOT, F_TOP + 0.01))
    # AN ACCESS CHANNEL FOR THE INSERT. The heat-set goes in from the mortise side,
    # down the same axis the screw uses -- but its pocket is O6 and everything above
    # it was the board pocket's local wall, which leaves 2.20 of radius against the
    # 2.95 the insert needs. It could not physically reach its bore (user spotted it).
    # So the pilot is carried out to the host's face. It notches the pocket's +t wall
    # beside the screw, which is the cheap half of the trade: the wall is 18 long in s
    # and the board is still held by the rest of it.
    # ...and it starts at F_BOT - 0.01, NOT F_BOT + 0.01. That sign left a 0.01 mm
    # film of plastic, 3.79 mm^2 of it, lying exactly in the board pocket's own plane:
    # the bore began one hundredth of a millimetre short of the cavity it was supposed
    # to open into, so instead of merging with it, it left a skin between the two.
    # check_thin reported it as a 0.01 wall -- the thinnest in the part by a factor of
    # forty -- and it would have printed as a torn membrane over the insert's mouth.
    # Cavities that are meant to be ONE cavity must OVERLAP; touching is not enough.
    out = out.union(j.bore_d(M4.insert_pilot_d, F_HOLE_T, F_HOLE_S,
                             F_BOT - 0.01, 0.5, up))
    return out.union(female_screw(j).cutter(up))


ROUTE_D = 5 * B                 # 4.0: the harness's own way up the tenon. The bore it
                                # replaced was O7.6, sized for a moulded TRRS plug that
                                # had to travel it; nothing travels this but four bare
                                # wires (they are crimped after threading), so it is
                                # sized for the O2.4 bundle -- and the narrower it is,
                                # the closer to the port its lane can sit (below).
ROUTE_OFF = -9 * B              # -7.2 off the leg's axis in -Y (the side the latch
                                # leaves free), and NOT on the port's own line, which is
                                # where this wanted to go.
                                #
                                # The port sits at y +5.20 and a straight shot up from
                                # it would be ideal -- but the ADJUSTMENT LADDER is
                                # teardropped, and a teardrop's envelope is not its
                                # diameter: O4.0 holes reach r*sqrt(2) = 2.83, not 2.00.
                                # Against that, a O4.0 lane needs y >= 6.43, so the port
                                # line is 1.23 short and the harness takes ONE 2.00 step
                                # in +Y at the plug and then runs straight.
                                #
                                # That step is real and worth keeping honest about. What
                                # it replaces is TWO doglegs -- a 2.10 hop onto the
                                # RETIRED TRRS bore's axis and then a jog back out to
                                # clear the ladder -- both inherited from a part that no
                                # longer exists (user spotted the offset in the tab).
# ── THE FIXED TENON'S LANE ────────────────────────────────
# The harness owns its own lane at BOTH ends -- this one and ROUTE_OFF -- rather than
# borrowing a bore from somewhere else, which is what put a dogleg in the other end.
#
# It sits in the tenon's -Y middle because the LATCH has the +Y one (leg_latch's pocket
# and spring run the depth of this tenon). The two are one decision: whichever middle
# the latch takes, the lane takes the other, and neither is squeezed past the other.
DROP_OFF = -7 * B               # -5.6, the middle the latch leaves free
DROP_X = -2 * B                 # -1.6: it is x that keeps this clear of the board


def drop_xy(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """World (x, y) of the fixed tenon's harness lane."""
    return sx + DROP_X, ly + DROP_OFF


# how far that lane sits from the nearest of the tenon's four flats. The section is a
# square on the diagonals, so the flats' normals are (+-_D, +-_D) at LS.TEN_W / 2.
_DROP_WALL = min(LS.TEN_W / 2.0 - (DROP_X * nx + DROP_OFF * ny) * _D
                 for nx in (1.0, -1.0) for ny in (1.0, -1.0))
assert _DROP_WALL - ROUTE_D / 2.0 * math.sqrt(2) >= D.MIN_WALL_2P, (
    "the fixed tenon's lane leaves only %.2f to its nearest flat"
    % (_DROP_WALL - ROUTE_D / 2.0 * math.sqrt(2)))

_LADDER_R = LS.ADJ_HOLE_D / 2.0 * math.sqrt(2)      # a TEARDROP's reach, not its radius
# the ladder is bored on the leg's axis, so what matters is how far OFF that axis the
# lane sits -- the side it is on does not enter into it
assert abs(ROUTE_OFF) - ROUTE_D / 2.0 - _LADDER_R >= D.MIN_WALL_2P, (
    "the harness lane at y %+.2f leaves only %.2f to the ladder's teardrop envelope"
    % (ROUTE_OFF, abs(ROUTE_OFF) - ROUTE_D / 2.0 - _LADDER_R))

ROUTE_X = 4 * B                 # 3.2 off the axis in X, and the FLATS set this, not the
                                # port. The port stands 5.20 out in X, and a lane there
                                # -- 5.20 out and ROUTE_OFF along Y -- drives into the
                                # +X-Y flat: 3.23 to it, 0.41 clear of the teardrop's
                                # envelope, against the 1.60 two beads want. Pulled to
                                # 3.20 the lane keeps 4.65 and 1.82. The harness pays a
                                # 2.00 step in X for it, the same size as the step it
                                # already takes to get off the port's line.


def route_xy(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """World (x, y) of the adjust tenon's harness lane."""
    return sx + ROUTE_X, ly + ROUTE_OFF


_ROUTE_WALL = min(LS.TEN_W / 2.0 - (ROUTE_X * nx + ROUTE_OFF * ny) * _D
                  for nx in (1.0, -1.0) for ny in (1.0, -1.0))
assert _ROUTE_WALL - ROUTE_D / 2.0 * math.sqrt(2) >= D.MIN_WALL_2P, (
    "the adjust tenon's lane leaves only %.2f to its nearest flat"
    % (_ROUTE_WALL - ROUTE_D / 2.0 * math.sqrt(2)))
CHAN_W = 4 * B                  # 3.2: the harness with room
CHAN_X = -13 * B                # -10.4 off the leg's axis: where the channel's LONG
                                # run down the adapter's top face sits.
                                #
                                # IT IS OUTBOARD OF EVERY BODY TENON, and that is the
                                # whole point of the number. The tenons stand on this
                                # same face and run the same way, so a channel on the
                                # connector's own line went straight under the outermost
                                # one's foot -- 3.20 wide and 2.00 deep for 21.45 of its
                                # 32.49 run, which is where it grabs the adapter (user
                                # saw it in the tab). Out here the run clears that foot
                                # by 2.26 and still leaves 10.40 to the -X face.
                                #
                                # The gaps BETWEEN tenons cannot take it: they are 3.80
                                # and 3.60 against a 3.20 channel, so the best either
                                # could leave is 0.30 a side.
                                #
                                # Getting there costs no dog-leg worth the name. The ZR's
                                # mouth already faces -t, which is -X+Y, so the harness
                                # leaves the connector heading THIS way; the channel just
                                # carries on to the lane before turning down it.
CHAN_D = 6 * B                  # 4.8 -- the body tenons are fused on after this is cut
                                # and refill the groove's top ~1 mm


def adapter_features(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """(None, negatives) for the body adapter at the signal corner, in its own frame.
    The harness rises out of the female's connector into a groove in the top face that
    runs out whichever Y face the port points at: -Y, inboard, under the instrument."""
    j = TOP
    neg = host_negatives(j)
    fc = j.p((WIRE_T0 + ZR_MOUTH - ZR_PLUG) / 2.0, 0.0, 0.0)
    # OUT THE -Y FACE (user): inboard, under the instrument. The +Y face is the rail
    # side, and it is also the one the latch now opens onto.
    #
    # AN L, not a straight run. The long leg goes down CHAN_X, outboard of every body
    # tenon (see CHAN_X); the short one carries the harness out to it from the plug,
    # along the direction the ZR's mouth already points. The ZR faces -t, which on this
    # diagonal is -X+Y, so the wire surfaces on the +Y side and heading -X -- the short
    # leg is the run it was making anyway, and the turn happens clear of the tenons
    # rather than under one.
    xc = j.x + CHAN_X
    y_out = j.y - (LS.LEG_W / 2.0 + 1.0)
    y_turn = fc[1]                                  # where the wire surfaces
    neg = neg.union(cq.Workplane("XY").add(cq.Solid.makeBox(   # the long leg, down -Y
        CHAN_W, (y_turn + CHAN_W / 2.0) - y_out, CHAN_D + 1.0,
        cq.Vector(xc - CHAN_W / 2.0, y_out, LS.Z_TOP - CHAN_D))))
    neg = neg.union(cq.Workplane("XY").add(cq.Solid.makeBox(   # ...and the short one
        (fc[0] + CHAN_W / 2.0) - (xc - CHAN_W / 2.0), CHAN_W, CHAN_D + 1.0,
        cq.Vector(xc - CHAN_W / 2.0, y_turn - CHAN_W / 2.0, LS.Z_TOP - CHAN_D))))
    return None, neg


def bar_features(floor_z: float, chamber_top_z: float):
    """(None, negatives) for the pedal bar, in the BAR's frame: the connector's cavity
    runs on down into the wiring chamber, which it overlaps."""
    j = Joint("bottom_bar", floor_z, BOTTOM.dz, BOTTOM.T, BOTTOM.tenon_up,
              BOTTOM.host_up)
    return None, host_negatives(j, deep=chamber_top_z - floor_z - 0.01)


# ── the harness, drawn ───────────────────────────────────────────────────────
# THE COIL IS ITS OWN PART, and round (cadkit.cables.helix_cable). Drawn octagonal and
# fused into the run it cost ~1200 faces against 3 -- the fuse splits a face at every
# corner, so coarsening the helix barely helped (~700 even at 4 segments a turn) -- and
# every pair the overlap gate checks against the harness then pays for them. Standing it
# alone buys the cheap swept solid AND keeps the round-to-octagon tangent fuse out, which
# was the only reason to polyline it. COIL_GAP holds the run clear of its tilted end caps.
# The run meets the coil VERTICALLY, on the helix's own start radius, so the run's end
# cap is square to the coil's overhang. Arriving at a slant instead needed 2.2 of gap --
# most of a cable diameter, which reads as a BREAK in the cable rather than a join.
# The coil's own end cap is NEARLY VERTICAL (its normal is the helix TANGENT, only 21.3
# off horizontal), so the coil overshoots its nominal end by (HARNESS_D / 2) cos(lead) =
# 1.118 -- cos, not sin, which is what a first guess of 0.6 got wrong.
FAN_RUN = 3 * B                 # 2.4 for the fan to gather, AFTER the lead-in ends.
                                # The lead-in is only half the job: with the bundle's
                                # first point 0.8 past the lead, four wires had to close
                                # the whole pin row in 0.8 of run and swung out almost
                                # square to the axis, so they read as running ALONG the
                                # plug's face rather than into it (user). Worse on the
                                # ZH stubs, where the lead-in (1.6) was LONGER than the
                                # 1.2 to the next point, so every wire ran out past it
                                # and doubled back.
# THE ZH STUB GETS ITS OWN, SHORTER PAIR, and not as a preference: its cavity stops at
# WIRE_T0 - CLR with only 1.6 of tenon beyond that, so PIN_LEAD + FAN_RUN (4.0) ran the
# wires out through the wall. It is the smaller connector anyway -- 1.5 pitch against the
# PH's 2.0 -- so it needs less room to separate its ways.
STUB_LEAD = 1 * B               # 0.8 square out of the ZH
STUB_FAN = 1 * B                # 0.8 for its fan
COIL_LEAD = 4.0                 # the vertical run-in
COIL_GAP = 2 * B                # 1.6 -- > (HARNESS_D / 2) cos(lead), measured 1.118


def port_xy(j):
    """World (x, y) of the PH port's axis: the line the harness leaves the plug on."""
    x, y, _ = j.p(TF + SE_H / 2.0, 0.0, 0.0)
    return x, y


def pin_s(pitch, k, n=RA_N):
    """Where way `k` (0-based) of an `n`-way connector sits along s, centred on the
    housing. PIN 1 IS AT -s at every connector in this joint, which is the half of
    the pin-order contract the CAD owns: elec.harness says WHICH circuit is pin 1,
    this says WHERE pin 1 is. bronner needs both to route the boards."""
    return (k - (n - 1) / 2.0) * pitch


def harness():
    """THE RUN, drawn: plug to plug down the whole leg -- over to the old lead's bore,
    down the fixed tenon, COILED through the gap between the tenons (src.coil_mandrel's
    coil at the span the leg is drawn at), the adjust tenon's channel past the ladder,
    the jog, and over to the bottom board -- plus the two female stubs."""
    from . import bar_trrs as BT
    from . import coil_mandrel as CM
    d = HARNESS_D
    dm = PLUG_TOP + PIN_LEAD + FAN_RUN      # lead-in, THEN room for the fan
    pt = TF + SE_H / 2.0
    xs, ys = drop_xy()
    xb, yb = BT._ax()
    xc, yc = LS.LEG_X + BT.CH_X, LS.LEG_Y + BT.CH_Y
    z_a, z_b = LS.Z_FIX_TEN_BOT - 8.0, LS.Z_ADJ_TEN_TOP + 8.0
    pitch = (z_a - z_b) / CM.TURNS
    r = math.sqrt(max((CM.COIL_LEN / CM.TURNS) ** 2 - pitch ** 2, 0.0)) / math.pi / 2.0
    ax, ay = LS.LEG_X, LS.LEG_Y
    up_path = [TOP.p(pt, 0.0, PLUG_TOP), TOP.p(pt, 0.0, dm),
               (xs, ys, TOP.p(0, 0, dm)[2]), (xs, ys, LS.Z_FIX_TEN_BOT - 2.0),
               (ax + r, ay, z_a + COIL_LEAD), (ax + r, ay, z_a + COIL_GAP)]
    # ...and down the PORT's OWN LINE from there: one turn at the top of the tenon and
    # then straight to the plug, which is what the bore is now cut for.
    # ...and down the lane on the PORT's OWN X, stepping the last 1.20 in +Y at the
    # plug (ROUTE_OFF: the ladder's teardrop envelope, not the port, sets that lane)
    _px, _ly = route_xy()
    lo_path = [(ax + r, ay, z_b - COIL_GAP), (ax + r, ay, z_b - COIL_LEAD),
               # the swing onto the lane happens ABOVE the tenon's top face, in open
               # air: done below it, the wires were moving sideways inside the bore and
               # rubbed its wall the whole way down
               (_px, _ly, LS.Z_ADJ_TEN_TOP + 4.0),
               (_px, _ly, BOTTOM.p(pt, 0.0, dm)[2]),
               BOTTOM.p(pt, 0.0, dm), BOTTOM.p(pt, 0.0, PLUG_TOP)]
    # THE COIL STAYS ONE BODY (see helix_cable): four helices about one axis is four
    # sweeps where the bundle reads the same, and the wind count and mean diameter --
    # the two things it has to get right -- are the bundle's, not a conductor's.
    coil = helix_cable(ax, ay, z_b, z_a, CM.TURNS, r, d)
    # ...and out of the ZH, where FAN_RUN does not fit: the wire cavity stops at
    # WIRE_T0 - CLR and the tenon's flat is only 1.6 beyond that, so the stub gets the
    # lead-in plus whatever is left (STUB_FAN) rather than the full 2.4.
    fr = ZR_MOUTH - ZR_PLUG - 0.1 - STUB_LEAD - STUB_FAN
    fc = fr                                          # ...and it drops there
    zd = F_TOP + ZR_H / 2.0                         # the plug's height off the host
    f0 = TOP.p(ZR_MOUTH - ZR_PLUG - 0.1, 0.0, zd)     # just off the plug's end
    zc = LS.Z_TOP - CHAN_D + d / 2.0 + 0.2          # lying in the groove's bottom
    y_out = LS.LEG_Y - LS.LEG_W / 2.0
    xc = LS.LEG_X + CHAN_X                          # the channel's long leg
    f1 = TOP.p(fr, 0.0, zd)
    body_path = [f0, f1, (f1[0], f1[1], zc), (xc, f1[1], zc), (xc, y_out, zc),
                 (xc, y_out - 12.0, zc)]
    g0 = BOTTOM.p(ZR_MOUTH - ZR_PLUG - 0.1, 0.0, zd)
    g0b = BOTTOM.p(fr, 0.0, zd)                    # clear of the plug first...
    # ...then SLANT onto the leg's axis line on the way down, rather than stepping
    # across at the plug's own height and turning square into the drop. That corner
    # was never forced: the move is 3.00 in s at a fixed t, the ZR's slot is +-4.80
    # wide in s, so the whole diagonal lies inside the cavity that was already there.
    # It read as a V hanging off the connector in the tab (user).
    g2 = BOTTOM.p(fc, -S_C, -17.0)                 # ...and down into the chamber
    bar_path = [g0, g0b, g2, (g2[0] + 10.0, g2[1], g2[2])]        # along the chamber,
                                                                  # toward the trough
    out = [("pogo_harness_coil", coil)]
    w = HARNESS_WIRE_OD
    # NUMBERED, not named, per run (0 leg above the coil, 1 leg below, 2 body stub,
    # 3 bar stub): check_overlaps strips a trailing index group, so all four runs of a
    # circuit collapse to ONE base name and the wire allow-list needs four entries
    # rather than sixteen.
    # ...and each run FANS OUT onto its own pin at the connector it ends at, instead
    # of all four arriving on the housing's centre line. Which end that is differs per
    # run: the leg's two runs leave a PH, the stubs leave a ZH.
    # (terminating end, pitch, joint, the direction the wire LEAVES the pin). The PH's
    # mouth faces up the leg, so its wires leave along the joint axis; the ZH lies on
    # the host face with its mouth facing -t, so its wires leave along -t.
    ends = ((0, PH_PITCH, TOP, (0.0, 0.0, TOP.dz), PIN_LEAD),
            (-1, PH_PITCH, BOTTOM, (0.0, 0.0, BOTTOM.dz), PIN_LEAD),
            (0, ZR_PITCH, TOP, (-TOP.T[0], -TOP.T[1], 0.0), STUB_LEAD),
            (0, ZR_PITCH, BOTTOM, (-BOTTOM.T[0], -BOTTOM.T[1], 0.0), STUB_LEAD))
    for k, (path, (at, pitch, j, ed, lead_l)) in enumerate(zip((up_path, lo_path,
                                                               body_path, bar_path),
                                                              ends)):
        # THE BUNDLE IS AIMED AT THE PIN ROW, and the frame is seeded at the path's
        # START, so a run that ENDS at its connector is walked backwards and flipped
        # again afterwards. Without both, the conductors arrive in whatever order the
        # frame happened to land in: one wire ran to the middle of the row and back out
        # to its own pin, and two others came in almost on top of each other (user).
        rev = at != 0
        walk = list(reversed(path)) if rev else list(path)
        legs = bundle_paths(walk, [o for _, o in HARNESS_WIRES],
                            across=(j.S[0], j.S[1], 0.0))
        if rev:
            legs = [list(reversed(q)) for q in legs]
        for i, ((name, _), cpath) in enumerate(zip(HARNESS_WIRES, legs)):
            cpath = list(cpath)
            p = cpath[at]
            ds = pin_s(pitch, i)        # this way's place along the row
            face = (p[0] + ds * j.S[0], p[1] + ds * j.S[1], p[2])
            lead = tuple(face[m] + ed[m] * lead_l for m in range(3))
            # square out of the pin FIRST, then fan back to the bundle
            cpath[at:at + 1] = ([face, lead] if at == 0 else [lead, face])
            out.append(("pogo_wire_%s_%d" % (name, k), oct_cable(cpath, w)))
    return out
