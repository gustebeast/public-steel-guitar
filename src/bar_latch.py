"""PEDAL BAR -> ADJUST TENON latch: a YOKE in a screw-on COLLAR at the top of the
bar's mortise tower.

WHY NOT leg_latch's SLIDER. That slider lets go by moving its hook INWARD, so it can
only hook a part that SURROUNDS the one carrying it. Here the tenon goes INTO the
bar, so the latch that lives on the bar goes round the tenon instead: pad on the -Y
side, hook on the far +Y side, and pressing the pad (+Y) pulls the hook out.

WHY A COLLAR (user). A ring sealed inside the bar's tower could never be fitted, and
the bar prints -Y -> +Y, so every -Y-facing latch cavity in it was a ceiling. So the
top COLLAR_H of the tower is its own part holding every latch cavity, all of them
open at its underside. The bar's tower keeps a plain top face.

HOW IT IS HELD ON: a cadkit SLIDE JOINT, not screws (user -- three screws was two
too many). The collar carries two T rails (cadkit.joinery, install parallel to the
print axis, so every working face is a vertical printed wall in BOTH parts) running
in slots in the tower's top face. The slots are open at the tower's +Y face and
CLOSED at RAIL_Y0: that closed end is the seat stop. Slid on, the joint locks X
(the rails' necks and head walls), Z both ways (the lips), -Y (the stop) and every
rotation. ONE direction is left: the collar backing out +Y, and ONE M4 button head
at the +X-Y corner locks it.

WHICH WAY THE COLLAR PRINTS follows from that: a joint needs BOTH hosts printing
along the install axis, and the tower's axis is the bar's, -Y -> +Y. So the collar
builds +Y -> -Y -- the same axis, the other way up (leg_stack.BAR_COLLAR_UP). It
suits the part anyway: the pad's recess back wall, a 20 x 20 face looking -Y, is a
floor this way up.

ASSEMBLY (the latch then cannot come out):
  1. Bar upside down. Collar upside down too -- mouth face on the bench, its
     underside up -- and drop the ring into its pocket, the two springs into their
     channels in front of the lugs. Gravity holds all three in place: they rest on
     the pocket roof, which is now under them.
  2. Slide the collar on from the tower's +Y face until the rails hit the stop.
     The springs are 0.4 longer free than installed; a chamfer at the far end of
     each channel cams the coil end in as the ring settles.
  3. One M4x30 button head down through the collar into its insert in the
     tower (cadkit.fasteners.ScrewJoint -- see `screw_joint`).

THE PARTS
  * FRAME: a flat ring riding the tower's top face. Its +Y bar IS the hook: its inner
    edge stands HOOK_ENGAGE inside the tenon's +Y apex, in a pocket cut across the
    tenon. The 20 x 20 pad plate stands up from its -Y side, flush in the collar's -Y
    face and centred leg_latch.PAD_X toward +X, like the leg latch (user priority 1).
  * ONE SPRING (leg_latch's coil, at leg_latch's own installed length, so the pad
    takes the same 4.0 N to start moving) in a channel in the collar over the ring's
    +Y side, seated at BOTH ENDS: a blind CUP on the ring at one end, the sleeve's
    blind floor at the other. REST is the ring on the -Y flanks of its own pocket
    (the pocket is the ring's outline swept through the stroke, so those flanks ARE
    the ring at rest); the pad on its recess floor is the hard stop.
  * The TENON gets a POCKET (the ledge the bar hangs on) and an END CHAMFER (the
    lead-in that cams the hook out as the tenon goes in: push to connect, no button).

LOAD PATH, bar hanging: tenon pocket floor -> hook's lower face -> ring -> collar
pocket roof -> collar -> screws -> tower. The ledge is flat: a pull cannot cam it out.

FRAME: world XY about the redesigned leg's axis (leg_stack.LEG_X/LEG_Y). Heights come
from the tower's MOUTH plane, passed in, because the bar is built in its own Z and
posed by leg_stack. Radii run from the axis toward +Y (the hook side).
"""

from __future__ import annotations

import dataclasses
import math

import cadquery as cq

from cadkit.fasteners import M4, ScrewJoint
from cadkit.holes import teardrop_hole
from cadkit.joinery import PrintSpec, joint, joint_box_min
from cadkit.supports import printable_bore
from . import dimensions as D
from . import latch as LT
from . import leg_latch as LL
from . import legs as LG
from . import leg_stack as LS
from .helpers import box_at

B = D.BEAD
_S2 = math.sqrt(2.0)
CLR = LL.CLR                       # sliding clearance, as the leg latch
TEN_R = LL.TEN_R                   # 16.171 axis -> the tenon's apex
BORE_R = LL.BORE_R                 # 16.595 axis -> the mortise's apex
FACE_R = 32 * B                    # 25.6 axis -> the tower's faces (pedal_bar asserts it)
FRAME_UP = LS.PRINT_UP["bar_latch_frame"]    # ring down, pad and lugs growing up
COLLAR_UP = LS.PRINT_UP["bar_latch_collar"]  # mouth face down
COLLAR_H = 28 * B                  # 22.4 the collar's height, mouth down to the split
BAR_UP = (0.0, 1.0, 0.0)           # the bar prints -Y -> +Y

