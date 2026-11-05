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

THREE SECTIONS, on the real deck's own seams so each fits the bed and the stack installs the same way
(+X first, -X out): the bridge-end REGION (where the pickup piece and fillers go), the MID span and
the KEYHEAD span. The keyhead section keeps the motor board's capture rib (top_plate._mctrl_capture):
without it the board has nothing holding it down.

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

# the three sections, +X to -X: (xa, xb). The region section ends a GAP short of the mid panel,
# exactly where the last filler did.
SECTIONS = ((TP.PX0, TP.REGION_X1 + TP.GAP), (TP.MID_X0, TP.MID_X1), (TP.KEY_X0, TP.KEY_X1))
BED_MAX = 250.0
for _xa, _xb in SECTIONS:
    assert _xa - _xb <= BED_MAX, f"a bench deck section is {_xa - _xb:.2f} long, over the bed"

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
    out = heal(out)
    assert len(out.val().Solids()) == 1, f"bench deck section {k} is not one solid"
    return out


sections = [section(k) for k in range(len(SECTIONS))]
