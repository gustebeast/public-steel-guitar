# -*- coding: utf-8 -*-
"""FOOT LIGHTING — the strip that fires DOWN through the chassis's light window.

The second of the two lighting jobs, and the one the original single-source strip was
always really for: light aimed at the player's feet. `src/fret_light.py` is the other.

    "add an LED design that will face down into the light window at the -z +y side
     of the instrument. That's a 572mm stretch. This one we don't have to align the
     board to the chassis sections because we'll install the chassis first, then
     slide the LED on."   (user, 2026-09-30)

WHAT IT LIGHTS, measured off the chassis rather than typed: `chassis._light_band()` is a
transparent band through the bottom prism, 8.00 wide in Y at y 50.35, running
**572.72 mm** from x -592.46 to -19.74 (the run between the two legs' feet), and 10.50
deep -- from the motor bay's floor at z -71.35 out to the bed face at -81.85. The strip
sits ON TOP of that band and shines into it; the 10.50 of PCTG is the diffuser.

⚠ EVERYTHING ABOVE IT IS EMPTY, AND THAT IS WHY THIS IS EASY. A box swept the whole run
at 15 mm wide and 5.85 tall (tools/_probe_mouth.py): **clear end to end**, with the
belt tensioners' lowest feature at z -65.22 and the +Y rail's inner face at y 55.55 the
only two things anywhere near. Both mouths are open too -- 34.4 mm of clear approach at
the bridge end and 44.8 at the keyhead end, bounded only by the endplates, which are not
on yet when this slides in.

⚠ TWO BOARDS, AND IT IS THE ASSEMBLER'S LIMIT, NOT A CHOICE. JLCPCB's published assembly
capability, read 2026-09-30: **Economic PCBA takes a single PCB from 10x10 to 470x500 mm;
Standard PCBA from 70x70 to 460x500.** 572.72 is past both, so one board cannot be built
whatever it would cost. Two of 308.36 are a long way inside.

THE SPLIT IS OPTICALLY INVISIBLE, which is the part worth protecting: 48 LEDs at one
pitch run the whole window, and the seam falls exactly half a pitch past LED 23 and half
a pitch before LED 24. Neither board knows where the chassis sections are -- the user's
point -- and neither does the light.

WHY THE PITCH IS WHAT IT IS. Same Lambertian model as the fret cells, and the same
lesson: what decides evenness is the ratio of SPACING to DEPTH. Here the depth is fixed
at 10.80 by the bottom prism, so the pitch is the only lever:

    S/h    pitch    ripple
    0.95   10.26    1.04 : 1
    1.11   11.93    1.11 : 1      <- chosen
    1.29   13.50    1.20 : 1
    1.52   16.00    1.40 : 1

11.93 is where the LED count lands on a whole number of ZONES: 48 LEDs, four in series
per channel, is 12 zones and exactly 4 x TLC59711 with nothing wasted -- 6 zones and 2
drivers on each board. One LED coarser and the arithmetic stops dividing.
"""
from __future__ import annotations

from . import dimensions as D
from . import pogo_part as PG
from .components import MOTOR_PULLEY_STANDOFF

# ── the window this lights, READ from the chassis ─────────────────────────────────────
# ⚠ NOT COPIED. The band's Y comes from the +Y rail's centre-line and its X from where
# the legs' feet start, so all four numbers move when the chassis does. The import is
# LATE because chassis imports THIS module to build the channel -- the same cycle
# top_plate/fret_light have, and the same way out of it.
_WIN = None


def _ch():
    from . import chassis as CH
    return CH


def window():
    """(x0, x1, yc, w, z_top, z_bot) of the transparent band, in world mm."""
    global _WIN
    if _WIN is None:
        b = _ch()._light_band().val().BoundingBox()
        _WIN = (b.xmin, b.xmax, (b.ymin + b.ymax) / 2.0, b.ymax - b.ymin, b.zmax, b.zmin)
    return _WIN


def run_len():
    x0, x1 = window()[0], window()[1]
    return x1 - x0


# ── the Z stack ───────────────────────────────────────────────────────────────────────
# Bottom up from the window's own top face. Everything on the board hangs from its
# underside, and the board stands just high enough for the TALLEST of them to clear the
# floor -- so the floor is not cut at all (user, 2026-10-02: "raise so we don't have to
# cut into the chassis floor"). The tallest is board A's cable socket, a side-entry JST XH
# at 5.75 (user, 2026-10-04: XH is the instrument's 24 V connector, "move the board
# further +z until the XH connector fits"); the seam pogo's barrel is 3.80, the buck's
# inductor 3.00 and the LED 1.60.
#
# ⚠ THE LED IS 4.45 OFF THE WINDOW NOW, and that is the price, paid twice over. It was
# 0.30 when the LED set the trough, 2.50 when the pogo did. The window is 8 mm wide, so a
# Lambertian row 4.45 above it puts about two thirds of its light straight into the
# opening where at 2.50 it was about 85 % -- the rest lands on the trough floor either
# side first. ESTIMATED from the geometry, not measured. Along the run it is BETTER: the
# depth the pitch is judged against grows with it.
FLOOR_NOM  = -71.35                 # window top = motor bay floor; asserted below
AIR_GAP    = 0.30                   # the tallest hanging part to the floor: a print tolerance
LED_H      = 1.60                   # XL-5050RGBW body (LCSC C7371891, and see fret_light)
LED_BODY   = 5.00                   # ...and its plan size, square (the footprint's F.Fab)
BOARD_T    = 1.60
XH_H       = 5.75                   # JST S4B-XH-SM4-TB above its board (board_geom's
                                    # figure; elec/foot_led.py asserts the two agree)