# -- the hook ------------------------------------------------------------------
HOOK_ENGAGE = 4 * B                # 3.2 how far the hook stands inside the tenon's apex
R_TIP = TEN_R - HOOK_ENGAGE        # the hook's inner edge at rest
STROKE = 5 * B                     # 4.0 press travel that clears the hook
S_MAX = STROKE + CLR               # the pad's travel to its recess floor
assert R_TIP + STROKE >= BORE_R + CLR, (
    "pressed, the hook still stands %.2f inside the mortise" % (BORE_R + CLR - R_TIP - STROKE))
HOOK_CH = 1 * B                    # 0.8 chamfer on the hook's top inner edge
TIP_HALF = LS.CHAM / 2.0 + HOOK_ENGAGE + 2 * CLR   # the hook's reach across X, with
                                   # room for the tenon to sit off-centre in its fit
# -- the ring --------------------------------------------------------------------
FRAME_H = 6 * B                    # 4.8
ARM_OUT = BORE_R + 2 * B           # 18.20 the ring's +-X outer faces. 2 beads of arm
                                   # (it only passes the pad's push to the hook -- the
                                   # hanging load goes hook -> +Y bar -> pocket roof).
                                   # It was 4: the RAILS took the other two, and they
                                   # need them more -- see RAIL_X.
Y_HOOK_OUT = TEN_R + CLR           # the +Y bar's outer face
# -- the pad ---------------------------------------------------------------------
PAD_W = LL.PAD_W                   # 20.0 across X
PAD_H = LL.PAD_FLAT                # 20.0 up from the tower's top face
PAD_T = 3 * B                      # 2.4 the plate, as the leg latch
PAD_X = LL.PAD_X                   # 3.6 toward +X, as the leg latch (user)
Y_PLATE_IN = -(FACE_R - PAD_T)     # the plate's back at rest = the ring's -Y face
RECESS_BACK = FACE_R - PAD_T - S_MAX
assert RECESS_BACK - BORE_R >= D.MIN_WALL_2P, (
    "only %.2f of collar behind the pad's recess" % (RECESS_BACK - BORE_R))
# -- the spring: ONE, at the leg's own installed length (user) ---------------------
# TWO coils made this latch feel like a different mechanism from the leg's, in both
# directions at once: half the preload (2.0 N against 4.0 -- a loose pad) and nearly
# double at the bottom of the press (22.1 N against 12.0). Doubling a spring doubles
# the force, so matching a FEEL on the same SKU means matching the COUNT and the
# installed length. One coil, installed at leg_latch's own number.
#
# WHAT IS LEFT of the difference is 14.1 N at full press against the leg's 12.0, and
# it is not tunable from here: this stroke is 4.0 where the leg's is 3.2, because the
# hook has to clear the MORTISE's bore (3.87 minimum), not just the tenon. Spending
# HOOK_ENGAGE down to 2.4 would buy the last 2 N for a third of the retention -- the
# user's trade to make, not a default.
#
# ONE coil is OFF-CENTRE, and that is survivable: 4.0 N on a 13.6 arm leans the ring
# on its pocket's +-X walls with about 1.4 N, so ~0.8 N of friction against a 4.0 N
# return, and the leg's slider already runs one coil against an off-centre pad. The
# centre is not on offer anyway -- the tenon's apex and the hook are there, and at
# x=0 the mortise leaves under 8 mm of length where the coil needs 10.4.
SPR_X = 17 * B                     # 13.6 the coil's axis, off the leg axis in X. +X --
                                   # the pad's own side (PAD_X), so the thumb's line
                                   # and the spring's are as close as the site allows
SPR_REST_L = LL.SPR_REST_L         # 10.4 installed -- THE LEG'S, so the pad's preload
                                   # is the leg's to the newton
SPR_PRESS_L = SPR_REST_L - S_MAX
assert SPR_PRESS_L >= LT.SPR_SOLID, "the spring goes solid before the pad stops"
PRELOAD_N = (LT.SPR_FREE - SPR_REST_L) * LT.SPR_RATE                  # 4.0, the leg's
PRESS_N = (LT.SPR_FREE - (SPR_REST_L - STROKE)) * LT.SPR_RATE         # 14.1
# THE TWO SEATS (user: the coil had no pocket to sit in, the way the leg's has).
#   * moving end: a CUP on the ring -- a blind bore the coil's end drops into, the
#     leg slider's seat exactly, with the locating blade still up its middle.
#   * fixed end: the channel is a SLEEVE at the coil's bore diameter for the whole
#     length, ending in a flat blind floor -- captured along its length, not butted.
CUP_D = LT.SPR_BORE_D              # 5.4 the cup's bore = the leg's spring bore
CUP_SEAT = 2 * B                   # 1.6 how far the coil's end sits into the cup
CUP_W = 9 * B                      # 7.2 across X: the bore plus a wall each side
CUP_Y0 = 14 * B                    # 11.2 the cup's FLOOR -- the coil's -Y end at rest.
                                   # A bead further +Y than the coil itself needs:
                                   # what sets it is the PEAK on the channel's -Y end
                                   # (see `collar`), whose flank runs PARALLEL to the
                                   # mortise's 45-degree flank -- the assert below
