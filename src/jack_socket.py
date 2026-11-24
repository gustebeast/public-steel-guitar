"""THE JACK NUT SOCKET (user, 2026-11-23): a small printed tool that ships with the instrument and
turns the 1/4" jack's (J5, Neutrik NMJ*HCD2) panel nut -- no metal socket needed.

The nut sits sunk in a counterbore in the +X endplate's face. The socket is a hex (the nut's A/F
+ SOCKET_CLR a side) in a round body with 1.6 of wall at the hex's corners (user: "we could likely
get away with 1.6mm walls around the nut"). TURNED WITH THE STOWED 2.5 HEX KEY AS A LEVER (user:
"just to get leverage"): a round CROSS HOLE through the body under the socket takes the key's long
arm, a T-handle -- no knob, and still one tool for the instrument.

Everything is READ from the jack's panel spec (cadkit PANEL: the nut's A/F and head) and the brain
board's pocket export (the counterbore's depth), and the counterbore and boss the endplate needs
are DERIVED here (CBORE_D, BOSS_D) and handed to src.board_geom's PANEL override, which the pocket
export reads -- so the hole, the boss and the tool cannot drift apart.

Printed on its closed end, the socket's open hex up (in the layers: nothing hangs); the cross
hole a teardrop. PETG-GF on the 0.8 nozzle.
"""

from __future__ import annotations

import json
import math
import os

import cadquery as cq
from cadkit.board_geom import PANEL as _CK_PANEL

from . import dimensions as D

JACK_FPS = ("Jack_6.35mm_Neutrik_NMJ6HCD2_Horizontal", "Jack_6.35mm_Neutrik_NMJ4HCD2_Horizontal")
NUT_AF, NUT_HEAD = _CK_PANEL[JACK_FPS[0]]["nut"][:2]          # 11.0, 2.05
assert all(_CK_PANEL[n]["nut"] == _CK_PANEL[JACK_FPS[0]]["nut"] for n in JACK_FPS), "one nut for both jacks"

SOCKET_CLR = 0.2                                 # a side, on the hex's flats (printed hex, metal nut)
SOCKET_WALL = D.MIN_WALL_2P                      # 1.6 at the hex's corners: two beads
CBORE_CLR = 0.3                                  # a side, the socket in the counterbore
SOCKET_AF = NUT_AF + 2 * SOCKET_CLR              # 11.4
SOCKET_CORNER = SOCKET_AF / math.cos(math.pi / 6)                # 13.16
SOCKET_OD = SOCKET_CORNER + 2 * SOCKET_WALL      # 16.36
CBORE_D = round(SOCKET_OD + 2 * CBORE_CLR, 2)    # 16.96: the face's counterbore
BOSS_D = round(CBORE_D + 2 * SOCKET_WALL, 2)     # 20.16: the boss behind it keeps 1.6 round it

KEY_AF = 2.5                                     # the stowed hex key (one tool for the instrument)
KEY_HOLE = 3.2                                   # its cross hole's FIT size (corners 2.89 + play)
assert KEY_HOLE > KEY_AF / math.cos(math.pi / 6), "the key's corners do not pass its hole"
HANDLE_L = KEY_HOLE + 2 * SOCKET_WALL + 1.6      # the body under the socket: the hole, a wall each
                                                 # side and the teardrop's peak
STANDOFF = 0.5                                   # the body stays this far off the face


def _cbore_depth() -> float:
    """The counterbore's depth, from the brain board's pocket export (J5)."""
    p = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "brain_board_pocket.json"), encoding="utf-8"))
    for c in p["parts_past_inner_face"]:
        if c.get("cbore"):
            return c["cbore"]["depth"]
    raise KeyError("no counterbore in brain_board_pocket.json")


def socket_len() -> float:
    """The socket's reach: into the counterbore to its floor, plus the standoff."""
    return _cbore_depth() + STANDOFF


def body() -> cq.Workplane:
    """The tool, as printed: its closed end on the bed (z 0), the socket's open hex up, the key's
    cross hole through the handle below it."""
    from cadkit.holes import teardrop_hole
    L = socket_len()
    assert NUT_HEAD <= L - STANDOFF + 1e-6, "the socket cannot reach over the nut's head"
    w = cq.Workplane("XY").circle(SOCKET_OD / 2).extrude(HANDLE_L + L)
    w = w.faces("<Z").edges().chamfer(D.BEAD)                   # the bed edge: no elephant's foot
    w = w.cut(cq.Workplane("XY").polygon(6, SOCKET_CORNER).extrude(L + 1).translate((0, 0, HANDLE_L)))
    zc = SOCKET_WALL + KEY_HOLE / 2
    w = w.cut(teardrop_hole(KEY_HOLE, SOCKET_OD + 2, axis_point=(-SOCKET_OD / 2 - 1, 0, zc),
                            axis_dir=(1, 0, 0), print_up=(0, 0, 1), fit=True))
    return w


if __name__ == "__main__":
    print(f"socket hex {SOCKET_AF} A/F ({SOCKET_CORNER:.2f} corners), OD {SOCKET_OD:.2f}, reach "
          f"{socket_len():.2f}, handle {HANDLE_L:.2f}; counterbore {CBORE_D}, boss {BOSS_D}")
    b = body().val()
    bb = b.BoundingBox()
    print("valid", b.isValid(), "volume", round(b.Volume(), 1), "height", round(bb.zlen, 2))
