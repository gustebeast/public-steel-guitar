# -*- coding: utf-8 -*-
"""FRET LIGHTING — the per-fret light cell, and the optics that size it.

One CELL per fret: an opaque box that takes three LEDs off the board below and turns them
into an evenly lit 2.4 x 79.6 line, while letting no light reach its neighbours except by
the one path the user allows.

    "Having some mixing near the top and bottom via a narrow channel is okay,
     mixing near the center is not."  (user, 2026-09-29)

WHAT THE CELL IS, bottom to top:

    z -19.00 .. -17.40   the LED board (1.6), clearing the tee PCBs at -19.65
    z -16.00             the 5050's emitting face
    z -16.00 ..   0.00   the TUNNEL: opaque walls on the fret pitch, gently tapered
    z   0.00 ..   4.80   a TRANSPARENT COLUMN through the deck's base, aperture-wide
    z   4.80 ..   6.40   the fret inlay itself, in the colour layer

⚠ THE ISOLATION HAS TO REACH z = 4.80, NOT z = 0, and that is why this is deck geometry
rather than a part clipped underneath. The deck's base is 4.80 of TRANSPARENT PCTG and it
is continuous across the panel: seal a tunnel at the deck's underside and light simply
crosses to the neighbouring fret INSIDE THE SLAB, 9.14 mm away at the bridge end. So in the
comb walls run UP THROUGH the base to the colour layer. Each cell is then bounded on all
four sides by opaque material from the board to the inlay, and the transparent base BETWEEN
two walls is simply part of that cell's cavity -- a 4.8 mm diffuser sitting right under its
own aperture.

⚠ AN EARLIER VERSION OF THIS NOTE SAID THE BASE HAD TO GO OPAQUE in the fret field, with
transparent columns left under each line. That is not needed and was the expensive answer:
the walls already isolate, because there is a wall on EVERY fret boundary running the full
height. Dropping it saves most of the second-material volume and leaves the deck's base the
single transparent slab it already is.

THE BLEED PATH THAT IS ALLOWED, and it is the only one: the fret inlay and the border strip
meet in the COLOUR LAYER at |y| = FRET_HY, a junction one aperture wide and 1.6 tall.
Narrow, at the extreme ends, and exactly what the user described. Everything below 4.80 is
sealed by opaque material.

WHY THREE LEDs LAND EVENLY (see `uniformity()`, which is what chose the numbers):
illuminance from a Lambertian source at depth h falls as (h^2/(h^2+y^2))^2, so one LED
under the middle of a 79.6 line leaves the ends 22x down. Three sources plus the two END
REFLECTORS give 1.21 : 1 over the whole line. The reflectors matter more than they look --
without them the same geometry is 1.9 : 1, because an end point is lit from one side where
a mid-gap is lit from two.
"""
from __future__ import annotations

from . import dimensions as D

# ── the fret line this has to light ───────────────────────────────────────────────────
# ⚠ READ FROM top_plate, NOT COPIED. This module first carried HALF_LEN = 39.80 as a
# "mirrors top_plate" constant and the cross-check caught it 6.0e-06 out: the real
# FRET_HY is 39.799993975610, because it is BORDER_HY - INLAY_W and BORDER_HY is
# _string_half_span() off the STRING FAN. It is a computed value that moves whenever the
# string geometry moves, so a copy of it goes stale silently.
#
# The import is LATE because top_plate imports THIS module to build the cells -- the same
# cycle ui_panel has, and the same way out of it.
def _tp():
    from . import top_plate as TP
    return TP


def half_len() -> float:
    """Half the fret line in Y — top_plate.FRET_HY."""
    return _tp().FRET_HY


def aperture() -> float:
    """The inlay's width in X — top_plate.INLAY_W."""
    return _tp().INLAY_W


def aperture_z() -> float:
    """The inlay's underside — top_plate.TZ - FRET_T."""
    TP = _tp()
    return TP.TZ - TP.FRET_T


# Nominal figures, for sizing only. Anything that must AGREE with the deck calls the
# functions above; these exist so the Z stack and the optics can be written down here.
HALF_LEN_NOM = 39.80
APERTURE_NOM = 2.40
APERTURE_Z_NOM = 4.80

