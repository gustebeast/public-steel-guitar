"""FIT FINDERS, ROUND 3: the smallest joint that prints AS DRAWN, per print-orientation pair.

    py -3.12 -m src.test.fit_round3            # the table, and every corner's radius
    py -3.12 -m src.test.fit_round3 --export   # ...and write src/test/test_fit3_plate_petg_gf.step

WHY (src/test/corner_radius.py, the user's calipers, 2026-10-14, PETG-GF at a 0.8 nozzle).
A corner the NOZZLE makes -- the profile lying in the layer plane -- does not print as
drawn: a CONVEX one comes out about 1.9-2.0 round whatever is drawn under that, and
from 2.0 drawn it tracks the drawing about 0.4 rounder; a CONCAVE one comes out about
1.05 until 0.5 is drawn, then follows it. A corner made by LAYER STACKING -- the profile
standing across the layers -- is assumed to print as drawn. Today's joints have no room
for that: the seam's head is 2.66 deep and the endplate tenon's 1.6, where two 2 mm
corners need 4, so their printed heads are beads, not the T's on the drawing.

THE RULE every coupon here is drawn to, on each NOZZLE-MADE half: convex corners at
CONVEX_R (2.0, prints ~2.4), concave at CONCAVE_R (0.5, prints ~1.1), and room for them
(a face carrying two convex corners is 2 * CONVEX_R long plus a bead of flat -- with no
flat at all the two arcs meet tangent and the second will not build). A LAYER-MADE half is
drawn to MATCH its mate (it prints as drawn): concave corners at the mate's convex
radius plus the clearance, convex at its concave radius -- so the model shows the gap
that prints, not a sharp pocket round a round head. The user (2026-10-14): test the smallest such joint for each
orientation pair the instrument uses, all in PETG-GF, before any joint in it changes.

  NOZZLE / NOZZLE  (drop-in tee: chassis seam, pedal-bar splice, bar-latch rail)
    TEE    neck NECK_W, head HEAD_W x HEAD_D, socket lip LIP_T: the smallest T whose every
           corner fits the rule (head overhang = CONCAVE_R + CONVEX_R a side, plus a half bead of flat).
    ROUND  the same neck into a ROUND head, radius BULB_R -- a circle has no corner to
           lose, so it may print truer in less room. Same lip.
  NOZZLE / LAYER   (chassis -> endplate mushroom): cadkit's own mushroom, its waist grown
           (joint depth) until the tenon's flat top and the corners either side of the
           waist fit the rule; the socket, layer-made, keeps its 45 degree roof, rounded to match.
  LAYER / LAYER    (octagon: knee lever, leg section, cover rail): unchanged in shape;
           its clearances again round round 2's good 0.20 (two of those cells were lost).

Clearance steps start from round 2's sharp results, the nearest thing to these shapes
(a sharp nozzle corner already printed ~2 mm round): seam 0.25 tight / 0.35 loose,
endplate 0.20 at 0.50 depth good. Same layout as before: token N beside cell N.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import sys

import cadquery as cq

from src import dimensions as D
from . import fit_finder as F
from . import fit_round2 as R2

HERE = pathlib.Path(__file__).resolve().parent
CONVEX_R = 2.0               # a nozzle-made convex corner: prints ~2.4
CONCAVE_R = 0.5              # a nozzle-made concave corner: prints ~1.1
NOZZLE_HALF = (CONVEX_R, CONCAVE_R)
WALL = 2 * D.BEAD            # 1.6, every socket wall
BACK = 4 * D.BEAD            # 3.2 behind a drop-in socket's head: its number is cut there,
                             # 1.6 deep, and leaves a full wall

NECK_W = 2 * D.BEAD                                 # 1.6, the quality tier
HEAD_W = NECK_W + 2 * (CONCAVE_R + CONVEX_R + D.BEAD / 2)   # 7.4: each overhang a root, a
                                                    # corner and a half bead of flat between
HEAD_D = 2 * CONVEX_R + D.BEAD                      # 4.8: two convex corners and a bead of flat
LIP_T = 2 * CONVEX_R + D.BEAD                       # 4.8: the socket lip's two, likewise
BULB_R = 3 * D.BEAD                                 # 2.4: the round head (4.8 across)
WAIST = 4 * D.BEAD                                  # 3.2: the mushroom waist (cadkit's is 1.6)
MUSH_CELL_T = 14 * D.BEAD                           # 11.2: the grown cavity plus three beads
                                                    # behind it, where its (deepened) number is cut

TEE = [(0.20, 0.30), (0.25, 0.30), (0.30, 0.30), (0.35, 0.30), (0.40, 0.30)]
ROUND = [0.20, 0.25, 0.30, 0.35, 0.40]
MUSHROOM = [(0.15, 0.50), (0.20, 0.50), (0.25, 0.50), (0.30, 0.50), (0.20, 0.70)]
OCTAGON = [(0.15, 0.60, 0.0), (0.20, 0.60, 0.0), (0.25, 0.60, 0.0), (0.30, 0.60, 0.0)]
TAG = "fit3"


def _round_u0(c):
    """Where the round head's centre stands: its socket lip, mouth to where the slot
    meets the circle, is LIP_T long."""
    return LIP_T + math.sqrt((BULB_R + c) ** 2 - (NECK_W / 2.0 + c) ** 2)


# EVERY CELL OF A STRIP IS AS DEEP AS ITS LOOSEST: the number is cut in the back face, one
# plane for the whole strip, so that face must not move with the step
D_TEE = LIP_T + max(c for c, _b in TEE) + HEAD_D + max(b for _c, b in TEE) + BACK
D_ROUND = max(_round_u0(c) + BULB_R + c for c in ROUND) + BACK
LOG = {}                     # finder name -> [each step's corner log], for the table


def _poly(pts, z0, z1):
    return cq.Workplane("XY").polyline(pts).close().extrude(z1 - z0).translate((0, 0, z0))


def _drop_pair(tenon_pts, cavity, host_w, host_d, name):
    """A drop-in pair in fit_finder's _drop frame (X depth past the seam, Y width, Z the
    drop; both halves print +Z): `tenon_pts` the tenon's plan (from x = -1, inside its
    host), `cavity` the socket cutter; both halves rounded to the rule."""
    hw = host_w / 2.0
    token = F._box(-host_d, 0, -hw, hw, 0, F.L).union(_poly(tenon_pts, 0, F.L))
    cell = F._box(0, host_d, -hw, hw, 0, F.L).cut(cavity)
    F.ROUND_LOG.clear()
    token, cell = F._round_pair(token, cell, "z", {"tenon": NOZZLE_HALF, "socket": NOZZLE_HALF,
                                                    "hosts": False})
    LOG.setdefault(name, []).append(F.ROUND_LOG[0])
    return token, cell


def tee(c, bc):
    """The smallest rule-fitting T: neck NECK_W through a LIP_T lip into a HEAD_W x HEAD_D
    head. `c` round the sides and under the head, `bc` past its tip."""
    n2, h2, lip = NECK_W / 2.0, HEAD_W / 2.0, LIP_T + c
    pts = [(-1.0, -n2), (lip, -n2), (lip, -h2), (lip + HEAD_D, -h2),
           (lip + HEAD_D, h2), (lip, h2), (lip, n2), (-1.0, n2)]
    cav = (_poly([(-1.0, -n2 - c), (lip - c + 0.01, -n2 - c), (lip - c + 0.01, n2 + c),
                  (-1.0, n2 + c)], -1.0, F.L + 1.0)
           .union(_poly([(lip - c, -h2 - c), (lip + HEAD_D + bc, -h2 - c),
                         (lip + HEAD_D + bc, h2 + c), (lip - c, h2 + c)], -1.0, F.L + 1.0)))
    host_w = HEAD_W + 2 * c + 2 * WALL
    return _drop_pair(pts, cav, host_w, D_TEE, "tee")


def round_head(c):
    """The same neck into a circle of BULB_R, whose centre stands far enough out that
    the socket's lip (mouth to where the slot meets the circle) is LIP_T long."""
    n2 = NECK_W / 2.0
    u0 = _round_u0(c)
    neck = _poly([(-1.0, -n2), (u0, -n2), (u0, n2), (-1.0, n2)], 0, F.L)
    bulb = cq.Workplane("XY").circle(BULB_R).extrude(F.L).translate((u0, 0, 0))
    hole = (_poly([(-1.0, -n2 - c), (u0, -n2 - c), (u0, n2 + c), (-1.0, n2 + c)], -1.0, F.L + 1.0)
            .union(cq.Workplane("XY").circle(BULB_R + c).extrude(F.L + 2.0)
                   .translate((u0, 0, -1.0))))
    hw = BULB_R + c + WALL
    host_d = D_ROUND
    token = F._box(-host_d, 0, -hw, hw, 0, F.L).union(neck).union(bulb)
    cell = F._box(0, host_d, -hw, hw, 0, F.L).cut(hole)
    F.ROUND_LOG.clear()
    token, cell = F._round_pair(token, cell, "z", {"tenon": NOZZLE_HALF, "socket": NOZZLE_HALF,
                                                    "hosts": False})
    LOG.setdefault("round", []).append(F.ROUND_LOG[0])
    return token, cell


