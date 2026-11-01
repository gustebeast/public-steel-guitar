"""Leg datums and the leg<->body joinery shared by the chassis, endplates and leg stack.

The leg column itself is built by src.leg_stack. What lives here is what the parts
around it cut from or mate with:

  * the leg's SECTION: SQ_W (44.8 square), the BLK_W terminal-block square and the
    flush octagon section tenon (_section_tenon) the pedal bar's +X stub tower uses;
  * the cover-rail octagon joint (_rail_tenon / _rail_groove, used by the joint coupon);
  * the shared TPU FOOT (leg_foot) and its dovetail mortise (foot_mortise_cutter);
  * the body joint: the Y-running crossing RIDGES (_stub_ridge, at _cross_x) and the
    world-space grooves the chassis and endplates cut for them (corner_groove_negatives);
  * the leg's one screw, the LOCK PIN (lock_pin_joint), and the SERVICE SLIDE that a
    second hole in the foot gives the +Y corners (service_pin_joint, foot_pin_joints).
"""

from __future__ import annotations


import cadquery as cq

from . import dimensions as D

B = D.BEAD                             # bead grid unit (cadkit.printing)
from .helpers import box_at
from cadkit.fasteners import M4 as _M4, ScrewJoint as _ScrewJoint

FOOT_H  = 15 * B                       # 12.0 the TPU foot's ground pad
# The shared foot's dovetail tenon stops HERE in local +Y, and the mortise's
# closed end sits 0.5 beyond it (that butt is the foot's Y registration).
#
# It used to reach 15.5. The pedal bar's lid now runs END TO END — over both foot
# stations — and the lid's dovetail occupies the last 4 mm of the +Y face, so a
# tenon poking past the groove floor sat in the lid's path for the whole install
# stroke. A local relief in the lid can't fix a moving part: the clearance has to
# hold everywhere the lid travels, so the tenon gave way instead. Costs 1.9 of a
# 33 tenon (5.8%) on a TPU pad that works in compression; the registration butt
# survives because the mortise end moved with it.
FOOT_TENON_Y1 = 13.6
# LEG_STATIONS_X (the two corner-station X's, both rails) is COMPUTED in chassis.py
# from the shared endplate<->leg model (chassis.LEG_STATIONS_X = endplate tip -/+
# LEG_W/2 -- FLUSH-X: each leg's outer X face lies ON its endplate's outer face).
# It lives there (not here) because it depends on the endplate tip positions,
# which are chassis constants. Result: (2.66, -614.86).


TENON_L = 197.0                # the old shaft's sliding tenon: travel 142
                               # + overlap 50 + 5 dead (the fine-stage law)
BAR_STUB_Z0  = D.PEDAL_BAR_H + D.PEDAL_TOWER_BAND               # 51.9: the bar
                               # tower's seat plane, in the bar's own frame.
                               # pedal_bar re-exports this as STUB_Z0.


def foot_mortise_cutter() -> cq.Workplane:
    """Underside DOVETAIL mortise for the shared TPU foot tenon (slides
    in from -Y local; grip + compression = no fastener). Cut at the
    origin; z0 = the block's bottom face."""
    return (cq.Workplane("XZ")
            .polyline([(-15.0, 0.0), (-13.4, 6.0), (13.4, 6.0),
                       (15.0, 0.0)])
            .close().extrude(40.0).translate((0, FOOT_TENON_Y1 + 0.5, 0)))


# ═══ SQUARE LEG: constant 44.8 square outside, printed LYING on a face in PETG-GF
# (layer lines run ALONG the leg, so kick bending loads stay within layers).
SQ_W = 56 * B                  # 44.8 outer square width (uniform). 56 beads, and the
                               # EVENNESS is the point (user): the leg's half-width is a
                               # datum for half the joinery -- SLV_FACE_Y, SH_Y, BLK_W and
                               # the latch's FACE_Y are all SQ_W/2 minus material. At the
                               # old 44.0 = 55 beads, an ODD count, that half was 22.0 and
                               # could never land on the grid, so the whole chain inherited
                               # the miss. 56/2 = 28 beads exactly, and the chain cleans up
                               # at the source rather than one constant at a time.

# ── SECTION JOINT: the cadkit OCTAGON ("stop-sign") slide joint, sliding along Z,
# authored with the flat octagon STEM BASE toward local +Y and the point toward
# local -Y. See _section_tenon (the pedal bar's +X stub tower uses it).
SEC_W       = 28.0    # octagon flat-to-flat across local X; 8.4 mm wall to the
                      # ±22.4 X faces
SEC_H       = 36.0    # profile HEIGHT (the cadkit room bound past the mating
                      # plane — user: pass the ACTUAL room). Width-driven
                      # minimum 22.24; the extra 13.76 grows the two verticals
                      # to 7.68 each (deeper lip engagement + flank bearing)