# ── the Z stack ───────────────────────────────────────────────────────────────────────
# ⚠ THE FLOOR IS STRUCTURE, NOT CABLE. Probing a 70 mm slab under the whole fret field:
# the highest STRUCTURAL part is the tee PCBs at -19.65; the things above it (wire_canl
# -17.15, wire_canh -19.09) are harness and move. Designing to the CABLE floor instead
# costs 2.5 mm of depth and takes the line from 1.21 : 1 to 1.35 : 1, so the harness is
# asked to move rather than the optics give way.
# ⚠ AND THE PANEL SLIDES OVER THEM, so this is a SLIDING clearance, not a static one
# (user, 2026-09-29: "we need to clear the PCBs on each motor so we can slide the top
# panels on and off"). The tee PCBs -- one per motor, tops at -19.65, at y -6.00, dead in
# the middle of the cell envelope -- are swept by the whole panel over a 465 mm stroke.
# BOARD_BOT was -19.00, which cleared them by 0.65: true at rest and not a clearance you
# would slide a printed panel through. 2.00 costs 1.35 of depth and takes the line from
# 1.21 : 1 to 1.28 : 1, which is the right way round.
# ⚠ AND THE TEE PCBs ARE NOT THE FLOOR. They are the highest STRUCTURE, but the CAN
# harness runs ABOVE them: wire_canl tops out at -17.15, two and a half millimetres over
# the boards it feeds. The gate found it the moment the board was placed -- fret_board_0
# and _1 against wire_canl_1..6. So the floor is the CABLE, and the tee PCBs are merely
# what the cable is above. Recovering those 2.5 mm is a harness job, and it is worth
# 0.74 -> 0.78 of uniformity if anyone does it.
TEE_TOP   = -19.65                 # highest STRUCTURE under the fret field
# ⚠ ...AND THE CABLE IS DRAWN WRONG (user, 2026-09-29): "the plugs are the real floor".
# Measured -- the tee board's own top face is -26.65, its side-entry XH plus a MATED plug
# is XH_SIDE_H 7.00 on top of that, so the real envelope ends at -19.65. wire_canl runs to
# -17.15, TWO AND A HALF MILLIMETRES ABOVE ITS OWN PLUG, because src/wiring.py stacks the
# trunk's four conductors in Z (its old TRUNK_DZ: gnd -0.8, hot 1.2, canh 3.2, canl 5.2) and canl
# is the top one. So this floor is an artefact, not a part.
# Holding to it anyway costs 1.5 mm of depth and takes the line 1.21 -> 1.28 : 1. Inverting
# that stack is a wiring.py change on a shared trunk, so it is FLAGGED, not taken.
# HISTORY ONLY: wiring.py was corrected 2026-10-01 (bronner b5d3efff -- TRUNK_Z_RUN /
# TRUNK_Z_OVER, highest conductor top -20.68, under the plugs). Nothing is set from this.
CABLE_TOP = -17.15                 # where the cable WAS drawn
# ⚠ THE PLUGS ARE THE FLOOR, AND THE BOARD IS SET FROM THEM (user, 2026-10-01: "the
# wiring isn't modeled accurately, the plugs on the boards are the actual +z extents").
# Re-probed against everything but the wire models (tools/_probe_fret_tab.py --no-wires):
# the only real thing under any board edge is the mated plugs of tee boards 6 and 7 under
# mid's -Y edge, at TEE_TOP. So the stack below the board is, from the plugs up:
#     SLIDE_OVER    1.50   the panel SLIDES over the plugs, so this is a sliding clearance
#                          (user: no "super narrow clearance there")
#     D.MIN_WALL    0.80   the edge wall's floor under the retainer strip's groove
#     STRIP_T_MAX   1.60   the strip itself -- user: "1.6 min"
# and the board's underside sits on the strip. That is 0.40 ABOVE where the drawn cable
# had put it, which costs the cells 0.40 of depth and gives mid its fourth strip.
SLIDE_OVER = 1.50
STRIP_T_MAX = D.MIN_WALL_2P        # 1.60: the retainer strip's thickness, every edge
BOARD_BOT = TEE_TOP + SLIDE_OVER + D.MIN_WALL + STRIP_T_MAX   # -15.75
BOARD_T   = 1.60
BOARD_TOP = BOARD_BOT + BOARD_T    # -14.55
# ⚠ 1.60, NOT THE 1.40 THIS LINE CARRIED. Read off the part's own listing while the
# PCB was being designed (LCSC C7371891): "Dimensions (L/W/H): 5.0x5.0x1.6mm", and the
# footprint elec/footprints/Steel.pretty/XINGLIGHT_XL-5050RGBW.kicad_mod has said 1.6
# in its description since bronner drew it. The same listing settles the other open
# question about this part -- "Installation method: Top-mount", 120 degrees -- which is
# what a cell needs and which docs/fret-led.md section 5.3 had recorded backwards.
# It costs 0.20 mm of depth: 17.95 -> 17.75, and the line goes 1.136 -> 1.143 : 1.
LED_H     = 1.60                   # XL-5050RGBW body top = its emitting face
LED_Z     = BOARD_TOP + LED_H      # -12.95
DEPTH_NOM = APERTURE_Z_NOM - LED_Z  # 17.75, the h the optics are solved at

# ── where the FOUR LEDs go along the fret ─────────────────────────────────────────────
# ⚠ FOUR, NOT THREE, AND IT IS THE CHEAP WAY OUT OF THE DEPTH PROBLEM. Three LEDs want
# h = 20.80 to reach 1.21 : 1, and the CAN trunk as drawn caps h at 17.95, where three
# give only 1.38 : 1. A fourth LED gives 1.14 : 1 AT THE CAPPED DEPTH -- better than three
# would manage even if the harness moved. Weighed against each other:
#
#     3 LEDs, harness moves 2.5 mm     1.28 : 1   a change to a SHARED trunk whose
#                                                 stacking order was chosen for reasons
#                                                 this work has not read
#     4 LEDs, harness untouched        1.14 : 1   +24 LEDs = $1.56, NO extra driver
#                                                 (they series on the same channel)
#
# The fourth LED is better and cheaper and touches nobody else's work. Positions solved
# numerically on the bead grid; note they are NOT evenly spaced -- the outer pair sits
# near the ends because the end reflectors do the work out there.
# ⚠ IT MOVES THE RAIL: four in series is 12.8 V for W/G/B, so the rail goes 12 -> 14 V.
# Still inside the TLC59711's 17 V (see docs/fret-led.md 6.5).
LED_Y_IN  = 13 * D.BEAD            # 10.40
LED_Y_OUT = 38 * D.BEAD            # 30.40
LED_YS    = (-LED_Y_OUT, -LED_Y_IN, LED_Y_IN, LED_Y_OUT)
END_REFL = 0.85                    # printed white PCTG, diffuse

# ── the cell's walls ──────────────────────────────────────────────────────────────────
# ⚠ ONE WALL BETWEEN TWO FRETS, NOT TWO. An earlier note of mine in docs/fret-led.md
# budgeted two walls per gap and concluded the tightest pair left 0.38 mm of air. Wrong:
# cell n's +X wall IS cell n+1's -X wall. At the 9.14 pitch a single 2-bead wall leaves
# 1.44 of air against the LED courtyards.
WALL      = D.MIN_WALL_2P          # 1.60 between neighbouring cells
WALL_MIN  = D.MIN_WALL             # 0.80, the 1-bead floor if a pitch ever demands it
LED_CRTYD = 6.10                   # XINGLIGHT_XL-5050RGBW F.CrtYd, read off the footprint

# The tunnel tapers from the LED's width at the board to the aperture at the deck: narrow
# at the top, wide at the bottom. In THIS part's print direction (top_plate PIECE_UP = -Z,
# deck face on the bed) that starts narrow at the bed and leans outward as it builds —
# 9 degrees off vertical at the tightest fret, 25 at the widest, both inside 45.
TAPER_MAX_DEG = 45.0

# ── the outboard ends ─────────────────────────────────────────────────────────────────
# ⚠ 31.20 HALF-WIDTH, NOT 30.00, and an import-time assert is why: at 30.00 the outer
# LEDs' courtyards overhang the board by 0.25, caught the first time this module loaded.
# Width is the expensive axis (docs/fret-led.md section 1: ~13x more per mm than length),
# but 2.4 mm of it is a rounding error against holding the optimum LED spacing.
BOARD_HALF_W = 44 * D.BEAD         # 35.20 -> a 70.4 wide board. The outer LED's BODY
                                   # reaches 32.90, so a retaining tab on the ramp has
                                   # 2.30 of reach over the board's edge without touching
                                   # it -- see docs/fret-led.md section 8.
