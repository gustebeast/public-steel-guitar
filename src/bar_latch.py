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
  3. One M4x30 button head down through the collar into the tower.

THE PARTS
  * FRAME: a flat ring riding the tower's top face. Its +Y bar IS the hook: its inner
    edge stands HOOK_ENGAGE inside the tenon's +Y apex, in a pocket cut across the
    tenon. The 20 x 20 pad plate stands up from its -Y side, flush in the collar's -Y
    face and centred leg_latch.PAD_X toward +X, like the leg latch (user priority 1).
  * TWO SPRINGS (leg_latch's coil) in channels in the collar over the ring's +Y
    side, pushed by lugs on the ring toward -Y. REST is the ring on the -Y flanks of
    its own pocket (the pocket is the ring's outline swept through the stroke, so
    those flanks ARE the ring at rest); the pad on its recess floor is the hard stop.
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

from cadkit.fasteners import M4, anchor_cutter, head_bore_cutter
from cadkit.joinery import PrintSpec, joint
from cadkit.supports import printable_bore
from . import dimensions as D
from . import latch as LT
from . import leg_latch as LL
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
# -- the springs -----------------------------------------------------------------
SPR_X = 16 * B                     # 12.8 each coil's axis, off the leg axis in X
LUG_Y0 = 12 * B                    # 9.6 each lug's -Y face at rest = its channel's end
LUG_L = 2 * B                      # 1.6 lug length along Y
LUG_W = 4 * B                      # 3.2 lug width across X
PIN_W = 2 * B                      # 1.6 the lug's locating blade, inside the coil's bore
PIN_L = 3 * B                      # 2.4 how far the blade reaches into the coil
SPR_REST_L = LT.SPR_FREE - 0.4     # 11.6 installed
SPR_PRESS_L = SPR_REST_L - S_MAX
assert SPR_PRESS_L >= LT.SPR_SOLID, "a spring goes solid before the pad stops"
PRELOAD_N = 2 * (LT.SPR_FREE - SPR_REST_L) * LT.SPR_RATE
PRESS_N = 2 * (LT.SPR_FREE - (SPR_REST_L - STROKE)) * LT.SPR_RATE
CHAN_R = LT.SPR_BORE_D / 2.0
CHAN_END = LUG_Y0 + LUG_L + SPR_REST_L
CHAN_CH = 1 * B                    # 0.8 install chamfers at the channel ends (> the 0.4
                                   # the free coil is too long)
assert CHAN_CH > LT.SPR_FREE - SPR_REST_L
assert FACE_R - (CHAN_END + CHAN_CH) >= D.MIN_WALL_2P, "a spring channel breaks the +Y face"
_flank = (LS.TEN_W + 2 * LS.FIT) / math.sqrt(2.0) - LUG_Y0   # mortise |x| at the channel
assert SPR_X - CHAN_R - _flank >= D.MIN_WALL_2P, (
    "a spring channel leaves %.2f to the mortise" % (SPR_X - CHAN_R - _flank))
# ... and that one number covers the channel's PEAKED end too (see `collar`),
# which reaches CHAN_R further -Y on 45-degree flanks: the mortise's flank at that
# corner is 45 degrees the other way, so peak and mortise run PARALLEL, the same
# 2.31 apart the whole way down.
# -- the screws and the TRRS jack (the corners) ------------------------------------
SCREW = dataclasses.replace(M4, name="M4 button", head_recess_d=11 * B,
                            head_recess_h=3 * B)   # m4_button_screw: head 7.6 x 2.2
SCREW_D = 35 * B                   # 28.0 axis -> each screw, along a diagonal
SCREW_CORNERS = ((1, -1),)         # ONE (user). The rails took the two +Y corners
                                   # and the TRRS jack has the fourth; this one locks
                                   # the single direction the rails leave open.
SCREW_L = 30.0                     # M4x30: through the collar, then SCREW_BITE into the tower
SCREW_BITE = SCREW_L - (COLLAR_H - SCREW.head_recess_h)
TRRS_D = 32 * B                    # 25.6 axis -> the TRRS jack way, -X-Y diagonal
TRRS_BORE_D = 14 * B               # 11.2 the CA-354S body way
TRRS_CORNER = (-1, -1)
assert SCREW_BITE >= M4.anchor_min_wall, "the collar screws bite %.1f" % SCREW_BITE
# -- the rails: what holds the collar on, with the screw ---------------------------
# A cadkit SLIDE JOINT. Both hosts print along Y -- the tower with the bar, the collar
# the other way up -- which is the plan-profile case: the joint lies in the X-Z plane
# and every working face of it is a vertical printed WALL in both parts. The slots are
# open at the tower's +Y face and closed at RAIL_Y0; the tower's build reaches that
# closed end FIRST, so the stop face is a floor, and the collar therefore seats
# travelling -Y.
RAIL_X = 27 * B                    # 21.6 each rail's line, off the axis in X. The
                                   # strip between the ring's pocket and the outer
                                   # face is all the room there is (asserted below --
                                   # it is why the ring gave up two beads of arm)
RAIL_W = 5 * B                     # 4.0 across X: the room, not the profile -- the
RAIL_D = 4 * B                     # 3.2 into the tower. cadkit sizes the T inside
RAIL_Y0 = -10 * B                  # -8.0 the slots' closed end: the SEAT STOP. Not the
                                   # -Y face, because the two -Y corners are spoken
                                   # for (the screw, the TRRS way) -- asserted below
_PS_COLLAR = PrintSpec(nozzle=D.NOZZLE_D, material="PETG-GF", facing="up")
_PS_TOWER = PrintSpec(nozzle=D.NOZZLE_D, material="PETG-GF", facing="down")
RAIL_STROKE = FACE_R - RAIL_Y0     # 33.6 how far the collar slides to seat
RAIL = joint(width=RAIL_W, length=RAIL_STROKE, depth=RAIL_D,
             tenon=_PS_COLLAR, mortise=_PS_TOWER, install="+z")
_RAIL_NECK = RAIL.dims["neck"] / 2.0
_RAIL_HEAD = RAIL.dims["head"] / 2.0 + RAIL.clearance
assert RAIL_X - _RAIL_NECK - (ARM_OUT + CLR) >= D.MIN_WALL_2P, (
    "only %.2f of collar between the ring's pocket and a rail"
    % (RAIL_X - _RAIL_NECK - (ARM_OUT + CLR)))
assert FACE_R - (RAIL_X + _RAIL_HEAD) >= D.MIN_WALL_2P, (
    "only %.2f of tower outside a slot" % (FACE_R - (RAIL_X + _RAIL_HEAD)))
assert RAIL.height <= COLLAR_H - D.MIN_WALL_2P
assert -SCREW_D / _S2 - (SCREW.head_recess_d / 2 + D.MIN_WALL_2P) <= RAIL_Y0, (
    "the rails run into the screw's corner")
assert -TRRS_D / _S2 - (TRRS_BORE_D / 2 + D.MIN_WALL_2P) <= RAIL_Y0, (
    "the rails run into the TRRS way's corner")

# -- the tenon's lead-in -----------------------------------------------------------
LEAD_DEG = 20.0                    # from the push axis: shallow, because the ring's
                                   # own sliding friction is in series with it
TIP_RELIEF = 1 * B
POCKET_TILT_DEG = 10.0
LIP_MIN = 4 * B                    # tenon left between its lead-in and the pocket

# The ring's corners are cut on the diagonals to clear what lives there; the collar's
# pocket for it is the ring swept through its stroke. Each cut is the line |x|+|y| = K.
_WEB = D.MIN_WALL_2P
K_MXMY = (TRRS_D - TRRS_BORE_D / 2 - _WEB) * _S2 - CLR * _S2                # -X-Y (jack)
K_PXMY = (SCREW_D - SCREW.shaft_clr_d / 2 - _WEB) * _S2 - CLR * _S2         # +X-Y (screw)
_OPEN_DIAG = (LS.TEN_W + 2 * LS.FIT) / 2 * _S2 + S_MAX + CLR   # the opening's -Y diagonals
assert (K_MXMY - _OPEN_DIAG) / _S2 >= D.MIN_WALL_2P, "the ring's -X-Y corner is too thin"


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
    # the spring lugs, standing on the ring, each with a BLADE the coil is slipped over
    # at assembly. Its underside rises at 45 degrees off the lug, so it grows out of
    # the lug in the print rather than hanging from its tip.
    ri = LT.SPR_ID / 2.0 - CLR                     # inside the coil's bore
    for sx in (-1.0, 1.0):
        x = sx * SPR_X
        f = f.union(_box(x - LUG_W / 2, x + LUG_W / 2,
                         LUG_Y0, LUG_Y0 + LUG_L, zr - 0.01, p["z_s"] + LT.SPR_OD / 2 - B))
        y0, zs = LUG_Y0 + LUG_L - 0.01, p["z_s"]
        f = f.union(_yz_prism([(y0, zs - ri), (y0 + PIN_L, zs - ri + PIN_L),
                               (y0 + PIN_L, zs + ri), (y0, zs + ri)],
                              x - PIN_W / 2, x + PIN_W / 2))
    return f


def springs(z_mouth: float):
    """The two coils at rest, from each lug's +Y face to its channel's end: drawn as
    TUBES, because the lug's pin sits inside the coil's bore."""
    p = planes(z_mouth)
    out = []
    for sx in (-1.0, 1.0):
        base = cq.Vector(LS.LEG_X + sx * SPR_X, LS.LEG_Y + LUG_Y0 + LUG_L, p["z_s"])
        tube = cq.Solid.makeCylinder(LT.SPR_OD / 2.0, SPR_REST_L, base, cq.Vector(0, 1, 0)).cut(
            cq.Solid.makeCylinder(LT.SPR_ID / 2.0, SPR_REST_L + 2.0, base - cq.Vector(0, 1, 0),
                                  cq.Vector(0, 1, 0)))
        out.append(cq.Workplane("XY").add(tube))
    return out


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
    """The three collar screws: (point on the mouth face, axis down)."""
    return [((LS.LEG_X + x, LS.LEG_Y + y, z_mouth), (0.0, 0.0, -1.0))
            for x, y in (_corner(SCREW_D, *c) for c in SCREW_CORNERS)]


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
    # the spring channels: an arch over each coil, open all the way down through the
    # collar's underside (a closed bottom would be a ceiling in this print, and would
    # stop the collar going on over the coils); each one's -Y end is its lug's rest
    # stop. The ends' lower edges are chamfered: lowering the collar at assembly, they
    # cam the free coil's end and the lug together.
    zb = p["z_pocket_top"]
    for sx in (-1.0, 1.0):
        x = sx * SPR_X
        c = c.cut(_box(x - CHAN_R, x + CHAN_R, LUG_Y0, CHAN_END, z0 - 1.0, p["z_s"]))
        c = c.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            CHAN_R, CHAN_END - LUG_Y0,
            cq.Vector(LS.LEG_X + x, LS.LEG_Y + LUG_Y0, p["z_s"]), cq.Vector(0, 1, 0))))
        c = c.cut(_yz_prism([(CHAN_END - 0.01, z0 - 0.01), (CHAN_END + CHAN_CH, z0 - 0.01),
                             (CHAN_END - 0.01, z0 + CHAN_CH)], x - CHAN_R, x + CHAN_R))
        # its -Y end. BELOW the pocket's roof there is no end at all -- channel and
        # pocket are one void. ABOVE it a flat end would be a wall looking +Y, a
        # ceiling in this print, so it is PEAKED IN PLAN: two 45-degree flanks
        # meeting CHAN_R further -Y. That way round, the end's material appears
        # first at the channel's own side walls and closes inward a layer at a
        # time. (A 45 ramp in Z fails here: its foot lands on the pocket's roof
        # plane, where there is nothing yet to grow from -- the check caught it.)
        # Nothing stops against this end: the ring's rest stop is the POCKET's own
        # -Y flanks (the pocket IS the ring's outline swept through the stroke, so
        # its -Y face is the ring at rest).
        c = c.cut(_xy_prism([(x - CHAN_R, LUG_Y0 + 0.01), (x + CHAN_R, LUG_Y0 + 0.01),
                             (x, LUG_Y0 - CHAN_R)],
                            z0 - 1.0, p["z_s"] + CHAN_R + 0.01))
    # the screws: button head recess at the mouth, clearance on down, via cadkit
    for (pt, axis) in screws(z_mouth):
        c = c.cut(head_bore_cutter(SCREW, pt, axis, COLLAR_H + 1.0, overshoot=1.0,
                                   print_up=COLLAR_UP))
    # the RAILS: what actually holds the collar on (the screw only stops it
    # sliding back off). They stand on the underside, outboard of everything.
    c = c.union(rails(z_mouth))
    # the TRRS jack way's upper end
    tx, ty = _corner(TRRS_D, *TRRS_CORNER)
    c = c.cut(printable_bore(TRRS_BORE_D, trrs_top - (z0 - 1.0),
                             (LS.LEG_X + tx, LS.LEG_Y + ty, z0 - 1.0), (0, 0, 1), COLLAR_UP))
    return c


# -- what the tower gives up ---------------------------------------------------------
def tower_cut(z_mouth: float) -> cq.Workplane:
    """Cut in the bar's tower: the two RAIL SLOTS the collar slides into, and the
    one screw's anchor (self-tap now, insert later) -- upright, so sideways to the
    bar's print, which is why cadkit shapes it."""
    z0 = planes(z_mouth)["z0"]
    out = rail_slots(z_mouth)
    for (x, y, _), axis in screws(z_mouth):
        a = anchor_cutter(M4, (x, y, z0), axis, SCREW_BITE + D.MIN_WALL_2P,
                          overshoot=1.0, print_up=BAR_UP)
        out = out.union(a)
    return out


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
