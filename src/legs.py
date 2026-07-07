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

KEYED FINE STAGE: the shaft carries flats (17 across, ±X) and the sleeve
bore matches, so the fine adjust is pure Z travel and the foot end of the
leg is clocked all the way from the chassis (flats are 180°-symmetric, so
the mirrored +Y-rail stacks key identically). The shaft's bottom 9..29 is a
WAIST (Ø18 / 16 across flats): the pedal bar's end plate wraps it, the two
shoulders capture the bar in Z, and the waist never enters the sleeve.

The SOCKET joins the rail with GLUED JOINERY, no fasteners: a vertical
dovetail tenon slides UP into a slot in the rail's outer face from below
until the barrel's top rim seats flat against the rail's bottom flange.
Ground reaction = large-area rim compression; bending/torsion = the dovetail
flanks + glue; the joint is invisible from outside. Sockets sit at x −18.4
(bridge) and −601.6 (keyhead), both rails — solid web, clear of the endplate
dovetails (positions computed in chassis.py; see LEG_STATIONS_X there). The socket is a separate part ONLY because the chassis can't
print below its bed, which is exactly the case glue is for.

All printed standing (tubes along Z): threads print cleanly, no supports.
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
SHAFT_FLAT_W  = 17.0                   # shaft key flats, across ±X
SLEEVE_FLAT_W = 17.4                   # matching sleeve-bore flats (0.2/side)
WAIST_D, WAIST_FLAT_W = 18.0, 16.0     # pedal-bar waist at the shaft bottom
WAIST_Z0, WAIST_Z1 = 9.0, 29.0         # waist band (z from the shaft bottom;
                                       # starts where the foot cap ends)
WAIST_CHORD_Y = 7.0                    # front CHORD flat on the waist (local
                                       # +Y; the rotated +Y-rail stacks aim it
                                       # at the bar mouth): the latch bolt
                                       # bears FLAT-on-flat — normal pure Y,
                                       # no cam-open component, 0.2 play.
                                       # NOTE: breaks the waist's 180° symmetry
                                       # — assemble shafts chord-toward-player
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
    return heal(body)   # helical-thread booleans need a ShapeFix pass


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
    # keyed bore: Ø20.4 with 17.4-across flats (±X) — the shaft cannot rotate,
    # the fine adjust is pure Z, and the pinch closes flat-on-flat
    body = body.cut(cyl(SHAFT_D + 0.4, SLEEVE_L + TH_LEN, z=-SLEEVE_L - 1)
                    .intersect(box_at(SLEEVE_FLAT_W, SHAFT_D + 4,
                                      SLEEVE_L + TH_LEN + 2,
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


def _keyed(d: float, flat_w: float, h: float, z: float) -> cq.Workplane:
    """Cylinder Ø d with ±X flats flat_w across, height h, base at z."""
    return cyl(d, h, z=z).intersect(box_at(flat_w, d + 2, h + 2, z=z + h / 2))


def leg_shaft() -> cq.Workplane:
    """Lower sliding shaft: Ø20 with 17-across key flats (±X) so the fine
    stage cannot rotate (the sleeve bore matches), plus the bottom WAIST
    (Ø18 / 16 across, z 9..29) the pedal bar's end plate wraps — the two
    shoulders capture the bar in Z; the sleeve never reaches down to the
    waist (exposure stays ≥ ~30 with the bar mounted). Solid (slicer
    infills); prints standing — the 1 mm upper waist shoulder is a small
    annular overhang, fine at this size. Foot spigot below."""
    body = _keyed(SHAFT_D, SHAFT_FLAT_W, SHAFT_L, 0.0)
    ring = (_keyed(SHAFT_D + 2, SHAFT_FLAT_W + 2, WAIST_Z1 - WAIST_Z0, WAIST_Z0)
            .cut(_keyed(WAIST_D, WAIST_FLAT_W, WAIST_Z1 - WAIST_Z0 + 2,
                        WAIST_Z0 - 1)))
    body = body.cut(ring)
    # waist front chord (the latch bolt's flat bearing face — see above);
    # cut ONLY in the waist band so the shoulders keep their full round
    body = body.cut(box_at(SHAFT_D + 2, 5.0, WAIST_Z1 - WAIST_Z0,
                           y=WAIST_CHORD_Y + 2.5,
                           z=(WAIST_Z0 + WAIST_Z1) / 2))
    return body


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
