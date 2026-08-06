"""DEMO of the proposed string termination at the nut — the WRAP POST scheme.

Not a printed part and not (yet) the real nut block: a teaching model, parked off
the +X end of the instrument beside the other coupons so it rebuilds every time and
cannot drift from dimensions.py.

WHAT IT SHOWS, left to right along the string:

    bridge  ->  BREAK DOWEL  ->  WRAP POST (2.5 turns)  ->  CLAMP  ->  tail

  * The BREAK DOWEL (O2, existing part) is unchanged — it is the scale endpoint,
    and it sits at a GAUGED height so every string's TOP lands on one plane.
  * The WRAP POST is the whole proposal: a O6 hardened dowel the string winds
    2.5 turns around before it reaches the clamp. Each turn multiplies the grip
    the post itself provides (capstan / Euler-Eytelwein, T = T0.e^-mu.theta), so
    the clamp behind it only has to hold what is LEFT:

        no wrap   147 N at the clamp  ->  490 N of clamp force  ->  39 MPa on the plastic
        2.5 turns  14 N at the clamp  ->   46 N of clamp force  ->  3.7 MPa

    That is the entire point. The clamp was never the wrong mechanism; it was
    being asked for 490 N. Nothing here is a new bought part except the post, and
    a post is the same for every gauge — which is what keeps it off the
    per-instrument, per-string-set cost the user rejected machining over.
  * The CLAMP is the EXISTING hardware (M4 cup-tip set screw in a brass heat-set
    insert), now working at a seventh of the load, with an optional second O2
    dowel under the string as a steel ANVIL so the pinch is metal-on-metal.

THREE GAUGES ARE DRAWN — .014, .030 and .070, the thinnest, a middle and the
fattest wound string — because the claim being illustrated is that ONE post size
and ONE clamp serve every gauge. Watch the string tops: they all leave the break
dowel on the same plane, and each one simply winds down its own post by its own
diameter.

Local frame matches nut_block: X = 0 at the break edge and +X toward the bridge,
Z = 0 at the string-top plane, Y across the strings.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from cadkit.fasteners import M4, screw as _screw, insert as _insert
from .helpers import box_at, cyl, cyl_y


# ── what the demo draws ──────────────────────────────────────────────────────
GAUGE_IDX = (1, 5, 9)               # .014, .030, .070 — thin / middle / fattest wound
PITCH     = D.STRING_PITCH          # 9.5, the real spacing (so the packing is honest)

POST_D    = 6.0                     # the proposed wrap post: O6 hardened dowel.
                                    # O6 keeps the bend radius near a guitar tuner
                                    # post's; O3 would be sharp on the .070
TURNS     = 2.5                     # 2.5, not 2: a half-turn puts the tail out the
                                    # -X side, pointing at the clamp. At 2 turns it
                                    # would exit on the +X side and have to cross
                                    # back past its own post
PIN_D     = D.NUT_PIN_D             # O2 break dowel + O2 anvil — the SAME part number
PIN_L     = D.NUT_PIN_L             # (BOM: bump the existing line 10 -> 20)

DOWEL_X   = 0.0                     # break edge = the scale "0"
POST_X    = -9.0                    # post centre
CLAMP_X   = -16.0                   # clamp / anvil
X_BACK    = -21.0                   # block -X face (matches nut_block's prism)
X_FRONT   = 6.0

HW        = PITCH * len(GAUGE_IDX) / 2.0 + 3.0     # block half-width in Y
SLAB_Z0   = -14.0                                  # block underside
SLAB_Z1   = -2.0                                   # block top (strings run above it)
BOSS_Z1   = 9.0                                    # clamp boss top (hosts the insert)
POST_Z1   = 2.0                                    # post top — PROUD of the string plane
# The string TOUCHES the post, the dowels and the screw tip — those are the
# working contacts. Drawn exactly tangent they are boolean noise (one wrap
# reported 12 mm3 against its own post), so every contact carries this hair of
# air. It is a drawing convention, not a fit.
CONTACT_CLR = 0.05

INSERT_D  = D.NUT_INSERT_D
INSERT_L  = D.NUT_INSERT_L
SCREW_D   = D.NUT_SCREW_D


def _y(n: int) -> float:
    return (n - (len(GAUGE_IDX) - 1) / 2.0) * PITCH


def _wrap_pitch(g: float) -> float:
    """Axial rise per turn: the string's own diameter plus a whisker, so the turns
    lie against each other without crossing. Crossing is the failure the steel
    forum warns about — under tension a string can cut itself in two."""
    return g * 1.25


def _string(n: int):
    """One string, drawn as it actually runs: in from the bridge, over the break
    dowel, 2.5 turns down the post, out to the clamp, and a stub of tail."""
    g = D.STRING_GAUGE[GAUGE_IDX[n]]
    y, r = _y(n), g / 2.0
    zc = -r                                    # centre, so the TOP sits on z = 0
    p = _wrap_pitch(g)
    h = TURNS * p
    hr = POST_D / 2.0 + r + CONTACT_CLR        # helix radius: string wraps the post

    def seg(a, b):
        va, vb = cq.Vector(*a), cq.Vector(*b)
        return cq.Workplane("XY").add(
            cq.Solid.makeCylinder(r, (vb - va).Length, va, vb - va))

    # in from the bridge, over the break dowel, on to the post's +X tangent
    out = seg((X_FRONT + 14.0, y, zc), (POST_X + hr, y, zc))

    # THE WRAP. makeHelix starts at angle 0 (+X side) and climbs, so building it
    # h tall and dropping it by h puts its TOP end exactly where the string arrives
    # — and 2.5 turns lands the far end at 180 deg, on the -X side, aimed at the
    # clamp. Same sweep recipe cadkit/threads.py uses for real threads.
    helix = cq.Wire.makeHelix(pitch=p, height=h, radius=hr)
    coil = (cq.Workplane("XZ").center(hr, 0).circle(r)
            .sweep(cq.Workplane("XY").add(helix), isFrenet=True))
    out = out.union(coil.translate((POST_X, y, zc - h)))

    # off the bottom of the wrap (-X side), into the clamp, then the tail
    z_end = zc - h
    out = out.union(seg((POST_X - hr, y, z_end), (CLAMP_X, y, z_end)))
    out = out.union(seg((CLAMP_X, y, z_end), (X_BACK - 3.0, y, z_end)))
    return out


def _hardware(n: int):
    """The metal that touches this string: break dowel, post, anvil, screw, insert."""
    g = D.STRING_GAUGE[GAUGE_IDX[n]]
    y = _y(n)
    h = TURNS * _wrap_pitch(g)
    z_end = -g / 2.0 - h
    out = []
    # BREAK DOWEL — gauged so the string TOP lands on z = 0 (this is the existing
    # scheme, unchanged; it is why one flat clamp face can serve every gauge)
    out.append((f"nutdemo_break_dowel_{n}",
                cyl_y(PIN_D, PIN_L, y0=y - PIN_L / 2.0, x=DOWEL_X,
                      z=-g - PIN_D / 2.0 - CONTACT_CLR)))
    # WRAP POST — the new part. Same O6 for every gauge. It has to stand PROUD of
    # the string-top plane: the first turn arrives at z = -g/2, so a post topping
    # out below 0 would have the thin string wrapping thin air (it did, first pass).
    out.append((f"nutdemo_post_{n}",
                cyl(POST_D, POST_Z1 - (z_end - 4.0), z=z_end - 4.0)
                .translate((POST_X, y, 0))))
    # ANVIL — optional second O2 dowel so the pinch is metal-on-metal
    out.append((f"nutdemo_anvil_{n}",
                cyl_y(PIN_D, PIN_L, y0=y - PIN_L / 2.0, x=CLAMP_X,
                      z=z_end - g / 2.0 - PIN_D / 2.0 - CONTACT_CLR)))
    # the EXISTING clamp, drawn with CADKIT's own dummies rather than bare
    # cylinders — so the set screw shows its 2 mm hex drive and the insert its real
    # knurled form. A hand-rolled cylinder hid the one feature that tells you which
    # end you turn.
    out.append((f"nutdemo_insert_{n}",
                _insert(M4).translate((CLAMP_X, y, BOSS_Z1))))
    _tip = z_end + g / 2.0 + CONTACT_CLR          # cup tip, resting on the string
    out.append((f"nutdemo_screw_{n}",
                _screw(M4, BOSS_Z1 - _tip).translate((CLAMP_X, y, BOSS_Z1))))
    return out


def block():
    """The printed body — slab plus the clamp boss, with seats cut for the dowels,
    the posts and the inserts. PETG-GF, exactly as the real nut block."""
    w = box_at(X_FRONT - X_BACK, 2 * HW, SLAB_Z1 - SLAB_Z0,
               x=(X_BACK + X_FRONT) / 2.0, y=0.0, z=(SLAB_Z0 + SLAB_Z1) / 2.0)
    w = w.union(box_at(10.0, 2 * HW, BOSS_Z1 - SLAB_Z1,
                       x=CLAMP_X, y=0.0, z=(SLAB_Z1 + BOSS_Z1) / 2.0))
    for n, gi in enumerate(GAUGE_IDX):
        g = D.STRING_GAUGE[gi]
        y = _y(n)
        h = TURNS * _wrap_pitch(g)
        z_end = -g / 2.0 - h                      # string centre where it leaves the wrap
        z_f = z_end - g / 2.0 - PIN_D - CONTACT_CLR     # channel floor = the anvil's seat
        # break-dowel seat + post bore
        w = w.cut(cyl_y(PIN_D + 0.4, PIN_L + 0.4, y0=y - (PIN_L + 0.4) / 2.0,
                        x=DOWEL_X, z=-g - PIN_D / 2.0 - CONTACT_CLR))
        w = w.cut(cyl(POST_D + 0.4, 40.0, z=z_end - 6.0).translate((POST_X, y, 0)))
        # ROOM FOR THE WRAP: an annulus around the post wide enough for the coil,
        # bounded to the wrap's own Z band. The first pass used a big box here and
        # it quietly ate the clamp boss the insert lives in — hence the boss-shaped
        # hole in the middle of the demo.
        w = w.cut(cyl(POST_D + 2 * (g + 1.0), (SLAB_Z1 + 2.0) - (z_end - 1.0),
                      z=z_end - 1.0).translate((POST_X, y, 0)))
        # CHANNEL for the run out to the clamp and the tail. Its floor is where the
        # anvil dowel sits, so the dowel is supported rather than floating.
        #
        # The top has to clear the STRING, not the slab. A thin string leaves its
        # wrap barely below the string plane — above SLAB_Z1 — so a channel that
        # stopped at the slab top left the .014 running straight through the clamp
        # boss. Take whichever is higher.
        z_c1 = max(SLAB_Z1, z_end + g / 2.0 + 0.5)
        w = w.cut(box_at(POST_X - (X_BACK - 4.0), g + 2.0, z_c1 - z_f,
                         x=(POST_X + X_BACK - 4.0) / 2.0, y=y,
                         z=(z_f + z_c1) / 2.0))
        # ...and the O2 anvil is 4 long against a channel only g+2 wide, so its ends
        # would bury in the channel walls. Give it its own pocket.
        w = w.cut(cyl_y(PIN_D + 0.4, PIN_L + 0.4, y0=y - (PIN_L + 0.4) / 2.0,
                        x=CLAMP_X,
                        z=z_end - g / 2.0 - PIN_D / 2.0 - CONTACT_CLR))
        # insert pocket + screw bore, down through the boss to the string
        w = w.cut(cyl(INSERT_D, INSERT_L + 0.2, z=BOSS_Z1 - INSERT_L)
                  .translate((CLAMP_X, y, 0)))
        w = w.cut(cyl(SCREW_D + 0.4, 40.0, z=z_end - 1.0).translate((CLAMP_X, y, 0)))
    return w


def demo_parts():
    """[(name, solid)] — the block, the metal, and the three strings."""
    out = [("nutdemo_block", block())]
    for n in range(len(GAUGE_IDX)):
        out += _hardware(n)
        out.append((f"nutdemo_string_{n}", _string(n)))
    return out


# ════════════════════════════════════════════════════════════════════════════
# VARIANT B — ONE SHARED ROD ALONG Y, designed around the INSTALL (user)
# ════════════════════════════════════════════════════════════════════════════
# The user's idea, and the better one: it is the TUNER CROSS SHAFT every keyless
# steel already uses, and this instrument already buys a shared O3 shaft spanning
# all ten strings for the bridge axle. Ten bought posts collapse to one.
#
# THE INSTALL IS THE DESIGN DRIVER (user). Working from the +X side, you:
#
#     push the tip UNDER the rod and around  ->  grab it as it comes out the top
#     pull the slack through                 ->  push under again, grab, pull
#     push under a third time                ->  and this time it leaves by the
#                                                EXIT HOLE, out to the clamp
#
# Three pushes = 2.5 turns, which is exactly the wrap the capstan sums wanted. The
# winding sense is right-handed about +Y, and that is what sends the tip UNDER the
# rod first rather than over it — probed off the curve, not assumed.
#
# What the install costs the geometry, in the order the user raised it:
#
#  1. THREADING ROOM. The bay is a full BAY_R annulus round the rod and OPEN TO THE
#     TOP, so a stiff .070 tip can be pushed round and then grabbed. A wrap-tight
#     bay would be unthreadable.
#  2. ENTRY ROOM. The +X approach lane is open for the whole height of the bay, so
#     the string can be presented on each of the three passes.
#  3. THE EXIT HOLE IS GATED BY THE CLAMP SCREW. This is the subtle one and it is
#     worth the trouble: the string passes the -X side of the rod THREE times (at
#     0.5, 1.5 and 2.5 turns) and only the last should find the hole. The earlier
#     two are 2p and 1p away in Y — and at the bass end 1p is smaller than the
#     hole's own half width, so an early pass really can catch it. With the screw
#     wound IN its shank fills the passage and the hole is not there at all. On the
#     final pass you back the screw out, the hole opens, the tail goes through, and
#     winding the screw down clamps it. One screw, two jobs, and the clunky "pull it
#     back out and try again" the user wanted to avoid cannot happen.
ROD_D  = 6.0                        # the shared rod: O6 ground shaft, ONE part
ROD_X  = POST_X
ROD_Z  = -1.0                       # rod centre; strings arrive at -g/2 and meet
                                    # its +X face. One height for every gauge
BAY_R  = 6.0                        # threading annulus — 3 clear of the rod
EXIT_X = ROD_X - BAY_R              # -15: the wall the exit hole pierces
GATE_X = -17.5                      # clamp screw. It crosses the exit passage, so
                                    # wound IN it is a GATE, and wound down on the
                                    # string it is the CLAMP
X_BACK_B = -22.0
WRAP_F_B = 1.15                     # turns lie close (they must not cross) while
                                    # still leaving a lane for the comb finger
# COMB FINGERS ONLY WHERE THERE IS ROOM. Every string pulls on the same rod, so an
# unsupported O6 across the field sags 0.94 mm at mid-span and the middle strings go
# flat. But support every THIRD string already holds it to 0.002 mm — and that
# freedom matters, because a .070's wrap eats 8.9 of its 9.5 lane while a .014's
# eats 3.4. So the fingers live in the TREBLE lanes where the wrap is narrow, and
# the bass end carries none and needs none.
FINGER_AFTER = (0,)                 # demo: one finger, in the thin string's gap
FINGER_T = 2.4                      # 3 beads


def _adv(g: float) -> float:
    """How far this string's wrap marches along the rod: one diameter per turn."""
    return TURNS * WRAP_F_B * g