HANG_MAX   = max(PG.POGO_BODY_H, XH_H)
TROUGH     = HANG_MAX + AIR_GAP     # 6.05: floor to the board's underside
SLOT_PLAY  = 0.30                   # board edge to the wall -- AND, via the 45° ramp,
                                    # the clearance over the board's top face
LIP_OVER   = 0.80                   # how far each lip reaches OVER the board: 1 bead
LIP_CAP    = 0.80                   # the flat cap above the ramp: 1 bead
# ⚠ WHAT THIS ASKS OF THE BELT CLAMPS, WHICH ARE BEING REDESIGNED (user, 2026-10-02, and
# 2026-10-04: "we can ignore collision with the belt clamp"). The lips top out at floor +
# 9.55 = -61.80 and the board's top is at -63.70. Today's placeholder tensioners come down
# to -65.22..-65.34 over y 20..48, so string 1's stands INTO the strip as drawn. The number
# the new clamps have to respect is ceiling_needed().
CEILING_CLR = 0.50


def z_stack():
    """(led_face, board_bot, board_top, lip_foot, lip_top) in world Z.

    ⚠ THE LIP'S FOOT IS THE BOARD'S OWN TOP PLANE, and that is the 45° ramp paying
    for itself. The ramp starts on the slot wall at exactly board_top, so at the board's
    EDGE -- SLOT_PLAY further in -- it stands SLOT_PLAY proud of the board, and the
    clearance over the board is the lateral play, not a second figure to keep in step
    with it."""
    floor = window()[4]
    bb = floor + TROUGH
    led = bb - LED_H
    bt = bb + BOARD_T
    return led, bb, bt, bt, bt + SLOT_PLAY + LIP_OVER + LIP_CAP


def ceiling_needed():
    """The lowest anything above the channel may come: the lips' tops plus a gap."""
    return z_stack()[4] + CEILING_CLR


def clear_top():
    """The plane the slot has to be CUT clear to: the ramp over the board's edge."""
    return z_stack()[2] + SLOT_PLAY


def depth():
    """The h the optics are solved at: the LED's face to the window's exit face."""
    led = z_stack()[0]
    return led - window()[5]


# ── the Y lanes ───────────────────────────────────────────────────────────────────────
# ⚠ THE +Y RAIL IS THE HARD EDGE. Its inner face is at y 55.55 and the window's centre
# at 50.35, so there are 5.20 mm on the +Y side of the LED row and as much as we like on
# the -Y side. That asymmetry is what decides the whole layout: the LED row sits on the
# window's centre, and everything else -- drivers, passives, the connector -- goes into a
# lane BELOW it in Y.
#
# It also means the two boards cannot be one part number used twice. A single SKU would
# have to be symmetric about the LED row to survive being turned end for end, and a board
# centred on 50.35 may only be 2 x 5.20 = 10.40 wide -- too narrow to put a driver
# anywhere but IN the LED row, which costs a 14 mm gap in the pitch and a 1.32 : 1 dip
# there against the 1.11 the rest of the run holds. Mirror-image boards cost one extra
# fab and assembly setup; the dip would have shown in four places.
RAIL_IN    = 55.55                  # chassis body's inner face (measured)
BOARD_Y1   = 55.20                  # board's +Y edge: 0.35 of play against the rail
# ⚠ THE -Y EDGE IS STRING 1'S MOTOR, PLUS ONE WALL (user, 2026-10-02: "there's 9.25 mm
# currently between the motor and the PCB. What if we drop that to 1.6"). The board was at
# 38.00 because that was all the lane needed for a cable socket. The seam is four pogos
# now and their lands are 3.50 wide, so the lane wants every millimetre there is -- and
# the only thing standing in it is that motor's faceplate wall, 6.40 thick. The slot is
# cut INTO the wall and leaves WALL_T of it against the motor; the board's edge is one
# sliding fit further out. Everywhere else along the run the same 1.60 stands alone as
# the channel's own wall.
WALL_T     = D.MIN_WALL_2P          # 1.60
# ⚠ THE WALL'S FACE, NOT THE MOTOR'S. The motor's faceplate is at 28.75 and the pocket is
# cut D.MOTOR_CLR larger all round (motor_bank.lift_prism), so the plastic starts at
# 29.15. Measuring the 1.60 from the motor itself left 1.20 of wall in the mouth and, in
# the run, a channel wall unioned back INTO the motor's fit -- found by sampling the
# finished chassis (tools/_probe_foot_mouth.py), not by the gate: the motor's body ends
# at 28.75 and never touched it.
MOTOR_FACE = D.motor_pos(0)[1] - MOTOR_PULLEY_STANDOFF + D.MOTOR_CLR   # 29.15
WALL_Y0    = MOTOR_FACE             # the -Y wall's outer face IS the pocket's own face
BOARD_Y0   = MOTOR_FACE + WALL_T + SLOT_PLAY              # 31.05
# The component lane's centre is where it was: drivers, the buck and the supply row sit
# on it, spaced along X. The 6.45 gained on the -Y side belongs to the pogos' first two.
DRV_Y      = 42.55
BOARD_W    = BOARD_Y1 - BOARD_Y0    # 24.15


