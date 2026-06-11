"""Adjustable pickup mount — saddle clamps + bridge bar + width jaws. PCTG.

Holds any common steel pickup (width ~22–40, length ~90–125, height ~14–25 —
e.g. a George L E-66 at 33×99×20.6) under the strings, with three adjustments:

  X (quick — bridge↔neck tone): two SADDLES clamp the chassis rails' top
    flanges, each pinched by one M4 set screw; loosen, slide the whole mount
    anywhere along the speaking length, retighten.
  Z (set once): the bar's end TABS carry vertical slots; two M4 screws per
    side into saddle-face inserts give ±6 mm — sets the string gap AND absorbs
    the pickup-height range (the pickup TOP is what the gap fixes).
  Size (set once per pickup — like Z, needs no quick release): two JAWS ride a
    T-slot across the bar and pinch the pickup's WIDTH (the dimension that
    actually varies between models); each locks with a vertical M4 set screw
    jammed against the bar top, hex-key tightened at install time. Length
    variants simply overhang the bar symmetrically — poles stay centred. The
    +Y rail sits only ~12 mm past string 10, so end-clamping the length has no
    jaw-travel room; width-clamping is the geometry that fits.

The bar passes OVER the belts (8 mm clear) and the assembly clears the motor
tops by ~2 mm at the bottom — no instrument-thickness increase. All hardware
is the M4 set screws + heat-set inserts + M4×12 buttons already in the BOM.

Frames: saddle local = rail centreline Y0, rail top Z0 (X-symmetric — rotate
180° about Z for the other rail). Jaw local = bar top Z0, clamp face at X0
(facing −X; rotate 180° about Z for the opposing jaw). The bar is built at its
GLOBAL Y/Z (the rails are asymmetric about the field) with X centred on 0;
build.py X-translates it to the chosen pickup position.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from .helpers import box_at, cyl, cyl_y

# ── the pickup itself (DEMO dummy dimensions; the mount adjusts around it) ──
PK_W, PK_L, PK_H = 33.0, 99.0, 20.0
GAP     = 3.0                                   # pickup top → heaviest string bottom
PK_TOP  = D.STRING_Z - max(D.STRING_GAUGE) - GAP
PK_BOT  = PK_TOP - PK_H

# ── bar (spans the rails under the pickup) ─────────────────────────────────
BAR_W   = 68.0                                  # along X (jaw travel lives in this)
BAR_H   = 12.0
BAR_TOP = PK_BOT                                # pickup rests on the bar top
NECK_W, NECK_D = 6.0, 3.8                       # T-slot opening
UC_W, UC_H     = 12.0, 4.0                      # T-slot undercut
SLOT_X  = 62.0                                  # T-slot length (jaw travel)
# The end tabs (and their saddles) sit OFFSET +X of the pickup centre: the +Y
# rail is only ~12 mm past string 10, so anything at the pickup's own X would
# collide with its +Y end — out at x 26..38 nothing else lives (pickups max
# x ±20, jaw bodies ±28).
TAB_XC, TAB_XW = 32.0, 12.0

# ── saddles (rail-top clamps) ───────────────────────────────────────────────
SAD_X   = 24.0                                  # along the rail
SAD_CAP = 8.0                                   # above the rail top
LEG_T   = 7.0                                   # holds a Ø5.6 insert pocket
LEG_DROP = 8.0
RAIL_CLR = 0.15                                 # sliding fit on the rail faces
INSERT_D, INSERT_L = 5.6, 4.7
SCREW_CLR = 4.3                                 # M4 clearance

# tab interface: the bar's end tabs lap the saddles' field-side leg faces
# (tabs reach down past the spine top so they fuse to it)
TAB_T   = 4.0
TAB_Z0, TAB_Z1 = BAR_TOP - 6.0, CH.Z_TOP + 2.0
_leg_in = CH.T / 2 + RAIL_CLR                   # leg inner face offset from rail centre
FACE_Y_HI = CH.Y_HI - _leg_in - LEG_T           # +Y saddle's field face (global)
FACE_Y_LO = CH.Y_LO + _leg_in + LEG_T           # −Y saddle's field face (global)

# ── jaws ────────────────────────────────────────────────────────────────────
JAW_Y   = 36.0                                  # clamp-face width along the pickup side
JAW_H   = 15.0                                  # face height above the bar top
JAW_T   = 8.0                                   # body thickness behind the face
FOOT_L  = 20.0                                  # foot length along the slot


def _saddle() -> cq.Workplane:
    """Rail-top clamp. Local: rail centreline Y0, rail top Z0; field side −Y."""
    y_out = _leg_in + LEG_T                     # leg outer face offset
    body = box_at(SAD_X, 2 * y_out, SAD_CAP, z=SAD_CAP / 2)
    for s in (-1, 1):                           # legs hugging the rail faces
        body = body.union(box_at(SAD_X, LEG_T, LEG_DROP,
                                 y=s * (_leg_in + LEG_T / 2), z=-LEG_DROP / 2))
    # rail pinch set screw: insert pocket in each leg's outer face (use either —
    # the part is symmetric) + M4 clearance straight through both legs
    for s in (-1, 1):
        body = body.cut(cyl_y(INSERT_D, INSERT_L + 0.3,
                              y0=(y_out - INSERT_L - 0.3) if s > 0 else -y_out - 0.01,
                              x=0, z=-LEG_DROP / 2))
    body = body.cut(cyl_y(SCREW_CLR, 2 * y_out + 2, y0=-y_out - 1,
                          x=0, z=-LEG_DROP / 2))
    # bar-tab screws: two Ø5.6 insert pockets in the field-side (−Y) leg face
    for sx in (-3.0, 3.0):
        body = body.cut(cyl_y(INSERT_D, INSERT_L + 0.3, y0=-y_out - 0.01,
                              x=sx, z=-LEG_DROP / 2))
    return body


def _bar() -> cq.Workplane:
    """Bridge bar, built at global Y/Z (X centred on the pickup)."""
    y_hi, y_lo = FACE_Y_HI, FACE_Y_LO
    spine = box_at(BAR_W, (y_hi + 1) - (y_lo - 1), BAR_H,
                   y=(y_hi + y_lo) / 2, z=BAR_TOP - BAR_H / 2)
    # corner arms out to the tab line (the tabs are offset +X of the pickup)
    arm_x0, arm_x1 = BAR_W / 2 - 4.0, TAB_XC + TAB_XW / 2
    for yf, s in ((y_hi, 1), (y_lo, -1)):
        spine = spine.union(box_at(arm_x1 - arm_x0, 14.0, BAR_H,
                                   x=(arm_x0 + arm_x1) / 2,
                                   y=yf - s * 6.0, z=BAR_TOP - BAR_H / 2))
        # end tab: rises up the saddle leg face, vertical slots = Z-adjust ±6
        tab = box_at(TAB_XW, TAB_T, TAB_Z1 - TAB_Z0,
                     x=TAB_XC, y=yf - s * TAB_T / 2, z=(TAB_Z0 + TAB_Z1) / 2)
        spine = spine.union(tab)
        cut_y0 = (yf - TAB_T if s > 0 else yf) - 1   # cyl_y extrudes +Y from y0
        for sx in (TAB_XC - 3.0, TAB_XC + 3.0):
            for sz in (CH.Z_TOP - 12.0, CH.Z_TOP):
                spine = spine.cut(cyl_y(SCREW_CLR, TAB_T + 2, y0=cut_y0, x=sx, z=sz))
            spine = spine.cut(box_at(SCREW_CLR, TAB_T + 2, 12.0, x=sx,
                                     y=yf - s * TAB_T / 2, z=CH.Z_TOP - 6.0))
    # T-slot along X at Y0 (jaw feet)
    spine = spine.cut(box_at(SLOT_X, NECK_W, NECK_D + 0.1,
                             z=BAR_TOP - (NECK_D + 0.1) / 2))
    spine = spine.cut(box_at(SLOT_X, UC_W, UC_H,
                             z=BAR_TOP - NECK_D - UC_H / 2))
    return spine


def _jaw() -> cq.Workplane:
    """Width jaw. Local: bar top Z0, clamp face at X0 facing −X."""
    body = box_at(JAW_T, JAW_Y, JAW_H, x=JAW_T / 2, z=JAW_H / 2)
    # T-foot under the body, riding the slot (0.3/0.15 clearances); the wing
    # hangs directly off the neck bottom so the foot is one piece
    neck_bot = -(NECK_D - 0.15)
    foot = box_at(FOOT_L, NECK_W - 0.3, NECK_D - 0.15,
                  x=JAW_T - FOOT_L / 2, z=neck_bot / 2)
    foot = foot.union(box_at(FOOT_L, UC_W - 0.3, UC_H - 0.15,
                             x=JAW_T - FOOT_L / 2,
                             z=neck_bot - (UC_H - 0.15) / 2))
    body = body.union(foot)
    # lock: vertical M4 set screw through a body insert, tip jamming the bar
    # top beside the slot opening (|Y| > opening half-width)
    body = body.cut(cyl(INSERT_D, INSERT_L + 0.3, z=JAW_H - INSERT_L - 0.3)
                    .translate((JAW_T / 2 + 1.5, 9.0, 0)))
    body = body.cut(cyl(SCREW_CLR, JAW_H + 2, z=-1)
                    .translate((JAW_T / 2 + 1.5, 9.0, 0)))
    return body


def pickup_demo() -> cq.Workplane:
    """DEMO pickup body (George L E-66-ish), centred X/Y, top at z=0."""
    return box_at(PK_W, PK_L, PK_H, z=-PK_H / 2)


pickup_saddle = _saddle()
pickup_bar    = _bar()
pickup_jaw    = _jaw()
