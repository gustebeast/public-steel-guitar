"""Bottom screw-support rail (shared) — FUSED into bridge_endplate (§8 item 2).

Not a standalone print: bridge_endplate unions this rail in and bridges it to
the cap, so the whole bridge end is one solid. The 10 vertical screws' bottom
supports live in ONE rail spanning the field at the screw line (X=SCREW_X).
Each station seats a TANDEM PAIR of MR85 bearings (Ø8 OD, 5.0 mm stacked) with a
top ledge that backs their OUTER RINGS against the screw's UPWARD pull (the string
pulls each carriage toward its bridge bearing, +Z). The inner rings are driven up
from below by the printed screw_collar, so the load crosses the balls in parallel
through both bearings. A single rail avoids the overlapping per-screw cradles that
10 separate holders would create at 9.5 mm pitch. Built in global position.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, box_at

ACROSS  = 2 * D.BRIDGE_AXLE_Y + D.BRIDGE_ARM_W   # reach the endplate edge-ribs' outer Y
# X span: the -X face reaches the endplate's own -X edge (BRIDGE_BASE_X0) so the
# drivetrain-mount base is the full 25 mm wide (matching the endplate); the +X face stops
# at SCREW_X+7, where the bridge's bottom-bridge takes over up to the +X tip.
X_NX    = D.BRIDGE_BASE_X0                 # -X face (= endplate -X edge, -16.5)
X_PX    = D.SCREW_X + 9 * D.BEAD           # 7.2: +X face (bottom-bridge takeover, -0.8;
                                           # keep = bridge_endplate._SRX)
# Z EXTENTS, datumed off the THRUST LEDGE (D.SUPPORT_BRG_Z) rather than off the rail's
# own centre. The old form put the rail's TOP at −52.5, which is 0.5 mm INSIDE the drive
# pulley's bottom flange — a real collision that only stayed quiet because the pair sits
# in check_overlaps' allow list. Ledge-first also removes a second inconsistency: HEIGHT
# happened to make the seat's top land on SUPPORT_BRG_Z, so the constant read as "ledge"
# here and as "stack centre" in build.py, and the bearings were placed half a stack high.
# Both ends are pinned by things that will not move, and between them there is
# only 10.7 mm for ledge + bearings + collar (see dimensions.COLLAR_H).
SEAT_CLR = 0.3                              # slop under the stack (it seats UP on the ledge)
BOT      = D.SUPPORT_BRG_BOT - SEAT_CLR     # -60.3, rail underside = seat mouth
TOP      = D.SUPPORT_BRG_Z + D.BRG_LEDGE_T  # -53.4, RAIL_PULLEY_CLR under the pulley
HEIGHT   = TOP - BOT                        # 6.9
_PULLEY_GAP = (D.SCREW_PULLEY_Z - D.PULLEY_W / 2) - TOP
assert _PULLEY_GAP >= D.RAIL_PULLEY_CLR - 1e-9, (
    f"the screw rail's top fouls the drive pulley by {-_PULLEY_GAP:.2f}: thin BRG_LEDGE_T")

SEAT_LEDGE_D = D.SUPPORT_BRG_OD - 2.5      # top-ledge bore (< OD, so it backs the outer ring)


def seat_cutter() -> cq.Workplane:
    """The ten bearing seats + their screw clearance, as a standalone cutter.

    Exported because the rail is FUSED into bridge_endplate and the endplate's own
    foot block reaches -X to about x −4.2 — far enough +X to refill the +X sliver of
    every Ø8.2 seat after the union. So the endplate re-applies this AFTER all its
    unions; cutting only inside this module was quietly leaving 0.2 mm of material
    in the bearings' way (the overlap gate found it)."""
    tool = None
    for i in range(D.N_STRINGS):
        y = D.string_y(i)
        # bearing seat: counterbore from the bottom (−Z) up to the thrust ledge
        seat = cyl(D.SUPPORT_BRG_OD + 0.2, D.SUPPORT_BRG_W + SEAT_CLR, z=BOT - 0.01)
        # screw clearance through the top ledge (Ø < the bearing OD — that step IS
        # the face the outer rings push against, and the whole string load with them)
        clr = cyl(SEAT_LEDGE_D, HEIGHT + 2, z=BOT - 1)
        cut = seat.union(clr).translate((D.SCREW_X, y, 0))
        tool = cut if tool is None else tool.union(cut)
    return tool


def _build() -> cq.Workplane:
    body = box_at(X_PX - X_NX, ACROSS, HEIGHT, x=(X_NX + X_PX) / 2, y=0, z=(BOT + TOP) / 2)
    return body.cut(seat_cutter())


screw_rail = _build()
