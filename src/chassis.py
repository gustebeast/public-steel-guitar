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
from . import nut_block as NB

T        = 8.0                         # rail thickness (solid; slicer infills)
X_BRIDGE = 6.0                         # +X (bridge) end — the rails end here; the bridge
                                       #   endplate caps them (a separate flat-printed part)
X_NUT    = -(D.MOUNTING_SPAN + 24.0)   # −X end, extended to carry the nut block;
                                       # rail ends FLUSH with the end bulkhead's
                                       # outer face (NUT_BLOCK_X − 9 − 15)
Z_TOP    = D.STRING_Z - 6.0            # body deck, 6 mm under the strings (normal action)
Z_BOT    = MB.BED_Z                    # print bed (shared with the motor walls)
Y_HI     = D.BRIDGE_AXLE_Y + 7.0       # +Y rail, outboard enough to clear the bearing arm
Y_LO     = (D.string_y(0) - MOTOR_PULLEY_STANDOFF - D.MOTOR_BODY_LEN
            - D.MOTOR_PCB_LEN - 6.0)   # −Y rail, just outside the motor PCBs
_XC, _ZC = (X_BRIDGE + X_NUT) / 2, (Z_TOP + Z_BOT) / 2
_RIB_W   = 10.0                        # cross-rib X-width (chunky section → slicer infills)
# Top-plate retention grooves (top_plate.py rides these): a slot in each rail
# inner face below the rail top, leaving a ~3 mm lip so the deck plates can't
# fall out when the instrument is inverted (they pull straight out toward −X).
TP_X0, TP_X1   = -16.0, -624.0         # groove X span (deck extent)
TP_GZ0, TP_GZ1 = -4.0, -1.0            # recessed deck (10 mm under strings):
                                       # groove z -4..-1, ~9 mm rail lip above
TP_GROOVE_D    = 3.0                    # depth into the rail (Y)
# A chunky rail-to-rail rib UNDER EACH MOTOR (the motor rests on it, its wall sits
# on it, and it ties the two rails) replaces a solid floor — far lighter for the
# strength. Plus a rib at the +X end (tying the rails behind the endplate) and one
# near the nut.
_RIB_X   = ([X_BRIDGE - 6.0]                       # bridge tie, kept −X of the cap (no clip)
            + [D.motor_pos(i)[0] for i in range(D.N_STRINGS)] + [-575.0])

# Bridge-endplate joint: the +X rail ends carry a sliding dovetail TONGUE on each
# side; the endplate caps + sockets them and drops down to engage (see
# bridge_endplate.py). ENDPLATE_JOINT_Y are the two rail centre-lines. ENDPLATE_DT
# is shallow (< cap thickness) so the socket is BLIND — the cap's +X face stays
# solid for strength.
ENDPLATE_JOINT_Y = (Y_HI, Y_LO)
ENDPLATE_DT = 5.0

SPLIT_X  = [-220.0, -440.0]            # 2 cuts → 3 segments < 255 mm, in motor-wall gaps
# dovetail: depth, root/tip width, shoulder, fit. Tip width kept ≤ T−3.2 so the
# socket walls in the 8 mm rail stay ≥1.6 mm (2 passes of a 0.8 mm nozzle).
_DT, _WR, _WT, _SH, _CLR = 8.0, 2.5, 4.5, 4.0, 0.3

# ── Pickup-mount tongue-and-groove (both rails) ──────────────────────────
# A locally-thickened BOSS strip on each rail's inner face carries an X-running
# GROOVE; the pickup bar's end tongues ride in it — even support across X, the
# mount slides in from +X before the endplate goes on (the endplate then caps
# the groove, retaining the mount). The groove's −X end is a hard stop at the
# 128 mm max pickup distance (fretboard lines live beyond). The boss sits
# BELOW the pickup's bottom (the +Y rail is only ~12 mm past string 10, so the
# pickup's end overhangs the boss); its underside is 45°-chamfered for the
# standing print, and the rail web behind it stays solid (no diamonds there).
PU_X0, PU_X1   = -168.0, X_BRIDGE      # groove run (−X end = hard stop: tongue half-
                                       # length 40 → pickup centre max −128)
PU_TNG_Z0, PU_TNG_Z1 = -25.5, -20.5    # tongue nominal Z band (groove adds 0.15/side);
                                       # bottom clears motor 0's PCB top (−25.85)