def _drop_finder(name, what, make, steps, host_w, host_d):
    f = F.Finder(name, what, make, (steps[0], steps[0]), host_w + F.GAP, F.UP_Z, F.UP_Z,
                 "chassis_0", "chassis_0",
                 cell_mark=((host_d, 0.0, F.L / 2.0), (1, 0, 0), (0, 1, 0)),
                 token_mark=((-host_d / 2.0, 0.0, F.L), (0, 0, 1), (0, 1, 0)))
    f.deltas = tuple(steps)
    return f


def finders():
    """The four round-3 finders, each re-stepped."""
    out = []
    w_tee = HEAD_W + 2 * max(c for c, _b in TEE) + 2 * WALL
    out.append(_drop_finder("tee", "nozzle/nozzle drop-in T, corners to the rule",
                            lambda k, d: tee(*d), TEE, w_tee, D_TEE))
    w_rd = 2 * (BULB_R + max(ROUND) + WALL)
    out.append(_drop_finder("round", "nozzle/nozzle drop-in round head",
                            lambda k, d: round_head(d), ROUND, w_rd, D_ROUND))
    base = {f.name: f for f in F.finders()}
    ep, octa = base["endplate"], base["octagon"]
    ep.deltas = tuple(MUSHROOM)
    ep.name = "mushroom"
    ep.make = _mushroom_make(ep.make)
    at, n, xd, kw = ep.cell_mark[0]
    ep.cell_mark = [((at[0], at[1], MUSH_CELL_T), n, xd, kw)]      # its bed face moved out
    octa.deltas = tuple(OCTAGON)
    # the octagon cell's number sits on its 1.6 roof, which has no bead to spare: it keeps
    # the plain V (0.6 deep) and leaves a bead over the mortise
    at, n, xd, kw = octa.cell_mark[0]
    octa.cell_mark = [(at, n, xd, dict(kw, shaft=0.0))]
    return out + [ep, octa]