CUP_FACE = CUP_Y0 + CUP_SEAT       # 11.2 the cup's mouth
PIN_W = 2 * B                      # 1.6 the blade up the cup's middle, inside the bore
PIN_L = 3 * B                      # 2.4 how far it reaches into the coil
CHAN_R = LT.SPR_BORE_D / 2.0
CHAN_END = CUP_Y0 + SPR_REST_L     # 20.0 the sleeve's blind floor: the fixed seat
CHAN_CH = 3 * B                    # 2.4 install chamfer at the sleeve's floor end. It
                                   # has to be longer than the coil is over-long --
                                   # 1.6 now, the leg's preload, where two weak
                                   # springs only needed 0.4 -- so that the free coil
                                   # can go in at an angle and cam straight
assert CHAN_CH > LT.SPR_FREE - SPR_REST_L, "the free coil cannot cam into its sleeve"
assert CUP_FACE + S_MAX < CHAN_END, "the cup's rim hits the sleeve's floor"
# (the coil going solid is the other way this could end badly, and SPR_PRESS_L
# above is that check: 6.16 pressed against 4.8 solid)
assert FACE_R - (CHAN_END + CHAN_CH) >= D.MIN_WALL_2P, "the spring channel breaks the +Y face"
# THE WALL THAT DECIDES THIS CORNER. The channel's -Y end is peaked at 45 degrees
# (see `collar`) and the mortise's flank under it is 45 degrees the other way up, so
# the two run PARALLEL: the gap is the same all the way along, and it is NOT the
# distance along X that a naive check reads. Both are lines x + y = k.
_MORT_K = (LS.TEN_W + 2 * LS.FIT) / math.sqrt(2.0)            # 17.39, the mortise's
_PEAK_K = (SPR_X - (CUP_W / 2 + CLR)) + (CUP_Y0 - B - CLR)    # the peak's -X flank
assert (_PEAK_K - _MORT_K) / _S2 >= D.MIN_WALL_2P, (
    "the spring channel's peak runs within %.2f of the mortise"
    % ((_PEAK_K - _MORT_K) / _S2))
# -- the screws and the TRRS jack (the corners) ------------------------------------
SCREW = dataclasses.replace(M4, name="M4 button", head_recess_d=11 * B,
                            head_recess_h=3 * B)   # m4_button_screw: head 7.6 x 2.2
SCREW_L = 30.0                     # M4x30: through the collar, then SCREW_BITE into the tower
SCREW_BITE = SCREW_L - (COLLAR_H - SCREW.head_recess_h)
SCREW_END = SCREW_BITE + COLLAR_H + 1.6   # where the hole stops, 1.6 past the tip
# the head is the leg's head: ONE M4 button SKU on the instrument (user's fastener
# rule), so the numbers come from there rather than being typed again
SCREW_HEAD_D, SCREW_HEAD_H = LG.LOCK_HEAD_D, LG.LOCK_HEAD_H
TRRS_BORE_D = 14 * B               # 11.2 the CA-354S body way, in the BAR
TRRS_COLLAR_D = 13 * B             # 10.4 -- the COLLAR'S share of that way is one bead
                                   # tighter on the same 9.6 body (0.4 a side, still a
                                   # drop fit). The corner cannot afford the wider one:
                                   # this part peaks its bores toward -Y, and 11.2's
                                   # peak walks the jack so far in off the -Y face that
                                   # the ring's own corner web falls to 1.35.
assert SCREW_BITE >= M4.anchor_min_wall, (
    "the screw bites %.1f, under the insert's own depth + min bite" % SCREW_BITE)


def _corner_xy(sx: float, bore_d: float, peak_d: float = None):
    """A -Y corner bore as deep into the corner as the WALLS allow.

    Both of these are upright bores in a part that builds toward -Y, so cadkit
    peaks them TOWARD -Y -- and a 45-degree teardrop's apex stands r*sqrt(2) off
    the axis, half again the bore's own radius. Sitting them on the diagonal by a
    single centre distance hid that: the peaks stood 0.42 PROUD OF THE -Y FACE
    (user caught it). So each axis gets its own rule -- the circle off the +-X
    face, the PEAK off the -Y face -- which walks the bore up the -Y face rather
    than in along the diagonal, and so costs the ring almost nothing (the pocket's
    corner clips below are measured off these same points).
    """
    r = bore_d / 2.0
    tip = (r if peak_d is None else peak_d / 2.0) * _S2
    return (sx * (FACE_R - D.MIN_WALL_2P - r), -(FACE_R - D.MIN_WALL_2P - tip))


