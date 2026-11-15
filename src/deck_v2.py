"""THE TOP PANELS FOR THE DIRECT BODY (user, 2026-11-13).

    "top panels that slide onto the instrument along X, are held strongly in place, don't bow
     when reasonable pressure is applied (note pressure can't be applied under the strings
     because you can't reach there) and have cradles that can hold the LED system in place
     without it falling out."

THE STACK, top down (world z). The deck's top is D.DECK_TOP_Z, set by the strings (v1's string to
deck). The LED system takes all the depth the motors leave and no more (user, 2026-11-13): it is
built UP from the highest motor's top, so it never makes the instrument thicker.

    TZ        6.40   the playing surface
    PZ        4.00   the panel's underside (SKIN 2.4, three beads) = the walls' tops
    LED_FACE -3.75   the LEDs' emitting faces: 7.75 of mixing depth under the skin
    BOARD    -6.95 .. -5.35
    LIP_BOT  -9.25   the cradle's lips: MOTOR_CLR (1.6) over the motors' tops (-10.85)

THE FRET LIGHT. Each lit fret (1..24) is a WINDOW through the skin, filled with WHITE PCTG, the
diffuser (user: "adding some opaque white material into the windows"). Between every two lit
frets an opaque CELL WALL hangs from the skin to COMB_CLR over the LEDs (v1's comb), so a fret's
light stays in its own window; the board slides in under the walls. The frets past 24, the markers
and the border are the same white as a shallow inlay (FRET_T deep), unlit. LEDs per fret against
evenness: uniformity_report() (v1's 4 give 3.6 : 1 at this depth; 8 give 1.2 : 1).

THE CRADLE IS SCREWLESS. Two rails hang from the skin, one each side of the board, each with a 45
degree lip under the board's edge (the v1 tilt-in lip's ramp, on both sides: a flat ledge cannot
print deck-down). The rails run through every panel that has board under it, so the board(s)
slide in along X from the -X end once the panels are on, ride the lips, and stop at a STOP wall
after fret 24; the KEYHEAD's nut block then closes the -X end. Nothing else holds it: gravity sits
it on the lips, the skin is LED_GAP over its LEDs.

THE JOINT: THE PANEL CARRIES THE TENON (decided 2026-11-13 for the thinnest instrument, with the
user's leave to re-decide). The panel caps each wall and drops v1's fit-tested deck tongue
(chassis._deck_halves, plate 8 B1, "ideal, low friction and wobble") into a groove down the wall's
centre. Either way round the joint costs no height -- it sits over the walls, where nothing else
is -- so the choice is the print: the panel prints deck-down (PIECE_UP -Z), where a tongue grows
toward the nozzle off its underside and a groove would be a ceiling. The wall's groove prints
mouth-up. The panels slide on from -X with the keyhead off and are trapped between it and the +X
endplate.

STIFFNESS where a hand can press: outboard of the strings, -Y (the forearm) and +Y. Each side
hangs a SKIRT down the wall's inner face (SKIRT_CLR off it) and TRANSVERSE RIBS from the skirt
to the cradle rail, RIB_Z deep. Pressed down, the panel pivots on the wall's inner top edge; the
skirt's foot bears on the wall's face 11.2 under it, so the side regions are cantilevers clamped
at the walls, the ribs their beams. Over the board (under the strings) there is only the skin.

THE UI STATION (ui_panel) sits in the third panel: the skin there thickens to v1's deck bottom
(z 0) so ui_panel's own cutter and cradle land on the deck they were designed for.
"""
from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from . import top_plate as TP                   # first: fret_light imports it back
from . import fret_light as FL
from .helpers import box_at
from cadkit.kept import kept

PIECE_UP = (0.0, 0.0, -1.0)                     # deck-down, as v1's (the top face on the bed)

