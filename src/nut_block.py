"""Nut block geometry (×1) — keyhead string termination. PA6-GF (clamps bear on it).

This is now FUSED into the keyhead endplate (one printed piece — keyhead_endplate.py
unions this geometry in); kept as its own module for the per-string layout + the
constants the build uses to place the break dowels / set screws. Per string it does
two jobs:

  1. Break edge — a hardened Ø2 dowel pin (DEMO) sets the open-string scale endpoint.
     Each pin sits at a GAUGED height (D.STRING_GAUGE) so every string TOP lands
     coplanar at STRING_Z. The string lays into an OPEN V-groove over the pin (no
     threading through a hole).

  2. Clamp — the plain end, laid in the same groove, is pinched DOWN onto the
     (solid PA6-GF) floor by an M4 cup-tip set screw (DEMO) running through a
     deeply-buried brass heat-set insert (DEMO). Clamps alternate between TWO rows
     (adjacent strings alternate front/back) so each Ø5.6 insert has ~13 mm of pitch
     (thick walls → no pull-out). Print with high wall/floor counts for a solid clamp
     floor. Reprint the whole keyhead piece to match a different string set.

Local frame: X=0 at the break edge, +X toward the bridge (speaking length); Z=0 at
the string-top plane (= STRING_Z global); body hangs −Z.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, cyl_y, box_at

# ── layout (local frame) ─────────────────────────────────────────────────
HW       = D.nut_y(0) + 11.0                    # half-width to the +Y-most string + room for 4 corner bolts
BODY_TOP = 1.0                                  # body top, just above the string plane
Z_BOT    = -6.0                                 # body bottom (local) → rests on the chassis top
X_FRONT  = 4.0                                  # +X lip (speaking side)
X_BACK   = -22.0                                # −X end (behind the back clamp row)
ROW1_X   = -8.0                                 # near clamp row (short run to the dowel)
ROW2_X   = -16.0                                # far clamp row (long run)


def clamp_row_x(i: int) -> float:
    """X of string i's clamp row. Adjacent strings alternate near/far rows so each Ø5.6
    insert keeps ~13 mm of Y pitch; phased off the −Y end so the heaviest string (last
    index) lands on the near ROW1 -- the shorter run, hence the shallower clamp floor."""
    return ROW1_X if (D.N_STRINGS - 1 - i) % 2 == 0 else ROW2_X

GROOVE_W = 1.8                                  # lay-in groove width (string channel)
GROOVE_FLOOR = -2.0                             # nominal groove bottom (per-string floor goes deeper)
BREAK_ANGLE = 10.0                              # MIN string break angle over the pin (deg). The
                                                # down-bearing on the pin is T*sin(angle); the
                                                # vibrating string lifts with ~T*pi*a/L, so the needed
                                                # angle is tension-independent. The clamp floor drops
                                                # per string (floor = -(gauge + run*tan(angle))) to
                                                # guarantee it, so the pin -- not the clamp -- cleanly
                                                # terminates the speaking length. Thin/already-steep
                                                # strings keep the nominal floor.
PIN_D    = 2.0 + 0.15                           # break-pin seat (Ø2 dowel + 0.15 sliding clearance)
PIN_L    = 4.0                                  # pin length (Ø2×4 dowel) — drops into its slot

BOSS_TOP = 10.0                                 # clamp boss top (houses the +Z insert; screw tip rests on the string)
BOSS_SQ  = 10.0                                 # clamp boss footprint
INSERT_D = 5.6                                  # M4 heat-set install hole
INSERT_L = 4.7
SCREW_D  = 4.3                                  # M4 set-screw clearance


def _build() -> cq.Workplane:
    body = box_at(X_FRONT - X_BACK, 2 * HW, BODY_TOP - Z_BOT,
                  x=(X_FRONT + X_BACK) / 2, y=0, z=(BODY_TOP + Z_BOT) / 2)

    for i in range(D.N_STRINGS):
        y = D.nut_y(i)
        g = D.STRING_GAUGE[i]
        gw = max(g + 0.8, 1.4)                  # GAUGED groove width — each string lays in + centres
        pin_z = -g - PIN_D / 2                  # gauged: pin top at −g → string top at 0
        row_x = clamp_row_x(i)
        # per-string pinch floor: deep enough that the string leaves the pin (top at -g) at
        # >= BREAK_ANGLE over the run to the clamp; keep the nominal floor if already steeper
        floor = min(GROOVE_FLOOR, -(g + abs(row_x) * math.tan(math.radians(BREAK_ANGLE))))

        # open lay-in groove along X (string channel), gauged to the string
        body = body.cut(box_at(X_FRONT - X_BACK, gw, BODY_TOP - floor,
                               x=(X_FRONT + X_BACK) / 2, y=y, z=(BODY_TOP + floor) / 2))
        # gauged break-pin seat (axis Y) + a top-open drop slot so the pin drops
        # straight in from above (the string then traps it down)
        body = body.cut(cyl_y(PIN_D, PIN_L, y0=y - PIN_L / 2, x=0.0, z=pin_z))
        body = body.cut(box_at(PIN_D, PIN_L, BODY_TOP - pin_z,
                               x=0.0, y=y, z=(BODY_TOP + pin_z) / 2))

        # clamp: raised boss + buried insert (from +Z) + set-screw bore down to the
        # string, which pinches it DOWN onto the solid (PA6-GF) groove floor
        body = body.union(box_at(BOSS_SQ, BOSS_SQ, BOSS_TOP - floor,
                                 x=row_x, y=y, z=(BOSS_TOP + floor) / 2))
        body = body.cut(cyl(INSERT_D, INSERT_L + 0.5, z=BOSS_TOP - INSERT_L)
                        .translate((row_x, y, 0)))
        body = body.cut(cyl(SCREW_D, BOSS_TOP - floor + 1, z=floor)
                        .translate((row_x, y, 0)))
        body = body.cut(box_at(BOSS_SQ + 1, gw, BODY_TOP - floor,   # groove through the boss
                               x=row_x, y=y, z=(BODY_TOP + floor) / 2))

    # No mount bolts: this block is now FUSED into the keyhead endplate (one PA6-GF
    # piece, keyhead_endplate.py) which drops in and is held by one screw + joinery.
    return body


nut_block = _build()