# The fret line runs to +-39.8, so the last ~8.6 mm of each cell has no board under it.
# Rather than widen the board to 84, the deck RAMPS ITS OWN FLOOR up from the board's edge
# to the aperture. The ramp closes the cell AND is the end reflector the optics want, and
# at 58 degrees from horizontal it self-supports in this print direction.
RAMP_DEG = 58.0

# ── the -Z retention ────────────────────────────────────────────────────
# Five of the six directions come free (docs/fret-led.md 8.3): the comb's end walls take
# +-X, the ramps and the edge walls take +-Y, and the cell walls' undersides take +Z at 23
# places along the length. -Z is gravity's direction and this is it.
#
# ⚠ RETAINER STRIPS, NOT TABS, AND THE CELL PITCH IS WHY. Section 8.4's lift-and-shift
# was retracted on measurement (docs/fret-led.md 8.6): an LED and a cell wall share
# z BOARD_TOP..BOARD_TOP+LED_H, so ANY X motion of a seated board drives every LED into a
# wall. Fret 24's cell leaves its LED 1.27 mm, and a tab must travel its own length --
# 8.50 -- to leave its notch. The scheme could never have been engaged on the mid board.
#
# A STRIP MOVES INSTEAD OF THE BOARD, and that dissolves it. The comb lives ABOVE
# BOARD_TOP and the board's underside is bare, every part being on its top face, so a strip
# sliding along X BELOW the board meets no wall and no LED. The panel is assembled face
# down: drop the board into the comb, gravity holds it against the cell walls, slide a
# strip in along each long edge to trap it. The board never moves.
#
# ⚠ AND IT DELETES THE NOTCHES. The board is a plain rectangle again -- a tab needed a
# notch through the edge and a notch removes substrate, so it was bounded by the outer
# LED's courtyard; a strip runs under a bare underside and may lap as far as it likes.
#
# ONE SCREW IS NOT ENOUGH, which is where 8.3 was right even though 8.4 was not: the M4
# sits 4.50 from the -X end, so the board cantilevers 206 mm, and at EI = 576,000 N.mm2
# with ~35 g that is **0.64 mm** of sag at the far end -- the board hanging off the cell
# walls there and leaking light between cells, which is what the comb exists to stop.
STRIP_OVER = 2.30                  # how far a strip laps OVER the board's underside
STRIP_CLR  = 0.20                  # sliding fit in the groove
STRIP_FLOOR_CLR = SLIDE_OVER       # the edge wall's underside to whatever it slides over
TAB_PLAY   = 0.30                  # board edge to the edge wall's inner face
# ⚠ THE ROOM UNDER EACH EDGE, MEASURED AGAINST REAL PARTS ONLY. The first table here was
# probed with the wire models in and read 1.00 under mid's -Y edge (wire_canl_6/7 at
# -17.15) and 5.30 under key's (motor pigtails) -- both artefacts of src/wiring.py, which
# draws the trunk 2.5 above its own plugs. tools/_probe_fret_tab.py --no-wires, 2026-10-01:
#     mid -Y           tee_pcb_6 / tee_pcb_7 mated plugs, top TEE_TOP
#     the other three  clear for the full 6.00 probed
# Mid's -Y room is therefore the Z stack's own sum, and all four edges carry a full strip.
STRIP_ROOM = {("mid", -1.0): BOARD_BOT - TEE_TOP, ("mid", 1.0): 6.00,
              ("key", -1.0): 6.00, ("key", 1.0): 6.00}
#
# ⚠ BOTH EDGES, BECAUSE A STRIP IS A HINGE AND NOT A CLAMP. This said one full-length
# strip was enough, on a cantilever-stiffness argument (15 um of droop). That treated the
# strip as built-in. It laps 2.30 with clearance in its groove, so a board held along ONE
# edge can rotate about it; what held mid's free edge was the M4 at one end and the board's
# own torsion over 206 mm, roughly 0.2 - 0.3 mm at the far corner. Two strips make it a
# plate supported on both long edges, which is what the cells need to stay light-tight.


def strip_room(panel, sgn):
    return STRIP_ROOM[(panel, sgn)]


def strip_t(panel, sgn):
    """How thick this edge's strip may be -- it and its groove floor must both fit."""
    return min(STRIP_T_MAX,
               strip_room(panel, sgn) - STRIP_FLOOR_CLR - D.MIN_WALL)


def has_strip(panel, sgn):
    """Is there room under this edge for a strip AND the floor that holds it up?"""
    return strip_t(panel, sgn) >= D.MIN_WALL - 1e-9


def strip_z(panel, sgn):
    """(top, bottom) of the strip: its top face carries the board's underside."""
    return BOARD_BOT, BOARD_BOT - strip_t(panel, sgn)


def wall_floor(panel, sgn):
    """How deep this edge's wall may hang -- NEVER past what was measured under it.

    ⚠ THIS IS WHAT TURNED THE GATE RED. The wall used to hang a full WALL below the
    strip regardless of side, which put mid's -Y wall at -18.55 against a CAN conductor at
    -17.15 and showed up as `top_plate_color_3 <-> wire_canl_7`, 4.4 mm3. A depth is a
    clearance question and it has to be asked of the measurement, not of a constant."""
    floor = BOARD_BOT - strip_room(panel, sgn) + STRIP_FLOOR_CLR
    if not has_strip(panel, sgn):
        return max(floor, BOARD_BOT - D.MIN_WALL)
    return max(floor, strip_z(panel, sgn)[1] - D.MIN_WALL)


def strip_y(sgn):
    """(inner, outer) Y of the strip on this edge; inner is how far it laps the board."""
    wall = sgn * (BOARD_HALF_W + TAB_PLAY)
    return wall - sgn * STRIP_OVER, wall + sgn * STRIP_GRIP


STRIP_GRIP = 1.60                  # how far the strip sits INTO the edge wall's groove
# the one M4's Y per board -- elec/fret_led.py cuts the hole there, reading THIS.
# ⚠ BOTH AT -28. Mid's went to -30 for a day to keep its head out of wire_canl_5 -- which
# is the wire MODEL, not a wire (see the Z stack). At -30 the O7.6 head would now sit
# 0.6 into mid's new -Y strip (inner edge y -33.20); at -28 it clears it by 1.40.
M4_Y       = {"mid": -28.00, "key": -28.00}
M4_LEN     = 10.0                  # M4x10 button head, the instrument's standard
M4_HEAD_CLR = 0.0                  # head sits on the board's underside
DECK_UNDER = 0.0                   # the deck's own underside: above it is material the
                                   # colour layer takes, below it is structure hanging free


