"""Pedal bar — spans the two +Y legs at ankle height; press-on / thumb-off.

The bar is the mounting rail for the (future) sensor pedals. It attaches to
the +Y legs' shafts (legs.py): each end has a rectangular SLOT, open toward
the instrument (-Y) — Ø20.4 walls register X on the shaft's rounds, and the
flat back FACE-seats on the shaft's single key flat (the leg's single-D key
aims everything). Z: the plate rests on the foot cap + the chord notch's
lower crescent; anti-lift is the CLOSED bolt head sitting inside the notch
(the head hits the upper crescent if the bar rides up). Everything lives
INSIDE the bar's prism — no lumps beyond its Y faces, and the bar ends just
past each leg (enough wall to close the slot, nothing more): each latch
sits INBOARD of its leg, in the span between the legs.

Y RETENTION — one latch per foot, mirror images of each other (both open
INBOARD): a rigid SLIDING BOLT, no flexing structural member. The bolt
rides an X channel in the plate's front band; closed, its thickened HEAD's
flat back face bears on the waist's front CHORD (legs.WAIST_CHORD_Y):
flat-on-flat, normal pure Y — a tug on the bar has NO cam-open component,
it's a hard geometric lock that wear cannot loosen, and the escape play is
just the 0.2 fit (the +Y face seat at the slot back is the matching 0.2, so
the seated bar floats ~0.4 total in Y). The tip's 45° plan bevel is the
entry ramp: pushing the bar on cams the bolt aside (rigid slide, not
material flex) and it snaps back at seat. To remove: grab the bar ends,
THUMB-SLIDE each top pad inboard (6.4 mm) and pull the bar off. The pad
rides an integral post through an X slot in the lid. Because the two
latches are mirrored,
the bolt and lid each come in a plain and a `_m` (mirrored) printed
variant; the TPU finger is symmetric — one part, print 2.

The only spring is the TPU FINGER: hung from a lid socket, it bends (~0.5
N/mm at the pusher tab — a compression TPU block would be ~30× too stiff)
to return the bolt. It is unloaded at rest and when latched, deflected only
during actuation, so it never creeps. No coil, no extra BOM spring.

TRRS AUTO-MATE at the -X foot: the CAN/TRRS connection clicks in as the bar
seats — no separate plug-in step. Female jack in the LEG (embedded in the
shaft through its key flat), male right-angle plug in the bar's back band
with its barrel reaching -Y into the leg's envelope; the slot's hard walls
align the pair 2mm before the connector halves can touch (see the TRRS
constants block for the full δ sequence and legs.leg_shaft_trrs for the
leg side). Removal is the same thumb-slide + pull — the pull un-mates it.

FRAME: modelled at ABSOLUTE X/Y (the legs' real stations, +Y rail); Z is
local with 0 = the plate bottom = the waist's lower shoulder (build.py
translates by ground + FOOT_H). Drawn SEATED: bolts closed. DEMO: the bar
is one prism — longer than any print bed; it gets segmented for printing
once the pedals land on it.
"""

from __future__ import annotations

import pathlib
import sys

import cadquery as cq

from .helpers import box_at, cyl
from .chassis import LEG_STATIONS_X, Y_HI
from .legs import SHAFT_D, SHAFT_FLAT_Y

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "freecad"))
from fasteners import (M2_SELFTAP_D, M2_SHAFT_CLR_D, M2_HEAD_RECESS_D,  # noqa: E402
                       M2_HEAD_RECESS_H, M2_INSERT_PILOT_D, M2_INSERT_DEPTH)

YC = Y_HI                              # leg axes sit on the +Y rail centreline
# one latch per foot, each opening INBOARD: (leg station, side sign). The
# ls=+1 latch is the mirror image of the ls=-1 one.
LATCHES = ((LEG_STATIONS_X[0], -1.0),  # +X (bridge-end) leg → latch extends -X
           (LEG_STATIONS_X[1], +1.0))  # -X (keyhead-end) leg → latch extends +X

# plate: 19 tall inside the 20-tall notch band (1.0 anti-lift clearance up)
BAR_H = 19.0
BAR_Y0, BAR_Y1 = YC - 25.0, YC + 23.0      # one clean prism. Front reaches
                                           # -25 so the slot's HARD walls
                                           # engage the shaft 16 before seat
                                           # — 2 BEFORE the TRRS barrel can
                                           # touch its jack (contact = the
                                           # 14 insertion depth). Back
                                           # reaches +23 to swallow the
                                           # right-angle plug body.
