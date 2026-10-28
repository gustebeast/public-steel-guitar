# -*- coding: utf-8 -*-
"""MKS SERVO42D on its NEMA17 -- MEASURED off the delivered unit (user, 2026-10-20).

The build draws every motor with this (components.motor_parts), one solid per material, so
the viewer shows the part as it is: a black-painted can with its laminations bare on the
chamfers, a machined aluminium face, a ground steel shaft, the driver in its own black
finned housing, green and blue screw terminals, and the motor's coil lead looping from
the white plug on the rear cap back into the blue block.

Frame, same as components.motor(): shaft along +Y, centred on X = Z = 0; the FACEPLATE is
y = 0 and everything else is -Y. The coil plug, its lead and the blue 4-way are on +Z; the
6-way (V+ GND COM EN STP DIR) is on +X, the 5-way (5V GND IN1 CANH CANL) on -X, and the
three buttons sit on the BACK face along the -Z edge.

WHERE EVERY NUMBER COMES FROM:
  MEASURED (user's calipers, 2026-10-20)
    * TOTAL_L 53.2  faceplate to the back of the driver's ribs (first read 53.4)
    * LOWER_L 51.6  ...and below the ribs, to the two lower back-plate screw heads: the
                    extent over the lower section, which is what the bay's back wall stops
    * SQ 42.0       the can across its flats, and DRV_SQ 42.5 the driver's cover, the
                    widest part (NEMA17 nominal 42.3: the bank keeps 42.3 for its pitch, so
                    the bay's 0.4 slip fit is 0.55 round the can and 0.30 round the cover).
                    Every height below "over the motor's bottom" is off the CAN's flat.
    * HEIGHT 51.1   bottom flat to the top of the coil lead's loop -> LOOP_TOP 29.9
    * SHAFT_L 21.5  the shaft ("rotor") from the FACEPLATE: 19.5 proud of the 2.0 pilot
                    boss (user, 2026-10-28; the 19.4 it was had been read from the boss and
                    drawn from the face). A D: 4.5 across its flat, the flat facing +Z.
    * BOSS 22 x 2   the pilot
  SCALED off the user's video of it (PXL_20261020_163421716), against the measured 53.4
  and 42.4 (side-on frame ~13.3 px/mm, back-on ~13.8 px/mm), +-0.5:
    * the can: front cap 8.3, laminations 22.5, rear cap 9.2 -> 40.0 (the vendor's "40mm"
      motor) -- so the driver is 13.4: a 10.4 housing and 3.0 of ribs and screw heads.
    * the terminal blocks' places and depths, the button row, the rib pattern, the plug.
  STANDARD: the NEMA17 bolt square (31), M3 holes, the 2.5 pitch of the terminals (measured) and
  of the coil plug, a 4.1 corner chamfer.

The screw terminals take a SMALL FLAT-BLADE screwdriver (2.0-2.5 mm blade) from the back.
That is the one exception to the single-hex-key rule (user, 2026-10-20): it is a bought
part's own hardware, and it is a bench tool, not one stowed on the instrument.
"""
from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_y

# -- measured --------------------------------------------------------------------------
SQ = D.MOTOR_SQ_MEASURED       # 42.0: the can across its flats
DRV_SQ = D.MOTOR_DRIVER_SQ_MEASURED    # 42.5: the driver's cover
DRV_HALF = DRV_SQ / 2
TOTAL_L = D.MOTOR_BODY_L       # 53.2 faceplate -> back of the driver's ribs
LOWER_L = D.MOTOR_LOWER_L_MEASURED   # 51.6 ...to the lower screw heads, under the ribs
LOOP_TOP = D.MOTOR_HEIGHT_MEASURED - DRV_SQ / 2  # 29.85: the loop, over the axis (the
                                                 # height was taken off the cover's flat)
PILOT_D, PILOT_H = D.NEMA17_PILOT_D, 2.0
SHAFT_L = PILOT_H + D.MOTOR_SHAFT_PROUD   # 21.5 from the faceplate (see the docstring)
SHAFT_CUT_L = PILOT_H + D.MOTOR_SHAFT_CUT  # 18.0: as installed, cut (dimensions.MOTOR_SHAFT_CUT)
HALF = SQ / 2

