"""Chassis frame (§8) — PCTG. Ties the bridge, screw rail, motor bank, and a nut
keyhead into ONE rigid frame.

The strings pull the bridge and nut toward each other (~10×100 N) at the speaking
height, which would bow the instrument; the chassis resists that. The stiffness
comes from DEPTH: two tall longitudinal side rails (web from just under the
strings down to the motor floor) run the whole length and are tied by bottom
cross-ribs, plus a keyhead at the nut. PCTG.

Bodies are modelled SOLID — weight is set by the slicer (wall count + low infill),
not by modelled lightening holes.

Too long for one print (>255 mm): SPLIT into ~3 segments joined with sliding
dovetails (slide in from one direction, hard-stop at the mount position, glued).
The dovetail joinery is not modelled yet — TODO. Built in global position.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import motor_bank as MB
from .helpers import box_at

T        = 3.0                         # wall thickness
X_BRIDGE = 6.0                         # +X (bridge) end
X_NUT    = -(D.MOUNTING_SPAN + 12.0)   # past the tuners at −MOUNTING_SPAN
Z_TOP    = D.STRING_Z - 6.0            # just under the speaking length
Z_BOT    = MB.Z_LO                     # motor-floor bottom
Y_HI     = D.BRIDGE_AXLE_Y + 1.0       # +Y rail, just outside the bridge uprights
Y_LO     = MB.Y_LO - 2.0               # −Y rail, just outside the motor bodies
_XC      = (X_BRIDGE + X_NUT) / 2
_ZC      = (Z_TOP + Z_BOT) / 2
_RIB_H   = 5.0                         # cross-rib height (sits on the very bottom)
_RIB_Z   = Z_BOT + _RIB_H / 2          # below the motors
_RIB_X   = [-15, -135, -255, -375, -495, -575]   # tie stations along the length


def _rail(y):
    """A tall longitudinal web (deep → bow-stiff), modelled solid (slicer infill
    sets weight)."""
    L = X_BRIDGE - X_NUT
    return box_at(L, T, Z_TOP - Z_BOT, x=_XC, y=y, z=_ZC)


def _build() -> cq.Workplane:
    body = _rail(Y_HI).union(_rail(Y_LO))
    # bottom cross-ribs tie the two rails (and touch the motor-bank floor)
    for x in _RIB_X:
        body = body.union(box_at(T, Y_HI - Y_LO, _RIB_H, x=x, y=(Y_HI + Y_LO) / 2, z=_RIB_Z))
    # keyhead: end cross-block at the nut, rising to the string height to carry
    # the 10 tuners; tied to both rails.
    ky = D.nut_y(D.N_STRINGS - 1) + 8.0
    keyhead = box_at(18.0, 2 * ky, Z_TOP + 8.0 - Z_BOT,
                     x=X_NUT + 9.0, y=0, z=(Z_TOP + 8.0 + Z_BOT) / 2)
    # link the keyhead out to both side rails at the bottom
    keyhead = keyhead.union(box_at(18.0, Y_HI - Y_LO, _RIB_H,
                                   x=X_NUT + 9.0, y=(Y_HI + Y_LO) / 2, z=_RIB_Z))
    return body.union(keyhead)


chassis = _build()
