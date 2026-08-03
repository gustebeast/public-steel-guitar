"""Chassis frame (§8) — PCTG. ONE rigid frame that absorbs the motor bank and
ties in the bridge endplate and a nut keyhead, SPLIT into SCREWED segments.

The strings pull the bridge and nut toward each other (~10×100 N) at the speaking
height, which would bow the instrument; the chassis resists that. The stiffness
comes from DEPTH: two longitudinal side rails (from just under the strings down
to the print bed) run the whole length, tied by per-motor cross-ribs and a
keyhead bulkhead at the nut. The motor faceplate walls (with their NEMA17
patterns) are fused in; the motors rest on the ribs (no floor plate). The rail
webs carry self-supporting diamond lightening; everything else is modelled
SOLID — the slicer's walls + infill set the strength-to-weight.

Too long for one print (~645 mm > 255 mm bed), so it's cut into 3 segments joined
by a cadkit install-z JOINT on each side rail: the profile lies in the plan plane,
so every working face is a printed VERTICAL wall, and you drop the next segment
straight DOWN onto it. The joint locks ±X (so string pull can never draw the seam
open) and ±Y by shape; Z — the install axis — needs no seam hardware at all, because
the assembly closes over it: deck panels, then endplates, and finally the four LEG
SCREWS, after which nothing can come apart (user). NO GLUE anywhere, and no seam
fastener either. The cuts fall in the gaps BETWEEN ribs; each motor faceplate is fused
WHOLE into the segment that owns its motor (_segments), so a plate straddling a cut
just overhangs into the relieved neighbour — never sliced. Built in global position;
the segments assemble into the whole.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import motor_bank as MB
from .components import MOTOR_PULLEY_STANDOFF
from .helpers import box_at, cyl
from cadkit.fasteners import M2, cut_anchor
from cadkit.joinery import PrintSpec, joint

T        = D.WALL_THICKNESS            # rail thickness (solid; slicer infills)
X_BRIDGE = 6.0                         # +X (bridge) end — the rails end here; the bridge
                                       #   endplate caps them (a separate flat-printed part)
X_NUT    = -(D.MOUNTING_SPAN + 24.0)   # −X end, extended to carry the nut block;
                                       # rail ends FLUSH with the end bulkhead's
                                       # outer face (NUT_BLOCK_X − 9 − 15)
Z_TOP    = D.STRING_Z - 6.0            # body deck, 6 mm under the strings (normal action)
Z_BOT    = MB.BED_Z                    # print bed (shared with the motor walls)
# Rail CENTRES, defined so the INNER faces stay fixed as the wall T changes (the wall
# grows outward): +Y inner clears the bearing arm, -Y inner clears the motor PCBs.
Y_HI     = D.BRIDGE_AXLE_Y + 3.0 + T / 2          # +Y rail (inner face = axle_Y + 3)
Y_LO     = (D.string_y(D.N_STRINGS - 1) - MOTOR_PULLEY_STANDOFF - D.MOTOR_BODY_LEN
            - D.MOTOR_PCB_LEN - 2.0) - T / 2      # −Y rail off the −Y-most string (last index)
_XC, _ZC = (X_BRIDGE + X_NUT) / 2, (Z_TOP + Z_BOT) / 2
_RIB_W   = D.XBAR                      # cross-rib X-width = XBAR (square XBAR×XBAR section)
# Top-plate retention grooves (top_plate.py rides these): a slot in each rail
# inner face below the rail top, leaving a ~3 mm lip so the deck plates can't
# fall out when the instrument is inverted (they pull straight out toward −X).
TP_X0, TP_X1   = -16.0, -638.0         # groove X span; open at the -X rail end so
                                       # the deck panels slide out -X once the
                                       # (removable) keyhead endplate is off
TP_GZ0, TP_GZ1 = 0.0, D.DECK_TOP_Z     # deck plate z-plane: bottom rests on the rail
                                       # top (lowered to z0 here), top = playing surface
# DECK JOINT — a cadkit slide joint. The deck plate caps the rail
# (right-angle bend) and drops a tongue straight down into a groove milled
# in the rail top. The foot is wider than the mouth, so the wide foot can't pull up
# through the narrow mouth -> +Z retention (plates stay put when inverted). The
# inboard groove wall is what the rail bears against if the rails try to spread, so
# it also ties the rails in Y. The tongue runs along X -> plates still slide out -X.
# top_plate.py builds the matching tongue; the rail top is lowered to z0 in the deck
# X-span so the plate sits flush on top.
TP_TG_DEPTH    = 6.0                    # the reserved groove ZONE below the deck. The
                                        # joint itself uses less (see TP_JOINT.height);
                                        # other geometry keys off this envelope, so it
                                        # stays the published number.
TP_TG_YC       = {1: Y_HI, -1: Y_LO}   # groove centre = each rail centre-line
# ── the joint itself is cadkit's, and the PRINT DIRECTION is what picks it ──────
# Now that a PrintSpec carries an axis AND a direction, this site describes itself. The
# deck panels print TOP-FACE-DOWN (their leadscrew head pockets open at the bed — see
# top_plate.HEAD_POCKET_D), so a panel builds world −Z while the chassis builds world +Z.
# In the joint's own frame — local +Z is the direction the tenon GROWS, i.e. downward off
# the panel's underside — that reads as tenon facing 'up', mortise facing 'down', and
# cadkit answers with the flat-top MUSHROOM. That is the right answer for a reason the
# hand-rolled dovetail got wrong: the rail builds TOWARD the groove's opening, so the
# cavity's WIDE end is reached first and prints as a supported floor. The dovetail's wide
# foot was a bridge instead, and its acute plan corners are the same 0.8-nozzle rounding
# problem that retired the dovetail everywhere else.
_DECK_UP   = PrintSpec(nozzle=0.8, material="PCTG", facing="up")      # builds world −Z
_RAIL_DOWN = PrintSpec(nozzle=0.8, material="PETG-GF", facing="down")  # builds world +Z
TP_TG_W    = 6.4                       # across Y: leaves (T − W)/2 − clearance = 1.65 mm
                                       # (2 beads) of rail wall per side. Wider than the
                                       # old 4.6 foot, so the groove's inboard wall — what
                                       # the rails bear on if they try to spread — gains.
TP_JOINT   = joint(width=TP_TG_W, length=1.0, tenon=_DECK_UP, mortise=_RAIL_DOWN,
                   install="+x")       # SIGNED: panels slide in travelling +X and butt the
                                       # bridge endplate, which IS the stop; they come back
                                       # out −X once the keyhead endplate is off.
assert TP_JOINT.height <= TP_TG_DEPTH, (
    f"deck joint swallows {TP_JOINT.height:.3f} but the reserved groove zone "
    f"TP_TG_DEPTH is {TP_TG_DEPTH} — deepen the zone or narrow TP_TG_W")
assert (T - TP_TG_W) / 2 - TP_JOINT.clearance >= D.MIN_WALL_2P, (
    f"deck groove leaves {(T - TP_TG_W) / 2 - TP_JOINT.clearance:.2f} of rail wall per "
    f"side, under the {D.MIN_WALL_2P} two-bead tier — narrow TP_TG_W")


def _deck_tg(yc, x0, x1, mortise):
    """The deck joint at rail Y=yc over x0..x1 — mortise (the rail-top groove) or tenon
    (the panel's tongue; top_plate calls it). Rotated 180° about X so the joint's local
    +Z points DOWN: the tenon grows off the panel's underside into the rail."""
    L = (x1 - x0) + (2.0 if mortise else 0.0)
    s = (TP_JOINT.mortise(drop=1.0, length=L) if mortise
         else TP_JOINT.tenon(root=1.0, length=L))
    return (s.rotate((0, 0, 0), (1, 0, 0), 180)
            .translate((x0 - (1.0 if mortise else 0.0), yc, TP_GZ0)))
# TOP L-joint X-clearance (housing<->endplate): the chassis rail end stops EP_TOP_CLR
# short of each endplate's INBOARD face, so the endplate drops on without binding in X --
# the same idea as the bottom L-joint's leg clearance (EP_LEG_CLR), and DERIVED from the
# endplate faces so both ends stay consistent however the endplates are positioned (the
# keyhead at the nut, the bridge centred on the axle). Without this the keyhead read 0 mm
# (face == rail end) and the bridge read 1 mm (centred face vs a hardcoded rail end).
EP_TOP_CLR     = 0.4
# +X END: the bridge endplate TAKES OVER the whole +X end as one solid block (the same
# endplate methodology as the keyhead): the +X cross-tie itself (no crossbar), held by
# the rail-end dovetails alone. The rail +X end stops EP_TOP_CLR -X of the bridge's
# inboard face (D.BRIDGE_BASE_X0); the deck groove runs up to there.
TP_EP_GX       = D.BRIDGE_BASE_X0 - EP_TOP_CLR   # rail +X end / deck +X face (-16.9)
# -X END: the keyhead takes over the whole -X end as one solid block (the -X cross-tie,
# held by the rail-end dovetails, no screw). KH_X is the keyhead INBOARD FACE; the rail
# -X end (KH_RAIL_X) stops EP_TOP_CLR +X of it.
KH_X           = -611.0                          # keyhead inboard face (-611)
KH_RAIL_X      = KH_X + EP_TOP_CLR               # rail -X end / keyhead dovetail face (-610.6)
# Endplate JOINERY (both ends, shared — see _end_dt / _kh_tongue / _br_tongue): each
# endplate is held by Y-flaring vertical dovetails that follow the L-shaped body<->
# endplate contact. Per rail there are TWO stacked dovetails: a LOWER one on the
# wall<->leg-shell face (z bed..foot line) and an UPPER one on the foot<->rail-end face
# (z foot line..deck-groove floor — it STOPS below the deck so the panel seat stays
# clear). Each is NARROW at the rail/shell face and WIDE KH_DT_DEPTH into the endplate,
# so string tension can't draw the wide foot back out. The body carries the tenons; the
# endplate sockets them (X+Y lock, still lifts +Z). The endplate's L-foot resting on the
# leg-shell top is the drop-depth stop, so the dovetails need no shoulder of their own.
KH_DT_WR, KH_DT_WT = 2.0, 3.0          # narrow / wide half-widths (Y). Sized so the socket's
                                       # OUTER wall (to the instrument's outer face, the only
                                       # bounded side: the dovetail centres on the rail, 5 mm
                                       # from that face) stays >= 1.6 mm (2x 0.8 nozzle): wall =
                                       # 5 - WT - KH_DT_CLR = 1.7 mm. 1:8 flank flare (WT-WR=1.0
                                       # over DEPTH), so the wall comfortably backs the undercut.
KH_DT_DEPTH    = 8.0                    # dovetail reach into the endplate (X)
KH_DT_Z0       = -23.15                 # foot line = leg-tenon top (-33.15) + XBAR; also the
                                       # LOWER/UPPER dovetail split (the L-corner / drop stop)
KH_DT_CLR      = 0.3                    # socket clearance (Y fit)
KH_DT_SEAT     = 0.1                    # lower-dovetail seating clearance: the mortise face stays
                                       # ON the foot line (KH_DT_Z0 = -23.15) and the TENON is
                                       # shortened by this (top -23.25) so the tenon seats on the
                                       # L-foot/shell, not the mortise ceiling -- without lifting
                                       # the visible mortise face off the foot line
# A chunky rail-to-rail rib UNDER EACH MOTOR (the motor rests on it, its wall sits
# on it, and it ties the two rails) replaces a solid floor — far lighter for the
# strength. Plus a rib near the nut, placed to keep the WHOLE bottom-rib set on a
# uniform pitch (the motor ribs already are): evenly-spaced ribs make every
# bay identical, so a knee/pedal lever's christmas-tree mount fits ANY pair. (No +X
# crossbar: the bridge block IS the +X tie.)
# HALF-PITCH RIB COMB (generative -- a rib can never go missing): a crossbar per motor
# PLUS one between each adjacent pair -> uniform 23 mm pitch, twice the crossbar support,
# extended TWO motor-pitches past each end of the motor bank. Every rib is identical
# (XBAR-wide, same christmas-tree mortise + wire raceway), so "one tenon fits any bay"
# holds -- a lever just spans two of the finer bays. NOTHING is excluded (the knee-lever
# bay keeps its ribs too; the lever housing is relieved for them in knee_lever.py).
def _rib_positions():
    """The rib X-list, computed so there is never a gap. Motor pitch = (first motor .. last
    motor) / (N-1); take N_STRINGS+4 BASE ribs at that pitch starting two pitches past the
    -X-most motor (a rib per motor + two beyond each end), then drop a rib at every midpoint
    between adjacent base ribs -> the uniform half-pitch comb."""
    mx = sorted(D.motor_pos(i)[0] for i in range(D.N_STRINGS))
    pitch = (mx[-1] - mx[0]) / (D.N_STRINGS - 1)                       # motor pitch (46)
    base = [mx[0] - 2 * pitch + k * pitch for k in range(D.N_STRINGS + 4)]   # 2 past each end
    mids = [(base[i] + base[i + 1]) / 2 for i in range(len(base) - 1)]
    return sorted(base + mids)   # _RIB_X is trimmed against the leg stubs below

_RIB_X = _rib_positions()
SPLIT_X  = [-216.5, -446.5]            # 2 cuts → 3 segments < 255 mm (224.7 / 230.0 / 192.5), each in a
                                       # 13 mm gap BETWEEN two ribs. The cut straddles a 43-wide motor
                                       # plate, but that plate is fused WHOLE into the segment that owns
                                       # its motor (see _segments): it overhangs the cut plane with its
                                       # bolt holes intact and the neighbour is relieved. So the split is
                                       # free of the motor-wall / bolt-column constraint -- it only has
                                       # to clear the ribs (a rib and an 8 mm joint won't share a 3 mm gap).

# Bridge-endplate joint: ENDPLATE_JOINT_Y are the two rail centre-lines the bridge
# (and keyhead) sit over; kept for the bridge's foot/joint references.
ENDPLATE_JOINT_Y = (Y_HI, Y_LO)

# guard: a split PLANE (full-Y cut) must miss every rail-to-rail rib -- it would slice one
# in half. (Motor plates are NOT a constraint any more: they fuse per segment, so the plane
# may cross a plate's X-span; the plate goes whole to its motor's segment and overhangs.)
for _s in SPLIT_X:
    _plane_hit = [rx for rx in _RIB_X if abs(_s - rx) < _RIB_W / 2]
    assert not _plane_hit, f"SPLIT_X {_s} plane slices rib(s) {_plane_hit} — move it into a rib gap"
# SEGMENT JOINT — cadkit, install='z' (both hosts print −Z→+Z, so the profile lies
# in the plan plane and every working face is a vertical printed wall). It replaces
# the hand-rolled sliding dovetail, which cadkit retired: at a 0.8 nozzle the
# dovetail's acute plan corners round DOWN on the tenon and UP in the mortise, so
# the halves collide at the corners before the faces seat.
_UP       = PrintSpec(nozzle=0.8, material="PETG-GF", facing="up")
_SEG_JW   = 6.4                        # width across Y — leaves (T − JW)/2 − clearance
                                       # = 1.65 mm of rail wall per side (2 beads)
_SEG_JD   = 8.0                        # room into the +X segment (the T uses 5.63 of it)
_SEG_JZ1  = TP_GZ0 - TP_TG_DEPTH       # tenon top = the deck-groove FLOOR (−6), so the
                                       # seam joint never reaches into the deck groove
_SEG_ROOT = 2.0                        # volumetric fusion depth back into the −X segment
_SEG_J    = joint(width=_SEG_JW, length=_SEG_JZ1 - Z_BOT, depth=_SEG_JD,
                  tenon=_UP, mortise=_UP, install="+z")   # signed: the +X segment is
                  # lowered on, so RELATIVE to it the tenon travels +Z to seat
_SEG_JX1  = _SEG_J.dims["depth_used"]  # the tenon's +X reach past the seam plane
# the rail wall left beside the cavity is a printed wall like any other, and the only
# thing keeping it at tier is the hand-picked width above. Say so, so a later change to
# either the width or the rail thickness fails here rather than quietly slicing it.
assert (T - _SEG_JW) / 2 - _SEG_J.clearance >= D.MIN_WALL_2P, (
    f"seam joint leaves {(T - _SEG_JW) / 2 - _SEG_J.clearance:.2f} of rail wall per "
    f"side, under the {D.MIN_WALL_2P} two-bead tier — narrow _SEG_JW or thicken the rail")
# guard: the seam JOINT (X-footprint s−ROOT .. s+reach, at the RAILS) must not overlap
# a rib -- the rib runs to the rails there, so an overlap would slice it.
for _s in SPLIT_X:
    _rib_hit = [rx for rx in _RIB_X
                if (rx + _RIB_W / 2) > (_s - _SEG_ROOT) and (rx - _RIB_W / 2) < (_s + _SEG_JX1)]
    assert not _rib_hit, f"SPLIT_X {_s} seam joint overlaps rib(s) {_rib_hit} — move it into a rib gap"
# Z — the install axis — carries NO seam hardware (user). It does not need any. The
# body is not three loose pieces bolted together; it is one assembly whose pieces are
# closed over by everything that follows: the deck panels ride a +Z-retaining dovetail
# groove in BOTH segments' rail tops, and both endplates socket the rail ends. The
# FINAL lock is the four LEG SCREWS (user): once the leg stubs are pinned to the
# corners, the whole body is captive and nothing can come apart — which is why no glue
# is needed anywhere and why a seam screw would be redundant hardware. So the seam
# joint does exactly its own job — X and Y by shape — and nothing more.

def _diamond_xz(cx, cz, h, yr):
    """Diamond (45°) prism through a rail (axis Y) — a self-supporting hole in the
    vertically-printed rail web (its crown is a 45° peak, not a flat bridge)."""
    p = [(cx, cz + h), (cx + h, cz), (cx, cz - h), (cx - h, cz)]
    y0 = yr - (T + 2.0) / 2.0
    pts = [cq.Vector(x, y0, z) for x, z in p]
    face = cq.Face.makeFromWires(cq.Wire.makePolygon([*pts, pts[0]]))
    return cq.Workplane("XY").add(cq.Solid.extrudeLinear(face, cq.Vector(0, T + 2.0, 0)))


# ── motor-9 cable cutout ──────────────────────────────────────────────────
# The +X-most motor's body reaches the -Y rail, so the harness trunk corridor is blocked
# there; the trunk dips OUTBOARD into the rail behind it (wiring._rail_pts / CUTOUT_Y). We
# notch the -Y rail's inner face for those cables over that span and DROP the diamond
# lightening there (keep the rail SOLID around the notch, per the user). +X-most motor.
_M9X_CH = D.motor_pos(D.N_STRINGS - 1)[0]                 # -110
M9_CUT_X0, M9_CUT_X1 = _M9X_CH - 25.0, _M9X_CH + 35.0     # cutout X-span (-135..-75; covers the m9 tee run)
M9_CUT_YBACK = Y_LO + T / 2 - 4.0                         # notch back: inner face -> 4mm into the rail
M9_CUT_Z0, M9_CUT_Z1 = -64.0, -40.0                      # trunk Z-band (above the rib tops, over the top lane)


def _rail(y):
    """A deep longitudinal rail. The strings bow the body about the Y axis, so the
    top/bottom EDGES are the high-stress flanges and the mid-depth sits near the
    neutral axis — lighten that web with a row of self-supporting diamonds (an
    I-beam by material placement: most of the bending stiffness is kept for far
    less mass). Solid is kept at the ~14 mm flanges, the dovetail joints, and the
    loaded ends (bulkhead/rib ties) for transport robustness."""
    rail = box_at(X_BRIDGE - X_NUT, T, Z_TOP - Z_BOT, x=_XC, y=y, z=_ZC)
    FL = 14.0                                   # flange kept top & bottom
    h = (Z_TOP - Z_BOT) / 2 - FL - 2.0          # diamond half-diagonal in the web band
    step = 2 * h + 8.0
    def ok(cx):                                 # leave the string-mount ends + joints SOLID
        return (cx + h < D.BRIDGE_AXLE_X - 10.0     # bridge support / bulkhead bond zone
                and cx - h > -560.0                  # keyhead bulkhead bond zone
                and all(abs(cx - s) > h + 14.0 for s in SPLIT_X)
                and not (y == Y_LO and M9_CUT_X0 - h < cx < M9_CUT_X1 + h))   # solid at the m9 cable cutout
    cx = X_BRIDGE - 30.0
    while cx > X_NUT + 30.0:
        if ok(cx):
            rail = rail.cut(_diamond_xz(cx, _ZC, h, y))
        cx -= step
    return rail


def _rib(x, w=_RIB_W):
    """Chunky cross-rib, rail-to-rail, its top flush with the motor rest (FLOOR_TOP)."""
    return box_at(w, Y_HI - Y_LO, MB.FLOOR_TOP - Z_BOT,
                  x=x, y=(Y_HI + Y_LO) / 2, z=(MB.FLOOR_TOP + Z_BOT) / 2)


RACE_HW   = 2.4     # wire-raceway half-width — passes the fattest cable (Ø2.6 USB)
RACE_WALL = 3 * D.NOZZLE_D   # 2.4 raceway vertical wall height above its floor (was 2.0)


def _raceway(cy, z0, x, thick):
    """Wire raceway through a cross-rib (axis X): flat floor + vertical walls +
    a 45° gable roof (self-supporting in the vertical print — its crown is a
    peak, not a flat bridge). SHALLOW on purpose: the floor z0 is derived just
    ABOVE the knee-lever rib-mortise tip (see _build_full), so the harness can
    never block a floating tenon sliding along the rib to any knee depth."""
    pts = [(cy - RACE_HW, z0), (cy + RACE_HW, z0),
           (cy + RACE_HW, z0 + RACE_WALL), (cy, z0 + RACE_WALL + RACE_HW),
           (cy - RACE_HW, z0 + RACE_WALL)]
    return (cq.Workplane("YZ").workplane(offset=x - (thick + 2.0) / 2.0)
            .polyline(pts).close().extrude(thick + 2.0))


def _build_full() -> cq.Workplane:
    body = _rail(Y_HI).union(_rail(Y_LO))
    # motor-9 cable cutout: notch the -Y rail inner face for the trunk that dips behind the
    # +X-most motor (diamonds already dropped over this span in _rail).
    body = body.cut(box_at(M9_CUT_X1 - M9_CUT_X0, -116.0 - M9_CUT_YBACK, M9_CUT_Z1 - M9_CUT_Z0,
                           x=(M9_CUT_X0 + M9_CUT_X1) / 2, y=(M9_CUT_YBACK + -116.0) / 2,
                           z=(M9_CUT_Z0 + M9_CUT_Z1) / 2))
    for x in _RIB_X:                                  # per-motor + bridge/nut cross-ribs (−Z)
        body = body.union(_rib(x))
    # knee/pedal lever mounts: cut a christmas-tree mortise into EVERY rib (so a lever can mount in
    # any bay -- its two tenons drop into the two ribs flanking the chosen bay). Even rib pitch -> the
    # one tenon fits all. (Retention is a set screw that presses the rib ledge -- no per-bay pilot.)
    from . import knee_lever as _KL
    for _rx in _RIB_X:
        body = body.cut(_KL.rib_mortise(_rx))
    # (the pickup now mounts entirely in its deck cover piece — top_plate.py — so
    # the old rail bosses/grooves/X-lock stations that used to live here are gone)
    # keyhead: the box-closure bulkhead is now a SEPARATE, removable part
    # (keyhead_endplate.py) so the deck panels slide out -X for service. It plugs
    # into the rail-end channels and is clamped down by the nut-block bolts (whose
    # inserts it carries) - lift the nut block off and the endplate lifts out. The
    # chassis keeps the compression wall + a shallow seat channel in each rail end
    # for the endplate's tabs.
    # (NO bottom tie/seat rib: the endplate part now fills its own body to the bed
    # and the -X end is tied by the keyhead block + leg stubs + the -570 rib. The
    # old _rib(_kx, 30) sat almost entirely inside the keyhead's removed zone (x <
    # KH_RAIL_X), leaving only a ~1.4 mm vestigial full-width sliver at its +X edge
    # -- which carried the TRRS harness window. Dropped at the source.)
    _kx = D.NUT_BLOCK_X - 9.0                               # endplate centre line
    ky = D.nut_y(0) + 9.0                                  # +Y-most string (index 0) + margin
    body = body.union(box_at(4.0, 2 * ky, 4.0,            # +X compression wall (below the strings)
                             x=D.NUT_BLOCK_X + 6.0, y=0, z=Z_TOP + 2.0))
    for _yf, _s in ((Y_HI - T / 2, 1), (Y_LO + T / 2, -1)):   # endplate tab channels
        body = body.cut(box_at(12.0, 3.5, Z_TOP - (Z_BOT + 8.0),
                               x=_kx, y=_yf + _s * 1.5, z=(Z_TOP + Z_BOT + 8.0) / 2))
    # (the old leg-socket dovetail slots + the Ø9.8 TRRS web way are GONE —
    # FLUSH-LEG round: the legs moved inboard to the wall plane and attach
    # via BODY STUBS whose octagon wall tenons mortise the rail band; see
    # the cuts after the end-takeover section below, and legs._body_stub)
    # electronics-tray drop-in channels: one vertical channel per rail inner
    # face (open at the top - the tray lowers in from above and its tabs
    # bottom on the channel floors), placed in the only solid-web window
    # between the leg dovetail slot and the rail diamonds
    from .electronics import TAB_X0, TAB_X1, CH_W, CH_D, TRAY_Z0
    _cxm = (TAB_X0 + TAB_X1) / 2
    for _yr, _s in ((Y_HI, 1), (Y_LO, -1)):
        _yf = _yr - _s * T / 2                         # inner face
        body = body.cut(box_at(CH_W, CH_D + 1.0, Z_TOP + 1.0 - TRAY_Z0,
                               x=_cxm, y=_yf + _s * (CH_D - 1.0) / 2,
                               z=(TRAY_Z0 + Z_TOP + 1.0) / 2))
    # AFE boss: widen the bridge cross-rib's -Y end into a solid pad that
    # carries the analog front-end board, sitting BELOW the pickup and INBOARD
    # of the leg barrel - so it fouls neither. Bonds to the bridge rib (no
    # cantilever), prints as a vertical block off the bed. Two posts hold the board.
    from .electronics import (AFE_X0, AFE_X1, AFE_Y0, AFE_Y1, AFE_Z,
                              AFE_PED_TOP)
    body = body.union(box_at(AFE_X1 + 2 - (AFE_X0 - 2), AFE_Y1 + 2 - (AFE_Y0 - 2),
                             AFE_PED_TOP - Z_BOT,
                             x=(AFE_X0 - 2 + AFE_X1 + 2) / 2,
                             y=(AFE_Y0 - 2 + AFE_Y1 + 2) / 2,
                             z=(Z_BOT + AFE_PED_TOP) / 2))
    # two posts hold the board (tops flush -> it RESTS on them); the -X/-Y post
    # is a fat boss carrying one M2 anchor so a single screw retains the AFE (no
    # snap/flexure -- the deliberate rule). The pedestal is solid below, so the
    # self-tap runs full depth.
    _afe_scr = (AFE_X0 + 4, AFE_Y0 + 4)
    for _px, _py in (_afe_scr, (AFE_X1 - 4, AFE_Y1 - 4)):
        _is_scr = _px == _afe_scr[0] and _py == _afe_scr[1]
        body = body.union(cyl(7.0 if _is_scr else 6.0, AFE_Z - AFE_PED_TOP, z=AFE_PED_TOP)
                          .translate((_px, _py, 0)))
    body = cut_anchor(M2, body, (_afe_scr[0], _afe_scr[1], AFE_Z), (0, 0, -1),
                      M2.anchor_min_wall)
    # NO wire raceways through the ribs. The ribs are for STRUCTURE and holding LEVERS
    # only: every rib carries the knee/pedal-lever octagon mortise along its whole Y, and
    # a lever slides to ANY knee depth in ANY bay -- so a cable sitting in a rib would
    # block a lever from being installed at that depth. The harness instead runs along the
    # -Y rail's INNER FACE, in the vertical channel ABOVE the rib tops (z > FLOOR_TOP)
    # where no rib reaches; it clears every motor except the +X-most (motor 9), whose body
    # reaches the -Y rail -- handled by the strategic cable cutout in the rail there
    # (_motor9_cable_cut below). See wiring.py.
    # DECK JOINT: the plates cap the rail and drop a vertical DOVETAIL tongue into a
    # groove milled in the rail top. Lower the rail top to z0 across the whole deck
    # X-span (rail -X end up to the +X takeover line TP_EP_GX) so a plate sits flush,
    # then mill the groove (matches top_plate's tongue + clearance). The groove runs
    # right to TP_EP_GX; +X of there the bridge takes over (rail removed below).
    _gx0 = TP_X1 - 2.0
    for _yc in (Y_HI, Y_LO):
        # shave the rail top to z0 across the deck span + mill the groove
        body = body.cut(box_at(TP_EP_GX - _gx0, T + 0.5, (Z_TOP + 1.0) - TP_GZ0,
                               x=(_gx0 + TP_EP_GX) / 2, y=_yc,
                               z=(TP_GZ0 + Z_TOP + 1.0) / 2))
        body = body.cut(_deck_tg(_yc, _gx0, TP_EP_GX, mortise=True))
    # NB: motor faceplate walls are NOT fused here -- _segments() adds each plate WHOLE to
    # the print segment that owns its motor (so a split can cross a plate without slicing it).
    # +X end: the bridge endplate TAKES OVER the +X end as a solid block (mirror of the
    # keyhead -X takeover): remove the rail ENTIRELY at x > TP_EP_GX (z full) so the
    # bridge fills it and IS the +X cross-tie (no separate crossbar); it's held by the
    # rail-end dovetails alone. Only the dovetail tongues it sockets are added back.
    body = body.cut(box_at((X_BRIDGE + 5.0) - TP_EP_GX, (Y_HI - Y_LO) + T + 4.0,
                           (Z_TOP + 1.0) - (Z_BOT - 1.0),
                           x=(TP_EP_GX + X_BRIDGE + 5.0) / 2, y=(Y_HI + Y_LO) / 2,
                           z=((Z_BOT - 1.0) + (Z_TOP + 1.0)) / 2))
    # KEEP a ~10 mm rail shell hugging the +X leg socket (the removal above stripped
    # the rail off the leg's +X reach); the bridge endplate nests over this shell.
    body = body.union(_leg_shell(LEG_STATIONS_X[0], *LEG_SHELL_PX))
    for _yc in (Y_HI, Y_LO):
        body = body.union(_br_tongue(_yc))
    # keyhead TAKES OVER the -X end as a solid block (its edge shows from the front like
    # the bridge end): remove the rail ENTIRELY at x < KH_RAIL_X (z full) so the keyhead
    # fills it and IS the -X cross-tie (no separate crossbar); it's held by the rail-end
    # dovetails alone (no screw). Only the dovetail tongues it sockets are added back.
    body = body.cut(box_at(KH_RAIL_X - (X_NUT - 5.0), (Y_HI - Y_LO) + T + 4.0,
                           (Z_TOP + 1.0) - (Z_BOT - 1.0),
                           x=(KH_RAIL_X + X_NUT - 5.0) / 2, y=(Y_HI + Y_LO) / 2,
                           z=((Z_BOT - 1.0) + (Z_TOP + 1.0)) / 2))
    # KEEP a ~10 mm rail shell hugging the -X leg station (mirror of the +X end).
    body = body.union(_leg_shell(LEG_STATIONS_X[1], *LEG_SHELL_NX))
    for _yc in (Y_HI, Y_LO):
        body = body.union(_kh_tongue(_yc))
    # ── WIDE CORNER RIBS (user): one per end, tying both leg corners to
    # the rails and hosting the crossing grooves CONTINUOUSLY, so all
    # three stub ridges run full length. x: from the endplate end wall's
    # inner face (+0.4 clearance) to the leg's inboard face (~34 wide);
    # the CHASSIS-zone part is rail-to-rail (unions rails / kept shells /
    # station ribs), the ENDPLATE-zone part fits the foot hollow with 0.4
    # wall clearance. Top flush with the motor rest (FLOOR_TOP, like every
    # rib) — 1.15 under the electronics tray's bottom (-64.0).
    _WR_Y0, _WR_Y1 = Y_LO + T / 2 + 0.4, Y_HI - T / 2 - 0.4
    for _c0, _c1, _h0, _h1 in (
            (KH_RAIL_X, LEG_STATIONS_X[1] + LEG_W / 2,
             EP_TIP_NX + T + 0.4, KH_RAIL_X),
            (LEG_STATIONS_X[0] - LEG_W / 2, TP_EP_GX,
             TP_EP_GX, EP_TIP_PX - T - 0.4)):
        body = body.union(box_at(abs(_c1 - _c0), Y_HI - Y_LO,
                                 MB.FLOOR_TOP - Z_BOT, x=(_c0 + _c1) / 2,
                                 y=(Y_HI + Y_LO) / 2,
                                 z=(MB.FLOOR_TOP + Z_BOT) / 2))
        body = body.union(box_at(abs(_h1 - _h0), _WR_Y1 - _WR_Y0,
                                 MB.FLOOR_TOP - Z_BOT, x=(_h0 + _h1) / 2,
                                 y=(_WR_Y0 + _WR_Y1) / 2,
                                 z=(MB.FLOOR_TOP + Z_BOT) / 2))
    # wired-corner services through the -X wide rib: the Ø10.5 JACK WELL
    # (the naked 10-03404 drops through it into the stub's way AFTER the
    # slide; the well sleeves the barrel) and the OVER-RIB raceway lane
    # (y 50.5, floor -67.0: the pigtail rides it east ABOVE the ridge
    # roofs (-67.91) and NORTH of the electronics tray, gabled-window
    # through the station rib, then drops to the bus-B tee)
    from .legs import TRRS_DY as _LEG_TDY
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        5.25, (MB.FLOOR_TOP - Z_BOT) + 2.0,
        cq.Vector(LEG_STATIONS_X[1] - 5.0, LEG_Y[0] - _LEG_TDY, Z_BOT - 1.0),
        cq.Vector(0, 0, 1))))
    #   ^ the TRRS axis rides the octagon's deep waist (legs.TRRS_DY) — the
    #     well tracks the stub's relocated jack way
    body = body.cut(_raceway(50.5, -67.0, -604.75, 31.5))
    # +X tee-10 clearance notch out of the bridge rib's west face (the
    # tee pokes 2.4 into it; box clears the PCB + header margin)
    body = body.cut(box_at(4.0, 17.0, (MB.FLOOR_TOP - Z_BOT) + 2.0,
                           x=-34.5, y=-108.0,
                           z=(MB.FLOOR_TOP + Z_BOT) / 2))
    # ── Y-INSTALL BODY-STUB JOINERY (user: the stubs print on their side,
    # so they SLIDE IN ALONG Y; cut LAST — the shells above host the wall
    # crossings). Each corner: three Y-running octagon ridges on the stub
    # top (legs.py) ride grooves cut here + in the endplates from the SAME
    # shared negatives (legs.corner_groove_negatives — cross-part grooves
    # align by construction): the side-wall band gets octagon THROUGH-
    # crossings at the THIRDS of the leg<->side-panel overlap (user:
    # station +0.667 / −10.667 toward inboard — legs._cross_x; their
    # side-face openings are filled flush by the ridge ends), and whatever
    # chassis crosses the corner (kept shell, seat rib, the +X comb rib)
    # gets tunnelled for extra engagement. The end-wall groove's blind end
    # (in the endplate) is the flush hard stop. ONE vertical M4 per stub
    # drops down the rail web from under the deck into the INBOARD ridge
    # = the Y-retention SHEAR PIN: Ø8.4 head well to Z_BOT+30 (3 mm hex
    # key reaches through it), Ø4.6 shaft way on down to the groove, Ø3.6
    # pilot in the ridge. Screw: M4×35 (head -45.15, tip -80.15).
    from .legs import corner_groove_negatives as _cgn, _cross_x as _cx
    _xc_mid = sum(LEG_STATIONS_X) / 2
    for _sx in LEG_STATIONS_X:
        _egx = -1.0 if _xc_mid > _sx else 1.0       # outboard x sign
        _xm4 = _sx + _cx(_egx)[1]                   # inboard crossing ridge
        for _yr, _s in ((Y_HI, 1), (Y_LO, -1)):
            _lc = LEG_Y[0] if _s > 0 else LEG_Y[1]  # flush leg centreline
            for _n in _cgn(_sx, _lc, float(_s), _egx, Z_BOT):
                body = body.cut(_n)
            body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
                2.3, 24.5, cq.Vector(_xm4, _yr, Z_BOT + 6.0),
                cq.Vector(0, 0, 1))))
            body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
                4.2, (TP_GZ0 - TP_TG_DEPTH - 0.1) - (Z_BOT + 30.0),
                cq.Vector(_xm4, _yr, Z_BOT + 30.0),
                cq.Vector(0, 0, 1))))
    # (the old y-33 / z-70.6 Ø7 harness window is GONE — the wired
    # corner's pigtail now rides the OVER-RIB raceway lane at y 50.5,
    # cut with the wide corner ribs above)
    return body


