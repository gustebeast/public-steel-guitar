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

The SOCKET joins the rail with GLUED JOINERY, no fasteners: a vertical
dovetail tenon slides UP into a slot in the rail's outer face from below
until the barrel's top rim seats flat against the rail's bottom flange.
Ground reaction = large-area rim compression; bending/torsion = the dovetail
flanks + glue; the joint is invisible from outside. Sockets sit at x −18.4
(bridge) and −601.6 (keyhead), both rails — solid web, clear of the endplate
dovetails (positions computed in chassis.py; see LEG_STATIONS_X there). The socket is a separate part ONLY because the chassis can't
print below its bed, which is exactly the case glue is for.

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
SLEEVE_L = 180.0
SHAFT_D, SHAFT_L = 20.0, 210.0         # 210 keeps 26 retained at 184 exposure —
                                       # the extra 10 buys the pedal bar its
                                       # ≥30 floor without opening band gaps
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
# from the shared endplate<->leg model (chassis.LEG_STATIONS_X): each station is set
# so the leg's dovetail tenon leaves the same EP_LEG_BUFFER (10mm) of solid body to
# its endplate wall, mirrored at both ends. It lives there (not here) because it
# depends on the endplate tip positions, which are chassis constants. Result: the +X
# leg at -18.4 and the -X leg at -601.6 -- each placed so its dovetail tenon leaves
# exactly EP_LEG_BUFFER (10mm) of SOLID BODY to the endplate wall (measured from the
# leg-shell face, so the wall<->shell clearance gap doesn't eat into the 10mm).
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
CHJ_MOUTH_Z = -8.2            # chassis-jack mouth plane (socket-local)
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
    body = cyl(TUBE_OD + 4, SLEEVE_L, z=-SLEEVE_L)
    spigot = cyl(TH_MINOR - TH_CLR, TH_LEN + 2, z=-2.0)
    spigot = spigot.union(_thread((TH_MINOR - TH_CLR) / 2, TH_LEN + 2)
                          .translate((0, 0, -2.0)))
    body = body.union(spigot)
    # male shoulder COLLAR + 45° cone (same hard stop as the segment top)
    body = body.union(cyl(COLLAR_D, COLLAR_H, z=0.0))
    body = body.union(cq.Workplane("XY").add(cq.Solid.makeCone(
        (TUBE_OD + 4) / 2, COLLAR_D / 2, 3.0,
        cq.Vector(0, 0, -3.0), cq.Vector(0, 0, 1))))
    # TRRS column way: the keyed bore stops 3 short of the spigot tip —
    # open it (Ø11, same as the segments) so the wired leg's CA-354S cable
    # passes clean through the column
    body = body.cut(cyl(11.0, 6.0, z=22.0))
    # keyed bore: Ø20.4 with ONE flat (local +Y at 7.0) — single-D: the shaft
    # cannot rotate AND can only insert in its one correct orientation
    body = body.cut(cyl(SHAFT_D + 0.4, SLEEVE_L + TH_LEN, z=-SLEEVE_L - 1)
                    .cut(box_at(SHAFT_D + 4, 6.0, SLEEVE_L + TH_LEN + 2,
                                y=SLEEVE_FLAT_Y + 3.0,
                                z=-SLEEVE_L - 1 + (SLEEVE_L + TH_LEN) / 2)))
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
    """Lower sliding shaft: Ø20 with a SINGLE key flat (local +Y at 6.8 —
    placed, it faces the bar's MOUTH) — prints LYING ON THE FLAT (no
    tall-skinny standing print; layer lines run ALONG the shaft, so kick
    bending loads bulk material, and the 43° flat→round junction is
    self-supporting). Single-D keys the sleeve in exactly one orientation,
    and the bed surface doubles as the latch bolt's bearing face (the bar's
    Z: foot cap below, the seated TRRS plug above — the plain end floats up
    freely until gravity returns it). 45° chamfers on the two bed edges
    absorb first-layer elephant foot so the sleeve/slot fits stay true.
    Solid (slicer infills); foot spigot below."""
    body = cyl(SHAFT_D, SHAFT_L, z=0.0).cut(
        box_at(SHAFT_D + 2, 6.0, SHAFT_L + 2,
               y=SHAFT_FLAT_Y + 3.0, z=SHAFT_L / 2))
    # elephant-foot chamfers along the two flat→round bed edges
    xe = math.sqrt((SHAFT_D / 2) ** 2 - SHAFT_FLAT_Y ** 2)
    for sx in (1, -1):
        body = body.cut(
            cq.Workplane("XY")
            .polyline([(sx * (xe - 0.6), SHAFT_FLAT_Y + 0.3),
                       (sx * (xe + 0.3), SHAFT_FLAT_Y + 0.3),
                       (sx * (xe + 0.3), SHAFT_FLAT_Y - 0.6)])
            .close().extrude(SHAFT_L + 2).translate((0, 0, -1)))
    # anti-lift SHELF band — SHARED by every shaft (the TRRS variant only
    # adds its jack dock on top): the full bounding rectangle at the top of
    # the foot band; its underside (z 26) overhangs the bar slot's solid
    # corners (the slot squares only its top 2.4 to slide past) → positive
    # hold-down at BOTH pedal-bar feet. X-symmetric, so the mirrored +Y-rail
    # stacks and the (bar-less) -Y legs all print the same part.
    body = body.union(box_at(20.0, SHAFT_FLAT_Y + 10.0, SHELF_Z1 - SHELF_Z0,
                             x=0.0, y=(SHAFT_FLAT_Y - 10.0) / 2,
                             z=(SHELF_Z0 + SHELF_Z1) / 2))
    for sx in (1, -1):   # band-limited bed-edge chamfers on the shelf
        body = body.cut(
            cq.Workplane("XY")
            .polyline([(sx * (10.0 - 0.6), SHAFT_FLAT_Y + 0.3),
                       (sx * (10.0 + 0.3), SHAFT_FLAT_Y + 0.3),
                       (sx * (10.0 + 0.3), SHAFT_FLAT_Y - 0.6)])
            .close().extrude(SHELF_Z1 - SHELF_Z0 + 0.2)
            .translate((0, 0, SHELF_Z0 - 0.1)))
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