# the head recess is the widest thing on the screw's axis, so it sets both rules
SCREW_XY = _corner_xy(1.0, SCREW.head_recess_d)
# the jack: the +-X rule takes the BAR's wider way (the tower holds that one), the
# -Y rule the COLLAR's narrower one (the collar holds the peak)
TRRS_XY = _corner_xy(-1.0, TRRS_BORE_D, TRRS_COLLAR_D)
SCREW_CORNERS = (SCREW_XY,)        # ONE (user). The rails took the two +Y corners
                                   # and the TRRS jack has the fourth; this one locks
                                   # the single direction the rails leave open.
# -- the rails: what holds the collar on, with the screw ---------------------------
# A cadkit SLIDE JOINT. Both hosts print along Y -- the tower with the bar, the collar
# the other way up -- which is the plan-profile case: the joint lies in the X-Z plane
# and every working face of it is a vertical printed WALL in both parts. The slots are
# open at the tower's +Y face and closed at RAIL_Y0; the tower's build reaches that
# closed end FIRST, so the stop face is a floor, and the collar therefore seats
# travelling -Y.
RAIL_W = 6 * B                     # 4.8 across X: the room, not the profile -- the
RAIL_D = 5 * B                     # 4.0 into the tower. cadkit sizes the T inside.
                                   # BOTH are the QUALITY box (joint_box_min below,
                                   # asserted): give the site less and the library
                                   # does not fail, it QUIETLY DEGRADES the profile
                                   # toward its one-bead floor -- 4.0 x 3.2 built a
                                   # 1.2 shoulder and a 1.45 head bar (user caught
                                   # it). Room in, segments out: check the segments.
RAIL_Y0 = -7 * B                   # -5.6 the slots' closed end: the SEAT STOP. Not the
                                   # -Y face, because the two -Y corners are spoken for
                                   # (the screw, the TRRS way) -- and not merely clear
                                   # of their BORES either: in the TOWER those bores
                                   # are peaked toward +Y, straight at this end of the
                                   # slots, so the wall that decides RAIL_Y0 is the one
                                   # to a teardrop's 45-degree FLANK (measured, not
                                   # derived -- see the verify script's wall probes)
_PS_COLLAR = PrintSpec(nozzle=D.NOZZLE_D, material="PETG-GF", facing="up")
_PS_TOWER = PrintSpec(nozzle=D.NOZZLE_D, material="PETG-GF", facing="down")
RAIL_STROKE = FACE_R - RAIL_Y0     # 33.6 how far the collar slides to seat
RAIL = joint(width=RAIL_W, length=RAIL_STROKE, depth=RAIL_D,
             tenon=_PS_COLLAR, mortise=_PS_TOWER, install="+z")
_RAIL_NECK = RAIL.dims["neck"] / 2.0
_RAIL_HEAD = RAIL.dims["head"] / 2.0 + RAIL.clearance
# WHERE the rails sit is not a free number: the site is ASYMMETRIC (user). Inboard
# the tower is solid -- the head may grow that way as far as it likes (its nearest
# obstacle, the mortise, is 2.0 off) -- and the only thing that stops the joint
# going further inboard is the COLLAR's own wall between the ring's pocket and the
# NECK. Outboard, the +-X face stops the HEAD. So the rail's line is bounded by a
# different feature on each side, and it sits in the middle of what they leave.
_RAIL_IN = (ARM_OUT + CLR) + D.MIN_WALL_2P + _RAIL_NECK      # 20.84
_RAIL_OUT = FACE_R - D.MIN_WALL_2P - _RAIL_HEAD              # 21.45
assert _RAIL_IN <= _RAIL_OUT, (
    "no room for a rail: the ring's pocket and the outer face leave %.2f"
    % (_RAIL_OUT - _RAIL_IN))
RAIL_X = (_RAIL_IN + _RAIL_OUT) / 2.0    # 21.14 each rail's line, off the axis in X
assert RAIL.height <= COLLAR_H - D.MIN_WALL_2P
_QW, _QD = joint_box_min(_PS_COLLAR, _PS_TOWER, install="+z", quality=True)
assert RAIL_W >= _QW - 1e-9 and RAIL_D >= _QD - 1e-9, (
    "the rail site is under cadkit's quality box (%.2f x %.2f): the profile degrades "
    "silently" % (_QW, _QD))
_RAIL_SEG = min(RAIL.dims["neck"], (RAIL.dims["head"] - RAIL.dims["neck"]) / 2.0,
                RAIL.dims["depth_used"] - RAIL.dims["lip"], RAIL.dims["lip"])
assert _RAIL_SEG >= D.MIN_WALL_2P - 1e-9, (
    "the rail's thinnest printed segment is %.2f" % _RAIL_SEG)
assert SCREW_XY[1] + SCREW.head_recess_d / 2 + D.MIN_WALL_2P <= RAIL_Y0, (
    "the rails run into the screw's corner")
