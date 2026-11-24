r"""NUT ENDPLATE STUDY (user, 2026-11-20): the printed -X endplate that carries the nut flex-clamp.

TWO BANDS (user): a THIN band across the body's whole Y (and Z) section, only as thick in X as the
wall-bar clamp needs (head recess, back wall, gap, pocket), so the chassis runs right out to it and
levers can mount close to the end; and a THICK band, only as wide in Y as the clamp's steel, that
holds every metal part of nut_flex_study (SPRING="head").

PRINT: the -X face on the bed (PRINT_UP +X), as the old v2 keyhead. Every face that looks back at the bed
is 45 deg or a short bridge across one string slot (4.3):
  * the WINDOW: the head plate's pocket, open through the -X face. The floor block and then the plate
    go in through it along +X; the screws and disc stacks follow from -X. The plate's 10 heads sit in
    it, reached with the 2.5 key.
  * the FLOOR POCKET: the floor block's +X end stops on a 45 deg gable (the string tension's stop,
    with the standoffs), on a 2.6 skin that holds the bottom tie heads in through-recesses.
  * the fingers between the string slots start over the plate pocket at 45 deg (they guide the
    shoes and GREENs in Y); the square nuts run in a band cut across them, roofed 45 deg.
  * the standoffs stand in hex pockets, a flat facing +X (the bearing face; a short bridge in the print).
  * nothing +X of the crown: the +X face is GREEN's face (the crown's tangent) top to bottom, and the
    slots run out through it. Past the floor block a slot's floor is the floor stop's lower 45 deg face
    carried on, so it opens low in the face, under the deck stack.

Frame: built in the nut block's local frame (nut_flex_study's), placed at AT. Run:
    PYTHONPATH=. py -3.12 src/test/nut_endplate_study.py        (checks, STEP for print_check)
"""
from __future__ import annotations

import math
import os

import cadquery as cq

from src import dimensions as D
from src import direct_bench as DB
from src import deck_v2 as DK
from src import m3_hardware as M3H
from src.test import nut_flex_study as S
from cadkit.fasteners import stepped_bore_cutter
from cadkit.holes import teardrop_hole

assert S.SPRING == "head" and S.TIES == "z"

PRINT_UP = (1.0, 0.0, 0.0)
AT = (D.NUT_BLOCK_X, 0.0, D.STRING_Z)            # local -> world
W2 = D.MIN_WALL_2P                               # 1.6: every printed wall (user)
CLR = 0.2                                        # steel blocks in their pockets, a side
SLOT_CLR = 0.15                                  # GREEN / SHOE (4.0) in their slots, a side
HEX_CLR = 0.15
HEAD_REC = (S.TS["head_d"] + 0.8, S.TS["head_h"] + 0.4)   # bottom tie heads' through-recess in the skin

# ── X (local) ────────────────────────────────────────────────────────────────────────────────
X0 = S.X_BACK_NEW                                # the bed face
WALL1 = X0 + DB.EP_WASHER[1] + M3H.HEAD_H        # thin band, from the bed: the bar screws' head recess,
WALL0 = WALL1 + DB.EP_WALL                       # the back wall they pull on (8: the load's),
BAR_X0 = WALL0 + DB.EP_GAP                       # the gap, the bar's locating pocket,
X_KJ = BAR_X0 + DB.EP_POCKET                     # and the joint, where the walls and floor end
FX1 = S._floor_sec()[1]                          # the floor block's +X end
X_FRONT = S.X_FRONT                              # GREEN's +X face: the crown's tangent
SLOT_W = S.T_PL + 2 * SLOT_CLR

