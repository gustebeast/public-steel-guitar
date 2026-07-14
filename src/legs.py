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
NOTCH at z 9..29 (local +Y → the bar-mouth side): the latch bolt's head
bears flat-on-flat on it, its crescent shoulders + the foot cap set the
bar's Z, and the CLOSED bolt head under the upper shoulder is the
anti-lift. The notch never enters the sleeve (exposure stays ≥ ~30).

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
  layers, glued into the rail, and it lives in the sustained ground-
  reaction path where GF's creep resistance pays.
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

from .helpers import box_at, cyl, heal

# thread (shared by every junction)
TH_MAJOR, TH_MINOR = 36.0, 30.0
TH_LEAD, TH_STARTS = 18.0, 1          # SINGLE start (one seated rotation per
                                       # junction); lead 18 → still 1.4 turns
TH_LEN  = 25.0
TH_CLR  = 0.4                          # printed-thread fit (diametral-ish)

# hard-stop junction: male shoulder collar + female rim gland (see header).
COLLAR_D, COLLAR_H = 40.0, 2.0         # male collar; its height IS the drawn
                                       # junction gap → stack math unchanged
GLAND_ID, GLAND_DEPTH = 36.4, 2.0      # female rim recess (clears the Ø35.6
                                       # male crests; open to the outside)
WASHER_OD, WASHER_ID, WASHER_T = 42.0, 36.6, 2.5   # TPU ring, squeezed 2.5→2.0

TUBE_OD, TUBE_ID = 30.0, 22.0
SEG_L   = 165.0                        # incl. the 25 male thread → 140 effective;
                                       # step/segment = 142 — MUST stay < the
                                       # shaft's slide range so bands overlap
SLEEVE_L = 200.0                       # bore-through; hosts up to 192 of
                                       # tenon engagement (prints standing)
SHAFT_D, SHAFT_L = 20.0, 212.0         # -Y long shaft: 197 sliding tenon + 15
                                       # foot zone. FINE-STAGE MATH (user):
                                       # travel = the 142 section pitch (so
                                       # height bands are CONTIGUOUS across
                                       # segment-count changes) + 50 minimum
                                       # extended overlap (1.8× the 28-wide
                                       # tenon — mortise proportion; the pinch
                                       # preloads it) + 5 dead = 197 tenon
SHAFT_FLAT_Y  = 6.8                    # SINGLE key flat (local +Y → the
                                       # rotated +Y-rail stacks aim it at the
                                       # bar MOUTH, i.e. INWARD): the
                                       # print-bed face, the sleeve key, AND
                                       # the latch bolt's bearing face — the
                                       # head bears flat-on-flat on the bed
                                       # surface itself (normal pure Y, no
                                       # cam-open component, 0.2 play). 6.8
                                       # keeps the flat→round junction at 43°
                                       # (< 45° overhang); single-D = one
                                       # unique orientation. The slot's back
                                       # is ROUND (r10.2 on the Ø20).
SLEEVE_FLAT_Y = 7.0                    # matching sleeve-bore flat (0.2 clr)
WAIST_Z0, WAIST_Z1 = 9.0, 29.0         # the FOOT BAND (z from the shaft
                                       # bottom: foot cap top → sleeve's
                                       # lowest reach): the bar plate rides
                                       # here; the TRRS shaft's corner-fill
                                       # extension is limited to this band
FOOT_H  = 12.0
# stack at k segments: 32 barrel + (k+1)×2 collar gaps + k×140 + 180 sleeve +
# shaft exposure 24..184 + 3 foot floor → height = 217 + 142k + exposure

# socket bracket
BARREL_OD, BARREL_L = 44.0, 32.0
# LEG_STATIONS_X (the two corner-station X's, both rails) is COMPUTED in chassis.py
# from the shared endplate<->leg model (chassis.LEG_STATIONS_X = endplate tip -/+
# LEG_W/2 -- FLUSH-X: each leg's outer X face lies ON its endplate's outer face).
# It lives there (not here) because it depends on the endplate tip positions,
# which are chassis constants. Result: (-13.4, -614.2).
# rail joinery (chassis.py cuts the matching slots from these)
DT_FACE_HW = 14.0                      # dovetail half-width at the rail face…
DT_DEEP_HW = 18.0                      # …flaring 45° to this at full depth
DT_DEPTH   = 4.0                       # into the Ø8-thick rail (half)
DT_H       = 38.0                      # straight band above Z_BOT; the roof
                                       # rises 45° toward the face above it


