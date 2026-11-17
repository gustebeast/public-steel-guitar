"""THE DIRECT INSTRUMENT'S BODY ADAPTERS (user, 2026-11-17): where the legs meet the body.

"The adapters will have tenons running along X. They slide into the chassis and then the
endplates slide onto them clamping them in place with their steel plate screws."

ONE AT EACH CORNER, under the body/endplate joint: a LEG_W square, its outer faces flush with
the instrument's end and side wall, its top on the underside (the body's and the endplates'
floor, one plane). Each end's joint (the keyhead's x_kj, the +X endplate's x_j) crosses it
about halfway, so its tenons run into both parts:

    body (socket open at the joint, blind inboard) | endplate / keyhead (open at the joint,
                                                     blind outboard)
            ======== tenon ========|======== tenon ========
    [                       adapter                         ]

Fitted: slide the adapters into the body's sockets from its ends, slide each endplate on over
their outer halves, and its four bar screws pull it home -- the adapters are then held in X
between the two blind ends (c each way), and in Z and Y by the tenons' heads.

THE JOINT is the fit-tested nozzle tenon (cadkit.fitted_joint, "N": the adapter PRINTS ALONG X,
ADAPTER_UP, so the profile lies in its layers) in two sockets:
  - the BODY's, mouth down on its bed ("up"), at the N/up long-joint pick BODY_C (as the v1
    endplate's X dovetail, chassis.KH_DT_CLR);
  - the ENDPLATES' (both print along X, so "N"), at the N/N full-length pick END_C. The N/up
    profile's tenon is the same at both clearances (it is sized by the pair, not c), so one tenon
    rides both; the endplates' socket is that profile's cavity at END_C.
TWO TENONS an adapter, a leg's kick being a moment about X either way: one under the side wall's
middle (wall_bar's line: 18 of solid wall under the bar), and its mirror LEG_W/2 the other side of
the adapter's centre, under the 4.8 floor -- so the body carries a RIB there over the socket.

THE LEG HALF is the v1 leg's interface, unchanged (the blind mortise, the latch's pocket and its
mouth chamfer: fit-tested), at each corner -- the redesigned legs meet it. Its numbers and shapes
are inlined below from src/leg_stack.py and src/leg_latch.py as they were at 4b38b97d (both
deleted in the v1 removal, round 2). The signal corner's pogo board is not carried over yet (where
the bus comes down is the brain board's to decide).
"""

from __future__ import annotations

import functools
import math

import cadquery as cq

from . import dimensions as D
from .helpers import box_at

BEAD = D.BEAD
BODY_C = 0.30                       # N/up, long joint (chassis.KH_DT_CLR's pick)
END_C = 0.55                        # N/N, full length (fitted_joint FULL_LENGTH, locked)
HOST_W = 10 * BEAD                  # 8.0 the joint's host slab across Y (as the v1 X dovetail)
DROP = 1.0                          # each socket carried this far past its open face
END_WALL = 2 * BEAD                 # each socket's blind end past the tenon's tip, beyond its c
RIB_HW = 13 * BEAD / 2              # the floor rib over an inboard socket: 10.4 wide
RIB_WALL = 2 * BEAD                 # ...and its top over the socket's roof
RAMP = 1.5                          # the tenons' outer ends: run along X per rise (see _tenons)


