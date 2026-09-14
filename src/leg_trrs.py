# -*- coding: utf-8 -*-
"""THE LEG'S BLIND-MATE: a spring-floated TRRS jack in the leg's fixed sleeve, meeting
a fixed plug in the body adapter, on the butt face those two already share.

WHY IT FLOATS (user). Blind mating is the point -- the leg's signal has to connect
when the leg latches, with nothing to plug in by hand -- but a connector that depends
on the latch stopping in exactly the right place depends on a printed hook, a printed
pocket, and their tolerances agreeing to a fraction of a millimetre. So one half
rides on a SPRING: it stands PROUD at rest, the other half bottoms it BEFORE the
faces meet, and the spring holds the pair seated wherever the latch actually stops.
Same coil the latches use (latch.SPR_*, the instrument's one spring SKU, user).

WHICH HALF STANDS PROUD is not a preference -- it is the only way the pair can bottom
at all. Two recessed halves never touch: the float has to be bought with protrusion,
and FLOAT is exactly how much. It is the JACK that stands out, a blunt O9.7 barrel
that survives a knock far better than a O3.5 pin would, and the PLUG that sits back
inside the adapter's own bore with 4 of its barrel in open air. The jack's nose is
then also the lead-in that finds the plug.

WHICH HALF FLOATS is then the PLUG, and that is a corner-room decision. A floating
half needs a collar to stop it, and a collar needs a bore fatter than the connector;
the sleeve cannot pay for one (its bore's teardrop points at the mortise, and a
carrier-sized bore leaves 0.43 there), while the adapter can, because a plug stops
on a plain STEP in its own bore -- no collar, no fatter bore. So the jack is fixed
and proud in the leg, the plug floats in the adapter, and neither needs a carrier.

WHERE IT SITS. The -X/+Y corner of both parts: the middle is the octagon mortise, the
-Y side is the latch, and the corner is the only place a O10 connector clears both.
It is NOT on the diagonal, because both halves print SIDEWAYS to these bores (the
adapter builds -Y -> +Y, the sleeve the other way) and cadkit peaks a sideways bore
toward the build -- a O10.6 teardrop's apex stands 7.5 off the axis, half again its
radius, so the axis is pulled off-diagonal until that apex keeps its wall.

THE CABLE never crosses the joint. The plug's lead runs up its OWN bore -- beside
the coil, which has 2.8 of annulus to spare -- and leaves through a window in the
adapter's +Y FACE at the cap's height (the leg slides along Y to come off, so
anything leaving the adapter's TOP face would be sheared -- user). It does not get a
channel of its own: there is no room for one that keeps a wall to that face, and an
earlier attempt at one broke out through it as a slot the whole length of the part.
The jack's lead runs on down the leg from under its spacer.
"""

from __future__ import annotations

import cadquery as cq

from cadkit.holes import teardrop_hole
from cadkit.supports import printable_bore
from . import dimensions as D
from . import latch as LT
from . import leg_stack as LS

B = D.BEAD

# ── the bought parts (BOM.md: the M->F extension cable, and its plug end) ─────
JACK_D = 9.7            # the moulded inline jack's barrel (BOM: 9.1..9.7, pick high)
JACK_L = 40.0           # ...and its length (BOM: <= 40)
PLUG_D = 10.0           # the moulded plug's handle
PLUG_L = 20.0           # its length. NOT off a drawing -- typical for a 4-pole moulded
                        # plug. Confirm at purchase: the CAP is sized off it, and the
                        # cap is the only thing that would have to change
BARREL_L = 14.0         # the plug's barrel: what actually crosses the joint
BARREL_D = 3.5
CABLE_D = 3.8           # the shielded lead on either end

# ── the float, and the three numbers it turns on ─────────────────────────────
FLOAT = 3.0             # how far the jack is pushed back when the leg latches -- and
                        # so how much SLOP THE LATCH IS ALLOWED: the pair bottoms this
                        # far before the faces butt, so anything from a perfect latch
                        # to this much short of one still seats the connector
PLUG_SET = 10.0         # the plug's shoulder, above the adapter's butt face. Its
                        # barrel is 14, so 4 of barrel stands in open air and the rest
                        # is inside the adapter's bore
