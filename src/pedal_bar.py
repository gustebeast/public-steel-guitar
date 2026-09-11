"""Pedal bar — spans the two +Y legs at ankle height, carrying their last
piece as FUSED STUB TOWERS.

The bar is the mounting rail for the (future) sensor pedals. Each end
carries a 44-sq STUB TOWER printed WITH the bar: the shortened +Y leg
shafts press DOWN onto the towers' octagon spigots — the leg↔body joint,
verbatim — and the wired (-X) tower adds the second
vertical TRRS blind-mate: its captive CA-354S plug (threaded up through
the foot-mortise access) points UP into the 10-03404 jack in the shaft,
on the TRRS axis at station +5. Pedal height is constant regardless of
instrument height, and stomp loads go floor-direct through the bar's
feet, never through the joint.

NO Z RETENTION (user): the seatbelt quick-release this joint shared with the
leg↔body one — wedging bolt + recessed button on the tower, bearing ledge in
the leg block — is GONE from both. The spigot still fixes X, Y and rotation
and takes the load; nothing holds the bar down onto the legs, so they part as
easily as they went together. Deliberate: a blank slate to redesign against.

FLUSH 35.6 COLUMN (user, symmetry round: match the leg shafts): the bar
prism is BLK_W wide (Y = YC ± 17.8) and 19 tall, and its END faces sit
at station ± 17.8 — flush with the slimmed towers and the 35.6 leg
blocks above, so each +Y stack reads as ONE clean 35.6-sq column from
block top to bar bottom, all at the legs' 4.2 inset. Only the shared
TPU feet stay 44 (proud ground boots, like under the -Y blocks). The
feet are the shared legs.leg_foot dovetail inserts (mortise opens at
the bar's -Y face).

PRINTS -Y -> +Y (user). The bar used to build bottom-up with its lid on
the +Z face; it now lies on its -Y face so that the fused foot-pedal
housings sit AT THE BED in the very orientation the knee lever already
prints in — same bed plane, no reorientation, and the pedal ends up on
the bar's -Y surface, closest to the player. Two things follow from the
flip and neither is a rotation:

  * THE LID MOVED TO THE +Y FACE, the top of the print. That is what
    makes the wiring trough ceiling-free — it opens skyward, so there is
    nothing to bridge. But the +Y face spans Z where the +Z face spanned
    Y, and the dovetail's 23.8 foot did not fit the old 19-tall bar; see
    dimensions.PEDAL_BAR_H, which now sizes BAR_H at 27.0 from the lid.

  * THE SPLICE INSTALL AXIS FOLLOWED, because it was never world Z — it
    was the PRINT axis, which is now world Y (see SPLICE_J).

A WIRING TROUGH runs between the towers under a full-length sliding-
DOVETAIL LID — no screws: the lid pieces slide in from the -X end (user),
which is the WIRED tower's end, so the open mouth doubles as the access
you thread the leg wiring through before closing the bar up. A TPU detent
nub in the groove floor clicks into lid A's underside dimple, setting the
position and locking the stack (A butts B). The wired tower's
cable enters from the trough through a Ø8 side way and rises to the plug
seat. The trough is deliberately shorter in Z than the dovetail's foot,
leaving groove floor for that nub — but not so short that it stops
clearing the splice mortises, which open through it.

SEGMENTED FOR THE 255×255 BED: FLUSH-X grew the bar to the full
instrument span (644.8) — THREE ~215 pieces now, each lying on its -Y
face (220.6×89, 212.3×27, 215.0×89, all 35.6 tall in the build axis), and
two ~278 lid pieces (butt splice at XL, mid-span, so each lid piece
BRIDGES one bar joint).

NO GLUE, and NO fastener either: the splice joints take X and Z by shape
and leave Y — the install axis — to the LID. A lid piece spans each
splice, and its foot cannot rise back through either piece's narrower
groove mouth, so neither bar piece can move off the other while the lid
is in. That is what "the lid is structure" already meant; the glue was
only ever belt-and-braces on top of it.

FRAME: modelled at ABSOLUTE X/Y (the legs' real stations, +Y rail); Z is
local with 0 = the plate bottom (build.py translates by ground + FOOT_H).
Drawn SEATED."""

from __future__ import annotations

import math

import cadquery as cq

from cadkit.holes import teardrop_hole
from cadkit.joinery import PrintSpec, joint
from . import dimensions as D
from .helpers import box_at, cyl, cyl_y
from .chassis import LEG_STATIONS_X, LEG_Y
# The redesigned leg owns the SECTION -- profile, fit and engagement all come from
# there, so the mortise in this bar cannot drift from the tenon that enters it.
# Safe to import at module level: leg_stack reaches back for pedal_bar only from
# inside a function (its context poser), so there is no cycle.
from .leg_stack import (ENGAGE as LS_ENGAGE, mortise_cutter as LS_mortise,
                        TEN_W as LS_TEN_W, FIT as LS_FIT,
                        LEG_X as LS_LEG_X, LEG_Y as LS_LEG_Y)
from . import bar_latch as BL
from . import legs as LG
from . import latch as LT
from .legs import _house

YC = LEG_Y[0]                          # FLUSH round: the bar rides the +Y
                                       # legs' centreline, 17 inboard of the
                                       # rail — its outer face continues the
                                       # body wall plane to the floor
# one foot per +Y leg: (leg station, inboard side sign). The side sign is the
# legacy latch-opening direction, kept because the TRRS way still keys off it.
# (Was LATCHES, back when each foot carried a snap/TRRS latch.)
# NO bar-joint latch (user, 2026-08-06). The latch is being taken to a finished
# state on ONE joint only -- the leg-to-body joint at the -X/+Y (TRRS) leg -- so
# the bar simply drops onto its towers with no z-retention, the blank-slate state
# the legs were left in when the old quick-release came out. Set to a FEET index
# to put the mechanism back on that tower.
LATCH_FOOT = None

