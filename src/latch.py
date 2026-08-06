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

WHY THE -Y SIDE: authored -Y is the only face that is the SAME face on every
leg. The stacks are placed rot 0 / 180, so authored -Y lands OUTBOARD on both
rails (measured: the -Y face reaches y +64.75 and -138.75, each 5 mm proud of
its rail plane), while authored +-X flips -- a +-X button would face the
instrument's end on one rail and its middle on the other. And the INBOARD face
is not available at all: that is where the octagon mortise opens its groove,
so the female has no wall there to hook.

So all six buttons sit on the OUTBOARD face, the +Y ones facing the player.
Visible, but on the leg and the bar -- never on the body -- and far easier to
find one-handed than a hidden one. The cost is that -Y is the octagon's POINT,
not a flat: the male's apex is cut away across the latch band, which is what
opens the channel the hook travels in. The female mortise is NOT reshaped -- it
keeps its gable, so the stub still prints without a flat roof.

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

# ── the latch band ───────────────────────────────────────────────────────────
# X band, kept clear of the TRRS blind-mate way (x +5, D8..11) and the M4
# retention clearance at x +7 -- both live on the +X half, so the latch takes
# the -X half exactly as the old bolt did.
LX_C = -6.5                       # band centre X, HEAD/STUB side
LX_W = 10.0                       # band width X
LX0, LX1 = LX_C - LX_W / 2, LX_C + LX_W / 2      # -11.5 .. -1.5
# The band has to dodge the TRRS blind-mate way (D11), and the two joints put it
# on OPPOSITE authored sides: the head/stub carry it at authored x +5, while the
# tower/shaft block are authored rotated 180 and carry it at x -5. So the band
# MIRRORS per joint -- and because the slider and cover are symmetric about their
# own centre, that costs nothing: still ONE SKU, just placed at +-LX_C.
LX_HEAD = LX_C                    # leg head <-> body stub
LX_TOWER = -LX_C                  # bar tower <-> shaft block (mirrored)

# ── Y datums (all inboard-negative) ──────────────────────────────────────────
# The male's outer face is NOT the same on both joints: the head/stub are 44 sq
# but the tower/shaft block are BLK_W (35.6) sq. Datum the mechanism to the
# SMALLER one so a single slider + cover SKU serves both; the 44-wide head gets
# a finger recess (well_cutter) sinking its face to match -- which doubles as
# the thumb well that keeps the button from being pressed by accident.
FACE_Y = -17.8                    # = -BLK_W/2, the SHALLOWER of the two faces
COVER_T = 2.0                     # cover plate thickness
COVER_IN = FACE_Y + COVER_T       # -20.0  cover inner face = slider's OUT stop
MORT_APEX = -14.1                 # female mortise apex (octagon point)
CH_FLOOR = -13.6                  # female CHANNEL floor: the hook rides this,
                                  # fully retracted, through the engagement.
                                  # 0.5 inboard of the apex so the channel is a
                                  # real cut in the wall, not a sliver of it.
# Engagement is set by the THINNER female wall, which is the shaft block's: only
# 3.7 mm from the mortise apex to its face. 3.0 deep would leave 0.7 mm there --
# under the 1.6 two-bead floor. 1.8 leaves 1.9 mm, and the same hook then serves
# the stub too (which keeps 6.1 mm). One hook, both joints.
HOOK_ENGAGE = 1.8
HOOK_TIP = CH_FLOOR - HOOK_ENGAGE                      # -15.4 when ENGAGED
BACK_Y = 2.5                      # tunnel back wall: the spring reacts here
STROKE = 2.8                      # press travel. MUST EXCEED HOOK_ENGAGE -- equal
                                  # would put the hook exactly on the channel floor
                                  # at full press, i.e. zero clearance. 2.8 also
                                  # reads as a proper button throw under the thumb.

