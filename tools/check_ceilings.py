"""Flat-ceiling (unsupported-bridge) checker for a part in ITS print orientation.

  py -3.12 -m tools.check_ceilings                 # every registered part
  py -3.12 -m tools.check_ceilings --only leg_head
  py -3.12 -m tools.check_ceilings --min 50        # only ceilings over 50 mm^2

WHY THIS EXISTS: the overlap gate reports interpenetration and nothing else. It
cannot see a flat roof over open air, and neither can a bead-grid check -- the
leg head's finger well was a 422 mm^2 flat ceiling sitting ON the print bed and
passed every automated check we had. A human spotted it in the viewer.

WHAT COUNTS. A flat ceiling is a PLANAR face whose normal points along the build
axis, AWAY from the bed, sitting back from the part's bed plane -- i.e. material
whose underside is open air parallel to the layers. The slicer must bridge it.

WHAT DOES NOT COUNT, and this is the distinction that matters:

  * 45 degree flanks. A dovetail undercut looks like an overhang to a crude
    point-probe (material inboard, void outboard) but is self-supporting by
    construction -- that is the whole reason the joints use 45. Testing FACE
    NORMALS instead of sampled points separates the two for free: a 45 flank's
    normal is nowhere near the build axis.
  * A pocket that opens AT the bed. That is a hole from layer one, not a
    ceiling; nothing is ever printed over air.

SPAN IS WHAT DECIDES A CEILING, NOT AREA -- and reporting only area is what this tool
got wrong for as long as it has existed. The chassis' worst-looking ceiling was 148 mm^2,
eighteen times over, and every one of them is 0.8 x 185.5: the flat cap at the apex of a
lever mortise's teardrop roof. One bead wide, anchored on both sides, and 185 mm long,
which is the only reason the area is big. A genuinely frightening 12 x 12 bridge is 144
mm^2 and used to sort BELOW it. So the span -- the shorter in-plane extent -- is printed
first and sorted on, and --min-span is the filter you actually want.

(The span comes from the face's bounding box, so it is honest for the strips and slabs
this finds and PESSIMISTIC for an L or a ring, whose box is bigger than anything the
slicer has to bridge. It over-reports rather than under-reports, which is the right way
round for a checker.)

DEPTH IS REPORTED TOO, because it changes what a ceiling means. One at the bed plane
bridges over the plate on layer one -- the worst case, and usually a real defect.
One deep inside a blind pocket bridges over a cavity that is already there; it
may droop, and whether that matters depends on what lives in the cavity. The
tool will not decide that for you, so it prints the depth and lets you judge.

Add a part below with the axis and direction it actually prints in. Getting that
wrong makes the whole report meaningless, so state it next to the part.
"""

from __future__ import annotations

import argparse
import importlib

from src import legs as LG
from src.dimensions import NOZZLE_D as D_NOZZLE

# name -> (builder, build axis 'x'|'y'|'z', bed plane coordinate on that axis,
#          which side the bed is on: +1 if the part's bed face is at MAX coord)
PARTS = {
    # The leg head lies on its +Y face: authored +Y is world -Y once every leg
    # is placed rot 180, so that face is both the bed and the button side.
    "leg_head": (lambda: LG.leg_head(latch=True), "y", None, +1),
    "leg_body_stub_trrs": (LG.leg_body_stub_trrs, "y", None, +1),
}


def _chassis_seg(i):
    """The chassis prints Z-UP, bed at chassis.Z_BOT (the rib/rail bottoms). Built lazily:
    importing src.build costs minutes, and the leg parts above must not pay it.

    The OPAQUE part AND its transparent light band, unioned: they are one printed object in two
    filaments, so the band's groove is not a ceiling -- the second filament fills it as the print
    goes. Checking the opaque half alone reported that groove's roof as a 2159 mm2 bridge."""
    def build():
        from src import build as B
        seg = B.chassis_segments[i]
        light = B.chassis_light[i]
        return seg.union(light) if light.solids().size() else seg
    return build


def _register_chassis():
    from src import chassis as CH
    for i in range(len(CH.SPLIT_X) + 1):
        PARTS[f"chassis_{i}"] = (_chassis_seg(i), "z", None, -1)


_register_chassis()