# ── Z (local) ────────────────────────────────────────────────────────────────────────────────
ZT = DK.TZ - AT[2]                               # the deck's top: the strip's top
# OVER THE STRING AREA the top rises to just under the DATUM (user, 2026-11-22: "extend the endplate as
# close to the datum as possible ... walls between each insert which serve as channels for threading
# strings"; 5.16 of air there before). Outside Y_STR it stays flush with the top panels (ZT).
Y_STR = (-45.7, 45.0)                            # the string area (user)
TOP_GAP = 0.2                                    # under the datum's ground underside: below string 1's
                                                 # .012 (0.30), so it cannot slip over a finger
ZT_STR = S.LAY["ZD"] - TOP_GAP                   # the fingers' top in the string area
Z_CUT = max(ZT, ZT_STR) + 1                      # every cavity open at the top runs out past it
# THE TAIL CHANNELS (user, 2026-11-22: "extend channels at the max string gauge height up until 1.6mm from
# the edge of the endplate. This gives space for the cut string ends to rest"): each slot carried on -X
# through the back wall to W2 short of the bed face, its floor under the heaviest gauge's string.
TAIL_CLR = 0.2
Z_TAIL = S.LAY["ZD"] - S.G_HI - TAIL_CLR         # the channels' floor: the .080's underside, less TAIL_CLR
# 2026-11-22 (user: "1.6mm will make pushing the strings through harder so let's just run them full length
# to the instrument edge"): the channels run OUT through the bed face, no end wall
X_TAIL_END = S.X_BACK_NEW - 1.0                  # past the bed face: open (the cut overshoots 1)
Z_FB = S.ZF - S.FLOOR_H                          # floor block's bottom
ZB = Z_FB - CLR - HEAD_REC[1]                    # the thick band's bottom: the skin under the floor
Z_WIN = (Z_FB - CLR, S.Z_LIP_TOP + CLR)

# ── Y ────────────────────────────────────────────────────────────────────────────────────────
Y_STEEL = S._bar_y() / 2 + CLR                   # floor, plate pockets' half width
YB = Y_STEEL + W2                                # the thick band's half width
Y_NUTS = 4.5 * S.PITCH + S.NUT_S / 2 + SLOT_CLR  # the square nuts' band
HEX_A = S.SO_HEX / 2 + HEX_CLR                   # hex pocket: half across flats (in X: a flat faces +X)
HEX_R = HEX_A / math.cos(math.pi / 6)            # and its corner (on Y)


def W(w):
    return w.translate(AT)


def _box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _xz_prism(pts, y0, y1):
    """A prism of an XZ polygon from y0 to y1."""
    return cq.Workplane("XZ").polyline(pts).close().extrude(-(y1 - y0)).translate((0, y0, 0))


def _xy_prism(pts, z0, z1):
    return cq.Workplane("XY").polyline(pts).close().extrude(z1 - z0).translate((0, 0, z0))


def green_floor_beyond(x):
    """Lowest any GREEN reaches +X of x (the heaviest gauge, dropped open to thread)."""
    g = S.green(dz=-(S.G_HI + S.THREAD_CLR)).val()
    cut = g.intersect(cq.Solid.makeBox(50, 20, 200, cq.Vector(x, -10, -100)))
    return cut.BoundingBox().zmin


ZS2 = green_floor_beyond(FX1 + CLR)              # GREEN's lowest past the floor block's end


# ── the cavities (local) ─────────────────────────────────────────────────────────────────────
def window():
    """The head plate's pocket, open through the bed face: the floor block and plate go in here."""
    return _box(X0 - 1, S.X_WALL_IN, -Y_STEEL, Y_STEEL, *Z_WIN)


def floor_pocket():
    """The floor block's pocket; its +X end a 45 deg gable that stops the block (string tension)."""
    z0, z1 = Z_FB - CLR, S.ZF + CLR
    x1 = FX1 + CLR
    h = (z1 - z0) / 2
    return _xz_prism([(S.X_WALL_IN - 1, z0), (x1, z0), (x1 + h, z0 + h), (x1, z1), (S.X_WALL_IN - 1, z1)],
                     -Y_STEEL, Y_STEEL)


