# -*- coding: utf-8 -*-
"""THE LEG'S BLIND-MATE, ON THE JOINT'S OWN AXIS: a spring-floated jack inside the
fixed TENON, meeting a plug fixed in the body adapter's roof, right down the middle
of the octagon joint the leg already hangs on.

WHY THE MIDDLE (user). The first pass put this in the -X/+Y corner, because the
connector stack was sized against the ADAPTER's depth and only a corner has 52.8 of
it -- on the axis the adapter has 12.8, the mortise being 40 of the 52.8. That was
the wrong part to measure. Put the bulk in the TENON, which is 252 long and solid,
and the axis is not merely possible but better:

  * the octagon joint's OWN 0.3 fit centres the pair. In the corner, two bores 20 off
    the axis had to agree across two parts and two print directions.
  * nothing stands proud. The plug's barrel protrudes, but into the MORTISE, which is
    a pocket 40 deep -- there is no exposed pin to knock.
  * the lead then runs the leg's CORE, which is the path the ADJUST tenon needs
    anyway (user): its ladder holes run along X at y 0, so a few mm of Y clears every
    one of them -- measured O9.2 clear the full 252.

WHERE, EXACTLY. Not the geometric axis: the latch's pocket owns the tenon's middle
(it takes everything y < -3 across x +-6), so the spine steps +Y off it. At
(-1.6, +4.8) the fixed tenon takes O14.8 for its top 46 and O12.8 for its whole
length, with the latch's pocket clear -- measured on the built solid, not derived.

WHAT IT COSTS, and the user chose it: the plug's way IN is a O6.6 hole in the
adapter's top face at that spine, and the MIDDLE RIDGE's root is there. Boring
through a ridge would leave 1.6 slivers, so the ridge is CUT BACK instead -- it
already gives up its inboard end to the service slide, and it now starts at
legs.SIGNAL_RIDGE_IN rather than at the slide. A shortening, not a hole.

HOW IT GOES TOGETHER. The plug drops in from the adapter's top face and PRESSES into
8.0 of O6.0 bore, its back at the channel's floor so the lead folds straight into the
channel and runs out the -Y face, inboard, under the instrument. The jack is dropped
down the tenon's bore onto its coil and is stopped by the THROAT at the tenon's tip --
a O6.6 lip the plug's overmould passes and the jack's O9.7 barrel cannot. At rest the
jack's mouth stands THROAT_L below the tip; the plug's shoulder bottoms it FLOAT
lower, and that FLOAT is how much the latch is allowed to be short.
"""

from __future__ import annotations

import cadquery as cq

from cadkit.holes import teardrop_hole
from . import dimensions as D
from . import latch as LT
from . import leg_stack as LS
from . import legs as LG

B = D.BEAD

# ── the bought parts (BOM.md: the M->F extension cable, and its plug end) ─────
JACK_D = 9.7            # the moulded inline jack's barrel (BOM: 9.1..9.7, pick high)
JACK_L = 40.0           # ...and its length (BOM: <= 40)
# The plug is a REAL PART, off its drawing (user asked for one rather than a
# "confirm at purchase"): Tensility 10-02155, a 3.5 mm 4C plug-to-plug assembly,
# 1830 mm, 28 AWG, $3.73 at DigiKey. The drawing gives the overmould as 6.1 x 14,
# the barrel 3.5 x 14 and the cable 3.8 -- all four numbers below.
PLUG_D = 6.1            # the moulded overmould (10-02155 drawing)
PLUG_L = 14.0           # ...and its length
BARREL_L = 14.0         # the plug's barrel: what actually crosses the joint
BARREL_D = 3.5
CABLE_D = 3.8           # the BODY side's lead (10-02155). Nothing threads over it
# THE LEG SIDE'S LEAD IS A SOURCING CONSTRAINT, not a free choice, and this is the
# number to buy to: the coil is dropped down the tenon OVER the already-threaded lead
# (see seat()), so it has to fall freely over it. The latches' coil is O5.0 on 0.6
# wire = 3.8 ID, and the body side's own 3.8 lead would be a zero-clearance fit that
# binds. The leg's M->F extension needs a cable no fatter than this.
LEAD_D_MAX = LT.SPR_ID - 0.6            # 3.2

# ── the float ────────────────────────────────────────────────────────────────
FLOAT = 3.0             # how far the jack is pushed back when the leg latches -- and
                        # so how much SLOP THE LATCH IS ALLOWED: the pair bottoms this
                        # far before the leg is home, so anything from a perfect latch
                        # to this much short of one still seats the connector