# ============================================================================
# Endplate <-> leg geometry — ONE shared model for BOTH ends (they CANNOT diverge)
# ============================================================================
# Each endplate is the same shape mirrored: a solid that closes its end, wraps its
# leg with a T-thick WALL, nests over the kept leg shell with EP_LEG_CLR clearance,
# and leaves EP_LEG_BUFFER of solid body between the leg's dovetail tenon and that
# wall. Measuring everything INBOARD from each endplate's outer face ("tip") with
# the SAME three constants guarantees both ends are identical by construction:
#   pocket edge = tip  ∓ T            (the endplate wall is T thick)
#   shell  edge = pocket ∓ EP_LEG_CLR (the kept rail shell sits a clearance inboard)
#   leg tenon   = shell ∓ EP_LEG_BUFFER          → station ∓ DT_FACE_HW further in
# (the BUFFER is SOLID BODY, so it's measured from the SHELL face where material
#  actually begins — the wall<->shell clearance gap is air and doesn't count.)
# The end removal would otherwise strip the rail off the leg + leave the endplate
# clearing it with a big empty box; instead we KEEP a rail shell (its T wall IS the
# body wrap) over the leg, re-cutting the leg dovetail slot in it (_leg_shell).
KH_EP_THK     = D.ENDPLATE_W  # keyhead endplate thickness in X (= keyhead_endplate.T_EP)
EP_LEG_CLR    = EP_TOP_CLR    # assembly clearance: endplate foot pocket vs the kept shell
                              # (= the top-joint clearance -- ONE value for both L joints)
