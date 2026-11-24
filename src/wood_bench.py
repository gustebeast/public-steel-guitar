"""WOOD BENCH -- one string of the DIRECT-DRIVE instrument on a wooden plank (user, 2026-11-13).

STRING 6 (index 5): the user has a 370 mm Tr8x2 screw, and string 6's station takes the 331 mm
cut (strings 4, 6 and 10 share it). Every bought part and every printed drive part is the
instrument's own, DRAWN AT THE INSTRUMENT'S WORLD COORDINATES (src.direct_bench at T_OPEN): the
yoke, keyplate, nut, collar, spring, sleeves, plug, guide rod, housing, collars A and B, the 688,
the coupler, the SERVO42D, the bend and bridge 688s on their axles, the keyhead's nut plate. What
is new here is only what holds them up off a plank:

    MOTOR MOUNT   the instrument's motor plate (mplate) where the instrument has it, run down to
                  the plank on a base with two buttresses (user, 2026-11-16: it matches the
                  instrument, so the bench runs the real coupler). It replaced the plank bench's
                  motor block, whose axis height (26.25 over the wood) still sets the plank
                  (Z_PLANK) and whose tab edge the plank's edge line (Y_EDGE).
    ANCHOR        a printed stand-in for the stainless anchor tray (user: "a part to stand in as
                  the anchor"): the tray's 4 mm web at the tray's x, with string 6's holes (collar
                  B, the rod, the housing's two M4s), held by two 45 deg buttresses on its +X side
                  (the screw's thrust pushes the web +X), and a RAIL along the plank to the
                  endplate: the rail's +X end BUTTS the endplate's joint face (x_j), so the
                  anchor-to-endplate spacing the guide rod and the spring are cut to is the print's,
                  not the plank's. Body and walls between them are not needed: the rail is the
                  body, in compression between the two, as the instrument's walls and floor are.
    ENDPLATE      the +X endplate cut down to string 6 (direct_bench._endplate(only=5)): the
                  bridge bearing's 90 deg turn down and the bend bearing's 90 deg turn back -X,
                  the lane, the keyhole plate's window, the rod's seat. SHORTENED BY KH_DROP
                  (user, 2026-11-13): a band of the fill between the two bearings comes out, so
                  the bridge bearing sits level with the lowered crown. Base out to the plank screws.
    KEYHEAD       the V2 NUT BLOCK cut down to string 6 (src.nut_block_v2 / keyhead_v2): the nut
                  plate (or its stand-in), the wrap rod, the side screw, the wedge height screw,
                  string 6's coil zone, lane and window. Only the block (user, 2026-11-13): its
                  bottom IS the wooden floor, so it stands KH_DROP lower than in the instrument.

THE DUAL-ROD BENCH (user, 2026-11-24: "test this new drivetrain with dual guide rod contact ... still
only one string"): the instrument's SHARED GUIDE RODS -- string 6's collar grips its own rod (rod 5)
with its jaw and HOOKS rod 8 (string 9's own rod, a full ROD_L like every string's) on the far side.
String 9 is not on the bench, so its rod is held by the bench: its +X end in a seat in the endplate
slice (direct_bench._endplate(extra_rods=...), the instrument's seat and crush ribs), its -X end
through the anchor stand-in's web and a post on its -X face. The stack is the INSTRUMENT'S (the
stack without ears: one-piece collar, NUT inserts down its channels, M3 x 35 through the nut's
flange, the keyplate's lobes); the plug, lid and ties stay the bench's (the M3 x 30s on hand).
Prints go to coupons/woodbench_dual/ (the first bench's coupons/woodbench/ is left as printed).

THE PLANK: its top is Z_PLANK; every base's -Y face is one plane, Y_EDGE (the motor block's own
tab edge, turned): lay them flush with the plank's edge and they are in line. The keyhead and
the endplate keep the instrument's spacing (the scale length): crown (NUT_BLOCK_X) to the bridge
bearing's axle, SCALE_SPAN, is the one measurement to make on the plank.

    py -3.12 -m src.wood_bench      -> coupons/woodbench/<material>/*.step + PRINT_LIST.md (all of it)
"""

from __future__ import annotations

import pathlib

import cadquery as cq

from . import dimensions as D
from . import direct_bench as DB
from . import m3_hardware as M3H
from . import plank_bench as PB
from .helpers import box_at, cyl_x
from cadkit.kept import kept

I = 5                                            # string 6
HOOK = I + DB.SHARE_NB                           # rod 8: string 9's own rod, which string 6's collar hooks
BENCH_KEEP = {"plug", "hb", "insert", "lid"}     # the bench's variants kept: its ties (M3 x 30 on hand);
                                                 # the stack (yoke, collar, nut, M3s, inserts) is the instrument's
Y5, Z5, XR = DB.y_of(I), DB.za(I), DB.x_ref(I)   # the screw's axis; XR its pulley plane
BASE_T = PB.BASE_T                               # 4.8
# THE PLANK: the motor block's axis height over the wood (its pad under the can) sets it
AXIS_OVER_PLANK = PB.XR_ZA - PB.Z_PLANK_X        # 26.25
Z_PLANK = Z5 - AXIS_OVER_PLANK                   # -111.43
ZB = Z_PLANK + BASE_T                            # every base's top
UP = (0.0, 0.0, 1.0)
TAB = 6.4                                        # a screw tab's half-size round its screw


def _box(x0, x1, y0, y1, z0, z1):
    return box_at(x1 - x0, y1 - y0, z1 - z0, x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(z0 + z1) / 2)


def _screw(x, y, up=UP):
    """A wood screw's clearance and countersink from the base's top; `up` the part's build
    direction (a sideways bore prints as a teardrop)."""
    return PB._wood_screw(x, y, up, Z_PLANK)


