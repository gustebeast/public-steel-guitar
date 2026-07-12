"""Pedal bar — spans the two +Y legs at ankle height, carrying their last
piece as FUSED STUB TOWERS.

The bar is the mounting rail for the (future) sensor pedals. Each end
carries a 44-sq STUB TOWER printed WITH the bar: the shortened +Y leg
shafts press DOWN onto the towers' house spigots — the leg↔body seatbelt
latch, verbatim (wedging bolt + recessed button live on the tower; the
leg block's socket is passive) — and the wired (-X) tower adds the second
vertical TRRS blind-mate: its captive CA-354S plug (threaded up through
the foot-mortise access) points UP into the 10-03404 jack in the shaft,
on the TRRS axis at station +5. Pedal height is constant regardless of
instrument height, and stomp loads go floor-direct through the bar's
feet, never through a latch.

FLUSH 44 COLUMN (user): the bar prism is 44 wide (Y = YC ± 22) and 19
tall, and its END faces sit at station ± 22 — flush with the towers, the
leg blocks above, and the TPU feet below, so each +Y stack reads as ONE
clean 44×44 column from block top to floor. The feet are the shared
legs.leg_foot dovetail inserts (mortise opens at the bar's -Y face).

A WIRING TROUGH runs between the towers under a full-length 45° sliding-
DOVETAIL LID — no screws: the lid pieces slide in from the +X end; a TPU
detent nub in the bar top clicks into lid B's underside dimple, setting
the position and locking the stack (B butts A). The wired tower's cable
enters from the trough through a Ø8 side way and rises to the plug seat.

SEGMENTED FOR THE 255×255 BED: two bar pieces (vertical slide-in
dovetail tenons + glue at XS, mid-trough; ~315/311 at 44 wide — diagonal
placement, (L+W)/√2 ≤ 255) and two lid pieces (butt splice at XL,
staggered 50 so each lid piece BRIDGES the glued bar joint).

FRAME: modelled at ABSOLUTE X/Y (the legs' real stations, +Y rail); Z is
local with 0 = the plate bottom (build.py translates by ground + FOOT_H).
Drawn SEATED."""

from __future__ import annotations

import cadquery as cq

from .helpers import box_at, cyl
from .chassis import LEG_STATIONS_X, LEG_Y
from . import legs as LG
from .legs import _house

YC = LEG_Y[0]                          # FLUSH round: the bar rides the +Y
                                       # legs' centreline, 17 inboard of the
                                       # rail — its outer face continues the
                                       # body wall plane to the floor
# one latch per foot, each opening INBOARD: (leg station, side sign)
LATCHES = ((LEG_STATIONS_X[0], -1.0),  # +X leg → plain snap latch, extends -X
           (LEG_STATIONS_X[1], +1.0))  # -X leg → TRRS latch, extends +X

BAR_H = 19.0
BAR_Y0, BAR_Y1 = YC - 22.0, YC + 22.0      # 44 wide (user): matches the
                                           # 44-sq towers/blocks/feet — the
                                           # +Y stacks are FLUSH columns
END_MARGIN = 22.0                          # bar END faces at station ±22,
                                           # flush with the tower faces
                                           # (15 used to shear the towers'
                                           # outer 6 via the piece clips)
BAR_X0 = LEG_STATIONS_X[1] - END_MARGIN
BAR_X1 = LEG_STATIONS_X[0] + END_MARGIN


STUB_Z0 = 43.0                             # tower seat plane (bar frame): the
                                           # leg block's mouth face lands here
                                           # (bar top 19 + 24 button band)
# Future pedals mount spring carriages vertically (lever pattern) above
# the bar: the legs' WIDE bottom sections must stay below this envelope
# (user placeholder; reference point x -313.80, y 43.75 = the bar top
# plane at z -699.15 global). Budget check: tower top = STUB_Z0 + 38 =
# 81, leg block top = STUB_Z0 + 48 = 91, both <= 19 + 75 = 94.
PEDAL_ASSEMBLY_Z_HEIGHT = 75.0
LID_Z0 = 15.0
FOOT_PAD = 12.0

