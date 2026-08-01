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

FLUSH 35.6 COLUMN (user, symmetry round: match the leg shafts): the bar
prism is BLK_W wide (Y = YC ± 17.8) and 19 tall, and its END faces sit
at station ± 17.8 — flush with the slimmed towers and the 35.6 leg
blocks above, so each +Y stack reads as ONE clean 35.6-sq column from
block top to bar bottom, all at the legs' 4.2 inset. Only the shared
TPU feet stay 44 (proud ground boots, like under the -Y blocks). The
feet are the shared legs.leg_foot dovetail inserts (mortise opens at
the bar's -Y face).

A WIRING TROUGH runs between the towers under a full-length 45° sliding-
DOVETAIL LID — no screws: the lid pieces slide in from the +X end; a TPU
detent nub in the bar top clicks into lid B's underside dimple, setting
the position and locking the stack (B butts A). The wired tower's cable
enters from the trough through a Ø8 side way and rises to the plug seat.

SEGMENTED FOR THE 255×255 BED: FLUSH-X grew the bar to the full
instrument span (644.8) — THREE ~215 pieces now, each printing STRAIGHT
(cadkit install-z joints at XS1/XS2, one per trough wall), and two ~278
lid pieces (butt splice at XL, mid-span, so each lid piece BRIDGES one
bar joint).

NO GLUE, and NO fastener either: the splice joints take X and Y by shape
and leave Z — the install axis — to the LID. A lid piece spans each
splice, and its 45° foot (23.8 wide) cannot rise back through either
piece's 20.6 groove mouth, so neither bar piece can lift off the other
while the lid is in. That is what "the lid is structure" already meant;
the glue was only ever belt-and-braces on top of it.

FRAME: modelled at ABSOLUTE X/Y (the legs' real stations, +Y rail); Z is
local with 0 = the plate bottom (build.py translates by ground + FOOT_H).
Drawn SEATED."""

from __future__ import annotations

import cadquery as cq

from cadkit.joinery import PrintSpec, joint
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
BAR_Y0 = YC - LG.BLK_W / 2                 # BLK_W (35.6) wide — matches
BAR_Y1 = YC + LG.BLK_W / 2                 # the slimmed towers/blocks: the
                                           # +Y stacks are FLUSH columns at
                                           # the legs' 4.2 inset (user)
END_MARGIN = LG.BLK_W / 2                  # bar END faces at station ±17.8,
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
PEDAL_ASSEMBLY_Z_HEIGHT = 90.0     # was 75 (a placeholder). foot_pedal.py now exists
                                   # and its stack measures 85.1 from the bar top: the
                                   # knee lever's cartridge, reused verbatim, is a 42
                                   # free-length coil plus guide post plus back-stop
                                   # screw. Raised to 90 with 4.9 to spare, and
                                   # foot_pedal asserts against this number so the two
                                   # cannot drift apart. NOTE the budget line below no
                                   # longer has slack the way it did — the leg blocks
                                   # (top 91) and the pedal stack (top ~104) now share
                                   # a Z band and only their X separation keeps them
                                   # apart; the overlap gate is what proves it.
LID_Z0 = 15.0
FOOT_PAD = 12.0

# ── SEGMENTATION (255×255 bed) + the full-length sliding-DOVETAIL lid ──
# everything here DERIVES from the leg stations (they are chassis-owned and
# have moved before — never hardcode absolutes against them).
# FLUSH-X: the bar spans the WHOLE instrument (644.8) — past any two-piece
# diagonal — so THREE ~215 pieces, each printing STRAIGHT, joined by cadkit
# install-z joints (the chassis-segment pattern).
XS1 = BAR_X0 + 215.0   # -X splice (mid-trough)
XS2 = BAR_X1 - 215.0   # +X splice (mid-trough)
XL = (LATCHES[0][0] + LATCHES[1][0]) / 2   # lid butt-splice: mid-span,
                   # ~107 from each bar splice so each lid piece BRIDGES
                   # one bar joint — the lid IS the splice's Z lock (the
                   # install axis the joint leaves free), not just a roof
LID_XA = LATCHES[1][0] + LG.BLK_W / 2 + 0.4   # lid span: between the
LID_XB = LATCHES[0][0] - LG.BLK_W / 2 - 0.4   # FUSED towers, 0.4 tip gaps
TROUGH_X0 = LATCHES[1][0] + LG.BLK_W / 2 + 0.6   # wiring trough: runs
TROUGH_X1 = LATCHES[0][0] - LG.BLK_W / 2 - 0.6   # right up to the towers
LOCK_X, LOCK_Y = LID_XB - 4.6, 7.6  # lid-lock detent nub: bar-top pocket; a
                                   # groove+dimple in lid B's underside sets
                                   # the final position, stops over-insert
                                   # and detents extraction (locks BOTH lid
                                   # pieces: B butts A). No screws anywhere.

def _stub_tower(lx: float, wired: bool) -> cq.Workplane:
    """FUSED stub tower (user: single printed piece — the tenon is part of
    the bar): BLK_W-sq button body (19..43 — slimmed with the leg blocks
    to the 4.2 inset, symmetry round) + octagon spigot (43..81) with the
    wedging-bolt channel + recessed button pocket (leg_latch_bolt/btn
    SKUs reuse verbatim; the button pocket shifts inboard to (x -10.5,
    face BLK_W/2) — at the old (x -14, face 22) the shared button pad
    would float outside the slim tower; build.py offsets the bar-tower
    button dummies to match). Authored at the ORIGIN and ROTATED 180°
    like the +Y leg stacks. The wired tower's captive CA-354S threads UP
    from the foot-mortise access below; its cable enters from the trough
    side way. Prints WITH the bar, bottom-down — plain standing
    geometry, no overhangs."""
    b = box_at(LG.BLK_W, LG.BLK_W, STUB_Z0 - BAR_H, z=(BAR_H + STUB_Z0) / 2)
    # spigot: the flush OCTAGON section tenon (round 3 — the lying leg
    # block's bed face turned the old house floor into a 28-wide ceiling
    # bridge). Constant Z-section: still prints clean standing with the bar.
    b = b.union(LG._section_tenon(39.0).translate((0, 0, STUB_Z0 - 1.0)))
    # COVER round: the leg block is truncated to the slider stem plane
    # (LG.SH_Y — its print-bed fix), so the tenon band above that plane is
    # SHAVED, INCLUDING the 1-embed slab below the seat plane (the slim
    # BLK_W body no longer buries it — it poked out as a 1-tall fin): the
    # truncated tenon lands FLUSH with the block's thinned face
    # (waist-vs-slit capture + the bolt latch are untouched)
    b = b.cut(box_at(LG.SQ_W + 2.0, 6.0, 42.0, y=LG.SH_Y + 3.0,
                     z=STUB_Z0 + 19.0))
    # bolt channel hooks the thick authored -Y (point-side) wall of the
    # block's mortise (the +Y face is the open groove); x +8 dodges the
    # TRRS way at authored (-5, +TRRS_DY)
    b = b.cut(box_at(LG.BOLT_W + 0.4, 34.0, LG.BOLT_H + 0.4,
                     x=8.0, y=2.5, z=STUB_Z0 + 31.8))
    b = b.cut(box_at(12.4, 9.0, 10.4, x=-10.5, y=LG.BLK_W / 2 - 4.4,
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
    wlx = LATCHES[1][0] + 5.0     # TRRS axis: +5 in x (the bolt owns the
    #                               other x side) and -13 in world y — the
    #                               fat flare band of the tower's octagon
    #                               (authored (-5, +13), tower rotated 180)
    wly = YC - LG.TRRS_DY
    body = body.cut(cyl(9.4, 1.7, z=STUB_Z0 + 37.4).translate((wlx, wly, 0)))
    body = body.cut(cyl(11.0, 31.2, z=STUB_Z0 + 6.3).translate((wlx, wly, 0)))
    #                    ^ way starts +6.3: the press retainer (bottom +6.4)
    #                      sits fully in Ø11 (probe-caught collar burial)
    body = body.cut(cyl(8.0, STUB_Z0 + 9.0, z=-0.5).translate((wlx, wly, 0)))
    # side way to the trough: at y wly+3.5 the Ø8 bore overlaps BOTH the
    # down-way column (wly±4) and the trough band (YC-10..YC+6.5) — a
    # snaked but continuous cable passage
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        4.0, 28.0, cq.Vector(wlx - 2.0, wly + 3.5, 11.0),
        cq.Vector(1, 0, 0))))

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


# SPLICE JOINTS — cadkit, install='z' (both pieces print bottom-down, so the
# profile lies in the plan plane and every working face is a vertical wall). One
# per trough wall. Width is what each wall can host with 1.6 (2 beads) of printed
# wall left on BOTH sides after the mortise's clearance dilation: the -Y wall runs
# YC-17.8..YC-10 (7.8 thick), the +Y wall YC+6.5..YC+17.8 (11.3).
_UP = PrintSpec(nozzle=0.8, material="PETG-GF", facing="up")
SPLICE_YC = (YC - 13.9, YC + 12.15)    # centred in each trough wall
SPLICE_W  = (4.3, 6.4)
SPLICE_L  = 15.0                       # Z engagement (the lid groove floor is 15)
SPLICE_D  = 8.0                        # room into the +X piece
SPLICE_J  = tuple(joint(width=w, length=SPLICE_L, depth=SPLICE_D,
                        tenon=_UP, mortise=_UP, install="+z")   # signed: the +X piece
                        for w in SPLICE_W)                      # drops on, so relative
                                                                # to it the tenon goes +Z


def _splice_tenons(xs: float) -> cq.Workplane:
    """The -X piece's half of both splice joints at bar splice `xs`."""
    out = None
    for j, yc in zip(SPLICE_J, SPLICE_YC):
        p = j.tenon(root=2.0).translate((xs, yc, 0.0))
        out = p if out is None else out.union(p)
    return out


def _splice_mortises(xs: float) -> cq.Workplane:
    """The +X piece's cavities — THROUGH slots, open at the piece's BOTTOM face
    (the tenons enter there as it is lowered on) and out through the top, so
    neither cavity has a ceiling to bridge. Z is unretained BY DESIGN — it is the
    install axis, and the LID closes it (see the module docstring); the two
    pieces' coplanar bottom faces set the height on the assembly bench."""
    out = None
    for j, yc in zip(SPLICE_J, SPLICE_YC):
        p = j.mortise(drop=3.0, length=BAR_H + 2.0).translate((xs, yc, -1.0))
        out = p if out is None else out.union(p)
    return out


def _clip(x0: float, x1: float) -> cq.Workplane:
    return box_at(x1 - x0, 80.0, 120.0, x=(x0 + x1) / 2, y=YC, z=40.0)


def pedal_bar_a() -> cq.Workplane:
    """-X bar piece (WIRED TRRS tower): full bar clipped at XS1 + its two
    splice tenons (piece B drops straight down onto them; the lid locks
    the stack — no glue). ~219 long — prints STRAIGHT."""
    return (_bar_full().intersect(_clip(BAR_X0 - 1.0, XS1))
            .union(_splice_tenons(XS1)))


def pedal_bar_b() -> cq.Workplane:
    """MID bar piece (trough only): clipped XS1..XS2 − the XS1 cavities +
    the XS2 tenons. ~219 long — straight print."""
    return (_bar_full().intersect(_clip(XS1, XS2))
            .cut(_splice_mortises(XS1))
            .union(_splice_tenons(XS2)))


def pedal_bar_c() -> cq.Workplane:
    """+X bar piece (plain tower): clipped at XS2 − the XS2 cavities.
    ~215 long — straight print."""
    return (_bar_full().intersect(_clip(XS2, BAR_X1 + 1.0))
            .cut(_splice_mortises(XS2)))


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
    """-X lid piece (~278 — diagonal print; bridges bar splice XS1)."""
    return _lid_full().intersect(_clip(LID_XA - 1.0, XL))


def pedal_lid_b() -> cq.Workplane:
    """+X lid piece (~278 — diagonal print; bridges bar splice XS2 +
    carries the lock dimple). Slides in last: its dimple clicks onto the
    bar-top nub, pinning BOTH lid pieces (B butts A, A butts nothing —
    the stack is set by the nub)."""
    return _lid_full().intersect(_clip(XL, LID_XB + 1.0))


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
    wly = YC - LG.TRRS_DY
    pts = [(lx + 24.0, YC - 3.0, 11.0), (lx + 14.0, wly + 3.5, 11.0),
           (lx + 5.0, wly, 11.0), (lx + 5.0, wly, 26.0)]
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
            ("pedal_bar_c", pedal_bar_c()),
            ("pedal_lid_a", pedal_lid_a()),
            ("pedal_lid_b", pedal_lid_b()),
            ("pedal_detent_nub_0", _lock_nub()),
            ("leg_foot_4",
             LG.leg_foot().translate((LATCHES[1][0], YC, -12.0))),
            ("leg_foot_5",
             LG.leg_foot().translate((LATCHES[0][0], YC, -12.0)))] + _cable_runs()
