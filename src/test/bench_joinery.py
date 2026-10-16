"""Print coupons for the TEST BENCH's joinery -- every joint a bench part makes.

    py -3.12 -m src.test.bench_joinery            # report only, from the lead's last build
    py -3.12 -m src.test.bench_joinery --export   # ...and write src/test/test_*.step
    py -3.12 -m src.test.bench_joinery --live     # build the instrument here first (minutes)

THE BENCH (user, 2026-10-12) is the chassis sections, the two endplates, the pulleys and
the nut slide inserts: enough to prove the motors and strings, printed so that it can be
built on into the instrument. Before any of it is printed, every joint those parts make
is printed small -- including the joints whose other half is NOT on the bench yet (a deck
panel, a body adapter, a lever housing), because the bench half is being committed now.

A COUPON HERE IS THE REAL PART WITH EVERYTHING AWAY FROM THE JOINT CUT OFF. Nothing is
modelled again: each one is a finished, placed component of the instrument intersected
with one or more boxes. That is what cadkit's coupon rule asks for (share the code) taken
to its end, and it is the only form that is true for this body, where a joint is cut in
chassis.py, re-cut per segment, and re-cut again in build.py after the cradles are fused.

It also settles the print: a coupon is cut with planes square to its part's build
direction and exported in that part's own orientation, so its layers lie as the real
part's do. A cut plane under it is a bed, never an overhang.

THREE THINGS A COUPON MUST NOT GET WRONG (user):
  * LENGTH. A sliding joint is cut at its real engaged length. A stub slides where the
    full run binds.
  * STIFFNESS. Enough of the part stays round the joint that the coupon cannot flex out
    of the way of a fit the real part would bite on. Where two halves of one joint are
    far apart (a deck panel's two tongues, a seam's two rails) they stay at their real
    spacing, tied together.
  * A PRINTABLE SHAPE. Nothing tall and thin: `report()` gives each coupon's height over
    its width half way up (its WAIST -- a wide foot does not excuse a
    thin column standing on it) and flags the slender ones.

FIXTURE GEOMETRY is the one thing here that is not the real part: a tie or a gusset that
holds two cut pieces at their real spacing or stops a column swaying. It is always away
from the joint, it is built by a function named `_fix_*`, and the report counts it.

NOT IN src.build, ON PURPOSE (user: "let's not add them to the lead's tab"). So these
STEPs are only as fresh as the last `--export`; the report prints the build they were
cut from.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import cadquery as cq

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

SLENDER = 3.0             # height over the waist: above this, flag it
CRUMB = 0.02              # a cut-off solid under this share of the coupon is a crumb


FAR = 2000.0              # "to the end of the part"


def _box(b):
    x0, x1, y0, y1, z0, z1 = [(-FAR if i % 2 == 0 else FAR) if v is None else v
                              for i, v in enumerate(b)]
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0)
            .translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)).val())


class Coupon(object):
    """One coupon: `sources` are component names of the placed instrument (fused if
    several -- a deck panel is its base and its colour layer), `boxes` what is kept of
    them, `up` the build direction of the real part, `fix` optional fixture geometry."""

    def __init__(self, name, sources, boxes, up, joint, fix=None, note=""):
        self.name, self.sources, self.boxes = name, tuple(sources), tuple(boxes)
        self.up, self.joint, self.fix, self.note = up, joint, fix, note

    def build(self, comps):
        kept, crumbs = [], []
        for s in self.sources:
            shape = comps[s]
            for b in self.boxes:
                c = shape.intersect(_box(b))
                kept += [x for x in c.Solids()]
        if not kept:
            raise ValueError("%s: nothing of %s lies in its boxes" % (self.name, self.sources))
        body = kept[0] if len(kept) == 1 else kept[0].fuse(*kept[1:]).clean()
        fixture = 0.0
        if self.fix is not None:
            f = self.fix(comps)
            fixture = f.Volume()
            body = body.fuse(f).clean()
        solids = sorted(body.Solids(), key=lambda s: -s.Volume())
        total = sum(s.Volume() for s in solids)
        keep = [s for s in solids if s.Volume() >= CRUMB * total]
        crumbs = [s.Volume() for s in solids if s.Volume() < CRUMB * total]
        out = keep[0] if len(keep) == 1 else cq.Compound.makeCompound(keep)
        return cq.Workplane("XY").newObject([out]), len(keep), crumbs, fixture


# ── the placed instrument the coupons are cut from ──────────────────────────────────
def components(live=False, own=False):
    """{name: shape} and a line saying where it came from: the lead's build, this worktree's
    last `scratch_view --own` build (`own`), or a build run here now (`live`)."""
    if live:
        from src import build as B
        return ({n: (w.val() if hasattr(w, "val") else w) for n, w in
                 ((c[0], c[1]) for c in B.collect_components())}, "built here, just now")
    import json
    from cadkit.scratch import shared_cache, read_brep, MANIFEST

    if own:
        cache = ROOT / ".scratch_cache"

        class _Own(dict):
            def __missing__(self, k):
                self[k] = read_brep(cache / (k + ".brep"))
                return self[k]
        return _Own(), "this worktree's own build (.scratch_cache)"
    cache = shared_cache(ROOT)
    man = json.loads((cache / MANIFEST).read_text(encoding="utf-8"))

    class _Lazy(dict):
        def __missing__(self, k):
            f = cache / (k + ".brep")
            if not f.exists():
                raise KeyError("%s is not in the lead's build #%s" % (k, man.get("build")))
            self[k] = read_brep(f)
            return self[k]
    return _Lazy(), "the lead's build #%s (%s)" % (man.get("build"), str(man.get("commit"))[:8])


# ── the coupons ─────────────────────────────────────────────────────────────────────
# A box is (x0, x1, y0, y1, z0, z1) in the instrument's own frame; None is "to the end of
# the part". The planes are CUTS, not dimensions: each is placed in plain material away
# from the joint, and nothing in the instrument follows from one. The few that have to
# land on a feature say which.
_ = None
UP_Z, DOWN_Z = (0.0, 0.0, 1.0), (0.0, 0.0, -1.0)
UP_X, DOWN_X = (1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)
DOWN_Y = (0.0, -1.0, 0.0)

EP_TOP = -5.5               # an endplate coupon's top: the upper socket's far end (-7.1) and a
                            # two-bead wall past it -- the endplate above that is not joint (user)
# ...and its inboard side: the rail's inner face. The sockets span y 57.6..64 (bridge) and
# -139.5..-134 (keyhead), so this leaves 2+ of wall; inboard of it is the leg screw and the
# endplate's body, not joint (user, 2026-10-16)
EP_BR_Y0, EP_KH_Y1 = 55.5, -131.5
FLOOR = -71.3               # just under the floor's top face: "the floor and nothing above"
RAIL_PY, RAIL_MY = 55.0, -131.0     # inboard of each rail's inner face (55.55 / -131.55)

# the lever grid under the floor: mortise k is centred GRID_0 + k * GRID_P, 7.2 wide,
# with a 3.2 web to the next. A housing takes eight; the cut is on the far side of the
# web beyond the first and the last, so all eight mortises keep both their walls.
GRID_0, GRID_P, GRID_WEB = -618.103, 10.4, 3.6 + 3.2
LEVER_K = (5, 12)

# the seam at -207.3 sits on a grid wall: stations -212.5 / -202.1 flank it. SEAM_K a side
# (a housing's eight, four on each section), cut on the far side of the web beyond the last
SEAM_X, SEAM_K = -207.30345584989846, 4
SEAM_X0 = SEAM_X - (GRID_P / 2.0 + (SEAM_K - 1) * GRID_P) - GRID_WEB
SEAM_X1 = SEAM_X + (GRID_P / 2.0 + (SEAM_K - 1) * GRID_P) + GRID_WEB
# the floor only as long as a housing's tenons (36.4, user: "only long enough to fit a
# lever") from the rail's outer face (-141.95) -- the mortises run on under the rail -- and
# two beads. The housing slides in from the cut end.
SEAM_TEN_L = 36.4
SEAM_Y1 = -141.95 + SEAM_TEN_L + 2 * 0.8
SEAM_FIN_MAX = SEAM_Y1 - (-131.55) - 1.0       # the fin stops a millimetre short of the cut

# THE MINI (user, 2026-10-16: test chassis-to-chassis-to-lever small first -- the seam is
# likely to open a little, and a housing spanning it tolerates only its tenons' 2 x 0.20).
# Two stations a side; the rail cut fifteen beads (user: +4) above the seam relief's 45 (its bottom 8.8
# of tenon is wedge, not head); floor and housing tenons MINI_L long.
MINI_K, MINI_L = 2, 15 * 0.8
MINI_TOP = FLOOR + 8.8 + 15 * 0.8
MINI_X0 = SEAM_X - (GRID_P / 2.0 + (MINI_K - 1) * GRID_P) - GRID_WEB
MINI_X1 = SEAM_X + (GRID_P / 2.0 + (MINI_K - 1) * GRID_P) + GRID_WEB
MINI_Y1 = -141.95 + MINI_L + 2 * 0.8
# the knee housing's tenons sit on stations -566.1 .. -493.3; the mini keeps the first four
# (2 + 2 across the seam) and MINI_L of their length from the deck's -Y edge
HOUS_TEN_Y0, HOUS_S0 = -86.15, -566.1
# SEAM COMPENSATION (user, 2026-10-16: "predict the amount of extra space the joint might add
# and compensate ... slightly under our 1.6 wall"). Measured on fit_plate2's seam halves (N/N,
# c 0.45, seat 0): the tenon pulls back 0.637 (c x sqrt 2 -- its catch is a 45 deg flank)
# before it catches, so the pitch across a seam runs 10.4 (faces pressed) .. 11.04 (pulled).
# Centre that on 10.4: each section's seam face comes in SEAM_COMP and carries its half of
# the joint with it, the walls either side 1.6 -> 1.44; the pitch then runs 10.08 .. 10.72.
# MINI PLATE 1 (user, 2026-10-16), the UNcompensated set at c 0.45: the web across the seam read
# 7.0 against 6.7 between any other two mortises -- 0.3 open, the centre of 0..0.637, so the
# prediction held. The seam is now c 0.40 (it wobbled): it opens 0..0.566, centred by 0.14 a face.
# Round 2 (seam 0.40, lever 0.25): "the lever joints are still a touch tight and the chassis
# joints a touch loose" -> half a step each: seam 0.375 (opens 0..0.530), lever 0.275.
SEAM_OPEN = round(0.375 * 2 ** 0.5, 3)      # 0.530: c x sqrt 2 (the catch is a 45 deg flank)
SEAM_COMP = round(SEAM_OPEN / 4.0, 2)       # 0.13 a face
COMP_SPLIT_Z = -72.5    # under the seam cavity (0.4 under the floor top), over the lever mortises (-73.86)


def compensate(shape, side, e=SEAM_COMP):
    """A seam coupon (world frame) with its seam face moved in by e, its half of the joint
    with it. side -1: the -X section (the tenon stands past the face at SEAM_X; it moves -e).
    side +1: the +X section (the rail above COMP_SPLIT_Z carries the cavity; it moves +e).
    The floor and its lever mortises stay put -- that is the point."""
    s = SEAM_X
    if side < 0:
        keep = shape.intersect(_box((_, s - e, _, _, _, _)))
        move = shape.intersect(_box((s, _, _, _, _, _))).translate(cq.Vector(-e, 0, 0))
    else:
        rail = (_, _, _, -131.55, COMP_SPLIT_Z, _)
        keep = shape.intersect(_box((s + e, _, _, _, _, _))).cut(_box(rail))
        move = shape.intersect(_box(rail)).translate(cq.Vector(e, 0, 0))
    return keep.fuse(move).clean()


# +X end cut as the housing's real -X edge is (user: no deck past the joint): the deck stops
# at the fourth tenon's STEM face; above its root chamfer (0.8, knee_lever.clip_tenon_root)
# the tenon carries on whole to its head's edge
HOUS_Z1_W, TEN_ROOT_CH = -81.85, 0.8         # the mating plane: the chassis underside
_MINI_S3 = HOUS_S0 + 3 * GRID_P
_R3_S7 = HOUS_S0 + 7 * GRID_P
R3_HOUS = [(HOUS_S0 - GRID_WEB, _R3_S7 + 3.2 / 2.0, _, HOUS_TEN_Y0 + 36.4 + 0.05, -86.4, _),
           (HOUS_S0 - GRID_WEB, _R3_S7 + 5.6 / 2.0 + 0.5, _, HOUS_TEN_Y0 + 36.4 + 0.05,
            HOUS_Z1_W + TEN_ROOT_CH, _)]
MINI_HOUS = [(HOUS_S0 - GRID_WEB, _MINI_S3 + 3.2 / 2.0, _, HOUS_TEN_Y0 + MINI_L, -86.4, _),
             (HOUS_S0 - GRID_WEB, _MINI_S3 + 5.6 / 2.0 + 0.5, _, HOUS_TEN_Y0 + MINI_L,
              HOUS_Z1_W + TEN_ROOT_CH, _)]
MIN_WALL = 0.8

DECK_UNDER = -10.4          # the rail strip: the groove (5.46 deep) on 4.9 of solid rail
TIE_Z = (DECK_UNDER, DECK_UNDER + 3.2)      # top 1.7 under the grooves' floor
TIE_W = 8.0


def _fix_rail_ties(comps):
    """THE DUMMY CHASSIS the two rail strips stand in (user): two grooves only test a
    panel if they are held at the rails' real spacing, square, the whole length -- the
    job the floor does 70 mm further down. Three cross-members on the bed, one at each
    end and one in the middle. Under the
    grooves' floor, so nothing of the joint touches them. STIFFER than the real rails,
    which can lean apart at the top: a panel that slides here has not been helped by
    the plastic giving."""
    bb = comps["chassis_1"].BoundingBox()
    x0, x1 = bb.xmin + 4.0, bb.xmax - 8.0 - TIE_W      # inside the section's two ends
    xs = (x0, (x0 + x1) / 2.0, x1)
    bars = [_box((x, x + TIE_W, RAIL_MY - 1.0, RAIL_PY + 1.0) + TIE_Z) for x in xs]
    return bars[0].fuse(*bars[1:])


# the fin only has to stop a rail swaying under the nozzle (user: "we wouldn't need much
# material to keep the object upright"): a two-bead web, braced along its whole edge by the
# rail, to two thirds of the height
Z_BOT = -81.85
FIN_TOP, FIN_RUN, FIN_T = Z_BOT + 2.0 / 3.0 * 81.85, 25.0, 2 * 0.8


def _fix_fin(x0, y_face, inboard, z0=Z_BOT, run=FIN_RUN):
    """A buttress for a cut length of RAIL: 82 mm tall and 10.4 thick, it is a wall in
    the chassis and a reed in a coupon. A triangular fin FIN_T thick, from the bed (or the
    floor's top, `z0`, where the floor under it is mortised) up the rail's inner face
    (`y_face`, running `inboard` = +1/-1 in Y), at the end of the piece FURTHEST from its
    joint, so the walls round the joint flex exactly as the real ones."""
    def fin(_comps):
        y0 = y_face - inboard * 1.0                       # a millimetre into the rail
        pts = [(y0, z0), (y_face + inboard * run, z0), (y0, FIN_TOP)]
        return (cq.Workplane("YZ").polyline(pts).close().extrude(FIN_T)
                .translate((x0, 0, 0)).val())
    return fin


RAIL_MY_C = (-141.95 + -131.55) / 2.0       # the -Y rail's centre line


def _fix_stub_fins(x_far, outward, top_z=FIN_TOP):
    """Two fins for a rail cut down to a STUB at the seam (user: the rail away from the joint
    is not needed) -- it can sway both ways now, so one fin across it on its inner face and
    one along it, off the stub's far end (`x_far`, the floor running on `outward` = -1/+1 in
    X). Both stand on the floor's top, clear of the mortises under it."""
    def fins(_comps):
        across = _fix_fin(x_far if outward < 0 else x_far - FIN_T, -131.55, +1, FLOOR,
                          min(FIN_RUN, SEAM_FIN_MAX))(_comps)
        far = SEAM_X0 if outward < 0 else SEAM_X1
        run = min(FIN_RUN, abs(far - x_far) - 1.0)
        x0 = x_far - outward * 1.0
        pts = [(x0, FLOOR), (x_far + outward * run, FLOOR), (x0, top_z)]
        along = (cq.Workplane("XZ").polyline(pts).close().extrude(FIN_T)
                 .translate((0, RAIL_MY_C + FIN_T / 2.0, 0)).val())
        return across.fuse(along)
    return fins