SPR_REST_L = 10.0       # the coil at rest: 2.0 of preload on a 12.0 free length
SPR_MATE_L = SPR_REST_L - FLOAT
PRELOAD_N = (LT.SPR_FREE - SPR_REST_L) * LT.SPR_RATE            # 5.0 N standing still
MATE_N = (LT.SPR_FREE - SPR_MATE_L) * LT.SPR_RATE               # 12.6 N seated
assert SPR_MATE_L >= LT.SPR_SOLID + 1.0, (
    "the coil is %.2f from solid when the leg latches -- no room for the latch's own "
    "slop" % (SPR_MATE_L - LT.SPR_SOLID))

# ── the spine: off the axis by just enough to clear the latch's pocket ───────
AX_X = -2 * B           # -1.6
AX_Y = 7 * B            # +5.6 -- the latch's pocket takes the tenon's -Y middle
THROAT_D = PLUG_D + 0.5         # 6.6: the plug's overmould passes, the jack does not.
                                # This lip IS the jack's up-stop with the leg off
PLUG_BORE_D = PLUG_D - 0.1      # 6.0: a press on the overmould
JACK_BORE_D = JACK_D + 0.2      # 9.9: the jack runs free in the tenon
SPR_BORE_D = LT.SPR_BORE_D      # 5.4, the latches' own coil pocket -- but in the SEAT,
                                # not in the tenon: see THREADING below
PASS_D = PLUG_D + 0.5           # 6.6: every bore below the throat is at least this,
                                # because the lead's FAR PLUG has to travel the whole
                                # length of the tenon and out the bottom. A O4.8 cable
                                # bore looks right and cannot be assembled (user).
SEAT_T = 4 * B                  # 3.2: the printed washer that gives the coil its floor.
                                # 4 beads, not 3: it is a POCKET over a FLOOR and both
                                # want MIN_WALL_2P. At 2.4 the floor came out 1.2 and
                                # tools/check_thin found it.
                                # The floor CANNOT be a step in the tenon -- a step
                                # narrow enough to seat a O5.0 coil is narrow enough to
                                # stop the O6.1 head that has to pass it
SEAT_CLR = 0.3                  # ...so it is a separate part, dropped in over the lead
SEAT_BORE_D = LEAD_D_MAX + 0.6  # 3.8 through it: the lead passes, the coil seats
CHAN_W = CABLE_D + 1.0          # 4.8 wide and deep: the groove in the adapter's top
CHAN_D = CABLE_D + 1.0          # face the lead is folded into

# ── the z chain, all of it hung off the tenon's tip ───────────────────────────
TIP = LS.Z_MORTISE_ROOF         # -94.55: the tenon's tip, and the mortise's roof
PLUG_TOP = LS.Z_TOP - CHAN_D    # -86.55: the plug's back sits AT the channel's floor,
                                # so the lead folds into the channel with no corner
PLUG_SHOULDER = PLUG_TOP - PLUG_L               # -100.55, and the jack's mouth when
                                                # the leg is home
THROAT_L = TIP - (PLUG_SHOULDER + FLOAT)        # 3.0: how far below the tip the jack's
                                                # mouth rests. It falls out of the chain
                                                # -- it is not a free number
JACK_REST = PLUG_SHOULDER + FLOAT               # -97.55, the jack's mouth at rest
JACK_BACK = PLUG_SHOULDER - JACK_L              # -140.55 seated, FLOAT higher at rest
SPR_SEAT = (JACK_BACK + FLOAT) - SPR_REST_L     # -147.55: the coil's own floor, which
                                                # is the printed SEAT's top face
SEAT_LEDGE = SPR_SEAT - SEAT_T                  # ...and the ledge that washer rests on
PLUG_GRIP = PLUG_TOP - TIP                      # 8.0 of press bore in the roof

assert THROAT_L >= D.MIN_WALL_2P, (
    "the throat is %.2f -- too thin a lip to stop the jack" % THROAT_L)
assert PLUG_GRIP >= 4 * D.MIN_WALL_2P, (
    "only %.1f of press holds the plug in the adapter's roof" % PLUG_GRIP)