# -- the can (scaled off the video) -----------------------------------------------------
BODY_L = 40.0                  # faceplate -> the can's back face
CAP_F, CAP_R = 8.3, 9.2        # front and rear end caps; the laminations between them
FACE_T = 0.6                   # the machined (bare aluminium) skin of the front cap's face
PAINT_T = 0.3                  # the black paint on the lamination stack's FLATS; the
                               # chamfers are bare steel (the silver band on the video)
CHAMFER = 4.1                  # corner chamfer leg
BOLT_SQ = D.NEMA17_BOLT_SQ
M3_TAP_D, M3_TAP_DEPTH = 2.5, 4.5

# the coil connector on the rear cap's top: a black socket at the back edge, the white
# plug mated in front of it, its four wires out of the plug's top
SOCK_W, SOCK_Y0, SOCK_Y1, SOCK_H = 12.4, -40.0, -37.0, 3.8
PLUG_W, PLUG_Y0, PLUG_Y1, PLUG_H = 12.4, -37.0, -31.0, 5.7
PLUG_PITCH = 2.5

# -- the driver (SERVO42D) ---------------------------------------------------------------
DRV_Y0 = -BODY_L               # its face against the can
DRV_BACK = -50.4               # its housing's back face; ribs and screw heads stand off it
RIB_H = TOTAL_L - (-DRV_BACK)  # 2.8
RIB_T = 1.0
TERM_PITCH = 2.5                # MEASURED (user, 2026-10-20): 6-way inside span 14.47, one cell
                               # 1.95-2.00 -> (14.47 - cell)/5 = 2.49-2.50; 2.54 would need 1.77
TERM_W = 5.0                   # green block, across X (it stands in a notch in the side)
TERM_INSET = 1.3               # MEASURED (user, 2026-10-20): the 6-way's wire face stands this
                               # far in from the can's side flat, in a notch open to the side
# MEASURED (user, 2026-10-20, roughly -- treat as +-1): each green block's bottom over the
# motor's bottom flat. The 6-way (+X) sits lower than the 5-way (-X).
TERM_BOTTOM = {6: 13.1, 5: 16.7}      # keyed by way count (TERM_6_N, TERM_5_N below)
TERM_Y0 = -44.4                # its front (motor-side) face; it runs back to -TOTAL_L
TERM_5_N, TERM_6_N, TERM_4_N = 5, 6, 4
TERM_HOLE = 1.8                # wire entry, square
TERM_HOLE_D = 3.0
TERM_HOLE_Y = -47.0            # wire entry's centre along Y
TSCREW_D, TSCREW_DEPTH = 2.2, 1.0    # the screw well in the back face; head 0.2 under it
TSCREW_SLOT = 0.4
BLUE_H = 4.8                   # blue 4-way, down from the top flat
BLUE_HOLE_Y = -46.0
SCREW_HEAD_D, SCREW_HEAD_H = 4.6, 1.4    # corner pan heads (Phillips)
SCREW_BOSS_D = 6.0
BAND_Z1 = -6.5                 # the ribs stand off the back only ABOVE this; under it the
                               # back is the housing and the two lower screw heads (LOWER_L)
BTN_SLOT = (19.0, 6.0, 2.0)    # x, z, depth of the button slot in the band
BTN_ZC, BTN_PITCH, BTN_SQ, BTN_H = -15.6, 5.8, 2.8, 1.6
LOGO, LOGO_H, LOGO_ZC = "MKS", 6.0, 6.5

WIRE_D = 1.2
WIRE_COLOURS = ("red", "black", "blue", "green")    # -X to +X, as on the blue block


def _square(length, y_far, size=SQ):
    """A chamfered-corner square prism along Y, its -Y face at y_far."""
    return (cq.Workplane("XZ").rect(size, size).extrude(-length).edges("|Y").chamfer(CHAMFER)
            .translate((0, y_far, 0)))


def _band(y0, y1, size=SQ):
    """The chamfered square between y0 > y1, as a clip for anything near the corners."""
    return _square(y0 - y1, y1, size)


def _bolt_xz():
    return [(sx * BOLT_SQ / 2, sz * BOLT_SQ / 2) for sx in (1, -1) for sz in (1, -1)]


