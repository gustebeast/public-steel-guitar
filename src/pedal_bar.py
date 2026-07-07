"""Pedal bar — spans the two +Y legs at ankle height; press-on / thumb-off.

The bar is the mounting rail for the (future) sensor pedals. It attaches to
the +Y legs' shaft WAISTS (legs.py): each end has a C-SLOT, open toward the
instrument (-Y), that wraps the waist — flat side walls grip the key flats
(exact X registration, no twist about the leg), the round back hugs the Ø18,
the waist's two shoulders capture the bar in Z, and the plate rests on the
foot-cap / lower-shoulder plane. Everything lives INSIDE the bar's prism —
no lumps beyond its Y faces, and the bar ends just past each leg (enough
wall to close the slot, nothing more): the whole latch sits INBOARD (-X) of
its leg, in the span between the legs.

Y RETENTION — the latch (+X leg only until the feel is validated; mirror to
the -X leg after): a rigid SLIDING BOLT, no flexing structural member. The
bolt rides an X channel in the plate's front band; closed, its flat back
face blocks the corridor in FRONT of the seated waist (face normal pure -Y,
so a tug on the bar cannot cam it open — a hard geometric lock that wear
cannot loosen). The tip's 45° plan bevel is the entry ramp: pushing the bar
on cams the bolt aside (rigid slide, not material flex) and it snaps back
at seat. To remove: grab the bar end, THUMB-SLIDE the top pad INBOARD
(5 mm) — the bolt clears the corridor — and pull the bar off the leg. The
pad rides an integral post through an X slot in the lid.

The only spring is the TPU FINGER: hung from a lid socket, it bends (~0.5
N/mm at the pusher tab — a compression TPU block would be ~30× too stiff)
to return the bolt. It is unloaded at rest and when latched, deflected only
during actuation, so it never creeps. No coil, no extra BOM spring — and no
ejector cartridge: unplugging (and the future TRRS un-mate) is the same
hand-pull that removes the bar. If the latch's designed play (~1.3 at the
flat face) ever buzzes, a thin TPU pad in the slot root takes it up.

FRAME: modelled at ABSOLUTE X/Y (the legs' real stations, +Y rail); Z is
local with 0 = the plate bottom = the waist's lower shoulder (build.py
translates by ground + FOOT_H). Drawn SEATED: bolt closed. DEMO: the bar is
one prism — longer than any print bed; it gets segmented for printing once
the pedals land on it.
"""

from __future__ import annotations

import pathlib
import sys

import cadquery as cq

from .helpers import box_at, cyl, cyl_y
from .chassis import LEG_STATIONS_X, Y_HI
from .legs import WAIST_D, WAIST_FLAT_W, SHAFT_D, SHAFT_FLAT_W, FOOT_H

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "freecad"))
from fasteners import (M2_SELFTAP_D, M2_SHAFT_CLR_D, M2_HEAD_RECESS_D,  # noqa: E402
                       M2_HEAD_RECESS_H, M2_INSERT_PILOT_D, M2_INSERT_DEPTH)

LX_LATCH, LX_PLAIN = LEG_STATIONS_X    # latch on the +X (bridge-end) leg
YC = Y_HI                              # leg axes sit on the +Y rail centreline
LS = -1.0                              # latch SIDE: the mechanism extends
                                       # INBOARD (-X) of its leg — the bar
                                       # ends just past the leg on +X

# plate: 19 tall inside the 20-tall waist (1.0 anti-lift clearance up top)
BAR_H = 19.0
BAR_Y0, BAR_Y1 = YC - 16.0, YC + 18.0      # one clean prism: 2.1 front wall
                                           # ahead of the bolt channel, 8.8
                                           # back wall behind the slot root
END_MARGIN = 15.0                          # bar end past each leg axis: the
                                           # 8.2 slot wall + 6.8 of closure
BAR_X0, BAR_X1 = LX_PLAIN - END_MARGIN, LX_LATCH + END_MARGIN
SLOT_W = WAIST_FLAT_W + 0.4                # 16.4 across the waist flats
SLOT_R = (WAIST_D + 0.4) / 2               # 9.2 round back