def _thread(rod_r: float, length: float, clr: float = 0.0,
            phase_deg: float = 0.0) -> cq.Workplane:
    """Thread ridges around a rod of radius rod_r: union for a male thread
    (clr=0), cut from a bore for a female one (clr>0 fattens the profile).
    Built as SEGMENTED straight prisms (skewed linear extrusions) — raw
    helical sweeps make booleans fragile in OCC; this is the same robust
    approach the belt model uses. IMPORTANT: a straight chord follows
    r(psi) = a/cos(psi) between facets, so the female cut must be generated
    on the MALE rod radius (clr only widens the profile) or the male skin
    escapes the cut mid-facet; callers must also extend a female cut one
    full lead past the mouth so out-of-band male prisms can't poke uncut
    overshoot tails into the engagement band."""
    depth = (TH_MAJOR - TH_MINOR) / 2 + clr
    w_root, w_crest = 4.4 + clr, 2.2 + clr
    n_turn = 48   # 7.5 deg facets — smooth enough to read as a helix. MUST
                  # divide the 60 deg joint phase so male/female facet grids
                  # coincide exactly when seated (60/7.5 = 8)
    dthe = 2 * math.pi / n_turn
    dz_seg = TH_LEAD / n_turn
    n_seg = int(length / dz_seg) + 1
    r0, r1 = rod_r - 0.2, rod_r + depth
    out = cq.Workplane("XY")
    for k in range(TH_STARTS):
        the0 = 2 * math.pi * k / TH_STARTS + math.radians(phase_deg)
        for j in range(n_seg):
            the = the0 + j * dthe
            zj = j * dz_seg
            u = cq.Vector(math.cos(the), math.sin(the), 0)
            zhat = cq.Vector(0, 0, 1)
            corners = [u.multiply(r0) + zhat.multiply(zj - w_root / 2),
                       u.multiply(r1) + zhat.multiply(zj - w_crest / 2),
                       u.multiply(r1) + zhat.multiply(zj + w_crest / 2),
                       u.multiply(r0) + zhat.multiply(zj + w_root / 2)]
            f = cq.Face.makeFromWires(cq.Wire.makePolygon([*corners, corners[0]]))
            # skewed extrusion along the (over-length) chord + the helical rise
            t = cq.Vector(-math.sin(the), math.cos(the), 0)
            chord = 2 * rod_r * math.sin(dthe / 2) * 1.3
            vec = t.multiply(chord) + zhat.multiply(dz_seg * 1.3)
            out = out.add(cq.Solid.extrudeLinear(f, vec))
    # clip the stack to the 0..length band so ends are clean planes
    band = cq.Solid.makeCylinder(r1 + 1, length, cq.Vector(0, 0, 0), zhat)
    clipped = cq.Workplane("XY")
    for s in out.vals():
        c = s.intersect(band)
        for ss in (c.Solids() if hasattr(c, "Solids") else []):
            clipped = clipped.add(ss)
    return clipped


def leg_socket() -> cq.Workplane:
    """Glued joinery socket, no fasteners: a vertical dovetail tenon slides
    UP into the rail-face slot from below until the barrel's top rim seats
    flat under the rail's bottom flange (ground reaction = big-area
    compression; the tenon's 45° matching top stops 0.3 shy so the rim is
    the bearing surface). Dovetail flanks + glue take bending/torsion; the
    tenon foot lands fully on the barrel's solid top disc. Prints barrel
    mouth down, tenon up (its 45° top self-supports). Local: barrel axis at
    origin under the rail centreline, rail outer face at y −4 (= chassis
    T/2, keep in sync), Z0 = rail bottom = the chassis print bed."""
    barrel = cyl(BARREL_OD, BARREL_L, z=-BARREL_L)
    c = 0.3                                       # dovetail sliding clearance
    tenon = (cq.Workplane("XY")
             .polyline([(-(DT_FACE_HW - c), -4.0), (DT_FACE_HW - c, -4.0),
                        (DT_DEEP_HW - 2 * c, -c), (-(DT_DEEP_HW - 2 * c), -c)])
             .close().extrude(DT_H + DT_DEPTH))
    # 45° top matching the slot roof (rises toward the face), dropped 0.3
    keep = (cq.Workplane("YZ")
            .polyline([(-5.0, 0.0), (-5.0, DT_H + 4.7), (1.0, DT_H - 1.3),
                       (1.0, 0.0)])
            .close().extrude(2 * DT_DEEP_HW + 4)
            .translate((-(DT_DEEP_HW + 2), 0, 0)))
    # tenon built on the OUTER face (y −4), then MIRRORED across the rail centreline to the INNER face
    # (+y) so the joint hides inside the instrument and the outer face stays clean/flush.
    body = barrel.union(tenon.intersect(keep).mirror("XZ"))
    # rim GLAND: washer recess in the mouth face — the surviving inner
    # Ø30.4..36.4 ring is the hard-stop face the male collar lands on
    body = body.cut(cyl(BARREL_OD + 2, GLAND_DEPTH + 0.5, z=-BARREL_L - 0.5)
                    .cut(cyl(GLAND_ID, GLAND_DEPTH + 2, z=-BARREL_L - 1)))
    # female thread: bore + ridge grooves, opening DOWN
    body = body.cut(cyl(TH_MINOR + TH_CLR, TH_LEN + 2, z=-BARREL_L - 1))
    # one extra lead of groove BELOW the mouth (in free air): prisms whose
    # faces sit under the band would otherwise poke uncut tails into it
    body = body.cut(_thread((TH_MINOR - TH_CLR) / 2, TH_LEN + 2 + TH_LEAD,
                            clr=0.8, phase_deg=60.0)
                    .translate((0, 0, -BARREL_L - 1 - TH_LEAD)))
    # bore-ceiling 45° cone (printed mouth-down, the bore roof was a flat
    # Ø30.4 internal bridge): self-supporting to Ø24, the small remaining
    # disc bridges cleanly; stops 2.8 under the tenon's solid top disc
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCone(
        (TH_MINOR + TH_CLR) / 2, 12.0, 3.2,
        cq.Vector(0, 0, -BARREL_L - 1 + TH_LEN + 2), cq.Vector(0, 0, 1))))
    return heal(body)   # helical-thread booleans need a ShapeFix pass


# ── TRRS leg↔body BLIND-MATE (the -X/+Y leg's stack; see pedal_bar.py for
# the bar joint). The chassis-side jack (Tensility 10-03404: Ø9.1 × 39.4
# molded body on 0.91 m of cable) embeds VERTICALLY in leg_socket_trrs,
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
                              # re-based for the square latch socket:
                              # spigot top -10, plug tip +3.7)
CHJ_D, CHJ_L = 9.1, 39.4      # 10-03404 molded body
SEG_BORE_D = 11.0             # segment axial bore (Ø10 handle way)
PLUG_TIP_Z = 4.8              # seated barrel tip (socket-local)