# ── the stack ───────────────────────────────────────────────────────────────────────────────
TZ = D.DECK_TOP_Z                               # 6.4
SKIN = 3 * D.BEAD                               # 2.4
PZ = TZ - SKIN                                  # 4.0: the panel's underside, the walls' tops
# THE LED SYSTEM TAKES ALL THE DEPTH THE MOTORS LEAVE, AND NO MORE (user, 2026-11-13: "use up the
# vertical space we have for sure, just don't want to make the instrument thicker because of the
# LEDs"). Built UP from the highest motor's top (row 0: Z_TOP + the motor's half-square), a two-bead
# clearance over it: the lips, the board, the LEDs; what is left to the skin is the mixing depth.
from . import direct_bench as _DB               # noqa: E402 (no deck import back at module level)
MOTOR_TOP = _DB.Z_TOP + _DB.M_HALF              # -10.85
MOTOR_CLR = D.MIN_WALL_2P
BOARD_T = FL.BOARD_T                            # 1.6
PLAY = 0.3                                      # the board in its cradle, each side in Y
LIP_LAP = 1.5                                   # the lip under the board's edge
LIP_CAP = D.MIN_WALL                            # one bead under the ramp's tip
LIP_BOT = MOTOR_TOP + MOTOR_CLR                 # -9.25 (the motors span the board's whole width)
BOARD_BOT = LIP_BOT + LIP_LAP + LIP_CAP         # -6.95
BOARD_TOP = BOARD_BOT + BOARD_T                 # -5.35
LED_FACE = BOARD_TOP + FL.LED_H                 # -3.75
LED_GAP = PZ - LED_FACE                         # 7.75: the mixing depth under the skin
STACK_BOT = LIP_BOT                             # the LED system's lowest point (keyhead_v2 reads it)
# THE CELL WALLS: with this much depth a fret's light reaches its neighbours' windows, so an opaque
# wall stands between every two lit frets (v1's comb), from the skin down to COMB_CLR over the LEDs'
# faces -- the board slides in under them. That slot is the only leak between cells.
COMB_CLR = 0.3
RAIL_T = D.MIN_WALL_2P
# THE BOARD'S WIDTH: the rail's outer face stands at the UI module's pocket (ui_panel.deck_cutter,
# -41.90 once the station is moved to the border), so the board is 80.0 -- the fret windows
# (+-FRET_HY 39.8) are all over it. v1's was 70.4 with ramps doing the window ends' light.
RAIL_OUT = 41.9
BOARD_HW = RAIL_OUT - RAIL_T - PLAY             # 40.0
assert BOARD_HW >= TP.FRET_HY, "the board must run under the whole fret window"

# ── the side regions ────────────────────────────────────────────────────────────────────────
SKIRT_T = D.MIN_WALL_2P
SKIRT_CLR = 0.2                                 # off the wall's inner face: a slide, and the play
                                                # the panel takes up before the skirt bears
RIB_T = D.MIN_WALL_2P
RIB_PITCH = 25.0                                # at most, between ribs along X
# 1.2 over the output board's top (-8.2), 3.9 over the motors' (-10.9)
RIB_Z = -7.0
GAP = 0.05                                      # between panels, and off the endplates
SEAM_FRET_CLR = TP.INLAY_W / 2 + D.MIN_WALL_2P  # a seam off any fret line's centre
SEAM_MARK_CLR = TP.MARK_D / 2 + 1.5             # ...and off any marker's centre
PANEL_MAX = 235.0                               # the bed (memory bambu-usable-bed)
LEAD_IN = 0.6                                   # the rails' and lips' lead-in at each -X end

N_LIT = 24                                      # frets with LEDs (fret_led: 24 zones)


def _db():
    from . import direct_bench as DB
    return DB


def _nb():
    from . import nut_block_v2 as NB
    return NB


# ── where things are ────────────────────────────────────────────────────────────────────────
def walls() -> dict:
    """The body's walls in y: outer faces, inner faces, centre lines (where the tongues run)."""
    DB = _db()
    (_, _), (y0, y1), _ = DB.body_box()["outer"]
    (_, _), (b0, b1), _ = DB.body_box()["inner"]
    return dict(y0=y0, y1=y1, b0=b0, b1=b1, c0=(y0 + b0) / 2, c1=(y1 + b1) / 2)