def led_y():
    """The LED row's Y: the window's own centre."""
    return window()[2]


# ── the channel ───────────────────────────────────────────────────────────────────────
# A slot the board SLIDES into along X, because that is the install the user described:
# chassis first, then the strip. It is deliberately plain -- two shoulders to stand the
# board on, two lips to hold it down, a wall on the -Y side, and the chassis's own body
# as the wall on the +Y side. Nothing in it is keyed to where a board ends, so the board
# and the chassis sections stay independent of each other.
#
# ⚠ THE LIPS ARE 45° RAMPS, AND THERE IS NO HORIZONTAL OVERHANG ANYWHERE IN THIS
# CHANNEL. The chassis builds world +Z, so a lip that reached flat over the slot would be
# an unsupported ceiling -- printable at 2 mm by bridging, but bridging is a sag and a
# rough underside, and the underside is the face that holds the board down. Instead each
# lip rises off its wall at 45°: every layer sits on the one below it, out to
# SLOT_PLAY + LIP_OVER, and then a flat cap of LIP_CAP finishes it. Nothing bridges,
# nothing droops, and the surface the board would lift into is solid.
#
# The middle of the slot stays open, which still lets the drivers' heat out into the bay.
#
# ⚠ NO RELIEF GROOVE ANY MORE. The opaque bottom used to be relieved 1.50 under the
# component lane, because the LED set the trough at 1.90 and the inductor and connector
# did not fit in it. The board is raised instead (see the Z stack), the trough is 4.10
# from wall to wall, and the floor under it is whole.
#
# ⚠ THE TWO SHOULDERS ARE DIFFERENT, AND THE POGOS ARE WHY. A barrel hangs the trough's
# full depth and travels the channel's whole length on the way in, so a shoulder may only
# stand where no barrel ever passes.
# ⚠ BOTH ARE TWO BEADS (user, 2026-10-05: they were 1.20 and 1.50, neither a whole number
# of beads). The -Y one is what positions the pogo row -- 1.60 of shoulder, 0.35 of air,
# then the first barrel -- so widening it moved all four pogos 0.40 toward the LED row;
# see check_optics for what that row is now held clear of.
SHOULDER_LO = D.MIN_WALL_2P          # 1.60, -Y shoulder's reach from the slot wall
SHOULDER_HI = D.MIN_WALL_2P          # 1.60, +Y shoulder's reach from the rail
SHOULDER_AIR = 0.35                 # a shoulder to the nearest barrel


def _slot_y():
    """(y0, y1) of the slot the board sits in."""
    return BOARD_Y0 - SLOT_PLAY, RAIL_IN


def trough_y():
    """(y0, y1) of the clear trough between the shoulders -- what may hang below."""
    y0, _y1 = _slot_y()
    return y0 + SHOULDER_LO, RAIL_IN - SHOULDER_HI