def leg_segment() -> cq.Workplane:
    """Stackable tube: male thread up top, female bell at the bottom. Two per
    leg; print more/shorter to leave the typical height range. Z0 = bottom."""
    body = cyl(TUBE_OD, SEG_L - TH_LEN, z=0.0)
    # male threaded spigot on top
    spigot = cyl(TH_MINOR - TH_CLR, TH_LEN + 2, z=SEG_L - TH_LEN - 2)
    spigot = spigot.union(_thread((TH_MINOR - TH_CLR) / 2, TH_LEN + 2)
                          .translate((0, 0, SEG_L - TH_LEN - 2)))
    body = body.union(spigot)
    # male shoulder COLLAR (the hard stop): Ø40 × 2 atop the tube; a 45° cone
    # below keeps the printed overhang legal (prints standing, bell down)
    body = body.union(cyl(COLLAR_D, COLLAR_H, z=SEG_L - TH_LEN))
    body = body.union(cq.Workplane("XY").add(cq.Solid.makeCone(
        TUBE_OD / 2, COLLAR_D / 2, 5.0,
        cq.Vector(0, 0, SEG_L - TH_LEN - 5.0), cq.Vector(0, 0, 1))))
    # female bell at the bottom
    body = body.union(cyl(BARREL_OD, TH_LEN + 6, z=0.0))
    # rim GLAND (washer recess; the inner ring is the hard-stop face)
    body = body.cut(cyl(BARREL_OD + 2, GLAND_DEPTH + 0.5, z=-0.5)
                    .cut(cyl(GLAND_ID, GLAND_DEPTH + 2, z=-1)))
    body = body.cut(cyl(TH_MINOR + TH_CLR, TH_LEN + 1, z=-1))
    body = body.cut(_thread((TH_MINOR - TH_CLR) / 2, TH_LEN + 1 + TH_LEAD,
                            clr=0.8, phase_deg=60.0)
                    .translate((0, 0, -1 - TH_LEAD)))   # extra lead below mouth
    # hollow core (weight)
    body = body.cut(cyl(TUBE_ID, SEG_L - 2 * TH_LEN - 14, z=TH_LEN + 4))
    # bore-ceiling 45° cone (printed bell-down, the female bore's roof was a
    # flat Ø30.4 internal bridge): rises into the core — fully self-
    # supporting; the spigot-tip clearance below is untouched
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCone(
        (TH_MINOR + TH_CLR) / 2, TUBE_ID / 2,
        (TH_MINOR + TH_CLR - TUBE_ID) / 2,
        cq.Vector(0, 0, TH_LEN), cq.Vector(0, 0, 1))))
    # TRRS column way (UNIVERSAL — every segment prints the same): a Ø11
    # axial bore through the solid spigot top links the Ø22 core to the
    # tip, sized for the CA-354S plug's Ø10 handle; the last 0.5 narrows
    # to Ø9.4 — that lip retains the plug UPWARD against the ≤4 kgf TRRS
    # withdrawal on the wired leg's TOP segment. Everywhere else it is
    # just a lighter spigot (and the cable's way on the wired leg's lower
    # segment).
    body = body.cut(cyl(SEG_BORE_D, 36.5, z=SEG_L - 37.0))
    body = body.cut(cyl(9.4, 1.7, z=SEG_L - 0.5))
    return heal(body)   # helical-thread booleans need a ShapeFix pass


def leg_sleeve() -> cq.Workplane:
    """Slider sleeve: MALE spigot up top (threads into the lower segment's
    bell), Ø20.4 bore for the shaft, PINCH COLLAR at the bottom: ONE slit
    (the solid wall opposite is the hinge) pulled closed by an M4 button
    screw spanning two lugs into a heat-set insert, shrinking the bore onto
    the shaft. Broad-band friction — ~MPa contact stress PCTG holds without
    creep — instead of a set-screw point load that stress-relaxes; the shaft
    stays unmarred. Set once per player, hex key. Closing the bore Ø0.4 needs
    ~1.3 of slit travel (< the 1.6 gap). Local: Z0 = shoulder; body −Z."""
    # SQUARE-LEG reskin: 44-sq outer body (the pinch lug pokes ~5 proud
    # of the +y face — accepted v1). Prints STANDING as always (the
    # sliding bore needs dimensional truth). ROUND 3: the threaded spigot
    # + collar are GONE — an integral 31.7-sq PLUG (28) slides into the
    # bottom segment's core, butt faces = hard stop, one M4 = retention.
    body = box_at(SQ_W, SQ_W, SLEEVE_L, z=-SLEEVE_L / 2)
    body = body.union(
        _house(27.7, -15.85, 1.85, SEG_PLUG_L + 1.0)
        .translate((0, 0, -1.0))
        .cut(_house(20.0, -12.0, 2.0, SEG_PLUG_L + 4.0)
             .translate((0, 0, -2.0))))
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.8, 8.0, cq.Vector(0, -SQ_CORE / 2 - 0.5, 14.0),
        cq.Vector(0, 1, 0))))
    # RECT keyed bore (ROUND 3): 20.4 × 17.2 matching the rectangular
    # shaft, with the 3×45° key chamfer on the (+x,-y) corner — one
    # orientation, no flat needed; the plug's hollow way continues above
    body = body.cut(cq.Workplane("XY")
                    .polyline([(-14.2, -13.2), (10.1, -13.2), (14.2, -9.1),
                               (14.2, 13.2), (-14.2, 13.2)])
                    .close().extrude(SLEEVE_L + TH_LEN)
                    .translate((0, 0, -SLEEVE_L - 1)))
    # lug block on +Y, then the single slit through block + wall + bore
    lz = -SLEEVE_L + 9.0                                  # bolt line
    body = body.union(box_at(16.0, 12.0, 18.0, y=21.0, z=lz))
    body = body.cut(box_at(1.6, 19.0, 44.0, y=18.5, z=-SLEEVE_L + 22.0))
    # M4 button screw enters +X: Ø8 head pocket to x=4 so the 12 mm screw
    # fully engages the insert seated in the −X lug (x −8..−3.3)
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.15, 18.0, cq.Vector(9.0, 21.0, lz), cq.Vector(-1, 0, 0))))
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        4.0, 5.5, cq.Vector(9.5, 21.0, lz), cq.Vector(-1, 0, 0))))
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.8, 6.0, cq.Vector(-9.0, 21.0, lz), cq.Vector(1, 0, 0))))
    # 45° teardrop roof on the Ø8 head pocket (horizontal bore, printed
    # standing; the Ø4.3/Ø5.6 bores are small enough to print round)
    t = 4.0 * 0.7071
    body = body.cut(cq.Workplane("YZ")
                    .polyline([(21.0 - t, lz + t), (21.0 + t, lz + t),
                               (21.0, lz + 4.0 * 1.4142)])
                    .close().extrude(5.5).translate((4.0, 0, 0)))
    return heal(body)   # helical-thread booleans need a ShapeFix pass


