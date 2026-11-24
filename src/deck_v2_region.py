"""The +X end of the v2 deck: the OPTICAL panel and the MAGNETIC pickup's swappable slot region.

User, 2026-11-14. From the +X endplate going -X:

  OPTICAL PANEL   a thin section that houses the optical pickup board. It is exactly wide enough
                  that the board's -X edge sits on the panel's -X edge with v1's sensing geometry:
                  the sensor row SENSE_D (20) out from the string's termination on the bridge
                  bearing, and the board's -X edge v1's keepout past the row (the PD15 courtyard
                  and the emitter rail's lane: optical_pickup.PCB_X1S). The board itself is being
                  redesigned (bronner), so it is drawn as a stand-in strip on the panel's plinth.
                  The plinth stands in the same y band as the endplate's raised part, so the two
                  read as one raised block; outside it the panel is flush with the deck.
  SLOT REGION     v1's system (src/top_plate.py), ported: N_SLOTS equal slots, a PIECE_SLOTS-wide
                  PICKUP PIECE in any run of them and plain FILLERS in the rest. Swapping which
                  slots hold the piece coarse-moves the magnetic pickup; it slides +-X_SLIDE on its
                  height plate in between. The piece carries v1's mount unchanged: the cavity, the
                  -Y skirt, three top-access M4 x 20 jacks lifting/tilting the height plate, the
                  +Y wall and -Y retention screw on the plate. The region ends at panel 3's seam,
                  so panels 1-3 (the LED cradle, the UI) never move.

All panels here are v1's solid 6.4 deck between the walls (the LED board stops short of the
region), with the v2 tongue on each wall.
"""
from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import deck_layout as DL
from . import deck_v2 as DK
from . import optical_pickup as OP
from . import pickup_mount as PM
from .helpers import box_at, cyl, heal
from cadkit.fasteners import M4, cut_counterbore
from cadkit.kept import kept
from cadkit.web.finishes import made_of

GAP = DK.GAP
TZ, PZ = DK.TZ, DK.PZ
BZ = 0.0                                        # the region panels' underside: v1's 6.4 deck


def _db():
    from . import direct_bench as DB
    return DB


# ── the optical panel ─────────────────────────────────────────────────────────────────────────
SENSE_D = OP.SENSE_D                            # 20.0: v1's sensor row off the termination
SENSE_EDGE = OP.SENSE_X - OP.PCB_X1S            # 4.16: v1's keepout, the row to the board's -X edge
PLINTH_TOP = OP.PLINTH_TOP                      # 12.04: the board's underside (worst-case thickness)
OPT_BOARD_W = OP.PCB_X0 - OP.PCB_X1S            # 8.81: v1's sensor strip, -X edge to +X edge


def termination_x() -> float:
    """Where the string leaves the bridge bearing's top: over the bridge axle."""
    return _db().X_BEND


def optical_x() -> tuple:
    """(x0, x1) of the optical panel: its -X edge is the board's -X edge."""
    x1 = _db().ep_x()["x_j"] - GAP
    x0 = termination_x() - SENSE_D - SENSE_EDGE
    assert x1 - x0 >= OPT_BOARD_W + GAP, (x0, x1, "the sensor strip no longer fits the panel")
    return x0, x1


def sense_x() -> float:
    return termination_x() - SENSE_D


# ── the slot region ───────────────────────────────────────────────────────────────────────────
N_SLOTS = 6
PIECE_SLOTS = 4
N_POS = N_SLOTS - PIECE_SLOTS + 1               # 3 coarse positions
PIECE_POS = 0                                   # shown: the piece in the +X-most slots, as v1


def slot0_x() -> float:
    return optical_x()[0] - GAP


def region_end() -> float:
    """The region's -X end: panel 3's +X face, a GAP on."""
    return DK.panel_x(DK.N_PANELS - 1)[1] + GAP


def pitch() -> float:
    return (slot0_x() + GAP - region_end()) / N_SLOTS


def band_w() -> float:
    return pitch() - GAP


def slot_x(i: int) -> tuple:
    """Slot i's (x0, x1), +X face first."""
    a = slot0_x() - i * pitch()
    return a, a - band_w()