SEC_TEN_L   = 28.0    # spigot engagement along Z
SEC_MOR_L   = SEC_TEN_L + 0.4   # socket depth: spigot 28 + a 0.4 tip gap (user: near-flush
                      # tips — the tolerance slack belongs HERE, never at the big
                      # shoulder faces, which are the ground-reaction hard stop)
# FLUSH AT THE BED FACE (user round 2): the joint is NOT hidden inside the leg.
# The tenon's flat STEM BASE lies exactly ON the local +Y face = the print bed
# (a floating inset base would be an unprintable mid-air flat on the side-lying
# spigot), and the mortise opens THROUGH that face as an octagon-profile groove
# — the open air gap the next tenon slides into. Capture survives: the face
# slit is the 14-wide stem, the 28 waist can't pass it.
SEC_CABLE_D = 7.0     # wired leg: axial cable bore through the spigot + socket roof
SH_CLR      = 0.2     # shaft↔sleeve octagon SLIDE fit (per side; the fine
                      # stage strokes, unlike the assemble-once 0.1 joints)
TRRS_DY     = 3.5     # the old TRRS axis offset in local +Y (the profile's deep
                      # waist); chassis still keys its well off it


# ── SLEEVE COVER: the sleeve's +Y face band is THINNED by COVER_T and a COVER
# PLATE rides it on two W5.6 octagon RAILS (_rail_tenon / _rail_groove, the
# joint the coupon prints). The SLIDER octagon drops with the face: stem plane SH_Y.
COVER_T    = 5 * B    # 4.0 cover plate thickness = the face-thinning depth
SLV_FACE_Y = SQ_W / 2 - COVER_T        # 18.4: the sleeve's thinned +Y face
SH_Y       = SLV_FACE_Y - SH_CLR       # 18.2: slider stem plane (0.2 running
                                       # clearance under the cover's inner face)
SH_H       = SH_Y + 18 * B             # 32.6: slider octagon height (roof -18 beads;
                                       # was a bare 14.0 = 17.5 beads, the only OFF-GRID
                                       # offset in the leg joinery)
CVR_RAIL_X = 21 * D.BEAD   # 16.8: rail centres ±x
CVR_RAIL_W = 7 * B    # 5.6 rail octagon flat-to-flat. 6 beads (4.8) is BELOW cadkit's
                      # family floor for this width (h_min 4.95 at nozzle 0.8), so 7 is
                      # the smallest legal bead count -- the floor picks it, not taste
from cadkit.joinery import PrintSpec as _PrintSpec, joint as _joint
from cadkit.printing import snap as _snap
# cadkit collapsed the per-family entrypoints into ONE `joint()` (you describe the
# SITE, it picks the geometry), so this file now says how its halves PRINT instead
# of naming the octagon. Both are PETG-GF printed -Z->+Z.
_UP = _PrintSpec(nozzle=D.NOZZLE_D, material="PETG-GF", facing="up")
CVR_RAIL_H = _snap(_joint(CVR_RAIL_W, 1.0, tenon=_UP, mortise=_UP, clearance=0.1).height,
                   D.NOZZLE_D, "up")
#   ASK cadkit for the floor, then round UP to the next whole bead -- both properties at
#   once. Hand-writing a bead-aligned height would break the moment cadkit tightens the
#   family; taking cadkit's raw number leaves the groove depth off the grid (7.283 =
#   9.10 beads). snap(..., 'up') can only ever ADD material to a floor, never violate it.
BLK_W      = 2 * SH_Y # 36.4: the shaft terminal blocks' square (user: the
                      # cover side's inset on ALL FOUR sides; the +Y face IS the
                      # slider stem plane, so the flat print bed comes free)


def _rail_tenon(length: float) -> cq.Workplane:
    """Cover-rail male: W5.6 octagon rib on the cover's inner face (stem rooted
    at the thinned-face plane, point -Y into the sleeve wall), z 0..length;
    caller translates to ±CVR_RAIL_X. Prints growing UP off the lying cover
    plate: neck, 45° flare out, 45° back to the 0.8 tip — no overhang."""
    return (_joint(CVR_RAIL_W, length, tenon=_UP, mortise=_UP, clearance=0.1, depth=CVR_RAIL_H).tenon(root=0.0)
            .rotate((0, 0, 0), (0, 1, 0), -90)
            .rotate((0, 0, 0), (0, 0, 1), 90)
            .translate((0, SLV_FACE_Y, 0)))


def _rail_groove(length: float) -> cq.Workplane:
    """Cover-rail female: the matching W5.6 slot, opening through the thinned
    +Y face — on the lying sleeve a standard mortise-at-the-bed. Z-running;
    caller translates/limits it."""
    return (_joint(CVR_RAIL_W, length, tenon=_UP, mortise=_UP, clearance=0.1, depth=CVR_RAIL_H).mortise(drop=2.0)
            .rotate((0, 0, 0), (0, 1, 0), -90)
            .rotate((0, 0, 0), (0, 0, 1), 90)
            .translate((0, SLV_FACE_Y, 0)))