# ── the boards ────────────────────────────────────────────────────────────────────────
# ⚠ 72 LEDs AND THREE TO A ZONE -- and the two numbers are one decision (user,
# 2026-09-30: "would it benefit us to put 3 LEDs per zone instead of 2? Same number of
# zones just increase LED density"). It does, and the reason is the economics this whole
# strip is built on: A CHANNEL COSTS A THIRD OF A DRIVER, AN LED COSTS SIX CENTS. The
# channel count is zones x 4 and the zone count is N_LED / N_SERIES, so raising both
# together leaves the channel count -- and therefore the driver count, and therefore the
# money and the board area -- exactly where it was:
#
#     48 LEDs, 2 in series   24 zones   96 channels   8 drivers   $19.28 + $3.12 of LEDs
#     72 LEDs, 3 in series   24 zones   96 channels   8 drivers   $19.28 + $4.68 of LEDs
#
# Half again the light for $1.56 an instrument, with the addressing untouched.
#
# ⚠ AND 72 IS THE LAST COUNT THAT FITS, which is the pleasant part: the XL-5050's
# courtyard is 6.10 and the pitch at 72 is 7.954, so 1.85 mm of clear lane between
# neighbours. 96 LEDs (4 a zone) would be a 5.97 pitch -- the courtyards OVERLAP by 0.13
# and check_placement rejects the board. So this is the densest the row can be at all, and
# it happens to land on a series count that divides into 24 zones.
#
#     LEDs  pitch   S/h    ripple
#      48   11.932  1.105  1.095 : 1
#      72    7.954  0.737  1.008 : 1    <- chosen
#      96    5.966  0.552  courtyards overlap
#
# What it costs is rail volts again, and only that: three dice at the LED's 3.2 V max is
# 9.6, so the rail goes 7.67 -> 11.00 (elec/foot_led.py, R11 10k) and the headroom over
# the string grows slightly, 1.27 -> 1.40. Rail CURRENT does not move at all, because the
# current is set by the channel count: 48 channels x 15 mA a board, before and after. The
# extra light is paid for in volts, which is the one thing this rail has spare.
N_LED      = 72
# ⚠ THREE IN SERIES, AND THE SERIES COUNT IS THE DIVISOR BETWEEN LEDs AND ZONES. It is
# the only knob on how finely the strip can be addressed: 72 LEDs at 3 in series is 24
# zones of 23.9 mm (user, 2026-09-30: "I'd like to have closer to 24 controllable zones").
# Zones come in threes, because a TLC59711 carries three, and 24 divides.
N_SERIES   = 3                      # LEDs per channel; 3 x 3.2 V = 9.6 on the 11.00 rail
HALVES     = ("a", "b")
# ⚠ ONE PART NUMBER, BUILT TWICE -- and it is the -X-only install that buys it (user,
# 2026-09-30: "we install this LED before we put the -x endplate on so it can slide in
# from -x"). Both halves go in the same way up and the same way round, one after the
# other through the same mouth, so the +X board is not a mirror of the -X board: it is
# the SAME board, 286.36 further along. A first draft had them as mirror images with
# their connectors at opposite outer ends, which cost a second fab and assembly setup
# and put one harness at the bridge end, 600 mm from the Pi. Sliding both from -X
# deletes all of that.
# ⚠ TWO BOARDS, TWO DESIGNS (user, 2026-10-04). They were one design built twice, and that
# is what put four pogos on each board's OUTER end, mating nothing, and left the strip
# with no way in: a cable socket cannot share an end with a pogo row. So the ends are
# populated for what they do --
#     board A (-X):  a cable socket at its -X end, the seam's four pogos at its +X end
#     board B (+X):  the seam's four pogos at its -X end, nothing at its +X end
# -- eight pogos instead of sixteen, and the Pi's cable plugs straight into board A.
# Everything between the ends is the same on both.
BOARD_NAME = {"a": "foot_led_a", "b": "foot_led_b"}
# ⚠ THE SEAM IS POGOS BECAUSE -X-ONLY INSERTION MAKES IT SO. The +X board is pushed the
# full length of the channel first, so nothing can be plugged into it once it is home.
# The two boards meet TIP TO TIP, the way the fret boards do across the deck seam: four
# side-mount pogos on one axis under each board, and pushing the second board home
# against the first is what makes the joint.
#
# FOUR CIRCUITS, ONE PIN EACH: +24V, GND, SCK, SDT. The part is rated 12 A a pin and the
# far board draws 0.37.
#
# WHERE THEY CAN STAND WAS MEASURED, AND IT IS A TIGHT ROW. A land is 3.50 wide. On the
# -Y side the first barrel has to clear the shoulder; on the +Y side the last land has to
# clear the end LED, and that LED sits at exactly the X a pogo needs, so the LED row's own
# Y is closed to them. Between the two:
#     shoulder  32.35 | 0.35 | barrel 1 ... four at POGO_PITCH 3.80 ... land 4 ends 47.40
#     | 0.45 | LED body 47.85     (and 0.10 INSIDE its 6.10 courtyard -- see check_optics)
# 3.80 leaves 0.30 of bare board between neighbouring lands and 0.70 between barrels. It
# is under the 4.50 the fret seam uses and under the courtyards' own 4.00, which is why
# elec/foot_led.py exempts these pairs from the courtyard check and asserts the copper.
# THE INLET: a 4-way side-entry JST XH on board A, its mouth facing -X.
# ⚠ IT STANDS ON A TAIL, -X OF THE WINDOW, AND THAT IS WHERE ITS WIDTH GOES (user,
# 2026-10-04: "extend the board towards -x and put the connector fully -x of the led").
# The socket is 13.4 across its body and 15.7 across its two mounting lands; the lane
# beside the LED row is 15.3 between the -Y shoulder and the end LED's courtyard. So the
# body's front and both mounting lands sit on TAIL_A of extra board past the window's -X
# end, where there is neither a shoulder nor an LED, and only its four signal lands --
# 8.8 across -- reach back beside the first LED.
# ⚠ AND NOT FURTHER -X THAN THIS. The keyhead endplate's face is 15.3 from the window's
# end. The mouth is J_MOUTH out, which leaves 8.8 for the mated plug (about 4.3 past the
# mouth) and the lead's first bend.
TAIL_A     = 7.0                    # board A's extra length past the window's -X end
J_INSET    = 0.5                    # the socket's mouth, in from that end: its mounting
                                    # lands stand 0.2 proud of the mouth