# ── latch geometry: x offsets from the latch leg axis, all POSITIVE here
#    and mirrored inboard by LS (y' = y−YC as before) ────────────────────
# bolt: closed tip at |x'| 4.0 (covers 4..8.2 of the ±8 corridor); thumb
# travel 5.0 clears it. The tip carries a thickened HEAD whose flat back
# face bears on the waist's front CHORD (legs.WAIST_CHORD_Y): flat-on-flat,
# normal pure Y — a tug on the bar has NO cam-open component, and the
# escape play is just the 0.2 fit (the +Y seat at the slot root is the
# matching 0.2, so the seated bar floats ~0.4 total in Y).
BOLT_X0, BOLT_X1 = 4.0, 27.0
BOLT_Y0, BOLT_Y1 = -13.6, -9.4             # thin BODY band (rides the channel)
HEAD_X1, HEAD_Y1 = 9.0, -7.2               # blocking head: 0.2 off the chord
BOLT_Z0, BOLT_Z1 = 2.4, 14.7
BOLT_TRAVEL = 5.0
DP_X0, DP_X1, DP_Y1 = 8.0, 14.3, -6.9      # deep pocket: the head's travel
                                           # garage behind the slot wall
TAB_X1, TAB_Z1 = 28.2, 5.5                 # low pusher tab → the TPU finger
                                           # bends about a long arm (soft)
CH_X0, CH_X1 = 8.0, 38.0                   # channel + finger bay (starts 0.2
                                           # INSIDE the slot wall at 8.2 so no
                                           # sliver survives across the bolt;
                                           # reaches 38 so the bent blade fits)
CH_Y0, CH_Y1 = -13.9, -9.1                 # channel walls (0.3 clr per side)
CH_Z0 = 2.4                                # channel floor

# thumb pad on an integral post through an X slot in the lid: slide 5 to
# open. The post sweep (13..22) stays clear of the finger base (27.8+).
POST_X0, POST_X1 = 13.0, 17.0
PAD_X0, PAD_X1 = 12.5, 21.0
PAD_Y0, PAD_Y1 = -14.5, -8.5               # wider than the lid slot → covers it
PAD_Z0, PAD_Z1 = BAR_H + 0.3, BAR_H + 3.8

# TPU return finger: hangs from a lid socket, blade bends in X
FNG_T, FNG_W = 4.5, 4.0                    # blade: X thickness × Y width
FNG_X0 = TAB_X1                            # front face rests on the bolt tab
FNG_Z0, FNG_ZTOP = 2.7, 15.0               # blade band; base potted above
FNG_BASE_H = 3.5                           # socket depth in the lid underside

# lid: recessed flush into the bar top, 2× M2 (self-tap + insert pockets)
LID_Z0 = 15.0
LID_X0, LID_X1 = 8.4, 38.4
LID_Y0, LID_Y1 = -16.5, -4.0
M2_XY = ((18.0, -6.55), (32.0, -6.55))     # both OUTSIDE the head's deep
                                           # pocket (x ≤ 14.3) so the insert
                                           # pockets keep a solid wall

# ── TRRS at the PLAIN (-X) foot, inboard (+X) side. x'' offsets from the
#    plain leg axis, positive INBOARD; connector axis along Y. The bar-side
#    RIGHT-ANGLE plug points -Y out of the bar's front wall; the leg-side
#    jack rides a RISER on pedal_jack_foot (keyed to the shaft flats, so the
#    deterministic leg clocking aims it at the bar). MORTISE & TENON grab
#    4.5 BEFORE the plug can touch the jack (tenon at 18.5 from seat, plug
#    contact at 14.0, C-slot only from 7.0) — misalignment lands on printed
#    walls, never on the connector. The jack's Ø6 nose enters the bar's Ø7
#    bore for the last ~3 as fine alignment.
TR_X, TR_Z = 16.0, 9.5                     # connector axis (x'' / bar-local z)
TR_HOLE_D = 7.0                            # front-wall bore (receives the nose)
PKT_X0, PKT_X1 = 10.3, 21.7                # plug-body pocket (open top)
PKT_Y0, PKT_Y1 = -13.0, -1.5               # ... behind the 3-thick front wall
CBL_X1 = 50.0                              # cable channel: pocket → inboard
MORT_W, MORT_H = 10.4, 13.0                # mortise (tenon 10.0 × 12.6)
MORT_XC, MORT_ZC = 29.3, 9.8               # ... beside the pocket, 2.4 wall
MORT_Y1 = 3.6                              # mortise back (tenon tip +2.5 + clr)
TEN_TIP, TEN_CH = 2.5, 2.5                 # tenon tip y'' / tip chamfer
RISER_X0, RISER_X1 = 6.0, 38.5             # riser column footprint
RISER_Y0, RISER_Y1 = -30.0, -16.5          # ... 0.5 shy of the bar front (-16)
RISER_Z1 = 18.5
JCK_NOSE_D, JCK_NOSE_Y1 = 6.0, -13.0       # jack nose: riser face → the bar
                                           # wall bore; mouth = plug-body face