assert LEAD_D_MAX + 0.4 <= LT.SPR_ID, (
    "a %.1f lead will not drop through a %.1f coil ID -- the leg's lead has to be "
    "bought thinner, or this joint needs its own spring"
    % (LEAD_D_MAX, LT.SPR_ID))
assert PASS_D >= PLUG_D + 0.4, (
    "the lead's far plug (%.1f) cannot travel a %.1f bore, so it can never be "
    "threaded down the tenon at all" % (PLUG_D, PASS_D))

# the plug's way in is a hole in the adapter's TOP FACE, and the middle ridge's root
# is there. legs cuts that ridge back for us; check it actually clears, apex included
_MOUTH_PEAK = AX_Y + (THROAT_D / 2.0) * 2 ** 0.5        # the teardrop's apex, toward +Y
assert LG.SIGNAL_RIDGE_IN >= _MOUTH_PEAK + D.MIN_WALL_2P, (
    "the middle ridge starts at %+.2f but the plug's mouth reaches %+.2f -- boring "
    "through a ridge leaves slivers; legs.SIGNAL_RIDGE_IN has to clear it"
    % (LG.SIGNAL_RIDGE_IN, _MOUTH_PEAK))


def _ax(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    return sx + AX_X, ly + AX_Y


def _bore(d, z0, z1, x, y, up):
    return teardrop_hole(d, z1 - z0, (x, y, z0), (0, 0, 1), up)


def chan_pts(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """The channel's centreline on the adapter's top face: straight out of the plug's
    mouth and down the part to the -Y face. It needs no dog-leg any more -- on the
    axis there is no tongue in the way."""
    x, y = _ax(sx, ly)
    return [(x, y), (x, ly - LS.LEG_W / 2.0 - 1.0)]


def channel(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """That path as a groove in the top face. It runs ALONG this part's build
    direction, so both its walls are vertical and it has no ceiling at all."""
    a, b = chan_pts(sx, ly)
    return (cq.Workplane("XY")
            .box(CHAN_W, a[1] - b[1], CHAN_D + 1.0, centered=(True, False, False))
            .translate((a[0], b[1], LS.Z_TOP - CHAN_D)))


def adapter_negatives(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, up=None):
    """Cut in the BODY ADAPTER: the plug's press bore through the roof, the mouth
    above it the plug drops in through, and the channel the lead is folded into."""
    x, y = _ax(sx, ly)
    up = up or LS.PRINT_UP["body_adapter"]
    out = _bore(PLUG_BORE_D, TIP - 0.01, PLUG_TOP, x, y, up)               # the press
    out = out.union(_bore(THROAT_D, PLUG_TOP, LS.Z_TOP + 0.01, x, y, up))  # the mouth
    return out.union(channel(sx, ly))


def tenon_negatives(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, up=None,
                    bot: float = None):
    """Cut in the FIXED TENON: the throat at its tip, the jack's travel and the coil
    below it, the ledge the coil's SEAT rests on, and a pass-through the rest of the
    way that is wide enough for the lead's far plug."""
    x, y = _ax(sx, ly)
    up = up or LS.PRINT_UP["fixed_tenon"]
    bot = LS.Z_FIX_TEN_BOT - 1.0 if bot is None else bot
    out = _bore(THROAT_D, JACK_REST, TIP + 1.0, x, y, up)                  # the lip
    out = out.union(_bore(JACK_BORE_D, SEAT_LEDGE, JACK_REST + 0.01, x, y, up))
    return out.union(_bore(PASS_D, bot, SEAT_LEDGE + 0.01, x, y, up))


def seat(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """THE COIL'S FLOOR, and the reason it is a separate part rather than a step.

    THREADING is what sizes this end of the leg. The jack is moulded onto its lead and
    the lead's far end is a O6.1 plug, so the lead cannot be pulled in from below and
    cannot be fed through the coil: it has to go in from the tenon's TIP, head first,
    and come out the bottom -- which means every bore it passes is at least PASS_D.
    A step narrow enough to seat a O5.0 coil would stop that head dead (user found the
    first pass had no way in at all). So the coil's floor arrives AFTERWARDS: this
    washer drops down the same bore over the already-threaded lead and lands on the
    tenon's ledge. Then the coil, then the jack. Nothing ever has to pass anything."""
    x, y = _ax(sx, ly)
    d = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        (JACK_BORE_D - SEAT_CLR) / 2.0, SEAT_T,
        cq.Vector(x, y, SEAT_LEDGE), cq.Vector(0, 0, 1)))
    d = d.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(   # the coil's own pocket
        SPR_BORE_D / 2.0, D.MIN_WALL_2P,
        cq.Vector(x, y, SPR_SEAT - D.MIN_WALL_2P), cq.Vector(0, 0, 1))))
    return d.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        SEAT_BORE_D / 2.0, SEAT_T + 2.0,
        cq.Vector(x, y, SEAT_LEDGE - 1.0), cq.Vector(0, 0, 1))))