def _section_tenon(length: float = SEC_TEN_L) -> cq.Workplane:
    """Section-joint male SPIGOT: the cadkit octagon TENON rotated so its slide
    axis is +Z (stacking), point toward local -Y, and the flat STEM BASE lying
    EXACTLY ON the local +Y face (y = SQ_W/2) — the print bed of the side-lying
    leg (user: the stem must be flat against the bed; an inset base would be a
    floating flat). root=0: any root would poke past the leg face. Callers
    embed 1 along Z for the volumetric fusion instead. Base plane at z=0."""
    return (_joint(SEC_W, length, tenon=_UP, mortise=_UP, clearance=0.1, depth=SEC_H).tenon(root=0.0)
            .rotate((0, 0, 0), (0, 1, 0), -90)
            .rotate((0, 0, 0), (0, 0, 1), 90)
            .translate((0, SQ_W / 2, 0)))


# ── the leg↔body joint, Y-INSTALL (user: the foot prints ON ITS SIDE for layer
# strength, so it SLIDES ALONG Y into the body, not Z): Y-running octagon RIDGES on
# its top face (_stub_ridge at _cross_x) slide into grooves the chassis and the
# endplates cut from corner_groove_negatives. Nothing holds it along Z but the
# LOCK PIN below (lock_pin_joint).
STUB_WALL_D = D.WALL_THICKNESS # endplate end-wall depth (= CH.T -- DERIVED now; it was a
                               # hardcoded 10.0 whose comment already claimed it tracked the
                               # chassis wall, so it silently would not have): the
                               # outboard 10.4 of the leg's 44.8 is under the
                               # end wall; the remaining 34.4 is the leg<->
                               # SIDE-PANEL overlap.
# CROSSING-ridge stations (user): split the side-panel overlap (34.4, from
# the end-wall inner face at local eps*12 to the leg's inboard face at
# local -eps*22.4) into THIRDS and put a ridge at each dividing point, then
# snap each to the lever-mortise grid where it reaches (see _cross_x).


def _cross_x(eps: float, station: float | None = None) -> tuple:
    """The two crossing-ridge |local-x| stations for an end-wall side.

    THE GRID WINS WHERE THE GRID EXISTS (user, 2026-09-16). The nominal stations are the THIRDS
    of the leg<->side-panel overlap, but a ridge that crosses the chassis floor has to land in a
    lever mortise -- the chassis cuts those by its own rule and nothing here may reshape them.
    Given the leg's world `station`, each third snaps to the nearest mortise station when one is
    within half a pitch; where there is none (the +X corners sit past the floor's +X end, so the
    grid does not reach them) the third stands."""
    inner = SQ_W / 2 - STUB_WALL_D              # end-wall inner face (12)
    span = SQ_W - STUB_WALL_D                   # side-panel overlap (34)
    raw = (eps * (inner - span / 3.0), eps * (inner - 2.0 * span / 3.0))
    if station is None:
        return raw
    # THE NEAREST STATION THAT IS NOT OUTBOARD OF THE THIRD. The lock pin's hole runs inboard
    # from the end face and stops a two-bead wall short of the first groove it meets, so a groove
    # that lands OUTBOARD of its third eats the insert's room -- 2.71 of it, which left 14.16 of
    # hole where the insert needs 18.9 and ScrewJoint refused to build. Inboard is free, so each
    # ridge takes the closest station on that side rather than the closest station outright.
    # (Rejecting the outboard one and keeping the third instead is not an option: the third is
    # not a station, so the ridge would have no mortise and be dropped -- which cost all four
    # corners BOTH ridges before this was a search rather than a test.)
    grid = D.lever_grid_x()
    out, taken = [], set()
    for r in raw:
        cand = [g for g in (s - station for s in grid)
                if eps * g <= eps * r + 1e-9 and round(g, 6) not in taken]
        if not cand:
            out.append(r)
            continue
        g = min(cand, key=lambda q: abs(q - r))
        taken.add(round(g, 6))
        out.append(g)
    return tuple(out)
STUB_TEN_W = 9 * D.BEAD        # 7.2: the ridge's widest (its root slab) -- THE SAME JOINT the
                               # levers use, because these ridges ride the same mortises (user):
                               # knee_lever._lever_joint, the fit-tested standing pair
# The END-WALL TONGUE and its rebate are gone (user, 2026-09-17: see
# corner_groove_negatives); these numbers survive only as the end-wall check below,
# which keeps a floor under the LOCK PIN's M4 insert pocket behind where the rebate was.
STUB_TNG_FIT = 0.1             # the PETG-GF coupon fit, on the rebate's outboard face
STUB_TNG_W = 5 * D.BEAD        # tongue thickness (x)
STUB_TNG_REBATE_IN = 0.2       # the rebate reached this far INBOARD of the tongue, into
                               # the endplate<->shell gap (< chassis.EP_LEG_CLR)
