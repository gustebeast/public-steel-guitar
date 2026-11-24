"""VARIANTS (STACK_VARIANT env, default "channel"):
  channel   (user, 2026-11-23) -- ONE PIECE, no split, no thread: an ACCESS CHANNEL at each screw
            (its Ø the NUT-mode pocket's, 5.5) from the collar's -X end through the spring's grip and
            the stop flange to a NUT-mode pocket in the solid band, where a fitted insert slid in by
            hand is the nut (its whole face on the lip; never melted). The screws from the keyplates'
            +X face, as today. The channels split the inner post in two halves (opened to the bore:
            no sliver); the sleeve is THICKENED over each channel (CH_SKIN outside it) instead.
  flipped   (user, 2026-11-23: "flip the screw head and insert") -- the M3 HEADS in F behind its lip
            (dropped in from -X through F's cup before R; ~13 mm2 each on the lip, ~2 MPa from the
            spring), a fitted insert on the keyplates' +X face as the nut, HELD BY FINGERS (snug only:
            the spring holds the joint; the stack is put together on the bench). No tip holes in R:
            R self-locks on its thread under the spring's pull (lead angle ~1.7 deg). F is STEPPED
            (user: "the screw head + minimal clearance + 1.6mm wall") over the lip and heads; the
            thread band behind still wraps the heads (+ its depth).
  insert    (user, 2026-11-23: "model the heat-set version") -- no retainer: two M3 HEAT-SET inserts in
            F, pressed from -X through F's open cup before R goes in, each one's +X face on F's lip
            ("used as a nut": the screw pulls it onto plastic, not out of its knurl). The screws from
            the keyplates' +X face, as today. One piece cannot take them: behind the lip r 8 is the
            spring's 2.5 channel, the insert 4.7 -- hence still F + R.
  retainer  the steel retainer below.

THE STACK WITHOUT EARS (user, 2026-11-23): a laser-cut steel RETAINER inside a TWO-PART collar, so
the stack clamps through the nut flange's OWN holes and nothing reaches far past the spring sleeve.

    retainer (steel, tapped M3) -> collar F's LIP (compression) -> nut flange -> yoke -> keyhole
    plates; two M3s from the plates' +X face, through the flange's holes, into the retainer

The collar is split so both halves print with nothing hanging (user: no paused prints -- replacement
parts must be orderable from a print service):
  F  the lip, a CUP round the retainer and an internal THREAD, the tab and the hook. Printed lip down
     (+X -> -X), the cup open -X: the retainer drops in.
  R  a threaded PLUG, then the stop flange, the sleeve and the post. Printed plug down (+X -> -X).
R screws into F's cup and clamps the retainer on F's lip. The spring pulls R -X: across the thread
(~0.5 MPa) into F, and F's lip bears on the retainer (compression). The stack screws' TIPS pass
through the retainer into holes in R, so R cannot unscrew. A screw head cannot reach R from -X (the
post and the sleeve wall it in) and a bayonet's notches would cut the retainer in two: the thread.

The thread is cadkit's self-supporting 45 deg thread (threaded_rod), both halves in phase.

Nothing here edits the instrument: direct_bench is read and patched IN MEMORY (no ears, the collar
COLLAR_GROW longer). Run:  py -3.12 -m src.test.stack_retainer_study  -> its own viewer tab.
"""

from __future__ import annotations

import math
import os
import sys

import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src import direct_bench as DB                      # noqa: E402
from src import dimensions as D                         # noqa: E402

STRINGS = (0, 1, 3)              # string 1, its next (row below: the tight pair), its same-row one
T = DB.T_OPEN

NUT_CLOCK = 45.0                 # the nut turned so its 4 holes sit at 0/90/180/270 (from 45/135/...)
SCREW_ANG = (0.0, 180.0)         # the two used: across the slit (+-Y), clear of the ball's way in
R_SCREW = DB.NUT_PCD / 2         # 8.0
M3_CLR = DB.M3H.CLR_PRINTED_D    # the screws' printed clearance
WALL = D.MIN_WALL_2P             # 1.6

