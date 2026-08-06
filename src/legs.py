"""Adjustable legs (×4) — PCTG tubes + TPU feet/washers. Quick-attach.

Height: COARSE = how many identical stackable SEGMENTS you thread in (the
legs must print in pieces for build volume anyway, so the pieces ARE the
adjustment); FINE = a Ø20 shaft sliding in a clamped SLEEVE. One segment
steps the height by 142 (140 effective + the 2 collar gap); the shaft slides
24–184 (160 of range > the 142 step), so adjacent bands OVERLAP and every
height is reachable: 0 segments → 241–401, 1 → 383–543, 2 → 525–685 (the
user's 655 at ~154 exposure), … Stack per leg (ground up): TPU foot → shaft →
sleeve → k× segment → the instrument SOCKET. The PEDAL BAR (pedal_bar.py)
wraps the shaft's bottom WAIST on the +Y legs, which needs the sleeve to stay
≥ ~30 above the foot — the bands still overlap (184 − 30 = 154 > 142).

Quick-attach thread (per the PC-fan-screw idea): SINGLE-start trapezoidal,
Ø36/Ø30 × 18 mm lead, 25 mm engagement = 1.4 turns. Every junction
(socket→segment, segment→segment, segment→sleeve) uses the same thread, so
legs break down for transport like real steel legs.

ONE SEATED ROTATION per junction — the pedal bar needs a deterministically
clocked leg. Single start = one engagement per revolution (a 2-start thread
seats two ways, 180° apart), and each junction bottoms on a HARD STOP: the
male carries a Ø40 × 2 shoulder COLLAR; the female rim keeps an inner
Ø30.4..36.4 ring that lands on it. The seated angle is therefore fixed by
printed geometry (thread phase + stop height), not by torque feel. The TPU
washer becomes an O-ring-style GLAND: it drops over the male thread onto the
collar and lives in a 2.0-deep recess in the female rim, squeezed a fixed
2.5→2.0 (20%) every assembly — identical preload + damping every time
(anti-unscrew friction no longer depends on how hard you crank). The collar
height IS the old 2 mm washer gap, so the 142 step and the drawn thread
phase (60° = 3 mm at the 18 lead) are unchanged. Loads in play are axial
(nothing torques a leg).

KEYED FINE STAGE: the shaft carries a SINGLE key flat (local -Y, 6.8 from
the axis, full length) and the sleeve bore matches — the fine adjust is
pure Z travel, the foot end is clocked all the way from the chassis, and a
single-D key admits exactly ONE orientation (no 180° ambiguity to get
wrong at assembly). The flat is on the ROOT side (global +Y on the rotated
+Y-rail stacks): the pedal bar's slot is a plain rectangular pocket — Ø20.4
walls register X on the shaft's rounds, the flat back at 7.0 is a proper
FACE seat on the key flat (0.2). The only other shaft feature is the CHORD
NOTCH at z 9..29 (local +Y → the bar-mouth side): its crescent shoulders +
the foot cap set the bar's Z. The notch never enters the sleeve (exposure
stays ≥ ~30). It USED to double as the latch bolt's bearing face, the bolt
head under the upper shoulder being the bar's anti-lift; with the
quick-release gone the notch keeps its other jobs (print-bed face, sleeve
key, X registration) and the bar has no anti-lift.

The BODY STUB joins the body with SLIDE-ALONG-Y OCTAGON JOINERY, no glue
(user: the stub prints ON ITS SIDE for layer strength, so the joint must
assemble along Y): three Y-running octagon ridges on its top face — the
END-WALL ridge (44 continuous inside the endplate's end wall = the
leg↔endplate tie) + two side-wall crossings at the THIRDS of the 34
side-panel overlap (station +0.667/−10.667 toward inboard) — slide in
from outboard until the end-wall ridge butts its blind groove end (outer
faces flush); ONE vertical M4 down the rail web into the inboard ridge
is the Y-retention shear pin. Groove entries in the side face are filled
flush by the ridge ends. The stub is a separate part ONLY because the
chassis can't print below its bed. Stations/centres are computed in
chassis.py (LEG_STATIONS_X / LEG_Y — flush corner columns).

PRINT PLAN (all standing, tubes along Z — the threads, gland, keyed bore and
waist are all round toleranced fits that need vertical circularity; sideways
Z-ovality would eat the 0.2..0.4 fits and roughen the thread flanks):
- SEGMENTS + SHAFT: **PCTG**, not PETG-GF. Standing prints carry bending
  across layer lines, and a kick is ENERGY-limited (~2-5 J): absorbable
  energy scales with strength²/stiffness. PCTG's interlayer strength is
  ~85-90% of bulk AND it yields ductilely at ~40 mm of mid-span flex →
  ~8-9 J before failure; PETG-GF's fibers do nothing across layers
  (interlayer ~15-25 MPa, brittle, high E → ~2 J: a solid kick snaps it at
  a layer line, and a fatter GF tube barely helps). The trade is sway
  (PCTG E ≈ 1.9 vs 4.5 GPa → ~2.3× body sway under knee-lever/bar loads);
  if the first print wobbles, the fix is SECTION (Ø30→Ø36 tube, wall 5,
  matches GF stiffness and keeps the 4× impact margin), not GF.
- SOCKET stays PETG-GF: 32 mm barrel = negligible moment arm across its
  layers, and it lives in the sustained ground-reaction path where GF's
  creep resistance pays. (This whole round-tube family is RETIRED; its
  glued rail joint is not something to revive. DELETED 2026-08-01.)
- SLEEVE was already PCTG (the pinch collar must flex). FOOT/WASHERS TPU.
- Settings that buy Z-strength: LOW part-cooling fan (0-30%), dry filament,
  0.2 layers; the 4 mm tube walls resolve as solid perimeter rings.
- EXCEPTION — the SHAFT prints LYING ON ITS SINGLE KEY FLAT (no threads,
  and standing Ø20×210 is too tall-skinny): the flat IS the bed face,
  continuous full length (the chord notch faces UP — no bridges), and the
  layer lines run ALONG the shaft so kick bending loads bulk material.
  The flat sits 6.8 from the axis so the flat→round junction overhangs
  43° (a 17-across dual-flat put that junction at ~58° — droop city; the
  convex top needs nothing, undersides are what count). 45° chamfers on
  the two bed edges absorb first-layer elephant foot.
- Each junction's TPU gland washer doubles as an impact isolator, and the
  bell-over-spigot overlap double-walls the joint zones — the plain tube
  mid-spans are the governing sections (the PCTG numbers above).
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl, heal
from . import latch as LT

# thread (shared by every junction)
                                       # junction); lead 18 → still 1.4 turns

# hard-stop junction: male shoulder collar + female rim gland (see header).
                                       # junction gap → stack math unchanged
                                       # male crests; open to the outside)

                                       # step/segment = 142 — MUST stay < the
                                       # shaft's slide range so bands overlap
SLEEVE_L = 200.0                       # groove-through. Retraction is
                                       # governed by the BLOCK BUTTING the
                                       # sleeve bottom (E=0), NOT the groove
                                       # top: tip gap at full retraction =
                                       # L−199 = 1.0; travel 147 ≥ the 142
                                       # law. (A +28 "range restoration" was
                                       # dead length — user-caught.)
                                       # Height bands: H = 590 + 142k − E
                                       # foot zone. FINE-STAGE MATH (user):
                                       # travel = the 142 section pitch (so
                                       # height bands are CONTIGUOUS across
                                       # segment-count changes) + 50 minimum
                                       # extended overlap (1.8× the 28-wide
                                       # tenon — mortise proportion; the pinch
                                       # preloads it) + 5 dead = 197 tenon
                                       # rotated +Y-rail stacks aim it at the
                                       # bar MOUTH, i.e. INWARD): the
                                       # print-bed face AND the sleeve key
                                       # (it was also the latch bolt's
                                       # bearing face, before the
                                       # quick-release came out). 6.8
                                       # keeps the flat→round junction at 43°
                                       # (< 45° overhang); single-D = one
                                       # unique orientation. The slot's back
                                       # is ROUND (r10.2 on the Ø20).
                                       # bottom: foot cap top → sleeve's
                                       # lowest reach): the bar plate rides
                                       # here; the TRRS shaft's corner-fill
                                       # extension is limited to this band
FOOT_H  = 12.0
# The shared foot's dovetail tenon stops HERE in local +Y, and the mortise's
# closed end sits 0.5 beyond it (that butt is the foot's Y registration).
#
# It used to reach 15.5. The pedal bar's lid now runs END TO END — over both foot
# stations — and the lid's dovetail occupies the last 4 mm of the +Y face, so a
# tenon poking past the groove floor sat in the lid's path for the whole install
# stroke. A local relief in the lid can't fix a moving part: the clearance has to
# hold everywhere the lid travels, so the tenon gave way instead. Costs 1.9 of a
# 33 tenon (5.8%) on a TPU pad that works in compression; the registration butt
# survives because the mortise end moved with it.
FOOT_TENON_Y1 = 13.6
# stack at k segments: 32 barrel + (k+1)×2 collar gaps + k×140 + 180 sleeve +
# shaft exposure 24..184 + 3 foot floor → height = 217 + 142k + exposure

# socket bracket
# LEG_STATIONS_X (the two corner-station X's, both rails) is COMPUTED in chassis.py
# from the shared endplate<->leg model (chassis.LEG_STATIONS_X = endplate tip -/+
# LEG_W/2 -- FLUSH-X: each leg's outer X face lies ON its endplate's outer face).
# It lives there (not here) because it depends on the endplate tip positions,
# which are chassis constants. Result: (-13.4, -614.2).
# rail joinery (chassis.py cuts the matching slots from these)
                                       # rises 45° toward the face above it






# ── TRRS leg↔body BLIND-MATE (the -X/+Y leg's stack; see pedal_bar.py for
# the bar joint). The chassis-side jack (Tensility 10-03404: Ø9.1 × 39.4
# molded body on 0.91 m of cable) embeds VERTICALLY in the leg socket,
# COAXIAL with the thread; the column-top plug (the second CA-354S,
# recessed in the top segment's spigot bore) blind-mates during the final
# thread turn — lead 18 > insertion 14, the plug's annular contacts spin
# freely inside the jack, so threading twists no wires, and the hard-stop
# clocking fixes the seated depth. Socket-local z (0 = rail bottom):
# seated spigot tip -9.0 (its Ø9.4 retention lip spans -9.5..-9.0); plug
# handle top -9.7 (0.2 under the lip; full barrel exposed), tip +4.8;
# jack mouth -8.2 → 13.0 insertion (the same DELIBERATE 1.0 shortfall as
# the bar joint — it buys the mouth-seat ring its thickness).
CHJ_MOUTH_Z = -9.3            # chassis-jack mouth plane (socket-local;
                              # re-based for the square socket:
                              # spigot top -10, plug tip +3.7)
CHJ_D, CHJ_L = 9.1, 39.4      # 10-03404 molded body




def leg_sleeve() -> cq.Workplane:
    """Slider sleeve (ROUND 3 all-octagon; COVER round: 44 × 40 × 200 — the
    +Y face is THINNED by COVER_T and leg_sleeve_cover restores the 44-sq
    silhouette). On top, the flush octagon SPIGOT into the bottom segment's
    socket (one M4 retention, Ø7 cable bore — one SKU ×4), TRUNCATED at the
    thinned face: the joint's missing stem/lip slab is the COVER'S TONGUE,
    which completes the octagon inside the segment's mortise and locks the
    cover's top end. Below, the fine-adjust way is the full-length OCTAGON
    GROOVE at the SLIDE clearance on the DROPPED profile (stem SH_Y under
    the cover, roof still -14), opening through the thinned face: the shaft
    rides it keyed + captured, stroked along Z (groove top at z -2 roots
    the spigot; retraction stop = the shaft BLOCK butting the mouth face).
    COVER RAILS: two W5 octagon slots at ±CVR_RAIL_X run the face, open at
    the TOP end (the cover slides down), BLIND 0.4 above the mouth = the
    cover's down-stop; covered, the open C-channel becomes a closed BOX
    TUBE — the long-extension bow of the free half-walls is gone (user).
    CLAMP = the EMBEDDED side GIB PAD (unchanged scheme): TPU pad in the +X
    wall bay near the mouth, pressed -X onto the shaft's waist wall by ONE
    M4 GRUB threading the outer +X face; ~500-650 N axial hold vs ~350 N
    worst leg share; a slip only sags to the block-butt stop. The bay's
    print ceiling IS the mortise's upper 45° taper plane EXTENDED — the
    sub-waist profile is UNCHANGED by the drop (same (14.2,-0.4) corner,
    same y = x - 14.6 plane); only the floor moves DOWN to the new dilated
    waist-top corner y 5.3243 (probe-measured, as 7.4245 was before).
    PETG-GF, prints LYING on the thinned +Y face (the truncated spigot's
    flat lands ON the bed — the full stem would float 4 above it).
    Local: Z0 = shoulder (top face); body -Z."""
    body = box_at(SQ_W, SQ_W, SLEEVE_L, z=-SLEEVE_L / 2)
    # full-length slider groove: open at the bottom mouth and through the
    # (thinned) +Y face; top at -2 (the disk under the spigot)
    body = body.cut(_shaft_groove(SLEEVE_L - 1.0)
                    .translate((0, 0, -SLEEVE_L - 1.0)))
    # top spigot (embed 1) + its cable bore + the M4 retention pilot (the
    # segment above brings the clearance bore from its own -Y wall)
    body = body.union(_section_tenon(SEG_PLUG_L + 1.0).translate((0, 0, -1.0)))
    body = body.cut(cyl(SEC_CABLE_D, SEG_PLUG_L + 3.0, z=-2.0)
                    .translate((0, SEC_BORE_Y, 0)))
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.8, 20.0, cq.Vector(7.0, -9.0, 14.0), cq.Vector(0, 1, 0))))
    # FACE THINNING (cover round): shave the whole +Y band above SLV_FACE_Y,
    # body AND spigot in one slab (the spigot's missing slab = cover tongue)
    body = body.cut(box_at(SQ_W + 2.0, COVER_T + 2.0,
                           SLEEVE_L + SEG_PLUG_L + 6.0,
                           y=SQ_W / 2 - COVER_T / 2 + 1.0,
                           z=(SEG_PLUG_L + 4.0 - SLEEVE_L - 2.0) / 2))
    # COVER RAIL SLOTS: open through the face + out the top end, blind 0.4
    # above the mouth (the cover's down-stop; plate lands mouth-flush)
    for gx in (CVR_RAIL_X, -CVR_RAIL_X):
        body = body.cut(_rail_groove(SLEEVE_L - 0.4 + 1.0)
                        .translate((gx, 0, -(SLEEVE_L - 0.4))))
    # GIB-PAD BAY in the +X wall at the waist band, near the mouth: opens
    # into the groove through the waist wall and out the mouth face (-Z,
    # pad loads from below). Ceiling CONTINUES the mortise's upper 45°
    # taper plane, floor ON the dilated waist-top corner (probe-measured
    # for the DROPPED profile: same (14.2,-0.4) / y = x - 14.6 below the
    # waist, floor 7.4245 → 5.3243). 0.4 through-wall ledge ≤ one bead.
    body = body.cut(cq.Workplane("XY")
                    .polyline([(13.8, -0.4), (14.2, -0.4), (16.9, 2.3),
                               (16.9, 5.3243), (13.8, 5.3243)])
                    .close().extrude(29.0)
                    .translate((0, 0, -SLEEVE_L - 1.0)))
    # ONE central M4 GRUB bore (Ø3.4 thread-forming, ~4.6 of PETG-GF thread)
    # through the +X outer wall, opening INTO the bay onto the pad's back.
    # Length 6.6 (was 5.6 — that bore stopped 0.5 SHY of the 16.9 bay wall:
    # a solid web the grub could never push through; latent until this round)
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.7, 6.6, cq.Vector(SQ_W / 2 + 1.0, 3.5, -SLEEVE_L + 15.0),
        cq.Vector(-1, 0, 0))))
    return heal(body)


def leg_pinch_gib() -> cq.Workplane:
    """TPU pinch GIB PAD ×4 (the sleeve's embedded shaft clamp): a grippy
    flat pad in the +X wall bay, pressed -X by ONE central grub screw onto
    the shaft octagon's +X WAIST WALL (flat-on-flat, 0.3 drawn standoff;
    the shaft then bears its -X wall + diagonals). TPU = the preload SPRING
    (defined compression survives creep) AND the friction surface (µ~0.7).
    A shallow dimple seats the grub tip. Slides in from the sleeve's mouth.
    COVER round: the waist band dropped with the slider profile — the pad
    tracks the new bay (floor 5.1, grub axis y 3.5). Prints flat.
    Local: sleeve frame, z 0..20."""
    b = (cq.Workplane("XY")
         .polyline([(14.3, 0.12), (16.5, 2.32), (16.5, 5.1), (14.3, 5.1)])
         .close().extrude(20.0))
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCone(
        1.6, 0.2, 1.2, cq.Vector(16.6, 3.5, 10.0), cq.Vector(-1, 0, 0))))
    return heal(b)


def leg_sleeve_cover() -> cq.Workplane:
    """PETG-GF sleeve COVER ×4 (user: at long extension the open C-channel
    is a poorly-supported span that can bow outward — and the slack coil
    shows). A 44-wide × COVER_T plate rides the sleeve's thinned +Y face on
    two W5 octagon RAILS (slid DOWN from the top end), closing the channel
    into a box tube and restoring the flush 44-sq leg look; it also hides
    the coil. Captive with ZERO fasteners: the TONGUE (14 × 4 × 28)
    continues past the top edge into the segment's mortise LIP BAND — the
    slab the truncated spigot leaves void — completing the octagon joint,
    flush with the segment's outer face, and trapping the cover once the
    segment is mated (up-play 0.4 to the tongue tip); down-stop = the
    rails' blind slot ends 0.4 above the mouth, landing the plate flush
    with the mouth face (the shaft block butts sleeve + cover evenly).
    Prints LYING on the outer (y 22) face: rails grow up with 45° flares,
    the tongue is plate-thickness. Local: sleeve frame — plate y 18..22,
    z -200..-0.2 (0.2 shy of the segment butt so the structural shoulder
    never rides the cover); rails z -199.6..-0.2; tongue z -0.2..28."""
    b = box_at(SQ_W, COVER_T, SLEEVE_L - 0.2,
               y=SQ_W / 2 - COVER_T / 2, z=-(SLEEVE_L + 0.2) / 2)
    b = b.union(box_at(14.0, COVER_T, CVR_TNG_L + 0.2,
                       y=SQ_W / 2 - COVER_T / 2, z=(CVR_TNG_L - 0.2) / 2))
    for gx in (CVR_RAIL_X, -CVR_RAIL_X):
        b = b.union(_rail_tenon(SLEEVE_L - 0.6)
                    .translate((gx, 0, -(SLEEVE_L - 0.4))))
    return heal(b)


def leg_shaft() -> cq.Workplane:
    """-Y shaft ×2 (user: ALL FOUR legs share the wide|narrow|wide look
    at EQUAL heights): the same 197 tenon over a 44-sq terminal block —
    here 91 tall and printed ONE SOLID (no joint down low; nothing below
    creates lateral force), so block 91 + foot 12 = 103 matches the +Y
    stack's block 48 + tower 24 + bar 19 + foot 12. Shared TPU foot's
    dovetail mortise underneath. ROUND 3: the tenon is the W28 flush
    OCTAGON prism (_shaft_prism — stem base on local +Y, riding the
    sleeve's open groove at the slide clearance; keyed + captured by
    shape). COVER round: the prism stem dropped to SH_Y (17.8) to run
    under the sleeve cover, so the BLOCK's +Y face is TRUNCATED to the
    SAME plane — and (user, symmetry round) the block now insets 4.2 on
    ALL FOUR sides: BLK_W 35.6 square, centred — the one-sided cut read
    asymmetrical. +Y face = the stem plane, so the ONE-plane print bed
    comes free; the TPU foot stays 44-sq (a proud ground boot, and it
    also serves the full-depth bar — its dovetail tail is trimmed to
    stay inside the smaller block). PETG-GF; 288 long — prints LYING on
    the stem face, laid DIAGONAL in plan. Z0 = block bottom."""
    body = _shaft_prism(TALL_SHAFT_L)
    body = body.union(box_at(BLK_W, BLK_W, TALL_BLOCK_H, z=TALL_BLOCK_H / 2))
    body = body.cut(foot_mortise_cutter())
    return body


# (The X-axis TRRS dock block that lived here is GONE with the quick-release:
# it described a bar-mounted LATCH SLIDER carrying the male plug and driving it
# along X, and its seven constants — TRRS_Z, TRRS_JACK_*, WIRE_BORE_D,
# SHELF_Z0/1 — were dead, each with no reference but its own definition. The
# live blind-mate is the VERTICAL one: a captive CA-354S pressed straight up,
# see leg_shaft_trrs / leg_head. The SHELF was that design's anti-lift.)


TENON_L = 197.0                # every shaft's sliding tenon: travel 142
                               # + overlap 50 + 5 dead (the fine-stage law)
BLOCK_H = 48.0                 # +Y 44-sq terminal block = the bar-joint
                               # mortise (socket 41, spigot 38 — reduced
                               # overlap per user: this joint's moment is
                               # small, and the wide stack must stay
                               # within PEDAL_ASSEMBLY_Z_HEIGHT (75 above
                               # the bar top) for the future pedals)
# -Y 44-sq terminal block, printed SOLID. The user requires EQUAL wide-section
# heights on all four legs, so this block must match what the +Y side stacks
# under its own block: bar + tower band. DERIVED (was a hardcoded 91.0 that
# silently encoded a 19.0 bar) — the bar grew to 27.0 when its lid moved to the
# +Y face, and the equality has to follow it rather than be re-typed.
TALL_BLOCK_H = D.PEDAL_BAR_H + D.PEDAL_TOWER_BAND + BLOCK_H     # 99.0 (was 91.0)
BAR_STUB_Z0  = D.PEDAL_BAR_H + D.PEDAL_TOWER_BAND               # 51.0: the bar
                               # tower's seat plane, in the bar's own frame.
                               # pedal_bar re-exports this as STUB_Z0; it lives
                               # here so SHORT_SHAFT_L below can close the loop.
TALL_SHAFT_L = TENON_L + TALL_BLOCK_H   # 296: prints LYING on the bed
                               # DIAGONAL ((296+44)/sqrt(2) = 240 < 255),
                               # like the bar pieces
SHORT_SHAFT_L = TALL_SHAFT_L - BAR_STUB_Z0   # 245.0: +Y shafts start BAR_STUB_Z0
                               # up the tower, so they end short by exactly that
                               # much and both sides' tops land level. Was a
                               # hardcoded 245.0 — it happens to be unchanged
                               # (block and seat plane both grew by 8), which is
                               # precisely why it needed deriving: a coincidence
                               # that survives one edit will not survive the next.
assert abs(D.PEDAL_BAR_H + D.PEDAL_TOWER_BAND + SHORT_SHAFT_L - TALL_SHAFT_L) < 1e-9, (
    "the +Y stack (bar + tower band + short shaft) must equal the -Y stack "
    "(tall shaft) or the instrument sits crooked")


def foot_mortise_cutter() -> cq.Workplane:
    """Underside DOVETAIL mortise for the shared TPU foot tenon (slides
    in from -Y local; grip + compression = no fastener). Cut at the
    origin; z0 = the block's bottom face."""
    return (cq.Workplane("XZ")
            .polyline([(-15.0, 0.0), (-13.4, 6.0), (13.4, 6.0),
                       (15.0, 0.0)])
            .close().extrude(40.0).translate((0, FOOT_TENON_Y1 + 0.5, 0)))


