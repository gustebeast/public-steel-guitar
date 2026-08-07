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
from cadkit.fasteners import M4, cut_insert_bore

YL = CH.Y_LO + CH.T / 2                 # -Y rail inner face (-128.75)
YH = CH.Y_HI - CH.T / 2                 # +Y rail inner face (+54.75)
BY0 = CH.Y_LO - CH.T / 2                # deck cap -Y edge (-Y rail OUTER face)
BY1 = CH.Y_HI + CH.T / 2                # deck cap +Y edge (+Y rail OUTER face)
TZ = EL.DECK_TOP                        # deck surface = D.DECK_TOP_Z (+6.4)
BZ = TZ - 8 * D.BEAD                    # 6.4 deck, bottom at 0 = the chassis groove
                                        # plane TP_GZ0 (the old 6.0 left a 0.4 gap
                                        # under the plate once the datum snapped)

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
# (The optical pickup does NOT live here. It hangs from the bridge endplate's tie bar,
# firing DOWN at the strings -- see optical_pickup.py. That keeps the whole slot grid
# for the MAGNETIC pickup, which needs every millimetre of approach to the changer.)
BAND_W   = 20.0                        # one slot (band material width)
N_SLOTS  = 7                           # pickup-region slots
PITCH    = BAND_W + GAP                # slot pitch = band + the gap after it
SLOT_X   = [PX0 - i * PITCH for i in range(N_SLOTS + 1)]   # +X face of each slot
PIECE_SLOTS = 4                        # the pickup piece spans 4 slots (enlarged one slot so the
                                       # 38.6-wide Alumitone still has >= +/-10 continuous X slide)
N_POS    = N_SLOTS - PIECE_SLOTS + 1   # = 4 coarse swap positions
CLAMP    = BAND_W / 2                  # 10.0 +/- fine X-adjust (BAND_W/2 -> continuous
                                       # by construction, so the identity is now literal)
