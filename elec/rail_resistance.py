"""Path resistance from a rail's SOURCE pad to every pad on the net, on a routed board.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/rail_resistance.py elec/out/optical.kicad_pcb +3V3A U9.5

WHY IT EXISTS (2026-10-01). DRC says a net is connected; it cannot say THROUGH WHAT. The
optical board's analog rail was "0 unconnected" with its LDO on one island and every load
on another, joined by 62 mm of 0.127 mm repair track: 0.6-0.7 ohm to the converters. A
width tally found the thin copper; this is what says whether thin copper MATTERS, because
it depends on where the source is.

It is a single shortest path over the TRACKS (Dijkstra on ohms), so it is an UPPER bound:
parallel paths and pours are not credited. A pad it cannot reach by track is fed by a pour
or a plane and is listed, not failed. 1 oz outer / 0.5 oz inner copper assumed.
"""
import pcbnew,sys,heapq,collections,math
b=pcbnew.LoadBoard(sys.argv[1]); net=sys.argv[2]; src=sys.argv[3]; M=pcbnew.ToMM
RS={"F.Cu":0.5e-3,"B.Cu":0.5e-3,"In1.Cu":1.0e-3,"In2.Cu":1.0e-3}   # ohm/sq: 1 oz outer, 0.5 oz inner
G=collections.defaultdict(list)
def e(a,c,r): G[a].append((c,r)); G[c].append((a,r))
R=lambda v:(round(M(v.x),2),round(M(v.y),2))
trk=[t for t in b.GetTracks() if t.GetNetname()==net]
segs=[]
for t in trk:
    if t.GetClass()=="PCB_VIA":
        p=R(t.GetPosition())
        for L in RS:
            if L!="F.Cu": e(("F.Cu",)+p,(L,)+p,0.5e-3)
    else:
        L=t.GetLayerName(); a=(L,)+R(t.GetStart()); c=(L,)+R(t.GetEnd()); w=M(t.GetWidth()); ln=M(t.GetLength())
        e(a,c,RS[L]*ln/w); segs.append((t,L,a,c,w))
nodes=list(G.keys())
for t,L,a,c,w in segs:
    for n in nodes:
        if n[0]==L and n!=a and n!=c and t.HitTest(pcbnew.VECTOR2I(pcbnew.FromMM(n[1]),pcbnew.FromMM(n[2])),pcbnew.FromMM(0.02)):
            e(n,a,RS[L]*math.hypot(n[1]-a[1],n[2]-a[2])/w); e(n,c,RS[L]*math.hypot(n[1]-c[1],n[2]-c[2])/w)
pads={}
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname()==net:
            k=("PAD",fp.GetReference()+"."+p.GetNumber()); pads[k]=p; bb=p.GetBoundingBox()
            for n in nodes:
                if p.IsOnLayer(b.GetLayerID(n[0])) and bb.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(n[1]),pcbnew.FromMM(n[2]))): e(k,n,0.0)
S=("PAD",src); d={S:0.0}; pq=[(0.0,S)]
while pq:
    c,u=heapq.heappop(pq)
    if c>d.get(u,9e9): continue
    for v,r in G[u]:
        if c+r<d.get(v,9e9): d[v]=c+r; heapq.heappush(pq,(c+r,v))
res=sorted(((d.get(k,float('inf')),k[1]) for k in pads),reverse=True)
unre=[n for r,n in res if r==float('inf')]
print("%s from %s: %d pads, %d unreached by tracks (pour/plane-fed) %s"%(net,src,len(res),len(unre),unre[:6]))
for r,n in [x for x in res if x[0]<9e9][:6]: print("   %-10s %.0f mohm"%(n,r*1000))
