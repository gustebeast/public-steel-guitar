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

The plug (Same Sky SP-3541: Ø3.5 barrel + Ø4.5 lead ring + 5×5 pin body)
sits in a cradle on the slider: the backstop pushes it in, the FRONT
RETAINER wall (top-open Ø4.7 keyhole over the lead ring, bearing on the
body's front face) pulls it out, the lid caps it. Its harness gets a ~15
service loop in the latch cavity, then exits inboard toward the pedal
electronics.

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
from .legs import SHAFT_D

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
SLOT_W = SHAFT_D + 0.4                     # 20.4 walls on the shaft's rounds;
                                           # the back is ROUND (r10.2 hugging
                                           # the shaft — its key flat faces
                                           # the MOUTH and is the latch's
                                           # bearing plane)

# ── the LATCH — IDENTICAL at both feet (the TRRS foot's slider is the SAME
#    design with the plug cradle grown on): 15.0 travel, NO bevel — always
#    retract to install or remove (an un-retracted install REFUSES: a cam
#    could only yield ~6 of the 15, and on the TRRS side would bend the
#    barrel). x offsets from the leg axis, flipped inboard by ls. ─────────
TRAVEL = 15.0
BOLT_TIP, BOLT_X1 = -4.3, 27.0             # head/body tip: clears the corridor
                                           # at 14.7 of the stroke (the plug at
                                           # 14.4) and bears across ~11.4 of
                                           # the shaft's key flat
BOLT_Y0, BOLT_Y1 = -13.6, -9.4             # thin BODY band
HEAD_Y1 = -7.0                             # blocking head: 0.2 off the shaft's
                                           # key flat (the print-bed face IS
                                           # the latch's bearing plane)
HEAD_X1 = 9.0
BOLT_Z0, BOLT_Z1 = 2.4, 14.7
CH_Y0, CH_Y1 = -13.9, -9.1                 # bolt-body lane (0.3 clr/side)
CH_Z0 = 2.4                                # cavity floor
CAV_X0, CAV_X1 = 10.0, 47.0                # ONE open-top cavity per latch
CAV_Y0, CAV_Y1 = -13.9, 6.5                # (slider + cradle + kick spring
                                           # + cable loop all live here)
POST_X0, POST_X1 = 13.0, 17.0              # thumb-pad post through the lid
PAD_X0, PAD_X1 = 12.5, 21.0
PAD_Y0, PAD_Y1 = -14.5, -8.5
PAD_Z0, PAD_Z1 = BAR_H + 0.3, BAR_H + 3.8
FNG_T, FNG_W = 4.5, 4.0                    # TPU finger blade: X × Y
FNG_X0 = 37.5                              # kick spring: presses the bolt
                                           # body's end face only over the
                                           # last ~4.5 of opening (holding
                                           # retracted is nearly free)
FNG_Z0, FNG_ZTOP = 2.7, 15.0
FNG_BASE_H = 3.5
LID_Z0 = 15.0

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
LID_XA = LATCHES[1][0] + 10.4      # lid span: between the slots' inboard
LID_XB = LATCHES[0][0] - 10.4      # walls (the shafts fill the slots to the
                                   # bar top — the lid cannot cross them)
TROUGH_X0 = LATCHES[1][0] + 45.0   # wiring trough: connects the two latch
TROUGH_X1 = LATCHES[0][0] - 45.0   # cavities (no leg slot is ever crossed)
LOCK_X, LOCK_Y = LID_XB - 4.6, 7.6  # lid-lock detent nub: bar-top pocket; a
                                   # groove+dimple in lid B's underside sets
                                   # the final position, stops over-insert
                                   # and detents extraction (locks BOTH lid
                                   # pieces: B butts A). No screws anywhere.

# ── TRRS delta (-X foot only): the slider's plug cradle ─────────────────
# Retracted (+15): barrel tip at 11 — the corridor (±10.2) is FULLY clear.
# Parts (DigiKey): male = Same Sky SP-3541 (Ø3.5×14.5 barrel + Ø4.5×3 lead
# ring that stays 0.5 proud of the mouth at the full 14 insertion; 5×5×8
# body, 4 solder pins — carried pins-UP in the cradle, wires solder from
# the open top before the lid slides on); female = Same Sky
# SJ-43516-SMT-TR (14.0 mating depth), embedded in legs.leg_shaft_trrs.
# Seated (drawn): jack mouth at the shaft surface (x' 10), tip at -4.
TR_Z = 8.7                                 # connector axis (bar-local z)
PLUG_TIP = -4.0                            # barrel tip (x', seated)
BODY_X0, BODY_X1 = 13.5, 21.6              # SP-3541 body (5 × 5) in the cradle
CRDL_X1 = 24.0                             # cradle backstop end


def _slot_cutter(lx: float, square_ls: float = 0.0) -> cq.Workplane:
    """Slot for one leg: Ø20.4 walls + ROUND back (r10.2 hugging the shaft's
    round side; the key flat faces the mouth as the latch's bearing plane),
    full height, opening -Y, 45° lead-in flares. square_ls ≠ 0 squares the
    back on that (inboard) side to fit the TRRS shaft's corner-fill."""
    # mouth box ends at y=0, where the r10.2 back circle is exactly SLOT_W
    # wide — the wall meets the round back TANGENTIALLY (a longer box left a
    # 0.2-thick curved sliver ridge between wall and circle)
    cut = box_at(SLOT_W, 17.0, BAR_H + 2, x=lx, y=YC - 8.5, z=BAR_H / 2)
    cut = cut.union(cyl(SLOT_W, BAR_H + 2, z=-1).translate((lx, YC, 0)))
    # TOP-BAND cavity (EVERY slot — the shelf band is on every shaft):
    # slides past the shaft's rectangular SHELF; the SOLID corners below it
    # sit under the shelf's underside = positive hold-down. Same SLOT_W as
    # the walls and back at the circle's +10.2 tangent — no 0.2 ledges (the
    # 20.0-wide shelf keeps its 0.2/side fit)
    cut = cut.union(box_at(SLOT_W, 27.2, 3.8, x=lx, y=YC - 3.4, z=18.5))
    if square_ls:
        cut = cut.union(box_at(SLOT_W / 2, 27.4, BAR_H + 2,
                               x=lx + square_ls * SLOT_W / 4,
                               y=YC - 3.3, z=BAR_H / 2))
    for s in (1, -1):
        cut = cut.union(
            cq.Workplane("XY")
            .polyline([(s * SLOT_W / 2, -16.0), (s * (SLOT_W / 2 + 4), -16.0),
                       (s * SLOT_W / 2, -11.0)])
            .close().extrude(BAR_H + 2).translate((lx, YC, -1)))
    return cut


def _bar_full() -> cq.Workplane:
    """The full bar (pre-split): slim prism − slots − latch cavities −
    wiring TROUGH − the full-length dovetail lid GROOVE − the lid-lock
    detent pocket. The trough connects both latch cavities (the TRRS
    pigtail routes to the mid-bar electronics without crossing a slot)."""
    body = box_at(BAR_X1 - BAR_X0, BAR_Y1 - BAR_Y0, BAR_H,
                  x=(BAR_X0 + BAR_X1) / 2, y=(BAR_Y0 + BAR_Y1) / 2, z=BAR_H / 2)
    body = body.cut(_slot_cutter(LATCHES[0][0]))
    body = body.cut(_slot_cutter(LATCHES[1][0], LATCHES[1][1]))

    # the IDENTICAL latch cavity at each foot: one open-top pocket swallows
    # the slider, (TRRS-side) cradle, plug travel, kick spring + cable loop
    for lx, ls in LATCHES:
        body = body.cut(box_at(CAV_X1 - CAV_X0, CAV_Y1 - CAV_Y0,
                               BAR_H - CH_Z0 + 1,
                               x=lx + ls * (CAV_X0 + CAV_X1) / 2,
                               y=YC + (CAV_Y0 + CAV_Y1) / 2,
                               z=(CH_Z0 + BAR_H + 1) / 2))

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
    half = box_at(XS - (BAR_X0 - 1), 80.0, 40.0,
                  x=(BAR_X0 - 1 + XS) / 2, y=YC, z=10.0)
    return _bar_full().intersect(half).union(_splice_prisms(0.0))


def pedal_bar_b() -> cq.Workplane:
    """+X bar piece (plain foot): clipped at the splice − the tenon slots
    (0.2 fit). 291.6 long — diagonal print."""
    half = box_at((BAR_X1 + 1) - XS, 80.0, 40.0,
                  x=(XS + BAR_X1 + 1) / 2, y=YC, z=10.0)
    return _bar_full().intersect(half).cut(_splice_prisms(0.2))


def _bolt_core(lx: float, ls: float) -> cq.Workplane:
    """The latch slider — IDENTICAL design at both feet: extended bolt body
    + blocking head (tip at BOLT_TIP: the lock disengages at the same
    stroke point as a carried plug) + thumb post/pad + detent groove. No
    bevel: always retract to install or remove."""
    body = box_at(BOLT_X1 - BOLT_TIP, BOLT_Y1 - BOLT_Y0, BOLT_Z1 - BOLT_Z0,
                  x=lx + ls * (BOLT_TIP + BOLT_X1) / 2,
                  y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                  z=(BOLT_Z0 + BOLT_Z1) / 2)
    body = body.union(box_at(HEAD_X1 - BOLT_TIP, HEAD_Y1 - BOLT_Y0,
                             BOLT_Z1 - BOLT_Z0,
                             x=lx + ls * (BOLT_TIP + HEAD_X1) / 2,
                             y=YC + (BOLT_Y0 + HEAD_Y1) / 2,
                             z=(BOLT_Z0 + BOLT_Z1) / 2))
    body = body.union(box_at(POST_X1 - POST_X0, BOLT_Y1 - BOLT_Y0,
                             PAD_Z0 - BOLT_Z1,
                             x=lx + ls * (POST_X0 + POST_X1) / 2,
                             y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                             z=(BOLT_Z1 + PAD_Z0) / 2))
    body = body.union(box_at(PAD_X1 - PAD_X0, PAD_Y1 - PAD_Y0, PAD_Z1 - PAD_Z0,
                             x=lx + ls * (PAD_X0 + PAD_X1) / 2,
                             y=YC + (PAD_Y0 + PAD_Y1) / 2,
                             z=(PAD_Z0 + PAD_Z1) / 2))
    # closed-position DETENT groove in the post's +Y face: the lid's TPU nub
    # clicks in (0.8 lateral engagement) — every latch holds itself closed
    # with or without a TRRS in it (the spring deflects SIDEWAYS a fixed
    # 0.8, so the detent works regardless of the latch's travel)
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.0, 5.25, cq.Vector(lx + ls * 15.0, YC - 8.2, 14.0),
        cq.Vector(0, 0, 1))))
    return body


