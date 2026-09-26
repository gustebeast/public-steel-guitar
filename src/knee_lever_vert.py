"""VERTICAL knee lever (LKV) — the up-push variant of the control core. PCTG.

Same job as knee_lever.py (a pure POSITION SENSOR: magnet on the axle, MT6701
reading it, springs for feel) and the same bought parts, but the player's knee
pushes UP instead of sideways.

WHAT ACTUALLY CHANGES, and it is less than it looks:

  * THE ARM MOVES, NOT THE AXLE. In this part's LOCAL frame the axle still runs
    along +Y and the throw is still a rotation about it. The arm, instead of
    hanging -Z and swinging laterally, extends +X HORIZONTALLY and swings up in
    Z. What makes the whole thing a "vertical" lever is the MOUNT: the assembly
    is posed rotated 90° about Z, so local +Y lands on the guitar's X and local
    +X points -Y at the player. That is the sense in which the axis runs along
    the instrument's length.

  * THE FEEL BLOCK MOVES UP, IT DOES NOT MIRROR. For a +X-pushing piston to
    resist an UPWARD push on a +X arm, the contact has to sit ABOVE the axle:
    force +X at height h gives +Y torque, which drives the arm back down. So the
    lobe and both cartridges translate from -LOBE_RC to +LOBE_RC_V. NOT a Z
    mirror — the cartridge pocket's 45° gable has to stay on TOP whatever the
    lever does, because that is a printability constraint, not a lever one.
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

  * TENONS RUN ALONG LOCAL X. cadkit's octagon slides along its extrude axis, so
    where the horizontal lever rotates it 90° to slide in Y, this one uses it
    as-is. After the mount's 90° pose that lands the slide on the guitar's Y,
    which is what the rib mortises accept. The stations then space out along
    local Y (= the guitar's X, the 23 mm rib comb), and only ~2 fit across the
    housing's 27.8 — so this lever mounts on FEWER but LONGER tenons than LKL's
    four short rails.

Everything else is imported from knee_lever and used unchanged: the cartridges,
their pistons, die springs, tension and position screws; the axle, magnet,
magnet cap, bearings and the MT6701 board.

DEFERRED (this round is the basic geometry, per the user):
  * the REST STOP. Gravity and the springs both pull this arm down, so unlike
    LKL there is no spring-defined rest angle — it needs a hard stop to land on.
  * the global MOUNT POSE (which bay, and how far inboard).
  * (DONE 2026-09-21) the follower recesses are knee_lever's swept tongue envelopes.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import knee_lever as KL
from .motor_bank import BED_Z as _BED_Z     # the chassis print-bed datum (= chassis.Z_BOT;
                                            # imported from motor_bank to stay out of the
                                            # chassis import cycle)
from .helpers import box_at, cyl_y, heal, pose_dir


# ── throw + the lobe that keeps the feel identical ───────────────────────────
THROW_V     = 20.0                  # user: the vertical may have less than the horizontal
ENGAGE_V    = THROW_V / 2.0         # half-stop still engages at half throw (10°)
LOBE_RC_V   = 13.2                  # chosen so LOBE_RC_V·sin(THROW_V) == the horizontal
                                    # lever's 4.50 stroke -> the feel system transfers
_STROKE     = LOBE_RC_V * math.sin(math.radians(THROW_V))
_FEEL_DZ_V  = LOBE_RC_V + KL.LOBE_RC        # +22.2: how far the whole feel block rises

# ── the lever ────────────────────────────────────────────────────────────────
# The two stations sit as far apart as the -Y wall was widened to allow, rounded DOWN to a
# whole number of bottom-grid pitches so both land in slots. On the old 22.35 comb that span was
# exactly one pitch; on the 8.8 grid it is two (17.6). Taking one pitch instead would put the
# inboard stem within 0.05 of the housing centre, straight over the arm slot -- the roof-height
# assert below catches that, which is how this was found.
TEN_SPAN    = KL.RIB_PITCH / 2.0    # the span the -Y wall was built to host (22.35)
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
LEVER_HW    = KL.LEVER_HW           # ±12 in Y -- LKL's, so every bearing/sensor Y holds
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
    ARM running +X to the knee. The lobe is a full-width ridge at LOBE_RC_V, on
    the leg's -X face, reached through one local recess per follower — same
    scheme as the horizontal lever (the ridge is a single primitive buried in
    solid material except where the pistons need to touch it)."""
    hub = cyl_y(HUB_D, 2 * LEVER_HW, y0=-LEVER_HW)
    leg = box_at(KL.ARM_TX, 2 * LEVER_HW, LEG_TOP, x=0.0, y=0.0, z=LEG_TOP / 2)
    arm = box_at(ARM_LEN_V, 2 * LEVER_HW, ARM_TZ, x=ARM_LEN_V / 2, y=0.0, z=0.0)
    body = hub.union(leg).union(arm)
    # follower recesses: knee_lever's SWEPT tongue envelope, one per lane, so the leg keeps its
    # material right behind the lobe (they were plain notches sized to the CARTRIDGE -- 14.8
    # wide each on a 24 leg once the Ø10 cartridges arrived -- which left the lobe standing on
    # a sliver). This lever throws the arm UP, i.e. -a about +Y, hence sense=-1.
    for yc in (KL.MAIN_YC, KL.HS_YC):
        body = body.cut(KL.recess_swept(yc, LOBE_RC_V, THROW_V, LOBE_RC_V + KL.FOLL_DZ,
                                        sense=-1, rest_span=REST_SAG_V))
    body = body.union(cyl_y(2 * KL.LOBE_R, 2 * LEVER_HW, y0=-LEVER_HW)
                      .translate((0.0, 0.0, LOBE_RC_V)))
    body = KL.cut_axle_bore(body)
    return heal(body)