LIP_T = WALL                     # F's lip, between the flange and the retainer
RET_T = 3.0                      # the retainer: 3 mm steel, tapped M3
RET_CLR = 0.2                    # its pocket, along x and round its edge
TAP_D = 2.5
LOBE_R = TAP_D / 2 + 1.25        # steel round each tapped hole
RET_HOLE = DB.COLLAR_NUT_D       # the nut's boss passes through it

THREAD_P, THREAD_H = 2.0, 0.8    # F/R thread: pitch, depth (45 deg flanks)
THREAD_TURNS = 2
THREAD_L = THREAD_TURNS * THREAD_P
M3_STOCK = DB.M3_STOCK + (35.0, 40.0)   # ISO 4762 stock past direct_bench's list
VARIANT = os.environ.get("STACK_VARIANT", "channel")
assert VARIANT in ("channel", "flipped", "insert", "retainer"), VARIANT
TIP_IN = 3.0                     # the stack screws' tips this far into R (R's unscrew lock)


def _pose(i):
    return DB.y_of(i), DB.za(i)


def _pts(i, angs, r=R_SCREW):
    y, z = _pose(i)
    return [(y + DB.at_ang(a, r)[0], z + DB.at_ang(a, r)[1]) for a in angs]


# ── sizes that follow from the above ─────────────────────────────────────────────────────────────
RET_R = R_SCREW + LOBE_R                                   # 10.5: the retainer, round (lobes = disc)
PASS_CLR = 0.2                                             # what passes F's thread, clear of its crests
if VARIANT == "flipped":
    BAND_T = DB.M3_HEAD[1] + PASS_CLR                      # the heads' band behind the lip (3.2)
    PASS_R = R_SCREW + DB.M3_HEAD[0] / 2                   # 10.75: a head at r 8
elif VARIANT == "insert":
    BAND_T = DB.INS_POCKET_L                               # the inserts' band behind the lip (4.6)
    PASS_R = R_SCREW + DB.INS_HEAT_D / 2                   # 10.4: an insert (its pocket) at r 8
else:
    BAND_T = RET_T + RET_CLR
    PASS_R = RET_R
R_MINOR_F = PASS_R + PASS_CLR                              # F's thread crests clear it
R_PITCH = R_MINOR_F + THREAD_H / 2                         # where F and R meet (drawn)
R_MAJOR_F = R_MINOR_F + THREAD_H
F_R = R_MAJOR_F + WALL                                     # F's outside (round the thread)
F_R_FRONT = (PASS_R + PASS_CLR + WALL) if VARIANT == "flipped" else F_R   # over the lip + heads
R_MINOR_R = R_MINOR_F - 0.2                         # R's plug, its thread's root
F_LEN = LIP_T + BAND_T + THREAD_L                 # F along x, from the flange's back face
COLLAR_GROW = 0.0 if VARIANT == "channel" else max(0.0, F_LEN - (DB.COLLAR_L + DB.STOP_T))  # the thread clear of the sleeve (f0)
DB.COLLAR_L += COLLAR_GROW


def bands(t=T):
    pb = DB.x_collar(t)[0]
    lip = (pb - LIP_T, pb)
    ret = (lip[0] - BAND_T, lip[0])
    thr = (pb - F_LEN, ret[0])
    return pb, lip, ret, thr


def _ring(i, r0, r1, x0, x1):
    y, z = _pose(i)
    w = DB.cyl_x(2 * r1, x1 - x0, x0, y=y, z=z)
    return w.cut(DB.cyl_x(2 * r0, x1 - x0 + 2, x0 - 1, y=y, z=z)) if r0 > 0 else w


def retainer(i, t=T):
    _, _, (r0, r1), _ = bands(t)
    x0 = r0 + RET_CLR / 2
    y, z = _pose(i)
    w = DB.cyl_x(2 * RET_R, RET_T, x0, y=y, z=z)
    w = w.cut(DB.cyl_x(RET_HOLE, RET_T + 2, x0 - 1, y=y, z=z))
    for (py, pz) in _pts(i, SCREW_ANG):
        w = w.cut(DB.cyl_x(TAP_D, RET_T + 2, x0 - 1, y=py, z=pz))
    return w


def _collar_whole(i, t=T):
    DB.HOLD_ANG, DB.PIN_ANG = (), SCREW_ANG[0]                 # no ears; the pin's hole under a screw
    return DB._collar(i, t)