def pedal_bolt() -> cq.Workplane:
    """+X foot slider, drawn CLOSED: the bare latch (retract 15, release,
    thumb-press to the detent click)."""
    return _bolt_core(*LATCHES[0])


def pedal_bolt_trrs() -> cq.Workplane:
    """-X foot slider, drawn CLOSED/SEATED: the SAME latch design with the
    TRRS MOUNT grown on — bridge + open-top plug CRADLE for the SP-3541.
    The plug drops in pins-UP (its Ø4.5 lead ring falls through the front
    retainer's top-open keyhole; solder access from the open top before
    the lid slides on): U-channel walls locate the 5-wide body, the
    backstop pushes it in, the FRONT RETAINER wall bears on the body's
    front face so retraction pulls it back out of the jack. At closed the
    retainer sits 2.1 off the shaft; nothing enters the leg but the barrel.
    An un-retracted install butts the shaft on the flat head and REFUSES
    (no bevel) — it cannot bend the barrel."""
    lx, ls = LATCHES[1]
    body = _bolt_core(lx, ls)
    # bridge: bolt body band → cradle wall
    body = body.union(box_at(8.0, 6.0, 8.0,
                             x=lx + ls * 16.0, y=YC - 6.6, z=TR_Z))
    # cradle — SUBTRACTIVE (one prism, hollowed; additive walls made wonky
    # sliver geometry): box → open-roof middle cut for the 5×5 body →
    # Ø4.8 hole in the -x wall that passes the barrel + Ø4.5 lead ring but
    # NOT the body. That wall bears on the body's front face (0.2) so
    # retraction PULLS the plug out of the jack; the +x wall is the
    # backstop. Assembly: thread the barrel through the hole (slight
    # tilt), lower the body in, solder from the open roof; the lid caps it.
    crdl = box_at(12.0, 8.8, 9.0, x=lx + ls * 17.9, y=YC, z=8.4)
    crdl = crdl.cut(box_at(8.5, 5.5, 7.6, x=lx + ls * 17.55, y=YC, z=9.9))
    crdl = crdl.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.4, 3.0, cq.Vector(lx + ls * 11.4, YC, TR_Z), cq.Vector(ls, 0, 0))))
    body = body.union(crdl)
    return body


