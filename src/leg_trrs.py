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

THE COIL IS NOT THE LATCHES' COIL, and that is the user's call after this joint
turned out to be unbuildable with it. The coil has to end up ON THE LEAD, between the
jack's back and its seat -- and a lead has two ends, the moulded jack (O9.7) and the
moulded far plug (O6.1). A 3.8 ID coil passes neither, so NO assembly order puts it
there; widening every bore to PASS_D was necessary and nowhere near sufficient. (The
install sweep missed it because a swept envelope treats each piece as a free rigid
body and has no notion of one part being THREADED ONTO another.) So this joint gets
its own coil, whose only new requirement is an ID that clears the far plug -- it is
slid onto the lead over that plug before anything goes in the tenon. Everything else
about it is the latch coil's numbers, deliberately: same free length, same rate, so
the force at rest and at seat are unchanged.

It pays for itself twice over: at O8.0 the coil seats DIRECTLY on the tenon's own
O9.9 -> PASS_D step, because a step that stops a O8.0 coil still passes the O6.1 head.
The printed seat washer the O5.0 coil needed is gone.
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
CABLE_D = 3.8           # the lead, either side (10-02155's is 3.8). The leg's coil is
                        # slid on over the far PLUG, not the cable, so the cable's own
                        # diameter is no longer a sourcing constraint -- the O6.6 coil
                        # ID clears the O6.1 overmould and everything thinner with it

# ── the float ────────────────────────────────────────────────────────────────
FLOAT = 3.0             # how far the jack is pushed back when the leg latches -- and
                        # so how much SLOP THE LATCH IS ALLOWED: the pair bottoms this
                        # far before the leg is home, so anything from a perfect latch
                        # to this much short of one still seats the connector
SPR_WIRE = 0.7          # THIS JOINT'S OWN COIL (see the docstring). The one number
SPR_OD = 8.0            # that had to change is the ID: it is slid onto the lead over
SPR_ID = SPR_OD - 2 * SPR_WIRE          # 6.6 -- clears the far plug's O6.1 overmould
SPR_FREE = LT.SPR_FREE                  # 12.0, and the rate below, are the LATCH
SPR_RATE = 2.5                          # coil's: the feel at rest and at seat is the
SPR_SOLID = 7 * SPR_WIRE                # same 5.0 N / 12.5 N it always was
SPR_REST_L = 10.0       # the coil at rest: 2.0 of preload on a 12.0 free length
SPR_MATE_L = SPR_REST_L - FLOAT
PRELOAD_N = (SPR_FREE - SPR_REST_L) * SPR_RATE                  # 5.0 N standing still
MATE_N = (SPR_FREE - SPR_MATE_L) * SPR_RATE                     # 12.5 N seated
assert SPR_ID >= PLUG_D + 0.4, (
    "a %.1f ID coil will not slide over the lead's %.1f far plug -- this joint is "
    "unbuildable, which is the whole reason it has its own SKU" % (SPR_ID, PLUG_D))
assert SPR_MATE_L >= SPR_SOLID + 1.0, (
    "the coil is %.2f from solid when the leg latches -- no room for the latch's own "
    "slop" % (SPR_MATE_L - SPR_SOLID))

# ── the spine: off the axis by just enough to clear the latch's pocket ───────
AX_X = -2 * B           # -1.6
AX_Y = 7 * B            # +5.6 -- the latch's pocket takes the tenon's -Y middle
THROAT_D = PLUG_D + 0.5         # 6.6: the plug's overmould passes, the jack does not.
                                # This lip is the jack's up-stop with the leg off -- and
                                # it is a separate PRESSED PART, not a step in the bore,
                                # for the same reason the coil's seat is: the jack is
                                # O9.7 and goes in from the tip, so a 6.6 step above it
                                # is a lid on a box with the box already shut. The first
                                # pass cut it as a bore and the cavity had O6.6 at BOTH
                                # ends, which the user spotted in the tab
PLUG_BORE_D = PLUG_D - 0.1      # 6.0: a press on the overmould
JACK_BORE_D = JACK_D + 0.2      # 9.9: the jack runs free in the tenon
PASS_D = PLUG_D + 0.5           # 6.6: every bore below the throat is at least this,
                                # because the lead's FAR PLUG has to travel the whole
                                # length of the tenon and out the bottom. A O4.8 cable
                                # bore looks right and cannot be assembled (user).
THROAT_BORE_D = 10.5                    # the keeper sits in a COUNTERBORE at the
                                        # tip, not in the jack's own bore. Its groove
                                        # for the set screw costs LOCK_GROOVE of wall,
                                        # and at O9.9 that left 0.70 (tools/check_thin);
                                        # widening the seat buys it back without
                                        # touching the O6.6 the plug has to pass.
                                        # It is a SQUEEZE, both ways: the octagon takes
                                        # O14.00 here (measured), so 10.7 leaves the
                                        # tenon 1.66, and the keeper is left 1.60 under
                                        # its groove. Both are the 1.6 floor, barely