assert TRRS_XY[1] + TRRS_BORE_D / 2 + D.MIN_WALL_2P <= RAIL_Y0, (
    "the rails run into the TRRS way's corner (%.2f)"
    % (TRRS_XY[1] + TRRS_BORE_D / 2 + D.MIN_WALL_2P))

# -- the tenon's lead-in -----------------------------------------------------------
LEAD_DEG = 20.0                    # from the push axis: shallow, because the ring's
                                   # own sliding friction is in series with it
TIP_RELIEF = 1 * B
POCKET_TILT_DEG = 10.0
LIP_MIN = 4 * B                    # tenon left between its lead-in and the pocket

# The ring's corners are cut on the diagonals to clear what lives there; the collar's
# pocket for it is the ring swept through its stroke. Each cut is the line |x|+|y| = K.
_WEB = D.MIN_WALL_2P
# Each corner clip keeps the ring _WEB clear of its bore. The clip line is at 45
# degrees, and so is the flank of the bore's teardrop peak -- and that flank is
# TANGENT to the bore's own circle, wherever the bore sits. So the peak costs the
# clip nothing: the circle's radius is still the whole story here.
K_MXMY = (abs(TRRS_XY[0]) + abs(TRRS_XY[1])                                 # -X-Y (jack)
          - (TRRS_COLLAR_D / 2 + _WEB) * _S2) - CLR * _S2   # the ring meets the
                                                            # COLLAR's bore, not the bar's
# the screw's hole is NOT its shank where the ring passes it: the insert pocket's
# mouth sits on the split, and cadkit flares a 45-degree step cone up out of it --
# into the collar's lowest 0.8, exactly the band the ring runs in. So the clip is
# measured off the POCKET (the hole's widest feature here), not the shank; sized off
# the shank it left 1.05 (measured, verify_bar_walls.py).
K_PXMY = (abs(SCREW_XY[0]) + abs(SCREW_XY[1])                               # +X-Y (screw)
          - (max(SCREW.shaft_clr_d, SCREW.insert_pilot_d) / 2 + _WEB) * _S2) - CLR * _S2
_OPEN_DIAG = (LS.TEN_W + 2 * LS.FIT) / 2 * _S2 + S_MAX + CLR   # the opening's -Y diagonals
for _k, _nm in ((K_MXMY, "-X-Y"), (K_PXMY, "+X-Y")):
    assert (_k - _OPEN_DIAG) / _S2 >= D.MIN_WALL_2P, (
        "the ring's %s corner is %.2f wide between the mortise's opening and the clip"
        % (_nm, (_k - _OPEN_DIAG) / _S2))


def planes(z_mouth: float) -> dict:
    """Every height, from the tower's mouth plane."""
    z0 = z_mouth - COLLAR_H                        # the split: the tower's top face
    zr = z0 + FRAME_H                              # the ring's top
    z_s = zr + CLR + LT.SPR_OD / 2.0               # coil axes: coils lying on the ring
    return dict(z0=z0, z_ring_top=zr, z_pocket_top=zr + 2 * CLR, z_s=z_s,
                z_tb=z_mouth - LS.ENGAGE)           # the seated tenon's bottom end


# -- 2-D helpers (axis-relative) ---------------------------------------------------
def _xy_prism(pts, z0: float, z1: float) -> cq.Workplane:
    wp = [(LS.LEG_X + x, LS.LEG_Y + y) for x, y in pts]
    return cq.Workplane("XY").workplane(offset=z0).polyline(wp).close().extrude(z1 - z0)


def _yz_prism(pts, x0: float, x1: float) -> cq.Workplane:
    plane = cq.Plane(origin=(LS.LEG_X + x0, LS.LEG_Y, 0.0), xDir=(0, 1, 0), normal=(1, 0, 0))
    return cq.Workplane(plane).polyline(pts).close().extrude(x1 - x0)


def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return box_at(x1 - x0, y1 - y0, z1 - z0, x=LS.LEG_X + (x0 + x1) / 2,
                  y=LS.LEG_Y + (y0 + y1) / 2, z=(z0 + z1) / 2)


def _clip(poly, a, b, c):
    """Convex polygon clipped to a*x + b*y <= c."""
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if fp * fq < 0:
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def _hull(pts):
    pts = sorted(set((round(x, 9), round(y, 9)) for x, y in pts))
    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (p[1] - out[-2][1])
                                     - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out
    lo, hi = half(pts), half(list(reversed(pts)))
    return lo[:-1] + hi[:-1]


def _grow(poly, d):
    """A convex polygon's edges pushed out by d (sharp corners)."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1]
               for i in range(n))
    s = 1.0 if area > 0 else -1.0
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        ex, ey = x1 - x0, y1 - y0
        L = math.hypot(ex, ey)
        nx, ny = s * ey / L, -s * ex / L
        lines.append((nx, ny, nx * x0 + ny * y0 + d))
    out = []
    for i in range(n):
        a1, b1, c1 = lines[i - 1]
        a2, b2, c2 = lines[i]
        det = a1 * b2 - a2 * b1
        out.append(((c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det))
    return out


def _octagon(w: float):
    """The leg's 45-degree octagon of `w` across flats."""
    h, c = w / 2.0, LS.CHAM / _S2
    sq = [(h - c, h), (-(h - c), h), (-h, h - c), (-h, -(h - c)),
          (-(h - c), -h), (h - c, -h), (h, -(h - c)), (h, h - c)]
    k = math.sqrt(0.5)
    return [(k * (x - y), k * (x + y)) for x, y in sq]