def depth() -> float:
    """The live h: the real aperture underside over the LED's emitting face."""
    return aperture_z() - LED_Z


def tunnel_width(pitch: float, wall: float = WALL) -> float:
    """Inner X width of a cell whose neighbour is `pitch` away, sharing one `wall`."""
    return pitch - wall


def wall_for(pitch: float) -> float:
    """The wall thickness a given fret pitch can afford — two beads wherever it fits.

    Generative rather than constant because the pitch runs 9.14 (frets 24-23) to 32.58
    (2-1): one figure is either wasteful at the nut end or impossible at the bridge."""
    if tunnel_width(pitch, WALL) >= LED_CRTYD:
        return WALL
    if tunnel_width(pitch, WALL_MIN) >= LED_CRTYD:
        return WALL_MIN
    raise ValueError("fret pitch %.2f cannot hold a %.2f courtyard even at a 1-bead wall"
                     % (pitch, LED_CRTYD))


def taper_deg(pitch: float) -> float:
    """How far off vertical a cell's wall leans, taking the tunnel down to the aperture."""
    import math
    half = (tunnel_width(pitch, wall_for(pitch)) - aperture()) / 2.0
    return math.degrees(math.atan(half / depth()))


def uniformity(leds=LED_YS, h=None, refl=END_REFL, n=321, orders=4, hy=None):
    """(min/max, profile) of illuminance along the fret line.

    Lambertian sources at depth `h`, end reflectors at +-half_len() by the method of
    images. This is the model that picked LED_Y and the Z stack; it lives here so those
    numbers cannot drift away from the geometry chosen for them."""
    h = depth() if h is None else h
    hy = half_len() if hy is None else hy
    srcs = [(s, 1.0) for s in leds]
    for k in range(1, orders + 1):
        w = refl ** k
        for s in leds:
            srcs.append((2 * hy * k - s if k % 2 else 2 * hy * k + s, w))
            srcs.append((-2 * hy * k - s if k % 2 else -2 * hy * k + s, w))
    ys = [-hy + 2 * hy * i / (n - 1) for i in range(n)]
    e = [sum(w * (h * h / (h * h + (y - s) ** 2)) ** 2 for s, w in srcs) for y in ys]
    return min(e) / max(e), list(zip(ys, e))


def check_optics(pitches=()):
    """The optical design, checked against the DECK's own datums.

    Not run at import, for the same reason ui_panel.check_posts() is not: reaching into
    top_plate from here at import time IS the cycle. A checker calls this once everything
    is loaded. Pass the real fret pitches and the wall/taper budget is checked too."""
    u, _ = uniformity()
    assert u >= 0.85, (
        "the fret line is %.2f : 1 end to end, past the 1.18 : 1 this geometry was solved "
        "for — LED_Y, the Z stack or top_plate.FRET_HY has moved" % (1.0 / u))
    u0, _ = uniformity(refl=0.0)
    assert u0 < u, "the end reflectors are supposed to help; check RAMP_DEG"
    assert abs(half_len() - HALF_LEN_NOM) < 0.5, (
        "the fret line is %.2f half-long against the %.2f the Z stack and LED_Y were "
        "solved for — re-solve them" % (half_len(), HALF_LEN_NOM))
    for p in pitches:
        assert taper_deg(p) <= TAPER_MAX_DEG, (
            "a cell on a %.2f pitch leans %.1f degrees off vertical, past %.0f"
            % (p, taper_deg(p), TAPER_MAX_DEG))
    return u


# these need no deck datum, so they run at import
assert BOARD_BOT - TEE_TOP >= 1.5, (
    "the LED board at %.2f leaves only %.2f over the tee PCBs at %.2f, and the panel has "
    "to SLIDE over them" % (BOARD_BOT, BOARD_BOT - TEE_TOP, TEE_TOP))
assert STRIP_OVER >= D.MIN_WALL, (
    "a %.2f strip lap against a %.2f bead" % (STRIP_OVER, D.MIN_WALL))
_PANELS = sorted({_k[0] for _k in STRIP_ROOM})
assert any(has_strip(_p, _s) for _p in _PANELS for _s in (-1.0, 1.0)), (
    "no edge on either panel has room for a retainer strip")
for _p in _PANELS:
    for _s in (-1.0, 1.0):
        assert has_strip(_p, _s) and strip_t(_p, _s) >= D.MIN_WALL_2P - 1e-9, (
            "%s %+.0fY: the retainer strip is %.2f, and 1.60 is the minimum (user)"
            % (_p, _s, strip_t(_p, _s)))
        assert wall_floor(_p, _s) - (BOARD_BOT - strip_room(_p, _s)) >= SLIDE_OVER - 1e-9, (
            "%s %+.0fY: the edge wall slides %.2f over what is under it"
            % (_p, _s, wall_floor(_p, _s) - (BOARD_BOT - strip_room(_p, _s))))
assert LED_Y_OUT + LED_CRTYD / 2.0 <= BOARD_HALF_W, (
    "the outer LEDs at +-%.2f plus a %.2f courtyard overhang a %.2f-half-width board"
    % (LED_Y_OUT, LED_CRTYD, BOARD_HALF_W))
assert LED_Y_OUT - LED_Y_IN >= LED_CRTYD, (
    "the two LED rows at %.2f and %.2f are closer than a %.2f courtyard"
    % (LED_Y_IN, LED_Y_OUT, LED_CRTYD))


# ── THE CAD ───────────────────────────────────────────────────────────────────────────
# The cell is a COMB, which is the simplest thing it can be: one wall plate on each fret
# boundary, closed at the Y ends by ramps. Everything here is authored in WORLD coordinates
# (the deck's own frame) because that is where top_plate works and where it has to land.
import cadquery as cq                                            # noqa: E402

from .helpers import box_at, heal                                # noqa: E402


# ⚠ FRET 1 GETS NO CELL, and the gate is what said so. Its cell would sit at x -580.5
# with an outer wall reaching about -596.8, straight through the keyhead cluster: the Pi
# (top -6.00), wire_ui (-8.27), wire_link (-11.30) and wire_usb (-13.70) all live there,
# and a cell floor at -14.55 goes through all four. This is the same finding recorded in
# docs/fret-led.md as "fret 1 has 8.27 mm, not 17" -- now measured rather than predicted.
# Fret 2 at -547.90 is clear of the whole cluster, so the comb starts there.
SKIP_FRETS = (1,)


