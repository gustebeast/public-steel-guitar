# -*- coding: utf-8 -*-
"""A PRINTED REAMING JIG for opening ONE ear of the Tr8x2 H-flange nut to GUIDE_EAR_D.

SHOP TOOL, not a part of the instrument (user, 2026-10-27). The reamer is the 9/64" HSS
chucking reamer of dimensions.GUIDE_EAR_D (McMaster 2995A116, 3.572-3.576), turned by hand in
a chuck. The jig holds the nut so it cannot turn and holds the reamer vertical over the ear.

ONE PIECE, PRINTED STANDING AS IT IS USED (table face on the bed), so the nut's seat and the
reamer's channel are both drawn by the nozzle round the axis they work along:

  SEAT       a CLOSED pocket the nut DROPS into, BOSS DOWN (its 10 mm side: "more to hold it in
             place"): a round bore for the boss, BOSS_DOWN deep, and over it the flange's whole
             outline -- both flats AND both R11 ends -- POCKET_D deep. Nothing is open to the
             side, so the nut can only lift out (user, 2026-10-27: the first print's slot was
             open to -X and the nut wobbled). The flange sits on the pocket's FLOOR, which
             carries the +X ear straight down under the reamer's push; the boss's bore runs out
             through the bottom, so the boss touches nothing below and stands FLOOR_LIFT clear
             of the table.
  WINDOW     the way in: a slot open to -X standing on the pocket's rim, tall enough for the
             whole nut to slide in over the rim with the boss's foot DROP_CLR clear of it, then
             drop straight down into the seat. Its walls are the flats' (the nut cannot turn on
             the way); its ceiling a 45 deg GABLE, ridge along X.
  CHANNEL    a bore on the +X ear's axis, from the gable's ridge to the top -- CH_L of guide
             -- and on down through the floor to the bed, so the reamer's tip and the brass
             chips leave through the bottom. Tube walls, a 45 deg collar onto the block. The
             reamer crosses the window's air unguided (WINDOW_GAP); the CH_L above aims it.

HOW IT IS USED
  1. Slide the nut in through the -X window, boss down, until it meets the window's far end,
     then let it drop into the seat (it falls flat: wiggle it if it hangs).
  2. Stand the jig on the table, hold it down, feed the reamer in at the top.
  3. Turn the chuck clockwise and push down; stop when the reamer's tip is through the flange
     (it comes out of the bottom face). Keep turning clockwise as it comes back out.

CH_CLR keeps the reamer's flutes off the channel walls: glass-filled PETG would dull HSS.
"""
from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D

B = D.BEAD

# ── the nut, as MEASURED (user, 2026-10-27, calipers) ───────────────────────
FL_T = 3.2                         # flange thickness
FL_W = 10.5                        # across the flats
FL_R = 22.0 / 2.0                  # tip to tip: R11 ends
BOSS_R = 10.2 / 2.0
BOSS_DOWN = 10.0                   # the boss below the flange
BOSS_UP = 2.0                      # ... and its stub above
EAR_X = (12.4 + 3.5) / 2.0         # 7.95: the holes' centres (12.4 between near edges, Ø3.5)

# ── fits ────────────────────────────────────────────────────────────────────
NUT_CLR = 0.2                      # the nut in its seat and window, each side (metal in a
                                   # nozzle-drawn wall; 0.25 in a slot open to -X wobbled)
TOP_CLR = 0.3                      # air over the stub in the window
DROP_CLR = 0.4                     # the boss's foot over the rim, sliding in
FLOOR_LIFT = 2 * 0.2               # the boss's foot over the table: the FLOOR carries the nut
REAMER_D = D.GUIDE_EAR_D           # 3.572
CH_CLR = 0.15                      # the reamer's flutes in the channel, each side
CH_D = REAMER_D + 2 * CH_CLR       # 3.87

# ── the block ───────────────────────────────────────────────────────────────
WALL = 4 * B                       # 3.2: every wall round the nut
FLOOR_Z = BOSS_DOWN + FLOOR_LIFT   # 10.4: the flange's seat
POCKET_D = 2 * B                   # 1.6: the flange's outline sunk this deep (keys its ends)
RIM_Z = FLOOR_Z + POCKET_D         # 12.0: the window's floor
SLOT_HW = FL_W / 2.0 + NUT_CLR     # 5.45: across the flats, seat and window alike
BOSS_SR = BOSS_R + NUT_CLR         # 5.3: the boss's bore
END_R = FL_R + NUT_CLR             # 11.2: the flange's round ends
ENTRY_Z = RIM_Z + DROP_CLR + BOSS_DOWN          # 22.4: the flange's underside, sliding in
WIN_TOP = ENTRY_Z + FL_T + BOSS_UP + TOP_CLR    # 27.9: the window's walls stop here...
WIN_APEX = WIN_TOP + SLOT_HW       # 33.35: ...and its gable's ridge
HW = SLOT_HW + WALL                # 8.65: the block's half-width
X1 = END_R + WALL                  # 14.4
X0 = -X1                           # the pocket's -X end is closed too: the block is symmetric
# THE BLOCK'S TOP IS A ROOF TOO (user: "efficient on material ... only what's needed"): a
# 45 deg gable ROOF_T over the window's, so the block is a shell round it, not a brick
ROOF_T = 2 * B                     # 1.6, square to the slope
ROOF_APEX = WIN_APEX + ROOF_T * math.sqrt(2.0)
ROOF_WALL = ROOF_APEX - HW         # the block's sides stand to here