END_MARGIN = 15.0                          # bar end past each leg axis: the
                                           # 8.2 slot wall + 6.8 of closure
BAR_X0 = LEG_STATIONS_X[1] - END_MARGIN
BAR_X1 = LEG_STATIONS_X[0] + END_MARGIN
SLOT_W = SHAFT_D + 0.4                     # 20.4 walls register X on the
                                           # shaft's rounds (0.2/side)
SLOT_BACK = SHAFT_FLAT_Y + 0.2             # 7.0 flat back: FACE seat on the
                                           # shaft's single key flat (0.2)

# ── latch geometry: x offsets from the latch leg axis, all POSITIVE here
#    and flipped inboard per-latch by ls (y' = y−YC as before) ────────────
# bolt: closed tip at |x'| 4.0 — the head overlaps the chord notch over
# x 4..7.1 (the notch flat's half-width) and the ±10.2 corridor means a
# 6.4 thumb travel clears it
BOLT_X0, BOLT_X1 = 4.0, 27.0
BOLT_Y0, BOLT_Y1 = -13.6, -9.4             # thin BODY band (rides the channel)
HEAD_X1, HEAD_Y1 = 9.0, -7.2               # blocking head: 0.2 off the chord
BOLT_Z0, BOLT_Z1 = 2.4, 14.7
BOLT_TRAVEL = 6.4
DP_X0, DP_X1, DP_Y1 = 10.0, 15.7, -6.9     # deep pocket: the head's travel
                                           # garage behind the slot wall
TAB_X1, TAB_Z1 = 28.2, 5.5                 # low pusher tab → the TPU finger
                                           # bends about a long arm (soft)
CH_X0, CH_X1 = 10.0, 39.5                  # channel + finger bay (starts 0.2
                                           # INSIDE the slot wall at 10.2 so no
                                           # sliver survives across the bolt;
                                           # reaches 39.5 so the bent blade fits)
CH_Y0, CH_Y1 = -13.9, -9.1                 # channel walls (0.3 clr per side)
CH_Z0 = 2.4                                # channel floor

# thumb pad on an integral post through an X slot in the lid: slide 6.4 to
# open. The post sweep (13..23.4) stays clear of the finger base (27.8+).
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
LID_X0, LID_X1 = 10.4, 39.9
LID_Y0, LID_Y1 = -16.5, -4.0
M2_XY = ((18.0, -6.55), (32.0, -6.55))     # both OUTSIDE the head's deep
                                           # pocket (x ≤ 15.7) so the insert
                                           # pockets keep a solid wall

# ── TRRS auto-mate at the -X/+Y foot (LATCHES[1]) ────────────────────────
# The connector clicks in AS the bar seats: the leg-side FEMALE (a PJ-320 /
# SJ-43516-class SMT TRRS jack, embedded in the shaft through its key flat,
# mouth 2.5 PROUD of the flat — see legs.leg_shaft_trrs) faces +Y; the
# bar-side MALE right-angle plug lives in the thickened back band, barrel
# -Y through the slot back and INTO the leg's envelope. Sequence (δ = travel
# to seat): δ=18 flare funnel, δ=16 HARD slot walls (X ±0.2), δ=14 barrel
# tip meets the jack mouth (its own conical entry), δ=2.3 the jack's proud
# nose enters the bar's recess (final fine alignment), δ=0 fully seated.
# The plug's cable elbows INBOARD along a channel in the back band.
TR_Z = 9.5                                 # connector axis (bar-local z)
JACK_Y0, JACK_Y1 = -2.7, 9.3               # jack body (leg-fixed): 12 deep,
JACK_W, JACK_H = 11.0, 6.0                 # ... mouth at +9.3 (2.5 proud)
PLUG_Y1 = 20.3                             # plug body back (9.3..20.3)
PLUG_W, PLUG_H = 10.0, 10.0
NOSE_Y0, NOSE_Y1 = 6.9, 9.8                # nose recess through the slot back
PKT_Y0, PKT_Y1 = 9.0, 20.9                 # plug pocket (open top)
CBL_X0, CBL_X1 = 5.8, 30.0                 # cable channel, inboard (ls)