def leg_shaft() -> cq.Workplane:
    """-Y shaft ×2 (user: ALL FOUR legs share the wide|narrow|wide look
    at EQUAL heights): the same 197 tenon over a 44-sq terminal block —
    here 91 tall and printed ONE SOLID (no joint down low; nothing below
    creates lateral force), so block 91 + foot 12 = 103 matches the +Y
    stack's block 48 + tower 24 + bar 19 + foot 12. Shared TPU foot's
    dovetail mortise underneath. PETG-GF; 288 long — prints LYING on the
    bed DIAGONAL (like the bar pieces). Z0 = the block's bottom face."""
    body = (cq.Workplane("XY")
            .polyline([(-14.0, -13.0), (10.0, -13.0), (14.0, -9.0),
                       (14.0, 13.0), (-14.0, 13.0)])
            .close().extrude(TALL_SHAFT_L))
    body = body.union(box_at(SQ_W, SQ_W, TALL_BLOCK_H, z=TALL_BLOCK_H / 2))
    body = body.cut(foot_mortise_cutter())
    return body


# TRRS dock (the -X/+Y leg only — see pedal_bar.py for the mating story):
# the FEMALE jack is a Same Sky SJ-43514-SMT (DigiKey SJ-43514-SMT-TR —
# the no-switch 4-terminal variant: we carry exactly 4 signals,
# ~14.5×6×5 body, 14.0 mating depth), embedded in the shaft with its mating
# axis along X, mouth flush with the Ø20 at the INBOARD face (local -X; the
# rotated +Y-rail stack turns that toward the bar's latch side). The bar's
# latch slider carries the male plug (Same Sky SP-3541) and drives it
# in/out along X. Wires solder to the jack pads and run UP the Ø6 hollow
# CENTER BORE to the shaft top, then inside the sleeve/segments to the
# chassis. The jack body (14.5) is longer than the mating depth (14), so
# the plug tip stays inside it — no tip well behind.
TRRS_Z = 17.7                          # jack axis (shaft-local; = bar-local
                                       # 8.7 — low enough that the bar-side
                                       # cradle clears the lid plane)
TRRS_JACK_L, TRRS_JACK_W, TRRS_JACK_H = 14.5, 6.0, 5.0    # X × Y × Z
WIRE_BORE_D = 6.0                      # hollow centre: jack pocket → top
SHELF_Z0, SHELF_Z1 = 26.0, 29.0        # small OUTBOARD corner fill at the TOP
                                       # of the foot band: its underside is a
                                       # SHELF over the bar's solid corner —
                                       # positive hold-down (the slot squares
                                       # only its top 2.4 to slide past)


TENON_L = 197.0                # every shaft's sliding tenon: travel 142
                               # + overlap 50 + 5 dead (the fine-stage law)
SHORT_SHAFT_L = 245.0          # +Y shafts: 197 tenon + the 48 block
                               # (prints LYING, straight, <255)
BLOCK_H = 48.0                 # +Y 44-sq terminal block = the bar-joint
                               # mortise (socket 41, spigot 38 — reduced
                               # overlap per user: this joint's moment is
                               # small, and the wide stack must stay
                               # within PEDAL_ASSEMBLY_Z_HEIGHT (75 above
                               # the bar top) for the future pedals)
TALL_BLOCK_H = 91.0            # -Y 44-sq terminal block, printed SOLID:
                               # user requires EQUAL wide-section heights
                               # on all four legs — foot 12 + 91 = 103 =
                               # foot 12 + bar 19 + tower 24 + block 48.
                               # Same silhouette, TPU foot mortise below.
TALL_SHAFT_L = TENON_L + TALL_BLOCK_H   # 288: prints LYING on the bed
                               # DIAGONAL ((288+44)/sqrt(2) = 235 < 255),
                               # like the bar pieces


def foot_mortise_cutter() -> cq.Workplane:
    """Underside DOVETAIL mortise for the shared TPU foot tenon (slides
    in from -Y local; grip + compression = no fastener). Cut at the
    origin; z0 = the block's bottom face."""
    return (cq.Workplane("XZ")
            .polyline([(-15.0, 0.0), (-13.4, 6.0), (13.4, 6.0),
                       (15.0, 0.0)])
            .close().extrude(40.0).translate((0, 16.0, 0)))


def leg_shaft_short() -> cq.Workplane:
    """+Y shaft ×2: the 28×26 tenon ends in the 44-sq terminal BLOCK
    whose downward house socket + ledge take the bar tower's spigot/bolt
    (the leg↔body latch pattern with REDUCED 38 overlap — user: small
    moment here, and the wide stack must clear the future pedals'
    PEDAL_ASSEMBLY_Z_HEIGHT). Passive. Z0 = the block's mouth face."""
    body = (cq.Workplane("XY")
            .polyline([(-14.0, -13.0), (10.0, -13.0), (14.0, -9.0),
                       (14.0, 13.0), (-14.0, 13.0)])
            .close().extrude(SHORT_SHAFT_L))
    body = body.union(box_at(SQ_W, SQ_W, BLOCK_H, z=BLOCK_H / 2))
    body = body.cut(_house(28.1, -16.05, 2.05, 41.0).translate((0, 0, -1)))
    # ledge pocket on the house FLOOR side (-y local): the floor is the
    # full-width flat face — a +y-side bolt would run into the gable's
    # solid flanks (latent since the stub round; probe-caught)
    # (bolt rides at local x +8: its 12 width must fit INSIDE the house
    # width — beyond ±14.05 is solid wall here, unlike the body joint's
    # big square way)
    body = body.cut(box_at(BOLT_W + 2.0, 4.2, 9.0,
                           x=8.0, y=-(16.05 + 2.1), z=31.9))
    return body