def _terminals():
    """{(name): box} of the three terminal blocks' envelopes, in the motor frame."""
    ty = (TERM_Y0 - TOTAL_L) / 2
    tl = TOTAL_L + TERM_Y0
    out = {}
    for side, n in ((1, TERM_6_N), (-1, TERM_5_N)):
        out[side] = box_at(TERM_W, tl, n * TERM_PITCH, x=side * _term_xc(), y=ty,
                           z=_term_zc(n))
    out[0] = box_at(TERM_4_N * TERM_PITCH, tl, BLUE_H, x=0.0, y=ty, z=DRV_HALF - BLUE_H / 2)
    return out


def _term_xc():
    """|x| of a green block's centre: its wire face TERM_INSET inside the side flat."""
    return HALF - TERM_INSET - TERM_W / 2


def _term_zc(n):
    return TERM_BOTTOM[n] - SQ / 2 + n * TERM_PITCH / 2


def _notches():
    """The housing's side notches: each green block's envelope run out through the side flat,
    so the wire entries stay open to the side."""
    t = _terminals()
    out = []
    for side, n in ((1, TERM_6_N), (-1, TERM_5_N)):
        b = t[side].val().BoundingBox()
        out.append(box_at(DRV_HALF - (HALF - TERM_INSET) + 0.1, b.ylen, b.zlen,
                          x=side * (DRV_HALF + HALF - TERM_INSET + 0.1) / 2,
                          y=(b.ymin + b.ymax) / 2,
                          z=(b.zmin + b.zmax) / 2))
    return out


# WHAT EACH GREEN WAY CARRIES (Makerbase schematic MKS SERVO42D_CAN V1.0_003), way 1 first.
SIX_WAY = ("V+", "GND", "COM", "EN", "STP", "DIR")     # +X block: power and step/dir
FIVE_WAY = ("5V", "GND", "IN1", "CANH", "CANL")        # -X block: CAN
# ⚠ ASSUMED, not seen: way 1 is each block's TOP (+Z) end. The silkscreen beside the blocks
# settles it; if it is the bottom, flip this and the drop leads re-route themselves.
WAY1_TOP = True


def terminal_way(block, net):
    """(x, y, z) in the motor frame where the wire for `net` enters its block -- on the
    block's wire face, at its hole -- and the exit direction (+-1, 0, 0). `block` is 6 or 5."""
    names = SIX_WAY if block == TERM_6_N else FIVE_WAY
    side = 1 if block == TERM_6_N else -1
    k = names.index(net)                            # 0-based way
    j = (block - 1 - k) if WAY1_TOP else k          # index into _ways, which runs bottom-up
    return ((side * (HALF - TERM_INSET), TERM_HOLE_Y, _term_zc(block) + _ways(block)[j]),
            (float(side), 0.0, 0.0))


def _ways(n):
    return [(k - (n - 1) / 2) * TERM_PITCH for k in range(n)]


# -- the can ---------------------------------------------------------------------------
def can_body() -> cq.Workplane:
    """Black: the front cap behind its face skin, the paint on the stack's flats, the rear
    cap, the pilot boss and the coil socket."""
    b = _square(CAP_F - FACE_T, -CAP_F)
    b = b.union(_square(CAP_R, -BODY_L))
    for sx in (1, -1):        # the paint on the four flats of the stack
        b = b.union(box_at(PAINT_T, BODY_L - CAP_F - CAP_R, 2 * (HALF - CHAMFER),
                           x=sx * (HALF - PAINT_T / 2), y=-(CAP_F + BODY_L - CAP_R) / 2))
        b = b.union(box_at(2 * (HALF - CHAMFER), BODY_L - CAP_F - CAP_R, PAINT_T,
                           z=sx * (HALF - PAINT_T / 2), y=-(CAP_F + BODY_L - CAP_R) / 2))
    b = b.union(cyl_y(PILOT_D, PILOT_H + FACE_T, y0=-FACE_T))   # through the face skin
    b = b.union(box_at(SOCK_W, SOCK_Y1 - SOCK_Y0, SOCK_H, y=(SOCK_Y0 + SOCK_Y1) / 2,
                       z=HALF + SOCK_H / 2))
    b = b.cut(cyl_y(D.MOTOR_SHAFT_D, PILOT_H + 0.2, y0=-0.1))     # the shaft's own hole
    for x, z in _bolt_xz():
        b = b.cut(cyl_y(M3_TAP_D, M3_TAP_DEPTH + 0.1, y0=-M3_TAP_DEPTH, x=x, z=z))
    return b