def _slot_cutter(lx: float) -> cq.Workplane:
    """Slot for one leg: a plain rectangular pocket — Ø20.4 walls register X
    on the shaft's rounds, the flat back FACE-seats on the single key flat —
    full height, opening -Y. A SHORT (2-deep) flare funnels the mouth; the
    hard walls behind it run 16 deep so they align the shaft 2mm before the
    TRRS halves can touch."""
    cut = box_at(SLOT_W, 26.0 + SLOT_BACK, BAR_H + 2,
                 x=lx, y=YC + (SLOT_BACK - 26.0) / 2, z=BAR_H / 2)
    for s in (1, -1):
        cut = cut.union(
            cq.Workplane("XY")
            .polyline([(s * SLOT_W / 2, -25.0), (s * (SLOT_W / 2 + 3), -25.0),
                       (s * SLOT_W / 2, -23.0)])
            .close().extrude(BAR_H + 2).translate((lx, YC, -1)))
    return cut


def pedal_bar() -> cq.Workplane:
    """The bar body: one prism − slots − a latch channel/recess per foot."""
    body = box_at(BAR_X1 - BAR_X0, BAR_Y1 - BAR_Y0, BAR_H,
                  x=(BAR_X0 + BAR_X1) / 2, y=(BAR_Y0 + BAR_Y1) / 2, z=BAR_H / 2)
    for lx, ls in LATCHES:
        body = body.cut(_slot_cutter(lx))
        # latch channel strip (open to the top; the lid roofs it)
        body = body.cut(box_at(CH_X1 - CH_X0, CH_Y1 - CH_Y0, BAR_H - CH_Z0 + 1,
                               x=lx + ls * (CH_X0 + CH_X1) / 2,
                               y=YC + (CH_Y0 + CH_Y1) / 2,
                               z=(CH_Z0 + BAR_H + 1) / 2))
        # deep pocket: the bolt HEAD's travel garage (reaches the chord depth)
        body = body.cut(box_at(DP_X1 - DP_X0, DP_Y1 - CH_Y0, BAR_H - CH_Z0 + 1,
                               x=lx + ls * (DP_X0 + DP_X1) / 2,
                               y=YC + (CH_Y0 + DP_Y1) / 2,
                               z=(CH_Z0 + BAR_H + 1) / 2))
        # lid recess in the bar top
        body = body.cut(box_at(LID_X1 - LID_X0, LID_Y1 - LID_Y0,
                               BAR_H - LID_Z0 + 1,
                               x=lx + ls * (LID_X0 + LID_X1) / 2,
                               y=YC + (LID_Y0 + LID_Y1) / 2,
                               z=(LID_Z0 + BAR_H + 1) / 2))
        # M2: Ø2.2 self-tap below a Ø3.3×3.5 insert pocket (CLAUDE.md rule)
        for mx, my in M2_XY:
            body = body.cut(cyl(M2_SELFTAP_D, LID_Z0 - 6.0, z=6.0)
                            .translate((lx + ls * mx, YC + my, 0)))
            body = body.cut(cyl(M2_INSERT_PILOT_D, M2_INSERT_DEPTH + 0.5,
                                z=LID_Z0 - M2_INSERT_DEPTH)
                            .translate((lx + ls * mx, YC + my, 0)))

    # ── TRRS dock at the -X foot (see the constants block) ────────────
    tx, tls = LATCHES[1]
    # nose recess: the jack's proud mouth pokes through the slot back here
    body = body.cut(box_at(JACK_W + 0.8, NOSE_Y1 - NOSE_Y0, JACK_H + 1.0,
                           x=tx, y=YC + (NOSE_Y0 + NOSE_Y1) / 2, z=TR_Z))
    # right-angle plug pocket (open top: plug drops in, barrel out -Y)
    body = body.cut(box_at(PLUG_W + 1.6, PKT_Y1 - PKT_Y0, BAR_H - 4.0 + 1,
                           x=tx, y=YC + (PKT_Y0 + PKT_Y1) / 2,
                           z=(4.0 + BAR_H + 1) / 2))
    # cable channel: the right-angle lead elbows inboard along the bar
    body = body.cut(box_at(CBL_X1 - CBL_X0, 6.0, 9.0,
                           x=tx + tls * (CBL_X0 + CBL_X1) / 2,
                           y=YC + 14.0, z=TR_Z))
    return body