def finger_part() -> cq.Workplane:
    """The single printed TPU finger (export once, print 2)."""
    return pedal_latch_finger(*LATCHES[0])


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
    # thumb-post slots + finger sockets + latch detent-nub pockets — the
    # SAME stations at both feet (the latches are identical)
    for lx, ls in LATCHES:
        body = body.cut(box_at(POST_X1 - POST_X0 + TRAVEL + 0.6,
                               BOLT_Y1 - BOLT_Y0 + 0.6, BAR_H - LID_Z0 + 2,
                               x=lx + ls * (POST_X0 - 0.3 + POST_X1 + TRAVEL + 0.3) / 2,
                               y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                               z=(LID_Z0 + BAR_H) / 2))
        body = body.cut(box_at(FNG_T + 0.8, FNG_W + 0.8, FNG_BASE_H,
                               x=lx + ls * (FNG_X0 + FNG_T / 2),
                               y=YC + (CH_Y0 + CH_Y1) / 2,
                               z=LID_Z0 + FNG_BASE_H / 2))
        # TPU detent-nub press pocket (Ø3.8 for the Ø4 nub): the nub bulges
        # into the post lane and clicks into the post's closed groove
        body = body.cut(cyl(3.8, BAR_H - LID_Z0 + 2, z=LID_Z0 - 1)
                        .translate((lx + ls * 15.0, YC - 8.2, 0)))
    # underside LOCK groove (rides the bar-top nub, 0.5 squeeze) + dimple
    body = body.cut(box_at(LID_XB - LID_XA + 2, 4.3, 0.7,
                           x=(LID_XA + LID_XB) / 2, y=YC + LOCK_Y,
                           z=LID_Z0 + 0.35))
    body = body.cut(cyl(4.4, 1.7, z=LID_Z0 - 0.1)
                    .translate((LOCK_X, YC + LOCK_Y, 0)))
    # the slot-mouth lead-in flares CONTINUE through the lid (same wedges as
    # _slot_cutter): otherwise the lid's square plan corner overhangs the
    # bar's chamfer right in the funnel path and catches the incoming foot
    for lx, _ in LATCHES:
        for s in (1, -1):
            body = body.cut(
                cq.Workplane("XY")
                .polyline([(s * SLOT_W / 2, -16.0),
                           (s * (SLOT_W / 2 + 4), -16.0),
                           (s * SLOT_W / 2, -11.0)])
                .close().extrude(BAR_H + 2).translate((lx, YC, -1)))
    return body