def slot(y):
    """One string's slot (GREEN and SHOE, 4.0 + clearance), open at the top. Over the floor block it
    runs down to the block. Past the block's end its floor is the floor-stop gable's LOWER face carried
    on at 45 deg (the only plastic there grows up from the skin; the fingers each side keep the whole
    gable), so it opens out through the +X face, under the deck stack, low down."""
    a, b = y - SLOT_W / 2, y + SLOT_W / 2
    x1, z0 = FX1 + CLR, Z_FB - CLR
    s = _box(S.X_WALL_IN - 1, x1, a, b, S.ZF, Z_CUT)
    xe = X_FRONT + 1.0
    return s.union(_xz_prism([(x1 - 0.01, z0), (xe, z0 + xe - x1), (xe, Z_CUT), (x1 - 0.01, Z_CUT)], a, b))


def tail_channel(y):
    """String y's tail channel: its slot's width, from the slot's -X end out to X_TAIL_END, its floor
    at Z_TAIL, open at the top. In the print (+X up) its end is a floor and its sides stand upright."""
    return _box(X_TAIL_END, S.X_WALL_IN, y - SLOT_W / 2, y + SLOT_W / 2, Z_TAIL, Z_CUT)


def finger_heads():
    """The fingers (and the side walls) over the plate pocket start at 45 deg from its top: nothing
    under them there but the window."""
    zt = Z_WIN[1]
    h = zt - (S.ZF + CLR) + 1
    return _xz_prism([(S.X_WALL_IN - 1, zt), (S.X_WALL_IN, zt), (S.X_WALL_IN + h, zt - h),
                      (S.X_WALL_IN - 1, zt - h)], -Y_STEEL, Y_STEEL)


def nut_band():
    """The square nuts (5.5, wider than the 4.0 slot) run across every finger. Down to the floor (the
    finger strip under them would be 1.4 and start in mid-air); the +X end one 45 deg face from the
    band's top down to the floor pocket."""
    x0 = S.S_MIN + S.NUT_U - 0.1
    x1 = S.S_MAX + S.NUT_U + 0.05 + S.NUT_M + SLOT_CLR
    z0, z1 = S.ZF, S.Z_SCREW + S.NUT_S / 2 + SLOT_CLR
    return _xz_prism([(x0, z0), (x0, z1), (x1, z1), (x1 + (z1 - z0), z0)], -Y_NUTS, Y_NUTS)


def hex_pocket(x, y):
    """A standoff's pocket: A FLAT FACES +X (user, 2026-11-23), so the string load bears on a face the
    width of the hex's side, not on two corner lines that sink into the plastic. Corners on +-Y. In
    the print (+X up) that flat is a ceiling: a HEX_R-long bridge, which is short."""
    r, a = HEX_R, HEX_A
    pts = [(x + a, y - r / 2), (x + a, y + r / 2), (x, y + r), (x - a, y + r / 2),
           (x - a, y - r / 2), (x, y - r)]
    return _xy_prism(pts, S.ZF - 0.01, Z_CUT)


def head_recess(x, y):
    """A bottom tie's button head, up through the skin from the bottom (teardropped: Z is sideways)."""
    z0 = ZB - 1
    return teardrop_hole(HEAD_REC[0], (Z_FB - CLR) - z0 + 0.01, axis_point=(x, y, z0),
                         axis_dir=(0.0, 0.0, 1.0), print_up=PRINT_UP)


def thick_band():
    return _box(X0, X_FRONT, -YB, YB, ZB, ZT)


def thin_band_world():
    (_, _), (y0, y1), (z0, _) = DB.body_box()["outer"]
    return _box(X0 + AT[0], X_KJ + AT[0], y0, y1, z0, DK.TZ)


