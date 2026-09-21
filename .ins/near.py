import pcbnew
b=pcbnew.LoadBoard('elec/out/motor_ctrl.kicad_pcb')
def w(p): return (round(p.x/1e6-100,2), round(100-p.y/1e6,2))
for t in b.GetTracks():
    s,e=w(t.GetStart()),w(t.GetEnd())
    if any(-11<p[0]<-1 and -18<p[1]<-6 for p in (s,e)) and t.GetLayerName() in ('F.Cu',) :
        print(t.GetNetname(), type(t).__name__, s, e)
for p in b.GetFootprint if False else []: pass