def fret_xs():
    """[(n, x)] the marked frets that get a cell, bridge end first — off top_plate."""
    TP = _tp()
    fr = [(n, x) for n, x in TP._fret_positions(-100.0, -620.0)
          if n <= 24 and n not in SKIP_FRETS]
    return sorted(fr, key=lambda t: -t[1])


def _boundaries(xs, x_lo=None, x_hi=None):
    """The X of every wall: half way between neighbours, and half a cell past each end.

    HALF a cell, not a whole one, and clamped into the panel if one is given — a comb that
    runs a full pitch past its last fret sticks out over whatever is beyond the panel, which
    at the keyhead end is the Pi."""
    # ⚠ AND NOT CLOSER THAN THE END LED'S OWN COURTYARD. Half a cell past fret 24 is
    # only 2.29 mm, and the wall then lands on the LED -- the gate caught it as
    # fret_led_0 <-> top_plate_color_3, 21.3 mm3. The end wall has to clear the outermost
    # LED's courtyard plus its own half-thickness.
    # ⚠ AND A CLAMPED WALL IS INSET BY HALF ITS OWN THICKNESS, or it hangs OUTSIDE the
    # panel. `min(lo, x_hi)` put the wall's CENTRE on the panel edge, so 0.80 of it
    # stood in the seam gap -- measured at -360.40 against the keyhead panel's edge of
    # -361.15. It collided with nothing (the mid panel has no structure under its own
    # last 11 mm) so the overlap gate never saw it, and it cost the mid board 0.80 mm
    # of its power bay, which is where the harness connector has to fit.
    end_min = LED_CRTYD / 2.0 + WALL / 2.0 + 0.2
    mids = [(xs[i] + xs[i + 1]) / 2.0 for i in range(len(xs) - 1)]
    lo = xs[0] + max((xs[0] - mids[0]) / 2.0, end_min)
    hi = xs[-1] - max((mids[-1] - xs[-1]) / 2.0, end_min)
    if x_hi is not None:
        lo = min(lo, x_hi - WALL / 2.0)
    if x_lo is not None:
        hi = max(hi, x_lo + WALL / 2.0)
    return [lo] + mids + [hi]


_optics_checked = False


def _check_optics_once():
    """Run check_optics() the first time a comb is built, on the real fret pitches.

    ⚠ A CHECKER NOTHING CALLS IS A CHECKER THAT DOES NOT RUN, and this one proved it:
    `check_optics` was written to be "called once everything is loaded" and nothing ever
    called it, so a commit shipped with the fret line at 1.39 : 1 against its own 1.18
    threshold and the repository said nothing. The deck cannot call it at import (that IS
    the cycle this module's late import exists to break), but by the time a comb is being
    BUILT top_plate's datums are all set -- which is why walls() can already read
    half_len(). So the check rides the build, and there is no separate tool to forget.
    """
    global _optics_checked
    if _optics_checked:
        return
    _optics_checked = True
    xs = [x for _n, x in fret_xs()]
    check_optics([abs(xs[i + 1] - xs[i]) for i in range(len(xs) - 1)])


def walls(x_lo=None, x_hi=None):
    """The comb: one opaque plate per fret boundary, board top up to the inlay's underside.

    ⚠ It reaches APERTURE_Z, not the deck's underside, because the deck's base is
    transparent and continuous — see the module docstring. Above z = 0 this is material
    the deck gives up to the colour layer; below it is new structure hanging free."""
    _check_optics_once()
    xs = [x for _n, x in fret_xs() if (x_lo is None or x_lo <= x <= x_hi)]
    if not xs:
        return cq.Workplane("XY")
    hy, top, bot = half_len(), aperture_z(), BOARD_TOP
    out = None
    for bx in _boundaries(xs, x_lo, x_hi):
        w = box_at(WALL, 2 * hy, top - bot, x=bx, y=0.0, z=(top + bot) / 2.0)
        out = w if out is None else out.union(w)
    return heal(out)


def ramps(x_lo=None, x_hi=None):
    """The outboard end closures: a wedge each side, board edge up to the deck underside.

    Closes the part of each cell the board does not reach (the board is 62.4 wide, the
    fret line 79.6), self-supports in the deck's print direction, and IS the end reflector
    the optics are solved with."""
    xs = [x for _n, x in fret_xs() if (x_lo is None or x_lo <= x <= x_hi)]
    if not xs:
        return cq.Workplane("XY")
    bnd = _boundaries(xs, x_lo, x_hi)
    x0, x1 = min(bnd), max(bnd)
    hy, y0, z0 = half_len(), BOARD_HALF_W, BOARD_TOP
    out = None
    for sgn in (-1.0, 1.0):
        # triangle in the YZ plane, extruded along X across the whole comb
        pts = [(sgn * y0, z0), (sgn * hy, z0), (sgn * hy, 0.0)]
        w = (cq.Workplane("YZ").polyline(pts).close()
             .extrude(x1 - x0).translate((x0, 0, 0)))
        out = w if out is None else out.union(w)
    return heal(out)


def edge_walls(x_lo=None, x_hi=None):
    """The wall each long edge of the board runs against, grooved for its retainer strip.

    ⚠ SECTION 8.3 SAYS THE RAMPS HOLD +-Y AND THEY VERY NEARLY DO NOT. A ramp is a
    triangle from (BOARD_HALF_W, BOARD_TOP) out to the deck, so at the board's edge it is a
    KNIFE EDGE: it meets the board's top corner and has nothing beside the board's 1.60 mm
    of thickness, nor any material to carry a retainer. This drops a real face past it,
    TAB_PLAY outboard, which is what the board bears against in Y.

    It costs nothing to print: it hangs from the ramp's flat underside at BOARD_TOP, in the
    deck's own print direction."""
    out = None
    for panel in BOARD_NAME:
        bx0, bx1 = board_span(panel)
        if x_lo is not None and not (x_lo <= (bx0 + bx1) / 2.0 <= x_hi):
            continue
        for sgn in (-1.0, 1.0):
            floor = wall_floor(panel, sgn)
            y0 = sgn * (BOARD_HALF_W + TAB_PLAY)
            y1 = y0 + sgn * (STRIP_GRIP + WALL)
            w = box_at(bx1 - bx0, abs(y1 - y0), BOARD_TOP - floor,
                       x=(bx0 + bx1) / 2.0, y=(y0 + y1) / 2.0,
                       z=(BOARD_TOP + floor) / 2.0)
            out = w if out is None else out.union(w)
    return heal(out) if out is not None else cq.Workplane("XY")