def pedal_lid_a() -> cq.Workplane:
    """-X lid piece (covers the TRRS latch; 241.4 — prints straight)."""
    half = box_at(XL - (LID_XA - 1), 80.0, 40.0,
                  x=(LID_XA - 1 + XL) / 2, y=YC, z=10.0)
    return _lid_full().intersect(half)


def pedal_lid_b() -> cq.Workplane:
    """+X lid piece (covers the plain latch + carries the lock dimple;
    321.6 — diagonal print). Slides in last: its lock dimple clicks onto
    the bar-top nub, pinning BOTH lid pieces (B butts A, A butts nothing —
    the stack is set by the nub)."""
    half = box_at((LID_XB + 1) - XL, 80.0, 40.0,
                  x=(XL + LID_XB + 1) / 2, y=YC, z=10.0)
    return _lid_full().intersect(half)


def pedal_latch_finger(lx: float, ls: float) -> cq.Workplane:
    """TPU KICK finger (identical at both feet): base potted in the lid,
    blade hangs down at the far end of the slider's travel — engaged only
    over the last ~4.5 of opening (pressing the bolt body's end face), so
    holding the latch retracted is nearly free, and release shoves the
    slider toward the leg (thumb completes the click). Symmetric boxes →
    ONE printed part serves both (print 2)."""
    yc = YC + (CH_Y0 + CH_Y1) / 2
    blade = box_at(FNG_T, FNG_W, FNG_ZTOP - FNG_Z0,
                   x=lx + ls * (FNG_X0 + FNG_T / 2), y=yc,
                   z=(FNG_Z0 + FNG_ZTOP) / 2)
    base = box_at(FNG_T + 0.8, FNG_W + 0.8, FNG_BASE_H,
                  x=lx + ls * (FNG_X0 + FNG_T / 2), y=yc,
                  z=FNG_ZTOP + FNG_BASE_H / 2)
    return blade.union(base)


