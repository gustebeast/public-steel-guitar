"""Push-to-connect / press-to-release LATCH — shared by both leg joints.

ONE mechanism, ONE spring SKU, ONE user interface, used at:
  * leg HEAD  -> body STUB      (you pull the LEG off the body)
  * bar TOWER -> shaft BLOCK    (you lift the BAR off the legs)

In both, the piece you REMOVE is the MALE (spigot) half, so the mechanism lives
in the male and the button sits on the male's own body BELOW the joint line.
The female gets only internal reliefs -- no through-hole, no button, nothing
visible. That is what keeps buttons off the body (user).

WHY THE BUTTON CANNOT SIMPLY BE THE BOLT'S NOSE: the obvious tube-lock layout
(nose pokes through the female wall and doubles as the button) puts the button
on the FEMALE -- the body at one joint, the leg at the other. Both are the
wrong part here. So the slider has to reach ACROSS the butt plane: hook above
it, button below it, one rigid piece.

WHY THE AUTHORED +Y SIDE: every leg is now placed rot 180, so authored +Y lands
world -Y on BOTH rails. All six buttons therefore end up on the single -Y face
-- hidden from an audience in front of the instrument, and all reachable from
one side when it is turned over for assembly (user).

That face is the octagon's GROOVE side, so the band has to dodge the STEM, which
runs out to the full 44 face over x -6..+6. Outside the stem there is real wall:
measured over x -13.5..-8.5 the octagon tops out at 12.80, leaving 5.00 mm to
the thin female's face (17.8) and 9.20 to the stub's (22.0). That is MORE wall
than the old -Y apex band had (3.70), so the engagement went up with the move.

The band also has to clear the TRRS D11 way -- x +5 on the head/stub (reaching
x -0.5) and mirrored to x -5 on the tower/shaft block. x -13.5..-8.5 clears both
by 8 mm, which is why the D11 z-cap that used to constrain the hook height is no
longer the binding constraint (the assertion stays as a guard).

SEQUENCE (no buttons pressed to connect -- user goal 2):
  push together -> the hook's 45 deg lead meets the female channel floor and
  cams the slider IN against the spring -> the hook rides the floor, fully
  retracted, up the whole engagement -> at depth it springs OUT into the
  retention pocket. The pocket's floor is a FLAT 90 deg ledge: pulling on the
  joint loads it in pure shear with NO cam-out component, so a hard lift
  cannot pop the latch.
To release (user goal 3): press the pad on the piece in your hand and pull --
one hand, one motion.

CREEP (user): nothing here is loaded at rest. Standing weight goes face-to-face
through the butt plane, not through the latch; the latch only sees load when
the instrument is LIFTED. The one continuous force is the spring holding the
button out, which is exactly why that spring is STEEL and not TPU -- a printed
elastomer takes a compression set there and the button sinks in over years.

PARTS, per joint: latch_slider + latch_cover (printed) + one steel coil. Both
printed parts are ONE SKU across both joints -- the head and the tower differ
only in what surrounds them, not in the mechanism.

ASSEMBLY: slider (spring in its blind bore) enters through the male's -Y face
opening, then lifts into place; the COVER slides DOWN a dovetail behind it,
bottoming on a hard stop. The cover can only come back out UPWARD, which the
female half blocks once the joint is together -- so with the leg on the body
(or the bar on the legs) the whole mechanism is captive with zero fasteners.

FRAME: male-local, z0 = the BUTT PLANE (male body top face = female mouth),
-Y = inboard = the button side. Both joints share this frame.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_y
from cadkit.printing import snap as _snap

# ── the bead grid ────────────────────────────────────────────────────────────
# Every printed length below is a whole number of beads, written as the COUNT so
# the count is what you read (cadkit.printing documents the rule). The three
# exemptions all appear in this module and are worth naming where they sit:
# CLR/OCT_CLR are CLEARANCES (gaps, never material -- no bead is laid across
# one), and the spring block is HARDWARE.
B = D.BEAD

# ── clearances (sub-bead BY NECESSITY -- see above) ──────────────────────────
CLR = 0.25                        # sliding clearance on the guided faces
OCT_CLR_MIN = 0.1                 # LEAST standoff of the channel floor from the octagon
TIP_GAP = 0.1                     # hook tip -> pocket back, so the hook never bottoms

# ── the latch band ───────────────────────────────────────────────────────────
# X band, kept clear of the TRRS blind-mate way (x +5, D8..11) and the M4
# retention clearance at x +7 -- both live on the +X half, so the latch takes
# the -X half exactly as the old bolt did.
LX_C = -13 * B                    # -10.4 band centre X, HEAD/STUB side. Moved in
                                  # one bead from -11.0 when everything went on the
                                  # grid: it buys the LOWER band the room to reach
                                  # 16 beads, which is what lets the pad be WIDER
                                  # than it was (8.0 vs 7.5) with an on-grid lip.
LX_W = 6 * B                      # 4.8 band width X (bounded by the stem at |x| 6
                                  # and the spigot edge at |x| 14; -12.8..-8.0
                                  # clears both, where a 7-bead 5.6 would have run
                                  # the band onto the spigot edge exactly)
LX0, LX1 = LX_C - LX_W / 2, LX_C + LX_W / 2      # -13.5 .. -8.5
# LX_W is bounded ABOVE the butt plane, where the slider is inside the spigot and
# has to miss the stem. BELOW it the male body is a full 44 square with nothing
# in the way, so the lower half runs WIDER -- otherwise the button pad inherits
# the 5 mm hook band minus its lip and ends up ~3 mm, which is not a thumb
# target. The slider is a T in plan: narrow hook, wide pad.
LOW_W = 16 * B                    # 12.8 lower band (pad + load window)
# The band still MIRRORS per joint, because the two joints carry the TRRS way on
# opposite authored sides (head/stub +5, tower/shaft block -5). The slider and
# cover are symmetric about their own centre, so that costs nothing: ONE SKU,
# placed at +-LX_C.
LX_HEAD = LX_C                    # leg head <-> body stub
LX_TOWER = -LX_C                  # bar tower <-> shaft block (mirrored)

# ── Y datums (all inboard-negative) ──────────────────────────────────────────
# The male's outer face is NOT the same on both joints: the head/stub are 44 sq
# but the tower/shaft block are BLK_W (35.6) sq. Datum the mechanism to the
# SMALLER one so a single slider + cover SKU serves both; the 44-wide head gets
# a finger recess (well_cutter) sinking its face to match -- which doubles as
# the thumb well that keeps the button from being pressed by accident.
FACE_Y = 28 * B                   # 22.4 = legs.SQ_W/2, the LEG HEAD'S OWN outer face.
                                  # Was 17.8 -- the tower/shaft block's face -- so that
                                  # one slider + cover SKU could serve both joints. The
                                  # bar joint is gone and re-use is explicitly not a
                                  # concern any more (user), so the mechanism sits on
                                  # the face it actually lives on. Everything the old
                                  # compromise cost goes with it: no finger well sunk
                                  # into the head (that was a 422 mm^2 flat ceiling ON
                                  # the print bed), no 4.2-thick second cover, no thumb
                                  # dish to claw the recess back. The cover is a plain
                                  # flat plate flush with the leg, and the button sits
                                  # flush with it -- nothing proud to be knocked.
COVER_T = 3 * B                   # 2.4 cover plate thickness
COVER_LIP = 3 * B                 # 2.4 the aperture lip each side: what the pad
                                  # shoulders against as the slider's OUT stop
COVER_IN = FACE_Y - COVER_T       # 15.8  cover inner face = slider's OUT stop
OCT_TOP = 13.8                    # octagon's max +Y within the band. MEASURED off the
                                  # real spigot, not derived -- cadkit owns the octagon's
                                  # profile and latch cannot import legs (legs imports
                                  # latch). So it is a STALE-DATUM RISK by construction,
                                  # and legs.leg_head asserts it: widening SQ_W 44.0 ->
                                  # 44.8 moved this 12.8 -> 13.8, which silently put the
                                  # channel floor 0.9 mm INSIDE the spigot until the
                                  # assert below was added.
CH_FLOOR = _snap(OCT_TOP + OCT_CLR_MIN + TIP_GAP, B, "up") - TIP_GAP
OCT_CLR = CH_FLOOR - OCT_TOP      # 0.50 the standoff that actually results
#   THE CLEARANCE IS WHAT ABSORBS THE OCTAGON (user: position the latch so the LEG comes
#   out bead-aligned). The octagon's apex within the band is 13.8 -- 17.25 beads -- and it
#   CANNOT be moved onto the grid: the flank is 45 deg, so the apex tracks the band 1:1 and
#   shifting the band by whole beads shifts the apex by whole beads, leaving the same 0.15
#   remainder every time (measured across five positions). The band's X placement is already
#   on-grid and stays there.
#   So the standoff takes the remainder instead. Snapping (apex + least standoff + tip gap)
#   UP to a bead and backing off TIP_GAP puts the POCKET BACK on the grid, which is what
#   makes the material behind it -- FACE_Y minus pocket back -- a whole 7 beads instead of
#   7.5. Self-adjusting: re-measure OCT_TOP after any leg resize and the wall stays on-grid.
#   12.9 -> 14.3 female CHANNEL floor: the hook rides
                                  # this, fully retracted, through the whole
                                  # engagement. Just clear of the octagon so the
                                  # channel is a real cut in the wall.
# Engagement is set by the THINNER female wall, which is the shaft block's: only
# 3.7 mm from the mortise apex to its face. 3.0 deep would leave 0.7 mm there --
# under the 1.6 two-bead floor. 1.8 leaves 1.9 mm, and the same hook then serves
# the stub too (which keeps 6.1 mm). One hook, both joints.
HOOK_ENGAGE = 3 * B               # 2.4 -- up again from 2.0 on the snap. Load-
                                  # bearing, so it rounds UP; the thin female still
                                  # keeps 17.8 - 15.3 = 2.5 mm behind the pocket.
HOOK_TIP = CH_FLOOR + HOOK_ENGAGE                      # 14.9 when ENGAGED
BACK_Y = -3 * B                   # -2.4 tunnel back wall: the spring reacts here.
                                  # MALE-FRAME ONLY -- the female must never use it
                                  # (see female_cutter; it did, and left a sliver).
HOOK_BACK = CH_FLOOR - CLR        # 12.65 the hook's INBOARD face at rest (the
                                  # slider's upper step rides here)
STROKE = 4 * B                    # 3.2 press travel. MUST EXCEED HOOK_ENGAGE -- equal
                                  # would put the hook exactly on the channel floor
                                  # at full press, i.e. zero clearance. 2.8 also
                                  # reads as a proper button throw under the thumb.


# ── Z bands (about the butt plane) ───────────────────────────────────────────
# The hook's TOP is capped by the TRRS way, not by anything in the latch. The
# D11 handle way opens at z +6.3 and runs to +37.5; where the tunnel reached up
# beside it the wall between the two cavities thinned to 1.25 mm -- under the
# 1.6 two-bead floor. Below +6.3 only the D8 way is alongside and the wall is
# 2.25. So the whole mechanism stays BELOW the D11 way.
TRRS_WAY_Z0 = 6.3                 # D11 handle way opens here (legs.leg_head)
# HOOK_Z0 is also the LEDGE THICKNESS: the ledge is the material between the
# female's mouth (z0) and the pocket floor, so a low hook means a wafer of a
# shelf carrying the whole pull-out load. At 1.0 it was 0.75 mm. 2.0 gives 1.75,
# just over the two-bead floor, and still keeps the pocket top under the TRRS way.
LEDGE_T = 3 * B                   # 2.4 the RETENTION LEDGE itself -- the one
                                  # surface carrying the whole instrument's weight
                                  # in shear. Was 1.75 = 2.19 beads, exactly the
                                  # case that makes Arachne improvise a bead; now
                                  # 3 clean ones. Named, because it is the number
                                  # that matters, not the z it happens to sit at.
HOOK_Z0 = LEDGE_T + CLR           # 2.65 -- ledge + the sliding gap above it
HOOK_Z1 = HOOK_Z0 + 3 * B         # 5.05 hook 2.4 tall, inside the female. 4 beads
                                  # would put the slider's top at 6.4 and the whole
                                  # mechanism has to stay under the D11 TRRS way at
                                  # 6.3 -- so the TRRS way is once again what caps
                                  # the hook, exactly as the comment above says.
PAD_Z0, PAD_Z1 = -10 * B, -3 * B  # -8.0 .. -2.4 button pad, on the male body
BODY_Z0, BODY_Z1 = -13 * B, 7 * B # -10.4 .. 5.6 slider overall
LOAD_Z = -15 * B                  # -12.0 tunnel/cover bottom (load window bottom).
                                  # Kept above the head's SECTION SOCKET, whose
                                  # roof is at -12.6: dip past it and the tunnel
                                  # opens into the socket, where the segment's
                                  # plug lives.

# ── spring (NEW BOM SKU) ─────────────────────────────────────────────────────
SPR_OD = 5.0
SPR_WIRE = 0.6
SPR_FREE = 12.0
SPR_N = 6.0                       # active coils
SPR_SOLID = (SPR_N + 2) * SPR_WIRE                     # 4.8
SPR_RATE = 2.51                   # N/mm (G=79300, see the BOM line)
SPR_BORE_D = SPR_OD + 0.4         # 5.4 pocket in the slider
SPR_ID = SPR_OD - 2 * SPR_WIRE    # 3.8 coil bore
POST_D = SPR_ID - 0.8             # 3.0 guide post (0.4 radial clearance in the coil)
POST_L = 6 * B                    # 4.8 post length off the tunnel's back wall
SPR_SEAT = 8 * B                  # 6.4 blind-bore depth in the slider
SPR_GAP = 5 * B                   # 4.0 slider back face -> tunnel back at REST.
                                  # MUST EXCEED STROKE or the slider bottoms on the
                                  # tunnel wall before the hook has cleared.
# installed = SEAT + GAP = 10.4 -> 1.6 preload -> 4.0 N holding the button out;
# at full press 4.8 compression -> 12.0 N. Never reaches solid (4.8 vs 7.2).

SLIDER_BACK = BACK_Y + SPR_GAP       # 1.60 the slider's back face at REST
CH_BACK = SLIDER_BACK - STROKE - CLR # -1.85 the female channel's inboard limit.
                                     # NOT the hook's back face: the slider's upper
                                     # STEP crosses the butt plane too, so the female
                                     # has to clear the whole pressed slider, not just
                                     # the hook. (Bounding it to the hook made release
                                     # jam -- caught by the release/insertion test.)
                                     # Derived from the slider so they cannot drift.

LG_BLK_HALF = FACE_Y                # = BLK_W/2; the thin female's outer face (legs.BLK_W
                                  # owns this number; latch cannot import legs -- legs
                                  # imports latch -- so _assert_sane cross-checks it)
PAD_W = LOW_W - 2 * COVER_LIP     # 8.0 button pad width. NARROWER than LOW_W so
                                  # the slider body cannot pass the cover aperture.
                                  # Derived from the LIP rather than set directly:
                                  # the lip is the slider's outward stop and the
                                  # thing that must be a whole number of beads, so
                                  # it is what gets stated. (Both were off-grid
                                  # before -- 7.5 pad, 1.75 lip.)


def _assert_sane():
    installed = SPR_SEAT + SPR_GAP
    assert installed < SPR_FREE, "spring must be preloaded at rest"
    assert installed - STROKE > SPR_SOLID + 0.5, "spring goes solid before full press"
    # the hook must clear the female channel floor when fully pressed
    assert STROKE > HOOK_ENGAGE + 0.4, "stroke too short: hook fouls the channel"
    assert LG_BLK_HALF - HOOK_TIP >= D.MIN_WALL_2P,         "pocket breaks the thin (shaft-block) female wall"
    assert SPR_GAP > STROKE, "slider bottoms on the tunnel back before full press"
    # ...but must NOT retract so far it leaves the male's own tunnel unsupported
    assert HOOK_Z0 > 0.0 and PAD_Z1 < 0.0, "hook belongs above the butt plane, pad below"
    assert BODY_Z0 <= PAD_Z0 and BODY_Z1 >= HOOK_Z1
    assert LOAD_Z < BODY_Z0, "load window must clear the slider's home position"
    assert BODY_Z1 <= TRRS_WAY_Z0 - 0.5,         "tunnel reaches the D11 TRRS way: the wall between them drops under MIN_WALL_2P"
    assert HOOK_Z0 - CLR >= D.MIN_WALL_2P,         "retention LEDGE too thin -- it is the material between the female mouth and the pocket floor"
    assert HOOK_Z1 > HOOK_Z0 + 1.0, "hook too short to carry the pull-out load"
    assert PAD_W < LOW_W - 2 * D.MIN_WALL_2P, "cover lip too thin to stop the slider"
    assert LOW_W > LX_W, "lower band should be the wide one"
    assert abs(LX_C) + LOW_W / 2 + 2 * COVER_T < 22.0, "cover dovetail runs off the 44 face"
    assert LX1 < -0.5 and LX0 > -14.0, "band must clear the TRRS way and stay on the spigot"
    assert abs(LX0) > 6.0 and abs(LX1) > 6.0, "band must clear the octagon STEM (|x| <= 6)"


_assert_sane()


# ═══════════════════════════════════════════════════════════════════════════
# geometry helpers
# ═══════════════════════════════════════════════════════════════════════════
def _yz(dx, y0, y1, z0, z1, x):
    """Box spanning y0..y1 and z0..z1, whichever way round the bounds come.
    The latch was authored on -Y and now lives on +Y; sign-agnostic spans are
    what stop that move from turning into a crop of negative-length boxes."""
    return box_at(dx, abs(y1 - y0), abs(z1 - z0),
                  x=x, y=(y0 + y1) / 2.0, z=(z0 + z1) / 2.0)


# ═══════════════════════════════════════════════════════════════════════════
# MALE cutters (leg head / bar tower)
# ═══════════════════════════════════════════════════════════════════════════
def male_cutter(cx: float = LX_C) -> cq.Workplane:
    """What the MALE half loses: the slider TUNNEL -- which also takes the
    octagon's +Y shoulder away across the band, opening the void the hook
    travels in -- plus the cover's dovetail. One cutter, so the head and the
    tower cannot drift apart."""
    up = _yz(LX_W + 2 * CLR, FACE_Y, BACK_Y, 0.0, BODY_Z1, cx)     # in the spigot
    low = _yz(LOW_W + 2 * CLR, FACE_Y, BACK_Y, LOAD_Z, 0.0, cx)    # in the body
    return up.union(low).union(_cover_slot(cx))


SLOT_W = LOW_W + 2 * COVER_T      # 17.6 slot mouth (the cover's outer width)


def _cover_slot(cx: float = LX_C) -> cq.Workplane:
    """Dovetail pocket for the cover: 45 deg flanks, narrow at the FACE and wide
    at the root, open at the TOP (z0, the butt plane) so the cover installs
    downward onto a hard stop and can only leave upward -- which the female half
    blocks once the joint is together.