def leg_shaft_trrs() -> cq.Workplane:
    """The -X/+Y leg's shaft (ROUND 4): leg_shaft_short() + the SECOND
    vertical TRRS blind-mate — a 10-03404 jack (mouth DOWN) coaxial above
    the socket roof, mating the bar stub's captive CA-354S plug on the
    same straight press that clicks the latch. Its factory cable runs UP
    the column to the mini junction PCB. The side dock / carrier PCB /
    corner channel of the sideways design are GONE."""
    body = leg_shaft_short()
    # vertical jack way, Ø9.7 CLEAN THROUGH to the tenon top: the
    # 10-03404 loads DOWN from the shaft's open top (pre-assembly) onto
    # the integral mouth-seat BOSS (withdrawal backstop); a pressed
    # jack_seat_ring ABOVE it takes insertion. Jack mouth +42.7, plug tip
    # +55.7 = 13.0 insertion on the same press that clicks the latch.
    # TRRS axis OFFSET to local x -5 (global +5 after the 180 placement):
    # the latch bolt owns the other side of the house floor band
    body = body.union(cyl(13.0, 1.9, z=38.2).translate((-5.0, 0, 0)))
    body = body.cut(cyl(4.8, 2.0, z=38.0).translate((-5.0, 0, 0)))
    body = body.cut(cyl(9.7, SHORT_SHAFT_L - 38.7 + 2.0, z=38.7)
                    .translate((-5.0, 0, 0)))
    return body


# ═══ SQUARE-LEG REDESIGN (2026-07-09, user-directed; supersedes the round
# tubes above — old generators kept during the staged swap) ══════════════
# Constant 44×44 outside, PRINTED LYING on a face in PETG-GF (layer lines
# run ALONG the leg → kick bending loads bulk material — the standing-
# print interlayer veto on GF is gone; square-44 ≈6× the Ø30 tube's
# stiffness by geometry, GF adds ~2.4× modulus). Threads can't print
# lying, so each body takes two STANDING-printed PCTG THREAD COUPLERS
# glued into its square core ends (huge glue area, inherent
# anti-rotation; preserves segment-count coarse height adjust). Internal
# joint geometry — Ø36/30 single-start thread, Ø40 collar hard stop, TPU
# gland washer — is UNCHANGED, so the 142 step and clocking phase carry
# over. The face CABLE CHANNEL + sliding lid (pedal-bar pattern) aligns
# across joints BECAUSE of the deterministic clocking: the cable lays in
# AFTER column assembly. Top joint = the SEATBELT LATCH head (separate
# part; all mechanism on the leg, passive socket) — see latch_head().
SQ_W = 44.0                    # outer square width (uniform, = old bell OD)
SQ_CORE = 32.0                 # square core (glue pocket for the couplers;
                               # 45° crown corners print lying)
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
PUCK_PLUG_L = 20.0             # coupler glue plug depth into the core
CH_MOUTH, CH_DEEP = 4.4, 5.2   # face cable channel (lidded; just the flat
                               # Ø3.7 run — the SLACK COIL lives in the
                               # core, so the channel stays narrow and the
                               # web to the joint socket wall stays ~2.8
                               # (user: protect the tenon walls))


def _sq_body(length: float, channel: bool = False) -> cq.Workplane:
    """Square leg body stock: 44×44×length, hollow 32-square core (prints
    lying on a face — the crown of the core self-supports via its 45°
    corner chamfers). channel=True (the WIRED leg's bodies ONLY — user:
    legs are otherwise identical) adds the +Y face CABLE CHANNEL with the
    45° dovetail LID seat (pedal-bar pattern: slide along Z, TPU nub, no
    screws) and a core DIVE hole near each end (cable → core at the
    sleeve joint below and at the latch head above). Z0 = bottom."""
    b = box_at(SQ_W, SQ_W, length, z=length / 2)
    if channel:
        # WIRED body: full house through-core (base 28, floor -16, walls
        # to +2, apex +16 — prints lying with the gable up; hosts the
        # cable + slack coil), stopping 4 short of the top where the
        # solid CAP roots the plug; house-20 way through the cap
        b = b.cut(_house(28.0, -16.0, 2.0, length - 4.0 + 1.0)
                  .translate((0, 0, -1)))
        b = b.cut(_house(20.0, -12.0, 2.0, 8.0)
                  .translate((0, 0, length - 6.0)))
    else:
        # PLAIN bodies are SOLID (user: only the wired leg needs the
        # channel/core; the slicer's infill sets real density) — just the
        # 30-deep house SOCKET at the bottom for the incoming plug
        b = b.cut(_house(28.1, -16.05, 2.05, 31.0).translate((0, 0, -1)))
    if channel:
        # cable channel on the +X SIDE face (the gable owns +y's depth);
        # lidded, so it reads as a seam. Same dovetail-seat profile,
        # coordinates swapped for the x-facing wall.
        hw, xf = CH_MOUTH / 2, SQ_W / 2
        b = b.cut(cq.Workplane("XY")
                  .polyline([(xf - CH_DEEP, -hw), (xf - CH_DEEP, hw),
                             (xf - 1.9, hw), (xf - 1.9, hw + 3.5),
                             (xf + 0.1, hw + 1.6), (xf + 0.1, -hw - 1.6),
                             (xf - 1.9, -hw - 3.5), (xf - 1.9, -hw)])
                  .close().extrude(length + 2).translate((0, 0, -1)))
        for dz in (24.0, length - 24.0):     # channel-floor dive holes
            b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
                2.1, CH_DEEP + 2.0, cq.Vector(SQ_W / 2 + 0.5, 0, dz),
                cq.Vector(-1, 0, 0))))
    # integral male HOUSE PLUG on the top end (wired: hollow house-20 way
    # keeps the cable and even the coil passable through joints; plain:
    # SOLID — stronger tenon, user request)
    plug = (_house(27.7, -15.85, 1.85, SEG_PLUG_L + 1.0)
            .translate((0, 0, length - 1.0)))
    if channel:
        plug = plug.cut(_house(20.0, -12.0, 2.0, SEG_PLUG_L + 4.0)
                        .translate((0, 0, length - 2.0)))
    b = b.union(plug)
    # M4 retention (user rule: joinery takes the force, the screw only
    # stops extraction): Ø4.5 clearance thru the -Y wall over the
    # INCOMING plug below + Ø3.6 thread-forming pilot in our OWN plug
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.25, 9.0, cq.Vector(0, -SQ_W / 2 - 1.0, 14.0),
        cq.Vector(0, 1, 0))))
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.8, 8.0, cq.Vector(0, -SQ_CORE / 2 - 0.5, length + 14.0),
        cq.Vector(0, 1, 0))))
    return b