JACK_PROUD = PLUG_SET + FLOAT   # 13.0: the jack's mouth above the sleeve's face --
                                # FIXED, not floating. PLUG_SET is where it has to
                                # reach; FLOAT is the overshoot the plug gives way by
SPR_REST_L = 10.0       # the coil at rest: 2.0 of preload on a 12.0 free length
SPR_MATE_L = SPR_REST_L - FLOAT
PRELOAD_N = (LT.SPR_FREE - SPR_REST_L) * LT.SPR_RATE            # 5.0 N standing still
MATE_N = (LT.SPR_FREE - SPR_MATE_L) * LT.SPR_RATE               # 12.6 N seated
assert SPR_MATE_L >= LT.SPR_SOLID + 1.0, (
    "the coil is %.2f from solid when the leg latches -- no room for the latch's own "
    "slop" % (SPR_MATE_L - LT.SPR_SOLID))

# ── where, in the corner of both parts ────────────────────────────────────────
AX_X = -18 * B          # -14.4 off the leg's axis: the -X/+Y corner
AX_Y = 16 * B           # +12.8, and NOT the 14.4 that would put it on the diagonal:
                        # see the docstring -- the teardrop's apex has to keep a wall
BORE_D = 10.6           # the adapter's: the plug's handle AND the jack's nose run in it
STEP_D = 8.0            # what the handle stops on -- the barrel passes, the handle cannot
JACK_BORE_D = JACK_D - 0.1      # the sleeve's: a LIGHT PRESS on the jack's moulded
                                # jacket, which is what holds it at height with the
                                # spacer under it
WINDOW_D = CABLE_D + 1.0        # the cable's way out through the +Y face

SPACER_L = 10 * B       # 8.0 of printed tube under the jack: enough bore to press
                        # into, and it puts the jack's back well clear of the mortise
_CAP_L = LS.ADAPT_L - (PLUG_SET + PLUG_L + SPR_REST_L)       # the cap fills what is left above the
                                                # plug, up to the adapter's top face --
                                                # the face the chassis closes
assert _CAP_L >= 4 * B, (
    "the plug and its set fill %.1f of a %.1f adapter, leaving %.1f of cap"
    % (PLUG_SET + PLUG_L, LS.ADAPT_L, _CAP_L))


def _ax(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    return sx + AX_X, ly + AX_Y


def _cone(x, y, z, big, small, down=True):
    """A 45-degree cone from `big` to `small`, `down` from z. A STEP between two
    bores is an annular ledge facing the build direction -- a ceiling in parts that
    print sideways to the bore, which both of these do (measured: the plug's step
    alone was 15 mm2 of it). Coning it is what cadkit does for the same reason on
    every fastener pocket."""
    h = (big - small) / 2.0
    z0 = z - h if down else z
    return cq.Workplane("XY").add(cq.Solid.makeCone(
        (big if down else small) / 2.0, (small if down else big) / 2.0, h,
        cq.Vector(x, y, z0), cq.Vector(0, 0, 1)))


def adapter_negatives(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, up=None):
    """Cut in the BODY ADAPTER: the plug's bore from the top down to the STEP it sits
    on, the barrel's way on through that step, and the cable's window out the +Y face
    at the cap's height."""
    x, y = _ax(sx, ly)
    up = up or LS.PRINT_UP["body_adapter"]
    z0, z1 = LS.Z_BUTT, LS.Z_TOP
    step = z0 + PLUG_SET                        # the handle's seat
    out = teardrop_hole(STEP_D, (step + 0.01) - (z0 - 1.0), (x, y, z0 - 1.0), (0, 0, 1), up)
    out = out.union(teardrop_hole(BORE_D, (z1 + 1.0) - step, (x, y, step), (0, 0, 1), up))
    out = out.union(_cone(x, y, step, BORE_D, STEP_D))      # the handle's seat, coned
    # the window, at the COIL's height -- below the cap, which stays solid, and
    # above the plug, so the lead leaves where it actually is. Along this part's
    # build direction, so it prints round
    wz = step + PLUG_L + SPR_REST_L / 2.0
    out = out.union(printable_bore(WINDOW_D, (ly + LS.LEG_W / 2 + 1.0) - y,
                                   (x, y, wz), (0, 1, 0), up))
    return out


def sleeve_negatives(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, up=None):
    """Cut in the FIXED SLEEVE: the jack's bore (a light press, so the jacket itself
    holds it) and the spacer's below it, then the cable's way on down the leg."""
    x, y = _ax(sx, ly)
    up = up or LS.PRINT_UP["fixed_sleeve"]
    z0 = LS.Z_BUTT
    bot = z0 + JACK_PROUD - JACK_L              # the jack's back end
    out = teardrop_hole(JACK_BORE_D, (z0 + 1.0) - bot, (x, y, bot), (0, 0, 1), up)
    out = out.union(teardrop_hole(JACK_BORE_D, SPACER_L + 0.01,
                                  (x, y, bot - SPACER_L), (0, 0, 1), up))
    out = out.union(teardrop_hole(WINDOW_D, 20.0, (x, y, bot - SPACER_L - 19.0),
                                  (0, 0, 1), up))
    out = out.union(_cone(x, y, bot - SPACER_L, JACK_BORE_D, WINDOW_D))   # ...and this one
    return out


def cap(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """The printed plug that closes the adapter's bore at the TOP and gives the COIL
    its back seat. No fastener: the adapter butts the chassis, so the cap cannot rise
    once the leg is on."""
    x, y = _ax(sx, ly)
    z1 = LS.Z_TOP
    z0 = z1 - _CAP_L
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        (BORE_D - 0.3) / 2.0, _CAP_L, cq.Vector(x, y, z0), cq.Vector(0, 0, 1)))