"""
    w0, w1 = SLOT_W, LOW_W + 4 * COVER_T
    pts = [(-w0 / 2, FACE_Y), (w0 / 2, FACE_Y), (w1 / 2, COVER_IN), (-w1 / 2, COVER_IN)]
    prof = (cq.Workplane("XY").polyline([(x + cx, y) for x, y in pts])
            .close().extrude(LOAD_Z))
    return cq.Workplane("XY").add(prof.val())


def male_post(cx: float = LX_C) -> cq.Workplane:
    """GUIDE POST for the coil, standing off the tunnel's back wall into the
    spring's ID -- the project's coil pattern (the knee-lever cartridge pilots
    its coil ID rather than cupping the end). Without it the coil is located at
    ONE end only. It also reaches past the slider's back face, so it pilots the
    slider against tilt."""
    return cyl_y(POST_D, POST_L, y0=BACK_Y, x=cx, z=(PAD_Z0 + PAD_Z1) / 2)


# ═══════════════════════════════════════════════════════════════════════════
# FEMALE cutters (body stub / shaft block)
# ═══════════════════════════════════════════════════════════════════════════
def female_cutter(engage_z: float, cx: float = LX_C) -> cq.Workplane:
    """What the FEMALE half loses -- all INTERNAL; the outer wall is never
    broken, so no button and no hole appears on the body (user).

      * CHANNEL: the hook's retracted travel path, spanning exactly the hook's
        OWN retracted Y band (CH_BACK..CH_FLOOR). The octagon's +Y flank slopes
        across the band, so the mortise void alone does not clear a rectangular
        hook -- this squares it off out to CH_FLOOR.

        This used to run to BACK_Y, which is a MALE-frame datum: the male's
        slider-tunnel back wall, 15.3 mm inboard. Nothing in the FEMALE needs
        the channel that deep -- only the hook ever crosses the butt plane --
        and the excess mostly landed harmlessly inside the octagon mortise
        (already void). Mostly: where the mortise's flank cut away, a
        0.75 x 0.75 x 35 mm sliver of real material survived and got sliced
        off, leaving a full-height notch visible on leg_body_stub_2 and on no
        other stub, since it is the only one carrying a latch (user report).
      * POCKET: the hook's home. Its floor is a FLAT 90 deg ledge, the retention
        face; the ledge is the material between the female's MOUTH and that
        floor, which is why HOOK_Z0 is also the ledge thickness.

    NO mouth lead-in. One used to sit here and it removed exactly the material
    the ledge is made of, so the hook passed straight through and the latch
    retained nothing. The camming is the hook's own 45 deg top chamfer."""
    z0, z1 = engage_z, engage_z + HOOK_Z1 + 30.0
    ch = _yz(LX_W + 2 * CLR, CH_FLOOR, CH_BACK, z0, z1, cx)
    return ch.union(_pocket(engage_z, cx))