def leg_shaft_trrs() -> cq.Workplane:
    """The -X/+Y leg's shaft: leg_shaft() + the CORNER-FILL extension on the
    inboard half (foot band only): the cylinder's inboard extent extruded to
    a full-width rectangle — a FLAT face for the TRRS jack with a touch more
    material around its pocket, flat X-seat faces for the bar slot, and an
    unmistakable single orientation. Then the X-facing jack pocket
    (SJ-43514-SMT, mouth flush in the flat face) and the Ø6 wire bore up
    the centre. Same lying-flat print: the extension reaches the bed at its
    own chamfered edge (vertical wall — even less overhang than the round),
    its top is flat, and the pocket opens sideways (no bridges); the centre
    bore prints as a long horizontal hole — acceptable sag, nothing fits it
    tightly."""
    body = leg_shaft()
    # TRRS delta 1: corner fill — local -X half → rectangle to x=-10, full
    # width up to the key flat, FOOT BAND only (never enters the sleeve or
    # the foot cap): flat jack face + meat around the pocket + flat slot
    # X-seat (the shared shelf band is already in leg_shaft())
    body = body.union(box_at(10.0, SHAFT_FLAT_Y + 10.0, WAIST_Z1 - WAIST_Z0,
                             x=-5.0, y=(SHAFT_FLAT_Y - 10.0) / 2,
                             z=(WAIST_Z0 + WAIST_Z1) / 2))
    # band-limited bed-edge chamfer on the fill's edge
    body = body.cut(cq.Workplane("XY")
                    .polyline([(-(10.0 - 0.6), SHAFT_FLAT_Y + 0.3),
                               (-(10.0 + 0.3), SHAFT_FLAT_Y + 0.3),
                               (-(10.0 + 0.3), SHAFT_FLAT_Y - 0.6)])
                    .close().extrude(WAIST_Z1 - WAIST_Z0 + 0.2)
                    .translate((0, 0, WAIST_Z0 - 0.1)))
    # jack pocket: local -X (inboard once placed), mouth in the flat face
    body = body.cut(box_at(TRRS_JACK_L + 1.0, TRRS_JACK_W + 0.6,
                           TRRS_JACK_H + 0.6, x=-10.5 + (TRRS_JACK_L + 1.0) / 2,
                           z=TRRS_Z))
    # widened band at the jack's terminal plane: the SJ-4351X's SMT
    # gull-wings splay to ~10 total width (datasheet PCB layout) — wider
    # than the body pocket
    body = body.cut(box_at(TRRS_JACK_L + 1.0, 10.6, 1.6,
                           x=-10.5 + (TRRS_JACK_L + 1.0) / 2,
                           z=TRRS_Z - 2.2))
    # WIRE GALLERY: the pocket's rear half opens upward to the bore mouth —
    # the four wires rise from the gull-wing tabs beside the body, cross
    # over its rear, and gather into the Ø6 centre bore. (Routing the wires
    # to their actual terminals showed the previous 0.3 gap over the jack
    # body was impassable.)
    body = body.cut(box_at(8.0, 10.6, 7.3, x=1.0, z=18.55))
    # CARRIER PCB seat: the jack rides a 1.6 board (factory-assembled, XH
    # header on its UNDERSIDE) — deepen the pocket floor by 2.0 for it
    body = body.cut(box_at(TRRS_JACK_L + 1.0, 7.0, 2.1,
                           x=-10.5 + (TRRS_JACK_L + 1.0) / 2, z=14.35))
    # bottom-entry cavity: the leg-column cable's crimped XH housing mates
    # UPWARD onto the carrier's underside header; the cavity opens at the
    # shaft's bottom face and hides under the TPU foot cap (assemble the
    # housing, then cap the foot). The foot spigot keeps its outer ring.
    body = body.cut(box_at(13.0, 8.0, 15.5, x=-1.5, z=6.65))
    # REAR CHANNEL: the Ø3.7 cable's downway (gallery → bottom cavity),
    # behind the jack. Plug-insertion loads now backstop through the
    # CARRIER BOARD's rear edge on its full-width seat wall (below this
    # channel), not the jack body — the SMT jack is rated for
    # board-carried insertion loads.
    body = body.cut(box_at(4.2, 4.6, 19.8, x=6.7, z=12.3))
    # ── open PRESS-IN CABLE CHANNEL (replaced the enclosed bore): the
    # cable lays in SIDEWAYS at the bench with its housing already crimped
    # — no threading through the shaft, no contact extraction to service
    # (unplug, pop the cable out laterally, slide the shaft off). Azimuth
    # 142° local = DIAGONALLY INWARD once placed (global +x/-y on this
    # -X/+Y leg): invisible from the front and side views; the sleeve
    # cages it over the engaged length. T-slot: Ø4.4 way at r7.7 under a
    # 3.2 mouth (lips grip the Ø3.7 jacket, fully sub-flush of the Ø20).
    # Over the foot band the mouth deepens through the corner-fill /
    # shelf corner (bar-covered when playing, foot-covered below) and
    # lands in the bottom cavity's corner.
    ang = 142.0
    _ca, _sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    body = body.cut(cyl(4.4, 204.0, z=8.0)
                    .translate((7.7 * _ca, 7.7 * _sa, 0)))
    body = body.cut(box_at(5.6, 3.2, 21.2, x=10.3, z=18.5)
                    .rotate((0, 0, 0), (0, 0, 1), ang))
    body = body.cut(box_at(3.4, 3.2, 183.0, x=9.15, z=120.4)
                    .rotate((0, 0, 0), (0, 0, 1), ang))
    # cavity corner reach: the channel's foot lands here; the cable curls
    # across the cavity to the carrier's underside header
    body = body.cut(box_at(5.0, 4.4, 15.0, x=-5.5, y=4.2, z=6.4))
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
SEG_BODY_L = 126.0             # GF body; + 6 male / 8 female coupler
                               # flanges = 140 effective (step stays 142)