def face() -> cq.Workplane:
    """The machined aluminium face of the front cap (round the boss and the bolt holes)."""
    f = _square(FACE_T, -FACE_T)
    f = f.cut(cyl_y(PILOT_D, FACE_T + 0.2, y0=-FACE_T - 0.1))     # the boss comes through
    for x, z in _bolt_xz():
        f = f.cut(cyl_y(M3_TAP_D, FACE_T + 0.2, y0=-FACE_T - 0.1, x=x, z=z))
    return f


def stack() -> cq.Workplane:
    """The lamination stack: bare steel, showing on the chamfers; its flats are painted."""
    ln = BODY_L - CAP_F - CAP_R
    s = _square(ln, -(BODY_L - CAP_R))
    return s.intersect(box_at(SQ - 2 * PAINT_T, ln, SQ - 2 * PAINT_T,
                              y=-(CAP_F + BODY_L - CAP_R) / 2))


def shaft() -> cq.Workplane:
    """Ground steel, from the face to SHAFT_CUT_L out (cut down from the bought SHAFT_L), its
    D flat (MOTOR_SHAFT_FLAT across, the last MOTOR_SHAFT_FLAT_L of the BOUGHT shaft) facing +Z.
    The part inside the can is not drawn."""
    r = D.MOTOR_SHAFT_D / 2.0
    z0 = D.MOTOR_SHAFT_FLAT - r                      # the flat's height over the axis
    flat = box_at(2 * r + 1.0, D.MOTOR_SHAFT_FLAT_L + 1.0, r + 1.0 - z0,
                  y=SHAFT_L - (D.MOTOR_SHAFT_FLAT_L - 1.0) / 2.0, z=(z0 + r + 1.0) / 2.0)
    return cyl_y(D.MOTOR_SHAFT_D, SHAFT_CUT_L, y0=0.0).cut(flat)


def coil_plug() -> cq.Workplane:
    """The white plug, mated into the socket, wires out of its top."""
    p = box_at(PLUG_W, PLUG_Y1 - PLUG_Y0, PLUG_H, y=(PLUG_Y0 + PLUG_Y1) / 2,
               z=HALF + PLUG_H / 2)
    p = p.edges("|Y and >Z").chamfer(0.6)
    for k in range(4):                     # the wire entries; each lead starts 1.5 down one
        p = p.cut(box_at(TERM_HOLE, TERM_HOLE, 3.0, x=(k - 1.5) * PLUG_PITCH,
                         y=(PLUG_Y0 + PLUG_Y1) / 2, z=HALF + PLUG_H))
    return p


# -- the driver -------------------------------------------------------------------------
def driver() -> cq.Workplane:
    """The black housing: its body, the ribs and logo on its back, the raised lower band
    with the button slot, the screw bosses -- notched for the three terminal blocks."""
    d = _square(DRV_Y0 - DRV_BACK, DRV_BACK, DRV_SQ)
    yr = DRV_BACK - RIB_H / 2
    feats = []
    for z in (18.5, 16.5, 14.5):                    # the two rib stacks beside the blue block
        for sx in (1, -1):
            feats.append(box_at(6.2, RIB_H, RIB_T, x=sx * 8.9, y=yr, z=z))
    feats.append(box_at(DRV_SQ, RIB_H, 1.6, y=yr, z=10.6))       # the bar under them
    for z in (2.6, 0.2):                                         # middle ribs
        feats.append(box_at(24.0, RIB_H, RIB_T, y=yr, z=z))
    for z in (-2.5, -4.8):                                       # side columns
        for sx in (1, -1):
            feats.append(box_at(5.0, RIB_H, RIB_T, x=sx * 10.5, y=yr, z=z))
    # (NO raised lower band to the ribs' line: under the ribs the back is the housing itself,
    #  and only the two lower screw heads stand off it, to LOWER_L -- user, 2026-10-20)
    for x, z in _bolt_xz():
        if z > 0:
            feats.append(cyl_y(SCREW_BOSS_D, RIB_H - SCREW_HEAD_H, y0=-TOTAL_L + SCREW_HEAD_H,
                               x=x, z=z))
    for f in feats:
        d = d.union(f)
    logo = (cq.Workplane("XZ").text(LOGO, LOGO_H, RIB_H, halign="center", valign="center",
                                    kind="bold")
            .translate((-1.0, DRV_BACK, LOGO_ZC)))
    d = d.union(logo)
    d = d.intersect(_band(DRV_Y0, -TOTAL_L, DRV_SQ))             # nothing past the corners
    bx, bz, bd = BTN_SLOT
    d = d.cut(box_at(bx, bd + 0.1, bz, y=DRV_BACK + (bd - 0.1) / 2, z=BTN_ZC))
    for t in list(_terminals().values()) + _notches():
        d = d.cut(t)
    return d