def string_area_rise():
    """The string area's walls up to the datum (local): over the thin band and the thick band's
    footprints only, so nothing new stands where the chassis or the deck is. Over the THICK band
    the rise is the band's own full width (+-YB, read, not typed): cut to Y_STR it left a shelf at
    the deck's height on each side (user, 2026-11-23: 0.565 on -Y, 1.26 on +Y, "it should be
    parametric so it can't get out of sync again"). The thin band, which runs on under the deck,
    rises over Y_STR only where that is wider than the thick band (today it is not)."""
    a, b = Y_STR
    w = _box(X0, X_KJ, a, b, ZT - 0.01, ZT_STR)
    return w.union(_box(X0, X_FRONT, -YB, YB, ZT - 0.01, ZT_STR))


def bar_clamp_world():
    """Each wall bar's locating pocket and its two M3 bores (head + washer recess flush in the bed face)."""
    out = None
    xa, w1, w0, kj = (v + AT[0] for v in (X0, WALL1, WALL0, X_KJ))
    for yc in DB.bar_y():
        c = DB._bar_box(yc, w0, kj + 1.0, DB.BAR_CLR)
        for zc in DB.EP_SCREW_Z:
            c = c.union(stepped_bore_cutter([(DB.EP_TUNNEL, w1 - xa + 1.0), (DB.EP_M3_CLR, w0 - w1 + 0.5)],
                                            (xa - 1.0, yc, zc), (1.0, 0.0, 0.0), print_up=PRINT_UP))
        out = c if out is None else out.union(c)
    return out


def endplate():
    """World pose."""
    cut = window().union(floor_pocket()).union(finger_heads()).union(nut_band())
    for i in range(D.N_STRINGS):
        cut = cut.union(slot(D.nut_y(i))).union(tail_channel(D.nut_y(i)))
    for y in (-S.Y_TIE, S.Y_TIE):
        for x in S.X_TIES:
            cut = cut.union(hex_pocket(x, y)).union(head_recess(x, y))
    w = thin_band_world().union(W(thick_band())).union(W(string_area_rise()))
    from src import body_adapter_v2 as BA                 # the -X leg adapters' sockets
    return w.cut(W(cut)).cut(bar_clamp_world()).cut(BA.end_cut(-1))


# ── parts and checks ─────────────────────────────────────────────────────────────────────────
def bar_stub(k):
    """The wall bar's -X end (ghost), from its end into the body."""
    xb = BAR_X0 + AT[0]
    return DB._bar_box(DB.bar_y()[k], xb, xb + 60.0)


def bar_screws():
    out = []
    xa, w1 = X0 + AT[0], WALL1 + AT[0]
    L = min(l for l in DB.M3_STOCK if l >= (BAR_X0 - WALL1) + DB.EP_ENGAGE)
    from src.motor_coupler import cap_screw              # cadkit's headed screw: socket and thread drawn
    for yc in DB.bar_y():
        for zc in DB.EP_SCREW_Z:
            top = w1 - DB.EP_WASHER[1] - M3H.HEAD_H
            out.append(cap_screw("m3", L, (top, yc, zc), (1.0, 0.0, 0.0)))
    return out, L


def bar_washers():
    """The bar screws' washers (EP_WASHER) in their recesses, under the heads, as at the +X end."""
    w1 = WALL1 + AT[0]
    return [DB.cyl_x(DB.EP_WASHER[0], DB.EP_WASHER[1], w1 - DB.EP_WASHER[1], y=yc, z=zc)
            .cut(DB.cyl_x(3.2, DB.EP_WASHER[1] + 1, w1 - DB.EP_WASHER[1] - 0.5, y=yc, z=zc))
            for yc in DB.bar_y() for zc in DB.EP_SCREW_Z]


def parts():
    ps = [("ep_nut", endplate())]
    for nm, wp in S.assembly():
        ps.append((nm, W(wp)))
    ps += [(f"ep_bar_{k}", bar_stub(k)) for k in range(2)]
    scr, _ = bar_screws()
    ps += [(f"ep_m3_{k}", s) for k, s in enumerate(scr)]
    return ps


