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

# ONE 25 mm part (x −636 .. −611, PA6-GF). A simple FULL-WIDTH solid prism (rail
# outer to rail outer) that TAKES OVER the rail −X ends — so its edge shows from the
# front, mirroring the bridge endplate. Installs LAST, dropping straight DOWN
# (+Z→−Z): it sockets a dovetail tongue on each rail end (X+Y lock + grip vs the +X
# string tension) and ONE screw up from the floor bottom locks it in +Z (it can
# otherwise only lift). The nut block is fused in. (15 % infill keeps it ~150 g.)
T_EP = 25.0                                # part thickness (X) — the 25 mm target
XHI  = CH.KH_X                             # +X face = rail -X end (-611)
XLO  = XHI - T_EP                          # = -636
KX   = (XLO + XHI) / 2
YFL  = CH.Y_LO - CH.T / 2                   # full width: -Y rail outer face
YFH  = CH.Y_HI + CH.T / 2                   # +Y rail outer face
ZB   = MB.FLOOR_TOP                        # bottom: SEATS ON the keyhead floor
SCREW_X = CH.KH_SCREW_X                     # +Z hold-down screw (vertical, centred)
SCREW_PILOT = 3.4                          # M4 thread-forming into the PA6-GF


def _build():
    # full-width solid prism (z floor-seat .. deck top); takes over the rail -X ends
    w = box_at(T_EP, YFH - YFL, CH.Z_TOP - ZB,
               x=KX, y=(YFL + YFH) / 2, z=(CH.Z_TOP + ZB) / 2)
    # fuse the nut block -> one PA6-GF piece; trim to the 25 mm X-slab
    w = w.union(NB.nut_block.translate((D.NUT_BLOCK_X, 0, D.STRING_Z)))
    w = w.intersect(box_at(T_EP, 4000.0, 4000.0, x=KX, y=0, z=0))
    # socket the rail-end dovetail tongues (chassis _kh_tongue): drop-in, X+Y lock +
    # grip vs the +X string tension; on the +X (rail) side so the back face stays flat
    for yc in (CH.Y_HI, CH.Y_LO):
        w = w.cut(CH._kh_tongue(yc, socket=True))
    # leg clearance: notch the lower-outer corners (below the dovetail) where the two
    # -X leg sockets poke up, so the full-width body clears them
    for y0, y1 in ((36.0, 63.0), (-138.0, -110.0)):
        w = w.cut(box_at(T_EP + 4.0, y1 - y0, CH.KH_DT_Z0 - (ZB - 1.0),
                         x=KX, y=(y0 + y1) / 2, z=(CH.KH_DT_Z0 + ZB - 1.0) / 2))
    # +Z hold-down screw pilot, up from the floor seat into the solid body
    w = w.cut(cyl(SCREW_PILOT, 12.0, z=ZB).translate((SCREW_X, 0.0, 0)))
    return heal(w)


keyhead_endplate = _build()
