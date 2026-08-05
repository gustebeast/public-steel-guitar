"""Belt-tension clamp — ANCHOR + SLIDER (PETG). ×10 (one per string).

Splices each cut GT2 belt into a loop AND dials its tension in one part. The two cut
ends mesh teeth-up into two ridged tunnels — the ANCHOR grips one end, the SLIDER the
other — and a single M4 turnbuckle screw (an existing M4×20 button) draws the slider
toward the anchor to take up slack. Tension is set by TURNING the screw: continuous
and fine, NOT quantised by cutting belt teeth. Coarse-cut the loop a hair long, snap
the clamp on loose, then wind the screw to the target tension. This retires the old
motor-slot + tension_fork scheme, so the motors can be fixed in a solid box.

ANTI-CREEP BY CONSTRUCTION — the whole point. Load path:
    belt teeth → tunnel ridges (positive tooth mesh, ~5 teeth, low shear)
              → STEEL M4 screw (tension) → M4 brass heat-set insert.
No smooth friction clamp anywhere (that is exactly what crept in the old motor slots).
The insert carries the belt preload (~30 N) at ~10 % of its pull-out, so plastic creep
is negligible. A captured steel HEX NUT would be even more positive, but 7 mm across
flats does not fit the 8.6 mm belt-lane body; the brass insert is the idiomatic project
"nut" and is amply strong here. (If a nut is wanted later, the belts would need more Y
room or a wider local boss.)

Local frame: belt runs along X, teeth +Z, +Z up, belt back on z = 0. The two parts nest
via a TONGUE (anchor) / SOCKET (slider) below the belt that also carries the screw and
keys them in Y/Z against the offset screw's tip-over moment. The head is at the +X end
(the long open run toward the screw pulley) for a right-angle / ball hex key. Both parts
print flat, TUNNEL-UP — the ridged ceiling is a self-supporting GT2 arch, no supports.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_y
from cadkit.fasteners import (M4, cut_insert_bore, cut_clearance,
                              m4_button_screw, seated_insert)

# ── belt cross-section ───────────────────────────────────────────────────────
BW  = D.BELT_W            # 5.0  belt width (Y)
BT  = D.BELT_T           # 1.4  belt back thickness
BTH = D.BELT_TOOTH_H     # 0.75 tooth height
BP  = D.BELT_PITCH       # 2.0  tooth pitch

# ── tunnel (belt teeth DOWN, ridged FLOOR meshes them) ───────────────────────
# Ridges live on the FLOOR (not the ceiling) so they print UPWARD and clean; the
# flat ceiling is just a bridge that retains the belt back (non-critical, spans the
# 5.4 tunnel fine). Belt goes in teeth-down: teeth 0..BTH mesh the floor ridges, back
# BTH..BTH+BT, 0.3 clear under the ceiling.
TUN_W    = BW + 0.4                 # 5.4  tunnel width (Y)
CEIL     = BT + BTH + 0.30          # 2.45 tunnel height (belt + a hair)
RIDGE_Z  = 0.0                      # ridge-cylinder centre on the floor; protrudes up BTH into a valley
WALL     = 1.6                      # two-bead wall over/around the tunnel
BODY_W   = TUN_W + 2 * WALL         # 8.6  (Y) — one belt lane (9.5 pitch) with cheeks
TOP      = CEIL + WALL              # 4.05 top of the ceiling wall

# ── below-belt boss: the M4 turnbuckle + a low keying tab ────────────────────
# The two grip blocks butt with a TRAVEL gap and are drawn together by one M4×20
# screw offset below the belt. The Ø6 insert only fits a full-width block, so it
# lives in the ANCHOR grip block (not a thin tongue). A low keying TAB/GROOVE below
# the screw resists the offset screw's tip-over moment.
Z_SCR    = -5.0                     # screw centreline, below the belt floor
HEAD_D   = 7.6                      # M4 button head (ISO 7380) — single-sourced to the dummy below
HEAD_H   = 2.2
GRIP     = 8.0                      # each end gripped over 4 teeth
GAP      = 4.0                      # travel: the gap the screw winds closed

A_X1 = -GRIP / 2 - 1.0             # anchor grip block +X face  (-5.0) = insert mouth
A_X0 = A_X1 - GRIP                 # anchor grip block -X face  (-13.0)
S_X0 = A_X1 + GAP                  # slider -X face             (-1.0)
S_X1 = S_X0 + 4.0 + GRIP           # slider +X outer face       (+11.0) = screw head
GB0  = S_X1 - GRIP                 # slider grip-B ridge start  (+3.0)
INS_X  = A_X1                      # insert mouth (+X face of the anchor block)
BEAR_X = S_X1                      # head BEARING FACE = the slider +X outer face. m4_button_screw is
HEAD_X = BEAR_X + HEAD_H           # authored head-top-at-origin, shank -X, so the DUMMY sits one head
                                   # height further +X or the head models INSIDE the slider.

TAB_W    = 5.0                     # keying tab width (Y)
# Tab roof clears the Ø4 shank, which sweeps this whole span in OPEN AIR (the travel gap) between the
# anchor insert and the slider bore — so this is a hard clearance, not a wall. -6.5 cut 0.5 into it.
SHANK_CLR = 0.6
TAB_TOP  = Z_SCR - M4.screw_d / 2 - SHANK_CLR                  # -7.6
TAB_X0   = A_X1                    # tab runs +X from the anchor face
TAB_X1   = A_X1 + GRIP - 2.0       # into the slider groove (+1.0)
# Boss bottom takes the DEEPER of the two things below the screw axis: the head circle must land wholly
# on the bearing face, and the keying tab must still be a 2-bead section under its clearance. (Both land
# on -9.2 as drawn; whichever wins, the head still clears the belt floor by HEAD_D/2 above the axis.)
BOT      = min(Z_SCR - HEAD_D / 2 - 0.4, TAB_TOP - D.MIN_WALL_2P)


def _belt_slot(x0: float, x1: float) -> cq.Workplane:
    """The belt pass-through, floor on z=0, height CEIL."""
    return box_at(x1 - x0, TUN_W, CEIL, x=(x0 + x1) / 2, y=0.0, z=CEIL / 2)


def _ridges(x0: float, x1: float) -> cq.Workplane:
    """GT2 ridges (half-round, axis Y) protruding down from the ceiling into the
    tooth valleys over [x0, x1]. Same meshing geometry as the old splice clamp."""
    out = None
    n = int((x1 - x0) / BP)
    for k in range(n):
        x = x0 + BP * (k + 0.5)
        c = cyl_y(2 * BTH, TUN_W, y0=-TUN_W / 2, x=x, z=RIDGE_Z)
        out = c if out is None else out.union(c)
    return out


def anchor() -> cq.Workplane:
    """-X part: grips belt end A in a ridged tunnel and holds the M4 insert in its
    full-width block (mouth +X). A low tab reaches +X into the slider groove to key
    the joint against the offset screw's tip-over moment."""
    body = box_at(A_X1 - A_X0, BODY_W, TOP - BOT,
                  x=(A_X0 + A_X1) / 2, y=0.0, z=(TOP + BOT) / 2)
    body = body.union(box_at(TAB_X1 - TAB_X0, TAB_W, TAB_TOP - BOT,       # keying tab
                             x=(TAB_X0 + TAB_X1) / 2, y=0.0, z=(TAB_TOP + BOT) / 2))
    body = body.cut(_belt_slot(A_X0, A_X1)).union(_ridges(A_X0, A_X1))
    # M4 brass insert, mouth at the +X face; the screw threads in -X (metal thread).
    # Clearance runs THROUGH the -X face (GRIP + 1) so the screw can never bottom out before it reaches
    # tension: the tip advances by GAP as the joint winds closed, and a blind bore sized to the -X face
    # exactly would have it touching down at full travel.
    body = cut_insert_bore(M4, body, (INS_X, 0.0, Z_SCR), (-1.0, 0.0, 0.0), clr_len=GRIP + 1.0,
                           reason="belt tensioner: metal thread, must not self-tap (anti-creep)")
    return body