# Slots the piece covers in EVERY position -- their fillers could never be installed, so they are not
# printed (user). The piece spans [p, p+PIECE_SLOTS) for p in 0..N_POS-1, so the intersection of all
# positions is [N_POS-1, PIECE_SLOTS): slot 3 alone as drawn. Derived, so it tracks the slot counts.
DEAD_SLOTS = set(range(N_POS - 1, PIECE_SLOTS))

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
MID_X1 = MID_X0 - 283 * D.BEAD         # 226.4: length picked so the mid/key seam lands in the CLEAR gap between
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
WALL      = 5 * D.NOZZLE_D                                 # 4.0 piece end walls (was 3.5)
OPEN_X0   = PIECE_X0 - WALL                                # +X opening edge (-21.0)
OPEN_X1   = PIECE_X1 + WALL                                # -X opening edge (-74.0)
OPEN_CTR  = (OPEN_X0 + OPEN_X1) / 2                        # -47.5
OPEN_LEN  = OPEN_X0 - OPEN_X1                              # 53.0 = PK_W + 2*CLAMP
SKIRT_T   = 4 * D.NOZZLE_D                                 # 3.2 (was 3.0)
FLG_T     = 4 * D.NOZZLE_D                                 # 3.2 Z-plate guide flange (was 2.5)
# ── pickup Y placement + EXTENDED -Y utility zone (user) ─────────────────────
# The pickup is placed by MAGNETIC coverage: its 88.9 MAGNETIC range must sit over
# string 1 (there's a ~6.35mm DEAD FRAME at each Y end, so coverage is reckoned against
# the magnetic range, NOT the 101.6 body edge -> the +Y body edge lands ~+50.1). The -Y
# side is a LONG UTILITY ZONE that runs well past the pickup so the -Y HEIGHT JACK sits
# CLEAR of the pickup, reached from +Z. NO tall +Y skirt (the +Y rail YH=+54.75 is 4.6mm
# off the body edge). (Y hold-down clamp REMOVED for now -- height adjustment only.)
PK_MAG_INSET = (PM.PK_L - PM.PK_MAG_L) / 2               # 6.35 dead frame at each Y end
PK_YP    = D.string_y(0) + 1.0 + PK_MAG_INSET            # +Y body edge (~+50.1); mag covers string 1
PK_YM    = PK_YP - PM.PK_L                                # DEMO Alumitone -Y edge (~-51.5), for the render only
PK_CTR_Y = (PK_YP + PK_YM) / 2                            # DEMO Alumitone centre Y (demo placement)
# Supported pickup LENGTH window. EVERY pickup butts the +Y wall (the magnetic datum), so a shorter
# pickup's -Y face sits further +Y; the -Y grub's reach is what still retains it. With the shared
# M4x10 cup-tip the grub's usable tip travel is ~GRUB_SWEEP, so the window is [PK_MAX_L - GRUB_SWEEP,
# PK_MAX_L]. PK_MAX_L is the ROOM size (cavity/plate/-Y grub face), set a hair ABOVE the Alumitone so
# 101.6 isn't at the exact edge (0.4 mm headroom, user); the sweep goes DOWN over the dense 10-string
# cluster (George L ~97, Steeltronics ~98, Bill Lawrence/Wilde 100, Lace/Wallace/Sentell 101.6). The
# 108 Sentell LS20 + 120.7 wide-10 stay out (they'd need a longer screw AND a still-bigger cavity).
PK_MAX_L      = 102.0                                     # longest supported pickup -> sizes the room
GRUB_SWEEP    = 5.5                                       # M4x10 usable tip travel (screw_l - min_bite - ~1 tip)
PK_MIN_L      = PK_MAX_L - GRUB_SWEEP                     # 96.5 shortest retained (covers the whole cluster)
PK_MAX_YM     = PK_YP - PK_MAX_L                          # ROOM -Y edge = the longest pickup's -Y face (~-51.9)
PK_ROOM_CTR_Y = (PK_YP + PK_MAX_YM) / 2                   # plate/cavity centre (room grows -Y, not toward the rail)
YZONE    = 16.0                                           # -Y utility-zone depth beyond the pickup
OPEN_YP  = PK_YP + 0.6                                    # +Y opening edge (open bay; < rail YH)
HY_CLAMP = -PK_MAX_YM + YZONE                             # -Y skirt inner = extended room -Y edge (~+67.9)
OPEN_YC  = (OPEN_YP - HY_CLAMP) / 2                       # opening/floor Y centre
OPEN_YW  = OPEN_YP + HY_CLAMP                             # opening/floor Y width
# Z-plate the pickup slides on in X (fine tone) -- lifted/tilted by the 3 jacks:
ZPL_T    = 3 * D.NOZZLE_D  # 2.4 (was 2.0)
ZPL_TOP  = PM.PK_BOT                                      # pickup rests on the plate top
ZPL_BOT  = ZPL_TOP - ZPL_T
FLG_BOT  = ZPL_BOT
FLG_TOP  = ZPL_TOP + PM.PK_H_MIN                          # -Y guide wall top (capped below pickup top)
# ── LEADSCREW JACKS (user): head captured in the SOLID DECK, plate rides the thread ──
# The deck is SOLID at the jacks now (only the pickup cavity + a small nub-cavity below are
# open), so each leadscrew HEAD is captured DIRECTLY in the solid deck at the print bed (TZ)
# -- a Ø7.5 head pocket + a Ø4.6 shaft bore, NO boss/web/overhang. The thread runs down
# through a cadkit heat-set-insert NUT on a plate NUB. Turning the head from +Z (axially
# fixed, free to rotate; gravity holds it on the shoulder) walks the plate up/down.
JACK_D         = 4.0                             # M4 (cadkit heat-set-insert nut on the plate)
BOSS_H         = 8 * D.NOZZLE_D   # 6.4 (was 6.0)                              # NUT boss height ABOVE the plate top (nut boss is on TOP now,
                                                 # so the plate BOTTOM stays flat -> prints -Z->+Z, user)