def _string_rod(n: int):
    """One string on the shared rod, drawn along the path the install describes."""
    g = D.STRING_GAUGE[GAUGE_IDX[n]]
    y0, r = _y(n), g / 2.0
    p = WRAP_F_B * g
    h = TURNS * p
    hr = ROD_D / 2.0 + r + CONTACT_CLR

    def seg(a, b):
        va, vb = cq.Vector(*a), cq.Vector(*b)
        return cq.Workplane("XY").add(
            cq.Solid.makeCylinder(r, (vb - va).Length, va, vb - va))

    # in from the bridge, LEVEL over the break dowel (the dowel is the scale, so
    # the string has to leave it flat), then down to the rod's +X face
    out = seg((X_FRONT + 14.0, y0, -r), (DOWEL_X, y0, -r))
    out = out.union(seg((DOWEL_X, y0, -r), (ROD_X + hr, y0, ROD_Z)))
    # THE WRAP — right-handed about +Y, which sends the tip UNDER the rod first.
    # makeHelix builds about Z; -90 about X carries +Z onto +Y.
    helix = cq.Wire.makeHelix(pitch=p, height=h, radius=hr)
    coil = (cq.Workplane("XZ").center(hr, 0).circle(r)
            .sweep(cq.Workplane("XY").add(helix), isFrenet=True))
    out = out.union(coil.rotate((0, 0, 0), (1, 0, 0), -90.0)
                        .translate((ROD_X, y0, ROD_Z)))
    # ...and out through the EXIT HOLE, one march further along Y
    y1 = y0 + h
    out = out.union(seg((ROD_X - hr, y1, ROD_Z), (X_BACK_B - 3.0, y1, ROD_Z)))
    return out


