"""Can every belt clamp run its whole belt, whatever its neighbours are doing?

    py -3.12 -m tools.clamp_range [step_mm] [twist_err_deg] [out.json]

Run it with -m from the repo root (it imports src). Exits 1 when it prints NOT CLEAR.

Belts, pulleys and clamps ONLY (user, 2026-10-05); the chassis, endplates, boards and
wiring are tools.clamp_study's and the overlap gate's business.

Each clamp is taken as its BOUNDING BOX in its own frame, which is what makes this cheap
enough to do exhaustively and errs on the safe side. Every question is then settled on
the REAL solids wherever a box meets something, so a chamfer or a relief counts (until
2026-10-22 only clamp against clamp was; own belt and static went on the box). Steps are
tried COARSE first, CLAMP_COARSE (default 4) to a box stretched and widened to hold all of
them; only a chunk whose box meets something is tried step by step. CLAMP_COARSE=1 tries
every step alone: same verdicts, checked identical, ~2.6x the time. It is stepped from one end of its
run to the other -- CLAMP_END_CLR off each pulley flange, further than the nut's travel
ever carries it -- on the run it is installed on, turned with the belt, and at every step
it is tried at the nominal twist and twist_err either side. Three questions per step:

  own     the OTHER run of its own belt (the clamp stands into its own loop)
  static  every other string's belt, and every pulley
  clamps  every other string's clamp, at EVERY one of that clamp's own steps and twists

THE VERDICT IS ON WHAT A CLAMP CAN REACH, not on the whole run. A clamp is spliced with
the nut on the ceiling (src.components.clamp_p) and the nut's travel carries it
CARRIAGE_TRAVEL * BELT_PER_MM from there; REACHABLE is that stretch plus REACH_MARGIN at
its far end. A string passes when nothing blocks it inside its reach, counting another
clamp only where THAT clamp is inside its own reach. Steps blocked outside the reach are
counted and reported, not failed: on most strings they are a neighbour's pulley near the
end of the run the clamp never visits. CLAMP_RANGE_ALL=1 lists them."""
import json
import math
import os
import sys
import time

import cadquery as cq

from src import build as B, components as C, dimensions as D, belt_tensioner as BTn

V = cq.Vector
KIN = C                 # main() has a local C (the posed boxes)
N = D.N_STRINGS
R = C.BELT_R
REACH_MARGIN = D.CLAMP_END_CLR   # mm of belt past the far end of the travel: a clamp spliced
                                 # off its mark by as much as its whole end clearance
STEP = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
ERR = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
OUT = sys.argv[3] if len(sys.argv) > 3 else None
COARSE = int(os.environ.get("CLAMP_COARSE", "4"))   # steps per coarse chunk; 1 = every step alone

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
    return (RUNS[i] == "U") if RUNS else B.clamp_upper(i)


def _ends(i):
    return D.motor_pos(i), (D.screw_x(i), D.string_y(i), D.screw_pulley_z(i))


def geom(i):
    """(sign, motor centre, screw-pulley centre) for string i's clamp run."""
    m, s = _ends(i)
    return (1.0 if upper(i) else -1.0), V(*m), V(*s)


def posed(i, p, da):
    """The clamp's placement: src.components.clamp_frame, the model the build draws with."""
    m, s = _ends(i)
    o, xd, n = C.clamp_frame(m, s, upper(i), p, X0, X1, da)
    return cq.Location(cq.Plane(origin=o, xDir=xd, normal=n))


def C_frame(i, p, da):
    m, s = _ends(i)
    return C.clamp_frame(m, s, upper(i), p, X0, X1, da)


def steps(i):
    m, s = _ends(i)
    p0, p1 = C.clamp_span(m, s, upper(i), X0, X1)
    n = max(1, int(math.ceil((p1 - p0) / STEP)))
    return [p0 + (p1 - p0) * k / n for k in range(n + 1)]