def pedal_detent_nub(lx: float, ls: float) -> cq.Workplane:
    """TPU detent nub (Ø4 × 4): pressed into the lid's Ø3.8 pocket, its side
    bulges ~0.8 into the thumb-post lane and clicks into the post's closed
    groove — the hold-closed force of EVERY latch, independent of any
    connector (~5-10 N pop, a light drag while sliding). Print 3 (two latch
    nubs + the lid-lock nub)."""
    return (cyl(4.0, BAR_H - LID_Z0, z=LID_Z0)
            .translate((lx + ls * 15.0, YC - 8.2, 0)))


def _lock_nub() -> cq.Workplane:
    """The lid-lock instance: same printed nub, pressed into the bar-top
    pocket; sits 1.2 proud of the groove floor into lid B's lock groove."""
    return cyl(4.0, 4.0, z=LID_Z0 - 2.8).translate((LOCK_X, YC + LOCK_Y, 0))


def nub_part() -> cq.Workplane:
    """The single printed TPU nub (export once, print 3)."""
    return pedal_detent_nub(*LATCHES[0])


def _trrs_jack() -> cq.Workplane:
    """DEMO leg-side female jack — Same Sky SJ-43516-SMT-TR (DigiKey;
    ~14.5×6×5 body, 14.0 mating depth): mating axis X, mouth flush at the
    shaft's inboard face, Ø3.6 way."""
    lx, ls = LATCHES[1]
    j = box_at(14.5, 6.0, 5.0, x=lx + ls * (10.0 - 14.5 / 2), y=YC, z=TR_Z)
    return j.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.8, 15.0, cq.Vector(lx + ls * 10.5, YC, TR_Z), cq.Vector(-ls, 0, 0))))