J_Y        = 41.50                  # world Y of the socket's centreline: its signal lands
                                    # end 0.85 short of the end LED's courtyard
POGO_NETS  = ("+24V", "GND", "SCK", "SDT")      # -Y first
POGO_PITCH = 3.80
# pad centre to the board's end: the barrel is centred on its pad and a plunger at its
# working length ends exactly at the board's edge, so two butted boards meet at the seam
POGO_SETBACK = PG.POGO_WORK - PG.POGO_BODY_L / 2.0        # 4.05


def pogo_ys():
    """World Y of the four pogo axes, -Y first."""
    y0 = (_slot_y()[0] + SHOULDER_LO + SHOULDER_AIR
          + (PG.POGO_BODY_W + PG.POGO_FAB_STROKE) / 2.0)
    return [y0 + i * POGO_PITCH for i in range(len(POGO_NETS))]


def pogo_pads(sgn):
    """[(board_x, board_y, net)] for one END of a board, in elec/'s board frame.

    `sgn` is -1 for the -X end (board B's seam end), +1 for the +X end (board A's). One
    list, so the two boards either side of the seam cannot disagree about which lane is
    which."""
    a, b = board_span("a" if sgn > 0 else "b")      # each end belongs to one board
    half = (b - a) / 2.0
    return [(sgn * (half - POGO_SETBACK), to_board_y(y), net)
            for y, net in zip(pogo_ys(), POGO_NETS)]


def pitch():
    return run_len() / N_LED


def led_xs():
    """Every LED's world X, -X first. One pitch throughout -- including across the seam."""
    x0, p = window()[0], pitch()
    return [x0 + p / 2.0 + i * p for i in range(N_LED)]


def seam_x():
    """Where the two boards meet: half a pitch past LED 23."""
    return window()[0] + run_len() / 2.0


def board_span(half):
    """(x0, x1) of one board in world X: its half of the window, and for board A the
    tail its cable socket stands on.

    The LED row runs to within half a pitch of the window's two ends and of the seam, so
    the seam costs no light at all; the tail carries no LED."""
    x0, x1 = window()[0], window()[1]
    return (x0 - TAIL_A, seam_x()) if half == "a" else (seam_x(), x1)


def board_cx(half):
    a, b = board_span(half)
    return (a + b) / 2.0


def to_board_x(half, world_x):
    """World X -> the board-local X elec/ places a part at."""
    return world_x - board_cx(half)


def to_board_y(world_y):
    """World Y -> the board-local Y elec/ places a part at.

    ⚠ IT IS A MIRROR, because the board is installed FACE DOWN. `_placed` turns it
    over about X, which negates Y as well as Z, so a part authored at board-local +a
    lands at world (board centre - a). Getting this backwards puts the LED row on the
    wrong side of the window and nothing downstream would notice: the board routes, the
    CAD renders, and the light misses the slot."""
    return (BOARD_Y0 + BOARD_W / 2.0) - world_y


def board_leds(half):
    """The world X of the LEDs this board carries."""
    lo, hi = board_span(half)
    return [x for x in led_xs() if lo <= x <= hi]


# ── the optics ────────────────────────────────────────────────────────────────────────
def uniformity(p=None, h=None, n=401, reach=40):
    """min/max illuminance along a periodic row of Lambertian sources at depth h.

    The same model fret_light uses, minus the end reflectors -- this run has no ends
    worth modelling, being 572 mm of identical pitch. `reach` is how many neighbours
    either side contribute; past ~20 the sum has converged."""
    p = pitch() if p is None else p
    h = depth() if h is None else h
    srcs = [k * p for k in range(-reach, reach + 1)]
    e = [sum((h * h / (h * h + (p * i / n - s) ** 2)) ** 2 for s in srcs)
         for i in range(n + 1)]
    return min(e) / max(e)


