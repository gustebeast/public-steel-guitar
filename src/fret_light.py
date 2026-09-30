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
fret field the base is opaque (colour material) EXCEPT for a transparent column under each
fret line and under the two border strips. Isolation by MATERIAL, not by air -- which also
keeps the deck a solid plate, where 24 slots of 7 x 79.6 through a 4.8 base would not.

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
BOARD_BOT = -19.00                 # 0.65 over the tee PCBs
BOARD_T   = 1.60
BOARD_TOP = BOARD_BOT + BOARD_T    # -17.40
LED_H     = 1.40                   # XL-5050RGBW body to its emitting face
LED_Z     = BOARD_TOP + LED_H      # -16.00
DEPTH_NOM = APERTURE_Z_NOM - LED_Z  # 20.80, the h the optics were solved at

# ── where the three LEDs go along the fret ────────────────────────────────────────────
# Solved numerically, not guessed: 27.15 maximises min/max over the whole 79.6 with end
# reflectors at 0.85. It is NOT 2*HALF_LEN/3 = 26.53, the even-thirds answer — the
# reflectors pull it outward. Rounded onto the bead grid at 34 beads.
LED_Y    = 34 * D.BEAD             # 27.20
LED_YS   = (-LED_Y, 0.0, LED_Y)
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
BOARD_HALF_W = 39 * D.BEAD         # 31.20 -> a 62.4 wide board
# The fret line runs to +-39.8, so the last ~8.6 mm of each cell has no board under it.
# Rather than widen the board to 84, the deck RAMPS ITS OWN FLOOR up from the board's edge
# to the aperture. The ramp closes the cell AND is the end reflector the optics want, and
# at 58 degrees from horizontal it self-supports in this print direction.
RAMP_DEG = 58.0


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
    assert u >= 0.80, (
        "the fret line is %.2f : 1 end to end, past the 1.25 : 1 this geometry was solved "
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
assert BOARD_BOT > -19.65, (
    "the LED board at %.2f is into the tee PCBs at -19.65" % BOARD_BOT)
assert LED_Y + LED_CRTYD / 2.0 <= BOARD_HALF_W, (
    "the outer LEDs at +-%.2f plus a %.2f courtyard overhang a %.2f-half-width board"
    % (LED_Y, LED_CRTYD, BOARD_HALF_W))