def strip_groove(x_lo=None, x_hi=None):
    """The slot the retainer strip slides along -- CUT from the edge wall.

    Runs the board's whole length and is open at both ends, because the strip goes in along
    X and nothing keys it to a position."""
    out = None
    for panel in BOARD_NAME:
        bx0, bx1 = board_span(panel)
        if x_lo is not None and not (x_lo <= (bx0 + bx1) / 2.0 <= x_hi):
            continue
        for sgn in (-1.0, 1.0):
            if not has_strip(panel, sgn):
                continue
            top, bot = strip_z(panel, sgn)
            yi, yo = strip_y(sgn)
            c = box_at(bx1 - bx0, abs(yo - yi) + STRIP_CLR,
                       strip_t(panel, sgn) + STRIP_CLR,
                       x=(bx0 + bx1) / 2.0,
                       y=(yi + yo) / 2.0 + sgn * STRIP_CLR / 2.0,
                       z=(top + bot) / 2.0)
            out = c if out is None else out.union(c)
    return heal(out) if out is not None else cq.Workplane("XY")


def strips():
    """[(name, solid)] -- the retainer strips, two per panel.

    A plain bar: it prints lying down, has no orientation to get wrong, and its X is free
    in the groove. The neighbouring panels close both ends once the deck is stacked."""
    out = []
    for panel in BOARD_NAME:
        bx0, bx1 = board_span(panel)
        for sgn, tag in ((-1.0, "ny"), (1.0, "py")):
            if not has_strip(panel, sgn):
                continue
            top, bot = strip_z(panel, sgn)
            yi, yo = strip_y(sgn)
            out.append(("fret_strip_%s_%s" % (panel, tag),
                        box_at(bx1 - bx0, abs(yo - yi), strip_t(panel, sgn),
                               x=(bx0 + bx1) / 2.0, y=(yi + yo) / 2.0,
                               z=(top + bot) / 2.0)))
    return out


def m4_xy(panel):
    """World (x, y) of this board's one M4, from where elec/ cut the hole.

    ⚠ NOT RETYPED. elec/fret_led.py cuts it at board-local (x0 - cx + 4.50, -28.0) and
    `_placed` translates board-local x by the board centre, so the world X is x0 + 4.50 --
    4.50 in from the board's -X end, inside the BAY, where there is no cell to shadow."""
    return board_span(panel)[0] + 4.50, M4_Y[panel]


def m4_boss(w, x_lo=None, x_hi=None):
    """Union this panel's M4 boss into the deck/comb solid `w`, and return it.

    A post from the deck's underside down to the board's top face, with the melt-fit
    pocket bored UP from its bottom. The screw comes from BELOW, through the board, so the
    pocket's mouth is the boss's lowest face -- which is also the LAST face printed in the
    deck's own direction (top_plate.PIECE_UP = -Z), so it needs no support and no bridging.

    ⚠ THE BOSS IS FINISHED BEFORE IT MEETS THE COMB, AND THAT IS A BUILD-TIME FIX, NOT
    A STYLE ONE. Cutting the pocket and the clearance bore out of the comb costs three
    booleans against a 23-wall solid per panel, and it took the deck's build from about
    4 minutes to over 20 -- enough to trip tools/build_profile.py on its own. Done on the
    bare post first, the same three booleans are against a single cylinder and the comb
    sees ONE union.

    ⚠ THE POST IS LONGER THAN THE HELPER'S OWN BOSS. cut_m4_boss builds M4.boss_prot
    (6.00) back from `pt`, and the board's top face is 14.55 below the deck's underside, so
    the post is drawn here and the helper is handed a point inside it. Without that the
    boss would float."""
    from cadkit.fasteners import cut_m4_boss, M4
    for panel in BOARD_NAME:
        bx0, bx1 = board_span(panel)
        if x_lo is not None and not (x_lo <= (bx0 + bx1) / 2.0 <= x_hi):
            continue
        x, y = m4_xy(panel)
        boss = (cq.Workplane("XY").circle(M4.boss_od / 2.0)
                .extrude(DECK_UNDER - BOARD_TOP).translate((x, y, BOARD_TOP)))
        boss = cut_m4_boss(boss, (x, y, BOARD_TOP + M4.boss_prot), (1, 0, 0), 0.0)
        w = w.union(boss)
    return w


def m4_screws():
    """[(name, solid)] -- the dummy screws, for the assembly only.

    ⚠ THE HEAD WAS INSIDE THE BOARD UNTIL THIS WAS FIRST WIRED INTO THE BUILD. The helper
    puts the head's TOP face at z = 0 (shank -Z), so after the flip the head stood UP from
    BOARD_BOT through the laminate: 47.2 mm3 into each board, and the tip 2.2 too deep in
    the deck. The function was never called, so nothing had intersected it. The head's top
    goes one head height BELOW the board, which puts the under-head face on its underside."""
    from cadkit.fasteners import m4_button_screw, M4_BUTTON_HEAD_H
    out = []
    for panel in BOARD_NAME:
        x, y = m4_xy(panel)
        out.append(("fret_m4_%s" % panel,
                    m4_button_screw(M4_LEN).rotate((0, 0, 0), (1, 0, 0), 180.0)
                    .translate((x, y, BOARD_BOT - M4_HEAD_CLR - M4_BUTTON_HEAD_H))))
    return out


def columns(x_lo=None, x_hi=None):
    """The clear volume under each fret line, z 0 .. APERTURE_Z.

    Kept for measurement and for the viewer; it is NOT a material boundary any more (see
    the docstring). The base is transparent throughout and the comb is what isolates."""
    hy, ap = half_len(), aperture()
    out = None
    for _n, x in fret_xs():
        if x_lo is not None and not (x_lo <= x <= x_hi):
            continue
        c = box_at(ap, 2 * hy, aperture_z() - 0.0, x=x, y=0.0, z=aperture_z() / 2.0)
        out = c if out is None else out.union(c)
    return heal(out)


