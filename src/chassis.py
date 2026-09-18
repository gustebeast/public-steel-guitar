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

import math

import cadquery as cq

from . import dimensions as D
from . import motor_bank as MB
from .components import MOTOR_PULLEY_STANDOFF
from .helpers import box_at, cyl
from cadkit.joinery import PrintSpec, joint

T        = D.WALL_THICKNESS            # rail thickness (solid; slicer infills)
X_BRIDGE = D.BRIDGE_BASE_X1 - 3 * D.BEAD   # 6.1: +X (bridge) end — the rails end here; the
                                       #   bridge endplate caps them (a separate flat-printed
                                       #   part). Anchored to the endplate's hardware-chained
                                       #   +X tip so the CAP it bounds is an on-grid 2.4 thick
X_NUT    = -(D.MOUNTING_SPAN + 24.0)   # −X end, extended to carry the nut block;
                                       # rail ends FLUSH with the end bulkhead's
                                       # outer face (NUT_BLOCK_X − 9 − 15)
Z_TOP    = D.STRING_Z - 8 * D.BEAD     # 9.6: rail top, 6.4 under the strings (normal
                                       # action; snapped AWAY from the strings)
Z_BOT    = MB.BED_Z                    # print bed (shared with the motor walls)
# Rail CENTRES, defined so the INNER faces stay fixed as the wall T changes (the wall
# grows outward): +Y inner clears the bearing arm, -Y inner clears the motor PCBs.
Y_HI     = D.BRIDGE_AXLE_Y + 4 * D.BEAD + T / 2   # +Y rail (inner face = axle_Y + 3.2)
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
TP_TG_DEPTH    = 8 * D.BEAD             # 6.4: the reserved groove ZONE below the deck. The
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
KH_X           = -764 * D.BEAD                   # keyhead inboard face (-611.2)
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
# (KH_DT_WR / KH_DT_WT are gone with the hand-rolled trapezoid they described: the flank
#  widths are cadkit's business now, computed from EP_J_W by the same max-min rule every
#  other joint in the body is sized by.)
KH_DT_DEPTH    = 8.0                    # dovetail reach into the endplate (X)
KH_DT_Z0       = -29 * D.BEAD           # -23.2 foot line; also the LOWER/UPPER dovetail
                                       # split (the L-corner / drop stop). Every mate
                                       # (keyhead FOOT_Z, leg shells, both dovetails)
                                       # derives from here. (The old -23.15 was "leg-tenon
                                       # top -33.15 + XBAR" -- arithmetic that had ALREADY
                                       # gone stale when the bed and XBAR moved onto the
                                       # grid, so the snap replaces a dead formula.)
KH_DT_CLR      = 0.3                    # socket clearance (Y fit) -- now what cadkit's own
                                       # policy returns for this site (PETG-GF 0.15, fit="loose"
                                       # x2 for a BLIND drop-on), so the hand-picked number and
                                       # the library's agree; asserted under _EP_J
# ── THE ENDPLATE JOINT IS A CADKIT JOINT NOW (user, 2026-09-18) ──────────────────────────
# It was the last hand-rolled joinery in the body: a Y-flaring trapezoid, i.e. exactly the
# angled dovetail cadkit RETIRED, because at a 0.8 nozzle the tenon's acute plan corners round
# DOWN while the mortise's inner corners round UP and the corners collide before the faces seat.
# The site is: the chassis (printing Z-up, ALONG the install axis -> facing 'axial') carries a
# tenon that the endplate (printing along the joint's DEPTH, from its deep end toward the mating
# face -> facing 'down') drops onto. That is cadkit's MUSHROOM site, and the shape it picks is
# the one the user drew: stem, two 45 deg flares, a two-bead waist vertical, one FLAT top -- the
# flat end is legal precisely because the mortise host prints it FIRST, on solid material.
# WIDTH is what the rail allows: the joint centres 5.0 from the instrument's outer face, and the
# cavity (width/2 + clearance) has to leave the two-bead wall there.
EP_J_W    = 7 * D.BEAD                  # 5.6 -> cavity half 3.1, outer wall 1.9
EP_J_ROOT = 3 * D.BEAD                  # 2.4 of volumetric fusion back into the chassis
_EP_AX    = PrintSpec(nozzle=0.8, material="PETG-GF", facing="axial")   # chassis: builds +Z,
                                                                       # along the install axis
_EP_DN    = PrintSpec(nozzle=0.8, material="PETG-GF", facing="down")    # endplates: deep end
                                                                       # first, mouth last
_EP_J     = joint(width=EP_J_W, length=10.0, tenon=_EP_AX, mortise=_EP_DN,
                  install="+x", depth=KH_DT_DEPTH, fit="loose")   # +x: the tenon travels +install
                                                                 # to seat, and the endplate comes
                                                                 # DOWN onto it
assert abs(_EP_J.clearance - KH_DT_CLR) < 1e-9, (
    "cadkit's clearance for this site is %.2f but KH_DT_CLR says %.2f -- one of them is stale"
    % (_EP_J.clearance, KH_DT_CLR))