# ── housing envelope, derived the same way LKL's is ──────────────────────────
def vplace(s):
    """knee_lever's feel-block placement, lifted so the contact lands at
    +LOBE_RC_V. A pure translation — see the module docstring on why this must
    not be a mirror."""
    return KL.feel_place(s).translate((0.0, 0.0, _FEEL_DZ_V))


HOUS_X0 = KL.HOUS_X0                # cartridge back + the rear (KL.cut_feel_rear) — unchanged
HOUS_X1 = max(HUB_D / 2 + KL.HS_CLR + KL.HS_HOUS_WALL,  # the arm exits through here...
              KL.BRG_SEAT_D / 2 + KL.BRG_WALL_X)        # ...or the seat + its +X wall, whichever is
              # bigger — same rule as knee_lever's housing. With the Ø16 688ZZ the race wins
              # (11.25); sizing off the hub alone let it poke 0.8 out of the +X face.
# Y IS ASYMMETRIC, and only one side moved. +Y is the SENSOR side: HOUS_HW is the
# datum the contact rib, the axle flange, the magnet, the cap and the whole board
# cradle cascade off, so touching it would lengthen the axle and grow the magnet's
# cantilever off the bearing. -Y carries nothing but wall, so that is where the room
# for a SECOND TENON gets bought (user asked what it would cost): the rib comb is
# 23 and a tenon is 6 wide, so two stations need 23 + 6 + margin of Y. At 0.5 of
# margin either side of each tenon that is 30.0 of span against the 27.8 we had —
# 2.2, ALL of it on -Y. (Bare minimum, tenons flush with the faces, is 1.2.)
HOUS_HW_P = KL.HOUS_HW              # +13.9 — the sensor side, untouched on purpose
TEN_MARGIN = KL.D.MIN_WALL          # 0.8 (one bead) of material outboard of each tenon's edge
HOUS_HW_N = max((TEN_PITCH + 2 * KL._JHW + 2 * TEN_MARGIN) - HOUS_HW_P,
                # ...and never inside the -Y cartridge pocket's own wall. The tenon sum
                # alone went UNDER it once the Ø10 die-spring cartridges spread the
                # pockets to ±8.45 (2026-09-21): the -Y pocket would have broken out.
                abs(KL.MAIN_YC) + KL.hs_pocket_hw() + KL.HS_HOUS_WALL,
                # ...and the -Y BEARING, which sits flush with the face (KL.BRG_Y0 + BRG_W =
                # KL.HOUS_HW): the tenon/pocket terms alone left it 0.75 proud once the
                # lever went to 25.6 (2026-09-21)
                KL.BRG_Y0 + KL.BRG_W)
