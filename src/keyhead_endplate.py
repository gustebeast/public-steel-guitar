"""Keyhead (-X) endplate + NUT BLOCK — PETG-GF, ONE merged 25 mm piece (x -636..-611).

The nut block (string termination) is fused into a simple FULL-WIDTH solid prism
(rail outer to rail outer) that TAKES OVER the rail -X ends, so its edge shows from
the front like the bridge endplate. It INSTALLS LAST, dropping straight down (+Z→-Z)
with the deck panels already in place. It:
  - closes the -X end of the box (its solid +X face stops the deck panels sliding -X);
  - terminates the strings (gauged break edge + 2-row clamps), bearing on solid
    PETG-GF — no separate nut block, no 4 corner bolts;
  - sockets a dovetail tongue on each rail end (mirrors the bridge joint) -> X+Y lock
    + grip against the +X string tension; locked in +Z by ONE thread-forming screw up
    from the chassis floor bottom into the solid body.

Service: send motors slack, back off the clamp set screws, remove the +Z screw,
lift this piece out, slide the deck panels off -X.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from . import nut_block as NB
from .endplate_base import endplate_base
from .helpers import box_at, heal


def _stow_bore(d, x_hole, x_face, z_top, z_bot):
    """The WHOLE string-stow hole as ONE swept solid (built at y=0) -- no unions, so no
    internal seams. A circle is swept up a straight vertical bore (from below the bed at
    z_bot, at x_hole), SMOOTHLY through a 45-deg (1/8-circle) arc, then out a short 45-deg
    lead-in at the -X face (x_face, z_top). The bore->arc and arc->lead joins are tangent,
    so the inserted string rides one continuous wall from the face down into the bore."""
    R = (x_hole - x_face) / (1.0 - math.cos(math.radians(45)))   # arc radius for the 45-deg span
    zj = z_top - R * math.sin(math.radians(45))                  # straight bore up to here, then arc
    cx = x_hole - R                                              # arc centre x (z = zj)
    mid = (cx + R * math.cos(math.radians(22.5)), zj + R * math.sin(math.radians(22.5)))
    c = math.cos(math.radians(45))
    path = (cq.Workplane("XZ").moveTo(x_hole, z_bot)
            .lineTo(x_hole, zj)                                  # straight vertical bore
            .threePointArc(mid, (x_face, z_top))                # 1/8-circle blend to 45 deg
            .lineTo(x_face - 3.0 * c, z_top + 3.0 * c))         # 45-deg lead-in through the face
    prof = cq.Workplane("XY", origin=(x_hole, 0.0, z_bot)).circle(d / 2)
    return prof.sweep(path)

# ONE part (x −636 .. −611, PETG-GF), FULL-WIDTH (rail outer to rail outer) so it TAKES
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
# FOOT POCKET: the chassis now KEEPS a ~10 mm rail shell hugging each -X leg socket
# (CH._leg_shell over CH.LEG_SHELL_NX), capped at the foot line (z -23.15); the keyhead
# is solid AROUND that shell and nests over it as it drops -Z. The pocket only clears
# z = Z_BOT .. FOOT_Z (over the shell), NOT full-Z -- so the solid fill band (z -23.15..6)
# stays intact over the legs. leg -> 10 mm rail wall -> keyhead, touching.
LEG_CLR = CH.EP_LEG_CLR                    # assembly clearance around the kept chassis shell (shared)
LEG_SHELL_X0, LEG_SHELL_X1 = CH.LEG_SHELL_NX     # -625.6 .. -610.6 (rail-takeover region)

ZHOLE_D = 5.0                              # string-stow bore Ø (string + pliers grip; pitch is 9.5)
ZHOLE_X = XLO + 8 * D.BEAD                 # -629.6: keeps ~3.9 mm of wall -X of the bore


def _build():
    # THE SHARED TWO-PRISM BASE (endplate_base — same code as the bridge):
    # 1) the FILL SLAB (z -23.15..6, full footprint) = the -X cross-tie;
    # 2) the FOOT BOX below, hollowed to CH.T exterior walls (the -X end
    # face + both +-Y side faces stay solid; +X opens to the chassis box —
    # the rail-end shells + tongues come from the chassis side).
    w = endplate_base(XLO, XHI, "lo")
    # nut block (the only thing reaching above the deck): ONE solid prism from the deck
    # plane (Z6) up to the boss top, fused on -- it bridges down to the fill zone itself,
    # so no separate riser
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
    # LEG-STUB grooves (Y-INSTALL round — user: the stubs print on their
    # side and SLIDE IN ALONG Y): cut this end's corner negatives from the
    # SAME shared source the chassis uses (legs.corner_groove_negatives).
    # For the keyhead that hosts: the 44-long END-WALL groove (x -631.2,
    # the wall centreline — its blind inboard end is the stub's flush hard
    # stop; the two crossing stow bores just poke its roof, shortening
    # those string tails ~7), the crossing grooves' reach through the
    # endplate's own side-wall band / tab, and nothing of the fin passage
    # (that crossing is all kept-shell). Groove roofs at bed + 7.34, far
    # below the dovetail sockets (-23.15..-6).
    # relief=False: the 45° overhang wedge relieves the CHASSIS tongue
    # only — cut here it eats the end-wall groove roof (user-caught).
    # + the per-leg M4 LOCK SCREW ways along x through the end face
    # (Ø4.6 outboard cheek / Ø3.6 pilot through tongue + inboard cheek).
    from .legs import (corner_groove_negatives as _cgn,
                       endwall_screw_negatives as _esn)
    for _ly, _s in ((CH.LEG_Y[0], 1.0), (CH.LEG_Y[1], -1.0)):
        for _n in _cgn(CH.LEG_STATIONS_X[1], _ly, _s, -1.0, CH.Z_BOT,
                       relief=False):
            w = w.cut(_n)
        for _n in _esn(CH.LEG_STATIONS_X[1], _ly, -1.0, CH.Z_BOT):
            w = w.cut(_n)
    # STRING-END STOWAGE (one per string): a vertical bore set INBOARD of the -X face
    # (ZHOLE_X, ~3.5 mm of wall left -X of it) running from near the body top straight DOWN
    # and out through the bed -- the cut string end tucks into it, so almost nothing
    # protrudes -X and what does is a smooth loop, not a sharp tail. The string can't drop
    # in from straight above (the nut-block riser caps that), so the bore curves smoothly
    # out to the -X face top corner (XLO, Z6): the WHOLE thing -- vertical bore, 45-deg
    # arc, and 45-deg face lead-in -- is one swept solid, so there's no seam where the
    # curve meets the bore (one continuous wall to push the string against). Restringing:
    # pull the end back out with pliers for a hand-hold while setting the new string hand-tight.
    # ON THE WRAP'S FAR END, NOT ON THE STRING'S OWN LANE (user caught this). Since the
    # capstan the tail does not leave at nut_y any more: it leaves where its coil ends,
    # nut_y - adv, which is 0.9 to 4.7 further -Y depending on gauge. The bores had stayed
    # on the old line, so every tail was aimed a little wide of its own hole and the fattest
    # was aimed at its neighbour's. Reading nut_block.wrap_y ties them to the wrap for good.
    bore = _stow_bore(ZHOLE_D, ZHOLE_X, XLO, Z6, CH.Z_BOT - 1.0)
    for i in range(D.N_STRINGS):
        w = w.cut(bore.translate((0, NB.wrap_y(i)[1], 0)))
    return heal(w)


keyhead_endplate = _build()