def check_optics():
    """The strip's own numbers, against the geometry it is actually built into."""
    u = uniformity()
    assert u >= 0.87, (
        "the foot strip is %.2f : 1 along the run, past the 1.15 : 1 this pitch was "
        "chosen for -- N_LED, the Z stack or the window's depth has moved" % (1.0 / u))
    assert abs(window()[4] - FLOOR_NOM) < 0.01, (
        "the window's top face is %.2f, not the %.2f the Z stack is written against"
        % (window()[4], FLOOR_NOM))
    _led, _bb, bt, lip_foot, lip_top = z_stack()
    assert lip_foot == bt, (
        "the lips' ramp starts at %.2f, not the board's top at %.2f -- the 45° face is "
        "what sets the clearance over the board and it has come adrift of it"
        % (lip_foot, bt))
    assert min(LIP_OVER, LIP_CAP) >= D.MIN_WALL - 1e-9, (
        "a %.2f lip reach and a %.2f cap against a %.2f bead" % (LIP_OVER, LIP_CAP,
                                                                D.MIN_WALL))
    ty0, ty1 = trough_y()
    assert ty0 - BOARD_Y0 >= D.MIN_WALL - 1e-9 and BOARD_Y1 - ty1 >= D.MIN_WALL - 1e-9, (
        "the trough %.2f..%.2f leaves a board edge under one bead to stand on"
        % (ty0, ty1))
    assert BOARD_Y1 <= RAIL_IN, (
        "the board's +Y edge at %.2f is inside the rail at %.2f" % (BOARD_Y1, RAIL_IN))
    # the pogo row, as BODIES rather than courtyards -- see POGO_PITCH
    ys = pogo_ys()
    hb = (PG.POGO_BODY_W + PG.POGO_FAB_STROKE) / 2.0
    assert ys[0] - hb - ty0 >= SHOULDER_AIR - 1e-9, (
        "the first barrel is %.2f off the -Y shoulder" % (ys[0] - hb - ty0))
    assert POGO_PITCH - PG.POGO_PAD_W >= 0.30 - 1e-9, (
        "%.2f of board between neighbouring pogo lands" % (POGO_PITCH - PG.POGO_PAD_W))
    # ⚠ AGAINST THE LED'S BODY, NOT ITS COURTYARD. This was 0.30 to the courtyard (6.10
    # square) until the -Y shoulder went to two beads and took 0.40 of the lane; the land
    # now stands 0.10 INSIDE that courtyard. What is physically there is the XL-5050's
    # 5.00 body, and its own lands stop 2.26 from its centre in Y -- so the pogo's land is
    # 0.45 from the LED's body and 0.69 from its nearest copper. elec/pcb_declared.py
    # accepts exactly that courtyard pair on each board.
    led_body = led_y() - LED_BODY / 2.0
    assert led_body - (ys[-1] + PG.POGO_PAD_W / 2.0) >= 0.30 - 1e-9, (
        "the last pogo land ends %.2f from the end LED's body"
        % (led_body - (ys[-1] + PG.POGO_PAD_W / 2.0)))
    assert TROUGH - HANG_MAX >= AIR_GAP - 1e-9
    # the cable socket: its tail and its plug stay inside the corridor cut for the boards
    assert TAIL_A <= MOUTH_CUT, (
        "board A's tail is %.1f and the corridor is cut %.1f past the window"
        % (TAIL_A, MOUTH_CUT))
    return u


# ── THE CAD ───────────────────────────────────────────────────────────────────────────
import cadquery as cq                                            # noqa: E402

from .helpers import box_at, heal                                # noqa: E402


def _lip(xl, xm, y_wall, sgn, foot_z, top_z):
    """One retaining lip: a 45° ramp off a slot wall, capped flat, run along X.

    Authored as a cross-section in Y-Z and extruded, because a chamfered box would mean
    picking an edge on a 572 mm prism by geometry search -- and the shape wanted here is
    the cross-section, so that is what is drawn."""
    reach = SLOT_PLAY + LIP_OVER
    pts = [(y_wall, foot_z),
           (y_wall + sgn * reach, foot_z + reach),
           (y_wall + sgn * reach, top_z),
           (y_wall, top_z)]
    return (cq.Workplane("YZ", origin=(xm - xl / 2.0, 0, 0))
            .polyline(pts).close().extrude(xl))


STOP_T  = 4 * D.BEAD                # 3.20 along X
STOP_Y0 = 47.60                     # ...from just past the last pogo land to the rail


