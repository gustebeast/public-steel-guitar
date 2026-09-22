import sys, json, pcbnew
b = pcbnew.LoadBoard(sys.argv[1] if len(sys.argv) > 1 else 'elec/out/optical.kicad_pcb')
out = {'tracks': [], 'vias': [], 'pads': []}
L = {pcbnew.F_Cu: 'F', pcbnew.In1_Cu: 'I1', pcbnew.In2_Cu: 'I2', pcbnew.B_Cu: 'B'}
m = lambda v: (pcbnew.ToMM(v.x) - 100, 100 - pcbnew.ToMM(v.y))
for t in b.GetTracks():
    if type(t) is pcbnew.PCB_VIA: out['vias'].append(m(t.GetPosition()) + (t.GetNetname(),))
    elif type(t) is pcbnew.PCB_TRACK: out['tracks'].append([m(t.GetStart()), m(t.GetEnd()), pcbnew.ToMM(t.GetWidth()), L.get(t.GetLayer(), '?'), t.GetNetname()])
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox()
        out['pads'].append([m(p.GetPosition()), pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()), p.GetNetname(), f.GetReference()])
out['fp'] = {f.GetReference(): m(f.GetPosition()) for f in b.GetFootprints()}
json.dump(out, open('.ins/board_dump.json', 'w'))
