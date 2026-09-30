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
# trunk's four conductors in Z (TRUNK_DZ: gnd -0.8, hot 1.2, canh 3.2, canl 5.2) and canl
# is the top one. So this floor is an artefact, not a part.
# Holding to it anyway costs 1.5 mm of depth and takes the line 1.21 -> 1.28 : 1. Inverting
# that stack is a wiring.py change on a shared trunk, so it is FLAGGED, not taken.
CABLE_TOP = -17.15                 # highest CABLE as DRAWN -- see above
SLIDE_CLR = 1.00
BOARD_BOT = CABLE_TOP + SLIDE_CLR  # -16.15
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

# ── the -Z retention ─────────────────────────────────────────────────────────────
# Five of the six directions come free (docs/fret-led.md section 8.3): the comb's end
# walls take +-X, the ramps take +-Y, and the cell walls' undersides take +Z at 23 places
# along the length. -Z is gravity's direction, it is held NOWHERE, and this is it.
#
# ⚠ THE TABS ARE 45 DEGREE RAMPS, AND IT IS THE SAME SHAPE AS THE FOOT STRIP'S LIPS,
# MIRRORED. `top_plate.PIECE_UP` is (0,0,-1) -- the deck face goes on the bed and the
# underside is built LAST, growing in world -Z -- while the chassis builds world +Z. So a
# tab reaching in over the board's underside is exactly the foot channel's retaining lip
# turned over: its retention face is the overhang, which is why that one became a ramp.
# Each tab rises off the ramp wall at 45 degrees, so every layer lands on the one below
# it, and the clearance over the board's edge is TAB_PLAY rather than a second number.
# docs/fret-led.md section 8.5.3 asked this question and this is the answer to it.
#
# ⚠ AND THE BOARD IS NOTCHED, BECAUSE A STRAIGHT EDGE CANNOT LIFT PAST A TAB. Section
# 8.4's install is lift-then-shift, and a continuous 211 mm edge is already under any tab
# that overhangs it -- there is nothing to lift past. So the board's long edges carry a
# notch at each tab: the board rises with the tabs IN its notches, then shifts SHIFT along
# X and the solid edge between the notches runs under them. The outline goes out as
# `outline_poly` (elec/layout.py _edge_poly, which the motor tee's ear already uses), so
# this costs a polygon in the board module and nothing at the fab.
#
# ⚠ THE REACH IS BOUNDED BY THE LED COURTYARD, NOT BY THE BODY. A notch removes
# substrate, so what it may not reach is the outer LED's KEEPOUT -- LED_Y_OUT + LED_CRTYD/2
# = 33.45 against the board's edge at 35.20. 1.75, not the 2.30 section 8.4 read off the
# body. Both tab and notch are held to it.
# ⚠ IT IS THE NOTCH THAT THE COURTYARD BOUNDS, NOT THE TAB, and the tab is one PLAY
# shorter than it: the tab sits TAB_PLAY outboard of the board's edge, so the slot it has
# to pass through is its own reach plus that play. Sizing the tab at 1.75 puts the notch
# at 2.05 and takes 0.30 out of the outer LED's keepout.
# ⚠ AND THE COURTYARD WANTS A CLEARANCE, NOT A TOUCH. The outer LED sits at every
# fret, so the +Y edge is LINED with courtyards reaching 33.45 -- a notch cut exactly to
# that line leaves the row standing on the lip of a hole for 23 frets. NOTCH_CLR holds it
# off. What is left, 1.05 of tab reach, is what the LED spacing leaves at this board
# width; buying more means buying width, which is ~13x length per mm.
NOTCH_CLR = 0.40
NOTCH_MAX = BOARD_HALF_W - (LED_Y_OUT + LED_CRTYD / 2.0) - NOTCH_CLR   # 1.35
TAB_REACH_MAX = NOTCH_MAX - 0.30                                       # 1.05
TAB_PLAY  = 0.30                   # board edge to the ramp wall -- and, via the 45
                                   # degree face, the clearance under the board's edge
TAB_CLR   = 0.40                   # tab tip to whatever lies below it
TAB_LEN   = 8.00                   # along X, per tab
TAB_SHIFT = 6.00                   # the install shift the M4 then locks
TAB_PITCH = 52.0                   # nominal spacing; the real one divides the span
# ⚠ THE FLOOR UNDER EACH EDGE IS MEASURED, NOT ASSUMED -- tools/_probe_fret_tab.py, run
# 2026-09-30 over both panels' long edges with the boards and the deck taken out:
#     key +Y, mid +Y   clear for the full 6.00 mm probed
#     key -Y           motor pigtails, top -21.45  -> 5.30 free
#     mid -Y           wire_canl_6/7, top -17.15  -> 1.00 free
# A 45 degree tab is DEEPER than a flat one by exactly its own reach, so that 1.00 is what
# decides the -Y side, and it is not enough: see tab_reach() and the assert below.
TAB_FLOOR = {-1.0: CABLE_TOP, 1.0: -22.15}


def tab_reach(sgn):
    """How far a tab on this edge may reach over the board, in mm.

    DERIVED, so that the day the CAN trunk stops floating above its own plug (section 8.1)
    the -Y tabs grow to the full reach with no edit here."""
    room = BOARD_BOT - TAB_FLOOR[sgn] - TAB_CLR - TAB_PLAY
    return min(TAB_REACH_MAX, max(0.0, room))


def tab_xs(panel):
    """World X centres of the tabs on one panel -- and so of the board's notches."""
    x0, x1 = board_span(panel)
    x0, x1 = x0 + TAB_LEN, x1 - TAB_LEN
    n = max(2, int(round((x1 - x0) / TAB_PITCH)) + 1)
    return [x0 + i * (x1 - x0) / (n - 1) for i in range(n)]


