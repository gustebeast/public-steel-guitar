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

from . import dimensions as D  # noqa: F401  (kept: bead-grid figures below)

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
# Bottom up from the window's own top face. The LED fires DOWN, so it hangs from the
# board's underside and is the LOWEST thing on the assembly.
FLOOR_NOM  = -71.35                 # window top = motor bay floor; asserted below
AIR_GAP    = 0.30                   # LED face to the PCTG: a print tolerance, not optics
LED_H      = 1.60                   # XL-5050RGBW body (LCSC C7371891, and see fret_light)
BOARD_T    = 1.60
SLOT_CLR   = 0.20                   # board top to the retaining lip
LIP_T      = 1.60                   # 2 beads
# ⚠ THE CEILING IS THE BELT TENSIONERS AT -65.22, measured, not the bay's full height.
# Their lowest feature reaches down to that across y 38.15..47.08 at several stations,
# which is squarely over this channel's -Y half.
TENSIONER_BOT = -65.22


def z_stack():
    """(led_face, board_bot, board_top, lip_bot, lip_top) in world Z."""
    floor = window()[4]
    led = floor + AIR_GAP
    bb = led + LED_H
    bt = bb + BOARD_T
    lb = bt + SLOT_CLR
    return led, bb, bt, lb, lb + LIP_T


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
# ⚠ 38.00, AND THE CONNECTOR IS WHAT SET IT. The board started at 39.30 and 15.90 wide,
# which left the lane 8.00 mm between the LED row's courtyard and the board edge -- and
# the 4-way SH's courtyard is 7.80 across its ways, so it fitted with 0.05 to spare on
# one side. 0.05 is not a gap (see elec/placecheck.py on what that costs). 17.20 wide
# gives the lane 9.30 and every part in it a real margin. Width is ~$0.02 a board here.
BOARD_Y0   = 38.00                  # board's -Y edge
# ⚠ 42.55, MOVED 0.40 OFF THE LED ROW AFTER THE SECOND ROUTE. Everything the drivers
# and the connectors have to talk to is in the LED row, so the gap between the lane's
# courtyards and the row's is the hole every return and every rail tap goes through. At
# 0.45 the router left 3 zone returns and a +24V pad unconnected; 0.85 is what it had
# room for. The lane is 9.30 tall and the parts are 7.0-7.8, so this costs nothing but
# 0.40 of the margin to the board's own edge.
DRV_Y      = 42.55                  # the component lane's centre: drivers, the buck and
                                    # the supply row sit on it, spaced along X
J_Y        = 42.40                  # ...and the two connectors 0.15 further off again:
                                    # their courtyard is 7.80 against the driver's 7.00,
                                    # and their pads are on a 1.00 pitch
BOARD_W    = BOARD_Y1 - BOARD_Y0    # 17.20


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
# ⚠ THE LIPS ARE NARROW ON PURPOSE. The chassis builds world +Z, so a lip is a horizontal
# overhang over the slot: 2.00 mm bridges, and a continuous 16 mm ceiling would sag. Left
# open down the middle, which also lets the drivers' heat out into the bay.
# ⚠ AND A RELIEF GROOVE UNDER THE COMPONENT LANE, WITHOUT WHICH THIS BOARD CANNOT BE
# BUILT. Everything that is not an LED hangs from the board's underside into the trough,
# and the trough is only AIR_GAP + LED_H = 1.90 mm deep -- the LED sets it, because the
# LED has to end up 0.30 off the window. That fits a driver (1.20) and an 0805 (1.45)
# and nothing else: the buck's inductor is 3.00 and the smallest side-entry connector
# that will carry the drop is 2.95 (JST SH, off JST's own drawing -- the PH the rest of
# the instrument uses is 5.50).
#
# So the opaque bottom is relieved 1.50 mm under the lane ONLY. It is 6.50 wide and runs
# the WHOLE length, which is the point: a local pocket would tie the board's layout to an
# X in the chassis, and the user asked for the opposite ("we don't have to align the
# board to the chassis sections"). It takes the bottom prism from 10.50 to 9.00 over a
# 6.50 mm strip, nowhere near the light window, and buys 3.40 mm of headroom.
RELIEF_D   = 1.50
RELIEF_Y0  = 39.20
# ⚠ 46.20, NOT 47.20: the window's -Y edge is at 46.35, and a relief that reached
# past it would take a 0.85 x 1.50 notch out of the top of the LIGHT GUIDE itself.
# Optically it would not matter -- the LED row starts at 47.85 -- but it would put
# a two-material step in the one part of this design that is about light. 7.00 mm
# of relief still covers every part in the lane with margin.
RELIEF_Y1  = 46.20
PART_H_MAX = 1.90 + RELIEF_D        # what may hang below the board, in the lane

