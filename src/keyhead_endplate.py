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
T_EP = 25.0                                # FULL thickness (X), at the top only
XHI  = CH.KH_X                             # +X face = rail -X end (-611)
XLO  = XHI - T_EP                          # = -636
KX   = (XLO + XHI) / 2
YFL  = CH.Y_LO - CH.T / 2                   # full width: -Y rail outer face
YFH  = CH.Y_HI + CH.T / 2                   # +Y rail outer face
Z6    = CH.TP_GZ1                          # deck/top-plate level = general plate top
ZSTEP = CH.KH_DT_Z0                         # foot-clearance top = XBAR above the leg tenon
NB_HW = 41.0                               # nut-block half-width (Y); riser ties it down
NB_Z0 = 10.0                               # nut-block base Z
FOOT_X0 = -625.0                           # foot clearance: -X edge (covers the leg dovetail)
# -X leg Y bands (from leg_socket_2/_3), clamped into the plate: hollow over each leg
LEG_BANDS = ((37.0, YFH), (YFL, -111.0))


def _build():
    yc, yw = (YFL + YFH) / 2, YFH - YFL
    # AS SOLID AS POSSIBLE: a solid block over the whole footprint from the deck level
    # (z6) down to the bed -- this block IS the -X cross-tie (no separate crossbar) and
    # is held by the rail-end dovetails (no screw). String holder (nut block) above z6.
    w = box_at(T_EP, yw, Z6 - CH.Z_BOT, x=KX, y=yc, z=(Z6 + CH.Z_BOT) / 2)
    # nut block (the only thing reaching above the deck) + a riser tying it to the block
    w = w.union(box_at(T_EP, 2 * NB_HW, NB_Z0 - Z6, x=KX, y=0, z=(NB_Z0 + Z6) / 2))
    w = w.union(NB.nut_block.translate((D.NUT_BLOCK_X, 0, D.STRING_Z)))
    w = w.intersect(box_at(T_EP, 4000.0, 4000.0, x=KX, y=0, z=0))
    # FOOT clearance: hollow over each -X leg below the XBAR-above-tenon line (the only
    # place we thin from the solid block) so the leg + the part's install drop clear
    for (y0, y1) in LEG_BANDS:
        w = w.cut(box_at(XHI - FOOT_X0, y1 - y0, ZSTEP - CH.Z_BOT,
                         x=(FOOT_X0 + XHI) / 2, y=(y0 + y1) / 2, z=(ZSTEP + CH.Z_BOT) / 2))
    # rail-end dovetail sockets (grip the rail tongues; X+Y lock vs the string tension)
    for ycc in (CH.Y_HI, CH.Y_LO):
        w = w.cut(CH._kh_tongue(ycc, socket=True))
    return heal(w)


keyhead_endplate = _build()
