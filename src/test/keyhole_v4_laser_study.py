"""KEYHOLE v4: LASER-CUT STACK (user, 2026-11-22: "CNC is way too expensive, we'll need to find a way
to do our best with stacked laser cut parts").

Same goals as v3 (src/test/keyhole_v3_study.py): .080 with room for its swell, seated only HOLE UP,
two states only (seated, or back out of the entry). Same frame: +X face at x = 0, ball side x = -7.

Laser sheets cut only straight through, so v3's 20 deg knife is out. What replaces it:

  LOAD   3 mm (x -3..0): the slit (SLIT_W, through, round bottom) and the entry hole.
  POCKET 2 + 2 mm (x -7..-3), one outline: the slit, a 4.2 x 3.2 RECTANGLE round the axis that
         only a hole-up ball fits (a sideways one is 3 across and goes straight through the slit
         instead), and the entry hole.
  ENTRY  Ø ENTRY_D, its centre placed so its rim passes EXACTLY through the pocket's top corner at
         the slit's edge (y = +-SLIT_W/2, z = POCKET_Z/2). The steel between the seat and the entry
         is then a sliver with a point at the slit's edge, growing only to ~0.36 tall where the
         ball's side is: that is all the "wall" a ball could stop on, and the ball reaches it on its
         point. The pull (the string's wrap acts through the ball's axis) is then nearly always
         above or below the contact, so it tips into the seat or into the entry.

  The ball bears on the load sheet's slit edges (two lines, 3 long), flush 0.8 under the -X face.
  Sheets >= 2 mm per the laser rule that a cut is no narrower than the sheet (pocket 3.2 tall).

    PYTHONPATH=. py -3.12 src/test/keyhole_v4_laser_study.py
"""
from __future__ import annotations

import math
import os
import sys

import cadquery as cq

sys.path.insert(0, os.path.dirname(__file__))
import keyhole_v3_study as V3                                 # noqa: E402  (ball, rest_x, contact_span, blank)

from src import direct_bench as B                             # noqa: E402

T = 7.0
LOAD_T = 3.0
POCKET_T = T - LOAD_T                    # 2 + 2
SLIT_W = V3.SLIT_W                       # 3.2
SLIT_Z0 = V3.SLIT_Z0                     # -3.2
POCKET_Y = V3.BALL_D + 0.25              # 4.25 (4.15 at -0.1 left a far-proud roll trap)
POCKET_Z = V3.BALL_L + 0.2               # 3.2
ENTRY_D = 5.4
CUSP_Y = 1.5                             # the entry rim meets the pocket top 0.1 inside the slit edge:
                                         # at 1.6 (+-0.1) a 70-75 deg roll threaded past the cusp to rest 0.7 proud
ARM_LO = -2.15                           # the POCKET sheets' slit stops here (flat): a sideways ball on
                                         # the axis (z -2) still drops through; a 70 deg roll (z -2.4) does not
_yc, _zc = CUSP_Y, POCKET_Z / 2
Z_ENTRY = _zc + math.sqrt((ENTRY_D / 2) ** 2 - _yc ** 2)    # 3.78: the rim through the corner


def _profile_cuts(pocket: bool, x0: float, x1: float) -> cq.Workplane:
    L = x1 - x0
    r = SLIT_W / 2
    if pocket:                           # flat-bottomed at ARM_LO, plus the pocket
        c = (B.box_at(L + 2, SLIT_W, Z_ENTRY - ARM_LO, x=(x0 + x1) / 2, y=0, z=(Z_ENTRY + ARM_LO) / 2)
             .union(B.box_at(L + 2, POCKET_Y, POCKET_Z, x=(x0 + x1) / 2, y=0, z=0)))
    else:                                # the load sheet: round bottom at SLIT_Z0
        c = (B.cyl_x(SLIT_W, L + 2, x0 - 1, y=0, z=SLIT_Z0 + r)
             .union(B.box_at(L + 2, SLIT_W, Z_ENTRY - (SLIT_Z0 + r), x=(x0 + x1) / 2, y=0,
                             z=(Z_ENTRY + SLIT_Z0 + r) / 2)))
    c = c.union(B.cyl_x(ENTRY_D, L + 2, x0 - 1, y=0, z=Z_ENTRY))
    return c


def sheets() -> dict:
    blank = V3._blank()
    out = {}
    for nm, x0, x1, pocket in (("load_3", -LOAD_T, 0.0, False),
                               ("pocket_2a", -LOAD_T - 2.0, -LOAD_T, True),
                               ("pocket_2b", -T, -LOAD_T - 2.0, True)):
        s = blank.intersect(B.cyl_x(3 * B.YK_D, x1 - x0, x0, y=0, z=0)).cut(_profile_cuts(pocket, x0, x1))
        out[nm] = s
    return out


def plate() -> cq.Workplane:
    s = list(sheets().values())
    w = s[0]
    for o in s[1:]:
        w = w.union(o)
    return w


def sliver_heights():
    """The steel between the pocket's top and the entry's rim, at the ball's side columns."""
    R = ENTRY_D / 2
    return [(y, Z_ENTRY - math.sqrt(R * R - y * y) - _zc) for y in (1.6, 1.7, 1.8, 1.9, 2.0, 2.1)]  # from the slit edge out


def report():
    p = plate()
    print(f"load {LOAD_T} + pocket {POCKET_T} (2+2); slit {SLIT_W}, pocket {POCKET_Y} x {POCKET_Z}, "
          f"entry Ø{ENTRY_D} at z {Z_ENTRY:.2f} (was KEY_Z {B.KEY_Z})")
    print("sliver (seat/entry web) height at y:", ", ".join(f"{y:.1f}:{h:.2f}" for y, h in sliver_heights()))
    print("roll phi -> centre stops (depth from the -X face; seated hole-up = +1.2... flush is 3.2+)")
    rows = []
    for phi in range(0, 91, 5):
        x = V3.rest_x(phi, 0.0, p)
        d = math.inf if x == math.inf else x - V3.X_FACE
        rows.append((phi, d))
        print(f"  phi {phi:3d}: " + ("THROUGH" if d == math.inf else f"{d:+.2f}"))
    print("hole-up ball, centre height z_c -> contact span, verdict")
    for zc in (0.0, 0.1, 0.3, 0.6, 1.0, 1.4, 1.55, 1.6, 1.65, 1.7, 1.75, 1.8, 1.9, 2.0, 2.5, 3.0, 3.5, Z_ENTRY):
        c = V3.contact_span(0, zc, p)
        if c is None:
            print(f"  z_c {zc:5.2f}: THROUGH"); continue
        x, z0, z1 = c
        if z0 - 0.02 <= zc <= z1 + 0.02:
            st = f"RESTS (band {z1 - z0:.2f})"
        elif zc < z0:
            st = "tips DOWN"
        else:
            st = "tips UP"
        print(f"  z_c {zc:5.2f}: centre {x - V3.X_FACE:+.2f} deep, touches z {z0:+.2f}..{z1:+.2f}: {st}")
    print("any roll at the entry:")
    for phi in (0, 30, 45, 60, 90):
        print(f"  phi {phi}: {'THROUGH' if V3.rest_x(phi, Z_ENTRY, p) == math.inf else 'BLOCKED'}")
    return rows


if __name__ == "__main__":
    report()
    os.makedirs("out/keyhole_v4", exist_ok=True)
    for nm, s in sheets().items():
        cq.exporters.export(s, f"out/keyhole_v4/keyplate_v4_{nm}.step")
    print("wrote out/keyhole_v4/keyplate_v4_*.step")