assert 5.0 - (EP_J_W / 2.0 + _EP_J.clearance) >= D.MIN_WALL_2P - 1e-9, (
    "the socket leaves %.2f of rail wall outboard, under the two-bead tier"
    % (5.0 - (EP_J_W / 2.0 + _EP_J.clearance)))
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
# The grid is dimensions' (D.lever_grid_x()): as many mortises as fit across the WHOLE chassis
# floor, centred, with an equal margin at each end. Nothing here trims it. The floor runs SHELL
# FACE to SHELL FACE -- the chassis' own ends -- not to the endplate takeover faces; laying the
# grid against the takeover faces instead cost two or three stations at each end, which is the
# gap the user kept finding (2026-09-16). The agreement is asserted below, where _SHELL_NX and
# _SHELL_PX are finally in scope.
_MORT_X = list(D.lever_grid_x())
# TARGETS MOVED (user's drop-in motor pockets, 2026-09-11): a housing is now 62.3 wide on a
# 43.9 pitch, so it reaches 31.15 past its own motor and the segment that OWNS that motor
# carries the whole overhang. A segment's real footprint is therefore its end motors +-31.15,
# not the split planes -- the old targets left segment 0 at 265.5, over the bed. These put one
# motor in segment 0 and five/four in the others. BED_X asserts the lengths; wiring asserts
# that neither plane lands in the RAIL NOTCH at motor 9, where the trunk dips outboard -- a
# split there puts its tenon back through the dip (5 wires were buried in it).
SPLIT_X  = [D.lever_wall_x(_t)
            for _t in (-205.0, -409.5)]  # 2 cuts → 3 segments < BED_X, each on the centre of one of the grid's 1.6 WALLS, so the
                                       # plane itself misses every mortise (the seam JOINT is wider than a wall,
                                       # so the stations it covers are dropped instead -- see _seam_blocked). Was a
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
    _plane_hit = [rx for rx in _MORT_X if abs(_s - rx) < D.LEVER_MORT_W / 2]
    assert not _plane_hit, (f"SPLIT_X {_s} plane slices mortise(s) {_plane_hit} — it must land "
                            "in one of the 1.6 walls (D.lever_wall_x snaps to one)")
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
_SEG_ROOT = 3 * D.BEAD                 # 2.4 volumetric fusion depth back into the −X segment
# IT STARTS AT THE BOTTOM'S TOP FACE, NOT AT THE BED (user, 2026-09-15). The tenon is the only
# MATERIAL half of this joint, and run from Z_BOT it stood in the same 10.4 band as the lever
# mortises -- so the two stations flanking every seam had to be dropped and mortises went
# missing exactly where two sections meet. Started at FLOOR_TOP it is clear of that band
# altogether and the grid runs through the seam unbroken. The cavity stays a THROUGH slot: it
# is a void, so where it meets a lever mortise the two simply merge.
_SEG_JZ0  = MB.FLOOR_TOP               # tenon base = the bottom prism's top face
# WHICH SEGMENT GOES DOWN LAST IS A DESIGN DECISION, and this is it (user, 2026-09-17: the
# joinery mortise must stop cutting -Z into the lever mortises). Lower the +X segment onto a
# standing tenon and its whole bottom prism has to sweep DOWN PAST that tenon -- the prism comes
# from high above, so the tenon's entire height is inside its swept column and the cavity has to
# run clean through the floor. That through-channel is what was eating the 3.2 walls between
# lever mortises at every seam. Lower the TENON'S OWN segment last instead and the tenon simply
# descends into the cavity from above: nothing sweeps the floor, so the cavity can stop at the
# floor's top face. ASSEMBLY ORDER, then: the +X-MOST segment is placed first and each neighbour
# comes down on it working -X (every segment carries its tenon at its +X end and its mortise at
# its -X end, so the chain is consistent). The endplates socket the rail ends and the deck rides
# both crowns, both of which come after, so nothing else cared which way this went.
_SEG_J    = joint(width=_SEG_JW, length=_SEG_JZ1 - _SEG_JZ0, depth=_SEG_JD,
                  tenon=_UP, mortise=_UP, install="-z")   # signed: the TENON's segment is
                  # lowered on, so RELATIVE to the mortise's host the tenon travels -Z to seat
# ...and the cavity's own floor: 0.4 below the bottom prism's top face, which is a SKIM off that
# face rather than a channel through it. The 0.4 is clearance, not a seat -- the segments' Z is
# set by the rail crowns and the endplates, and the tenon must not bottom out before the rail
# faces meet (if it ever does sag, this floor is a hard stop, which is a bonus, not the design).
_SEG_RELIEF_CLR = 0.4                   # the gap under the tenon: the cavity's floor sits this
                                        # far below the bottom prism's top face AND its 45 deg
                                        # ramp this far below the tenon's, so the tenon lands on
                                        # neither -- one number, both faces
_SEG_MZ0  = MB.FLOOR_TOP - _SEG_RELIEF_CLR
_SEG_JX1  = _SEG_J.dims["depth_used"]  # the tenon's +X reach past the seam plane
# the rail wall left beside the cavity is a printed wall like any other, and the only
# thing keeping it at tier is the hand-picked width above. Say so, so a later change to
# either the width or the rail thickness fails here rather than quietly slicing it.
assert (T - _SEG_JW) / 2 - _SEG_J.clearance >= D.MIN_WALL_2P, (
    f"seam joint leaves {(T - _SEG_JW) / 2 - _SEG_J.clearance:.2f} of rail wall per "
    f"side, under the {D.MIN_WALL_2P} two-bead tier — narrow _SEG_JW or thicken the rail")
# guard: the seam JOINT (X-footprint s−ROOT .. s+reach, at the RAILS) must not overlap
# a rib -- the rib runs to the rails there, so an overlap would slice it.
# The seam and the grid no longer argue in X: the split PLANE runs down the middle of a 3.2
# wall, and the joint's material half starts above the mortise band in Z (_SEG_JZ0). So no
# station is dropped for a seam -- asserted against the real solids in _build_full.
# Z — the install axis — carries NO seam hardware (user). It does not need any. The
# body is not three loose pieces bolted together; it is one assembly whose pieces are
# closed over by everything that follows: the deck panels ride a +Z-retaining dovetail
# groove in BOTH segments' rail tops, and both endplates socket the rail ends. The
# FINAL lock is the four LEG SCREWS (user): once the leg stubs are pinned to the
# corners, the whole body is captive and nothing can come apart — which is why no glue
# is needed anywhere and why a seam screw would be redundant hardware. So the seam
# joint does exactly its own job — X and Y by shape — and nothing more.