JACK_MOUTH_Z   = ZPL_TOP + BOSS_H                  # plate NUT mouth = the boss TOP (screw threads down into it)
# The leadscrew is a real M4 BUTTON-HEAD cap screw (headed, hex-socket drive) captured in the
# deck: a counterbore seats the head, the shoulder bears on its floor, the shank threads down
# through the plate nut. Turning the head from +Z walks the plate up/down.
JACK_HEAD_D    = 7.6                               # M4 button-head cap screw head Ø (ISO 7380)
JACK_HEAD_H    = 2.2                               # button-head height
JACK_HEAD_Z    = TZ - (JACK_HEAD_H + 0.3)          # head SHOULDER (pocket floor) in the solid deck (=3.5)
HEAD_POCKET_D  = JACK_HEAD_D + 0.4                 # Ø8 head counterbore, opens at the bed (deck top TZ)
JACK_SCREW_L   = 20.0                              # NEW BOM part: M4×20 button-head leadscrew. 20 mm shank
                                                   # spans the full height-adjust travel (15..22 mm pickup
                                                   # depths + string-gap set) with the nut engaged throughout.
FLOOR_BOT = ZPL_BOT - 6 * D.BEAD                   # 4.8 below the plate: -Y skirt / end-wall bottom
                                                   # (structure / endplate-lip datum)
# TOP-ACCESS at the PLATE's clear zones (pickup-agnostic): TWO +Y plate corners + ONE
# deep -Y. Equalise the two +Y = X LEVEL; the -Y jack = across-string tilt. The -Y jack is
# nudged slightly off-CENTRE (JACK_MX_OFF) to free the CENTRE for the retention setscrew --
# a plane is set by any 3 non-collinear points, so an off-centre tilt jack still levels fully.
PICKUP_X_NOM  = OPEN_CTR                          # nominal pickup centre X
JACK_INSET_X  = 39 * D.BEAD                       # 31.2: +Y jacks near the plate X-ends (toward the corners)
JACK_YP       = 57 * D.BEAD                        # 45.6: +Y corner jacks outboard of string 1, on the nubs
JACK_YM       = PK_MAX_YM - 13 * D.BEAD             # -Y jack deep in the -Y zone (~-62.3), below the room edge, on its nub
JACK_MX_OFF   = 8.0                                # -Y jack X-nudge off centre (frees the centre for the setscrew)
JACK_POS      = [(PICKUP_X_NOM + JACK_INSET_X, JACK_YP),
                 (PICKUP_X_NOM - JACK_INSET_X, JACK_YP),
                 (PICKUP_X_NOM + JACK_MX_OFF, JACK_YM)]
HEIGHT_HOLE = PICKUP_X_NOM
# ── plate SHAPE (user): GREEN pickup-area prism + 3 RED nubs out to the screws ────
# The plate is JUST the usable pickup area (a green prism) plus nubs that reach the 3 jack
# nuts. Everywhere else the plate used to occupy is now SOLID DECK (reclaimed as coloured
# top surface) -- the deck cavity is only the pickup + the 3 screws.
# ── pickup RETENTION (user): +Y WALL + -Y SCREW lock the pickup to the PLATE only ─
# (so the plate still moves up/down freely). The pickup's +Y face butts a wall that rises
# from the plate; a horizontal M4 grub through a -Y boss pushes the pickup +Y against it.
RET_WALL_T = 3 * D.NOZZLE_D                        # 2.4 +Y wall thickness (was 2.0)
RET_WALL_H = 8.0                                   # +Y wall height above the plate top (enough to lock, not tall)
RET_SCREW_Z = ZPL_TOP + 4 * D.BEAD                 # 3.2 grub axis height (bears low on the pickup base)
RET_BOSS_L = D.NUT_INSERT_L + 1.0                  # -Y grub boss length (Y): insert pocket + 1 to the boss +Y
                                                   # face at PK_MAX_YM (the LONGEST supported pickup's -Y face).
                                                   # Shorter pickups butt the +Y wall, so their -Y face sits +Y of
                                                   # here and the grub protrudes across open cavity to reach it.