_PIN_FLOOR = (STUB_WALL_D - STUB_TNG_W - STUB_TNG_FIT) - _M4.insert_depth
assert _PIN_FLOOR >= D.MIN_WALL, (
    "the end wall behind the rebate leaves only %.2f under the M4 insert pocket" % _PIN_FLOOR)
assert _M4.screw_l <= STUB_WALL_D + 1e-9, (
    "an M4 set screw flush in the end face would reach past the tongue into the gap")
# Crossing-ridge z placement: the octagon profile's z=0 IS the mating
# plane (the stem runs from -root below it, through it, to the waist
# above), so the ridge sits at exactly the foot's top and the groove at
# exactly z = Z_BOT — the built-in root/drop do the embedding/opening.
TRRS_DX = 5.0                  # the old TRRS axis offset in local x (paired with TRRS_DY)


def _stub_ridge(length: float = SQ_W) -> cq.Workplane:
    """One RIDGE as a Y-RUNNING prism (slide axis +y), head UP, width along x, mating
    plane at z 0, extruded +y from y 0: the knee lever's mount tenon, because it rides the
    same mortises. The joint is built along X; rotate Z(+90) maps it to +y."""
    from . import knee_lever as _KL
    assert abs(STUB_TEN_W - _KL._J_HOST_W) < 1e-9, "STUB_TEN_W is not the lever joint's width"
    return _KL._lever_joint(length).tenon().rotate((0, 0, 0), (0, 0, 1), 90)


def _groove(length: float) -> cq.Workplane:
    """The matching cavity (the lever mount's mortise), Y-running, head up, opening
    DOWNWARD at its base plane (its mouth carried 2.1 below it -- over the sliding plane
    that is air). Callers translate it to (ridge x, y0, Z_BOT)."""
    from . import knee_lever as _KL
    # the legs' ridges keep the seat at 0: round 6 tested the seat at c on the levers only, and
    # moving it here lowers every leg stub against the chassis (latch, pogo, TRRS)
    return _KL._lever_joint(length).mortise(drop=2.1, seat=0.0).rotate((0, 0, 0), (0, 0, 1), 90)


# SERVICE POSITION (user, restored 2026-09-17 on the decoupled foot). To reach what sits over a
# +Y foot -- the bridge's string access channels, the keyhead's nut-block height screws -- back
# the leg's one screw out, slide the FOOT SERVICE_SLIDE outboard along Y until its SECOND hole
# lines up with that same screw's axis, and drive the screw back in, which locks it there. Work,
# slide it home, screw back in. ONE DISTANCE FOR BOTH ENDS (see SERVICE_SLIDE): the player
# memorizes a position, not a pair of them.
# Only SERVICE_CORNERS get it, keyed (egx, syg) by outboard x and y sign: the strings span
# Y +-42.8, so only the +Y feet sit under them. Nothing is cut back to make room -- the foot
# simply travels along the grid joint it already slides in on, and the assert in
# service_pin_joint is what proves there is still tenon in the body to pin out there (at the
# bridge one, 20.2 of it; at the keyhead all three, 20.2/12.8/7.9).
# WHAT NEEDS THE ROOM: the keyhead's nut-block HEIGHT SCREWS (bronner, user: slide the leg rather
# than move the screws) -- their button heads hang down into the floor in head cavities, which is
# also why the mortises over that foot stop short of them -- and the bridge's ten STRING ACCESS
# CHANNELS, which drop through the floor right over the other foot. Those two shortened tenons are
# the same fact as the slide: what stops a tenon is what the slide exists to uncover.
# LEG_NY_FACE is chassis.LEG_Y[0] - LEG_W/2 spelled out from dimensions (legs cannot import
# chassis); keyhead_endplate asserts the two agree.
from . import nut_block as _NB                # nut_block imports dimensions + motor_bank only: no cycle
LEG_NY_FACE = D.RAIL_HI_INNER_Y + D.WALL_THICKNESS - SQ_W     # a +Y leg's -Y face
KEYHEAD_CLEAR_Y = (max(_NB.height_screw_xy(i)[1] for i in range(D.N_STRINGS))
                   + _NB.HS_HEAD_CAV_D / 2.0 + D.MIN_WALL_2P)   # +Y edge of the room the heads need
# ...and the BRIDGE's string access channels (user, 2026-09-11). The +Y bridge-end leg stands under
# strings 1-3's channels; slid out, it clears the +Y-most one (string 1's), so a hand can feed every
# string up from below (bridge_endplate.access_blocked tests the SLID leg). The margin is to the
# FOOT's own -Y face now, not a groove's end (user, 2026-09-17): the thing standing over those
# channels is the body adapter -- its 44.8 block and the grid tenons that start on the block's
# -Y face -- and it is the whole foot that slides. So the margin is measured to that face, and
# the slide is what puts it a two-bead wall clear of string 1's hole.
CROSS_GROOVE_IN = 0.5          # crossing grooves' inboard overshoot past the leg face (corner_groove_negatives)
BRIDGE_CLEAR_Y = (max(D.string_y(i) for i in range(D.N_STRINGS))
                  + D.STRING_ACCESS_D / 2.0 + D.MIN_WALL_2P)