# THE PLANK'S EDGE LINE: where the plank bench's motor block (the first motor mount here, its base
# turned 180 deg about Z onto string 6) had its tab edge; the anchor, endplate and keyhead printed
# to it, so it stays
# MORE CENTRED ON THE PLANK (user, 2026-11-24: "move the assembly so it's more centered on the plank,
# that way we can give more clearance between the +x endplate 45 supports and the guide rods"): the
# edge line every base is flush with stands EDGE_SHIFT further -Y than the first bench's (the plank
# bench's motor block's tab edge, -28.35): the string ~centred on a 90 wide plank
EDGE_SHIFT = 20.0
Y_EDGE = Y5 - (PB.Y_EDGE - PB.SY) - EDGE_SHIFT   # -48.35


# ── THE MOTOR MOUNT: THE INSTRUMENT'S PLATE, STANDING ON THE PLANK (user, 2026-11-16: "make a new
# one that matches the instrument" ... "I want to use the real coupler") ─────────────────────────
# It replaces the plank bench's motor block, whose 8 mm face wall stood 4 nearer the coupler than
# the instrument's 4 mm plate, so the bench needed a coupler of its own. This is direct_bench's
# mplate where the instrument has it -- PLATE_T thick on the motor's face, its pilot and four M3
# holes -- run down to the plank, on a base, held square by a buttress each side OUTSIDE the
# motor's square (inside it the face screws' heads and the coupler's swept Ø24.8 need the room).
# The -Y buttress is what fits between the square and the plank's edge line (Y_EDGE).
MM_X0 = XR - DB.M_FACE                           # the plate's -X face, on the motor's faceplate
MM_X1 = MM_X0 + DB.PLATE_T
MM_SQ = D.MOTOR_SQ
MM_Y = (Y_EDGE, Y5 + MM_SQ / 2 + 6 * D.BEAD)    # out to the +Y buttress (4.8)
MM_TOP = Z5 + MM_SQ / 2                          # the plate's top, as the instrument's
MM_BUT_TOP = Z5 + 8.0                            # the buttresses' top: over the axis
MM_FOOT = MM_X1 + (MM_BUT_TOP - ZB)              # their 45 deg foot
MM_UP = (0.0, 0.0, 1.0)                          # prints base down
MM_M3_L = 12.0                                   # M3 x 12: a SPACER's 4 and the plate's 4, 4 into
                                                 # the motor (user, 2026-11-18: through the bare plate
                                                 # the 12 bottoms in the motor's shallow holes)
MM_SPACER_L = 4.0                                # the spacers under the heads (direct_bench's
MM_SPACER_D = (DB.MPLATE_BOSS_D, 3.4)            # MPLATE_BOSS on the instrument)
MM_SCREWS = [(MM_X0 - TAB, Y_EDGE + TAB), (MM_X0 - TAB, MM_Y[1] - TAB),
             (MM_FOOT + TAB, Y_EDGE + TAB), (MM_FOOT + TAB, MM_Y[1] - TAB)]


def motor_mount() -> cq.Workplane:
    """The plate (x MM_X0..MM_X1, y over the plank's edge line to past the square, z plank to the
    square's top), its two buttresses +X of it, the base with four wood screws. Holes as the
    instrument's plate's, sideways here: teardrops peaked +Z."""
    from cadkit.holes import teardrop_hole
    w = _box(MM_X0, MM_X1, MM_Y[0], MM_Y[1], Z_PLANK, MM_TOP)
    for y0, y1 in ((MM_Y[0], Y5 - MM_SQ / 2), (Y5 + MM_SQ / 2, MM_Y[1])):
        assert y1 - y0 >= 3 * D.BEAD - 1e-6, (y0, y1, "a buttress under three beads")
        tri = (cq.Workplane("XZ", origin=(0, y1, 0))
               .polyline([(MM_X1 - 0.01, ZB - 0.01), (MM_X1 - 0.01, MM_BUT_TOP), (MM_FOOT, ZB - 0.01)])
               .close().extrude(y1 - y0))
        w = w.union(tri)
    w = w.union(_box(MM_X0 - 2 * TAB, MM_FOOT + 2 * TAB, MM_Y[0], MM_Y[1], Z_PLANK, ZB))   # the base

    def hole(d, y, z, fit=False):
        return teardrop_hole(d, DB.PLATE_T + 2.0, axis_point=(MM_X0 - 1.0, y, z), axis_dir=(1, 0, 0),
                             print_up=MM_UP, fit=fit)
    w = w.cut(hole(D.NEMA17_PILOT_D + 0.6, Y5, Z5, fit=True))
    for sy in (1, -1):
        for sz in (1, -1):
            w = w.cut(hole(3.4, Y5 + sy * DB.NEMA17_HOLES / 2, Z5 + sz * DB.NEMA17_HOLES / 2))
    for x, y in MM_SCREWS:
        w = w.cut(_screw(x, y, MM_UP))
    return w


def _motor_m3s() -> list:
    """The four M3 x 12 SHCS on their 4 mm spacers (MM_SPACER_L) over the plate's +X face, into the
    motor's faceplate; the spacers one part each."""
    from . import motor_coupler as MC
    out = []
    for k, (sy, sz) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        yc, zc = Y5 + sy * DB.NEMA17_HOLES / 2, Z5 + sz * DB.NEMA17_HOLES / 2
        out.append((f"wb_face_m3_{(sy + 1) // 2}{(sz + 1) // 2}", MC.cap_screw(
            "m3", MM_M3_L, (MM_X1 + MM_SPACER_L + MC.M3_HEAD[1], yc, zc), (-1, 0, 0))))
        sp = DB.cyl_x(MM_SPACER_D[0], MM_SPACER_L, MM_X1, y=yc, z=zc)
        out.append((f"wb_motor_spacer_{k}", sp.cut(DB.cyl_x(MM_SPACER_D[1], MM_SPACER_L + 2, MM_X1 - 1,
                                                             y=yc, z=zc))))
    return out