def _trrs_plug() -> cq.Workplane:
    """DEMO bar-side male plug — Same Sky SP-3541 (DigiKey; Ø3.5×11.5
    barrel + Ø4.5×3 lead + 5×5×12.1 body, 4 solder pins), drawn SEATED:
    tip at x' -4 (full 14 insertion), body in the cradle pins-UP, wire stub
    over the backstop with its service loop implied."""
    lx, ls = LATCHES[1]
    p = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.75, 14.5, cq.Vector(lx + ls * 10.5, YC, TR_Z), cq.Vector(-ls, 0, 0)))
    p = p.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.25, 3.0, cq.Vector(lx + ls * BODY_X0, YC, TR_Z), cq.Vector(-ls, 0, 0))))
    p = p.union(box_at(BODY_X1 - BODY_X0, 5.0, 5.0,
                       x=lx + ls * (BODY_X0 + BODY_X1) / 2, y=YC, z=TR_Z))
    for px in (15.0, 17.0, 19.0, 21.0):     # solder pins, facing UP
        p = p.union(box_at(0.6, 0.6, 2.5, x=lx + ls * px, y=YC,
                           z=TR_Z + 2.5 + 1.25))
    return p


def _wire_bar() -> cq.Workplane:
    """DEMO bar-side wires — FOUR 28 AWG conductors (Ø1.1 insulated; the
    smallest gauge already in the cabinet — fine here: the CAN stub is far
    too short for 28 AWG's resistance/impedance to matter, and the sensor
    supply is mA-level): one per plug pin, through the latch cavity (the
    ~15 service loop lives here) into the wiring trough toward the mid-bar
    electronics."""
    lx, ls = LATCHES[1]
    out = None
    for i, px in enumerate((15.0, 17.0, 19.0, 21.0)):
        rod = cq.Workplane("XY").add(cq.Solid.makeCylinder(
            0.55, 70.0 - px,
            cq.Vector(lx + ls * px, YC - 1.8 + 1.2 * i, 13.2),
            cq.Vector(ls, 0, 0)))
        out = rod if out is None else out.union(rod)
    return out


def _wire_leg() -> cq.Workplane:
    """DEMO leg-side wires — the same FOUR 28 AWG conductors from the jack
    pads up the shaft's Ø6 hollow centre bore (stub — they continue inside
    the sleeve/segments to the chassis)."""
    lx, _ = LATCHES[1]
    out = None
    for dx, dy in ((-1.1, -1.1), (1.1, -1.1), (-1.1, 1.1), (1.1, 1.1)):
        rod = cq.Workplane("XY").add(cq.Solid.makeCylinder(
            0.55, 28.0, cq.Vector(lx + dx, YC + dy, 11.4),
            cq.Vector(0, 0, 1)))
        out = rod if out is None else out.union(rod)
    return out


def assembly_parts():
    """[(name, workplane)] — printed parts + connector DEMOs, drawn SEATED,
    absolute X/Y, z0 = plate bottom (build.py lifts by ground + FOOT_H)."""
    (lx_a, ls_a), (lx_b, ls_b) = LATCHES
    return [("pedal_bar_a", pedal_bar_a()),
            ("pedal_bar_b", pedal_bar_b()),
            ("pedal_lid_a", pedal_lid_a()),
            ("pedal_lid_b", pedal_lid_b()),
            ("pedal_bolt", pedal_bolt()),
            ("pedal_bolt_trrs", pedal_bolt_trrs()),
            ("pedal_latch_finger_0", pedal_latch_finger(lx_a, ls_a)),
            ("pedal_latch_finger_1", pedal_latch_finger(lx_b, ls_b)),
            ("pedal_detent_nub_0", pedal_detent_nub(lx_a, ls_a)),
            ("pedal_detent_nub_1", pedal_detent_nub(lx_b, ls_b)),
            ("pedal_detent_nub_2", _lock_nub()),
            ("pedal_trrs_jack", _trrs_jack()),
            ("pedal_trrs_plug", _trrs_plug()),
            ("pedal_wire_0", _wire_bar()),
            ("pedal_wire_1", _wire_leg())]