# THE +X END SETS THE DISTANCE AND THE -X END REUSES IT (user, 2026-09-17), so there is ONE
# position to memorize: pull the foot out until the second hole lines up, screw in, work, slide
# back. Hence the bridge's number ALONE and not the max of the two ends' -- the assert says what
# that costs, which is nothing: the keyhead's own need is less than half of it, so the one
# position clears both. NOT rounded to whole beads: it is a travel, not a wall.
SERVICE_SLIDE = round(BRIDGE_CLEAR_Y - LEG_NY_FACE, 6)              # 25.6
assert SERVICE_SLIDE >= KEYHEAD_CLEAR_Y - LEG_NY_FACE - 1e-9, (
    "the shared service slide (%.2f, the bridge's need) is short of the keyhead's own (%.2f) -- "
    "one memorized position cannot serve both ends any more"
    % (SERVICE_SLIDE, KEYHEAD_CLEAR_Y - LEG_NY_FACE))
SERVICE_CORNERS = ((-1.0, 1.0), (1.0, 1.0))
# The LOCK PIN sits LOCK_PIN_DY OUTBOARD of the leg's centreline (user), which is what
# leaves room for a long service slide: the second hole goes SERVICE_SLIDE inboard of it and
# has to stay on a tenon whose run covers the foot's full 44.8 (SERVICE_SLIDE_MAX). 7.5
# (user, 2026-09-11; was 7.0) was what let the slide reach the bridge's need; each bead the +Y rail
# comes in lengthens the slide, so past that the pin moves out with it.
LOCK_PIN_DY = max(7.5, SERVICE_SLIDE - (SQ_W / 2 - (_M4.shaft_clr_d / 2 + D.MIN_WALL_2P)))
# ...and the screw itself (lock_pin_joint): a stock M4 button head recessed in the end
# face, into a heat-set insert on the kept shell's face across the endplate<->shell gap
SHELL_GAP = 0.4                    # that gap: chassis.EP_LEG_CLR, asserted equal there
LOCK_SCREW_L = 40.0                # M4x40 button head. THE SERVICE POSITION CHOSE THIS LENGTH,
                                   # not the seated one: with the foot slid out, the ONLY material
                                   # left under this axis is a tenon whose mortise runs the foot's
                                   # full 44.8 in Y, and at both ends that is the THIRD station in
                                   # (39.96 from the end face) -- the two outboard ones stop short,
                                   # at the bridge for the string channels and at the keyhead for
                                   # the height screws, which is exactly why the foot has to slide
                                   # at all. So the pin has to reach 39.96 to hold the foot out
                                   # there, and 18 reached 20.4. Seated it now crosses ALL THREE
                                   # tenons instead of one and stops 0.86 short of breaking out of
                                   # the last, so the retention got stronger on the way. The cost
                                   # is a BOM length. It rode the "M4 hold-down screw" row while it
                                   # was 18 (that row already stocked M4x18 for the keyhead's +Z
                                   # lock and the ten height screws) and no stocked length in the
                                   # box reaches: 35 lands 0.74 into the third tenon, which pins
                                   # nothing. So four of them become their own row -- the only new
                                   # line the service position costs, and still the same M4 button
                                   # head on the same 2.5 mm key.
                                   # WHAT IT CROSSES on the way: two 3.2 walls between the end
                                   # stations' mortises, each keeping 3.6 of web under the Ø4.4 hole
                                   # and 1.59 of floor over the teardrop's apex -- both above the
                                   # two-bead rule, because the hole sits low in a 8.13-deep mortise.
LOCK_INSERT_AT = 4.0               # the insert's mouth, measured in from the end face: inside
                                   # the ENDPLATE's own wall (user, 2026-09-17), clear of the
                                   # head's recess and finishing 1.4 short of the wall's inner
                                   # face. It used to sit in the CHASSIS, which is what forced
                                   # the chassis to keep a mortise-free zone for it.