def leg_shaft_short() -> cq.Workplane:
    """+Y shaft ×2: the 28×26 tenon ends in the 44-sq terminal BLOCK
    whose downward socket + ledge take the bar tower's spigot/bolt.
    ROUND 3: tenon = the W28 flush OCTAGON prism; the bar-joint socket =
    the flush octagon mortise (the lying shaft's +Y bed face flipped the
    old house floor into a 28-wide ceiling bridge), ledge pocket in the
    thick -Y wall at x +8 (matches the tower's mirrored channel) + tail
    window through the face skin. Passive. COVER + SYMMETRY rounds: the
    block is BLK_W 35.6 square (4.2 inset on all four sides — user: the
    +Y-only truncation looked asymmetrical; +Y face = the stem plane, so
    the flat bed comes free). The bar tower's tenon is shaved to the
    same +Y plane and lands flush in the opened socket (capture keeps
    3.5 of lip band; waist-vs-slit unchanged; socket X walls 3.6, -Y
    back wall 3.5). Z0 = the block's mouth face."""
    body = _shaft_prism(SHORT_SHAFT_L)
    body = body.union(box_at(BLK_W, BLK_W, BLOCK_H, z=BLOCK_H / 2))
    body = body.cut(_section_mortise(length=39.4).translate((0, 0, -1.0)))
    # LATCH (female half) for the bar joint — same cutter as the body stub. This
    # is the THIN wall of the pair (BLK_W leaves 3.7 from the apex), which is what
    # capped HOOK_ENGAGE at 1.8 for BOTH joints; 2.4 mm of wall survives here.
    body = body.cut(LT.female_cutter(engage_z=0.0, cx=LT.LX_TOWER))
    return body