EP_LEG_BUFFER = D.XBAR        # 10 mm solid body between the leg tenon and the endplate wall
EP_TIP_NX = KH_X - KH_EP_THK              # keyhead -X outer face (-636)
EP_TIP_PX = D.BRIDGE_BASE_X1              # bridge +X outer tip (8.5) -- the ACTUAL outer face,
                                          # so the leg/shell/wall track it (10 mm wall preserved)


LEG_W = 44.0                  # = legs.SQ_W (legs.py owns the part; the chassis
                              # owns the placement)


def _leg_geom(tip, sign):
    """All inboard from one endplate's outer face `tip`. `sign` = the direction from
    the tip toward the instrument body (+1 for the -X/keyhead end, -1 for the +X/
    bridge end). Returns (pocket_edge, shell_edge, station) for that leg.
    FLUSH-X round (user): the station sits LEG_W/2 inboard of the tip, so the
    leg's outer X face lies ON the endplate's outer face (the old formula kept
    a dovetail-era buffer that inset the legs 12.4)."""
    pocket = tip + sign * T
    shell = pocket + sign * EP_LEG_CLR
    station = tip + sign * LEG_W / 2
    return pocket, shell, station


_PKT_NX, _SHELL_NX, _STN_NX = _leg_geom(EP_TIP_NX, +1)    # -X end → body is +X of the tip
_PKT_PX, _SHELL_PX, _STN_PX = _leg_geom(EP_TIP_PX, -1)    # +X end → body is -X of the tip
# the kept shell spans from its pinned outer edge to the rail-takeover join line:
LEG_SHELL_NX = (_SHELL_NX, KH_RAIL_X)       # -X leg: -625.6 .. -610.6 (reaches the rail end)
LEG_SHELL_PX = (TP_EP_GX, _SHELL_PX)        # +X leg: -17.5 .. 5.6
# leg stations: (+X leg, -X leg) — outer faces ON the endplate tips (flush X):
LEG_STATIONS_X = (_STN_PX, _STN_NX)         # (-13.4, -614.2)
# Trim the rib comb against the leg BODY STUBS (SQ_W-sq at each station): a comb rib
# whose footprint collides with a stub is redundant -- the stub + its endplate are the
# corner cross-tie there -- and it merges into the stub as a clipped nub while its lever
# mortise would gouge the stub. Drop those (deferred to here: the stations resolve after
# _rib_positions). A rib within (SQ_W + rib_w)/2 of a station touches its stub.
from .legs import SQ_W as _STUB_W
_RIB_X = [x for x in _RIB_X
          if all(abs(x - _st) >= (_STUB_W + _RIB_W) / 2.0 for _st in LEG_STATIONS_X)]