THREAD_CLR = 0.2                 # radial, the plug's thread inside the cup's (printed on printed)


def _thread_x(i, minor_r, major_r, x0, length, nut):
    """cadkit's self-supporting 45 deg thread along +X at string i, its first turn starting at x0
    (both halves start at a whole turn from the same x: their helices are in phase). nut = the
    female cutter (full crest to its ends, small overshoot), else the male plug (lead-in bevels)."""
    from cadkit.threads import threaded_rod
    kw = dict(overshoot=0.05, bevel_ends=not nut)   # fine pitch: the 0.3 default overshoot overlaps turns
    rod = threaded_rod(2 * minor_r, 2 * major_r, THREAD_P, length, **kw)
    y, z = _pose(i)
    return rod.rotate((0, 0, 0), (0, 1, 0), 90).translate((x0, y, z))


def collar_f(i, t=T):
    """F: the collar from the flange's back to the retainer's -X face, its outside grown to F_R over
    F_LEN, the retainer's pocket, and the cup + thread band (r >= R_PITCH) behind it."""
    pb, (l0, l1), (r0, r1), (h0, h1) = bands(t)
    c = _collar_whole(i, t)
    front = c.intersect(DB.box_at(pb - r0, 100, 100, x=(pb + r0) / 2, y=_pose(i)[0], z=_pose(i)[1]))
    front = front.union(_ring(i, DB.COLLAR_NUT_D / 2, F_R_FRONT, r0, pb))
    if VARIANT == "retainer":
        front = front.cut(_ring(i, 0, RET_R + RET_CLR, r0 - 0.01, r1))          # the pocket
    elif VARIANT == "flipped":
        front = front.cut(_ring(i, 0, PASS_R + PASS_CLR, r0 - 0.01, r1))        # the heads' room
    y, z = _pose(i)
    front = front.cut(DB.cyl_x(DB.COLLAR_NUT_D, pb - r0 + 2, r0 - 1, y=y, z=z))  # the boss's bore
    cup = _ring(i, R_MINOR_F, F_R, h0, h1 + 0.01)
    tab = c.intersect(DB.box_at(h1 - h0, 100, 100, x=(h0 + h1) / 2, y=y, z=z)).cut(
        DB.cyl_x(2 * R_MINOR_F, h1 - h0 + 2, h0 - 1, y=y, z=z))               # tab/hook, past the thread
    w = front.union(cup, clean=False).union(tab, clean=False)
    for (py, pz) in _pts(i, SCREW_ANG):                                       # through the lip
        w = w.cut(DB.cyl_x(M3_CLR, LIP_T + 2, l0 - 1, y=py, z=pz))
        if VARIANT != "flipped":     # flipped: the 0.8 to the bore stays (two 0.4 beads) -- the head bears on it
            w = w.cut(DB._radial_box_at(i, l0 - 0.01, pb + 1, DB.COLLAR_NUT_D / 2 - 0.5, R_SCREW, M3_CLR,
                                        SCREW_ANG[_pts(i, SCREW_ANG).index((py, pz))]))   # opened (0.8)
    if VARIANT == "insert":                    # the inserts' pockets, open -X (up as printed: no roof)
        for a, (py, pz) in zip(SCREW_ANG, _pts(i, SCREW_ANG)):
            w = w.cut(DB.fitted_insert_cutter(DB.INS, (r0, py, pz), (1.0, 0.0, 0.0), DB.HEAT_SET,
                                              depth=BAND_T, overshoot=1.0, print_up=(-1.0, 0.0, 0.0),
                                              roof=False), clean=False)
            w = w.cut(DB._radial_box_at(i, r0 - 1.0, r1 + 0.01, DB.COLLAR_NUT_D / 2 - 0.5, R_SCREW,
                                        DB.COLLAR_SLIT_W, a), clean=False)   # pocket -> bore: no sliver
    w = w.cut(_thread_x(i, R_MINOR_F, R_MAJOR_F, h0 - THREAD_P, THREAD_L + THREAD_P, nut=True),
              clean=False)                                         # LAST (thread rule): the internal thread, open at -X
    return w