def leg_shaft_trrs() -> cq.Workplane:
    """The -X/+Y leg's shaft (ROUND 4): leg_shaft_short() + the SECOND
    vertical TRRS blind-mate — a 10-03404 jack (mouth DOWN) coaxial above
    the socket roof, mating the bar stub's captive CA-354S plug on the
    same straight press that seats the joint. Its factory cable runs UP
    the column to the mini junction PCB. The side dock / carrier PCB /
    corner channel of the sideways design are GONE."""
    body = leg_shaft_short()
    # vertical jack way, Ø9.7 CLEAN THROUGH to the tenon top: the leg
    # EXTENSION cable's molded jack barrel (10-03404-class envelope,
    # verify the SKU) loads DOWN from the shaft's open top onto the
    # integral mouth-seat BOSS (withdrawal backstop); a pressed
    # jack_seat_ring ABOVE it takes insertion. Jack mouth +42.7, plug tip
    # +55.7 = 13.0 insertion on the same press that seats the joint.
    # TRRS axis at local (-5, +13): x -5 kept clear of the old latch bolt
    # (global +5 after the 180 placement); +13 rides the fat flare band —
    # the way keeps a ~1.3 wall to the tenon's taper flank
    body = body.union(cyl(13.0, 1.9, z=38.2).translate((-5.0, TRRS_DY, 0)))
    body = body.cut(cyl(4.8, 2.0, z=38.0).translate((-5.0, TRRS_DY, 0)))
    body = body.cut(cyl(9.7, SHORT_SHAFT_L - 38.7 + 2.0, z=38.7)
                    .translate((-5.0, TRRS_DY, 0)))
    return body


