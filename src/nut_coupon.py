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
# VARIANT B — ONE SHARED ROD ALONG Y instead of ten posts along Z (user)
# ════════════════════════════════════════════════════════════════════════════
# This is the better idea, and it has precedent twice over: it is the TUNER CROSS
# SHAFT every keyless steel already uses, and this instrument already buys a shared
# O3 shaft spanning all ten strings for the bridge axle. Ten posts become one rod.
#
# THE COMB IS NOT OPTIONAL. Every string pulls on the same rod, so an unsupported
# O6 spanning the string field carries 17.2 N/mm and sags 0.94 mm in the middle —
# the middle strings would simply go flat. Supported by a printed web between each
# pair of strings the same span sags 0.00003 mm. So the rod threads a COMB, exactly
# as the bridge axle threads its nine comb fingers.
#
# THE WRAP MARCHES ALONG THE ROD. Winding about Y means each turn advances the
# string along Y by its own diameter: 1.11 mm for the .014, 5.56 mm for the .070,
# inside a 9.5 lane. That is what sets the comb web thickness, and it has a bonus —
# the string leaves its wrap OFFSET from where it arrived, so the clamps land
# between the string lanes instead of on them. The two-row clamp stagger the
# current nut block needs to give its inserts pitch comes free.
ROD_D  = 6.0                        # the shared rod: O6 ground shaft, ONE part
ROD_X  = POST_X
ROD_Z  = -1.0                       # rod centre: strings arrive at -g/2 and touch
                                    # its +X side. One height for every gauge —
                                    # they differ by 0.7 across the set, small
                                    # against O6, so tangency shifts and nothing else


def _y_b(n: int) -> float:
    return _y(n)


def _adv(g: float) -> float:
    """How far this string's wrap marches along the rod."""
    return TURNS * _wrap_pitch(g)


def _string_rod(n: int):
    """One string on the shared rod: in from the bridge, 2.5 turns about Y, out to
    a clamp that sits OFFSET by the wrap's own march."""
    g = D.STRING_GAUGE[GAUGE_IDX[n]]
    y0, r = _y_b(n), g / 2.0
    p = _wrap_pitch(g)
    h = TURNS * p
    hr = ROD_D / 2.0 + r + CONTACT_CLR

    def seg(a, b):
        va, vb = cq.Vector(*a), cq.Vector(*b)
        return cq.Workplane("XY").add(
            cq.Solid.makeCylinder(r, (vb - va).Length, va, vb - va))

    # in from the bridge at its own plane, HORIZONTAL over the break dowel, and
    # only then down to the rod's +X face. Descending from the start clipped the
    # dowel it is supposed to break over — the dowel sets the scale, so the string
    # has to leave it level.
    out = seg((X_FRONT + 14.0, y0, -r), (DOWEL_X, y0, -r))
    out = out.union(seg((DOWEL_X, y0, -r), (ROD_X + hr, y0, ROD_Z)))
    # THE WRAP — a helix about Y. makeHelix builds about Z, so it is rotated -90
    # about X, which carries +Z onto +Y.
    helix = cq.Wire.makeHelix(pitch=p, height=h, radius=hr)
    coil = (cq.Workplane("XZ").center(hr, 0).circle(r)
            .sweep(cq.Workplane("XY").add(helix), isFrenet=True))
    out = out.union(coil.rotate((0, 0, 0), (1, 0, 0), -90.0)
                        .translate((ROD_X, y0, ROD_Z)))
    # 2.5 turns lands it on the -X side, one march further along Y, aimed at the clamp
    y1 = y0 + h
    out = out.union(seg((ROD_X - hr, y1, ROD_Z), (CLAMP_X, y1, ROD_Z)))
    out = out.union(seg((CLAMP_X, y1, ROD_Z), (X_BACK - 3.0, y1, ROD_Z)))
    return out


def _hardware_rod(n: int):
    """Per string: the break dowel, the anvil and the clamp — all that is left,
    because the ten posts have become one rod (emitted once, in demo_parts_rod)."""
    g = D.STRING_GAUGE[GAUGE_IDX[n]]
    y1 = _y_b(n) + _adv(g)
    out = [(f"rodnut_break_dowel_{n}",
            cyl_y(PIN_D, PIN_L, y0=_y_b(n) - PIN_L / 2.0, x=DOWEL_X,
                  z=-g - PIN_D / 2.0 - CONTACT_CLR))]
    out.append((f"rodnut_anvil_{n}",
                cyl_y(PIN_D, PIN_L, y0=y1 - PIN_L / 2.0, x=CLAMP_X,
                      z=ROD_Z - g / 2.0 - PIN_D / 2.0 - CONTACT_CLR)))
    out.append((f"rodnut_insert_{n}",
                _insert(M4).translate((CLAMP_X, y1, BOSS_Z1))))
    _tip = ROD_Z + g / 2.0 + CONTACT_CLR
    out.append((f"rodnut_screw_{n}",
                _screw(M4, BOSS_Z1 - _tip).translate((CLAMP_X, y1, BOSS_Z1))))
    return out


