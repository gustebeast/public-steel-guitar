"""FOOT PEDAL — the third member of the control-core family. PCTG.

INITIAL DESIGN (user asked for a best shot, reusing the knee lever as far as it
goes). Same job as knee_lever.py and knee_lever_vert.py: a pure POSITION SENSOR
(magnet on the axle, MT6701 reading it) with springs for feel, and the SAME
bought parts.

THE INSIGHT THAT MAKES THE REUSE WORK: a foot pedal is the horizontal knee lever
ROTATED, not a new machine. Look at what knee_lever already is in its own local
frame — axle along +Y, arm hanging -Z, lobe on the far side of the axle, piston
pushing along -X perpendicular to the arm/lobe line. That is exactly the pedal
the user described: "the spring contact in line with the pedal arm just on the
other side of the axle... the contact goes up and pushes into springs mounted
vertically along z". Same three-part relationship; only the MOUNT POSE differs.

So this module keeps knee_lever's LOCAL FRAME verbatim and changes only:

  * THE FEEL BLOCK RISES, exactly as the vertical lever's does, from -LOBE_RC to
    +LOBE_RC_P — because the contact has to be on the opposite side of the axle
    from the arm for a downward press to push the contact UP into the springs. A
    translation, NOT a mirror: the cartridge pocket's 45° gable is a printability
    constraint and has to stay on the same side whatever the lever does.

  * THE POSE. local +Y -> guitar +X (the pedal pivots about the instrument's
    length, so pedals line up along the bar), local -Z -> guitar -Y (the arm runs
    out toward the player, horizontal), local +X -> guitar +Z (so the cartridge,
    which pushes -X, pushes DOWN). That last one is the user's point about the
    springs: they stand VERTICALLY above the bar, in the envelope pedal_bar
    already reserves for them (PEDAL_ASSEMBLY_Z_HEIGHT).

  * THROW and the arm. 20° at a 90 mm arm gives 30.8 mm of pedal travel, which is
    a normal pedal-steel throw. LOBE_RC_P is then chosen the way the vertical
    lever chose its own: 13.2 makes LOBE_RC_P·sin(20°) equal the horizontal
    lever's 4.50 spring stroke, so the coils, preload, back-stop screws, drag
    pads and the HALF STOP all transfer with no re-tuning and no new part. The
    user asked for the half stop even though it is rare on a foot pedal; keeping
    the stroke identical is what makes it free.

  * FORCE follows from the same ratio. The knee lever runs ~1 N -> 8 N at a 100
    arm off LOBE_RC 9, i.e. ~11 -> 89 N at the lobe. Here that same lobe force
    acts at 13.2 against a 90 arm, so the PEDAL sees ~1.6 N -> 13 N (0.4 -> 3.0
    lb). That is in the normal pedal-steel band, and it tunes with the same
    back-stop screw.

THE HOUSING IS NOT A SEPARATE PART (user). It is fused straight into the pedal
bar. There is nothing to adjust about a pedal's position, and the bar already
prints -Z -> +Z, which is the orientation the housing wanted anyway — so it is
simply bar geometry. That deleted three problems rather than solving them: the
bar<->housing mount joint, the scheme for retaining it, and the fact that the two
parts' print directions landed on a facing combination cadkit does not model.
All three vanish when the joint does. What still prints separately is what has to
MOVE or be assembled: this lever, the axle, the magnet and cap, the bearings, the
cartridges and the sensor board.

A consequence worth keeping in view: all three stations fall between XS1 and XS2,
so every housing lands in pedal_bar_b. That piece goes from 136 cm3 to 293 and
from 36 mm deep to 77 — still inside the 255 bed (212 x 77 x 96), but it is now
the big print of the bar set, and adding a fourth pedal is what would break it.

DEFERRED (this is the first round):
  * the REST STOP. Gravity pulls the pedal arm down and the spring pushes it up;
    the rest angle wants a hard stop like LKV's, not a spring balance.
  * the sensor CRADLE is inherited from knee_lever, which draws it to stand up
    off a LOCAL +Z bed. Fused into the bar it builds along guitar +Z instead, so
    that bed is now a side wall — the cradle and the lever-room ceiling both want
    a printability pass in the bar's orientation before this is cut.
  * pedal STATIONS along X are placeholders until the copedent is fixed.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import knee_lever as KL
from . import pedal_bar as PB
from .helpers import box_at, cyl_y, heal


# ── throw, arm and the lobe that keeps the feel identical ────────────────────
THROW_P    = 20.0                   # pedal throw (deg, +theta about local +Y)
ENGAGE_P   = THROW_P / 2.0          # the half stop engages at half throw (10°)
LOBE_RC_P  = 13.2                   # so LOBE_RC_P·sin(THROW_P) == the horizontal
                                    # lever's 4.50 stroke -> the whole feel system
                                    # transfers untouched (same trick as LKV)
_STROKE    = LOBE_RC_P * math.sin(math.radians(THROW_P))
_FEEL_DZ_P = LOBE_RC_P + KL.LOBE_RC          # +22.2: how far the feel block rises

ARM_LEN_P  = 90.0                   # axle -> pedal-board centre
ARM_TX     = KL.ARM_TX              # arm depth in X = the bending axis (the foot
                                    # presses along -X), same section as the knee arm
HUB_D      = KL.HUB_D               # Ø10 hub on the axle — unchanged
LEVER_HW   = KL.LEVER_HW            # ±10 in Y — unchanged, so the whole bearing /
                                    # axle / magnet / board stack transfers verbatim
PAD_LZ     = 70.0                   # board length along local Z (= guitar Y, the
                                    # foot's own direction)
PAD_WY     = 28.0                   # board width along local Y (= guitar X, across)
PAD_T      = 4.0                    # board thickness
REC_X      = 3.5                    # follower recess depth into the leg's -X face
REC_Z      = 7.0                    # recess height (the follower's swept band)
LEG_TOP    = LOBE_RC_P + 3.0        # the leg reaches past the lobe station

PEDAL_X    = (-260.0, -313.8, -367.6)   # PLACEHOLDER stations along the bar (guitar X),
                                        # centred on the bar's mid-span at the classic
                                        # ~54 mm pedal pitch; the copedent fixes these


def swing(s, deg):
    """Rotate a lever solid through `deg` of throw about the axle (local +Y)."""
    return s.rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), deg)


def pplace(s):
    """knee_lever's feel-block placement, lifted so the contact lands at
    +LOBE_RC_P. A pure translation — never a mirror (see the docstring)."""
    return KL.feel_place(s).translate((0.0, 0.0, _FEEL_DZ_P))


# ── the lever ────────────────────────────────────────────────────────────────
def _lever() -> cq.Workplane:
    """Hub on the axle, a LEG rising +Z to carry the return lobe, an ARM running
    -Z to the player, and the pedal BOARD across its end. The lobe is a
    full-width ridge at LOBE_RC_P on the leg's -X face, reached through one local
    recess per follower — knee_lever's scheme unchanged."""
    hub = cyl_y(HUB_D, 2 * LEVER_HW, y0=-LEVER_HW)
    leg = box_at(ARM_TX, 2 * LEVER_HW, LEG_TOP, x=0.0, y=0.0, z=LEG_TOP / 2)
    arm = box_at(ARM_TX, 2 * LEVER_HW, ARM_LEN_P, x=0.0, y=0.0, z=-ARM_LEN_P / 2)
    body = hub.union(leg).union(arm)
    # follower recesses, one per cartridge lane, cut into the leg's -X face so the
    # lobe can protrude into them
    for yc in (KL.MAIN_YC, KL.HS_YC):
        body = body.cut(box_at(REC_X, KL.HS_CART_WY + 2 * KL.HS_CLR, REC_Z,
                               x=-ARM_TX / 2 + REC_X / 2, y=yc, z=LOBE_RC_P))
    body = body.union(cyl_y(2 * KL.LOBE_R, 2 * LEVER_HW, y0=-LEVER_HW)
                      .translate((0.0, 0.0, LOBE_RC_P)))
    # PEDAL BOARD: the foot presses -X, so the board's working face is its +X one.
    body = body.union(box_at(PAD_T, PAD_WY, PAD_LZ,
                             x=ARM_TX / 2 - PAD_T / 2, y=0.0,
                             z=-(ARM_LEN_P - PAD_LZ / 2 + 4.0)))
    body = KL.cut_axle_bore(body)
    return heal(body)


