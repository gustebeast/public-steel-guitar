"""Bottom screw-support rail (shared) — FUSED into bridge_endplate (§8 item 2).

Not a standalone print: bridge_endplate unions this rail in and bridges it to
the cap, so the whole bridge end is one solid. The 10 vertical screws' bottom
supports live in ONE rail spanning the field across BOTH screw rows (+/-SCREW_ROW_DX).
Each station seats ONE 688ZZ bearing (Ø16 OD, 5.0 wide) with a
top ledge that backs their OUTER RINGS against the screw's UPWARD pull (the string
pulls each carriage toward its bridge bearing, +Z). The inner rings are driven up
from below by the printed screw_collar, so the load crosses the balls in parallel
through both bearings. A single rail avoids the overlapping per-screw cradles that
10 separate holders would create at 9.5 mm pitch. Built in global position.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at
from cadkit.supports import printable_bore

# This rail is FUSED into bridge_endplate, so it prints in that part's orientation —
# flat on the +X face, building -X. Every bore here has axis Z, i.e. SIDEWAYS to the
# build, so every one of them is a teardrop. Duplicated rather than imported because
# bridge_endplate imports this module, not the other way round; asserted equal there.
PRINT_UP = (-1.0, 0.0, 0.0)

ACROSS  = 2 * D.BRIDGE_AXLE_Y + D.BRIDGE_ARM_W   # reach the endplate edge-ribs' outer Y
# X span: the -X face reaches the endplate's own -X edge (BRIDGE_BASE_X0) so the
# drivetrain-mount base is the full 25 mm wide (matching the endplate); the +X face stops
# at SCREW_X+7, where the bridge's bottom-bridge takes over up to the +X tip.
# The rail now spans the WHOLE bridge base. It used to stop at SCREW_X+7 and hand over
# to the bridge's bottom-bridge, which worked when every seat sat on one X line; with
# TWO ROWS the seats are at -/+SCREW_ROW_DX and the rail has to reach both.
X_NX    = D.BRIDGE_BASE_X0                 # -X face (= endplate -X edge)
X_PX    = D.BRIDGE_BASE_X1                 # +X face (= endplate +X edge)
# Z EXTENTS, datumed off the THRUST LEDGE (D.SUPPORT_BRG_Z). The stack now sits ON
# the pulleys rather than under them, so this rail rode up with it — and everything
# that used to live below the pulley went away in the move: no retaining collar, no
# 10.7 mm budget squeezed against the chassis end block, ~9 mm off the screw.
# The belts do not object, which was the objection when this was first considered:
# they wrap the toothed band, whose top is 1.5 mm below the pulley's own top
# (measured off the built belts), so a rail seated on the tops clears them.
SEAT_CLR = 0.3                              # slop under the stack (it seats UP on the ledge)
BOT      = D.SUPPORT_BRG_BOT - SEAT_CLR     # -38.9, rail underside = seat mouth
TOP      = D.SUPPORT_BRG_Z + D.BRG_LEDGE_T  # -30.4
HEIGHT   = TOP - BOT                        # 8.5
# (No plane-vs-plane nut check here any more. It compared NUT_BOT_MIN with this TOP as if
# the rail were solid, but the nut's lowest part is its Ø10.2 boss, which passes DOWN
# THROUGH the ledge bore. The real checks are the bore's radial clearance, below SEAT_LEDGE_D,
# and the boss-to-bearing gap in dimensions._NUT_BRG_GAP.)

# TOP-LEDGE BORE. It has to be a window that lands on the OUTER rings and NOTHING
# else: the ledge is part of the endplate and never turns, while the inner rings turn
# with the screw. At the old 5.5 it reached inward over the inner ring's face (that
# ring's OD is ~5.8-6.0), so the stationary ledge would have rubbed a rotating race
# under the full string load, every move, forever. 6.4 sits in the gap — clear of the
# inner ring by ~0.4, still covering the outer ring (bore ~7.0-7.2) by ~0.8.
# It is the mirror of the constraint on screw_collar's Ø5.6 pilot boss, which lands on
# the inner rings only for the same reason from the other side.
SEAT_LEDGE_D = 18 * D.BEAD                 # 14.4 — lands on 688ZZ's OUTER ring
# 12.0 was wrong: it sat in the SHIELD zone (~10.2..13.8), so the ledge would have
# pressed on a shield rather than the outer ring it has to back. The outer ring starts
# at ~13.8, so the bore has to clear that before it bears on anything real.
assert SEAT_LEDGE_D >= 13.8, "the ledge would press the 688's SHIELD, not its outer ring"
assert SEAT_LEDGE_D <= 15.4, "the ledge no longer backs the 688's outer ring"
# The nut's Ø10.2 boss sweeps DOWN INTO this bore at the bottom of travel whenever the
# ledge top sits above NUT_BOT_MIN, so the bore — not the ledge plane — is its clearance.
if D.NUT_BOT_MIN < TOP:
    assert SEAT_LEDGE_D / 2 - D.NUT_BOSS_D / 2 >= 1.0 - 1e-9, (
        f"the nut boss sweeps into the ledge bore with only "
        f"{SEAT_LEDGE_D / 2 - D.NUT_BOSS_D / 2:.2f} radial clearance (want 1.0)")

# WHY THE LEDGE IS ON TOP, not underneath (user asked, and the answer is the load).
# The string pulls every carriage +Z, so the screw is pulled +Z at 88-147 N. The
# retention path only closes if the outer rings bear UP against something: collar ->
# inner rings -> balls -> outer rings -> THIS ledge -> endplate. Put the ledge below
# instead and the primary load is unresisted — the screw simply lifts out.
# Gravity is the other direction and is not close to a competing case: the screw is
# 8.6 g, about 0.08 N, some 1700x smaller than the load it is fighting. And with the
# strings off, when gravity IS the only force, the stack can drop exactly
# RAIL_PULLEY_CLR (0.4 mm) before the drive pulley's bottom flange lands on this
# rail's top face and stops it.


def _bore(d, length, at):
    """A teardrop cutter, axis +Z from `at`, apex toward the build-up direction.

    Every bore in this rail runs SIDEWAYS to the endplate's build (which goes -X), so
    a plain cylinder would droop its ceiling out of round — and these are BEARING
    SEATS, where out-of-round is not cosmetic: an outer ring that does not seat square
    tilts the whole stack under 147 N. cadkit.supports.printable_bore shapes the 45°
    peak and leaves the round lower half — which is the half the bearing sits in —
    untouched."""
    return printable_bore(d, length, axis_point=at, axis_dir=(0.0, 0.0, 1.0),
                          print_up=PRINT_UP)


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
        seat = _bore(D.SUPPORT_BRG_OD + 0.2, D.SUPPORT_BRG_W + SEAT_CLR,
                     (D.screw_x(i), y, BOT - 0.01))
        # screw clearance through the top ledge (Ø < the bearing OD — that step IS
        # the face the outer rings push against, and the whole string load with them)
        clr = _bore(SEAT_LEDGE_D, HEIGHT + 2, (D.screw_x(i), y, BOT - 1))
        cut = seat.union(clr)
        tool = cut if tool is None else tool.union(cut)
    return tool


def _build() -> cq.Workplane:
    body = box_at(X_PX - X_NX, ACROSS, HEIGHT, x=(X_NX + X_PX) / 2, y=0, z=(BOT + TOP) / 2)
    return body.cut(seat_cutter())


screw_rail = _build()