def report():
    k = DB.kh_x()                                    # the chassis reads its joint there: they must agree
    assert abs(k["x_kj"] - (X_KJ + AT[0])) < 1e-6 and abs(k["x0"] - (X0 + AT[0])) < 1e-6, "kh_x and the study disagree"
    _, L = bar_screws()
    lines = [
        f"bed face (-X) x {X0 + AT[0]:.2f} world",
        f"thin band {X_KJ - X0:.1f} thick: recess {WALL1 - X0:.1f}, wall {WALL0 - WALL1:.1f}, gap {BAR_X0 - WALL0:.1f}, "
        f"pocket {X_KJ - BAR_X0:.1f}; joint x {X_KJ + AT[0]:.2f} (direct_bench.kh_x agrees), bar screws M3x{L:.0f}",
        f"thick band {X_FRONT - X0:.1f} in X x {2 * YB:.1f} in Y, z {ZB + AT[2]:.2f}..{ZT + AT[2]:.2f} world",
        f"string area y {Y_STR[0]}..{Y_STR[1]}: top {ZT_STR + AT[2]:.2f} world, {TOP_GAP} under the datum "
        f"({ZT_STR - ZT:.2f} over the top panels' {ZT + AT[2]:.2f})",
        f"tail channels {SLOT_W:.2f} wide, x {X_TAIL_END + AT[0]:.2f}..{S.X_WALL_IN + AT[0]:.2f} world "
        f"({S.X_WALL_IN - S.X_BACK_NEW:.1f} long, open through the bed face), floor {Z_TAIL + AT[2]:.2f} world "
        f"({S.LAY['ZD'] - Z_TAIL:.2f} under the datum)",
        f"plastic +X of the crown's tangent: {X_FRONT - (S.XC + S.RC):.2f} (the +X face is GREEN's)",
        f"walls: fingers {S.PITCH - SLOT_W:.2f}, nut band to hex {S.Y_TIE - HEX_R - Y_NUTS:.2f}, "
        f"outer slot to hex {S.Y_TIE - HEX_R - (4.5 * S.PITCH + SLOT_W / 2):.2f}, side walls {YB - Y_STEEL:.2f}, "
        f"skin {HEAD_REC[1]:.2f}, "
        f"window top to deck top {ZT - Z_WIN[1]:.2f}, floor gable to +X face "
        f"{X_FRONT - (FX1 + CLR + (S.FLOOR_H + 2 * CLR) / 2):.2f}",
        f"past the floor block GREEN reaches z {ZS2:.2f}; the slot floor there {Z_FB - CLR + X_FRONT - FX1 - CLR:.2f} "
        f"at the +X face (local)",
    ]
    return lines


def overlaps(ps):
    ep = ps[0][1].val()
    bad = []
    for nm, wp in ps[1:]:
        if nm.startswith("nf_string"):
            continue
        v = ep.intersect(wp.val()).Volume()
        if v > 1e-3:
            bad.append((nm, v))
    return bad


if __name__ == "__main__":
    out = os.path.join("out", "nut_flex_study")
    os.makedirs(out, exist_ok=True)
    for ln in report():
        print(" ", ln)
    ps = parts()
    bad = overlaps(ps)
    print(f"  [{'OK' if not bad else 'FAIL'}] endplate overlaps steel: {bad if bad else 'none'}")
    ep = ps[0][1]
    print(f"  endplate volume {ep.val().Volume() / 1000:.1f} cm3, valid {ep.val().isValid()}")
    # print pose: +X build -> +Z up
    pose = ep.rotate((0, 0, 0), (0, 1, 0), -90)
    cq.exporters.export(pose, os.path.join(out, "nut_endplate_print.step"))
    print(f"  wrote {out}/nut_endplate_print.step (print pose, +Z up)")