PUCK_PLUG_L = 20.0             # coupler glue plug depth into the core
CH_MOUTH, CH_DEEP = 6.0, 7.0   # face cable channel (lidded; Ø3.7 + slack)


def _sq_body(length: float, channel: bool = False) -> cq.Workplane:
    """Square leg body stock: 44×44×length, hollow 32-square core (prints
    lying on a face — the crown of the core self-supports via its 45°
    corner chamfers). channel=True (the WIRED leg's bodies ONLY — user:
    legs are otherwise identical) adds the +Y face CABLE CHANNEL with the
    45° dovetail LID seat (pedal-bar pattern: slide along Z, TPU nub, no
    screws) and a core DIVE hole near each end (cable → core at the
    sleeve joint below and at the latch head above). Z0 = bottom."""
    b = box_at(SQ_W, SQ_W, length, z=length / 2)
    b = b.cut(box_at(SQ_CORE, SQ_CORE, length + 2, z=length / 2))
    if channel:
        hw, yf = CH_MOUTH / 2, SQ_W / 2
        b = b.cut(cq.Workplane("XY")
                  .polyline([(-hw, yf - CH_DEEP), (hw, yf - CH_DEEP),
                             (hw, yf - 1.9), (hw + 3.5, yf - 1.9),
                             (hw + 1.6, yf + 0.1), (-hw - 1.6, yf + 0.1),
                             (-hw - 3.5, yf - 1.9), (-hw, yf - 1.9)])
                  .close().extrude(length + 2).translate((0, 0, -1)))
        for dz in (24.0, length - 24.0):     # channel-floor dive holes
            b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
                2.75, CH_DEEP + 2.0, cq.Vector(0, SQ_W / 2 + 0.5, dz),
                cq.Vector(0, -1, 0))))
    # coupler retention screws (user rule: the snug square JOINERY carries
    # every load; ONE M4 per coupler only prevents extraction the way it
    # went in — no glue, no press fit). Ø4.5 clearance through the -Y
    # wall, 12 in from each end
    for sz in (12.0, length - 12.0):
        b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            2.25, 9.0, cq.Vector(0, -SQ_W / 2 - 1.0, sz),
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
    """PCTG female THREAD COUPLER (prints STANDING, mouth down): 44 sq ×8
    flange whose mouth face carries the TPU-washer GLAND + rim hard-stop
    ring, internal thread rising through the square 32 glue plug. Z0 =
    the mouth face (= body bottom end - 8)."""
    b = box_at(SQ_W, SQ_W, 8.0, z=4.0)
    b = b.union(box_at(SQ_CORE - 0.3, SQ_CORE - 0.3, PUCK_PLUG_L,
                       z=8.0 + PUCK_PLUG_L / 2))
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
    b = b.cut(cyl(22.0, PUCK_PLUG_L - TH_LEN + 8 + 2,
                  z=TH_LEN + 3.0))                     # open core way
    # M4 retention pilot (see coupler_m note)
    b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.8, 8.0, cq.Vector(0, -SQ_CORE / 2 - 0.5, 20.0),
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
SQS_OUT = 52.0                 # passive socket outer square
SQS_WAY = 36.4                 # socket way (spigot 36.0 + 0.4)
SQS_DEPTH = 50.0               # mouth at z -50 (socket-local, 0 = rail
                               # bottom); way roof at -8