def _lever_envelope() -> cq.Workplane:
    """The lever grown by HS_CLR on every face — swept to make the lever room.
    Built from the same primitives as _lever, so a change to one shows as a
    change to the other."""
    c = KL.HS_CLR
    hub = cyl_y(HUB_D + 2 * c, 2 * (LEVER_HW + c), y0=-(LEVER_HW + c))
    leg = box_at(ARM_TX + 2 * c, 2 * (LEVER_HW + c), LEG_TOP + c,
                 x=0.0, y=0.0, z=(LEG_TOP + c) / 2)
    arm = box_at(ARM_TX + 2 * c, 2 * (LEVER_HW + c), ARM_LEN_P + 2.0,
                 x=0.0, y=0.0, z=-(ARM_LEN_P + 2.0) / 2)
    return heal(hub.union(leg).union(arm))


# ── housing envelope ─────────────────────────────────────────────────────────
HOUS_X0 = KL.HOUS_X0                       # cartridge back + back-stop engagement
HOUS_X1 = HUB_D / 2 + KL.HS_CLR + KL.HS_HOUS_WALL       # +7.8
HOUS_HW = KL.HOUS_HW                       # the sensor side sets Y — untouched, so the
                                           # axle / flange / magnet / cap / board all hold
HOUS_Z1 = (pplace(KL._hs_pocket(KL.HS_YC, -20.0, KL.HS_BACK_X)).val()
           .BoundingBox().zmax + KL.HS_HOUS_WALL)