# ═══ SQUARE-LEG REDESIGN (2026-07-09, user-directed; supersedes the round
# tubes above — old generators kept during the staged swap) ══════════════
# Constant 44×44 outside, PRINTED LYING on a face in PETG-GF (layer lines
# run ALONG the leg → kick bending loads bulk material — the standing-
# print interlayer veto on GF is gone; square-44 ≈6× the Ø30 tube's
# stiffness by geometry, GF adds ~2.4× modulus). Threads can't print
# lying, so each body originally took two STANDING-printed PCTG THREAD
# COUPLERS glued into its square core ends — RETIRED at round 3 below
# (threadless, and the project is glue-free). Internal
# joint geometry — Ø36/30 single-start thread, Ø40 collar hard stop, TPU
# gland washer — is UNCHANGED, so the 142 step and clocking phase carry
# over. The face CABLE CHANNEL + sliding lid (pedal-bar pattern) aligns
# across joints BECAUSE of the deterministic clocking: the cable lays in
# AFTER column assembly. Top joint = the LEG HEAD (separate part, passive
# octagon spigot into the stub's socket) — see leg_head().
SQ_W = 44.0                    # outer square width (uniform, = old bell OD)
                               # at round 3; 45° crown corners print lying)
SEG_BODY_L = 142.0             # ROUND 3 (user): NO THREADS, NO TPU
                               # GASKETS in the square legs — the thread
                               # couplers and washers are GONE. Each body
                               # is the full 142 pitch with an INTEGRAL
                               # 31.7-sq male PLUG (28 long) on its top
                               # end sliding into the part above; the
                               # butt of the shoulder faces is the hard
                               # stop, clocking is geometric, and ONE M4
                               # per joint is extraction retention only
                               # (user rule: joinery takes the force).
SEG_PLUG_L = 28.0              # male plug engagement (sockets are 30)

# ── SECTION JOINT (2026-07-20, user-directed): the stackable section joint is
# now the cadkit OCTAGON ("stop-sign"/"dull arrowhead") slide joint — the same
# family the leg↔BODY joint uses — REPLACING the old _house plug/socket, so the
# whole leg column prints LYING ON ITS INNER-Y FACE (layer lines run along the
# leg → kick/bending loads stay within layers). Unlike the body joint (slides
# along Y), sections connect via Z (stacking): the octagon spigot sticks out the
# top Z-end and the socket swallows it on a straight -Z drop. Authored ONCE with
# the flat octagon STEM BASE toward local +Y and the point toward local -Y;
# build.py's 180°-per-side leg rotation then lands the base on the INNER face
# (the print bed) for BOTH Y-sides. See _section_tenon / _section_mortise.
SEC_W       = 28.0    # octagon flat-to-flat across local X (= the old house's X
                      # footprint); 8 mm wall to the ±22 X faces
SEC_H       = 36.0    # profile HEIGHT (the cadkit room bound past the mating
                      # plane — user: pass the ACTUAL room): 44 leg depth − ~7
                      # structural outer wall (2 perimeters + infill; also the
                      # sleeve's C-channel wall) − drop/dilation. Width-driven
                      # minimum 22.24; the extra 13.76 grows the two verticals
                      # to 7.68 each (deeper lip engagement + flank bearing)
SEC_TEN_L   = 28.0    # spigot engagement along Z (= the old SEG_PLUG_L)
SEC_MOR_L   = 28.4    # socket depth: spigot 28 + a 0.4 tip gap (user: near-flush
                      # tips — the tolerance slack belongs HERE, never at the big
                      # shoulder faces, which are the ground-reaction hard stop)
# FLUSH AT THE BED FACE (user round 2): the joint is NOT hidden inside the leg.
# The tenon's flat STEM BASE lies exactly ON the local +Y face = the print bed
# (a floating inset base would be an unprintable mid-air flat on the side-lying
# spigot), and the mortise opens THROUGH that face as an octagon-profile groove
# — the open air gap the next tenon slides into. Capture survives: the face
# slit is the 14-wide stem, the 28 waist can't pass it. Profile spans local
# y +22 (base) .. -0.24 (point); the outer (-Y) wall keeps ~21 of material.
SEC_BORE_Y  = 13.0    # wired: cable-bore centre (in the fat flare band; clears
                      # the M4 at x+7 and stays inside the profile walls)
SEC_CABLE_D = 7.0     # wired leg: axial cable bore through the spigot + socket roof
# ROUND 3 (user): EVERY leg joint is this flush octagon now — sections, the
# head↔body stub, the sleeve↔segment, the shaft↔sleeve fine-adjust
# SLIDER, and the bar tower↔block joint (the shaft lying on +Y flipped the old
# house sockets' flat floors into unprintable 28-wide ceiling bridges). The
# slider pair uses a looser SLIDE clearance; the fixed joints keep the 0.1
# assembly fit. TRRS blind-mate axes move into the profile's fat flare band
# (y +13 — the old y-0 axes have no material around them in a bed-flush
# octagon); the world couplings (chassis jack well, bar tower ways, dummy
# placements) shift with them.
SH_CLR      = 0.2     # shaft↔sleeve octagon SLIDE fit (per side; the fine
                      # stage strokes, unlike the assemble-once 0.1 joints)
TRRS_DY     = 3.5     # TRRS axes ride the profile's deep waist (also the
                      # groove's inscribed-circle centre): head/stub at local
                      # (+TRRS_DX, +TRRS_DY), shaft/tower at (-TRRS_DX,
                      # +TRRS_DY). At SEC_H 36 the Ø11/Ø13 ways clear the
                      # orange/taper flanks by ~9 and the waist wall by ≥2.5


# ── SLEEVE COVER (2026-07-21, user): at long extension the sleeve's open
# C-channel is a poorly-supported span — the two half-walls can bow outward
# (and the slack coil shows through the opening). Fix: the sleeve's +Y face
# band is THINNED by COVER_T (outer becomes 44 × 40) and a separate 44-wide
# COVER PLATE (leg_sleeve_cover) slides down two W5 octagon RAILS, closing
# the C into a box tube and restoring the 44-sq silhouette — nothing steps
# past the leg profile. The SLIDER octagon drops with the face (the shaft
# must run UNDER the solid plate): stem plane SH_Y, roof pinned at -14 (the
# section joints' roof — the whole sub-waist profile, and with it the gib
# bay's taper-plane ceiling, is UNCHANGED). The sleeve's top spigot is
# TRUNCATED at the thinned face; its missing stem/lip slab is the cover's
# TONGUE, which completes the octagon inside the segment's mortise and
# locks the cover's top end — no cover fasteners at all.
COVER_T    = 4.0      # cover plate thickness = the face-thinning depth
SLV_FACE_Y = SQ_W / 2 - COVER_T        # 18.0: the sleeve's thinned +Y face
SH_Y       = SLV_FACE_Y - SH_CLR       # 17.8: slider stem plane (0.2 running
                                       # clearance under the cover's inner face)
SH_H       = SH_Y + 14.0               # 31.8: slider octagon height (roof -14)
CVR_RAIL_X = 17.0     # rail centres ±x: slot spans 14.4..19.6 dilated — 7.2
                      # web to the groove's lip band, 2.4 outer ±X skin
CVR_RAIL_W = 5.0      # rail octagon flat-to-flat (cadkit h_min 4.95 at n0.8)
from cadkit.joinery import PrintSpec as _PrintSpec, joint as _joint
# cadkit collapsed the per-family entrypoints into ONE `joint()` (you describe the
# SITE, it picks the geometry), so this file now says how its halves PRINT instead
# of naming the octagon. Both are PETG-GF printed -Z->+Z.
_UP = _PrintSpec(nozzle=0.8, material="PETG-GF", facing="up")


def _octagon_height(width, nozzle=0.8, clearance=0.1, height=None):
    """Height of a joint of this width — the sizing figure the cover rail needs."""
    return _joint(width, 1.0, tenon=_UP, mortise=_UP, clearance=clearance,
                  depth=height).height
CVR_RAIL_H = _octagon_height(CVR_RAIL_W, 0.8)   # ASK cadkit, don't hand-write it: the
#   octagon's height is not free — 45° diagonals plus two-nozzle verticals set a floor
#   per width, and this was a hard 5.0 until cadkit raised the verticals to the
#   two-bead quality tier and started REJECTING it (min for W5 is 6.591). Deriving it
#   means the next tightening moves the groove instead of breaking the build.
CVR_TNG_L  = 28.0     # cover tongue engagement (= SEC_TEN_L; 0.4 tip gap in
                      # the segment's 28.4 socket = the cover's up-play)