LOCK_HEAD_D, LOCK_HEAD_H = 7.6, 2.2   # cadkit.fasteners.m4_button_screw's head
LOCK_RECESS = 3 * D.BEAD           # 2.4: the head sits just under the end face
# the screw's axis above the mating plane: its head recess (head + 0.4 of air) keeps a
# 2-bead floor over the endplate's underside, which also keeps it off the adapter's top
LOCK_Z = LOCK_HEAD_D / 2 + 0.4 + D.MIN_WALL_2P
# THE PIN BREAKS OUT OF THE TENON'S TOP, DELIBERATELY. The tenon is the grid joint, 8.6 tall,
# and a Ø4.4 hole centred at LOCK_Z leaves 0.6 above it -- a sliver that would tear off the one
# feature doing the pinning. leg_stack takes that strip away instead, so the pin sits in a NOTCH
# in the tenon and bears on its Y walls. What must hold is the material BELOW the hole.
assert LOCK_Z - _M4.shaft_clr_d / 2 >= D.MIN_WALL_2P - 1e-9, (
    "the lock pin leaves %.2f of tenon under its hole, under the two-bead floor"
    % (LOCK_Z - _M4.shaft_clr_d / 2))
assert LOCK_PIN_DY + _M4.shaft_clr_d / 2 + D.MIN_WALL_2P <= SQ_W / 2, (
    "the lock pin falls off the tenon's outboard end")
# ...and the most the slide can be: the SERVICE hole, SERVICE_SLIDE inboard of the seated one,
# still has to keep a two-bead wall to the inboard END of a full-length tenon (-SQ_W/2 from the
# centreline). Same form it had for the deleted tongue -- the full-length grid tenon runs the
# same 44.8 the tongue did, so the bound did not move when the tongue went.
SERVICE_SLIDE_MAX = SQ_W / 2 - (_M4.shaft_clr_d / 2 + D.MIN_WALL_2P) + LOCK_PIN_DY


# THE SIGNAL CORNER'S MIDDLE RIDGE. src.leg_trrs brings the leg's TRRS up the octagon
# joint's OWN axis (user: "go with the centre"), and the plug drops in through a O6.6
# hole in the body adapter's top face at that spine. The MIDDLE ridge's root is exactly
# there. Boring through a ridge would leave 1.6 slivers either side, so the ridge is CUT
# BACK instead -- it is already the one that gives up its inboard end to the service
# slide, and this is the same kind of loss, not a new kind. Both the adapter's ridge and
# the chassis/endplate GROOVE come from mid_ridge_cut(), so they cannot drift apart.
SIGNAL_RIDGE_IN = 14 * D.BEAD       # 11.2: where that ridge now starts, inboard of the
                                    # leg's centre. leg_trrs asserts it clears the hole
                                    # (apex included) by MIN_WALL_2P
SIGNAL_CORNER = (-1.0, 1.0)         # the -X/+Y leg: the one with a cable in it


def mid_ridge_cut(egx: float, syg: float) -> float:
    """How much of the MIDDLE crossing ridge's inboard end this corner gives up: the
    service slide everywhere, and on the signal corner whatever the leg's connector
    needs on top of it."""
    c = service_slide(egx, syg)
    if (float(egx), float(syg)) == SIGNAL_CORNER:
        c = max(c, SQ_W / 2.0 + SIGNAL_RIDGE_IN)
    assert c < SQ_W - D.MIN_WALL_2P, (
        "the middle ridge is cut back %.1f of its %.1f -- nothing left to engage"
        % (c, SQ_W))
    return c


def service_slide(egx: float, syg: float) -> float:
    """This corner's service slide: 0 unless it is one of SERVICE_CORNERS."""
    assert 0.0 <= SERVICE_SLIDE <= SERVICE_SLIDE_MAX + 1e-9, (
        "SERVICE_SLIDE %.1f is outside 0..%.1f: the second lock-pin hole would fall off "
        "the tongue" % (SERVICE_SLIDE, SERVICE_SLIDE_MAX))
    return SERVICE_SLIDE if (float(egx), float(syg)) in SERVICE_CORNERS else 0.0


def corner_groove_negatives(station: float, ly: float, syg: float,
                            egx: float,
                            z_bot: float,
                            relief: bool = True) -> list:
    """WORLD-space groove negatives for ONE leg corner — the ONE source
    both the chassis and the endplates cut from, so cross-part grooves
    (shell<->endplate, tab<->channel, wide corner rib) align by
    construction. syg = outboard y sign (+1 for +Y legs), egx = outboard
    x sign (+1 at the bridge end). Per corner: the END-WALL groove (blind
    at the stub's inboard y face = the flush hard stop, open + 1
    overshoot outboard) and two CROSSING grooves (overshot both ends).
    (No fin passage any more — nothing rides above the stub top.)
    relief=True appends the 45° overhang wedge — for the CHASSIS ONLY
    (it relieves the wall-plate tongue's print overhang; the endplates
    pass relief=False or the wedge eats their end-wall groove roof).
"""
    negs = []
    # (THE END-WALL REBATE IS GONE with the straight tongue it hosted -- user, 2026-09-17: the
    #  endplate gets that material back and holds the lock pin's INSERT in it instead. Its 45 deg
    #  overhang relief went with it: there is no rebate roof left to relieve.)
    # crossing grooves (thirds of the side-panel overlap): 0.5 inboard
    # overshoot, 1 outboard
    Lc = SQ_W + 1.5
    y0c = (ly - SQ_W / 2 - CROSS_GROOVE_IN) if syg > 0 else (ly - SQ_W / 2 - 1.0)
    mid = mid_ridge_cut(egx, syg)        # main: service_slide + the signal corner's own give
    for i, dx in enumerate(_cross_x(egx, station)):
        c = mid if i == 0 else 0.0             # the MIDDLE ridge's inboard end (above)
        if c >= SQ_W - 1e-9:
            continue
        negs.append(_groove(Lc - c).translate((station + dx, y0c + (c if syg > 0 else 0.0),
                                               z_bot)))
    # (the 45 deg OVERHANG RELIEF went with the end-wall rebate it relieved -- there is no
    #  rebate roof left over a tongue, because there is no tongue.)
    return negs