FEET = ((LEG_STATIONS_X[0], -1.0),     # +X leg → plain tower
        (LEG_STATIONS_X[1], +1.0))     # -X leg → wired (TRRS) tower

BAR_H = D.PEDAL_BAR_H                      # 27.0 — sized by the LID (see below and
                                           # dimensions.PEDAL_BAR_H). Shared with
                                           # legs.py, which needs the same number to
                                           # keep all four wide sections equal.
BAR_Y0 = YC - LG.BLK_W / 2                 # BLK_W (35.6) wide — matches
BAR_Y1 = YC + LG.BLK_W / 2                 # the slimmed towers/blocks: the
                                           # +Y stacks are FLUSH columns at
                                           # the legs' 4.2 inset (user)
# TOWER_W lives up here because the bar's END FACES are derived from it -- see
# _mortise_tower for what sets the number.
TOWER_W = 64 * D.BEAD                      # 51.2 across flats. Chosen so the corner
                                           # room clears the latch stack: half-diagonal
                                           # 36.2 minus the tenon's 12.3 flat = 23.9
                                           # against the 22.4 needed, 1.5 spare. 49.6
                                           # also fits, at 0.37 -- not margin on a
                                           # mechanism that is not designed yet.

# END MARGIN IS PER END, because the two towers are no longer the same size. The
# rule has not changed -- "the bar's end face is flush with the tower's" -- but the
# -X station now carries the 51.2 MORTISE tower while +X still has the 36.4 spigot.
# Sharing one margin silently AMPUTATED the wide tower: the piece clip runs at
# BAR_X0 - 1, so 7.4 of tower was sliced off, taking the wall of the TRRS bore with
# it (the bore ran -639.7..-628.5 against a piece starting at -638.4). Nothing
# failed; the part just came out with a hole in its end face.
END_MARGIN = LG.BLK_W / 2                  # +X end: the spigot tower's face
END_MARGIN_X0 = TOWER_W / 2                # -X end: the mortise tower is wider
BAR_X0 = LEG_STATIONS_X[1] - END_MARGIN_X0
BAR_X1 = LEG_STATIONS_X[0] + END_MARGIN


STUB_Z0 = LG.BAR_STUB_Z0                   # 51.0 — tower seat plane (bar frame): the
                                           # leg block's mouth face lands here (bar top
                                           # + the 24 button band). Owned by legs.py so
                                           # SHORT_SHAFT_L can close the level-top loop
                                           # against it; was a hardcoded 43.0.
# Future pedals mount spring carriages vertically (lever pattern) above
# the bar: the legs' WIDE bottom sections must stay below this envelope
# (user placeholder; reference point x -313.80, y 43.75 = the bar top
# plane at z -699.15 global). Budget check: tower top = STUB_Z0 + 38 =
# 81, leg block top = STUB_Z0 + 48 = 91, both <= 19 + 75 = 94.
PEDAL_ASSEMBLY_Z_HEIGHT = 113 * D.NOZZLE_D   # 90.4 (was 75, a placeholder). foot_pedal.py exists
                                   # and its stack measures 85.1 from the bar top: the
                                   # knee lever's cartridge, reused verbatim, is a 42
                                   # free-length coil plus guide post plus back-stop
                                   # screw. Raised to 90 with 4.9 to spare, and
                                   # foot_pedal asserts against this number so the two
                                   # cannot drift apart. NOTE the budget line below no
                                   # longer has slack the way it did — the leg blocks
                                   # (top 91) and the pedal stack (top ~104) now share
                                   # a Z band and only their X separation keeps them
                                   # apart; the overlap gate is what proves it.
FOOT_PAD = 12.0

# ── the LID's face, after the -Y -> +Y print flip ────────────────────────────
# The bar used to build bottom-up (+Z) with the lid on its +Z face; it now builds
# -Y -> +Y so the pedal housings sit AT THE BED, in the orientation the knee lever
# already prints in. The lid therefore moves to the +Y face — the top of the print
# — which is also what makes the trough ceiling-free (it opens skyward, so there is
# nothing to bridge).
#
# The move is a rigid rotation of the profile about X, but it swaps which bar
# dimension the lid has to fit inside: the +Z face spans Y (35.6, roomy), the +Y
# face spans Z. That is why BAR_H had to grow from 19.0 — see D.PEDAL_BAR_H.
LID_T        = 4.0                         # lid plate thickness = groove depth in Y
LID_Y0       = BAR_Y1 - LID_T              # groove floor plane (the lid's inner face)
LID_ZC       = BAR_H / 2.0                 # centred in the face's Z span (the old
                                           # -3.5 bias was the +Z face's trough offset
                                           # and has no meaning on this face)
LID_FOOT_HW  = D.PEDAL_LID_FOOT_W / 2.0    # 11.90 — widest, at the groove floor
LID_RAIL     = D.MIN_WALL_2P               # 1.6 step per side = the rail the dovetail
                                           # hooks; it is printed material, so it is
                                           # held to the 2-bead tier
LID_MOUTH_HW = LID_FOOT_HW - LID_RAIL      # 10.30 — at the face
TROUGH_D     = 19 * D.NOZZLE_D             # 15.2 wiring cavity depth in Y behind the floor
# The trough is deliberately SHORTER in Z than the dovetail's foot, exactly as it
# used to be narrower in Y than the foot was wide. Two things need that leftover
# groove-floor material: the lid-lock detent nub has to be bored into solid, and
# the floor is what the dovetail rails stand on. But it also cannot be too short —
# the splice mortises open through it (that is the tenons' entry path from +Y), so
# every joint has to fall inside this band. It is squeezed from both sides.
TROUGH_HZ    = 16.5                        # cavity height in Z (the proven section)
TROUGH_Z0    = LID_ZC - 1.75 - TROUGH_HZ / 2.0     # 3.50
TROUGH_Z1    = TROUGH_Z0 + TROUGH_HZ               # 20.00

