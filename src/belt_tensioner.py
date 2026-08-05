"""Belt-tension clamp — FOUR parts (PETG), ×10 (one per string).

Splices each cut GT2 belt into a loop, dials its tension, AND lets the belt drop in
freely then lock. Four printed parts:
  • ANCHOR + SLIDER — the two tension halves. One M4×30 turnbuckle screw (head bearing
    on the ANCHOR's −X face, threaded into a brass insert in the SLIDER) draws them
    together; turning it takes up slack CONTINUOUSLY, not in belt-tooth steps. Gap travel
    = 4 mm = 2 belt teeth of range (need ≥1 for continuous coverage; pitch 2 mm → 1 tooth
    = 2 mm of loop for an in-line splice), a full tooth of margin.
  • LIFTER_A + LIFTER_B — a ridged bar in each half's belt well. Screw OUT → the bar sits
    ~1.5 mm low on the well floor, ridges below the belt path → the belt threads through
    FREE. Screw IN → the bar rides the screw crest (proud of the floor) → its GT2 ridges
    mesh the belt teeth and the flat ceiling caps peel → positive grip. Lift the bar by a
    fingernail while seating the screw if it doesn't cam up on its own (no gravity reliance;
    no captive retention by request — keep the parts printable and easy to assemble).

HOLD / ANTI-CREEP: belt teeth → lifter ridges (positive mesh) → STEEL M4 screw (tension)
→ brass insert; plastic seats in COMPRESSION. No friction clamp anywhere (that is what
crept in the old motor slots). The insert takes the belt preload (~30 N) at ~10 % of its
pull-out — creep negligible. Retires the motor-slot + tension_fork scheme so the motors
can be fixed.

Frame: belt runs along X, teeth DOWN (mesh the FLOOR-side lifter ridges — they print
UPWARD, clean; the flat ceiling is a non-critical belt-retention bridge), +Z up, belt
back plane on z = 0. The screw runs below the belt at z = −4.5: low enough its Ø7.6 head
clears the belt floor (0.7 mm), high enough its crest stands proud in the wells. The head
is at the −X (motor-pulley) end for a right-angle / ball hex key. All four parts print
flat; each bar prints ridges-up as a small solid.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_y
from cadkit.fasteners import M4, cut_insert_bore, m4_button_screw, seated_insert

# ── belt cross-section ───────────────────────────────────────────────────────
BW  = D.BELT_W            # 5.0  belt width (Y)
BT  = D.BELT_T           # 1.4  belt back
BTH = D.BELT_TOOTH_H     # 0.75 tooth height
BP  = D.BELT_PITCH       # 2.0  pitch

# ── Z levels ─────────────────────────────────────────────────────────────────
Z_SCR    = -4.5                          # screw centreline
HEAD_D   = 7.6                           # M4 button head (ISO 7380)
HEAD_H   = 2.2
CREST    = Z_SCR + M4.screw_d / 2        # -2.5  Ø4 crest — the bar rides this when locked
DROP     = 1.5                           # bar drop when the screw is out (> tooth height, clears)
WELL_FLR = CREST - DROP                  # -4.0  bar rests here (on the well-floor shoulders) unlocked
BAR_H    = -CREST                        # 2.5   bar body height → ridges land on z0 when locked
CEIL_UZ  = BT + BTH + 0.15               # 2.30  ceiling underside (0.15 over the belt back)
WALL     = 1.6
TOP      = CEIL_UZ + WALL                # 3.90  part top
BOT      = Z_SCR - M4.screw_d / 2 - 2.0  # -8.5  part bottom (below the Ø4.4 channel)

TUN_W    = BW + 0.4                       # 5.4  belt width in the tunnel
WELL_W   = BW + 0.6                       # 5.6  well width (bar slide clearance)
BODY_W   = WELL_W + 2 * WALL              # 8.8  (Y) — one belt lane with cheeks
SCR_CLR  = M4.shaft_clr_d                 # 4.4  screw channel Ø

# ── X layout (M4×30; head at anchor −X, insert in slider +X) ─────────────────
HEAD_X   = -16.0                          # anchor −X outer face = screw head bearing face
SCREW_L  = 30.0
A_X1     = -4.0                           # anchor +X face
GAP      = 4.0                            # travel = 2 teeth
S_X0     = A_X1 + GAP                      # 0.0  slider −X face
S_X1     = 14.0                            # slider +X face (screw tip lands flush here)
INS_X    = 7.0                            # slider insert mouth (faces −X); bore runs +X
GRIP     = 6.0                            # each bar grips 3 teeth
GA0, GA1 = -13.0, -7.0                    # anchor bar well
GB0, GB1 = 1.0, 7.0                       # slider bar well


def cyl_x(d: float, length: float, x0: float, z: float = 0.0) -> cq.Workplane:
    """Solid cylinder along +X, base at x0, centred on (y=0, z)."""
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        d / 2, length, pnt=cq.Vector(x0, 0.0, z), dir=cq.Vector(1, 0, 0)))


def _ridges(x0: float, x1: float, zc: float, width: float) -> cq.Workplane:
    """GT2 half-round ridges (axis Y) at pitch BP over [x0,x1], centred at z=zc."""
    out = None
    for k in range(int((x1 - x0) / BP)):
        c = cyl_y(2 * BTH, width, y0=-width / 2, x=x0 + BP * (k + 0.5), z=zc)
        out = c if out is None else out.union(c)
    return out


def _half_body(x0: float, x1: float, w0: float, w1: float) -> cq.Workplane:
    """Solid block + flat belt tunnel (full length) + one bar WELL over [w0,w1]. The
    Ø4.4 screw channel is added by the caller (its X extent differs per half)."""
    body = box_at(x1 - x0, BODY_W, TOP - BOT, x=(x0 + x1) / 2, y=0.0, z=(TOP + BOT) / 2)
    body = body.cut(box_at(x1 - x0 + 2, TUN_W, CEIL_UZ,                 # belt tunnel (flat ceiling)
                           x=(x0 + x1) / 2, y=0.0, z=CEIL_UZ / 2))
    body = body.cut(box_at(w1 - w0, WELL_W, -WELL_FLR,                  # bar well down to the floor
                           x=(w0 + w1) / 2, y=0.0, z=WELL_FLR / 2))
    return body


def anchor() -> cq.Workplane:
    """−X half: belt well for LIFTER_A; the M4 head bears FLUSH on its −X face; the screw
    channel opens up into the well so the crest lifts the bar."""
    body = _half_body(HEAD_X, A_X1, GA0, GA1)
    body = body.cut(cyl_x(SCR_CLR, (A_X1 + 1) - HEAD_X, HEAD_X, Z_SCR))
    return body


def slider() -> cq.Workplane:
    """+X half: belt well for LIFTER_B; holds the brass insert (mouth −X, bore +X). The
    M4×30 tip lands flush at the +X face."""
    body = _half_body(S_X0, S_X1, GB0, GB1)
    body = body.cut(cyl_x(SCR_CLR, INS_X - (S_X0 - 1), S_X0 - 1, Z_SCR))
    body = cut_insert_bore(M4, body, (INS_X, 0.0, Z_SCR), (1.0, 0.0, 0.0),
                           clr_len=(S_X1 - INS_X) - M4.insert_l + 1.0,
                           reason="belt tensioner: metal thread, must not self-tap (anti-creep)")
    return body


def _lifter(length: float) -> cq.Workplane:
    """Ridged bar: BAR_H body with GT2 ridges on top (ridge centre = bar top). Prints
    ridges-up; local origin at the bar underside centre (z=0)."""
    bar = box_at(length, BW, BAR_H, x=0.0, y=0.0, z=BAR_H / 2)
    return bar.union(_ridges(-length / 2, length / 2, BAR_H, BW))


def lifter_a() -> cq.Workplane:
    return _lifter(GA1 - GA0 - 0.4)


def lifter_b() -> cq.Workplane:
    return _lifter(GB1 - GB0 - 0.4)


# ── dummies for the assembly render (purchased, no standalone STEP) ──────────
def screw_dummy() -> cq.Workplane:
    # native head-top-at-origin, shank −Z; rotate → shank +X, head at −X. Offset by HEAD_H so the
    # head/shank junction (the BEARING face) lands on HEAD_X and the head sits OUTSIDE the anchor.
    scr = m4_button_screw(SCREW_L, head_d=HEAD_D, head_h=HEAD_H).rotate((0, 0, 0), (0, 1, 0), -90)
    return scr.translate((HEAD_X - HEAD_H, 0.0, Z_SCR))


def insert_dummy() -> cq.Workplane:
    return seated_insert(M4, (INS_X, 0.0, Z_SCR), (1.0, 0.0, 0.0))


def seated_lifter(bar, well_mid: float, locked: bool = True) -> cq.Workplane:
    """Place a bar in its well: bottom on the screw crest (locked) or the well floor."""
    return bar.translate((well_mid, 0.0, (CREST if locked else WELL_FLR)))


# ── coupon: all four parts in PRINT orientation, spread in Y ─────────────────
def tensioner_coupon() -> cq.Workplane:
    a  = anchor().translate((0.0, -(BODY_W + 4.0), -BOT))
    s  = slider().translate((0.0, -(BODY_W + 4.0), -BOT))          # inline: same belt line
    la = lifter_a().translate((-6.0, +(BODY_W / 2 + 4.0), 0.0))
    lb = lifter_b().translate((+6.0, +(BODY_W / 2 + 4.0), 0.0))
    return a.union(s).union(la).union(lb)


anchor_part = anchor()
slider_part = slider()
