"""Bridge endplate (§8) — PCTG, printed FLAT, dovetailed onto the rail ends.

ONE solid piece that closes the box at the +X end AND carries the bridge-bearing
axle (the 90° string turn — the highest-load point in the instrument). Because it
prints flat (on its face) it needs no supports, so it can be fully solid and
featured; the rails' dovetail tongues glue into blind sockets in the base, driving
the bearing load straight into the rails — far stronger than the old bolted
bridge support. Replaces the bridge support, the +X bulkhead AND the +X crossbar.
Built in global position.

Endplate methodology (mirrors the keyhead): the base is AS SOLID AS POSSIBLE — a
block over the whole +X footprint (the cap thickness x6..16 PLUS a -X rail-takeover
extension over each rail to x -17.5) from the deck level (z6) down to the bed, so
the block itself IS the +X cross-tie (no separate chassis crossbar). It TAKES OVER
the rail +X ends (the chassis removes the rail at x > -17.5) and sockets a low
keyhead-style dovetail on each rail end (wide +X / narrow -X, gripping the bearing
wrap's -X pull). Above z6 only the string-holding mechanism: the bearing AXLE on
two ARMS + a TIE BAR (the 90° turn) and the axle-support COMB. The +X carriages
move in Z and install from +X, so the stringing window + guide ledges + screw rail
+ carriage sweep stay HOLLOW; foot clearance is hollowed only over the +X legs.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from .screw_rail import screw_rail as _screw_rail, HEIGHT as _SR_H
from .helpers import box_at, cyl, cyl_y

X0   = CH.X_BRIDGE                 # join line (the rails end here; cap is +X of it)
X1   = X0 + D.WALL_THICKNESS       # +X tip (cap thickness = wall)
ARM_X = D.BRIDGE_AXLE_X - 4.0      # arms reach −X to past the axle
ARM_W = D.BRIDGE_ARM_W             # arm / edge-web thickness (Y) — kept clear of the +Y rail
TIE_Z = D.STRING_Z + 6.0          # tie bar / arm top, clear above the strings
AXLE_BORE = D.BRIDGE_AXLE_D + 0.4

# Guide-rod LEDGES: two shallow bars protruding −X from the cap face below the
# stringing window, spanning arm to arm — straight X-extensions of solid cap, so
# (printing along X) every layer is backed: no overhang. (The cap band between
# the ledges is opened — see the guide-view window.)
# UPPER bar: the TOP hard stop — flush with the carriage foot at default (the
# anchor post can never reach the bridge bearings) — and it carries a snug
# Ø2.55 drop-in hole per rod: the rod installs top-down through it (through the
# carriage's closed bore) and its top stays friction-held in this hole. LOWER
# bar: BLIND snug sockets the rods land in; its top face is the BOTTOM hard stop.
GRX     = D.SCREW_X + D.GUIDE_ROD_DX                      # rod line (+3.5)
GR_H    = 6.0                                             # ledge heights
GR_UBOT = D.CARRIAGE_NOM_Z + D.GUIDE_FOOT_DZ              # upper bottom = top stop (−20)
GR_UTOP = GR_UBOT + GR_H                                  # = the window sill (−14)
GR_LTOP = GR_UBOT - D.CARRIAGE_TRAVEL - D.GUIDE_FOOT_H    # lower top = bottom stop (−38)
GR_LBOT = GR_LTOP - GR_H

# Stringing-access cutout (over the field): a clean rectangle with a UNIFORM cap
# border on every side. WIN_BORDER is that border to the cap top and the bearing
# arms; the diamond lightening is kept the same distance clear of it below.
WIN_BORDER = 4.0
WIN_HW     = D.BRIDGE_AXLE_Y - ARM_W / 2                  # out to the arm inner faces, so the
                                                          # edge carriages/string balls are reachable
WIN_Z1     = CH.Z_TOP - WIN_BORDER                        # top (rim to the cap top)
WIN_Z0     = GR_UTOP                                      # bottom = the upper guide ledge's top


Z6     = CH.TP_GZ1                 # deck/top-plate level = the bridge's general top
MECH_HW = D.BRIDGE_AXLE_Y + ARM_W / 2   # field-centre upper-cap half-span (arm outer)
# +X-leg foot clearance: hollow the solid base over each +X leg below the XBAR-above-
# tenon line (KH_DT_Z0). The +X legs are at x -40..4, y 37.75..81.75 (+Y) and
# -155.75..-111.75 (-Y) -- both fully cover their rail Y band, so the clearance is the
# whole rail-takeover block below KH_DT_Z0 (it keeps the dovetail band z -23.15..6).
FOOT_Z   = CH.KH_DT_Z0
LEG_BANDS = ((37.75, 81.75), (-155.75, -111.75))


def _cap() -> cq.Workplane:
    """SOLID BASE + box-closure plate at the +X end. The endplate methodology: a solid
    block over the whole +X footprint from the deck level (z6) down to the bed -- this
    block IS the +X cross-tie (no separate crossbar). It spans the cap thickness (x6..16,
    rail-to-rail) PLUS a -X rail-takeover extension over each rail (x -17.5..6) that fills
    the rail end the chassis dropped. Generally it tops at z6; only a field-centre upper
    band (z6..10, |y| <= the bearing arms) reaches the body top to back the window rim +
    axle comb + arm/tie roots. Lightened with diamonds in the cap thickness (flat-printed,
    so the holes cost nothing). Foot clearance is hollowed over each +X leg afterward."""
    xc, thk = (X0 + X1) / 2, X1 - X0
    # cap (x6..16), rail-to-rail, z6 down to the bed -- the box closure + cross-tie
    w = box_at(thk, CH.Y_HI - CH.Y_LO + CH.T, Z6 - CH.Z_BOT,
               x=xc, y=(CH.Y_HI + CH.Y_LO) / 2, z=(Z6 + CH.Z_BOT) / 2)
    # field-centre upper band (z6..10): backs the window rim, the axle comb roots and
    # the bearing-arm/tie roots (the mechanism above z6 lives here, in the centre only)
    w = w.union(box_at(thk, 2 * MECH_HW, CH.Z_TOP - Z6,
                       x=xc, y=0, z=(CH.Z_TOP + Z6) / 2))
    # -X rail-takeover extension: fill each rail end (x -17.5..6) over its Y band, z6
    # down to the bed, so the bridge IS the rail there (the chassis removed it)
    for yf in (CH.Y_HI, CH.Y_LO):
        w = w.union(box_at(X0 - CH.TP_EP_GX, CH.T, Z6 - CH.Z_BOT,
                           x=(CH.TP_EP_GX + X0) / 2, y=yf, z=(Z6 + CH.Z_BOT) / 2))
    # diamond lightening of the cap thickness (the flat-print face); skip the window
    # border, the guide-ledge backing and the -Y jack zone
    H, WEB, M = 11.0, 7.0, 9.0
    step = 2 * H + WEB
    yc = (CH.Y_LO + CH.Y_HI) / 2
    cz = CH.Z_TOP - M - H
    while cz - H >= CH.Z_BOT + M:
        cy = yc - step * 8
        while cy <= yc + step * 8:
            in_field = CH.Y_LO + M <= cy - H and cy + H <= CH.Y_HI - M
            above_base = cz - H >= Z6 and abs(cy) + H > MECH_HW   # only the field band is solid up there
            # keep a clear border around the stringing cutout AND solid cap behind
            # the guide ledges (their print layers + stop loads back onto it)
            near_win = (abs(cy) - H <= WIN_HW + WIN_BORDER
                        and cz + H >= GR_LBOT - WIN_BORDER
                        and cz - H <= WIN_Z1 + WIN_BORDER)
            # keep the -Y jack zone solid: the panel-jack recess (TS, DC,
            # USB-C, raised to z -41) thins it to a 4 mm wall instead
            near_jack = (cy + H >= -119.0 and cy - H <= -57.0
                         and cz - H <= -28.0 and cz + H >= -54.0)
            if in_field and not near_win and not near_jack and not above_base:
                w = w.cut(CH._diamond(cy, cz, H, xc, thk))
            cy += step
        cz -= step
    return w


def _arm(sy) -> cq.Workplane:
    """Edge arm (clear of the strings) holding the axle. Spans the FULL endplate
    X-depth (axle line → +X tip) so it fuses solidly to the cap and prints with no
    overhang when built up along X."""
    z_lo = CH.Z_TOP - 4.0
    arm = box_at(X1 - ARM_X, ARM_W, TIE_Z - z_lo,
                 x=(X1 + ARM_X) / 2, y=sy, z=(TIE_Z + z_lo) / 2)
    return arm.cut(cyl_y(AXLE_BORE, ARM_W + 2, y0=sy - ARM_W / 2 - 1,
                         x=D.BRIDGE_AXLE_X, z=D.BRIDGE_BEARING_Z))


_SRX = D.SCREW_X + 7.0            # screw-rail +X face (DEPTH/2 past the screw line)


def _build() -> cq.Workplane:
    body = _cap()
    for sy in (-D.BRIDGE_AXLE_Y, D.BRIDGE_AXLE_Y):
        body = body.union(_arm(sy))
    # tie bar linking the arm tops above the strings (full depth → +X tip)
    body = body.union(box_at(X1 - ARM_X, 2 * D.BRIDGE_AXLE_Y + ARM_W, 5.0,
                             x=(X1 + ARM_X) / 2, y=0, z=TIE_Z - 2.5))
    # FUSE IN the screw-support rail and bridge it to the cap at the bottom + tie it
    # up to the bearing arms at the edges — the whole bridge end becomes one solid
    # piece (screw support + bearing support + box closure) with continuous material.
    # The bottom + edge bridges run the FULL X-depth (screw line → +X tip).
    body = body.union(_screw_rail)
    body = body.union(box_at(X1 - _SRX, 2 * D.BRIDGE_AXLE_Y, 10.0,    # bottom bridge → tip
                             x=(X1 + _SRX) / 2, y=0, z=D.SUPPORT_BRG_Z))
    z_lo = CH.Z_TOP - 4.0
    sr_bot = D.SUPPORT_BRG_Z - _SR_H / 2                              # screw-rail −Z extent
    for sy in (-D.BRIDGE_AXLE_Y, D.BRIDGE_AXLE_Y):                    # edge webs rail→arm
        body = body.union(box_at(X1 - _SRX, ARM_W, z_lo - sr_bot,     # down to the rail bottom
                                 x=(X1 + _SRX) / 2, y=sy, z=(z_lo + sr_bot) / 2))
    # (no +X deck-lock shelf / capture groove / dropped section / -Y roof: the solid
    #  base over the rail ends now IS the cross-tie + the deck panels' +X stop; the
    #  deck is held in +Z by the rail-top grooves along its length, not by the bridge.)
    # GUIDE-ROD LEDGES (see the GR_* block above): upper = stop bar + drop-in
    # holes; lower = bottom stop + blind landing sockets. Arm to arm. Both bars
    # reach X ≥ +1.4 so the Ø2.55 rod holes are fully enclosed (−X wall 0.8).
    body = body.union(box_at(4.6, 2 * D.BRIDGE_AXLE_Y, GR_H,
                             x=X0 - 2.3, y=0, z=(GR_UBOT + GR_UTOP) / 2))
    body = body.union(box_at(4.6, 2 * D.BRIDGE_AXLE_Y, GR_H,
                             x=X0 - 2.3, y=0, z=(GR_LBOT + GR_LTOP) / 2))
    for i in range(D.N_STRINGS):
        sy = D.string_y(i)
        # blind landing socket: the rod drops until it bottoms at GR_LBOT+2
        body = body.cut(cyl(D.GUIDE_ROD_D + 0.05, (GR_LTOP + 1) - (GR_LBOT + 2),
                            z=GR_LBOT + 2).translate((GRX, sy, 0)))
        # drop-in hole through the stop bar (a complete O — the bar is deep
        # enough to wall it all round; the rod top stays friction-held in it)
        body = body.cut(cyl(D.GUIDE_ROD_D + 0.05, GR_H + 2, z=GR_UBOT - 1)
                        .translate((GRX, sy, 0)))
    # GUIDE-VIEW window: open the cap between the two ledges so the rods' free
    # span is visible/inspectable from outside. The ledge Z-bands stay solid —
    # they're the ledges' print backing and carry the stops + rod sockets.
    body = body.cut(box_at((X1 - X0) + 2.0, 2 * WIN_HW, GR_UBOT - GR_LTOP,
                           x=(X0 + X1) / 2, y=0, z=(GR_UBOT + GR_LTOP) / 2))

    # AXLE-SUPPORT COMB: nine fingers from the cap band above the stringing
    # window, one in each gap between bridge bearings. Without them the Ø3 axle
    # spans 103.5 mm carrying ~1.5 kN of string wrap load (≈28 mm computed
    # deflection — it would simply bend); the fingers cut the free span to one
    # string pitch (δ ≈ 0.004 mm, ~140 MPa in the shaft). Each finger: a ROOT on
    # the cap band (Z 6..10), an ARCH whose underside clears the anchor post's
    # sweep by 0.8, and a HEAD with a Ø3.3 bore on the axle line. REST TABS
    # protrude 0.8 into each gap, topped by a shallow V dipping to Z 8.0
    # (= axle Z − bearing radius): a bearing dropped between two heads lands on
    # the tabs with its bore exactly on the axle line — the comb is the assembly
    # jig: set all 10 bearings in their slots, then slide the axle through
    # arms + finger bores + bearing bores in one pass (axle must be a g6/h6
    # precision shaft, NOT an m6 dowel — see BOM). 45° ramps keep every surface
    # self-supporting printing along X from the cap.
    CB_W = 5.2                                # finger width → 0.15 to each bearing face
    _fpro = (cq.Workplane("XZ")
             .polyline([(6.0, 6.0), (2.6, 6.0), (2.6, 7.8), (-4.2, 7.8),
                        (-5.5, 6.5), (-6.5, 6.5), (-6.5, 14.5), (-1.5, 14.5),
                        (3.0, 10.0), (6.0, 10.0)])
             .close().extrude(CB_W / 2, both=True))
    _tpro = (cq.Workplane("XZ")
             .polyline([(-2.0, 7.5), (-2.0, 8.25), (-4.0, 7.9),
                        (-6.0, 8.25), (-6.0, 7.5)])
             .close().extrude((CB_W + 1.6) / 2, both=True))
    for k in range(D.N_STRINGS - 1):
        yc = (D.string_y(k) + D.string_y(k + 1)) / 2
        body = body.union(_fpro.translate((0, yc, 0)))
        body = body.union(_tpro.translate((0, yc, 0)))
        body = body.cut(cyl_y(D.BRIDGE_AXLE_D + 0.3, CB_W + 2, y0=yc - CB_W / 2 - 1,
                              x=D.BRIDGE_AXLE_X, z=D.BRIDGE_BEARING_Z))

    # STRINGING-ACCESS window: open the cap over the field (top-centre, between the
    # bearing arms) so each string threads over its bridge bearing and its end-nut
    # slots into the carriage from +X. Inboard of the arms (±BRIDGE_AXLE_Y) and below
    # the tie bar, so the axle support, dovetails and screw rail are untouched.
    body = body.cut(box_at((X1 - X0) + 2.0, 2 * WIN_HW, WIN_Z1 - WIN_Z0,
                           x=(X0 + X1) / 2, y=0, z=(WIN_Z1 + WIN_Z0) / 2))
    # FOOT clearance: hollow the solid base over each +X leg below the XBAR-above-tenon
    # line (the only place we thin the rail-takeover block) so the leg + the bridge's
    # install drop clear. x -17.5..4 covers the leg's +X reach into the bridge footprint.
    for (y0, y1) in LEG_BANDS:
        body = body.cut(box_at(4.0 - CH.TP_EP_GX, y1 - y0, FOOT_Z - CH.Z_BOT,
                               x=(CH.TP_EP_GX + 4.0) / 2, y=(y0 + y1) / 2,
                               z=(FOOT_Z + CH.Z_BOT) / 2))
    # SOCKET the rail-end dovetail tongue on each rail (keyhead-style, low band z
    # -23.15..-6): the endplate drops straight down onto the rail tongues and glues.
    # The dovetail (wide +X / narrow -X) locks it in X+Y and grips the bearing-wrap
    # pull (-X); the low band leaves the cap free to drop to z6.
    for yr in CH.ENDPLATE_JOINT_Y:
        body = body.cut(CH._br_tongue(yr, socket=True))
    # PANEL I/O (the instrument's right face): recess the lower -Y corner from
    # the inside down to a 4 mm wall, then the three jack holes - 1/4" TS line
    # out, DC power inlet, USB-C (audio-interface port). Printed flat, so the
    # recess and holes are vertical in the print - no support concerns.
    from .electronics import TS_Y, DC_Y, USB_Y, JACK_Z, JACK_WALL_X
    body = body.cut(box_at(JACK_WALL_X - X0 + 1.0, 58.0, 22.0,
                           x=(X0 - 1.0 + JACK_WALL_X) / 2, y=-88.0, z=JACK_Z))
    for jy, jd in ((TS_Y, 11.8), (DC_Y, 6.2)):   # Ø11.4 TS bushing, Ø5.7 DC thread
        body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            jd / 2, 6.0, cq.Vector(JACK_WALL_X - 1.0, jy, JACK_Z),
            cq.Vector(1, 0, 0))))
    body = body.cut(box_at(6.0, 13.2, 6.8, x=JACK_WALL_X + 2.0, y=USB_Y, z=JACK_Z))
    for sy in (USB_Y - 9.0, USB_Y + 9.0):       # USB-C flange screw pilots
        body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            1.25, 6.0, cq.Vector(JACK_WALL_X - 1.0, sy, JACK_Z),
            cq.Vector(1, 0, 0))))
    return body


bridge_endplate = _build()