# ── Z bands (about the butt plane) ───────────────────────────────────────────
HOOK_Z0, HOOK_Z1 = 2.0, 9.0       # hook, inside the female
PAD_Z0, PAD_Z1 = -9.0, -2.0       # button pad, on the male body
BODY_Z0, BODY_Z1 = -12.0, 9.0     # slider overall
LOAD_Z = -14.0                    # tunnel/cover bottom (load window bottom)

# ── spring (NEW BOM SKU) ─────────────────────────────────────────────────────
SPR_OD = 5.0
SPR_WIRE = 0.6
SPR_FREE = 12.0
SPR_N = 6.0                       # active coils
SPR_SOLID = (SPR_N + 2) * SPR_WIRE                     # 4.8
SPR_RATE = 2.51                   # N/mm (G=79300, see the BOM line)
SPR_BORE_D = SPR_OD + 0.4         # 5.4 pocket in the slider
SPR_SEAT = 6.0                    # blind-bore depth in the slider
SPR_GAP = 4.0                     # slider back face -> tunnel back at REST.
                                  # MUST EXCEED STROKE or the slider bottoms on the
                                  # tunnel wall before the hook has cleared.
# installed = SEAT + GAP = 10.0 -> 2.0 preload -> 5 N holding the button out;
# at full press 5.6 compression -> 14 N. Never reaches solid (4.8).

LG_BLK_HALF = 17.8                # = BLK_W/2; the thin female's outer face
CLR = 0.25                        # sliding clearance on the guided faces
PAD_W = 6.0                       # button pad width. NARROWER than LX_W so the
                                  # slider body cannot pass the cover aperture --
                                  # that lip is the slider's outward stop.


def _assert_sane():
    installed = SPR_SEAT + SPR_GAP
    assert installed < SPR_FREE, "spring must be preloaded at rest"
    assert installed - STROKE > SPR_SOLID + 0.5, "spring goes solid before full press"
    # the hook must clear the female channel floor when fully pressed
    assert STROKE > HOOK_ENGAGE + 0.4, "stroke too short: hook fouls the channel"
    assert LG_BLK_HALF - (-HOOK_TIP) >= D.MIN_WALL_2P,         "pocket breaks the thin (shaft-block) female wall"
    assert SPR_GAP > STROKE, "slider bottoms on the tunnel back before full press"
    # ...but must NOT retract so far it leaves the male's own tunnel unsupported
    assert HOOK_Z0 > 0.0 and PAD_Z1 < 0.0, "hook belongs above the butt plane, pad below"
    assert BODY_Z0 <= PAD_Z0 and BODY_Z1 >= HOOK_Z1
    assert LOAD_Z < BODY_Z0, "load window must clear the slider's home position"
    assert PAD_W < LX_W - 2 * D.MIN_WALL, "cover lip too thin to stop the slider"
    assert LX1 < -0.5, "latch band fouls the TRRS way at x +5 (D11)"


_assert_sane()


# ═══════════════════════════════════════════════════════════════════════════
# MALE cutters (leg head / bar tower)
# ═══════════════════════════════════════════════════════════════════════════
def male_cutter(cx: float = LX_C) -> cq.Workplane:
    """Everything the MALE half loses: the slider TUNNEL (which also cuts the
    octagon apex away across the band -- that void is the hook's travel
    channel), the -Y load window the slider enters through, and the cover's
    dovetail. One cutter so the head and the tower cannot drift apart."""
    # tunnel: -Y face inward to the spring's back wall, over the slider's Z span
    tun = box_at(LX_W + 2 * CLR, BACK_Y - FACE_Y, BODY_Z1 - LOAD_Z,
                 x=cx, y=(FACE_Y + BACK_Y) / 2, z=(LOAD_Z + BODY_Z1) / 2)
    return tun.union(_cover_slot(cx))


def well_cutter(face_y: float, cx: float = LX_C) -> cq.Workplane:
    """FINGER WELL -- only for the 44-wide male (the leg head). Sinks its -Y
    face back to FACE_Y so the tower's cover and slider fit it unchanged, and
    leaves a recess your thumb drops into. The tower is already at FACE_Y and
    needs none of this."""
    if abs(face_y - FACE_Y) < 0.01:
        return None
    w = LX_W + 2 * COVER_T + 2 * COVER_T + 4.0
    return box_at(w, FACE_Y - face_y, (0.0 - LOAD_Z) + 4.0,
                  x=cx, y=(face_y + FACE_Y) / 2, z=(LOAD_Z - 4.0 + 0.0) / 2)