# ── THE BOARDS ────────────────────────────────────────────────────────────────────────
# One PCB per panel, designed in elec/fret_led.py, which imports THIS module for every
# fret X, the four LED Y positions, the board width and the Z stack. The span is here
# rather than there because it is geometry -- where a board may reach is a fact about
# the deck and the harness, and the CAD has to place the board without reading elec/.
#
# THE BAY is the run at each board's -X end that lies OUTSIDE the light cells: the
# 24 V harness plug, the buck and its inductor go there, because a part standing inside
# a cell is a dark patch on that cell's floor. Both ends were MEASURED, not chosen:
#   mid   the mid comb's end wall is at -350.00 and the panel runs to -361.15, so the
#         bay is the panel's own last 11 mm. It stops at -360.50, which leaves 0.65 to
#         the keyhead panel's edge -- the two boards are coplanar and the keyhead comb's
#         last wall stands right at that edge, so this is a face-to-face clearance.
#         ⚠ IT WAS -359.50 UNTIL THE CONNECTOR WOULD NOT FIT. The 6-way PH's courtyard
#         reaches 11.91 back from the board edge and fret 10's outer LED begins 12.29
#         in, which is 0.38 of clearance and was -0.62 before `_boundaries` stopped
#         hanging a clamped wall half outside its panel. The checker in elec/fret_led.py
#         is what found it, before the board was routed rather than after.
#   key   the keyhead comb's end wall is at -555.59 and the panel runs to -610.80, so
#         there is 55 mm of room. It stops at -573.00 because `wire_usb` crosses at
#         z -14.55..-13.70 from -580.00 -X, and the board's top face IS -14.55.
BOARD_BAY = {"mid": -360.50, "key": -573.00}
BOARD_NAME = {"mid": "fret_led_mid", "key": "fret_led_key"}


def panel_range(panel):
    """(x_lo, x_hi) of the deck panel a board serves."""
    TP = _tp()
    return (TP.MID_X1, TP.MID_X0) if panel == "mid" else (TP.KEY_X1, TP.KEY_X0)


def board_span(panel):
    """(x0, x1) of the PCB in world X: its comb's boundaries, plus the bay at the -X end."""
    lo, hi = panel_range(panel)
    xs = [x for _n, x in fret_xs() if lo <= x <= hi]
    bnd = _boundaries(xs, lo, hi)
    return min(BOARD_BAY[panel], min(bnd)), max(bnd)


def board_cx(panel):
    """The board frame's origin in world X (elec/ works board-centred)."""
    x0, x1 = board_span(panel)
    return (x0 + x1) / 2.0


def _led_refs(panel):
    from . import board_geom as BG
    return [f["ref"] for f in BG.load(BOARD_NAME[panel])["footprints"]
            if f["ref"].startswith("D")]


def _placed(panel, wp):
    return wp.translate((board_cx(panel), 0.0, BOARD_BOT))


def pcb(panel):
    """The PCB and every part on it EXCEPT the LEDs, as routed.

    ⚠ READ BACK FROM THE ROUTED BOARD (src/board_geom.py), not drawn from a table. The
    slab this used to be was 70.4 x 200 x 1.6 with four boxes per fret on top, and it
    agreed with nothing but itself: it had no drivers, no buck, no inductor, no harness
    plug and no mounting hole, which are exactly the parts that decide whether this
    thing fits under the deck. The same argument board_geom's own docstring makes about
    the output board, and the same three classes of error waiting in it."""
    from . import board_geom as BG
    return _placed(panel, BG.solid(BOARD_NAME[panel], skip=_led_refs(panel)))


def leds(panel):
    """The panel's LEDs, as their routed bodies -- their own part so they read as lit."""
    from . import board_geom as BG
    return _placed(panel, BG.bodies(BOARD_NAME[panel], _led_refs(panel)))


def parts(panel):
    """[(name, solid)] for build.py, so the idea renders in the viewer."""
    lo, hi = panel_range(panel)
    return [("fret_cell_%s" % panel, walls(lo, hi).union(ramps(lo, hi))),
            ("fret_pcb_%s" % panel, pcb(panel)),
            ("fret_led_%s" % panel, leds(panel))]


# ── THE SEAM JOINT ────────────────────────────────────────────────────────────────────
# docs/fret-led.md 9.1f. The two boards meet across the deck-panel seam TIP TO TIP: six
# side-mount pogos on each, on one axis, 1.90 above each board's top face -- the boards
# are coplanar, so both axes are at the same height by construction. The keyhead board
# carries the harness plug and the buck; the seam carries +14V, GND and the TLC59711
# chain from key's last driver into mid's first.
#
# Xinyangze YZF0002-38080-02 (LCSC C5203987), off LCSC's own EasyEDA footprint
# CONN-SMD_YZF0002-38080-02 and the maker's drawing, both read 2026-09-30. Everything
# is measured from the PAD CENTRE, because that is where elec/ places the part:
#     pad         5.00 (along the axis) x 3.50
#     barrel      4.50 x 3.00 x 3.80, centred on the pad: rear face 2.25 BEHIND the
#                 centre, front face 2.25 AHEAD of it
#     plunger     O2.00, 3.50 proud of the barrel at free length (8.00 rear-to-tip),
#                 bottoms at 5.70, rated 200 gf at 6.00
POGO_MPN = "YZF0002-38080-02"
POGO_PAD_L, POGO_PAD_W = 5.00, 3.50
POGO_BODY_L, POGO_BODY_W, POGO_BODY_H = 4.50, 3.00, 3.80
POGO_AXIS_H = 1.90
POGO_PLUNGER_D = 2.00
# ⚠ THE BARREL AS BUILT IS 4.60, NOT 4.50. board_geom extrudes a part's F.Fab to KiCad's
# bounding box, which includes the outline's 0.10 stroke -- 0.05 proud all round. The
# plungers start at THAT face, or each one sits 0.05 inside its own barrel and the gate
# reads 0.94 mm3 per board (tools/_probe_seam.py found it). Geometry of the pogo itself
# (setbacks, working height) still uses the drawing's 4.50.
POGO_FAB_STROKE = 0.10
POGO_FREE, POGO_LIMIT = 8.00, 5.70
# ⚠ 6.30 AT FLUSH, NOT THE CATALOGUE'S 6.00 -- 9.1e. Bottoming is the failure that
# cannot be recovered: a pogo at its 5.70 limit is a brass strut holding the panels
# apart, and no endplate clamping closes that seam. Losing a little force is not.
POGO_WORK = 6.30
POGO_STACK = 0.80          # +- the deck stack at the seam, both panels' ribs and the gap
# key's barrels to key's end wall: elec/fret_led.py's WALL_CLR (0.30), plus 0.05 so its
# strict float test is not decided by rounding when the two are equal
POGO_WALL_CLR = 0.35
POGO_EDGE_MIN = 0.50       # a pad's inboard edge to its board's edge
POGO_NOTCH_CLR = 0.50      # the plunger's lateral float in its notch, each side
POGO_PITCH = 4.50          # 4.00 courtyards with 0.50 between -- and 0.45 to the LEDs
# ⚠ TWO LANES, THREE EACH, AND THE LED ROWS ARE WHAT DECIDE IT. key's pogos stand INSIDE
# fret 9's cell (its seam end is a comb end, not a bay), so they must sit between LED
# rows: 13.90 clear between two courtyards, which takes three 4.00 courtyards and not
# four. The -Y lane is left for the M4 on mid (M4_Y["mid"] = -28.00 is in it).
#     centre lane   +14V GND +14V     power doubled, its return in the middle
#     +Y lane       SCK  GND SDT      each signal beside a ground, loop ~4.5 x 12
POGO_LANES = ((0.0, ("+14V", "GND", "+14V")),
              ((LED_Y_IN + LED_Y_OUT) / 2.0, ("SCK_SEAM", "GND", "SDT_SEAM")))
