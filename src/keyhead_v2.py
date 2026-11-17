"""The v2 keyhead (-X) endplate, for the direct body (user, 2026-11-13).

EVERY SCREW ON THE -X FACE. The nut block is nut_block_v2: from the top of that face down, the side
screws, the plier window, the height screws (along X, on the plates' 45 degree wedges). The endplate
is one print, the bed its -X face (PRINT_UP +X), so every screw bore is along the build axis and
prints round.

The body clamps to it as it does to the +X endplate (direct_bench.kh_x, mirrored from ep_x): each
wall bar's -X end sits in a pocket EP_POCKET deep and stops EP_GAP short of its floor, and two M3s
through the back wall, heads in recesses flush with the -X face, pull the endplate onto the walls'
ends. The slab is the body's whole section (and stands to the nut block's top), from the -X face to
the joint x_kj; the nut block's prism runs on +X of it to its own +X face, over the pockets.

The wrap rod slides in from the -Y face down its bore, and is pushed back out from the +Y face
with the 2.5 key.
"""
from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from . import direct_bench as DB
from . import nut_block_v2 as NB
from .helpers import box_at, cyl_x
from cadkit.holes import teardrop_hole
from cadkit.kept import kept

PRINT_UP = (1.0, 0.0, 0.0)                      # the -X face on the bed
AT = (D.NUT_BLOCK_X, 0.0, D.STRING_Z)           # nut block local -> world
NB_FLOOR_W = 2 * D.MIN_WALL_2P                  # under the plates' slots
# THE +X FACE THICKENS UNDER THE FRETBOARD (user, 2026-11-13). At the top it is the 0.8 in front of the
# plates' pockets, so the crown stands right at the zero fret line; below the fretboard's stack it grows
# FACE_EXTRA +X. The stack is src.deck_v2's: its LED board butts this face, and its cradle's lips are the
# lowest thing that reaches it (deck_v2.STACK_BOT); the step is half a millimetre under them.
FACE_EXTRA = 3 * D.BEAD                          # 0.8 -> 3.2 of wall


def face_step_z() -> float:
    """World z under which the +X face stands FACE_EXTRA further +X: under the deck's stack."""
    from . import deck_v2 as DK
    return DK.STACK_BOT - 0.5


def face_thickening_local() -> cq.Workplane:
    """The block's added +X face, nut block local frame: its bottom to face_step_z."""
    z0 = NB.HS_FLOOR - NB_FLOOR_W
    z1 = face_step_z() - D.STRING_Z
    return box_at(FACE_EXTRA + 0.01, NB.HW - NB.Y_LO, z1 - z0, x=NB.X_FRONT + (FACE_EXTRA - 0.01) / 2,
                  y=(NB.HW + NB.Y_LO) / 2, z=(z0 + z1) / 2)


def _local(w: cq.Workplane) -> cq.Workplane:
    return w.translate(AT)


def extents() -> dict:
    (_, _), (y0, y1), (z0, _) = DB.body_box()["outer"]
    k = DB.kh_x()
    return dict(x0=k["x0"], x_kj=k["x_kj"], x1=D.NUT_BLOCK_X + NB.X_FRONT, y0=y0, y1=y1, z0=z0,
                z1=D.STRING_Z + NB.NUT_TOP, nb_y0=NB.Y_LO, nb_y1=NB.HW,
                nb_z0=D.STRING_Z + NB.HS_FLOOR - NB_FLOOR_W, deck_under=_deck_under())


def _deck_under() -> float:
    from .deck_layout import DECK_UNDER
    return DECK_UNDER