# ── motor-9 cable cutout ──────────────────────────────────────────────────
# The +X-most motor's body reaches the -Y rail, so the harness trunk corridor is blocked
# there; the trunk dips OUTBOARD into the rail behind it (wiring._rail_pts / CUTOUT_Y). We
# notch the -Y rail's inner face for those cables over that span and DROP the diamond
# lightening there (keep the rail SOLID around the notch, per the user). +X-most motor.
_M9X_CH = D.motor_pos(D.N_STRINGS - 1)[0]                 # -110
M9_CUT_X0, M9_CUT_X1 = _M9X_CH - 25.0, _M9X_CH + 35.0     # cutout X-span (covers the m9 trunk dip)
M9_CUT_YBACK = Y_LO + T / 2 - 4.0                         # notch back: inner face -> 4mm into the rail
M9_CUT_Z0, M9_CUT_Z1 = -64.0, -40.0                      # trunk Z-band (above the rib tops, over the top lane)


def _rail(y):
    """A deep longitudinal rail, SOLID.

    It used to carry a row of 45 deg diamond lightening holes through the web -- an I-beam by
    material placement, on the argument that the strings bow the body about Y so the mid-depth
    sits near the neutral axis. They are gone (user, 2026-09-15): the rail is a side WALL as
    much as a beam, and a wall full of holes does not hold light or motor noise in, which is
    what the sealed bottom is for. The mass they saved is small beside what they cost the
    enclosure."""
    return box_at(X_BRIDGE - X_NUT, T, Z_TOP - Z_BOT, x=_XC, y=y, z=_ZC)


def mort_segments(station):
    """The WORLD (y0, y1) runs of the mortise at `station`.

    Most stations are one run, from outboard of the -Y rail to the light window's face. The
    three at each end are the ones the FEET ride, and they get TWO SHORT runs instead -- one
    over each foot, open outboard so the foot can slide in, with the floor BETWEEN the feet left
    solid (user, 2026-09-17). Nothing rides there, and it is most of the floor's length."""
    from . import knee_lever as _KLY
    near = _KLY.MOUNT_Y + _KLY.MORT_Y0                   # -Y mouth, outboard of the -Y rail
    if abs(D.mortise_y_end(station) - D.LIGHT_WIN_Y0) < 1e-9:
        return [(near, D.LIGHT_WIN_Y0)]
    lo, hi = LEG_Y[1] + LEG_W / 2.0, LEG_Y[0] - LEG_W / 2.0
    # ...and both runs KEEP OFF WHATEVER ELSE DROPS THROUGH THE FLOOR in this station's X band
    # (D.floor_block_y): the bridge end's string access channels, the keyhead end's height-screw
    # head cavities. Both families sit on the string pitch, so the gaps between neighbours fit no
    # mortise -- what is left is the clear band outboard of them, and the +Y run starts a two-bead
    # wall past the +Y-most one (user). It still opens out past the rail, so the +Y foot can
    # slide in on it. Each station meets only what is near it in X, which is what makes the three
    # at each end come out at different lengths.
    field = D.floor_block_y(station)
    if field is not None:
        lo, hi = min(lo, field[0]), max(hi, field[1])
    return [(near, lo),                                  # over the -Y foot, open -Y
            (hi, D.MORT_FULL_Y1)]                        # over the +Y foot, open +Y


def foot_tenon_runs(sx, ly, syg):
    """[(station, y0, y1)] the tenon runs a foot at (sx, ly) can actually use.

    ONE place decides this, because two parts need the same answer: the body adapter builds a
    tenon per run, and the leg's lock pin has to know which is the OUTERMOST one it can pin. A
    run counts when a mortise is there at all, and when it is open the way that corner slides
    in -- a foot goes outboard along Y, so a run that stops short of its outboard face is no
    use to it however long it is."""
    out = []
    for st in D.lever_grid_x():
        if abs(st - sx) > LEG_W / 2.0 - LEG_TEN_W / 2.0 + 1e-9:
            continue
        y0, y1 = ly - LEG_W / 2.0, ly + LEG_W / 2.0
        seg = next((q for q in mort_segments(st) if q[0] < y1 and q[1] > y0), None)
        if seg is None:
            continue
        y0, y1 = max(y0, seg[0]), min(y1, seg[1])
        if syg > 0 and seg[1] < ly + LEG_W / 2.0 - 1e-9:
            continue
        if syg < 0 and seg[0] > ly - LEG_W / 2.0 + 1e-9:
            continue
        if y1 - y0 < 1.0:
            continue
        out.append((st, y0, y1))
    return out


