"""Pickup carrier hardware — the DEMO pickup body + the clamp bolt.

The pickup is held by the swappable PICKUP PIECE in the deck (see top_plate.py):
it drops into a channel formed by two depending skirts, pokes up through the
deck opening, and is pinned by two clamp bolts that pass through X-slots in the
skirts and thread the pickup's sides. Loosen the bolts -> slide +/-22.5 mm in X
(tone) -> retighten. Coarse moves come from re-slotting the whole piece.

  X (tone, bridge<->neck): clamp-bolt X-slots (fine) + piece slot position (coarse)
  Z (string gap, set once): the pickup top sits GAP below the heaviest string;
    swap a pickup of different height or add a printed shim under it to tune.
  Size: the channel skirts are spaced for the demo's 99 mm length; reprint the
    piece for a very different footprint.

The clamp bolts are the stocked M4 button-heads (zero new BOM lines).
Frames: pickup centred X/Y with its top at z=0 (build.py lifts it to PK_TOP);
clamp bolt axis +Y with its shank tip at y=0 (build mirrors it for the -Y side).
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_y

# ── the pickup itself (DEMO dummy; the piece adjusts around it) ───────────────
PK_W, PK_L, PK_H = 33.0, 99.0, 20.0            # X (width), Y (length), Z (height)
GAP     = 3.0                                   # pickup top -> heaviest string bottom
PK_TOP  = D.STRING_Z - max(D.STRING_GAUGE) - GAP
PK_BOT  = PK_TOP - PK_H

# ── clamp bolt (stocked M4 button head) ──────────────────────────────────────
CLAMP_BOLT_D = 4.0
CLAMP_BOLT_L = 12.0


def pickup_demo() -> cq.Workplane:
    """DEMO pickup body (George L E-66-ish 33x99x20), centred X/Y, top at z=0."""
    return box_at(PK_W, PK_L, PK_H, z=-PK_H / 2)


def clamp_bolt() -> cq.Workplane:
    """DEMO M4x12 button-head clamp bolt, axis +Y: shank tip at y=0, head at +Y."""
    shank = cyl_y(CLAMP_BOLT_D, CLAMP_BOLT_L, y0=0.0)
    head = cyl_y(7.5, 2.2, y0=CLAMP_BOLT_L)
    return shank.union(head)
