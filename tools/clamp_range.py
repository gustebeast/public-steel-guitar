"""Can every belt clamp run its whole belt, whatever its neighbours are doing?

    py -3.12 -m tools.clamp_range [step_mm] [twist_err_deg] [out.json]

Belts, pulleys and clamps ONLY (user, 2026-10-05); the chassis, endplates, boards and
wiring are tools.clamp_study's and the overlap gate's business.

Each clamp is taken as its BOUNDING BOX in its own frame, which is what makes this cheap
enough to do exhaustively and errs on the safe side. Clamp against clamp is then settled
on the REAL solids wherever two boxes meet, so a chamfer or a relief counts. It is stepped from one end of its
run to the other -- CLAMP_END_CLR off each pulley flange, further than the nut's travel
ever carries it -- on the run it is installed on, turned with the belt, and at every step
it is tried at the nominal twist and twist_err either side. Three questions per step:

  own     the OTHER run of its own belt (the clamp stands into its own loop)
  static  every other string's belt, and every pulley
  clamps  every other string's clamp, at EVERY one of that clamp's own steps and twists

A string passes when all three are clear at every step."""
import json
import math
import os
import sys
import time

import cadquery as cq

from src import build as B, dimensions as D, belt_tensioner as BTn

V = cq.Vector
N = D.N_STRINGS
R = D.PULLEY_OD / 2 + D.BELT_T / 2
STEP = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
ERR = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
OUT = sys.argv[3] if len(sys.argv) > 3 else None

_bbs = [s.val().BoundingBox() for _n, s in BTn.clamp_components()]
X0, X1 = min(b.xmin for b in _bbs), max(b.xmax for b in _bbs)
Y0, Y1 = min(b.ymin for b in _bbs), max(b.ymax for b in _bbs)
Z0, Z1 = min(b.zmin for b in _bbs), max(b.zmax for b in _bbs)
BOX = (cq.Workplane("XY").box(X1 - X0, Y1 - Y0, Z1 - Z0, centered=False)
       .translate((X0, Y0, Z0)).val())
REAL = cq.Compound.makeCompound([s.val() for _n, s in BTn.clamp_components()])


RUNS = os.environ.get("CLAMP_RUNS", "")     # e.g. UUUUUUUUUU: which run each string's clamp is on;
                                            # default is the install rule (near row upper, far row lower)


def upper(i):
    return (RUNS[i] == "U") if RUNS else (not D.screw_far(i))


def geom(i):
    M = V(*D.motor_pos(i))
    S = V(D.screw_x(i), D.string_y(i), D.screw_pulley_z(i))
    sg = 1.0 if upper(i) else -1.0
    mb, sm = V(M.x, M.y, M.z + sg * R), V(S.x, S.y + sg * R, S.z)
    return sm, mb.sub(sm).normalized(), mb.sub(sm).Length, sg, M, S


def posed(i, p, da):
    sm, tan, L, sg, _M, _S = geom(i)
    ls, lm = p + X0, L - (p + X1)
    a = (math.pi / 2) * ls / (ls + lm) + math.radians(da)
    n = V(0, math.cos(a), math.sin(a)).multiply(-sg)
    n = n.sub(tan.multiply(n.dot(tan))).normalized()
    o = sm.add(tan.multiply(p))
    return cq.Location(cq.Plane(origin=(o.x, o.y, o.z), xDir=(tan.x, tan.y, tan.z),
                                normal=(n.x, n.y, n.z)))


def steps(i):
    L = geom(i)[2]
    p0 = D.PULLEY_FLANGE_OD / 2 + D.CLAMP_END_CLR - X0
    p1 = L - D.PULLEY_FLANGE_OD / 2 - D.CLAMP_END_CLR - X1
    n = max(1, int(math.ceil((p1 - p0) / STEP)))
    return [p0 + (p1 - p0) * k / n for k in range(n + 1)]


def other_run(i, belt):
    """The half of string i's belt that its clamp is NOT on: the loop split by the plane
    through the motor and screw axes' centres that separates the two runs."""
    _sm, _t, _L, sg, M, S = geom(i)
    d = S.sub(M).normalized()
    n = V(0, 1, 1)
    n = n.sub(d.multiply(n.dot(d))).normalized().multiply(-sg)       # toward the other run
    mid = M.add(S).multiply(0.5)
    half = (cq.Workplane(cq.Plane(origin=(mid.x, mid.y, mid.z), xDir=(d.x, d.y, d.z),
                                  normal=(n.x, n.y, n.z)))
            .box(2000.0, 400.0, 200.0, centered=(True, True, False)).val())
    return belt.intersect(half)


def far(a, b):
    return (a.xmax < b.xmin or b.xmax < a.xmin or a.ymax < b.ymin or b.ymax < a.ymin
            or a.zmax < b.zmin or b.zmax < a.zmin)


