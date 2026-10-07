"""Which way should each board's lettering read? Worked out from where the CAD puts it.

    py -3.12 -m tools.silk_read            # every board
    py -3.12 -m tools.silk_read pi_cap

Prints, per board, the `silk_read` its generator should declare (cadkit/kicad_silk.py:
0, 90, 180 or 270) and the pose it came from. It only REPORTS: the number is written
into elec/<board>.py by hand, with the reason, because a board that is placed several
times or turned over in service needs a person to say which view counts.

THE VIEWER (src/dimensions.py: the player sits at -Y, +X to their right, +Z up):
  * a board lying flat, front up     -- read from the player's side: text runs +X, tops +Y
  * a board lying flat, front DOWN   -- read with the instrument rolled over about its
                                        long axis, as it is on a bench: text runs +X,
                                        tops toward -Y
  * a board standing up              -- tops toward +Z, read from the side its front faces
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "elec"))

import cadquery as cq                                   # noqa: E402

from cadkit import board_check as CHK                   # noqa: E402
from src import board_geom as BG                        # noqa: E402
import cad_geom_check as CGC                            # noqa: E402

AX = {(1, 0, 0): "+X", (-1, 0, 0): "-X", (0, 1, 0): "+Y", (0, -1, 0): "-Y",
      (0, 0, 1): "+Z", (0, 0, -1): "-Z"}


def _name(v):
    return AX.get((round(v.x), round(v.y), round(v.z)), "(%.2f, %.2f, %.2f)" % (v.x, v.y, v.z))


def read_of(board):
    solid, _ink = CGC._cad(board)
    shape = solid.val() if hasattr(solid, "val") else solid
    (_m, mirrored, _p, (c, u, v, n)), _pl, _parts = CHK._find_pose(
        shape, BG.load(board), CHK.NO_BODY_PREFIX)
    if abs(n.z) > 0.5:                                  # lying flat
        top = cq.Vector(0, 1, 0) if n.z > 0 else cq.Vector(0, -1, 0)
    else:                                               # standing
        top = cq.Vector(0, 0, 1)
    right = top.cross(n)
    best = max((0, 90, 180, 270), key=lambda a: (
        (u if a == 0 else v if a == 90 else u * -1 if a == 180 else v * -1).dot(right)))
    return best, _name(n), _name(u), _name(v), mirrored


def main(argv):
    for b in (argv or CGC.BOARDS):
        try:
            a, n, u, v, mir = read_of(b)
            print("%-24s silk_read %3d   front faces %s, board +x is %s, board +y is %s%s"
                  % (b, a, n, u, v, "   !! MIRRORED POSE" if mir else ""))
        except Exception as exc:
            print("%-24s COULD NOT READ THE POSE: %s" % (b, exc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