def _ring_outline():
    poly = [(-ARM_OUT, Y_PLATE_IN), (ARM_OUT, Y_PLATE_IN), (ARM_OUT, Y_HOOK_OUT),
            (-ARM_OUT, Y_HOOK_OUT)]
    for a, b, c in ((-1, -1, K_MXMY), (1, -1, K_PXMY)):   # the +Y corners are square
                                                          # now: no screws up there
        poly = _clip(poly, a, b, c)
    return poly


def _opening(z0: float, z1: float) -> cq.Workplane:
    """The ring's inside: the mortise's octagon swept toward -Y by the stroke (so the
    pressed ring still clears the tenon), cut off at the hook's edge."""
    o = _octagon(LS.TEN_W + 2 * LS.FIT)
    sweep = S_MAX + CLR
    hull = _hull(o + [(x, y - sweep) for x, y in o])
    return _xy_prism(_clip(hull, 0, 1, R_TIP), z0, z1)


def _corner(d, sx, sy):
    return (sx * d / _S2, sy * d / _S2)


# -- the moving part -----------------------------------------------------------------
def frame(z_mouth: float) -> cq.Workplane:
    """The yoke AT REST: hook in, pad flush, lugs on their stops."""
    p = planes(z_mouth)
    z0, zr = p["z0"], p["z_ring_top"]
    f = _xy_prism(_ring_outline(), z0, zr).cut(_opening(z0 - 1.0, zr + 1.0))
    # the hook's top inner edge, chamfered so the tenon's lead-in meets a slope
    f = f.cut(_yz_prism([(R_TIP - 0.01, zr + 0.01), (R_TIP + HOOK_CH, zr + 0.01),
                         (R_TIP - 0.01, zr - HOOK_CH)], -TIP_HALF, TIP_HALF))
    # the pad plate, standing up from the ring's -Y face, flush with the collar
    f = f.union(_box(PAD_X - PAD_W / 2, PAD_X + PAD_W / 2, -FACE_R, Y_PLATE_IN,
                     z0, z0 + PAD_H))
    # the spring's CUP, standing on the ring: a blind bore the coil's end sits in
    # (the leg slider's seat), with a BLADE up its middle inside the coil's bore. A
    # blade and not a round post: a post would start in mid-air in this part's
    # print, where the blade's underside rises at 45 degrees off the cup's floor.
    zs = p["z_s"]
    f = f.union(_box(SPR_X - CUP_W / 2, SPR_X + CUP_W / 2, CUP_Y0 - B, CUP_FACE,
                     zr - 0.01, zs + CUP_D / 2.0 * _S2 + B))
    f = f.cut(teardrop_hole(CUP_D, CUP_SEAT + 0.01,
                            (LS.LEG_X + SPR_X, LS.LEG_Y + CUP_FACE + 0.01, zs),
                            (0.0, -1.0, 0.0), FRAME_UP))
    ri = LT.SPR_ID / 2.0 - CLR                     # inside the coil's bore
    f = f.union(_yz_prism([(CUP_Y0 - 0.01, zs - ri), (CUP_Y0 + PIN_L, zs - ri + PIN_L),
                           (CUP_Y0 + PIN_L, zs + ri), (CUP_Y0 - 0.01, zs + ri)],
                          SPR_X - PIN_W / 2, SPR_X + PIN_W / 2))
    return f


def springs(z_mouth: float):
    """The coil at rest, from the cup's floor to the sleeve's: drawn as a TUBE,
    because the cup's blade sits inside its bore."""
    p = planes(z_mouth)
    base = cq.Vector(LS.LEG_X + SPR_X, LS.LEG_Y + CUP_Y0, p["z_s"])
    tube = cq.Solid.makeCylinder(LT.SPR_OD / 2.0, SPR_REST_L, base, cq.Vector(0, 1, 0)).cut(
        cq.Solid.makeCylinder(LT.SPR_ID / 2.0, SPR_REST_L + 2.0, base - cq.Vector(0, 1, 0),
                              cq.Vector(0, 1, 0)))
    return [cq.Workplane("XY").add(tube)]


def _rail_pose(w: cq.Workplane, sx: float, z0: float, y0: float) -> cq.Workplane:
    """A joint solid from its own frame onto a rail line. cadkit draws the joint
    with the install axis along +Z, the tenon rising +X off the mating plane at
    x=0 and its width across Y; here the install axis is -Y (the collar slides on
    toward -Y), the rise is -Z (down out of the collar's underside) and the width
    is X. `y0` is where the prism STARTS -- its open end."""
    return (w.rotate((0, 0, 0), (0, 0, 1), -90).rotate((0, 0, 0), (1, 0, 0), 90)
            .translate((LS.LEG_X + sx * RAIL_X, LS.LEG_Y + y0, z0)))


