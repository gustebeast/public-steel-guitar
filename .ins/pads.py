import pcbnew
b=pcbnew.LoadBoard('elec/out/optical.kicad_pcb')
F={f.GetReference():f for f in b.GetFootprints()}
def pads(r):
    out=[]
    for p in F[r].Pads():
        bb=p.GetBoundingBox(); out.append((p.GetNetname(), bb.GetLeft()/1e6, bb.GetRight()/1e6, bb.GetTop()/1e6, bb.GetBottom()/1e6))
    return out
for r in ('D1','PD1A','PD1B'):
    for q in pads(r): print(r, q[0], [round(v,3) for v in q[1:]])
ds=b.GetDesignSettings(); print('min clearance', ds.m_MinClearance/1e6 if hasattr(ds,'m_MinClearance') else '?', 'solder mask min web', ds.m_SolderMaskMinWidth/1e6)
