"""FIT FINDERS: the bench's joints as thumbnail pairs, each at several clearances.

    py -3.12 -m src.test.fit_finder            # the table: which mark is which clearance
    py -3.12 -m src.test.fit_finder --export   # ...and write src/test/test_fit_*.step

PRINT THESE FIRST (user, 2026-10-12). bench_joinery's coupons are the real parts at the
real lengths and cost 500 cm3; they are the LAST check, and it is a waste to print one
to learn that the joint will not start. A fit finder is a few cm3: a STRIP of short
sockets, each cut at a different clearance, and a TOKEN for each -- the matching short
tenon. Try each token in its own socket, pick the clearance that feels right, put that
number in the joint, and only then print the full-length coupon to prove it at length.

WHAT IS SHARED WITH THE REAL PART is the joint, not the solid: every pair here is made by
cadkit's `joint()` from the SAME width, print specs, install direction and site
arguments the part's own module passes (read off that module, never retyped), with only
the clearance changed. `_check_nominal` asserts that the variant at +0.00 IS the part's
joint -- same family, same clearances, same height -- so a joint that is re-specified in
its module fails here rather than leaving a finder that tests the old one.

WHAT IS KEPT TRUE besides the profile:
  * the PRINT DIRECTION of each half, from the joint's own PrintSpec (the report says
    which way up, and the STEPs are exported in that pose);
  * the WALLS round each socket: every cell is as wide as the real host is at the joint
    (a rail, a floor web each side), and cells are joined only by a 0.8 skin on the bed,
    so a socket here can spring open exactly as far as the real one and no further;
  * NOT the length. These answer "does it go together, and how freely"; whether a
    218 mm tongue still slides is what the full-length coupons are for.

READING THEM: a token carries one groove per step, counted from the TIGHTEST (one groove
= the first clearance in the table). A strip's cells run in the same order, and the
tight end is the one with the tab. The insert finders have ONE token: an insert does
not change with its fit, only its slot does.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import cadquery as cq

from cadkit.joinery import joint

HERE = pathlib.Path(__file__).resolve().parent

L = 12.0                    # engagement: enough to feel a slide, short enough to print five
DELTAS = (-0.10, -0.05, 0.0, 0.05, 0.10)      # added to the joint's own clearances
C_MIN = 0.02                # a clearance never goes below this (it is not zero: the two
                            # halves must still be two solids)
GAP = 2.4                   # air between a strip's cells -- the walls flex into it
SKIN = 0.8                  # the bed skin that joins a strip
GROOVE_W, GROOVE_D, GROOVE_P = 0.9, 0.6, 1.8

UP_Z, DOWN_Z, UP_X, DOWN_X = (0, 0, 1.0), (0, 0, -1.0), (1.0, 0, 0), (-1.0, 0, 0)


def _box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0)
            .translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)))


def _clrs(c0, bc0, d):
    return max(C_MIN, round(c0 + d, 3)), max(C_MIN, round(bc0 + d, 3))


def _facing_up(facing, axial=UP_X):
    return {"up": UP_Z, "down": DOWN_Z, "axial": axial}[facing]


def _grooves(body, k, face_x, y0, z0, z1):
    """k+1 vertical grooves on the face x=face_x, starting GROOVE_P in from y0."""
    for j in range(k + 1):
        y = y0 + GROOVE_P * (j + 0.8)
        body = body.cut(_box(face_x - GROOVE_D, face_x + GROOVE_D,
                             y - GROOVE_W / 2, y + GROOVE_W / 2, z0, z1))
    return body


def _strip(cells, pitch, up):
    """Cells (each centred on y=0) set out along Y, tightest first, joined by a skin on
    the bed with a tab past the tight end."""
    placed = [c.translate((0, i * pitch, 0)) for i, c in enumerate(cells)]
    body = placed[0]
    for c in placed[1:]:
        body = body.union(c)
    bb = body.val().BoundingBox()
    hw = (pitch - GAP) / 2.0
    y0, y1 = -hw - 4.0, (len(cells) - 1) * pitch + hw          # the tab is the -4
    if up[2] > 0:
        skin = _box(bb.xmin, bb.xmax, y0, y1, bb.zmin, bb.zmin + SKIN)
    elif up[2] < 0:
        skin = _box(bb.xmin, bb.xmax, y0, y1, bb.zmax - SKIN, bb.zmax)
    else:
        skin = _box(bb.xmin, bb.xmin + SKIN, y0, y1, bb.zmin, bb.zmax)
    return body.union(skin).clean()


def _row(tokens, pitch):
    """Tokens set out along Y as one print job (separate solids)."""
    return cq.Workplane("XY").newObject(
        [cq.Compound.makeCompound([t.translate((0, i * pitch, 0)).val()
                                   for i, t in enumerate(tokens)])])


class Finder(object):
    """One joint family: `make(d)` -> (token, cell) at clearance step d, in the joint's
    local frame; `pitch` between them; which way each prints; what it stands for."""

    def __init__(self, name, what, make, clr, pitch, token_up, cell_up, token_as, cell_as,
                 deltas=DELTAS, one_token=False):
        self.name, self.what, self.make, self.clr = name, what, make, clr
        self.deltas, self.one_token = deltas, one_token
        self.pitch, self.token_up, self.cell_up = pitch, token_up, cell_up
        self.token_as, self.cell_as = token_as, cell_as      # the real part each is printed as

    def build(self):
        pairs = [self.make(k, d) for k, d in enumerate(self.deltas)]
        # an insert is the same insert at every step -- only its slot is cut differently
        # -- so one token tries all five cells and carries no grooves
        return (_row([p[0] for p in pairs][:1 if self.one_token else None], self.pitch),
                _strip([p[1] for p in pairs], self.pitch, self.cell_up))


def _check_nominal(real, mine):
    assert (real.family, real.install) == (mine.family, mine.install), (real.family, mine.family)
    assert abs(real.clearance - mine.clearance) < 1e-9 and \
        abs(real.back_clearance - mine.back_clearance) < 1e-9 and \
        abs(real.height - mine.height) < 1e-6, (
        "the fit finder's +0.00 step is not the part's joint any more: %s vs %s"
        % ((real.clearance, real.back_clearance, real.height),
           (mine.clearance, mine.back_clearance, mine.height)))


def _slide(real, site, host_w, ten_t, mort_t, root, drop):
    """An X-SLIDE joint's pair maker. Local frame (cadkit's): X the slide, Y the width,
    Z the depth -- the tenon's host under z=0, the socket's host over it."""
    def make(k, d):
        c, bc = _clrs(real.clearance, real.back_clearance, d)
        J = joint(length=L, clearance=c, back_clearance=bc, **site)
        if d == 0.0:
            _check_nominal(real, J)
        hw = host_w / 2.0
        token = _box(0, L, -hw, hw, -ten_t, 0).union(J.tenon(root=root, length=L))
        token = _grooves(token, k, 0.0, -hw, -ten_t, -0.1)
        so = getattr(J, "standoff", 0.0)
        cell = (_box(0, L, -hw, hw, so, mort_t)
                .cut(J.mortise(drop=drop, length=L + 2.0).translate((-1.0, 0, 0))))
        return token, cell
    return make


def _drop(real, site, host_w, host_d, root):
    """A DROP-IN (z-install) joint's pair maker. The profile lies in plan: X the depth
    past the seam, Y the width, Z the drop; both halves print +Z."""
    def make(k, d):
        c, bc = _clrs(real.clearance, real.back_clearance, d)
        J = joint(length=L, clearance=c, back_clearance=bc, **site)
        if d == 0.0:
            _check_nominal(real, J)
        hw = host_w / 2.0
        token = _box(-host_d, 0, -hw, hw, 0, L).union(J.tenon(root=root, length=L))
        token = _grooves(token, k, -host_d, -hw, 0.0, L)
        cell = (_box(0, host_d, -hw, hw, 0, L)
                .cut(J.mortise(drop=root + 1.0, length=L + 2.0).translate((0, 0, -1.0))))
        return token, cell
    return make


def _insert(i):
    """A nut slide insert's pair maker: the insert's own plan as a short prism, and that
    plan grown by the clearance as a slot -- which is how nut_block cuts the real one."""
    from src import nut_block as NB
    from src import dimensions as D
    wire = NB._plan_wire(i)
    pb = wire.extrude(1.0).val().BoundingBox()
    cx, cy = (pb.xmin + pb.xmax) / 2.0, (pb.ymin + pb.ymax) / 2.0
    wy, wx = D.MIN_WALL_2P, 3 * D.BEAD            # a printed finger each side; the end walls

    def make(k, d):
        c = max(C_MIN, round(NB._clr(i) + d, 3))
        token = NB._plan_wire(i).extrude(L + 4.0).translate((-cx, -cy, 0))
        cell = (_box(pb.xmin - cx - wx, pb.xmax - cx + wx,
                     pb.ymin - cy - c - wy, pb.ymax - cy + c + wy, 0, L)
                .cut(NB._plan_wire(i).offset2D(c, kind="arc").extrude(L + 2.0)
                     .translate((-cx, -cy, -1.0))))
        return token, cell
    return make, (pb.ymax - pb.ymin) + 2 * (NB._clr(i) + max(DELTAS) + wy) + GAP, NB._clr(i)


def finders():
    from src import chassis as CH
    from src import knee_lever as KL
    from src import dimensions as D
    T = CH.T
    out = []

    # the deck: a panel's tongue (PCTG, printed deck-down) in a rail-top groove
    j = CH.TP_JOINT
    out.append(Finder(
        "deck", "deck panel tongue <-> rail-top groove",
        _slide(j, dict(width=CH.TP_TG_W, tenon=CH._DECK_UP, mortise=CH._RAIL_DOWN,
                       install="+x"),
               host_w=T, ten_t=8 * D.BEAD, mort_t=T, root=1.0, drop=1.0),
        (j.clearance, j.back_clearance), T + GAP,
        _facing_up("up"), _facing_up("down"), "top_plate_color_0", "chassis_0"))

    # the section seam: the tee a section drops onto
    j = CH._SEG_J
    out.append(Finder(
        "seam", "chassis section seam (tee, drop-in)",
        _drop(j, dict(width=CH._SEG_JW, depth=CH._SEG_JD, tenon=CH._UP, mortise=CH._UP,
                      install="-z"),
              host_w=T, host_d=CH._SEG_JD + 3 * D.BEAD, root=CH._SEG_ROOT),
        (j.clearance, j.back_clearance), T + GAP, UP_Z, UP_Z, "chassis_0", "chassis_0"))

    # the endplate: the mushroom on a rail end / shell end, the endplate's socket over it
    j = CH._EP_J
    out.append(Finder(
        "endplate", "chassis <-> endplate (mushroom, the loose tier)",
        # (no fit="loose" here: that tier is how the part ARRIVES at 0.30/0.60, and the
        #  clearances are given outright below -- passing both would double them again)
        _slide(j, dict(width=CH.EP_J_W, tenon=CH._EP_AX, mortise=CH._EP_DN, install="+x",
                       standoff=CH.EP_TOP_CLR),
               host_w=T, ten_t=10 * D.BEAD, mort_t=10 * D.BEAD, root=CH.EP_J_ROOT,
               drop=CH.EP_J_ROOT + 1.0),
        (j.clearance, j.back_clearance), T + GAP,
        _facing_up("axial"), _facing_up("down"), "chassis_0", "bridge_endplate"))

    # the lever grid: a housing's (or a body adapter's) octagon in a floor mortise, with
    # a whole 3.2 web each side of it
    j = KL._lever_joint(L)
    web = D.XBAR - D.LEVER_MORT_W
    out.append(Finder(
        "octagon", "lever housing / body adapter <-> floor mortise (octagon)",
        _slide(j, dict(width=KL._JW, tenon=KL._JUP, mortise=KL._JUP),
               host_w=D.LEVER_MORT_W + 2 * web, ten_t=6 * D.BEAD,
               mort_t=CH.MB.FLOOR_TOP - CH.Z_BOT, root=1.0, drop=1.0),
        (j.clearance, j.back_clearance), D.LEVER_MORT_W + 2 * web + GAP,
        UP_Z, UP_Z, "knee_housing", "chassis_0"))

    # the nut's slide inserts: SKU A between printed fingers, SKU C at the stack fit
    # (the stack fit is 0.06 a side: there is nothing to try below it but line-to-line,
    #  so its steps run upward)
    for name, i, what, ds in (
            ("insert_a", 6, "nut slide insert SKU A <-> its slot", DELTAS),
            ("insert_c", 9, "nut slide insert SKU C <-> its slot (stack fit)",
             (-0.04, 0.0, 0.05, 0.10, 0.15))):
        make, pitch, c0 = _insert(i)
        out.append(Finder(name, what, make, (c0, c0), pitch, DOWN_X, UP_X,
                          "nut_slide_insert_0", "keyhead_endplate", deltas=ds, one_token=True))
    return out


def parts():
    """[(name, Workplane, up, printed-as)] -- every strip and every row of tokens."""
    out = []
    for f in finders():
        tokens, strip = f.build()
        out.append(("fit_%s_tokens" % f.name, tokens, f.token_up, f.token_as))
        out.append(("fit_%s_strip" % f.name, strip, f.cell_up, f.cell_as))
    return out


def source_of(name):
    """The real part a finder piece (`test_fit_*`) is printed as, or None."""
    if not name.startswith("test_fit_"):
        return None
    for f in finders():
        if name == "test_fit_%s_tokens" % f.name:
            return f.token_as
        if name == "test_fit_%s_strip" % f.name:
            return f.cell_as
    return None


def assembly(origin=(-560.0, 150.0, 160.0), step=70.0):
    """[(name, Workplane)] for the scratch view: each family's strip with its tokens
    beside it, in a row in front of the instrument."""
    out = []
    for n, (name, wp, _up, _as) in enumerate(parts()):
        fam, col = divmod(n, 2)
        out.append(("test_" + name,
                    wp.translate((origin[0] + fam * step, origin[1] + col * 90.0, origin[2]))))
    return out


def main(argv=None):
    from cadkit.orientation import PrintOrientation as PO
    from cadkit.step_export import export_print, print_pose
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", action="store_true", help="write src/test/test_fit_*.step")
    a = ap.parse_args(argv)
    fs = finders()
    print("grooves on a token = its place in this table, counted from 1; a strip's cells run "
          "the same way from its tab")
    print("%-10s %-52s %s" % ("finder", "joint", "clearance (lateral / depth face) per step"))
    for f in fs:
        steps = ["%.2f/%.2f%s" % (_clrs(f.clr[0], f.clr[1], d) + ("*" if d == 0 else "",))
                 for d in f.deltas]
        print("%-10s %-52s %s" % (f.name, f.what, "  ".join(steps)))
    print("(* = what the instrument is drawn at today)\n")
    print("%-24s %-8s %6s  %s" % ("piece", "filament", "cm3", "on the bed, tall"))
    from tools.web_materials import material_of
    total = 0.0
    for name, wp, up, _as in parts():
        po = PO.from_build_dir(up, "the build direction of the half it stands for")
        bb = print_pose(wp, po).val().BoundingBox()
        vol = sum(s.Volume() for s in wp.val().Solids()) / 1000.0
        total += vol
        print("%-24s %-8s %6.1f  %5.1f x %5.1f, %5.1f" % (
            name, material_of("test_" + name), vol, bb.xlen, bb.ylen, bb.zlen))
        if a.export:
            export_print(wp, po, str(HERE / ("test_%s.step" % name)))
    print("%-24s %-8s %6.1f" % ("TOTAL", "", total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