RET_SCREW_X = PICKUP_X_NOM                          # CENTRED (the -Y jack was nudged off centre to free it):
                                                   # a centred setscrew stays on the pickup across the FULL
                                                   # +/-X_SLIDE, unlike the old +14 offset (rode off the +X
                                                   # edge in the last ~0.7 mm of -X slide). The setscrew boss
                                                   # + jack nub are one part (the plate) so they overlap
                                                   # freely; only the screw/insert dummies keep JACK_MX_OFF.
# The -Y grub is an M4 cup-tip SET SCREW threading a heat-set insert (cadkit set-screw bore), so the
# boss ceiling must clear the Ø6 insert pocket by MIN_WALL_2P (2 beads) on EVERY side (the reported
# thin-ceiling fix). Ceiling = axis + pocket radius + MIN_WALL_2P.
RET_BOSS_TOP_Z = RET_SCREW_Z + M4.insert_pilot_d / 2 + D.MIN_WALL_2P   # 1.6 (2-bead quality floor) over the bore
X_SLIDE   = 6.0                                    # pickup X-position room on the plate (+/-)
PLATE_X   = PM.PK_W + 2 * X_SLIDE                  # green X (pickup + slide) ~50.6
PLATE_Y   = (PK_YP - PK_MAX_YM) + 2 * RET_WALL_T   # green Y (LONGEST pickup + wall room each side) ~106.0
NUB_W     = 14 * D.NOZZLE_D                        # 11.2 (was 11.0) nub/arm width (>= boss Ø8)
CAVITY_X  = PLATE_X + 1.5                          # pickup cavity in the deck (green + clearance)
CAVITY_Y  = PLATE_Y + 1.5
# (Y hold-down CLAMP removed; retention above locks the pickup to the plate instead.)

MARKER_FRETS = {3, 5, 7, 9, 12, 15, 17, 19, 21, 24}
# ── fret lines + fretboard border as a MATERIAL split, not an engraving ──────
FRET_T  = 1.6      # colour-layer thickness = embossed inlay height (Z)
INLAY_W = 2.4      # SHARED in-plane width: transparent fret-line width (to fret 24) AND the border-frame band
MIN_WEB = D.MIN_WALL   # smallest colour web left between lines (1-bead floor; stops dense micro-lines at the bridge)
# The high frets crowd toward the bridge, so from fret HI_FRET UP the LINES go THIN (user): a 2.4 line there
# needs a 3.2 gap and culls early; 1.6 (2-bead min) reads cleaner in the crowd and renders a few frets closer.
HI_FRET    = 24
HI_INLAY_W = D.MIN_WALL_2P


def _inlay_w(n):
    """Fret-LINE width for fret n: full INLAY_W below HI_FRET, thin HI_INLAY_W at HI_FRET and above."""
    return HI_INLAY_W if n >= HI_FRET else INLAY_W
# border X: the fretted length — from the bridge end of the fretboard (just -X of the pickup region) to
# the nut/keyhead end. Absolute coords; _split gives each panel its portion so the frame is continuous.
FRET_AREA_X0 = SLOT_X[PIECE_SHOWN + PIECE_SLOTS]   # +X (bridge) end of the FRET FIELD (lines + markers)
FRET_AREA_X1 = PX1                                 # -X (nut / keyhead) end
# The BORDER's side bands run further +X than the field, all the way to the deck's bridge end, so the
# band-region fillers carry the same top/bottom border as the rest of the fretboard (user). Those slots
# only ever hold the pickup piece OR a filler, and whichever fillers aren't covered are installed — an
# unbordered band there read as the fretboard just stopping short of the bridge.
BORDER_X0 = PX0                                    # +X (bridge) end of the border side bands
# The strings FAN (nut pitch 6.5 -> changer pitch 9.5), so size the fret BOX (border included) in Y to
# the OUTER-string span at its WIDEST edge (the +X / bridge end); the frets then finish INLAY_W short.