def leg_seg_body() -> cq.Workplane:
    """PETG-GF square segment BODY ×6 (the plain legs; prints LYING on a
    face — layer lines along the leg). Takes one male + one female thread
    coupler, M4-retained in the square core ends."""
    return _sq_body(SEG_BODY_L)


def leg_seg_body_ch() -> cq.Workplane:
    """PETG-GF square segment BODY, CHANNELED ×2 (the wired -X/+Y leg
    only): + the lidded face cable channel and core dive holes."""
    return _sq_body(SEG_BODY_L, channel=True)


def leg_coupler_m() -> cq.Workplane:
    """PCTG male THREAD COUPLER (prints STANDING — thread quality): 44 sq
    ×6 flange + Ø40×2 hard-stop collar + the same Ø36/30 single-start
    spigot, square 32 glue plug below (0.3 fit into the body core; big
    glue area, inherent anti-rotation). Ø14 cable way through. Z0 = the
    flange's glue face (= body top end)."""
    b = box_at(SQ_W, SQ_W, 6.0, z=3.0)
    b = b.union(box_at(SQ_CORE - 0.3, SQ_CORE - 0.3, PUCK_PLUG_L,
                       z=-PUCK_PLUG_L / 2))
    b = b.union(cyl(COLLAR_D, COLLAR_H, z=6.0))
    b = b.union(cyl(TH_MINOR - TH_CLR, TH_LEN + 2, z=6.0))
    b = b.union(_thread((TH_MINOR - TH_CLR) / 2, TH_LEN + 2)
                .translate((0, 0, 6.0)))
    b = b.cut(cyl(14.0, PUCK_PLUG_L + 6 + TH_LEN + 4,
                  z=-PUCK_PLUG_L - 1))                 # cable way
    # M4 retention pilot (thread-forming; the plug's slide fit takes the
    # loads, this only stops extraction)
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.8, 8.0, cq.Vector(0, -SQ_CORE / 2 - 0.5, -12.0),
        cq.Vector(0, 1, 0))))
    return heal(b)


def leg_coupler_f() -> cq.Workplane:
    """PCTG female THREAD COUPLER (prints STANDING, mouth down): a 44-sq
    ×28 BARREL that hosts the full internal thread (Ø36.4 crests cannot
    fit inside the 32-square core — the barrel is exposed leg surface,
    flush with the bodies) with the TPU-washer GLAND + rim hard-stop ring
    in its mouth face, and a SHORT 32-sq locating plug (z 28..36) into
    the body core, M4-retained. Z0 = the mouth face."""
    b = box_at(SQ_W, SQ_W, 28.0, z=14.0)
    b = b.union(box_at(SQ_CORE - 0.3, SQ_CORE - 0.3, 8.0, z=32.0))
    b = b.cut(cyl(SQ_W + 4, GLAND_DEPTH + 0.5, z=-0.5)
              .cut(cyl(GLAND_ID, GLAND_DEPTH + 2, z=-1)))
    b = b.cut(cyl(TH_MINOR + TH_CLR, TH_LEN + 1, z=-1))
    b = b.cut(_thread((TH_MINOR - TH_CLR) / 2, TH_LEN + 1 + TH_LEAD,
                      clr=0.8, phase_deg=60.0)
              .translate((0, 0, -1 - TH_LEAD)))
    # bore ceiling 45° cone into the core (prints mouth-down)
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCone(
        (TH_MINOR + TH_CLR) / 2, 11.0, 4.2,
        cq.Vector(0, 0, TH_LEN), cq.Vector(0, 0, 1))))
    b = b.cut(cyl(22.0, 10.0, z=27.5))                 # open core way
    # M4 retention pilot into the locating plug (see coupler_m note)
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.8, 8.0, cq.Vector(0, -SQ_CORE / 2 - 0.5, 32.0),
        cq.Vector(0, 1, 0))))
    return heal(b)


def leg_lid() -> cq.Workplane:
    """PETG-GF sliding channel LID (one per segment body, prints lying,
    top-face down like the bar lid): 45° dovetail flanks ride the body's
    seat; a TPU nub (pedal_detent_nub SKU) locks it. Z0 = bottom."""
    hw = CH_MOUTH / 2
    return (cq.Workplane("XY")
            .polyline([(-hw - 3.3, -1.8), (hw + 3.3, -1.8),
                       (hw + 1.5, 0.0), (-hw - 1.5, 0.0)])
            .close().extrude(SEG_BODY_L - 0.6)
            .translate((0, 1.8, 0.3)))