# X-lock stations: a hand-knob M4 button screw threads an insert in the −Y
# boss's ceiling and presses DOWN on the tongue inside the groove — friction
# pins the mount; knobs turn from above, over the open motor bay. TWO stations
# (both permanently fitted): their ±34 tongue-reach zones (−114..−46 and
# −173..−105) overlap to cover the whole 50..128 range — a single mid station
# would land inside the motor-0 service notch (below), and ±34 reach keeps the
# bar's sides STRAIGHT (tongue = bar width, no corner extensions).
PU_LOCK_XS     = (-80.0, -139.0)
# Motor-0 service notch: motor 0's PCB tail lives under the −Y boss, so its
# lift-out column needs the boss cut away over x −134..−91 (full boss height).
# The groove is interrupted there; the 80 mm tongue always bridges it with
# ≥40 mm engaged elsewhere.
PU_NOTCH_X0, PU_NOTCH_X1 = -134.0, -91.0
PU_BOSS_T      = 6.0                   # boss protrusion off the rail face
PU_GROOVE_D    = PU_BOSS_T             # groove runs the FULL boss depth — its inner
                                       # wall IS the rail web face, so the tongue
                                       # seats (0.45 shy of) flush with the side wall
PU_FACE_HI     = Y_HI - T / 2 - PU_BOSS_T    # +Y boss field face (+48.75)
PU_FACE_LO     = Y_LO + T / 2 + PU_BOSS_T    # −Y boss field face (−122.75)


def _pickup_boss(yr, s):
    """Boss strip + groove on the rail at centreline yr (s = +1 for the +Y rail,
    whose boss protrudes −Y). Returns (boss_solid, groove_cutter)."""
    face = yr - s * (T / 2 + PU_BOSS_T)            # field face of the boss
    rail_face = yr - s * T / 2
    x0, x1 = PU_X0 - 3.0, PU_X1                    # boss runs past the groove stop
    # bottom lip: groove floor (−25.65) + 3.65 of material = −29.3 (it only
    # carries the bar's weight and the lock screw's clamp), then the 45°
    # self-supporting chamfer down to the rail face. Top at −14.35 = exactly
    # where the groove's 45° roof lands at the face, so the roof and floor
    # share their y extents (and the pickup still clears the top by 0.57).
    prof = [(rail_face, -35.3), (face, -29.3),
            (face, -14.35), (rail_face, -14.35)]
    pts = [cq.Vector(x0, py, pz) for py, pz in prof]
    f = cq.Face.makeFromWires(cq.Wire.makePolygon([*pts, pts[0]]))
    boss = cq.Workplane("XY").add(cq.Solid.extrudeLinear(f, cq.Vector(x1 - x0, 0, 0)))
    groove = box_at(PU_X1 - PU_X0 + 1, PU_GROOVE_D + 0.5, (PU_TNG_Z1 - PU_TNG_Z0) + 0.3,
                    x=(PU_X0 + PU_X1 + 1) / 2,
                    y=face + s * ((PU_GROOVE_D + 0.5) / 2 - 0.5),
                    z=(PU_TNG_Z0 + PU_TNG_Z1) / 2)
    # Groove roof: a SINGLE 45° plane, high at the open face and descending to
    # the web — the only printable direction: roof material can only accrete
    # from the web wall (the face side of the opening has nothing under or
    # beside it, so any face-side flank floats; a chevron peak fails the same
    # way). The cut runs out through the boss's top-outer corner (a harmless
    # chamfer along the run). Uniform along the whole groove — the bar's
    # wedge-topped tongue sweeps it, so no flat patches are possible; the lock
    # inserts live in bumps ON the boss top instead (see _build_full).
    zt = PU_TNG_Z1 + 0.15
    tri = [(face, zt), (face, zt + PU_GROOVE_D),
           (face + s * PU_GROOVE_D, zt)]
    pts = [cq.Vector(PU_X0, py, pz) for py, pz in tri]
    f2 = cq.Face.makeFromWires(cq.Wire.makePolygon([*pts, pts[0]]))
    groove = groove.union(cq.Workplane("XY").add(
        cq.Solid.extrudeLinear(f2, cq.Vector(PU_X1 + 1 - PU_X0, 0, 0))))
    return boss, groove


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
                and cx + h < PU_X0 - 3.0             # solid web behind the pickup boss
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


def _lighten(plate, x, thick):
    """Punch a grid of self-supporting diamond holes into a bulkhead, leaving a
    solid perimeter frame (≥M), the 45° funnel edges, and ≥WEB webs — a shear truss
    instead of a solid plate."""
    zfull = Z_TOP - 8.0                                   # above this the plate is full width
    def yl(z): return Y_LO + max(0.0, zfull - z)
    def yr(z): return Y_HI - max(0.0, zfull - z)
    H, WEB, M = 10.0, 6.0, 6.0
    step = 2 * H + WEB
    def inside(y, z): return (Z_BOT + M <= z <= Z_TOP - M) and (yl(z) + M <= y <= yr(z) - M)
    yc = (Y_LO + Y_HI) / 2
    cz = Z_TOP - M - H
    while cz - H >= Z_BOT + M:
        cy = yc - step * 6
        while cy <= yc + step * 6:
            if all(inside(y, z) for y, z in
                   [(cy, cz + H), (cy, cz - H), (cy - H, cz), (cy + H, cz)]):
                plate = plate.cut(_diamond(cy, cz, H, x, thick))
            cy += step
        cz -= step
    return plate


