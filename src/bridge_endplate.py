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
from .screw_rail import screw_rail as _screw_rail, HEIGHT as _SR_H
from .helpers import box_at, cyl, cyl_y

X0   = CH.X_BRIDGE                 # join line (the rails end here; cap is +X of it)
X1   = X0 + 8.0                    # +X tip
ARM_X = D.BRIDGE_AXLE_X - 4.0      # arms reach −X to past the axle
ARM_W = D.BRIDGE_ARM_W             # arm / edge-web thickness (Y) — kept clear of the +Y rail
TIE_Z = D.STRING_Z + 6.0          # tie bar / arm top, clear above the strings
AXLE_BORE = D.BRIDGE_AXLE_D + 0.4

# Stringing-access cutout (over the field): a clean rectangle with a UNIFORM cap
# border on every side. WIN_BORDER is that border to the cap top and the bearing
# arms; the diamond lightening is kept the same distance clear of it below.
WIN_BORDER = 4.0
WIN_HW     = D.BRIDGE_AXLE_Y - ARM_W / 2                  # out to the arm inner faces, so the
                                                          # edge carriages/string balls are reachable
WIN_Z1     = CH.Z_TOP - WIN_BORDER                        # top (rim to the cap top)
WIN_Z0     = WIN_Z1 - 16.0                                # bottom (rim of cap below)


def _cap() -> cq.Workplane:
    """Solid box-closure plate at the +X end, lightened with diamonds (flat-printed,
    so the holes cost nothing); a frame is kept around the edges and the tenons."""
    xc, thk = (X0 + X1) / 2, X1 - X0
    # span out to the rail OUTER faces so the cap fully caps the rail ends + covers
    # the dovetail sockets (no clipping into the rail sides)
    w = box_at(thk, CH.Y_HI - CH.Y_LO + CH.T, CH.Z_TOP - CH.Z_BOT,
               x=xc, y=(CH.Y_HI + CH.Y_LO) / 2, z=(CH.Z_TOP + CH.Z_BOT) / 2)
    H, WEB, M = 11.0, 7.0, 9.0
    step = 2 * H + WEB
    yc = (CH.Y_LO + CH.Y_HI) / 2
    cz = CH.Z_TOP - M - H
    while cz - H >= CH.Z_BOT + M:
        cy = yc - step * 8
        while cy <= yc + step * 8:
            in_field = CH.Y_LO + M <= cy - H and cy + H <= CH.Y_HI - M
            # keep a clear border around the stringing cutout (no diamonds in it)
            near_win = (abs(cy) - H <= WIN_HW + WIN_BORDER
                        and cz + H >= WIN_Z0 - WIN_BORDER
                        and cz - H <= WIN_Z1 + WIN_BORDER)
            if in_field and not near_win:
                w = w.cut(CH._diamond(cy, cz, H, xc, thk))
            cy += step
        cz -= step
    return w


def _arm(sy) -> cq.Workplane:
    """Edge arm (clear of the strings) holding the axle. Spans the FULL endplate
    X-depth (axle line → +X tip) so it fuses solidly to the cap and prints with no
    overhang when built up along X."""
    z_lo = CH.Z_TOP - 4.0
    arm = box_at(X1 - ARM_X, ARM_W, TIE_Z - z_lo,
                 x=(X1 + ARM_X) / 2, y=sy, z=(TIE_Z + z_lo) / 2)
    return arm.cut(cyl_y(AXLE_BORE, ARM_W + 2, y0=sy - ARM_W / 2 - 1,
                         x=D.BRIDGE_AXLE_X, z=D.BRIDGE_BEARING_Z))


_SRX = D.SCREW_X + 7.0            # screw-rail +X face (DEPTH/2 past the screw line)