def collar_r(i, t=T):
    """R: the collar behind the retainer, its thread band cut to the plug (r <= R_PITCH), with the
    stack screws' tip holes."""
    pb, _, (r0, r1), (h0, h1) = bands(t)
    c = _collar_whole(i, t)
    y, z = _pose(i)
    xmin = c.val().BoundingBox().xmin
    w = c.intersect(DB.box_at(r0 - xmin + 1, 100, 100, x=(xmin - 1 + r0) / 2, y=y, z=z))
    w = w.cut(_ring(i, R_MINOR_F - THREAD_CLR, 40, h0, r0 + 1))      # to the plug's root...
    plug = _thread_x(i, R_MINOR_F - THREAD_CLR, R_MAJOR_F - THREAD_CLR, h0, THREAD_L, nut=False)
    for (py, pz) in (_pts(i, SCREW_ANG) if VARIANT != "flipped" else ()):
        tip = screw_len() - grip() + 0.5                       # the chosen stock screw's tip, + 0.5
        w = w.cut(DB.cyl_x(M3_CLR, tip + 1, r0 - tip, y=py, z=pz))
    w = w.union(plug.cut(DB.cyl_x(2 * (R_MINOR_F - THREAD_CLR) - 0.1, THREAD_L + 2, h0 - 1, y=y, z=z),
                         clean=False), clean=False)                # LAST: its thread, in phase
    return w


# -- the CHANNEL variant: one piece ------------------------------------------------------------------
CH_SKIN = WALL                                  # the sleeve's skin outside each channel (thickened)
CH_DIR = (1.0, 0.0, 0.0)                        # the insert slides +X, to the lip
CH_WEDGE_R_GRIP = DB.R_COIL + DB.SLEEVE_CLR - 0.08   # the wedge in the grip: inside the sleeve's bore
CH_POST_CREST = DB.R_COIL - DB.post_in(DB.POST_GROOVE_C)   # the post's crest radius
CH_CHAMFER = 1.0            # the split's chamfer at the crest (> the tooth)


def ch_d():
    """The channel = the NUT-mode pocket's Ø (cadkit: one rule per mode), along the print axis."""
    return DB.INS.insert_pocket_d(DB.NUT, CH_DIR, DB.COLLAR_UP)


def ch_x(t=T):
    """(the pocket's mouth: the stop flange's +X face, its floor, the nut flange's back face)."""
    pb, (f0, f1), _ = DB.x_collar(t)
    return f1, f1 + DB.INS.insert_l + DB.NUT_END_SLIP, pb


def collar_channel(i, t=T):
    """direct_bench's collar with no ears, a bump of CH_SKIN outside the sleeve over each channel
    (solids first), then each channel, its pocket, the screw's hole through the lip, and the post
    opened to the leadscrew's bore along the channel (holes last)."""
    c = _collar_whole(i, t)
    y, z = _pose(i)
    xlo = c.val().BoundingBox().xmin
    mouth, floor, pb = ch_x(t)
    f0 = DB.x_collar(t)[1][0]
    d = ch_d()
    r_sl = DB.SLEEVE_OD / 2
    pts = list(zip(SCREW_ANG, _pts(i, SCREW_ANG)))
    for a, (py, pz) in pts:                                           # the bumps: outside the sleeve only
        bump = DB.cyl_x(d + 2 * CH_SKIN, pb - xlo, xlo, y=py, z=pz)        # to the +X face: it is on the
        c = c.union(bump.cut(DB.cyl_x(2 * r_sl - 0.02, pb - xlo + 2, xlo - 1, y=y, z=z)))   # bed (no overhang)
    for a, (py, pz) in pts:
        c = c.cut(DB.cyl_x(d, mouth - xlo + 1.01, xlo - 1, y=py, z=pz))          # the channel
        c = c.cut(DB.fitted_insert_cutter(DB.INS, (mouth, py, pz), CH_DIR, DB.NUT,
                                          print_up=DB.COLLAR_UP, roof=False))  # the insert's pocket
        c = c.cut(DB.cyl_x(M3_CLR, pb - floor + 2, floor - 1, y=py, z=pz))     # the screw, through the lip
    # A WEDGE FROM THE AXIS to each channel (user, 2026-11-23: two separate cuts left nubs, and the
    # channels met the nut boss's bore in cusps; then print_check: a flat-sided slab met the post's
    # round crest at 67 deg, a knife edge along each half). The wedge's sides are RADIAL -- square to
    # the post's crest, its groove and every bore -- and TANGENT to the channel, so they run into it
    # smooth. In the spring's grip it reaches CH_WEDGE_R_GRIP (past the post, inside the sleeve's bore:
    # only the spring's empty room); through the stop flange and the band it stops at the tangent
    # points (no notch in the solid). To the pockets' floor: the lip under each insert stays whole.
    th = math.degrees(math.asin(d / 2 / R_SCREW))                     # the channel's half-angle
    r_tan = math.sqrt(R_SCREW ** 2 - (d / 2) ** 2)                    # where the sides touch it
    for (x0, x1, rc) in ((xlo - 1, f0, CH_WEDGE_R_GRIP), (f0 - 0.01, floor, r_tan)):
        for a in SCREW_ANG:
            c = c.cut(_wedge_x(i, x0, x1, a - th, a + th, rc))
    # A 45 DEG CHAMFER DOWN EACH EDGE OF THE SPLIT, in the grip (print_check, 2026-11-23: where the
    # radial side crossed the groove's helix it left the crest a stub 0.7 long in a layer, a POINT;
    # and a square thread end the spring's wire crosses every turn): CH_CHAMFER deep at the crest,
    # so the tooth ramps out of the split as the posts' lead-ins do
    for a in SCREW_ANG:
        for e, sg in ((a + th, 1.0), (a - th, -1.0)):
            c = c.cut(_chamfer_x(i, xlo - 1, f0, e, sg, CH_POST_CREST - CH_CHAMFER, CH_WEDGE_R_GRIP))
    return c


