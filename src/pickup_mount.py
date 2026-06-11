"""Adjustable pickup mount — tongue-and-groove bar + width jaws + shims. PCTG.

Holds any common steel pickup (width ~22–40, length ≤ ~108, height ~14–25 —
e.g. a George L E-66 at 33×99×20.6) under the strings:

  X (quick, TOOL-FREE — bridge↔neck tone): the bar's end TONGUES ride X-grooves
    cut into locally-thickened bosses on BOTH rails (even support across X, no
    point clamps). The mount slides in from +X before the endplate goes on; the
    endplate then caps the grooves and retains it. Lock: a hand-knobbed M4 set
    screw (printed pickup_knob threaded onto a stock set screw) lives in ONE
    fixed station in the −Y boss's ceiling and presses down on the tongue
    inside the groove — friction pins the mount; turn it from above over the
    open motor bay. The tongues run ±40 (past the bar ends) so the one station
    at X −89 reaches them anywhere in the range. The groove's −X end is a hard
    stop at exactly 128 mm pickup-centre distance from the string termination
    (fretboard lines live beyond); verified clean at the 50 mm spec minimum.
  Z (set once): printed SHIM plates under the pickup. The bar top is sized for
    the TALLEST (25 mm) pickup at a 3 mm string gap; shim thickness =
    25 − pickup height (5 mm for the E-66), reprint to tweak the gap. The
    groove must sit below the pickup's bottom (the +Y rail is only ~12 mm past
    string 10, so the pickup's end overhangs the boss) — that geometry is why
    the height adjust is shims rather than slotted tabs.
  Size (set once): two JAWS ride a T-slot across the bar and pinch the
    pickup's WIDTH; each locks with a vertical M4 set screw jammed against the
    bar top through a deep counterbore. Lengths just overhang symmetrically —
    poles stay centred; nothing clamps the length (clamp friction holds Y).

All hardware reuses the stocked M4 set screws + heat-set inserts: zero new
BOM lines. Frames: bar built at global Y/Z, X centred on the pickup (build.py
X-translates); jaw local = bar top Z0, clamp face at X0 facing −X (rotate 180°
about Z for the opposing jaw); shim local = pickup footprint, bottom at Z0.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from .helpers import box_at, cyl

# ── the pickup itself (DEMO dummy; the mount adjusts around it) ─────────────
PK_W, PK_L, PK_H = 33.0, 99.0, 20.0
GAP     = 3.0                                   # pickup top → heaviest string bottom
PK_TOP  = D.STRING_Z - max(D.STRING_GAUGE) - GAP
PK_BOT  = PK_TOP - PK_H

PK_H_MAX = 25.0                                 # tallest supported pickup
SHIM_T   = PK_H_MAX - PK_H                      # shim for the demo pickup (5.0)

# ── bar ─────────────────────────────────────────────────────────────────────
BAR_W   = 68.0                                  # along X
BAR_H   = 8.0
BAR_TOP = PK_TOP - PK_H_MAX                     # supports the tallest pickup bare
BAR_BOT = BAR_TOP - BAR_H                       # −21.8: clears motor tops (−22.85)
NECK_W, NECK_D = 6.0, 3.0                       # T-slot opening
UC_W, UC_H     = 12.0, 3.2                      # T-slot undercut
SLOT_X  = 62.0                                  # T-slot length (jaw travel)
TNG_CLR = 0.15                                  # tongue fit in the groove, per side

# ── jaws ────────────────────────────────────────────────────────────────────
JAW_Y   = 36.0                                  # clamp-face width along the pickup side
JAW_H   = 22.0                                  # face covers any pickup height (+shim)
JAW_T   = 8.0
FOOT_L  = 20.0
INSERT_D, INSERT_L = 5.6, 4.7
SCREW_CLR = 4.3

TNG_HALF = 40.0                                 # tongue half-length (> BAR_W/2: the
                                                # tongues outrun the bar so the fixed
                                                # lock station always reaches them)


def _bar() -> cq.Workplane:
    """Bridge bar, built at global Y/Z (X centred on the pickup)."""
    y_hi, y_lo = CH.PU_FACE_HI - 0.3, CH.PU_FACE_LO + 0.3   # body clear of the bosses
    spine = box_at(BAR_W, y_hi - y_lo, BAR_H,
                   y=(y_hi + y_lo) / 2, z=(BAR_TOP + BAR_BOT) / 2)
    for yf, s in ((y_hi, 1), (y_lo, -1)):
        # End block bridging the spine down to the tongue band; bottom stays
        # 0.65 above motor 0's PCB top, which the far position slides over.
        # The −Y side runs ±TNG_HALF (past the bar ends) so the fixed lock screw
        # always reaches its tongue; the +Y side stays bar-width — its end zone
        # meets carriage 9's travel space at near positions, and only the −Y
        # tongue needs the reach.
        half = TNG_HALF if s < 0 else BAR_W / 2
        blk_bot = CH.PU_TNG_Z0 + 0.3
        spine = spine.union(box_at(2 * half, 6.0, BAR_TOP - blk_bot,
                                   y=yf - s * 3.0,
                                   z=(BAR_TOP + blk_bot) / 2))
        # tongue: launches from the end-block face, crosses the 0.3 body-to-boss
        # gap, rides the rail groove; tip stops 0.45 off the groove floor
        tng = 0.3 + 4.0 - 0.45
        spine = spine.union(box_at(
            2 * half, tng, (CH.PU_TNG_Z1 - CH.PU_TNG_Z0) - 2 * TNG_CLR,
            y=yf + s * tng / 2,
            z=(CH.PU_TNG_Z0 + CH.PU_TNG_Z1) / 2))
    # T-slot along X at Y0 (jaw feet)
    spine = spine.cut(box_at(SLOT_X, NECK_W, NECK_D + 0.1,
                             z=BAR_TOP - (NECK_D + 0.1) / 2))
    spine = spine.cut(box_at(SLOT_X, UC_W, UC_H,
                             z=BAR_TOP - NECK_D - UC_H / 2))
    return spine


def _jaw() -> cq.Workplane:
    """Width jaw. Local: bar top Z0, clamp face at X0 facing −X."""
    body = box_at(JAW_T, JAW_Y, JAW_H, x=JAW_T / 2, z=JAW_H / 2)
    # T-foot riding the slot (0.3/0.15 clearances), wing straight off the neck
    neck_bot = -(NECK_D - 0.15)
    foot = box_at(FOOT_L, NECK_W - 0.3, NECK_D - 0.15,
                  x=JAW_T - FOOT_L / 2, z=neck_bot / 2)
    foot = foot.union(box_at(FOOT_L, UC_W - 0.3, UC_H - 0.15,
                             x=JAW_T - FOOT_L / 2,
                             z=neck_bot - (UC_H - 0.15) / 2))
    body = body.union(foot)
    # lock: M4 set screw down a deep counterbore, insert low so the tip jams
    # the bar top
    cx, cy = JAW_T / 2 + 1.5, 9.0
    body = body.cut(cyl(INSERT_D, JAW_H - 5.0, z=5.0).translate((cx, cy, 0)))
    body = body.cut(cyl(SCREW_CLR, 7.0, z=-1).translate((cx, cy, 0)))
    return body


def pickup_demo() -> cq.Workplane:
    """DEMO pickup body (George L E-66-ish), centred X/Y, top at z=0."""
    return box_at(PK_W, PK_L, PK_H, z=-PK_H / 2)


def _shim() -> cq.Workplane:
    """Height shim under the pickup (between the jaws), bottom at z=0.
    Thickness = PK_H_MAX − pickup height; reprint to fine-tune the gap."""
    return box_at(PK_W - 2.0, 60.0, SHIM_T, z=SHIM_T / 2)


KNOB_D, KNOB_H = 12.0, 8.0


def _knob() -> cq.Workplane:
    """Grip knob for the X-lock screw (an M4×12 button head — the stocked
    92095A192): fluted rim; the button head presses into a Ø7.7 pocket in the
    underside (dab of CA — the lock torque is tiny). Bottom at z=0."""
    import math
    k = cyl(KNOB_D, KNOB_H, z=0.0)
    for i in range(8):                          # grip flutes
        a = 2 * math.pi * i / 8
        k = k.cut(cyl(2.5, KNOB_H + 2, z=-1.0)
                  .translate((KNOB_D / 2 * math.cos(a), KNOB_D / 2 * math.sin(a), 0)))
    k = k.cut(cyl(7.7, 2.5, z=-0.01))           # button-head pocket
    return k.cut(cyl(4.2, KNOB_H, z=-0.01))     # shank clearance


def pickup_lock_screw() -> cq.Workplane:
    """DEMO M4×12 button-head lock screw, axis Z: shank tip at z=0 (on the
    tongue), head on top."""
    return cyl(4.0, 12.0, z=0.0).union(cyl(7.5, 2.2, z=12.0))


pickup_bar  = _bar()
pickup_jaw  = _jaw()
pickup_shim = _shim()
pickup_knob = _knob()
