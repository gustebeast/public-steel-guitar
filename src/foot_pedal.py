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
bar. There is nothing to adjust about a pedal's position, so it is simply bar
geometry. That deleted three problems rather than solving them: the bar<->housing
mount joint, the scheme for retaining it, and the fact that the two parts' print
directions landed on a facing combination cadkit does not model. All three vanish
when the joint does. What still prints separately is what has to MOVE or be
assembled: this lever, the axle, the magnet and cap, the bearings, the cartridges
and the sensor board.

AND THE PRINT DIRECTIONS NOW AGREE, which is the point of the bar's -Y -> +Y flip
(user). The bar's bed is its -Y face; the housing's local -Z end is the bed the
knee lever already prints from; and the pose maps local +Z onto guitar +Y. So the
two bed planes coincide and the fused housing builds in exactly the orientation it
was designed in — no re-pass, no reorientation, nothing owed. The housing seats
FLUSH ON that face and stands ON the bar top, so the bar's own features — trough,
lid groove, splices, all below BAR_H — never contend with it.

AND IT FITS THE BAR'S Y EXACTLY (user: move the axles -Y into the 35.6 budget).
The printed housing spans BAR_Y0..BAR_Y1 dead on, flush plastic on BOTH faces —
an earlier round let it outreach the bar by 5.05 and stand proud of the +Y face,
which is what this replaces. The axle moved 5.05 -Y with it. That was paid for at
the time by giving up the sensor board's -Y retention — but the board has since
been trimmed of its dead strip (PCB_WZ 19 -> 16) and now ends at -9.00, inside
this housing's -10.15, so the retention came back for free. See HOUS_Z0/CRADLE_Z0.

WHERE THE HOUSINGS LAND. Five pedals on the 62.4 pitch span 277.6 (10.93 in) and
the cluster crosses a splice, so pedal_bar_a takes 2 housings and pedal_bar_b takes
3 (c takes none). THE SPLICES ARE DERIVED FROM THE STATIONS for exactly this reason
— see pedal_bar, where the layout now lives: a flat BAR_X0 + 215 put XS1 at -417.20,
inside the -413.20 pedal, cutting it in half. XS1 now sits in a pedal GAP at -426.60,
31.2 clear of the nearest pedal centre. Pieces come out 205.6 / 215.6 / 215.6 long,
293.1 / 305.0 / 187.4 cm3; bed lying on the -Y face 211.2 x 111.4, 221.2 x 111.4 and
215.6 x 89.0, all inside 255, print height 35.6. The first pad sits 62.4 — one whole
pitch, the empty slot 1 — off the keyhead leg's INBOARD FACE.

DEFERRED (this is the first round):
  * (RESOLVED — it was never needed) the REST STOP. The worry was that gravity pulls
    the pedal arm down while the spring pushes it up, so the rest angle would be a
    spring balance rather than a hard stop. Two things say otherwise. FIRST, the
    MAIN cartridge already IS the rest stop, here as on the knee lever: its follower
    touches the lobe with the piston at full extension, which is why knee_lever says
    "sets the rest angle -> no rest screw". The pedal inherits it because LOBE_RC_P
    was picked to give the identical 4.51 stroke, and the back-stop screw adjusts it.
    SECOND, the direction is favourable: gravity pulls the arm the SAME way the foot
    presses — into the spring — so it is resisted, not assisted. Measured: the lever
    is 23.0 cm3, ~29 g, CoM 41.4 from the axle, so gravity is 0.0117 N.m against the
    spring's 0.1452 N.m of preload torque. 12.5x margin. It cannot sag.
  * (RESOLVED) the board's -Z stop. The clip used to remove the cradle floor, leaving
    nothing to stop the board sliding out the open -Y end while pcb_shim pressed it
    that way. Trimming the board's dead 4.0 strip (PCB_WZ 19 -> 16) lifted its bottom
    edge to -9.00, inside this housing's -10.15, so there is a 1.15 floor again and
    the board no longer overhangs at all. The deferral went away rather than being
    solved — which is the second time shrinking the board fixed a mechanical problem.
  * (RESOLVED) pedal STATIONS. Fixed by the user and NOT copedent-dependent: five
    pedals on a PEDAL_PITCH slot scheme, slot 1 flush with the left (keyhead) leg's
    INBOARD FACE and left empty for breathing room, slots 2..6 filled. The layout
    lives in pedal_bar now, because the bar's splices have to dodge it. Nothing is
    deferred on this module.