# ── THE ANCHOR STAND-IN ──────────────────────────────────────────────────────────────────────
AX0, AX1 = DB.ANCHOR                             # the web, -194.7 .. -190.7
A_TOP = Z5 + 19.0                                # -66.2: 8 over the plug's and housing's tops
def _drive_y_extent():
    """The plug's and housing's widest in y: their ears round string 6's ties (the plug's ring
    round an insert, the housing's boss) and the guide rod's boss."""
    ear = max(max(DB.plug_ear_hw(I)), DB.TIE_BOSS)
    ys = [dy - ear for dy, _ in DB.tie_offsets(I)] + [dy + ear for dy, _ in DB.tie_offsets(I)]
    rb = DB.GUIDE_SEAT / 2 + DB.GUIDE_WALL
    ry = DB.rod_yz(I)[0] - Y5
    return min(ys + [ry - rb]), max(ys + [ry + rb])


A_IN = tuple(Y5 + v + s for v, s in zip(_drive_y_extent(), (-1.0, 1.0)))   # the buttresses' inner
                                                 # faces: 1.0 off the plug's and housing's widest
A_WALL = 6 * D.BEAD                              # 4.8: each buttress
A_Y = (min(A_IN[0], DB.rod_yz(HOOK)[0] - DB.GUIDE_SEAT / 2 - 2 * D.BEAD) - A_WALL, A_IN[1] + A_WALL)   # a wall each
                                                 # side (user, 2026-11-24: the -Y one out to the edge line wasted plastic)
A_FOOT = AX1 + (A_TOP - ZB)                      # the buttresses' 45 deg foot, x
A_BASE_X0 = AX0 - 16.0                           # the base's -X end: room for two screws
RAIL_Y = (Y_EDGE, Y_EDGE + 16.0)                 # the rail to the endplate: along the edge
XJ = DB.ep_x()["x_j"]                            # -20.2: the endplate's joint face
# THE ENDPLATE'S -Y FLANGE (THE DUAL-ROD BENCH): the slice now runs to the edge line over rod 8's seat,
# so its -Y screw can no longer stand beside it (a screw's access shaft ran down through the seat);
# it goes on a flange off the joint face at the plank, and the rail stops short and butts THAT
# THE ENDPLATE'S BUTTRESSES (user, 2026-11-24: "it was bowing towards -x due to the string tension. Can
# you add 45 supports going towards -x"): two 45 deg buttresses off the joint face, one each side of the
# drive in Y, standing on flanges the plate's base runs -X on, screwed to the plank. Their top at the
# joint face is as high as the R1 board over them allows: the slope stays BUT_CLR under the board's
# lowest (its underside, less the parts under it) where the board begins, OPT_FACE_GAP off the face
# (BUT_TOP and the flanges' length below, with the board's numbers).
# in Y: the +Y one from past the optical screw bracket (y 5.9 .. 12.7) and rod 5 to the widened plate's
# edge; the -Y one from the plank's edge line to rod 8, BUT_ROD_CLR off it
BUT_ROD_CLR = 5.0
BUT_W = 10.0
BUT_PY = (DB.rod_yz(I)[0] + DB.GUIDE_D / 2 + BUT_ROD_CLR, 0.0)
BUT_PY = (BUT_PY[0], BUT_PY[0] + BUT_W)
BUT_NY = (DB.rod_yz(HOOK)[0] - DB.GUIDE_D / 2 - BUT_ROD_CLR - BUT_W, DB.rod_yz(HOOK)[0] - DB.GUIDE_D / 2 - BUT_ROD_CLR)
assert BUT_NY[0] >= Y_EDGE, "the -Y buttress off the plank's edge line"
assert BUT_NY[1] - BUT_NY[0] >= 5 * D.BEAD - 1e-6, "the -Y buttress under five beads"


def anchor() -> cq.Workplane:
    """The web (the tray's, at its x), two buttresses +X of it, the base, the rail to x_j.
    PRINTS BASE DOWN (+Z): the buttresses stand as walls either side of the web, so the web
    spans between them along its layers. Its X holes are teardrops peaked +Z."""
    from cadkit.holes import teardrop_hole
    pu = A_UP
    w = _box(AX0, AX1, A_Y[0], A_Y[1], Z_PLANK, A_TOP)                       # the web
    for y0, y1 in ((A_Y[0], A_IN[0]), (A_IN[1], A_Y[1])):                    # the buttresses
        tri = (cq.Workplane("XZ", origin=(0, y1, 0))
               .polyline([(AX1 - 0.01, ZB - 0.01), (AX1 - 0.01, A_TOP), (A_FOOT, ZB - 0.01)])
               .close().extrude(y1 - y0))
        w = w.union(tri)
    w = w.union(_box(A_BASE_X0, A_FOOT + 2 * TAB, Y_EDGE, A_Y[1], Z_PLANK, ZB))    # the base
    w = w.union(_box(A_FOOT, X_RAIL_END, RAIL_Y[0], RAIL_Y[1], Z_PLANK, ZB))       # the rail
    # string 6's holes, as the tray's: the screw's, the rod's, the housing's two M3 ties
    def hole(d, y, z):
        return teardrop_hole(d, AX1 - AX0 + 2.0, axis_point=(AX0 - 1.0, y, z),
                             axis_dir=(1, 0, 0), print_up=pu, fit=True)
    w = w.cut(hole(DB.PLATE_HOLE_D, Y5, Z5))
    ry, rz = DB.rod_yz(I)
    w = w.cut(hole(DB.GUIDE_SEAT + 0.4, ry, rz))
    # ROD 8 (THE DUAL-ROD BENCH): the instrument holds it in string 9's plug and housing; here the web
    # and a POST on the web's -X face, to the rod's -X end, standing on the base (printed base down:
    # vertical walls, the bore a teardrop peaked +Z)
    hy, hz = DB.rod_yz(HOOK)
    w = w.union(_box(HOOK_POST_X0, AX0 + 0.01, hy - HOOK_POST_R, hy + HOOK_POST_R, ZB - 0.01, hz))
    w = w.union(cyl_x(2 * HOOK_POST_R, AX0 + 0.01 - HOOK_POST_X0, HOOK_POST_X0, y=hy, z=hz))
    w = w.cut(teardrop_hole(DB.GUIDE_SEAT + 0.4, AX1 - HOOK_POST_X0 + 2.0, axis_point=(HOOK_POST_X0 - 1.0, hy, hz),
                            axis_dir=(1, 0, 0), print_up=pu, fit=True))
    for dy, dz in DB.tie_offsets(I):
        w = w.cut(hole(3.5, Y5 + dy, Z5 + dz))
    for x, y in a_screws():
        w = w.cut(_screw(x, y, pu))
    return w