def other_run(i, belt):
    """The half of string i's belt that its clamp is NOT on: the loop split by the plane
    through the motor and screw axes' centres that separates the two runs."""
    sg, M, S = geom(i)
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
    # COARSE, THEN FINE. COARSE consecutive steps are one CHUNK, tried first as one box that
    # holds every one of them: the clamp box stretched along the belt by half the chunk's
    # length each way, and widened across it by what the belt's turn over the chunk can
    # swing a corner (R * half the turn, the clamp turning about the belt's own line). Where
    # a chunk's box meets nothing, none of its steps can; only where it does are the steps
    # tried one by one -- box first, then the REAL clamp wherever a box meets something, so a
    # chamfer or a relief counts here as it does clamp against clamp.
    R = math.hypot(max(abs(Y0), abs(Y1)), max(abs(Z0), abs(Z1)))
    CH = {i: [list(range(k, min(k + COARSE, len(P[i])))) for k in range(0, len(P[i]), COARSE)]
          for i in range(N)}

    def chunk_box(i, ks, t):
        m, sc = _ends(i)
        p0, p1 = P[i][ks[0]], P[i][ks[-1]]
        nm = C_frame(i, (p0 + p1) / 2.0, DAS[t])[2]

        def ang(p):
            n = C_frame(i, p, DAS[t])[2]
            return math.acos(max(-1.0, min(1.0, sum(a * b for a, b in zip(n, nm)))))
        turn = max(ang(P[i][k]) for k in ks)          # the furthest any step turns off the middle
        h, e = (p1 - p0) / 2.0, 2.0 * R * math.sin(turn / 2.0) + 1e-3   # a corner's chord
        box = (cq.Workplane("XY").box(X1 - X0 + 2 * h, Y1 - Y0 + 2 * e, Z1 - Z0 + 2 * e,
                                      centered=False)
               .translate((X0 - h, Y0 - e, Z0 - e)).val())
        return box.moved(posed(i, (p0 + p1) / 2.0, DAS[t]))
    CHB = {i: [[chunk_box(i, ks, t) for t in range(len(DAS))] for ks in CH[i]] for i in range(N)}
    CHBB = {i: [[b.BoundingBox() for b in row] for row in CHB[i]] for i in range(N)}

    def meets(c, cb, s, sb):
        return not far(cb, sb) and vol(c, s) > 1e-3

    res = {i: [dict(p=round(p, 1), own=0.0, static={}, clamps={}) for p in P[i]] for i in range(N)}
    fine = 0
    for i in range(N):
        ob, obb = own[i]
        others = [(nm, s, sb) for nm, (j, s, sb) in static.items() if j != i]
        for q, ks in enumerate(CH[i]):
            for t in range(len(DAS)):
                hb, hbb = CHB[i][q][t], CHBB[i][q][t]
                own_hit = meets(hb, hbb, ob, obb)
                near = [(nm, s, sb) for nm, s, sb in others if meets(hb, hbb, s, sb)]
                if not own_hit and not near:
                    continue
                for k in ks:
                    c, cb = C[i][k][t], CB[i][k][t]
                    fine += 1
                    if own_hit and meets(c, cb, ob, obb):
                        res[i][k]["own"] = max(res[i][k]["own"], round(vol(real(i, k, t), ob), 3))
                    for nm, s, sb in near:
                        if meets(c, cb, s, sb):
                            v = vol(real(i, k, t), s)
                            if v > 1e-3:
                                res[i][k]["static"][nm] = max(res[i][k]["static"].get(nm, 0.0),
                                                              round(v, 3))
        print("string %2d own/static done (%d steps, %.0fs)" % (i + 1, len(P[i]), time.time() - t0),
              flush=True)
    for i in range(N):
        for j in range(i + 1, N):
            worst = 0.0
            for q, ks in enumerate(CH[i]):
                for r, ms in enumerate(CH[j]):
                    if not any(meets(CHB[i][q][t], CHBB[i][q][t], CHB[j][r][u], CHBB[j][r][u])
                               for t in range(len(DAS)) for u in range(len(DAS))):
                        continue
                    for k in ks:
                        for m in ms:
                            v = 0.0
                            for t, (c, cb) in enumerate(zip(C[i][k], CB[i][k])):
                                for u, (e, eb) in enumerate(zip(C[j][m], CB[j][m])):
                                    if meets(c, cb, e, eb):
                                        v = max(v, vol(real(i, k, t), real(j, m, u)))
                            if v > 1e-3:
                                res[i][k]["clamps"].setdefault(str(j + 1), []).append(round(P[j][m], 1))
                                res[j][m]["clamps"].setdefault(str(i + 1), []).append(round(P[i][k], 1))
                                worst = max(worst, v)
            if worst > 0:
                print("clamp %d x clamp %d: worst %.2f mm3" % (i + 1, j + 1, worst), flush=True)
    print("fine steps tried: %d of %d" % (fine, sum(len(P[i]) for i in range(N)) * len(DAS)))
    print("pairs done %.0fs" % (time.time() - t0), flush=True)
    need = D.CARRIAGE_TRAVEL * D.BELT_PER_MM
    win = {}
    for i in range(N):
        m, sc = _ends(i)
        a = KIN.clamp_p(m, sc, upper(i), X0, X1, 0.0)
        b = KIN.clamp_p(m, sc, upper(i), X0, X1, D.CARRIAGE_TRAVEL)
        b += REACH_MARGIN if b > a else -REACH_MARGIN
        win[i] = (min(a, b), max(a, b))

    def inside(i, p):
        return win[i][0] - 1e-6 <= p <= win[i][1] + 1e-6

    ok_all = True
    for i in range(N):
        run = P[i][-1] - P[i][0]
        hit, out = [], []
        for r in res[i]:
            what = []
            if r["own"] > 1e-3:
                what.append("own belt %.2f" % r["own"])
            what += ["%s %.2f" % kv for kv in sorted(r["static"].items())]
            reach = bool(what) and inside(i, r["p"])
            for j, q in sorted(r["clamps"].items()):
                qin = [x for x in q if inside(int(j) - 1, x)]
                what.append("clamp %s at %.0f..%.0f" % (j, min(q), max(q)))
                reach = reach or (inside(i, r["p"]) and bool(qin))
            if what:
                (hit if reach else out).append("      p %6.1f  %s" % (r["p"], "; ".join(what)))
        short = run < need - 1e-6 or win[i][0] < P[i][0] - 1e-6 or win[i][1] > P[i][-1] + 1e-6
        verdict = ("CLEAR" if not hit and not short else
                   "BLOCKED IN REACH (%d step(s))" % len(hit) if hit else "RUN TOO SHORT")
        print("string %2d  %s run %.1f..%.1f  REACHABLE %.1f..%.1f  spare %.1f  %s"
              % (i + 1, "upper" if upper(i) else "lower", P[i][0], P[i][-1], win[i][0], win[i][1],
                 run - need, verdict))
        for line in hit:
            print(line + "   <-- IN REACH")
        if out:
            print("      outside reach, never visited: %d step(s), p %s .. %s"
                  % (len(out), out[0].split()[1], out[-1].split()[1]))
            if os.environ.get("CLAMP_RANGE_ALL"):
                for line in out:
                    print(line)
        if hit or short:
            ok_all = False
    tight = min(range(N), key=lambda i: P[i][-1] - P[i][0])
    print("%s (%s screw). Tightest: string %d, %.1f mm of belt to spare beyond its travel."
          % ("ALL CLEAR: every clamp is clear over everything it can reach, wherever the "
             "other clamps are in THEIR reach" if ok_all else "NOT CLEAR", D.SCREW_HAND,
             tight + 1, P[tight][-1] - P[tight][0] - need))
    if OUT:
        json.dump({str(i + 1): res[i] for i in range(N)}, open(OUT, "w"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
