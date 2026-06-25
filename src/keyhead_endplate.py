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
from . import motor_bank as MB
from . import nut_block as NB
from .helpers import box_at, cyl, heal

# ONE part (x −636 .. −611, PA6-GF), FULL-WIDTH (rail outer to rail outer) so it
# TAKES OVER the rail −X ends and its edge shows from the front, mirroring the bridge
# endplate. In side view it's an **L**: the full 25 mm thickness only up top (where
# the nut block sits + the rail-end dovetails engage), and an 8 mm back plate (like
# the +X endplate) for the rest — the open +X-lower zone clears the −X legs, so no
# foot cutouts are needed. Installs LAST, dropping straight DOWN (+Z→−Z): it sockets
# a dovetail tongue on each rail end (X+Y lock + grip vs the +X string tension), and
# ONE screw up from the floor bottom locks it in +Z. Nut block fused in (~15 % infill).
T_EP = 25.0                                # FULL thickness (X), at the top only
XHI  = CH.KH_X                             # +X face = rail -X end (-611)
XLO  = XHI - T_EP                          # = -636
KX   = (XLO + XHI) / 2
YFL  = CH.Y_LO - CH.T / 2                   # full width: -Y rail outer face
YFH  = CH.Y_HI + CH.T / 2                   # +Y rail outer face
ZB   = MB.FLOOR_TOP                        # bottom: SEATS ON the keyhead floor
ZSTEP = CH.KH_DT_Z0                         # thick-top / 8 mm-back boundary (above the legs)
SCREW_X = CH.KH_SCREW_X                     # +Z hold-down screw (vertical), in the 8 mm back
SCREW_PILOT = 3.4                          # M4 thread-forming into the PA6-GF


def _build():
    yc, yw = (YFL + YFH) / 2, YFH - YFL
    # thick TOP (full 25 mm): holds the nut block + the rail-end dovetail sockets,
    # butts the rail end; sits above the -X leg sockets
    w = box_at(T_EP, yw, CH.Z_TOP - ZSTEP, x=KX, y=yc, z=(CH.Z_TOP + ZSTEP) / 2)
    # 8 mm back plate (matching the +X endplate) for the rest, at the -X back — seats
    # on the floor; its +X-lower zone stays open so the -X legs tuck in (no cutouts)
    w = w.union(box_at(CH.T, yw, ZSTEP - ZB, x=XLO + CH.T / 2, y=yc, z=(ZSTEP + ZB) / 2))
    # fuse the nut block -> one PA6-GF piece; trim to the 25 mm X-slab
    w = w.union(NB.nut_block.translate((D.NUT_BLOCK_X, 0, D.STRING_Z)))
    w = w.intersect(box_at(T_EP, 4000.0, 4000.0, x=KX, y=0, z=0))
    # socket the rail-end dovetail tongues (in the thick top, above the legs)
    for ycc in (CH.Y_HI, CH.Y_LO):
        w = w.cut(CH._kh_tongue(ycc, socket=True))
    # +Z hold-down screw pilot, up from the floor seat into the 8 mm back plate
    w = w.cut(cyl(SCREW_PILOT, 16.0, z=ZB).translate((SCREW_X, 0.0, 0)))
    return heal(w)


keyhead_endplate = _build()
