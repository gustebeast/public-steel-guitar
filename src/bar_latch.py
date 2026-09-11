"""PEDAL BAR -> ADJUST TENON latch: a YOKE that lives in the bar's mortise tower.

WHY NOT leg_latch's SLIDER (user asked for the same SKU first). That slider lets go
by moving its hook INWARD, so it can only hook a part that SURROUNDS the one
carrying it: at the body joint the tenon carries it and the adapter is hooked. Here
the tenon goes INTO the bar, so a slider carried by the bar would have to hook
inward and pressing would drive it deeper. The yoke gets round that by going round
the tenon: the pad is on the -Y side, the hook on the far +Y side, so pressing the
pad (+Y) pulls the hook OUT of the tenon.

THE PAD matches the leg latch (user priority 1): a 20 x 20 plate flush in the -Y
face, centred leg_latch.PAD_X toward +X, so the thumb finds it in the same place.

THE PARTS
  * FRAME: a flat ring in a slot through the tower just under the mouth. The ring's
    +Y bar IS the hook: its inner edge stands HOOK_ENGAGE inside the tenon's +Y
    apex, in a pocket cut across the tenon. The pad plate hangs below the ring.
  * TWO SPRINGS (leg_latch's coil, one SKU for the instrument) in pockets beside
    the ring's +-X arms, pushing lugs under the arms toward -Y. There is no room
    for a spring on the +Y side: the tower wall there is taken by the hook's stroke.
  * The TENON gets a POCKET (the ledge the bar hangs on) and an END CHAMFER (the
    lead-in that cams the hook out as the tenon goes in: push to connect, no button).

LOAD PATH, bar hanging: tenon pocket floor -> hook's lower face -> frame -> the
slot's ROOF -> tower. The ledge is flat, so a pull cannot cam the hook out.

PRINTING. The frame prints TOP FACE DOWN (FRAME_UP): the pad and lugs grow up off
the ring. The tower prints with the bar on its -Y face, so anything in it that faces
-Y is a ceiling: the slot's +Y end is a 45-degree ridge, and the pad recess ends in a
45-degree pyramid (a flat back would be a 20 mm bridge) that opens into the mortise
behind the pad. The pocket in the tenon has its back tilted POCKET_TILT_DEG off the
tenon's 45-degree build so it is not sitting exactly at the limit.

FRAME: world XY about the redesigned leg's axis (leg_stack.LEG_X/LEG_Y). Heights
come from the tower's MOUTH plane, passed in, because the bar is built in its own Z
and posed by leg_stack. Radii run from the axis toward +Y (the hook side).
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import latch as LT
from . import leg_latch as LL
from . import leg_stack as LS
from .helpers import box_at

B = D.BEAD
CLR = LL.CLR                       # sliding clearance, as the leg latch
TEN_R = LL.TEN_R                   # 16.171 axis -> the tenon's apex
BORE_R = LL.BORE_R                 # 16.595 axis -> the mortise's apex
FACE_R = 32 * B                    # 25.6 axis -> the tower's faces (pedal_bar asserts
                                   # TOWER_W / 2 against it)
FRAME_UP = LS.PRINT_UP["bar_latch_frame"]   # top face down (leg_stack keeps the record)

# -- the hook ------------------------------------------------------------------
HOOK_ENGAGE = 4 * B                # 3.2 how far the hook stands inside the tenon's apex
R_TIP = TEN_R - HOOK_ENGAGE        # 12.97 the hook's inner edge at rest
STROKE = 5 * B                     # 4.0 press travel that clears the hook
S_MAX = STROKE + CLR               # where the plate actually stops (see tower_cut)
assert R_TIP + STROKE >= BORE_R + CLR, (
    "pressed, the hook still stands %.2f inside the mortise" % (BORE_R + CLR - R_TIP - STROKE))
HOOK_CH = 1 * B                    # 0.8 chamfer on the hook's top inner edge
TIP_HALF = LS.CHAM / 2.0 + HOOK_ENGAGE + 2 * CLR   # the hook's reach across X, with
                                   # room for the tenon to sit off-centre in its fit
# -- the ring ------------------------------------------------------------------
FRAME_H = 6 * B                    # 4.8 the ring's height
ROOF = 4 * B                       # 3.2 tower above the slot: it carries the bar
ARM_OUT = BORE_R + 4 * B           # the ring's +-X outer faces
Y_HOOK_OUT = TEN_R + CLR           # the +Y bar's outer face (its edges; a ridge rises
                                   # FRAME_H / 2 beyond at mid-height)
# -- the pad -------------------------------------------------------------------
PAD_W = LL.PAD_W                   # 20.0 across X
PAD_H = LL.PAD_FLAT                # 20.0 down from the ring's top
PAD_T = 4 * B                      # 3.2 the plate
PAD_X = LL.PAD_X                   # 3.6 toward +X, as the leg latch (user)
Y_PLATE_IN = -(FACE_R - PAD_T)     # the plate's back face at rest = the ring's -Y face
RECESS_BACK = FACE_R - PAD_T - STROKE   # where the straight recess ends
# -- the springs ---------------------------------------------------------------
SPR_X = 23 * B                     # 18.4 each spring's axis, off the leg axis in X: under
                                   # the arm, so the lug's stem rises straight into it
LUG_Y0 = 5 * B                     # 4.0 each lug's -Y face at rest: far enough along
                                   # that the pocket clears the mortise's flank
STEM_W = 2 * B                     # 1.6 the stem from the arm down to the lug
LUG_L = 4 * B                      # 3.2 lug length along Y
LUG_HALF = LT.SPR_BORE_D / 2.0 - CLR   # the lug's diamond, inside the spring pocket
SPR_REST_L = LT.SPR_FREE - 0.4     # 11.6 installed: light preload, two coils share the press
SPR_PRESS_L = SPR_REST_L - S_MAX
assert SPR_PRESS_L >= LT.SPR_SOLID, "a spring goes solid before the plate stops"
PRELOAD_N = 2 * (LT.SPR_FREE - SPR_REST_L) * LT.SPR_RATE
PRESS_N = 2 * (LT.SPR_FREE - (SPR_REST_L - STROKE)) * LT.SPR_RATE
# -- the tenon's lead-in -------------------------------------------------------
LEAD_DEG = 20.0                    # from the push axis: shallow, because the frame's
                                   # own guide friction is in series with it
TIP_RELIEF = 1 * B
POCKET_TILT_DEG = 10.0


def planes(z_mouth: float) -> dict:
    """Every height, from the tower's mouth plane."""
    z_ct = z_mouth - ROOF                          # slot roof
    z_cb = z_ct - FRAME_H - 2 * CLR                # slot floor
    z_ft, z_fb = z_ct - CLR, z_cb + CLR            # the frame, centred in the slot
    z_s = z_cb - D.MIN_WALL - LT.SPR_BORE_D / 2.0  # spring axes: each pocket a one-bead
                                                   # web under the slot floor
    return dict(z_ct=z_ct, z_cb=z_cb, z_ft=z_ft, z_fb=z_fb, z_s=z_s,
                z_tb=z_mouth - LS.ENGAGE)           # the seated tenon's bottom end