BLK_W      = 2 * SH_Y # 35.6: the shaft terminal blocks' square (user: the
                      # cover side's 4.2 inset on ALL FOUR sides — the one-
                      # sided cut looked asymmetrical; the +Y face IS the
                      # slider stem plane, so the flat print bed comes free)


def _rail_tenon(length: float) -> cq.Workplane:
    """Cover-rail male: W5 octagon rib on the cover's inner face (stem rooted
    at the thinned-face plane, point -Y into the sleeve wall), z 0..length;
    caller translates to ±CVR_RAIL_X. Prints growing UP off the lying cover
    plate: neck, 45° flare out, 45° back to the 0.8 tip — no overhang."""
    return (_joint(CVR_RAIL_W, length, tenon=_UP, mortise=_UP, clearance=0.1, depth=CVR_RAIL_H).tenon(root=0.0)
            .rotate((0, 0, 0), (0, 1, 0), -90)
            .rotate((0, 0, 0), (0, 0, 1), 90)
            .translate((0, SLV_FACE_Y, 0)))


def _rail_groove(length: float) -> cq.Workplane:
    """Cover-rail female: the matching W5 slot, opening through the thinned
    +Y face — on the lying sleeve a standard mortise-at-the-bed (0.8 roof
    bridge at y 12.9). Z-running; caller translates/limits it."""
    return (_joint(CVR_RAIL_W, length, tenon=_UP, mortise=_UP, clearance=0.1, depth=CVR_RAIL_H).mortise(drop=2.0)
            .rotate((0, 0, 0), (0, 1, 0), -90)
            .rotate((0, 0, 0), (0, 0, 1), 90)
            .translate((0, SLV_FACE_Y, 0)))


def _house(w: float, floor_y: float, wall_top_y: float,
           length: float) -> cq.Workplane:
    """HOUSE-profile prism (user rule: every joint cross-section is a
    house — vertical walls, 45° gable to the apex, flat floor — so the
    LYING bodies print with ZERO overhang; the gable points AWAY from
    the print face). A house also admits exactly ONE orientation, so it
    IS the clocking key. Extruded +Z from 0."""
    hw = w / 2
    return (cq.Workplane("XY")
            .polyline([(-hw, floor_y), (hw, floor_y), (hw, wall_top_y),
                       (0.0, wall_top_y + hw), (-hw, wall_top_y)])
            .close().extrude(length))


def _section_tenon(length: float = SEC_TEN_L) -> cq.Workplane:
    """Section-joint male SPIGOT: the cadkit octagon TENON rotated so its slide
    axis is +Z (stacking), point toward local -Y, and the flat STEM BASE lying
    EXACTLY ON the local +Y face (y = SQ_W/2) — the print bed of the side-lying
    leg (user: the stem must be flat against the bed; an inset base would be a
    floating flat). root=0: any root would poke past the leg face. Callers
    embed 1 along Z for the volumetric fusion instead. Base plane at z=0."""
    return (_joint(SEC_W, length, tenon=_UP, mortise=_UP, clearance=0.1, depth=SEC_H).tenon(root=0.0)
            .rotate((0, 0, 0), (0, 1, 0), -90)
            .rotate((0, 0, 0), (0, 0, 1), 90)
            .translate((0, SQ_W / 2, 0)))


def _section_mortise(length: float = SEC_MOR_L, drop: float = 2.0) -> cq.Workplane:
    """Matching section SOCKET cavity (the octagon MORTISE, same rotation), its
    mating plane on the local +Y face so the `drop` opens the cavity THROUGH
    that face — the visible groove/air gap the tenon needs (its bed-flat stem
    base can't be walled in). The 14-wide face slit still captures the 28
    waist. Cut from the part's bottom Z-end; callers translate to (0,0,z_open)
    with a small -Z overshoot; the far (+Z) end inside is the stop wall."""
    return (_joint(SEC_W, length, tenon=_UP, mortise=_UP, clearance=0.1, depth=SEC_H).mortise(drop=drop)
            .rotate((0, 0, 0), (0, 1, 0), -90)
            .rotate((0, 0, 0), (0, 0, 1), 90)
            .translate((0, SQ_W / 2, 0)))


def _shaft_prism(length: float) -> cq.Workplane:
    """The FINE-ADJUST SLIDER's male: the same flush W28 octagon profile as the
    section joints but at the SLIDE clearance (SH_CLR) — the shaft is this
    prism, riding the sleeve's matching full-length groove. COVER round: stem
    plane at SH_Y (17.8 — the shaft runs 0.2 under the cover plate), roof
    still -14 → height SH_H. The stem base is the lying shaft's print bed,
    z 0..length."""
    return (_joint(SEC_W, length, tenon=_UP, mortise=_UP, clearance=SH_CLR, depth=SH_H).tenon(root=0.0)
            .rotate((0, 0, 0), (0, 1, 0), -90)
            .rotate((0, 0, 0), (0, 0, 1), 90)
            .translate((0, SH_Y, 0)))


def _shaft_groove(length: float, drop: float = 2.0) -> cq.Workplane:
    """The slider's female: octagon mortise at SH_CLR on the DROPPED slider
    profile (SH_Y/SH_H), open through the sleeve's thinned +Y face (the
    dilated opening lands flush at SLV_FACE_Y — hidden under the cover once
    it's on). Z-running; callers place/limit it so it never severs the
    sleeve's top spigot."""
    return (_joint(SEC_W, length, tenon=_UP, mortise=_UP, clearance=SH_CLR, depth=SH_H).mortise(drop=drop)
            .rotate((0, 0, 0), (0, 1, 0), -90)
            .rotate((0, 0, 0), (0, 0, 1), 90)
            .translate((0, SH_Y, 0)))


# (CH_MOUTH/CH_DEEP retired with the face channel + leg_lid — user: the cable
# runs up the CENTER of the column through the flush-octagon joints' Ø7 bores;
# in-column access requires disassembly, accepted.)


def _sq_body(length: float, channel: bool = False) -> cq.Workplane:
    """Square leg body stock: 44×44×length (prints lying on the +Y face).
    channel=True (the WIRED leg's bodies ONLY — user: legs are otherwise
    identical) hollows the house CORE (cable + slack coil + junction PCB)
    and bores the Ø7 cable ways through the cap and socket roof — the cable
    runs entirely INSIDE the column, through every joint's center. The old
    lidded face channel + dive holes are gone. Z0 = bottom."""
    b = box_at(SQ_W, SQ_W, length, z=length / 2)
    # bottom SOCKET (both variants): the octagon section MORTISE, opening
    # through the bottom Z-face (1 below for a clean mouth); its +Z end is the
    # stop wall. The old house socket doubled as the wired core — now the socket
    # and the core cavity are separate so the joint is a clean octagon.
    b = b.cut(_section_mortise(length=SEC_MOR_L + 1.0).translate((0, 0, -1.0)))
    if channel:
        # WIRED body: above the socket, a house CORE cavity hosts the cable +
        # slack coil. Because the body now lies on its +Y (inner) face, the
        # gable must point -Y (up in the build) — so author the +Y-gable house
        # and rotate it 180° about Z (floor lands near the +Y bed, apex at -Y).
        b = b.cut(_house(28.0, -16.0, 2.0, length - SEC_MOR_L - 3.0)
                  .rotate((0, 0, 0), (0, 0, 1), 180)
                  .translate((0, 0, SEC_MOR_L + 1.0)))
        # Ø7 cable ways: link the socket roof up into the core (cable rises from
        # the incoming spigot's bore) and through the solid top CAP that roots
        # the spigot. The old 20-wide slack-coil-through-joint way is gone (the
        # octagon stem is only 14 wide) — thread the cable straight, coil in core.
        b = b.cut(cyl(SEC_CABLE_D, 6.0, z=SEC_MOR_L - 2.0)
                  .translate((0, SEC_BORE_Y, 0)))
        b = b.cut(cyl(SEC_CABLE_D, 8.0, z=length - 6.0)
                  .translate((0, SEC_BORE_Y, 0)))
    # (the old +X face cable channel + lid + dive holes are GONE — user: with
    # the Ø7 bores through every flush-octagon joint the cable simply runs up
    # the CENTER of the column; access requires disassembly, accepted)
    # integral male SPIGOT on the top end: the octagon section TENON, embedded
    # 1 along Z into the body for volumetric fusion (root=0 — the flush base
    # can't extend past the leg face). Wired: a Ø7 axial cable bore, open out
    # the tip; plain: solid.
    plug = _section_tenon(SEG_PLUG_L + 1.0).translate((0, 0, length - 1.0))
    if channel:
        plug = plug.cut(cyl(SEC_CABLE_D, SEG_PLUG_L + 3.0, z=length - 2.0)
                        .translate((0, SEC_BORE_Y, 0)))
    b = b.union(plug)
    # M4 retention (user rule: joinery takes the force, the screw only stops
    # extraction): ONE M4×25 button per joint from the OUTER (-Y) face — the +Y
    # face is the open groove, so the screw comes through the point-side wall
    # (~7.3 at SEC_H 36). At x +7 (clears the Ø7 cable bore at x ±3.5): Ø4.5
    # clearance through our wall over the INCOMING spigot (bottom socket) +
    # Ø3.6 thread-forming pilot crossing our OWN spigot (blind — stops 9 shy
    # of the bed face, so the inner face stays clean).
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.25, 17.0, cq.Vector(7.0, -SQ_W / 2 - 1.0, 14.0),
        cq.Vector(0, 1, 0))))
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.8, 20.0, cq.Vector(7.0, -9.0, length + 14.0),
        cq.Vector(0, 1, 0))))
    return b