def block_face() -> float:
    """World x of the nut block's +X face: the board's -X stop."""
    return D.NUT_BLOCK_X + _nb().X_FRONT


def block_hw() -> float:
    return _nb().HW


def deck_x() -> tuple:
    """(x_kj, x_j): the deck runs from the keyhead's joint face to the +X endplate's."""
    DB = _db()
    return DB.kh_x()["x_kj"], DB.ep_x()["x_j"]


def pickup_keepout(grow: float = 1.0) -> tuple:
    from .changer_bench import PICKUP_GHOST
    (x0, x1), (y0, y1), (z0, z1) = PICKUP_GHOST
    return (x0 - grow, x1 + grow), (y0 - grow, y1 + grow), (z0 - grow, z1 + grow)


def _ui_shift() -> float:
    return _db().ui_parts()[1]


def ui_cutter() -> cq.Workplane:
    from . import ui_panel as U
    return U.deck_cutter().translate((0.0, _ui_shift(), 0.0))


def ui_mount() -> cq.Workplane:
    from . import ui_panel as U
    return U.deck_mount().translate((0.0, _ui_shift(), 0.0))


def ui_x() -> tuple:
    """The UI station's x span (its cutter and cradle), 2 round."""
    bbs = [w.val().BoundingBox() for w in (kept(ui_cutter), kept(ui_mount))]
    return min(b.xmin for b in bbs) - 2.0, max(b.xmax for b in bbs) + 2.0


def fret_x(n: int) -> float:
    return TP._fret_x(n)


def fret_field_x0() -> float:
    """The fret field's +X end: short of the pickup's opening."""
    return pickup_keepout()[0][0] - 2.0


def frets() -> list:
    """(n, x) of every fret line on the deck: 12-TET from the nut, to the field's +X end, while
    two lines still leave a web between them (top_plate's rule)."""
    out, n = [], 1
    while True:
        fx, nxt = fret_x(n), fret_x(n + 1)
        if fx > fret_field_x0() or nxt - fx < TP.INLAY_W + TP.MIN_WEB:
            return out
        out.append((n, fx))
        n += 1


# FRET 0 IS LIT (user, 2026-11-14, via the lead: "The LED board needs 0 fret LEDs"). The nut line
# itself (fret_x(0) = -615.0) is inside the nut block, so the zero fret's WINDOW is the border's band
# across the block's face, opened through the skin, and its LED row stands just +X of the block face,
# a courtyard's half and 0.2 clear of it -- on the board, which already starts at that face.
def zero_window_x() -> tuple:
    return block_face(), block_face() + TP.INLAY_W


def zero_led_x() -> float:
    return block_face() + FL.LED_CRTYD / 2 + 0.2


def lit_led_xs() -> list:
    """The x of every lit row of LEDs: fret 0's, then frets 1 .. N_LIT."""
    return [zero_led_x()] + [fx for n, fx in frets() if n <= N_LIT]


def board_x() -> tuple:
    """(x0, x1) of the LED board(s): from the nut block's face to past fret 24's LEDs."""
    return block_face(), fret_x(N_LIT) + FL.LED_CRTYD / 2 + 1.0


def stop_x() -> tuple:
    x0 = board_x()[1] + 0.5                     # the board's X play
    return x0, x0 + D.MIN_WALL_2P


def _seam_ok(x: float) -> bool:
    if any(abs(x - fx) < SEAM_FRET_CLR for _, fx in frets()):
        return False
    return all(abs(x - TP._mark_x(n)) >= SEAM_MARK_CLR for n in TP.MARKER_FRETS)


def _snap(target: float, lo: float = -1e9, hi: float = 1e9) -> float:
    for k in range(0, 400):
        for x in (target + 0.1 * k, target - 0.1 * k):
            if lo <= x <= hi and _seam_ok(x):
                return round(x, 2)
    raise ValueError(f"no seam near {target}")