def slider() -> cq.Workplane:
    """+X part: grips belt end B; the M4 head seats at its +X face (right-angle/ball
    hex key), and a groove takes the anchor's keying tab."""
    body = box_at(S_X1 - S_X0, BODY_W, TOP - BOT,
                  x=(S_X0 + S_X1) / 2, y=0.0, z=(TOP + BOT) / 2)
    body = body.cut(_belt_slot(S_X0, S_X1)).union(_ridges(GB0, S_X1))     # ridges over grip B
    # groove for the anchor keying tab (open -X), with room for the wind-in travel
    gr_x0, gr_x1 = S_X0 - 1.0, TAB_X1 + GAP
    body = body.cut(box_at(gr_x1 - gr_x0, TAB_W + 0.6, (TAB_TOP + 0.2) - BOT,
                           x=(gr_x0 + gr_x1) / 2, y=0.0, z=((TAB_TOP + 0.2) + BOT) / 2))
    # M4 clearance from the +X bearing face across to the anchor insert. NO pocket here: the head bears
    # FLUSH on this face (docstring), and cut_m4_pocket is the Ø6x5 HEAT-SET pocket, not a head seat --
    # calling it put a second insert pocket in the slider that neither the design nor the BOM has.
    body = cut_clearance(M4, body, (BEAR_X, 0.0, Z_SCR), (-1.0, 0.0, 0.0), length=S_X1 - S_X0 + 1.0)
    return body


# ── dummies for the assembly render (purchased, no standalone STEP) ───────────
def screw_dummy() -> cq.Workplane:
    """M4×20 button: head BEARING on the slider +X face, shank running -X into the insert."""
    scr = m4_button_screw(20.0, head_d=HEAD_D, head_h=HEAD_H).rotate((0, 0, 0), (0, 1, 0), 90)
    return scr.translate((HEAD_X, 0.0, Z_SCR))                      # native -Z shank → -X


def insert_dummy() -> cq.Workplane:
    """Brass insert seated in the anchor bore, mouth at the +X face, barrel -X —
    same (point, direction) convention as the cut_insert_bore that made the pocket."""
    return seated_insert(M4, (INS_X, 0.0, Z_SCR), (-1.0, 0.0, 0.0))


# ── coupon: both parts in PRINT orientation (tunnel-up), split apart in Y so the
#    slicer sees two bodies. Shares the exact production geometry above. ────────
def tensioner_coupon() -> cq.Workplane:
    a = anchor().translate((0.0, -(BODY_W / 2 + 3.0), -BOT))   # sit on the bed (z 0 = bed)
    s = slider().translate((0.0, +(BODY_W / 2 + 3.0), -BOT))
    return a.union(s)


anchor_part = anchor()
slider_part = slider()