# FLUSH-LEG round (user): the 44-sq legs sit FLUSH with the outer wall
# planes instead of outset on the rail centrelines — centres 17 inboard
# of the rails. Everything leg-shaped (stubs, columns, pedal bar rail)
# derives its Y from here.
LEG_Y = (Y_HI + T / 2 - LEG_W / 2,          # +Y legs: 42.75 (outer face 64.75)
         Y_LO - T / 2 + LEG_W / 2)          # -Y legs: -116.75


def _leg_shell(sx, x0, x1):
    """The kept rail shell around one leg station (both rails), spanning x0..x1
    over the rail Y-bands, from the bed up to the FOOT LINE (z = KH_DT_Z0 =
    -23.15). The shell only wraps the leg tenon + its 10 mm border BELOW the foot
    line; ABOVE the foot line (z -23.15..6) is the endplate's own solid fill band,
    not the shell -- so the shell stops at -23.15 and the endplate band sits on
    top of it. Re-cut the leg dovetail slot in it afterward."""
    out = None
    z1 = KH_DT_Z0                                     # foot line (-23.15); the endplate's
                                                      # solid fill band takes over above this
    for yr, s in ((Y_HI, 1), (Y_LO, -1)):
        # bottom EXACTLY on the bed (Z_BOT) -- the same constant the chassis/endplate
        # floors use -- so the shell can't poke below the instrument floor. (This is a
        # UNION, so it needs no -Z boolean overshoot; the leg-slot CUT below overshoots
        # on its own.)
        sh = box_at(x1 - x0, T, z1 - Z_BOT,
                    x=(x0 + x1) / 2, y=yr, z=(Z_BOT + z1) / 2)
        # (no dovetail re-cut — FLUSH-LEG round: the shells now host the
        # body stubs' octagon wall mortises, cut in the main builder)
        out = sh if out is None else out.union(sh)
    return out