def seams() -> list:
    """Panel boundaries -X -> +X: the keyhead joint, two seams, the UI panel's +X seam, the +X end.
    The UI panel's +X seam is the first marker-free gap past the station; the -X run is split in
    three as evenly as the fret lines allow."""
    _, xe = deck_x()
    xa = deck_x()[0]                            # the panels end at the keyhead strip's +X face
    u0, u1 = ui_x()
    s3 = _snap(u1 + 4.0, lo=u1)
    s1 = _snap(xa + (s3 - xa) / 3)
    s2 = _snap(xa + 2 * (s3 - xa) / 3, hi=u0)
    out = [xa, s1, s2, s3, xe]
    for a, b in zip(out, out[1:]):
        assert b - a <= PANEL_MAX, f"panel {a:.1f}..{b:.1f} is {b - a:.1f} long, over the bed"
    return out


def panel_x(k: int) -> tuple:
    s = seams()
    a = s[k] + (GAP if k == 0 else GAP / 2)
    b = s[k + 1] - (GAP if k == len(s) - 2 else GAP / 2)
    return a, b


N_PANELS = 3                                    # the fret panels; the +X end is deck_v2_region's


# ── the pieces ──────────────────────────────────────────────────────────────────────────────
def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return box_at(x1 - x0, y1 - y0, z1 - z0, x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=(z0 + z1) / 2)


def _yz_prism(pts, x0, x1) -> cq.Workplane:
    return cq.Workplane("YZ", origin=(x0, 0, 0)).polyline(pts).close().extrude(x1 - x0)


def _rail(s: int, x0: float, x1: float) -> cq.Workplane:
    """One side's cradle rail with its lip, x0..x1. s = +1 / -1. The lip's top is a 45 deg ramp
    through the board's nominal bottom corner, so a centred board sits on both."""
    yi = BOARD_HW + PLAY
    pts = [(RAIL_OUT, PZ + 0.01), (yi, PZ + 0.01), (yi, BOARD_BOT + PLAY),
           (BOARD_HW - LIP_LAP, BOARD_BOT - LIP_LAP), (BOARD_HW - LIP_LAP, LIP_BOT),
           (RAIL_OUT, LIP_BOT)]
    w = _yz_prism([(s * y, z) for y, z in pts], x0, x1)
    # THE LEAD-IN at the -X end: the board's leading edge comes in +X and meets this panel's rail
    # a joint's tolerance off the last one's -- a 45 deg chamfer on the rail's face. NOT on the lip:
    # any end cut across a 45 deg lip leaves a ridge under 45 (two 45s meet at 35), so the lip's end
    # stays square and the board's leading bottom edge is chamfered instead (INSTALL_NOTES).
    li = LEAD_IN
    face = (cq.Workplane("XY", origin=(0, 0, LIP_BOT - 1))
            .polyline([(x0 - 0.01, s * (yi - 0.01)), (x0 - 0.01, s * (yi + li)), (x0 + li, s * (yi - 0.01))])
            .close().extrude(PZ - LIP_BOT + 1))
    return w.cut(face)


def _tongues(x0: float, x1: float) -> cq.Workplane:
    from . import chassis as CH
    wl = walls()
    out = None
    for yc in (wl["c0"], wl["c1"]):
        t = CH._deck_tg(yc, x0, x1, mortise=False).translate((0.0, 0.0, PZ))
        out = t if out is None else out.union(t)
    return out.intersect(_box(x0 - 1, x1 + 1, wl["y0"] - 1, wl["y1"] + 1, -50, TZ))


