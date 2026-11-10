# -*- coding: utf-8 -*-
"""A PRINTED DRILL JIG for the cross hole through a Tr8x2 leadscrew that pins it into the
printed motor coupler (direct_bench / plank_bench's in-line motor).

SHOP TOOL, not a part of the instrument (user, 2026-11-09): "clamps the screw similarly to our
cut to length jig but then has a vertical shaft similar to the reaming jig". Two ideas borrowed
whole:

  from saw_jig   the rod lies along X in the DIAMOND tunnel (a 90 deg V it rests in on two
                 thread crests, a 45 deg roof over it), and saw_jig's own CAP drops down a clamp
                 channel onto it: one Quick-Grip squeezes cap, rod, jig and table in one stack.
                 The rod is pushed in until its end meets the END STOP, so the hole lands
                 PIN_FROM_END (5.0) from the end every time without measuring.
  from ream_jig  a TOWER over the rod with a vertical bore, here a socket for DROP-IN BUSHINGS:
                 one per drill, each a tube with the drill's bore and a flange that sits on the
                 tower's top, its foot BUSH_GAP over the rod's crest so the bit cannot walk off a
                 thread flank before it bites. An exit hole runs on down through the floor.

THE BITS are the user's set (Hercules, 2026-11-09; no 2.5 mm, no tap):
  PILOT  1/16 in (1.59) first: a short bit, stiff, starts the hole dead on the axis.
  PIN    1/8 in (3.18) through: clearance for the belt clamp's M3 x 12 (belt_tensioner.SCREW_L),
         which then passes the screw as a PIN and threads into the coupler's far wall. 0.18 of
         play on the M3 -- a few hundredths of a mm of nut travel at a reversal: fine for the bench.
  (For a TAPPED pin later: a 2.5 mm bit and an M3x0.5 hand tap, and a bushing for each -- add them
  to BUSHINGS; the bore is all that changes.)

HOW IT IS USED
  1. Push the screw in from -X until its end meets the stop.
  2. Drop the cap in, Quick-Grip it to the table (pad in the cap's pocket).
  3. PILOT bushing in, 1/16 bit through the screw (into the exit hole); oil, slow.
  4. Swap to the PIN bushing, 1/8 through. Unclamp, deburr both sides with the next size up.

PRINTS: the body table face down (+Z up: the tunnel's V and roof are 45 deg, the tower's bore is
round); each bushing flange down (its bore round along the build).
"""
from __future__ import annotations

import cadquery as cq

from . import motor_coupler as MC
from . import saw_jig as SJ

B = SJ.B
IN = 25.4

# ── the hole ────────────────────────────────────────────────────────────────
PIN_FROM_END = MC.PIN_FROM_END             # hole axis to the screw's end: the coupler's own
BUSHINGS = {"pilot": IN / 16, "pin": IN / 8}
BIT_CLR = 0.3                              # each side: the bushing SOCKET's slide (bores: BORE_EXTRA)

# ── the rod, as saw_jig holds it ───────────────────────────────────────────
ROD_R, ROD_Z = SJ.ROD_R, SJ.ROD_Z
CREST_Z = ROD_Z + ROD_R
STOP_X = PIN_FROM_END                      # the drill's axis is x = 0
STOP_T = 4 * B

# ── the tower and its bushings ─────────────────────────────────────────────
BUSH_OD = 10.0
SOCKET_D = BUSH_OD + 2 * BIT_CLR           # 10.6: a drop-in slide, 0.3 a side as the bits' bores.
                                           # Round holes print ~0.15-0.25 small on the diameter
                                           # (guide rod: +0.15 and +0.25 drawn both PRESS), so the
                                           # first draw's 10.3 would have been a press, not a drop-in
BUSH_GAP = 0.6                             # the bushing's foot over the rod's crest
BUSH_FLANGE = (14.0, 2 * B)                # Ø, thickness: sits on the tower's top
TOWER_WALL = 4 * B
TOWER_R = SOCKET_D / 2 + TOWER_WALL
TOWER_TOP = CREST_Z + BUSH_GAP + 28.0      # 28 of guide
BUSH_L = TOWER_TOP - (CREST_Z + BUSH_GAP)
EXIT_D = 4.5                               # under the rod: the bit's way out, chips with it

# ── the clamp: saw_jig's cap and channel, just -X of the tower ─────────────
CAP_X1 = -(TOWER_R + 1.0)
CAP_X0 = CAP_X1 - SJ.CAP_L
CH_X0, CH_X1 = CAP_X0 - SJ.CAP_CLR, CAP_X1 + SJ.CAP_CLR
HW = SJ.HW
X_MIN = CH_X0 - SJ.WALL
Z_TOP = SJ.Z_TOP                           # the cap's channel walls: the cap fits as for the saw
X_MAX = max(STOP_X + STOP_T, TOWER_R)      # the tower stands on the block, no ledge past its +X face

_box = SJ._box