def _pocket(engage_z: float, cx: float = LX_C) -> cq.Workplane:
    """Retention pocket. Floor FLAT (the ledge). No gable: on this face the
    pocket's outer boundary is the BED side in the female's print, so it is a
    floor rather than a ceiling and needs no roof relief."""
    return _yz(LX_W + 2 * CLR, CH_FLOOR, HOOK_TIP + TIP_GAP,
               engage_z + HOOK_Z0 - CLR, engage_z + HOOK_Z1 + CLR, cx)


# ═══════════════════════════════════════════════════════════════════════════
# the printed parts
# ═══════════════════════════════════════════════════════════════════════════
def slider(cx: float = LX_C) -> cq.Workplane:
    """LATCH SLIDER (PCTG) -- one SKU for both joints, drawn ENGAGED.

    A STEPPED bar: the two ends work at different radii, because below the butt
    plane the male body runs out to FACE_Y while above it there is only the
    spigot, whose shoulder the tunnel cut away. The lower step reaches the cover
    (its OUT stop); the upper step stops just short of the female channel floor,
    with the HOOK protruding from it."""
    back = BACK_Y + SPR_GAP                     # 1.5  back face at REST
    up_front = CH_FLOOR - CLR                   # 12.65 upper step front:
    #   the female's material starts ABOVE CH_FLOOR, so the step sits below it.
    b = _yz(LOW_W, COVER_IN, back, BODY_Z0, PAD_Z1, cx)         # lower step (wide)
    b = b.union(_yz(LX_W, up_front, back, PAD_Z1, BODY_Z1, cx))  # upper step
    # HOOK: out to HOOK_TIP. BOTTOM face flat = the retention face; TOP face
    # chamfered 45 deg = the push-together cam.
    b = b.union(_yz(LX_W, up_front, HOOK_TIP, HOOK_Z0, HOOK_Z1, cx))
    lead = (cq.Workplane("YZ")
            .polyline([(HOOK_TIP, HOOK_Z1), (up_front, HOOK_Z1),
                       (HOOK_TIP, HOOK_Z1 - (HOOK_TIP - up_front))])
            .close().extrude(LX_W).translate((cx - LX_W / 2, 0, 0)))
    b = b.cut(lead)
    # PAD: through the cover aperture, flush with the outer face at rest
    b = b.union(_yz(PAD_W, FACE_Y, COVER_IN, PAD_Z0, PAD_Z1, cx))
    # spring blind bore, into the back face
    b = b.cut(cyl_y(SPR_BORE_D, SPR_SEAT + 0.2, y0=back - 0.2,
                    x=cx, z=(PAD_Z0 + PAD_Z1) / 2))
    return b