_LID_SKIN = (BAR_H - 2 * LID_FOOT_HW) / 2.0
assert _LID_SKIN >= D.MIN_WALL_2P - 1e-6, (
    f"the lid groove leaves {_LID_SKIN:.2f} of bar above/below it, under the "
    f"{D.MIN_WALL_2P} tier — raise D.PEDAL_BAR_H or narrow the dovetail")
_BACK_WALL = (LID_Y0 - TROUGH_D) - BAR_Y0
assert _BACK_WALL >= D.MIN_WALL_2P, (
    f"the trough leaves a {_BACK_WALL:.2f} back wall on the player side")

# ── SEGMENTATION (255×255 bed) + the full-length sliding-DOVETAIL lid ──
# everything here DERIVES from the leg stations (they are chassis-owned and
# have moved before — never hardcode absolutes against them).
# FLUSH-X: the bar spans the WHOLE instrument (644.8) — past any two-piece
# diagonal — so THREE ~215 pieces, each printing STRAIGHT, joined by cadkit
# install-z joints (the chassis-segment pattern).
# ── PEDAL STATIONS, and the splices DERIVED from them ────────────────────────
# The stations live HERE, not in foot_pedal, because the BAR is what has to be cut
# up and a splice may not land on a pedal. They used to be foot_pedal's, and the
# splices were a flat BAR_X0 + 215 that knew nothing about them — so XS1 fell at
# -417.20, inside the -413.20 pedal's -426.9..-399.5 housing. It cut a pedal in
# half. foot_pedal reads PEDAL_X back from here; the import stays one-way.
PEDAL_PITCH = 78 * D.NOZZLE_D               # 62.4 centre-to-centre, on the nozzle grid
PEDAL_W     = 28.0                          # a pedal's X footprint (the PAD, which is
                                            # marginally wider than its 27.4 housing)
N_PEDALS    = 5
SLOT1_X     = FEET[1][0] + LG.BLK_W / 2.0    # -596.60: slot 1 starts FLUSH WITH THE
                                            # LEFT (keyhead-side) leg and is left EMPTY
                                            # for breathing room; slots 2..6 carry the
                                            # pedals.
                                            #
                                            # "Flush with the leg" means the leg's
                                            # INBOARD FACE, not its centre station. It
                                            # was the station (-614.40), and the test that
                                            # catches it is to put a pedal in slot 1: at
                                            # the station it spans -614.40..-586.40 while
                                            # the tower occupies -632.20..-596.60, so it
                                            # drives 17.8 INTO the leg. Off the face a
                                            # slot-1 pedal butts the tower exactly, which
                                            # is what "flush" has to mean for the empty
                                            # slot to be a real pedal's worth of room.
PEDAL_X     = tuple(SLOT1_X + PEDAL_PITCH * n + PEDAL_W / 2.0
                    for n in range(1, N_PEDALS + 1))

BED = 255.0
_SPLICE_KEEP = (PEDAL_W + 2 * 6.4) / 2.0    # a splice must clear a pedal's centre by
                                            # half its width plus room for the joint

def _clears_pedals(x):
    return all(abs(x - px) >= _SPLICE_KEEP for px in PEDAL_X)

# XS1 goes in a GAP BETWEEN NEIGHBOURING PEDALS; XS2 then halves what is left. Pick
# the gap that minimises the longest piece, so no piece is near the bed by accident.
_best = None
for _i in range(len(PEDAL_X) - 1):
    _g = (PEDAL_X[_i] + PEDAL_X[_i + 1]) / 2.0      # gap midpoint (pitch is uniform)
    _h = (_g + BAR_X1) / 2.0                        # halve the remainder
    if not _clears_pedals(_h):
        continue
    _lens = (_g - BAR_X0, _h - _g, BAR_X1 - _h)
    if _best is None or max(_lens) < max(_best[2]):
        _best = (_g, _h, _lens)
assert _best is not None, "no pedal gap gives a splice pair that clears every pedal"
XS1, XS2, _PIECE_L = _best
assert max(_PIECE_L) <= BED, (
    f"bar pieces {tuple(round(v, 1) for v in _PIECE_L)} — one exceeds the {BED} bed")
for _x, _n in ((XS1, "XS1"), (XS2, "XS2")):
    assert _clears_pedals(_x), (
        f"{_n} at {_x:.2f} lands within {_SPLICE_KEEP:.2f} of a pedal centre "
        f"{PEDAL_X} — a splice may not cut a pedal in half")
XL = (FEET[0][0] + FEET[1][0]) / 2   # lid butt-splice: mid-span,
                   # ~107 from each bar splice so each lid piece BRIDGES
                   # one bar joint — the lid IS the splice's Z lock (the
                   # install axis the joint leaves free), not just a roof
# LID SPAN — END TO END (user round: install runs -X -> +X). The lid used to
# sit BETWEEN the fused towers and slide in from +X. Both ends changed:
#
#   -X  FLUSH with the bar's end face. The groove runs out of it, so that mouth
#       is the lid's entry AND the opening the leg wiring is installed through
#       (the -X tower is the WIRED one — its Ø8 side way feeds the trough).
#   +X  the groove STOPS short, leaving MIN_WALL_2P of bar as an end wall. That
#       1.6 is the whole retention story on this end: the lid cannot slide out
#       the far side, so the nub at the near end pins the stack against it.
LID_END_STOP = D.MIN_WALL_2P                  # 1.6 — the +X end wall (user)
LID_XA = BAR_X0                               # -X: flush, open (wiring access)
LID_XB = BAR_X1 - LID_END_STOP                # +X: hard stop, 1.6 of bar left
TROUGH_X0 = FEET[1][0] + LG.BLK_W / 2 + 0.6   # wiring trough: runs
TROUGH_X1 = FEET[0][0] - LG.BLK_W / 2 - 0.6   # right up to the towers
# End-to-end, the two lid pieces are ~318 each — they no longer fit the bed
# STRAIGHT and never did (they printed diagonally at ~278 already). A part laid on
# the diagonal has BED*sqrt(2) to work with, less its own width.
_LID_L = (XL - LID_XA, LID_XB - XL)
assert max(_LID_L) <= BED * 2 ** 0.5 - D.PEDAL_LID_FOOT_W, (
    f"lid pieces {tuple(round(v, 1) for v in _LID_L)} — one exceeds the "
    f"{BED * 2 ** 0.5 - D.PEDAL_LID_FOOT_W:.1f} diagonal a {D.PEDAL_LID_FOOT_W}-wide "
    f"part gets on the {BED} bed")

