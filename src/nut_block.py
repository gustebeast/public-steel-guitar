"""Nut block (×1) — keyhead string termination. PA6-GF (clamps bear on it).

REMOVABLE: bolts to the chassis keyhead (no glue) so it can be reprinted to match a
different string set. Per string it does two jobs:

  1. Break edge — a hardened Ø2 dowel pin (DEMO) sets the open-string scale endpoint.
     Each pin sits at a GAUGED height (D.STRING_GAUGE) so every string TOP lands
     coplanar at STRING_Z. The string lays into an OPEN V-groove over the pin (no
     threading through a hole).

  2. Clamp — the plain end, laid in the same groove, is pinched DOWN onto the
     (solid PA6-GF) floor by an M4 cup-tip set screw (DEMO) running through a
     deeply-buried brass heat-set insert (DEMO). Clamps alternate between TWO rows
     (even strings front, odd strings back) so each Ø5.6 insert has ~13 mm of pitch
     (thick walls → no pull-out). Print with high wall/floor counts for a solid clamp
     floor. Bolts on at 4 corners (no glue) → reprintable per string set.

Local frame: X=0 at the break edge, +X toward the bridge (speaking length); Z=0 at
the string-top plane (= STRING_Z global); body hangs −Z.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, cyl_y, box_at

# ── layout (local frame) ─────────────────────────────────────────────────
HW       = D.nut_y(D.N_STRINGS - 1) + 11.0     # half-width (room for 4 corner bolts clear of the clamps)
BODY_TOP = 1.0                                  # body top, just above the string plane
Z_BOT    = -6.0                                 # body bottom (local) → rests on the chassis top
X_FRONT  = 4.0                                  # +X lip (speaking side)
X_BACK   = -22.0                                # −X end (behind the back clamp row)
ROW1_X   = -8.0                                 # clamp row 1 (even strings)
ROW2_X   = -16.0                                # clamp row 2 (odd strings)

GROOVE_W = 1.8                                  # lay-in groove width (string channel)
GROOVE_FLOOR = -2.0                             # groove bottom
PIN_D    = 2.0 + 0.15                           # break-pin seat (Ø2 dowel + 0.15 sliding clearance)
PIN_L    = 4.0                                  # pin length (Ø2×4 dowel) — drops into its slot

BOSS_TOP = 10.0                                 # clamp boss top (houses the +Z insert; screw tip rests on the string)
BOSS_SQ  = 10.0                                 # clamp boss footprint
INSERT_D = 5.6                                  # M4 heat-set install hole
INSERT_L = 4.7
SCREW_D  = 4.3                                  # M4 set-screw clearance
BOLT_D   = 4.3                                  # M4 mount-bolt clearance (the 4 corner
                                                # screws are M4×0.7×12, threading the same
                                                # heat-set inserts as the clamps — was 3.4,
                                                # an M3 hole the M4 screws couldn't pass)


def _build() -> cq.Workplane:
    body = box_at(X_FRONT - X_BACK, 2 * HW, BODY_TOP - Z_BOT,
                  x=(X_FRONT + X_BACK) / 2, y=0, z=(BODY_TOP + Z_BOT) / 2)

    for i in range(D.N_STRINGS):
        y = D.nut_y(i)
        g = D.STRING_GAUGE[i]
        gw = max(g + 0.8, 1.4)                  # GAUGED groove width — each string lays in + centres
        pin_z = -g - PIN_D / 2                  # gauged: pin top at −g → string top at 0
        row_x = ROW1_X if i % 2 == 0 else ROW2_X

        # open lay-in groove along X (string channel), gauged to the string
        body = body.cut(box_at(X_FRONT - X_BACK, gw, BODY_TOP - GROOVE_FLOOR,
                               x=(X_FRONT + X_BACK) / 2, y=y, z=(BODY_TOP + GROOVE_FLOOR) / 2))
        # gauged break-pin seat (axis Y) + a top-open drop slot so the pin drops
        # straight in from above (the string then traps it down)
        body = body.cut(cyl_y(PIN_D, PIN_L, y0=y - PIN_L / 2, x=0.0, z=pin_z))
        body = body.cut(box_at(PIN_D, PIN_L, BODY_TOP - pin_z,
                               x=0.0, y=y, z=(BODY_TOP + pin_z) / 2))

        # clamp: raised boss + buried insert (from +Z) + set-screw bore down to the
        # string, which pinches it DOWN onto the solid (PA6-GF) groove floor
        body = body.union(box_at(BOSS_SQ, BOSS_SQ, BOSS_TOP - GROOVE_FLOOR,
                                 x=row_x, y=y, z=(BOSS_TOP + GROOVE_FLOOR) / 2))
        body = body.cut(cyl(INSERT_D, INSERT_L + 0.5, z=BOSS_TOP - INSERT_L)
                        .translate((row_x, y, 0)))
        body = body.cut(cyl(SCREW_D, BOSS_TOP - GROOVE_FLOOR + 1, z=GROOVE_FLOOR)
                        .translate((row_x, y, 0)))
        body = body.cut(box_at(BOSS_SQ + 1, gw, BODY_TOP - GROOVE_FLOOR,   # groove through the boss
                               x=row_x, y=y, z=(BODY_TOP + GROOVE_FLOOR) / 2))

    # mount: 4 corner bolts (string pull taken by the chassis compression wall; these
    # just hold it down). Clear of the clamp rows.
    for sx in (X_FRONT - 3.0, X_BACK + 3.0):
        for sy in (-(HW - 4.0), HW - 4.0):
            body = body.cut(cyl(BOLT_D, BODY_TOP - Z_BOT + 2, z=Z_BOT - 1)
                            .translate((sx, sy, 0)))
    return body


nut_block = _build()
