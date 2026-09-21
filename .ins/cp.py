import sys; sys.path.insert(0,'.')
import src.wiring as W
w=dict(W.build_wires())
pairs=[('wire_canh_0','wire_pwr_hot_2'),('wire_canh_1','wire_canl_0'),('wire_canh_0','wire_canh_1'),('wire_pwr_hot_0','wire_pwr_gnd_0'),('wire_canl_0','wire_canl_1'),('wire_pwr_hot_12','wire_pwr_gnd_11'),('wire_canl_0','wire_pwr_gnd_11')]
for a,b in pairs:
    i=w[a].intersect(w[b]); 
    for s in i.val().Solids():
        bb=s.BoundingBox(); print(f'{a:16s} {b:16s} {s.Volume():6.2f}  x {bb.xmin:8.1f}..{bb.xmax:8.1f} y {bb.ymin:7.1f}..{bb.ymax:7.1f} z {bb.zmin:6.1f}..{bb.zmax:6.1f}')