def _mushroom_make(base_make):
    """The endplate finder's maker with the waist grown to WAIST, the TENON (the
    nozzle-made half) rounded to the rule and the layer-made socket rounded to match it
    (layer-made corners print as drawn, so the socket is drawn as the tenon prints)."""
    from src import chassis as CH
    from cadkit.joinery import joint

    def make(k, d):
        c, bc = d
        site = dict(width=CH.EP_J_W, tenon=CH._EP_AX, mortise=CH._EP_DN, install="+x",
                    standoff=CH.EP_TOP_CLR)
        h0 = joint(length=F.L, clearance=c, back_clearance=bc, **site).height
        J = joint(length=F.L, clearance=c, back_clearance=bc,
                  depth=h0 - 2 * D.BEAD + WAIST, **site)
        hw = CH.T / 2.0
        root = CH.EP_J_ROOT
        token = F._box(0, F.L, -hw, hw, -10 * D.BEAD, 0).union(J.tenon(root=root, length=F.L))
        so = getattr(J, "standoff", 0.0)
        assert J.height + bc + 3 * D.BEAD <= MUSH_CELL_T + 1e-9, "no room behind the cavity for its number"
        cell = (F._box(0, F.L, -hw, hw, so, MUSH_CELL_T)
                .cut(J.mortise(drop=root + 1.0, length=F.L + 2.0).translate((-1.0, 0, 0))))
        F.ROUND_LOG.clear()
        # the socket drawn to MATCH the tenon: each concave corner the tenon's printed
        # convex one grown by the clearance (parallel faces, not a sharp pocket round a
        # round head), each convex one the tenon's concave radius
        token, cell = F._round_pair(token, cell, "x", {"tenon": NOZZLE_HALF,
                                                        "socket": (CONCAVE_R, CONVEX_R + c),
                                                        "hosts": False})
        LOG.setdefault("mushroom", []).append(F.ROUND_LOG[0])
        return token, cell
    return make