def rails(z_mouth: float) -> cq.Workplane:
    """The collar's two rails, fused into its underside."""
    z0 = planes(z_mouth)["z0"]
    out = None
    for sx in (-1.0, 1.0):
        t = _rail_pose(RAIL.tenon(root=1.0), sx, z0, FACE_R)
        out = t if out is None else out.union(t)
    return out


def rail_slots(z_mouth: float) -> cq.Workplane:
    """Their slots in the tower's top face: open (with overshoot) at the +Y face,
    closed CLR past the rails' ends -- that far end is the seat stop."""
    z0 = planes(z_mouth)["z0"]
    out = None
    for sx in (-1.0, 1.0):
        m = _rail_pose(RAIL.mortise(drop=2.0, length=RAIL_STROKE + 2.0 + CLR),
                       sx, z0, FACE_R + 2.0)
        out = m if out is None else out.union(m)
    return out


def screws(z_mouth: float):
    """The collar's screw: (point on the mouth face, axis down)."""
    return [((LS.LEG_X + x, LS.LEG_Y + y, z_mouth), (0.0, 0.0, -1.0))
            for x, y in SCREW_CORNERS]


def screw_joint(z_mouth: float) -> ScrewJoint:
    """THE screw, defined once for both parts (cadkit.fasteners.ScrewJoint): head
    recessed in the collar's mouth face, clearance down through the collar, and the
    INSERT in the tower with its pocket mouth on the split -- the face the insert is
    pressed into. Each part cuts `cutter(its own print_up)`, so the one hole comes
    out teardropped for -Y in the collar and for +Y in the tower, and the assembly
    draws the screw and the insert from the same numbers."""
    (pt, ax), = screws(z_mouth)
    return ScrewJoint(SCREW, pt, ax, SCREW_L, insert_at=COLLAR_H, end_at=SCREW_END,
                      head_d=SCREW_HEAD_D, head_h=SCREW_HEAD_H,
                      recess=SCREW.head_recess_h)


def screw_dummies(z_mouth: float):
    """The screw seated and its insert in the tower, for the assembly."""
    return screw_joint(z_mouth).dummies("bar_latch_screw", "bar_latch_insert")