# the rail kept round the seam: four beads behind the tenon's root (the tenon stands wholly
# past the seam, in the neighbour), two past the far end of the mortise (_SEG_JD, 10.4)
STUB_TEN_X0 = SEAM_X - 4 * 0.8
STUB_MORT_X1 = SEAM_X + 13 * 0.8 + 2 * 0.8


COUPONS = [
    # A. chassis section <-> chassis section AND the lever grid across it (user, 2026-10-16:
    #    "use two pieces both to test the chassis to chassis joint and the knee to chassis"
    #    -- so the seam is also shown to keep the grid's pitch for a housing that spans it).
    #    The tee tenon on a section's +X end drops (-Z) into the next section's -Y rail (the
    #    floor meets that rail directly; a trough runs beside the +Y), at its full length;
    #    the floor under it is the lever grid, SEAM_K stations a side, one tenon length
    #    (SEAM_Y1) long. A knee housing slides in along Y across the seam, and a body
    #    adapter's three ridges in any three of the same mortises. The floor is the foot;
    #    the rail is only a stub round the seam joint, finned both ways.
    Coupon("seam_tenon", ["chassis_1"],
           [(STUB_TEN_X0, _, _, RAIL_MY, _, _), (SEAM_X0, _, _, SEAM_Y1, _, FLOOR)],
           UP_Z, "section seam (tee tenon, drop-in) + SEAM_K lever mortises",
           fix=_fix_stub_fins(STUB_TEN_X0, -1)),
    Coupon("seam_mortise", ["chassis_0"],
           [(_, STUB_MORT_X1, _, RAIL_MY, _, _), (_, SEAM_X1, _, SEAM_Y1, _, FLOOR)],
           UP_Z, "section seam (tee mortise), the deck groove across it, SEAM_K lever mortises",
           fix=_fix_stub_fins(STUB_MORT_X1, +1)),

    # A-mini: the same three parts, short -- does a housing still go on across the seam?
    # (27 tall: the stub needs no fin)
    Coupon("mini_seam_tenon", ["chassis_1"],
           [(STUB_TEN_X0, _, _, RAIL_MY, _, MINI_TOP), (MINI_X0, _, _, MINI_Y1, _, FLOOR)],
           UP_Z, "seam tenon, short, + 2 lever mortises"),
    Coupon("mini_seam_mortise", ["chassis_0"],
           [(_, STUB_MORT_X1, _, RAIL_MY, _, MINI_TOP), (_, MINI_X1, _, MINI_Y1, _, FLOOR)],
           UP_Z, "seam mortise, short, + 2 lever mortises"),
    # ROUND 3 (user, 2026-10-16): "test the full 8 mortise/tenons and the full 36.4mm length" --
    # SEAM_K stations a side on a floor one tenon length long, the rail still the mini's stub
    Coupon("r3_seam_tenon", ["chassis_1"],
           [(STUB_TEN_X0, _, _, RAIL_MY, _, MINI_TOP), (SEAM_X0, _, _, SEAM_Y1, _, FLOOR)],
           UP_Z, "seam tenon, short, + 4 lever mortises, full tenon length"),
    Coupon("r3_seam_mortise", ["chassis_0"],
           [(_, STUB_MORT_X1, _, RAIL_MY, _, MINI_TOP), (_, SEAM_X1, _, SEAM_Y1, _, FLOOR)],
           UP_Z, "seam mortise, short, + 4 lever mortises, full tenon length"),
    Coupon("r3_lever", ["knee_housing"], R3_HOUS,
           UP_Z, "all 8 housing tenons, full 36.4"),
    Coupon("mini_lever", ["knee_housing"], MINI_HOUS,
           UP_Z, "4 housing tenons (2 each side of the seam), MINI_L long"),

    # B. chassis <-> bridge endplate, +Y corner: the two stacked mushroom tenons the
    #    endplate drops over and the leg screw through the end wall. (The three floor
    #    mortises the body adapter takes here are the lever grid's own: A carries them.)
    Coupon("corner_bridge_chassis", ["chassis_0"],
           [(-38.0, _, RAIL_PY, _, _, _)],
           UP_Z, "endplate tenons (upper + lower), leg screw",
           fix=_fix_fin(-38.0, 55.55, -1)),
    Coupon("corner_bridge_endplate", ["bridge_endplate"],
           [(_, _, EP_BR_Y0, _, _, EP_TOP)],
           DOWN_X, "endplate sockets for both tenons"),
    # the adapter's three ridges (x -17.7..8.7, z -82..-75) on a two-bead slab of its plate:
    # the rest of the plate (12 thick, and 16 past the last ridge) is the leg's half.
    # PRINTED RIDGES UP, as the housing's tenons are: the ridge takes the lever's standing
    # layer/layer profile, which the real adapter's DOWN_Y would make nozzle-wise (open)
    Coupon("corner_adapter", ["body_adapter_1"],
           [(-17.7 - 2 * MIN_WALL, 8.7 + 2 * MIN_WALL, _, _, -82.0 - 2 * MIN_WALL, _)],
           UP_Z, "adapter ridges (octagon, slide in along Y): into A's floor mortises"),

    # C. chassis <-> keyhead endplate, -Y corner: the same joint printed the other way
    #    up (+X) on the other rail, in the thinner endplate.
    Coupon("corner_keyhead_chassis", ["chassis_2"],
           [(_, -588.0, _, RAIL_MY, _, _)],
           UP_Z, "endplate tenons (upper + lower)", fix=_fix_fin(-588.0 - FIN_T, -131.55, +1)),
    Coupon("corner_keyhead_endplate", ["keyhead_endplate"],
           [(_, _, _, EP_KH_Y1, _, EP_TOP)],
           UP_X, "endplate sockets for both tenons"),

    # D. deck panel <-> rail tops: BOTH grooves of the longest section at its whole
    #    length, and the LONGEST panel's two tongues at their real spacing (the keyhead
    #    panel, 249.6: 31 longer than the section, so it also shows a panel running on
    #    out of a groove's end). The mid panel is no use here -- the UI opening cuts
    #    every strip that could tie its two edges together.
    Coupon("deck_rails", ["chassis_1"],
           [(_, _, RAIL_PY, _, DECK_UNDER, _), (_, _, _, RAIL_MY, DECK_UNDER, _)],
           UP_Z, "both deck grooves, 218.4 long", fix=_fix_rail_ties),
    Coupon("deck_panel", ["top_plate_4", "top_plate_color_4"],
           [(_, _, RAIL_PY, _, -5.3, _), (_, _, _, RAIL_MY, -5.3, _)]
           + [(x, x + TIE_W, _, _, 3.2, _) for x in (-606.0, -490.0, -374.0)],
           DOWN_Z, "both deck tongues, 249.6 long, tied by three strips of the real slab"),

    # E. knee-lever housing <-> floor: eight octagon tenons into the lever grid, slid in
    #    along Y from outside the -Y rail to the housing's station. The engaged length
    #    is the tenons' own 36.4 wherever the housing is, so the floor is cut to the
    #    station and a housing-length of lead-in, not to the whole 120 mm of travel.
    Coupon("lever_floor", ["chassis_2"],
           [(GRID_0 + LEVER_K[0] * GRID_P - GRID_WEB, GRID_0 + LEVER_K[1] * GRID_P + GRID_WEB,
             -104.0, -24.0, _, FLOOR)],
           UP_Z, "eight floor mortises: the housing's station and its lead-in"),
    Coupon("lever_housing", ["knee_housing"],
           [(_, _, _, -49.7, -86.4, _)],
           UP_Z, "the housing's eight tenons on its own top deck"),

    # F. nut slide inserts <-> keyhead: the slots of strings 7-10 and the four inserts
    #    that fill them -- every SKU (A string 7, B strings 8 and 9, C string 10), and
    #    BOTH B's (user): 8, 9 and 10 have no printed wall between them, each insert
    #    slides against its neighbour, so the three only prove they fit when all three
    #    are in.
    Coupon("insert_slots", ["keyhead_endplate"],
           [(_, _, -46.0, -3.0, -63.0, _)],
           UP_X, "the insert slots of strings 7-10"),
    Coupon("insert_a", ["nut_slide_insert_6"], [(_,) * 6], DOWN_X, "slide insert, SKU A"),
    Coupon("insert_b", ["nut_slide_insert_7"], [(_,) * 6], DOWN_X, "slide insert, SKU B"),
    Coupon("insert_b2", ["nut_slide_insert_8"], [(_,) * 6], DOWN_X,
           "slide insert, SKU B again: string 9, between a B and the C"),
    Coupon("insert_c", ["nut_slide_insert_9"], [(_,) * 6], DOWN_X, "slide insert, SKU C"),
]