def _mort_cutters(x0=None, x1=None):
    """Every lever mortise in [x0, x1] as ONE compound. The grid has ~70 stations and a
    separate boolean per station, repeated for each segment, dominates the build -- OCC cuts a
    compound of tools in one pass for the same result."""
    from . import knee_lever as _KLM
    xs = [x for x in _MORT_X
          if (x0 is None or x > x0) and (x1 is None or x < x1)]
    if not xs:
        return None
    return cq.Workplane(obj=cq.Compound.makeCompound(
        [s for x in xs for y0, y1 in mort_segments(x)
         for s in _KLM.rib_mortise(x, y0, y1).val().Solids()]))


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
    # THE BOTTOM IS ONE PRISM (user, 2026-09-15), XBAR tall, rail to rail, instead of a comb of
    # cross-ribs with air between them. The mortises cut below take most of it back out, so it
    # costs little; what it buys is a lever mounting place every 8.8 instead of every 22.35, and
    # a continuous CAP over every slot -- the body sealed from underneath against escaping light
    # and motor noise. It is also self-supporting by construction: a bay wall no longer bridges
    # a rib gap, because there are no rib gaps.
    # (THE BOTTOM is not drawn here any more -- each SEGMENT draws its own, identically, at
    #  the top of the segment pipeline. See _bottom() and _segments.)
    # knee/pedal lever mounts: cut a christmas-tree mortise into EVERY rib (so a lever can mount in
    # any bay -- its two tenons drop into the two ribs flanking the chosen bay). Even rib pitch -> the
    # one tenon fits all. (Retention is a set screw that presses the rib ledge -- no per-bay pilot.)
    from . import knee_lever as _KL
    # IT IS THE TENONS THAT MUST LAND ON STATIONS, not the lever's origin (user, 2026-09-18).
    # That used to be the same statement -- the tenon set started at the axle, so posing the
    # axle on a station put every tenon on one. It no longer is: the set is anchored on the
    # housing's -X edge now, so it carries a phase and MOUNT_X is deliberately off-station by
    # exactly that much. Assert what actually matters, and assert it for EVERY tenon rather
    # than for one datum that used to stand in for them. knee_lever cannot check this itself
    # (chassis imports it, not the other way), so it lives here, where both are in scope:
    # change the grid pitch and this fires instead of silently burying tenons in solid floor
    # (3021 mm^3, found the hard way).
    _off = [round(_KL.MOUNT_X + _t, 3) for _t in _KL.TEN_X
            if not any(abs(_rx - (_KL.MOUNT_X + _t)) < 1e-6 for _rx in _MORT_X)]
    assert not _off, (
        "knee_lever tenons at %s are not on mortise stations (MOUNT_X %.2f, phase %.2f). The "
        "grid is at %s -- the pose has to hand the tenon phase back." % (
            _off, _KL.MOUNT_X, _KL.TEN_X[0],
            [round(r, 2) for r in _MORT_X if abs(r - _KL.MOUNT_X) < 40]))
    # THE SEAM TENON MUST CLEAR THE GRID. It is the only material half of the seam joint, and
    # it used to stand from the bed straight through the mortise band -- which is why the two
    # stations flanking each seam had to be dropped. Keyed to the real solids so that a later
    # change to either datum fails here instead of quietly eating a tenon root.
    _cap = MB.FLOOR_TOP - _KL.rib_mortise(_MORT_X[0]).val().BoundingBox().zmax
    assert _cap >= D.MIN_WALL_2P - 1e-9, (
        "only %.2f of cap over the lever mortises -- the bottom prism (D.BOTTOM_T %.1f) has to "
        "carry two beads over the joint, and the joint is already at its own floor"
        % (_cap, D.BOTTOM_T))
    _tz = _seg_tenon(SPLIT_X[0], Y_LO).val().BoundingBox().zmin
    _mz = _KL.rib_mortise(_MORT_X[0]).val().BoundingBox().zmax
    assert _tz >= _mz - 1e-6, (
        "the seam tenon starts at z %.2f, inside the lever mortises' band (they reach %.2f) -- "
        "it would be notched by every station it crosses" % (_tz, _mz))
    _mc = _mort_cutters()
    if _mc is not None:
        body = body.cut(_mc)
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
    # (the electronics-tray drop-in channels are gone: the tray stands against the
    #  keyhead endplate now, and its retention waits on bronner's endplate round)
    # (The AFE BOSS that stood here is gone with the AFE itself, 2026-09-14:
    #  the bypass relay and the magnetic buffer moved onto the optical pickup
    #  board, which sits 10 mm from the audio connector they feed rather than
    #  110 mm from the pickup they were supposed to be buffering.)
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
    for _n in _floor_negatives():
        body = body.cut(_n)
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
    # (in the endplate) is the flush hard stop. There is NO screw down the rail web
    # any more (user): the leg's one screw is the endplate's lock pin across the
    # end-wall tongue, which also locks the endplate to the chassis. It ENDS here: its
    # heat-set insert sits in the kept shell (legs.lock_pin_joint), the hole stopping
    # short of the middle ridge's groove. The chassis prints Z-up, so cadkit teardrops it.
    from .legs import corner_groove_negatives as _cgn, lock_pin_joint as _lpj
    _xc_mid = sum(LEG_STATIONS_X) / 2
    for _sx in LEG_STATIONS_X:
        _egx = -1.0 if _xc_mid > _sx else 1.0       # outboard x sign
        for _s in (1, -1):
            _lc = LEG_Y[0] if _s > 0 else LEG_Y[1]  # flush leg centreline
            # THESE DO NOT REACH THE FLOOR ANY MORE (user, 2026-09-16). They are still cut
            # here because the leg's ridges cross the RAIL BAND and the kept +X shell, where
            # there is no grid to ride and this is the only joinery there is -- dropping them
            # outright drives 0.65-3.2 cm3 of every adapter into the body. What they can no
            # longer touch is the FLOOR: each segment lays that down fresh after this and cuts
            # only the grid out of it, so the leg cannot shape the grid even by accident. The
            # ridges that run in the floor take grid stations instead (leg_stack.body_adapter).
            for _n in _cgn(_sx, _lc, float(_s), _egx, Z_BOT):
                body = body.cut(_n)
            body = body.cut(_lpj(_sx, _lc, _egx, float(_s), Z_BOT).cutter((0.0, 0.0, 1.0)))
    # (the old y-33 / z-70.6 Ø7 harness window is GONE — the wired corner's pigtail now rides
    # the raceway lane at y 50.5, cut with the floor's own negatives. The wide corner ribs that
    # comment used to refer to are gone with the whole rib comb -- the bottom is one solid prism
    # now, so there is MORE material under the feet than there was, not less.)
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
from . import nut_block as _NB                # nut_block imports dimensions + motor_bank only: no cycle
KH_EP_THK     = _NB.KEYHEAD_W  # keyhead endplate thickness in X (= keyhead_endplate.T_EP),
                               # DERIVED from its stow bores (user). The -X legs, their shells
                               # and dovetails below all follow it by the flush-X rule.
EP_LEG_CLR    = EP_TOP_CLR    # assembly clearance: endplate foot pocket vs the kept shell
                              # (= the top-joint clearance -- ONE value for both L joints)