# ── stage 2: seatbelt-latch top joint (all mechanism ON the leg) ────────
# ── the leg↔body joint (FLUSH round, replaces the 52-sq outset socket):
# a 44-sq BODY STUB per corner — "a regular leg section, as short as
# possible" (user) — semi-permanently attached via TWO tall octagon
# WALL TENONS (cadkit.joinery stop-sign profile, coupon-validated)
# sliding UP into closed mortises in the rail band / kept shells, ONE
# vertical M4 dropped down the rail web (head hidden under the deck) =
# extraction retention only. Below the body the stub carries the SAME
# passive latch socket as the leg↔bar joint (house 28.1 × 41 + ledge);
# the latch head engages it exactly like a bar tower — but the whole
# joint is authored FLIPPED 180° so the bolt channel opens INBOARD
# (never through the flush outer wall).
SPG_W = 36.0                   # latch-bolt sizing datum (legacy spigot
                               # width — the bolt SKU spans SPG_W/2+2.6)
HEAD_BODY_L = 42.0             # head body (30-deep plug socket + button
                               # band + plug seat)
BOLT_W, BOLT_H, BOLT_X = 12.0, 8.0, -12.0
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
STUB_WALL_D = 10.0             # endplate end-wall depth (= CH.T): the
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
STUB_TNG_W = 5.0               # end-wall tongue thickness (x) = CH.T/2
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
    from cadkit.joinery import octagon_tenon
    return (octagon_tenon(width=STUB_TEN_W, length=length)
            .rotate((0, 0, 0), (0, 0, 1), 90))


