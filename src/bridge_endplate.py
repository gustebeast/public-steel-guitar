"""Bridge endplate (§8) — PCTG, printed FLAT, joined to the body by mortise/tenon.

ONE solid piece that closes the box at the +X end AND carries the bridge-bearing
axle (the 90° string turn — the highest-load point in the instrument). Because it
prints flat (on its face) it needs no supports, so it can be fully solid and
featured; glued tenons into the rail ends drive the bearing load straight into the
bow rails — far stronger than the old bolted bridge support. Replaces both the
bridge support and the +X bulkhead. Built in global position.

Layout: a solid CAP (+X of all the mechanism) closes the box rail-to-rail; two
ARMS reach −X at the field edges (clear of the carriages) to hold the axle above
the strings, linked by a TIE BAR; TENONS protrude −X into mortises in the rails.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from .screw_rail import screw_rail as _screw_rail
from .helpers import box_at, cyl_y

X0   = CH.X_BRIDGE                 # join line (the rails end here; cap is +X of it)
X1   = X0 + 8.0                    # +X tip
ARM_X = D.BRIDGE_AXLE_X - 4.0      # arms reach −X to past the axle
ARM_W = 6.0                        # arm thickness (Y)
TIE_Z = D.STRING_Z + 6.0          # tie bar / arm top, clear above the strings
AXLE_BORE = D.BRIDGE_AXLE_D + 0.4


def _cap() -> cq.Workplane:
    """Solid box-closure plate at the +X end, lightened with diamonds (flat-printed,
    so the holes cost nothing); a frame is kept around the edges and the tenons."""
    xc, thk = (X0 + X1) / 2, X1 - X0
    w = box_at(thk, CH.Y_HI - CH.Y_LO, CH.Z_TOP - CH.Z_BOT,
               x=xc, y=(CH.Y_HI + CH.Y_LO) / 2, z=(CH.Z_TOP + CH.Z_BOT) / 2)
    H, WEB, M = 11.0, 7.0, 9.0
    step = 2 * H + WEB
    yc = (CH.Y_LO + CH.Y_HI) / 2
    cz = CH.Z_TOP - M - H
    while cz - H >= CH.Z_BOT + M:
        cy = yc - step * 8
        while cy <= yc + step * 8:
            if CH.Y_LO + M <= cy - H and cy + H <= CH.Y_HI - M:
                w = w.cut(CH._diamond(cy, cz, H, xc, thk))
            cy += step
        cz -= step
    return w


def _arm(sy) -> cq.Workplane:
    """Edge arm (clear of the strings) reaching −X from the cap to hold the axle."""
    z_lo = CH.Z_TOP - 4.0
    arm = box_at(X0 - ARM_X, ARM_W, TIE_Z - z_lo,
                 x=(X0 + ARM_X) / 2, y=sy, z=(TIE_Z + z_lo) / 2)
    return arm.cut(cyl_y(AXLE_BORE, ARM_W + 2, y0=sy - ARM_W / 2 - 1,
                         x=D.BRIDGE_AXLE_X, z=D.BRIDGE_BEARING_Z))


_SRX = D.SCREW_X + 7.0            # screw-rail +X face (DEPTH/2 past the screw line)


def _build() -> cq.Workplane:
    body = _cap()
    for sy in (-D.BRIDGE_AXLE_Y, D.BRIDGE_AXLE_Y):
        body = body.union(_arm(sy))
    # tie bar linking the arm tops above the strings
    body = body.union(box_at(X0 - ARM_X, 2 * D.BRIDGE_AXLE_Y + ARM_W, 5.0,
                             x=(X0 + ARM_X) / 2, y=0, z=TIE_Z - 2.5))
    # FUSE IN the screw-support rail and bridge it to the cap at the bottom + tie it
    # up to the bearing arms at the edges — the whole bridge end becomes one solid
    # piece (screw support + bearing support + box closure) with continuous material.
    body = body.union(_screw_rail)
    body = body.union(box_at(X0 - _SRX, 2 * D.BRIDGE_AXLE_Y, 10.0,    # bottom bridge → cap
                             x=(X0 + _SRX) / 2, y=0, z=D.SUPPORT_BRG_Z))
    z_lo = CH.Z_TOP - 4.0
    for sy in (-D.BRIDGE_AXLE_Y, D.BRIDGE_AXLE_Y):                    # edge webs rail→arm
        body = body.union(box_at(X0 - _SRX, ARM_W, z_lo - D.SUPPORT_BRG_Z,
                                 x=(X0 + _SRX) / 2, y=sy, z=(z_lo + D.SUPPORT_BRG_Z) / 2))
    # tenons protruding −X into the rail-end mortises (glued; the string pull
    # compresses this joint, so it is self-tightening)
    for py, pz in CH.ENDPLATE_PEGS:
        body = body.union(box_at(CH.PEG_L, CH.PEG, CH.PEG,
                                 x=X0 - CH.PEG_L / 2, y=py, z=pz))
    return body


bridge_endplate = _build()
