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

THE LEG HALF is leg_stack's, unchanged (the blind mortise, the latch's pocket and its mouth
chamfer: fit-tested), moved from the v1 leg station to each corner. The signal corner's pogo board
is not carried over yet (where the bus comes down is the brain board's to decide).
"""

from __future__ import annotations

import functools

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


def _ls():
    from . import leg_stack as LS
    return LS


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
    f, W = frame(), _ls().LEG_W
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
    cx, W = centre(ex, 1)[0], _ls().LEG_W
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
    LS = _ls()
    from . import leg_latch as LL
    _, ex, ey = corners()[k]
    cx, cy = centre(ex, ey)
    z0 = frame()["z0"]
    b = box_at(LS.LEG_W, LS.LEG_W, LS.ADAPT_L, x=LS.LEG_X, y=LS.LEG_Y,
               z=(LS.Z_BUTT + LS.Z_TOP) / 2.0)
    b = b.cut(LS.mortise_cutter(LS.Z_BUTT - 1.0, LS.Z_MORTISE_ROOF))
    b = b.cut(LL.adapter_pocket())
    b = b.cut(LL.mouth_chamfer())
    b = b.translate((cx - LS.LEG_X, cy - LS.LEG_Y, z0 - LS.Z_TOP))
    return b.union(_tenons(ex, ey))


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