EP_LEG_BUFFER = D.XBAR        # 10 mm solid body between the leg tenon and the endplate wall
EP_TIP_NX = KH_X - KH_EP_THK              # keyhead -X outer face
EP_TIP_PX = D.BRIDGE_BASE_X1              # bridge +X outer tip (8.5) -- the ACTUAL outer face,
                                          # so the leg/shell/wall track it (10 mm wall preserved)


# legs.py owns the leg's SECTION; the chassis owns its PLACEMENT. That split is
# fine, but this used to be a hand-copied 44.0 -- and when SQ_W moved 44.0 -> 44.8
# (odd -> even bead count) the copy went stale silently: `station` below puts the
# leg LEG_W/2 inboard of the endplate tip to make its outer face FLUSH, so a
# too-small LEG_W leaves the real leg standing 0.4 proud of the tip. The overlap
# gate cannot catch it -- leg_body_stub<->chassis is an allowlisted designed
# contact, so it is blind to that pair forever. Import the real value instead.
from .legs import SQ_W as LEG_W
from .legs import STUB_TEN_W as LEG_TEN_W
from .legs import SHELL_GAP as _SHELL_GAP
assert abs(_SHELL_GAP - EP_LEG_CLR) < 1e-9, (
    "legs.SHELL_GAP must equal EP_LEG_CLR: the endplate's foot pocket sits a clearance "
    "outboard of the kept shell")
# (the tongue-rebate assert went with the tongue -- the leg screw's insert is in the ENDPLATE
#  now, so nothing of the leg's reaches across that gap into the kept shell.)


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
assert (abs(_SHELL_NX - D.bottom_span()[0]) < 1e-9
        and abs(_SHELL_PX - D.bottom_span()[1]) < 1e-9), (
    "dimensions lays the floor grid against %.3f..%.3f but the chassis' own shell faces are "
    "%.3f..%.3f -- the floor is drawn to the second pair, so the grid would not reach its ends"
    % (D.bottom_span()[0], D.bottom_span()[1], _SHELL_NX, _SHELL_PX))
LEG_SHELL_NX = (_SHELL_NX, KH_RAIL_X)       # -X leg: -625.6 .. -610.6 (reaches the rail end)
LEG_SHELL_PX = (TP_EP_GX, _SHELL_PX)        # +X leg: -17.5 .. 5.6
# leg stations: (+X leg, -X leg) — outer faces ON the endplate tips (flush X):
LEG_STATIONS_X = (_STN_PX, _STN_NX)         # (-13.4, -614.2)
# Trim the rib comb against the leg BODY STUBS (SQ_W-sq at each station): a comb rib
# whose footprint collides with a stub is redundant -- the stub + its endplate are the
# corner cross-tie there -- and it merges into the stub as a clipped nub while its lever
# mortise would gouge the stub. Drop those (deferred to here: the stations resolve after
# _rib_positions). A rib within (SQ_W + rib_w)/2 of a station touches its stub.
# (the grid runs unbroken past the leg stubs now -- see _mort_positions and the bottom prism)
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


def _seg_relief(s, yr, dz=0.0):
    """The 45 deg wedge under the seam joint, at split X=s and rail Y=yr -- ONE definition, cut
    from BOTH halves so they cannot drift apart (user, 2026-09-17: the tenon had the 45 and the
    mortise did not).

    The TENON needs it: it stands on the bottom prism's top face, so everything it projects past
    the seam plane hangs over the NEIGHBOUR's floor, and flat that underside was a 5.63-deep
    bridge over air. The MORTISE takes the same wedge lowered by _SEG_RELIEF_CLR -- which gives
    the cavity's ramp a clearance gap under the tenon's instead of a coincident face to bottom
    out on, and hands the +X segment back the material its cavity was taking below a tenon that
    is no longer there. Same `reach`, same angle, same line of code: change one and both move."""
    reach = _SEG_JX1
    return (cq.Workplane("XZ")
            .polyline([(s, _SEG_JZ0), (s + reach, _SEG_JZ0), (s + reach, _SEG_JZ0 + reach)])
            .close().extrude(T + 4.0)
            .translate((0.0, yr + (T + 4.0) / 2.0, dz)))


def _relieved(solid, s, yr, dz, what):
    """`solid` minus the seam relief, with proof it bit. A wedge that misses is a SILENT no-op:
    the overhang (or the surplus cavity) would still be there and nothing downstream would
    notice, so make the cut prove it took the corner it was aimed at."""
    out = solid.cut(_seg_relief(s, yr, dz))
    assert out.val().Volume() < solid.val().Volume() - 1.0, (
        "the 45 deg relief took %.2f mm3 off the seam %s at x %.2f -- it is missing the corner"
        % (solid.val().Volume() - out.val().Volume(), what, s))
    return out


def _seg_tenon(s, yr):
    """The −X segment's half of the seam joint at split X=s, rail Y=yr: a plan-plane
    T prism standing from the BOTTOM PRISM'S TOP FACE up to the deck-groove floor (see
    _SEG_JZ0 -- below that is the lever-mortise grid, and this may not stand in it). (The bridge/keyhead END
    joints are a different site — they use the low _br_tongue/_kh_tongue dovetails.)"""
    # the 45 deg underside is _seg_relief -- self-supporting back to this segment's own floor,
    # at a cost to the head of its bottom 5.63 of engagement out of 65.35
    return _relieved(_SEG_J.tenon(root=_SEG_ROOT).translate((s, yr, _SEG_JZ0)),
                     s, yr, 0.0, "tenon")


def _seg_mortise(s, yr):
    """The +X segment's cavity: open at the TOP through the rail crown, where the tenon comes
    in, and closed 0.4 into the bottom prism's top face (_SEG_MZ0). No ceiling to bridge; its
    only horizontal face is a floor.

    IT USED TO RUN CLEAN THROUGH THE BOTTOM PRISM as a second, narrower cavity (drop=0, the
    tenon's bare footprint) -- the path the +X segment's own floor needed to pass the standing
    tenon while being lowered on. That band IS the lever-mortise grid, so every mm of it came
    out of a 3.2 wall between two slots, and the user caught it collided with them. Reversing
    which segment goes down last deleted the need for it outright (see the SEGMENT JOINT block):
    nothing sweeps the floor any more, so the cavity stops at the floor."""
    cav = _SEG_J.mortise(drop=_SEG_ROOT + 1.0,
                         length=(TP_GZ0 + 2.0) - _SEG_MZ0).translate((s, yr, _SEG_MZ0))
    return _relieved(cav, s, yr, -_SEG_RELIEF_CLR, "cavity")