def body() -> cq.Workplane:
    blk = _box(X_MIN, X_MAX, -HW, HW, 0.0, Z_TOP)
    blk = blk.cut(_box(CH_X0, CH_X1, -SJ.CH_HW, SJ.CH_HW, ROD_Z, Z_TOP + 1.0))   # clamp channel
    blk = blk.cut(SJ._tunnel(X_MIN - 1.0, STOP_X))                                # blind: the stop
    tower = cq.Workplane("XY").circle(TOWER_R).extrude(TOWER_TOP - Z_TOP + 0.01).translate((0, 0, Z_TOP - 0.01))
    out = blk.union(tower)
    out = out.cut(cq.Workplane("XY").circle(SOCKET_D / 2).extrude(TOWER_TOP - CREST_Z)
                  .translate((0, 0, CREST_Z + 0.01)))                             # bushing socket
    out = out.cut(cq.Workplane("XY").circle(EXIT_D / 2).extrude(ROD_Z + 1.0).translate((0, 0, -1.0)))
    return out


# THE BORES, MEASURED (user, 2026-11-10, PETG-GF 0.8 nozzle, printed flange down):
#   1/8  drawn bit + 0.6 (Ø3.78): GOOD -- tight, the bit runs through it to a clean fit. Kept.
#   1/16 drawn bit + 0.6 (Ø2.19): TOO TIGHT. A small hole loses more of itself (the nozzle's
#        ~1 mm concave corner), so the 1/8's +0.6 does not carry down. Not yet known how much
#        more: PILOT_TRY prints three, marked by 1/2/3 notches on the flange's rim; keep the one
#        that is tight but runs through, like the 1/8's, and put its extra in BORE_EXTRA.
BORE_EXTRA = {"pin": 0.6, "pilot": 0.6}    # drawn bore - bit, on the diameter
PILOT_TRY = (0.9, 1.1, 1.3)                # the pilot's trial bores: notches 1, 2, 3


def bushing(kind: str = "pin", extra: float | None = None, notches: int = 0) -> cq.Workplane:
    """Drawn in place, in the tower: its foot BUSH_GAP over the crest, the flange on the top.
    `extra` overrides BORE_EXTRA[kind]; `notches` cuts that many marks in the flange's rim."""
    d = BUSHINGS[kind] + (BORE_EXTRA[kind] if extra is None else extra)
    z0 = CREST_Z + BUSH_GAP
    fd, ft = BUSH_FLANGE
    b = cq.Workplane("XY").circle(BUSH_OD / 2).extrude(BUSH_L).translate((0, 0, z0))
    b = b.union(cq.Workplane("XY").circle(fd / 2).extrude(ft).translate((0, 0, TOWER_TOP)))
    for i in range(notches):                       # round SCALLOPS 1.0 into the rim, 90 deg apart:
        # centred outside the rim, so they meet it at obtuse corners (square notches left tips)
        b = b.cut(cq.Workplane("XY").circle(1.6).extrude(ft + 2)
                  .translate((fd / 2 + 0.6, 0, TOWER_TOP - 1))
                  .rotate((0, 0, 0), (0, 0, 1), 90.0 * i))
    return b.cut(cq.Workplane("XY").circle(d / 2).extrude(BUSH_L + ft + 2).translate((0, 0, z0 - 1)))


def pilot_trials():
    """The three trial pilot bushings, side by side for one plate, flange down."""
    return [(f"pin_drill_bushing_pilot_{n + 1}",
             bushing("pilot", e, n + 1).rotate((0, 0, 0), (1, 0, 0), 180)
             .translate((18.0 * n, 0, 0))) for n, e in enumerate(PILOT_TRY)]


def cap() -> cq.Workplane:
    """saw_jig's cap, moved to this channel."""
    return SJ.cap().translate((CAP_X0 - SJ.CAP_X0, 0, 0))


def rod(length=60.0) -> cq.Workplane:
    """The Tr8 rod at its crest, pushed to the stop -- for checking only."""
    return cq.Workplane("YZ").circle(ROD_R).extrude(length).translate((STOP_X - length, 0.0, ROD_Z))


def components():
    """The scratch view's scope: body, cap, the pin bushing and a rod."""
    return [("pin_drill_jig", body()), ("pin_drill_jig_cap", cap()),
            ("pin_drill_bushing", bushing("pin")), ("rod", rod())]


if __name__ == "__main__":
    j = body().val()
    r = rod().val()
    print("body %.1f cm3, solids %d, valid %s" % (j.Volume() / 1000, len(j.Solids()), j.isValid()))
    print("rod in body %.4f mm3, cap on rod %.4f, bushing in body %.4f"
          % (j.intersect(r).Volume(), cap().val().intersect(r).Volume(),
             bushing().val().intersect(j).Volume()))
    print("guide %.1f, the bushing's foot %.1f over the crest; hole %.1f from the end"
          % (BUSH_L, BUSH_GAP, PIN_FROM_END))