def _seg_tenon(s, yr):
    """The −X segment's half of the seam joint at split X=s, rail Y=yr: a plan-plane
    T prism standing from the bed up to the deck-groove floor. (The bridge/keyhead END
    joints are a different site — they use the low _br_tongue/_kh_tongue dovetails.)"""
    return _SEG_J.tenon(root=_SEG_ROOT).translate((s, yr, Z_BOT))


def _seg_mortise(s, yr):
    """The +X segment's cavity — a THROUGH slot: open at the segment's BOTTOM face
    (the tenon enters there as the segment is lowered on) and open at the top through
    the rail crown, so the cavity has no ceiling to bridge and no 'blind pocket' that
    the deck groove would have to pass the tenon through. Z is unretained here BY
    DESIGN — cadkit's install axis; the assembly around it closes Z (see the SEGMENT
    JOINT block: deck, endplates, and finally the four leg screws)."""
    return (_SEG_J.mortise(drop=_SEG_ROOT + 1.0,
                           length=(TP_GZ0 + 2.0) - (Z_BOT - 1.0))
            .translate((s, yr, Z_BOT - 1.0)))


def _end_dt(x_face, into, yc, z0, z1, socket=False, top_clr=TP_TG_DEPTH):
    """ONE Y-flaring vertical dovetail on an end-contact face at x=x_face, Z-extruded
    z0..z1, centred on Y=yc. `into` (+1/-1) points from the face toward the endplate
    tip: the trapezoid is NARROW at x_face (rail/shell side) and WIDE KH_DT_DEPTH into
    the endplate, so string tension can't draw the wide foot back out. The body carries
    it (tenon); the endplate cuts it (socket=True widens it by the clearance all round).
    `top_clr` raises the SOCKET top above the tenon top (z1) so the tenon seats on its
    real stop, not the mortise ceiling: the UPPER dovetail uses TP_TG_DEPTH (its top sits
    in the deck zone). The LOWER dovetail instead passes z1 = foot line - KH_DT_SEAT with
    top_clr = KH_DT_SEAT, so the MORTISE face lands exactly on the foot line (-23.15) while
    the tenon is the shortened one (-23.25) -- the seating clearance, kept off the face."""
    g = KH_DT_CLR if socket else 0.0
    wr, wt = KH_DT_WR + g, KH_DT_WT + g
    x_in = x_face + into * KH_DT_DEPTH
    z_hi = z1 + (top_clr if socket else 0.0)
    pts = [(x_face, yc - wr), (x_face, yc + wr),        # narrow (rail/shell face)
           (x_in, yc + wt), (x_in, yc - wt)]            # wide (into the endplate)
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z_hi - z0)