# -- helpers ---------------------------------------------------------------------
def _w(x: float, y: float) -> cq.Vector:
    return cq.Vector(LS.LEG_X + x, LS.LEG_Y + y, 0.0)


def _xy_prism(pts, z0: float, z1: float) -> cq.Workplane:
    """A closed XY polygon (axis-relative) extruded from world z0 to z1."""
    wp = [(LS.LEG_X + x, LS.LEG_Y + y) for x, y in pts]
    return cq.Workplane("XY").workplane(offset=z0).polyline(wp).close().extrude(z1 - z0)


def _yz_prism(pts, x0: float, x1: float) -> cq.Workplane:
    """A closed (y, z) polygon (y axis-relative) extruded across axis-relative x0..x1."""
    plane = cq.Plane(origin=(LS.LEG_X + x0, LS.LEG_Y, 0.0), xDir=(0, 1, 0), normal=(1, 0, 0))
    return cq.Workplane(plane).polyline(pts).close().extrude(x1 - x0)


def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return box_at(x1 - x0, y1 - y0, z1 - z0, x=LS.LEG_X + (x0 + x1) / 2,
                  y=LS.LEG_Y + (y0 + y1) / 2, z=(z0 + z1) / 2)


def _octagon(w: float):
    """The leg's 45-degree octagon of `w` across flats, axis-relative points."""
    h, c = w / 2.0, LS.CHAM / math.sqrt(2.0)
    sq = [(h - c, h), (-(h - c), h), (-h, h - c), (-h, -(h - c)),
          (-(h - c), -h), (h - c, -h), (h, -(h - c)), (h, h - c)]
    k = math.sqrt(0.5)
    return [(k * (x - y), k * (x + y)) for x, y in sq]


def _hull(pts):
    pts = sorted(set((round(x, 9), round(y, 9)) for x, y in pts))
    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (p[1] - out[-2][1])
                                     - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out
    lo, hi = half(pts), half(reversed(pts))
    return lo[:-1] + hi[:-1]