def _string_half_span(x):
    """Half the Y between the two outer strings at deck X (linear nut->bridge fan)."""
    t = (x - D.NUT_BLOCK_X) / (D.BRIDGE_X - D.NUT_BLOCK_X)   # 0 at nut, 1 at the bridge/changer
    return D.nut_y(0) + (D.string_y(0) - D.nut_y(0)) * t


BORDER_HY = _string_half_span(BORDER_X0)      # box half-Y = outer-string half-span at the frame's WIDEST
                                              # (+X) edge -- which is BORDER_X0, not FRET_AREA_X0, now that
                                              # the side bands run on to the bridge end. Datuming to the
                                              # field edge instead would leave the outer strings crossing
                                              # OUT over the band across the last ~80 mm of fan.
FRET_HY   = BORDER_HY - INLAY_W               # frets end one border-width short of the box edge


def _fret_positions(x0, x1):
    """(n, absolute X) of every 12-TET fret line landing on panel x0(+X)..x1 AND inside the fret
    FIELD: fret n at nut + scale*(1 - 2^(-n/12)) — they compress toward the bridge.

    The field ends at FRET_AREA_X0. Frets run monotonically +X toward the bridge, so passing it
    ends the walk. Without that clamp this emitted any fret that merely LANDED on a panel, which
    put frets 33-35 on the band-region fillers — lines +X of the fretboard, in the region the
    pickup piece occupies. Those panels get the BORDER only (user)."""
    nut = D.NUT_BLOCK_X
    scale = D.BRIDGE_X - nut                     # full speaking length (nut->bridge)
    out, n = [], 1
    while True:
        fx = nut + scale * (1 - 2 ** (-n / 12.0))
        nxt = nut + scale * (1 - 2 ** (-(n + 1) / 12.0))
        if fx > FRET_AREA_X0 or nxt - fx < (_inlay_w(n) + _inlay_w(n + 1)) / 2 + MIN_WEB:
            break
        if x1 + 0.8 < fx < x0 - 0.8:
            out.append((n, fx))
        n += 1
    return out


def _border_frame():
    """Transparent U-frame (band width INLAY_W) around the fret field — the two long Y sides + the
    -X (nut/keyhead) end. OPEN at the +X (bridge) end: there is no fretboard edge there — the field
    just runs out under the pickup, whose seam X MOVES with the pickup's slot position (user), so a
    fixed +X edge would be both wrong and a false 'fret' on the seam. Same inlay/material as the fret
    lines, in the colour band (TZ-FRET_T .. TZ); _split clips it to each panel so the U reads continuous.

    The side bands run to BORDER_X0 (the deck's bridge end), PAST the fret field, so the band-region
    fillers are bordered too. The pickup PIECE is split lines=False and never takes any of this; where
    it sits, its cavity is wider than the frame anyway, so the border could not survive there."""
    x_hi, x_lo = BORDER_X0, FRET_AREA_X1                          # +X (bridge) end, -X (nut) end
    outer = box_at(x_hi - x_lo, 2 * BORDER_HY, FRET_T,
                   x=(x_hi + x_lo) / 2, y=0.0, z=TZ - FRET_T / 2)
    ix_lo, ix_hi = x_lo + INLAY_W, x_hi + 1.0                     # inset the -X end; RUN PAST the +X end
    inner = box_at(ix_hi - ix_lo, 2 * FRET_HY, FRET_T + 1.0,
                   x=(ix_hi + ix_lo) / 2, y=0.0, z=TZ - FRET_T / 2)
    return outer.cut(inner)


