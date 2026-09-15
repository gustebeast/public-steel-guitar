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

import math

import cadquery as cq

from cadkit.fasteners import M4_BUTTON_HEAD_D
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
LEAD_BORE_D = 6 * B             # 4.8 -- and the plug does NOT come down through it.
                                # THE LEAD IS A PIGTAIL NOW (user): the far end is bare
                                # wire crimped to a JST-XH at the station, not a second
                                # moulded plug. That buys three things at once.
                                #  1. the plug goes in from BELOW, up from the mortise,
                                #     and this bore is a POSITIVE up-stop -- a step the
                                #     O6.1 overmould cannot pass. The printed cap that
                                #     used to do that job is gone.
                                #  2. the four leads thread up it easily, so nothing
                                #     wide has to reach the top face: the mouth drops
                                #     from O8.8 to O4.8 and the middle ridge gets 2.4 of
                                #     its length back (legs.SIGNAL_RIDGE_IN).
                                #  3. the 90 degree turn into the channel happens in
                                #     BARE 28 AWG leads, not in a O3.8 jacketed cable.
                                #     The bend was the whole problem -- 6.5 of radius on
                                #     a 3.8 cable is 1.7x OD, well under the 3x a static
                                #     install wants. Stripped, it is a non-question.
LOCK_RECESS = 2.6               # the button head's pocket depth (head 2.2 + 0.4)
LOCK_SCREW_L = 16.0             # M4 x 16 BUTTON, 2.5 hex: the instrument's one driver
LOCK_GROOVE = 0.4               # how deep the screw's tip sits in the keeper's OD.
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
PLUG_GRIP = 3 * B               # 2.4 of press bore left after the keeper takes its 8.6.
                                # At 4 beads the straight screw's window closes to a
                                # single point (cover and flange both exactly 1.60);
                                # one more bead to the keeper buys 0.4 either side
PLUG_TOP = TIP + PLUG_GRIP      # THE KEEPER GETS THE HEIGHT (user: make the throat
                                # taller so the screw can be straight). THROAT_L and
                                # PLUG_GRIP share a fixed 11.0 -- both come off this one
                                # number -- so every mm the keeper gains, the plug's
                                # press gives up. A STRAIGHT O7.6 button needs the
                                # keeper at 7.8 (see LOCK_Z), which leaves the press
                                # 3.2, and 3.2 cannot hold MATE_N. So the plug stops
                                # relying on its press at all: cap() gives it a POSITIVE
                                # up-stop and the press only has to keep it from
                                # dropping out while the leg is off
PLUG_SHOULDER = PLUG_TOP - PLUG_L               # -100.55, and the jack's mouth when
                                                # the leg is home
THROAT_L = TIP - (PLUG_SHOULDER + FLOAT)        # 3.0: how far below the tip the jack's
                                                # mouth rests. It falls out of the chain
                                                # -- it is not a free number
JACK_REST = PLUG_SHOULDER + FLOAT               # -97.55, the jack's mouth at rest
JACK_BACK = PLUG_SHOULDER - JACK_L              # -140.55 seated, FLOAT higher at rest
SPR_SEAT = (JACK_BACK + FLOAT) - SPR_REST_L     # -147.55: the coil's floor, and the
                                                # tenon's own O9.9 -> PASS_D step

assert THROAT_L >= D.MIN_WALL_2P, (
    "the throat is %.2f -- too thin a lip to stop the jack" % THROAT_L)
assert PLUG_GRIP >= 3 * D.BEAD, (
    "only %.1f of press guides the plug in the adapter's roof. It no longer "
    "CARRIES the mate force -- cap() does -- but it is still what keeps a "
    "14-long overmould concentric and stops it dropping out with the leg off"
    % PLUG_GRIP)

# THE SCREW IS STRAIGHT (user), and this is the window that makes it so. A O7.6 button
# recessed square to the flank needs MIN_WALL_2P of tenon over its top edge, and the
# keeper needs MIN_WALL_2P of flange under the groove. Between them they fix LOCK_Z to
# a window that only exists once THROAT_L >= 7.8 -- which is what the plug's press paid
# for. Tilting it was the alternative and the user did not want it.
_HEAD_R = M4_BUTTON_HEAD_D / 2.0 + 0.4          # the head in its recess, radius
_LOCK_HI = TIP - _HEAD_R - D.MIN_WALL_2P
_LOCK_LO = JACK_REST + LOCK_GROOVE + D.MIN_WALL_2P
assert _LOCK_LO <= _LOCK_HI + 1e-9, (
    "no room for a STRAIGHT lock screw: the head wants z <= %.2f and the keeper's "
    "flange wants z >= %.2f. THROAT_L is %.2f and needs %.2f -- give it more by "
    "lowering PLUG_TOP (it costs PLUG_GRIP one for one)"
    % (_LOCK_HI, _LOCK_LO, THROAT_L, THROAT_L + (_LOCK_LO - _LOCK_HI)))
LOCK_Z = (_LOCK_LO + _LOCK_HI) / 2.0    # the set screw's line, centred in that window


# the plug's way in is a hole in the adapter's TOP FACE, and the middle ridge's root
# is there. legs cuts that ridge back for us; check it actually clears, apex included
_MOUTH_PEAK = AX_Y + (LEAD_BORE_D / 2.0) * 2 ** 0.5     # the teardrop's apex, toward +Y
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
    out = out.union(_bore(LEAD_BORE_D, PLUG_TOP, LS.Z_TOP + 0.01, x, y, up))
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