SPG_W, SPG_L = 36.0, 40.0      # latch-head spigot (geometric clocking:
                               # one 6×45° keyed corner)
HEAD_BODY_L = 30.0             # head body below the 50-sq shoulder plate
# latch: bolt in the spigot's +y (inboard-placed) face; ledge pocket in
# the socket way wall. Washer preload pushes the head DOWN onto the
# pocket floor = zero play. Bolt/button drawn as functional dummies —
# the 35° wedge coupling + TPU return finger detail at refinement.
BOLT_W, BOLT_H, BOLT_X = 12.0, 8.0, -12.0
LEDGE_Z = -22.2                # pocket floor (socket-local) = retention


def leg_washer_sq() -> cq.Workplane:
    """TPU square gland washer ×4 (top joint): 44 sq × 2.5, 37-sq hole —
    lives in the socket mouth's 2.0-deep recess, squeezed 2.5→2.0 when
    the head's 50-sq shoulder plate hits the mouth face (defined
    compression, same rule as the threaded joints). Z0 = bottom."""
    return (box_at(44.0, 44.0, 2.5, z=1.25)
            .cut(box_at(37.0, 37.0, 4.0, z=1.25)))


def _sq_socket_core() -> cq.Workplane:
    """Shared passive square socket: 52-sq barrel below the rail, square
    way + keyed corner, gland recess, latch LEDGE pocket (+y way wall),
    dovetail tenon on top (chassis interface unchanged). Socket-local:
    z0 = rail bottom."""
    body = box_at(SQS_OUT, SQS_OUT, SQS_DEPTH, z=-SQS_DEPTH / 2)
    # tenon (same joinery as the round socket — copied placement)
    c = 0.3
    tenon = (cq.Workplane("XY")
             .polyline([(-(DT_FACE_HW - c), -4.0), (DT_FACE_HW - c, -4.0),
                        (DT_DEEP_HW - 2 * c, -c), (-(DT_DEEP_HW - 2 * c), -c)])
             .close().extrude(DT_H + DT_DEPTH))
    keep = (cq.Workplane("YZ")
            .polyline([(-5.0, 0.0), (-5.0, DT_H + 4.7), (1.0, DT_H - 1.3),
                       (1.0, 0.0)])
            .close().extrude(2 * DT_DEEP_HW + 4)
            .translate((-(DT_DEEP_HW + 2), 0, 0)))
    body = body.union(tenon.intersect(keep).mirror("XZ"))
    # square way (keyed corner: the +x/+y corner carries a 6×45° fill —
    # the spigot's matching chamfer admits ONE orientation)
    way = box_at(SQS_WAY, SQS_WAY, SQS_DEPTH - 8.0,
                 z=-(SQS_DEPTH + 8.0) / 2 + 0.0)
    way = way.cut(cq.Workplane("XY")
                  .polyline([(SQS_WAY / 2 - 6.2, SQS_WAY / 2),
                             (SQS_WAY / 2, SQS_WAY / 2),
                             (SQS_WAY / 2, SQS_WAY / 2 - 6.2)])
                  .close().extrude(SQS_DEPTH)
                  .translate((0, 0, -SQS_DEPTH - 1)))
    body = body.cut(way)
    # gland recess in the mouth face (44.6 sq × 2 deep, washer 44 sq)
    body = body.cut(box_at(44.6, 44.6, 2.0, z=-SQS_DEPTH + 1.0)
                    .cut(box_at(SQS_WAY - 0.4, SQS_WAY - 0.4, 4.0,
                                z=-SQS_DEPTH + 1.0)))
    # latch LEDGE pocket in the +y way wall (bolt noses in; its underside
    # bears on the pocket floor = the retention/preload face)
    body = body.cut(box_at(BOLT_W + 2.0, 3.7, 9.0,
                           x=BOLT_X, y=SQS_WAY / 2 + 1.75,
                           z=LEDGE_Z + 4.5))
    return body


