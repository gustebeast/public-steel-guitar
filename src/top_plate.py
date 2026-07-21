"""Removable top deck — swappable fret-marked BANDS + a pickup-cover piece.

Roles: (1) fret-position lines for the player; (2) dust cover over the motors +
electronics; (3) sound damping; (4) OLED + joystick mount; (5) hand rest; (6) the
pickup carrier.

MULTI-MATERIAL: every panel is TWO aligned parts printed as ONE object (the
ha-keypad keycaps/keycaps_text pattern): `top_plate_N` — the TRANSPARENT PCTG
base (full body below the colour line, plus the fret lines + marker dots
EMBOSSED up to the deck top, so bay light glows through the full plate) — and
`top_plate_N_color` — the COLOUR PCTG layer (the top FRET_T band between the
lines; exact complement, flush top). Same origin; assign one filament per part
in the slicer. BOTH parts are PCTG (never glass-filled): the deck is the
player's forearm rest, and abrasion slowly exposes fiber ends on GF surfaces —
plus same-resin pairs weld and purge cleanest.

Form: the deck is a STACK of panels that ride a GROOVE in both rail inner faces
(a tongue down each Y edge -> can't fall when the instrument is inverted) and
pull straight out -X for service (after the keyhead endplate + nut block come
off; the bridge endplate + a chassis stop ledge cap the +X end). The whole stack
is trapped between that +X ledge and the keyhead endplate, so no panel needs to
latch and none can slide out on its own.

The bridge end is divided into BAND_W-wide slots. A 3-slot PICKUP PIECE carries
the pickup: the pickup pokes up through an opening, depending side skirts form a
channel, and two clamp bolts in X-slots give +/-CLAMP mm of fine X-adjust. The
remaining slot(s) take plain fret-marked FILLER bands. Swapping which slots hold
the piece coarse-moves the pickup (tone: bridge<->neck); the clamp covers every
position in between -> continuous reach (50 mm spec min is comfortably inside).
Because the pickup region is always the same total width, the UI + keyhead
panels downstream never shift.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from . import electronics as EL
from . import pickup_mount as PM
from .helpers import box_at, cyl, cyl_y, heal

YL = CH.Y_LO + CH.T / 2                 # -Y rail inner face (-128.75)
YH = CH.Y_HI - CH.T / 2                 # +Y rail inner face (+54.75)
BY0 = CH.Y_LO - CH.T / 2                # deck cap -Y edge (-Y rail OUTER face)
BY1 = CH.Y_HI + CH.T / 2                # deck cap +Y edge (+Y rail OUTER face)
TZ = EL.DECK_TOP                        # deck surface (10 mm under strings = +6)
BZ = TZ - 6.0                           # 6 mm deck, recessed between the rails

# Deck joint: each plate CAPS both rails and drops a vertical DOVETAIL tongue down
# the rail centre-line into a rail-top groove (chassis.py). Wide foot, narrow mouth
# -> +Z retention (plates can't fall out inverted) AND a Y-tie (the inboard groove
# wall stops the rails spreading). The tongue runs along X -> plates slide out -X.

# Deck X-extent, DERIVED from the endplates so it tracks them. The stack installs
# +X -> -X: the FIRST panel butts the bridge endplate FLUSH (no gap -- you push it home),
# then each panel keeps GAP clearance to the previous so the stack can't bind, and the
# LAST panel stops EP_TOP_CLR short of the keyhead face so the keyhead slides in past the
# seated stack. Fret lines are at absolute X, so this positioning makes every marker land
# true on its panel.
PX0 = D.BRIDGE_BASE_X0                  # +X deck end: FLUSH with the bridge endplate -X face
                                        # (-16.5); +Z held by the rail-top grooves
PX1 = CH.KH_RAIL_X                      # -X deck end: EP_TOP_CLR off the keyhead face
                                        # (-610.6) -> the keyhead can slide in past it
GAP = 0.05                              # assembly clearance between consecutive panels

# ── band slots at the bridge end ─────────────────────────────────────────────
BAND_W   = 20.0                        # one slot (band material width)
N_SLOTS  = 7                           # pickup-region slots
PITCH    = BAND_W + GAP                # slot pitch = band + the gap after it
SLOT_X   = [PX0 - i * PITCH for i in range(N_SLOTS + 1)]   # +X face of each slot
PIECE_SLOTS = 3                        # the pickup piece spans 3 slots
N_POS    = N_SLOTS - PIECE_SLOTS + 1   # = 5 coarse swap positions
CLAMP    = 10.0                        # +/- fine X-adjust (= BAND_W/2 -> continuous)

# shown installed state: piece in the 3 bridge-most slots, fillers behind it
PIECE_SHOWN = 0                        # piece occupies slots [0 .. PIECE_SLOTS)
PIECE_X0 = SLOT_X[PIECE_SHOWN]
PIECE_X1 = PIECE_X0 - (PIECE_SLOTS * BAND_W + (PIECE_SLOTS - 1) * GAP)   # spans its slots
                                       # INCLUDING the 2 internal gaps it absorbs, so
                                       # swapping it for 3 fillers leaves the downstream
                                       # panels (UI, keyhead) put
REGION_X1 = SLOT_X[-1]                  # -X end of the band region (after the last gap)

# the two long panels behind the band region
MID_X0 = REGION_X1                      # carries the UI (string-10 deck band)
MID_X1 = MID_X0 - 226.0                # length picked so the mid/key seam lands in the CLEAR gap between
                                       #   the fret-9 pentagon marker and the fret-8 line (was 220 -> the
                                       #   seam ran through the pentagon); both panels stay < 255 mm bed
KEY_X0 = MID_X1 - GAP                   # keyhead panel, sized so its -X face lands on PX1
KEY_X1 = PX1

# ── pickup-piece interior geometry ───────────────────────────────────────────
# The pickup does NOT rest on the height screws directly (those would block its X
# travel); it rests on a full-width Z-PLATE that the screws lift. The plate slides
# only in Z inside the piece pocket, so the pickup can sit ANYWHERE across its
# +/-CLAMP fine-X range -> that's what lets the piece be only 3 bands wide. Height
# screws thread the floor and are turned from BELOW (a long driver past the belts);
# a side CLAMP screw drives a protective shim that pins the pickup +Y against the
# reference skirt (friction then holds X and, with the plate under it, Z).
PIECE_CTR = (PIECE_X0 + PIECE_X1) / 2                      # -47.5
WALL      = 3.5                                            # piece end walls
OPEN_X0   = PIECE_X0 - WALL                                # +X opening edge (-21.0)
OPEN_X1   = PIECE_X1 + WALL                                # -X opening edge (-74.0)
OPEN_CTR  = (OPEN_X0 + OPEN_X1) / 2                        # -47.5
OPEN_LEN  = OPEN_X0 - OPEN_X1                              # 53.0 = PK_W + 2*CLAMP
SKIRT_T   = 3.0
FLG_T     = 2.5                                            # Z-plate guide-flange thickness
# +Y REFERENCE (user): the pickup seats flush to the +Y wall, positioned so its +Y
# edge JUST covers string 1 (D.nut_y(0), the +Y-most / highest string). The
# Alumitone blade is far longer than the 58.5 string field, so it OVERHANGS -Y past
# string 10; the mount (opening + -Y skirt) is sized to HOLD the overhang.
PK_COVER  = 2.0                                           # +Y margin past string 1
PK_YP     = D.nut_y(0) + PK_COVER                         # pickup +Y face (~31.25)
PK_YM     = PK_YP - PM.PK_L                               # pickup -Y face (~-63.75)
HY_REF    = PK_YP + 0.3 + FLG_T                           # +Y reference skirt (pickup seats -0.3)
HY_CLAMP  = -PK_YM + 7.0                                  # -Y clamp skirt (room: shim + screw)
OPEN_YC   = (HY_REF - HY_CLAMP) / 2                       # opening/floor Y centre
OPEN_YW   = HY_REF + HY_CLAMP                             # opening/floor Y width
# Z-plate the pickup rests on (slides only in Z, lifted by the tripod jacks):
ZPL_T     = 2.0
ZPL_TOP   = PM.PK_BOT                                     # pickup sits on the plate top
ZPL_BOT   = ZPL_TOP - ZPL_T
FLG_BOT   = ZPL_BOT
# wall TOP capped PK_H_MIN above the plate so the walls never top the pickup
FLG_TOP   = ZPL_TOP + PM.PK_H_MIN
FLOOR_BOT = ZPL_BOT - 5.2                                 # piece bottom -- DEEP for the 22mm
                                                         # pickup's tripod tabs/pads (now below
                                                         # the -14 ribs; the neck-slide collision
                                                         # is a TODO the user will review)
# ── TOP-ACCESS jackscrews (user: adjust height with the instrument assembled) ──
# THREE vertical M2 GRUB-SCREW jacks in a TRIPOD (deterministic, no rock): TWO on
# the +Y reference side just OUTBOARD of string 1, at the two X-ends (beyond the
# pickup in X); ONE on the -Y side at CENTRE X, outboard of the pickup's -Y edge.
# All three sit outboard of the strings so a driver reaches them from +Z. Each
# threads a downward TAB on the plate; its tip bears on a FIXED pad in the piece
# below. Turn CW to jack that corner up; the fine thread self-locks. LEVELLING: the
# -Y screw is at centre X (no along-neck moment), so EQUALISING the two +Y screws =
# X LEVEL; the -Y screw then sets ACROSS-STRING tilt.
JACK_YP       = D.nut_y(0) + 2.25                # +Y jacks: just outboard of string 1
JACK_YM       = PK_YM - 3.0                       # -Y jack: just outboard of the pickup -Y edge
JACK_POS      = [(OPEN_X0 - 3.5, JACK_YP),        # +X end, +Y
                 (OPEN_X1 + 3.5, JACK_YP),        # -X end, +Y
                 (PIECE_CTR, JACK_YM)]            # centre X, -Y
JACK_D        = 2.0                              # M2
JACK_TAB_OD   = 4.5                              # plate threaded-tab OD
JACK_TAB_BOTZ = ZPL_BOT - 3.0                    # tab bottom (3mm thread below the plate)
JACK_PAD_TOPZ = JACK_TAB_BOTZ - 0.4              # fixed pad top (screw tip bears here)
HEIGHT_HOLE = PIECE_CTR
# X clamp: THREE clamp-screw holes along the -Y skirt -> use the one nearest the
# pickup so the side clamp pushes near the pickup centre wherever it's slid. The
# shim spreads the load, so the hole needn't line up exactly with the midpoint.
CLAMP_HOLES = [PIECE_CTR - 18.0, PIECE_CTR, PIECE_CTR + 18.0]
CL_Z      = -4.0                                          # side clamp screw / shim height
CLAMP_SHIM_Y = PK_YM - 1.0                                # shim bears on the pickup -Y face

MARKER_FRETS = {3, 5, 7, 9, 12, 15, 17, 19, 21, 24}
# ── fret lines + fretboard border as a MATERIAL split, not an engraving ──────
FRET_T  = 1.6      # colour-layer thickness = embossed inlay height (Z)
INLAY_W = 2.4      # SHARED in-plane width: transparent fret-line width AND the border-frame band width
MIN_WEB = 0.8      # smallest colour web left between lines (stops the dense micro-lines at the bridge)
# border X: the fretted length — from the bridge end of the fretboard (just -X of the pickup region) to
# the nut/keyhead end. Absolute coords; _split gives each panel its portion so the frame is continuous.
FRET_AREA_X0 = SLOT_X[PIECE_SHOWN + PIECE_SLOTS]   # +X (bridge) end of the fretboard
FRET_AREA_X1 = PX1                                 # -X (nut / keyhead) end
# The strings FAN (nut pitch 6.5 -> changer pitch 9.5), so size the fret BOX (border included) in Y to
# the OUTER-string span at its WIDEST edge (the +X / bridge end); the frets then finish INLAY_W short.


def _string_half_span(x):
    """Half the Y between the two outer strings at deck X (linear nut->bridge fan)."""
    t = (x - D.NUT_BLOCK_X) / (D.BRIDGE_X - D.NUT_BLOCK_X)   # 0 at nut, 1 at the bridge/changer
    return D.nut_y(0) + (D.string_y(0) - D.nut_y(0)) * t


BORDER_HY = _string_half_span(FRET_AREA_X0)   # box half-Y = outer-string half-span at the +X edge
FRET_HY   = BORDER_HY - INLAY_W               # frets end one border-width short of the box edge


def _fret_positions(x0, x1):
    """(n, absolute X) of every 12-TET fret line landing on panel x0(+X)..x1:
    fret n at nut + scale*(1 - 2^(-n/12)) — they compress toward the bridge."""
    nut = D.NUT_BLOCK_X
    scale = D.BRIDGE_X - nut                     # full speaking length (nut->bridge)
    out, n = [], 1
    while True:
        fx = nut + scale * (1 - 2 ** (-n / 12.0))
        nxt = nut + scale * (1 - 2 ** (-(n + 1) / 12.0))
        if fx >= D.BRIDGE_X or nxt - fx < INLAY_W + MIN_WEB:
            break
        if x1 + 0.8 < fx < x0 - 0.8:
            out.append((n, fx))
        n += 1
    return out


def _border_frame():
    """Transparent rectangular frame (band width INLAY_W) around the fret field — same inlay/material as
    the fret lines, in the colour band (TZ-FRET_T .. TZ). Absolute coords: _split clips it to each panel
    so the frame reads as one continuous border across the stack."""
    xm = (FRET_AREA_X0 + FRET_AREA_X1) / 2
    lx = FRET_AREA_X0 - FRET_AREA_X1
    outer = box_at(lx, 2 * BORDER_HY, FRET_T, x=xm, y=0.0, z=TZ - FRET_T / 2)
    inner = box_at(lx - 2 * INLAY_W, 2 * FRET_HY, FRET_T + 1.0, x=xm, y=0.0, z=TZ - FRET_T / 2)
    return outer.cut(inner)


# ── fret-position MARKERS (between the lines, not on them) ───────────────────
# Different symbols mark the frets, keyed by the fret's position in the octave (n % 12) and REPEATING
# every octave: circle, triangle, square, pentagon, and a 4-circle octave marker (12 & 24).
MARK_D     = 5.0                       # marker circumscribed size
MARK_SHAPE = {3: "circle", 5: "triangle", 7: "square", 9: "pentagon", 0: "quad"}
# Per-marker X nudge for panel-edge printability: the fret-24 quad sits right at the mid panel's +X
# edge (its dots were 0.12 mm off it); shift it -X so ≥0.8 mm of material backs the dots (0.8 nozzle).
MARK_X_ADJ = {24: -0.7}


def _fret_x(n):
    return D.NUT_BLOCK_X + (D.BRIDGE_X - D.NUT_BLOCK_X) * (1 - 2 ** (-n / 12.0))


def _mark_x(n):
    return (_fret_x(n) + _fret_x(n - 1)) / 2 + MARK_X_ADJ.get(n, 0.0)   # fret-space centre + edge nudge


def _reg_prism(nsides, r, x, ang0):
    """Regular nsides polygon, circumradius r, centred at (x, 0), first vertex at ang0, in the colour band."""
    pts = [(x + r * math.cos(ang0 + 2 * math.pi * k / nsides),
            r * math.sin(ang0 + 2 * math.pi * k / nsides)) for k in range(nsides)]
    verts = [cq.Vector(px, py, TZ - FRET_T) for px, py in pts]
    face = cq.Face.makeFromWires(cq.Wire.makePolygon(verts + [verts[0]]))
    return cq.Workplane("XY").add(cq.Solid.extrudeLinear(face, cq.Vector(0, 0, FRET_T)))


def _marker(n):
    """One fret marker at its space, shaped by n % 12 (see MARK_SHAPE), embossed in the colour band."""
    x, r = _mark_x(n), MARK_D / 2
    shape = MARK_SHAPE[n % 12]
    if shape == "circle":
        return cyl(MARK_D, FRET_T, z=TZ - FRET_T).translate((x, 0, 0))
    if shape == "triangle":
        return _reg_prism(3, r + 0.5, x, 0.0)                       # a vertex toward +X (bridge)
    if shape == "square":
        return box_at(MARK_D * 0.85, MARK_D * 0.85, FRET_T, x=x, y=0.0, z=TZ - FRET_T / 2)
    if shape == "pentagon":
        return _reg_prism(5, r + 0.5, x, math.pi / 2)               # a vertex toward +Y
    out = None                                                      # "quad" octave marker: 4 circles across Y
    for i in range(4):
        c = cyl(MARK_D * 0.5, FRET_T, z=TZ - FRET_T).translate((x, (i - 1.5) * 3.0, 0))
        out = c if out is None else out.union(c)
    return out


_MARKERS = None
for _n in sorted(MARKER_FRETS):
    _m = _marker(_n)
    _MARKERS = _m if _MARKERS is None else _MARKERS.union(_m)


def _fret_solids(x0, x1):
    """The fret lines (string-field Y only) + the fretboard border frame + all fret-position markers
    (absolute; _split clips each panel's share), as prisms in the colour band (TZ-FRET_T .. TZ). _split
    embosses these into the transparent base and cuts them from the colour layer."""
    out = _border_frame().union(_MARKERS)
    for n, fx in _fret_positions(x0, x1):
        out = out.union(box_at(INLAY_W, 2 * FRET_HY, FRET_T, x=fx, y=0.0, z=TZ - FRET_T / 2))
    return out


def _split(panel, xa, xb, lines=True):
    """Split a finished panel at the colour line (z = TZ-FRET_T) → (base, colour).
    BASE (transparent PCTG) keeps everything below, plus the embossed fret solids
    trimmed to the panel (openings/windows interrupt the lines automatically);
    COLOUR (colour PCTG) is the top band minus those solids. Exact complements with a
    flush top at TZ — the deck datum doesn't move. Print the pair as one object."""
    slab = box_at(xa - xb + 2.0, BY1 - BY0 + 2.0, FRET_T,
                  x=(xa + xb) / 2, y=(BY0 + BY1) / 2, z=TZ - FRET_T / 2)
    frets = _fret_solids(xa, xb) if lines else None
    base, colour = panel.cut(slab), panel.intersect(slab)
    if frets is not None:
        inlay = frets.intersect(panel)
        if inlay.solids().vals():          # nothing lands on this panel (e.g. a pickup-region filler)
            base = base.union(inlay)
            colour = colour.cut(frets)
    return heal(base), heal(colour)


def _deck_body(xa, xb):
    """Bare deck plate, xa (+X) to xb (-X): a slab that CAPS both rails (the chassis
    lowers their tops to z0 across the deck span) with a vertical DOVETAIL tongue
    dropping down each rail centre-line into the rail-top groove. Wide foot, narrow
    mouth -> the plate can't lift out when inverted, and the tongue ties the rails
    in Y. The tongue runs along X, so the plate still slides out -X."""
    xm = (xa + xb) / 2
    body = box_at(xa - xb, BY1 - BY0, TZ - BZ, x=xm, y=(BY0 + BY1) / 2,
                  z=(BZ + TZ) / 2)
    MW, FLR, DEP = CH.TP_TG_MW, CH.TP_TG_FLR, CH.TP_TG_DEPTH
    for yc in (CH.Y_HI, CH.Y_LO):                     # dovetail tongue down each rail
        prof = [(yc - MW, BZ), (yc + MW, BZ),         # mouth (narrow) at the deck bottom
                (yc + MW + FLR, BZ - DEP),            # flare to the wide foot ...
                (yc - MW - FLR, BZ - DEP)]            # ... DEP below (in the rail groove)
        pts = [cq.Vector(xb, py, pz) for py, pz in prof]
        face = cq.Face.makeFromWires(cq.Wire.makePolygon([*pts, pts[0]]))
        body = body.union(cq.Workplane("XY").add(
            cq.Solid.extrudeLinear(face, cq.Vector(xa - xb, 0, 0))))
    return body


def _band(xa, xb, *, ui=False):
    """A plain (filler / mid / keyhead) deck panel body + opt. UI (fret lines are
    applied by _split, which turns them into the base/colour material boundary)."""
    body = _deck_body(xa, xb)
    if ui:
        # clearance windows for the OLED glass + joystick actuator
        body = body.cut(box_at(64.0, 35.0, TZ - BZ + 2, x=EL.UI_X, y=EL.OLED_Y,
                               z=(BZ + TZ) / 2))
        body = body.cut(cyl(9.0, TZ - BZ + 2, z=BZ - 1).translate(
            (EL.JOY_X, EL.JOY_Y, 0)))
        for dx in (-34, 34):                        # OLED mount bosses (M2 self-tap)
            for dy in (-15, 15):
                body = body.union(cyl(5.0, TZ - BZ, z=BZ).translate(
                    (EL.UI_X + dx, EL.OLED_Y + dy, 0)))
                body = body.cut(cyl(1.6, TZ - BZ + 1, z=BZ - 0.5).translate(
                    (EL.UI_X + dx, EL.OLED_Y + dy, 0)))
    return body


def _pickup_piece():
    """3-slot deck panel that carries the pickup. A pocket bounded by two side
    skirts (+Y = reference, -Y = clamp) and two end walls; the Z-plate drops in
    from above and the pickup rests on it. The +Y skirt inner face (continuous
    with the deck opening edge) is the full-height guide track for the plate's +Y
    flange; the -Y skirt has THREE clamp-screw holes. HEIGHT: two vertical M3
    grub-screw jacks at the plate X-ends thread plate tabs and bear on FIXED pads
    added here (no mechanism under the pickup -> the bay is open below the plate)."""
    body = _deck_body(PIECE_X0, PIECE_X1)
    # deck opening (pickup pokes through; offset -Y to give the clamp shim room)
    body = body.cut(box_at(OPEN_LEN, OPEN_YW, (TZ - BZ) + 2,
                           x=OPEN_CTR, y=OPEN_YC, z=(BZ + TZ) / 2))
    for y_in, s in ((HY_REF, 1), (HY_CLAMP, -1)):   # +Y reference / -Y clamp skirts
        body = body.union(box_at(OPEN_LEN + 2 * WALL, SKIRT_T, BZ - FLOOR_BOT,
                                 x=OPEN_CTR, y=s * y_in + s * SKIRT_T / 2,
                                 z=(BZ + FLOOR_BOT) / 2))
    for xe in (PIECE_X0 - WALL / 2, PIECE_X1 + WALL / 2):   # end walls (stop plate X)
        body = body.union(box_at(WALL, OPEN_YW, BZ - FLOOR_BOT,
                                 x=xe, y=OPEN_YC, z=(BZ + FLOOR_BOT) / 2))
    for cx in CLAMP_HOLES:                          # 3 clamp-screw holes (-Y skirt)
        body = body.cut(cyl_y(PM.CSCREW_D + 0.4, SKIRT_T + 2.0,
                              y0=-(HY_CLAMP + SKIRT_T + 1.0), x=cx, z=CL_Z))
    # FIXED jack pads: a small post under each of the 3 tripod screws (fused to the
    # nearest end wall / -Y skirt) that the grub-screw tip bears on to jack the plate
    # up. Bottom on the piece floor plane (FLOOR_BOT, clears the -14 ribs), top at
    # JACK_PAD_TOPZ. NO central floor -> the bay is open below the plate.
    for jx, jy in JACK_POS:
        body = body.union(box_at(9.0, 10.0, JACK_PAD_TOPZ - FLOOR_BOT,
                                 x=jx, y=jy,
                                 z=(FLOOR_BOT + JACK_PAD_TOPZ) / 2.0))
    return heal(body)


def _pickup_zplate():
    """Full-width height plate the pickup rests on, lifted by the single central
    height screw. It's guided flat by full-height flanges on BOTH Y rails that ride
    the carrier faces (deck edge + skirt) as it drops in from above:
      +Y: a solid wall (also reference-locates the pickup +Y face);
      -Y: a COMB -- fingers between the 3 clamp-screw holes, joined by a top bar
          set above the clamp-screw Z so it never covers the holes.
    Full-width so the pickup mounts anywhere in X. Built in place."""
    plate = box_at(OPEN_LEN - 0.8, OPEN_YW - 0.8, ZPL_T,
                   x=OPEN_CTR, y=OPEN_YC, z=(ZPL_BOT + ZPL_TOP) / 2)
    # +Y solid guide wall (full height)
    yp = (HY_REF - 0.3) - FLG_T / 2                   # rides the +Y carrier face (0.3 clr)
    plate = plate.union(box_at(OPEN_LEN - 0.8, FLG_T, FLG_TOP - FLG_BOT,
                               x=OPEN_CTR, y=yp, z=(FLG_BOT + FLG_TOP) / 2))
    # -Y guide: a solid wall like +Y, but with a SELF-SUPPORTING notch over each
    # clamp-screw hole -- open at the bottom (the screw passes; print bed is the
    # plate bottom) and closing to a point at 45 deg above the screw, so the wall
    # prints -z->+z with no flat bridge over the holes.
    ym = -(HY_CLAMP - 0.3) + FLG_T / 2
    plate = plate.union(box_at(OPEN_LEN - 0.8, FLG_T, FLG_TOP - FLG_BOT,
                               x=OPEN_CTR, y=ym, z=(FLG_BOT + FLG_TOP) / 2))
    nz0 = CL_Z + PM.CSCREW_D / 2 + 0.5              # screw clears below here
    half = PM.CSCREW_D / 2 + 2.0                    # notch half-width
    for cx in CLAMP_HOLES:
        pts = [(cx - half, FLG_BOT - 1.0), (cx + half, FLG_BOT - 1.0),
               (cx + half, nz0), (cx, nz0 + half), (cx - half, nz0)]   # box + 45 roof
        notch = (cq.Workplane("XZ").polyline(pts).close()
                 .extrude(10.0, both=True).translate((0, ym, 0)))
        plate = plate.cut(notch)
    # JACK TABS: a downward threaded boss under each of the 3 tripod screws — head
    # counterbore on the plate TOP (reached from +Z), M2 self-tap thread through the
    # tab, tip protrudes below to the fixed pad. (self-tap Ø = screw_d + 0.2, prints
    # near the major Ø; a heat-set insert is the upgrade for repeated adjustment.)
    for jx, jy in JACK_POS:
        plate = plate.union(cyl(JACK_TAB_OD, ZPL_BOT - JACK_TAB_BOTZ, z=JACK_TAB_BOTZ)
                            .translate((jx, jy, 0.0)))
        plate = plate.cut(cyl(JACK_D + 0.2, ZPL_TOP - JACK_TAB_BOTZ + 1.0,
                              z=JACK_TAB_BOTZ - 0.5).translate((jx, jy, 0.0)))
        plate = plate.cut(cyl(JACK_D + 2.0, 1.5, z=ZPL_TOP - 1.5)
                          .translate((jx, jy, 0.0)))       # head counterbore
    return plate


def _pickup_xclamp():
    """Protective shim between the side clamp screw and the pickup -Y face (spreads
    the screw load so no metal digs the pickup). Pushed +Y. Built in place at the
    nominal pickup X (build.py shifts it to the actual pickup)."""
    return box_at(24.0, 2.0, 7.0,          # bears on the pickup -Y face, above the plate top
                  x=PIECE_CTR, y=CLAMP_SHIM_Y, z=CL_Z)


def _filler(slot):
    """One fret-marked filler band at slot index `slot` (its own fixed X span; BAND_W
    wide, with the GAP to the next slot left as clearance)."""
    return _band(SLOT_X[slot], SLOT_X[slot] - BAND_W)


pickup_zplate = heal(_pickup_zplate())
pickup_xclamp = heal(_pickup_xclamp())

# every panel becomes a (base, colour) print pair. The pickup piece keeps a
# line-free top (its opening chops the field, and it had no lines before); every
# other panel carries the lines. Fret lines are at absolute X, so a filler only
# fits its own slot; print the set, install the ones the piece doesn't cover.
# SHOWN config: piece in slots [0..3), fillers in slots [3..7).
_piece_pair   = _split(_pickup_piece(), PIECE_X0, PIECE_X1, lines=False)
_filler_pairs = [_split(_filler(i), SLOT_X[i], SLOT_X[i] - BAND_W)
                 for i in range(N_SLOTS)]
_mid_pair     = _split(_band(MID_X0, MID_X1, ui=True), MID_X0, MID_X1)
_key_pair     = _split(_band(KEY_X0, KEY_X1), KEY_X0, KEY_X1)

# build.py places these in the assembly (piece + visible fillers + the 2 panels)
# and exports base + colour side by side (top_plate_N + top_plate_N_color). The
# fillers under the piece are exported as parts but not placed (they'd clash).
_shown_pairs = [_filler_pairs[i] for i in range(PIECE_SHOWN + PIECE_SLOTS, N_SLOTS)]
_seg_pairs   = [_piece_pair, *_shown_pairs, _mid_pair, _key_pair]
segments        = [b for b, _ in _seg_pairs]
segments_color  = [c for _, c in _seg_pairs]
_spare_pairs = [_filler_pairs[i] for i in range(PIECE_SHOWN, PIECE_SHOWN + PIECE_SLOTS)]
spare_fillers       = [b for b, _ in _spare_pairs]
spare_fillers_color = [c for _, c in _spare_pairs]