A_UP = (0.0, 0.0, 1.0)
# rod 8's post: from just +X of the rod's -X end (pushed home in the endplate's seat) to the web,
# 1.6 of wall round the bore
HOOK_POST_X0 = DB.ROD_END + 0.3
HOOK_POST_R = DB.GUIDE_SEAT / 2 + 2 * D.BEAD
# the base's -X, -Y screw moves +Y out from under the post (the anchor goes down before the drive)
def a_screws():
    return [(A_BASE_X0 + TAB, DB.rod_yz(HOOK)[0] + HOOK_POST_R + TAB), (A_BASE_X0 + TAB, A_Y[1] - TAB),
                (A_FOOT + TAB, Y_EDGE + TAB), (A_FOOT + TAB, A_Y[1] - TAB),
                ((A_FOOT + X_RAIL_END) / 2, (RAIL_Y[0] + RAIL_Y[1]) / 2),
                (X_RAIL_END - 2 * TAB, (RAIL_Y[0] + RAIL_Y[1]) / 2)]   # the rail's: X_RAIL_END is set below


# ── THE +X ENDPLATE, CUT DOWN TO STRING 6 ────────────────────────────────────────────────────
E = DB.ep_x()
EP_Y_OPT = (Y5 - 12.0, DB.rod_yz(I)[0] + DB.GUIDE_SEAT / 2 + DB.GUIDE_WALL + 3.0)   # the first bench's
                                                 # slice, -16.75 .. 15.95: the optical brackets keep to it
EP_Y = (BUT_NY[0], BUT_PY[1])                    # buttress to buttress: rod 8's seat (THE DUAL-ROD BENCH)
                                                 # and both buttresses' roots; the base runs on to the edge line
assert DB.rod_yz(HOOK)[0] - DB.GUIDE_SEAT / 2 - DB.GUIDE_WALL - EP_Y[0] >= 2 * D.BEAD, "rod 8's seat off the slice"
EP_BASE_Y1 = EP_Y[1] + 2 * TAB                   # the base: a flange each side in Y, flush
# the -Y flange's screws: the far side of the -Y buttress, -X of the optical rest bracket (x XJ - OB_L ..
# XJ, y -16.75 .. -13.55: a screw's access shaft beside the face would cut it)
Y_NSCREW = BUT_NY[0] - 0.5 - 4.8                 # -Y of the -Y buttress, on the flange
assert Y_NSCREW - 4.8 >= Y_EDGE - 1e-6, "the -Y flange's screws off the edge line"
def ep_screws():
    return ([(x, EP_BASE_Y1 - TAB) for x in (XJ + TAB, E["x_end"] - TAB, (XJ + BUT_FOOT_X) / 2,
                                             BUT_FOOT_X - TAB)]                 # the +Y base and flange
            + [(x, Y_NSCREW) for x in (XJ - OB_L - 9.0, BUT_FOOT_X - TAB)])       # the -Y flange


def endplate() -> cq.Workplane:
    """direct_bench's endplate with only string 6's features, cut to EP_Y and the plank, with the
    band EP_BAND taken out of the fill between the bearings (everything over it comes down KH_DROP).
    PRINTS AS THE INSTRUMENT'S, +X -> -X on its +X face (the base's flanges flush with it)."""
    w = DB._endplate(only=I, extra_rods=(HOOK,)).intersect(_box(XJ - 1, E["x_end"] + 1, EP_Y[0], EP_Y[1], Z_PLANK, 100))
    lo = w.intersect(_box(XJ - 2, E["x_end"] + 2, EP_Y[0] - 1, EP_Y[1] + 1, Z_PLANK - 1, EP_BAND[0]))
    hi = w.intersect(_box(XJ - 2, E["x_end"] + 2, EP_Y[0] - 1, EP_Y[1] + 1, EP_BAND[1], 100))
    w = lo.union(hi.translate((0.0, 0.0, KH_DROP)))
    w = w.union(_box(XJ, E["x_end"], Y_EDGE, EP_BASE_Y1, Z_PLANK, ZB))   # the base, both sides
    w = w.union(_box(X_RAIL_END, XJ + 0.01, RAIL_Y[0], max(RAIL_Y[1], BUT_NY[1]), Z_PLANK, ZB))   # the -Y flange
    w = w.union(_box(X_RAIL_END, XJ + 0.01, BUT_PY[0], EP_BASE_Y1, Z_PLANK, ZB))  # the +Y flange
    for y0, y1 in (BUT_PY, BUT_NY):                                          # THE BUTTRESSES
        tri = (cq.Workplane("XZ", origin=(0, y1, 0))
               .polyline([(XJ + 0.5, ZB - 0.01), (XJ + 0.5, BUT_TOP), (XJ - OB_L, BUT_TOP),
                          (XJ - OB_L, BUT_TOP - OB_TIP), (BUT_FOOT_X, ZB - 0.01)])   # 0.5 into the plate:
               # over the band its joint face stands a few hundredths +X of XJ
               .close().extrude(y1 - y0))
        w = w.union(tri)
    for x, y in ep_screws():
        w = w.cut(_screw(x, y, DB.EP_UP))
    return _opt_anchor(w.union(opt_brackets()))   # the optical board's two brackets (below)


