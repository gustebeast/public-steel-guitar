import sys, math, itertools
sys.path.insert(0, 'elec')
import repair_search as R
stem='elec/out/output_panel'; net='BOOT0'
b=R.Board(stem, net)
A=(100-7.2, 100+4.06); B=(100+13.49, 100+12.0)   # kicad frame (y down)
def vias_near(p, reach=2.0):
    out=[]; n=int(reach/0.1)
    for i in range(-n,n+1):
        for j in range(-n,n+1):
            v=(round(p[0]+i*0.1,2), round(p[1]+j*0.1,2))
            if b.via_ok(*v) and b.track_ok(p, v, 'F.Cu'):
                out.append((math.hypot(v[0]-p[0],v[1]-p[1]), v))
    out.sort(); return [v for _,v in out]
va=vias_near(A); vb=vias_near(B)
print(len(va), len(vb))
best=None
for L in ('In2.Cu','B.Cu'):
    for a in va[:150]:
        for c in vb[:150]:
            for path in ([a,c],[a,(c[0],a[1]),c],[a,(a[0],c[1]),c]):
                if all(b.track_ok(path[k],path[k+1],L) for k in range(len(path)-1)):
                    t=math.dist(A,a)+math.dist(B,c)+sum(math.dist(path[k],path[k+1]) for k in range(len(path)-1))
                    if best is None or t<best[0]: best=(t,L,path)
print(best)
if best:
    t,L,path=best
    f=lambda p:(round(p[0]-100,3), round(100-p[1],3))
    print('repair_vias', [f(path[0]), f(path[-1])])
    print('F', [f(A), f(path[0])], [f(B), f(path[-1])])
    print(L, [f(p) for p in path])
