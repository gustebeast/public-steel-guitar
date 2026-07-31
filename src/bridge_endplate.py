"""Bridge endplate (§8) — PCTG, printed FLAT, dovetailed onto the rail ends.

ONE solid piece that closes the box at the +X end AND carries the bridge-bearing
axle (the 90° string turn — the highest-load point in the instrument). Because it
prints flat (on its face) it needs no supports, so it can be fully solid and
featured; the rails' dovetail tongues socket into blind pockets in the base, driving
the bearing load straight into the rails — far stronger than the old bolted
bridge support. NO GLUE: the sockets lock X and Y by shape, and +Z — the drop-on
install axis — is closed by the RETENTION LIP below, which the installed deck
panels trap (probed: seated 0, lift 0.2 fouls the deck by 114 mm³). Replaces the
bridge support, the +X bulkhead AND the +X crossbar.
Built in global position.

Endplate methodology: BOTH endplates start from THE SAME TWO PRISMS (shared code,
endplate_base): the fill slab (z -23.15..6, full 25 footprint) = the +X cross-tie
(no separate chassis crossbar), and the hollowed foot box below it whose kept
exterior walls are the +X END face (CH.T = 10 thick) and the +-Y side faces (=
the rail takeovers: the chassis removes the rail ends at x > -17.5 and this piece
IS the rail there). Each rail end sockets a low keyhead-style dovetail (wide +X /
narrow -X, gripping the bearing wrap's -X pull). Above z6 only the string-holding
mechanism: the bearing AXLE on two short ARM stubs (the 90° turn) and the
axle-support COMB. The +X carriages move in Z and install from +X, so the
stringing window + guide ledges + screw rail + carriage sweep are OPENED out of
the base's field centre (below the lower guide ledge nothing sweeps — the base
stays solid to the bed); foot clearance is pocketed only over the +X legs' kept
chassis shells, and the panel-jack corner is recessed back to a 4 mm panel.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import chassis as CH
from . import top_plate as TP
from . import optical_pickup as OP
from .endplate_base import endplate_base
from .screw_rail import screw_rail as _screw_rail, HEIGHT as _SR_H
from .helpers import box_at, cyl, cyl_y
from cadkit.fasteners import M2, cut_selftap

X0   = CH.X_BRIDGE                 # cap -X face / field<->cap boundary: the field stays
                                   #   OPEN -X of here (carriage sweep / strings / rods)
# 25 mm block CENTERED on the bearing axle (the highest-load string-turn point), so the
# axle sits mid-material and the ~1.5 kN of string wrap is balanced about it. Both
# endplates are 25 mm (= CH.KH_EP_THK); the keyhead pins its inboard face to the rail
# end, the bridge instead centers that span on the axle. The arms, the fill band and the
# L-foot all span XLO..XHI SYMMETRIC about the axle, so the load path is balanced.
# XLO sits EP_TOP_CLR (0.4) +X of the rail end (CH.TP_EP_GX, derived as XLO - EP_TOP_CLR):
# the consistent top-joint X-gap to the housing; the dovetail's locking foot stays captured.
T_EP = D.ENDPLATE_W                # 25 mm width in X (shared with the keyhead + base)
XHI  = D.BRIDGE_BASE_X1            # +X outer tip (8.5), 12.5 +X of the axle
XLO  = D.BRIDGE_BASE_X0            # -X inboard face (-16.5), 12.5 -X of the axle
X1   = XHI                         # +X tip (8.5) -- alias for the mechanism references
ARM_X = XLO                        # arms span the FULL 25 mm block: symmetric edge webs
ARM_W = D.BRIDGE_ARM_W             # arm / edge-web thickness (Y) — kept clear of the +Y rail
# ── TIE BAR DELETED (user) -- THE TOP IS NOW FREE ───────────────────────────
# There is no longer ANY structure above the strings at the bridge. The old bar spanned
# x -16.6..8.6 at z 17..22, i.e. its underside was 0.11 mm over the thickest string's top
# and it started 12.6 mm out from the termination -- dead centre of the palm blocking
# zone, with no hand room at all.
#
# Removing it costs the axle almost nothing, and the reason is worth writing down: the
# axle bore is at z 12.0 and the SOLID field-centre cap band runs z 6..10, so the axle is
# carried 2 mm above the top of solid material. The arms are not really cantilevers at
# all at that height -- they are stubs. Everything the arm had from the bore's top (13.7)
# up to 22 was there to host the tie bar, not to hold the axle up. So the string load path
# is unchanged: bearings -> axle -> the nine comb fingers + two arm stubs -> cap band ->
# endplate block -> dovetails -> rails.
#
# The arms sit at y +-51.75, 9.35 mm OUTBOARD of the outermost string (+-42.4), so their
# height was never a string-clearance question either -- only the bar's span was.
ARM_TOP = D.BRIDGE_BEARING_Z + (D.BRIDGE_AXLE_D + 0.4) / 2 + 2.0   # 15.70: bore + a real
                                                                   # cap, and nothing more
MIN_ADDED = D.MIN_WALL_2P         # 1.6 -- two-bead QUALITY floor for material this
                                  # feature ADDS (single-sourced via dimensions)

# ── OPTICAL-STRIP CARRIER (optical_pickup.py) ────────────────────────────────
# The strip moved OUT from under this bar and UNDER THE STRINGS (user): a bar 3 mm over
# the strings, starting 14.5 mm out from the termination, sat straight in the palm
# blocking zone. It now lies on the deck, and this carrier is what holds it.
#
# A PLINTH, not a slot, and it is monolithic with the endplate on purpose: the sensor
# standoff is the signal-critical dimension on this board, so it wants to reference the
# bridge directly rather than through the deck panel's tolerance stack. It simply RIDES
# ON TOP of the deck -- no slot is spent, so the magnetic pickup keeps the whole grid.
#
# The strip is single-sided with every part on its TOP face, so the whole underside can
# bear on a solid plinth top; no ledges, no floor, nothing to fuse back after a cut.
# X is capped by the deck band OP reads from top_plate (pickup cavity to deck end): there
# is 0.2 either side of the board, so the plinth cannot have an -X wall and the board is
# located +X against the endplate face.
#
# The plinth is BACKED BY THE COMB BRACE below -- which is what makes it printable at all.
# On its own its first layer floated: the field-centre band above z6 is only unioned from
# X0 (+6.0) to X1, so between XLO and +6 there is no material at this height for the
# plinth to start on. (User-caught.)
CARRIER_TOP  = OP.PCB_BOT                     # 9.661 -- the board bears directly on this
CARRIER_BOT  = OP.DECK_TOP + 0.2              # 6.2 -- clearance so the deck slides under
CARRIER_X1   = OP.PCB_X1S - 0.1               # -X face, inside the band by a hair
CARRIER_HY   = 54.0                           # out to the arms

# ── COMB BACK-BRACE (user's sketch) ──────────────────────────────────────────
# The comb fingers root on the cap band at x 2.6..6.0 and reach out to -6.5 with the AXLE
# BORE AT THEIR TIP -- a 12.5 mm cantilever carrying the highest load in the instrument.
# This braces the other side: each finger grows -X, then FLARES AT 45 deg in plan until
# neighbouring flares merge into one solid bar spanning the full Y extent. The finger
# stops being a cantilever and becomes a beam held at both ends.
#
# 45 deg is not cosmetic -- it is the print constraint. The endplate builds +X -> -X, so
# growing in Y as X decreases means new material with nothing behind it; 45 deg is exactly
# the self-supporting limit, so the gaps close without a single overhang.
#
# And the same bar keeps running -X to BECOME the PCB plinth, which is what fixes that
# part's floating first layer: the whole path from the cap band to the optical strip is
# now continuous material in the build direction.
BRACE_X0 = -8.6                  # start of the flare: 0.6 clear of the bearing OD (x -8..0)
BRACE_X1 = XLO                   # -16.60, where the plinth takes over
BRACE_Z0 = CARRIER_BOT           # 6.2, so the plinth is backed over its full height
BRACE_Z1 = 13.0                  # covers the bore (10.3..13.7) up to where string
                                 # clearance runs out: 2.11 under the lowest string
AXLE_BORE = D.BRIDGE_AXLE_D + 0.4
# AXLE RETENTION, NO GLUE (user: every part comes apart). The Ø3 ground shaft slides
# -Y through both arms, 10 bearings and 9 comb fingers, so it can carry no shoulder;
# a glue dab at the arms used to hold it. Instead: the -Y arm's bore is BLIND (that
# wall is the -Y hard stop) and one M2 grub in the +Y arm's TOP bears on the shaft to
# close +Y. Deleting the tie bar freed that top face, so the grub is now reachable
# from straight above with the strings off. It self-taps in AXLE_GRUB_L of material
# rather than taking a heat-set insert (cadkit's usual set-screw preference): there
# are only 2.0 mm between the bore crown and the arm top, and 2.0 is five threads at
# 0.4 pitch against a shaft that nothing pushes axially -- 10 bearing bores of friction
# already hold it, and the blind end takes the other direction positively.
AXLE_END_WALL = 1.6                                   # -Y blind-bore wall (2 beads)
AXLE_GRUB_Z   = ARM_TOP                               # grub mouth: the arm's free top
AXLE_GRUB_L   = ARM_TOP - (D.BRIDGE_BEARING_Z + D.BRIDGE_AXLE_D / 2) + 0.2

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
# +X-leg foot POCKET: the chassis now KEEPS a ~10 mm rail shell hugging the +X leg
# socket (CH._leg_shell over CH.LEG_SHELL_PX), so the leg is wrapped by body. The
# bridge's foot is therefore NOT a big empty box -- it is just the chassis-shell
# outer profile grown by a small assembly clearance, so the bridge nests over the
# kept shell as it drops -Z (no gap: leg -> 10 mm rail wall -> bridge, all touching).
FOOT_Z   = CH.KH_DT_Z0              # XBAR-above-tenon line (-23.15) = use-up box floor
LEG_CLR  = CH.EP_LEG_CLR            # assembly clearance around the kept chassis shell (shared)
LEG_SHELL_X0, LEG_SHELL_X1 = CH.LEG_SHELL_PX     # leg-wrap shell span (rail-takeover region)

# +Z RETENTION LIP (-Y bay, BRIDGE ONLY) -- see _build. A 5x5 mm bar protruding -X off
# the endplate's -X face at the deck-bottom plane, running in Y from the -Y rail inner
# face to the pickup piece's -Y skirt. The deck panels slide in OVER it (deck bottom and
# lip top both at z0), so once the deck is in the lip is trapped under it and the endplate
# can't lift +Z. Internal (under the deck) -> nothing shows on the outside. The keyhead
# is held in +Z separately (nut-block screw path), so it gets no lip.
LIP_DX  = 5.0                                   # -X protrusion off the endplate -X face
LIP_DZ  = 5.0                                   # Z height, hanging below the deck bottom
LIP_CLR = CH.EP_TOP_CLR                         # clearance to the rail inner face + skirt
LIP_Y0  = CH.Y_LO + CH.T / 2 + LIP_CLR          # -Y rail inner face + clr (-128.35)
LIP_Y1  = -(TP.HY_CLAMP + TP.SKIRT_T) - LIP_CLR # pickup -Y skirt outer face - clr; self-tracks the
                                                # top_plate -Y room (-(HY_CLAMP + SKIRT_T), ~-70.9 now
                                                # that the room sizes to PK_MAX_L=102, not the Alumitone)


def _cap() -> cq.Workplane:
    """SOLID BASE + box-closure plate at the +X end, from THE SHARED TWO-
    PRISM BASE (endplate_base — same code as the keyhead): the fill slab
    (z -23.15..6, full 25 footprint) = the +X cross-tie, and the hollowed
    foot box below it whose kept exterior walls are the +X END face
    (x -1.4..8.6, CH.T thick — no more 2.6 sliver) and the two +-Y side
    faces (= the rail takeovers; the chassis drops the rail ends here).
    Then cut only what the mechanism needs: the FIELD-CENTRE OPENING
    (|y| <= WIN_HW, x < X0) from the lower guide-ledge line up — the
    carriage sweep, guide feet, strings and screw rail live there (below
    GR_LTOP nothing sweeps, so the base stays SOLID down to the bed).
    Only a field-centre upper band (z6..10) reaches the body top to back
    the window rim + axle comb + arm/tie roots. Foot clearance over each
    +X leg's kept chassis shell is pocketed afterward."""
    w = endplate_base(XLO, XHI, "hi")
    # field-centre upper band (z6..10): backs the window rim, the axle comb roots and
    # the bearing-arm/tie roots (the mechanism above z6 lives here, in the centre only)
    w = w.union(box_at(X1 - X0, 2 * MECH_HW, CH.Z_TOP - Z6,
                       x=(X0 + X1) / 2, y=0, z=(CH.Z_TOP + Z6) / 2))
    # FIELD-CENTRE OPENING: clear x XLO..X0 between the arms from the lower
    # guide-ledge line (GR_LTOP) to the top — the guide ledges + windows are
    # re-added/cut by _build in this space exactly as before
    w = w.cut(box_at(X0 - (XLO - 1.0), 2 * WIN_HW, (Z6 + 1.0) - GR_LTOP,
                     x=((XLO - 1.0) + X0) / 2, y=0,
                     z=(GR_LTOP + (Z6 + 1.0)) / 2))
    return w


