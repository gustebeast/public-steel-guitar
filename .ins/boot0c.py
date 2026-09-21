import sys, math
sys.path.insert(0, 'elec')
import repair_search as R
b=R.Board('elec/out/output_panel','BOOT0')
A=(100-7.2, 100+4.06); E=(A[0],A[1]-0.4)
va=[]
for i in range(-20,21):
    for j in range(-20,21):
        v=(round(E[0]+i*0.1,2), round(E[1]+j*0.1,2))
        if b.via_ok(*v) and b.track_ok(E,v,'F.Cu',half=0.1): va.append(v)
B=(100+13.49, 100+12.0)
vb=[]
for i in range(-25,26):
    for j in range(-25,26):
        v=(round(B[0]+i*0.1,2), round(B[1]+j*0.1,2))
        if b.via_ok(*v) and b.track_ok(B,v,'F.Cu'): vb.append(v)
vb.sort(key=lambda v: math.dist(v,B)); vb=vb[:300]
print(len(va),len(vb))
best=None
for L in ('In2.Cu','B.Cu'):
    for a in va:
        for c in vb:
            mids=[[],[(c[0],a[1])],[(a[0],c[1])]]
            for ym in range(-8,8):   # dogleg via horizontal at a chosen y
                y=a[1]+ym*0.5; mids.append([(a[0],y),(c[0],y)])
            for m in mids:
                path=[a]+m+[c]
                if all(b.track_ok(path[k],path[k+1],L) for k in range(len(path)-1)):
                    t=sum(math.dist(path[k],path[k+1]) for k in range(len(path)-1))+math.dist(B,c)
                    if best is None or t<best[0]: best=(t,L,path)
print(best)
if best:
    f=lambda p:(round(p[0]-100,3), round(100-p[1],3))
    t,L,path=best
    print('vias',f(path[0]),f(path[-1])); print('F',f(A),f(E),f(path[0]),'|',f(B),f(path[-1])); print(L,[f(p) for p in path])