def _chamfer_x(i, x0, x1, e, sg, r1, r2):
    """A 45 deg chamfer along the split's radial side at angle e (material toward sg), from r1 on
    that side out to r2 (clipped there: the sleeve's bore is past it), extruded x0..x1."""
    y, z = _pose(i)
    u = DB.at_ang(e, 1.0)
    n = DB.at_ang(e + sg * 90, 1.0)
    r2 += 0.3
    pts = [(u[0] * r1, u[1] * r1), (u[0] * r2, u[1] * r2),
           (u[0] * r2 + n[0] * (r2 - r1), u[1] * r2 + n[1] * (r2 - r1))]
    pts = [(p[0] - n[0] * 0.01, p[1] - n[1] * 0.01) if k < 2 else p for k, p in enumerate(pts)]   # into the split
    tri = cq.Workplane("YZ", origin=(x0, y, z)).polyline(pts).close().extrude(x1 - x0)
    return tri.intersect(DB.cyl_x(2 * (r2 - 0.3), x1 - x0, x0, y=y, z=z))   # inside the spring's room


def _wedge_x(i, x0, x1, a0, a1, r):
    """A sector of string i's section from angle a0 to a1, radius r, extruded x0..x1."""
    y, z = _pose(i)
    pts = [(0.0, 0.0)] + [DB.at_ang(a0 + (a1 - a0) * k / 16, r) for k in range(17)]
    return (cq.Workplane("YZ", origin=(x0, y, z)).polyline(pts).close().extrude(x1 - x0))


def yoke(i, t=T):
    """direct_bench's yoke with no ears, no pin pocket; the screws' clearance at R_SCREW."""
    y, z = _pose(i)
    ft, yt = DB.x_ft(t), DB.x_yt(t)
    out = DB.cyl_x(DB.YK_D, DB.YK_H - DB.YK_ROOF, ft, y=y, z=z)
    out = out.cut(DB.cyl_x(D.SCREW_OD + 0.8, yt - DB.YK_ROOF - ft + 1, ft - 1, y=y, z=z))
    out = out.cut(DB.cyl_x(DB.NUT_LIP_REG_D, D.NUT_LIP_L + 1.3, ft - 1, y=y, z=z))
    rl, rb = DB.NUT_LIP_REG_D / 2, (D.SCREW_OD + 0.8) / 2
    xl = ft + D.NUT_LIP_L + 0.3
    out = out.cut(DB._cone_x(rl, rb - 0.01, xl - 0.01, xl + rl - rb, y, z))
    ry, rz = DB.rod_yz(i)
    out = out.cut(DB.cyl_x(DB.GUIDE_D + 2.0, DB.YK_H + 2, ft - 1, y=ry, z=rz))
    for (py, pz) in _pts(i, SCREW_ANG):
        out = out.cut(DB.cyl_x(M3_CLR, DB.YK_H + 2, ft - 1, y=py, z=pz))
    return out


