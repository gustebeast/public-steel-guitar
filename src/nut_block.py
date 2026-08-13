"""Nut block geometry (×1) — keyhead string termination. PETG-GF (clamps bear on it).

THE WRAP CAPSTAN (user). The string does not go straight from the break edge to a
clamp any more. It winds turns around a shared rod first, and the clamp behind it
only has to hold what the capstan leaves:

    bridge  ->  BREAK DOWEL  ->  WRAP ROD (n turns)  ->  GATE/CLAMP  ->  tail

Capstan (Euler-Eytelwein), T = T0.e^-mu.theta, mu = 0.15 steel on steel:

    no wrap    147 N at the clamp  ->  490 N of clamp force  ->  39 MPa on plastic
    1.5 turns   36 N               ->  119 N
    3.5 turns    5 N               ->   18 N

That is the whole point of the scheme: the clamp was never the wrong mechanism, it
was being asked for 490 N. Every string still terminates on the SAME clamp hardware
it did before (M4 cup-tip set screw in a brass heat-set insert) — it is only the
load that changed.

THE ROD IS THE BRIDGE AXLE'S OWN PART. Ø5 g6 precision shaft, D.BRIDGE_AXLE_D, the
same stock the changer end already buys — one shaft diameter now serves the bridge
axle and this rod, so a wrap post is not a new line in the BOM. Ø5 also bends the
.070 at 26.2% outer-fibre strain against Ø3's 37.2% (Ø6 would be 22.9%), i.e. it
sits where a guitar tuner post sits, which is the thing this is imitating.

ONE ROD, NOT TEN POSTS (user). Ten vertical posts would let each wrap climb in Z,
where height is free. A shared rod along Y makes the wrap climb ACROSS THE STRINGS
instead, and there the budget is D.NUT_PITCH — 6.5 mm — which is what sets the turn
count. See _turns: it is not a taste parameter, it is the largest number of turns
whose coil still leaves a printable web to the next string.

WHICH WAY THE WRAPS MARCH IS THE DESIGN (user-driven, and it is worth the sentence).
Every wrap marches -Y, toward the THICKER neighbour. Marching the other way puts the
two fattest strings' coils into each other and string 10 ends up with 1.12 mm of web,
under the two-bead floor. Marching -Y instead lands the fattest coil — the .070's,
which needs 6.53 mm of rod — in the OPEN AIR outboard of the field where there is no
neighbour at all, and every web in the comb clears 1.6:

    s1..s6  3.5 turns     s7  2.5     s8, s9  1.5     s10  3.5 (marches out free)
    thinnest web 1.76 mm (s9 -> s10), worst residual 35.8 N (s8, s9)

Local frame: X=0 at the break edge, +X toward the bridge (speaking length); Z=0 at
the string-top plane (= STRING_Z global); body hangs -Z to the deck plane.

PRINTS -X -> +X. The -X end face is the bed. Every bore here runs PERPENDICULAR to
that axis — the rod along Y, the screws and inserts along Z — so each is a
"horizontal" hole in the print sense and takes cadkit's 45° teardrop; without it they
print as sagging round ceilings and come out oval.

This is FUSED into the keyhead endplate (one printed piece — keyhead_endplate.py
unions it in); it stays its own module for the per-string layout.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import cyl, box_at, cyl_y
from cadkit.holes import teardrop_hole

PRINT_UP = (1.0, 0.0, 0.0)                      # build axis: the -X face is the bed

# ── hardware (the clamp is unchanged; only its load changed) ────────────────
INSERT_D = D.NUT_INSERT_D
INSERT_L = D.NUT_INSERT_L
SCREW_D  = D.NUT_SCREW_D
PIN_D    = D.NUT_PIN_D                          # Ø2 break dowel — AND the Ø2 anvil
PIN_L    = D.NUT_PIN_L
PIN_CLR  = D.NUT_PIN_CLR
PIN_SEAT_D = PIN_D + 2 * PIN_CLR
PIN_SEAT_L = PIN_L + 2 * PIN_CLR

ROD_D = D.BRIDGE_AXLE_D                         # Ø5 — the bridge axle's own shaft
ROD_FIT = 0.4                                   # the rod is LOCATED, not gripped: the wraps
                                                # load it -X and the comb takes that; it only
                                                # has to slide in through 10 fingers at once
ROD_BORE = ROD_D + ROD_FIT

# ── X layout (local frame) ─────────────────────────────────────────────────
# The prism is the KEYHEAD's footprint, D.KEYHEAD_W -- which is 4.2 thicker than the
# bridge's D.ENDPLATE_W, and this module is the reason why (user: extend the thickness
# along X to fit). The capstan spends X the old scheme did not: the rod, and the
# threading bay a hand needs around it. Behind that the clamp inserts STILL need two
# staggered rows, because O6 pockets on a 6.5 string pitch cannot share one row at all
# -- perfectly spaced they leave 0.5 mm of wall, and the turn counts differ so the
# worst pair closes to 5.78 and interferes outright.
#
# The growth is all -X, AWAY FROM THE STRINGS: X_FRONT and the break edge at X=0 do not
# move, so the scale length is untouched and the bridge stays exactly where it is.
X_FRONT = D.BREAK_PX_BUF                        # +4: +X lip / inboard face
X_BACK  = X_FRONT - D.KEYHEAD_W                 # -25.6: -X outer face (the bed face)
DOWEL_X = 0.0                                   # break edge = the scale "0"
ROD_X   = -8 * D.BEAD                           # -6.4 rod centre
# ROD_Z IS SET BY THE BREAK ANGLE, not by taste. The dowel -- not the rod -- has to
# terminate the speaking length, which means the string must leave the dowel at a real
# down-angle rather than drifting off it. The angle is worst for the THICKEST string
# (its centre starts lowest, so it has the least drop to play with over the same run),
# so one rod height for all ten is set by the .070 and every thinner string simply gets
# a steeper break. At -0.8 the .070 broke at 5.5 deg, half the floor -- three beads down
# fixes every string at once. See _break_deg, which is asserted below.
ROD_Z   = -3 * D.BEAD                           # -2.4 rod centre
BAY_R   = ROD_D / 2 + 2.5                       # 5.0 threading annulus around the rod --
                                                # the room a hand needs to pass the tail
                                                # around it, not a clearance
# TWO CLAMP ROWS, adjacent strings alternating. The near row clears the threading bay;
# the far row sits ROW_DX behind it, and ROW_DX is not a round number -- it is what the
# insert pitch demands. Neighbouring strings are always in DIFFERENT rows, so what has
# to clear O6 is the DIAGONAL between them: the tightest pair is 5.78 apart in Y (the
# wrap ends differ, since the turn counts do), and sqrt(5.78^2 + 5.6^2) = 8.05 leaves
# 2.05 of wall. Same-row neighbours are two strings apart and never closer than 11.88.
ROW_A   = -19 * D.BEAD                          # -15.2 near row: +X edge 0.8 clear of the bay
ROW_DX  = 7 * D.BEAD                            # 5.6 row separation -- see the diagonal above
ROW_B   = ROW_A - ROW_DX                        # -20.8 far row
GATE_X  = ROW_A                                 # the gate/clamp X for the near row. Either row
                                                # crosses its string's exit passage, so wound OUT
                                                # it is a GATE the tail threads past and wound IN
                                                # it is the CLAMP


def clamp_row_x(i: int) -> float:
    """X of string i's clamp. Adjacent strings alternate rows so the O6 inserts never
    share one; phased off the -Y end so the heaviest string lands on the NEAR row."""
    return ROW_A if (D.N_STRINGS - 1 - i) % 2 == 0 else ROW_B


_NX_WALL = abs(X_BACK - (ROW_B - INSERT_D / 2))
assert _NX_WALL >= D.SCREW_NX_WALL - 1e-9, (
    f"only {_NX_WALL:.2f} of wall behind the far clamp insert (floor {D.SCREW_NX_WALL})")
assert ROD_X - BAY_R > ROW_A + INSERT_D / 2, (
    "the threading bay has eaten into the near clamp insert's column")

# ── Y/Z extent ─────────────────────────────────────────────────────────────
Y_WALL   = 8.0
_HW_CLAMP = D.nut_y(0) + INSERT_D / 2 + Y_WALL  # ≈40.25 — what the CLAMP field needs
                                                # (HW itself is settled below: the wrap
                                                # field now reaches further -Y than this)
INSERT_GAP = 1.6
INSERT_POCKET_EXTRA = 0.8
INSERT_POCKET = INSERT_L + INSERT_POCKET_EXTRA  # 5.5
NUT_TOP  = INSERT_GAP + INSERT_POCKET           # 7.1 boss top / ceiling
NUT_BASE = D.DECK_TOP_Z - D.STRING_Z            # -10: prism base on the deck plane

# ── the wrap ───────────────────────────────────────────────────────────────
WRAP_F   = 1.05                                 # axial rise per turn, as a multiple of the
                                                # string's own diameter: the turns lie all but
                                                # touching. They must NOT cross -- under tension
                                                # a string crossing itself can cut itself in two
LANE_CLR = 0.5                                  # air each side of a coil, before its comb web
TURN_CHOICES = (3.5, 2.5, 1.5)                  # half-turns only: a whole number would put the
                                                # tail back out the +X side, facing the wrong way
MU = 0.15                                       # steel on steel, dry, deliberately pessimistic
STRING_T = 147.0                                # per-string tension the capstan is dividing


def _adv(i: int) -> float:
    """How far string i's coil marches along the rod (always -Y)."""
    return _turns(i) * WRAP_F * D.STRING_GAUGE[i]


