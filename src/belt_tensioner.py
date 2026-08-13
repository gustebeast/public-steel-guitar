"""Belt-tension clamp — FOUR parts (PETG), ×10 (one per string).

Splices each cut GT2 belt into a loop, dials its tension, AND lets the belt drop in
freely then lock. Four printed parts:
  • ANCHOR + SLIDER — the two tension halves. One M4×45 turnbuckle screw (head bearing
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
→ M4 insert used as a CAPTIVE NUT. The screw pulls the insert against a solid Ø4.4→Ø6
SHOULDER, so the ~30 N belt preload bears on SOLID PCTG (compression), NOT the heat-set
melt bond — the melt (or a press fit) only has to ANTI-ROTATE the insert. Same insert as
elsewhere in the BOM (no new line item). No friction clamp anywhere (that is what crept in
the old motor slots). Retires the motor-slot + tension_fork scheme so the motors can be fixed.

Frame: belt runs along X, teeth DOWN (mesh the FLOOR-side lifter ridges — they print
UPWARD, clean; the flat ceiling is a non-critical belt-retention bridge), +Z up, belt
back plane on z = 0. The screw runs below the belt at z = −4.5: low enough its Ø7.6 head
clears the belt floor (0.7 mm), high enough its crest stands proud in the wells. The head
is at the −X (motor-pulley) end for a right-angle / ball hex key.

PRINT: the two HALVES build +X (on the −X face) — the belt tunnel, screw channel and Ø6
insert bore all run along the build, so they come out as clean walls and round bores (a
sagging ceiling-bridge and out-of-round bores if built +Z), and the head-bearing face is
the flat first layer. Each well's +X end is closed by a 45° self-supporting RAMP (springs
from the solid base, closes toward the open tunnel), so nothing bridges — the halves print
support-free. The BARS build −Y→+Y (belt-width vertical) so the ridge curves and the concave
seat land in the layer plane. The insert pocket opens to the +X (up) face, so the insert
installs from the top AND both halves now print FULLY support-free (the old insert-pocket-
bottom bridge is gone).
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_y
from cadkit.fasteners import M4, m4_button_screw, seated_insert

# ── belt cross-section ───────────────────────────────────────────────────────
BW  = D.BELT_W            # 5.0  belt width (Y)
BT  = D.BELT_T           # 1.4  belt back
BTH = D.BELT_TOOTH_H     # 0.75 tooth height
BP  = D.BELT_PITCH       # 2.0  pitch

# ── Z levels ─────────────────────────────────────────────────────────────────
Z_SCR    = -6 * D.BEAD                   # -4.8  screw centreline
HEAD_D   = 7.6                           # M4 button head (ISO 7380)
HEAD_H   = 2.2
CREST    = Z_SCR + M4.screw_d / 2        # -2.8  Ø4 screw crest (the bar rides on it when locked)

# concave seat — the crest seats FLUSH into it (was a shallow dimple that floated 0.8 mm above it)
SEAT_CLR = 0.2                           # lifter prints at a 0.2 mm nozzle → 1-bead seat clearance
SEAT_RC  = M4.screw_d / 2 + SEAT_CLR     # 2.2  cradle radius: hugs the Ø4 crest
SEAT_STRADDLE = 0.4                      # bar-bottom flanks wrap this far below the crest (anti-roll)
LOCK_Z   = CREST - SEAT_STRADDLE         # -3.2  locked bar-bottom height (cradle tangent on the crest)
SEAT_ZG  = CREST - SEAT_RC - LOCK_Z      # -1.8  cradle axis in the BAR-LOCAL frame (flanks at z0)

CEIL_UZ  = BT + BTH + 0.15               # 2.30  ceiling underside (0.15 over the belt back)
WALL     = 1.6
TOP      = CEIL_UZ + WALL                # 3.90  part top
BAR_H    = -LOCK_Z                       # 3.2  body height → ribs reach the belt valley floor (z=BTH) locked

# unlocked rest — ribs sit JUST below the belt teeth: enough to thread the belt, no more. Extra
# clearance would only drop the bar lower and make it harder for the screw to cam up. Tips are at z0.
RIB_CLR  = 0.3                           # unlocked rib clearance below the belt tooth tips (z0)
WELL_FLR = -RIB_CLR - BAR_H - BTH        # -4.25  well floor = unlocked rest (rib tops at −RIB_CLR)
BOT      = Z_SCR - M4.screw_d / 2 - 2.0  # -8.8  part bottom (below the Ø4.4 channel)

# +X retention (anchor) — a 45°-supported ramp of RET_RUN added material at the mouth blocks the
# lifter's +X exit at every operating Z. Only lifting the bar to its highest Z (up into the belt
# tunnel, belt out) clears it; once the belt is threaded it caps the rise, so the bar never gets there.
RET_RUN  = 2 * D.BEAD                    # 1.6  ramp run = rise (45°) — the "1.6 mm of added material"
RET_TOP  = WELL_FLR + RET_RUN            # -2.65  ramp top (above LOCK_Z → the locked bar stays blocked)
RET_CH   = 0.6                           # 45° chamfer on the lifter's +X-bottom clears the ramp

# auto-lift — a 45° lead-in on the lifter's −X-bottom so the entering crest cams the bar up to the seat
LEADIN   = 2.0                           # −X lead-in chamfer height (spans the crest at the unlocked rest)

TUN_W    = BW + 0.4                       # 5.4  belt width in the tunnel
WELL_W   = BW + 0.6                       # 5.6  well width (bar slide clearance)
BODY_W   = WELL_W + 2 * WALL              # 8.8  (Y) — one belt lane with cheeks
SCR_CLR  = M4.shaft_clr_d                 # 4.4  screw channel Ø

# ── X layout: derived from the tooth count, so grip WIDTH is a single knob ────
# ~6 teeth per bar reaches the GT2 belt's full working rating (mirrors the "6 teeth in
# mesh" pulley rule); fewer derates the joint and overstresses the lead tooth. The screw
# must run under BOTH wells to lift both bars, so it spans the whole ~48 mm clamp → M4×45
# (the clamp grew ~6 mm when the 45° end ramps pushed the +X faces + the slider insert out).
N_TEETH  = 6                              # teeth gripped per bar
LIFT_LEN = N_TEETH * BP + 0.2             # 12.2  bar length (fits N_TEETH ridges)
GRIP     = LIFT_LEN + 0.4                 # 12.6  well length (bar slides in it)
GAP      = 4.0                            # travel = 2 teeth (unchanged — we GROW, not eat it)
_MRG     = 2 * D.BEAD                     # 1.6 −X (bed-end) margins — that end needs no ramp
RAMP_RUN = -WELL_FLR                      # 4.0  a 45° self-supporting ramp needs run = well depth
HEAD_X   = -20.0                          # anchor −X face = screw head bearing face (the print BED)
GA0      = HEAD_X + _MRG                  # anchor bar well (−X end = bed, no ramp)
GA1      = GA0 + GRIP
A_X1     = GA1 + RAMP_RUN                 # anchor +X face — the well ramp closes exactly here
S_X0     = A_X1 + GAP                     # slider −X face
GB0      = S_X0 + _MRG                    # slider bar well (−X end = bed, no ramp)
GB1      = GB0 + GRIP
INS_X    = GB1 + RAMP_RUN                 # insert mouth — AFTER the well-B ramp, so it keeps a full collar
S_X1     = INS_X + M4.insert_l + 2.0      # slider +X face (insert pocket + tip clr)
SCREW_L  = 45.0                           # M4×45 spans head → insert (grew with the ramp; new BOM length)


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


def _end_ramp(w1: float) -> cq.Workplane:
    """45° self-supporting closure of a well's +X end. A right-triangle prism (X-Z section,
    full well width in Y) that carves the floor UP from WELL_FLR at x=w1 to z0 at x=w1+RAMP_RUN.
    Standing the half on +X, the build direction is +X: this ramp springs from the solid base
    below the floor and closes toward the (already-open) belt tunnel at 45°, so it prints with
    no ceiling/bridge. It also becomes the bar's +X end-stop (the bar's flat floor meets the
    rising ramp at x=w1), so no bar travel is lost."""
    pts = [(w1, WELL_FLR), (w1, 0.0), (w1 + RAMP_RUN, 0.0)]
    return cq.Workplane("XZ").polyline(pts).close().extrude(WELL_W / 2, both=True)


def _ret_ramp(x1: float) -> cq.Workplane:
    """+X RETENTION ramp for the anchor: a 45° wedge (full well width in Y) filling the well's
    +X-bottom corner — floor rising from WELL_FLR at x=x1−RET_RUN up to RET_TOP at the +X mouth
    (x=x1). Building +X it is an up-facing floor, so it self-supports (a vertical stop face can't
    print in this orientation). It blocks the lifter's +X exit at every operating Z; the bar only
    clears it above RET_TOP — a height it reaches only lifted into the belt tunnel with the belt
    out, since the threaded belt caps its rise. The lifter's +X-bottom is chamfered (RET_CH) to
    clear the ramp face."""
    pts = [(x1 - RET_RUN, WELL_FLR), (x1, WELL_FLR), (x1, RET_TOP)]
    return cq.Workplane("XZ").polyline(pts).close().extrude(WELL_W / 2, both=True)


def _half_body(x0: float, x1: float, w0: float, w1: float) -> cq.Workplane:
    """Solid block + flat belt tunnel (full length) + one bar WELL over [w0,w1] closed at its
    +X end by a 45° self-supporting ramp. The Ø4.4 screw channel is added by the caller (its X
    extent differs per half)."""
    body = box_at(x1 - x0, BODY_W, TOP - BOT, x=(x0 + x1) / 2, y=0.0, z=(TOP + BOT) / 2)
    body = body.cut(box_at(x1 - x0 + 2, TUN_W, CEIL_UZ,                 # belt tunnel (flat ceiling)
                           x=(x0 + x1) / 2, y=0.0, z=CEIL_UZ / 2))
    body = body.cut(box_at(w1 - w0, WELL_W, -WELL_FLR,                  # bar well down to the floor
                           x=(w0 + w1) / 2, y=0.0, z=WELL_FLR / 2))
    body = body.cut(_end_ramp(w1))                                     # 45° self-supporting +X closure
    return body


def anchor() -> cq.Workplane:
    """−X half (the SIMPLE one — no insert): the M4 head bears flush on the −X (bed) face and the
    screw runs through, its crest lifting LIFTER_A. Three cuts + one retention ramp, all keyed off
    the belt/lifter so the belt tunnel and the lifter well share walls EXACTLY — no ledge where they
    meet (the old lip came from the tunnel being 0.2 mm narrower than the well):

      1. screw channel — a Ø4.4 cylinder on the screw axis, full length (head → gap → slider).
      2. lifter well   — a LANE-wide slot down to the well floor, spanning the lifter GRIP but
                         STOPPING SHORT of the −X face: the _MRG-thick wall at GA0 is the load
                         back-stop the belt pulls LIFTER_A into, so the bar can't escape the −X
                         (belt-entry) side.
      3. belt tunnel   — the SAME LANE width and the SAME +X extent as the well, but run all the
                         way OUT the −X face so the belt threads in from the pulley.
      4. +X retention  — a 45°-supported ramp (`_ret_ramp`) UNIONED back into the well's +X-bottom
                         corner. It blocks LIFTER_A from being pushed out the +X mouth (by the
                         entering screw) at every operating Z; the bar clears it only lifted up into
                         the belt tunnel (belt out), so once the belt is threaded it can never eject.

    #2 and #3 share LANE and the +X extent, so their Y walls coincide; they differ only at the −X
    end (belt open, lifter walled). LIFTER_A drops in from the top with the belt out, then rests low
    behind the retention ramp."""
    LANE   = WELL_W                                 # ONE Y width for BOTH cuts → their walls coincide (no lip)
    x1     = GA1                                    # lifter well +X end = the +X mouth (sized to the lifter)
    mouth  = x1 + 1.0                               # +X mouth (overshoot → cleanly open above the ramp)
    bx0    = HEAD_X - 1.0                            # belt runs OUT the −X face (overshoot → cleanly open)
    body = box_at(x1 - HEAD_X, BODY_W, TOP - BOT, x=(HEAD_X + x1) / 2, y=0.0, z=(TOP + BOT) / 2)
    body = body.cut(box_at(mouth - GA0, LANE, -WELL_FLR,                              # 2  lifter well
                           x=(GA0 + mouth) / 2, y=0.0, z=WELL_FLR / 2))               #    (−X wall at GA0)
    body = body.cut(box_at(mouth - bx0, LANE, CEIL_UZ,                                # 3  belt tunnel
                           x=(bx0 + mouth) / 2, y=0.0, z=CEIL_UZ / 2))                #    (open at −X)
    body = body.union(_ret_ramp(x1))                                                 # 4  +X retention ramp
    body = body.cut(cyl_x(SCR_CLR, mouth - HEAD_X, HEAD_X, Z_SCR))                    # 1  screw channel — cut
    return body                                                                      #    LAST, so it clears the ramp too


def slider() -> cq.Workplane:
    """+X half: belt well for LIFTER_B; holds the M4 insert used as a CAPTIVE NUT. The Ø4.4
    screw channel ends at INS_X in a Ø4.4→Ø6 SHOULDER — the screw pulls the insert −X against
    that solid PCTG shoulder, so the belt tension bears on SOLID PLASTIC, not the heat-set melt
    bond (the melt/press only has to ANTI-ROTATE the insert while the screw threads in). The Ø6
    pocket is OPEN to the +X face — the print's UP face — so the insert can actually be
    INSTALLED: the old bore was Ø6 buried behind Ø4.4 at BOTH ends, which trapped the Ø6 insert
    (it couldn't pass either face). Opening it also deletes the old insert-pocket-bottom bridge."""
    body = _half_body(S_X0, S_X1, GB0, GB1)
    body = body.cut(cyl_x(SCR_CLR, INS_X - (S_X0 - 1), S_X0 - 1, Z_SCR))            # screw channel; its +X end IS the bearing shoulder
    body = body.cut(cyl_x(M4.insert_pilot_d, (S_X1 - INS_X) + 1.0, INS_X, Z_SCR))   # Ø6 insert pocket, OPEN at the +X face to install
    return body


def _lifter(length: float = LIFT_LEN) -> cq.Workplane:
    """Ridged bar (N_TEETH ridges), printed at a 0.2 mm nozzle (the ONLY 0.2 mm part — the ribs and
    seat need the resolution; everything else is 0.8 mm). The XZ body profile carries both end
    chamfers, then GT2 ridges union on top and a CONCAVE screw seat cuts the underside:

      • SEAT — a Ø(2·SEAT_RC) groove that hugs the Ø4 crest so the screw seats FLUSH (was a shallow
        dimple whose apex floated 0.8 mm above the crest). Sits tangent on the crest at LOCK_Z.
      • −X LEAD-IN — a 45° chamfer on the −X-bottom: the crest, entering from −X, rides UP it and
        cams the bar into the seat (no manual lift).
      • +X CHAMFER — a 45° cut on the +X-bottom (RET_CH) that clears the anchor's retention ramp.

    Modelled in the WORKING pose (ribs +Z); the coupon rotates it to the −Y→+Y PRINT pose so the
    ridge curves and the seat land in the layer plane."""
    L = length
    prof = [(-L / 2 + LEADIN, 0.0),       # −X-bottom: 45° lead-in for the entering crest
            (L / 2 - RET_CH, 0.0),        # +X-bottom: 45° chamfer clearing the retention ramp
            (L / 2, RET_CH),
            (L / 2, BAR_H),               # +X face, full height
            (-L / 2, BAR_H),              # −X face, full height
            (-L / 2, LEADIN)]
    bar = cq.Workplane("XZ").polyline(prof).close().extrude(BW / 2, both=True)
    bar = bar.union(_ridges(-L / 2, L / 2, BAR_H, BW))
    seat = cyl_x(2 * SEAT_RC, L + 2, -L / 2 - 1, z=SEAT_ZG)                 # flush concave crest seat
    return bar.cut(seat)


def lifter_a() -> cq.Workplane:
    return _lifter()


def lifter_b() -> cq.Workplane:
    return _lifter()


# ── dummies for the assembly render (purchased, no standalone STEP) ──────────
def screw_dummy() -> cq.Workplane:
    # native head-top-at-origin, shank −Z; rotate → shank +X, head at −X. Offset by HEAD_H so the
    # head/shank junction (the BEARING face) lands on HEAD_X and the head sits OUTSIDE the anchor.
    scr = m4_button_screw(SCREW_L, head_d=HEAD_D, head_h=HEAD_H).rotate((0, 0, 0), (0, 1, 0), -90)
    return scr.translate((HEAD_X - HEAD_H, 0.0, Z_SCR))


def insert_dummy() -> cq.Workplane:
    return seated_insert(M4, (INS_X, 0.0, Z_SCR), (1.0, 0.0, 0.0))


def seated_lifter(bar, well_mid: float, locked: bool = True) -> cq.Workplane:
    """Place a bar in its well: flush on the screw crest (locked = LOCK_Z) or on the well floor
    (unlocked = WELL_FLR, ribs just clear of the belt)."""
    return bar.translate((well_mid, 0.0, (LOCK_Z if locked else WELL_FLR)))


# ── coupon: all four parts in PRINT orientation, spread in Y ─────────────────
def tensioner_coupon() -> cq.Workplane:
    """All four parts in their PRINT poses. HALVES build +X: the belt tunnel, screw
    channel and Ø6 insert bore all run along the build → clean walls + round bores (a
    ceiling-bridge and sagging bores if built +Z), and the head-bearing face is the flat
    first layer. BARS build −Y→+Y: the ridge curves + concave seat land in the layer plane."""
    def _on_bed(w):
        return w.translate((0.0, 0.0, -w.val().BoundingBox().zmin))
    a = _on_bed(anchor().rotate((0, 0, 0), (0, 1, 0), -90)).translate((0.0, -14.0, 0.0))
    s = _on_bed(slider().rotate((0, 0, 0), (0, 1, 0), -90)).translate((0.0, +2.0, 0.0))
    la = _on_bed(lifter_a().rotate((0, 0, 0), (1, 0, 0), 90)).translate((22.0, -6.0, 0.0))
    lb = _on_bed(lifter_b().rotate((0, 0, 0), (1, 0, 0), 90)).translate((22.0, +6.0, 0.0))
    return a.union(s).union(la).union(lb)


anchor_part = anchor()
slider_part = slider()