def pinned_tenon_offsets(station: float, ly: float, egx: float, syg: float) -> list:
    """This corner's tenon offsets from the leg's centreline, outboard first.

    Asks chassis.foot_tenon_runs, which is the one authority on which runs a foot can actually
    use -- so a tenon the foot had to give up (the string access channels take two from the
    +X/+Y corner) is not one the pin will aim at. Imported at call time because chassis imports
    THIS module while it loads."""
    from . import chassis as _CHP
    return sorted((egx * (st - station) for st, _, _ in _CHP.foot_tenon_runs(station, ly, syg)),
                  reverse=True)


def pin_tenons(station: float, ly: float, egx: float, syg: float, tip: float) -> list:
    """The tenons a pin `tip` deep finishes INSIDE, as (offset from the centreline, y0, y1).

    Both halves of the question in one place: the X test (does the tip stop in tenon material
    rather than in a mortise void or a 3.2 chassis wall) and the Y RUN that tenon actually has,
    which is what decides whether a service hole can go in it. Both come from
    chassis.foot_tenon_runs, the one authority on a foot's runs."""
    from . import chassis as _CHP          # call time: chassis imports THIS module while it loads
    out = []
    for st, y0, y1 in _CHP.foot_tenon_runs(station, ly, syg):
        o = egx * (st - station)
        if (SQ_W / 2 - (o + D.LEVER_MORT_W / 2)) + D.MIN_WALL <= tip                 <= SQ_W / 2 - (o - D.LEVER_MORT_W / 2):
            out.append((o, y0, y1))
    return out


def lock_pin_joint(station: float, ly: float, egx: float, syg: float, z_bot: float,
                   dy: float = 0.0) -> _ScrewJoint:
    """THE LEG'S ONE SCREW (user), defined once for every part it crosses: an M4 button
    head recessed in the ENDPLATE's end face, a heat-set insert in that same endplate wall,
    and clearance on through the shell gap, the chassis floor and into the foot's OUTERMOST
    TENON -- which it pins. That is the whole retention now: it locks the leg in the body (the
    tenon cannot slide in Y past the pin) and the endplate to the chassis.

    THE INSERT MOVED OUT OF THE CHASSIS (user, 2026-09-17). Holding it there meant the chassis
    had to keep a mortise-free zone for the pocket, and once the grid ran end to end the pocket
    broke into a mortise anyway (97 mm3 of it). With the insert in the endplate -- in the
    material the straight tongue used to occupy -- the chassis only ever sees a Ø4.4 clearance
    hole, which is what the user asked for: a smaller hole disrupts the joinery less.

    On the axis LOCK_PIN_DY outboard of the leg's centreline, LOCK_Z up; `dy` moves it along Y,
    which is how the SERVICE hole is drilled (service_pin_joint)."""
    zc = z_bot + LOCK_Z
    entry = (station + egx * SQ_W / 2, ly + syg * LOCK_PIN_DY + dy, zc)
    end_at = LOCK_RECESS + LOCK_SCREW_L + 0.4
    j = _ScrewJoint(_M4, entry, (-egx, 0.0, 0.0), LOCK_SCREW_L,
                    insert_at=LOCK_INSERT_AT, end_at=end_at,
                    head_d=LOCK_HEAD_D, head_h=LOCK_HEAD_H, recess=LOCK_RECESS)
    # IT MUST FINISH INSIDE ONE OF THIS CORNER'S TENONS. The screw is a PIN now, not a pull on
    # an insert in the chassis, so the tip has to stop in tenon material -- in ANY of them, since
    # on most corners it runs through the outboard ones on the way. A tip parked in a mortise
    # void or in a 3.2 chassis wall would pin nothing.
    tip = LOCK_RECESS + LOCK_SCREW_L
    landed = pin_tenons(station, ly, egx, syg, tip)
    assert landed, (
        "the lock pin's tip lands %.2f in from the end face at corner (%.1f, %.1f), which is "
        "not inside any of its tenons (offsets %s) -- pick a stocked length that finishes in one"
        % (tip, station, ly, [round(o, 2) for o in
                              pinned_tenon_offsets(station, ly, egx, syg)]))
    return j


