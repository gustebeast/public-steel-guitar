"""Two neighbouring belt clamps against EACH OTHER, both moving.

    py -3.12 -m tools.clamp_pair 8 A 9 B        # string 9 on run A vs string 10 on run B

tools.clamp_study tests a clamp against the other strings' STATIC parts. Two clamps are both
moving, each through its own travel and independently (the strings are tuned separately),
so every position of one has to be tried against every position of the other."""
import math
import sys

import cadquery as cq

from src import build as B, dimensions as D, belt_tensioner as BTn

V = cq.Vector
_R = D.PULLEY_OD / 2 + D.BELT_T / 2
LO, HI = min(B._CLAMP_XS), max(B._CLAMP_XS)
CLAMP = cq.Compound.makeCompound([s.val() for _n, s in BTn.clamp_components(with_lifters=True)])


def geom(i, run):
    M = V(*D.motor_pos(i))
    S = V(D.screw_x(i), D.string_y(i), D.screw_pulley_z(i))
    if run == "A":
        mb, sm = V(M.x, M.y, M.z + _R), V(S.x, S.y + _R, S.z)
    else:
        mb, sm = V(M.x, M.y, M.z - _R), V(S.x, S.y - _R, S.z)
    return sm, mb.sub(sm).normalized(), mb.sub(sm).Length


def posed(i, run, p):
    sm, tan, L = geom(i, run)
    ls, lm = p + LO, L - (p + HI)
    a = (math.pi / 2) * ls / (ls + lm)
    n = V(0, math.cos(a), math.sin(a)).multiply(-1.0 if run == "A" else 1.0)
    n = n.sub(tan.multiply(n.dot(tan))).normalized()
    o = sm.add(tan.multiply(p))
    return CLAMP.moved(cq.Location(cq.Plane(origin=(o.x, o.y, o.z), xDir=(tan.x, tan.y, tan.z),
                                            normal=(n.x, n.y, n.z))))


def span(i, run, step):
    _sm, _t, L = geom(i, run)
    p0 = D.PULLEY_FLANGE_OD / 2 + D.CLAMP_END_CLR - LO
    p1 = L - D.PULLEY_FLANGE_OD / 2 - D.CLAMP_END_CLR - HI
    n = max(1, int(math.ceil((p1 - p0) / step)))
    return [p0 + (p1 - p0) * k / n for k in range(n + 1)]


def main():
    step = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0
    ra, ia, rb, ib = sys.argv[2], int(sys.argv[3]) - 1, sys.argv[4], int(sys.argv[5]) - 1
    pa, pb = span(ia, ra, step), span(ib, rb, step)
    ca = [(p, posed(ia, ra, p)) for p in pa]
    cb = [(p, posed(ib, rb, p)) for p in pb]
    print("string %d run %s (down)  x  string %d run %s (across), mm3; . = clear" % (ia + 1, ra, ib + 1, rb))
    print("        " + " ".join("%5.0f" % p for p, _ in cb))
    worst = 0.0
    for p, a in ca:
        row = []
        for _q, b in cb:
            ab, bb = a.BoundingBox(), b.BoundingBox()
            if (ab.xmax < bb.xmin or bb.xmax < ab.xmin or ab.ymax < bb.ymin or bb.ymax < ab.ymin
                    or ab.zmax < bb.zmin or bb.zmax < ab.zmin):
                v = 0.0
            else:
                try:
                    v = a.intersect(b).Volume()
                except Exception:
                    v = 0.0
            worst = max(worst, v)
            row.append("    ." if v < 1e-3 else "%5.1f" % v)
        print("%6.0f  " % p + " ".join(row))
    print("worst %.2f mm3" % worst)


if __name__ == "__main__":
    main()