def _run(pts, d=CABLE_D):
    """A cable through `pts`: cylinders with balls at the corners."""
    out = None
    for a, b in zip(pts, pts[1:]):
        v = cq.Vector(*b) - cq.Vector(*a)
        seg = cq.Solid.makeCylinder(d / 2.0, v.Length, cq.Vector(*a), v.normalized())
        out = seg if out is None else out.fuse(seg)
    for q in pts[1:-1]:
        out = out.fuse(cq.Solid.makeSphere(d / 2.0, cq.Vector(*q)))
    return cq.Workplane("XY").add(out)


def cables(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, k: int = 0):
    """THE RUN, drawn -- a hole in a face with nothing coming out of it reads as a
    mystery (user saw exactly that on the first pass).

    The patch lead leaves the plug's back AT the channel's floor, runs straight down
    the adapter's top face and out the -Y one -- inboard, under the instrument, where
    nothing shows from the front -- then along the underside to the jack in the
    chassis floor. Below the joint, the leg's own lead drops from the floating jack's
    back down the middle of the tenon, which is where the adjust tenon will want it."""
    x, y = _ax(sx, ly)
    _, b = chan_pts(sx, ly)
    fold = LS.Z_TOP - CHAN_D / 2.0
    from . import electronics as EL                      # late: sizes only
    from . import wiring as WR                           # late: wiring reads chassis
    patch = _run([(x, y, PLUG_TOP),                             # the plug's back
                  (x, y, fold),                                 # folded into the channel
                  (b[0], b[1] + 1.0, fold),                     # out the -Y face
                  (b[0], b[1] - 4.0, fold),                     # clear of it
                  (WR.TRRS_X, WR.TRRS_Y - 10.0, fold),          # inboard, under the body
                  (WR.TRRS_X, WR.TRRS_Y, fold),
                  (WR.TRRS_X, WR.TRRS_Y,
                   WR.trrs_mouth_z() - EL.TRRS_PLUG_RUN)])      # and up into the jack.
                                    # It STOPS at the plug's tail: that plug is drawn
                                    # at the station, and running the two into each
                                    # other only trips the gate
    leg = _run([(x, y, JACK_BACK), (x, y, JACK_BACK - 40.0)])
    return [("leg_trrs_patch_%d" % k, patch), ("leg_trrs_leg_lead_%d" % k, leg)]


def dummies(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, k: int = 0, mated: bool = True):
    """The bought parts where they sit. `mated` is the latched state: the jack pushed
    back FLOAT off its throat, its coil that much shorter."""
    x, y = _ax(sx, ly)
    back = 0.0 if mated else FLOAT
    plug = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        PLUG_D / 2.0, PLUG_L, cq.Vector(x, y, PLUG_SHOULDER), cq.Vector(0, 0, 1)))
    plug = plug.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        BARREL_D / 2.0, BARREL_L, cq.Vector(x, y, PLUG_SHOULDER - BARREL_L),
        cq.Vector(0, 0, 1))))
    mouth = PLUG_SHOULDER + back                 # the jack's mouth: it is what moves
    jack = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        JACK_D / 2.0, JACK_L, cq.Vector(x, y, mouth - JACK_L), cq.Vector(0, 0, 1)))
    coil_l = SPR_REST_L if not mated else SPR_MATE_L
    coil = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        LT.SPR_OD / 2.0, coil_l, cq.Vector(x, y, SPR_SEAT), cq.Vector(0, 0, 1)).cut(
        cq.Solid.makeCylinder(LT.SPR_ID / 2.0, coil_l + 2.0,
                              cq.Vector(x, y, SPR_SEAT - 1.0), cq.Vector(0, 0, 1))))
    return [("leg_trrs_plug_%d" % k, plug), ("leg_trrs_jack_%d" % k, jack),
            ("leg_trrs_spring_%d" % k, coil),
            ("leg_trrs_seat_%d" % k, seat(sx, ly))] + cables(sx, ly, k)
