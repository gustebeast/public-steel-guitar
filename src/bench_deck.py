"""BENCH DECK -- an open, braced stand-in for the top deck, for bench testing (user, 2026-11-05).

Its ONLY job is to hold the instrument together while the inside stays reachable: no fret lines,
no UI station, no fret light, no pickup. It keeps exactly what the real deck does structurally --
the cap over each rail and the dovetail tongue down each rail's groove (top_plate._deck_body), which
are the rail-to-rail tie -- and opens everything between the rails, leaving a frame and one X brace:

    CHORDS   the rail caps, carried CHORD_LIP past each rail's inner face
    ENDS     a bar across each end, so a section is a closed frame
    X BRACE  both diagonals of the frame's opening. One is in tension whichever way the body
             racks, so neither has to carry compression (a 250 long 8 x 6.4 strut buckles under
             ~80 N; in tension it takes kN)

THREE EQUAL SECTIONS, GAP apart like the real deck's panels, so the stack installs the same way (+X
first, -X out). Each is short enough to print with a 5 mm ear on every corner inside the bed (user,
2026-11-05: the first print's corners lifted off the plate; the bed's edges run cooler). The -X section
keeps the motor board's capture rib (top_plate._mctrl_capture): without it the board has nothing
holding it down.

PETG-GF: it is structure and nobody rests a forearm on it. Prints deck-DOWN like the real panels
(top_plate.PIECE_UP).
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import top_plate as TP
from .helpers import box_at, heal

CHORD_LIP = 6 * D.BEAD          # 4.8: each chord past its rail's inner face
END_W = 6 * D.BEAD              # 4.8: each end bar
DIAG_W = 10 * D.BEAD            # 8.0: each diagonal, across its own length
PRINT_UP = TP.PIECE_UP

# the sections, +X to -X: (xa, xb), equal, the deck's whole span less a GAP at each seam
N_SECTIONS = 3
_SEC_L = (TP.PX0 - TP.PX1 - (N_SECTIONS - 1) * TP.GAP) / N_SECTIONS
SECTIONS = tuple((TP.PX0 - k * (_SEC_L + TP.GAP), TP.PX0 - k * (_SEC_L + TP.GAP) - _SEC_L)
                 for k in range(N_SECTIONS))
BED_MAX = 250.0                 # the bed's usable length (top_plate.KEY_L)
BED_W = 235.0                   # ...and width (the left nozzle's strip)
EAR = 5.0                       # the ear on each corner: a disc this radius on the corner, 3/4 of it
                                # outside the part (user, 2026-11-05)
EAR_T = 0.4                     # one layer at the 0.8 nozzle: it lies on the bed (the deck face, TZ)
for _xa, _xb in SECTIONS:
    assert _xa - _xb + 2 * EAR <= BED_MAX, f"a bench deck section is {_xa - _xb:.2f} long: no room for ears"
assert TP.BY1 - TP.BY0 + 2 * EAR <= BED_W, "a bench deck section is too wide for ears"

WY0, WY1 = TP.YL + CHORD_LIP, TP.YH - CHORD_LIP     # the opening's Y span, every section


def _diag(x0, y0, x1, y1, z0, z1):
    """A DIAG_W bar from (x0, y0) to (x1, y1), z0..z1, overshooting its ends (clipped by the caller)."""
    ang = math.atan2(y1 - y0, x1 - x0)
    ln = math.hypot(x1 - x0, y1 - y0) + 2 * DIAG_W
    return (cq.Workplane("XY").rect(ln, DIAG_W).extrude(z1 - z0)
            .rotate((0, 0, 0), (0, 0, 1), math.degrees(ang))
            .translate(((x0 + x1) / 2, (y0 + y1) / 2, z0)))


def section(k: int) -> cq.Workplane:
    """Bench deck section k (0 = bridge end): the deck body with its opening cut and braced."""
    xa, xb = SECTIONS[k]
    body = TP._deck_body(xa, xb)
    end_b = END_W
    rib = None
    if k == len(SECTIONS) - 1:
        rib = TP._mctrl_capture()
        # the -X end bar is widened to carry the capture rib, a bead past its +X face
        end_b = max(END_W, rib.val().BoundingBox().xmax - xb + D.BEAD)
    ox0, ox1 = xa - END_W, xb + end_b                        # the opening, +X and -X faces
    assert ox0 - ox1 > 4 * DIAG_W, f"section {k} has no room left for a brace"
    z0, z1 = TP.BZ, TP.TZ
    win = box_at(ox0 - ox1, WY1 - WY0, z1 - z0 + 2.0, x=(ox0 + ox1) / 2, y=(WY0 + WY1) / 2,
                 z=(z0 + z1) / 2)
    brace = (_diag(ox0, WY0, ox1, WY1, z0, z1).union(_diag(ox0, WY1, ox1, WY0, z0, z1))
             .intersect(win))
    out = body.cut(win).union(brace)
    if rib is not None:
        out = out.union(rib)
    # THE EARS: on the bed face, one layer thick, snipped off after the print
    for x in (xa, xb):
        for y in (TP.BY0, TP.BY1):
            out = out.union(cq.Workplane("XY").circle(EAR).extrude(EAR_T)
                            .translate((x, y, TP.TZ - EAR_T)))
    out = heal(out)
    assert len(out.val().Solids()) == 1, f"bench deck section {k} is not one solid"
    return out


sections = [section(k) for k in range(len(SECTIONS))]

# what the scratch view draws: the three sections where the deck goes
demo = [(f"bench_deck_{k}", s) for k, s in enumerate(sections)]