def leg_seg_body() -> cq.Workplane:
    """PETG-GF square segment BODY ×6 (the plain legs; prints LYING on a
    face — layer lines along the leg). Takes one male + one female thread
    coupler, M4-retained in the square core ends."""
    return _sq_body(SEG_BODY_L)


def leg_seg_body_ch() -> cq.Workplane:
    """PETG-GF square segment BODY, CORED ×2 (the wired -X/+Y leg only):
    hollow house core + Ø7 through-joint cable ways — the cable runs up
    the column CENTER (no face channel/lid; access = disassembly)."""
    return _sq_body(SEG_BODY_L, channel=True)






# (leg_lid RETIRED with the face channel — the wired cable runs up the
# column CENTER through the flush-octagon joints' Ø7 bores.)


# ── stage 2: the leg↔body top joint ────────────────────────────────────
# ── the leg↔body joint (FLUSH round, replaces the 52-sq outset socket):
# a 44-sq BODY STUB per corner — "a regular leg section, as short as
# possible" (user) — semi-permanently attached via TWO tall octagon
# WALL TENONS (cadkit.joinery stop-sign profile, coupon-validated)
# sliding UP into closed mortises in the rail band / kept shells, ONE
# vertical M4 dropped down the rail web (head hidden under the deck) =
# extraction retention only. Below the body the stub carries the SAME
# passive octagon socket as the leg↔bar joint; the leg head enters it
# exactly like a bar tower.
#
# NO Z RETENTION (user, this round). The seatbelt quick-release that used
# to lock this joint — sliding bolt, release button, and the bearing
# ledge/tail window each socket cut for them — is GONE from BOTH joints,
# back to a blank slate. What remains is pure joinery: the octagon spigot
# and mortise fix X, Y and rotation and carry the load, but nothing holds
# the joint together along Z, so a leg pulls out as easily as it goes in.
# Whatever replaces it gets a clean, fully passive socket to work against.
HEAD_BODY_L = 42.0             # head body (30-deep plug socket + plug seat)
STUB_H = 48.0                  # stub protrusion below the body bottom =
                               # the disassembled-instrument z cost (the
                               # old 52-sq socket hung 50)
# Y-INSTALL joinery (user: the stubs print ON THEIR SIDE for layer
# strength, so the stub<->body joint SLIDES ALONG Y, not Z): the stub top
# carries THREE octagon RIDGES running the full 44 local y, roof UP.
# Grooves in the body bottom open at the instrument's +-Y side face; the
# stub slides in from outboard until the end-wall tongue tip butts its
# blind groove end (= outer faces flush); ONE vertical M4 down the rail
# web into the inboard ridge is the Y-retention SHEAR PIN, and ONE
# horizontal M4 through the endplate's end face cross-pins the tongue.
# Every groove entry on the side face is FILLED flush when seated.
STUB_WALL_D = D.WALL_THICKNESS # endplate end-wall depth (= CH.T -- DERIVED now; it was a
                               # hardcoded 10.0 whose comment already claimed it tracked the
                               # chassis wall, so it silently would not have): the
                               # outboard 10 of the stub's 44 is under the
                               # end wall; the remaining 34 is the leg<->
                               # SIDE-PANEL overlap.
# CROSSING-ridge stations (user): split the side-panel overlap (34, from
# the end-wall inner face at local eps*12 to the leg's inboard face at
# local -eps*22) into THIRDS and put a ridge at each dividing point:
# local x = eps*(12 - 34/3) = eps*0.667 and eps*(12 - 68/3) = -eps*10.667
# (globally: keyhead -614.87/-603.53, bridge -12.73/-24.07). Each crosses
# the side-wall band through an octagon through-hole (kept shell / true
# rail) and tunnels whatever chassis crosses the corner; the INBOARD one
# (-eps*10.667) takes the M4 pin.


def _cross_x(eps: float) -> tuple:
    """The two crossing-ridge |local-x| stations for an end-wall side."""
    inner = SQ_W / 2 - STUB_WALL_D              # end-wall inner face (12)
    span = SQ_W - STUB_WALL_D                   # side-panel overlap (34)
    return (eps * (inner - span / 3.0), eps * (inner - 2.0 * span / 3.0))
STUB_TEN_W = 8.0               # CROSSING-ridge octagon width (flat-to-
                               # flat), profile height 7.24
STUB_RIDGE_EP = 17.0           # end-wall TONGUE |local x| (= the endplate
                               # end wall's centreline, tip - 5): runs the
                               # FULL 44 inside the endplate's wall = the
                               # leg<->ENDPLATE joint (user), blind inboard
                               # end = the flush hard stop
# END-WALL TONGUE-AND-GROOVE (user: simple, not octagon, + one M4 lock
# screw along x per leg). The 10-thick end wall is SPLIT EVENLY between
# the two parts — tongue 5 = the two groove cheeks 2.5 + 2.5 — so tenon
# shear area equals the mortise cheeks' combined section (the same
# analytic even-split rule as the octagon stem = width/2: the weaker
# member is maximized). Height 8 leaves 2.2 of cover above/below the
# Ø3.6 M4 pilot crossing at mid-height. Fit = the PETG-GF coupon 0.1/side
# (groove 5.2 wide x 8.1 deep).
STUB_TNG_W = D.WALL_THICKNESS / 2   # end-wall tongue thickness (x) = CH.T/2 (was hardcoded 5.0)
STUB_TNG_H = 8.0               # end-wall tongue height above the stub top
# Crossing-ridge z placement: the octagon profile's z=0 IS the mating
# plane (the stem runs from -root below it, through it, to the waist
# above), so the ridge sits at exactly z = STUB_H and the groove at
# exactly z = Z_BOT — the built-in root/drop do the embedding/opening.
# Waist top (roof) at +7.24, groove roof +7.34; the stub top riding the
# wall bottoms is the Z datum. (A -0.3 'extra embed' here mis-aligned the
# 45° flanks by 0.2 past the 0.1 fit — probe-caught at all 8 corners.)
TRRS_DX = 5.0                  # the flipped TRRS axis (local +x offset).
                               # WIRED stub, Y-INSTALL: NOTHING protrudes
                               # above the stub top any more (user killed
                               # the tall jack fin) — the naked 10-03404
                               # DROPS INTO the Ø9.7 way from above AFTER
                               # the stub seats (the keyhead foot hollow
                               # opens east into the open-top chassis box
                               # during assembly, and the WIDE corner
                               # rib's Ø10.5 well guides it + sleeves the
                               # barrel), seats on the mouth boss, and is
                               # clamped by an M2 SET SCREW reached from
                               # the stub's inboard-y face (below the
                               # body — accessible even assembled).


def _stub_ridge(length: float = SQ_W) -> cq.Workplane:
    """One octagon RIDGE as a Y-RUNNING prism (slide axis +y), roof UP,
    width along x, base (stem plane) at z 0, extruded +y from y 0.
    cadkit.joinery builds the profile in Y-Z extruded along X; rotate
    Z(+90) maps the extrusion to +y and the width onto x."""
    return (_joint(STUB_TEN_W, length, tenon=_UP, mortise=_UP, clearance=0.1)
            .tenon()
            .rotate((0, 0, 0), (0, 0, 1), 90))


def _groove(length: float) -> cq.Workplane:
    """The matching cavity (ridge dilated 0.1/side, the coupon fit),
    Y-running, roof up, opening DOWNWARD at its base plane (the mortise's
    stem slit extends 2.1 below it — over the sliding plane that is air).
    Callers translate it to (ridge x, y0, Z_BOT)."""
    return (_joint(STUB_TEN_W, length, tenon=_UP, mortise=_UP, clearance=0.1)
            .mortise()
            .rotate((0, 0, 0), (0, 0, 1), 90))