FOOT_ARM_Y0 = -11.0                        # foot arm starts clear of the Ø20


def _lx(c: float) -> float:
    """Absolute X of a latch-frame offset c (mirrored inboard by LS)."""
    return LX_LATCH + LS * c


def _slot_cutter(lx: float) -> cq.Workplane:
    """C-slot for one leg: flat walls over the key flats + round back, full
    height, opening -Y, with 45° lead-in flares at the mouth."""
    cut = box_at(SLOT_W, 24.0, BAR_H + 2, x=lx, y=YC - 12.0, z=BAR_H / 2)
    cut = cut.union(cyl(2 * SLOT_R, BAR_H + 2, z=-1).translate((lx, YC, 0)))
    for s in (1, -1):
        cut = cut.union(
            cq.Workplane("XY")
            .polyline([(s * SLOT_W / 2, -16.0), (s * (SLOT_W / 2 + 4), -16.0),
                       (s * SLOT_W / 2, -11.0)])
            .close().extrude(BAR_H + 2).translate((lx, YC, -1)))
    return cut


def pedal_bar() -> cq.Workplane:
    """The bar body: one prism − slots − latch channel/recess − M2 bores."""
    body = box_at(BAR_X1 - BAR_X0, BAR_Y1 - BAR_Y0, BAR_H,
                  x=(BAR_X0 + BAR_X1) / 2, y=(BAR_Y0 + BAR_Y1) / 2, z=BAR_H / 2)
    body = body.cut(_slot_cutter(LX_LATCH)).cut(_slot_cutter(LX_PLAIN))

    # latch channel strip (open to the top; the lid roofs it)
    body = body.cut(box_at(CH_X1 - CH_X0, CH_Y1 - CH_Y0, BAR_H - CH_Z0 + 1,
                           x=_lx((CH_X0 + CH_X1) / 2), y=YC + (CH_Y0 + CH_Y1) / 2,
                           z=(CH_Z0 + BAR_H + 1) / 2))
    # deep pocket: the bolt HEAD's travel garage (reaches the chord depth)
    body = body.cut(box_at(DP_X1 - DP_X0, DP_Y1 - CH_Y0, BAR_H - CH_Z0 + 1,
                           x=_lx((DP_X0 + DP_X1) / 2), y=YC + (CH_Y0 + DP_Y1) / 2,
                           z=(CH_Z0 + BAR_H + 1) / 2))
    # lid recess in the bar top
    body = body.cut(box_at(LID_X1 - LID_X0, LID_Y1 - LID_Y0, BAR_H - LID_Z0 + 1,
                           x=_lx((LID_X0 + LID_X1) / 2), y=YC + (LID_Y0 + LID_Y1) / 2,
                           z=(LID_Z0 + BAR_H + 1) / 2))
    # M2: Ø2.2 self-tap below a Ø3.3×3.5 insert pocket (CLAUDE.md convention)
    for mx, my in M2_XY:
        body = body.cut(cyl(M2_SELFTAP_D, LID_Z0 - 6.0, z=6.0)
                        .translate((_lx(mx), YC + my, 0)))
        body = body.cut(cyl(M2_INSERT_PILOT_D, M2_INSERT_DEPTH + 0.5,
                            z=LID_Z0 - M2_INSERT_DEPTH)
                        .translate((_lx(mx), YC + my, 0)))

    # ── TRRS at the plain foot (inboard, +X of that leg) ──────────────
    px = LX_PLAIN
    # front-wall bore: the plug barrel exits / the jack's Ø6 nose enters
    body = body.cut(cyl_y(TR_HOLE_D, 6.0, y0=YC - 17.5, x=px + TR_X, z=TR_Z))
    # right-angle plug-body pocket (open top: the plug drops in, barrel
    # through the wall; the cable channel keys it — glue dab for now)
    body = body.cut(box_at(PKT_X1 - PKT_X0, PKT_Y1 - PKT_Y0, BAR_H - 4.0 + 1,
                           x=px + (PKT_X0 + PKT_X1) / 2,
                           y=YC + (PKT_Y0 + PKT_Y1) / 2,
                           z=(4.0 + BAR_H + 1) / 2))
    # cable route: the right-angle lead exits the pocket inboard, jogs +Y
    # BEFORE the mortise's x-range (the tenon owns y −17..+3.6 there), then
    # runs down the bar inside the back band behind the slot root
    body = body.cut(box_at(23.9 - 18.0, 24.5, 9.0,          # +Y jog
                           x=px + (18.0 + 23.9) / 2, y=YC + (-13.0 + 11.5) / 2,
                           z=TR_Z))
    body = body.cut(box_at(CBL_X1 - 22.0, 5.0, 9.0,          # back-band run
                           x=px + (22.0 + CBL_X1) / 2, y=YC + 13.0, z=TR_Z))
    # mortise: grabs the riser's tenon 4.5 BEFORE the plug can touch the jack
    body = body.cut(box_at(MORT_W, MORT_Y1 + 17.0, MORT_H,
                           x=px + MORT_XC, y=YC + (MORT_Y1 - 17.0) / 2,
                           z=MORT_ZC))
    return body


