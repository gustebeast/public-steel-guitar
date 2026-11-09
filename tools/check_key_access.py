"""Can the instrument's ONE 2.5 mm key turn every screw? (user, 2026-10-22)

The key is a Bondhus 10954 (BOM, Tools): an L, ball end on the LONG arm, plain hex on the
short one. For every screw in the last scratch build this asks, from the screw's socket out:

  LONG    the long arm straight down the screw's axis: a clear column ARM_L long, and the
          short arm, the handle at its far end, able to swing SWING_MIN of a turn there
  SHORT   the short arm in the socket: a clear column SHORT_L long, and the long arm able to
          swing SWING_MIN of a turn in the plane at its end
  BALL    the long arm's ball end, tilted up to BALL_DEG off the axis (BALL_AZ directions
          around it): a clear column ARM_L long, and the handle's swing at its end

BALL is reported as a WARNING: the ball end turns a screw but should not be what TIGHTENS one
(user, 2026-10-22: "ideally we won't need to use the ball end for anything requiring torque").

It prints, per screw, the first way that works -- or, when none does, what each way meets
first and how far out. SWING_MIN is 60 deg: the hex re-seats every 60, so a key that swings
that far can be flipped over and walked round.

It reads the parts as they were BUILT (the scratch cache: your own, else the lead's), in the
pose the assembly draws them. A screw that is only turned with a part slid out (a leg in its
service position, a nut lowered) shows as blocked here; read the obstacle and decide.

    py -3.12 tools/check_key_access.py [--only SUBSTR[,SUBSTR]] [--verbose]
"""

from __future__ import annotations

import argparse
import math
import pathlib
import re
import sys
import time

import cadquery as cq
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

KEY_AC    = 2.9          # the 2.5 hex over its corners
KEY_D     = KEY_AC + 0.2 # the column it needs, with a hand's wobble
ARM_L     = 88.0         # Bondhus 10954's long arm
SHORT_L   = 20.0         # its short arm (⚠ not on the listings found: measure one)
BALL_DEG  = 25.0         # Bondhus's working angle for the ball end
BALL_TRY  = (10.0, 15.0, 20.0, BALL_DEG)   # tilts tried, up to it
BALL_AZ   = 24           # directions tried around the axis at each tilt
SWING_MIN = 60.0         # of a turn, for the handle
SECTOR    = 15.0         # the swing is looked at in sectors this wide
SOCKET_IN = 1.5          # the ball's centre below the head's top

SCREW = re.compile(r"(screws?)(_\d+)?$|_screw_")
NOT_KEY = re.compile(r"leadscrew|screw_bearing|screw_pulley|motor_term_screws")  # not ours / not hex


def _load(path):
    s = TopoDS_Shape()
    BRepTools.Read_s(s, str(path), BRep_Builder())
    return cq.Shape.cast(s)


def _caches():
    own = ROOT / ".scratch_cache"
    out = [own]
    try:
        from cadkit.scratch import shared_cache
        out.append(shared_cache(ROOT))
    except Exception:
        pass
    return [c for c in out if c.exists()]


def load_parts():
    parts = {}
    for c in _caches():
        for p in c.glob("*.brep"):
            if p.stem not in parts:
                parts[p.stem] = p
    shapes = {}
    for n, p in parts.items():
        s = _load(p)
        if s.Solids():
            shapes[n] = s
    return shapes


def sockets(name, shape):
    """[(top, out)] for each screw in a part: the head's top centre and the way out of the
    socket. The head is the solid's widest cylinder; out is along its axis, away from the
    shank. A head-only stand-in (one radius) gives both ends; the caller keeps the better."""
    found = []
    for sol in shape.Solids():
        cyl = [f for f in sol.Faces() if f.geomType() == "CYLINDER"]
        if not cyl:
            continue
        head = max(cyl, key=lambda f: f._geomAdaptor().Cylinder().Radius())
        ax = head._geomAdaptor().Cylinder().Axis()
        o = cq.Vector(ax.Location().X(), ax.Location().Y(), ax.Location().Z())
        d = cq.Vector(ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()).normalized()
        ts = [(cq.Vector(*v.toTuple()) - o).dot(d) for v in head.Vertices()]
        lo, hi = min(ts), max(ts)
        c = sol.Center()
        shank = (c - o).dot(d)
        mid = (lo + hi) / 2
        if len({round(f._geomAdaptor().Cylinder().Radius(), 2) for f in cyl}) == 1:
            found.append([(o + d * hi, d), (o + d * lo, -d)])     # either end
        elif shank < mid:
            found.append([(o + d * hi, d)])
        else:
            found.append([(o + d * lo, -d)])
    return found