def plate():
    """[(name, solid)], bed at z = 0: every finder's strip with its tokens beside it."""
    out, x = [], 0.0
    for f in finders():
        grp, w = R2._group(f, "both", TAG)
        y0 = min(sh.BoundingBox().ymin for _n, sh in grp)
        out += [(n, sh.moved(cq.Location(cq.Vector(x, -y0, 0.0)))) for n, sh in grp]
        x += w + R2.BETWEEN
    return [(n, sh if sh.isValid() else sh.fix()) for n, sh in out]


def assembly(origin=(-560.0, 330.0, 160.0)):
    """[(name, Workplane)] for the scratch view: the plate as it prints."""
    return [("test_" + n, cq.Workplane("XY").newObject([s]).translate(origin)) for n, s in plate()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", action="store_true", help="write src/test/test_fit3_plate_petg_gf.step")
    a = ap.parse_args(argv)
    LOG.clear()
    pl = plate()
    print("TEE neck %.1f, head %.1f x %.1f, lip %.1f | ROUND head r %.1f | MUSHROOM waist %.1f"
          % (NECK_W, HEAD_W, HEAD_D, LIP_T, BULB_R, WAIST))
    for name, steps in (("tee", TEE), ("round", ROUND), ("mushroom", MUSHROOM), ("octagon", OCTAGON)):
        print(name)
        for k, d in enumerate(steps):
            dd = d if isinstance(d, tuple) else (d,)
            print("   %d    %s" % (k + 1, " / ".join("%.2f" % v for v in dd[:2])))
    for name, logs in LOG.items():
        short = [(half, kind, used, want) for half in ("tenon", "socket") for u, v, kind, used in logs[0][half]
                 for want in [NOZZLE_HALF[0] if kind == "convex" else NOZZLE_HALF[1]]
                 if used is None or (name != "mushroom" or half == "tenon") and used < want - 1e-9]
        print("%s corners not at the rule (step 1): %s" % (name, short if short else "none"))
    lo = [min(getattr(s.BoundingBox(), a_) for _n, s in pl) for a_ in ("xmin", "ymin", "zmin")]
    hi = [max(getattr(s.BoundingBox(), a_) for _n, s in pl) for a_ in ("xmax", "ymax", "zmax")]
    print("plate: %d pieces, %.1f cm3, %.1f x %.1f, %.1f tall" % (
        len(pl), sum(s.Volume() for _n, s in pl) / 1000.0, hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))
    bad = [n for n, s in pl if not s.isValid() or len(s.Solids()) != 1]
    print("every piece one valid solid" if not bad else "NOT ONE VALID SOLID: %s" % ", ".join(bad))
    if a.export:
        from cadkit.step_export import export_step
        path = HERE / "test_fit3_plate_petg_gf.step"
        export_step(cq.Workplane("XY").newObject(
            [cq.Compound.makeCompound([s for _n, s in pl])]), str(path))
        print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