def wall_cutter() -> cq.Workplane:
    """What the body loses for the deck: everything over PZ, and a groove down each wall's
    centre, from the keyhead's joint face to the +X endplate's (open at -X: the panels slide on
    from there, the keyhead closes it)."""
    from . import chassis as CH
    wl = walls()
    xa, xe = deck_x()
    out = _box(xa - 1, xe + 1, wl["y0"] - 1, wl["y1"] + 1, PZ, TZ + 5)
    for yc in (wl["c0"], wl["c1"]):
        out = out.union(CH._deck_tg(yc, xa - 1, xe + 1, mortise=True).translate((0.0, 0.0, PZ)))
    return out


def _rib_xs(x0: float, x1: float, keep_out) -> list:
    """Rib x0's along a panel: one flush at each end, the rest evenly, at most RIB_PITCH apart,
    none in a keep-out span."""
    n = max(1, math.ceil((x1 - x0 - RIB_T) / RIB_PITCH))
    xs = [x0 + k * (x1 - x0 - RIB_T) / n for k in range(n + 1)]
    return [x for x in xs if not any(a - RIB_T < x < b for a, b in keep_out)]


def _side(s: int, x0: float, x1: float, inner: float, keep_out) -> cq.Workplane:
    """One side's skirt and ribs, x0..x1: the skirt down the wall's inner face, the ribs from it
    in to |y| = inner."""
    wl = walls()
    yw = wl["b1"] if s > 0 else wl["b0"]        # the wall's inner face
    ya, yb = yw - s * SKIRT_CLR, yw - s * (SKIRT_CLR + SKIRT_T)
    w = _box(x0, x1, min(ya, yb), max(ya, yb), RIB_Z, PZ + 0.01)
    for xr in _rib_xs(x0, x1, keep_out):
        y_in = s * inner
        w = w.union(_box(xr, xr + RIB_T, min(yb, y_in), max(yb, y_in), RIB_Z, PZ + 0.01))
    return w


def _panel_solid(k: int) -> cq.Workplane:
    """Panel k (0 = the keyhead's), one PCTG body before the inlays come out."""
    wl = walls()
    x0, x1 = panel_x(k)
    # over the keyhead (panel 0, x0 .. x_kj) the panel is the skin alone, sat on the keyhead's slab
    # beside the nut block; the walls, their grooves and so the tongues, skirt and ribs start at x_kj
    xw = max(x0, deck_x()[0] + GAP)
    w = _box(x0, x1, wl["y0"], wl["y1"], PZ, TZ).union(_tongues(xw, x1))
    bx0, _ = board_x()
    sx0, sx1 = stop_x()
    u0, u1 = ui_x()
    (px0, px1), (py0, py1), (pz0, pz1) = pickup_keepout()
    keep_out = [(u0, u1)] if (x0 < u1 and x1 > u0) else []
    # the cradle: rails where there is board, and the stop wall
    ra, rb = max(x0, bx0), min(x1, sx1)
    if rb > ra:
        for s in (1, -1):
            w = w.union(_rail(s, ra, rb))
        inner = RAIL_OUT
    else:
        inner = RAIL_OUT
    if rb > ra:
        w = w.union(_comb(x0, x1))
    if x0 < sx0 < x1:
        w = w.union(_box(sx0, sx1, -(BOARD_HW + PLAY + 0.01), BOARD_HW + PLAY + 0.01, LIP_BOT, PZ + 0.01))
    for s in (1, -1):
        w = w.union(_side(s, xw, x1, inner, keep_out))
    # the UI station: v1's deck depth under its footprint, then its own cutter and cradle
    if keep_out:
        w = w.union(_box(max(x0, u0), min(x1, u1), wl["b0"] + SKIRT_CLR, -RAIL_OUT, 0.0, PZ + 0.01))
        w = w.union(kept(ui_mount)).cut(kept(ui_cutter))
        # the pocket's -Y face reaches 0.1 into the skirt above its floor: take the skirt's face
        # back to it all the way down, so no 0.1 ledge is left under it
        cb = kept(ui_cutter).val().BoundingBox()
        if cb.ymin < wl["b0"] + SKIRT_CLR + SKIRT_T:
            w = w.cut(_box(cb.xmin, cb.xmax, cb.ymin, wl["b0"] + SKIRT_CLR + SKIRT_T + 0.01, RIB_Z - 1, cb.zmin + 0.01))
    # the nut block's notch (panel 0): the block stands through it to the board's -X stop
    if k == 0:
        hw = block_hw() + PLAY
        w = w.cut(_box(x0 - 1, block_face() + GAP, -hw, hw, -50, TZ + 1))
    # the pickup's opening
    if x1 > px0:
        w = w.cut(_box(px0, px1, py0, py1, -50, TZ + 1))
    return w