LOCK_D = 3.8                       # detent pocket diameter — sized to the groove-floor
                                   # band above the trough, which the assert below holds
                                   # at its exact limit (a 4.0 snap left it 0.1 short)
LOCK_X = LID_XA + 6 * D.NOZZLE_D   # +4.8: the nub FOLLOWED the install flip: it has to
                                   # sit at the OPEN end, because that is the only
                                   # end anything can escape from. Piece B goes in
                                   # first and runs to the +X stop wall; A follows
                                   # and its dimple clicks here, trapping B
LOCK_Z = (TROUGH_Z1 + LID_ZC + LID_FOOT_HW) / 2.0   # 22.70 — centred in the groove
                                   # floor left ABOVE the trough (the wider of the
                                   # two leftover bands)
assert (LID_ZC + LID_FOOT_HW - TROUGH_Z1) >= LOCK_D + 2 * 0.8 - 1e-6, (
    f"only {LID_ZC + LID_FOOT_HW - TROUGH_Z1:.2f} of groove floor above the trough "
    f"for a {LOCK_D} detent pocket")
                                   # lid-lock detent nub: now a pocket in
                                   # the GROOVE FLOOR (the +Y face's inner plane)
                                   # rather than the old bar top; a
                                   # groove+dimple in lid B's underside sets
                                   # the final position, stops over-insert
                                   # and detents extraction (locks BOTH lid
                                   # pieces: B butts A). No screws anywhere.

# ── MORTISE TOWER (the redesigned leg's end of the chain) ───────────────────
# The bar used to present a male SPIGOT and the leg swallowed it. The redesigned
# leg (src.leg_stack) is a chain of through-mortise sleeves joined by FLOATING
# TENONS, so the adjust tenon arrives here as a male -- and the bar has to be the
# female. This is that end, and it is per-station on purpose: leg_stack redesigns
# ONE leg (the -X/+Y TRRS station), so FEET[1] gets the mortise and FEET[0] keeps
# the old spigot until its leg is redone too.
#
# WHAT SETS THE TOWER'S SIZE, because it is NOT the mortise. Three things live in
# this tower and the mortise is the smallest of them:
#
#   mortise    the tenon is 24.0 across flats, 24.6 with the slide fit, used at
#              45 degrees -- so its apex reaches 17.4 and its flats sit 12.3 off
#              the axis.
#   TRRS       a 9.6 jack body needs ~9.6 + walls of clear material.
#   LATCH      src.bar_latch's YOKE: a ring round the tenon in a slot under the
#              mouth, its pad flush in the -Y face and its springs beside the arms.
#              It is sized off the tower's faces (asserted below).
#
# A tower at the leg's own 44.8 gives 5.0 of wall at the face centres -- nowhere
# near it, and this is exactly why the latch's handedness mattered: on a tenon
# the mechanism buries itself in the section, on a mortise it has only the wall.
#
# THE 45 DEGREES IS WHAT PAYS FOR IT. The tenon is rotated, so its FLATS face the
# tower's CORNERS and its apexes face the face centres. The corners are the deep
# direction (half-diagonal, not half-width) AND the direction where the tenon
# presents a flat -- the ideal surface for a hook pocket. The TRRS jack goes in
# a corner (the latch's yoke rings the whole tenon, under the mouth), and the tower only has to be big enough for the
# corner to be deep enough.
TOWER_FLOOR = 4 * D.BEAD           # 3.2 the mortise's blind floor. BLIND, not
                                   # through: this joint is NOT height-adjustable
                                   # (user) -- the floor is the fixed, repeatable
                                   # installation stop the tenon bottoms on. It
                                   # works in compression against the bar prism
                                   # right beneath it.
TOWER_TOP = BAR_H + LS_ENGAGE + TOWER_FLOOR    # 71.1 the MOUTH plane, in bar
                                   # coordinates. This is the datum leg_stack
                                   # poses the bar from -- the tenon's far end
                                   # lands on the floor, so the mouth sits
                                   # ENGAGE above it.
TOWER_CORNER = TOWER_W / 2.0 * math.sqrt(2.0)  # 36.2 axis -> corner
assert BAR_X0 <= FEET[1][0] - TOWER_W / 2 + 1e-9, (
    "the bar's -X end face cuts into the mortise tower")


def _corner(d: float, sx: float, sy: float):
    """A point `d` out along one of the tower's diagonals, where the tenon shows
    a flat and the wall is deepest."""
    return (sx * d / math.sqrt(2.0), sy * d / math.sqrt(2.0))


# The tenon's FLAT, measured off leg_stack's own numbers rather than typed in:
# rotated 45 degrees, the octagon's flats face the corners at half its across-flats.
TEN_FLAT = (LS_TEN_W + 2 * LS_FIT) / 2.0       # 12.30 axis -> tenon flat
TRRS_BORE_D = 14 * D.BEAD          # 11.2 -- the CA-354S body way, the Ø11 the old
                                   # axial route already used, rounded onto the grid