def ep_axles() -> list:
    """The bend row's axle (row c) and the bridge axle (brought down KH_DROP): the instrument's
    100 mm, through the slice."""
    k_bend = DB.level(I)
    n = len(DB.axle_zs()) - 1
    return [(nm, kept(DB._axle, k).translate((0.0, 0.0, KH_DROP if k == n else 0.0)))
            for k, (nm, _) in enumerate(DB.axle_zs()) if k in (k_bend, n)]


# ── THE KEYHEAD: A HOLDER FOR THE STEEL NUT PLATE, ON THE WOOD (user, 2026-11-24: "the string clamping
# system wasn't working so we can make a simple version that just holds an insert in place. Same metal
# insert ... I have a guitar tuner holding the string so the crown is just to set the height") ──────
# THE STRING AS LOW AS THE HARDWARE ALLOWS (user, 2026-11-24: "as low as is reasonably allowed by the
# hardware"): the bench lowers the crown and the bridge bearing together by taking a band out of the
# endplate's fill between the bend bearing and the bridge bearing (EP_BAND). The band is as tall as it
# goes: from 1.8 over the bend bearing's roof to 1 under the bridge bearing's pocket -- the bridge
# bearing then sits just over the bend bearing. (The motor, 16 under the string then, and the R1
# board over the drive, 19, do not limit it.)
from . import nut_block_v2 as NB2
_BAND0 = DB.z_level(DB.level(I)) + DB.R + D.BRG688_OD / 2 + DB.EP_BRG_CLR + 1.8
_BR_POCKET = DB.BR_C[1] - D.BRG688_OD / 2 - DB.EP_BRG_CLR
KH_DROP = -((_BR_POCKET - 1.0) - _BAND0)         # -64.0: the string at z -48
EP_BAND = (_BAND0, _BAND0 - KH_DROP)
assert EP_BAND[1] <= _BR_POCKET - 1.0 + 1e-9, "the band runs into the bridge pocket"
assert EP_BAND[0] > DB.rod_yz(I)[1] + DB.GUIDE_SEAT / 2 + DB.GUIDE_WALL, "the band cuts the rod's seat"
KH_AT = (D.NUT_BLOCK_X, 0.0, D.STRING_Z + KH_DROP)   # nut block local -> bench world
# THE HOLDER: a block with a SLOT the plate drops into from the top, its foot on the slot's floor (so
# the crown stands where KH_DROP puts the string), its sides held to KH_TOP. Over that only the crown
# arm stands: the string leaves the crown -X for the tuner over a free 24. PRINTS BASE DOWN (+Z).
KH_PRINT_UP = (0.0, 0.0, 1.0)
KH_CLR_X, KH_CLR_Y = 0.3, 0.2                    # the slot round the plate (a cut 304 plate: +-0.1)
KH_WALL = 6 * D.BEAD                             # 4.8 round the slot
KH_TOP = -24.0                                   # the walls' top, under the string top (local z)


def _plate_box():
    """The plate's (x0, x1, y0, y1, z0) in the world."""
    b = NB2.plate(I).translate(KH_AT).val().BoundingBox()
    return b.xmin, b.xmax, b.ymin, b.ymax, b.zmin


def kh_box():
    """The holder's block (x0, x1, y0, y1): the slot's walls (its base runs -Y to the edge line)."""
    x0, x1, y0, y1, _ = _plate_box()
    return (x0 - KH_CLR_X - KH_WALL, x1 + KH_CLR_X + KH_WALL, y0 - KH_CLR_Y - KH_WALL, y1 + KH_CLR_Y + KH_WALL)


def keyhead() -> cq.Workplane:
    """The holder: the block from the plank to KH_TOP, its base out each side in X with the screws,
    the slot from the plate's foot up through the top."""
    x0, x1, y0, y1, zf = _plate_box()
    bx0, bx1, by0, by1 = kh_box()
    assert zf - Z_PLANK >= 2 * D.MIN_WALL_2P, "the slot's floor under the plate is too thin"
    zt = KH_AT[2] + KH_TOP
    w = _box(bx0, bx1, by0, by1, Z_PLANK, zt)
    w = w.union(_box(bx0 - 2 * TAB, bx1 + 2 * TAB, by0 - 2 * TAB, by1 + 2 * TAB, Z_PLANK, ZB))   # the base,
                                                 # centred on the plate (user, 2026-11-24)
    w = w.cut(_box(x0 - KH_CLR_X, x1 + KH_CLR_X, y0 - KH_CLR_Y, y1 + KH_CLR_Y, zf, zt + 1.0))
    for x, y in kh_screws():
        w = w.cut(_screw(x, y, KH_PRINT_UP))
    return w


def kh_screws():
    bx0, bx1, by0, by1 = kh_box()
    return [(x, y) for x in (bx0 - TAB, bx1 + TAB) for y in (by0 - TAB, by1 + TAB)]


def keyhead_hardware() -> list:
    return [("wb_nut_plate", NB2.plate(I).translate(KH_AT))]


def bench_string(t: float) -> cq.Workplane:
    """String 6 as direct_bench draws it, the run from the crown over the bridge bearing brought
    down KH_DROP (the crown and the bridge bearing both came down)."""
    import math
    g = D.STRING_GAUGE[I]
    y0, y1 = D.nut_y(I), DB.y_of(I)
    zs = D.STRING_Z + g / 2 + KH_DROP
    rr = DB.R + g / 2
    bz = DB.BR_C[1] + KH_DROP
    pts = [(D.NUT_BLOCK_X - 30.0, y0, zs - 3.0), (D.NUT_BLOCK_X, y0, zs), (DB.BR_C[0], y1, zs)]
    for k in range(1, 7):
        a = math.pi / 2 * (1 - k / 6)
        pts.append((DB.BR_C[0] + rr * math.cos(a), y1, bz + rr * math.sin(a)))
    zc = DB.z_level(DB.level(I)) + DB.R
    for k in range(0, 7):
        a = -math.pi / 2 * k / 6
        pts.append((DB.X_BEND + rr * math.cos(a), y1, zc + rr * math.sin(a)))
    pts.append(DB.yaw_pt((DB._ball_x(t), y1, DB.za(I)), I))
    out = None
    for a, b in zip(pts, pts[1:]):
        if math.dist(a, b) > 1e-3:
            sg = DB._seg(a, b, g)
            out = sg if out is None else out.union(sg)
    return DB.with_string_look(out, I, t, KH_DROP, nut="block")