def _end_dt(x_face, into, yc, z0, z1, socket=False, top_clr=TP_TG_DEPTH):
    """ONE endplate<->body joint on an end-contact face at x=x_face, running z0..z1 in Z
    (the install axis) and centred on Y=yc. `into` (+1/-1) points from the face toward the
    endplate's interior -- the direction the joint's DEPTH runs. The body carries the tenon;
    the endplate cuts the socket (socket=True).

    THE SHAPE IS CADKIT'S, not ours (see the _EP_J block): a mushroom, because the endplate
    prints from its deep end toward this face. All this function does is place it -- the
    library authors the profile in its own frame (width across local Y, depth along local Z,
    extruded along local X = the install axis), so the placement is a rotation:

        local +X (install)  ->  world +Z     the endplate drops on
        local +Z (depth)    ->  world `into` * X
        local  Y (width)    ->  world Y      (the profile is symmetric, so its sign is free --
                                              which is what lets one rotation serve both ends)

    `top_clr` raises the SOCKET's far end past the tenon's so the tenon seats on its real stop
    (the L-foot on the shell) and not on the cavity's end -- unchanged in meaning, and still the
    only asymmetry between the two halves."""
    L = (z1 - z0) + (top_clr if socket else 0.0)
    half = (_EP_J.mortise(drop=EP_J_ROOT + 1.0, length=L) if socket
            else _EP_J.tenon(root=EP_J_ROOT, length=L))
    half = half.rotate((0, 0, 0), (0, 1, 0), -90.0)      # +x -> +z, +z -> -x
    if into > 0:
        half = half.rotate((0, 0, 0), (0, 0, 1), 180.0)  # ...and -x -> +x at the bridge end
    return half.translate((x_face, yc, z0))


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


# A DOWNWARD LIGHT WINDOW (user, 2026-09-15/16). The sealed bottom is what holds the motor
# noise in; this is the one deliberate leak, and it aims DOWN at the pedals. It is a window
# THROUGH THE BOTTOM PRISM -- full XBAR of it, so light passes straight out the bed face -- set
# one XBAR inboard of the +Y rail's centre, which leaves 1.2 of opaque body between it and the
# rail's inner face. That inset is the point: the rail stands outboard of it, so nothing of the
# window is visible from the front. (It was first built as an 8 mm band ON the rail's underside,
# which read as a lit stripe along the flank -- wrong on both counts.)
LIGHT_BAND_W  = D.LIGHT_WIN_W
LIGHT_BAND_DY = D.LIGHT_WIN_DY
assert abs((Y_HI - LIGHT_BAND_DY) - D.LIGHT_WIN_YC) < 1e-9, (
    "dimensions spells the +Y rail one way (LIGHT_WIN_YC %.3f) and chassis another "
    "(Y_HI - DY = %.3f) -- knee_lever reads the first to stop its mortises at the window"
    % (D.LIGHT_WIN_YC, Y_HI - LIGHT_BAND_DY))


# (NO TIES. The window used to be interrupted every few stations, because cut clean through
#  for the whole length it leaves the +Y rail as a separate solid in the OPAQUE half -- nothing
#  above the bottom reaches that far +Y. That only mattered while I read the opaque half as the
#  part: it is one fused print in two filaments (user), so the transparent material is what
#  holds the rail, and the window runs unbroken end to end.)


def _light_band():
    """The window's own volume: a run down the bottom, broken by ties. Intersected with a
    segment it gives that segment's transparent piece; cut from it, the aperture it fills."""
    # BETWEEN THE LEGS, FLUSH WITH WHERE EACH FOOT STARTS (user, 2026-09-17). It ran the
    # bottom's whole span, and the -X +Y leg stub stood in that band -- 284 mm3 of transparent
    # material inside the adapter. The legs were there first, so the window gives way, and it
    # gives way exactly as far as the foot reaches and no further.
    x0 = min(LEG_STATIONS_X) + LEG_W / 2
    x1 = max(LEG_STATIONS_X) - LEG_W / 2
    x0, x1 = max(x0, _SHELL_NX), min(x1, _SHELL_PX)
    return box_at(x1 - x0, LIGHT_BAND_W, D.BOTTOM_T,
                  x=(x0 + x1) / 2, y=Y_HI - LIGHT_BAND_DY,
                  z=(Z_BOT + MB.FLOOR_TOP) / 2)


def _floor_negatives():
    """The chassis' OWN features that pass through the floor band, as a list of cutters.

    Factored out because each segment lays its floor down fresh (see _bottom): anything cut into
    that band earlier would otherwise be filled straight back in. These are the chassis' own --
    the +Y wire raceway and the keyhead height screws' head cavities. NOT the leg's grooves:
    those are the coupling the user asked to remove, and the leg fits the grid instead."""
    from .legs import lock_pin_joint as _lpj_f
    out = [_raceway(50.5, -67.0, -604.75, 31.5)]
    # THE LEG LOCK PINS. A fastener has to pass through whatever it passes through, and this one
    # crosses the floor band -- cut in the main builder it was filled straight back in by the
    # fresh slab, burying 45-65 mm3 of every insert and screw in solid body.
    _xc = sum(LEG_STATIONS_X) / 2
    for _sx in LEG_STATIONS_X:
        _egx = -1.0 if _xc > _sx else 1.0
        for _s in (1, -1):
            _lc = LEG_Y[0] if _s > 0 else LEG_Y[1]
            out.append(_lpj_f(_sx, _lc, _egx, float(_s), Z_BOT).cutter((0.0, 0.0, 1.0)))
    # HEAD CAVITIES FOR THE KEYHEAD'S INSERT HEIGHT SCREWS (bronner prototype, user's height
    # adjust). Their heat-sets sit flush in the keyhead's bottom face just over the floor, so the
    # button heads hang down INTO it and the 2.5 mm key comes up to them from below. Placed from
    # nut_block's own height_screw_xy so they cannot drift off their screws.
    for _hi in range(D.N_STRINGS):
        _hx, _hy = _NB.height_screw_xy(_hi)
        out.append(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            _NB.HS_HEAD_CAV_D / 2.0, (MB.FLOOR_TOP - Z_BOT) + 2.0,
            cq.Vector(D.NUT_BLOCK_X + _hx, _hy, Z_BOT - 1.0), cq.Vector(0, 0, 1))))
    return out