# ── WHICH PARTS GET CHECKED, AND WHERE THE ORIENTATION COMES FROM ─────────
# This registry used to hold five parts out of the seventy-one src.build prints, each with a
# hand-typed bed plane. Two things were wrong with that. The obvious one is coverage: sixty-six
# printed parts had never been checked for an unsupported ceiling at all. The other is that a
# transcribed orientation is exactly the kind of number this repo has been burned by -- it is
# copied from prose, nothing compares the two, and check_ceilings' own docstring says getting it
# wrong makes the whole report meaningless.
#
# It does not need transcribing. The orientation is ALREADY DECLARED, once per part, as the
# build-direction vector the hole cutters read (src/leg_stack.py: "PRINT ORIENTATION (user) --
# the record, declared once per part"). So the registry NAMES those declarations rather than
# copying them, and a part that is ever re-oriented brings this along with it.
#
# The bed PLANE is derived too: it is the part's own extreme face on the build axis, which is
# what the five hand-typed constants were each spelling out the long way.
DECLARED_UP = {
    "bridge_endplate":   ("src.bridge_endplate", "PRINT_UP"),
    "keyhead_endplate":  ("src.keyhead_endplate", "PRINT_UP"),
    "adjust_sleeve":     ("src.leg_stack", "SLEEVE_UP"),
    "fixed_sleeve":      ("src.leg_stack", "SLEEVE_UP"),
    "body_adapter":      ("src.leg_stack", "ADAPTER_UP"),
    "adjust_tenon":      ("src.leg_stack", "TENON_UP"),     # diagonal: reported, not checked
    "fixed_tenon":       ("src.leg_stack", "TENON_UP"),     # diagonal: reported, not checked
    "leg_latch_slider":  ("src.leg_stack", "SLIDER_UP"),
    "bar_latch_frame":   ("src.leg_stack", "BAR_FRAME_UP"),
    "bar_latch_collar":  ("src.leg_stack", "BAR_COLLAR_UP"),
    "latch_slider":      ("src.latch", "SLIDER_UP"),
    "pickup_zplate":     ("src.top_plate", "ZPL_UP"),
    "pedal_bar_a":       ("src.pedal_bar", "BAR_UP"),
    "pedal_bar_b":       ("src.pedal_bar", "BAR_UP"),
    "pedal_bar_c":       ("src.pedal_bar", "BAR_UP"),
}
# The deck panels print deck-DOWN on the one declaration -- each as ONE OBJECT with its colour
# layer, so that is the unit checked, exactly as a chassis segment is checked with its light band
# (see _chassis_seg, which learned this the same way). Checking a BASE alone is not a stricter
# test, it is a wrong one: top_plate_4's base has 4056 mm2 of embossed fret line standing 1.6
# proud of a 39350 mm2 deck, so on its own it reads as resting on the fret lines with the whole
# field bridging -- 95 mm of it. The colour layer is what fills that 1.6, and the two go on the
# bed as a single printed object.
for _i in list(range(6)) + ["spare_0", "spare_1", "spare_2"]:
    DECLARED_UP[f"top_plate_{_i}"] = ("src.top_plate", "PIECE_UP")
# ...and the body adapter's three other corners are the SAME part posed to another corner, so
# their world build direction is not ADAPTER_UP and they are deliberately left out until each
# corner's pose declares its own.


def _up_of(name):
    """The declared build direction for `name`, or None if it has never declared one."""
    where = DECLARED_UP.get(name)
    if where is None:
        return None
    return getattr(importlib.import_module(where[0]), where[1])


def _axis_side(up, tol=1e-6):
    """(axis, side) for a build direction, or None when it is not axis-aligned.

    side follows the checker's own convention: +1 when the bed face is at the MAX coordinate,
    which is the case when the part builds toward the MINIMUM -- so it is the opposite sign to
    the build direction."""
    comps = {"x": up[0], "y": up[1], "z": up[2]}
    big = [k for k, v in comps.items() if abs(abs(v) - 1.0) <= tol]
    if len(big) != 1 or any(abs(v) > tol for k, v in comps.items() if k not in big):
        return None                        # diagonal (the floating tenons) -- no flat bed axis
    ax = big[0]
    return ax, (-1 if comps[ax] > 0 else +1)


# parts that are printed as ONE OBJECT with another part, and so must be checked fused to it
FUSED_WITH = {f"top_plate_{i}": f"top_plate_{i}_color"
              for i in list(range(6)) + ["spare_0", "spare_1", "spare_2"]}


def _src_part(name):
    """A builder for one of src.build's printed parts, imported lazily (src.build costs
    minutes, and the leg parts above must not pay it), fused to whatever prints with it."""
    def build():
        from src import build as B
        part = B.PARTS[name][0]()
        mate = FUSED_WITH.get(name)
        if mate and mate in B.PARTS:
            other = B.PARTS[mate][0]()
            if other.solids().size():
                part = part.union(other)
        return part
    return build


def _register_declared():
    for nm in DECLARED_UP:
        up = _up_of(nm)
        got = _axis_side(up)
        if got is None:
            continue                       # listed in the report as not checkable
        ax, side = got
        PARTS[nm] = (_src_part(nm), ax, None, side)   # None bed = derive from the part