HOUS_HW = HOUS_HW_P                 # the sensor-side alias the Y stack reads
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
# and that swaps left-for-right together with top-for-bottom. The user wants the plug
# to face +Y in the guitar frame; local X maps to guitar -Y here (place() turns -90
# about Z), so +Y means the connector at local -X, which is the board AS DRAWN.
# So this floor is sized for the AS-DRAWN board (bottom edge PCB_Z0), not the
# turned-over one (-PCB_Z1). That is the entire price of the connector side: 5.0 mm
# of extra housing depth, -9.80 -> -14.80. The hub alone would allow -7.80.
HOUS_Z0 = min(-(HUB_D / 2 + KL.HS_CLR + KL.HS_HOUS_WALL),
              KL.PCB_Z0 - KL.CR_FLOOR_T)               # -14.80
assert not KL.board_flip(HOUS_Z0, HOUS_Z1), (
    "LKV wants the board AS DRAWN so its CAN plug exits +Y, but this housing only "
    "fits it turned over — the floor must reach PCB_Z0 - CR_FLOOR_T")
# PRINT ORIENTATION (the record, declared once per part) -- the housing goes on the bed
# on its FLOOR and builds +Z, in world coordinates. It is written here rather than
# transcribed into a checker because it is a design fact: every 45 in the horizontal lever is
# drawn self-supporting AGAINST THIS, the keeper's foot is sized "on the bed" at
# HOUS_Z0, and the buttress "grows up from the print bed". A part that is ever
# re-oriented brings this declaration along with it, and tools.check_ceilings reads it
# by name (src.leg_stack's SLEEVE_UP and friends set the pattern).
PRINT_UP = (0.0, 0.0, 1.0)

AXLE_DROP = HOUS_Z1 - KL.HOUS_Z1    # how much lower the axle sits than LKL's (+11.0..15.2)

# ── mount tenons: slide along LOCAL X (see the docstring) ────────────────────
TEN_X0, TEN_X1 = HOUS_X0 + 2.0, HOUS_X1     # the slide span available
# Two stations, pushed as far apart as the span allows. Their absolute Y is free —
# the phase is set by where we pose the lever in the guitar's X, since after the
# mount's 90° rotation the rib comb runs along local Y. So the housing does not
# chase the ribs; the pose does.
# CENTRED on the housing, not pushed against the sensor wall. With the spacing free, hard
# against that wall was the way to get them furthest apart; with the spacing locked to the grid
# the phase is the only freedom left, and centring is what maximises the distance from the
# nearest stem to the ARM SLOT -- which is what sets how high the slot wall may go (the assert
# in _housing). Anchored at the wall, the inboard stem came 3.5 from the centre and the roof
# had to drop under the arm's reach.
# THREE, with the MIDDLE ONE ON THE LEVER'S CENTRELINE (user, 2026-09-18). The outer pair is
# where it was -- TEN_PITCH apart, so the housing's own width (HOUS_HW_N) does not move -- and
# the middle station is the grid station between them, free room that was being left empty.
# It is INTERRUPTED over the arm slot's X span, by construction and not by special-casing: the
# slot is cut after the tenons, so the same sweep that clears the arm trims this one, exactly
# as LKL's over-the-lever station is trimmed by its lever room. What survives is the -X run,
# about 60 of it, which is where this lever's engagement lives anyway.
TEN_Y = (-TEN_PITCH / 2.0, 0.0, TEN_PITCH / 2.0)


def _top_tenon(ty):
    """One fused octagon tenon at local y=ty. cadkit's octagon already slides
    along +X with its roof +Z, which is exactly what this lever wants — no
    rotation, unlike LKL's."""
    return (KL._lever_joint(TEN_X1 - TEN_X0).tenon(root=KL.TEN_ROOT)
            .translate((TEN_X0, ty, HOUS_Z1)))