# ── SEGMENTATION (255×255 bed, pieces placed on the DIAGONAL:
#    (L + W)/√2 ≤ 255) + the full-length sliding-DOVETAIL lid ────────────
# everything here DERIVES from the leg stations (they are chassis-owned and
# have moved before — never hardcode absolutes against them)
XS = (LATCHES[0][0] + LATCHES[1][0]) / 2   # bar splice (mid-trough): 315/311
                   # per piece at 44 wide → ≤254 diagonal footprint. Joined
                   # by vertical slide-in dovetail tenons + glue (the
                   # chassis-segment pattern).
XL = XS - 50.0     # lid butt-splice, STAGGERED 50 from XS so each lid piece
                   # bridges the glued bar joint (the lid is structure)
LID_XA = LATCHES[1][0] + 22.4      # lid span: between the FUSED stub
LID_XB = LATCHES[0][0] - 22.4      # towers (44-sq, printed with the bar)
TROUGH_X0 = LATCHES[1][0] + 22.6   # wiring trough: runs right up to the
TROUGH_X1 = LATCHES[0][0] - 22.6   # towers
LOCK_X, LOCK_Y = LID_XB - 4.6, 7.6  # lid-lock detent nub: bar-top pocket; a
                                   # groove+dimple in lid B's underside sets
                                   # the final position, stops over-insert
                                   # and detents extraction (locks BOTH lid
                                   # pieces: B butts A). No screws anywhere.

def _stub_tower(lx: float, wired: bool) -> cq.Workplane:
    """FUSED stub tower (user: single printed piece — the tenon is part of
    the bar): 44-sq button body (19..43) + house spigot (43..85) with the
    wedging-bolt channel + recessed button pocket (leg_latch_bolt/btn SKUs
    reuse verbatim, frame = seat plane 43). Authored at the ORIGIN and
    ROTATED 180° like the +Y leg stacks, so the house gable, bolt and
    ledge all face the leg block's rotated features. The wired tower's
    captive CA-354S threads UP from the foot-mortise access below; its
    cable enters from the trough side way. Prints WITH the bar,
    bottom-down — plain standing geometry, no overhangs."""
    b = box_at(LG.SQ_W, LG.SQ_W, STUB_Z0 - BAR_H, z=(BAR_H + STUB_Z0) / 2)
    b = b.union(_house(27.7, -15.85, 1.85, 38.0).translate((0, 0, STUB_Z0)))
    # bolt channel on the house FLOOR side (pre-rotation -y → global +y;
    # the gabled receiving mortise has no room on the roof side)
    b = b.cut(box_at(LG.BOLT_W + 0.4, 30.0, LG.BOLT_H + 0.4,
                     x=8.0, y=-12.2, z=STUB_Z0 + 31.8))
    b = b.cut(box_at(12.4, 9.0, 10.4, x=-14.0, y=LG.SQ_W / 2 - 4.4,
                     z=STUB_Z0 - 11.0))
    b = b.rotate((0, 0, 0), (0, 0, 1), 180).translate((lx, YC, 0))
    return b


def _foot_mortise_cutter(lx: float) -> cq.Workplane:
    """The SHARED foot mortise (legs.foot_mortise_cutter) at a station —
    one TPU foot SKU serves the -Y leg blocks and the bar."""
    return LG.foot_mortise_cutter().translate((lx, YC, 0))


