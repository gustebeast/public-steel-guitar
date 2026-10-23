"""VERTICAL knee lever (LKV) — the up-push variant of the control core. PCTG.

Same job as knee_lever.py (a pure POSITION SENSOR: magnet on the axle, MT6701
reading it, springs for feel) and the same bought parts, but the player's knee
pushes UP instead of sideways.

WORLD FRAME, about the axle. Everything in this module is written in the
instrument's own axes, origin on the axle; src.build only translates it to its
station. The AXLE runs along X (the instrument's length); the ARM leaves the
housing through its -Y face and reaches out at the player; the throw lifts it, a
rotation about +X (swing). The sensor side is +X.

THE LEVER CORE IS SHARED. The axle stack (bearings, magnet, board, cradle), the
two feel cartridges and the follower recesses are ONE design, drawn in
knee_lever's own frame (axle along Y, arm +X) and placed into each housing of the
family. Every horizontal station takes it as drawn; this lever takes it with its
axle along X (core, the placement every shared cutter and dummy here goes
through -- the same `place` argument cut_feel_pockets has always taken).
Everything that is this lever's own -- the arm, the housing prism, its tenons,
its lever room, install stroke, roof closure and knee relief -- is drawn here,
natively.

WHAT IS DIFFERENT FROM THE HORIZONTAL LEVER, and it is less than it looks:

  * THE ARM MOVES, NOT THE AXLE. The arm, instead of hanging -Z and swinging
    laterally, extends HORIZONTALLY (-Y) and swings up in Z, about the same axle.

  * THE FEEL BLOCK MOVES UP, IT DOES NOT MIRROR. For a piston pushing toward the
    arm to resist an UPWARD push on the arm, the contact has to sit ABOVE the
    axle: the piston's force at height h gives a torque that drives the arm back
    down. So the lobe and both cartridges translate from -LOBE_RC to +LOBE_RC_V.
    NOT a Z mirror — the cartridge pocket's 45° gable has to stay on TOP whatever
    the lever does, because that is a printability constraint, not a lever one.
    Mirroring would put a flat ceiling over both pockets.

  * THE AXLE SITS LOWER. That is forced, not chosen: the cartridges have to stay
    under the instrument, so putting them above the axle pushes the axle down by
    exactly as much. It is also what buys the arm its room to swing up.

  * THROW IS SHORTER (20° vs 30°, user: the vertical is the space-constrained
    one) — but the FEEL IS UNCHANGED, because the spring stroke is
    LOBE_RC·sin(throw) and LOBE_RC is free. Raising it 9.0 -> 13.2 puts the
    stroke back at 4.51 against the horizontal lever's 4.50, so the springs,
    preload, back-stops, drag pads and half-stop all transfer with no re-tuning
    and no new part. The web behind the lobe recess scales with LOBE_RC too, so
    this is the SAFE direction for it (~6.8 of web where 9.0 gave 2.6).

  * TENONS SLIDE ALONG Y, like every lever's, into the same rib mortises; with
    the axle along X they lie ALONG the housing's length here, so the stations
    space out across it in X (the rib comb) and only a few fit — this lever
    mounts on FEWER but LONGER tenons than LKL's four short rails.

Everything else is imported from knee_lever and used unchanged: the cartridges,
their pistons, die springs, tension and position screws; the axle, magnet,
magnet cap, bearings and the MT6701 board.

DEFERRED (this round is the basic geometry, per the user):
  * the REST STOP. Gravity and the springs both pull this arm down, so unlike
    LKL there is no spring-defined rest angle — it needs a hard stop to land on.
  * (DONE 2026-09-21) the follower recesses are knee_lever's swept tongue envelopes.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import knee_lever as KL
from .motor_bank import BED_Z as _BED_Z     # the chassis print-bed datum (= chassis.Z_BOT;
                                            # imported from motor_bank to stay out of the
                                            # chassis import cycle)
from .helpers import box_at, cyl_x, heal
from cadkit.lazy import lazy


# ── the shared lever core, placed with its axle along X ──────────────────────
def core(s):
    """A solid of the SHARED lever core (knee_lever's frame: axle along +Y, arm +X), placed
    into this lever: its axle on +X, its arm side on -Y. Shapes and Workplanes alike."""
    return s.rotate((0, 0, 0), (0, 0, 1), -90)


def core_pt(p):
    """A POINT or direction of the shared core (knee_lever's frame), placed as core places
    solids."""
    x, y, z = p
    return (y + 0.0, -x + 0.0, z + 0.0)


# ── throw + the lobe that keeps the feel identical ───────────────────────────
THROW_V     = 20.0                  # user: the vertical may have less than the horizontal
ENGAGE_V    = THROW_V / 2.0         # half-stop still engages at half throw (10°)
LOBE_RC_V   = 13.2                  # chosen so LOBE_RC_V·sin(THROW_V) == the horizontal
                                    # lever's 4.50 stroke -> the feel system transfers
_STROKE     = LOBE_RC_V * math.sin(math.radians(THROW_V))
_FEEL_DZ_V  = LOBE_RC_V + KL.LOBE_RC        # +22.2: how far the whole feel block rises

# ── the lever ────────────────────────────────────────────────────────────────
# The two outer stations sit as far apart as the -X wall was widened to allow, rounded DOWN to
# a whole number of bottom-grid pitches so both land in slots. On the old 22.35 comb that span
# was exactly one pitch; on the 8.8 grid it is two (17.6). Taking one pitch instead would put
# the inboard stem within 0.05 of the housing centre, straight over the arm slot -- the
# roof-height assert below catches that, which is how this was found.
TEN_SPAN    = KL.RIB_PITCH / 2.0    # the span the -X wall was built to host (22.35)
TEN_PITCH   = KL.D.LEVER_PITCH * int(TEN_SPAN // KL.D.LEVER_PITCH)      # 17.6
ARM_LEN_V   = 80.0                  # axle -> paddle end (user; was 50). 80 gives 27.4 of
                                    # paddle lift at 20° instead of 17.1 — a bigger knee
                                    # rise, and a LIGHTER one: the feel spring makes a
                                    # fixed torque, so the force the knee feels scales
                                    # as 1/arm. 50 -> 80 is x0.625, which brings the
                                    # vertical lever's ~2->16 N down to ~1.25->10 N,
                                    # i.e. closer to the horizontal lever's own 1->8 N
                                    # than it has ever been. Longer also means the arm
                                    # reaches further -Y toward the player, so where it
                                    # SITS has to follow — build._vkl_mount_y measures
                                    # the arm off the solid and re-centres it on the
                                    # shared contact plane automatically.
ARM_TZ      = 8.0                   # arm thickness in Z (it is the arm's bending depth now)
LEG_TOP     = LOBE_RC_V + 4 * KL.D.BEAD     # leg reaches 3.2 past the lobe station
HUB_D       = KL.HUB_D              # Ø10 hub on the axle — unchanged
LEVER_HW    = KL.LEVER_HW           # ±12 along the axle -- LKL's, so every bearing/sensor
                                    # station on the axle holds
# The arm SAGS past rest (gravity and both springs pull it down) until its rest stop, which is
# still deferred -- so the recess covers REST_SAG_V of travel that way with the follower at rest.
REST_SAG_V  = 10.0
# HALF-STOP SETBACK for THIS lever. LKL's HS_SETBACK (1.863) was solved for its 9.5 lobe
# radius and a 15° engagement; on this lever's 13.2 radius it engaged at 8.32° instead of
# ENGAGE_V. Re-solved the same way -- a solid-contact bisection of kv_lever against the
# half-stop piston -- for first contact at ENGAGE_V (2026-09-21): +0.373. It is only where the
# cartridge PARKS on its position screw (the same part, the same pocket), and it leaves that
# screw 1.23 / 1.97 of its range either side.
HS_SETBACK_V = KL.HS_SETBACK + 0.373


def _lever() -> cq.Workplane:
    """The L. Hub on the axle, a LEG rising +Z to carry the return lobe, and the
    ARM running -Y to the knee. The lobe is a full-width ridge at LOBE_RC_V, on
    the leg's +Y face, reached through one local recess per follower — same
    scheme as the horizontal lever (the ridge is a single primitive buried in
    solid material except where the pistons need to touch it)."""
    hub = cyl_x(HUB_D, 2 * LEVER_HW, x0=-LEVER_HW)
    leg = box_at(2 * LEVER_HW, KL.ARM_TX, LEG_TOP, x=0.0, y=0.0, z=LEG_TOP / 2)
    arm = box_at(2 * LEVER_HW, ARM_LEN_V, ARM_TZ, x=0.0, y=-ARM_LEN_V / 2, z=0.0)
    body = hub.union(leg).union(arm)
    # follower recesses: knee_lever's SWEPT tongue envelope, one per lane, so the leg keeps its
    # material right behind the lobe (they were plain notches sized to the CARTRIDGE -- 14.8
    # wide each on a 24 leg once the Ø10 cartridges arrived -- which left the lobe standing on
    # a sliver). In the core's own terms this lever's working throw is -a about its axle,
    # hence sense=-1.
    for lane in (KL.MAIN_YC, KL.HS_YC):
        body = body.cut(core(KL.recess_swept(lane, LOBE_RC_V, THROW_V, LOBE_RC_V + KL.FOLL_DZ,
                                             sense=-1, rest_span=REST_SAG_V)))
    body = body.union(cyl_x(2 * KL.LOBE_R, 2 * LEVER_HW, x0=-LEVER_HW, z=LOBE_RC_V))
    body = KL.cut_axle_bore(body, place=core)
    return heal(body)


# ── housing envelope, derived the same way LKL's is ──────────────────────────
def vplace(s):
    """knee_lever's feel-block placement, lifted so the contact lands at
    +LOBE_RC_V, then placed with the core. The lift is a pure translation — see
    the module docstring on why this must not be a mirror."""
    return core(KL.feel_place(s).translate((0.0, 0.0, _FEEL_DZ_V)))


# -Y IS THE ARM'S FACE: the arm exits through it, so it stands far enough out for the hub to
# pass -- or for the bearing seat and its wall, whichever is bigger; same rule as knee_lever's
# housing. With the Ø16 688ZZ the race wins (11.25); sizing off the hub alone let it poke 0.8
# out of the face.
ARM_FACE = max(HUB_D / 2 + KL.HS_CLR + KL.HS_HOUS_WALL,
               KL.BRG_SEAT_D / 2 + KL.BRG_WALL_X)
HOUS_Y0 = -ARM_FACE
HOUS_Y1 = -KL.HOUS_X0               # +Y: the cartridges' backs + their rear (KL.cut_feel_rear)
# X IS ASYMMETRIC, and only one side moved. +X is the SENSOR side: KL.HOUS_HW is the
# datum the axle flange, the magnet, the cap and the whole board cradle cascade off,
# so touching it would lengthen the axle and grow the magnet's cantilever off the
# bearing. -X carries nothing but wall, so that is where the room for the OUTER TENON
# PAIR gets bought (user asked what it would cost): the rib comb is 23 and a tenon is
# 6 wide, so two stations need 23 + 6 + margin of X. At 0.5 of margin either side of
# each tenon that is 30.0 of span against the 27.8 a symmetric housing has — 2.2, ALL
# of it on -X. (Bare minimum, tenons flush with the faces, is 1.2.)
HOUS_X1 = KL.HOUS_HW                # +13.9 — the sensor side, untouched on purpose
TEN_MARGIN = KL.D.MIN_WALL          # 0.8 (one bead) of material outboard of each tenon's edge
HOUS_X0 = -max((TEN_PITCH + 2 * KL._JHW + 2 * TEN_MARGIN) - HOUS_X1,
               # ...and never inside the -X cartridge pocket's own wall. The tenon sum
               # alone went UNDER it once the Ø10 die-spring cartridges spread the
               # pockets to ±8.45 (2026-09-21): the -X pocket would have broken out.
               abs(KL.MAIN_YC) + KL.hs_pocket_hw() + KL.HS_HOUS_WALL,
               # ...and the -X BEARING, which sits flush with the face (KL.BRG_Y0 + BRG_W =
               # KL.HOUS_HW): the tenon/pocket terms alone left it 0.75 proud once the
               # lever went to 25.6 (2026-09-21)
               KL.BRG_Y0 + KL.BRG_W)
# +Z comes from the RAISED POCKET's own measured extent, not from the piston: the
# cartridge block stands 6.6 above its centre where the piston stands 3.0, and using
# the piston's figure put the housing lid 3.6 BELOW the cartridge it is meant to
# enclose. Overlap probes cannot see that — a part poking out into free air
# intersects nothing — it took a bounding-box check.
HOUS_Z1 = (vplace(KL._hs_pocket(KL.HS_YC, -20.0, KL.HS_BACK_X)).val()
           .BoundingBox().zmax + KL.HS_HOUS_WALL)
# -Z is the deeper of two demands: clearing the hub/arm at rest, and giving the
# SENSOR BOARD its floor. The board is one fixed design (user), and WHICH WAY UP it
# goes is not a free choice about fit alone — it also decides WHICH END THE CAN PLUG
# EXITS, because the only orientation freedom is a 180 deg turn about the axle axis
# and that swaps front-for-back together with top-for-bottom. The user wants the plug
# to face +Y, the housing's back end, which is where the board AS DRAWN puts it.
# So this floor is sized for the AS-DRAWN board (bottom edge PCB_Z0), not the
# turned-over one (-PCB_Z1). That is the entire price of the connector side: 5.0 mm
# of extra housing depth, -9.80 -> -14.80. The hub alone would allow -7.80.
HOUS_Z0 = min(-(HUB_D / 2 + KL.HS_CLR + KL.HS_HOUS_WALL),
              KL.PCB_Z0 - KL.CR_FLOOR_T)               # -14.80
assert not KL.board_flip(HOUS_Z0, HOUS_Z1), (
    "LKV wants the board AS DRAWN so its CAN plug exits +Y, but this housing only "
    "fits it turned over — the floor must reach PCB_Z0 - CR_FLOOR_T")
# PRINT ORIENTATION (the record, declared once per part) -- the housing goes on the bed
# on its FLOOR and builds +Z. It is written here rather than transcribed into a checker
# because it is a design fact: every 45 in the lever family is drawn self-supporting
# AGAINST THIS, the keeper's foot is sized "on the bed" at HOUS_Z0, and the buttress
# "grows up from the print bed". tools.check_ceilings reads it by name (src.leg_stack's
# SLEEVE_UP and friends set the pattern).
PRINT_UP = (0.0, 0.0, 1.0)

AXLE_DROP = HOUS_Z1 - KL.HOUS_Z1    # how much lower the axle sits than LKL's (+11.0..15.2)

# ── mount tenons: slide along Y, stations along X ────────────────────────────
TEN_Y0, TEN_Y1 = HOUS_Y0, HOUS_Y1 - 2.0     # the slide span available
# The stations' phase in X is free: it is set by where src.build puts the lever along the
# instrument, since the rib comb runs in X. So the housing does not chase the ribs; the
# station does.
# CENTRED on the housing, not pushed against the sensor wall. With the spacing free, hard
# against that wall was the way to get them furthest apart; with the spacing locked to the grid
# the phase is the only freedom left, and centring is what maximises the distance from the
# nearest stem to the ARM SLOT -- which is what sets how high the slot wall may go (the assert
# in _housing). Anchored at the wall, the inboard stem came 3.5 from the centre and the roof
# had to drop under the arm's reach.
# THREE, with the MIDDLE ONE ON THE LEVER'S CENTRELINE (user, 2026-09-18). The outer pair is
# TEN_PITCH apart, so the housing's own width (HOUS_X0) does not move, and the middle station
# is the grid station between them, free room that would otherwise be left empty.
# It is INTERRUPTED over the arm slot's Y span, by construction and not by special-casing: the
# slot is cut after the tenons, so the same sweep that clears the arm trims this one, exactly
# as LKL's over-the-lever station is trimmed by its lever room. What survives is the +Y run,
# about 60 of it, which is where this lever's engagement lives anyway.
TEN_X = (-TEN_PITCH / 2.0, 0.0, TEN_PITCH / 2.0)


def _top_tenon(tx):
    """One fused mount tenon at x=tx: the joint (slides +X, head +Z) turned to slide -Y,
    its mouth end at the housing's back. Its root slab and root chamfer are clipped to the
    housing's X, so an outer station's stays inside; the stem and flare above are left
    whole (KL.clip_tenon_root)."""
    t = (KL._lever_joint(TEN_Y1 - TEN_Y0).tenon(root=KL.TEN_ROOT)
         .rotate((0, 0, 0), (0, 0, 1), -90)                   # slide axis X -> -Y (head stays +Z)
         .translate((tx, TEN_Y1, HOUS_Z1)))
    yc, ly = (HOUS_Y0 + HOUS_Y1) / 2, HOUS_Y1 - HOUS_Y0
    return KL.clip_tenon_root(t, TEN_Y1 - TEN_Y0, HOUS_Z1,
                              (HOUS_X0, HOUS_X1, yc - 2 * ly, yc + 2 * ly))


def _lever_envelope() -> cq.Workplane:
    """The lever grown by HS_CLR on every face — the thing that gets swept to make
    the lever room. Built from the same primitives as _lever rather than offset
    from it, so a change to one is visibly a change to the other."""
    c = KL.HS_CLR
    hub = cyl_x(HUB_D + 2 * c, 2 * (LEVER_HW + c), x0=-(LEVER_HW + c))
    leg = box_at(2 * (LEVER_HW + c), KL.ARM_TX + 2 * c, LEG_TOP + c,
                 x=0.0, y=0.0, z=(LEG_TOP + c) / 2)
    arm = box_at(2 * (LEVER_HW + c), ARM_LEN_V + 2.0, ARM_TZ + 2 * c,
                 x=0.0, y=-(ARM_LEN_V + 2.0) / 2, z=0.0)
    return heal(hub.union(leg).union(arm))


# HOW FAR THE LEVER CAN ACTUALLY GO -- which is NOT how far it is driven (user: "LKV
# will have shorter travel, we just need to ensure it isn't blocked until the lever tip
# touches the chassis. The chassis sets the limit"). THROW_V is the driven range; the room
# has to be carved to the PHYSICAL one, or the housing becomes the stop instead of the
# instrument.
#
# THE CHASSIS IS HOUS_Z1. This housing's top is mounted FLUSH with the instrument's
# underside -- that is what MOUNT_Z is -- so "the lever tip touches the chassis" is
# "the lever reaches z HOUS_Z1", and it needs no chassis import to say so. The tip
# starts HOUS_Z1 - the envelope's own zmax below it, which measures 14.8 at the lever's
# leg and 27.6 out at the tip the user read off the model; either way the angle falls out
# of the same sweep rather than being typed.
#
# IT IS ABOUT 20 DEG, NOT 63 (user: "the lever will never sweep that far, it will hit the
# chassis well before that"). 63 is what a probe reads with the lever posed 99 mm too far
# -Y, where the tip is outboard of the chassis's -Y edge and nothing stops it until 62.6.
# Measured through build's own station the gap closes at 20-21, which is THROW_V, as a
# sensibly-designed lever should be. It is derived here, where the housing's own datum
# already says it, so no pose can get between the sweep and the answer.
def _throw_max():
    """Sweep until the lever reaches the instrument's underside; that angle is the limit."""
    for i in range(1, 181):
        if swing(_lever_envelope(), float(i)).val().BoundingBox().zmax >= HOUS_Z1:
            return float(i)
    raise AssertionError("the vertical lever never reaches the chassis")


# ...assigned below, once swing() exists -- _housing() is the first thing that reads it


def _housing() -> cq.Workplane:
    """The prism, derived from the lever + the raised cartridges exactly as LKL's
    is, minus the lever room, the two house pockets and the drag recesses, plus
    the bearing seats, the sensor cradle and the mount tenons."""
    w = box_at(HOUS_X1 - HOUS_X0, HOUS_Y1 - HOUS_Y0, HOUS_Z1 - HOUS_Z0,
               x=(HOUS_X0 + HOUS_X1) / 2, y=(HOUS_Y0 + HOUS_Y1) / 2,
               z=(HOUS_Z0 + HOUS_Z1) / 2)
    for tx in TEN_X:
        w = w.union(_top_tenon(tx))
    # LEVER ROOM = the lever's OWN SWEPT ENVELOPE, as a union of clearance copies
    # through the throw. A single planar polygon from the hub to the arm tip is the
    # obvious shortcut and it is wrong in a way worth recording: its lower edge runs
    # from the hub straight out to the tip's FULL-THROW position, so it slopes up
    # above the arm's own rest underside and the lever fouls from 3° on. Sweeping
    # the real shape cannot make that mistake. 1° steps leave scallops well under
    # one nozzle; a closed-form polygon is the tidy-up, not a correctness fix.
    # ...AND IT SWEEPS TO THE CHASSIS, not to THROW_V (user, 2026-09-25: "LKV will have
    # shorter travel, we just need to ensure it isn't blocked until the lever tip touches
    # the chassis. The chassis sets the limit"). THROW_V is how far the lever is DRIVEN;
    # it is not how far it can go, and carving only the driven range would leave the housing
    # stopping the arm 40 deg before anything physical does. The arm rises until it meets
    # the instrument's underside, which is HOUS_Z1.
    _hw = LEVER_HW + KL.HS_CLR
    # THE MOUNT GETS THE LAST WORD. The arm leaves through a slot in the -Y face whose roof
    # may not rise past a tenon stem's root, and the arm's reach inside that span climbs
    # steeply once it is past ~44 deg: 17.95 at 44, 26.03 at 56, 33.73 at 63.
    _stem = min(abs(tx) - KL._J_STEM / 2 for tx in TEN_X if abs(tx) > 1e-9)
    _y0 = HOUS_Y0 - 1.0
    _y1 = KL.ARM_TX / 2 + KL.HS_CLR
    _span = box_at(2 * _hw + 2.0, _y1 - _y0, 400.0, x=0.0, y=(_y0 + _y1) / 2, z=0.0)
    # THE SLOT IS SIZED BY THE LEVER'S OWN SECTION, not by where the lever GETS TO (user,
    # 2026-09-25: "I'm confused why the lever would need to be that far +z during
    # installation. It seems like it could slide in purely along Y and not need to go up in
    # Z beyond where it is in the assembly"). Exactly right, and measured: the lever's
    # section in this span is z -6.80..16.40 and it stays that for the whole withdrawal --
    # a constant section, because sliding a part out does not move it in Z.
    #
    # Sized against the swept envelope's reach instead, the wall would stand at 26.35: ten
    # mm of opening nothing passes through, with a 45 deg roof adding another 13.2 above THAT.
    # And it would be self-defeating, because the roof then has to stay under a mount tenon's
    # root, which caps the room's sweep at 56 deg. Proven by A/B, not argued: with no slot
    # at all the lever still clears the housing at every angle to 63, and WITH it the lever
    # slides straight out -Y with zero contact. The envelope carries the sweep; the slot
    # carries the INSTALL STROKE. They are different things.
    _zw = _lever_envelope().val().intersect(_span.val()).BoundingBox().zmax
    _root = HOUS_Z1 - KL.TEN_ROOT - max(0.0, _hw - _stem)
    assert _zw <= _root + 1e-6, (
        "the slot's roof (%.2f) would undercut a mount tenon's root (%.2f)" % (_zw, _root))
    _env = None
    for i in range(int(THROW_MAX) + 1):
        c = swing(_lever_envelope(), float(i))
        _env = c if _env is None else _env.union(c)
    # ...CAPPED AT THE HOUSING TOP (user, 2026-09-10). The top is flush with the instrument's
    # underside, so the arm cannot swing above it: past ~15 deg it meets the body, not air.
    # Sweeping the full envelope up through it would hollow out the inner halves of the
    # mount tenons and leave the rib mortises half empty.
    _env = _env.intersect(box_at(400.0, 400.0, HOUS_Z1 - (HOUS_Z0 - 50.0),
                                 x=0.0, y=0.0, z=(HOUS_Z1 + HOUS_Z0 - 50.0) / 2))
    w = w.cut(_env)
    # THE INSTALL ROOM = THE MOTION THAT INSTALLS IT, swept (user, 2026-09-25: "let's redo
    # the arm exit slot based on the room we actually need for installation. That would mean
    # moving the lever up just enough to clear the small indent it has in the floor below it
    # and then sweeping it out towards -y").
    #
    # A house-profile slot running the full height is a guess at the motion rather than the
    # motion, and both of its faults were found by the user in the viewer, invisible to any
    # check here:
    #   its height comes from the swept envelope's REACH, ten mm above anything that
    #     passes through it, and since the roof then has to duck a mount tenon's root it
    #     caps the lever's own sweep six degrees short of the chassis;
    #   its inboard end is a vertical wall standing on a 17 mm void -- 44.47 mm2 of face
    #     with nothing under it, and everything above it unsupported.
    # A cut shaped like the motion cannot have either: it is bounded by the lever's own
    # section, and it ENDS at the lever's rest pose, which is inside the room already.
    #
    # THE LIFT IS THE SEAT'S OWN DEPTH, read off the envelope rather than typed: the room
    # follows the lever, so the dip the hub sits in IS the envelope's own dip, 2.78 here.
    _at = lambda y: (_lever_envelope().val()
                     .intersect(box_at(400.0, 1.0, 400.0, x=0.0, y=y, z=0.0).val())
                     .BoundingBox().zmin)
    _lift = _at(0.0) * -1 + _at(-(HUB_D / 2 + 2.0))   # seat bottom -> the floor outside it
    _draw = _lever_envelope().val().BoundingBox().ymax - (HOUS_Y0 - 2.0)
    _ins = None
    for dz in [j * 0.5 for j in range(0, int(_lift / 0.5) + 2)]:
        c = _lever_envelope().translate((0.0, 0.0, min(dz, _lift)))
        _ins = c if _ins is None else _ins.union(c)
    _top = _lever_envelope().translate((0.0, 0.0, _lift))
    for dy in [j * 2.0 for j in range(1, int(_draw / 2.0) + 2)]:
        _ins = _ins.union(_top.translate((0.0, -min(dy, _draw), 0.0)))
    # ...AND IT GETS A ROOF OF ITS OWN. The install stroke is the lever's own section
    # swept, so its top is the lever's FLAT top, and a flat-topped hole is a ceiling: 7.2
    # mm of it here, 38.7 mm2, the biggest on this part. helpers.corbel_close would trim
    # that back to a 45, but only to within one of its courses -- it credits a course
    # with a whole step of 45 growth at the course's own floor, and this jump happens AT
    # a floor, so a lip exactly one step wide survives. 0.82 at a bead, 0.43 at half a
    # bead, and never zero (user, 2026-09-29, twice: "there's an overhang here", "still a
    # small overhang"). Chasing it with a finer step is chasing a limit.
    #
    # A hole in this project is not left flat-topped in the first place -- every pocket
    # here is a house profile. So the CUTTER gets the gable, drafted up off its own top
    # face at 45 until it closes to a ridge, and then there is nothing for the closure to
    # find. It costs no strength: the material it takes is the material that could not
    # have been printed anyway.
    _ins = _ins.union(_gable_up(_ins))
    w = w.cut(_ins)
    w = KL.cut_axle_stack(w, place=core)          # bearing seats + the axle way
    # the pockets run out through the arm's face: ARM_FACE is that face in the core's terms
    w = KL.cut_feel_pockets(w, vplace, ARM_FACE)
    # SENSOR CRADLE — knee_lever's, parameterised by this housing's Z extents
    # (user: draw it once and reuse it). Everything about the sensor stack is
    # identical between the levers except how tall the board is, and that falls
    # out of z_bot/z_top.
    w = KL._cradle(w, HOUS_Z0, HOUS_Z1, x_max=ARM_FACE, place=core)
    # HUNG, not stood on the bed: this housing is 46.6 deep, so a post from its floor
    # would run the whole depth of the lever and put its coil 18 below the horizontal
    # levers'. Hung at KL.KEEP_DROP on a 45 deg buttress, every coil is at one height.
    # (The keeper is the core's: its cheek is this housing's sensor face, its back this
    # housing's back, in the core's own coordinates.)
    w = w.union(core(KL.cable_keeper(HOUS_X1, HOUS_Z0, -HOUS_Y1, HOUS_Z1, hung=True)))
    # NO SECOND POST HERE (user, 2026-09-23: "you added an extra winding post to the
    # LKV but it's unnecessary"). Right -- this lever already has a column, and the
    # arriving cable can turn round THAT. A turn post belongs to an approach round the
    # front, into the arm's sweep; the cable comes round the +Y back end instead, where
    # the keeper is already sitting and does the job.
    # ...AND THE SAME 45 DEG KNEE RELIEF LKL HAS (user, 2026-09-25: "I would recommend
    # adding the same 45 cut we added to the LKL yesterday to the LKV so we can get a bit
    # more space for the knee"). Same construction, same constant: a plane TANGENT to a
    # circle of bearing seat + KNEE_BRG_WALL about the axle, so the material that takes the
    # spring's force and the knee's counter-force is sized by the bearing rather than by a
    # printing minimum. This housing is 46.6 deep, so the corner it gives back is bigger
    # than LKL's.
    w = w.cut(_knee_relief())
    # ...AND THE 45 DEG CLOSURE OVER BOTH VOIDS, last, on the finished solid -- as clean cuts
    # (user, 2026-10-16), not the layer sweep. KL.roof_close stays as the TOOL that found
    # them: it took 739 mm3 here, these take 726 in two prisms and a wedge.
    return heal(w.cut(roof_cut(_env, _ins)))


def roof_cut(env, ins) -> cq.Workplane:
    """The closure over this housing's voids, as a few clean cuts (see KL.roof_cut for the rule:
    a point stays if ANY wall reaches it at 45, so the cut sits under every wall's surface at
    once). Here the walls are simpler than LKL's, and every number is read off the voids:

      * OVER THE INSTALL STROKE. Its top is a flat (the lever's own top, lifted) that the
        middle mount tenon crosses. Held from +Y at 45 off the flat's +Y edge, and from each
        side at 45 off the cartridge pockets' gable flats (their outer edge, where the pocket's
        outer wall carries them). The -Y face is the arm's exit: nothing there.
      * UNDER THE WEB BETWEEN THE POCKETS, over the arm's sweep. The sweep's +Y flank leaves
        the wall at its +Y-most point and climbs at ~24 deg; the web over it is held only from
        that corner, so it is trimmed to 45 off it, as far as the install stroke's +Y wall."""
    ib = ins.val().BoundingBox()
    zr = ib.zmax                                               # the stroke's top flat...
    yr = max(f.BoundingBox().ymax for f in ins.val().Faces()   # ...and its +Y edge
             if f.geomType() == "PLANE" and f.normalAt(f.Center()).z > 0.99
             and abs(f.Center().z - zr) < 1e-6)
    pk = vplace(KL._hs_pocket(KL.HS_YC, -20.0, KL.HS_BACK_X)).val().BoundingBox().zmax
    xw = KL.HS_YC + KL.ROOF_FLAT / 2.0                         # the gable flat's outer edge
    ye, top = HOUS_Y0 - 1.0, HOUS_Z1 + 2 * KL._J_HOST_W       # past the tenons' tips
    lo = zr - 1.0
    a = cq.Workplane("YZ").polyline([(yr + 1.0, lo), (ye, lo), (ye, top),
                                     (yr - (top - zr), top)]).close().extrude(xw + 1.0, both=True)
    b = (cq.Workplane("XZ").polyline([(-xw, lo), (xw, lo), (xw, pk), (0.0, pk + xw), (-xw, pk)])
         .close().extrude(yr - ye + 3.0).translate((0, yr + 2.0, 0)))
    cut = a.val().intersect(b.val())
    # the web: its corner is the sweep's +Y-most point in the web's plane (x = 0)
    sec = env.val().intersect(box_at(0.02, 400.0, 400.0, x=0.0, y=0.0, z=0.0).val())
    pts = [e.positionAt(i / 200.0) for e in sec.Edges() for i in range(201)]
    c = max(pts, key=lambda q: q.y)
    yc, zc = c.y, c.z
    yw = ib.ymax                                               # the install stroke's +Y wall
    xi = KL.HS_YC - KL.hs_pocket_hw()                          # the web: between the pockets
    assert yc > yw and xi > 0.0, "the sweep's corner / the web are not where this assumes"
    wedge = (cq.Workplane("YZ").polyline([(yc, zc), (yw, zc), (yw, zc + (yc - yw))]).close()
             .extrude(xi + 0.5, both=True))
    return cq.Workplane("XY").add(cut.fuse(wedge.val()))


def _gable_up(v):
    """A 45 deg gable standing on every flat top face of a cutter, to its own ridge.

    cadkit's house profile said as an operation instead of as a drawn section: OCC drafts
    the wire, so the roof is exact planes and arcs whatever shape the face is. The height
    is found by trying -- a draft that would close the face before it gets there is
    refused by the kernel rather than clamped, and the footprint's inradius is not
    something the bounding box knows."""
    # HEALED FIRST. The install stroke is a union of forty-odd translated copies, so its
    # roof arrives as forty-odd coplanar shards; drafting each one and fusing the results
    # hands back a NULL shape. Merged into whole faces there is one roof to gable.
    v = KL.heal(v)
    out = []
    for f in v.val().Faces():
        if f.Area() < 1.0:                # a shard the merge could not absorb
            continue
        try:
            n = f.normalAt()
        except Exception:
            continue
        if n.z < 0.999:
            continue
        b = f.BoundingBox()
        h = min(b.xlen, b.ylen) / 2.0
        while h > KL.D.BEAD / 4:
            g = None
            try:
                g = cq.Solid.extrudeLinear(f.outerWire(), list(f.innerWires()),
                                           cq.Vector(0, 0, h), taper=45)
                # ...and it must FUSE with the cutter it stands on. A draft run right to
                # the footprint's closing height can come back "valid" and still be
                # degenerate at its ridge, and every boolean after it returns a null shape;
                # tried here, on the spot, it is just one more refusal.
                ok = (g.isValid() and g.Volume() > 1e-6
                      and v.val().fuse(g).Volume() > v.val().Volume())
            except Exception:
                ok = False                # ...and a REFUSAL is not the only failure:
            if ok:                        #   OCC also hands back a null shape, which
                out.append(g)             #   only raises later, inside the union
                break
            h *= 0.5
    if not out:
        return cq.Workplane("XY")
    got = out[0]
    for g in out[1:]:                     # one at a time, checked: a fuse can come back
        try:                              #   null, and it only shows up much later
            f = got.fuse(g)
            if f.isValid() and f.Volume() >= got.Volume() - 1e-6:
                got = f
        except Exception:
            pass
    return cq.Workplane("XY").add(got)


def _knee_relief():
    """The 45 deg corner off the bottom of the arm's face, across this housing's own width.

    BOUNDED TO THE HOUSING, like LKL's, so the sensor cradle beyond the +X face keeps the
    board's grooves; and guarded around the board itself for the same reason as there --
    the arithmetic is about one pose of a board that can be installed turned over."""
    z0 = HOUS_Z0 - 1.0
    yo = HOUS_Y0 - 1.0
    # ...AND IT RUNS OVER THE CRADLE, as LKL's does (user, 2026-09-25: "the 45 cut doesn't
    # cut the PCB like you have it for the LKL"). Bounded at the sensor face it would stop at
    # the cheek and leave the cradle's corner standing proud of the relief on the very side
    # the knee comes from. The board is guarded instead -- by ITS OWN installed height here,
    # not LKL's, which is what KL.board_guard exists to get right.
    x0, x1 = HOUS_X0, KL.CR_Y1 + KL.D.MIN_WALL_2P
    pts = [(-(z0 + KL.KNEE_CHAM_C), z0), (yo, z0), (yo, -yo - KL.KNEE_CHAM_C)]
    f = cq.Face.makeFromWires(cq.Wire.makePolygon(
        [cq.Vector(x0, y, z) for y, z in pts] + [cq.Vector(x0, pts[0][0], pts[0][1])]))
    wedge = cq.Workplane("XY").add(cq.Solid.extrudeLinear(f, cq.Vector(x1 - x0, 0, 0)))
    return wedge.cut(core(KL.board_guard(HOUS_Z0, HOUS_Z1)))


def swing(s, throw=0.0):
    """Pose a lever solid at a given throw, about the axle. +throw lifts the arm."""
    return s.rotate((0, 0, 0), (1, 0, 0), -throw)


THROW_MAX = _throw_max()

kv_lever = lazy(_lever)                 # built when first used: see knee_lever
kv_housing = lazy(_housing)
# the board's SHIM: the core's one shim design, cut to this housing's slack. It is a plate in
# the board's plane, and the board stands across the axle, so here it lies on its -X face.
kv_pcb_shim = lazy(lambda: core(KL.pcb_shim(HOUS_Z0, HOUS_Z1)))
SHIM_UP = core_pt(KL.SHIM_UP)
assert SHIM_UP == (1.0, 0.0, 0.0), SHIM_UP


def demo_parts():
    """Bought/printed dummies, placed in this lever's frame, for the assembly."""
    out = KL.axle_dummies(core, "kv", HOUS_Z0, HOUS_Z1)
    out += KL.cart_dummies(vplace, "kv", hs_setback=HS_SETBACK_V)
    # the springs, tension screws, inserts and back-stops too -- without them the lever
    # reads as cartridge bodies with no feel system inside them
    out += KL.feel_dummies(vplace, "kv", hs_setback=HS_SETBACK_V)
    return out


# ── the board's plug and cable keeper, for the harness ───────────────────────
def plug_pin(way):
    """KL.plug_pin for this housing's board, in this lever's frame."""
    return core_pt(KL.plug_pin(way, HOUS_Z0, HOUS_Z1))


def keeper_point():
    """KL.keeper_point for this housing's keeper (see _housing), in this lever's frame."""
    return core_pt(KL.keeper_point(HOUS_Z0, -HOUS_Y1, HOUS_X1, HOUS_Z1))


PLUG_DIR = core_pt((-1.0, 0.0, 0.0))        # the plug's wires leave along the core's -X: +Y
KEEPER_AXIS = core_pt(KL.keeper_axis())
PIN_AXIS = core_pt(KL.pin_axis())
CHEEK_AXIS = core_pt(KL.cheek_axis())       # the connector cheek's outward normal: +X


if __name__ == "__main__":
    print(f"THROW_V   {THROW_V}   LOBE_RC_V {LOBE_RC_V}   stroke {_STROKE:.2f} "
          f"(horizontal: {KL.LOBE_RC * math.sin(math.radians(KL.THROW)):.2f})")
    print(f"housing   x {HOUS_X0:.2f}..{HOUS_X1:.2f}  y {HOUS_Y0:.2f}..{HOUS_Y1:.2f}  "
          f"z {HOUS_Z0:.2f}..{HOUS_Z1:.2f}")
    print(f"axle sits {AXLE_DROP:.2f} lower than the horizontal lever's")
    print(f"tenons at x {TEN_X}, sliding y {TEN_Y0:.2f}..{TEN_Y1:.2f}")


# ── STATION ──────────────────────────────────────────────────────────────────
# Z is the design's: the housing top lands flush on the chassis underside and the tenons
# rise into the rib mortises from the same plane -- which is why chassis.py needs NO
# feature of its own for this lever: rib_mortise is already an octagon slot of this width
# running along Y in every rib, so it accepts these tenons as they are. What has to line
# up is X: MOUNT_X lands the stations on real ribs.
_Z_BOT = _BED_Z                     # -74.95 chassis underside (= chassis.Z_BOT, via
                                    # motor_bank.BED_Z — the spelled -75.15 it replaces had
                                    # gone stale when the bed datum snapped to the grid)
MOUNT_X = -455.0 - TEN_X[1]         # a rib-comb X: the stations land on ribs
MOUNT_Y = -130.0                    # axle 3.75 inboard of the -Y rail, so the housing
                                    # runs inboard under the body and the arm reaches out
MOUNT_Z = _Z_BOT - HOUS_Z1 - KL.MORT_SEAT   # housing top c under the chassis underside (seat at c)
MOUNT_POSE = (MOUNT_X, MOUNT_Y, MOUNT_Z)


def place(s):
    """This lever at its default station: a translation, nothing else."""
    return s.translate(MOUNT_POSE)


# PRINT ORIENTATION (the record, declared once per part) -- the ARM is the horizontal
# lever's arm on this lever's axle, so it prints the way that one does: lying on the face
# its axle bore leaves through, building ALONG the axle, so cadkit's bore along it is a
# plain cylinder. The axle runs along X here: the arm lies on its -X face.
LEVER_UP = core_pt(KL.LEVER_UP)
assert LEVER_UP == (1.0, 0.0, 0.0), LEVER_UP


# ── the boards must be ONE design (user) ────────────────────────────────────
def _assert_one_board():
    """Both levers must put the SAME board in — installed differently, drawn the
    same. They already share sensor_board(), so this is a guard against a future
    round quietly re-parameterising the outline for one of them: it compares the
    solids that actually reach the assembly, by volume and by sorted bounding-box
    dimensions, which a pure rotation leaves untouched and any redraw would not."""
    a = dict(KL.demo_parts())["kl_pcb"]
    b = dict(demo_parts())["kv_pcb"]
    for nm, s in (("kl", a), ("kv", b)):
        if len(s.val().Solids()) != 1:
            raise AssertionError(f"{nm}_pcb is not one solid")
    va = sum(x.Volume() for x in a.val().Solids())
    vb = sum(x.Volume() for x in b.val().Solids())
    if abs(va - vb) > 1e-6:
        raise AssertionError(f"the two levers draw DIFFERENT boards: {va:.3f} vs {vb:.3f} mm3")
    da = sorted(round(v, 6) for v in (a.val().BoundingBox().xlen,
                                      a.val().BoundingBox().ylen,
                                      a.val().BoundingBox().zlen))
    db = sorted(round(v, 6) for v in (b.val().BoundingBox().xlen,
                                      b.val().BoundingBox().ylen,
                                      b.val().BoundingBox().zlen))
    if da != db:
        raise AssertionError(f"the two levers draw DIFFERENT boards: {da} vs {db}")


_assert_one_board()