def _groove(length: float) -> cq.Workplane:
    """The matching cavity (ridge dilated 0.1/side, the coupon fit),
    Y-running, roof up, opening DOWNWARD at its base plane (the mortise's
    stem slit extends 2.1 below it — over the sliding plane that is air).
    Callers translate it to (ridge x, y0, Z_BOT)."""
    from cadkit.joinery import octagon_mortise
    return (octagon_mortise(width=STUB_TEN_W, length=length)
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
    end. Bottom = the leg↔bar latch
    socket VERBATIM (house 28.1 × 41 + ledge pocket), FLIPPED 180° so
    the head's bolt channel opens inboard. Wired: + the mouth-seat boss,
    barrel way and the Ø9.7 jack way opening through the FLAT top face
    (see TRRS_DX — no fin/chimney: the naked 10-03404 drops in through
    the wide rib's well AFTER the stub seats, and an M2 set screw from
    the inboard-y face clamps it)."""
    b = box_at(SQ_W, SQ_W, STUB_H, z=STUB_H / 2)
    cuts = _house(28.1, -16.05, 2.05, 41.0).translate((0, 0, -1))
    # ledge pocket on the house FLOOR side at local x +8 — VERBATIM the
    # bar-joint block's pocket (leg_shaft_short), so the same bolt nests
    cuts = cuts.union(box_at(BOLT_W + 2.0, 4.2, 9.0,
                             x=8.0, y=-(16.05 + 2.1), z=31.9))
    b = b.cut(cuts.rotate((0, 0, 0), (0, 0, 1), 180))
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
        b = b.union(cyl(13.0, 1.9, z=38.2).translate((TRRS_DX, 0, 0)))
        #                                    mouth-seat boss: 38.7 ledge
        #                                    seats the jack, bottom clears
        #                                    the plug handle (37.2)
        b = b.cut(cyl(4.8, 2.0, z=38.0).translate((TRRS_DX, 0, 0)))  # barrel
        #                                                              way
        b = b.cut(cyl(9.7, (STUB_H + 7.24 - 38.7) + 1.0, z=38.7)
                  .translate((TRRS_DX, 0, 0)))     # jack way: opens through
        #                                    the flat TOP FACE and notches
        #                                    the +0.667 crossing ridge
        #                                    where it overhangs the mouth
        #                                    (the jack drops in after the
        #                                    slide, through the wide rib's
        #                                    well; nothing stands proud)
        # M2 SET-SCREW way from the stub's INBOARD-y face (local +y —
        # exposed below the body even when assembled) clamping the jack
        # barrel just above its seated mouth: Ø4.2 access bore + Ø1.6
        # thread-forming pilot poking into the Ø9.7 way (1.5 hex key
        # drives the M2×5 through the access bore)
        b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            2.1, 15.0, cq.Vector(TRRS_DX, SQ_W / 2 + 1.0, 43.0),
            cq.Vector(0, -1, 0))))
        b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            0.8, 4.5, cq.Vector(TRRS_DX, 8.5, 43.0),
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


def leg_latch_head() -> cq.Workplane:
    """LATCH HEAD x4 (PCTG, prints standing): the leg column's top piece
    = the INSERTING half of the leg<->body latch, the bar-tower pattern
    VERBATIM but authored FLIPPED 180 deg so the bolt channel opens
    INBOARD (under the body's shadow - never through the flush outer
    wall): 44-sq body with the 27.7 house SPIGOT (38, into the body
    stub's 41 socket + ledge), wedging-bolt channel + recessed seatbelt
    BUTTON pocket, the standard section house socket below (any
    segment's integral plug + one M4), and the captive TRRS plug seat +
    cable ways on the flipped +5 axis (every head carries them
    invisibly - ONE SKU for all four legs). The 50-sq shoulder plate is
    GONE (user: consistent 44 everywhere); the body top face butting
    the stub mouth is the hard stop. Local z0 = the body TOP face
    (mounted at global Z_BOT - 48)."""
    b = box_at(SQ_W, SQ_W, HEAD_BODY_L, z=-HEAD_BODY_L / 2)
    # section socket below (STANDARD stack orientation - the segment
    # chain underneath is not flipped) + its M4 retention pilot
    b = b.cut(_house(28.1, -16.05, 2.05, 31.0)
              .translate((0, 0, -HEAD_BODY_L - 1.0)))
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.25, 9.0, cq.Vector(0, -SQ_W / 2 - 1.0, -HEAD_BODY_L + 14.0),
        cq.Vector(0, 1, 0))))
    # house spigot + latch cuts, FLIPPED 180 (mirrors the stub's socket)
    b = b.union(_house(27.7, -15.85, 1.85, 38.0)
                .rotate((0, 0, 0), (0, 0, 1), 180))
    b = b.cut(box_at(BOLT_W + 0.4, 30.0, BOLT_H + 0.4,
                     x=-8.0, y=12.2, z=31.8))       # bolt channel (floor side)
    b = b.cut(box_at(12.4, 9.0, 10.4, x=14.0, y=-(SQ_W / 2 - 4.4),
                     z=-11.0))                      # recessed button pocket
    # captive CA-354S seat + cable ways on the flipped TRRS axis (+5):
    # tip lip, handle way, then the Ø8 down-way into the section core
    b = b.cut(cyl(9.4, 1.7, z=37.4).translate((5.0, 0, 0)))
    b = b.cut(cyl(11.0, 31.2, z=6.3).translate((5.0, 0, 0)))   # way starts
    #                        at +6.3: the press retainer (bottom +6.4) sits
    #                        fully in Ø11 (probe-caught collar burial)
    b = b.cut(cyl(8.0, 22.0, z=-13.0).translate((5.0, 0, 0)))
    return heal(b)


def leg_latch_bolt() -> cq.Workplane:
    """Latch BOLT ×4 (PCTG): rigid slider in the spigot channel, 45° nose
    chamfer self-latches on push-in; underside bears on the socket's
    ledge (washer preload = zero play). Drawn ENGAGED. Local = head
    frame."""
    b = box_at(BOLT_W, SPG_W / 2 + 2.6, BOLT_H,
               x=BOLT_X, y=SPG_W / 4 + 0.7, z=31.8)   # bottom at the ledge;
    #                                       rear at y -0.6 so the bar-joint
    #                                       placement (ry - 1.4) clears the
    #                                       shaft block's descending gable
    b = b.cut(cq.Workplane("YZ")                     # 45° insertion chamfer
              .polyline([(SPG_W / 2 + 2.0, 31.8 + BOLT_H / 2),
                         (SPG_W / 2 - 1.0, 31.8 + BOLT_H / 2),
                         (SPG_W / 2 + 2.0, 31.8 - BOLT_H / 2 + 1.0)])
              .close().extrude(BOLT_W + 2).translate((BOLT_X - BOLT_W / 2 - 1, 0, 0)))
    return b


def leg_latch_btn() -> cq.Workplane:
    """Latch BUTTON ×4 (PCTG): recessed seatbelt-style pad on the head
    body's inboard face + stem into the mechanism cavity (35° wedge to
    the bolt at refinement). Local = head frame. Stem tip lands ON the
    pocket floor (y 13.1) — not through it."""
    b = box_at(12.0, 3.0, 10.0, x=-14.0, y=SQ_W / 2 - 1.6, z=-11.0)
    b = b.union(box_at(8.0, 5.9, 6.0, x=-14.0, y=SQ_W / 2 - 5.95, z=-11.0))
    return b


def leg_socket_trrs() -> cq.Workplane:
    """leg_socket() + the vertical CHASSIS-JACK pocket for the leg↔body
    blind-mate (the -X/+Y station only — see the TRRS block above): a
    Ø9.7 way COAXIAL with the thread, from the bore-ceiling void up
    through the top disc and the tenon core (the dovetail FLANKS carry
    the glue; a centre bore costs little), a MOUTH-SEAT boss hanging into
    the void whose Ø4.8..9.7 bottom ring seats the jack face (withdrawal
    backstop; the printed socket_jack_slug + the rail slot roof backstop
    insertion after glue-up), and a 90° CABLE CHANNEL above the jack out
    the tenon's inner face (local +y; the 180°-placed +Y-rail socket
    turns it toward the body interior). The jack drops in from the tenon
    top BEFORE glue-up — a 5000-cycle part that outlives the joint."""
    body = leg_socket()
    body = body.union(cyl(13.0, 6.2, z=-8.8))       # mouth-seat boss
    body = body.cut(cyl(4.8, 1.2, z=-8.9))          # barrel way thru the ring
    body = body.cut(cyl(9.7, 52.0, z=CHJ_MOUTH_Z))  # jack way, open to top
    body = body.cut(box_at(4.4, 8.5, 9.0, y=4.25, z=35.5))   # cable channel
    return body


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
    compression-loaded, TPU-grippy, no fastener. Tenon 37 long (y -21.5
    ..15.5): fully INSIDE the 44 faces — nothing pokes the flush column.
    Z0 = ground."""
    b = box_at(SQ_W, SQ_W, FOOT_H, z=FOOT_H / 2)
    b = b.union(cq.Workplane("XZ")
                .polyline([(-14.8, FOOT_H), (-13.3, FOOT_H + 5.8),
                           (13.3, FOOT_H + 5.8), (14.8, FOOT_H)])
                .close().extrude(37.0).translate((0, 15.5, 0)))
    return b


def leg_washer() -> cq.Workplane:
    """TPU gland washer: drops over the male thread onto the Ø40 collar and
    lives in the female rim's 2.0-deep recess; bottoming the joint on its
    hard stop squeezes it a fixed 2.5→2.0 (20%) — identical preload +
    damping every assembly. (The drawn assembly shows it at free height,
    0.5 proud into the recess roof — a designed compression.)"""
    return cyl(WASHER_OD, WASHER_T, z=0.0).cut(cyl(WASHER_ID, WASHER_T + 2, z=-1))