def channel():
    """The slot the strip slides into, to be unioned into the chassis bottom.

    Authored in WORLD coordinates, like the fret comb, because that is where the chassis
    works and where it has to land. Runs the WINDOW's length exactly -- the boards'
    tails hang out past both ends into the clear approach, which is also where their
    connectors are, so nothing has to be threaded through a wall."""
    x0, x1 = window()[0], window()[1]
    floor = window()[4]
    _led, board_bot, _bt, lip_foot, lip_top = z_stack()
    sy0, sy1 = _slot_y()
    ty0, ty1 = trough_y()
    xm, xl = (x0 + x1) / 2.0, x1 - x0

    def run(y0, y1, z0, z1):
        return box_at(xl, y1 - y0, z1 - z0, x=xm, y=(y0 + y1) / 2.0, z=(z0 + z1) / 2.0)

    out = run(WALL_Y0, sy0, floor, lip_top)                       # the -Y wall
    # THE +X STOP. The seam pogos push the two boards apart with about 0.8 kgf, so the
    # far board needs something to be pushed AGAINST. A block across the slot's end, on
    # the LED row's side only: the +X board's own unused plungers stand 1.70 past its end
    # across the pogo lane and must find air there.
    out = out.union(box_at(STOP_T, sy1 - STOP_Y0, lip_foot - floor,
                           x=x1 + STOP_T / 2.0, y=(STOP_Y0 + sy1) / 2.0,
                           z=(floor + lip_foot) / 2.0))
    out = out.union(run(sy0, ty0, floor, board_bot))              # -Y shoulder
    out = out.union(run(ty1, sy1, floor, board_bot))              # +Y shoulder
    out = out.union(_lip(xl, xm, sy0, +1.0, lip_foot, lip_top))
    out = out.union(_lip(xl, xm, sy1, -1.0, lip_foot, lip_top))
    return heal(out)


def slot_cut():
    """The volume the strip and its parts occupy -- CUT from the chassis before the
    channel is unioned back in.

    ⚠ THE CHANNEL IS ADDITIVE, SO IT CANNOT MAKE ROOM BY ITSELF. Unioning walls and lips
    onto the bottom says nothing about what was already standing in the slot. Cutting the
    envelope first and building the channel into the hole makes the board's space a fact
    rather than a hope -- and it is also the INSERTION CORRIDOR, which runs the channel's
    whole length because that is how the board gets in.

    ⚠ IT CUTS INTO STRING 1'S FACEPLATE WALL, AND TAKES ONLY WHAT IT MUST (user,
    2026-10-02: "remains printable and keeps as much material as possible, only removing
    what we need to fit the PCB and avoid print overhangs"). The wall is 6.40 thick and
    the slot takes all but WALL_T of it over the board's height. What is left ABOVE the
    slot would be a flat ceiling 4.80 deep in a chassis that prints +Z, so the cut's roof
    rises at 45° from the slot wall instead: the same ramp as the -Y lip, simply carried
    on up through the wall until it leaves it. Nothing above that line is touched."""
    # ⚠ THE CORRIDOR STARTS BEFORE THE WINDOW DOES. String 1's faceplate wall runs 13.7 mm
    # past the window's -X end, and the slot cut used to stop AT that end -- so the wall
    # stood whole across the mouth and no board could have been slid in past it. Found as
    # 5.3 mm3 of one free plunger inside chassis_2 (tools/_probe_foot_cut.py).
    x0, x1 = window()[0] - MOUTH_CUT, window()[1]
    floor = window()[4]
    top = clear_top()
    foot = z_stack()[3]
    sy0, sy1 = _slot_y()
    yr = MOTOR_FACE + ROOF_REACH
    # ONE section: up the slot wall to the board's top, then the ramp -- so even the fit's
    # 0.30 over the board is under the 45° line and no flat is left at the wall
    return (cq.Workplane("YZ", origin=(x0, 0, 0))
            .polyline([(sy0, floor), (sy1, floor), (sy1, top), (yr, top),
                       (yr, foot + (yr - sy0)), (sy0, foot)])
            .close().extrude(x1 - x0))


MOUTH_CUT = 16.0     # how far -X of the window the corridor is cut: past the wall's end

# how far +Y of the motor's face the 45° roof is carried: the faceplate wall (6.40) and a
# little, so the cut leaves the wall through its far face rather than stopping inside it
ROOF_REACH = 8 * D.NOZZLE_D + 0.50


def pogo_pins():
    """[(name, solid)] -- the seam's eight plungers, barrel front to seam plane.

    The barrels are the boards' own (board_geom reads the pogo's F.Fab); the plungers are
    here because they leave the board. Each pair meets on the seam plane."""
    _led, bb, _bt, _lf, _lt = z_stack()
    z = bb - PG.POGO_AXIS_H
    out = None
    edge = seam_x()
    for sgn in (1.0, -1.0):                 # board A's +X end, board B's -X end
        pad = edge - sgn * POGO_SETBACK
        front = pad + sgn * (PG.POGO_BODY_L + PG.POGO_FAB_STROKE) / 2.0
        for y in pogo_ys():
            c = (cq.Workplane("YZ").circle(PG.POGO_PLUNGER_D / 2.0)
                 .extrude(abs(edge - front)).translate((min(front, edge), y, z)))
            out = c if out is None else out.union(c)
    return [("foot_pogo_pins", out)]


def _led_refs(half):
    from . import board_geom as BG
    return [f["ref"] for f in BG.load(BOARD_NAME[half])["footprints"]
            if f["ref"].startswith("D")]