WHAT IS SHARED AND WHAT BRANCHES (user). Shared: the whole feel system — the
cartridges are the SAME PRINTED SKUs across all three levers (cart_base,
cart_piston, guide_post, and the coils/screws/inserts/back-stops that
knee_lever.feel_dummies emits), plus the axle, bearings, magnet, board and cradle
builder. Branching: the pose, the lobe radius, the throw, the housing envelope,
and now the cradle's clip — this is the only lever whose housing has an external
Y budget to satisfy.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
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

# ── PEDAL STATIONS ───────────────────────────────────────────────────────────
# Owned by pedal_bar now (PB.PEDAL_X): the BAR is what gets cut into printable
# pieces, and a splice may not land on a pedal, so the bar has to know where they
# are to place its own splices. Keeping the layout here and the splices there is
# exactly how XS1 came to fall inside a pedal.
PEDAL_X  = PB.PEDAL_X
N_PEDALS = PB.N_PEDALS
assert PAD_WY == PB.PEDAL_W, (
    f"the pad is {PAD_WY} but the bar lays the stations out on {PB.PEDAL_W} — the "
    f"bar's spacing and the pedal's own footprint have to be the same number")


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


def lever_room() -> cq.Workplane:
    """The arm's swept envelope through the throw — the room BOTH the housing and
    the bar under it have to give up.

    Public because the bar needs it too. The housing alone is not enough: the arm
    swings down PAST the housing's floor and clips the bar's top -Y corner, which
    is how 111 mm3 survived after the sweep direction was fixed. The housing owns
    the room above BAR_H and the bar owns the room below it, and they are the same
    solid, so neither can drift from the other.
    """
    env = None
    for i in range(int(THROW_P) + 1):
        c = swing(_lever_envelope(), -float(i))
        env = c if env is None else env.union(c)
    return env


# ── housing envelope ─────────────────────────────────────────────────────────
HOUS_X0 = KL.HOUS_X0                       # cartridge back + back-stop engagement
HOUS_X1 = HUB_D / 2 + KL.HS_CLR + KL.HS_HOUS_WALL       # +7.8
HOUS_HW = KL.HOUS_HW                       # the sensor side sets Y — untouched, so the
                                           # axle / flange / magnet / cap / board all hold
HOUS_Z1 = (pplace(KL._hs_pocket(KL.HS_YC, -20.0, KL.HS_BACK_X)).val()
           .BoundingBox().zmax + KL.HS_HOUS_WALL)
# -Z: THE AXLE MOVES -Y (user). The printed housing is held to the bar's own Y
# width so its plastic is FLUSH on both faces — nothing proud of the +Y face, which
# is what the earlier "the depth is free, let it overhang" arrangement gave. The
# housing spans exactly BAR_Y0..BAR_Y1 and the axle lands Y_BUDGET - HOUS_Z1 = 10.15
# in from the player-side face instead of 15.20, i.e. 5.05 further -Y.
#
# What paid for it is the SENSOR BOARD's -Y retention (user): the board is 19 tall
# and sat 12 below the axle with a 3.2 floor under it, which is the whole 5.05. It
# now runs OUT THROUGH the housing's -Y face — _cradle drops the floor and opens the
# slot's bottom when the board overruns z_bot — and pokes 1.85 into open air on the
# player side, where there is nothing to hit. Printed plastic stays inside the
# budget; only the bought board leaves it.
#
# RETENTION CONSEQUENCE, stated because it is a real loss and not yet resolved: the
# floor was the board's -Z seat, and the pcb_shim presses DOWN onto it. With the
# floor gone the shim would push the board straight out the open bottom. The side
# grooves still hold Y and X over 17.15 of the board's 19, so it cannot fall out
# sideways, but the pedal needs a positive -Z stop before this is buildable.
Y_BUDGET = PB.BAR_Y1 - PB.BAR_Y0            # 35.6 — the bar's own width
CRADLE_Z0 = KL.PCB_Z0 - KL.CR_FLOOR_T       # the z_bot the cradle is BUILT
                                            # against (then clipped to HOUS_Z0).
                                            # Everything that asks knee_lever where
                                            # the board goes must pass THIS, not
                                            # HOUS_Z0 — board_flip keys off z_bot and
                                            # the two values disagree about it, so
                                            # mixing them would flip the demo board
                                            # inside an unflipped cradle.