# ── the white: windows over the lit frets, shallow inlays for the rest ─────────────────────────
def _comb(x0: float, x1: float) -> cq.Workplane:
    """The cell walls under panel x0..x1: one midway between every two lit frets (fret_light's wall
    for that pitch), none within 3 of a seam -- there the panel's own end walls, half each side,
    stand instead -- all between the rails, from the skin down to COMB_CLR over the LEDs."""
    lit = lit_led_xs()
    ends = [x for x in seams()[1:-1]]
    yi = BOARD_HW + PLAY + 0.01
    z0, z1 = LED_FACE + COMB_CLR, PZ + 0.01
    out = None
    bx0, _ = board_x()
    sx0, _ = stop_x()

    def add(a, b):
        nonlocal out
        a, b = max(a, x0), min(b, x1)
        if b - a > 0.1:
            c = _box(a, b, -yi, yi, z0, z1)
            out = c if out is None else out.union(c)

    for fa, fb in zip(lit, lit[1:]):
        xm, t = (fa + fb) / 2, FL.wall_for(fb - fa)
        if all(abs(xm - e) > 3.0 for e in ends):
            add(xm - t / 2, xm + t / 2)
    for e in (x0, x1):                          # the panel's own end walls, inside the board's run
        if bx0 < e < sx0 and all(abs(e - s_) > 0.1 for s_ in (bx0,)):
            if abs(e - x0) < 1e-6 and e > bx0 + 1.0:
                add(e, e + D.MIN_WALL_2P)
            elif abs(e - x1) < 1e-6:
                add(e - D.MIN_WALL_2P, e)
    return out if out is not None else cq.Workplane("XY")


def _inlay_all() -> cq.Workplane:
    """Every white solid on the deck, absolute: the lit frets' windows through the skin, the
    unlit frets, the markers and the border (FRET_T deep)."""
    hy, w = TP.FRET_HY, TP.INLAY_W
    out = None

    def add(s):
        nonlocal out
        out = s if out is None else out.union(s)

    for n, fx in frets():
        z0 = PZ if n <= N_LIT else TZ - TP.FRET_T
        add(_box(fx - w / 2, fx + w / 2, -hy, hy, z0, TZ))
    for n in sorted(TP.MARKER_FRETS):
        add(_marker(n))
    # the border: the two long bands from the nut block's face to the deck's +X end, and the band
    # across at the block's face (the frame is open at +X, as v1's)
    bx0 = block_face()
    _, xe = deck_x()
    for s in (1, -1):
        add(_box(bx0, xe, min(s * hy, s * TP.BORDER_HY), max(s * hy, s * TP.BORDER_HY),
                 TZ - TP.FRET_T, TZ))
    add(_box(bx0, bx0 + w, -TP.BORDER_HY, TP.BORDER_HY, TZ - TP.FRET_T, TZ))
    zx0, zx1 = zero_window_x()                  # fret 0's window, through the skin
    add(_box(zx0, zx1, -hy, hy, PZ, TZ))
    return out


QUAD_D = TP.MARK_D * 0.5                        # 2.4: the octave marker's four dots
QUAD_P = QUAD_D + D.MIN_WALL                    # 3.2: a bead of panel between them (v1's 3.0 left 0.6)


