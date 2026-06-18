"""Keyhead (-X) endplate + NUT BLOCK — PA6-GF, ONE merged 25 mm piece (x -636..-611).

The nut block (string termination) is fused into the box-closure wall: one solid
piece (prints -X→+X). It INSTALLS LAST, dropping straight down (+Z→-Z) with the
deck panels already in place. It:
  - closes the -X end of the box, caps the rail tops + plugs the deck-panel grooves
    (so the panels can't slide out -X until it's removed);
  - terminates the strings (gauged break edge + 2-row clamps), bearing on solid
    PA6-GF — no separate nut block, no 4 corner bolts;
  - is located in X/Y by side tabs + rail caps + the deck butt, and locked in +Z by
    ONE thread-forming screw up from the chassis floor bottom into a centre boss.

Service: send motors slack, back off the clamp set screws, remove the +Z screw,
lift this piece out, slide the deck panels off -X.
"""

from __future__ import annotations

from . import dimensions as D
from . import chassis as CH
from . import motor_bank as MB
from . import nut_block as NB
from .helpers import box_at, cyl, heal

# ONE 25 mm part, x −636 .. −611 (PA6-GF prints −X→+X). Installs LAST, dropping
# straight DOWN (+Z→−Z): side tabs + rail caps locate it in X/Y, the deck groove
# plug stops the panels sliding out −X, and ONE screw up from the chassis floor
# bottom locks it in +Z (it can otherwise only lift). The nut block is fused in.
T_EP = 25.0                                # part thickness (X) — the 25 mm target
XHI  = -611.0                              # +X face: flush with the deck (-X end)
XLO  = XHI - T_EP                          # = -636
KX   = (XLO + XHI) / 2                     # = -623.5
YL   = CH.Y_LO + CH.T / 2 + 0.3            # just inside the -Y rail
YH   = CH.Y_HI - CH.T / 2 - 0.3            # just inside the +Y rail
ZB   = MB.FLOOR_TOP                        # wall bottom: SEATS ON the keyhead floor
TAB_Z0 = CH.Z_BOT + 8.0                    # tab/channel band (matches chassis cut)
SCREW_X = KX                               # +Z hold-down: vertical screw on the centre-
SCREW_PILOT = 3.4                          # line, M4 threading into the PA6-GF


def _build():
    w = box_at(T_EP, YH - YL, CH.Z_TOP - ZB,
               x=KX, y=(YL + YH) / 2, z=(CH.Z_TOP + ZB) / 2)
    # 45deg lower-outer chamfers: self-supporting print + clears the leg barrels
    w = w.edges("|X and <Z").chamfer(CH.Z_TOP - ZB - 10.0)
    # side tabs plug into the rail-end channels (X/Y location + anti-fall)
    for yf, s in ((YL, -1), (YH, 1)):
        w = w.union(box_at(11.0, 3.0, CH.Z_TOP - TAB_Z0,
                           x=KX, y=yf + s * 1.2, z=(CH.Z_TOP + TAB_Z0) / 2))
    # cap each rail top (lowered to z0 here) and PLUG the deck groove so the panels
    # can't slide out -X until this part is removed. The plug is only mouth-wide (no
    # dovetail flare) so the part still lifts straight up +Z to come off.
    MW, DEP, GZ = CH.TP_TG_MW, CH.TP_TG_DEPTH, CH.TP_GZ0
    for yc, inner, outer in ((CH.Y_HI, YH, CH.Y_HI + CH.T / 2),
                             (CH.Y_LO, YL, CH.Y_LO - CH.T / 2)):
        w = w.union(box_at(T_EP, abs(outer - inner), CH.Z_TOP - GZ,
                           x=KX, y=(inner + outer) / 2, z=(CH.Z_TOP + GZ) / 2))
        w = w.union(box_at(T_EP, 2 * MW, DEP, x=KX, y=yc, z=GZ - DEP / 2))
    # FUSE the nut block (string termination) -> one PA6-GF piece (no mount bolts);
    # then trim the result to the 25 mm X-slab.
    w = w.union(NB.nut_block.translate((D.NUT_BLOCK_X, 0, D.STRING_Z)))
    w = w.intersect(box_at(T_EP, 4000.0, 4000.0, x=KX, y=0, z=0))
    # +Z hold-down screw: a centre BOSS reaching the floor seat (the lower chamfer
    # would otherwise leave no material here) + an M4 pilot up into it (PA6-GF).
    w = w.union(cyl(11.0, 14.0, z=ZB).translate((SCREW_X, 0.0, 0)))
    w = w.intersect(box_at(T_EP, 4000.0, 4000.0, x=KX, y=0, z=0))   # keep the 25 mm slab
    w = w.cut(cyl(SCREW_PILOT, 10.0, z=ZB).translate((SCREW_X, 0.0, 0)))
    return heal(w)


keyhead_endplate = _build()