def pedal_bolt(lx: float, ls: float) -> cq.Workplane:
    """One sliding bolt, drawn CLOSED. Flat -Y-normal head face on the waist
    chord (a tug cannot cam it open), 45° plan bevel on the tip (the
    incoming waist cams it aside on push-on), low pusher tab for the TPU
    finger, and an integral post + thumb pad through the lid slot — slide 5
    inboard to open."""
    body = box_at(BOLT_X1 - BOLT_X0, BOLT_Y1 - BOLT_Y0, BOLT_Z1 - BOLT_Z0,
                  x=lx + ls * (BOLT_X0 + BOLT_X1) / 2,
                  y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                  z=(BOLT_Z0 + BOLT_Z1) / 2)
    # blocking HEAD: thickened to 0.2 off the waist chord (flat-on-flat seat)
    body = body.union(box_at(HEAD_X1 - BOLT_X0, HEAD_Y1 - BOLT_Y0,
                             BOLT_Z1 - BOLT_Z0,
                             x=lx + ls * (BOLT_X0 + HEAD_X1) / 2,
                             y=YC + (BOLT_Y0 + HEAD_Y1) / 2,
                             z=(BOLT_Z0 + BOLT_Z1) / 2))
    # tip bevel (plan view) — the entry ramp
    body = body.cut(cq.Workplane("XY")
                    .polyline([(ls * BOLT_X0, BOLT_Y0),
                               (ls * (BOLT_X0 + 3.0), BOLT_Y0),
                               (ls * BOLT_X0, BOLT_Y0 + 3.0)])
                    .close().extrude(BOLT_Z1 - BOLT_Z0 + 2)
                    .translate((lx, YC, BOLT_Z0 - 1)))
    # pusher tab (low, so the finger bends about a long arm)
    body = body.union(box_at(TAB_X1 - BOLT_X1, BOLT_Y1 - BOLT_Y0,
                             TAB_Z1 - BOLT_Z0,
                             x=lx + ls * (BOLT_X1 + TAB_X1) / 2,
                             y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                             z=(BOLT_Z0 + TAB_Z1) / 2))
    # post through the lid slot + thumb pad above the lid
    body = body.union(box_at(POST_X1 - POST_X0, BOLT_Y1 - BOLT_Y0,
                             PAD_Z0 - BOLT_Z1,
                             x=lx + ls * (POST_X0 + POST_X1) / 2,
                             y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                             z=(BOLT_Z1 + PAD_Z0) / 2))
    body = body.union(box_at(PAD_X1 - PAD_X0, PAD_Y1 - PAD_Y0, PAD_Z1 - PAD_Z0,
                             x=lx + ls * (PAD_X0 + PAD_X1) / 2,
                             y=YC + (PAD_Y0 + PAD_Y1) / 2,
                             z=(PAD_Z0 + PAD_Z1) / 2))
    return body


def pedal_latch_lid(lx: float, ls: float) -> cq.Workplane:
    """One latch lid: roofs the channel (recessed flush), carries the
    thumb-pad slot, sockets the TPU finger, 2× M2 down into the bar."""
    body = box_at(LID_X1 - LID_X0, LID_Y1 - LID_Y0, BAR_H - LID_Z0,
                  x=lx + ls * (LID_X0 + LID_X1) / 2,
                  y=YC + (LID_Y0 + LID_Y1) / 2,
                  z=(LID_Z0 + BAR_H) / 2)
    # thumb-slide slot: post width + 5 travel + 0.3 clr each side
    body = body.cut(box_at(POST_X1 - POST_X0 + BOLT_TRAVEL + 0.6,
                           BOLT_Y1 - BOLT_Y0 + 0.6, BAR_H - LID_Z0 + 2,
                           x=lx + ls * (POST_X0 - 0.3 + POST_X1 + BOLT_TRAVEL + 0.3) / 2,
                           y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                           z=(LID_Z0 + BAR_H) / 2))
    # TPU finger base socket (press-in from below, before the lid screws on)
    body = body.cut(box_at(FNG_T + 0.8, FNG_W + 0.8, FNG_BASE_H,
                           x=lx + ls * (FNG_X0 + FNG_T / 2),
                           y=YC + (CH_Y0 + CH_Y1) / 2,
                           z=LID_Z0 + FNG_BASE_H / 2))
    for mx, my in M2_XY:
        body = body.cut(cyl(M2_SHAFT_CLR_D, BAR_H - LID_Z0 + 2, z=LID_Z0 - 1)
                        .translate((lx + ls * mx, YC + my, 0)))
        body = body.cut(cyl(M2_HEAD_RECESS_D, M2_HEAD_RECESS_H + 1,
                            z=BAR_H - M2_HEAD_RECESS_H)
                        .translate((lx + ls * mx, YC + my, 0)))
    return body