def _cover_slot(cx: float = LX_C) -> cq.Workplane:
    """Dovetail pocket for the cover: a 45 deg-flanked slot in the -Y face,
    open at the TOP (z0, the butt plane) so the cover installs DOWNWARD onto a
    hard stop, and can only leave upward -- which the female blocks once the
    joint is together. 45 deg flanks print without support in both the head's
    (build +-Y) and the tower's (build Z) orientations."""
    w0, w1 = LX_W + 2 * COVER_T, LX_W + 2 * COVER_T + 2 * COVER_T   # mouth, root
    pts = [(-w0 / 2, FACE_Y), (w0 / 2, FACE_Y),
           (w1 / 2, COVER_IN), (-w1 / 2, COVER_IN)]
    prof = (cq.Workplane("XY").polyline([(x + cx, y) for x, y in pts])
            .close().extrude(-(0.0 - LOAD_Z)))
    return cq.Workplane("XY").add(prof.val()).translate((0, 0, 0.0))


# ═══════════════════════════════════════════════════════════════════════════
# FEMALE cutters (body stub / shaft block)
# ═══════════════════════════════════════════════════════════════════════════
def female_cutter(engage_z: float, cx: float = LX_C) -> cq.Workplane:
    """Everything the FEMALE half loses -- all INTERNAL, nothing breaks the
    outer wall (user: no buttons, no holes on the body).

      * CHANNEL: the hook's retracted travel path, from the mouth up. Its floor
        (CH_FLOOR) is what cams the hook in on the way past.
      * MOUTH LEAD-IN: 45 deg, so the push-together cams the hook rather than
        butting it.
      * POCKET: the hook's home, 3.0 deeper. Its floor is a FLAT 90 deg ledge
        -- the retention face. Its roof is gabled 45 deg so the pocket does not
        put a flat ceiling in the female's print.

    `engage_z` is the female-local z of the butt plane (its mouth)."""
    z0, z1 = engage_z, engage_z + HOOK_Z1 + 30.0
    ch = box_at(LX_W + 2 * CLR, BACK_Y - CH_FLOOR, z1 - z0,
                x=cx, y=(CH_FLOOR + BACK_Y) / 2, z=(z0 + z1) / 2)
    # 45 deg lead-in at the mouth: a wedge that opens the channel floor downward
    lead = (cq.Workplane("YZ")
            .polyline([(CH_FLOOR, z0), (CH_FLOOR - 3.0, z0), (CH_FLOOR, z0 + 3.0)])
            .close().extrude(LX_W + 2 * CLR)
            .translate((cx - LX_W / 2 - CLR, 0, 0)))
    pk = _pocket(engage_z, cx)
    return ch.union(lead).union(pk)


def _pocket(engage_z: float, cx: float = LX_C) -> cq.Workplane:
    """Retention pocket + its 45 deg gable roof (printability), floor FLAT."""
    zl = engage_z + HOOK_Z0 - CLR          # the LEDGE (retention face)
    zt = engage_z + HOOK_Z1 + CLR
    body = box_at(LX_W + 2 * CLR, CH_FLOOR - HOOK_TIP, zt - zl,
                  x=cx, y=(HOOK_TIP + CH_FLOOR) / 2, z=(zl + zt) / 2)
    # gable the pocket's -Y extremity (its roof in the female's print)
    gab = (cq.Workplane("YZ")
           .polyline([(HOOK_TIP, zt), (CH_FLOOR, zt), (CH_FLOOR, zt + (CH_FLOOR - HOOK_TIP))])
           .close().extrude(LX_W + 2 * CLR)
           .translate((cx - LX_W / 2 - CLR, 0, 0)))
    return body.union(gab)