def _placed(half, wp):
    """Board frame (centred, underside at z=0, parts rising +Z) into world.

    ⚠ THE BOARD IS UPSIDE DOWN HERE, and that is the whole point of this strip: its
    parts face -Z. board_geom hands back a board with its underside at z = 0 and its
    parts rising +Z, so it is turned over about X -- which also mirrors Y, so the board
    is authored in elec/ with its LED row at -(led_y() - cy) and comes out right."""
    _led, board_bot, board_top, _lb, _lt = z_stack()
    return (wp.rotate((0, 0, 0), (1, 0, 0), 180.0)
            .translate((board_cx(half), BOARD_Y0 + BOARD_W / 2.0, board_top)))


def pcb(half):
    """One board and every part on it, LEDs included, as routed -- one PART, so a board
    and its LEDs hide and show together."""
    from . import board_geom as BG
    return _placed(half, BG.solid(BOARD_NAME[half]))


def silk(half):
    """The board's lettering, both faces, where the board is -- its own part (white
    ink). The back's is mirror writing under the laminate, as the fab prints it."""
    from . import board_geom as BG
    sides = [w for w in (BG.silk(BOARD_NAME[half], s) for s in ("F", "B")) if w is not None]
    if not sides:
        return None
    solids = [x for w in sides for v in w.vals() for x in v.Solids()]
    return _placed(half, cq.Workplane("XY").newObject([cq.Compound.makeCompound(solids)]))


def leds(half):
    """The strip's LEDs alone, as their routed bodies -- for probes; the build draws
    them as part of pcb()."""
    from . import board_geom as BG
    return _placed(half, BG.bodies(BOARD_NAME[half], _led_refs(half)))


# ── the lead: board A's socket to the Pi cap ────────────────────────────────────────────
# One 4-way XH-to-XH lead (GND, 24 V, SCK, SDT). It is DRAWN in src/led_leads.py, as four
# conductors each on its own contact; what is here is where it may go.
LEAD_STUB  = 4.0                    # straight out of the mouth before the first bend: the
                                    # XHP-4 housing stands about 4.3 past it
# ⚠ IT GOES OVER STRING 1's MOTOR, BECAUSE THERE IS NO WAY ROUND IT. The socket is +Y of
# that motor and the Pi is -Y of it; the motor is a 42 mm square from the bay floor up, its
# back 2.4 from the endplate's wall and its side 2.4 from the next motor. Measured on
# sections of the built parts, 2026-10-04.
LEAD_FLY   = 12.0                   # above the motor's top, and what sets it is string 1's
                                    # CAN tee, which lies ON that motor at y 18..35 and tops
                                    # out 9.35 above it: the lead crosses 1.0 over the board.
                                    # (At 6.0 it cleared the chassis rib and ran straight
                                    # through the tee, 130 mm3 -- the gate found it.)
LEAD_COL_X = -595.5                 # the column it crosses in. 2.5 further -X it meets the
                                    # motor board's corner post (x -599.7..-598.3, up to
                                    # z -21.95); 1.5 further +X it grazes the 24 V trunk's
                                    # drop into the motor board (3.5 mm3)
# (Where it comes back down is no longer a number here: led_leads drops each conductor
#  a plug length and 1.0 out of the Pi cap's J6, which puts the four at y -54.5 to -49.7
#  -- between the motor's -Y face at -41.25 and the cap's +Y edge at -59.2.)


def routed():
    """Have both boards been routed and exported yet?

    ⚠ THE FIRST RUN OF A FRESH CHECKOUT HAS NO BOARD. elec/geom/<board>.geom.json is
    written by export_geom AFTER a route, and elec/foot_led.py imports THIS module to
    lay that board out -- so on a tree where the geometry has never been exported, asking
    build.py for the strip is asking for a file that the build itself is a prerequisite
    of. ui_panel records the same cycle and breaks it with a late import; that is not
    enough here, because the file can be legitimately absent rather than merely
    late. So the CAD leaves the strip out and says why, instead of failing the build."""
    import os
    from . import board_geom as BG
    return all(os.path.isfile(os.path.join(BG.GEOM_DIR, n + ".geom.json"))
               for n in BOARD_NAME.values())


def parts():
    """[(name, solid)] for build.py -- the two boards and the seam's plungers. The lead
    to the Pi cap is src/led_leads.py."""
    if not routed():
        print("  (no %s.geom.json yet -- the foot strip is left out of this build; "
              "route and export it, see elec/foot_led.py)" % "/".join(BOARD_NAME.values()))
        return []
    inks = [("foot_pcb_%s_silk" % h, silk(h)) for h in HALVES]
    return ([("foot_pcb_%s" % h, pcb(h)) for h in HALVES]
            + [(n, w) for n, w in inks if w is not None] + pogo_pins())
