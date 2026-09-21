import pcbnew
b=pcbnew.LoadBoard('elec/out/output_panel.kicad_pcb')
def w(p): return (round(p.x/1e6-100,3), round(100-p.y/1e6,3))
for t in b.GetTracks():
    if t.GetNetname().startswith('HUB_DN2'):
        s,e=w(t.GetStart()),w(t.GetEnd())
        if any(-18<p[0]<-12 and -11<p[1]<-5 for p in (s,e)): print(t.GetNetname(), t.GetLayerName(), type(t).__name__, s, e)