_register_declared()

AX = {"x": 0, "y": 1, "z": 2}


def bed_plane(part, axis: str, side: int):
    """The part's own extreme face on the build axis -- which IS the bed plane, since the part
    lies on it. Derived rather than typed: a hand-written bed constant is one more number that
    goes stale when a datum moves, and a wrong one silently rebases every depth in the report."""
    bb = part.val().BoundingBox() if hasattr(part, "val") else part.BoundingBox()
    lo = (bb.xmin, bb.ymin, bb.zmin)[AX[axis]]
    hi = (bb.xmax, bb.ymax, bb.zmax)[AX[axis]]
    return hi if side > 0 else lo


def ceilings(part, axis: str, bed: float, side: int, tol: float = 1e-6):
    """Planar faces normal to `axis`, facing the bed, set back from it."""
    i = AX[axis]
    out = []
    for f in part.faces().vals():
        try:
            n = f.normalAt()
        except Exception:
            continue                      # non-planar: no flat ceiling to have
        comp = (n.x, n.y, n.z)
        # normal must lie ALONG the build axis (this is what excludes 45s)
        if abs(abs(comp[i]) - 1.0) > tol:
            continue
        if any(abs(c) > tol for j, c in enumerate(comp) if j != i):
            continue
        if comp[i] * side <= 0:           # must face the bed, not away from it
            continue
        c = (f.Center().x, f.Center().y, f.Center().z)
        depth = (bed - c[i]) * side
        if depth > tol:                   # set BACK from the bed plane
            bb = f.BoundingBox()
            ext = [bb.xlen, bb.ylen, bb.zlen]
            span = min(e for j, e in enumerate(ext) if j != i)
            out.append((span, f.Area(), depth, c))
    return sorted(out, reverse=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated part names")
    ap.add_argument("--min", type=float, default=1.0,
                    help="ignore ceilings smaller than this (mm^2)")
    ap.add_argument("--min-span", type=float, default=0.0,
                    help="ignore ceilings that bridge less than this (mm). A span at or "
                         "under one nozzle width is a bead-wide ledge, not a bridge.")
    a = ap.parse_args()

    names = list(PARTS)
    if a.only:
        want = {s.strip() for s in a.only.split(",")}
        names = [n for n in names if n in want]

    total = 0
    for nm in names:
        build, axis, bed, side = PARTS[nm]
        part = build()
        if bed is None:
            bed = bed_plane(part, axis, side)
        found = [c for c in ceilings(part, axis, bed, side)
                 if c[1] >= a.min and c[0] >= a.min_span]
        area = sum(c[1] for c in found)
        worst = max((c[0] for c in found), default=0.0)
        print("%-22s build axis %s, bed at %+.2f : %d ceiling(s), %.1f mm^2, "
              "worst span %.2f mm" % (nm, axis.upper(), bed, len(found), area, worst))
        for span, ar, depth, c in found:
            flag = "  <-- ON THE BED" if depth < 0.6 else ""
            if span <= D_NOZZLE + 1e-6:
                flag += "  (one bead wide: a ledge, not a bridge)"
            print("    span %6.2f mm  %8.1f mm^2  %6.2f mm in from the bed  "
                  "at (%.1f, %.1f, %.1f)%s" % (span, ar, depth, c[0], c[1], c[2], flag))
        total += len(found)
    if not total:
        print("\nno flat ceilings above the threshold.")
    if not a.only:
        _coverage()
    return 0        # advisory: depth decides severity, so this never gates


def _coverage():
    """What this run did NOT look at, said out loud.

    A checker that silently covers five parts out of seventy-one reads exactly like a clean
    bill of health, which is how sixty-six prints went unexamined. The gap is a real one --
    most printed parts have never declared which way up they print -- so it is reported on
    every run rather than left to be noticed."""
    from src import build as B
    printed = set(B.PARTS)
    checked = printed & set(PARTS)
    diagonal = {n for n in DECLARED_UP if n in printed and _axis_side(_up_of(n)) is None}
    undeclared = sorted(printed - set(DECLARED_UP))
    print("")
    print("coverage: %d of %d src.build prints checked" % (len(checked), len(printed)))
    if diagonal:
        print("  %d declare a DIAGONAL build direction, which has no flat bed axis and so "
              "cannot be checked here: %s" % (len(diagonal), ", ".join(sorted(diagonal))))
    if undeclared:
        print("  %d have never declared a print orientation, so there is nothing to check "
              "them against:" % len(undeclared))
        for k in range(0, len(undeclared), 6):
            print("      " + ", ".join(undeclared[k:k + 6]))


if __name__ == "__main__":
    raise SystemExit(main())