def leg_socket_sq() -> cq.Workplane:
    """Passive square latch socket ×3 (plain legs). PETG-GF (glued into
    the rail; sustained ground-reaction path)."""
    return _sq_socket_core()


def leg_socket_sq_trrs() -> cq.Workplane:
    """Passive square latch socket ×1 (the -X/+Y WIRED leg): + the
    vertical chassis-jack way re-hosted from the round design — Ø9.7
    coaxial way, mouth-seat boss hanging under the way roof (jack mouth
    -9.3, plug tip +3.7 at seat = 13.0 insertion), tenon cable channel.
    The chassis web bore + slug + 10-03404 carry over unchanged."""
    body = _sq_socket_core()
    body = body.union(cyl(13.0, 4.0, z=-9.9))       # mouth-seat boss (into
    #                                                 the way-roof material)
    body = body.cut(cyl(4.8, 1.4, z=-10.0))         # barrel way thru ring
    body = body.cut(cyl(9.7, 53.0, z=-9.3))         # jack way, open to top
    body = body.cut(box_at(4.4, 8.5, 9.0, y=4.25, z=35.5))   # cable channel
    return body


def leg_latch_head() -> cq.Workplane:
    """LATCH HEAD ×4 (PCTG, prints standing — thread + mechanism quality):
    the leg's top piece. Bottom = the SAME female thread joint (gland +
    rim + Ø36/30 thread) taking any segment's male coupler; middle = the
    50-sq shoulder PLATE (hard stop on the socket mouth, washer under
    it); top = the 36-sq keyed SPIGOT with the bolt channel, recessed
    seatbelt BUTTON pocket on the body's inboard face (x -14 — beside
    the cable channel at x 0), captive TRRS plug seat (Ø11 + Ø9.4 lip;
    leg_plug_retainer presses beneath) and Ø14 cable way. Local z0 =
    shoulder-plate TOP (mounted at socket mouth -50)."""
    b = box_at(50.0, 50.0, 4.0, z=-2.0)                       # shoulder plate
    b = b.union(box_at(SQ_W, SQ_W, HEAD_BODY_L, z=-4.0 - HEAD_BODY_L / 2))
    spig = box_at(SPG_W, SPG_W, SPG_L, z=SPG_L / 2)
    spig = spig.cut(cq.Workplane("XY")                        # keyed corner
                    .polyline([(SPG_W / 2 - 6.0, SPG_W / 2),
                               (SPG_W / 2, SPG_W / 2),
                               (SPG_W / 2, SPG_W / 2 - 6.0)])
                    .close().extrude(SPG_L + 2).translate((0, 0, -1)))
    b = b.union(spig)
    # female thread joint at the bottom (mirrors coupler_f/leg_segment)
    zm = -4.0 - HEAD_BODY_L                                   # mouth face
    b = b.cut(cyl(SQ_W + 4, GLAND_DEPTH + 0.5, z=zm - 0.5)
              .cut(cyl(GLAND_ID, GLAND_DEPTH + 2, z=zm - 1)))
    b = b.cut(cyl(TH_MINOR + TH_CLR, TH_LEN + 1, z=zm - 1))
    b = b.cut(_thread((TH_MINOR - TH_CLR) / 2, TH_LEN + 1 + TH_LEAD,
                      clr=0.8, phase_deg=60.0)
              .translate((0, 0, zm - 1 - TH_LEAD)))
    # TRRS plug seat + cable way down the centre
    b = b.cut(cyl(9.4, 1.5, z=SPG_L - 0.5))                   # tip lip way
    b = b.cut(cyl(11.0, SPG_L - 0.5 - 8.0, z=8.0))            # handle way
    b = b.cut(cyl(14.0, 8.0 + HEAD_BODY_L - TH_LEN + 2.0,
                  z=zm + TH_LEN - 1.0))                       # cable way
    # (NO face channel — user: only the wired leg's SEGMENTS carry the
    # channel; the cable dives into the core at the top segment's upper
    # dive hole and rises through this head's internal Ø14/Ø11 way, which
    # every head carries invisibly — ONE head SKU for all four legs)
    # bolt channel through the spigot's +y face + button pocket on the
    # body's inboard face (functional dummies; wedge detail at refinement)
    b = b.cut(box_at(BOLT_W + 0.4, SPG_W / 2 + 4.0, BOLT_H + 0.4,
                     x=BOLT_X, y=SPG_W / 4 + 1.0, z=SPG_L - 12.0))
    b = b.cut(box_at(12.4, 9.0, 10.4, x=-14.0, y=SQ_W / 2 - 4.4,
                     z=-4.0 - HEAD_BODY_L / 2))
    return heal(b)