def pedal_bolt() -> cq.Workplane:
    """The sliding bolt, drawn CLOSED. Flat -Y-normal blocking face (a tug on
    the bar cannot cam it open), 45° plan bevel on the tip (the incoming
    waist cams it aside on push-on), low pusher tab for the TPU finger, and
    an integral post + thumb pad through the lid slot — slide 5 inboard to
    open."""
    body = box_at(BOLT_X1 - BOLT_X0, BOLT_Y1 - BOLT_Y0, BOLT_Z1 - BOLT_Z0,
                  x=_lx((BOLT_X0 + BOLT_X1) / 2), y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                  z=(BOLT_Z0 + BOLT_Z1) / 2)
    # blocking HEAD: thickened to 0.2 off the waist chord (flat-on-flat seat)
    body = body.union(box_at(HEAD_X1 - BOLT_X0, HEAD_Y1 - BOLT_Y0,
                             BOLT_Z1 - BOLT_Z0,
                             x=_lx((BOLT_X0 + HEAD_X1) / 2),
                             y=YC + (BOLT_Y0 + HEAD_Y1) / 2,
                             z=(BOLT_Z0 + BOLT_Z1) / 2))
    # tip bevel (plan view) — the entry ramp
    body = body.cut(cq.Workplane("XY")
                    .polyline([(LS * BOLT_X0, BOLT_Y0),
                               (LS * (BOLT_X0 + 3.0), BOLT_Y0),
                               (LS * BOLT_X0, BOLT_Y0 + 3.0)])
                    .close().extrude(BOLT_Z1 - BOLT_Z0 + 2)
                    .translate((LX_LATCH, YC, BOLT_Z0 - 1)))
    # pusher tab (low, so the finger bends about a long arm)
    body = body.union(box_at(TAB_X1 - BOLT_X1, BOLT_Y1 - BOLT_Y0,
                             TAB_Z1 - BOLT_Z0,
                             x=_lx((BOLT_X1 + TAB_X1) / 2),
                             y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                             z=(BOLT_Z0 + TAB_Z1) / 2))
    # post through the lid slot + thumb pad above the lid
    body = body.union(box_at(POST_X1 - POST_X0, BOLT_Y1 - BOLT_Y0, PAD_Z0 - BOLT_Z1,
                             x=_lx((POST_X0 + POST_X1) / 2),
                             y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                             z=(BOLT_Z1 + PAD_Z0) / 2))
    body = body.union(box_at(PAD_X1 - PAD_X0, PAD_Y1 - PAD_Y0, PAD_Z1 - PAD_Z0,
                             x=_lx((PAD_X0 + PAD_X1) / 2),
                             y=YC + (PAD_Y0 + PAD_Y1) / 2,
                             z=(PAD_Z0 + PAD_Z1) / 2))
    return body


