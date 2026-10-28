# -*- coding: utf-8 -*-
"""A PRINTED REAMING JIG for opening ONE ear of the Tr8x2 H-flange nut to GUIDE_EAR_D.

SHOP TOOL, not a part of the instrument (user, 2026-10-27). The reamer is the 9/64" HSS
chucking reamer of dimensions.GUIDE_EAR_D (McMaster 2995A116, 3.572-3.576), turned by hand in
a chuck. The jig holds the nut so it cannot turn and holds the reamer vertical over the ear.

ONE PIECE, PRINTED STANDING AS IT IS USED (table face on the bed), so the nut's slot and the
reamer's channel are both drawn by the nozzle round the axis they work along:

  NUT SLOT   the nut slides in from -X, BOSS DOWN (its 10 mm side: "more to hold it in place"),
             +X ear first, until the boss's half-round end and the flange's R11 end meet the
             slot's. The flange's two flats run along the slot's walls, so it cannot turn; it
             sits on the slot FLOOR, which carries the +X ear straight down under the reamer's
             push. The boss's slot runs out through the bottom, so the boss touches nothing
             below and stands FLOOR_LIFT clear of the table.
  ROOFS      every ceiling over the nut is a 45 deg GABLE (ridge along X, the slide): over the
             flange, and higher over the 2 mm stub that stands on the flange's top, which
             only reaches out to the boss's radius, so the ear's roof stays low.
  CHANNEL    a bore on the +X ear's axis, from the gable's ridge to the top -- CH_L of guide
             -- and on down through the floor to the bed, so the reamer's tip and the brass
             chips leave through the bottom. Tube walls, a 45 deg collar onto the block.

HOW IT IS USED
  1. Slide the nut in from the open -X side, boss down, until it stops.
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
NUT_CLR = 0.25                     # the nut's slide in its slot, each side (metal in a print)
TOP_CLR = 0.3                      # air over the flange and over the stub
FLOOR_LIFT = 2 * 0.2               # the boss's foot over the table: the FLOOR carries the nut
REAMER_D = D.GUIDE_EAR_D           # 3.572
CH_CLR = 0.15                      # the reamer's flutes in the channel, each side
CH_D = REAMER_D + 2 * CH_CLR       # 3.87

# ── the block ───────────────────────────────────────────────────────────────
WALL = 4 * B                       # 3.2: every wall round the nut
FLOOR_Z = BOSS_DOWN + FLOOR_LIFT   # 10.4: the flange's seat
SLOT_HW = FL_W / 2.0 + NUT_CLR     # 5.5
BOSS_SR = BOSS_R + NUT_CLR         # 5.35: the boss's slot, half-width and end radius
FL_TOP = FLOOR_Z + FL_T + TOP_CLR  # 13.9: the flange slot's walls stop here...
FL_APEX = FL_TOP + SLOT_HW         # 19.4: ...and its gable's ridge
STUB_TOP = FLOOR_Z + FL_T + BOSS_UP + TOP_CLR   # 15.9
STUB_APEX = STUB_TOP + SLOT_HW     # 21.4
HW = SLOT_HW + WALL                # 8.7: the block's half-width
X0 = -9.6                          # the open end: inside where the flats end (9.67), so the
                                   # flats bear on the walls their whole run in the block
X1 = FL_R + NUT_CLR + WALL         # 14.45
# THE BLOCK'S TOP IS A ROOF TOO (user: "efficient on material ... only what's needed"): a
# 45 deg gable ROOF_T over the stub's, so the block is a shell round the slot, not a brick
ROOF_T = 2 * B                     # 1.6, square to the slope
ROOF_APEX = STUB_APEX + ROOF_T * math.sqrt(2.0)   # 23.66
ROOF_WALL = ROOF_APEX - HW         # 14.96: the block's sides stand to here

# ── the tower ───────────────────────────────────────────────────────────────
TUBE_R = CH_D / 2.0 + WALL         # 5.135: the channel's tube
TOP_Z = 80 * B                     # 64.0
CH_L = TOP_Z - FL_APEX             # 44.6 of channel over the ear's roof
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


def _plan(end_r, z0, z1):
    """A slot's plan, z0..z1: open to -X, closed at +X by a round end of radius end_r about
    the nut's axis, clipped to the slot's width."""
    run = _box(X0 - 1.0, 0.0, -SLOT_HW, SLOT_HW, z0, z1)
    end = (cq.Workplane("XY").circle(end_r).extrude(z1 - z0).translate((0, 0, z0))
           .intersect(_box(-end_r, end_r, -SLOT_HW, SLOT_HW, z0, z1)))
    return run.union(end)


def nut_void():
    boss = (cq.Workplane("XY").circle(BOSS_SR).extrude(FLOOR_Z + 1.0).translate((0, 0, -1.0))
            .union(_box(X0 - 1.0, 0.0, -BOSS_SR, BOSS_SR, -1.0, FLOOR_Z)))
    flange = _plan(FL_R + NUT_CLR, FLOOR_Z, FL_APEX + 1.0).intersect(
        _gable(FL_TOP, FL_APEX, X0 - 1.0, X1))
    stub = _plan(BOSS_SR, FLOOR_Z, STUB_APEX + 1.0).intersect(
        _gable(STUB_TOP, STUB_APEX, X0 - 1.0, X1))
    return boss.union(flange).union(stub)


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
    # under the floor the exit bore would leave a 0.67 sliver against the boss's slot: open
    # it into the slot instead (the ear still sits on the floor round its other three sides)
    bore = bore.union(_box(0.0, EAR_X, -CH_D / 2.0, CH_D / 2.0, -1.0, FLOOR_Z))
    mouth = (cq.Workplane("XY").circle(CH_D / 2.0).workplane(offset=LEAD_IN + 0.01)
             .circle(CH_D / 2.0 + LEAD_IN + 0.01).loft().translate((EAR_X, 0, TOP_Z - LEAD_IN)))
    return out.cut(bore).cut(mouth)


def nut() -> cq.Workplane:
    """The nut, seated -- for checking only."""
    fl = (cq.Workplane("XY").circle(FL_R).extrude(FL_T)
          .intersect(_box(-FL_R, FL_R, -FL_W / 2.0, FL_W / 2.0, 0.0, FL_T)))
    boss = cq.Workplane("XY").circle(BOSS_R).extrude(BOSS_DOWN + FL_T + BOSS_UP).translate((0, 0, -BOSS_DOWN))
    n = fl.union(boss)
    for s in (+1, -1):
        n = n.cut(cq.Workplane("XY").circle(3.5 / 2.0).extrude(10).translate((s * EAR_X, 0, -1)))
    return n.translate((0, 0, FLOOR_Z))


if __name__ == "__main__":
    j, n = jig().val(), nut().val()
    print("jig %.1f cm3, %.1f x %.1f x %.1f" % (j.Volume() / 1000, *(lambda b: (b.xlen, b.ylen, b.zlen))(j.BoundingBox())))
    print("nut overlap %.4f mm3" % j.intersect(n).Volume())
    print("solids", len(j.Solids()), " channel guide over the ear %.1f" % CH_L)


def components():
    """The scratch view's scope: the jig with the nut seated in it."""
    return [("ream_jig", jig()), ("nut", nut())]
