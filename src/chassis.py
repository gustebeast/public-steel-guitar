"""Chassis frame (§8) — PCTG. ONE rigid frame that absorbs the motor bank and
ties in the bridge, screw rail, and a nut keyhead, SPLIT into glued segments.

The strings pull the bridge and nut toward each other (~10×100 N) at the speaking
height, which would bow the instrument; the chassis resists that. The stiffness
comes from DEPTH: two solid longitudinal side rails (from just under the strings
down to the motor floor) run the whole length, tied by bottom cross-ribs and the
motor-bank floor, plus a keyhead at the nut. The motor faceplate walls (with their
NEMA17 patterns) are fused in. Bodies are modelled SOLID — the slicer's walls +
infill set the strength-to-weight (no modelled lightening).

Too long for one print (~630 mm > 255 mm bed), so it's cut into 3 segments joined
by SLIDING DOVETAILS on the side rails: each joint's tongue flares toward +X
(locking the segments against the string pull), you drop the next segment straight
DOWN onto it (one direction), and it bottoms on a shoulder that sets the position —
then glue. The cuts fall in the ~0.7 mm gaps BETWEEN motor walls, so no motor
mount is split. Built in global position; the segments assemble into the whole.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import motor_bank as MB
from .components import MOTOR_PULLEY_STANDOFF
from .helpers import box_at

T        = 8.0                         # rail thickness (solid; slicer infills)
X_BRIDGE = 6.0                         # +X (bridge) end
X_NUT    = -(D.MOUNTING_SPAN + 12.0)   # past the tuners at −MOUNTING_SPAN
Z_TOP    = D.STRING_Z - 6.0            # just under the speaking length
Z_BOT    = MB.FLOOR_TOP - 11.0         # 11 mm chunky rib depth below the motor rest
Y_HI     = D.BRIDGE_AXLE_Y + 1.0       # +Y rail, just outside the bridge uprights
Y_LO     = (D.string_y(0) - MOTOR_PULLEY_STANDOFF - D.MOTOR_BODY_LEN
            - D.MOTOR_PCB_LEN - 6.0)   # −Y rail, just outside the motor PCBs
_XC, _ZC = (X_BRIDGE + X_NUT) / 2, (Z_TOP + Z_BOT) / 2
_RIB_W   = 10.0                        # cross-rib X-width (chunky section → slicer infills)
# A chunky rail-to-rail rib UNDER EACH MOTOR (the motor rests on it, its wall sits
# on it, and it ties the two rails) replaces a solid floor — far lighter for the
# strength. Plus a rib near the bridge and near the nut.
_RIB_X   = [-15.0] + [D.motor_pos(i)[0] for i in range(D.N_STRINGS)] + [-575.0]

SPLIT_X  = [-220.0, -440.0]            # 2 cuts → 3 segments < 255 mm, in motor-wall gaps
_DT, _WR, _WT, _SH, _CLR = 8.0, 4.0, 7.0, 4.0, 0.3   # dovetail: depth, root/tip W, shoulder, fit


def _rail(y):
    """A tall solid longitudinal rail (deep → bow-stiff); slicer infill sets weight."""
    return box_at(X_BRIDGE - X_NUT, T, Z_TOP - Z_BOT, x=_XC, y=y, z=_ZC)


def _rib(x, w=_RIB_W):
    """Chunky cross-rib, rail-to-rail, its top flush with the motor rest (FLOOR_TOP)."""
    return box_at(w, Y_HI - Y_LO, MB.FLOOR_TOP - Z_BOT,
                  x=x, y=(Y_HI + Y_LO) / 2, z=(MB.FLOOR_TOP + Z_BOT) / 2)


def _build_full() -> cq.Workplane:
    body = _rail(Y_HI).union(_rail(Y_LO))
    for x in _RIB_X:                                  # per-motor + bridge/nut cross-ribs
        body = body.union(_rib(x))
    ky = D.nut_y(D.N_STRINGS - 1) + 8.0               # keyhead at the nut carries the tuners
    body = body.union(box_at(18.0, 2 * ky, Z_TOP + 8.0 - Z_BOT,
                             x=X_NUT + 9.0, y=0, z=(Z_TOP + 8.0 + Z_BOT) / 2))
    body = body.union(_rib(X_NUT + 9.0, w=18.0))      # tie the keyhead to both rails
    body = body.union(MB.motor_bank)                  # fuse in the motor faceplate walls
    return body


def _tongue(s, yr, socket=False):
    """Dovetail prism at split X=s on the rail at Y=yr: a trapezoid (flaring +X in
    Y) extruded in Z. The −X segment carries it; the +X segment gets it as a socket
    (with clearance, open-topped). It bottoms on a shoulder of height _SH."""
    g = _CLR if socket else 0.0
    wr, wt = (_WR + g) / 2, (_WT + g) / 2
    z0 = Z_BOT + _SH
    z1 = (Z_TOP + 14.0) if socket else Z_TOP
    pts = [(s - 2, yr - wr), (s - 2, yr + wr), (s + _DT, yr + wt), (s + _DT, yr - wt)]
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def _seg_box(a, b):
    h = (Z_TOP + 18.0) - (Z_BOT - 6.0)
    return box_at(abs(a - b) + 0.02, (Y_HI - Y_LO) + 40.0, h,
                  x=(a + b) / 2, y=(Y_HI + Y_LO) / 2, z=(Z_TOP + 18.0 + Z_BOT - 6.0) / 2)


def _is_split(x):
    return any(abs(x - s) < 1e-6 for s in SPLIT_X)


def _segments():
    full = _build_full()
    edges = [X_BRIDGE] + sorted(SPLIT_X, reverse=True) + [X_NUT]   # +6, -205, -420, -627
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