def _opening(z0: float, z1: float) -> cq.Workplane:
    """The ring's inside: the mortise's octagon swept toward -Y by the stop travel
    (so the pressed ring still clears the tenon), cut off at the hook's edge."""
    o = _octagon(LS.TEN_W + 2 * LS.FIT)
    sweep = S_MAX + CLR
    hull = _hull(o + [(x, y - sweep) for x, y in o])
    return _xy_prism(hull, z0, z1).intersect(_box(-40, 40, -40, R_TIP, z0 - 1, z1 + 1))


def _diamond_y(x: float, z: float, half: float, y0: float, y1: float) -> cq.Workplane:
    """A square prism turned 45 degrees, running along Y (a lug that prints)."""
    plane = cq.Plane(origin=(LS.LEG_X + x, LS.LEG_Y + y0, z), xDir=(1, 0, 0), normal=(0, 1, 0))
    return (cq.Workplane(plane).polyline([(half, 0), (0, half), (-half, 0), (0, -half)])
            .close().extrude(y1 - y0))


# -- the moving part -----------------------------------------------------------
def frame(z_mouth: float) -> cq.Workplane:
    """The yoke AT REST: hook in, pad flush."""
    p = planes(z_mouth)
    zb, zt = p["z_fb"], p["z_ft"]
    zm = (zb + zt) / 2.0
    f = _box(-ARM_OUT, ARM_OUT, Y_PLATE_IN, Y_HOOK_OUT, zb, zt)
    # the +Y bar's outer face as a 45-degree ridge, matching the slot's printable end
    f = f.union(_yz_prism([(Y_HOOK_OUT - 0.01, zb), (Y_HOOK_OUT + FRAME_H / 2.0, zm),
                           (Y_HOOK_OUT - 0.01, zt)], -ARM_OUT, ARM_OUT))
    f = f.cut(_opening(zb - 1.0, zt + 1.0))
    # the hook's top inner edge, chamfered so the tenon's lead-in meets a slope
    f = f.cut(_yz_prism([(R_TIP - 0.01, zt + 0.01), (R_TIP + HOOK_CH, zt + 0.01),
                         (R_TIP - 0.01, zt - HOOK_CH)], -TIP_HALF, TIP_HALF))
    # the pad plate, hanging from the ring's -Y face, flush with the tower face
    f = f.union(_box(PAD_X - PAD_W / 2, PAD_X + PAD_W / 2, -FACE_R, Y_PLATE_IN,
                     zt - PAD_H, zt))
    # the spring lugs under the arms, each on a short stem (the pocket's chord at the
    # slot floor is what the stem passes through)
    for sx in (-1.0, 1.0):
        f = f.union(_diamond_y(sx * SPR_X, p["z_s"], LUG_HALF, LUG_Y0, LUG_Y0 + LUG_L))
        f = f.union(_box(sx * SPR_X - STEM_W / 2, sx * SPR_X + STEM_W / 2,
                         LUG_Y0, LUG_Y0 + LUG_L, p["z_s"] + LUG_HALF - D.MIN_WALL, zb + 0.01))
    return f


def springs(z_mouth: float):
    """The two coils at rest, from each lug's +Y face to its pocket floor."""
    p = planes(z_mouth)
    out = []
    for sx in (-1.0, 1.0):
        out.append(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            LT.SPR_OD / 2.0, SPR_REST_L, _w(sx * SPR_X, LUG_Y0 + LUG_L) + cq.Vector(0, 0, p["z_s"]),
            cq.Vector(0, 1, 0))))
    return out