def report(comps, where, export=False):
    from cadkit.orientation import PrintOrientation as PO
    from cadkit.step_export import export_print, print_pose
    from tools.web_materials import material_of
    print("coupons cut from %s" % where)
    print("%-28s %-8s %6s  %-22s %7s  %s" % ("coupon", "filament", "cm3", "on the bed, tall",
                                             "h/waist", "notes"))
    total = 0.0
    for c in COUPONS:
        wp, n, crumbs, fixture = c.build(comps)
        po = PO.from_build_dir(c.up, "the build direction of the part it is cut from")
        bb = print_pose(wp, po).val().BoundingBox()
        vol = sum(s.Volume() for s in wp.val().Solids()) / 1000.0
        total += vol
        posed = print_pose(wp, po).val()
        waist = min(bb.xlen, bb.ylen)
        for f in (0.5,):
            z = bb.zmin + f * bb.zlen
            cut = posed.intersect(_box((_, _, _, _, z, z + 0.1)))
            if cut.Volume() > 0:
                sb = cut.BoundingBox()
                waist = min(waist, sb.xlen, sb.ylen)
        ratio = bb.zlen / waist
        notes = []
        if n != 1:
            notes.append("%d SEPARATE SOLIDS" % n)
        if crumbs:
            notes.append("%d crumbs dropped (%.1f mm3)" % (len(crumbs), sum(crumbs)))
        if fixture:
            notes.append("fixture %.1f cm3" % (fixture / 1000.0))
        if ratio > SLENDER:
            notes.append("SLENDER")
        print("%-28s %-8s %6.1f  %5.1f x %5.1f, %5.1f  %7.2f  %s" % (
            c.name, material_of("test_" + c.name), vol, bb.xlen, bb.ylen, bb.zlen, ratio,
            "; ".join(notes)))
        if export:
            export_print(wp, po, str(HERE / ("test_%s.step" % c.name)))
    print("%-28s %-8s %6.1f" % ("TOTAL", "", total))