def cover(cx: float = LX_C) -> cq.Workplane:
    """LATCH COVER (PCTG) -- ONE flat plate, flush with the leg head's face.
    Closes the slider's load window; its aperture lip is the slider's outward
    stop AND its Z lock. Slides DOWN its dovetail onto a hard stop, and is
    captive once the joint is assembled. Prints flat, no overhang."""
    b = _cover_slot(cx)
    b = b.cut(_yz(PAD_W + 2 * CLR, FACE_Y + 1.0, COVER_IN - 1.0,
                  PAD_Z0 - CLR, PAD_Z1 + CLR, cx))
    return b


def slider_pressed(cx: float = LX_C) -> cq.Workplane:
    """The slider RELEASED -- pressed in by STROKE, i.e. away from the face."""
    return slider(cx).translate((0, -STROKE, 0))


# ═══════════════════════════════════════════════════════════════════════════
# hardware dummy
# ═══════════════════════════════════════════════════════════════════════════
SPR_TURNS_DEAD = 1.0              # closed coil at each end (closed-and-ground)
SPR_TURNS = SPR_N + 2 * SPR_TURNS_DEAD                 # 8.0 total


def spring_length(pressed: bool = False) -> float:
    """Installed coil length: SEAT (inside the slider's blind bore) + GAP (open,
    to the tunnel's back wall). Pressing the button closes the GAP by STROKE."""
    return SPR_SEAT + SPR_GAP - (STROKE if pressed else 0.0)