class Scene:
    def __init__(self, shapes):
        self.shapes = shapes
        self.boxes = {n: s.BoundingBox() for n, s in shapes.items()}

    def hits(self, probe, skip):
        """[(name, solid)] of parts the probe meets (by volume)."""
        pb = probe.BoundingBox()
        out = []
        for n, bb in self.boxes.items():
            if n in skip:
                continue
            if (bb.xmax < pb.xmin or bb.xmin > pb.xmax or bb.ymax < pb.ymin or bb.ymin > pb.ymax
                    or bb.zmax < pb.zmin or bb.zmin > pb.zmax):
                continue
            com = probe.intersect(self.shapes[n])
            if com.Solids() and com.Volume() > 1e-3:
                out.append((n, com))
        return out

    def column(self, start, d, L, skip):
        """(clear length, first part met) along a key column of KEY_D from start."""
        cylr = cq.Solid.makeCylinder(KEY_D / 2, L, start, d)
        best, who = L, None
        for n, com in self.hits(cylr, skip):
            t = min((cq.Vector(*v.toTuple()) - start).dot(d) for v in com.Vertices())
            if t < best:
                best, who = max(t, 0.0), n
        return best, who

    def swing(self, centre, d, r_out, skip):
        """The longest free arc (deg) for an arm of r_out turning about d at centre."""
        free = []
        for k in range(int(360 / SECTOR)):
            w = cq.Solid.makeCylinder(r_out, KEY_D, centre - d * (KEY_D / 2), d, SECTOR)
            w = w.rotate(centre, centre + d, k * SECTOR)
            free.append(not self.hits(w, skip))
        if all(free):
            return 360.0
        run, best = 0, 0
        for f in free + free:
            run = run + 1 if f else 0
            best = max(best, run)
        return min(best, len(free)) * SECTOR


def _tilts(d):
    """BALL_AZ directions around d at each tilt in BALL_TRY."""
    a = cq.Vector(1, 0, 0) if abs(d.x) < 0.9 else cq.Vector(0, 1, 0)
    u = d.cross(a).normalized()
    v = d.cross(u).normalized()
    for deg in BALL_TRY:
        t = math.radians(deg)
        for k in range(BALL_AZ):
            p = 2 * math.pi * k / BALL_AZ
            yield (d * math.cos(t) + (u * math.cos(p) + v * math.sin(p)) * math.sin(t)).normalized()


def judge(scene, name, top, d):
    skip = {name}
    out = {}
    L, who = scene.column(top, d, ARM_L, skip)
    out["long"] = (L, who)
    if L >= ARM_L - 1e-6:
        sw = scene.swing(top + d * ARM_L, d, SHORT_L, skip)
        if sw >= SWING_MIN:
            return "LONG", out
        out["long_swing"] = sw
    if L >= SHORT_L:
        sw = scene.swing(top + d * SHORT_L, d, ARM_L, skip)
        if sw >= SWING_MIN:
            return "SHORT", out
        out["short_swing"] = sw
    ball = top - d * SOCKET_IN
    best = None
    for t in _tilts(d):
        Lb, wb = scene.column(ball + t * SOCKET_IN, t, ARM_L, skip)
        if Lb >= ARM_L - 1e-6:
            sw = scene.swing(ball + t * ARM_L, t, SHORT_L, skip)
            if sw >= SWING_MIN:
                return "BALL", out
        if best is None or Lb > best[0]:
            best = (Lb, wb)
    out["ball"] = best
    return "BLOCKED", out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", help="comma-separated substrings of part names")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    shapes = load_parts()
    scene = Scene(shapes)
    names = sorted(n for n in shapes if SCREW.search(n) and not NOT_KEY.search(n))
    if a.only:
        keys = a.only.split(",")
        names = [n for n in names if any(k in n for k in keys)]
    print("%d parts loaded, %d screw parts (%.0f s)" % (len(shapes), len(names), time.time() - t0))
    tally = {}
    for n in names:
        found = sockets(n, shapes[n])
        for i, ends in enumerate(found):
            label = n + ("[%d]" % i if len(found) > 1 else "")
            res = [judge(scene, n, top, d) + (top,) for top, d in ends]
            order = ["LONG", "SHORT", "BALL", "BLOCKED"]
            verdict, info, top = min(res, key=lambda r: order.index(r[0]))
            tally[verdict] = tally.get(verdict, 0) + 1
            if verdict in ("BLOCKED", "BALL") or a.verbose:
                lg = info.get("long")
                bl = info.get("ball")
                msg = "long arm meets %s at %.1f" % (lg[1], lg[0]) if lg and lg[1] else "long arm clear"
                if "long_swing" in info:
                    msg += ", handle swings %.0f" % info["long_swing"]
                if "short_swing" in info:
                    msg += ", short-arm swing %.0f" % info["short_swing"]
                if bl:
                    msg += "; best ball end meets %s at %.1f" % (bl[1], bl[0])
                print("  %-8s %-44s at (%.1f, %.1f, %.1f)  %s"
                      % (verdict, label, top.x, top.y, top.z, msg))
    print("\n" + ", ".join("%s %d" % (k, v) for k, v in sorted(tally.items()))
          + "  (%.0f s)" % (time.time() - t0))


if __name__ == "__main__":
    main()
