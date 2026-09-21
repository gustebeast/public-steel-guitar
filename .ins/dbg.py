import sys; sys.path.insert(0,'.')
import src.wiring as W
cap={}
orig=W._wire
def spy(pts,d=W.WIRE_D):
    r=orig(pts,d); cap[id(r)]=pts; return r
W._wire=spy
w=dict(W.build_wires())
for n in ('wire_canh_1','wire_canl_1','wire_pwr_hot_2','wire_pwr_gnd_2'):
    print(n, [tuple(round(v,2) for v in p) for p in cap[id(w[n])]])