def service_pin_joint(station: float, ly: float, egx: float, syg: float, z_bot: float):
    """THE SECOND HOLE (user, 2026-09-17): the same screw, the same insert, the SAME AXIS -- it
    is the foot that moved. Slid SERVICE_SLIDE outboard, the hole that lines up with the pin is
    that far INBOARD in the foot's own material, so this is just lock_pin_joint with
    dy = -syg * slide. None at the corners that have no slide.

    IT CAN ONLY LAND IN A FULL-LENGTH TENON, and that is not a coincidence -- it is the same
    fact twice. A tenon over a foot stops short exactly where something drops through the floor
    (the bridge's string channels, the keyhead's height screws), which is the very thing the
    slide exists to uncover; slid out, those short tenons are outside the body altogether. The
    one tenon whose mortise runs the foot's full 44.8 is therefore both the only one still
    engaged out there (20.2 of it) and the only one that can hold the pin. At both ends that is
    the THIRD station in, which is what sets LOCK_SCREW_L."""
    s = service_slide(egx, syg)
    if not s:
        return None
    y_hole = ly + syg * (LOCK_PIN_DY - s)
    tip = LOCK_RECESS + LOCK_SCREW_L
    wall = _M4.shaft_clr_d / 2 + D.MIN_WALL_2P
    held = [t for t in pin_tenons(station, ly, egx, syg, tip)
            if t[1] + wall <= y_hole <= t[2] - wall]
    assert held, (
        "the service hole at y %.2f (slide %.2f) is not a two-bead wall inside any tenon the "
        "pin's tip reaches at corner (%.1f, %.1f) -- it would hold the foot out on air. The "
        "tenons it reaches run %s" % (y_hole, s, station, ly,
                                      [(round(a, 2), round(b, 2), round(c, 2))
                                       for a, b, c in pin_tenons(station, ly, egx, syg, tip)]))
    return lock_pin_joint(station, ly, egx, syg, z_bot, dy=-syg * s)


def foot_pin_joints(station: float, ly: float, egx: float, syg: float,
                    z_bot: float) -> list:
    """Every hole the leg screw needs in a FOOT: the seated one, plus the service one where the
    corner has a slide. The chassis and the endplate get only the first -- the axis never moves,
    so their hole is the same hole; it is the foot that carries two."""
    js = [lock_pin_joint(station, ly, egx, syg, z_bot)]
    j = service_pin_joint(station, ly, egx, syg, z_bot)
    if j is not None:
        js.append(j)
    return js


def endwall_screw_negatives(station: float, ly: float, egx: float,
                            z_bot: float, print_up, syg: float) -> list:
    """The leg screw's hole in an ENDPLATE (lock_pin_joint), shaped from its print_up."""
    return [lock_pin_joint(station, ly, egx, syg, z_bot).cutter(print_up)]


def lock_pin_dummies(station: float, ly: float, egx: float, syg: float, z_bot: float,
                     k: int) -> list:
    """The leg screw and its insert as assembly dummies, for corner `k`."""
    return lock_pin_joint(station, ly, egx, syg, z_bot).dummies(
        "lock_pin_screw_%d" % k, "lock_pin_insert_%d" % k)


# PRINT ORIENTATION (the record, declared once per part) -- INFERRED, not stated: no
# comment in this module says how the foot prints. The geometry only works one way up
# though. "Z0 = ground", the 44.8-square pad runs z 0..12 and the dovetail above it tapers
# inward going +Z, so built +Z the tenon is self-supporting; built -Z the full pad would
# bridge over the 29.6-wide tenon. Declared on that basis and said out loud, so a reader
# knows this one is read off the shape rather than off the designer.
FOOT_UP = (0.0, 0.0, 1.0)


def leg_foot() -> cq.Workplane:
    """SHARED TPU foot ×4 (user: one look everywhere — the same dovetail
    insert serves the -Y leg blocks AND the pedal bar): 44.8-sq ground pad
    + dovetail tenon sliding into the underside mortise from -Y local;
    compression-loaded, TPU-grippy, no fastener. Tenon 31.1 long (y -17.5
    ..FOOT_TENON_Y1): inside the 36.4 BLK_W block faces (and the bar;
    the +Y end still butts the slot's closed end 0.5 beyond it = the Y
    registration), and now clear of the pedal lid's groove — see
    FOOT_TENON_Y1. Z0 = ground."""
    b = box_at(SQ_W, SQ_W, FOOT_H, z=FOOT_H / 2)
    b = b.union(cq.Workplane("XZ")
                .polyline([(-14.8, FOOT_H), (-13.3, FOOT_H + 5.8),
                           (13.3, FOOT_H + 5.8), (14.8, FOOT_H)])
                .close().extrude(FOOT_TENON_Y1 + 17.5)
                .translate((0, FOOT_TENON_Y1, 0)))
    return b