def _lever_envelope() -> cq.Workplane:
    """The lever grown by HS_CLR on every face — the thing that gets swept to make
    the lever room. Built from the same primitives as _lever rather than offset
    from it, so a change to one is visibly a change to the other."""
    c = KL.HS_CLR
    hub = cyl_y(HUB_D + 2 * c, 2 * (LEVER_HW + c), y0=-(LEVER_HW + c))
    leg = box_at(KL.ARM_TX + 2 * c, 2 * (LEVER_HW + c), LEG_TOP + c,
                 x=0.0, y=0.0, z=(LEG_TOP + c) / 2)
    arm = box_at(ARM_LEN_V + 2.0, 2 * (LEVER_HW + c), ARM_TZ + 2 * c,
                 x=(ARM_LEN_V + 2.0) / 2, y=0.0, z=0.0)
    return heal(hub.union(leg).union(arm))


# HOW FAR THE ARM CAN ACTUALLY GO -- which is NOT how far it is driven (user, 2026-09-25:
# "LKV will have shorter travel, we just need to ensure it isn't blocked until the lever
# tip touches the chassis. The chassis sets the limit"). THROW_V is the driven range; the
# room has to be carved to the PHYSICAL one, or the housing becomes the stop instead of
# the instrument. Carved to THROW_V it was: the arm fouled its own housing from 22 deg,
# forty degrees before anything real.
#
# MEASURED, NOT DERIVED, and that is a weakness worth stating. The contact is between the
# POSED arm and the chassis, and this module cannot see either -- src.build owns the pose
# and importing it here would be a cycle. Swept in the assembly, the tip closes its 15.2 mm
# of clearance and touches at 62.6 deg. The local HOUS_Z1 plane is NOT a stand-in for it:
# the arm reaches out to x 80, far outboard of the housing, and out there it passes that
# plane at 20 deg with nothing above it. Believing otherwise is what made the first attempt
# at this stop at 21.
THROW_MAX = 63.0                    # deg, +throw: the arm tip on the chassis underside