def _web(i: int, t: float) -> float:
    """Printed web left between string i's coil and its -Y neighbour, if it took t turns.
    The outermost string has no -Y neighbour, so its coil is free to run out into air."""
    if i + 1 >= D.N_STRINGS:
        return math.inf
    return (D.NUT_PITCH - t * WRAP_F * D.STRING_GAUGE[i]
            - D.STRING_GAUGE[i] / 2 - D.STRING_GAUGE[i + 1] / 2 - 2 * LANE_CLR)


def _turns(i: int) -> float:
    """Turns for string i: the MOST it can take and still leave its neighbour a
    two-bead web. More turns is strictly better (it is what divides the 147 N), so
    this takes the largest that fits rather than a number someone picked."""
    for t in TURN_CHOICES:
        if _web(i, t) >= D.MIN_WALL_2P - 1e-9:
            return t
    raise AssertionError(
        f"string {i + 1} (g {D.STRING_GAUGE[i]:.3f}) cannot take even {TURN_CHOICES[-1]} "
        f"turns at {D.NUT_PITCH} pitch — its web would be {_web(i, TURN_CHOICES[-1]):.2f}")


def residual(i: int) -> float:
    """Tension still left at the clamp after the wrap — what the clamp actually holds."""
    return STRING_T * math.exp(-MU * _turns(i) * 2 * math.pi)