TRRS_CORNER_D = TEN_FLAT + 2 * D.MIN_WALL_2P + TRRS_BORE_D / 2.0
# The way stops a 2-bead web UNDER the latch's slot: the slot's ring spans this
# corner, so the jack sits below it. That web is the roof the jack's shoulder
# presses up against.
TRRS_WAY_TOP = BL.planes(TOWER_TOP)["z_cb"] - D.MIN_WALL_2P
TRRS_CORNER = (-1, -1)             # the -X-Y corner of the tower
BAR_UP = (0.0, 1.0, 0.0)           # the bar prints lying on its -Y face

# THE THINGS THE TOWER MUST HOLD, each asserted against the number that actually
# constrains it, so the tower cannot be quietly shrunk back to the leg's own width.
# The LATCH (src.bar_latch) sized its slot, pad recess and spring pockets off the
# tower's faces, so the faces must be where it assumed.
assert abs(TOWER_W / 2 - BL.FACE_R) < 1e-9, (
    "bar_latch sized the yoke for faces %.1f off the axis; the tower's are %.1f"
    % (BL.FACE_R, TOWER_W / 2))
assert TOWER_CORNER - TRRS_CORNER_D >= TRRS_BORE_D / 2 + D.MIN_WALL_2P, (
    "the TRRS bore breaks out of the tower's corner")
assert TOWER_W / 2 - TRRS_CORNER_D / math.sqrt(2) >= TRRS_BORE_D / 2 + D.MIN_WALL_2P, (
    "the TRRS bore breaks out of the tower's flat face")
# and the mortise itself must not eat the bar underneath it
assert TOWER_TOP - LS_ENGAGE >= BAR_H + D.MIN_WALL_2P, (
    "the blind mortise floor is inside the bar prism")
# The jack way must NOT surface on the mouth -- that face is a mating face, and a
# hole in it is either a blind-mate connector or a mistake. It is a mistake here.
assert TRRS_WAY_TOP <= TOWER_TOP - D.MIN_WALL_2P, (
    "the TRRS way breaks out through the mortise's MOUTH face")
assert TRRS_WAY_TOP - (BAR_H - 1.0) >= 30.0, (
    "the TRRS way is %.1f long; the CA-354S body needs ~31"
    % (TRRS_WAY_TOP - (BAR_H - 1.0)))


def _mortise_tower(lx: float, wired: bool) -> cq.Workplane:
    """The FEMALE tower: a TOWER_W prism carrying a blind octagon mortise that
    the leg's adjust tenon drops into, built in place on the redesigned leg's
    axis (the tenon's mortise cutter comes from leg_stack already positioned).

    Prints WITH the bar, which lies on its -Y face -- and that is what the 45
    buys again: the mortise's roof is two 45-degree flanks rather than a flat
    bridge, so a 40-deep blind pocket needs no support. The one ceiling in it is
    the FLOOR seen from the mouth, and that is a floor, not a ceiling.
    """
    assert (lx, YC) == (LS_LEG_X, LS_LEG_Y), (
        "the mortise tower must stand on the redesigned leg's axis")
    b = box_at(TOWER_W, TOWER_W, TOWER_TOP - BAR_H, x=lx, y=YC,
               z=(BAR_H + TOWER_TOP) / 2)
    # the mortise: ENGAGE deep from the mouth, overshooting the top so the cut
    # opens cleanly, floored TOWER_FLOOR above the bar
    b = b.cut(LS_mortise(TOWER_TOP - LS_ENGAGE, TOWER_TOP + 2.0))
    # the pedal bar's LATCH (src.bar_latch): the yoke's slot under the mouth, the
    # pad's recess in the -Y face and the spring pockets, on this same axis
    b = b.cut(BL.tower_cut(TOWER_TOP))
    if wired:
        # TRRS jack, moved OUT OF THE AXIS. It used to thread up the middle of
        # the spigot -- which is now the mortise, so it goes in a corner.
        #
        # IT DOES NOT REACH THE MOUTH, and that is the point. A bore that opens
        # on the mouth face only earns its keep if the jack BLIND-MATES as the
        # leg seats, the way the old spigot's captive plug did. On this chain it
        # cannot: what enters the mouth is the floating tenon, which is solid and
        # moving. The leg's own TRRS bore is up on the adjust sleeve, so this
        # boundary is a patch cable -- which means the jack wants a closed roof
        # to press up against, not an exit.
        cx, cy = _corner(TRRS_CORNER_D, *TRRS_CORNER)
        # upright in the tower, so SIDEWAYS to the bar's print: via cadkit, a teardrop
        b = b.cut(teardrop_hole(TRRS_BORE_D, TRRS_WAY_TOP - (BAR_H - 1.0),
                                (lx + cx, YC + cy, BAR_H - 1.0), (0.0, 0.0, 1.0), BAR_UP))
    return b


def _stub_tower(lx: float, wired: bool, latch: bool = False) -> cq.Workplane:
    """FUSED stub tower (user: single printed piece — the tenon is part of
    the bar): BLK_W-sq button body (19..43 — slimmed with the leg blocks
    to the 4.2 inset, symmetry round) + octagon spigot (43..81) with the
    no bolt channel or button pocket any more (the quick-release is gone —
    the spigot is a plain sliding fit). Authored at the ORIGIN and ROTATED 180°
    like the +Y leg stacks. The wired tower's captive CA-354S threads UP
    from the foot-mortise access below; its cable enters from the trough
    side way. Prints WITH the bar, bottom-down — plain standing
    geometry, no overhangs."""
    b = box_at(LG.BLK_W, LG.BLK_W, STUB_Z0 - BAR_H, z=(BAR_H + STUB_Z0) / 2)
    # spigot: the flush OCTAGON section tenon (round 3 — the lying leg
    # block's bed face turned the old house floor into a 28-wide ceiling
    # bridge). Constant Z-section: still prints clean standing with the bar.
    b = b.union(LG._section_tenon(39.0).translate((0, 0, STUB_Z0 - 1.0)))
    # COVER round: the leg block is truncated to the slider stem plane
    # (LG.SH_Y — its print-bed fix), so the tenon band above that plane is
    # SHAVED, INCLUDING the 1-embed slab below the seat plane (the slim
    # BLK_W body no longer buries it — it poked out as a 1-tall fin): the
    # truncated tenon lands FLUSH with the block's thinned face
    # (waist-vs-slit capture untouched)
    b = b.cut(box_at(LG.SQ_W + 2.0, 6.0, 42.0, y=LG.SH_Y + 3.0,
                     z=STUB_Z0 + 19.0))
    # LATCH (male half), butt plane at STUB_Z0. The tower is already BLK_W wide,
    # i.e. the face the mechanism is datumed to, so it needs no finger well — the
    # 44-wide leg head gets one instead to match. The button lands on the BAR,
    # facing outboard: the piece you lift off (user).
    if latch:
        b = b.cut(LT.male_cutter(cx=LT.LX_TOWER).translate((0, 0, STUB_Z0)))
        b = b.union(LT.male_post(cx=LT.LX_TOWER).translate((0, 0, STUB_Z0)))
    b = b.rotate((0, 0, 0), (0, 0, 1), 180).translate((lx, YC, 0))
    return b