def spring_force(pressed: bool = False) -> float:
    return (SPR_FREE - spring_length(pressed)) * SPR_RATE


def spring(cx: float = LX_C, pressed: bool = False) -> cq.Workplane:
    """The steel compression coil, as a real swept helix -- axis along Y (the
    slider's travel), seated in the slider's blind bore and bearing on the
    tunnel's back wall. pressed=True for the released state.

    Exact where it matters: OD, wire diameter, turn count, and OVERALL length
    (the helix PATH is built one wire-diameter short, because the swept tube
    adds a wire radius past the path at each end).

    Simplified where it does not: uniform pitch, so the closed-and-ground END
    coils are drawn pitched rather than touching. No interface cares -- OD sets
    the bore fit, overall length sets the gap, and solid height is turns*wire
    either way. The three-segment version has non-tangent pitch junctions whose
    fuse is not reliably a single solid."""
    L = spring_length(pressed)
    r_mid = (SPR_OD - SPR_WIRE) / 2.0
    path_h = L - SPR_WIRE
    wire = cq.Wire.makeHelix(pitch=path_h / SPR_TURNS, height=path_h, radius=r_mid)
    coil = (cq.Workplane("XZ").center(r_mid, 0).circle(SPR_WIRE / 2)
            .sweep(cq.Workplane("XY").add(wire), isFrenet=True))
    coil = coil.rotate((0, 0, 0), (1, 0, 0), -90)
    # Anchor on the TUNNEL BACK, the end that does not move. Anchoring on the
    # slider's bore floor leaves the pressed state drawn a full STROKE out.
    return coil.translate((cx, BACK_Y + SPR_WIRE / 2, (PAD_Z0 + PAD_Z1) / 2))


def _assert_spring():
    assert abs(SPR_TURNS * SPR_WIRE - SPR_SOLID) < 1e-6, "solid height must be turns*wire"
    assert spring_length(True) > SPR_SOLID + 0.5, "coil binds before the button bottoms"
    assert SPR_OD + 0.4 <= SPR_BORE_D + 1e-9, "coil does not clear its bore"
    assert POST_D < SPR_ID - 0.4, "guide post binds inside the coil"
    # the post must never reach the slider's bore floor, closest at full press
    floor_pressed = BACK_Y + SPR_GAP + SPR_SEAT - STROKE
    assert BACK_Y + POST_L < floor_pressed - 1.0, "guide post bottoms in the slider's bore"


_assert_spring()
