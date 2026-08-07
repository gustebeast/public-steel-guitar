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
POST_X    = -11 * D.BEAD            # -8.8 post centre
CLAMP_X   = -16.0                   # clamp / anvil
X_BACK    = -26 * D.BEAD            # -20.8 block -X face (~nut_block's prism)
X_FRONT   = 8 * D.BEAD              # 6.4

HW        = PITCH * len(GAUGE_IDX) / 2.0 + 4 * D.BEAD   # block half-width in Y
SLAB_Z0   = -18 * D.BEAD                           # -14.4 block underside
SLAB_Z1   = -3 * D.BEAD                            # -2.4 block top (strings run above it)
BOSS_Z1   = 12 * D.BEAD                            # 9.6 clamp boss top (hosts the insert)
POST_Z1   = 3 * D.BEAD                             # 2.4 post top — PROUD of the string plane
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
# VARIANT B — ONE SHARED ROD ALONG Y, on the CHANGER'S OWN SHAFT (user)
# ════════════════════════════════════════════════════════════════════════════
# The user's idea, and the better one: it is the TUNER CROSS SHAFT every keyless
# steel already uses. Ten bought posts collapse to one — and to the SAME one the
# +X changer already buys, which is the part of it that pays twice.
#
# THE ROD IS O3, the bridge axle's own g6/h6 precision shaft, cut to a second
# length. The first cut of this demo used O6, which was not a part this project
# buys at all (the user spotted that). What O3 costs and buys, measured:
#
#     rod     bend strain on the .070     sag per 9.5 span     rod bending stress
#     O6              22.9%                   0.00003 mm            6 MPa
#     O3              37.2%  (1.63x)          0.00046 mm           48 MPa
#     O1.5            54.2%  (2.37x)          0.00729 mm          388 MPa
#
# O1.5 is the one to avoid: 2.4x O6's bend on the fattest wound string, on a rod
# whose own bending stress has climbed 8x. O3 is the sweet spot — the bend is
# worse than a guitar tuner post's but the rod is a part we already own, and
# halving the rod also shrinks the threading bay by 3 mm, which is what finally
# brings the whole termination inside the endplate's X budget.
#
# HONEST RISK: wrap-area breakage is a KNOWN pedal-steel failure (the steel forum
# reports .011s cracking at the wrap at 28-33 lbf, and this instrument runs
# 26-33 lbf), and this instrument cycles tension far more than a guitar does
# because the motors are always moving. O3 makes that bend 1.63x sharper. If
# strings start letting go at the nut, O6 is the fallback and costs only depth.
#
# THE INSTALL IS THE DESIGN DRIVER (user). Working from the +X side, you:
#
#     push the tip UNDER the rod and around  ->  grab it as it comes out the top
#     pull the slack through                 ->  push under again, grab, pull
#     push under a third time                ->  and this time it leaves by the
#                                                EXIT HOLE, out to the clamp
#
# Three pushes = 2.5 turns, exactly the wrap the capstan sums wanted. Right-handed
# about +Y is what sends the tip UNDER the rod first — probed off the curve.
#
#  1. THREADING ROOM: a 3 mm annulus round the rod, OPEN TO THE TOP, so a stiff
#     .070 tip can be pushed round and then grabbed.
#  2. ENTRY ROOM: the +X lane is open the full bay height, for all three passes.
#  3. THE SCREW GATES THE EXIT HOLE. The string passes the -X side THREE times and
#     only the last should find the hole; the earlier two are 2p and 1p away in Y,
#     and at the bass end 1p is smaller than the hole's own half width. Wound IN,
#     the screw fills the passage and the hole is not there. gate_check() measures
#     it rather than assuming.
#
# PRINTS -X -> +X (user). The -X end face is the bed. Every bore here runs
# PERPENDICULAR to that build axis — the rod along Y, the screws and inserts along
# Z — so each one is a "horizontal" hole in the print sense and takes cadkit's 45°
# TEARDROP with print_up = +X. Without it they print as sagging round ceilings and
# come out oval.
from cadkit.holes import teardrop_hole

ROD_D  = D.BRIDGE_AXLE_D            # Ø5 — literally the bridge axle's own shaft, read
                                    # from dimensions so it cannot drift. The 695ZZ
                                    # round put BOTH endplates and every lever axle on
                                    # one Ø5 stock. Better here too: Ø5 bends the .070
                                    # at 26.2% against Ø3's 37.2% (Ø6 would be 22.9%).
