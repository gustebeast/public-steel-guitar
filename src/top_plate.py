"""Removable top deck — PCTG. Swappable fret-marked BANDS + a pickup-cover piece.

Roles: (1) fret-position lines for the player; (2) dust cover over the motors +
electronics; (3) sound damping; (4) OLED + joystick mount; (5) hand rest; (6) the
pickup carrier.

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

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from . import electronics as EL
from . import pickup_mount as PM
from .helpers import box_at, cyl, cyl_y, heal

YL = CH.Y_LO + CH.T / 2                 # -Y rail inner face (-128.75)
YH = CH.Y_HI - CH.T / 2                 # +Y rail inner face (+54.75)
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
MID_X1 = MID_X0 - 220.0
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
HY_REF    = PM.PK_L / 2 + 1.0                              # +50.5  reference skirt (+Y)
HY_CLAMP  = PM.PK_L / 2 + 7.0                              # -56.5  clamp skirt (room for
                                                          #        the shim + side screw)
OPEN_YC   = (HY_REF - HY_CLAMP) / 2                        # opening/floor Y centre (-3.0)
OPEN_YW   = HY_REF + HY_CLAMP                              # opening/floor Y width (107.0)
SKIRT_T   = 3.0
FLOOR_BOT = -13.5                                          # floor bottom clears the chassis
FLOOR_T   = 1.5                                            # motor ribs (tops at z -14)
# Z-plate: full-opening, slides only in Z (lifted by the screws); pickup rests on it
ZPL_T     = 2.0
ZPL_TOP   = PM.PK_BOT                                      # pickup sits on the plate top
ZPL_BOT   = ZPL_TOP - ZPL_T
SPINE_W   = 16.0                                          # central spine carrying the boss
FLG_T     = 2.5                                           # Z-plate guide-flange thickness
FLG_BOT   = ZPL_BOT                                       # flange bottoms FLUSH with the plate
                                                          # body -> flat print bottom (the
                                                          # carrier guide TRACK still runs the
                                                          # full -13.5..+6; the flange rides it)
# wall TOP is capped one shortest-pickup-height above the rest surface, so that
# even raising the shortest pickup until it touches the strings, the walls land at
# the pickup top -- never above it (never fouling the bar/strings)
FLG_TOP   = ZPL_TOP + PM.PK_H_MIN
# Z height: ONE central screw lifts the plate (reached from below); the plate's
# +/-Y flanges ride the skirt inner faces so it can only move in flat Z (no
# see-saw) -> one knob sets the height.
HEIGHT_HOLE = PIECE_CTR
HSCREW_CLR = PM.HSCREW_D + 0.4                            # tapped/insert hole for the screw
# X clamp: THREE clamp-screw holes along the -Y skirt -> use the one nearest the
# pickup so the side clamp pushes near the pickup centre wherever it's slid. The
# shim spreads the load, so the hole needn't line up exactly with the midpoint.
CLAMP_HOLES = [PIECE_CTR - 18.0, PIECE_CTR, PIECE_CTR + 18.0]
CL_Z      = -4.0                                          # side clamp screw / shim height

MARKER_FRETS = {3, 5, 7, 9, 12, 15, 17, 19, 21, 24}


def _fret_lines(plate, x0, x1):
    """Engrave EVERY 12-TET fret line across the panel (they compress toward the
    bridge: fret n at nut + scale*(1 - 2^(-n/12))), plus marker dots at the
    standard frets (double at 12 & 24). Stops where the spacing drops below
    1.5 mm (unmarkable, right at the bridge). Cosmetic recesses in the deck top."""
    nut = D.NUT_BLOCK_X
    scale = D.BRIDGE_X - nut                     # full speaking length (nut->bridge)
    n = 1
    while True:
        fx = nut + scale * (1 - 2 ** (-n / 12.0))
        nxt = nut + scale * (1 - 2 ** (-(n + 1) / 12.0))
        if fx >= D.BRIDGE_X or nxt - fx < 1.5:
            break
        if x1 + 0.8 < fx < x0 - 0.8:
            plate = plate.cut(box_at(0.7, YH - YL - 8, 0.9,
                                     x=fx, y=(YL + YH) / 2, z=TZ - 0.45))
            if n in MARKER_FRETS:
                for dy in ((-9.0, 9.0) if n in (12, 24) else (0.0,)):
                    plate = plate.cut(cyl(4.0, 1.3, z=TZ - 1.3)
                                      .translate((fx, dy, 0)))
        n += 1
    return plate


def _deck_body(xa, xb):
    """Bare deck plate, xa (+X) to xb (-X): a slab that CAPS both rails (the chassis
    lowers their tops to z0 across the deck span) with a vertical DOVETAIL tongue
    dropping down each rail centre-line into the rail-top groove. Wide foot, narrow
    mouth -> the plate can't lift out when inverted, and the tongue ties the rails
    in Y. The tongue runs along X, so the plate still slides out -X."""
    xm = (xa + xb) / 2
    BY0 = CH.Y_LO - CH.T / 2             # cap from the -Y rail outer face ...
    BY1 = CH.Y_HI + CH.T / 2             # ... to the +Y rail outer face
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
    """A plain (filler / mid / keyhead) deck panel: body + fret lines + opt. UI."""
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
    return heal(_fret_lines(body, xa, xb))


def _pickup_piece():
    """3-slot deck panel that carries the pickup. It's a pocket bounded by two
    side skirts (+Y = reference, -Y = clamp) and two end walls; the Z-plate drops
    in from above and the pickup rests on it. The +Y skirt inner face (continuous
    with the deck opening edge) is the full-height guide track for the plate's +Y
    flange. A central spine carries ONE height-screw hole (reached from below);
    the -Y skirt has THREE clamp-screw holes (use the one nearest the pickup)."""
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
    # central spine (Y=0) carrying the single height-screw boss, reached from below
    body = body.union(box_at(OPEN_LEN + 2 * WALL, SPINE_W, FLOOR_T,
                             x=OPEN_CTR, y=0, z=FLOOR_BOT + FLOOR_T / 2))
    body = body.union(cyl(8.0, 2.0, z=FLOOR_BOT).translate((HEIGHT_HOLE, 0, 0)))
    body = body.cut(cyl(HSCREW_CLR, 6.0, z=FLOOR_BOT - 1.0).translate((HEIGHT_HOLE, 0, 0)))
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
    return plate


def _pickup_xclamp():
    """Protective shim between the side clamp screw and the pickup -Y face (spreads
    the screw load so no metal digs the pickup). Pushed +Y. Built in place at the
    nominal pickup X (build.py shifts it to the actual pickup)."""
    return box_at(24.0, 2.0, 7.0,          # bears on the pickup -Y face, above the plate top
                  x=PIECE_CTR, y=-52.3, z=CL_Z)


def _filler(slot):
    """One fret-marked filler band at slot index `slot` (its own fixed X span; BAND_W
    wide, with the GAP to the next slot left as clearance)."""
    return _band(SLOT_X[slot], SLOT_X[slot] - BAND_W)


pickup_piece  = _pickup_piece()
pickup_zplate = heal(_pickup_zplate())
pickup_xclamp = heal(_pickup_xclamp())
deck_mid     = _band(MID_X0, MID_X1, ui=True)
deck_keyhead = _band(KEY_X0, KEY_X1)

# every slot has its own fret-marked filler (fret lines are at absolute X, so a
# filler only fits its own slot); print the set, install the ones the piece
# doesn't cover. SHOWN config: piece in slots [0..4), fillers in slots [4..7).
fillers = [_filler(i) for i in range(N_SLOTS)]
shown_fillers = [fillers[i] for i in range(PIECE_SHOWN + PIECE_SLOTS, N_SLOTS)]

# build.py places these in the assembly (piece + visible fillers + the 2 panels).
# The fillers under the piece are exported as parts but not placed (they'd clash).
segments = [pickup_piece, *shown_fillers, deck_mid, deck_keyhead]
spare_fillers = [fillers[i] for i in range(PIECE_SHOWN, PIECE_SHOWN + PIECE_SLOTS)]