def source_of(name):
    """The instrument part a coupon (`test_<name>`) is printed as, or None: what it is
    made of and so what colour it is drawn (tools.web_materials). A deck coupon is one
    filament where the panel is two, and takes the SKIN's -- the last source listed."""
    for c in COUPONS:
        if name == "test_" + c.name:
            return c.sources[-1]
    if name.startswith(("test_fit2_", "test_fit3_", "test_corner_r_")):   # PETG-GF plates
        return "chassis_0"
    if name.startswith("test_fit_"):
        from . import fit_finder
        return fit_finder.source_of(name)
    return None


VIEW_LIFT = 160.0          # the scratch view: coupons float this far over their parts


# the tab shows the round on the bench; True adds the bench coupons and rounds 1-2 back
ALL_ROUNDS = False


def assembly(live=False):
    """[(name, Workplane)] for the scratch view: every coupon over the place it was cut
    from, mated to its partner, VIEW_LIFT above the instrument so it is not buried in
    the part it is a piece of."""
    comps = components(live)[0] if ALL_ROUNDS else None
    from . import fit_finder                      # the thumbnails, in a row in front
    from . import fit_round2                      # ...round 2's plates, as they print
    from . import fit_round3                      # ...and round 3's, the one on the bench
    from . import corner_radius                   # ...with the corner-radius rings beside it
    # ON TRIAL IN THIS TAB (user, 2026-10-13): the keyhead as this branch draws it -- the
    # bass stack's roof left open, its outer wall doubled -- under its own name, so it
    # stands in the instrument in place of the lead's and the two tabs can be compared
    from .keyhead_roof_trial import keyhead
    from src.helpers import heal
    shown = (fit_round3.assembly() + corner_radius.assembly()
             + [("keyhead_endplate", heal(keyhead()))])
    if ALL_ROUNDS:
        shown += [("test_" + c.name, c.build(comps)[0].translate((0, 0, VIEW_LIFT)))
                  for c in COUPONS] + fit_finder.assembly() + fit_round2.assembly()
    return shown


