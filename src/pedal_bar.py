"""Pedal bar — spans the two +Y legs at ankle height; retract-slide-release.

The bar is the mounting rail for the (future) sensor pedals. It attaches to
the +Y legs' shafts (legs.py): each end has a rectangular SLOT, open toward
the instrument (-Y) — Ø20.4 walls register X on the shaft's rounds, and the
flat back FACE-seats on the shaft's single key flat (the leg's single-D key
aims everything). Z: the plate rests on the foot cap + the chord notch's
lower crescent; anti-lift is the CLOSED bolt head sitting inside the notch.
The bar is one slim prism (Y -16..+12): no lumps, ends just past each leg.

Y RETENTION — one sliding-bolt latch per foot, both opening INBOARD; rigid
lock, no flexing structural member. Closed, the bolt's thickened HEAD bears
flat-on-flat on the waist's front CHORD (legs.WAIST_CHORD_Y): normal pure
Y — a tug cannot cam it open, wear cannot loosen it, seated Y float ~0.4
total (0.2 chord + 0.2 slot-back seat). The thumb pad rides an integral
post through an X slot in the lid.

The two latches differ:
- +X foot (pedal_bolt, 6.4 travel): keeps the 45° tip bevel — pushing the
  bar on cams it aside and it SNAPS in; TPU finger return.
- -X foot (pedal_bolt_trrs, 15.0 travel): the slider ALSO carries the male
  TRRS plug (axis X, pointing at the leg), so the latch IS the connector
  actuator: RETRACT the pad (the plug clears the leg's envelope), slide the
  bar on/off freely, RELEASE — the far-end TPU kick spring shoves the
  slider toward the leg — and THUMB-PRESS the pad home: the plug clicks
  into the jack embedded in the shaft (legs.leg_shaft_trrs; wires up the
  leg's Ø6 hollow centre). Deliberately NO tip bevel here: an un-retracted
  install butts the shaft against the flat head and refuses — a cam could
  only yield ~6 of the needed 15 and the leg would bend the barrel. The
  seated TRRS detent (5-15 N) is the hold-closed force; the kick spring is
  engaged only over the last ~4.5 of opening, so holding it retracted while
  positioning the bar costs almost nothing.

The plug (a STRAIGHT solder/molded TRRS plug, Ø~9 × ~18 body + Ø3.5 × 14
barrel) sits in a cradle on the slider: backstop pushes it in, a Ø9 collar
around the barrel pulls it out (the collar noses into the shaft pocket's
counterbore at full insertion), the lid caps it. Its cable gets a ~15
service loop in the latch cavity, then exits inboard toward the pedal
electronics.

FRAME: modelled at ABSOLUTE X/Y (the legs' real stations, +Y rail); Z is
local with 0 = the plate bottom (build.py translates by ground + FOOT_H).
Drawn SEATED: bolts closed, plug fully inserted. DEMO: the bar is one prism
— longer than any print bed; it gets segmented once the pedals land on it.
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
# one latch per foot, each opening INBOARD: (leg station, side sign)
LATCHES = ((LEG_STATIONS_X[0], -1.0),  # +X leg → plain snap latch, extends -X
           (LEG_STATIONS_X[1], +1.0))  # -X leg → TRRS latch, extends +X

# plate: 19 tall inside the 20-tall notch band (1.0 anti-lift clearance up)
BAR_H = 19.0
BAR_Y0, BAR_Y1 = YC - 16.0, YC + 12.0      # slim prism: 2.1 front wall ahead
                                           # of the bolt channel, 5.0 back
                                           # wall behind the slot back
END_MARGIN = 15.0                          # bar end past each leg axis
BAR_X0 = LEG_STATIONS_X[1] - END_MARGIN
BAR_X1 = LEG_STATIONS_X[0] + END_MARGIN
SLOT_W = SHAFT_D + 0.4                     # 20.4 walls on the shaft's rounds
SLOT_BACK = SHAFT_FLAT_Y + 0.2             # 7.0 flat back: face seat (0.2)

# ── shared latch geometry (x offsets from the leg axis, flipped by ls) ───
BOLT_X0, BOLT_X1 = 4.0, 27.0
BOLT_Y0, BOLT_Y1 = -13.6, -9.4             # thin BODY band (rides the channel)
HEAD_X1, HEAD_Y1 = 9.0, -7.2               # blocking head: 0.2 off the chord
BOLT_Z0, BOLT_Z1 = 2.4, 14.7
CH_Y0, CH_Y1 = -13.9, -9.1                 # body-channel walls (0.3 clr/side)
CH_Z0 = 2.4                                # cavity floor
POST_X0, POST_X1 = 13.0, 17.0              # thumb-pad post through the lid
PAD_X0, PAD_X1 = 12.5, 21.0
PAD_Y0, PAD_Y1 = -14.5, -8.5
PAD_Z0, PAD_Z1 = BAR_H + 0.3, BAR_H + 3.8
FNG_T, FNG_W = 4.5, 4.0                    # TPU finger blade: X × Y
FNG_Z0, FNG_ZTOP = 2.7, 15.0
FNG_BASE_H = 3.5
LID_Z0 = 15.0
LID_Y0, LID_Y1 = -16.5, -4.0

# ── plain (+X) latch: 6.4 travel, snap-in tip bevel ──────────────────────
A_TRAVEL = 6.4
A_DP_X0, A_DP_X1, DP_Y1 = 10.0, 15.7, -6.9  # head's travel garage
A_TAB_X1, TAB_Z1 = 28.2, 5.5               # low pusher tab → finger arm
A_CH_X0, A_CH_X1 = 10.0, 39.5              # channel + finger bay
A_FNG_X0 = A_TAB_X1                        # finger front rests on the tab
A_LID_X0, A_LID_X1 = 10.4, 39.9
A_M2 = ((18.0, -6.55), (32.0, -6.55))

# ── TRRS (-X) latch: 15.0 travel, the slider carries the plug ────────────
# Seated (drawn) plug: jack mouth flush at the shaft surface (x' 10), barrel
# Ø3.5 spans 10.2 → -3.8 (13.8 of the 14 insertion; the collar noses 0.8
# into the shaft's counterbore). Retracted (+15): barrel tip at 11.2 — the
# corridor (±10.2) is FULLY clear, the leg slides past nothing.
B_TRAVEL = 15.0
TR_Z = 8.7                                 # connector axis (bar-local z; low
                                           # enough that the cradle tube roof
                                           # stays under the lid plane)
PLUG_TIP, PLUG_BASE = -3.8, 10.2           # barrel (x', seated)
PLUG_BODY_L, PLUG_BODY_D = 18.0, 9.0       # straight plug body in the cradle
TUBE_X1 = 30.2                             # cradle tube incl. backstop end
SHELL_X1 = TUBE_X1
B_CAV_X0, B_CAV_X1 = 10.0, 49.5            # one open-top latch cavity
B_CAV_Y0, B_CAV_Y1 = -13.9, 6.5
B_FNG_X0 = 40.7                            # kick spring: engaged only over
                                           # the last ~4.5 of opening
B_LID_X0, B_LID_X1 = 10.4, 54.0
B_M2 = ((51.5, -11.0), (51.5, 2.0))        # both beyond the cavity (x>49.5)


def _slot_cutter(lx: float) -> cq.Workplane:
    """Slot for one leg: rectangular pocket (Ø20.4 walls, 7.0 flat back),
    full height, opening -Y, with 45° lead-in flares at the mouth."""
    cut = box_at(SLOT_W, 17.0 + SLOT_BACK, BAR_H + 2,
                 x=lx, y=YC + (SLOT_BACK - 17.0) / 2, z=BAR_H / 2)
    for s in (1, -1):
        cut = cut.union(
            cq.Workplane("XY")
            .polyline([(s * SLOT_W / 2, -16.0), (s * (SLOT_W / 2 + 4), -16.0),
                       (s * SLOT_W / 2, -11.0)])
            .close().extrude(BAR_H + 2).translate((lx, YC, -1)))
    return cut


def _m2_bores(body, lx, ls, holes):
    """Ø2.2 self-tap below a Ø3.3×3.5 insert pocket (CLAUDE.md rule)."""
    for mx, my in holes:
        body = body.cut(cyl(M2_SELFTAP_D, LID_Z0 - 6.0, z=6.0)
                        .translate((lx + ls * mx, YC + my, 0)))
        body = body.cut(cyl(M2_INSERT_PILOT_D, M2_INSERT_DEPTH + 0.5,
                            z=LID_Z0 - M2_INSERT_DEPTH)
                        .translate((lx + ls * mx, YC + my, 0)))
    return body


def pedal_bar() -> cq.Workplane:
    """The bar body: one slim prism − slots − the two (different) latch
    cavities and lid recesses."""
    body = box_at(BAR_X1 - BAR_X0, BAR_Y1 - BAR_Y0, BAR_H,
                  x=(BAR_X0 + BAR_X1) / 2, y=(BAR_Y0 + BAR_Y1) / 2, z=BAR_H / 2)
    for lx, _ in LATCHES:
        body = body.cut(_slot_cutter(lx))

    # ── plain latch (+X foot) ──────────────────────────────────────────
    lx, ls = LATCHES[0]
    body = body.cut(box_at(A_CH_X1 - A_CH_X0, CH_Y1 - CH_Y0, BAR_H - CH_Z0 + 1,
                           x=lx + ls * (A_CH_X0 + A_CH_X1) / 2,
                           y=YC + (CH_Y0 + CH_Y1) / 2,
                           z=(CH_Z0 + BAR_H + 1) / 2))
    body = body.cut(box_at(A_DP_X1 - A_DP_X0, DP_Y1 - CH_Y0, BAR_H - CH_Z0 + 1,
                           x=lx + ls * (A_DP_X0 + A_DP_X1) / 2,
                           y=YC + (CH_Y0 + DP_Y1) / 2,
                           z=(CH_Z0 + BAR_H + 1) / 2))
    body = body.cut(box_at(A_LID_X1 - A_LID_X0, LID_Y1 - LID_Y0,
                           BAR_H - LID_Z0 + 1,
                           x=lx + ls * (A_LID_X0 + A_LID_X1) / 2,
                           y=YC + (LID_Y0 + LID_Y1) / 2,
                           z=(LID_Z0 + BAR_H + 1) / 2))
    body = _m2_bores(body, lx, ls, A_M2)

    # ── TRRS latch (-X foot): one open-top cavity swallows the slider,
    #    cradle, plug travel, kick spring and cable service loop ─────────
    lx, ls = LATCHES[1]
    body = body.cut(box_at(B_CAV_X1 - B_CAV_X0, B_CAV_Y1 - B_CAV_Y0,
                           BAR_H - CH_Z0 + 1,
                           x=lx + ls * (B_CAV_X0 + B_CAV_X1) / 2,
                           y=YC + (B_CAV_Y0 + B_CAV_Y1) / 2,
                           z=(CH_Z0 + BAR_H + 1) / 2))
    body = body.cut(box_at(B_LID_X1 - B_LID_X0, (7.0 - LID_Y0),
                           BAR_H - LID_Z0 + 1,
                           x=lx + ls * (B_LID_X0 + B_LID_X1) / 2,
                           y=YC + (LID_Y0 + 7.0) / 2,
                           z=(LID_Z0 + BAR_H + 1) / 2))
    body = _m2_bores(body, lx, ls, B_M2)
    return body


def _bolt_core(lx: float, ls: float, bevel: bool) -> cq.Workplane:
    """Bolt body + blocking head + thumb post/pad (shared by both latches)."""
    body = box_at(BOLT_X1 - BOLT_X0, BOLT_Y1 - BOLT_Y0, BOLT_Z1 - BOLT_Z0,
                  x=lx + ls * (BOLT_X0 + BOLT_X1) / 2,
                  y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                  z=(BOLT_Z0 + BOLT_Z1) / 2)
    body = body.union(box_at(HEAD_X1 - BOLT_X0, HEAD_Y1 - BOLT_Y0,
                             BOLT_Z1 - BOLT_Z0,
                             x=lx + ls * (BOLT_X0 + HEAD_X1) / 2,
                             y=YC + (BOLT_Y0 + HEAD_Y1) / 2,
                             z=(BOLT_Z0 + BOLT_Z1) / 2))
    if bevel:   # snap-in entry ramp (plain latch only — see header)
        body = body.cut(cq.Workplane("XY")
                        .polyline([(ls * BOLT_X0, BOLT_Y0),
                                   (ls * (BOLT_X0 + 3.0), BOLT_Y0),
                                   (ls * BOLT_X0, BOLT_Y0 + 3.0)])
                        .close().extrude(BOLT_Z1 - BOLT_Z0 + 2)
                        .translate((lx, YC, BOLT_Z0 - 1)))
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


def pedal_bolt() -> cq.Workplane:
    """Plain (+X foot) bolt, drawn CLOSED: snap-in bevel, pusher tab for its
    TPU return finger. Slide 6.4 inboard to release."""
    lx, ls = LATCHES[0]
    body = _bolt_core(lx, ls, bevel=True)
    body = body.union(box_at(A_TAB_X1 - BOLT_X1, BOLT_Y1 - BOLT_Y0,
                             TAB_Z1 - BOLT_Z0,
                             x=lx + ls * (BOLT_X1 + A_TAB_X1) / 2,
                             y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                             z=(BOLT_Z0 + TAB_Z1) / 2))
    return body


def pedal_bolt_trrs() -> cq.Workplane:
    """TRRS (-X foot) slider, drawn CLOSED/SEATED: bolt (no bevel — an
    un-retracted install must REFUSE, not half-cam into the barrel) + bridge
    + plug cradle TUBE (Ø12 over a Ø9.5 bore). The plug loads barrel-first
    through the tube's open front BEFORE the slider drops into the bar; the
    backstop end (Ø5 cable bore) pushes it in, an M2 set screw through the
    tube roof (Ø2.2 self-tap, CLAUDE.md rule) pinches the molded body so
    retraction pulls it back out of the jack. At closed the tube's front
    face sits 0.2 off the shaft (the shaft's round has receded everywhere
    else); nothing enters the leg but the barrel."""
    lx, ls = LATCHES[1]
    body = _bolt_core(lx, ls, bevel=False)
    # bridge: bolt body band → cradle tube
    body = body.union(box_at(8.0, 5.0, 8.0,
                             x=lx + ls * 16.0, y=YC - 7.1, z=TR_Z))
    # cradle tube + backstop end
    tube = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        6.0, TUBE_X1 - PLUG_BASE,
        cq.Vector(lx + ls * PLUG_BASE, YC, TR_Z), cq.Vector(ls, 0, 0)))
    tube = tube.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        4.75, PLUG_BODY_L + 1.2,
        cq.Vector(lx + ls * (PLUG_BASE - 1), YC, TR_Z), cq.Vector(ls, 0, 0))))
    tube = tube.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.5, TUBE_X1 - PLUG_BASE + 2,
        cq.Vector(lx + ls * (PLUG_BASE - 1), YC, TR_Z), cq.Vector(ls, 0, 0))))
    # M2 set-screw way through the tube roof (retains the plug body)
    tube = tube.cut(cyl(M2_SELFTAP_D, 8.0, z=TR_Z)
                    .translate((lx + ls * (PLUG_BASE + PLUG_BODY_L / 2), YC, 0)))
    body = body.union(tube)
    return body


def lid_plain() -> cq.Workplane:
    lx, ls = LATCHES[0]
    return pedal_latch_lid(lx, ls, A_LID_X0, A_LID_X1, LID_Y1, A_FNG_X0, A_M2)


def lid_trrs() -> cq.Workplane:
    lx, ls = LATCHES[1]
    return pedal_latch_lid(lx, ls, B_LID_X0, B_LID_X1, 7.0, B_FNG_X0, B_M2)


def finger_part() -> cq.Workplane:
    """The single printed TPU finger (export once, print 2)."""
    lx, ls = LATCHES[0]
    return pedal_latch_finger(lx, ls, A_FNG_X0, (CH_Y0 + CH_Y1) / 2)


def pedal_latch_lid(lx: float, ls: float, x0: float, x1: float, y1: float,
                    fng_x0: float, m2) -> cq.Workplane:
    """A latch lid: roofs its cavity (recessed flush), carries the thumb-pad
    slot, sockets the TPU finger, M2s down into the bar."""
    body = box_at(x1 - x0, y1 - LID_Y0, BAR_H - LID_Z0,
                  x=lx + ls * (x0 + x1) / 2, y=YC + (LID_Y0 + y1) / 2,
                  z=(LID_Z0 + BAR_H) / 2)
    travel = A_TRAVEL if fng_x0 == A_FNG_X0 else B_TRAVEL
    body = body.cut(box_at(POST_X1 - POST_X0 + travel + 0.6,
                           BOLT_Y1 - BOLT_Y0 + 0.6, BAR_H - LID_Z0 + 2,
                           x=lx + ls * (POST_X0 - 0.3 + POST_X1 + travel + 0.3) / 2,
                           y=YC + (BOLT_Y0 + BOLT_Y1) / 2,
                           z=(LID_Z0 + BAR_H) / 2))
    body = body.cut(box_at(FNG_T + 0.8, FNG_W + 0.8, FNG_BASE_H,
                           x=lx + ls * (fng_x0 + FNG_T / 2),
                           y=YC + (CH_Y0 + CH_Y1) / 2
                           if fng_x0 == A_FNG_X0 else YC,
                           z=LID_Z0 + FNG_BASE_H / 2))
    for mx, my in m2:
        body = body.cut(cyl(M2_SHAFT_CLR_D, BAR_H - LID_Z0 + 2, z=LID_Z0 - 1)
                        .translate((lx + ls * mx, YC + my, 0)))
        body = body.cut(cyl(M2_HEAD_RECESS_D, M2_HEAD_RECESS_H + 1,
                            z=BAR_H - M2_HEAD_RECESS_H)
                        .translate((lx + ls * mx, YC + my, 0)))
    return body


def pedal_latch_finger(lx: float, ls: float, fng_x0: float,
                       yc_off: float) -> cq.Workplane:
    """TPU finger: base potted in the lid, blade hangs down. On the plain
    latch it is the return spring (rests on the pusher tab); on the TRRS
    latch it sits at the FAR end as the kick spring — engaged only over the
    last ~4.5 of opening, so holding the latch retracted is nearly free,
    and release shoves the slider toward the leg (thumb completes the TRRS
    click). Symmetric boxes → ONE printed part serves both (print 2)."""
    blade = box_at(FNG_T, FNG_W, FNG_ZTOP - FNG_Z0,
                   x=lx + ls * (fng_x0 + FNG_T / 2), y=YC + yc_off,
                   z=(FNG_Z0 + FNG_ZTOP) / 2)
    base = box_at(FNG_T + 0.8, FNG_W + 0.8, FNG_BASE_H,
                  x=lx + ls * (fng_x0 + FNG_T / 2), y=YC + yc_off,
                  z=FNG_ZTOP + FNG_BASE_H / 2)
    return blade.union(base)


def _trrs_jack() -> cq.Workplane:
    """DEMO leg-side female jack (PJ-320 / SJ-43516 class, 12×11×5): mating
    axis X, mouth flush at the shaft's inboard face, Ø3.6 way."""
    lx, ls = LATCHES[1]
    j = box_at(12.0, 11.0, 5.0, x=lx + ls * 4.0, y=YC, z=TR_Z)
    return j.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.8, 14.0, cq.Vector(lx + ls * 10.5, YC, TR_Z), cq.Vector(-ls, 0, 0))))