def piece_x(pos: int = PIECE_POS) -> tuple:
    """(+X face, -X face, centre) of the piece in slots pos .. pos + PIECE_SLOTS - 1."""
    a = slot_x(pos)[0]
    b = slot_x(pos + PIECE_SLOTS - 1)[1]
    return a, b, (a + b) / 2


# v1's piece interior, ported: everything in y and z is v1's, x is relative to the piece centre
WALL = DL.WALL
SKIRT_T = DL.SKIRT_T
JACKS = [(jx - DL.PICKUP_X_NOM, jy) for jx, jy in DL.JACK_POS]      # (dx, y) off the centre
# the end walls stop short of the +Y jacks' nubs, which reach out under them (v1's piece was 80 wide
# and its walls cleared them; at this pitch the nub's boss reaches 1.7 into the wall)
END_WALL_Y1 = min(jy for _, jy in JACKS if jy > 0) - DL.NUB_W / 2 - 1.0
FILL_UP = DL.PIECE_UP                           # the piece and the fillers print deck-down, as v1


def _body(x0: float, x1: float) -> cq.Workplane:
    """A region panel x1 (-X) .. x0 (+X): the skin over the walls, v1's solid 6.4 deck between
    them, the tongue down each wall's groove."""
    wl = DK.walls()
    w = DK._box(x1, x0, wl["y0"], wl["y1"], PZ, TZ)
    w = w.union(DK._box(x1, x0, wl["b0"] + DK.SKIRT_CLR, wl["b1"] - DK.SKIRT_CLR, BZ, PZ + 0.01))
    return w.union(DK._tongues(x1, x0))


def optical_panel() -> cq.Workplane:
    x0, x1 = optical_x()
    ya, yb = _db().ep_raised_y()
    w = _body(x1, x0)
    w = w.union(DK._box(x0, x1, ya, yb, TZ - 0.01, PLINTH_TOP))
    sx0, sx1, sy0, sy1 = j4_slot()
    return w.cut(DK._box(sx0, sx1, sy0, sy1, BZ - 3.0, PLINTH_TOP + 0.01))


def optical_board() -> cq.Workplane:
    """STAND-IN: v1's sensor strip, its -X edge on the panel's, flat on the plinth."""
    x0, _ = optical_x()
    ya, yb = _db().ep_raised_y()
    return DK._box(x0, x0 + OPT_BOARD_W, ya + 1.0, yb - 1.0, PLINTH_TOP, PLINTH_TOP + OP.PCB_T)


# ── THE RIBBON'S OPTICAL END: J4, DECLARED (lead, 2026-11-23) ─────────────────────────────────────
# The optical board is being redesigned (no MCU: the brain board's STM32H743 reads its converters
# over a 20-way ribbon, elec/brain_board.py J4). Its shape is not decided, but where the ribbon lands
# on it is, here, so the harness measures a real end and the redesign has a fixed interface to keep:
#   * THE SAME PART AS THE BRAIN'S J4, a 2 x 10 1.27 mm vertical SMD header (HX PZ1.27, the socket
#     src/ribbon_socket.py draws), and THE SAME WAY ON EVERY PIN: an IDC ribbon is wire n = pin n
#     at both ends, so OPT_J4_PINOUT must read as brain J4's (check_j4_mirror, below).
#   * ON THE UNDERSIDE (B), pointing -Z into a slot through the plinth: the strip's top face is
#     under the strings (optical_pickup.PCB_TOP), with no room for 7.4 mm of header and socket.
#     That makes the redesigned board two-sided for assembly: one part on B.
#   * At the strip's -Y end, rows along Y, pin 1 at the -Y end. The ribbon leaves the socket +X
#     (toward the endplate: the strip's -X side is the panel's edge) and turns down through the
#     slot to the body cavity, then to the brain on the -Y wall.
#   * THE SLOT IS IN THE PLINTH AND THE PANEL ONLY (lead): a MIN_WALL_2P web each side in X, and
#     in Y it starts a web in from the plinth's -Y face. The side rails are nowhere near it
#     (asserted); if it ever reaches one, the header moves, not the rail.
# Plug the ribbon before the board goes down on the plinth (INSTALL_NOTES).
OPT_J4_FP = "Connector_PinHeader_1.27mm:PinHeader_2x10_P1.27mm_Vertical_SMD"   # brain J4's footprint
OPT_J4_N = 10                                   # ways a row
OPT_J4_SIDE = "B"
OPT_J4_PINOUT = ("+5V", "+5V", "GND", "SAI_SCK", "GND", "SAI_FS", "GND", "SAI_SD1", "SAI_SD2",
                 "GND", "SAI_SD3", "SAI_SD4", "GND", "SAI_SD5", "GND", "OPT_EMIT", "GND",
                 "I2C2_SDA", "I2C2_SCL", "GND")