def _housing() -> cq.Workplane:
    """The prism, derived from the lever + the raised cartridges exactly as LKL's
    is, minus the lever room, the two house pockets and the drag recesses, plus
    the bearing seats, the sensor-side contact rib and the mount tenons."""
    w = box_at(HOUS_X1 - HOUS_X0, HOUS_HW_P + HOUS_HW_N, HOUS_Z1 - HOUS_Z0,
               x=(HOUS_X0 + HOUS_X1) / 2, y=(HOUS_HW_P - HOUS_HW_N) / 2,
               z=(HOUS_Z0 + HOUS_Z1) / 2)
    for ty in TEN_Y:
        w = w.union(_top_tenon(ty))
    # LEVER ROOM = the lever's OWN SWEPT ENVELOPE, as a union of clearance copies
    # through the throw. The first attempt was one planar polygon from the hub to
    # the arm tip, and it was wrong in a way worth recording: its lower edge ran
    # from the hub straight out to the tip's FULL-THROW position, so it sloped up
    # above the arm's own rest underside and the lever fouled from 3° on. Sweeping
    # the real shape cannot make that mistake. 1° steps leave scallops well under
    # one nozzle; a closed-form polygon is the tidy-up, not a correctness fix.
    # ...AND IT SWEEPS TO THE CHASSIS, not to THROW_V (user, 2026-09-25: "LKV will have
    # shorter travel, we just need to ensure it isn't blocked until the lever tip touches
    # the chassis. The chassis sets the limit"). THROW_V is how far the lever is DRIVEN;
    # it is not how far it can go, and carving only the driven range left the housing
    # stopping the arm 40 deg before anything physical did. The arm rises until it meets
    # the instrument's underside, which is HOUS_Z1 -- measured at 62.6 deg, where the tip
    # closes the 15.2 mm it starts with.
    _hw = LEVER_HW + KL.HS_CLR
    # THE MOUNT GETS THE LAST WORD. The arm leaves through a slot in the +X face whose roof
    # may not rise past a tenon stem's root, and the arm's reach inside that span climbs
    # steeply once it is past ~44 deg: 17.95 at 44, 26.03 at 56, 33.73 at 63. So the room is
    # swept as far as the roots allow and no further -- measured at 56 deg, against the
    # chassis's 62.6. The last 6.6 deg would cost a tenon root, and the lever is DRIVEN 20.
    _stem = min(abs(ty) - KL._JW / 4 for ty in TEN_Y if abs(ty) > 1e-9)
    _x0 = -(KL.ARM_TX / 2 + KL.HS_CLR)
    _x1 = HOUS_X1 + 1.0
    _span = box_at(_x1 - _x0, 2 * _hw + 2.0, 400.0, x=(_x0 + _x1) / 2, y=0.0, z=0.0)
    # THE SLOT IS SIZED BY THE LEVER'S OWN SECTION, not by where the lever GETS TO (user,
    # 2026-09-25: "I'm confused why the lever would need to be that far +z during
    # installation. It seems like it could slide in purely along Y and not need to go up in
    # Z beyond where it is in the assembly"). Exactly right, and measured: the lever's
    # section in this span is z -6.80..16.40 and it stays that for the whole withdrawal --
    # a constant section, because sliding a part out does not move it in Z.
    #
    # Sized against the swept envelope's reach instead, the wall stood at 26.35: ten mm of
    # opening nothing passes through, with a 45 deg roof adding another 13.2 above THAT. And
    # it was self-defeating, because the roof then had to stay under a mount tenon's root,
    # which is what capped the room's sweep at 56 deg. Proven by A/B, not argued: with the
    # slot deleted entirely the lever still clears the housing at every angle to 63, and
    # WITH it the lever slides straight out +X with zero contact. The envelope carries the
    # sweep; the slot carries the INSTALL STROKE. They were conflated.
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
    # Sweeping the full envelope up through it hollowed out the inner halves of both mount
    # tenons, which left the rib mortises half empty.
    _env = _env.intersect(box_at(400.0, 400.0, HOUS_Z1 - (HOUS_Z0 - 50.0),
                                 x=0.0, y=0.0, z=(HOUS_Z1 + HOUS_Z0 - 50.0) / 2))
    w = w.cut(_env)
    # THE INSTALL ROOM = THE MOTION THAT INSTALLS IT, swept (user, 2026-09-25: "let's redo
    # the arm exit slot based on the room we actually need for installation. That would mean
    # moving the lever up just enough to clear the small indent it has in the floor below it
    # and then sweeping it out towards -y").
    #
    # WHAT WAS THERE was a house-profile slot 26.4 wide running the full height, and it was
    # a guess at the motion rather than the motion. Two faults followed from that, both
    # found by the user in the viewer and neither visible to any check here:
    #   its height was taken from the swept envelope's REACH, ten mm above anything that
    #     passes through it, and since the roof then had to duck a mount tenon's root it
    #     was what capped the lever's own sweep six degrees short of the chassis;
    #   its inboard end was a vertical wall at _x0 standing on a 17 mm void -- 44.47 mm2
    #     of face with nothing under it, and everything above it unsupported.
    # A cut shaped like the motion cannot have either: it is bounded by the lever's own
    # section, and it ENDS at the lever's rest pose, which is inside the room already.
    #
    # THE LIFT IS THE SEAT'S OWN DEPTH, read off the envelope rather than typed: the room
    # follows the lever, so the dip the hub sits in IS the envelope's own dip, 2.78 here.
    _at = lambda x: (_lever_envelope().val()
                     .intersect(box_at(1.0, 400.0, 400.0, x=x, y=0.0, z=0.0).val())
                     .BoundingBox().zmin)
    _lift = _at(0.0) * -1 + _at(HUB_D / 2 + 2.0)      # seat bottom -> the floor outside it
    _draw = (HOUS_X1 + 2.0) - _lever_envelope().val().BoundingBox().xmin
    _ins = None
    for dz in [j * 0.5 for j in range(0, int(_lift / 0.5) + 2)]:
        c = _lever_envelope().translate((0.0, 0.0, min(dz, _lift)))
        _ins = c if _ins is None else _ins.union(c)
    _top = _lever_envelope().translate((0.0, 0.0, _lift))
    for dx in [j * 2.0 for j in range(1, int(_draw / 2.0) + 2)]:
        _ins = _ins.union(_top.translate((min(dx, _draw), 0.0, 0.0)))
    # ...AND THE SLIVER OF RIB LEFT ABOVE IT. The strip between the two cartridge pockets
    # is 2.1 wide; the sweep takes it from below and the lever room takes it from above,
    # and what was left in between was 2.87 of rib standing on nothing -- a 25.7 mm2 flat
    # ceiling and a 6 mm2 end face with no material under either. Carrying the cut on up
    # through that band deletes it. It costs nothing structural: at 2.1 wide the rib is
    # already the thinnest thing in the part, and over this span it is in three pieces.
    _rib = (abs(KL.HS_YC) - KL.HS_POCKET_HW) + KL.HS_CLR
    _ib = _ins.val().BoundingBox()
    w = w.cut(_ins)
    w = KL.cut_axle_stack(w)       # bearing seats + contact rib + axle way
    w = KL.cut_feel_pockets(w, vplace, HOUS_X1)
    # SENSOR CRADLE — knee_lever's, parameterised by this housing's Z extents
    # (user: draw it once and reuse it). Everything about the sensor stack is
    # identical between the levers except how tall the board is, and that falls
    # out of z_bot/z_top.
    w = KL._cradle(w, HOUS_Z0, HOUS_Z1, x_max=HOUS_X1)
    # HUNG, not stood on the bed: this housing is 46.6 deep, so a post from its floor
    # would run the whole depth of the lever and put its coil 18 below the horizontal
    # levers'. Hung at KL.KEEP_DROP on a 45 deg buttress, every coil is at one height.
    w = w.union(KL.cable_keeper(HOUS_HW_P, HOUS_Z0, HOUS_X0, HOUS_Z1, hung=True))
    # NO SECOND POST HERE (user, 2026-09-23: "you added an extra winding post to the
    # LKV but it's unnecessary"). Right -- this lever already has a column, and the
    # arriving cable can turn round THAT. A turn post was added when the approach was
    # coming round the front, into the arm's sweep; once it comes round the +Y back end
    # instead, the keeper is already sitting at that end and does the job.
    # ...AND THE SAME 45 DEG KNEE RELIEF LKL GOT (user, 2026-09-25: "I would recommend
    # adding the same 45 cut we added to the LKL yesterday to the LKV so we can get a bit
    # more space for the knee"). Same construction, same constant: a plane TANGENT to a
    # circle of bearing seat + KNEE_BRG_WALL about the axle, so the material that takes the
    # spring's force and the knee's counter-force is sized by the bearing rather than by a
    # printing minimum. This housing is 46.6 deep, so the corner it gives back is bigger
    # than LKL's.
    w = w.cut(_knee_relief())
    return heal(w)                  # no printed back-stop threads any more (KL.cut_feel_rear)