# -Z: deep enough to clear the hub and let the arm swing out, and to floor the
# sensor board. Same two demands the vertical lever balances.
HOUS_Z0 = min(-(HUB_D / 2 + KL.HS_CLR + KL.HS_HOUS_WALL),
              KL.PCB_Z0 - KL.CR_FLOOR_T)


def _housing() -> cq.Workplane:
    """The prism, derived from the lever and the raised cartridges, minus the
    lever room, the two house pockets and the drag recesses, plus the bearing
    seats, the sensor-side contact rib and the bar-mount tenon."""
    w = box_at(HOUS_X1 - HOUS_X0, 2 * HOUS_HW, HOUS_Z1 - HOUS_Z0,
               x=(HOUS_X0 + HOUS_X1) / 2, y=0.0, z=(HOUS_Z0 + HOUS_Z1) / 2)
    # LEVER ROOM = the lever's own swept envelope through the throw (LKV's finding:
    # a single planar polygon slopes above the arm's rest underside and fouls early)
    _env = None
    for i in range(int(THROW_P) + 1):
        c = swing(_lever_envelope(), float(i))
        _env = c if _env is None else _env.union(c)
    w = w.cut(_env)
    w = KL.cut_axle_stack(w)       # bearing seats + contact rib + axle way
    w = KL.cut_feel_pockets(w, pplace, HOUS_X1)
    return heal(w)


# ── pose: local -> guitar ────────────────────────────────────────────────────
def _to_guitar(s):
    """local +Y -> guitar -X (the axle, along the bar), local +Z -> guitar +Y,
    local +X -> guitar -Z.

    That last mapping is forced, and a kinematics probe caught it: knee_lever's
    cartridge sits at local -X and pushes its piston in +X onto the lobe, so the
    lobe torque is +theta and the FOOT has to drive -theta, i.e. press along local
    +X. Pressing DOWN therefore means local +X -> guitar -Z, which is what puts
    the cartridges (local -X) ABOVE the lobe, pushing down — the springs standing
    vertically that the user asked for. The naive mapping had them hanging 77 mm
    BELOW the bar and the pedal working upside down.

    The extra 180° about guitar Y is also what keeps this a proper rotation: the
    mapping (+X->-Z, +Y->+X, +Z->+Y) has determinant -1 — a reflection, not a
    pose. Flipping the axle's sign too makes it a rotation again."""
    return (s.rotate((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), -90.0)
             .rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), -90.0)
             .rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 180.0))


