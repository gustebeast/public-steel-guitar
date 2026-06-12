"""Adjustable legs (×4) — PCTG tubes + TPU feet/washers. Quick-attach.

Height: the user's reference is 655 mm of lift at 6'; scaling to typical
players (~5'2"–6'6") needs ~560–710. Stack per leg (ground up): TPU foot →
Ø20 shaft sliding 0–150 in a clamped SLEEVE (continuous fine adjust) → two
identical 190 mm SEGMENTS → the instrument SOCKET. Outside that range, print
a longer/shorter segment (the parts are modular by design).

Quick-attach thread (per the PC-fan-screw idea): 2-start trapezoidal,
Ø36/Ø30 × 9 mm pitch (18 mm lead), 25 mm engagement = 1.4 turns. Every
junction (socket→segment, segment→segment, segment→sleeve) uses the same
thread, so legs break down for transport like real steel legs. Anti-unscrew:
a TPU WASHER under each shoulder compresses on the final quarter turn —
preload + damping; loads in play are axial (nothing torques a leg).

The SOCKET bolts to a rail's outer face (3× M4 into web inserts — stocked
hardware) with its threaded barrel hanging below the floor at the corner;
sockets sit at x −20 (bridge) and −600 (keyhead), both rails. The barrel adds
nothing inside the box and the chassis still prints flat (the socket is a
separate part precisely because the chassis can't grow below its print bed).

All printed standing (tubes along Z): threads print cleanly, no supports.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl, heal

# thread (shared by every junction)
TH_MAJOR, TH_MINOR = 36.0, 30.0
TH_LEAD, TH_STARTS = 18.0, 2          # pitch 9 → 1.4 turns for full engagement
TH_LEN  = 25.0
TH_CLR  = 0.4                          # printed-thread fit (diametral-ish)

TUBE_OD, TUBE_ID = 30.0, 22.0
SEG_L   = 180.0                        # incl. the 25 male thread → 155 effective
SLEEVE_L = 180.0
SHAFT_D, SHAFT_L = 20.0, 200.0
FOOT_H  = 12.0
# stack: 32 barrel + 3×2 washers + 2×155 segments + 180 sleeve + 9 foot
# = 536 fixed + 24..174 of shaft slide → 560..710 floor-to-body (user's 655
# lands at ~119 of exposure)

# socket bracket
PLATE_T, PLATE_W, PLATE_H = 6.0, 46.0, 40.0
BARREL_OD, BARREL_L = 44.0, 32.0
LEG_STATIONS_X = (-20.0, -600.0)       # solid web at both (clear of rail diamonds)


def _thread(rod_r: float, length: float, clr: float = 0.0,
            phase_deg: float = 0.0) -> cq.Workplane:
    """Thread ridges around a rod of radius rod_r: union for a male thread
    (clr=0), cut from a bore for a female one (clr>0 fattens the profile).
    Built as SEGMENTED straight prisms (16 chords/turn, skewed linear
    extrusions) — raw helical sweeps make booleans fragile in OCC; this is the
    same robust approach the belt model uses. At this coarseness the chord
    facets are ~0.1 mm — irrelevant to a printed Ø36 thread."""
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
    """Bolt-on corner socket: plate against the rail's outer face, threaded
    barrel hanging below the floor. Local: rail outer face = Y0 (plate on −Y),
    barrel axis at (0, +Y rail half-thickness…) — placed by build.py; here the
    barrel axis is X0/Y= +PLATE_T? Simplest: barrel axis at origin, plate
    tangent on −Y; bolts along +Y. Z0 = floor plane (barrel extends −Z)."""
    barrel = cyl(BARREL_OD, BARREL_L, z=-BARREL_L)
    plate = box_at(PLATE_W, PLATE_T, PLATE_H,
                   y=-(BARREL_OD / 2 + PLATE_T / 2) + 2.0, z=PLATE_H / 2)
    gusset = box_at(PLATE_W, BARREL_OD / 2 + 2.0, 6.0,
                    y=-(BARREL_OD / 4), z=3.0)
    body = barrel.union(plate).union(gusset)
    # female thread: bore + ridge grooves, opening DOWN
    body = body.cut(cyl(TH_MINOR + TH_CLR, TH_LEN + 2, z=-BARREL_L - 1))
    # one extra lead of groove BELOW the mouth (in free air): prisms whose
    # faces sit under the band would otherwise poke uncut tails into it
    body = body.cut(_thread((TH_MINOR - TH_CLR) / 2, TH_LEN + 2 + TH_LEAD,
                            clr=0.8, phase_deg=60.0)
                    .translate((0, 0, -BARREL_L - 1 - TH_LEAD)))
    # bolt holes through the plate (M4 into rail-web inserts; kept LOW so the
    # inserts land in the rail's solid bottom flange / under the diamonds)
    py = -(BARREL_OD / 2 + PLATE_T) + 2.0
    for bx, bz in ((-16.0, 12.0), (16.0, 12.0), (0.0, 26.0)):
        body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            2.15, PLATE_T + 2, cq.Vector(bx, py - 1, bz), cq.Vector(0, 1, 0))))
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
    # female bell at the bottom
    body = body.union(cyl(BARREL_OD, TH_LEN + 6, z=0.0))
    body = body.cut(cyl(TH_MINOR + TH_CLR, TH_LEN + 1, z=-1))
    body = body.cut(_thread((TH_MINOR - TH_CLR) / 2, TH_LEN + 1 + TH_LEAD,
                            clr=0.8, phase_deg=60.0)
                    .translate((0, 0, -1 - TH_LEAD)))   # extra lead below mouth
    # hollow core (weight)
    body = body.cut(cyl(TUBE_ID, SEG_L - 2 * TH_LEN - 14, z=TH_LEN + 4))
    return heal(body)   # helical-thread booleans need a ShapeFix pass


def leg_sleeve() -> cq.Workplane:
    """Slider sleeve: MALE spigot up top (threads into the lower segment's
    bell), Ø20.4 bore for the shaft, slit clamp end with an insert + M4 set
    screw. Local: Z0 = the shoulder; spigot +Z, body −Z."""
    body = cyl(TUBE_OD + 4, SLEEVE_L, z=-SLEEVE_L)
    spigot = cyl(TH_MINOR - TH_CLR, TH_LEN + 2, z=-2.0)
    spigot = spigot.union(_thread((TH_MINOR - TH_CLR) / 2, TH_LEN + 2)
                          .translate((0, 0, -2.0)))
    body = body.union(spigot)
    body = body.cut(cyl(SHAFT_D + 0.4, SLEEVE_L + TH_LEN, z=-SLEEVE_L - 1))
    # clamp: two slits + a boss with insert + M4 set screw squeezing the bore
    for a in (0, 180):
        sl = box_at(1.6, 26.0, 36.0, y=13.0, z=-SLEEVE_L + 18.0)
        body = body.cut(sl.rotate((0, 0, 0), (0, 0, 1), a + 90))
    boss = box_at(14.0, 12.0, 16.0, y=TUBE_OD / 2 + 2.0, z=-SLEEVE_L + 12.0)
    body = body.union(boss)
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.8, 14, cq.Vector(0, TUBE_OD / 2 + 9, -SLEEVE_L + 12), cq.Vector(0, -1, 0))))
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        2.15, 20, cq.Vector(0, TUBE_OD / 2 + 9, -SLEEVE_L + 12), cq.Vector(0, -1, 0))))
    return heal(body)   # helical-thread booleans need a ShapeFix pass


def leg_shaft() -> cq.Workplane:
    """Lower sliding shaft, Ø20 solid (slicer infills), foot spigot below."""
    return cyl(SHAFT_D, SHAFT_L, z=0.0)


def leg_foot() -> cq.Workplane:
    """TPU foot cap, pressed over the shaft end. Z0 = ground."""
    body = cyl(SHAFT_D + 8.0, FOOT_H, z=0.0)
    return body.cut(cyl(SHAFT_D + 0.2, FOOT_H - 3.0, z=3.0))


def leg_washer() -> cq.Workplane:
    """TPU anti-unscrew washer: sits under each shoulder; the last quarter
    turn compresses it (preload + damping so the coarse thread can't walk)."""
    return cyl(BARREL_OD - 2, 2.0, z=0.0).cut(cyl(TH_MINOR + 1.0, 4.0, z=-1))