def _hardware_rod(n: int):
    """Per string: break dowel, anvil, and the gate/clamp screw with its insert."""
    g = D.STRING_GAUGE[GAUGE_IDX[n]]
    y1 = _y(n) + _adv(g)
    out = [(f"rodnut_break_dowel_{n}",
            cyl_y(PIN_D, PIN_L, y0=_y(n) - PIN_L / 2.0, x=DOWEL_X,
                  z=-g - PIN_D / 2.0 - CONTACT_CLR))]
    out.append((f"rodnut_anvil_{n}",
                cyl_y(PIN_D, PIN_L, y0=y1 - PIN_L / 2.0, x=GATE_X,
                      z=ROD_Z - g / 2.0 - PIN_D / 2.0 - CONTACT_CLR)))
    out.append((f"rodnut_insert_{n}",
                _insert(M4).translate((GATE_X, y1, BOSS_Z1))))
    _tip = ROD_Z + g / 2.0 + CONTACT_CLR          # resting on the string = CLAMPED
    out.append((f"rodnut_screw_{n}",
                _screw(M4, BOSS_Z1 - _tip).translate((GATE_X, y1, BOSS_Z1))))
    return out


def block_rod():
    """The printed body: slab, the comb the rod threads, the open threading bay,
    the +X entry lanes, and the gated exit passages."""
    w = box_at(X_FRONT - X_BACK_B, 2 * HW, SLAB_Z1 - SLAB_Z0,
               x=(X_BACK_B + X_FRONT) / 2.0, y=0.0, z=(SLAB_Z0 + SLAB_Z1) / 2.0)
    w = w.union(box_at(9.0, 2 * HW, BOSS_Z1 - SLAB_Z1,
                       x=GATE_X, y=0.0, z=(SLAB_Z1 + BOSS_Z1) / 2.0))
    # the comb block the rod threads
    w = w.union(box_at(2 * BAY_R, 2 * HW, (ROD_Z + BAY_R) - SLAB_Z1,
                       x=ROD_X, y=0.0, z=(SLAB_Z1 + ROD_Z + BAY_R) / 2.0))
    w = w.cut(cyl_y(ROD_D + 0.4, 4 * HW, y0=-2 * HW, x=ROD_X, z=ROD_Z))

    # ONE open bay across the strings, then the fingers put BACK. Cutting the bay
    # first and restoring fingers is what makes "fingers only where there is room"
    # expressible at all; a bay-per-string leaves the bass lanes no wall to build.
    w = w.cut(box_at(2 * BAY_R, 2 * HW, (SLAB_Z1 + 12.0) - (ROD_Z - BAY_R),
                     x=ROD_X, y=0.0, z=((ROD_Z - BAY_R) + SLAB_Z1 + 12.0) / 2.0))
    for i in FINGER_AFTER:
        g = D.STRING_GAUGE[GAUGE_IDX[i]]
        yf = _y(i) + _adv(g) + (PITCH - _adv(g)) / 2.0      # mid-gap
        fin = box_at(2 * BAY_R, FINGER_T, (ROD_Z + BAY_R) - SLAB_Z0,
                     x=ROD_X, y=yf, z=(SLAB_Z0 + ROD_Z + BAY_R) / 2.0)
        w = w.union(fin.cut(cyl_y(ROD_D + 0.4, 4 * HW, y0=-2 * HW,
                                  x=ROD_X, z=ROD_Z)))

    for n, gi in enumerate(GAUGE_IDX):
        g = D.STRING_GAUGE[gi]
        y0 = _y(n)
        y1 = y0 + _adv(g)
        w = w.cut(cyl_y(PIN_D + 0.4, PIN_L + 0.4, y0=y0 - (PIN_L + 0.4) / 2.0,
                        x=DOWEL_X, z=-g - PIN_D / 2.0 - CONTACT_CLR))
        # ENTRY LANE — open the full bay height, so the string can be presented on
        # each of the three passes
        w = w.cut(box_at(X_FRONT - ROD_X, g + 2.0,
                         (SLAB_Z1 + 12.0) - (ROD_Z - g),
                         x=(ROD_X + X_FRONT) / 2.0, y=y0,
                         z=((ROD_Z - g) + SLAB_Z1 + 12.0) / 2.0))
        # EXIT PASSAGE — a HOLE, not an open channel: it has to be something the
        # screw can plug. Its FLOOR is exactly where the screw tip lands (= the
        # anvil top); centring it on the rod instead left a 0.35 slot underneath
        # the tip, which the gate check caught and which is precisely the gap a
        # thin string would find on an early pass.
        _floor = ROD_Z - g / 2.0 - CONTACT_CLR
        w = w.cut(box_at(EXIT_X - (X_BACK_B - 4.0), g + 0.8, g + 0.8,
                         x=(EXIT_X + X_BACK_B - 4.0) / 2.0, y=y1,
                         z=_floor + (g + 0.8) / 2.0))
        w = w.cut(cyl_y(PIN_D + 0.4, PIN_L + 0.4, y0=y1 - (PIN_L + 0.4) / 2.0,
                        x=GATE_X, z=ROD_Z - g / 2.0 - PIN_D / 2.0 - CONTACT_CLR))
        w = w.cut(cyl(INSERT_D, INSERT_L + 0.2, z=BOSS_Z1 - INSERT_L)
                  .translate((GATE_X, y1, 0)))
        w = w.cut(cyl(SCREW_D + 0.4, 40.0, z=ROD_Z - 2.0).translate((GATE_X, y1, 0)))
    return w