LOCK_Z = None                   # set below, once THROAT_L is known
LOCK_GROOVE = 0.4               # how deep the set screw's tip sits in the keeper's OD.
                                # 0.4, not 0.8: the groove comes straight off the
                                # keeper's wall and 0.8 took it under the floor
# LOCK_BITE is MEASURED off the octagon at run time rather than written down: the
# flank slopes, so the wall depends on the spine, and a spine move would otherwise
# leave the hole's mouth buried or hanging. Whatever it comes to is 0.5-1.5 short of
# M4's anchor_min_wall, so this is a THREAD-FORMED grub and not an insert -- the same
# call legs.py makes for its pinch grubs. The -Y flank has 16.0 and would take a
# pocket, but then the grub has to be 20 long to cross it.
THROAT_PRESS = 0.1              # the keeper's interference in the jack's bore. It only
                                # ever carries the coil's 5 N preload, and only while the
                                # leg is OFF: with the leg on, the adapter's mortise roof
                                # sits directly over it
CHAN_W = CABLE_D + 1.0          # 4.8 wide and deep: the groove in the adapter's top
CHAN_D = CABLE_D + 1.0          # face the lead is folded into

# ── the z chain, all of it hung off the tenon's tip ───────────────────────────
TIP = LS.Z_MORTISE_ROOF         # -94.55: the tenon's tip, and the mortise's roof
PLUG_TOP = LS.Z_TOP - CHAN_D - 2 * B    # the plug sits 1.6 BELOW the channel's floor,
                                # and the 1.6 is the KEEPER's: THROAT_L falls out of
                                # this chain, and at the channel's floor it came to 3.0
                                # -- too short to carry the set screw's groove with
                                # MIN_WALL_2P either side of it (1.10, check_thin). The
                                # lead just rises those 1.6 inside the mouth bore it
                                # drops in through, and folds into the channel there
PLUG_SHOULDER = PLUG_TOP - PLUG_L               # -100.55, and the jack's mouth when
                                                # the leg is home
THROAT_L = TIP - (PLUG_SHOULDER + FLOAT)        # 3.0: how far below the tip the jack's
                                                # mouth rests. It falls out of the chain
                                                # -- it is not a free number
JACK_REST = PLUG_SHOULDER + FLOAT               # -97.55, the jack's mouth at rest
JACK_BACK = PLUG_SHOULDER - JACK_L              # -140.55 seated, FLOAT higher at rest
SPR_SEAT = (JACK_BACK + FLOAT) - SPR_REST_L     # -147.55: the coil's floor, and the
                                                # tenon's own O9.9 -> PASS_D step
PLUG_GRIP = PLUG_TOP - TIP                      # 8.0 of press bore in the roof

assert THROAT_L >= D.MIN_WALL_2P, (
    "the throat is %.2f -- too thin a lip to stop the jack" % THROAT_L)
assert PLUG_GRIP >= 4 * D.MIN_WALL_2P, (
    "only %.1f of press holds the plug in the adapter's roof" % PLUG_GRIP)
assert THROAT_L - 2 * LOCK_GROOVE >= 2 * D.MIN_WALL_2P, (
    "the keeper is %.2f tall and its groove %.2f, leaving %.2f of flange either side "
    "for the set screw to bear on"
    % (THROAT_L, 2 * LOCK_GROOVE, (THROAT_L - 2 * LOCK_GROOVE) / 2))
assert PASS_D >= PLUG_D + 0.4, (
    "the lead's far plug (%.1f) cannot travel a %.1f bore, so it can never be "
    "threaded down the tenon at all" % (PLUG_D, PASS_D))

LOCK_Z = JACK_REST + THROAT_L / 2.0     # the set screw's line, on the keeper's middle

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
    """Cut in the FIXED TENON: one straight O9.9 bore from the tip down past the jack
    and the coil to the ledge their SEAT rests on, then a pass-through the rest of the
    way that is wide enough for the lead's far plug. Nothing narrows on the way in --
    everything that has to get past goes in from the tip, in order."""
    x, y = _ax(sx, ly)
    up = up or LS.PRINT_UP["fixed_tenon"]
    bot = LS.Z_FIX_TEN_BOT - 1.0 if bot is None else bot
    out = _bore(JACK_BORE_D, SPR_SEAT, TIP + 1.0, x, y, up)     # ONE bore, tip to step
    out = out.union(_bore(THROAT_BORE_D, JACK_REST, TIP + 1.0, x, y, up))  # the keeper's
    return out.union(_bore(PASS_D, bot, SPR_SEAT + 0.01, x, y, up))