HOUS_Z0 = HOUS_Z1 - Y_BUDGET

assert KL.PCB_Z0 >= HOUS_Z0, (
    f"the sensor board reaches z {KL.PCB_Z0:.2f}, below this housing's {HOUS_Z0:.2f} — it "
    f"would poke through the -Y face and the clip would take the cradle floor with it, "
    f"leaving nothing to stop the board sliding out while pcb_shim presses that way. "
    f"That was the state before PCB_WZ came down to {KL.PCB_WZ:.0f}; keep it fitting.")
# Unguarded until now, and the one direction nothing else checks: board_flip polices
# the board against a housing's Z WINDOW, but this housing is clipped to a Y budget
# that is tighter than the window its cradle is built against, so the board can fit
# board_flip and still overhang here.


def _housing() -> cq.Workplane:
    """The prism, derived from the lever and the raised cartridges, minus the
    lever room, the two house pockets and the drag recesses, plus the bearing
    seats, the sensor-side contact rib and the bar-mount tenon."""
    w = box_at(HOUS_X1 - HOUS_X0, 2 * HOUS_HW, HOUS_Z1 - HOUS_Z0,
               x=(HOUS_X0 + HOUS_X1) / 2, y=0.0, z=(HOUS_Z0 + HOUS_Z1) / 2)
    # LEVER ROOM = the lever's own swept envelope through the throw (LKV's finding:
    # a single planar polygon slopes above the arm's rest underside and fouls early)
    #
    # SWEPT THE WAY THE PEDAL ACTUALLY GOES, which is -theta. This used to run 0..+20
    # and the pedal presses 0..-20, so the room was carved out of the half of the arc
    # the arm never visits: the lever fouled its own housing from 2 deg of travel and
    # was 611 mm3 into it at full throw. Nothing caught it because the overlap gate
    # only ever sees the REST pose, and at rest it is clean. _to_guitar's docstring
    # has said "the FOOT has to drive -theta" all along — the sweep just did not read
    # it. Probed after the change, not assumed: 0 contact across 21 samples.
    w = w.cut(lever_room())
    w = KL.cut_axle_stack(w)       # bearing seats + contact rib + axle way
    w = KL.cut_feel_pockets(w, pplace, HOUS_X1)
    # SENSOR CRADLE, verbatim from knee_lever. It could not be cut before the print
    # flip: _cradle grows along local +Z and has no ceiling anywhere, which is only
    # true if local +Z is the build direction — and fused into the OLD bar, which
    # built guitar +Z, local +Z was a side wall. The flip makes local +Z guitar +Y,
    # the bar's build axis, so the helper's guarantee holds again and this is a
    # plain call. board_z picks the flip from the housing's own Z bounds.
    # SENSOR CRADLE — knee_lever's, TURNED OVER (user: rotate the pedal boards so
    # the connector faces DOWN into the bar, where the wiring can be hidden).
    #
    # This reverses an earlier call recorded here, and the reason it reverses is
    # that the cost changed. The old note rejected the flip because "the board runs
    # past HOUS_X1 = 7 — it would hang into the bar", and with a solid bar that was
    # simply a clash. Now the bar OPENS to receive it: board_bay_cutter() takes a
    # bay out of the bar top at every station, so the flipped board's lower half,
    # its connector and the mated plug all live INSIDE the beam, and the bay breaks
    # into the wiring trough — which is what actually hides the loom, and is also
    # how a hand reaches the plug (through the open lid channel, before the lid
    # goes on). Local +X is guitar -Z, so "past HOUS_X1" IS "down into the bar".
    #
    # The orientation is now REQUESTED, not inferred. Both ways up fit this housing
    # in Z, so the fit-based default would have picked as-drawn forever; flip=True
    # states the design intent and board_flip still checks it fits.
    w = KL._cradle(w, CRADLE_Z0, HOUS_Z1, x_max=CRADLE_X_MAX, flip=BOARD_FLIP)
    w = w.cut(box_at(200.0, 200.0, 100.0, x=(HOUS_X0 + HOUS_X1) / 2, y=0.0,
                     z=HOUS_Z0 - 50.0))
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
BAR_FACE_Y = PB.BAR_Y0                     # the player-side face = THE PRINT BED
BAR_TOP_Z  = PB.BAR_H + HOUS_X1            # axle datum: local +X is guitar -Z, so
                                           # putting the housing's local x = HOUS_X1
                                           # face at the bar top makes the housing sit
                                           # squarely ON the bar rather than sinking
                                           # into it — and everything the bar owns
                                           # (trough, lid groove, splices) lives below
                                           # BAR_H, so the two never contend.