def _keyhead() -> cq.Workplane:
    e, k = extents(), DB.kh_x()
    xa = e["x0"]
    from . import deck_v2 as DK
    zs = DK.TZ                                   # THE STRIP STANDS TO THE TOP PANELS' TOP (user, 2026-11-14):
                                                 # flush with the deck past the nut block, which alone rises
                                                 # to the nut's top (the union below) -- the deck panels end
                                                 # at the strip's +X face (deck_v2)
    w = box_at(e["x_kj"] - xa, e["y1"] - e["y0"], zs - e["z0"],
               x=(xa + e["x_kj"]) / 2, y=(e["y0"] + e["y1"]) / 2, z=(e["z0"] + zs) / 2)
    w = w.union(box_at(e["x1"] - xa, e["nb_y1"] - e["nb_y0"], e["z1"] - e["nb_z0"],
                       x=(xa + e["x1"]) / 2, y=(e["nb_y0"] + e["nb_y1"]) / 2,
                       z=(e["nb_z0"] + e["z1"]) / 2))
    w = w.union(_local(face_thickening_local()))
    # the nut block's cuts, fused first (one subtraction against the slab)
    cut = NB.all_pockets().union(NB.lanes()).union(NB.plier_window())
    cut = cut.union(NB.all_side_screw_negatives()).union(NB.all_height_screw_negatives())
    cut = cut.union(NB.rod_bore())
    w = w.cut(_local(cut))
    # THE ROD'S WAY IN: the rod's centre is 2 +X of the strip's joint face, so its way past the block
    # on -Y is a SLOT in that face, from the block's -Y face out through the -Y face, the bore's height
    # (no ceiling: it opens toward +X, the build direction). The rod goes in and out with the keyhead
    # off the body -- the strings off; it is an axle, not a service part.
    rx, rz, rr = D.NUT_BLOCK_X + NB.ROD_X, D.STRING_Z + NB.ROD_Z, NB.ROD_BORE / 2
    w = w.cut(box_at(e["x_kj"] + 1.0 - (rx - rr), e["nb_y0"] - e["y0"] + 1.01, 2 * rr,
                     x=(e["x_kj"] + 1.0 + rx - rr) / 2, y=(e["y0"] - 1.0 + e["nb_y0"] + 0.01) / 2,
                     z=rz))
    # the rod's push hole on out through the +Y face (now the strip's: the body's)
    w = w.cut(_local(teardrop_hole(NB.ROD_PUSH_D, e["y1"] - NB.ROD_Y1 + 1.0,
                                   axis_point=(NB.ROD_X, NB.ROD_Y1, NB.ROD_Z),
                                   axis_dir=(0.0, 1.0, 0.0), print_up=PRINT_UP)))
    # the bar clamp: each bar's pocket, its two M3s and their flush head recesses
    from cadkit.fasteners import stepped_bore_cutter
    for yc in DB.bar_y():
        w = w.cut(DB._bar_box(yc, k["wall0"], e["x_kj"] + 1.0, DB.BAR_CLR))
        for zc in DB.EP_SCREW_Z:
            w = w.cut(stepped_bore_cutter([(DB.EP_TUNNEL, k["wall1"] - xa + 1.0),
                                           (DB.EP_M3_CLR, k["wall0"] - k["wall1"] + 0.5)],
                                          (xa - 1.0, yc, zc), (1.0, 0.0, 0.0), print_up=PRINT_UP))
    return w


def _screws() -> cq.Workplane:
    """The four M3 SHCS and washers, heads flush with the -X face, into the bars' -X ends."""
    from . import m3_hardware as BTn
    k = DB.kh_x()
    out = None
    for yc in DB.bar_y():
        for zc in DB.EP_SCREW_Z:
            top = k["wall1"] - DB.EP_WASHER[1] - BTn.HEAD_H
            sc = DB._cap("m3", DB.bar_screw_len(-1), (top, yc, zc), (1, 0, 0))
            sc = sc.union(cyl_x(DB.EP_WASHER[0], DB.EP_WASHER[1], k["wall1"] - DB.EP_WASHER[1], y=yc, z=zc)
                          .cut(cyl_x(3.2, DB.EP_WASHER[1] + 1, k["wall1"] - DB.EP_WASHER[1] - 0.5,
                                     y=yc, z=zc)))
            out = sc if out is None else out.union(sc)
    return out


_PER_STRING = {"kh_plate": "plate", "kh_shoe": "shoe", "kh_side_screw": "side_screw", "kh_side_insert": "side_insert",
               "kh_height_screw": "height_screw", "kh_height_insert": "height_insert"}


def _one(fn: str, i: int) -> cq.Workplane:
    return _local(getattr(NB, fn)(i))


def _rod():
    return _local(NB.rod())


def parts() -> list:
    """Every keyhead part, each kept on its own (per string, indexed, so the gate pairs each screw
    with its own insert)."""
    out = [("keyhead", kept(_keyhead)), ("kh_m3", kept(_screws)), ("kh_rod", kept(_rod))]
    for nm, fn in _PER_STRING.items():
        out += [(f"{nm}_{i}", kept(_one, fn, i)) for i in range(D.N_STRINGS)]
    return out