# ── THE LEG HALF (inlined 2026-11-17 from leg_stack / leg_latch at 4b38b97d) ───────────────────
# The leg's SECTION: a LEG_W square sleeve round an octagon mortise TEN_W across flats, its corners
# chamfered to CHAM faces, turned 45 deg (an apex where a side-printed part's top is, so the roof is
# two 45 faces), the tenon's slide fit FIT a face (leg_stack, square-leg rounds; the octagon's 1.6
# faces because sharp corners bound in the fit coupons).
LEG_W = 56 * BEAD                   # 44.8
TEN_W = 30 * BEAD                   # 24.0
CHAM = 2 * BEAD                     # 1.6
FIT = 0.30
ADAPT_L = 52.8                      # the adapter's height: its top to the sleeve's butt face
ROOF_D = 12.8                       # the blind mortise's roof below the top
# THE LATCH (leg_latch): the retention POCKET the leg's sprung hook clicks into -- its flat ledge is
# what the leg hangs on -- and a 45 deg chamfer round the mortise's mouth across the latch band so
# the hook's printed stairs ride in. All toward +Y (BUTTON_SIDE), the same at every corner.
BUTTON_SIDE = 1.0
BAND_W = 16 * BEAD                  # 12.8 the latch band across X
POCKET_R = 19.74482681718907        # the pocket's reach from the axis
LEDGE_D = 47.2                      # the ledge's depth below the top
LEAD_D = 40.8                       # ...and the pocket's top end
LATCH_CLR = 0.25
FACE_R = 28 * BEAD                  # 22.4 the chamfer's band reach (the sleeve's face)
MOUTH_CH = 3 * BEAD                 # 2.4
_K = math.sqrt(0.5)


def _oct_pts(w: float, cx: float, cy: float, lift: float = 0.0) -> list:
    """The octagon (w across flats, CHAM faces) turned 45 deg on (cx, cy), lifted +Y by lift:
    leg_stack.octagon's perimeter walk (a wrong walk self-crosses and still extrudes)."""
    h, c = w / 2.0, CHAM / math.sqrt(2.0)
    sq = [(h - c, h), (-(h - c), h), (-h, h - c), (-h, -(h - c)),
          (-(h - c), -h), (h - c, -h), (h, -(h - c)), (h, h - c)]
    return [(cx + _K * (x - y), cy + _K * (x + y) + BUTTON_SIDE * lift) for x, y in sq]


def _mortise_cutter(cx: float, cy: float, z0: float, z1: float) -> cq.Workplane:
    """The blind mortise from z0 up to z1: the tenon's section grown FIT a face."""
    pts = _oct_pts(TEN_W + 2 * FIT, cx, cy)
    return cq.Workplane("XY").polyline(pts).close().extrude(z1 - z0).translate((0, 0, z0))


def _band(cx: float, cy: float, r0: float, r1: float, z0: float, z1: float, w: float) -> cq.Workplane:
    return box_at(w, r1 - r0, z1 - z0, x=cx, y=cy + BUTTON_SIDE * (r0 + r1) / 2.0, z=(z0 + z1) / 2.0)


def _bore_wire(cx: float, cy: float, z: float, lift: float) -> cq.Wire:
    pts = [cq.Vector(x, y, z) for x, y in _oct_pts(TEN_W + 2 * FIT, cx, cy, lift)]
    return cq.Wire.makePolygon(pts + [pts[0]])


def _leg_half(cx: float, cy: float, top: float) -> cq.Workplane:
    """The adapter's leg half on (cx, cy) from its top down ADAPT_L: the blind mortise open at the
    butt face, the latch's pocket, and the mouth's chamfer across the latch band."""
    butt = top - ADAPT_L
    b = box_at(LEG_W, LEG_W, ADAPT_L, x=cx, y=cy, z=top - ADAPT_L / 2.0)
    b = b.cut(_mortise_cutter(cx, cy, butt - 1.0, top - ROOF_D))
    b = b.cut(_band(cx, cy, 0.0, POCKET_R, top - LEDGE_D - LATCH_CLR, top - LEAD_D + LATCH_CLR,
                    BAND_W + 2 * LATCH_CLR))
    lo = _bore_wire(cx, cy, butt - 1.0, MOUTH_CH + 1.0)
    hi = _bore_wire(cx, cy, butt + MOUTH_CH, 0.0)
    cone = cq.Workplane("XY").add(cq.Solid.makeLoft([lo, hi], True))
    b = b.cut(cone.intersect(_band(cx, cy, 0.0, FACE_R, butt - 1.0, butt + MOUTH_CH + 0.01,
                                   BAND_W + 2 * LATCH_CLR)))
    return b