# Print-orientation note: the tower's octagon spigot has a constant Z section, so
# with the bar now lying on its -Y face the spigot builds ACROSS its octagon —
# which is exactly how the leg shaft it mates with already prints. The two halves
# of that joint finally share a build direction.


def _foot_mortise_cutter(lx: float) -> cq.Workplane:
    """The SHARED foot mortise (legs.foot_mortise_cutter) at a station —
    one TPU foot SKU serves the -Y leg blocks and the bar."""
    return LG.foot_mortise_cutter().translate((lx, YC, 0))


def _bar_full() -> cq.Workplane:
    """The full bar (pre-split): slim prism − slots − wiring TROUGH −
    the full-length dovetail lid GROOVE − the lid-lock detent pocket."""
    body = box_at(BAR_X1 - BAR_X0, BAR_Y1 - BAR_Y0, BAR_H,
                  x=(BAR_X0 + BAR_X1) / 2, y=(BAR_Y0 + BAR_Y1) / 2, z=BAR_H / 2)
    body = body.union(_stub_tower(FEET[0][0], False, latch=(LATCH_FOOT == 0)))
    # FEET[1] is the -X/+Y TRRS station -- the ONE leg src.leg_stack redesigns, so
    # it is the one end that has flipped to a mortise. FEET[0] keeps the spigot
    # until its leg is redone; the two towers are deliberately different right now
    # and this is the line that says so.
    body = body.union(_mortise_tower(FEET[1][0], True))
    body = body.cut(_foot_mortise_cutter(FEET[0][0]))
    body = body.cut(_foot_mortise_cutter(FEET[1][0]))
    # WIRED TOWER'S WAYS. The old route threaded the jack straight UP THE AXIS of
    # the spigot; that axis is now the mortise, so the jack moved into a corner
    # (_mortise_tower) and its cable drops from the corner bore into the trough.
    # Cut AFTER the union because it pierces both the tower and the bar beneath.
    cx, cy = _corner(TRRS_CORNER_D, *TRRS_CORNER)
    wlx, wly = FEET[1][0] + cx, YC + cy
    # down-way: corner bore -> the trough band, opening out the bar's underside
    # for assembly access the way the old foot-mortise route did
    body = body.cut(cyl(8 * D.BEAD, BAR_H + 2.0, z=-1.0).translate((wlx, wly, 0)))
    # side way into the trough itself, along -Y
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        4.0, 24.0, cq.Vector(wlx, wly, BAR_H / 2.0), cq.Vector(0, 1, 0))))

    # wiring TROUGH — now opens +Y (the top of the print), directly behind the
    # groove floor and exactly as tall in Z as the dovetail's foot, so the two
    # cavities merge into one channel and the 1.6 rails survive as ledges. No
    # ceiling anywhere in it: that is what the print flip bought.
    body = body.cut(box_at(TROUGH_X1 - TROUGH_X0, TROUGH_D + LID_T + 1.0, TROUGH_HZ,
                           x=(TROUGH_X0 + TROUGH_X1) / 2,
                           y=(LID_Y0 - TROUGH_D + BAR_Y1 + 1.0) / 2,
                           z=(TROUGH_Z0 + TROUGH_Z1) / 2))

    # full-length dovetail lid GROOVE in the +Y FACE: runs out the -X end face
    # (the install mouth + the leg-wiring access) and dies 1.6 short of the +X
    # end, leaving the wall that stops the lid. Profile is the old one rotated
    # about X — same rail step, same self-supporting flanks, now across Z.
    groove = (cq.Workplane("YZ")
              .polyline([(LID_Y0 - YC,      LID_ZC - LID_FOOT_HW),
                         (LID_Y0 - YC,      LID_ZC + LID_FOOT_HW),
                         (BAR_Y1 - YC,      LID_ZC + LID_MOUTH_HW),
                         (BAR_Y1 + 1 - YC,  LID_ZC + LID_MOUTH_HW),
                         (BAR_Y1 + 1 - YC,  LID_ZC - LID_MOUTH_HW),
                         (BAR_Y1 - YC,      LID_ZC - LID_MOUTH_HW)])
              .close().extrude(LID_XB - (BAR_X0 - 1.0)))
    body = body.cut(cq.Workplane("XY").add(groove.val())
                    .translate((BAR_X0 - 1.0, YC, 0)))
    # lid-lock detent pocket, bored -Y into the groove floor (a TPU nub sits 1.2
    # proud of it, into lid B's underside groove)
    body = body.cut(cyl_y(LOCK_D, 3.2, y0=LID_Y0 - 3.1, x=LOCK_X, z=LOCK_Z))
    return body