def corner_groove_negatives(station: float, ly: float, syg: float,
                            egx: float,
                            z_bot: float,
                            relief: bool = True) -> list:
    """WORLD-space groove negatives for ONE leg corner — the ONE source
    both the chassis and the endplates cut from, so cross-part grooves
    (shell<->endplate, tab<->channel, wide corner rib) align by
    construction. syg = outboard y sign (+1 for +Y legs), egx = outboard
    x sign (+1 at the bridge end). Per corner: the END-WALL groove (blind
    at the stub's inboard y face = the flush hard stop, open + 1
    overshoot outboard) and two CROSSING grooves (overshot both ends).
    (No fin passage any more — nothing rides above the stub top.)
    relief=True appends the 45° overhang wedge — for the CHASSIS ONLY
    (it relieves the wall-plate tongue's print overhang; the endplates
    pass relief=False or the wedge eats their end-wall groove roof)."""
    negs = []
    # end-wall groove: SIMPLE rectangular tongue-and-groove (user) —
    # width STUB_TNG_W + 0.1/side, depth STUB_TNG_H + 0.1, opened 1
    # below the mating plane; blind end exactly at the stub's inboard
    # face. The M4 lock screw crossing it lives in
    # endwall_screw_negatives (endplates) / _body_stub (tongue pilot).
    L = SQ_W + 1.0
    y0 = ly - SQ_W / 2 if syg > 0 else ly - SQ_W / 2 - 1.0
    negs.append(box_at(STUB_TNG_W + 0.2, L, STUB_TNG_H + 0.1 + 1.0,
                       x=station + egx * STUB_RIDGE_EP, y=y0 + L / 2,
                       z=z_bot + (STUB_TNG_H + 0.1 - 1.0) / 2))
    # crossing grooves (thirds of the side-panel overlap): 0.5 inboard
    # overshoot, 1 outboard
    Lc = SQ_W + 1.5
    y0c = (ly - SQ_W / 2 - 0.5) if syg > 0 else (ly - SQ_W / 2 - 1.0)
    for dx in _cross_x(egx):
        negs.append(_groove(Lc).translate((station + dx, y0c, z_bot)))
    # 45° OVERHANG RELIEF (user): in the RAIL-BAND y (where the end-wall
    # groove crosses the rail-end dovetail tongue at the keyhead / the
    # kept-shell exit at the bridge), the corner left standing above the
    # groove's OUTBOARD exit is trimmed by a 45° plane that JUST CLEARS
    # the joint's roof — height from the groove depth (STUB_TNG_H + fit),
    # so the plane tracks any joint-size change — rising outboard: one
    # continuous 45° underside from the joint's top-inboard flank out
    # through the tongue / wall face. Reach 3.6 stays inside the
    # endplate's outer skin (groove face gap 0.86 + skin 0.9 both ends).
    if not relief:
        return negs
    zr = z_bot + (STUB_TNG_H + 0.1) + 0.3
    xg = station + egx * STUB_RIDGE_EP
    RCH = 3.6
    prof = [(xg, zr), (xg + egx * RCH, zr + RCH),
            (xg + egx * RCH, z_bot - 1.0), (xg, z_bot - 1.0)]
    yw0 = ly + syg * 10.5
    yw1 = ly + syg * 23.0
    ylo, yhi = min(yw0, yw1), max(yw0, yw1)
    negs.append(cq.Workplane("XZ").workplane(offset=-yhi)
                .polyline(prof).close().extrude(yhi - ylo))
    return negs


def endwall_screw_negatives(station: float, ly: float, egx: float,
                            z_bot: float) -> list:
    """The per-leg M4 LOCK SCREW (user): ONE M4x10 button head per leg
    runs ALONG X in from the instrument's end face, crossing the
    tongue-and-groove transversely — Ø4.6 clearance through the OUTBOARD
    groove cheek, Ø3.6 thread-forming pilot on through the stub's tongue
    and the INBOARD cheek (a double-shear lock pin: holds the stub
    against y slide-out and z pull-off; tip flush with the wall inner
    face). Axis on the leg centreline at tongue mid-height (z_bot + 4) —
    clear of the rail-band relief wedge (ly+10.5..23) and the KH stow
    bores (|y| <= 31.75). WORLD-space cutters for the ENDPLATES; the
    stub cuts its own tongue pilot in _body_stub."""
    zc = z_bot + STUB_TNG_H / 2
    tip = station + egx * (SQ_W / 2 + 1.0)          # 1 outboard of the face
    negs = [cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.8, STUB_WALL_D + 1.0, cq.Vector(tip, ly, zc),
        cq.Vector(-egx, 0, 0)))]
    negs.append(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.3, 1.0 + (STUB_WALL_D - (STUB_TNG_W + 0.2)) / 2,
        cq.Vector(tip, ly, zc), cq.Vector(-egx, 0, 0))))
    return negs


def _body_stub(wired: bool, eps: float) -> cq.Workplane:
    """BODY STUB ×4 (PETG-GF, prints LYING ON ITS LOCAL +Y FACE — the
    Y-install round's point: layer lines run in x-z, so BOTH leg-bending
    directions load within layers, and the house-socket gable points up
    in the print). z0 = MOUTH (bottom face, at global Z_BOT - 48); body
    0..48; on top (full 44 in y): TWO Y-running octagon crossing ridges
    at the side-panel-overlap THIRDS (_cross_x: local eps*0.667 /
    -eps*10.667) + the END-WALL rectangular TONGUE 5 x 8 at x = eps*17
    (eps = which local x side this SKU's corner faces its endplate on),
    with the Ø3.6 M4 lock-screw pilot crossing it along x at mid-height
    (the screw comes in through the endplate's end face —
    endwall_screw_negatives). The stub slides in ALONG +local-y until
    the tongue tip butts its blind groove end (outer faces flush); every
    groove entry in the side face is filled flush by its ridge/tongue
    end. Bottom = the flush OCTAGON socket (round 3 — mortise open
    through the bottom face + the local +Y groove; fully passive now the
    quick-release ledge pocket and bolt tail window are gone). Wired: + the mouth-seat boss,
    barrel way and the Ø9.7 jack way opening through the FLAT top face
    (see TRRS_DX — no fin/chimney: the naked 10-03404 drops in through
    the wide rib's well AFTER the stub seats, and an M2 set screw from
    the inboard-y face clamps it)."""
    b = box_at(SQ_W, SQ_W, STUB_H, z=STUB_H / 2)
    # SOCKET: the flush OCTAGON mortise (net 40 deep from the mouth,
    # spigot 38 → mouth-butt hard stop), opening through the bottom face AND
    # the local +Y face (the groove — user round 3: every leg joint is the
    # flush octagon; no 180 flip any more, the bed face fixes the orientation)
    b = b.cut(_section_mortise(length=39.4).translate((0, 0, -1.0)))
    # LATCH (female half): hook channel + 45 deg mouth lead-in + retention
    # pocket, ALL INTERNAL — the outer wall keeps 6.6 mm and is never broken,
    # so no button and no hole appears on the body (user). Mouth is local z0.
    b = b.cut(LT.female_cutter(engage_z=0.0))
    ca, cb = _cross_x(eps)
    for rx in (ca, cb):
        b = b.union(_stub_ridge(SQ_W).translate((rx, -SQ_W / 2, STUB_H)))
    # end-wall TONGUE (simple rectangle, user) + its Ø3.6 M4 pilot
    # crossing at mid-height on the y centreline (world y = leg centre)
    b = b.union(box_at(STUB_TNG_W, SQ_W, STUB_TNG_H,
                       x=eps * STUB_RIDGE_EP, z=STUB_H + STUB_TNG_H / 2))
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.8, STUB_TNG_W + 2.0,
        cq.Vector(eps * (STUB_RIDGE_EP + STUB_TNG_W / 2 + 1.0), 0.0,
                  STUB_H + STUB_TNG_H / 2),
        cq.Vector(-eps, 0, 0))))
    # M4 SHEAR-PIN pilots down through the crossing ridges at the wall
    # band (local y -17 = the rail-web access-bore line; only the
    # inboard one gets a screw, the SKU keeps both for every corner)
    for tx in (ca, cb):
        b = b.cut(cyl(3.6, 12.0, z=STUB_H + 7.24 - 12.0)
                  .translate((tx, -17.0, 0)))
    if wired:
        # TRRS axis at (TRRS_DX, TRRS_DY) — the fat flare band of the flush
        # octagon (the old y-0 axis has no material around it any more)
        b = b.union(cyl(13.0, 1.9, z=38.2).translate((TRRS_DX, TRRS_DY, 0)))
        #                                    mouth-seat boss: 38.7 ledge
        #                                    seats the jack, bottom clears
        #                                    the plug handle (37.2)
        b = b.cut(cyl(4.8, 2.0, z=38.0).translate((TRRS_DX, TRRS_DY, 0)))
        b = b.cut(cyl(9.7, (STUB_H + 7.24 - 38.7) + 1.0, z=38.7)
                  .translate((TRRS_DX, TRRS_DY, 0)))   # jack way: opens
        #                                    through the flat TOP FACE and
        #                                    notches the +0.667 crossing
        #                                    ridge (jack drops in after the
        #                                    slide through the rib's well)
        # M2 SET-SCREW way from the inboard +y face, re-derived for the new
        # axis (the way's +y wall is now at y 17.85): Ø4.2 access bore to
        # the wall + Ø1.6 thread-forming pilot poking into the Ø9.7 way
        b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            2.1, 13.5, cq.Vector(TRRS_DX, SQ_W / 2 + 1.5, 43.0),
            cq.Vector(0, -1, 0))))
        b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            0.8, 3.5, cq.Vector(TRRS_DX, 10.3, 43.0),
            cq.Vector(0, -1, 0))))
    return b