def terminals() -> dict:
    """{"green": the 5-way and 6-way, "blue": the coil 4-way}, wire holes and screw wells cut."""
    t = _terminals()
    green = t[1].union(t[-1])
    for side, n in ((1, TERM_6_N), (-1, TERM_5_N)):
        for dz in _ways(n):
            green = green.cut(box_at(TERM_HOLE_D * 2, TERM_HOLE, TERM_HOLE,
                                     x=side * (HALF - TERM_INSET), y=TERM_HOLE_Y,
                                     z=_term_zc(n) + dz))
            green = green.cut(cyl_y(TSCREW_D, TSCREW_DEPTH + 0.1, y0=-TOTAL_L - 0.1,
                                    x=side * _term_xc(), z=_term_zc(n) + dz))
    blue = t[0]
    for dx in _ways(TERM_4_N):
        blue = blue.cut(box_at(TERM_HOLE, TERM_HOLE, TERM_HOLE_D * 2, x=dx, y=BLUE_HOLE_Y,
                               z=DRV_HALF))
        blue = blue.cut(cyl_y(TSCREW_D, TSCREW_DEPTH + 0.1, y0=-TOTAL_L - 0.1, x=dx,
                              z=DRV_HALF - BLUE_H / 2))
    return {"green": green, "blue": blue}


def _slotted(x, z):
    """A terminal's slotted screw head at the bottom of its well."""
    y0 = -TOTAL_L + TSCREW_DEPTH
    h = cyl_y(TSCREW_D - 0.3, 0.6, y0=y0 - 0.6 - 0.2, x=x, z=z)
    return h.cut(box_at(TSCREW_D, 0.5, TSCREW_SLOT, x=x, y=y0 - 0.2 - 0.6 + 0.25, z=z))


def screws() -> dict:
    """{"corner": the four pan heads, "terminal": the fifteen slotted terminal screws}."""
    corner = None
    for x, z in _bolt_xz():
        yb = -TOTAL_L if z > 0 else -LOWER_L                     # upper on bosses, lower bare
        hh = SCREW_HEAD_H if z > 0 else DRV_BACK + LOWER_L       # a lower head ends on the housing
        h = cyl_y(SCREW_HEAD_D, hh, y0=yb, x=x, z=z)
        for w, t in ((2.6, 0.6), (0.6, 2.6)):                    # the Phillips cross
            h = h.cut(box_at(w, 1.2, t, x=x, y=yb + 0.5, z=z))
        corner = h if corner is None else corner.union(h)
    term = []
    for side, n in ((1, TERM_6_N), (-1, TERM_5_N)):
        term += [_slotted(side * _term_xc(), _term_zc(n) + dz) for dz in _ways(n)]
    term += [_slotted(dx, DRV_HALF - BLUE_H / 2) for dx in _ways(TERM_4_N)]
    ts = term[0]
    for s in term[1:]:
        ts = ts.union(s)
    return {"corner": corner, "terminal": ts}


def buttons() -> cq.Workplane:
    _, _, bd = BTN_SLOT
    y0 = DRV_BACK + bd
    out = None
    for i in (-1, 0, 1):
        b = box_at(BTN_SQ, BTN_H, BTN_SQ, x=i * BTN_PITCH, y=y0 - BTN_H / 2, z=BTN_ZC)
        out = b if out is None else out.union(b)
    return out