# SPLICE JOINTS — cadkit install-z, ROTATED. cadkit only models ±x and ±z because
# its frame is PRINT-relative: its Z is the build axis, not world Z. The bar now
# builds -Y -> +Y, so cadkit's Z *is* world Y here, and an install-z joint is
# exactly right — it just has to be rotated -90 about X to land, which maps local
# +Z -> world +Y and local +Y -> world -Z. (There is no install='y' to reach for,
# and there should not be: the axis that matters to a joint is the print axis.)
#
# install='-z': the tenon seats travelling local -Z = world -Y, so the STOP closes
# the -Y end and the cavity opens +Y — no ceiling to bridge, and the LID (which caps
# +Y) is what blocks the escape direction. Same bargain as before, one axis over.
_UP = PrintSpec(nozzle=0.8, material="PETG-GF", facing="up")
# Both joints now live in the trough's solid BACK WALL and stack along world Z
# (the old pair straddled the trough in Y; that room is the lid's now).
SPLICE_ZC = (TROUGH_Z0 + 3.5, TROUGH_Z1 - 3.5)  # 7.00 / 16.50 — INSIDE the trough
                                                # band, or the tenons have no way in
SPLICE_W  = 6.4                                 # across, world Z
SPLICE_L  = _BACK_WALL - D.MIN_WALL_2P          # 15.0 engagement along world Y,
                                                # leaving a 1.6 stop floor at -Y
SPLICE_D  = 8.0                                 # room into the +X piece (world X)
SPLICE_J  = tuple(joint(width=SPLICE_W, length=SPLICE_L, depth=SPLICE_D,
                        tenon=_UP, mortise=_UP, install="-z")
                  for _ in SPLICE_ZC)
# what is left beside each cavity in Z is printed wall — hold it to the tier
_SPLICE_EDGES = [0.0] + [z for zc in SPLICE_ZC for z in
                         (zc - SPLICE_W / 2, zc + SPLICE_W / 2)] + [BAR_H]
for _i, _j in enumerate(SPLICE_J):
    _lo = _SPLICE_EDGES[2 * _i + 1] - _SPLICE_EDGES[2 * _i] - _j.clearance
    _hi = _SPLICE_EDGES[2 * _i + 3] - _SPLICE_EDGES[2 * _i + 2] - _j.clearance
    assert min(_lo, _hi) >= D.MIN_WALL_2P, (
        f"splice joint at z {SPLICE_ZC[_i]:.1f} leaves {min(_lo, _hi):.2f} of bar "
        f"beside it, under the {D.MIN_WALL_2P} tier")
    assert (TROUGH_Z0 <= SPLICE_ZC[_i] - SPLICE_W / 2 - _j.clearance
            and SPLICE_ZC[_i] + SPLICE_W / 2 + _j.clearance <= TROUGH_Z1), (
        f"splice joint at z {SPLICE_ZC[_i]:.1f} pokes outside the trough band "
        f"{TROUGH_Z0:.2f}..{TROUGH_Z1:.2f} — its mortise opens through the trough, "
        f"so any part outside it is a blind pocket the tenon cannot enter")


def _splice_pose(s, xs: float, zc: float) -> cq.Workplane:
    """cadkit frame -> bar frame: rotate the print axis onto world Y, then land the
    joint at splice `xs` and Z centre `zc`. Authored at local y=0 so the rotation
    puts it on the bar's Z axis; the world-Y offset seats it in the back wall."""
    return (s.rotate((0, 0, 0), (1, 0, 0), -90.0)
             .translate((xs, BAR_Y0 + D.MIN_WALL_2P, zc)))


def _splice_tenons(xs: float) -> cq.Workplane:
    """The -X piece's half of both splice joints at bar splice `xs`."""
    out = None
    for j, zc in zip(SPLICE_J, SPLICE_ZC):
        p = _splice_pose(j.tenon(root=2.0), xs, zc)
        out = p if out is None else out.union(p)
    return out


def _splice_mortises(xs: float) -> cq.Workplane:
    """The +X piece's cavities — open at the piece's +Y face (the top of the print,
    so no ceiling to bridge) and stopped at -Y by the back wall's 1.6 floor, which
    is what sets the depth on the assembly bench. Y is unretained BY DESIGN — it is
    the install axis, and the LID closes it (see the module docstring)."""
    out = None
    for j, zc in zip(SPLICE_J, SPLICE_ZC):
        p = _splice_pose(j.mortise(drop=3.0), xs, zc)
        out = p if out is None else out.union(p)
    return out


def _clip(x0: float, x1: float) -> cq.Workplane:
    return box_at(x1 - x0, 80.0, 120.0, x=(x0 + x1) / 2, y=YC, z=40.0)


def pedal_bar_a() -> cq.Workplane:
    """-X bar piece (WIRED TRRS tower): full bar clipped at XS1 + its two
    splice tenons (piece B drops straight down onto them; the lid locks
    the stack — no glue). ~219 long — prints STRAIGHT."""
    return (_bar_full().intersect(_clip(BAR_X0 - 1.0, XS1))
            .union(_splice_tenons(XS1)))


def pedal_bar_b() -> cq.Workplane:
    """MID bar piece (trough only): clipped XS1..XS2 − the XS1 cavities +
    the XS2 tenons. ~219 long — straight print."""
    return (_bar_full().intersect(_clip(XS1, XS2))
            .cut(_splice_mortises(XS1))
            .union(_splice_tenons(XS2)))


def pedal_bar_c() -> cq.Workplane:
    """+X bar piece (plain tower): clipped at XS2 − the XS2 cavities.
    ~215 long — straight print."""
    return (_bar_full().intersect(_clip(XS2, BAR_X1 + 1.0))
            .cut(_splice_mortises(XS2)))


# X span each bar piece OWNS, for deciding which pedal housings fuse into it.
# Single-sourced because it is needed twice in build.py — once for the exported
# STEP and once for the assembly — and when those two carried their own copies the
# assembly silently kept the UNFUSED bar.
PIECE_SPAN = {"pedal_bar_a": (-1e9, XS1),
              "pedal_bar_b": (XS1, XS2),
              "pedal_bar_c": (XS2, 1e9)}