# ── a PLATE: several coupons laid out on one bed, as their own exports print ───────────
PLATE_GAP = 5.0                    # between pieces
BED = 250.0                        # usable of the 256 bed

# step 3 (user's joinery sequence): the PETG-GF joints at full length, rows by depth
PLATES = {
    # as drawn, then with SEAM_COMP (user: "print one as is, then one with the compensation")
    "seam_lever_mini": [["mini_seam_tenon", "mini_seam_mortise", "mini_lever"],
                        ["mini_seam_tenon_comp", "mini_seam_mortise_comp"]],   # one lever tests both
    # round 2: seam c 0.40, lever c 0.25 -- the compensated pair only (round 1 measured the
    # uncompensated one) and its lever
    "seam_lever_mini_2": [["mini_seam_tenon_comp", "mini_seam_mortise_comp", "mini_lever"]],
    # round 3: seam 0.375, lever 0.275
    "seam_lever_mini_3": [["r3_seam_tenon_comp", "r3_seam_mortise_comp", "r3_lever"]],
    "full_length_1": [
        ["seam_tenon", "seam_mortise", "corner_bridge_chassis", "corner_adapter"],
        ["corner_keyhead_chassis", ("corner_bridge_endplate", "corner_keyhead_endplate")],
        ["lever_housing"],
    ],
}