def _bar_full() -> cq.Workplane:
    """The full bar (pre-split): slim prism − slots − latch cavities −
    wiring TROUGH − the full-length dovetail lid GROOVE − the lid-lock
    detent pocket. The trough connects both latch cavities (the TRRS
    pigtail routes to the mid-bar electronics without crossing a slot)."""
    body = box_at(BAR_X1 - BAR_X0, BAR_Y1 - BAR_Y0, BAR_H,
                  x=(BAR_X0 + BAR_X1) / 2, y=(BAR_Y0 + BAR_Y1) / 2, z=BAR_H / 2)
    body = body.union(_stub_tower(LATCHES[0][0], False))
    body = body.union(_stub_tower(LATCHES[1][0], True))
    body = body.cut(_foot_mortise_cutter(LATCHES[0][0]))
    body = body.cut(_foot_mortise_cutter(LATCHES[1][0]))
    # wired tower's ways — cut AFTER the union (they pierce both the tower
    # and the bar prism beneath it): captive plug seat, Ø8 down-way to the
    # foot-mortise access, Ø8 side way to the trough
    wlx = LATCHES[1][0] + 5.0     # TRRS axis offset +5 (the bolt owns the
    #                               other side of the house floor band)
    body = body.cut(cyl(9.4, 1.7, z=STUB_Z0 + 37.4).translate((wlx, YC, 0)))
    body = body.cut(cyl(11.0, 31.2, z=STUB_Z0 + 6.3).translate((wlx, YC, 0)))
    #                    ^ way starts +6.3: the press retainer (bottom +6.4)
    #                      sits fully in Ø11 (probe-caught collar burial)
    body = body.cut(cyl(8.0, STUB_Z0 + 9.0, z=-0.5).translate((wlx, YC, 0)))
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        4.0, 28.0, cq.Vector(wlx - 2.0, YC, 11.0), cq.Vector(1, 0, 0))))

    # wiring TROUGH (open top; the lid roofs it)
    body = body.cut(box_at(TROUGH_X1 - TROUGH_X0, 16.5, BAR_H - 4.0 + 1,
                           x=(TROUGH_X0 + TROUGH_X1) / 2, y=YC - 1.75,
                           z=(4.0 + BAR_H + 1) / 2))

    # full-length dovetail lid GROOVE (45° flanks — the rails print as
    # self-supporting overhangs with the bar lying bottom-down): runs out
    # the +X end face for lid insertion (the short open stub over the +X
    # slot region is cosmetic)
    groove = (cq.Workplane("YZ")
              .polyline([(-15.4, 15.0), (8.4, 15.0), (6.8, 19.0),
                         (6.8, 20.0), (-13.8, 20.0), (-13.8, 19.0)])
              .close().extrude(BAR_X1 + 1 - LID_XA))
    body = body.cut(cq.Workplane("XY").add(groove.val())
                    .translate((LID_XA, YC, 0)))
    # lid-lock detent pocket (a TPU nub sits 1.2 proud of the groove floor)
    body = body.cut(cyl(3.8, 3.2, z=LID_Z0 - 3.1)
                    .translate((LOCK_X, YC + LOCK_Y, 0)))
    return body


def _splice_prisms(grow: float) -> cq.Workplane:
    """The two vertical slide-in dovetail tenons at the bar splice (plan-view
    trapezoids on the front/back trough walls, z 0..15 so the lid groove
    stays untouched). grow=0 → piece A's tenons; grow>0 → piece B's slots."""
    out = None
    for y0, y1 in ((-14.5, -11.5), (9.25, 12.25)):      # tenon roots
        p = (cq.Workplane("XY")
             .polyline([(XS - grow * 4, y0 + YC - grow),
                        (XS + 4.0 + grow, y0 - 0.7 + YC - grow),
                        (XS + 4.0 + grow, y1 + 0.7 + YC + grow),
                        (XS - grow * 4, y1 + YC + grow)])
             .close().extrude(15.0 + grow))
        out = p if out is None else out.union(p)
    return out


def pedal_bar_a() -> cq.Workplane:
    """-X bar piece (TRRS tower): full bar clipped at the splice + the two
    dovetail tenons (slide piece B down onto them, glue). 315 long × 44 —
    fits the 255² bed on the diagonal ((315+44)/√2 = 254)."""
    half = box_at(XS - (BAR_X0 - 1), 80.0, 120.0,
                  x=(BAR_X0 - 1 + XS) / 2, y=YC, z=40.0)
    return _bar_full().intersect(half).union(_splice_prisms(0.0))


def pedal_bar_b() -> cq.Workplane:
    """+X bar piece (plain tower): clipped at the splice − the tenon slots
    (0.2 fit). 311 long × 44 — diagonal print."""
    half = box_at((BAR_X1 + 1) - XS, 80.0, 120.0,
                  x=(XS + BAR_X1 + 1) / 2, y=YC, z=40.0)
    return _bar_full().intersect(half).cut(_splice_prisms(0.2))