def _trrs_plug() -> cq.Workplane:
    """DEMO bar-side straight male plug, drawn SEATED in the jack: Ø3.5×14
    barrel + Ø9×18 body in the cradle + cable stub with its service loop."""
    lx, ls = LATCHES[1]
    p = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.75, PLUG_BASE - PLUG_TIP,
        cq.Vector(lx + ls * PLUG_BASE, YC, TR_Z), cq.Vector(-ls, 0, 0)))
    p = p.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        PLUG_BODY_D / 2, PLUG_BODY_L,
        cq.Vector(lx + ls * PLUG_BASE, YC, TR_Z), cq.Vector(ls, 0, 0))))
    # cable stub: out the backstop's Ø5 bore, service loop implied (stops
    # short of the kick spring at x' 40.7)
    p = p.union(box_at(11.6, 3.4, 3.4,
                       x=lx + ls * (28.4 + 11.6 / 2), y=YC, z=TR_Z))
    return p


def assembly_parts():
    """[(name, workplane)] — printed parts + connector DEMOs, drawn SEATED,
    absolute X/Y, z0 = plate bottom (build.py lifts by ground + FOOT_H)."""
    (lx_a, ls_a), (lx_b, ls_b) = LATCHES
    return [("pedal_bar", pedal_bar()),
            ("pedal_bolt", pedal_bolt()),
            ("pedal_bolt_trrs", pedal_bolt_trrs()),
            ("pedal_latch_lid", pedal_latch_lid(
                lx_a, ls_a, A_LID_X0, A_LID_X1, LID_Y1, A_FNG_X0, A_M2)),
            ("pedal_latch_lid_trrs", pedal_latch_lid(
                lx_b, ls_b, B_LID_X0, B_LID_X1, 7.0, B_FNG_X0, B_M2)),
            ("pedal_latch_finger_0", pedal_latch_finger(
                lx_a, ls_a, A_FNG_X0, (CH_Y0 + CH_Y1) / 2)),
            ("pedal_latch_finger_1", pedal_latch_finger(
                lx_b, ls_b, B_FNG_X0, 0.0)),
            ("pedal_trrs_jack", _trrs_jack()),
            ("pedal_trrs_plug", _trrs_plug())]