def leg_body_stub() -> cq.Workplane:
    """Plain body stub ×2 (bridge/+Y at rot 180 and keyhead/-Y at rot 0:
    both face their endplate on local -x -> end-wall ridge at -17)."""
    return _body_stub(False, -1.0)


def leg_body_stub_jk() -> cq.Workplane:
    """Body stub, MIRRORED end-wall side, ×1 (the +X/-Y jack corner,
    rot 0 -> endplate on local +x -> end-wall ridge at +17)."""
    return _body_stub(False, 1.0)


def leg_body_stub_trrs() -> cq.Workplane:
    """Wired body stub ×1 (the -X/+Y corner, rot 180 -> endplate on
    local +x): carries the chassis-side 10-03404 of the leg↔body
    blind-mate on the flipped TRRS axis (local +5) — dropped into the
    Ø9.7 way from above after install; NOTHING above the top face."""
    return _body_stub(True, 1.0)


def leg_head() -> cq.Workplane:
    """LEG HEAD x4 (PCTG, prints LYING on its +Y bed face — round 3,
    all-octagon): octagon section socket below (mates the top segment), flush
    octagon SPIGOT above (into the body stub), TRRS plug seat + ways on the
    (+5,+13) axis (the flare band). PRINT-REFINEMENT FLAG: the lying TRRS
    seat/way bores are horizontal — want teardrops / a roundness print-check.

    The leg column's top piece = the INSERTING half of the leg<->body joint,
    the bar-tower pattern: 44-sq body with the octagon SPIGOT (38, into the
    body stub's socket), the standard section socket below (any segment's
    integral plug + one M4), and the captive TRRS plug seat + cable ways
    (every head carries them invisibly - ONE SKU for all four legs). The
    50-sq shoulder plate is GONE (user: consistent 44 everywhere); the body
    top face butting the stub mouth is the hard stop. Local z0 = the body
    TOP face (mounted at global Z_BOT - 48).

    The wedging-bolt channel and recessed seatbelt-button pocket are GONE
    with the quick-release (user): the spigot is now a plain sliding fit,
    so this joint has no Z retention at all. Was named leg_latch_head."""
    b = box_at(SQ_W, SQ_W, HEAD_BODY_L, z=-HEAD_BODY_L / 2)
    # section socket below (STANDARD stack orientation - the segment chain
    # underneath is not flipped): the OCTAGON section mortise, opening through
    # the head's bottom face AND its +Y face (the flush-joint groove) + the M4
    # retention clearance from the OUTER -Y face at x +7 (same scheme as the
    # segment sockets; nothing shares that band now the button pocket is gone)
    b = b.cut(_section_mortise(length=SEC_MOR_L + 1.0)
              .translate((0, 0, -HEAD_BODY_L - 1.0)))
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.25, 17.0, cq.Vector(7.0, -SQ_W / 2 - 1.0, -HEAD_BODY_L + 14.0),
        cq.Vector(0, 1, 0))))
    # SPIGOT: the flush OCTAGON section tenon (38 up, embedded 1 into the
    # body top; stem base ON the +Y bed face — user round 3, replaces the
    # house). Slides -Z-relative into the stub's mortise; mouth-butt stop.
    b = b.union(_section_tenon(39.0).translate((0, 0, -1.0)))
    # LATCH (male half): the slider tunnel — which also takes the octagon apex
    # away across the band, opening the channel the hook travels in — plus the
    # cover dovetail, and the finger well that sinks this 44 face to the tower's
    # 35.6 so ONE slider + cover SKU serves both joints. See latch.py.
    b = b.cut(LT.well_cutter(-SQ_W / 2)).cut(LT.male_cutter())
    b = b.union(LT.male_post())          # coil guide post (union AFTER the tunnel cut)
    # captive CA-354S seat + cable ways on the TRRS axis (+5, +13 — moved
    # into the fat flare band): tip lip, handle way, Ø8 down-way to the core
    b = b.cut(cyl(9.4, 1.7, z=37.4).translate((5.0, TRRS_DY, 0)))
    b = b.cut(cyl(11.0, 31.2, z=6.3).translate((5.0, TRRS_DY, 0)))
    #                        way starts at +6.3: the press retainer (bottom
    #                        +6.4) sits fully in Ø11 (probe-caught burial)
    b = b.cut(cyl(8.0, 22.0, z=-13.0).translate((5.0, TRRS_DY, 0)))
    return heal(b)


# leg_latch_bolt() / leg_latch_btn() REMOVED (user): the seatbelt quick-release
# is gone from both the leg↔body and the leg↔bar joints. They were one shared
# SKU pair — bolt ×4 on the leg heads, ×2 more on the pedal-bar towers — and
# with them go the BOLT_W/BOLT_H/BOLT_X and SPG_W datums, the ledge pockets and
# tail windows in leg_body_stub + leg_shaft_short, and the channel/pocket in
# leg_head + pedal_bar._stub_tower. Neither joint retains in Z now, by design.




def leg_plug_retainer() -> cq.Workplane:
    """Printed press sleeve ×1 (PCTG): pushed up the wired leg's top-
    segment Ø11 bore under the plug handle — the INSERTION backstop (the
    blind-mate pushes the plug DOWN; the spigot's Ø9.4 tip lip takes
    withdrawal). 18 long at Ø11.15 (0.15 press) spreads the load; the
    side slot admits the cable during assembly. Z0 = bottom."""
    b = cyl(11.15, 18.0, z=0.0)
    b = b.cut(cyl(6.6, 20.0, z=-1.0))    # the Ø6 spring relief passes through
    b = b.cut(box_at(4.2, 8.0, 20.0, y=4.0, z=9.0))
    return b


def chassis_trrs_jack() -> cq.Workplane:
    """DEMO chassis-side jack — Tensility 10-03404 (Ø9.1 × 39.4 molded
    body, Ø3.6 mouth DOWN, factory cable out the top): seated on the
    socket's mouth ring, coaxial with the leg thread. Socket-local."""
    b = cyl(CHJ_D, CHJ_L, z=CHJ_MOUTH_Z)
    b = b.cut(cyl(3.7, 14.5, z=CHJ_MOUTH_Z - 0.2))
    return b


def jack_seat_ring() -> cq.Workplane:
    """Printed press ring ×1 (PCTG): pushed DOWN the wired short shaft's
    Ø9.7 way onto the bar-joint jack's top — its insertion backstop (the
    integral boss below the mouth takes withdrawal). Ø5 way passes the
    factory cable. Z0 = bottom (sits on the jack top)."""
    return cyl(9.75, 6.0, z=0.0).cut(cyl(5.0, 8.0, z=-1.0))


def leg_column_plug() -> cq.Workplane:
    """DEMO column-top plug — the SECOND CA-354S, recessed in the top
    segment's Ø11 bore with its full barrel exposed (handle top 0.2 under
    the tip lip): tip at +4.8 = 13.0 into the chassis jack at seat.
    Socket-local."""
    b = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.75, 14.5, cq.Vector(0, 0, -10.8), cq.Vector(0, 0, 1)))
    b = b.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        5.0, 12.6, cq.Vector(0, 0, -10.8), cq.Vector(0, 0, -1))))
    b = b.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        3.0, 16.0, cq.Vector(0, 0, -23.4), cq.Vector(0, 0, -1))))
    return b


def leg_foot() -> cq.Workplane:
    """SHARED TPU foot ×4 (user: one look everywhere — the same dovetail
    insert serves the -Y leg blocks AND the pedal bar): 44-sq ground pad
    + dovetail tenon sliding into the underside mortise from -Y local;
    compression-loaded, TPU-grippy, no fastener. Tenon 31.1 long (y -17.5
    ..FOOT_TENON_Y1): inside the 35.6 BLK_W block faces (and the 44 bar;
    the +Y end still butts the slot's closed end 0.5 beyond it = the Y
    registration), and now clear of the pedal lid's groove — see
    FOOT_TENON_Y1. Z0 = ground."""
    b = box_at(SQ_W, SQ_W, FOOT_H, z=FOOT_H / 2)
    b = b.union(cq.Workplane("XZ")
                .polyline([(-14.8, FOOT_H), (-13.3, FOOT_H + 5.8),
                           (13.3, FOOT_H + 5.8), (14.8, FOOT_H)])
                .close().extrude(FOOT_TENON_Y1 + 17.5)
                .translate((0, FOOT_TENON_Y1, 0)))
    return b


