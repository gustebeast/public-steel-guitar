"""Fast wire-to-wire clearance: build_wires() with _wire() stubbed to keep only the polyline,
then centreline distance between every pair of the named wires. No solids, ~3 s.

    py -3.12 -m tools.wire_clearance [-p] [-a] [wire names...]

-p prints the polylines; -a tests every wire against every other. With no names it tests the
keyhead corner (both 24 V pairs, the Pi link and bus A's head), where seven conductors share
one 3.3 mm slot. It sees WIRES ONLY -- parts are check_overlaps' job -- and it treats a wire
as a round tube, so it is the quick iteration loop, not the gate (check_cable_pairs is)."""
import time,sys
import numpy as np
from src import wiring as W
class Stub:
    def __init__(s,pts,d): s.pts=[np.array(p,float) for p in pts]; s.d=d
t=time.time(); _o=W._wire
W._wire=lambda pts,d=W.WIRE_D: Stub(pts,d)
try: out=dict((n,o) for n,o in W.build_wires() if isinstance(o,Stub))
except Exception as e:
    import traceback; traceback.print_exc(); sys.exit(1)
print("stub build %.1fs, %d polylines"%(time.time()-t,len(out)))
def segd(p1,q1,p2,q2):
    d1=q1-p1; d2=q2-p2; r=p1-p2; a=d1@d1; e=d2@d2; f=d2@r
    if a<1e-12 and e<1e-12: s=t=0
    elif a<1e-12: s=0; t=np.clip(f/e,0,1)
    else:
        c=d1@r
        if e<1e-12: t=0; s=np.clip(-c/a,0,1)
        else:
            b=d1@d2; den=a*e-b*b
            s=np.clip((b*f-c*e)/den,0,1) if den>1e-12 else 0.0
            t=(b*s+f)/e
            if t<0: t=0; s=np.clip(-c/a,0,1)
            elif t>1: t=1; s=np.clip((b-c)/a,0,1)
    c1=p1+d1*s; return np.linalg.norm(c1-(p2+d2*t)),c1
DEF=["wire_pwr_hot_11","wire_pwr_gnd_11","wire_pwr_hot_12","wire_pwr_gnd_12","wire_link","wire_canh_0","wire_canl_0"]
names=sys.argv[1:]
if "-p" in names:
    names.remove("-p"); names=names or DEF
    for n in names: print(n, [tuple(round(float(v),2) for v in p) for p in out[n].pts])
if "-a" in names: names=sorted(out)
names=names or DEF
bad=0
for i,a in enumerate(names):
    for b in names[i+1:]:
        A,Bw=out[a],out[b]; need=(A.d+Bw.d)/2
        for k in range(len(A.pts)-1):
            for m in range(len(Bw.pts)-1):
                d,c=segd(A.pts[k],A.pts[k+1],Bw.pts[m],Bw.pts[m+1])
                if d<need+0.05:
                    bad+=1; print("  %-16s seg%d x %-16s seg%d  gap %.2f (need %.2f) at (%.1f, %.1f, %.1f)"%(a,k,b,m,d,need,*c))
print("contacts:",bad)