def _kh_tongue(yc, socket=False):
    """Keyhead joinery at Y=yc: the two stacked dovetails of the L-shaped joint (see the
    KH_DT_* block). LOWER on the wall<->leg-shell face (x=_SHELL_NX, z bed..foot line);
    UPPER on the foot<->rail-end face (x=KH_RAIL_X, z foot line..deck-groove floor). Both
    wide -X into the keyhead so the +X string pull is gripped. Body carries them; the
    keyhead drops on and sockets them. socket=True adds clearance + open tops for the cut."""
    lower = _end_dt(_SHELL_NX, -1, yc, Z_BOT, KH_DT_Z0 - KH_DT_SEAT, socket, top_clr=KH_DT_SEAT)
    upper = _end_dt(KH_RAIL_X, -1, yc, KH_DT_Z0, TP_GZ0 - TP_TG_DEPTH, socket)
    return lower.union(upper)


def _br_tongue(yc, socket=False):
    """Bridge joinery at Y=yc: the mirror of _kh_tongue across the +X takeover line. LOWER
    on the wall<->leg-shell face (x=_SHELL_PX, z bed..foot line); UPPER on the foot<->rail
    face (x=TP_EP_GX, z foot line..deck-groove floor). Both wide +X into the bridge so the
    +X bearing wrap (which pulls the bridge -X) can't draw the wide foot out. Body carries
    them; the bridge drops on and sockets them. socket=True adds clearance + open tops."""
    lower = _end_dt(_SHELL_PX, +1, yc, Z_BOT, KH_DT_Z0 - KH_DT_SEAT, socket, top_clr=KH_DT_SEAT)
    upper = _end_dt(TP_EP_GX, +1, yc, KH_DT_Z0, TP_GZ0 - TP_TG_DEPTH, socket)
    return lower.union(upper)