def leg_latch_bolt() -> cq.Workplane:
    """Latch BOLT ×4 (PCTG): rigid slider in the spigot channel, 45° nose
    chamfer self-latches on push-in; underside bears on the socket's
    ledge (washer preload = zero play). Drawn ENGAGED. Local = head
    frame."""
    b = box_at(BOLT_W, SPG_W / 2 + 3.0, BOLT_H,
               x=BOLT_X, y=SPG_W / 4 + 0.5, z=SPG_L - 12.0)
    b = b.cut(cq.Workplane("YZ")                     # 45° insertion chamfer
              .polyline([(SPG_W / 2 + 2.0, SPG_L - 12.0 + BOLT_H / 2),
                         (SPG_W / 2 - 1.0, SPG_L - 12.0 + BOLT_H / 2),
                         (SPG_W / 2 + 2.0, SPG_L - 12.0 - BOLT_H / 2 + 1.0)])
              .close().extrude(BOLT_W + 2).translate((BOLT_X - BOLT_W / 2 - 1, 0, 0)))
    return b


def leg_latch_btn() -> cq.Workplane:
    """Latch BUTTON ×4 (PCTG): recessed seatbelt-style pad on the head
    body's inboard face + stem into the mechanism cavity (35° wedge to
    the bolt at refinement). Local = head frame."""
    b = box_at(12.0, 3.0, 10.0, x=-14.0, y=SQ_W / 2 - 1.6,
               z=-4.0 - HEAD_BODY_L / 2)
    b = b.union(box_at(8.0, 6.0, 6.0, x=-14.0, y=SQ_W / 2 - 6.0,
                       z=-4.0 - HEAD_BODY_L / 2))
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