def _knee_relief():
    """The 45 deg corner off the bottom +X end, across this housing's own width.

    BOUNDED TO THE HOUSING, like LKL's, so the sensor cradle outboard of +HOUS_HW_P keeps
    the board's grooves; and guarded around the board itself for the same reason as there
    -- the arithmetic is about one pose of a board that has been turned over before."""
    z0 = HOUS_Z0 - 1.0
    xo = HOUS_X1 + 1.0
    # ...AND IT RUNS OVER THE CRADLE, as LKL's does (user, 2026-09-25: "the 45 cut doesn't
    # cut the PCB like you have it for the LKL"). Bounded at HOUS_HW_P it stopped at the
    # cheek and left the cradle's corner standing proud of the relief on the very side the
    # knee comes from. The board is guarded instead -- by ITS OWN installed height here,
    # not LKL's, which is what KL.board_guard exists to get right.
    y0, y1 = -HOUS_HW_N, KL.CR_Y1 + KL.D.MIN_WALL_2P
    pts = [(z0 + KL.KNEE_CHAM_C, z0), (xo, z0), (xo, xo - KL.KNEE_CHAM_C)]
    f = cq.Face.makeFromWires(cq.Wire.makePolygon(
        [cq.Vector(x, y0, z) for x, z in pts] + [cq.Vector(pts[0][0], y0, pts[0][1])]))
    wedge = cq.Workplane("XY").add(cq.Solid.extrudeLinear(f, cq.Vector(0, y1 - y0, 0)))
    return wedge.cut(KL.board_guard(HOUS_Z0, HOUS_Z1))


