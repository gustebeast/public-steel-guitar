"""Keyhead (-X) endplate + NUT BLOCK — PA6-GF, ONE merged 25 mm piece (x -636..-611).

The nut block (string termination) is fused into a simple FULL-WIDTH solid prism
(rail outer to rail outer) that TAKES OVER the rail -X ends, so its edge shows from
the front like the bridge endplate. It INSTALLS LAST, dropping straight down (+Z→-Z)
with the deck panels already in place. It:
  - closes the -X end of the box (its solid +X face stops the deck panels sliding -X);
  - terminates the strings (gauged break edge + 2-row clamps), bearing on solid
    PA6-GF — no separate nut block, no 4 corner bolts;
  - sockets a dovetail tongue on each rail end (mirrors the bridge joint) -> X+Y lock
    + grip against the +X string tension; locked in +Z by ONE thread-forming screw up
    from the chassis floor bottom into the solid body.

Service: send motors slack, back off the clamp set screws, remove the +Z screw,
lift this piece out, slide the deck panels off -X.
"""

from __future__ import annotations

from . import dimensions as D
from . import chassis as CH
from . import nut_block as NB
from .helpers import box_at, heal

# ONE part (x −636 .. −611, PA6-GF), FULL-WIDTH (rail outer to rail outer) so it TAKES
# OVER the whole −X end and its edge shows from the front, mirroring the bridge endplate.
# Per the endplate methodology it's AS SOLID AS POSSIBLE: a solid block from the deck
# level (z6) down to the bed -- so the block itself is the −X cross-tie (no separate
# crossbar) -- with the nut block the only thing reaching above the deck and foot
# clearance hollowed only over the −X legs (XBAR above the tenon). Installs LAST,
# dropping straight DOWN (+Z→−Z): it sockets a dovetail tongue on each rail end (X+Y
# lock + grip vs the +X string tension) and is held by those alone (no screw). Nut
# block fused in (~15 % infill).
T_EP = CH.KH_EP_THK                        # FULL thickness (X), at the top only (=25; the leg
                                           # shell's -X edge is pinned to this so the -X wall = T)
XHI  = CH.KH_X                             # +X (inboard) face (-611); the rail end stops
                                           # EP_TOP_CLR short of it (CH.KH_RAIL_X)
XLO  = XHI - T_EP                          # = -636
KX   = (XLO + XHI) / 2
YFL  = CH.Y_LO - CH.T / 2                   # full width: -Y rail outer face
YFH  = CH.Y_HI + CH.T / 2                   # +Y rail outer face
Z6    = CH.TP_GZ1                          # deck/top-plate level = general plate top
FOOT_Z = CH.KH_DT_Z0                       # foot line (-23.15): fill band bottom / wall-box top
NB_HW = 41.0                               # nut-block half-width (Y); riser ties it down
NB_Z0 = 10.0                               # nut-block base Z
# FOOT POCKET: the chassis now KEEPS a ~10 mm rail shell hugging each -X leg socket
# (CH._leg_shell over CH.LEG_SHELL_NX), capped at the foot line (z -23.15); the keyhead
# is solid AROUND that shell and nests over it as it drops -Z. The pocket only clears
# z = Z_BOT .. FOOT_Z (over the shell), NOT full-Z -- so the solid fill band (z -23.15..6)
# stays intact over the legs. leg -> 10 mm rail wall -> keyhead, touching.
LEG_CLR = CH.EP_LEG_CLR                    # assembly clearance around the kept chassis shell (shared)
LEG_SHELL_X0, LEG_SHELL_X1 = CH.LEG_SHELL_NX     # -625.6 .. -611 (rail-takeover region)


def _build():
    yc, yw = (YFL + YFH) / 2, YFH - YFL
    # 1) FILL ZONE (z -23.15 .. 6): a SOLID slab over the FULL endplate X-Y footprint --
    # computed from the endplate's own Y extent (YFL..YFH) and the fill-zone X/Z extents
    # (NOT hardcoded strips). This band IS the -X cross-tie and ties the rails. The -X end
    # has NO cut in this band at all (the +X stringing window is a bridge-only feature).
    w = box_at(T_EP, yw, Z6 - FOOT_Z, x=KX, y=yc, z=(Z6 + FOOT_Z) / 2)
    # 2) BELOW z -23.15 (foot region): thin to a 10 mm wall -- only the exterior faces
    # (the -X end face + the two +-Y side faces) stay solid at CH.T; the interior is
    # hollow. Build the full footprint box, then cut the interior inset by CH.T on the
    # +-Y sides and the +X (interior) side. The -X end face is the instrument's end, the
    # +-Y faces are the side walls; +X opens to the rest of the chassis box so it is part
    # of the inset interior (the rail-end shells + tongues come from the chassis side).
    foot = box_at(T_EP, yw, FOOT_Z - CH.Z_BOT, x=KX, y=yc, z=(FOOT_Z + CH.Z_BOT) / 2)
    # hollow = footprint inset by CH.T on the two +-Y walls and the +X face; the -X end
    # face wall is kept (XLO + CH.T). Reaches up to FOOT_Z and down past the bed.
    hol_y0 = YFL + CH.T                                   # +Y-side inner face (inset by wall)
    hol_y1 = YFH - CH.T                                   # -Y-side inner face (inset by wall)
    foot = foot.cut(box_at((XHI + 1.0) - (XLO + CH.T), hol_y1 - hol_y0,
                           (FOOT_Z + 0.1) - (CH.Z_BOT - 1.0),
                           x=((XLO + CH.T) + (XHI + 1.0)) / 2,
                           y=(hol_y0 + hol_y1) / 2,
                           z=((CH.Z_BOT - 1.0) + (FOOT_Z + 0.1)) / 2))
    w = w.union(foot)
    # nut block (the only thing reaching above the deck) + a riser tying it to the block
    w = w.union(box_at(T_EP, 2 * NB_HW, NB_Z0 - Z6, x=KX, y=0, z=(NB_Z0 + Z6) / 2))
    w = w.union(NB.nut_block.translate((D.NUT_BLOCK_X, 0, D.STRING_Z)))
    w = w.intersect(box_at(T_EP, 4000.0, 4000.0, x=KX, y=0, z=0))
    # FOOT POCKET: pocket exactly the kept chassis rail shell (+ clearance) out of each
    # -X leg station so the keyhead nests over it as it drops -Z. It ONLY clears z =
    # Z_BOT .. FOOT_Z (over the shell, capped at -23.15) -- NOT full-Z -- so the solid
    # fill band above stays intact over the legs.
    for yr, s in ((CH.Y_HI, 1), (CH.Y_LO, -1)):
        yf = yr + s * CH.T / 2 + s * LEG_CLR        # shell outer face + clearance
        yi = yr - s * CH.T / 2 - s * LEG_CLR        # shell inner face + clearance
        w = w.cut(box_at((XHI + 1.0) - (LEG_SHELL_X0 - LEG_CLR), abs(yf - yi),
                         FOOT_Z - (CH.Z_BOT - 1.0),       # stop AT the foot line (= band floor):
                         x=((LEG_SHELL_X0 - LEG_CLR) + (XHI + 1.0)) / 2,   # no +0.1 step into the band
                         y=(yf + yi) / 2, z=((CH.Z_BOT - 1.0) + FOOT_Z) / 2))
    # rail-end dovetail sockets (grip the rail tongues; X+Y lock vs the string tension)
    for ycc in (CH.Y_HI, CH.Y_LO):
        w = w.cut(CH._kh_tongue(ycc, socket=True))
    return heal(w)


keyhead_endplate = _build()
