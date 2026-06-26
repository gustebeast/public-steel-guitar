"""Chassis frame (§8) — PCTG. ONE rigid frame that absorbs the motor bank and
ties in the bridge endplate and a nut keyhead, SPLIT into glued segments.

The strings pull the bridge and nut toward each other (~10×100 N) at the speaking
height, which would bow the instrument; the chassis resists that. The stiffness
comes from DEPTH: two longitudinal side rails (from just under the strings down
to the print bed) run the whole length, tied by per-motor cross-ribs and a
keyhead bulkhead at the nut. The motor faceplate walls (with their NEMA17
patterns) are fused in; the motors rest on the ribs (no floor plate). The rail
webs carry self-supporting diamond lightening; everything else is modelled
SOLID — the slicer's walls + infill set the strength-to-weight.

Too long for one print (~645 mm > 255 mm bed), so it's cut into 3 segments joined
by SLIDING DOVETAILS on the side rails: each joint's tongue flares toward +X
(locking the segments against the string pull), you drop the next segment straight
DOWN onto it (one direction), and it bottoms on a shoulder that sets the position —
then glue. The cuts fall in the ~1 mm gaps BETWEEN motor walls, so no motor
mount is split. Built in global position; the segments assemble into the whole.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import motor_bank as MB
from .components import MOTOR_PULLEY_STANDOFF
from .helpers import box_at, cyl
from .legs import DT_FACE_HW, DT_DEEP_HW, DT_DEPTH, DT_H

T        = D.WALL_THICKNESS            # rail thickness (solid; slicer infills)
X_BRIDGE = 6.0                         # +X (bridge) end — the rails end here; the bridge
                                       #   endplate caps them (a separate flat-printed part)
X_NUT    = -(D.MOUNTING_SPAN + 24.0)   # −X end, extended to carry the nut block;
                                       # rail ends FLUSH with the end bulkhead's
                                       # outer face (NUT_BLOCK_X − 9 − 15)
Z_TOP    = D.STRING_Z - 6.0            # body deck, 6 mm under the strings (normal action)
Z_BOT    = MB.BED_Z                    # print bed (shared with the motor walls)
# Rail CENTRES, defined so the INNER faces stay fixed as the wall T changes (the wall
# grows outward): +Y inner clears the bearing arm, -Y inner clears the motor PCBs.
Y_HI     = D.BRIDGE_AXLE_Y + 3.0 + T / 2          # +Y rail (inner face = axle_Y + 3)
Y_LO     = (D.string_y(0) - MOTOR_PULLEY_STANDOFF - D.MOTOR_BODY_LEN
            - D.MOTOR_PCB_LEN - 2.0) - T / 2      # −Y rail (inner = PCB back − 2)
_XC, _ZC = (X_BRIDGE + X_NUT) / 2, (Z_TOP + Z_BOT) / 2
_RIB_W   = D.XBAR                      # cross-rib X-width = XBAR (square XBAR×XBAR section)
# Top-plate retention grooves (top_plate.py rides these): a slot in each rail
# inner face below the rail top, leaving a ~3 mm lip so the deck plates can't
# fall out when the instrument is inverted (they pull straight out toward −X).
TP_X0, TP_X1   = -16.0, -638.0         # groove X span; open at the -X rail end so
                                       # the deck panels slide out -X once the
                                       # (removable) keyhead endplate is off
TP_GZ0, TP_GZ1 = 0.0, 6.0              # deck plate z-plane: bottom rests on the rail
                                       # top (lowered to z0 here), top = playing surface
# DECK JOINT — a VERTICAL DOVETAIL tongue-and-groove. The deck plate caps the rail
# (right-angle bend) and drops a dovetail tongue straight down into a groove milled
# in the rail top. The foot is wider than the mouth, so the wide foot can't pull up
# through the narrow mouth -> +Z retention (plates stay put when inverted). The
# inboard groove wall is what the rail bears against if the rails try to spread, so
# it also ties the rails in Y. The tongue runs along X -> plates still slide out -X.
# top_plate.py builds the matching tongue; the rail top is lowered to z0 in the deck
# X-span so the plate sits flush on top.
TP_TG_DEPTH    = 6.0                    # tongue depth below the deck (z0 .. -DEPTH)
TP_TG_MW       = 1.5                    # mouth half-width (at z0)
TP_TG_FLR      = 0.8                    # dovetail flare per side over DEPTH (foot = MW+FLR)
TP_TG_YC       = {1: Y_HI, -1: Y_LO}   # groove centre = each rail centre-line
TP_TG_CLR      = 0.25                  # sliding clearance (groove = tongue + CLR)
# +X END: the bridge endplate TAKES OVER the whole +X end as one solid block (the
# same endplate methodology as the keyhead): it is the +X cross-tie itself (no
# separate crossbar) and is held by the rail-end dovetails alone. The rails simply
# stop at TP_EP_GX; the deck groove runs up to there, then the bridge takes over.
TP_EP_GX       = -17.5                  # bridge +X face / rail +X end (rails stop here) =
                                       # deck +X face (the panels butt the bridge)
# -X END: the keyhead endplate takes over the whole -X end as one solid block (it is the
# -X cross-tie itself -- no separate crossbar -- and is held by the rail-end dovetails
# alone, no screw). The rails simply stop at KH_X.
KH_X           = -611.0                 # keyhead +X face / rail -X end (rails stop here)
# Endplate JOINERY (both ends, shared — see _end_dt / _kh_tongue / _br_tongue): each
# endplate is held by Y-flaring vertical dovetails that follow the L-shaped body<->
# endplate contact. Per rail there are TWO stacked dovetails: a LOWER one on the
# wall<->leg-shell face (z bed..foot line) and an UPPER one on the foot<->rail-end face
# (z foot line..deck-groove floor — it STOPS below the deck so the panel seat stays
# clear). Each is NARROW at the rail/shell face and WIDE KH_DT_DEPTH into the endplate,
# so string tension can't draw the wide foot back out. The body carries the tenons; the
# endplate sockets them (X+Y lock, still lifts +Z). The endplate's L-foot resting on the
# leg-shell top is the drop-depth stop, so the dovetails need no shoulder of their own.
KH_DT_WR, KH_DT_WT = 2.0, 3.0          # narrow / wide half-widths (Y). Sized so the socket's
                                       # OUTER wall (to the instrument's outer face, the only
                                       # bounded side: the dovetail centres on the rail, 5 mm
                                       # from that face) stays >= 1.6 mm (2x 0.8 nozzle): wall =
                                       # 5 - WT - KH_DT_CLR = 1.7 mm. 1:8 flank flare (WT-WR=1.0
                                       # over DEPTH), so the wall comfortably backs the undercut.
KH_DT_DEPTH    = 8.0                    # dovetail reach into the endplate (X)
KH_DT_Z0       = -23.15                 # foot line = leg-tenon top (-33.15) + XBAR; also the
                                       # LOWER/UPPER dovetail split (the L-corner / drop stop)
KH_DT_CLR      = 0.3                    # socket clearance (Y fit)
KH_DT_SEAT     = 0.1                    # lower-mortise headroom above the foot line: the
                                       # socket tops at KH_DT_Z0 + this so the tenon seats on
                                       # the L-foot/shell, not the mortise ceiling (-23.05)
# A chunky rail-to-rail rib UNDER EACH MOTOR (the motor rests on it, its wall sits
# on it, and it ties the two rails) replaces a solid floor — far lighter for the
# strength. Plus a rib near the nut. (No +X crossbar: the bridge block IS the +X tie.)
_RIB_X   = ([D.motor_pos(i)[0] for i in range(D.N_STRINGS)] + [-575.0])

# Bridge-endplate joint: ENDPLATE_JOINT_Y are the two rail centre-lines the bridge
# (and keyhead) sit over; kept for the bridge's foot/joint references.
ENDPLATE_JOINT_Y = (Y_HI, Y_LO)

SPLIT_X  = [-220.0, -440.0]            # 2 cuts → 3 segments < 255 mm, in motor-wall gaps
# dovetail: depth, root/tip width, shoulder, fit. Tip width kept ≤ T−3.2 so the
# socket walls in the 8 mm rail stay ≥1.6 mm (2 passes of a 0.8 mm nozzle).
_DT, _WR, _WT, _SH, _CLR = 8.0, 2.5, 4.5, 4.0, 0.3

def _diamond_xz(cx, cz, h, yr):
    """Diamond (45°) prism through a rail (axis Y) — a self-supporting hole in the
    vertically-printed rail web (its crown is a 45° peak, not a flat bridge)."""
    p = [(cx, cz + h), (cx + h, cz), (cx, cz - h), (cx - h, cz)]
    y0 = yr - (T + 2.0) / 2.0
    pts = [cq.Vector(x, y0, z) for x, z in p]
    face = cq.Face.makeFromWires(cq.Wire.makePolygon([*pts, pts[0]]))
    return cq.Workplane("XY").add(cq.Solid.extrudeLinear(face, cq.Vector(0, T + 2.0, 0)))


def _rail(y):
    """A deep longitudinal rail. The strings bow the body about the Y axis, so the
    top/bottom EDGES are the high-stress flanges and the mid-depth sits near the
    neutral axis — lighten that web with a row of self-supporting diamonds (an
    I-beam by material placement: most of the bending stiffness is kept for far
    less mass). Solid is kept at the ~14 mm flanges, the dovetail joints, and the
    loaded ends (bulkhead/rib ties) for transport robustness."""
    rail = box_at(X_BRIDGE - X_NUT, T, Z_TOP - Z_BOT, x=_XC, y=y, z=_ZC)
    FL = 14.0                                   # flange kept top & bottom
    h = (Z_TOP - Z_BOT) / 2 - FL - 2.0          # diamond half-diagonal in the web band
    step = 2 * h + 8.0
    def ok(cx):                                 # leave the string-mount ends + joints SOLID
        return (cx + h < D.BRIDGE_AXLE_X - 10.0     # bridge support / bulkhead bond zone
                and cx - h > -560.0                  # keyhead bulkhead bond zone
                and all(abs(cx - s) > h + 14.0 for s in SPLIT_X))
    cx = X_BRIDGE - 30.0
    while cx > X_NUT + 30.0:
        if ok(cx):
            rail = rail.cut(_diamond_xz(cx, _ZC, h, y))
        cx -= step
    return rail


def _rib(x, w=_RIB_W):
    """Chunky cross-rib, rail-to-rail, its top flush with the motor rest (FLOOR_TOP)."""
    return box_at(w, Y_HI - Y_LO, MB.FLOOR_TOP - Z_BOT,
                  x=x, y=(Y_HI + Y_LO) / 2, z=(MB.FLOOR_TOP + Z_BOT) / 2)


def _diamond(cy, cz, h, x, thick):
    """A diamond (45°) prism through the plate (axis X) — self-supporting as a hole
    in a vertically-printed plate (its crown is a 45° peak, not a flat bridge)."""
    return (cq.Workplane("YZ").workplane(offset=x - (thick + 2.0) / 2.0)
            .polyline([(cy, cz + h), (cy + h, cz), (cy, cz - h), (cy - h, cz)]).close()
            .extrude(thick + 2.0))


def _build_full() -> cq.Workplane:
    body = _rail(Y_HI).union(_rail(Y_LO))
    for x in _RIB_X:                                  # per-motor + bridge/nut cross-ribs (−Z)
        body = body.union(_rib(x))
    # (the pickup now mounts entirely in its deck cover piece — top_plate.py — so
    # the old rail bosses/grooves/X-lock stations that used to live here are gone)
    # keyhead: the box-closure bulkhead is now a SEPARATE, removable part
    # (keyhead_endplate.py) so the deck panels slide out -X for service. It seats
    # on this bottom tie rib, plugs into the rail-end channels, and is clamped
    # down by the nut-block bolts (whose inserts it carries) - lift the nut block
    # off and the endplate lifts out. The chassis keeps the rib + compression
    # wall + a shallow seat channel in each rail end for the endplate's tabs.
    _kx = D.NUT_BLOCK_X - 9.0                               # endplate centre line
    body = body.union(_rib(_kx, w=30.0))                   # bottom tie / seat
    ky = D.nut_y(D.N_STRINGS - 1) + 9.0
    body = body.union(box_at(4.0, 2 * ky, 4.0,            # +X compression wall (below the strings)
                             x=D.NUT_BLOCK_X + 6.0, y=0, z=Z_TOP + 2.0))
    for _yf, _s in ((Y_HI - T / 2, 1), (Y_LO + T / 2, -1)):   # endplate tab channels
        body = body.cut(box_at(12.0, 3.5, Z_TOP - (Z_BOT + 8.0),
                               x=_kx, y=_yf + _s * 1.5, z=(Z_TOP + Z_BOT + 8.0) / 2))
    # leg-socket joinery: a vertical sliding-dovetail slot in each rail's
    # OUTER face at the corner stations (solid web there). The printed socket
    # slides up from below and GLUES (it is only a separate part because the
    # chassis can't print below its bed); its barrel rim seats on the rail's
    # bottom face. The slot roof rises 45° toward the face — in-layer support
    # accretes from beyond the deep wall (a single supported slope, never a
    # chevron over an open edge).
    for _sx in LEG_STATIONS_X:
        for _yr, _s in ((Y_HI, 1), (Y_LO, -1)):
            body = body.cut(_leg_dt_slot(_sx, _yr, _s))
    # electronics-tray drop-in channels: one vertical channel per rail inner
    # face (open at the top - the tray lowers in from above and its tabs
    # bottom on the channel floors), placed in the only solid-web window
    # between the leg dovetail slot and the rail diamonds
    from .electronics import TAB_X0, TAB_X1, CH_W, CH_D, TRAY_Z0
    _cxm = (TAB_X0 + TAB_X1) / 2
    for _yr, _s in ((Y_HI, 1), (Y_LO, -1)):
        _yf = _yr - _s * T / 2                         # inner face
        body = body.cut(box_at(CH_W, CH_D + 1.0, Z_TOP + 1.0 - TRAY_Z0,
                               x=_cxm, y=_yf + _s * (CH_D - 1.0) / 2,
                               z=(TRAY_Z0 + Z_TOP + 1.0) / 2))
    # AFE boss: widen the bridge cross-rib's -Y end into a solid pad that
    # carries the analog front-end board, sitting BELOW the pickup and INBOARD
    # of the leg barrel - so it fouls neither. Bonds to the bridge rib (no
    # cantilever), prints as a vertical block off the bed. Two posts hold the board.
    from .electronics import (AFE_X0, AFE_X1, AFE_Y0, AFE_Y1, AFE_Z,
                              AFE_PED_TOP)
    body = body.union(box_at(AFE_X1 + 2 - (AFE_X0 - 2), AFE_Y1 + 2 - (AFE_Y0 - 2),
                             AFE_PED_TOP - Z_BOT,
                             x=(AFE_X0 - 2 + AFE_X1 + 2) / 2,
                             y=(AFE_Y0 - 2 + AFE_Y1 + 2) / 2,
                             z=(Z_BOT + AFE_PED_TOP) / 2))
    for _px, _py in ((AFE_X0 + 4, AFE_Y0 + 4), (AFE_X1 - 4, AFE_Y1 - 4)):
        body = body.union(cyl(6.0, (AFE_Z - 0.2) - AFE_PED_TOP, z=AFE_PED_TOP)
                          .translate((_px, _py, 0)))
    # wire raceways: a self-supporting diamond through every cross-rib at
    # each floor-trunk lane y (the harness runs at z -70.6, under the motors)
    from .wiring import RIB_RACE_Y
    for _rx in _RIB_X:
        for _ly in RIB_RACE_Y:
            body = body.cut(_diamond(_ly, -70.65, 3.5, _rx, _RIB_W + 2.0))
    # DECK JOINT: the plates cap the rail and drop a vertical DOVETAIL tongue into a
    # groove milled in the rail top. Lower the rail top to z0 across the whole deck
    # X-span (rail -X end up to the +X takeover line TP_EP_GX) so a plate sits flush,
    # then mill the groove (matches top_plate's tongue + clearance). The groove runs
    # right to TP_EP_GX; +X of there the bridge takes over (rail removed below).
    _gx0 = TP_X1 - 2.0
    for _yc in (Y_HI, Y_LO):
        # shave the rail top to z0 across the deck span + mill the groove
        body = body.cut(box_at(TP_EP_GX - _gx0, T + 0.5, (Z_TOP + 1.0) - TP_GZ0,
                               x=(_gx0 + TP_EP_GX) / 2, y=_yc,
                               z=(TP_GZ0 + Z_TOP + 1.0) / 2))
        MW, FLR, DEP, C = TP_TG_MW, TP_TG_FLR, TP_TG_DEPTH, TP_TG_CLR
        prof = [(_yc - MW - C, TP_GZ0 + 0.1), (_yc + MW + C, TP_GZ0 + 0.1),
                (_yc + MW + FLR + C, TP_GZ0 - DEP), (_yc - MW - FLR - C, TP_GZ0 - DEP)]
        pts = [cq.Vector(_gx0, py, pz) for py, pz in prof]
        face = cq.Face.makeFromWires(cq.Wire.makePolygon([*pts, pts[0]]))
        body = body.cut(cq.Workplane("XY").add(
            cq.Solid.extrudeLinear(face, cq.Vector(TP_EP_GX - _gx0, 0, 0))))
    body = body.union(MB.motor_bank)                  # fuse in the motor faceplate walls
    # +X end: the bridge endplate TAKES OVER the +X end as a solid block (mirror of the
    # keyhead -X takeover): remove the rail ENTIRELY at x > TP_EP_GX (z full) so the
    # bridge fills it and IS the +X cross-tie (no separate crossbar); it's held by the
    # rail-end dovetails alone. Only the dovetail tongues it sockets are added back.
    body = body.cut(box_at((X_BRIDGE + 5.0) - TP_EP_GX, (Y_HI - Y_LO) + T + 4.0,
                           (Z_TOP + 1.0) - (Z_BOT - 1.0),
                           x=(TP_EP_GX + X_BRIDGE + 5.0) / 2, y=(Y_HI + Y_LO) / 2,
                           z=((Z_BOT - 1.0) + (Z_TOP + 1.0)) / 2))
    # KEEP a ~10 mm rail shell hugging the +X leg socket (the removal above stripped
    # the rail off the leg's +X reach); the bridge endplate nests over this shell.
    body = body.union(_leg_shell(LEG_STATIONS_X[0], *LEG_SHELL_PX))
    for _yc in (Y_HI, Y_LO):
        body = body.union(_br_tongue(_yc))
    # keyhead TAKES OVER the -X end as a solid block (its edge shows from the front like
    # the bridge end): remove the rail ENTIRELY at x < KH_X (z full) so the keyhead fills
    # it and IS the -X cross-tie (no separate crossbar); it's held by the rail-end
    # dovetails alone (no screw). Only the dovetail tongues it sockets are added back.
    body = body.cut(box_at(KH_X - (X_NUT - 5.0), (Y_HI - Y_LO) + T + 4.0,
                           (Z_TOP + 1.0) - (Z_BOT - 1.0),
                           x=(KH_X + X_NUT - 5.0) / 2, y=(Y_HI + Y_LO) / 2,
                           z=((Z_BOT - 1.0) + (Z_TOP + 1.0)) / 2))
    # KEEP a ~10 mm rail shell hugging the -X leg socket (mirror of the +X end).
    body = body.union(_leg_shell(LEG_STATIONS_X[1], *LEG_SHELL_NX))
    for _yc in (Y_HI, Y_LO):
        body = body.union(_kh_tongue(_yc))
    return body


def _leg_dt_slot(sx, yr, s):
    """The vertical sliding-dovetail SLOT for a leg socket in the rail's OUTER
    face at station (sx, yr); `s` = +1 (Y_HI) / -1 (Y_LO). Cut from the rail; the
    printed leg tenon slides up into it from below. Factored out so the +X/-X
    end-takeover can KEEP a rail shell around the leg and re-cut this same slot."""
    yf = yr + s * T / 2                              # outer face
    yd = yf - s * DT_DEPTH                           # deep wall
    trap = (cq.Workplane("XY").workplane(offset=Z_BOT - 1.0)
            .polyline([(sx - DT_FACE_HW, yf), (sx + DT_FACE_HW, yf),
                       (sx + DT_DEEP_HW, yd), (sx - DT_DEEP_HW, yd)])
            .close().extrude(1.0 + DT_H + DT_DEPTH))
    keep = (cq.Workplane("YZ")
            .polyline([(yf + s, Z_BOT - 2.0),
                       (yf + s, Z_BOT + DT_H + DT_DEPTH + 1.0),
                       (yd - s, Z_BOT + DT_H - 1.0),
                       (yd - s, Z_BOT - 2.0)])
            .close().extrude(2 * DT_DEEP_HW + 4)
            .translate((sx - DT_DEEP_HW - 2, 0, 0)))
    return trap.intersect(keep)


# ============================================================================
# Endplate <-> leg geometry — ONE shared model for BOTH ends (they CANNOT diverge)
# ============================================================================
# Each endplate is the same shape mirrored: a solid that closes its end, wraps its
# leg with a T-thick WALL, nests over the kept leg shell with EP_LEG_CLR clearance,
# and leaves EP_LEG_BUFFER of solid body between the leg's dovetail tenon and that
# wall. Measuring everything INBOARD from each endplate's outer face ("tip") with
# the SAME three constants guarantees both ends are identical by construction:
#   pocket edge = tip  ∓ T            (the endplate wall is T thick)
#   shell  edge = pocket ∓ EP_LEG_CLR (the kept rail shell sits a clearance inboard)
#   leg tenon   = shell ∓ EP_LEG_BUFFER          → station ∓ DT_FACE_HW further in
# (the BUFFER is SOLID BODY, so it's measured from the SHELL face where material
#  actually begins — the wall<->shell clearance gap is air and doesn't count.)
# The end removal would otherwise strip the rail off the leg + leave the endplate
# clearing it with a big empty box; instead we KEEP a rail shell (its T wall IS the
# body wrap) over the leg, re-cutting the leg dovetail slot in it (_leg_shell).
KH_EP_THK     = 25.0          # keyhead endplate thickness in X (= keyhead_endplate.T_EP)
EP_LEG_CLR    = 0.4           # assembly clearance: endplate foot pocket vs the kept shell
EP_LEG_BUFFER = D.XBAR        # 10 mm solid body between the leg tenon and the endplate wall
EP_TIP_NX = KH_X - KH_EP_THK              # keyhead -X outer face (-636)
EP_TIP_PX = X_BRIDGE + D.WALL_THICKNESS   # bridge   +X outer tip  (16)


def _leg_geom(tip, sign):
    """All inboard from one endplate's outer face `tip`. `sign` = the direction from
    the tip toward the instrument body (+1 for the -X/keyhead end, -1 for the +X/
    bridge end). Returns (pocket_edge, shell_edge, station) for that leg."""
    pocket = tip + sign * T
    shell = pocket + sign * EP_LEG_CLR
    station = shell + sign * (EP_LEG_BUFFER + DT_FACE_HW)   # BUFFER of solid body from the shell face
    return pocket, shell, station


_PKT_NX, _SHELL_NX, _STN_NX = _leg_geom(EP_TIP_NX, +1)    # -X end → body is +X of the tip
_PKT_PX, _SHELL_PX, _STN_PX = _leg_geom(EP_TIP_PX, -1)    # +X end → body is -X of the tip
# the kept shell spans from its pinned outer edge to the rail-takeover join line:
LEG_SHELL_NX = (_SHELL_NX, KH_X)            # -X leg: -625.6 .. -611
LEG_SHELL_PX = (TP_EP_GX, _SHELL_PX)        # +X leg: -17.5 .. 5.6
# leg stations: (+X leg, -X leg) — each set so its tenon leaves EP_LEG_BUFFER of body:
LEG_STATIONS_X = (_STN_PX, _STN_NX)         # (-18.4, -601.6)


def _leg_shell(sx, x0, x1):
    """The kept rail shell around one leg station (both rails), spanning x0..x1
    over the rail Y-bands, from the bed up to the FOOT LINE (z = KH_DT_Z0 =
    -23.15). The shell only wraps the leg tenon + its 10 mm border BELOW the foot
    line; ABOVE the foot line (z -23.15..6) is the endplate's own solid fill band,
    not the shell -- so the shell stops at -23.15 and the endplate band sits on
    top of it. Re-cut the leg dovetail slot in it afterward."""
    out = None
    z1 = KH_DT_Z0                                     # foot line (-23.15); the endplate's
                                                      # solid fill band takes over above this
    for yr, s in ((Y_HI, 1), (Y_LO, -1)):
        # bottom EXACTLY on the bed (Z_BOT) -- the same constant the chassis/endplate
        # floors use -- so the shell can't poke below the instrument floor. (This is a
        # UNION, so it needs no -Z boolean overshoot; the leg-slot CUT below overshoots
        # on its own.)
        sh = box_at(x1 - x0, T, z1 - Z_BOT,
                    x=(x0 + x1) / 2, y=yr, z=(Z_BOT + z1) / 2)
        sh = sh.cut(_leg_dt_slot(sx, yr, s))
        out = sh if out is None else out.union(sh)
    return out


def _tongue(s, yr, socket=False, depth=None):
    """Dovetail prism at split X=s on the rail at Y=yr: a trapezoid (flaring +X in
    Y) extruded in Z. The −X segment carries it; the +X segment gets it as a socket
    (with clearance, open-topped). It bottoms on a shoulder of height _SH. `depth`
    is the +X reach (default _DT). Used for the inter-SEGMENT joints (the bridge/
    keyhead end joints use the low _br_tongue/_kh_tongue dovetails instead)."""
    d = _DT if depth is None else depth
    g = _CLR if socket else 0.0
    wr, wt = (_WR + g) / 2, (_WT + g) / 2
    z0 = Z_BOT + _SH
    z1 = (Z_TOP + 14.0) if socket else Z_TOP
    if TP_X1 < s < TP_X0:                 # deck span: stop at the deck-groove FLOOR so
        z1 = TP_GZ0 - TP_TG_DEPTH          # the segment joint never blocks the groove
                                           # (z -6 .. 0) the deck tongue slides through
    pts = [(s - 2, yr - wr), (s - 2, yr + wr), (s + d, yr + wt), (s + d, yr - wt)]
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def _end_dt(x_face, into, yc, z0, z1, socket=False, top_clr=TP_TG_DEPTH):
    """ONE Y-flaring vertical dovetail on an end-contact face at x=x_face, Z-extruded
    z0..z1, centred on Y=yc. `into` (+1/-1) points from the face toward the endplate
    tip: the trapezoid is NARROW at x_face (rail/shell side) and WIDE KH_DT_DEPTH into
    the endplate, so string tension can't draw the wide foot back out. The body carries
    it (tenon); the endplate cuts it (socket=True widens it by the clearance all round).
    `top_clr` raises the SOCKET top above the tenon top (z1) so the tenon seats on its
    real stop, not the mortise ceiling: the UPPER dovetail uses TP_TG_DEPTH (its top sits
    in the deck zone); the LOWER passes KH_DT_SEAT -- a hair above the fill-zone floor."""
    g = KH_DT_CLR if socket else 0.0
    wr, wt = KH_DT_WR + g, KH_DT_WT + g
    x_in = x_face + into * KH_DT_DEPTH
    z_hi = z1 + (top_clr if socket else 0.0)
    pts = [(x_face, yc - wr), (x_face, yc + wr),        # narrow (rail/shell face)
           (x_in, yc + wt), (x_in, yc - wt)]            # wide (into the endplate)
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z_hi - z0)


def _kh_tongue(yc, socket=False):
    """Keyhead joinery at Y=yc: the two stacked dovetails of the L-shaped joint (see the
    KH_DT_* block). LOWER on the wall<->leg-shell face (x=_SHELL_NX, z bed..foot line);
    UPPER on the foot<->rail-end face (x=KH_X, z foot line..deck-groove floor). Both wide
    -X into the keyhead so the +X string pull is gripped. Body carries them; the keyhead
    drops on and sockets them. socket=True adds clearance + open tops for the cut."""
    lower = _end_dt(_SHELL_NX, -1, yc, Z_BOT, KH_DT_Z0, socket, top_clr=KH_DT_SEAT)
    upper = _end_dt(KH_X, -1, yc, KH_DT_Z0, TP_GZ0 - TP_TG_DEPTH, socket)
    return lower.union(upper)


def _br_tongue(yc, socket=False):
    """Bridge joinery at Y=yc: the mirror of _kh_tongue across the +X takeover line. LOWER
    on the wall<->leg-shell face (x=_SHELL_PX, z bed..foot line); UPPER on the foot<->rail
    face (x=TP_EP_GX, z foot line..deck-groove floor). Both wide +X into the bridge so the
    +X bearing wrap (which pulls the bridge -X) can't draw the wide foot out. Body carries
    them; the bridge drops on and sockets them. socket=True adds clearance + open tops."""
    lower = _end_dt(_SHELL_PX, +1, yc, Z_BOT, KH_DT_Z0, socket, top_clr=KH_DT_SEAT)
    upper = _end_dt(TP_EP_GX, +1, yc, KH_DT_Z0, TP_GZ0 - TP_TG_DEPTH, socket)
    return lower.union(upper)


def _seg_box(a, b):
    h = (Z_TOP + 18.0) - (Z_BOT - 6.0)
    return box_at(abs(a - b) + 0.02, (Y_HI - Y_LO) + 40.0, h,
                  x=(a + b) / 2, y=(Y_HI + Y_LO) / 2, z=(Z_TOP + 18.0 + Z_BOT - 6.0) / 2)


def _is_split(x):
    return any(abs(x - s) < 1e-6 for s in SPLIT_X)


def _largest(seg):
    """Keep only the largest solid: the lightening diamonds + wire raceways + joint
    cuts can pinch off tiny disconnected slivers near the splits; those print as
    loose chips. Drop them (each is <1 % of the body and isn't attached anyway)."""
    sols = seg.val().Solids()
    if len(sols) <= 1:
        return seg
    return cq.Workplane("XY").add(max(sols, key=lambda s: s.Volume()))


def _segments():
    full = _build_full()
    # +X-most bound reaches past the rail +X end + its bridge dovetail tongues
    edges = [X_BRIDGE + 2.0] + sorted(SPLIT_X, reverse=True) + [X_NUT]
    segs = []
    for i in range(len(edges) - 1):
        a, b = edges[i], edges[i + 1]                 # a (+X) > b (−X)
        seg = full.intersect(_seg_box(a, b))
        if _is_split(b):                              # −X boundary split → +X side → socket
            for yr in (Y_HI, Y_LO):
                seg = seg.cut(_tongue(b, yr, socket=True))
        if _is_split(a):                              # +X boundary split → −X side → tongue
            for yr in (Y_HI, Y_LO):
                seg = seg.union(_tongue(a, yr))
        segs.append(_largest(seg))
    return segs


segments = _segments()