def block_rod():
    """The printed body for the shared-rod scheme: slab, the COMB the rod threads,
    and the clamp boss — with a bay opened per string for its wrap."""
    w = box_at(X_FRONT - X_BACK, 2 * HW, SLAB_Z1 - SLAB_Z0,
               x=(X_BACK + X_FRONT) / 2.0, y=0.0, z=(SLAB_Z0 + SLAB_Z1) / 2.0)
    w = w.union(box_at(10.0, 2 * HW, BOSS_Z1 - SLAB_Z1,
                       x=CLAMP_X, y=0.0, z=(SLAB_Z1 + BOSS_Z1) / 2.0))
    # the COMB: a rib block across the rod line. Cutting a bay per wrap leaves the
    # material between bays standing as the fingers that carry the rod.
    w = w.union(box_at(ROD_D + 8.0, 2 * HW, 6.0, x=ROD_X, y=0.0, z=SLAB_Z1 + 1.0))
    w = w.cut(cyl_y(ROD_D + 0.4, 4 * HW, y0=-2 * HW, x=ROD_X, z=ROD_Z))
    for n, gi in enumerate(GAUGE_IDX):
        g = D.STRING_GAUGE[gi]
        y0 = _y_b(n)
        h = _adv(g)
        y1 = y0 + h
        hr = ROD_D / 2.0 + g / 2.0 + CONTACT_CLR
        w = w.cut(cyl_y(PIN_D + 0.4, PIN_L + 0.4, y0=y0 - (PIN_L + 0.4) / 2.0,
                        x=DOWEL_X, z=-g - PIN_D / 2.0 - CONTACT_CLR))
        # the wrap's own bay — this is what leaves the comb fingers behind
        w = w.cut(cyl_y(2 * (hr + g / 2.0 + 0.4), h + g + 0.8,
                        y0=y0 - g / 2.0 - 0.4, x=ROD_X, z=ROD_Z))
        # ...and the lane the string arrives down, through the comb's +X face
        w = w.cut(box_at(X_FRONT - ROD_X, g + 2.0, (SLAB_Z1 + 6.5) - (ROD_Z - g),
                         x=(ROD_X + X_FRONT) / 2.0, y=y0,
                         z=((ROD_Z - g) + SLAB_Z1 + 6.5) / 2.0))
        # channel out to the clamp, at the OFFSET y the wrap delivers it to
        z_f = ROD_Z - g / 2.0 - PIN_D - CONTACT_CLR
        z_c1 = max(SLAB_Z1, ROD_Z + g / 2.0 + 0.5)
        w = w.cut(box_at(ROD_X - (X_BACK - 4.0), g + 2.0, z_c1 - z_f,
                         x=(ROD_X + X_BACK - 4.0) / 2.0, y=y1,
                         z=(z_f + z_c1) / 2.0))
        w = w.cut(cyl_y(PIN_D + 0.4, PIN_L + 0.4, y0=y1 - (PIN_L + 0.4) / 2.0,
                        x=CLAMP_X, z=ROD_Z - g / 2.0 - PIN_D / 2.0 - CONTACT_CLR))
        w = w.cut(cyl(INSERT_D, INSERT_L + 0.2, z=BOSS_Z1 - INSERT_L)
                  .translate((CLAMP_X, y1, 0)))
        w = w.cut(cyl(SCREW_D + 0.4, 40.0, z=ROD_Z - 1.0)
                  .translate((CLAMP_X, y1, 0)))
    return w


def demo_parts_rod():
    """[(name, solid)] — the shared-rod variant. ONE rod, not ten posts."""
    out = [("rodnut_block", block_rod())]
    out.append(("rodnut_rod", cyl_y(ROD_D, 2 * HW + 8.0, y0=-HW - 4.0,
                                    x=ROD_X, z=ROD_Z)))
    for n in range(len(GAUGE_IDX)):
        out += _hardware_rod(n)
        out.append((f"rodnut_string_{n}", _string_rod(n)))
    return out