def gate_check():
    """Does the screw, wound fully IN, actually close the exit passage?

    The whole anti-clunk trick rests on this, so it gets measured rather than
    asserted: drop the screw to the passage floor and subtract it from the
    passage's own cross-section. Anything left over is a gap a thin string could
    still find on an early pass.
    """
    out = []
    for n, gi in enumerate(GAUGE_IDX):
        g = D.STRING_GAUGE[gi]
        y1 = _y(n) + _adv(g)
        floor = ROD_Z - g / 2.0 - CONTACT_CLR
        shut = cyl(SCREW_D - 0.4, BOSS_Z1 - floor, z=floor).translate((GATE_X, y1, 0))
        window = box_at(1.0, g + 0.8, g + 0.8, x=GATE_X, y=y1,
                        z=floor + (g + 0.8) / 2.0)
        out.append((gi, round(window.val().Volume(), 3),
                    round(window.cut(shut).val().Volume(), 3)))
    return out


def demo_parts_rod():
    """[(name, solid)] — the shared-rod variant. ONE rod, not ten posts."""
    out = [("rodnut_block", block_rod())]
    out.append(("rodnut_rod", cyl_y(ROD_D, 2 * HW + 8.0, y0=-HW - 4.0,
                                    x=ROD_X, z=ROD_Z)))
    for n in range(len(GAUGE_IDX)):
        out += _hardware_rod(n)
        out.append((f"rodnut_string_{n}", _string_rod(n)))
    return out
