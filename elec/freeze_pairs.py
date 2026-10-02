# Lift the named nets' routed copper out of elec/out/output_panel.kicad_pcb into
# elec/output_panel.frozen.json (placement frame). Run with KiCad's python from the repo
# root, ONLY on a board whose finish.py summary carries no verify FAIL. See the note at
# the bottom of output_panel.py.
import pcbnew, json, sys
b=pcbnew.LoadBoard("elec/out/output_panel.kicad_pcb"); mm=pcbnew.ToMM
NETS=("THRU_DP","THRU_DM","HUB_DN1_DP","HUB_DN1_DM","HUB_DN2_DP","HUB_DN2_DM","HUB_UP_DP","HUB_UP_DM")
out={"nets":list(NETS),"tracks":[],"vias":[]}
P=lambda p:(round(mm(p.x)-100.0,4), round(100.0-mm(p.y),4))
for t in b.GetTracks():
    n=t.GetNetname()
    if n=="GND" and t.GetClass()=="PCB_VIA":
        x,y=P(t.GetPosition())
        if abs(x+9.5)<0.01 and abs(y+7.3)<0.01: print("calibration: declared GND via found at",(x,y))
    if n not in NETS: continue
    if t.GetClass()=="PCB_VIA":
        x,y=P(t.GetPosition()); out["vias"].append([n,x,y,round(mm(t.GetDrillValue()),3),round(mm(t.GetWidth(pcbnew.F_Cu)),3)])
    else:
        out["tracks"].append([n,t.GetLayerName(),round(mm(t.GetWidth()),3),[list(P(t.GetStart())),list(P(t.GetEnd()))]])
json.dump(out,open("elec/output_panel.frozen.json","w"),indent=0)
import collections
c=collections.Counter(t[0] for t in out["tracks"]); print(dict(c), "vias", collections.Counter(v[0] for v in out["vias"]))
print(set((t[1],t[2]) for t in out["tracks"]), set((v[3],v[4]) for v in out["vias"]))