# ── the tower ───────────────────────────────────────────────────────────────
TUBE_R = CH_D / 2.0 + WALL         # 5.135: the channel's tube
TOP_Z = 88 * B                     # 70.4: the reamer reaches TOP_Z - FLOOR_Z = 60 out of the chuck
CH_L = TOP_Z - WIN_APEX            # 37.05 of channel over the window
WINDOW_GAP = WIN_APEX - (FLOOR_Z + FL_T)        # 19.75: unguided, ridge to the ear's top
COLLAR = HW                        # the collar's foot: as wide as the block allows
LEAD_IN = 0.8                      # the 45 deg chamfer at the channel's mouth
PRINT_UP = (0.0, 0.0, 1.0)         # as drawn, table face on the bed


def _box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _gable(z_wall, apex, x0, x1, hw=SLOT_HW):
    """A YZ section -- walls at +-hw up to z_wall, a 45 deg gable to `apex` -- from x0 to x1,
    from below the bed up."""
    pts = [(-hw, -1.0), (hw, -1.0), (hw, z_wall), (0.0, apex), (-hw, z_wall)]
    return cq.Workplane("YZ").polyline(pts).close().extrude(x1 - x0).translate((x0, 0, 0))


def _flange_plan(z0, z1, x_open=None):
    """The flange's outline + NUT_CLR, z0..z1: flats at +-SLOT_HW, R END_R ends about the
    nut's axis; with x_open, run out to x_open on the -X side (the window)."""
    sec = (cq.Workplane("XY").circle(END_R).extrude(z1 - z0).translate((0, 0, z0))
           .intersect(_box(-END_R, END_R, -SLOT_HW, SLOT_HW, z0, z1)))
    if x_open is not None:
        sec = sec.union(_box(x_open, 0.0, -SLOT_HW, SLOT_HW, z0, z1))
    return sec


def nut_void():
    bore = cq.Workplane("XY").circle(BOSS_SR).extrude(FLOOR_Z + 1.0).translate((0, 0, -1.0))
    pocket = _flange_plan(FLOOR_Z, RIM_Z + 0.01)
    window = _flange_plan(RIM_Z, WIN_APEX + 1.0, X0 - 1.0).intersect(
        _gable(WIN_TOP, WIN_APEX, X0 - 1.0, X1))
    return bore.union(pocket).union(window)


def jig() -> cq.Workplane:
    blk = _gable(ROOF_WALL, ROOF_APEX, X0, X1, HW).intersect(_box(X0, X1, -HW, HW, 0.0, TOP_Z))
    # the collar: a 45 deg cone from the block's full width where its sides stop, so it stands
    # inside the roof's own 45 deg section all the way up (the roof narrows no faster)
    h = COLLAR - TUBE_R
    collar = (cq.Workplane("XY").circle(COLLAR).workplane(offset=h).circle(TUBE_R).loft()
              .translate((EAR_X, 0, ROOF_WALL))
              .intersect(_box(X0, X1, -HW, HW, ROOF_WALL, ROOF_WALL + h)))
    tube = cq.Workplane("XY").circle(TUBE_R).extrude(TOP_Z - ROOF_WALL).translate((EAR_X, 0, ROOF_WALL))
    out = blk.union(collar).union(tube).cut(nut_void())
    bore = cq.Workplane("XY").circle(CH_D / 2.0).extrude(TOP_Z + 2.0).translate((EAR_X, 0, -1.0))
    # under the floor the exit bore would leave a 0.7 sliver against the boss's bore: open
    # it into the bore instead (the ear still sits on the floor round its other three sides)
    bore = bore.union(_box(0.0, EAR_X, -CH_D / 2.0, CH_D / 2.0, -1.0, FLOOR_Z))
    mouth = (cq.Workplane("XY").circle(CH_D / 2.0).workplane(offset=LEAD_IN + 0.01)
             .circle(CH_D / 2.0 + LEAD_IN + 0.01).loft().translate((EAR_X, 0, TOP_Z - LEAD_IN)))
    return out.cut(bore).cut(mouth)


def nut(x=0.0, z=FLOOR_Z) -> cq.Workplane:
    """The nut, its flange's underside at (x, z): seated by default -- for checking only."""
    fl = (cq.Workplane("XY").circle(FL_R).extrude(FL_T)
          .intersect(_box(-FL_R, FL_R, -FL_W / 2.0, FL_W / 2.0, 0.0, FL_T)))
    boss = cq.Workplane("XY").circle(BOSS_R).extrude(BOSS_DOWN + FL_T + BOSS_UP).translate((0, 0, -BOSS_DOWN))
    n = fl.union(boss)
    for s in (+1, -1):
        n = n.cut(cq.Workplane("XY").circle(3.5 / 2.0).extrude(10).translate((s * EAR_X, 0, -1)))
    return n.translate((x, 0, z))


if __name__ == "__main__":
    j, n = jig().val(), nut().val()
    print("jig %.1f cm3, %.1f x %.1f x %.1f" % (j.Volume() / 1000, *(lambda b: (b.xlen, b.ylen, b.zlen))(j.BoundingBox())))
    print("nut overlap %.4f mm3 seated" % j.intersect(n).Volume())
    # the way in: slide in at ENTRY_Z from outside the block, then drop to the seat
    path = [nut(x, ENTRY_Z) for x in (X0 - FL_R - 1.0, X0, X0 / 2.0, 0.0)]
    path += [nut(0.0, z) for z in (ENTRY_Z - 4.0, ENTRY_Z - 8.0, RIM_Z + 1.0)]
    print("nut overlap on the way in %.4f mm3" % max(j.intersect(p.val()).Volume() for p in path))
    print("solids", len(j.Solids()), " channel guide %.1f, unguided %.1f, reach %.1f"
          % (CH_L, WINDOW_GAP, TOP_Z - FLOOR_Z))


def components():
    """The scratch view's scope: the jig with the nut seated in it."""
    return [("ream_jig", jig()), ("nut", nut())]