SCALE_SPAN = DB.X_BEND - D.NUT_BLOCK_X           # crown to the bridge bearing's axle (x)


# ── PRINTED STAND-INS FOR THE BOUGHT METAL (user, 2026-11-16: "swap in plastic versions of the
# spacers and the keyplate") ───────────────────────────────────────────────────────────────────
# THE TIE SPACERS: the instrument's are aluminium tube, 0.65 of wall -- a print needs more. Same 13
# between lip and plate, Ø6.4 (the ear's boss is Ø5.8; 0.85 off collar B's swept Ø24.8 and 0.87 off
# the guide rod on string 6). The M3's bore is the printed clearance every printed M3 hole takes
# (m3_hardware.CLR_PRINTED_D, 3.7 round: they print STANDING, +X up), not a hand 4.0 (user,
# 2026-11-17). PCTG (user, 2026-11-17: "prints a bit more accurately at small sizes").
WB_SPACER = (6.4, M3H.CLR_PRINTED_D)


def tie_spacers() -> list:
    """The two printed spacers, one part each (the instrument's tie_spacer_<k>)."""
    od, idd = WB_SPACER
    L = DB.TIE_SPACER[2]
    x1 = DB.ANCHOR[0]
    return [cyl_x(od, L, x1 - L, y=Y5 + dy, z=Z5 + dz).cut(cyl_x(idd, L + 2, x1 - L - 1, y=Y5 + dy, z=Z5 + dz))
            for dy, dz in DB.tie_offsets(I)]


# THE KEYHOLE PLATE: the instrument's 4 mm plate (direct_bench.keyhole_plate), printed in PETG-GF
# until the steel one is cut. The ball bears on ~4 mm^2 either side of the slit: ~40 MPa under the
# string's 147 N, near what PETG-GF takes -- watch it for creep into the slit.
def _swap(nm: str, w, t: float = DB.T_OPEN):
    if nm.startswith("tie_spacer"):                # tie_spacer_<k>_<i>: piece k
        k = int(nm.split("_")[2])
        return f"wb_tie_spacer_{k}", kept(tie_spacers)[k]
    if nm.startswith("keyplate"):              # PRINTED: the printed M3 clearance, not the laser's 3.4
        p = DB.keyhole_plate(M3H.CLR_PRINTED_D, seat=True,
                              slit_w=DB.slit_w_printed(D.STRING_GAUGE[I])).translate((DB.x_yt(t), DB.y_of(I), DB.za(I)))
        return "wb_keyplate", DB.yaw(p, I)
    return nm, w


# ── THE R1 OPTICAL BOARD ON TWO 45 DEG BRACKETS OFF THE ENDPLATE (user, 2026-11-16: "two 45 angled
# supports which hold up the R1 optical board and a single screw mount ... rotate the board 180 from
# its original intended orientation so we can get the sensors close to where they need to go without
# needing to run the bearing/string through the PCB hole" ... "it would just be part of the endplate
# not a separate part") ──────────────────────────────────────────────────────────────────────────
# The board as ordered (elec/rev1/optical.geom.json), turned 180 deg about Z: its sensor row, on its
# -X edge in the instrument, is its +X edge here, and the whole board lies -X of the bridge bearing
# under the speaking length, its +X edge 3.65 off the endplate's joint face -- the bearing's slots go
# unused. A sensor channel sits under string 6 where the instrument senses, 20 before the bridge axle
# (optical_pickup: SENSE_X -28 off BRIDGE_AXLE_X -8), the board's top the instrument's 2.2 under the
# string (PART_STRING_CLR 1.1 over the field's tallest 1.1; nothing along any channel's line on the
# turned board is taller). THE CHANNEL IS D10 (PD10A/B): it is the one that puts the board's Ø4.4
# mounting hole over the endplate (y 9.3; D6's would be at y 46.8, off its side). The endplate grows
# two 45 deg brackets off its -X face, their tops the board's seat: the M4 x 10 button head through
# the hole, self-tapped into one (_opt_anchor), the board resting on the other; the rest overhangs.
OPT_SENSE_DX = -20.0                             # LED row off the bridge axle (R1: SENSE_X - BRIDGE_AXLE_X)
OPT_GAP = 2.2                                    # string bottom -> board top (R1 PCB_TOP)
OPT_LED = "D10"                                  # the channel under string 6 (see above)
OPT_REV1 = pathlib.Path(__file__).resolve().parents[1] / "elec" / "rev1" / "optical.geom.json"
OB_L = 36.0                                      # a bracket's reach off the joint face (and its
                                                 # drop: 45 deg), its foot over the drive (z -74)
OB_W = 11.0                                      # the old width in y (opt_hole's fit test keeps it)
# SLIM BRACKETS (user, 2026-11-18: "we don't need much to hold the board in place. One support can
# be quite thin, the other just thick enough to fit the screw plus 1.6mm on either side"): the
# screw's bracket the self-tap bore + 2 x 1.6, the resting one two beads
OB_WALL = 1.6
OB_REST_W = 4 * D.BEAD                           # 3.2 (user, 2026-11-18), AT THE ENDPLATE'S -Y EDGE:
                                                 # the two brackets as far apart as the plate allows