def _build() -> cq.Workplane:
    body = _cap()
    for sy in (-D.BRIDGE_AXLE_Y, D.BRIDGE_AXLE_Y):
        body = body.union(_arm(sy))
    # tie bar linking the arm tops above the strings (full depth → +X tip)
    body = body.union(box_at(X1 - ARM_X, 2 * D.BRIDGE_AXLE_Y + ARM_W, 5.0,
                             x=(X1 + ARM_X) / 2, y=0, z=TIE_Z - 2.5))
    # FUSE IN the screw-support rail and bridge it to the cap at the bottom + tie it
    # up to the bearing arms at the edges — the whole bridge end becomes one solid
    # piece (screw support + bearing support + box closure) with continuous material.
    # The bottom + edge bridges run the FULL X-depth (screw line → +X tip).
    body = body.union(_screw_rail)
    body = body.union(box_at(X1 - _SRX, 2 * D.BRIDGE_AXLE_Y, 10.0,    # bottom bridge → tip
                             x=(X1 + _SRX) / 2, y=0, z=D.SUPPORT_BRG_Z))
    z_lo = CH.Z_TOP - 4.0
    sr_bot = D.SUPPORT_BRG_Z - _SR_H / 2                              # screw-rail −Z extent
    for sy in (-D.BRIDGE_AXLE_Y, D.BRIDGE_AXLE_Y):                    # edge webs rail→arm
        body = body.union(box_at(X1 - _SRX, ARM_W, z_lo - sr_bot,     # down to the rail bottom
                                 x=(X1 + _SRX) / 2, y=sy, z=(z_lo + sr_bot) / 2))
    # GUIDE-ROD cross-member: a bar at the guide-rod line (−X of the screws) carrying
    # the 10 anti-rotation rod tops, tied to the bearing arms — so the rods are part of
    # the endplate. Its BOTTOM face is flush with the carriage's guide-block top at the
    # default (top-of-travel) position, so it is the TOP HARD STOP: the carriage cannot
    # be driven up into the precision bridge bearings — it bottoms out on this bar first.
    GX = D.SCREW_X - D.GUIDE_ROD_DX
    gz0 = D.CARRIAGE_NOM_Z + 6.0                          # = guide-block top at default
    gz1 = gz0 + 6.0
    body = body.union(box_at(6.0, 2 * D.BRIDGE_AXLE_Y, gz1 - gz0, x=GX, y=0, z=(gz0 + gz1) / 2))
    link_top = z_lo + 3.0                                 # lap up into the arms for a solid fuse
    for sy in (-D.BRIDGE_AXLE_Y, D.BRIDGE_AXLE_Y):        # links to the arms
        body = body.union(box_at((ARM_X + 3.0) - GX, ARM_W, link_top - gz0,
                                 x=((ARM_X + 3.0) + GX) / 2, y=sy, z=(link_top + gz0) / 2))
    for i in range(D.N_STRINGS):                          # guide-rod top sockets
        body = body.cut(cyl(D.GUIDE_ROD_D + 0.1, gz1 - gz0 + 2, z=gz0 - 1)
                        .translate((GX, D.string_y(i), 0)))

    # STRINGING-ACCESS window: open the cap over the field (top-centre, between the
    # bearing arms) so each string threads over its bridge bearing and its end-nut
    # slots into the carriage from +X. Inboard of the arms (±BRIDGE_AXLE_Y) and below
    # the tie bar, so the axle support, dovetails and screw rail are untouched.
    body = body.cut(box_at((X1 - X0) + 2.0, 2 * WIN_HW, WIN_Z1 - WIN_Z0,
                           x=(X0 + X1) / 2, y=0, z=(WIN_Z1 + WIN_Z0) / 2))
    # SOCKET the sliding-dovetail tongue on each rail end (both side walls): the
    # endplate drops straight down onto the rail tongues and glues. The dovetail
    # locks it in X+Y; the string pull also compresses it against the rail ends.
    for yr in CH.ENDPLATE_JOINT_Y:
        body = body.cut(CH._tongue(CH.X_BRIDGE, yr, socket=True, depth=CH.ENDPLATE_DT))
    return body


bridge_endplate = _build()