def coil_lead() -> dict:
    """{colour: wire}: out of the plug's top, up over the socket to LOOP_TOP, and down into
    the blue block's wire holes (2 mm in). The cable's mitred elbows stand a little past its
    across-corners, so the loop is drawn once, measured, and drawn again to touch LOOP_TOP."""
    from cadkit.cables import oct_cable
    yp = (PLUG_Y0 + PLUG_Y1) / 2
    zp = HALF + PLUG_H - 1.5               # inside the plug's own wire entry

    def draw(zt):
        out = {}
        for (colour, xt), xp in zip(zip(WIRE_COLOURS, _ways(TERM_4_N)),
                                    [(k - 1.5) * PLUG_PITCH for k in range(4)]):
            pts = [(xp, yp, zp), (xp, yp, zt - 1.6), (xp, yp - 1.6, zt),
                   (xt, BLUE_HOLE_Y + 1.6, zt), (xt, BLUE_HOLE_Y, zt - 1.6),
                   (xt, BLUE_HOLE_Y, DRV_HALF - 2.0)]
            out[colour] = oct_cable(pts, WIRE_D)
        return out

    zt = LOOP_TOP - WIRE_D / 2
    over = max(w.val().BoundingBox().zmax for w in draw(zt).values()) - LOOP_TOP
    return draw(zt - over)


# -- the unit --------------------------------------------------------------------------
# suffix -> (colour, finish). The build names each part motor_<suffix>_<i> and the body
# motor_<i>; the colours are the build's (sRGB), the finishes cadkit.web.finishes names.
LOOK = {
    "":              ((0.05, 0.05, 0.055), "painted"),    # the can: black paint
    "face":          ((0.80, 0.81, 0.82), "aluminium"),   # machined front face
    "stack":         ((0.42, 0.42, 0.44), "steel"),       # laminations, bare on the chamfers
    "shaft":         ((0.78, 0.79, 0.80), "polished"),
    "coil_plug":     ((0.93, 0.93, 0.90), "nylon"),       # white JST plug
    "driver":        ((0.04, 0.04, 0.045), "painted"),    # the driver's black housing
    "terminal":      ((0.25, 0.62, 0.32), "nylon"),       # green 5-way + 6-way
    "coil_terminal": ((0.15, 0.55, 0.88), "nylon"),       # blue 4-way
    "screws":        ((0.82, 0.82, 0.84), "steel"),       # four corner pan heads
    "term_screws":   ((0.72, 0.72, 0.74), "steel"),       # the terminals' slotted screws
    "buttons":       ((0.80, 0.78, 0.72), "nylon"),
    "lead_red":      ((0.85, 0.10, 0.10), "pvc"),
    "lead_black":    ((0.06, 0.06, 0.06), "pvc"),
    "lead_blue":     ((0.10, 0.25, 0.85), "pvc"),
    "lead_green":    ((0.10, 0.60, 0.25), "pvc"),
}
SUFFIXES = tuple(k for k in LOOK if k)


def parts() -> list:
    """[(suffix, solid, colour, finish)], one solid per material."""
    t, s, w = terminals(), screws(), coil_lead()
    solids = {"": can_body(), "face": face(), "stack": stack(), "shaft": shaft(),
              "coil_plug": coil_plug(), "driver": driver(), "terminal": t["green"],
              "coil_terminal": t["blue"], "screws": s["corner"], "term_screws": s["terminal"],
              "buttons": buttons()}
    solids.update({"lead_" + c: w[c] for c in WIRE_COLOURS})
    return [(k, solids[k]) + LOOK[k] for k in LOOK]


def servo42d() -> cq.Workplane:
    """The whole unit as one compound (no booleans: the parts only touch)."""
    return cq.Workplane("XY").add(cq.Compound.makeCompound(
        [v for _, wp, _, _ in parts() for v in wp.vals()]))


def report() -> str:
    b = servo42d().val().BoundingBox()
    return ("SERVO42D: %.2f behind the faceplate (can %.1f + driver %.1f), shaft %.1f out; "
            "x %.2f..%.2f  z %.2f..%.2f (height %.2f)"
            % (-b.ymin, BODY_L, -b.ymin - BODY_L, b.ymax, b.xmin, b.xmax, b.zmin, b.zmax,
               b.zmax - b.zmin))


if __name__ == "__main__":
    import pathlib
    from cadkit.web import show
    out = pathlib.Path(__file__).resolve().parent.parent / "servo42d"
    out.mkdir(exist_ok=True)
    print(report())
    show([("servo42d" + ("_" + k if k else ""), wp, rgb, fin) for k, wp, rgb, fin in parts()],
         root=out, title="SERVO42D")