OB_Y2 = EP_Y_OPT[0] + OB_REST_W / 2              # the resting bracket, where the first bench had it
OB_TIP = 2.0                                     # the tip cut flat (no knife edge on the print's top)
OS_M4_L = 10.0                                   # M4 x 10: 1.6 of board, 8.4 self-tapped into the bracket

# THE ENDPLATE'S BUTTRESSES' height and the flanges' length (see THE ENDPLATE'S BUTTRESSES above)
# THE BUTTRESSES CARRY THE BOARD (user, 2026-11-24: "put the supports on the existing downward
# creep-prevention supports to reuse the same material"): each rises to the board's underside, a flat
# SEAT OB_L long under it, OB_TIP of square end, then 45 deg down to the base
BUT_TOP = D.STRING_Z + KH_DROP - OPT_GAP - 1.6   # the board's underside (R1: 1.6 thick)
BUT_FOOT_X = XJ - OB_L - (BUT_TOP - OB_TIP - ZB)  # the slope reaches the base here
EP_FLANGE_L = XJ - BUT_FOOT_X + 2 * TAB          # the base's flanges, -X off the joint face
X_RAIL_END = XJ - EP_FLANGE_L                    # the anchor's rail butts the -Y one


def _opt_geom() -> dict:
    import json
    return json.loads(OPT_REV1.read_text(encoding="utf-8"))


def _string_y(x: float) -> float:
    y0, y1 = D.nut_y(I), DB.y_of(I)
    return y0 + (y1 - y0) * (x - D.NUT_BLOCK_X) / (DB.BR_C[0] - D.NUT_BLOCK_X)


def opt_frame():
    """(DX, DY, Z0, t): board (x, y, z) -> world (DX - x, DY - y, Z0 + z); z 0 its underside."""
    g = _opt_geom()
    led = next(f for f in g["footprints"] if f["ref"] == OPT_LED)
    t = g["thickness_mm"]
    xs = DB.BR_C[0] + OPT_SENSE_DX
    z0 = D.STRING_Z + KH_DROP - OPT_GAP - t      # the string's underside, less the gap and the board
    return xs + led["x"], _string_y(xs) + led["y"], z0, t


def _opt_to_world(x, y):
    dx, dy, _, _ = opt_frame()
    return dx - x, dy - y


def opt_board() -> cq.Workplane:
    """The R1 board (parts and all, as ordered), turned and placed."""
    from . import board_geom as BG
    b = BG.on_the_bench(())
    b._cache["optical"] = _opt_geom()            # R1, whatever OPTICAL_REV the build runs
    dx, dy, z0, _ = opt_frame()
    return b.solid("optical").rotate((0, 0, 0), (0, 0, 1), 180).translate((dx, dy, z0))


