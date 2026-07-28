# -*- coding: utf-8 -*-
"""cadkit.printing — FDM print-process limits that geometry must respect.

Currently one rule: the MINIMUM MATERIAL floor.

    min_wall(nozzle_d)          -> a single bead: nozzle_d + SLICER_BUFFER
    min_wall(nozzle_d, beads=N) -> N deliberate beads: N * nozzle_d   (no buffer)

WHY A BUFFER, AND ONLY ON A SINGLE BEAD
Material EXACTLY one nozzle wide sometimes lands just under the slicer's
extrusion-width threshold and gets DROPPED, leaving a gap where you drew solid.
So the floor for any lone web / ceiling / rib is nozzle_d + SLICER_BUFFER
(0.05 mm) — just enough to push it safely over the threshold.

But a wall designed as an INTEGER number of beads (2*nozzle for a 2-perimeter
wall, 3*nozzle, ...) needs no buffer: the slicer lays exactly that many full
beads and the buffer would only bloat the wall and push the perimeters out of
register. That is why we do NOT simply bump the nozzle to nozzle+0.05 globally —
the buffer belongs on the one-bead floor, not on multi-bead walls.

USE IT
Set the nozzle ONCE per project and derive every minimum from it:

    from cadkit.printing import min_wall
    NOZZLE_D = 0.8
    MIN_WALL = min_wall(NOZZLE_D)      # 0.85 — floor for any single-bead feature

RULE OF THUMB: no load- or seal-bearing material dimension below
min_wall(nozzle). This bites hardest at HIDDEN thin spots — a boss ceiling over
a cross-bore, a web between two pockets — where a nominal number looks fine but
the finished solid is a razor. Check those on the real solid, not on paper.

Self-test: `python -m cadkit.printing` (or run this file).
"""

__all__ = ["SLICER_BUFFER", "DEFAULT_NOZZLE_D", "min_wall"]

# Material == one nozzle can be skipped by the slicer; pad a lone bead past the
# threshold by this much. NOT applied to deliberate integer-bead walls.
SLICER_BUFFER = 0.05

# A common FDM nozzle. Projects override with their own (this repo runs 0.8).
DEFAULT_NOZZLE_D = 0.4


def min_wall(nozzle_d=DEFAULT_NOZZLE_D, beads=1):
    """Smallest material thickness that reliably prints.

    beads == 1 (the default): a single bead, floored at nozzle_d + SLICER_BUFFER
    so the slicer can't drop it. beads > 1: a deliberate multi-bead wall,
    beads * nozzle_d with NO buffer (the slicer lays that many full beads)."""
    if nozzle_d <= 0:
        raise ValueError("min_wall: nozzle_d must be > 0, got %r" % (nozzle_d,))
    if beads < 1:
        raise ValueError("min_wall: beads must be >= 1, got %r" % (beads,))
    if beads == 1:
        return nozzle_d + SLICER_BUFFER
    return beads * nozzle_d


if __name__ == "__main__":
    # One bead gets the buffer; multi-bead walls are exact multiples.
    assert abs(min_wall(0.8) - 0.85) < 1e-12, min_wall(0.8)
    assert abs(min_wall(0.8, beads=1) - 0.85) < 1e-12
    assert abs(min_wall(0.8, beads=2) - 1.6) < 1e-12   # 2 perimeters, no buffer
    assert abs(min_wall(0.4) - 0.45) < 1e-12
    assert abs(min_wall(0.4, beads=3) - 1.2) < 1e-12
    for bad in (0.0, -0.4):
        try:
            min_wall(bad); raise AssertionError("expected ValueError")
        except ValueError:
            pass
    try:
        min_wall(0.8, beads=0); raise AssertionError("expected ValueError")
    except ValueError:
        pass
    print("cadkit.printing self-test OK")