def pedal_latch_lid() -> cq.Workplane:
    """Latch lid: roofs the channel (recessed flush), carries the thumb-pad
    slot, sockets the TPU finger, 2× M2 down into the bar."""
    body = box_at(LID_X1 - LID_X0, LID_Y1 - LID_Y0, BAR_H - LID_Z0,
                  x=_lx((LID_X0 + LID_X1) / 2), y=YC + (LID_Y0 + LID_Y1) / 2,
                  z=(LID_Z0 + BAR_H) / 2)
    # thumb-slide slot: post width + 5 travel + 0.3 clr each side
    body = body.cut(box_at(POST_X1 - POST_X0 + BOLT_TRAVEL + 0.6,
                           BOLT_Y1 - BOLT_Y0 + 0.6, BAR_H - LID_Z0 + 2,
                           x=_lx((POST_X0 - 0.3 + POST_X1 + BOLT_TRAVEL + 0.3) / 2),
                           y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                           z=(LID_Z0 + BAR_H) / 2))
    # TPU finger base socket (press-in from below, before the lid screws on)
    body = body.cut(box_at(FNG_T + 0.8, FNG_W + 0.8, FNG_BASE_H,
                           x=_lx(FNG_X0 + FNG_T / 2),
                           y=YC + (CH_Y0 + CH_Y1) / 2,
                           z=LID_Z0 + FNG_BASE_H / 2))
    for mx, my in M2_XY:
        body = body.cut(cyl(M2_SHAFT_CLR_D, BAR_H - LID_Z0 + 2, z=LID_Z0 - 1)
                        .translate((_lx(mx), YC + my, 0)))
        body = body.cut(cyl(M2_HEAD_RECESS_D, M2_HEAD_RECESS_H + 1,
                            z=BAR_H - M2_HEAD_RECESS_H)
                        .translate((_lx(mx), YC + my, 0)))
    return body


def pedal_latch_finger() -> cq.Workplane:
    """TPU return finger: base potted in the lid, blade hangs down behind the
    bolt's pusher tab. Bending spring (~0.5 N/mm at the tab) — unloaded at
    rest and when latched, deflected only during actuation, so no creep."""
    yc = YC + (CH_Y0 + CH_Y1) / 2
    blade = box_at(FNG_T, FNG_W, FNG_ZTOP - FNG_Z0,
                   x=_lx(FNG_X0 + FNG_T / 2), y=yc,
                   z=(FNG_Z0 + FNG_ZTOP) / 2)
    base = box_at(FNG_T + 0.8, FNG_W + 0.8, FNG_BASE_H,
                  x=_lx(FNG_X0 + FNG_T / 2), y=yc,
                  z=FNG_ZTOP + FNG_BASE_H / 2)
    return blade.union(base)


def pedal_jack_foot() -> cq.Workplane:
    """Replaces the TPU foot cap at the PLAIN (+Y, -X) leg: PETG-GF, bore
    KEYED to the shaft flats (the deterministic leg clocking aims it), with
    an arm + RISER column standing 0.5 shy of the bar's front face. The
    riser hosts the panel TRRS jack (axis Y, mouth toward the bar) and the
    alignment TENON that reaches the bar's mortise 4.5 before the plug can
    touch the jack. A flush TPU pad (pedal_foot_pad) fills the underside
    recess so floor behaviour matches the other feet. Prints on its BACK
    (-Y face down): the tenon points up, no supports. Bar-local frame
    (z0 = plate bottom): the cap spans -12..0."""
    px = LX_PLAIN
    body = cyl(SHAFT_D + 8.0, FOOT_H, z=-FOOT_H).translate((px, YC, 0))
    # arm under the bar (0.5 clr) out to the riser; starts clear of the Ø20
    body = body.union(box_at(RISER_X1, FOOT_ARM_Y0 - RISER_Y0, FOOT_H - 0.5,
                             x=px + RISER_X1 / 2,
                             y=YC + (RISER_Y0 + FOOT_ARM_Y0) / 2,
                             z=-FOOT_H + (FOOT_H - 0.5) / 2))
    body = body.union(box_at(RISER_X1 - RISER_X0, RISER_Y1 - RISER_Y0,
                             RISER_Z1 + 0.5,
                             x=px + (RISER_X0 + RISER_X1) / 2,
                             y=YC + (RISER_Y0 + RISER_Y1) / 2,
                             z=(-0.5 + RISER_Z1) / 2))
    # alignment tenon (10 × 12.6, chamfered tip)
    ten = box_at(MORT_W - 0.4, TEN_TIP - RISER_Y1, MORT_H - 0.4,
                 x=px + MORT_XC, y=YC + (RISER_Y1 + TEN_TIP) / 2, z=MORT_ZC)
    hw, hh = (MORT_W - 0.4) / 2, (MORT_H - 0.4) / 2
    for s in (1, -1):     # top/bottom tip chamfers (lead-in funnel)
        ten = ten.cut(cq.Workplane("YZ")
                      .polyline([(TEN_TIP + 0.1, s * hh),
                                 (TEN_TIP + 0.1, s * (hh - TEN_CH)),
                                 (TEN_TIP - TEN_CH, s * hh)])
                      .close().extrude(MORT_W)
                      .translate((px + MORT_XC - hw, YC, MORT_ZC)))
        ten = ten.cut(cq.Workplane("XY")
                      .polyline([(s * hw, TEN_TIP + 0.1),
                                 (s * (hw - TEN_CH), TEN_TIP + 0.1),
                                 (s * hw, TEN_TIP - TEN_CH)])
                      .close().extrude(MORT_H)
                      .translate((px + MORT_XC, YC, MORT_ZC - hh)))
    body = body.union(ten)
    # keyed bore (grips the shaft's bottom Ø20/flats section)
    body = body.cut(cyl(SHAFT_D + 0.2, FOOT_H - 3.0 + 1, z=-FOOT_H + 3.0)
                    .intersect(box_at(SHAFT_FLAT_W + 0.2, SHAFT_D + 4,
                                      FOOT_H + 2, z=-FOOT_H / 2))
                    .translate((px, YC, 0)))
    # TPU pad recess in the underside (pad prints flush)
    body = body.cut(cyl(24.0, 3.5, z=-FOOT_H - 0.5).translate((px, YC, 0)))
    # jack bores: Ø9.2 body from the back, Ø6.2 nose way through the face
    body = body.cut(cyl_y(9.2, 13.0, y0=YC + RISER_Y0 - 1, x=px + TR_X, z=TR_Z))
    body = body.cut(cyl_y(6.2, 3.0, y0=YC - 18.5, x=px + TR_X, z=TR_Z))
    return body