def opt_hole():
    """The board's mounting hole over the endplate, world (x, y)."""
    g = _opt_geom()
    for h in g["holes"]:
        xs, ys = [p[0] for p in h], [p[1] for p in h]
        if max(xs) - min(xs) > 6.0:              # the bearing slots
            continue
        x, y = _opt_to_world((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        if EP_Y_OPT[0] + OB_W / 2 <= y <= EP_Y_OPT[1] - OB_W / 2:
            assert XJ - OB_L + 8.0 < x < XJ, "the hole off the bracket"
            return x, y
    raise AssertionError("no mounting hole over the endplate: pick another OPT_LED")


def opt_brackets() -> cq.Workplane:
    """THE SCREW'S BLOCK (the board's brackets are the buttresses' seats now): the board's Ø4.4 hole
    is over neither buttress, so a block off the +Y one runs -Y under it, the self-tap bore + 2 x
    OB_WALL wide, OB_L along the face, down to OB_STACK_CLR over the stack (the keyplate's top)."""
    from cadkit.fasteners import M4
    _, hy = opt_hole()
    hw = M4.tap_d((0.0, 0.0, -1.0), DB.EP_UP) / 2 + OB_WALL
    assert hy + hw <= BUT_PY[1], "the screw's block past the +Y buttress"
    return _box(XJ - OB_L, XJ + 0.5, hy - hw, BUT_PY[0] + 0.5, OB_Z_MIN, BUT_TOP)


OB_STACK_CLR = 2.0
OB_Z_MIN = DB.za(I) + DB.YK_D / 2 + OB_STACK_CLR   # the keyplate's (the stack's widest) top, and the clearance


# SELF-TAPPED, NO INSERT (user, 2026-11-16: "use self tapping so we don't have to put in and remove
# the insert"): the M4 cuts its own thread in the bracket, 8.4 of it under the board (5.6 x D's 0.7
# pitch past min_bite's five), the bore 1.0 past the tip
OPT_TAP_L = OS_M4_L - 1.6 + 1.0


def _opt_anchor(w):
    from cadkit.fasteners import M4, cut_selftap
    _, _, z0, _ = opt_frame()
    hx, hy = opt_hole()
    return cut_selftap(M4, w, (hx, hy, z0), (0, 0, -1), OPT_TAP_L, overshoot=0.5, print_up=DB.EP_UP)


def opt_hardware() -> list:
    from cadkit.fasteners import M4_BUTTON_HEAD_H, m4_button_screw
    _, _, z0, t = opt_frame()
    hx, hy = opt_hole()
    return [("wb_opt_screw", m4_button_screw(OS_M4_L).translate((hx, hy, z0 + t + M4_BUTTON_HEAD_H)))]


# ── THE ASSEMBLY ─────────────────────────────────────────────────────────────────────────────
def assembly(t: float = DB.T_OPEN) -> list:
    out = [_swap(nm, w, t) for nm, w in DB.string_parts(I, t, bench=BENCH_KEEP)
           if not nm.startswith(("mplate", "string", "keyseat"))]   # the bench's printed
                                                                       # keyplate is one piece
    out.append((f"wb_string_{I}", kept(bench_string, t)))
    hy, hz = DB.rod_yz(HOOK)
    out.append(("wb_hook_rod", cyl_x(DB.GUIDE_D, DB.ROD_L, DB.ROD_END, y=hy, z=hz)))   # rod 8
    out += [(nm, w.translate((0.0, 0.0, KH_DROP)) if nm.startswith("bridge_brg") else w)
            for nm, w in DB._bend_parts() if nm.endswith(f"_{I}")]
    out += ep_axles()
    out += [("wb_motor_mount", kept(motor_mount)), ("wb_anchor", kept(anchor)),
            ("wb_endplate", kept(endplate)), ("wb_keyhead", kept(keyhead))]
    out += _motor_m3s() + keyhead_hardware()
    out += [("optical_r1", kept(opt_board))] + opt_hardware()   # its colour: direct_bench's table
    x0 = D.NUT_BLOCK_X - 60.0
    out.append(("ghost_plank", _box(x0, E["x_end"] + 40.0, Y_EDGE, Y_EDGE + 90.0,
                                    Z_PLANK - 19.0, Z_PLANK)))
    return [(nm, _made(nm, w)) for nm, w in out]


MATERIAL = {"wb_motor_mount": "petg-gf", "wb_anchor": "petg-gf", "wb_endplate": "petg-gf",
            "wb_tie_spacer": "pctg", "wb_keyplate": "petg-gf", "wb_motor_spacer": "petg-gf",

            "wb_keyhead": "petg-gf", "wb_wrap_rod": "steel", "wb_hook_rod": "steel", "ghost_plank": "wood",
            "wb_string": "polished", "wb_nut_plate": "stainless", "wb_nut_side_insert": "brass",
            "wb_nut_height_insert": "brass", "wb_nut_shoe": "petg-gf"}


def material_of(base: str):
    """tools.web_materials asks here for wb_ names."""
    return MATERIAL.get(base) or ("steel" if ("m3" in base or "screw" in base or "rod" in base)
                                  else None)


def _made(nm, w):
    from cadkit.web.finishes import made_of
    if DB.owns(nm):
        return DB._made(nm, w)
    import re as _re
    m = MATERIAL.get(_re.sub(r"(_\d+)+$", "", nm)) or ("steel" if ("m3" in nm or "screw" in nm or "plate" in nm) else
                             "brass" if "insert" in nm else None)
    return made_of(w, m) if m else w


PRINTS = ("wb_motor_mount", "wb_anchor", "wb_endplate", "wb_keyhead", "wb_nut_shoe", "wb_tie_spacer",
          "wb_keyplate", "wb_motor_spacer")


# each bench print's build direction (the comments at each part say why)
WB_PRINT_UP = {"wb_motor_mount": MM_UP, "wb_anchor": A_UP, "wb_endplate": DB.EP_UP,
               "wb_keyhead": KH_PRINT_UP,
               "wb_tie_spacer": (1.0, 0.0, 0.0),           # standing, +X up
               "wb_keyplate": (-1.0, 0.0, 0.0),            # flat on its +X face: the ball's seat
                                                           # (-X face) opens on top, no bridge
                                                           # over it (user, 2026-11-18)
               "wb_motor_spacer": (1.0, 0.0, 0.0)}         # a ring, flat
# the instrument's own string-6 prints the bench does NOT use: the motor mount replaces the plate
WB_NOT_USED = ("mplate",)
# ...and the ones it prints ITS OWN WAY (direct_bench, THE WOOD BENCH'S STACK: the ties on hand;
# the stack is the instrument's -- THE DUAL-ROD BENCH)
WB_VARIANT = {"plug": lambda: kept(DB._anchor_plug, I, True),
              "lid": lambda: DB._lid(I, True)}
WB_DIR = pathlib.Path(__file__).resolve().parents[1] / "coupons" / "woodbench_dual"


def main():
    """EVERYTHING TO PRINT FOR THE BENCH (user, 2026-11-16: "put all the woodbench steps in a folder
    so I can print them all"): coupons/woodbench/<material>/, each in its print pose, and
    PRINT_LIST.md with the quantities -- the bench's own parts and string 6's instrument prints
    (src.build's parts and print directions; collars A and B are one clamp_collar, two of it)."""
    from cadkit.orientation import PrintOrientation as PO
    from cadkit.step_export import export_print
    from . import build as B
    rows = {}

    def put(w, mat, stem, up):
        d = WB_DIR / mat
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{stem}.step"
        if f"{mat}/{stem}" not in rows:
            export_print(w, up, str(p))
            print("wrote", p)
        rows[f"{mat}/{stem}"] = rows.get(f"{mat}/{stem}", 0) + 1

    import re as _re
    for nm, w in assembly():
        b = _re.sub(r"(_\d+)+$", "", nm)          # a piece (wb_tie_spacer_1) prints as its kind
        if b in PRINTS:
            put(w, MATERIAL[b], b, PO.from_build_dir(WB_PRINT_UP[b], "src.wood_bench.WB_PRINT_UP"))
    for leader, (stem, mat, members) in B.STRING_FAMILIES.items():
        for key in members:
            base = key.rsplit("_", 1)[0]
            if key.endswith(f"_{I}") and base not in WB_NOT_USED:
                make = WB_VARIANT.get(base, B.PARTS[key][0])
                put(make(), mat, stem, B.PRINT_ORIENTATION[key])
    (WB_DIR / "PRINT_LIST.md").write_text(
        "# Wood bench (dual rod): what to print\n\nGenerated by `py -3.12 -m src.wood_bench`: string 6's "
        "bench with the shared guide rods, "
        "each STEP in its print pose.\n\n| file | qty |\n|---|---|\n"
        + "\n".join(f"| `{k}.step` | {n} |" for k, n in sorted(rows.items())) + "\n",
        encoding="utf-8")
    print("wrote", WB_DIR / "PRINT_LIST.md")


if __name__ == "__main__":
    main()