# the bar's -Y face and top, in guitar coordinates (pedal_bar is drawn at
# absolute X/Y with local Z; build.py lifts it by ground + FOOT_H)
BAR_FACE_Y = PB.BAR_Y0                     # the player-side face the pedals hang on
BAR_TOP_Z  = PB.BAR_H                      # bar top (bar-local Z, = the lid groove floor
                                           # datum the lid then closes over)


# The housing hangs on the bar's PLAYER-SIDE face, flush against it: local +Z is
# guitar +Y, so its +Y-most feature (the sensor side, local z = HOUS_Z1) lands ON
# BAR_FACE_Y and everything else is -Y of the bar. Nothing intrudes into the bar's
# own footprint, which is what lets the trough and the lid groove stay untouched.
MOUNT_DY = BAR_FACE_Y - HOUS_Z1


def place(s, x):
    """Pose a local solid onto the bar at guitar station `x`."""
    return _to_guitar(s).translate((x, MOUNT_DY, BAR_TOP_Z))


def pedal_lever() -> cq.Workplane:
    return _lever()


def fuse_into_bar(piece, x0, x1):
    """Union every pedal housing whose station falls in [x0, x1) INTO a pedal-bar
    piece. The housing is not a separate part (user): there is nothing to adjust
    about a pedal's position, and the bar already prints -Z -> +Z, which is the
    orientation the housing wanted anyway. So it is simply bar geometry.

    That deletes a whole problem rather than solving it — no mount joint, no
    retention scheme, and no need for the bar<->housing facing combination that
    cadkit does not model. What still prints separately is what has to MOVE or be
    assembled: the lever, the axle, the magnet and cap, the bearings, the
    cartridges and the sensor board.

    Called from build.py rather than pedal_bar, to keep the import one-way (this
    module reads pedal_bar for the bar's own faces) — the same dodge chassis uses
    for the motor plates and the tee cradles."""
    for x in PEDAL_X:
        if x0 <= x < x1:
            piece = piece.union(place(_housing(), x))
    return piece


def demo_parts():
    """(name, solid) in GUITAR coordinates — the LEVERS only; the housings are
    part of the bar now (fuse_into_bar)."""
    return [(f"pedal_lever_{i}", place(swing(_lever(), 0.0), x))
            for i, x in enumerate(PEDAL_X)]


# ── sanity on the pose: three facts, each of which the naive mapping got wrong ──
_p = _to_guitar(box_at(1.0, 20.0, 1.0)).val().BoundingBox()
assert _p.xlen > _p.ylen and _p.xlen > _p.zlen, (
    "the pedal pose must put the axle (local Y) along the guitar's X")
_a = _to_guitar(box_at(1.0, 1.0, 20.0).translate((0.0, 0.0, -10.0))).val().BoundingBox()
assert _a.ymax <= 0.1, "the pedal arm (local -Z) must run out toward the player (-Y)"
_s = _to_guitar(box_at(1.0, 1.0, 1.0).translate((-10.0, 0.0, 0.0))).val().BoundingBox()
assert _s.zmin >= 0.0, (
    "the cartridges (local -X) must stand ABOVE the bar — if they land -Z the "
    "pedal is upside down and the springs would assist the foot, not resist it")
# the reserved envelope pedal_bar keeps clear above the bar for exactly this
assert (HOUS_X1 - HOUS_X0) <= PB.PEDAL_ASSEMBLY_Z_HEIGHT + 5.0, (
    f"the pedal stack is {HOUS_X1 - HOUS_X0:.1f} tall against pedal_bar's reserved "
    f"{PB.PEDAL_ASSEMBLY_Z_HEIGHT:.1f} — raise the reservation or shorten the cartridge")