def throat(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """THE JACK'S UP-STOP, pressed into the tenon's tip LAST.

    It cannot be a step in the bore. The jack is O9.7 and can only go in from the tip,
    so anything narrower than 9.7 above it is a lid fitted before the box is filled --
    which is exactly what the first pass drew, a O9.8 cavity with O6.6 at both ends and
    no way to put a jack in it (user). So the lip arrives after the jack: a ring
    pressed into the bore, bored THROAT_D so the plug's overmould still passes.

    It is barely loaded. With the leg OFF it holds the coil's 5 N preload on a press
    over THROAT_L; with the leg ON the jack is pushed DOWN off it and the adapter's
    mortise roof sits right over its top face."""
    x, y = _ax(sx, ly)
    r = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        (THROAT_BORE_D + THROAT_PRESS) / 2.0, THROAT_L,
        cq.Vector(x, y, JACK_REST), cq.Vector(0, 0, 1)))
    r = r.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        THROAT_D / 2.0, THROAT_L + 2.0,
        cq.Vector(x, y, JACK_REST - 1.0), cq.Vector(0, 0, 1))))
    # the set screw's GROOVE: right round, so the keeper can go in at any clocking
    groove = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        (THROAT_BORE_D + THROAT_PRESS) / 2.0 + 1.0, LOCK_GROOVE * 2,
        cq.Vector(x, y, LOCK_Z - LOCK_GROOVE), cq.Vector(0, 0, 1)))
    groove = groove.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        (THROAT_BORE_D + THROAT_PRESS) / 2.0 - LOCK_GROOVE, LOCK_GROOVE * 2 + 2,
        cq.Vector(x, y, LOCK_Z - LOCK_GROOVE - 1), cq.Vector(0, 0, 1))))
    return r.cut(groove)


def _flank_x(y, z):
    """Where the tenon's +X flank actually is at (y, z) -- measured on the octagon
    itself, because it slopes and the spine is off-axis."""
    prism = LS.tenon(z - 1.0, z + 1.0).val()
    t = 0.0
    while t < 30.0:
        if not prism.isInside(cq.Vector(LS.LEG_X + t, y, z), 1e-4):
            return LS.LEG_X + t
        t += 0.05
    raise AssertionError("no +X flank found at y %.2f z %.2f" % (y, z))


def lock_negatives(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, up=None):
    """The set screw's hole in the FIXED TENON: in from the +X flank, thread-formed,
    landing in the keeper's groove. Without it the keeper is held by THROAT_PRESS
    alone -- 3.7 mm3 of contact against the coil's 5 N, which the user rightly would
    not take (the adapter's mortise roof caps it, but only with the leg ON)."""
    from cadkit.fasteners import M4
    x, y = _ax(sx, ly)
    face_x = _flank_x(y, LOCK_Z)
    bite = face_x - (x + (THROAT_BORE_D + THROAT_PRESS) / 2.0)
    assert bite >= M4.min_bite, (
        "only %.2f of +X flank between the keeper and the outside -- not enough to "
        "thread-form an M4 (min bite %.2f)" % (bite, M4.min_bite))
    up = up or LS.PRINT_UP["fixed_tenon"]
    # PLAIN ROUND, not teardropped: this bore lies 45 degrees off the tenon's diagonal
    # build, which is inside leg_stack.TEN_HOLE_LIMIT_DEG, exactly as the ladder holes
    # in the adjust tenon are. Teardropping it anyway threw an apex at the -Y flank and
    # took that wall to 1.10 (tools/check_thin).
    end_x = x + (THROAT_BORE_D + THROAT_PRESS) / 2.0 - LOCK_GROOVE
    out = teardrop_hole(M4.selftap_d, (face_x + 4.0) - end_x,
                        (face_x + 4.0, y, LOCK_Z), (-1.0, 0.0, 0.0), up,
                        limit_deg=LS.TEN_HOLE_LIMIT_DEG)
    # OPEN AT THE TIP, not a buried hole. The mate chain leaves THROAT_L of tenon above
    # the jack's rest, and an M4 cross-hole with MIN_WALL_2P over it wants about 6 --
    # buried, it left 0.20 of web (tools/check_thin). So the slot runs out through the
    # tip face, which is the one face that does not need to hold anything: the adapter's
    # mortise roof lands flat on it and caps the slot the moment the leg is on.
    slot = (cq.Workplane("XY")
            .box(( face_x + 4.0) - end_x, M4.selftap_d + 0.8,   # WIDER than the bore:
                 # flush with it the two are tangent and leave a zero-thickness feather
                 (LS.Z_MORTISE_ROOF + 1.0) - LOCK_Z,
                 centered=(False, True, False))
            .translate((end_x, y, LOCK_Z)))
    return out.union(slot)


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
        SPR_OD / 2.0, coil_l, cq.Vector(x, y, SPR_SEAT), cq.Vector(0, 0, 1)).cut(
        cq.Solid.makeCylinder(SPR_ID / 2.0, coil_l + 2.0,
                              cq.Vector(x, y, SPR_SEAT - 1.0), cq.Vector(0, 0, 1))))
    return [("leg_trrs_plug_%d" % k, plug), ("leg_trrs_jack_%d" % k, jack),
            ("leg_trrs_spring_%d" % k, coil),
            ("leg_trrs_throat_%d" % k, throat(sx, ly))] + cables(sx, ly, k)