# THE PLAYING DATUM. The user sizes this instrument's pedal geometry by how high the
# axle centre sits above the floor, and dimensions.PEDAL_BAR_H is solved backwards
# from it. That inversion is only safe while the other two terms hold, so check the
# height the model ACTUALLY builds rather than trusting the arithmetic: the foot's
# underside is FOOT_H below the bar's z0, and the axle is BAR_TOP_Z above it.
_AXLE_H = PB.LG.FOOT_H + BAR_TOP_Z
assert abs(_AXLE_H - D.PEDAL_AXLE_H) < 1e-9, (
    f"pedal axle sits {_AXLE_H:.2f} above the floor, not the {D.PEDAL_AXLE_H} datum "
    f"— re-solve dimensions.PEDAL_BAR_H (= PEDAL_AXLE_H - FOOT_H - HOUS_X1)")


# The housing SITS ON the bar's -Y face, it does not hang off it. The bar builds
# -Y -> +Y, so that face is the bed; the housing's own bed face (local z = HOUS_Z0,
# the side the knee lever already prints from) lands flush ON it. That is both the
# printable arrangement and the one that keeps the pedal as close to the player as
# the bar allows. Anchoring on HOUS_Z0 rather than HOUS_Z1 is the whole fix: it
# makes the seating independent of how deep the housing happens to be.
MOUNT_DY = BAR_FACE_Y - HOUS_Z0


# ── the board goes in UPSIDE DOWN, and the bar opens to take it ──────────────
BOARD_FLIP = True                   # user: connector DOWN into the bar (see _housing)
# Flipped, the board's far edge is at local +X = -PCB_X0, so the cradle is allowed
# out that far instead of stopping at the bar top. On the knee lever the rule is
# "nothing +X of the housing prism's face"; here +X is INTO the bar, and the bay
# below is what makes that legal.
CRADLE_X_MAX = -KL.PCB_X0                          # 25.0
# Everything that has to live inside the beam: the board's lower half, the mated
# connector and the plug's reach past the mouth.
BAY_X1 = -KL.CONN_MOUTH_X + KL.CONN_PLUG_RUN       # 30.65 — deepest hardware
BAY_CLR = 0.6                                      # printed clearance around the bay
# WHERE THE SHIM STOPS. The knee lever's shim runs to the housing ceiling and the
# chassis underside presses it. The pedal's ceiling IS the bar's +Y face — and that
# face carries the lid groove, so a full-height shim runs straight into the lid (the
# gate caught it on all five stations). It stops at the groove floor instead and the
# LID becomes the retainer: the same scheme, with the bar's lid standing in for the
# instrument's underside. Local z maps to guitar Y through MOUNT_DY.
SHIM_TOP = PB.LID_Y0 - MOUNT_DY                    # 21.45