def _lid_full() -> cq.Workplane:
    """The full sliding-dovetail lid (pre-split): a 4-thick plate with 45°
    dovetail flanks riding the bar's top groove — ONE lid roofs the wiring
    trough (no screws — and no latch cavities to roof either, since the
    quick-release went). It carries the thumb-post slots and the underside
    LOCK groove (both pieces slide over the
    groove-floor nub; lid A's groove ends in a dimple that clicks in at the
    final position). Prints TOP-FACE DOWN: the flanks are 45°."""
    _c = 0.1                                   # per-side sliding clearance
    prof = (cq.Workplane("YZ")
            .polyline([(LID_Y0 - YC, LID_ZC - LID_FOOT_HW + _c),
                       (LID_Y0 - YC, LID_ZC + LID_FOOT_HW - _c),
                       (BAR_Y1 - YC, LID_ZC + LID_MOUTH_HW - _c),
                       (BAR_Y1 - YC, LID_ZC - LID_MOUTH_HW + _c)])
            .close().extrude(LID_XB - LID_XA))
    body = cq.Workplane("XY").add(prof.val()).translate((LID_XA, YC, 0))
    # underside LOCK groove (rides the groove-floor nub, 0.5 squeeze) + dimple
    body = body.cut(box_at(LID_XB - LID_XA + 2, 0.7, LOCK_D + 0.5,
                           x=(LID_XA + LID_XB) / 2, y=LID_Y0 + 0.35, z=LOCK_Z))
    body = body.cut(cyl_y(LOCK_D + 0.6, 1.7, y0=LID_Y0 - 0.1, x=LOCK_X, z=LOCK_Z))
    return body


def pedal_lid_a() -> cq.Workplane:
    """-X lid piece (bridges bar splice XS1 + carries the lock dimple).
    Goes in SECOND now that install runs -X -> +X: it follows B through the
    same mouth, butts it, and its dimple clicks onto the groove-floor nub —
    pinning both pieces against the +X end wall. Its -X end is FLUSH with
    the bar's, so the closed bar shows no mouth."""
    return _lid_full().intersect(_clip(LID_XA - 1.0, XL))


def pedal_lid_b() -> cq.Workplane:
    """+X lid piece (bridges bar splice XS2). Goes in FIRST and runs the
    whole bar to the 1.6 end wall, riding over the nub on its lock groove
    (which is why that groove is full length and only A's ends in a
    dimple)."""
    return _lid_full().intersect(_clip(XL, LID_XB + 1.0))


def _lock_nub() -> cq.Workplane:
    """The lid-lock instance: same printed nub, pressed into the bar-top
    pocket; sits 1.2 proud of the groove floor into lid B's lock groove."""
    return cyl_y(4.0, 4.0, y0=LID_Y0 - 2.8, x=LOCK_X, z=LOCK_Z)


def nub_part() -> cq.Workplane:
    """The single printed TPU nub (export once, print 1 — the lid lock)."""
    return _lock_nub()


def _cable_runs():
    """DEMO bar cable: from the trough, through the wired stub's side way,
    up its core to the captive plug seat (the column-side cable is placed
    by build.py with the leg stack). Rises on the TRRS axis — offset +5
    from the station, matching the down-way and the plug seat."""
    lx = FEET[1][0]
    wly = YC - LG.TRRS_DY
    pts = [(lx + 24.0, YC + 2.0, 11.0), (lx + 14.0, wly + 3.5, 11.0),
           #        ^ the trough moved to the +Y side with the lid; YC-3.0 is
           #          solid bar now (the run used to sit in the +Z trough)
           (lx + 5.0, wly, 11.0), (lx + 5.0, wly, 26.0)]
    out = None
    for a, bpt in zip(pts[:-1], pts[1:]):
        va, vb = cq.Vector(*a), cq.Vector(*bpt)
        rod = cq.Workplane("XY").add(cq.Solid.makeCylinder(
            1.85, (vb - va).Length, va, vb - va))
        out = rod if out is None else out.union(rod)
    return [("pedal_trrs_cable_bar", out)]


def assembly_parts():
    """[(name, workplane)] — printed bar parts + the bar cable, drawn
    SEATED, absolute X/Y, z0 = plate bottom (build.py lifts by ground +
    FOOT_H and places the stubs/bolts/buttons/plug/jack dummies with the
    leg stacks)."""
    return [("pedal_bar_a", pedal_bar_a()),
            ("pedal_bar_b", pedal_bar_b()),
            ("pedal_bar_c", pedal_bar_c()),
            ("pedal_lid_a", pedal_lid_a()),
            ("pedal_lid_b", pedal_lid_b()),
            ("pedal_detent_nub_0", _lock_nub()),
            ("leg_foot_4",
             LG.leg_foot().translate((FEET[1][0], YC, -12.0))),
            ("leg_foot_5",
             LG.leg_foot().translate((FEET[0][0], YC, -12.0)))]         + _latch_parts() + _cable_runs()


def _latch_parts():
    """The bar-joint latch. It lives in the TOWER, so they travel with
    the BAR -- which is the piece you lift off, and therefore the piece the
    button has to be on (user). Authored at the tower origin, then through the
    tower's own 180 rotation so the button faces outboard like the legs'."""
    out = []
    for i, (lx, _s) in enumerate(FEET):
        if i != LATCH_FOOT:                 # one joint pair while the latch is iterated
            continue
        for nm, wp in (("latch_slider", LT.slider(LT.LX_TOWER)),
                       ("latch_cover", LT.cover(LT.LX_TOWER)),
                       ("latch_spring", LT.spring(LT.LX_TOWER))):
            out.append(("%s_%d" % (nm, 4 + i),
                        wp.translate((0, 0, STUB_Z0))
                        .rotate((0, 0, 0), (0, 0, 1), 180)
                        .translate((lx, YC, 0))))
    return out