def _lid_full() -> cq.Workplane:
    """The full sliding-dovetail lid (pre-split): a 4-thick plate with 45°
    dovetail flanks riding the bar's top groove — ONE lid roofs the wiring
    trough AND both latch cavities (no separate latch lids, no screws). It
    carries the thumb-post slots, the TPU finger sockets, the latch detent
    nub pockets, and the underside LOCK groove (both pieces slide over the
    bar-top nub; lid B's groove ends in a dimple that clicks in at the
    final position). Prints TOP-FACE DOWN: the flanks are 45°."""
    prof = (cq.Workplane("YZ")
            .polyline([(-15.3, 15.0), (8.3, 15.0), (6.7, 19.0), (-13.7, 19.0)])
            .close().extrude(LID_XB - LID_XA))
    body = cq.Workplane("XY").add(prof.val()).translate((LID_XA, YC, 0))
    # underside LOCK groove (rides the bar-top nub, 0.5 squeeze) + dimple
    body = body.cut(box_at(LID_XB - LID_XA + 2, 4.3, 0.7,
                           x=(LID_XA + LID_XB) / 2, y=YC + LOCK_Y,
                           z=LID_Z0 + 0.35))
    body = body.cut(cyl(4.4, 1.7, z=LID_Z0 - 0.1)
                    .translate((LOCK_X, YC + LOCK_Y, 0)))
    return body


def pedal_lid_a() -> cq.Workplane:
    """-X lid piece (covers the TRRS latch; 241.4 — prints straight)."""
    half = box_at(XL - (LID_XA - 1), 80.0, 120.0,
                  x=(LID_XA - 1 + XL) / 2, y=YC, z=40.0)
    return _lid_full().intersect(half)


def pedal_lid_b() -> cq.Workplane:
    """+X lid piece (covers the plain latch + carries the lock dimple;
    321.6 — diagonal print). Slides in last: its lock dimple clicks onto
    the bar-top nub, pinning BOTH lid pieces (B butts A, A butts nothing —
    the stack is set by the nub)."""
    half = box_at((LID_XB + 1) - XL, 80.0, 120.0,
                  x=(XL + LID_XB + 1) / 2, y=YC, z=40.0)
    return _lid_full().intersect(half)


def _lock_nub() -> cq.Workplane:
    """The lid-lock instance: same printed nub, pressed into the bar-top
    pocket; sits 1.2 proud of the groove floor into lid B's lock groove."""
    return cyl(4.0, 4.0, z=LID_Z0 - 2.8).translate((LOCK_X, YC + LOCK_Y, 0))


def nub_part() -> cq.Workplane:
    """The single printed TPU nub (export once, print 1 — the lid lock)."""
    return _lock_nub()


def _cable_runs():
    """DEMO bar cable: from the trough, through the wired stub's side way,
    up its core to the captive plug seat (the column-side cable is placed
    by build.py with the leg stack). Rises on the TRRS axis — offset +5
    from the station, matching the down-way and the plug seat."""
    lx = LATCHES[1][0]
    pts = [(lx + 24.0, YC, 11.0), (lx + 14.0, YC, 11.0),
           (lx + 5.0, YC, 11.0), (lx + 5.0, YC, 26.0)]
    out = None
    for a, bpt in zip(pts[:-1], pts[1:]):
        va, vb = cq.Vector(*a), cq.Vector(*bpt)
        rod = cq.Workplane("XY").add(cq.Solid.makeCylinder(
            1.85, (vb - va).Length, va, vb - va))
        out = rod if out is None else out.union(rod)
    return [("pedal_trrs_cable_bar", out)]


def assembly_parts():
    """[(name, workplane)] — printed bar parts + the bar cable, drawn
    SEATED, absolute X/Y, z0 = plate bottom (build.py lifts by ground +
    FOOT_H and places the stubs/bolts/buttons/plug/jack dummies with the
    leg stacks)."""
    return [("pedal_bar_a", pedal_bar_a()),
            ("pedal_bar_b", pedal_bar_b()),
            ("pedal_lid_a", pedal_lid_a()),
            ("pedal_lid_b", pedal_lid_b()),
            ("pedal_detent_nub_0", _lock_nub()),
            ("leg_foot_4",
             LG.leg_foot().translate((LATCHES[1][0], YC, -12.0))),
            ("leg_foot_5",
             LG.leg_foot().translate((LATCHES[0][0], YC, -12.0)))] + _cable_runs()