J4_BODY = (3.41, 12.70)                         # the footprint's F.Fab body, across x along the rows
J4_PLASTIC = 1.30                               # HX PZ1.27: 5.3 off the board, 4.0 of pin past its plastic
SLOT_WEB = D.MIN_WALL_2P                        # the plinth's wall either side of the slot
SLOT_CLR = 0.5                                  # socket to slot, along Y


def j4_socket_len() -> float:
    """The IDC socket along its rows: Samtec FFSD, N x 1.27 + 4.19 (src/ribbon_socket.py)."""
    return OPT_J4_N * 1.27 + 4.19


def j4_slot() -> tuple:
    """(x0, x1, y0, y1) of the ribbon slot through the plinth and the panel."""
    x0, x1 = optical_x()
    ya, _ = _db().ep_raised_y()
    sx0, sx1 = x0 + SLOT_WEB, x1 - SLOT_WEB
    sy0 = ya + SLOT_WEB
    sy1 = sy0 + j4_socket_len() + 2.0 * SLOT_CLR
    wl = DK.walls()
    assert wl["b0"] + SLOT_WEB < sy0 and sy1 < wl["b1"] - SLOT_WEB, (
        "the J4 slot reaches a side rail: move the header, not the rail", (sy0, sy1), wl)
    return sx0, sx1, sy0, sy1


def j4_centre() -> tuple:
    """(x, y) of J4's body centre in instrument mm: the strip's middle in X, in the slot in Y."""
    x0, _ = optical_x()
    _, _, sy0, _ = j4_slot()
    return x0 + OPT_BOARD_W / 2.0, sy0 + SLOT_CLR + j4_socket_len() / 2.0


def j4_pose() -> tuple:
    """(x, y, z) of J4's F.Fab body middle, 0.5 off the face it stands on (the board's underside):
    what new_boards_view.header_pose reads, the way every other board's header is measured."""
    cx, cy = j4_centre()
    return cx, cy, PLINTH_TOP - 0.5


def _j4_socket_z() -> float:
    """The socket's mating face, down from the board's underside."""
    from . import ribbon_socket as RS
    return PLINTH_TOP - RS.MOUTH


def j4_ribbon_exit() -> tuple:
    """Where the ribbon leaves the panel's underside, down into the body cavity."""
    from . import ui_panel as UP
    cx, cy = j4_centre()
    return cx + UP.IDC_BODY_R / 2.0 + 1.0 + UP.RIBBON_T / 2.0, cy, BZ


def j4_ribbon_in_slot() -> float:
    """The ribbon's length from the socket to the panel's underside: out +X, then down."""
    from . import ui_panel as UP
    cx, _ = j4_centre()
    return (j4_ribbon_exit()[0] - (cx + UP.IDC_BODY_R / 2.0)) + (_j4_socket_z() - UP.IDC_CABLE_M - BZ)


def j4_parts() -> list:
    """J4's plastic under the stand-in, the IDC socket on it, and the ribbon down the slot."""
    from . import ui_panel as UP
    cx, cy = j4_centre()
    bx, by = J4_BODY
    hdr = DK._box(cx - bx / 2, cx + bx / 2, cy - by / 2, cy + by / 2, PLINTH_TOP - J4_PLASTIC, PLINTH_TOP)
    L, r = j4_socket_len(), UP.IDC_BODY_R
    zm = _j4_socket_z()
    sock = DK._box(cx - r / 2, cx + r / 2, cy - L / 2, cy + L / 2, zm - UP.IDC_BODY_M, zm)
    zc = zm - UP.IDC_BODY_M - UP.IDC_GAP
    sock = sock.union(DK._box(cx - r / 2, cx + r / 2, cy - L / 2, cy + L / 2, zc - UP.IDC_COVER_M, zc))
    # the ribbon: out of the body/cover gap toward +X, then straight down the slot past the panel
    w, t = 2 * OPT_J4_N * 0.635, UP.RIBBON_T
    zr = zm - UP.IDC_CABLE_M
    xe = j4_ribbon_exit()[0]
    rib = DK._box(cx + r / 2, xe + t / 2, cy - w / 2, cy + w / 2, zr - t / 2, zr + t / 2)
    rib = rib.union(DK._box(xe - t / 2, xe + t / 2, cy - w / 2, cy + w / 2, BZ - 6.0, zr + t / 2))
    sx0, sx1, sy0, sy1 = j4_slot()
    assert sx0 < cx - r / 2 and xe + t / 2 < sx1 and sy0 < cy - L / 2 and cy + L / 2 < sy1, (
        "J4's socket or ribbon does not fit its slot")
    return [("optical_j4", hdr), ("optical_idc", sock), ("optical_idc_ribbon", rib)]