def _bottom(a, b):
    """ONE segment's floor: a plain solid block, rail to rail, bed to FLOOR_TOP, over whatever
    of the bottom's span this segment holds. Every segment gets the same thing by the same code
    (user, 2026-09-16), and the lever mortises are cut out of it afterwards.

    Drawn per segment and EARLY in the pipeline on purpose. Drawn once in _build_full it picked
    up whatever anything else had already carved out of that band -- the leg corner grooves took
    7-8.6 cm3 a corner out of it, 86% of that inside the grid's own band. A segment that lays its
    floor down fresh, then cuts only the grid out of it, cannot inherit that."""
    x0, x1 = max(_SHELL_NX, min(a, b)), min(_SHELL_PX, max(a, b))
    if x1 - x0 < 0.1:
        return None
    return box_at(x1 - x0, Y_HI - Y_LO, MB.FLOOR_TOP - Z_BOT,
                  x=(x0 + x1) / 2, y=(Y_HI + Y_LO) / 2, z=(MB.FLOOR_TOP + Z_BOT) / 2)


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
    keep = max(sols, key=lambda s: s.Volume())
    # WHAT IT DROPS, IT MUST BE ALLOWED TO DROP. This exists to bin the scraps a cut strands --
    # a sliver of side wall over the corridor, a nub past a seam. It is not a licence to delete
    # a PART: a corridor that reached under the -Y rail cut that whole rail loose, and this
    # threw it away in silence, which is how the instrument lost a side wall in both tabs
    # without one check going red (user spotted it by eye, 2026-09-15).
    lost = [s for s in sols if s is not keep]
    _v = sum(s.Volume() for s in lost)
    # 5 cm3 is the line between the two: the -Y rail was ~190, and the largest honest scrap
    # here is the 1.2 cm3 strip the keyhead's rail top leaves above Z_TOP at x -611..-607.
    assert _v < 5000.0, (
        "_largest would drop %.1f cm3 in %d piece(s) -- that is a part coming loose, not a "
        "scrap. Bounding boxes: %s" % (
            _v / 1000.0, len(lost),
            [tuple(round(v, 1) for v in (s.BoundingBox().xmin, s.BoundingBox().xmax,
                                         s.BoundingBox().ymin, s.BoundingBox().ymax,
                                         s.BoundingBox().zmin, s.BoundingBox().zmax))
             for s in lost]))
    return cq.Workplane("XY").add(keep)


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
        _flr = _bottom(a, b)                          # this segment's floor, laid fresh...
        if _flr is not None:
            seg = seg.union(_flr)
            for _fn in _floor_negatives():            # ...and the chassis' own way through it
                seg = seg.cut(_fn)
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
        # EVERY motor's lift path, out of EVERYTHING fused above: a bay claims the whole gap on
        # each side (one 1.6 wall between two motors, not two 0.8 halves), so it reaches across
        # into its neighbour's fit and only this cut takes it back out. It is also what keeps
        # every motor's way IN clear, whatever gets built over the bank.
        for _mi in range(D.N_STRINGS):
            seg = seg.cut(MB.lift_prism(_mi))
            seg = seg.cut(MB.tee_pocket(_mi))     # ...and its tee board's, which reaches into
                                                  # the neighbouring bay (40 board, 42.3 motor)
        # THE HARNESS CORRIDOR is the wiring's, the whole length of the bank: the trunk rides it
        # at MB.HARNESS_Y1 and DIPS OUTBOARD into the rail notch behind the +X-most motor, so
        # there is nowhere down here a bay may reach the rail. What survives is the part of each
        # bay's back wall ABOVE the corridor, and it gets a 45 deg underside so it is a wedge off
        # what is left rather than a shelf hanging over the wiring.
        # IT STOPS AT THE RAIL'S INNER FACE. Taking it out to Y_LO - 20 (outside the
        # instrument) meant this cut swallowed the -Y rail's bottom 41.75 mm along the whole
        # body -- the missing side wall the user saw in both tabs. The corridor is the lane
        # INBOARD of the rail; the rail is the wall that closes it, and the only thing allowed
        # to reach into it is the m9 notch, which is bounded on its own.
        # IT STOPS AT THE RAIL'S INNER FACE, AND ON TOP OF THE BOTTOM. Taken out to Y_LO - 20
        # and down to Z_BOT - 10 it swallowed the -Y rail's own section and, worse, the strip of
        # BOTTOM that ties that rail to the rest of the body -- so the rail came out of the cut
        # as a separate solid and _largest threw it away. That is the missing side wall the user
        # saw in both tabs. The corridor is a lane INBOARD of the rail and ABOVE the bottom: the
        # trunk rides it at HARNESS_Z1, nothing needs the 30 mm below FLOOR_TOP, and leaving the
        # bottom whole is the whole point of sealing it.
        _cy0 = Y_LO + T / 2.0
        seg = seg.cut(box_at((a - b) + 40.0, MB.HARNESS_Y1 - _cy0,
                             MB.HARNESS_Z1 - MB.FLOOR_TOP,
                             x=(a + b) / 2, y=(_cy0 + MB.HARNESS_Y1) / 2,
                             z=(MB.FLOOR_TOP + MB.HARNESS_Z1) / 2))
        # RISE PAST THE PRISM'S TOP, not past the seat plane. The wedge is a triangle, so its
        # own top edge is FLAT: anything the bay puts above that edge survives with a flat
        # underside. Sized to Z_HI it topped out at -27.25 and left 1.8 of each side wall
        # hanging there -- two 7.6 mm2 ceilings on string 10's bay, which the user spotted.
        # ...and ACROSS THE M9 NOTCH it reaches back to the notch's own face. The notch takes
        # 4 mm off the rail's inner face for the trunk's outboard dip, and string 10's bay back
        # wall reaches 1.2 past that face -- so with the rail gone there, that 1.2 stood alone
        # between the notch void and the corridor void. One sliver per probe line, six of them.
        _nx0, _nx1 = max(M9_CUT_X0, b - 20.0), min(M9_CUT_X1, a + 20.0)
        if _nx1 - _nx0 > 0.1:
            seg = seg.cut(box_at(_nx1 - _nx0, _cy0 - M9_CUT_YBACK,
                                 MB.HARNESS_Z1 - MB.FLOOR_TOP,
                                 x=(_nx0 + _nx1) / 2, y=(M9_CUT_YBACK + _cy0) / 2,
                                 z=(MB.FLOOR_TOP + MB.HARNESS_Z1) / 2))
        # THE 45 DEG UNDERSIDE on whatever stands over the corridor. It is bounded by the VOID
        # IT RELIEVES: a bare triangle running -Y from HARNESS_Y1 used to reach 15.55 past it,
        # which was harmless while the -Y rail was (wrongly) missing and became a 2035 mm2 flat
        # ceiling on the rail's inner face the moment the rail came back. It now stops at the
        # void's own -Y face -- the rail inside, the notch's back face across the notch.
        def _relief(yb, x0, x1):
            # the wedge sitting ON the channel's ceiling, so what is left IS the 45 deg ramp:
            # from a knife edge at the HARNESS_Y1 wall up to (yb, +(HARNESS_Y1 - yb)). Cutting
            # the other side of that line -- everything ABOVE the ramp -- is what the old
            # triangle did, and it leaves the flat ceiling in place with a wedge resting on it.
            _prof = [(MB.HARNESS_Y1, MB.HARNESS_Z1), (yb, MB.HARNESS_Z1),
                     (yb, MB.HARNESS_Z1 + (MB.HARNESS_Y1 - yb))]
            return (cq.Workplane("YZ").workplane(offset=x0)
                    .polyline(_prof).close().extrude(x1 - x0))

        seg = seg.cut(_relief(_cy0, b - 20.0, a + 20.0))
        if _nx1 - _nx0 > 0.1:
            seg = seg.cut(_relief(M9_CUT_YBACK, _nx0, _nx1))
        # THE LEVER MORTISES, RE-CUT AFTER THE BAYS (user, 2026-09-15). _build_full cuts a
        # christmas-tree into every rib, but the housings fuse in above it -- and each faceplate
        # wall runs all the way down to the BED, so it crosses the ribs and fills those mortises
        # straight back in. The documented refill trap: a feature cut before a union does not
        # survive the union. Same remedy as the tee anchors in build.py -- re-cut afterwards,
        # for the ribs this segment actually holds.
        _segmc = _mort_cutters(b - 30.0, a + 30.0)
        if _segmc is not None:
            seg = seg.cut(_segmc)
        segs.append(_largest(seg))
    return segs