# -- the collar ----------------------------------------------------------------------
def collar(z_mouth: float, trrs_top: float) -> cq.Workplane:
    """The top COLLAR_H of the bar's tower, printed on its own mouth face. Every latch
    cavity opens at its underside. `trrs_top` is where the bar's TRRS jack way ends
    (world z): the way continues up into the collar, which closes it."""
    p = planes(z_mouth)
    z0 = p["z0"]
    c = box_at(2 * FACE_R, 2 * FACE_R, COLLAR_H, x=LS.LEG_X, y=LS.LEG_Y,
               z=z0 + COLLAR_H / 2.0)
    c = c.cut(LS.mortise_cutter(z0 - 1.0, z_mouth + 1.0))
    # the mortise's -Y apex is a 1.6 flat looking +Y: a ceiling in THIS part's print
    # (the bar peaks its +Y one for the same reason, the other way up). Peak it at
    # 45 degrees -- only more clearance over the tenon's apex.
    _br = (LS.TEN_W + 2 * LS.FIT) / _S2 - LS.CHAM / 2.0
    _h = LS.CHAM / 2.0 + 0.05
    c = c.cut(cq.Workplane("XY").workplane(offset=z0 - 1.0)
              .polyline([(LS.LEG_X - _h, LS.LEG_Y - _br + 0.05),
                         (LS.LEG_X + _h, LS.LEG_Y - _br + 0.05),
                         (LS.LEG_X, LS.LEG_Y - _br - _h)])
              .close().extrude((z_mouth + 1.0) - (z0 - 1.0)))
    # the ring's pocket: its outline swept through the stroke, + CLR
    ring = _ring_outline()
    swept = _hull(ring + [(x, y + S_MAX) for x, y in ring])
    c = c.cut(_xy_prism(_grow(swept, CLR), z0 - 1.0, p["z_pocket_top"]))
    # the pad's recess, to the plate's full travel: its floor is the hard stop
    c = c.cut(_box(PAD_X - PAD_W / 2 - CLR, PAD_X + PAD_W / 2 + CLR, -(FACE_R + 1.0),
                   -RECESS_BACK, z0 - 1.0, z0 + PAD_H + CLR))
    assert z_mouth - (z0 + PAD_H + CLR) >= D.MIN_WALL_2P, "the pad's recess breaks the mouth"
    # THE SPRING'S CHANNEL -- one of them now, and three things in a line: a box the
    # CUP travels in, the SLEEVE the coil runs in at its own bore diameter, and the
    # sleeve's flat blind floor, which is the coil's fixed seat. All of it opens at
    # the collar's underside: a closed bottom would be a ceiling in this print, and
    # the coil and the ring are dropped in from that side at assembly.
    zs = p["z_s"]
    x = SPR_X
    y_cup0 = CUP_Y0 - B - CLR                       # the void's -Y end
    y_cup1 = CUP_FACE + S_MAX + CLR                 # the cup's mouth at FULL PRESS
    cup_hw = CUP_W / 2.0 + CLR
    c = c.cut(_box(x - cup_hw, x + cup_hw, y_cup0, y_cup1, z0 - 1.0,
                   zs + CUP_D / 2.0 * _S2 + B + CLR))
    c = c.cut(_box(x - CHAN_R, x + CHAN_R, y_cup1 - 0.01, CHAN_END, z0 - 1.0, zs))
    c = c.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        CHAN_R, CHAN_END - (y_cup1 - 0.01),
        cq.Vector(LS.LEG_X + x, LS.LEG_Y + y_cup1 - 0.01, zs), cq.Vector(0, 1, 0))))
    # the floor end's lower edge, chamfered: it cams the over-long free coil up into
    # the sleeve as the ring settles
    c = c.cut(_yz_prism([(CHAN_END - 0.01, z0 - 0.01), (CHAN_END + CHAN_CH, z0 - 0.01),
                         (CHAN_END - 0.01, z0 + CHAN_CH)], x - CHAN_R, x + CHAN_R))
    # its -Y end. BELOW the pocket's roof there is no end at all -- channel and
    # pocket are one void. ABOVE it a flat end would be a wall looking +Y, a ceiling
    # in this print, so it is PEAKED IN PLAN: two 45-degree flanks meeting a half
    # width further -Y. That way round the end's material appears first at the
    # channel's own side walls and closes inward a layer at a time. (A 45 ramp in Z
    # fails here: its foot lands on the pocket's roof plane, where there is nothing
    # yet to grow from -- the layer check caught that one.) Nothing stops against
    # this end: the ring's rest stop is the POCKET's own -Y flanks, which ARE the
    # ring's outline at rest.
    c = c.cut(_xy_prism([(x - cup_hw, y_cup0 + 0.01), (x + cup_hw, y_cup0 + 0.01),
                         (x, y_cup0 - cup_hw)],
                        z0 - 1.0, zs + CUP_D / 2.0 * _S2 + B + CLR))
    # the screw: one hole, defined once for collar and tower alike
    c = c.cut(screw_joint(z_mouth).cutter(COLLAR_UP))
    # the RAILS: what actually holds the collar on (the screw only stops it
    # sliding back off). They stand on the underside, outboard of everything.
    c = c.union(rails(z_mouth))
    # the TRRS jack way's upper end
    tx, ty = TRRS_XY
    c = c.cut(printable_bore(TRRS_COLLAR_D, trrs_top - (z0 - 1.0),
                             (LS.LEG_X + tx, LS.LEG_Y + ty, z0 - 1.0), (0, 0, 1), COLLAR_UP))
    return c


# -- what the tower gives up ---------------------------------------------------------
def tower_cut(z_mouth: float) -> cq.Workplane:
    """Cut in the bar's tower: the two RAIL SLOTS the collar slides into, and the
    screw's end of its joint -- the insert's pocket, mouthed on the split, and the
    clearance past it. Upright, so sideways to the bar's print: cadkit shapes the
    bore and steps the pocket for that."""
    return rail_slots(z_mouth).union(screw_joint(z_mouth).cutter(BAR_UP))


# -- what the tenon gives up ---------------------------------------------------------
def tenon_cut(z_mouth: float) -> cq.Workplane:
    """Cut in the adjust tenon, seated with its end on the mortise floor: the
    retention POCKET across its +Y apex at the ring's height, and the LEAD-IN chamfer
    on its end that cams the hook out on the way in."""
    p = planes(z_mouth)
    t = math.tan(math.radians(POCKET_TILT_DEG))
    # the pocket's back, 2 CLR behind the hook's edge at its +X reach and DEEPENING
    # toward -X: the tilt turns its normal away from the tenon's bed flat (+X+Y)
    yb = R_TIP - 2 * CLR
    xa = TIP_HALF
    back = [(-40.0, yb - (40.0 + xa) * t), (40.0, yb + (40.0 - xa) * t),
            (40.0, 40.0), (-40.0, 40.0)]
    z_lo = p["z0"] - CLR
    pocket = _xy_prism(back, z_lo, p["z_pocket_top"])
    tl = math.tan(math.radians(LEAD_DEG))
    r0 = R_TIP - TIP_RELIEF
    L = (TEN_R + 1.0 - r0) / tl
    zt = p["z_tb"]
    lead = _yz_prism([(r0 - tl, zt - 1.0), (r0 + tl * L, zt + L), (40.0, zt + L),
                      (40.0, zt - 1.0)], -40.0, 40.0)
    assert z_lo - (zt + L) >= LIP_MIN, (
        "only %.2f of tenon between the lead-in and the pocket" % (z_lo - (zt + L)))
    return pocket.union(lead)