def _j4_piece(nm: str) -> cq.Workplane:
    return dict(j4_parts())[nm]


def _brain_j4_pinout() -> tuple:
    """Brain J4's ways, read off elec/brain_board.py's own pin table (as tools read elec/fab.py),
    not imported: the generator builds a netlist on import."""
    import os
    import re
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "elec", "brain_board.py"), encoding="utf-8").read()
    blk = src[src.index('ref="J4"'):]
    blk = blk[blk.index("for pin, net in ("):blk.index("):")]
    ways = re.findall(r"\((\d+),\s*(opt_5v|gnd|io\[\"(\w+)\"\])\)", blk)
    out = {}
    for n, net, io in ways:
        out[int(n)] = io or {"opt_5v": "+5V", "gnd": "GND"}[net]
    assert sorted(out) == list(range(1, 2 * OPT_J4_N + 1)), ("brain J4's pin table did not parse", out)
    return tuple(out[n] for n in sorted(out))


def check_j4_mirror() -> None:
    """The optical end carries brain J4's ways pin for pin (a straight-through IDC ribbon)."""
    b = _brain_j4_pinout()
    bad = [(i + 1, x, y) for i, (x, y) in enumerate(zip(b, OPT_J4_PINOUT)) if x != y]
    assert not bad, "optical J4 does not mirror brain J4 (pin, brain, optical): %s" % bad


def filler(slot: int) -> cq.Workplane:
    a, b = slot_x(slot)
    return _body(a, b)


def _cavity(ctr: float, grow: float = 0.0) -> cq.Workplane:
    return box_at(DL.CAVITY_X + 2 * grow, DL.CAVITY_Y + 2 * grow, (TZ - BZ) + 2,
                  x=ctr, y=DL.PLATE_CTR_Y, z=(BZ + TZ) / 2)


def pickup_piece(pos: int = PIECE_POS) -> cq.Workplane:
    """v1's _pickup_piece at slot position `pos`: solid deck but for the cavity and the jacks' bores,
    the -Y skirt and the two end walls under it, the retention screw's relief and slot."""
    x0, x1, c = piece_x(pos)
    body = _body(x0, x1).cut(_cavity(c))
    body = body.union(box_at(x0 - x1, SKIRT_T, BZ - DL.SKIRT_DEEP_BOT,
                             x=c, y=-(DL.HY_CLAMP + SKIRT_T / 2), z=(BZ + DL.SKIRT_DEEP_BOT) / 2))
    ya = -DL.HY_CLAMP
    for xe in (x0 - WALL / 2, x1 + WALL / 2):
        body = body.union(box_at(WALL, END_WALL_Y1 - ya, BZ - DL.SKIRT_DEEP_BOT,
                                 x=xe, y=(ya + END_WALL_Y1) / 2, z=(BZ + DL.SKIRT_DEEP_BOT) / 2))
    # the retention screw's relief over its boss, and its slot through the -Y skirt (v1's, after
    # every union: a later union would refill them)
    body = body.cut(box_at(DL.RET_RELIEF_W, DL.RET_RELIEF_Y1 - DL.RET_RELIEF_Y0,
                           DL.RET_RELIEF_Z1 - BZ + 0.5, x=c,
                           y=(DL.RET_RELIEF_Y0 + DL.RET_RELIEF_Y1) / 2, z=(BZ - 0.5 + DL.RET_RELIEF_Z1) / 2))
    body = body.cut(box_at(DL.RET_SLOT_W, SKIRT_T + 2.0, BZ - DL.RET_SLOT_Z0, x=c,
                           y=-(DL.HY_CLAMP + SKIRT_T / 2), z=(BZ + DL.RET_SLOT_Z0) / 2))
    # the jacks: each head captured in the solid deck from the top, through cadkit's counterbore
    for dx, jy in JACKS:
        body = cut_counterbore(body, DL.HEAD_POCKET_D, TZ - DL.JACK_HEAD_Z,
                               M4.shaft_clr_d + 0.4, TZ - (BZ - 1.0),
                               (c + dx, jy, TZ), (0.0, 0.0, -1.0),
                               print_up=FILL_UP, overshoot=1.0)
    for dx, jy in JACKS:
        body = body.cut(cyl(M4.boss_od + D.BEAD, DL.JACK_BOSS_RELIEF + 0.5, z=BZ - 0.5)
                        .translate((c + dx, jy, 0.0)))
    return heal(body)


