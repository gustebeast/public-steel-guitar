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
def components(live=False):
    """{name: shape} and a line saying where it came from."""
    if live:
        from src import build as B
        return ({n: (w.val() if hasattr(w, "val") else w) for n, w in
                 ((c[0], c[1]) for c in B.collect_components())}, "built here, just now")
    import json
    from cadkit.scratch import shared_cache, read_brep, MANIFEST

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

FLOOR = -71.3               # just under the floor's top face: "the floor and nothing above"
RAIL_PY, RAIL_MY = 55.0, -131.0     # inboard of each rail's inner face (55.55 / -131.55)

# the lever grid under the floor: mortise k is centred GRID_0 + k * GRID_P, 7.2 wide,
# with a 3.2 web to the next. A housing takes eight; the cut is on the far side of the
# web beyond the first and the last, so all eight mortises keep both their walls.
GRID_0, GRID_P, GRID_WEB = -618.103, 10.4, 3.6 + 3.2
LEVER_K = (5, 12)

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


Z_BOT, FIN_TOP, FIN_RUN, FIN_T = -81.85, -8.0, 40.0, 4.8


def _fix_fin(x0, y_face, inboard):
    """A buttress for a cut length of RAIL: 82 mm tall and 10.4 thick, it is a wall in
    the chassis and a reed in a coupon. A triangular fin FIN_T thick, from the bed up the
    rail's inner face (`y_face`, running `inboard` = +1/-1 in Y), at the end of the piece
    FURTHEST from its joint, so the walls round the joint flex exactly as the real ones."""
    def fin(_comps):
        y0 = y_face - inboard * 1.0                       # a millimetre into the rail
        pts = [(y0, Z_BOT), (y_face + inboard * FIN_RUN, Z_BOT), (y0, FIN_TOP)]
        return (cq.Workplane("YZ").polyline(pts).close().extrude(FIN_T)
                .translate((x0, 0, 0)).val())
    return fin


COUPONS = [
    # A. chassis section <-> chassis section: the tee tenon on a section's +X end drops
    #    (-Z) into the next section's rail. One rail of the two: both are the same joint,
    #    and their spacing is the same printer error on both parts. Full tenon length
    #    (64.95), on a foot of real floor so the 82 mm column does not stand alone -- the
    #    -Y rail, because the floor meets that one directly (a trough runs beside the +Y).
    Coupon("seam_tenon", ["chassis_1"],
           [(-233.0, _, _, RAIL_MY, _, _), (-233.0, _, _, -106.0, _, FLOOR)],
           UP_Z, "section seam (tee tenon, drop-in)", fix=_fix_fin(-233.0, -131.55, +1)),
    Coupon("seam_mortise", ["chassis_0"],
           [(_, -175.0, _, RAIL_MY, _, _), (_, -175.0, _, -106.0, _, FLOOR)],
           UP_Z, "section seam (tee mortise) + the deck groove across the seam",
           fix=_fix_fin(-175.0 - FIN_T, -131.55, +1)),

    # B. chassis <-> bridge endplate, +Y corner: the two stacked mushroom tenons the
    #    endplate drops over, the leg screw through the end wall, and under the floor the
    #    three mortises a body adapter slides into along Y (their whole 44.8 run).
    Coupon("corner_bridge_chassis", ["chassis_0"],
           [(-38.0, _, RAIL_PY, _, _, _), (-21.5, _, 20.5, _, _, FLOOR)],
           UP_Z, "endplate tenons (upper + lower), adapter mortises, leg screw",
           fix=_fix_fin(-38.0, 55.55, -1)),
    Coupon("corner_bridge_endplate", ["bridge_endplate"],
           [(_, _, 45.0, _, _, 6.4)],
           DOWN_X, "endplate sockets for both tenons, leg-screw recess + insert pocket"),
    Coupon("corner_adapter", ["body_adapter_1"],
           [(_, _, _, _, -94.0, _)],
           DOWN_Y, "adapter ridges (octagon, slide in along Y) + the screw's hole"),

    # C. chassis <-> keyhead endplate, -Y corner: the same joint printed the other way
    #    up (+X) on the other rail, in the thinner endplate.
    Coupon("corner_keyhead_chassis", ["chassis_2"],
           [(_, -588.0, _, RAIL_MY, _, _), (_, -591.0, _, -112.0, _, FLOOR)],
           UP_Z, "endplate tenons (upper + lower)", fix=_fix_fin(-588.0 - FIN_T, -131.55, +1)),
    Coupon("corner_keyhead_endplate", ["keyhead_endplate"],
           [(_, _, _, -120.0, _, 6.4)],
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
    if name.startswith("test_fit_"):
        from . import fit_finder
        return fit_finder.source_of(name)
    return None


VIEW_LIFT = 160.0          # the scratch view: coupons float this far over their parts


def assembly(live=False):
    """[(name, Workplane)] for the scratch view: every coupon over the place it was cut
    from, mated to its partner, VIEW_LIFT above the instrument so it is not buried in
    the part it is a piece of."""
    comps, _where = components(live)
    from . import fit_finder                      # the thumbnails, in a row in front
    return ([("test_" + c.name, c.build(comps)[0].translate((0, 0, VIEW_LIFT)))
             for c in COUPONS] + fit_finder.assembly())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", action="store_true", help="write src/test/test_*.step")
    ap.add_argument("--live", action="store_true",
                    help="build the instrument here instead of reading the lead's build")
    a = ap.parse_args(argv)
    comps, where = components(a.live)
    report(comps, where, a.export)
    return 0


if __name__ == "__main__":
    sys.exit(main())
