import pcbnew
b=pcbnew.LoadBoard('elec/out/output_panel.kicad_pcb')
for r in ('J1','J3'):
    f=b.FindFootprintByReference(r)
    print(r, sorted({(p.GetNumber(), p.GetNetname()) for p in f.Pads()}))