def board_bay_cutter():
    """The pocket the bar gives up at each station, in the pedal's LOCAL frame.

    Sized from the placed hardware rather than typed: take everything the flipped
    board puts below the bar top — cradle, board, sensor parts, connector, plug —
    bound it, and open that box from the bar's top face downward. Because the box
    is derived, trimming the board or moving the connector re-sizes the bay instead
    of quietly clashing with it.

    It deliberately runs OUT through the top face (local -X, guitar +Z): the bay has
    to be open upward or the board could never be lowered in.
    """
    parts = [KL.sensor_board(), KL.sensor_connector()]
    parts += [s for _, s in KL.sensor_hardware()]
    parts = [p.rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 180.0) for p in parts]
    y0 = y1 = z0 = z1 = None
    for p in parts:
        b = p.val().BoundingBox()
        y0 = b.ymin if y0 is None else min(y0, b.ymin)
        y1 = b.ymax if y1 is None else max(y1, b.ymax)
        z0 = b.zmin if z0 is None else min(z0, b.zmin)
        z1 = b.zmax if z1 is None else max(z1, b.zmax)
    # widen to the CRADLE's own footprint — the webs and floor stand outside the
    # board in both local Y and Z, and they descend with it
    y0, y1 = min(y0, KL.CR_Y0) - BAY_CLR, max(y1, KL.CR_Y1) + BAY_CLR
    z0, z1 = z0 - KL.CR_WEB_T - BAY_CLR, z1 + KL.CR_WEB_T + BAY_CLR
    x0, x1 = HOUS_X1 - 20.0, BAY_X1 + BAY_CLR      # -20: run out through the top
    return box_at(x1 - x0, y1 - y0, z1 - z0,
                  x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(z0 + z1) / 2)


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

    All three stations fall between XS1 and XS2, so every housing lands in
    pedal_bar_b — the piece that is otherwise just trough.

    Called from build.py rather than pedal_bar, to keep the import one-way (this
    module reads pedal_bar for the bar's own faces) — the same dodge chassis uses
    for the motor plates and the tee cradles.

    ORDER MATTERS: the bay comes out of the BAR first, then the housing goes in.
    The housing's own cradle descends into that bay, so cutting the other way round
    takes the cradle straight back out — which is exactly what happened, and the
    tell was the piece falling into 3 and 4 disconnected solids as each far web was
    severed from its housing. A solid count is a good check on a cut you cannot
    see."""
    bay, room = board_bay_cutter(), lever_room()
    for x in PEDAL_X:
        if x0 <= x < x1:
            piece = (piece.cut(place(bay, x))
                          .cut(place(room, x))
                          .union(place(_housing(), x)))
    return piece


def cut_backstop_threads(piece, x0: float, x1: float):
    """The two FEMALE back-stop threads per pedal, cut into the fused bar piece.

    Separate from fuse_into_bar, and called AFTER the piece is healed, because the
    thread rules say threads are cut last and alone and a threaded part is never
    healed — and this housing is fused into a bar piece that heal()s. Cutting them
    inside _housing would have put a heal after the threads.

    They were missing entirely: knee_lever and knee_lever_vert both cut these, the
    pedal did not, so its back-stop screws had nothing to thread into and sat
    183 mm3 buried in solid bar. Invisible until the housings actually reached the
    assembly."""
    from cadkit.threads import threaded_rod
    for x in PEDAL_X:
        if not (x0 <= x < x1):
            continue
        for dy in (KL.MAIN_YC - KL.HS_YC, 0.0):
            nut = (threaded_rod(KL.HS_TH_MINOR, KL.HS_BSTOP_OD, KL.HS_TH_PITCH,
                                KL.HS_BSTOP_ENGAGE)
                   .rotate((0, 0, 0), (0, 1, 0), 90)
                   .translate((KL.HS_BACK_X + KL.HS_SETBACK,
                               KL.HS_YC + dy, KL.HS_Z)))
            piece = piece.cut(place(pplace(nut), x), clean=False)
    return piece


def demo_parts():
    """(name, solid) in GUITAR coordinates — the WHOLE control core at each of the
    three stations, not just the arm: bearings, magnet, sensor board, connector and
    shim on the axle, and both feel cartridges with their coils, tension screws,
    inserts and back-stops. The housing is not here because it is part of the bar
    now (fuse_into_bar).

    This used to emit the bare lever alone, which is why the pedal read as
    non-working in the assembly — there was a lever and an empty housing and
    nothing in between. Every part below is knee_lever's, placed through this
    module's own pose, so what you see IS the knee lever 1:1, only posed as a
    pedal. Nothing here is a pedal-specific copy."""
    out = []
    for i, x in enumerate(PEDAL_X):
        pre = f"pedal{i}"
        # lever frame -> guitar, and feel frame -> guitar, both bound to this station
        def _P(s, _x=x):
            return place(s, _x)

        def _F(s, _x=x):
            return place(pplace(s), _x)

        out.append((f"pedal_lever_{i}", _P(swing(_lever(), 0.0))))
        out += KL.axle_dummies(_P, pre, CRADLE_Z0, HOUS_Z1, flip=BOARD_FLIP,
                               shim_top=SHIM_TOP)
        out += KL.cart_dummies(_F, pre)
        out += KL.feel_dummies(_F, pre)
    return out


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