# ── fret-position MARKERS (between the lines, not on them) ───────────────────
# Different symbols mark the frets, keyed by the fret's position in the octave (n % 12) and REPEATING
# every octave: circle, triangle, square, pentagon, and a 4-circle octave marker (12 & 24).
MARK_D     = 6 * D.BEAD                # 4.8 marker circumscribed size
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
        out = out.union(box_at(_inlay_w(n), 2 * FRET_HY, FRET_T, x=fx, y=0.0, z=TZ - FRET_T / 2))
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
    for yc in (CH.Y_HI, CH.Y_LO):        # cadkit mushroom tenon down each rail
        body = body.union(CH._deck_tg(yc, xb, xa, mortise=False))
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
    """4-slot deck panel that carries the pickup. The deck is SOLID except (a) the PICKUP
    CAVITY -- a hole the pickup pokes up through and moves in -- and (b) the 3 LEADSCREW
    bores. Everywhere the plate no longer needs to move is filled deck (reclaimed as
    coloured top surface, user). A -Y skirt + two end walls hang below (structure / the
    endplate-lip datum). Each leadscrew HEAD is captured in the SOLID DECK at the print bed
    (Ø7.5 pocket down to the shoulder + Ø4.6 shaft bore) -- no boss/web, so no overhang."""
    body = _deck_body(PIECE_X0, PIECE_X1)
    # PICKUP CAVITY only (pickup pokes through + slides/rises); rest of the deck stays solid
    body = body.cut(box_at(CAVITY_X, CAVITY_Y, (TZ - BZ) + 2,
                           x=PICKUP_X_NOM, y=PK_ROOM_CTR_Y, z=(BZ + TZ) / 2))
    # -Y skirt + end walls below the deck (structure / endplate-lip datum)
    body = body.union(box_at(OPEN_LEN + 2 * WALL, SKIRT_T, BZ - FLOOR_BOT,
                             x=OPEN_CTR, y=-(HY_CLAMP + SKIRT_T / 2),
                             z=(BZ + FLOOR_BOT) / 2))
    for xe in (PIECE_X0 - WALL / 2, PIECE_X1 + WALL / 2):
        body = body.union(box_at(WALL, OPEN_YW, BZ - FLOOR_BOT,
                                 x=xe, y=OPEN_YC, z=(BZ + FLOOR_BOT) / 2))
    # LEADSCREW BORES through the solid deck: head pocket (Ø7.5, opens at the bed TZ, down
    # to the shoulder) + shaft bore (Ø4.6, on down into the open bay where the plate nut is)
    for jx, jy in JACK_POS:
        body = body.cut(cyl(HEAD_POCKET_D, TZ - JACK_HEAD_Z + 1, z=JACK_HEAD_Z)
                        .translate((jx, jy, 0.0)))
        body = body.cut(cyl(M4.shaft_clr_d + 0.4, JACK_HEAD_Z - BZ + 1.1, z=BZ - 1)
                        .translate((jx, jy, 0.0)))
    return heal(body)


