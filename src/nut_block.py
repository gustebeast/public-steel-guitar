"""Nut block geometry (×1) — keyhead string termination. PETG-GF (clamps bear on it).

This is FUSED into the keyhead endplate (one printed piece — keyhead_endplate.py unions
this geometry in); kept as its own module for the per-string layout. The block is ONE
SOLID PRISM spanning the full keyhead-endplate X-thickness (rail outer faces of the nut
field), the nut Y-width, and Z from the deck plane up to the boss top -- and EVERY feature
is CUT from it (no additive bosses). Its X extent is the very thing that SETS the endplate
thickness: dimensions.py walks the hardware along X (lip, dowel, two clamp rows, insert
wall) to derive D.ENDPLATE_W, and this module reads those same constants back to place the
cuts, so the prism and the endplate always agree by construction.

Per string it does two jobs:

  1. Break edge — a hardened Ø2 dowel pin (DEMO) sets the open-string scale endpoint.
     Each pin sits at a GAUGED height (D.STRING_GAUGE) so every string TOP lands
     coplanar at STRING_Z. The string lays into an OPEN V-groove over the pin (no
     threading through a hole).

  2. Clamp — the plain end, laid in the same groove, is pinched DOWN onto the solid
     PETG-GF floor by an M4 cup-tip set screw (DEMO) running through a deeply-buried brass
     heat-set insert (DEMO). Clamps alternate between TWO rows (adjacent strings alternate
     front/back) so each Ø5.6 insert has ~13 mm of pitch (thick walls → no pull-out).
     Print with high wall/floor counts for a solid clamp floor. Reprint the whole keyhead
     piece to match a different string set.

Local frame: X=0 at the break edge, +X toward the bridge (speaking length); Z=0 at the
string-top plane (= STRING_Z global); body hangs −Z to the deck plane.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, box_at

# ── hardware sizes (the X-driving ones live in dimensions; read them back here) ──
INSERT_D = D.NUT_INSERT_D
INSERT_L = D.NUT_INSERT_L
SCREW_D  = D.NUT_SCREW_D
PIN_D    = D.NUT_PIN_D                          # dowel nominal Ø2
PIN_L    = D.NUT_PIN_L                          # dowel length 4 (axis Y)
PIN_CLR  = D.NUT_PIN_CLR                        # 0.4 clearance perimeter around the dowel
PIN_SEAT_D = PIN_D + 2 * PIN_CLR                # = 2.8: pocket Ø (0.4 all round the dowel)
PIN_SEAT_L = PIN_L + 2 * PIN_CLR                # = 4.8: pocket length (0.4 past each dowel end)

# ── X layout (local frame) — DERIVED from the same buffers that set D.ENDPLATE_W,
# so the prism is exactly the endplate footprint (−21 .. +4 → global −636 .. −611) ──
X_FRONT = D.BREAK_PX_BUF                                    # +4: +X lip / inboard face
ROW1_X  = -D.DOWEL_SCREW_RUN                                # −8: near clamp row (short run)
ROW2_X  = ROW1_X - D.SCREW_ROW_GAP                          # −16: far clamp row (long run)
X_BACK  = ROW2_X - D.NUT_INSERT_D / 2 - D.SCREW_NX_WALL     # −21: −X outer face (wall behind insert)

# ── Y/Z extent ──
Y_WALL   = 8.0                                  # wall +-Y of the outermost clamp insert
HW       = D.nut_y(0) + INSERT_D / 2 + Y_WALL   # half-width to that wall (≈40)
INSERT_GAP = 1.6                                # insert bottom sits this far ABOVE the string plane:
                                                # close to the string (little dead Z below it) but
                                                # clear of it -- the clamped string sits lower still,
                                                # so true clearance is ~3 mm.
INSERT_POCKET_EXTRA = 0.8                       # pocket sunk this much DEEPER than the insert is long,
                                                # so the insert can dip just below the top surface
                                                # (more wall over it -> stronger heat-set grip). This
                                                # raises the CEILING, not the floor -- the 1.6 gap is
                                                # untouched.
INSERT_POCKET = INSERT_L + INSERT_POCKET_EXTRA  # = 5.5: the install-hole depth
NUT_TOP  = INSERT_GAP + INSERT_POCKET           # boss top / ceiling (= 7.1 → global 23.1). The set
                                                # screw (D.NUT_SCREW_L=10) is longer than gap+pocket,
                                                # so its tail still stands PROUD of this top.
NUT_BASE = D.DECK_TOP_Z - D.STRING_Z            # −10: prism base sits on the deck plane (global 6)


def clamp_row_x(i: int) -> float:
    """X of string i's clamp row. Adjacent strings alternate near/far rows so each Ø5.6
    insert keeps ~13 mm of Y pitch; phased off the −Y end so the heaviest string (last
    index) lands on the near ROW1 -- the shorter run, hence the shallower clamp floor."""
    return ROW1_X if (D.N_STRINGS - 1 - i) % 2 == 0 else ROW2_X


GROOVE_W = 1.8                                  # lay-in groove width (string channel)
GROOVE_FLOOR = -2.0                             # nominal groove bottom (per-string floor goes deeper)
ROOF_CLR = 0.8                                  # vertical headroom from the string top to the FLAT channel
                                                # roof (2x the 0.4 lay-in side gap). Flat (not /\) is fine
                                                # because the keyhead prints ALONG X, so the roof is a wall
                                                # parallel to the layers -- not a bridged ceiling
BREAK_ANGLE = 10.0                              # MIN string break angle over the pin (deg). The
                                                # down-bearing on the pin is T*sin(angle); the
                                                # vibrating string lifts with ~T*pi*a/L, so the needed
                                                # angle is tension-independent. The clamp floor drops
                                                # per string (floor = -(gauge + run*tan(angle))) to
                                                # guarantee it, so the pin -- not the clamp -- cleanly
                                                # terminates the speaking length. Thin/already-steep
                                                # strings keep the nominal floor.


def clamp_floor(i: int) -> float:
    """Per-string groove floor at the clamp (local Z). Deep enough that the string leaves the
    pin at >= BREAK_ANGLE over the run to the clamp, never shallower than GROOVE_FLOOR. The set
    screw presses the string DOWN onto this floor, so floor + gauge IS the clamped string top --
    the build draws the string (and the screw tip) pressed to here, not floating above it."""
    g = D.STRING_GAUGE[i]
    return min(GROOVE_FLOOR, -(g + abs(clamp_row_x(i)) * math.tan(math.radians(BREAK_ANGLE))))


EXIT_ANGLE = 45.0                               # the string leaves the nut at this down-angle,
                                                # primed for the loop into the keyhead stow bore
EXIT_X0    = ROW2_X - SCREW_D / 2                # curve start: the -X EDGE of the far clamp's set
                                                # screw (not its centre) -- COMMON to all strings, so
                                                # every screw is fully clear before the floor drops
EXIT_X1    = X_BACK                               # reach the -X outer face (X_BACK is exactly it now,
                                                # so the exit hole is no longer left short by a 1 mm lip)


def _exit_curve(floor, gw, y):
    """A down-CURVE in the groove floor from EXIT_X0 (tangent-flat, just past the far clamp)
    to the -X edge, bending the string's free end down to EXIT_ANGLE so it leaves the nut
    already angled toward the stow loop. Same start + shape for every string (only `floor`
    differs), so they all exit the same way. Cuts the crescent between the flat floor and
    the descending arc, so the remaining floor IS the arc (tangent-flat at EXIT_X0)."""
    R = (EXIT_X0 - EXIT_X1) / math.sin(math.radians(EXIT_ANGLE))
    drop = R * (1.0 - math.cos(math.radians(EXIT_ANGLE)))
    th = math.radians(EXIT_ANGLE / 2.0)
    mid = (EXIT_X0 - R * math.sin(th), floor - R * (1.0 - math.cos(th)))
    prof = (cq.Workplane("XZ").moveTo(EXIT_X0, floor)
            .lineTo(EXIT_X1, floor).lineTo(EXIT_X1, floor - drop)
            .threePointArc(mid, (EXIT_X0, floor)).close())
    return prof.extrude(gw / 2.0, both=True).translate((0, y, 0))


def _channel(gw, floor, y, x0, x1):
    """A run of the string channel over x0..x1, as a solid to CUT: a rectangular slot, gw wide,
    from `floor` up to a FLAT roof ROOF_CLR above the string-top plane, with SOLID material above
    it to the ceiling (no open slot to the top -> the clamp inserts sit in solid material for grip).
    A flat roof is fine because the keyhead prints ALONG X (the channel length is the build
    direction), so the roof is a wall parallel to the layers, not a bridged ceiling. The string
    keeps ROOF_CLR over its top and the gauged side gap at the walls; the insert pocket, set-screw
    bore and dowel access punch up through it. Cut in TWO runs at different floors (see _build): a
    shallow one at the dowel midline that leaves solid UNDER the dowel, and the deep one to the exit."""
    roof = ROOF_CLR                                        # flat roof, ROOF_CLR above the string top (z=0)
    return box_at(x1 - x0, gw, roof - floor, x=(x0 + x1) / 2.0, y=y, z=(roof + floor) / 2.0)


def _dowel_pocket(seat_z, y):
    """The dowel seat as a solid to CUT (an X-Z profile extruded along Y). A round cradle (Ø
    PIN_SEAT_D) cups the dowel from BELOW for gravity retention (gravity pulls the pin −Z), with
    its bottom flush to the dowel bottom and 0.4 side clearance growing from the floor. The wrap is
    asymmetric for the print (keyhead prints −X→+X): a full 90° up the −X side to a vertical wall,
    but only 45° up the +X side -- a steeper +X wall would be a print overhang. Above the 45° point
    the +X side opens at 45° (the printable limit) out to the +X face, which also clears the access
    overhang and lets the dowel drop in. Little +X retention, but the net +X string push is ~1-2 N."""
    R = PIN_SEAT_D / 2.0
    s = R * math.sin(math.radians(45.0))                     # the +X 45° (4:30) point offset
    z_face = seat_z + X_FRONT - 2.0 * s                      # where the +X 45° slope meets the +X face
    prof = (cq.Workplane("XZ")
            .moveTo(-R, NUT_TOP)                              # top of the −X wall
            .lineTo(-R, seat_z)                              # down the −X vertical wall to the 90° point
            .threePointArc((0.0, seat_z - R), (s, seat_z - s))  # cradle: −X 90° → bottom → +X 45°
            .lineTo(X_FRONT, z_face)                         # 45° slope out to the +X face (no overhang)
            .lineTo(X_FRONT, NUT_TOP)                        # up the open +X face
            .close())                                        # across the top
    return prof.extrude(PIN_SEAT_L / 2.0, both=True).translate((0.0, y, 0.0))


def _build() -> cq.Workplane:
    # ONE solid prism: the full endplate X-thickness × the nut Y-width × deck plane up to
    # the boss top. ALL string-termination features are CUT from it -- no additive bosses.
    body = box_at(X_FRONT - X_BACK, 2 * HW, NUT_TOP - NUT_BASE,
                  x=(X_FRONT + X_BACK) / 2, y=0, z=(NUT_TOP + NUT_BASE) / 2)

    for i in range(D.N_STRINGS):
        y = D.nut_y(i)
        g = D.STRING_GAUGE[i]
        gw = max(g + 0.8, 1.4)                  # GAUGED groove width — each string lays in + centres
        pin_z  = -g - PIN_D / 2                 # dowel centre -> its top at −g (string top 0)
        seat_z = pin_z + PIN_CLR                # seat (Ø dowel+2*clr) centre, raised so its BOTTOM is
                                                # flush with the dowel bottom: no Z clearance under the
                                                # gauge datum (clearance grows 0 at the floor -> clr at
                                                # the sides), the dowel rests where the string presses it
        dowel_nx = -PIN_D / 2                   # dowel −X extent (break starts here)
        row_x = clamp_row_x(i)
        floor = clamp_floor(i)                  # per-string clamp floor (string is pressed down to here)

        # string channel under a FLAT roof, in TWO floor runs: shallow at the dowel midline from the
        # +X entry to the dowel's −X edge (leaves SOLID under the dowel so it's supported across the
        # channel, not just at its ends), then the deep break-angle floor on out to the exit
        body = body.cut(_channel(gw, pin_z, y, dowel_nx, X_FRONT))
        body = body.cut(_channel(gw, floor, y, X_BACK, dowel_nx))
        # break-pin seat: a round cradle cupping the dowel from below (gravity retention), wrapping 90°
        # up the −X side and 45° up the +X side, then opening at 45° out to the +X face (print + access)
        body = body.cut(_dowel_pocket(seat_z, y))
        # clamp: buried M4 insert (from +Z, punching up through the roof) + set-screw bore down
        # to the string, which pinches it DOWN onto the solid (PETG-GF) groove floor. The pocket
        # runs from the gap up to the ceiling (INSERT_POCKET deep) so the insert recesses slightly.
        body = body.cut(cyl(INSERT_D, INSERT_POCKET + 0.5, z=INSERT_GAP)
                        .translate((row_x, y, 0)))
        body = body.cut(cyl(SCREW_D, NUT_TOP - floor + 1, z=floor)
                        .translate((row_x, y, 0)))
        # exit down-curve: bend the free end to EXIT_ANGLE toward the stow loop
        body = body.cut(_exit_curve(floor, gw, y))

    # No mount bolts: this block is FUSED into the keyhead endplate (one PETG-GF piece,
    # keyhead_endplate.py) which drops in and is held by the rail-end dovetails + joinery.
    return body


nut_block = _build()