def sheets(i, t=T):
    DB.HOLD_ANG = ()
    y, z = _pose(i)
    out = []
    for k in (0, 1):
        s = DB.key_sheet(k)
        for a in SCREW_ANG:
            dy, dz = DB.at_ang(a, R_SCREW)
            s = s.cut(DB.cyl_x(3.4, 10, -8, y=dy, z=dz))
        out.append(s.translate((DB.x_yt(t), y, z)))
    return out


def nut(i, t=T):
    y, z = _pose(i)
    return DB._nut(i, t).rotate((0, y, z), (1, y, z), NUT_CLOCK)


def grip(t=T):
    if VARIANT == "channel":                   # the plates' +X face -> the pocket's floor (the lip)
        return DB.x_yt(t) - ch_x(t)[1]
    return _grip_split(t)


def _grip_split(t=T):
    """The stack screws' grip: the plates' +X face to the retainer's -X face."""
    if VARIANT == "flipped":                   # the head's face on the lip -> the plates' +X face
        return DB.x_yt(t) - bands(t)[1][0]
    return DB.x_yt(t) - (bands(t)[2][0] + (RET_CLR / 2 if VARIANT == "retainer" else 0.0))


INSERT_ENGAGE_MIN = 2.0          # flipped: the screw at least this far into the finger-held insert


def screw_len():
    """retainer/insert: the shortest stock M3 whose tip reaches TIP_IN into R. flipped: the longest
    whose tip stays inside the insert (INS long), at least INSERT_ENGAGE_MIN into it."""
    if VARIANT == "channel":                   # through the whole insert
        return min(L for L in M3_STOCK if L >= grip() + DB.INS.insert_l)
    if VARIANT == "flipped":
        ok = [L for L in M3_STOCK if grip() + INSERT_ENGAGE_MIN <= L <= grip() + DB.COL_INS[1]]
        assert ok, f"no stock M3 between {grip() + INSERT_ENGAGE_MIN:.1f} and {grip() + DB.COL_INS[1]:.1f}"
        return max(ok)
    return min(L for L in M3_STOCK if L >= grip() + TIP_IN)


def screws(i, t=T):
    yt, L = DB.x_yt(t), screw_len()
    if VARIANT == "flipped":                   # the head in F on the lip, the shank on +X
        l0 = bands(t)[1][0]
        return [DB.cyl_x(DB.M3_HEAD[0], DB.M3_HEAD[1], l0 - DB.M3_HEAD[1], y=py, z=pz).union(
                DB.cyl_x(3.0, L, l0, y=py, z=pz)) for (py, pz) in _pts(i, SCREW_ANG)]
    return [DB.cyl_x(DB.M3_HEAD[0], DB.M3_HEAD[1], yt, y=py, z=pz).union(
            DB.cyl_x(3.0, L, yt - L, y=py, z=pz)) for (py, pz) in _pts(i, SCREW_ANG)]