def _pickup_zplate():
    """The height plate: a GREEN pickup-area prism (the pickup rests on it; X-slide room)
    plus 3 NUBS reaching the leadscrew NUTS (user's green+red shape). PRINTS -Z->+Z with a
    FLAT BOTTOM (user): every boss is on TOP -- the nut bosses stand UP (insert pocket down
    from the boss top; the screw tail passes through a Ø4.4 hole in the flat plate). RETENTION
    (user): a +Y WALL the pickup butts + a -Y horizontal grub that pushes it +Y against the
    wall, locking the pickup to the PLATE only (so the plate still travels)."""
    plate = box_at(PLATE_X, PLATE_Y, ZPL_T,
                   x=PICKUP_X_NOM, y=PK_ROOM_CTR_Y, z=(ZPL_BOT + ZPL_TOP) / 2)
    for jx, jy in JACK_POS:
        dx, dy = jx - PICKUP_X_NOM, jy - PK_ROOM_CTR_Y
        if abs(dx) - PLATE_X / 2 >= abs(dy) - PLATE_Y / 2:      # jack juts past the green in X -> X-arm
            xe = PICKUP_X_NOM + (PLATE_X / 2 if dx > 0 else -PLATE_X / 2)
            plate = plate.union(box_at(abs(jx - xe) + NUB_W, NUB_W, ZPL_T,
                                       x=(jx + xe) / 2, y=jy, z=(ZPL_BOT + ZPL_TOP) / 2))
        else:                                                  # -> Y-arm
            ye = PK_ROOM_CTR_Y + (PLATE_Y / 2 if dy > 0 else -PLATE_Y / 2)
            plate = plate.union(box_at(NUB_W, abs(jy - ye) + NUB_W, ZPL_T,
                                       x=jx, y=(jy + ye) / 2, z=(ZPL_BOT + ZPL_TOP) / 2))
        # LEADSCREW NUT boss ON TOP (flat plate bottom): Ø8 boss up from the plate, Ø6×5
        # insert pocket down from the boss top, Ø4.4 screw-tail clearance on through the plate.
        plate = plate.union(cyl(M4.boss_od, BOSS_H, z=ZPL_TOP).translate((jx, jy, 0.0)))
        plate = plate.cut(cyl(M4.insert_pilot_d, M4.insert_depth + 0.6,
                              z=JACK_MOUTH_Z - M4.insert_depth).translate((jx, jy, 0.0)))
        plate = plate.cut(cyl(M4.shaft_clr_d, (JACK_MOUTH_Z - M4.insert_depth) - (ZPL_BOT - 2),
                              z=ZPL_BOT - 2).translate((jx, jy, 0.0)))
    # +Y RETENTION WALL (rises from the plate top; the pickup +Y face butts its -Y face)
    plate = plate.union(box_at(PM.PK_W, RET_WALL_T, RET_WALL_H,
                               x=PICKUP_X_NOM, y=PK_YP + RET_WALL_T / 2,
                               z=ZPL_TOP + RET_WALL_H / 2))
    # -Y RETENTION grub boss: a pedestal rising from the plate at the LONGEST supported pickup's -Y edge
    # (PK_MAX_YM), hosting a HORIZONTAL M4 heat-set insert (cadkit set-screw bore -> a cup-tip grub, which
    # must never self-tap). The grub pushes the pickup +Y against the wall; threading it in/out lets its
    # tip meet any pickup in the [PK_MIN_L, PK_MAX_L] window (its -Y face floats +Y for shorter pickups).
    # The pedestal ceiling reaches RET_BOSS_TOP_Z so >= MIN_WALL_2P (1.6) rings the Ø6 pocket every side.
    ret_face_y = PK_MAX_YM - RET_BOSS_L               # -Y outer face = the insert-entry (grub) face
    plate = plate.union(box_at(NUB_W, RET_BOSS_L, RET_BOSS_TOP_Z - ZPL_BOT,
                               x=RET_SCREW_X, y=(ret_face_y + PK_MAX_YM) / 2,
                               z=(ZPL_BOT + RET_BOSS_TOP_Z) / 2))
    plate = cut_insert_bore(M4, plate, (RET_SCREW_X, ret_face_y, RET_SCREW_Z), (0, 1, 0),
                            clr_len=RET_BOSS_L - M4.insert_depth + 1.0,
                            reason="set screw: -Y pickup-retention grub, must not self-tap")
    return plate


def _filler(slot):
    """One fret-marked filler band at slot index `slot` (its own fixed X span; BAND_W
    wide, with the GAP to the next slot left as clearance)."""
    return _band(SLOT_X[slot], SLOT_X[slot] - BAND_W)


pickup_zplate = heal(_pickup_zplate())

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
_spare_pairs = [_filler_pairs[i] for i in range(PIECE_SHOWN, PIECE_SHOWN + PIECE_SLOTS)
                if i not in DEAD_SLOTS]      # DEAD_SLOTS never surface -> nothing to print
spare_fillers       = [b for b, _ in _spare_pairs]
spare_fillers_color = [c for _, c in _spare_pairs]