# (which end of board_span faces the seam, which way is inboard)
_SEAM = {"mid": (0, 1.0), "key": (1, -1.0)}


def pogo_ys():
    """[(y, net)] the six contacts, -Y to +Y -- the same on both boards, tip to tip."""
    out = []
    for yc, nets in POGO_LANES:
        for i, net in enumerate(nets):
            out.append((yc + (i - (len(nets) - 1) / 2.0) * POGO_PITCH, net))
    return sorted(out)


def _key_seam_wall():
    """X of the comb wall at key's seam end -- it straddles the board's +X edge."""
    lo, hi = panel_range("key")
    return max(_boundaries([x for _n, x in fret_xs() if lo <= x <= hi], lo, hi))


def pogo_sep_flush():
    """Board edge to board edge across the seam with the two panels BUTTED (9.1e).

    The two insets, derived: a panel length that moves moves this, and the setbacks
    follow instead of the joint silently leaving preload."""
    return ((board_span("mid")[0] - panel_range("mid")[0])
            + (panel_range("key")[1] - board_span("key")[1]))


def pogo_set():
    """{panel: its pads' centre, inboard of its seam edge}.

    The two must SUM to the tip-to-tip span at POGO_WORK, less the flush separation.
    Key's is the one with a floor that is not the board edge: its barrels stand in fret
    9's cell and must clear the end wall that straddles the edge. Mid takes the rest."""
    reach = POGO_WORK - POGO_BODY_L / 2.0            # pad centre to tip
    total = 2.0 * reach - pogo_sep_flush()
    wall_in = board_span("key")[1] - (_key_seam_wall() - WALL / 2.0)
    key = wall_in + POGO_WALL_CLR + POGO_BODY_L / 2.0
    return {"mid": total - key, "key": key}


def pogo_pads(panel):
    """[(x, y, net)] world pad centres on this board, -Y to +Y."""
    end, inb = _SEAM[panel]
    x = board_span(panel)[end] + inb * pogo_set()[panel]
    return [(x, y, net) for y, net in pogo_ys()]


def pogo_fire(panel):
    """+1 / -1: which way this board's plungers point in world X."""
    return -_SEAM[panel][1]


def _pogo_contact():
    """World X where the tips meet AS MODELLED -- the panels' modelled 0.05 gap included,
    so each pogo sits a hair past POGO_WORK here and at it when the panels butt."""
    return (pogo_pads("mid")[0][0] + pogo_pads("key")[0][0]) / 2.0


def pogo_pins():
    """[(name, solid)] -- the twelve plungers, barrel front to the shared contact.

    The barrels are the boards' own (board_geom reads the pogo's F.Fab); the plungers are
    here because they leave the board and one set crosses key's end wall."""
    z = BOARD_TOP + POGO_AXIS_H
    xc = _pogo_contact()
    out = None
    for panel in BOARD_NAME:
        f = pogo_fire(panel)
        for x, y, _net in pogo_pads(panel):
            x0 = x + f * (POGO_BODY_L + POGO_FAB_STROKE) / 2.0
            c = (cq.Workplane("YZ").circle(POGO_PLUNGER_D / 2.0).extrude(abs(xc - x0))
                 .translate((min(x0, xc), y, z)))
            out = c if out is None else out.union(c)
    return [("fret_pogo_pins", out)]


def pogo_notches(x_lo=None, x_hi=None):
    """The plungers' way through key's end wall -- CUT from the comb.

    Open at the wall's base rather than a round hole: a hole with the plunger's float
    around it would leave 0.40 of wall under it at a 1.90 axis, half a bead. Open, it
    needs nothing below it, and in the deck's -Z print direction its roof is printed
    before the notch starts, so it is not an overhang either. Fret 9 loses six 3.00 x
    3.40 windows into the seam bay, which has no LEDs in it -- a light trap, not
    crosstalk."""
    bx = _key_seam_wall()
    if x_lo is not None and not (x_lo <= bx <= x_hi):
        return cq.Workplane("XY")
    w = POGO_PLUNGER_D + 2.0 * POGO_NOTCH_CLR
    top = POGO_AXIS_H + POGO_PLUNGER_D / 2.0 + POGO_NOTCH_CLR
    out = None
    for y, _net in pogo_ys():
        c = box_at(WALL + 0.4, w, top + 0.2, x=bx, y=y, z=BOARD_TOP + (top - 0.2) / 2.0)
        out = c if out is None else out.union(c)
    return out


_ps = pogo_set()
assert min(_ps.values()) - POGO_PAD_L / 2.0 >= POGO_EDGE_MIN - 1e-9, (
    "a seam pad hangs within %.2f of its board edge: %s" % (POGO_EDGE_MIN, _ps))
assert POGO_WORK - POGO_STACK / 2.0 > POGO_LIMIT, (
    "the seam pogos bottom out at the short end of the stack: %.2f vs %.2f"
    % (POGO_WORK - POGO_STACK / 2.0, POGO_LIMIT))
assert POGO_WORK + POGO_STACK / 2.0 < POGO_FREE, "the seam pogos lose contact"
for _yc, _nets in POGO_LANES:
    _half = (len(_nets) - 1) / 2.0 * POGO_PITCH + POGO_PAD_W / 2.0 + 0.25
    _near = min(abs(_yc - _ly) for _ly in LED_YS)
    assert _near - LED_CRTYD / 2.0 - _half >= 0.30 - 1e-9, (
        "seam lane at y %.2f comes within %.2f of an LED courtyard"
        % (_yc, _near - LED_CRTYD / 2.0 - _half))
assert POGO_PITCH - POGO_PLUNGER_D - 2.0 * POGO_NOTCH_CLR >= D.MIN_WALL, (
    "the wall between two seam notches is under a bead")