# Every string is checked at import: the webs are what make the comb printable and the
# residual is what makes the clamp credible, and both are functions of the gauge table,
# so a different string set has to re-pass them rather than quietly go out of spec.
_WORST_WEB = min(_web(i, _turns(i)) for i in range(D.N_STRINGS - 1))
_WORST_RES = max(residual(i) for i in range(D.N_STRINGS))
assert _WORST_WEB >= D.MIN_WALL_2P - 1e-9, f"thinnest comb web is {_WORST_WEB:.2f}"
assert _WORST_RES <= 60.0, (
    f"the worst string still leaves {_WORST_RES:.1f} N at the clamp — the wrap is not "
    f"doing its job and the clamp is back to bearing on plastic")


def wrap_y(i: int) -> tuple[float, float]:
    """(start, end) Y of string i's coil. It arrives on its own lane and leaves -Y of it."""
    y0 = D.nut_y(i)
    return y0, y0 - _adv(i)


def rod_span() -> tuple[float, float]:
    """(y0, y1) the rod has to cover: every bay plus a bearing length in the end walls."""
    lo = min(wrap_y(i)[1] for i in range(D.N_STRINGS)) - D.STRING_GAUGE[-1] / 2 - LANE_CLR
    return lo - 2 * D.BEAD, D.nut_y(0) + 2 * D.BEAD