def corners() -> list:
    """[(k, ex, ey)]: the four corners, ex/ey the outboard signs (k 0: -X/+Y, then as v1:
    +X/+Y, +X/-Y, -X/-Y)."""
    return [(0, -1, 1), (1, 1, 1), (2, 1, -1), (3, -1, -1)]


@functools.lru_cache(maxsize=None)
def frame() -> dict:
    """The numbers every part reads: the ends, the joints, the side faces, the underside."""
    from . import direct_bench as DB
    (_, _), (y0, y1), (z0, _) = DB.body_box()["outer"]
    e, k = DB.ep_x(), DB.kh_x()
    return dict(x_lo=k["x0"], x_hi=e["x_end"], xj_lo=k["x_kj"], xj_hi=e["x_j"],
                y0=y0, y1=y1, z0=z0, bar_y=DB.bar_y())


def centre(ex: int, ey: int) -> tuple:
    f, W = frame(), LEG_W
    cx = f["x_hi"] - W / 2 if ex > 0 else f["x_lo"] + W / 2
    cy = f["y1"] - W / 2 if ey > 0 else f["y0"] + W / 2
    return cx, cy


def stations(ey: int) -> tuple:
    """The two tenons' y at a side: under the wall's middle, and its mirror about the adapter."""
    f = frame()
    yo = f["bar_y"][1] if ey > 0 else f["bar_y"][0]
    cy = centre(1, ey)[1]
    return yo, 2 * cy - yo


def tenon_x(ex: int) -> tuple:
    """The tenons' run along X (x_in, x_out): END_WALL + c inside each end of the adapter."""
    cx, W = centre(ex, 1)[0], LEG_W
    a, b = cx - W / 2, cx + W / 2
    if ex > 0:
        return a + END_WALL + BODY_C, b - END_WALL - END_C
    return b - END_WALL - BODY_C, a + END_WALL + END_C


def joint_x(ex: int) -> float:
    f = frame()
    return f["xj_hi"] if ex > 0 else f["xj_lo"]


@functools.lru_cache(maxsize=None)
def _halves(c: float, length: float):
    """(tenon, cavity); the cavity's mouth carried DROP down past the underside (a clean cut).
    Not fitted_joint's own `drop`: that returns an INVALID solid at every c and length tried
    (2026-11-17) and the body cut from it with it -- so the mouth face is extruded here."""
    from cadkit import fitted_joint as FJ
    ten, cav, S = FJ.halves("N", "up", c, length, 0.0, HOST_W)
    mouth = cav.faces("<Z").vals()
    assert len(mouth) == 1, "the socket's mouth is %d faces" % len(mouth)
    cav = cav.union(cq.Workplane("XY").add(cq.Solid.extrudeLinear(mouth[0], cq.Vector(0, 0, -DROP))))
    assert cav.val().isValid() and len(cav.solids().vals()) == 1, "the socket cutter is broken"
    return ten, cav


def _place(w: cq.Workplane, x0: float, x1: float, y: float) -> cq.Workplane:
    """Joint frame (X 0..L along the slide) -> world: from x0 toward x1 at y, on the underside."""
    z0 = frame()["z0"]
    if x1 >= x0:
        return w.translate((x0, y, z0))
    return w.mirror("YZ").translate((x0, y, z0))


def _tenons(ex: int, ey: int) -> cq.Workplane:
    """The two tenons, their OUTER ends ramped at 45 deg: the adapter builds from its outer end
    (ADAPTER_UP), so a square end there is a 4.8 ceiling over air 2.15 off the bed (print_check);
    ramped, the head steps back as it rises and carries itself. The base still reaches x_out, so
    the endplate's blind socket end still holds the adapter in X."""
    x_in, x_out = tenon_x(ex)
    L = abs(x_out - x_in)
    z0 = frame()["z0"]
    s = 1.0 if ex > 0 else -1.0                      # outboard
    H = 20.0
    # the wedge to take off: past x_out - s * RAMP * (z - z0), above the underside -- steeper than
    # 45 deg in the print, so where it meets the tenon's own 45 deg flanks the edges climb past 45
    # too (at 1:1 they came out at 44)
    wedge = (cq.Workplane("XZ").polyline([(x_out, z0), (x_out + s * (H + 1), z0),
                                           (x_out + s * (H + 1), z0 + H), (x_out - s * RAMP * H, z0 + H)])
             .close().extrude(-50.0).translate((0, -25.0, 0)))
    out = None
    for y in stations(ey):
        t = _place(_halves(BODY_C, round(L, 3))[0], x_in, x_out, y)
        t = t.cut(wedge.translate((0, y, 0)))
        out = t if out is None else out.union(t)
    return out