def notch(sgn):
    """(depth, length) of the board-edge notch a tab passes through on the way in."""
    return tab_reach(sgn) + TAB_PLAY, TAB_LEN + TAB_SHIFT + 1.0


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
assert BOARD_BOT - CABLE_TOP >= 0.8, (
    "the LED board at %.2f leaves only %.2f over the CAN harness at %.2f"
    % (BOARD_BOT, BOARD_BOT - CABLE_TOP, CABLE_TOP))
assert BOARD_BOT - TEE_TOP >= 1.5, (
    "the LED board at %.2f leaves only %.2f over the tee PCBs at %.2f, and the panel has "
    "to SLIDE over them" % (BOARD_BOT, BOARD_BOT - TEE_TOP, TEE_TOP))
assert tab_reach(1.0) >= D.MIN_WALL, (
    "the +Y retaining tab reaches %.2f, under a %.2f bead -- with %.2f of room under that "
    "edge it should have the full %.2f" % (tab_reach(1.0), D.MIN_WALL,
                                           BOARD_BOT - TAB_FLOOR[1.0], TAB_REACH_MAX))
# ⚠ THE -Y TAB IS STARVED AND THIS IS A WARNING, NOT AN ASSERT, ON PURPOSE. It is
# short because the CAN trunk is drawn 2.5 mm above the plug it lands in -- section 8.1's
# TRUNK_DZ finding, raised there for the 1.5 mm of optical depth it costs and unresolved
# because the trunk is shared geometry. Inverting that stack puts the cable top at the
# mated plug's -19.65 and this edge gets 3.50 mm, i.e. the full reach. Asserting would
# stop every build over a number this module does not own; saying it once, loudly, at the
# one moment someone is looking at fret geometry, is the useful thing.
if tab_reach(-1.0) < D.MIN_WALL:
    import sys
    print("  !! fret_light: the -Y retaining tab reaches only %.2f (a %.2f bead is the "
          "floor).\n     %.2f mm under that edge, and a 45 deg tab needs its reach plus "
          "%.2f.\n     wiring.py TRUNK_DZ floats canl %.2f above its own plug -- invert "
          "it and this\n     edge gets %.2f. See docs/fret-led.md 8.1 and 8.5."
          % (tab_reach(-1.0), D.MIN_WALL, BOARD_BOT - TAB_FLOOR[-1.0],
             TAB_CLR + TAB_PLAY, CABLE_TOP - TEE_TOP,
             min(TAB_REACH_MAX, BOARD_BOT - TEE_TOP - TAB_CLR - TAB_PLAY)),
          file=sys.stderr)

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
    """The wall each long edge of the board runs against -- and what the tabs stand on.

    ⚠ SECTION 8.3 SAYS THE RAMPS HOLD +-Y AND THEY VERY NEARLY DO NOT. A ramp is a
    triangle from (BOARD_HALF_W, BOARD_TOP) out to the deck, so at the board's edge it is
    a KNIFE EDGE: it meets the board's top corner and has nothing beside the board's
    1.60 mm of thickness. This drops a real face past it, TAB_PLAY outboard, which is what
    the board actually bears against in Y -- and it is the only thing a tab can hang from,
    the ramp having no material at that Y to hold one.

    It costs nothing to print: it hangs from the ramp's flat underside at BOARD_TOP, in
    the deck's own print direction."""
    out = None
    for panel in BOARD_NAME:
        bx0, bx1 = board_span(panel)
        if x_lo is not None and not (x_lo <= (bx0 + bx1) / 2.0 <= x_hi):
            continue
        for sgn in (-1.0, 1.0):
            bot = BOARD_BOT - tab_reach(sgn) - TAB_PLAY
            y0 = sgn * (BOARD_HALF_W + TAB_PLAY)
            w = box_at(bx1 - bx0, WALL, BOARD_TOP - bot,
                       x=(bx0 + bx1) / 2.0, y=y0 + sgn * WALL / 2.0,
                       z=(BOARD_TOP + bot) / 2.0)
            out = w if out is None else out.union(w)
    return heal(out) if out is not None else cq.Workplane("XY")


def tabs(x_lo=None, x_hi=None):
    """The -Z retaining tabs: short 45 degree ledges under the board's long edges.

    Cross-section in Y-Z, extruded along X, exactly as the foot channel's lips are built
    -- and for the same reason, that the shape wanted is the cross-section. The face that
    holds the board is the 45 degree one; it starts at the board's own underside on the
    ramp wall, TAB_PLAY outboard of the board's edge, so over the edge it stands TAB_PLAY
    proud and the clearance under the board IS the lateral play."""
    out = None
    for panel in BOARD_NAME:
        bx0, bx1 = board_span(panel)
        if x_lo is not None and not (x_lo <= (bx0 + bx1) / 2.0 <= x_hi):
            continue
        for sgn in (-1.0, 1.0):
            r = tab_reach(sgn)
            if r < D.MIN_WALL:
                continue                      # starved: see TAB_FLOOR and section 8.1
            yw = sgn * (BOARD_HALF_W + TAB_PLAY)
            pts = [(yw, BOARD_BOT),
                   (yw - sgn * (r + TAB_PLAY), BOARD_BOT - r - TAB_PLAY),
                   (yw, BOARD_BOT - r - TAB_PLAY)]
            for xc in tab_xs(panel):
                w = (cq.Workplane("YZ").polyline(pts).close()
                     .extrude(TAB_LEN).translate((xc - TAB_LEN / 2.0, 0, 0)))
                out = w if out is None else out.union(w)
    return heal(out) if out is not None else cq.Workplane("XY")


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