def socket_jack_slug() -> cq.Workplane:
    """Printed saddle slug ×1 (TPU): drops into the socket's jack way on
    top of the seated chassis jack (the side-open slot clears the axial
    cable exit) and fills the bore toward the rail-slot roof — the jack's
    INSERTION backstop after glue-up. Z0 = bottom."""
    b = cyl(9.55, 8.0, z=0.0)
    b = b.cut(box_at(4.4, 9.0, 10.0, y=2.0, z=4.0))
    return b


def chassis_trrs_jack() -> cq.Workplane:
    """DEMO chassis-side jack — Tensility 10-03404 (Ø9.1 × 39.4 molded
    body, Ø3.6 mouth DOWN, factory cable out the top): seated on the
    socket's mouth ring, coaxial with the leg thread. Socket-local."""
    b = cyl(CHJ_D, CHJ_L, z=CHJ_MOUTH_Z)
    b = b.cut(cyl(3.7, 14.5, z=CHJ_MOUTH_Z - 0.2))
    return b


def leg_column_plug() -> cq.Workplane:
    """DEMO column-top plug — the SECOND CA-354S, recessed in the top
    segment's Ø11 bore with its full barrel exposed (handle top 0.2 under
    the tip lip): tip at +4.8 = 13.0 into the chassis jack at seat.
    Socket-local."""
    b = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        1.75, 14.5, cq.Vector(0, 0, -9.7), cq.Vector(0, 0, 1)))
    b = b.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        5.0, 12.6, cq.Vector(0, 0, -9.7), cq.Vector(0, 0, -1))))
    b = b.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        3.0, 16.0, cq.Vector(0, 0, -22.3), cq.Vector(0, 0, -1))))
    return b


def leg_foot() -> cq.Workplane:
    """TPU foot cap, pressed over the shaft end (grips the round sides of the
    keyed shaft; its cap ends exactly where the waist begins). Z0 = ground."""
    body = cyl(SHAFT_D + 8.0, FOOT_H, z=0.0)
    return body.cut(cyl(SHAFT_D + 0.2, FOOT_H - 3.0, z=3.0))


def leg_washer() -> cq.Workplane:
    """TPU gland washer: drops over the male thread onto the Ø40 collar and
    lives in the female rim's 2.0-deep recess; bottoming the joint on its
    hard stop squeezes it a fixed 2.5→2.0 (20%) — identical preload +
    damping every assembly. (The drawn assembly shows it at free height,
    0.5 proud into the recess roof — a designed compression.)"""
    return cyl(WASHER_OD, WASHER_T, z=0.0).cut(cyl(WASHER_ID, WASHER_T + 2, z=-1))