WALL_T     = 1.60
WALL_Y0    = 36.10                  # the -Y wall's outer face
SHOULDER   = 1.50                   # how far each shoulder reaches under the board
LIP_REACH  = 1.70                   # how far each lip reaches over it
SLOT_PLAY  = 0.30                   # board edge to the -Y wall's inner face


def _slot_y():
    """(y0, y1) of the slot the board sits in."""
    return BOARD_Y0 - SLOT_PLAY, RAIL_IN


def trough_y():
    """(y0, y1) of the clear trough between the shoulders -- what may hang below."""
    y0, _y1 = _slot_y()
    return y0 + SHOULDER, RAIL_IN - SHOULDER


# ── the boards ────────────────────────────────────────────────────────────────────────
N_LED      = 48
N_SERIES   = 4                      # LEDs per channel; 4 x 3.2 V = 12.8 on the 14 V rail
HALVES     = ("a", "b")
# ⚠ ONE PART NUMBER, BUILT TWICE -- and it is the -X-only install that buys it (user,
# 2026-09-30: "we install this LED before we put the -x endplate on so it can slide in
# from -x"). Both halves go in the same way up and the same way round, one after the
# other through the same mouth, so the +X board is not a mirror of the -X board: it is
# the SAME board, 286.36 further along. A first draft had them as mirror images with
# their connectors at opposite outer ends, which cost a second fab and assembly setup
# and put one harness at the bridge end, 600 mm from the Pi. Sliding both from -X
# deletes all of that.
BOARD_NAME = "foot_led"
BOARD_QTY  = 2
# ⚠ THE STRIP IS A CHAIN, AND -X-ONLY INSERTION IS WHAT MAKES IT ONE. The +X board is
# pushed the full length of the channel first, so its own connector ends up 286 mm inside
# and its cable can never reach the mouth. Nor can it rise out of the channel: below the
# board is the trough, and the trough is under a board everywhere except at a board EDGE.
# So each board carries an IN connector at its -X end and an OUT at its +X end, both in
# the component lane, and a short jumper joins them in the relief groove. Only the -X
# board's IN leaves the instrument.
#
# J_INSET is how far in from each end those two sit. 12.0 is what gives the jumper
# somewhere to be: mouth to mouth across the BUTTED seam is 2 x 12 = 24 mm and the two
# mated plugs take about 8 of it, leaving ~16 mm of free wire lying in the relief groove
# UNDER the two boards. The boards themselves touch, so the LED pitch runs through the
# seam unbroken and the joint costs no light at all.
J_INSET    = 12.0


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
    """(x0, x1) of one board in world X -- exactly its half of the window.

    No tail on either end: the connector is inboard, in the component lane, so the LED
    row runs to within half a pitch of both edges and the seam costs no light at all."""
    x0, x1 = window()[0], window()[1]
    return (x0, seam_x()) if half == "a" else (seam_x(), x1)


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
    _led, _bb, bt, _lb, lip_top = z_stack()
    assert lip_top <= TENSIONER_BOT - 0.5, (
        "the channel's lip tops out at %.2f and the belt tensioners come down to %.2f"
        % (lip_top, TENSIONER_BOT))
    ty0, ty1 = trough_y()
    assert ty0 <= BOARD_Y0 + SHOULDER + 1e-9 and ty1 >= BOARD_Y1 - SHOULDER - 1e-9, (
        "the trough %.2f..%.2f does not leave the board's edges anything to stand on"
        % (ty0, ty1))
    assert BOARD_Y1 <= RAIL_IN, (
        "the board's +Y edge at %.2f is inside the rail at %.2f" % (BOARD_Y1, RAIL_IN))
    assert RELIEF_Y0 >= ty0 and RELIEF_Y1 <= ty1, (
        "the relief groove %.2f..%.2f is not inside the trough %.2f..%.2f -- it would "
        "undercut a shoulder" % (RELIEF_Y0, RELIEF_Y1, ty0, ty1))
    assert RELIEF_D <= window()[4] - window()[5] - 6.0, (
        "a %.2f relief leaves under 6 mm of the bottom prism" % RELIEF_D)
    return u


# ── THE CAD ───────────────────────────────────────────────────────────────────────────
import cadquery as cq                                            # noqa: E402

from .helpers import box_at, heal                                # noqa: E402