def parts():
    ps = []
    for i in STRINGS:
        n = i + 1
        ld, pk = sheets(i)
        if VARIANT == "channel":
            ps.append((f"collar_{n}", collar_channel(i)))
            ps += [(f"insert_{n}_{k}", DB.fitted_insert(DB.INS, (ch_x()[0], py, pz), CH_DIR))
                   for k, (py, pz) in enumerate(_pts(i, SCREW_ANG))]
            ps += [(f"yoke_{n}", yoke(i)), (f"nut_{n}", nut(i)), (f"keyplate_{n}", ld), (f"keyseat_{n}", pk)]
            ps += [(f"m3_{n}_{k}", s) for k, s in enumerate(screws(i))]
            ry, rz = DB.rod_yz(i)
            ps.append((f"rod_{n}", DB.cyl_x(DB.GUIDE_D, 80, DB.x_collar(T)[0] - 60, y=ry, z=rz)))
            continue
        if VARIANT == "retainer":
            ps.append((f"retainer_{n}", retainer(i)))
        elif VARIANT == "flipped":                 # the finger-held inserts on the plates' +X face
            ps += [(f"insert_{n}_{k}", DB.fitted_insert(DB.INS, (DB.x_yt(T), py, pz), (1.0, 0.0, 0.0)))
                   for k, (py, pz) in enumerate(_pts(i, SCREW_ANG))]
        else:
            r0 = bands()[2][0]
            ps += [(f"insert_{n}_{k}", DB.fitted_insert(DB.INS, (r0, py, pz), (1.0, 0.0, 0.0)))
                   for k, (py, pz) in enumerate(_pts(i, SCREW_ANG))]
        ps += [(f"collarF_{n}", collar_f(i)), (f"collarR_{n}", collar_r(i)),
               (f"yoke_{n}", yoke(i)), (f"nut_{n}", nut(i)), (f"keyplate_{n}", ld), (f"keyseat_{n}", pk)]
        ps += [(f"m3_{n}_{k}", s) for k, s in enumerate(screws(i))]
        ry, rz = DB.rod_yz(i)
        ps.append((f"rod_{n}", DB.cyl_x(DB.GUIDE_D, 80, DB.x_collar(T)[0] - 60, y=ry, z=rz)))
    return ps


COLORS = {"collar": (0.36, 0.30, 0.42), "retainer": (0.75, 0.76, 0.78), "insert": (0.80, 0.60, 0.35), "collarF": (0.36, 0.30, 0.42), "collarR": (0.52, 0.44, 0.60),
          "yoke": (0.42, 0.38, 0.50), "nut": (0.82, 0.60, 0.20), "keyplate": (0.80, 0.81, 0.83),
          "keyseat": (0.70, 0.71, 0.73), "m3": (0.20, 0.20, 0.22), "rod": (0.35, 0.35, 0.38)}


def _insert_face():
    """The insert's +X face on the lip: its OD (the knurl, capped by the pocket) less the screw's
    printed clearance, less the slot to the bore."""
    ro, ri = min(DB.COL_INS[0], DB.INS_HEAT_D) / 2, M3_CLR / 2
    return math.pi * (ro * ro - ri * ri) - DB.COLLAR_SLIT_W * (ro - ri)


def _arc_in(r, d):
    """Degrees of the circle of radius r (about the axis) inside a Ø d channel centred at R_SCREW."""
    c = (r * r + R_SCREW * R_SCREW - d * d / 4) / (2 * r * R_SCREW)
    return 0.0 if c >= 1 else 2 * math.degrees(math.acos(max(-1.0, c)))