def spacer(sx: float = LS.LEG_X, ly: float = LS.LEG_Y):
    """The printed tube under the jack. It is what sets JACK_PROUD -- the jack is a
    plain moulded barrel with nothing to catch on, so its height is the length of
    what it stands on, and the press fit in the bore is what keeps it there when the
    leg comes off. The cable runs straight down its middle."""
    x, y = _ax(sx, ly)
    bot = LS.Z_BUTT + JACK_PROUD - JACK_L - SPACER_L
    tube = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        JACK_BORE_D / 2.0 - 0.15, SPACER_L, cq.Vector(x, y, bot), cq.Vector(0, 0, 1)))
    return tube.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        WINDOW_D / 2.0, SPACER_L + 2.0, cq.Vector(x, y, bot - 1.0), cq.Vector(0, 0, 1))))


def dummies(sx: float = LS.LEG_X, ly: float = LS.LEG_Y, k: int = 0, mated: bool = True):
    """The bought parts where they sit. `mated` is the latched state: the plug pushed
    back FLOAT off its step, its coil that much shorter."""
    x, y = _ax(sx, ly)
    z0 = LS.Z_BUTT
    back = FLOAT if mated else 0.0
    shoulder = z0 + PLUG_SET + back              # the plug's handle, off its step
    plug = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        BARREL_D / 2.0, BARREL_L, cq.Vector(x, y, shoulder - BARREL_L), cq.Vector(0, 0, 1)))
    plug = plug.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        PLUG_D / 2.0, PLUG_L, cq.Vector(x, y, shoulder), cq.Vector(0, 0, 1))))
    coil_l = SPR_MATE_L if mated else SPR_REST_L
    coil = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        LT.SPR_OD / 2.0, coil_l, cq.Vector(x, y, shoulder + PLUG_L), cq.Vector(0, 0, 1)).cut(
        cq.Solid.makeCylinder(LT.SPR_ID / 2.0, coil_l + 2.0,
                              cq.Vector(x, y, shoulder + PLUG_L - 1.0), cq.Vector(0, 0, 1))))
    mouth = z0 + JACK_PROUD                      # the jack does not move
    jack = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        JACK_D / 2.0, JACK_L, cq.Vector(x, y, mouth - JACK_L), cq.Vector(0, 0, 1)))
    return [("leg_trrs_plug_%d" % k, plug), ("leg_trrs_jack_%d" % k, jack),
            ("leg_trrs_spring_%d" % k, coil), ("leg_trrs_spacer_%d" % k, spacer(sx, ly)),
            ("leg_trrs_cap_%d" % k, cap(sx, ly))]