ROD_Y0, ROD_Y1 = rod_span()
ROD_END_W = D.MIN_WALL_2P                       # the +Y bore is BLIND; that wall is the stop
# THE BLOCK IS NOW AS WIDE AS THE WRAP FIELD, not as wide as the clamp field. The .070
# marches 6.53 mm OUTWARD past the last string -- that free air is exactly what buys it
# 3.5 turns -- so the -Y end of the rod lands 0.12 outside the old half-width. Take the
# wider of the two requirements and put the surplus on the bead grid, so the block grows
# by whole beads rather than by whatever the gauge table happens to ask for.
_HW_NEED = max(_HW_CLAMP, ROD_END_W - ROD_Y0)
HW = D.nut_y(0) + math.ceil((_HW_NEED - D.nut_y(0)) / D.BEAD - 1e-9) * D.BEAD
assert ROD_Y0 - ROD_END_W >= -HW, "the rod's -Y end has run out of block to sit in"

GROOVE_W = 1.8
ROOF_CLR = 0.8
BREAK_ANGLE = 10.0                              # MIN break angle over the dowel, so the DOWEL
                                                # (not the rod) terminates the speaking length


def _break_deg(i: int) -> float:
    """Down-angle string i takes as it leaves the break dowel for the rod. The string
    runs level over the dowel at -g/2 and meets the rod's +X tangent at ROD_Z."""
    run = DOWEL_X - (ROD_X + ROD_D / 2 + D.STRING_GAUGE[i] / 2)   # dowel -> rod tangent
    return math.degrees(math.atan2(abs(ROD_Z) - D.STRING_GAUGE[i] / 2, run))


_WORST_BREAK = min(_break_deg(i) for i in range(D.N_STRINGS))
assert _WORST_BREAK >= BREAK_ANGLE - 1e-9, (
    f"the worst string breaks over the dowel at only {_WORST_BREAK:.1f} deg (floor "
    f"{BREAK_ANGLE}) — at that angle the ROD, not the dowel, sets the scale length")


def _gw(i: int) -> float:
    """Gauged channel width — each string lays in and centres itself."""
    return max(D.STRING_GAUGE[i] + 0.8, 1.4)


def _dowel_pocket(seat_z, y):
    """The break dowel's seat, as a solid to CUT. A round cradle cups it from BELOW so
    gravity retains it, wrapping 90° up the -X side to a vertical wall but only 45° up
    the +X side -- a steeper +X wall would be a print overhang in the -X -> +X build --
    then opening at 45° out to the +X face, which is also how the dowel drops in."""
    R = PIN_SEAT_D / 2.0
    s = R * math.sin(math.radians(45.0))
    z_face = seat_z + X_FRONT - 2.0 * s
    prof = (cq.Workplane("XZ")
            .moveTo(-R, NUT_TOP)
            .lineTo(-R, seat_z)
            .threePointArc((0.0, seat_z - R), (s, seat_z - s))
            .lineTo(X_FRONT, z_face)
            .lineTo(X_FRONT, NUT_TOP)
            .close())
    return prof.extrude(PIN_SEAT_L / 2.0, both=True).translate((0.0, y, 0.0))