def _seg_box(a, b):
    h = (Z_TOP + 18.0) - (Z_BOT - 6.0)
    return box_at(abs(a - b) + 0.02, (Y_HI - Y_LO) + 40.0, h,
                  x=(a + b) / 2, y=(Y_HI + Y_LO) / 2, z=(Z_TOP + 18.0 + Z_BOT - 6.0) / 2)


def _is_split(x):
    return any(abs(x - s) < 1e-6 for s in SPLIT_X)


def _largest(seg):
    """Keep only the largest solid: the lightening diamonds + wire raceways + joint
    cuts can pinch off tiny disconnected slivers near the splits; those print as
    loose chips. Drop them (each is <1 % of the body and isn't attached anyway)."""
    sols = seg.val().Solids()
    if len(sols) <= 1:
        return seg
    return cq.Workplane("XY").add(max(sols, key=lambda s: s.Volume()))


def _segments():
    full = _build_full()
    # +X-most bound must clear the +X-most chassis feature -- the LOWER bridge dovetail
    # tongue tip (_SHELL_PX + KH_DT_DEPTH = 13.6); a smaller bound (the old X_BRIDGE+2 = 8)
    # sliced the tongue off at the segment boundary.
    edges = [_SHELL_PX + KH_DT_DEPTH + 2.0] + sorted(SPLIT_X, reverse=True) + [X_NUT]
    # each motor's faceplate plate is fused WHOLE into the segment whose X-band holds its
    # motor -- a plate straddling a split overhangs into the neighbour rather than being cut.
    _motor_x = [D.motor_pos(i)[0] for i in range(D.N_STRINGS)]
    segs = []
    for i in range(len(edges) - 1):
        a, b = edges[i], edges[i + 1]                 # a (+X) > b (−X)
        seg = full.intersect(_seg_box(a, b))
        if _is_split(b):                              # −X boundary split → +X side → mortise
            for yr in (Y_HI, Y_LO):
                seg = seg.cut(_seg_mortise(b, yr))
        if _is_split(a):                              # +X boundary split → −X side → tenon
            for yr in (Y_HI, Y_LO):
                seg = seg.union(_seg_tenon(a, yr))
        for mi, mx in enumerate(_motor_x):
            if b < mx < a:                            # this segment OWNS the motor: fuse its plate whole
                seg = seg.union(MB.plates[mi])
            else:                                     # a neighbour's plate may overhang in: relieve it
                seg = seg.cut(MB.plates[mi])
        segs.append(_largest(seg))
    return segs


segments = _segments()