def pickup_plate(pos: int = PIECE_POS) -> cq.Workplane:
    """v1's height plate, at the piece's centre."""
    return DL.pickup_zplate.translate((piece_x(pos)[2] - DL.PICKUP_X_NOM, 0.0, 0.0))


def _mount_hardware(pos: int = PIECE_POS) -> list:
    """The pickup, its three jacks (screw + insert nut) and its retention screw + insert: v1's
    _pickup_mount_components, at the piece's centre."""
    from cadkit.fasteners import insert as f_insert, headed_screw, seated_insert, m4_button_screw
    c = piece_x(pos)[2]
    out = [("pickup", PM.pickup_demo().translate((c, DL.PK_CTR_Y, PM.PK_TOP)))]
    js, ji = None, None
    for dx, jy in JACKS:
        s = headed_screw(M4, DL.JACK_SCREW_L, head_d=DL.JACK_HEAD_D, head_h=DL.JACK_HEAD_H,
                         socket_af=2.5).translate((c + dx, jy, DL.JACK_HEAD_Z + DL.JACK_HEAD_H))
        n = f_insert(M4).translate((c + dx, jy, DL.JACK_MOUTH_Z))
        js = s if js is None else js.union(s)
        ji = n if ji is None else ji.union(n)
    out += [("pickup_jack_screw", js), ("pickup_jack_insert", ji)]
    g = m4_button_screw(DL.RET_SCREW_L).rotate((0, 0, 0), (1, 0, 0), 90)       # head -Y, tip +Y
    gb = g.val().BoundingBox()
    out.append(("pickup_ret_screw", g.translate((c, DL.PK_YM - gb.ymax, DL.RET_SCREW_Z))))
    out.append(("pickup_ret_insert", seated_insert(M4, (c, DL.PK_MAX_YM - DL.RET_BOSS_L,
                                                        DL.RET_SCREW_Z), (0, 1, 0))))
    return out


def parts(pos: int = PIECE_POS) -> list:
    check_j4_mirror()
    out = [("deck_optical", kept(optical_panel)), ("optical_board", kept(optical_board))]
    out += [(nm, made_of(kept(_j4_piece, nm), m)) for nm, m in
            (("optical_j4", "nylon"), ("optical_idc", "nylon"), ("optical_idc_ribbon", "pvc"))]
    out += [
           ("deck_pickup", kept(pickup_piece, pos)), ("pickup_plate", kept(pickup_plate, pos))]
    held = range(pos, pos + PIECE_SLOTS)
    k = 0
    for i in range(N_SLOTS):
        if i not in held:
            k += 1
            out.append((f"deck_filler_{k}", kept(filler, i)))
    return out + _mount_hardware(pos)


def report() -> str:
    x0, x1 = optical_x()
    c = [round(piece_x(p)[2], 2) for p in range(N_POS)]
    return (f"optical panel x {x0:.2f}..{x1:.2f} ({x1 - x0:.2f}); sensors at {sense_x():.2f}, "
            f"{SENSE_D} off the termination at {termination_x():.2f}\n"
            f"slots: {N_SLOTS} x {band_w():.2f} (pitch {pitch():.3f}), region {slot0_x():.2f}..{region_end():.2f}\n"
            f"piece {PIECE_SLOTS} slots = {piece_x()[0] - piece_x()[1]:.2f}; pickup centre at the {N_POS} "
            f"positions {c}, each +-{DL.X_SLIDE} on the plate")