def _marker(n: int) -> cq.Workplane:
    """top_plate's marker, but the octave's four dots a whole bead apart."""
    if TP.MARK_SHAPE[n % 12] != "quad":
        return TP._marker(n)
    x, out = TP._mark_x(n), None
    for i in range(4):
        c = (cq.Workplane("XY").circle(QUAD_D / 2).extrude(TP.FRET_T)
             .translate((x, (i - 1.5) * QUAD_P, TZ - TP.FRET_T)))
        out = c if out is None else out.union(c)
    return out


def _panel(k: int) -> cq.Workplane:
    return kept(_panel_solid, k).cut(kept(_inlay_all))


def _inlay(k: int) -> cq.Workplane:
    return kept(_inlay_all).intersect(kept(_panel_solid, k))


# ── the LED system (stand-in: v1's four per fret, at the new height) ───────────────────────────
def board() -> cq.Workplane:
    x0, x1 = board_x()
    return _box(x0, x1, -BOARD_HW, BOARD_HW, BOARD_BOT, BOARD_TOP)


def leds() -> cq.Workplane:
    out = None
    for fx in lit_led_xs():
        for y in FL.LED_YS:
            b = _box(fx - 2.5, fx + 2.5, y - 2.5, y + 2.5, BOARD_TOP, BOARD_TOP + FL.LED_H)
            out = b if out is None else out.union(b)
    return out


def parts() -> list:
    out = []
    for k in range(N_PANELS):
        out += [(f"deck_{k + 1}", kept(_panel, k)), (f"deck_white_{k + 1}", kept(_inlay, k))]
    out += [("fret_board", kept(board)), ("fret_leds", kept(leds))]
    from . import deck_v2_region as RG              # the optical panel and the pickup's slots (user 11-14)
    return out + RG.parts()


# ── the report ───────────────────────────────────────────────────────────────────────────────
def uniformity_report() -> str:
    """The fret line's evenness against LED count and depth (fret_light's Lambertian model with
    end reflectors). h is the LED's face to where the light is seen; the white diffuser adds
    roughly its own thickness to it."""
    lines = ["  h (mm)  " + "  ".join(f"{n:>5d}" for n in (4, 5, 6, 8, 12, 16)) + "   LEDs per fret"]
    hy = TP.FRET_HY
    for h in (LED_GAP, LED_GAP + SKIN / 2, LED_GAP + SKIN, 15.3):
        row = []
        for n in (4, 5, 6, 8, 12, 16):
            best = 0.0
            for k in range(60):
                out = hy * (0.5 + 0.5 * k / 60)
                ys = [-out + 2 * out * i / (n - 1) for i in range(n)]
                best = max(best, FL.uniformity(leds=ys, h=h, n=161)[0])
            row.append(f"{1 / best:5.2f}")
        lines.append(f"  {h:6.2f}  " + "  ".join(row))
    return "\n".join(lines)


def report() -> str:
    s = seams()
    out = ["THE TOP PANELS (src.deck_v2)",
           f"  stack: top {TZ:.2f}, skin to {PZ:.2f}, LED face {LED_FACE:.2f}, board {BOARD_BOT:.2f}.."
           f"{BOARD_TOP:.2f}, lips to {LIP_BOT:.2f}  ({TZ - LIP_BOT:.1f} under the top; v1 22.5)",
           f"  board: x {board_x()[0]:.2f}..{board_x()[1]:.2f} ({board_x()[1] - board_x()[0]:.1f} long), "
           f"y +-{BOARD_HW:.2f}; stop wall at {stop_x()[0]:.2f}",
           "  panels: " + ", ".join(f"{panel_x(k)[0]:.2f}..{panel_x(k)[1]:.2f} "
                                    f"({panel_x(k)[1] - panel_x(k)[0]:.1f})" for k in range(N_PANELS)),
           f"  seams at {s[1]:.2f}, {s[2]:.2f}, {s[3]:.2f}; UI station x {ui_x()[0]:.1f}..{ui_x()[1]:.1f}",
           "  fret line max:min (1.27 was v1's):", uniformity_report()]
    return "\n".join(out)


if __name__ == "__main__":
    print(report())