def socket_body(ex: int, ey: int) -> cq.Workplane:
    """The BODY's two sockets at a corner: from DROP past the joint face, inboard to BODY_C past
    the tenons' inner tips (the cavity's own length, the tenon's plus c)."""
    x_in, _ = tenon_x(ex)
    xj = joint_x(ex)
    s = 1.0 if ex > 0 else -1.0                      # outboard
    x0 = x_in - s * BODY_C                           # the blind end
    x1 = xj + s * DROP                               # past the joint face
    L = abs(x1 - x0)
    out = None
    for y in stations(ey):
        c = _place(_halves(BODY_C, round(L, 3))[1], x0, x1, y)
        out = c if out is None else out.union(c)
    return out


def socket_end(ex: int, ey: int) -> cq.Workplane:
    """The ENDPLATE's (ex +1) or the KEYHEAD's (ex -1) two sockets: from DROP inboard of the
    joint face, outboard to END_C past the tenons' outer tips."""
    _, x_out = tenon_x(ex)
    xj = joint_x(ex)
    s = 1.0 if ex > 0 else -1.0
    x0 = xj - s * DROP
    x1 = x_out + s * END_C
    L = abs(x1 - x0)
    out = None
    for y in stations(ey):
        c = _place(_halves(END_C, round(L, 3))[1], x0, x1, y)
        out = c if out is None else out.union(c)
    return out


def body_ribs(ex: int, ey: int) -> cq.Workplane:
    """The floor rib over the inboard socket: the floor's underside up to RIB_WALL over the
    socket's roof, from the joint face inboard to RIB_WALL past the socket's blind end."""
    f = frame()
    y = stations(ey)[1]
    roof = _halves(BODY_C, 10.0)[1].val().BoundingBox().zmax
    top = f["z0"] + roof + RIB_WALL
    x_in, _ = tenon_x(ex)
    xj = joint_x(ex)
    s = 1.0 if ex > 0 else -1.0
    xa = x_in - s * (BODY_C + RIB_WALL)
    lo, hi = min(xa, xj), max(xa, xj)
    return box_at(hi - lo, 2 * RIB_HW, top - f["z0"], x=(lo + hi) / 2, y=y, z=(f["z0"] + top) / 2)


def adapter(k: int) -> cq.Workplane:
    """Corner k's adapter: the v1 leg half moved here, and its two X tenons on top."""
    _, ex, ey = corners()[k]
    cx, cy = centre(ex, ey)
    return _leg_half(cx, cy, frame()["z0"]).union(_tenons(ex, ey))


def adapter_up(k: int) -> tuple:
    """Builds along X from its outer end face (on the bed): the tenons' profile in the layers."""
    return (-1.0, 0.0, 0.0) if corners()[k][1] > 0 else (1.0, 0.0, 0.0)


def body_cut() -> cq.Workplane:
    out = None
    for _, ex, ey in corners():
        c = socket_body(ex, ey)
        out = c if out is None else out.union(c)
    return out


def body_add() -> cq.Workplane:
    out = None
    for _, ex, ey in corners():
        r = body_ribs(ex, ey)
        out = r if out is None else out.union(r)
    return out


def end_cut(ex: int) -> cq.Workplane:
    """The +X endplate's (ex 1) or the keyhead's (ex -1) sockets, both sides."""
    return socket_end(ex, 1).union(socket_end(ex, -1))


def parts() -> list:
    from cadkit.kept import kept
    return [(f"adapter_{k}", kept(adapter, k)) for k, _, _ in corners()]
