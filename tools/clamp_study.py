"""Where on each belt may the tension clamp sit?

    py -3.12 -m tools.clamp_study [step_mm] [out.json] [A|B] [twist_err_deg] [strings, e.g. 9,10]

Steps the clamp along one run of every belt (B = the lower run, A = the upper), turned to
the belt's local twist -- 90 deg spread evenly over the FREE belt either side of the rigid
clamp -- and intersects it with every OTHER string's belt, motor and pulleys, the bridge
endplate and the chassis. The clear spans are where a clamp may live; a span / BELT_PER_MM
is the nut travel that belt can carry. The even spread is an ASSUMPTION (a real belt
twists where it is slackest and the clamp's own weight hangs it off-angle), so twist_err
also tests the clamp that many degrees either side and a position is clear only if all
three are. First run 2026-10-01: see docs/belt-clamp-travel.md."""
import math, sys, json, time, re
import cadquery as cq
from src import build as B, dimensions as D, belt_tensioner as BTn
V = cq.Vector
r = D.PULLEY_OD / 2 + D.BELT_T / 2
XS = B._CLAMP_XS; LO, HI = min(XS), max(XS)            # clamp extent about its origin
clamp = cq.Compound.makeCompound([s.val() for _n, s in BTn.clamp_components(with_lifters=True)])
# CLAMP_BOX="L,W,T,below": study a STAND-IN clamp instead -- a box L along the belt, W across
# its width, T through it with `below` of that on the tooth side -- to size a clamp that
# does not exist yet (e.g. a screwless clip: CLAMP_BOX=26,8.2,5.35,1.6). +z of the box is
# the INSIDE of the belt loop (the tooth side); `below` is what stands outside it.
import os
if os.environ.get("CLAMP_BOX"):
    _L, _W, _T, _b, *_yo = [float(v) for v in os.environ["CLAMP_BOX"].split(",")]
    clamp = (cq.Workplane("XY").box(_L, _W, _T, centered=(True, True, False))
             .translate((0, _yo[0] if _yo else 0.0, -_b)).val())      # 5th value: offset across the belt
    LO, HI = -_L / 2, _L / 2
B.DEMO_POSE_DZ = {i: -D.CARRIAGE_TRAVEL / 2 for i in range(10)}
static = {}
for i in range(10):
    for n, s in B._string_components(i):
        if n.startswith("belt_tensioner"): continue
        static[n] = (i, s.val(), s.val().BoundingBox())
ctx = [("bridge_endplate", B.PARTS["bridge_endplate"][0]().val())] + \
      [(f"chassis_{k}", s.val()) for k, s in enumerate(B.chassis_segments)]
for n, s in ctx: static[n] = (-1, s, s.BoundingBox())
def far(A, Bb): return A.xmax<Bb.xmin or Bb.xmax<A.xmin or A.ymax<Bb.ymin or Bb.ymax<A.ymin or A.zmax<Bb.zmin or Bb.zmax<A.zmin
def geom(i):
    M = V(*D.motor_pos(i)); S = V(D.screw_x(i), D.string_y(i), D.screw_pulley_z(i))
    if RUN == "A":
        mb = V(M.x, M.y, M.z + r); sm = V(S.x, S.y + r, S.z)
    else:
        mb = V(M.x, M.y, M.z - r); sm = V(S.x, S.y - r, S.z)
    return sm, mb.sub(sm).normalized(), mb.sub(sm).Length
def posed(i, p, da=0.0):
    sm, tan, L = geom(i)
    Ls, Lm = p + LO, L - (p + HI)                      # free belt each side of the clamp
    a = (math.pi / 2) * Ls / (Ls + Lm) + math.radians(da)   # 0 at the screw (normal +Y) .. 90 at the motor (+Z)
    n = V(0, math.cos(a), math.sin(a)).multiply(-1.0 if RUN == 'A' else 1.0); n = n.sub(tan.multiply(n.dot(tan))).normalized()
    o = sm.add(tan.multiply(p))
    return clamp.moved(cq.Location(cq.Plane(origin=(o.x, o.y, o.z), xDir=(tan.x, tan.y, tan.z), normal=(n.x, n.y, n.z)))), math.degrees(a)
RUN = sys.argv[3] if len(sys.argv) > 3 else 'B'
STEP = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0
ERR = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
ONLY = [int(x) - 1 for x in sys.argv[5].split(',')] if len(sys.argv) > 5 else range(10)
out = {}
t0 = time.time()
for i in ONLY:
    sm, tan, L = geom(i)
    pmin = D.PULLEY_FLANGE_OD / 2 + D.CLAMP_END_CLR - LO
    pmax = L - D.PULLEY_FLANGE_OD / 2 - D.CLAMP_END_CLR - HI
    n = max(1, int(math.ceil((pmax - pmin) / STEP)))
    rows = []
    for k in range(n + 1):
        p = pmin + (pmax - pmin) * k / n
        a = posed(i, p)[1] - 0.0; hits = {}
        for da in ((-ERR, 0.0, ERR) if ERR else (0.0,)):
            c = posed(i, p, da)[0]; cb = c.BoundingBox()
            for nm, (j, s, sb) in static.items():
                if j == i or far(cb, sb): continue
                try: v = c.intersect(s).Volume()
                except Exception: v = 0.0
                if v > 1e-3: hits[nm] = max(hits.get(nm, 0.0), round(v, 2))
        rows.append((round(p, 1), round(a, 1), hits))
    out[i] = dict(L=L, pmin=pmin, pmax=pmax, rows=rows)
    print("string %2d  run %.1f  p %.1f..%.1f  (%d positions, %.0fs)" % (i + 1, L, pmin, pmax, n + 1, time.time() - t0), flush=True)
    seg = None
    for p, a, h in rows:
        tag = "clear" if not h else ", ".join("%s %.2f" % kv for kv in sorted(h.items()))
        print("    p %6.1f  twist %4.1f  %s" % (p, a, tag), flush=True)
json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else "clamp_study.json", "w"))
print("done %.0fs" % (time.time() - t0))