def swing(s, throw=0.0):
    """Pose a lever-frame solid at a given throw. +throw pushes the +X arm UP."""
    return s.rotate((0, 0, 0), (0, 1, 0), -throw)


kv_lever = _lever()
kv_housing = _housing()


def demo_parts():
    """Bought/printed dummies in the local frame, for the assembly."""
    out = KL.axle_dummies(lambda s: s, "kv", HOUS_Z0, HOUS_Z1)
    out += KL.cart_dummies(vplace, "kv", hs_setback=HS_SETBACK_V)
    # the springs, tension screws, inserts and back-stops were MISSING here — this
    # lever was drawn with cartridge bodies and no feel system inside them
    out += KL.feel_dummies(vplace, "kv", hs_setback=HS_SETBACK_V)
    return out


if __name__ == "__main__":
    print(f"THROW_V   {THROW_V}   LOBE_RC_V {LOBE_RC_V}   stroke {_STROKE:.2f} "
          f"(horizontal: {KL.LOBE_RC * math.sin(math.radians(KL.THROW)):.2f})")
    print(f"housing   x {HOUS_X0:.2f}..{HOUS_X1:.2f}  y ±{HOUS_HW}  z {HOUS_Z0:.2f}..{HOUS_Z1:.2f}")
    print(f"axle sits {AXLE_DROP:.2f} lower than the horizontal lever's")
    print(f"tenons at local y {TEN_Y}, sliding local x {TEN_X0:.2f}..{TEN_X1:.2f}")


# ── GLOBAL POSE ──────────────────────────────────────────────────────────────
# The 90° that makes this a "vertical" lever. Local +X -> global -Y (the arm reaches
# out at the player), local +Y -> global +X (the sensor cluster runs toward the
# bridge). Z is untouched, so the housing top still lands flush on the chassis
# underside and the tenons still rise into the rib mortises from the same plane —
# which is why chassis.py needs NO new feature: rib_mortise is already an octagon
# slot of this width running along global Y in every rib, so it accepts these
# tenons as they are. What has to line up is X: the two stations sit at local
# y -12.60 / +10.40, so MOUNT_X is chosen to land them on two real ribs.
_Z_BOT = _BED_Z                     # -74.95 chassis underside (= chassis.Z_BOT, via
                                    # motor_bank.BED_Z — the spelled -75.15 it replaces had
                                    # gone stale when the bed datum snapped to the grid)
MOUNT_X = -455.0 - TEN_Y[1]         # -465.40 -> stations at ribs -478.0 and -455.0
MOUNT_Y = -130.0                    # axle 3.75 inboard of the -Y rail, so the housing
                                    # runs inboard under the body and the arm reaches out
MOUNT_Z = _Z_BOT - HOUS_Z1          # housing top flush with the chassis underside
MOUNT_POSE = (MOUNT_X, MOUNT_Y, MOUNT_Z)


POSE_ROT = (((0, 0, 1), -90),)      # ...the rotation half of it, on its own


def place(s):
    """Local frame -> guitar frame."""
    s = _rot(s)
    return s.translate(MOUNT_POSE)


def _rot(s):
    for ax, deg in POSE_ROT:
        s = s.rotate((0, 0, 0), ax, deg)
    return s


# PRINT ORIENTATION (the record, declared once per part) -- the ARM is the horizontal
# lever's arm, so it prints the way that one does; it just arrives in the guitar frame
# turned. Derived through this module's OWN pose rather than written out as +X, so a
# change to `place` carries it: local +Y -> world +X.
LEVER_UP = pose_dir(POSE_ROT, KL.LEVER_UP)


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
