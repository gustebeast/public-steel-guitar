"""Pedal bar — spans the two +Y legs at ankle height; retract-slide-release.

The bar is the mounting rail for the (future) sensor pedals. It attaches to
the +Y legs' shafts (legs.py): each end has a SLOT, open toward the
instrument (-Y) — Ø20.4 walls register X, a ROUND back (r10.2) hugs the
shaft's round side, and the shaft's single key flat faces the MOUTH, where
it is the latch bolt's bearing plane (the leg's single-D key aims
everything; at the TRRS leg the slot's inboard back corner is SQUARED to
fit that shaft's corner-fill extension, whose flat also face-seats the
wall). Z: the plate rests on the foot caps; anti-lift is every shaft's
SHELF band overhanging the slot's solid corners (the seated TRRS plug adds
belt-and-braces at the -X foot). Bar = one slim prism (Y -16..+15), ends
just past each leg; each latch sits INBOARD of its leg.

Y RETENTION — one sliding-bolt latch per foot, both opening INBOARD; rigid
lock, no flexing structural member. Closed, the bolt's thickened HEAD bears
flat-on-flat on the shaft's key flat — the PRINT-BED surface reused as the
bearing plane: normal pure Y, a tug cannot cam it open, wear cannot loosen
it, seated Y float ~0.4 total (0.2 flat + 0.2 round-back seat). The thumb
pad rides an integral post through an X slot in the lid.

The LATCHES ARE IDENTICAL at both feet (15.0 travel, extended head, no
bevel, far-end kick spring, detent-nub hold-closed): RETRACT both pads
(the +X slot clears; at the -X foot the carried plug also clears the leg's
envelope), slide the bar on/off freely, RELEASE — the kick springs shove
the sliders toward the legs — and THUMB-PRESS each pad to its click. The
-X slider is the SAME design with a TRRS MOUNT grown on: it carries the
male plug (axis X, pointing at the leg), so that latch is also the
connector actuator — the plug clicks into the jack embedded in the shaft
(legs.leg_shaft_trrs; wires up the leg's Ø6 hollow centre). Deliberately NO
tip bevel anywhere: an un-retracted install butts the shaft against the
flat head and refuses — a cam could only yield ~6 of the needed 15 and, on
the TRRS side, the leg would bend the barrel. The kick springs engage only
over the last ~4.5 of opening, so holding the pads retracted while
positioning the bar costs almost nothing.

The plug (Tensility CA-354S, factory-molded on its own shielded cable:
Ø3.5×14 barrel + Ø10×12.6 handle + Ø6 spring relief) lies in a Ø10.4
cradle channel on the slider: the rear wall backstops insertion, the
FRONT wall (top-open Ø5.4 keyhole around the barrel, bearing on the
handle's front face) pulls it out, the lid caps it. Its cable exits the
rear keyhole through the latch cavity into the trough, cut + crimped into
an XH housing at the first bar tee — no solder anywhere.

SEGMENTED FOR THE 255×255 BED: two bar pieces (dovetail-splice + glue at
XS, mid-trough; 322/292 — diagonal placement, (L+W)/√2 ≤ 255) and two lid
pieces (butt splice at XL, staggered 55 so each lid piece BRIDGES the glued
bar joint). A WIRING TROUGH runs between the two latch cavities (the TRRS
pigtail reaches the mid-bar electronics without crossing a leg slot), and
ONE full-length 45° sliding-DOVETAIL LID roofs trough + both latches — no
screws: the lid pieces slide in from the +X end; a third TPU detent nub in
the bar top clicks into lid B's underside dimple, setting the position and
locking the stack (B butts A). Assembly: glue the bar halves; drop each
slider in with its plug/finger; slide lid A, then lid B to the click; press
the latch nubs down through their lid pockets.

FRAME: modelled at ABSOLUTE X/Y (the legs' real stations, +Y rail); Z is
local with 0 = the plate bottom (build.py translates by ground + FOOT_H).
Drawn SEATED: bolts closed, plug fully inserted.
"""

from __future__ import annotations

import cadquery as cq

from .helpers import box_at, cyl
from .chassis import LEG_STATIONS_X, Y_HI
from . import legs as LG
from .legs import _house

YC = Y_HI                              # leg axes sit on the +Y rail centreline
# one latch per foot, each opening INBOARD: (leg station, side sign)
LATCHES = ((LEG_STATIONS_X[0], -1.0),  # +X leg → plain snap latch, extends -X
           (LEG_STATIONS_X[1], +1.0))  # -X leg → TRRS latch, extends +X

# plate: 19 tall inside the 20-tall notch band (1.0 anti-lift clearance up)
BAR_H = 19.0
BAR_Y0, BAR_Y1 = YC - 16.0, YC + 15.0      # slim prism: 2.1 front wall ahead
                                           # of the bolt channel, 4.6 back
                                           # wall behind the round slot back
END_MARGIN = 15.0                          # bar end past each leg axis
BAR_X0 = LEG_STATIONS_X[1] - END_MARGIN
BAR_X1 = LEG_STATIONS_X[0] + END_MARGIN


# ── the LATCH — IDENTICAL at both feet (the TRRS foot's slider is the SAME
#    design with the plug cradle grown on): 15.0 travel, NO bevel — always
#    retract to install or remove (an un-retracted install REFUSES: a cam
#    could only yield ~6 of the 15, and on the TRRS side would bend the
#    barrel). x offsets from the leg axis, flipped inboard by ls. ─────────
# ROUND 4: the sliding latches are GONE — the bar carries two STUB TOWERS
# (the last ~72 of the +Y legs, semipermanently M4-mounted through the
# bar) and installs by pressing DOWN onto them: house spigot + wedging
# bolt + recessed button up top (the leg↔body latch, verbatim), TPU feet
# below, the second vertical TRRS blind-mate inside the wired one.
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
XS = (LATCHES[0][0] + LATCHES[1][0]) / 2   # bar splice (mid-trough): ~303
                   # per piece (+4 tenon) → ≤240 diagonal footprint. Joined
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
    body = body.cut(cyl(11.0, 29.5, z=STUB_Z0 + 8.0).translate((wlx, YC, 0)))
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
    """-X bar piece (TRRS foot): full bar clipped at the splice + the two
    dovetail tenons (slide piece B down onto them, glue). 321.6 long —
    fits the 255² bed on the diagonal."""
    half = box_at(XS - (BAR_X0 - 1), 80.0, 120.0,
                  x=(BAR_X0 - 1 + XS) / 2, y=YC, z=40.0)
    return _bar_full().intersect(half).union(_splice_prisms(0.0))


def pedal_bar_b() -> cq.Workplane:
    """+X bar piece (plain foot): clipped at the splice − the tenon slots
    (0.2 fit). 291.6 long — diagonal print."""
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
    by build.py with the leg stack)."""
    lx = LATCHES[1][0]
    pts = [(lx + 24.0, YC, 11.0), (lx + 14.0, YC, 11.0),
           (lx, YC, 11.0), (lx, YC, 26.0)]
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