def _lock_axis(sx=LS.LEG_X, ly=LS.LEG_Y):
    """(entry point, unit direction, run) for the keeper's lock screw.

    STRAIGHT IN from the -Y flank (user). A O7.6 button head -- the only M4 head on this
    instrument, because its 2.5 hex is the one driver (fasteners.AGENTS) -- needs 4.2 of
    radius about its axis, so the tenon has to be tall enough over the jack's rest to
    bury it: see LOCK_Z, which asserts the window exists. It only does because the
    keeper took 8.6 of the chain's 11.0 and left the plug 2.4."""
    x, y = _ax(sx, ly)
    d = (0.0, 1.0, 0.0)                                  # straight in from the -Y flank
    tip = (x, y - (THROAT_BORE_D + THROAT_PRESS) / 2.0 + LOCK_GROOVE, LOCK_Z)
    prism = LS.tenon(LOCK_Z - 40.0, LOCK_Z + 5.0).val()
    run = 0.0
    while run < 40.0:
        p = cq.Vector(tip[0] - d[0] * run, tip[1] - d[1] * run, tip[2] - d[2] * run)
        if not prism.isInside(p, 1e-4):
            break
        run += 0.05
    entry = (tip[0] - d[0] * run, tip[1] - d[1] * run, tip[2] - d[2] * run)
    return entry, d, run


def lock_negatives(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, up=None):
    """The lock screw's hole in the FIXED TENON: a recessed O7.6 button head, its
    heat-set insert, and clearance on through to the keeper's groove. Without it the
    keeper is held by THROAT_PRESS alone -- 1.7 mm3 of contact against the coil's 5 N,
    which the user rightly would not take (the mortise roof caps it, but only with the
    leg ON)."""
    from cadkit.fasteners import M4, M4_BUTTON_HEAD_D, M4_BUTTON_HEAD_H, anchor_cutter
    entry, d, run = _lock_axis(sx, ly)
    up = up or LS.PRINT_UP["fixed_tenon"]
    assert run >= LOCK_RECESS + M4.insert_l + M4.min_bite, (
        "only %.2f of tenon along the lock's axis -- not enough for a recessed head, "
        "its insert and a bite" % run)
    # the head's recess, opened outward so it breaks the sloping flank cleanly
    head = teardrop_hole(M4_BUTTON_HEAD_D + 2 * 0.4, LOCK_RECESS + 4.0,
                         (entry[0] - d[0] * 4.0, entry[1] - d[1] * 4.0,
                          entry[2] - d[2] * 4.0), d, up,
                         limit_deg=LS.TEN_HOLE_LIMIT_DEG)
    # ...then the insert's pocket and the clearance on to the groove
    mouth = (entry[0] + d[0] * LOCK_RECESS, entry[1] + d[1] * LOCK_RECESS,
             entry[2] + d[2] * LOCK_RECESS)
    body = anchor_cutter(M4, mouth, d, run - LOCK_RECESS + LOCK_GROOVE + 0.4,
                         print_up=up)
    return head.union(body)


def lock_dummies(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, k: int = 0):
    """The screw and its insert, where they actually sit -- so the tab shows hardware
    and not just a hole (user)."""
    from cadkit.fasteners import (M4, M4_BUTTON_HEAD_H, m4_button_screw,
                                  seated_insert)
    entry, d, run = _lock_axis(sx, ly)
    mouth = (entry[0] + d[0] * LOCK_RECESS, entry[1] + d[1] * LOCK_RECESS,
             entry[2] + d[2] * LOCK_RECESS)
    ins = seated_insert(M4, mouth, d)
    sc = m4_button_screw(LOCK_SCREW_L)
    # m4_button_screw draws head-top at z 0 down -Z; put its head top at the recess floor
    top = (entry[0] + d[0] * (LOCK_RECESS - M4_BUTTON_HEAD_H),
           entry[1] + d[1] * (LOCK_RECESS - M4_BUTTON_HEAD_H),
           entry[2] + d[2] * (LOCK_RECESS - M4_BUTTON_HEAD_H))
    sc = _aim(sc, d).translate(top)
    return [("leg_trrs_lock_screw_%d" % k, sc),
            ("leg_trrs_lock_insert_%d" % k, ins)]


def _aim(w, d):
    """Turn a dummy drawn along -Z onto `-d` (screws drive INWARD along d)."""
    import cadquery as _cq
    v = _cq.Vector(*d)
    z = _cq.Vector(0, 0, -1)
    ax = z.cross(v)
    if ax.Length < 1e-9:
        return w if v.z < 0 else w.rotate((0, 0, 0), (1, 0, 0), 180)
    ang = math.degrees(math.acos(max(-1.0, min(1.0, z.dot(v)))))
    return w.rotate((0, 0, 0), ax.toTuple(), ang)


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
    return ([("leg_trrs_plug_%d" % k, plug), ("leg_trrs_jack_%d" % k, jack),
            ("leg_trrs_spring_%d" % k, coil),
            ("leg_trrs_throat_%d" % k, throat(sx, ly)),
            ]
            + lock_dummies(sx, ly, k) + cables(sx, ly, k))