def _arm(sy, blind=False) -> cq.Workplane:
    """Edge arm (clear of the strings) holding the axle. Spans the FULL endplate
    X-depth (axle line → +X tip) so it fuses solidly to the cap and prints with no
    overhang when built up along X.

    `blind=True` (the -Y arm) stops the bore AXLE_END_WALL short of the outer face:
    that wall is the shaft's -Y hard stop. See AXLE_END_WALL for why."""
    z_lo = CH.Z_TOP - 4.0
    arm = box_at(X1 - ARM_X, ARM_W, ARM_TOP - z_lo,
                 x=(X1 + ARM_X) / 2, y=sy, z=(ARM_TOP + z_lo) / 2)
    y0 = sy - ARM_W / 2 + (AXLE_END_WALL if blind else -1.0)
    h = (ARM_W / 2 + 1.0) - (y0 - sy)
    return arm.cut(cyl_y(AXLE_BORE, h, y0=y0,
                         x=D.BRIDGE_AXLE_X, z=D.BRIDGE_BEARING_Z))


_SRX = D.SCREW_X + 7.0            # screw-rail +X face (DEPTH/2 past the screw line)


def _comb_brace(yc: float, cb_w: float) -> cq.Workplane:
    """One finger's back-brace: constant width out to BRACE_X0, then a 45 deg flare in
    plan. Neighbouring flares merge into a solid bar; the outermost ones run on toward the
    arms. Nothing here is an overhang -- 1 mm of Y growth per 1 mm of X is exactly the
    self-supporting limit for a +X -> -X build."""
    hw0 = cb_w / 2
    hw1 = hw0 + (BRACE_X0 - BRACE_X1)          # 45 deg: Y growth == X run
    pts = [(-6.5, yc - hw0), (-6.5, yc + hw0),
           (BRACE_X0, yc + hw0), (BRACE_X1, yc + hw1),
           (BRACE_X1, yc - hw1), (BRACE_X0, yc - hw0)]
    return (cq.Workplane("XY").polyline(pts).close()
            .extrude(BRACE_Z1 - BRACE_Z0).translate((0, 0, BRACE_Z0)))


