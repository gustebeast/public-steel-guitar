import sys, math
sys.path.insert(0, 'elec')
import repair_search as R
b=R.Board('elec/out/output_panel','BOOT0')
A=(100-7.2, 100+4.06)
for margin in (0.15,0.1,0.05):
    R.MARGIN=margin
    for e in [x/10 for x in range(3,30)]:
        E=(A[0],A[1]-e)
        if not b.track_ok(A,E,'F.Cu',half=0.1): continue
        n=20; hits=[]
        for i in range(-n,n+1):
            for j in range(-n,n+1):
                v=(round(E[0]+i*0.1,2), round(E[1]+j*0.1,2))
                if b.via_ok(*v) and b.track_ok(E,v,'F.Cu',half=0.1):
                    hits.append((math.dist(E,v)+e, v))
        if hits:
            hits.sort(); print(margin,e,hits[0], len(hits)); break
    else: print(margin,'none')
# what blocks straight up?
R.MARGIN=0.15
E=(A[0],A[1]-1.0)
for s in b.segs:
    if s['layer']=='F.Cu' and s['net']!='BOOT0' and R._d_seg_seg(*A,*E,s['x1'],s['y1'],s['x2'],s['y2'])<0.1+s['half']+0.15: print('seg',s['net'],round(s['x1']-100,2),round(100-s['y1'],2),round(s['x2']-100,2),round(100-s['y2'],2))
for p in b.pads:
    if p['net']!='BOOT0' and R._d_seg_seg(*A,*E,p['x1'],p['y1'],p['x2'],p['y2'])<0.1+p['r']+0.15: print('pad',p['net'],round(p['x1']-100,2),round(100-p['y1'],2),p['r'])