def _split_light(segs):
    """(opaque, transparent) for each segment. Same origin, printed as ONE object in two
    filaments -- the deck panels' base/colour pattern (build.py registers them as a pair).

    Each band is clipped to its OWN segment's X span. _seg_box deliberately overshoots its
    neighbour by 0.02 so the halves of a seam joint meet; inherited by the band that reads as
    two transparent parts interpenetrating (1.1 mm3 a seam, which the gate duly reported)."""
    edges = [_SHELL_PX + KH_DT_DEPTH + 2.0] + sorted(SPLIT_X, reverse=True) + [X_NUT]
    out = []
    for i, s in enumerate(segs):
        a, b = edges[i], edges[i + 1]
        band = _light_band().intersect(
            box_at(a - b, LIGHT_BAND_W + 2.0, D.BOTTOM_T + 2.0,
                   x=(a + b) / 2, y=Y_HI - LIGHT_BAND_DY,
                   z=(Z_BOT + MB.FLOOR_TOP) / 2))
        out.append((s.cut(_light_band()), s.intersect(band)))
    return out


_seg_pairs = _split_light(_segments())
segments       = [s for s, _ in _seg_pairs]
segments_light = [c for _, c in _seg_pairs]
# CONNECTIVITY IS TESTED ON THE PRINTED OBJECT, not on the opaque half. The two filaments fuse
# into one solid part, so the opaque half may legitimately come out in pieces wherever the
# window runs between them -- what must never come apart is the union. (Reading the opaque half
# as the part is what had me tying the window every few stations to keep the +Y rail attached.)
for _i, (_op, _lt) in enumerate(_seg_pairs):
    _n = _op.union(_lt).solids().size()
    assert _n == 1, (
        "chassis segment %d prints as %d separate solids -- something has come loose "
        "(the opaque half alone may be in pieces; the fused part may not)" % (_i, _n))

BED_X = 255.0                          # the printer's X, the reason the chassis is in pieces
for _si, _seg in enumerate(segments):
    _sl = _seg.val().BoundingBox().xlen
    assert _sl <= BED_X + 1e-6, (
        "chassis segment %d is %.1f long, over the %.0f bed -- move SPLIT_X (remember each "
        "segment carries its end motors' housings, 31.15 past the motor)" % (_si, _sl, BED_X))