# ═══════════════════════════════════════════════════════════════════════════
# the printed parts
# ═══════════════════════════════════════════════════════════════════════════
def slider(cx: float = LX_C) -> cq.Workplane:
    """LATCH SLIDER (PCTG) -- one SKU for both joints. Drawn at its ENGAGED
    (rest) position in the male frame.

    A STEPPED bar. The step exists because the two ends work at very different
    radii: below the butt plane the male body runs out to FACE_Y (-22), while
    above it there is only the octagon spigot, whose apex the tunnel cut away.
    So the lower step reaches out to the cover (its OUT stop) and the upper step
    stops at the female channel floor, with the HOOK protruding from it.

    Prints flat on its BACK face: the hook lead and the pad both face up, so
    there is nothing to support."""
    back = BACK_Y - SPR_GAP                     # -1.5  back face at REST
    up_front = CH_FLOOR - 0.1                   # -13.7 upper step front

    def span(y0, y1, z0, z1):
        return box_at(LX_W, y1 - y0, z1 - z0,
                      x=cx, y=(y0 + y1) / 2, z=(z0 + z1) / 2)

    b = span(COVER_IN, back, BODY_Z0, PAD_Z1)          # lower step
    b = b.union(span(up_front, back, PAD_Z1, BODY_Z1))  # upper step
    # HOOK: out to HOOK_TIP. BOTTOM face flat = the retention face; TOP face
    # chamfered 45 deg = the push-together cam.
    b = b.union(span(HOOK_TIP, up_front, HOOK_Z0, HOOK_Z1))
    lead = (cq.Workplane("YZ")
            .polyline([(HOOK_TIP, HOOK_Z1), (up_front, HOOK_Z1),
                       (HOOK_TIP, HOOK_Z1 - (up_front - HOOK_TIP))])
            .close().extrude(LX_W).translate((cx - LX_W / 2, 0, 0)))
    b = b.cut(lead)
    # PAD: through the cover aperture, flush with the outer face at rest
    b = b.union(box_at(PAD_W, COVER_IN - FACE_Y, PAD_Z1 - PAD_Z0,
                       x=cx, y=(FACE_Y + COVER_IN) / 2,
                       z=(PAD_Z0 + PAD_Z1) / 2))
    # spring blind bore, into the back face
    b = b.cut(cyl_y(SPR_BORE_D, SPR_SEAT + 0.2, y0=back - SPR_SEAT,
                    x=cx, z=(PAD_Z0 + PAD_Z1) / 2))
    return b


def cover(cx: float = LX_C) -> cq.Workplane:
    """LATCH COVER (PCTG) -- one SKU for both joints. The plate that closes the
    slider's load window: it is the slider's OUTWARD stop (so the pad cannot
    push out past its aperture) and its Z lock. Slides DOWN its 45 deg dovetail
    onto a hard stop; only leaves upward, which the female half blocks once the
    joint is assembled -> captive, no fasteners. Prints flat."""
    w0, w1 = LX_W + 2 * COVER_T, LX_W + 2 * COVER_T + 2 * COVER_T
    pts = [(-w0 / 2, FACE_Y), (w0 / 2, FACE_Y),
           (w1 / 2, COVER_IN), (-w1 / 2, COVER_IN)]
    prof = (cq.Workplane("XY").polyline([(x + cx, y) for x, y in pts])
            .close().extrude(-(0.0 - LOAD_Z)))
    b = cq.Workplane("XY").add(prof.val())
    # button APERTURE: the pad passes, the slider's body cannot
    b = b.cut(box_at(PAD_W + 2 * CLR, COVER_T + 2.0,
                     (PAD_Z1 - PAD_Z0) + 2 * CLR,
                     x=cx, y=(FACE_Y + COVER_IN) / 2,
                     z=(PAD_Z0 + PAD_Z1) / 2))
    return b


def slider_pressed(cx: float = LX_C) -> cq.Workplane:
    """The slider drawn RELEASED (pressed in by STROKE) -- for clearance checks."""
    return slider(cx).translate((0, STROKE, 0))
