import pcbnew
b=pcbnew.LoadBoard('elec/out/motor_ctrl.kicad_pcb')
def w(p): return (round(p.x/1e6-100,2), round(100-p.y/1e6,2))
u=b.FindFootprintByReference('U4')
for p in u.Pads():
    x,y=w(p.GetPosition())
    if x< -7 : print('U4', p.GetNumber(), p.GetNetname(), (x,y))
for n in ('USB_DP','USB_DM'):
    for t in b.GetTracks():
        if t.GetNetname()==n: print(n, t.GetLayerName(), w(t.GetStart()), w(t.GetEnd()))
