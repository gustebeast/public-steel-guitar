"""Keyhead (-X) endplate — PCTG, REMOVABLE box-closure wall.

Mirrors the bridge endplate's role at the nut end, but it's a separate, bolt-off
part so the deck panels can slide out -X for motor/electronics service. It:
  - closes the -X end of the box and caps the deck-panel grooves (panels can't
    slide out until it's removed);
  - carries the four nut-block bolt inserts (the nut block bolts down THROUGH to
    it), so removing the nut block frees the endplate to lift out;
  - seats on the chassis keyhead rib and plugs side tabs into shallow channels
    in the rail ends (located in X/Y, can't fall when the instrument is inverted
    while the nut block clamps it down).

Service: send motors slack, back off the nut-block set screws, unbolt the nut
block, lift this endplate out, slide the deck panels off -X.
"""

from __future__ import annotations

from . import dimensions as D
from . import chassis as CH
from . import motor_bank as MB
from . import nut_block as NB
from .helpers import box_at, cyl, heal

KX   = D.NUT_BLOCK_X - 9.0                 # endplate centre line (= chassis seat)
T_EP = 30.0                                # wall thickness (X)
YL   = CH.Y_LO + CH.T / 2 + 0.3            # just inside the -Y rail
YH   = CH.Y_HI - CH.T / 2 - 0.3            # just inside the +Y rail
ZB   = MB.FLOOR_TOP                        # wall bottom: SEATS ON the keyhead tie rib
                                           # (don't drop into the open bottom between
                                           # the rails — the rib closes that 11 mm)
TAB_Z0 = CH.Z_BOT + 8.0                    # tab/channel band (matches chassis cut)


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
    # can't slide out -X until the endplate is removed. The plug is only mouth-wide
    # (no dovetail flare) so the endplate still lifts straight up +Z to come off.
    MW, DEP, GZ = CH.TP_TG_MW, CH.TP_TG_DEPTH, CH.TP_GZ0
    for yc, inner, outer in ((CH.Y_HI, YH, CH.Y_HI + CH.T / 2),
                             (CH.Y_LO, YL, CH.Y_LO - CH.T / 2)):
        w = w.union(box_at(T_EP, abs(outer - inner), CH.Z_TOP - GZ,
                           x=KX, y=(inner + outer) / 2, z=(CH.Z_TOP + GZ) / 2))
        w = w.union(box_at(T_EP, 2 * MW, DEP, x=KX, y=yc, z=GZ - DEP / 2))
    # nut-block bolt inserts (the block bolts down through into these)
    for sx in (D.NUT_BLOCK_X + NB.X_FRONT - 3.0, D.NUT_BLOCK_X + NB.X_BACK + 3.0):
        for sy in (-(NB.HW - 4.0), NB.HW - 4.0):
            w = w.cut(cyl(5.6, 9.0, z=CH.Z_TOP - 9.0).translate((sx, sy, 0)))
    return heal(w)


keyhead_endplate = _build()