def _end_bulkhead(x, thick):
    """Self-supporting end wall that closes the box at a string end: full width at
    the deck (ties both rails), 45° sides converging DOWN to a narrow base on the
    bed. Prints with no overhang (it builds up from the base); the lower-outer
    corners are removed and the interior is lightened with diamond holes (shear
    truss). Far better than a horizontal tie, which would bridge ~185 mm."""
    w = box_at(thick, Y_HI - Y_LO, Z_TOP - Z_BOT, x=x, y=(Y_HI + Y_LO) / 2, z=(Z_TOP + Z_BOT) / 2)
    w = w.edges("|X and <Z").chamfer(Z_TOP - Z_BOT - 8.0)
    return _lighten(w, x, thick)


def _build_full() -> cq.Workplane:
    body = _rail(Y_HI).union(_rail(Y_LO))
    for x in _RIB_X:                                  # per-motor + bridge/nut cross-ribs (−Z)
        body = body.union(_rib(x))
    # pickup-mount tongue-and-groove bosses on both rails' inner faces
    for yr, s in ((Y_HI, 1), (Y_LO, -1)):
        boss, groove = _pickup_boss(yr, s)
        body = body.union(boss).cut(groove)
    # X-lock stations: an insert BUMP on the −Y boss top (the sloped groove
    # roof leaves no flat ceiling to house the insert), screw bore descending
    # through solid sloped-ceiling material near the web; the knobbed M4
    # button's tip lands on the tongue's 45° wedge top — pressing it down AND
    # into the web. A pocket in the rail's inner face lets each Ø12 knob turn
    # (the web is solid here — diamonds are skipped behind the boss).
    _ly = Y_LO + T / 2 + 2.5                       # screw line, web side of the boss
    _bmid = (Y_LO + T / 2 + PU_FACE_LO) / 2        # boss centre
    for _lx in PU_LOCK_XS:
        # bump sits flush on the (raised) boss top but starts 0.85 back from
        # the face: the bar's clean-45° wedge only rises above −15 within that
        # first strip, so the bump clears its sweep comfortably
        _by = (PU_FACE_LO - 0.85 + (Y_LO + T / 2)) / 2
        body = body.union(box_at(10.0, PU_BOSS_T - 0.85, 4.2,
                                 x=_lx, y=_by, z=-12.45))
        body = body.cut(cyl(5.6, 4.8, z=-15.15).translate((_lx, _ly, 0)))
        body = body.cut(cyl(4.3, 6.5, z=-21.5).translate((_lx, _ly, 0)))
        body = body.cut(box_at(20.0, 3.6, 21.0,
                               x=_lx, y=Y_LO + T / 2 - 1.8, z=-5.5))
    # motor-0 service notch: clear the −Y boss from motor 0's lift column
    body = body.cut(box_at(PU_NOTCH_X1 - PU_NOTCH_X0, PU_BOSS_T + 0.3, 23.0,
                           x=(PU_NOTCH_X0 + PU_NOTCH_X1) / 2,
                           y=(Y_LO + T / 2 + PU_FACE_LO) / 2 + 0.15, z=-26.0))
    # keyhead: a thick bulkhead under the nut-block footprint (it sits on top, Z_TOP),
    # plus a compression wall its +X face bears against (string pull → self-tightening),
    # and pilot holes for the 4 corner heat-set inserts the retention bolts thread into.
    _kx = D.NUT_BLOCK_X - 9.0                               # under the block centre
    body = body.union(_end_bulkhead(_kx, 30.0))            # self-supporting bulkhead
    body = body.union(_rib(_kx, w=30.0))                   # bottom tie
    ky = D.nut_y(D.N_STRINGS - 1) + 9.0
    body = body.union(box_at(4.0, 2 * ky, 4.0,            # +X compression wall (below the strings)
                             x=D.NUT_BLOCK_X + 6.0, y=0, z=Z_TOP + 2.0))
    for sx in (D.NUT_BLOCK_X + NB.X_FRONT - 3.0, D.NUT_BLOCK_X + NB.X_BACK + 3.0):
        for sy in (-(NB.HW - 4.0), NB.HW - 4.0):          # insert pilots under the 4 corner bolts
            body = body.cut(cyl(5.6, 8.0, z=Z_TOP - 8.0).translate((sx, sy, 0)))
    # leg-socket joinery: a vertical sliding-dovetail slot in each rail's
    # OUTER face at the corner stations (solid web there). The printed socket
    # slides up from below and GLUES (it is only a separate part because the
    # chassis can't print below its bed); its barrel rim seats on the rail's
    # bottom face. The slot roof rises 45° toward the face — in-layer support
    # accretes from beyond the deep wall, same rule as the pickup groove.
    from .legs import LEG_STATIONS_X, DT_FACE_HW, DT_DEEP_HW, DT_DEPTH, DT_H
    for _sx in LEG_STATIONS_X:
        for _yr, _s in ((Y_HI, 1), (Y_LO, -1)):
            yf = _yr + _s * T / 2                          # outer face
            yd = yf - _s * DT_DEPTH                        # deep wall
            trap = (cq.Workplane("XY").workplane(offset=Z_BOT - 1.0)
                    .polyline([(_sx - DT_FACE_HW, yf), (_sx + DT_FACE_HW, yf),
                               (_sx + DT_DEEP_HW, yd), (_sx - DT_DEEP_HW, yd)])
                    .close().extrude(1.0 + DT_H + DT_DEPTH))
            keep = (cq.Workplane("YZ")
                    .polyline([(yf + _s, Z_BOT - 2.0),
                               (yf + _s, Z_BOT + DT_H + DT_DEPTH + 1.0),
                               (yd - _s, Z_BOT + DT_H - 1.0),
                               (yd - _s, Z_BOT - 2.0)])
                    .close().extrude(2 * DT_DEEP_HW + 4)
                    .translate((_sx - DT_DEEP_HW - 2, 0, 0)))
            body = body.cut(trap.intersect(keep))
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
    # carries the analog front-end board, sitting BELOW the pickup bar and
    # INBOARD of both the pickup-bar groove (at the rail face) and the leg
    # barrel - so it fouls neither. Bonds to the bridge rib (no cantilever),
    # prints as a vertical block off the bed. Two posts hold the board.
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
    # top-plate retention grooves: a slot cut INTO each rail from the inner
    # face (s = into-rail direction), z 3.5..7 with a ~3 mm lip up to the top
    for _yf, _s in ((Y_HI - T / 2, 1), (Y_LO + T / 2, -1)):
        body = body.cut(box_at(TP_X0 - TP_X1 + 4, TP_GROOVE_D + 0.5,
                               TP_GZ1 - TP_GZ0, x=(TP_X0 + TP_X1) / 2,
                               y=_yf + _s * TP_GROOVE_D / 2.0,
                               z=(TP_GZ0 + TP_GZ1) / 2))
    body = body.union(MB.motor_bank)                  # fuse in the motor faceplate walls
    # +X end: a sliding-dovetail tongue on each rail end; the bridge endplate caps
    # and sockets them (drops down to engage, glued).
    for yr in ENDPLATE_JOINT_Y:
        body = body.union(_tongue(X_BRIDGE, yr, depth=ENDPLATE_DT))
    return body