def pedal_latch_finger(lx: float, ls: float) -> cq.Workplane:
    """TPU return finger: base potted in the lid, blade hangs down behind the
    bolt's pusher tab. Bending spring (~0.5 N/mm at the tab) — unloaded at
    rest and when latched, deflected only during actuation, so no creep.
    Symmetric boxes → the SAME printed part serves both (mirrored) latches."""
    yc = YC + (CH_Y0 + CH_Y1) / 2
    blade = box_at(FNG_T, FNG_W, FNG_ZTOP - FNG_Z0,
                   x=lx + ls * (FNG_X0 + FNG_T / 2), y=yc,
                   z=(FNG_Z0 + FNG_ZTOP) / 2)
    base = box_at(FNG_T + 0.8, FNG_W + 0.8, FNG_BASE_H,
                  x=lx + ls * (FNG_X0 + FNG_T / 2), y=yc,
                  z=FNG_ZTOP + FNG_BASE_H / 2)
    return blade.union(base)


def _trrs_jack() -> cq.Workplane:
    """DEMO leg-side female jack (PJ-320 / SJ-43516 class, ~11×12×6): body
    embedded in the shaft through its key flat, mouth 2.5 proud, Ø3.6 way."""
    tx, _ = LATCHES[1]
    j = box_at(JACK_W, JACK_Y1 - JACK_Y0, JACK_H,
               x=tx, y=YC + (JACK_Y0 + JACK_Y1) / 2, z=TR_Z)
    return j.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.8, JACK_Y1 - JACK_Y0 + 2,
        cq.Vector(tx, YC + JACK_Y0 - 1, TR_Z), cq.Vector(0, 1, 0))))


def _trrs_plug() -> cq.Workplane:
    """DEMO bar-side right-angle male plug: Ø3.5×14 barrel -Y through the
    slot back into the leg-mounted jack (drawn fully seated), molded body in
    the back-band pocket, cable stub elbowing inboard."""
    tx, tls = LATCHES[1]
    p = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.75, 14.0, cq.Vector(tx, YC + JACK_Y1, TR_Z), cq.Vector(0, -1, 0)))
    p = p.union(box_at(PLUG_W, PLUG_Y1 - JACK_Y1, PLUG_H,
                       x=tx, y=YC + (JACK_Y1 + PLUG_Y1) / 2, z=TR_Z))
    p = p.union(box_at(22.0, 4.5, 4.5,
                       x=tx + tls * (5.0 + 22.0 / 2), y=YC + 14.0, z=TR_Z))
    return p


def assembly_parts():
    """[(name, workplane)] — the printed parts + connector DEMOs, drawn
    SEATED, in absolute X/Y with z0 = the plate bottom (build.py lifts the
    whole set by ground + FOOT_H). The ls=+1 latch is the mirror image of
    the ls=-1 one, so its bolt/lid are the `_m` printed variants; the finger
    is symmetric (one part ×2)."""
    (lx_a, ls_a), (lx_b, ls_b) = LATCHES
    return [("pedal_bar", pedal_bar()),
            ("pedal_bolt", pedal_bolt(lx_a, ls_a)),
            ("pedal_bolt_m", pedal_bolt(lx_b, ls_b)),
            ("pedal_latch_lid", pedal_latch_lid(lx_a, ls_a)),
            ("pedal_latch_lid_m", pedal_latch_lid(lx_b, ls_b)),
            ("pedal_latch_finger_0", pedal_latch_finger(lx_a, ls_a)),
            ("pedal_latch_finger_1", pedal_latch_finger(lx_b, ls_b)),
            ("pedal_trrs_jack", _trrs_jack()),
            ("pedal_trrs_plug", _trrs_plug())]