def report(ps):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    d = dict(ps)

    def gap(a, b):
        e = BRepExtrema_DistShapeShape(d[a].val().wrapped, d[b].val().wrapped); e.Perform(); return e.Value()
    if VARIANT == "channel":
        cd = ch_d()
        mouth, floor, pb = ch_x()
        face = math.pi / 4 * (DB.INS.insert_od ** 2 - M3_CLR ** 2)
        post_r = DB.R_COIL - DB.post_in(DB.POST_GROOVE_C)
        lost = len(SCREW_ANG) * _arc_in(DB.R_COIL, cd)
        lines = [f"screws: M3 x {screw_len():.0f} (grip {grip():.2f}), through the {DB.INS.insert_l} insert",
                 f"channel/pocket D {cd:.2f} at r {R_SCREW}: r {R_SCREW - cd / 2:.2f} .. {R_SCREW + cd / 2:.2f}; "
                 f"lip under the insert {pb - floor:.2f}; insert face on it ~{face:.1f} mm2 -> "
                 f"{53 / len(SCREW_ANG) / face:.1f} MPa from the spring",
                 f"screw hole to the nut bore {R_SCREW - M3_CLR / 2 - DB.COLLAR_NUT_D / 2:.2f}; insert inner "
                 f"edge to the nut body {R_SCREW - DB.INS.insert_od / 2 - D.NUT_BOSS_D / 2:.2f}",
                 f"spring grip lost: {lost:.0f} deg of 360 at the coil centre ({lost / 3.6:.0f} pct), post + sleeve",
                 f"post: two halves, each ~{180 - _arc_in(post_r, cd):.0f} deg at its crest (r {post_r:.2f})",
                 f"sleeve: bumps to r {R_SCREW + cd / 2 + CH_SKIN:.2f} (D {2 * (R_SCREW + cd / 2 + CH_SKIN):.2f}) "
                 f"at {SCREW_ANG}; elsewhere D {DB.SLEEVE_OD}"]
        for a, b in (("collar_1", "collar_2"), ("collar_1", "collar_4"), ("collar_2", "collar_4"),
                     ("yoke_1", "yoke_2")):
            lines.append(f"gap {a} - {b}: {gap(a, b):.3f}")
        bad = [n for n, w in ps if not w.val().isValid()]
        lines.append("every solid valid" if not bad else "INVALID: " + ", ".join(bad))
        return lines
    area = 2 * math.pi * R_PITCH * THREAD_L * 0.5                      # thread shear, ~half engaged
    head_face = math.pi / 4 * (DB.M3_HEAD[0] ** 2 - M3_CLR ** 2)
    lines = [(f"screws: M3 x {screw_len():.0f} (grip {grip():.2f}), {screw_len() - grip():.2f} into the "
              f"{DB.COL_INS[1]} insert; heads on the lip ~{head_face:.1f} mm2 each -> "
              f"{53 / 2 / head_face:.1f} MPa from the spring; head to the nut body "
              f"{R_SCREW - DB.M3_HEAD[0] / 2 - D.NUT_BOSS_D / 2:.2f}") if VARIANT == "flipped" else
             f"screws: M3 x {screw_len():.0f} (grip {grip():.2f}), tips {screw_len() - grip():.2f} into R",
             f"F stepped: lip + heads D {2 * F_R_FRONT:.2f}, thread band D {2 * F_R:.2f}" if VARIANT == "flipped" else
             (f"retainer: R {RET_R:.2f}; steel inside a tapped hole {R_SCREW - TAP_D / 2 - RET_HOLE / 2:.2f}, "
              f"round it {RET_R - R_SCREW - TAP_D / 2:.2f}") if VARIANT == "retainer" else
             (f"inserts: Ø{DB.COL_INS[0]} x {DB.COL_INS[1]} in Ø{DB.INS_HEAT_D} pockets; face on the lip "
              f"~{_insert_face():.1f} mm2 each -> {53 / 2 / _insert_face():.1f} MPa from the spring; pocket "
              f"wall to the nut bore {R_SCREW - DB.INS_HEAT_D / 2 - DB.COLLAR_NUT_D / 2:.2f} (slotted)"),
             f"thread: pitch {THREAD_P}, {THREAD_TURNS} turns at r {R_PITCH:.2f}; 53 N over ~{area:.0f} mm2 = "
             f"{53 / area:.2f} MPa",
             f"F: outside D {2 * F_R:.2f} (sleeve {DB.STOP_D:.2f}), cup wall {F_R - R_MAJOR_F:.2f}, length {F_LEN:.2f}; "
             f"collar {COLLAR_GROW:.2f} longer",
             "R: no tip holes (self-locks on its thread)" if VARIANT == "flipped" else
             (f"R: plug wall, tip hole to thread root {R_MINOR_R - R_SCREW - M3_CLR / 2:.2f}, "
              f"nut bore to tip hole {R_SCREW - M3_CLR / 2 - DB.COLLAR_NUT_D / 2:.2f}")]
    for a, b in (("collarF_1", "collarF_2"), ("collarF_1", "collarR_2"), ("collarF_1", "collarF_4"),
                 ("yoke_1", "yoke_2")):
        lines.append(f"gap {a} - {b}: {gap(a, b):.3f}")
    bad = [n for n, w in ps if not w.val().isValid()]
    lines.append("every solid valid" if not bad else "INVALID: " + ", ".join(bad))
    return lines


if __name__ == "__main__":
    ps = parts()
    for ln in report(ps):
        print(ln, flush=True)
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "out", "stack_retainer")                 # one tab, whichever variant
    os.makedirs(root, exist_ok=True)
    from cadkit.web import show
    show([(n, w, COLORS[n.split("_")[0]]) for n, w in ps], root=root, title=f"Stack study ({VARIANT})")
