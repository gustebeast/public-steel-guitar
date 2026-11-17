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
    return w.union(DK._box(x0, x1, ya, yb, TZ - 0.01, PLINTH_TOP))


def optical_board() -> cq.Workplane:
    """STAND-IN: v1's sensor strip, its -X edge on the panel's, flat on the plinth."""
    x0, _ = optical_x()
    ya, yb = _db().ep_raised_y()
    return DK._box(x0, x0 + OPT_BOARD_W, ya + 1.0, yb - 1.0, PLINTH_TOP, PLINTH_TOP + OP.PCB_T)


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
    out = [("deck_optical", kept(optical_panel)), ("optical_board", kept(optical_board)),
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