def channel():
    """The slot the strip slides into, to be unioned into the chassis bottom.

    Authored in WORLD coordinates, like the fret comb, because that is where the chassis
    works and where it has to land. Runs the WINDOW's length exactly -- the boards'
    tails hang out past both ends into the clear approach, which is also where their
    connectors are, so nothing has to be threaded through a wall."""
    x0, x1 = window()[0], window()[1]
    floor = window()[4]
    _led, board_bot, _bt, lip_bot, lip_top = z_stack()
    sy0, sy1 = _slot_y()
    ty0, ty1 = trough_y()
    xm, xl = (x0 + x1) / 2.0, x1 - x0

    def run(y0, y1, z0, z1):
        return box_at(xl, y1 - y0, z1 - z0, x=xm, y=(y0 + y1) / 2.0, z=(z0 + z1) / 2.0)

    out = run(WALL_Y0, sy0, floor, lip_top)                       # the -Y wall
    out = out.union(run(sy0, ty0, floor, board_bot))              # -Y shoulder
    out = out.union(run(ty1, sy1, floor, board_bot))              # +Y shoulder
    out = out.union(run(sy0, sy0 + LIP_REACH + SLOT_PLAY, lip_bot, lip_top))
    out = out.union(run(sy1 - LIP_REACH - (RAIL_IN - BOARD_Y1), sy1, lip_bot, lip_top))
    return heal(out)


def slot_cut():
    """The volume the strip and its parts occupy -- CUT from the chassis before the
    channel is unioned back in.

    ⚠ THE CHANNEL IS ADDITIVE, SO IT CANNOT MAKE ROOM BY ITSELF. Unioning walls and lips
    onto the bottom says nothing about what was already standing in the slot, and the
    motor bay's own structure comes in somewhere below y 40. Cutting the envelope first
    and building the channel into the hole makes the board's space a fact rather than a
    hope -- and it is also the INSERTION CORRIDOR, which runs the channel's whole length
    because that is how the board gets in."""
    x0, x1 = window()[0], window()[1]
    floor = window()[4]
    _led, _bb, _bt, lip_bot, _lt = z_stack()
    sy0, sy1 = _slot_y()
    return box_at(x1 - x0, sy1 - sy0, lip_bot - floor,
                  x=(x0 + x1) / 2.0, y=(sy0 + sy1) / 2.0, z=(floor + lip_bot) / 2.0)


def relief():
    """The groove under the component lane -- CUT from the chassis, not added to it."""
    x0, x1 = window()[0], window()[1]
    top = window()[4]
    return box_at(x1 - x0, RELIEF_Y1 - RELIEF_Y0, RELIEF_D + 0.02,
                  x=(x0 + x1) / 2.0, y=(RELIEF_Y0 + RELIEF_Y1) / 2.0,
                  z=top - RELIEF_D / 2.0 + 0.01)


def _led_refs():
    from . import board_geom as BG
    return [f["ref"] for f in BG.load(BOARD_NAME)["footprints"]
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
    """The PCB and every part on it EXCEPT the LEDs, as routed -- ONE board, placed twice."""
    from . import board_geom as BG
    return _placed(half, BG.solid(BOARD_NAME, skip=_led_refs()))


def leds(half):
    """The strip's LEDs, as their routed bodies -- their own part so they read as lit."""
    from . import board_geom as BG
    return _placed(half, BG.bodies(BOARD_NAME, _led_refs()))


def routed():
    """Has the board been routed and exported yet?

    ⚠ THE FIRST RUN OF A FRESH CHECKOUT HAS NO BOARD. elec/geom/<board>.geom.json is
    written by export_geom AFTER a route, and elec/foot_led.py imports THIS module to
    lay that board out -- so on a tree where the geometry has never been exported, asking
    build.py for the strip is asking for a file that the build itself is a prerequisite
    of. ui_panel records the same cycle and breaks it with a late import; that is not
    enough here, because the file can be legitimately absent rather than merely
    late. So the CAD leaves the strip out and says why, instead of failing the build."""
    import os
    from . import board_geom as BG
    return os.path.isfile(os.path.join(BG.GEOM_DIR, BOARD_NAME + ".geom.json"))


def parts():
    """[(name, solid)] for build.py -- one board, placed twice."""
    if not routed():
        print("  (no %s.geom.json yet -- the foot strip is left out of this build; "
              "route and export it, see elec/foot_led.py)" % BOARD_NAME)
        return []
    return [(n, f(h)) for h in HALVES
            for n, f in (("foot_pcb_%s" % h, pcb), ("foot_led_%s" % h, leds))]