def _tongue(s, yr, socket=False, depth=None):
    """Dovetail prism at split X=s on the rail at Y=yr: a trapezoid (flaring +X in
    Y) extruded in Z. The −X segment carries it; the +X segment gets it as a socket
    (with clearance, open-topped). It bottoms on a shoulder of height _SH. `depth`
    is the +X reach (default _DT; the endplate joint uses a shallower, BLIND depth)."""
    d = _DT if depth is None else depth
    g = _CLR if socket else 0.0
    wr, wt = (_WR + g) / 2, (_WT + g) / 2
    z0 = Z_BOT + _SH
    z1 = (Z_TOP + 14.0) if socket else Z_TOP
    pts = [(s - 2, yr - wr), (s - 2, yr + wr), (s + d, yr + wt), (s + d, yr - wt)]
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def _seg_box(a, b):
    h = (Z_TOP + 18.0) - (Z_BOT - 6.0)
    return box_at(abs(a - b) + 0.02, (Y_HI - Y_LO) + 40.0, h,
                  x=(a + b) / 2, y=(Y_HI + Y_LO) / 2, z=(Z_TOP + 18.0 + Z_BOT - 6.0) / 2)


def _is_split(x):
    return any(abs(x - s) < 1e-6 for s in SPLIT_X)


def _segments():
    full = _build_full()
    # +X-most bound extends past the endplate tongues so they survive the segment cut
    edges = [X_BRIDGE + ENDPLATE_DT + 2.0] + sorted(SPLIT_X, reverse=True) + [X_NUT]
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
        segs.append(seg)
    return segs


segments = _segments()
