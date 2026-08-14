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

WELL_W   = BW + 0.6                       # 5.6  well width (bar slide clearance) = the ONE belt lane
BODY_W   = WELL_W + 2 * WALL              # 8.8  (Y) — one belt lane with cheeks
SCR_CLR  = M4.shaft_clr_d                 # 4.4  screw channel Ø

# ── X layout — ONE clamp_half serves BOTH sides (the +X half is it turned 180° about Z) ───────
# The half is symmetric about its own y=0 plane, so its mirror across the gap IS a 180° Z rotation
# → printable as ONE SKU. Layout derived from the tooth count, so grip WIDTH is a single knob.
N_TEETH  = 6                              # teeth gripped per bar (~full GT2 rating; fewer overstresses the lead tooth)
LIFT_LEN = N_TEETH * BP + 0.2             # 12.2  bar length (fits N_TEETH ridges)
GRIP     = LIFT_LEN + 0.4                 # 12.6  well length (bar slides in it)
GAP      = 4.0                            # gap between the two inner mouths = tension travel (2 belt teeth)
_MRG     = 2 * D.BEAD                     # 1.6  −X (bed-end) back-stop wall — that end needs no ramp
HEAD_X   = -20.0                          # half-A −X (outer) face = fastener bearing face / print BED
GA0      = HEAD_X + _MRG                  # -18.4  well −X end (the back-stop wall)
GA1      = GA0 + GRIP                     # -5.8   well +X end = the inner mouth (faces the gap)
WELL_MID_A = (GA0 + GA1) / 2              # -12.1  lifter_a well centre

# half-B = clamp_half turned 180° about Z, shifted so its inner mouth sits GAP past half-A's.
TB       = 2 * GA1 + GAP                  # -7.6   half-B X-translation after the 180° Z spin
HALF_B_OUTER = -HEAD_X + TB               # 12.4   half-B +X (outer) face — the insert-nut bears here
WELL_MID_B = -WELL_MID_A + TB             # 4.5    lifter_b well centre (SAME lifter, placed un-rotated)

# ONE M4 screw: head on half-A's −X face → both Ø4.4 channels → the insert used as an EXTERNAL nut
# on half-B's +X face. Sized for ~2 teeth (= GAP) of tightening take-up (recovers a 1-tooth belt
# mis-cut) while staying threaded in the 5 mm nut. Min = reach the nut at the loosest gap + ~2 mm
# engagement; M4×35 gives 2.6 mm engaged at GAP and only ≤1.6 mm proud when fully closed. (M4×40 also
# works but over-reaches — a permanent 2.6–6.6 mm stub past the nut.)
_SCREW_MIN = (HALF_B_OUTER - HEAD_X) + 2.0               # 34.4  reach the nut at GAP + 2 mm engagement
SCREW_L  = 35.0                           # M4×35 (nearest stock ≥ min; see the take-up table)


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