def _build() -> cq.Workplane:
    body = _cap()
    for sy in (-D.BRIDGE_AXLE_Y, D.BRIDGE_AXLE_Y):
        body = body.union(_arm(sy, blind=sy < 0))     # -Y arm: blind bore = the -Y stop
    # +Y arm: the M2 grub that closes the shaft's one remaining direction
    body = cut_selftap(M2, body, (D.BRIDGE_AXLE_X, D.BRIDGE_AXLE_Y, AXLE_GRUB_Z),
                       (0.0, 0.0, -1.0), AXLE_GRUB_L, overshoot=0.5)
    # Tie bar linking the arm tops above the strings. Runs from the +X tip out to
    # TIE_X0 -- past the endplate block -- so its underside can carry the DOWN-FIRING
    # optical strip at OP.SENSE_X, ~20 mm off the string termination.
    # OPTICAL-STRIP CARRIER: a plinth reaching -X over the deck, top face at the board's
    # underside. Prints with the rest -- at x = XLO its whole cross-section is backed by
    # the endplate's z6..10 field-centre band, which is why CARRIER_HY stops at 54.
    body = body.union(box_at(XLO - CARRIER_X1, 2 * CARRIER_HY, CARRIER_TOP - CARRIER_BOT,
                             x=(XLO + CARRIER_X1) / 2, y=0,
                             z=(CARRIER_BOT + CARRIER_TOP) / 2))
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
        body = body.union(_comb_brace(yc, CB_W))
        body = body.cut(cyl_y(D.BRIDGE_AXLE_D + 0.3, CB_W + 2, y0=yc - CB_W / 2 - 1,
                              x=D.BRIDGE_AXLE_X, z=D.BRIDGE_BEARING_Z))

    # STRINGING-ACCESS window: open the cap over the field (top-centre, between the
    # bearing arms) so each string threads over its bridge bearing and its end-nut
    # slots into the carriage from +X. Inboard of the arms (±BRIDGE_AXLE_Y) and below
    # the tie bar, so the axle support, dovetails and screw rail are untouched.
    body = body.cut(box_at((X1 - X0) + 2.0, 2 * WIN_HW, WIN_Z1 - WIN_Z0,
                           x=(X0 + X1) / 2, y=0, z=(WIN_Z1 + WIN_Z0) / 2))
    # FOOT POCKET: the chassis KEEPS a ~10 mm rail shell hugging each +X leg socket
    # (CH._leg_shell), capped at the foot line (z FOOT_Z = -23.15). Pocket exactly
    # that shell + a small assembly clearance out of the bridge so it nests over the
    # shell as it drops -Z. No empty box: leg -> 10 mm rail wall -> bridge, all
    # touching. The pocket ONLY clears z = Z_BOT .. FOOT_Z (over the shell) -- NOT
    # full-Z -- so the solid fill band (z -23.15..6) stays intact over the legs (the
    # band sits on top of the capped shell; the shell ends at FOOT_Z so nothing above
    # it needs clearing on the install drop).
    for yr, s in ((CH.Y_HI, 1), (CH.Y_LO, -1)):
        yf = yr + s * CH.T / 2 + s * LEG_CLR        # shell outer face + clearance
        yi = yr - s * CH.T / 2 - s * LEG_CLR        # shell inner face + clearance
        body = body.cut(box_at((LEG_SHELL_X1 + LEG_CLR) - (LEG_SHELL_X0 - 1.0),
                               abs(yf - yi), FOOT_Z - (CH.Z_BOT - 1.0),   # stop AT the foot line
                               x=((LEG_SHELL_X0 - 1.0) + (LEG_SHELL_X1 + LEG_CLR)) / 2,
                               y=(yf + yi) / 2,
                               z=((CH.Z_BOT - 1.0) + FOOT_Z) / 2))
    # SOCKET the rail-end dovetail tongue on each rail (keyhead-style, low band z
    # -23.15..-6): the endplate drops straight down onto the rail tongues. No glue —
    # the deck panels trap the +Z retention lip (see the module docstring).
    # The dovetail (wide +X / narrow -X) locks it in X+Y and grips the bearing-wrap
    # pull (-X); the low band leaves the cap free to drop to z6.
    for yr in CH.ENDPLATE_JOINT_Y:
        body = body.cut(CH._br_tongue(yr, socket=True))
    # LEG-STUB grooves (Y-INSTALL round — user: the stubs print on their
    # side and SLIDE IN ALONG Y): cut this end's corner negatives from the
    # SAME shared source the chassis uses (legs.corner_groove_negatives),
    # so the end-wall groove continues seamlessly across the kept-shell /
    # endplate boundary at the rail bands. The bridge hosts the 44-long
    # END-WALL groove at x 3.6 (wall centreline; blind inboard end = the
    # flush hard stop) — its band (bed..bed+7.34) sits far below the jack
    # recess floor (-55) and the guide windows.
    # relief=False: the 45° overhang wedge relieves the CHASSIS tongue
    # only — cut here it eats the end-wall groove roof (user-caught).
    # + the per-leg M4 LOCK SCREW ways along x through the end face
    # (Ø4.6 outboard cheek / Ø3.6 pilot through tongue + inboard cheek).
    from .legs import (corner_groove_negatives as _cgn,
                       endwall_screw_negatives as _esn)
    for _ly, _s in ((CH.LEG_Y[0], 1.0), (CH.LEG_Y[1], -1.0)):
        for _n in _cgn(CH.LEG_STATIONS_X[0], _ly, _s, 1.0, CH.Z_BOT,
                       relief=False):
            body = body.cut(_n)
        for _n in _esn(CH.LEG_STATIONS_X[0], _ly, 1.0, CH.Z_BOT):
            body = body.cut(_n)
    # PANEL I/O (the instrument's right face): the base's +X end wall is CH.T (10)
    # thick -- too deep for the jacks (their bodies span x -16..6) -- so RECESS its
    # interior back to a 4 mm panel at the -Y jack corner (the wall face at
    # JACK_WALL_X..XHI stays; the bodies seat through the recess into the hollow
    # foot interior). Recess band z (JACK_Z-14)..FOOT_Z, inside the hollow's Y span
    # (the Y-INSTALL leg grooves top out at bed+7.34, 12.7 below the recess floor,
    # so the recess is back at its full pre-EP-tenon size).
    # Then the three jack holes - 1/4" TS line out, DC power inlet, USB-C (audio-interface
    # port). Printed flat, so the panel + holes are vertical in the print - no supports.
    from .electronics import TS_Y, DC_Y, USB_Y, JACK_Z, JACK_WALL_X
    body = body.cut(box_at(JACK_WALL_X - (XLO - 1.0), 62.0, FOOT_Z - (JACK_Z - 14.0),
                           x=((XLO - 1.0) + JACK_WALL_X) / 2, y=-88.0,
                           z=(FOOT_Z + (JACK_Z - 14.0)) / 2))
    for jy, jd in ((TS_Y, 11.8), (DC_Y, 6.2)):   # Ø11.4 TS bushing, Ø5.7 DC thread
        body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            jd / 2, 6.0, cq.Vector(JACK_WALL_X - 1.0, jy, JACK_Z),
            cq.Vector(1, 0, 0))))
    body = body.cut(box_at(6.0, 13.2, 6.8, x=JACK_WALL_X + 2.0, y=USB_Y, z=JACK_Z))
    for sy in (USB_Y - 9.0, USB_Y + 9.0):       # USB-C flange screw pilots
        body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            1.25, 6.0, cq.Vector(JACK_WALL_X - 1.0, sy, JACK_Z),
            cq.Vector(1, 0, 0))))
    # +Z RETENTION LIP: protrudes -X under the deck in the -Y bay (see the LIP_* block);
    # the installed deck panels trap it, blocking the endplate from lifting +Z. Its +X face
    # is the endplate -X face (XLO); top is the deck-bottom plane (z0) so the deck rides it.
    body = body.union(box_at(LIP_DX, LIP_Y1 - LIP_Y0, LIP_DZ,
                             x=XLO - LIP_DX / 2, y=(LIP_Y0 + LIP_Y1) / 2,
                             z=CH.TP_GZ0 - LIP_DZ / 2))
    return body


bridge_endplate = _build()