def vol(a, b):
    try:
        return a.intersect(b).Volume()
    except Exception:
        return 0.0


def main():
    t0 = time.time()
    DAS = (-ERR, 0.0, ERR) if ERR else (0.0,)
    static, own = {}, {}
    for i in range(N):
        for n, s in B._string_components(i):
            if n.startswith(("belt_tensioner", "belt_clamp")):
                continue
            if n.startswith("belt_"):
                static[n] = (i, s.val(), s.val().BoundingBox())
                o = other_run(i, s.val())
                own[i] = (o, o.BoundingBox())
            elif n.startswith(("motor_pulley_", "screw_pulley_")):
                static[n] = (-1, s.val(), s.val().BoundingBox())
    print("parts built %.0fs; clamp box %.2f x %.2f x %.2f, step %.1f, twist +-%.0f"
          % (time.time() - t0, X1 - X0, Y1 - Y0, Z1 - Z0, STEP, ERR), flush=True)
    P = {i: steps(i) for i in range(N)}
    LOC = {i: [[posed(i, p, da) for da in DAS] for p in P[i]] for i in range(N)}
    C = {i: [[BOX.moved(l) for l in row] for row in LOC[i]] for i in range(N)}
    _real = {}

    def real(i, k, t):
        if (i, k, t) not in _real:
            _real[(i, k, t)] = REAL.moved(LOC[i][k][t])
        return _real[(i, k, t)]
    CB = {i: [[c.BoundingBox() for c in row] for row in C[i]] for i in range(N)}
    res = {i: [dict(p=round(p, 1), own=0.0, static={}, clamps={}) for p in P[i]] for i in range(N)}
    for i in range(N):
        ob, obb = own[i]
        for k in range(len(P[i])):
            for c, cb in zip(C[i][k], CB[i][k]):
                if not far(cb, obb):
                    res[i][k]["own"] = max(res[i][k]["own"], round(vol(c, ob), 3))
                for nm, (j, s, sb) in static.items():
                    if j == i or far(cb, sb):
                        continue
                    v = vol(c, s)
                    if v > 1e-3:
                        res[i][k]["static"][nm] = max(res[i][k]["static"].get(nm, 0.0), round(v, 3))
        print("string %2d own/static done (%d steps, %.0fs)" % (i + 1, len(P[i]), time.time() - t0),
              flush=True)
    for i in range(N):
        for j in range(i + 1, N):
            worst = 0.0
            for k in range(len(P[i])):
                for m in range(len(P[j])):
                    v = 0.0
                    for t, (c, cb) in enumerate(zip(C[i][k], CB[i][k])):
                        for u, (e, eb) in enumerate(zip(C[j][m], CB[j][m])):
                            if not far(cb, eb) and vol(c, e) > 1e-3:
                                v = max(v, vol(real(i, k, t), real(j, m, u)))
                    if v > 1e-3:
                        res[i][k]["clamps"].setdefault(str(j + 1), []).append(round(P[j][m], 1))
                        res[j][m]["clamps"].setdefault(str(i + 1), []).append(round(P[i][k], 1))
                        worst = max(worst, v)
            if worst > 0:
                print("clamp %d x clamp %d: worst %.2f mm3" % (i + 1, j + 1, worst), flush=True)
    print("pairs done %.0fs" % (time.time() - t0), flush=True)
    need = D.CARRIAGE_TRAVEL * D.BELT_PER_MM
    ok_all = True
    for i in range(N):
        bad = [r for r in res[i] if r["own"] > 1e-3 or r["static"] or r["clamps"]]
        run = P[i][-1] - P[i][0]
        print("string %2d  %s run  steps %3d  end-to-end %.1f = %.1f mm travel (need %.2f)  %s"
              % (i + 1, "upper" if upper(i) else "lower", len(P[i]), run, run / D.BELT_PER_MM,
                 D.CARRIAGE_TRAVEL, "CLEAR at every step" if not bad else "%d step(s) BLOCKED" % len(bad)))
        for r in bad:
            ok_all = False
            what = []
            if r["own"] > 1e-3:
                what.append("own belt %.2f" % r["own"])
            what += ["%s %.2f" % kv for kv in sorted(r["static"].items())]
            what += ["clamp %s at %s" % (j, ("%.0f..%.0f" % (min(q), max(q)))) for j, q in sorted(r["clamps"].items())]
            print("      p %6.1f  %s" % (r["p"], "; ".join(what)))
        if run < need - 1e-6:
            ok_all = False
    print("ALL CLEAR" if ok_all else "NOT CLEAR")
    if OUT:
        json.dump({str(i + 1): res[i] for i in range(N)}, open(OUT, "w"))


if __name__ == "__main__":
    main()