def clamp_half() -> cq.Workplane:
    """ONE printed half — used for BOTH sides of the clamp (the +X half is this part turned 180°
    about Z; it is symmetric about its own y=0 plane, so its mirror across the gap IS that spin).
    On one half the M4 head bears on the −X (bed) face; on the other, the insert — used as a plain
    EXTERNAL nut resting on the Ø4.4 rim like the head, NOT heat-set — bears on the +X face. Four
    features, all keyed off the belt/lifter so the belt tunnel and lifter well share walls EXACTLY
    (no ledge — the old lip came from the tunnel being 0.2 mm narrower than the well):

      1. screw channel — a Ø4.4 cylinder on the screw axis, full length (bearing face → gap → nut).
      2. lifter well   — a LANE-wide slot to the floor, spanning the lifter GRIP but STOPPING SHORT
                         of the −X face: the _MRG-thick back-stop wall at GA0 boxes the lifter on
                         the outer side.
      3. belt tunnel   — the SAME LANE width and the SAME +X extent as the well, run OUT the −X face
                         so the belt threads in from that (outer) side.
      4. +X retention  — a 45°-supported ramp (`_ret_ramp`) unioned into the well's +X-bottom corner,
                         boxing the lifter on the inner side. The lifter clears it only lifted up into
                         the belt tunnel (belt out); once threaded, the belt caps the rise.

    Each lifter is boxed between the −X back-stop wall and the +X retention ramp; the screw's push is
    taken by the ramp on the head half and by the wall on the flipped nut half (see `place_b`)."""
    LANE   = WELL_W                                 # ONE Y width for BOTH cuts → their walls coincide (no lip)
    x1     = GA1                                    # lifter well +X end = the inner mouth (sized to the lifter)
    mouth  = x1 + 1.0                               # +X mouth (overshoot → cleanly open above the ramp)
    bx0    = HEAD_X - 1.0                            # belt runs OUT the −X face (overshoot → cleanly open)
    body = box_at(x1 - HEAD_X, BODY_W, TOP - BOT, x=(HEAD_X + x1) / 2, y=0.0, z=(TOP + BOT) / 2)
    body = body.cut(box_at(mouth - GA0, LANE, -WELL_FLR,                              # 2  lifter well
                           x=(GA0 + mouth) / 2, y=0.0, z=WELL_FLR / 2))               #    (−X back-stop wall at GA0)
    body = body.cut(box_at(mouth - bx0, LANE, CEIL_UZ,                                # 3  belt tunnel
                           x=(bx0 + mouth) / 2, y=0.0, z=CEIL_UZ / 2))                #    (open at −X)
    body = body.union(_ret_ramp(x1))                                                 # 4  +X retention ramp
    body = body.cut(cyl_x(SCR_CLR, mouth - HEAD_X, HEAD_X, Z_SCR))                    # 1  screw channel — cut
    return body                                                                      #    LAST, so it clears the ramp too


def place_b(part: cq.Workplane) -> cq.Workplane:
    """Move a half (in clamp_half's frame) into the +X (nut) position: spin 180° about Z, then
    shift by TB so its inner mouth sits GAP past half-A's. The half is y-symmetric, so this spin
    reproduces the opposing (mirror) half from the SAME SKU."""
    return part.rotate((0, 0, 0), (0, 0, 1), 180).translate((TB, 0.0, 0.0))


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
    # head/shank junction (the BEARING face) lands on HEAD_X and the head sits OUTSIDE half-A.
    scr = m4_button_screw(SCREW_L, head_d=HEAD_D, head_h=HEAD_H).rotate((0, 0, 0), (0, 1, 0), -90)
    return scr.translate((HEAD_X - HEAD_H, 0.0, Z_SCR))


def insert_dummy() -> cq.Workplane:
    # NOT heat-set: the insert sits OUTSIDE half-B's +X face on the Ø4.4 rim, acting as a plain nut
    return seated_insert(M4, (HALF_B_OUTER, 0.0, Z_SCR), (1.0, 0.0, 0.0))


def seated_lifter(bar, well_mid: float, locked: bool = True) -> cq.Workplane:
    """Place a bar in its well: flush on the screw crest (locked = LOCK_Z) or on the well floor
    (unlocked = WELL_FLR, ribs just clear of the belt)."""
    return bar.translate((well_mid, 0.0, (LOCK_Z if locked else WELL_FLR)))


# ── coupon: the printable set (2 identical halves + 2 identical lifters), spread in Y ────────
def tensioner_coupon() -> cq.Workplane:
    """TWO identical clamp_halves + TWO identical lifters, in PRINT poses. HALVES build +X: the
    belt tunnel and screw channel run along the build → clean walls + a round bore (a ceiling-
    bridge + sagging bore if built +Z), and the bearing face is the flat first layer. BARS build
    −Y→+Y (0.2 mm nozzle) so the ridge curves + concave seat land in the layer plane."""
    def _on_bed(w):
        return w.translate((0.0, 0.0, -w.val().BoundingBox().zmin))
    h1 = _on_bed(clamp_half().rotate((0, 0, 0), (0, 1, 0), -90)).translate((0.0, -14.0, 0.0))
    h2 = _on_bed(clamp_half().rotate((0, 0, 0), (0, 1, 0), -90)).translate((0.0, +2.0, 0.0))
    la = _on_bed(_lifter().rotate((0, 0, 0), (1, 0, 0), 90)).translate((22.0, -6.0, 0.0))
    lb = _on_bed(_lifter().rotate((0, 0, 0), (1, 0, 0), 90)).translate((22.0, +6.0, 0.0))
    return h1.union(h2).union(la).union(lb)


clamp_half_part = clamp_half()