def pedal_foot_pad() -> cq.Workplane:
    """TPU floor pad, flush in the jack foot's underside recess."""
    return (cyl(23.6, 3.0, z=-FOOT_H)
            .translate((LX_PLAIN, YC, 0)))


def _trrs_jack() -> cq.Workplane:
    """DEMO panel TRRS jack: Ø9 body in the riser, Ø6 nose protruding into
    the bar's front-wall bore at seat (the last-3-mm fine alignment)."""
    px = LX_PLAIN
    j = cyl_y(9.0, 12.0, y0=YC - 30.5, x=px + TR_X, z=TR_Z)   # body: in the
    #   Ø9.2 riser bore, stopping at the 2-thick panel wall (y −18.5)
    j = j.union(cyl_y(JCK_NOSE_D, 5.5, y0=YC - 18.5, x=px + TR_X, z=TR_Z))
    return j.cut(cyl_y(3.7, 16.0, y0=YC - 29.0, x=px + TR_X, z=TR_Z))


def _trrs_plug() -> cq.Workplane:
    """DEMO right-angle TRRS plug: Ø3.5 × 14 barrel out the bar's front wall
    (drawn fully seated in the jack), overmould body in the pocket, cable
    stub elbowing inboard along the bar's channel."""
    px = LX_PLAIN
    p = cyl_y(3.5, 14.0, y0=YC - 27.0, x=px + TR_X, z=TR_Z)
    p = p.union(box_at(11.0, 11.0, 10.0, x=px + TR_X, y=YC - 7.5, z=TR_Z))
    # cable stub: out the body inboard, +Y jog ahead of the mortise, then
    # down the bar's back band (mirrors the routed channel)
    p = p.union(box_at(4.5, 4.5, 4.5, x=px + 21.0, y=YC - 9.0, z=TR_Z))
    p = p.union(box_at(4.5, 21.0, 4.5, x=px + 21.0, y=YC + 0.75, z=TR_Z))
    p = p.union(box_at(22.0, 4.5, 4.5, x=px + 33.5, y=YC + 13.0, z=TR_Z))
    return p


def assembly_parts():
    """[(name, workplane)] — printed parts + connector DEMOs, drawn SEATED,
    in absolute X/Y with z0 = the plate bottom (build.py lifts the whole set
    by ground + FOOT_H)."""
    return [("pedal_bar", pedal_bar()),
            ("pedal_bolt", pedal_bolt()),
            ("pedal_latch_lid", pedal_latch_lid()),
            ("pedal_latch_finger", pedal_latch_finger()),
            ("pedal_jack_foot", pedal_jack_foot()),
            ("pedal_foot_pad", pedal_foot_pad()),
            ("pedal_trrs_jack", _trrs_jack()),
            ("pedal_trrs_plug", _trrs_plug())]