ROD_X  = -9 * D.BEAD                # -7.2
ROD_Z  = -D.BEAD                    # -0.8 rod centre; strings arrive at -g/2 and meet
                                    # its +X face. One height for every gauge
BAY_R  = ROD_D / 2.0 + 2.5          # 5.0 — threading annulus. Trimmed 3.0 -> 2.5 to
                                    # pay for the fatter rod and keep the whole
                                    # termination inside the endplate's 25.4
EXIT_X = ROD_X - BAY_R              # -11.5: the wall the exit hole pierces
GATE_X = -17 * D.BEAD               # -13.6 clamp screw: it crosses the exit passage, so
                                    # wound IN it is a GATE and wound down on the
                                    # string it is the CLAMP
X_BACK_B = -24 * D.BEAD             # -19.2
WRAP_F_B = 1.05                     # turns lie all but touching. Tightening this
                                    # from 1.15 is part of what buys a finger in
                                    # EVERY lane (see below)
LANE_CLR = 0.5                      # air each side of a wrap, before its finger
PRINT_UP = (1.0, 0.0, 0.0)          # the build axis: -X -> +X


def _adv(g: float) -> float:
    """How far this string's wrap marches along the rod: one diameter per turn."""
    return TURNS * WRAP_F_B * g


# A FINGER IN EVERY LANE (user: two of the three strings had none).
#
# The first cut supported the rod only where it was easy, on the argument that a
# .070's wrap eats its whole lane. That argument was wrong, and wrong in an
# interesting way: it measured the .070's OWN lane without asking which neighbour
# the wrap marches toward. The wrap marches +Y, D.string_y falls with index, so
# string i marches at string i-1 and the binding gap is the one between the .070
# and the .054 — not the .070's own. With the clearance at 0.5 a side and the wrap
# pitch at 1.05, that gap leaves 2.26 mm, comfortably over the 1.6 two-bead floor:
#
#     factor 1.15, clr 1.0  ->  0.81 mm   TOO THIN   (what the first cut assumed)
#     factor 1.15, clr 0.5  ->  1.81 mm
#     factor 1.05, clr 0.5  ->  2.26 mm   <- and every other lane is wider
#
# So every string gets its own bay, the rod is supported at 9.5 throughout (the
# best case, 0.00003 mm), and the bay walls guide the tip while threading instead
# of letting it wander into next door. Better on all three counts.
def finger_span(n: int):
    """(y0, y1) of the printed web between string n and string n+1, or None."""
    if n + 1 >= len(GAUGE_IDX):
        return None
    g0 = D.STRING_GAUGE[GAUGE_IDX[n]]
    g1 = D.STRING_GAUGE[GAUGE_IDX[n + 1]]
    a = _y(n) + _adv(g0) + g0 / 2.0 + LANE_CLR
    b = _y(n + 1) - g1 / 2.0 - LANE_CLR
    return (a, b) if b - a > 0 else None


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
    helix = cq.Wire.makeHelix(pitch=p, height=h, radius=hr)
    coil = (cq.Workplane("XZ").center(hr, 0).circle(r)
            .sweep(cq.Workplane("XY").add(helix), isFrenet=True))
    out = out.union(coil.rotate((0, 0, 0), (1, 0, 0), -90.0)
                        .translate((ROD_X, y0, ROD_Z)))
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
    """The printed body: slab, the comb the rod threads, one threading bay per
    string, the +X entry lanes, and the gated exit passages. Builds -X -> +X."""
    w = box_at(X_FRONT - X_BACK_B, 2 * HW, SLAB_Z1 - SLAB_Z0,
               x=(X_BACK_B + X_FRONT) / 2.0, y=0.0, z=(SLAB_Z0 + SLAB_Z1) / 2.0)
    # the clamp boss runs BACK TO THE BED FACE. Floating it around GATE_X left its
    # -X wall as a 369 mm2, 11 mm tall ledge starting in mid-print — the largest
    # unsupported face in the part, and pure overhang. Taken back to X_BACK_B its
    # -X face IS the first layer, and it also buries the comb's own -X wall, which
    # was the next offender. Costs a little material and no print time.
    w = w.union(box_at((GATE_X + 4.0) - X_BACK_B, 2 * HW, BOSS_Z1 - SLAB_Z1,
                       x=(X_BACK_B + GATE_X + 4.0) / 2.0, y=0.0,
                       z=(SLAB_Z1 + BOSS_Z1) / 2.0))
    w = w.union(box_at(2 * BAY_R, 2 * HW, (ROD_Z + BAY_R) - SLAB_Z1,
                       x=ROD_X, y=0.0, z=(SLAB_Z1 + ROD_Z + BAY_R) / 2.0))

    # ONE bay per string, so every gap keeps its comb finger
    for n, gi in enumerate(GAUGE_IDX):
        g = D.STRING_GAUGE[gi]
        y0 = _y(n)
        bay_y0 = y0 - g / 2.0 - LANE_CLR
        bay_y1 = y0 + _adv(g) + g / 2.0 + LANE_CLR
        w = w.cut(box_at(2 * BAY_R, bay_y1 - bay_y0,
                         (SLAB_Z1 + 12.0) - (ROD_Z - BAY_R),
                         x=ROD_X, y=(bay_y0 + bay_y1) / 2.0,
                         z=((ROD_Z - BAY_R) + SLAB_Z1 + 12.0) / 2.0))

    # the rod's own bore — PERPENDICULAR to the build axis, so it teardrops
    w = w.cut(teardrop_hole(ROD_D + 0.4, 4 * HW,
                            axis_point=(ROD_X, -2 * HW, ROD_Z),
                            axis_dir=(0.0, 1.0, 0.0), print_up=PRINT_UP))

    for n, gi in enumerate(GAUGE_IDX):
        g = D.STRING_GAUGE[gi]
        y0 = _y(n)
        y1 = y0 + _adv(g)
        w = w.cut(cyl_y(PIN_D + 0.4, PIN_L + 0.4, y0=y0 - (PIN_L + 0.4) / 2.0,
                        x=DOWEL_X, z=-g - PIN_D / 2.0 - CONTACT_CLR))
        # ENTRY LANE — open the full bay height, for all three passes
        w = w.cut(box_at(X_FRONT - ROD_X, g + 2.0,
                         (SLAB_Z1 + 12.0) - (ROD_Z - g),
                         x=(ROD_X + X_FRONT) / 2.0, y=y0,
                         z=((ROD_Z - g) + SLAB_Z1 + 12.0) / 2.0))
        # EXIT PASSAGE — a HOLE the screw can plug. Its FLOOR is exactly where the
        # tip lands; centring it on the rod left a slot under the tip, which is the
        # gap a thin string would find on an early pass.
        _floor = ROD_Z - g / 2.0 - CONTACT_CLR
        w = w.cut(box_at(EXIT_X - (X_BACK_B - 4.0), g + 0.8, g + 0.8,
                         x=(EXIT_X + X_BACK_B - 4.0) / 2.0, y=y1,
                         z=_floor + (g + 0.8) / 2.0))
        w = w.cut(cyl_y(PIN_D + 0.4, PIN_L + 0.4, y0=y1 - (PIN_L + 0.4) / 2.0,
                        x=GATE_X, z=_floor - PIN_D / 2.0))
        # insert pocket + screw bore: also perpendicular to the build axis
        w = w.cut(teardrop_hole(INSERT_D, INSERT_L + 0.2,
                                axis_point=(GATE_X, y1, BOSS_Z1 - INSERT_L),
                                axis_dir=(0.0, 0.0, 1.0), print_up=PRINT_UP))
        w = w.cut(teardrop_hole(SCREW_D + 0.4, 40.0,
                                axis_point=(GATE_X, y1, ROD_Z - 2.0),
                                axis_dir=(0.0, 0.0, 1.0), print_up=PRINT_UP))
    return w


def gate_check():
    """Does the screw, wound fully IN, actually close the exit passage?"""
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


def depth() -> float:
    """X the whole termination occupies — against the endplate's 25.4 budget."""
    return X_FRONT - X_BACK_B


def demo_parts_rod():
    """[(name, solid)] — the shared-rod variant. ONE rod, not ten posts."""
    out = [("rodnut_block", block_rod())]
    out.append(("rodnut_rod", cyl_y(ROD_D, 2 * HW + 8.0, y0=-HW - 4.0,
                                    x=ROD_X, z=ROD_Z)))
    for n in range(len(GAUGE_IDX)):
        out += _hardware_rod(n)
        out.append((f"rodnut_string_{n}", _string_rod(n)))
    return out