def plate(name):
    """One STEP of the plate's coupons, read from their exports (already in print pose) and
    laid out in rows: each row's entries left to right; a tuple is a COLUMN of pieces stacked
    in Y. Every piece keeps its own pose, so its layers lie as the real part's do."""
    def load(n):
        s = cq.importers.importStep(str(HERE / ("test_%s.step" % n))).val()
        bb = s.BoundingBox()
        return s.translate(cq.Vector(-bb.xmin, -bb.ymin, -bb.zmin))
    out, y = [], 0.0
    for row in PLATES[name]:
        x, depth = 0.0, 0.0
        for entry in row:
            col = entry if isinstance(entry, tuple) else (entry,)
            cy, width = y, 0.0
            for n in col:
                s = load(n)
                bb = s.BoundingBox()
                out.append((n, s.translate(cq.Vector(x, cy, 0.0))))
                cy += bb.ylen + PLATE_GAP
                width = max(width, bb.xlen)
            depth = max(depth, cy - PLATE_GAP - y)
            x += width + PLATE_GAP
        assert x - PLATE_GAP <= BED, "%s: a row runs %.1f, past the bed" % (name, x - PLATE_GAP)
        y += depth + PLATE_GAP
    assert y - PLATE_GAP <= BED, "%s: the rows run %.1f, past the bed" % (name, y - PLATE_GAP)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", action="store_true", help="write src/test/test_*.step")
    ap.add_argument("--plate", choices=sorted(PLATES),
                    help="write one plate of already-exported coupons, laid out, as one STEP")
    ap.add_argument("--live", action="store_true",
                    help="build the instrument here instead of reading the lead's build")
    ap.add_argument("--own", action="store_true",
                    help="read this worktree's last `scratch_view --own` build")
    a = ap.parse_args(argv)
    if a.plate:
        from cadkit.step_export import export_step
        pcs = plate(a.plate)
        for n, s in pcs:
            bb = s.BoundingBox()
            print("%-26s x %6.1f..%6.1f  y %6.1f..%6.1f  %.1f tall" % (n, bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zlen))
        path = HERE / ("test_%s_plate.step" % a.plate)
        export_step(cq.Workplane("XY").newObject([cq.Compound.makeCompound([s for _n, s in pcs])]), str(path))
        print("wrote", path)
        return 0
    comps, where = components(a.live, a.own)
    report(comps, where, a.export)
    return 0


if __name__ == "__main__":
    sys.exit(main())