# -- what the tower gives up -----------------------------------------------------
def tower_cut(z_mouth: float) -> cq.Workplane:
    """Cut in the bar's mortise tower: the ring's slot, the pad's recess, the spring
    pockets. Every face that looks toward the bed (-Y) is 45 degrees or a floor."""
    p = planes(z_mouth)
    zb, zt = p["z_cb"], p["z_ct"]
    zm = (zb + zt) / 2.0
    xo = ARM_OUT + CLR
    y_end = Y_HOOK_OUT + S_MAX + 2 * CLR           # the pressed ring's edges, + CLR
    slot = _box(-xo, xo, Y_PLATE_IN - CLR, y_end, zb, zt)
    slot = slot.union(_yz_prism([(y_end - 0.01, zb), (y_end + (zt - zb) / 2.0, zm),
                                 (y_end - 0.01, zt)], -xo, xo))
    # the pad's recess: straight for the plate plus its stroke...
    x0, x1 = PAD_X - PAD_W / 2 - CLR, PAD_X + PAD_W / 2 + CLR
    z0 = p["z_ft"] - PAD_H - CLR
    recess = _box(x0, x1, -(FACE_R + 1.0), -RECESS_BACK, z0, zt)
    # ...then closing at 45 degrees from the sides and bottom, which is also the stop:
    # the plate's edges land on those faces CLR past STROKE (S_MAX). Its TOP stays level
    # with the slot, so no thin wedge of tower is left between the two; it opens into
    # the mortise behind the pad.
    xc, d = (x0 + x1) / 2.0, (x1 - x0) / 2.0 - 0.1
    ya = -RECESS_BACK - 0.01
    def rect(y, k):
        return cq.Wire.makePolygon([
            cq.Vector(LS.LEG_X + x0 + k, LS.LEG_Y + y, z0 + k),
            cq.Vector(LS.LEG_X + x1 - k, LS.LEG_Y + y, z0 + k),
            cq.Vector(LS.LEG_X + x1 - k, LS.LEG_Y + y, zt),
            cq.Vector(LS.LEG_X + x0 + k, LS.LEG_Y + y, zt)], close=True)
    pyramid = cq.Workplane("XY").add(cq.Solid.makeLoft([rect(ya, 0.0), rect(ya + d, d)], True))
    cut = slot.union(recess).union(pyramid)
    # the spring pockets, with room for each lug's travel and a 45-degree end
    for sx in (-1.0, 1.0):
        y0 = LUG_Y0 - CLR
        y_floor = LUG_Y0 + LUG_L + SPR_REST_L
        _flank = (LS.TEN_W + 2 * LS.FIT) / math.sqrt(2.0) - y0      # mortise |x| at y0
        assert SPR_X - LT.SPR_BORE_D / 2.0 - _flank >= D.MIN_WALL_2P, (
            "the spring pocket leaves %.2f to the mortise"
            % (SPR_X - LT.SPR_BORE_D / 2.0 - _flank))
        base = _w(sx * SPR_X, y0) + cq.Vector(0, 0, p["z_s"])
        r = LT.SPR_BORE_D / 2.0
        cut = cut.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            r, y_floor - y0, base, cq.Vector(0, 1, 0))))
        cut = cut.union(cq.Workplane("XY").add(cq.Solid.makeCone(
            r, 0.0, r, base + cq.Vector(0, y_floor - y0 - 0.01, 0), cq.Vector(0, 1, 0))))
        # the lug's stem passes up through the web to the arm: a slot over the lug's
        # travel, ending in a 45-degree point so its end is no ceiling
        hw = STEM_W / 2.0 + CLR
        ys0, ys1 = LUG_Y0 - CLR, LUG_Y0 + LUG_L + S_MAX + CLR
        xs = sx * SPR_X
        cut = cut.union(_xy_prism([(xs - hw, ys0), (xs + hw, ys0), (xs + hw, ys1),
                                   (xs, ys1 + hw), (xs - hw, ys1)],
                                  p["z_s"], zb + 0.01))
    return cut


# -- what the tenon gives up -------------------------------------------------------
def tenon_cut(z_mouth: float) -> cq.Workplane:
    """Cut in the adjust tenon, seated with its end on the mortise floor: the
    retention POCKET across its +Y apex at the ring's height, and the LEAD-IN
    chamfer on its end that cams the hook out on the way in."""
    p = planes(z_mouth)
    t = math.tan(math.radians(POCKET_TILT_DEG))
    # the pocket's back, 2 CLR behind the hook's edge (a hook printed long must still
    # spring fully home) at its +X reach, and DEEPENING toward -X: that tilt turns the
    # back's normal away from the tenon's bed flat (+X+Y), below the 45 limit
    yb = R_TIP - 2 * CLR
    xa = TIP_HALF
    back = [(-40.0, yb - (40.0 + xa) * t), (40.0, yb + (40.0 - xa) * t),
            (40.0, 40.0), (-40.0, 40.0)]
    pocket = _xy_prism(back, p["z_cb"], p["z_ct"])
    # lead-in: from TIP_RELIEF inside the hook's edge at the end, rising at LEAD_DEG
    tl = math.tan(math.radians(LEAD_DEG))
    r0 = R_TIP - TIP_RELIEF
    L = (TEN_R + 1.0 - r0) / tl
    zt = p["z_tb"]
    lead = _yz_prism([(r0 - tl, zt - 1.0), (r0 + tl * L, zt + L), (40.0, zt + L),
                      (40.0, zt - 1.0)], -40.0, 40.0)
    assert zt + L < p["z_cb"] - LS.ENGAGE / 4, "the lead-in runs into the pocket's ledge"
    return pocket.union(lead)