def _build() -> cq.Workplane:
    # ONE solid prism, the endplate footprint, and every feature is CUT from it.
    body = box_at(X_FRONT - X_BACK, 2 * HW, NUT_TOP - NUT_BASE,
                  x=(X_FRONT + X_BACK) / 2, y=0, z=(NUT_TOP + NUT_BASE) / 2)

    for i in range(D.N_STRINGS):
        y0, y1 = wrap_y(i)
        g = D.STRING_GAUGE[i]
        gw = _gw(i)
        pin_z = -g - PIN_D / 2                  # dowel centre: its top at -g, string top at 0
        seat_z = pin_z + PIN_CLR                # seat raised so its BOTTOM is flush with the
                                                # dowel's -- no Z slop under the gauge datum
        # ENTRY: level over the dowel (the dowel is the scale, so the string leaves it flat),
        # then on -X to the bay. Two floors: the +X run keeps SOLID under the dowel so it is
        # supported across the channel and not only at its ends.
        body = body.cut(box_at(X_FRONT - (-PIN_D / 2), gw, ROOF_CLR - pin_z,
                               x=(X_FRONT + -PIN_D / 2) / 2, y=y0,
                               z=(ROOF_CLR + pin_z) / 2))
        body = body.cut(box_at((-PIN_D / 2) - (ROD_X + BAY_R), gw, ROOF_CLR - (ROD_Z - g),
                               x=((-PIN_D / 2) + (ROD_X + BAY_R)) / 2, y=y0,
                               z=(ROOF_CLR + ROD_Z - g) / 2))
        body = body.cut(_dowel_pocket(seat_z, y0))

        # THE BAY: the room the coil lives in and the tail is threaded through. Open to
        # the TOP, because that is how a string is wound on -- down the -X side, under the
        # rod, up the +X side, and round again, one lane per string so the walls guide the
        # tip instead of letting it wander next door.
        bay_y1 = y0 + g / 2 + LANE_CLR
        bay_y0 = y1 - g / 2 - LANE_CLR
        body = body.cut(box_at(2 * BAY_R, bay_y1 - bay_y0, (NUT_TOP + 1.0) - (ROD_Z - BAY_R),
                               x=ROD_X, y=(bay_y0 + bay_y1) / 2,
                               z=((ROD_Z - BAY_R) + NUT_TOP + 1.0) / 2))

        # EXIT: the tail leaves the rod's -X tangent at the coil's far end and runs out the
        # back face, crossing the clamp screw's column on the way -- see GATE_X.
        body = body.cut(box_at((ROD_X - BAY_R) - X_BACK, gw, ROOF_CLR - (ROD_Z - g),
                               x=(X_BACK + ROD_X - BAY_R) / 2, y=y1,
                               z=(ROOF_CLR + ROD_Z - g) / 2))
        # ANVIL: a second Ø2 dowel under the tail at the clamp, so the pinch is
        # metal-on-metal and the plastic floor is not the thing being squeezed.
        gx = clamp_row_x(i)
        anvil_z = ROD_Z - g / 2 - PIN_D / 2
        body = body.cut(_anvil_pocket(anvil_z + PIN_CLR, y1, gx))
        # CLAMP: buried M4 insert from +Z and the set-screw bore down onto the tail.
        body = body.cut(cyl(INSERT_D, INSERT_POCKET + 0.5, z=INSERT_GAP)
                        .translate((gx, y1, 0)))
        body = body.cut(cyl(SCREW_D, NUT_TOP - (ROD_Z - g) + 1, z=ROD_Z - g)
                        .translate((gx, y1, 0)))

    # THE ROD BORE, cut LAST so none of the unions above can refill it (the bridge end
    # lost both its axle bores exactly that way). BLIND at +Y: that wall is the rod's +Y
    # stop, the same trick the bridge axle uses. It slides in from -Y through all ten
    # comb webs at once, so it must be a precision shaft and not a dowel.
    body = body.cut(teardrop_hole(ROD_BORE, (ROD_Y1 - ROD_Y0) + 20.0,
                                  axis_point=(ROD_X, ROD_Y0 - 20.0, ROD_Z),
                                  axis_dir=(0.0, 1.0, 0.0), print_up=PRINT_UP))
    return body


def _anvil_pocket(seat_z, y, gx):
    """The anvil dowel's seat: the same cradle as the break dowel's, opening +X so it
    drops in from the bay side rather than needing its own access."""
    R = PIN_SEAT_D / 2.0
    s = R * math.sin(math.radians(45.0))
    prof = (cq.Workplane("XZ")
            .moveTo(gx - R, NUT_TOP)
            .lineTo(gx - R, seat_z)
            .threePointArc((gx, seat_z - R), (gx + s, seat_z - s))
            .lineTo(gx + s, NUT_TOP)
            .close())
    return prof.extrude(PIN_SEAT_L / 2.0, both=True).translate((0.0, y, 0.0))


def rod() -> cq.Workplane:
    """The wrap rod itself, in the nut block's local frame — the bridge axle's shaft."""
    return cyl_y(ROD_D, ROD_Y1 - ROD_Y0, y0=ROD_Y0, x=ROD_X, z=ROD_Z)


nut_block = _build()
